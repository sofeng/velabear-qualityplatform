export const AI_GENERATION_PRIMARY_TAB_DEFS = Object.freeze([
  { name: 'conversation', label: 'AI产品' },
  { name: 'foundation', label: '基础配置' },
])

export const AI_GENERATION_TAB_DEFS = Object.freeze([
  { name: 'ai-products', label: 'AI产品', primary: 'conversation' },
  { name: 'enterprise-project-workbench', label: '企业项目研发工作台', primary: 'conversation' },
  { name: 'codex-chat', label: 'CodexChat', primary: 'conversation' },
  { name: 'projects', label: '项目管理', primary: 'foundation' },
  { name: 'versions', label: '版本管理', primary: 'foundation' },
  { name: 'ai-dev-configs', label: 'AI开发项目配置', primary: 'foundation' },
  { name: 'ai-dev-runtime-configs', label: 'AI开发环境配置', primary: 'foundation' },
])

export const AI_GENERATION_DEFAULT_TAB = 'ai-products'
export const AI_GENERATION_TAB_ORDER = Object.freeze(AI_GENERATION_TAB_DEFS.map(item => item.name))

const AI_GENERATION_TAB_SET = new Set(AI_GENERATION_TAB_ORDER)
const AI_GENERATION_TAB_ALIASES = Object.freeze({
  'ai-conversations': 'codex-chat',
  'ai-rd-platform': 'enterprise-project-workbench',
  'project-workbench': 'enterprise-project-workbench',
  'enterprise-workbench': 'enterprise-project-workbench',
  'new-project-blueprints': 'codex-chat',
  'ai-files': 'codex-chat',
  'requirement-analysis': 'codex-chat',
  'requirement-file-create': 'codex-chat',
  'requirement-manual-create': 'codex-chat',
  'ai-requirements': 'codex-chat',
  'generated-testcases': 'codex-chat',
  'ai-dev-tasks': 'codex-chat',
  'ai-dev-defects': 'codex-chat',
  'workflow-workbench': 'codex-chat',
  'ai-dev-build-configs': 'codex-chat',
  'deployment-targets': 'codex-chat',
  'deployment-templates': 'codex-chat',
  'build-artifacts': 'codex-chat',
  'deployment-executions': 'codex-chat',
  'rollback-records': 'codex-chat',
})

const normalizeValue = value => (Array.isArray(value) ? value[0] : value)

export const normalizeAiGenerationTab = value => {
  const normalized = String(normalizeValue(value) || '').trim()
  const canonical = AI_GENERATION_TAB_ALIASES[normalized] || normalized
  return AI_GENERATION_TAB_SET.has(canonical) ? canonical : ''
}

export const getAiGenerationTabDef = value => {
  const normalized = normalizeAiGenerationTab(value)
  return AI_GENERATION_TAB_DEFS.find(item => item.name === normalized) || null
}

export const getAiGenerationPrimaryTab = value => (
  getAiGenerationTabDef(value)?.primary || AI_GENERATION_PRIMARY_TAB_DEFS[0].name
)

export const getAiGenerationTabsByPrimary = primary => (
  AI_GENERATION_TAB_DEFS.filter(item => item.primary === primary)
)

export const getAiGenerationDefaultTabByPrimary = primary => (
  primary === 'conversation'
    ? AI_GENERATION_DEFAULT_TAB
    : getAiGenerationTabsByPrimary(primary)[0]?.name || AI_GENERATION_DEFAULT_TAB
)
