<template>
  <el-dialog
    :model-value="visible"
    title="转交流程待办"
    width="520px"
    data-testid="workflow-transfer-dialog"
    destroy-on-close
    @close="$emit('cancel')"
  >
    <div class="transfer-summary">
      <div class="summary-item">
        <span>当前环节</span>
        <strong>{{ task?.step_name || '-' }}</strong>
      </div>
      <div class="summary-item">
        <span>当前处理人</span>
        <strong>{{ formatUser(task?.assignee) || '未认领' }}</strong>
      </div>
    </div>

    <el-form label-width="88px" data-testid="workflow-transfer-form">
      <el-form-item label="转交给">
        <div data-testid="workflow-transfer-assignee">
          <el-select v-model="form.assigneeId" placeholder="请选择处理人" style="width: 100%">
            <el-option
              v-for="user in transferCandidates"
              :key="user.id"
              :label="formatUser(user)"
              :value="user.id"
            />
          </el-select>
        </div>
      </el-form-item>
      <el-form-item label="说明">
        <div data-testid="workflow-transfer-comment">
          <el-input
            v-model="form.comment"
            type="textarea"
            :rows="4"
            placeholder="可选填写转交原因，帮助下一位处理人快速接手"
          />
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button data-testid="workflow-transfer-cancel" @click="$emit('cancel')">取消</el-button>
        <el-button
          type="primary"
          :loading="loading"
          data-testid="workflow-transfer-submit"
          @click="handleSubmit"
        >
          确认转交
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  task: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['cancel', 'submit'])

const form = reactive({
  assigneeId: null,
  comment: '',
})

const transferCandidates = computed(() =>
  (props.task?.transfer_candidates || props.task?.candidate_users || []).filter((item) => item?.id),
)

const formatUser = (user) => {
  if (!user) {
    return ''
  }
  return user.full_name || user.username || `用户${user.id}`
}

watch(
  () => [props.visible, props.task?.id],
  () => {
    form.assigneeId = transferCandidates.value[0]?.id || null
    form.comment = ''
  },
  { immediate: true },
)

const handleSubmit = () => {
  if (!form.assigneeId) {
    ElMessage.error('请选择转交对象')
    return
  }

  emit('submit', {
    assignee_id: form.assigneeId,
    comment: form.comment.trim(),
  })
}
</script>

<style scoped>
.transfer-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.summary-item {
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.summary-item span {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.summary-item strong {
  display: block;
  margin-top: 6px;
  color: #111827;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 768px) {
  .transfer-summary {
    grid-template-columns: 1fr;
  }
}
</style>
