FROM python:3.12-slim-trixie

WORKDIR /app

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libc-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# uv binaries (optional, nur wenn du uv für andere Backends brauchst)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Project metadata for caching
COPY pyproject.toml uv.lock ./

# Install dependencies via uv
RUN uv sync --locked

# Copy source code
COPY src/ src/

# Expose Dash port
EXPOSE 8050

# Set environment for Docker
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_RELOAD=False

CMD ["uv", "run", "-m", "src.app", "--host", "0.0.0.0", "--port", "8050"]
