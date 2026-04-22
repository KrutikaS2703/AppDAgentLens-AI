import streamlit as st
import os
import re
import gzip
import html as html_lib


# ─────────────────────────────── file helpers ────────────────────────────────

def get_log_files(log_dir):
    """Get all log files from the directory."""
    if not log_dir or not os.path.exists(log_dir):
        return []
    log_files = []
    try:
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith(('.log', '.txt', '.out', '.gz')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, log_dir)
                    log_files.append((rel_path, full_path))
    except Exception as e:
        st.error(f"Error reading log directory: {e}")
    return sorted(log_files)


def truncate_filename(filename, max_length=25):
    """Truncate filename if too long."""
    if len(filename) <= max_length:
        return filename
    return filename[:max_length - 3] + "..."


def search_in_all_files(log_files, query):
    """Search for query across all log files."""
    results = []
    for rel_path, full_path in log_files:
        try:
            with _open_log_file(full_path) as f:
                for i, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        results.append({
                            'file': rel_path,
                            'full_path': full_path,
                            'line_num': i,
                            'content': line.rstrip('\n'),
                        })
        except Exception:
            continue
    return results


def _open_log_file(file_path: str):
    """Open plain text logs and gzipped logs transparently."""
    if file_path.lower().endswith('.gz'):
        return gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore')
    return open(file_path, 'r', encoding='utf-8', errors='ignore')


@st.cache_data(show_spinner=False)
def read_log_file_content(file_path: str) -> str:
    """Read file content with cache to speed up repeated file switching."""
    with _open_log_file(file_path) as fh:
        return fh.read()


# ─────────────────────────── HTML rendering helpers ──────────────────────────

def get_line_level(line: str) -> str:
    """Return 'error', 'warn', or '' based on log level token."""
    if re.search(r'\bERROR\b', line):
        return 'error'
    if re.search(r'\bWARN(?:ING)?\b', line):
        return 'warn'
    return ''


def _escape_and_highlight(text: str, query: str) -> str:
    """HTML-escape text and wrap query matches in a highlight mark."""
    escaped = html_lib.escape(text)
    if query:
        esc_q = re.escape(html_lib.escape(query))
        escaped = re.sub(
            esc_q,
            lambda m: f'<mark style="background:#fde047;color:#1a1a1a;padding:0 2px">{m.group()}</mark>',
            escaped,
            flags=re.IGNORECASE,
        )
    return escaped


_ROW_STYLE = {
    'error': (
        'rgba(220,38,38,0.18)', '#ef4444',
        '<span style="background:#ef4444;color:#fff;padding:1px 5px;border-radius:3px;'
        'font-size:10px;margin-right:6px;flex-shrink:0">ERROR</span>',
    ),
    'warn': (
        'rgba(234,179,8,0.18)', '#ca8a04',
        '<span style="background:#ca8a04;color:#fff;padding:1px 5px;border-radius:3px;'
        'font-size:10px;margin-right:6px;flex-shrink:0">WARN</span>',
    ),
    '': ('transparent', '#374151', ''),
}


def build_filtered_html(matching: list, search_query: str) -> str:
    """Styled HTML block for filtered search results with ERROR/WARN colors."""
    rows = []
    for item in matching:
        ln = item['line_num']
        content = item['content']
        file_tag = (
            f'<span style="color:#a3adc2;font-size:10px;margin-left:6px">'
            f'[{html_lib.escape(str(item.get("file", "")))}]</span>'
            if item.get('file') else ''
        )
        level = get_line_level(content)
        bg, border, badge = _ROW_STYLE[level]
        highlighted = _escape_and_highlight(content, search_query)
        rows.append(
            f'<div style="display:flex;align-items:flex-start;background:{bg};'
            f'border-left:3px solid {border};padding:5px 8px;margin:2px 0;'
            f'border-radius:0 4px 4px 0">'
            f'<span style="color:#9ca3af;font-size:11px;min-width:52px;flex-shrink:0">L{ln}</span>'
            f'{badge}'
            f'<span style="color:#e5e7eb;font-family:\'Courier New\',monospace;font-size:12px;word-break:break-all">'
            f'{highlighted}{file_tag}</span>'
            f'</div>'
        )
    inner = ''.join(rows)
    return (
        '<div style="background:#0e1117;padding:8px;border-radius:6px;'
        'max-height:420px;overflow-y:auto">' + inner + '</div>'
    )


