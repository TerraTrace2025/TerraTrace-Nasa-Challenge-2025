FROM python:3.12-slim-trixie

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make libc-dev libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata
COPY pyproject.toml uv.lock ./

# Install uv to manage dependencies
RUN pip install --upgrade pip \
    && pip install uv gunicorn "uvicorn[standard]"

# Create virtualenv (optional) and generate requirements.txt
RUN uv venv create \
    && uv sync --locked \
    && uv export > requirements.txt

# Install dependencies via pip from generated requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/

# Expose port
EXPOSE 8050

# Environment variables
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_RELOAD=False

# Start the Dash app via Gunicorn + UvicornWorker
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "src.app:server"]