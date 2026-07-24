<template>
  <div class="snapshot-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="snapshots"
      directory-title="快照页面目录"
      body-class="snapshot-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >

      <main class="snapshot-main-panel">
        <el-card class="toolbar-card" shadow="never">
          <div class="toolbar">
            <div class="toolbar-filters">
              <div class="toolbar-summary">
                <div>
                  <div class="list-title">快照文件列表</div>
                  <div class="list-subtitle">
                    共 {{ pagination.total }} 个快照，当前页 {{ snapshots.length }} 个
                  </div>
                </div>
              </div>

              <el-input
                v-model="filters.keyword"
                clearable
                placeholder="搜索页面名称或快照文件名"
                style="width: 260px"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>

              <el-select v-model="filters.extension" style="width: 120px">
                <el-option label="全部格式" value="all" />
                <el-option label=".yml" value=".yml" />
                <el-option label=".yaml" value=".yaml" />
              </el-select>

              <el-select v-model="filters.sortBy" style="width: 180px">
                <el-option label="最近修改" value="modified_desc" />
                <el-option label="最早修改" value="modified_asc" />
                <el-option label="文件名 A-Z" value="name_asc" />
                <el-option label="文件名 Z-A" value="name_desc" />
                <el-option label="文件最大" value="size_desc" />
                <el-option label="文件最小" value="size_asc" />
              </el-select>

              <el-button @click="loadSnapshots">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>

            <div class="toolbar-actions">
              <TableColumnSettings
                :table-ref="snapshotTableRef"
                storage-key="manual-testcases.snapshots"
              />
              <el-upload
                accept=".yml,.yaml"
                :http-request="handleImportRequest"
                :show-file-list="false"
                multiple
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  导入快照
                </el-button>
              </el-upload>

              <el-button @click="openCreateDrawer">
                <el-icon><Plus /></el-icon>
                新建快照
              </el-button>

              <el-button :disabled="!selectedRows.length" :loading="batchParsing" @click="handleBatchParse">
                批量解析
              </el-button>

              <el-button :disabled="!selectedRows.length" @click="handleBatchExport">
                <el-icon><Download /></el-icon>
                导出选中
              </el-button>

              <el-button :disabled="!selectedRows.length" type="danger" plain @click="handleBatchDelete">
                <el-icon><Delete /></el-icon>
                删除选中
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card class="list-card" shadow="never">
          <div class="table-shell">
          <el-table
            ref="snapshotTableRef"
            v-loading="loading"
            :data="pagedSnapshots"
            height="100%"
            border
            stripe
            @selection-change="handleSelectionChange"
          >
        <el-table-column type="selection" width="48" />

        <el-table-column label="文件名" min-width="280">
          <template #default="{ row }">
            <el-button link type="primary" @click="openSnapshot(row.filename, 'view')">
              {{ row.filename }}
            </el-button>
          </template>
        </el-table-column>

        <el-table-column label="页面名称" min-width="180">
          <template #default="{ row }">
            <span v-if="row.page_name">{{ row.page_name }}</span>
            <el-tag v-else type="info">未设置</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="别名" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.alias || '-' }}</template>
        </el-table-column>

        <el-table-column label="创建方式" min-width="180">
          <template #default="{ row }">
            <el-tag :type="getCreationMethodTagType(row.creation_method)">
              {{ getCreationMethodLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="模块" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ getSnapshotModuleLabel(row) }}</template>
        </el-table-column>

        <el-table-column label="解析状态" min-width="180">
          <template #default="{ row }">
            <div class="parse-status-cell">
              <el-tooltip
                :disabled="!getParseStatusTooltip(row.filename)"
                :content="getParseStatusTooltip(row.filename)"
                placement="top"
              >
                <el-tag :type="getParseStatusType(row.filename)">
                  {{ getParseStatusLabel(row.filename) }}
                </el-tag>
              </el-tooltip>
              <div v-if="getParseStatusMeta(row.filename)" class="parse-status-meta">
                {{ getParseStatusMeta(row.filename) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="修改时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.modified_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" :width="snapshotActionColumnWidth" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openSnapshot(row.filename, 'view')">查看</el-button>
            <el-button link type="success" @click="openSnapshot(row.filename, 'edit')">编辑</el-button>
            <el-button
              link
              type="warning"
              :loading="getParseState(row.filename).status === 'parsing'"
              @click="handleSingleParse(row.filename)"
            >
              解析
            </el-button>
            <el-button link @click="handleSingleExport(row.filename)">导出</el-button>
            <el-button link type="danger" @click="handleDelete(row.filename)">删除</el-button>
          </template>
        </el-table-column>
          </el-table>
          </div>

          <div class="table-footer">
            <div class="table-footer-text">
              已选择 {{ selectedRows.length }} 个文件
            </div>
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
      v-model="recordingDialogVisible"
      title="启动平台受控浏览器录制"
      width="520px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="录制名称">
          <el-input v-model="recordingForm.name" placeholder="例如 登录与下单流程" />
        </el-form-item>
        <el-form-item label="目标系统地址" required>
          <el-input v-model="recordingForm.target_url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="recordingForm.browser_type" style="width: 180px">
            <el-option label="Chromium" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <div class="module-picker">
            <div class="module-picker-row">
              <el-select
                v-model="recordingForm.project_id"
                clearable
                filterable
                placeholder="选择项目"
                style="width: 180px"
                @change="handleRecordingProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <el-button :loading="moduleCategoryLoading" @click="loadModuleCategories(recordingForm.project_id)">
                加载目录
              </el-button>
            </div>
            <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选模块" />
            <div class="module-tree-box">
              <el-tree
                ref="moduleTreeRef"
                :data="moduleCategoryTree"
                node-key="id"
                :props="{ label: 'label', children: 'children' }"
                :filter-node-method="filterModuleTreeNode"
                highlight-current
                default-expand-all
                @node-click="node => applyModuleSelection(recordingForm, node)"
              />
              <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
            </div>
            <div class="module-current">当前模块：{{ recordingForm.module_path || recordingForm.module_name || '-' }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordingDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="recordingStarting" @click="startRecording">
          启动录制
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      direction="rtl"
      size="60%"
      :destroy-on-close="false"
    >
      <div v-loading="drawerLoading" class="snapshot-drawer">
        <div class="drawer-actions">
          <template v-if="isEditing">
            <el-button @click="cancelEdit">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveSnapshot">保存</el-button>
          </template>
          <template v-else>
            <el-button @click="handleSingleExport(currentSnapshot.originalFilename)">导出</el-button>
            <el-button
              type="warning"
              plain
              :loading="getParseState(currentSnapshot.originalFilename).status === 'parsing'"
              @click="handleSingleParse(currentSnapshot.originalFilename)"
            >
              解析
            </el-button>
            <el-button type="primary" @click="switchToEdit">编辑</el-button>
          </template>
        </div>

        <el-row :gutter="12" class="summary-row">
          <el-col :span="6">
            <div class="summary-card">
              <div class="summary-label">文件大小</div>
              <div class="summary-value">{{ formatSize(currentSnapshot.size) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="summary-card">
              <div class="summary-label">文件行数</div>
              <div class="summary-value">{{ currentSnapshotAnalysis.lineCount }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="summary-card">
              <div class="summary-label">可交互元素</div>
              <div class="summary-value">{{ currentSnapshotAnalysis.interactiveCount }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="summary-card">
              <div class="summary-label">解析状态</div>
              <div class="summary-value">
                <el-tag :type="currentSnapshotAnalysis.valid ? 'success' : 'danger'">
                  {{ currentSnapshotAnalysis.valid ? '可解析' : '解析失败' }}
                </el-tag>
              </div>
            </div>
          </el-col>
        </el-row>

        <el-descriptions :column="2" border class="snapshot-meta">
          <el-descriptions-item label="文件名">
            {{ currentSnapshot.originalFilename || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="页面名称">
            {{ currentSnapshot.page_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="别名">
            {{ currentSnapshot.alias || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建方式">
            {{ getCreationMethodLabel(currentSnapshot) }}
          </el-descriptions-item>
          <el-descriptions-item label="模块">
            {{ currentSnapshot.module_path || currentSnapshot.module_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="修改时间">
            {{ formatDate(currentSnapshot.modified_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentSnapshot.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="文件类型">
            {{ currentSnapshot.extension || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-tabs v-model="activeTab" class="drawer-tabs">
          <el-tab-pane label="文件内容" name="content">
            <div class="content-panel">
              <el-form label-position="top">
                <el-form-item label="页面名称">
                  <el-input
                    v-model="currentSnapshot.page_name"
                    :disabled="!isEditing"
                    placeholder="例如 登录页"
                  />
                </el-form-item>
                <el-form-item label="别名">
                  <el-input
                    v-model="currentSnapshot.alias"
                    :disabled="!isEditing"
                    placeholder="例如 登录页 - 初始状态"
                  />
                </el-form-item>
                <el-form-item label="模块">
                  <div class="module-picker">
                    <div class="module-picker-row">
                      <el-select
                        v-model="currentSnapshot.project_id"
                        clearable
                        filterable
                        :disabled="!isEditing"
                        placeholder="选择项目"
                        style="width: 180px"
                        @change="handleSnapshotProjectChange"
                      >
                        <el-option
                          v-for="project in projects"
                          :key="project.id"
                          :label="project.name"
                          :value="project.id"
                        />
                      </el-select>
                      <el-button :disabled="!isEditing" :loading="moduleCategoryLoading" @click="loadModuleCategories(currentSnapshot.project_id)">
                        加载目录
                      </el-button>
                      <el-button v-if="isEditing" link type="danger" @click="clearModuleSelection(currentSnapshot)">清空模块</el-button>
                    </div>
                    <template v-if="isEditing">
                      <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选模块" />
                      <div class="module-tree-box">
                        <el-tree
                          ref="moduleTreeRef"
                          :data="moduleCategoryTree"
                          node-key="id"
                          :props="{ label: 'label', children: 'children' }"
                          :filter-node-method="filterModuleTreeNode"
                          highlight-current
                          default-expand-all
                          @node-click="node => applyModuleSelection(currentSnapshot, node)"
                        />
                        <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
                      </div>
                    </template>
                    <div class="module-current">当前模块：{{ currentSnapshot.module_path || currentSnapshot.module_name || '-' }}</div>
                  </div>
                </el-form-item>
                <el-form-item label="文件名">
                  <el-input
                    v-model="currentSnapshot.filename"
                    :disabled="!isEditing"
                    placeholder="例如 login-page.yml"
                  />
                </el-form-item>
                <el-form-item v-if="isEditing" label="YAML 内容">
                  <el-input
                    v-model="currentSnapshot.content"
                    :autosize="{ minRows: 18, maxRows: 28 }"
                    type="textarea"
                    placeholder="请输入 Playwright 快照 YAML 内容"
                  />
                </el-form-item>
              </el-form>

              <pre v-if="!isEditing" class="snapshot-preview">{{ currentSnapshot.content }}</pre>
            </div>
          </el-tab-pane>

          <el-tab-pane label="解析摘要" name="summary">
            <div class="summary-panel">
              <el-alert
                v-if="!currentSnapshotAnalysis.valid && currentSnapshotAnalysis.error"
                :closable="false"
                :title="currentSnapshotAnalysis.error"
                type="error"
              />

              <el-empty
                v-else-if="!currentSnapshotAnalysis.sampleElements.length"
                description="当前快照没有解析到可交互元素"
              />

              <el-table v-else :data="currentSnapshotAnalysis.sampleElements" border stripe>
                <el-table-column prop="type" label="元素类型" width="120" />
                <el-table-column prop="text" label="元素文本" min-width="220" />
                <el-table-column prop="selector" label="推荐选择器" min-width="260" />
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import {
  createPlaywrightSnapshot,
  deletePlaywrightSnapshot,
  downloadPlaywrightSnapshot,
  exportPlaywrightSnapshots,
  getManualCategories,
  getPlaywrightSnapshotContent,
  getPlaywrightSnapshots,
  getProjectList,
  savePlaywrightSnapshotParseResult,
  startPlaywrightRecording,
  updatePlaywrightSnapshot,
  uploadPlaywrightSnapshots
} from '@/api/testcases'
import {
  buildParseStateFromSnapshot,
  buildSnapshotParsePayload
} from '@/utils/snapshotParseUtils'
import snapshotParser from '@/utils/snapshotParser'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'

const defaultParseState = Object.freeze({
  status: 'idle',
  valid: null,
  lineCount: 0,
  interactiveCount: 0,
  error: '',
  parsedAt: null
})
const snapshotActionColumnWidth = buildActionColumnWidth([[
  '查看',
  '编辑',
  '解析',
  '导出',
  '删除',
]], {
  variant: 'link',
})

const loading = ref(false)
const snapshotTableRef = ref(null)
const drawerLoading = ref(false)
const saving = ref(false)
const batchParsing = ref(false)
const importOverwrite = ref(false)
const drawerVisible = ref(false)
const drawerMode = ref('view')
const activeTab = ref('content')
const snapshots = ref([])
const selectedRows = ref([])
const originalSnapshot = ref(null)
const parseStatusMap = reactive({})
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const recordingDialogVisible = ref(false)
const recordingStarting = ref(false)
const projects = ref([])
const moduleCategoryTree = ref([])
const moduleCategoryLoading = ref(false)
const moduleTreeFilterText = ref('')
const moduleTreeRef = ref(null)
const flatModuleOptions = ref([])
const emptyModuleFields = {
  project_id: '',
  module_id: '',
  module_name: '',
  module_path: ''
}
const CREATION_METHOD_MANUAL = 'manual'
const CREATION_METHOD_SERVER = 'server_playwright_cli'
const CREATION_METHOD_LOCAL_AGENT = 'local_agent_playwright'
const recordingForm = reactive({
  name: '',
  target_url: '',
  browser_type: 'chromium',
  ...emptyModuleFields
})
const researchContext = ref({ ...emptyModuleFields, version_id: 'all', version_name: '' })

const filters = reactive({
  keyword: '',
  extension: 'all',
  sortBy: 'modified_desc'
})
const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'snapshots') {
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

const currentSnapshot = reactive({
  originalFilename: '',
  filename: '',
  page_name: '',
  alias: '',
  content: '',
  creation_method: CREATION_METHOD_MANUAL,
  ...emptyModuleFields,
  size: 0,
  created_at: null,
  modified_at: null,
  extension: ''
})

const isEditing = computed(() => drawerMode.value === 'edit' || drawerMode.value === 'create')

const drawerTitle = computed(() => {
  if (drawerMode.value === 'create') return '新建快照文件'
  if (drawerMode.value === 'edit') return '编辑快照文件'
  return '查看快照文件'
})

const filteredSnapshots = computed(() => {
  return snapshots.value
})

const pagedSnapshots = computed(() => {
  return filteredSnapshots.value
})

const analyzeSnapshotContent = (content = '') => {
  const normalizedContent = typeof content === 'string' ? content : ''
  const lineCount = normalizedContent ? normalizedContent.split(/\r?\n/).length : 0

  if (!normalizedContent.trim()) {
    return {
      valid: true,
      lineCount,
      interactiveCount: 0,
      sampleElements: [],
      interactiveElements: [],
      error: ''
    }
  }

  try {
    const tree = snapshotParser.parse(normalizedContent)
    const interactiveElements = snapshotParser.extractInteractiveElements(tree)

    return {
      valid: true,
      lineCount,
      interactiveCount: interactiveElements.length,
      sampleElements: interactiveElements.slice(0, 20).map(item => ({
        type: item.type || '-',
        text: item.text || item.attributes?.placeholder || item.attributes?.name || item.id || '-',
        selector: item.selectors?.find(selector => selector.type !== 'data-ref')?.value || item.type || '-'
      })),
      interactiveElements,
      error: ''
    }
  } catch (error) {
    return {
      valid: false,
      lineCount,
      interactiveCount: 0,
      sampleElements: [],
      error: error.message || '快照解析失败'
    }
  }
}

const currentSnapshotAnalysis = computed(() => analyzeSnapshotContent(currentSnapshot.content || ''))

watch(
  () => [filters.keyword, filters.extension, filters.sortBy],
  () => {
    if (pagination.page !== 1) {
      pagination.page = 1
    } else {
      loadSnapshots()
    }
  }
)

watch(
  () => [pagination.page, pagination.pageSize],
  () => {
    loadSnapshots()
  }
)

watch(moduleTreeFilterText, value => {
  moduleTreeRef.value?.filter?.(value)
})

watch(
  () => pagination.total,
  total => {
    const maxPage = Math.max(1, Math.ceil(total / pagination.pageSize))
    if (pagination.page > maxPage) {
      pagination.page = maxPage
    }
  }
)

const createParseState = (payload = {}) => ({
  ...defaultParseState,
  ...payload
})

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

const flattenModuleTree = (nodes = []) => {
  const result = []
  nodes.forEach(node => {
    if (!node) return
    result.push({ id: node.id, label: node.label, fullPath: node.fullPath || node.label })
    result.push(...flattenModuleTree(node.children || []))
  })
  return result
}

const filterModuleTreeNode = (keyword, data) => {
  const normalizedKeyword = String(keyword || '').trim().toLowerCase()
  if (!normalizedKeyword) return true
  return [data?.label, data?.fullPath].some(value => String(value || '').toLowerCase().includes(normalizedKeyword))
}

const assignModuleFields = (target, source = {}) => {
  target.project_id = source.project_id || ''
  target.module_id = source.module_id || ''
  target.module_name = source.module_name || ''
  target.module_path = source.module_path || ''
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
  assignModuleFields(recordingForm, context || {})
  resetAndLoadSnapshots()
}

const clearModuleSelection = target => assignModuleFields(target, { project_id: target.project_id || '' })

const applyModuleSelection = (target, node) => {
  if (!target || !node) return
  target.module_id = node.id || ''
  target.module_name = node.label || ''
  target.module_path = node.fullPath || node.label || ''
}

const handleDirectorySelect = node => {
  applyModuleSelection(recordingForm, node)
  resetAndLoadSnapshots()
}

const getSnapshotModuleLabel = snapshot => snapshot?.module_path || snapshot?.module_name || '-'

const getCreationMethodLabel = snapshot => {
  const method = typeof snapshot === 'string' ? snapshot : snapshot?.creation_method
  const labels = {
    [CREATION_METHOD_MANUAL]: '手工创建',
    [CREATION_METHOD_SERVER]: '服务端Playwright CLI录制',
    [CREATION_METHOD_LOCAL_AGENT]: '本地Agent-Playwright录制'
  }
  return snapshot?.creation_method_label || labels[method] || method || '手工创建'
}

const getCreationMethodTagType = method => {
  if (method === CREATION_METHOD_LOCAL_AGENT) return 'primary'
  if (method === CREATION_METHOD_SERVER) return 'success'
  return 'info'
}

const buildModulePayload = form => ({
  project_id: form.project_id || null,
  version_id: researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : null,
  version_name: researchContext.value?.version_name || '',
  module_id: form.module_id || null,
  module_name: form.module_name || '',
  module_path: form.module_path || ''
})

const loadProjects = async () => {
  try {
    const response = await getProjectList()
    projects.value = normalizeListResponse(response.data)
    if (!recordingForm.project_id && projects.value.length) {
      recordingForm.project_id = projects.value[0].id
    }
  } catch (error) {
    projects.value = []
  }
}

const loadModuleCategories = async projectId => {
  const effectiveProjectId = projectId || projects.value[0]?.id
  if (!effectiveProjectId) {
    moduleCategoryTree.value = []
    flatModuleOptions.value = []
    return
  }

  moduleCategoryLoading.value = true
  try {
    const response = await getManualCategories({ project: effectiveProjectId })
    moduleCategoryTree.value = normalizeModuleCategoryTree(normalizeListResponse(response.data))
    flatModuleOptions.value = flattenModuleTree(moduleCategoryTree.value)
  } catch (error) {
    moduleCategoryTree.value = []
    flatModuleOptions.value = []
    ElMessage.error('加载模块目录失败')
  } finally {
    moduleCategoryLoading.value = false
  }
}

const ensureModuleData = async () => {
  if (!projects.value.length) {
    await loadProjects()
  }
  if (!moduleCategoryTree.value.length) {
    await loadModuleCategories(recordingForm.project_id)
  }
}

const handleRecordingProjectChange = async projectId => {
  assignModuleFields(recordingForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
}

const handleDirectoryProjectChange = async projectId => {
  assignModuleFields(recordingForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
  resetAndLoadSnapshots()
}

const handleSnapshotProjectChange = async projectId => {
  assignModuleFields(currentSnapshot, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
}

const getParseState = filename => {
  if (!filename) return defaultParseState
  return parseStatusMap[filename] || defaultParseState
}

const getParseStatusLabel = filename => {
  const state = getParseState(filename)
  switch (state.status) {
    case 'parsing':
      return '解析中'
    case 'success':
      return '可解析'
    case 'error':
      return '解析失败'
    default:
      return '未解析'
  }
}

const getParseStatusType = filename => {
  const state = getParseState(filename)
  switch (state.status) {
    case 'parsing':
      return 'warning'
    case 'success':
      return 'success'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
}

const getParseStatusMeta = filename => {
  const state = getParseState(filename)
  if (state.status !== 'success') return ''
  return `${state.interactiveCount} 个交互元素 / ${state.lineCount} 行`
}

const getParseStatusTooltip = filename => {
  const state = getParseState(filename)
  if (state.status !== 'error') return ''
  return state.error || '快照解析失败'
}

const syncParseStateFromSnapshot = (snapshot) => {
  const filename = snapshot?.filename || snapshot?.originalFilename
  if (!filename) {
    return createParseState(buildParseStateFromSnapshot(snapshot))
  }

  parseStatusMap[filename] = createParseState(buildParseStateFromSnapshot(snapshot))
  return parseStatusMap[filename]
}

const syncParseStateMapFromSnapshots = (items = []) => {
  const filenameSet = new Set()

  items.forEach(item => {
    if (!item?.filename) return
    filenameSet.add(item.filename)
    syncParseStateFromSnapshot(item)
  })

  Object.keys(parseStatusMap).forEach(filename => {
    if (!filenameSet.has(filename)) {
      delete parseStatusMap[filename]
    }
  })
}

const setParseRequestError = (filename, errorMessage) => {
  if (!filename) return
  parseStatusMap[filename] = createParseState({
    status: 'error',
    valid: false,
    error: errorMessage || '加载快照内容失败',
    parsedAt: Date.now()
  })
}

const resetCurrentSnapshot = () => {
  currentSnapshot.originalFilename = ''
  currentSnapshot.filename = ''
  currentSnapshot.page_name = ''
  currentSnapshot.alias = ''
  currentSnapshot.content = ''
  currentSnapshot.creation_method = CREATION_METHOD_MANUAL
  assignModuleFields(currentSnapshot, {})
  currentSnapshot.size = 0
  currentSnapshot.created_at = null
  currentSnapshot.modified_at = null
  currentSnapshot.extension = ''
}

const syncCurrentSnapshot = payload => {
  const filename = payload.originalFilename || payload.filename || ''
  currentSnapshot.originalFilename = filename
  currentSnapshot.filename = payload.filename || filename
  currentSnapshot.page_name = payload.page_name || ''
  currentSnapshot.alias = payload.alias || ''
  currentSnapshot.content = payload.content || ''
  currentSnapshot.creation_method = payload.creation_method || CREATION_METHOD_MANUAL
  assignModuleFields(currentSnapshot, payload.module || payload)
  currentSnapshot.size = payload.size || 0
  currentSnapshot.created_at = payload.created_at || null
  currentSnapshot.modified_at = payload.modified_at || null
  currentSnapshot.extension = payload.extension || ''
  originalSnapshot.value = { ...payload, originalFilename: filename }
}

const loadSnapshots = async () => {
  loading.value = true
  try {
    const response = await getPlaywrightSnapshots({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: filters.keyword.trim() || undefined,
      extension: filters.extension === 'all' ? undefined : filters.extension,
      sort_by: filters.sortBy,
      project_id: recordingForm.project_id || undefined,
      module_id: recordingForm.module_id || undefined,
      module_path: recordingForm.module_path || undefined,
      module_name: recordingForm.module_name || undefined,
      version_id: researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : undefined,
      include_descendants: true
    })
    const results = response.data?.results || []
    snapshots.value = results
    pagination.total = response.data?.count ?? results.length
    selectedRows.value = []
    syncParseStateMapFromSnapshots(results)
  } catch (error) {
    ElMessage.error('加载快照文件列表失败')
  } finally {
    loading.value = false
  }
}

const resetAndLoadSnapshots = () => {
  if (pagination.page !== 1) {
    pagination.page = 1
  } else {
    loadSnapshots()
  }
}

const fetchSnapshotContent = async filename => {
  const response = await getPlaywrightSnapshotContent(filename)
  return response.data || {}
}

const parseSnapshot = async (filename, { silent = false } = {}) => {
  if (!filename) {
    return { ok: false, requestFailed: true, error: '缺少快照文件名' }
  }

  parseStatusMap[filename] = createParseState({
    ...getParseState(filename),
    status: 'parsing',
    error: ''
  })

  try {
    const payload = await fetchSnapshotContent(filename)
    const analysis = analyzeSnapshotContent(payload.content || '')
    const response = await savePlaywrightSnapshotParseResult(filename, buildSnapshotParsePayload(analysis))
    syncParseStateFromSnapshot({ filename, ...(response?.data || response || {}) })
    return {
      ok: analysis.valid,
      requestFailed: false,
      error: analysis.error,
      analysis,
      snapshot: response?.data || response || {}
    }
  } catch (error) {
    const errorMessage = error.response?.data?.error || '加载快照内容失败'
    setParseRequestError(filename, errorMessage)
    if (!silent) {
      ElMessage.error(errorMessage)
    }
    return {
      ok: false,
      requestFailed: true,
      error: errorMessage
    }
  }
}

const openSnapshot = async (filename, mode = 'view') => {
  drawerVisible.value = true
  drawerLoading.value = true
  drawerMode.value = mode
  activeTab.value = 'content'
  resetCurrentSnapshot()

  try {
    const payload = await fetchSnapshotContent(filename)
    syncCurrentSnapshot(payload)
    syncParseStateFromSnapshot(payload)
    if (payload.project_id) {
      await loadModuleCategories(payload.project_id)
    }
  } catch (error) {
    drawerVisible.value = false
    ElMessage.error(error.response?.data?.error || '加载快照文件失败')
  } finally {
    drawerLoading.value = false
  }
}

const openCreateDrawer = () => {
  drawerVisible.value = true
  drawerMode.value = 'create'
  activeTab.value = 'content'
  originalSnapshot.value = null
  resetCurrentSnapshot()
  currentSnapshot.filename = `snapshot-${Date.now()}.yml`
  assignModuleFields(currentSnapshot, recordingForm)
  ensureModuleData()
}

const openRecordingDialog = () => {
  recordingDialogVisible.value = true
  if (!recordingForm.name) {
    recordingForm.name = `录制 ${new Date().toLocaleString()}`
  }
  ensureModuleData()
}

const startRecording = async () => {
  const targetUrl = recordingForm.target_url.trim()
  if (!targetUrl) {
    ElMessage.warning('请输入目标系统地址')
    return
  }

  if (!/^https?:\/\//i.test(targetUrl)) {
    ElMessage.warning('目标系统地址需要以 http:// 或 https:// 开头')
    return
  }
  if (!recordingForm.module_path && !recordingForm.module_name && !recordingForm.module_id) {
    ElMessage.warning('请先选择左侧目录树中的页面菜单节点')
    return
  }

  recordingStarting.value = true
  try {
    const response = await startPlaywrightRecording({
      name: recordingForm.name.trim(),
      target_url: targetUrl,
      browser_type: recordingForm.browser_type,
      recording_method: CREATION_METHOD_SERVER,
      ...buildModulePayload(recordingForm)
    })
    const sessionId = response.data?.session?.session_id
    recordingDialogVisible.value = false
    ElMessage.success('平台受控浏览器录制已启动')
    if (sessionId) {
      router.push({
        path: '/manual-testcases/recordings',
        query: { session_id: sessionId }
      })
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '启动录制失败')
  } finally {
    recordingStarting.value = false
  }
}

const cancelEdit = () => {
  if (drawerMode.value === 'create') {
    drawerVisible.value = false
    return
  }

  if (originalSnapshot.value) {
    syncCurrentSnapshot(originalSnapshot.value)
  }
  drawerMode.value = 'view'
}

const switchToEdit = () => {
  drawerMode.value = 'edit'
  ensureModuleData()
}

const saveSnapshot = async () => {
  if (!currentSnapshot.filename.trim()) {
    ElMessage.warning('请输入文件名')
    return
  }

  if (!currentSnapshot.content.trim()) {
    ElMessage.warning('请输入快照内容')
    return
  }

  saving.value = true
  try {
    let response
    const previousFilename = currentSnapshot.originalFilename
    const payload = {
      filename: currentSnapshot.filename.trim(),
      page_name: currentSnapshot.page_name?.trim() || '',
      alias: currentSnapshot.alias?.trim() || '',
      content: currentSnapshot.content,
      creation_method: currentSnapshot.creation_method || CREATION_METHOD_MANUAL,
      ...buildModulePayload(currentSnapshot)
    }

    if (drawerMode.value === 'create') {
      response = await createPlaywrightSnapshot(payload)
      ElMessage.success('快照文件创建成功')
    } else {
      response = await updatePlaywrightSnapshot(currentSnapshot.originalFilename, payload)
      ElMessage.success('快照文件保存成功')
    }

    const savedSnapshot = response.data || payload
    if (previousFilename && previousFilename !== savedSnapshot.filename) {
      delete parseStatusMap[previousFilename]
    }
    syncCurrentSnapshot(savedSnapshot)
    syncParseStateFromSnapshot(savedSnapshot)
    drawerMode.value = 'view'
    await loadSnapshots()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存快照文件失败')
  } finally {
    saving.value = false
  }
}

const handleImportRequest = async options => {
  const formData = new FormData()
  formData.append('file', options.file)
  formData.append('overwrite', String(importOverwrite.value))
  formData.append('creation_method', CREATION_METHOD_MANUAL)
  const modulePayload = buildModulePayload(recordingForm)
  Object.entries(modulePayload).forEach(([key, value]) => {
    if (value !== null && value !== '') {
      formData.append(key, value)
    }
  })

  try {
    await uploadPlaywrightSnapshots(formData)
    delete parseStatusMap[options.file.name]
    options.onSuccess?.({}, options.file)
    ElMessage.success(`导入成功：${options.file.name}`)
    await loadSnapshots()
  } catch (error) {
    options.onError?.(error)
    ElMessage.error(error.response?.data?.error || `导入失败：${options.file.name}`)
  }
}

const handleSelectionChange = rows => {
  selectedRows.value = rows
}

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const handleSingleParse = async filename => {
  const result = await parseSnapshot(filename, { silent: true })
  if (result.requestFailed) {
    ElMessage.error(result.error || '解析失败')
    return
  }

  if (result.ok) {
    ElMessage.success('快照解析完成')
  } else {
    ElMessage.warning(result.error || '快照解析失败')
  }
}

const handleBatchParse = async () => {
  const filenames = [...new Set(selectedRows.value.map(item => item.filename).filter(Boolean))]
  if (!filenames.length) return

  batchParsing.value = true
  let successCount = 0
  let failedCount = 0

  try {
    for (const filename of filenames) {
      const result = await parseSnapshot(filename, { silent: true })
      if (result.ok) {
        successCount += 1
      } else {
        failedCount += 1
      }
    }

    if (failedCount > 0) {
      ElMessage.warning(`批量解析完成，成功 ${successCount} 个，失败 ${failedCount} 个`)
    } else {
      ElMessage.success(`批量解析完成，共 ${successCount} 个`)
    }
  } finally {
    batchParsing.value = false
  }
}

const handleSingleExport = async filename => {
  if (!filename) return

  try {
    const response = await downloadPlaywrightSnapshot(filename)
    downloadBlob(response.data, filename)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出快照文件失败')
  }
}

const handleBatchExport = async () => {
  const filenames = selectedRows.value.map(item => item.filename)
  if (!filenames.length) return

  try {
    const response = await exportPlaywrightSnapshots(filenames)
    downloadBlob(response.data, 'playwright-snapshots.zip')
    ElMessage.success('批量导出成功')
  } catch (error) {
    ElMessage.error('批量导出失败')
  }
}

const removeSnapshot = async filename => {
  await deletePlaywrightSnapshot(filename)
  delete parseStatusMap[filename]
  if (currentSnapshot.originalFilename === filename) {
    drawerVisible.value = false
  }
  await loadSnapshots()
}

const handleDelete = async filename => {
  try {
    await ElMessageBox.confirm(`确定删除快照文件 ${filename} 吗？`, '提示', {
      type: 'warning'
    })
    await removeSnapshot(filename)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '删除快照文件失败')
    }
  }
}

const handleBatchDelete = async () => {
  const filenames = selectedRows.value.map(item => item.filename)
  if (!filenames.length) return

  try {
    await ElMessageBox.confirm(`确定删除选中的 ${filenames.length} 个快照文件吗？`, '提示', {
      type: 'warning'
    })

    for (const filename of filenames) {
      await deletePlaywrightSnapshot(filename)
      delete parseStatusMap[filename]
    }

    selectedRows.value = []
    await loadSnapshots()
    ElMessage.success('批量删除成功')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '批量删除失败')
    }
  }
}

const formatSize = size => {
  const value = Number(size || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(2)} MB`
}

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(Number(value) * 1000)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

onMounted(() => {
  loadProjects().then(() => {
    if (recordingForm.project_id) {
      return loadModuleCategories(recordingForm.project_id)
    }
    return null
  }).catch(() => {
    // Initial module loading is best-effort; snapshot listing remains usable.
  })
  loadSnapshots()
})
</script>

<style scoped>
.snapshot-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f6fb 100%);
  overflow: hidden;
}

.snapshot-workspace {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
}

.snapshot-directory-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}

.snapshot-directory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.snapshot-directory-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.snapshot-directory-project {
  width: 100%;
}

.snapshot-directory-tree {
  min-height: 0;
  flex: 1;
  overflow: auto;
  border: 1px solid #edf0f5;
  background: #fbfcfe;
}

.snapshot-directory-current {
  min-height: 34px;
  padding: 8px 10px;
  color: #3b82f6;
  font-size: 12px;
  line-height: 1.4;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.snapshot-main-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar-card,
.list-card {
  border-radius: 18px;
  border: 1px solid #e4ebf5;
}

.workspace-section-tabs {
  margin-bottom: 4px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-filters,
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-right: 4px;
}

.overwrite-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4b5563;
  font-size: 13px;
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

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.list-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.list-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.parse-status-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.parse-status-meta {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
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

.snapshot-drawer {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
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

.summary-row {
  margin-bottom: 4px;
}

.summary-card {
  height: 100%;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #ffffff 0%, #f6f8fc 100%);
  border: 1px solid #e6ebf2;
}

.summary-label {
  font-size: 12px;
  color: #6b7280;
}

.summary-value {
  margin-top: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.snapshot-meta {
  margin-bottom: 4px;
}

.drawer-tabs {
  min-height: 0;
}

.content-panel,
.summary-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.snapshot-preview {
  margin: 0;
  padding: 16px;
  border-radius: 14px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 420px;
  overflow: auto;
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

:deep(.drawer-tabs .el-tabs__content) {
  padding-top: 16px;
}

@media (max-width: 1200px) {
  .snapshot-manager {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .snapshot-manager {
    padding: 12px;
  }

  .toolbar,
  .list-header,
  .table-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-filters,
  .toolbar-actions {
    width: 100%;
  }

  .toolbar-summary {
    width: 100%;
    justify-content: space-between;
  }

  .toolbar-filters :deep(.el-input),
  .toolbar-filters :deep(.el-select),
  .toolbar-actions :deep(.el-button),
  .toolbar-actions :deep(.el-upload) {
    width: 100%;
  }
}
</style>
