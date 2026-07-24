<template>
  <div
    class="research-progress-page"
    :class="{ 'research-progress-page--embedded': embedded }"
  >
    <div class="research-progress-panel" v-loading="loading">
      <el-empty
        v-if="!normalizedLinkedVersion"
        description="请选择版本号后查看研发进展"
      />

      <template v-else>
        <div class="overview-toolbar">
          <el-form :inline="true" :model="filters" class="search-form">
            <el-form-item label="需求编号">
              <el-input
                v-model="filters.requirementKey"
                clearable
                placeholder="需求编号"
                style="width: 150px"
              />
            </el-form-item>
            <el-form-item label="需求标题">
              <el-input
                v-model="filters.requirementTitle"
                clearable
                placeholder="需求标题"
                style="width: 220px"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="filters.status"
                clearable
                filterable
                placeholder="状态"
                style="width: 140px"
              >
                <el-option
                  v-for="item in filterOptions.status"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="模块">
              <el-select
                v-model="filters.module"
                clearable
                filterable
                placeholder="模块"
                style="width: 180px"
              >
                <el-option
                  v-for="item in filterOptions.module"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="组别">
              <el-select
                v-model="filters.groupName"
                clearable
                filterable
                placeholder="组别"
                style="width: 150px"
              >
                <el-option
                  v-for="item in filterOptions.groupName"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="PM">
              <el-select
                v-model="filters.pm"
                clearable
                filterable
                placeholder="PM"
                style="width: 140px"
              >
                <el-option
                  v-for="item in filterOptions.pm"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="前端">
              <el-select
                v-model="filters.frontendDeveloper"
                clearable
                filterable
                placeholder="前端"
                style="width: 140px"
              >
                <el-option
                  v-for="item in filterOptions.frontendDeveloper"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="后端">
              <el-select
                v-model="filters.backendDeveloper"
                clearable
                filterable
                placeholder="后端"
                style="width: 140px"
              >
                <el-option
                  v-for="item in filterOptions.backendDeveloper"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="测试人员">
              <el-select
                v-model="filters.tester"
                clearable
                filterable
                placeholder="测试人员"
                style="width: 150px"
              >
                <el-option
                  v-for="item in filterOptions.tester"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button @click="resetFilters">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="table-panel">
          <el-table
            :data="filteredRows"
            stripe
            class="records-table"
            :max-height="tableMaxHeight"
            row-key="id"
            empty-text="当前版本暂无可展示的研发进展数据"
          >
            <el-table-column label="需求编号" min-width="140" fixed="left" sortable>
              <template #default="{ row }">
                <a
                  v-if="row.requirement_key && row.requirement_url"
                  :href="row.requirement_url"
                  class="jira-link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ row.requirement_key }}
                </a>
                <span v-else>{{ formatCell(row.requirement_key) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="requirement_title" label="需求标题" min-width="280" sortable show-overflow-tooltip />
            <el-table-column prop="customer_name" label="客户或项目名称" min-width="160" sortable show-overflow-tooltip />
            <el-table-column prop="priority" label="版本内研发优先级别" min-width="150" sortable show-overflow-tooltip />
            <el-table-column prop="status" label="状态" min-width="120" sortable show-overflow-tooltip />
            <el-table-column prop="module" label="模块" min-width="180" sortable show-overflow-tooltip />
            <el-table-column prop="group_name" label="组别" min-width="120" sortable show-overflow-tooltip />
            <el-table-column prop="pm" label="PM" min-width="120" sortable show-overflow-tooltip />
            <el-table-column prop="frontend_developer" label="前端" min-width="120" sortable show-overflow-tooltip />
            <el-table-column prop="backend_developer" label="后端" min-width="120" sortable show-overflow-tooltip />
            <el-table-column prop="tester" label="测试人员" min-width="120" sortable show-overflow-tooltip />
            <el-table-column
              label="自测测试点"
              min-width="210"
              align="center"
              sortable
              :sort-method="createCountSorter(row => row.dev_self_test_count)"
            >
              <template #default="{ row }">
                <StatusCountTags :counts="row.dev_self_test_count" />
              </template>
            </el-table-column>
            <el-table-column label="测试脑图ID" min-width="140" align="center">
              <template #default="{ row }">
                <div v-if="row.mindmaps?.length" class="mindmap-id-list">
                  <el-button
                    v-for="mindmap in row.mindmaps"
                    :key="mindmap.id"
                    link
                    type="primary"
                    @click="jumpToMindmap(mindmap.id)"
                  >
                    {{ mindmap.id }}
                  </el-button>
                </div>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column
              label="测试用例数"
              min-width="210"
              align="center"
              sortable
              :sort-method="createCountSorter(row => row.case_count)"
            >
              <template #default="{ row }">
                <StatusCountTags :counts="row.case_count" />
              </template>
            </el-table-column>
            <el-table-column
              label="测试点数"
              min-width="210"
              align="center"
              sortable
              :sort-method="createCountSorter(row => row.testpoint_count)"
            >
              <template #default="{ row }">
                <StatusCountTags :counts="row.testpoint_count" />
              </template>
            </el-table-column>
            <el-table-column
              label="评审测试点数"
              min-width="130"
              align="center"
              sortable
              :sort-method="(left, right) => getReviewCountTotal(left.review_testpoint_count) - getReviewCountTotal(right.review_testpoint_count)"
            >
              <template #default="{ row }">
                {{ formatReviewCount(row.review_testpoint_count) }}
              </template>
            </el-table-column>
            <el-table-column
              label="版本缺陷"
              min-width="240"
              align="center"
              sortable
              :sort-method="createDefectCountSorter(row => row.version_defect_count)"
            >
              <template #default="{ row }">
                <DefectCountTags :items="row.version_defect_count" />
              </template>
            </el-table-column>
            <el-table-column
              label="线上缺陷"
              min-width="240"
              align="center"
              fixed="right"
              sortable
              :sort-method="createDefectCountSorter(row => row.online_defect_count)"
            >
              <template #default="{ row }">
                <DefectCountTags :items="row.online_defect_count" />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, reactive, ref, watch } from 'vue'
import { ElMessage, ElTag } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  active: {
    type: Boolean,
    default: true,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
  linkedProjectId: {
    type: [Number, String, null],
    default: null,
  },
})

