#!/bin/sh
set -eu

cd /app

MODE="${1:-web}"
if [ $# -gt 0 ]; then
  shift
fi

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-backend.settings_container}"
export APP_PORT="${APP_PORT:-8000}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@testhub.local}"
export DB_WAIT_INTERVAL="${DB_WAIT_INTERVAL:-3}"
export DB_WAIT_MAX_ATTEMPTS="${DB_WAIT_MAX_ATTEMPTS:-40}"
export APP_INIT_WAIT_INTERVAL="${APP_INIT_WAIT_INTERVAL:-3}"
export APP_INIT_WAIT_MAX_ATTEMPTS="${APP_INIT_WAIT_MAX_ATTEMPTS:-120}"
export CREATE_ADMIN_USER="${CREATE_ADMIN_USER:-1}"
export RUN_INIT_LOCATOR_STRATEGIES="${RUN_INIT_LOCATOR_STRATEGIES:-1}"
export COLLECTSTATIC_ON_INIT="${COLLECTSTATIC_ON_INIT:-1}"
export IMPORT_INIT_SEED="${IMPORT_INIT_SEED:-1}"
export FORCE_INIT_SEED="${FORCE_INIT_SEED:-0}"
export INIT_SEED_COPY_MEDIA="${INIT_SEED_COPY_MEDIA:-1}"
export INIT_SEED_BUNDLE_DIR="${INIT_SEED_BUNDLE_DIR:-/app/init-seed}"
export INIT_SEED_FIXTURE="${INIT_SEED_FIXTURE:-${INIT_SEED_BUNDLE_DIR}/seed_data.json}"
export INIT_SEED_MARKER_FILE="${INIT_SEED_MARKER_FILE:-/app/data/.init-seed-imported}"
export APP_INIT_MARKER_FILE="${APP_INIT_MARKER_FILE:-/app/data/.app-init-complete}"
export WAIT_FOR_APP_INIT="${WAIT_FOR_APP_INIT:-1}"
export CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"
export CELERY_QUEUE="${CELERY_QUEUE:-}"
export CELERY_POOL="${CELERY_POOL:-}"
export CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-}"

mkdir -p /app/data /app/logs /app/media /app/static

log() {
  printf '%s %s\n' "[entrypoint]" "$*"
}

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

wait_for_database() {
  attempt=1
  while [ "$attempt" -le "$DB_WAIT_MAX_ATTEMPTS" ]; do
    if python manage.py shell -c "from django.db import connections; connections['default'].cursor(); print('ok')" >/dev/null 2>&1; then
      log "Database is ready."
      return 0
    fi
    log "Waiting for database ($attempt/$DB_WAIT_MAX_ATTEMPTS)..."
    sleep "$DB_WAIT_INTERVAL"
    attempt=$((attempt + 1))
  done

  log "Database did not become ready in time."
  return 1
}

wait_for_app_init() {
  if ! is_true "$WAIT_FOR_APP_INIT"; then
    log "Skipping app init marker wait."
    return 0
  fi

  attempt=1
  while [ "$attempt" -le "$APP_INIT_WAIT_MAX_ATTEMPTS" ]; do
    if [ -f "$APP_INIT_MARKER_FILE" ]; then
      log "App init marker detected: $APP_INIT_MARKER_FILE"
      return 0
    fi
    log "Waiting for app init marker ($attempt/$APP_INIT_WAIT_MAX_ATTEMPTS)..."
    sleep "$APP_INIT_WAIT_INTERVAL"
    attempt=$((attempt + 1))
  done

  log "App init marker was not created in time."
  return 1
}

run_migrations() {
  log "Applying migrations..."
  python manage.py migrate --noinput
}

collect_static() {
  if ! is_true "$COLLECTSTATIC_ON_INIT"; then
    log "Skipping collectstatic."
    return 0
  fi

  log "Collecting static assets..."
  python manage.py collectstatic --noinput
}

ensure_admin_user() {
  if ! is_true "$CREATE_ADMIN_USER"; then
    log "Skipping admin user bootstrap."
    return 0
  fi

  log "Ensuring admin user exists..."
  python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ["ADMIN_USERNAME"]
password = os.environ["ADMIN_PASSWORD"]
email = os.environ["ADMIN_EMAIL"]

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "email": email,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
    },
)

changed = created
if user.email != email:
    user.email = email
    changed = True
if not user.is_staff:
    user.is_staff = True
    changed = True
if not user.is_superuser:
    user.is_superuser = True
    changed = True
if not user.is_active:
    user.is_active = True
    changed = True

user.set_password(password)
changed = True

if changed:
    user.save()
PY
}

init_locator_strategies() {
  if ! is_true "$RUN_INIT_LOCATOR_STRATEGIES"; then
    log "Skipping locator strategy bootstrap."
    return 0
  fi

  log "Initializing locator strategies..."
  python manage.py init_locator_strategies || true
}

import_init_seed() {
  if ! is_true "$IMPORT_INIT_SEED"; then
    log "Skipping init-seed import."
    return 0
  fi

  if [ -f "$INIT_SEED_MARKER_FILE" ] && ! is_true "$FORCE_INIT_SEED"; then
    log "Init-seed marker already exists: $INIT_SEED_MARKER_FILE"
    return 0
  fi

  if [ ! -f "$INIT_SEED_FIXTURE" ] && [ ! -d "$INIT_SEED_BUNDLE_DIR" ]; then
    log "Init-seed bundle not found, skipping import."
    return 0
  fi

  log "Importing init-seed bundle from $INIT_SEED_BUNDLE_DIR"
  if is_true "$INIT_SEED_COPY_MEDIA"; then
    python manage.py import_init_seed "$INIT_SEED_BUNDLE_DIR" --copy-media
  else
    python manage.py import_init_seed "$INIT_SEED_BUNDLE_DIR"
  fi

  mkdir -p "$(dirname "$INIT_SEED_MARKER_FILE")"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$INIT_SEED_MARKER_FILE"
}

run_web() {
  log "Starting Django web server on port $APP_PORT..."
  exec python manage.py runserver --noreload 0.0.0.0:${APP_PORT}
}

run_worker() {
  log "Starting Celery worker..."
  set -- celery -A backend worker -l "$CELERY_LOG_LEVEL"
  if [ -n "$CELERY_QUEUE" ]; then
    set -- "$@" -Q "$CELERY_QUEUE"
  fi
  if [ -n "$CELERY_POOL" ]; then
    set -- "$@" --pool "$CELERY_POOL"
  fi
  if [ -n "$CELERY_CONCURRENCY" ]; then
    set -- "$@" --concurrency "$CELERY_CONCURRENCY"
  fi
  exec "$@"
}

run_init() {
  rm -f "$APP_INIT_MARKER_FILE"
  wait_for_database
  run_migrations
  collect_static
  init_locator_strategies
  import_init_seed
  ensure_admin_user
  mkdir -p "$(dirname "$APP_INIT_MARKER_FILE")"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$APP_INIT_MARKER_FILE"
  log "Init sequence completed."
}

case "$MODE" in
  init)
    run_init
    ;;
  web)
    wait_for_database
    wait_for_app_init
    run_web
    ;;
  worker)
    wait_for_database
    wait_for_app_init
    run_worker
    ;;
  *)
    exec "$MODE" "$@"
    ;;
esac
