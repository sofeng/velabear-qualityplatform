FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=backend.settings_deploy \
    APP_PORT=38000

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

RUN if [ -f /app/allure/bin/allure ]; then sed -i 's/\r$//' /app/allure/bin/allure && chmod +x /app/allure/bin/allure; fi \
    && chmod +x /app/deploy/docker/entrypoint.sh \
    && mkdir -p /app/data /app/logs /app/media /app/static

EXPOSE 38000

ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
