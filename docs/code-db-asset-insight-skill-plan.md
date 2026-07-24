# 代码与数据库资产洞察 Skill 方案

更新日期：2026-06-25

本文记录 TestHub 平台后续建设“代码排查、代码关系图、幽灵代码识别、数据库排查、数据库 ER 图”的短平快方案，并说明当前【思源质量 / 知识库助手】已经实现的代码关联关系图和页面菜单梳理机制。

## 1. 核心结论

平台不需要把大量扫描器、MCP、数据治理系统直接暴露给用户或 Codex CLI。

推荐做成一个统一 Skill，例如：

```text
testhub-asset-insight
```

该 Skill 作为 Codex CLI 和平台页面的统一入口，底层封装一组轻量开源工具：

```text
Codex CLI / 知识库助手
  -> TestHub Skill / 平台 Tool API
  -> scanner container / backend service
  -> JSON / SARIF / graph artifacts
  -> 平台页面、工作区附件、知识库证据包
```

这样用户只感知“资产洞察 / 代码与数据库体检”能力，不需要理解每个底层工具。

## 2. 第一版范围

第一版只解决高价值、可落地的能力：

- 扫描多语言代码仓库，生成符号索引、引用关系、文件依赖关系。
- 排查疑似幽灵代码：未引用函数、未引用文件、未命中路由、未命中菜单入口、未命中定时任务、未命中测试覆盖等。
- 生成代码关系图：仓库 -> 模块 -> 文件 -> 类/函数/接口 -> 调用/引用/路由/API 关系。
- 扫描数据库 Schema：库、表、字段、主键、外键、索引、字段类型、字段备注。
- 生成 ER 图数据：不一次性渲染几千张表，而是支持搜索、局部关系展开、按模块/Schema/关键字过滤。
- 输出统一报告和图谱数据，供知识库助手回答、Codex CLI 排查、前端画布展示。

## 3. 推荐底层工具

### 3.1 代码扫描

第一版建议内置：

| 工具 | 用途 |
| --- | --- |
| `ripgrep` | 快速文本检索、引用搜索、入口搜索、路由/配置搜索 |
| `git` | 最近变更、提交历史、文件生命周期、作者和活跃度 |
| `universal-ctags` | 多语言符号索引，识别类、函数、方法、变量、接口等 |
| `semgrep` | 多语言规则扫描，识别危险代码、废弃写法、框架入口、接口模式 |

按语言可选增强，不作为第一版必选：

| 语言/生态 | 可选工具 | 用途 |
| --- | --- | --- |
| TypeScript / JavaScript | `knip` | 未使用导出、依赖、文件排查 |
| Python | `vulture` | 未使用代码排查 |
| Go | `staticcheck` | 静态问题与未使用代码 |
| Java | `jdeps` / `jdtls` / `maven` 插件 | 依赖和调用关系增强 |
| C/C++ | `clangd` / `clang-tidy` | 编译数据库可用时增强分析 |

### 3.2 数据库扫描

第一版建议内置：

| 工具 | 用途 |
| --- | --- |
| `SchemaCrawler` | 跨数据库 Schema 元数据抽取，适合生成表、字段、主外键、索引信息 |
| Java runtime | 运行 SchemaCrawler |

备选工具：

| 工具 | 适用场景 |
| --- | --- |
| `tbls` | 轻量数据库文档和 ER 输出，适合 MySQL/PostgreSQL 等常见库 |
| `SchemaSpy` | 静态 HTML 数据库文档和关系图，适合离线归档 |
| `DBHub MCP` | 需要 MCP 形式直接访问数据库时可评估 |
| `MCP Toolbox for Databases` | 需要统一 MCP 数据库工具层时可评估 |

第一版不建议上 OpenMetadata、Trino、Ranger、OpenFGA 这类重型平台，除非后续明确转向企业级数据治理。

## 4. Skill 对外能力

对 Codex CLI 和知识库助手暴露一个 Skill，内部提供以下工具函数：

| 工具函数 | 输入 | 输出 |
| --- | --- | --- |
| `scan_codebase` | 仓库路径、分支、include/exclude | `code_symbols.json`、`code_files.json` |
| `find_ghost_code` | 仓库路径、语言、入口规则 | `ghost_code_report.json/md` |
| `build_code_relation_graph` | 仓库路径、范围、深度 | `code_reference_graph.json` |
| `inspect_database_schema` | 数据库连接配置或平台环境配置 ID | `db_schema.json` |
| `generate_database_er_graph` | schema、过滤条件、中心表、展开深度 | `er_graph.json`、`er.mmd` |
| `search_table_or_field` | 关键字、schema、表范围 | 表/字段搜索结果 |

Codex CLI 默认不直接拿数据库明文密码。优先由平台保存连接配置，Skill 通过平台受控 API 获取临时授权或扫描结果。

