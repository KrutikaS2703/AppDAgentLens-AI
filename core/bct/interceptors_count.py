#!/usr/bin/env python3

from collections import Counter

from core.bct.files import get_unique_bct_files, open_log

APPLY_KEY = "Applying method interceptor"
DESC_KEY = "with description "


# -----------------------------
# Extract interceptor description
# -----------------------------
def extract_interceptor_description(line):
    """
    Example:
    Applying method interceptor with description async.handoff.AsyncTaskArg1AnnouncementTracker at com/...

    Returns:
    async.handoff.AsyncTaskArg1AnnouncementTracker
    """
    try:
        after_desc = line.split(DESC_KEY, 1)[1]
        interceptor = after_desc.split(" at ", 1)[0]
        return interceptor.strip()
    except Exception:
        return None


# -----------------------------
# Scan logs
# -----------------------------
def scan_interceptor_counts(folder):
    counter = Counter()

    for path in get_unique_bct_files(folder):
        with open_log(path) as f:
            for line in f:
                if APPLY_KEY in line and DESC_KEY in line:
                    interceptor = extract_interceptor_description(line)
                    if interceptor:
                        counter[interceptor] += 1

    return counter


