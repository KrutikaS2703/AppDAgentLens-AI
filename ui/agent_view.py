import streamlit as st
import pandas as pd
import html as html_lib
from urllib.parse import urlencode

from ai.analyzer import analyze_potential_issues, llm_analyze_issue


def _build_error_navigation_html(entries):
    rows = []
    for entry in entries:
        jump_file = entry.get("full_path")
        jump_line = entry.get("line_num")
        if not jump_file or jump_line is None:
            continue

        target_url = "?" + urlencode({
            "analyzer": "Log File Browser",
            "jump_file": jump_file,
            "jump_line": jump_line,
        })
        line_text = html_lib.escape(entry.get("line", ""))
        file_name = html_lib.escape(entry.get("file_name") or entry.get("file") or "")

        rows.append(
            f'<div ondblclick="window.location.assign(\'{target_url}\')" '
            'style="cursor:pointer;padding:8px 10px;margin:6px 0;border:1px solid #1f2937;'
            'border-radius:8px;background:#0f172a;color:#e5e7eb">'
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:4px">'
            f'<span style="font-size:11px;color:#fca5a5;background:#7f1d1d;padding:2px 6px;border-radius:999px">'
            f'LINE {jump_line}</span>'
            f'<span style="font-size:11px;color:#94a3b8">{file_name}</span>'
            '</div>'
            f'<div style="font-family:monospace;font-size:12px;white-space:pre-wrap;word-break:break-word">{line_text}</div>'
            '</div>'
        )

    if not rows:
        return ""

    return (
        '<div style="font-family:sans-serif">'
        + ''.join(rows)
        + '</div>'
    )


def _build_error_tree(errors_by_file):
    tree = {"children": {}, "entries": []}

    for relative_path, entries in errors_by_file.items():
        parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
        if not parts:
            parts = [relative_path]

        node = tree
        for part in parts:
            node = node["children"].setdefault(part, {"children": {}, "entries": []})
        node["entries"].extend(entries)

    return tree


def _count_tree_errors(node):
    total = len(node["entries"])
    for child in node["children"].values():
        total += _count_tree_errors(child)
    return total


def _render_error_selector_tree(node, parent_parts=None):
    if parent_parts is None:
        parent_parts = []

    for name in sorted(node["children"].keys()):
        child = node["children"][name]
        current_parts = parent_parts + [name]

        if child["children"]:
            with st.expander(f"📁 {name} ({_count_tree_errors(child)})", expanded=False):
                _render_error_selector_tree(child, current_parts)
        else:
            relative_path = "/".join(current_parts)
            if st.button(
                f"{name} ({len(child['entries'])})",
                key=f"agent_error_node_{relative_path}",
            ):
                st.session_state.agent_selected_node = f"error/{relative_path}"



def _render_warn_selector_tree(node, parent_parts=None):
    if parent_parts is None:
        parent_parts = []

    for name in sorted(node["children"].keys()):
        child = node["children"][name]
        current_parts = parent_parts + [name]

        if child["children"]:
            with st.expander(f"📁 {name} ({_count_tree_errors(child)})", expanded=False):
                _render_warn_selector_tree(child, current_parts)
        else:
            relative_path = "/".join(current_parts)
            if st.button(
                f"{name} ({len(child['entries'])})",
                key=f"agent_warn_node_{relative_path}",
            ):
                st.session_state.agent_selected_node = f"warn/{relative_path}"

def _render_clickable_text(label, node_id):
    """Render a clickable text item for navigation"""
    if st.button(label, key=f"nav_{node_id}"):
        st.session_state.agent_selected_node = node_id


