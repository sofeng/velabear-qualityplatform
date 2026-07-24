# TestHub 平台交付说明

本文档用于说明当前 TestHub 平台在目标服务器 `172.31.119.49` 上的离线部署交付信息。内容基于 `2026-04-26` 当前运行状态整理。

## 1. 交付概况

- 部署方式：离线镜像部署
- 部署特点：服务器不保留平台源码，仅保留运行目录、初始化数据和持久化数据
- 目标服务器：`172.31.119.49`
- 部署目录：`/AIOps/apps/testhub-platform-offline-20260424`
- 数据持久化目录：`/AIOps/data/testhub-platform`
- 当前镜像版本：`IMAGE_TAG=20260424-2`

## 2. 访问入口

- 平台前端：`http://172.31.119.49:31080/`
- 平台登录页：`http://172.31.119.49:31080/login`
- Django 管理后台：`http://172.31.119.49:38000/admin/login/`
- 后端 API Base URL：`http://172.31.119.49:38000/`

## 3. 平台账号

- 平台管理员账号：`admin`
- 平台管理员密码：`Admin@Testhub2026`
- Django 管理后台账号：`admin`
- Django 管理后台密码：`Admin@Testhub2026`

说明：

- 平台前端和 Django 管理后台当前使用同一管理员账号
- 管理员账号已可用于平台登录

## 4. 数据库与缓存信息

### 4.1 MySQL

- 地址：`172.31.119.49`
- 端口：`13306`
- 数据库名：`testhub`
- 业务账号：`testhub`
- 业务密码：`Testhub@2026`
- Root 账号：`root`
- Root 密码：`TesthubRoot@2026`

### 4.2 Redis

- 地址：`172.31.119.49`
- 端口：`16379`
- 密码：`Redis@2026`

## 5. 当前运行服务

### 5.1 前端服务

- 容器名：`testhub-frontend`
- 镜像：`local/testhub-platform-frontend-bundle:20260424`
- 端口映射：`31080 -> 80`
- 作用：平台前端页面访问入口

### 5.2 后端服务

- 容器名：`testhub-backend`
- 镜像：`local/testhub-platform-backend-bundle:20260424-2`
- 端口映射：`38000 -> 8000`
- 作用：平台后端 API 服务

### 5.3 Celery Worker

- 容器名：`testhub-celery-worker`
- 镜像：`local/testhub-platform-backend-bundle:20260424-2`
- 作用：后台异步任务执行服务

### 5.4 MySQL

- 容器名：`testhub-mysql`
- 镜像：`local/testhub-mysql-bundle:8.0`
- 端口映射：`13306 -> 3306`

### 5.5 Redis

- 容器名：`testhub-redis`
- 镜像：`local/testhub-redis-bundle:7-alpine`
- 端口映射：`16379 -> 6379`

## 6. 目录清单

### 6.1 部署目录

- 运行根目录：`/AIOps/apps/testhub-platform-offline-20260424`
- Compose 目录：`/AIOps/apps/testhub-platform-offline-20260424/deploy/docker`
- Compose 文件：`/AIOps/apps/testhub-platform-offline-20260424/deploy/docker/docker-compose.offline.yml`
- 环境变量文件：`/AIOps/apps/testhub-platform-offline-20260424/deploy/docker/.env`
- 初始化数据目录：`/AIOps/apps/testhub-platform-offline-20260424/deploy/init-seed`

### 6.2 持久化数据目录

- 数据根目录：`/AIOps/data/testhub-platform`
- MySQL 数据：`/AIOps/data/testhub-platform/mysql`
- Redis 数据：`/AIOps/data/testhub-platform/redis`
- 应用数据：`/AIOps/data/testhub-platform/appdata`
- 媒体文件：`/AIOps/data/testhub-platform/media`
- 静态文件：`/AIOps/data/testhub-platform/static`
- 日志目录：`/AIOps/data/testhub-platform/logs`

## 7. 常用运维命令

先进入部署目录：

```bash
cd /AIOps/apps/testhub-platform-offline-20260424/deploy/docker
```

启动整套服务：

```bash
docker-compose --env-file .env -f docker-compose.offline.yml up -d
```

停止整套服务：

```bash
docker-compose --env-file .env -f docker-compose.offline.yml stop
```

重启整套服务：

```bash
docker-compose --env-file .env -f docker-compose.offline.yml restart
```

查看服务状态：

```bash
docker-compose --env-file .env -f docker-compose.offline.yml ps
docker ps --filter name=testhub
```

仅重建后端与任务服务：

```bash
docker-compose --env-file .env -f docker-compose.offline.yml up -d --force-recreate testhub-backend testhub-celery-worker
```

查看服务日志：

```bash
docker logs -f testhub-frontend
docker logs -f testhub-backend
docker logs -f testhub-celery-worker
docker logs -f testhub-mysql
docker logs -f testhub-redis
```

## 8. 当前环境配置摘要

- 时区：`Asia/Shanghai`
- 数据根目录：`/AIOps/data/testhub-platform`
- 镜像版本：`20260424-2`
- 初始化 seed 导入：已开启
- 媒体复制：已开启
- 静态文件收集：已开启
- 初始管理员创建：已开启

## 9. 初始化数据说明

当前交付已包含初始化数据导入能力，并已考虑以下数据类型：

- 平台数据库初始化数据
- 平台创建后需要自动导入的 seed 数据
- 当前已配置功能数据，包括：
- 版本
- JIRA 接口配置
- JIRA 编号 URL 前缀配置
- 邮件模板配置
- 目录树

说明：

- 初始化数据目录位于 `deploy/init-seed`
- 持久化数据不随容器重建丢失
- 当前部署已启用初始化导入相关开关

## 10. 当前交付状态

- 前端服务运行中
- 后端服务运行中
- Celery Worker 运行中
- MySQL 运行中且健康
- Redis 运行中且健康
- 平台当前为离线镜像部署
- 服务器未保留平台源码
- 平台数据已持久化到 `/AIOps/data/testhub-platform`

## 11. 交付注意事项

- 生产使用过程中请定期备份 `/AIOps/data/testhub-platform`
- 若后续升级镜像版本，优先保留现有 `.env` 和 `/AIOps/data/testhub-platform` 数据目录
- 如需重新导入初始化数据，应谨慎处理，避免覆盖现网数据
- 如需迁移服务器，建议同时迁移运行目录配置和持久化数据目录
