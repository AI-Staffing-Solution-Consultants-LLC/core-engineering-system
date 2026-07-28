FROM python:3.12-slim

LABEL org.opencontainers.image.title="Self-Remediation — OpenCode Execution Wrapper"
LABEL org.opencontainers.image.description="Receives remediation plans from Krieger, executes via OpenCode CLI (stubbed), and maintains tamper-evident ledger."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (main.py, auditor.py, health-hooks.py, telemetry, steward, RAG, and src/ directory for ledger)
COPY main.py .
COPY auditor.py .
COPY health-hooks.py .
COPY telemetry.py .
COPY knowledge_steward.py .
COPY rag_connector.py .
COPY --chown=coreengine:coreengine src/ ./src/

# Create ledger directory
RUN mkdir -p /var/log/ledger && \
    chown -R coreengine:coreengine /var/log/ledger

# OpenCode CLI — installed but NOT auto-executed.
# Real remediation requires human approval before wiring OpenCode.
# COPY --from=opencode-builder /usr/local/bin/opencode /usr/local/bin/opencode

USER coreengine
EXPOSE 8087

CMD ["python", "-u", "main.py"]
