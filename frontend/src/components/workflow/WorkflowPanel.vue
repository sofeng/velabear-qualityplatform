<template>
  <div class="workflow-panel" :data-testid="`workflow-panel-${bizType}-${bizId}`">
    <div class="workflow-header" data-testid="workflow-header">
      <div>
        <div class="workflow-title">{{ title }}</div>
        <div class="workflow-subtitle">{{ subtitle }}</div>
      </div>
      <div class="workflow-header-actions">
        <el-button
          v-if="canRestartWorkflow"
          type="primary"
          plain
          :loading="startLoading"
          data-testid="workflow-restart-button"
          @click="handleStart"
        >
          重新发起
        </el-button>
        <el-button v-if="workbenchPath" link type="primary" @click="goWorkbench">我的待办</el-button>
      </div>
    </div>

    <div v-if="!workflow" class="workflow-empty" data-testid="workflow-empty">
      <div class="workflow-empty-title">当前未启动流程</div>
      <div class="workflow-empty-text">启动后将由流程节点驱动审批、状态流转和时限提醒。</div>
      <el-button
        type="primary"
        :loading="startLoading"
        data-testid="workflow-start-button"
        @click="handleStart"
      >
        启动流程
      </el-button>
    </div>

    <template v-else>
      <div class="workflow-meta-grid" data-testid="workflow-meta-grid">
        <div class="workflow-meta-card" data-testid="workflow-run-card">
          <span>流转批次</span>
          <strong>{{ runLabel }}</strong>
        </div>
        <div class="workflow-meta-card" data-testid="workflow-status-card">
          <span>流程状态</span>
          <el-tag :type="getWorkflowStatusTag(workflow.status)">{{ getWorkflowStatusText(workflow.status) }}</el-tag>
        </div>
        <div class="workflow-meta-card" data-testid="workflow-step-card">
          <span>当前环节</span>
          <strong>{{ workflow.current_step_name || '-' }}</strong>
        </div>
        <div class="workflow-meta-card" data-testid="workflow-assignee-card">
          <span>当前处理人</span>
          <strong>{{ currentTask?.assignee?.full_name || currentTask?.assignee?.username || '待处理' }}</strong>
        </div>
        <div class="workflow-meta-card" data-testid="workflow-due-card">
          <span>截止时间</span>
          <strong>{{ formatDateTime(currentTask?.due_at) }}</strong>
        </div>
      </div>

      <div
        v-if="workflow.status === 'terminated'"
        class="workflow-terminated-notice"
        data-testid="workflow-terminated-notice"
      >
        <strong>流程已被管理员终止</strong>
        <span>{{ workflow.metadata?.termination_comment || '未填写终止原因。' }}</span>
      </div>

      <div v-if="currentTask" class="task-card" data-testid="workflow-current-task">
        <div class="task-head" data-testid="workflow-current-task-head">
          <div>
            <div class="task-title">{{ currentTask.step_name }}</div>
            <div class="task-subtitle">候选人：{{ formatCandidates(currentTask.candidate_users) }}</div>
          </div>
          <el-tag :type="currentTask.can_act ? 'success' : 'info'">
            {{ currentTask.can_act ? '当前账号可处理' : '当前账号不可处理' }}
          </el-tag>
        </div>

        <div
          v-if="currentTask.can_claim || currentTask.can_transfer"
          class="task-collaboration"
          data-testid="workflow-task-collaboration"
        >
          <el-button
            v-if="currentTask.can_claim"
            plain
            type="primary"
            :loading="actionLoadingKey === 'claim'"
            data-testid="workflow-action-claim"
            @click="handleClaim"
          >
            认领
          </el-button>
          <el-button
            v-if="currentTask.can_transfer"
            plain
            type="warning"
            :loading="actionLoadingKey === 'transfer'"
            data-testid="workflow-action-transfer"
            @click="transferDialogVisible = true"
          >
            转交
          </el-button>
        </div>

        <div
          v-if="currentTask.can_act && currentTask.available_actions?.length"
          class="task-actions"
          data-testid="workflow-task-actions"
        >
          <el-button
            v-for="action in currentTask.available_actions"
            :key="action.key"
            :type="getActionButtonType(action.key)"
            :loading="actionLoadingKey === action.key"
            :data-testid="`workflow-action-${action.key}`"
            @click="handleAction(action)"
          >
            {{ action.label }}
          </el-button>
        </div>
      </div>

      <div v-if="recentTimeline.length" class="timeline-panel" data-testid="workflow-timeline">
        <div class="timeline-title">流转记录</div>
        <div
          v-for="item in recentTimeline"
          :key="item.id"
          class="timeline-item"
          :data-testid="`workflow-timeline-item-${item.id}`"
        >
          <div class="timeline-main">
            <strong>{{ item.action_label || item.action }}</strong>
            <span>{{ item.from_step_name || '-' }} -> {{ item.to_step_name || '-' }}</span>
          </div>
          <div class="timeline-meta">
            <span>{{ item.operator?.full_name || item.operator?.username || '系统' }}</span>
            <span>{{ formatDateTime(item.created_at) }}</span>
          </div>
          <div v-if="item.comment" class="timeline-comment">{{ item.comment }}</div>
        </div>
      </div>

      <WorkflowTransferDialog
        :visible="transferDialogVisible"
        :task="currentTask"
        :loading="actionLoadingKey === 'transfer'"
        @cancel="transferDialogVisible = false"
        @submit="handleTransfer"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { executeWorkflowTaskAction, startWorkflow } from '@/api/workflow'
