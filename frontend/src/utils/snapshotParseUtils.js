import snapshotParser from '@/utils/snapshotParser'

const DEFAULT_PARSE_STATUS = 'idle'
const VALID_PARSE_STATUSES = new Set(['idle', 'success', 'error'])
const PRIVATE_USE_CHAR_RE = /[\uE000-\uF8FF]/g
const cleanSnapshotText = value => String(value || '').replace(PRIVATE_USE_CHAR_RE, '').replace(/\s+/g, ' ').trim()

const normalizeParseStatus = (value) => {
  const normalized = String(value || '').trim().toLowerCase()
  return VALID_PARSE_STATUSES.has(normalized) ? normalized : DEFAULT_PARSE_STATUS
}

const normalizeScalar = (value) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') {
    return cleanSnapshotText(value)
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return value
  }
  return cleanSnapshotText(value)
}

const normalizeAttributes = (attributes) => {
  if (!attributes || typeof attributes !== 'object' || Array.isArray(attributes)) {
    return {}
  }

  return Object.entries(attributes).reduce((accumulator, [key, value]) => {
    if (!key || value === null || value === undefined) {
      return accumulator
    }

    accumulator[String(key)] = normalizeScalar(value)
    return accumulator
  }, {})
}

const normalizeSelectors = (selectors) => {
  if (!Array.isArray(selectors)) return []

  return selectors.reduce((accumulator, selector) => {
    if (!selector || typeof selector !== 'object') {
      return accumulator
    }

    const value = cleanSnapshotText(selector.value || '')
    if (!value) {
      return accumulator
    }

    const normalizedSelector = {
      type: String(selector.type || 'selector').trim() || 'selector',
      value
    }

    if (Number.isFinite(Number(selector.priority))) {
      normalizedSelector.priority = Number(selector.priority)
    }

    accumulator.push(normalizedSelector)
    return accumulator
  }, [])
}

const normalizeInteractiveElement = (element, index = 0) => ({
  id: String(element?.id || `element_${index}`),
  type: String(element?.type || 'generic'),
  text: cleanSnapshotText(element?.text || ''),
  ref: String(element?.ref || ''),
  attributes: normalizeAttributes(element?.attributes),
  selectors: normalizeSelectors(element?.selectors)
})

const normalizeSampleElement = (element) => ({
  type: String(element?.type || '-'),
  text: cleanSnapshotText(element?.text || '-') || '-',
  selector: cleanSnapshotText(element?.selector || '-') || '-'
})

const buildSampleElements = (interactiveElements) => {
  return interactiveElements.slice(0, 20).map(item => ({
    type: item.type || '-',
    text: item.text || item.attributes?.placeholder || item.attributes?.name || item.id || '-',
    selector: item.selectors?.find(selector => selector.type !== 'data-ref')?.value || item.type || '-'
  }))
}

export const analyzeSnapshotContent = (content = '') => {
  const normalizedContent = typeof content === 'string' ? content : ''
  const lineCount = normalizedContent ? normalizedContent.split(/\r?\n/).length : 0

  if (!normalizedContent.trim()) {
    return {
      valid: true,
      lineCount,
      interactiveCount: 0,
      sampleElements: [],
      interactiveElements: [],
      error: ''
    }
  }

  try {
    const elementTree = snapshotParser.parse(normalizedContent)
    const interactiveElements = snapshotParser
      .extractInteractiveElements(elementTree)
      .map((element, index) => normalizeInteractiveElement(element, index))

    return {
      valid: true,
      lineCount,
      interactiveCount: interactiveElements.length,
      sampleElements: buildSampleElements(interactiveElements),
      interactiveElements,
      error: ''
    }
  } catch (error) {
    return {
      valid: false,
      lineCount,
      interactiveCount: 0,
      sampleElements: [],
      interactiveElements: [],
      error: error.message || '快照解析失败'
    }
  }
}

export const buildSnapshotParsePayload = (analysis = {}) => ({
  parse_status: analysis.valid ? 'success' : 'error',
  line_count: Number(analysis.lineCount || 0),
  interactive_count: Number(analysis.interactiveCount || 0),
  parse_error: analysis.error || '',
  sample_elements: Array.isArray(analysis.sampleElements)
    ? analysis.sampleElements.map(normalizeSampleElement)
    : [],
  interactive_elements: Array.isArray(analysis.interactiveElements)
    ? analysis.interactiveElements.map((element, index) => normalizeInteractiveElement(element, index))
    : []
})

export const buildParseStateFromSnapshot = (snapshot = {}) => {
  const parsedSnapshot = snapshot?.parsed_snapshot || snapshot || {}
  const status = normalizeParseStatus(parsedSnapshot.parse_status || snapshot.parse_status)

  return {
    status,
    valid: status === 'success' ? true : status === 'error' ? false : null,
    lineCount: Number(parsedSnapshot.line_count ?? snapshot.line_count ?? 0),
    interactiveCount: Number(parsedSnapshot.interactive_count ?? snapshot.interactive_count ?? 0),
    error: parsedSnapshot.error || parsedSnapshot.parse_error || snapshot.parse_error || '',
    parsedAt: parsedSnapshot.parsed_at ?? snapshot.parsed_at ?? null
  }
}

export const buildSnapshotRuntimeData = (snapshot = {}) => {
  const parsedSnapshot = snapshot?.parsed_snapshot || snapshot || {}
  const interactiveElements = Array.isArray(parsedSnapshot.interactive_elements)
    ? parsedSnapshot.interactive_elements.map((element, index) => normalizeInteractiveElement(element, index))
    : []

  return {
    filename: snapshot.filename || '',
    pageName: snapshot.page_name || '',
    content: snapshot.content || '',
    interactiveElements,
    metadata: {
      size: snapshot.size,
      createdAt: snapshot.created_at,
      modifiedAt: snapshot.modified_at
    },
    parseStatus: normalizeParseStatus(parsedSnapshot.parse_status || snapshot.parse_status),
    parsedAt: parsedSnapshot.parsed_at ?? snapshot.parsed_at ?? null
  }
}

export const hasPersistedParsedSnapshot = (snapshot = {}) => {
  const parsedSnapshot = snapshot?.parsed_snapshot || snapshot || {}
  const status = normalizeParseStatus(parsedSnapshot.parse_status || snapshot.parse_status)
  return status === 'success' && Array.isArray(parsedSnapshot.interactive_elements)
}
