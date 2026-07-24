<template>
  <div class="notification-configs-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <h2>{{ pageTitle }}</h2>
            <p>{{ pageDescription }}</p>
          </div>
          <div class="card-header__actions">
            <el-button v-if="showReturnButton" :icon="ArrowLeft" @click="goBack">返回</el-button>
            <el-button :icon="Refresh" @click="fetchAllWebhookConfigs">刷新</el-button>
          </div>
        </div>
      </template>

      <section v-loading="loading" class="notification-card-section">
        <div class="notification-card-grid">
          <article
            v-for="bot in botMetas"
            :key="bot.type"
            class="notification-card"
          >
            <div class="notification-card-title">
              <div class="notification-thumb" :class="`notification-thumb--${bot.type}`">
                {{ bot.shortName }}
              </div>
              <div class="notification-title-block">
                <h3>{{ bot.label }}</h3>
                <span>{{ bot.description }}</span>
              </div>
            </div>

            <div class="notification-card-meta">
              <el-tag :type="webhookBots[bot.type].enabled ? 'success' : 'info'" size="small">
                {{ webhookBots[bot.type].enabled ? '启用中' : '已禁用' }}
              </el-tag>
              <el-tag size="small" :type="webhookBots[bot.type].connection_mode === 'auth' ? 'warning' : 'primary'">
                {{ getConnectionModeLabel(webhookBots[bot.type].connection_mode) }}
              </el-tag>
              <span>{{ getConfiguredLabel(bot.type) }}</span>
            </div>

            <el-form
              :ref="el => setFormRef(bot.type, el)"
              :model="webhookBots[bot.type]"
              label-position="top"
              class="notification-card-body"
            >
              <div class="connection-mode-row">
                <el-radio-group v-model="webhookBots[bot.type].connection_mode" size="small">
                  <el-radio-button label="webhook">Webhook配置</el-radio-button>
                  <el-radio-button label="auth">授权连接</el-radio-button>
                </el-radio-group>
              </div>

              <el-form-item label="机器人名称">
                <el-input
                  v-model="webhookBots[bot.type].name"
                  :placeholder="`请输入${bot.label}名称`"
                />
              </el-form-item>

              <template v-if="webhookBots[bot.type].connection_mode === 'webhook'">
                <el-form-item label="Webhook URL">
                  <el-input
                    v-model="webhookBots[bot.type].webhook_url"
                    :placeholder="bot.placeholder"
                  />
                  <div class="form-item-hint">{{ bot.hint }}</div>
                </el-form-item>
                <el-form-item v-if="bot.type === 'dingtalk'" label="签名密钥">
                  <el-input
                    v-model="webhookBots.dingtalk.secret"
                    :placeholder="webhookBots.dingtalk.has_secret ? '已配置，留空不变' : '请输入钉钉机器人签名密钥（可选）'"
                    type="password"
                    show-password
                  />
                </el-form-item>
              </template>

              <template v-else>
                <div class="auth-status-row">
                  <el-tag :type="getAuthStatusType(webhookBots[bot.type].auth_connection.status)" size="small">
                    {{ getAuthStatusLabel(webhookBots[bot.type].auth_connection.status) }}
                  </el-tag>
                  <span>{{ bot.authSummary }}</span>
                </div>

                <el-form-item
                  v-for="field in bot.authFields"
                  :key="field.key"
                  :label="field.label"
                  :required="isAuthorizeRequiredField(bot.type, field.key)"
                  :class="{ 'auth-field-missing': isAuthFieldMissing(bot.type, field.key) }"
                >
                  <el-input
                    v-model="webhookBots[bot.type].auth_connection[field.key]"
                    :type="field.secret ? 'password' : 'text'"
                    :show-password="field.secret"
                    :placeholder="getAuthFieldPlaceholder(bot.type, field)"
                  />
                  <div v-if="field.hint" class="form-item-hint">{{ field.hint }}</div>
                </el-form-item>
              </template>

              <el-form-item label="启用状态">
                <el-switch v-model="webhookBots[bot.type].enabled" />
              </el-form-item>
            </el-form>

            <div class="notification-card-footer">
              <button
                type="button"
                class="action-btn primary"
                :disabled="savingType === bot.type"
                @click="saveWebhookBot(bot.type)"
              >
                {{ savingType === bot.type ? '保存中' : '保存配置' }}
              </button>
              <button
                v-if="webhookBots[bot.type].connection_mode === 'auth'"
                type="button"
                class="action-btn"
                :disabled="authorizingType === bot.type || savingType === bot.type"
                @click="openAuthorizationPage(bot.type)"
              >
                {{ authorizingType === bot.type ? '授权中' : '打开授权页' }}
              </button>
              <button
                v-if="webhookBots[bot.type].connection_mode === 'auth'"
                type="button"
                class="action-btn danger"
                :disabled="disconnectingType === bot.type || !configIds[bot.type]"
                @click="disconnectAuthConnection(bot.type)"
              >
                断开授权
              </button>
            </div>
          </article>
        </div>
      </section>
    </el-card>
  </div>