def _render_controller_config(result):
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Controller Host:** {result.get('controller_host', 'N/A')}")
        st.write(f"**Controller Port:** {result.get('controller_port', 'N/A')}")
        st.write(f"**Controller Version:** {result.get('controller_version', 'N/A')}")
        st.write(f"**Application Name:** {result.get('application_name', 'N/A')}")
        st.write(f"**Tier Name:** {result.get('tier_name', 'N/A')}")
        st.write(f"**Node Name:** {result.get('node_name', 'N/A')}")

    with col2:
        st.write(f"**SSL Enabled:** {result.get('controller_ssl_enabled', 'N/A')}")
        st.write(f"**AppAgent Directory:** {result.get('appagent_dir', 'N/A')}")
        st.write(f"**Host Name:** {result.get('registration_host_name', 'N/A')}")
        st.write(f"**Application ID:** {result.get('registration_application_id', 'N/A')}")
        st.write(f"**Component ID:** {result.get('registration_component_id', 'N/A')}")
        st.write(f"**Node ID:** {result.get('registration_node_id', 'N/A')}")

def _render_jvm_config(result):
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Java Home:** {result.get('java_home', 'N/A')}")
        st.write(f"**Java Version:** {result.get('java_version', 'N/A')}")
        st.write(f"**Java Agent Version:** {result.get('java_agent_version', 'N/A')}")
        st.write(f"**VM Vendor:** {result.get('java_vm_vendor', 'N/A')}")
    with col2:
        st.write(f"**VM Name:** {result.get('java_vm_name', 'N/A')}")
        st.write(f"**OS Name:** {result.get('os_name', 'N/A')}")


def _render_jvm_process_info(result):
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**JVM Runtime Name:** {result.get('jvm_runtime_name', 'N/A')}")
    with col2:
        st.write(f"**JVM PID:** {result.get('jvm_pid', 'N/A')}")


def _render_jvm_args(result):
    jvm_args = result.get('jvm_args', 'N/A')
    if jvm_args and jvm_args != 'N/A':
        args_list = [arg.strip() for arg in jvm_args.split('|')]
        search_term = st.text_input(
            "🔍 Search JVM Arguments",
            placeholder="e.g., -Dappdynamics, -XX",
            key="agent_jvm_args_search",
        )
        if search_term:
            filtered_args = [arg for arg in args_list if search_term.lower() in arg.lower()]
        else:
            filtered_args = args_list

        st.dataframe(
            pd.DataFrame({"Arguments": filtered_args}),
            width='stretch',
            height=400,
        )
        st.caption(f"Showing {len(filtered_args)} of {len(args_list)} arguments")
    else:
        st.write("No JVM arguments found.")


def _render_checkpoints_inline(result):
    """Render checkpoints inline within agent-core (compact format)"""
    checkpoint_block = result.get("agent_checkpoints", {}) or {}
    checkpoints = checkpoint_block.get("items", []) or []
    jmx_domains = checkpoint_block.get("jmx_domains", []) or []

    if not checkpoints and not jmx_domains:
        return

    st.markdown("### Checkpoints")

    # Single line checkpoints
    debug_item = next((c for c in checkpoints if c.get("key") == "debug_logger"), None)
    if debug_item:
        status_icon = "✅" if debug_item.get("status") else "❌"
        st.write(f"DEBUG mode {status_icon}")

    disable_item = next((c for c in checkpoints if c.get("key") == "disable_agent"), None)
    if disable_item:
        status_icon = "✅" if disable_item.get("status") else "❌"
        st.write(f"Agent disabled {status_icon}")

    # Entry points - each on separate line
    pojo_item = next((c for c in checkpoints if c.get("key") == "pojo_entry_point"), None)
    servlet_item = next((c for c in checkpoints if c.get("key") == "servlet_entry_point"), None)
    jms_item = next((c for c in checkpoints if c.get("key") == "jms_entry_point"), None)

    if servlet_item or jms_item or pojo_item:
        st.write("Entry Points:")
        if servlet_item:
            icon = "✅" if servlet_item.get("status") else "❌"
            st.write(f"Servlet {icon}")
        if jms_item:
            icon = "✅" if jms_item.get("status") else "❌"
            st.write(f"JMS {icon}")
        if pojo_item:
            icon = "✅" if pojo_item.get("status") else "❌"
            st.write(f"POJO {icon}")

    # JMX Domains as simple list
    if jmx_domains:
        st.write("**JMX Domains Discovered:**")
        domains_text = ", ".join(jmx_domains)
        st.write(domains_text)


