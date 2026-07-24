<template>
  <div class="defect-notification-settings">
    <el-tabs
      v-model="activeSubTab"
      class="defect-notification-tabs"
      :class="{ 'defect-notification-tabs--header-hidden': hasFixedSubTab }"
    >
      <el-tab-pane label="邮件配置" name="email-config">
        <div class="settings-card">
          <div class="settings-card__header">
            <div>
              <h3>邮件配置</h3>
              <p>维护缺陷邮件服务器配置，并支持 SMTP 校验和测试发送。</p>
            </div>
            <div class="settings-card__actions">
              <el-button :loading="smtpVerifying" @click="handleVerifySmtp">校验 SMTP</el-button>
              <el-button type="primary" :loading="emailSaving" @click="handleSaveEmailConfig">保存配置</el-button>
            </div>
          </div>

          <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" label-width="120px">
            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 服务器" prop="host">
                  <el-input v-model="emailForm.host" placeholder="例如：smtp.example.com" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 端口" prop="port">
                  <el-input-number v-model="emailForm.port" :min="1" :max="65535" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 用户名" prop="username">
                  <el-input v-model="emailForm.username" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 密码" prop="password">
                  <el-input v-model="emailForm.password" show-password />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="发件人名称" prop="from_name">
                  <el-input v-model="emailForm.from_name" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="发件人邮箱" prop="from_email">
                  <el-input v-model="emailForm.from_email" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="启用邮件通知">
                  <el-switch v-model="emailForm.is_active" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <div class="settings-card settings-card--secondary">
          <div class="settings-card__header">
            <div>
              <h3>测试邮件</h3>
              <p>使用已保存的邮件配置，发送测试邮件验证邮件链路。</p>
            </div>
            <div class="settings-card__actions">
              <el-button type="primary" :loading="testSending" @click="handleSendTestEmail">发送测试邮件</el-button>
            </div>
          </div>

          <el-form ref="testFormRef" :model="testForm" :rules="testRules" label-width="120px">
            <el-row :gutter="16">
              <el-col :xs="24" :md="10">
                <el-form-item label="收件人邮箱" prop="to">
                  <el-input v-model="testForm.to" placeholder="请输入测试邮箱" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="14">
                <el-form-item label="邮件主题" prop="subject">
                  <el-input v-model="testForm.subject" placeholder="留空则使用默认主题" />
                </el-form-item>
              </el-col>
              <el-col :xs="24">
                <el-form-item label="邮件内容" prop="text">
                  <el-input v-model="testForm.text" type="textarea" :rows="4" placeholder="留空则使用默认内容" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane label="邮件模板" name="email-template-config">
        <div class="settings-card">
          <div class="settings-card__header">
            <div>
              <h3>邮件模板</h3>
              <p>维护不同缺陷状态下的邮件模板内容，发送时会自动填充模板变量。</p>
            </div>
            <div class="settings-card__actions">
              <el-button type="primary" :loading="templateSaving" @click="handleSaveEmailTemplateConfig">保存模板</el-button>
            </div>
          </div>

          <div class="template-tip">
            支持变量：{{ '${ID}' }}、{{ '${标题}' }}、{{ '${创建人}' }}、{{ '${处理人}' }}
          </div>

          <el-form ref="emailTemplateFormRef" :model="templateForm" :rules="templateRules" label-width="120px">
            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-form-item label="新缺陷模板" prop="new_bug_template">
                  <el-input v-model="templateForm.new_bug_template" type="textarea" :rows="6" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="已解决模板" prop="resolved_bug_template">
                  <el-input v-model="templateForm.resolved_bug_template" type="textarea" :rows="6" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="已拒绝模板" prop="rejected_bug_template">
                  <el-input v-model="templateForm.rejected_bug_template" type="textarea" :rows="6" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="重新打开模板" prop="reopened_bug_template">
                  <el-input v-model="templateForm.reopened_bug_template" type="textarea" :rows="6" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane label="消息提醒" name="notification-settings">
        <div class="settings-card">
          <div class="settings-card__header">
            <div>
              <h3>消息提醒</h3>
              <p>配置浏览器右下角提醒类型，并管理当前浏览器的通知权限。</p>
            </div>
            <div class="settings-card__actions">
              <el-button @click="handleAllowBrowserNotification" :disabled="permissionState === 'unsupported'">
                {{ permissionButtonText }}
              </el-button>
              <el-button type="primary" :loading="notificationSaving" @click="handleSaveNotificationTypes">
                保存提醒设置
              </el-button>
            </div>
          </div>

          <div class="permission-status">
            浏览器通知权限：
            <el-tag :type="permissionTagType">{{ permissionStatusText }}</el-tag>
            <span v-if="platformOrigin" class="permission-status__origin">{{ platformOrigin }}</span>
          </div>

          <el-checkbox-group v-model="notificationTypes" class="type-group">
            <el-checkbox v-for="item in notificationTypeOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDefectEmailConfig,
  getDefectNotificationSettings,
  saveDefectEmailConfig,
  saveDefectNotificationSettings,
  testDefectEmailConfig,
  verifyDefectEmailConfig,
} from '@/api/defects'
import {
  getCurrentPlatformOrigin,
  getDefectNotificationPermissionState,
  requestDefectNotificationPermission,
  showDefectNotificationPermissionPreview,
} from '@/services/defectNotifications'

