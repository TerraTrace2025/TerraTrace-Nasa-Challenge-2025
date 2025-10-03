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

# Copy project metadata first for caching
COPY pyproject.toml uv.lock ./

# Install uv (Python-based) and dependencies
RUN pip install --upgrade pip \
    && pip install uv

# Sync dependencies via uv
RUN uv sync --locked

# Copy source code
COPY src/ src/

# Expose port for FastAPI / Dash
EXPOSE 8000

# Set environment variables
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_RELOAD=False

# Command to run the app
CMD ["uv", "run", "-m", "src.app", "--host", "0.0.0.0", "--port", "8000"]
