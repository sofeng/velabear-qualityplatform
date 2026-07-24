# 思源质量知识库 Roadmap

更新日期：2026-06-19

本文用于支撑【思源质量】知识库助手做“菜单 -> 页签 -> 功能 -> 操作项 -> 字段 -> 页面路径 -> 接口能力 -> 数据库表”的先检索、再回答。后续涉及思源质量模块的功能说明、操作路径、数据口径、接口定位、表结构定位，优先从本文开始检索。

## 1. 模块边界

思源质量当前收敛在前端路由 `/manual-testcases` 下，主工作台页面为：

- 页面：`/manual-testcases/list`
- tab 参数：`/manual-testcases/list?tab=<section>`
- 常用上下文参数：`project_id`、`version_id`、`category_id`
- 主组件：`frontend/src/views/manual-testcases/ManualTestCaseList.vue`
- 导航定义：`frontend/src/utils/manualTestcaseWorkspace.js`
- 权限定义：`frontend/src/utils/permissions.js`

旧的 `/quality-analysis/*`、`/manual-testcases/defects`、`/manual-testcases/reports` 等入口多数已重定向到 `/manual-testcases/list?tab=...`。

## 2. 通用上下文

| 上下文 | 用途 | 主要来源 |
| --- | --- | --- |
| 项目 | 控制目录树、版本、脑图、缺陷、需求统计范围 | `projects`、`project_members` |
| 版本 | 控制需求、测试、缺陷、报告统计联动 | `versions` |
| 目录 / 模块 | 左侧目录树，联动脑图、测试点、缺陷、技术方案 | `manual_testcase_categories` |
| 用户 | 成员、角色、处理人、开发、测试、审核人 | `users_user`、`users_role*` |

通用 API：

| 能力 | API |
| --- | --- |
| 项目列表 | `GET /api/projects/list/` |
| 项目 CRUD / 成员 | `GET/POST/PUT/PATCH/DELETE /api/projects/`，`/api/projects/{id}/members/` |
| 版本列表 | `GET /api/versions/?projects=<project_id>`，`GET /api/versions/projects/{project_id}/versions/` |
| 版本 CRUD | `GET/POST/PUT/DELETE /api/versions/` |
| 用户列表 | `GET /api/auth/users/` |
| 目录树 | `GET/POST /api/testcases/manual-categories/`，`PUT/DELETE /api/testcases/manual-categories/{id}/` |

## 3. 项目组织结构 Roadmap

知识库助手右侧关系图以本节为业务结构事实源，只展示“项目名称 / 模块 / 多级菜单 / 多级页签 / 页面模块 / 功能或操作项”。URI、页面 URL、API、数据库表、字段、组件路径和代码路径不作为关系图节点展示，这些信息保留在后续表格、命中路径和数据来源中，用于问答检索和溯源。

