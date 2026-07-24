import { AI_GENERATION_TAB_ORDER, normalizeAiGenerationTab } from '@/utils/aiGenerationWorkspace'
import {
  MANUAL_TESTCASE_PRIMARY_TAB_DEFS,
  MANUAL_TESTCASE_WORKSPACE_TAB_ORDER,
  normalizeManualTestcaseTab,
} from '@/utils/manualTestcaseWorkspace'

export const AI_GENERATION_PRIMARY_TAB_MENU_ITEMS = Object.freeze([
  {
    key: 'conversation',
    label: 'AI产品',
    path: '/ai-generation/products',
    permissionCodes: [
      'menu:ai-generation:conversation',
      'menu:ai-generation:list',
    ],
  },
  {
    key: 'foundation',
    label: '基础配置',
    path: '/ai-generation/list?tab=projects',
    permissionCodes: [
      'menu:ai-generation:foundation',
      'menu:ai-generation:projects',
      'menu:ai-generation:versions',
      'menu:ai-generation:ai-dev-configs',
      'menu:ai-generation:ai-dev-runtime-configs',
      'menu:ai-generation:list',
    ],
  },
])

const buildManualPrimaryMenuPermissionCodes = codes => Object.freeze({
  'knowledge-assistant': [
    codes.qualityKnowledgeAssistant,
    codes.list,
  ],
  overview: [
    codes.list,
    codes.requirementOverview,
    codes.testingOverview,
    codes.product,
    codes.versionRequirements,
    codes.testing,
    codes.mindmaps,
  ],
  product: [
    codes.product,
    codes.versionRequirements,
    codes.requirementRecords,
    codes.list,
  ],
  development: [
    codes.development,
    codes.devSelfTest,
    codes.technicalSolutionDesigns,
    codes.list,
  ],
  testing: [
    codes.testing,
    codes.mindmaps,
    codes.testcases,
    codes.testpoints,
    codes.list,
  ],
  defect: [
    codes.defect,
    codes.versionDefects,
    codes.bugRecords,
    codes.list,
  ],
  report: [
    codes.reports,
    codes.qualityReportList,
    codes.qualityReportLive,
    codes.list,
  ],
  config: [
    codes.config,
    codes.projectEnvironments,
    codes.knowledgeRepositories,
    codes.projectAssetInsight,
    codes.configs,
    codes.otherSettings,
    codes.emailTemplateConfig,
    codes.defectNotificationEmailConfig,
    codes.defectNotificationTestEmail,
    codes.defectNotificationSettings,
    codes.workflowWorkbench,
    codes.list,
  ],
  management: [
    codes.management,
    codes.members,
    codes.groups,
    codes.roles,
    codes.projects,
    codes.versions,
    codes.permissions,
    codes.list,
  ],
  recording: [
    codes.recording,
    codes.recordingScripts,
    codes.automationScripts,
    codes.snapshots,
    codes.recordings,
    codes.controlledBrowserLab,
    codes.flows,
    codes.visualFlow,
    codes.visualFlowExecutions,
    codes.list,
  ],
})

