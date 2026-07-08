# unibot-v2 Streamlit Client

A Streamlit-based chat interface for the unibot-v2 unified orchestrator API gateway, featuring conversation history management and an optimized landing page UX.

## Features

### Conversation History
- **Persistent Conversations**: All conversations are stored in browser session state using `st.session_state`
- **Conversation Selector**: Dropdown menu in the top-left header to switch between conversations
- **New Conversation Button**: "+ New Conversation" button to start fresh chats
- **Auto-generated Titles**: Conversations automatically get titles from the first user message
- **Message History**: Full conversation history persists within the browser session

### Landing Page
- Clean, focused initial view with suggested topic pills
- Centered chat input for first-time interactions
- Legal disclaimer accessible via button
- Automatic transition to chat view after first interaction

### Chat Interface
- Standard conversational layout with user/assistant message bubbles
- Streaming-style responses with "Working..." spinner
- Follow-up questions supported via persistent chat input

## Architecture

This application follows the client-server model:

- **Streamlit App**: Acts as the client UI
- **Orchestrator API Gateway**: Provides the unibot-v2 backend functionality (LangGraph/LangChain agent)
- **Session State**: Manages conversation history in-browser using `st.session_state`

## Local Development

### Prerequisites
- Python 3.9+
- Access to unibot-v2 orchestrator API (default: `http://localhost:8001/v1/chat`)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd unibot-v2/streamlit
   ```

2. Create virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

### Configuration

Set the orchestrator API URL via environment variable:
```bash
export ORCHESTRATOR_API_URL="http://your-orchestrator-url/v1/chat"
```
Or create a `.env` file:
```
ORCHESTRATOR_API_URL=http://localhost:8001/v1/chat
```

### Running the Application

```bash
streamlit run app/streamlit_app.py
```

The application will be available at `http://localhost:8501`

## Usage

### Starting a Conversation
1. On first visit, you'll see the landing page with suggested topics
2. Either:
   - Type a question in the chat input and press Enter
   - Click one of the suggested topic pills
3. After your first interaction, the landing page transitions to the chat view

### Managing Conversations
- **Switch Conversations**: Use the dropdown in the top-left header
- **New Conversation**: Click the "+ New Conversation" button in the header
- **View History**: All messages in the selected conversation are displayed in the chat area

### Continuing a Conversation
- Type follow-up questions in the chat input at the bottom
- The assistant responds with context from the full conversation history
- Conversation title updates automatically after your first message

## How It Works

### Conversation Management
1. On initial load, the app creates an empty conversation
2. The header contains:
   - **Conversation Selector**: Dropdown showing all conversations by title
   - **+ New Conversation**: Button to create a blank conversation
3. Selecting a different conversation from the dropdown instantly loads its message history
4. Starting a new conversation clears landing page states and begins fresh

### Title Generation
- New conversations start with title "New conversation"
- After the first user message, the title automatically updates to that message (truncated to 30 characters with ellipsis if longer)

### Session Storage
- All conversation data is stored in `st.session_state`:
  - `conversations`: List of conversation objects (`{id, title, messages}`)
  - `current_conversation_id`: ID of the actively viewed conversation
  - `messages`: Reference to the current conversation's messages (for compatibility)
- Data persists for the browser session duration (until tab is closed/refreshed)

### API Integration
- Sends requests to the orchestrator API at `ORCHESTRATOR_API_URL`
- Payload includes current message and conversation history
- Handles timeouts up to 240 seconds for deep agentic processing
- Displays errors for API failures or network issues

## File Structure
```
streamlit/
├── app/
│   ├── streamlit_app.py      # Main Streamlit application
│   └── .streamlit/           # Streamlit configuration
├── Dockerfile                # Containerization
├── docker-compose.yaml       # Deployment configuration
├── k8s/                      # Kubernetes manifests
└── README.md                 # This file
```

## Customization

### Modifying Suggested Topics
Edit the `SUGGESTIONS` dictionary in `streamlit_app.py`:
```python
SUGGESTIONS = {
    ":blue[:material/school:] Tell me about UMass Lowell": (
        "What is UMass Lowell, what is its campus culture like, and what are its signature programs?"
    ),
    // Add more suggestions as needed
}
```

### Changing Appearance
- Page config is set via `st.set_page_config()` at the top of the file
- Logo image URL can be modified in the `st.image()` call
- Colors and layout follow Streamlit's default theming

## Deployment

### Docker
```bash
docker build -t unibot-v2-streamlit .
docker run -p 8501:8501 -e ORCHESTRATOR_API_URL="http://host.docker.internal:8001/v1/chat" unibot-v2-streamlit
```

### Kubernetes
See the `k8s/` directory for deployment manifests.

## Notes
- Conversation history is stored only in browser memory (session state)
- Refreshing the browser tab will clear all conversations
- For persistent storage across sessions, a backend implementation would be required