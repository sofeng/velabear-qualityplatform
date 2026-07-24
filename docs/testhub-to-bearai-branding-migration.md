# TestHub 字样迁移为 BearAI 的方案与执行记录

记录日期：2026-06-20

## 目标

将平台用户可见的 `TestHub` / `TestHub AI` 品牌展示迁移为 `BearAI` / `BearAI AI`，同时保留历史数据、运行协议、容器、环境变量、前端缓存 key、AI 会话 marker 等兼容标识，避免旧会话、旧记录、本地 Agent、Codex Runtime、已生成产物和部署环境失效。

本次迁移采用“展示层改名 + 兼容桥接”的方案，不做全仓库无差别替换。

## 核心原则

1. 用户看得见的品牌文案改为 `BearAI`。
2. AI/Codex 提示词、内置 Skill、能力市场、运行日志等展示层内容改为 `BearAI`。
3. 旧数据中 `provider=TestHub` 不直接迁移字段值，通过序列化和查询兼容桥显示为 `BearAI`。
4. 新配置优先使用 `BEARAI_*`，旧 `TESTHUB_*` 继续兼容。
5. 协议、marker、容器名、镜像名、localStorage key、历史 schema、旧 header 等内部标识不做硬改。
6. 后续如需彻底删除旧标识，必须先做专项数据迁移、协议升级和历史产物兼容验证。

## 已改动项

### 统一品牌常量

- 新增后端品牌 helper：`apps/core/branding.py`
  - `PLATFORM_BRAND_NAME = BearAI`
  - `PLATFORM_BRAND_AI_NAME = BearAI AI`
  - `PLATFORM_LOG_PREFIX = [BearAI]`
  - `display_brand_provider()`
  - `provider_filter_values()`
- 新增前端品牌 helper：`frontend/src/utils/brand.js`
  - `PLATFORM_BRAND_NAME`
  - `PLATFORM_BRAND_AI_NAME`
  - `LEGACY_PLATFORM_BRAND_NAME`
  - `normalizeBrandProvider()`
  - `BRAND_PROVIDER_OPTIONS`

### Provider 展示与查询兼容

- 旧记录 `provider=TestHub` 通过 serializer 显示为 `BearAI`。
- 前端能力来源、能力资产、能力市场、AI 工坊等 provider 选项改为 `BearAI`。
- 后端查询 `provider=BearAI` 时同时查询 `BearAI` 和旧值 `TestHub`。
- 涉及文件：
  - `apps/assistant/serializers.py`
  - `apps/assistant/views.py`
  - `frontend/src/views/ai-generation/AIWorkshopManager.vue`
  - `frontend/src/views/ai-generation/CapabilityAssetList.vue`
  - `frontend/src/views/ai-generation/CapabilityMarketplace.vue`
  - `frontend/src/views/ai-generation/AIProductCreate.vue`
  - `frontend/src/views/ai-generation/AIEnterpriseProjectWorkbench.vue`

### AI/Codex 运行时品牌展示

- Codex Runtime 新日志前缀改为 `[BearAI]`。
- 答案提取逻辑同时识别并过滤 `[BearAI]` 和历史 `[TestHub]` 平台日志。
- Codex Runtime 环境变量新增 `BEARAI_PLATFORM_*`，同时保留旧 `TESTHUB_PLATFORM_*`。
- AI/Codex 提示词中的平台品牌展示改为 `BearAI`。
- 涉及文件：
  - `apps/assistant/codex_cli_runtime.py`
  - `apps/assistant/chat_context.py`
  - `apps/assistant/local_chat.py`
  - `apps/ai_development/ai_tools/codex_cli_controller.py`

### 内置能力、Skill、能力市场品牌展示

- 内置官方 Skill / Prompt 在运行时统一将展示文案品牌化为 `BearAI`。
- 能力市场精选目录 provider 改为 `BearAI`。
- 完整系统生成器 Skill 文案改为 `BearAI`，但保留旧 skill code/name 标识。
- 能力安装默认描述改为 `BearAI AI Workshop`。
- 涉及文件：
  - `apps/assistant/new_project_runtime.py`
  - `apps/assistant/marketplace.py`
  - `apps/assistant/codex_capability_sync.py`
  - `apps/assistant/bootstrap.py`
  - `apps/assistant/capability_runtime.py`
  - `apps/assistant/tool_gateway.py`

### 前端展示文案

- AI 产品创建、AI 工坊、能力资产、能力市场等页面的品牌展示改为 `BearAI`。
- 本地 Agent 页面展示文案改为 `BearAI Local Agent`，但协议仍保留 `testhub-agent://`。
- 通知、XMind 导出等用户可见来源文案改为 `BearAI`。
- 涉及文件：
  - `frontend/src/utils/brand.js`
  - `frontend/src/services/defectNotifications.js`
  - `frontend/src/utils/xmindMinder.js`
  - `frontend/src/views/manual-testcases/RecordingScriptManager.vue`
  - `frontend/src/views/manual-testcases/SnapshotRecordingManager.vue`
  - `frontend/src/views/manual-testcases/VisualFlowEditor.vue`

