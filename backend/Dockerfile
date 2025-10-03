FROM python:3.12-slim-trixie

WORKDIR /app

# uv binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libc-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# nur Projekt-Metadaten zuerst für Caching
COPY pyproject.toml uv.lock ./

# Dependencies installieren
RUN uv sync --locked

# Quellcode reinkopieren
COPY src/ src/

EXPOSE 8000

# Set environment for Docker
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_RELOAD=False

CMD ["uv", "run", "-m", "src.app", "--host", "0.0.0.0", "--port", "8000"]
