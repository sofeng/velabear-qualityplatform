<template>
  <div class="version-live-panel">
    <div v-if="loading" class="panel-state">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="panel-state panel-state--error">
      <h3>版本实时分析加载失败</h3>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="analysis" class="panel-content">
      <el-tabs v-model="activeTab" class="version-analysis-tabs">
        <el-tab-pane
          v-if="showProgressTabs"
          label="需求进展"
          name="requirement-progress"
        >
          <div class="progress-tab-body">
            <RequirementOverviewPanel
              embedded
              :active="active && activeTab === 'requirement-progress'"
              :linked-version="effectiveReportVersion"
              :linked-project-id="effectiveProjectId"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane
          v-if="showProgressTabs"
          label="测试进展"
          name="testing-progress"
        >
          <div class="progress-tab-body">
            <TestingOverviewPanel
              embedded
              :active="active && activeTab === 'testing-progress'"
              :linked-version="effectiveReportVersion"
              :linked-project-id="effectiveProjectId"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane
          v-for="tab in displayTabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <div class="analysis-tab-body">
            <section
              v-for="(block, blockIndex) in tab.priorityBlocks"
              :key="`${tab.key}-${block.type}-${blockIndex}`"
              class="analysis-block"
            >
              <div class="analysis-block__header">
                <h3>{{ block.title }}</h3>
                <p v-if="block.description">{{ block.description }}</p>
              </div>

              <ul v-if="block.type === 'bullets'" class="bullet-list">
                <li v-for="item in block.items || []" :key="`${block.title}-${item}`">
                  {{ item }}
                </li>
              </ul>
              <QualityAnalysisBlockChart
                v-else
                :block="block"
                :active="active && activeTab === tab.key"
                :show-value-labels="true"
              />
              <QualityAnalysisBlockNarrative
                v-if="block.type !== 'bullets'"
                :block="block"
              />
            </section>

            <div v-if="tab.metrics?.length" class="metric-strip">
              <div class="metric-grid">
                <article
                  v-for="metric in tab.metrics"
                  :key="`${tab.key}-${metric.label}`"
                  class="metric-card"
                >
                  <span class="metric-card__label">{{ metric.label }}</span>
                  <strong class="metric-card__value">{{ formatCell(metric.value) }}</strong>
                  <p class="metric-card__desc">{{ metric.description || '-' }}</p>
                </article>
              </div>
            </div>

            <section
              v-for="(block, blockIndex) in tab.regularBlocks"
              :key="`${tab.key}-${block.type}-${blockIndex}`"
              class="analysis-block"
            >
              <div class="analysis-block__header">
                <h3>{{ block.title }}</h3>
                <p v-if="block.description">{{ block.description }}</p>
              </div>

              <ul v-if="block.type === 'bullets'" class="bullet-list">
                <li v-for="item in block.items || []" :key="`${block.title}-${item}`">
                  {{ item }}
                </li>
              </ul>
              <QualityAnalysisBlockChart
                v-else
                :block="block"
                :active="active && activeTab === tab.key"
                :show-value-labels="true"
              />
              <QualityAnalysisBlockNarrative
                v-if="block.type !== 'bullets'"
                :block="block"
              />
            </section>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-else class="panel-state">
      <el-empty description="暂无可展示的版本分析数据" :image-size="72" />
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/utils/api'
import QualityAnalysisBlockChart from './QualityAnalysisBlockChart.vue'
import QualityAnalysisBlockNarrative from './QualityAnalysisBlockNarrative.vue'
import RequirementOverviewPanel from '@/views/manual-testcases/RequirementOverviewPanel.vue'
import TestingOverviewPanel from '@/views/manual-testcases/TestingOverviewPanel.vue'

