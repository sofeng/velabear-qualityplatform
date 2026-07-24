<template>
  <div class="testcase-detail-page">
    <div class="page-header-card">
      <div>
        <h1 class="page-title">测试用例详情</h1>
        <p class="page-subtitle">查看手工测试用例，并直接生成对应的 UI 自动化候选用例。</p>
      </div>
      <div class="header-actions">
        <el-button @click="router.back()">返回</el-button>
        <el-button @click="goToUiAutomationCases">查看UI自动化用例</el-button>
        <el-button type="primary" @click="openGenerateDialog">生成UI自动化用例</el-button>
        <el-button type="warning" @click="editTestCase">编辑</el-button>
      </div>
    </div>

    <div v-if="testcase" class="summary-grid">
      <div class="summary-card">
        <span>来源项目</span>
        <strong>{{ testcase.project?.name || '-' }}</strong>
      </div>
      <div class="summary-card">
        <span>优先级</span>
        <strong>{{ getPriorityText(testcase.priority) }}</strong>
      </div>
      <div class="summary-card">
        <span>状态</span>
        <strong>{{ getStatusText(testcase.status) }}</strong>
      </div>
      <div class="summary-card">
        <span>UI自动化状态</span>
        <strong>{{ getUiStatusText(uiRecord?.status) }}</strong>
      </div>
      <div class="summary-card">
        <span>目标UI项目</span>
        <strong>{{ uiRecord?.target_ui_project_name || '-' }}</strong>
      </div>
      <div class="summary-card">
        <span>落地UI用例</span>
        <strong>{{ uiRecord?.generated_test_case_name || '-' }}</strong>
      </div>
    </div>

    <el-alert
      v-if="uiRecord?.generation_error"
      type="warning"
      :closable="false"
      show-icon
      class="record-alert"
      :title="`最近一次生成存在告警：${uiRecord.generation_error}`"
    />

    <div class="card-container" v-if="testcase">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用例标题" :span="2">{{ testcase.title }}</el-descriptions-item>
        <el-descriptions-item label="优先级">
          <el-tag :class="`priority-tag ${testcase.priority}`">{{ getPriorityText(testcase.priority) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(testcase.status)">{{ getStatusText(testcase.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="测试类型">{{ getTypeText(testcase.test_type) }}</el-descriptions-item>
        <el-descriptions-item label="归属项目">{{ testcase.project?.name || '未关联项目' }}</el-descriptions-item>
        <el-descriptions-item label="关联版本" :span="2">
          <div v-if="testcase.versions?.length" class="version-tags">
            <el-tag
              v-for="version in testcase.versions"
              :key="version.id"
              size="small"
              :type="version.is_baseline ? 'warning' : 'info'"
              class="version-tag"
            >
              {{ version.name }}
            </el-tag>
          </div>
          <span v-else class="empty-text">未关联版本</span>
        </el-descriptions-item>
        <el-descriptions-item label="作者">{{ testcase.author?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(testcase.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="UI自动化状态" :span="2">
          <div class="record-summary">
            <el-tag :type="getUiStatusType(uiRecord?.status)">{{ getUiStatusText(uiRecord?.status) }}</el-tag>
            <span v-if="uiRecord?.target_ui_project_name">目标UI项目：{{ uiRecord.target_ui_project_name }}</span>
            <span v-if="uiRecord?.generated_test_case_name">落地UI用例：{{ uiRecord.generated_test_case_name }}</span>
            <span v-if="uiRecord?.updated_at">最近更新时间：{{ formatDate(uiRecord.updated_at) }}</span>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="用例描述" :span="2">{{ testcase.description || '暂无描述' }}</el-descriptions-item>
        <el-descriptions-item label="前置条件" :span="2">
          <div class="rich-text" v-html="testcase.preconditions || '-'"></div>
        </el-descriptions-item>
        <el-descriptions-item label="操作步骤" :span="2">
          <div class="rich-text" v-html="testcase.steps || '-'"></div>
        </el-descriptions-item>
        <el-descriptions-item label="预期结果" :span="2">
          <div class="rich-text" v-html="testcase.expected_result || '-'"></div>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <el-dialog v-model="generateDialogVisible" title="生成 UI 自动化用例" width="520px">
      <el-form label-width="110px">
        <el-form-item label="目标项目">
          <el-select
            v-model="generateForm.targetUiProject"
            placeholder="当前用例所属项目"
            style="width: 100%"
            :disabled="!sourceProjectOption?.available"
          >
            <el-option
              v-if="sourceProjectOption"
              :key="sourceProjectOption.projectId"
              :label="formatTargetProjectLabel(sourceProjectOption)"
              :value="sourceProjectOption.uiProjectId"
              :disabled="!sourceProjectOption.available"
            />
          </el-select>
          <div v-if="sourceProjectOption?.available" class="field-tip">
            将落地到 UI 自动化项目：{{ sourceProjectOption.uiProjectName }}
          </div>
          <div v-else-if="sourceProjectOption" class="field-tip warning">
            当前 AI 项目未匹配到同名 UI 自动化项目，暂不可生成。
          </div>
        </el-form-item>
        <el-form-item label="执行引擎">
          <el-select v-model="generateForm.engine" style="width: 100%">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Selenium" value="selenium" />
          </el-select>
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="生成后可在【UI自动化用例】菜单页统一查看审核状态、编辑步骤并落地为正式 UI 自动化用例。"
        />
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitGenerate" :loading="generateLoading">开始生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const testcase = ref(null)
const uiRecord = ref(null)
const uiProjects = ref([])
const generateDialogVisible = ref(false)
const generateLoading = ref(false)

const generateForm = reactive({
  targetUiProject: null,
  engine: 'playwright',
})

const normalizeProjectName = (value) => (value || '').trim().toLowerCase()

const sourceProjectOption = computed(() => {
  const sourceProject = testcase.value?.project
  if (!sourceProject) return null

  const matchedUiProject = uiProjects.value.find(
    (item) => normalizeProjectName(item.name) === normalizeProjectName(sourceProject.name)
  )

  return {
    projectId: sourceProject.id,
    projectName: sourceProject.name,
    uiProjectId: matchedUiProject?.id || null,
    uiProjectName: matchedUiProject?.name || '',
    available: Boolean(matchedUiProject),
  }
})

const fetchTestCase = async () => {
  try {
    const response = await api.get(`/testcases/${route.params.id}/`)
    testcase.value = response.data
  } catch (error) {
    ElMessage.error('获取测试用例详情失败')
  }
}

const fetchUiAutomationRecord = async () => {
  try {
    const response = await api.get('/executions/testcase_ui_automation_records/by_testcase/', {
      params: { source_testcase: route.params.id },
    })
    uiRecord.value = Object.prototype.hasOwnProperty.call(response.data || {}, 'record')
      ? response.data.record
      : response.data || null
  } catch (error) {
    uiRecord.value = null
  }
}

const fetchUiProjects = async () => {
  try {
    const response = await api.get('/ui-automation/projects/', { params: { page_size: 1000 } })
    uiProjects.value = response.data?.results || response.data || []
  } catch (error) {
    uiProjects.value = []
  }
}

const openGenerateDialog = async () => {
  await fetchUiProjects()
  generateForm.targetUiProject = sourceProjectOption.value?.uiProjectId || uiRecord.value?.target_ui_project || null
  generateForm.engine = uiRecord.value?.engine || 'playwright'
  generateDialogVisible.value = true
}

const submitGenerate = async () => {
  if (!generateForm.targetUiProject) {
    ElMessage.warning('当前 AI 项目未匹配到同名 UI 自动化项目，暂不可生成')
    return
  }
  generateLoading.value = true
  try {
    const response = await api.post('/executions/testcase_ui_automation_records/generate/', {
      source_testcase: Number(route.params.id),
      target_ui_project: generateForm.targetUiProject || null,
      engine: generateForm.engine,
    })
    uiRecord.value = response.data
    generateDialogVisible.value = false
    ElMessage.success('AI UI 自动化候选用例生成完成，已进入审核页')
    router.push({
      path: '/ai-generation/ui-automation-cases',
      query: {
        source_testcase: route.params.id,
        open_record: response.data.id,
      },
    })
  } catch (error) {
    await fetchUiAutomationRecord()
    ElMessage.error(error.response?.data?.error || '生成 UI 自动化用例失败')
  } finally {
    generateLoading.value = false
  }
}

const editTestCase = () => {
  router.push(`/ai-generation/testcases/${route.params.id}/edit`)
}

const goToUiAutomationCases = () => {
  router.push({
    path: '/ai-generation/ui-automation-cases',
    query: { source_testcase: route.params.id },
  })
}

const getPriorityText = (priority) => ({
  low: '低',
  medium: '中',
  high: '高',
  critical: '紧急',
}[priority] || priority)

const getStatusType = (status) => ({
  draft: 'info',
  active: 'success',
  deprecated: 'warning',
}[status] || 'info')

const getStatusText = (status) => ({
  draft: '草稿',
  active: '激活',
  deprecated: '废弃',
}[status] || status)

const getTypeText = (type) => ({
  functional: '功能测试',
  integration: '集成测试',
  api: 'API测试',
  ui: 'UI测试',
  performance: '性能测试',
  security: '安全测试',
}[type] || '-')

const getUiStatusType = (status) => ({
  draft: 'info',
  generating: 'warning',
  pending_review: 'warning',
  approved: 'success',
  rejected: 'danger',
  failed: 'danger',
}[status] || 'info')

const getUiStatusText = (status) => ({
  draft: '未生成',
  generating: '生成中',
  pending_review: '待审核',
  approved: '已审核',
  rejected: '已驳回',
  failed: '失败',
}[status] || '暂无记录')

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const formatTargetProjectLabel = (option) => {
  if (!option) return ''
  return option.available ? option.projectName : `${option.projectName}（未匹配 UI 自动化项目）`
}

onMounted(async () => {
  await Promise.all([fetchTestCase(), fetchUiAutomationRecord()])
})
</script>

<style lang="scss" scoped>
.testcase-detail-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 28px 32px;
  border-radius: 18px;
  margin-bottom: 24px;
  color: #fff;
  background: linear-gradient(135deg, #1d4ed8, #0f766e);
}

.page-title {
  margin: 0 0 8px;
  font-size: 30px;
  font-weight: 700;
}

.page-subtitle {
  margin: 0;
  max-width: 720px;
  line-height: 1.6;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-card {
  padding: 16px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card span {
  font-size: 13px;
  color: #64748b;
}

.summary-card strong {
  font-size: 18px;
  color: #0f172a;
}

.record-alert {
  margin-bottom: 18px;
}

.card-container {
  background: #fff;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.priority-tag {
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}

.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.version-tag {
  margin: 0;
}

.record-summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.field-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.field-tip.warning {
  color: #b45309;
}

.rich-text {
  white-space: pre-wrap;
  line-height: 1.7;
  color: #334155;
}

.empty-text {
  color: #909399;
  font-style: italic;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .testcase-detail-page {
    padding: 16px;
  }

  .page-header-card {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