export const PERMISSION_CODES = Object.freeze({
  home: Object.freeze({
    view: 'menu:home:view',
    aiGeneration: 'menu:home:ai-generation',
    configuration: 'menu:home:configuration',
    manualTestcases: 'menu:home:manual-testcases',
  }),
  aiGeneration: Object.freeze({
    workspace: 'menu:ai-generation:list',
    list: 'menu:ai-generation:list',
    conversation: 'menu:ai-generation:conversation',
    workshop: 'menu:ai-generation:workshop',
    foundation: 'menu:ai-generation:foundation',
    aiConversations: 'menu:ai-generation:conversation',
    files: 'menu:ai-generation:files',
    newProjectBlueprints: 'menu:ai-generation:new-project-blueprints',
    projects: 'menu:ai-generation:projects',
    versions: 'menu:ai-generation:versions',
    promptConfig: 'menu:ai-generation:prompt-config',
    requirement: 'menu:ai-generation:requirement',
    requirementAnalysis: 'menu:ai-generation:requirement-analysis',
    aiRequirements: 'menu:ai-generation:ai-requirements',
    generatedTestcases: 'menu:ai-generation:generated-testcases',
    testcaseCreate: 'button:ai-generation:testcases:create',
    development: 'menu:ai-generation:development',
    aiDevConfigs: 'menu:ai-generation:ai-dev-configs',
    aiDevRepositoryConfigs: 'menu:ai-generation:ai-dev-repository-configs',
    aiDevLlmConfigs: 'menu:ai-generation:ai-dev-llm-configs',
    aiDevTestToolConfigs: 'menu:ai-generation:ai-dev-test-tool-configs',
    aiDevRuntimeConfigs: 'menu:ai-generation:ai-dev-runtime-configs',
    aiDevBuildConfigs: 'menu:ai-generation:ai-dev-build-configs',
    aiDevTasks: 'menu:ai-generation:ai-dev-tasks',
    workflowWorkbench: 'menu:ai-generation:workflow-workbench',
    defect: 'menu:ai-generation:defect',
    operations: 'menu:ai-generation:operations',
    deploymentTargets: 'menu:ai-generation:deployment-targets',
    deploymentTemplates: 'menu:ai-generation:deployment-templates',
    buildArtifacts: 'menu:ai-generation:build-artifacts',
    deploymentExecutions: 'menu:ai-generation:deployment-executions',
    rollbackRecords: 'menu:ai-generation:rollback-records',
    skill: 'menu:ai-generation:skill',
    agent: 'menu:ai-generation:agent',
    flow: 'menu:ai-generation:flow',
    mcp: 'menu:ai-generation:mcp',
    marketplace: 'menu:ai-generation:marketplace',
    tools: 'menu:ai-generation:tools',
    cicd: 'menu:ai-generation:ci-cd',
  }),
  manualTestcases: Object.freeze({
    workspace: 'menu:manual-testcases:list',
    list: 'menu:manual-testcases:list',
    qualityKnowledgeAssistant: 'menu:manual-testcases:quality-knowledge-assistant',
    overview: 'menu:manual-testcases:list',
    requirementOverview: 'menu:manual-testcases:requirement-overview',
    testingOverview: 'menu:manual-testcases:testing-overview',
    product: 'menu:manual-testcases:product',
    versionRequirements: 'menu:manual-testcases:version-requirements',
    requirementRecords: 'menu:manual-testcases:requirement-records',
    development: 'menu:manual-testcases:development',
    devSelfTest: 'menu:manual-testcases:devselftest',
    technicalSolutionDesigns: 'menu:manual-testcases:technical-solution-designs',
    testing: 'menu:manual-testcases:testing',
    mindmaps: 'menu:manual-testcases:mindmaps',
    testcases: 'menu:manual-testcases:testcases',
    testpoints: 'menu:manual-testcases:testpoints',
    defect: 'menu:manual-testcases:defect',
    versionDefects: 'menu:manual-testcases:version-defects',
    bugRecords: 'menu:manual-testcases:bug-records',
    reports: 'menu:manual-testcases:reports',
    qualityReportList: 'menu:manual-testcases:quality-report-list',
    qualityReportLive: 'menu:manual-testcases:quality-report-live',
    config: 'menu:manual-testcases:config',
    projectEnvironments: 'menu:manual-testcases:project-environments',
    knowledgeRepositories: 'menu:manual-testcases:knowledge-repositories',
    projectAssetInsight: 'menu:manual-testcases:project-asset-insight',
    configs: 'menu:manual-testcases:configs',
    otherSettings: 'menu:manual-testcases:other-settings',
    defectNotifications: 'menu:manual-testcases:defect-notifications',
    emailTemplateConfig: 'menu:manual-testcases:defect-notifications',
    defectNotificationEmailConfig: 'menu:manual-testcases:defect-notifications:email-config',
    defectNotificationTestEmail: 'menu:manual-testcases:defect-notifications:test-email',
    defectNotificationSettings: 'menu:manual-testcases:defect-notifications:notification-settings',
    listSortConfig: 'menu:manual-testcases:list-sort-config',
    management: 'menu:manual-testcases:management',
    members: 'menu:manual-testcases:members',
    groups: 'menu:manual-testcases:groups',
    roles: 'menu:manual-testcases:roles',
    projects: 'menu:manual-testcases:projects',
    versions: 'menu:manual-testcases:versions',
    permissions: 'menu:manual-testcases:permissions',
    permissionUiRolePermissions: 'menu:manual-testcases:permissions:ui-role-permissions',
    permissionCatalog: 'menu:manual-testcases:permissions:permission-catalog',
    projectCreate: 'button:manual-testcases:projects:create',
    projectEdit: 'button:manual-testcases:projects:edit',
    projectDelete: 'button:manual-testcases:projects:delete',
    versionCreate: 'button:manual-testcases:versions:create',
    versionEdit: 'button:manual-testcases:versions:edit',
    versionDelete: 'button:manual-testcases:versions:delete',
    versionSetDefault: 'action:manual-testcases:versions:set-default',
    recording: 'menu:manual-testcases:recording',
    recordingScripts: 'menu:manual-testcases:recording-scripts',
    automationScripts: 'menu:manual-testcases:automation-scripts',
    snapshots: 'menu:manual-testcases:snapshots',
    recordings: 'menu:manual-testcases:recordings',
    controlledBrowserLab: 'menu:manual-testcases:controlled-browser-lab',
    flows: 'menu:manual-testcases:flows',
    visualFlow: 'menu:manual-testcases:visual-flow',
    visualFlowExecutions: 'menu:manual-testcases:visual-flow-executions',
    workflowWorkbench: 'menu:manual-testcases:workflow-workbench',
    permissionCreate: 'button:manual-testcases:permissions:create',
    permissionEdit: 'button:manual-testcases:permissions:edit',
    permissionDelete: 'button:manual-testcases:permissions:delete',
    permissionAssign: 'action:manual-testcases:permissions:assign',
  }),
})

const HOME_CODES = PERMISSION_CODES.home
const AI_GENERATION_CODES = PERMISSION_CODES.aiGeneration
const MANUAL_TESTCASE_CODES = PERMISSION_CODES.manualTestcases

