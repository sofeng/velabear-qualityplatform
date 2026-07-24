#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR=""
RELEASE_DIR=""
RUN_SMOKE=0

log() {
  printf '%s %s\n' "[registry-release]" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  remote_apply_registry_release.sh --runtime-dir <dir> --release-dir <dir> [--run-smoke]
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

load_env_file() {
  local env_file="$1"
  set -a
  # shellcheck disable=SC1090
  . <(sed '1s/^\xEF\xBB\xBF//; s/\r$//' "$env_file")
  set +a
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

pull_and_tag() {
  local image_ref="$1"
  shift

  if [ -z "$image_ref" ]; then
    printf 'Missing image ref for release component.\n' >&2
    exit 1
  fi

  log "Pulling image: $image_ref"
  docker pull "$image_ref"

  for local_tag in "$@"; do
    [ -n "$local_tag" ] || continue
    docker tag "$image_ref" "$local_tag"
  done
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime-dir)
      RUNTIME_DIR="$2"
      shift 2
      ;;
    --release-dir)
      RELEASE_DIR="$2"
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

if [ -z "$RUNTIME_DIR" ] || [ -z "$RELEASE_DIR" ]; then
  usage >&2
  exit 1
fi

COMPOSE_DIR="$RUNTIME_DIR/deploy/docker"
ENV_FILE="$COMPOSE_DIR/.env"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.offline.yml"
RELEASE_ENV="$RELEASE_DIR/release.env"
HISTORY_ROOT="$RUNTIME_DIR/releases/history"
CURRENT_RELEASE_ENV="$RUNTIME_DIR/releases/current.release.env"
RUNTIME_RELEASE_DIR="$RUNTIME_DIR/deploy/release"

[ -f "$ENV_FILE" ] || { printf 'Missing env file: %s\n' "$ENV_FILE" >&2; exit 1; }
[ -f "$COMPOSE_FILE" ] || { printf 'Missing compose file: %s\n' "$COMPOSE_FILE" >&2; exit 1; }
[ -f "$RELEASE_ENV" ] || { printf 'Missing release env: %s\n' "$RELEASE_ENV" >&2; exit 1; }

RUNTIME_PROJECT_NAME="$(get_env_value "$ENV_FILE" 'COMPOSE_PROJECT_NAME')"
[ -n "$RUNTIME_PROJECT_NAME" ] || RUNTIME_PROJECT_NAME="$(basename "$RUNTIME_DIR")"
CONTAINER_PREFIX_VALUE="$(get_env_value "$ENV_FILE" 'CONTAINER_PREFIX')"
[ -n "$CONTAINER_PREFIX_VALUE" ] || CONTAINER_PREFIX_VALUE="testhub"

load_env_file "$RELEASE_ENV"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HISTORY_DIR="$HISTORY_ROOT/${STAMP}_${RELEASE_TAG}"
mkdir -p "$HISTORY_DIR"
mkdir -p "$RUNTIME_RELEASE_DIR"
cp "$ENV_FILE" "$HISTORY_DIR/.env.before"
cp "$RELEASE_ENV" "$HISTORY_DIR/release.env"
cp "$RELEASE_DIR/runtime/deploy/release/remote_apply_registry_release.sh" "$RUNTIME_RELEASE_DIR/remote_apply_registry_release.sh"
cp "$RELEASE_DIR/runtime/deploy/release/remote_smoke_verify.sh" "$RUNTIME_RELEASE_DIR/remote_smoke_verify.sh"
cp "$RELEASE_DIR/runtime/deploy/release/remote_rollback_registry_release.sh" "$RUNTIME_RELEASE_DIR/remote_rollback_registry_release.sh"

CURRENT_IMAGE_TAG="$(grep '^IMAGE_TAG=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
printf '%s\n' "$CURRENT_IMAGE_TAG" > "$HISTORY_DIR/previous_image_tag.txt"

case ",${COMPONENTS_CSV}," in
  *,backend-runtime,*)
    pull_and_tag "${BACKEND_RUNTIME_IMAGE_REF:-}" \
      "local/testhub-platform-backend-runtime:$RELEASE_TAG" \
      "local/testhub-platform-backend-runtime:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,backend,*)
    pull_and_tag "${BACKEND_IMAGE_REF:-}" \
      "local/testhub-platform-backend-bundle:$RELEASE_TAG"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,frontend,*)
    pull_and_tag "${FRONTEND_IMAGE_REF:-}" \
      "local/testhub-platform-frontend-bundle:$RELEASE_TAG"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,mysql,*)
    pull_and_tag "${MYSQL_IMAGE_REF:-}" \
      "local/testhub-mysql-bundle:8.0"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,redis,*)
    pull_and_tag "${REDIS_IMAGE_REF:-}" \
      "local/testhub-redis-bundle:7-alpine"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,aidev-runtime,*)
    pull_and_tag "${AIDEV_RUNTIME_IMAGE_REF:-}" \
      "testhub/ai-dev:$RELEASE_TAG" \
      "testhub/ai-dev:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,codex-runtime,*)
    pull_and_tag "${CODEX_RUNTIME_IMAGE_REF:-}" \
      "local/testhub-platform-codex-runtime:$RELEASE_TAG" \
      "local/testhub-platform-codex-runtime:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,claude-runtime,*)
    pull_and_tag "${CLAUDE_RUNTIME_IMAGE_REF:-}" \
      "local/testhub-platform-claude-runtime:$RELEASE_TAG" \
      "local/testhub-platform-claude-runtime:latest"
    ;;
