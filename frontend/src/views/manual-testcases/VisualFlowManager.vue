<template>
  <div class="visual-flow-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="flows"
      directory-title="流程页面目录"
      body-class="flow-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >

      <main class="flow-main-panel">
        <el-card class="toolbar-card" shadow="never">
          <div class="toolbar">
            <div class="toolbar-filters">
              <div class="toolbar-summary">
                <div class="list-title">流程管理</div>
                <div class="list-subtitle">共 {{ pagination.total }} 条流程，当前页 {{ flows.length }} 条</div>
              </div>

              <el-input
                v-model="filters.keyword"
                clearable
                placeholder="搜索流程名称、ID、描述或目标地址"
                style="width: 300px"
                @keyup.enter="resetAndLoadFlows"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select v-model="filters.source" clearable placeholder="全部来源" style="width: 140px" @change="resetAndLoadFlows">
                <el-option label="手工创建" value="manual" />
                <el-option label="录制生成" value="recording" />
              </el-select>
              <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px" @change="resetAndLoadFlows">
                <el-option label="草稿" value="draft" />
                <el-option label="启用" value="active" />
                <el-option label="归档" value="archived" />
              </el-select>
              <el-button :loading="loading" @click="loadFlows">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button
                type="primary"
                plain
                :disabled="!selectedFlows.length"
                @click="openBatchCopyDialog"
              >
                复制{{ selectedFlows.length ? `(${selectedFlows.length})` : '' }}
              </el-button>
            </div>

            <div class="toolbar-actions">
              <TableColumnSettings
                :table-ref="flowTableRef"
                storage-key="manual-testcases.visual-flows"
              />
              <el-button type="primary" @click="openCreateDialog">
                <el-icon><Plus /></el-icon>
                新建流程
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card class="list-card" shadow="never">
          <div class="table-shell">
          <el-table
            ref="flowTableRef"
            v-loading="loading"
            :data="flows"
            height="100%"
            border
            stripe
            @selection-change="handleFlowSelectionChange"
          >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="流程名称" min-width="220">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditor(row)">
              {{ row.name || row.flow_id }}
            </el-button>
            <div class="row-subtext">{{ row.flow_id }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="110">
          <template #default="{ row }">
            <el-tag :type="row.source === 'recording' ? 'success' : 'info'">
              {{ getSourceLabel(row.source) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="节点数" width="90" align="right">
          <template #default="{ row }">{{ row.graph_cell_count || 0 }}</template>
        </el-table-column>
        <el-table-column label="快照/步骤" width="120" align="right">
          <template #default="{ row }">
            {{ row.snapshot_summary?.unique_snapshot_count || 0 }}/{{ row.snapshot_summary?.total_step_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="target_url" label="目标地址" min-width="240" show-overflow-tooltip />
        <el-table-column label="页面目录" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ getFlowModuleLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="录制会话" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.recording_session_name || row.recording_session_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditor(row)">编辑流程</el-button>
            <el-button link type="primary" @click="openCopyDialog(row)">复制</el-button>
            <el-button link type="warning" @click="openEditDialog(row)">编辑信息</el-button>
            <el-button link type="danger" @click="deleteFlow(row)">删除</el-button>
          </template>
        </el-table-column>
          </el-table>
          </div>

          <div class="table-footer">
            <div class="table-footer-text">当前页 {{ flows.length }} 条</div>
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </main>
    </ManualWorkspaceRecordingShell>

    <el-dialog
      v-model="dialogVisible"
      :title="editingFlowId ? '编辑流程信息' : '新建流程'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="flowForm" label-position="top">
        <el-form-item label="流程名称" required>
          <el-input v-model="flowForm.name" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="flowForm.status" style="width: 180px">
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标地址">
          <el-input v-model="flowForm.target_url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="flowForm.browser_type" style="width: 180px">
            <el-option label="Chromium" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="页面目录">
          <div class="module-picker">
            <div class="module-picker-row">
              <el-select
                v-model="flowForm.project_id"
                clearable
                filterable
                placeholder="选择项目"
                style="width: 180px"
                @change="handleFlowProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <el-button :loading="moduleCategoryLoading" @click="loadModuleCategories(flowForm.project_id)">
                加载目录树
              </el-button>
              <el-button link type="danger" @click="clearModuleSelection(flowForm)">清空目录选择</el-button>
            </div>
            <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选页面目录" />
            <div class="module-tree-box">
              <el-tree
                ref="moduleTreeRef"
                :data="moduleCategoryTree"
                node-key="id"
                :props="{ label: 'label', children: 'children' }"
                :filter-node-method="filterModuleTreeNode"
                highlight-current
                default-expand-all
                @node-click="node => applyModuleSelection(flowForm, node)"
              />
              <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
            </div>
            <div class="module-current">流程范围：{{ flowForm.module_path || flowForm.module_name || '未选择目录树页面' }}</div>
          </div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="flowForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveFlowInfo">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="copyDialogVisible"
      title="复制流程"
      width="560px"
      destroy-on-close
    >
      <el-form :model="copyForm" label-position="top">
        <el-form-item label="流程名称" required>
          <el-input v-model="copyForm.name" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="版本号" required>
          <el-select
            v-model="copyForm.version_id"
            filterable
            placeholder="请选择版本号"
            style="width: 240px"
            :loading="versionsLoading"
          >
            <el-option
              v-for="version in versionOptions"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="copyForm.status" style="width: 180px">
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标地址">
          <el-input v-model="copyForm.target_url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="copyForm.browser_type" style="width: 180px">
            <el-option label="Chromium" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="页面目录">
          <div class="module-picker">
            <div class="module-picker-row">
              <el-select
                v-model="copyForm.project_id"
                clearable
                filterable
                placeholder="选择项目"
                style="width: 180px"
                @change="handleCopyProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <el-button :loading="moduleCategoryLoading" @click="loadModuleCategories(copyForm.project_id)">
                加载目录树
              </el-button>
              <el-button link type="danger" @click="clearModuleSelection(copyForm)">清空目录选择</el-button>
            </div>
            <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选页面目录" />
            <div class="module-tree-box">
              <el-tree
                ref="copyModuleTreeRef"
                :data="moduleCategoryTree"
                node-key="id"
                :props="{ label: 'label', children: 'children' }"
                :filter-node-method="filterModuleTreeNode"
                highlight-current
                default-expand-all
                @node-click="node => applyModuleSelection(copyForm, node)"
              />
              <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
            </div>
            <div class="module-current">流程范围：{{ copyForm.module_path || copyForm.module_name || '未选择目录树页面' }}</div>
          </div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="copyForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="copyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="copying" @click="submitCopyFlow">确认复制</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchCopyDialogVisible"
      title="批量复制流程"
      width="420px"
      destroy-on-close
    >
      <el-form :model="batchCopyForm" label-position="top">
        <el-form-item label="版本号" required>
          <el-select
            v-model="batchCopyForm.version_id"
            filterable
            placeholder="请选择版本号"
            style="width: 240px"
            :loading="versionsLoading"
          >
            <el-option
              v-for="version in versionOptions"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchCopyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="copying" @click="submitBatchCopyFlows">确认复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import api from '@/utils/api'
import {
  batchCopyVisualFlows,
  copyVisualFlow,
  createVisualFlow,
  deleteVisualFlow,
  getManualCategories,
  getProjectList,
  getVisualFlows,
  updateVisualFlow
} from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const flowTableRef = ref(null)
const saving = ref(false)
const copying = ref(false)
const dialogVisible = ref(false)
const copyDialogVisible = ref(false)
const batchCopyDialogVisible = ref(false)
const editingFlowId = ref('')
const copyingFlowId = ref('')
const flows = ref([])
const selectedFlows = ref([])
const projects = ref([])
const versionOptions = ref([])
const versionsLoading = ref(false)
const moduleCategoryTree = ref([])
const moduleCategoryLoading = ref(false)
const moduleTreeFilterText = ref('')
const moduleTreeRef = ref(null)
const copyModuleTreeRef = ref(null)

const emptyModuleFields = {
  project_id: '',
  version_name: '',
  module_id: '',
  module_name: '',
  module_path: ''
}

const filters = reactive({
  keyword: '',
  source: '',
  status: ''
})
const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'flows') {
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const flowForm = reactive({
  name: '',
  description: '',
  status: 'draft',
  target_url: '',
  browser_type: 'chromium',
  ...emptyModuleFields
})
const copyForm = reactive({
  name: '',
  description: '',
  status: 'draft',
  target_url: '',
  browser_type: 'chromium',
  version_id: '',
  ...emptyModuleFields
})
const batchCopyForm = reactive({
  version_id: ''
})

const directoryForm = reactive({
  ...emptyModuleFields
})
const researchContext = ref({ ...emptyModuleFields, version_id: 'all', version_name: '' })

watch(
  () => filters.keyword,
  () => {
    if (!filters.keyword) {
      resetAndLoadFlows()
    }
  }
)

watch(
  () => [pagination.page, pagination.pageSize],
  () => {
    loadFlows()
  }
)

watch(
  () => pagination.total,
  total => {
    const maxPage = Math.max(1, Math.ceil(total / pagination.pageSize))
    if (pagination.page > maxPage) {
      pagination.page = maxPage
    }
  }
)

watch(moduleTreeFilterText, value => {
  moduleTreeRef.value?.filter?.(value)
  copyModuleTreeRef.value?.filter?.(value)
})

const resetForm = () => {
  flowForm.name = ''
  flowForm.description = ''
  flowForm.status = 'draft'
  flowForm.target_url = ''
  flowForm.browser_type = 'chromium'
  assignModuleFields(flowForm, directoryForm)
}

const resetCopyForm = row => {
  copyForm.name = row?.name || ''
  copyForm.description = row?.description || ''
  copyForm.status = row?.status || 'draft'
  copyForm.target_url = row?.target_url || ''
  copyForm.browser_type = row?.browser_type || 'chromium'
  copyForm.version_id = ''
  copyForm.version_name = ''
  assignModuleFields(copyForm, row?.module || row || directoryForm)
}

const resetAndLoadFlows = () => {
  if (pagination.page !== 1) {
    pagination.page = 1
  } else {
    loadFlows()
  }
}

const loadFlows = async () => {
  loading.value = true
  try {
    const response = await getVisualFlows({
      keyword: filters.keyword.trim(),
      source: filters.source || undefined,
      status: filters.status || undefined,
      project_id: directoryForm.project_id || undefined,
      module_id: directoryForm.module_id || undefined,
      module_path: directoryForm.module_path || undefined,
      module_name: directoryForm.module_name || undefined,
      version_id: researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : undefined,
      include_descendants: true,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    flows.value = response.data?.results || []
    selectedFlows.value = []
    pagination.total = response.data?.count ?? flows.value.length
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '加载流程列表失败')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingFlowId.value = ''
  resetForm()
  dialogVisible.value = true
  ensureModuleData()
}

const openEditDialog = row => {
  editingFlowId.value = row.flow_id
  flowForm.name = row.name || ''
  flowForm.description = row.description || ''
  flowForm.status = row.status || 'draft'
  flowForm.target_url = row.target_url || ''
  flowForm.browser_type = row.browser_type || 'chromium'
  assignModuleFields(flowForm, row.module || row)
  dialogVisible.value = true
  ensureModuleData()
}

const handleFlowSelectionChange = rows => {
  selectedFlows.value = rows || []
}

const loadVersions = async projectId => {
  const effectiveProjectId = projectId || directoryForm.project_id || copyForm.project_id
  if (!effectiveProjectId) {
    versionOptions.value = []
    return
  }
  versionsLoading.value = true
  try {
    const response = await api.get('/versions/', { params: { projects: effectiveProjectId } })
    versionOptions.value = normalizeListResponse(response.data)
  } catch (error) {
    versionOptions.value = []
    ElMessage.error('加载版本号失败')
  } finally {
    versionsLoading.value = false
  }
}

const openCopyDialog = async row => {
  if (!row?.flow_id) return
  copyingFlowId.value = row.flow_id
  resetCopyForm(row)
  copyDialogVisible.value = true
  await ensureModuleData(copyForm.project_id)
  await loadVersions(copyForm.project_id || directoryForm.project_id)
  const currentVersionId = researchContext.value?.version_id
  copyForm.version_id = currentVersionId && currentVersionId !== 'all' ? currentVersionId : (versionOptions.value[0]?.id || '')
}

const openBatchCopyDialog = async () => {
  if (!selectedFlows.value.length) {
    ElMessage.warning('请选择要复制的流程')
    return
  }
  batchCopyForm.version_id = ''
  batchCopyDialogVisible.value = true
  await loadVersions(directoryForm.project_id || selectedFlows.value[0]?.project_id)
  const currentVersionId = researchContext.value?.version_id
  batchCopyForm.version_id = currentVersionId && currentVersionId !== 'all' ? currentVersionId : (versionOptions.value[0]?.id || '')
}

const submitCopyFlow = async () => {
  const name = copyForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入流程名称')
    return
  }
  if (!copyForm.version_id) {
    ElMessage.warning('请选择版本号')
    return
  }
  copying.value = true
  try {
    await copyVisualFlow(copyingFlowId.value, {
      name,
      description: copyForm.description,
      status: copyForm.status,
      target_url: copyForm.target_url,
      browser_type: copyForm.browser_type,
      version_id: copyForm.version_id,
      ...buildModulePayload(copyForm)
    })
    copyDialogVisible.value = false
    ElMessage.success('流程复制成功')
    await loadFlows()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '复制流程失败')
  } finally {
    copying.value = false
  }
}

const submitBatchCopyFlows = async () => {
  if (!selectedFlows.value.length) {
    ElMessage.warning('请选择要复制的流程')
    return
  }
  if (!batchCopyForm.version_id) {
    ElMessage.warning('请选择版本号')
    return
  }
  copying.value = true
  try {
    await batchCopyVisualFlows({
      flow_ids: selectedFlows.value.map(row => row.flow_id).filter(Boolean),
      version_id: batchCopyForm.version_id
    })
    batchCopyDialogVisible.value = false
    ElMessage.success('流程批量复制成功')
    await loadFlows()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '批量复制流程失败')
  } finally {
    copying.value = false
  }
}

const saveFlowInfo = async () => {
  const name = flowForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入流程名称')
    return
  }

  saving.value = true
  try {
    const payload = {
      name,
      description: flowForm.description,
      status: flowForm.status,
      target_url: flowForm.target_url,
      browser_type: flowForm.browser_type,
      ...buildModulePayload(flowForm)
    }

    if (editingFlowId.value) {
      await updateVisualFlow(editingFlowId.value, payload)
      ElMessage.success('流程信息已更新')
    } else {
      const response = await createVisualFlow({
        ...payload,
        source: 'manual',
        graph_data: { cells: [] }
      })
      const flowId = response.data?.flow_id
      ElMessage.success('流程已创建')
      if (flowId) {
        openEditor({ flow_id: flowId })
      }
    }

    dialogVisible.value = false
    await loadFlows()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存流程失败')
  } finally {
    saving.value = false
  }
}

const deleteFlow = async row => {
  try {
    await ElMessageBox.confirm(`确定删除流程“${row.name || row.flow_id}”吗？`, '提示', { type: 'warning' })
    await deleteVisualFlow(row.flow_id)
    await loadFlows()
    ElMessage.success('流程已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '删除流程失败')
    }
  }
}

const openEditor = row => {
  if (!row?.flow_id) return
  router.push({
    path: '/manual-testcases/visual-flow',
    query: { flow_id: row.flow_id }
  })
}

const normalizeListResponse = payload => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const normalizeModuleCategoryTree = (categories = [], parentPath = []) =>
  normalizeListResponse(categories).map(category => {
    const label = String(category?.name || '').trim()
    const currentPath = [...parentPath, label].filter(Boolean)
    return {
      id: category?.id,
      label,
      fullPath: currentPath.join(' / '),
      children: normalizeModuleCategoryTree(category?.children || [], currentPath)
    }
  })

const filterModuleTreeNode = (keyword, data) => {
  const normalizedKeyword = String(keyword || '').trim().toLowerCase()
  if (!normalizedKeyword) return true
  return [data?.label, data?.fullPath].some(value => String(value || '').toLowerCase().includes(normalizedKeyword))
}

const assignModuleFields = (target, source = {}) => {
  target.project_id = source.project_id || ''
  if ('version_name' in target || source.version_name) {
    target.version_name = source.version_name || ''
  }
  target.module_id = source.module_id || ''
  target.module_name = source.module_name || ''
  target.module_path = source.module_path || ''
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
  assignModuleFields(directoryForm, context || {})
  resetAndLoadFlows()
}

const clearModuleSelection = target => assignModuleFields(target, { project_id: target.project_id || '' })

const applyModuleSelection = (target, node) => {
  if (!target || !node) return
  target.module_id = node.id || ''
  target.module_name = node.label || ''
  target.module_path = node.fullPath || node.label || ''
}

const buildModulePayload = form => ({
  project_id: form.project_id || null,
  version_id: form.version_id && form.version_id !== 'all'
    ? form.version_id
    : (researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : null),
  version_name: versionOptions.value.find(version => String(version.id) === String(form.version_id))?.name || form.version_name || researchContext.value?.version_name || '',
  module_id: form.module_id || null,
  module_name: form.module_name || '',
  module_path: form.module_path || ''
})

const getFlowModuleLabel = flow => flow?.module_path || flow?.module_name || '-'

const loadProjects = async () => {
  try {
    const response = await getProjectList()
    projects.value = normalizeListResponse(response.data)
    if (!directoryForm.project_id && projects.value.length) {
      directoryForm.project_id = projects.value[0].id
    }
  } catch (error) {
    projects.value = []
  }
}

const loadModuleCategories = async projectId => {
  const effectiveProjectId = projectId || projects.value[0]?.id
  if (!effectiveProjectId) {
    moduleCategoryTree.value = []
    return
  }

  moduleCategoryLoading.value = true
  try {
    const response = await getManualCategories({ project: effectiveProjectId })
    moduleCategoryTree.value = normalizeModuleCategoryTree(normalizeListResponse(response.data))
  } catch (error) {
    moduleCategoryTree.value = []
    ElMessage.error('加载模块目录失败')
  } finally {
    moduleCategoryLoading.value = false
  }
}

const ensureModuleData = async projectId => {
  if (!projects.value.length) {
    await loadProjects()
  }
  const effectiveProjectId = projectId || directoryForm.project_id || flowForm.project_id
  if (!moduleCategoryTree.value.length || (effectiveProjectId && String(effectiveProjectId) !== String(directoryForm.project_id || flowForm.project_id || ''))) {
    await loadModuleCategories(effectiveProjectId)
  }
}

const handleDirectorySelect = node => {
  applyModuleSelection(directoryForm, node)
  resetAndLoadFlows()
}

const handleDirectoryProjectChange = async projectId => {
  assignModuleFields(directoryForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
  resetAndLoadFlows()
}

const handleFlowProjectChange = async projectId => {
  assignModuleFields(flowForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
}

const handleCopyProjectChange = async projectId => {
  assignModuleFields(copyForm, { project_id: projectId || '', version_id: copyForm.version_id || '' })
  copyForm.version_id = ''
  await Promise.all([
    loadModuleCategories(projectId),
    loadVersions(projectId)
  ])
}

const getSourceLabel = source => {
  const labels = {
    manual: '手工创建',
    recording: '录制生成'
  }
  return labels[source] || source || '-'
}

const getStatusLabel = status => {
  const labels = {
    draft: '草稿',
    active: '启用',
    archived: '归档'
  }
  return labels[status] || status || '-'
}

const getStatusTag = status => {
  const tags = {
    draft: 'info',
    active: 'success',
    archived: 'warning'
  }
  return tags[status] || 'info'
}

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

onMounted(() => {
  loadProjects().then(() => {
    if (directoryForm.project_id) {
      return loadModuleCategories(directoryForm.project_id)
    }
    return null
  }).catch(() => {
    // Initial module loading is best-effort; flow listing remains usable.
  })
  loadFlows()
})
</script>

<style scoped>
.visual-flow-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f5f7fb;
  overflow: hidden;
}

.flow-workspace {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
}

.flow-directory-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}

.flow-directory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.flow-directory-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.flow-directory-project {
  width: 100%;
}

.flow-directory-tree {
  min-height: 0;
  flex: 1;
  overflow: auto;
  border: 1px solid #edf0f5;
  background: #fbfcfe;
}

.flow-directory-current {
  min-height: 34px;
  padding: 8px 10px;
  color: #3b82f6;
  font-size: 12px;
  line-height: 1.4;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.flow-main-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar-card,
.list-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.workspace-section-tabs {
  margin-bottom: 4px;
}

.toolbar,
.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.toolbar-filters,
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-summary {
  flex-shrink: 0;
  padding-right: 4px;
}

.list-card {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-shell {
  flex: 1;
  min-height: 0;
}

.list-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.list-subtitle,
.row-subtext {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.table-footer {
  flex-shrink: 0;
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.table-footer-text {
  color: #6b7280;
  font-size: 13px;
}

.module-picker {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.module-picker-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.module-tree-box {
  max-height: 220px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.module-current {
  font-size: 12px;
  color: #6b7280;
}

:deep(.el-card__body) {
  padding: 12px 14px;
}

:deep(.list-card .el-card__body) {
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
