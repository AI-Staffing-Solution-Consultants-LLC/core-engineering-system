FROM python:3.12-slim

LABEL org.opencontainers.image.title="Sheryl — Memory & Context Agent"
LABEL org.opencontainers.image.description="Executive Quartet member. Manages persistent context via MemoryPlugin, consults RAG corpus, runs planning loop."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

# Install only what's needed — no build tools in runtime
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries (pre-staged into this directory by deploy-gcr.sh)
COPY src/ ./src/
COPY memory_client.py .

# Copy the service module
COPY main.py .

# Create ledger and RAG directories, set ownership
RUN mkdir -p /var/log/ledger /rag/docs && \
    chown -R coreengine:coreengine /var/log/ledger /rag/docs /app

USER coreengine
EXPOSE 8083

CMD ["python", "-u", "main.py"]
