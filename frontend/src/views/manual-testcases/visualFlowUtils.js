export const PAGE_NODE_LAYOUT = {
  headerHeight: 58,
  footerHeight: 34,
  paddingX: 20,
  paddingY: 16
}

export const IFRAME_LAYOUT = {
  headerHeight: 30,
  paddingX: 12,
  paddingY: 12
}

export const COMPONENT_META = {
  input: {
    label: '输入框',
    icon: 'I',
    tagType: 'primary',
    size: { width: 148, height: 82 },
    compatibleTypes: ['textbox', 'input', 'searchbox']
  },
  button: {
    label: '按钮',
    icon: 'B',
    tagType: 'success',
    size: { width: 140, height: 76 },
    compatibleTypes: ['button']
  },
  select: {
    label: '下拉框',
    icon: 'S',
    tagType: 'warning',
    size: { width: 152, height: 82 },
    compatibleTypes: ['select', 'combobox', 'listbox']
  },
  checkbox: {
    label: '复选框',
    icon: 'C',
    tagType: '',
    size: { width: 152, height: 72 },
    compatibleTypes: ['checkbox']
  },
  radio: {
    label: '单选框',
    icon: 'R',
    tagType: '',
    size: { width: 152, height: 72 },
    compatibleTypes: ['radio']
  },
  link: {
    label: '链接',
    icon: 'L',
    tagType: 'info',
    size: { width: 144, height: 68 },
    compatibleTypes: ['link', 'a']
  },
  tab: {
    label: '标签页',
    icon: 'T',
    tagType: 'info',
    size: { width: 142, height: 66 },
    compatibleTypes: ['tab']
  },
  menuitem: {
    label: '菜单项',
    icon: 'M',
    tagType: 'info',
    size: { width: 150, height: 68 },
    compatibleTypes: ['menuitem']
  },
  clickable: {
    label: '可点击元素',
    icon: 'K',
    tagType: 'info',
    size: { width: 150, height: 68 },
    compatibleTypes: ['clickable', 'generic']
  },
  file: {
    label: '文件上传',
    icon: 'U',
    tagType: 'warning',
    size: { width: 160, height: 76 },
    compatibleTypes: ['file', 'input']
  },
  iframe: {
    label: 'Iframe',
    icon: 'F',
    tagType: 'warning',
    size: { width: 232, height: 176 },
    compatibleTypes: ['iframe', 'frame']
  }
}

export const COMPONENT_LIBRARY = Object.entries(COMPONENT_META).map(([type, meta]) => ({
  type,
  ...meta
}))

export const FLOW_PORT_GROUPS = {
  in: 'dynamic-in',
  out: 'dynamic-out'
}

export const FLOW_VARIABLE_SOURCES = [
  { label: '无', value: 'none' },
  { label: '当前值', value: 'value' },
  { label: '文本', value: 'text' },
  { label: '选择器', value: 'selector' },
  { label: '选中状态', value: 'checked' },
  { label: '页面地址', value: 'url' },
  { label: '自定义', value: 'custom' }
]

export const FLOW_INPUT_MODES = [
  { label: '固定值', value: 'literal' },
  { label: '引用上一步输出', value: 'reference' }
]

export const FLOW_ASSERTION_TARGETS = [
  { label: '页面文本', value: 'pageText' },
  { label: '元素文本', value: 'selectorText' },
  { label: '元素值', value: 'selectorValue' },
  { label: '选中状态', value: 'selectorChecked' },
  { label: '页面地址', value: 'url' },
  { label: '变量值', value: 'variable' },
  { label: '自定义表达式', value: 'custom' }
]

export const FLOW_ASSERTION_OPERATORS = [
  { label: '等于', value: 'equals' },
  { label: '不等于', value: 'notEquals' },
  { label: '包含', value: 'contains' },
  { label: '不包含', value: 'notContains' },
  { label: '开头是', value: 'startsWith' },
  { label: '结尾是', value: 'endsWith' },
  { label: '正则匹配', value: 'regex' }
]

