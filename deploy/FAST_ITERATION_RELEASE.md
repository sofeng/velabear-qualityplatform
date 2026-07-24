# Fast Iteration Release

This document defines the fast iteration release flow for TestHub after the first offline deployment has already been completed.

Preferred release channel split:

- first deployment and fallback: offline bundle flow
- normal daily backend or frontend iteration: registry flow

See the registry path here:

- `deploy/REGISTRY_FAST_RELEASE.md`

## Goal

Future releases must avoid repeating the full first-day offline deployment process.

The runtime topology stays fixed:

- Runtime root stays on the server
- `docker-compose.offline.yml` stays the runtime compose file
- `.env` remains the source of runtime values
- Persistent data stays under `/AIOps/data/testhub-platform`

Only changed images should be rebuilt, exported, uploaded, loaded, and recreated.

That statement still applies, but there are now two execution channels:

- offline bundle channel: image tars are exported and uploaded
- registry channel: image tags are pushed and the target host pulls only changed layers

## Release model

Each release is identified by a new `IMAGE_TAG`.

Recommended examples:

- `20260426-1`
- `20260426-2`
- `20260426-gitsha`

## Components

Supported release components:

- `backend-runtime`
- `backend`
- `frontend`
- `mysql`
- `redis`
- `aidev-runtime`

Normal iteration releases should usually update only:

- `backend`
- `frontend`

Infrastructure or low-frequency runtime images should be rebuilt only when the image contract actually changes.

`backend-runtime` is the reusable backend dependency base image. It contains:

- system packages
- Python dependencies
- Playwright browsers and browser OS dependencies

Normal code iterations should not rebuild `backend-runtime` unless:

- `requirements.txt` changed
- browser runtime requirements changed
- backend system package requirements changed

The `aidev-runtime` component is the optional Docker runtime used by AI development tasks when they launch isolated project workspaces.

## Channel Choice

Use the offline bundle channel when:

- the target host is being deployed for the first time
- the environment is air-gapped
- you need a disaster-recovery fallback package

Use the registry channel when:

- the environment is already online and stable
- backend or frontend iterations are frequent
- you want remote hosts to reuse cached image layers instead of receiving large tar archives

## Scripts

Local scripts:

- `deploy/release/build_release_bundle.ps1`
- `deploy/release/publish_release_remote.ps1`
- `deploy/release/rollback_release_remote.ps1`
- `deploy/release/smoke_release_remote.ps1`
- `deploy/release/release_split_test_server.ps1`
- `deploy/release/rollback_split_test_server.ps1`
- `deploy/release/smoke_split_test_server.ps1`

Remote scripts included in each release bundle:

- `deploy/release/remote_apply_release.sh`
- `deploy/release/remote_smoke_verify.sh`
- `deploy/release/remote_rollback_release.sh`

For the currently deployed split test runtime on `172.31.119.49`, use:

- `deploy/SPLIT_RUNTIME_LIGHT_RELEASE.md`

That document records the exact runtime directory, ports, credentials, and the prefilled one-click wrapper commands for the split environment.

## Standard flow

This section describes the offline bundle variant.

### 1. Build a release bundle locally

Example:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-1 `
  -Components backend,frontend
```

Low-frequency backend runtime refresh example:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-runtime-1 `
  -Components backend-runtime
```

Output:

- `.release_out/testhub-platform-release-20260426-1/`

Bundle contents:

- `release.env`
- `images/*.tar`
- `runtime/deploy/docker/*`
- `runtime/deploy/release/*.sh`

### 2. Upload and apply the release remotely

Example:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/publish_release_remote.ps1 `
  -ReleaseDir .release_out/testhub-platform-release-20260426-1 `
  -Host 172.31.119.49 `
  -User root `
  -Password 'your-password' `
  -RemoteReleaseRoot /AIOps/releases/testhub-platform `
  -RuntimeDir /AIOps/apps/testhub-platform-offline-20260424 `
  -AutoApply `
  -RunSmoke
```

### 3. What the remote apply step does

For a backend release:

1. uploads the release bundle
2. `docker load` imports the image tar files
3. updates `IMAGE_TAG` in runtime `.env`
4. runs `testhub-backend-init`
5. recreates `testhub-backend`, `testhub-celery-worker`, and `testhub-ai-dev-worker`
6. recreates `testhub-frontend` when included
7. runs smoke verification
8. stores a release history snapshot under the runtime directory

For a frontend-only release:

1. loads the frontend image
2. updates `IMAGE_TAG`
3. recreates only `testhub-frontend`
4. runs frontend smoke verification

For an AI development runtime release:

1. loads the `testhub/ai-dev` image tar
2. does not change `IMAGE_TAG`
3. does not recreate the platform runtime services
4. makes the new isolated AI development runtime available for subsequent AI tasks

For a backend runtime base refresh:

1. builds or exports the reusable runtime base image
2. does not directly recreate running services by itself
3. is intended to support subsequent backend app image builds or registry-layer reuse

## Rollback

Rollback can be done with either:

- a saved release history directory
- a target `IMAGE_TAG`

Example with a target image tag:

```bash
bash deploy/release/remote_rollback_release.sh \
  --runtime-dir /AIOps/apps/testhub-platform-offline-20260424 \
  --image-tag 20260424-2 \
  --components backend,frontend
```

Local wrapper example:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/rollback_release_remote.ps1 `
  -Host 172.31.119.49 `
  -User root `
  -Password 'your-password' `
  -RuntimeDir /AIOps/apps/testhub-platform-offline-20260424 `
  -ImageTag 20260424-2 `
  -Components backend,frontend `
  -RunSmoke
```

## Safety rules

- Do not rebuild the server runtime structure for each release
- Do not overwrite `/AIOps/data/testhub-platform`
- Do not re-import seed data during normal releases
- Do not upload source code to the target server
- Do not recreate MySQL or Redis unless their images are intentionally part of the release
- Do not rebuild the backend runtime base on every app iteration unless the dependency contract changed
- Do not rebuild the AI development runtime on every app iteration unless its toolchain actually changed
- Quick rollback in this flow is primarily designed for `backend` and `frontend` releases

## Important limitation

The current offline release mode uses `docker save` tar archives.

That means:

- the split between `backend-runtime` and `backend` speeds up local rebuilds
- but exporting the final backend image as a tar archive still includes its parent layers
- so offline tar uploads are not true incremental transfer for high-frequency backend releases

If daily multi-version iteration speed becomes critical, the next step should be a private registry based release flow so the target host reuses cached layers instead of receiving full backend tars every time.

That next step is now documented separately in:

- `deploy/REGISTRY_FAST_RELEASE.md`

## Recommended release patterns

Backend-only release:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-1 `
  -Components backend
```

Frontend-only release:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-2 `
  -Components frontend
```

Full app release:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-3 `
  -Components backend,frontend
```

Low-frequency AI development runtime refresh:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-aidev-1 `
  -Components aidev-runtime
```

Low-frequency backend runtime refresh:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_release_bundle.ps1 `
  -ReleaseTag 20260426-runtime-1 `
  -Components backend-runtime
```

## Expected result

After this flow is in place, future iteration releases should become:

1. build changed image(s)
2. export changed image tar(s)
3. upload one release directory
4. apply remotely
5. smoke verify
6. rollback quickly if needed

That is the release path Phase 2 is meant to establish.
