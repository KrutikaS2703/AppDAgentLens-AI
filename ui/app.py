import streamlit as st
import os
import shutil
import zipfile
import tempfile
import base64
from pathlib import Path
from typing import Optional

from core.agent.scanner import run_agent_analysis
from core.bct.scanner import run_bct_analysis
from core.bt.scanner import run_bt_analysis
from state.session import init_session_state
from state.usage_tracker import (
    increment_counter,
    track_analyzer_selection,
    track_ui_access_once_per_session,
)
from ui.bct_view import render_bct
from ui.bt_view import render_bt
from ui.agent_view import render_agent
from ui.logs_view import render_logs
from ui.chatbot_view import render_chatbot
from ui.thread_dump_view import render_thread_dump_view


ANALYZER_OPTIONS = [
    "BCT Analyzer",
    "BT Analyzer",
    "Agent Analyzer",
    "AI Assistant",
    "Log File Browser",
]

APP_NAME = "AgentLens AI"
APP_TAGLINE = "Intelligent Log & Thread Analysis for AppDynamics JavaAgent"
APPDYNAMICS_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "AppDLogo.png"


def _get_analyzer_palette() -> dict:
    analyzer = st.session_state.get("selected_analyzer", "BCT Analyzer")
    dark_mode = st.session_state.get("dark_mode", True)

    dark_palettes = {
        "BCT Analyzer": {
            "accent": "#66e3ff",
            "accent_soft": "rgba(102, 227, 255, 0.14)",
            "accent_secondary": "#4f7cff",
        },
        "BT Analyzer": {
            "accent": "#ffbf69",
            "accent_soft": "rgba(255, 191, 105, 0.16)",
            "accent_secondary": "#ff8f5a",
        },
        "Agent Analyzer": {
            "accent": "#4df0b5",
            "accent_soft": "rgba(77, 240, 181, 0.14)",
            "accent_secondary": "#1bc4a1",
        },
        "AI Assistant": {
            "accent": "#c084fc",
            "accent_soft": "rgba(192, 132, 252, 0.16)",
            "accent_secondary": "#7c5cff",
        },
        "Log File Browser": {
            "accent": "#7dd3fc",
            "accent_soft": "rgba(125, 211, 252, 0.14)",
            "accent_secondary": "#38bdf8",
        },
    }

    light_palettes = {
        "BCT Analyzer": {
            "accent": "#4f7cff",
            "accent_soft": "rgba(79, 124, 255, 0.12)",
            "accent_secondary": "#66e3ff",
        },
        "BT Analyzer": {
            "accent": "#f59e0b",
            "accent_soft": "rgba(245, 158, 11, 0.14)",
            "accent_secondary": "#f97316",
        },
        "Agent Analyzer": {
            "accent": "#10b981",
            "accent_soft": "rgba(16, 185, 129, 0.14)",
            "accent_secondary": "#14b8a6",
        },
        "AI Assistant": {
            "accent": "#8b5cf6",
            "accent_soft": "rgba(139, 92, 246, 0.14)",
            "accent_secondary": "#c084fc",
        },
        "Log File Browser": {
            "accent": "#0ea5e9",
            "accent_soft": "rgba(14, 165, 233, 0.14)",
            "accent_secondary": "#38bdf8",
        },
    }

    palette = dark_palettes if dark_mode else light_palettes
    return palette.get(analyzer, palette["BCT Analyzer"])


