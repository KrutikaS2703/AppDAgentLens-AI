import streamlit as st

def init_session_state():
    defaults = {
        "log_path": None,

        "bct_result": None,
        "bt_result": None,
        "agent_result": None,

        # BCT specific
        "matched": [],
        "applied": [],
        "no_interceptor_classes": [],
        "excludable_pkgs": {},
        "interceptor_counts": {}
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