```text
TestHub平台
└─ 思源质量
   ├─ 知识库助手
   │  └─ 知识库助手
   │     └─ AI会话工作区
   │        ├─ 知识库对象问答
   │        ├─ 历史会话查看
   │        ├─ 右侧关系图
   │        └─ 命中路径与数据来源
   ├─ 总览
   │  └─ 总览
   │     └─ 研发进展总览
   │        ├─ 需求进展统计
   │        ├─ 自测与测试覆盖统计
   │        ├─ 跳转测试脑图
   │        └─ 跳转版本缺陷
   ├─ 需求
   │  ├─ JIRA需求数据
   │  │  └─ 需求同步与列表
   │  │     ├─ 同步需求
   │  │     ├─ 需求筛选
   │  │     ├─ 查看需求详情
   │  │     ├─ 跳转测试点
   │  │     └─ 跳转缺陷
   │  └─ 版本需求
   │     └─ 版本需求管理
   │        ├─ 新增版本需求
   │        ├─ 编辑版本需求
   │        ├─ 删除版本需求
   │        ├─ 关联测试脑图
   │        └─ 跳转版本缺陷
   ├─ 开发
   │  ├─ 自测测试点
   │  │  └─ 自测测试点表格
   │  │     ├─ 查看脑图
   │  │     ├─ 编辑自测测试点
   │  │     ├─ 审核自测测试点
   │  │     └─ 提交缺陷
   │  └─ 技术方案设计
   │     └─ 技术方案设计列表
   │        ├─ 新增技术方案
   │        ├─ 编辑技术方案
   │        ├─ 导入Excel
   │        ├─ 流转状态
   │        └─ 评论与附件
   ├─ 测试
   │  ├─ 测试脑图
   │  │  └─ 脑图列表与编辑器
   │  │     ├─ 新建脑图
   │  │     ├─ 编辑脑图
   │  │     ├─ 查看脑图
   │  │     └─ 批量删除脑图
   │  ├─ 测试用例
   │  │  └─ 脑图用例抽取
   │  │     ├─ 用例查看
   │  │     ├─ 按需求筛选
   │  │     └─ 跳转脑图
   │  └─ 测试点
   │     └─ 脑图测试点抽取
   │        ├─ 测试点查看
   │        ├─ 按状态和模块筛选
   │        ├─ 提交缺陷
   │        └─ 跳转脑图
   ├─ 缺陷
   │  ├─ 版本缺陷分析
   │  │  └─ 缺陷统计分析
   │  │     ├─ 按开发人员统计
   │  │     ├─ 按缺陷状态统计
   │  │     └─ 按问题根因统计
   │  ├─ 版本缺陷
   │  │  └─ 版本缺陷列表
   │  │     ├─ 新建缺陷
   │  │     ├─ 编辑缺陷
   │  │     ├─ 变更状态
   │  │     ├─ 指派处理人
   │  │     ├─ 评论与附件
   │  │     └─ 导入Excel
   │  └─ 线上缺陷
   │     └─ 线上BUG同步列表
   │        ├─ 同步线上BUG
   │        ├─ 线上缺陷筛选
   │        ├─ 关联需求
   │        └─ 关联测试用例或测试点
   ├─ 报告
   │  ├─ 报告列表
   │  │  └─ 质量报告列表
   │  │     ├─ 上传报告
   │  │     ├─ 分析报告
   │  │     ├─ 刷新实时快照
   │  │     └─ 分享报告
   │  └─ 实时质量分析
   │     └─ 实时质量分析看板
   │        ├─ 版本质量分析
   │        ├─ 需求进展分析
   │        ├─ 测试进展分析
   │        ├─ 缺陷与工时分析
   │        └─ 复制分享链接
   ├─ 配置
   │  ├─ 项目环境
   │  │  └─ 项目环境配置
   │  │     ├─ 新增环境
   │  │     ├─ 编辑环境
   │  │     └─ 启用停用环境
   │  ├─ Git/GitHub仓库配置
   │  │  └─ 知识库仓库配置
   │  │     ├─ 新增仓库配置
   │  │     ├─ 弹出授权页面
   │  │     ├─ 测试连接
   │  │     ├─ 触发索引
   │  │     └─ 查看索引报告
   │  ├─ 项目资产图谱
   │  │  └─ 项目知识库与资产图谱
   │  │     ├─ 创建项目知识库
   │  │     ├─ 页面接口库表关系图
   │  │     ├─ 数据库ER图
   │  │     ├─ 代码调用图
   │  │     ├─ 幽灵代码排查
   │  │     └─ 库表字段检索
   │  ├─ JIRA接口配置
   │  │  └─ JIRA同步接口配置
   │  │     ├─ 新增接口配置
   │  │     ├─ 编辑接口配置
   │  │     ├─ 执行同步配置
   │  │     └─ 查看同步记录
   │  ├─ 通知配置
   │  │  └─ 邮件与消息提醒
   │  │     ├─ 配置邮件模板
   │  │     ├─ 配置SMTP
   │  │     ├─ 测试发送
   │  │     └─ 配置消息提醒
   │  └─ 流程工作台
   │     └─ 流程定义与待办
   │        ├─ 查看待办
   │        ├─ 维护流程定义
   │        ├─ 维护流程规则
   │        └─ 启动或处理流程
   ├─ 管理
   │  ├─ 成员
   │  │  └─ 成员管理
   │  │     ├─ 新增成员
   │  │     ├─ 编辑成员
   │  │     ├─ 停用启用成员
   │  │     └─ 重置密码
   │  ├─ 组别
   │  │  └─ 组别管理
   │  │     ├─ 新增组别
   │  │     └─ 维护组成员
   │  ├─ 角色
   │  │  └─ 角色管理
   │  │     ├─ 新增角色
   │  │     └─ 维护角色成员
   │  ├─ 项目
   │  │  └─ 项目管理
   │  │     ├─ 新增项目
   │  │     ├─ 设置默认项目
   │  │     └─ 维护项目成员
   │  ├─ 版本
   │  │  └─ 版本管理
   │  │     ├─ 新增版本
   │  │     └─ 设置默认版本
   │  └─ 权限
   │     └─ 权限管理
   │        ├─ 权限目录
   │        ├─ 角色授权
   │        └─ 维护权限项
   ├─ 录制
   │  ├─ 自动化脚本生成
   │  │  └─ 脚本生成
   │  │     └─ 生成Playwright脚本
   │  ├─ 自动化脚本管理
   │  │  └─ 脚本版本管理
   │  │     ├─ 查看脚本版本
   │  │     └─ 恢复版本
   │  ├─ 快照文件管理
   │  │  └─ 快照管理
   │  │     ├─ 上传快照
   │  │     ├─ 解析快照
   │  │     └─ 批量导出
   │  ├─ 录制结果管理
   │  │  └─ 录制会话管理
   │  │     ├─ 本地Agent录制
   │  │     ├─ 步骤去重
   │  │     └─ 转流程
   │  ├─ 流程管理
   │  │  └─ 可视化流程列表
   │  │     ├─ 创建流程
   │  │     ├─ 复制流程
   │  │     └─ 执行流程
   │  ├─ 可视化流程编辑器
   │  │  └─ 流程画布
   │  │     ├─ 编排节点
   │  │     ├─ 绑定录制步骤
   │  │     └─ 保存流程
   │  └─ 测试执行结果
   │     └─ 执行结果列表
   │        ├─ 查看执行结果
   │        ├─ 查看步骤截图
   │        └─ 查看执行日志
   └─ Wiki
      └─ Wiki
         └─ Wiki目录与页面
            ├─ 维护目录
            ├─ 编辑页面内容
            └─ 上传附件图片
```

