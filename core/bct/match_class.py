#!/usr/bin/env python3
from core.bct.files import *

MATCH_KEY = "Matching class name"


# -----------------------------
# Extract matched class
# -----------------------------
def extract_class_from_match(line):
    """
    Example line:
    Matching class name com/tibco/plugin/json/rest/server/runtime/http/XiHttpServlet

    Java BCT logic effectively does:
      line.substring(line.indexOf("Matching")).split()[3]
    """
    try:
        tail = line[line.index("Matching"):]
        return tail.split()[3]
    except Exception:
        return None


# -----------------------------
# Scan logs for MATCH classes
# -----------------------------
def scan_match_classes(folder):
    matched_classes = []

    for path in get_unique_bct_files(folder):
        with open_log(path) as f:
            for line in f:
                if MATCH_KEY in line:
                    cls = extract_class_from_match(line)
                    if cls:
                        matched_classes.append(cls)

    return matched_classes
