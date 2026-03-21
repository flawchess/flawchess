FROM node:24-alpine AS builder
WORKDIR /app
# Build context is project root — copy package files from frontend/ subdirectory
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.2 AS runtime
COPY --from=builder /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
