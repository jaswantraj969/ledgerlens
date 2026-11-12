# Frontend: build with Node, serve with Caddy, which also proxies /api to the API service.
#   docker build -t ledgerlens-web frontend
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2.8-alpine
# Run as an unprivileged user: Caddy listens on 8080 and only needs its data and config dirs.
RUN addgroup -S -g 10002 web && adduser -S -D -H -u 10002 -G web web \n    && chown -R web:web /data /config
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
USER web
