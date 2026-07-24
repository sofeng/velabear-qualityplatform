<template>
  <div class="page-container defect-list-page" :class="{ 'defect-list-page--embedded': embedded }">
    <div v-if="!embedded" class="page-header">
      <div class="header-title">
        <h1 class="page-title">技术方案设计管理</h1>
        <p v-if="hasLinkedContext" class="page-subtitle">
          已联动到
          <span v-if="selectedProjectName">项目 {{ selectedProjectName }}</span>
          <span v-if="selectedProjectName && selectedVersionName"> / </span>
          <span v-if="selectedVersionName">版本 {{ selectedVersionName }}</span>
        </p>
      </div>
    </div>
    <div class="tab-panel defect-list-panel">
      <div class="tab-toolbar">
        <el-form :inline="true" :model="filters" class="search-form defect-search-form">
          <el-form-item label="方案编号">
            <el-input
              v-model="filters.code"
              clearable
              placeholder="支持编号模糊搜索"
              style="width: 180px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="关键字">
            <el-input
              v-model="filters.keyword"
              clearable
              placeholder="搜索标题、描述、设计背景、方案说明或需求编号"
              style="width: 220px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="测试点ID">
            <el-input
              v-model="filters.testpointId"
              clearable
              placeholder="请输入测试点ID"
              style="width: 220px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item v-if="!embedded" label="项目">
            <el-select
              v-model="filters.projectId"
              clearable
              filterable
              placeholder="全部项目"
              style="width: 180px"
              @change="handleProjectChange"
            >
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="!embedded" label="版本">
            <el-select
              v-model="filters.versionId"
              clearable
              filterable
              placeholder="全部版本"
              style="width: 180px"
              :disabled="!filters.projectId"
            >
              <el-option
                v-for="version in versions"
                :key="version.id"
                :label="version.name"
                :value="version.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="filters.status"
              clearable
              placeholder="全部状态"
              style="width: 140px"
            >
              <el-option
                v-for="option in statusOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="复杂度">
            <el-select
              v-model="filters.severity"
              clearable
              placeholder="全部等级"
              style="width: 140px"
            >
              <el-option
                v-for="option in severityOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="负责人">
            <el-select
              v-model="filters.assigneeId"
              clearable
              filterable
              placeholder="全部负责人"
              style="width: 180px"
            >
              <el-option
                v-for="user in users"
                :key="user.id"
                :label="getUserDisplayName(user, `用户${user.id}`)"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleReset">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>

        <div class="tab-toolbar-actions defect-toolbar-actions">
          <div class="defect-toolbar-buttons">
            <TableColumnSettings
              :table-ref="technicalSolutionTableRef"
              storage-key="manual-testcases.technical-solution-designs"
            />
            <el-button v-if="!embedded && hasLinkedContext" link type="primary" @click="clearLinkedContext">
              清空联动
            </el-button>
            <el-button v-if="!embedded && isFromManualWorkspace" @click="goBackToManualWorkspace">
              返回思源研发管理
            </el-button>
            <el-button @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button :loading="excelImporting" @click="handleImportButtonClick">
              导入技术方案设计Excel
            </el-button>
            <el-button type="primary" @click="goToCreate">
              <el-icon><Plus /></el-icon>
              新建技术方案设计
            </el-button>
            <input
              ref="excelFileInputRef"
              type="file"
              accept=".xlsx"
              class="excel-import-input"
              @change="handleImportFileChange"
            >
          </div>
        </div>
      </div>

      <el-table
        ref="technicalSolutionTableRef"
        v-loading="loading"
        :data="defects"
        stripe
        row-key="id"
        style="width: 100%"
        class="defect-table"
        :max-height="defectTableMaxHeight"
        empty-text="暂无技术方案设计数据"
      >
        <el-table-column
          prop="code"
          label="方案编号"
          width="168"
          fixed="left"
          sortable
          :sort-method="createTextSorter(row => row.code)"
          :filters="defectColumnFilters.code"
          :filter-method="createTableFilter(row => row.code)"
        />
        <el-table-column
          prop="title"
          label="标题"
          min-width="240"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.title)"
          :filters="defectColumnFilters.title"
          :filter-method="createTableFilter(row => row.title)"
        />
        <el-table-column
          prop="priority"
          label="优先级"
          width="100"
          sortable
          :sort-method="createTextSorter(getDefectPriority)"
          :filters="defectColumnFilters.priority"
          :filter-method="createTableFilter(getDefectPriority)"
        >
          <template #default="{ row }">
            <el-tag :type="getPriorityTagType(row.priority)" effect="light">
              {{ getDefectPriority(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="problem_reason"
          label="设计背景"
          min-width="220"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(getDefectProblemReason)"
          :filters="defectColumnFilters.problem_reason"
          :filter-method="createTableFilter(getDefectProblemReason)"
        >
          <template #default="{ row }">
            {{ row.problem_reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="root_cause"
          label="方案说明"
          min-width="220"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(getDefectRootCause)"
          :filters="defectColumnFilters.root_cause"
          :filter-method="createTableFilter(getDefectRootCause)"
        >
          <template #default="{ row }">
            {{ row.root_cause || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="需求编号"
          min-width="140"
          sortable
          :sort-method="createTextSorter(row => row.requirement_id)"
          :filters="defectColumnFilters.requirement_id"
          :filter-method="createTableFilter(row => row.requirement_id)"
        >
          <template #default="{ row }">
            <el-button
              v-if="row.requirement_id"
              link
              type="primary"
              @click="jumpToRequirement(row)"
            >
              {{ row.requirement_id }}
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="frontend_developer"
          label="前端方案负责人"
          min-width="140"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(getDefectFrontendDeveloper)"
          :filters="defectColumnFilters.frontend_developer"
          :filter-method="createTableFilter(getDefectFrontendDeveloper)"
        >
          <template #default="{ row }">
            {{ row.frontend_developer || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="backend_developer"
          label="后端方案负责人"
          min-width="140"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(getDefectBackendDeveloper)"
          :filters="defectColumnFilters.backend_developer"
          :filter-method="createTableFilter(getDefectBackendDeveloper)"
        >
          <template #default="{ row }">
            {{ row.backend_developer || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="模块路径"
          min-width="260"
          sortable
          :sort-method="createTextSorter(getDefectModuleLabels)"
          :filters="defectColumnFilters.modules"
          :filter-method="createTableFilter(getDefectModuleLabels)"
        >
          <template #default="{ row }">
            <div v-if="getModuleRelations(row).length" class="relation-tags">
              <el-tag
                v-for="item in getModuleRelations(row)"
                :key="item.relation_key"
                class="relation-tag"
                size="small"
                effect="plain"
                @click="jumpToRelation(item, 'module')"
              >
                {{ item.path || item.short_label }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="关联测试用例"
          min-width="220"
          sortable
          :sort-method="createTextSorter(getDefectTestcaseLabels)"
          :filters="defectColumnFilters.related_testcases"
          :filter-method="createTableFilter(getDefectTestcaseLabels)"
        >
          <template #default="{ row }">
            <div v-if="getTestcaseRelations(row).length" class="relation-tags">
              <el-tag
                v-for="item in getTestcaseRelations(row)"
                :key="item.relation_key"
                class="relation-tag"
                size="small"
                effect="plain"
                @click="jumpToRelation(item, 'case')"
              >
                {{ item.short_label }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="关联测试点"
          min-width="220"
          sortable
          :sort-method="createTextSorter(getDefectTestpointLabels)"
          :filters="defectColumnFilters.related_testpoints"
          :filter-method="createTableFilter(getDefectTestpointLabels)"
        >
          <template #default="{ row }">
            <div v-if="getTestpointRelations(row).length" class="relation-tags">
              <el-tag
                v-for="item in getTestpointRelations(row)"
                :key="item.relation_key"
                class="relation-tag"
                size="small"
                effect="plain"
                @click="jumpToRelation(item, 'testpoint')"
              >
                {{ item.short_label }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="项目"
          min-width="140"
          sortable
          :sort-method="createTextSorter(getDefectProjectName)"
          :filters="defectColumnFilters.project"
          :filter-method="createTableFilter(getDefectProjectName)"
        >
          <template #default="{ row }">
            {{ row.project?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="版本"
          min-width="140"
          sortable
          :sort-method="createTextSorter(getDefectVersionName)"
          :filters="defectColumnFilters.version"
          :filter-method="createTableFilter(getDefectVersionName)"
        >
          <template #default="{ row }">
            {{ row.version?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="复杂度"
          width="110"
          sortable
          :sort-method="createTextSorter(row => getSeverityText(row.severity))"
          :filters="defectColumnFilters.severity"
          :filter-method="createTableFilter(row => getSeverityText(row.severity))"
        >
          <template #default="{ row }">
            <el-tag :type="getSeverityTagType(row.severity)" effect="light">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="120"
          sortable
          :sort-method="createTextSorter(row => getStatusText(row.status))"
          :filters="defectColumnFilters.status"
          :filter-method="createTableFilter(row => getStatusText(row.status))"
        >
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="负责人"
          min-width="220"
          sortable
          :sort-method="createTextSorter(getDefectAssigneeNames)"
          :filters="defectColumnFilters.assignees"
          :filter-method="createTableFilter(getDefectAssigneeNames)"
        >
          <template #default="{ row }">
            <div v-if="row.assignees?.length" class="relation-tags">
              <el-tag
                v-for="assignee in row.assignees"
                :key="assignee.id"
                size="small"
                effect="plain"
              >
                {{ getUserDisplayName(assignee, `用户${assignee.id}`) }}
              </el-tag>
            </div>
            <span v-else class="empty-text">未指派</span>
          </template>
        </el-table-column>
        <el-table-column
          label="创建人"
          width="120"
          sortable
          :sort-method="createTextSorter(getDefectCreatorName)"
          :filters="defectColumnFilters.created_by"
          :filter-method="createTableFilter(getDefectCreatorName)"
        >
          <template #default="{ row }">
            {{ getUserDisplayName(row.created_by, '-') }}
          </template>
        </el-table-column>
        <el-table-column
          prop="attachments_count"
          label="附件数"
          width="88"
          align="center"
          sortable
          :sort-method="createNumberSorter(row => row.attachments_count)"
          :filters="defectColumnFilters.attachments_count"
          :filter-method="createTableFilter(row => row.attachments_count)"
        />
        <el-table-column
          label="更新时间"
          width="180"
          sortable
          :sort-method="createDateSorter(row => row.updated_at)"
          :filters="defectColumnFilters.updated_at"
          :filter-method="createTableFilter(getDefectUpdatedAt)"
        >
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="defectActionColumnWidth" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button type="success" size="small" @click="handleViewMindmap(row)">
                <el-icon><View /></el-icon>
                查看脑图
              </el-button>
              <el-button type="primary" size="small" @click="goToEdit(row.id)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button type="danger" plain size="small" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        class="tab-pagination"
        @current-change="loadDefects"
        @size-change="handlePageSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh, Search, View } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/utils/api'
import { deleteTechnicalSolutionDesign, getTechnicalSolutionDesigns, importTechnicalSolutionDesignExcel } from '@/api/technicalSolutionDesigns'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import {
  buildTableFilters,
  compareTableNumber,
  createDateSorter,
  createNumberSorter,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { getUserDisplayName } from '@/utils/userDisplay'
import {
  buildDefectRelationRouteQuery,
  ensureUniqueDefectRelationItems,
} from '@/utils/defectRelations'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  active: {
    type: Boolean,
    default: true,
  },
  linkedCategoryId: {
    type: [Number, String],
    default: null,
  },
  linkedProjectId: {
    type: [Number, String],
    default: null,
  },
  linkedVersionId: {
    type: [Number, String],
    default: null,
  },
  linkedCategoryName: {
    type: String,
    default: '',
  },
  linkedCategoryPath: {
    type: String,
    default: '',
  },
  linkedKeyword: {
    type: String,
    default: '',
  },
  linkedTestpointId: {
    type: String,
    default: '',
  },
})

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const technicalSolutionTableRef = ref(null)
const defects = ref([])
const projects = ref([])
const versions = ref([])
const users = ref([])
const excelImporting = ref(false)
const excelFileInputRef = ref(null)
const isSyncingRoute = ref(false)
const latestLoadRequestId = ref(0)

const filters = reactive({
  code: '',
  keyword: '',
  testpointId: '',
  projectId: '',
  versionId: '',
  status: '',
  severity: '',
  assigneeId: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const severityOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '关键', value: 'critical' },
]

const priorityOptions = [
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
  { label: 'P4', value: 'P4' },
]

const statusOptions = [
  { label: '草稿', value: 'new' },
  { label: '设计中', value: 'in_progress' },
  { label: '已评审', value: 'resolved' },
  { label: '已驳回', value: 'rejected' },
  { label: '已归档', value: 'closed' },
  { label: '重新设计', value: 'reopened' },
  { label: '作废', value: 'invalid' },
]
const defectActionColumnWidth = buildActionColumnWidth([[
  { label: '查看脑图', icon: true },
  { label: '编辑', icon: true },
  { label: '删除', icon: true },
]])

const getQueryValue = (value) => (Array.isArray(value) ? value[0] : value)

const parseNumberQuery = (value, fallback = '') => {
  const normalized = getQueryValue(value)
  if (normalized === undefined || normalized === null || normalized === '') {
    return fallback
  }

  const parsed = Number(normalized)
  return Number.isNaN(parsed) ? fallback : parsed
}

const normalizeQueryForCompare = (query = {}) => {
  const normalized = {}

  Object.keys(query)
    .sort()
    .forEach((key) => {
      const value = getQueryValue(query[key])
      if (value === undefined || value === null || value === '') {
        return
      }
      normalized[key] = String(value)
    })

  return normalized
}

const buildQuerySignature = (query = {}) => JSON.stringify(normalizeQueryForCompare(query))

const areQueryObjectsEqual = (left, right) => {
  const leftQuery = normalizeQueryForCompare(left)
  const rightQuery = normalizeQueryForCompare(right)
  const leftKeys = Object.keys(leftQuery)
  const rightKeys = Object.keys(rightQuery)

  if (leftKeys.length !== rightKeys.length) {
    return false
  }

  return leftKeys.every((key) => leftQuery[key] === rightQuery[key])
}

const getSeverityText = (value) =>
  severityOptions.find((option) => option.value === value)?.label || value || '-'

const getPriorityText = (value) =>
  priorityOptions.find((option) => option.value === value)?.label || value || '-'

const getPriorityTagType = (value) =>
  ({
    P1: 'danger',
    P2: 'warning',
    P3: 'success',
    P4: 'info',
  }[value] || 'info')

const getSeverityTagType = (value) =>
  ({
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  }[value] || 'info')

const getStatusText = (value) =>
  statusOptions.find((option) => option.value === value)?.label || value || '-'

const getStatusTagType = (value) =>
  ({
    new: 'info',
    in_progress: 'warning',
    resolved: 'success',
    rejected: 'danger',
    closed: '',
    reopened: 'warning',
    invalid: 'info',
  }[value] ?? 'info')

const formatDate = (value) => (value ? dayjs(value).format('YYYY/MM/DD HH:mm:ss') : '-')
const defectTableMaxHeight = computed(() => (props.embedded ? 'calc(100vh - 320px)' : 'calc(100vh - 360px)'))

const selectedProjectName = computed(() => {
  const matchedProject = projects.value.find((item) => String(item.id) === String(filters.projectId))
  return matchedProject?.name || ''
})

const selectedVersionName = computed(() => {
  const matchedVersion = versions.value.find((item) => String(item.id) === String(filters.versionId))
  return matchedVersion?.name || ''
})

const normalizedLinkedKeyword = computed(() => String(props.linkedKeyword || '').trim())
const normalizedLinkedTestpointId = computed(() => String(props.linkedTestpointId || '').trim())
const hasLinkedContext = computed(() => Boolean(filters.projectId || filters.versionId))
const isFromManualWorkspace = computed(() => getQueryValue(route.query.source) === 'manual-testcases')

const manualWorkspaceQuery = computed(() => {
  const query = {}
  const projectId = filters.projectId || parseNumberQuery(route.query.project_id)
  const versionId = filters.versionId || parseNumberQuery(route.query.version_id)
  const categoryId = props.linkedCategoryId || parseNumberQuery(route.query.category_id)
  const tab = String(getQueryValue(route.query.tab) || '')

  if (projectId) {
    query.project_id = String(projectId)
  }
  if (versionId) {
    query.version_id = String(versionId)
  }
  if (categoryId) {
    query.category_id = String(categoryId)
  }
  if (tab) {
    query.tab = tab
  }

  return query
})

const listStateQuery = computed(() => {
  const query = {}
  const source = getQueryValue(route.query.source)
  const tab = props.embedded ? 'technical-solution-designs' : String(getQueryValue(route.query.tab) || '')

  if (filters.code.trim()) {
    query.code = filters.code.trim()
  }
  if (filters.keyword.trim()) {
    query.keyword = filters.keyword.trim()
  }
  if (filters.testpointId.trim()) {
    query.testpoint_id = filters.testpointId.trim()
  }
  if (filters.projectId) {
    query.project_id = String(filters.projectId)
  }
  if (filters.versionId) {
    query.version_id = String(filters.versionId)
  }
  if (filters.status) {
    query.status = filters.status
  }
  if (filters.severity) {
    query.severity = filters.severity
  }
  if (filters.assigneeId) {
    query.assignee_id = String(filters.assigneeId)
  }
  if (pagination.page > 1) {
    query.page = String(pagination.page)
  }
  if (pagination.pageSize !== 10) {
    query.page_size = String(pagination.pageSize)
  }
  if (source && !props.embedded) {
    query.source = source
  }
  if (tab) {
    query.tab = tab
  }

  return query
})

const embeddedContextSignature = computed(() => buildQuerySignature({
  linked_project_id: props.linkedProjectId,
  linked_version_id: props.linkedVersionId,
  linked_category_id: props.linkedCategoryId,
  linked_category_name: props.linkedCategoryName,
  linked_category_path: props.linkedCategoryPath,
}))

const getModuleRelations = (row) => ensureUniqueDefectRelationItems(row?.modules || [], 'module')
const getTestcaseRelations = (row) => ensureUniqueDefectRelationItems(row?.related_testcases || [], 'case')
const getTestpointRelations = (row) => ensureUniqueDefectRelationItems(row?.related_testpoints || [], 'testpoint')
const getMindmapRelationTarget = (row) => (
  getTestpointRelations(row)[0] ||
  getTestcaseRelations(row)[0] ||
  getModuleRelations(row)[0] ||
  null
)
const getDefectModuleLabels = (row) => getModuleRelations(row).map(item => item.path || item.short_label).filter(Boolean)
const getDefectTestcaseLabels = (row) => getTestcaseRelations(row).map(item => item.short_label).filter(Boolean)
const getDefectTestpointLabels = (row) => getTestpointRelations(row).map(item => item.short_label).filter(Boolean)
const getDefectProjectName = (row) => row?.project?.name || '-'
const getDefectVersionName = (row) => row?.version?.name || '-'
const getDefectPriority = (row) => getPriorityText(row?.priority)
const getDefectProblemReason = (row) => row?.problem_reason || '-'
const getDefectRootCause = (row) => row?.root_cause || '-'
const getDefectFrontendDeveloper = (row) => row?.frontend_developer || '-'
const getDefectBackendDeveloper = (row) => row?.backend_developer || '-'
const getDefectAssigneeNames = (row) => (
  Array.isArray(row?.assignees)
    ? row.assignees.map(assignee => getUserDisplayName(assignee, `用户${assignee.id}`)).filter(Boolean)
    : []
)
const getDefectCreatorName = (row) => getUserDisplayName(row?.created_by, '-')
const getDefectUpdatedAt = (row) => formatDate(row?.updated_at)
const defectColumnFilters = computed(() => ({
  code: buildTableFilters(defects.value, row => row.code, 20),
  title: buildTableFilters(defects.value, row => row.title, 20),
  priority: buildTableFilters(defects.value, getDefectPriority, 20),
  problem_reason: buildTableFilters(defects.value, getDefectProblemReason, 20),
  root_cause: buildTableFilters(defects.value, getDefectRootCause, 20),
  requirement_id: buildTableFilters(defects.value, row => row.requirement_id, 20),
  frontend_developer: buildTableFilters(defects.value, getDefectFrontendDeveloper, 20),
  backend_developer: buildTableFilters(defects.value, getDefectBackendDeveloper, 20),
  modules: buildTableFilters(defects.value, getDefectModuleLabels, 30),
  related_testcases: buildTableFilters(defects.value, getDefectTestcaseLabels, 30),
  related_testpoints: buildTableFilters(defects.value, getDefectTestpointLabels, 30),
  project: buildTableFilters(defects.value, getDefectProjectName, 20),
  version: buildTableFilters(defects.value, getDefectVersionName, 20),
  severity: buildTableFilters(defects.value, row => getSeverityText(row.severity), 20),
  status: buildTableFilters(defects.value, row => getStatusText(row.status), 20),
  assignees: buildTableFilters(defects.value, getDefectAssigneeNames, 30),
  created_by: buildTableFilters(defects.value, getDefectCreatorName, 20),
  attachments_count: buildTableFilters(defects.value, row => row.attachments_count, 20, compareTableNumber),
  updated_at: buildTableFilters(defects.value, getDefectUpdatedAt, 20),
}))

const loadProjects = async () => {
  try {
    const response = await api.get('/projects/list/')
    projects.value = response.data?.results || response.data || []
  } catch (error) {
    projects.value = []
    ElMessage.error('获取项目列表失败')
  }
}

const loadVersions = async (projectId) => {
  if (!projectId) {
    versions.value = []
    return
  }

  try {
    const response = await api.get(`/versions/projects/${projectId}/versions/`)
    versions.value = response.data || []
  } catch (error) {
    versions.value = []
    ElMessage.error('获取版本列表失败')
  }
}

const loadUsers = async () => {
  try {
    const response = await api.get('/auth/users/', {
      params: { page_size: 500 },
    })
    users.value = response.data?.results || response.data || []
  } catch (error) {
    users.value = []
    ElMessage.error('获取用户列表失败')
  }
}

const resolveAccessibleProjectId = (preferredProjectId) => {
  if (preferredProjectId && projects.value.some(item => String(item.id) === String(preferredProjectId))) {
    return preferredProjectId
  }

  return ''
}

const normalizeEmbeddedCategoryFilter = () => {
  const rawCategoryName = String(props.linkedCategoryName || '').trim()
  const pathSegments = String(props.linkedCategoryPath || '')
    .split(' / ')
    .map(item => item.trim())
    .filter(Boolean)

  if (pathSegments.length <= 1) {
    return {
      categoryName: '',
      categoryPath: '',
    }
  }

  return {
    categoryName: rawCategoryName,
    categoryPath: pathSegments.slice(1).join(' / '),
  }
}

const syncContextFilters = async () => {
  const requestedProjectId = parseNumberQuery(route.query.project_id)
  const linkedProjectId = parseNumberQuery(props.linkedProjectId)
  const requestedVersionId = parseNumberQuery(route.query.version_id)
  const linkedVersionId = parseNumberQuery(props.linkedVersionId)

  filters.projectId = resolveAccessibleProjectId(props.embedded ? linkedProjectId || requestedProjectId : requestedProjectId)
  filters.versionId = props.embedded ? (linkedVersionId || requestedVersionId) : requestedVersionId

  if (filters.projectId) {
    await loadVersions(filters.projectId)
    if (!versions.value.some(item => String(item.id) === String(filters.versionId))) {
      filters.versionId = ''
    }
  } else {
    versions.value = []
    filters.versionId = ''
  }
}

const applyRouteQuery = async () => {
  if (props.embedded) {
    filters.keyword = normalizedLinkedKeyword.value
    filters.testpointId = normalizedLinkedTestpointId.value
    await syncContextFilters()
    return
  }

  filters.code = String(getQueryValue(route.query.code) || '')
  filters.keyword = String(getQueryValue(route.query.keyword) || '')
  filters.testpointId = String(getQueryValue(route.query.testpoint_id) || '')
  filters.status = String(getQueryValue(route.query.status) || '')
  filters.severity = String(getQueryValue(route.query.severity) || '')
  filters.assigneeId = parseNumberQuery(route.query.assignee_id)
  pagination.page = parseNumberQuery(route.query.page, 1)
  pagination.pageSize = parseNumberQuery(route.query.page_size, 10)
  await syncContextFilters()
}

const syncRouteQuery = async () => {
  if (props.embedded) {
    return
  }

  const query = { ...route.query }
  ;['code', 'keyword', 'testpoint_id', 'project_id', 'version_id', 'status', 'severity', 'assignee_id', 'page', 'page_size', 'source', 'tab'].forEach((key) => {
    delete query[key]
  })

  const nextQuery = {
    ...query,
    ...listStateQuery.value,
  }

  if (areQueryObjectsEqual(route.query, nextQuery)) {
    return
  }

  isSyncingRoute.value = true
  try {
    await router.replace({
      path: route.path,
      query: nextQuery,
    })
  } finally {
    isSyncingRoute.value = false
  }
}

const buildRequestParams = () => {
  const searchTerms = [filters.code.trim(), filters.keyword.trim()].filter(Boolean)
  const { categoryName: linkedCategoryName, categoryPath: linkedCategoryPath } = normalizeEmbeddedCategoryFilter()
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: '-updated_at',
  }

  if (searchTerms.length) {
    params.search = searchTerms.join(' ')
  }
  if (filters.projectId) {
    params.project = filters.projectId
  }
  if (filters.testpointId.trim()) {
    params.testpoint_id = filters.testpointId.trim()
  }
  if (filters.versionId) {
    params.version = filters.versionId
  }
  if (filters.status) {
    params.status = filters.status
  }
  if (filters.severity) {
    params.severity = filters.severity
  }
  if (filters.assigneeId) {
    params.assignees = filters.assigneeId
  }
  if (props.embedded && linkedCategoryName) {
    params.module_category_name = linkedCategoryName
  }
  if (props.embedded && linkedCategoryPath) {
    params.module_category_path = linkedCategoryPath
  }

  return params
}

const loadDefects = async () => {
  const requestId = latestLoadRequestId.value + 1
  latestLoadRequestId.value = requestId
  loading.value = true
  try {
    await syncRouteQuery()
    const response = await getTechnicalSolutionDesigns(buildRequestParams())
    if (requestId !== latestLoadRequestId.value) {
      return
    }
    defects.value = response.data?.results || []
    pagination.total = response.data?.count || 0
  } catch (error) {
    if (requestId !== latestLoadRequestId.value) {
      return
    }
    defects.value = []
    pagination.total = 0
    ElMessage.error('获取技术方案设计列表失败')
  } finally {
    if (requestId === latestLoadRequestId.value) {
      loading.value = false
    }
  }
}

const handleProjectChange = async (projectId) => {
  filters.versionId = ''
  await loadVersions(projectId)
}

const handleSearch = async () => {
  pagination.page = 1
  if (props.embedded) {
    await syncContextFilters()
  }
  await loadDefects()
}

const handleReset = async () => {
  filters.code = ''
  filters.keyword = ''
  filters.testpointId = ''
  filters.status = ''
  filters.severity = ''
  filters.assigneeId = ''

  if (!props.embedded) {
    filters.projectId = ''
    filters.versionId = ''
    versions.value = []
  } else {
    await syncContextFilters()
  }

  pagination.page = 1
  pagination.pageSize = 10
  await loadDefects()
}

const clearLinkedContext = async () => {
  if (props.embedded) {
    return
  }

  filters.projectId = ''
  filters.versionId = ''
  versions.value = []
  pagination.page = 1
  await loadDefects()
}

const handleRefresh = async () => {
  if (props.embedded) {
    await syncContextFilters()
  }
  await loadDefects()
}

const resetExcelFileInput = () => {
  if (excelFileInputRef.value) {
    excelFileInputRef.value.value = ''
  }
}

const escapeSummaryHtml = (value) => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const buildImportSummaryHtml = (payload = {}) => {
  const summaryLines = [`成功导入 ${Number(payload.created_count || 0)} 条技术方案设计`]
  const skippedCount = Number(payload.skipped_count || 0)
  if (skippedCount > 0) {
    summaryLines.push(`跳过 ${skippedCount} 条无效记录`)
  }

  const warningItems = Array.isArray(payload.warnings) ? payload.warnings : []
  if (warningItems.length) {
    summaryLines.push('')
    summaryLines.push(`告警 ${warningItems.length} 条：`)
    warningItems.slice(0, 10).forEach((item) => {
      summaryLines.push(`- ${item}`)
    })
    if (warningItems.length > 10) {
      summaryLines.push(`- 其余 ${warningItems.length - 10} 条请按导入结果继续检查`)
    }
  }

  return summaryLines.map(escapeSummaryHtml).join('<br>')
}

const handleImportButtonClick = () => {
  if (!filters.projectId) {
    ElMessage.warning('请先选择所属项目')
    return
  }
  if (!filters.versionId) {
    ElMessage.warning('请先选择关联版本')
    return
  }
  excelFileInputRef.value?.click()
}

const handleImportFileChange = async (event) => {
  const file = event?.target?.files?.[0]
  resetExcelFileInput()
  if (!file) {
    return
  }
  if (!/\.xlsx$/i.test(file.name)) {
    ElMessage.warning('仅支持导入 .xlsx 文件')
    return
  }

  excelImporting.value = true
  try {
    const response = await importTechnicalSolutionDesignExcel({
      projectId: filters.projectId,
      versionId: filters.versionId,
      file,
    })
    await loadDefects()
    ElMessage.success('技术方案设计导入成功')
    await ElMessageBox.alert(buildImportSummaryHtml(response.data), '导入结果', {
      dangerouslyUseHTMLString: true,
    })
  } catch (error) {
    const responseData = error?.response?.data
    const errorMessage = responseData?.detail || Object.values(responseData || {}).flat().find(Boolean)
    ElMessage.error(errorMessage || '导入技术方案设计失败')
  } finally {
    excelImporting.value = false
  }
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  if (props.embedded) {
    await syncContextFilters()
  }
  await loadDefects()
}

const buildDefectRouteQuery = () => {
  const query = {
    ...listStateQuery.value,
    tab: 'technical-solution-designs',
  }
  const categoryId = props.linkedCategoryId || parseNumberQuery(route.query.category_id)

  if (categoryId) {
    query.category_id = String(categoryId)
  }

  return query
}

const goToCreate = () => {
  router.push({
    path: '/manual-testcases/technical-solution-designs/create',
    query: buildDefectRouteQuery(),
  })
}

const goToEdit = (id) => {
  router.push({
    path: `/manual-testcases/technical-solution-designs/${id}/edit`,
    query: buildDefectRouteQuery(),
  })
}

const goBackToManualWorkspace = () => {
  router.push({
    path: '/manual-testcases/list',
    query: manualWorkspaceQuery.value,
  })
}

const jumpToRequirement = (row) => {
  if (!row?.requirement_id) {
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: {
      project_id: String(row?.project?.id || filters.projectId || ''),
      version_id: String(row?.version?.id || filters.versionId || ''),
      tab: 'version-requirements',
      jira_keyword: String(row.requirement_id),
    },
  })
}

const jumpToRelation = (item, defaultNodeType) => {
  const query = buildDefectRelationRouteQuery(item, defaultNodeType)
  if (!query) {
    ElMessage.warning('当前关联缺少脑图定位信息')
    return
  }

  query.from_tab = 'technical-solution-designs'
  query.return_query = encodeURIComponent(JSON.stringify(buildDefectRouteQuery()))

  router.push({
    path: '/manual-testcases/view',
    query,
  })
}

const handleViewMindmap = (row) => {
  const relationItem = getMindmapRelationTarget(row)
  if (!relationItem) {
    ElMessage.warning('当前技术方案设计未关联测试用例或测试点')
    return
  }

  jumpToRelation(relationItem, relationItem.node_type || 'testpoint')
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除技术方案设计“${row.code || row.title}”吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await deleteTechnicalSolutionDesign(row.id)
    ElMessage.success('技术方案设计已删除')

    if (defects.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }

    await loadDefects()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除技术方案设计失败')
    }
  }
}

const initializeList = async () => {
  await applyRouteQuery()
  if (!props.embedded || props.active) {
    await loadDefects()
  }
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadUsers()])
  await initializeList()
})

watch(
  () => route.fullPath,
  async () => {
    if (props.embedded) {
      return
    }
    if (isSyncingRoute.value) {
      return
    }
    await applyRouteQuery()
    await loadDefects()
  }
)

watch(
  () => embeddedContextSignature.value,
  async (nextSignature, previousSignature) => {
    if (!props.embedded || !props.active || nextSignature === previousSignature) {
      return
    }
    pagination.page = 1
    await syncContextFilters()
    await loadDefects()
  }
)

watch(
  () => props.linkedKeyword,
  async (nextKeyword, previousKeyword) => {
    if (!props.embedded || !props.active || String(nextKeyword || '').trim() === String(previousKeyword || '').trim()) {
      return
    }
    filters.keyword = normalizedLinkedKeyword.value
    pagination.page = 1
    await syncContextFilters()
    await loadDefects()
  }
)

watch(
  () => props.linkedTestpointId,
  async (nextTestpointId, previousTestpointId) => {
    if (!props.embedded || !props.active || String(nextTestpointId || '').trim() === String(previousTestpointId || '').trim()) {
      return
    }
    filters.testpointId = normalizedLinkedTestpointId.value
    pagination.page = 1
    await syncContextFilters()
    await loadDefects()
  }
)

watch(
  () => props.active,
  async (active) => {
    if (!props.embedded || !active) {
      return
    }
    filters.keyword = normalizedLinkedKeyword.value
    filters.testpointId = normalizedLinkedTestpointId.value
    await syncContextFilters()
    await loadDefects()
  }
)
</script>

<style lang="scss" scoped>
.defect-list-page {
  flex: 1 1 0;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .page-header {
    margin-bottom: 0;
  }

  .header-title {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .page-subtitle {
    margin: 0;
    color: #606266;
    line-height: 1.6;
  }

  .header-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
}

.defect-list-page--embedded {
  padding: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.context-tags,
.relation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.excel-import-input {
  display: none;
}

.defect-list-panel {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.defect-table {
  flex: 1 1 0;
  min-height: 0;
}

.defect-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.search-form {
  margin: 0;
  flex: 1;
}

.defect-search-form {
  min-width: min(100%, 720px);
}

:deep(.defect-search-form .el-form-item) {
  margin-bottom: 0;
}

.defect-toolbar-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  margin-left: auto;
}

.defect-toolbar-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.relation-tag {
  cursor: pointer;
}

.empty-text {
  color: #909399;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: nowrap;
  width: 100%;
  white-space: nowrap;
}

.row-actions :deep(.el-button) {
  margin-left: 0;
}

.tab-pagination {
  margin-top: auto;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .tab-toolbar,
  .defect-toolbar-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .defect-toolbar-buttons {
    justify-content: flex-start;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
