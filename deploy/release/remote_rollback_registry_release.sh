#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR=""
IMAGE_TAG=""
HISTORY_DIR=""
COMPONENTS_CSV="backend,frontend"
REGISTRY_ENDPOINT=""
REGISTRY_NAMESPACE=""
RUN_SMOKE=0

log() {
  printf '%s %s\n' "[registry-rollback]" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  remote_rollback_registry_release.sh --runtime-dir <dir> [--image-tag <tag>] [--history-dir <dir>] [--components backend,frontend] [--registry-endpoint <host:port>] [--registry-namespace <path>] [--run-smoke]
EOF
}

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    docker compose "$@"
  fi
}

compose_runtime() {
  compose_cmd -p "$RUNTIME_PROJECT_NAME" --env-file .env -f docker-compose.offline.yml "$@"
}

load_env_file() {
  local env_file="$1"
  set -a
  # shellcheck disable=SC1090
  . <(sed '1s/^\xEF\xBB\xBF//; s/\r$//' "$env_file")
  set +a
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
    printf 'Missing image ref for rollback component.\n' >&2
    exit 1
  fi

  log "Pulling image: $image_ref"
  docker pull "$image_ref"

  for local_tag in "$@"; do
    [ -n "$local_tag" ] || continue
    docker tag "$image_ref" "$local_tag"
  done
}

write_current_release_env() {
  local current_release_env="$1"
  local update_image_tag="$2"
  local run_backend_init="$3"

  mkdir -p "$(dirname "$current_release_env")"
  {
    printf 'RELEASE_MODE=registry\n'
    printf 'RELEASE_TAG=%s\n' "$IMAGE_TAG"
    printf 'RELEASE_CREATED_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'COMPONENTS_CSV=%s\n' "$COMPONENTS_CSV"
    printf 'UPDATE_IMAGE_TAG=%s\n' "$update_image_tag"
    printf 'RUN_BACKEND_INIT=%s\n' "$run_backend_init"
    printf 'REGISTRY_ENDPOINT=%s\n' "$REGISTRY_ENDPOINT"
    printf 'REGISTRY_NAMESPACE=%s\n' "$REGISTRY_NAMESPACE"
    printf 'RECREATE_SERVICES="%s"\n' "$RECREATE_SERVICES"
    printf 'SMOKE_SERVICES="%s"\n' "$SMOKE_SERVICES"
    [ -n "${BACKEND_RUNTIME_IMAGE_REF:-}" ] && printf 'BACKEND_RUNTIME_IMAGE_REF=%s\n' "$BACKEND_RUNTIME_IMAGE_REF"
    [ -n "${BACKEND_IMAGE_REF:-}" ] && printf 'BACKEND_IMAGE_REF=%s\n' "$BACKEND_IMAGE_REF"
    [ -n "${FRONTEND_IMAGE_REF:-}" ] && printf 'FRONTEND_IMAGE_REF=%s\n' "$FRONTEND_IMAGE_REF"
    [ -n "${MYSQL_IMAGE_REF:-}" ] && printf 'MYSQL_IMAGE_REF=%s\n' "$MYSQL_IMAGE_REF"
    [ -n "${REDIS_IMAGE_REF:-}" ] && printf 'REDIS_IMAGE_REF=%s\n' "$REDIS_IMAGE_REF"
    [ -n "${AIDEV_RUNTIME_IMAGE_REF:-}" ] && printf 'AIDEV_RUNTIME_IMAGE_REF=%s\n' "$AIDEV_RUNTIME_IMAGE_REF"
    [ -n "${CODEX_RUNTIME_IMAGE_REF:-}" ] && printf 'CODEX_RUNTIME_IMAGE_REF=%s\n' "$CODEX_RUNTIME_IMAGE_REF"
    [ -n "${CLAUDE_RUNTIME_IMAGE_REF:-}" ] && printf 'CLAUDE_RUNTIME_IMAGE_REF=%s\n' "$CLAUDE_RUNTIME_IMAGE_REF"
  } > "$current_release_env"
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
    --registry-endpoint)
      REGISTRY_ENDPOINT="$2"
      shift 2
      ;;
    --registry-namespace)
      REGISTRY_NAMESPACE="$2"
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
CURRENT_RELEASE_ENV="$RUNTIME_DIR/releases/current.release.env"
HISTORY_ROOT="$RUNTIME_DIR/releases/history"
[ -f "$ENV_FILE" ] || { printf 'Missing env file: %s\n' "$ENV_FILE" >&2; exit 1; }