export const clampPercent = (value, min, max) => Math.min(Math.max(Number(value) || 0, min), max)

export const getComponentMeta = (type) => COMPONENT_META[type] || {
  label: type,
  icon: 'U',
  tagType: 'info',
  size: { width: 120, height: 52 },
  compatibleTypes: []
}

export const getComponentTypeName = (type) => getComponentMeta(type).label
export const getComponentIcon = (type) => getComponentMeta(type).icon
export const getComponentTagType = (type) => getComponentMeta(type).tagType
const normalizeComponentSizeValue = (value, fallback) => {
  const normalized = Number(value)
  if (!Number.isFinite(normalized) || normalized <= 0) {
    return fallback
  }
  return Math.max(normalized, fallback)
}

const getComponentSizingText = (component) => {
  if (!component || typeof component !== 'object') {
    return ''
  }

  const config = component.config || {}
  const elementData = component.elementData || {}
  const candidates = [
    config.text,
    config.label,
    config.value,
    config.inputValue,
    config.selectedValue,
    config.filePath,
    elementData.text,
    elementData.ref,
    elementData.attributes?.placeholder,
    elementData.attributes?.title,
    elementData.attributes?.['aria-label'],
    component.elementId
  ]

  return candidates
    .map(value => String(value ?? '').trim())
    .filter(Boolean)
    .sort((left, right) => right.length - left.length)[0] || ''
}

const normalizeTextValue = value => String(value ?? '').replace(/\s+/g, ' ').trim()

const getPrimaryComponentPreviewText = (component) => {
  if (!component || typeof component !== 'object') {
    return ''
  }

  const config = component.config || {}
  const elementData = component.elementData || {}

  if (component.type === 'input') {
    if (config.inputMode === 'reference') {
      return config.inputReference ? `{{${config.inputReference}}}` : ''
    }
    return normalizeTextValue(config.value || config.inputValue)
  }

  if (component.type === 'select') {
    if (config.inputMode === 'reference') {
      return config.inputReference ? `{{${config.inputReference}}}` : ''
    }
    return normalizeTextValue(config.selectedValue || elementData.text)
  }

  if (component.type === 'file') {
    return normalizeTextValue(config.filePath || config.inputValue || elementData.text)
  }

  return normalizeTextValue(elementData.text || elementData.ref || config.text || config.label || component.elementId)
}

const getTextMeasureUnits = (text) => {
  return Array.from(String(text || '')).reduce((total, char) => {
    if (/\s/.test(char)) return total + 0.35
    if (/[\u3400-\u9FFF\uF900-\uFAFF]/u.test(char)) return total + 1.1
    if (/[A-Z]/.test(char)) return total + 0.8
    return total + 0.65
  }, 0)
}

const estimateComponentTextHeight = (component, baseSize) => {
  if (!component || typeof component !== 'object' || component.type === 'iframe') {
    return baseSize.height
  }

  const text = getPrimaryComponentPreviewText(component) || getComponentSizingText(component)
  if (!text) {
    return baseSize.height
  }

  const usableWidth = Math.max((baseSize.width || 140) - 24, 64)
  const unitsPerLine = Math.max(8, Math.floor(usableWidth / 7))
  const lineCount = Math.max(1, Math.ceil(getTextMeasureUnits(text) / unitsPerLine))
  const previewExtra = Math.max(0, lineCount - 1) * 15
  const captionExtra = Math.max(0, Math.min(lineCount, 4) - 1) * 12

  return Math.ceil(baseSize.height + previewExtra + captionExtra)
}

export const getComponentSize = (componentOrType) => {
  const component = typeof componentOrType === 'object' && componentOrType !== null ? componentOrType : null
  const type = component ? component.type : componentOrType
  const baseSize = getComponentMeta(type).size
  const customSize = component?.size || {}
  const autoHeight = estimateComponentTextHeight(component, baseSize)

  return {
    width: normalizeComponentSizeValue(customSize.width, baseSize.width),
    height: normalizeComponentSizeValue(customSize.height, Math.max(baseSize.height, autoHeight))
  }
}

