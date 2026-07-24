<template>
  <div
    class="testing-overview-page"
    :class="{ 'testing-overview-page--embedded': embedded }"
  >
    <div class="testing-overview-panel" v-loading="loading">
      <el-empty
        v-if="!normalizedLinkedVersion"
        description="请选择版本号后查看测试总览"
      />

      <el-empty
        v-else-if="!groupedMindmaps.length"
        description="当前版本暂无可展示的测试脑图数据"
      />

      <el-tabs
        v-else
        v-model="activeGroupTab"
        class="testing-group-tabs"
      >
        <el-tab-pane
          v-for="group in groupedMindmaps"
          :key="group.name"
          :label="`${group.name} (${group.requirementCount})`"
          :name="group.name"
        >
          <div class="testing-group-panel">
            <div class="group-toolbar">
              <div class="testing-legend testing-legend--group">
                <span class="testing-legend__item">
                  <i class="testing-legend__swatch testing-legend__swatch--not-run" />
                  未执行
                </span>
                <span class="testing-legend__item">
                  <i class="testing-legend__swatch testing-legend__swatch--pass" />
                  通过
                </span>
                <span class="testing-legend__item">
                  <i class="testing-legend__swatch testing-legend__swatch--fail" />
                  失败
                </span>
                <span class="testing-legend__item">
                  <i class="testing-legend__swatch testing-legend__swatch--block" />
                  阻塞
                </span>
                <span class="testing-legend__item">
                  <i class="testing-legend__swatch testing-legend__swatch--not-test" />
                  本版本不测
                </span>
              </div>

              <el-tabs
                v-model="activeDimensionTab"
                class="dimension-tabs"
              >
                <el-tab-pane label="需求维度" name="requirement" />
                <el-tab-pane label="成员维度" name="member" />
              </el-tabs>
            </div>

            <div class="group-summary">
              <div class="group-summary-card group-summary-card--blue">
                <span class="group-summary-card__label">需求数</span>
                <strong class="group-summary-card__value">{{ group.requirementCount }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--blue">
                <span class="group-summary-card__label">测试点总数</span>
                <strong class="group-summary-card__value">{{ group.totalPoints }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--blue">
                <span class="group-summary-card__label">未执行</span>
                <strong class="group-summary-card__value">{{ group.statusTotals.not_run }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--green">
                <span class="group-summary-card__label">通过</span>
                <strong class="group-summary-card__value">{{ group.statusTotals.pass }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--red">
                <span class="group-summary-card__label">失败</span>
                <strong class="group-summary-card__value">{{ group.statusTotals.fail }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--yellow">
                <span class="group-summary-card__label">阻塞</span>
                <strong class="group-summary-card__value">{{ group.statusTotals.block }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--gray">
                <span class="group-summary-card__label">本版本不测</span>
                <strong class="group-summary-card__value">{{ group.statusTotals.not_test }}</strong>
              </div>
            </div>

            <el-empty
              v-if="activeDimensionTab === 'requirement' && !group.requirements.length"
              description="该组别暂无需求数据"
            />

            <el-empty
              v-else-if="activeDimensionTab === 'member' && !group.memberRows.length"
              description="该组别暂无可视化成员测试数据"
            />

            <div
              v-else-if="activeDimensionTab === 'requirement'"
              class="count-scroll"
            >
              <div class="count-board">
                <div class="count-row count-row--header">
                  <div class="count-meta count-meta--header">
                    需求 / 测试点状态
                  </div>
                  <div
                    class="count-timeline count-timeline--header"
                    :style="buildScaleStyle(group.maxTotalCount)"
                  >
                    <div
                      v-for="cell in group.scaleCells"
                      :key="cell.key"
                      class="count-cell-header"
                    >
                      {{ cell.label }}
                    </div>
                  </div>
                </div>

                <div
                  v-for="requirement in group.requirements"
                  :key="requirement.id"
                  class="count-row"
                >
                  <div class="count-meta">
                    <div class="count-meta__top">
                      <span class="count-meta__name">{{ requirement.requirementName }}</span>
                      <el-tag
                        size="small"
                        effect="plain"
                        :type="getProgressTagType(requirement.progressState)"
                      >
                        {{ getProgressLabel(requirement.progressState) }}
                      </el-tag>
                    </div>

                    <div class="count-meta__stats">
                      <span>总数：{{ requirement.totalCount }}</span>
                      <span>未执行：{{ requirement.statusCounts.not_run }}</span>
                      <span>通过：{{ requirement.statusCounts.pass }}</span>
                      <span>失败：{{ requirement.statusCounts.fail }}</span>
                      <span>阻塞：{{ requirement.statusCounts.block }}</span>
                      <span>不测：{{ requirement.statusCounts.not_test }}</span>
                    </div>
                  </div>

                  <div
                    class="count-timeline count-timeline--body"
                    :style="buildScaleStyle(group.maxTotalCount)"
                  >
                    <div class="count-grid">
                      <span
                        v-for="cell in group.scaleCells"
                        :key="`${requirement.id}-${cell.key}`"
                        class="count-grid__cell"
                      />
                    </div>

                    <div class="count-lane">
                      <div
                        v-if="requirement.totalCount"
                        class="count-bar"
                      >
                        <div
                          v-for="segment in requirement.segments"
                          :key="`${requirement.id}-${segment.key}`"
                          class="count-bar__segment"
                          :class="`count-bar__segment--${segment.key}`"
                          :style="buildSegmentStyle(segment)"
                        >
                          <span
                            v-if="shouldShowSegmentLabel(segment)"
                            class="count-bar__label"
                          >
                            {{ segment.count }}
                          </span>
                        </div>
                      </div>
                      <span v-else class="count-lane__empty">无测试点</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="count-scroll">
              <div class="count-board">
                <div class="count-row count-row--header">
                  <div class="count-meta count-meta--header">
                    成员 / 关联需求
                  </div>
                  <div
                    class="count-timeline count-timeline--header"
                    :style="buildScaleStyle(group.memberMaxTotalCount)"
                  >
                    <div
                      v-for="cell in group.memberScaleCells"
                      :key="cell.key"
                      class="count-cell-header"
                    >
                      {{ cell.label }}
                    </div>
                  </div>
                </div>

                <div
                  v-for="memberRow in group.memberRows"
                  :key="memberRow.name"
                  class="count-row"
                >
                  <div class="count-meta member-count-meta">
                    <div class="count-meta__top">
                      <span class="count-meta__name">{{ memberRow.name }}</span>
                      <el-tag size="small" effect="plain">
                        {{ memberRow.requirementCount }} 条需求
                      </el-tag>
                    </div>

                    <div class="count-meta__summary">
                      {{ buildMemberRowSummary(memberRow) }}
                    </div>

                    <div
                      v-if="memberRow.requirementPreview.length"
                      class="member-count-meta__requirements"
                    >
                      {{ memberRow.requirementPreview.join('、') }}<span v-if="memberRow.requirementCount > memberRow.requirementPreview.length"> 等</span>
                    </div>
                  </div>

                  <div
                    class="count-timeline count-timeline--body member-count-timeline"
                    :style="buildMemberTimelineStyle(group.memberMaxTotalCount, memberRow)"
                  >
                    <div class="count-grid">
                      <span
                        v-for="cell in group.memberScaleCells"
                        :key="`${memberRow.name}-${cell.key}`"
                        class="count-grid__cell"
                      />
                    </div>

                    <div class="count-lane">
                      <template
                        v-for="memberRequirement in memberRow.visualRequirements"
                        :key="`${memberRow.name}-${memberRequirement.requirementId}`"
                      >
                        <div
                          class="member-count-bar"
                          :style="buildMemberRequirementStyle(memberRequirement)"
                          :title="buildMemberRequirementTitle(memberRow, memberRequirement)"
                        >
                          <div
                            v-for="segment in memberRequirement.segments"
                            :key="`${memberRow.name}-${memberRequirement.requirementId}-${segment.key}`"
                            class="count-bar__segment"
                            :class="`count-bar__segment--${segment.key}`"
                            :style="buildSegmentStyle(segment)"
                          />

                          <div
                            v-if="shouldShowMemberRequirementInlineLabel(memberRequirement)"
                            class="member-count-bar__label"
                          >
                            <span class="member-count-bar__text">{{ memberRequirement.shortLabel }}</span>
                            <span class="member-count-bar__metrics">
                              {{ formatPercent(memberRequirement.completionRatio) }} / {{ formatPercent(memberRequirement.passRate) }}
                            </span>
                          </div>
                        </div>

                        <div
                          v-if="shouldShowMemberRequirementCompactLabel(memberRequirement)"
                          class="member-count-bar__compact-label"
                          :style="buildMemberRequirementCompactLabelStyle(memberRequirement)"
                        >
                          <span class="member-count-bar__compact-text">{{ memberRequirement.shortLabel }}</span>
                          <span class="member-count-bar__compact-metrics">
                            {{ formatPercent(memberRequirement.completionRatio) }} / {{ formatPercent(memberRequirement.passRate) }}
                          </span>
                        </div>
                      </template>

                      <span v-if="!memberRow.visualRequirements.length" class="count-lane__empty">无关联测试点</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  active: {
    type: Boolean,
    default: true,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
  linkedVersionId: {
    type: [Number, String, null],
    default: null,
  },
  linkedProjectId: {
    type: [Number, String, null],
    default: null,
  },
})

const MINDMAP_ENDPOINT = '/quality-analysis/reports/live-testing-overview/'
const COUNT_UNIT_WIDTH = 24
const NO_GROUP_LABEL = '无组别'
const STATUS_ORDER = Object.freeze([
  { key: 'not_run', label: '未执行' },
  { key: 'pass', label: '通过' },
  { key: 'fail', label: '失败' },
  { key: 'block', label: '阻塞' },
  { key: 'not_test', label: '本版本不测' },
])

const loading = ref(false)
const mindmaps = ref([])
const activeGroupTab = ref('')
const activeDimensionTab = ref('requirement')

const normalizeText = value => String(value ?? '').trim()
const normalizePositiveNumber = value => {
  const parsedValue = Number(value)
  return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null
}
const normalizedLinkedVersion = computed(() => normalizeText(props.linkedVersion))
const normalizedLinkedVersionId = computed(() => normalizePositiveNumber(props.linkedVersionId))
const normalizedLinkedProjectId = computed(() => normalizePositiveNumber(props.linkedProjectId))

const createEmptyStatusCounts = () => ({
  not_run: 0,
  pass: 0,
  fail: 0,
  block: 0,
  not_test: 0,
})

const normalizeStatusCounts = value => {
  const source = value && typeof value === 'object' ? value : {}

  return {
    not_run: Number(source.not_run) || 0,
    pass: Number(source.pass) || 0,
    fail: Number(source.fail) || 0,
    block: Number(source.block) || 0,
    not_test: Number(source.not_test) || 0,
  }
}

const buildSegments = statusCounts => {
  let offset = 0

  return STATUS_ORDER.reduce((segments, status) => {
    const count = Number(statusCounts[status.key]) || 0
    if (!count) {
      return segments
    }

    segments.push({
      key: status.key,
      count,
      offset,
    })
    offset += count
    return segments
  }, [])
}

const resolveProgressState = statusCounts => {
  const totalCount = STATUS_ORDER.reduce((sum, status) => sum + (Number(statusCounts[status.key]) || 0), 0)
  const effectiveTotal = totalCount - (Number(statusCounts.not_test) || 0)
  if (totalCount > 0 && effectiveTotal === 0) {
    return 'not_test'
  }
  if (!effectiveTotal || statusCounts.not_run === effectiveTotal) {
    return 'pending'
  }

  if (statusCounts.fail > 0 || statusCounts.block > 0) {
    return 'risk'
  }

  if (statusCounts.pass === effectiveTotal) {
    return 'completed'
  }

  return 'active'
}

const buildScaleCells = maxTotalCount => {
  const normalizedMaxCount = Math.max(Number(maxTotalCount) || 0, 0)
  if (!normalizedMaxCount) {
    return []
  }

  const interval = normalizedMaxCount <= 10
    ? 1
    : normalizedMaxCount <= 20
      ? 2
      : normalizedMaxCount <= 50
        ? 5
        : 10

  return Array.from({ length: normalizedMaxCount }, (_item, index) => {
    const value = index + 1
    return {
      key: value,
      label: value === 1 || value === normalizedMaxCount || value % interval === 0 ? String(value) : '',
    }
  })
}

const getExecutedCount = statusCounts => (
  Number(statusCounts.pass) + Number(statusCounts.fail) + Number(statusCounts.block)
)

const getCompletionRatio = (statusCounts, totalCount) => {
  const normalizedTotalCount = (Number(totalCount) || 0) - (Number(statusCounts.not_test) || 0)
  if (normalizedTotalCount <= 0) {
    return Number(totalCount) > 0 ? 1 : 0
  }
  return getExecutedCount(statusCounts) / normalizedTotalCount
}

const getPassRate = (statusCounts) => {
  const executedCount = getExecutedCount(statusCounts)
  if (!executedCount) {
    return 0
  }
  return (Number(statusCounts.pass) || 0) / executedCount
}

const formatPercent = value => {
  const percent = (Number(value) || 0) * 100
  if (Math.abs(percent - Math.round(percent)) < 0.0001) {
    return `${Math.round(percent)}%`
  }
  return `${percent.toFixed(1).replace(/\.0$/, '')}%`
}

const buildRequirementDisplayName = item => {
  const requirementKey = normalizeText(item?.requirementKey) || normalizeText(item?.requirement_key)
  const requirementTitle = normalizeText(item?.requirementTitle) || normalizeText(item?.requirement_title)
  const fallbackMindmapName = normalizeText(item?.mindmapName) || normalizeText(item?.name) || `脑图 #${item?.id || '-'}`
  const requirementName = [requirementKey, requirementTitle].filter(Boolean).join(' ') || fallbackMindmapName

  return {
    requirementKey,
    requirementTitle,
    mindmapName: fallbackMindmapName,
    requirementName,
    shortLabel: requirementKey || requirementTitle || fallbackMindmapName,
  }
}

const normalizedRequirements = computed(() => (
  mindmaps.value.map(item => {
    const statusCounts = normalizeStatusCounts(item?.statusCounts ?? item?.testpoint_count)
    const totalCount = Number(item?.totalCount) || STATUS_ORDER.reduce((sum, status) => sum + statusCounts[status.key], 0)
    const display = buildRequirementDisplayName(item)

    return {
      id: item?.id || display.requirementName,
      mindmapName: display.mindmapName,
      requirementKey: display.requirementKey,
      requirementTitle: display.requirementTitle,
      requirementName: display.requirementName,
      shortLabel: display.shortLabel,
      groupName: normalizeText(item?.groupName) || normalizeText(item?.responsibility_group) || NO_GROUP_LABEL,
      tester: normalizeText(item?.testerName) || normalizeText(item?.tester),
      frontendDeveloper: normalizeText(item?.frontendDeveloper) || normalizeText(item?.frontend_developer),
      backendDeveloper: normalizeText(item?.backendDeveloper) || normalizeText(item?.backend_developer),
      statusCounts,
      totalCount,
      segments: buildSegments(statusCounts),
      progressState: resolveProgressState(statusCounts),
      failOrBlockCount: statusCounts.fail + statusCounts.block,
      executedCount: getExecutedCount(statusCounts),
      completionRatio: getCompletionRatio(statusCounts, totalCount),
      updatedAt: normalizeText(item?.updatedAt) || normalizeText(item?.updated_at),
    }
  })
))

const buildCompactLabelWidth = requirement => {
  const labelLength = Array.from(String(requirement.shortLabel || '')).length
  const metricsText = `${formatPercent(requirement.completionRatio)} / ${formatPercent(requirement.passRate)}`
  const metricsLength = Array.from(metricsText).length
  const estimatedWidth = (Math.max(labelLength, 4) * 8) + (metricsLength * 7) + 32
  return Math.min(Math.max(estimatedWidth, 96), 168)
}

const assignCompactLabelLevels = requirements => {
  const levelRightEdges = []

  return requirements.map(requirement => {
    const barWidth = Math.max((requirement.totalCount * COUNT_UNIT_WIDTH) - 4, 16)
    if (barWidth >= 132) {
      return {
        ...requirement,
        compactLabelLevel: -1,
        compactLabelWidth: 0,
      }
    }

    const compactLabelWidth = buildCompactLabelWidth(requirement)
    const labelLeft = (requirement.offset * COUNT_UNIT_WIDTH) + 2
    const labelRight = labelLeft + compactLabelWidth
    let compactLabelLevel = 0

    while ((levelRightEdges[compactLabelLevel] ?? -Infinity) > labelLeft - 8) {
      compactLabelLevel += 1
    }

    levelRightEdges[compactLabelLevel] = labelRight

    return {
      ...requirement,
      compactLabelLevel,
      compactLabelWidth,
    }
  })
}

const buildMemberRows = requirements => {
  const memberMap = new Map()

  const addMemberRequirement = (memberName, requirement) => {
    const normalizedMemberName = normalizeText(memberName) || '未分配测试人员'
    if (!memberMap.has(normalizedMemberName)) {
      memberMap.set(normalizedMemberName, [])
    }

    memberMap.get(normalizedMemberName).push({
      requirementId: requirement.id,
      requirementKey: requirement.requirementKey,
      requirementTitle: requirement.requirementTitle,
      requirementName: requirement.requirementName,
      shortLabel: requirement.shortLabel,
      mindmapName: requirement.mindmapName,
      totalCount: requirement.totalCount,
      executedCount: requirement.executedCount,
      completionRatio: requirement.completionRatio,
      passRate: getPassRate(requirement.statusCounts),
      statusCounts: requirement.statusCounts,
      segments: buildSegments(requirement.statusCounts),
      progressState: requirement.progressState,
    })
  }

  requirements.forEach(requirement => {
    addMemberRequirement(requirement.tester, requirement)
  })

  return Array.from(memberMap.entries())
    .map(([name, memberRequirements]) => {
      const sortedRequirements = [...memberRequirements]
        .sort((left, right) => {
          const ratioDiff = right.completionRatio - left.completionRatio
          if (Math.abs(ratioDiff) > 0.0001) {
            return ratioDiff
          }

          const totalDiff = right.totalCount - left.totalCount
          if (totalDiff !== 0) {
            return totalDiff
          }

          return left.requirementName.localeCompare(right.requirementName, 'zh-CN')
        })

      let offset = 0
      const laidOutRequirements = sortedRequirements.map(requirement => {
        const requirementOffset = offset
        offset += requirement.totalCount
        return {
          ...requirement,
          offset: requirementOffset,
        }
      })

      const requirementsWithCompactLabels = assignCompactLabelLevels(laidOutRequirements)
      const visualRequirements = requirementsWithCompactLabels.filter(requirement => requirement.totalCount > 0)

      const statusTotals = requirementsWithCompactLabels.reduce((totals, requirement) => ({
        not_run: totals.not_run + requirement.statusCounts.not_run,
        pass: totals.pass + requirement.statusCounts.pass,
        fail: totals.fail + requirement.statusCounts.fail,
        block: totals.block + requirement.statusCounts.block,
        not_test: totals.not_test + requirement.statusCounts.not_test,
      }), createEmptyStatusCounts())

      const compactLabelLevelCount = requirementsWithCompactLabels.reduce(
        (maxValue, requirement) => Math.max(maxValue, requirement.compactLabelLevel + 1),
        0,
      )

      return {
        name,
        requirements: requirementsWithCompactLabels,
        visualRequirements,
        requirementCount: requirementsWithCompactLabels.length,
        totalCount: requirementsWithCompactLabels.reduce((sum, requirement) => sum + requirement.totalCount, 0),
        executedCount: requirementsWithCompactLabels.reduce((sum, requirement) => sum + requirement.executedCount, 0),
        statusTotals,
        requirementPreview: requirementsWithCompactLabels.map(requirement => requirement.shortLabel).filter(Boolean).slice(0, 3),
        compactLabelLevelCount,
      }
    })
    .filter(memberRow => memberRow.requirementCount > 0)
    .sort((left, right) => {
      const totalDiff = right.totalCount - left.totalCount
      if (totalDiff !== 0) {
        return totalDiff
      }

      const countDiff = right.requirementCount - left.requirementCount
      if (countDiff !== 0) {
        return countDiff
      }

      return left.name.localeCompare(right.name, 'zh-CN')
    })
}

const groupedMindmaps = computed(() => {
  const groupMap = new Map()

  normalizedRequirements.value.forEach(requirement => {
    const groupName = requirement.groupName || NO_GROUP_LABEL
    if (!groupMap.has(groupName)) {
      groupMap.set(groupName, [])
    }
    groupMap.get(groupName).push(requirement)
  })

  return Array.from(groupMap.entries())
    .map(([name, requirements]) => {
      const sortedRequirements = [...requirements].sort((left, right) => {
        const riskDiff = right.failOrBlockCount - left.failOrBlockCount
        if (riskDiff !== 0) {
          return riskDiff
        }

        const totalDiff = right.totalCount - left.totalCount
        if (totalDiff !== 0) {
          return totalDiff
        }

        return left.requirementName.localeCompare(right.requirementName, 'zh-CN')
      })

      const statusTotals = requirements.reduce((totals, requirement) => ({
        not_run: totals.not_run + requirement.statusCounts.not_run,
        pass: totals.pass + requirement.statusCounts.pass,
        fail: totals.fail + requirement.statusCounts.fail,
        block: totals.block + requirement.statusCounts.block,
        not_test: totals.not_test + requirement.statusCounts.not_test,
      }), createEmptyStatusCounts())

      const maxTotalCount = sortedRequirements.reduce(
        (maxValue, requirement) => Math.max(maxValue, requirement.totalCount),
        0,
      )
      const memberRows = buildMemberRows(sortedRequirements)
      const memberMaxTotalCount = memberRows.reduce(
        (maxValue, memberRow) => Math.max(maxValue, memberRow.totalCount),
        0,
      )

      return {
        name,
        requirements: sortedRequirements,
        memberRows,
        requirementCount: sortedRequirements.length,
        totalPoints: sortedRequirements.reduce((sum, requirement) => sum + requirement.totalCount, 0),
        statusTotals,
        maxTotalCount,
        scaleCells: buildScaleCells(maxTotalCount),
        memberMaxTotalCount,
        memberScaleCells: buildScaleCells(memberMaxTotalCount),
      }
    })
    .sort((left, right) => {
      const countDiff = right.requirementCount - left.requirementCount
      if (countDiff !== 0) {
        return countDiff
      }

      return left.name.localeCompare(right.name, 'zh-CN')
    })
})

const buildScaleStyle = maxTotalCount => ({
  width: `${Math.max((Number(maxTotalCount) || 0) * COUNT_UNIT_WIDTH, COUNT_UNIT_WIDTH)}px`,
})

const buildMemberTimelineStyle = (maxTotalCount, memberRow) => ({
  ...buildScaleStyle(maxTotalCount),
  height: `${buildMemberLaneHeight(memberRow)}px`,
})

const buildSegmentStyle = segment => ({
  left: `${(segment.offset * COUNT_UNIT_WIDTH) + 2}px`,
  width: `${Math.max((segment.count * COUNT_UNIT_WIDTH) - 4, 16)}px`,
})

const buildMemberRequirementStyle = memberRequirement => ({
  left: `${(memberRequirement.offset * COUNT_UNIT_WIDTH) + 2}px`,
  top: `${buildMemberLaneTop(memberRequirement)}px`,
  width: `${Math.max((memberRequirement.totalCount * COUNT_UNIT_WIDTH) - 4, 16)}px`,
})

const shouldShowSegmentLabel = segment => (segment.count * COUNT_UNIT_WIDTH) >= 36
const shouldShowMemberRequirementInlineLabel = memberRequirement => (memberRequirement.totalCount * COUNT_UNIT_WIDTH) >= 132
const shouldShowMemberRequirementCompactLabel = memberRequirement => !shouldShowMemberRequirementInlineLabel(memberRequirement)

const buildMemberLaneStyle = memberRow => ({
  height: `${buildMemberLaneHeight(memberRow)}px`,
})

const buildMemberLaneHeight = memberRow => {
  const compactLabelHeight = memberRow.compactLabelLevelCount > 0 ? (memberRow.compactLabelLevelCount * 20) + 8 : 0
  return compactLabelHeight + 52
}

const buildMemberLaneTop = memberRequirement => {
  const compactLabelOffset = memberRequirement.compactLabelLevel >= 0 ? 28 : 8
  return compactLabelOffset
}

const buildMemberRequirementCompactLabelStyle = memberRequirement => ({
  left: `${(memberRequirement.offset * COUNT_UNIT_WIDTH) + 2}px`,
  top: `${(memberRequirement.compactLabelLevel * 20) + 4}px`,
  width: `${memberRequirement.compactLabelWidth}px`,
})

const buildMemberRowSummary = memberRow => (
  `测试点 ${memberRow.totalCount} / 已执行 ${memberRow.executedCount} / 完成率 ${formatPercent(memberRow.executedCount / Math.max(memberRow.totalCount, 1))}`
)

const buildMemberRequirementTitle = (memberRow, memberRequirement) => (
  `${memberRow.name} / ${memberRequirement.requirementName} / 执行完成 ${formatPercent(memberRequirement.completionRatio)} / 通过率 ${formatPercent(memberRequirement.passRate)} / 测试点 ${memberRequirement.totalCount}`
)

const getProgressLabel = progressState => {
  if (progressState === 'not_test') return '本版本不测'
  if (progressState === 'completed') return '全部通过'
  if (progressState === 'risk') return '存在风险'
  if (progressState === 'active') return '进行中'
  return '未开始'
}

const getProgressTagType = progressState => {
  if (progressState === 'not_test') return 'info'
  if (progressState === 'completed') return 'success'
  if (progressState === 'risk') return 'danger'
  if (progressState === 'active') return 'warning'
  return 'info'
}

const loadAllMindmaps = async () => {
  if (!props.active) {
    return
  }

  if (!normalizedLinkedVersion.value) {
    mindmaps.value = []
    return
  }

  loading.value = true
  try {
    const response = await api.get(MINDMAP_ENDPOINT, {
      params: {
        project_id: normalizedLinkedProjectId.value || undefined,
        version: normalizedLinkedVersion.value,
      },
    })

    mindmaps.value = Array.isArray(response.data?.mindmaps) ? response.data.mindmaps : []
  } catch (error) {
    mindmaps.value = []
    ElMessage.error(`加载测试总览失败：${error.response?.data?.detail || error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

watch(
  () => groupedMindmaps.value,
  groups => {
    if (!groups.some(group => group.name === activeGroupTab.value)) {
      activeGroupTab.value = groups[0]?.name || ''
    }
  },
  { immediate: true }
)

watch(
  [
    () => props.active,
    () => normalizedLinkedVersion.value,
    () => normalizedLinkedProjectId.value,
  ],
  async ([active, linkedVersion, linkedProjectId], previousValues = []) => {
    const [previousActive, previousVersion, previousProjectId] = previousValues

    if (!active) {
      return
    }

    if (!linkedVersion) {
      mindmaps.value = []
      return
    }

    if (
      active !== previousActive ||
      linkedVersion !== previousVersion ||
      linkedProjectId !== previousProjectId
    ) {
      await loadAllMindmaps()
    }
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.testing-overview-page {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.testing-overview-page--embedded {
  height: 100%;
}

.testing-overview-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 16px 16px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.95) 0%, rgba(255, 255, 255, 1) 28%),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 34%);
}

.testing-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.testing-legend--group {
  padding-top: 2px;
}

.testing-legend__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.testing-legend__swatch {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  display: inline-flex;
}

.testing-legend__swatch--not-run {
  background: linear-gradient(90deg, #64748b, #94a3b8);
}

.testing-legend__swatch--pass {
  background: linear-gradient(90deg, #15803d, #22c55e);
}

.testing-legend__swatch--fail {
  background: linear-gradient(90deg, #b91c1c, #ef4444);
}

.testing-legend__swatch--block {
  background: linear-gradient(90deg, #b45309, #f59e0b);
}

.testing-legend__swatch--not-test {
  background: #6b7280;
}

.testing-group-tabs {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.testing-group-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.group-summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.group-summary-card {
  min-width: 128px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-summary-card__label {
  font-size: 12px;
  line-height: 18px;
  color: #64748b;
}

.group-summary-card__value {
  font-size: 18px;
  line-height: 24px;
  color: #0f172a;
}

.group-summary-card--blue {
  border-color: #bfdbfe;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
}

.group-summary-card--blue .group-summary-card__label,
.group-summary-card--blue .group-summary-card__value {
  color: #1d4ed8;
}

.group-summary-card--green {
  border-color: #bbf7d0;
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
}

.group-summary-card--green .group-summary-card__label,
.group-summary-card--green .group-summary-card__value {
  color: #15803d;
}

.group-summary-card--yellow {
  border-color: #fde68a;
  background: linear-gradient(180deg, #fffbeb 0%, #ffffff 100%);
}

.group-summary-card--yellow .group-summary-card__label,
.group-summary-card--yellow .group-summary-card__value {
  color: #b45309;
}

.group-summary-card--red {
  border-color: #fecaca;
  background: linear-gradient(180deg, #fef2f2 0%, #ffffff 100%);
}

.group-summary-card--red .group-summary-card__label,
.group-summary-card--red .group-summary-card__value {
  color: #b91c1c;
}

.group-summary-card--gray {
  border-color: #d1d5db;
  background: #f9fafb;
}

.group-summary-card--gray .group-summary-card__label,
.group-summary-card--gray .group-summary-card__value {
  color: #4b5563;
}

.count-scroll {
  flex: 1 1 0;
  min-height: 0;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
}

.count-board {
  min-width: fit-content;
}

.count-row {
  display: flex;
  align-items: stretch;
  min-width: fit-content;
  border-bottom: 1px solid #edf2f7;
}

.count-row--header {
  position: sticky;
  top: 0;
  z-index: 12;
}

.count-meta {
  position: sticky;
  left: 0;
  z-index: 4;
  width: 320px;
  min-width: 320px;
  padding: 14px 16px;
  border-right: 1px solid #edf2f7;
  background: #ffffff;
}

.count-meta--header {
  z-index: 13;
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  background: #f8fafc;
}

.count-meta__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.count-meta__name {
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
  color: #0f172a;
}

.count-meta__summary {
  margin-top: 8px;
  font-size: 13px;
  line-height: 20px;
  color: #334155;
}

.count-meta__stats {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  font-size: 12px;
  line-height: 18px;
  color: #64748b;
}

.count-timeline {
  position: relative;
}

.count-timeline--header {
  display: flex;
  background: #f8fafc;
}

.count-cell-header {
  width: 24px;
  min-width: 24px;
  padding: 10px 0 8px;
  text-align: center;
  border-right: 1px solid #edf2f7;
  color: #334155;
  font-size: 11px;
  line-height: 16px;
  font-weight: 600;
}

.count-timeline--body {
  height: 62px;
}

.count-grid {
  position: absolute;
  inset: 0;
  display: flex;
}

.count-grid__cell {
  width: 24px;
  min-width: 24px;
  border-right: 1px solid #f1f5f9;
}

.count-lane {
  position: relative;
  height: 62px;
}

.count-lane__empty {
  position: absolute;
  left: 10px;
  top: 22px;
  font-size: 11px;
  line-height: 16px;
  color: #94a3b8;
}

.count-bar {
  position: absolute;
  inset: 10px 0 10px 0;
}

.count-bar__segment {
  position: absolute;
  top: 0;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.count-bar__segment--not_run {
  background: linear-gradient(90deg, #64748b 0%, #94a3b8 100%);
}

.count-bar__segment--pass {
  background: linear-gradient(90deg, #15803d 0%, #22c55e 100%);
}

.count-bar__segment--fail {
  background: linear-gradient(90deg, #b91c1c 0%, #ef4444 100%);
}

.count-bar__segment--block {
  background: linear-gradient(90deg, #b45309 0%, #f59e0b 100%);
}

.count-bar__segment--not_test {
  background: #6b7280;
}

.count-bar__label {
  padding: 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dimension-tabs {
  margin-left: auto;
  flex: none;
}

.member-count-meta__requirements {
  margin-top: 8px;
  font-size: 12px;
  line-height: 18px;
  color: #334155;
}

.member-count-timeline {
  position: relative;
}

.member-count-bar {
  position: absolute;
  top: 10px;
  height: 42px;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.member-count-bar .count-bar__segment {
  top: 0;
  height: 42px;
  border-radius: 0;
  box-shadow: none;
}

.member-count-bar__label {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(15, 23, 42, 0.24);
  pointer-events: none;
}

.member-count-bar__role {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  font-size: 11px;
  line-height: 16px;
  font-weight: 700;
}

.member-count-bar__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-count-bar__metrics {
  flex: none;
  font-size: 11px;
  line-height: 16px;
  font-weight: 700;
  opacity: 0.92;
  white-space: nowrap;
}

.member-count-bar__compact-label {
  position: absolute;
  top: -18px;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 168px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.88);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
  pointer-events: none;
}

.member-count-bar__compact-text,
.member-count-bar__compact-metrics {
  font-size: 11px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.member-count-bar__compact-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.dimension-tabs .el-tabs__header) {
  margin: 0;
}

:deep(.dimension-tabs .el-tabs__content) {
  display: none;
}

:deep(.dimension-tabs .el-tabs__nav-wrap::after) {
  background-color: transparent;
}

:deep(.testing-group-tabs .el-tabs__header) {
  margin: 0;
}

:deep(.testing-group-tabs .el-tabs__nav-wrap::after) {
  background-color: #e2e8f0;
}

:deep(.testing-group-tabs .el-tabs__content) {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

:deep(.testing-group-tabs .el-tab-pane) {
  height: 100%;
}

@media (max-width: 768px) {
  .testing-overview-panel {
    padding: 12px 12px 16px;
  }

  .group-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .dimension-tabs {
    margin-left: 0;
    align-self: flex-end;
  }

  .count-meta {
    width: 260px;
    min-width: 260px;
  }

  .testing-legend,
  .group-summary {
    gap: 8px;
  }

  .group-summary-card {
    min-width: 112px;
  }
}
</style>
