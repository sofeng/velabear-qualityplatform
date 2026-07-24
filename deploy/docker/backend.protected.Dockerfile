ARG PROTECTED_CODE_IMAGE=local/testhub-platform-backend-protected-code:latest
ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest

FROM ${PROTECTED_CODE_IMAGE} AS protected-code
FROM ${BACKEND_RUNTIME_BASE}

ENV TESTHUB_RUNTIME_ROLE=core

WORKDIR /app

COPY --from=protected-code /protected/manage.py /app/manage.py
COPY --from=protected-code /protected/backend /app/backend
COPY --from=protected-code /protected/apps /app/apps
COPY --from=protected-code /protected/pyarmor_runtime_000000 /app/pyarmor_runtime_000000
COPY --from=protected-code /protected/protection-summary.txt /app/protection-summary.txt
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh
COPY deploy/docker/verify_backend_core_contract.py /app/deploy/docker/verify_backend_core_contract.py

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static /app/init-seed \
    && test -f /app/pyarmor_runtime_000000/pyarmor_runtime.so \
    && python /app/deploy/docker/verify_backend_core_contract.py

EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