const normalizePermissionCandidateList = permissionCandidates => {
  if (Array.isArray(permissionCandidates)) {
    return permissionCandidates
  }

  return permissionCandidates ? [permissionCandidates] : []
}

export const getViewPermissionCode = permissionCode => {
  const normalizedCode = String(permissionCode || '').trim()
  if (!normalizedCode.startsWith('menu:')) {
    return ''
  }

  return `button:${normalizedCode.slice(5)}:view`
}

export const getPermissionAccessCandidates = permissionCandidates => {
  const expandedCandidates = []
  const seenCandidates = new Set()

  normalizePermissionCandidateList(permissionCandidates).forEach(item => {
    const normalizedCode = String(item || '').trim()
    if (!normalizedCode) {
      return
    }

    ;[normalizedCode, getViewPermissionCode(normalizedCode)].forEach(candidate => {
      if (!candidate || seenCandidates.has(candidate)) {
        return
      }

      seenCandidates.add(candidate)
      expandedCandidates.push(candidate)
    })
  })

  return expandedCandidates
}

export const hasPermissionAccess = (permissionCandidates, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  return getPermissionAccessCandidates(permissionCandidates).some(code => hasPermissionCode(code))
}

const MANUAL_TESTCASE_TAB_ORDER = MANUAL_TESTCASE_WORKSPACE_TAB_ORDER

const MANUAL_PRIMARY_MENU_PERMISSION_CODES = buildManualPrimaryMenuPermissionCodes(MANUAL_TESTCASE_CODES)

export const MANUAL_TESTCASE_PRIMARY_TAB_MENU_ITEMS = Object.freeze(
  MANUAL_TESTCASE_PRIMARY_TAB_DEFS.map(item => ({
    key: item.name,
    label: item.label,
    path: item.path,
    permissionCodes: MANUAL_PRIMARY_MENU_PERMISSION_CODES[item.name] || [MANUAL_TESTCASE_CODES.list],
  }))
)

const LEGACY_AI_GENERATION_ROUTE_TAB_MAP = Object.freeze({
  '/ai-generation/projects': 'projects',
  '/ai-generation/requirement-analysis': 'codex-chat',
  '/ai-generation/products': 'ai-products',
  '/ai-generation/products/all': 'ai-products',
  '/ai-generation/products/project-workbench': 'enterprise-project-workbench',
  '/ai-generation/ai-requirements': 'codex-chat',
  '/ai-generation/generated-testcases': 'codex-chat',
  '/ai-generation/ai-conversations': 'codex-chat',
  '/ai-generation/codex-chat': 'codex-chat',
  '/ai-generation/ai-files': 'codex-chat',
  '/ai-generation/new-project-blueprints': 'codex-chat',
  '/ai-generation/ai-dev-tasks': 'codex-chat',
  '/ai-generation/ai-dev-defects': 'codex-chat',
  '/ai-generation/workflow-workbench': 'codex-chat',
  '/ai-generation/versions': 'versions',
  '/ai-generation/ai-dev-configs': 'ai-dev-configs',
  '/ai-generation/ai-dev-runtime-configs': 'ai-dev-runtime-configs',
  '/ai-generation/ai-dev-build-configs': 'codex-chat',
  '/ai-generation/deployment-targets': 'codex-chat',
  '/ai-generation/deployment-templates': 'codex-chat',
  '/ai-generation/build-artifacts': 'codex-chat',
  '/ai-generation/deployment-executions': 'codex-chat',
  '/ai-generation/rollback-records': 'codex-chat',
})

const AI_GENERATION_TAB_PERMISSION_CANDIDATES = Object.freeze({
  'ai-products': [
    AI_GENERATION_CODES.aiConversations,
    AI_GENERATION_CODES.conversation,
    AI_GENERATION_CODES.list,
  ],
  'enterprise-project-workbench': [
    AI_GENERATION_CODES.conversation,
    AI_GENERATION_CODES.list,
  ],
  'codex-chat': [
    AI_GENERATION_CODES.aiConversations,
    AI_GENERATION_CODES.conversation,
    AI_GENERATION_CODES.list,
  ],
  projects: [AI_GENERATION_CODES.projects, AI_GENERATION_CODES.foundation],
  versions: [AI_GENERATION_CODES.versions, AI_GENERATION_CODES.foundation],
  'ai-dev-configs': [AI_GENERATION_CODES.aiDevConfigs, AI_GENERATION_CODES.foundation],
  'ai-dev-runtime-configs': [
    AI_GENERATION_CODES.aiDevRuntimeConfigs,
    AI_GENERATION_CODES.aiDevConfigs,
    AI_GENERATION_CODES.foundation,
  ],
})

