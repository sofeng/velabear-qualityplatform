<template>
  <div
    class="requirement-overview-page"
    :class="{ 'requirement-overview-page--embedded': embedded }"
  >
    <div class="requirement-overview-panel" v-loading="loading">
      <el-empty
        v-if="!normalizedLinkedVersion"
        description="请选择版本号后查看需求总览"
      />

      <el-empty
        v-else-if="!groupedRequirements.length"
        description="当前版本暂无可展示的需求排期数据"
      />

      <el-tabs
        v-else
        v-model="activeGroupTab"
        class="overview-group-tabs"
      >
        <el-tab-pane
          v-for="group in groupedRequirements"
          :key="group.name"
          :label="`${group.name} (${group.requirements.length})`"
          :name="group.name"
        >
          <div class="overview-group-panel">
            <div class="group-toolbar">
              <div class="overview-legend overview-legend--group">
                <span class="overview-legend__item">
                  <i class="overview-legend__swatch overview-legend__swatch--status-completed" />
                  已完成
                </span>
                <span class="overview-legend__item">
                  <i class="overview-legend__swatch overview-legend__swatch--status-active" />
                  进行中
                </span>
                <span class="overview-legend__item">
                  <i class="overview-legend__swatch overview-legend__swatch--status-pending" />
                  待开始
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
                <strong class="group-summary-card__value">{{ group.requirements.length }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--green">
                <span class="group-summary-card__label">已完成</span>
                <strong class="group-summary-card__value">{{ group.completedCount }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--yellow">
                <span class="group-summary-card__label">进行中</span>
                <strong class="group-summary-card__value">{{ group.activeCount }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--red">
                <span class="group-summary-card__label">无排期</span>
                <strong class="group-summary-card__value">{{ group.noScheduleCount }}</strong>
              </div>
              <div class="group-summary-card group-summary-card--blue">
                <span class="group-summary-card__label">时间跨度</span>
                <strong class="group-summary-card__value">{{ formatGroupRange(group) }}</strong>
              </div>
            </div>

            <el-empty
              v-if="!group.timelineDays.length"
              description="该组别暂无可视化排期数据"
            />

            <template v-else-if="activeDimensionTab === 'requirement'">
              <div class="gantt-scroll">
                <div class="gantt-board">
                  <div class="gantt-row gantt-row--header">
                    <div class="gantt-meta gantt-meta--header">
                      需求 / 状态
                    </div>
                    <div
                      class="gantt-timeline gantt-timeline--header"
                      :style="buildTimelineStyle(group)"
                    >
                      <div
                        v-for="day in group.timelineDays"
                        :key="day.key"
                        class="gantt-day-header"
                        :class="{ 'gantt-day-header--weekend': day.isWeekend }"
                      >
                        <div class="gantt-day-header__date">{{ day.label }}</div>
                        <div class="gantt-day-header__week">{{ day.weekLabel }}</div>
                      </div>
                    </div>
                  </div>

                  <div
                    v-for="requirement in group.requirements"
                    :key="requirement.id"
                    class="gantt-row"
                  >
                    <div class="gantt-meta">
                      <div class="gantt-meta__top">
                        <span class="gantt-meta__issue-key">{{ requirement.issueKey }}</span>
                        <el-tag
                          size="small"
                          effect="plain"
                          :type="getStatusTagType(requirement.statusState)"
                        >
                          {{ requirement.statusText || '未设置状态' }}
                        </el-tag>
                      </div>

                      <div class="gantt-meta__summary">{{ requirement.summary || '-' }}</div>

                      <div class="gantt-meta__schedule">
                        <span>前端：{{ formatTaskRange(requirement.frontendTask) }}</span>
                        <span>后端：{{ formatTaskRange(requirement.backendTask) }}</span>
                      </div>
                    </div>

                    <div
                      class="gantt-timeline gantt-timeline--body"
                      :style="buildTimelineStyle(group)"
                    >
                      <div class="gantt-grid">
                        <span
                          v-for="day in group.timelineDays"
                          :key="`${requirement.id}-${day.key}`"
                          class="gantt-grid__cell"
                          :class="{ 'gantt-grid__cell--weekend': day.isWeekend }"
                        />
                      </div>

                      <div class="gantt-lane gantt-lane--frontend">
                        <div
                          v-if="requirement.frontendTask"
                          class="gantt-bar gantt-bar--frontend"
                          :class="`gantt-bar--${requirement.statusState}`"
                          :style="buildTaskStyle(group, requirement.frontendTask)"
                        >
                          <span class="gantt-bar__label">前端</span>
                        </div>
                        <span v-else class="gantt-lane__empty">未排期</span>
                      </div>

                      <div class="gantt-lane gantt-lane--backend">
                        <div
                          v-if="requirement.backendTask"
                          class="gantt-bar gantt-bar--backend"
                          :class="`gantt-bar--${requirement.statusState}`"
                          :style="buildTaskStyle(group, requirement.backendTask)"
                        >
                          <span class="gantt-bar__label">后端</span>
                        </div>
                        <span v-else class="gantt-lane__empty">未排期</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <el-empty
              v-else-if="!group.memberRows.length"
              description="该组别暂无可视化成员排期数据"
            />

            <div v-else class="gantt-scroll">
              <div class="member-board">
                <div class="member-board__header">
                  <div class="member-board__header-cell member-board__header-cell--member">
                    成员信息
                  </div>
                  <div class="member-board__header-cell member-board__header-cell--requirement">
                    需求信息
                  </div>
                  <div
                    class="gantt-timeline gantt-timeline--header member-board__timeline-header"
                    :style="buildTimelineStyle(group)"
                  >
                    <div
                      v-for="day in group.timelineDays"
                      :key="day.key"
                      class="gantt-day-header"
                      :class="{ 'gantt-day-header--weekend': day.isWeekend }"
                    >
                      <div class="gantt-day-header__date">{{ day.label }}</div>
                      <div class="gantt-day-header__week">{{ day.weekLabel }}</div>
                    </div>
                  </div>
                </div>

                <div
                  v-for="memberRow in group.memberRows"
                  :key="memberRow.name"
                  class="member-board__section"
                >
                  <div
                    class="member-board__member-info"
                    :style="buildMemberInfoStyle(memberRow)"
                  >
                    <div class="member-board__member-field">
                      <span class="member-board__field-label">成员姓名：</span>
                      <strong class="member-board__member-name">{{ memberRow.name }}</strong>
                    </div>
                    <div class="member-board__member-field">
                      <span class="member-board__field-label">成员归属：</span>
                      <span class="member-board__field-value">{{ memberRow.roleLabel }}</span>
                    </div>
                    <div class="member-board__member-field">
                      <span class="member-board__field-label">已完成需求数 / 总需求量：</span>
                      <span class="member-board__field-value">
                        {{ memberRow.completedRequirementCount }} / {{ memberRow.requirementCount }}
                      </span>
                    </div>
                  </div>

                  <div class="member-board__rows">
                    <div
                      v-for="memberRequirement in memberRow.requirementRows"
                      :key="memberRequirement.rowKey"
                      class="member-board__row"
                    >
                      <div class="member-board__requirement-info">
                        <div class="member-board__requirement-top">
                          <span class="member-board__requirement-key">{{ memberRequirement.issueKey }}</span>
                          <el-tag
                            size="small"
                            effect="plain"
                            :type="getStatusTagType(memberRequirement.statusState)"
                          >
                            {{ memberRequirement.statusText || '未设置状态' }}
                          </el-tag>
                        </div>
                        <div class="member-board__requirement-summary">
                          {{ memberRequirement.summary || '-' }}
                        </div>
                      </div>

                      <div
                        class="gantt-timeline member-board__timeline-row"
                        :style="buildTimelineStyle(group)"
                      >
                        <div class="gantt-grid">
                          <span
                            v-for="day in group.timelineDays"
                            :key="`${memberRow.name}-${memberRequirement.rowKey}-${day.key}`"
                            class="gantt-grid__cell"
                            :class="{ 'gantt-grid__cell--weekend': day.isWeekend }"
                          />
                        </div>

                        <div
                          class="gantt-bar member-board__progress-bar"
                          :class="`gantt-bar--${memberRequirement.statusState}`"
                          :style="buildMemberRequirementTaskStyle(group, memberRequirement.task)"
                          :title="buildMemberRequirementTitle(memberRow, memberRequirement)"
                        >
                          <span class="gantt-bar__label">{{ memberRequirement.issueKey }}</span>
                        </div>

                        <div
                          v-if="memberRequirement.delayTask"
                          class="member-board__delay-bar"
                          :style="buildMemberRequirementDelayStyle(group, memberRequirement.delayTask)"
                          :title="buildMemberDelayTitle(memberRow, memberRequirement)"
                        />
                      </div>
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
import dayjs from 'dayjs'
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
  linkedProjectId: {
    type: [Number, String, null],
    default: null,
  },
  linkedProjectName: {
    type: String,
    default: '',
  },
})

const RECORD_ENDPOINT = '/quality-analysis/reports/live-requirement-overview/'
const DAY_WIDTH = 42
const MEMBER_REQUIREMENT_ROW_HEIGHT = 84
const MEMBER_PROGRESS_BAR_TOP = 26
const MEMBER_PROGRESS_BAR_HEIGHT = 32
const NO_GROUP_LABEL = '无组别'
const WEEK_LABELS = ['日', '一', '二', '三', '四', '五', '六']
const ROLE_ORDER = Object.freeze({
  frontend: 0,
  backend: 1,
})
const ROLE_LABELS = Object.freeze({
  frontend: '前端开发',
  backend: '后端开发',
})
const TIMELINE_FIELD_CANDIDATES = Object.freeze({
  frontendStart: ['frontend_start_time', 'frontend_start_date', 'customfield_10523'],
  frontendEnd: ['frontend_end_time', 'frontend_end_date', 'customfield_11017', 'customfield_11018'],
  backendStart: ['backend_start_time', 'backend_start_date', 'customfield_10522'],
  backendEnd: ['backend_end_time', 'backend_end_date', 'customfield_11019', 'customfield_11018'],
})
const COMPLETED_STATUS_PATTERNS = [/完结/, /完成/, /已完成/, /done/i, /closed/i, /resolved/i]
const ACTIVE_STATUS_PATTERNS = [/研发中/, /开发中/, /处理中/, /联调/, /进行中/, /测试中/, /分析中/]
const PENDING_STATUS_PATTERNS = [/规划/, /待/, /未开始/]
const TODAY = dayjs().startOf('day')

const loading = ref(false)
const records = ref([])
const activeGroupTab = ref('')
const activeDimensionTab = ref('requirement')

const normalizeText = value => String(value ?? '').trim()
const normalizedLinkedVersion = computed(() => normalizeText(props.linkedVersion))

const normalizeRawFieldValue = value => {
  if (Array.isArray(value)) {
    return value
      .map(item => normalizeRawFieldValue(item))
      .filter(Boolean)
      .join(' / ')
  }

  if (value && typeof value === 'object') {
    return normalizeRawFieldValue(
      value.name ??
      value.value ??
      value.label ??
      value.displayName ??
      ''
    )
  }

  return normalizeText(value)
}

const resolveRawFieldValue = (rawFields, fieldKeys) => {
  for (const fieldKey of fieldKeys) {
    const value = normalizeRawFieldValue(rawFields?.[fieldKey])
    if (value) {
      return value
    }
  }

  return ''
}

const parseDateValue = value => {
  const normalizedValue = normalizeText(value)
  if (!normalizedValue) {
    return null
  }

  const parsedDate = dayjs(normalizedValue)
  return parsedDate.isValid() ? parsedDate.startOf('day') : null
}

const resolveStatusState = status => {
  const normalizedStatus = normalizeText(status)

  if (COMPLETED_STATUS_PATTERNS.some(pattern => pattern.test(normalizedStatus))) {
    return 'completed'
  }

  if (ACTIVE_STATUS_PATTERNS.some(pattern => pattern.test(normalizedStatus))) {
    return 'active'
  }

  if (PENDING_STATUS_PATTERNS.some(pattern => pattern.test(normalizedStatus))) {
    return 'pending'
  }

  return normalizedStatus ? 'active' : 'pending'
}

const buildTask = (startValue, endValue, statusState) => {
  let startDate = parseDateValue(startValue)
  let endDate = parseDateValue(endValue)

  if (!startDate && !endDate) {
    return null
  }

  if (!startDate && endDate) {
    startDate = endDate
  }

  if (!endDate) {
    endDate = statusState === 'active' ? dayjs().startOf('day') : startDate
  }

  if (endDate.isBefore(startDate, 'day')) {
    const temporaryDate = startDate
    startDate = endDate
    endDate = temporaryDate
  }

  return {
    startDate,
    endDate,
    startLabel: startDate.format('YYYY-MM-DD'),
    endLabel: endDate.format('YYYY-MM-DD'),
    spanDays: endDate.diff(startDate, 'day') + 1,
  }
}

const normalizeTask = task => {
  const startDate = parseDateValue(task?.startDate ?? task?.startLabel)
  const endDate = parseDateValue(task?.endDate ?? task?.endLabel)
  if (!startDate || !endDate) {
    return null
  }

  return {
    startDate,
    endDate,
    startLabel: normalizeText(task?.startLabel) || startDate.format('YYYY-MM-DD'),
    endLabel: normalizeText(task?.endLabel) || endDate.format('YYYY-MM-DD'),
    spanDays: Number(task?.spanDays) || endDate.diff(startDate, 'day') + 1,
  }
}

const buildTaskRange = (startDate, endDate) => {
  if (!startDate || !endDate) {
    return null
  }

  return {
    startDate,
    endDate,
    startLabel: startDate.format('YYYY-MM-DD'),
    endLabel: endDate.format('YYYY-MM-DD'),
    spanDays: endDate.diff(startDate, 'day') + 1,
  }
}

const sortRoles = roles => (
  [...roles].sort((left, right) => (ROLE_ORDER[left] ?? 99) - (ROLE_ORDER[right] ?? 99))
)

const getRoleLabel = role => ROLE_LABELS[role] || '未分配'

const buildMemberRoleLabel = roles => sortRoles(new Set(roles))
  .map(role => getRoleLabel(role))
  .join(' / ') || '未分配'

const getDisplayTaskEndDate = (task, statusState) => {
  if (!task?.endDate) {
    return null
  }

  if (statusState !== 'completed' && TODAY.isAfter(task.endDate, 'day')) {
    return TODAY
  }

  return task.endDate
}

const buildDelayTask = (task, statusState) => {
  if (!task?.endDate || statusState === 'completed' || !TODAY.isAfter(task.endDate, 'day')) {
    return null
  }

  return buildTaskRange(task.endDate.add(1, 'day'), TODAY)
}

const getFallbackSortDate = record => parseDateValue(record?.sortDate) || TODAY

const normalizedRequirements = computed(() => (
  records.value.map(record => {
    const statusText = normalizeText(record?.statusText)
    const statusState = normalizeText(record?.statusState) || resolveStatusState(statusText)
    const frontendTask = normalizeTask(record?.frontendTask)
    const backendTask = normalizeTask(record?.backendTask)
    const frontendDeveloper = normalizeText(record?.frontendDeveloper) || normalizeText(record?.frontend_developer)
    const backendDeveloper = normalizeText(record?.backendDeveloper) || normalizeText(record?.backend_developer)
    const earliestStartDate = [frontendTask?.startDate, backendTask?.startDate]
      .filter(Boolean)
      .sort((left, right) => left.valueOf() - right.valueOf())[0]

    return {
      id: record?.id || record?.issueKey,
      issueKey: normalizeText(record?.issueKey) || '-',
      summary: normalizeText(record?.summary),
      groupName: normalizeText(record?.groupName) || normalizeText(record?.group_name) || NO_GROUP_LABEL,
      frontendDeveloper,
      backendDeveloper,
      statusText,
      statusState,
      frontendTask,
      backendTask,
      sortDate: earliestStartDate || getFallbackSortDate(record),
      hasTimeline: Boolean(frontendTask || backendTask),
    }
  })
))

const buildTimelineDays = (startDate, endDate) => {
  if (!startDate || !endDate) {
    return []
  }

  const days = []
  let currentDate = startDate.startOf('day')

  while (currentDate.isBefore(endDate, 'day') || currentDate.isSame(endDate, 'day')) {
    days.push({
      key: currentDate.format('YYYY-MM-DD'),
      label: currentDate.format('MM/DD'),
      weekLabel: WEEK_LABELS[currentDate.day()],
      isWeekend: currentDate.day() === 0 || currentDate.day() === 6,
    })
    currentDate = currentDate.add(1, 'day')
  }

  return days
}

const buildMemberRows = requirements => {
  const memberMap = new Map()

  const addMemberTask = (memberName, role, requirement, task) => {
    if (!task) {
      return
    }

    const normalizedMemberName = normalizeText(memberName) || `未分配${role === 'frontend' ? '前端' : '后端'}`
    if (!memberMap.has(normalizedMemberName)) {
      memberMap.set(normalizedMemberName, {
        roles: new Set(),
        requirementMap: new Map(),
      })
    }

    const memberEntry = memberMap.get(normalizedMemberName)
    memberEntry.roles.add(role)

    const requirementKey = String(requirement.id || requirement.issueKey)
    if (!memberEntry.requirementMap.has(requirementKey)) {
      memberEntry.requirementMap.set(requirementKey, {
        rowKey: `${normalizedMemberName}-${requirementKey}`,
        requirementId: requirement.id,
        issueKey: requirement.issueKey,
        summary: requirement.summary,
        statusText: requirement.statusText,
        statusState: requirement.statusState,
        roles: new Set(),
        assignments: [],
      })
    }

    const requirementEntry = memberEntry.requirementMap.get(requirementKey)
    requirementEntry.roles.add(role)
    requirementEntry.assignments.push({
      role,
      roleLabel: getRoleLabel(role),
      task,
    })
  }

  requirements.forEach(requirement => {
    addMemberTask(requirement.frontendDeveloper, 'frontend', requirement, requirement.frontendTask)
    addMemberTask(requirement.backendDeveloper, 'backend', requirement, requirement.backendTask)
  })

  return Array.from(memberMap.entries())
    .map(([name, memberEntry]) => {
      const requirementRows = Array.from(memberEntry.requirementMap.values())
        .map(requirementEntry => {
          const sortedAssignments = [...requirementEntry.assignments].sort((left, right) => {
            const startDiff = left.task.startDate.valueOf() - right.task.startDate.valueOf()
            if (startDiff !== 0) {
              return startDiff
            }

            const endDiff = left.task.endDate.valueOf() - right.task.endDate.valueOf()
            if (endDiff !== 0) {
              return endDiff
            }

            return (ROLE_ORDER[left.role] ?? 99) - (ROLE_ORDER[right.role] ?? 99)
          })

          const taskStartDates = sortedAssignments.map(item => item.task.startDate)
          const taskEndDates = sortedAssignments.map(item => item.task.endDate)
          const mergedTask = buildTaskRange(
            taskStartDates.sort((left, right) => left.valueOf() - right.valueOf())[0],
            taskEndDates.sort((left, right) => right.valueOf() - left.valueOf())[0],
          )

          return {
            rowKey: requirementEntry.rowKey,
            requirementId: requirementEntry.requirementId,
            issueKey: requirementEntry.issueKey,
            summary: requirementEntry.summary,
            statusText: requirementEntry.statusText,
            statusState: requirementEntry.statusState,
            roleLabel: buildMemberRoleLabel(requirementEntry.roles),
            assignments: sortedAssignments,
            task: mergedTask,
            delayTask: buildDelayTask(mergedTask, requirementEntry.statusState),
            sortDate: mergedTask?.startDate || TODAY,
          }
        })
        .filter(item => item.task)
        .sort((left, right) => {
          const startDiff = left.sortDate.valueOf() - right.sortDate.valueOf()
          if (startDiff !== 0) {
            return startDiff
          }

          return left.issueKey.localeCompare(right.issueKey, 'zh-CN')
        })

      const earliestStartDate = requirementRows
        .map(item => item.sortDate)
        .sort((left, right) => left.valueOf() - right.valueOf())[0]

      return {
        name,
        roleLabel: buildMemberRoleLabel(memberEntry.roles),
        requirementRows,
        requirementCount: requirementRows.length,
        completedRequirementCount: requirementRows.filter(item => item.statusState === 'completed').length,
        infoHeight: Math.max(requirementRows.length, 1) * MEMBER_REQUIREMENT_ROW_HEIGHT,
        sortDate: earliestStartDate || TODAY,
      }
    })
    .filter(memberRow => memberRow.requirementCount > 0)
    .sort((left, right) => {
      const dateDiff = left.sortDate.valueOf() - right.sortDate.valueOf()
      if (dateDiff !== 0) {
        return dateDiff
      }

      return left.name.localeCompare(right.name, 'zh-CN')
    })
}

const groupedRequirements = computed(() => {
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
        const dateDiff = left.sortDate.valueOf() - right.sortDate.valueOf()
        if (dateDiff !== 0) {
          return dateDiff
        }

        return left.issueKey.localeCompare(right.issueKey, 'zh-CN')
      })

      const timelineTasks = sortedRequirements.flatMap(requirement => [requirement.frontendTask, requirement.backendTask].filter(Boolean))
      const timelineEndDates = sortedRequirements.flatMap(requirement => (
        [requirement.frontendTask, requirement.backendTask]
          .filter(Boolean)
          .map(task => getDisplayTaskEndDate(task, requirement.statusState))
          .filter(Boolean)
      ))

      const startDate = timelineTasks.length
        ? timelineTasks.map(task => task.startDate).sort((left, right) => left.valueOf() - right.valueOf())[0]
        : null
      const endDate = timelineEndDates.length
        ? timelineEndDates.sort((left, right) => right.valueOf() - left.valueOf())[0]
        : null

      return {
        name,
        requirements: sortedRequirements,
        memberRows: buildMemberRows(sortedRequirements),
        completedCount: requirements.filter(item => item.statusState === 'completed').length,
        activeCount: requirements.filter(item => item.statusState === 'active').length,
        noScheduleCount: requirements.filter(item => !item.hasTimeline).length,
        startDate,
        endDate,
        timelineDays: buildTimelineDays(startDate, endDate),
      }
    })
    .sort((left, right) => {
      const countDiff = right.requirements.length - left.requirements.length
      if (countDiff !== 0) {
        return countDiff
      }

      return left.name.localeCompare(right.name, 'zh-CN')
    })
})

