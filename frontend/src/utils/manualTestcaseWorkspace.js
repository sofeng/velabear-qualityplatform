export const MANUAL_TESTCASE_PRIMARY_TAB_DEFS = Object.freeze([
  { name: 'knowledge-assistant', label: '知识库助手', path: '/manual-testcases/list?tab=quality-knowledge-assistant' },
  { name: 'overview', label: '总览', path: '/manual-testcases/list?tab=requirement-overview' },
  { name: 'product', label: '需求', path: '/manual-testcases/list?tab=requirement-records' },
  { name: 'development', label: '开发', path: '/manual-testcases/list?tab=devselftest' },
  { name: 'testing', label: '测试', path: '/manual-testcases/list?tab=mindmaps' },
  { name: 'defect', label: '缺陷', path: '/manual-testcases/list?tab=version-defects' },
  { name: 'report', label: '报告', path: '/manual-testcases/list?tab=quality-report-list' },
  { name: 'config', label: '配置', path: '/manual-testcases/list?tab=configs' },
  { name: 'management', label: '管理', path: '/manual-testcases/list?tab=members' },
  { name: 'recording', label: '录制', path: '/manual-testcases/recording-scripts' },
  { name: 'wiki', label: 'Wiki', path: '/manual-testcases/wiki' },
])

export const MANUAL_TESTCASE_SECTION_DEFS = Object.freeze([
  { name: 'quality-knowledge-assistant', label: '知识库助手', primary: 'knowledge-assistant', workspace: true, hidden: true },
  { name: 'requirement-overview', label: '总览', primary: 'overview', workspace: true },
  { name: 'requirement-records', label: 'JIRA需求数据', primary: 'product', workspace: true },
  { name: 'version-requirements', label: '版本需求', primary: 'product', workspace: true },
  { name: 'devselftest', label: '自测测试点', primary: 'development', workspace: true },
  { name: 'technical-solution-designs', label: '技术方案设计', primary: 'development', workspace: true },
  { name: 'mindmaps', label: '测试脑图', primary: 'testing', workspace: true },
  { name: 'testcases', label: '测试用例', primary: 'testing', workspace: true },
  { name: 'testpoints', label: '测试点', primary: 'testing', workspace: true },
  { name: 'version-defect-analysis', label: '版本缺陷分析', primary: 'defect', workspace: true },
  { name: 'version-defects', label: '版本缺陷', primary: 'defect', workspace: true },
  { name: 'bug-records', label: '线上缺陷', primary: 'defect', workspace: true },
  { name: 'quality-report-list', label: '报告列表', primary: 'report', workspace: true },
  { name: 'quality-report-live', label: '实时质量分析', primary: 'report', workspace: true },
  { name: 'project-environments', label: '项目环境', primary: 'config', workspace: true },
  { name: 'knowledge-repositories', label: '代码仓库', primary: 'config', workspace: true },
  { name: 'project-asset-insight', label: '资产图谱', primary: 'config', workspace: true },
  { name: 'configs', label: 'JIRA接口', primary: 'config', workspace: true },
  { name: 'other-settings', label: 'JIRA编号URL', primary: 'config', workspace: true },
  { name: 'email-template-config', label: '邮件模板', primary: 'config', workspace: true },
  { name: 'email-config', label: '邮件配置', primary: 'config', workspace: true },
  { name: 'notification-settings', label: '消息提醒', primary: 'config', workspace: true },
  { name: 'list-sort-config', label: '列表排序', primary: 'config', workspace: true },
  { name: 'workflow-workbench', label: '流程工作台', primary: 'config', workspace: false, path: '/manual-testcases/workflow-workbench' },
  { name: 'members', label: '成员', primary: 'management', workspace: true },
  { name: 'groups', label: '组别', primary: 'management', workspace: true },
  { name: 'roles', label: '角色', primary: 'management', workspace: true },
  { name: 'projects', label: '项目', primary: 'management', workspace: true },
  { name: 'versions', label: '版本', primary: 'management', workspace: true },
  { name: 'permissions', label: '权限', primary: 'management', workspace: true },
  { name: 'recording-scripts', label: '脚本生成', primary: 'recording', workspace: false, path: '/manual-testcases/recording-scripts' },
  { name: 'automation-scripts', label: '脚本管理', primary: 'recording', workspace: false, path: '/manual-testcases/automation-scripts' },
  { name: 'snapshots', label: '快照管理', primary: 'recording', workspace: false, path: '/manual-testcases/snapshots' },
  { name: 'recordings', label: '录制管理', primary: 'recording', workspace: false, path: '/manual-testcases/recordings' },
  { name: 'controlled-browser-lab', label: '模拟页面组件', primary: 'recording', workspace: false, path: '/manual-testcases/controlled-browser-lab' },
  { name: 'flows', label: '流程管理', primary: 'recording', workspace: false, path: '/manual-testcases/flows' },
  { name: 'visual-flow', label: '流程图', primary: 'recording', workspace: false, path: '/manual-testcases/visual-flow' },
  { name: 'visual-flow-executions', label: '测试结果', primary: 'recording', workspace: false, path: '/manual-testcases/visual-flow-executions' },
  { name: 'wiki', label: 'Wiki', primary: 'wiki', workspace: false, path: '/manual-testcases/wiki' },
])

export const MANUAL_TESTCASE_WORKSPACE_TAB_ORDER = Object.freeze(
  MANUAL_TESTCASE_SECTION_DEFS.filter(item => item.workspace).map(item => item.name)
)

