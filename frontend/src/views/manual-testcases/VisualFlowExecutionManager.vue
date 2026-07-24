<template>
  <div class="visual-flow-execution-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="visual-flow-executions"
      directory-title="执行结果页面目录"
      body-class="execution-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >
      <main class="execution-main-panel">
        <section class="execution-toolbar">
          <div class="toolbar-filters">
            <el-input
              v-model="query.search"
              clearable
              placeholder="搜索流程名称 / 执行ID"
              style="width: 260px"
              @keyup.enter="loadExecutions"
            />
            <el-select v-model="query.status" clearable placeholder="状态" style="width: 140px">
              <el-option label="执行中" value="running" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="已中止" value="aborted" />
            </el-select>
            <el-select v-model="query.run_type" clearable placeholder="类型" style="width: 140px">
              <el-option label="后台回放" value="backend" />
              <el-option label="本地回放" value="local" />
            </el-select>
            <el-button type="primary" @click="loadExecutions">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </div>
          <el-button :loading="loading" @click="loadExecutions">刷新</el-button>
        </section>

        <section class="execution-list">
          <el-table :data="executions" v-loading="loading" height="100%">
            <el-table-column prop="execution_id" label="执行ID" min-width="220" show-overflow-tooltip />
            <el-table-column prop="flow_name" label="流程名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="run_type" label="类型" width="110">
              <template #default="{ row }">{{ row.run_type === 'local' ? '本地回放' : '后台回放' }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="步骤" width="150">
              <template #default="{ row }">
                {{ row.success_count || 0 }}/{{ row.step_count || 0 }}
                <span v-if="row.failed_count" class="failed-count">失败 {{ row.failed_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_by_name" label="执行人" width="120" />
            <el-table-column prop="started_at" label="开始时间" width="180">
              <template #default="{ row }">{{ formatTime(row.started_at || row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="100">
              <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="loadExecutions"
            @current-change="loadExecutions"
          />
        </div>
      </main>
    </ManualWorkspaceRecordingShell>

    <el-dialog v-model="detailVisible" title="测试结果" width="980px">
      <div v-if="currentExecution" class="execution-detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="流程">{{ currentExecution.flow_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentExecution.run_type === 'local' ? '本地回放' : '后台回放' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(currentExecution.status)">{{ getStatusText(currentExecution.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(currentExecution.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(currentExecution.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ formatDuration(currentExecution.duration) }}</el-descriptions-item>
        </el-descriptions>

        <el-table class="step-table" :data="currentExecution.steps || []" max-height="460">
          <el-table-column prop="step_order" label="#" width="70" />
          <el-table-column prop="title" label="节点/组件" min-width="180" show-overflow-tooltip />
          <el-table-column prop="item_type" label="类型" width="90">
            <template #default="{ row }">{{ row.item_type === 'component' ? '组件' : '节点' }}</template>
          </el-table-column>
          <el-table-column prop="status" label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="输入/输出" min-width="260">
            <template #default="{ row }">
              <el-collapse class="inline-collapse">
                <el-collapse-item title="执行信息">
                  <pre class="payload-pre">输入：{{ formatPayload(row.input_data) }}</pre>
                  <pre class="payload-pre">输出：{{ formatPayload(row.output_data) }}</pre>
                  <pre v-if="row.error_log" class="payload-pre error-pre">失败日志：{{ row.error_log }}</pre>
                </el-collapse-item>
              </el-collapse>
            </template>
          </el-table-column>
          <el-table-column label="截图" width="100">
            <template #default="{ row }">
              <el-image
                v-if="row.screenshot_url"
                class="step-shot"
                :src="row.screenshot_url"
                :preview-src-list="[row.screenshot_url]"
                fit="cover"
                preview-teleported
              />
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getVisualFlowExecutionDetail, getVisualFlowExecutions } from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const executions = ref([])
const detailVisible = ref(false)
const currentExecution = ref(null)
const query = reactive({
  search: '',
  status: '',
  run_type: ''
})
const researchContext = ref({
  project_id: '',
  version_id: 'all',
  module_id: '',
  module_name: '',
  module_path: ''
})
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const normalizeRouteQueryValue = value => {
  if (Array.isArray(value)) {
    return String(value[0] || '').trim()
  }
  return String(value || '').trim()
}

const getRouteExecutionId = () => normalizeRouteQueryValue(route.query.execution_id)
const getRouteFlowId = () => normalizeRouteQueryValue(route.query.flow_id)
const shouldBypassDirectoryFilter = () => Boolean(getRouteExecutionId() || getRouteFlowId())

const applyRouteQueryFilters = () => {
  const executionId = getRouteExecutionId()
  const routeSearch = normalizeRouteQueryValue(route.query.search || route.query.keyword)
  const routeStatus = normalizeRouteQueryValue(route.query.status)
  const routeRunType = normalizeRouteQueryValue(route.query.run_type)

  if (executionId) {
    query.search = executionId
  } else if (routeSearch) {
    query.search = routeSearch
  }
  if (routeStatus) {
    query.status = routeStatus
  }
  if (routeRunType) {
    query.run_type = routeRunType
  }
}

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'visual-flow-executions') return
  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) router.push(targetLocation)
}

const getStatusText = status => ({
  pending: '待执行',
  running: '执行中',
  success: '成功',
  failed: '失败',
  aborted: '已中止'
}[status] || status || '-')

const getStatusTagType = status => ({
  success: 'success',
  failed: 'danger',
  running: 'warning',
  pending: 'info',
  aborted: 'info'
}[status] || 'info')

const formatTime = value => value ? new Date(value).toLocaleString() : '-'
const formatDuration = value => {
  const seconds = Number(value || 0)
  return seconds ? `${seconds.toFixed(1)}s` : '-'
}
const formatPayload = payload => {
  try {
    return JSON.stringify(payload || {}, null, 2)
  } catch (error) {
    return String(payload || '')
  }
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
  if (shouldBypassDirectoryFilter()) {
    return
  }
  pagination.page = 1
  loadExecutions()
}

const loadExecutions = async () => {
  loading.value = true
  try {
    const context = researchContext.value || {}
    const bypassDirectory = shouldBypassDirectoryFilter()
    const response = await getVisualFlowExecutions({
      ...query,
      flow_id: getRouteFlowId() || undefined,
      project_id: !bypassDirectory && context.project_id ? context.project_id : undefined,
      module_id: !bypassDirectory && context.module_id ? context.module_id : undefined,
      module_path: !bypassDirectory && context.module_path ? context.module_path : undefined,
      module_name: !bypassDirectory && context.module_name ? context.module_name : undefined,
      version_id: !bypassDirectory && context.version_id && context.version_id !== 'all' ? context.version_id : undefined,
      include_descendants: true,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    const payload = response?.data || response || {}
    executions.value = payload.results || []
    pagination.total = payload.count || 0
    await openRouteExecutionDetailIfNeeded()
  } catch (error) {
    console.error('加载测试结果失败:', error)
    ElMessage.error(error.response?.data?.error || '加载测试结果失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  query.search = ''
  query.status = ''
  query.run_type = ''
  pagination.page = 1
  loadExecutions()
}

const openDetail = async row => {
  try {
    const response = await getVisualFlowExecutionDetail(row.execution_id)
    currentExecution.value = response?.data || response || row
    detailVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '加载执行详情失败')
  }
}

const openRouteExecutionDetailIfNeeded = async () => {
  const executionId = getRouteExecutionId()
  if (!executionId || currentExecution.value?.execution_id === executionId) {
    return
  }
  const matched = executions.value.find(item => item.execution_id === executionId)
  if (matched) {
    await openDetail(matched)
  }
}

onMounted(() => {
  applyRouteQueryFilters()
  loadExecutions()
})
</script>

<style scoped lang="scss">
.visual-flow-execution-manager {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #f5f7fb;

  .workspace-section-tabs {
    padding: 16px 24px 0;
  }
}

.execution-workspace {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  padding: 12px 24px 0;
}

.execution-main-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.execution-toolbar {
  margin: 0;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.toolbar-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.execution-list {
  flex: 1;
  min-height: 0;
  margin: 12px 0 0;
  padding: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.pagination-bar {
  padding: 12px 0 18px;
  display: flex;
  justify-content: flex-end;
}

.failed-count {
  color: #dc2626;
  margin-left: 6px;
}

.step-table {
  margin-top: 16px;
}

.inline-collapse {
  border: none;
}

.payload-pre {
  margin: 0 0 8px;
  padding: 8px;
  max-height: 120px;
  overflow: auto;
  background: #f8fafc;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.error-pre {
  background: #fef2f2;
  color: #991b1b;
}

.step-shot {
  width: 56px;
  height: 40px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}
</style>
