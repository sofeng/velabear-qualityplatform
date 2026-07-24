# TestHub 本地假远程目标环境

本文档用于把本机 Docker Desktop 固化成一套“控制面 + 假远程目标面”的联调环境。

目标：

- 当前本地验证环境继续作为控制面
- 额外启动一套本地 SSH 网关容器，模拟远程 Linux 主机
- 通过该 SSH 网关去驱动 Docker Desktop 上的另一套目标容器
- 后续 AI 开发、AI 自动部署、AI 自动化运维都优先在本地闭环联调

## 1. 架构

本地会分成两套环境：

1. 控制面
- 你现在已经在用的本地平台
- 典型端口：`41080`、`48000`
- 容器名通常是 `testhub-local-*`

2. 假远程目标面
- SSH 网关容器：`testhub-fake-remote-ssh`
- 目标平台容器：`testhub-*`
- 典型端口：`51080`、`58000`

注意：

- 控制面不要把 `127.0.0.1` 直接当远程主机
- 对控制面容器来说，推荐远程地址使用 `host.docker.internal`
- 这样后端/Celery 容器通过 SSH 连到本机暴露出来的 `2222` 端口时，路径与网络都更稳定

## 2. 本次新增文件

假远程网关与模板：

- `deploy/local-fake-remote/docker-compose.ssh-gateway.yml`
- `deploy/local-fake-remote/ssh-gateway.Dockerfile`
- `deploy/local-fake-remote/gateway-entrypoint.sh`
- `deploy/local-fake-remote/bootstrap-runtime.sh`
- `deploy/local-fake-remote/docker-compose.fake-remote-target.yml`
- `deploy/local-fake-remote/.env.fake-remote-target.example`

快捷脚本：

- `deploy/local-fake-remote/start_fake_remote_gateway.ps1`
- `deploy/local-fake-remote/stop_fake_remote_gateway.ps1`
- `deploy/local-fake-remote/sync_fake_remote_runtime.ps1`
- `deploy/local-fake-remote/start_fake_remote_gateway.sh`
- `deploy/local-fake-remote/stop_fake_remote_gateway.sh`
- `deploy/local-fake-remote/sync_fake_remote_runtime.sh`

控制面初始化命令：

- `python manage.py bootstrap_fake_remote_target --project-id <id>`

## 3. 启动假远程 SSH 网关

Windows PowerShell：

```powershell
./deploy/local-fake-remote/start_fake_remote_gateway.ps1
```

Linux / macOS：

```bash
bash deploy/local-fake-remote/start_fake_remote_gateway.sh
```

默认会暴露：

- SSH 地址：`host.docker.internal:2222`
- SSH 用户：`testhub`
- SSH 密码：`testhub123`

说明：

- 网关容器内部是 Linux 环境
- 它通过 `/var/run/docker.sock` 直接操控本机 Docker Desktop
- 它第一次启动时会自动准备运行目录：
  - `/AIOps/apps/testhub-platform-local-remote`
  - `/AIOps/releases/testhub-platform`
  - `/AIOps/releases/testhub-platform-registry`

如果后续你更新了假远程模板，执行：

```powershell
./deploy/local-fake-remote/sync_fake_remote_runtime.ps1
```

## 4. 控制面中一键创建 DeploymentTarget / Template

在当前控制面代码目录执行：

```powershell
python manage.py bootstrap_fake_remote_target --project-id 1
```

如果你的项目 ID 不是 `1`，替换成真实项目 ID。

这个命令会自动创建或更新：

- DeploymentTarget：`本地假远程目标`
- DeploymentTemplate：`本地假远程-离线发布`
- DeploymentTemplate：`本地假远程-Registry发布`

默认核心参数：

- host：`host.docker.internal`
- ssh_port：`2222`
- runtime_dir：`/AIOps/apps/testhub-platform-local-remote`
- default_release_mode：`offline_bundle`
- allowed_release_modes：`offline_bundle, registry`
- metadata.credentials：`testhub / testhub123`
- metadata.allow_automation：`true`

