# AI 返回信息展示 & 工作区平台化 方案

> 状态：产品方案（**已采纳全部推荐默认值定稿**），**未进入开发**。§7 组织归属、§8 行业库、§9 落地路线、§10 护栏中的推荐默认值均按 PM 建议采纳；用户尚未逐条复核，后续如需调整可推翻。
> 视角：资深产品经理，从"平台想给用户的体验 + 用户真正想看的信息 + 用户体验"出发。
> 范围：【AI产品】/【AI会话详情】会话展示框中 AI 返回信息的展示形式与内容处理，以及由此延伸出的右侧工作区平台化、自建 Skill 契约、Agent 编排。

---

## 0. 一句话总纲

> 建立一套"消息展示协议"，把三件事显式化：**这是什么类型的 AI 输出、用户此刻最该关注什么、用户能做什么**；并把右侧工作区从"硬编码结果展示器"抽象为"可被 Agent 编排、可被用户自建、可被 AI 会话驱动的工作面板"，让平台成为各行业可复用的 AI 工作底座。

核心原则贯穿全文：**结论上浮、过程下沉、动作贴身；展示放开、写回收紧；渲染放开自由度、逻辑与写回收紧管控；首期可落地、服务稳定不失控。**

---

## 1. 现状与问题（基于代码核对）

### 1.1 现状事实

| 维度 | 现状 |
|---|---|
| 消息模型 | `ChatMessage`（`apps/assistant/models.py:1054`）只有 `role`(user/assistant)、`content`、`context_payload`(仅存 knowledge_* 三键)。**消息本身无 type/skill/capability 字段。** |
| 渲染位置 | 全部集中在 `frontend/src/views/ai-development/AIDevConversationWorkspace.vue`（约 24600 行）。 |
| 正文渲染 | `formatMessageContent` 只做 HTML 转义 + 链接化 + `<br>`，**不是 Markdown**。 |
| 结构化产出 | 存在 `CapabilityExecution.output_payload`（`models.py:735`），带 `type`（20+ 种）+ `sections.candidate_*`；前端靠 `has*Candidate()` 逐一探测渲染。 |
| 结果路由 | 官方 skill 后端硬编码 `target_workspace_tab` 路由到右侧约 18 个固定页签；自建 skill 走 `generic_capability_result`，**无 target_tab**，只能在会话框平铺。 |
| 编排 | `flow_ai_dev_full_cycle`（`flow_runtime.py`）是硬编码的 10+ 步工作流；`AIProductCreate.vue` 的 `sessionTypeConfig` 把会话类型硬编码映射到 `{workspaceTab, capabilityCodes[]}`。 |
| 写回 | `accept_requirement_analysis` 等"接受"动作用 `select_for_update`+事务**真写核心业务表**（Requirement/TestCase/Defect）。 |

### 1.2 三个产品体验缺陷

1. **信息平权**：寒暄与"全链路研发闭环"用同一种气泡形态返回，用户不知该看哪、该做什么。
2. **关注点错位**：不同 skill 用户真正关心的东西差别巨大（需求分析关心"覆盖哪些验收点、漏了什么"；用例生成关心"生成几条、P0 几条、能否一键入库"；Playwright 关心"跑哪些、要不要确认执行"；缺陷关心"根因、要不要建单"），现在都被压平成"一段文字 + 一张卡"。
3. **过程与结论混杂**：`process-text` 步骤流、思考中、最终答案挤在一个气泡里，用户要自己分辨"AI 在干嘛"和"AI 给了我什么"。

---

## 2. 会话展示框：三层展示模型

每一条 AI 返回信息拆成三个语义层，任何会话类型/skill 都套此模型，区别只在每层填什么。

```
┌─ 层1 身份带 (Identity Bar) ──── 我是谁、什么类型、什么状态、风险等级
├─ 层2 结论区 (Verdict / Payload) ── 用户此刻最该看的一句话 + 结构化主体
└─ 层3 过程与证据 (Process / Evidence) ── 默认折叠：思考流、原始返回、日志、引用
```

### 2.1 层1 身份带规格

顶部一条细带，四个信息槽，让用户 0.5 秒判断"这是什么、能不能信、要不要动作"：

```
[图标·类型标签]      [来源: skill名/模型名]        [状态]    [风险]        [耗时]
  🧪 用例生成         prompt_testcase_generation    ✓完成     低风险        3.2s
  ⛔ 自动部署         flow_ai_ops_deployment        待确认    高风险·需批准  —
```

