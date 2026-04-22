# core/no_interceptor_classes.py
from core.bct.match_class import scan_match_classes
from core.bct.apply_interceptor import scan_apply_classes

def scan_classes_without_interceptors(log_path):
    """
    Returns a sorted list of classes which don't have any interceptors applied.
    """
    # All matched classes
    matched_classes = scan_match_classes(log_path)

    # All classes where interceptors are applied
    applied_classes = scan_apply_classes(log_path)

    # Classes with no interceptors applied
    no_interceptor = sorted(set(matched_classes) - set(applied_classes))
    
    return no_interceptor
