# Multi-stage Docker build for OPSGuardian AI + ArmorIQ Control Center
# Stage 1: Build frontend and server bundle
FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY package*.json tsconfig.json vite.config.ts ./
RUN npm ci
COPY src/ ./src/
COPY index.html ./
COPY server.ts ./
RUN npm run build

# Stage 2: Production runtime image with Python 3.11+ and Node.js
FROM python:3.11-slim-bullseye AS runtime
WORKDIR /app

# Install Node.js runtime and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend & server bundle from builder
COPY --from=frontend-builder /app/dist ./dist
COPY --from=frontend-builder /app/node_modules ./node_modules
COPY --from=frontend-builder /app/package.json ./package.json

# Copy Python backend code
COPY python/ ./python/

# Default environment configuration
ENV NODE_ENV=production \
    PORT=3000 \
    PYTHON_PORT=8001 \
    PYTHON_BIN=python \
    AI_PROVIDER=deterministic \
    ARMORIQ_MODE=mock \
    DATABASE_URL=sqlite:///./opsguardian.db

EXPOSE 3000 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Start using server
CMD ["node", "dist/server.cjs"]