def build_context_viewer_html(all_lines: list, selected_line: int, radius: int = 80) -> str:
    """
    HTML for ±radius lines around selected_line.
    ERROR=red, WARN=yellow, selected line=blue. JS auto-scrolls to it.
    """
    total = len(all_lines)
    start = max(0, selected_line - radius - 1)
    end = min(total, selected_line + radius)
    rows = []
    if start > 0:
        rows.append(
            f'<div style="color:#6b7280;padding:4px 8px;font-style:italic;font-size:11px">'
            f'\u2026 {start} lines above \u2026</div>'
        )
    for idx in range(start, end):
        ln = idx + 1
        raw = all_lines[idx].rstrip('\n')
        level = get_line_level(raw)
        escaped = html_lib.escape(raw)
        if ln == selected_line:
            bg, border, weight, row_id = (
                'rgba(56,189,248,0.25)', '#38bdf8', 'font-weight:bold', ' id="sel"'
            )
        elif level == 'error':
            bg, border, weight, row_id = 'rgba(220,38,38,0.18)', '#ef4444', '', ''
        elif level == 'warn':
            bg, border, weight, row_id = 'rgba(234,179,8,0.18)', '#ca8a04', '', ''
        else:
            bg, border, weight, row_id = 'transparent', 'transparent', '', ''
        rows.append(
            f'<div{row_id} style="display:flex;align-items:flex-start;background:{bg};'
            f'border-left:3px solid {border};padding:2px 8px;{weight}">'
            f'<span style="color:#6b7280;font-size:11px;min-width:48px;flex-shrink:0;'
            f'text-align:right;padding-right:10px">{ln}</span>'
            f'<span style="font-family:\'Courier New\',monospace;font-size:12px;'
            f'word-break:break-all;white-space:pre-wrap">{escaped}</span>'
            f'</div>'
        )
    if end < total:
        rows.append(
            f'<div style="color:#6b7280;padding:4px 8px;font-style:italic;font-size:11px">'
            f'\u2026 {total - end} lines below \u2026</div>'
        )
    return (
        '<!DOCTYPE html><html><head>'
        '<style>body{margin:0;background:#0e1117;color:#fafafa}#v{padding:8px}</style>'
        '</head><body><div id="v">'
        + ''.join(rows)
        + '</div>'
        '<script>window.onload=function(){'
        'var e=document.getElementById("sel");'
        'if(e)e.scrollIntoView({behavior:"smooth",block:"center"})}'
        '</script></body></html>'
    )


def build_full_file_html(all_lines: list) -> str:
    """Full file HTML with ERROR/WARN coloring and line numbers."""
    rows = []
    for ln, raw in enumerate(all_lines, 1):
        content = raw.rstrip('\n')
        level = get_line_level(content)
        escaped = html_lib.escape(content)
        if level == 'error':
            bg, border = 'rgba(220,38,38,0.18)', '#ef4444'
        elif level == 'warn':
            bg, border = 'rgba(234,179,8,0.18)', '#ca8a04'
        else:
            bg, border = 'transparent', 'transparent'
        rows.append(
            f'<div style="display:flex;align-items:flex-start;background:{bg};'
            f'border-left:3px solid {border};padding:2px 8px">'
            f'<span style="color:#6b7280;font-size:11px;min-width:48px;flex-shrink:0;'
            f'text-align:right;padding-right:10px">{ln}</span>'
            f'<span style="font-family:\'Courier New\',monospace;font-size:12px;'
            f'word-break:break-all;white-space:pre-wrap">{escaped}</span>'
            f'</div>'
        )
    return (
        '<!DOCTYPE html><html><head>'
        '<style>body{margin:0;background:#0e1117;color:#fafafa}#v{padding:8px}</style>'
        '</head><body><div id="v">'
        + ''.join(rows)
        + '</div></body></html>'
    )


def _render_full_file_view(log_content: str, file_path: str):
    """Render full file with colors (text_area fallback for large files) + stats."""
    MAX_LINES = 3000
    all_lines = log_content.splitlines()
    if len(all_lines) <= MAX_LINES:
        st.components.v1.html(build_full_file_html(all_lines), height=700, scrolling=True)
    else:
        st.text_area(
            "Log Content",
            value=log_content,
            height=700,
            key=f"log_viewer_full::{file_path}",
            label_visibility="collapsed",
        )
        st.caption(
            f"\u26a0\ufe0f Color highlighting disabled for files > {MAX_LINES} lines "
            f"({len(all_lines):,} lines in this file)."
        )
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Lines", f"{len(all_lines):,}")
    with c2:
        st.metric("Characters", f"{len(log_content):,}")
    with c3:
        try:
            size = os.path.getsize(file_path)
            st.metric("Size", f"{size / 1024:.2f} KB")
        except Exception:
            st.metric("Size", "N/A")




