ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-automation-runtime:latest
FROM ${BACKEND_RUNTIME_BASE}

ENV TESTHUB_RUNTIME_ROLE=automation

WORKDIR /app

COPY manage.py /app/manage.py
COPY backend /app/backend
COPY apps /app/apps
COPY tools/local_playwright_agent.py \
     tools/start_local_playwright_agent.ps1 \
     tools/start_local_playwright_agent.bat \
     tools/stop_local_playwright_agent.ps1 \
     tools/stop_local_playwright_agent.bat \
     tools/register_local_playwright_agent.ps1 \
     tools/testhub_agent_protocol.ps1 \
     tools/uninstall_local_playwright_agent.ps1 \
     tools/install_local_playwright_agent.ps1 \
     /app/local-agent-package/
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static /app/playwright_snapshot \
    && test -f /app/local-agent-package/local_playwright_agent.py \
    && test -f /app/local-agent-package/install_local_playwright_agent.ps1

EXPOSE 8000 9222-9262 6080-6120

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
