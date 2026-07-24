<template>
  <div class="execution-detail">
    <div class="page-header-card">
      <div class="header-content">
        <div>
          <h1 class="page-title">{{ testPlan.name || '测试计划详情' }}</h1>
          <p class="page-subtitle">{{ testPlan.description || '查看手工执行情况，并将中文描述性用例桥接为 UI 自动化执行。' }}</p>
        </div>
        <div class="header-meta">
          <el-tag v-if="testPlan.version" type="primary" effect="dark">
            <el-icon><Stamp /></el-icon>
            <span>{{ testPlan.version }}</span>
          </el-tag>
          <span class="meta-item">
            <el-icon><FolderOpened /></el-icon>
            {{ (testPlan.projects || []).join('、') || '未关联项目' }}
          </span>
        </div>
      </div>
    </div>

    <el-empty
      v-if="!(testPlan.test_runs || []).length"
      description="当前测试计划还没有执行数据。"
      class="empty-state"
    />

    <div v-for="run in testPlan.test_runs || []" :key="run.id" class="test-run-card">
      <div class="run-top">
        <div>
          <div class="run-title-row">
            <h2 class="run-title">{{ run.name }}</h2>
            <el-tag :type="getRunStatusType(run.progress)">{{ getRunStatusText(run.progress) }}</el-tag>
          </div>
          <div class="run-meta">
            <span>{{ run.project_name || '-' }}</span>
            <span>执行人：{{ run.assignee_name || '-' }}</span>
          </div>
        </div>

        <div v-if="false" class="run-actions">
          <el-button
            type="primary"
            @click="openGenerateDialog(run)"
            :loading="loading.generateRunId === run.id"
          >
            生成UI自动化用例
          </el-button>
          <el-button
            type="success"
            @click="executeUiAutomation(run)"
            :disabled="!canExecuteBatch(run)"
            :loading="loading.executeRunId === run.id"
          >
            执行已审核用例
          </el-button>
        </div>
      </div>

      <div class="stats-cards">
        <div class="stat-card total">
          <span class="stat-label">总数</span>
          <strong>{{ run.progress.total }}</strong>
        </div>
        <div class="stat-card passed">
          <span class="stat-label">通过</span>
          <strong>{{ run.progress.passed }}</strong>
        </div>
        <div class="stat-card failed">
          <span class="stat-label">失败</span>
          <strong>{{ run.progress.failed }}</strong>
        </div>
        <div class="stat-card blocked">
          <span class="stat-label">阻塞</span>
          <strong>{{ run.progress.blocked }}</strong>
        </div>
        <div class="stat-card untested">
          <span class="stat-label">未测</span>
          <strong>{{ run.progress.untested }}</strong>
        </div>
      </div>

      <el-progress
        class="run-progress"
        :percentage="run.progress.progress"
        :stroke-width="12"
        :color="getProgressColor(run.progress.progress)"
      />

      <section v-if="false" class="bridge-panel">
        <div class="section-header">
          <div>
            <h3>UI 自动化桥接</h3>
            <p>先生成候选用例，再审核通过后复用现有 Playwright / Selenium 执行链路。</p>
          </div>
          <el-tag v-if="run.ui_automation_batch" :type="getBatchStatusType(run.ui_automation_batch.status)">
            {{ getBatchStatusText(run.ui_automation_batch.status) }}
          </el-tag>
        </div>

        <el-empty
          v-if="!run.ui_automation_batch"
          description="还没有生成 UI 自动化候选用例。"
        />

        <template v-else>
          <div class="batch-summary">
            <div class="summary-item">
              <span>目标 UI 项目</span>
              <strong>{{ run.ui_automation_batch.target_ui_project_name || '-' }}</strong>
            </div>
            <div class="summary-item">
              <span>执行引擎</span>
              <strong>{{ run.ui_automation_batch.engine }}</strong>
            </div>
            <div class="summary-item">
              <span>候选总数</span>
              <strong>{{ run.ui_automation_batch.counts.total }}</strong>
            </div>
            <div class="summary-item">
              <span>已审核</span>
              <strong>{{ run.ui_automation_batch.counts.approved }}</strong>
            </div>
            <div class="summary-item">
              <span>待审核</span>
              <strong>{{ run.ui_automation_batch.counts.pending }}</strong>
            </div>
            <div class="summary-item">
              <span>最近执行</span>
              <strong>{{ getExecutionStatusText(run.ui_automation_batch.last_execution_status) }}</strong>
            </div>
          </div>

          <el-alert
            v-if="run.ui_automation_batch.counts.warnings > 0"
            type="warning"
            :closable="false"
            show-icon
            class="batch-alert"
            title="部分候选用例未能完整通过 AI 生成，已回退为规则生成，审核时请重点确认元素映射与步骤动作。"
          />

          <el-table
            :data="run.ui_automation_batch.candidates || []"
            border
            class="candidate-table"
            empty-text="暂无候选用例"
          >
            <el-table-column prop="source_testcase_title" label="来源手工用例" min-width="220" show-overflow-tooltip />
            <el-table-column prop="name" label="候选UI用例" min-width="220" show-overflow-tooltip />
            <el-table-column label="生成方式" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.generation_source === 'ai' ? 'success' : 'warning'">
                  {{ row.generation_source === 'ai' ? 'AI' : '规则' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="getCandidateStatusType(row.review_status)">
                  {{ getCandidateStatusText(row.review_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="step_count" label="步骤数" width="90" />
            <el-table-column prop="generated_test_case_name" label="已落地UI用例" min-width="180" show-overflow-tooltip />
            <el-table-column prop="generation_error" label="生成告警" min-width="220" show-overflow-tooltip />
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button link type="primary" @click="openReviewDialog(run, row)">审核</el-button>
                  <el-button link type="success" @click="quickApprove(row)">快速通过</el-button>
                  <el-button link type="danger" @click="quickReject(row)">驳回</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </section>

      <section class="bridge-panel">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="【生成UI自动化用例】能力已迁移到【测试用例】页面；生成后的记录、审核和统计请前往【UI自动化用例】菜单页查看。"
        />
      </section>

      <section class="manual-panel">
        <div class="section-header compact">
          <div>
            <h3>手工执行用例</h3>
            <p>保留原有状态更新、备注编辑和执行历史查看能力。</p>
          </div>
          <el-button
            v-if="getSelectedCases(run.id).length > 0"
            type="danger"
            @click="batchDeleteCases(run)"
            :loading="loading.deleteRunId === run.id"
          >
            批量删除 {{ getSelectedCases(run.id).length }}
          </el-button>
        </div>

        <el-table
          :ref="(el) => setTableRef(run.id, el)"
          :data="paginatedCases(run)"
          border
          row-key="id"
          @selection-change="(selection) => handleSelectionChange(run.id, selection)"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column type="index" label="#" width="60" :index="(index) => getSerialNumber(run.id, index)" />
          <el-table-column prop="testcase" label="测试用例" min-width="240" show-overflow-tooltip />
          <el-table-column label="执行状态" width="140">
            <template #default="{ row }">
              <el-select v-model="row.status" size="small" @change="updateCaseStatus(row)">
                <el-option label="未测试" value="untested" />
                <el-option label="通过" value="passed" />
                <el-option label="失败" value="failed" />
                <el-option label="阻塞" value="blocked" />
                <el-option label="重测" value="retest" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="260">
            <template #default="{ row }">
              <el-input
                v-model="row.comments"
                type="textarea"
                :rows="2"
                resize="none"
                placeholder="填写执行备注"
                @blur="updateCaseDetails(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewCaseHistory(row)">历史</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="(run.run_cases || []).length > 0" class="pagination-container">
          <el-pagination
            :current-page="getPagination(run.id).currentPage"
            :page-size="getPagination(run.id).pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="(run.run_cases || []).length"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="(page) => handlePageChange(run.id, page)"
            @size-change="(size) => handleSizeChange(run.id, size)"
          />
        </div>
      </section>
    </div>

    <el-dialog v-model="historyDialogVisible" title="执行历史" width="760px">
      <el-table :data="currentCaseHistory" border>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comments" label="备注" min-width="220" show-overflow-tooltip />
        <el-table-column prop="executed_by.username" label="执行者" width="120" />
        <el-table-column prop="executed_at" label="执行时间" width="180">
          <template #default="{ row }">{{ formatDate(row.executed_at) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="generateDialogVisible" title="生成 UI 自动化候选用例" width="520px">
      <el-form label-width="110px">
        <el-form-item label="目标 UI 项目">
          <el-select v-model="generateForm.targetUiProject" filterable placeholder="请选择目标 UI 项目" style="width: 100%">
            <el-option
              v-for="item in targetUiProjectOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
              :disabled="item.disabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行引擎">
          <el-alert
            v-if="missingTargetUiProjectCount > 0"
            type="warning"
            :closable="false"
            show-icon
            title="目标 UI 项目按【AI研发平台】模块的项目列表展示；若某个项目不可选，表示当前还没有同名的 UI 自动化项目，请先创建对应 UI 项目。"
          />
          <el-select v-model="generateForm.engine" style="width: 100%">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Selenium" value="selenium" />
          </el-select>
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="生成时会优先调用已启用的编写模型；若模型未配置或返回异常，会自动回退为规则生成。"
        />
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitGenerateDialog" :loading="loading.generateRunId === generateForm.runId">
          开始生成
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="审核 UI 自动化候选用例" width="92%" top="4vh" destroy-on-close>
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
                <li v-for="(item, index) in extractSourceSteps(reviewForm.source_snapshot)" :key="`${index}-${item}`">{{ item }}</li>
              </ol>
            </div>
            <div class="review-field"><span>预期结果</span><p>{{ reviewForm.source_snapshot.expected_result || '-' }}</p></div>
          </div>

          <div class="review-card">
            <h4>候选用例信息</h4>
            <el-form label-width="100px">
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
                <el-input v-model="reviewForm.review_comment" type="textarea" :rows="4" />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="steps-toolbar">
          <div>
            <h4>步骤审核与元素映射</h4>
            <p>可直接修正动作、元素、断言和值，审核通过后会落地为真实 UI 自动化用例。</p>
          </div>
          <el-button type="primary" plain @click="addReviewStep">新增步骤</el-button>
        </div>

        <el-table :data="reviewForm.steps_data" border max-height="420">
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
          <el-table-column label="动作" width="150">
            <template #default="{ row }">
              <el-select v-model="row.action_type">
                <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="元素" min-width="220">
            <template #default="{ row }">
              <el-select v-model="row.element_id" filterable clearable placeholder="选择元素" @change="(value) => syncElementName(row, value)">
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
        <el-button @click="saveReviewDraft" :loading="loading.saveCandidateId === reviewForm.id">保存草稿</el-button>
        <el-button type="danger" @click="submitReviewReject" :loading="loading.candidateActionId === reviewForm.id">驳回</el-button>
        <el-button type="primary" @click="submitReviewApprove" :loading="loading.candidateActionId === reviewForm.id">通过并生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderOpened, Stamp } from '@element-plus/icons-vue'
import api from '@/utils/api'

const route = useRoute()

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
  { label: '切换标签页', value: 'switchTab' }
]

const assertOptions = [
  { label: '文本包含', value: 'textContains' },
  { label: '文本相等', value: 'textEquals' },
  { label: '元素可见', value: 'isVisible' },
  { label: '元素存在', value: 'exists' },
  { label: '属性存在', value: 'hasAttribute' }
]

const testPlan = ref({})
const uiProjects = ref([])
const sourceProjects = ref([])
const historyDialogVisible = ref(false)
const currentCaseHistory = ref([])
const generateDialogVisible = ref(false)
const reviewDialogVisible = ref(false)

const generateForm = reactive({
  runId: null,
  targetUiProject: null,
  engine: 'playwright'
})

const reviewForm = reactive({
  id: null,
  runId: null,
  targetUiProject: null,
  source_snapshot: {},
  name: '',
  description: '',
  preconditions: '',
  priority: 'medium',
  review_comment: '',
  steps_data: []
})

const loading = reactive({
  page: false,
  generateRunId: null,
  executeRunId: null,
  deleteRunId: null,
  saveCandidateId: null,
  candidateActionId: null
})

const selectionState = reactive({})
const paginationState = reactive({})
const projectElementsCache = reactive({})
const tableRefs = new Map()

const reviewElementOptions = computed(() => projectElementsCache[reviewForm.targetUiProject] || [])
const missingTargetUiProjectCount = computed(() => targetUiProjectOptions.value.filter((item) => item.disabled).length)

const normalizeName = (value) => String(value || '').toLowerCase().replace(/[\s\-_:/\\|,.，。！？!?'"]/g, '')

const normalizeListResponse = (response) => {
  if (Array.isArray(response?.data)) return response.data
  if (Array.isArray(response?.data?.results)) return response.data.results
  return []
}

const deepClone = (value) => JSON.parse(JSON.stringify(value ?? null))

const getPagination = (runId) => {
  if (!paginationState[runId]) {
    paginationState[runId] = { currentPage: 1, pageSize: 10 }
  }
  return paginationState[runId]
}

const getSelectedCases = (runId) => selectionState[runId] || []

const setTableRef = (runId, el) => {
  if (el) tableRefs.set(runId, el)
}

const fetchUiProjects = async () => {
  const response = await api.get('/ui-automation/projects/', { params: { page_size: 1000 } })
  uiProjects.value = normalizeListResponse(response)
}

const fetchSourceProjects = async () => {
  const response = await api.get('/projects/list/')
  sourceProjects.value = normalizeListResponse(response)
}

const findUiProjectByName = (name) => {
  const currentName = normalizeName(name)
  if (!currentName) return null
  return uiProjects.value.find((item) => normalizeName(item.name) === currentName)
    || uiProjects.value.find((item) => normalizeName(item.name).includes(currentName) || currentName.includes(normalizeName(item.name)))
    || null
}

const targetUiProjectOptions = computed(() => {
  const options = []
  const usedUiProjectIds = new Set()

  sourceProjects.value.forEach((project) => {
    const matchedUiProject = findUiProjectByName(project.name)
    if (matchedUiProject?.id) {
      usedUiProjectIds.add(matchedUiProject.id)
    }
    options.push({
      value: matchedUiProject?.id ?? `missing-${project.id}`,
      label: matchedUiProject ? project.name : `${project.name}（未创建同名 UI 项目）`,
      disabled: !matchedUiProject
    })
  })

  if (generateForm.targetUiProject && !usedUiProjectIds.has(generateForm.targetUiProject)) {
    const currentUiProject = uiProjects.value.find((item) => item.id === generateForm.targetUiProject)
    if (currentUiProject) {
      options.unshift({
        value: currentUiProject.id,
        label: `${currentUiProject.name}（仅 UI 自动化项目）`,
        disabled: false
      })
    }
  }

  return options
})

const fetchTestPlan = async () => {
  const planId = route.params.id
  const response = await api.get(`/executions/plans/${planId}/`)
  testPlan.value = response.data || {}
  ;(testPlan.value.test_runs || []).forEach((run) => getPagination(run.id))
}

const ensureProjectElements = async (projectId) => {
  if (!projectId || projectElementsCache[projectId]) return
  const response = await api.get('/ui-automation/elements/', { params: { project: projectId, page_size: 1000 } })
  projectElementsCache[projectId] = normalizeListResponse(response)
}

const guessUiProject = (run) => findUiProjectByName(run?.project_name)

const paginatedCases = (run) => {
  const { currentPage, pageSize } = getPagination(run.id)
  const start = (currentPage - 1) * pageSize
  return (run.run_cases || []).slice(start, start + pageSize)
}

const getSerialNumber = (runId, index) => {
  const { currentPage, pageSize } = getPagination(runId)
  return (currentPage - 1) * pageSize + index + 1
}

const handleSelectionChange = (runId, selection) => {
  selectionState[runId] = selection
}

const handlePageChange = (runId, page) => {
  getPagination(runId).currentPage = page
  selectionState[runId] = []
  tableRefs.get(runId)?.clearSelection?.()
}

const handleSizeChange = (runId, size) => {
  getPagination(runId).pageSize = size
  getPagination(runId).currentPage = 1
  selectionState[runId] = []
  tableRefs.get(runId)?.clearSelection?.()
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getProgressColor = (percentage) => {
  if (percentage < 30) return '#f56c6c'
  if (percentage < 70) return '#e6a23c'
  return '#67c23a'
}

const getRunStatusType = (progress) => {
  if ((progress?.progress || 0) === 100) return 'success'
  if ((progress?.failed || 0) > 0) return 'danger'
  if ((progress?.blocked || 0) > 0) return 'warning'
  return 'info'
}

const getRunStatusText = (progress) => {
  if ((progress?.progress || 0) === 100) return '已完成'
  if ((progress?.untested || 0) === (progress?.total || 0)) return '未开始'
  return '进行中'
}

const getStatusType = (status) => ({
  untested: 'info',
  passed: 'success',
  failed: 'danger',
  blocked: 'warning',
  retest: 'primary'
}[status] || 'info')

const getStatusText = (status) => ({
  untested: '未测试',
  passed: '通过',
  failed: '失败',
  blocked: '阻塞',
  retest: '重测'
}[status] || status)

const getBatchStatusType = (status) => ({
  draft: 'info',
  generating: 'warning',
  pending_review: 'warning',
  partially_approved: 'primary',
  approved: 'success',
  running: 'primary',
  completed: 'success',
  failed: 'danger'
}[status] || 'info')

const getBatchStatusText = (status) => ({
  draft: '未生成',
  generating: '生成中',
  pending_review: '待审核',
  partially_approved: '部分已审核',
  approved: '已审核',
  running: '执行中',
  completed: '已完成',
  failed: '失败'
}[status] || status || '-')

const getCandidateStatusType = (status) => ({
  pending: 'warning',
  approved: 'success',
  rejected: 'danger'
}[status] || 'info')

const getCandidateStatusText = (status) => ({
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}[status] || status)

const getExecutionStatusText = (status) => ({
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  ABORTED: '已中止',
  PENDING: '待执行'
}[status] || '-')

const canExecuteBatch = (run) => Number(run?.ui_automation_batch?.counts?.approved || 0) > 0

const updateCaseStatus = async (runCase) => {
  await api.patch(`/executions/run_cases/${runCase.id}/update_status/`, {
    status: runCase.status,
    comments: runCase.comments || ''
  })
  ElMessage.success('执行状态已更新')
  await fetchTestPlan()
}

const updateCaseDetails = async (runCase) => {
  await api.patch(`/executions/run_cases/${runCase.id}/update_status/`, {
    status: runCase.status,
    comments: runCase.comments || ''
  })
  ElMessage.success('备注已保存')
}

const viewCaseHistory = async (runCase) => {
  const response = await api.get(`/executions/run_cases/${runCase.id}/history/`)
  currentCaseHistory.value = response.data || []
  historyDialogVisible.value = true
}

const batchDeleteCases = async (run) => {
  const selected = getSelectedCases(run.id)
  if (!selected.length) return
  try {
    await ElMessageBox.confirm(`确认删除已选中的 ${selected.length} 条执行用例吗？`, '批量删除', { type: 'warning' })
    loading.deleteRunId = run.id
    for (const item of selected) {
      await api.delete(`/executions/run_cases/${item.id}/`)
    }
    selectionState[run.id] = []
    ElMessage.success('批量删除完成')
    await fetchTestPlan()
  } catch (error) {
    if (!['cancel', 'close'].includes(error)) throw error
  } finally {
    loading.deleteRunId = null
  }
}

const openGenerateDialog = (run) => {
  generateForm.runId = run.id
  generateForm.engine = run.ui_automation_batch?.engine || 'playwright'
  generateForm.targetUiProject = run.ui_automation_batch?.target_ui_project || guessUiProject(run)?.id || null
  generateDialogVisible.value = true
}

const submitGenerateDialog = async () => {
  if (!generateForm.runId) return
  if (!generateForm.targetUiProject) {
    ElMessage.warning('请先选择目标 UI 项目')
    return
  }

  loading.generateRunId = generateForm.runId
  try {
    await api.post(
      `/executions/runs/${generateForm.runId}/generate_ui_automation/`,
      {
        target_ui_project: generateForm.targetUiProject,
        engine: generateForm.engine
      },
      { timeout: 300000 }
    )
    ElMessage.success('候选用例生成完成')
    generateDialogVisible.value = false
    await fetchTestPlan()
  } finally {
    loading.generateRunId = null
  }
}

const executeUiAutomation = async (run) => {
  if (!canExecuteBatch(run)) return
  try {
    await ElMessageBox.confirm(
      `将执行 ${run.ui_automation_batch.counts.approved} 条已审核通过的 UI 自动化用例，是否继续？`,
      '执行确认',
      { type: 'warning' }
    )
    loading.executeRunId = run.id
    const response = await api.post(`/executions/runs/${run.id}/execute_ui_automation/`, {
      browser: 'chrome',
      headless: true
    })
    ElMessage.success(response.data?.message || '已开始执行')
    await fetchTestPlan()
  } catch (error) {
    if (!['cancel', 'close'].includes(error)) throw error
  } finally {
    loading.executeRunId = null
  }
}

const formatElementOption = (item) => item.page ? `${item.page} / ${item.name}` : item.name

const syncElementName = (row, elementId) => {
  const element = reviewElementOptions.value.find((item) => item.id === elementId)
  row.element_name = element?.name || ''
}

const normalizeReviewSteps = () => {
  reviewForm.steps_data = deepClone(reviewForm.steps_data)
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
      match_reason: item.match_reason || ''
    }))
}

const createEmptyStep = () => ({
  step_number: reviewForm.steps_data.length + 1,
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
  match_reason: ''
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

const openReviewDialog = async (run, candidate) => {
  await ensureProjectElements(run.ui_automation_batch?.target_ui_project)
  reviewForm.id = candidate.id
  reviewForm.runId = run.id
  reviewForm.targetUiProject = run.ui_automation_batch?.target_ui_project || null
  reviewForm.source_snapshot = deepClone(candidate.source_snapshot || {})
  reviewForm.name = candidate.name || ''
  reviewForm.description = candidate.description || ''
  reviewForm.preconditions = candidate.preconditions || ''
  reviewForm.priority = candidate.priority || 'medium'
  reviewForm.review_comment = candidate.review_comment || ''
  reviewForm.steps_data = deepClone(candidate.steps_data || []).length ? deepClone(candidate.steps_data) : [createEmptyStep()]
  normalizeReviewSteps()
  reviewDialogVisible.value = true
}

const addReviewStep = () => {
  reviewForm.steps_data.push(createEmptyStep())
  normalizeReviewSteps()
}

const removeReviewStep = (index) => {
  reviewForm.steps_data.splice(index, 1)
  if (!reviewForm.steps_data.length) {
    reviewForm.steps_data.push(createEmptyStep())
  }
  normalizeReviewSteps()
}

const buildReviewPayload = () => {
  normalizeReviewSteps()
  return {
    name: reviewForm.name,
    description: reviewForm.description,
    preconditions: reviewForm.preconditions,
    priority: reviewForm.priority,
    review_comment: reviewForm.review_comment,
    steps_data: reviewForm.steps_data
  }
}

const saveReviewDraft = async () => {
  if (!reviewForm.id) return
  loading.saveCandidateId = reviewForm.id
  try {
    await api.patch(`/executions/ui_automation_candidates/${reviewForm.id}/`, buildReviewPayload())
    ElMessage.success('候选用例草稿已保存')
    await fetchTestPlan()
  } finally {
    loading.saveCandidateId = null
  }
}

const quickApprove = async (candidate) => {
  loading.candidateActionId = candidate.id
  try {
    await api.post(`/executions/ui_automation_candidates/${candidate.id}/approve/`, {})
    ElMessage.success('候选用例已审核通过')
    await fetchTestPlan()
  } finally {
    loading.candidateActionId = null
  }
}

const quickReject = async (candidate) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回说明（可选）', '驳回候选用例', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：元素映射不准确，需要重新调整步骤'
    })
    loading.candidateActionId = candidate.id
    await api.post(`/executions/ui_automation_candidates/${candidate.id}/reject/`, { review_comment: value || '' })
    ElMessage.success('候选用例已驳回')
    await fetchTestPlan()
  } catch (error) {
    if (!['cancel', 'close'].includes(error)) throw error
  } finally {
    loading.candidateActionId = null
  }
}

const submitReviewApprove = async () => {
  if (!reviewForm.id) return
  loading.candidateActionId = reviewForm.id
  try {
    await api.post(`/executions/ui_automation_candidates/${reviewForm.id}/approve/`, buildReviewPayload())
    ElMessage.success('候选用例已审核通过并落地为 UI 自动化用例')
    reviewDialogVisible.value = false
    await fetchTestPlan()
  } finally {
    loading.candidateActionId = null
  }
}

const submitReviewReject = async () => {
  if (!reviewForm.id) return
  loading.candidateActionId = reviewForm.id
  try {
    await api.post(`/executions/ui_automation_candidates/${reviewForm.id}/reject/`, {
      review_comment: reviewForm.review_comment
    })
    ElMessage.success('候选用例已驳回')
    reviewDialogVisible.value = false
    await fetchTestPlan()
  } finally {
    loading.candidateActionId = null
  }
}

onMounted(async () => {
  loading.page = true
  try {
    await Promise.all([fetchTestPlan(), fetchUiProjects(), fetchSourceProjects()])
  } catch (error) {
    ElMessage.error('加载测试计划详情失败')
  } finally {
    loading.page = false
  }
})
</script>

<style scoped>
.execution-detail { padding: 24px; background: #f5f7fa; min-height: 100vh; }
.page-header-card { background: linear-gradient(135deg, #1d4ed8, #0f766e); border-radius: 18px; padding: 28px 32px; color: #fff; margin-bottom: 24px; }
.header-content { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }
.page-title { margin: 0 0 8px; font-size: 30px; font-weight: 700; }
.page-subtitle { margin: 0; opacity: .88; line-height: 1.6; max-width: 720px; }
.header-meta { display: flex; flex-direction: column; gap: 12px; align-items: flex-end; }
.meta-item { display: inline-flex; align-items: center; gap: 6px; opacity: .92; }
.empty-state { background: #fff; border-radius: 16px; padding: 24px; }
.test-run-card { background: #fff; border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: 0 8px 28px rgba(15, 23, 42, .06); }
.run-top { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 20px; }
.run-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.run-title { margin: 0; font-size: 22px; color: #0f172a; }
.run-meta { display: flex; gap: 16px; color: #64748b; font-size: 14px; flex-wrap: wrap; }
.run-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.stats-cards { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.stat-card { border-radius: 14px; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.stat-card strong { font-size: 26px; line-height: 1; }
.stat-label { font-size: 13px; opacity: .88; }
.total { background: #dbeafe; color: #1d4ed8; }
.passed { background: #dcfce7; color: #15803d; }
.failed { background: #fee2e2; color: #dc2626; }
.blocked { background: #fef3c7; color: #b45309; }
.untested { background: #e2e8f0; color: #475569; }
.run-progress { margin-bottom: 24px; }
.bridge-panel, .manual-panel { border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; margin-top: 20px; }
.section-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
.section-header h3 { margin: 0 0 6px; font-size: 18px; color: #0f172a; }
.section-header p { margin: 0; color: #64748b; line-height: 1.5; }
.compact { align-items: center; }
.batch-summary { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.summary-item { background: #f8fafc; border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.summary-item span { font-size: 12px; color: #64748b; }
.summary-item strong { color: #0f172a; }
.batch-alert { margin-bottom: 16px; }
.row-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.candidate-table { margin-top: 4px; }
.pagination-container { display: flex; justify-content: center; margin-top: 18px; }
.review-layout { display: flex; flex-direction: column; gap: 18px; }
.review-grid { display: grid; grid-template-columns: 1.1fr .9fr; gap: 18px; }
.review-card { border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; background: #fcfcfd; }
.review-card h4, .steps-toolbar h4 { margin: 0 0 14px; color: #0f172a; }
.review-field { margin-bottom: 12px; }
.review-field > span { display: block; font-size: 12px; color: #64748b; margin-bottom: 6px; }
.review-field p { margin: 0; color: #334155; line-height: 1.6; white-space: pre-wrap; }
.source-steps { margin: 0; padding-left: 20px; color: #334155; }
.steps-toolbar { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.steps-toolbar p { margin: 6px 0 0; color: #64748b; }

@media (max-width: 1200px) {
  .stats-cards, .batch-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .review-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .execution-detail { padding: 16px; }
  .header-content, .run-top, .section-header, .steps-toolbar { flex-direction: column; }
  .header-meta { align-items: flex-start; }
  .stats-cards, .batch-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
