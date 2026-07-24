<template>
  <div class="excel-import-shell" :class="{ 'excel-import-shell--embedded': embedded }">
    <div class="panel-grid">
      <section class="panel panel--compact">
        <div class="panel-header panel-header--compact">
          <h2>创建报告</h2>
          <p>上传缺陷 Excel，先建立分析报告主档。</p>
        </div>
        <el-form class="compact-form compact-form--create" label-position="top" @submit.prevent>
          <div class="create-form-grid">
            <div v-if="props.useLinkedVersion" class="compact-field compact-field--linked-version">
              <span class="compact-label">关联版本</span>
              <div class="linked-version-value">{{ linkedVersionLabel }}</div>
              <p class="helper-text" :class="{ 'helper-text--warning': !createTargetVersion }">
                {{ createTargetVersion ? '创建报告后，数据将直接关联到左侧当前版本。' : '请先在左侧目录树选择具体版本。' }}
              </p>
            </div>
            <el-form-item v-else label="版本号" class="compact-item">
              <el-select
                v-model="createForm.version"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="选择或输入版本号"
                style="width: 100%"
              >
                <el-option
                  v-for="item in availableVersionOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>

            <div class="compact-field">
              <span class="compact-label">缺陷 Excel</span>
              <input
                ref="sourceFileInput"
                type="file"
                accept=".xlsx"
                class="native-file-input"
                @change="handleSourceFileChange"
              />
              <div class="file-row">
                <el-button @click="sourceFileInput?.click()">选择文件</el-button>
                <span class="file-name">{{ createForm.file?.name || '未选择文件' }}</span>
              </div>
            </div>

            <div class="compact-action">
              <el-button
                type="primary"
                :loading="creating"
                :disabled="!createTargetVersion || !createForm.file"
                @click="createReport"
              >
                创建质量分析报告
              </el-button>
            </div>
          </div>
        </el-form>
      </section>

      <section class="panel panel--compact">
        <div class="panel-header panel-header--compact">
          <h2>补充数据</h2>
          <p>可选上传需求清单和测试用例统计，解锁更多分析图表。</p>
        </div>
        <el-form class="compact-form compact-form--supplement" label-position="top" @submit.prevent>
          <div v-if="props.useLinkedVersion" class="compact-field compact-field--linked-version compact-item">
            <span class="compact-label">关联版本</span>
            <div class="linked-version-value">{{ linkedVersionLabel }}</div>
            <p v-if="!createTargetVersion" class="helper-text helper-text--warning">请先在左侧目录树选择具体版本。</p>
            <p v-else-if="!hasReports" class="helper-text">当前版本下还没有质量分析报告，请先创建报告，再上传补充数据。</p>
            <p v-else class="helper-text">当前上传目标：{{ selectedReportLabel }}</p>
          </div>
          <el-form-item v-else label="版本号" class="compact-item">
            <el-select
              v-model="supplementForm.reportId"
              filterable
              placeholder="选择报告"
              style="width: 100%"
              :disabled="!hasReports"
            >
              <el-option
                v-for="report in visibleReports"
                :key="report.id"
                :label="report.version"
                :value="report.id"
              />
            </el-select>
            <p v-if="!hasReports" class="helper-text">请先创建质量分析报告，再上传补充数据。</p>
            <p v-else class="helper-text">当前上传目标：{{ selectedReportLabel }}</p>
          </el-form-item>

          <div class="supplement-grid">
            <div class="upload-block">
              <div class="upload-block-header">
                <span class="compact-label">需求清单 Excel</span>
              </div>
              <input
                ref="requirementFileInput"
                type="file"
                accept=".xlsx"
                class="native-file-input"
                @change="handleRequirementFileChange"
              />
              <div class="file-row">
                <el-button @click="requirementFileInput?.click()">选择需求清单</el-button>
                <span class="file-name">{{ supplementForm.requirementFile?.name || '未选择文件' }}</span>
              </div>
              <el-button
                class="upload-btn"
                :disabled="!canUploadRequirements"
                :loading="uploadingRequirements"
                @click="uploadRequirements"
              >
                上传需求清单
              </el-button>
            </div>

            <div class="upload-block">
              <div class="upload-block-header">
                <span class="compact-label">测试用例统计 Excel</span>
              </div>
              <input
                ref="testcaseFileInput"
                type="file"
                accept=".xlsx"
                class="native-file-input"
                @change="handleTestcaseFileChange"
              />
              <div class="file-row">
                <el-button @click="testcaseFileInput?.click()">选择测试用例统计</el-button>
                <span class="file-name">{{ supplementForm.testcaseFile?.name || '未选择文件' }}</span>
              </div>
              <el-button
                class="upload-btn secondary"
                :disabled="!canUploadTestcases"
                :loading="uploadingTestcases"
                @click="uploadTestcases"
              >
                上传测试用例统计
              </el-button>
            </div>
          </div>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
  useLinkedVersion: {
    type: Boolean,
    default: false,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
})

