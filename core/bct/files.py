#!/usr/bin/env python3
import gzip
import os
def get_unique_bct_files(folder):
    """
    Return list of BCT log files, preferring .log over .log.gz
    """
    files = {}

    for fname in os.listdir(folder):
        if not fname.startswith("ByteCode"):
            continue

        if fname.endswith(".log.gz"):
            base = fname[:-3]  # remove .gz
            files.setdefault(base, fname)

        elif fname.endswith(".log"):
            files[fname] = fname  # prefer unzipped

    return [os.path.join(folder, f) for f in files.values()]


# -----------------------------
# File handling
# -----------------------------
def open_log(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="ignore")
    return open(path, "r", errors="ignore")

