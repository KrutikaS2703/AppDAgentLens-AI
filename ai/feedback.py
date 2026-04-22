"""Persistent feedback storage for AI Assistant answer corrections."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


FEEDBACK_FILE = Path(__file__).resolve().parent.parent / "kb_data" / "chat_feedback.json"


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", (question or "").strip().lower())


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_.-]+", (text or "").lower())


def _ensure_feedback_dir() -> None:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_feedback_entries() -> List[Dict[str, str]]:
    if not FEEDBACK_FILE.exists():
        return []

    try:
        content = FEEDBACK_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_feedback_entries(entries: List[Dict[str, str]]) -> None:
    _ensure_feedback_dir()
    FEEDBACK_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def save_feedback(question: str, assistant_answer: str, correction: str) -> None:
    normalized = _normalize_question(question)
    if not normalized or not (correction or "").strip():
        return

    entries = load_feedback_entries()
    record = {
        "question": question.strip(),
        "question_normalized": normalized,
        "assistant_answer": (assistant_answer or "").strip(),
        "correction": correction.strip(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    replaced = False
    for i, entry in enumerate(entries):
        if entry.get("question_normalized") == normalized:
            entries[i] = record
            replaced = True
            break

    if not replaced:
        entries.append(record)

    _save_feedback_entries(entries)


def delete_feedback(question_normalized: str) -> bool:
    key = (question_normalized or "").strip().lower()
    if not key:
        return False

    entries = load_feedback_entries()
    if not entries:
        return False

    updated = [entry for entry in entries if entry.get("question_normalized") != key]
    if len(updated) == len(entries):
        return False

    _save_feedback_entries(updated)
    return True


def clear_feedback() -> None:
    _save_feedback_entries([])


def get_correction_for_question(question: str) -> Optional[str]:
    normalized = _normalize_question(question)
    if not normalized:
        return None

    entries = load_feedback_entries()
    if not entries:
        return None

    # Exact normalized-question match first.
    for entry in entries:
        if entry.get("question_normalized") == normalized:
            correction = (entry.get("correction") or "").strip()
            if correction:
                return correction

    # Fallback to token-overlap for near-identical repeats.
    q_tokens = set(_tokenize(normalized))
    if not q_tokens:
        return None

    best_score = 0.0
    best_correction: Optional[str] = None
    for entry in entries:
        entry_q = entry.get("question_normalized", "")
        entry_tokens = set(_tokenize(entry_q))
        if not entry_tokens:
            continue
        overlap = len(q_tokens.intersection(entry_tokens)) / max(len(q_tokens), len(entry_tokens))
        if overlap > best_score:
            candidate = (entry.get("correction") or "").strip()
            if candidate:
                best_score = overlap
                best_correction = candidate

    if best_score >= 0.85:
        return best_correction

    return None