## 5. 输出文件约定

每次扫描生成一个 artifacts 目录：

```text
asset-insight-runs/<run_id>/
  code_symbols.json
  code_files.json
  code_reference_graph.json
  ghost_code_report.json
  ghost_code_report.md
  db_schema.json
  er_graph.json
  er.mmd
  er.svg
  scan_summary.md
```

核心 JSON 结构建议统一为：

```json
{
  "run_id": "20260625-001",
  "scope": {
    "repository": "xxx",
    "branch": "main",
    "database": "xxx"
  },
  "nodes": [],
  "edges": [],
  "findings": [],
  "sources": [],
  "warnings": []
}
```

## 6. ER 图展示策略

有些系统可能有几千张表、几十万字段，不适合一次性完整渲染到画布。

推荐展示方式：

- 左侧：Schema / 表 / 字段搜索树。
- 中间：局部 ER 关系画布，只展示中心表和 N 层邻居。
- 右侧：表字段、索引、外键、备注、引用来源详情。
- 顶部：按模块、Schema、表名前缀、关键字、关系深度过滤。
- 导出：Mermaid、SVG、PNG、JSON、Markdown 文档。

前端画布可以复用平台已有 AntV X6 做局部交互式 ER 画布。X6 支持大画布、缩放、拖拽、节点交互，但不建议一次渲染几千张表和全部字段。大规模场景必须做局部加载、虚拟化、搜索定位和按需展开。

Mermaid/SVG 更适合静态导出，不适合承载几千表的交互式浏览。

## 7. 轻量审计和权限

短平快版本不做重型权限治理，但必须保留最低限度审计：

- 谁触发扫描。
- 扫描了哪个仓库、哪个分支、哪个目录。
- 扫描了哪个数据库配置。
- 是否读取样例数据。
- 生成了哪些 artifacts。
- Codex CLI 是否使用了扫描结果。

平台已有 AI R&D 审计模型可以复用或参考，例如 `AIRdAuditEvent`。Harness 可以承接部署流水线、交付和运维链路的证据，但不建议替代平台内的工具调用审计。平台内审计用于回答“谁在什么时候让 Codex 扫了什么、用了什么结果”。

## 8. 当前知识库助手实现现状

当前【思源质量 / 知识库助手】已经有一套轻量知识图谱能力，但不是用 `ctags`、`semgrep`、`SchemaCrawler`、`Joern`、`CodeQL` 这类外部代码图谱工具扫描出来的。

当前实现是平台自研的 Python 索引器：

```text
apps/knowledge/services.py
  -> KnowledgeIndexBuilder
  -> KnowledgeObject
  -> KnowledgeRelation
```

### 8.1 当前如何扫描和关联

当前索引流程：

```text
KnowledgeRepositoryConfig
  -> index_repository
  -> KnowledgeIndexBuilder.build()
  -> seed_core_manual_quality_objects()
  -> index_roadmap()
  -> index_frontend_workspace()
  -> index_backend_urls()
  -> index_database_schema()
  -> index_django_models()
  -> persist()
```

生成的数据模型：

| 模型 | 作用 |
| --- | --- |
| `KnowledgeObject` | 平台、模块、菜单、页面、页签、功能、操作项、字段、API、表、组件、仓库等节点 |
| `KnowledgeRelation` | 节点之间的 contains、calls、reads、writes、implements、uses 等关系 |
| `KnowledgeIndexRun` | 每次索引任务、数量、日志、报告 |
| `KnowledgeQueryTrace` | 每次知识库问答命中的对象、边、路径、证据包 |

当前关联来源主要有四类：

| 来源 | 当前方式 | 产出 |
| --- | --- | --- |
| Roadmap 文档 | 读取 `docs/manual-quality-knowledge-roadmap.md`，解析 Markdown 表格 | 菜单、页面、页签、API、表关系 |
| 前端工作区配置 | 读取 `frontend/src/utils/manualTestcaseWorkspace.js`，用正则抽取 `name/label/primary` | 一级菜单、页签、页面路径 |
| 前端主页面 | 读取 `ManualTestCaseList.vue`，用正则抽取 `el-tab-pane` 和组件标签 | 页签到组件的 implements 关系 |
| 后端路由 | 读取 `backend/urls.py` 和 `apps/*/urls.py`，用正则抽取 Django path 和 DRF router | API 节点 |
| Django 模型 | 通过 `django_apps.get_models()` 读取模型元数据 | 表、字段节点 |
| MySQL Schema | 连接 `information_schema.TABLES/COLUMNS` | 外部数据库表、字段节点 |

### 8.2 当前页面菜单、页面、功能、操作项如何梳理

当前不是完全自动从 DOM 或运行时页面爬取，而是“人工 Roadmap + 代码轻量抽取 + 固定上下文”组合：

