<template>
  <div class="recording-script-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="recording-scripts"
      directory-title="自动化脚本页面目录"
      body-class="recording-script-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >
      <main class="script-main-panel">
        <el-card class="panel-card mode-card" shadow="never">
          <el-tabs v-model="activeModeTab" class="mode-tabs">
            <el-tab-pane label="配置与脚本" name="config">
              <section class="script-layout">
                <div class="script-config-panel">
                  <el-form label-position="top" class="script-form">
                    <el-form-item label="目标系统地址">
                      <el-input
                        v-model="form.target_url"
                        clearable
                        placeholder="http://localhost:41080/..."
                      />
                    </el-form-item>

                    <div class="form-grid">
                      <el-form-item label="脚本生成方式">
                        <el-alert
                          type="info"
                          :closable="false"
                          show-icon
                          title="思源质量版使用内置录制 Skill 与确定性模板生成脚本，无需配置 AI 模型。"
                        />
                      </el-form-item>
                    </div>

                    <el-form-item label="页面目录">
                      <div class="module-box">
                        <el-icon><Document /></el-icon>
                        <span>{{ selectedModuleLabel }}</span>
                      </div>
                    </el-form-item>

                    <el-form-item label="自然语言录制描述">
                      <el-input
                        v-model="form.instruction"
                        type="textarea"
                        :rows="8"
                        maxlength="8000"
                        show-word-limit
                        resize="vertical"
                        placeholder="例如：登录系统，进入收费管理，新增一条收费标准并保存"
                      />
                    </el-form-item>

                    <div class="option-row">
                      <el-checkbox v-model="form.auto_stop_after_replay">
                        执行后自动停止并生成流程
                      </el-checkbox>
                      <div class="agent-check-group">
                        <el-tag :type="localAgentStatusTagType">{{ localAgentStatusLabel }}</el-tag>
                        <el-button :loading="localAgentState.checking || localAgentState.starting" @click="ensureLocalAgentReady">
                          <el-icon><Monitor /></el-icon>
                          检测 Agent
                        </el-button>
                      </div>
                    </div>

                    <div class="action-row">
                      <el-button
                        type="primary"
                        :loading="generating"
                        @click="generateScript"
                      >
                        <el-icon><MagicStick /></el-icon>
                        自然语言转 Playwright 指令
                      </el-button>
                      <el-button
                        type="warning"
                        :disabled="!scriptResult.script || isPreviewStale"
                        :loading="savingScript"
                        @click="saveGeneratedScript"
                      >
                        <el-icon><Document /></el-icon>
                        保存脚本
                      </el-button>
                      <el-button
                        type="success"
                        :disabled="!scriptResult.script || isPreviewStale"
                        :loading="executing"
                        @click="executeGeneratedRecording"
                      >
                        <el-icon><VideoPlay /></el-icon>
                        确认执行自动录制
                      </el-button>
                      <el-button @click="resetForm">
                        <el-icon><Refresh /></el-icon>
                        重置
                      </el-button>
                    </div>
                  </el-form>
                </div>

                <div class="script-preview-panel">
                  <div class="preview-header">
                    <div>
                      <div class="card-title">脚本预览</div>
                      <div class="card-subtitle">
                        {{ previewMetaLabel }}
                      </div>
                    </div>
                    <el-button :disabled="!scriptResult.script" @click="copyScript">
                      <el-icon><CopyDocument /></el-icon>
                      复制
                    </el-button>
                  </div>

                  <el-alert
                    v-if="isPreviewStale"
                    class="preview-alert"
                    type="warning"
                    title="需求、地址或 Skill 已变化，请重新生成脚本后再执行"
                    show-icon
                    :closable="false"
                  />

                  <div v-if="scriptResult.summary" class="summary-block">
                    <div class="block-title">执行摘要</div>
                    <p>{{ scriptResult.summary }}</p>
                  </div>

                  <div v-if="scriptResult.warnings.length" class="warning-block">
                    <div class="block-title">风险提示</div>
                    <ul>
                      <li v-for="item in scriptResult.warnings" :key="item">{{ item }}</li>
                    </ul>
                  </div>

                  <pre v-if="scriptResult.script" class="script-code"><code>{{ scriptResult.script }}</code></pre>
                  <el-empty v-else description="生成后在此预览脚本" />
                </div>
              </section>
            </el-tab-pane>

            <el-tab-pane label="执行状态" name="status">
              <section class="status-panel">
                <div class="card-header compact">
                  <div class="card-title">执行状态</div>
                  <el-tag :type="executionStatusTagType">{{ executionStatusLabel }}</el-tag>
                </div>
              <el-steps :active="activeStep" finish-status="success" simple>
                <el-step title="生成脚本" />
                <el-step title="用户确认" />
                <el-step title="自动录制" />
                <el-step title="生成结果" />
              </el-steps>
              <div class="status-lines">
                <div><span>会话ID</span>{{ executionState.session_id || '-' }}</div>
                <div><span>流程ID</span>{{ executionState.flow_id || '-' }}</div>
                <div><span>消息</span>{{ executionState.message || '-' }}</div>
              </div>
              <el-alert
                v-if="executionState.error"
                class="status-alert"
                type="error"
                :title="executionState.error"
                show-icon
                :closable="false"
              />
              </section>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </main>
    </ManualWorkspaceRecordingShell>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CopyDocument,
  Document,
  MagicStick,
  Monitor,
  Refresh,
  VideoPlay
} from '@element-plus/icons-vue'
import {
  createPlaywrightAutomationScript,
  createPlaywrightAutomationScriptVersion,
  generatePlaywrightRecordingScript,
  getPlaywrightRecordingDetail,
  startPlaywrightRecording,
  stopPlaywrightRecording
} from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const RECORDING_METHOD_LOCAL_AGENT = 'local_agent_playwright'
const LOCAL_AGENT_SERVICE_URL = 'http://127.0.0.1:18765'
const LOCAL_AGENT_PROTOCOL = 'testhub-agent://'
const LOCAL_AGENT_UNREACHABLE_MESSAGE = '本地 Agent 服务未连接，请先启动或安装本地 Agent'

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
const generating = ref(false)
const executing = ref(false)
const savingScript = ref(false)
const activeModeTab = ref('config')
const savedAutomationScriptId = ref('')
const savedAutomationScriptVersion = ref(0)

