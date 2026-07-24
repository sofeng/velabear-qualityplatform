#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST=""
REMOTE_PORT="22"
USER_NAME=""
PASSWORD=""
RUNTIME_DIR="/AIOps/apps/testhub-platform-offline-20260424"
COMPONENTS="backend,frontend"

usage() {
  cat <<'EOF'
Usage:
  smoke_release_remote.sh --remote-host <host> --user <user> --password <password>
    [--remote-port 22] [--runtime-dir <dir>] [--components backend,frontend]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --remote-host) REMOTE_HOST="$2"; shift 2 ;;
    --remote-port) REMOTE_PORT="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --runtime-dir) RUNTIME_DIR="$2"; shift 2 ;;
    --components) COMPONENTS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 1 ;;
  esac
done

[ -n "$REMOTE_HOST" ] || { usage >&2; exit 1; }
[ -n "$USER_NAME" ] || { usage >&2; exit 1; }
[ -n "$PASSWORD" ] || { usage >&2; exit 1; }

sshpass -p "$PASSWORD" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USER_NAME@$REMOTE_HOST" \
  "bash '$RUNTIME_DIR/deploy/release/remote_smoke_verify.sh' --runtime-dir '$RUNTIME_DIR' --components '$COMPONENTS'"
