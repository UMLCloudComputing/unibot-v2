# unibot-v2 Discord Bot

A Discord bot that integrates with an LLM orchestrator to provide AI-powered conversations. The bot responds to mentions, maintains conversation history per user via Redis, and supports slash commands for session management.

## Features

- **Mention Responses**: Responds when the bot is mentioned (`@bot`)
- **Conversation History**: Stores last 10 messages per user in Redis with 1-hour TTL
- **Long Response Handling**: Automatically sends responses >2000 characters as a file attachment
- **Slash Commands**:
  - `/clear`: Clears your conversation history
  - `/get_history`: Retrieves your conversation history as a text file
- **Robust Error Handling**: Graceful degradation with informative error messages
- **Kubernetes Ready**: Includes deployment manifests for production use

## Architecture

### Core Components

1. **Discord Client** (`DiscordLLMBot` class): Extends `discord.Client` with message content intent
2. **Message Handling Flow**:
   - Listens for bot mentions
   - Cleans mention from message content
   - Shows typing indicator during processing
   - Fetches LLM response from orchestrator
   - Sends response back (with 2000-char limit handling)
3. **LLM Integration** (`fetch_llm_response` function):
   - Retrieves conversation history from Redis
   - Sends request to Open WebUI-compatible orchestrator endpoint
   - Stores updated history back in Redis
   - Handles timeouts and connection errors
4. **Session Management** (Redis-based):
   - Key format: `session:{user_id}`
   - Stores last 10 messages with 1-hour expiration

### Key Dependencies

- `discord.py`: Discord API wrapper
- `aiohttp`: Async HTTP client for orchestrator communication
- `redis`: Redis client for session storage
- `python-dotenv`: Environment variable loading
- `uv`: Fast Python package installer/dependency manager

## Setup

### Environment Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Activate virtual environment:

   ```bash
   source .venv/bin/activate
   ```

3. Install in development mode (if needed):

   ```bash
   pip install -e .
   ```

### Environment Variables

Create a `.env` file based on `.env.example` and configure:

- `DISCORD_TOKEN`: Discord bot token
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `ORCHESTRATOR_URL`: URL of the LLM orchestrator service (default: `http://localhost:8001/v1/chat`)

## Running the Bot

### Direct Execution

```bash
python app/main.py
# or
uv run app/main.py
```

### Docker

```bash
# Build
docker build -t unibot-discord .

# Run
docker run --env-file .env unibot-discord
```

### Docker Compose (from project root)

```bash
docker-compose up
```

### Kubernetes

Apply the manifests:

```bash
kubectl apply -f k8s/k8s.yaml
```

Note: You must create a secret named `bot-secrets` in the `discord-bot` namespace containing:

- Key: `discord-token`
- Value: Your Discord bot token

## Slash Commands

| Command | Description |
|---------|-------------|
| `/clear` | Clears your conversation history (ephemeral response) |
| `/get_history` | Retrieves your conversation history as a text file attachment (ephemeral) |

## Deployment Artifacts

- `Dockerfile`: Multi-stage build using Astral's uv image
- `docker-compose.yaml`: Service definition (located in project root)
- `k8s/k8s.yaml`: Kubernetes deployment manifests including:
  - Namespace: `discord-bot`
  - ConfigMap: `bot-config` (REDIS_URL, ORCHESTRATOR_URL)
  - Deployment: `discord-bot` (1 replica, resource limits/responses)

## Development

### Adding New Slash Commands

Decorate async functions with `@bot.tree.command()`:

```python
@bot.tree.command(name="example", description="An example command")
async def example_command(interaction: discord.Interaction):
    await interaction.response.send_message("Hello world!")
```

### Modifying LLM Parameters

Adjust the payload in `fetch_llm_response()` function in `app/main.py`.

### Changing History Limits

Modify the `save_history()` function parameters (currently 10 messages, 1-hour TTL).

### Updating Dependencies

Edit `pyproject.toml` and run:

```bash
uv lock
uv sync
```

## Error Handling & Resilience

- Timeout handling for LLM requests (90 seconds)
- Graceful degradation with user-friendly error messages
- Comprehensive logging via standard library logging
- Note: Redis connection failure would require manual inspection (no retry logic shown)

## Testing

Currently no formal test suite exists. Manual testing approaches:

1. Run the bot locally and test in a Discord development server
2. Use environment variables pointing to local/test services:
   - Set `ORCHESTRATOR_URL` to the orchestrator URL endpoint
   - Set `REDIS_URL` to local Redis instance
   - Use a test `DISCORD_TOKEN` from a bot account in a test server

## License

This project is part of the unibot-v2 suite. Please see the root repository for licensing information.

