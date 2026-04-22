#!/usr/bin/env python3
"""
Fetch AppDynamics public documentation pages and save them as KB documents
in kb_documents/ so the RAG system can retrieve them for AI-grounded answers.

Usage:
    python3 scripts/fetch_appd_docs.py
    python3 scripts/fetch_appd_docs.py --force    # overwrite existing files
    python3 scripts/fetch_appd_docs.py --dry-run  # preview without writing

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import argparse
import os
import re
import sys
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4 lxml")
    sys.exit(1)

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "kb_documents")
BASE = "https://help.splunk.com/en/appdynamics-saas/application-performance-monitoring/26.4.0"

# (filename, category, tags, url)
APPD_PAGES = [
    ("java_agent_install", "agent-install",
     "java, agent, install, jvm, startup, jar",
     f"{BASE}/install-app-server-agents/java-agent/install-the-java-agent"),

    ("java_agent_config_properties", "agent-config",
     "java, agent, system properties, configuration, appdynamics.controller",
     f"{BASE}/install-app-server-agents/java-agent/java-agent-configuration-properties"),

    ("java_agent_administer", "agent-config",
     "jvm, flags, -javaagent, jvm-args, heap, memory, restart, rolling",
     f"{BASE}/administer-app-server-agents/administer-the-java-agent"),

    ("business_transactions_overview", "bt-guide",
     "business transaction, bt, detection, naming, entry point",
     f"{BASE}/business-transactions"),

    ("business_transaction_discovery", "bt-guide",
     "bt, auto discovery, naming rules, custom match, exclusion",
     f"{BASE}/business-transactions/discover-and-configure-business-transactions"),

    ("business_transaction_management", "bt-guide",
     "bt limit, 200 transactions, overflow, drop, register, lock",
     f"{BASE}/business-transactions/business-transaction-management"),

    ("bct_instrumentation_overview", "bct-guide",
     "bytecode, instrumentation, interceptors, BCT, overhead, applied classes",
     f"{BASE}/configure-instrumentation"),

    ("bct_exclude_packages", "bct-guide",
     "exclude, package, bci-exclude, instrumentation, no interceptor",
     f"{BASE}/configure-instrumentation/exclude-packages-classes-and-methods"),

    ("jvm_monitoring", "jvm-guide",
     "heap, gc, garbage collection, memory, metaspace, oom, out of memory, jvm",
     f"{BASE}/monitor-jvms-and-clrs"),

    ("thread_monitoring", "thread-guide",
     "threads, thread dump, deadlock, blocked, runnable, stuck, waiting",
     f"{BASE}/monitor-jvms-and-clrs/monitor-thread-activity"),

    ("controller_config_properties", "controller-config",
     "controller, network, port, firewall, proxy, ssl, registration, host",
     f"{BASE}/install-app-server-agents/java-agent/java-agent-configuration-properties/controller-configuration-properties"),

    ("transaction_snapshots", "diagnostics",
     "snapshot, call graph, slow transaction, error, diagnostic session",
     f"{BASE}/troubleshoot-business-transaction-performance/transaction-snapshots"),

    ("data_collectors", "diagnostics",
     "data collector, http parameter, method invocation, pojo, session, snapshot",
     f"{BASE}/configure-instrumentation/data-collectors"),

    ("jmx_monitoring", "jmx-guide",
     "jmx, mbean, custom metrics, jmx-service, permission, monitoring",
     f"{BASE}/configure-instrumentation/jmx-monitoring"),

    ("health_rules", "alerting",
     "health rule, policy, alert, action, baseline, threshold, violation",
     f"{BASE}/alert-and-respond/health-rules-and-alerting/health-rules"),

    ("error_detection", "error-resolution",
     "error detection, exception, http error, ignore errors, mark as error",
     f"{BASE}/troubleshoot-business-transaction-performance/error-detection"),

    ("bct_logging", "bct-guide",
     "BCT log, bytecode transformer log, instrumentation log, agent-log, bct_errors",
     f"{BASE}/administer-app-server-agents/agent-log-files/bytecode-transformer-logging"),

    ("agent_log_files", "agent-config",
     "log files, agent log, logging level, debug, log structure, log4j",
     f"{BASE}/administer-app-server-agents/agent-log-files/agent-log-file-information"),

    ("node_properties_reference", "agent-config",
     "node properties, custom properties, javaagent, override, tier, node",
     f"{BASE}/administer-app-server-agents/app-agent-node-properties-reference/app-agent-node-properties-by-type"),

    ("java_agent_upgrade", "agent-install",
     "upgrade, java agent, version, migration, rolling upgrade",
     f"{BASE}/install-app-server-agents/java-agent/upgrade-the-java-agent"),

    ("distributed_tracing_correlation", "bt-guide",
     "distributed tracing, correlation, X-singularityheader, cross-tier, microservices, propagation",
     f"{BASE}/business-transactions/transaction-and-call-graph-snapshots/correlate-business-transactions-and-snapshots"),

    ("database_visibility", "database-agent",
     "database agent, database monitoring, query, slow query, connection pool",
     f"{BASE}/database-visibility"),
]


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["nav", "footer", "script", "style", "aside",
                               "header", "noscript", "iframe", "button",
                               "form", "svg", "img"]):
        tag.decompose()

    content_el = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|main|article|body", re.I))
        or soup.body
    )
    if content_el is None:
        return ""

    for br in content_el.find_all("br"):
        br.replace_with("\n")
    for tag in content_el.find_all(["p", "li", "h1", "h2", "h3", "h4", "dt", "dd", "tr"]):
        tag.insert_before("\n")

    text = content_el.get_text(separator=" ")
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def fetch_page(url: str, timeout: int = 20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout,
                         allow_redirects=True, verify=False)
        if r.status_code == 200:
            return r.text
        print(f"  HTTP {r.status_code} — skipping")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def write_kb_file(filename, category, tags, content, url):
    os.makedirs(KB_DIR, exist_ok=True)
    path = os.path.join(KB_DIR, f"{filename}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# category: {category}\n")
        f.write(f"# tags: {tags}\n")
        f.write(f"# source: {url}\n\n")
        f.write(content)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"KB output: {os.path.abspath(KB_DIR)}\n")

    success = skipped = failed = 0

    for filename, category, tags, url in APPD_PAGES:
        out_path = os.path.join(KB_DIR, f"{filename}.txt")
        print(f"[{filename}]")

        if args.dry_run:
            print(f"  DRY-RUN: {url}")
            continue

        if os.path.exists(out_path) and not args.force:
            print(f"  Already exists — skipping (--force to overwrite)")
            skipped += 1
            continue

        print(f"  Fetching: {url}")
        html = fetch_page(url)
        if html is None:
            failed += 1
            continue

        content = clean_html(html)
        if len(content) < 200:
            print(f"  Too short ({len(content)} chars) — page may need login, skipping")
            failed += 1
            continue

        path = write_kb_file(filename, category, tags, content, url)
        print(f"  Saved: {path} ({len(content):,} chars)")
        success += 1
        time.sleep(0.4)

    print(f"\nDone. Fetched={success}  Skipped={skipped}  Failed={failed}")

    if success > 0:
        db_path = os.path.join(os.path.dirname(__file__), "..", "kb_data", "documents.json")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("Cleared vector DB cache — will re-seed on next app start.")


if __name__ == "__main__":
    main()
