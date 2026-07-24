import JSZip from 'jszip'

export const DEFAULT_MINDMAP_THEME = Object.freeze({
  template: 'default',
  theme: 'fresh-blue',
  version: '1.4.43'
})

const getNodeText = value => {
  const text = String(value || '').trim()
  return text || '未命名节点'
}

const normalizePriority = markerId => {
  const match = String(markerId || '').match(/\d+/)
  const priority = Number(match?.[0] || 0)
  if (priority >= 1 && priority <= 4) {
    return priority - 1
  }
  return null
}

const normalizeNode = node => {
  const data = node?.data && typeof node.data === 'object' ? { ...node.data } : {}
  data.text = getNodeText(data.text)
  data.nodeType = data.nodeType || 'module'

  const children = Array.isArray(node?.children)
    ? node.children.map(child => normalizeNode(child))
    : []

  return {
    ...(node && typeof node === 'object' ? node : {}),
    data,
    children
  }
}

const buildMindmapData = root => ({
  root: normalizeNode(root),
  ...DEFAULT_MINDMAP_THEME
})

const createXMindIdFactory = () => {
  let counter = 0
  const randomPart = () => {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
      return globalThis.crypto.randomUUID()
    }
    counter += 1
    return `${Date.now().toString(36)}-${counter.toString(36)}`
  }

  return prefix => `${prefix}-${randomPart()}`
}

const normalizeLabelList = value => (
  Array.isArray(value)
    ? value.map(item => String(item || '').trim()).filter(Boolean)
    : []
)

const normalizeNoteText = value => String(value || '').trim()

const normalizeExportPriority = value => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const priority = Number(value)
  return Number.isFinite(priority) && priority >= 0 && priority <= 3 ? priority : null
}

const convertMindmapNodeToXMindTopic = (node, createId, depth = 0) => {
  const normalizedNode = normalizeNode(node)
  const data = normalizedNode.data || {}
  const topic = {
    id: createId('topic'),
    class: 'topic',
    title: getNodeText(data.text)
  }

  if (depth === 0) {
    topic.structureClass = 'org.xmind.ui.map.unbalanced'
  }

  const labels = normalizeLabelList(data.tags)
  if (labels.length) {
    topic.labels = labels
  }

  const note = normalizeNoteText(data.note)
  if (note) {
    topic.notes = {
      plain: {
        content: note
      }
    }
  }

  const priority = normalizeExportPriority(data.priority)
  if (priority !== null) {
    topic.markers = [
      {
        markerId: `priority-${priority + 1}`
      }
    ]
  }

  const attachedChildren = normalizedNode.children
    .map(child => convertMindmapNodeToXMindTopic(child, createId, depth + 1))
  if (attachedChildren.length) {
    topic.children = {
      attached: attachedChildren
    }
  }

  return topic
}

const countAttachedTopics = topic => (
  1 + (Array.isArray(topic?.children?.attached) ? topic.children.attached : [])
    .reduce((total, child) => total + countAttachedTopics(child), 0)
)

const getJsonRootTopic = xmindData => {
  if (Array.isArray(xmindData)) {
    return xmindData.find(item => item?.rootTopic)?.rootTopic || null
  }

  if (xmindData?.rootTopic) {
    return xmindData.rootTopic
  }

  if (Array.isArray(xmindData?.sheets)) {
    return xmindData.sheets.find(item => item?.rootTopic)?.rootTopic || null
  }

  return null
}

const convertXMindJsonTopic = topic => {
  const node = {
    data: {
      text: getNodeText(topic?.title)
    }
  }

  if (Array.isArray(topic?.labels) && topic.labels.length) {
    node.data.tags = topic.labels.map(label => String(label).trim()).filter(Boolean)
  }

  const noteContent = topic?.notes?.plain?.content || topic?.notes?.plain?.[0]?.content
  if (noteContent) {
    node.data.note = String(noteContent)
  }

  if (Array.isArray(topic?.markers)) {
    const priorityMarker = topic.markers.find(marker => String(marker?.markerId || '').includes('priority'))
    const priority = normalizePriority(priorityMarker?.markerId)
    if (priority !== null) {
      node.data.priority = priority
    }
  }

  const attachedChildren = Array.isArray(topic?.children?.attached) ? topic.children.attached : []
  if (attachedChildren.length) {
    node.children = attachedChildren.map(child => convertXMindJsonTopic(child))
  }

  return node
}

const getLocalName = element => {
  if (!element) {
    return ''
  }

  return String(element.localName || element.tagName || '')
    .split(':')
    .pop()
    .toLowerCase()
}

const findDirectChild = (element, localName) => (
  Array.from(element?.children || []).find(child => getLocalName(child) === localName) || null
)