const MANUAL_TESTCASE_TAB_PERMISSION_CANDIDATES = Object.freeze({
  'quality-knowledge-assistant': [
    MANUAL_TESTCASE_CODES.qualityKnowledgeAssistant,
    MANUAL_TESTCASE_CODES.list,
  ],
  mindmaps: [MANUAL_TESTCASE_CODES.mindmaps, MANUAL_TESTCASE_CODES.testing],
  testcases: [MANUAL_TESTCASE_CODES.testcases, MANUAL_TESTCASE_CODES.testing],
  testpoints: [MANUAL_TESTCASE_CODES.testpoints, MANUAL_TESTCASE_CODES.testing],
  devselftest: [MANUAL_TESTCASE_CODES.devSelfTest, MANUAL_TESTCASE_CODES.development],
  'technical-solution-designs': [
    MANUAL_TESTCASE_CODES.technicalSolutionDesigns,
    MANUAL_TESTCASE_CODES.development,
  ],
  'requirement-overview': [
    MANUAL_TESTCASE_CODES.requirementOverview,
    MANUAL_TESTCASE_CODES.list,
    MANUAL_TESTCASE_CODES.versionRequirements,
    MANUAL_TESTCASE_CODES.product,
  ],
  'testing-overview': [
    MANUAL_TESTCASE_CODES.testingOverview,
    MANUAL_TESTCASE_CODES.list,
    MANUAL_TESTCASE_CODES.mindmaps,
    MANUAL_TESTCASE_CODES.testing,
  ],
  'version-requirements': [MANUAL_TESTCASE_CODES.versionRequirements, MANUAL_TESTCASE_CODES.product],
  'requirement-records': [MANUAL_TESTCASE_CODES.requirementRecords, MANUAL_TESTCASE_CODES.product],
  'version-defect-analysis': [MANUAL_TESTCASE_CODES.versionDefects, MANUAL_TESTCASE_CODES.defect],
  'version-defects': [MANUAL_TESTCASE_CODES.versionDefects, MANUAL_TESTCASE_CODES.defect],
  'bug-records': [MANUAL_TESTCASE_CODES.bugRecords, MANUAL_TESTCASE_CODES.defect],
  'project-environments': [MANUAL_TESTCASE_CODES.projectEnvironments, MANUAL_TESTCASE_CODES.config],
  'knowledge-repositories': [MANUAL_TESTCASE_CODES.knowledgeRepositories, MANUAL_TESTCASE_CODES.config],
  'project-asset-insight': [MANUAL_TESTCASE_CODES.projectAssetInsight, MANUAL_TESTCASE_CODES.knowledgeRepositories, MANUAL_TESTCASE_CODES.config],
  configs: [MANUAL_TESTCASE_CODES.configs, MANUAL_TESTCASE_CODES.config],
  'other-settings': [MANUAL_TESTCASE_CODES.otherSettings, MANUAL_TESTCASE_CODES.config],
  'email-template-config': [
    MANUAL_TESTCASE_CODES.emailTemplateConfig,
    MANUAL_TESTCASE_CODES.config,
  ],
  'email-config': [
    MANUAL_TESTCASE_CODES.defectNotificationEmailConfig,
    MANUAL_TESTCASE_CODES.defectNotificationTestEmail,
    MANUAL_TESTCASE_CODES.config,
    MANUAL_TESTCASE_CODES.emailTemplateConfig,
  ],
  'test-email': [
    MANUAL_TESTCASE_CODES.defectNotificationTestEmail,
    MANUAL_TESTCASE_CODES.config,
    MANUAL_TESTCASE_CODES.emailTemplateConfig,
  ],
  'notification-settings': [
    MANUAL_TESTCASE_CODES.defectNotificationSettings,
    MANUAL_TESTCASE_CODES.config,
    MANUAL_TESTCASE_CODES.emailTemplateConfig,
  ],
  'list-sort-config': [MANUAL_TESTCASE_CODES.listSortConfig, MANUAL_TESTCASE_CODES.config],
  'quality-report-list': [MANUAL_TESTCASE_CODES.qualityReportList, MANUAL_TESTCASE_CODES.reports],
  'quality-report-live': [MANUAL_TESTCASE_CODES.qualityReportLive, MANUAL_TESTCASE_CODES.reports],
  members: [MANUAL_TESTCASE_CODES.members, MANUAL_TESTCASE_CODES.management],
  groups: [MANUAL_TESTCASE_CODES.groups, MANUAL_TESTCASE_CODES.management],
  roles: [MANUAL_TESTCASE_CODES.roles, MANUAL_TESTCASE_CODES.management],
  projects: [MANUAL_TESTCASE_CODES.projects, MANUAL_TESTCASE_CODES.management],
  versions: [MANUAL_TESTCASE_CODES.versions, MANUAL_TESTCASE_CODES.management],
  permissions: [MANUAL_TESTCASE_CODES.permissions, MANUAL_TESTCASE_CODES.management],
})

