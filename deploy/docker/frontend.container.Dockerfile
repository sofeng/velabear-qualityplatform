ARG NODE_BASE=docker.m.daocloud.io/library/node:20-alpine
ARG NGINX_BASE=docker.m.daocloud.io/library/nginx:1.27-alpine

FROM ${NODE_BASE} AS build

WORKDIR /app/frontend
ENV NODE_OPTIONS=--max-old-space-size=4096

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend /app/frontend
RUN npm run build
RUN find /app/frontend/dist -type f -name "*.map" -delete \
    && find /app/frontend/dist -type f \( -name "*.js" -o -name "*.css" \) \
       -exec sed -i '/sourceMappingURL/d' {} +

FROM ${NGINX_BASE}

COPY deploy/docker/nginx.container.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
