FROM python:3.12-slim

LABEL org.opencontainers.image.title="Track B - Actuator"
LABEL org.opencontainers.image.description="C-P-A Model: Action layer. Receives tool-call requests from Track A, executes against the allowlist, returns results."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN mkdir -p /var/log/ledger /policy && \
    chown -R coreengine:coreengine /var/log/ledger

USER coreengine
EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8081/healthz')"]

CMD ["python", "-u", "main.py"]
