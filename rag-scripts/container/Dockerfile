FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    git curl unzip 

# Install aws cli
RUN curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip' && unzip awscliv2.zip && ./aws/install

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Ramalama
RUN curl -fsSL https://ramalama.ai/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

# Copy files into /app
COPY links.txt vectorize.sh entrypoint.sh parallel_download.py /app/

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/vectorize.sh

# Set workdir
WORKDIR /app

# Install download script deps
RUN uv init .
RUN uv add pip-system-certs aiohttp

# Default entrypoint
ENTRYPOINT ["./entrypoint.sh"]
