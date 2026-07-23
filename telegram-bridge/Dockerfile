FROM python:3.12-slim

LABEL org.opencontainers.image.title="Sheryl-Telegram Bridge"
LABEL org.opencontainers.image.description="Webhook bridge between Telegram Bot API and Sheryl ingestion pipeline."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Create ledger directory
RUN mkdir -p /var/log/ledger && \
    chown -R coreengine:coreengine /var/log/ledger

USER coreengine
EXPOSE 8088

CMD ["python", "-u", "main.py"]