export const getDefaultComponentAction = (type) => {
  const actionMap = {
    input: 'fill',
    button: 'click',
    select: 'select',
    checkbox: 'check',
    radio: 'check',
    link: 'click',
    tab: 'click',
    menuitem: 'click',
    clickable: 'click',
    file: 'setInputFiles',
    iframe: 'scope'
  }
  return actionMap[type] || 'click'
}

export const buildComponentDefaultConfig = (type) => {
  const commonConfig = {
    action: getDefaultComponentAction(type),
    inputMode: 'literal',
    inputValue: '',
    inputReference: '',
    outputName: '',
    outputSource: 'none',
    outputValue: ''
  }

  switch (type) {
    case 'input':
      return {
        ...commonConfig,
        value: ''
      }
    case 'button':
    case 'link':
      return {
        ...commonConfig
      }
    case 'select':
      return {
        ...commonConfig,
        selectedValue: ''
      }
    case 'checkbox':
    case 'radio':
      return {
        ...commonConfig,
        checked: true
      }
    case 'file':
      return {
        ...commonConfig,
        filePath: ''
      }
    case 'iframe':
      return {
        ...commonConfig,
        action: 'scope'
      }
    default:
      return commonConfig
  }
}

export const ensureFlowConfig = (config = {}) => {
  if (!Array.isArray(config.innerComponents)) {
    config.innerComponents = []
  }
  if (!Array.isArray(config.executionPath)) {
    config.executionPath = []
  }
  return config
}

const buildRect = (left, top, width, height) => ({
  left,
  top,
  width,
  height,
  right: left + width,
  bottom: top + height,
  centerX: left + width / 2,
  centerY: top + height / 2
})

export const getPageInnerRect = (nodeSize) => {
  const width = Math.max((nodeSize?.width || 320) - PAGE_NODE_LAYOUT.paddingX * 2, 40)
  const height = Math.max(
    (nodeSize?.height || 450) - PAGE_NODE_LAYOUT.headerHeight - PAGE_NODE_LAYOUT.footerHeight - PAGE_NODE_LAYOUT.paddingY * 2,
    40
  )
  return buildRect(
    PAGE_NODE_LAYOUT.paddingX,
    PAGE_NODE_LAYOUT.headerHeight + PAGE_NODE_LAYOUT.paddingY,
    width,
    height
  )
}

export const getIframeInnerRect = (outerRect) => buildRect(
  outerRect.left + IFRAME_LAYOUT.paddingX,
  outerRect.top + IFRAME_LAYOUT.headerHeight + IFRAME_LAYOUT.paddingY,
  Math.max(outerRect.width - IFRAME_LAYOUT.paddingX * 2, 40),
  Math.max(outerRect.height - IFRAME_LAYOUT.headerHeight - IFRAME_LAYOUT.paddingY * 2, 40)
)

export const isPointInRect = (x, y, rect) => {
  return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
}

export const normalizeInnerComponents = (pageConfig, getSnapshotElementById) => {
  ensureFlowConfig(pageConfig)
  const componentIds = new Set((pageConfig.innerComponents || []).map(component => component.id))
  pageConfig.innerComponents = pageConfig.innerComponents.map((component, index) => {
    const elementData = getSnapshotElementById?.(pageConfig, component.elementId) || component.elementData || null
    const parentId = component.parentId && componentIds.has(component.parentId) ? component.parentId : null
    const componentSize = getComponentSize(component)
    return {
      ...component,
      parentId,
      size: component.size ? componentSize : undefined,
      position: {
        x: clampPercent(component.position?.x, 6, 94),
        y: clampPercent(component.position?.y, 8, 92)
      },
      zIndex: index,
      order: index,
      elementData,
      config: {
        ...buildComponentDefaultConfig(component.type),
        ...(component.config || {})
      }
    }
  })
}

