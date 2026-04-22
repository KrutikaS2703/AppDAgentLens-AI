import json
import re
import hashlib
import streamlit as st
import pandas as pd

from ai.llm import ask_llm
from core.thread_dump.analyzer import analyze_thread_dump_text, parse_uploaded_thread_dump


def _build_ai_prompt(doc_name: str, analysis: dict) -> str:
    state_counts = analysis.get("state_counts", {})
    top_contention = analysis.get("top_lock_contention", [])[:5]
    stuck_threads = analysis.get("stuck_threads", [])[:10]
    deadlocks = analysis.get("deadlock_sections", [])

    return f"""
You are a senior JVM performance and concurrency expert with AppDynamics agent expertise.

Use ONLY the deterministic findings provided. Do NOT assume or invent data.

Goals:
- Identify critical issues and root causes
- Provide precise, minimal, actionable remediation
- Detect if AppDynamics agent threads (com.singularity) are contributing to issues

Strict Rules:
- NO generic advice (e.g., "optimize", "check logs")
- Remediation must be SHORT, BULLET-POINTED, and directly mapped to findings
- Max 1 line per remediation action
- If insufficient data, explicitly say so
- Prioritize by severity
- Be technical and precise
- Use markdown bold for all top-level section headers, e.g., **5. Remediation Plan** and **3. AppDynamics Agent Analysis**

Thread dump source: {doc_name}
Threads parsed: {analysis.get('thread_count', 0)}
State counts: {state_counts}
Deadlocks detected: {len(deadlocks)}
Top contention locks: {top_contention}
Potential stuck threads: {stuck_threads}

Return format:

1. Executive Summary
- 2 lines: system state + primary risk

2. Key Findings (by severity)
For each:
- Issue:
- Evidence:
- Impact:

3. AppDynamics Agent Analysis
- Are any threads with "com.singularity" present? (Yes/No)
- If Yes:
  - Thread states (RUNNABLE/BLOCKED/etc.)
  - Any lock contention or blocking caused by them
  - Impact on application threads (if any)
- If No issues:
  - Clearly state: "No AppDynamics agent impact observed"

4. Root Cause Hypothesis
- Most likely cause(s) based on thread patterns

5. Remediation Plan

Immediate:
- (max 3 bullets, 1 line each)

Near-term:
- (max 3 bullets, 1 line each)

Long-term:
- (max 2 bullets, 1 line each)

6. Validation Steps
- 3 bullets max (what to verify post-fix)

7. Confidence
- High / Medium / Low + reason
""".strip()


def _highlight_ai_sections(ai_response: str) -> str:
    """Ensure key AI output section labels are bold for readability."""
    text = ai_response or ""

    section_labels = [
        "1. Executive Summary",
        "2. Key Findings (by severity)",
        "3. AppDynamics Agent Analysis",
        "4. Root Cause Hypothesis",
        "5. Remediation Plan",
        "6. Validation Steps",
        "7. Confidence",
        "Immediate:",
        "Near-term:",
        "Long-term:",
    ]

    for label in section_labels:
        pattern = rf"(?m)^\s*{re.escape(label)}\s*$"
        text = re.sub(pattern, f"**{label}**", text)

    return text


def _render_summary(analysis: dict):
    c1, c2, c3, c4, c5 = st.columns(5)
    state_counts = analysis.get("state_counts", {})

    with c1:
        st.metric("Threads", analysis.get("thread_count", 0))
    with c2:
        st.metric("Deadlocks", len(analysis.get("deadlock_sections", [])))
    with c3:
        st.metric("BLOCKED", state_counts.get("BLOCKED", 0))
    with c4:
        st.metric("RUNNABLE", state_counts.get("RUNNABLE", 0))
    with c5:
        st.metric("WAITING+TIMED", state_counts.get("WAITING", 0) + state_counts.get("TIMED_WAITING", 0))

    st.info(analysis.get("summary", "No summary available."))


