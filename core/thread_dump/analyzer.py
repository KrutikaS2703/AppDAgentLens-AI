import gzip
import io
import re
import zipfile
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


THREAD_HEADER_RE = re.compile(r'^"(?P<name>[^\"]+)"')
STATE_RE = re.compile(r"java\.lang\.Thread\.State:\s+([A-Z_]+)")
LOCKED_RE = re.compile(r"- locked <([^>]+)>")
WAITING_RE = re.compile(r"- (?:waiting to lock|parking to wait for) <([^>]+)>")


def parse_uploaded_thread_dump(uploaded_file, max_size_mb: int = 200) -> Tuple[List[Dict[str, str]], List[str]]:
    """Parse uploaded thread dump sources from txt/log/tdump/gz/zip into text documents."""
    docs: List[Dict[str, str]] = []
    warnings: List[str] = []

    if uploaded_file is None:
        return docs, warnings

    raw = uploaded_file.getvalue()
    file_size_mb = len(raw) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        warnings.append(
            f"Uploaded file size is {file_size_mb:.1f} MB which is above the {max_size_mb} MB analyzer limit."
        )
        return docs, warnings

    name = uploaded_file.name.lower()
    if name.endswith(".zip"):
        docs_from_zip, zip_warnings = _read_zip(raw)
        docs.extend(docs_from_zip)
        warnings.extend(zip_warnings)
    elif name.endswith(".gz"):
        try:
            text = gzip.decompress(raw).decode("utf-8", errors="ignore")
            docs.append({"name": uploaded_file.name, "content": text})
        except Exception as exc:
            warnings.append(f"Could not read gzip file {uploaded_file.name}: {exc}")
    else:
        docs.append({"name": uploaded_file.name, "content": raw.decode("utf-8", errors="ignore")})

    if not docs:
        warnings.append("No readable thread dump content found in the uploaded file.")

    return docs, warnings


def _read_zip(raw: bytes) -> Tuple[List[Dict[str, str]], List[str]]:
    docs: List[Dict[str, str]] = []
    warnings: List[str] = []

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                lower_name = info.filename.lower()
                if not lower_name.endswith((".txt", ".log", ".tdump", ".dump", ".out", ".gz")):
                    continue

                try:
                    file_bytes = zf.read(info.filename)
                    if lower_name.endswith(".gz"):
                        content = gzip.decompress(file_bytes).decode("utf-8", errors="ignore")
                    else:
                        content = file_bytes.decode("utf-8", errors="ignore")
                    docs.append({"name": info.filename, "content": content})
                except Exception as exc:
                    warnings.append(f"Could not parse {info.filename} inside zip: {exc}")
    except Exception as exc:
        warnings.append(f"Could not open zip file: {exc}")

    return docs, warnings


def analyze_thread_dump_text(text: str) -> Dict:
    """Deterministic thread-dump analysis for deadlocks, states, contention, hot stacks, and stuck threads."""
    if not text.strip():
        return {
            "threads": [],
            "thread_count": 0,
            "state_counts": {},
            "deadlock_sections": [],
            "top_lock_contention": [],
            "top_lock_owners": [],
            "hot_stacks": [],
            "stuck_threads": [],
            "summary": "No thread dump content found.",
        }

    threads = _extract_threads(text)
    state_counts = Counter([t.get("state", "UNKNOWN") for t in threads])
    deadlock_sections = _extract_deadlock_sections(text)
    lock_contention, lock_owners = _compute_lock_contention(threads)
    hot_stacks = _compute_hot_stacks(threads)
    stuck_threads = _detect_stuck_threads(threads, lock_contention)

    summary_parts = [
        f"Threads parsed: {len(threads)}",
        f"Deadlocks detected: {len(deadlock_sections)}",
        f"Blocked threads: {state_counts.get('BLOCKED', 0)}",
        f"Runnable threads: {state_counts.get('RUNNABLE', 0)}",
        f"Waiting threads: {state_counts.get('WAITING', 0) + state_counts.get('TIMED_WAITING', 0)}",
    ]

    return {
        "threads": threads,
        "thread_count": len(threads),
        "state_counts": dict(state_counts),
        "deadlock_sections": deadlock_sections,
        "top_lock_contention": lock_contention[:10],
        "top_lock_owners": lock_owners[:10],
        "hot_stacks": hot_stacks[:10],
        "stuck_threads": stuck_threads[:20],
        "summary": " | ".join(summary_parts),
    }