### 其他兼容增强

- 源码仓库路径环境变量新增 `BEARAI_SOURCE_REPO` / `BEARAI_SOURCE_REPO_DIR` 优先读取，旧 `TESTHUB_SOURCE_REPO` / `TESTHUB_SOURCE_REPO_DIR` 继续兼容。
- 公开访问地址新增 `BEARAI_PUBLIC_HOST` 优先读取，旧 `TESTHUB_PUBLIC_HOST` 继续兼容。
- 涉及文件：
  - `apps/assistant/views.py`
  - `apps/knowledge/services.py`
  - `apps/ai_development/tasks.py`

## 本次明确未改动项

以下内容属于协议、历史数据、运行时约定或部署标识，暂不改动：

- 环境变量协议：
  - `TESTHUB_REPLAY_CDP_URL`
  - `TESTHUB_PLAYWRIGHT_*`
  - `TESTHUB_FLOW_*`
  - `TESTHUB_PLATFORM_*`
  - `TESTHUB_CODEX_*`
- HTML / AI 会话 marker：
  - `TESTHUB_WORKSPACE_ARTIFACT`
  - `TESTHUB_CODEX_HTML_WORKSPACE`
  - `TESTHUB_CODEX_RUN_METADATA`
  - `TESTHUB_PROTOTYPE_AGENT`
  - `TESTHUB_KNOWLEDGE_CHART`
- 本地 Agent 协议与 header：
  - `testhub-agent://`
  - `X-TestHub-Agent-Token`
  - `testhub-local-playwright-agent`
- 前端缓存和事件 key：
  - `testhub-navigation-theme`
  - `testhub-ai-model-configs-changed`
  - `testhub-requirement-*`
  - `testhub-flow-*`
- Docker、镜像、容器、volume 默认名：
  - `testhub/ai-dev:latest`
  - `local/testhub-platform-codex-runtime:latest`
  - `testhub-codex-*`
  - `testhub_codex`
- 历史 schema、枚举、文件类型：
  - `testhub_json`
  - `testhub-playwright-recording`
  - 旧 migration 中的 `TestHub`
- 旧数据实际字段值：
  - 数据库中已有 `provider=TestHub` 暂不批量改值，只通过展示/查询兼容桥处理。
- 仓库路径、部署栈、历史文档中的 `testhub`：
  - 例如本地路径 `D:\AI\syswin-testhub\testhub-platform-src`
  - 历史文档、演示材料、压缩包、截图、PPT 等非运行主路径资料。

## 未改动原因

这些标识被脚本、Agent、旧会话、前端缓存、运行时容器、历史产物解析器或数据库历史记录直接引用。贸然替换会导致：

- 历史 AI 会话产物无法解析。
- 本地 Agent 无法唤起或鉴权失败。
- Playwright 回放脚本找不到运行时变量。
- Codex Runtime 无法识别历史 workspace marker。
- 旧 provider 记录筛选不到。
- Docker 容器、镜像、volume 名与现有环境不匹配。
- 前端用户缓存丢失或事件同步失效。

## 验证记录

已完成以下验证：

- `python -m py_compile ...` 通过。
- `python manage.py check` 通过。
- `npm --prefix frontend run build` 通过。
- 已同步并重启：
  - `testhub-fresh-backend`
  - `testhub-fresh-celery-worker`
  - `testhub-fresh-ai-dev-worker`
  - `testhub-fresh-frontend`
- 容器内 `python manage.py check` 通过。
- `http://localhost:42080/` 返回 200。
- `http://localhost:42080/ai-generation/products/all` 返回 200。
- 容器内验证：
  - `display_brand_provider('TestHub') -> BearAI`
  - `provider_filter_values('BearAI') -> ['BearAI', 'TestHub']`
  - 内置官方 Skill 运行时文案包含 `BearAI`，不包含 `TestHub`。
- 前端构建产物中包含 `BearAI` 品牌常量。

构建过程中仅出现既有 Sass legacy API 和 chunk size warning，不影响本次品牌迁移功能。

## 后续建议

1. 新增品牌文案时统一使用 `apps/core/branding.py` 和 `frontend/src/utils/brand.js`，不要再硬编码 `TestHub` 或 `BearAI`。
2. 新增环境变量优先使用 `BEARAI_*`，但涉及平台运行时能力时继续提供 `TESTHUB_*` 兼容回退。
3. 如果未来要彻底清理 `testhub` 内部标识，需要单独立项，至少包括：
   - 数据库 provider 数据迁移。
   - Agent 协议升级和旧协议转发。
   - HTML marker 双写和历史解析兼容。
   - localStorage key 迁移。
   - Docker 镜像、容器、volume 迁移策略。
   - 历史 AI 会话和生成产物回放验证。
4. 当前阶段不建议继续做全局字符串替换。