- 类型标签复用 `capability_kind`（prompt/skill/agent/flow/mcp/tool）+ 普通对话，各配固定图标与色。
- 风险槽复用 `risk_level`，**高风险必须视觉抢眼**（红边/角标）。
- 状态槽复用 `status`，`waiting_confirmation` 要有呼吸感提示——它在等用户。
- **闲聊要轻、干活要重**：普通对话的身份带可极简（甚至只留一个小图标）。

### 2.2 层2 结论区

- 后端为每种产出补充 **`headline`** 字段（层2 那句"最该看的话"，后端生成，前端不猜）。
- 结构化主体按"展示原型"渲染（见 §3）。

### 2.3 层3 过程与证据（当前最乱，重点整改）

1. **运行中**：气泡顶显示单行"当前动作"（"正在调用 xx 分析需求…"），下面一个可展开的"过程日志（N 步）"，不摊开全部 `process-text`。
2. **完成后**：过程整体折叠成一行"🧾 查看推理过程 / 共 N 步 / 耗时 Xs"，结论区上浮到最前。
3. **引用/证据**：`context_payload.knowledge_evidence` 做成"依据 (3)"折叠块，挂结论下方。
4. 原则：**用户信任时不看过程，怀疑时才展开。** 过程是"可审计"，不是"默认阅读材料"。

### 2.4 P0 技术底座：正文接 Markdown

引入 `markdown-it` + `DOMPurify`（前端已有 xlsx/monaco），作为对话型与所有 `rendered_text` 的默认渲染器；代码块沿用现有 fenced-code 工具条。**这一步单独就能显著提升"AI 回复看起来专业"的观感，且不依赖后端。**

---

## 3. 会话框 vs 右侧工作区：分工与展示原型

### 3.1 分工判断标准（一句话）

> **有固定归宿 tab 的成果 → 会话框只留"任务卡"，成果去右侧；没有固定归宿的 → 在会话框内完整展开。**

| 内容 | 有固定工作区 tab？ | 会话框里显示 | 右侧工作区显示 |
|---|:---:|---|---|
| 需求分析/澄清/业务逻辑/原型/测试分析/自动化用例 | ✅ | 任务卡：任务名+状态+headline+"查看结果 →" | 完整结构化成果 |
| 候选用例、候选需求项 | ✅ | 任务卡 + 计数摘要（"生成24条 P0×6"）+ 采纳动作 | 明细列表 |
| Flow 全链路/部署 | ✅ | 步骤进度条（走到第几步、当前卡哪） | 各步产物 |
| HTML/原型/代码产物 | ✅ preview | 任务卡 + 预览按钮 | 预览/工作区 |
| 普通对话、问答、评审意见、根因结论、高风险待确认 | ❌ | 会话框内完整展示 | — |

### 3.2 会话框收敛成 3 形态

1. **对话型**：普通对话/问答/评审结论/根因 → 会话框内 Markdown 完整展示（会话框主业）。
2. **任务卡型**：所有"成果在右侧"的 skill → 极简卡片 + 状态 + 查看入口。绝大多数 skill 落这里。
3. **决策型**：待确认的高风险执行（Playwright 跑测/部署/写库）→ 会话框内展示计划 + 确认/驳回（决策属会话流，不藏到右侧）。

> 简记：**要你读的 → 会话框展开；成果性的 → 塌成任务卡去右侧；要你拍板的 → 会话框内决策。**

### 3.3 任务卡规格

```
┌────────────────────────────────────┐
│ 🧩 需求分析        ✓ 已完成 · 低风险    │  ← 任务名 + 状态 + 风险
│ 已生成基线需求分析，覆盖 8 个验收点        │  ← headline（后端给）
│                          查看结果 →     │  ← 跳右侧对应 tab（复用 target_workspace_tab）
└────────────────────────────────────┘
```
- 运行中：转圈 + "正在分析…"；完成变 ✓ 并亮出"查看结果"。
- 待确认：任务卡上直接挂"确认/驳回"（决策不赶去右侧）。

### 3.4 后端最小改动

为每种 `output_payload.type` 增加：
- **`display_archetype`**（A–F，见下表）：前端从"探测 20+ 种 has*Candidate"退化为"读 archetype 分发到少数组件"。
- **`headline`**：层2 那句话。

| 展示原型 | 覆盖 type | 用户最关注 | 内嵌动作 |
|---|---|---|---|
| A 对话型 | 普通对话/Dify/skill_guidance/prompt_summary | 答案本身 | 复制、追问 |
| B 候选清单型 | testcase_generation、requirement_analysis | 生成多少、质量分布、能否一键采纳 | 批量入库/逐条采纳/编辑/丢弃 |
| C 评审结论型 | requirement_review、testcase_review、skill_defect_triage | 通过/需补、漏了什么、根因 | 接受意见/建缺陷单/忽略 |
| D 执行计划型 | agent_playwright_testing_guidance、*_confirmation_plan | 做什么、风险多高、要不要批准 | 确认执行/驳回 |
| E 流程编排型 | flow_*、prototype_agent、ai_app_chain | 走到第几步、卡在哪 | 确认当前步/跳过/查看产物 |
| F 产物型 | codex_html_workspace、workspace_artifacts、代码 | 产出物本身 | 预览/下载/打开工作区/快照对比 |

