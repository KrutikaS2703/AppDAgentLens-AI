from typing import List, Dict, Optional
from collections import Counter

def optimize_packages(packages):
    """
    Remove child packages if a parent package already exists.
    Example:
      com/google/zxing/
      com/google/zxing/common/
    → keep only com/google/zxing/
    """
    packages = sorted(packages)  # lexicographic sort
    optimized = []

    for pkg in packages:
        if not any(pkg.startswith(parent) for parent in optimized):
            optimized.append(pkg)

    return optimized


def derive_excludable_packages_with_counts(no_interceptor_classes, applied_classes):

    if callable(no_interceptor_classes):
        raise TypeError(
            "scan_classes_without_interceptors() was not called. "
            "Pass its RESULT, not the function."
        )

    no_set = set(no_interceptor_classes)
    applied_set = set(applied_classes)
    
    pkg_to_classes = {}

    for cls in no_set:
        parts = cls.split("/")
        for depth in range(2, len(parts)):
            pkg = "/".join(parts[:depth]) + "/"
            pkg_to_classes.setdefault(pkg, set()).add(cls)

    eligible = {}

    for pkg, classes in pkg_to_classes.items():
        # Skip if any interceptor-applied class exists under this pkg
        if any(c.startswith(pkg) for c in applied_set):
            continue

        eligible[pkg] = len(classes)

    # Remove redundant child packages
    final = {}
    for pkg in sorted(eligible, key=lambda x: x.count("/")):
        if not any(pkg.startswith(parent) for parent in final):
            final[pkg] = eligible[pkg]

    return final  # {pkg: class_count}


def to_bci_exclude_format(packages: List[str]) -> List[str]:
    return [
        f'<custom-exclude filter-type="STARTSWITH" filter-value="{pkg}"/>'
        for pkg in packages
    ]

def prune_redundant_packages(pkg_counts):
    """
    Removes child packages if a parent package already exists.
    Example:
      com/ibm/ exists → drop com/ibm/ws/
    """
    pruned = {}
    accepted = []

    for pkg in sorted(pkg_counts.keys(), key=len):
        if any(pkg.startswith(parent) for parent in accepted):
            continue
        accepted.append(pkg)
        pruned[pkg] = pkg_counts[pkg]

    return pruned

def extract_package(class_name: str, depth: int) -> Optional[str]:
    """
    Extracts package up to given depth.
    Example:
      depth=3 → org/springframework/web/
      depth=4 → org/springframework/web/servlet/
    """
    if "/" not in class_name:
        return None

    # Strip proxy / inner class suffix
    base = class_name.split("$", 1)[0]
    parts = base.split("/")

    if len(parts) <= depth:
        return None

    return "/".join(parts[:depth]) + "/"


def suggest_exclusion_packages(
    classes: List[str],
    min_hits: int = 10,
    max_depth: int = 6
) -> Dict[str, int]:
    """
    Returns package → count mapping for exclusion candidates.
    """
    counter = Counter()

    for cls in classes:
        for depth in range(2, max_depth + 1):
            pkg = extract_package(cls, depth)
            if pkg:
                counter[pkg] += 1

    return {
        pkg: count
        for pkg, count in counter.items()
        if count >= min_hits
    }
