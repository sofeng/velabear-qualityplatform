<template>
  <div class="analysis-chart-panel">
    <el-empty
      v-if="!hasChartData"
      description="暂无可展示的图表数据"
      :image-size="64"
    />
    <div
      v-else
      ref="chartRef"
      class="analysis-chart-panel__canvas"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
  active: {
    type: Boolean,
    default: true,
  },
  showValueLabels: {
    type: Boolean,
    default: false,
  },
})

const chartRef = ref(null)
let chartInstance = null

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

const truncateLabel = value => {
  const normalized = normalizeText(value)
  if (normalized.length <= 12) {
    return normalized
  }
  return `${normalized.slice(0, 12)}...`
}

const buildAxisLabelConfig = () => ({
  color: '#5c7489',
  fontSize: 12,
  formatter: value => truncateLabel(value),
})

const buildGrid = (rowCount, { hasLegend = false, hasValueLabels = false } = {}) => ({
  left: 56,
  right: 24,
  top: hasLegend || hasValueLabels ? 56 : 28,
  bottom: rowCount > 6 ? 82 : 52,
  containLabel: true,
})

const buildDataZoom = rowCount => {
  if (rowCount <= 8) {
    return []
  }

  return [
    {
      type: 'inside',
      xAxisIndex: 0,
      startValue: 0,
      endValue: Math.min(7, rowCount - 1),
    },
    {
      type: 'slider',
      xAxisIndex: 0,
      height: 16,
      bottom: 18,
      borderColor: 'rgba(17, 45, 67, 0.08)',
      fillerColor: 'rgba(36, 115, 166, 0.18)',
      handleStyle: {
        color: '#2473a6',
      },
      startValue: 0,
      endValue: Math.min(7, rowCount - 1),
    },
  ]
}

const formatValueLabel = (value, suffix = '') => {
  const normalizedValue = Array.isArray(value) ? value[value.length - 1] : value
  const numericValue = toNumber(normalizedValue)
  if (numericValue === null) {
    const fallbackValue = normalizeText(normalizedValue)
    return fallbackValue ? `${fallbackValue}${suffix}` : ''
  }

  const roundedValue = Math.round(numericValue * 100) / 100
  const displayValue = Number.isInteger(roundedValue)
    ? String(roundedValue)
    : roundedValue.toFixed(2).replace(/\.?0+$/, '')

  return `${displayValue}${suffix}`
}

const shouldRenderValueLabels = series =>
  props.showValueLabels && series.some(item => ['bar', 'line'].includes(item?.type))

const buildSeriesValueLabel = seriesItem => ({
  show: true,
  position: 'top',
  distance: seriesItem?.type === 'line' ? 10 : 6,
  color: '#1f3d5a',
  fontSize: 11,
  fontWeight: 600,
  formatter: params => formatValueLabel(params?.value, seriesItem?.qaValueLabelSuffix || ''),
})

const withValueLabels = series => {
  if (!shouldRenderValueLabels(series)) {
    return series
  }

  return series.map(seriesItem => ({
    ...seriesItem,
    label: {
      ...(seriesItem.label || {}),
      ...buildSeriesValueLabel(seriesItem),
    },
    labelLayout: {
      hideOverlap: true,
      ...(seriesItem.labelLayout || {}),
    },
  }))
}

const buildBaseOption = ({ categories, legend = [], series = [], yAxis = null }) => ({
  color: ['#1f78b4', '#31a354', '#ff8c42', '#7b61ff', '#d1495b', '#2a9d8f', '#ef476f'],
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow',
    },
    backgroundColor: 'rgba(18, 36, 53, 0.92)',
    borderWidth: 0,
    textStyle: {
      color: '#fff',
    },
  },
  legend: legend.length
    ? {
        top: 0,
        icon: 'roundRect',
        textStyle: {
          color: '#5c7489',
        },
      }
    : undefined,
  grid: buildGrid(categories.length, {
    hasLegend: legend.length > 0,
    hasValueLabels: shouldRenderValueLabels(series),
  }),
  xAxis: {
    type: 'category',
    data: categories,
    axisLine: {
      lineStyle: {
        color: '#d8e2eb',
      },
    },
    axisLabel: buildAxisLabelConfig(),
  },
  yAxis: yAxis || {
    type: 'value',
    splitLine: {
      lineStyle: {
        color: 'rgba(17, 45, 67, 0.08)',
      },
    },
    axisLabel: {
      color: '#5c7489',
      fontSize: 12,
    },
  },
  dataZoom: buildDataZoom(categories.length),
  series: withValueLabels(series),
})

const buildDistributionOption = block => {
  const rows = Array.isArray(block?.rows) ? block.rows : []
  if (!rows.length) {
    return null
  }

  const categories = rows.map(row => normalizeText(row.label) || '-')
  const countSeries = rows.map(row => toNumber(row.count) ?? 0)
  const ratioSeries = rows.map(row => toNumber(row.ratio) ?? 0)

  return buildBaseOption({
    categories,
    legend: ['数量', '占比'],
    yAxis: [
      {
        type: 'value',
        name: '数量',
        splitLine: {
          lineStyle: {
            color: 'rgba(17, 45, 67, 0.08)',
          },
        },
        axisLabel: {
          color: '#5c7489',
          fontSize: 12,
        },
      },
      {
        type: 'value',
        name: '占比',
        min: 0,
        max: 100,
        splitLine: {
          show: false,
        },
        axisLabel: {
          color: '#5c7489',
          fontSize: 12,
          formatter: value => `${value}%`,
        },
      },
    ],
    series: [
      {
        name: '数量',
        type: 'bar',
        barMaxWidth: 28,
        data: countSeries,
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
        },
      },
      {
        name: '占比',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        qaValueLabelSuffix: '%',
        data: ratioSeries,
      },
    ],
  })
}

