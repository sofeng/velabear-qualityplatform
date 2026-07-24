<template>
  <div class="quality-detail-page" :class="{ 'quality-detail-page--embedded': embedded }">
    <div v-if="showTopBar" class="top-bar" :class="{ 'top-bar--compact': isCompactHeader }">
      <div v-if="!isCompactHeader" class="top-bar-info">
        <el-button v-if="showBackButton" text @click="handleBack">返回报告列表</el-button>
      </div>

      <div class="top-actions" :class="{ 'top-actions--compact': isCompactHeader }">
        <div v-if="!isCompactHeader && report" class="inline-meta">
          <span>创建时间：{{ formatDate(report.created_at) }}</span>
          <span>分析完成：{{ formatDate(report.analyzed_at) }}</span>
        </div>

        <div v-if="!isCompactHeader && useLinkedVersion" class="linked-version-chip">
          关联版本：{{ linkedVersionLabel }}
        </div>

        <div v-else-if="!isCompactHeader" class="report-switcher">
          <el-select
            v-model="selectedReportId"
            filterable
            placeholder="选择版本号"
            :loading="listLoading"
            style="width: 280px"
            @change="handleReportChange"
          >
            <el-option
              v-for="item in selectableReports"
              :key="item.id"
              :label="item.version"
              :value="item.id"
            >
              <div class="report-option">
                <span>{{ item.version }}</span>
                <span>{{ item.status_display }}</span>
              </div>
            </el-option>
          </el-select>
        </div>

        <div v-if="showLiveHeaderCopy" class="live-header-copy">
          <h2>版本实时质量分析</h2>
          <p>基于当前平台版本下的需求、自测、脑图资产、版本缺陷与线上缺陷数据进行多维深度分析。</p>
        </div>

        <div v-if="showLiveScopeMeta" class="live-scope-meta">
          <div
            v-for="item in liveScopeItems"
            :key="item.key"
            class="live-scope-chip"
          >
            <span class="live-scope-chip__label">{{ item.label }}</span>
            <strong class="live-scope-chip__value">{{ item.value }}</strong>
          </div>
        </div>

        <div class="top-actions__buttons">
          <el-button :disabled="!report || report.status !== 'completed'" @click="shareReport">复制分享链接</el-button>
          <el-button type="primary" :disabled="!canRefreshCurrentReport" @click="refreshCurrentReport">刷新数据</el-button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="state-card">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="state-card error">
      <h2>加载失败</h2>
      <p>{{ error }}</p>
    </div>

    <template v-else-if="report">
      <div v-if="report.status !== 'completed'" class="state-card">
        <h2>报告尚未完成分析</h2>
        <p>当前报告还没有进入可视化阶段，请先回到报告列表完成分析后再查看图表。</p>
      </div>

      <template v-else>
        <el-tabs
          v-model="detailTab"
          class="detail-tabs"
          :class="{ 'detail-tabs--header-hidden': hideDetailTabs }"
        >
          <el-tab-pane label="实时质量分析" name="live">
            <section class="chart-section">
              <QualityAnalysisVersionLivePanel
                :report-id="liveReportId"
                :report-version="liveReportVersion"
                :linked-project-id="linkedProjectId"
                :active="active && detailTab === 'live'"
                @scope-change="handleLiveAnalysisScopeChange"
              />
            </section>
          </el-tab-pane>

          <el-tab-pane label="Excel专项图表" name="excel">
            <div v-if="chartErrors.length" class="warning-card">
              <h2>部分图表未能加载</h2>
              <ul>
                <li v-for="item in chartErrors" :key="`${item.chart}-${item.message}`">{{ item.chart }}：{{ item.message }}</li>
              </ul>
            </div>

            <section class="chart-section">
              <div class="section-title">
                <h2>Excel专项图表</h2>
                <p>保留原有基于缺陷 Excel 与补充数据的专项图表分析，统一收敛到这个独立页签查看。</p>
              </div>
              <div class="chart-grid">
                <article v-for="chart in coreCharts" :key="chart.id" class="chart-card">
                  <div class="chart-card-header">
                    <div>
                      <h3>{{ chart.title }}</h3>
                      <p>{{ chart.description }}</p>
                    </div>
                  </div>
                  <div :ref="element => setChartRef(chart.id, element)" class="chart-body"></div>
                </article>
              </div>
            </section>

            <section v-if="report.requirement_excel_name" class="chart-section">
              <div class="section-title">
                <h2>需求清单分析</h2>
                <p>来自需求清单 Excel 的补充统计。</p>
              </div>
              <div class="chart-grid compact">
                <article v-for="chart in requirementCharts" :key="chart.id" class="chart-card">
                  <div class="chart-card-header">
                    <h3>{{ chart.title }}</h3>
                  </div>
                  <div :ref="element => setChartRef(chart.id, element)" class="chart-body"></div>
                </article>
              </div>
            </section>

            <section v-if="report.testcase_excel_name" class="chart-section">
              <div class="section-title">
                <h2>测试用例执行分析</h2>
                <p>从测试人员视角查看用例执行情况。</p>
              </div>
              <div class="chart-grid compact">
                <article v-for="chart in testcaseCharts" :key="chart.id" class="chart-card">
                  <div class="chart-card-header">
                    <h3>{{ chart.title }}</h3>
                    <p>总执行率：{{ testcaseSummary.total_rate }}%</p>
                  </div>
                  <div :ref="element => setChartRef(chart.id, element)" class="chart-body"></div>
                </article>
              </div>
            </section>

            <section v-if="report.requirement_excel_name && report.testcase_excel_name" class="chart-section">
              <div class="section-title">
                <h2>综合分析</h2>
                <p>联动需求清单、缺陷和测试用例统计的综合视角。</p>
              </div>
              <div class="chart-grid compact">
                <article v-for="chart in combinedCharts" :key="chart.id" class="chart-card">
                  <div class="chart-card-header">
                    <h3>{{ chart.title }}</h3>
                  </div>
                  <div :ref="element => setChartRef(chart.id, element)" class="chart-body"></div>
                </article>
              </div>
            </section>

            <div
              v-if="!report.requirement_excel_name && !report.testcase_excel_name"
              class="state-card excel-empty-state"
            >
              <h2>暂无补充 Excel 数据</h2>
              <p>当前报告只有基础缺陷分析图表；如果还需要需求清单或测试用例执行的专项图表，可以先到【Excel数据导入】补充上传。</p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '@/utils/api'
