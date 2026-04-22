"""
Streamlit UI for node-properties assistant.
"""

import streamlit as st
from ai.analyzer import detect_frameworks_used
from ai.chatbot import ask_chatbot_with_source
from ai.feedback import clear_feedback, delete_feedback, load_feedback_entries, save_feedback


def _render_feedback_for_last_answer():
    history = st.session_state.get("chat_history", [])
    if not history:
        return

    assistant_index = None
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "assistant":
            assistant_index = i
            break

    if assistant_index is None:
        return

    assistant_msg = history[assistant_index]
    question = assistant_msg.get("question", "")
    if not question:
        return

    if assistant_msg.get("feedback_status") in {"yes", "no"}:
        if assistant_msg.get("feedback_status") == "no":
            st.caption("Feedback saved. I will use your correction for future similar questions.")
        return

    st.markdown("### Feedback")
    st.markdown("Have I answered your question correctly?")

    choice_key = f"feedback_choice_{assistant_index}"
    correction_key = f"feedback_correction_{assistant_index}"
    submit_yes_key = f"feedback_yes_btn_{assistant_index}"
    submit_no_key = f"feedback_no_btn_{assistant_index}"

    choice = st.radio(
        "Feedback selection",
        options=["Yes", "No"],
        key=choice_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    if choice == "Yes":
        if st.button("Submit Feedback", key=submit_yes_key):
            history[assistant_index]["feedback_status"] = "yes"
            st.session_state.chat_history = history
            st.success("Thanks for your feedback.")
            st.rerun()
    else:
        correction = st.text_area(
            "What should be the correct answer?",
            placeholder="Write the corrected answer here...",
            key=correction_key,
            height=120,
        )
        if st.button("Save Correction", key=submit_no_key):
            correction_text = (correction or "").strip()
            if not correction_text:
                st.warning("Please provide the correct answer before saving.")
            else:
                save_feedback(
                    question=question,
                    assistant_answer=assistant_msg.get("content", ""),
                    correction=correction_text,
                )
                history[assistant_index]["feedback_status"] = "no"
                history[assistant_index]["correction"] = correction_text
                st.session_state.chat_history = history
                st.success("Correction saved. I will use this answer next time.")
                st.rerun()


def _render_feedback_admin():
    with st.expander("🧠 Learned Corrections", expanded=False):
        entries = load_feedback_entries()
        if not entries:
            st.caption("No saved corrections yet.")
            return

        st.caption(f"Saved corrections: {len(entries)}")
        if st.button("Clear All Corrections", key="clear_all_feedback_btn"):
            clear_feedback()
            st.success("All saved corrections were removed.")
            st.rerun()

        st.markdown("---")
        for idx, entry in enumerate(reversed(entries)):
            question = entry.get("question", "")
            correction = entry.get("correction", "")
            updated_at = entry.get("updated_at", "")
            q_norm = entry.get("question_normalized", "")

            st.markdown(f"**Q:** {question}")
            st.markdown(f"**Saved Correction:** {correction}")
            if updated_at:
                st.caption(f"Updated: {updated_at}")

            if st.button("Delete", key=f"delete_feedback_{idx}"):
                if delete_feedback(q_norm):
                    st.success("Correction deleted.")
                    st.rerun()
                st.warning("Could not delete this correction.")

            st.markdown("---")


def _expand_quick_question(question: str) -> str:
    if question != "Which scanned frameworks are supported by AppDynamics?":
        return question

    bct_result = st.session_state.get("bct_result") or {}
    matched_classes = bct_result.get("matched_classes", []) or []
    frameworks = detect_frameworks_used(matched_classes)

    if not frameworks:
        return (
            "Which Java frameworks are supported by the AppDynamics Java Agent? "
            "Please summarize major supported frameworks and version ranges from the Java Supported Environments reference."
        )

    framework_names = ", ".join(item["framework"] for item in frameworks)
    return (
        "Based on my current BCT scan, these frameworks were detected from scanned classes: "
        f"{framework_names}. "
        "For each detected framework, say whether it is supported by the AppDynamics Java Agent, "
        "include known supported versions if available, and mention any important configuration caveats."
    )


def render_chatbot():
    """Render the AI chatbot interface."""
    st.title("🤖 AI Assistant")

    st.markdown("Ask anything about AppDynamics configuration, node properties, JVM args, or troubleshooting.")

    get_all_properties = st.button("Get Node Properties", width='stretch')

    st.markdown("### Quick Questions")
    suggested_questions = [
        "List snapshots related node properties",
        "Does JDK 8 supported by 26.2 agent version?",
        "How do I configure the controller host and port?",
        "Agent metric limit is reached",
        "Which scanned frameworks are supported by AppDynamics?",
    ]

    selected_quick_question = None
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button(suggested_questions[0], width='stretch'):
            selected_quick_question = suggested_questions[0]
        if st.button(suggested_questions[2], width='stretch'):
            selected_quick_question = suggested_questions[2]
        if st.button(suggested_questions[4], width='stretch'):
            selected_quick_question = suggested_questions[4]
    with q_col2:
        if st.button(suggested_questions[1], width='stretch'):
            selected_quick_question = suggested_questions[1]
        if st.button(suggested_questions[3], width='stretch'):
            selected_quick_question = suggested_questions[3]
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("role") == "assistant" and message.get("source"):
                model_info = message.get("model", "Unknown")
                st.caption(f"Answer source: {message['source']} | Model: {model_info}")
    
    # Chat input
    chat_input_value = st.chat_input("Ask about AppDynamics configuration, properties, or troubleshooting...")
    display_input = chat_input_value
    request_input = chat_input_value

    if not display_input and get_all_properties:
        display_input = "Get Node Properties"
        request_input = display_input
    if not display_input and selected_quick_question:
        display_input = selected_quick_question
        request_input = _expand_quick_question(selected_quick_question)
    
    if display_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": display_input
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(display_input)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                result = ask_chatbot_with_source(request_input)
            response = result.get("answer", "")
            source = result.get("source", "Unknown")
            model = result.get("model", "Unknown")
            st.markdown(response)
            st.caption(f"Answer source: {source} | Model: {model}")
        
        # Add assistant message to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response,
            "source": source,
            "model": model,
            "question": display_input,
            "feedback_status": None,
        })

    _render_feedback_for_last_answer()
    _render_feedback_admin()
    
    # Clear chat button
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
