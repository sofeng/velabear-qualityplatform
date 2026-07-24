<template>
  <div v-if="analysisItems.length" class="analysis-narrative">
    <article
      v-for="item in analysisItems"
      :key="item.key"
      class="analysis-narrative__item"
      :class="`analysis-narrative__item--${item.key}`"
    >
      <h4>{{ item.title }}</h4>
      <p>{{ item.content }}</p>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const ANALYSIS_ORDER = [
  { key: 'problem', title: '\u5df2\u51fa\u73b0\u95ee\u9898\u5206\u6790' },
  { key: 'risk', title: '\u98ce\u9669\u5206\u6790' },
  { key: 'overall', title: '\u6574\u4f53\u8d28\u91cf\u5206\u6790' },
  { key: 'attention', title: '\u9700\u5173\u6ce8\u9879' },
  { key: 'excellent', title: '\u8868\u73b0\u4f18\u79c0\u9879' },
]

const NEGATIVE_KEYWORDS = [
  '\u5931\u8d25',
  '\u963b\u585e',
  '\u672a\u901a\u8fc7',
  '\u672a\u6267\u884c',
  '\u5f85\u5904\u7406',
  '\u5f85\u5ba1\u6838',
  '\u5f85\u9a8c\u8bc1',
  '\u5f85\u5173\u95ed',
  '\u5f85\u4fee\u590d',
  '\u672a\u5173\u95ed',
  '\u672a\u5b8c\u6210',
  '\u91cd\u5f00',
  '\u5ef6\u671f',
  '\u5f02\u5e38',
  '\u7f3a\u9677',
  '\u98ce\u9669',
  '\u9ad8\u4f18\u5148\u7ea7',
  '\u9ad8\u4e25\u91cd',
  'critical',
  'high',
  'pending',
  'block',
  'fail',
  'reopen',
  'open',
  'new',
  'in_progress',
]

const POSITIVE_KEYWORDS = [
  '\u901a\u8fc7',
  '\u5df2\u5173\u95ed',
  '\u5173\u95ed',
  '\u5b8c\u6210',
  '\u5df2\u5b8c\u6210',
  '\u5ba1\u6838\u901a\u8fc7',
  '\u6210\u529f',
  '\u7a33\u5b9a',
  '\u5df2\u4ea4\u4ed8',
  '\u5df2\u4e0a\u7ebf',
  '\u9a8c\u6536',
  '\u6b63\u5e38',
  'pass',
  'closed',
  'done',
  'approved',
  'resolved',
  'success',
]

const OPEN_STATUS_KEYWORDS = [
  '\u5f85',
  '\u672a',
  '\u963b\u585e',
  '\u91cd\u5f00',
  '\u8fdb\u884c\u4e2d',
  '\u5904\u7406\u4e2d',
  '\u4fee\u590d\u4e2d',
  '\u5f00\u53d1\u4e2d',
  '\u6d4b\u8bd5\u4e2d',
  '\u8bbe\u8ba1\u4e2d',
  'open',
  'new',
  'pending',
  'reopen',
  'todo',
  'doing',
  'progress',
]

const CLOSED_STATUS_KEYWORDS = [
  '\u901a\u8fc7',
  '\u5df2\u5173\u95ed',
  '\u5173\u95ed',
  '\u5b8c\u6210',
  '\u5df2\u5b8c\u6210',
  '\u5df2\u4ea4\u4ed8',
  '\u5df2\u4e0a\u7ebf',
  '\u9a8c\u6536',
  'closed',
  'resolved',
  'done',
  'pass',
  'approved',
]

const HIGH_PRIORITY_KEYWORDS = [
  'p0',
  'p1',
  '\u9ad8',
  '\u7d27\u6025',
  '\u7279\u6025',
  '\u7279\u9ad8',
  'critical',
  'highest',
  'high',
  'blocker',
]

const LOW_PRIORITY_KEYWORDS = [
  'p3',
  'p4',
  '\u4f4e',
  '\u666e\u901a',
  '\u4e00\u822c',
  'low',
  'lowest',
]

const HIGH_SEVERITY_KEYWORDS = [
  '\u81f4\u547d',
  '\u4e25\u91cd',
  '\u963b\u65ad',
  's0',
  's1',
  's2',
  'critical',
  'high',
]

const LOW_SEVERITY_KEYWORDS = [
  '\u63d0\u793a',
  '\u5efa\u8bae',
  '\u8f7b\u5fae',
  's3',
  's4',
  'low',
  'minor',
  'trivial',
]

const PEOPLE_ROLE_KEYWORDS = [
  '\u4ea7\u54c1',
  '\u524d\u7aef',
  '\u540e\u7aef',
  '\u5f00\u53d1',
  '\u6d4b\u8bd5',
  '\u8d23\u4efb\u5c0f\u7ec4',
  '\u5c0f\u7ec4',
  '\u8d23\u4efb\u65b9',
  '\u4eba\u5458',
]

const COVERAGE_GAP_KEYWORDS = [
  '\u672a\u5173\u8054',
  '\u65e0\u7528\u4f8b',
  '\u65e0\u6d4b\u8bd5\u70b9',
  '\u7f3a\u5931',
  '\u7a7a\u767d',
  '\u7f3a\u53e3',
  '\u7f3a\u6f0f',
]

const normalizeText = value => String(value ?? '').trim()

const toNumber = value => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  const normalized = normalizeText(value).replace(/,/g, '')
  if (!normalized) {
    return null
  }

  const parsedValue = Number(normalized)
  return Number.isFinite(parsedValue) ? parsedValue : null
}

const roundTo = (value, digits = 1) => {
  const factor = 10 ** digits
  return Math.round((Number(value) || 0) * factor) / factor
}

const formatNumber = value => {
  const numericValue = toNumber(value)
  if (numericValue === null) {
    return normalizeText(value) || '-'
  }

  const roundedValue = roundTo(numericValue, 2)
  return Number.isInteger(roundedValue)
    ? String(roundedValue)
    : roundedValue.toFixed(2).replace(/\.?0+$/, '')
}

const formatPercent = value => `${formatNumber(value)}%`

const includesAny = (text, keywords) => {
  const normalized = normalizeText(text).toLowerCase()
  return keywords.some(keyword => normalized.includes(String(keyword).toLowerCase()))
}

const classifyLabel = label => {
  if (includesAny(label, NEGATIVE_KEYWORDS)) {
    return 'negative'
  }

  if (includesAny(label, POSITIVE_KEYWORDS)) {
    return 'positive'
  }

  return 'neutral'
}

const classifyCell = (rowLabel, columnLabel) => {
  if (includesAny(`${rowLabel} ${columnLabel}`, NEGATIVE_KEYWORDS)) {
    return 'negative'
  }

  if (includesAny(`${rowLabel} ${columnLabel}`, POSITIVE_KEYWORDS)) {
    return 'positive'
  }

  return 'neutral'
}

const getMetricValue = item => toNumber(item?.count ?? item?.total ?? item?.value) ?? 0

const getMetricShare = item => toNumber(item?.share ?? item?.ratio) ?? 0

const sortByValue = items => items.slice().sort((left, right) => getMetricValue(right) - getMetricValue(left))

const getPrimaryItems = summary => (summary.kind === 'distribution' ? summary.rows : summary.rowItems || [])

const getSecondaryItems = summary => (summary.kind === 'table' ? summary.columnItems || [] : [])

const getAllSearchItems = summary => [
  ...getPrimaryItems(summary).map(item => ({ ...item, axis: 'primary' })),
  ...getSecondaryItems(summary).map(item => ({ ...item, axis: 'secondary' })),
]

const findTopMatch = (items, keywords) =>
  sortByValue(items.filter(item => includesAny(item?.label, keywords)))[0] || null

const findWeakestItem = items =>
  items.length
    ? items.slice().sort((left, right) => getMetricShare(left) - getMetricShare(right) || getMetricValue(left) - getMetricValue(right))[0]
    : null

const sumShares = (items, limit = 3) =>
  roundTo(items.slice(0, limit).reduce((total, item) => total + getMetricShare(item), 0), 1)

const describeItem = item => {
  if (!item) {
    return '-'
  }

  return `${item.label}(${formatNumber(getMetricValue(item))} / ${formatPercent(getMetricShare(item))})`
}

const describeItems = (items, limit = 2) =>
  items.slice(0, limit).map(describeItem).join('\u3001')

const describeCell = cell => {
  if (!cell) {
    return '-'
  }

  return `${cell.rowLabel} \u00d7 ${cell.columnLabel}(${formatNumber(cell.value)} / ${formatPercent(cell.share)})`
}

const findTopCell = (summary, predicate = () => true) => {
  if (!Array.isArray(summary?.cellItems) || !summary.cellItems.length) {
    return null
  }

  return summary.cellItems.find(predicate) || null
}

const findTopCellByAnyKeywords = (summary, keywords) =>
  findTopCell(summary, cell => includesAny(cell.rowLabel, keywords) || includesAny(cell.columnLabel, keywords))

const findTopCellByAxisKeywords = (summary, rowKeywords = [], columnKeywords = []) =>
  findTopCell(summary, cell => {
    const rowMatched = rowKeywords.length ? includesAny(cell.rowLabel, rowKeywords) : true
    const columnMatched = columnKeywords.length ? includesAny(cell.columnLabel, columnKeywords) : true
    return rowMatched && columnMatched
  })

const summarizeDistribution = block => {
  const sourceRows = Array.isArray(block?.rows) ? block.rows : []
  if (!sourceRows.length) {
    return null
  }

  const provisionalRows = sourceRows.map(row => ({
    label: normalizeText(row?.label) || '-',
    count: toNumber(row?.count) ?? 0,
    ratio: toNumber(row?.ratio),
    sentiment: classifyLabel(row?.label),
  }))

  const total = provisionalRows.reduce((sum, row) => sum + row.count, 0)
  const rows = provisionalRows
    .map(row => ({
      ...row,
      share: row.ratio !== null ? row.ratio : (total ? roundTo((row.count / total) * 100, 1) : 0),
    }))
    .sort((left, right) => right.count - left.count)

  const negativeRows = rows.filter(row => row.sentiment === 'negative')
  const positiveRows = rows.filter(row => row.sentiment === 'positive')
  const negativeTotal = negativeRows.reduce((sum, row) => sum + row.count, 0)
  const positiveTotal = positiveRows.reduce((sum, row) => sum + row.count, 0)

  return {
    kind: 'distribution',
    title: normalizeText(block?.title) || '\u5f53\u524d\u56fe\u8868',
    total,
    rows,
    topRow: rows[0] || null,
    topNegativeRow: negativeRows[0] || null,
    topPositiveRow: positiveRows[0] || null,
    negativeShare: total ? roundTo((negativeTotal / total) * 100, 1) : 0,
    positiveShare: total ? roundTo((positiveTotal / total) * 100, 1) : 0,
  }
}

