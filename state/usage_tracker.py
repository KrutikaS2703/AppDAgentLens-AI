import json
import os
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st


COUNTERS_PATH = Path(__file__).resolve().parent / "usage_counters.json"
_WRITE_LOCK = threading.Lock()

ANALYZER_COUNTER_KEYS = {
    "BCT Analyzer": "bct_analyzer_access",
    "BT Analyzer": "bt_analyzer_access",
    "Agent Analyzer": "agent_analyzer_access",
    "AI Assistant": "ai_assistant_access",
    "Log File Browser": "log_file_browser_access",
}


def _read_counters() -> dict:
    if not COUNTERS_PATH.exists():
        return {}

    try:
        data = json.loads(COUNTERS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_counters(counters: dict) -> None:
    COUNTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = COUNTERS_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(counters, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp_path, COUNTERS_PATH)


def increment_counter(counter_key: str, amount: int = 1) -> None:
    if amount <= 0:
        return

    with _WRITE_LOCK:
        counters = _read_counters()
        current = counters.get(counter_key, 0)
        try:
            current = int(current)
        except (TypeError, ValueError):
            current = 0

        counters[counter_key] = current + amount
        counters["last_updated_utc"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        _write_counters(counters)


def track_ui_access_once_per_session() -> None:
    state_key = "_usage_ui_access_tracked"
    if st.session_state.get(state_key):
        return

    increment_counter("ui_access")
    st.session_state[state_key] = True


def track_analyzer_selection(analyzer_label: str) -> None:
    counter_key = ANALYZER_COUNTER_KEYS.get(analyzer_label)
    if not counter_key:
        return

    state_key = "_usage_last_analyzer_counter"
    if st.session_state.get(state_key) == counter_key:
        return

    increment_counter(counter_key)
    st.session_state[state_key] = counter_key
