FROM python:3.12-slim

LABEL org.opencontainers.image.title="Krieger — Incident Remediation Agent"
LABEL org.opencontainers.image.description="Receives incidents and proposes remediation plans for the Core Engineering System."
LABEL org.opencontainers.image.vendor="core-engineering-system"

RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN mkdir -p /var/log/ledger && \
    chown -R coreengine:coreengine /var/log/ledger

USER coreengine
EXPOSE 8086

CMD ["python", "-u", "main.py"]
