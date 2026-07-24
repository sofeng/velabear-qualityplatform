# Workbench Studio · P0 设计：数据模型 + 接口契约 + 解耦架构

> 状态：P0 技术设计（**待评审**，未落库）。上层愿景见 `workbench-studio-composable-platform-plan.md`。
> 三条硬约束贯穿全文：
> 1. **企业级** —— 多租户、版本化、RBAC、生命周期治理、审计、软删除、可回滚。
> 2. **真解耦** —— 平台内核**领域无关**，不认识"需求/用例/缺陷"，只认"内容类型契约"；模块间只通过 `(资源 key, 版本范围)` 引用，绝不硬编码彼此。
> 3. **行业可复用** —— 一套"方案包(SolutionPack)"即可一键装出某行业的完整 AI 工作台；现有 AI 研发全链路只是**第一个方案包**。

---

## 0. P0 范围与边界

**P0 做**：立起对象模型 + 注册表 + 契约校验引擎 + 数据总线骨架 + 工作台组装器(最小)；把现有 9 环节页签迁成**预置定义（A 类·壳内渲染，无容器）**；打包成第一个 SolutionPack。

**P0 不做**（后续分期）：C 类容器运行时 + 网关 + Tab SDK 跨容器（P3）、市场分享/fork（P4）、DAG 并行编排（P5）。P0 的数据模型**预留**这些字段与扩展点，但不实现运行时。

---

## 1. 分层架构（解耦总纲）

```
L4 方案包层   SolutionPack（行业模板包：打包 L2 定义 + L3 模板，一键安装/卸载/升级）
L3 实例层     TabInstance · Workspace · DataArtifact(数据槽)
L2 资源层     ContentType · RenderTool · AuthoringTool · Skill · TabType · Agent   ← 全部可注册/版本化/可治理
L1 契约层     ContentType Schema · Tool Manifest · TabType Manifest · Agent Schema · Tab SDK 协议
L0 平台内核   注册表 · 内容类型契约引擎 · 数据总线 · 运行时网关 · AI会话底座 · RBAC/审计   ← 领域无关
```

**第一原则（真解耦的关键）**：L0 内核对"需求/用例/原型"零认知。这些都是 L2 的预置 `ContentType` + `TabType`，装在"AI 研发方案包"里。换一个行业 = 换一个方案包，内核不改一行。

**第二原则（引用即契约）**：任何跨资源引用都写成 `ref = {key, version_range}`（如 `content_type: "requirement-analysis@^1.2"`），由注册表解析，**不用数据库外键硬绑**。这样资源可独立演进、可被市场 fork、可跨租户复用。

---

## 2. 核心数据模型（字段级）

### 2.0 企业级公共基类 `ResourceBase`（所有 L2/L3 资源继承）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 主键 |
| `key` | slug | 稳定业务标识（跨版本不变，供 ref 引用） |
| `name` / `description` | str | 展示名/描述（支持 i18n 见 §6） |
| `org_id` | FK | 所属组织（多租户隔离） |
| `owner_id` | FK(User) | 拥有者 |
| `visibility` | enum | `private` / `org` / `public`（市场可见性） |
| `version` | semver | 资源版本（如 `1.3.0`） |
| `status` | enum | 生命周期：`draft`/`in_review`/`published`/`deprecated`/`archived` |
| `tier` | enum | 开放层级：`L1`配置 / `L2`沙箱 / `L3`官方扩展 |
| `review_status` | enum | `none`/`pending`/`approved`/`rejected` |
| `source` | enum | `official`/`user`/`forked` |
| `forked_from` | ref | fork 血缘（市场复用溯源） |
| `metadata` | JSON | 扩展位 |
| `created_by/at` `updated_by/at` | | 审计 |
| `deleted_at` | datetime | 软删除 |

> 约束：`(org_id, key, version)` 唯一；`(org_id, key)` + `status=published` 唯一"当前发布版"。

### 2.1 `ContentType` 内容类型（**解耦中枢**）

| 字段 | 说明 |
|---|---|
| `category` | 大类：`page`/`canvas`/`mindmap`/`table`/`doc`/`kanban`/`chart`/`clarification`/`prototype`/`code`/`file`/`timeline`/`map`… |
| `data_schema` | JSON Schema：该类型数据的**契约**（校验 producer/consumer 的核心依据） |
| `ui_hints` | 渲染提示（默认视图、可编辑字段、字段分组） |
| `samples` | 样例数据（市场预览、AI 生成参照） |
| `compat_range` | 向后兼容的 semver 范围（schema 演进用） |
| `migrations` | schema 版本迁移钩子引用（旧数据→新 schema） |