const props = defineProps({
  reportId: {
    type: [Number, String],
    default: null,
  },
  reportVersion: {
    type: String,
    default: '',
  },
  linkedProjectId: {
    type: [Number, String],
    default: null,
  },
  shareToken: {
    type: String,
    default: '',
  },
  active: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['scope-change'])

const route = useRoute()

const loading = ref(false)
const error = ref('')
const analysis = ref(null)
const activeTab = ref('overview')
const PROGRESS_TAB_KEYS = Object.freeze(['requirement-progress', 'testing-progress'])

const normalizeText = value => String(value ?? '').trim()
const effectiveReportVersion = computed(() => normalizeText(props.reportVersion))
const effectiveShareToken = computed(() => normalizeText(props.shareToken))
const isAllVersionAnalysis = computed(() => ['all', '全部版本'].includes(effectiveReportVersion.value.toLowerCase()))
const requestReportVersion = computed(() => (isAllVersionAnalysis.value ? 'all' : effectiveReportVersion.value))
const showProgressTabs = computed(() => !effectiveShareToken.value && !isAllVersionAnalysis.value)
const PRIORITY_BLOCK_PATTERN = /需求状态/

const effectiveProjectId = computed(() => {
  const candidates = [
    props.linkedProjectId,
    Array.isArray(route.query.project_id) ? route.query.project_id[0] : route.query.project_id,
  ]

  for (const candidate of candidates) {
    const parsedValue = Number(candidate)
    if (!Number.isNaN(parsedValue) && parsedValue > 0) {
      return parsedValue
    }
  }

  return null
})

const formatCell = value => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  if (typeof value === 'number') {
    const rounded = Math.round(value * 100) / 100
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2).replace(/\.?0+$/, '')
  }

  return normalizeText(value) || '-'
}
const syncActiveTab = () => {
  const tabs = [
    ...(showProgressTabs.value ? PROGRESS_TAB_KEYS : []),
    ...((analysis.value?.tabs || []).map(item => item.key)),
  ]
  if (!tabs.length) {
    activeTab.value = 'overview'
    return
  }

  if (tabs.some(tabKey => tabKey === activeTab.value)) {
    return
  }

  activeTab.value = tabs[0]
}

const isPriorityBlock = block => PRIORITY_BLOCK_PATTERN.test(normalizeText(block?.title))

const displayTabs = computed(() => (
  (analysis.value?.tabs || []).map(tab => {
    const blocks = Array.isArray(tab?.blocks) ? tab.blocks : []
    return {
      ...tab,
      priorityBlocks: blocks.filter(isPriorityBlock),
      regularBlocks: blocks.filter(block => !isPriorityBlock(block)),
    }
  })
))

const emitScopeChange = payload => {
  emit('scope-change', payload || null)
}

const buildScopePayload = payload => {
  if (!payload) {
    return null
  }

  return {
    projectName: normalizeText(payload.project?.name) || '全部项目',
    reportVersion: normalizeText(payload.report_version) || effectiveReportVersion.value || '-',
    generatedAt: normalizeText(payload.generated_at),
  }
}

