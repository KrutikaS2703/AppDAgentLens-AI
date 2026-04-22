import streamlit as st
import pandas as pd


def _build_bt_dataframe(result: dict) -> pd.DataFrame:
    bt_details = result.get("bt_details") or {}
    if bt_details:
        rows = [
            {
                "Business Transaction": bt,
                "Type": metadata.get("type") or "N/A",
                "Count": metadata.get("count", 0),
            }
            for bt, metadata in bt_details.items()
        ]
        return pd.DataFrame(rows)

    return pd.DataFrame(
        [
            {
                "Business Transaction": bt,
                "Type": "N/A",
                "Count": count,
            }
            for bt, count in result.get("bt_counts", {}).items()
        ]
    )


def _build_dropped_bt_dataframe(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Business Transaction": bt,
                "Dropped Count": count,
            }
            for bt, count in result.get("dropped_bt_counts", {}).items()
        ]
    )


def render_bt():
    st.title("📈 Business Transaction Analyzer")

    # ✅ 1. Gate the UI
    if not st.session_state.scan_done:
        st.info("👈 Click **Scan JavaAgent Logs** to start analysis")
        return

    # ✅ 2. Read results ONLY from session state
    result = st.session_state.bt_result
    if not result:
        st.warning("No BT data found")
        return

    # ✅ 3. PURE DISPLAY
    st.metric("Unique BTs", result["unique_bts"])

    df = _build_bt_dataframe(result)

    bt_search = st.text_input("🔍 Search business transactions", placeholder="Filter by BT name...", key="bt_search")
    df_display = df[df["Business Transaction"].str.contains(bt_search, case=False, na=False)] if bt_search else df
    with st.expander("📋 Business Transactions Table", expanded=True):
        st.caption(f"Showing {len(df_display)} of {len(df)}")
        st.dataframe(df_display, width='stretch')

    st.download_button(
        "⬇️ Download BT summary",
        data=df.to_csv(index=False),
        file_name="bt_summary.csv"
    )
    st.divider()
    st.subheader("🚫 Dropped Business Transactions")

    dropped = result.get("dropped_bt_counts", {})

    if not dropped:
        st.success("No dropped BTs detected 🎉")
    else:
        df_dropped = _build_dropped_bt_dataframe(result).sort_values("Dropped Count", ascending=False)

        dropped_search = st.text_input("🔍 Search dropped BTs", placeholder="Filter by BT name...", key="dropped_search")
        df_dropped_display = df_dropped[df_dropped["Business Transaction"].str.contains(dropped_search, case=False, na=False)] if dropped_search else df_dropped
        with st.expander("📋 Dropped Business Transactions Table", expanded=True):
            st.caption(f"Showing {len(df_dropped_display)} of {len(df_dropped)}")
            st.dataframe(df_dropped_display, width='stretch')

        st.download_button(
            "⬇️ Download Dropped BTs",
            data=df_dropped.to_csv(index=False),
            file_name="dropped_bt_summary.csv"
        )