def _render_checkpoints_view(result):
    """Render checkpoints as full detailed view (for navigation) - compact format only"""
    checkpoint_block = result.get("agent_checkpoints", {}) or {}
    checkpoints = checkpoint_block.get("items", []) or []
    jmx_domains = checkpoint_block.get("jmx_domains", []) or []

    if not checkpoints and not jmx_domains:
        st.info("No checkpoint lines found in agent logs.")
        return

    # Single line checkpoints
    debug_item = next((c for c in checkpoints if c.get("key") == "debug_logger"), None)
    if debug_item:
        status_icon = "✅" if debug_item.get("status") else "❌"
        st.write(f"DEBUG mode {status_icon}")

    disable_item = next((c for c in checkpoints if c.get("key") == "disable_agent"), None)
    if disable_item:
        status_icon = "✅" if disable_item.get("status") else "❌"
        st.write(f"Agent disabled {status_icon}")

    # Entry points - each on separate line
    pojo_item = next((c for c in checkpoints if c.get("key") == "pojo_entry_point"), None)
    servlet_item = next((c for c in checkpoints if c.get("key") == "servlet_entry_point"), None)
    jms_item = next((c for c in checkpoints if c.get("key") == "jms_entry_point"), None)

    if servlet_item or jms_item or pojo_item:
        st.write("Entry Points:")
        if servlet_item:
            icon = "✅" if servlet_item.get("status") else "❌"
            st.write(f"Servlet {icon}")
        if jms_item:
            icon = "✅" if jms_item.get("status") else "❌"
            st.write(f"JMS {icon}")
        if pojo_item:
            icon = "✅" if pojo_item.get("status") else "❌"
            st.write(f"POJO {icon}")

    # JMX Domains as simple list
    if jmx_domains:
        st.write("**JMX Domains Discovered:**")
        domains_text = ", ".join(jmx_domains)
        st.write(domains_text)


def _render_agent_core(result):
    with st.expander("⚙️ Controller Config", expanded=True):
        _render_controller_config(result)

    with st.expander("⚙️ JVM Config", expanded=True):
        _render_jvm_config(result)

    with st.expander("⚙️ JVM Process Info", expanded=True):
        _render_jvm_process_info(result)

    with st.expander("⚙️ JVM Args", expanded=True):
        _render_jvm_args(result)


def _render_registered_bts(result):
    registered_bts = result.get("registered_business_transactions", [])
    if not registered_bts:
        st.write("No pre-registered business transactions found in agent logs.")
        return

    bt_search_term = st.text_input(
        "Search Business Transactions",
        placeholder="Filter by BT name, ID, or entry point type...",
        key="agent_bt_search",
    )

    if bt_search_term:
        filtered_bts = [
            bt for bt in registered_bts
            if bt_search_term.lower() in bt.get("bt_name", "").lower()
            or bt_search_term.lower() in bt.get("bt_id", "").lower()
            or bt_search_term.lower() in bt.get("entry_point_type", "").lower()
        ]
    else:
        filtered_bts = registered_bts

    bt_df = pd.DataFrame([
        {
            "Business Transaction Name": bt.get("bt_name", ""),
            "Business Transaction ID": bt.get("bt_id", ""),
            "Entry Point Type": bt.get("entry_point_type", ""),
        }
        for bt in filtered_bts
    ])

    st.dataframe(bt_df, width='stretch', height=300)
    st.caption(f"Showing {len(filtered_bts)} of {len(registered_bts)} unique business transactions")


