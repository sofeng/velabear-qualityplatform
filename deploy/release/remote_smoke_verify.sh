#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR=""
COMPONENTS_CSV="backend,frontend"

log() {
  printf '%s %s\n' "[fast-smoke]" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  remote_smoke_verify.sh --runtime-dir <dir> [--components backend,frontend]
EOF
}

get_env_value() {
  local env_file="$1"
  local key="$2"
  grep "^${key}=" "$env_file" | tail -n 1 | cut -d= -f2- || true
}

service_container_name() {
  local service_name="$1"
  local suffix="${service_name#testhub-}"
  printf '%s-%s\n' "$CONTAINER_PREFIX_VALUE" "$suffix"
}

load_env_file() {
  local env_file="$1"
  set -a
  # shellcheck disable=SC1090
  . <(sed '1s/^\xEF\xBB\xBF//; s/\r$//' "$env_file")
  set +a
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime-dir)
      RUNTIME_DIR="$2"
      shift 2
      ;;
    --components)
      COMPONENTS_CSV="$2"
      shift 2
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

if [ -z "$RUNTIME_DIR" ]; then
  usage >&2
  exit 1
fi

COMPOSE_DIR="$RUNTIME_DIR/deploy/docker"
ENV_FILE="$COMPOSE_DIR/.env"
[ -f "$ENV_FILE" ] || { printf 'Missing env file: %s\n' "$ENV_FILE" >&2; exit 1; }

CONTAINER_PREFIX_VALUE="$(get_env_value "$ENV_FILE" 'CONTAINER_PREFIX')"
[ -n "$CONTAINER_PREFIX_VALUE" ] || CONTAINER_PREFIX_VALUE="testhub"

load_env_file "$ENV_FILE"

SMOKE_HOST="${SMOKE_HOST:-127.0.0.1}"
BACKEND_SMOKE_URL="${BACKEND_SMOKE_URL:-http://$SMOKE_HOST:${BACKEND_HOST_PORT}/admin/login/}"
FRONTEND_SMOKE_URL="${FRONTEND_SMOKE_URL:-http://$SMOKE_HOST:${FRONTEND_HOST_PORT}/}"
SMOKE_MAX_ATTEMPTS="${SMOKE_MAX_ATTEMPTS:-60}"
SMOKE_INTERVAL_SECONDS="${SMOKE_INTERVAL_SECONDS:-2}"

assert_running() {
  local container_name="$1"
  local max_attempts="${2:-30}"
  local interval="${3:-2}"
  local attempt=1

  while [ "$attempt" -le "$max_attempts" ]; do
    local running
    running="$(docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null || true)"
    if [ "$running" = "true" ]; then
      return 0
    fi
    sleep "$interval"
    attempt=$((attempt + 1))
  done

  printf 'Container not running: %s\n' "$container_name" >&2
  docker ps -a --filter "name=$container_name" || true
  return 1
}

assert_healthy_or_running() {
  local container_name="$1"
  local max_attempts="${2:-30}"
  local interval="${3:-2}"
  local attempt=1

  while [ "$attempt" -le "$max_attempts" ]; do
    local health
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_name" 2>/dev/null || true)"
    case "$health" in
      healthy|running)
        return 0
        ;;
    esac
    sleep "$interval"
    attempt=$((attempt + 1))
  done

  printf 'Container not healthy: %s (%s)\n' "$container_name" "$health" >&2
  docker ps -a --filter "name=$container_name" || true
  return 1
}

dump_container_logs() {
  local container_name="$1"
  log "Last logs for $container_name"
  docker logs "$container_name" --tail 120 2>&1 || true
}

wait_http_ok() {
  local name="$1"
  local url="$2"
  local max_attempts="${3:-$SMOKE_MAX_ATTEMPTS}"
  local interval="${4:-$SMOKE_INTERVAL_SECONDS}"
  local attempt=1
  local last_output=""

  while [ "$attempt" -le "$max_attempts" ]; do
    if last_output="$(curl -fsS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}' "$url" 2>&1)"; then
      case "$last_output" in
        2*|3*)
          log "$name is ready: $url ($last_output)"
          return 0
          ;;
      esac
    fi

    log "Waiting for $name: attempt $attempt/$max_attempts, url=$url, result=$last_output"
    sleep "$interval"
    attempt=$((attempt + 1))
  done

  printf '%s did not become ready: %s. Last result: %s\n' "$name" "$url" "$last_output" >&2
  return 1
}

case ",${COMPONENTS_CSV}," in
  *,mysql,*|*,backend,*)
    assert_healthy_or_running "$(service_container_name testhub-mysql)"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,redis,*|*,backend,*)
    assert_healthy_or_running "$(service_container_name testhub-redis)"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,backend,*)
    backend_container="$(service_container_name testhub-backend)"
    celery_container="$(service_container_name testhub-celery-worker)"
    aidev_container="$(service_container_name testhub-ai-dev-worker)"
    assert_running "$backend_container"
    assert_running "$celery_container"
    assert_running "$aidev_container"
    log "Checking backend admin login page"
    if ! wait_http_ok "backend" "$BACKEND_SMOKE_URL"; then
      dump_container_logs "$backend_container"
      dump_container_logs "$celery_container"
      dump_container_logs "$aidev_container"
      exit 1
    fi
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,frontend,*)
    frontend_container="$(service_container_name testhub-frontend)"
    assert_running "$frontend_container"
    log "Checking frontend root"
    if ! wait_http_ok "frontend" "$FRONTEND_SMOKE_URL"; then
      dump_container_logs "$frontend_container"
      exit 1
    fi
    ;;
esac

log "Smoke verification passed for components: $COMPONENTS_CSV"
