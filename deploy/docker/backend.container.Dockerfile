ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_RUNTIME_BASE}

WORKDIR /app

COPY manage.py /app/manage.py
COPY backend /app/backend
COPY apps /app/apps
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh
COPY deploy/docker/verify_backend_core_contract.py /app/deploy/docker/verify_backend_core_contract.py

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static /app/init-seed \
    && python /app/deploy/docker/verify_backend_core_contract.py

EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
