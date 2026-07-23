FROM python:3.12-slim

LABEL org.opencontainers.image.title="agency-agents daemon"
LABEL org.opencontainers.image.description="Phase-5 NEXUS-Sprint daemon skeleton. Team-spawn coordinator with isolation contract. Port-bind OFF by default (human gate #11)."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security (non-root: coreengine)
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

# Install only what's needed — no build tools in runtime
RUN pip install --no-cache-dir flask

COPY main.py .
COPY teams.json .

# Create tmpfs mount point for per-team ephemeral ledger
# tmpfs /var/ledger — isolation contract enforced at runtime by teams.json
RUN mkdir -p /var/ledger && \
    chown -R coreengine:coreengine /var/ledger

USER coreengine
EXPOSE 8082

# Default CMD: skeleton mode (no port-bind). Override with --serve to bind.
CMD ["python", "-u", "main.py"]
