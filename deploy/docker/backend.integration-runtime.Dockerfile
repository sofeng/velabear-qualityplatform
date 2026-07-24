ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.aliyun.com/debian

ENV TESTHUB_RUNTIME_ROLE=integration

COPY requirements/runtime/integration.txt /tmp/integration-requirements.txt

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r /tmp/integration-requirements.txt \
    && rm -f /tmp/integration-requirements.txt \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       git \
       openssh-client \
    && rm -rf /var/lib/apt/lists/*

LABEL org.testhub.runtime.role="integration" \
      org.testhub.runtime.tools="docker-api,git,ssh"