## 4. 菜单到页签总览

| 一级菜单 | 页签 / 页面 | tab 或 path | 主要组件 | 主要数据表 |
| --- | --- | --- | --- | --- |
| 知识库助手 | 知识库助手 | `quality-knowledge-assistant` | `ManualQualityKnowledgeAssistant.vue` | `assistant_session*`、业务表只读检索 |
| 总览 | 总览 | `requirement-overview` | `ResearchProgressOverviewPanel.vue` | `quality_analysis_jira_requirement_records`、`manual_testcase_mindmaps`、`dev_self_test_records`、`defects`、`quality_analysis_jira_bug_records` |
| 需求 | JIRA需求数据 | `requirement-records` | `QualityAnalysisJiraData.vue` | `quality_analysis_jira_requirement_records` |
| 需求 | 版本需求 | `version-requirements` | `VersionRequirementList.vue` | `quality_analysis_jira_requirement_records`、`quality_analysis_jira_requirement_record_attachments` |
| 开发 | 自测测试点 | `devselftest` | `ManualTestCaseList.vue` 内嵌表格 | `dev_self_test_records`、`manual_testcase_mindmaps` |
| 开发 | 技术方案设计 | `technical-solution-designs` | `TechnicalSolutionDesignList.vue`、`TechnicalSolutionDesignForm.vue` | `defects`，`record_type=technical_solution_design` |
| 测试 | 测试脑图 | `mindmaps` | `ManualTestCaseList.vue` / `ManualTestCaseEditor.vue` | `manual_testcase_mindmaps` |
| 测试 | 测试用例 | `testcases` | `ManualTestCaseList.vue` | `manual_testcase_mindmaps.mindmap_data`、`testcases` |
| 测试 | 测试点 | `testpoints` | `ManualTestCaseList.vue` | `manual_testcase_mindmaps.mindmap_data` |
| 缺陷 | 版本缺陷分析 | `version-defect-analysis` | `VersionDefectAnalysisPanel.vue` | `defects` |
| 缺陷 | 版本缺陷 | `version-defects` | `DefectList.vue`、`DefectForm.vue` | `defects`、`defect_attachments`、`defect_comments`、`defect_histories` |
| 缺陷 | 线上缺陷 | `bug-records` | `QualityAnalysisJiraData.vue` | `quality_analysis_jira_bug_records` |
| 报告 | 报告列表 | `quality-report-list` | `QualityAnalysisReportListPanel.vue` | `quality_analysis_reports` |
| 报告 | 实时质量分析 | `quality-report-live` | `QualityAnalysisReportDetailPanel.vue`、`QualityAnalysisVersionLivePanel.vue` | 聚合读取需求、脑图、自测、缺陷、线上缺陷等表 |
| 配置 | 项目环境 | `project-environments` | `ProjectEnvironmentPanel.vue` | `project_environments` |
| 配置 | 项目资产图谱 | `project-asset-insight` | `ProjectAssetInsightPanel.vue` | `knowledge_spaces`、`knowledge_repository_configs`、`knowledge_objects`、`knowledge_relations`、`knowledge_index_runs` |
| 配置 | JIRA接口配置 | `configs` | `QualityAnalysisJiraData.vue` | `quality_analysis_jira_configs`、`quality_analysis_jira_requirement_configs` |
| 配置 | JIRA编号URL前缀配置 | `other-settings` | `QualityAnalysisJiraData.vue` | `quality_analysis_settings` |
| 配置 | 邮件模板配置 | `email-template-config` | `DefectNotificationSettings.vue` | `defect_email_configs` |
| 配置 | 邮件配置 | `email-config` | `DefectNotificationSettings.vue` | `defect_email_configs` |
| 配置 | 测试发送 | `test-email` | `DefectNotificationSettings.vue` | `defect_email_configs` |
| 配置 | 消息提醒 | `notification-settings` | `DefectNotificationSettings.vue` | `defect_email_configs` |
| 配置 | 流程工作台 | `/manual-testcases/workflow-workbench` | `WorkflowWorkbench.vue` | `workflow_definitions`、`workflow_rules`、`workflow_instances`、`workflow_tasks`、`workflow_action_logs` |
| 管理 | 成员 | `members` | `MemberManagementPanel.vue` | `users_user` |
| 管理 | 组别 | `groups` | `GroupManagementPanel.vue` | `auth_group` / 平台 group API 相关表 |
| 管理 | 角色 | `roles` | `RoleManagementPanel.vue` | `users_role`、`users_role_membership` |
| 管理 | 项目 | `projects` | `ProjectManagementPanel.vue` | `projects`、`project_members` |
| 管理 | 版本 | `versions` | `VersionManagementPanel.vue` | `versions` |
| 管理 | 权限 | `permissions` | `PermissionManagementPanel.vue` | `users_permission_item`、`users_role_permission` |
| 录制 | 自动化脚本生成 | `/manual-testcases/recording-scripts` | `RecordingScriptManager.vue` | `playwright_automation_scripts`、`playwright_automation_script_versions` |
| 录制 | 自动化脚本管理 | `/manual-testcases/automation-scripts` | `AutomationScriptManager.vue` | `playwright_automation_scripts`、`playwright_automation_script_versions` |
| 录制 | 快照文件管理 | `/manual-testcases/snapshots` | `SnapshotManager.vue` | 文件系统快照 + 解析元数据 |
| 录制 | 录制结果管理 | `/manual-testcases/recordings` | `SnapshotRecordingManager.vue` | `playwright_recording_sessions`、`playwright_recording_steps` |
| 录制 | 流程管理 | `/manual-testcases/flows` | `VisualFlowManager.vue` | `visual_flows` |
| 录制 | 可视化流程编辑器 | `/manual-testcases/visual-flow` | `VisualFlowEditor.vue` | `visual_flows` |
| 录制 | 测试执行结果 | `/manual-testcases/visual-flow-executions` | `VisualFlowExecutionManager.vue` | `visual_flow_executions`、`visual_flow_execution_steps` |
| Wiki | Wiki | `/manual-testcases/wiki` | `WikiManager.vue` | `wiki_directories`、`defects`，`record_type=wiki` |

