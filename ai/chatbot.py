"""
AI assistant for AppDynamics node properties and general knowledge base Q&A.
- "Get Node Properties" lists all properties from node-properties.txt.
- All other questions use RAG retrieval from kb_documents/ and an LLM for the answer.
"""

from pathlib import Path
import re
import os
import threading
from typing import Dict, List, Tuple


NODE_PROPERTIES_FILE = Path(__file__).resolve().parent.parent / "kb_documents" / "node-properties.txt"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_.-]+", text.lower())


def _parse_properties_file(file_path: Path) -> List[Dict[str, str]]:
    """Parse node-properties.txt block format.

    Each block:
        name: <property-name>
        type: <type>
        value: <default-value>
        description: <description text>
    Blocks are separated by blank lines.
    """
    properties: List[Dict[str, str]] = []
    if not file_path.exists():
        return properties

    current: Dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            # blank line = end of block
            if current.get("name"):
                properties.append({
                    "property": current.get("name", "").strip(),
                    "type": current.get("type", "").strip(),
                    "value": current.get("value", "").strip(),
                    "description": current.get("description", "").strip(),
                })
            current = {}
            continue

        if line.startswith("#"):
            continue

        if ":" in line:
            key, _, val = line.partition(":")
            current[key.strip().lower()] = val.strip()

    # flush last block if file has no trailing blank line
    if current.get("name"):
        properties.append({
            "property": current.get("name", "").strip(),
            "type": current.get("type", "").strip(),
            "value": current.get("value", "").strip(),
            "description": current.get("description", "").strip(),
        })

    return properties


def _score_property(question_tokens: List[str], row: Dict[str, str]) -> int:
    combined = " ".join([row["property"], row.get("type", ""), row["value"], row["description"]]).lower()
    return sum(3 if token in row["property"].lower() else 1 for token in question_tokens if token in combined)


def _format_property_rows(rows: List[Dict[str, str]]) -> str:
    formatted = []
    for row in rows:
        type_label = f" *(type: {row['type']})*" if row.get("type") else ""
        formatted.append(
            f"- **{row['property']}**{type_label} — default: `{row['value']}`\n"
            f"  {row['description']}"
        )
    return "\n".join(formatted)


def _all_properties_answer(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "No node properties found in node-properties.txt."

    return (
        "Node properties available:\n\n"
        + _format_property_rows(rows)
        + "\n\nYou can ask things like: `jmx`, `reconnect`, `thread`, or `mbean`."
    )


def _limit_kb_context(context: str) -> str:
    """Keep prompt context bounded so LLM calls stay responsive."""
    max_chars_raw = os.getenv("KB_CONTEXT_MAX_CHARS", "6000").strip()
    try:
        max_chars = max(int(max_chars_raw), 1000)
    except ValueError:
        max_chars = 6000

    if len(context) <= max_chars:
        return context

    return context[:max_chars] + "\n\n[Context truncated for faster response]"


def _ask_llm_with_deadline(ask_llm_fn, prompt: str) -> Tuple[str, str]:
    """Run LLM call with a hard timeout to keep UI responsive. Returns (response, model_name)."""
    timeout_raw = os.getenv("CHATBOT_LLM_DEADLINE_SECONDS", "35").strip()
    try:
        timeout_s = max(int(timeout_raw), 1)
    except ValueError:
        timeout_s = 35

    result = {"value": None, "model": None, "error": None}

    def _worker():
        try:
            response, model = ask_llm_fn(prompt)
            result["value"] = response
            result["model"] = model
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if thread.is_alive():
        return "AI unavailable: timed out", "Unknown"
    if result["error"] is not None:
        return "AI unavailable: internal error", "Unknown"

    return str(result["value"] or "").strip(), str(result["model"] or "Unknown").strip()


def ask_chatbot_with_source(question: str) -> Dict[str, str]:
    """
    Answer user questions using kb_documents/ as the knowledge source.

    - "Get Node Properties" / "List node properties" → return all parsed entries
      from node-properties.txt without calling the LLM.
    - All other queries:
        1. RAG retrieval from kb_documents/ (includes node-properties.txt and JVM-args.txt).
        2. LLM generates an answer grounded in the retrieved context.
        3. If LLM is unavailable, the raw retrieved excerpts are returned.
        4. If nothing is retrieved, the LLM answers from its own knowledge.
    """
    from ai.kb_seed import initialize_kb
    from ai.rag import get_vector_db, format_retrieved_docs
    from ai.llm import ask_llm_with_model
    from ai.prompts import KB_QA_PROMPT, GENERAL_QA_PROMPT
    from ai.feedback import get_correction_for_question

    normalized = re.sub(r"\s+", " ", (question or "").strip().lower())

    corrected_answer = get_correction_for_question(question)
    if corrected_answer:
        return {
            "answer": corrected_answer,
            "source": "Learned Correction",
            "model": "N/A",
        }

    # ── "Get Node Properties" intent: list all parsed node-properties entries ──
    if not normalized or normalized in {
        "get node properties", "show node properties", "list node properties"
    }:
        rows = _parse_properties_file(NODE_PROPERTIES_FILE)
        return {
            "answer": _all_properties_answer(rows),
            "source": "Local Node Properties",
            "model": "N/A",
        }

    # ── RAG retrieval from kb_documents/ ──
    initialize_kb()
    db = get_vector_db()
    retrieved = db.retrieve(question, top_k=4)

    if retrieved:
        kb_context = format_retrieved_docs(retrieved)
        kb_context = _limit_kb_context(kb_context)
        prompt = KB_QA_PROMPT.format(context=kb_context, question=question)
        response, model = _ask_llm_with_deadline(ask_llm_with_model, prompt)
        if response and not response.strip().lower().startswith("ai unavailable"):
            return {
                "answer": response,
                "source": "KB + AI",
                "model": model,
            }
        # LLM unavailable — surface the raw KB excerpts as a fallback
        return {
            "answer": (
                "AI response unavailable. Here is the most relevant information from the knowledge base:\n\n"
                + kb_context
            ),
            "source": "KB Fallback",
            "model": "N/A",
        }

    # ── Nothing found in KB — ask LLM to answer on its own ──
    prompt = GENERAL_QA_PROMPT.format(question=question)
    response, model = _ask_llm_with_deadline(ask_llm_with_model, prompt)
    if response and not response.strip().lower().startswith("ai unavailable"):
        return {
            "answer": response,
            "source": "AI Only",
            "model": model,
        }

    return {
        "answer": (
            "I could not find relevant information in the knowledge base, "
            "and the AI is currently unavailable. Please try again later or "
            "rephrase your question."
        ),
        "source": "AI Unavailable",
        "model": "N/A",
    }


def ask_chatbot(question: str) -> str:
    result = ask_chatbot_with_source(question)
    return result.get("answer", "")