const loadAnalysis = async () => {
  emitScopeChange(null)

  if (effectiveShareToken.value) {
    loading.value = true
    error.value = ''

    try {
      const response = await axios.get(`/api/quality-analysis/share/live/${effectiveShareToken.value}/version-analysis/`)
      analysis.value = response.data || null
      emitScopeChange(buildScopePayload(analysis.value))
      syncActiveTab()
    } catch (err) {
      analysis.value = null
      emitScopeChange(null)
      error.value = err.response?.data?.detail || err.message || '版本实时分析加载失败'
    } finally {
      loading.value = false
    }
    return
  }

  const normalizedReportId = Number(props.reportId)
  if ((!normalizedReportId || Number.isNaN(normalizedReportId)) && !requestReportVersion.value) {
    analysis.value = null
    emitScopeChange(null)
    error.value = ''
    return
  }

  loading.value = true
  error.value = ''

  try {
    const params = {
      ...(effectiveProjectId.value ? { project_id: effectiveProjectId.value } : {}),
    }
    let response

    if (normalizedReportId && !Number.isNaN(normalizedReportId)) {
      response = await api.get(`/quality-analysis/reports/${normalizedReportId}/version-analysis/`, {
        params,
      })
    } else {
      response = await api.get('/quality-analysis/reports/live-version-analysis/', {
        params: {
          ...params,
          version: requestReportVersion.value,
        },
      })
    }

    analysis.value = response.data || null
    emitScopeChange(buildScopePayload(analysis.value))
    syncActiveTab()
  } catch (err) {
    analysis.value = null
    emitScopeChange(null)
    error.value = err.response?.data?.detail || err.message || '版本实时分析加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.reportId, props.reportVersion, props.active, effectiveProjectId.value, effectiveShareToken.value],
  async (
    [nextReportId, nextReportVersion, nextActive, , nextShareToken],
    [previousReportId, previousReportVersion, previousActive, , previousShareToken]
  ) => {
    if (!nextActive) {
      return
    }

    if (
      normalizeText(nextReportId) === normalizeText(previousReportId) &&
      normalizeText(nextReportVersion) === normalizeText(previousReportVersion) &&
      normalizeText(nextShareToken) === normalizeText(previousShareToken) &&
      nextActive === previousActive &&
      analysis.value
    ) {
      return
    }

    await loadAnalysis()
  }
)

onMounted(async () => {
  if (props.active) {
    await loadAnalysis()
  }
})
</script>

<style scoped lang="scss">
.version-live-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-state {
  padding: 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(17, 45, 67, 0.08);
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
}

.panel-state--error {
  color: #b42318;
}

.panel-state h3 {
  margin: 0 0 12px;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.version-analysis-tabs {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(17, 45, 67, 0.08);
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
}

:deep(.version-analysis-tabs .el-tabs__header) {
  margin: 0;
  padding: 0 20px;
}

:deep(.version-analysis-tabs .el-tabs__content) {
  padding: 0 20px 20px;
}

.analysis-tab-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-top: 4px;
}

.progress-tab-body {
  height: min(760px, calc(100vh - 250px));
  min-height: 560px;
  display: flex;
  flex-direction: column;
  padding-top: 4px;
}

.metric-strip {
  overflow-x: auto;
  padding-bottom: 4px;
}

.metric-grid {
  display: flex;
  flex-wrap: nowrap;
  gap: 14px;
  width: max-content;
  min-width: 100%;
}

.metric-card {
  flex: 0 0 188px;
  min-width: 188px;
  padding: 18px 20px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(26, 86, 124, 0.08), rgba(57, 138, 180, 0.12));
  border: 1px solid rgba(32, 93, 131, 0.12);
}

.metric-card__label {
  display: block;
  color: #60788d;
  font-size: 13px;
}

.metric-card__value {
  display: block;
  margin-top: 10px;
  color: #17324d;
  font-size: 28px;
  line-height: 1.1;
}

.metric-card__desc {
  margin: 10px 0 0;
  color: #6a8195;
  font-size: 12px;
  line-height: 1.5;
}

.analysis-block {
  padding: 20px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid rgba(17, 45, 67, 0.08);
}

.analysis-block__header {
  margin-bottom: 14px;
}

.analysis-block__header h3 {
  margin: 0;
  color: #17324d;
  font-size: 18px;
}

.analysis-block__header p {
  margin: 8px 0 0;
  color: #60788d;
  font-size: 13px;
  line-height: 1.5;
}

.bullet-list {
  margin: 0;
  padding-left: 20px;
  color: #4f6578;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .metric-card {
    flex-basis: 168px;
    min-width: 168px;
  }

  :deep(.version-analysis-tabs .el-tabs__header),
  :deep(.version-analysis-tabs .el-tabs__content) {
    padding-left: 14px;
    padding-right: 14px;
  }
}
</style>