## 5. 核心业务页签明细

### 5.1 知识库助手

| 项 | 内容 |
| --- | --- |
| 页面路径 | `/manual-testcases/list?tab=quality-knowledge-assistant` |
| 组件 | `ManualQualityKnowledgeAssistant.vue` -> `AIDevConversationWorkspace.vue` |
| 功能 | 用 `manual_quality_knowledge` 会话类型回答思源质量功能、操作、数据口径、统计图、页面入口问题 |
| 操作项 | 输入问题、读取固定上下文、按规则查询平台接口、返回文本或图表 marker |
| 上下文文件 | `思源质量页面操作速查.md`、`思源质量知识库回答规则.md`，建议追加本文摘要 |
| 主要表 | `assistant_session`、`assistant_chat_message` 等会话表；业务数据来自下述业务表 |

### 5.2 总览 / 研发进展

| 项 | 内容 |
| --- | --- |
| 页面路径 | `/manual-testcases/list?tab=requirement-overview` |
| 组件 | `ResearchProgressOverviewPanel.vue` |
| 功能 | 按版本、项目汇总需求、自测、测试脑图、测试用例、测试点、版本缺陷、线上缺陷 |
| 操作项 | 过滤需求编号、标题、状态、模块、组别、PM、前端、后端、测试人员；跳转测试脑图、版本缺陷、线上缺陷 |
| 可见字段 | 需求编号、需求标题、客户或项目名称、版本内研发优先级别、状态、模块、组别、PM、前端、后端、测试人员、自测测试点、测试脑图ID、测试用例数、测试点数、评审测试点数、版本缺陷、线上缺陷 |
| API | `GET /api/quality-analysis/reports/live-rd-progress-overview/` |
| 主要表 | `quality_analysis_jira_requirement_records`、`manual_testcase_mindmaps`、`dev_self_test_records`、`defects`、`quality_analysis_jira_bug_records` |

### 5.3 需求：JIRA需求数据 / 版本需求

