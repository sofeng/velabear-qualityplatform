# TestHub 私有化部署源码保护三阶段方案

## 目标

客户私有化部署仍采用镜像和容器服务交付，但客户不能通过导出镜像、进入容器、F12 或网络抓包拿到平台后端源码。前端浏览器代码无法做到不可见，因此目标是禁用 source map、避免暴露 Vue 源文件和敏感配置，并把核心逻辑留在后端。

## 总体方案

- 后端：使用 PyArmor 保护 `manage.py`、`backend/`、`apps/`、`tools/`，客户交付镜像只复制保护产物，不复制原始 Python 源码。
- 镜像：保留普通 `backend.container.Dockerfile` 用于开发和内部调试，新增 `backend.protected.Dockerfile` 用于客户交付。
- 前端：继续使用 Vite 生产构建，保持 `sourcemap: false`，交付 nginx 镜像内的 `frontend/dist`。
- 网络暴露面：生产环境默认关闭 OpenAPI schema、Swagger、Redoc，避免接口结构被无意公开。
- 验证：交付前扫描后端镜像内的明文源码特征、前端 `.map` 和 `sourceMappingURL`。

## 阶段一：最快可用版

目标：先解决“客户导出后端镜像能看到完整 Python 源码”的主要风险。

交付内容：
- 新增 `deploy/docker/backend.protected.Dockerfile`。
- Docker builder 阶段安装免费版 PyArmor 并生成保护产物。
- Runtime 阶段只复制保护后的 `/app/manage.py`、`/app/backend`、`/app/apps`、`/app/tools`。
- 免费版 PyArmor 对大脚本有限制，因此默认使用 trial-hybrid：小脚本用 PyArmor，大脚本编译为 legacy `.pyc` 二进制并移除 `.py`，测试文件不进入客户镜像。
- 保留现有 `allure`、`deploy/docker`、`deploy/release`、`deploy/init-seed` 等运行资源。
- 新增 `deploy/docker/docker-compose.protected.yml`，用于在现有 bundle compose 上覆盖后端构建 Dockerfile。
- 新增 `deploy/protection/build_protected_backend.ps1`，用于单独构建受保护后端镜像。
- 受保护 Dockerfile 使用 BuildKit secret mount；构建脚本会自动设置 `DOCKER_BUILDKIT=1`。

验证标准：
- 受保护后端镜像能构建成功。
- 容器内没有可读的原始后端业务源码。
- 原开发镜像和开发流程不受影响。

## 阶段二：生产可交付版

目标：让受保护镜像具备正式客户交付能力。

交付内容：
- 发布脚本增加 `-ProtectBackend` 开关，可以选择构建受保护后端镜像。
- 新增 `deploy/protection/scan_protected_release.ps1`，交付前扫描后端源码泄露和前端 source map。
- Django 生产配置新增 `ENABLE_API_DOCS` 开关，容器默认关闭 `/api/schema/`、`/api/docs/`、`/api/redoc/`。
- Docker compose 显式传入 `ENABLE_API_DOCS=0`。

验证标准：
- `build_release_bundle.ps1 -ProtectBackend` 可以产出受保护后端镜像。
- `build_registry_release.ps1 -ProtectBackend` 可以推送受保护后端镜像。
- 扫描脚本发现明文源码、source map 或 sourceMappingURL 时失败。

## 阶段三：加固版预留

目标：为后续 PyArmor Pro/Group 授权、RFT/BCC、客户授权绑定留好发布入口。

交付内容：
- `backend.protected.Dockerfile` 支持 `PYARMOR_OPTIONS`，免费版默认不启用 Pro 功能。
- `PYARMOR_MAX_SCRIPT_BYTES` 默认 30000，表示超过该大小的脚本在免费版下转为 `.pyc`；购买 Pro/Group 后可设为 0，改为全量 PyArmor。
- 构建脚本支持传入 PyArmor license 文件，并通过 Docker BuildKit secret 注入，避免 license 进入镜像层。
- 发布脚本支持 `-PyArmorVersion`、`-PyArmorOptions`、`-PyArmorMaxScriptBytes`、`-PyArmorLicenseFile`。
- 文档列出后续 Pro/Group 推荐参数。

后续 Pro/Group 建议：
- 普通保护：`--mix-str --assert-import`
- Django/Web 优先：`--enable-rft`
- 核心模块选择性增强：按模块评估后再启用 BCC，避免破坏 Django 动态导入、Celery task discovery 和反射逻辑。

## 常用命令

构建免费版受保护后端镜像：

```powershell
.\deploy\protection\build_protected_backend.ps1 -ReleaseTag protected-local -TagLatest
```

用 compose 覆盖文件构建本地受保护 bundle：

```powershell
docker compose -f deploy/docker/docker-compose.bundle.yml -f deploy/docker/docker-compose.protected.yml build testhub-backend-init
```

构建离线交付包时启用后端保护：

```powershell
.\deploy\release\build_release_bundle.ps1 -ReleaseTag 20260608-protected -Components backend,frontend -ProtectBackend
```

扫描交付镜像：

```powershell
.\deploy\protection\scan_protected_release.ps1 `
  -BackendImage local/testhub-platform-backend-bundle:20260608-protected `
  -FrontendImage local/testhub-platform-frontend-bundle:20260608-protected
```

使用 PyArmor Pro/Group license 构建：

```powershell
.\deploy\protection\build_protected_backend.ps1 `
  -ReleaseTag protected-pro `
  -PyArmorLicenseFile C:\secure\pyarmor-regfile.zip `
  -PyArmorMaxScriptBytes 0 `
  -PyArmorOptions "--mix-str --assert-import" `
  -TagLatest
```

## 边界说明

- F12 中一定能看到浏览器运行所需的前端 JS，这是浏览器应用的基本特性；本方案保证不发布 Vue 源码和 source map。
- 抓包能看到用户有权限访问的 API 响应；本方案不能隐藏业务数据本身，只能避免后端源码、调试堆栈、接口文档和敏感配置泄露。
- 免费版 PyArmor 用于先跑通流程；正式商业交付建议升级 PyArmor Pro 或 Group。
- trial-hybrid 中 `.pyc` 只是二进制化，不等同于 PyArmor Pro/BCC；它满足“镜像内无明文源码”的 PoC 要求，但正式客户交付应使用 Pro/Group 全量保护。
