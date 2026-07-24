#!/usr/bin/env bash
set -euo pipefail

RELEASE_DIR=""
REMOTE_HOST=""
REMOTE_PORT="22"
USER_NAME=""
PASSWORD=""
REMOTE_RELEASE_ROOT="/AIOps/releases/testhub-platform-registry"
RUNTIME_DIR="/AIOps/apps/testhub-platform-offline-20260424"
AUTO_APPLY=0
RUN_SMOKE=0

usage() {
  cat <<'EOF'
Usage:
  publish_registry_release_remote.sh --release-dir <dir> --remote-host <host> --user <user> --password <password>
    [--remote-port 22] [--remote-release-root <dir>] [--runtime-dir <dir>] [--auto-apply] [--run-smoke]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --release-dir) RELEASE_DIR="$2"; shift 2 ;;
    --remote-host) REMOTE_HOST="$2"; shift 2 ;;
    --remote-port) REMOTE_PORT="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --remote-release-root) REMOTE_RELEASE_ROOT="$2"; shift 2 ;;
    --runtime-dir) RUNTIME_DIR="$2"; shift 2 ;;
    --auto-apply) AUTO_APPLY=1; shift ;;
    --run-smoke) RUN_SMOKE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 1 ;;
  esac
done

[ -n "$RELEASE_DIR" ] || { usage >&2; exit 1; }
[ -n "$REMOTE_HOST" ] || { usage >&2; exit 1; }
[ -n "$USER_NAME" ] || { usage >&2; exit 1; }
[ -n "$PASSWORD" ] || { usage >&2; exit 1; }

RESOLVED_RELEASE_DIR="$(cd "$RELEASE_DIR" && pwd)"
RELEASE_LEAF="$(basename "$RESOLVED_RELEASE_DIR")"
REMOTE_RELEASE_DIR="$REMOTE_RELEASE_ROOT/$RELEASE_LEAF"
SSH_OPTS=(-p "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

required_files=(
  "$RESOLVED_RELEASE_DIR/release.env"
  "$RESOLVED_RELEASE_DIR/runtime/deploy/release/remote_apply_registry_release.sh"
  "$RESOLVED_RELEASE_DIR/runtime/deploy/release/remote_smoke_verify.sh"
  "$RESOLVED_RELEASE_DIR/runtime/deploy/release/remote_rollback_registry_release.sh"
)

for required_file in "${required_files[@]}"; do
  [ -f "$required_file" ] || { printf 'Required release file not found: %s\n' "$required_file" >&2; exit 1; }
done

sshpass -p "$PASSWORD" ssh "${SSH_OPTS[@]}" "$USER_NAME@$REMOTE_HOST" "mkdir -p '$REMOTE_RELEASE_ROOT'"
sshpass -p "$PASSWORD" scp -P "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r "$RESOLVED_RELEASE_DIR" "$USER_NAME@$REMOTE_HOST:$REMOTE_RELEASE_ROOT/"

if [ "$AUTO_APPLY" = "1" ]; then
  smoke_flag=""
  if [ "$RUN_SMOKE" = "1" ]; then
    smoke_flag="--run-smoke"
  fi
  sshpass -p "$PASSWORD" ssh "${SSH_OPTS[@]}" "$USER_NAME@$REMOTE_HOST" \
    "bash '$REMOTE_RELEASE_DIR/runtime/deploy/release/remote_apply_registry_release.sh' --runtime-dir '$RUNTIME_DIR' --release-dir '$REMOTE_RELEASE_DIR' $smoke_flag"
fi

printf 'Remote registry release directory: %s\n' "$REMOTE_RELEASE_DIR"