---

## 4. 自建 Skill 的输出类型契约

### 4.1 核心机制：选类型 → 给模板 → 三处校验

新建 skill 时增加"输出类型"下拉，映射官方 `output_payload.type`。选了官方类型，skill 自带该类型的**格式化模板 + 约束**，用户照模板改成自己的内容。

| 用户可选类型 | 映射官方 type | 模板给什么 | 去哪展示 |
|---|---|---|---|
| 需求分析 | requirement_analysis | business_goals/scope_items/acceptance_criteria/risks/candidate_requirement_items 骨架 | baselineRequirementAnalysis 页签 |
| 用例生成 | testcase_generation | candidate_cases[]（case_id/title/priority/precondition/steps/expected_result） | automationTestCases 页签 |
| 需求评审 | requirement_review | {dimension, result(通过/需补充), suggestion}[] | 会话框决策区 |
| 用例评审 | testcase_review | verdict + missing_items[] + recommendations[] | 会话框决策区 |
| 缺陷分析 | skill_defect_triage | triage_dimensions[] + candidate_ai_defect{} | 会话框决策区 + 建单 |
| 自动化测试计划 | agent_playwright_testing_guidance | test_plan[] + candidate_automation_plan{} | 会话框决策区（确认执行） |
| **通用产物** | generic_capability_result | 自选 render_hint（table/markdown/list/…） | Skill 产出通用页签 |
| **纯对话** | — (inline) | 无格式约束 | 会话框内展示 |

存储：契约写入 `Capability.config_schema`（已有 JSONField，零迁移）。

### 4.2 两层校验

1. **静态校验（新建/编辑/导入，即时卡住）**：检查 skill 内容里是否声明了该类型要求的输出字段（schema 指纹/必需字段清单）。缺字段 → 标红指出。挡"人为改错"。
2. **运行时校验（skill 真跑出结果，兜底降级）**：AI 实际返回的 `sections` 是否符合类型 schema。符合 → 进官方页签；不符合 → 降级"通用产物"页签 + "输出未匹配声明类型"提示。兜"AI 跑偏"。

### 4.3 两个边界（已确认）

- **边界一（导入校验不过）**：允许导入，但**强制降级为"通用产物" + 警告标记**，保持 `review_status=draft` 待审核；降级原因记入校验日志。
- **边界二（官方类型对自建的开放范围）**：只开放 项目 / 需求 / 原型 / 原型需求分析 / 测试设计 / 设计风格 / 产品预览。
  - **关键结论：开放"页签展示"零风险（纯渲染，不碰核心表、不加库负载）；真正风险在页签背后的"接受写回核心表"动作。**
  - **展示放开、写回收紧**：自建 skill 的写回动作默认禁用或强确认 + 来源标记（`source=custom_skill`，便于追溯/回滚），且必须复用官方那套 `select_for_update`+事务，不开旁路。
  - 高风险类（flow 全链路/部署/直接执行）**锁给官方**，不对自建开放。

---

## 5. 工作区平台化：用户自定义页签

### 5.1 统一页签定义模型

右侧页签抽象成统一的"页签定义"，**官方那 18 个 tab 也变成预置定义**（`is_official=true` 不可删），与用户自建走同一渲染管线。整个工作区从"硬编码 if-else"变为"页签定义列表 + 按 render_type 分发的通用渲染器"。

**页签定义四元组：**
```
页签定义 = render_type（怎么画）
         + data_schema（吃什么形状的数据）
         + bound_skills（哪些 skill 产出投递到此）
         + actions（能做什么，默认只读）
```

### 5.2 渲染原语（封闭枚举，用户只能选不能造）

| render_type | 吃什么数据 | 复用现有 |
|---|---|---|
| 脑图 mindmap | 树 {node, children[]} | requirement_mindmap_seed |
| 流程图 flowchart | {nodes[], edges[]} | 新增（可接 draw.io） |
| 表格 table | {columns[], rows[]} | 已有 xlsx |
| 澄清风格 clarification | {groups:[{questions[]}]} | 已有 questionnaire |
| 原型 prototype | HTML/资源包 | 已有 codex_html_workspace |
| 页面 page-preview | URL/HTML | 已有 preview 页签 |
| 文档 document | Markdown | markdown-it |
| 图表 chart | ECharts option | 已有 knowledge_charts |
| 看板 kanban | {columns[], cards[]} | 新增 |
| 卡片列表 card-list | items[] | 已有 candidate 卡片 |
| 地图 map / 时间线 timeline | 地理/时间数据 | 新增 |

