<template>
  <div class="ui-automation-cases-page">
    <div class="page-header-card">
      <div>
        <h1 class="page-title">UI自动化用例</h1>
        <p class="page-subtitle">集中查看从手工测试用例生成的 UI 自动化候选结果、审核状态和落地情况。</p>
      </div>
      <div class="header-actions">
        <el-button @click="router.push('/ai-generation/testcases')">返回测试用例</el-button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card total">
        <span>总记录数</span>
        <strong>{{ stats.total || 0 }}</strong>
      </div>
      <div class="stat-card pending">
        <span>待审核</span>
        <strong>{{ stats.pending_review || 0 }}</strong>
      </div>
      <div class="stat-card approved">
        <span>已审核</span>
        <strong>{{ stats.approved || 0 }}</strong>
      </div>
      <div class="stat-card rejected">
        <span>已驳回</span>
        <strong>{{ stats.rejected || 0 }}</strong>
      </div>
      <div class="stat-card warning">
        <span>告警数</span>
        <strong>{{ stats.warnings || 0 }}</strong>
      </div>
      <div class="stat-card generated">
        <span>已落地</span>
        <strong>{{ stats.generated || 0 }}</strong>
      </div>
    </div>

    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-input
              v-model="filters.search"
              placeholder="搜索手工用例 / 候选用例 / UI用例"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.sourceProject" placeholder="来源项目" clearable filterable>
              <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.targetUiProject" placeholder="目标UI项目" clearable filterable>
              <el-option v-for="item in uiProjects" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.status" placeholder="审核状态" clearable>
              <el-option label="待审核" value="pending_review" />
              <el-option label="已审核" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-col>
          <el-col :span="6" class="filter-actions">
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-col>
        </el-row>
      </div>

      <el-table :data="records" v-loading="loading.page" border class="record-table">
        <el-table-column prop="source_testcase_title" label="来源测试用例" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="goToSourceTestCase(row.source_testcase)">{{ row.source_testcase_title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="source_project_name" label="来源项目" min-width="160" show-overflow-tooltip />
        <el-table-column prop="target_ui_project_name" label="目标UI项目" min-width="180" show-overflow-tooltip />
        <el-table-column prop="name" label="候选UI用例" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="openReviewDialog(row)">{{ row.name || '-' }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="生成方式" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.generation_source === 'ai' ? 'success' : 'warning'">
              {{ row.generation_source === 'ai' ? 'AI' : '规则' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="step_count" label="步骤数" width="90" />
        <el-table-column prop="generated_test_case_name" label="已落地UI用例" min-width="180" show-overflow-tooltip />
        <el-table-column prop="generation_error" label="生成告警" min-width="220" show-overflow-tooltip />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openReviewDialog(row)">审核</el-button>
              <el-button link type="success" @click="quickApprove(row)" :disabled="loading.actionId === row.id">
                快速通过
              </el-button>
              <el-button link type="danger" @click="quickReject(row)" :disabled="loading.actionId === row.id">
                驳回
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="reviewDialogVisible"
      title="审核 UI 自动化候选用例"
      width="92%"
      top="4vh"
      destroy-on-close
    >
      <div v-if="reviewForm.id" class="review-layout">
        <div class="review-grid">
          <div class="review-card">
            <h4>来源手工用例</h4>
            <div class="review-field"><span>标题</span><strong>{{ reviewForm.source_snapshot.title }}</strong></div>
            <div class="review-field"><span>描述</span><p>{{ reviewForm.source_snapshot.description || '-' }}</p></div>
            <div class="review-field"><span>前置条件</span><p>{{ reviewForm.source_snapshot.preconditions || '-' }}</p></div>
            <div class="review-field">
              <span>来源步骤</span>
              <ol class="source-steps">
                <li v-for="(item, index) in extractSourceSteps(reviewForm.source_snapshot)" :key="`${index}-${item}`">
                  {{ item }}
                </li>
              </ol>
            </div>
            <div class="review-field"><span>预期结果</span><p>{{ reviewForm.source_snapshot.expected_result || '-' }}</p></div>
          </div>

          <div class="review-card">
            <h4>候选用例信息</h4>
            <el-form label-width="100px">
              <el-form-item label="目标项目">
                <el-select
                  v-model="reviewForm.targetUiProject"
                  style="width: 100%"
                  :disabled="!reviewProjectOption?.available"
                >
                  <el-option
                    v-if="reviewProjectOption"
                    :key="reviewProjectOption.projectId"
                    :label="formatProjectOptionLabel(reviewProjectOption)"
                    :value="reviewProjectOption.uiProjectId"
                    :disabled="!reviewProjectOption.available"
                  />
                </el-select>
                <div v-if="reviewProjectOption?.available" class="form-tip">
                  将落地到 UI 自动化项目：{{ reviewProjectOption.uiProjectName }}
                </div>
                <div v-else-if="reviewProjectOption" class="form-tip warning">
                  当前 AI 项目未匹配到同名 UI 自动化项目，暂不可审核落地。
                </div>
              </el-form-item>
              <el-form-item label="用例名称">
                <el-input v-model="reviewForm.name" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="reviewForm.description" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="前置条件">
                <el-input v-model="reviewForm.preconditions" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="优先级">
                <el-select v-model="reviewForm.priority" style="width: 100%">
                  <el-option label="高" value="high" />
                  <el-option label="中" value="medium" />
                  <el-option label="低" value="low" />
                </el-select>
              </el-form-item>
              <el-form-item label="审核备注">
                <el-input v-model="reviewForm.reviewComment" type="textarea" :rows="4" />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="steps-toolbar">
          <div>
            <h4>步骤审核与元素映射</h4>
            <p>可以在这里修正动作、元素、断言和值，审核通过后会直接落地为 UI 自动化用例。</p>
          </div>
          <el-button type="primary" plain @click="addReviewStep">新增步骤</el-button>
        </div>

        <el-table :data="reviewForm.stepsData" border max-height="420">
          <el-table-column label="#" width="90">
            <template #default="{ row }">
              <el-input-number v-model="row.step_number" :min="1" :step="1" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="步骤描述" min-width="240">
            <template #default="{ row }">
              <el-input v-model="row.description" type="textarea" :rows="2" resize="none" />
            </template>
          </el-table-column>
          <el-table-column label="动作" width="160">
            <template #default="{ row }">
              <el-select v-model="row.action_type">
                <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="元素" min-width="220">
            <template #default="{ row }">
              <el-select
                v-model="row.element_id"
                filterable
                clearable
                placeholder="选择元素"
                @change="(value) => syncElementName(row, value)"
              >
                <el-option
                  v-for="item in reviewElementOptions"
                  :key="item.id"
                  :label="formatElementOption(item)"
                  :value="item.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="输入值" min-width="180">
            <template #default="{ row }">
              <el-input v-model="row.input_value" />
            </template>
          </el-table-column>
          <el-table-column label="断言" width="150">
            <template #default="{ row }">
              <el-select v-model="row.assert_type" clearable>
                <el-option v-for="item in assertOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="断言值" min-width="180">
            <template #default="{ row }">
              <el-input v-model="row.assert_value" />
            </template>
          </el-table-column>
          <el-table-column label="等待(ms)" width="120">
            <template #default="{ row }">
              <el-input-number v-model="row.wait_time" :min="0" :step="500" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ $index }">
              <el-button link type="danger" @click="removeReviewStep($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button @click="saveReviewDraft" :loading="loading.saveId === reviewForm.id">保存草稿</el-button>
        <el-button type="danger" @click="submitReviewReject" :loading="loading.actionId === reviewForm.id">驳回</el-button>
        <el-button type="primary" @click="submitReviewApprove" :loading="loading.actionId === reviewForm.id">
          通过并生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()

const actionOptions = [
  { label: '点击', value: 'click' },
  { label: '输入', value: 'fill' },
  { label: '获取文本', value: 'getText' },
  { label: '等待元素', value: 'waitFor' },
  { label: '悬停', value: 'hover' },
  { label: '滚动', value: 'scroll' },
  { label: '截图', value: 'screenshot' },
  { label: '断言', value: 'assert' },
  { label: '等待', value: 'wait' },
  { label: '进入iframe', value: 'enterIframe' },
  { label: '退出iframe', value: 'exitIframe' },
  { label: '切换标签页', value: 'switchTab' },
]

const assertOptions = [
  { label: '文本包含', value: 'textContains' },
  { label: '文本相等', value: 'textEquals' },
  { label: '元素可见', value: 'isVisible' },
  { label: '元素存在', value: 'exists' },
  { label: '属性存在', value: 'hasAttribute' },
]

const loading = reactive({
  page: false,
  actionId: null,
  saveId: null,
})

const stats = ref({
  total: 0,
  pending_review: 0,
  approved: 0,
  rejected: 0,
  warnings: 0,
  generated: 0,
})

const records = ref([])
const projects = ref([])
const uiProjects = ref([])
const reviewDialogVisible = ref(false)
const projectElementsCache = reactive({})

const filters = reactive({
  search: '',
  sourceProject: route.query.source_project || '',
  sourceTestcase: route.query.source_testcase || '',
  status: '',
  targetUiProject: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const reviewForm = reactive({
  id: null,
  sourceProjectId: null,
  sourceProjectName: '',
  targetUiProject: null,
  source_snapshot: {},
  name: '',
  description: '',
  preconditions: '',
  priority: 'medium',
  reviewComment: '',
  stepsData: [],
})

const reviewElementOptions = computed(() => projectElementsCache[reviewForm.targetUiProject] || [])
const normalizeProjectName = (value) => (value || '').trim().toLowerCase()
const reviewProjectOption = computed(() => {
  if (!reviewForm.sourceProjectName) return null
  const matchedUiProject = uiProjects.value.find(
    (item) => normalizeProjectName(item.name) === normalizeProjectName(reviewForm.sourceProjectName)
  )
  return {
    projectId: reviewForm.sourceProjectId,
    projectName: reviewForm.sourceProjectName,
    uiProjectId: matchedUiProject?.id || null,
    uiProjectName: matchedUiProject?.name || '',
    available: Boolean(matchedUiProject),
  }
})

const buildQueryParams = () => ({
  page: pagination.page,
  page_size: pagination.pageSize,
  search: filters.search || undefined,
  source_project: filters.sourceProject || undefined,
  source_testcase: filters.sourceTestcase || undefined,
  status: filters.status || undefined,
  target_ui_project: filters.targetUiProject || undefined,
})

const syncFiltersFromRoute = () => {
  filters.sourceProject = route.query.source_project || ''
  filters.sourceTestcase = route.query.source_testcase || ''
}

const fetchProjects = async () => {
  const response = await api.get('/projects/list/')
  projects.value = response.data?.results || response.data || []
}

const fetchUiProjects = async () => {
  const response = await api.get('/ui-automation/projects/', { params: { page_size: 1000 } })
  uiProjects.value = response.data?.results || response.data || []
}

const fetchStats = async () => {
  const response = await api.get('/executions/testcase_ui_automation_records/stats/', {
    params: buildQueryParams(),
  })
  stats.value = response.data || {}
}

const fetchRecords = async () => {
  loading.page = true
  try {
    const response = await api.get('/executions/testcase_ui_automation_records/', {
      params: buildQueryParams(),
    })
    records.value = response.data?.results || []
    pagination.total = response.data?.count || 0
  } catch (error) {
    ElMessage.error('获取 UI 自动化用例记录失败')
  } finally {
    loading.page = false
  }
}

const refreshPage = async () => {
  await Promise.all([fetchRecords(), fetchStats()])
}

const openRecordFromQuery = async () => {
  const recordId = Number(route.query.open_record || 0)
  if (!recordId) return

  let record = records.value.find((item) => item.id === recordId)
  if (!record) {
    try {
      const response = await api.get(`/executions/testcase_ui_automation_records/${recordId}/`)
      record = response.data
    } catch (error) {
      record = null
    }
  }

  if (record) {
    await openReviewDialog(record)
  }

  const nextQuery = { ...route.query }
  delete nextQuery.open_record
  router.replace({ path: route.path, query: nextQuery })
}

const handleSearch = async () => {
  pagination.page = 1
  await refreshPage()
}

const resetFilters = async () => {
  filters.search = ''
  filters.sourceProject = ''
  filters.sourceTestcase = ''
  filters.status = ''
  filters.targetUiProject = ''
  pagination.page = 1
  await refreshPage()
}

const handlePageChange = async (page) => {
  pagination.page = page
  await fetchRecords()
}

const handleSizeChange = async (size) => {
  pagination.pageSize = size
  pagination.page = 1
  await fetchRecords()
}

const ensureProjectElements = async (projectId) => {
  if (!projectId || projectElementsCache[projectId]) return
  const response = await api.get('/ui-automation/elements/', { params: { project: projectId, page_size: 1000 } })
  projectElementsCache[projectId] = response.data?.results || response.data || []
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getStatusType = (status) => ({
  draft: 'info',
  generating: 'warning',
  pending_review: 'warning',
  approved: 'success',
  rejected: 'danger',
  failed: 'danger',
}[status] || 'info')

const getStatusText = (status) => ({
  draft: '未生成',
  generating: '生成中',
  pending_review: '待审核',
  approved: '已审核',
  rejected: '已驳回',
  failed: '失败',
}[status] || status || '-')

const formatElementOption = (item) => item.page ? `${item.page} / ${item.name}` : item.name
const formatProjectOptionLabel = (item) => {
  if (!item) return ''
  return item.available ? item.projectName : `${item.projectName}（未匹配 UI 自动化项目）`
}

const syncElementName = (row, elementId) => {
  const element = reviewElementOptions.value.find((item) => item.id === elementId)
  row.element_name = element?.name || ''
}

const normalizeReviewSteps = () => {
  reviewForm.stepsData = JSON.parse(JSON.stringify(reviewForm.stepsData || []))
    .sort((a, b) => (a.step_number || 9999) - (b.step_number || 9999))
    .map((item, index) => ({
      step_number: index + 1,
      description: item.description || '',
      action_type: item.action_type || 'click',
      element_id: item.element_id || null,
      element_name: item.element_name || '',
      input_value: item.input_value || '',
      wait_time: Number(item.wait_time || 1000),
      assert_type: item.assert_type || '',
      assert_value: item.assert_value || '',
      match_type: item.match_type || '',
      match_score: Number(item.match_score || 0),
      match_reason: item.match_reason || '',
    }))
}

const createEmptyStep = () => ({
  step_number: reviewForm.stepsData.length + 1,
  description: '',
  action_type: 'click',
  element_id: null,
  element_name: '',
  input_value: '',
  wait_time: 1000,
  assert_type: '',
  assert_value: '',
  match_type: '',
  match_score: 0,
  match_reason: '',
})

const extractSourceSteps = (snapshot) => {
  const detailSteps = snapshot?.step_details || []
  if (detailSteps.length) {
    return detailSteps.map((item) => `${item.step_number}. ${item.action}${item.expected ? `；预期：${item.expected}` : ''}`)
  }
  const text = snapshot?.steps_text || ''
  return text
    ? text.split(/\r?\n+/).map((item) => item.trim()).filter(Boolean)
    : ['-']
}

const buildReviewPayload = () => {
  normalizeReviewSteps()
  return {
    target_ui_project: reviewForm.targetUiProject,
    name: reviewForm.name,
    description: reviewForm.description,
    preconditions: reviewForm.preconditions,
    priority: reviewForm.priority,
    review_comment: reviewForm.reviewComment,
    steps_data: reviewForm.stepsData,
  }
}

const openReviewDialog = async (record) => {
  reviewForm.id = record.id
  reviewForm.sourceProjectId = record.source_project_id || null
  reviewForm.sourceProjectName = record.source_project_name || ''
  const matchedUiProject = uiProjects.value.find(
    (item) => normalizeProjectName(item.name) === normalizeProjectName(reviewForm.sourceProjectName)
  )
  reviewForm.targetUiProject = matchedUiProject?.id || record.target_ui_project || null
  reviewForm.source_snapshot = JSON.parse(JSON.stringify(record.source_snapshot || {}))
  reviewForm.name = record.name || ''
  reviewForm.description = record.description || ''
  reviewForm.preconditions = record.preconditions || ''
  reviewForm.priority = record.priority || 'medium'
  reviewForm.reviewComment = record.review_comment || ''
  reviewForm.stepsData = (record.steps_data || []).length ? JSON.parse(JSON.stringify(record.steps_data)) : [createEmptyStep()]
  normalizeReviewSteps()
  await ensureProjectElements(reviewForm.targetUiProject)
  reviewDialogVisible.value = true
}

const addReviewStep = () => {
  reviewForm.stepsData.push(createEmptyStep())
  normalizeReviewSteps()
}

const removeReviewStep = (index) => {
  reviewForm.stepsData.splice(index, 1)
  if (!reviewForm.stepsData.length) {
    reviewForm.stepsData.push(createEmptyStep())
  }
  normalizeReviewSteps()
}

const saveReviewDraft = async () => {
  if (!reviewForm.id) return
  loading.saveId = reviewForm.id
  try {
    await api.patch(`/executions/testcase_ui_automation_records/${reviewForm.id}/`, buildReviewPayload())
    ElMessage.success('审核草稿已保存')
    await refreshPage()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || error.response?.data?.target_ui_project?.[0] || '保存审核草稿失败')
  } finally {
    loading.saveId = null
  }
}

const quickApprove = async (record) => {
  loading.actionId = record.id
  try {
    await api.post(`/executions/testcase_ui_automation_records/${record.id}/approve/`, {})
    ElMessage.success('候选用例已审核通过')
    await refreshPage()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '审核通过失败')
  } finally {
    loading.actionId = null
  }
}

const quickReject = async (record) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回说明（可选）', '驳回候选用例', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：元素映射不准确，需要重新调整步骤',
    })
    loading.actionId = record.id
    await api.post(`/executions/testcase_ui_automation_records/${record.id}/reject/`, {
      review_comment: value || '',
    })
    ElMessage.success('候选用例已驳回')
    await refreshPage()
  } catch (error) {
    if (!['cancel', 'close'].includes(error)) {
      ElMessage.error(error.response?.data?.error || '驳回候选用例失败')
    }
  } finally {
    loading.actionId = null
  }
}

const submitReviewApprove = async () => {
  if (!reviewForm.id) return
  if (!reviewForm.targetUiProject) {
    ElMessage.warning('当前 AI 项目未匹配到同名 UI 自动化项目，暂不可审核落地')
    return
  }
  loading.actionId = reviewForm.id
  try {
    await api.post(`/executions/testcase_ui_automation_records/${reviewForm.id}/approve/`, buildReviewPayload())
    ElMessage.success('候选用例已审核通过并落地为 UI 自动化用例')
    reviewDialogVisible.value = false
    await refreshPage()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || error.response?.data?.target_ui_project?.[0] || '审核通过失败')
  } finally {
    loading.actionId = null
  }
}