const findDirectChildren = (element, localName) => (
  Array.from(element?.children || []).filter(child => getLocalName(child) === localName)
)

const getDirectText = (element, localName) => {
  const child = findDirectChild(element, localName)
  return child?.textContent || ''
}

const getAttachedXmlTopics = topicElement => {
  const childrenElement = findDirectChild(topicElement, 'children')
  if (!childrenElement) {
    return []
  }

  const topicsElement = findDirectChildren(childrenElement, 'topics')
    .find(item => String(item.getAttribute('type') || '').toLowerCase() === 'attached')

  return findDirectChildren(topicsElement, 'topic')
}

const convertXMindXmlTopic = topicElement => {
  const node = {
    data: {
      text: getNodeText(getDirectText(topicElement, 'title'))
    }
  }

  const notesElement = findDirectChild(topicElement, 'notes')
  const plainNote = getDirectText(notesElement, 'plain').trim()
  if (plainNote) {
    node.data.note = plainNote
  }

  const labelsElement = findDirectChild(topicElement, 'labels')
  const labels = findDirectChildren(labelsElement, 'label')
    .map(label => String(label.textContent || '').trim())
    .filter(Boolean)
  if (labels.length) {
    node.data.tags = labels
  }

  const children = getAttachedXmlTopics(topicElement).map(child => convertXMindXmlTopic(child))
  if (children.length) {
    node.children = children
  }

  return node
}

const parseXMindJsonContent = jsonContent => {
  const xmindData = JSON.parse(jsonContent)
  const rootTopic = getJsonRootTopic(xmindData)
  if (!rootTopic) {
    throw new Error('未找到 XMind 根节点')
  }
  return buildMindmapData(convertXMindJsonTopic(rootTopic))
}

const parseXMindXmlContent = xmlContent => {
  const parser = new DOMParser()
  const xmlDoc = parser.parseFromString(xmlContent, 'text/xml')
  if (xmlDoc.querySelector('parsererror')) {
    throw new Error('XMind XML 解析失败')
  }

  const rootElement = xmlDoc.documentElement
  const sheetElement = findDirectChild(rootElement, 'sheet') || rootElement.querySelector('sheet')
  const rootTopic = findDirectChild(sheetElement, 'topic') || sheetElement?.querySelector('topic')
  if (!rootTopic) {
    throw new Error('未找到 XMind 根节点')
  }

  return buildMindmapData(convertXMindXmlTopic(rootTopic))
}

export const getMindmapRootText = (mindmapData, fallback = '') => {
  const text = String(mindmapData?.root?.data?.text || '').trim()
  return text || fallback
}

export const exportMindmapDataToXMindBlob = async (mindmapData, options = {}) => {
  const normalizedMindmapData = buildMindmapData(mindmapData?.root)
  const createId = createXMindIdFactory()
  const sheetId = createId('sheet')
  const rootTopic = convertMindmapNodeToXMindTopic(normalizedMindmapData.root, createId)
  const title = getMindmapRootText(normalizedMindmapData, options.title || '脑图')
  const generatedAt = new Date().toISOString()
  const content = [
    {
      id: sheetId,
      class: 'sheet',
      title,
      rootTopic,
      topicPositioning: 'fixed'
    }
  ]
  const metadata = {
    dataStructureVersion: '3',
    creator: {
      name: 'BearAI',
      version: '1.0.0'
    },
    layoutEngineVersion: '5',
    created: generatedAt,
    modified: generatedAt,
    activeSheetId: sheetId,
    topicCount: countAttachedTopics(rootTopic)
  }
  const manifest = {
    'file-entries': {
      'content.json': {
        'media-type': 'application/json'
      },
      'metadata.json': {
        'media-type': 'application/json'
      }
    }
  }

  const zip = new JSZip()
  zip.file('content.json', JSON.stringify(content, null, 2))
  zip.file('metadata.json', JSON.stringify(metadata, null, 2))
  zip.file('manifest.json', JSON.stringify(manifest, null, 2))

  return zip.generateAsync({
    type: 'blob',
    mimeType: 'application/vnd.xmind.workbook',
    compression: 'DEFLATE',
    compressionOptions: {
      level: 6
    }
  })
}

export const parseXMindFileToMindmapData = async file => {
  const arrayBuffer = await file.arrayBuffer()
  const zip = await JSZip.loadAsync(arrayBuffer)

  if (zip.files['content.json']) {
    const jsonContent = await zip.files['content.json'].async('text')
    return parseXMindJsonContent(jsonContent)
  }

  if (zip.files['content.xml']) {
    const xmlContent = await zip.files['content.xml'].async('text')
    return parseXMindXmlContent(xmlContent)
  }

  throw new Error('不支持的 XMind 文件格式')
}
