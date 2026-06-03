# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- Install dependencies: `uv sync` (uses the uv.lock file for reproducible installs)
- Activate virtual environment: `source .venv/bin/activate`
- Install in development mode: `pip install -e .` (if needed)

### Running the Bot
- Direct execution: `python src/main.py` or `uv run src/main.py`
- Docker build: `docker build -t unibot-discord .`
- Docker run: `docker run --env-file .env unibot-discord`
- Docker compose: `docker-compose up` (from project root)

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `DISCORD_TOKEN`: Discord bot token
- `OPEN_WEBUI_URL`: URL for Open WebUI API endpoint
- `OPEN_WEBUI_KEY`: API key for Open WebUI authentication
- `MODEL_ID`: Model identifier to use in Open WebUI
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)

### Testing
Currently no formal test suite exists. Manual testing approaches:
1. Run the bot locally and test in a Discord development server
2. Use environment variables pointing to local/test services:
   - Set `OPEN_WEBUI_URL` to local Open WebUI instance
   - Set `REDIS_URL` to local Redis instance
   - Use a test `DISCORD_TOKEN` from a bot account in a test server

## Code Architecture

### Core Components
1. **Bot Client** (`DiscordLLMBot` class):
   - Extends `discord.Client` with message content intent enabled
   - Sets up command tree for slash commands
   - Handles `on_message` event for bot mentions

2. **Message Handling Flow**:
   - Bot listens for messages where it's mentioned (`@bot`)
   - Cleans the mention from the message content
   - Sends typing indicator while processing
   - Calls `fetch_llm_response` to get LLM reply
   - Sends response back to Discord (with 2000 char limit handling)

3. **LLM Integration** (`fetch_llm_response` function):
   - Retrieves conversation history from Redis
   - Sends request to Open WebUI `/api/chat/completions` endpoint
   - Stores updated history back in Redis (10 message limit, 1hr expiry)
   - Handles timeouts and connection errors gracefully

4. **Session Management** (Redis-based):
   - `get_history(user_id)`: Retrieves JSON conversation history
   - `save_history(user_id, history)`: Stores last 10 messages with 1-hour TTL
   - Key format: `session:{user_id}`

5. **Slash Commands**:
   - `/clear`: Deletes user's session history from Redis

### Key Dependencies
- `discord.py`: Discord API wrapper
- `aiohttp`: Async HTTP client for Open WebUI communication
- `redis`: Redis client for session storage
- `python-dotenv`: Environment variable loading
- `uv`: Fast Python package installer/dependency manager

### Deployment Artifacts
- `Dockerfile`: Multi-stage build using Astral's uv image
- `docker-compose.yaml`: Service definition (referenced from project root)
- `k8s.yaml`: Kubernetes deployment manifests

### Error Handling & Resilience
- Timeout handling for LLM requests (90 seconds)
- Graceful degradation with user-friendly error messages
- Comprehensive logging via standard library logging
- Redis connection failure would require manual inspection (no retry logic shown)

## Common Workflows
1. Adding new slash commands: Decorate async functions with `@bot.tree.command()`
2. Modifying LLM parameters: Adjust payload in `fetch_llm_response`
3. Changing history limits: Modify `save_history` function parameters
4. Updating dependencies: Edit `pyproject.toml` and run `uv lock` then `uv sync`