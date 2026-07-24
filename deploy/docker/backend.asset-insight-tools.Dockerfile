ARG BACKEND_RUNTIME_BASE=local/testhub-platform-backend-runtime-fresh:latest
FROM ${BACKEND_RUNTIME_BASE}

ARG SCHEMACRAWLER_VERSION=17.11.3

ENV SCHEMACRAWLER_COMMAND=/opt/schemacrawler/bin/schemacrawler.sh

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       default-jre-headless \
       universal-ctags \
       unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --timeout 60 --retries 2 semgrep \
    || pip install --no-cache-dir --timeout 60 --retries 2 -i https://pypi.tuna.tsinghua.edu.cn/simple semgrep \
    || echo "semgrep install failed; asset scanner will fall back to internal rules."

RUN mkdir -p /opt/schemacrawler \
    && (curl --connect-timeout 30 --max-time 180 --retry 2 -L "https://github.com/schemacrawler/SchemaCrawler-Installers/releases/download/v${SCHEMACRAWLER_VERSION}/schemacrawler-${SCHEMACRAWLER_VERSION}-bin.zip" -o /tmp/schemacrawler.zip \
        && unzip -q /tmp/schemacrawler.zip -d /tmp/schemacrawler-install \
        && cp -R "$(find /tmp/schemacrawler-install -mindepth 1 -maxdepth 1 -type d | head -n 1)"/* /opt/schemacrawler/ \
        && rm -f /tmp/schemacrawler.zip \
        && rm -rf /tmp/schemacrawler-install \
        && chmod +x /opt/schemacrawler/bin/schemacrawler.sh) \
    || echo "SchemaCrawler install failed; asset scanner will fall back to information_schema."
