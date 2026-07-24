set -euo pipefail

PROJECT_ID="${1:-1}"
BUNDLE_ROOT="${BUNDLE_ROOT:-/workspace-release}"
BUNDLE_PATH_PREFIX="${BUNDLE_PATH_PREFIX:-/workspace-release}"
REFRESH_RUNTIME_SCRIPTS="${REFRESH_RUNTIME_SCRIPTS:-0}"

docker compose -f "deploy/local-fake-remote/docker-compose.ssh-gateway.yml" up -d --build
docker exec testhub-fake-remote-ssh /usr/local/bin/fake-remote-bootstrap-runtime --force
docker exec testhub-local-backend python manage.py bootstrap_fake_remote_target --project-id "$PROJECT_ID"

set -- \
  docker exec testhub-local-backend \
  python manage.py bootstrap_local_release_artifacts \
  --project-id "$PROJECT_ID" \
  --bundle-root "$BUNDLE_ROOT" \
  --bundle-path-prefix "$BUNDLE_PATH_PREFIX"

if [ "$REFRESH_RUNTIME_SCRIPTS" = "1" ]; then
  set -- "$@" --refresh-runtime-scripts
fi

"$@"