</template>

<script>
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { computed, reactive, ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createUnifiedNotificationConfig,
  disconnectAuthorizedNotificationConnection,
  getUnifiedNotificationConfigs,
  getAuthorizedNotificationConnectionStatus,
  startAuthorizedNotificationOAuth,
  updateUnifiedNotificationConfig,
} from '@/api/core.js'

const AUTH_STATUS_LABELS = Object.freeze({
  connected: '已连接',
  disconnected: '未连接',
  error: '连接异常',
  pending: '待完善',
  authorizing: '授权中',
})

const AUTH_FIELD_DEFS = Object.freeze({
  feishu: [
    { key: 'app_id', label: 'App ID', hint: '飞书开放平台应用的 App ID。' },
    { key: 'app_secret', label: 'App Secret', secret: true, hint: '用于授权回调后换取访问凭证，不会明文返回。' },
    { key: 'oauth_scope', label: '授权范围', hint: '可按飞书应用权限填写；留空使用平台默认授权范围。' },
    { key: 'default_receive_id', label: '默认会话 ID', hint: '例如 chat_id，发送消息时作为默认接收目标。' },
    { key: 'receive_id_type', label: '会话 ID 类型', hint: '默认 chat_id，也可填写 open_id、user_id、union_id。' },
    { key: 'tenant_name', label: '租户名称' },
  ],
  wechat: [
    { key: 'corp_id', label: '企业 ID' },
    { key: 'corp_secret', label: '应用 Secret', secret: true, hint: '用于授权回调后换取企业微信访问凭证，不会明文返回。' },
    { key: 'agent_id', label: '应用 Agent ID' },
    { key: 'oauth_scope', label: '授权范围', hint: '默认 snsapi_privateinfo。' },
    { key: 'default_to_user', label: '默认接收成员', hint: '企业微信应用消息接收人，多个账号用 | 分隔，@all 表示全部。' },
    { key: 'corp_name', label: '企业名称' },
  ],
  dingtalk: [
    { key: 'app_key', label: 'AppKey' },
    { key: 'app_secret', label: 'AppSecret', secret: true, hint: '用于授权回调后换取访问凭证，不会明文返回。' },
    { key: 'oauth_scope', label: '授权范围', hint: '默认 openid corpid。' },
    { key: 'robot_code', label: '机器人编码', hint: '钉钉应用机器人 robotCode。' },
    { key: 'open_conversation_id', label: '群会话 ID', hint: '应用机器人发送群消息的 openConversationId。' },
    { key: 'tenant_name', label: '组织名称' },
  ],
})

const AUTH_AUTHORIZE_REQUIRED_FIELDS = Object.freeze({
  feishu: ['app_id', 'app_secret'],
  wechat: ['corp_id', 'corp_secret', 'agent_id'],
  dingtalk: ['app_key', 'app_secret'],
})

const BOT_METAS = Object.freeze([
  {
    type: 'feishu',
    label: '飞书机器人',
    shortName: '飞',
    description: '用于向飞书群发送研发和测试通知。',
    placeholder: 'https://open.feishu.cn/open-apis/bot/v2/hook/...',
    hint: '飞书机器人 Webhook URL 格式：https://open.feishu.cn/open-apis/bot/v2/hook/...',
    authSummary: '授权模式使用飞书开放平台应用机器人发送消息。',
    authFields: AUTH_FIELD_DEFS.feishu,
  },
  {
    type: 'wechat',
    label: '企微机器人',
    shortName: '企',
    description: '用于向企业微信群发送自动化通知。',
    placeholder: 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...',
    hint: '企业微信机器人 Webhook URL 格式：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...',
    authSummary: '授权模式使用企业微信自建应用消息，适合企业级通知。',
    authFields: AUTH_FIELD_DEFS.wechat,
  },
  {
    type: 'dingtalk',
    label: '钉钉机器人',
    shortName: '钉',
    description: '用于向钉钉群发送任务、缺陷和执行通知。',
    placeholder: 'https://oapi.dingtalk.com/robot/send?access_token=...',
    hint: '钉钉机器人 Webhook URL 格式：https://oapi.dingtalk.com/robot/send?access_token=...',
    authSummary: '授权模式使用钉钉应用机器人发送群聊消息。',
    authFields: AUTH_FIELD_DEFS.dingtalk,
  },
])

