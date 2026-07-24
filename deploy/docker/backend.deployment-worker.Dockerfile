ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-deployment-runtime:latest
FROM ${BACKEND_RUNTIME_BASE}

ENV TESTHUB_RUNTIME_ROLE=deployment

WORKDIR /app

COPY manage.py /app/manage.py
COPY backend /app/backend
COPY apps /app/apps
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh
COPY deploy/release /app/deploy/release

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && find /app/deploy/release -type f -name "*.sh" -exec chmod +x {} \; \
    && mkdir -p /app/data /app/logs /app/media /app/static

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["worker"]
