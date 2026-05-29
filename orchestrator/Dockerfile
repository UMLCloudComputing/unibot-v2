# Use the official uv image built on top of Debian slim Specifying the Python version explicitly guarantees reproducibility
FROM ghcr.io/astral-sh/uv:debian-slim

# Set the working directory inside the container
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# --- Optimization Configurations ---
# 1. Compile Python source files to bytecode (.pyc) for faster container startup times
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_DEV=1

# --- Dependency Installation ---
# Copy ONLY the lockfile and project configuration files first to maximize Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# --- Source Code Layer ---
# Copy the actual application code base into the container
COPY ./app /app

# Run a final sync to install your actual package code (without dev dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

# Place the generated virtual environment's executables directly onto the system PATH
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint back to an empty definition to allow standard CMD script execution
ENTRYPOINT []

# Expose the API port 
EXPOSE 8001

# Run the API application server by executing your api file
CMD ["uv", "run", "api.py"]
