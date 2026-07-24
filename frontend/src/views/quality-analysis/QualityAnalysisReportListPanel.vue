<template>
  <div class="page-container report-list-page">
    <div class="tab-panel report-list-panel">
      <div class="tab-toolbar">
        <el-form :inline="true" :model="filters" class="search-form report-search-form">
          <el-form-item label="关键词">
            <el-input
              v-model="filters.keyword"
              clearable
              placeholder="版本号或文件名"
              style="width: 220px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item v-if="!useLinkedVersion" label="版本号">
            <el-select
              v-model="filters.version"
              clearable
              filterable
              placeholder="全部版本"
              style="width: 180px"
            >
              <el-option
                v-for="version in versionOptions"
                :key="version"
                :label="version"
                :value="version"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="filters.status"
              clearable
              placeholder="全部状态"
              style="width: 150px"
            >
              <el-option
                v-for="option in statusOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
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

        <div class="report-toolbar-buttons">
          <div class="report-toolbar-stats">
            <el-tag effect="plain">报告 {{ filteredReports.length }}</el-tag>
            <el-tag effect="plain" type="success">已完成 {{ completedCount }}</el-tag>
            <el-tag effect="plain" type="warning">分析中 {{ analyzingCount }}</el-tag>
            <el-tag effect="plain" type="danger">失败 {{ failedCount }}</el-tag>
            <el-tag v-if="useLinkedVersion && linkedVersionLabel" effect="plain" type="info">
              当前版本 {{ linkedVersionLabel }}
            </el-tag>
          </div>
          <div class="report-toolbar-buttons">
            <TableColumnSettings
              :table-ref="reportTableRef"
              storage-key="manual-testcases.quality-report-list"
            />
            <el-button @click="loadReports" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </div>

      <el-table
        ref="reportTableRef"
        v-loading="loading"
        :data="pagedReports"
        stripe
        row-key="id"
        class="reports-table"
        :max-height="reportTableMaxHeight"
        style="width: 100%"
        empty-text="暂无报告数据"
      >
        <el-table-column
          v-if="!useLinkedVersion"
          prop="version"
          label="版本号"
          min-width="160"
          sortable
          :sort-method="createTextSorter(row => row.version)"
          :filters="reportColumnFilters.version"
          :filter-method="createTableFilter(row => row.version)"
        />
        <el-table-column
          label="状态"
          width="120"
          sortable
          :sort-method="createTextSorter(getReportStatusLabel)"
          :filters="reportColumnFilters.status"
          :filter-method="createTableFilter(getReportStatusLabel)"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="缺陷数"
          width="100"
          align="center"
          sortable
          :sort-method="createNumberSorter(row => row.total_defects)"
          :filters="reportColumnFilters.total_defects"
          :filter-method="createTableFilter(row => row.total_defects)"
        >
          <template #default="{ row }">{{ row.total_defects || '-' }}</template>
        </el-table-column>
        <el-table-column
          label="已分类"
          width="100"
          align="center"
          sortable
          :sort-method="createNumberSorter(row => row.classified_defects)"
          :filters="reportColumnFilters.classified_defects"
          :filter-method="createTableFilter(row => row.classified_defects)"
        >
          <template #default="{ row }">{{ row.classified_defects || '-' }}</template>
        </el-table-column>
        <el-table-column
          label="缺陷文件"
          min-width="220"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.source_excel_name)"
          :filters="reportColumnFilters.source_excel_name"
          :filter-method="createTableFilter(row => row.source_excel_name)"
        >
          <template #default="{ row }">{{ row.source_excel_name || '-' }}</template>
        </el-table-column>
        <el-table-column
          label="需求清单"
          min-width="180"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.requirement_excel_name)"
          :filters="reportColumnFilters.requirement_excel_name"
          :filter-method="createTableFilter(row => row.requirement_excel_name)"
        >
          <template #default="{ row }">{{ row.requirement_excel_name || '未上传' }}</template>
        </el-table-column>
        <el-table-column
          label="测试用例统计"
          min-width="180"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.testcase_excel_name)"
          :filters="reportColumnFilters.testcase_excel_name"
          :filter-method="createTableFilter(row => row.testcase_excel_name)"
        >
          <template #default="{ row }">{{ row.testcase_excel_name || '未上传' }}</template>
        </el-table-column>
        <el-table-column
          label="创建时间"
          min-width="180"
          sortable
          :sort-method="createDateSorter(row => row.created_at)"
          :filters="reportColumnFilters.created_at"
          :filter-method="createTableFilter(getReportCreatedAt)"
        >
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button
                v-if="!useLinkedVersion"
                size="small"
                type="primary"
                plain
                @click="analyze(row)"
                :disabled="row.status === 'analyzing' || row.status === 'completed'"
              >
                {{ row.status === 'completed' ? '已完成' : '开始分析' }}
              </el-button>
              <el-button size="small" @click="openDetail(row)" :disabled="useLinkedVersion ? false : row.status !== 'completed'">
                查看详情
              </el-button>
              <el-button v-if="!useLinkedVersion" size="small" @click="shareReport(row)" :disabled="row.status !== 'completed'">
                分享
              </el-button>
              <el-button v-if="!useLinkedVersion" size="small" type="danger" plain @click="deleteReport(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="report-footer">
        <div class="report-toolbar-stats">
          <el-tag effect="plain">报告 {{ filteredReports.length }}</el-tag>
          <el-tag effect="plain" type="success">已完成 {{ completedCount }}</el-tag>
          <el-tag effect="plain" type="warning">分析中 {{ analyzingCount }}</el-tag>
          <el-tag effect="plain" type="danger">失败 {{ failedCount }}</el-tag>
          <el-tag v-if="useLinkedVersion && linkedVersionLabel" effect="plain" type="info">
            当前版本 {{ linkedVersionLabel }}
          </el-tag>
        </div>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredReports.length"
          class="tab-pagination"
          @size-change="handlePageSizeChange"
          @current-change="handleCurrentPageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import api from '@/utils/api'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import {
  buildTableFilters,
  compareTableNumber,
  createDateSorter,
  createNumberSorter,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
  detailViewMode: {
    type: String,
    default: 'window',
  },
  detailRouteName: {
    type: String,
    default: 'ManualTestCaseList',
  },
  detailQuery: {
    type: Object,
    default: () => ({
      tab: 'quality-report-live',
    }),
  },
  useLinkedVersion: {
    type: Boolean,
    default: false,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
  linkedProjectId: {
    type: [Number, String],
    default: null,
  },
})