RUNTIME_PROJECT_NAME="$(get_env_value "$ENV_FILE" 'COMPOSE_PROJECT_NAME')"
[ -n "$RUNTIME_PROJECT_NAME" ] || RUNTIME_PROJECT_NAME="$(basename "$RUNTIME_DIR")"
CONTAINER_PREFIX_VALUE="$(get_env_value "$ENV_FILE" 'CONTAINER_PREFIX')"
[ -n "$CONTAINER_PREFIX_VALUE" ] || CONTAINER_PREFIX_VALUE="testhub"

if [ -f "$CURRENT_RELEASE_ENV" ]; then
  if [ -z "$REGISTRY_ENDPOINT" ]; then
    REGISTRY_ENDPOINT="$(get_env_value "$CURRENT_RELEASE_ENV" 'REGISTRY_ENDPOINT')"
  fi
  if [ -z "$REGISTRY_NAMESPACE" ]; then
    REGISTRY_NAMESPACE="$(get_env_value "$CURRENT_RELEASE_ENV" 'REGISTRY_NAMESPACE')"
  fi
fi

if [ -n "$HISTORY_DIR" ]; then
  [ -f "$HISTORY_DIR/.env.before" ] || { printf 'Missing history env backup: %s/.env.before\n' "$HISTORY_DIR" >&2; exit 1; }
  cp "$HISTORY_DIR/.env.before" "$ENV_FILE"
  if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG="$(grep '^IMAGE_TAG=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true)"
  fi
fi

if [ -z "$IMAGE_TAG" ]; then
  printf 'Missing image tag for registry rollback.\n' >&2
  exit 1
fi

if [ -z "$REGISTRY_ENDPOINT" ] || [ -z "$REGISTRY_NAMESPACE" ]; then
  printf 'Missing registry endpoint or namespace for registry rollback.\n' >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK_HISTORY_DIR="$HISTORY_ROOT/${STAMP}_rollback_to_${IMAGE_TAG}"
mkdir -p "$ROLLBACK_HISTORY_DIR"
cp "$ENV_FILE" "$ROLLBACK_HISTORY_DIR/.env.before"
printf '%s\n' "$COMPONENTS_CSV" > "$ROLLBACK_HISTORY_DIR/components.txt"
if [ -n "$HISTORY_DIR" ]; then
  printf '%s\n' "$HISTORY_DIR" > "$ROLLBACK_HISTORY_DIR/source_history_dir.txt"
fi

BACKEND_RUNTIME_IMAGE_REF=""
BACKEND_IMAGE_REF=""
FRONTEND_IMAGE_REF=""
MYSQL_IMAGE_REF=""
REDIS_IMAGE_REF=""
AIDEV_RUNTIME_IMAGE_REF=""
CODEX_RUNTIME_IMAGE_REF=""
CLAUDE_RUNTIME_IMAGE_REF=""
RECREATE_SERVICES=""
SMOKE_SERVICES=""

