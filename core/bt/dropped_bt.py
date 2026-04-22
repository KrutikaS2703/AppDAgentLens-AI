# core/bt/dropped_bt.py

import re
from collections import defaultdict
from pathlib import Path

# Regex patterns
SUMMARY_PATTERN = re.compile(
    r"Dropped BT \[(?P<bt>.*?)\]\s+Load\s+\[(?P<count>\d+)\]"
)

EVENT_PATTERN = re.compile(
    r"Dropped BT \[\d+\]\s+Name\[(?P<bt>.*?)\]"
)

def scan_dropped_bts(log_dir: str) -> dict:
    """
    Parses JavaAgent logs and returns:
    {
        "/bt/name": count,
        ...
    }
    """
    dropped_counts = defaultdict(int)

    for log_file in Path(log_dir).glob("*.log"):
        try:
            with open(log_file, errors="ignore") as f:
                for line in f:
                    # Format 1
                    m1 = SUMMARY_PATTERN.search(line)
                    if m1:
                        bt = m1.group("bt")
                        count = int(m1.group("count"))
                        dropped_counts[bt] += count
                        continue

                    # Format 2
                    m2 = EVENT_PATTERN.search(line)
                    if m2:
                        bt = m2.group("bt")
                        dropped_counts[bt] += 1
        except Exception:
            continue

    return dict(dropped_counts)