const emit = defineEmits(['summary-change'])

const RECORD_ENDPOINT = '/quality-analysis/reports/live-rd-progress-overview/'
const STATUS_ORDER = ['not_run', 'pass', 'fail', 'block', 'not_test']
const STATUS_META = Object.freeze({
  not_run: { label: '未执行', type: 'info' },
  pass: { label: '通过', type: 'success' },
  fail: { label: '失败', type: 'danger' },
  block: { label: '阻塞', type: 'warning' },
  not_test: { label: '本版本不测', type: 'info' },
})
const DEFECT_STATUS_TYPE = Object.freeze({
  new: 'danger',
  in_progress: 'warning',
  reopened: 'warning',
  resolved: 'success',
  closed: 'success',
  rejected: 'info',
  invalid: 'info',
})

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const rows = ref([])
const scope = ref(null)
const filters = reactive({
  requirementKey: '',
  requirementTitle: '',
  status: '',
  module: '',
  groupName: '',
  pm: '',
  frontendDeveloper: '',
  backendDeveloper: '',
  tester: '',
})

const normalizeText = value => String(value ?? '').trim()
const normalizeSearchText = value => normalizeText(value).toLocaleLowerCase()
const normalizedLinkedVersion = computed(() => normalizeText(props.linkedVersion))
const normalizedLinkedProjectId = computed(() => {
  const parsedValue = Number(props.linkedProjectId)
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null
})
const tableMaxHeight = 'calc(100vh - 308px)'

const normalizeStatusCounts = counts => {
  if (typeof counts === 'number') {
    return { not_run: counts, pass: 0, fail: 0, block: 0, not_test: 0 }
  }

  const source = counts && typeof counts === 'object' ? counts : {}
  return STATUS_ORDER.reduce((result, statusKey) => {
    result[statusKey] = Number(source[statusKey]) || 0
    return result
  }, {})
}

const normalizeDefectCountItems = items => (
  (Array.isArray(items) ? items : [])
    .map(item => ({
      key: normalizeText(item?.key || item?.label) || 'unknown',
      label: normalizeText(item?.label || item?.key) || '未填写',
      count: Number(item?.count) || 0,
    }))
    .filter(item => item.count > 0)
)

const getStatusCountTotal = counts => (
  STATUS_ORDER.reduce((sum, statusKey) => sum + (Number(counts?.[statusKey]) || 0), 0)
)
const getDefectCountTotal = items => (
  (Array.isArray(items) ? items : []).reduce((sum, item) => sum + (Number(item?.count) || 0), 0)
)
const getReviewCountTotal = counts => Number(counts?.total) || 0

const formatCell = value => normalizeText(value) || '-'
const formatReviewCount = counts => {
  const total = getReviewCountTotal(counts)
  const unprocessed = Number(counts?.unprocessed) || 0
  return total ? `${unprocessed}/${total}` : '0'
}