def _render_registered_backends(result):
    backends = result.get("registered_backends", [])
    if not backends:
        st.write("No registered backends found in agent logs.")
        return

    search_term = st.text_input(
        "Search Backends",
        placeholder="Filter by backend name or ID...",
        key="agent_backend_search",
    )

    filtered = [
        b for b in backends
        if not search_term
        or search_term.lower() in b["backend_name"].lower()
        or search_term.lower() in b["backend_id"].lower()
    ]

    df = pd.DataFrame([
        {"Backend Name": b["backend_name"], "Backend ID": b["backend_id"]}
        for b in filtered
    ])
    st.dataframe(df, width='stretch', height=300)
    st.caption(f"Showing {len(filtered)} of {len(backends)} unique backends")


def _render_registered_service_endpoints(result):
    service_endpoints = result.get("registered_service_endpoints", [])
    if not service_endpoints:
        st.write("No registered service endpoints found in agent logs.")
        return

    search_term = st.text_input(
        "Search Service EndPoints",
        placeholder="Filter by SEP name, type, or ID...",
        key="agent_sep_search",
    )

    filtered = [
        sep for sep in service_endpoints
        if not search_term
        or search_term.lower() in sep["sep_name"].lower()
        or search_term.lower() in sep["sep_type"].lower()
        or search_term.lower() in sep["sep_id"].lower()
    ]

    df = pd.DataFrame([
        {
            "SEP Name": sep["sep_name"],
            "Type": sep["sep_type"],
            "ID": sep["sep_id"],
        }
        for sep in filtered
    ])

    st.dataframe(df, width='stretch', height=300)
    st.caption(f"Showing {len(filtered)} of {len(service_endpoints)} unique service endpoints")


def _render_registered_errors(result):
    registered_errors = result.get("registered_errors", [])
    if not registered_errors:
        st.write("No registered errors found in agent logs.")
        return

    search_term = st.text_input(
        "Search Registered Errors",
        placeholder="Filter by error name or ID...",
        key="agent_registered_error_search",
    )

    filtered = [
        err for err in registered_errors
        if not search_term
        or search_term.lower() in err["error_name"].lower()
        or search_term.lower() in err["error_id"].lower()
    ]

    df = pd.DataFrame([
        {
            "Error Name": err["error_name"],
            "ID": err["error_id"],
        }
        for err in filtered
    ])

    st.dataframe(df, width='stretch', height=420)
    st.caption(f"Showing {len(filtered)} of {len(registered_errors)} unique registered errors")


def _render_node_properties(result):
    props = result.get("node_properties", []) or []

    if not props:
        st.info("No node property assignments found in agent logs.")
        return

    search_term = st.text_input(
        "Search Properties",
        placeholder="Filter by property name or value...",
        key="agent_node_props_search",
    )
    filtered = [
        p for p in props
        if not search_term
        or search_term.lower() in p.get("name", "").lower()
        or search_term.lower() in p.get("value", "").lower()
    ]

    props_df = pd.DataFrame([
        {
            "Name": p.get("name", ""),
            "Value": p.get("value", ""),
        }
        for p in filtered
    ])
    st.dataframe(props_df, width='stretch', height=420)
    st.caption(f"Showing {len(filtered)} of {len(props)} unique properties (latest value per name)")