| 页签 | 页面路径 | 组件 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- | --- |
| JIRA需求数据 | `/manual-testcases/list?tab=requirement-records` | `QualityAnalysisJiraData.vue` | 同步、筛选、查看、详情、测试点/版本缺陷/线上缺陷跳转 | 版本号、需求编号、需求标题、需求类型、所属模块、客户、优先级、状态、创建人、处理人、测试人员、组别、同步时间、扩展字段 | `GET/POST /api/quality-analysis/jira-requirement-records/`，`POST refresh/`，`POST clear-selected/` | `quality_analysis_jira_requirement_records`、`quality_analysis_jira_requirement_record_attachments` |
| 版本需求 | `/manual-testcases/list?tab=version-requirements` | `VersionRequirementList.vue` | 新增、编辑、删除、清空所选、详情、关联测试脑图、跳转版本缺陷/线上缺陷 | 版本号、需求编号、需求标题、需求描述、需求类型、所属模块、客户、优先级、状态、创建人、处理人、测试人员、组别、前端开发、后端开发、关联测试脑图、扩展字段 JSON、附件 | `GET/POST/PATCH/DELETE /api/quality-analysis/jira-requirement-records/` | 同上 |

### 5.4 开发：自测测试点 / 技术方案设计

| 页签 | 页面路径 | 组件 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- | --- |
| 自测测试点 | `/manual-testcases/list?tab=devselftest` | `ManualTestCaseList.vue` 内表格 | 查看脑图、编辑自测测试点、提缺陷、审核 | 需求编号、需求标题、模块、测试点、优先级、前置条件、步骤、期望结果、备注、状态、审核状态、组别、前端、后端、模块路径、更新时间 | `GET /api/testcases/dev-self-test/`，`GET /api/testcases/dev-self-test/detail/`，`PATCH /api/testcases/dev-self-test/detail/`，`POST /api/testcases/dev-self-test/audit/` | `dev_self_test_records`、`manual_testcase_mindmaps` |
| 技术方案设计 | `/manual-testcases/list?tab=technical-solution-designs` | `TechnicalSolutionDesignList.vue`、`TechnicalSolutionDesignForm.vue` | 新增、编辑、查看、删除、导入 Excel、状态流转、指派、评论、附件 | 编号、标题、优先级、问题原因、问题根因、需求编号、前端开发、后端开发、模块路径、关联测试用例、关联测试点、项目、版本、严重程度、状态、处理人、创建人、附件数、更新时间 | `/api/defects/technical-solution-designs/` 系列 | `defects(record_type=technical_solution_design)`、`defect_attachments`、`defect_comments`、`defect_histories` |

### 5.5 测试：脑图 / 用例 / 测试点

| 页签 | 页面路径 | 组件 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- | --- |
| 测试脑图 | `/manual-testcases/list?tab=mindmaps` | `ManualTestCaseList.vue`、`ManualTestCaseEditor.vue` | 新建、编辑、查看、删除、批量删除、复制、按目录/版本/需求过滤 | 脑图名称、需求编号、需求标题、目录、版本、组别、前端、后端、执行人、URL、更新时间 | `GET/POST/PUT/DELETE /api/testcases/manual-mindmaps/` | `manual_testcase_mindmaps` |
| 测试用例 | `/manual-testcases/list?tab=testcases` | `ManualTestCaseList.vue` | 从脑图节点提取测试用例，查看/过滤/跳转脑图 | 用例标题、前置条件、步骤、预期结果、优先级、状态、模块路径、需求信息 | `GET /api/testcases/manual-mindmap-nodes/`，可关联 `/api/testcases/` | `manual_testcase_mindmaps.mindmap_data`、`testcases` |
| 测试点 | `/manual-testcases/list?tab=testpoints` | `ManualTestCaseList.vue` | 从脑图节点提取测试点，按状态/模块/需求过滤，提缺陷 | 测试点、模块、模块路径、优先级、状态、评审状态、需求编号、需求标题 | `GET /api/testcases/manual-mindmap-nodes/` | `manual_testcase_mindmaps.mindmap_data` |

### 5.6 缺陷：版本缺陷分析 / 版本缺陷 / 线上缺陷