const form = reactive({
  name: '',
  target_url: String(route.query.target_url || ''),
  model_config_id: '',
  capability_id: '',
  instruction: '',
  auto_stop_after_replay: true
})

const generatedSnapshot = reactive({
  instruction: '',
  target_url: '',
  capability_id: '',
  model_config_id: ''
})

const scriptResult = reactive({
  script: '',
  summary: '',
  warnings: [],
  planned_actions: [],
  generation_source: '',
  fallback_reason: '',
  model: null,
  capability: null,
  generated_at: ''
})

const localAgentState = reactive({
  status: 'unknown',
  checking: false,
  starting: false,
  error: '',
  last_checked_at: ''
})

const executionState = reactive({
  status: 'idle',
  session_id: '',
  flow_id: '',
  message: '',
  error: ''
})

const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const selectedModuleLabel = computed(() => {
  const context = researchContext.value || {}
  return context.module_path || context.module_name || '请先在左侧页面目录中选择录制归属页面'
})

const localAgentStatusLabel = computed(() => {
  if (localAgentState.status === 'available') return 'Agent 可用'
  if (localAgentState.status === 'checking') return '检测中'
  if (localAgentState.status === 'starting') return '启动中'
  if (localAgentState.status === 'unavailable') return 'Agent 未连接'
  return 'Agent 未检测'
})

const localAgentStatusTagType = computed(() => {
  if (localAgentState.status === 'available') return 'success'
  if (['checking', 'starting'].includes(localAgentState.status)) return 'warning'
  if (localAgentState.status === 'unavailable') return 'danger'
  return 'info'
})

const executionStatusLabel = computed(() => {
  const labels = {
    idle: '未开始',
    generated: '已生成',
    creating: '创建会话',
    starting_agent: '执行脚本',
    stopping: '停止录制',
    recording: '录制中',
    completed: '已完成',
    failed: '失败'
  }
  return labels[executionState.status] || executionState.status || '未开始'
})

