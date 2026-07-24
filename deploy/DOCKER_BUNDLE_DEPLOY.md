# Docker Bundle Deploy

This deployment bundle is intended for the current MySQL + Redis based platform runtime.

## Files

- Compose: `deploy/docker/docker-compose.bundle.yml`
- Backend runtime base image: `deploy/docker/backend.runtime-base.Dockerfile`
- Backend image: `deploy/docker/backend.container.Dockerfile`
- Frontend image: `deploy/docker/frontend.container.Dockerfile`
- Runtime env example: `deploy/docker/.env.bundle.example`
- Seed mount directory: `deploy/init-seed/`
- Host persistence root: `/AIOps/data/testhub-platform`
- Base image mirror: `docker.m.daocloud.io`

## What the bundle does

`testhub-backend-init` runs the initialization sequence and writes `/app/data/.app-init-complete`.

`testhub-backend`, `testhub-celery-worker`, and `testhub-ai-dev-worker` wait on that shared marker before they start serving traffic, so the bundle remains compatible with older `docker-compose` releases.

`testhub-celery-worker` is the shared worker for the default `celery` queue and the Phase 5-8 `deployments` queue. Async publish, smoke, regression, retry, and rollback actions depend on this worker consuming both queues.

`testhub-ai-dev-worker` is the dedicated Celery worker for the `ai_coding` queue. It is the only always-on platform service that mounts `/var/run/docker.sock`, so AI development tasks can start isolated project work containers without giving Docker socket access to the main web container.

`backend.runtime-base.Dockerfile` contains the low-frequency backend runtime dependencies:

- system packages
- Python packages from `requirements.txt`
- Playwright browsers and their OS dependencies

`backend.container.Dockerfile` now contains only the high-frequency application layer:

- `manage.py`
- `backend/`
- `apps/`
- runtime entrypoint assets under `deploy/docker/`
- bundled prompt and SQL files used by the current platform runtime

The init sequence is:

1. waits for MySQL
2. runs `python manage.py migrate`
3. runs `python manage.py collectstatic`
4. runs `python manage.py init_locator_strategies`
5. imports `deploy/init-seed/seed_data.json` when present
6. copies `deploy/init-seed/media/` into the runtime media volume when enabled
7. ensures the admin user exists

The init container writes a marker file into `/app/data/.init-seed-imported` so the seed is only imported once unless `FORCE_INIT_SEED=1`.

## Host persistence

The bundle persists runtime data directly on the host under `${DATA_ROOT}`.

Default directory layout:

- `${DATA_ROOT}/mysql`
- `${DATA_ROOT}/redis`
- `${DATA_ROOT}/appdata`
- `${DATA_ROOT}/media`
- `${DATA_ROOT}/static`
- `${DATA_ROOT}/logs`

With the default `.env`, these resolve to:

- `/AIOps/data/testhub-platform/mysql`
- `/AIOps/data/testhub-platform/redis`
- `/AIOps/data/testhub-platform/appdata`
- `/AIOps/data/testhub-platform/media`
- `/AIOps/data/testhub-platform/static`
- `/AIOps/data/testhub-platform/logs`

Create these directories on the target host before the first `docker-compose up`.

On SELinux-enabled hosts such as CentOS 7, the compose file already applies `:z` bind mount labels for these directories.

## How to prepare a seed bundle

Export from the current source workspace:

```powershell
python manage.py export_init_seed --output .seed_exports/current --include-media
```

Then copy these generated files into `deploy/init-seed/`:

- `seed_data.json`
- `seed_inventory.json`
- `seed_inventory.md`
- optional `media/`

## AI development runtime image

The compose bundle does not start the isolated AI development runtime as a long-lived service.

Instead, AI development tasks launch short-lived work containers from the image configured in `AIDevelopmentConfig.docker_image`.

Default image:

- `testhub/ai-dev:latest`

This image should be loaded onto the target host when:

- the platform is deployed for the first time
- the AI development toolchain changes

It does not need to be republished for normal frontend/backend code iterations.

## First deployment

Build the reusable backend runtime base image first:

```powershell
docker build -t local/testhub-platform-backend-runtime:latest -f deploy/docker/backend.runtime-base.Dockerfile .
```

Then start the bundle:

```powershell
docker compose -f deploy/docker/docker-compose.bundle.yml up -d --build
```

If the target host only has classic `docker-compose`, run:

```powershell
docker-compose -f deploy/docker/docker-compose.bundle.yml up -d --build
```

## Useful commands

View init logs:

```powershell
docker logs testhub-backend-init
```

View backend logs:

```powershell
docker logs testhub-backend
```

View AI development worker logs:

```powershell
docker logs testhub-ai-dev-worker
```

Restart web only:

```powershell
docker compose -f deploy/docker/docker-compose.bundle.yml restart testhub-backend
```

Re-import seed on next init run:

```powershell
$env:FORCE_INIT_SEED="1"
docker compose -f deploy/docker/docker-compose.bundle.yml up -d testhub-backend-init
```

## Fast iteration releases

After the first offline deployment has completed, normal version iterations should move to the fast release flow instead of repeating the full bundle deployment process.

Important limitation:

- splitting the backend into `backend-runtime` and `backend` reduces rebuild cost and clarifies ownership of heavy dependencies
- but a plain `docker save` of the final `backend` image still carries the parent layers inside the tar archive
- that means offline tar uploads are still not true layer-delta delivery

So this split is the right base for fast iteration, but the real next step for high-frequency releases is registry-style layer reuse rather than repeatedly shipping full backend tar files.

See:

- `deploy/FAST_ITERATION_RELEASE.md`
- `deploy/REGISTRY_FAST_RELEASE.md`
- `deploy/release/build_release_bundle.ps1`
- `deploy/release/publish_release_remote.ps1`

## Default ports

- Frontend: `31080`
- Backend API: `38000`
- MySQL: `13306`
- Redis: `16379`

## Default credentials

- Django admin username: `admin`
- Django admin password: `admin123`

Change these values through compose environment variables before formal deployment.