const formatTaskRange = task => {
  if (!task) {
    return '未排期'
  }

  return `${task.startLabel} ~ ${task.endLabel}`
}

const formatGroupRange = group => {
  if (!group?.startDate || !group?.endDate) {
    return '暂无'
  }

  return `${group.startDate.format('MM/DD')} ~ ${group.endDate.format('MM/DD')}`
}

const getStatusTagType = statusState => {
  if (statusState === 'completed') return 'success'
  if (statusState === 'active') return 'warning'
  return 'info'
}

const buildTimelineStyle = group => ({
  width: `${Math.max(group.timelineDays.length * DAY_WIDTH, DAY_WIDTH)}px`,
})

const buildTaskStyle = (group, task) => {
  if (!group?.startDate || !task?.startDate || !task?.endDate) {
    return {}
  }

  const offsetDays = task.startDate.diff(group.startDate, 'day')
  const width = Math.max((task.spanDays * DAY_WIDTH) - 8, 18)

  return {
    left: `${(offsetDays * DAY_WIDTH) + 4}px`,
    width: `${width}px`,
  }
}

const buildMemberInfoStyle = memberRow => ({
  minHeight: `${memberRow.infoHeight}px`,
})

const buildMemberRequirementTaskStyle = (group, task) => {
  if (!group?.startDate || !task?.startDate || !task?.endDate) {
    return {}
  }

  const offsetDays = task.startDate.diff(group.startDate, 'day')
  const width = Math.max((task.spanDays * DAY_WIDTH) - 8, 18)

  return {
    left: `${(offsetDays * DAY_WIDTH) + 4}px`,
    top: `${MEMBER_PROGRESS_BAR_TOP}px`,
    width: `${width}px`,
    height: `${MEMBER_PROGRESS_BAR_HEIGHT}px`,
  }
}