import { chartOptionFactories, combinedCharts, coreCharts, requirementCharts, testcaseCharts } from './chartCatalog'
import QualityAnalysisVersionLivePanel from './QualityAnalysisVersionLivePanel.vue'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  active: {
    type: Boolean,
    default: true,
  },
  showBackButton: {
    type: Boolean,
    default: true,
  },
  compactHeader: {
    type: Boolean,
    default: false,
  },
  backRouteName: {
    type: String,
    default: 'ManualTestCaseList',
  },
  backRouteQuery: {
    type: Object,
    default: () => ({
      tab: 'quality-report-list',
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
  fixedDetailTab: {
    type: String,
    default: '',
  },
  showDetailTabs: {
    type: Boolean,
    default: false,
  },
  externalToolbar: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toolbar-state-change'])

const route = useRoute()
const router = useRouter()

const reportList = ref([])
const report = ref(null)
const selectedReportId = ref(null)
const normalizeDetailTab = value => (String(value || '').trim() === 'excel' ? 'excel' : 'live')
const detailTab = ref(normalizeDetailTab(props.fixedDetailTab))
const listLoading = ref(false)
const loading = ref(true)
const error = ref('')
const chartErrors = ref([])
const liveAnalysisScope = ref(null)
const testcaseSummary = ref({ total_rate: 0 })
const excelChartsLoadedReportId = ref(null)
const chartRefs = new Map()
const chartInstances = new Map()
const initialized = ref(false)
const hasFixedDetailTab = computed(() => Boolean(String(props.fixedDetailTab || '').trim()))
const hideDetailTabs = computed(() => hasFixedDetailTab.value && !props.showDetailTabs)
const isCompactHeader = computed(() => props.compactHeader)
const showTopBar = computed(() => !props.externalToolbar)
const showLiveHeaderCopy = computed(() => detailTab.value === 'live' && showTopBar.value)

const normalizeVersion = value => String(value || '').trim()
const normalizeText = value => String(value || '').trim()

const effectiveLinkedVersion = computed(() => normalizeVersion(props.linkedVersion))
const effectiveLinkedProjectId = computed(() => {
  const parsedValue = Number(props.linkedProjectId)
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null
})

const linkedVersionLabel = computed(() => effectiveLinkedVersion.value || '全部版本')
const isLiveSyntheticReport = computed(() => String(report.value?.report_type || '') === 'live')
const liveReportId = computed(() => (isLiveSyntheticReport.value ? null : report.value?.id))
const liveReportVersion = computed(() => (
  isLiveSyntheticReport.value
    ? (effectiveLinkedVersion.value || 'all')
    : (report.value?.version || effectiveLinkedVersion.value)
))

const canRefreshCurrentReport = computed(() => (
  props.useLinkedVersion
    ? true
    : Boolean(selectedReportId.value)
))

const canShareCurrentReport = computed(() => Boolean(report.value && report.value.status === 'completed'))

const selectableReports = computed(() => reportList.value)

const showLiveScopeMeta = computed(() => (
  detailTab.value === 'live' &&
  report.value?.status === 'completed' &&
  Boolean(liveAnalysisScope.value)
))

const liveScopeItems = computed(() => {
  if (!showLiveScopeMeta.value || !liveAnalysisScope.value) {
    return []
  }

  return [
    {
      key: 'project',
      label: '项目名称',
      value: liveAnalysisScope.value.projectName || '全部项目',
    },
    {
      key: 'version',
      label: '版本号',
      value: liveAnalysisScope.value.reportVersion || report.value?.version || '-',
    },
    {
      key: 'generated-at',
      label: '生成时间',
      value: formatDate(liveAnalysisScope.value.generatedAt),
    },
  ]
})

const externalToolbarState = computed(() => ({
  visible: props.externalToolbar && detailTab.value === 'live',
  loading: loading.value,
  canShare: canShareCurrentReport.value,
  canRefresh: canRefreshCurrentReport.value,
  scopeItems: liveScopeItems.value,
}))

const resolvePreferredReportId = () => {
  const raw = Array.isArray(route.query.reportId) ? route.query.reportId[0] : route.query.reportId
  if (!raw) return null

  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
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
  if (!props.useLinkedVersion && !effectiveLinkedVersion.value) {
    return null
  }

  return {
    version: effectiveLinkedVersion.value || 'all',
    ...(effectiveLinkedProjectId.value ? { project_id: effectiveLinkedProjectId.value } : {}),
  }
}

const setChartRef = (key, element) => {
  if (element) {
    chartRefs.set(key, element)
  } else {
    chartRefs.delete(key)
  }
}

const nextFrame = () => new Promise(resolve => requestAnimationFrame(resolve))

const waitForChartRefs = async charts => {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const ready = charts.every(chart => {
      const element = chartRefs.get(chart.id)
      return element && element.offsetWidth > 0 && element.offsetHeight > 0
    })

    if (ready) {
      return true
    }

    await nextTick()
    await nextFrame()
  }

  return false
}

const clearChartInstances = ({ clearRefs = true } = {}) => {
  if (clearRefs) {
    chartRefs.clear()
  }
  chartInstances.forEach(instance => instance.dispose())
  chartInstances.clear()
}

const resetExcelChartState = ({ clearRefs = false } = {}) => {
  chartErrors.value = []
  testcaseSummary.value = { total_rate: 0 }
  excelChartsLoadedReportId.value = null
  clearChartInstances({ clearRefs })
}

const getChartInstance = key => {
  const element = chartRefs.get(key)
  if (!element) return null

  let instance = chartInstances.get(key)
  if (!instance) {
    instance = echarts.init(element)
    chartInstances.set(key, instance)
  }
  return instance
}

const renderChart = (chart, data) => {
  const instance = getChartInstance(chart.id)
  const factory = chartOptionFactories[chart.endpoint]
  if (!instance || !factory) return

  instance.setOption(factory(data), true)
  instance.resize()
}

const fetchChartGroup = async charts => {
  const refsReady = await waitForChartRefs(charts)
  if (!refsReady) {
    charts.forEach(chart => {
      chartErrors.value.push({
        chart: chart.title,
        message: '图表容器初始化失败，请刷新页面后重试',
      })
    })
    return
  }

  const requests = charts.map(async chart => {
    try {
      const response = await api.get(`/quality-analysis/reports/${selectedReportId.value}/charts/${chart.endpoint}/`)
      if (chart.endpoint === 'testcase-tester') {
        testcaseSummary.value = response.data
      }
      renderChart(chart, response.data)
    } catch (err) {
      chartErrors.value.push({
        chart: chart.title,
        message: err.response?.data?.detail || err.message,
      })
    }
  })

  await Promise.all(requests)
}

const resizeCharts = () => {
  chartInstances.forEach(instance => instance.resize())
}

const loadExcelCharts = async ({ force = false } = {}) => {
  if (!props.active || detailTab.value !== 'excel' || !report.value?.id || report.value.status !== 'completed') {
    return
  }

  if (!force && excelChartsLoadedReportId.value === report.value.id && chartInstances.size) {
    resizeCharts()
    return
  }

  resetExcelChartState()
  await nextTick()
  await nextFrame()
  await nextFrame()

  await fetchChartGroup(coreCharts)
  if (report.value.requirement_excel_name) {
    await fetchChartGroup(requirementCharts)
  }
  if (report.value.testcase_excel_name) {
    await fetchChartGroup(testcaseCharts)
  }
  if (report.value.requirement_excel_name && report.value.testcase_excel_name) {
    await fetchChartGroup(combinedCharts)
  }

  excelChartsLoadedReportId.value = report.value.id
}

const syncSelectedReportId = preferredId => {
  const ids = reportList.value.map(item => item.id)
  const latestCompleted = reportList.value.find(item => item.status === 'completed')

  if (!ids.length) {
    selectedReportId.value = null
    return null
  }

  if (preferredId && ids.includes(preferredId)) {
    selectedReportId.value = preferredId
    return preferredId
  }

  if (selectedReportId.value && ids.includes(selectedReportId.value)) {
    return selectedReportId.value
  }

  selectedReportId.value = latestCompleted?.id || reportList.value[0].id
  return selectedReportId.value
}

const syncRouteQuery = async (reportId, replace = false) => {
  const nextValue = reportId ? String(reportId) : undefined
  const currentValue = Array.isArray(route.query.reportId) ? route.query.reportId[0] : route.query.reportId
  if (nextValue === currentValue) return

  const query = { ...route.query }
  if (reportId) {
    query.reportId = String(reportId)
  } else {
    delete query.reportId
  }

  const navigation = {
    path: route.path,
    query,
  }

  if (replace) {
    await router.replace(navigation)
    return
  }

  await router.push(navigation)
}

const loadReportList = async preferredId => {
  listLoading.value = true
  try {
    const response = await api.get('/quality-analysis/reports/', {
      params: buildReportListParams(),
    })
    reportList.value = response.data.results || response.data || []
    const targetId = syncSelectedReportId(preferredId)
    await syncRouteQuery(targetId, true)
    return targetId
  } finally {
    listLoading.value = false
  }
}

const loadLiveReport = async () => {
  const params = buildLiveReportParams()
  if (!params) {
    selectedReportId.value = null
    report.value = null
    liveAnalysisScope.value = null
    loading.value = false
    error.value = '请选择版本号后再查看实时质量分析'
    reportList.value = []
    resetExcelChartState({ clearRefs: true })
    return
  }

  loading.value = true
  error.value = ''
  selectedReportId.value = null
  reportList.value = []
  liveAnalysisScope.value = null
  resetExcelChartState({ clearRefs: true })

  try {
    const response = await api.get('/quality-analysis/reports/live-snapshot/', {
      params,
    })
    report.value = response.data || null
    selectedReportId.value = response.data?.id || 'live'
    loading.value = false
  } catch (err) {
    report.value = null
    error.value = err.response?.data?.detail || err.message || '实时质量分析加载失败'
  } finally {
    if (error.value) {
      loading.value = false
    }
  }
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

const shareReport = async () => {
  if (props.useLinkedVersion) {
    if (!effectiveLinkedVersion.value) {
      ElMessage.warning('请先选择版本后再复制分享链接')
      return
    }

    const response = await api.post('/quality-analysis/reports/live-share/', {
      version: effectiveLinkedVersion.value,
      ...(effectiveLinkedProjectId.value ? { project_id: effectiveLinkedProjectId.value } : {}),
    })
    const routeData = router.resolve({
      name: 'QualityAnalysisLiveShare',
      params: { token: response.data.share_token },
    })
    const shareUrl = `${window.location.origin}${routeData.href}`
    await copyText(shareUrl)
    ElMessage.success('分享链接已复制到剪贴板')
    return
  }

  if (!report.value?.id) return

  const response = await api.post(`/quality-analysis/reports/${report.value.id}/share/`)
  const routeData = router.resolve({
    name: 'QualityAnalysisShare',
    params: { token: response.data.share_token },
  })
  const shareUrl = `${window.location.origin}${routeData.href}`
  await copyText(shareUrl)
  ElMessage.success('分享链接已复制到剪贴板')
}

const loadReport = async reportId => {
  if (!reportId) {
    selectedReportId.value = null
    report.value = null
    liveAnalysisScope.value = null
    loading.value = false
    error.value = '暂无可查看的质量分析报告'
    resetExcelChartState({ clearRefs: true })
    return
  }

  selectedReportId.value = Number(reportId)
  loading.value = true
  error.value = ''
  liveAnalysisScope.value = null
  resetExcelChartState({ clearRefs: true })

  try {
    const response = await api.get(`/quality-analysis/reports/${reportId}/`)
    report.value = response.data
    loading.value = false
    if (detailTab.value === 'excel') {
      await loadExcelCharts({ force: true })
    }
  } catch (err) {
    report.value = null
    error.value = err.response?.data?.detail || err.message || '报告加载失败'
  } finally {
    if (error.value) {
      loading.value = false
    }
  }
}

const refreshView = async preferredId => {
  if (props.useLinkedVersion) {
    await loadLiveReport()
    return
  }

  const targetId = await loadReportList(preferredId)
  await loadReport(targetId)
}

const handleLiveAnalysisScopeChange = scope => {
  liveAnalysisScope.value = scope || null
}

const handleBack = () => {
  router.push({
    name: props.backRouteName,
    query: props.backRouteQuery,
  })
}

const handleReportChange = async value => {
  if (!value) return

  selectedReportId.value = value
  await syncRouteQuery(value)
  await loadReport(value)
}

const refreshCurrentReport = async () => {
  if (props.useLinkedVersion) {
    await loadLiveReport()
    return
  }

  if (!selectedReportId.value) return
  await loadReport(selectedReportId.value)
}

const formatDate = dateTime => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

const initializeView = async () => {
  try {
    await refreshView(resolvePreferredReportId())
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '报告列表加载失败'
    loading.value = false
  } finally {
    initialized.value = true
  }
}

watch(
  externalToolbarState,
  state => {
    emit('toolbar-state-change', state)
  },
  { immediate: true, deep: true }
)

watch(
  () => props.fixedDetailTab,
  nextTab => {
    detailTab.value = normalizeDetailTab(nextTab)
  },
  { immediate: true }
)

watch(
  detailTab,
  async nextTab => {
    if (nextTab === 'excel') {
      await loadExcelCharts()
      return
    }

    resizeCharts()
  }
)

watch(
  () => route.query.reportId,
  async newValue => {
    if (props.useLinkedVersion) return
    if (!initialized.value || !props.active) return

    if (!reportList.value.length) {
      await syncRouteQuery(null, true)
      if (report.value) {
        await loadReport(null)
      }
      return
    }

    if (!newValue) {
      const fallbackId = syncSelectedReportId()
      await syncRouteQuery(fallbackId, true)
      if (fallbackId && report.value?.id !== fallbackId) {
        await loadReport(fallbackId)
      }
      return
    }

    const targetId = Number(Array.isArray(newValue) ? newValue[0] : newValue)
    if (!Number.isFinite(targetId) || targetId <= 0 || !reportList.value.some(item => item.id === targetId)) {
      const fallbackId = syncSelectedReportId()
      await syncRouteQuery(fallbackId, true)
      if (fallbackId && report.value?.id !== fallbackId) {
        await loadReport(fallbackId)
      }
      if (!fallbackId) {
        await loadReport(null)
      }
      return
    }

    if (targetId === selectedReportId.value && report.value?.id === targetId) return

    selectedReportId.value = targetId
    await loadReport(targetId)
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

    await refreshView(resolvePreferredReportId())
  }
)

watch(
  () => props.active,
  async active => {
    if (!active) return

    if (!initialized.value) {
      await initializeView()
      return
    }

    await refreshView(resolvePreferredReportId())
  }
)

onMounted(async () => {
  window.addEventListener('resize', resizeCharts)

  if (props.active) {
    await initializeView()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  clearChartInstances()
})

defineExpose({
  refreshCurrentReport,
  shareReport,
})
</script>

<style scoped lang="scss">
.quality-detail-page {
  min-height: 100vh;
  padding: 24px;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top left, rgba(16, 74, 119, 0.14), transparent 25%),
    linear-gradient(180deg, #f3f7fb 0%, #edf2f7 100%);
}

.quality-detail-page--embedded {
  width: 100%;
  min-height: 100%;
  height: auto;
  padding: 0;
  background: transparent;
  overflow: visible;
}

.detail-tabs {
  display: flex;
  flex-direction: column;
}

:deep(.detail-tabs > .el-tabs__content) {
  overflow: visible;
}

:deep(.detail-tabs--header-hidden > .el-tabs__header) {
  display: none;
}

.top-bar,
.warning-card,
.state-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(17, 45, 67, 0.08);
  border-radius: 22px;
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 28px;
  margin-bottom: 20px;
}

.top-bar--compact {
  justify-content: flex-end;
  align-items: center;
  padding: 16px 24px;
}

.top-bar-info {
  display: flex;
  align-items: center;
  min-height: 32px;
}

.inline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  color: #5c7489;
  font-size: 13px;
  white-space: nowrap;
}

.inline-meta span {
  display: inline-flex;
  align-items: center;
}

.top-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.top-actions--compact {
  width: 100%;
  justify-content: space-between;
}

.live-header-copy {
  flex: 1 1 320px;
  min-width: 260px;
  margin-right: auto;
}

.live-header-copy h2 {
  margin: 0;
  font-size: 20px;
  line-height: 28px;
  color: #17324d;
}

.live-header-copy p {
  margin: 4px 0 0;
  color: #60788d;
  font-size: 13px;
  line-height: 20px;
}

.top-actions__buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.live-scope-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
}

.live-scope-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(28, 91, 135, 0.12);
  background: rgba(24, 86, 134, 0.06);
}

