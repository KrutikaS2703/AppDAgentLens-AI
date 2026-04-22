# core/bct/scanner.py

from core.bct.apply_interceptor import scan_apply_classes, scan_applied_by_interceptor
from core.bct.exclude_package import (
    derive_excludable_packages_with_counts,
    suggest_exclusion_packages,
    prune_redundant_packages,
    to_bci_exclude_format,
)
from core.bct.interceptors_count import scan_interceptor_counts
from core.bct.match_class import scan_match_classes
from core.bct.method_excluded import (
    scan_excluded_methods,
    get_excluded_methods_by_interceptor,
    get_excluded_methods_by_prefix,
    get_excluded_methods_by_limit,
    get_unique_classes_with_methods,
)
from core.bct.no_interceptor_classes import scan_classes_without_interceptors


def run_bct_analysis(log_path: str) -> dict:
    """
    Runs full BCT analysis and returns structured results
    """

    result = {}

    # 1️⃣ Matched classes
    matched = scan_match_classes(log_path)
    result["matched_classes"] = matched
    result["matched_count"] = len(matched)

    # 2️⃣ Applied interceptors
    applied = scan_apply_classes(log_path)
    result["applied_classes"] = applied
    result["applied_count"] = len(applied)
    result["applied_by_interceptor"] = scan_applied_by_interceptor(log_path)

    # 3️⃣ Interceptor counts
    interceptor_counts = scan_interceptor_counts(log_path)
    result["interceptor_counts"] = interceptor_counts
    result["unique_interceptors"] = len(interceptor_counts)

    # 4️⃣ No interceptor classes
    no_interceptors = scan_classes_without_interceptors(log_path)
    result["no_interceptor_classes"] = no_interceptors
    result["no_interceptor_count"] = len(no_interceptors)

    # 4️⃣.5️⃣ Method excluded warnings
    excluded_methods = scan_excluded_methods(log_path)
    result["excluded_methods"] = [m.to_dict() for m in excluded_methods]
    result["excluded_methods_objects"] = excluded_methods  # Keep objects for later use
    result["excluded_count"] = len(excluded_methods)
    result["unique_excluded_classes"] = get_unique_classes_with_methods(excluded_methods)
    result["excluded_by_interceptor"] = {
        k: [m.to_dict() for m in v]
        for k, v in get_excluded_methods_by_interceptor(excluded_methods).items()
    }
    result["excluded_by_prefix"] = {
        k: [m.to_dict() for m in v]
        for k, v in get_excluded_methods_by_prefix(excluded_methods).items()
    }
    result["excluded_by_limit"] = {
        k: [m.to_dict() for m in v]
        for k, v in get_excluded_methods_by_limit(excluded_methods).items()
    }

    # 5️⃣ Exclusion suggestions (package-level)
    candidates = suggest_exclusion_packages(no_interceptors)
    final_pkgs = prune_redundant_packages(candidates)

    result["exclusion_suggestions"] = final_pkgs

    # 6️⃣ BCI Exclude derivation
    packages = derive_excludable_packages_with_counts(no_interceptors, applied)
    result["excludable_packages"] = packages
    result["bci_exclude_config"] = to_bci_exclude_format(packages)
    bci_exclude_lines = result["bci_exclude_config"]
    return result
