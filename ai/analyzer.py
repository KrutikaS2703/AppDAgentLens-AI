'''
#### Rule-based/Heurisric Approch ####

def explain_package(pkg, class_count, risk):
    explanation = (
        f"This package has {class_count} classes with no interceptors applied. "
        f"It appears to be {'framework' if risk == 'Low' else 'application'} code."
    )

    impact = (
        "Excluding this package will reduce bytecode instrumentation overhead. "
        "No business transaction impact is expected."
        if risk == "Low"
        else
        "Excluding this package may affect visibility of application logic."
    )

    return {
        "risk": risk,
        "explanation": explanation,
        "impact": impact
    }
'''
### LLM reasoning approach ###

import json
from typing import Optional

from ai.llm import ask_llm


FRAMEWORK_PREFIXES = [
    ("Spring Boot", ["org.springframework.boot"]),
    ("Spring Framework", ["org.springframework"]),
    ("Spring WebFlux", ["org.springframework.web", "org.springframework.web.reactive", "org.springframework.webflux"]),
    ("Spring Cloud Gateway", ["org.springframework.cloud"]),
    ("Spring Kafka", ["org.springframework.kafka"]),
    ("Spring Integration", ["org.springframework.integration"]),
    ("Spring WS", ["org.springframework.ws"]),
    ("Spring AMQP / RabbitMQ", ["org.springframework.amqp"]),
    ("Jakarta EE", ["jakarta.servlet", "jakarta.ws.rs", "jakarta.jms", "jakarta.ejb", "jakarta.persistence", "jakarta"]),
    ("Javax / Java EE", ["javax.servlet", "javax.ws.rs", "javax.jms", "javax.ejb", "javax.persistence", "javax"]),
    ("Hibernate", ["org.hibernate"]),
    ("Apache Kafka", ["org.apache.kafka"]),
    ("Apache CXF", ["org.apache.cxf"]),
    ("Apache Camel", ["org.apache.camel"]),
    ("Apache Struts", ["org.apache.struts"]),
    ("Apache Tapestry", ["org.apache.tapestry"]),
    ("Apache Wicket", ["org.apache.wicket"]),
    ("Netty", ["io.netty"]),
    ("Reactor", ["reactor.core", "reactor.netty"]),
    ("gRPC", ["io.grpc"]),
    ("Micronaut", ["io.micronaut"]),
    ("Quarkus", ["io.quarkus"]),
    ("Dropwizard", ["io.dropwizard"]),
    ("Vert.x", ["io.vertx"]),
    ("MyBatis", ["org.mybatis"]),
    ("Jersey", ["org.glassfish.jersey", "com.sun.jersey"]),
    ("JAX-RS", ["javax.ws.rs", "jakarta.ws.rs"]),
    ("Servlet API", ["javax.servlet", "jakarta.servlet"]),
    ("JSF", ["javax.faces", "jakarta.faces"]),
    ("JSP", ["javax.servlet.jsp", "jakarta.servlet.jsp"]),
    ("RabbitMQ Java Client", ["com.rabbitmq"]),
    ("Akka", ["akka"]),
    ("Ktor", ["io.ktor"]),
    ("Play Framework", ["play"]),
    ("Http4s", ["org.http4s"]),
    ("Grails", ["grails"]),
    ("Mule ESB", ["org.mule"]),
    ("WebLogic", ["weblogic"]),
    ("WebSphere", ["com.ibm.ws", "com.ibm.websphere"]),
    ("JBoss / WildFly", ["org.jboss", "org.wildfly"]),
    ("Tomcat", ["org.apache.catalina", "org.apache.tomcat"]),
    ("Jetty", ["org.eclipse.jetty"]),
]


