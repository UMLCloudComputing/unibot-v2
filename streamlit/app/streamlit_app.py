#!/usr/bin/env python3
"""
Streamlit Client for unibot-v2
Connects to a unified orchestrator API gateway with an optimized landing page UX.
"""

import streamlit as st
import httpx
import os

# --- 1. Configurations & Constants ---
ORCHESTRATOR_API_URL = os.getenv(
    "ORCHESTRATOR_API_URL", "http://localhost:8001/v1/chat"
)

st.set_page_config(
    page_title="unibot-v2",
    page_icon="🎓",
    layout="centered",
)

st.image(
    "https://raw.githubusercontent.com/UMLCloudComputing/unibot-v2/refs/heads/main/images/unibot-v2-logo-light.png",
    use_container_width=True,
)

# Suggested prompt values mapped: "Display Label": "Actual Prompt Sent to LLM"
SUGGESTIONS = {
    ":blue[:material/school:] Tell me about UMass Lowell": (
        "What is UMass Lowell, what is its campus culture like, and what are its signature programs?"
    ),
    ":green[:material/menu_book:] Course Catalog Help": (
        "How do I look up course prerequisites and catalog codes classes?"
    ),
    ":orange[:material/calendar_month:] Upcoming Semester Schedules": (
        "Where can I find academic calendar dates, enrollment deadlines, and schedule grids for the upcoming term?"
    ),
    ":violet[:material/person:] Who is Rowdy?": (
        "Who is Rowdy the River Hawk? Tell me about the school mascot and history."
    ),
}

# --- 2. Initialize Session Tracking ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. Persistent Header with Structural Action Row ---
title_row = st.container(horizontal=True, vertical_alignment="bottom")

# Evaluate conditional runtime interaction states
user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)
user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)
user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)
has_message_history = len(st.session_state.messages) > 0

# --- 4. CONDITIONAL UI: Empty Landing Page View ---
if not user_first_interaction and not has_message_history:
    with st.container():
        # Renders chat input centered inside the blank landing page block
        st.chat_input("Ask a question...", key="initial_question")

        # Display suggestion options as clean selectable pills
        st.pills(
            label="Suggested topics:",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )

    st.stop()  # Halt interface building until an action initiates an interaction state change

# --- 5. CONDITIONAL UI: Active Conversation Thread View ---
# Render a clean conversational chat input fixed at the bottom of the viewport
user_message = st.chat_input("Ask a follow-up question...")

# Capture input when transitioning from the initial landing view
if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    elif user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

# Inject the "Restart" button into the shared persistent title header row
with title_row:

    def clear_conversation():
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

# Redraw historic messages saved to session memory
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. Orchestration Processing Engine Node ---
if user_message:
    # Escape character issues regarding Markdown rendering for raw currency or formatting strings
    user_message = user_message.replace("$", r"\$")

    # Render current message instantly to view stream
    with st.chat_message("user"):
        st.markdown(user_message)

    # Dispatch to Remote FastAPI LangGraph Stack Container
    with st.chat_message("assistant"):
        with st.spinner("Working..."):
            try:
                # Structure payload matching network contract requirements
                payload_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]

                request_body = {"message": user_message, "history": payload_history}

                response = httpx.post(
                    ORCHESTRATOR_API_URL,
                    json=request_body,
                    timeout=240.0,  # High timeout for deep agentic multi-tool loop execution
                )

                if response.status_code == 200:
                    data = response.json()
                    response_text = data["response"].get(
                        "content", "Error: No response generated."
                    )

                    with st.container():
                        st.markdown(response_text)

                    # Update local state memory to capture successful interactions
                    st.session_state.messages.append(
                        {"role": "user", "content": user_message}
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )

                    # Clear input keys to prevent loop interception bugs on structural reruns
                    st.session_state.initial_question = None
                    st.session_state.selected_suggestion = None
                    st.rerun()
                else:
                    st.error(
                        f"API System Fault ({response.status_code}): {response.text}"
                    )

            except httpx.RequestError as exc:
                st.error(f"API Orchestrator Gateway error: {str(exc)}")