| 页签 | 页面路径 | 组件 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- | --- |
| 版本缺陷分析 | `/manual-testcases/list?tab=version-defect-analysis` | `VersionDefectAnalysisPanel.vue` | 刷新统计，按当前版本或全部版本展示开发人员缺陷状态、问题根因、按版本统计 | 图表：开发人员、状态、问题根因、版本 | `GET /api/defects/version-analysis/` | `defects` |
| 版本缺陷 | `/manual-testcases/list?tab=version-defects` | `DefectList.vue`、`DefectForm.vue` | 新建缺陷、编辑、查看、删除、状态变更、指派、评论、附件、导入 Excel | 缺陷编号、标题、优先级、问题原因、问题根因、需求编号、前端开发、后端开发、模块路径、关联测试用例、关联测试点、项目、版本、严重程度、状态、处理人、创建人、附件数、更新时间 | `GET/POST /api/defects/`，`GET/PUT/PATCH/DELETE /api/defects/{id}/`，`POST /api/defects/import-excel/`，`POST /api/defects/{id}/status/`，`POST /api/defects/{id}/assignees/` | `defects(record_type=defect)`、`defect_attachments`、`defect_comments`、`defect_histories` |
| 线上缺陷 | `/manual-testcases/list?tab=bug-records` | `QualityAnalysisJiraData.vue` | 同步线上 BUG、筛选、扩展字段、清空所选、关联需求/测试用例/测试点、详情、打开 JIRA 链接 | 版本号、缺陷编号、缺陷标题、问题类型、模块、客户、优先级、状态、创建人、处理人、测试人员、责任组、同步时间、原始字段、关联需求/用例/测试点 | `GET /api/quality-analysis/jira-bug-records/`，`POST refresh/`，`POST clear-selected/`，`POST /api/quality-analysis/jira-bug-records/{id}/associations/` | `quality_analysis_jira_bug_records` |

注意：当前【缺陷】-【线上缺陷】页签隐藏“线上缺陷质量统计”图表；【报告】-【实时质量分析】中的同类分析图表仍保留，走 `QualityAnalysisVersionLivePanel.vue` 和实时质量分析接口。

### 5.7 报告：报告列表 / 实时质量分析

| 页签 | 页面路径 | 组件 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- | --- |
| 报告列表 | `/manual-testcases/list?tab=quality-report-list` | `QualityAnalysisReportListPanel.vue` | 上传报告 Excel、分析、刷新实时快照、分享、删除、进入详情 | 版本号、状态、缺陷总数、已分类数、创建人、创建时间、分析完成时间 | `GET/POST /api/quality-analysis/reports/`，`POST /api/quality-analysis/reports/{id}/analyze/`，`POST /api/quality-analysis/reports/{id}/share/`，`DELETE /api/quality-analysis/reports/{id}/` | `quality_analysis_reports` |
| 实时质量分析 | `/manual-testcases/list?tab=quality-report-live` | `QualityAnalysisReportDetailPanel.vue`、`QualityAnalysisVersionLivePanel.vue` | 实时生成版本质量分析、需求进展、测试进展、缺陷/工时/投入图表、复制分享链接 | 图表块、指标卡、分析叙述、版本/项目范围 | `GET /api/quality-analysis/reports/live-snapshot/`，`GET /api/quality-analysis/reports/live-version-analysis/`，`GET /api/quality-analysis/reports/live-requirement-overview/`，`GET /api/quality-analysis/reports/live-testing-overview/`，`GET /api/quality-analysis/reports/live-rd-progress-overview/`，`POST /api/quality-analysis/reports/live-share/` | 聚合读取 `quality_analysis_jira_requirement_records`、`manual_testcase_mindmaps`、`dev_self_test_records`、`defects`、`quality_analysis_jira_bug_records` |

### 5.8 配置

| 页签 / 页面 | 路径 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- |
| 项目环境 | `/manual-testcases/list?tab=project-environments` | 新增、编辑、启停、删除项目环境 | 项目、环境名称、URL、账号、备注、启用状态 | `/api/projects/environments/` 或项目环境相关 endpoint | `project_environments` |
| 项目资产图谱 | `/manual-testcases/list?tab=project-asset-insight` | 创建项目知识库、查看页面-接口-库表图、数据库ER图、代码调用图、幽灵代码排查、库表字段检索 | 项目、知识空间、仓库配置、数据库Schema、图谱类型、搜索关键词、中心表 | `GET /api/knowledge/asset-insight/`，`GET /api/knowledge/project-knowledge/status/`，`POST /api/knowledge/project-knowledge/enable/` | `knowledge_spaces`、`knowledge_repository_configs`、`knowledge_objects`、`knowledge_relations`、`knowledge_index_runs` |
| JIRA接口配置 | `/manual-testcases/list?tab=configs` | 新增、编辑、复制、删除、执行 BUG/需求接口配置 | 接口类型、版本号、配置名称、请求方法、请求 URL、超时、启用、同步记录、状态码、最后执行时间、执行结果、请求头 JSON、请求体、备注 | `GET/POST/PATCH/DELETE /api/quality-analysis/jira-configs/`，`/jira-requirement-configs/`，`POST {id}/execute/`，`GET /api/quality-analysis/jira-configs/combined/` | `quality_analysis_jira_configs`、`quality_analysis_jira_requirement_configs` |
| JIRA编号URL前缀配置 | `/manual-testcases/list?tab=other-settings` | 保存 JIRA 编号跳转前缀 | `jira_browse_prefix` | `GET/PUT /api/quality-analysis/settings/` | `quality_analysis_settings` |
| 邮件模板/邮件配置/测试发送/消息提醒 | `email-template-config`、`email-config`、`test-email`、`notification-settings` | 配置 SMTP、模板、测试发送、缺陷消息提醒 | host、port、username、password、from_name、from_email、模板字段、启用状态 | `GET/PUT /api/defects/email-config/`，`POST test-send/`，`POST verify-smtp/`，`GET/PUT /api/defects/notification-settings/` | `defect_email_configs` |
| 流程工作台 | `/manual-testcases/workflow-workbench` | 查看待办、实例、流程定义、规则、模拟、恢复版本、启动/处理/终止流程 | biz_type、definition、rule、instance、task、action log | `/api/workflow/*` | `workflow_definitions`、`workflow_rules`、`workflow_instances`、`workflow_tasks`、`workflow_action_logs` |