FRAMEWORK_SUPPORT = {
    "Akka": {"versions": "2.1 to 2.5.x", "hint": "Supported; Akka HTTP has separate support notes."},
    "Apache CXF": {"versions": "2.1", "hint": "Supported for JAX-WS; SOAP header correlation may require a node property."},
    "Apache Kafka": {"versions": "0.9.0.0 to 3.0.0", "hint": "Supported; Kafka consumer entry points are disabled by default."},
    "Apache Struts": {"versions": "1.x, 2.x", "hint": "Supported; Struts actions are detected as entry points."},
    "Grails": {"versions": "Supported", "hint": "Supported, but some setups are not enabled by default."},
    "gRPC": {"versions": "1.6.x to 1.42.x", "hint": "Supported for asynchronous RPC instrumentation."},
    "Http4s": {"versions": "Blaze 0.20.5, 0.20.23, 0.21.0, 0.21.1", "hint": "Supported for Blaze client."},
    "Hibernate": {"versions": "Supported", "hint": "Hibernate support exists; additional Hibernate JMS listener support is also listed."},
    "JAX-RS": {"versions": "3.0+", "hint": "Supported with configuration caveats for some REST naming/correlation behaviors."},
    "JBoss / WildFly": {"versions": "WildFly 4.x to 32.x; JBoss EAP 7.1.5, 7.2.0, 7.3.0, 7.4.0, 8.0", "hint": "Supported; some web service scenarios require servlet exclude rules."},
    "Jersey": {"versions": "1.x, 2.x", "hint": "Supported; JAX-RS naming often uses node properties such as rest-uri controls."},
    "Jetty": {"versions": "6.x, 7.x, 8.x, 9.x, 12", "hint": "Supported as application server and HTTP client runtime."},
    "JSF": {"versions": "1.x, 2.x", "hint": "Supported."},
    "JSP": {"versions": "2.x", "hint": "Supported."},
    "Javax / Java EE": {"versions": "Supported on listed Java EE APIs", "hint": "Support depends on specific API or framework in use."},
    "Jakarta EE": {"versions": "Supported on listed Jakarta APIs", "hint": "Support depends on specific API or framework in use."},
    "Ktor": {"versions": "1.0.x to 1.6.x", "hint": "Supported with Netty engine notes."},
    "Micronaut": {"versions": "4.0.x to 4.6.x", "hint": "Supported by Java Agent and OpenTelemetry support matrix."},
    "Mule ESB": {"versions": "3.4, 3.6, 3.7, 3.8, 3.9, 4.1.x, 4.2.x, 4.3.0, 4.4.0, 4.5.x, 4.6.x, 4.7.x, 4.10.x", "hint": "Supported for HTTP and JMS scenarios."},
    "MyBatis": {"versions": "Not explicitly listed in current summary", "hint": "May require custom instrumentation depending on entry/exit pattern."},
    "Netty": {"versions": "3.x, 4.x", "hint": "Supported by default; node property netty-enabled controls instrumentation."},
    "Play Framework": {"versions": "2.1 to 2.8", "hint": "Supported for Play for Java and Scala."},
    "Quarkus": {"versions": "RESTEasy Classic 3.15+; Rest Client 3.15", "hint": "Supported with Quarkus-specific configuration notes in some cases."},
    "RabbitMQ Java Client": {"versions": "Supported", "hint": "RabbitMQ backend detection is supported; Spring client has separate support entry."},
    "Reactor": {"versions": "Covered via Spring WebFlux / Reactor Netty support", "hint": "Usually relevant through WebFlux and WebClient instrumentation."},
    "Servlet API": {"versions": "2.x, 3.0", "hint": "Supported in support matrix; note Servlet 3.x detection caveat in app server docs."},
    "Spring AMQP / RabbitMQ": {"versions": "Supported", "hint": "RabbitMQ Spring client and AMQP-related support are documented."},
    "Spring Boot": {"versions": "2.x, 3.x", "hint": "Supported by Java Agent and OpenTelemetry support matrix."},
    "Spring Cloud Gateway": {"versions": "2.0.x, 2.1.x, 2.2.x, 3.0.x, 3.1.x", "hint": "Supported by default."},
    "Spring Framework": {"versions": "Supported across multiple modules", "hint": "General Spring support exists; module-specific versions vary."},
    "Spring Integration": {"versions": "2.2.0+, 4.0+, 5.2, 5.3", "hint": "Supported for JMS/integration flows."},
    "Spring Kafka": {"versions": "3.1.3", "hint": "Supported without custom interceptors."},
    "Spring WebFlux": {"versions": "5.0, 5.1, 5.2, 5.3", "hint": "Supported by default; WebClient note applies."},
    "Spring WS": {"versions": "3.x, 4.x, 5.x", "hint": "Supported for HTTP/SOAP with SOAP correlation note."},
    "Tomcat": {"versions": "5.x, 6.x, 7.x, 8.x, 9, 10", "hint": "Supported application server."},
    "Vert.x": {"versions": "3.3.3 to 4.5.x", "hint": "Supported including Vert.x core and event bus coverage."},
    "WebLogic": {"versions": "9.x+", "hint": "Supported; several RPC/JMS/web service modes are also documented."},
    "WebSphere": {"versions": "6.1, 7.x, 8.x, 9.x", "hint": "Supported; JAX-WS and PMI coverage have specific notes."},
}