### 2.2 `RenderTool` 渲染工具（类型的消费者）

| 字段 | 说明 |
|---|---|
| `renders` | `[content_type_ref...]`（可渲染哪些内容类型） |
| `delivery` | `builtin`(内置原语) / `iframe` / `webcomponent` / `service`(容器) |
| `runtime_class` | `A`壳内 / `B`共享工具容器 / `C`独立服务 |
| `capabilities` | `{editable, interactive, streaming, exportable}` |
| `entry` | 内置组件名 / iframe URL 模板 / 镜像+manifest 引用 |
| `config_schema` | 实例化时可配置项的 schema |

### 2.3 `AuthoringTool` 制作工具（类型的生产者）

| 字段 | 说明 |
|---|---|
| `produces` | `[content_type_ref...]` |
| `invocation` | `mcp` / `skill` / `external_url` / `builtin` |
| `endpoint` / `mcp_ref` | 接入点 |
| `config_schema` | 配置项 schema |

> 说明：draw.io 类工具同时登记为 RenderTool + AuthoringTool（既渲染又制作）。

### 2.4 `Skill`（扩展现有 `CapabilityExecution`）

新增声明 `output_content_type: content_type_ref`（把现有 `output_payload.type` 的 20+ 枚举升级为对内容类型的显式契约）。其余复用现有能力运行时。

### 2.5 `TabType` 页签类型（蓝图 / "类"）

| 字段 | 说明 |
|---|---|
| `content_type_ref` | 承载的内容类型 |
| `render_tool_ref` | 绑定渲染工具 |
| `authoring_tool_ref` | 可选，绑定制作工具 |
| `bound_skills` | `[skill_ref...]`（可在此页签调用的 skill） |
| `actions` | `[{key, label, kind:read/write, requires_permission, confirm_level}]` |
| `data_supply` | `static` / `emit` / `tool`（数据供给模式，可多选） |
| `runtime_class` | `A/B/C` |
| `manifest` | 见 §4.2 |
| `default_config` | 实例化默认配置 |

> **合法性校验（契约引擎）**：`render_tool.renders ∋ content_type` 且（有制作工具时）`authoring_tool.produces ∋ content_type` 且 `bound_skills[*].output_content_type` 与 `content_type` 兼容（semver）。不通过 → 允许保存但降级 `draft` + 标记"通用产物/待审核"。

### 2.6 `TabInstance` 页签实例（"对象"）

| 字段 | 说明 |
|---|---|
| `tab_type_ref` | `key@pinned_version`（**钉版本**，保证稳定） |
| `workspace_id` | 所属工作台 |
| `data_binding` | `{mode, source}`：static(导入/URL) / emit(哪个 skill/agent 投递) / tool(绑哪个工具会话) |
| `layout` | `{x,y,w,h}` 或分栏位置 |
| `state_ref` | 指向平台托管状态（决策③：页签不自持存储） |
| `scoped_token` | 该实例的作用域签名 token（P3 容器通讯用，P0 预留） |

### 2.7 `Workspace` 工作台

| 字段 | 说明 |
|---|---|
| `layout` | `grid` / `tabs` / `free` 编排模型 |
| `tab_instances` | 有序实例列表 |
| `is_template` | 是否为可复刻模板 |
| `solution_pack_ref` | 来自哪个方案包（可空） |
| `sharing` | 复用 `visibility` |

### 2.8 `DataArtifact` 数据总线槽（决策④：平台中介）

| 字段 | 说明 |
|---|---|
| `workspace_id` | 作用域 |
| `slot_key` | 槽标识（编排连线读写此 key） |
| `content_type_ref` | 槽的类型契约 |
| `payload` | 数据（按 content_type.data_schema 校验） |
| `revision` | 版本号（DAG 阶段并发合并用，P0 单调递增） |
| `producer` | `{kind: tab_instance/skill/agent, id}` |
| `history` | 修订历史（回滚/审计） |

### 2.9 `AgentDefinition` + `AgentStep`（编排者）

| AgentDefinition | 说明 |
|---|---|
| `steps` | 有序步骤（P0 线性） |
| `control_flow` | `linear`（P0）；`dag`（P5 预留） |
| `entry_session_type` | 作为会话类型出现的标识 |
| `enabled` | 启用才可选为会话类型 |

