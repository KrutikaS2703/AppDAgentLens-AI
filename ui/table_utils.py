import pandas as pd
import streamlit as st


def _table_palette() -> dict:
    if st.session_state.get("dark_mode", True):
        return {
            "cell_bg": "#0f1b31",
            "cell_bg_alt": "#13233d",
            "header_bg": "#162947",
            "text": "#e8f7ff",
            "muted": "#9fb7cb",
            "grid": "rgba(107, 227, 255, 0.18)",
        }

    return {
        "cell_bg": "#ffffff",
        "cell_bg_alt": "#f6f7fb",
        "header_bg": "#eceff8",
        "text": "#2f2948",
        "muted": "#6b7280",
        "grid": "#d9deea",
    }


def render_themed_dataframe(df: pd.DataFrame, *, width="stretch", height=None):
    palette = _table_palette()

    styler = (
        df.style
        .set_properties(
            **{
                "background-color": palette["cell_bg"],
                "color": palette["text"],
                "border-color": palette["grid"],
            }
        )
        .set_table_styles(
            [
                {
                    "selector": "th.col_heading",
                    "props": [
                        ("background-color", palette["header_bg"]),
                        ("color", palette["muted"]),
                        ("border", f"1px solid {palette['grid']}"),
                        ("font-weight", "600"),
                    ],
                },
                {
                    "selector": "th.row_heading, th.blank",
                    "props": [
                        ("background-color", palette["header_bg"]),
                        ("color", palette["muted"]),
                        ("border", f"1px solid {palette['grid']}"),
                    ],
                },
                {
                    "selector": "td",
                    "props": [
                        ("border", f"1px solid {palette['grid']}"),
                    ],
                },
                {
                    "selector": "tbody tr:nth-child(even) td",
                    "props": [("background-color", palette["cell_bg_alt"])],
                },
            ],
            overwrite=False,
        )
    )

    kwargs = {"width": width}
    if height is not None:
        kwargs["height"] = height

    st.dataframe(styler, **kwargs)