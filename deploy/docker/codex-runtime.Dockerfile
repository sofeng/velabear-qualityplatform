ARG NODE_BASE=docker.m.daocloud.io/library/node:22-bookworm-slim
FROM ${NODE_BASE}

ARG CODEX_CLI_VERSION=0.88.0

ENV DEBIAN_FRONTEND=noninteractive \
    CODEX_HOME=/home/codex/.codex \
    HOME=/home/codex \
    NPM_CONFIG_UPDATE_NOTIFIER=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       curl \
       git \
       openssh-client \
       python3 \
       python3-pip \
       ripgrep \
       tini \
       procps \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       docker-ce-cli \
       docker-compose-plugin \
    && npm install -g "@openai/codex@${CODEX_CLI_VERSION}" \
    && useradd -m -d /home/codex -s /bin/bash codex \
    && mkdir -p /home/codex/.codex /workspace \
    && chown -R codex:codex /home/codex /workspace \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/docker/codex-openai-compat-proxy.py /usr/local/bin/testhub-codex-openai-compat-proxy

RUN chmod +x /usr/local/bin/testhub-codex-openai-compat-proxy

USER codex
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]