| AgentStep | 说明 |
|---|---|
| `skill_ref` | 本步调用的 skill |
| `input_slots` | `[slot_key...]`（从数据总线读输入） |
| `output_slot` | 产出写入的槽 + 绑定的 tab_instance |
| `human_gate` | 是否人工确认卡点（写库/部署/直接执行**强制** true 不可配为自动） |

### 2.10 `SolutionPack` 行业方案包（**行业复用中枢**）

| 字段 | 说明 |
|---|---|
| `industry` | 行业标签（研发/法务/医疗/教育/运营…） |
| `bundles` | 打包引用：`content_types[] / tools[] / skills[] / tab_types[] / agents[] / workspace_templates[]` |
| `install_manifest` | 安装清单（依赖、权限、默认配置、迁移） |
| `version` | 包版本 |

安装 = 把包内定义注册到目标 org + 生成工作台模板；卸载/升级走 install_manifest 的迁移钩子。

---

## 3. 契约匹配引擎（真解耦的执行者）

- **中枢**：一切经 `ContentType` 协商，producer/consumer 不直接依赖。
- **引用解析**：`ref = key@version_range` → 注册表按 semver 解析到具体版本；实例层钉版本，资源层可浮动。
- **校验时机**：保存时静态校验（三处：新建/编辑/导入）+ 运行时兜底；不通过则降级而非硬失败。
- **版本兼容**：ContentType schema 演进用 semver + `compat_range` + `migrations`；破坏性变更升 major，实例保持钉旧版直到迁移。

---

## 4. 接口契约（schema 草案）

### 4.1 ContentType manifest

```json
{
  "key": "requirement-analysis",
  "version": "1.2.0",
  "category": "clarification",
  "data_schema": { "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": { "items": {"type":"array"}, "mindmap_seed": {"type":"object"} }, "required": ["items"] },
  "compat_range": "^1.0.0",
  "ui_hints": { "default_view": "list", "editable_fields": ["items[].content"] },
  "samples": ["./samples/req-analysis.json"]
}
```

### 4.2 TabType manifest (`tabtype.manifest.json`，会话式开发产物)

```json
{
  "key": "requirement-analysis-tab",
  "version": "1.0.0",
  "content_type": "requirement-analysis@^1.0",
  "render_tool": "builtin-clarification-view@^1",
  "authoring_tool": null,
  "bound_skills": ["baseline-requirement-analysis@^2"],
  "data_supply": ["emit"],
  "runtime_class": "A",
  "actions": [
    {"key":"edit","label":"AI编辑","kind":"write","confirm_level":"inline"},
    {"key":"accept","label":"接受写回","kind":"write","requires_permission":"action:req:accept","confirm_level":"strong"}
  ]
}
```

### 4.3 Tab SDK · 前端 postMessage 协议（信封 + 消息类型）

```json
{ "v": 1, "instance_id": "ti_xxx", "type": "data.push", "payload": {}, "trace_id": "..." }
```

消息类型：`host→tab`: `init` / `focus` / `data.push` / `action.invoke` / `config.update`；`tab→host`: `ready` / `data.request` / `data.emit` / `action.result` / `event` / `resize` / `error`。

### 4.4 Tab SDK · 后端 API（P0 定义、P3 落容器）

`POST /api/wb/tabs/{instance}/register` · `GET .../health` · `GET/PUT .../slots/{slot_key}`（数据总线读写，按 content_type 校验）· `WS .../subscribe`（订阅槽变更）· `POST .../session-bind`（绑 AI 会话）。鉴权：实例 `scoped_token`（最小权限）。

### 4.5 Agent 步骤 schema

```json
{
  "control_flow": "linear",
  "steps": [
    {"skill_ref":"project-clarification@^1","output_slot":"clarify","output_tab":"clarify-tab","human_gate":true},
    {"skill_ref":"baseline-requirement-analysis@^2","input_slots":["clarify"],"output_slot":"req","output_tab":"req-tab","human_gate":true}
  ]
}
```

---

## 5. 权限 / 治理 / 审计（企业级）

