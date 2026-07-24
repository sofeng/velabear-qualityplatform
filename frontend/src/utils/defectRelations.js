const normalizeText = (value) => String(value ?? '').trim()
const clampText = (value, maxLength) => {
  const text = normalizeText(value)
  if (!maxLength || text.length <= maxLength) {
    return text
  }

  return text.slice(0, maxLength)
}

export const DEFECT_RELATION_FIELD_LIMITS = {
  id: 255,
  mindmap_name: 255,
  node_text: 500,
  node_type: 50,
  path: 1000,
  parent_text: 500,
  case_id: 255,
  responsibility_group: 255,
  version_name: 255,
}

export const sanitizeDefectRelationItem = (item = {}, defaultNodeType = '') => {
  const normalizedItem = {
    id: clampText(item?.id || item?.node_id, DEFECT_RELATION_FIELD_LIMITS.id),
    mindmap_id: Number(item?.mindmap_id) || null,
    mindmap_name: clampText(item?.mindmap_name, DEFECT_RELATION_FIELD_LIMITS.mindmap_name),
    node_text: clampText(item?.node_text, DEFECT_RELATION_FIELD_LIMITS.node_text),
    node_type: clampText(item?.node_type || defaultNodeType, DEFECT_RELATION_FIELD_LIMITS.node_type),
    path: clampText(item?.path, DEFECT_RELATION_FIELD_LIMITS.path),
    parent_text: clampText(item?.parent_text, DEFECT_RELATION_FIELD_LIMITS.parent_text),
    case_id: clampText(item?.case_id, DEFECT_RELATION_FIELD_LIMITS.case_id),
    responsibility_group: clampText(item?.responsibility_group, DEFECT_RELATION_FIELD_LIMITS.responsibility_group),
  }

  if (
    !normalizedItem.mindmap_id &&
    !normalizedItem.mindmap_name &&
    !normalizedItem.node_text &&
    !normalizedItem.path
  ) {
    return null
  }

  return normalizedItem
}

export const buildDefectRelationKey = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  if (!normalizedItem) {
    return ''
  }

  return [
    normalizedItem.mindmap_id || '0',
    normalizedItem.node_type || 'node',
    normalizedItem.path || normalizedItem.node_text || normalizedItem.mindmap_name || normalizedItem.id,
  ].join('::')
}

export const getDefectRelationShortLabel = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  if (!normalizedItem) {
    return ''
  }

  const baseLabel = normalizedItem.node_text || normalizedItem.path || normalizedItem.mindmap_name
  if (normalizedItem.case_id) {
    return `${baseLabel} (${normalizedItem.case_id})`
  }

  return baseLabel
}

export const getDefectRelationOptionLabel = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  if (!normalizedItem) {
    return ''
  }

  const pathLabel = normalizedItem.path || normalizedItem.node_text || '未命名节点'
  if (normalizedItem.mindmap_name) {
    return `${pathLabel}（${normalizedItem.mindmap_name}）`
  }

  return pathLabel
}

export const decorateDefectRelationItem = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  if (!normalizedItem) {
    return null
  }

  return {
    ...normalizedItem,
    relation_key: buildDefectRelationKey(normalizedItem),
    short_label: getDefectRelationShortLabel(normalizedItem),
    option_label: getDefectRelationOptionLabel(normalizedItem),
  }
}

export const ensureUniqueDefectRelationItems = (items = [], defaultNodeType = '') => {
  const itemMap = new Map()

  ;(Array.isArray(items) ? items : []).forEach((item) => {
    const decoratedItem = decorateDefectRelationItem(item, defaultNodeType)
    if (!decoratedItem) {
      return
    }

    itemMap.set(decoratedItem.relation_key, decoratedItem)
  })

  return [...itemMap.values()]
}

export const serializeDefectRelationItems = (items = [], defaultNodeType = '') =>
  ensureUniqueDefectRelationItems(items, defaultNodeType).map((item) => ({
    id: item.id,
    mindmap_id: item.mindmap_id,
    mindmap_name: item.mindmap_name,
    node_text: item.node_text,
    node_type: item.node_type || defaultNodeType,
    path: item.path,
    parent_text: item.parent_text,
    case_id: item.case_id,
    responsibility_group: item.responsibility_group,
  }))

export const getDefectRelationTargetTab = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  const nodeType = normalizedItem?.node_type || defaultNodeType

  return (
    {
      module: 'mindmaps',
      case: 'testcases',
      testpoint: 'testpoints',
    }[nodeType] || 'mindmaps'
  )
}

export const buildDefectRelationRouteQuery = (item = {}, defaultNodeType = '') => {
  const normalizedItem = sanitizeDefectRelationItem(item, defaultNodeType)
  if (!normalizedItem?.mindmap_id) {
    return null
  }

  const normalizedPath = normalizedItem.path.replace(/\s*\/\s*/g, '/')

  return {
    id: String(normalizedItem.mindmap_id),
    node_text: normalizedItem.node_text || undefined,
    node_path: normalizedPath || undefined,
    from_tab: getDefectRelationTargetTab(normalizedItem, defaultNodeType),
  }
}
