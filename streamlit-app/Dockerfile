# Use the official uv image built on top of Debian slim
FROM ghcr.io/astral-sh/uv:debian-slim

# Set working directory
WORKDIR /app

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

# Expose port for Streamlit
EXPOSE 8501

ENTRYPOINT []

# Run the Streamlit app
CMD ["uv", "run", "streamlit", "run", "streamlit_app.py"]