### 5.3 数据供给三模式（已确认：三种一次做全）

```
页签定义 = render_type + data_source
data_source：
├─ static 静态源     → URL / 用户导入文件（HTML页签配URL、表格导入）
├─ emit 会话产出源   → skill/会话把结果投递到此页签（泛化 target_workspace_tab）
└─ tool 工具驱动源   → 页签绑 MCP（如 draw.io），AI 会话调用工具实时写画布
```

**支持页签间数据流**：A 页签数据 → AI 分析 → B 页签出图。此机制与 §6 Agent 步骤间数据流合并为同一套（"页签即数据总线"）。

四个验证场景可行性（均可实现，代价递增）：
1. HTML/URL 页签（static）— 最易，复用 preview + upsertPreviewUrl。**必须 iframe 沙箱 + CSP + URL 白名单**。
2. 表格导入 + AI 分析（static + "页签数据作为会话上下文"）。
3. 跨页签出图（emit + 页签间数据流）。
4. draw.io MCP 实时画布（tool）— 最重，需引入 draw.io embed 渲染器。

### 5.4 渲染能力分三层开放（已确认，权限递增、隔离递增）

| 层 | 谁可用 | 能力 | 隔离 |
|---|---|---|---|
| **L1 配置层** | 人人 | 选 render_type + 填配置（URL/字段映射/绑 MCP） | 零风险，覆盖约 90% 需求；四个验证场景全落此层 |
| **L2 沙箱脚本层** | 需申请/审核 | 自定义渲染逻辑 | iframe 沙箱/Web Worker；无 DOM/token/cookie；网络白名单代理；CPU/内存/超时硬限 |
| **L3 官方扩展层** | 平台/认证开发者 | 真自定义组件 | 审核 + 代码审查后上架市场 |

> 反直觉事实：用户举的所有场景其实都在 L1（选类型+填配置+绑 MCP，无需写代码）。L2/L3 是留给长尾/生态的，首期不必全开安全闸门。

---

## 6. Agent 编排：从会话类型到用户自定义工作流

### 6.1 定位

把硬编码在 `flow_runtime.py` 和 `sessionTypeConfig` 里的编排，提取成用户可视化配置的 **Agent 对象**。Agent 是把 skill/页签/渲染层串成可执行工作流的**骨架**。

```
Agent（编排/工作流）= 会话类型
  ├─ 编排若干 Skill（首期按顺序串联）
  ├─ 绑定若干 页签（每步产出去哪展示）
  └─ 定义步骤流转（首期串行 + 人工确认卡点）
        ↓
会话类型选择 = 选一个已启用(enabled)的 Agent
        ↓
默认对话 Agent（不可删、置顶、纯对话兜底）
```

**"会话类型 = 选已启用的 agent"**：用户配好并启用的 agent 自动成为可选会话类型；草稿态 agent 不出现在下拉；默认对话 agent 永远置顶不可删。

### 6.2 控制流：分期（已确认）

- **阶段 A（首期）：线性序列 + 人工卡点。** 复用现有 `FlowStepRun.sort_order` + `waiting_confirmation`；列表式编排器；能表达现有 `flow_ai_dev_full_cycle` 的 100% 语义 + 用户自定义。
- **阶段 B（长期）：完整 DAG/并行。** 列表→画布，sort_order→nodes+edges；届时才引入环检测、并行调度、汇总超时、失败恢复、以及**页签并发写的版本/分区/合并策略**。
- **分期几乎零浪费**：线性是 DAG 的子集，阶段 A 的步骤定义/权限校验/人工卡点/页签绑定在阶段 B 全部复用；skill/页签/渲染层作为"被编排对象"零改动。

> 为何不首期直接 DAG：DAG 是工作流引擎级工程（环检测/并行调度/并发写数据竞争/失败恢复），与"首期可落地"冲突，且会拖累前面高价值低风险部分上线；用户首次接触编排，线性列表心智负担也远低于 DAG 画布。

### 6.3 数据传递：页签即数据总线（已确认）

- 每步产出落到它绑定的页签，下一步从指定页签读输入。
- 编排器上"连线" = 声明"这一步读哪个页签、写哪个页签"。
- **线性下天然安全**（一次一步写）；DAG 阶段并行写同一页签是数据竞争点，留待阶段 B 解决。

### 6.4 可视化编排器（首期）