const router = useRouter()

const reports = ref([])
const reportTableRef = ref(null)
const loading = ref(false)

const filters = reactive({
  keyword: '',
  status: '',
  version: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
})

const statusOptions = [
  { label: '已上传', value: 'uploaded' },
  { label: '分析中', value: 'analyzing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const normalizeVersion = value => String(value || '').trim()
const normalizeText = value => String(value || '').trim()

const effectiveLinkedVersion = computed(() => normalizeVersion(props.linkedVersion))
const effectiveLinkedProjectId = computed(() => {
  const parsedValue = Number(props.linkedProjectId)
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null
})
const linkedVersionLabel = computed(() => effectiveLinkedVersion.value || '')
const reportTableMaxHeight = computed(() => (props.useLinkedVersion ? 'calc(100vh - 320px)' : 'calc(100vh - 360px)'))
const getReportStatusLabel = row => row?.status_display || '-'
const getReportCreatedAt = row => formatDate(row?.created_at)

const versionOptions = computed(() => (
  [...new Set(
    reports.value
      .map(item => normalizeVersion(item?.version))
      .filter(Boolean)
  )]
))

const filteredReports = computed(() => {
  let nextReports = [...reports.value]

  if (props.useLinkedVersion && effectiveLinkedVersion.value) {
    nextReports = nextReports.filter(item => normalizeVersion(item?.version) === effectiveLinkedVersion.value)
  } else if (filters.version) {
    nextReports = nextReports.filter(item => normalizeVersion(item?.version) === filters.version)
  }

  if (filters.status) {
    nextReports = nextReports.filter(item => normalizeText(item?.status) === filters.status)
  }

  const keyword = normalizeText(filters.keyword).toLowerCase()
  if (keyword) {
    nextReports = nextReports.filter(item => (
      [
        item?.version,
        item?.project_name,
        item?.source_excel_name,
        item?.requirement_excel_name,
        item?.testcase_excel_name,
      ]
        .map(value => normalizeText(value).toLowerCase())
        .some(value => value.includes(keyword))
    ))
  }

  return nextReports
})

const pagedReports = computed(() => {
  const startIndex = (pagination.page - 1) * pagination.pageSize
  const endIndex = startIndex + pagination.pageSize
  return filteredReports.value.slice(startIndex, endIndex)
})

const completedCount = computed(() => filteredReports.value.filter(item => item.status === 'completed').length)
const analyzingCount = computed(() => filteredReports.value.filter(item => item.status === 'analyzing').length)
const failedCount = computed(() => filteredReports.value.filter(item => item.status === 'failed').length)
const reportColumnFilters = computed(() => ({
  version: buildTableFilters(filteredReports.value, row => row.version, 20),
  status: buildTableFilters(filteredReports.value, getReportStatusLabel, 20),
  total_defects: buildTableFilters(filteredReports.value, row => row.total_defects, 20, compareTableNumber),
  classified_defects: buildTableFilters(filteredReports.value, row => row.classified_defects, 20, compareTableNumber),
  source_excel_name: buildTableFilters(filteredReports.value, row => row.source_excel_name, 20),
  requirement_excel_name: buildTableFilters(filteredReports.value, row => row.requirement_excel_name, 20),
  testcase_excel_name: buildTableFilters(filteredReports.value, row => row.testcase_excel_name, 20),
  created_at: buildTableFilters(filteredReports.value, getReportCreatedAt, 20),
}))

const ensureValidPage = () => {
  const pageCount = Math.max(1, Math.ceil(filteredReports.value.length / pagination.pageSize))
  if (pagination.page > pageCount) {
    pagination.page = pageCount
  }
}

const resetPagination = () => {
  pagination.page = 1
}

const buildReportListParams = () => {
  if (!props.useLinkedVersion || !effectiveLinkedVersion.value) {
    return {}
  }

  return {
    version: effectiveLinkedVersion.value,
  }
}

const buildLiveReportParams = () => {
  if (!effectiveLinkedVersion.value) {
    return null
  }

  return {
    version: effectiveLinkedVersion.value,
    ...(effectiveLinkedProjectId.value ? { project_id: effectiveLinkedProjectId.value } : {}),
  }
}

const loadReports = async () => {
  loading.value = true
  try {
    if (props.useLinkedVersion) {
      const params = buildLiveReportParams()
      if (!params) {
        reports.value = []
        ensureValidPage()
        return
      }

      const response = await api.get('/quality-analysis/reports/live-snapshot/', {
        params,
      })
      reports.value = response.data ? [response.data] : []
    } else {
      const response = await api.get('/quality-analysis/reports/', {
        params: buildReportListParams(),
      })
      reports.value = response.data.results || response.data || []
    }

    ensureValidPage()
  } catch (error) {
    reports.value = []
    ensureValidPage()
    ElMessage.error(error.response?.data?.detail || error.message || '获取报告列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  resetPagination()
}

const handleReset = () => {
  filters.keyword = ''
  filters.status = ''
  filters.version = ''
  pagination.page = 1
  pagination.pageSize = 10
}

const handlePageSizeChange = () => {
  pagination.page = 1
}

const handleCurrentPageChange = () => {}

const analyze = async report => {
  try {
    await ElMessageBox.confirm(`确认开始分析版本 ${report.version} 吗？`, '开始分析', {
      type: 'warning',
    })
    await api.post(`/quality-analysis/reports/${report.id}/analyze/`)
    ElMessage.success('分析任务执行完成')
    await loadReports()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error
    }
  }
}

const openDetail = report => {
  const target = {
    name: props.detailRouteName,
    query: props.useLinkedVersion
      ? {
          ...props.detailQuery,
        }
      : {
          ...props.detailQuery,
          reportId: String(report.id),
        },
  }

  if (props.detailViewMode === 'route') {
    router.push(target)
    return
  }

  const routeData = router.resolve(target)
  window.open(routeData.href, '_blank')
}

const copyText = async text => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

const shareReport = async report => {
  const response = await api.post(`/quality-analysis/reports/${report.id}/share/`)
  const routeData = router.resolve({
    name: 'QualityAnalysisShare',
    params: { token: response.data.share_token },
  })
  const shareUrl = `${window.location.origin}${routeData.href}`
  await copyText(shareUrl)
  ElMessage.success('分享链接已复制到剪贴板')
}

const deleteReport = async report => {
  try {
    await ElMessageBox.confirm(`确认删除报告 ${report.version} 吗？`, '删除确认', {
      type: 'warning',
    })
    await api.delete(`/quality-analysis/reports/${report.id}/`)
    ElMessage.success('报告已删除')
    await loadReports()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error
    }
  }
}

const statusTagType = status => {
  const map = {
    uploaded: 'info',
    analyzing: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const formatDate = dateTime => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

watch(
  () => filteredReports.value.length,
  () => {
    ensureValidPage()
  }
)

watch(
  () => props.active,
  async active => {
    if (active) {
      resetPagination()
      await loadReports()
    }
  }
)

watch(
  () => [props.linkedVersion, props.linkedProjectId],
  async ([nextVersion, nextProjectId], [previousVersion, previousProjectId]) => {
    if (
      !props.useLinkedVersion ||
      (
        normalizeVersion(nextVersion) === normalizeVersion(previousVersion) &&
        normalizeText(nextProjectId) === normalizeText(previousProjectId)
      ) ||
      !props.active
    ) {
      return
    }

    resetPagination()
    await loadReports()
  }
)

onMounted(async () => {
  if (props.active) {
    await loadReports()
  }
})
</script>

<style scoped lang="scss">
.report-list-page {
  flex: 1 1 0;
  min-height: 100%;
  height: 100%;
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-list-panel {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
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

.report-search-form {
  min-width: min(100%, 720px);
}

:deep(.report-search-form .el-form-item) {
  margin-bottom: 0;
}

.report-toolbar-stats,
.report-toolbar-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.tab-toolbar > .report-toolbar-buttons {
  margin-left: auto;
}

.tab-toolbar > .report-toolbar-buttons > .report-toolbar-stats {
  display: none;
}

.reports-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.reports-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-group :deep(.el-button) {
  margin-left: 0;
}

.report-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.report-footer .report-toolbar-stats {
  justify-content: flex-start;
}

.tab-pagination {
  margin-top: 0;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .tab-toolbar,
  .report-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .report-toolbar-stats,
  .report-toolbar-buttons {
    justify-content: flex-start;
  }

  .tab-pagination {
    justify-content: flex-start;
  }
}
</style>