const executionStatusTagType = computed(() => {
  if (executionState.status === 'completed') return 'success'
  if (executionState.status === 'failed') return 'danger'
  if (['creating', 'starting_agent', 'stopping', 'recording'].includes(executionState.status)) return 'warning'
  if (executionState.status === 'generated') return 'primary'
  return 'info'
})

const activeStep = computed(() => {
  if (executionState.status === 'completed') return 4
  if (['starting_agent', 'stopping', 'recording'].includes(executionState.status)) return 3
  if (executionState.status === 'creating') return 2
  if (scriptResult.script) return 1
  return 0
})

const isPreviewStale = computed(() => {
  if (!scriptResult.script) return false
  return (
    generatedSnapshot.instruction !== form.instruction.trim() ||
    generatedSnapshot.target_url !== form.target_url.trim() ||
    String(generatedSnapshot.capability_id || '') !== String(form.capability_id || '') ||
    String(generatedSnapshot.model_config_id || '') !== String(form.model_config_id || '')
  )
})

const previewMetaLabel = computed(() => {
  if (!scriptResult.script) return '等待生成'
  const modelName = scriptResult.model?.name || '自动模型'
  const skillName = scriptResult.capability?.name || '自动 Skill'
  return `${modelName} / ${skillName} / ${scriptResult.generated_at || '-'}`
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


const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'recording-scripts') return
  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
}

const buildModulePayload = () => {
  const context = researchContext.value || {}
  return {
    project_id: context.project_id || null,
    version_id: context.version_id && context.version_id !== 'all' ? context.version_id : null,
    version_name: context.version_name || '',
    module_id: context.module_id || null,
    module_name: context.module_name || '',
    module_path: context.module_path || ''
  }
}

const validateForm = ({ requireInstruction = true } = {}) => {
  const targetUrl = form.target_url.trim()
  if (!targetUrl) {
    ElMessage.warning('请输入目标系统地址')
    return false
  }
  if (!/^https?:\/\//i.test(targetUrl)) {
    ElMessage.warning('目标系统地址需要以 http:// 或 https:// 开头')
    return false
  }
  const module = buildModulePayload()
  if (!module.module_id && !module.module_name && !module.module_path) {
    ElMessage.warning('请先在左侧页面目录中选择录制归属页面')
    return false
  }
  if (requireInstruction && !form.instruction.trim()) {
    ElMessage.warning('请输入自然语言录制描述')
    return false
  }
  return true
}

const generateScript = async () => {
  if (!validateForm()) return
  generating.value = true
  executionState.error = ''
  try {
    const response = await generatePlaywrightRecordingScript({
      instruction: form.instruction.trim(),
      target_url: form.target_url.trim(),
      model_config_id: form.model_config_id || null,
      capability_id: form.capability_id || null,
      module: buildModulePayload()
    })
    const payload = response.data || {}
    scriptResult.script = payload.script || ''
    scriptResult.summary = payload.summary || ''
    scriptResult.warnings = Array.isArray(payload.warnings) ? payload.warnings : []
    scriptResult.planned_actions = Array.isArray(payload.planned_actions) ? payload.planned_actions : []
    scriptResult.generation_source = payload.generation_source || ''
    scriptResult.fallback_reason = payload.fallback_reason || ''
    scriptResult.model = payload.model || null
    scriptResult.capability = payload.capability || null
    scriptResult.generated_at = new Date().toLocaleString()
    if (payload.capability?.id && !form.capability_id) {
      form.capability_id = payload.capability.id
    }
    if (payload.model?.id && !form.model_config_id) {
      form.model_config_id = payload.model.id
    }
    generatedSnapshot.instruction = form.instruction.trim()
    generatedSnapshot.target_url = form.target_url.trim()
    generatedSnapshot.capability_id = payload.capability?.id || form.capability_id || ''
    generatedSnapshot.model_config_id = payload.model?.id || form.model_config_id || ''
    executionState.status = 'generated'
    executionState.message = '脚本已生成，等待确认执行'
    activeModeTab.value = 'config'
    ElMessage.success('录制脚本已生成')
  } catch (error) {
    executionState.status = 'failed'
    executionState.error = normalizeError(error)
    ElMessage.error(executionState.error)
  } finally {
    generating.value = false
  }
}