纵向步骤列表编辑器：加步骤 → 每步选用哪个 skill → 选产出去哪个页签 → 勾选是否需人工确认。**非**自由拖拽画布（DAG 阶段再升级）。

### 6.5 治理

- agent 能编排的 skill 受该用户/该 agent 有权用的 skill 集合限制（复用 `AssistantSessionCapability` + skill `review_status`）。
- **高风险步骤（写库/部署/直接执行）在 agent 里强制"人工确认"卡点，不能被配成自动通过。**
- agent 本身需过启用/审核：只有 `enabled` 的可作为会话类型。

---

## 7. 组织归属（PM 推荐默认值，评审可否决）

前面各对象跟着谁走，决定"个人 AI 工作台"能否跨会话复用。推荐：

| 对象 | 归属 | 理由 |
|---|---|---|
| Skill / Capability | 平台级（官方）+ 用户/团队级（自建） | 复用面最广，已有 review 流程 |
| 页签定义 | 用户/团队级（可复用于其名下会话）；官方页签平台级预置 | "个人工作台"的核心是页签模板可跨会话复用 |
| Agent | 用户/团队级；官方 agent 平台级预置 | agent 是用户组装的工作流，天然属于用户/团队 |
| 会话实例 | 会话级 | 一次具体对话 |
| 页签数据 | 会话级（默认）；可显式"固化"到项目 | 避免会话间数据串味，需要沉淀时显式提升 |

> L3 市场形态：用户/团队级的"页签定义 + agent + skill 组合"可打包成**行业模板包**，经审核后上架，供他人一键安装——这是"人人以本平台为底座建行业 AI 工作平台"的最终形态。

---

## 8. 行业页签库（证明抽象成立）

同一组约 12 个渲染原语 + 3 种数据源，跨行业复用：

- **通用**：网页嵌入(page+static)、数据表(table+static)、分析图表(chart+emit)、看板(kanban+emit)、文档(document+emit)、流程图(flowchart+tool)、脑图(mindmap+emit)、地图、时间线。
- **软件研发**（本行）：需求分析、用例、原型、自动化计划、缺陷看板、部署流程图。
- **金融/投研**：行情页(page+tool)、财报表(table)、K线图(chart)、风控流程图(flowchart)、投研报告(document)。
- **医疗**：病历表、诊疗路径流程图、影像页、指标趋势图、用药知识图谱。
- **教育**：知识点脑图、课程时间线、题库表、学情图、教案文档。
- **制造/供应链**：产线看板、BOM 表、工艺流程图(draw.io)、设备监控页(tool 实时)、排产甘特图。
- **法律/合规**：合同条款表、审查意见文档、合规流程图、案例知识图谱、风险热力图。
- **市场/运营**：数据看板、用户旅程图、内容日历、竞品对比表、投放报告。

> 结论：行业差异 = 用户建的页签组合 + 绑的 skill/MCP，**全在配置层，不在代码层。** 这是"平台底座"命题成立的证据。

---

## 9. 落地路线（按投入产出排序）

| 阶段 | 动作 | 产出 | 依赖 |
|---|---|---|---|
| **P0** | 正文接 Markdown（markdown-it+DOMPurify） | 所有文字回复立刻变专业 | 纯前端 |
| **P1** | output_payload 加 `display_archetype`+`headline`；统一身份带组件 | 用户秒懂消息类型 | 前后端小改 |
| **P1** | 会话框任务卡 + 过程折叠 + 结论上浮 | 阅读焦点正确 | 前端 |
| **P2** | has*Candidate 卡片重构进 A–F 原型组件 | 减少重复、动作贴身 | 前后端 |
| **P2** | 自建 skill 输出类型契约（选类型+模板+两层校验） | 自建 skill 有归宿、不污染官方槽 | 前后端 |
| **P3** | 页签定义统一模型（官方 tab 改预置定义）+ L1 配置层 + data_source 三模式 | 用户可自建页签 | 前后端 |
| **P3** | Agent 编排（线性+人工卡点，列表式编排器）+ 会话类型=选 agent | 用户可编排工作流 | 前后端 |
| **P4** | L2 沙箱脚本层 + 行业模板包 + L3 市场 | 生态化 | 前后端 |
| **P5** | Agent 编排升级 DAG/并行（含页签并发写策略） | 完整编排引擎 | 前后端 |

---

## 10. 贯穿全案的护栏（稳定性/安全）

