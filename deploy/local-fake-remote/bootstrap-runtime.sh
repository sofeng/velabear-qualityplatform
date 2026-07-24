#!/usr/bin/env bash
set -euo pipefail

FORCE_SYNC_RUNTIME="${FAKE_REMOTE_FORCE_SYNC_RUNTIME:-0}"
REMOTE_RUNTIME_DIR="${FAKE_REMOTE_RUNTIME_DIR:-/AIOps/apps/testhub-platform-local-remote}"
TEMPLATE_ROOT="${FAKE_REMOTE_TEMPLATE_ROOT:-/workspace/deploy/local-fake-remote}"
WORKSPACE_ROOT="${FAKE_REMOTE_WORKSPACE_ROOT:-/workspace}"

if [ "${1:-}" = "--force" ]; then
  FORCE_SYNC_RUNTIME=1
fi

runtime_docker_dir="$REMOTE_RUNTIME_DIR/deploy/docker"
runtime_release_dir="$REMOTE_RUNTIME_DIR/deploy/release"
runtime_history_dir="$REMOTE_RUNTIME_DIR/releases/history"

mkdir -p "$runtime_docker_dir" "$runtime_release_dir" "$runtime_history_dir"

template_compose="$TEMPLATE_ROOT/docker-compose.fake-remote-target.yml"
template_env="$TEMPLATE_ROOT/.env.fake-remote-target.example"

[ -f "$template_compose" ] || { printf 'Missing template compose: %s\n' "$template_compose" >&2; exit 1; }
[ -f "$template_env" ] || { printf 'Missing template env: %s\n' "$template_env" >&2; exit 1; }

cp "$template_compose" "$runtime_docker_dir/docker-compose.offline.yml"
if [ "$FORCE_SYNC_RUNTIME" = "1" ] || [ ! -f "$runtime_docker_dir/.env" ]; then
  cp "$template_env" "$runtime_docker_dir/.env"
fi

for script_name in \
  remote_apply_release.sh \
  remote_smoke_verify.sh \
  remote_rollback_release.sh \
  remote_apply_registry_release.sh \
  remote_rollback_registry_release.sh
do
  source_script="$WORKSPACE_ROOT/deploy/release/$script_name"
  [ -f "$source_script" ] || { printf 'Missing release script: %s\n' "$source_script" >&2; exit 1; }
  cp "$source_script" "$runtime_release_dir/$script_name"
  chmod +x "$runtime_release_dir/$script_name"
done

mkdir -p /AIOps/releases/testhub-platform /AIOps/releases/testhub-platform-registry

printf 'Fake remote runtime prepared at %s\n' "$REMOTE_RUNTIME_DIR"