const buildScriptSavePayload = () => ({
  name: form.name.trim() || `${buildModulePayload().module_name || '自动化'}录制脚本`,
  target_url: form.target_url.trim(),
  instruction: generatedSnapshot.instruction || form.instruction.trim(),
  script: scriptResult.script,
  summary: scriptResult.summary,
  warnings: scriptResult.warnings,
  planned_actions: scriptResult.planned_actions,
  generation_source: scriptResult.generation_source,
  fallback_reason: scriptResult.fallback_reason,
  module: buildModulePayload(),
  model: scriptResult.model || {},
  capability: scriptResult.capability || {},
  metadata: {
    generated_at: scriptResult.generated_at,
    saved_from: 'recording_script_manager'
  },
  change_summary: savedAutomationScriptVersion.value ? '从脚本生成页保存新版本' : '从脚本生成页首次保存'
})

const saveGeneratedScript = async () => {
  if (!scriptResult.script) {
    ElMessage.warning('请先生成脚本')
    return
  }
  if (isPreviewStale.value) {
    ElMessage.warning('需求、地址或 Skill 已变化，请重新生成脚本后再保存')
    return
  }
  if (!validateForm({ requireInstruction: false })) return

  savingScript.value = true
  try {
    const payload = buildScriptSavePayload()
    const response = savedAutomationScriptId.value
      ? await createPlaywrightAutomationScriptVersion(savedAutomationScriptId.value, payload)
      : await createPlaywrightAutomationScript(payload)
    const responsePayload = response.data || {}
    const scriptPayload = responsePayload.script || responsePayload
    const versionPayload = responsePayload.version || responsePayload.version_record || {}
    savedAutomationScriptId.value = scriptPayload.script_id || savedAutomationScriptId.value
    savedAutomationScriptVersion.value = versionPayload.version || scriptPayload.latest_version || savedAutomationScriptVersion.value
    executionState.message = savedAutomationScriptId.value
      ? `脚本已保存至脚本管理：v${savedAutomationScriptVersion.value || '-'}`
      : '脚本已保存至脚本管理'
    ElMessage.success(executionState.message)
  } catch (error) {
    ElMessage.error(normalizeError(error))
  } finally {
    savingScript.value = false
  }
}

const buildBrowserReachablePairingUrl = (sessionId, fallbackUrl = '') => {
  const path = sessionId
    ? `/api/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/agent/`
    : ''
  if (window.location?.origin && path) {
    return `${window.location.origin}${path}`
  }
  return fallbackUrl
}

const fetchWithTimeout = async (url, options = {}, timeoutMs = 45000) => {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    })
  } finally {
    window.clearTimeout(timer)
  }
}

const normalizeLocalAgentError = error => {
  const message = error?.message || ''
  if (!message || message === 'Failed to fetch' || message.includes('NetworkError') || message.includes('aborted')) {
    return LOCAL_AGENT_UNREACHABLE_MESSAGE
  }
  return message
}

const applyLocalAgentHealthPayload = () => {
  localAgentState.status = 'available'
  localAgentState.error = ''
  localAgentState.last_checked_at = new Date().toISOString()
}

