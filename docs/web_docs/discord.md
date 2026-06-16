# Discord Bot Usage and Design

This document provides detailed usage instructions and design information for the unibot-v2 Discord bot component.

## Overview

The unibot-v2 Discord bot is a Python-based application that enables users to interact with AI language models through Discord. When mentioned in a Discord channel (`@bot`), the bot processes the user's query through the orchestrator service, which in turn communicates with LLMs, vector databases, and external MCP (Model Context Protocol) tools to generate informed responses.

## Key Features

### Core Functionality

- **Mention-based Interaction**: The bot only responds when explicitly mentioned, reducing noise in busy channels
- **Persistent Conversation History**: Each user's conversation history is stored in Redis with a 1-hour TTL, limited to the last 10 exchanges
- **Long Response Handling**: Responses exceeding Discord's 2000-character limit are automatically truncated and provided as a file attachment
- **Slash Commands**:
  - `/clear`: Clears the user's conversation history (ephemeral response)
  - `/get_history`: Retrieves the user's conversation history as a downloadable text file (ephemeral)

### Technical Implementation

- Built with `discord.py` library using the commands extension
- Asynchronous architecture using `asyncio` for non-blocking I/O
- Redis-backed session storage for conversation history
- HTTP communication with the orchestrator service via `aiohttp`
- Comprehensive error handling with user-friendly error messages
- Structured logging using Python's standard logging module

## System Architecture

### Component Diagram

```
[Discord User] 
       ↓ (mentions @bot)
[Discord Bot Instance] 
       ↓ (HTTP POST)
[Orchestrator Service] 
       ↓ (integrates with)
[LLM (Ollama)] + [Vector Store (Milvus)] + [MCP Tools]
       ↓
[Response] ← (returns to) [Discord Bot] ← (sends to) [Discord User]
```

### Data Flow

1. User sends a message mentioning the bot (`@bot Hello!`)
2. Bot's `on_message` event triggers, filtering out self-sent messages
3. Bot checks if it was mentioned in the message
4. If mentioned:
   - Cleans the mention from the message content
   - Shows typing indicator in Discord channel
   - Retrieves user's conversation history from Redis
   - Sends HTTP request to orchestrator service with:
     - User ID
     - Cleaned prompt
     - Conversation history
   - Orchestrator processes request through its AI stack
   - Bot receives response and updates Redis history
   - Response sent back to Discord (with 2000-char limit handling)
5. Slash commands (`/clear`, `/get_history`) operate directly on Redis data

### Session Management

- **Storage**: Redis database
- **Key Format**: `session:{user_id}` where `user_id` is the Discord user's snowflake ID
- **Value**: JSON array of message objects, each containing:
  - `"role"`: Either `"user"` or `"assistant"`
  - `"content"`: The message text
- **Limits**:
  - Maximum 10 message pairs (20 total messages) stored
  - 1-hour time-to-live (TTL) for automatic cleanup
- **Functions**:
  - `get_history(user_id)`: Retrieves and parses history from Redis
  - `save_history(user_id, history)`: Stores trimmed history (last 10) with TTL

### Error Handling

The bot implements multiple layers of error handling:

1. **Orchestrator Communication**:
   - Timeout after 90 seconds for LLM requests
   - HTTP status code checking
   - Exception catching for network issues
   - User-friendly error messages returned to Discord
2. **Discord API Limits**:
   - Automatic file attachment for responses >2000 characters
   - Truncation with ellipsis for displayed portion
3. **Redis Operations**:
   - Assumes Redis is available (no retry logic shown in current implementation)
   - Would require manual intervention if Redis becomes unavailable

## Usage Instructions

### Prerequisites

Before running the Discord bot, ensure you have:

1. A Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
2. Access to a running unibot-v2 orchestrator service
3. Access to a Redis instance
4. Python 3.9+ installed (or Docker for containerized deployment)

### Environment Configuration

Create a `.env` file in the discord directory with the following variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `DISCORD_TOKEN` | Your Discord bot token (required) | *Must be set* |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `ORCHESTRATOR_URL` | URL of the LLM orchestrator service | `http://localhost:8001/v1/chat` |

### Running the Bot

#### Local Development

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Activate virtual environment:

   ```bash
   source .venv/bin/activate
   ```

3. Run the bot:

   ```bash
   python app/main.py
   # or
   uv run app/main.py
   ```

#### Docker Container

1. Build the image:

   ```bash
   docker build -t unibot-discord .
   ```

2. Run the container:

   ```bash
   docker run --env-file .env unibot-discord
   ```

