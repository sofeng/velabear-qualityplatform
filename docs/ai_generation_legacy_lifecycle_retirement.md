# AI 研发旧生命周期模块退役记录

## 当前决策

平台主工作流收敛到 `AI产品` 与 `AI会话详情页`。原来的 `AI文件`、`AI需求`、`AI开发`、`AI缺陷`、`AI运维` 不再作为独立菜单、独立工作台页签或未来会话详情页的嵌入式页面形态继续演进。

这些名称代表的能力仍然保留在后端服务、数据表、会话上下文和部署链路中，但后续展示与操作要按 AI 会话详情页中的项目生命周期事项重建。

## 本次已退役的展示入口

- `AI文件`
- `AI需求`
- `AI开发`
- `AI缺陷`
- `AI运维`
- 文件管理、需求管理、用例生成记录、AI开发任务、AI缺陷、构建配置、发布目标、部署模板、构建制品、发布任务、回滚记录等旧工作台 tab

旧菜单权限保留为兼容记录，但置为 inactive，并将历史角色权限迁移到 `AI产品 / AI会话` 入口。

## 本次保留的底层能力

- 需求文档、需求记录、生成用例等 `requirement_analysis` 数据与接口
- AI 开发任务、运行环境、构建与修复任务等 `ai_development` 数据与接口
- AI 缺陷记录与缺陷修复任务链路
- 部署目标、部署模板、构建制品、发布任务、回滚记录等部署服务
- AI 会话文件、会话上下文、Codex CLI 调用与技能运行链路
- 历史 URL、历史权限码、历史数据兼容

## 后续需要彻底清除的事项

完成 AI 会话详情页的新生命周期工作区后，再逐项清除以下旧形态：

- 删除 `frontend/src/views/ai-generation/AIFileManagement.vue` 的独立文件管理页面形态，保留或重建为会话文件资料组件。
- 删除 `frontend/src/views/requirement-analysis/AIRequirementsList.vue` 的独立需求管理页面形态，改为会话内需求澄清、需求基线、需求接受/拒绝工作区。
- 删除 `frontend/src/views/requirement-analysis/GeneratedTestCaseList.vue` 的独立用例生成记录页面形态，改为需求基线或测试资产页签内的会话产物。
- 删除 `frontend/src/views/ai-development/AIDevTaskList.vue` 的独立 AI 开发任务列表形态，改为会话内开发执行、Codex 任务、环境状态页签。
- 删除 `frontend/src/views/ai-development/AIDevDefectList.vue` 的独立 AI 缺陷列表形态，改为会话内问题修复页签。
- 删除 `frontend/src/views/deployments/DeploymentResourceConsole.vue` 作为 AI 运维旧菜单入口的展示形态，改为会话内部署运行页签；如果部署控制台仍被其他模块使用，只删除 AI 运维入口适配层。
- 清理 `frontend/src/utils/aiGenerationWorkspace.js` 中为历史 tab 保留的 alias，前提是历史 URL 已完成迁移或不再需要兼容。
- 清理 `frontend/src/router/index.js` 中旧 AI 生命周期路径到 CodexChat 的兼容跳转。
- 清理 `frontend/src/utils/permissions.js` 中旧 AI 生命周期权限码常量和兼容路由权限映射，前提是数据库角色权限已完成迁移且旧权限码不再作为审计记录。
- 清理 `apps/users/migrations` 中新增的退役迁移不需要做反向删除；只在未来新库初始化脚本中移除旧权限种子。
- 评估 `apps/assistant/tool_gateway.py`、`apps/assistant/views.py`、`apps/ai_development/views.py`、`apps/ai_development/defect_views.py`、`apps/requirement_analysis/views.py` 中旧命名的 API 是否需要重命名为会话生命周期语义。

## 清除前置条件

- AI 会话详情页已经提供文件资料、项目/需求澄清、需求基线、开发执行、问题修复、部署运行等新页签。
- 新页签能覆盖旧页面中的必要操作，并通过真实会话数据验证。
- 旧 URL 已稳定跳转到新入口至少一个版本周期。
- 角色权限已迁移到新的 AI 会话工作区权限。
- 已确认外部脚本、Codex CLI、技能、后端任务不再依赖旧页面路径或旧 tab 名称。