const detectLocalAgent = async ({ silent = true } = {}) => {
  if (localAgentState.checking) return localAgentState.status === 'available'
  localAgentState.checking = true
  localAgentState.status = localAgentState.status === 'available' ? 'available' : 'checking'
  try {
    const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/health`, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store'
    }, 5000)
    if (!response.ok) {
      throw new Error(`本地 Agent 服务健康检查失败：HTTP ${response.status}`)
    }
    const payload = await response.json().catch(() => ({}))
    if (payload?.service !== 'testhub-local-playwright-agent') {
      throw new Error('本地端口响应不是 BearAI Local Agent')
    }
    applyLocalAgentHealthPayload(payload)
    if (!silent) ElMessage.success('本地 Agent 可用')
    return true
  } catch (error) {
    localAgentState.status = 'unavailable'
    localAgentState.error = normalizeLocalAgentError(error)
    localAgentState.last_checked_at = new Date().toISOString()
    if (!silent) ElMessage.warning(localAgentState.error)
    return false
  } finally {
    localAgentState.checking = false
  }
}

const invokeLocalAgentProtocol = action => {
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = `${LOCAL_AGENT_PROTOCOL}${action}`
  document.body.appendChild(iframe)
  window.setTimeout(() => {
    iframe.parentNode?.removeChild(iframe)
  }, 1500)
}

const waitForLocalAgentReady = async (timeoutMs = 18000) => {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await detectLocalAgent({ silent: true })) {
      return true
    }
    await new Promise(resolve => window.setTimeout(resolve, 1200))
  }
  return false
}

const ensureLocalAgentReady = async () => {
  if (await detectLocalAgent({ silent: true })) {
    ElMessage.success('本地 Agent 可用')
    return true
  }
  localAgentState.starting = true
  localAgentState.status = 'starting'
  localAgentState.error = ''
  try {
    invokeLocalAgentProtocol('start')
    const ready = await waitForLocalAgentReady(18000)
    if (!ready) {
      localAgentState.status = 'unavailable'
      localAgentState.error = '未能唤起本地 Agent，请确认本机已安装 Agent 并允许浏览器打开协议链接'
      ElMessage.warning(localAgentState.error)
      return false
    }
    ElMessage.success('本地 Agent 已启动')
    return true
  } finally {
    localAgentState.starting = false
  }
}

const buildLocalAgentPayload = (session, agent = {}) => ({
  pairing_url: buildBrowserReachablePairingUrl(
    session?.session_id,
    agent.pairing_url || session?.metadata?.local_agent_pairing_url || ''
  ),
  token: agent.token || '',
  browser: 'chromium',
  headless: false,
  replay_script: scriptResult.script,
  record_replay_events: true,
  maximize: true,
  viewport_width: 1920,
  viewport_height: 1080,
  api_origin: `${window.location.origin}/api`,
  access_token: userStore.accessToken || '',
  refresh_token: userStore.refreshToken || '',
  token_expires_at: String(userStore.tokenExpiresAt || ''),
  user: userStore.user || null,
  timeout_seconds: 300
})

const startLocalAgentWithScript = async (session, agent = {}) => {
  const payload = buildLocalAgentPayload(session, agent)
  if (!payload.pairing_url || !payload.token) {
    throw new Error('本地 Agent 配对信息不完整')
  }
  const ready = await ensureLocalAgentReady()
  if (!ready) {
    throw new Error(localAgentState.error || LOCAL_AGENT_UNREACHABLE_MESSAGE)
  }
  const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/recordings/start`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }, 330000)
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(result.error || `本地 Agent 执行失败：HTTP ${response.status}`)
  }
  if (result.recording?.status && result.recording.status !== 'recording') {
    throw new Error(result.recording.error || '本地 Agent 尚未进入录制状态')
  }
  return result
}

const waitForRecordingCompleted = async sessionId => {
  const startedAt = Date.now()
  let latest = null
  while (Date.now() - startedAt < 30000) {
    const response = await getPlaywrightRecordingDetail(sessionId)
    latest = response.data || null
    const status = latest?.status || latest?.session?.status || ''
    if (['completed', 'failed'].includes(status)) {
      return latest
    }
    await new Promise(resolve => window.setTimeout(resolve, 1200))
  }
  return latest
}