const buildMemberRequirementDelayStyle = (group, delayTask) => (
  buildMemberRequirementTaskStyle(group, delayTask)
)

const buildMemberRequirementTitle = (memberRow, memberRequirement) => (
  `${memberRow.name} / ${memberRequirement.roleLabel} / ${memberRequirement.issueKey}${memberRequirement.summary ? ` / ${memberRequirement.summary}` : ''} / ${formatTaskRange(memberRequirement.task)}`
)

const buildMemberDelayTitle = (memberRow, memberRequirement) => (
  `${buildMemberRequirementTitle(memberRow, memberRequirement)} / 滞后 ${memberRequirement.delayTask?.spanDays || 0} 天`
)

const loadRequirements = async () => {
  if (!props.active) {
    return
  }

  if (!normalizedLinkedVersion.value) {
    records.value = []
    return
  }

  loading.value = true
  try {
    const response = await api.get(RECORD_ENDPOINT, {
      params: {
        version: normalizedLinkedVersion.value,
        project_id: props.linkedProjectId || undefined,
      },
    })
    records.value = Array.isArray(response.data?.requirements) ? response.data.requirements : []
  } catch (error) {
    records.value = []
    ElMessage.error(`加载需求总览失败：${error.response?.data?.detail || error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

watch(
  () => groupedRequirements.value,
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
    () => props.linkedProjectId,
  ],
  async ([active, linkedVersion], previousValues = []) => {
    const [previousActive, previousVersion, previousProjectId] = previousValues

    if (!active) {
      return
    }

    if (!linkedVersion) {
      records.value = []
      return
    }

    if (
      active !== previousActive ||
      linkedVersion !== previousVersion ||
      props.linkedProjectId !== previousProjectId
    ) {
      await loadRequirements()
    }
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.requirement-overview-page {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.requirement-overview-page--embedded {
  height: 100%;
}

.requirement-overview-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 16px 16px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.95) 0%, rgba(255, 255, 255, 1) 28%),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 34%);
}

.overview-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.overview-legend--group {
  padding-top: 2px;
}

.overview-legend__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.overview-legend__swatch {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  display: inline-flex;
  box-sizing: border-box;
}

.overview-legend__swatch--status-completed,
.overview-legend__swatch--status-active,
.overview-legend__swatch--status-pending {
  border: none;
}

.overview-legend__swatch--status-completed {
  background: linear-gradient(90deg, #15803d, #22c55e);
}

.overview-legend__swatch--status-active {
  background: linear-gradient(90deg, #b45309, #f59e0b);
}

.overview-legend__swatch--status-pending {
  background: linear-gradient(90deg, #64748b, #94a3b8);
}

.overview-group-tabs {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.overview-group-panel {
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

.gantt-scroll {
  flex: 1 1 0;
  min-height: 0;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
}

.gantt-board {
  min-width: fit-content;
}

.member-board {
  min-width: fit-content;
  --member-info-width: 240px;
  --member-requirement-width: 340px;
}

.gantt-row {
  display: flex;
  align-items: stretch;
  min-width: fit-content;
  border-bottom: 1px solid #edf2f7;
}

.gantt-row--header {
  position: sticky;
  top: 0;
  z-index: 12;
}

.gantt-meta {
  position: sticky;
  left: 0;
  z-index: 4;
  width: 320px;
  min-width: 320px;
  padding: 14px 16px;
  border-right: 1px solid #edf2f7;
  background: #ffffff;
}

.gantt-meta--header {
  z-index: 13;
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  background: #f8fafc;
}

.gantt-meta__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.gantt-meta__issue-key {
  font-size: 13px;
  font-weight: 600;
  line-height: 20px;
  color: #0f172a;
}

.gantt-meta__summary {
  margin-top: 8px;
  font-size: 13px;
  line-height: 20px;
  color: #334155;
}

.gantt-meta__schedule {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  line-height: 18px;
  color: #64748b;
}

.gantt-timeline {
  position: relative;
}

.gantt-timeline--header {
  display: flex;
  background: #f8fafc;
}

.gantt-day-header {
  width: 42px;
  min-width: 42px;
  padding: 10px 0 8px;
  text-align: center;
  border-right: 1px solid #edf2f7;
  color: #334155;
}

.gantt-day-header--weekend {
  background: #f1f5f9;
  color: #64748b;
}

.gantt-day-header__date {
  font-size: 12px;
  line-height: 18px;
  font-weight: 600;
}

.gantt-day-header__week {
  margin-top: 3px;
  font-size: 11px;
  line-height: 16px;
}

.gantt-timeline--body {
  height: 92px;
}

.gantt-grid {
  position: absolute;
  inset: 0;
  display: flex;
}

.gantt-grid__cell {
  width: 42px;
  min-width: 42px;
  border-right: 1px solid #f1f5f9;
}

.gantt-grid__cell--weekend {
  background: rgba(148, 163, 184, 0.08);
}

.gantt-lane {
  position: relative;
  height: 46px;
}

.gantt-lane--backend {
  border-top: 1px dashed #e2e8f0;
}

.gantt-lane__empty {
  position: absolute;
  left: 10px;
  top: 13px;
  font-size: 11px;
  line-height: 16px;
  color: #94a3b8;
}

.gantt-bar {
  position: absolute;
  top: 8px;
  height: 30px;
  border-radius: 999px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  overflow: hidden;
  white-space: nowrap;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
}

.gantt-bar__label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.dimension-tabs {
  margin-left: auto;
  flex: none;
}

.gantt-bar--frontend {
  background: linear-gradient(90deg, #64748b 0%, #94a3b8 100%);
}

.gantt-bar--backend {
  background: linear-gradient(90deg, #64748b 0%, #94a3b8 100%);
}

.gantt-bar--completed {
  background: linear-gradient(90deg, #15803d 0%, #22c55e 100%);
}

.gantt-bar--active {
  background: linear-gradient(90deg, #b45309 0%, #f59e0b 100%);
}

.gantt-bar--pending {
  background: linear-gradient(90deg, #64748b 0%, #94a3b8 100%);
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

:deep(.overview-group-tabs .el-tabs__header) {
  margin: 0;
}

:deep(.overview-group-tabs .el-tabs__nav-wrap::after) {
  background-color: #e2e8f0;
}

:deep(.overview-group-tabs .el-tabs__content) {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

:deep(.overview-group-tabs .el-tab-pane) {
  height: 100%;
}

.member-board__header {
  position: sticky;
  top: 0;
  z-index: 12;
  display: flex;
  align-items: stretch;
  min-width: fit-content;
}

.member-board__header-cell {
  position: sticky;
  top: 0;
  z-index: 14;
  display: flex;
  align-items: center;
  padding: 14px 16px;
  box-sizing: border-box;
  border-right: 1px solid #edf2f7;
  background: #f8fafc;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.member-board__header-cell--member {
  left: 0;
  z-index: 15;
  width: var(--member-info-width);
  min-width: var(--member-info-width);
}

.member-board__header-cell--requirement {
  left: var(--member-info-width);
  width: var(--member-requirement-width);
  min-width: var(--member-requirement-width);
}

.member-board__timeline-header {
  z-index: 13;
}

.member-board__section {
  display: flex;
  align-items: stretch;
  min-width: fit-content;
  border-bottom: 1px solid #edf2f7;
}

.member-board__member-info {
  position: sticky;
  left: 0;
  z-index: 6;
  width: var(--member-info-width);
  min-width: var(--member-info-width);
  padding: 12px 16px;
  box-sizing: border-box;
  border-right: 1px solid #edf2f7;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.member-board__member-field {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.member-board__field-label {
  color: #64748b;
  flex: none;
}

.member-board__field-value {
  color: #0f172a;
  font-weight: 500;
}

.member-board__member-name {
  color: #0f172a;
  font-size: 13px;
  line-height: 20px;
  font-weight: 600;
}

.member-board__rows {
  display: flex;
  flex-direction: column;
}

.member-board__row {
  display: flex;
  align-items: stretch;
  min-width: fit-content;
}

.member-board__row + .member-board__row {
  border-top: 1px solid #edf2f7;
}

.member-board__requirement-info {
  position: sticky;
  left: var(--member-info-width);
  z-index: 5;
  width: var(--member-requirement-width);
  min-width: var(--member-requirement-width);
  padding: 12px 16px;
  box-sizing: border-box;
  border-right: 1px solid #edf2f7;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.member-board__requirement-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.member-board__requirement-key {
  font-size: 13px;
  line-height: 20px;
  font-weight: 600;
  color: #0f172a;
}

.member-board__requirement-summary {
  margin-top: 8px;
  font-size: 13px;
  line-height: 20px;
  color: #334155;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.member-board__timeline-row {
  position: relative;
  height: 84px;
}

.member-board__progress-bar {
  z-index: 3;
  height: 32px;
}

.member-board__delay-bar {
  position: absolute;
  z-index: 2;
  border: 2px dashed #2563eb;
  border-radius: 999px;
  background: transparent;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .requirement-overview-panel {
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

  .gantt-meta {
    width: 260px;
    min-width: 260px;
  }

  .member-board {
    --member-info-width: 200px;
    --member-requirement-width: 280px;
  }

  .overview-legend,
  .group-summary {
    gap: 8px;
  }

  .group-summary-card {
    min-width: 112px;
  }
}
</style>