1. **展示放开、写回收紧**：任何非官方内容进核心表必须强确认 + 来源标记 + 走事务锁，绝不开旁路。
2. **render_type 封闭枚举**：用户选不写码（L1）；要写码进 L2 沙箱（无 DOM/token、网络白名单、资源硬限）。
3. **URL/iframe 沙箱**：page 类页签强制 sandbox + CSP + 白名单，防 XSS/钓鱼/内网跳板。
4. **Skill 执行治理**：自建 skill 的执行频率/超时/并发单独限流 + 熔断（这才是影响服务稳定性的真实点，与展示无关）。
5. **高风险步骤强制人工卡点**：写库/部署/直接执行在 agent 编排里不可配成自动通过。
6. **默认保守**：未声明契约的 skill 一律留会话框；未启用的 agent 不可选；页签数据默认会话级不串味。

---

## 11. 竞争定位：测试驱动的 AI 研发闭环

> 战略结论（已确认）：**先把测试/研发这个垂直领域做透做出标杆，这是真正的竞争力**，暂不做通用搭建平台（不与 Retool/Coze/Dify 正面竞争）。生态化（社区/黑客松）是长期目标，前置条件是底座跑通 + 有量化标杆样板。

### 11.1 市场现状：两个割裂的阵营（2026 市场扫描）

| 阵营 | 代表 | 强项 | 缺口 |
|---|---|---|---|
| **AI 造软件** | Devin、Lovable、Replit、Bolt、v0 | 一句话到能跑的原型 | 集体撞"80% 墙 / 最后 20% 悬崖"：复杂业务逻辑/鉴权/集成/边界处理就崩；产出半成品非完整软件；chat 表达不清 AI 瞎猜致需求跑偏；"能跑 ≠ 能上生产"；**几乎不做测试覆盖度保障** |
| **AI 保障质量** | Testsigma、ACCELQ、Virtuoso、NVIDIA HEPH | 从需求生成用例、扩覆盖度、CI 质量门禁；HEPH 甚至用覆盖率反馈迭代生成 | **只做测试一侧，不造软件**，是给别人造好的软件做质检的 |

**关键结论：这两个阵营割裂——造软件的不管测试覆盖，做测试的不造软件。把两侧焊成闭环（用完整覆盖度的测试分析作为质量闸门反向约束 AI 开发）的打法，2026 市场扫描中未见完全对应的产品。这就是本平台的差异化缝隙。**

### 11.2 四个主张的诚实评估（哪些立得住、哪些是危险承诺）

| 主张 | 市场现实 | 判断 |
|---|---|---|
| ① 需求一一对齐不跑偏 | 全行业核心痛点，无人真正解决；根因是"chat 表达不清 AI 瞎猜" | ✅ **真机会**。平台的需求澄清 skill + 结构化澄清页签 + 需求分析写回正对根因，是真差异化 |
| ② 产出完整软件非半成品 | "80% 墙"是**工程本质难题**，非工具成熟度问题 | ⚠️ **别正面硬扛**。收窄到特定领域/特定复杂度才成立 |
| ③ 完整覆盖度测试分析→完整覆盖度用例 | 测试侧已有强者，但**没人拿覆盖度反向卡开发** | ✅✅ **最硬的牌 / 护城河**。稀缺的不是"生成用例"，是"用覆盖度反向约束开发" |
| ④ 功能几乎无 bug | **全行业无人敢承诺**（"no tool can honestly promise no bugs"、"human oversight remains essential"） | ❌ **危险承诺，务必删掉**。第一个 bug 出现即信誉崩塌 |

### 11.3 价值主张改写（对外叙事锚点）

> **不说**"我能造出无 bug 的完整软件"（做不到、会翻车）；
> **改说**"我是唯一把测试覆盖度做成开发质量闸门的 AI 研发闭环——软件在开发过程中就被完整测试覆盖持续校准，最大限度对齐需求、逼近生产可用"。

三个好处：
1. **诚实且防御性强**——承诺"过程被测试持续校准"（可验证）而非"无 bug"（会翻车）。
2. **精准卡在两阵营的缝里**——造软件的没有测试闭环，做测试的没有开发能力。
3. **与既有方案严丝合缝**——需求澄清/需求分析/测试分析 skill/用例生成/评审/Playwright 自动化/Agent 编排全链路，正是这条闭环的零件。**本平台不是"又一个 AI 编码工具"，而是"测试驱动的研发闭环平台"——这才是标杆定位。**

### 11.4 标杆必须用数字证明（验证动作）

在对外宣传"标杆"前，先用本平台闭环造出 1-2 个真实中等复杂度软件，量化三个数字：

- **需求覆盖率**：生成用例覆盖了百分之多少验收点
- **一次通过率**：AI 产出 vs 需求，第一次对齐了多少
- **缺陷逃逸率**：测试覆盖后还漏了多少 bug

> 没有数字的"对齐/完整/无 bug"是口号；有数字的"需求覆盖率 95%、缺陷逃逸率 3%"才是能打的标杆，也是黑客松/社区/融资时最有说服力的证据。

