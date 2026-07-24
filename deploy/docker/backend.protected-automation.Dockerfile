ARG PROTECTED_CODE_IMAGE=local/testhub-platform-backend-protected-code:latest
ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-automation-runtime:latest

FROM ${PROTECTED_CODE_IMAGE} AS protected-code
FROM ${BACKEND_RUNTIME_BASE}

ENV TESTHUB_RUNTIME_ROLE=automation

WORKDIR /app

COPY --from=protected-code /protected/manage.py /app/manage.py
COPY --from=protected-code /protected/backend /app/backend
COPY --from=protected-code /protected/apps /app/apps
COPY --from=protected-code /protected/local-agent-package /app/local-agent-package
COPY --from=protected-code /protected/pyarmor_runtime_000000 /app/pyarmor_runtime_000000
COPY --from=protected-code /protected/protection-summary.txt /app/protection-summary.txt
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static /app/playwright_snapshot \
    && test -f /app/pyarmor_runtime_000000/pyarmor_runtime.so \
    && test -f /app/local-agent-package/local_playwright_agent.py \
    && test -f /app/local-agent-package/install_local_playwright_agent.ps1

EXPOSE 8000 9222-9262 6080-6120

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