const props = defineProps({
  fixedSubTab: {
    type: String,
    default: '',
  },
})

const DEFECT_NOTIFICATION_SUB_TABS = Object.freeze([
  'email-config',
  'email-template-config',
  'notification-settings',
])
const LEGACY_DEFECT_NOTIFICATION_SUB_TAB_MAP = Object.freeze({
  'test-email': 'email-config',
})
const normalizeSubTab = value => {
  const normalizedValue = String(value || '').trim()
  const mappedValue = LEGACY_DEFECT_NOTIFICATION_SUB_TAB_MAP[normalizedValue] || normalizedValue
  return DEFECT_NOTIFICATION_SUB_TABS.includes(mappedValue) ? mappedValue : 'email-config'
}

const DEFAULT_FROM_NAME = '缺陷管理平台'
const DEFAULT_TEST_EMAIL_SUBJECT = '缺陷邮件配置测试'
const DEFAULT_TEST_EMAIL_TEXT = '这是一封测试邮件，表示缺陷邮件配置可正常使用。'

const emailFormRef = ref(null)
const emailTemplateFormRef = ref(null)
const testFormRef = ref(null)
const activeSubTab = ref(normalizeSubTab(props.fixedSubTab))

const emailSaving = ref(false)
const templateSaving = ref(false)
const smtpVerifying = ref(false)
const testSending = ref(false)
const notificationSaving = ref(false)
const permissionState = ref(getDefectNotificationPermissionState())
const notificationTypes = ref([])
const persistedEmailConfig = ref({})
const hasFixedSubTab = computed(() => Boolean(String(props.fixedSubTab || '').trim()))
const platformOrigin = computed(() => getCurrentPlatformOrigin())

const createEmailConfigState = (payload = {}) => ({
  host: payload?.host || '',
  port: payload?.port || 465,
  username: payload?.username || '',
  password: payload?.password || '',
  from_name: payload?.from_name || DEFAULT_FROM_NAME,
  from_email: payload?.from_email || '',
  is_active: payload?.is_active !== false,
})

const createEmailTemplateState = (payload = {}) => ({
  new_bug_template: payload?.new_bug_template || '',
  resolved_bug_template: payload?.resolved_bug_template || '',
  rejected_bug_template: payload?.rejected_bug_template || '',
  reopened_bug_template: payload?.reopened_bug_template || '',
})

const emailForm = reactive(createEmailConfigState())
const templateForm = reactive(createEmailTemplateState())

const testForm = reactive({
  to: '',
  subject: DEFAULT_TEST_EMAIL_SUBJECT,
  text: DEFAULT_TEST_EMAIL_TEXT,
})