const MANUAL_TESTCASE_WORKSPACE_TAB_SET = new Set(MANUAL_TESTCASE_WORKSPACE_TAB_ORDER)
const MANUAL_TESTCASE_SECTION_MAP = new Map(MANUAL_TESTCASE_SECTION_DEFS.map(item => [item.name, item]))
const MANUAL_TESTCASE_PRIMARY_TAB_MAP = new Map(MANUAL_TESTCASE_PRIMARY_TAB_DEFS.map(item => [item.name, item]))
const MANUAL_TESTCASE_DIRECT_ROUTE_SECTION_MAP = new Map(
  MANUAL_TESTCASE_SECTION_DEFS
    .filter(item => !item.workspace && item.path)
    .map(item => [item.path, item.name])
)

const LEGACY_MANUAL_TESTCASE_TAB_MAP = Object.freeze({
  'testing-overview': 'quality-report-live',
  'quality-report-detail': 'quality-report-live',
  'quality-report-excel': 'quality-report-live',
  'excel-import': 'quality-report-live',
  'defect-notifications': 'email-config',
  'test-email': 'email-config',
})

const normalizeValue = value => (Array.isArray(value) ? value[0] : value)

export const normalizeManualTestcaseTab = value => {
  const normalized = String(normalizeValue(value) || '').trim()
  const mappedValue = LEGACY_MANUAL_TESTCASE_TAB_MAP[normalized] || normalized
  return MANUAL_TESTCASE_WORKSPACE_TAB_SET.has(mappedValue) ? mappedValue : ''
}

export const getManualTestcaseSectionDef = value => {
  const normalized = String(normalizeValue(value) || '').trim()
  return MANUAL_TESTCASE_SECTION_MAP.get(normalized) || null
}

export const getManualTestcasePrimaryTab = value => (
  getManualTestcaseSectionDef(value)?.primary || MANUAL_TESTCASE_PRIMARY_TAB_DEFS[0].name
)

export const getManualTestcasePrimaryTabDef = primary => (
  MANUAL_TESTCASE_PRIMARY_TAB_MAP.get(String(primary || '').trim()) || null
)

export const getManualTestcaseSectionsByPrimary = primary => (
  MANUAL_TESTCASE_SECTION_DEFS.filter(item => item.primary === primary)
)

export const getManualTestcaseWorkspaceSectionsByPrimary = primary => (
  getManualTestcaseSectionsByPrimary(primary).filter(item => item.workspace)
)

export const getManualTestcaseDefaultSectionByPrimary = primary => (
  getManualTestcaseSectionsByPrimary(primary)[0]?.name || MANUAL_TESTCASE_SECTION_DEFS[0].name
)

const getPreservedManualQuery = currentQuery => {
  const query = {}
  ;['project_id', 'version_id', 'category_id'].forEach(key => {
    const value = normalizeValue(currentQuery?.[key])
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      query[key] = String(value).trim()
    }
  })
  return query
}

export const buildManualTestcaseSectionLocation = (sectionName, currentQuery = {}) => {
  const sectionDef = getManualTestcaseSectionDef(sectionName)
  if (!sectionDef) {
    return null
  }

  const preservedQuery = getPreservedManualQuery(currentQuery)
  if (sectionDef.workspace) {
    return {
      path: '/manual-testcases/list',
      query: {
        ...preservedQuery,
        tab: sectionDef.name,
      },
    }
  }

  return {
    path: sectionDef.path,
    query: preservedQuery,
  }
}

export const buildManualTestcaseLocationFromPath = (rawPath, currentQuery = {}) => {
  const normalizedPath = String(rawPath || '').trim()
  if (!normalizedPath.startsWith('/manual-testcases')) {
    return normalizedPath
  }

  const parsedUrl = new URL(normalizedPath, 'https://manual-testcase.local')
  const query = Object.fromEntries(parsedUrl.searchParams.entries())
  const preservedQuery = getPreservedManualQuery(currentQuery)

  return {
    path: parsedUrl.pathname,
    query: {
      ...preservedQuery,
      ...query,
    },
  }
}

export const getManualTestcaseSectionNameByRoute = routeLike => {
  const path = String(routeLike?.path || '').trim()
  if (!path.startsWith('/manual-testcases')) {
    return ''
  }

  if (path === '/manual-testcases/list') {
    return normalizeManualTestcaseTab(routeLike?.query?.tab)
  }

  if (MANUAL_TESTCASE_DIRECT_ROUTE_SECTION_MAP.has(path)) {
    return MANUAL_TESTCASE_DIRECT_ROUTE_SECTION_MAP.get(path) || ''
  }

  if (path === '/manual-testcases/editor' || path === '/manual-testcases/view') {
    return normalizeManualTestcaseTab(routeLike?.query?.from_tab) || 'mindmaps'
  }

  if (path.startsWith('/manual-testcases/defects')) {
    return normalizeManualTestcaseTab(routeLike?.query?.tab) || 'version-defects'
  }

  if (path.startsWith('/manual-testcases/technical-solution-designs')) {
    return normalizeManualTestcaseTab(routeLike?.query?.tab) || 'technical-solution-designs'
  }

  if (path.startsWith('/manual-testcases/requirements')) {
    return normalizeManualTestcaseTab(routeLike?.query?.tab) || 'requirement-records'
  }

  return ''
}

export const getManualTestcasePrimaryMenuPath = primary => (
  getManualTestcasePrimaryTabDef(primary)?.path || MANUAL_TESTCASE_PRIMARY_TAB_DEFS[0].path
)

export const getManualTestcasePrimaryMenuPathByRoute = routeLike => {
  const sectionName = getManualTestcaseSectionNameByRoute(routeLike)
  if (!sectionName) {
    return getManualTestcasePrimaryMenuPath(MANUAL_TESTCASE_PRIMARY_TAB_DEFS[0].name)
  }

  return getManualTestcasePrimaryMenuPath(getManualTestcasePrimaryTab(sectionName))
}
