# =============================================================================
# University Operations AI Agent
#
# Single-container image: Streamlit UI (Layer 1) + LangGraph orchestration
# (Layer 2) + configurable LLM client (Layer 3) + tools/DB layer (Layer 4).
# =============================================================================
FROM python:3.11-slim

# Avoid .pyc clutter and ensure stdout/stderr are unbuffered (so logs show
# up immediately with `docker compose logs -f`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application code
COPY app ./app
COPY streamlit_app.py ./streamlit_app.py

# Build the bundled SQLite database (schema + sample data) inside the image
# as a build-time sanity check. At runtime, if DATABASE_PATH points to a
# (volume-mounted) path that does not yet exist, the app builds/seeds it
# automatically on first access (see app/db/connection.py::ensure_database).
RUN python -m app.db.init_db --force

# Create a non-root user and hand over ownership of the app directory
# (including the database file/dir, which must remain writable at runtime).
RUN useradd --create-home --uid 1000 agent && \
    mkdir -p /app/data && \
    chown -R agent:agent /app
USER agent

EXPOSE 8501

# Container health check - Streamlit exposes a lightweight health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').status == 200 else 1)"

CMD ["streamlit", "run", "streamlit_app.py"]