def _render_failed_seps(result):
    failed = result.get("failed_seps", {}) or {}
    nested_seps = failed.get("nested_seps", []) or []
    blacklisted_seps = failed.get("blacklisted_seps", []) or []

    if not nested_seps and not blacklisted_seps:
        st.success("No failed SEP registration warnings found in agent logs.")
        return

    with st.expander("Nested SEPs", expanded=True):
        if not nested_seps:
            st.write("No nested SEP warnings found.")
        else:
            search_term = st.text_input(
                "Search Nested SEPs",
                placeholder="Filter by SEP name or type...",
                key="agent_nested_sep_search",
            )
            filtered_nested = [
                sep for sep in nested_seps
                if not search_term
                or search_term.lower() in sep.get("sep_name", "").lower()
                or search_term.lower() in sep.get("sep_type", "").lower()
            ]
            nested_df = pd.DataFrame([
                {
                    "SEP Name": sep.get("sep_name", ""),
                    "Type": sep.get("sep_type", ""),
                }
                for sep in filtered_nested
            ])
            st.dataframe(nested_df, width='stretch', height=260)
            st.caption(f"Showing {len(filtered_nested)} of {len(nested_seps)} nested SEPs")

    with st.expander("Blacklisted SEP", expanded=True):
        if not blacklisted_seps:
            st.write("No blacklisted SEP warnings found.")
        else:
            search_term = st.text_input(
                "Search Blacklisted SEPs",
                placeholder="Filter by SEP name or type...",
                key="agent_blacklisted_sep_search",
            )
            filtered_blacklisted = [
                sep for sep in blacklisted_seps
                if not search_term
                or search_term.lower() in sep.get("sep_name", "").lower()
                or search_term.lower() in sep.get("sep_type", "").lower()
            ]
            blacklisted_df = pd.DataFrame([
                {
                    "SEP Name": sep.get("sep_name", ""),
                    "Type": sep.get("sep_type", ""),
                }
                for sep in filtered_blacklisted
            ])
            st.dataframe(blacklisted_df, width='stretch', height=260)
            st.caption(f"Showing {len(filtered_blacklisted)} of {len(blacklisted_seps)} blacklisted SEPs")


