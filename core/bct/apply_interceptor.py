#!/usr/bin/env python3

import re

from core.bct.files import *

APPLY_KEY = "Applying method interceptor"
DESC_KEY = "with description "

APPLY_PATTERN = re.compile(
    r"Applying method interceptor(?:\s+with description\s+(?P<interceptor>.+?))?\s+at\s+(?P<class_name>.+?)\.(?P<method_name>[^.(\s]+)\s*\("
)


def extract_apply_details(line):
    """
    Example:
    Applying method interceptor with description async.handoff.AsyncTaskArg1AnnouncementTracker at com/tibco/.../XiHttpServlet.service (...)

    Returns:
    {
        "interceptor": "async.handoff.AsyncTaskArg1AnnouncementTracker",
        "class_name": "com/tibco/.../XiHttpServlet",
        "method_name": "service",
    }
    """

    match = APPLY_PATTERN.search(line)
    if not match:
        return None

    return {
        "interceptor": (match.group("interceptor") or "").strip() or None,
        "class_name": match.group("class_name").strip(),
        "method_name": match.group("method_name").strip(),
    }


# -----------------------------
# Extract class from APPLY line
# -----------------------------
def extract_class_from_apply(line):
    """
    Example:
    Applying method interceptor ... at com/tibco/.../XiHttpServlet.service (...)

    We want:
    com/tibco/.../XiHttpServlet
    """

    details = extract_apply_details(line)
    if details:
        return details["class_name"]

    try:
        after_at = line.split(" at ", 1)[1]
        class_part = after_at.split(".", 1)[0]
        return class_part.strip()
    except Exception:
        return None


def scan_applied_by_interceptor(folder):
    """
    Group applied classes and methods by interceptor.

    Returns:
    {
        "interceptor.name": {
            "com/example/MyClass": ["method1", "method2"],
        }
    }
    """

    applied_by_interceptor = {}

    for path in get_unique_bct_files(folder):
        with open_log(path) as f:
            for line in f:
                if APPLY_KEY not in line or DESC_KEY not in line:
                    continue

                details = extract_apply_details(line)
                if not details or not details["interceptor"]:
                    continue

                interceptor = details["interceptor"]
                class_name = details["class_name"]
                method_name = details["method_name"]

                if interceptor not in applied_by_interceptor:
                    applied_by_interceptor[interceptor] = {}
                if class_name not in applied_by_interceptor[interceptor]:
                    applied_by_interceptor[interceptor][class_name] = set()

                if method_name:
                    applied_by_interceptor[interceptor][class_name].add(method_name)

    return {
        interceptor: {
            class_name: sorted(methods)
            for class_name, methods in sorted(class_map.items())
        }
        for interceptor, class_map in sorted(applied_by_interceptor.items())
    }


# -----------------------------
# Scan logs
# -----------------------------
def scan_apply_classes(folder):
    applied_classes = []

    for path in get_unique_bct_files(folder):
        with open_log(path) as f:
            for line in f:
                if APPLY_KEY in line:
                    cls = extract_class_from_apply(line)
                    if cls:
                        applied_classes.append(cls)

    return applied_classes