const MANUAL_TESTCASE_SECTION_PERMISSION_CANDIDATES = Object.freeze({
  ...MANUAL_TESTCASE_TAB_PERMISSION_CANDIDATES,
  'recording-scripts': [MANUAL_TESTCASE_CODES.recordingScripts, MANUAL_TESTCASE_CODES.recording],
  'automation-scripts': [MANUAL_TESTCASE_CODES.automationScripts, MANUAL_TESTCASE_CODES.recording],
  snapshots: [MANUAL_TESTCASE_CODES.snapshots, MANUAL_TESTCASE_CODES.recording],
  recordings: [MANUAL_TESTCASE_CODES.recordings, MANUAL_TESTCASE_CODES.recording],
  'controlled-browser-lab': [MANUAL_TESTCASE_CODES.controlledBrowserLab, MANUAL_TESTCASE_CODES.recording],
  flows: [MANUAL_TESTCASE_CODES.flows, MANUAL_TESTCASE_CODES.recording],
  'visual-flow': [MANUAL_TESTCASE_CODES.visualFlow, MANUAL_TESTCASE_CODES.recording],
  'visual-flow-executions': [MANUAL_TESTCASE_CODES.visualFlowExecutions, MANUAL_TESTCASE_CODES.recording],
  'workflow-workbench': [MANUAL_TESTCASE_CODES.workflowWorkbench, MANUAL_TESTCASE_CODES.config],
})

export const AI_GENERATION_TAB_PERMISSION_CODES = Object.freeze(
  Object.fromEntries(
    Object.entries(AI_GENERATION_TAB_PERMISSION_CANDIDATES).map(([tab, codes]) => [tab, codes[0]])
  )
)

export const MANUAL_TESTCASE_TAB_PERMISSION_CODES = Object.freeze(
  Object.fromEntries(
    Object.entries(MANUAL_TESTCASE_TAB_PERMISSION_CANDIDATES).map(([tab, codes]) => [tab, codes[0]])
  )
)

export const AI_WORKSPACE_ENTRY_PERMISSION_CODES = Object.freeze([
  AI_GENERATION_CODES.list,
  AI_GENERATION_CODES.conversation,
  AI_GENERATION_CODES.workshop,
  'menu:ai-generation:workshop-models',
  'menu:ai-generation:workshop-test-tools',
  'menu:ai-generation:workshop-ui-env',
  'menu:ai-generation:workshop-integrations',
  'menu:ai-generation:workshop-notifications',
  'menu:ai-generation:workshop-ai-session',
  AI_GENERATION_CODES.foundation,
  AI_GENERATION_CODES.projects,
  AI_GENERATION_CODES.versions,
  AI_GENERATION_CODES.aiDevConfigs,
  AI_GENERATION_CODES.aiDevRuntimeConfigs,
  'menu:configuration:ai-model',
  'menu:configuration:ui-env',
  'menu:configuration:scheduled-task',
])

export const AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES = Object.freeze({
  llm: [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    'menu:ai-generation:workshop-models',
    'menu:configuration:ai-model',
    AI_GENERATION_CODES.aiDevLlmConfigs,
  ],
  'test-tools': [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    'menu:ai-generation:workshop-test-tools',
    AI_GENERATION_CODES.aiDevTestToolConfigs,
  ],
  'ui-env': [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    'menu:ai-generation:workshop-ui-env',
    'menu:configuration:ui-env',
  ],
  git: [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    'menu:ai-generation:workshop-integrations',
    AI_GENERATION_CODES.aiDevRepositoryConfigs,
    AI_GENERATION_CODES.cicd,
  ],
  notifications: [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    'menu:ai-generation:workshop-notifications',
    'menu:configuration:scheduled-task',
  ],
  robots: [
    AI_GENERATION_CODES.workshop,
    AI_GENERATION_CODES.list,
    AI_GENERATION_CODES.conversation,
    'menu:ai-generation:workshop-ai-session',
    'menu:ai-generation:workshop-notifications',
    'menu:configuration:scheduled-task',
  ],
})

