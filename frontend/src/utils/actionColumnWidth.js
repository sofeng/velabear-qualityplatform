const CJK_CHAR_REGEXP = /[\u3400-\u9fff\uf900-\ufaff]/

const VARIANT_METRICS = Object.freeze({
  button: {
    horizontalPadding: 22,
    borderWidth: 2,
    iconWidth: 16,
    iconGap: 4,
  },
  link: {
    horizontalPadding: 0,
    borderWidth: 0,
    iconWidth: 0,
    iconGap: 0,
  },
  text: {
    horizontalPadding: 0,
    borderWidth: 0,
    iconWidth: 0,
    iconGap: 0,
  },
})

export const estimateTextWidth = (text = '') => {
  let width = 0

  for (const char of String(text).trim()) {
    if (char === ' ') {
      width += 4
    } else if (CJK_CHAR_REGEXP.test(char)) {
      width += 14
    } else if (/[A-Z0-9]/.test(char)) {
      width += 8
    } else {
      width += 7
    }
  }

  return width
}

const normalizeColumnValue = (value) => {
  if (Array.isArray(value)) {
    return value.map(item => normalizeColumnValue(item)).filter(Boolean).join(' / ')
  }
  if (value && typeof value === 'object') {
    return String(value.label ?? value.name ?? value.title ?? value.code ?? value.id ?? '').trim()
  }
  return String(value ?? '').trim()
}

export const buildTableColumnWidth = (label, rows, valueGetter, options = {}) => {
  const min = Number(options.min ?? 96)
  const max = Number(options.max ?? 320)
  const padding = Number(options.padding ?? 36)
  const headerExtra = Number(options.headerExtra ?? 32)
  const contentExtra = Number(options.contentExtra ?? 0)
  const sampleLimit = Number(options.sampleLimit ?? 100)
  const safeRows = Array.isArray(rows) ? rows.slice(0, sampleLimit) : []

  const headerWidth = estimateTextWidth(label) + headerExtra
  const contentWidth = safeRows.reduce((currentMax, row) => {
    try {
      return Math.max(
        currentMax,
        estimateTextWidth(normalizeColumnValue(valueGetter?.(row))) + contentExtra
      )
    } catch (error) {
      return currentMax
    }
  }, 0)

  return Math.min(max, Math.max(min, Math.ceil(Math.max(headerWidth, contentWidth) + padding)))
}

const normalizeActionItem = (item, fallbackVariant) => {
  if (typeof item === 'string') {
    return {
      label: item,
      variant: fallbackVariant,
      icon: false,
      extraWidth: 0,
    }
  }

  return {
    label: String(item?.label ?? item?.text ?? '').trim(),
    variant: item?.variant || fallbackVariant,
    icon: Boolean(item?.icon),
    extraWidth: Number(item?.extraWidth || 0),
  }
}

const estimateActionItemWidth = (item, fallbackVariant = 'button') => {
  const normalizedItem = normalizeActionItem(item, fallbackVariant)
  const metrics = VARIANT_METRICS[normalizedItem.variant] || VARIANT_METRICS.button

  return Math.ceil(
    estimateTextWidth(normalizedItem.label) +
      metrics.horizontalPadding +
      metrics.borderWidth +
      (normalizedItem.icon ? metrics.iconWidth + metrics.iconGap : 0) +
      normalizedItem.extraWidth
  )
}

export const buildActionColumnWidth = (lines, options = {}) => {
  const variant = options.variant || 'button'
  const gap = Number(options.gap ?? 8)
  const padding = Number(options.padding ?? 12)
  const min = Number(options.min ?? (variant === 'button' ? 120 : 96))
  const max = Number(options.max ?? 520)

  const normalizedLines = (Array.isArray(lines) ? lines : [])
    .map(line => (Array.isArray(line) ? line : [line]).filter(Boolean))
    .filter(line => line.length)

  if (!normalizedLines.length) {
    return min
  }

  const maxLineWidth = normalizedLines.reduce((currentMax, line) => {
    const lineWidth = line.reduce(
      (total, item) => total + estimateActionItemWidth(item, variant),
      0
    ) + Math.max(0, line.length - 1) * gap

    return Math.max(currentMax, lineWidth)
  }, 0)

  return Math.min(max, Math.max(min, Math.ceil(maxLineWidth + padding)))
}
