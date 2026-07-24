import * as echarts from 'echarts'

const responsibilityColors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#feca57']
const seriesColors = ['#667eea', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#fa709a', '#feca57', '#36cfc9', '#1890ff', '#9254de']

const baseGrid = {
  left: '3%',
  right: '4%',
  bottom: '15%',
  containLabel: true
}

function createAxisBarOption({ xAxisData = [], series = [], legend = [], rotate = 40, yAxisName = '数量', grid = baseGrid }) {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: legend.length ? {
      data: legend,
      bottom: 0,
      type: 'scroll'
    } : undefined,
    grid,
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLabel: {
        rotate,
        interval: 0,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: yAxisName
    },
    series
  }
}

function buildSeriesMap(seriesMap = {}, stack = null, palette = seriesColors) {
  return Object.keys(seriesMap).map((name, index) => ({
    name,
    type: 'bar',
    stack,
    data: seriesMap[name] || [],
    itemStyle: { color: palette[index % palette.length] },
    label: {
      show: true,
      position: stack ? 'inside' : 'top',
      formatter: params => (params.value > 0 ? params.value : '')
    }
  }))
}

export function createRequirementDefectsOption(data = {}) {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: data.requirements || [],
      axisLabel: {
        rotate: 45,
        interval: 0,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: '缺陷数'
    },
    series: [
      {
        type: 'bar',
        data: data.defect_counts || [],
        barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        },
        label: { show: true, position: 'top' }
      }
    ]
  }
}

export function createRootCauseResponsibilityOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.root_causes || [],
    legend: Object.keys(data.responsibilities || {}),
    series: buildSeriesMap(data.responsibilities, 'total', responsibilityColors),
    yAxisName: '缺陷数'
  })
}

export function createRequirementRootCauseResponsibilityOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.requirements || [],
    legend: Object.keys(data.responsibilities || {}),
    series: buildSeriesMap(data.responsibilities, 'total', responsibilityColors),
    yAxisName: '缺陷数'
  })
}

export function createProductRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.root_causes || [],
    legend: Object.keys(data.products || {}),
    series: buildSeriesMap(data.products),
    yAxisName: '缺陷数'
  })
}

export function createDeveloperRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.root_causes || [],
    legend: Object.keys(data.developers || {}),
    series: buildSeriesMap(data.developers),
    yAxisName: '缺陷数'
  })
}

export function createTesterRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.root_causes || [],
    legend: Object.keys(data.testers || {}),
    series: buildSeriesMap(data.testers),
    yAxisName: '缺陷数'
  })
}

export function createProductManagerRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.product_managers || [],
    legend: Object.keys(data.root_causes || {}),
    series: buildSeriesMap(data.root_causes),
    yAxisName: '缺陷数'
  })
}

export function createFrontendDeveloperRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.frontend_developers || [],
    legend: Object.keys(data.root_causes || {}),
    series: buildSeriesMap(data.root_causes),
    yAxisName: '缺陷数'
  })
}

export function createBackendDeveloperRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.backend_developers || [],
    legend: Object.keys(data.root_causes || {}),
    series: buildSeriesMap(data.root_causes),
    yAxisName: '缺陷数'
  })
}

export function createTesterPersonRootCauseOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.tester_persons || [],
    legend: Object.keys(data.root_causes || {}),
    series: buildSeriesMap(data.root_causes),
    yAxisName: '缺陷数'
  })
}

export function createReqPriorityStatusOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.priorities || [],
    legend: Object.keys(data.statuses || {}),
    series: buildSeriesMap(data.statuses, 'status-stack'),
    yAxisName: '需求数'
  })
}

export function createReqPriorityTypeOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.priorities || [],
    legend: Object.keys(data.types || {}),
    series: buildSeriesMap(data.types, 'type-stack'),
    yAxisName: '需求数'
  })
}

export function createReqGroupOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.groups || [],
    series: [
      {
        name: '需求数',
        type: 'bar',
        data: data.counts || [],
        itemStyle: { color: '#5b8ff9' },
        label: { show: true, position: 'top' }
      }
    ],
    yAxisName: '需求数'
  })
}

export function createReqProductManagerOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.product_managers || [],
    series: [
      {
        name: '需求数',
        type: 'bar',
        data: data.counts || [],
        itemStyle: { color: '#36cfc9' },
        label: { show: true, position: 'top' }
      }
    ],
    yAxisName: '需求数'
  })
}

export function createReqDeveloperOption(data = {}) {
  return createAxisBarOption({
    xAxisData: data.developers || [],
    series: [
      {
        name: '需求数',
        type: 'bar',
        data: data.counts || [],
        itemStyle: { color: '#9254de' },
        label: { show: true, position: 'top' }
      }
    ],
    yAxisName: '需求数'
  })
}

export function createReqTesterWorkloadOption(data = {}) {
  return {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['需求数', '测试工时'],
      bottom: 0
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: data.testers || [],
      axisLabel: {
        rotate: 35,
        interval: 0
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '需求数'
      },
      {
        type: 'value',
        name: '测试工时'
      }
    ],
    series: [
      {
        name: '需求数',
        type: 'bar',
        data: data.req_counts || [],
        itemStyle: { color: '#5b8ff9' },
        label: { show: true, position: 'top' }
      },
      {
        name: '测试工时',
        type: 'line',
        yAxisIndex: 1,
        data: data.workloads || [],
        smooth: true,
        itemStyle: { color: '#f59e0b' }
      }
    ]
  }
}

export function createTestcaseTesterOption(data = {}) {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['已执行', '未执行', '总数'],
      bottom: 0
    },
    grid: baseGrid,
    xAxis: {
      type: 'category',
      data: data.testers || [],
      axisLabel: {
        rotate: 35,
        interval: 0
      }
    },
    yAxis: {
      type: 'value',
      name: '用例数'
    },
    series: [
      {
        name: '已执行',
        type: 'bar',
        stack: 'execution',
        data: data.executed || [],
        itemStyle: { color: '#52c41a' },
        label: { show: true, position: 'inside', formatter: params => (params.value ? params.value : '') }
      },
      {
        name: '未执行',
        type: 'bar',
        stack: 'execution',
        data: data.not_executed || [],
        itemStyle: { color: '#faad14' },
        label: { show: true, position: 'inside', formatter: params => (params.value ? params.value : '') }
      },
      {
        name: '总数',
        type: 'line',
        data: data.total || [],
        itemStyle: { color: '#1890ff' }
      }
    ]
  }
}

export function createDefectReqRateOption(data = {}) {
  const categories = data.categories || []
  const counts = data.counts || []
  return {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 0
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: categories.map((category, index) => ({
          name: category,
          value: counts[index] || 0,
          itemStyle: {
            color: seriesColors[index % seriesColors.length]
          }
        })),
        label: {
          formatter: '{b}\n{c}'
        }
      }
    ]
  }
}

