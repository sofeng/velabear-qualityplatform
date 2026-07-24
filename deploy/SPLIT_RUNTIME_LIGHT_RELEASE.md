# Split Runtime Light Release

This document is the direct operating manual for the current split runtime already deployed on the test server.

It is intended for normal daily iterations of the platform, especially `frontend` and `backend` releases for the `Siyuan R&D Management` related modules.

## Current Split Runtime

Verified on `2026-04-29`.

- Remote host: `172.31.119.49`
- Runtime dir: `/AIOps/apps/testhub-platform-split-20260429`
- Release root: `/AIOps/releases/testhub-platform-split`
- Data root: `/AIOps/data2/testhub-platform`
- Compose project: `testhub-split`
- Container prefix: `testhub-split`

Current endpoints:

- Frontend: `http://172.31.119.49:41080`
- Backend base: `http://172.31.119.49:48000`
- Backend admin: `http://172.31.119.49:48000/admin/login/`
- MySQL host: `172.31.119.49`
- MySQL port: `23306`
- Redis host: `172.31.119.49`
- Redis port: `26379`

Current credentials:

- Django admin username: `admin`
- Django admin password: `Admin@Testhub2026`
- MySQL database: `testhub`
- MySQL username: `testhub`
- MySQL password: `Testhub@2026`
- MySQL root password: `TesthubRoot@2026`
- Redis password: `Redis@2026`

## What Normally Needs Releasing

For future `Siyuan R&D Management` frontend and backend iterations, the answer is yes: in normal cases, only light releases of `frontend`, `backend`, or `backend,frontend` are needed.

Use `frontend` only when:

- only `frontend/` code changed
- no backend API contract changed

Use `backend` only when:

- only Django code changed under `backend/` or `apps/`
- no frontend code needs rebuilding
- `requirements.txt` did not change
- no new browser or OS runtime dependency was introduced

Use `backend,frontend` when:

- the page and the API changed together
- request or response contracts changed
- a backend change requires the frontend to consume new fields or behavior

Do not rebuild low-frequency components unless their contract changed:

- `backend-runtime`: only when Python packages, Playwright, or system package dependencies changed
- `aidev-runtime`: only when the AI development work-container toolchain changed
- `mysql`, `redis`: only when those images themselves need version or configuration-level replacement

## Wrapper Scripts

These wrappers are already prefilled for the current split test server:

- `deploy/release/release_split_test_server.ps1`
- `deploy/release/smoke_split_test_server.ps1`
- `deploy/release/rollback_split_test_server.ps1`

They default to:

- host `172.31.119.49`
- user `root`
- release root `/AIOps/releases/testhub-platform-split`
- runtime dir `/AIOps/apps/testhub-platform-split-20260429`

## Password Handling

Recommended:

```powershell
$env:TESTHUB_SPLIT_REMOTE_PASSWORD='your-password'
```

You can also pass the password directly:

```powershell
-Password 'your-password'
```

## Standard Light Release Commands

Backend and frontend together:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-r1
```

Frontend only:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-r2 `
  -Components frontend
```

Backend only:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-r3 `
  -Components backend
```

Backend runtime refresh:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-runtime-r1 `
  -Components backend-runtime
```

AI development runtime refresh:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-aidev-r1 `
  -Components aidev-runtime
```

If the images were already built locally and you only want to repackage and publish:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/release_split_test_server.ps1 `
  -ReleaseTag 20260429-r4 `
  -Components backend,frontend `
  -SkipBuild
```

## Smoke Verification

Run the split runtime smoke check directly:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/smoke_split_test_server.ps1
```

Backend only smoke:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/smoke_split_test_server.ps1 `
  -Components backend
```

## Rollback

Rollback to a previous image tag:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/rollback_split_test_server.ps1 `
  -ImageTag 20260429-r1 `
  -Components backend,frontend `
  -RunSmoke
```

Rollback with a stored history snapshot directory:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/release/rollback_split_test_server.ps1 `
  -HistoryDir '/AIOps/apps/testhub-platform-split-20260429/.release-history/20260429-r1' `
  -Components backend,frontend `
  -RunSmoke
```

## Safety Notes

- This split runtime is intentionally independent from the old monolithic runtime still exposed on `31080/38000/13306/16379`.
- Normal light releases must not touch `/AIOps/data/testhub-platform`.
- The current split runtime persists only under `/AIOps/data2/testhub-platform`.
- Normal light releases must not re-import seed data.
- Normal light releases must not upload source code to the server.

## Recommended Rule

For `Siyuan R&D Management` daily release work, use this default rule:

1. frontend-only change: release `frontend`
2. backend-only change: release `backend`
3. full feature linkage change: release `backend,frontend`
4. dependency or toolchain change: release `backend-runtime` or `aidev-runtime` only when actually required

If later release frequency becomes very high, move the same split runtime to the registry-based release path documented in `deploy/REGISTRY_FAST_RELEASE.md` so the server can reuse cached layers instead of repeatedly receiving full tar archives.
