"""
Logger Issue Knowledge Base
Maps AppDynamics Java Agent logger class names to known issue categories,
descriptions, and remediation hints used by AI Potential Issues analysis.
"""

LOGGER_ISSUE_KB = {
    # ── Controller Connectivity ──────────────────────────────────────────────
    "ConfigurationChannel": {
        "category": "Controller Connectivity",
        "issues": [
            "Agent not reporting to controller",
            "Network / connectivity issues",
            "Controller registration failure",
        ],
        "description": (
            "ConfigurationChannel maintains the persistent connection from the "
            "agent to the AppDynamics Controller. Errors here indicate "
            "registration failures, network timeouts, or SSL/TLS issues "
            "preventing the agent from reporting data."
        ),
        "remediation": (
            "Check controller host/port, firewall rules, SSL certificate "
            "validity, and proxy configuration in controller-info.xml."
        ),
    },
   

    # ── Metrics Not Reporting ────────────────────────────────────────────────
    "MetricSender": {
        "category": "Metrics Reporting & Communication",
        "issues": [
            "Metric send failed",
            "Controller connection timeout",
            "Metric queue overflow",
            "Invalid metric data"
        ],
        "description": (
            "Handles the transmission of collected metrics and performance data to the AppDynamics "
            "controller. Manages metric batching, buffering, and retry logic."
        ),
        "remediation": (
            "Verify controller connectivity (host, port, network), check metric queue buffer settings, "
            "enable retry logic and backoff configuration, review controller response for errors, "
            "and validate metric data format matches controller schema."
        ),
    },
   

    # ── Snapshots / Call Graphs ──────────────────────────────────────────────
    "ASnapshotCountTracker": {
        "category": "Transaction Snapshot Management",
        "issues": [
            "Snapshot count exceeded limit",
            "Snapshot buffer overflow",
            "Snapshot dropped/truncated",
            "Max snapshot limit reached"
        ],
        "description": (
            "Tracks the count and lifecycle of transaction snapshots collected during the "
            "monitoring period. Manages snapshot buffering, limits, and throttling to prevent "
            "resource exhaustion."
        ),
        "remediation": (
            "Review snapshot collection configuration and rate limits, increase snapshot buffer "
            "capacity if needed, reduce transaction sampling rate or snapshot detail level, check "
            "controller snapshot handling settings, and verify snapshot data is being flushed "
            "to controller regularly."
        ),
    },
    "RequestSegmentDataQueue": {
        "category": "Transaction Data Buffering & Transmission",
        "issues": [
            "Segment queue overflow",
            "Segment data dropped",
            "Queue flush timeout",
            "Segment transmission failed"
        ],
        "description": (
            "Manages the buffered queue of transaction request segment data (method calls, "
            "service calls, database queries) waiting to be transmitted to the controller. "
            "Handles queue overflow scenarios and batch transmission."
        ),
        "remediation": (
            "Increase segment data queue buffer size, reduce transaction sampling rate, verify "
            "controller connectivity for reliable segment transmission, check network bandwidth "
            "and latency, enable batch compression if available, and review queue flush/timeout "
            "settings."
        ),
    },


    # ── JMX Metrics ─────────────────────────────────────────────────────────
    "JMXMetricReporter": {
        "category": "JMX Metric Collection",
        "issues": ["JMX metrics not collected", "MBean discovery failure"],
        "description": (
            "Collects JMX MBean metrics from the JVM. Errors indicate "
            "MBean discovery failures or access issues."
        ),
        "remediation": (
            "Check jmx-appserver-mbean-finder-delay-in-seconds, verify "
            "MBean names, and confirm JMX permissions."
        ),
    },
    "DefaultJMXAttributeMetricReporter": {
        "category": "JVM Metrics & JMX Monitoring",
        "issues": [
            "JMX attribute not found",
            "MBean connection failed",
            "Metric collection timeout",
            "JMX parsing error",
    
        ],
        "description": (
            "Collects and reports JVM metrics via JMX (Java Management Extensions), including "
            "memory usage, garbage collection, thread counts, and custom MBean attributes. "
            "Aggregates JMX data for transmission to the controller."
        ),
        "remediation": (
            "Verify JMX is enabled in JVM startup (-Dcom.sun.management.jmxremote), check MBean "
            "availability and naming, ensure DISABLE_JVM_JMX_METRIC_REPORTING property is not set to true, "
            "validate JMX connection security settings, review JMX attribute filters/rules, and check "
            "agent logs for MBean lookup errors or timeout issues."
        ),
    },



    # ── Backend Detection ────────────────────────────────────────────────────
        "AFastTrackedMethodInterceptor": {
        "category": "Transaction Exit Tracking",
        "issues": [
            "Exit call not tracked",
            "Backend not linked to transaction",
            "Correlation header not propagated",
            "noTxDetect=true for outbound call"
        ],
        "description": (
            "Tracks fast-path method interceptors for outbound/exit calls and "
            "associates them with the active business transaction context."
        ),
        "remediation": (
            "Verify a BT is active before the exit call, ensure interceptor "
            "registration/match rules are correct, and validate correlation header "
            "generation settings (cross-app/cross-tier correlation enabled)."
        ),
    },
    "ExitCallRegistry": {
        "category": "Backend Detection & Registration",
        "issues": [
            "Backend detection failed",
            "Duplicate backend entries",
            "Exit point not registered",
            "Registry lookup timeout"
        ],
        "description": (
            "Manages the registry of detected external backends (databases, HTTP services, "
            "message queues, caches, etc.). Tracks backend identification, correlation, and metadata."
        ),
        "remediation": (
            "Check backend detection rules configuration, verify exit point matchers are defined, "
            "ensure backend correlation is enabled in the controller, and review agent logs for "
            "blocked/skipped backend detection patterns."
        ),
    },


    # ── Neutralization ────────────────────────────────────────────────────────────
    "AgentErrorProcessor": {
        "category": "Reflection / Instrumentation Errors",
        "issues": [
            "Visibility issues in the controller",
            "Business Transaction detection failure",
        ],
        "description": (
            "Handles errors and issues related to agent operations."
        ),
        "remediation": (
            "May add node property error-safety-rule-error-threshold=-1 to disable neutralization of instrumentation points."

        ),
    },
    "ReflectionUtility": {
        "category": "Class Instrumentation & Reflection",
        "issues": [
            "Reflection access failed",
            "Method not found",
            "Class not accessible",
            "Instrumentation hook not invoked"
        ],
        "description": (
            "Provides reflection-based utilities for dynamic class introspection, method invocation, "
            "and runtime instrumentation. Used for bytecode matching and interceptor registration."
        ),
        "remediation": (
            "Verify target class/method exists and is accessible (not private/final), check "
            "instrumentation point configuration, review bytecode matching rules, and ensure "
            "proper ClassLoader context is set during reflection operations."
        ),
    },

    # ── Agent Memory / Overhead ──────────────────────────────────────────────
    "HeapShortageMonitor": {
        "category": "Memory & Heap Management",
        "issues": [
            "Heap usage critical",
            "Out of memory error",
            "Heap dump generation failed",
            "Memory pressure threshold exceeded"
        ],
        "description": (
            "Monitors JVM heap usage and memory pressure. Triggers cleanup actions (buffer "
            "drains, metric flushes) when heap approaches limits to prevent OOM conditions."
        ),
        "remediation": (
            "Increase JVM heap size (-Xmx), reduce collection buffer limits, disable expensive "
            "features (detailed logging, data sampling), review agent config for memory leaks, "
            "and check Post9AgentClassLoader for retained references."
        ),
    },
}
