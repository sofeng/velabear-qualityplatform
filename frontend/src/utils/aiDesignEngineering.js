export const AI_DESIGN_DEFAULT_PROFILE_KEY = 'enterprise-stable'

export const AI_DESIGN_DEFAULT_PROFILE = Object.freeze({
  key: AI_DESIGN_DEFAULT_PROFILE_KEY,
  name: '企业稳健',
  fit: '研发平台 / 质量平台 / 管理后台',
  loginTitle: '企业级AI软件研发平台',
  loginSubtitle: '让交付快一点，稳一点',
  tokens: {
    primary: '#1456f0',
    secondary: '#0f766e',
    accent: '#f59e0b',
    bg: '#f6f8fb',
    surface: '#ffffff',
    text: '#172033',
    muted: '#667085',
    border: '#d8e0ea',
    radius: '8px',
    density: '常规密度',
    font: 'Inter / system-ui',
    shadow: '0 10px 24px rgba(15, 23, 42, 0.08)',
  },
  gates: ['低噪声界面', '表格可扫描', '操作路径明确', '权限状态清晰', '异常反馈完整'],
})

export const AI_DESIGN_DEFAULT_PAGE_TEMPLATES = Object.freeze(['login', 'dashboard', 'list', 'detail', 'form'])
export const AI_DESIGN_DEFAULT_QUALITY_GATES = Object.freeze(['tokens', 'responsive', 'playwright', 'overflow'])
export const AI_DESIGN_DEFAULT_FLOW = Object.freeze([
  '需求理解',
  '风格定向',
  'Token生成',
  '多页面预览',
  '代码生成',
  '视觉验收',
  '资产沉淀',
])

export const AI_DESIGN_DEFAULT_RULES = Object.freeze([
  'AI生成页面必须优先使用项目设计Token',
  '新增页面需匹配项目已保存的设计档案',
  '交付前必须进行Playwright桌面和移动端截图验证',
  '视觉修复必须基于截图中的具体问题，不做无关重构',
])

const clonePlain = value => JSON.parse(JSON.stringify(value || {}))

export const buildDefaultAIDesignStyleSpec = ({
  projectId = 'ai-app-default',
  projectName = '一句话生成应用',
  productName = '',
  productType = 'business-admin',
  deliveryMode = 'design-first',
  businessDomain = '',
  profile = AI_DESIGN_DEFAULT_PROFILE,
  pageTemplates = AI_DESIGN_DEFAULT_PAGE_TEMPLATES,
  qualityGates = AI_DESIGN_DEFAULT_QUALITY_GATES,
} = {}) => ({
  project: {
    id: projectId,
    name: projectName,
    productName: productName || projectName || '一句话生成应用',
    productType,
    deliveryMode,
    businessDomain,
  },
  designSystem: {
    profileKey: profile.key || AI_DESIGN_DEFAULT_PROFILE.key,
    profileName: profile.name || AI_DESIGN_DEFAULT_PROFILE.name,
    fit: profile.fit || AI_DESIGN_DEFAULT_PROFILE.fit,
    tokens: {
      ...clonePlain(AI_DESIGN_DEFAULT_PROFILE.tokens),
      ...clonePlain(profile.tokens),
    },
    pageTemplates: [...pageTemplates],
    gates: Array.isArray(profile.gates) ? [...profile.gates] : [...AI_DESIGN_DEFAULT_PROFILE.gates],
    qualityGates: [...qualityGates],
  },
  aiDevelopmentPolicy: {
    flow: [...AI_DESIGN_DEFAULT_FLOW],
    rules: [...AI_DESIGN_DEFAULT_RULES],
  },
})

