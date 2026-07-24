ARG PROTECTED_CODE_IMAGE=local/testhub-platform-backend-protected-code:latest
ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest

FROM ${PROTECTED_CODE_IMAGE} AS protected-code
FROM ${BACKEND_RUNTIME_BASE}

ARG TESTHUB_RUNTIME_ROLE=service
ENV TESTHUB_RUNTIME_ROLE=${TESTHUB_RUNTIME_ROLE}

WORKDIR /app

COPY --from=protected-code /protected/manage.py /app/manage.py
COPY --from=protected-code /protected/backend /app/backend
COPY --from=protected-code /protected/apps /app/apps
COPY --from=protected-code /protected/pyarmor_runtime_000000 /app/pyarmor_runtime_000000
COPY --from=protected-code /protected/protection-summary.txt /app/protection-summary.txt
COPY deploy/docker/entrypoint.sh /app/deploy/docker/entrypoint.sh
COPY tester.md /app/tester.md
COPY tester_pro.md /app/tester_pro.md
COPY requirement_writer.md /app/requirement_writer.md
COPY requirement_reviewer.md /app/requirement_reviewer.md
COPY document_requirement_writer.md /app/document_requirement_writer.md
COPY document_testcase_writer.md /app/document_testcase_writer.md

RUN chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static /app/playwright_snapshot \
    && test -f /app/pyarmor_runtime_000000/pyarmor_runtime.so

EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