export const buildComponentLayouts = (components, nodeSize) => {
  const orderedComponents = [...(components || [])].sort((a, b) => (a.order ?? a.zIndex ?? 0) - (b.order ?? b.zIndex ?? 0))
  const childrenByParent = new Map()
  orderedComponents.forEach(component => {
    const parentId = component.parentId || '__root__'
    if (!childrenByParent.has(parentId)) {
      childrenByParent.set(parentId, [])
    }
    childrenByParent.get(parentId).push(component)
  })

  const layouts = []

  const visit = (parentId, parentRect, depth = 0) => {
    const children = childrenByParent.get(parentId) || []
    children.forEach(component => {
      const size = getComponentSize(component)
      const x = parentRect.left + parentRect.width * clampPercent(component.position?.x, 6, 94) / 100
      const y = parentRect.top + parentRect.height * clampPercent(component.position?.y, 8, 92) / 100
      const rect = buildRect(x - size.width / 2, y - size.height / 2, size.width, size.height)
      const innerRect = component.type === 'iframe' ? getIframeInnerRect(rect) : null
      const layout = {
        component,
        rect,
        innerRect,
        depth,
        parentRect,
        parentId: component.parentId || null
      }
      layouts.push(layout)
      if (component.type === 'iframe') {
        visit(component.id, innerRect, depth + 1)
      }
    })
  }

  visit('__root__', getPageInnerRect(nodeSize))
  return layouts
}

export const findIframeDropTarget = (components, nodeSize, x, y) => {
  const iframeLayouts = buildComponentLayouts(components, nodeSize)
    .filter(layout => layout.component.type === 'iframe' && layout.innerRect)
    .filter(layout => isPointInRect(x, y, layout.innerRect))
    .sort((a, b) => b.depth - a.depth)

  return iframeLayouts[0] || null
}

export const createDirectionalPorts = ({ idPrefix, rect, wall = 'component', data = {} }) => ([
  {
    id: `${idPrefix}-top-in`,
    group: FLOW_PORT_GROUPS.in,
    args: { x: rect.centerX, y: rect.top },
    data: { ...data, wall, side: 'top', direction: 'in' }
  },
  {
    id: `${idPrefix}-left-in`,
    group: FLOW_PORT_GROUPS.in,
    args: { x: rect.left, y: rect.centerY },
    data: { ...data, wall, side: 'left', direction: 'in' }
  },
  {
    id: `${idPrefix}-bottom-out`,
    group: FLOW_PORT_GROUPS.out,
    args: { x: rect.centerX, y: rect.bottom },
    data: { ...data, wall, side: 'bottom', direction: 'out' }
  },
  {
    id: `${idPrefix}-right-out`,
    group: FLOW_PORT_GROUPS.out,
    args: { x: rect.right, y: rect.centerY },
    data: { ...data, wall, side: 'right', direction: 'out' }
  }
])

const DIRECTIONAL_PORT_SUFFIX_RE = /-(top|left|bottom|right)-(in|out)$/

export const getDirectionalPortSuffix = (portId = '') => {
  const match = String(portId || '').match(DIRECTIONAL_PORT_SUFFIX_RE)
  return match ? `${match[1]}-${match[2]}` : ''
}

export const buildIframeSharedPortId = (componentId, suffixOrSide = 'right-out', direction = '') => {
  const suffix = direction ? `${suffixOrSide}-${direction}` : suffixOrSide
  return `iframe-${componentId}-${suffix}`
}

