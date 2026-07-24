ARG PYTHON_BASE=docker.m.daocloud.io/library/python:3.11-slim
FROM ${PYTHON_BASE}
ARG SKIP_PIP_INSTALL=0
ARG SKIP_PLAYWRIGHT_INSTALL=0
ARG SCHEMACRAWLER_VERSION=17.11.3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DJANGO_SETTINGS_MODULE=backend.settings_container \
    APP_PORT=8000 \
    SCHEMACRAWLER_COMMAND=/opt/schemacrawler/bin/schemacrawler.sh

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       antiword \
       binutils \
       openssh-client \
       ca-certificates \
       curl \
       default-jre-headless \
       git \
       libarchive-tools \
       sshpass \
       tesseract-ocr \
       tesseract-ocr-chi-sim \
       unar \
       universal-ctags \
       unzip \
       wget \
       xauth \
    && rm -rf /var/lib/apt/lists/*

RUN if [ "$SKIP_PIP_INSTALL" = "1" ]; then \
        echo "Skipping pip install; reusing packages from base image."; \
    else \
        pip install --upgrade pip \
        && (pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /app/requirements.txt \
            || pip install -i https://pypi.org/simple -r /app/requirements.txt); \
    fi

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

RUN if [ "$SKIP_PLAYWRIGHT_INSTALL" = "1" ]; then \
        echo "Skipping Playwright browser install; reusing browsers from base image."; \
    else \
        python -m playwright install --with-deps chromium firefox webkit; \
    fi