def get_framework_support_summary(framework_name: str) -> str:
    info = FRAMEWORK_SUPPORT.get(framework_name)
    if not info:
        return "Check AppD support matrix; custom rules may be required"

    versions = info.get("versions", "Supported")
    hint = info.get("hint", "")
    if hint:
        return f"{versions} | {hint}"
    return versions


def _normalize_class_name(class_name: str) -> str:
    """Normalize Java class names from logs to dot-separated FQCN format."""
    normalized = (class_name or "").strip()
    if not normalized:
        return ""

    # Handle JVM descriptor style names like Lorg/springframework/Context;
    if normalized.startswith("L") and normalized.endswith(";"):
        normalized = normalized[1:-1]

    # BCT logs commonly emit slash-separated class names.
    normalized = normalized.replace("/", ".")

    # Drop inner class suffix for package/framework inference.
    normalized = normalized.split("$", 1)[0]

    return normalized


def detect_frameworks_used(class_names: list[str]) -> list[dict]:
    """Infer likely frameworks from scanned class package prefixes."""
    class_candidates = []

    for class_name in class_names or []:
        normalized_class_name = _normalize_class_name(class_name)
        if not normalized_class_name or "." not in normalized_class_name:
            continue

        package_name = normalized_class_name.rsplit(".", 1)[0].strip().lower()
        if not package_name:
            continue

        parts = [part for part in package_name.split(".") if part]
        if len(parts) < 2:
            continue

        candidate_prefixes = set()
        candidate_prefixes.add(".".join(parts[:2]))
        if len(parts) >= 3:
            candidate_prefixes.add(".".join(parts[:3]))

        class_candidates.append({
            "class_name": normalized_class_name,
            "prefixes": candidate_prefixes,
        })

    detected = []
    for framework_name, known_prefixes in FRAMEWORK_PREFIXES:
        matched_prefixes = set()
        matched_classes = set()

        for item in class_candidates:
            item_prefixes = item["prefixes"]
            matched_item_prefixes = {
                observed_prefix
                for observed_prefix in item_prefixes
                if any(
                    observed_prefix == known_prefix or observed_prefix.startswith(f"{known_prefix}.")
                    for known_prefix in known_prefixes
                )
            }
            if matched_item_prefixes:
                matched_classes.add(item["class_name"])
                matched_prefixes.update(matched_item_prefixes)

        if matched_classes:
            detected.append({
                "framework": framework_name,
                "matching_prefixes": sorted(matched_prefixes),
                "class_count": len(matched_classes),
                "support_summary": get_framework_support_summary(framework_name),
            })

    detected.sort(key=lambda item: (-item["class_count"], item["framework"].lower()))
    return detected


def analyze_potential_issues(logger_issues: list, level_filter: Optional[str] = None) -> list:
    """
    Match logger names found in ERROR / WARN lines against the logger KB and
    return a structured list of potential issues.

    Each returned item:
        {
          "logger"      : str,
          "level"       : str,          # ERROR | WARN
          "category"    : str,
          "issues"      : list[str],
          "description" : str,
          "remediation" : str,
          "latest_line" : str,          # full log line from latest file
          "timestamp"   : str,
          "file_name"   : str,
          "occurrences" : int,
        }
    """
    from ai.logger_kb import LOGGER_ISSUE_KB

    results = []
    seen_categories: set = set()

    normalized_filter = (level_filter or "").strip().upper()

    for item in logger_issues or []:
        level = (item.get("level") or "").upper()
        if normalized_filter and level != normalized_filter:
            continue

        logger = item.get("logger", "")
        kb_entry = LOGGER_ISSUE_KB.get(logger)
        if not kb_entry:
            continue

        category = kb_entry["category"]
        # Deduplicate: if a category is already represented by an ERROR entry,
        # skip a WARN entry for the same category.
        dedup_key = (logger, category, level)
        if dedup_key in seen_categories:
            continue
        seen_categories.add(dedup_key)

        results.append({
            "logger":       logger,
            "level":        level,
            "category":     category,
            "issues":       kb_entry.get("issues", []),
            "description":  kb_entry.get("description", ""),
            "remediation":  kb_entry.get("remediation", ""),
            "latest_line":  item.get("latest_line", ""),
            "timestamp":    item.get("timestamp", ""),
            "file_name":    item.get("file_name", ""),
            "occurrences":  item.get("occurrences", 0),
        })

    # Sort: ERROR before WARN, then by occurrences descending
    results.sort(key=lambda x: (0 if x["level"] == "ERROR" else 1, -x["occurrences"]))
    return results


