#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR=""
IMAGE_TAG=""
HISTORY_DIR=""
COMPONENTS_CSV="backend,frontend"
RUN_SMOKE=0

log() {
  printf '%s %s\n' "[fast-rollback]" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  remote_rollback_release.sh --runtime-dir <dir> [--image-tag <tag>] [--history-dir <dir>] [--components backend,frontend] [--run-smoke]
EOF
}

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    docker compose "$@"
  fi
}

get_env_value() {
  local env_file="$1"
  local key="$2"
  grep "^${key}=" "$env_file" | tail -n 1 | cut -d= -f2- || true
}

compose_runtime() {
  compose_cmd -p "$RUNTIME_PROJECT_NAME" --env-file .env -f docker-compose.offline.yml "$@"
}

service_container_name() {
  local service_name="$1"
  local suffix="${service_name#testhub-}"
  printf '%s-%s\n' "$CONTAINER_PREFIX_VALUE" "$suffix"
}

wait_container_exit_zero() {
  local container_name="$1"
  local max_attempts="${2:-120}"
  local interval="${3:-2}"
  local attempt=1

  while [ "$attempt" -le "$max_attempts" ]; do
    local status
    status="$(docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null || true)"
    if [ "$status" = "exited" ]; then
      local exit_code
      exit_code="$(docker inspect -f '{{.State.ExitCode}}' "$container_name" 2>/dev/null || printf '1')"
      if [ "$exit_code" = "0" ]; then
        return 0
      fi
      docker logs "$container_name" --tail 200 || true
      return 1
    fi
    sleep "$interval"
    attempt=$((attempt + 1))
  done

  docker logs "$container_name" --tail 200 || true
  return 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime-dir)
      RUNTIME_DIR="$2"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --history-dir)
      HISTORY_DIR="$2"
      shift 2
      ;;
    --components)
      COMPONENTS_CSV="$2"
      shift 2
      ;;
    --run-smoke)
      RUN_SMOKE=1
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

if [ -z "$RUNTIME_DIR" ]; then
  usage >&2
  exit 1
fi

COMPOSE_DIR="$RUNTIME_DIR/deploy/docker"
ENV_FILE="$COMPOSE_DIR/.env"
[ -f "$ENV_FILE" ] || { printf 'Missing env file: %s\n' "$ENV_FILE" >&2; exit 1; }

RUNTIME_PROJECT_NAME="$(get_env_value "$ENV_FILE" 'COMPOSE_PROJECT_NAME')"
[ -n "$RUNTIME_PROJECT_NAME" ] || RUNTIME_PROJECT_NAME="$(basename "$RUNTIME_DIR")"
CONTAINER_PREFIX_VALUE="$(get_env_value "$ENV_FILE" 'CONTAINER_PREFIX')"
[ -n "$CONTAINER_PREFIX_VALUE" ] || CONTAINER_PREFIX_VALUE="testhub"

if [ -n "$HISTORY_DIR" ]; then
  [ -f "$HISTORY_DIR/.env.before" ] || { printf 'Missing history env backup: %s/.env.before\n' "$HISTORY_DIR" >&2; exit 1; }
  cp "$HISTORY_DIR/.env.before" "$ENV_FILE"
  if [ -f "$HISTORY_DIR/docker-compose.offline.yml.before" ]; then
    cp "$HISTORY_DIR/docker-compose.offline.yml.before" "$COMPOSE_DIR/docker-compose.offline.yml"
  fi
  IMAGE_TAG="$(grep '^IMAGE_TAG=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
fi

if [ -n "$IMAGE_TAG" ]; then
  if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$IMAGE_TAG/" "$ENV_FILE"
  else
    printf '\nIMAGE_TAG=%s\n' "$IMAGE_TAG" >> "$ENV_FILE"
  fi
fi

cd "$COMPOSE_DIR"

case ",${COMPONENTS_CSV}," in
  *,backend,*)
    log "Running backend init during rollback"
    compose_runtime up -d --no-deps --force-recreate testhub-backend-init
    wait_container_exit_zero "$(service_container_name testhub-backend-init)"
    log "Recreating backend services"
    compose_runtime up -d --no-deps --force-recreate testhub-backend testhub-celery-worker testhub-ai-dev-worker
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,frontend,*)
    log "Recreating frontend service"
    compose_runtime up -d --no-deps --force-recreate testhub-frontend
    ;;
esac

if [ "$RUN_SMOKE" = "1" ]; then
  bash "$RUNTIME_DIR/deploy/release/remote_smoke_verify.sh" \
    --runtime-dir "$RUNTIME_DIR" \
    --components "$COMPONENTS_CSV"
fi

log "Rollback completed. Active IMAGE_TAG=${IMAGE_TAG:-unchanged}"