export const normalizeIframePortId = (portId = '', components = []) => {
  const normalizedPortId = String(portId || '')
  if (!normalizedPortId) {
    return ''
  }

  const suffix = getDirectionalPortSuffix(normalizedPortId)
  if (!suffix) {
    return normalizedPortId
  }

  const iframeIds = [...(components || [])]
    .filter(component => component?.type === 'iframe' && component?.id)
    .map(component => String(component.id))
    .sort((left, right) => right.length - left.length)

  for (const iframeId of iframeIds) {
    if (
      normalizedPortId === `iframe-${iframeId}-${suffix}` ||
      normalizedPortId === `iframe-${iframeId}-outer-${suffix}` ||
      normalizedPortId === `iframe-${iframeId}-inner-${suffix}` ||
      normalizedPortId === `component-${iframeId}-${suffix}`
    ) {
      return buildIframeSharedPortId(iframeId, suffix)
    }
  }

  const legacyIframeMatch = normalizedPortId.match(/^iframe-(.+?)-(?:outer|inner)-(top|left|bottom|right)-(in|out)$/)
  if (legacyIframeMatch) {
    return buildIframeSharedPortId(legacyIframeMatch[1], `${legacyIframeMatch[2]}-${legacyIframeMatch[3]}`)
  }

  return normalizedPortId
}

export const normalizeExecutionEndpointPortIds = (endpoint = {}, components = []) => ({
  ...endpoint,
  portId: normalizeIframePortId(endpoint?.portId || endpoint?.port || '', components)
})

export const normalizeExecutionConnectionPorts = (sourcePort, targetPort) => {
  const sourceDirection = sourcePort?.data?.direction
  const targetDirection = targetPort?.data?.direction
  const sourceIsPage = sourcePort?.data?.scopeType === 'page'
  const targetIsPage = targetPort?.data?.scopeType === 'page'
  const shouldSwap =
    (sourceDirection === 'in' && targetDirection === 'out') ||
    (sourceDirection === 'in' && targetDirection === 'in' && !sourceIsPage && targetIsPage) ||
    (sourceDirection === 'out' && targetDirection === 'out' && sourceIsPage && !targetIsPage)

  return shouldSwap
    ? { sourcePort: targetPort, targetPort: sourcePort, reversed: true }
    : { sourcePort, targetPort, reversed: false }
}

export const buildPageNodePorts = (nodeSize, innerComponents) => {
  const pageOuterRect = buildRect(0, 0, nodeSize?.width || 320, nodeSize?.height || 450)
  const pageInnerRect = getPageInnerRect(nodeSize)
  const layouts = buildComponentLayouts(innerComponents, nodeSize)
  const ports = createDirectionalPorts({
    idPrefix: 'page',
    rect: pageOuterRect,
    wall: 'shared',
    data: { scopeType: 'page', scopeId: 'page' }
  })

  layouts.forEach(layout => {
    const baseData = {
      scopeType: layout.component.type === 'iframe' ? 'iframe' : 'component',
      scopeId: layout.component.id,
      componentId: layout.component.id,
      componentType: layout.component.type,
      elementId: layout.component.elementId,
      elementType: layout.component.elementData?.type || layout.component.type,
      elementText: layout.component.elementData?.text || layout.component.elementData?.ref || layout.component.elementId || layout.component.type,
      parentId: layout.component.parentId || null
    }

    if (layout.component.type === 'iframe' && layout.innerRect) {
      ports.push(...createDirectionalPorts({
        idPrefix: `iframe-${layout.component.id}`,
        rect: layout.rect,
        wall: 'shared',
        data: baseData
      }))
      return
    }

    ports.push(...createDirectionalPorts({
      idPrefix: `component-${layout.component.id}`,
      rect: layout.rect,
      wall: 'component',
      data: baseData
    }))
  })

  return { ports, layouts, pageInnerRect, pageOuterRect }
}

export const isElementCompatible = (element, componentType) => {
  const compatibleTypes = getComponentMeta(componentType).compatibleTypes || []
  return compatibleTypes.includes(element?.type)
}

export const isElementInsideElement = (element, ancestorElementId) => {
  let current = element?.parent || null
  while (current) {
    if (current.id === ancestorElementId) {
      return true
    }
    current = current.parent || null
  }
  return false
}

export const getComponentDisplayText = (component) => {
  return component?.elementData?.text || component?.elementData?.ref || component?.elementId || '未映射元素'
}