### 11.5 市场信源（2026 扫描）

- [The 2026 AI Coding Platform Wars: Replit vs Windsurf vs Bolt.new vs Lovable](https://medium.com/@aftab001x/the-2026-ai-coding-platform-wars-replit-vs-windsurf-vs-bolt-new-f908b9f76325)
- [Lovable AI Review (2026): Honest Take After Building Real Apps](https://www.aibuilderclub.com/blog/lovable-ai-review-2026)
- [Best AI App Builder in 2026: Lovable vs Bolt vs v0 vs Replit](https://whichaiisbest.com/best-ai-app-builder/)
- [Building AI Agents to Automate Software Test Case Creation | NVIDIA](https://developer.nvidia.com/blog/building-ai-agents-to-automate-software-test-case-creation/)
- [How AI Agents Automated Our QA: 700+ Test Coverage](https://openobserve.ai/blog/autonomous-qa-testing-ai-agents-claude-code/)
- [15 Best AI Testing Tools in 2026: Practitioner's Guide](https://www.virtuosoqa.com/post/best-ai-testing-tools)
- [How AI Is Redefining Software Testing Practices in 2026](https://www.evozon.com/how-ai-is-redefining-software-testing-practices-in-2026/)

---

## 12. L3 造软件能力评估与闭环补强

### 12.1 复杂度阶梯（7 维度 + 五级）

评估维度：实体数 / 页面数 / 业务规则密度 / 集成点 / 状态与事务 / 非功能要求 / 角色权限。

| 级别 | 名称 | 实体 | 页面 | 业务规则 | 集成 | 状态/事务 | 典型例子 | AI 闭环现实 |
|---|---|---|---|---|---|---|---|---|
| L1 | 玩具/Demo | 1-2 | 1-3 | 几乎无 | 0 | 无 | 待办、计算器、落地页 | 现有工具都能一次成 |
| L2 | 简单应用 | 3-5 | 4-8 | 少量校验 | 0-1 | 简单 CRUD | 博客、单表后台、问卷 | Lovable/Replit 能到 |
| **L3** | **中等复杂度** | **6-15** | **10-25** | **中等：状态机+权限+多条件** | **2-4** | **状态流转+事务** | **工单/进销存/预约/轻CRM/CMS/小电商后台** | **"80% 墙"开始显现** |
| L4 | 复杂应用 | 16-40 | 26-60 | 高：复杂工作流+权限矩阵 | 5-10 | 并发+分布式事务 | ERP模块/多租户SaaS/订单履约 | 现有工具几乎必崩 |
| L5 | 企业级/关键系统 | 40+ | 60+ | 极高：合规+审计+高可用 | 10+ | 强一致+高并发 | 银行核心/HIS/大平台 | 不在一次性生成范围 |

**验证标杆锁定 L3**：L2 证明不了差异化，L4 第一个样板就翻车。推荐首个样板 = **设备报修工单系统**（实体6-8、集成≤2、有状态机+权限、无支付无高并发）——能秀对齐与覆盖能力，同时避开集成/并发死亡陷阱。

### 12.2 平台造 L3 软件的五大不足（能力体检）

前提结论：**编排链是全市场最完整的**（需求分析→评审→用例生成→用例评审→需求回填→代码开发→自动化测试→提缺陷→修缺陷→回归→提交→部署），但目前是"走一遍的直线"，非真正闭环。代码核对依据见 `flow_runtime.py`、`codex_cli_runtime.py`、`new_project_runtime.py`。

| # | 不足 | 事实依据 | 后果 | 补强方案 |
|---|---|---|---|---|
| **一** | **闭环没闭合——缺自动反馈循环**（最致命） | flow 步骤靠 `complete/skip_current_flow_step` 人工推进；`code→test→defect→fix→regression` 是线性排列，代码里无 retry/loop/feedback（已搜证） | "逼近无 bug"是空话——测试失败不能自动驱动修复迭代 | automation_test 后加**判定网关**：全绿前进/有失败携证据自动回灌 fix_ai_defect 重跑；设最大轮次+收敛判据防烧钱 |
| **二** | **覆盖度是 AI 自评，非客观测量** | `coverage_matrix`/`quality_gate`/`coverage_percent` 由模型在 prompt 里生成（new_project_runtime.py） | 护城河最脆弱处——被拆穿"覆盖率是编的"则标杆信誉崩 | 双轨：需求覆盖度(用traceability_matrix,可信)+**代码覆盖度真测**(容器内跑 pytest --cov / nyc / jacoco)。真测的才做门禁 |
| **三** | **需求→代码缺机器可读 spec 契约** | 需求分析结构化产出到 code_development 时被压回自然语言消息(build_codex_execution_message) | 需求跑偏病根——对齐在最后一公里丢失 | 需求分析固化成结构化 spec(实体/字段/状态机/验收点/权限矩阵)，**同一份 spec 喂 开发+用例+断言**三方(spec-driven build)。已有 mindmap/traceability 半成品 |
| **四** | **非功能与集成是盲区** | flow 链只覆盖功能开发+功能测试，无性能/安全/并发环节，集成无专门处理 | L3 的"最后 20% 墙"恰是集成+非功能 | 首期样板主动收窄(集成≤2、低并发)；中期在测试分析 skill 显式加非功能维度(越权/边界/并发/集成失败回退) |
| **五** | **产物完整性无"可运行验证"闸门** | codex 真容器跑但无强制"build+启动+冒烟"闸门；smoke_verify 在部署阶段非开发产出阶段 | 半成品当完整软件交出，正是想区别于 Lovable 却没守住的点 | code_development 后插硬闸门：容器内真实 build+启动+冒烟，不过退回重做 |

**收敛一句话**：编排链最完整，但缺三样让它成为真闭环——① code↔test 自动回退循环、② 客观测量的真实覆盖率、③ 需求/开发/测试共享的机器可读 spec 契约；再加"可运行验证闸门"+"收窄非功能盲区"，才真正拥有"测试驱动、对齐需求、逼近生产可用"的 L3 能力，且无竞品同时具备。

**⚠️ 与 §6 编排选择的冲突**：核心竞争力（测试驱动闭环）需要 code↔test 的**条件回退循环**，但 §6 首期选了"线性+人工卡点"无回退。**建议：把"code↔test 自动回退循环"作为首期唯一例外，硬编码进研发闭环 flow（不依赖通用 DAG），其余编排仍走线性。**

### 12.3 已有资产：testhub-self-debug-repair skill

用户已有 `C:\Users\fengs\.codex\skills\testhub-self-debug-repair`（证据驱动的端到端自修复工作法）。**它正好补不足一的"自动回退循环"精神内核**：复现→抓证据→最窄边界诊断→最小改动→同步容器→重跑直到通过；且强调"单测通过不算数，必须浏览器/E2E 证明"。

**可复用到开发环节的核心方法论**（提炼成通用能力）：
- 证据优先：flow id/execution id/失败步/脚本/截图/stderr 作为诊断依据。
- 最窄失败边界优先诊断，最小责任模块修补。
- **"通过=可运行证明"而非"代码写完"**——正是不足五要的可运行闸门。
- 循环重跑直到真实链路通过——正是不足一要的回退循环。

**该 skill 的缺点/待优化**（用于开发环节前需完善）：
1. **强耦合 TestHub 自身**：全篇写死 testhub-local-* 容器、41080/18765 端口、平台专有 API（visual flow/recording/replay）。用到"生成任意 L3 软件"的开发环节，需**抽象出通用层**（复现→证据→诊断→修补→验证循环）与**平台适配层**（TestHub 专有部分）分离。
2. **端口/环境硬编码且已漂移**：41080 vs 31080、13306 等散落，skill 自己也说"inspect docker ps before choosing"——应做成**环境探测而非硬编码**。
3. **收敛与终止判据缺失**：描述"repeat until it passes"，但**无最大轮次、无收敛判据、无失败升级人工**——直接用于自动开发循环会有无限重跑/烧钱风险（正是不足一补强方案要补的）。
4. **无覆盖率维度**：skill 验证的是"链路跑通/E2E 通过"，**不含代码覆盖率测量**——与不足二互补但未覆盖，需补真实 coverage 采集。
5. **无 spec 对齐校验**：验证"功能是否工作"，但不校验"是否与需求 spec 一一对齐"——需与不足三的 spec 契约结合，增加"产出 vs spec"的一致性断言。
6. **同步机制脆弱**：docker cp + restart 是手工式同步，多容器逐个 py_compile；用于高频自动循环需更健壮的构建/热更机制。
7. **证据格式非结构化**：`.tmp-*result.json` 是临时约定，未标准化——若要喂回自动循环做判定，需定义稳定的机器可读证据 schema。

**结论**：这个 skill 的**方法论**（证据驱动、最窄边界、可运行证明、循环重跑）应当**提炼为开发环节自修复循环的内核**；但其**实现**（TestHub 专有、硬编码、无收敛判据、无覆盖率/spec 维度）需重构为"通用自修复引擎 + 平台适配"两层，并补齐终止判据、覆盖率、spec 对齐三项后才能安全用于自动开发闭环。

---

*本文档为方案评审稿，各推荐默认值可在评审中调整。确认后再拆分为各期开发任务。*