def _get_theme_tokens() -> dict:
    analyzer_palette = _get_analyzer_palette()
    if st.session_state.get("dark_mode", True):
        tokens = {
            "bg": "#07111f",
            "surface": "rgba(10, 20, 38, 0.84)",
            "surface_strong": "#0d1830",
            "surface_soft": "rgba(15, 28, 51, 0.72)",
            "border": "rgba(107, 227, 255, 0.22)",
            "text": "#e8f7ff",
            "muted": "#8ba8bd",
            "button_text": "#041522",
            "sidebar_bg": "rgba(6, 16, 31, 0.96)",
            "header_bg": "rgba(6, 16, 31, 0.72)",
            "shadow": "0 14px 40px rgba(0, 0, 0, 0.38)",
            "brand_bg": "linear-gradient(135deg, rgba(8, 21, 41, 0.95) 0%, rgba(19, 34, 66, 0.90) 100%)",
            "brand_logo_bg": "linear-gradient(145deg, #66e3ff 0%, #4f7cff 100%)",
            "logo_wrap_bg": "rgba(255, 255, 255, 0.96)",
            "logo_wrap_border": "rgba(102, 227, 255, 0.26)",
            "grid_primary": "rgba(102, 227, 255, 0.08)",
            "grid_secondary": "rgba(139, 92, 246, 0.06)",
        }
        tokens.update(analyzer_palette)
        return tokens

    tokens = {
        "bg": "#f7f5fc",
        "surface": "#ffffff",
        "surface_strong": "#ffffff",
        "surface_soft": "#f3f0fb",
        "border": "#ddd7ef",
        "text": "#2f2948",
        "muted": "#625b7d",
        "button_text": "#3e365f",
        "sidebar_bg": "#f3f0fb",
        "header_bg": "rgba(247, 245, 252, 0.9)",
        "shadow": "0 10px 30px rgba(45, 35, 80, 0.08)",
        "brand_bg": "linear-gradient(135deg, #f7f5fc 0%, #ede8fb 100%)",
        "brand_logo_bg": "linear-gradient(145deg, #4f7cff 0%, #66e3ff 100%)",
        "logo_wrap_bg": "rgba(255, 255, 255, 0.88)",
        "logo_wrap_border": "#d7cfee",
        "grid_primary": "rgba(111, 95, 168, 0.05)",
        "grid_secondary": "rgba(159, 130, 226, 0.05)",
    }
    tokens.update(analyzer_palette)
    return tokens


def _consume_log_browser_navigation():
    query_params = st.query_params
    target_analyzer = query_params.get("analyzer")
    jump_file = query_params.get("jump_file")
    jump_line = query_params.get("jump_line")

    if not target_analyzer and not jump_file and not jump_line:
        return

    if target_analyzer in ANALYZER_OPTIONS:
        st.session_state.selected_analyzer = target_analyzer
    elif jump_file or jump_line:
        st.session_state.selected_analyzer = "Log File Browser"

    if jump_file and os.path.exists(jump_file):
        st.session_state.selected_log_file = jump_file
        st.session_state.jump_to_file = jump_file
        st.session_state.loaded_log_file = None
        st.session_state.search_query = ""

    if jump_line:
        try:
            st.session_state.jump_to_line = int(jump_line)
        except (TypeError, ValueError):
            st.session_state.jump_to_line = None

    query_params.clear()