#### Docker Compose (from project root)

```bash
docker-compose up
```

#### Kubernetes Deployment

1. Ensure you have a secret named `bot-secrets` in the `discord-bot` namespace containing:
   - Key: `discord-token`
   - Value: Your Discord bot token
2. Apply the manifests:

   ```bash
   kubectl apply -f k8s/k8s.yaml
   ```

### Slash Commands

Once the bot is running and connected to Discord, users can interact with it using these slash commands:

| Command | Description | Response Type |
|---------|-------------|---------------|
| `/clear` | Clears your conversation history | Ephemeral (visible only to you) |
| `/get_history` | Retrieves your conversation history as a text file | Ephemeral (visible only to you) |

## Design Considerations

### Intentionally Limited Scope

The bot focuses exclusively on:

- Processing mentions (`@bot`)
- Providing conversational AI responses
- Managing per-user session history

It does not:

- Monitor or respond to all channel messages (only mentions)
- Provide moderation or administrative functions
- Implement complex command hierarchies beyond basic slash commands

### Extensibility Points

1. **Adding New Slash Commands**: Decorate async functions with `@bot.tree.command()`

   ```python
   @bot.tree.command(name="example", description="An example command")
   async def example_command(interaction: discord.Interaction):
       await interaction.response.send_message("Hello world!")
   ```

2. **Modifying LLM Parameters**: Adjust the payload in `fetch_llm_response()` function in `app/main.py`

3. **Changing History Limits**: Modify the `save_history()` function parameters (currently 10 messages, 1-hour TTL)

4. **Updating Dependencies**: Edit `pyproject.toml` and run:

   ```bash
   uv lock
   uv sync
   ```

### Deployment Considerations

- **Resource Usage**: Designed for low resource consumption (suitable for small VMs or containers)
- **Scaling**: Horizontal scaling is limited by Redis session storage; multiple instances require shared Redis
- **Security**:
  - Discord token must be kept secret (use Kubernetes secrets or Docker secrets)
  - No direct user input validation beyond mention filtering (relies on orchestrator for input sanitization)
  - Communication with orchestrator should ideally use internal network endpoints in production

## Relationship to Other Components

### Orchestrator Service

The Discord bot acts as a thin client layer that:

- Transforms Discord messages into orchestrator-compatible requests
- Transforms orchestrator responses back into Discord-compatible messages
- Manages user-specific state (conversation history) independently of the orchestrator

### Kubernetes Deployment

When deployed via Kubernetes:

- Runs in the `discord-bot` namespace
- Uses ConfigMap `bot-config` for `REDIS_URL` and `ORCHESTRATOR_URL`
- Uses Secret `bot-secrets` for `DISCORD_TOKEN`
- Configured with resource requests/limits:
  - Requests: 512Mi memory, 250m CPU
  - Limits: 1Gi memory, 500m CPU
- Includes liveness and readiness probes on `/health` endpoint (though the bot doesn't explicitly expose this - note: this might need verification)

## Maintenance and Troubleshooting

### Logging

The bot outputs structured logs to stdout with the format:

```
TIMESTAMP | LEVEL     | MESSAGE
```

Log level is set to INFO by default and can be adjusted by modifying the `logging.basicConfig()` call in `main.py`.

### Common Issues

1. **Bot Not Responding**:
   - Verify the bot is online in Discord (green dot)
   - Check logs for startup errors
   - Confirm `DISCORD_TOKEN` is correct in `.env`
   - Ensure the bot has permission to read messages and send messages in the channel

2. **No Response to Mentions**:
   - Check bot logs for "Mention received" entries
   - Verify orchestrator service is reachable (`ORCHESTRATOR_URL`)
   - Check Redis connectivity
   - Look for timeout or connection errors in logs

3. **History Not Persisting**:
   - Verify Redis is running and accessible
   - Check `REDIS_URL` in `.env` or ConfigMap
   - Look for Redis connection errors in bot logs

### Health Checks

While the bot doesn't expose a dedicated health endpoint, you can verify it's functioning by:

1. Checking if it responds to pings in Discord (should show as online)
2. Monitoring logs for regular activity
3. Testing with a simple mention and verifying response

## Future Enhancements

Potential areas for future development include:

- Adding more sophisticated command groups (e.g., admin commands)
- Implementing rate limiting per user
- Adding support for direct messages (DMs) in addition to channel mentions
- Implementing richer message formatting (embeds, buttons, etc.)
- Adding metrics export (Prometheus-compatible)
- Implementing retry logic for transient failures (Redis, orchestrator)
