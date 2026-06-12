# ══════════════════════════════════════════
# Stage 1 — Builder
# Install all dependencies including build tools
# ══════════════════════════════════════════
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (layer caching)
COPY requirements-docker.txt .

# Install all dependencies into a separate location
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements-docker.txt

# ══════════════════════════════════════════
# Stage 2 — Runtime
# Copy only what's needed to run the app
# ══════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy only application code
COPY app/ ./app/
COPY main.py .

# Copy .env only if it exists (handled via docker run --env-file in production)
# Never bake secrets into the image

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]