def _get_logo_data_uri(image_path: Path) -> Optional[str]:
    if not image_path.exists():
        return None

    suffix = image_path.suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix)
    if not mime_type:
        return None

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _apply_global_styles():
        theme = _get_theme_tokens()
        st.markdown(
                f"""
                <style>
                @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

                @keyframes brandPulse {{
                    0%, 100% {{ box-shadow: inset 0 0 0 1px rgba(255,255,255,0.28), 0 0 20px rgba(102, 227, 255, 0.18); }}
                    50% {{ box-shadow: inset 0 0 0 1px rgba(255,255,255,0.32), 0 0 28px rgba(102, 227, 255, 0.32); }}
                }}

                @keyframes panelSweep {{
                    0% {{ transform: translateX(-130%) skewX(-18deg); opacity: 0; }}
                    12% {{ opacity: 0.18; }}
                    35% {{ opacity: 0.08; }}
                    100% {{ transform: translateX(185%) skewX(-18deg); opacity: 0; }}
                }}

                @keyframes logoOrbit {{
                    from {{ transform: rotate(0deg); }}
                    to {{ transform: rotate(360deg); }}
                }}

                :root {{
                    --la-bg: {theme['bg']};
                    --la-surface: {theme['surface']};
                    --la-surface-strong: {theme['surface_strong']};
                    --la-surface-soft: {theme['surface_soft']};
                    --la-border: {theme['border']};
                    --la-text: {theme['text']};
                    --la-muted: {theme['muted']};
                    --la-accent: {theme['accent']};
                    --la-accent-soft: {theme['accent_soft']};
                    --la-accent-secondary: {theme['accent_secondary']};
                    --la-button-text: {theme['button_text']};
                    --la-shadow: {theme['shadow']};
                }}

                .stApp {{
                    font-family: 'Manrope', sans-serif;
                    color: var(--la-text);
                    background:
                        linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
                        linear-gradient(90deg, {theme['grid_primary']} 1px, transparent 1px),
                        linear-gradient({theme['grid_primary']} 1px, transparent 1px),
                        radial-gradient(circle at 14% 10%, {theme['grid_secondary']} 0, transparent 24%),
                        radial-gradient(circle at 88% 8%, {theme['grid_primary']} 0, transparent 26%),
                        var(--la-bg);
                    background-size: auto, 34px 34px, 34px 34px, auto, auto;
                    min-height: 100vh;
                }}

                [data-testid='stSidebar'] {{
                    background: {theme['sidebar_bg']};
                    border-right: 1px solid var(--la-border);
                }}

                [data-testid='stSidebar'] * {{
                    color: var(--la-text);
                }}

                [data-testid='stHeader'] {{
                    background: {theme['header_bg']};
                    border-bottom: 1px solid var(--la-border);
                    backdrop-filter: blur(6px);
                }}

                h1, h2, h3 {{
                    color: var(--la-text) !important;
                    letter-spacing: -0.02em;
                }}

                p, li, label, span, [data-testid='stMarkdownContainer'] {{
                    color: var(--la-text);
                }}

                .stAlert {{
                    border-radius: 12px;
                    border: 1px solid var(--la-border);
                    background: var(--la-surface-soft);
                    box-shadow: var(--la-shadow);
                }}

                [data-testid='stAlert'] {{
                    background: var(--la-surface-soft) !important;
                    border-radius: 12px !important;
                    border: 1px solid var(--la-border) !important;
                }}

                [data-testid='stAlert'] > div {{
                    color: var(--la-text) !important;
                }}

                .st-emotion-cache-1wmy9hl {{
                    background: var(--la-surface-soft) !important;
                    color: var(--la-text) !important;
                }}

                .st-emotion-cache-12qpnml {{
                    background: var(--la-surface-soft) !important;
                    color: var(--la-text) !important;
                    border-color: var(--la-border) !important;
                }}

                [data-testid='stMetric'] {{
                    background: var(--la-surface-soft);
                    border: 1px solid var(--la-border);
                    border-radius: 14px;
                    padding: 14px;
                    box-shadow: var(--la-shadow);
                }}

                [data-testid='stMetricLabel'],
                [data-testid='stMetricValue'] {{
                    color: var(--la-text) !important;
                }}

                .stTabs [data-baseweb='tab-list'] {{
                    gap: 8px;
                    border-bottom: none;
                    margin-bottom: 10px;
                }}

                .stTabs [data-baseweb='tab'] {{
                    background: var(--la-surface-soft);
                    border-radius: 999px;
                    padding: 8px 14px;
                    color: var(--la-muted);
                    border: 1px solid var(--la-border);
                }}

                .stTabs [aria-selected='true'] {{
                    background: var(--la-accent-soft) !important;
                    color: var(--la-text) !important;
                    border-color: var(--la-accent) !important;
                    box-shadow: 0 0 0 1px var(--la-accent-soft), 0 0 18px color-mix(in srgb, var(--la-accent) 24%, transparent);
                }}

                .stButton > button,
                [data-testid='stDownloadButton'] > button {{
                    border-radius: 10px;
                    border: 1px solid var(--la-accent);
                    background: var(--la-surface-soft);
                    color: var(--la-text) !important;
                    font-weight: 700;
                    box-shadow: 0 0 0 1px var(--la-border);
                }}

                .stButton > button:hover,
                [data-testid='stDownloadButton'] > button:hover {{
                    border-color: var(--la-accent);
                    color: var(--la-text) !important;
                    background: var(--la-accent-soft);
                    filter: brightness(1.04);
                }}

                .stButton > button:active,
                .stButton > button:focus,
                [data-testid='stDownloadButton'] > button:active,
                [data-testid='stDownloadButton'] > button:focus {{
                    color: var(--la-text) !important;
                    background: var(--la-accent-soft);
                    border-color: var(--la-accent) !important;
                }}

                .stButton button {{
                    color: var(--la-text) !important;
                }}

                .stButton button span {{
                    color: var(--la-text) !important;
                }}

                [data-testid='stTextInput'] input,
                [data-testid='stTextArea'] textarea,
                [data-testid='stSelectbox'] > div {{
                    background: var(--la-surface-strong) !important;
                    color: var(--la-text) !important;
                    border: 1px solid var(--la-border) !important;
                    border-radius: 10px !important;
                }}

                [data-testid='stTextInput'] input::placeholder,
                [data-testid='stTextArea'] textarea::placeholder {{
                    color: var(--la-muted) !important;
                    opacity: 0.8 !important;
                }}

                [data-baseweb='select'] > div,
                [data-baseweb='input'] > div {{
                    background: var(--la-surface-strong) !important;
                    color: var(--la-text) !important;
                    border-color: var(--la-border) !important;
                }}

                [data-baseweb='input'] input {{
                    color: var(--la-text) !important;
                }}

                [data-baseweb='input'] input::placeholder {{
                    color: var(--la-muted) !important;
                    opacity: 0.8 !important;
                }}

                [data-testid='stExpander'] {{
                    background: var(--la-surface-soft);
                    border: 1px solid var(--la-border);
                    border-radius: 12px;
                    box-shadow: var(--la-shadow);
                }}

                [data-testid='stExpander'] summary {{
                    color: var(--la-text) !important;
                    background: var(--la-surface-soft) !important;
                }}

                [data-testid='stExpander'] summary:hover {{
                    color: var(--la-text) !important;
                    background: var(--la-accent-soft) !important;
                }}

                [data-testid='stExpander'] summary p,
                [data-testid='stExpander'] summary span,
                [data-testid='stExpander'] summary div,
                [data-testid='stExpander'] [data-testid='stExpanderToggleIcon'],
                [data-testid='stExpander'] [data-testid='stExpanderHeader'] {{
                    color: var(--la-text) !important;
                }}

                details > summary {{
                    color: var(--la-text) !important;
                }}

                details > summary::-webkit-details-marker {{
                    color: var(--la-accent) !important;
                }}

                [data-testid='stDataFrame'] {{
                    border: 1px solid var(--la-border) !important;
                    border-radius: 12px !important;
                    overflow: hidden !important;
                    background: var(--la-surface-soft) !important;
                }}

                [data-testid='stDataFrame'] table {{
                    background: var(--la-surface-soft) !important;
                    width: 100% !important;
                }}

                [data-testid='stDataFrame'] tr {{
                    background: #0f1b31 !important;
                    border-bottom: 1px solid var(--la-border) !important;
                }}

                [data-testid='stDataFrame'] tr:nth-child(odd) {{
                    background: #0f1b31 !important;
                }}

                [data-testid='stDataFrame'] tr:nth-child(even) {{
                    background: #13233d !important;
                }}

                [data-testid='stDataFrame'] tr:first-child {{
                    background: #162947 !important;
                }}

                [data-testid='stDataFrame'] tr:first-child:nth-child(odd) {{
                    background: #162947 !important;
                }}

                [data-testid='stDataFrame'] tr:hover {{
                    background: #1a3a4a !important;
                }}

                [data-testid='stDataFrame'] th {{
                    background: #162947 !important;
                    color: #9fb7cb !important;
                    font-weight: 600 !important;
                    padding: 10px !important;
                    border: none !important;
                }}

                [data-testid='stDataFrame'] td {{
                    color: #e8f7ff !important;
                    padding: 8px 10px !important;
                    border: none !important;
                }}

                .stColumn, [data-testid='stColumn'] {{
                    background: transparent !important;
                }}

                [data-testid='stVerticalBlock'] {{
                    background: transparent !important;
                }}

                [data-testid='stHorizontalBlock'] {{
                    background: transparent !important;
                }}

                .stRadio > div {{
                    background: var(--la-surface-soft);
                    border: 1px solid var(--la-border);
                    border-radius: 14px;
                    padding: 10px;
                }}

                [data-testid='stFileUploader'] {{
                    background: var(--la-surface-soft) !important;
                    border: 2px dashed var(--la-border) !important;
                    border-radius: 14px !important;
                    padding: 20px !important;
                }}

                [data-testid='stFileUploader'] * {{
                    color: var(--la-text) !important;
                    background: var(--la-surface-soft) !important;
                }}

                [data-testid='stFileUploader'] [role='button'] {{
                    background: var(--la-accent-soft) !important;
                    border: 1px solid var(--la-accent) !important;
                    color: var(--la-text) !important;
                }}

                .brand-shell {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 16px;
                    margin: 2px 0 10px 0;
                    padding: 14px 16px;
                    border: 1px solid var(--la-border);
                    border-radius: 16px;
                    background: {theme['brand_bg']};
                    box-shadow: var(--la-shadow), inset 0 0 0 1px rgba(102, 227, 255, 0.06);
                    position: relative;
                    overflow: hidden;
                }}

                .brand-shell::before {{
                    content: '';
                    position: absolute;
                    top: -20%;
                    bottom: -20%;
                    width: 30%;
                    background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--la-accent) 18%, transparent), transparent);
                    animation: panelSweep 9s linear infinite;
                    pointer-events: none;
                }}

                .brand-shell::after {{
                    content: '';
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.04) 45%, transparent 70%);
                    pointer-events: none;
                }}

                .brand-left {{
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    min-width: 0;
                    flex: 1 1 auto;
                    position: relative;
                    z-index: 1;
                }}

                .brand-logo {{
                    width: 52px;
                    height: 52px;
                    border-radius: 14px;
                    position: relative;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    background: {theme['brand_logo_bg']};
                    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.28), 0 0 20px color-mix(in srgb, var(--la-accent) 22%, transparent);
                    overflow: hidden;
                    animation: brandPulse 4.8s ease-in-out infinite;
                }}

                .brand-logo-orbit {{
                    position: absolute;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 2px solid rgba(255, 255, 255, 0.65);
                    top: 8px;
                    left: 8px;
                    animation: logoOrbit 16s linear infinite;
                }}

                .brand-logo-core {{
                    position: absolute;
                    width: 9px;
                    height: 9px;
                    border-radius: 50%;
                    background: #ffffff;
                    top: 17px;
                    left: 17px;
                    box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.22);
                }}

                .brand-logo-text {{
                    position: absolute;
                    right: 7px;
                    bottom: 4px;
                    font-weight: 800;
                    font-size: 13px;
                    color: #ffffff;
                    letter-spacing: 0.04em;
                }}

                .brand-title {{
                    margin: 0;
                    font-size: 1.7rem;
                    line-height: 1.05;
                    color: var(--la-text);
                    font-weight: 800;
                    letter-spacing: -0.02em;
                    text-shadow: 0 0 20px rgba(102, 227, 255, 0.08);
                }}

                .brand-tagline {{
                    margin: 4px 0 0 0;
                    font-size: 1.02rem;
                    color: var(--la-muted);
                    font-weight: 650;
                    letter-spacing: 0.01em;
                }}

                .brand-right-logo-wrap {{
                    margin-left: auto;
                    flex: 0 0 118px;
                    border: 1px solid {theme['logo_wrap_border']};
                    border-radius: 12px;
                    padding: 8px;
                    background: {theme['logo_wrap_bg']};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    z-index: 1;
                }}

                .brand-right-logo-wrap img {{
                    display: block;
                    width: 100%;
                    max-width: 102px;
                    height: auto;
                    object-fit: contain;
                }}

                @media (max-width: 720px) {{
                    .brand-shell {{
                        flex-wrap: wrap;
                        padding: 12px;
                        gap: 10px;
                    }}

                    .brand-left {{
                        width: 100%;
                    }}

                    .brand-logo {{
                        width: 44px;
                        height: 44px;
                        border-radius: 12px;
                    }}

                    .brand-logo-orbit {{
                        width: 24px;
                        height: 24px;
                        top: 7px;
                        left: 7px;
                    }}

                    .brand-logo-core {{
                        width: 7px;
                        height: 7px;
                        top: 14px;
                        left: 14px;
                    }}

                    .brand-logo-text {{
                        right: 6px;
                        bottom: 4px;
                        font-size: 11px;
                    }}

                    .brand-title {{
                        font-size: 1.35rem;
                    }}

                    .brand-tagline {{
                        font-size: 0.92rem;
                    }}

                    .brand-right-logo-wrap {{
                        margin-top: 0;
                        margin-left: 0;
                        flex-basis: 100px;
                    }}
                }}

                @media (prefers-color-scheme: light) {{
                    [data-testid='stDataFrame'] {{
                        background: #ffffff !important;
                        border-color: #ddd7ef !important;
                    }}

                    [data-testid='stDataFrame'] table {{
                        background: #ffffff !important;
                    }}

                    [data-testid='stDataFrame'] tr {{
                        background: #ffffff !important;
                    }}

                    [data-testid='stDataFrame'] tr:nth-child(odd) {{
                        background: #ffffff !important;
                    }}

                    [data-testid='stDataFrame'] tr:nth-child(even) {{
                        background: #f3f0fb !important;
                    }}

                    [data-testid='stDataFrame'] tr:first-child {{
                        background: #eceff8 !important;
                    }}

                    [data-testid='stDataFrame'] tr:hover {{
                        background: #ede8fb !important;
                    }}

                    [data-testid='stDataFrame'] th {{
                        background: #eceff8 !important;
                        color: #625b7d !important;
                    }}

                    [data-testid='stDataFrame'] td {{
                        color: #2f2948 !important;
                    }}

                    .stButton > button,
                    [data-testid='stDownloadButton'] > button {{
                        color: #2f2948 !important;
                    }}

                    .stButton > button:hover,
                    [data-testid='stDownloadButton'] > button:hover {{
                        color: #2f2948 !important;
                    }}

                    .stButton button,
                    .stButton button span {{
                        color: #2f2948 !important;
                    }}
                }}
                </style>
                """,
                unsafe_allow_html=True,
        )


