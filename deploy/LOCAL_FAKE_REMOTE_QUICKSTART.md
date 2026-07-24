# Local Fake Remote Quickstart

This quickstart keeps only the shortest path for bringing up the local fake-remote integration loop so it can be reused by later AI auto-deploy and AI ops workflows.

## 1. Goal

Split one local Docker Desktop into two environments:

- Control plane: `testhub-local-*`
- Fake remote target: `testhub-fake-remote-*`

The control plane reaches `host.docker.internal:2222` over SSH and treats the same machine as a remote Linux + Docker target.

## 2. One-click bootstrap

Windows PowerShell:

```powershell
./deploy/local-fake-remote/bootstrap_fake_remote_assets.ps1 -ProjectId 1
```

Linux / macOS:

```bash
bash deploy/local-fake-remote/bootstrap_fake_remote_assets.sh 1
```

This flow will:

- start or rebuild `testhub-fake-remote-ssh`
- sync fake-remote runtime files to `/AIOps/apps/testhub-platform-local-remote`
- create or update the fake-remote `DeploymentTarget / DeploymentTemplate`
- scan `/workspace-release` from the control-plane backend container and create or update `BuildArtifact` rows
- leave `/workspace-release` unchanged by default, which is required because that mount is read-only in local validate mode

If the bundle root is writable and you explicitly want to refresh runtime scripts inside bundles:

```powershell
./deploy/local-fake-remote/bootstrap_fake_remote_assets.ps1 -ProjectId 1 -RefreshRuntimeScripts
```

## 3. Core commands

Create the target and templates:

```bash
python manage.py bootstrap_fake_remote_target --project-id 1
```

Register local bundles as artifacts:

```bash
python manage.py bootstrap_local_release_artifacts \
  --project-id 1 \
  --bundle-root /workspace-release \
  --bundle-path-prefix /workspace-release
```

Refresh runtime scripts only when the bundle directory is writable:

```bash
python manage.py bootstrap_local_release_artifacts \
  --project-id 1 \
  --bundle-root /workspace-release \
  --bundle-path-prefix /workspace-release \
  --refresh-runtime-scripts
```

## 4. Default access

Control plane:

- Frontend: `http://localhost:41080`
- Backend: `http://localhost:48000`

Fake remote target:

- Frontend: `http://localhost:51080`
- Backend admin: `http://localhost:58000/admin/login/`
- MySQL: `127.0.0.1:53306`
- Redis: `127.0.0.1:56379`

Default credentials:

- Admin: `admin / admin123`
- Fake-remote SSH: `testhub / testhub123`
- MySQL app user: `testhub / testhub123`
- MySQL root: `root / root123`
- Redis password: `1234`

## 5. Suggested loop

After rebuilding the local control plane or resetting the local database:

1. Start the local control plane `testhub-local-*`.
2. Run `bootstrap_fake_remote_assets.ps1`.
3. Select `本地假远程目标` in the platform.
4. Create a `DeploymentExecution`.
5. Run `publish -> smoke -> regression -> rollback`.

## 6. Intended reuse

This setup is meant to support:

- AI auto-deploy
- AI ops automation
- AI release failure diagnosis
- AI smoke / regression closed-loop validation
- local pseudo-remote integration testing