export const normalizeAIDesignStyleSpec = (spec, fallback = {}) => {
  const source = spec && typeof spec === 'object' ? spec : {}
  const project = source.project && typeof source.project === 'object' ? source.project : {}
  const designSystem = source.designSystem || source.design_system || {}
  const tokens = designSystem.tokens || source.tokens || {}
  const profile = {
    ...AI_DESIGN_DEFAULT_PROFILE,
    key: designSystem.profileKey || designSystem.profile_key || source.profileKey || source.profile_key || AI_DESIGN_DEFAULT_PROFILE.key,
    name: designSystem.profileName || designSystem.profile_name || source.profileName || source.profile_name || AI_DESIGN_DEFAULT_PROFILE.name,
    fit: designSystem.fit || source.fit || AI_DESIGN_DEFAULT_PROFILE.fit,
    tokens: {
      ...clonePlain(AI_DESIGN_DEFAULT_PROFILE.tokens),
      ...clonePlain(tokens),
    },
    gates: Array.isArray(designSystem.gates) ? designSystem.gates : AI_DESIGN_DEFAULT_PROFILE.gates,
  }
  return buildDefaultAIDesignStyleSpec({
    projectId: project.id || fallback.projectId || 'ai-app-default',
    projectName: project.name || fallback.projectName || fallback.productName || '一句话生成应用',
    productName: project.productName || project.product_name || fallback.productName || fallback.projectName || '一句话生成应用',
    productType: project.productType || project.product_type || fallback.productType || 'business-admin',
    deliveryMode: project.deliveryMode || project.delivery_mode || fallback.deliveryMode || 'design-first',
    businessDomain: project.businessDomain || project.business_domain || fallback.businessDomain || '',
    profile,
    pageTemplates: Array.isArray(designSystem.pageTemplates)
      ? designSystem.pageTemplates
      : (Array.isArray(designSystem.page_templates) ? designSystem.page_templates : AI_DESIGN_DEFAULT_PAGE_TEMPLATES),
    qualityGates: Array.isArray(designSystem.qualityGates)
      ? designSystem.qualityGates
      : (Array.isArray(designSystem.quality_gates) ? designSystem.quality_gates : AI_DESIGN_DEFAULT_QUALITY_GATES),
  })
}

export const buildAIDesignStylePromptSection = (spec, {
  targetName = '',
  baseRequirement = '',
} = {}) => {
  const normalized = normalizeAIDesignStyleSpec(spec, {
    productName: targetName,
    businessDomain: baseRequirement,
  })
  const designSystem = normalized.designSystem
  const tokens = designSystem.tokens || {}
  const tokenRows = [
    ['主色', tokens.primary],
    ['辅助色', tokens.secondary],
    ['强调色', tokens.accent],
    ['页面背景', tokens.bg],
    ['卡片/表面', tokens.surface],
    ['正文颜色', tokens.text],
    ['辅助文字', tokens.muted],
    ['边框', tokens.border],
    ['圆角', tokens.radius],
    ['密度', tokens.density],
    ['字体', tokens.font],
    ['阴影', tokens.shadow],
  ]
  return [
    '【页面设计风格约束】',
    `已选页面设计风格：${designSystem.profileName}（${designSystem.fit}）。`,
    targetName ? `目标应用：${targetName}` : '',
    baseRequirement ? `原始需求摘要：${baseRequirement}` : '',
    `页面模板范围：${(designSystem.pageTemplates || []).join('、') || '登录页、工作台、列表页、详情页、表单页'}`,
    'Design Token：',
    ...tokenRows.filter(([, value]) => value).map(([label, value]) => `- ${label}: ${value}`),
    '开发落地要求：',
    '- 产品实现必须把上述 Token 映射为全局 CSS 变量或主题常量，并贯穿登录页、首页/工作台、列表、详情、表单、空态和异常态。',
    '- 主色、辅助色、强调色、圆角、表格/表单密度、字体和阴影必须与所选风格一致；不要随意切换成紫色渐变、米色系、深蓝单色或其他未选风格。',
    '- 生成完成后必须用真实浏览器截图核对桌面和移动端，确认文字不溢出、不重叠，按钮/表单可点击，整体视觉与所选风格一致。',
    '设计档案 JSON：',
    JSON.stringify(normalized, null, 2),
  ].filter(Boolean).join('\n')
}
