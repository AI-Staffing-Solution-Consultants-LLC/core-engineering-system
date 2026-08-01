FROM node:22-slim AS builder

WORKDIR /app

COPY package*.json tsconfig.json ./
RUN npm ci
COPY src/ ./src/
RUN npm run build

# ── Runtime image ──────────────────────────────────────────────────
FROM node:22-slim

LABEL org.opencontainers.image.title="Web Interface Backend"
LABEL org.opencontainers.image.description="Node.js backend for the web interface. Serves API endpoints and proxies C-P-A service calls."
LABEL org.opencontainers.image.vendor="core-engineering-system"

# curl needed for Docker Compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY --from=builder /app/dist/ ./dist/

USER node
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:3001/healthz || exit 1

CMD ["node", "dist/index.js"]
