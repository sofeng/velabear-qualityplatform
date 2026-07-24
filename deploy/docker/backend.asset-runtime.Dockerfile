ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG SCHEMACRAWLER_VERSION=17.11.3
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.aliyun.com/debian
ARG SCHEMACRAWLER_SHA256=aef46dbf9463b41473deef7b7fda91b7e0308dce51ac6e3692f246951620639d
ARG SCHEMACRAWLER_DOWNLOAD_BASE=https://ghfast.top/https://github.com/schemacrawler/SchemaCrawler-Installers/releases/download

ENV TESTHUB_RUNTIME_ROLE=asset \
    SCHEMACRAWLER_COMMAND=/opt/schemacrawler/bin/schemacrawler.sh

COPY requirements/runtime/asset.txt /tmp/asset-requirements.txt

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources

RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r /tmp/asset-requirements.txt \
    && rm -f /tmp/asset-requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       default-jre-headless \
       git \
       universal-ctags \
       unzip \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/var/cache/testhub-downloads \
    archive="/var/cache/testhub-downloads/schemacrawler-${SCHEMACRAWLER_VERSION}-bin.zip" \
    && if ! echo "${SCHEMACRAWLER_SHA256}  ${archive}" | sha256sum -c -; then \
         curl --fail --location --continue-at - \
           --connect-timeout 30 --max-time 1800 --retry 10 --retry-all-errors \
           "${SCHEMACRAWLER_DOWNLOAD_BASE}/v${SCHEMACRAWLER_VERSION}/schemacrawler-${SCHEMACRAWLER_VERSION}-bin.zip" \
           --output "${archive}"; \
       fi \
    && echo "${SCHEMACRAWLER_SHA256}  ${archive}" | sha256sum -c - \
    && rm -rf /opt/schemacrawler /tmp/schemacrawler-install \
    && mkdir -p /opt/schemacrawler /tmp/schemacrawler-install \
    && unzip -q "${archive}" -d /tmp/schemacrawler-install \
    && cp -R "$(find /tmp/schemacrawler-install -mindepth 1 -maxdepth 1 -type d | head -n 1)"/* /opt/schemacrawler/ \
    && chmod +x /opt/schemacrawler/bin/schemacrawler.sh \
    && rm -rf /tmp/schemacrawler-install

LABEL org.testhub.runtime.role="asset" \
      org.testhub.runtime.tools="git,ctags,semgrep,schemacrawler"