### 5.9 管理

| 页签 | 页面路径 | 功能与操作 | 字段 | API | 表 |
| --- | --- | --- | --- | --- | --- |
| 成员 | `/manual-testcases/list?tab=members` | 新增、编辑、停用/启用、重置密码、删除 | 用户名、姓名、邮箱、手机号、状态、角色/组信息 | `/api/auth/users/` | `users_user`、`user_profiles` |
| 组别 | `/manual-testcases/list?tab=groups` | 新增、编辑、删除、维护组成员 | 组名、描述、成员、角色 | `/api/auth/groups/` | Django group 相关表 |
| 角色 | `/manual-testcases/list?tab=roles` | 新增、编辑、删除、维护角色成员 | 角色名、描述、成员 | `/api/auth/roles/` | `users_role`、`users_role_membership` |
| 项目 | `/manual-testcases/list?tab=projects` | 新增、编辑、删除、设为默认、维护项目成员 | 项目名、描述、默认项目、成员、角色 | `/api/projects/`、`/api/projects/{id}/members/` | `projects`、`project_members` |
| 版本 | `/manual-testcases/list?tab=versions` | 新增、编辑、删除、设为默认 | 版本名称、项目、描述、默认版本 | `/api/versions/` | `versions` |
| 权限 | `/manual-testcases/list?tab=permissions` | 权限目录、角色授权、权限项维护 | 权限编码、名称、路由、父级、排序、角色授权 | `/api/auth/permission-items/`、`/api/auth/roles/{id}/permissions/` | `users_permission_item`、`users_role_permission` |

### 5.10 录制与自动化

| 页面 | 路径 | 功能与操作 | API | 表 / 文件 |
| --- | --- | --- | --- | --- |
| 自动化脚本生成 | `/manual-testcases/recording-scripts` | 基于说明、能力、页面上下文生成 Playwright 脚本 | `POST /api/testcases/playwright-recording-scripts/generate/` | `playwright_automation_scripts`、`playwright_automation_script_versions` |
| 自动化脚本管理 | `/manual-testcases/automation-scripts` | 列表、版本、恢复、删除、查看脚本 | `/api/testcases/playwright-automation-scripts/` | 同上 |
| 快照文件管理 | `/manual-testcases/snapshots` | 上传/解析/下载/删除/批量导出 Playwright 快照 | `/api/testcases/playwright-snapshots/` | 文件系统快照、解析元数据 |
| 录制结果管理 | `/manual-testcases/recordings` | 本地 Agent 录制、步骤管理、去重、Allure 报告、转流程 | `/api/testcases/playwright-recordings/` | `playwright_recording_sessions`、`playwright_recording_steps` |
| 流程管理 | `/manual-testcases/flows` | 创建、复制、删除、执行流程 | `/api/testcases/visual-flows/` | `visual_flows` |
| 可视化流程编辑器 | `/manual-testcases/visual-flow` | X6 节点编排、保存流程、绑定录制步骤 | `/api/testcases/visual-flows/{flow_id}/` | `visual_flows` |
| 测试执行结果 | `/manual-testcases/visual-flow-executions` | 查看执行结果、步骤、截图、日志 | `/api/testcases/visual-flow-executions/` | `visual_flow_executions`、`visual_flow_execution_steps` |

### 5.11 Wiki