const reports = ref([])
const jiraVersions = ref([])
const creating = ref(false)
const uploadingRequirements = ref(false)
const uploadingTestcases = ref(false)

const createForm = ref({
  version: '',
  file: null,
})

const supplementForm = ref({
  reportId: null,
  requirementFile: null,
  testcaseFile: null,
})

const sourceFileInput = ref(null)
const requirementFileInput = ref(null)
const testcaseFileInput = ref(null)

const normalizeVersion = value => String(value || '').trim()
const effectiveLinkedVersion = computed(() => normalizeVersion(props.linkedVersion))
const createTargetVersion = computed(() => (
  props.useLinkedVersion ? effectiveLinkedVersion.value : normalizeVersion(createForm.value.version)
))
const visibleReports = computed(() => {
  if (!props.useLinkedVersion) {
    return reports.value
  }

  return reports.value.filter(item => normalizeVersion(item?.version) === effectiveLinkedVersion.value)
})
const hasReports = computed(() => visibleReports.value.length > 0)
const availableVersionOptions = computed(() => {
  const versions = new Set()

  jiraVersions.value.forEach(item => {
    const version = String(item?.version || '').trim()
    if (version) {
      versions.add(version)
    }
  })

  reports.value.forEach(item => {
    const version = String(item?.version || '').trim()
    if (version) {
      versions.add(version)
    }
  })

  return Array.from(versions).sort((left, right) => right.localeCompare(left, 'zh-CN'))
})
const linkedVersionLabel = computed(() => effectiveLinkedVersion.value || '未选择左侧版本')
const selectedReport = computed(() => visibleReports.value.find(item => item.id === supplementForm.value.reportId) || null)
const selectedReportLabel = computed(() => {
  if (!selectedReport.value) return '未选择报告'
  return `${selectedReport.value.version} / ${selectedReport.value.status_display}`
})
const canUploadRequirements = computed(() => Boolean(selectedReport.value?.id && supplementForm.value.requirementFile))
const canUploadTestcases = computed(() => Boolean(selectedReport.value?.id && supplementForm.value.testcaseFile))

const syncSupplementReport = preferredReportId => {
  const availableIds = visibleReports.value.map(item => item.id)

  if (!availableIds.length) {
    supplementForm.value.reportId = null
    return
  }

  if (preferredReportId && availableIds.includes(preferredReportId)) {
    supplementForm.value.reportId = preferredReportId
    return
  }

  if (supplementForm.value.reportId && availableIds.includes(supplementForm.value.reportId)) {
    return
  }

  supplementForm.value.reportId = visibleReports.value[0].id
}

const loadReports = async preferredReportId => {
  const response = await api.get('/quality-analysis/reports/')
  reports.value = response.data.results || response.data || []
  syncSupplementReport(preferredReportId)
}

const loadJiraVersions = async () => {
  const response = await api.get('/quality-analysis/reports/jira-versions/')
  jiraVersions.value = response.data || []
}

const handleSourceFileChange = event => {
  createForm.value.file = event.target.files?.[0] || null
}

const handleRequirementFileChange = event => {
  supplementForm.value.requirementFile = event.target.files?.[0] || null
}

const handleTestcaseFileChange = event => {
  supplementForm.value.testcaseFile = event.target.files?.[0] || null
}

const resetCreateForm = () => {
  createForm.value = { version: '', file: null }
  if (sourceFileInput.value) {
    sourceFileInput.value.value = ''
  }
}

const resetRequirementFile = () => {
  supplementForm.value.requirementFile = null
  if (requirementFileInput.value) {
    requirementFileInput.value.value = ''
  }
}

const resetTestcaseFile = () => {
  supplementForm.value.testcaseFile = null
  if (testcaseFileInput.value) {
    testcaseFileInput.value.value = ''
  }
}

