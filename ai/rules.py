FRAMEWORK_KEYWORDS = [
    "springframework",
    "javax",
    "jakarta",
    "apache",
    "ibm",
    "netty",
    "hibernate"
]

def classify_package(pkg):
    for k in FRAMEWORK_KEYWORDS:
        if k in pkg:
            return "Low"
    if any(x in pkg for x in ["controller", "service", "repo", "dao"]):
        return "High"
    return "Medium"
def assess_risk(pkg: str) -> str:
    if any(k in pkg for k in FRAMEWORK_KEYWORDS):
        return "Low"
    if any(x in pkg for x in ["controller", "service", "repo", "dao"]):
        return "High"
    return "Medium"