const normalizeSelectorValue = (value) => {
  const normalized = String(value ?? '').trim()
  if (
    (normalized.startsWith('"') && normalized.endsWith('"')) ||
    (normalized.startsWith("'") && normalized.endsWith("'"))
  ) {
    return normalized.slice(1, -1).trim()
  }
  return normalized
}

const escapeSelectorPreviewText = (value) => String(value ?? '')
  .replace(/\\/g, '\\\\')
  .replace(/"/g, '\\"')

const isMeaningfulSelectorText = (value, maxLength = 80) => {
  const normalized = normalizeSelectorValue(value)
  if (!normalized || normalized.length > maxLength) {
    return false
  }

  const compact = normalized.replace(/\s+/g, '')
  if (!compact) {
    return false
  }

  return !/^[\uE000-\uF8FF]+$/u.test(compact)
}

export const getComponentSelectorPreview = (component) => {
  const elementData = component?.elementData || {}

  if (component?.type === 'input') {
    const placeholder = [
      component?.config?.placeholder,
      elementData?.attributes?.placeholder,
      elementData?.text
    ]
      .map(value => normalizeSelectorValue(value))
      .find(value => value && value !== '输入内容...' && value !== '输入内容')

    if (placeholder) {
      return `get_by_placeholder("${escapeSelectorPreviewText(placeholder)}")`
    }
  }

  const roleMap = {
    input: 'textbox',
    button: 'button',
    link: 'link',
    select: 'combobox',
    checkbox: 'checkbox',
    radio: 'radio',
    tab: 'tab',
    menuitem: 'menuitem'
  }
  const role = roleMap[component?.type] || ''
  const roleNameCandidates = [
    elementData?.attributes?.['aria-label'],
    elementData?.attributes?.label,
    elementData?.attributes?.title,
    elementData?.attributes?.name
  ]

  if (['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem', 'clickable'].includes(component?.type)) {
    roleNameCandidates.push(elementData?.text)
  }

  const roleName = roleNameCandidates
    .map(value => normalizeSelectorValue(value))
    .find(value => isMeaningfulSelectorText(value))

  if (role && roleName) {
    return `get_by_role("${escapeSelectorPreviewText(role)}", name="${escapeSelectorPreviewText(roleName)}")`
  }

  if (['button', 'link', 'tab', 'menuitem', 'clickable'].includes(component?.type)) {
    const text = normalizeSelectorValue(elementData?.text)
    if (isMeaningfulSelectorText(text)) {
      return `get_by_text("${escapeSelectorPreviewText(text)}")`
    }
  }

  const selector = (elementData?.selectors || []).find(item => {
    const value = item?.value || ''
    return item?.type !== 'data-ref' && !value.includes('[data-ref=')
  })?.value

  if (selector) {
    return `locator("${escapeSelectorPreviewText(selector)}")`
  }

  return ''
}

export const getComponentActionText = (component) => {
  const action = component?.config?.action || getDefaultComponentAction(component?.type)
  if (component?.type === 'input') {
    const sourceText = component.config?.inputMode === 'reference'
      ? `引用:${component.config?.inputReference || '未配置'}`
      : component.config?.value || component.config?.inputValue || '未配置'
    return action === 'press' ? `按键 ${sourceText}` : `输入 ${sourceText}`
  }

  if (component?.type === 'select') {
    const sourceText = component.config?.inputMode === 'reference'
      ? `引用:${component.config?.inputReference || '未配置'}`
      : component.config?.selectedValue || '未配置'
    return `选择 ${sourceText}`
  }

  if (component?.type === 'checkbox' || component?.type === 'radio') {
    return component.config?.checked ? '勾选' : '取消勾选'
  }

  if (component?.type === 'file') {
    return `上传 ${component.config?.filePath || component.config?.inputValue || '未配置'}`
  }

  if (component?.type === 'iframe') {
    return '容器作用域'
  }

  const labelMap = {
    click: '单击',
    dblclick: '双击',
    contextmenu: '右键',
    hover: '悬停'
  }
  return labelMap[action] || action
}
