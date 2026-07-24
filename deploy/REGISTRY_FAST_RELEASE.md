# Registry Fast Release

This document defines the preferred high-frequency release flow for TestHub after the first offline deployment is already complete.

## Goal

The offline bundle flow remains the correct path for:

- first environment delivery
- air-gapped fallback
- low-frequency infrastructure packaging

It is not the best path for daily backend and frontend iteration, because `docker save` archives still carry parent layers and therefore do not provide true incremental transfer.

The registry flow solves that by pushing tagged images to a private registry so the target host can reuse cached layers through `docker pull`.

## Release Model

Recommended split of responsibilities:

- offline bundle: first deployment and disaster fallback
- registry release: normal backend and frontend iterations

Recommended tag examples:

- `20260427-1`
- `20260427-2`
- `20260427-gitsha`

## One-Time Bootstrap

Bootstrap a private registry on the target host:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/bootstrap_registry_remote.ps1 `
  -Host 172.31.119.49 `
  -User root `
  -Password 'your-password' `
  -RegistryHost 172.31.119.49 `
  -RegistryPort 5443
```

What this does:

- uploads and runs `remote_bootstrap_registry.sh`
- creates a TLS-enabled `registry:2` container on the target host
- stores registry data under `/AIOps/data/testhub-release-registry`
- downloads the registry CA certificate
- imports the CA into `Cert:\CurrentUser\Root`

If Docker Desktop still reports TLS trust errors after that, restart Docker Desktop once.

## Build And Push

Build changed images locally, tag them for the registry, push them, and generate a tiny metadata release directory:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_registry_release.ps1 `
  -ReleaseTag 20260427-1 `
  -RegistryEndpoint 172.31.119.49:5443 `
  -RegistryNamespace testhub-platform `
  -Components backend,frontend
```

Output:

- `.release_out/testhub-platform-registry-release-20260427-1/`

Release directory contents:

- `release.env`
- `RELEASE_NOTES.txt`
- `image-manifest.txt`
- `runtime/deploy/release/*.sh`

Local dry-run without network:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/build_registry_release.ps1 `
  -ReleaseTag 20260424 `
  -RegistryEndpoint 172.31.119.49:5443 `
  -RegistryNamespace testhub-platform `
  -Components backend,frontend `
  -SkipBuild `
  -SkipPush `
  -OutputRoot .release_out_localtest
```

That mode validates the registry release directory contract against already-built local images, but it does not push anything and must not be used as a real deployment artifact.

## Publish And Apply

Upload only the metadata release directory, then let the target host pull the real image layers from the registry:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/publish_registry_release_remote.ps1 `
  -ReleaseDir .release_out/testhub-platform-registry-release-20260427-1 `
  -Host 172.31.119.49 `
  -User root `
  -Password 'your-password' `
  -RuntimeDir /AIOps/apps/testhub-platform-offline-20260424 `
  -AutoApply `
  -RunSmoke
```

Remote apply behavior:

1. uploads the small release metadata directory
2. reads the registry image refs from `release.env`
3. `docker pull`s only the selected images
4. retags them to the local image names already used by runtime compose
5. updates `IMAGE_TAG` when backend or frontend changed
6. runs `testhub-backend-init` when backend changed
7. recreates only the changed runtime services
8. runs smoke verification when requested

## Rollback

Rollback to a previous release tag:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/rollback_registry_release_remote.ps1 `
  -Host 172.31.119.49 `
  -User root `
  -Password 'your-password' `
  -RuntimeDir /AIOps/apps/testhub-platform-offline-20260424 `
  -ImageTag 20260427-1 `
  -Components backend,frontend `
  -RunSmoke
```

The target host reconstructs the registry refs from the stored registry metadata and pulls the selected older tags back into place.

## Components

Supported components:

- `backend-runtime`
- `backend`
- `frontend`
- `mysql`
- `redis`
- `aidev-runtime`

Recommended normal usage:

- `backend`
- `frontend`

Low-frequency only:

- `backend-runtime`
- `mysql`
- `redis`
- `aidev-runtime`

## Why This Is Faster

The current backend split already showed the real shape of the problem:

- high-frequency backend source layer is only a few MB
- low-frequency browser and dependency runtime layers are multiple GB

With registry-based releases:

- local rebuilds can reuse the split runtime base
- remote pulls can reuse already cached layers
- only changed layers cross the network again

That is the real Phase 2 release model for rapid iteration.

## Safety Rules

- do not replace the first offline deployment path with registry-only delivery
- keep `/AIOps/data/testhub-platform` untouched during normal releases
- do not re-import init seed during normal app releases
- do not publish source code to the target server
- rebuild `backend-runtime` only when dependency contracts change
- rebuild `aidev-runtime` only when the AI development toolchain changes

## Related Files

- `deploy/FAST_ITERATION_RELEASE.md`
- `deploy/DOCKER_BUNDLE_DEPLOY.md`
- `deploy/release/build_registry_release.ps1`
- `deploy/release/publish_registry_release_remote.ps1`
- `deploy/release/rollback_registry_release_remote.ps1`
- `deploy/release/bootstrap_registry_remote.ps1`
