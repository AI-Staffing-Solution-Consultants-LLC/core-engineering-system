# Barry DO-Lobe Preservation Dockerfile
# Base image for DigitalOcean lead-generation container migration.
# ZERO CODE MODIFICATION — this image does not alter any Barry container code.
# The Dockerfile serves as a reproducible build manifest for the preserved container.
#
# Convention: matches core-engineering-system track-a/track-b Dockerfile patterns.
#   - python:3.12-slim base
#   - Non-root user "coreengine" (uid 1000)
#   - No application code COPY — preservation-only packaging

FROM python:3.12-slim

# Create non-root user (matching core-engineering-system convention)
RUN groupadd -r coreengine && useradd -r -g coreengine -u 1000 coreengine

# Preserved container metadata — NOT code modification
LABEL org.coreengine.preservation="barry-do-lobe"
LABEL org.coreengine.preservation.note="ZERO CODE MODIFICATION — as-is preservation"
LABEL org.coreengine.preservation.date="2026-07-21"

# Work directory placeholder (overridden by preserved image layers)
WORKDIR /app

# No application COPY, no CMD — this is a base manifest image.
# The actual Barry DO-Lobe container is preserved as-is via docker save/load.

USER coreengine
