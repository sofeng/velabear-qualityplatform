<template>
  <section class="version-defect-analysis" v-loading="loading">
    <div class="analysis-toolbar">
      <div>
        <h3>版本缺陷分析</h3>
        <span>{{ currentScopeLabel }}</span>
      </div>
      <el-button @click="loadAnalysis" :loading="loading">刷新统计</el-button>
    </div>

    <div v-if="activeCharts.length" class="analysis-grid">
      <article
        v-for="chart in activeCharts"
        :key="chart.key"
        class="analysis-panel"
      >
        <header>{{ chart.title }}</header>
        <div
          :ref="element => setChartRef(chart.key, element)"
          class="analysis-chart"
        />
      </article>
    </div>
    <el-empty v-else description="暂无可统计的版本缺陷数据" />
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
  linkedProjectId: {
    type: [Number, String],
    default: null,
  },
  linkedVersionId: {
    type: [Number, String],
    default: null,
  },
  linkedVersionName: {
    type: String,
    default: '',
  },
})

const loading = ref(false)
const analysisData = ref(null)
const chartRefs = reactive({})
const chartInstances = new Map()

const hasSelectedVersion = computed(() => {
  const value = String(props.linkedVersionId ?? '').trim()
  return Boolean(value && value !== 'all')
})

const currentScopeLabel = computed(() => {
  if (hasSelectedVersion.value) {
    return props.linkedVersionName ? `当前版本：${props.linkedVersionName}` : '当前版本'
  }
  return '全部版本'
})

const activeCharts = computed(() => {
  const payload = analysisData.value || {}
  const selectedCharts = [
    {
      key: 'developerStatus',
      title: '前后端开发人员缺陷状态统计',
      data: payload.selected_version?.developer_status,
      stack: true,
    },
    {
      key: 'developerRootCause',
      title: '前后端开发人员问题根因统计',
      data: payload.selected_version?.developer_root_cause,
      stack: true,
    },
  ]
  const allVersionCharts = [
    {
      key: 'developerTotalsByVersion',
      title: '按版本统计前后端开发人员缺陷数量',
      data: payload.all_versions?.developer_totals_by_version,
      stack: false,
    },
    {
      key: 'rootCauseByVersion',
      title: '按版本统计问题根因',
      data: payload.all_versions?.root_cause_by_version,
      stack: true,
    },
  ]

  return (hasSelectedVersion.value ? selectedCharts : allVersionCharts).filter(chart => hasChartData(chart.data))
})

const hasChartData = data => {
  if (!data || !Array.isArray(data.categories) || !Array.isArray(data.series)) {
    return false
  }
  return data.series.some(item => Array.isArray(item.data) && item.data.some(value => Number(value || 0) > 0))
}

const setChartRef = (key, element) => {
  if (element) {
    chartRefs[key] = element
  }
}

const disposeCharts = () => {
  chartInstances.forEach(instance => instance.dispose())
  chartInstances.clear()
}

const buildChartOption = chart => {
  const categories = chart.data?.categories || []
  const series = (chart.data?.series || []).map(item => ({
    name: item.name,
    type: 'bar',
    stack: chart.stack ? 'total' : undefined,
    emphasis: { focus: 'series' },
    label: {
      show: true,
      position: chart.stack ? 'inside' : 'top',
      formatter: params => (Number(params.value || 0) > 0 ? params.value : ''),
    },
    data: item.data || [],
  }))

  return {
    color: ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2', '#4b5563', '#db2777'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { color: '#334155' },
    },
    grid: {
      top: 48,
      left: 48,
      right: 24,
      bottom: categories.length > 6 ? 88 : 48,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        color: '#475569',
        interval: 0,
        rotate: categories.length > 6 ? 32 : 0,
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#475569' },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series,
  }
}

const renderCharts = async () => {
  await nextTick()
  const activeKeys = new Set(activeCharts.value.map(item => item.key))

  Array.from(chartInstances.keys()).forEach(key => {
    if (!activeKeys.has(key)) {
      chartInstances.get(key)?.dispose()
      chartInstances.delete(key)
    }
  })

  activeCharts.value.forEach(chart => {
    const element = chartRefs[chart.key]
    if (!element) {
      return
    }
    const instance = chartInstances.get(chart.key) || echarts.init(element)
    chartInstances.set(chart.key, instance)
    instance.setOption(buildChartOption(chart), true)
    instance.resize()
  })
}

const loadAnalysis = async () => {
  if (!props.active) {
    return
  }

  loading.value = true
  try {
    const params = {}
    if (props.linkedProjectId) {
      params.project = props.linkedProjectId
    }
    if (hasSelectedVersion.value) {
      params.version = props.linkedVersionId
    }
    const response = await api.get('/defects/version-analysis/', { params })
    analysisData.value = response.data || null
    await renderCharts()
  } catch (error) {
    analysisData.value = null
    ElMessage.error('获取版本缺陷分析失败')
  } finally {
    loading.value = false
  }
}

const handleWindowResize = () => {
  chartInstances.forEach(instance => instance.resize())
}

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  await loadAnalysis()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
  disposeCharts()
})

watch(
  () => [props.active, props.linkedProjectId, props.linkedVersionId, props.linkedVersionName],
  async () => {
    if (props.active) {
      await loadAnalysis()
    }
  }
)

watch(activeCharts, renderCharts)
</script>

<style scoped lang="scss">
.version-defect-analysis {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  overflow: auto;
  background: #f8fafc;
}

.analysis-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.analysis-toolbar h3 {
  margin: 0 0 4px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 600;
}

.analysis-toolbar span {
  color: #64748b;
  font-size: 13px;
}

.analysis-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.analysis-panel {
  min-width: 0;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.analysis-panel header {
  margin-bottom: 12px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 600;
}

.analysis-chart {
  width: 100%;
  height: 380px;
}

</style>
