#!/usr/bin/env bash
set -euo pipefail

REGISTRY_HOST=""
REGISTRY_PORT="5443"
DATA_ROOT="/AIOps/data/testhub-release-registry"
CONTAINER_NAME="testhub-release-registry"
BIND_IP="0.0.0.0"
CERT_DAYS="3650"
FORCE_REGENERATE_CERT=0

log() {
  printf '%s %s\n' "[registry-bootstrap]" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  remote_bootstrap_registry.sh --registry-host <host-or-ip> [--registry-port 5443] [--data-root /AIOps/data/testhub-release-registry] [--container-name testhub-release-registry] [--bind-ip 0.0.0.0] [--cert-days 3650] [--force-regenerate-cert]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --registry-host)
      REGISTRY_HOST="$2"
      shift 2
      ;;
    --registry-port)
      REGISTRY_PORT="$2"
      shift 2
      ;;
    --data-root)
      DATA_ROOT="$2"
      shift 2
      ;;
    --container-name)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --bind-ip)
      BIND_IP="$2"
      shift 2
      ;;
    --cert-days)
      CERT_DAYS="$2"
      shift 2
      ;;
    --force-regenerate-cert)
      FORCE_REGENERATE_CERT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ -z "$REGISTRY_HOST" ]; then
  usage >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || { printf 'docker command not found.\n' >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { printf 'openssl command not found.\n' >&2; exit 1; }

CERT_DIR="$DATA_ROOT/certs"
STORE_DIR="$DATA_ROOT/data"
TMP_DIR="$DATA_ROOT/tmp"
CERT_FILE="$CERT_DIR/registry.crt"
KEY_FILE="$CERT_DIR/registry.key"
OPENSSL_CONFIG="$TMP_DIR/openssl.cnf"

mkdir -p "$CERT_DIR" "$STORE_DIR" "$TMP_DIR"

if [ "$FORCE_REGENERATE_CERT" = "1" ]; then
  rm -f "$CERT_FILE" "$KEY_FILE"
fi

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  log "Generating self-signed TLS certificate for $REGISTRY_HOST:$REGISTRY_PORT"
  {
    printf '[req]\n'
    printf 'distinguished_name = dn\n'
    printf 'x509_extensions = v3_req\n'
    printf 'prompt = no\n'
    printf '[dn]\n'
    printf 'CN = %s\n' "$REGISTRY_HOST"
    printf '[v3_req]\n'
    printf 'subjectAltName = @alt_names\n'
    printf 'keyUsage = digitalSignature,keyEncipherment\n'
    printf 'extendedKeyUsage = serverAuth\n'
    printf '[alt_names]\n'
    if printf '%s' "$REGISTRY_HOST" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
      printf 'IP.1 = %s\n' "$REGISTRY_HOST"
    else
      printf 'DNS.1 = %s\n' "$REGISTRY_HOST"
    fi
  } > "$OPENSSL_CONFIG"

  openssl req -x509 -nodes -newkey rsa:4096 \
    -days "$CERT_DAYS" \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -config "$OPENSSL_CONFIG"
fi

if ! docker image inspect registry:2 >/dev/null 2>&1; then
  log "Pulling registry:2 image"
  docker pull registry:2
fi

if docker ps -a --format '{{.Names}}' | grep -Fx "$CONTAINER_NAME" >/dev/null 2>&1; then
  log "Removing existing registry container: $CONTAINER_NAME"
  docker rm -f "$CONTAINER_NAME"
fi

log "Starting registry container: $CONTAINER_NAME"
docker run -d \
  --restart unless-stopped \
  --name "$CONTAINER_NAME" \
  -p "$BIND_IP:$REGISTRY_PORT:5000" \
  -v "$STORE_DIR:/var/lib/registry" \
  -v "$CERT_DIR:/certs" \
  -e REGISTRY_HTTP_ADDR=0.0.0.0:5000 \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/registry.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/registry.key \
  registry:2 >/dev/null

sleep 2
docker ps --filter "name=$CONTAINER_NAME" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
printf 'Registry URL: https://%s:%s\n' "$REGISTRY_HOST" "$REGISTRY_PORT"
printf 'Registry CA certificate: %s\n' "$CERT_FILE"