export const AI_WORKSHOP_TAB_PERMISSION_CANDIDATES = Object.freeze({
  skills: [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  plugins: [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  prompts: [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  'design-engineering': [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  agents: [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  flows: [AI_GENERATION_CODES.workshop, AI_GENERATION_CODES.list],
  'ai-session': AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.robots,
  models: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.llm,
  'test-tools': [
    ...AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES['test-tools'],
    ...AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES['ui-env'],
  ],
  integrations: [
    ...AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.git,
    ...AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.notifications,
  ],
})

export const getAIGenerationPrimaryTabMenuItems = () => AI_GENERATION_PRIMARY_TAB_MENU_ITEMS.map(item => ({
  key: item.key,
  label: item.label,
  path: item.path,
  permissionCodes: [...item.permissionCodes],
}))

export const getManualTestcasePrimaryTabMenuItems = () => MANUAL_TESTCASE_PRIMARY_TAB_MENU_ITEMS.map(item => ({
  key: item.key,
  label: item.label,
  path: item.path,
  permissionCodes: item.permissionCodes,
}))

export const MANUAL_TESTCASE_WORKSPACE_ENTRY_PERMISSION_CODES = Object.freeze([
  MANUAL_TESTCASE_CODES.list,
  MANUAL_TESTCASE_CODES.requirementOverview,
  MANUAL_TESTCASE_CODES.testingOverview,
  MANUAL_TESTCASE_CODES.product,
  MANUAL_TESTCASE_CODES.versionRequirements,
  MANUAL_TESTCASE_CODES.requirementRecords,
  MANUAL_TESTCASE_CODES.development,
  MANUAL_TESTCASE_CODES.devSelfTest,
  MANUAL_TESTCASE_CODES.technicalSolutionDesigns,
  MANUAL_TESTCASE_CODES.testing,
  MANUAL_TESTCASE_CODES.mindmaps,
  MANUAL_TESTCASE_CODES.testcases,
  MANUAL_TESTCASE_CODES.testpoints,
  MANUAL_TESTCASE_CODES.defect,
  MANUAL_TESTCASE_CODES.versionDefects,
  MANUAL_TESTCASE_CODES.bugRecords,
  MANUAL_TESTCASE_CODES.reports,
  MANUAL_TESTCASE_CODES.qualityReportList,
  MANUAL_TESTCASE_CODES.qualityReportLive,
  MANUAL_TESTCASE_CODES.config,
  MANUAL_TESTCASE_CODES.projectEnvironments,
  MANUAL_TESTCASE_CODES.knowledgeRepositories,
  MANUAL_TESTCASE_CODES.projectAssetInsight,
  MANUAL_TESTCASE_CODES.configs,
  MANUAL_TESTCASE_CODES.otherSettings,
  MANUAL_TESTCASE_CODES.emailTemplateConfig,
  MANUAL_TESTCASE_CODES.defectNotifications,
  MANUAL_TESTCASE_CODES.defectNotificationEmailConfig,
  MANUAL_TESTCASE_CODES.defectNotificationTestEmail,
  MANUAL_TESTCASE_CODES.defectNotificationSettings,
  MANUAL_TESTCASE_CODES.management,
  MANUAL_TESTCASE_CODES.members,
  MANUAL_TESTCASE_CODES.groups,
  MANUAL_TESTCASE_CODES.roles,
  MANUAL_TESTCASE_CODES.projects,
  MANUAL_TESTCASE_CODES.versions,
  MANUAL_TESTCASE_CODES.permissions,
  MANUAL_TESTCASE_CODES.recording,
  MANUAL_TESTCASE_CODES.recordingScripts,
  MANUAL_TESTCASE_CODES.automationScripts,
  MANUAL_TESTCASE_CODES.snapshots,
  MANUAL_TESTCASE_CODES.recordings,
  MANUAL_TESTCASE_CODES.controlledBrowserLab,
  MANUAL_TESTCASE_CODES.flows,
  MANUAL_TESTCASE_CODES.visualFlow,
  MANUAL_TESTCASE_CODES.workflowWorkbench,
])

export const HOME_CARD_PERMISSION_CODES = Object.freeze([
  HOME_CODES.aiGeneration,
  HOME_CODES.manualTestcases,
])

const AI_SCOPED_WORKSPACE_PERMISSION_CODES = Object.freeze(
  getPermissionAccessCandidates(
    AI_WORKSPACE_ENTRY_PERMISSION_CODES.filter(code => code !== AI_GENERATION_CODES.list)
  )
)

const MANUAL_TESTCASE_SCOPED_WORKSPACE_PERMISSION_CODES = Object.freeze(
  getPermissionAccessCandidates(
    MANUAL_TESTCASE_WORKSPACE_ENTRY_PERMISSION_CODES.filter(code => code !== MANUAL_TESTCASE_CODES.list)
  )
)

const HOME_CARD_VISIBILITY_RULES = Object.freeze({
  ai: {
    code: HOME_CODES.aiGeneration,
    fallback: AI_WORKSPACE_ENTRY_PERMISSION_CODES,
  },
  manual: {
    code: HOME_CODES.manualTestcases,
    fallback: MANUAL_TESTCASE_WORKSPACE_ENTRY_PERMISSION_CODES,
  },
})

const AI_PROJECT_DETAIL_ROUTE_PERMISSION_CODES = Object.freeze([
  AI_GENERATION_CODES.projects,
  AI_GENERATION_CODES.foundation,
])

const AI_GENERATED_TASK_DETAIL_PERMISSION_CODES = Object.freeze([
  AI_GENERATION_CODES.generatedTestcases,
  AI_GENERATION_CODES.requirement,
])

const MANUAL_TESTCASE_EDITOR_PERMISSION_CODES = Object.freeze([
  MANUAL_TESTCASE_CODES.mindmaps,
  MANUAL_TESTCASE_CODES.testcases,
  MANUAL_TESTCASE_CODES.testpoints,
  MANUAL_TESTCASE_CODES.testing,
  MANUAL_TESTCASE_CODES.devSelfTest,
  MANUAL_TESTCASE_CODES.development,
])

const MANUAL_TESTCASE_DEFECT_ROUTE_PERMISSION_CODES = Object.freeze([
  MANUAL_TESTCASE_CODES.versionDefects,
  MANUAL_TESTCASE_CODES.bugRecords,
  MANUAL_TESTCASE_CODES.defect,
  MANUAL_TESTCASE_CODES.testcases,
  MANUAL_TESTCASE_CODES.testpoints,
  MANUAL_TESTCASE_CODES.devSelfTest,
  MANUAL_TESTCASE_CODES.versionRequirements,
  MANUAL_TESTCASE_CODES.requirementRecords,
  MANUAL_TESTCASE_CODES.product,
  MANUAL_TESTCASE_CODES.testing,
  MANUAL_TESTCASE_CODES.development,
])

const MANUAL_TESTCASE_TECHNICAL_SOLUTION_DESIGN_ROUTE_PERMISSION_CODES = Object.freeze([
  MANUAL_TESTCASE_CODES.technicalSolutionDesigns,
  MANUAL_TESTCASE_CODES.development,
  MANUAL_TESTCASE_CODES.devSelfTest,
  MANUAL_TESTCASE_CODES.versionRequirements,
  MANUAL_TESTCASE_CODES.requirementRecords,
  MANUAL_TESTCASE_CODES.product,
])

const EXACT_ROUTE_PERMISSION_CODES = Object.freeze({
  '/configuration/ai-model': AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.llm,
  '/configuration/ui-env': AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES['ui-env'],
  '/configuration/scheduled-task': AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.notifications,
  '/ai-generation/testcases/create': AI_GENERATION_CODES.testcaseCreate,
  '/manual-testcases/reports': MANUAL_TESTCASE_CODES.reports,
  '/manual-testcases/recording-scripts': [MANUAL_TESTCASE_CODES.recordingScripts, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/automation-scripts': [MANUAL_TESTCASE_CODES.automationScripts, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/snapshots': [MANUAL_TESTCASE_CODES.snapshots, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/recordings': [MANUAL_TESTCASE_CODES.recordings, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/controlled-browser-lab': [MANUAL_TESTCASE_CODES.controlledBrowserLab, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/flows': [MANUAL_TESTCASE_CODES.flows, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/visual-flow': [MANUAL_TESTCASE_CODES.visualFlow, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/visual-flow-executions': [MANUAL_TESTCASE_CODES.visualFlowExecutions, MANUAL_TESTCASE_CODES.recording],
  '/manual-testcases/workflow-workbench': [MANUAL_TESTCASE_CODES.workflowWorkbench, MANUAL_TESTCASE_CODES.config],
})

const hasScopedAiGenerationWorkspacePermission = hasPermissionCode => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  return hasPermissionAccess(AI_SCOPED_WORKSPACE_PERMISSION_CODES, hasPermissionCode)
}

const hasScopedManualTestcaseWorkspacePermission = hasPermissionCode => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  return hasPermissionAccess(MANUAL_TESTCASE_SCOPED_WORKSPACE_PERMISSION_CODES, hasPermissionCode)
}

const hasScopedHomeCardPermission = hasPermissionCode => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  return hasPermissionAccess(HOME_CARD_PERMISSION_CODES, hasPermissionCode)
}

const isAiGenerationWorkspaceScopedPath = path => (
  path === '/ai-generation/list' ||
  path === '/ai-generation/workshop' ||
  path === '/ai-generation/products' ||
  path === '/ai-generation/products/all' ||
  path.startsWith('/ai-generation/projects/') ||
  path.startsWith('/ai-generation/task-detail/')
)

export const isHomeCardVisible = (cardKey, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  const visibilityRule = HOME_CARD_VISIBILITY_RULES[cardKey]
  if (!visibilityRule) {
    return false
  }

  if (hasPermissionAccess(visibilityRule.code, hasPermissionCode)) {
    return true
  }

  if (!visibilityRule.fallback) {
    return !hasScopedHomeCardPermission(hasPermissionCode)
  }

  const fallbackCodes = Array.isArray(visibilityRule.fallback)
    ? visibilityRule.fallback
    : [visibilityRule.fallback]

  return hasPermissionAccess(fallbackCodes, hasPermissionCode)
}

export const getAIGenerationTabPermissionCandidates = tab => {
  const normalizedTab = normalizeAiGenerationTab(tab)
  return AI_GENERATION_TAB_PERMISSION_CANDIDATES[normalizedTab] || [AI_GENERATION_CODES.list]
}

export const getAIGenerationTabPermissionCode = tab => {
  const [permissionCode] = getAIGenerationTabPermissionCandidates(tab)
  return permissionCode || AI_GENERATION_CODES.list
}

export const isAIGenerationTabAccessible = (tab, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  const permissionCandidates = getAIGenerationTabPermissionCandidates(tab)
  if (hasPermissionAccess(permissionCandidates, hasPermissionCode)) {
    return true
  }

  return !hasScopedAiGenerationWorkspacePermission(hasPermissionCode) &&
    hasPermissionAccess(AI_GENERATION_CODES.list, hasPermissionCode)
}

export const getFirstAccessibleAIGenerationTab = hasPermissionCode => (
  AI_GENERATION_TAB_ORDER.find(tab => isAIGenerationTabAccessible(tab, hasPermissionCode)) || null
)

export const resolveAuthorizedAIGenerationTab = (tab, hasPermissionCode) => {
  const normalizedTab = normalizeAiGenerationTab(tab)

  if (normalizedTab && isAIGenerationTabAccessible(normalizedTab, hasPermissionCode)) {
    return normalizedTab
  }

  return getFirstAccessibleAIGenerationTab(hasPermissionCode)
}

export const getManualTestcaseTabPermissionCandidates = tab => {
  const normalizedTab = normalizeManualTestcaseTab(tab)
  return MANUAL_TESTCASE_TAB_PERMISSION_CANDIDATES[normalizedTab] || [MANUAL_TESTCASE_CODES.list]
}

export const getManualTestcaseTabPermissionCode = tab => {
  const [permissionCode] = getManualTestcaseTabPermissionCandidates(tab)
  return permissionCode || MANUAL_TESTCASE_CODES.list
}

export const isManualTestcaseTabAccessible = (tab, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  const permissionCandidates = getManualTestcaseTabPermissionCandidates(tab)
  if (hasPermissionAccess(permissionCandidates, hasPermissionCode)) {
    return true
  }

  return !hasScopedManualTestcaseWorkspacePermission(hasPermissionCode) &&
    hasPermissionAccess(MANUAL_TESTCASE_CODES.list, hasPermissionCode)
}

export const getFirstAccessibleManualTestcaseTab = hasPermissionCode => (
  MANUAL_TESTCASE_TAB_ORDER.find(tab => isManualTestcaseTabAccessible(tab, hasPermissionCode)) || null
)

export const resolveAuthorizedManualTestcaseTab = (tab, hasPermissionCode) => {
  const normalizedTab = normalizeManualTestcaseTab(tab)

  if (normalizedTab && isManualTestcaseTabAccessible(normalizedTab, hasPermissionCode)) {
    return normalizedTab
  }

  return getFirstAccessibleManualTestcaseTab(hasPermissionCode)
}

export const getManualTestcaseSectionPermissionCandidates = sectionName => {
  const normalizedSectionName = String(sectionName || '').trim()
  return MANUAL_TESTCASE_SECTION_PERMISSION_CANDIDATES[normalizedSectionName] || [MANUAL_TESTCASE_CODES.list]
}

export const isManualTestcaseSectionAccessible = (sectionName, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  const permissionCandidates = getManualTestcaseSectionPermissionCandidates(sectionName)
  if (hasPermissionAccess(permissionCandidates, hasPermissionCode)) {
    return true
  }

  return !hasScopedManualTestcaseWorkspacePermission(hasPermissionCode) &&
    hasPermissionAccess(MANUAL_TESTCASE_CODES.list, hasPermissionCode)
}

export const getRoutePermissionCode = routeLike => {
  const path = String(routeLike?.path || '').trim()
  if (!path || path === '/home') {
    return null
  }

  if (path === '/ai-generation/list') {
    return getAIGenerationTabPermissionCandidates(routeLike?.query?.tab)
  }

  if (path === '/ai-generation/workshop' || path.startsWith('/ai-generation/workshop/')) {
    return [
      AI_GENERATION_CODES.list,
      ...AI_WORKSPACE_ENTRY_PERMISSION_CODES,
    ]
  }

  if (LEGACY_AI_GENERATION_ROUTE_TAB_MAP[path]) {
    return getAIGenerationTabPermissionCandidates(LEGACY_AI_GENERATION_ROUTE_TAB_MAP[path])
  }

  if (path.startsWith('/ai-generation/projects/')) {
    return AI_PROJECT_DETAIL_ROUTE_PERMISSION_CODES
  }

  if (path.startsWith('/ai-generation/task-detail/')) {
    return AI_GENERATED_TASK_DETAIL_PERMISSION_CODES
  }

  if (path === '/manual-testcases/list') {
    return getManualTestcaseTabPermissionCandidates(routeLike?.query?.tab)
  }

  if (path === '/manual-testcases/editor' || path === '/manual-testcases/view') {
    return MANUAL_TESTCASE_EDITOR_PERMISSION_CODES
  }

  if (path.startsWith('/manual-testcases/defects')) {
    return MANUAL_TESTCASE_DEFECT_ROUTE_PERMISSION_CODES
  }

  if (path.startsWith('/manual-testcases/technical-solution-designs')) {
    return MANUAL_TESTCASE_TECHNICAL_SOLUTION_DESIGN_ROUTE_PERMISSION_CODES
  }

  return EXACT_ROUTE_PERMISSION_CODES[path] || null
}

export const hasRoutePermission = (routeLike, hasPermissionCode) => {
  if (typeof hasPermissionCode !== 'function') {
    return false
  }

  const path = String(routeLike?.path || '').trim()
  const requiredPermissionCode = getRoutePermissionCode(routeLike)

  if (!requiredPermissionCode) {
    return true
  }

  if (hasPermissionAccess(requiredPermissionCode, hasPermissionCode)) {
    return true
  }

  if (
    isAiGenerationWorkspaceScopedPath(path) &&
    !hasScopedAiGenerationWorkspacePermission(hasPermissionCode)
  ) {
    return hasPermissionAccess(AI_GENERATION_CODES.list, hasPermissionCode)
  }

  if (
    (
      path === '/manual-testcases/list' ||
      path === '/manual-testcases/editor' ||
      path === '/manual-testcases/view' ||
      path.startsWith('/manual-testcases/defects') ||
      path.startsWith('/manual-testcases/technical-solution-designs')
    ) &&
    !hasScopedManualTestcaseWorkspacePermission(hasPermissionCode)
  ) {
    return hasPermissionAccess(MANUAL_TESTCASE_CODES.list, hasPermissionCode)
  }

  return false
}