const summarizeTableLike = block => {
  const rows = Array.isArray(block?.rows) ? block.rows : []
  const columns = Array.isArray(block?.columns) ? block.columns : []
  if (!rows.length || columns.length < 2) {
    return null
  }

  const dimensionColumn = columns[0]
  const numericColumns = columns
    .slice(1)
    .filter(column => column.key !== 'total' && rows.some(row => toNumber(row?.[column.key]) !== null))

  if (numericColumns.length) {
    const rawRowItems = rows.map(row => {
      const label = normalizeText(row?.[dimensionColumn.key]) || '-'
      const total = numericColumns.reduce((sum, column) => sum + (toNumber(row?.[column.key]) ?? 0), 0)
      return {
        label,
        total,
        sentiment: classifyLabel(label),
      }
    })

    const rawColumnItems = numericColumns.map(column => {
      const label = normalizeText(column.label) || column.key
      const total = rows.reduce((sum, row) => sum + (toNumber(row?.[column.key]) ?? 0), 0)
      return {
        key: column.key,
        label,
        total,
        sentiment: classifyLabel(label),
      }
    })

    const total = rawRowItems.reduce((sum, item) => sum + item.total, 0)
    const rowItems = rawRowItems
      .map(item => ({
        ...item,
        share: total ? roundTo((item.total / total) * 100, 1) : 0,
      }))
      .sort((left, right) => right.total - left.total)

    const columnItems = rawColumnItems
      .map(item => ({
        ...item,
        share: total ? roundTo((item.total / total) * 100, 1) : 0,
      }))
      .sort((left, right) => right.total - left.total)

    const cellItems = rows
      .flatMap(row => {
        const rowLabel = normalizeText(row?.[dimensionColumn.key]) || '-'
        return numericColumns.map(column => {
          const columnLabel = normalizeText(column.label) || column.key
          const value = toNumber(row?.[column.key]) ?? 0
          return {
            rowLabel,
            columnLabel,
            value,
            share: total ? roundTo((value / total) * 100, 1) : 0,
            sentiment: classifyCell(rowLabel, columnLabel),
          }
        })
      })
      .sort((left, right) => right.value - left.value)

    const negativeTotal = cellItems
      .filter(item => item.sentiment === 'negative')
      .reduce((sum, item) => sum + item.value, 0)
    const positiveTotal = cellItems
      .filter(item => item.sentiment === 'positive')
      .reduce((sum, item) => sum + item.value, 0)

    return {
      kind: 'table',
      coverageMode: false,
      title: normalizeText(block?.title) || '\u5f53\u524d\u56fe\u8868',
      total,
      rowItems,
      columnItems,
      cellItems,
      topRow: rowItems[0] || null,
      topColumn: columnItems[0] || null,
      topCell: cellItems[0] || null,
      topNegativeCell: cellItems.find(item => item.sentiment === 'negative') || null,
      topPositiveCell: cellItems.find(item => item.sentiment === 'positive') || null,
      negativeShare: total ? roundTo((negativeTotal / total) * 100, 1) : 0,
      positiveShare: total ? roundTo((positiveTotal / total) * 100, 1) : 0,
      rowCount: rowItems.length,
      columnCount: columnItems.length,
    }
  }

  const coverageColumns = columns
    .slice(1)
    .filter(column => rows.some(row => normalizeText(row?.[column.key])))

  if (!coverageColumns.length) {
    return null
  }

  const columnItems = coverageColumns
    .map(column => {
      const filledCount = rows.reduce((sum, row) => sum + (normalizeText(row?.[column.key]) ? 1 : 0), 0)
      return {
        key: column.key,
        label: normalizeText(column.label) || column.key,
        total: filledCount,
        share: rows.length ? roundTo((filledCount / rows.length) * 100, 1) : 0,
        sentiment: classifyLabel(column.label),
      }
    })
    .sort((left, right) => right.total - left.total)

  const rowItems = rows
    .map(row => {
      const label = normalizeText(row?.[dimensionColumn.key]) || '-'
      const filledCount = coverageColumns.reduce(
        (sum, column) => sum + (normalizeText(row?.[column.key]) ? 1 : 0),
        0
      )
      return {
        label,
        total: filledCount,
        share: coverageColumns.length ? roundTo((filledCount / coverageColumns.length) * 100, 1) : 0,
        sentiment: classifyLabel(label),
      }
    })
    .sort((left, right) => right.total - left.total)

  const total = rowItems.reduce((sum, item) => sum + item.total, 0)
  const averageCoverage = columnItems.length
    ? roundTo(columnItems.reduce((sum, item) => sum + item.share, 0) / columnItems.length, 1)
    : null

  return {
    kind: 'table',
    coverageMode: true,
    title: normalizeText(block?.title) || '\u5f53\u524d\u56fe\u8868',
    total,
    rowItems,
    columnItems,
    cellItems: [],
    topRow: rowItems[0] || null,
    topColumn: columnItems[0] || null,
    weakestRow: findWeakestItem(rowItems),
    weakestColumn: findWeakestItem(columnItems),
    averageCoverage,
    negativeShare: 0,
    positiveShare: averageCoverage ?? 0,
    rowCount: rowItems.length,
    columnCount: columnItems.length,
  }
}

const resolveTheme = summary => {
  const title = normalizeText(summary?.title)

  if (includesAny(title, ['\u5de5\u65f6'])) {
    return 'workload'
  }

  if (includesAny(title, ['\u6839\u56e0'])) {
    return 'root-cause'
  }

  if (includesAny(title, ['\u4e25\u91cd\u7a0b\u5ea6'])) {
    return 'severity'
  }

  if (includesAny(title, ['\u4f18\u5148\u7ea7'])) {
    return 'priority'
  }

  if (includesAny(title, ['\u8986\u76d6', '\u5173\u8054\u60c5\u51b5', '\u5173\u952e\u4fe1\u606f', '\u8d44\u4ea7', '\u65e0\u7528\u4f8b'])) {
    return 'coverage'
  }

  if (includesAny(title, ['\u4ea7\u54c1\u7ecf\u7406', '\u524d\u7aef\u5f00\u53d1', '\u540e\u7aef\u5f00\u53d1', '\u6d4b\u8bd5\u4eba\u5458', '\u8d23\u4efb\u5c0f\u7ec4'])) {
    return 'people'
  }

  if (includesAny(title, ['\u6a21\u5757'])) {
    return 'module'
  }

  if (includesAny(title, ['\u72b6\u6001', '\u6267\u884c', '\u5ba1\u6838'])) {
    return 'status'
  }

  if (includesAny(title, ['\u00d7', '\u770b\u677f', '\u98ce\u9669\u94fe\u8def'])) {
    return 'matrix'
  }

  return summary.coverageMode ? 'coverage' : 'distribution'
}