.live-scope-chip__label {
  font-size: 12px;
  color: #5c7489;
}

.live-scope-chip__value {
  font-size: 13px;
  font-weight: 600;
  color: #17324d;
}

.linked-version-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(24, 86, 134, 0.1);
  color: #1c5b87;
  font-size: 13px;
  font-weight: 600;
}

.report-switcher {
  display: flex;
  align-items: center;
}

.report-option {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.warning-card,
.state-card {
  padding: 24px;
  margin-bottom: 20px;
}

.warning-card h2,
.state-card h2 {
  margin: 0 0 12px;
  color: #183b56;
}

.warning-card ul {
  margin: 0;
  padding-left: 18px;
  color: #567086;
}

.state-card.error {
  color: #b42318;
}

.chart-section {
  margin-bottom: 28px;
}

.section-title {
  margin-bottom: 14px;
}

.section-title h2 {
  margin: 0;
  font-size: 24px;
  color: #17324d;
}

.section-title p {
  margin: 8px 0 0;
  color: #60788d;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.chart-grid.compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-card {
  padding: 22px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(17, 45, 67, 0.08);
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
}

.chart-card-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.chart-card-header h3 {
  margin: 0;
  font-size: 19px;
  color: #17324d;
}

.chart-card-header p {
  margin: 6px 0 0;
  color: #5e768b;
  font-size: 13px;
  line-height: 1.5;
}

.chart-body {
  width: 100%;
  height: 420px;
}

@media (max-width: 1200px) {
  .chart-grid,
  .chart-grid.compact {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 900px) {
  .quality-detail-page {
    padding: 16px;
  }

  .quality-detail-page--embedded {
    padding: 0;
  }

  .top-bar {
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .top-actions__buttons {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .live-scope-meta {
    width: 100%;
  }

  .inline-meta {
    width: 100%;
    white-space: normal;
  }

  .report-switcher {
    width: 100%;
  }

  .chart-grid,
  .chart-grid.compact {
    grid-template-columns: 1fr;
  }
}
</style>
