ARG PYTHON_BASE=docker.m.daocloud.io/library/python:3.11-slim

FROM ${PYTHON_BASE} AS protector

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src

ARG PYARMOR_VERSION=pyarmor
ARG PYARMOR_OPTIONS=
ARG PYARMOR_LICENSE_REQUIRED=0
ARG PYARMOR_MAX_SCRIPT_BYTES=30000
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=

RUN set -eu; \
    pip_args="--index-url ${PIP_INDEX_URL}"; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then pip_args="$pip_args --trusted-host ${PIP_TRUSTED_HOST}"; fi; \
    pip install $pip_args --upgrade pip \
    && pip install $pip_args "${PYARMOR_VERSION}"

COPY manage.py /src/manage.py
COPY backend /src/backend
COPY apps /src/apps
COPY tools /src/tools
COPY deploy/protection/prepare_pyarmor_sources.py /src/deploy/protection/prepare_pyarmor_sources.py

RUN --mount=type=secret,id=pyarmor_license,target=/tmp/pyarmor-license,required=false \
    set -eu; \
    if [ -s /tmp/pyarmor-license ]; then \
        pyarmor reg /tmp/pyarmor-license; \
    elif [ "${PYARMOR_LICENSE_REQUIRED}" = "1" ]; then \
        echo "PyArmor license is required but was not provided." >&2; \
        exit 1; \
    fi; \
    python /src/deploy/protection/prepare_pyarmor_sources.py \
        --src /src \
        --armor-src /armor-src \
        --protected /protected \
        --max-script-bytes "${PYARMOR_MAX_SCRIPT_BYTES}" \
        --summary-file /protected/protection-summary.txt; \
    cd /armor-src; \
    pyarmor gen -O /protected ${PYARMOR_OPTIONS} -r manage.py backend apps; \
    find /protected -type d -name '__pycache__' -prune -exec rm -rf {} +

FROM scratch
COPY --from=protector /protected /protected
