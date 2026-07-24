#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST=""
REMOTE_PORT="22"
USER_NAME=""
PASSWORD=""
RUNTIME_DIR="/AIOps/apps/testhub-platform-local-remote"
IMAGE_TAG="latest"
SKIP_BACKUP=0

usage() {
  cat <<'EOF'
Usage:
  remote_reseed_fake_remote.sh --remote-host <host> --user <user> --password <password>
    [--remote-port 22] [--runtime-dir <dir>] [--image-tag <tag>] [--skip-backup]
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
    --skip-backup) SKIP_BACKUP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 1 ;;
  esac
done

[ -n "$REMOTE_HOST" ] || { usage >&2; exit 1; }
[ -n "$USER_NAME" ] || { usage >&2; exit 1; }
[ -n "$PASSWORD" ] || { usage >&2; exit 1; }

backup_arg=""
if [ "$SKIP_BACKUP" = "1" ]; then
  backup_arg="--skip-backup"
fi

SSH_OPTS=(-p "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
sshpass -p "$PASSWORD" ssh "${SSH_OPTS[@]}" "$USER_NAME@$REMOTE_HOST" \
  "export IMAGE_TAG='$IMAGE_TAG'; export RUNTIME_DIR='$RUNTIME_DIR'; bash -lc '
set -euo pipefail
compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose \"\$@\"
  else
    docker compose \"\$@\"
  fi
}

runtime_compose_file=\"\$RUNTIME_DIR/deploy/docker/docker-compose.offline.yml\"
runtime_env_file=\"\$RUNTIME_DIR/deploy/docker/.env\"
[ -f \"\$runtime_compose_file\" ] || { echo Missing compose file: \"\$runtime_compose_file\" >&2; exit 1; }
[ -f \"\$runtime_env_file\" ] || { echo Missing env file: \"\$runtime_env_file\" >&2; exit 1; }

project_name=\"\$(grep \"^COMPOSE_PROJECT_NAME=\" \"\$runtime_env_file\" | tail -n 1 | cut -d= -f2- || true)\"
[ -n \"\$project_name\" ] || project_name=\"testhub-fake-remote\"

container_prefix=\"\$(grep \"^CONTAINER_PREFIX=\" \"\$runtime_env_file\" | tail -n 1 | cut -d= -f2- || true)\"
[ -n \"\$container_prefix\" ] || container_prefix=\"testhub-fake-remote\"

mysql_container=\"\$container_prefix-mysql\"
backup_root=\"\$RUNTIME_DIR/releases/fake-remote-backups\"
mkdir -p \"\$backup_root\"

if [ \"$SKIP_BACKUP\" != \"1\" ]; then
  if docker ps -a --format \"{{.Names}}\" | grep -qx \"\$mysql_container\"; then
    stamp=\"\$(date -u +%Y%m%dT%H%M%SZ)\"
    docker exec \"\$mysql_container\" sh -lc \"mysqldump -uroot -p\\\"\\\$MYSQL_ROOT_PASSWORD\\\" --databases \\\"\\\$MYSQL_DATABASE\\\" --single-transaction --quick --routines --events\" > \"\$backup_root/fake-remote-\$stamp.sql\"
  fi
fi

volume_prefix=\"\${project_name}_testhub_fake_remote_\"
for volume_name in \
  \"\${volume_prefix}mysql\" \
  \"\${volume_prefix}redis\" \
  \"\${volume_prefix}appdata\" \
  \"\${volume_prefix}media\" \
  \"\${volume_prefix}static\" \
  \"\${volume_prefix}logs\"
do
  docker volume rm \"\$volume_name\" >/dev/null 2>&1 || true
done

tmp_env=\"\$(mktemp)\"
cp \"\$runtime_env_file\" \"\$tmp_env\"
if grep -q \"^IMAGE_TAG=\" \"\$tmp_env\"; then
  sed -i \"s/^IMAGE_TAG=.*/IMAGE_TAG=$IMAGE_TAG/\" \"\$tmp_env\"
else
  printf \"\nIMAGE_TAG=%s\n\" \"$IMAGE_TAG\" >> \"\$tmp_env\"
fi

compose_cmd -p \"\$project_name\" --env-file \"\$tmp_env\" -f \"\$runtime_compose_file\" down
compose_cmd -p \"\$project_name\" --env-file \"\$tmp_env\" -f \"\$runtime_compose_file\" up -d

backend_init=\"\$container_prefix-backend-init\"
attempt=1
while [ \"\$attempt\" -le 180 ]; do
  state=\"\$(docker inspect -f \"{{.State.Status}} {{.State.ExitCode}}\" \"\$backend_init\" 2>/dev/null || true)\"
  if [ \"\$state\" = \"exited 0\" ]; then
    break
  fi
  if printf \"%s\" \"\$state\" | grep -q \"^exited \"; then
    docker logs \"\$backend_init\" --tail 200 || true
    echo \"backend init failed: \$state\" >&2
    exit 1
  fi
  sleep 2
  attempt=\$((attempt + 1))
done

if [ \"\$attempt\" -gt 180 ]; then
  docker logs \"\$backend_init\" --tail 200 || true
  echo \"timeout waiting for backend init\" >&2
  exit 1
fi

rm -f \"\$tmp_env\"
printf \"Fake remote reseed completed with IMAGE_TAG=%s\n\" \"$IMAGE_TAG\"
' $backup_arg"
