<template>
  <div class="automation-script-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="automation-scripts"
      directory-title="自动化脚本页面目录"
      body-class="automation-script-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >
      <main class="manager-main-panel">
        <section class="manager-layout">
          <el-card class="panel-card list-card" shadow="never">
            <template #header>
              <div class="toolbar-row">
                <div>
                  <div class="card-title">脚本管理</div>
                  <div class="card-subtitle">{{ currentModuleLabel }}</div>
                </div>
                <div class="toolbar-actions">
                  <el-input
                    v-model="filters.keyword"
                    class="search-input"
                    clearable
                    placeholder="搜索脚本、地址或描述"
                    @keyup.enter="loadScripts"
                    @clear="loadScripts"
                  >
                    <template #prefix>
                      <el-icon><Search /></el-icon>
                    </template>
                  </el-input>
                  <el-button :loading="loading" @click="loadScripts">
                    <el-icon><Refresh /></el-icon>
                    刷新
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              v-loading="loading"
              class="script-table"
              :data="scripts"
              height="100%"
              highlight-current-row
              :current-row-key="selectedScript?.script_id"
              row-key="script_id"
              @row-click="selectScript"
            >
              <el-table-column prop="name" label="脚本名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="latest_version" label="版本" width="76">
                <template #default="{ row }">
                  <el-tag size="small">v{{ row.latest_version || 0 }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="target_url" label="目标地址" min-width="210" show-overflow-tooltip />
              <el-table-column prop="module_path" label="页面目录" min-width="180" show-overflow-tooltip />
              <el-table-column prop="updated_at" label="更新时间" width="170">
                <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="190" fixed="right">
                <template #default="{ row }">
                  <el-button text type="primary" @click.stop="openDetail(row)">详情</el-button>
                  <el-button text @click.stop="copyScript(row.script)">复制</el-button>
                  <el-button text type="danger" @click.stop="deleteScript(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-row">
              <el-pagination
                v-model:current-page="pagination.page"
                v-model:page-size="pagination.page_size"
                small
                layout="total, sizes, prev, pager, next"
                :page-sizes="[10, 20, 50, 100]"
                :total="pagination.count"
                @current-change="loadScripts"
                @size-change="handlePageSizeChange"
              />
            </div>
          </el-card>
        </section>

        <el-drawer
          v-model="detailDrawerVisible"
          class="script-detail-drawer"
          direction="rtl"
          size="58%"
          destroy-on-close
        >
          <template #header>
            <div class="detail-header">
              <div>
                <div class="card-title">{{ selectedScript?.name || '脚本详情' }}</div>
                <div class="card-subtitle">
                  {{ selectedScript ? `当前版本 v${selectedScript.latest_version || 0}` : '选择脚本查看详情' }}
                </div>
              </div>
              <el-tag v-if="selectedScript" type="success">已保存</el-tag>
            </div>
          </template>

          <el-empty v-if="!selectedScript" description="请选择一个自动化脚本" />

          <div v-else class="drawer-detail-content">
            <el-tabs v-model="activeDetailTab" class="detail-tabs">
              <el-tab-pane label="脚本详情" name="detail">
                <div class="detail-tab-body">
                  <div class="meta-grid">
                    <div><span>目标地址</span>{{ selectedScript.target_url || '-' }}</div>
                    <div><span>页面目录</span>{{ selectedScript.module_path || selectedScript.module_name || '-' }}</div>
                    <div><span>创建人</span>{{ selectedScript.created_by_name || '-' }}</div>
                    <div><span>更新人</span>{{ selectedScript.updated_by_name || '-' }}</div>
                  </div>

                  <div class="drawer-content-grid">
                    <section class="script-preview-section">
                      <div class="code-toolbar">
                        <span>{{ selectedVersion ? `预览 v${selectedVersion.version}` : `预览 v${selectedScript.latest_version || 0}` }}</span>
                        <el-button :disabled="!previewScript" @click="copyScript(previewScript)">
                          <el-icon><CopyDocument /></el-icon>
                          复制
                        </el-button>
                      </div>
                      <pre v-if="previewScript" class="script-code"><code>{{ previewScript }}</code></pre>
                      <el-empty v-else description="暂无脚本内容" />
                    </section>

                    <section class="version-section">
                      <div class="section-title">版本记录</div>
                      <div v-loading="versionsLoading" class="version-list">
                        <div
                          v-for="item in versions"
                          :key="item.id"
                          :class="['version-item', { active: selectedVersion?.id === item.id }]"
                          @click="selectedVersion = item"
                        >
                          <div class="version-main">
                            <el-tag size="small" :type="item.version === selectedScript.latest_version ? 'success' : 'info'">
                              v{{ item.version }}
                            </el-tag>
                            <span>{{ item.change_summary || '保存脚本版本' }}</span>
                          </div>
                          <div class="version-meta">
                            {{ formatDate(item.created_at) }} / {{ item.created_by_name || '-' }}
                          </div>
                          <div class="version-actions">
                            <el-button text type="primary" @click.stop="selectedVersion = item">预览</el-button>
                            <el-button
                              text
                              :disabled="item.version === selectedScript.latest_version"
                              @click.stop="restoreVersion(item)"
                            >
                              恢复为当前
                            </el-button>
                          </div>
                        </div>
                        <el-empty v-if="!versions.length && !versionsLoading" description="暂无版本记录" />
                      </div>
                    </section>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="自然语言" name="natural_language">
                <div class="natural-language-panel">
                  <div class="code-toolbar">
                    <span>{{ selectedVersion ? `自然语言 v${selectedVersion.version}` : `自然语言 v${selectedScript.latest_version || 0}` }}</span>
                    <el-button :disabled="!previewInstruction" @click="copyScript(previewInstruction)">
                      <el-icon><CopyDocument /></el-icon>
                      复制
                    </el-button>
                  </div>
                  <pre v-if="previewInstruction" class="natural-language-code">{{ previewInstruction }}</pre>
                  <el-empty v-else description="暂无自然语言描述" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-drawer>
      </main>
    </ManualWorkspaceRecordingShell>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Refresh, Search } from '@element-plus/icons-vue'
