ARG BACKEND_CORE_RUNTIME_BASE=local/testhub-platform-backend-core-runtime:latest
FROM ${BACKEND_CORE_RUNTIME_BASE}

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.aliyun.com/debian

ENV TESTHUB_RUNTIME_ROLE=document

COPY requirements/runtime/document.txt /tmp/document-requirements.txt

RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r /tmp/document-requirements.txt \
    && rm -f /tmp/document-requirements.txt \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       antiword \
       binutils \
       libarchive-tools \
       tesseract-ocr \
       tesseract-ocr-chi-sim \
       unar \
    && rm -rf /var/lib/apt/lists/*

LABEL org.testhub.runtime.role="document" \
      org.testhub.runtime.tools="antiword,archive,tesseract"
