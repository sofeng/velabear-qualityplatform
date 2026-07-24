<template>
  <div class="page-container workflow-workbench-page" data-testid="workflow-workbench-page">
    <div class="page-header" data-testid="workflow-workbench-header">
      <div>
        <h1 class="page-title">流程运营台</h1>
        <p class="page-subtitle">统一查看待办任务、流转实例、流程定义与规则，支撑需求和缺陷流转运营。</p>
      </div>
      <div class="header-actions">
        <el-button
          v-if="canManageWorkflow"
          :loading="escalationLoading"
          data-testid="workflow-run-escalations"
          @click="handleRunEscalations"
        >
          运行 SLA 检查
        </el-button>
        <el-button
          type="primary"
          :loading="refreshing"
          data-testid="workflow-refresh-current-tab"
          @click="refreshCurrentTab"
        >
          刷新当前页
        </el-button>
      </div>
    </div>

    <div class="summary-grid" data-testid="workflow-workbench-summary">
      <div class="summary-card" data-testid="workflow-summary-tasks">
        <span>我的待办</span>
        <strong>{{ tasks.length }}</strong>
      </div>
      <div class="summary-card" data-testid="workflow-summary-instances">
        <span>可见实例</span>
        <strong>{{ instances.length }}</strong>
      </div>
      <div class="summary-card" data-testid="workflow-summary-definitions">
        <span>流程定义</span>
        <strong>{{ definitions.length }}</strong>
      </div>
      <div class="summary-card" data-testid="workflow-summary-rules">
        <span>规则条数</span>
        <strong>{{ filteredRules.length }}</strong>
      </div>
    </div>

    <div class="tab-card" data-testid="workflow-workbench-tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="我的待办" name="tasks">
          <div class="filter-card" data-testid="workflow-task-filters">
            <span class="filter-label">业务类型</span>
            <el-radio-group v-model="taskFilters.bizType" @change="loadTasks">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="defect">缺陷</el-radio-button>
              <el-radio-button label="requirement">需求</el-radio-button>
            </el-radio-group>
            <span class="task-count">当前 {{ tasks.length }} 条</span>
          </div>

          <div class="table-card" v-loading="tasksLoading" data-testid="workflow-task-table-card">
            <el-empty v-if="!tasks.length" description="当前没有可处理的流程待办" />
            <el-table v-else :data="tasks" border stripe data-testid="workflow-task-table">
              <el-table-column label="业务类型" width="110">
                <template #default="{ row }">
                  <el-tag :type="getBizTypeTag(row.biz_type)">
                    {{ getBizTypeText(row.biz_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="业务编号" width="160">
                <template #default="{ row }">
                  {{ row.biz_code || `#${row.biz_id}` }}
                </template>
              </el-table-column>
              <el-table-column label="流转批次" width="110">
                <template #default="{ row }">
                  {{ getInstanceRunText(row.run_number) }}
                </template>
              </el-table-column>
              <el-table-column label="标题" min-width="260" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-button link type="primary" @click="openBusiness(row)">
                    {{ row.biz_title || `业务 ${row.biz_id}` }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column label="当前环节" min-width="180">
                <template #default="{ row }">
                  {{ row.summary?.step_name || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="处理人" width="160">
                <template #default="{ row }">
                  {{ getAssigneeName(row.summary?.assignee) }}
                </template>
              </el-table-column>
              <el-table-column label="截止时间" width="170">
                <template #default="{ row }">
                  {{ formatDateTime(row.summary?.due_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="320">
                <template #default="{ row }">
                  <div class="action-group">
                    <el-button link type="primary" @click="openBusiness(row)">查看</el-button>
                    <el-button
                      v-if="row.summary?.can_claim"
                      link
                      type="primary"
                      :loading="busyTaskKey === `${row.id}:claim`"
                      :data-testid="`workbench-task-action-${row.biz_type}-${row.biz_code || row.biz_id}-claim`"
                      @click="handleClaimTask(row)"
                    >
                      认领
                    </el-button>
                    <el-button
                      v-if="row.summary?.can_transfer"
                      link
                      type="warning"
                      :loading="busyTaskKey === `${row.id}:transfer`"
                      :data-testid="`workbench-task-action-${row.biz_type}-${row.biz_code || row.biz_id}-transfer`"
                      @click="openTransferDialog(row)"
                    >
                      转交
                    </el-button>
                    <el-button
                      v-for="action in row.summary?.available_actions || []"
                      :key="action.key"
                      :type="getActionButtonType(action.key)"
                      link
                      :disabled="!row.summary?.can_act"
                      :loading="busyTaskKey === `${row.id}:${action.key}`"
                      :data-testid="`workbench-task-action-${row.biz_type}-${row.biz_code || row.biz_id}-${action.key}`"
                      @click="handleTaskAction(row, action)"
                    >
                      {{ action.label }}
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="实例监控" name="instances">
          <div class="filter-card" data-testid="workflow-instance-filters">
            <span class="filter-label">业务类型</span>
            <el-radio-group v-model="instanceFilters.bizType" @change="loadInstances">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="defect">缺陷</el-radio-button>
              <el-radio-button label="requirement">需求</el-radio-button>
            </el-radio-group>
            <span class="filter-label status-label">实例状态</span>
            <el-radio-group v-model="instanceFilters.status" @change="loadInstances">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="running">运行中</el-radio-button>
              <el-radio-button label="completed">已完成</el-radio-button>
              <el-radio-button label="terminated">已终止</el-radio-button>
            </el-radio-group>
          </div>

          <div class="table-card" v-loading="instancesLoading" data-testid="workflow-instance-table-card">
            <el-empty v-if="!instances.length" description="当前没有可见的流程实例" />
            <el-table v-else :data="instances" border stripe data-testid="workflow-instance-table">
              <el-table-column label="业务类型" width="110">
                <template #default="{ row }">
                  <el-tag :type="getBizTypeTag(row.biz_type)">
                    {{ getBizTypeText(row.biz_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="业务编号" width="160">
                <template #default="{ row }">
                  {{ row.biz_code || `#${row.biz_id}` }}
                </template>
              </el-table-column>
              <el-table-column label="标题" min-width="260" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-button link type="primary" @click="openBusiness(row)">
                    {{ row.biz_title || `业务 ${row.biz_id}` }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column label="流程状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="getWorkflowStatusTag(row.status)">
                    {{ getWorkflowStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="当前环节" min-width="180">
                <template #default="{ row }">
                  {{ row.current_step_name || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="当前处理人" width="160">
                <template #default="{ row }">
                  {{ getAssigneeName(row.workflow?.current_task?.assignee) }}
                </template>
              </el-table-column>
              <el-table-column label="发起时间" width="170">
                <template #default="{ row }">
                  {{ formatDateTime(row.started_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="220">
                <template #default="{ row }">
                  <div class="action-group">
                    <el-button
                      link
                      type="primary"
                      :data-testid="`workflow-instance-view-${row.id}`"
                      @click="openInstanceDetail(row)"
                    >
                      查看详情
                    </el-button>
                    <el-button
                      v-if="canManageWorkflow && row.status === 'running'"
                      link
                      type="danger"
                      :loading="instanceTerminateLoading && selectedInstance?.id === row.id"
                      :data-testid="`workflow-instance-terminate-${row.id}`"
                      @click="handleTerminateInstance(row)"
                    >
                      终止流程
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="定义与规则" name="catalog">
          <div class="catalog-layout" v-loading="catalogLoading" data-testid="workflow-catalog-layout">
            <div class="catalog-section">
              <div class="section-head">
                <div class="section-head-main">
                  <div class="section-title">流程定义</div>
                  <span class="section-hint">支持在工作台中直接通过画布设计流程节点、连线和责任人配置。</span>
                </div>
                <el-button
                  v-if="canManageWorkflow"
                  type="primary"
                  plain
                  :loading="catalogBootstrapLoading"
                  data-testid="workflow-bootstrap-catalog"
                  @click="handleBootstrapCatalog"
                >
                  初始化默认流程
                </el-button>
              </div>
              <div v-if="!definitions.length" class="definition-empty-state">
                <el-empty description="当前没有流程定义" />
                <p class="definition-empty-hint">当前平台只支持缺陷流转和需求流转两套内置流程，先初始化后再设计。</p>
              </div>
              <div v-else class="definition-grid">
                <div
                  v-for="definition in definitions"
                  :key="definition.id"
                  class="definition-card"
                  :data-testid="`workflow-definition-${definition.id}`"
                >
                  <div class="definition-head">
                    <div>
                      <div class="definition-name">{{ definition.name }}</div>
                      <div class="definition-meta">
                        <el-tag size="small" :type="getBizTypeTag(definition.biz_type)">
                          {{ getBizTypeText(definition.biz_type) }}
                        </el-tag>
                        <span>场景：{{ definition.scene_key }}</span>
                        <span>版本：v{{ definition.version }}</span>
                      </div>
                      <div class="definition-card-summary">
                        <span>步骤 {{ getDefinitionStepCount(definition.config) }}</span>
                        <span>动作 {{ getDefinitionActionCount(definition.config) }}</span>
                      </div>
                    </div>
                    <div class="definition-head-actions">
                      <el-button
                        link
                        type="info"
                        :data-testid="`workflow-definition-versions-${definition.id}`"
                        @click="openDefinitionVersionDrawer(definition)"
                      >
                        版本历史
                      </el-button>
                      <el-button
                        v-if="canManageWorkflow"
                        link
                        type="primary"
                        :data-testid="`workflow-definition-edit-${definition.id}`"
                        @click="openDefinitionDialog(definition)"
                      >
                        设计流程
                      </el-button>
                    </div>
                  </div>
                  <div class="step-list">
                    <div
                      v-for="(step, index) in definition.config?.steps || []"
                      :key="`${definition.id}-${step.key}`"
                      class="step-item"
                    >
                      <span class="step-index">{{ index + 1 }}</span>
                      <div class="step-main">
                        <strong>{{ step.name }}</strong>
                        <span>{{ step.key }}</span>
                      </div>
                      <div class="step-extra">
                        <span v-if="step.candidate_roles?.length">角色：{{ step.candidate_roles.join(' / ') }}</span>
                        <span v-if="step.sla_hours">SLA：{{ step.sla_hours }}h</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="catalog-section">
              <div class="section-head">
                <div class="section-title">规则列表</div>
                <div class="inline-filters">
                  <span class="filter-label">业务类型</span>
                  <el-radio-group v-model="ruleFilters.bizType">
                    <el-radio-button label="">全部</el-radio-button>
                    <el-radio-button label="defect">缺陷</el-radio-button>
                    <el-radio-button label="requirement">需求</el-radio-button>
                  </el-radio-group>
                  <el-button
                    v-if="canManageWorkflow"
                    type="primary"
                    data-testid="workflow-add-rule"
                    @click="openRuleDialog()"
                  >
                    新增规则
                  </el-button>
                </div>
              </div>

              <div v-if="definitions.length" class="simulation-card" data-testid="workflow-definition-simulation-card">
                <div class="simulation-card-head">
                  <div class="section-head-main">
                    <div class="section-title">规则模拟</div>
                    <span class="section-hint">先选择流程定义和业务场景，预演命中的规则、启用的步骤、SLA 和动作配置。</span>
                  </div>
                  <el-button
                    v-if="canManageWorkflow"
                    type="primary"
                    plain
                    :loading="definitionSimulationLoading"
                    data-testid="workflow-definition-simulate-run"
                    @click="handleRunDefinitionSimulation"
                  >
                    运行模拟
                  </el-button>
                </div>

                <div class="simulation-form-grid">
                  <div class="simulation-form-item" data-testid="workflow-definition-simulation-definition">
                    <span class="filter-label">流程定义</span>
                    <el-select v-model="definitionSimulationForm.definitionId" placeholder="请选择流程定义">
                      <el-option
                        v-for="definition in definitions"
                        :key="definition.id"
                        :label="`${definition.name} · v${definition.version}`"
                        :value="definition.id"
                      />
                    </el-select>
                  </div>

                  <div
                    v-if="selectedSimulationDefinition?.biz_type === 'defect'"
                    class="simulation-form-item"
                    data-testid="workflow-definition-simulation-severity"
                  >
                    <span class="filter-label">缺陷严重级别</span>
                    <el-select v-model="definitionSimulationForm.severity">
                      <el-option label="严重" value="critical" />
                      <el-option label="高" value="high" />
                      <el-option label="中" value="medium" />
                      <el-option label="低" value="low" />
                    </el-select>
                  </div>

                  <div
                    v-else-if="selectedSimulationDefinition?.biz_type === 'requirement'"
                    class="simulation-form-item"
                    data-testid="workflow-definition-simulation-requirement-level"
                  >
                    <span class="filter-label">需求等级</span>
                    <el-select v-model="definitionSimulationForm.requirementLevel">
                      <el-option label="高" value="high" />
                      <el-option label="中" value="medium" />
                      <el-option label="低" value="low" />
                    </el-select>
                  </div>
                </div>

                <template v-if="definitionSimulationResult">
                  <div class="simulation-summary-grid">
                    <div class="simulation-summary-card">
                      <span>首环节</span>
                      <strong data-testid="workflow-definition-simulation-first-step">
                        {{ definitionSimulationResult.first_step_name || '-' }}
                      </strong>
                    </div>
                    <div class="simulation-summary-card">
                      <span>启用步骤</span>
                      <strong>{{ definitionSimulationResult.active_step_count }}</strong>
                    </div>
                    <div class="simulation-summary-card">
                      <span>跳过步骤</span>
                      <strong>{{ definitionSimulationResult.skipped_step_count }}</strong>
                    </div>
                    <div class="simulation-summary-card">
                      <span>启动规则</span>
                      <strong>{{ definitionSimulationResult.start_rules?.length || 0 }}</strong>
                    </div>
                  </div>

                  <div class="simulation-info-grid">
                    <div class="simulation-info-card">
                      <span>输入场景</span>
                      <pre class="json-block" data-testid="workflow-definition-simulation-inputs">{{ formatJson(definitionSimulationResult.inputs) }}</pre>
                    </div>
                    <div class="simulation-info-card">
                      <span>生效变量</span>
                      <pre class="json-block" data-testid="workflow-definition-simulation-variables">{{ formatJson(definitionSimulationResult.variables) }}</pre>
                    </div>
                  </div>

                  <div class="simulation-rule-strip" data-testid="workflow-definition-simulation-start-rules">
                    <span class="simulation-strip-label">启动规则</span>
                    <el-tag
                      v-for="rule in definitionSimulationResult.start_rules || []"
                      :key="`start-rule-${rule.id}`"
                      size="small"
                      effect="plain"
                    >
                      {{ rule.name }}
                    </el-tag>
                    <span v-if="!(definitionSimulationResult.start_rules || []).length" class="simulation-strip-empty">未命中启动规则</span>
                  </div>

                  <div class="simulation-step-list" data-testid="workflow-definition-simulation-step-list">
                    <div
                      v-for="step in definitionSimulationResult.steps || []"
                      :key="`simulation-step-${step.key}`"
                      class="simulation-step-card"
                      :data-testid="`workflow-definition-simulation-step-${step.key}`"
                    >
                      <div class="simulation-step-head">
                        <div>
                          <div class="simulation-step-title">{{ step.index }}. {{ step.name }}</div>
                          <div class="simulation-step-meta">
                            <span>{{ step.key }}</span>
                            <span v-if="step.candidate_roles?.length">角色：{{ step.candidate_roles.join(' / ') }}</span>
                            <span v-if="step.sla_hours">SLA：{{ step.sla_hours }}h</span>
                            <span v-if="step.remind_after_hours">提醒：{{ step.remind_after_hours }}h</span>
                            <span v-if="step.escalation_after_hours">升级：{{ step.escalation_after_hours }}h</span>
                          </div>
                        </div>
                        <el-tag :type="step.enabled ? 'success' : 'info'">
                          {{ step.enabled ? '本场景启用' : '本场景跳过' }}
                        </el-tag>
                      </div>

                      <div v-if="step.skip_reason" class="simulation-step-skip-reason">{{ step.skip_reason }}</div>

                      <div class="simulation-rule-strip">
                        <span class="simulation-strip-label">命中规则</span>
                        <el-tag
                          v-for="rule in step.matched_rules || []"
                          :key="`step-rule-${step.key}-${rule.id}`"
                          size="small"
                          effect="plain"
                        >
                          {{ rule.name }}
                        </el-tag>
                        <span v-if="!(step.matched_rules || []).length" class="simulation-strip-empty">未命中步骤规则</span>
                      </div>

                      <div class="simulation-rule-strip">
                        <span class="simulation-strip-label">动作</span>
                        <el-tag
                          v-for="action in step.actions || []"
                          :key="`step-action-${step.key}-${action.key}`"
                          size="small"
                          effect="light"
                        >
                          {{ action.label || action.key }} -> {{ action.complete ? '结束流程' : (action.next || '-') }}
                        </el-tag>
                      </div>
                    </div>
                  </div>
                </template>
              </div>

              <el-empty v-if="!filteredRules.length" description="当前没有匹配的规则" />
              <el-table v-else :data="filteredRules" border stripe data-testid="workflow-rule-table">
                <el-table-column label="业务类型" width="110">
                  <template #default="{ row }">
                    <el-tag :type="getBizTypeTag(row.biz_type)">
                      {{ getBizTypeText(row.biz_type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="step_key" label="步骤键" width="140" />
                <el-table-column prop="name" label="规则名称" min-width="220" show-overflow-tooltip />
                <el-table-column prop="priority" label="优先级" width="110" />
                <el-table-column label="条件" min-width="220">
                  <template #default="{ row }">
                    <pre class="json-block" :data-testid="`workflow-rule-conditions-${row.id}`">{{ formatJson(row.conditions) }}</pre>
                  </template>
                </el-table-column>
                <el-table-column label="输出" min-width="260">
                  <template #default="{ row }">
                    <pre class="json-block" :data-testid="`workflow-rule-outputs-${row.id}`">{{ formatJson(row.outputs) }}</pre>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.is_active ? 'success' : 'info'">
                      {{ row.is_active ? '启用' : '停用' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column v-if="canManageWorkflow" label="操作" width="180">
                  <template #default="{ row }">
                    <div class="action-group">
                      <el-button
                        link
                        type="primary"
                        :data-testid="`workflow-rule-edit-${row.id}`"
                        @click="openRuleDialog(row)"
                      >
                        编辑
                      </el-button>
                      <el-button
                        link
                        type="danger"
                        :data-testid="`workflow-rule-delete-${row.id}`"
                        @click="handleDeleteRule(row)"
                      >
                        删除
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog
      v-model="ruleDialogVisible"
      :title="editingRuleId ? '编辑流程规则' : '新增流程规则'"
      width="720px"
      class="workflow-rule-dialog"
      data-testid="workflow-rule-dialog"
      destroy-on-close
    >
      <el-form label-width="110px" data-testid="workflow-rule-form">
        <div class="rule-form-grid">
          <el-form-item label="业务类型">
            <div data-testid="workflow-rule-biz-type">
              <el-select v-model="ruleForm.biz_type" placeholder="请选择业务类型">
                <el-option label="缺陷" value="defect" />
                <el-option label="需求" value="requirement" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="场景键">
            <div data-testid="workflow-rule-scene-key">
              <el-input v-model="ruleForm.scene_key" placeholder="default" />
            </div>
          </el-form-item>
          <el-form-item label="步骤键">
            <div data-testid="workflow-rule-step-key">
              <el-input v-model="ruleForm.step_key" placeholder="例如 triage 或 *" />
            </div>
          </el-form-item>
          <el-form-item label="优先级">
            <div data-testid="workflow-rule-priority">
              <el-input-number v-model="ruleForm.priority" :min="1" :max="9999" />
            </div>
          </el-form-item>
        </div>
        <el-form-item label="规则名称">
          <div data-testid="workflow-rule-name">
            <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
          </div>
        </el-form-item>
        <el-form-item label="匹配条件">
          <div data-testid="workflow-rule-conditions-input">
            <el-input
              v-model="ruleForm.conditionsText"
              type="textarea"
              :rows="6"
              placeholder='例如：{"severity":["critical"]}'
            />
          </div>
        </el-form-item>
        <el-form-item label="规则输出">
          <div data-testid="workflow-rule-outputs-input">
            <el-input
              v-model="ruleForm.outputsText"
              type="textarea"
              :rows="8"
              placeholder='例如：{"sla_hours":4,"set_variables":{"need_qa_review":false}}'
            />
          </div>
        </el-form-item>
        <el-form-item label="启用状态">
          <div data-testid="workflow-rule-active">
            <el-switch v-model="ruleForm.is_active" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button data-testid="workflow-rule-cancel" @click="ruleDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="ruleSaving" data-testid="workflow-rule-save" @click="handleSaveRule">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="definitionDialogVisible"
      :title="editingDefinitionId ? '设计流程定义' : '流程定义'"
      width="92%"
      class="workflow-definition-dialog"
      data-testid="workflow-definition-dialog"
      destroy-on-close
    >
      <div class="definition-form-layout" data-testid="workflow-definition-form">
        <div class="definition-form-grid">
          <div class="definition-form-card">
            <span>业务类型</span>
            <strong>{{ getBizTypeText(definitionForm.biz_type) }}</strong>
          </div>
          <div class="definition-form-card">
            <span>定义键</span>
            <strong>{{ definitionForm.key || '-' }}</strong>
          </div>
          <div class="definition-form-card">
            <span>场景键</span>
            <strong>{{ definitionForm.scene_key || '-' }}</strong>
          </div>
          <div class="definition-form-card">
            <span>保存策略</span>
            <strong>保存后自动发布新版本</strong>
          </div>
        </div>

        <el-form label-width="100px">
          <el-form-item label="流程名称">
            <div data-testid="workflow-definition-name">
              <el-input v-model="definitionForm.name" placeholder="请输入流程名称" />
            </div>
          </el-form-item>
        </el-form>

        <WorkflowDefinitionCanvasEditor
          ref="definitionCanvasEditorRef"
          :initial-config="definitionForm.config"
          :role-options="workflowRoleOptions"
          :fallback-options="workflowFallbackOptions"
        />
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button data-testid="workflow-definition-cancel" @click="definitionDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="definitionSaving"
            data-testid="workflow-definition-save"
            @click="handleSaveDefinition"
          >
            发布新版本
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer
      v-model="definitionVersionDrawerVisible"
      title="流程定义版本历史"
      size="960px"
      destroy-on-close
      data-testid="workflow-definition-version-drawer"
    >
      <template v-if="versionHistoryDefinition">
        <div class="definition-version-layout" v-loading="definitionVersionLoading">
          <div class="definition-version-sidebar">
            <div class="definition-version-family">
              <div class="definition-version-family-title">{{ versionHistoryDefinition.name }}</div>
              <div class="definition-version-family-meta">
                <el-tag size="small" :type="getBizTypeTag(versionHistoryDefinition.biz_type)">
                  {{ getBizTypeText(versionHistoryDefinition.biz_type) }}
                </el-tag>
                <span>{{ versionHistoryDefinition.key }}</span>
                <span>{{ versionHistoryDefinition.scene_key }}</span>
              </div>
            </div>

            <div class="definition-version-list" data-testid="workflow-definition-version-list">
              <button
                v-for="version in definitionVersions"
                :key="version.id"
                type="button"
                class="definition-version-item"
                :class="{ 'is-active': selectedDefinitionVersion?.id === version.id }"
                :data-testid="`workflow-definition-version-item-${version.id}`"
                @click="selectedDefinitionVersionId = version.id"
              >
                <div class="definition-version-item-head">
                  <strong>v{{ version.version }}</strong>
                  <el-tag size="small" :type="version.is_active ? 'success' : 'info'">
                    {{ version.is_active ? '当前启用' : '历史版本' }}
                  </el-tag>
                </div>
                <div class="definition-version-item-name">{{ version.name }}</div>
                <div class="definition-version-item-meta">
                  <span>{{ getVersionActorName(version.created_by) }}</span>
                  <span>{{ formatDateTime(version.created_at) }}</span>
                </div>
                <div class="definition-version-item-diff">{{ formatDefinitionVersionChange(version.change_summary) }}</div>
              </button>
            </div>
          </div>

          <div class="definition-version-detail" v-if="selectedDefinitionVersion">
            <div class="definition-version-detail-head">
              <div>
                <div class="definition-version-detail-title">
                  {{ selectedDefinitionVersion.name }}
                  <el-tag size="small" :type="selectedDefinitionVersion.is_active ? 'success' : 'info'">
                    v{{ selectedDefinitionVersion.version }}
                  </el-tag>
                </div>
                <div class="definition-version-detail-subtitle">
                  发布人：{{ getVersionActorName(selectedDefinitionVersion.created_by) }} / 发布时间：{{ formatDateTime(selectedDefinitionVersion.created_at) }}
                </div>
              </div>
              <el-button
                v-if="canManageWorkflow && !selectedDefinitionVersion.is_active"
                type="primary"
                plain
                :loading="definitionRestoreLoading"
                data-testid="workflow-definition-version-restore"
                @click="handleRestoreDefinitionVersion(selectedDefinitionVersion)"
              >
                恢复为当前版本
              </el-button>
            </div>

            <div class="definition-version-summary-grid">
              <div class="definition-version-summary-card">
                <span>步骤数</span>
                <strong data-testid="workflow-definition-version-step-count">{{ selectedDefinitionVersion.step_count }}</strong>
              </div>
              <div class="definition-version-summary-card">
                <span>动作数</span>
                <strong data-testid="workflow-definition-version-action-count">{{ selectedDefinitionVersion.action_count }}</strong>
              </div>
              <div class="definition-version-summary-card definition-version-summary-card-wide">
                <span>变更摘要</span>
                <strong>{{ formatDefinitionVersionChange(selectedDefinitionVersion.change_summary) }}</strong>
              </div>
            </div>

            <div class="definition-version-change-grid">
              <div class="definition-version-change-card">
                <span>新增步骤</span>
                <strong>{{ formatVersionStepList(selectedDefinitionVersion.change_summary?.added_steps) }}</strong>
              </div>
              <div class="definition-version-change-card">
                <span>移除步骤</span>
                <strong>{{ formatVersionStepList(selectedDefinitionVersion.change_summary?.removed_steps) }}</strong>
              </div>
              <div class="definition-version-change-card">
                <span>调整步骤</span>
                <strong>{{ formatVersionStepList(selectedDefinitionVersion.change_summary?.modified_steps) }}</strong>
              </div>
            </div>

            <div class="definition-version-step-list" data-testid="workflow-definition-version-steps">
              <div
                v-for="(step, index) in selectedDefinitionVersion.steps"
                :key="`${selectedDefinitionVersion.id}-${step.key || index}`"
                class="definition-version-step-card"
              >
                <div class="definition-version-step-head">
                  <div>
                    <div class="definition-version-step-title">{{ index + 1 }}. {{ step.name || step.key }}</div>
                    <div class="definition-version-step-meta">
                      <span>{{ step.key }}</span>
                      <span v-if="step.candidate_roles?.length">角色：{{ step.candidate_roles.join(' / ') }}</span>
                      <span v-if="step.sla_hours">SLA：{{ step.sla_hours }}h</span>
                      <span v-if="step.enabled_if">条件：{{ step.enabled_if }}</span>
                    </div>
                  </div>
                  <el-tag size="small" type="info">{{ step.actions.length }} 个动作</el-tag>
                </div>
                <div class="definition-version-action-tags">
                  <el-tag
                    v-for="action in step.actions"
                    :key="`${step.key}-${action.key}`"
                    size="small"
                    effect="plain"
                  >
                    {{ action.label || action.key }} -> {{ action.complete ? '结束流程' : (action.next || '-') }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>

    <WorkflowTransferDialog
      :visible="transferDialogVisible"
      :task="selectedTransferTask"
      :loading="transferSaving"
      @cancel="closeTransferDialog"
      @submit="handleTransferSubmit"
    />

    <el-drawer
      v-model="instanceDetailVisible"
      title="流程实例详情"
      size="720px"
      destroy-on-close
      data-testid="workflow-instance-detail-drawer"
    >
      <template v-if="selectedInstance">
        <div class="instance-detail-layout">
          <div class="instance-detail-header">
            <div>
              <div class="instance-detail-title">{{ selectedInstance.biz_title || `业务 ${selectedInstance.biz_id}` }}</div>
              <div class="instance-detail-subtitle">
                {{ getBizTypeText(selectedInstance.biz_type) }} / {{ selectedInstance.biz_code || `#${selectedInstance.biz_id}` }} / {{ getInstanceRunText(selectedInstance.run_number) }}
              </div>
            </div>
            <div class="instance-detail-actions">
              <el-button plain @click="openBusiness(selectedInstance)">打开业务详情</el-button>
              <el-button
                v-if="canManageWorkflow && selectedInstance.status === 'running'"
                type="danger"
                :loading="instanceTerminateLoading"
                data-testid="workflow-instance-detail-terminate"
                @click="handleTerminateInstance(selectedInstance)"
              >
                终止流程
              </el-button>
            </div>
          </div>

          <div class="instance-detail-grid">
            <div class="instance-detail-card">
              <span>流转批次</span>
              <strong>{{ getInstanceRunText(selectedInstance.run_number) }}</strong>
            </div>
            <div class="instance-detail-card">
              <span>流程状态</span>
              <el-tag :type="getWorkflowStatusTag(selectedInstance.status)">
                {{ getWorkflowStatusText(selectedInstance.status) }}
              </el-tag>
            </div>
            <div class="instance-detail-card">
              <span>当前环节</span>
              <strong>{{ selectedInstance.workflow?.current_step_name || '-' }}</strong>
            </div>
            <div class="instance-detail-card">
              <span>当前处理人</span>
              <strong>{{ getAssigneeName(selectedInstance.workflow?.current_task?.assignee) }}</strong>
            </div>
            <div class="instance-detail-card">
              <span>发起时间</span>
              <strong>{{ formatDateTime(selectedInstance.started_at) }}</strong>
            </div>
            <div class="instance-detail-card">
              <span>完成时间</span>
              <strong>{{ formatDateTime(selectedInstance.completed_at || selectedInstance.workflow?.completed_at) }}</strong>
            </div>
            <div class="instance-detail-card">
              <span>候选处理人</span>
              <strong>{{ formatUsers(selectedInstance.workflow?.current_task?.candidate_users) }}</strong>
            </div>
          </div>

          <div
            v-if="selectedInstance.workflow?.status === 'terminated'"
            class="instance-warning"
            data-testid="workflow-instance-terminated-notice"
          >
            <strong>该实例已终止</strong>
            <span>{{ selectedInstance.workflow?.metadata?.termination_comment || '未填写终止原因。' }}</span>
          </div>

          <div class="instance-section">
            <div class="section-title">流程变量</div>
            <pre class="json-block instance-json" data-testid="workflow-instance-variables">{{ formatJson(selectedInstance.workflow?.variables) }}</pre>
          </div>

          <div class="instance-section">
            <div class="section-title">流程元数据</div>
            <pre class="json-block instance-json" data-testid="workflow-instance-metadata">{{ formatJson(selectedInstance.workflow?.metadata) }}</pre>
          </div>

          <div class="instance-section">
            <div class="section-title">流转记录</div>
            <div v-if="selectedInstanceTimeline.length" class="instance-timeline" data-testid="workflow-instance-timeline">
              <div
                v-for="item in selectedInstanceTimeline"
                :key="item.id"
                class="instance-timeline-item"
                :data-testid="`workflow-instance-timeline-item-${item.id}`"
              >
                <div class="instance-timeline-main">
                  <strong>{{ item.action_label || item.action }}</strong>
                  <span>{{ item.from_step_name || '-' }} -> {{ item.to_step_name || '-' }}</span>
                </div>
                <div class="instance-timeline-meta">
                  <span>{{ getOperatorName(item.operator) }}</span>
                  <span>{{ formatDateTime(item.created_at) }}</span>
                </div>
                <div v-if="item.comment" class="instance-timeline-comment">{{ item.comment }}</div>
              </div>
            </div>
            <el-empty v-else description="当前没有流转记录" />
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import WorkflowDefinitionCanvasEditor from '@/components/workflow/WorkflowDefinitionCanvasEditor.vue'
import WorkflowTransferDialog from '@/components/workflow/WorkflowTransferDialog.vue'
import {
  bootstrapWorkflowCatalog,
  createWorkflowRule,
  deleteWorkflowRule,
  executeWorkflowTaskAction,
  getWorkflowDefinitionVersions,
  getMyWorkflowTasks,
  getWorkflowDefinitions,
  getWorkflowInstances,
  getWorkflowRules,
  restoreWorkflowDefinition,
  simulateWorkflowDefinition,
  runWorkflowEscalations,
  terminateWorkflowInstance,
  updateWorkflowDefinition,
  updateWorkflowRule,
} from '@/api/workflow'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('tasks')
const tasksLoading = ref(false)
const instancesLoading = ref(false)
const catalogLoading = ref(false)
const catalogBootstrapLoading = ref(false)
const escalationLoading = ref(false)
const busyTaskKey = ref('')
const ruleDialogVisible = ref(false)
const ruleSaving = ref(false)
const editingRuleId = ref(null)
const definitionDialogVisible = ref(false)
const definitionSaving = ref(false)
const editingDefinitionId = ref(null)
const definitionCanvasEditorRef = ref(null)
const definitionVersionDrawerVisible = ref(false)
const definitionVersionLoading = ref(false)
const definitionRestoreLoading = ref(false)
const versionHistoryDefinition = ref(null)
const definitionVersions = ref([])
const selectedDefinitionVersionId = ref(null)
const definitionSimulationLoading = ref(false)
const definitionSimulationResult = ref(null)
const transferDialogVisible = ref(false)
const transferSaving = ref(false)
const selectedTransferTask = ref(null)
const instanceDetailVisible = ref(false)
const instanceTerminateLoading = ref(false)
const selectedInstance = ref(null)
const refreshing = computed(
  () => tasksLoading.value || instancesLoading.value || catalogLoading.value || catalogBootstrapLoading.value || escalationLoading.value,
)
const canManageWorkflow = computed(() => Boolean(userStore.user?.is_staff || userStore.user?.is_superuser))

const tasks = ref([])
const instances = ref([])
const definitions = ref([])
const rules = ref([])

const taskFilters = reactive({
  bizType: '',
})

const instanceFilters = reactive({
  bizType: '',
  status: '',
})

const ruleFilters = reactive({
  bizType: '',
})

const ruleForm = reactive({
  biz_type: 'defect',
  scene_key: 'default',
  step_key: '*',
  name: '',
  priority: 100,
  conditionsText: '{}',
  outputsText: '{}',
  is_active: true,
})

const definitionForm = reactive({
  id: null,
  biz_type: '',
  key: '',
  scene_key: '',
  name: '',
  config: {
    steps: [],
    editor: {},
  },
})

const definitionSimulationForm = reactive({
  definitionId: null,
  severity: 'critical',
  requirementLevel: 'high',
})

const workflowRoleOptions = [
  { label: '项目负责人', value: 'owner' },
  { label: '管理员', value: 'admin' },
  { label: '开发', value: 'developer' },
  { label: '测试', value: 'tester' },
]

const workflowFallbackOptions = [
  { label: '创建人', value: 'created_by' },
  { label: '缺陷处理人', value: 'assignees' },
  { label: '评审人或负责人', value: 'reviewer_or_owner' },
]

const filteredRules = computed(() =>
  ruleFilters.bizType ? rules.value.filter((item) => item.biz_type === ruleFilters.bizType) : rules.value,
)
const selectedInstanceTimeline = computed(() => [...(selectedInstance.value?.workflow?.timeline || [])].reverse())
const selectedDefinitionVersion = computed(
  () => definitionVersions.value.find((item) => item.id === selectedDefinitionVersionId.value) || definitionVersions.value[0] || null,
)
const selectedSimulationDefinition = computed(
  () => definitions.value.find((item) => item.id === definitionSimulationForm.definitionId) || null,
)

const unwrapList = (response) => response?.data?.results || response?.data || []
const normalizeInstance = (instance) => ({
  ...instance,
  workflow: instance?.workflow ? { ...instance.workflow } : null,
})

const formatDateTime = (value) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-')
const getDefinitionSteps = (config) => (Array.isArray(config?.steps) ? config.steps : [])
const getDefinitionStepCount = (config) => getDefinitionSteps(config).length
const getDefinitionActionCount = (config) =>
  getDefinitionSteps(config).reduce((total, step) => total + (Array.isArray(step?.actions) ? step.actions.length : 0), 0)

const formatJson = (value) => JSON.stringify(value || {}, null, 2)
const formatUsers = (users = []) =>
  Array.isArray(users) && users.length
    ? users.map((item) => item?.full_name || item?.username || `用户${item?.id}`).join('、')
    : '未配置'
const getVersionActorName = (user) => user?.full_name || user?.username || '系统'
const formatVersionStepList = (steps = []) => (Array.isArray(steps) && steps.length ? steps.join('、') : '无')
const isSameDefinitionFamily = (left, right) =>
  Boolean(
    left
    && right
    && left.biz_type === right.biz_type
    && left.key === right.key
    && left.scene_key === right.scene_key,
  )
const formatDefinitionVersionChange = (summary = {}) => {
  const segments = []
  if (summary?.name_changed) {
    segments.push('名称已调整')
  }
  if (Number(summary?.step_delta)) {
    const value = Number(summary.step_delta)
    segments.push(`步骤 ${value > 0 ? '+' : ''}${value}`)
  }
  if (Number(summary?.action_delta)) {
    const value = Number(summary.action_delta)
    segments.push(`动作 ${value > 0 ? '+' : ''}${value}`)
  }
  if (Array.isArray(summary?.added_steps) && summary.added_steps.length) {
    segments.push(`新增 ${summary.added_steps.join('、')}`)
  }
  if (Array.isArray(summary?.removed_steps) && summary.removed_steps.length) {
    segments.push(`移除 ${summary.removed_steps.join('、')}`)
  }
  if (Array.isArray(summary?.modified_steps) && summary.modified_steps.length) {
    segments.push(`调整 ${summary.modified_steps.join('、')}`)
  }
  return segments.length ? segments.join(' · ') : '与前一版本一致'
}

const buildDefinitionSimulationInputs = () => {
  if (selectedSimulationDefinition.value?.biz_type === 'defect') {
    return {
      severity: definitionSimulationForm.severity,
    }
  }
  if (selectedSimulationDefinition.value?.biz_type === 'requirement') {
    return {
      requirement_level: definitionSimulationForm.requirementLevel,
    }
  }
  return {}
}

const getBizTypeText = (bizType) =>
  ({
    defect: '缺陷',
    requirement: '需求',
  }[bizType] || bizType || '-')

const getBizTypeTag = (bizType) =>
  ({
    defect: 'danger',
    requirement: 'success',
  }[bizType] || 'info')

const getWorkflowStatusText = (value) =>
  ({
    running: '运行中',
    completed: '已完成',
    terminated: '已终止',
  }[value] || value || '-')

const getWorkflowStatusTag = (value) =>
  ({
    running: 'warning',
    completed: 'success',
    terminated: 'info',
  }[value] || 'info')

const getInstanceRunText = (runNumber) => `第${runNumber || 1}次`

const getActionButtonType = (actionKey) =>
  ({
    reject: 'danger',
    invalid: 'warning',
    approve: 'primary',
    resolve: 'primary',
    return: 'warning',
  }[actionKey] || 'primary')

const getAssigneeName = (assignee) => assignee?.full_name || assignee?.username || '待处理'
const getOperatorName = (operator) => operator?.full_name || operator?.username || '系统'

const openBusiness = (row) => {
  if (row.biz_type === 'defect') {
    router.push(`/manual-testcases/defects/${row.biz_id}/edit`)
    return
  }

  if (row.biz_type === 'requirement') {
    router.push({
      path: '/ai-generation/list',
      query: {
        tab: 'ai-requirements',
        detail_id: String(row.biz_id),
      },
    })
  }
}

const loadTasks = async () => {
  tasksLoading.value = true
  try {
    const response = await getMyWorkflowTasks({
      ...(taskFilters.bizType ? { biz_type: taskFilters.bizType } : {}),
      page_size: 100,
    })
    tasks.value = unwrapList(response)
  } catch (error) {
    tasks.value = []
    ElMessage.error(error.response?.data?.detail || '加载流程待办失败')
  } finally {
    tasksLoading.value = false
  }
}

const loadInstances = async () => {
  instancesLoading.value = true
  try {
    const response = await getWorkflowInstances({
      ...(instanceFilters.bizType ? { biz_type: instanceFilters.bizType } : {}),
      ...(instanceFilters.status ? { status: instanceFilters.status } : {}),
      page_size: 100,
    })
    instances.value = unwrapList(response)
    if (selectedInstance.value) {
      const matched = instances.value.find((item) => item.id === selectedInstance.value.id)
      if (matched) {
        selectedInstance.value = normalizeInstance(matched)
      }
    }
  } catch (error) {
    instances.value = []
    ElMessage.error(error.response?.data?.detail || '加载流程实例失败')
  } finally {
    instancesLoading.value = false
  }
}

const loadCatalog = async () => {
  catalogLoading.value = true
  try {
    const [definitionsResponse, rulesResponse] = await Promise.all([
      getWorkflowDefinitions({ page_size: 100 }),
      getWorkflowRules({ page_size: 100 }),
    ])
    definitions.value = unwrapList(definitionsResponse)
    rules.value = unwrapList(rulesResponse)
  } catch (error) {
    definitions.value = []
    rules.value = []
    ElMessage.error(error.response?.data?.detail || '加载流程定义与规则失败')
  } finally {
    catalogLoading.value = false
  }
}

const resetRuleForm = () => {
  editingRuleId.value = null
  ruleForm.biz_type = 'defect'
  ruleForm.scene_key = 'default'
  ruleForm.step_key = '*'
  ruleForm.name = ''
  ruleForm.priority = 100
  ruleForm.conditionsText = '{}'
  ruleForm.outputsText = '{}'
  ruleForm.is_active = true
}

const normalizeDefinitionAction = (action = {}) => ({
  key: String(action.key || '').trim(),
  label: String(action.label || '').trim(),
  next: String(action.next || '').trim(),
  complete: Boolean(action.complete),
  business_status: String(action.business_status || '').trim(),
})

const normalizeDefinitionStep = (step = {}) => ({
  key: String(step.key || '').trim(),
  name: String(step.name || '').trim(),
  candidate_roles: Array.isArray(step.candidate_roles) ? [...step.candidate_roles] : [],
  fallback_field: String(step.fallback_field || '').trim(),
  sla_hours: Number.isFinite(Number(step.sla_hours)) && step.sla_hours !== '' ? Number(step.sla_hours) : null,
  enabled_if: String(step.enabled_if || '').trim(),
  business_status: String(step.business_status || '').trim(),
  actions: Array.isArray(step.actions) && step.actions.length
    ? step.actions.map((action) => normalizeDefinitionAction(action))
    : [],
})

const normalizeDefinitionConfig = (config = {}) => ({
  steps: Array.isArray(config?.steps) ? config.steps.map((step) => normalizeDefinitionStep(step)) : [],
  editor: config?.editor && typeof config.editor === 'object'
    ? JSON.parse(JSON.stringify(config.editor))
    : {},
})

const resetDefinitionForm = () => {
  editingDefinitionId.value = null
  definitionForm.id = null
  definitionForm.biz_type = ''
  definitionForm.key = ''
  definitionForm.scene_key = ''
  definitionForm.name = ''
  definitionForm.config = {
    steps: [],
    editor: {},
  }
}

const openRuleDialog = (rule = null) => {
  resetRuleForm()
  if (rule) {
    editingRuleId.value = rule.id
    ruleForm.biz_type = rule.biz_type
    ruleForm.scene_key = rule.scene_key
    ruleForm.step_key = rule.step_key
    ruleForm.name = rule.name
    ruleForm.priority = rule.priority
    ruleForm.conditionsText = formatJson(rule.conditions)
    ruleForm.outputsText = formatJson(rule.outputs)
    ruleForm.is_active = Boolean(rule.is_active)
  }
  ruleDialogVisible.value = true
}

const openDefinitionDialog = (definition) => {
  resetDefinitionForm()
  editingDefinitionId.value = definition.id
  definitionForm.id = definition.id
  definitionForm.biz_type = definition.biz_type
  definitionForm.key = definition.key
  definitionForm.scene_key = definition.scene_key
  definitionForm.name = definition.name || ''
  definitionForm.config = normalizeDefinitionConfig(definition.config || {})
  definitionDialogVisible.value = true
}

const closeDefinitionVersionDrawer = () => {
  definitionVersionDrawerVisible.value = false
  versionHistoryDefinition.value = null
  definitionVersions.value = []
  selectedDefinitionVersionId.value = null
}

const loadDefinitionVersions = async (definitionId, { selectedId = null, preserveSelection = false } = {}) => {
  definitionVersionLoading.value = true
  try {
    const response = await getWorkflowDefinitionVersions(definitionId)
    definitionVersions.value = unwrapList(response)
    if (preserveSelection && definitionVersions.value.some((item) => item.id === selectedDefinitionVersionId.value)) {
      return
    }
    if (selectedId && definitionVersions.value.some((item) => item.id === selectedId)) {
      selectedDefinitionVersionId.value = selectedId
      return
    }
    selectedDefinitionVersionId.value = definitionVersions.value.find((item) => item.is_active)?.id || definitionVersions.value[0]?.id || null
  } catch (error) {
    definitionVersions.value = []
    selectedDefinitionVersionId.value = null
    ElMessage.error(error.response?.data?.detail || '加载流程定义版本历史失败')
  } finally {
    definitionVersionLoading.value = false
  }
}

const openDefinitionVersionDrawer = async (definition) => {
  versionHistoryDefinition.value = definition
  definitionVersionDrawerVisible.value = true
  await loadDefinitionVersions(definition.id)
}

const resetDefinitionSimulationResult = () => {
  definitionSimulationResult.value = null
}

const parseRuleJson = (value, fieldLabel) => {
  try {
    return JSON.parse(value || '{}')
  } catch {
    throw new Error(`${fieldLabel} 不是合法 JSON`)
  }
}

const buildDefinitionPayload = () => {
  const name = definitionForm.name.trim()
  if (!name) {
    throw new Error('流程名称不能为空')
  }
  const config = definitionCanvasEditorRef.value?.buildConfig?.()
  if (!config) {
    throw new Error('流程画布尚未准备完成')
  }

  return {
    name,
    config,
  }
}

const handleSaveDefinition = async () => {
  if (!editingDefinitionId.value) {
    return
  }

  let payload
  try {
    payload = buildDefinitionPayload()
  } catch (error) {
    ElMessage.error(error.message || '流程定义校验失败')
    return
  }

  definitionSaving.value = true
  try {
    await updateWorkflowDefinition(editingDefinitionId.value, payload)
    definitionDialogVisible.value = false
    ElMessage.success('流程定义已发布新版本')
    await loadCatalog()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '流程定义保存失败')
  } finally {
    definitionSaving.value = false
  }
}

const handleRestoreDefinitionVersion = async (version) => {
  if (!version || version.is_active) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认基于 v${version.version} 的配置恢复并发布一个新的当前版本吗？`,
      '恢复流程定义版本',
      {
        type: 'warning',
        confirmButtonText: '确认恢复',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  definitionRestoreLoading.value = true
  try {
    const response = await restoreWorkflowDefinition(version.id)
    await loadCatalog()
    const restoredDefinition =
      definitions.value.find((item) => item.id === response.data?.id)
      || definitions.value.find((item) => isSameDefinitionFamily(item, versionHistoryDefinition.value))
    if (restoredDefinition) {
      versionHistoryDefinition.value = restoredDefinition
    }
    await loadDefinitionVersions(
      restoredDefinition?.id || response.data?.id || version.id,
      { selectedId: response.data?.id },
    )
    ElMessage.success(`已基于 v${version.version} 发布恢复版本 v${response.data?.version || ''}`.trim())
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '恢复流程定义版本失败')
  } finally {
    definitionRestoreLoading.value = false
  }
}

const handleRunDefinitionSimulation = async () => {
  if (!selectedSimulationDefinition.value) {
    ElMessage.error('请先选择流程定义')
    return
  }

  definitionSimulationLoading.value = true
  try {
    const response = await simulateWorkflowDefinition({
      definition_id: selectedSimulationDefinition.value.id,
      inputs: buildDefinitionSimulationInputs(),
    })
    definitionSimulationResult.value = response.data
  } catch (error) {
    definitionSimulationResult.value = null
    ElMessage.error(error.response?.data?.detail || '运行规则模拟失败')
  } finally {
    definitionSimulationLoading.value = false
  }
}

const handleSaveRule = async () => {
  if (!ruleForm.name.trim()) {
    ElMessage.error('规则名称不能为空')
    return
  }

  let payload
  try {
    payload = {
      biz_type: ruleForm.biz_type,
      scene_key: ruleForm.scene_key.trim() || 'default',
      step_key: ruleForm.step_key.trim() || '*',
      name: ruleForm.name.trim(),
      priority: Number(ruleForm.priority) || 100,
      conditions: parseRuleJson(ruleForm.conditionsText, '匹配条件'),
      outputs: parseRuleJson(ruleForm.outputsText, '规则输出'),
      is_active: Boolean(ruleForm.is_active),
    }
  } catch (error) {
    ElMessage.error(error.message || '规则配置解析失败')
    return
  }

  ruleSaving.value = true
  try {
    if (editingRuleId.value) {
      await updateWorkflowRule(editingRuleId.value, payload)
      ElMessage.success('规则已更新')
    } else {
      await createWorkflowRule(payload)
      ElMessage.success('规则已创建')
    }
    ruleDialogVisible.value = false
    await loadCatalog()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '规则保存失败')
  } finally {
    ruleSaving.value = false
  }
}

const handleDeleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm(`确认删除规则“${rule.name}”吗？`, '删除规则', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await deleteWorkflowRule(rule.id)
    ElMessage.success('规则已删除')
    await loadCatalog()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '规则删除失败')
  }
}

const executeWorkbenchAction = async (taskId, payload, successMessage, busyKey) => {
  busyTaskKey.value = busyKey
  try {
    await executeWorkflowTaskAction(taskId, payload)
    ElMessage.success(successMessage)
    await Promise.all([loadTasks(), loadInstances()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '流程动作执行失败')
  } finally {
    busyTaskKey.value = ''
  }
}

const handleClaimTask = async (row) => {
  await executeWorkbenchAction(
    row.id,
    { action: 'claim', comment: '' },
    '待办已认领',
    `${row.id}:claim`,
  )
}

const openTransferDialog = (row) => {
  selectedTransferTask.value = row.summary
  transferDialogVisible.value = true
}

const closeTransferDialog = () => {
  transferDialogVisible.value = false
  selectedTransferTask.value = null
}

const handleTransferSubmit = async (payload) => {
  if (!selectedTransferTask.value) {
    return
  }

  transferSaving.value = true
  try {
    await executeWorkflowTaskAction(selectedTransferTask.value.id, {
      action: 'transfer',
      assignee_id: payload.assignee_id,
      comment: payload.comment || '',
    })
    ElMessage.success('待办已转交')
    closeTransferDialog()
    await Promise.all([loadTasks(), loadInstances()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '流程动作执行失败')
  } finally {
    transferSaving.value = false
  }
}

const handleTaskAction = async (row, action) => {
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '可选填写处理意见，留空也可以继续。',
      `执行“${action.label}”`,
      {
        inputType: 'textarea',
        inputPlaceholder: '例如：已验证通过，进入下一环节',
        confirmButtonText: '提交',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  await executeWorkbenchAction(
    row.id,
    {
      action: action.key,
      comment: promptResult.value || '',
    },
    `已执行：${action.label}`,
    `${row.id}:${action.key}`,
  )
}

const openInstanceDetail = (row) => {
  selectedInstance.value = normalizeInstance(row)
  instanceDetailVisible.value = true
}

const applyWorkflowSummaryToInstance = (row, workflow) => ({
  ...row,
  status: workflow.status,
  current_step_key: workflow.current_step_key,
  current_step_name: workflow.current_step_name,
  completed_at: workflow.completed_at,
  workflow,
})

const handleTerminateInstance = async (row) => {
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '可选填写终止原因，终止后当前待办会被取消，实例不可继续流转。',
      '终止流程实例',
      {
        inputType: 'textarea',
        inputPlaceholder: '例如：需求已取消，关闭当前流转',
        confirmButtonText: '确认终止',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }

  instanceTerminateLoading.value = true
  selectedInstance.value = normalizeInstance(row)
  try {
    const response = await terminateWorkflowInstance(row.id, {
      comment: promptResult.value || '',
    })
    selectedInstance.value = applyWorkflowSummaryToInstance(normalizeInstance(row), response.data)
    instanceDetailVisible.value = true
    ElMessage.success('流程实例已终止')
    await loadInstances()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '终止流程实例失败')
  } finally {
    instanceTerminateLoading.value = false
  }
}

const handleRunEscalations = async () => {
  escalationLoading.value = true
  try {
    const response = await runWorkflowEscalations()
    const reminders = response.data?.reminders ?? 0
    const escalations = response.data?.escalations ?? 0
    ElMessage.success(`SLA 检查完成：提醒 ${reminders} 条，升级 ${escalations} 条`)
    await Promise.all([loadTasks(), loadInstances()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '运行 SLA 检查失败')
  } finally {
    escalationLoading.value = false
  }
}

const handleBootstrapCatalog = async () => {
  catalogBootstrapLoading.value = true
  try {
    const response = await bootstrapWorkflowCatalog()
    const createdDefinitions = Array.isArray(response.data?.definitions) ? response.data.definitions : []
    ElMessage.success(`已准备 ${createdDefinitions.length} 条默认流程定义`)
    await loadCatalog()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '初始化默认流程失败')
  } finally {
    catalogBootstrapLoading.value = false
  }
}

const refreshCurrentTab = async () => {
  if (activeTab.value === 'tasks') {
    await loadTasks()
    return
  }
  if (activeTab.value === 'instances') {
    await loadInstances()
    return
  }
  await loadCatalog()
}

watch(activeTab, async (value) => {
  if (value === 'tasks' && !tasks.value.length) {
    await loadTasks()
    return
  }
  if (value === 'instances' && !instances.value.length) {
    await loadInstances()
    return
  }
  if (value === 'catalog' && (!definitions.value.length || !rules.value.length)) {
    await loadCatalog()
  }
})

watch(definitionVersionDrawerVisible, (value) => {
  if (!value) {
    closeDefinitionVersionDrawer()
  }
})

watch(
  definitions,
  (items) => {
    if (!items.length) {
      definitionSimulationForm.definitionId = null
      resetDefinitionSimulationResult()
      return
    }
    if (!items.some((item) => item.id === definitionSimulationForm.definitionId)) {
      definitionSimulationForm.definitionId = items[0].id
      resetDefinitionSimulationResult()
    }
  },
  { immediate: true },
)

watch(
  () => definitionSimulationForm.definitionId,
  () => {
    resetDefinitionSimulationResult()
  },
)

watch(
  () => [definitionSimulationForm.severity, definitionSimulationForm.requirementLevel],
  () => {
    resetDefinitionSimulationResult()
  },
)

onMounted(async () => {
  await Promise.all([loadTasks(), loadInstances(), loadCatalog()])
})
</script>

<style scoped>
.workflow-workbench-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header,
.summary-grid,
.tab-card,
.filter-card,
.table-card,
.catalog-section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}

.page-header,
.filter-card,
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-header,
.tab-card,
.catalog-section,
.filter-card,
.table-card {
  padding: 20px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #111827;
}

.page-subtitle {
  margin: 8px 0 0;
  color: #6b7280;
}

.header-actions,
.action-group,
.inline-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0;
  overflow: hidden;
}

.summary-card {
  padding: 18px 20px;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card:last-child {
  border-right: 0;
}

.summary-card span {
  color: #6b7280;
  font-size: 13px;
}

.summary-card strong {
  color: #111827;
  font-size: 26px;
}

.filter-card {
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.filter-label,
.task-count,
.status-label {
  color: #6b7280;
  font-size: 13px;
}

.status-label {
  margin-left: auto;
}

.catalog-layout {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(360px, 1.2fr);
  gap: 16px;
}

.catalog-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.section-head-main,
.definition-empty-state {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-hint {
  color: #6b7280;
  font-size: 13px;
}

.definition-empty-hint {
  margin: -8px 0 0;
  color: #6b7280;
  font-size: 13px;
  text-align: center;
}

.simulation-card,
.simulation-summary-card,
.simulation-info-card,
.simulation-step-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.simulation-card {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #f8fafc;
}

.simulation-card-head,
.simulation-step-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.simulation-form-grid,
.simulation-summary-grid,
.simulation-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.simulation-form-item,
.simulation-step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.simulation-summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.simulation-summary-card,
.simulation-info-card,
.simulation-step-card {
  padding: 14px 16px;
}

.simulation-summary-card {
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.simulation-summary-card span,
.simulation-info-card span,
.simulation-strip-label,
.simulation-step-skip-reason,
.simulation-step-meta {
  color: #6b7280;
  font-size: 12px;
}

.simulation-summary-card strong,
.simulation-step-title {
  color: #111827;
}

.simulation-info-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.simulation-rule-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.simulation-strip-label {
  min-width: 56px;
  font-weight: 600;
}

.simulation-strip-empty {
  color: #94a3b8;
  font-size: 12px;
}

.simulation-step-list {
  gap: 12px;
}

.simulation-step-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.simulation-step-title {
  font-size: 14px;
  font-weight: 600;
}

.simulation-step-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.definition-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.definition-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
}

.definition-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.definition-head-actions,
.definition-card-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.definition-head-actions {
  align-items: flex-start;
  justify-content: flex-end;
}

.definition-card-summary {
  margin-top: 8px;
  color: #6b7280;
  font-size: 12px;
}

.definition-name {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.definition-meta,
.step-extra {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #6b7280;
  font-size: 12px;
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.step-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) minmax(0, 180px);
  gap: 10px;
  align-items: start;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
}

.step-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-main strong {
  color: #111827;
}

.step-main span {
  color: #6b7280;
  font-size: 12px;
}

.rule-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.json-block {
  margin: 0;
  padding: 10px;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.definition-form-layout,
.definition-step-list,
.definition-action-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.definition-form-grid,
.definition-step-grid,
.definition-action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.definition-form-card,
.definition-step-card,
.definition-action-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.definition-form-card {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
}

.definition-form-card span {
  font-size: 12px;
  color: #6b7280;
}

.definition-form-card strong {
  color: #111827;
}

.definition-step-card {
  padding: 16px;
  background: #f8fafc;
}

.definition-step-header,
.definition-step-actions,
.definition-action-header,
.definition-step-toolbar,
.definition-action-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.definition-step-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.definition-step-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.definition-action-toolbar {
  margin-top: 12px;
}

.definition-action-card {
  padding: 14px 16px;
}

.definition-version-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  min-height: 540px;
}

.definition-version-sidebar,
.definition-version-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.definition-version-family,
.definition-version-summary-card,
.definition-version-change-card,
.definition-version-step-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.definition-version-family,
.definition-version-step-card {
  padding: 16px;
}

.definition-version-family-title,
.definition-version-detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.definition-version-family-meta,
.definition-version-detail-subtitle,
.definition-version-step-meta,
.definition-version-item-meta,
.definition-version-item-diff {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #6b7280;
  font-size: 12px;
}

.definition-version-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.definition-version-item {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.definition-version-item:hover,
.definition-version-item.is-active {
  border-color: #2563eb;
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.definition-version-item-head,
.definition-version-detail-head,
.definition-version-step-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.definition-version-item-name,
.definition-version-step-title {
  margin-top: 10px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.definition-version-summary-grid,
.definition-version-change-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.definition-version-summary-card,
.definition-version-change-card {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
}

.definition-version-summary-card span,
.definition-version-change-card span {
  font-size: 12px;
  color: #6b7280;
}

.definition-version-summary-card strong,
.definition-version-change-card strong {
  color: #111827;
}

.definition-version-summary-card-wide {
  grid-column: span 1;
}

.definition-version-step-list,
.definition-version-action-tags {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.definition-version-action-tags {
  margin-top: 12px;
  flex-direction: row;
  flex-wrap: wrap;
}

.definition-action-header {
  margin-bottom: 12px;
}

.full-width {
  grid-column: 1 / -1;
}

.instance-detail-layout,
.instance-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.instance-detail-header,
.instance-detail-actions,
.instance-timeline-meta,
.instance-timeline-main {
  display: flex;
  gap: 12px;
}

.instance-detail-header {
  align-items: flex-start;
  justify-content: space-between;
}

.instance-detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.instance-detail-subtitle,
.instance-timeline-meta,
.instance-timeline-main span {
  color: #6b7280;
  font-size: 13px;
}

.instance-detail-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.instance-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.instance-detail-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
}

.instance-detail-card span {
  font-size: 12px;
  color: #6b7280;
}

.instance-detail-card strong {
  color: #111827;
}

.instance-warning {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border: 1px solid #f59e0b;
  border-radius: 12px;
  background: #fffbeb;
  color: #92400e;
}

.instance-json {
  min-height: 96px;
}

.instance-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.instance-timeline-item {
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.instance-timeline-main {
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.instance-timeline-meta {
  margin-top: 8px;
  justify-content: space-between;
  flex-wrap: wrap;
}

.instance-timeline-comment {
  margin-top: 8px;
  color: #111827;
}

@media (max-width: 1024px) {
  .catalog-layout {
    grid-template-columns: 1fr;
  }

  .definition-version-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header,
  .filter-card,
  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-label {
    margin-left: 0;
  }

  .summary-card {
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }

  .summary-card:last-child {
    border-bottom: 0;
  }

  .rule-form-grid,
  .step-item,
  .instance-detail-grid,
  .definition-form-grid,
  .definition-step-grid,
  .definition-action-grid,
  .simulation-form-grid,
  .simulation-summary-grid,
  .simulation-info-grid,
  .definition-version-summary-grid,
  .definition-version-change-grid {
    grid-template-columns: 1fr;
  }

  .instance-detail-header {
    flex-direction: column;
  }

  .instance-detail-actions {
    justify-content: flex-start;
  }

  .definition-step-header,
  .definition-action-header,
  .definition-step-toolbar,
  .definition-action-toolbar,
  .definition-head,
  .simulation-card-head,
  .simulation-step-head,
  .definition-version-detail-head,
  .definition-version-step-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