const buildTableLikeOption = block => {
  const rows = Array.isArray(block?.rows) ? block.rows : []
  const columns = Array.isArray(block?.columns) ? block.columns : []
  if (!rows.length || columns.length < 2) {
    return null
  }

  const dimensionColumn = columns[0]
  const seriesColumns = columns
    .slice(1)
    .filter(column => rows.some(row => toNumber(row?.[column.key]) !== null))
    .slice(0, 6)

  if (!seriesColumns.length) {
    const coverageColumns = columns.slice(1).filter(column => rows.some(row => normalizeText(row?.[column.key])))
    if (!coverageColumns.length) {
      return null
    }

    const categories = coverageColumns.map(column => normalizeText(column.label) || column.key)
    const countSeries = coverageColumns.map(column =>
      rows.reduce((total, row) => total + (normalizeText(row?.[column.key]) ? 1 : 0), 0)
    )
    const ratioSeries = coverageColumns.map((_, index) => {
      const count = countSeries[index] || 0
      return rows.length ? Math.round((count / rows.length) * 1000) / 10 : 0
    })

    return buildBaseOption({
      categories,
      legend: ['记录数', '覆盖率'],
      yAxis: [
        {
          type: 'value',
          name: '记录数',
          splitLine: {
            lineStyle: {
              color: 'rgba(17, 45, 67, 0.08)',
            },
          },
          axisLabel: {
            color: '#5c7489',
            fontSize: 12,
          },
        },
        {
          type: 'value',
          name: '覆盖率',
          min: 0,
          max: 100,
          splitLine: {
            show: false,
          },
          axisLabel: {
            color: '#5c7489',
            fontSize: 12,
            formatter: value => `${value}%`,
          },
        },
      ],
      series: [
        {
          name: '记录数',
          type: 'bar',
          barMaxWidth: 28,
          itemStyle: {
            borderRadius: [8, 8, 0, 0],
          },
          data: countSeries,
        },
        {
          name: '覆盖率',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbolSize: 8,
          qaValueLabelSuffix: '%',
          data: ratioSeries,
        },
      ],
    })
  }

  const displayRows = rows.slice(0, 12)
  const categories = displayRows.map(row => normalizeText(row?.[dimensionColumn.key]) || '-')

  const series = seriesColumns.map((column, index) => {
    const label = normalizeText(column.label) || `系列${index + 1}`
    const isTrendSeries = /率|ratio|趋势|指数|占比|\/|%/i.test(`${column.key} ${label}`)

    return {
      name: label,
      type: isTrendSeries ? 'line' : 'bar',
      smooth: isTrendSeries,
      barMaxWidth: isTrendSeries ? undefined : 26,
      symbolSize: isTrendSeries ? 7 : undefined,
      itemStyle: isTrendSeries
        ? undefined
        : {
            borderRadius: [8, 8, 0, 0],
          },
      data: displayRows.map(row => toNumber(row?.[column.key]) ?? 0),
    }
  })

  return buildBaseOption({
    categories,
    legend: series.map(item => item.name),
    series,
  })
}

const buildMultiSeriesOption = (block, chartType = 'bar') => {
  const categories = Array.isArray(block?.categories)
    ? block.categories.map(item => normalizeText(item) || '-')
    : []
  const isLineChart = chartType === 'line'
  const series = (Array.isArray(block?.series) ? block.series : [])
    .map(item => ({
      name: normalizeText(item?.name || item?.key),
      type: chartType,
      smooth: isLineChart,
      symbolSize: isLineChart ? 7 : undefined,
      barMaxWidth: isLineChart ? undefined : 26,
      itemStyle: isLineChart
        ? undefined
        : {
            borderRadius: [8, 8, 0, 0],
          },
      data: (Array.isArray(item?.data) ? item.data : []).map(value => toNumber(value) ?? 0),
    }))
    .filter(item => item.name)

  if (!categories.length || !series.length) {
    return null
  }

  return buildBaseOption({
    categories,
    legend: series.map(item => item.name),
    series,
  })
}

const chartOption = computed(() => {
  if (props.block?.type === 'distribution') {
    return buildDistributionOption(props.block)
  }

  if (props.block?.type === 'multi-series-bar') {
    return buildMultiSeriesOption(props.block, 'bar')
  }

  if (props.block?.type === 'multi-series-line') {
    return buildMultiSeriesOption(props.block, 'line')
  }

  if (props.block?.type === 'table' || props.block?.type === 'matrix') {
    return buildTableLikeOption(props.block)
  }

  return null
})

const hasChartData = computed(() => Boolean(chartOption.value))

const renderChart = async () => {
  if (!props.active || !hasChartData.value) {
    return
  }

  await nextTick()
  const element = chartRef.value
  if (!element || element.offsetWidth <= 0 || element.offsetHeight <= 0) {
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(element)
  }

  chartInstance.setOption(chartOption.value, true)
  chartInstance.resize()
}

const resizeChart = () => {
  chartInstance?.resize()
}

const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

watch(
  () => [props.active, props.block, props.showValueLabels],
  async () => {
    if (!hasChartData.value) {
      disposeChart()
      return
    }

    await renderChart()
  },
  {
    deep: true,
    immediate: true,
  }
)

onMounted(() => {
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  disposeChart()
})
</script>

<style scoped lang="scss">
.analysis-chart-panel {
  min-height: 360px;
}

.analysis-chart-panel__canvas {
  width: 100%;
  height: 360px;
}
</style>
