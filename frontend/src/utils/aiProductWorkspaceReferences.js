const WORKSPACE_GROUP_DEFS = Object.freeze([
  {
    key: 'project',
    label: '项目',
    emptyText: '暂无项目工作区子对象',
    children: [
      { key: 'project', label: '项目澄清', workspaceTab: 'project' },
      { key: 'projectBaseline', label: '项目基线', workspaceTab: 'projectBaseline' },
    ],
  },
  {
    key: 'requirement',
    label: '需求',
    emptyText: '暂无需求工作区子对象',
    children: [
      { key: 'clarification', label: '需求澄清', workspaceTab: 'clarification' },
      { key: 'baselineRequirementAnalysis', label: '基线需求分析', workspaceTab: 'baselineRequirementAnalysis' },
      { key: 'businessLogic', label: '基线业务逻辑', workspaceTab: 'businessLogic' },
    ],
  },
  {
    key: 'prototype',
    label: '原型预览',
    emptyText: '暂无原型预览子对象',
    children: [
      { key: 'prototypeAi', label: 'AI原型', workspaceTab: 'prototype', subtype: 'ai' },
      { key: 'prototypeAxure', label: 'Axure原型', workspaceTab: 'prototype', subtype: 'axure' },
    ],
  },
  {
    key: 'prototypeRequirementAnalysis',
    label: '原型需求分析',
    emptyText: '暂无原型需求分析子对象',
    children: [
      { key: 'prototypeRequirementAnalysis', label: '原型需求分析', workspaceTab: 'prototypeRequirementAnalysis' },
      { key: 'prototypeBusinessLogic', label: '原型业务逻辑', workspaceTab: 'prototypeBusinessLogic' },
    ],
  },
  {
    key: 'testDesign',
    label: '测试设计',
    emptyText: '暂无测试设计子对象',
    children: [
      { key: 'testAnalysis', label: '测试分析', workspaceTab: 'testAnalysis' },
      { key: 'automationTestCases', label: '自动化测试用例', workspaceTab: 'automationTestCases' },
    ],
  },
  {
    key: 'designEngineering',
    label: '设计风格',
    emptyText: '暂无设计风格子对象',
    children: [
      { key: 'designEngineering', label: '页面设计风格', workspaceTab: 'designEngineering' },
    ],
  },
  {
    key: 'preview',
    label: '产品预览',
    emptyText: '暂无产品预览子对象',
    children: [
      { key: 'preview', label: '产品预览', workspaceTab: 'preview' },
    ],
  },
  {
    key: 'sessionWorkspace',
    label: '工作区',
    emptyText: '暂无工作区文件或治理对象',
    children: [
      { key: 'sessionWorkspace', label: '工作区文件', workspaceTab: 'sessionWorkspace' },
      { key: 'workspaceSnapshots', label: '工作区快照', workspaceTab: 'sessionWorkspace', subtype: 'snapshot' },
    ],
  },
  {
    key: 'code',
    label: '代码预览',
    emptyText: '暂无代码预览子对象',
    children: [
      { key: 'code', label: '代码预览', workspaceTab: 'code' },
    ],
  },
  {
    key: 'files',
    label: '上传文件',
    emptyText: '暂无上传文件',
    children: [
      { key: 'files', label: '上传文件', workspaceTab: 'files' },
    ],
  },
])

export const AI_PRODUCT_WORKSPACE_GROUP_DEFS = WORKSPACE_GROUP_DEFS

export const AI_PRODUCT_WORKSPACE_CONTEXT_KEYS = Object.freeze(
  WORKSPACE_GROUP_DEFS.map(item => item.key)
)

export const AI_PRODUCT_WORKSPACE_DEFAULT_CONTEXT_KEY = WORKSPACE_GROUP_DEFS[0].key

export const AI_PRODUCT_WORKSPACE_CHILD_DEFS = Object.freeze(
  WORKSPACE_GROUP_DEFS.flatMap(group =>
    group.children.map(child => ({
      ...child,
      groupKey: group.key,
      groupLabel: group.label,
    }))
  )
)

export const AI_PRODUCT_WORKSPACE_CHILD_BY_KEY = Object.freeze(
  AI_PRODUCT_WORKSPACE_CHILD_DEFS.reduce((mapping, item) => {
    mapping[item.key] = item
    return mapping
  }, {})
)

export const createEmptyProductWorkspaceReferenceState = () =>
  AI_PRODUCT_WORKSPACE_CONTEXT_KEYS.reduce((state, key) => {
    state[key] = []
    return state
  }, {})

export const getProductWorkspaceGroupDef = key =>
  WORKSPACE_GROUP_DEFS.find(item => item.key === key) || null

export const getProductWorkspaceChildDef = key =>
  AI_PRODUCT_WORKSPACE_CHILD_BY_KEY[key] || null