import WorkflowTransferDialog from '@/components/workflow/WorkflowTransferDialog.vue'

const props = defineProps({
  title: {
    type: String,
    default: '流程流转',
  },
  subtitle: {
    type: String,
    default: '通过流程节点驱动审批、状态同步和时限控制。',
  },
  bizType: {
    type: String,
    required: true,
  },
  bizId: {
    type: [Number, String],
    required: true,
  },
  workflow: {
    type: Object,
    default: null,
  },
  workbenchPath: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['changed'])

const router = useRouter()
const startLoading = ref(false)
const actionLoadingKey = ref('')
const transferDialogVisible = ref(false)

const currentTask = computed(() => props.workflow?.current_task || null)
const recentTimeline = computed(() => [...(props.workflow?.timeline || [])].reverse().slice(0, 6))
const canRestartWorkflow = computed(() => Boolean(props.workflow && props.workflow.status !== 'running'))
const runLabel = computed(() => `第${props.workflow?.run_number || 1}次`)

const formatDateTime = (value) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-')

const formatCandidates = (users = []) => {
  if (!Array.isArray(users) || !users.length) {
    return '未配置'
  }
  return users.map((item) => item.full_name || item.username || `用户${item.id}`).join('、')
}

const getWorkflowStatusText = (value) =>
  ({
    running: '进行中',
    completed: '已完成',
    terminated: '已终止',
  }[value] || value || '-')

const getWorkflowStatusTag = (value) =>
  ({
    running: 'warning',
    completed: 'success',
    terminated: 'info',
  }[value] || 'info')

const getActionButtonType = (actionKey) =>
  ({
    reject: 'danger',
    reopen: 'warning',
    close: 'success',
    approve: 'primary',
    resolve: 'primary',
    submit: 'primary',
  }[actionKey] || 'primary')

const goWorkbench = () => {
  router.push(props.workbenchPath)
}

const handleStart = async () => {
  startLoading.value = true
  try {
    await startWorkflow(props.bizType, props.bizId)
    ElMessage.success(props.workflow ? '流程已重新发起' : '流程已启动')
    emit('changed')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '启动流程失败')
  } finally {
    startLoading.value = false
  }
}

const executeAction = async (payload, successMessage) => {
  actionLoadingKey.value = payload.action
  try {
    await executeWorkflowTaskAction(currentTask.value.id, payload)
    ElMessage.success(successMessage)
    emit('changed')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '流程动作执行失败')
  } finally {
    actionLoadingKey.value = ''
  }
}

const handleClaim = async () => {
  if (!currentTask.value) {
    return
  }
  await executeAction({ action: 'claim', comment: '' }, '待办已认领')
}

const handleAction = async (action) => {
  if (!currentTask.value) {
    return
  }

  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '可填写处理意见，留空也可以继续。',
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

  await executeAction(
    {
      action: action.key,
      comment: promptResult.value || '',
    },
    `已执行：${action.label}`,
  )
}

const handleTransfer = async (payload) => {
  if (!currentTask.value) {
    return
  }
  transferDialogVisible.value = false
  await executeAction(
    {
      action: 'transfer',
      assignee_id: payload.assignee_id,
      comment: payload.comment || '',
    },
    '待办已转交',
  )
}
</script>

<style scoped>
.workflow-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workflow-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.workflow-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.workflow-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.workflow-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.workflow-empty {
  padding: 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc, #eef6ff);
}

.workflow-empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.workflow-empty-text {
  margin: 8px 0 16px;
  line-height: 1.6;
  color: #475569;
}

.workflow-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.workflow-meta-card,
.task-card,
.timeline-panel {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
}

.workflow-meta-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-meta-card span {
  font-size: 12px;
  color: #6b7280;
}

.workflow-meta-card strong {
  color: #111827;
}

.workflow-terminated-notice {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #f59e0b;
  background: #fffbeb;
  color: #92400e;
}

.workflow-terminated-notice strong {
  color: #78350f;
}

.task-head,
.timeline-main,
.timeline-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-title,
.timeline-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.task-subtitle,
.timeline-meta {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7280;
}

.task-collaboration,
.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.timeline-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-item + .timeline-item {
  padding-top: 12px;
  border-top: 1px solid #eef2f7;
}

.timeline-main span,
.timeline-comment {
  font-size: 13px;
  color: #4b5563;
}

.timeline-comment {
  margin-top: 6px;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .task-head,
  .timeline-main,
  .timeline-meta,
  .workflow-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