| 项 | 内容 |
| --- | --- |
| 页面路径 | `/manual-testcases/wiki` |
| 组件 | `WikiManager.vue` |
| 功能 | Wiki 目录、页面内容、富文本、附件/图片、按项目组织知识 |
| API | `GET/POST /api/defects/wiki-directories/`，`GET/POST /api/defects/wiki-pages/` |
| 表 | `wiki_directories`、`defects(record_type=wiki)`、富文本图片文件 |

## 6. 数据库表分组速查

| 分组 | 表 |
| --- | --- |
| 项目/版本 | `projects`、`project_members`、`project_environments`、`versions` |
| 用户/权限 | `users_user`、`user_profiles`、`users_role`、`users_role_membership`、`users_permission_item`、`users_role_permission` |
| 需求/JIRA | `quality_analysis_jira_requirement_configs`、`quality_analysis_jira_requirement_records`、`quality_analysis_jira_requirement_record_attachments` |
| 线上缺陷/JIRA | `quality_analysis_jira_configs`、`quality_analysis_jira_bug_records`、`quality_analysis_settings` |
| 版本缺陷/技术方案/Wiki | `defects`、`defect_attachments`、`defect_comments`、`defect_histories`、`defect_email_configs`、`wiki_directories` |
| 测试资产 | `manual_testcase_categories`、`manual_testcase_mindmaps`、`dev_self_test_records`、`testcases`、`testcase_steps`、`testcase_attachments`、`testcase_comments` |
| 质量报告 | `quality_analysis_reports` |
| 流程 | `workflow_definitions`、`workflow_rules`、`workflow_instances`、`workflow_tasks`、`workflow_action_logs` |
| 自动化录制 | `playwright_recording_sessions`、`playwright_recording_steps`、`playwright_automation_scripts`、`playwright_automation_script_versions`、`visual_flows`、`visual_flow_executions`、`visual_flow_execution_steps` |

## 7. 知识库助手检索策略

1. 先识别用户问题属于哪个一级菜单和页签。
2. 再用本文定位页面路径、组件、主要操作、可见字段。
3. 如果用户问页面操作，只返回用户能打开的页面 URL，不把 API 当页面链接。
4. 如果用户问接口或数据来源，才输出 API 与表名，并标注需要登录态/鉴权。
5. 如果用户问真实业务数据，先调用对应 API 或数据库查询，再按用户指定口径聚合。
6. 如果用户要求图表，按平台 `TESTHUB_KNOWLEDGE_CHART` marker 返回图表数据。
7. 对同名概念要区分：
   - 版本缺陷：平台内缺陷表 `defects(record_type=defect)`。
   - 线上缺陷：外部 JIRA 同步表 `quality_analysis_jira_bug_records`。
   - 版本需求/JIRA需求数据：同源于 `quality_analysis_jira_requirement_records`，但页面操作能力不同。
   - 实时质量分析：实时聚合多表，不等同于历史 Excel 报告。

## 8. Obsidian + Codex 的建议

Obsidian 适合做人维护的知识库视图，因为它把笔记保存为本地 Markdown vault，外部编辑器和文件管理器也能直接编辑，同步和 Git 管理也比较自然。建议用 Obsidian 管理“可读知识”，用 Codex 管理“可执行知识”：

- Obsidian：页面说明、业务术语、统计口径、FAQ、会议纪要、决策记录、roadmap、ERD 草图。
- Codex `AGENTS.md`：仓库长期约定、验证命令、代码风格、不可触碰边界。
- Codex Skill：可重复执行的工作流，例如“更新思源质量 roadmap”、“补充接口到表映射”、“生成知识库问答卡片”。
- MCP：当 Codex 需要读取 Obsidian vault、内部文档服务、JIRA、GitHub、Figma 等外部系统时再接入。

推荐落地方式：

1. 在仓库中保留 `docs/manual-quality-knowledge-roadmap.md` 作为代码事实源。
2. 若团队使用 Obsidian，可把 `docs/` 或专门的 `knowledge-vault/` 作为 Obsidian vault，但不要把 Obsidian 的个人 workspace 状态文件作为业务事实。
3. 用 Git 管理 Markdown 知识库；`.obsidian/workspace.json`、`.obsidian/workspaces.json` 这类个人布局文件建议忽略。
4. 对 Codex，不要指望它自动读取整个 Obsidian 知识库；应把稳定规则写入 `AGENTS.md`，把重复流程写成 Skill，把外部知识库读取做成 MCP 或脚本。
5. 对平台内知识库助手，应把高频 roadmap 摘要注入固定上下文，真实业务数据仍走平台 API 查询。

结论：Obsidian 可以作为人类友好的知识编辑层；Codex 更适合作为把这些 Markdown 事实转化为代码修改、接口核验、文档更新、自动化脚本的执行层。两者结合的关键不是“装很多插件”，而是保持单一事实源、结构化索引和可验证的更新流程。