const createReport = async () => {
  const version = createTargetVersion.value
  if (!version) {
    ElMessage.warning('请先在左侧选择版本后再创建报告')
    return
  }

  creating.value = true
  try {
    const formData = new FormData()
    formData.append('version', version)
    formData.append('source_excel', createForm.value.file)
    const response = await api.post('/quality-analysis/reports/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('质量分析报告创建成功')
    resetCreateForm()
    await loadReports(response.data?.id || null)
  } finally {
    creating.value = false
  }
}

const uploadRequirements = async () => {
  if (!selectedReport.value?.id) {
    ElMessage.warning('当前左侧版本下还没有可补充数据的报告')
    return
  }

  uploadingRequirements.value = true
  try {
    const formData = new FormData()
    formData.append('file', supplementForm.value.requirementFile)
    await api.post(`/quality-analysis/reports/${selectedReport.value.id}/upload-requirements/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('需求清单上传成功')
    resetRequirementFile()
    await loadReports()
  } finally {
    uploadingRequirements.value = false
  }
}

const uploadTestcases = async () => {
  if (!selectedReport.value?.id) {
    ElMessage.warning('当前左侧版本下还没有可补充数据的报告')
    return
  }

  uploadingTestcases.value = true
  try {
    const formData = new FormData()
    formData.append('file', supplementForm.value.testcaseFile)
    await api.post(`/quality-analysis/reports/${selectedReport.value.id}/upload-testcases/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('测试用例统计上传成功')
    resetTestcaseFile()
    await loadReports()
  } finally {
    uploadingTestcases.value = false
  }
}

onMounted(async () => {
  await loadReports()
  if (!props.useLinkedVersion) {
    await loadJiraVersions()
  }
})

watch(
  visibleReports,
  () => {
    syncSupplementReport()
  },
  { immediate: true }
)

watch(
  () => props.linkedVersion,
  async (nextVersion, previousVersion) => {
    if (!props.useLinkedVersion || normalizeVersion(nextVersion) === normalizeVersion(previousVersion)) {
      return
    }
    await loadReports()
  }
)

watch(
  () => props.active,
  async isActive => {
    if (!isActive) {
      return
    }
    await loadReports()
  }
)
</script>

<style scoped lang="scss">
.excel-import-shell {
  min-height: 100%;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel {
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(18, 50, 74, 0.08);
  box-shadow: 0 18px 38px rgba(15, 45, 68, 0.08);
}

.panel--compact {
  padding: 16px 18px;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-header--compact {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
}

.panel-header h2 {
  margin: 0;
  font-size: 20px;
  color: #183b56;
}

.panel-header p {
  margin: 4px 0 0;
  color: #557086;
  font-size: 13px;
}

.native-file-input {
  display: none;
}

.compact-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.compact-item {
  margin-bottom: 0;
}

.create-form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr) auto;
  gap: 12px;
  align-items: end;
}

.compact-field,
.upload-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.compact-field--linked-version {
  min-width: 0;
}

.compact-label {
  font-size: 13px;
  font-weight: 600;
  color: #35556f;
}

.linked-version-value {
  min-height: 40px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 12px;
  background: rgba(246, 249, 252, 0.96);
  border: 1px solid rgba(18, 50, 74, 0.08);
  color: #183b56;
  font-size: 14px;
  font-weight: 600;
}

.file-row {
  display: flex;
  gap: 12px;
  align-items: center;
  min-height: 40px;
}

.file-name {
  color: #557086;
  font-size: 13px;
  word-break: break-all;
}

.compact-action {
  display: flex;
  align-items: end;
}

.supplement-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.upload-block {
  padding: 14px;
  border-radius: 16px;
  background: rgba(246, 249, 252, 0.9);
  border: 1px solid rgba(18, 50, 74, 0.08);
}

.upload-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.helper-text {
  margin: 6px 0 0;
  color: #557086;
  font-size: 12px;
  line-height: 1.5;
}

.helper-text--warning {
  color: #c45656;
}

.upload-btn {
  margin-top: 2px;
  align-self: flex-start;
}

.upload-btn.secondary {
  --el-button-bg-color: #205d86;
  --el-button-border-color: #205d86;
  --el-button-hover-bg-color: #194968;
  --el-button-hover-border-color: #194968;
  --el-button-text-color: #fff;
}

@media (max-width: 1200px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .create-form-grid,
  .supplement-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .panel-header--compact,
  .file-row {
    flex-direction: column;
    align-items: stretch;
  }

  .compact-action :deep(.el-button),
  .upload-btn {
    width: 100%;
  }
}
</style>
