# Build: the Quasar SPA into dist/spa.
FROM node:26.12.0-alpine AS build

WORKDIR /app

# Manifests first: the npm layer is reused until package-lock.json changes.
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
RUN npm run build

# Serve: unprivileged nginx (uid 101, port 8080).
FROM nginxinc/nginx-unprivileged:stable-alpine-slim

# The alpine base lags its package repo; take every fixed package now
# (same as co2-calculator). apk needs root.
USER root
RUN apk upgrade --no-cache && rm /etc/nginx/conf.d/default.conf
USER 101

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist/spa /usr/share/nginx/html

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
