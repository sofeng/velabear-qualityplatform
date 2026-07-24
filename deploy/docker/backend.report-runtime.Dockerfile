ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG APT_MIRROR=https://mirrors.aliyun.com/debian

ENV TESTHUB_RUNTIME_ROLE=report \
    ALLURE_HOME=/opt/allure \
    PATH=/opt/allure/bin:${PATH}

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY allure /opt/allure
RUN sed -i 's/\r$//' /opt/allure/bin/allure \
    && chmod +x /opt/allure/bin/allure

LABEL org.testhub.runtime.role="report" \
      org.testhub.runtime.tools="allure,java"