def _render_tables(analysis: dict):
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "State Distribution",
            "Deadlocks",
            "Lock Contention",
            "Top Lock Owners",
            "Hot Stacks",
            "Stuck Threads",
        ]
    )

    with tab1:
        state_counts = analysis.get("state_counts", {})
        if not state_counts:
            st.write("No thread states parsed.")
        else:
            df = pd.DataFrame(
                [{"State": k, "Count": v} for k, v in state_counts.items()]
            ).sort_values("Count", ascending=False)
            st.dataframe(df, width='stretch')
            st.bar_chart(df.set_index("State")["Count"])

    with tab2:
        deadlocks = analysis.get("deadlock_sections", [])
        if not deadlocks:
            st.success("No Java-level deadlock section found.")
        else:
            for i, section in enumerate(deadlocks, start=1):
                with st.expander(f"Deadlock #{i}", expanded=(i == 1)):
                    st.code(section)

    with tab3:
        contention = analysis.get("top_lock_contention", [])
        if not contention:
            st.write("No lock contention found.")
        else:
            rows = []
            for c in contention:
                rows.append(
                    {
                        "Lock": c.get("lock_id", ""),
                        "Owner": c.get("owner", ""),
                        "Waiter Count": c.get("waiter_count", 0),
                        "Sample Waiters": ", ".join(c.get("waiters", [])[:5]),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width='stretch')

    with tab4:
        owners = analysis.get("top_lock_owners", [])
        if not owners:
            st.write("No lock owner data available.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "Owner Thread": o.get("owner", ""),
                        "Blocked Threads": o.get("blocked_threads", 0),
                    }
                    for o in owners
                ]
            )
            st.dataframe(df, width='stretch')

    with tab5:
        hot = analysis.get("hot_stacks", [])
        if not hot:
            st.write("No repeated hot stacks detected.")
        else:
            for i, item in enumerate(hot, start=1):
                with st.expander(f"Hot Stack #{i} ({item.get('count', 0)} threads)", expanded=(i == 1)):
                    st.write("**Sample Threads:** " + ", ".join(item.get("sample_threads", [])))
                    sig = item.get("signature", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(
                        f'<pre style="background:#f8fafc;color:#1e293b;padding:10px 14px;border-radius:6px;'
                        f'font-size:12px;font-family:monospace;overflow:auto;white-space:pre;'
                        f'border:1px solid #cbd5e1;max-height:200px;">{sig}</pre>',
                        unsafe_allow_html=True,
                    )

    with tab6:
        stuck = analysis.get("stuck_threads", [])
        if not stuck:
            st.success("No likely stuck threads detected by heuristic checks.")
        else:
            rows = []
            for item in stuck:
                rows.append(
                    {
                        "Thread": item.get("thread", ""),
                        "State": item.get("state", ""),
                        "Waiting On": item.get("waiting_on", ""),
                        "Reasons": "; ".join(item.get("reasons", [])),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width='stretch')


def render_thread_dump_view():
    st.title("🧵 Thread Dump Analyzer")
    st.markdown("Upload a thread dump (`.txt`, `.log`, `.tdump`, `.gz`, `.zip`) to run deterministic analysis.")

    max_mb = st.number_input("Max upload size for analysis (MB)", min_value=10, max_value=500, value=200, step=10)
    use_ai = st.checkbox("Add AI explanation and remediation (optional)", value=True)

    uploaded = st.file_uploader(
        "Upload thread dump file",
        type=["txt", "log", "tdump", "dump", "out", "gz", "zip"],
        accept_multiple_files=False,
    )

    if not uploaded:
        st.info("Upload a thread dump file to begin analysis.")
        return

    docs, warnings = parse_uploaded_thread_dump(uploaded, max_size_mb=int(max_mb))
    for warning in warnings:
        st.warning(warning)

    if not docs:
        return

    selected_doc = st.selectbox("Parsed source", options=list(range(len(docs))), format_func=lambda i: docs[i]["name"])
    doc = docs[selected_doc]

    analysis = analyze_thread_dump_text(doc["content"])
    _render_summary(analysis)
    _render_tables(analysis)

    st.subheader("Deterministic Findings (JSON)")
    st.download_button(
        "⬇️ Download Findings JSON",
        data=json.dumps(analysis, indent=2),
        file_name="thread_dump_analysis.json",
        mime="application/json",
    )

    if use_ai:
        st.subheader("AI Explanation and Remediation")
        with st.spinner("Generating AI explanation from deterministic findings..."):
            prompt = _build_ai_prompt(doc["name"], analysis)
            cache = st.session_state.setdefault("thread_dump_ai_cache", {})
            prompt_key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if prompt_key in cache:
                ai_response = cache[prompt_key]
            else:
                ai_response = ask_llm(prompt)
                cache[prompt_key] = ai_response

        if ai_response.strip().lower().startswith("ai unavailable"):
            st.warning(ai_response)
        else:
            st.markdown(_highlight_ai_sections(ai_response))

    with st.expander("Raw Thread Dump", expanded=False):
        st.text_area("Thread dump content", doc["content"], height=420)
