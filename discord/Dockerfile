# Use the official uv image with Debian Trixie-slim
FROM ghcr.io/astral-sh/uv:debian-slim

# Set the working directory in the container
WORKDIR /app

# Install CA certificates for SSL/HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*


# Enable bytecode compilation and set timeouts
ENV UV_COMPILE_BYTECODE=1
ENV UV_HTTP_TIMEOUT=60
# Ensure Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# 1. Copy only the dependency files for caching
COPY pyproject.toml uv.lock ./

# 2. Pre-install dependencies 
# This creates the environment that 'uv run' will use later
RUN uv sync --frozen --no-install-project --no-dev

# 3. Copy the source code
# Note: Ensure the path matches your project structure (e.g., src/main.py)
COPY ./app /app

# 4. Final sync to include the project itself
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Replicate native behavior: 'uv run' handles the venv internally
CMD ["uv", "run", "main.py"]
