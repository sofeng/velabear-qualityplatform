#!/usr/bin/env bash
set -euo pipefail

SSH_USER="${SSH_USER:-testhub}"
SSH_PASSWORD="${SSH_PASSWORD:-testhub123}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
TEMPLATE_ROOT="${TEMPLATE_ROOT:-$WORKSPACE_ROOT/deploy/local-fake-remote}"
REMOTE_RUNTIME_DIR="${REMOTE_RUNTIME_DIR:-/AIOps/apps/testhub-platform-local-remote}"
FORCE_SYNC_RUNTIME="${FORCE_SYNC_RUNTIME:-0}"

if ! id -u "$SSH_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$SSH_USER"
fi
echo "$SSH_USER:$SSH_PASSWORD" | chpasswd

if [ -S /var/run/docker.sock ]; then
  socket_gid="$(stat -c '%g' /var/run/docker.sock)"
  socket_group="$(getent group "$socket_gid" | cut -d: -f1 || true)"
  if [ -z "$socket_group" ]; then
    socket_group="dockersock"
    groupadd -f -g "$socket_gid" "$socket_group"
  fi
  usermod -aG "$socket_group" "$SSH_USER"
  chmod 666 /var/run/docker.sock || true
fi

mkdir -p /var/run/sshd /AIOps/apps /AIOps/releases
chown -R "$SSH_USER:$SSH_USER" /AIOps/apps /AIOps/releases

if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
if ! grep -q '^PubkeyAuthentication yes' /etc/ssh/sshd_config; then
  printf '\nPubkeyAuthentication yes\n' >> /etc/ssh/sshd_config
fi
if ! grep -q '^UsePAM no' /etc/ssh/sshd_config; then
  printf 'UsePAM no\n' >> /etc/ssh/sshd_config
fi

FAKE_REMOTE_FORCE_SYNC_RUNTIME="$FORCE_SYNC_RUNTIME" \
FAKE_REMOTE_RUNTIME_DIR="$REMOTE_RUNTIME_DIR" \
FAKE_REMOTE_TEMPLATE_ROOT="$TEMPLATE_ROOT" \
FAKE_REMOTE_WORKSPACE_ROOT="$WORKSPACE_ROOT" \
/usr/local/bin/fake-remote-bootstrap-runtime

exec /usr/sbin/sshd -D -e