const executeGeneratedRecording = async () => {
  if (!scriptResult.script) {
    ElMessage.warning('请先生成脚本')
    return
  }
  if (isPreviewStale.value) {
    ElMessage.warning('需求、地址或 Skill 已变化，请重新生成脚本')
    return
  }
  if (!validateForm({ requireInstruction: false })) return

  try {
    await ElMessageBox.confirm(
      '确认后将启动本地浏览器执行脚本，并把执行过程录制为 BearAI 录制会话。',
      '确认执行自动录制',
      { type: 'warning', confirmButtonText: '开始执行', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }

  executing.value = true
  executionState.status = 'creating'
  executionState.error = ''
  executionState.message = '正在创建录制会话'
  try {
    const response = await startPlaywrightRecording({
      name: form.name.trim() || `半自动录制 ${new Date().toLocaleString()}`,
      target_url: form.target_url.trim(),
      browser_type: 'chromium',
      recording_method: RECORDING_METHOD_LOCAL_AGENT,
      ...buildModulePayload()
    })
    const session = response.data?.session
    const agent = response.data?.agent || {}
    if (!session?.session_id) {
      throw new Error('后端未返回录制会话ID')
    }
    executionState.session_id = session.session_id
    executionState.status = 'starting_agent'
    executionState.message = '本地 Agent 正在执行脚本'
    await startLocalAgentWithScript(session, agent)

    if (form.auto_stop_after_replay) {
      executionState.status = 'stopping'
      executionState.message = '脚本执行完成，正在停止录制'
      const stopResponse = await stopPlaywrightRecording(session.session_id)
      executionState.flow_id = stopResponse.data?.flow?.flow_id || ''
      const completedSession = await waitForRecordingCompleted(session.session_id)
      executionState.flow_id = executionState.flow_id || completedSession?.flow?.flow_id || ''
      executionState.status = 'completed'
      executionState.message = '自动录制已完成'
    } else {
      executionState.status = 'recording'
      executionState.message = '脚本执行完成，浏览器保持录制中'
    }

    ElMessage.success(executionState.message)
    router.push({
      path: '/manual-testcases/recordings',
      query: {
        ...route.query,
        session_id: session.session_id
      }
    })
  } catch (error) {
    executionState.status = 'failed'
    executionState.error = normalizeLocalAgentError(error)
    ElMessage.error(executionState.error)
  } finally {
    executing.value = false
  }
}

const copyScript = async () => {
  if (!scriptResult.script) return
  try {
    await navigator.clipboard.writeText(scriptResult.script)
    ElMessage.success('脚本已复制')
  } catch (error) {
    ElMessage.warning('复制失败')
  }
}

const resetForm = () => {
  form.name = ''
  form.target_url = ''
  form.instruction = ''
  scriptResult.script = ''
  scriptResult.summary = ''
  scriptResult.warnings = []
  scriptResult.planned_actions = []
  scriptResult.generation_source = ''
  scriptResult.fallback_reason = ''
  scriptResult.model = null
  scriptResult.capability = null
  scriptResult.generated_at = ''
  savedAutomationScriptId.value = ''
  savedAutomationScriptVersion.value = 0
  activeModeTab.value = 'config'
  executionState.status = 'idle'
  executionState.session_id = ''
  executionState.flow_id = ''
  executionState.message = ''
  executionState.error = ''
}

onMounted(() => {
  detectLocalAgent({ silent: true })
})
</script>

<style scoped>
.recording-script-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f6fb 100%);
  overflow: hidden;
}

.script-main-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
}

.mode-card {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mode-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mode-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mode-tabs :deep(.el-tabs__content),
.mode-tabs :deep(.el-tab-pane) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.script-layout {
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(360px, 0.42fr) minmax(480px, 0.58fr);
  gap: 12px;
}

.script-config-panel,
.script-preview-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
  background: #fbfdff;
  overflow: auto;
}

.panel-card {
  border: 1px solid #d8e2ef;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header.compact {
  align-items: center;
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

.script-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.module-box {
  width: 100%;
  min-height: 34px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #f9fbfe;
  color: #3d4d63;
}

.option-row,
.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.option-row {
  justify-content: space-between;
  margin-top: 2px;
}

.agent-check-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.action-row {
  margin-top: 8px;
}

.status-panel {
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  padding: 8px 4px 0;
  overflow: auto;
}

.status-lines {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  color: #334155;
  font-size: 13px;
}

.status-lines span {
  display: inline-block;
  width: 64px;
  color: #7a8699;
}

.status-alert,
.preview-alert {
  margin-top: 12px;
}

.summary-block,
.warning-block {
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
  background: #fbfdff;
}

.block-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #344054;
}

.summary-block p {
  margin: 0;
  color: #3d4d63;
  line-height: 1.6;
  white-space: pre-wrap;
}

.warning-block ul {
  margin: 0;
  padding-left: 18px;
  color: #9a5b00;
  line-height: 1.6;
}

.script-code {
  margin: 0;
  min-height: 420px;
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

@media (max-width: 1180px) {
  .script-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