const submitReviewReject = async () => {
  if (!reviewForm.id) return
  loading.actionId = reviewForm.id
  try {
    await api.post(`/executions/testcase_ui_automation_records/${reviewForm.id}/reject/`, {
      review_comment: reviewForm.reviewComment,
    })
    ElMessage.success('候选用例已驳回')
    reviewDialogVisible.value = false
    await refreshPage()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '驳回候选用例失败')
  } finally {
    loading.actionId = null
  }
}

const goToSourceTestCase = (testcaseId) => {
  router.push(`/ai-generation/testcases/${testcaseId}`)
}

onMounted(async () => {
  syncFiltersFromRoute()
  await Promise.all([fetchProjects(), fetchUiProjects(), refreshPage()])
  await openRecordFromQuery()
})

watch(
  () => [route.query.source_project, route.query.source_testcase],
  async () => {
    syncFiltersFromRoute()
    pagination.page = 1
    await refreshPage()
  }
)
</script>

<style scoped>
.ui-automation-cases-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 28px 32px;
  border-radius: 18px;
  margin-bottom: 24px;
  color: #fff;
  background: linear-gradient(135deg, #0f766e, #1d4ed8);
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

.form-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.form-tip.warning {
  color: #b45309;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #0f172a;
  background: #fff;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.stat-card span {
  font-size: 13px;
  color: #64748b;
}

.stat-card strong {
  font-size: 28px;
  line-height: 1;
}

.total { border-top: 4px solid #1d4ed8; }
.pending { border-top: 4px solid #f59e0b; }
.approved { border-top: 4px solid #16a34a; }
.rejected { border-top: 4px solid #dc2626; }
.warning { border-top: 4px solid #d97706; }
.generated { border-top: 4px solid #0f766e; }

.card-container {
  background: #fff;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.filter-bar {
  margin-bottom: 18px;
}

.filter-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.record-table {
  margin-top: 4px;
}

.row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.review-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.review-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 18px;
}

.review-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px;
  background: #fcfcfd;
}

.review-card h4,
.steps-toolbar h4 {
  margin: 0 0 14px;
  color: #0f172a;
}

.review-field {
  margin-bottom: 12px;
}

.review-field > span {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.review-field p {
  margin: 0;
  color: #334155;
  line-height: 1.6;
  white-space: pre-wrap;
}

.source-steps {
  margin: 0;
  padding-left: 20px;
  color: #334155;
}

.steps-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.steps-toolbar p {
  margin: 6px 0 0;
  color: #64748b;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .review-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .ui-automation-cases-page {
    padding: 16px;
  }

  .page-header-card,
  .steps-toolbar {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-actions {
    justify-content: flex-start;
    margin-top: 8px;
  }
}
</style>
