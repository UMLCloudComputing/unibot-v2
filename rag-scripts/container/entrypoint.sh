#!/bin/sh


# Append UID/GID ranges (optional if already in Dockerfile)
echo "raguser:100000:65536" >> /etc/subuid
echo "raguser:100000:65536" >> /etc/subgid

# Perform podman system migration at runtime
podman system migrate || true

# Core program
uv run parallel_download.py 
./vectorize.sh ecr rag-data
