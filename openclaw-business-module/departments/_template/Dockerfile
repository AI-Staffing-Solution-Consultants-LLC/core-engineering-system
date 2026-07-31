FROM python:3.12-slim

LABEL org.opencontainers.image.title="<DEPARTMENT_NAME> — <DEPARTMENT_SLUG>"
LABEL org.opencontainers.image.description="OpenClaw Business Module — <PHASE_DESCRIPTION>"
LABEL org.opencontainers.image.vendor="core-engineering-system"

# Non-root user for container security
RUN groupadd -r coreengine && useradd -r -g coreengine -d /app coreengine

WORKDIR /app

# Install only what's needed — no build tools in runtime
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY *.json ./

USER coreengine
EXPOSE $PORT

CMD python -u main.py
