export const normalizeTableValue = (value) => {
  if (value === undefined || value === null) {
    return ''
  }

  if (Array.isArray(value)) {
    return value
      .flatMap(item => splitTableValues(item))
      .join(', ')
  }

  if (typeof value === 'object') {
    return String(
      value.label ??
      value.name ??
      value.value ??
      value.text ??
      ''
    ).trim()
  }

  return String(value).trim()
}

export const splitTableValues = (value) => {
  if (Array.isArray(value)) {
    return value
      .flatMap(item => splitTableValues(item))
      .filter(Boolean)
  }

  const normalized = normalizeTableValue(value)
  return normalized ? [normalized] : []
}

export const compareTableText = (left, right) => (
  normalizeTableValue(left).localeCompare(
    normalizeTableValue(right),
    'zh-CN',
    {
      numeric: true,
      sensitivity: 'base',
    }
  )
)

export const compareTableNumber = (left, right) => {
  const leftNumber = Number(left)
  const rightNumber = Number(right)
  return (Number.isFinite(leftNumber) ? leftNumber : 0) - (Number.isFinite(rightNumber) ? rightNumber : 0)
}

export const compareTableDate = (left, right) => {
  const leftTime = new Date(left || 0).getTime()
  const rightTime = new Date(right || 0).getTime()
  return (Number.isFinite(leftTime) ? leftTime : 0) - (Number.isFinite(rightTime) ? rightTime : 0)
}

export const buildTableFilters = (rows, resolver, limit = 20, comparator = compareTableText) => {
  const values = Array.from(
    new Set(
      (Array.isArray(rows) ? rows : [])
        .flatMap(row => splitTableValues(resolver(row)))
        .filter(Boolean)
    )
  )

  return values
    .sort(comparator)
    .slice(0, limit)
    .map(value => ({
      text: value,
      value,
    }))
}

export const createTableFilter = resolver => (value, row) => {
  const normalized = normalizeTableValue(value)
  return splitTableValues(resolver(row)).includes(normalized)
}

export const createTextSorter = resolver => (left, right) => compareTableText(resolver(left), resolver(right))
export const createNumberSorter = resolver => (left, right) => compareTableNumber(resolver(left), resolver(right))
export const createDateSorter = resolver => (left, right) => compareTableDate(resolver(left), resolver(right))
