ARG PYTHON_BASE=docker.m.daocloud.io/library/python:3.11-slim

FROM ${PYTHON_BASE} AS wheel-builder

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY requirements/runtime/core.txt /build/core.txt

RUN pip install --index-url "${PIP_INDEX_URL}" --upgrade pip \
    && pip wheel --index-url "${PIP_INDEX_URL}" --wheel-dir /wheels -r /build/core.txt

FROM ${PYTHON_BASE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=backend.settings_container \
    APP_PORT=8000 \
    TESTHUB_RUNTIME_ROLE=core

WORKDIR /app

COPY --from=wheel-builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r /dev/null \
    && pip install --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

LABEL org.testhub.runtime.role="backend-core" \
      org.testhub.runtime.tools="none"

CMD ["python3"]
