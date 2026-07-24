export const MINDMAP_TEST_STATUS_KEYS = Object.freeze([
  'not_run',
  'pass',
  'fail',
  'block',
  'not_test',
])

const MODULE_MATCH_FIELDS = Object.freeze([
  'moduleCategoryMatched',
  'moduleCategoryId',
  'moduleCategoryPath',
  'moduleCategoryMatchMode',
])

export const normalizeModuleMatchName = value => (
  String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase()
)

const commonSuffixLength = (left, right) => {
  let matched = 0
  while (
    matched < left.length &&
    matched < right.length &&
    left[left.length - 1 - matched] === right[right.length - 1 - matched]
  ) {
    matched += 1
  }
  return matched
}

export const buildManualCategoryMatchIndex = categoryTree => {
  const descriptors = []
  const byName = new Map()

  const walk = (categories, parentPath = []) => {
    ;(Array.isArray(categories) ? categories : []).forEach(category => {
      const name = String(category?.name || category?.label || '').trim()
      if (!name) return

      const path = [...parentPath, name]
      const descriptor = {
        id: category.id,
        name,
        path,
        normalizedPath: path.map(normalizeModuleMatchName).filter(Boolean),
      }
      descriptors.push(descriptor)

      const normalizedName = normalizeModuleMatchName(name)
      const candidates = byName.get(normalizedName) || []
      candidates.push(descriptor)
      byName.set(normalizedName, candidates)
      walk(category.children, path)
    })
  }

  walk(categoryTree)
  return { descriptors, byName }
}

const resolveCategoryMatch = (modulePath, categoryIndex) => {
  const normalizedPath = modulePath.map(normalizeModuleMatchName).filter(Boolean)
  if (!normalizedPath.length) return { category: null, mode: '' }

  const candidates = categoryIndex?.byName?.get(normalizedPath[normalizedPath.length - 1]) || []
  if (!candidates.length) return { category: null, mode: '' }

  const scored = candidates.map(category => ({
    category,
    score: commonSuffixLength(normalizedPath, category.normalizedPath),
  }))
  const bestScore = Math.max(...scored.map(item => item.score))
  const bestCandidates = scored.filter(item => item.score === bestScore)

  if (bestScore >= 2 && bestCandidates.length === 1) {
    return { category: bestCandidates[0].category, mode: 'path' }
  }
  if (candidates.length === 1) {
    return { category: candidates[0], mode: 'unique_name' }
  }
  return { category: null, mode: '' }
}

export const annotateMindmapModuleMatches = (mindmapData, categoryIndex) => {
  const summary = { total: 0, matched: 0, unmatched: 0 }

  const walk = (node, modulePath = []) => {
    if (!node || typeof node !== 'object') return
    const data = node.data && typeof node.data === 'object' ? node.data : (node.data = {})
    const currentModulePath = [...modulePath]

    if (data.nodeType === 'module') {
      const moduleName = String(data.text || '').trim()
      if (moduleName) currentModulePath.push(moduleName)

      const { category, mode } = resolveCategoryMatch(currentModulePath, categoryIndex)
      data.moduleCategoryMatched = Boolean(category)
      data.moduleCategoryId = category?.id ?? null
      data.moduleCategoryPath = category ? [...category.path] : []
      data.moduleCategoryMatchMode = mode
      summary.total += 1
      summary[category ? 'matched' : 'unmatched'] += 1
    } else {
      MODULE_MATCH_FIELDS.forEach(fieldName => delete data[fieldName])
    }

    ;(Array.isArray(node.children) ? node.children : []).forEach(child => {
      walk(child, currentModulePath)
    })
  }

  walk(mindmapData?.root)
  return summary
}

export const collectMindmapOverview = root => {
  const overview = {
    modules: { unmatched: 0, total: 0 },
    testpoints: Object.fromEntries(MINDMAP_TEST_STATUS_KEYS.map(key => [key, 0])),
    reviews: { unprocessed: 0, total: 0 },
  }

  const walk = node => {
    if (!node || typeof node !== 'object') return
    const data = node.data && typeof node.data === 'object' ? node.data : {}

    if (data.nodeType === 'module') {
      overview.modules.total += 1
      if (data.moduleCategoryMatched !== true) overview.modules.unmatched += 1
    }

    if (data.nodeType === 'testpoint') {
      const status = MINDMAP_TEST_STATUS_KEYS.includes(data.status) ? data.status : 'not_run'
      overview.testpoints[status] += 1

      const reviewOpinion = String(data.reviewOpinion || '').trim()
      const reviewStatus = String(data.reviewStatus || '').trim()
      if (reviewOpinion || ['未处理', '已处理'].includes(reviewStatus)) {
        overview.reviews.total += 1
        if (reviewStatus !== '已处理') overview.reviews.unprocessed += 1
      }
    }

    ;(Array.isArray(node.children) ? node.children : []).forEach(walk)
  }

  walk(root)
  return overview
}