const buildStatusNarrative = summary => {
  const items = getAllSearchItems(summary)
  const openItem = findTopMatch(items, OPEN_STATUS_KEYWORDS)
  const closedItem = findTopMatch(items, CLOSED_STATUS_KEYWORDS)
  const openCell = findTopCellByAnyKeywords(summary, OPEN_STATUS_KEYWORDS)
  const topShare = getMetricShare(summary.topRow)
  const openShare = openItem ? getMetricShare(openItem) : summary.negativeShare
  const focusItems = sortByValue(items.filter(item => includesAny(item.label, OPEN_STATUS_KEYWORDS))).slice(0, 2)

  const problem = openCell
    ? `\u5728\u300a${summary.title}\u300b\u4e2d\uff0c${describeCell(openCell)}\u662f\u5f53\u524d\u6700\u4e3b\u8981\u7684\u672a\u95ed\u73af\u4ea4\u53c9\u70b9\uff0c\u8bf4\u660e\u95ee\u9898\u5df2\u4ece\u5355\u4e00\u72b6\u6001\u79ef\u538b\u6f14\u53d8\u4e3a\u7ec4\u5408\u6027\u5361\u70b9\u3002`
    : openItem
      ? `\u5728\u300a${summary.title}\u300b\u4e2d\uff0c${describeItem(openItem)}\u662f\u9996\u8981\u5f85\u6e05\u7406\u72b6\u6001\uff0c\u8bf4\u660e\u5f53\u524d\u8fd8\u5b58\u5728\u660e\u663e\u7684\u95ed\u73af\u6ede\u540e\u3002`
      : `\u300a${summary.title}\u300b\u76ee\u524d\u4ee5${describeItem(summary.topRow)}\u4e3a\u4e3b\u5bfc\u5206\u5e03\uff0c\u72b6\u6001\u7ed3\u6784\u5df2\u51fa\u73b0\u660e\u663e\u503e\u659c\u3002`

  const risk = openShare >= 35
    ? `\u672a\u95ed\u73af\u72b6\u6001\u5360\u6bd4\u5df2\u8fbe${formatPercent(openShare)}\uff0c\u5bf9\u7248\u672c\u8282\u594f\u3001\u56de\u5f52\u9a8c\u8bc1\u548c\u4e0a\u7ebf\u51b3\u7b56\u90fd\u4f1a\u5f62\u6210\u8fde\u9501\u538b\u529b\u3002`
    : topShare >= 45
      ? `\u5934\u90e8\u72b6\u6001${summary.topRow?.label}\u5360\u6bd4\u5df2\u8fbe${formatPercent(topShare)}\uff0c\u96c6\u4e2d\u5ea6\u504f\u9ad8\uff0c\u540e\u7eed\u53ea\u8981\u8be5\u72b6\u6001\u7ee7\u7eed\u62ac\u5347\uff0c\u6574\u4f53\u66f2\u7ebf\u5c31\u4f1a\u88ab\u5feb\u901f\u62c9\u504f\u3002`
      : `\u72b6\u6001\u5206\u5e03\u6682\u672a\u8fdb\u5165\u5931\u63a7\u533a\uff0c\u4f46${openItem ? openItem.label : summary.topRow?.label}\u4ecd\u662f\u6700\u9700\u8981\u7ee7\u7eed\u76ef\u9632\u7684\u6ce2\u52a8\u70b9\u3002`

  const overall = closedItem && getMetricShare(closedItem) >= 50 && openShare <= 20
    ? `\u4ece\u6d4b\u8bd5\u603b\u76d1\u89c6\u89d2\u770b\uff0c\u8be5\u72b6\u6001\u9762\u603b\u4f53\u53ef\u63a7\uff0c\u95ed\u73af\u72b6\u6001\u5df2\u5177\u5907\u4e3b\u5bfc\u4f18\u52bf\uff0c\u53d1\u5e03\u524d\u66f4\u504f\u5411\u505a\u5c40\u90e8\u6536\u53e3\u3002`
    : openShare >= 30
      ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u66f4\u63a5\u8fd1\u201c\u95ed\u73af\u80fd\u529b\u4e0d\u8db3\u201d\u800c\u4e0d\u662f\u201c\u4ec5\u6709\u4e2a\u522b\u95ee\u9898\u201d\uff0c\u5efa\u8bae\u6309\u98ce\u9669\u770b\u677f\u6765\u9a71\u52a8\u6bcf\u65e5\u6536\u655b\u3002`
      : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u5904\u4e8e\u53ef\u63a7\u4f46\u4e0d\u7a33\u5b9a\u533a\u95f4\uff0c\u8bf4\u660e\u95ed\u73af\u80fd\u529b\u6709\u57fa\u7840\uff0c\u4f46\u8fd8\u672a\u5f62\u6210\u8db3\u591f\u7a33\u5b9a\u7684\u8282\u594f\u3002`

  const attention = focusItems.length
    ? `\u63a5\u4e0b\u6765\u9700\u91cd\u70b9\u8ddf\u8fdb${describeItems(focusItems)}\uff0c\u4f18\u5148\u786e\u8ba4\u662f\u5426\u5b58\u5728\u963b\u585e\u3001\u91cd\u5f00\u6216\u957f\u65f6\u95f4\u505c\u7559\u72b6\u6001\u3002`
    : `\u63a5\u4e0b\u6765\u9700\u6301\u7eed\u89c2\u5bdf\u5934\u90e8\u72b6\u6001\u7684\u589e\u957f\u65b9\u5411\uff0c\u907f\u514d\u65b0\u7684\u79ef\u538b\u9879\u5728\u4e0b\u4e00\u4e2a\u8282\u594f\u8fdb\u5165\u524d\u5217\u3002`

  const excellent = closedItem
    ? `${describeItem(closedItem)}\u662f\u5f53\u524d\u6700\u660e\u786e\u7684\u6b63\u5411\u4fe1\u53f7\uff0c\u8bf4\u660e\u56e2\u961f\u4ecd\u7136\u5177\u5907\u6301\u7eed\u95ed\u73af\u548c\u6d88\u5316\u5b58\u91cf\u7684\u80fd\u529b\u3002`
    : openShare <= 15
      ? `\u76ee\u524d\u672a\u51fa\u73b0\u660e\u663e\u7684\u72b6\u6001\u79ef\u538b\u5cf0\u503c\uff0c\u6574\u4f53\u72b6\u6001\u7ed3\u6784\u76f8\u5bf9\u5e73\u7a33\uff0c\u8fd9\u662f\u5f53\u524d\u53ef\u4ee5\u4fdd\u6301\u7684\u597d\u4fe1\u53f7\u3002`
      : `\u672c\u56fe\u4e2d\u6b63\u5411\u72b6\u6001\u4f18\u52bf\u8fd8\u4e0d\u591f\u7a81\u51fa\uff0c\u4f18\u5148\u76ee\u6807\u4ecd\u5e94\u662f\u538b\u964d\u5b58\u91cf\u3001\u63d0\u5347\u95ed\u73af\u901f\u5ea6\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildPriorityNarrative = summary => {
  const items = getAllSearchItems(summary)
  const highPriorityItem = findTopMatch(items, HIGH_PRIORITY_KEYWORDS)
  const lowPriorityItem = findTopMatch(items, LOW_PRIORITY_KEYWORDS)
  const unresolvedHighCell =
    findTopCellByAxisKeywords(summary, HIGH_PRIORITY_KEYWORDS, OPEN_STATUS_KEYWORDS) ||
    findTopCellByAxisKeywords(summary, OPEN_STATUS_KEYWORDS, HIGH_PRIORITY_KEYWORDS) ||
    findTopCellByAnyKeywords(summary, HIGH_PRIORITY_KEYWORDS)
  const resolvedHighCell =
    findTopCellByAxisKeywords(summary, HIGH_PRIORITY_KEYWORDS, CLOSED_STATUS_KEYWORDS) ||
    findTopCellByAxisKeywords(summary, CLOSED_STATUS_KEYWORDS, HIGH_PRIORITY_KEYWORDS)
  const highShare = highPriorityItem ? getMetricShare(highPriorityItem) : 0

  const problem = unresolvedHighCell
    ? `\u300a${summary.title}\u300b\u4e2d\u6700\u9700\u8981\u5f53\u573a\u5904\u7406\u7684\u662f${describeCell(unresolvedHighCell)}\uff0c\u8fd9\u7c7b\u201c\u9ad8\u4f18\u5148\u7ea7 + \u672a\u95ed\u73af\u201d\u7684\u7ec4\u5408\u76f4\u63a5\u5bf9\u53d1\u5e03\u51b3\u7b56\u6784\u6210\u538b\u529b\u3002`
    : highPriorityItem
      ? `\u300a${summary.title}\u300b\u4e2d\u9ad8\u4f18\u5148\u7ea7\u4e8b\u9879\u4ee5${describeItem(highPriorityItem)}\u4e3a\u4e3b\uff0c\u8bf4\u660e\u5f53\u524d\u56e2\u961f\u7684\u4e3b\u8981\u7ba1\u63a7\u91cd\u70b9\u4ecd\u5728\u9ad8\u7d27\u6025\u4e8b\u9879\u3002`
      : `\u300a${summary.title}\u300b\u76ee\u524d\u4ee5${describeItem(summary.topRow)}\u4e3a\u4e3b\u5bfc\u5206\u5e03\uff0c\u9700\u7ed3\u5408\u4e1a\u52a1\u8bed\u4e49\u786e\u8ba4\u4f18\u5148\u7ea7\u7ed3\u6784\u662f\u5426\u7b26\u5408\u9884\u671f\u3002`

  const risk = highShare >= 30
    ? `\u9ad8\u4f18\u5148\u7ea7\u5360\u6bd4\u5df2\u8fbe${formatPercent(highShare)}\uff0c\u8fd9\u4e0d\u53ea\u662f\u7ba1\u7406\u6392\u671f\u95ee\u9898\uff0c\u800c\u662f\u6574\u4e2a\u7248\u672c\u8d28\u91cf\u7136\u70b9\u8fc7\u4e8e\u96c6\u4e2d\u7684\u4fe1\u53f7\u3002`
    : unresolvedHighCell && unresolvedHighCell.share >= 10
      ? `\u9ad8\u4f18\u5148\u7ea7\u672a\u95ed\u73af\u4ea4\u53c9\u70b9\u5360\u5168\u56fe${formatPercent(unresolvedHighCell.share)}\uff0c\u4e00\u65e6\u95ed\u73af\u901f\u5ea6\u4e0d\u8db3\uff0c\u4f1a\u5feb\u901f\u63a8\u9ad8\u53d1\u5e03\u524d\u963b\u65ad\u98ce\u9669\u3002`
      : `\u4f18\u5148\u7ea7\u7ed3\u6784\u6682\u672a\u51fa\u73b0\u5931\u63a7\uff0c\u4f46${highPriorityItem ? highPriorityItem.label : summary.topRow?.label}\u4ecd\u662f\u8d44\u6e90\u503e\u659c\u548c\u7ba1\u7406\u5347\u7ea7\u7684\u6838\u5fc3\u89c2\u5bdf\u70b9\u3002`

  const overall = highShare <= 15 && resolvedHighCell
    ? `\u4ece\u6d4b\u8bd5\u603b\u76d1\u89c6\u89d2\u770b\uff0c\u9ad8\u4f18\u5148\u7ea7\u9879\u89c4\u6a21\u53ef\u63a7\uff0c\u4e14${describeCell(resolvedHighCell)}\u63d0\u4f9b\u4e86\u826f\u597d\u7684\u95ed\u73af\u8bc1\u636e\uff0c\u6574\u4f53\u8d28\u91cf\u8282\u594f\u76f8\u5bf9\u5065\u5eb7\u3002`
    : highShare >= 25
      ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u7248\u672c\u4ecd\u5904\u5728\u201c\u9ad8\u4f18\u5148\u7ea7\u4e8b\u9879\u9a71\u52a8\u201d\u9636\u6bb5\uff0c\u8fd9\u610f\u5473\u7740\u540e\u7eed\u6d4b\u8bd5\u548c\u53d1\u5e03\u4f9d\u65e7\u4f1a\u53d7\u5230\u5934\u90e8\u95ee\u9898\u7275\u5236\u3002`
      : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u4f18\u5148\u7ea7\u7ed3\u6784\u57fa\u672c\u53ef\u63a7\uff0c\u4f46\u8fd8\u6ca1\u6709\u8fbe\u5230\u53ef\u4ee5\u5bf9\u9ad8\u4f18\u9879\u5b8c\u5168\u653e\u5fc3\u7684\u7a0b\u5ea6\u3002`

  const attentionTargets = sortByValue(items.filter(item => includesAny(item.label, HIGH_PRIORITY_KEYWORDS))).slice(0, 2)
  const attention = attentionTargets.length
    ? `\u63a5\u4e0b\u6765\u9700\u76ef\u7d27${describeItems(attentionTargets)}\uff0c\u540c\u65f6\u6838\u67e5\u5b83\u4eec\u662f\u5426\u5df2\u7ecf\u8f6c\u5165\u95ed\u73af\u6216\u4ecd\u5904\u4e8e\u957f\u5c3e\u62d6\u5ef6\u72b6\u6001\u3002`
    : `\u63a5\u4e0b\u6765\u5efa\u8bae\u6309\u9ad8\u3001\u4e2d\u3001\u4f4e\u4f18\u5148\u7ea7\u5206\u5c42\u8ddf\u8fdb\uff0c\u786e\u4fdd\u6700\u9ad8\u4f18\u4e8b\u9879\u4e0d\u4f1a\u5728\u8282\u594f\u4e2d\u51fa\u73b0\u53cd\u590d\u7feb\u8fd4\u3002`

  const excellent = resolvedHighCell
    ? `${describeCell(resolvedHighCell)}\u662f\u672c\u56fe\u6700\u503c\u5f97\u4fdd\u7559\u7684\u6b63\u5411\u4fe1\u53f7\uff0c\u8fd9\u8bf4\u660e\u56e2\u961f\u5bf9\u9ad8\u4f18\u9879\u4ecd\u6709\u5feb\u901f\u6536\u655b\u80fd\u529b\u3002`
    : highShare <= 10 || !highPriorityItem
      ? `\u9ad8\u4f18\u5148\u7ea7\u89c4\u6a21\u672a\u6210\u4e3a\u4e3b\u5bfc\u9762\uff0c\u8fd9\u672c\u8eab\u5c31\u662f\u7248\u672c\u8d28\u91cf\u57fa\u7ebf\u76f8\u5bf9\u7a33\u5b9a\u7684\u4f53\u73b0\u3002`
      : lowPriorityItem
        ? `${describeItem(lowPriorityItem)}\u4e3a\u5f53\u524d\u7ed3\u6784\u63d0\u4f9b\u4e86\u7f13\u51b2\u5e26\uff0c\u8bf4\u660e\u8d44\u6e90\u5e76\u672a\u88ab\u9ad8\u4f18\u9879\u5b8c\u5168\u6324\u5360\u3002`
        : `\u5f53\u524d\u6700\u9700\u8981\u505a\u7684\u4ecd\u662f\u538b\u964d\u9ad8\u4f18\u4e8b\u9879\u7684\u672a\u95ed\u73af\u5b58\u91cf\uff0c\u6b63\u5411\u4fe1\u53f7\u8fd8\u9700\u901a\u8fc7\u540e\u7eed\u6536\u655b\u6765\u5efa\u7acb\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildSeverityNarrative = summary => {
  const items = getAllSearchItems(summary)
  const highSeverityItem = findTopMatch(items, HIGH_SEVERITY_KEYWORDS)
  const lowSeverityItem = findTopMatch(items, LOW_SEVERITY_KEYWORDS)
  const unresolvedHighCell =
    findTopCellByAxisKeywords(summary, HIGH_SEVERITY_KEYWORDS, OPEN_STATUS_KEYWORDS) ||
    findTopCellByAxisKeywords(summary, OPEN_STATUS_KEYWORDS, HIGH_SEVERITY_KEYWORDS) ||
    findTopCellByAnyKeywords(summary, HIGH_SEVERITY_KEYWORDS)
  const resolvedHighCell =
    findTopCellByAxisKeywords(summary, HIGH_SEVERITY_KEYWORDS, CLOSED_STATUS_KEYWORDS) ||
    findTopCellByAxisKeywords(summary, CLOSED_STATUS_KEYWORDS, HIGH_SEVERITY_KEYWORDS)
  const highShare = highSeverityItem ? getMetricShare(highSeverityItem) : 0

  const problem = unresolvedHighCell
    ? `\u300a${summary.title}\u300b\u5df2\u663e\u793a\u51fa${describeCell(unresolvedHighCell)}\u8fd9\u4e00\u9ad8\u4e25\u91cd\u5ea6\u672a\u95ed\u73af\u7ec4\u5408\uff0c\u8fd9\u7c7b\u95ee\u9898\u5bf9\u7248\u672c\u53ef\u53d1\u5e03\u6027\u7684\u51b2\u51fb\u6700\u76f4\u63a5\u3002`
    : highSeverityItem
      ? `\u300a${summary.title}\u300b\u4e2d\u9ad8\u4e25\u91cd\u5ea6\u9879\u4ee5${describeItem(highSeverityItem)}\u4e3a\u4e3b\uff0c\u8fd9\u610f\u5473\u7740\u5f53\u524d\u4ecd\u5b58\u5728\u76f4\u63a5\u5f71\u54cd\u4e3b\u5e72\u8d28\u91cf\u7684\u7f3a\u9677\u538b\u529b\u3002`
      : `\u300a${summary.title}\u300b\u76ee\u524d\u4ee5${describeItem(summary.topRow)}\u4e3a\u4e3b\u5bfc\uff0c\u9700\u8fdb\u4e00\u6b65\u7ed3\u5408\u5b9e\u9645\u4e25\u91cd\u5ea6\u5206\u7ea7\u6807\u51c6\u6765\u786e\u8ba4\u98ce\u9669\u5f3a\u5ea6\u3002`

  const risk = highShare >= 20
    ? `\u9ad8\u4e25\u91cd\u5ea6\u5360\u6bd4\u5df2\u8fbe${formatPercent(highShare)}\uff0c\u5bf9\u6838\u5fc3\u6d41\u7a0b\u3001\u4e3b\u8981\u4ea4\u4e92\u6216\u5173\u952e\u6570\u636e\u94fe\u8def\u90fd\u6709\u8f83\u5927\u7684\u5931\u6548\u98ce\u9669\u3002`
    : unresolvedHighCell && unresolvedHighCell.share >= 8
      ? `\u9ad8\u4e25\u91cd\u5ea6\u672a\u95ed\u73af\u4ea4\u53c9\u70b9\u5360\u5168\u56fe${formatPercent(unresolvedHighCell.share)}\uff0c\u4e00\u65e6\u56de\u5f52\u4e0d\u5145\u5206\u6216\u6536\u53e3\u4e0d\u5e72\u51c0\uff0c\u4e0a\u7ebf\u540e\u5f88\u5bb9\u6613\u5f15\u53d1\u91cd\u5927\u53cd\u590d\u3002`
      : `\u4e25\u91cd\u5ea6\u7ed3\u6784\u76ee\u524d\u4ecd\u9700\u8ddf\u8fdb\u5934\u90e8\u9879\uff0c\u7279\u522b\u8981\u907f\u514d\u201c\u9ad8\u4e25\u91cd\u5ea6 + \u957f\u5c3e\u672a\u95ed\u73af\u201d\u7684\u98ce\u9669\u7ec4\u5408\u3002`

  const overall = highShare <= 10 && resolvedHighCell
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u9ad8\u4e25\u91cd\u95ee\u9898\u89c4\u6a21\u53ef\u63a7\uff0c\u4e14\u5df2\u6709\u660e\u786e\u95ed\u73af\u4fe1\u53f7\uff0c\u8fd9\u5bf9\u53d1\u5e03\u4fe1\u5fc3\u662f\u52a0\u5206\u9879\u3002`
    : highShare >= 18
      ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u7248\u672c\u8fd8\u5904\u5728\u201c\u9ad8\u4e25\u91cd\u95ee\u9898\u9700\u8981\u91cd\u70b9\u7ba1\u63a7\u201d\u7684\u9636\u6bb5\uff0c\u5f53\u524d\u66f4\u9002\u5408\u6309\u963b\u65ad\u98ce\u9669\u4f18\u5148\u800c\u4e0d\u662f\u6309\u89c4\u6a21\u4f18\u5148\u63a8\u8fdb\u3002`
      : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u4e25\u91cd\u5ea6\u9762\u8fd8\u672a\u51fa\u73b0\u5931\u63a7\uff0c\u4f46\u4ecd\u9700\u4fdd\u6301\u5bf9\u9ad8\u5371\u7f3a\u9677\u7684\u5feb\u901f\u8bc6\u522b\u548c\u5feb\u901f\u95ed\u73af\u3002`

  const attentionTargets = sortByValue(items.filter(item => includesAny(item.label, HIGH_SEVERITY_KEYWORDS))).slice(0, 2)
  const attention = attentionTargets.length
    ? `\u5efa\u8bae\u4e0b\u4e00\u8f6e\u76ef\u7d27${describeItems(attentionTargets)}\uff0c\u4f18\u5148\u786e\u8ba4\u5b83\u4eec\u662f\u5426\u5df2\u5b8c\u6210\u56de\u5f52\u3001\u590d\u73b0\u53ca\u5f71\u54cd\u8303\u56f4\u8bc4\u4f30\u3002`
    : `\u5efa\u8bae\u6309\u4e25\u91cd\u5ea6\u5206\u5c42\u7ba1\u7406\u6d4b\u8bd5\u8d44\u6e90\uff0c\u786e\u4fdd\u9ad8\u5371\u9879\u6c38\u8fdc\u62e5\u6709\u6700\u9ad8\u7684\u8ddf\u8fdb\u4f18\u5148\u7ea7\u3002`

  const excellent = resolvedHighCell
    ? `${describeCell(resolvedHighCell)}\u8bf4\u660e\u56e2\u961f\u5bf9\u9ad8\u4e25\u91cd\u5ea6\u95ee\u9898\u5177\u5907\u7a33\u5b9a\u7684\u6536\u655b\u80fd\u529b\uff0c\u8fd9\u662f\u5f53\u524d\u6700\u6709\u4ef7\u503c\u7684\u6b63\u5411\u8868\u73b0\u3002`
    : highShare <= 8
      ? `\u9ad8\u4e25\u91cd\u5ea6\u5e76\u672a\u5f62\u6210\u4e3b\u5bfc\u538b\u529b\uff0c\u8fd9\u8868\u660e\u7248\u672c\u5e95\u5c42\u7a33\u5b9a\u6027\u76ee\u524d\u4ecd\u6709\u4e00\u5b9a\u4fdd\u969c\u3002`
      : lowSeverityItem
        ? `${describeItem(lowSeverityItem)}\u8bf4\u660e\u5927\u91cf\u95ee\u9898\u4ecd\u96c6\u4e2d\u5728\u4f4e\u5371\u9762\uff0c\u5bf9\u53d1\u5e03\u51b3\u7b56\u7684\u76f4\u63a5\u538b\u529b\u76f8\u5bf9\u6709\u9650\u3002`
        : `\u6b63\u5411\u4fe1\u53f7\u8fd8\u9700\u540e\u7eed\u901a\u8fc7\u9ad8\u4e25\u91cd\u5ea6\u7f3a\u9677\u7684\u6301\u7eed\u6e05\u96f6\u6765\u8fdb\u4e00\u6b65\u5efa\u7acb\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildRootCauseNarrative = summary => {
  const primaryItems = getPrimaryItems(summary)
  const secondaryItems = getSecondaryItems(summary)
  const topCause = primaryItems[0] || secondaryItems[0] || null
  const ownerItem = findTopMatch(getAllSearchItems(summary), PEOPLE_ROLE_KEYWORDS)
  const riskCell = summary.topCell
  const top3Share = sumShares(primaryItems, 3)

  const problem = riskCell
    ? `\u300a${summary.title}\u300b\u4e2d${describeCell(riskCell)}\u662f\u5f53\u524d\u6700\u4e3b\u8981\u7684\u6839\u56e0\u4e0e\u8d23\u4efb\u4ea4\u6c47\u70b9\uff0c\u8bf4\u660e\u95ee\u9898\u5df2\u7ecf\u4ece\u73b0\u8c61\u5c42\u8fdb\u5165\u5230\u6d41\u7a0b\u8d23\u4efb\u5c42\u3002`
    : topCause
      ? `\u300a${summary.title}\u300b\u5df2\u663e\u793a\u51fa${describeItem(topCause)}\u662f\u4e3b\u5bfc\u6839\u56e0\uff0c\u8fd9\u610f\u5473\u7740\u5f53\u524d\u95ee\u9898\u5e76\u975e\u9694\u79bb\u4e8b\u4ef6\uff0c\u800c\u662f\u5728\u540c\u7c7b\u8d28\u91cf\u94fe\u8def\u4e0a\u91cd\u590d\u51fa\u73b0\u3002`
      : `\u300a${summary.title}\u300b\u7684\u6839\u56e0\u4fe1\u53f7\u5df2\u51fa\u73b0\u96c6\u4e2d\u8d8b\u52bf\uff0c\u9700\u5c3d\u5feb\u628a\u73b0\u8c61\u5f80\u4e0a\u6eaf\u6e90\u5230\u6d41\u7a0b\u548c\u8d23\u4efb\u73af\u8282\u3002`

  const risk = topCause && getMetricShare(topCause) >= 30
    ? `\u5355\u4e00\u6839\u56e0\u5360\u6bd4\u5df2\u8fbe${formatPercent(getMetricShare(topCause))}\uff0c\u8fd9\u8bf4\u660e\u98ce\u9669\u5e76\u4e0d\u662f\u70b9\u72b6\u66b4\u9732\uff0c\u800c\u662f\u67d0\u6761\u4e0a\u6e38\u8fc7\u7a0b\u5df2\u7ecf\u5f62\u6210\u7cfb\u7edf\u6027\u6f0f\u635f\u3002`
    : riskCell && riskCell.share >= 12
      ? `\u6700\u5927\u6839\u56e0\u4ea4\u53c9\u70b9\u5360\u5168\u56fe${formatPercent(riskCell.share)}\uff0c\u5982\u679c\u4e0d\u5728\u8d23\u4efb\u4fa7\u540c\u6b65\u6539\u9032\uff0c\u540e\u7eed\u5f88\u5bb9\u6613\u51fa\u73b0\u540c\u7c7b\u95ee\u9898\u7684\u6279\u91cf\u56de\u5f52\u3002`
      : `\u6839\u56e0\u9762\u98ce\u9669\u76ee\u524d\u4ecd\u5177\u6709\u6269\u6563\u53ef\u80fd\uff0c\u5efa\u8bae\u4e0d\u8981\u505c\u7559\u5728\u5355\u6761\u95ee\u9898\u4fee\u590d\uff0c\u800c\u662f\u8981\u540c\u6b65\u68c0\u67e5\u4e0a\u6e38\u8bc4\u5ba1\u3001\u8bbe\u8ba1\u548c\u81ea\u6d4b\u8d28\u91cf\u95ed\u73af\u3002`

  const overall = top3Share >= 65
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u6839\u56e0\u5df2\u5728\u5934\u90e8\u51e0\u6761\u94fe\u8def\u4e0a\u9ad8\u5ea6\u96c6\u4e2d\uff0c\u8fd9\u5bf9\u7ba1\u7406\u5c42\u662f\u6e05\u6670\u7684\u9884\u8b66\uff1a\u95ee\u9898\u7684\u672c\u8d28\u66f4\u63a5\u8fd1\u8fc7\u7a0b\u8d28\u91cf\uff0c\u800c\u4e0d\u662f\u4e2a\u4eba\u5931\u8bef\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u6839\u56e0\u5c1a\u672a\u6536\u655b\u5230\u5355\u4e00\u94fe\u8def\uff0c\u8fd9\u8bf4\u660e\u5f53\u524d\u95ee\u9898\u5305\u542b\u591a\u6e90\u89e6\u53d1\u56e0\u7d20\uff0c\u4f46\u4e5f\u610f\u5473\u7740\u6cbb\u7406\u65f6\u8981\u6709\u660e\u786e\u4e3b\u6b21\u3002`

  const causeFocus = primaryItems.slice(0, 2)
  const attention = ownerItem
    ? `\u5efa\u8bae\u4f18\u5148\u8ddf\u8fdb${describeItems(causeFocus)}\uff0c\u5e76\u7ed3\u5408${describeItem(ownerItem)}\u6240\u4ee3\u8868\u7684\u8d23\u4efb\u65b9\u5411\u505a\u4e13\u9879\u6539\u9032\u548c\u590d\u76d8\u3002`
    : causeFocus.length
      ? `\u5efa\u8bae\u4f18\u5148\u56f4\u7ed5${describeItems(causeFocus)}\u505a\u4e13\u9879\u6cbb\u7406\uff0c\u5148\u628a\u6700\u4e3b\u8981\u7684\u4e0a\u6e38\u6f0f\u6d1e\u5835\u4f4f\u3002`
      : `\u5efa\u8bae\u4e0b\u4e00\u6b65\u7ee7\u7eed\u901a\u8fc7\u5206\u5c42\u5206\u7c7b\u590d\u76d8\uff0c\u5c06\u6839\u56e0\u4ece\u73b0\u8c61\u5f52\u56e0\u5f80\u4e0a\u6eaf\u6e90\u5230\u6d41\u7a0b\u7f3a\u53e3\u3002`

  const excellent = topCause && getMetricShare(topCause) < 20
    ? `\u76ee\u524d\u6839\u56e0\u672a\u5728\u5355\u4e00\u94fe\u8def\u4e0a\u5f62\u6210\u538b\u5012\u6027\u96c6\u4e2d\uff0c\u8fd9\u8bf4\u660e\u8fd8\u6ca1\u6709\u51fa\u73b0\u5355\u70b9\u6d41\u7a0b\u5931\u63a7\u7684\u60c5\u51b5\u3002`
    : ownerItem && getMetricShare(ownerItem) < 25
      ? `${describeItem(ownerItem)}\u5e76\u672a\u5f62\u6210\u8d23\u4efb\u8fc7\u5ea6\u96c6\u4e2d\uff0c\u8bf4\u660e\u95ee\u9898\u8fd8\u6709\u8fdb\u884c\u7ec4\u7ec7\u6027\u5206\u6d41\u548c\u6cbb\u7406\u7684\u7a7a\u95f4\u3002`
      : `\u5f53\u524d\u66f4\u5927\u7684\u673a\u4f1a\u5728\u4e8e\uff0c\u6839\u56e0\u5df2\u80fd\u901a\u8fc7\u56fe\u8868\u88ab\u6e05\u6670\u6307\u5411\uff0c\u8fd9\u4e3a\u540e\u7eed\u4e13\u9879\u6539\u9032\u63d0\u4f9b\u4e86\u660e\u786e\u843d\u70b9\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildModuleNarrative = summary => {
  const primaryItems = getPrimaryItems(summary)
  const topModule = primaryItems[0] || null
  const riskCell = summary.topNegativeCell || summary.topCell
  const top3Share = sumShares(primaryItems, 3)

  const problem = riskCell
    ? `\u300a${summary.title}\u300b\u4e2d${describeCell(riskCell)}\u662f\u6700\u660e\u663e\u7684\u6a21\u5757\u98ce\u9669\u70ed\u70b9\uff0c\u8bf4\u660e\u5f53\u524d\u95ee\u9898\u5df2\u5728\u5177\u4f53\u6a21\u5757\u94fe\u8def\u4e0a\u51fa\u73b0\u540c\u5411\u53e0\u52a0\u3002`
    : topModule
      ? `\u300a${summary.title}\u300b\u663e\u793a${describeItem(topModule)}\u662f\u5f53\u524d\u627f\u538b\u6700\u660e\u663e\u7684\u6a21\u5757\uff0c\u9700\u89c6\u4e3a\u8fd9\u4e00\u7248\u672c\u7684\u91cd\u70b9\u8d28\u91cf\u70ed\u533a\u3002`
      : `\u300a${summary.title}\u300b\u5df2\u51fa\u73b0\u6a21\u5757\u95f4\u660e\u663e\u5206\u5316\uff0c\u5f53\u524d\u5e94\u4f18\u5148\u8bc6\u522b\u51fa\u5934\u90e8\u98ce\u9669\u6a21\u5757\u3002`

  const risk = topModule && getMetricShare(topModule) >= 25
    ? `\u5934\u90e8\u6a21\u5757\u5360\u6bd4\u5df2\u8fbe${formatPercent(getMetricShare(topModule))}\uff0c\u98ce\u9669\u96c6\u4e2d\u5ea6\u504f\u9ad8\uff0c\u8fd9\u610f\u5473\u7740\u53ea\u8981\u8be5\u6a21\u5757\u518d\u51fa\u73b0\u6ce2\u52a8\uff0c\u6574\u4e2a\u7248\u672c\u8d28\u91cf\u4f53\u611f\u5c31\u4f1a\u88ab\u660e\u663e\u62c9\u4f4e\u3002`
    : top3Share >= 60
      ? `\u524d\u4e09\u4e2a\u6a21\u5757\u5df2\u805a\u96c6${formatPercent(top3Share)}\u7684\u538b\u529b\uff0c\u8fd9\u8bf4\u660e\u95ee\u9898\u5df2\u4ece\u96f6\u6563\u5206\u5e03\u8f6c\u4e3a\u5c40\u90e8\u70ed\u533a\u6536\u7f29\u3002`
      : `\u6a21\u5757\u7ef4\u5ea6\u6682\u672a\u51fa\u73b0\u5168\u9762\u5931\u63a7\uff0c\u4f46\u5934\u90e8\u6a21\u5757\u7684\u65b0\u589e\u6ce2\u52a8\u4ecd\u4f1a\u5bf9\u8fdb\u5ea6\u548c\u7f3a\u9677\u66f2\u7ebf\u5f62\u6210\u660e\u663e\u653e\u5927\u6548\u5e94\u3002`

  const overall = top3Share >= 65
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u7248\u672c\u98ce\u9669\u73b0\u5728\u5df2\u7ecf\u4e0d\u662f\u201c\u5e73\u5747\u5730\u6709\u70b9\u95ee\u9898\u201d\uff0c\u800c\u662f\u201c\u5c11\u6570\u6a21\u5757\u51b3\u5b9a\u6574\u4f53\u8d28\u91cf\u4e0a\u9650\u201d\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u6a21\u5757\u95f4\u8fd8\u4fdd\u6301\u4e00\u5b9a\u5747\u8861\uff0c\u8bf4\u660e\u7248\u672c\u5e76\u672a\u5b8c\u5168\u88ab\u5355\u4e00\u6a21\u5757\u7ed1\u67b6\uff0c\u4f46\u5934\u90e8\u70ed\u533a\u4ecd\u9700\u91cd\u5175\u76ef\u9632\u3002`

  const attention = primaryItems.length
    ? `\u5efa\u8bae\u4e0b\u4e00\u8f6e\u91cd\u70b9\u8ddf\u8fdb${describeItems(primaryItems, 3)}\uff0c\u6309\u6a21\u5757\u5212\u5206\u7f3a\u9677\u3001\u7528\u4f8b\u3001\u6d4b\u8bd5\u70b9\u548c\u4e0a\u7ebf\u95ee\u9898\u7684\u8054\u52a8\u72b6\u6001\u3002`
    : `\u5efa\u8bae\u5c06\u76d1\u63a7\u89d2\u5ea6\u805a\u7126\u5728\u6a21\u5757\u7ef4\u5ea6\uff0c\u907f\u514d\u4ec5\u6309\u5355\u4e2a\u7f3a\u9677\u6216\u5355\u4e2a\u7528\u4f8b\u6765\u7406\u89e3\u98ce\u9669\u3002`

  const excellent = topModule && getMetricShare(topModule) < 18
    ? `\u76ee\u524d\u6a21\u5757\u98ce\u9669\u672a\u88ab\u5355\u4e00\u70ed\u533a\u5b8c\u5168\u4e3b\u5bfc\uff0c\u8fd9\u8868\u660e\u6574\u4f53\u6a21\u5757\u57fa\u7ebf\u8fd8\u6709\u4e00\u5b9a\u7a33\u5b9a\u6027\u3002`
    : riskCell && riskCell.share < 10
      ? `\u6a21\u5757\u4ea4\u53c9\u5361\u70b9\u7684\u5355\u70b9\u5360\u6bd4\u4e0d\u9ad8\uff0c\u8bf4\u660e\u5c1a\u672a\u51fa\u73b0\u67d0\u4e2a\u6a21\u5757\u5bf9\u6574\u4f53\u8d28\u91cf\u7684\u7edd\u5bf9\u62d6\u7d2f\u3002`
      : `\u6a21\u5757\u7ef4\u5ea6\u7684\u597d\u5904\u662f\u98ce\u9669\u843d\u70b9\u975e\u5e38\u6e05\u6670\uff0c\u8fd9\u4e3a\u540e\u7eed\u5b9a\u5411\u589e\u8865\u6d4b\u8bd5\u8d44\u6ea2\u548c\u5b9a\u5411\u6539\u9032\u63d0\u4f9b\u4e86\u57fa\u7840\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildPeopleNarrative = summary => {
  const primaryItems = getPrimaryItems(summary)
  const topOwner = primaryItems[0] || summary.topColumn || null
  const supportOwner = primaryItems[1] || null
  const riskCell = summary.topCell
  const topShare = getMetricShare(topOwner)

  const problem = riskCell
    ? `\u300a${summary.title}\u300b\u4e2d${describeCell(riskCell)}\u662f\u5f53\u524d\u6700\u7a81\u51fa\u7684\u4eba\u5458/\u8d23\u4efb\u7ec4\u5408\u538b\u529b\u70b9\uff0c\u8bf4\u660e\u98ce\u9669\u5df2\u7ecf\u4ece\u4e2a\u4f53\u627f\u8f7d\u5ef6\u4f38\u5230\u5177\u4f53\u5de5\u4f5c\u9762\u3002`
    : topOwner
      ? `\u300a${summary.title}\u300b\u4e2d${describeItem(topOwner)}\u662f\u6700\u4e3b\u8981\u7684\u627f\u538b\u4e3b\u4f53\uff0c\u8fd9\u4e2a\u7ed3\u679c\u9700\u653e\u5230\u5bb9\u91cf\u3001\u8d23\u4efb\u5206\u914d\u548c\u5361\u70b9\u6cbb\u7406\u4e09\u4e2a\u7ef4\u5ea6\u7efc\u5408\u5224\u65ad\u3002`
      : `\u300a${summary.title}\u300b\u663e\u793a\u51fa\u4eba\u5458/\u8d23\u4efb\u9762\u5df2\u51fa\u73b0\u660e\u663e\u5206\u5316\uff0c\u5f53\u524d\u9700\u5148\u627e\u51fa\u5934\u90e8\u627f\u538b\u4e3b\u4f53\u3002`

  const risk = topShare >= 35
    ? `\u5934\u90e8\u4e3b\u4f53\u5360\u6bd4${formatPercent(topShare)}\uff0c\u8fd9\u79cd\u96c6\u4e2d\u5ea6\u610f\u5473\u7740\u4e00\u65e6\u8be5\u4eba\u5458/\u5c0f\u7ec4\u51fa\u73b0\u6392\u671f\u6324\u538b\u6216\u8d28\u91cf\u6ce2\u52a8\uff0c\u6574\u4e2a\u7248\u672c\u4f1a\u88ab\u540c\u6b65\u62d6\u6162\u3002`
    : riskCell && riskCell.share >= 12
      ? `\u4eba\u5458\u4e0e\u5177\u4f53\u5de5\u4f5c\u9762\u7684\u6700\u5927\u4ea4\u53c9\u70b9\u5360\u6bd4${formatPercent(riskCell.share)}\uff0c\u9700\u89c6\u4e3a\u5f53\u524d\u7684\u5bb9\u91cf\u74f6\u9888\u4f4d\u7f6e\u3002`
      : `\u4eba\u5458/\u5c0f\u7ec4\u5206\u5e03\u6682\u672a\u5931\u8861\uff0c\u4f46${topOwner ? topOwner.label : '\u5934\u90e8\u4e3b\u4f53'}\u4ecd\u662f\u6700\u9700\u8981\u8ddf\u8fdb\u7684\u5173\u952e\u627f\u538b\u70b9\u3002`

  const overall = topShare <= 25
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u7ba1\u7406\u770b\uff0c\u4eba\u5458/\u5c0f\u7ec4\u627f\u8f7d\u8fd8\u7b97\u5747\u8861\uff0c\u6574\u4f53\u5bb9\u91cf\u98ce\u9669\u53ef\u63a7\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u7ba1\u7406\u770b\uff0c\u5f53\u524d\u66f4\u63a5\u8fd1\u201c\u5934\u90e8\u4e3b\u4f53\u51b3\u5b9a\u8282\u594f\u201d\u7684\u72b6\u6001\uff0c\u9700\u8981\u540c\u65f6\u505a\u597d\u5bb9\u91cf\u5e73\u8861\u548c\u8d28\u91cf\u652f\u63f4\u3002`

  const attentionTargets = [topOwner, supportOwner].filter(Boolean)
  const attention = attentionTargets.length
    ? `\u5efa\u8bae\u91cd\u70b9\u76ef\u7d27${describeItems(attentionTargets)}\uff0c\u5e76\u7ed3\u5408\u5176\u5bf9\u5e94\u7684\u6a21\u5757\u3001\u7f3a\u9677\u548c\u72b6\u6001\u538b\u529b\u4e00\u8d77\u8bc4\u4f30\u662f\u5426\u9700\u8981\u518d\u5206\u914d\u8d44\u6e90\u3002`
    : `\u5efa\u8bae\u540e\u7eed\u7ee7\u7eed\u4ece\u4eba\u5458\u627f\u8f7d\u89d2\u5ea6\u76ef\u7d27\u5934\u90e8\u4e3b\u4f53\u53d8\u5316\uff0c\u907f\u514d\u5c40\u90e8\u51fa\u73b0\u8d85\u8d1f\u8377\u3002`

  const excellent = topShare <= 20
    ? `\u76ee\u524d\u672a\u51fa\u73b0\u5355\u4e00\u4eba\u5458/\u8d23\u4efb\u7ec4\u8fc7\u5ea6\u62c9\u9ad8\u5168\u5c40\u6ce2\u52a8\u7684\u60c5\u51b5\uff0c\u8fd9\u8bf4\u660e\u56e2\u961f\u7684\u8d44\u6e90\u5e03\u5c40\u8fd8\u4fdd\u6301\u4e00\u5b9a\u97e7\u6027\u3002`
    : supportOwner && getMetricShare(supportOwner) >= 15
      ? `${describeItem(supportOwner)}\u8d77\u5230\u4e86\u4e00\u5b9a\u7684\u5206\u62c5\u4f5c\u7528\uff0c\u8fd9\u8868\u660e\u5f53\u524d\u8fd8\u5177\u5907\u901a\u8fc7\u534f\u540c\u6765\u7f13\u51b2\u5355\u70b9\u538b\u529b\u7684\u7a7a\u95f4\u3002`
      : `\u5f53\u524d\u6700\u5927\u7684\u4f18\u52bf\u662f\u98ce\u9669\u6240\u5c5e\u4e3b\u4f53\u5df2\u88ab\u6e05\u6670\u663e\u793a\uff0c\u4fbf\u4e8e\u76f4\u63a5\u505a\u4eba\u3001\u6a21\u5757\u3001\u72b6\u6001\u4e09\u7ef4\u8054\u52a8\u7ba1\u7406\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildWorkloadNarrative = summary => {
  const primaryItems = getPrimaryItems(summary)
  const topItem = primaryItems[0] || null
  const secondItem = primaryItems[1] || null
  const topShare = getMetricShare(topItem)
  const top3Share = sumShares(primaryItems, 3)

  const problem = topItem
    ? `\u300a${summary.title}\u300b\u663e\u793a${describeItem(topItem)}\u662f\u5f53\u524d\u5de5\u65f6/\u5de5\u4f5c\u91cf\u6295\u5165\u6700\u91cd\u7684\u627f\u8f7d\u4e3b\u4f53\uff0c\u8fd9\u4e2a\u4f4d\u7f6e\u9700\u8981\u4f5c\u4e3a\u8d44\u6e90\u8c03\u6574\u7684\u9996\u8981\u89c2\u5bdf\u70b9\u3002`
    : `\u300a${summary.title}\u300b\u5df2\u53cd\u6620\u51fa\u5de5\u65f6/\u5de5\u4f5c\u91cf\u5206\u5e03\u5b58\u5728\u660e\u663e\u504f\u659c\uff0c\u5f53\u524d\u9700\u5148\u627e\u51fa\u6700\u5927\u627f\u8f7d\u4e3b\u4f53\u3002`

  const risk = topShare >= 35
    ? `\u5934\u90e8\u5de5\u65f6\u5360\u6bd4\u5df2\u8fbe${formatPercent(topShare)}\uff0c\u8fd9\u79cd\u8fc7\u5ea6\u96c6\u4e2d\u5f88\u5bb9\u6613\u5f15\u53d1\u8bc4\u4f30\u4e0d\u51c6\u3001\u6267\u884c\u635f\u8017\u548c\u56de\u5f52\u4e0d\u8db3\u4e09\u91cd\u98ce\u9669\u3002`
    : top3Share >= 65
      ? `\u524d\u4e09\u4e2a\u627f\u8f7d\u4e3b\u4f53\u5df2\u96c6\u4e2d${formatPercent(top3Share)}\u7684\u5de5\u65f6\uff0c\u8fd9\u8bf4\u660e\u7248\u672c\u4ea4\u4ed8\u8282\u594f\u5f88\u4f9d\u8d56\u5c11\u6570\u5173\u952e\u70b9\u3002`
      : `\u5de5\u65f6\u7ed3\u6784\u6682\u672a\u5931\u63a7\uff0c\u4f46\u5934\u90e8\u4e3b\u4f53\u662f\u5426\u4f1a\u7ee7\u7eed\u62ac\u5347\uff0c\u4ecd\u51b3\u5b9a\u540e\u7eed\u5bb9\u91cf\u98ce\u9669\u3002`

  const overall = topShare <= 25
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u7ba1\u7406\u770b\uff0c\u5de5\u65f6/\u5de5\u4f5c\u91cf\u5206\u5e03\u76f8\u5bf9\u5747\u8861\uff0c\u5f53\u524d\u8d44\u6e90\u914d\u7f6e\u8fd8\u5177\u5907\u8f83\u597d\u7684\u6297\u6ce2\u52a8\u80fd\u529b\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u7ba1\u7406\u770b\uff0c\u5f53\u524d\u5de5\u65f6\u66f4\u50cf\u662f\u201c\u5c11\u6570\u70b9\u4f4d\u652f\u6491\u5168\u5c40\u201d\uff0c\u5f53\u51fa\u73b0\u8fdb\u5ea6\u5ef6\u8fdf\u6216\u8d28\u91cf\u6ce2\u52a8\u65f6\uff0c\u5f88\u5bb9\u6613\u8fde\u5e26\u5f71\u54cd\u8fd4\u5de5\u4e0e\u53d1\u5e03\u3002`

  const attention = [topItem, secondItem].filter(Boolean).length
    ? `\u5efa\u8bae\u91cd\u70b9\u8ddf\u8fdb${describeItems([topItem, secondItem].filter(Boolean))}\uff0c\u68c0\u67e5\u662f\u5426\u5df2\u7ecf\u51fa\u73b0\u8bc4\u4f30\u5dee\u3001\u6392\u671f\u6324\u538b\u6216\u8de8\u89d2\u8272\u534f\u4f5c\u8017\u635f\u8fc7\u5927\u7684\u95ee\u9898\u3002`
    : `\u5efa\u8bae\u540e\u7eed\u6301\u7eed\u76ef\u7d27\u5de5\u65f6\u589e\u957f\u6700\u5feb\u7684\u4e3b\u4f53\uff0c\u53ca\u65f6\u505a\u8d44\u6e90\u5e73\u8861\u3002`

  const excellent = topShare <= 20
    ? `\u76ee\u524d\u5de5\u65f6/\u5de5\u4f5c\u91cf\u672a\u9ad8\u5ea6\u96c6\u4e2d\u5230\u5355\u70b9\uff0c\u8fd9\u5bf9\u7248\u672c\u8282\u594f\u7684\u53ef\u6301\u7eed\u6027\u662f\u4e00\u4e2a\u660e\u663e\u5229\u597d\u3002`
    : secondItem && getMetricShare(secondItem) >= 18
      ? `${describeItem(secondItem)}\u8bf4\u660e\u5f53\u524d\u4ecd\u6709\u7b2c\u4e8c\u627f\u8f7d\u70b9\u53ef\u4ee5\u4e0e\u5934\u90e8\u70ed\u70b9\u5171\u540c\u5206\u62c5\u538b\u529b\u3002`
      : `\u6700\u5927\u7684\u6b63\u5411\u4fe1\u53f7\u5728\u4e8e\uff0c\u5de5\u65f6\u96c6\u4e2d\u70b9\u5df2\u80fd\u88ab\u6e05\u6670\u8bc6\u522b\uff0c\u4fbf\u4e8e\u540e\u7eed\u5b9a\u5411\u62c6\u89e3\u548c\u518d\u5206\u914d\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildCoverageNarrative = summary => {
  const gapItem = findTopMatch(getAllSearchItems(summary), COVERAGE_GAP_KEYWORDS)
  const linkedItem = findTopMatch(getAllSearchItems(summary), ['\u5df2\u5173\u8054', '\u5df2\u8986\u76d6', '\u5b8c\u6574', '\u9f50\u5168'])
  const weakestColumn = summary.coverageMode ? summary.weakestColumn : null
  const weakestRow = summary.coverageMode ? summary.weakestRow : null

  const problem = weakestColumn
    ? `\u300a${summary.title}\u300b\u663e\u793a${describeItem(weakestColumn)}\u662f\u5f53\u524d\u6700\u660e\u663e\u7684\u8986\u76d6\u77ed\u677f\uff0c\u800c${weakestRow ? describeItem(weakestRow) : '\u90e8\u5206\u5bf9\u8c61'}\u53c8\u628a\u8fd9\u4e2a\u77ed\u677f\u8fdb\u4e00\u6b65\u653e\u5927\u3002`
    : gapItem
      ? `\u300a${summary.title}\u300b\u4e2d${describeItem(gapItem)}\u662f\u5f53\u524d\u6700\u660e\u786e\u7684\u53ef\u8ffd\u6eaf/\u53ef\u8986\u76d6\u7f3a\u53e3\uff0c\u8fd9\u4f1a\u76f4\u63a5\u5f71\u54cd\u540e\u7eed\u5206\u6790\u7ed3\u8bba\u7684\u5b8c\u6574\u6027\u3002`
      : `\u300a${summary.title}\u300b\u5df2\u53cd\u6620\u51fa\u8986\u76d6\u9762\u5b58\u5728\u4e0d\u5747\u8861\uff0c\u9700\u5148\u627e\u51fa\u89c6\u56fe\u4e2d\u7684\u6700\u77ed\u677f\u5b57\u6bb5\u6216\u6a21\u5757\u3002`

  const risk = summary.coverageMode && summary.averageCoverage !== null
    ? summary.averageCoverage < 75
      ? `\u5e73\u5747\u8986\u76d6\u7387\u4ec5${formatPercent(summary.averageCoverage)}\uff0c\u8fd9\u610f\u5473\u7740\u5f53\u524d\u8d28\u91cf\u5206\u6790\u4ecd\u6709\u8f83\u5927\u7684\u4fe1\u606f\u76f2\u533a\u3002`
      : `\u8986\u76d6\u9762\u603b\u4f53\u5c1a\u53ef\uff0c\u4f46\u77ed\u677f\u5b57\u6bb5\u4ecd\u4f1a\u5bf9\u7528\u4f8b\u8bbe\u8ba1\u3001\u7f3a\u9677\u5f52\u56e0\u548c\u4e0a\u7ebf\u5224\u65ad\u9020\u6210\u504f\u5dee\u3002`
    : gapItem && getMetricShare(gapItem) >= 20
      ? `\u7f3a\u53e3\u7c7b\u4fe1\u53f7\u5360\u6bd4\u5df2\u8fbe${formatPercent(getMetricShare(gapItem))}\uff0c\u5f53\u524d\u6700\u5927\u98ce\u9669\u5e76\u4e0d\u662f\u51fa\u73b0\u4e86\u591a\u5c11\u95ee\u9898\uff0c\u800c\u662f\u6709\u591a\u5c11\u95ee\u9898\u53ef\u80fd\u8fd8\u6ca1\u88ab\u770b\u89c1\u3002`
      : `\u8986\u76d6/\u5173\u8054\u9762\u76ee\u524d\u4ecd\u9700\u8ffd\u8e2a\uff0c\u5982\u679c\u7f3a\u53e3\u4e0d\u5c3d\u5feb\u8865\u9f50\uff0c\u540e\u7eed\u56fe\u8868\u7684\u5206\u6790\u5206\u91cf\u4f1a\u6301\u7eed\u6253\u6298\u3002`

  const overall = summary.coverageMode && summary.averageCoverage !== null
    ? summary.averageCoverage >= 85
      ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u6570\u636e\u6c89\u6dc0\u548c\u53ef\u8ffd\u6eaf\u6027\u57fa\u672c\u5230\u4f4d\uff0c\u5df2\u5177\u5907\u652f\u6491\u540e\u7eed\u6df1\u5165\u5206\u6790\u7684\u57fa\u7840\u3002`
      : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u66f4\u9700\u8981\u5148\u8865\u9f50\u8986\u76d6\u53ca\u5173\u8054\u95ed\u73af\uff0c\u518d\u8c08\u66f4\u7ec6\u5206\u7684\u4eba\u6548\u3001\u6a21\u5757\u6216\u8d23\u4efb\u5bf9\u6bd4\u3002`
    : gapItem
      ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u5b58\u5728\u660e\u663e\u7684\u8ffd\u8e2a\u94fe\u8def\u7f3a\u53e3\uff0c\u8fd9\u4f1a\u9650\u5236\u7248\u672c\u5bf9\u98ce\u9669\u7684\u53ef\u89c6\u5316\u548c\u53ef\u8ffd\u8d23\u80fd\u529b\u3002`
      : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u8986\u76d6/\u5173\u8054\u9762\u57fa\u672c\u53ef\u7528\uff0c\u4f46\u4ecd\u9700\u7ee7\u7eed\u538b\u7f29\u6570\u636e\u76f2\u533a\u3002`

  const attention = weakestColumn
    ? `\u5efa\u8bae\u4f18\u5148\u8865\u9f50${describeItem(weakestColumn)}${weakestRow ? `\uff0c\u5e76\u540c\u6b65\u68c0\u67e5${describeItem(weakestRow)}` : ''}\u5bf9\u5e94\u7684\u4fe1\u606f\u6c89\u6dc0\u8d28\u91cf\u3002`
    : gapItem
      ? `\u5efa\u8bae\u5148\u76ef\u7d27${describeItem(gapItem)}\uff0c\u6838\u5b9e\u7f3a\u53e3\u6765\u81ea\u5bf9\u8c61\u672a\u5efa\u7acb\uff0c\u8fd8\u662f\u6765\u81ea\u6570\u636e\u672a\u56de\u586b\u6216\u6807\u8bc6\u4e0d\u89c4\u8303\u3002`
      : `\u5efa\u8bae\u6301\u7eed\u8ddf\u8fdb\u8986\u76d6\u7387\u6700\u4f4e\u7684\u90a3\u4e00\u6279\u5bf9\u8c61\uff0c\u786e\u4fdd\u5206\u6790\u94fe\u8def\u4e0d\u4f1a\u518d\u65b0\u589e\u76f2\u533a\u3002`

  const excellent = summary.coverageMode && summary.averageCoverage !== null && summary.averageCoverage >= 90
    ? `\u5f53\u524d\u5e73\u5747\u8986\u76d6\u7387\u5df2\u8fbe${formatPercent(summary.averageCoverage)}\uff0c\u8fd9\u8bf4\u660e\u8be5\u7248\u672c\u7684\u6d4b\u8bd5\u8d44\u4ea7\u6c89\u6dc0\u548c\u53ef\u8ffd\u6eaf\u57fa\u7ebf\u8868\u73b0\u8f83\u597d\u3002`
    : linkedItem
      ? `${describeItem(linkedItem)}\u662f\u672c\u56fe\u91cc\u6700\u7a81\u51fa\u7684\u6b63\u5411\u4fe1\u53f7\uff0c\u8bf4\u660e\u90e8\u5206\u94fe\u8def\u5df2\u7ecf\u5177\u5907\u8f83\u597d\u7684\u53ef\u8ffd\u6eaf\u6027\u3002`
      : `\u5f53\u524d\u6700\u5927\u7684\u4f18\u52bf\u662f\u77ed\u677f\u4f4d\u7f6e\u5df2\u7ecf\u6bd4\u8f83\u6e05\u6670\uff0c\u53ef\u4ee5\u901a\u8fc7\u5b9a\u5411\u8865\u6570\u548c\u5b9a\u5411\u6cbb\u7406\u5feb\u901f\u89c1\u6548\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildMatrixNarrative = summary => {
  const topCell = summary.topNegativeCell || summary.topCell
  const topRow = summary.topRow
  const topColumn = summary.topColumn
  const top3RowShare = sumShares(summary.rowItems || [], 3)

  const problem = topCell
    ? `\u300a${summary.title}\u300b\u4e2d${describeCell(topCell)}\u662f\u5f53\u524d\u6700\u7a81\u51fa\u7684\u7ec4\u5408\u98ce\u9669\u70b9\uff0c\u8bf4\u660e\u95ee\u9898\u5df2\u4ece\u5355\u7ef4\u6307\u6807\u6f14\u53d8\u4e3a\u4ea4\u53c9\u7ef4\u5ea6\u7684\u53e0\u52a0\u538b\u529b\u3002`
    : `\u300a${summary.title}\u300b\u5df2\u51fa\u73b0\u660e\u663e\u7684\u4ea4\u53c9\u5206\u5e03\u503e\u659c\uff0c\u5f53\u524d\u9700\u5148\u805a\u7126\u6700\u5927\u503c\u6240\u5728\u7684\u7ec4\u5408\u533a\u57df\u3002`

  const risk = topCell && topCell.share >= 15
    ? `\u5355\u4e00\u4ea4\u53c9\u5355\u5143\u683c\u5360\u6bd4\u5df2\u8fbe${formatPercent(topCell.share)}\uff0c\u8fd9\u610f\u5473\u7740\u98ce\u9669\u4e0d\u662f\u5747\u5300\u5206\u6563\u7684\uff0c\u800c\u662f\u5728\u7279\u5b9a\u7ec4\u5408\u4e0a\u5feb\u901f\u5806\u79ef\u3002`
    : top3RowShare >= 60
      ? `\u5934\u90e8\u7ec4\u5408\u6240\u5c5e\u7684\u884c\u7ef4\u5ea6\u5df2\u805a\u96c6${formatPercent(top3RowShare)}\u7684\u538b\u529b\uff0c\u5982\u679c\u4e0d\u5c3d\u5feb\u505a\u4e13\u9879\u6253\u6563\uff0c\u540e\u7eed\u4f1a\u6301\u7eed\u63a8\u9ad8\u53d1\u5e03\u98ce\u9669\u3002`
      : `\u4ea4\u53c9\u7ef4\u5ea6\u76ee\u524d\u8fd8\u672a\u51fa\u73b0\u5168\u9762\u5931\u63a7\uff0c\u4f46\u5934\u90e8\u884c\u5217\u7684\u7ec4\u5408\u6ce2\u52a8\u4ecd\u662f\u6700\u9700\u8981\u76ef\u9632\u7684\u5bf9\u8c61\u3002`

  const overall = topCell && topCell.share >= 12
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u4e0d\u662f\u5355\u4e00\u6307\u6807\u5f31\uff0c\u800c\u662f\u4e24\u4e2a\u6216\u591a\u4e2a\u7ef4\u5ea6\u5728\u540c\u4e00\u70b9\u4f4d\u4e0a\u53d1\u751f\u4e86\u8016\u5408\uff0c\u8fd9\u7c7b\u98ce\u9669\u66f4\u503c\u5f97\u7ba1\u7406\u5c42\u91cd\u89c6\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u7ef4\u5ea6\u4e4b\u95f4\u8fd8\u6ca1\u6709\u5f62\u6210\u7edd\u5bf9\u7684\u5355\u70b9\u5931\u63a7\uff0c\u4f46\u5df2\u7ecf\u51fa\u73b0\u5c40\u90e8\u7ec4\u5408\u98ce\u9669\u96c6\u4e2d\u7684\u96cf\u5f62\u3002`

  const attention = topRow && topColumn
    ? `\u5efa\u8bae\u4f18\u5148\u540c\u65f6\u8ddf\u8fdb${describeItem(topRow)}\u548c${describeItem(topColumn)}\u8fd9\u4e24\u6761\u7ebf\uff0c\u518d\u56f4\u7ed5\u5b83\u4eec\u7684\u4ea4\u53c9\u70b9\u505a\u4e13\u9879\u6536\u655b\u3002`
    : `\u5efa\u8bae\u6309\u884c\u3001\u5217\u4e24\u4e2a\u7ef4\u5ea6\u540c\u65f6\u8ffd\u8e2a\u5934\u90e8\u5bf9\u8c61\uff0c\u907f\u514d\u4ec5\u770b\u5355\u8fb9\u5206\u5e03\u800c\u6f0f\u6389\u771f\u6b63\u7684\u7ec4\u5408\u98ce\u9669\u3002`

  const excellent = topCell && topCell.share <= 8
    ? `\u76ee\u524d\u6700\u5927\u4ea4\u53c9\u70b9\u5360\u6bd4\u4e0d\u9ad8\uff0c\u8fd9\u8bf4\u660e\u5404\u7ef4\u5ea6\u4e4b\u95f4\u8fd8\u6ca1\u6709\u51fa\u73b0\u5f3a\u8026\u5408\u5931\u63a7\u3002`
    : `\u672c\u56fe\u7684\u4f18\u52bf\u5728\u4e8e\u7ec4\u5408\u98ce\u9669\u843d\u70b9\u6e05\u6670\uff0c\u53ef\u4ee5\u76f4\u63a5\u7528\u4e8e\u6307\u5bfc\u540e\u7eed\u4e13\u9879\u6cbb\u7406\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildFallbackNarrative = summary => {
  const primaryItems = getPrimaryItems(summary)
  const topItem = primaryItems[0] || null
  const secondItem = primaryItems[1] || null
  const topShare = getMetricShare(topItem)

  const problem = summary.topNegativeCell
    ? `\u300a${summary.title}\u300b\u4e2d${describeCell(summary.topNegativeCell)}\u662f\u5f53\u524d\u6700\u9700\u8981\u5904\u7406\u7684\u5934\u90e8\u95ee\u9898\u70b9\uff0c\u5df2\u5bf9\u6574\u4f53\u5206\u5e03\u5f62\u6210\u660e\u663e\u62c9\u52a8\u3002`
    : topItem
      ? `\u300a${summary.title}\u300b\u76ee\u524d\u4ee5${describeItem(topItem)}\u4e3a\u4e3b\u5bfc\uff0c\u8fd9\u662f\u5f53\u524d\u6700\u503c\u5f97\u7ba1\u7406\u5c42\u5173\u6ce8\u7684\u5934\u90e8\u4fe1\u53f7\u3002`
      : `\u300a${summary.title}\u300b\u5df2\u663e\u793a\u51fa\u660e\u663e\u7684\u5934\u90e8\u503e\u659c\uff0c\u9700\u5c3d\u5feb\u5bf9\u6700\u5927\u503c\u6240\u5728\u9879\u8fdb\u884c\u5b9a\u4f4d\u3002`

  const risk = topShare >= 40
    ? `\u5934\u90e8\u9879\u5360\u6bd4${formatPercent(topShare)}\uff0c\u8bf4\u660e\u76ee\u524d\u5df2\u51fa\u73b0\u660e\u663e\u7684\u5355\u70b9\u4f9d\u8d56\u6216\u5355\u70b9\u538b\u529b\u3002`
    : summary.negativeShare >= 35
      ? `\u8d1f\u5411\u4fe1\u53f7\u7d2f\u8ba1\u5360\u6bd4${formatPercent(summary.negativeShare)}\uff0c\u98ce\u9669\u5df2\u4e0d\u518d\u662f\u5c40\u90e8\u5f02\u5e38\uff0c\u800c\u662f\u5728\u5411\u7ed3\u6784\u6027\u95ee\u9898\u6f14\u53d8\u3002`
      : `\u5f53\u524d\u7ed3\u6784\u6682\u672a\u5931\u63a7\uff0c\u4f46\u5934\u90e8\u9879\u4ecd\u8981\u7eb3\u5165\u4e0b\u4e00\u8f6e\u8d28\u91cf\u8ddf\u8e2a\u540d\u5355\u3002`

  const overall = summary.positiveShare >= 40 && summary.negativeShare <= 20
    ? `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u8be5\u56fe\u8868\u53cd\u6620\u7684\u7ed3\u6784\u57fa\u672c\u5065\u5eb7\uff0c\u6b63\u5411\u4fe1\u53f7\u80fd\u591f\u5bf9\u8d1f\u5411\u6ce2\u52a8\u5f62\u6210\u652f\u6491\u3002`
    : `\u4ece\u6574\u4f53\u8d28\u91cf\u770b\uff0c\u5f53\u524d\u66f4\u9002\u5408\u91c7\u7528\u201c\u5934\u90e8\u95ee\u9898\u5148\u6e05\u7406\u3001\u7ed3\u6784\u98ce\u9669\u518d\u538b\u964d\u201d\u7684\u63a8\u8fdb\u7b56\u7565\u3002`

  const attention = [topItem, secondItem].filter(Boolean).length
    ? `\u5efa\u8bae\u91cd\u70b9\u76ef\u7d27${describeItems([topItem, secondItem].filter(Boolean))}\uff0c\u786e\u8ba4\u5b83\u4eec\u662f\u5426\u8fd8\u5728\u6301\u7eed\u62ac\u5347\u6216\u5df2\u51fa\u73b0\u95ed\u73af\u8f6c\u6298\u3002`
    : `\u5efa\u8bae\u540e\u7eed\u7ee7\u7eed\u76ef\u9632\u5934\u90e8\u4fe1\u53f7\u7684\u53d8\u5316\u65b9\u5411\uff0c\u907f\u514d\u5176\u8fdb\u4e00\u6b65\u6269\u5927\u3002`

  const excellent = topShare <= 20
    ? `\u76ee\u524d\u672a\u51fa\u73b0\u5355\u70b9\u538b\u5012\u6027\u96c6\u4e2d\uff0c\u8fd9\u8bf4\u660e\u56fe\u8868\u6240\u5bf9\u5e94\u7684\u8d28\u91cf\u9762\u4ecd\u5177\u5907\u4e00\u5b9a\u97e7\u6027\u3002`
    : summary.topPositiveRow
      ? `${describeItem(summary.topPositiveRow)}\u662f\u5f53\u524d\u503c\u5f97\u4fdd\u6301\u7684\u6b63\u5411\u57fa\u7ebf\uff0c\u53ef\u4f5c\u4e3a\u540e\u7eed\u590d\u5236\u7684\u53c2\u8003\u3002`
      : `\u672c\u56fe\u7684\u4f18\u52bf\u5728\u4e8e\u95ee\u9898\u840c\u53d1\u70b9\u6e05\u6670\uff0c\u6709\u5229\u4e8e\u5feb\u901f\u805a\u7126\u548c\u76f4\u63a5\u5e72\u9884\u3002`

  return { problem, risk, overall, attention, excellent }
}

const buildNarrativeByTheme = summary => {
  const theme = resolveTheme(summary)

  switch (theme) {
    case 'status':
      return buildStatusNarrative(summary)
    case 'priority':
      return buildPriorityNarrative(summary)
    case 'severity':
      return buildSeverityNarrative(summary)
    case 'root-cause':
      return buildRootCauseNarrative(summary)
    case 'module':
      return buildModuleNarrative(summary)
    case 'people':
      return buildPeopleNarrative(summary)
    case 'workload':
      return buildWorkloadNarrative(summary)
    case 'coverage':
      return buildCoverageNarrative(summary)
    case 'matrix':
      return buildMatrixNarrative(summary)
    default:
      return buildFallbackNarrative(summary)
  }
}

const narrative = computed(() => {
  let summary = null

  if (props.block?.type === 'distribution') {
    summary = summarizeDistribution(props.block)
  } else if (props.block?.type === 'table' || props.block?.type === 'matrix') {
    summary = summarizeTableLike(props.block)
  }

  return summary ? buildNarrativeByTheme(summary) : null
})

const analysisItems = computed(() => {
  if (!narrative.value) {
    return []
  }

  return ANALYSIS_ORDER.map(item => ({
    ...item,
    content: narrative.value[item.key] || '\u6682\u65e0\u53ef\u5c55\u793a\u7684\u5206\u6790\u7ed3\u8bba\u3002',
  }))
})
</script>

<style scoped lang="scss">
.analysis-narrative {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.analysis-narrative__item {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(17, 45, 67, 0.08);
  background: linear-gradient(180deg, rgba(246, 249, 252, 0.92), rgba(255, 255, 255, 0.96));
}

.analysis-narrative__item h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #17324d;
}

.analysis-narrative__item p {
  margin: 0;
  color: #567086;
  font-size: 13px;
  line-height: 1.7;
}

.analysis-narrative__item--problem {
  background: linear-gradient(180deg, rgba(255, 244, 242, 0.95), rgba(255, 255, 255, 0.98));
  border-color: rgba(217, 119, 87, 0.18);
}

.analysis-narrative__item--risk {
  background: linear-gradient(180deg, rgba(255, 248, 235, 0.95), rgba(255, 255, 255, 0.98));
  border-color: rgba(214, 157, 46, 0.2);
}

.analysis-narrative__item--overall {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.98));
  border-color: rgba(59, 130, 246, 0.16);
}

.analysis-narrative__item--attention {
  background: linear-gradient(180deg, rgba(245, 243, 255, 0.95), rgba(255, 255, 255, 0.98));
  border-color: rgba(124, 58, 237, 0.16);
}

.analysis-narrative__item--excellent {
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.95), rgba(255, 255, 255, 0.98));
  border-color: rgba(34, 197, 94, 0.16);
}

@media (max-width: 900px) {
  .analysis-narrative {
    grid-template-columns: 1fr;
  }
}
</style>