const emailRules = {
  host: [{ required: true, message: '请输入 SMTP 服务器', trigger: 'blur' }],
  port: [{ required: true, message: '请输入 SMTP 端口', trigger: 'change' }],
  username: [{ required: true, message: '请输入 SMTP 用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入 SMTP 密码', trigger: 'blur' }],
  from_name: [{ required: true, message: '请输入发件人名称', trigger: 'blur' }],
  from_email: [
    { required: true, message: '请输入发件人邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
}

const templateRules = {
  new_bug_template: [{ required: true, message: '请输入新缺陷模板', trigger: 'blur' }],
  resolved_bug_template: [{ required: true, message: '请输入已解决模板', trigger: 'blur' }],
  rejected_bug_template: [{ required: true, message: '请输入已拒绝模板', trigger: 'blur' }],
  reopened_bug_template: [{ required: true, message: '请输入重新打开模板', trigger: 'blur' }],
}

const testRules = {
  to: [
    { required: true, message: '请输入测试收件人邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
}

const notificationTypeOptions = [
  { label: '新缺陷提醒', value: 'new' },
  { label: '指派提醒', value: 'assign' },
  { label: '标题变更提醒', value: 'title' },
  { label: '描述变更提醒', value: 'description' },
  { label: '状态变更提醒', value: 'status' },
  { label: '评论提醒', value: 'comment' },
]

const permissionStatusText = computed(() => {
  if (permissionState.value === 'granted') {
    return '已授权'
  }
  if (permissionState.value === 'denied') {
    return '已拒绝'
  }
  if (permissionState.value === 'default') {
    return '未设置'
  }
  return '当前浏览器不支持'
})

const permissionTagType = computed(() => {
  if (permissionState.value === 'granted') {
    return 'success'
  }
  if (permissionState.value === 'denied') {
    return 'danger'
  }
  if (permissionState.value === 'default') {
    return 'warning'
  }
  return 'info'
})

const permissionButtonText = computed(() => {
  if (permissionState.value === 'granted') {
    return '已允许浏览器通知'
  }
  if (permissionState.value === 'denied') {
    return '允许浏览器通知'
  }
  if (permissionState.value === 'default') {
    return '允许浏览器通知'
  }
  return '当前浏览器不支持'
})

const validateForm = async formRef => {
  if (!formRef?.value) {
    return false
  }
  try {
    await formRef.value.validate()
    return true
  } catch (error) {
    return false
  }
}

const syncPersistedEmailConfig = payload => {
  const normalizedConfig = createEmailConfigState(payload)
  const normalizedTemplate = createEmailTemplateState(payload)

  persistedEmailConfig.value = {
    ...normalizedConfig,
    ...normalizedTemplate,
  }

  return { normalizedConfig, normalizedTemplate }
}

const assignEmailForms = payload => {
  const { normalizedConfig, normalizedTemplate } = syncPersistedEmailConfig(payload)
  Object.assign(emailForm, normalizedConfig)
  Object.assign(templateForm, normalizedTemplate)
}

const buildEmailConfigPayload = ({ useCurrentConfig = true, useCurrentTemplate = true } = {}) => {
  const persistedConfig = createEmailConfigState(persistedEmailConfig.value)
  const persistedTemplate = createEmailTemplateState(persistedEmailConfig.value)

  return {
    ...persistedConfig,
    ...persistedTemplate,
    ...(useCurrentConfig ? { ...emailForm } : persistedConfig),
    ...(useCurrentTemplate ? { ...templateForm } : persistedTemplate),
  }
}

const persistEmailConfig = async (payload, { syncConfig = true, syncTemplate = true } = {}) => {
  const response = await saveDefectEmailConfig(payload)
  const { normalizedConfig, normalizedTemplate } = syncPersistedEmailConfig(response.data || payload)

  if (syncConfig) {
    Object.assign(emailForm, normalizedConfig)
  }
  if (syncTemplate) {
    Object.assign(templateForm, normalizedTemplate)
  }

  return response.data || payload
}

const loadEmailConfig = async () => {
  const response = await getDefectEmailConfig()
  assignEmailForms(response.data || {})
}

const loadNotificationSettings = async () => {
  const response = await getDefectNotificationSettings()
  notificationTypes.value = Array.isArray(response.data?.types) ? response.data.types : []
}

const loadPageData = async () => {
  try {
    await Promise.all([loadEmailConfig(), loadNotificationSettings()])
    permissionState.value = getDefectNotificationPermissionState()
  } catch (error) {
    ElMessage.error('加载缺陷通知配置失败')
  }
}

const handleSaveEmailConfig = async () => {
  const passed = await validateForm(emailFormRef)
  if (!passed) {
    return
  }

  emailSaving.value = true
  try {
    await persistEmailConfig(
      buildEmailConfigPayload({
        useCurrentConfig: true,
        useCurrentTemplate: false,
      }),
      {
        syncConfig: true,
        syncTemplate: false,
      }
    )
    ElMessage.success('邮件配置已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存邮件配置失败')
  } finally {
    emailSaving.value = false
  }
}

const handleSaveEmailTemplateConfig = async () => {
  const passed = await validateForm(emailTemplateFormRef)
  if (!passed) {
    return
  }

  templateSaving.value = true
  try {
    await persistEmailConfig(
      buildEmailConfigPayload({
        useCurrentConfig: false,
        useCurrentTemplate: true,
      }),
      {
        syncConfig: false,
        syncTemplate: true,
      }
    )
    ElMessage.success('邮件模板已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存邮件模板失败')
  } finally {
    templateSaving.value = false
  }
}

const handleVerifySmtp = async () => {
  const passed = await validateForm(emailFormRef)
  if (!passed) {
    return
  }

  smtpVerifying.value = true
  try {
    await persistEmailConfig(
      buildEmailConfigPayload({
        useCurrentConfig: true,
        useCurrentTemplate: false,
      }),
      {
        syncConfig: true,
        syncTemplate: false,
      }
    )
    await verifyDefectEmailConfig()
    ElMessage.success('SMTP 连接正常')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'SMTP 校验失败')
  } finally {
    smtpVerifying.value = false
  }
}

const handleSendTestEmail = async () => {
  const emailPassed = await validateForm(emailFormRef)
  if (!emailPassed) {
    if (!hasFixedSubTab.value) {
      activeSubTab.value = 'email-config'
    } else {
      ElMessage.warning('请先完善邮件配置')
    }
    return
  }

  const testPassed = await validateForm(testFormRef)
  if (!testPassed) {
    if (!hasFixedSubTab.value) {
      activeSubTab.value = 'email-config'
    }
    return
  }

  testSending.value = true
  try {
    await persistEmailConfig(
      buildEmailConfigPayload({
        useCurrentConfig: true,
        useCurrentTemplate: false,
      }),
      {
        syncConfig: true,
        syncTemplate: false,
      }
    )
    await testDefectEmailConfig({ ...testForm })
    ElMessage.success('测试邮件发送成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '测试邮件发送失败')
  } finally {
    testSending.value = false
  }
}

const handleSaveNotificationTypes = async () => {
  notificationSaving.value = true
  try {
    await saveDefectNotificationSettings({ types: notificationTypes.value })
    ElMessage.success('消息提醒设置已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存消息提醒设置失败')
  } finally {
    notificationSaving.value = false
  }
}

const handleAllowBrowserNotification = async () => {
  const nextPermission = await requestDefectNotificationPermission()
  permissionState.value = nextPermission

  if (nextPermission === 'granted') {
    showDefectNotificationPermissionPreview()
    ElMessage.success('浏览器通知权限已开启')
    return
  }
  if (nextPermission === 'denied') {
    ElMessage.warning('浏览器通知权限已被拒绝，请在浏览器设置中重新开启')
    return
  }
  if (nextPermission === 'unsupported') {
    ElMessage.warning('当前浏览器不支持通知能力')
  }
}

watch(
  () => props.fixedSubTab,
  nextSubTab => {
    activeSubTab.value = normalizeSubTab(nextSubTab)
  },
  { immediate: true }
)

onMounted(() => {
  loadPageData()
})
</script>

<style lang="scss" scoped>
.defect-notification-settings {
  min-height: auto;
  padding: 16px 20px 20px;
  background: #f5f7fa;
  overflow: visible;
}

.defect-notification-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }

  :deep(.el-tabs__content) {
    overflow: visible;
  }
}

.defect-notification-tabs--header-hidden {
  :deep(.el-tabs__header) {
    display: none;
  }
}

.settings-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.settings-card--secondary {
  margin-top: 16px;
}

.settings-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;

  h3 {
    margin: 0 0 6px;
    color: #303133;
    font-size: 16px;
  }

  p {
    margin: 0;
    color: #909399;
    line-height: 1.6;
  }
}

.settings-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.template-tip,
.permission-status {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.permission-status__origin {
  margin-left: 8px;
  color: #909399;
}

.template-tip {
  margin-bottom: 16px;
}

.type-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .defect-notification-settings {
    padding: 12px;
  }

  .settings-card {
    padding: 16px;
  }

  .settings-card__header {
    flex-direction: column;
  }
}
</style>