import {
  deletePlaywrightAutomationScript,
  getPlaywrightAutomationScriptVersions,
  getPlaywrightAutomationScripts,
  restorePlaywrightAutomationScriptVersion
} from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const emptyModuleFields = {
  project_id: '',
  project_name: '',
  version_id: 'all',
  version_name: '',
  module_id: '',
  module_name: '',
  module_path: ''
}

const researchContext = ref({ ...emptyModuleFields })
const filters = reactive({ keyword: '' })
const pagination = reactive({ page: 1, page_size: 20, count: 0 })
const scripts = ref([])
const versions = ref([])
const selectedScript = ref(null)
const selectedVersion = ref(null)
const activeDetailTab = ref('detail')
const detailDrawerVisible = ref(false)
const loading = ref(false)
const versionsLoading = ref(false)

const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const currentModuleLabel = computed(() => {
  const context = researchContext.value || {}
  return context.module_path || context.module_name || '全部自动化脚本'
})

const previewScript = computed(() => {
  if (selectedVersion.value) return selectedVersion.value.script_content || ''
  return selectedScript.value?.script || ''
})

const previewInstruction = computed(() => {
  if (selectedVersion.value) return selectedVersion.value.instruction || ''
  return selectedScript.value?.instruction || ''
})

const normalizeListResponse = payload => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const normalizeError = error => (
  error?.response?.data?.error ||
  error?.response?.data?.detail ||
  error?.message ||
  '操作失败'
)

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

const buildModuleParams = () => {
  const context = researchContext.value || {}
  const params = {}
  if (context.project_id) params.project_id = context.project_id
  if (context.version_id && context.version_id !== 'all') params.version_id = context.version_id
  if (context.module_id) params.module_id = context.module_id
  if (context.module_name) params.module_name = context.module_name
  if (context.module_path) params.module_path = context.module_path
  params.include_descendants = true
  return params
}

const loadScripts = async () => {
  loading.value = true
  try {
    const response = await getPlaywrightAutomationScripts({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: filters.keyword.trim(),
      ...buildModuleParams()
    })
    const payload = response.data || {}
    scripts.value = normalizeListResponse(payload)
    pagination.count = payload.count || scripts.value.length
    if (selectedScript.value) {
      const matched = scripts.value.find(item => item.script_id === selectedScript.value.script_id)
      selectedScript.value = matched || null
      if (matched) {
        await loadVersions(matched)
      } else {
        versions.value = []
        selectedVersion.value = null
      }
    }
  } catch (error) {
    ElMessage.error(normalizeError(error))
  } finally {
    loading.value = false
  }
}