- **RBAC**：复用现有 `PermissionItem`/`Role`；资源级 ACL（owner/org/public + 动作权限码）。
- **生命周期闸门**：`draft→in_review→published→deprecated→archived`；`published` 才可被他人引用/装入方案包。
- **三层开放**：L1 配置(人人可用) / L2 沙箱(审核+强隔离) / L3 官方扩展(认证+代码审查上架)。
- **写回收紧**：`actions.kind=write` 且写核心业务表的动作，强制 `confirm_level=strong` + 来源标记；自研页签默认禁用写回。
- **审计**：独立 `AuditLog`（who/what/resource/version/action/time），资源变更与写回全留痕。

---

## 6. 多租户 · 版本 · 升级 · i18n

- **多租户**：`org_id` 贯穿所有资源；跨 org 复用只经市场 `public` 发布。
- **版本钉扎**：实例钉 tab_type 版本；资源可发新版；升级由用户显式触发，走 content_type `migrations`。
- **i18n**：`name/description/label` 用 `{locale: text}` 或翻译键；ContentType `ui_hints` 支持多语言字段名。

---

## 7. 行业复用：SolutionPack 机制

- **结构**：一包 = 若干 ContentType + Tool + Skill + TabType + Agent + Workspace 模板 + install_manifest。
- **AI 研发方案包（首个参考实现）**：装入即得现有全链路工作台。
- **其他行业示例**：法务(合同审查/条款比对/风险清单)、医疗(病历结构化/指南比对)、教育(教案/题库/学情看板)、运营(活动编排/数据看板)——各自只需一包，内核零改动。

---

## 8. 现有 9 环节 → 预置定义映射（AI 研发方案包内容）

| 环节 | ContentType | RenderTool(A类) | 绑定 Skill(现有) | data_supply | 现有写回 |
|---|---|---|---|---|---|
| 项目澄清 | `project-clarification` | clarification-view | 新项目启动澄清 | emit | — |
| 需求澄清 | `requirement-clarification` | clarification-view | 需求澄清 | emit | 候选更新 |
| 需求分析 | `requirement-analysis` | clarification-view + mindmap | 基线需求分析 | emit | accept→Requirement |
| 原型设计 | `prototype`/`html-page` | iframe-html | 应用原型生成 | emit/tool | editUrl 编辑 |
| 测试设计 | `test-design` | table/doc | 测试设计 | emit | accept→TestCase |
| 设计选型 | `design-tokens` | tokens-preview | 设计工程(aiDesignEngineering) | emit | 选定持久化 |
| 开发实现 | `dev-task` | doc/kanban | flow_ai_dev_full_cycle 步骤 | emit | — |
| 代码展示 | `code-bundle` | code-viewer(A→C) | 产品实现 | emit | 预览/下载 |
| 上传文件 | `file` | file-view | — | static | — |

> "一句话生成应用" = 一个 `AgentDefinition`(线性) 串起上述 skill，逐环节把产出写入对应 slot/tab；code↔test 回退循环作为唯一硬编码例外内置（沿用既有 §12 结论）。

---

## 9. P0 落地拆解（交付物 + 顺序）

1. 新建 `apps/workbench/` app：`ResourceBase` mixin + 9 个模型（§2）+ 迁移。
2. **注册表服务** `registry.py`：ref 解析(semver)、发布/引用校验。
3. **契约校验引擎** `contracts.py`：ContentType schema 校验 + TabType 合法性校验 + 降级策略。
4. **数据总线**（P0 进程内）：DataArtifact 读写 + 槽订阅（内存/DB，P3 升 WS 跨容器）。
5. **预置定义 fixtures**：9 环节 ContentType/RenderTool/TabType/Agent + AI 研发 SolutionPack。
6. **列表/详情 API + Admin**：8 个注册表页的后端。
7. **最小组装器**（前端）：页签类型市场选型 → 建实例 → 排序 → 存工作台（A 类壳内渲染）。
8. 测试：契约校验、ref 解析、数据总线读写、方案包安装、9 环节渲染冒烟。

**P0 明确不含**：C 类容器运行时/网关/Tab SDK 跨容器、市场 fork/分享、DAG。数据模型已预留字段。

---

## 10. 待确认点

1. `apps/workbench/` 命名是否 OK（或 `apps/studio/`）。
2. ContentType `data_schema` 用 JSON Schema（推荐，工具链成熟） vs 自定义 DSL。
3. 现有 `CapabilityExecution` 是**原地扩展** `output_content_type`（推荐，改动小） vs 新表映射。
4. P0 数据总线：进程内 + DB 落库（推荐） vs 直接上 Redis/WS。