def _render_potential_issues(result):
    """AI Potential Issues section based on logger KB matching."""
    logger_issues = result.get("logger_issues") or []
    potential = analyze_potential_issues(logger_issues)

    if not potential:
        st.success("✅ No known issue patterns detected in agent logs.")
        return

    st.markdown(
        f"**{len(potential)} potential issue(s) detected** from logger patterns "
        "in ERROR / WARN lines:"
    )

    for item in potential:
        is_error = item["level"] == "ERROR"
        # Badge uses explicit colours that remain legible on both themes.
        badge_color = "#b91c1c" if is_error else "#b45309"
        badge_bg    = "#fee2e2" if is_error else "#fef3c7"
        level_badge = (
            f'<span style="font-size:11px;color:{badge_color};background:{badge_bg};'
            f'padding:2px 8px;border-radius:999px;font-weight:bold;'
            f'margin-right:8px;border:1px solid {badge_color}">'
            f'{item["level"]}</span>'
        )
        # Logger / occurrences meta — use currentColor so it inherits the
        # theme's foreground and is readable in both light and dark mode.
        meta = (
            f'<span style="font-size:11px;opacity:0.6;margin-left:6px">'
            f'Logger: {item["logger"]} &nbsp;|&nbsp; Occurrences: {item["occurrences"]}'
            f'</span>'
        )
        with st.expander(item["category"], expanded=True):
            st.markdown(
                f'<div style="margin-bottom:8px">{level_badge}{meta}</div>',
                unsafe_allow_html=True,
            )

            # Possible issues
            issues_md = "  \n".join(f"• {iss}" for iss in item["issues"])
            st.markdown(f"**Possible Issues:**  \n{issues_md}")

            st.markdown(f"**Description:** {item['description']}")
            st.markdown(f"**Remediation:** {item['remediation']}")

            # Latest log line from newest file — monospace block, theme-neutral
            if item.get("latest_line"):
                ts       = html_lib.escape(item.get("timestamp", ""))
                fname    = html_lib.escape(item.get("file_name", ""))
                raw_line = html_lib.escape(item["latest_line"])
                ts_part  = (
                    f' &nbsp;<span style="font-size:11px;opacity:0.5">{ts}</span>'
                    if ts else ""
                )
                st.markdown(
                    f'<div style="margin-top:10px;padding:8px 12px;'
                    f'border:1px solid rgba(128,128,128,0.3);border-radius:8px;'
                    f'background:rgba(0,0,0,0.05)">'
                    f'<div style="margin-bottom:4px">'
                    f'<span style="font-size:11px;opacity:0.6">{fname}</span>{ts_part}'
                    f'</div>'
                    f'<div style="font-family:monospace;font-size:12px;'
                    f'white-space:pre-wrap;word-break:break-word">{raw_line}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            issue_key = f"{item.get('logger', 'logger')}_{item.get('level', 'level')}_{item.get('category', 'category')}"
            ai_btn_key = f"ask_ai_btn_{issue_key}"
            ai_out_key = f"ask_ai_out_{issue_key}"

            if st.button("Ask AI", key=ai_btn_key):
                with st.spinner("Analyzing this issue..."):
                    st.session_state[ai_out_key] = llm_analyze_issue(item)

            ai_output = st.session_state.get(ai_out_key)
            if ai_output:
                st.markdown("**AI Analysis**")
                st.markdown(ai_output)


def _render_error_overview(error_summary):
    total_errors = error_summary.get("total_errors", 0)
    unique_errors = error_summary.get("unique_errors", 0)
    error_type_counts = error_summary.get("error_type_counts", [])

    unique_error_types = len(error_type_counts)
    col1, col2 = st.columns(2)
    col1.metric("Total ERROR lines", total_errors)
    col2.metric("Unique ERROR types", unique_error_types)

    if not error_type_counts:
        st.success("No ERROR lines found in agent logs.")
        return

    st.markdown("---")
    st.markdown("##### Error Summary (sorted by frequency)")

    search_term = st.text_input(
        "🔍 Filter errors",
        placeholder="Search error text...",
        key="agent_error_overview_search",
    )

    filtered = [
        e for e in error_type_counts
        if not search_term or search_term.lower() in e["label"].lower()
    ]

    df = pd.DataFrame([
        {
            "Error": e["label"],
            "Occurrences": e["occurrences"],
        }
        for e in filtered
    ])

    st.dataframe(df, width='stretch', height=420)
    st.caption(f"Showing {len(filtered)} of {unique_error_types} unique error types")


def _render_error_details(result, selected_node):
    error_summary = result.get("error_summary", {})
    total_errors = error_summary.get("total_errors", 0)
    unique_errors = error_summary.get("unique_errors", 0)
    errors_by_file = error_summary.get("errors_by_file", {})

    st.write(f"**Total ERROR lines:** {total_errors}")
    st.write(f"**Unique ERRORs (latest occurrence shown):** {unique_errors}")

    if total_errors == 0:
        st.success("No ERROR lines found in agent logs.")
        return

    if not errors_by_file:
        st.info("ERROR summary is empty.")
        return

    selected_relative_path = ""
    if selected_node.startswith("error/"):
        selected_relative_path = selected_node[len("error/"):]

    if not selected_relative_path or selected_relative_path == "_overview":
        _render_error_overview(error_summary)
        return

    entries = errors_by_file.get(selected_relative_path, [])
    st.caption(f"Selected file: {selected_relative_path}")

    search_term = st.text_input(
        "Search ERROR logs in selected file",
        placeholder="Filter ERROR lines...",
        key="agent_error_detail_search",
    )

    if search_term:
        entries = [
            entry for entry in entries
            if search_term.lower() in entry.get("line", "").lower()
        ]

    if not entries:
        st.warning("No ERROR lines match the current search.")
        return

    navigation_html = _build_error_navigation_html(entries)
    if navigation_html:
        st.markdown(navigation_html, unsafe_allow_html=True)
    else:
        st.dataframe(
            pd.DataFrame([{"Latest ERROR": entry.get("line", "")} for entry in entries]),
            width='stretch',
            height=320,
        )


def _render_warn_overview(warn_summary):
    total_warns = warn_summary.get("total_warns", 0)
    warn_type_counts = warn_summary.get("warn_type_counts", [])

    unique_warn_types = len(warn_type_counts)
    col1, col2 = st.columns(2)
    col1.metric("Total WARN lines", total_warns)
    col2.metric("Unique WARN types", unique_warn_types)

    if not warn_type_counts:
        st.success("No WARN lines found in agent logs.")
        return

    st.markdown("---")
    st.markdown("##### Warn Summary (sorted by frequency)")

    search_term = st.text_input(
        "🔍 Filter warnings",
        placeholder="Search warning text...",
        key="agent_warn_overview_search",
    )

    filtered = [
        w for w in warn_type_counts
        if not search_term or search_term.lower() in w["label"].lower()
    ]

    df = pd.DataFrame([
        {"Warning": w["label"], "Occurrences": w["occurrences"]}
        for w in filtered
    ])

    st.dataframe(df, width='stretch', height=420)
    st.caption(f"Showing {len(filtered)} of {unique_warn_types} unique warning types")


def _render_warn_details(result, selected_node):
    warn_summary = result.get("warn_summary", {})
    total_warns = warn_summary.get("total_warns", 0)
    warns_by_file = warn_summary.get("warns_by_file", {})

    if not selected_node.startswith("warn/"):
        _render_warn_overview(warn_summary)
        return

    selected_relative_path = selected_node[len("warn/"):]

    if not selected_relative_path or selected_relative_path == "_overview":
        _render_warn_overview(warn_summary)
        return

    entries = warns_by_file.get(selected_relative_path, [])
    st.caption(f"Selected file: {selected_relative_path}")

    search_term = st.text_input(
        "Search WARN logs in selected file",
        placeholder="Filter WARN lines...",
        key="agent_warn_detail_search",
    )

    if search_term:
        entries = [
            entry for entry in entries
            if search_term.lower() in entry.get("line", "").lower()
        ]

    if not entries:
        st.warning("No WARN lines match the current search.")
        return

    navigation_html = _build_warn_navigation_html(entries)
    if navigation_html:
        st.markdown(navigation_html, unsafe_allow_html=True)
    else:
        st.dataframe(
            pd.DataFrame([{"Latest WARN": entry.get("line", "")} for entry in entries]),
            width='stretch',
            height=320,
        )


def _build_warn_navigation_html(entries):
    rows = []
    for entry in entries:
        jump_file = entry.get("full_path")
        jump_line = entry.get("line_num")
        if not jump_file or jump_line is None:
            continue

        from urllib.parse import urlencode as _ue
        import html as _html
        target_url = "?" + _ue({
            "analyzer": "Log File Browser",
            "jump_file": jump_file,
            "jump_line": jump_line,
        })
        line_text = _html.escape(entry.get("line", ""))
        file_name = _html.escape(entry.get("file_name") or entry.get("file") or "")

        rows.append(
            f'<div ondblclick="window.location.assign(\'{target_url}\')" '
            'style="cursor:pointer;padding:8px 10px;margin:6px 0;border:1px solid #1f2937;'
            'border-radius:8px;background:#0f172a;color:#e5e7eb">'
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:4px">'
            f'<span style="font-size:11px;color:#fde68a;background:#78350f;padding:2px 6px;border-radius:999px">'
            f'LINE {jump_line}</span>'
            f'<span style="font-size:11px;color:#94a3b8">{file_name}</span>'
            '</div>'
            f'<div style="font-family:monospace;font-size:12px;white-space:pre-wrap;word-break:break-word">{line_text}</div>'
            '</div>'
        )

    if not rows:
        return ""
    return '<div style="font-family:sans-serif">' + ''.join(rows) + '</div>'

def render_agent():
    st.title("🧠 JavaAgent Analysis")
    if not st.session_state.scan_done:
        st.info("👈 Click **Scan JavaAgent Logs** to start analysis")
        return

    result = st.session_state.agent_result
    if not result or (isinstance(result, dict) and result.get("error")):
        st.warning("No agent log details found.")
        if result and result.get("error"):
            st.text(result["error"])
        return

    error_summary = result.get("error_summary", {})
    errors_by_file = error_summary.get("errors_by_file", {})
    error_tree = _build_error_tree(errors_by_file)

    warn_summary = result.get("warn_summary", {})
    warns_by_file = warn_summary.get("warns_by_file", {})
    warn_tree = _build_error_tree(warns_by_file)

    if "agent_selected_node" not in st.session_state:
        st.session_state.agent_selected_node = "agent-core"

    left_col, right_col = st.columns([1.1, 2.4], gap="large")

    with left_col:
        st.markdown("### 📁 Navigation")
        
        # agent-core section
        with st.expander("🔧 agent-core", expanded=True):
            _render_clickable_text("🔧 agent-core", "agent-core")
            _render_clickable_text("✅ Checkpoints", "agent-core/checkpoints")
            _render_clickable_text("🤖 AI Potential Issues", "ai-potential-issues")
        
        # Registration section
        with st.expander("📋 Registration", expanded=True):
            _render_clickable_text("📋 Registered Business Transactions", "registration/registered-business-transactions")
            _render_clickable_text("🔗 Registered Backends", "registration/registered-backends")
            _render_clickable_text("🧩 Registered ServiceEndPoints", "registration/registered-service-endpoints")
            _render_clickable_text("❗ Registered Errors", "registration/registered-errors")
            _render_clickable_text("⚙️ Node Properties", "registration/node-properties")
            _render_clickable_text("🚫 Failed SEPs", "registration/failed-seps")
        
        # ERROR section
        with st.expander("⚠️ ERROR", expanded=True):
            _render_clickable_text("📊 Overview", "error/_overview")
            
            if errors_by_file:
                st.markdown("**Error Files:**")
                _render_error_selector_tree(error_tree)
            else:
                st.caption("No ERROR files found")

        # WARN section
        with st.expander("🟡 WARN", expanded=True):
            _render_clickable_text("📊 Overview", "warn/_overview")
            
            if warns_by_file:
                st.markdown("**Warn Files:**")
                _render_warn_selector_tree(warn_tree)
            else:
                st.caption("No WARN files found")

    with right_col:
        selected = st.session_state.agent_selected_node

        # Handle agent-core sub-sections
        if selected == "agent-core/checkpoints":
            st.subheader("Checkpoints")
            _render_checkpoints_view(result)
        elif selected.startswith("agent-core/"):
            selected = "agent-core"
            _render_agent_core(result)
        elif selected == "agent-core":
            _render_agent_core(result)
        elif selected == "ai-potential-issues":
            st.subheader("🤖 AI Potential Issues")
            _render_potential_issues(result)
        elif selected == "registration/registered-business-transactions":
            st.subheader("Registered Business Transactions")
            _render_registered_bts(result)
        elif selected == "registration/registered-backends":
            st.subheader("Registered Backends")
            _render_registered_backends(result)
        elif selected == "registration/registered-service-endpoints":
            st.subheader("Registered ServiceEndPoints")
            _render_registered_service_endpoints(result)
        elif selected == "registration/registered-errors":
            st.subheader("Registered Errors")
            _render_registered_errors(result)
        elif selected == "registration/node-properties":
            st.subheader("Node Properties")
            _render_node_properties(result)
        elif selected == "registration/failed-seps":
            st.subheader("Failed SEPs")
            _render_failed_seps(result)
        elif selected.startswith("error/"):
            st.subheader("ERROR")
            _render_error_details(result, selected)
        elif selected.startswith("warn/"):
            st.subheader("WARN")
            _render_warn_details(result, selected)
        else:
            st.info("Select a node from the left tree.")
