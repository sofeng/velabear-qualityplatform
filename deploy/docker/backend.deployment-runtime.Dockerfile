ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG APT_MIRROR=https://mirrors.aliyun.com/debian

ENV TESTHUB_RUNTIME_ROLE=deployment

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
       libarchive-tools \
       openssh-client \
       sshpass \
       wget \
    && rm -rf /var/lib/apt/lists/*

LABEL org.testhub.runtime.role="deployment" \
      org.testhub.runtime.tools="git,ssh,release-scripts"
