<template>
  <div class="quality-share-page">
    <div class="share-header">
      <div>
        <p class="eyebrow">Shared Report</p>
        <h1>{{ report?.version || '质量分析分享' }}</h1>
        <p class="description">公开查看该质量分析报告的核心图表，无需登录即可访问。</p>
      </div>
      <div class="share-meta" v-if="report">
        <div class="meta-pill">
          <span>缺陷总数</span>
          <strong>{{ report.total_defects || 0 }}</strong>
        </div>
        <div class="meta-pill">
          <span>分类率</span>
          <strong>{{ classificationRate }}%</strong>
        </div>
      </div>
    </div>

    <div v-if="loading" class="state-card">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="error" class="state-card error">
      <h2>分享页加载失败</h2>
      <p>{{ error }}</p>
    </div>

    <template v-else-if="report">
      <div class="meta-strip">
        <span>创建时间：{{ formatDate(report.created_at) }}</span>
        <span>分析完成：{{ formatDate(report.analyzed_at) }}</span>
      </div>

      <div class="chart-grid">
        <article v-for="chart in shareCharts" :key="chart.id" class="chart-card">
          <div class="chart-card-header">
            <h3>{{ chart.title }}</h3>
          </div>
          <div :ref="element => setChartRef(chart.id, element)" class="chart-body"></div>
        </article>
      </div>
    </template>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { chartOptionFactories, shareCharts } from './chartCatalog'

const route = useRoute()

const report = ref(null)
const loading = ref(true)
const error = ref('')

const chartRefs = new Map()
const chartInstances = new Map()

const classificationRate = computed(() => {
  if (!report.value?.total_defects) return 0
  return Math.round((report.value.classified_defects / report.value.total_defects) * 100)
})

const setChartRef = (key, element) => {
  if (element) {
    chartRefs.set(key, element)
  } else {
    chartRefs.delete(key)
  }
}

const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => resolve()))

const waitForChartRefs = async charts => {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const ready = charts.every(chart => chartRefs.get(chart.id))
    if (ready) return true
    await nextTick()
    await nextFrame()
  }
  return false
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

const resizeCharts = () => {
  chartInstances.forEach(instance => instance.resize())
}

const loadShareReport = async () => {
  loading.value = true
  error.value = ''

  try {
    const reportResponse = await axios.get(`/api/quality-analysis/share/${route.params.token}/`)
    report.value = reportResponse.data
    loading.value = false
    await nextTick()
    await nextFrame()

    const refsReady = await waitForChartRefs(shareCharts)
    if (!refsReady) {
      throw new Error('图表容器初始化失败，请刷新页面后重试')
    }

    await Promise.all(
      shareCharts.map(async chart => {
        const response = await axios.get(`/api/quality-analysis/share/${route.params.token}/charts/${chart.endpoint}/`)
        renderChart(chart, response.data)
      })
    )
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '分享页加载失败'
  } finally {
    if (error.value) {
      loading.value = false
    }
  }
}

const formatDate = dateTime => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  loadShareReport()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  chartInstances.forEach(instance => instance.dispose())
  chartInstances.clear()
})
</script>

<style scoped lang="scss">
.quality-share-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(73, 134, 176, 0.18), transparent 25%),
    linear-gradient(180deg, #f4f8fb 0%, #edf2f6 100%);
}

.share-header,
.meta-strip,
.state-card,
.chart-card {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(17, 45, 67, 0.08);
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
}

.share-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 30px;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #587189;
}

.share-header h1 {
  margin: 0;
  font-size: 34px;
  color: #17324d;
}

.description {
  margin: 10px 0 0;
  color: #60788d;
}

.share-meta {
  display: flex;
  gap: 12px;
}

.meta-pill {
  min-width: 120px;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #1d4c6e 0%, #2d769a 100%);
  color: #fff;
}

.meta-pill span {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.78);
}

.meta-pill strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
}

.meta-strip,
.state-card {
  padding: 18px 22px;
  margin-bottom: 20px;
}

.meta-strip {
  display: flex;
  gap: 24px;
  color: #587189;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.chart-card {
  padding: 22px;
}

.chart-card-header {
  margin-bottom: 16px;
}

.chart-card-header h3 {
  margin: 0;
  font-size: 20px;
  color: #17324d;
}

.chart-body {
  width: 100%;
  height: 420px;
}

@media (max-width: 900px) {
  .quality-share-page {
    padding: 16px;
  }

  .share-header,
  .meta-strip,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .share-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .share-meta {
    width: 100%;
  }

  .meta-pill {
    flex: 1;
  }

  .meta-strip {
    flex-direction: column;
    gap: 10px;
  }

  .chart-grid {
    display: grid;
  }
}
</style>