def llm_analyze_issue(item: dict) -> str:
    """
    Analyze one KB-matched logger issue with LLM context.
    Falls back to a KB-based response when AI is unavailable or too weak.
    """
    issues = item.get("issues", []) or []
    issues_text = "\n".join(f"- {x}" for x in issues)
    logger = item.get("logger", "UnknownLogger")
    level = item.get("level", "UNKNOWN")
    category = item.get("category", "Unknown Category")
    occurrences = item.get("occurrences", 0)
    description = item.get("description", "")
    remediation = item.get("remediation", "")
    latest_line = item.get("latest_line", "")
    file_name = item.get("file_name", "")
    timestamp = item.get("timestamp", "")

    prompt = f"""
You are an AppDynamics Java Agent troubleshooting expert.

Analyze the following logger issue from production logs.

Logger: {logger}
Level: {level}
Category: {category}
Occurrences: {occurrences}

Known issue hints from KB:
{issues_text}

KB context:
Description: {description}
Remediation: {remediation}

Latest matching line:
File: {file_name}
Timestamp: {timestamp}
Line: {latest_line}

Return concise markdown with exactly these sections:
1) Likely Issue
2) Why This Is Happening
3) Immediate Next Checks
4) Suggested Fix

Ground your answer in the latest log line and do not speculate beyond the evidence.
"""

    raw = (ask_llm(prompt) or "").strip()

    # If provider is unavailable or answer quality is weak, use deterministic KB fallback.
    weak_ai = (
        not raw
        or raw.lower().startswith("ai unavailable")
        or len(raw) < 80
        or "i don't know" in raw.lower()
        or "cannot determine" in raw.lower()
    )
    if not weak_ai:
        return raw

    likely_issue = ", ".join(issues[:2]) if issues else category
    return (
        f"**Likely Issue**\n"
        f"{likely_issue}\n\n"
        f"**Why This Is Happening**\n"
        f"Logger `{logger}` emitted a {level} event in `{file_name}` at `{timestamp}`. "
        f"This pattern maps to **{category}** in the logger KB.\n\n"
        f"**Immediate Next Checks**\n"
        f"1. Verify connectivity/configuration linked to this logger category.\n"
        f"2. Inspect surrounding lines near the latest event for root cause markers (timeouts, auth, SSL, queue/full).\n"
        f"3. Confirm occurrence trend ({occurrences}) to determine if issue is persistent.\n\n"
        f"**Suggested Fix**\n"
        f"{remediation or 'Apply logger KB remediation and validate with a fresh scan.'}"
    )


def explain_package(pkg: str, class_count: int, risk: str) -> dict:
    prompt = f"""
You are an AppDynamics Java Agent expert.

Analyze whether excluding this package from bytecode instrumentation is safe.

Package: {pkg}
Classes count: {class_count}
Precomputed risk level: {risk}

Respond in this exact JSON format:
{{
  "risk": "<LOW|MEDIUM|HIGH>",
  "explanation": "<why it is safe or unsafe>",
  "impact": "<performance or visibility impact>"
}}
"""

    raw = ask_llm(prompt)
    raw_text = (raw or "").strip()

    # Provider or connectivity issue: return a clear fallback.
    if not raw_text or raw_text.lower().startswith("ai unavailable"):
        return {
            "risk": risk,
            "explanation": "AI analysis unavailable: provider returned an error or empty response.",
            "impact": "Could not generate impact analysis"
        }

    # Try to parse JSON from the full response first, then from the first JSON-like block.
    try:
        parsed = json.loads(raw_text)
    except Exception:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {
                "risk": risk,
                "explanation": "AI analysis unavailable: model did not return JSON in the expected format.",
                "impact": "Could not generate impact analysis"
            }
        try:
            parsed = json.loads(raw_text[start:end + 1])
        except Exception:
            return {
                "risk": risk,
                "explanation": "AI analysis unavailable: model returned malformed JSON.",
                "impact": "Could not generate impact analysis"
            }

    return {
        "risk": parsed.get("risk", risk),
        "explanation": parsed.get("explanation", "No explanation available"),
        "impact": parsed.get("impact", "No impact analysis available")
    }
