ARG FAKE_REMOTE_GATEWAY_BASE=local/testhub-platform-backend-runtime:latest
FROM ${FAKE_REMOTE_GATEWAY_BASE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       docker-cli \
       docker.io \
       docker-compose \
       openssh-server \
    && rm -rf /var/lib/apt/lists/*

COPY gateway-entrypoint.sh /usr/local/bin/fake-remote-gateway-entrypoint
COPY bootstrap-runtime.sh /usr/local/bin/fake-remote-bootstrap-runtime

RUN chmod +x /usr/local/bin/fake-remote-gateway-entrypoint /usr/local/bin/fake-remote-bootstrap-runtime \
    && mkdir -p /var/run/sshd /AIOps/apps /AIOps/releases \
    && printf '#!/bin/sh\nexec docker compose "$@"\n' > /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

EXPOSE 22

ENTRYPOINT ["/usr/local/bin/fake-remote-gateway-entrypoint"]
