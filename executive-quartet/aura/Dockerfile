FROM python:3.12-slim

LABEL org.opencontainers.image.title="Aura - Identity Guardian"
LABEL org.opencontainers.image.description="Executive Quartet member: identity verification, drift detection, and memory integration."
LABEL org.opencontainers.image.vendor="core-engineering-system"

RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY memory_client.py .

RUN mkdir -p /var/log/ledger && \
    chown -R coreengine:coreengine /var/log/ledger

USER coreengine
EXPOSE 8084

CMD ["python", "-u", "main.py"]