def _extract_threads(text: str) -> List[Dict]:
    threads: List[Dict] = []
    current = None

    for line in text.splitlines():
        header_match = THREAD_HEADER_RE.match(line.strip())
        if header_match:
            if current:
                threads.append(current)
            current = {
                "name": header_match.group("name"),
                "state": "UNKNOWN",
                "stack": [],
                "locks_held": [],
                "waiting_on": None,
            }
            continue

        if current is None:
            continue

        state_match = STATE_RE.search(line)
        if state_match:
            current["state"] = state_match.group(1)

        locked_match = LOCKED_RE.search(line)
        if locked_match:
            current["locks_held"].append(locked_match.group(1))

        waiting_match = WAITING_RE.search(line)
        if waiting_match:
            current["waiting_on"] = waiting_match.group(1)

        if line.strip().startswith("at "):
            current["stack"].append(line.strip())

    if current:
        threads.append(current)

    return threads


def _extract_deadlock_sections(text: str) -> List[str]:
    sections: List[str] = []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if "Found one Java-level deadlock" in line:
            snippet = lines[i : min(i + 70, len(lines))]
            sections.append("\n".join(snippet))

    return sections


def _compute_lock_contention(threads: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    owner_map: Dict[str, str] = {}
    waiting_map: Dict[str, List[str]] = defaultdict(list)

    for t in threads:
        t_name = t.get("name", "<unknown>")
        for lock_id in t.get("locks_held", []):
            owner_map[lock_id] = t_name
        waiting_on = t.get("waiting_on")
        if waiting_on:
            waiting_map[waiting_on].append(t_name)

    contention = []
    owner_counts = Counter()

    for lock_id, waiters in waiting_map.items():
        owner = owner_map.get(lock_id, "unknown")
        owner_counts[owner] += len(waiters)
        contention.append(
            {
                "lock_id": lock_id,
                "owner": owner,
                "waiter_count": len(waiters),
                "waiters": waiters,
            }
        )

    contention.sort(key=lambda x: x["waiter_count"], reverse=True)
    top_owners = [
        {"owner": owner, "blocked_threads": count}
        for owner, count in owner_counts.most_common()
        if owner and owner != "unknown"
    ]

    return contention, top_owners


def _stack_signature(stack: List[str], depth: int = 8) -> str:
    if not stack:
        return "<no-stack>"
    key_lines = [re.sub(r"\(.*\)", "", s) for s in stack[:depth]]
    return " | ".join(key_lines)


def _compute_hot_stacks(threads: List[Dict]) -> List[Dict]:
    grouped: Dict[str, List[str]] = defaultdict(list)

    for t in threads:
        sig = _stack_signature(t.get("stack", []))
        grouped[sig].append(t.get("name", "<unknown>"))

    hot = []
    for sig, names in grouped.items():
        if len(names) > 1:
            hot.append(
                {
                    "signature": sig,
                    "count": len(names),
                    "sample_threads": names[:8],
                }
            )

    hot.sort(key=lambda x: x["count"], reverse=True)
    return hot


def _detect_stuck_threads(threads: List[Dict], lock_contention: List[Dict]) -> List[Dict]:
    contention_locks = {entry["lock_id"] for entry in lock_contention[:10] if entry["waiter_count"] >= 2}
    stuck: List[Dict] = []

    for t in threads:
        reasons = []
        state = t.get("state", "UNKNOWN")
        name = t.get("name", "<unknown>")
        waiting_on = t.get("waiting_on")

        if state == "BLOCKED":
            reasons.append("Thread is BLOCKED")

        if waiting_on and waiting_on in contention_locks:
            reasons.append("Waiting on a heavily contended lock")

        stack_text = " ".join(t.get("stack", [])).lower()
        if "deadlock" in stack_text:
            reasons.append("Deadlock term found in stack")

        if any(k in name.lower() for k in ["stuck", "blocked", "hung"]):
            reasons.append("Thread name hints at stuck condition")

        if reasons:
            stuck.append(
                {
                    "thread": name,
                    "state": state,
                    "waiting_on": waiting_on or "",
                    "reasons": reasons,
                }
            )

    return stuck
