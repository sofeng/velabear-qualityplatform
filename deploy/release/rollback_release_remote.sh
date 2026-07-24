#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST=""
REMOTE_PORT="22"
USER_NAME=""
PASSWORD=""
RUNTIME_DIR="/AIOps/apps/testhub-platform-offline-20260424"
IMAGE_TAG=""
HISTORY_DIR=""
COMPONENTS="backend,frontend"
RUN_SMOKE=0

usage() {
  cat <<'EOF'
Usage:
  rollback_release_remote.sh --remote-host <host> --user <user> --password <password>
    [--remote-port 22] [--runtime-dir <dir>] [--image-tag <tag>] [--history-dir <dir>]
    [--components backend,frontend] [--run-smoke]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --remote-host) REMOTE_HOST="$2"; shift 2 ;;
    --remote-port) REMOTE_PORT="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --runtime-dir) RUNTIME_DIR="$2"; shift 2 ;;
    --image-tag) IMAGE_TAG="$2"; shift 2 ;;
    --history-dir) HISTORY_DIR="$2"; shift 2 ;;
    --components) COMPONENTS="$2"; shift 2 ;;
    --run-smoke) RUN_SMOKE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 1 ;;
  esac
done

[ -n "$REMOTE_HOST" ] || { usage >&2; exit 1; }
[ -n "$USER_NAME" ] || { usage >&2; exit 1; }
[ -n "$PASSWORD" ] || { usage >&2; exit 1; }
[ -n "$IMAGE_TAG" ] || [ -n "$HISTORY_DIR" ] || { printf 'Either --image-tag or --history-dir is required.\n' >&2; exit 1; }

image_tag_arg=""
history_dir_arg=""
run_smoke_arg=""
SSH_OPTS=(-p "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

[ -n "$IMAGE_TAG" ] && image_tag_arg="--image-tag '$IMAGE_TAG'"
[ -n "$HISTORY_DIR" ] && history_dir_arg="--history-dir '$HISTORY_DIR'"
[ "$RUN_SMOKE" = "1" ] && run_smoke_arg="--run-smoke"

sshpass -p "$PASSWORD" ssh "${SSH_OPTS[@]}" "$USER_NAME@$REMOTE_HOST" \
  "bash '$RUNTIME_DIR/deploy/release/remote_rollback_release.sh' --runtime-dir '$RUNTIME_DIR' $image_tag_arg $history_dir_arg --components '$COMPONENTS' $run_smoke_arg"