esac

if [ "${UPDATE_IMAGE_TAG:-0}" = "1" ]; then
  log "Updating IMAGE_TAG to $RELEASE_TAG"
  if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$RELEASE_TAG/" "$ENV_FILE"
  else
    printf '\nIMAGE_TAG=%s\n' "$RELEASE_TAG" >> "$ENV_FILE"
  fi
fi

cd "$COMPOSE_DIR"

case ",${COMPONENTS_CSV}," in
  *,mysql,*|*,redis,*)
    infra_services=()
    case ",${COMPONENTS_CSV}," in
      *,mysql,*) infra_services+=("testhub-mysql") ;;
    esac
    case ",${COMPONENTS_CSV}," in
      *,redis,*) infra_services+=("testhub-redis") ;;
    esac
    if [ "${#infra_services[@]}" -gt 0 ]; then
      log "Recreating infrastructure services: ${infra_services[*]}"
      compose_runtime up -d --force-recreate "${infra_services[@]}"
    fi
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,backend,*)
    if [ "${RUN_BACKEND_INIT:-0}" = "1" ]; then
      log "Running backend init for release $RELEASE_TAG"
      compose_runtime up -d --no-deps --force-recreate testhub-backend-init
      wait_container_exit_zero "$(service_container_name testhub-backend-init)"
    fi

    log "Recreating backend services"
    compose_runtime up -d --force-recreate testhub-backend testhub-celery-worker testhub-ai-dev-worker
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,frontend,*)
    log "Recreating frontend service"
    compose_runtime up -d --force-recreate testhub-frontend
    ;;
esac

mkdir -p "$(dirname "$CURRENT_RELEASE_ENV")"
cp "$RELEASE_ENV" "$CURRENT_RELEASE_ENV"
cp "$ENV_FILE" "$HISTORY_DIR/.env.after"

if [ "$RUN_SMOKE" = "1" ]; then
  log "Running smoke verification"
  bash "$RELEASE_DIR/runtime/deploy/release/remote_smoke_verify.sh" \
    --runtime-dir "$RUNTIME_DIR" \
    --components "$COMPONENTS_CSV"
fi

log "Registry release applied successfully: $RELEASE_TAG"