const createEmptyAuthConnection = botType => ({
  provider: botType,
  status: 'disconnected',
  ...Object.fromEntries((AUTH_FIELD_DEFS[botType] || []).map(field => [field.key, ''])),
})

const createEmptyBotConfig = botType => ({
  name: '',
  webhook_url: '',
  secret: '',
  has_secret: false,
  enabled: true,
  connection_mode: 'webhook',
  enable_ui_automation: false,
  enable_api_testing: false,
  auth_connection: createEmptyAuthConnection(botType),
})

const AUTH_POPUP_SIZE = Object.freeze({ width: 720, height: 760 })

const DEFAULT_AUTH_PERMISSION_ITEMS = Object.freeze({
  feishu: [
    '获取当前授权用户基本信息',
    '获取应用访问凭证用于发送飞书消息',
    '向已配置的飞书会话发送研发和测试通知',
    '持续访问已授权的通知配置数据',
  ],
  wechat: [
    '获取企业微信应用访问凭证',
    '识别当前授权成员基础信息',
    '向已配置的企业微信成员发送通知',
  ],
  dingtalk: [
    '获取钉钉应用访问凭证',
    '识别当前授权用户基础信息',
    '向已配置的钉钉群会话发送通知',
  ],
})

const escapePopupHtml = value => String(value == null ? '' : value).replace(/[&<>"']/g, char => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}[char]))

const toPopupInlineJson = value => JSON.stringify(value).replace(/[<>&\u2028\u2029]/g, char => ({
  '<': '\\u003c',
  '>': '\\u003e',
  '&': '\\u0026',
  '\u2028': '\\u2028',
  '\u2029': '\\u2029',
}[char]))

const splitScopeItems = scopeText => String(scopeText || '')
  .split(/[,\s，、]+/)
  .map(item => item.trim())
  .filter(Boolean)

const getAuthorizationPermissionItems = (botType, authConnection = {}) => {
  const configuredScopes = splitScopeItems(authConnection.oauth_scope)
  if (configuredScopes.length) {
    return configuredScopes.map(scope => `授权范围：${scope}`)
  }
  return DEFAULT_AUTH_PERMISSION_ITEMS[botType] || ['获取三方平台授权所需的基础信息']
}

const getAuthorizationPopupMeta = botType => (
  BOT_METAS.find(item => item.type === botType) || { label: '通知机器人', shortName: '授' }
)

const getAuthFieldLabel = (botType, fieldKey) => (
  (AUTH_FIELD_DEFS[botType] || []).find(field => field.key === fieldKey)?.label || fieldKey
)

const isAuthFieldConfigured = (authConnection = {}, fieldKey) => {
  if (String(authConnection[fieldKey] || '').trim()) return true
  return Boolean(authConnection[`has_${fieldKey}`])
}

const buildPopupScript = scriptContent => `<scr${'ipt'}>${scriptContent}</scr${'ipt'}>`

const buildAuthorizationPopupShell = ({
  botType,
  title,
  appName,
  permissionItems,
  buttonHtml,
  helperText,
  statusText,
  scriptHtml = '',
}) => {
  const botMeta = getAuthorizationPopupMeta(botType)
  const safeBotType = escapePopupHtml(botType)
  const safeShortName = escapePopupHtml(botMeta.shortName)
  const safeTitle = escapePopupHtml(title)
  const safeAppName = escapePopupHtml(appName || botMeta.label)
  const safeStatusText = escapePopupHtml(statusText || `当前平台账号的 ${appName || botMeta.label}`)
  const safeHelperText = escapePopupHtml(helperText || '该应用将可持续访问已授权的数据')
  const permissionHtml = permissionItems
    .map(item => `<li>${escapePopupHtml(item)}</li>`)
    .join('')

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${safeTitle}</title>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fff;
      color: #172033;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    .page {
      width: min(420px, calc(100vw - 32px));
      padding: 28px 0 22px;
      text-align: center;
    }
    .avatar {
      width: 48px;
      height: 48px;
      margin: 0 auto 10px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      color: #fff;
      font-size: 20px;
      font-weight: 800;
      box-shadow: 0 8px 20px rgba(37, 99, 235, .18);
    }
    .avatar--feishu { background: linear-gradient(135deg, #1d4ed8, #06b6d4); }
    .avatar--wechat { background: linear-gradient(135deg, #16a34a, #65a30d); }
    .avatar--dingtalk { background: linear-gradient(135deg, #0ea5e9, #4f46e5); }
    .identity {
      margin: 0 0 28px;
      color: #475569;
      font-size: 14px;
      line-height: 1.5;
    }
    h1 {
      margin: 0 0 30px;
      color: #0f172a;
      font-size: 20px;
      font-weight: 600;
      line-height: 1.4;
      letter-spacing: 0;
    }
    .scope-panel {
      width: 100%;
      max-height: 548px;
      overflow: auto;
      padding: 16px 20px;
      border-radius: 8px;
      background: #f7f8fa;
      text-align: left;
    }
    ul {
      margin: 0;
      padding-left: 18px;
      color: #475569;
      font-size: 14px;
      line-height: 2.15;
    }
    li::marker { color: #8b95a5; }
    .actions { margin-top: 0; }
    .primary-btn,
    .secondary-btn {
      width: 100%;
      height: 40px;
      border: 0;
      border-radius: 4px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
    }
    .primary-btn {
      background: #1c5cff;
      color: #fff;
    }
    .primary-btn:hover:not(:disabled) { background: #1852e6; }
    .primary-btn:disabled {
      cursor: not-allowed;
      background: #8bb0ff;
    }
    .secondary-btn {
      border: 1px solid #d0d5dd;
      background: #fff;
      color: #344054;
    }
    .footnote {
      margin: 12px 0 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.6;
    }
    .info-dot {
      display: inline-grid;
      place-items: center;
      width: 14px;
      height: 14px;
      margin-left: 4px;
      border: 1px solid #98a2b3;
      border-radius: 50%;
      font-size: 10px;
      line-height: 1;
    }
    .status-text {
      margin: 10px 0 0;
      color: #667085;
      font-size: 13px;
      line-height: 1.6;
    }
  </style>
</head>
<body>
  <main class="page">
    <div class="avatar avatar--${safeBotType}">${safeShortName}</div>
    <div class="identity">${safeStatusText}</div>
    <h1>${safeTitle}</h1>
    <section class="scope-panel">
      <ul>${permissionHtml}</ul>
    </section>
    <div class="actions">${buttonHtml}</div>
    <p class="footnote">${safeHelperText}<span class="info-dot">i</span></p>
    <p class="status-text">${safeAppName}</p>
  </main>
  ${scriptHtml}
</body>
</html>`
}

const buildAuthorizationPopupLoadingHtml = ({ botType, appName }) => buildAuthorizationPopupShell({
  botType,
  title: '正在准备授权页面',
  appName,
  statusText: `当前平台账号的 ${appName || getAuthorizationPopupMeta(botType).label}`,
  permissionItems: ['保存当前通知机器人配置', '生成安全授权 state', '获取三方授权页面地址'],
  buttonHtml: '<button class="primary-btn" type="button" disabled>准备中</button>',
  helperText: '请保持此窗口打开',
})

const buildAuthorizationPopupReadyHtml = ({ botType, appName, authConnection, authorizationUrl }) => {
  const authorizationUrlJson = toPopupInlineJson(authorizationUrl)
  const title = botType === 'feishu' ? '确定开通并授权以下权限吗?' : '确定授权以下权限吗?'
  return buildAuthorizationPopupShell({
    botType,
    title,
    appName,
    statusText: `当前平台账号的 ${appName || getAuthorizationPopupMeta(botType).label}`,
    permissionItems: getAuthorizationPermissionItems(botType, authConnection),
    buttonHtml: '<button id="authorize" class="primary-btn" type="button">开通并授权</button>',
    helperText: '该应用将可持续访问已授权的数据',
    scriptHtml: buildPopupScript(`
      const authorizationUrl = ${authorizationUrlJson};
      document.getElementById('authorize').addEventListener('click', () => {
        const button = document.getElementById('authorize');
        button.disabled = true;
        button.textContent = '正在跳转...';
        window.location.assign(authorizationUrl);
      });
    `),
  })
}

const buildAuthorizationPopupErrorHtml = ({ botType, appName, detail }) => buildAuthorizationPopupShell({
  botType,
  title: '授权页面打开失败',
  appName,
  statusText: `当前平台账号的 ${appName || getAuthorizationPopupMeta(botType).label}`,
  permissionItems: [detail || '请关闭窗口后重新发起授权。'],
  buttonHtml: '<button id="close" class="secondary-btn" type="button">关闭窗口</button>',
  helperText: '未发起三方授权',
  scriptHtml: buildPopupScript(`
    document.getElementById('close').addEventListener('click', () => window.close());
  `),
})

const writeAuthorizationPopup = (popup, html) => {
  if (!popup || popup.closed) return false
  try {
    popup.document.open()
    popup.document.write(html)
    popup.document.close()
    popup.focus()
    return true
  } catch (error) {
    console.error('渲染授权弹窗失败:', error)
    return false
  }
}

export default {
  name: 'NotificationConfigs',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const loading = ref(false)
    const savingType = ref('')
    const authorizingType = ref('')
    const disconnectingType = ref('')
    const formRefs = reactive({})
    const configIds = reactive({})
    const missingAuthFields = reactive({
      feishu: [],
      wechat: [],
      dingtalk: [],
    })
    const normalizeQueryValue = value => String(Array.isArray(value) ? value[0] : value || '').trim()
    const focusedBotType = computed(() => {
      const botType = normalizeQueryValue(route.query.bot_type)
      return BOT_METAS.some(item => item.type === botType) ? botType : ''
    })
    const focusedBotMeta = computed(() => BOT_METAS.find(item => item.type === focusedBotType.value) || null)
    const botMetas = computed(() => (
      focusedBotType.value ? BOT_METAS.filter(item => item.type === focusedBotType.value) : BOT_METAS
    ))
    const pageTitle = computed(() => focusedBotMeta.value ? `${focusedBotMeta.value.label}配置` : '通知机器人')
    const pageDescription = computed(() => (
      focusedBotMeta.value
        ? `配置${focusedBotMeta.value.label}，保存后可在 AI 会话中开启并调用。`
        : '配置飞书、企业微信、钉钉通知机器人，支持 Webhook 和授权连接。'
    ))
    const showReturnButton = computed(() => Boolean(normalizeQueryValue(route.query.return_to)))

    const goBack = () => {
      const returnPath = normalizeQueryValue(route.query.return_to) || '/ai-generation/workshop'
      const query = {}
      const workshopTab = normalizeQueryValue(route.query.return_workshop_tab)
      const configTab = normalizeQueryValue(route.query.return_config_tab)
      if (workshopTab) query.workshop_tab = workshopTab
      if (configTab) query.config_tab = configTab
      router.push({ path: returnPath, query })
    }

    const webhookBots = reactive({
      feishu: createEmptyBotConfig('feishu'),
      wechat: createEmptyBotConfig('wechat'),
      dingtalk: createEmptyBotConfig('dingtalk'),
    })

    const getConfigType = botType => ({
      feishu: 'webhook_feishu',
      wechat: 'webhook_wechat',
      dingtalk: 'webhook_dingtalk',
    })[botType]

    const getBotLabel = botType => BOT_METAS.find(item => item.type === botType)?.label || '机器人'

    const setFormRef = (botType, el) => {
      if (el) {
        formRefs[botType] = el
      }
    }

    const getConnectionModeLabel = mode => (mode === 'auth' ? '授权连接' : 'Webhook')

    const getAuthStatusLabel = status => AUTH_STATUS_LABELS[status] || '未连接'

    const getAuthStatusType = status => ({
      connected: 'success',
      error: 'danger',
      authorizing: 'warning',
      pending: 'warning',
      disconnected: 'info',
    })[status] || 'info'

    const getConfiguredLabel = botType => {
      const botConfig = webhookBots[botType]
      if (botConfig.connection_mode === 'auth') {
        return getAuthStatusLabel(botConfig.auth_connection.status)
      }
      return botConfig.webhook_url ? '已配置地址' : '未配置地址'
    }

    const getAuthFieldPlaceholder = (botType, field) => {
      const auth = webhookBots[botType].auth_connection
      if (field.secret && auth[`has_${field.key}`]) {
        return '已配置，留空不变'
      }
      return `请输入${field.label}`
    }

    const getAuthorizeMissingFields = botType => {
      const auth = webhookBots[botType].auth_connection || {}
      return (AUTH_AUTHORIZE_REQUIRED_FIELDS[botType] || [])
        .filter(fieldKey => !isAuthFieldConfigured(auth, fieldKey))
    }

    const getAuthorizeMissingLabels = botType => (
      getAuthorizeMissingFields(botType).map(fieldKey => getAuthFieldLabel(botType, fieldKey))
    )

    const isAuthorizeRequiredField = (botType, fieldKey) => (
      (AUTH_AUTHORIZE_REQUIRED_FIELDS[botType] || []).includes(fieldKey)
    )

    const isAuthFieldMissing = (botType, fieldKey) => (
      (missingAuthFields[botType] || []).includes(fieldKey)
    )

    const normalizeAuthConnection = (botType, authConnection = {}) => ({
      ...createEmptyAuthConnection(botType),
      ...authConnection,
      provider: botType,
      status: authConnection.status || 'disconnected',
    })

    const buildBotData = botType => {
      const botConfig = webhookBots[botType]
      const botData = {
        name: botConfig.name || getBotLabel(botType),
        webhook_url: botConfig.webhook_url,
        enabled: botConfig.enabled,
        connection_mode: botConfig.connection_mode,
        enable_ui_automation: false,
        enable_api_testing: false,
        auth_connection: normalizeAuthConnection(botType, botConfig.auth_connection),
      }

      if (botType === 'dingtalk' && botConfig.secret) {
        botData.secret = botConfig.secret
      }

      return botData
    }

    const getFirstConfig = async botType => {
      const response = await getUnifiedNotificationConfigs({ config_type: getConfigType(botType) })
      return response.data.results?.[0] || null
    }

    const saveWebhookBot = async (botType, options = {}) => {
      const formRef = formRefs[botType]
      if (!formRef) return false

      const valid = await new Promise(resolve => {
        formRef.validate(result => resolve(result))
      })
      if (!valid) return false

      savingType.value = botType
      try {
        const existingConfig = await getFirstConfig(botType)
        const botData = buildBotData(botType)

        if (existingConfig?.id) {
          await updateUnifiedNotificationConfig(existingConfig.id, {
            name: existingConfig.name || `${getBotLabel(botType)}配置`,
            config_type: getConfigType(botType),
            webhook_bots: {
              ...(existingConfig.webhook_bots || {}),
              [botType]: botData,
            },
            is_active: true,
          })
          configIds[botType] = existingConfig.id
          if (!options.silent) {
            ElMessage.success(`${getBotLabel(botType)}配置更新成功`)
          }
        } else {
          const response = await createUnifiedNotificationConfig({
            name: `${getBotLabel(botType)}配置`,
            config_type: getConfigType(botType),
            webhook_bots: {
              [botType]: botData,
            },
            is_active: true,
          })
          configIds[botType] = response.data.id
          if (!options.silent) {
            ElMessage.success(`${getBotLabel(botType)}配置创建成功`)
          }
        }

        await fetchWebhookConfig(botType)
        return true
      } catch (error) {
        console.error('保存通知机器人配置失败:', error)
        ElMessage.error(`${getBotLabel(botType)}配置保存失败: ${error.response?.data?.detail || error.message}`)
        return false
      } finally {
        savingType.value = ''
      }
    }

    const applyAuthStatus = (botType, statusPayload = {}) => {
      const auth = webhookBots[botType].auth_connection
      auth.status = statusPayload.status || auth.status || 'disconnected'
      auth.authorized_user_name = statusPayload.authorized_user_name || auth.authorized_user_name || ''
      auth.last_authorized_at = statusPayload.last_authorized_at || auth.last_authorized_at || ''
    }

    const pollAuthorizationStatus = async botType => {
      if (!configIds[botType]) return

      for (let index = 0; index < 18; index += 1) {
        await new Promise(resolve => setTimeout(resolve, index === 0 ? 1200 : 2500))
        try {
          const response = await getAuthorizedNotificationConnectionStatus(configIds[botType], { bot_type: botType })
          applyAuthStatus(botType, response.data || {})
          if (['connected', 'error', 'disconnected'].includes(response.data?.status)) {
            await fetchWebhookConfig(botType)
            return
          }
        } catch (error) {
          console.error('刷新授权状态失败:', error)
          return
        }
      }
      await fetchWebhookConfig(botType)
    }

    const openAuthorizationPage = async botType => {
      const missingFields = getAuthorizeMissingFields(botType)
      if (missingFields.length) {
        missingAuthFields[botType] = missingFields
        ElMessage.warning(`请先填写${getBotLabel(botType)}授权必填项：${getAuthorizeMissingLabels(botType).join('、')}`)
        return
      }
      missingAuthFields[botType] = []

      const popupName = `testhub-notification-oauth-${botType}-${Date.now()}`
      const popupFeatures = `width=${AUTH_POPUP_SIZE.width},height=${AUTH_POPUP_SIZE.height}`
      const popup = window.open('', popupName, popupFeatures)
      if (!popup) {
        ElMessage.warning('浏览器拦截了授权窗口，请允许弹窗后重试')
        return
      }

      const appName = webhookBots[botType].name || getBotLabel(botType)
      writeAuthorizationPopup(popup, buildAuthorizationPopupLoadingHtml({ botType, appName }))

      const saved = await saveWebhookBot(botType, { silent: true })
      if (!saved || !configIds[botType]) {
        writeAuthorizationPopup(popup, buildAuthorizationPopupErrorHtml({
          botType,
          appName,
          detail: '通知机器人配置尚未保存，无法发起授权。',
        }))
        return
      }

      authorizingType.value = botType
      try {
        const response = await startAuthorizedNotificationOAuth(configIds[botType], { bot_type: botType })
        applyAuthStatus(botType, response.data.auth_status || { status: 'authorizing' })
        const authorizationUrl = response.data.authorization_url
        if (!authorizationUrl) {
          ElMessage.error('未获取到授权页面地址')
          writeAuthorizationPopup(popup, buildAuthorizationPopupErrorHtml({
            botType,
            appName,
            detail: '未获取到授权页面地址。',
          }))
          return
        }

        if (botType === 'feishu') {
          writeAuthorizationPopup(popup, buildAuthorizationPopupReadyHtml({
            botType,
            appName,
            authConnection: webhookBots[botType].auth_connection,
            authorizationUrl,
          }))
          ElMessage.info('请在弹出的授权页面点击“开通并授权”')
        } else if (!popup.closed) {
          popup.location.assign(authorizationUrl)
          ElMessage.info('请在弹出的授权页面完成授权')
        }
        await pollAuthorizationStatus(botType)
      } catch (error) {
        console.error('打开授权页面失败:', error)
        writeAuthorizationPopup(popup, buildAuthorizationPopupErrorHtml({
          botType,
          appName,
          detail: error.response?.data?.detail || error.message,
        }))
        ElMessage.error(error.response?.data?.detail || error.message)
      } finally {
        authorizingType.value = ''
      }
    }

    const handleAuthorizationMessage = event => {
      if (event.origin !== window.location.origin) return
      const data = event.data || {}
      if (data.source !== 'testhub-notification-oauth') return
      if (data.ok) {
        ElMessage.success(data.detail || '授权完成')
      } else {
        ElMessage.error(data.detail || '授权失败')
      }
      authorizingType.value = ''
      fetchAllWebhookConfigs()
    }

    const disconnectAuthConnection = async botType => {
      if (!configIds[botType]) return

      try {
        await ElMessageBox.confirm(`确认断开${getBotLabel(botType)}授权连接吗？`, '断开授权', {
          type: 'warning',
          confirmButtonText: '断开',
          cancelButtonText: '取消',
        })
      } catch {
        return
      }

      disconnectingType.value = botType
      try {
        const response = await disconnectAuthorizedNotificationConnection(configIds[botType], { bot_type: botType })
        ElMessage.success(response.data.detail || '已断开授权连接')
        await fetchWebhookConfig(botType)
      } catch (error) {
        console.error('断开授权连接失败:', error)
        ElMessage.error(error.response?.data?.detail || error.message)
      } finally {
        disconnectingType.value = ''
      }
    }

    const fetchWebhookConfig = async botType => {
      try {
        const config = await getFirstConfig(botType)
        configIds[botType] = config?.id || ''
        const bot = config?.webhook_bots?.[botType]
        if (!bot) return

        webhookBots[botType].name = bot.name || ''
        webhookBots[botType].webhook_url = bot.webhook_url || ''
        webhookBots[botType].enabled = bot.enabled !== false
        webhookBots[botType].connection_mode = bot.connection_mode || 'webhook'
        webhookBots[botType].enable_ui_automation = false
        webhookBots[botType].enable_api_testing = false
        webhookBots[botType].auth_connection = normalizeAuthConnection(botType, bot.auth_connection || {})
        missingAuthFields[botType] = []
        if (botType === 'dingtalk') {
          webhookBots.dingtalk.secret = ''
          webhookBots.dingtalk.has_secret = Boolean(bot.has_secret)
        }
      } catch (error) {
        console.error('获取通知机器人配置失败:', error)
      }
    }

    const fetchAllWebhookConfigs = async () => {
      loading.value = true
      try {
        await Promise.all(botMetas.value.map(bot => fetchWebhookConfig(bot.type)))
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      window.addEventListener('message', handleAuthorizationMessage)
      fetchAllWebhookConfigs()
    })

    onBeforeUnmount(() => {
      window.removeEventListener('message', handleAuthorizationMessage)
    })

    watch(
      focusedBotType,
      () => {
        fetchAllWebhookConfigs()
      }
    )

    return {
      Refresh,
      ArrowLeft,
      loading,
      savingType,
      authorizingType,
      disconnectingType,
      botMetas,
      pageTitle,
      pageDescription,
      showReturnButton,
      configIds,
      webhookBots,
      setFormRef,
      getConfiguredLabel,
      getConnectionModeLabel,
      getAuthStatusLabel,
      getAuthStatusType,
      getAuthFieldPlaceholder,
      isAuthorizeRequiredField,
      isAuthFieldMissing,
      saveWebhookBot,
      openAuthorizationPage,
      disconnectAuthConnection,
      fetchAllWebhookConfigs,
      goBack,
    }
  },
}
</script>

<style scoped>
.notification-configs-container {
  min-height: 0;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.card-header h2 {
  margin: 0;
  color: #173d67;
  font-size: 20px;
  font-weight: 700;
}

.card-header p {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.notification-card-section {
  min-height: 260px;
}

.notification-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.notification-card {
  min-height: 560px;
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.notification-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.notification-card-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.notification-thumb {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  flex: 0 0 auto;
}

.notification-thumb--feishu {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
}

.notification-thumb--wechat {
  background: linear-gradient(135deg, #16a34a, #65a30d);
}

.notification-thumb--dingtalk {
  background: linear-gradient(135deg, #0ea5e9, #4f46e5);
}

.notification-title-block {
  min-width: 0;
}

.notification-title-block h3 {
  margin: 0;
  color: #173d67;
  font-size: 16px;
}

.notification-title-block span {
  display: block;
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.notification-card-meta,
.notification-card-footer {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.notification-card-meta {
  min-height: 26px;
  color: #667085;
  font-size: 12px;
}

.notification-card-body {
  border-top: 1px solid #eef2f7;
  padding-top: 12px;
  flex: 1;
}

.connection-mode-row {
  margin-bottom: 14px;
}

.auth-status-row {
  min-height: 28px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.form-item-hint {
  margin-top: 4px;
  color: #98a2b3;
  font-size: 12px;
  line-height: 1.5;
}

.auth-field-missing :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #ef4444 inset;
}

.notification-card-footer {
  margin-top: auto;
}

.action-btn {
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  height: 32px;
  background: #fff;
  cursor: pointer;
  color: #344054;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  min-width: 96px;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.action-btn:hover:not(:disabled) {
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.action-btn.primary {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.action-btn.primary:hover:not(:disabled) {
  border-color: #93c5fd;
  background: #dbeafe;
}

.action-btn.danger {
  border-color: #fecaca;
  background: #fff5f5;
  color: #b91c1c;
}

.action-btn.danger:hover:not(:disabled) {
  border-color: #fca5a5;
  background: #fee2e2;
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 1100px) {
  .notification-card-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 1101px) and (max-width: 1440px) {
  .notification-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
