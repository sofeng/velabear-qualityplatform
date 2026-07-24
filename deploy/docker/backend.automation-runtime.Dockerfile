ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.aliyun.com/debian

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TESTHUB_RUNTIME_ROLE=automation

COPY requirements/runtime/automation.txt /tmp/automation-requirements.txt

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r /tmp/automation-requirements.txt \
    && rm -f /tmp/automation-requirements.txt \
    && python -m playwright install --with-deps chromium \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       dbus-x11 \
       fcitx5 \
       fcitx5-chinese-addons \
       fluxbox \
       fonts-noto-cjk \
       novnc \
       websockify \
       xauth \
       x11vnc \
    && rm -rf /var/lib/apt/lists/*

LABEL org.testhub.runtime.role="automation" \
      org.testhub.runtime.tools="playwright-chromium,novnc,fcitx"
