# Streamlit Front-End UI

The Streamlit front-end provides a user-friendly chat interface for interacting with the unibot-v2 orchestrator. It is designed to be simple and intuitive, featuring a landing page with suggested topics and a conversational chat view.

## Overview

The UI is built with Streamlit and connects to the orchestrator API gateway at the endpoint specified by the `ORCHESTRATOR_API_URL` environment variable (default: `http://localhost:8001/v1/chat`).

## Key Components

### 1. Landing Page View

When the user first opens the application (or after restarting the conversation), they are presented with a landing page that includes:

- A centered chat input box labeled "Ask a question..."
- A set of suggested topic pills (see [Suggested Topics](#suggested-topics))

The application remains in this view until the user either types a question and presses Enter or clicks one of the suggested topics.

### 2. Suggested Topics

The landing page displays four predefined suggestions, each with an icon and a label. When a suggestion is clicked, the corresponding predefined prompt is sent to the orchestrator.

The suggestions are defined in the code as:

| Display Label | Actual Prompt Sent to LLM |
|---------------|---------------------------|
| :blue[:material/school:] Tell me about UMass Lowell | "What is UMass Lowell, what is its campus culture like, and what are its signature programs?" |
| :green[:material/menu_book:] Course Catalog Help | "How do I look up course prerequisites and catalog codes classes?" |
| :orange[:material/calendar_month:] Upcoming Semester Schedules | "Where can I find academic calendar dates, enrollment deadlines, and schedule grids for the upcoming term?" |
| :violet[:material/person:] Who is Rowdy? | "Who is Rowdy the River Hawk? Tell me about the school mascot and history." |

### 3. Active Conversation View

After the user initiates an interaction (by asking a question or clicking a suggestion), the UI transitions to the active conversation view. This view includes:

- A persistent header with a "Restart" button (icon: :material/refresh:) that clears the conversation history and returns to the landing page.
- A chat interface that displays messages from both the user and the assistant.
- A chat input box at the bottom labeled "Ask a follow-up question..." for continuing the conversation.

### 4. Conversation Handling

- User messages and assistant responses are stored in Streamlit's session state (`st.session_state.messages`).
- When the user sends a message, the UI:
  1. Immediately displays the user message.
  2. Shows a spinner with the text "Working..." while waiting for the orchestrator's response.
  3. Sends a POST request to the orchestrator API with the user message and the conversation history.
  4. Upon receiving a successful response (status code 200), displays the assistant's message and appends both the user and assistant messages to the session state.
  5. Clears the initial question and selected suggestion session states to prevent loop interception bugs and triggers a rerun to update the UI.

If the orchestrator returns an error or is unreachable, an error message is displayed.

## Configuration

The Streamlit UI can be configured via a `config.toml` file located in the `.streamlit` directory. The current configuration sets the theme and widget styles.

Example `.streamlit/config.toml`:
```toml
[theme]
base = "light"
textColor = "#3f3f46"
primaryColor = "#60a5fa"
backgroundColor = "#fafafa"
secondaryBackgroundColor = "#ffffff"

showWidgetBorder = true
borderColor = "#eeeef0"

font = "Inter:https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap"
baseFontWeight = 400
baseFontSize = 14

headingFont = "Inter:https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap"
headingFontWeights = [600, 600, 600, 200, 600, 200]
headingFontSizes = ["3rem", "1.5rem", "1rem", "1rem", "0.8rem", "0.8rem"]
```

## Environment Variables

- `ORCHESTRATOR_API_URL`: The URL of the orchestrator API endpoint. Defaults to `http://localhost:8001/v1/chat`.

## Running the Streamlit UI

The Streamlit UI is typically run via Docker or Kubernetes as part of the unibot-v2 deployment. For local development, you can run:

```bash
streamlit run streamlit/app/streamlit_app.py
```

Make sure to set the `ORCHESTRATOR_API_URL` environment variable if your orchestrator is running on a different address.

## Notes

- The UI uses a high timeout (240 seconds) for requests to the orchestrator to accommodate deep agentic multi-tool loop execution.
- The UI escapes dollar signs (`$`) in user messages to prevent Markdown rendering issues.
- The "Restart" button clears the conversation history and returns the UI to the landing page view.