const loadVersions = async script => {
  if (!script?.script_id) return
  versionsLoading.value = true
  try {
    const response = await getPlaywrightAutomationScriptVersions(script.script_id)
    versions.value = normalizeListResponse(response.data)
    selectedVersion.value = versions.value.find(item => item.version === script.latest_version) || versions.value[0] || null
  } catch (error) {
    ElMessage.error(normalizeError(error))
  } finally {
    versionsLoading.value = false
  }
}

const selectScript = async row => {
  selectedScript.value = row
  selectedVersion.value = null
  activeDetailTab.value = 'detail'
  detailDrawerVisible.value = true
  await loadVersions(row)
}

const openDetail = async row => {
  await selectScript(row)
}

const copyScript = async script => {
  if (!script) return
  try {
    await navigator.clipboard.writeText(script)
    ElMessage.success('脚本已复制')
  } catch (error) {
    ElMessage.warning('复制失败')
  }
}

const deleteScript = async row => {
  try {
    await ElMessageBox.confirm(
      `确认删除“${row.name}”及其全部版本？`,
      '删除自动化脚本',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }

  try {
    await deletePlaywrightAutomationScript(row.script_id)
    if (selectedScript.value?.script_id === row.script_id) {
      selectedScript.value = null
      selectedVersion.value = null
      versions.value = []
    }
    ElMessage.success('脚本已删除')
    await loadScripts()
  } catch (error) {
    ElMessage.error(normalizeError(error))
  }
}

const restoreVersion = async version => {
  if (!selectedScript.value?.script_id || !version?.version) return
  try {
    await ElMessageBox.confirm(
      `确认将 v${version.version} 恢复为新的当前版本？`,
      '恢复脚本版本',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }

  try {
    const response = await restorePlaywrightAutomationScriptVersion(
      selectedScript.value.script_id,
      version.version,
      { change_summary: `从 v${version.version} 恢复` }
    )
    selectedScript.value = response.data?.script || selectedScript.value
    await loadScripts()
    if (selectedScript.value) {
      await loadVersions(selectedScript.value)
    }
    activeDetailTab.value = 'detail'
    ElMessage.success('版本已恢复')
  } catch (error) {
    ElMessage.error(normalizeError(error))
  }
}

const handlePageSizeChange = () => {
  pagination.page = 1
  loadScripts()
}

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'automation-scripts') return
  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
  pagination.page = 1
  loadScripts()
}

onMounted(() => {
  loadScripts()
})
</script>

<style scoped>
.automation-script-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f6fb 100%);
  overflow: hidden;
}

.manager-main-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
}

.manager-layout {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
}

.panel-card {
  min-width: 0;
  min-height: 0;
  border: 1px solid #d8e2ef;
  border-radius: 8px;
}

.list-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.list-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.toolbar-row,
.detail-header,
.code-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 260px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #7a8699;
}

.script-table {
  flex: 1;
  min-height: 0;
}

.pagination-row {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
}

.script-detail-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #e1e8f0;
}

.script-detail-drawer :deep(.el-drawer__body) {
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 18px 18px;
  overflow: hidden;
}

.drawer-detail-content {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.meta-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
  background: #fbfdff;
  color: #334155;
  font-size: 13px;
}

.meta-grid span {
  display: inline-block;
  width: 64px;
  color: #7a8699;
}

.detail-tabs {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.detail-tabs :deep(.el-tabs__content),
.detail-tabs :deep(.el-tab-pane) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.detail-tab-body {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-content-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 12px;
}

.script-preview-section,
.version-section,
.natural-language-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.section-title {
  height: 32px;
  display: flex;
  align-items: center;
  color: #344054;
  font-size: 13px;
  font-weight: 700;
}

.script-code {
  margin: 12px 0 0;
  height: calc(100% - 44px);
  min-height: 360px;
  padding: 14px;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  background: #0f172a;
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  white-space: pre;
}

.natural-language-code {
  margin: 12px 0 0;
  flex: 1;
  min-height: 0;
  padding: 14px;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  background: #fbfdff;
  color: #24364b;
  font-size: 13px;
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.version-list {
  height: 100%;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-item {
  padding: 12px;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
  background: #fbfdff;
  cursor: pointer;
}

.version-item.active {
  border-color: #409eff;
  background: #eef6ff;
}

.version-main,
.version-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-main {
  color: #24364b;
  font-weight: 600;
}

.version-meta {
  margin-top: 6px;
  color: #7a8699;
  font-size: 12px;
}

.version-actions {
  margin-top: 8px;
}

@media (max-width: 1180px) {
  .script-detail-drawer {
    --el-drawer-padding-primary: 12px;
  }

  .drawer-content-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