# ─────────────────────────────── main view ─────────────────────────────────────


def render_logs():
    """Render the log file browser and viewer with enhanced styling."""
    effective_log_path = (
        st.session_state.get("uploaded_logs_path")
        if st.session_state.get("using_uploaded_logs")
        else st.session_state.get("log_path")
    )

    if not effective_log_path:
        st.warning("⚠️ Please enter a log directory path in the sidebar first.")
        return

    if not os.path.exists(effective_log_path):
        st.error(f"❌ Directory not found: {effective_log_path}")
        return

    for key, default in [
        ('fullscreen_mode', False),
        ('jump_to_line', None),
        ('jump_to_file', None),
        ('loaded_log_file', None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    st.markdown("""<style>
    .logs-header {
        background: linear-gradient(135deg, #f4f2fc 0%, #e9e6f7 100%);
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 8px 16px rgba(62, 54, 95, 0.18);
    }
    .logs-header h1 {
        color: #2f2948 !important;
        margin: 0;
        background: none !important;
        -webkit-text-fill-color: #2f2948 !important;
    }
    .file-list-item {
        padding: 8px 12px;
        border-radius: 6px;
        margin: 4px 0;
        transition: all 0.3s ease;
    }
    .file-list-item:hover {
        background: rgba(233, 230, 247, 0.8);
        transform: translateX(4px);
    }
    </style>""", unsafe_allow_html=True)

    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.header("📁 Log File Browser")
    with col_header2:
        if st.button("⛶ Toggle Fullscreen", key="logs_fullscreen_btn"):
            st.session_state.fullscreen_mode = not st.session_state.fullscreen_mode
            st.rerun()

    log_files = get_log_files(effective_log_path)
    if not log_files:
        st.info("No log files found in the specified directory.")
        st.caption("Looking for files with extensions: .log, .txt, .out, .gz")
        return

    if st.session_state.fullscreen_mode:
        col1, col2 = st.columns([1, 10])
    else:
        col1, col2 = st.columns([1, 3])

    # ── File list ─────────────────────────────────────────────────────────────
    with col1:
        st.subheader(f"Files ({len(log_files)})")
        st.markdown("---")
        st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"] > div:has(> button) { padding: 2px 0px; }
        button[kind="secondary"] { padding: 4px 8px; font-size: 12px; min-height: 28px; }
        </style>
        """, unsafe_allow_html=True)
        for rel_path, full_path in log_files:
            truncated = truncate_filename(rel_path, max_length=30)
            is_sel = st.session_state.get('selected_log_file') == full_path
            label = f"📂 {truncated}" if is_sel else f"📄 {truncated}"
            if st.button(label, key=f"btn_{full_path}", width='stretch'):
                st.session_state.selected_log_file = full_path
                st.session_state.loaded_log_file = None
                st.session_state.search_query = ""
                st.session_state.jump_to_line = None
                st.session_state.jump_to_file = None
                st.rerun()

    # ── Content panel ─────────────────────────────────────────────────────────
    with col2:
        s1, s2, s3 = st.columns([4, 1, 1])
        with s1:
            search_query = st.text_input(
                "🔍 Search",
                value=st.session_state.get('search_query', ''),
                placeholder="Search in current file or all files...",
                key="search_input",
            )
            if search_query != st.session_state.get('search_query', ''):
                st.session_state.search_query = search_query
                st.session_state.jump_to_line = None
        with s2:
            search_mode = st.selectbox("Mode", ["Current File", "All Files"], key="search_mode")
        with s3:
            if st.button("Clear", width='stretch'):
                st.session_state.search_query = ""
                st.session_state.jump_to_line = None
                st.rerun()

        st.markdown("---")

        # ── Context view (jump to selected line) ──────────────────────────────
        if st.session_state.jump_to_line is not None:
            jump_file = st.session_state.jump_to_file or st.session_state.get('selected_log_file')
            jump_line = st.session_state.jump_to_line
            back_col, title_col = st.columns([1, 5])
            with back_col:
                if st.button("← Back"):
                    st.session_state.jump_to_line = None
                    st.session_state.jump_to_file = None
                    st.rerun()
            with title_col:
                st.markdown(f"**{os.path.basename(jump_file)}** — Line **{jump_line}** highlighted")
            try:
                with _open_log_file(jump_file) as fh:
                    all_lines = fh.readlines()
                st.components.v1.html(
                    build_context_viewer_html(all_lines, jump_line),
                    height=650,
                    scrolling=True,
                )
                st.caption(
                    f"Showing ±80 lines around line {jump_line}. "
                    f"Total: {len(all_lines):,} lines in {os.path.basename(jump_file)}"
                )
            except Exception as e:
                st.error(f"Error reading file: {e}")

        # ── Multi-file search ──────────────────────────────────────────────────
        elif st.session_state.get('search_query') and search_mode == "All Files":
            with st.spinner("Searching across all files..."):
                results = search_in_all_files(log_files, st.session_state.search_query)
            if results:
                unique_files = len(set(r['file'] for r in results))
                st.success(f"✓ Found {len(results)} match(es) across {unique_files} file(s)")
                st.markdown(
                    build_filtered_html(results, st.session_state.search_query),
                    unsafe_allow_html=True,
                )
                options = [
                    f"L{r['line_num']} | {r['file']} | {r['content'][:70]}"
                    for r in results
                ]
                st.session_state._jump_map = {
                    opt: {'line_num': r['line_num'], 'full_path': r['full_path']}
                    for opt, r in zip(options, results)
                }

                def _on_multi_jump():
                    sel = st.session_state.get('multi_jump_select')
                    data = st.session_state.get('_jump_map', {}).get(sel)
                    if not data:
                        return
                    st.session_state.jump_to_line = data['line_num']
                    st.session_state.jump_to_file = data['full_path']
                    st.session_state.selected_log_file = data['full_path']
                    st.session_state.loaded_log_file = None

                st.selectbox(
                    "📍 Select a result to open at its original position:",
                    options,
                    key="multi_jump_select",
                    on_change=_on_multi_jump,
                )
            else:
                st.warning(f"No matches found for '{st.session_state.search_query}' across all files")

        # ── Single file view ───────────────────────────────────────────────────
        elif st.session_state.get('selected_log_file'):
            file_path = st.session_state.selected_log_file
            st.subheader(f"📄 {os.path.basename(file_path)}")
            st.caption(file_path)
            st.markdown("---")
            try:
                if st.session_state.get('loaded_log_file') != file_path:
                    st.session_state.log_content = read_log_file_content(file_path)
                    st.session_state.loaded_log_file = file_path
                log_content = st.session_state.get('log_content', '')
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return

            if st.session_state.get('search_query') and search_mode == "Current File":
                all_lines = log_content.split('\n')
                matching = [
                    {'line_num': i, 'content': line, 'full_path': file_path}
                    for i, line in enumerate(all_lines, 1)
                    if st.session_state.search_query.lower() in line.lower()
                ]
                if matching:
                    st.success(f"✓ Found {len(matching)} matching line(s)")
                    st.markdown(
                        build_filtered_html(matching, st.session_state.search_query),
                        unsafe_allow_html=True,
                    )
                    options = [f"L{m['line_num']} | {m['content'][:80]}" for m in matching]
                    st.session_state._jump_map = {
                        opt: {'line_num': m['line_num'], 'full_path': file_path}
                        for opt, m in zip(options, matching)
                    }

                    def _on_single_jump():
                        sel = st.session_state.get('single_jump_select')
                        data = st.session_state.get('_jump_map', {}).get(sel)
                        if not data:
                            return
                        st.session_state.jump_to_line = data['line_num']
                        st.session_state.jump_to_file = data['full_path']

                    st.selectbox(
                        "📍 Select a result to open at its original position:",
                        options,
                        key="single_jump_select",
                        on_change=_on_single_jump,
                    )
                else:
                    st.warning(f"No matches found for '{st.session_state.search_query}'")
                    _render_full_file_view(log_content, file_path)
            else:
                _render_full_file_view(log_content, file_path)

        # ── Welcome screen ─────────────────────────────────────────────────────
        else:
            if not st.session_state.get('search_query'):
                st.info("👈 Select a log file from the left panel to view its contents")
                st.markdown("""
### Features
- 🔍 **Single File Search** — Search within the current file
- 🔍 **Multi-File Search** — Search across all log files
- 📍 **Jump to Context** — Select any filtered result to open at its original position
- 🎨 **Color Highlighting** — ERROR lines in red, WARN lines in yellow
- ⛶ **Fullscreen Mode** — Maximize viewing area
- 📈 **File Stats** — View file size and line count
""")
