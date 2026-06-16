# Configuration

This document outlines the configurable variables for the unibot-v2 project.

## Discord Bot

In Kubernetes, the Discord bot configuration is set via the `bot-config` ConfigMap and the `bot-secrets` secret.

- `DISCORD_TOKEN`: The token for the Discord bot (stored in the `bot-secrets` secret).
- `ORCHESTRATOR_URL`: The URL of the orchestrator service.
- `REDIS_URL`: The URL for the Redis instance.

For local development, running via Docker Compose is preferred; configuration variables are set in `discord/docker-compose.yml`. As an alternative, the service can be run directly on bare metal with environment variables defined in a `.env` file in the `discord/` directory.

## Orchestrator

In Kubernetes, the orchestrator service configuration is set via the `api-orchestrator-config` ConfigMap.

- `OLLAMA_BASE_URL`: The base URL for the Ollama API endpoint.
- `MCP_SERVER_1`: The first MCP server, formatted as `"name,url"` (e.g., `uml-now-mcp,http://uml-now-mcp-svc.mcp.svc.cluster.local:8000/mcp`).
- `MCP_SERVER_2`: The second MCP server, formatted as `"name,url"` (e.g., `uml-search-mcp,http://uml-search-mcp-svc.mcp.svc.cluster.local:8000/mcp`).
- `OLLAMA_MODEL`: The name of the Ollama model to use for inference.

The orchestrator currently supports a maximum of two MCP servers via these variables.

For local development, running via Docker Compose is preferred; configuration variables are set directly in the `orchestrator/docker-compose.yml` file under the `environment` section. As an alternative, the service can be run directly on bare metal with environment variables defined in a `.env` file in the `orchestrator/` directory.

## Streamlit UI

In Kubernetes, the Streamlit UI configuration is set via the `streamlit-ui-config` ConfigMap.

- `ORCHESTRATOR_API_URL`: The URL of the orchestrator API endpoint.

For local development, running via Docker Compose is preferred; this variable is set in `streamlit/docker-compose.yml`. As an alternative, the service can be run directly on bare metal with the environment variable defined in a `.env` file in the `streamlit/` directory.

Additionally, the Streamlit theme can be customized in `streamlit/app/.streamlit/config.toml` (see [Streamlit theming documentation](https://docs.streamlit.io/library/api-reference/themes)).

## Notes

- When referencing external services (such as MCP servers, Ollama, etc.), please refer to their respective documentation for details on configuration and usage.
- In Kubernetes, the values for these variables are set in ConfigMaps (and secrets for sensitive data). The examples shown in the manifests are for reference only; replace them with your actual values.
- For Docker Compose deployments, variables are set directly in the respective `docker-compose.yml` files.