## 5. 假远程目标面的访问与账号

目标平台默认端口：

- 前端：`http://localhost:51080`
- 后端：`http://localhost:58000`
- MySQL：`127.0.0.1:53306`
- Redis：`127.0.0.1:56379`

目标平台默认账号：

- 管理员：`admin / admin123`
- MySQL：`testhub / testhub123`
- Redis 密码：`1234`

说明：

- 目标面默认不挂载初始化 seed
- `IMPORT_INIT_SEED=0`
- 它更侧重验证发布链路、冒烟、回滚、回归、AI 运维联动

## 6. 联调流程建议

推荐顺序：

1. 启动控制面本地验证环境
2. 启动假远程 SSH 网关
3. 在控制面执行 `bootstrap_fake_remote_target`
4. 生成或准备 BuildArtifact
5. 在控制面创建 DeploymentExecution，目标选“本地假远程目标”
6. 执行 `dispatch -> publish -> smoke -> regression -> rollback`

这样可以完整验证：

- AI 任务到制品的关联
- 部署异步队列
- 远端脚本执行
- Docker Desktop 上目标环境重建
- 事件日志与 AI 运维建议

## 7. 关键实现说明

### 7.1 为什么不用绑定宿主机目录

SSH 网关容器内执行 `docker compose` 时，如果目标 compose 使用宿主机绝对路径绑定，很容易出现 Docker daemon 解析路径和容器内路径不一致的问题。

因此本地假远程目标模板改成了：

- MySQL / Redis / appdata / media / static / logs 全部使用 named volume
- 不依赖宿主机路径
- 更适合通过 Docker socket 从网关容器转调 Docker Desktop

### 7.2 为什么要给 smoke 增加 `SMOKE_HOST`

远端 smoke 脚本原来默认检查 `127.0.0.1`。

但在假远程模式下，脚本运行在 SSH 网关容器里，目标容器的发布端口实际暴露在 Docker host 上，所以：

- 默认 smoke host 改为可配置
- 假远程目标环境通过 `.env` 使用 `SMOKE_HOST=host.docker.internal`

现有真实远程服务器不受影响，因为默认值仍是 `127.0.0.1`

## 8. 停止网关

```powershell
./deploy/local-fake-remote/stop_fake_remote_gateway.ps1
```

该命令只停止网关容器，不会删除目标面卷数据。

## 9. 重置本地测试环境并重新导入初始化数据

当 `testhub-fake-remote-*` 这套本地测试环境需要恢复成“带完整初始化数据的干净测试环境”时，直接执行：

```powershell
./deploy/local-fake-remote/reseed_fake_remote_env.ps1 -ImageTag latest
```

脚本会自动执行：
- 备份 fake-remote 当前 MySQL 数据到 `.docker-data/fake-remote-backups/`
- 停止 `testhub-fake-remote-*` 容器
- 删除 fake-remote 专属数据卷
- 重新创建 fake-remote 容器
- 等待 `backend-init` 完成迁移、seed 导入、media 复制和管理员初始化
- 校验 `http://localhost:58000/admin/login/` 与 `http://localhost:51080/`

当前 fake-remote 模板默认已经开启：
- `IMPORT_INIT_SEED=1`
- `INIT_SEED_COPY_MEDIA=1`

注意：
- split backend 镜像必须包含 `deploy/init-seed`
- 本仓库 `deploy/init-seed/` 目录需要保持最新

## 10. AI 页面只读 Smoke

本地 fake-remote 测试环境重建或发版后，可直接执行：

```powershell
python tests/fake_remote_ai_workspace_smoke.py
```

它会只读验证以下页面：
- `AI会话`
- `AI开发环境配置`
- `AI开发项目配置`

主要检查：
- 页面中文是否正常显示
- seed 配置是否出现在前端页面
- 关键按钮是否可见
