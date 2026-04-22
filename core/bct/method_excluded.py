#!/usr/bin/env python3
import re
from core.bct.files import get_unique_bct_files, open_log

METHOD_EXCLUDED_KEY = "Method excluded because"


# Data structure for excluded method info
class ExcludedMethod:
    def __init__(self, class_name, interceptor, prefix=None, transformation_limit=None, method_name=None):
        self.class_name = class_name
        self.interceptor = interceptor
        self.prefix = prefix
        self.transformation_limit = transformation_limit
        self.method_name = method_name

    def __repr__(self):
        return (
            f"ExcludedMethod(class={self.class_name}, "
            f"method={self.method_name}, "
            f"interceptor={self.interceptor}, "
            f"prefix={self.prefix}, "
            f"limit={self.transformation_limit})"
        )

    def to_dict(self):
        return {
            "class": self.class_name,
            "interceptor": self.interceptor,
            "prefix": self.prefix or "N/A",
            "transformation_limit": self.transformation_limit or "N/A",
        }


def extract_method_name_from_class(class_name):
    """
    Extract method name from class name if it contains synthetic method markers.
    Example: IAssessmentOrderOutpost$$$view255 -> view255
    """
    if "$$$" in class_name:
        return class_name.split("$$$")[-1]
    elif "$" in class_name:
        return class_name.split("$")[-1]
    return None


# Pattern 1: Cannot instrument class ... for interceptor class ... because maximum X transformations exceeded for package prefix ...
# Example: Cannot instrument class be/sofico/outpost/sess/assessmentorder/IAssessmentOrderOutpost$$$view255 for interceptor class com.singularity.ee.agent.appagent.services.transactionmonitor.ejb.EJBInterceptor because maximum 200 transformations exceeded for package prefix be.sofico

PATTERN_1 = re.compile(
    r"Cannot instrument class\s+(\S+)"  # class name
    r"\s+for interceptor class\s+(\S+)"  # interceptor
    r"\s+because maximum\s+(\d+)\s+transformations exceeded"  # limit
    r"\s+for package prefix\s+(\S+)"  # prefix
)

# Pattern 2: Max transformations X reached for interceptor Y when loading class Z
# Example: Method excluded because Max transformations 500 reached for interceptor entry.SepDiscovery when loading class be/sofico/outpost/sess/assessmentorder/IAssessmentOrderOutpost$$$view255

PATTERN_2 = re.compile(
    r"Max transformations\s+(\d+)\s+reached"  # limit
    r"\s+for interceptor\s+(\S+)"  # interceptor
    r"\s+when loading class\s+(\S+)"  # class name
)


def extract_excluded_method(line):
    """
    Extract excluded method information from a log line.
    Supports both patterns of method exclusion.
    
    Args:
        line: A line from BCT log that contains "Method excluded..."
        
    Returns:
        ExcludedMethod object if match found, None otherwise
    """
    try:
        # Try Pattern 1 first
        match = PATTERN_1.search(line)
        if match:
            class_name = match.group(1)
            interceptor = match.group(2)
            transformation_limit = int(match.group(3))
            prefix = match.group(4)
            method_name = extract_method_name_from_class(class_name)

            return ExcludedMethod(
                class_name=class_name,
                interceptor=interceptor,
                prefix=prefix,
                transformation_limit=transformation_limit,
                method_name=method_name
            )
        
        # Try Pattern 2
        match = PATTERN_2.search(line)
        if match:
            transformation_limit = int(match.group(1))
            interceptor = match.group(2)
            class_name = match.group(3)
            method_name = extract_method_name_from_class(class_name)

            return ExcludedMethod(
                class_name=class_name,
                interceptor=interceptor,
                transformation_limit=transformation_limit,
                method_name=method_name
            )
    except Exception as e:
        print(f"Error parsing excluded method: {e}")

    return None


def scan_excluded_methods(folder):
    """
    Scan BCT logs for all "Method excluded" warnings.
    
    Args:
        folder: Path to folder containing BCT log files
        
    Returns:
        List of ExcludedMethod objects
    """
    excluded_methods = []

    for path in get_unique_bct_files(folder):
        with open_log(path) as f:
            for line in f:
                if METHOD_EXCLUDED_KEY in line:
                    excluded = extract_excluded_method(line)
                    if excluded:
                        excluded_methods.append(excluded)

    return excluded_methods


def get_excluded_methods_by_interceptor(excluded_methods):
    """
    Group excluded methods by interceptor.
    
    Args:
        excluded_methods: List of ExcludedMethod objects
        
    Returns:
        Dictionary with interceptor as key and list of ExcludedMethod as value
    """
    result = {}
    for method in excluded_methods:
        if method.interceptor not in result:
            result[method.interceptor] = []
        result[method.interceptor].append(method)
    return result


def get_excluded_methods_by_prefix(excluded_methods):
    """
    Group excluded methods by package prefix.
    
    Args:
        excluded_methods: List of ExcludedMethod objects
        
    Returns:
        Dictionary with prefix as key and list of ExcludedMethod as value
    """
    result = {}
    for method in excluded_methods:
        if method.prefix not in result:
            result[method.prefix] = []
        result[method.prefix].append(method)
    return result


def get_excluded_methods_by_limit(excluded_methods):
    """
    Group excluded methods by transformation limit.
    
    Args:
        excluded_methods: List of ExcludedMethod objects
        
    Returns:
        Dictionary with limit as key and list of ExcludedMethod as value
    """
    result = {}
    for method in excluded_methods:
        limit = method.transformation_limit
        if limit not in result:
            result[limit] = []
        result[limit].append(method)
    return result


def get_unique_classes_with_methods(excluded_methods):
    """
    Get unique classes and their methods that were excluded.
    
    Args:
        excluded_methods: List of ExcludedMethod objects
        
    Returns:
        Dictionary with class_name as key and list of methods as value
    """
    result = {}
    for method in excluded_methods:
        if method.class_name not in result:
            result[method.class_name] = {
                "methods": set(),
                "interceptors": set(),
                "transformation_limits": set()
            }
        
        if method.method_name:
            result[method.class_name]["methods"].add(method.method_name)
        result[method.class_name]["interceptors"].add(method.interceptor)
        if method.transformation_limit:
            result[method.class_name]["transformation_limits"].add(method.transformation_limit)
    
    # Convert sets to lists for serialization
    final_result = {}
    for cls, data in result.items():
        final_result[cls] = {
            "methods": sorted(list(data["methods"])),
            "interceptors": sorted(list(data["interceptors"])),
            "transformation_limits": sorted(list(data["transformation_limits"]))
        }
    
    return final_result


def get_methods_for_class(excluded_methods, class_name):
    """
    Get all methods and details for a specific class.
    
    Args:
        excluded_methods: List of ExcludedMethod objects
        class_name: The class name to filter by
        
    Returns:
        List of ExcludedMethod objects for that class
    """
    return [m for m in excluded_methods if m.class_name == class_name]