def _render_brand_header():
    logo_src = _get_logo_data_uri(APPDYNAMICS_LOGO_PATH)
    right_logo_html = ""
    if logo_src:
        right_logo_html = (
            '<div class="brand-right-logo-wrap" aria-label="AppDynamics logo">'
            f'<img src="{logo_src}" alt="AppDynamics logo" />'
            '</div>'
        )

    st.markdown(
        f"""
        <div class="brand-shell">
            <div class="brand-left">
                <div class="brand-logo" aria-label="AgentLens AI logo">
                    <span class="brand-logo-orbit"></span>
                    <span class="brand-logo-core"></span>
                    <span class="brand-logo-text">AL</span>
                </div>
                <div>
                    <h1 class="brand-title">{APP_NAME}</h1>
                    <p class="brand-tagline">{APP_TAGLINE}</p>
                </div>
            </div>
            {right_logo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_uploaded_logs_dir() -> Path:
    """Create/get a session-scoped temp directory for uploaded JavaAgent logs."""
    if "uploaded_logs_dir" not in st.session_state or not st.session_state.uploaded_logs_dir:
        st.session_state.uploaded_logs_dir = tempfile.mkdtemp(prefix="javaagent_logs_")
    return Path(st.session_state.uploaded_logs_dir)


def _save_uploaded_javaagent_logs(uploaded_files, target_dir: Path):
    """Save uploaded files to a local folder and extract zip archives."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Refresh directory on each upload apply to avoid stale files.
    for child in target_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child, ignore_errors=True)

    saved_files = 0
    extracted_files = 0
    errors = []

    for uploaded in uploaded_files:
        file_name = Path(uploaded.name).name
        file_bytes = uploaded.getvalue()

        if file_name.lower().endswith(".zip"):
            try:
                zip_path = target_dir / file_name
                zip_path.write_bytes(file_bytes)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        # Keep only typical log-like files.
                        lower_member = member.filename.lower()
                        if not lower_member.endswith((".log", ".txt", ".out", ".gz")):
                            continue
                        zf.extract(member, target_dir)
                        extracted_files += 1

                # Keep extracted content only.
                zip_path.unlink(missing_ok=True)
                saved_files += 1
            except Exception as exc:
                errors.append(f"{file_name}: {exc}")
            continue

        try:
            out_path = target_dir / file_name
            out_path.write_bytes(file_bytes)
            saved_files += 1
        except Exception as exc:
            errors.append(f"{file_name}: {exc}")

    return {
        "saved_files": saved_files,
        "extracted_files": extracted_files,
        "errors": errors,
    }

