#!/usr/bin/env bash
set -euo pipefail

docker exec testhub-fake-remote-ssh /usr/local/bin/fake-remote-bootstrap-runtime --force