case ",${COMPONENTS_CSV}," in
  *,backend-runtime,*)
    BACKEND_RUNTIME_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/backend-runtime:$IMAGE_TAG"
    pull_and_tag "$BACKEND_RUNTIME_IMAGE_REF" \
      "local/testhub-platform-backend-runtime:$IMAGE_TAG" \
      "local/testhub-platform-backend-runtime:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,backend,*)
    BACKEND_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/backend:$IMAGE_TAG"
    pull_and_tag "$BACKEND_IMAGE_REF" \
      "local/testhub-platform-backend-bundle:$IMAGE_TAG"
    RECREATE_SERVICES="testhub-backend testhub-celery-worker testhub-ai-dev-worker"
    SMOKE_SERVICES="testhub-backend testhub-celery-worker testhub-ai-dev-worker"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,frontend,*)
    FRONTEND_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/frontend:$IMAGE_TAG"
    pull_and_tag "$FRONTEND_IMAGE_REF" \
      "local/testhub-platform-frontend-bundle:$IMAGE_TAG"
    if [ -n "$RECREATE_SERVICES" ]; then
      RECREATE_SERVICES="$RECREATE_SERVICES testhub-frontend"
      SMOKE_SERVICES="$SMOKE_SERVICES testhub-frontend"
    else
      RECREATE_SERVICES="testhub-frontend"
      SMOKE_SERVICES="testhub-frontend"
    fi
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,mysql,*)
    MYSQL_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/mysql:$IMAGE_TAG"
    pull_and_tag "$MYSQL_IMAGE_REF" \
      "local/testhub-mysql-bundle:8.0"
    if [ -n "$RECREATE_SERVICES" ]; then
      RECREATE_SERVICES="testhub-mysql $RECREATE_SERVICES"
      SMOKE_SERVICES="testhub-mysql $SMOKE_SERVICES"
    else
      RECREATE_SERVICES="testhub-mysql"
      SMOKE_SERVICES="testhub-mysql"
    fi
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,redis,*)
    REDIS_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/redis:$IMAGE_TAG"
    pull_and_tag "$REDIS_IMAGE_REF" \
      "local/testhub-redis-bundle:7-alpine"
    if [ -n "$RECREATE_SERVICES" ]; then
      RECREATE_SERVICES="testhub-redis $RECREATE_SERVICES"
      SMOKE_SERVICES="testhub-redis $SMOKE_SERVICES"
    else
      RECREATE_SERVICES="testhub-redis"
      SMOKE_SERVICES="testhub-redis"
    fi
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,aidev-runtime,*)
    AIDEV_RUNTIME_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/ai-dev:$IMAGE_TAG"
    pull_and_tag "$AIDEV_RUNTIME_IMAGE_REF" \
      "testhub/ai-dev:$IMAGE_TAG" \
      "testhub/ai-dev:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,codex-runtime,*)
    CODEX_RUNTIME_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/codex-runtime:$IMAGE_TAG"
    pull_and_tag "$CODEX_RUNTIME_IMAGE_REF" \
      "local/testhub-platform-codex-runtime:$IMAGE_TAG" \
      "local/testhub-platform-codex-runtime:latest"
    ;;
esac

case ",${COMPONENTS_CSV}," in
  *,claude-runtime,*)
    CLAUDE_RUNTIME_IMAGE_REF="$REGISTRY_ENDPOINT/$REGISTRY_NAMESPACE/claude-runtime:$IMAGE_TAG"
    pull_and_tag "$CLAUDE_RUNTIME_IMAGE_REF" \
      "local/testhub-platform-claude-runtime:$IMAGE_TAG" \
      "local/testhub-platform-claude-runtime:latest"
    ;;
esac

if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
  sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$IMAGE_TAG/" "$ENV_FILE"
else
  printf '\nIMAGE_TAG=%s\n' "$IMAGE_TAG" >> "$ENV_FILE"
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
    log "Running backend init during rollback"
    compose_runtime up -d --no-deps --force-recreate testhub-backend-init
    wait_container_exit_zero "$(service_container_name testhub-backend-init)"
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

write_current_release_env "$CURRENT_RELEASE_ENV" \
  "$(case ",${COMPONENTS_CSV}," in *,backend,*|*,frontend,*) printf '1' ;; *) printf '0' ;; esac)" \
  "$(case ",${COMPONENTS_CSV}," in *,backend,*) printf '1' ;; *) printf '0' ;; esac)"
cp "$ENV_FILE" "$ROLLBACK_HISTORY_DIR/.env.after"

if [ "$RUN_SMOKE" = "1" ]; then
  bash "$RUNTIME_DIR/deploy/release/remote_smoke_verify.sh" \
    --runtime-dir "$RUNTIME_DIR" \
    --components "$COMPONENTS_CSV"
fi

log "Registry rollback completed. Active IMAGE_TAG=$IMAGE_TAG"