const buildFilterOptions = fieldName => (
  [...new Set(rows.value.map(row => normalizeText(row[fieldName])).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
)

const filterOptions = computed(() => ({
  status: buildFilterOptions('status'),
  module: buildFilterOptions('module'),
  groupName: buildFilterOptions('group_name'),
  pm: buildFilterOptions('pm'),
  frontendDeveloper: buildFilterOptions('frontend_developer'),
  backendDeveloper: buildFilterOptions('backend_developer'),
  tester: buildFilterOptions('tester'),
}))

const matchesKeyword = (value, keyword) => {
  const normalizedKeyword = normalizeSearchText(keyword)
  if (!normalizedKeyword) {
    return true
  }
  return normalizeSearchText(value).includes(normalizedKeyword)
}

const matchesExact = (value, expectedValue) => {
  const normalizedExpectedValue = normalizeText(expectedValue)
  if (!normalizedExpectedValue) {
    return true
  }
  return normalizeText(value) === normalizedExpectedValue
}

const filteredRows = computed(() => rows.value.filter(row => (
  matchesKeyword(row.requirement_key, filters.requirementKey) &&
  matchesKeyword(row.requirement_title, filters.requirementTitle) &&
  matchesExact(row.status, filters.status) &&
  matchesExact(row.module, filters.module) &&
  matchesExact(row.group_name, filters.groupName) &&
  matchesExact(row.pm, filters.pm) &&
  matchesExact(row.frontend_developer, filters.frontendDeveloper) &&
  matchesExact(row.backend_developer, filters.backendDeveloper) &&
  matchesExact(row.tester, filters.tester)
)))

const emptyStatusCounts = () => ({ not_run: 0, pass: 0, fail: 0, block: 0, not_test: 0 })

const aggregateStatusCounts = fieldName => rows.value.reduce((result, row) => {
  const counts = normalizeStatusCounts(row[fieldName])
  STATUS_ORDER.forEach(statusKey => {
    result[statusKey] += counts[statusKey]
  })
  return result
}, emptyStatusCounts())

const aggregateDefectCountItems = fieldName => {
  const itemMap = new Map()
  rows.value.forEach(row => {
    normalizeDefectCountItems(row[fieldName]).forEach(item => {
      const existing = itemMap.get(item.key) || { ...item, count: 0 }
      existing.count += item.count
      itemMap.set(item.key, existing)
    })
  })
  return [...itemMap.values()].filter(item => item.count > 0)
}

const aggregateRequirementCountItems = () => {
  const itemMap = new Map()
  rows.value.forEach(row => {
    const statusKey = normalizeText(row.status) || 'unknown'
    const existing = itemMap.get(statusKey) || {
      key: statusKey,
      label: statusKey === 'unknown' ? '未填写' : statusKey,
      count: 0,
    }
    existing.count += 1
    itemMap.set(statusKey, existing)
  })
  return [...itemMap.values()]
    .filter(item => item.count > 0)
    .sort((left, right) => left.label.localeCompare(right.label, 'zh-CN'))
}

const sumStatusCountTotal = counts => STATUS_ORDER.reduce((sum, statusKey) => (
  sum + (Number(counts?.[statusKey]) || 0)
), 0)
const sumCountItemsTotal = items => normalizeDefectCountItems(items).reduce((sum, item) => sum + item.count, 0)

const summaryPayload = computed(() => {
  const summary = scope.value?.summary || {}
  const requirementCount = normalizeDefectCountItems(summary.requirement_count || aggregateRequirementCountItems())
  const devSelfTestCount = normalizeStatusCounts(summary.dev_self_test_count || aggregateStatusCounts('dev_self_test_count'))
  const testpointCount = normalizeStatusCounts(summary.testpoint_count || aggregateStatusCounts('testpoint_count'))
  const versionDefectCount = normalizeDefectCountItems(summary.version_defect_count || aggregateDefectCountItems('version_defect_count'))
  const onlineDefectCount = normalizeDefectCountItems(summary.online_defect_count || aggregateDefectCountItems('online_defect_count'))
  return {
    requirement_count: requirementCount,
    requirement_count_total: Number(summary.requirement_count_total) || sumCountItemsTotal(requirementCount),
    dev_self_test_count: devSelfTestCount,
    dev_self_test_count_total: Number(summary.dev_self_test_count_total) || sumStatusCountTotal(devSelfTestCount),
    testpoint_count: testpointCount,
    testpoint_count_total: Number(summary.testpoint_count_total) || sumStatusCountTotal(testpointCount),
    version_defect_count: versionDefectCount,
    version_defect_count_total: Number(summary.version_defect_count_total) || sumCountItemsTotal(versionDefectCount),
    online_defect_count: onlineDefectCount,
    online_defect_count_total: Number(summary.online_defect_count_total) || sumCountItemsTotal(onlineDefectCount),
  }
})

const StatusCountTags = defineComponent({
  name: 'StatusCountTags',
  props: {
    counts: {
      type: Object,
      default: () => ({}),
    },
  },
  setup(componentProps) {
    return () => {
      const normalizedCounts = normalizeStatusCounts(componentProps.counts)
      const tags = STATUS_ORDER
        .filter(statusKey => normalizedCounts[statusKey])
        .map(statusKey => h(
          ElTag,
          {
            key: statusKey,
            type: STATUS_META[statusKey].type,
            size: 'small',
          },
          () => `${STATUS_META[statusKey].label}:${normalizedCounts[statusKey]}`
        ))

      return h('div', { class: 'status-tags' }, tags.length ? tags : [h('span', '0')])
    }
  },
})

const DefectCountTags = defineComponent({
  name: 'DefectCountTags',
  props: {
    items: {
      type: Array,
      default: () => [],
    },
  },
  setup(componentProps) {
    return () => {
      const tags = normalizeDefectCountItems(componentProps.items)
        .map(item => h(
          ElTag,
          {
            key: item.key || item.label,
            type: DEFECT_STATUS_TYPE[item.key] || '',
            size: 'small',
          },
          () => `${item.label || item.key}:${Number(item.count) || 0}`
        ))

      return h('div', { class: 'status-tags' }, tags.length ? tags : [h('span', '0')])
    }
  },
})

const createCountSorter = resolver => (left, right) => getStatusCountTotal(resolver(left)) - getStatusCountTotal(resolver(right))
const createDefectCountSorter = resolver => (left, right) => getDefectCountTotal(resolver(left)) - getDefectCountTotal(resolver(right))

const resetFilters = () => {
  Object.keys(filters).forEach(key => {
    filters[key] = ''
  })
}

const loadRows = async () => {
  if (!props.active) {
    return
  }

  if (!normalizedLinkedVersion.value) {
    rows.value = []
    scope.value = null
    return
  }

  loading.value = true
  try {
    const response = await api.get(RECORD_ENDPOINT, {
      params: {
        version: normalizedLinkedVersion.value,
        project_id: normalizedLinkedProjectId.value || undefined,
      },
    })
    rows.value = (Array.isArray(response.data?.rows) ? response.data.rows : []).map(row => ({
      ...row,
      dev_self_test_count: normalizeStatusCounts(row.dev_self_test_count),
      case_count: normalizeStatusCounts(row.case_count),
      testpoint_count: normalizeStatusCounts(row.testpoint_count),
      mindmaps: Array.isArray(row.mindmaps) ? row.mindmaps : [],
      version_defect_count: normalizeDefectCountItems(row.version_defect_count),
      online_defect_count: normalizeDefectCountItems(row.online_defect_count),
    }))
    scope.value = response.data || null
  } catch (error) {
    rows.value = []
    scope.value = null
    ElMessage.error(`加载研发进展总览失败：${error.response?.data?.detail || error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

const jumpToMindmap = mindmapId => {
  const normalizedMindmapId = normalizeText(mindmapId)
  if (!normalizedMindmapId) {
    ElMessage.warning('测试脑图ID为空')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: {
      ...route.query,
      tab: 'mindmaps',
      mindmap_id: normalizedMindmapId,
    },
  })
}

watch(
  [
    () => props.active,
    () => normalizedLinkedVersion.value,
    () => normalizedLinkedProjectId.value,
  ],
  async ([active]) => {
    if (active) {
      await loadRows()
    }
  },
  { immediate: true }
)

watch(
  summaryPayload,
  value => {
    emit('summary-change', props.active ? value : null)
  },
  { immediate: true, deep: true }
)
</script>

<style scoped lang="scss">
.research-progress-page {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.research-progress-page--embedded {
  height: 100%;
}

.research-progress-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
  background: transparent;
  overflow: hidden;
}

.overview-toolbar {
  position: sticky;
  top: 0;
  z-index: 15;
  padding-bottom: 0;
  background: rgba(255, 255, 255, 0.92);
}

.search-form {
  margin: 0;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.table-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 24px;
  box-shadow: 0 18px 38px rgba(15, 45, 68, 0.08);
}

.records-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.records-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.records-table :deep(.el-table__header-wrapper .cell) {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  white-space: nowrap;
  word-break: keep-all;
}

.jira-link {
  color: #0f6dba;
  text-decoration: none;
  font-weight: 500;
}

.jira-link:hover {
  text-decoration: underline;
}

.mindmap-id-list {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
}

@media (max-width: 768px) {
  .research-progress-panel {
    padding: 12px;
  }
}
</style>
