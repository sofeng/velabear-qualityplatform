# TestHub Phase 5-8 交付说明

本文档用于说明截至 `2026-04-28` 已落地的 Phase 5-8 能力、运行前提、本地验证方式和当前边界。

## 1. 当前落地状态

Phase 5-8 已完成第一版可用 MVP，不再只是方案文档。

已落地范围：

- Phase 5：`apps.deployments` 已接通真实发布执行层，可生成执行计划并驱动 `publish/smoke/rollback` 脚本
- Phase 6：AI 开发任务已支持创建 `BuildArtifact`，并进一步创建 `DeploymentExecution`
- Phase 7：部署状态机、审批、事件审计、日志回看已落地到部署域模型
- Phase 8：已提供规则型 AI 运维建议入口，可基于真实执行记录返回结构化建议

本轮实现刻意保持边界：

- 不新增第二套发布体系，继续复用 Phase 2 的 `deploy/release` 脚本链路
- 不默认开放任意远程命令执行
- 不默认开放生产环境自动发布
- 不深度改造现有 `apps.workflow`，而是在 `apps.deployments` 内先落地稳定状态机与审计能力

## 2. 代码入口

后端核心目录：

- `apps/deployments/models.py`
- `apps/deployments/services.py`
- `apps/deployments/dispatch_service.py`
- `apps/deployments/tasks.py`
- `apps/deployments/log_service.py`
- `apps/deployments/integration_service.py`
- `apps/deployments/ops_advisor.py`
- `apps/deployments/views.py`

AI 研发闭环入口：

- `apps/ai_development/views.py`
- `apps/ai_development/serializers.py`

前端控制台入口：

- `frontend/src/views/deployments/DeploymentResourceConsole.vue`
- `frontend/src/views/ai-generation/AIGenerationWorkspace.vue`
- `frontend/src/api/deployments.js`

## 3. 已提供的 API 能力

部署主资源：

- `/api/deployments/targets/`
- `/api/deployments/templates/`
- `/api/deployments/artifacts/`
- `/api/deployments/executions/`
- `/api/deployments/events/`
- `/api/deployments/approvals/`
- `/api/deployments/rollbacks/`

部署执行动作：

- `POST /api/deployments/executions/{id}/dispatch/`
- `POST /api/deployments/executions/{id}/approve/`
- `POST /api/deployments/executions/{id}/reject/`
- `POST /api/deployments/executions/{id}/publish/`
- `POST /api/deployments/executions/{id}/smoke/`
- `POST /api/deployments/executions/{id}/regression/`
- `POST /api/deployments/executions/{id}/retry/`
- `POST /api/deployments/executions/{id}/rollback/`
- `GET /api/deployments/executions/{id}/events/`
- `GET /api/deployments/executions/{id}/logs/`
- `GET /api/deployments/executions/{id}/advice/`

AI 研发到部署桥接动作：

- `POST /api/ai-development/tasks/{task_id}/create_artifact/`
- `POST /api/ai-development/tasks/{task_id}/create_deployment/`

## 4. 运行前提

### 4.1 容器镜像前提

为支持 Phase 5-8 的真实远端发布，后端运行镜像已补齐以下运行时依赖：

- `openssh-client`
- `sshpass`
- `git`
- `curl`
- Playwright 浏览器及系统依赖

同时，后端应用镜像会额外打包：

- `deploy/release/` 发布脚本目录
- `deploy/docker/entrypoint.sh`

### 4.2 Celery 队列前提

这是本轮补齐的一个关键点。

部署异步动作默认会路由到 `DEPLOYMENT_CELERY_QUEUE`，默认值为 `deployments`。因此：

- `testhub-celery-worker` 必须消费 `celery,deployments`
- `testhub-ai-dev-worker` 继续只消费 `ai_coding`

对应默认配置已经调整为：

- `CELERY_QUEUE=celery,deployments`
- `DEPLOYMENT_CELERY_QUEUE=deployments`
- `AIDEV_CELERY_QUEUE=ai_coding`

如果没有这条队列消费关系，前端点击“发布/冒烟/回归/回滚/重试”虽然会入队，但任务不会真正执行。

### 4.3 凭据前提

部署执行需要能解析目标机凭据，支持两种方式：

1. `DeploymentTarget.metadata.credentials`
2. 环境变量 `DEPLOYMENT_CREDENTIAL_MAP_JSON`

若两者都没有，则会回退读取：

- `DEPLOYMENT_DEFAULT_SSH_USER`
- `DEPLOYMENT_DEFAULT_SSH_PASSWORD`

## 5. 本地验证方式

本地验证文件：

- 环境变量文件：`deploy/docker/.env.local`
- Compose 主文件：`deploy/docker/docker-compose.offline.yml`
- Compose 本地覆盖：`deploy/docker/docker-compose.local-validate.yml`

推荐启动方式：

```powershell
docker compose `
  --env-file deploy/docker/.env.local `
  -f deploy/docker/docker-compose.offline.yml `
  -f deploy/docker/docker-compose.local-validate.yml `
  up -d
```

本地验证默认访问入口：

- 前端：`http://localhost:41080`
- 后端 API：`http://localhost:48000`
- MySQL：`127.0.0.1:23306`
- Redis：`127.0.0.1:26379`

本地验证默认账号：

- 管理员账号：`admin`
- 管理员密码：`admin123`
- MySQL 库：`testhub`
- MySQL 用户：`testhub`
- MySQL 密码：`testhub123`
- Redis 密码：`1234`

本地持久化目录：

- `D:/AI/syswin-testhub/testhub-platform-src/.docker-data/testhub-platform-local`

另外，已经补充了专门的“本地假远程目标环境”方案：

- [LOCAL_FAKE_REMOTE.md](D:/AI/syswin-testhub/testhub-platform-src/deploy/LOCAL_FAKE_REMOTE.md)

这套模式会把当前本地验证环境作为控制面，再额外启动一个本地 SSH 网关作为假远程 Linux 主机，用来联调真实的发布、冒烟、回滚和 AI 运维链路。

## 6. 已完成的验证

本轮代码完成后已通过以下验证：

- `python -m compileall apps backend`
- `python manage.py test apps.deployments --settings=backend.settings_smoke`
- `npm run build`

## 7. 当前边界与后续建议

当前 MVP 已经满足“AI 开发成果 -> 构建制品 -> 部署任务 -> 自动发布/冒烟/回归 -> 失败联动缺陷 -> AI 运维建议”的最小闭环。

但当前仍建议后续继续做以下增强：

- 把部署审批与治理规则更深接入统一 `workflow`
- 将前端动作从 prompt 式交互升级为更明确的表单对话框
- 为部署目标与模板补一版初始化种子或后台初始化脚本
- 在真实联调环境补一轮端到端异步发布验证
