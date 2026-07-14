FROM python:3.12-slim

LABEL org.opencontainers.image.title="Track A - Control Loop"
LABEL org.opencontainers.image.description="C-P-A Model: Context and Planning brain. Holds RAG context, runs the planning loop, emits action requests to Track B."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

# Install only what's needed — no build tools in runtime
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Create ledger and RAG directories
RUN mkdir -p /var/log/ledger /rag/docs /policy && \
    chown -R coreengine:coreengine /var/log/ledger

USER coreengine
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]

CMD ["python", "-u", "main.py"]