1. `docs/manual-quality-knowledge-roadmap.md`
   - 作为主要业务事实源。
   - 明确“一级菜单 -> 页签 -> 功能 -> 操作项 -> 字段 -> 页面路径 -> 接口能力 -> 数据库表”。
   - 后端 `index_roadmap()` 解析其中 Markdown 表格，生成菜单、页面、API、表关系。

2. `frontend/src/views/manual-testcases/ManualQualityKnowledgeAssistant.vue`
   - 内置 `manualQualityRoadmapStructure`，用于右侧组织结构图的业务层级。
   - 内置 `pageOperationEntries` 和 `operationQuickReferenceContent`，用于稳定回答高频页面操作，例如创建版本缺陷。
   - 内置 `roadmapReferenceContent` 和 `assistantRuleContent`，作为知识库助手固定上下文。

3. `frontend/src/utils/manualTestcaseWorkspace.js`
   - 定义思源质量主工作台的页签、一级菜单、可访问入口。
   - 后端 `index_frontend_workspace()` 读取该文件，补充菜单和页签节点。

4. `frontend/src/views/manual-testcases/ManualTestCaseList.vue`
   - 主工作台渲染各页签。
   - 后端通过正则抽取 `<el-tab-pane>` 和内部组件标签，建立页签到组件的关系。

5. `apps/knowledge/services.py`
   - 将上述信息统一写入 `KnowledgeObject` 和 `KnowledgeRelation`。
   - 问答时 `query_knowledge_context()` 根据用户问题做 token 匹配、对象打分、邻居关系扩展，生成“知识库对象证据包.md”。

### 8.3 当前右侧关系图用什么画

当前知识库关系图前端在：

```text
frontend/src/views/ai-development/AIDevConversationWorkspace.vue
```

知识库关系图使用的是 ECharts `graph` series，canvas 渲染，布局是 force layout：

```text
echarts.init(...)
series: [{ type: 'graph', layout: 'force', roam: true, draggable: true }]
```

同一个文件中也引入了 AntV X6，但 X6 当前主要用于业务逻辑画布，不是知识库关系图的当前渲染工具。

### 8.4 当前实现的局限

当前实现适合支撑【思源质量】模块的页面问答和轻量知识图谱，但不适合直接扩展为“通用多语言代码排查”：

- 代码扫描主要靠正则和约定文件，无法稳定识别任意语言的复杂调用关系。
- 操作项不少来自 Roadmap 和固定上下文，不是完整自动发现。
- 对前端按钮、表格列、表单字段的抽取还不完整。
- 数据库 Schema 只实现了 MySQL `information_schema` 的轻量抽取。
- 幽灵代码识别尚未形成通用算法和置信度模型。

因此后续通用能力应保留现有知识库对象模型和 UI 能力，但底层扫描器升级为统一 Skill + 工具链。

## 9. 建议演进路径

### 9.1 保留现有能力

保留当前：

- `KnowledgeObject`
- `KnowledgeRelation`
- `KnowledgeIndexRun`
- `KnowledgeQueryTrace`
- `/api/knowledge/query-context/`
- `/api/knowledge/graph/`
- 知识库助手右侧关系图和证据包机制

这些已经是平台问答和展示的基础设施。

### 9.2 新增扫描器结果接入

新增扫描结果导入层：

```text
asset-insight scanner output
  -> normalize_to_knowledge_objects()
  -> normalize_to_knowledge_relations()
  -> KnowledgeObject / KnowledgeRelation
```

也就是不推翻现有知识库模型，而是把通用代码扫描、数据库扫描结果转换进已有对象和关系表。

### 9.3 分阶段实现

第一阶段：

- 新建 scanner container，内置 `ripgrep`、`git`、`universal-ctags`、`semgrep`、`SchemaCrawler`。
- 新增后端 API：创建扫描任务、查询任务、获取 artifacts。
- 支持本地仓库路径和项目数据库配置。
- 输出 `scan_summary.md`、`ghost_code_report.md`、`code_reference_graph.json`、`er_graph.json`。

第二阶段：

- 将扫描结果导入 `KnowledgeObject/KnowledgeRelation`。
- 知识库助手问答可引用扫描结果。
- ER 图新增局部展开页面，优先使用 X6 展示中心表关系。

第三阶段：

- 增加 per-language 插件。
- 增加更多数据库类型。
- 引入 SARIF、置信度、误报确认、忽略规则。
- 支持 Codex CLI 在开发、部署、排障、运维时按需调用。

## 10. 一句话产品定位

第一版不要做成“工具集合市场”，而是做成一个平台 Skill：

```text
用户问：帮我排查这个系统的代码关系、幽灵代码和数据库 ER 图。
平台做：统一调度轻量扫描器，生成可追溯证据包和图谱，供 Codex CLI、知识库助手和平台页面复用。
```