# =============================
# SESSION STATE INITIALIZATION
# =============================

defaults = {
    "log_path": "",
    "run_scan": False,
    "bct_result": None,
    "bt_result": None,
    "agent_result": None,
    "selected_log_file": None,
    "log_content": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "scan_done" not in st.session_state:
    st.session_state.scan_done = False

if "bct_result" not in st.session_state:
    st.session_state.bct_result = None

if "bt_result" not in st.session_state:
    st.session_state.bt_result = None

if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

if "log_path" not in st.session_state:
    st.session_state.log_path = None

if "run_scan" not in st.session_state:
    st.session_state.run_scan = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "javaagent"

if "upload_apply_message" not in st.session_state:
    st.session_state.upload_apply_message = ""

if "uploaded_logs_path" not in st.session_state:
    st.session_state.uploaded_logs_path = None

if "using_uploaded_logs" not in st.session_state:
    st.session_state.using_uploaded_logs = False

if "uploader_reset_counter" not in st.session_state:
    st.session_state.uploader_reset_counter = 0

if "selected_analyzer" not in st.session_state:
    st.session_state.selected_analyzer = "BCT Analyzer"

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True


# =============================
# App config
# =============================
st.set_page_config(
    page_title=APP_NAME,
    layout="wide"
)

_apply_global_styles()
init_session_state()
_consume_log_browser_navigation()
track_ui_access_once_per_session()

# =============================
# SIDEBAR (GLOBAL)
# =============================
st.sidebar.header("JavaAgent Logs")

toggle_widget = getattr(st.sidebar, "toggle", st.sidebar.checkbox)
toggle_widget(
    "Dark Mode",
    key="dark_mode",
    help="Toggle between dark mode and light mode.",
)

st.session_state.log_path = st.sidebar.text_input(
    "Log Directory (manual)",
    value=st.session_state.log_path,
    placeholder="/path/to/JavaAgent/logs",
    help="Enter a directory path with JavaAgent logs, or use the upload option below."
)

if st.session_state.using_uploaded_logs and st.session_state.uploaded_logs_path:
    st.sidebar.info(f"✓ Using uploaded logs from: {st.session_state.log_path}")

st.sidebar.markdown("Or Upload JavaAgent Logs")
#st.sidebar.caption("Folder upload is not supported by Streamlit picker. Upload multiple files together ")

uploaded_javaagent_files = st.sidebar.file_uploader(
    "Upload logs (select all files in logs folder)",
    type=["log", "txt", "out", "gz", "zip"],
    accept_multiple_files=True,
    key=f"javaagent_logs_uploader_{st.session_state.uploader_reset_counter}",
)

if st.sidebar.button("Use Uploaded Logs"):
    if not uploaded_javaagent_files:
        st.session_state.upload_apply_message = "Please upload one or more files first."
    else:
        upload_dir = _get_uploaded_logs_dir()
        result = _save_uploaded_javaagent_logs(uploaded_javaagent_files, upload_dir)
        st.session_state.uploaded_logs_path = str(upload_dir)
        st.session_state.using_uploaded_logs = True

        msg = (
            f"Using uploaded logs (files: {result['saved_files']}, extracted from zip: {result['extracted_files']})."
        )
        if result["errors"]:
            msg += " Errors: " + " | ".join(result["errors"][:3])
        st.session_state.upload_apply_message = msg

if st.sidebar.button("Clear Uploaded Logs"):
    upload_dir_value = st.session_state.get("uploaded_logs_dir")
    if upload_dir_value and Path(upload_dir_value).exists():
        shutil.rmtree(upload_dir_value, ignore_errors=True)
    st.session_state.uploaded_logs_dir = ""
    st.session_state.uploaded_logs_path = None
    st.session_state.using_uploaded_logs = False
    st.session_state.upload_apply_message = "Uploaded logs cleared. Using manual directory path."
    # Increment counter to force file_uploader widget to reset
    st.session_state.uploader_reset_counter += 1
    st.rerun()

if st.session_state.upload_apply_message:
    st.sidebar.caption(st.session_state.upload_apply_message)


if st.sidebar.button("🚀 Scan JavaAgent Logs"):
    scan_path = st.session_state.uploaded_logs_path if st.session_state.using_uploaded_logs else st.session_state.log_path
    if not scan_path:
        st.sidebar.error("Please provide a log directory path or upload files.")
    else:
        increment_counter("scan_javaagent_logs")
        with st.spinner("Scanning all logs..."):
            st.session_state.bct_result = run_bct_analysis(scan_path)
            st.session_state.bt_result = run_bt_analysis(scan_path)
            st.session_state.agent_result = run_agent_analysis(scan_path)
            st.session_state.scan_done = True

if st.sidebar.button("🧵 Thread Dump Analyzer"):
    increment_counter("thread_dump_analyzer_access")
    st.session_state.app_mode = "thread_dump"

if st.session_state.app_mode == "thread_dump":
    if st.sidebar.button("⬅️ Back to JavaAgent Analyzer"):
        st.session_state.app_mode = "javaagent"
        st.rerun()

    _render_brand_header()
    st.subheader("Thread Dump Analysis")
    render_thread_dump_view()
    st.stop()


_render_brand_header()

# =============================
# ANALYZER SELECTION
# =============================

analyzer = st.radio(
    "Choose Analyzer",
    ANALYZER_OPTIONS,
    horizontal=True,
    key="selected_analyzer",
)

track_analyzer_selection(analyzer)

if analyzer == "BCT Analyzer":
    render_bct()

elif analyzer == "BT Analyzer":
    render_bt()

elif analyzer == "Agent Analyzer":
    render_agent()

elif analyzer == "AI Assistant":
    render_chatbot()

else:
    render_logs()
