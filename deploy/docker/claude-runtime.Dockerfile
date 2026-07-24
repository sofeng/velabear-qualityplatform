ARG NODE_BASE=docker.m.daocloud.io/library/node:22-bookworm-slim
FROM ${NODE_BASE}

# Pin the Claude Code CLI for reproducible release builds (mirrors codex-runtime's
# pinned CODEX_CLI_VERSION). Override at build time with
# --build-arg CLAUDE_CLI_VERSION=<version>.
ARG CLAUDE_CLI_VERSION=2.1.210

ENV DEBIAN_FRONTEND=noninteractive \
    CLAUDE_CONFIG_DIR=/home/claude/.claude \
    HOME=/home/claude \
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
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}" \
    && useradd -m -d /home/claude -s /bin/bash claude \
    && mkdir -p /home/claude/.claude /workspace \
    && chown -R claude:claude /home/claude /workspace \
    && rm -rf /var/lib/apt/lists/*

USER claude
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]
