<template>
  <div ref="pageNodeContentRef" class="page-node-content" @click.stop="selectPageNode">
    <div class="page-node-header" @pointerdown="startDragPageNode">
      <div class="page-title">
        <span class="page-icon">P</span>
        <span class="page-name">{{ pageName }}</span>
      </div>
      <div class="page-stats">
        <span class="page-stat">{{ interactiveCount }} 元素</span>
        <span class="page-stat">{{ innerComponents.length }} 组件</span>
      </div>
    </div>

      <div
        v-if="nodeExecutionResult"
        class="execution-result-strip"
        data-execution-result-key="node"
        @pointerdown.stop.prevent
        @wheel.stop
        @click.stop.prevent
      >
        <button
          class="execution-result-toggle"
          type="button"
        @pointerdown.stop.prevent="handleExecutionResultPointerDown($event, 'node')"
        @click.stop.prevent
      >
        <span class="execution-result-icon" :class="`execution-result-icon-${nodeExecutionResult.status}`"></span>
        <span>{{ formatExecutionStatus(nodeExecutionResult.status) }}</span>
      </button>
    </div>

    <div class="page-node-body">
      <div v-if="!hasSnapshot" class="empty-state">
        <div class="empty-icon">YML</div>
        <p>未绑定快照文件</p>
        <p class="empty-hint">在右侧节点详情中选择页面名称后自动绑定快照</p>
      </div>

      <div v-else class="component-canvas">
        <div v-if="innerComponents.length === 0" class="empty-state mapped-empty">
          <div class="empty-icon">UI</div>
          <p>页面已解析，暂无映射组件</p>
          <p class="empty-hint">从左侧组件库拖拽组件到当前页面节点或 iframe 容器内</p>
        </div>
      </div>
    </div>

    <div
      v-if="hasSnapshot && innerComponents.length > 0"
      class="component-overlay"
    >
      <svg
        v-if="executionConnectionLines.length > 0"
        class="execution-connection-layer"
        :viewBox="`0 0 ${getNodeSize().width} ${getNodeSize().height}`"
        preserveAspectRatio="none"
      >
        <defs>
          <marker
            :id="connectionMarkerId"
            markerWidth="12"
            markerHeight="12"
            refX="10"
            refY="5"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M0,0 L10,5 L0,10 z" class="execution-connection-marker" />
          </marker>
        </defs>
        <g
          v-for="line in executionConnectionLines"
          :key="line.id"
          class="execution-connection-item"
          @click.stop="selectExecutionConnection(line.index)"
        >
          <path class="execution-connection-halo" :d="line.path" />
          <path
            class="execution-connection-path"
            :d="line.path"
            :marker-end="`url(#${connectionMarkerId})`"
          />
          <text
            v-if="line.label"
            class="execution-connection-label"
            :x="line.labelX"
            :y="line.labelY"
          >
            {{ line.label }}
          </text>
        </g>
      </svg>
      <div
        v-for="layout in componentLayouts"
        :key="layout.component.id"
        class="flow-component"
        :class="[
          `flow-component-${layout.component.type}`,
          {
            'flow-component-iframe': layout.component.type === 'iframe',
            dragging: draggingComponentId === layout.component.id
          }
        ]"
        :data-component-id="layout.component.id"
        :style="getComponentStyle(layout)"
        @pointerdown="(e) => startDragComponent(e, layout)"
        @mousedown.stop.prevent
        @click.stop="selectInnerComponent(layout.component)"
        :title="`拖动调整 ${getComponentTypeName(layout.component.type)} 位置`"
      >
        <div v-if="layout.component.type === 'iframe'" class="iframe-shell">
          <div class="iframe-header">
            <span class="iframe-badge">IFRAME</span>
            <span class="iframe-title">{{ getComponentLabel(layout.component) }}</span>
          </div>
          <div class="iframe-body">
            <div class="iframe-hint">可在该区域内继续摆放组件</div>
          </div>
        </div>

        <div v-else class="component-shell">
          <div class="component-shell-header">
            <span class="component-shell-title-group">
              <span class="flow-component-icon">{{ getComponentIcon(layout.component.type) }}</span>
              <span class="component-shell-title">{{ getComponentTypeName(layout.component.type) }}</span>
            </span>
            <span class="component-shell-action">{{ getComponentActionBadgeText(layout.component) }}</span>
          </div>

          <div class="component-shell-preview">
            <div
              v-if="layout.component.type === 'input'"
              class="component-preview-input"
              :class="{
                'is-reference': layout.component.config?.inputMode === 'reference',
                'is-placeholder': !getInputPreviewValue(layout.component)
              }"
            >
              {{ getInputPreviewValue(layout.component) || getInputPlaceholder(layout.component) }}
            </div>

            <button
              v-else-if="layout.component.type === 'button'"
              class="component-preview-button"
              type="button"
            >
              {{ getButtonPreviewText(layout.component) }}
            </button>

            <div v-else-if="layout.component.type === 'select'" class="component-preview-select">
              <span class="component-preview-select-value">{{ getSelectPreviewValue(layout.component) }}</span>
              <span class="component-preview-caret">▾</span>
            </div>

            <div v-else-if="layout.component.type === 'checkbox'" class="component-preview-checkbox">
              <span
                class="component-preview-checkbox-box"
                :class="{ checked: Boolean(layout.component.config?.checked) }"
              >
                <span v-if="layout.component.config?.checked">✓</span>
              </span>
              <span class="component-preview-checkbox-text">{{ getCheckboxPreviewText(layout.component) }}</span>
            </div>

            <div v-else-if="layout.component.type === 'radio'" class="component-preview-checkbox component-preview-radio">
              <span
                class="component-preview-checkbox-box component-preview-radio-dot"
                :class="{ checked: Boolean(layout.component.config?.checked) }"
              >
                <span v-if="layout.component.config?.checked"></span>
              </span>
              <span class="component-preview-checkbox-text">{{ getRadioPreviewText(layout.component) }}</span>
            </div>

            <a
              v-else-if="layout.component.type === 'link'"
              href="javascript:void(0)"
              class="component-preview-link"
            >
              {{ getLinkPreviewText(layout.component) }}
            </a>

            <div v-else-if="layout.component.type === 'file'" class="component-preview-file">
              <span class="component-preview-file-button">选择文件</span>
              <span class="component-preview-file-name">{{ getFilePreviewText(layout.component) }}</span>
            </div>

            <div v-else class="component-preview-generic">
              {{ getComponentLabel(layout.component) }}
            </div>
          </div>

          <div v-if="getComponentCaption(layout.component)" class="component-shell-caption">
            {{ getComponentCaption(layout.component) }}
          </div>
        </div>
      </div>

      <div
        v-for="layout in componentExecutionLayouts"
        :key="`execution-${layout.component.id}`"
        class="component-execution-result"
        :class="`component-execution-result-${getComponentExecutionResult(layout.component).status}`"
        :data-execution-result-key="layout.component.id"
        :style="getComponentExecutionResultStyle(layout)"
        @click.stop.prevent
        @mousedown.stop
        @mouseup.stop
        @pointerdown.stop.prevent="handleExecutionResultPointerDown($event, layout.component.id)"
        @pointerup.stop
        @wheel.stop
        @dblclick.stop
      >
        <button
          class="component-execution-toggle"
          type="button"
          @pointerdown.stop.prevent="handleExecutionResultPointerDown($event, layout.component.id)"
          @click.stop.prevent
        >
          <span
            class="execution-result-icon"
            :class="`execution-result-icon-${getComponentExecutionResult(layout.component).status}`"
          ></span>
          <span>{{ formatExecutionStatus(getComponentExecutionResult(layout.component).status) }}</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-for="detail in []"
        :key="`floating-execution-${detail.key}`"
        class="floating-execution-detail"
        :class="`floating-execution-detail-${normalizeExecutionStatus(detail.result.status)}`"
        :style="detail.style"
        tabindex="0"
        @click.stop
        @mousedown.stop
        @pointerdown.stop
        @wheel.stop
      >
        <div v-if="hasExecutionPayload(detail.result.input)" class="execution-payload">
          <span>输入</span>
          <pre>{{ formatExecutionPayload(detail.result.input) }}</pre>
        </div>
        <div v-if="hasExecutionPayload(detail.result.output)" class="execution-payload">
          <span>输出</span>
          <pre>{{ formatExecutionPayload(detail.result.output) }}</pre>
        </div>
        <div v-if="detail.result.errorLog" class="execution-payload execution-payload-error">
          <span>失败日志</span>
          <pre>{{ detail.result.errorLog }}</pre>
        </div>
        <button
          v-if="detail.result.screenshotUrl"
          class="execution-screenshot-button"
          type="button"
          title="查看截图"
          @click.stop="openScreenshotPreview(detail.result.screenshotUrl)"
        >
          <img
            class="execution-screenshot"
            :src="detail.result.screenshotUrl"
            alt="执行截图"
          />
        </button>
      </div>
      <div
        v-if="screenshotPreviewUrl"
        class="execution-screenshot-preview"
        @click.self="closeScreenshotPreview"
      >
        <button
          class="execution-screenshot-preview-close"
          type="button"
          title="关闭"
          @click="closeScreenshotPreview"
        >
          ×
        </button>
        <img
          class="execution-screenshot-preview-image"
          :src="screenshotPreviewUrl"
          alt="执行截图"
        />
      </div>
    </Teleport>

    <div class="page-node-footer">
      <span class="footer-text">{{ pageFooterText }}</span>
    </div>
  </div>
</template>

<script>
import { reactive } from 'vue'

const createInnerDragSession = () => ({
  nodeId: null,
  componentId: null,
  pointerId: null,
  pageElement: null,
  componentElement: null,
  startPos: { x: 0, y: 0 },
  offset: { x: 0, y: 0 },
  componentSize: { width: 0, height: 0 },
  previewPosition: null,
  moveHandler: null,
  endHandler: null
})

const innerDragSession = reactive(createInnerDragSession())
const expandedExecutionResultsStore = new Map()

const resetInnerDragSession = () => {
  Object.assign(innerDragSession, createInnerDragSession())
}
</script>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  buildPageNodePorts,
  buildComponentLayouts,
  getComponentActionText,
  getComponentDisplayText,
  getComponentIcon,
  getComponentSize,
  getPageInnerRect,
  getComponentTypeName,
  normalizeExecutionConnectionPorts,
  normalizeIframePortId
} from './visualFlowUtils'

const props = defineProps({
  node: {
    type: Object,
    default: () => ({})
  }
})

// 拖动状态
const isCurrentNodeDragging = () => innerDragSession.nodeId === props.node?.id
const draggingComponentId = computed(() => isCurrentNodeDragging() ? innerDragSession.componentId : null)
const dragPreviewPosition = computed(() => isCurrentNodeDragging() ? innerDragSession.previewPosition : null)

const nodeData = computed(() => props.node?.data || {})
const config = computed(() => nodeData.value.config || {})
const expandedExecutionResults = computed({
  get() {
    const key = props.node?.id || '__unknown__'
    return expandedExecutionResultsStore.get(key) || {}
  },
  set(value) {
    const key = props.node?.id || '__unknown__'
    expandedExecutionResultsStore.set(key, value || {})
  }
})
const pageName = computed(() => config.value.pageName || config.value.name || '页面节点')
const snapshotName = computed(() => config.value.snapshotFile || '')
const hasSnapshot = computed(() => Boolean(config.value.snapshotData))
const interactiveCount = computed(() => config.value.snapshotData?.interactiveElements?.length || 0)
const pageFooterText = computed(() => {
  const path = config.value.recordingPagePath || ''
  const snapshotCount = config.value.snapshotData?.metadata?.snapshotCount || 0
  if (path && snapshotCount > 1) return `${path} · ${snapshotCount} 个快照`
  if (path) return path
  return snapshotName.value || '未选择快照'
})
const innerComponents = computed(() => {
  const components = config.value.innerComponents || []
  return [...components].sort((a, b) => (a.order ?? a.zIndex ?? 0) - (b.order ?? b.zIndex ?? 0))
})
const nodeExecutionResult = computed(() => config.value.executionResult || null)
const pageNodeContentRef = ref(null)
const screenshotPreviewUrl = ref('')
const floatingExecutionAnchors = ref({})
const getNodeSize = () => props.node?.getSize?.() || props.node?.size || { width: 320, height: 450 }
const componentLayouts = computed(() =>
  buildComponentLayouts(innerComponents.value, getNodeSize())
)
const componentExecutionLayouts = computed(() =>
  componentLayouts.value.filter(layout => getComponentExecutionResult(layout.component))
)
const connectionMarkerId = computed(() => {
  const nodeId = String(props.node?.id || 'page-node').replace(/[^A-Za-z0-9_-]/g, '-')
  return `page-node-connection-arrow-${nodeId}`
})

const resolvePortSide = (sourcePort, targetPort) => {
  const source = sourcePort.args || {}
  const target = targetPort.args || {}
  const dx = (target.x || 0) - (source.x || 0)
  const dy = (target.y || 0) - (source.y || 0)
  const horizontalFirst = Math.abs(dx) >= Math.abs(dy)

  if (horizontalFirst) {
    return {
      source: dx >= 0 ? 'right' : 'left',
      target: dx >= 0 ? 'left' : 'right'
    }
  }

  return {
    source: dy >= 0 ? 'bottom' : 'top',
    target: dy >= 0 ? 'top' : 'bottom'
  }
}

const getSideVector = side => {
  if (side === 'left') return { x: -1, y: 0 }
  if (side === 'right') return { x: 1, y: 0 }
  if (side === 'top') return { x: 0, y: -1 }
  if (side === 'bottom') return { x: 0, y: 1 }
  return { x: 1, y: 0 }
}

const buildConnectionPath = (sourcePort, targetPort) => {
  const source = sourcePort.args || {}
  const target = targetPort.args || {}
  const sourceX = source.x || 0
  const sourceY = source.y || 0
  const targetX = target.x || 0
  const targetY = target.y || 0
  const visibleSides = {
    source: sourcePort?.data?.side || resolvePortSide(sourcePort, targetPort).source,
    target: targetPort?.data?.side || resolvePortSide(sourcePort, targetPort).target
  }
  const sourceVector = getSideVector(visibleSides.source)
  const targetVector = getSideVector(visibleSides.target)
  const dx = targetX - sourceX
  const dy = targetY - sourceY
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)
  const sameRow = absDy <= 18
  const sameColumn = absDx <= 18
  const sourceCurve = Math.max(42, Math.min(150, sameRow ? absDx * 0.45 : Math.max(absDx, absDy) * 0.35))
  const targetCurve = Math.max(sameRow ? 42 : 58, Math.min(170, sameColumn ? absDy * 0.45 : Math.max(absDx, absDy) * 0.42))
  const sourceDirectionSign = sourcePort?.data?.direction === 'in' ? -1 : 1
  const targetDirectionSign = targetPort?.data?.direction === 'in' ? 1 : -1
  const c1x = sourceX + sourceVector.x * sourceCurve * sourceDirectionSign
  const c1y = sourceY + sourceVector.y * sourceCurve * sourceDirectionSign
  const c2x = targetX + targetVector.x * targetCurve * targetDirectionSign
  const c2y = targetY + targetVector.y * targetCurve * targetDirectionSign

  return `M ${sourceX} ${sourceY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${targetX} ${targetY}`
}

const getConnectionLabel = (step) => {
  const label = step?.action || step?.from?.elementText || ''
  return String(label || '').slice(0, 18)
}

const normalizeExecutionStatus = status => {
  const normalized = String(status || '').toLowerCase()
  if (['success', 'passed', 'pass'].includes(normalized)) return 'success'
  if (['failed', 'fail', 'error'].includes(normalized)) return 'failed'
  if (normalized === 'running') return 'running'
  return normalized || 'pending'
}

const formatExecutionStatus = status => {
  const normalized = normalizeExecutionStatus(status)
  if (normalized === 'success') return '执行成功'
  if (normalized === 'failed') return '执行失败'
  if (normalized === 'running') return '执行中'
  return '待执行'
}

const getComponentExecutionResult = component => component?.executionResult || null
const getExecutionResultByKey = (key) => {
  if (key === 'node') {
    return nodeExecutionResult.value
  }
  const component = innerComponents.value.find(item => item.id === key)
  return getComponentExecutionResult(component)
}

const escapeDomAttributeValue = value => {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
    return CSS.escape(String(value || ''))
  }
  return String(value || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

const findExecutionAnchorElement = (key) => {
  const root = pageNodeContentRef.value
  if (!root || !key) {
    return null
  }
  return root.querySelector(`[data-execution-result-key="${escapeDomAttributeValue(key)}"]`)
}

const buildAnchorFromElement = (element) => {
  const rect = element?.getBoundingClientRect?.()
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    return null
  }
  return {
    left: rect.left,
    top: rect.bottom,
    width: Math.max(rect.width, 280)
  }
}

const resolveFloatingExecutionAnchor = (key) => {
  const currentAnchor = buildAnchorFromElement(findExecutionAnchorElement(key))
  return currentAnchor || floatingExecutionAnchors.value[key] || null
}

const buildFloatingExecutionStyle = (anchor) => {
  if (!anchor) {
    return null
  }

  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1280
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720
  const width = Math.max(260, Math.min(anchor.width || 320, 520, viewportWidth - 24))
  const left = Math.max(12, Math.min(anchor.left, viewportWidth - width - 12))
  const preferredTop = (anchor.top || 0) + 8
  const maxTop = Math.max(12, viewportHeight - 160)
  const top = Math.max(12, Math.min(preferredTop, maxTop))

  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`
  }
}

const floatingExecutionDetails = computed(() =>
  Object.entries(expandedExecutionResults.value)
    .filter(([, expanded]) => expanded)
    .map(([key]) => {
      const anchor = resolveFloatingExecutionAnchor(key)
      return {
        key,
        result: getExecutionResultByKey(key),
        style: buildFloatingExecutionStyle(anchor)
      }
    })
    .filter(detail => detail.result && detail.style)
)

const setFloatingExecutionAnchor = (key, event) => {
  if (!key || typeof window === 'undefined') {
    return
  }

  const sourceElement = event?.currentTarget?.closest?.('.execution-result-strip, .component-execution-result') || event?.currentTarget
  const anchor = buildAnchorFromElement(sourceElement) || buildAnchorFromElement(findExecutionAnchorElement(key))
  if (!anchor) {
    return
  }

  floatingExecutionAnchors.value = {
    ...floatingExecutionAnchors.value,
    [key]: anchor
  }
}

const clearFloatingExecutionAnchor = (key) => {
  if (!key || !floatingExecutionAnchors.value[key]) {
    return
  }

  const nextAnchors = { ...floatingExecutionAnchors.value }
  delete nextAnchors[key]
  floatingExecutionAnchors.value = nextAnchors
}

const notifyExecutionResultVisibility = (key, expanded, options = {}) => {
  window.dispatchEvent(new CustomEvent('testhub-flow-execution-result-expanded', {
    detail: {
      nodeId: props.node?.id || '',
      key,
      expanded: Boolean(expanded),
      detailOnly: Boolean(options.detailOnly)
    }
  }))
}

const openExecutionResultDetailPanel = (key) => {
  if (!key || !getExecutionResultByKey(key)) {
    return
  }

  expandedExecutionResults.value = {
    ...expandedExecutionResults.value,
    [key]: false
  }
  clearFloatingExecutionAnchor(key)
  notifyExecutionResultVisibility(key, true, { detailOnly: true })
}

const toggleExecutionResult = (key, forceExpanded = null, event = null) => {
  const nextExpanded = forceExpanded === null
    ? !expandedExecutionResults.value[key]
    : Boolean(forceExpanded)
  expandedExecutionResults.value = {
    ...expandedExecutionResults.value,
    [key]: nextExpanded
  }
  if (nextExpanded) {
    setFloatingExecutionAnchor(key, event)
  } else {
    clearFloatingExecutionAnchor(key)
  }
  notifyExecutionResultVisibility(key, nextExpanded)
}

const handleExecutionResultPointerDown = (event, key) => {
  event?.preventDefault?.()
  event?.stopPropagation?.()

  const target = event?.target
  if (target?.closest?.('.floating-execution-detail')) {
    return
  }

  openExecutionResultDetailPanel(key)
}

const openScreenshotPreview = (url) => {
  screenshotPreviewUrl.value = url || ''
}

const closeScreenshotPreview = () => {
  screenshotPreviewUrl.value = ''
}

const isExecutionResultExpanded = key => Boolean(expandedExecutionResults.value[key])

const hasExecutionPayload = payload => {
  if (!payload || typeof payload !== 'object') return false
  return Object.keys(payload).length > 0
}

const formatExecutionPayload = payload => {
  try {
    return JSON.stringify(payload || {}, null, 2)
  } catch (error) {
    return String(payload || '')
  }
}

const executionConnectionLines = computed(() => {
  const executionPath = Array.isArray(config.value.executionPath) ? config.value.executionPath : []
  if (!executionPath.length) {
    return []
  }

  const { ports } = buildPageNodePorts(getNodeSize(), innerComponents.value)
  const portMap = new Map(ports.map(port => [port.id, port]))

  return executionPath
    .map((step, index) => {
      const sourcePortId = normalizeIframePortId(step?.from?.portId, innerComponents.value)
      const targetPortId = normalizeIframePortId(step?.to?.portId, innerComponents.value)
      const sourcePort = portMap.get(sourcePortId)
      const targetPort = portMap.get(targetPortId)
      if (!sourcePort || !targetPort) {
        return null
      }

      const normalizedPorts = normalizeExecutionConnectionPorts(sourcePort, targetPort)
      const lineSourcePort = normalizedPorts.sourcePort
      const lineTargetPort = normalizedPorts.targetPort
      const source = lineSourcePort.args || {}
      const target = lineTargetPort.args || {}
      return {
        id: `${sourcePortId || 'source'}-${targetPortId || 'target'}-${index}`,
        index,
        path: buildConnectionPath(lineSourcePort, lineTargetPort),
        label: getConnectionLabel(step),
        labelX: ((source.x || 0) + (target.x || 0)) / 2,
        labelY: ((source.y || 0) + (target.y || 0)) / 2 - 8
      }
    })
    .filter(Boolean)
})

const getComponentLabel = (component) => {
  const text = getComponentDisplayText(component)
  return text || ''
}

const getComponentShortLabel = (component, length = 18) => {
  const text = getComponentLabel(component)
  return text.length > length ? `${text.slice(0, length)}...` : text
}

const normalizeDisplayText = value => String(value ?? '').replace(/\s+/g, ' ').trim()

const getComponentPreviewText = (component) => {
  if (!component) return ''
  if (component.type === 'input') {
    return getInputPreviewValue(component) || getInputPlaceholder(component)
  }
  if (component.type === 'button') return getButtonPreviewText(component)
  if (component.type === 'select') return getSelectPreviewValue(component)
  if (component.type === 'checkbox') return getCheckboxPreviewText(component)
  if (component.type === 'radio') return getRadioPreviewText(component)
  if (component.type === 'link') return getLinkPreviewText(component)
  if (component.type === 'file') return getFilePreviewText(component)
  return getComponentLabel(component)
}

const getComponentActionBadgeText = (component) => {
  const action = component?.config?.action || ''
  const actionMap = {
    fill: '填充',
    press: '按键',
    click: '单击',
    dblclick: '双击',
    contextmenu: '右键',
    hover: '悬停',
    select: '选择',
    check: component?.config?.checked === false ? '取消勾选' : '勾选',
    setInputFiles: '上传'
  }
  return actionMap[action] || getComponentActionText(component)
}

const getComponentCaption = (component) => {
  const label = normalizeDisplayText(getComponentLabel(component))
  if (!label) return ''

  const previewText = normalizeDisplayText(getComponentPreviewText(component))
  if (previewText && (previewText === label || previewText.includes(label) || label.includes(previewText))) {
    return ''
  }

  return label
}

const getInputPreviewValue = (component) => {
  if (component?.config?.inputMode === 'reference') {
    return component.config?.inputReference ? `{{${component.config.inputReference}}}` : ''
  }
  const value = normalizeDisplayText(component?.config?.value)
  const inputValue = normalizeDisplayText(component?.config?.inputValue)
  if (value && inputValue && value !== inputValue) {
    return value.includes(inputValue) ? value : inputValue.includes(value) ? inputValue : value
  }
  return value || inputValue || ''
}

const getInputPlaceholder = (component) => {
  const placeholder = normalizeDisplayText(component?.config?.placeholder || component?.elementData?.attributes?.placeholder)
  if (placeholder) {
    return placeholder
  }
  return '输入内容'
}

const getButtonPreviewText = (component) => {
  return getComponentLabel(component) || '按钮'
}

const getSelectPreviewValue = (component) => {
  if (component?.config?.inputMode === 'reference') {
    return component.config?.inputReference ? `{{${component.config.inputReference}}}` : '选择变量'
  }
  return component?.config?.selectedValue || component?.elementData?.text || '请选择'
}

const getCheckboxPreviewText = (component) => {
  return getComponentLabel(component) || '复选框'
}

const getRadioPreviewText = (component) => {
  return getComponentLabel(component) || '单选框'
}

const getLinkPreviewText = (component) => {
  return getComponentLabel(component) || '链接'
}

const getFilePreviewText = (component) => {
  return component?.config?.filePath || component?.config?.inputValue || getComponentLabel(component) || '未选择'
}

const isComponentDescendantOf = (component, ancestorId) => {
  if (!component?.parentId || !ancestorId) {
    return false
  }

  const componentMap = new Map(innerComponents.value.map(item => [item.id, item]))
  let parentId = component.parentId
  while (parentId) {
    if (parentId === ancestorId) {
      return true
    }
    parentId = componentMap.get(parentId)?.parentId || null
  }
  return false
}

const getPreviewRect = (layout) => {
  const preview = dragPreviewPosition.value
  if (!preview?.componentId || !draggingComponentId.value) {
    return layout.rect
  }

  const draggingLayout = componentLayouts.value.find(item => item.component.id === preview.componentId)
  if (!draggingLayout) {
    return layout.rect
  }

  if (layout.component.id === preview.componentId) {
    return {
      ...layout.rect,
      left: preview.left,
      top: preview.top,
      right: preview.left + layout.rect.width,
      bottom: preview.top + layout.rect.height,
      centerX: preview.left + layout.rect.width / 2,
      centerY: preview.top + layout.rect.height / 2
    }
  }

  if (isComponentDescendantOf(layout.component, preview.componentId)) {
    const dx = preview.left - draggingLayout.rect.left
    const dy = preview.top - draggingLayout.rect.top
    return {
      ...layout.rect,
      left: layout.rect.left + dx,
      top: layout.rect.top + dy,
      right: layout.rect.right + dx,
      bottom: layout.rect.bottom + dy,
      centerX: layout.rect.centerX + dx,
      centerY: layout.rect.centerY + dy
    }
  }

  return layout.rect
}

const getComponentStyle = (layout) => {
  const rect = getPreviewRect(layout)
  return {
    left: `${rect.left}px`,
    top: `${rect.top}px`,
    width: `${rect.width}px`,
    height: `${rect.height}px`,
    zIndex: layout.component.type === 'iframe' ? 1 + layout.depth : 10 + layout.depth
  }
}

const getComponentExecutionResultStyle = (layout) => {
  const rect = getPreviewRect(layout)
  const top = rect.bottom

  return {
    left: `${rect.left}px`,
    top: `${top}px`,
    width: `${rect.width}px`,
    zIndex: layout.component.type === 'iframe' ? 80 + layout.depth : 90 + layout.depth
  }
}

watch(
  componentExecutionLayouts,
  layouts => {
    if (!layouts.length) {
      return
    }

    const validKeys = new Set(['node', ...layouts.map(layout => layout.component.id)])
    const nextExpanded = { ...expandedExecutionResults.value }
    const nextAnchors = { ...floatingExecutionAnchors.value }
    let changed = false

    Object.keys(nextExpanded).forEach(key => {
      if (!validKeys.has(key)) {
        delete nextExpanded[key]
        delete nextAnchors[key]
        notifyExecutionResultVisibility(key, false)
        changed = true
      }
    })

    if (changed) {
      expandedExecutionResults.value = nextExpanded
      floatingExecutionAnchors.value = nextAnchors
    }
  },
  { flush: 'post' }
)

const dispatchNodeSelect = (componentId = '') => {
  const nodeId = props.node?.id
  if (!nodeId) return
  window.dispatchEvent(new CustomEvent('testhub-flow-node-select', {
    detail: {
      nodeId,
      componentId
    }
  }))
}

const selectPageNode = () => {
  dispatchNodeSelect('')
}

const selectInnerComponent = (component) => {
  dispatchNodeSelect(component?.id || '')
}

const startDragPageNode = (event) => {
  if (event.button !== undefined && event.button !== 0) return
  if (!props.node) return

  event.preventDefault()
  event.stopPropagation()
  dispatchNodeSelect('')

  const pageElement = event.currentTarget?.closest?.('.page-node-content')
  const nodeRect = pageElement?.getBoundingClientRect?.()
  const nodeSize = getNodeSize()
  const startPosition = props.node.getPosition?.() || { x: 0, y: 0 }
  const startClient = {
    x: event.clientX,
    y: event.clientY
  }
  const scale = {
    x: nodeRect?.width ? (nodeSize.width || nodeRect.width) / nodeRect.width : 1,
    y: nodeRect?.height ? (nodeSize.height || nodeRect.height) / nodeRect.height : 1
  }
  const pointerId = event.pointerId ?? null

  const moveHandler = moveEvent => {
    if (
      pointerId !== null &&
      moveEvent.pointerId !== undefined &&
      moveEvent.pointerId !== pointerId
    ) {
      return
    }

    moveEvent.preventDefault()
    moveEvent.stopPropagation()
    props.node.setPosition?.({
      x: startPosition.x + (moveEvent.clientX - startClient.x) * scale.x,
      y: startPosition.y + (moveEvent.clientY - startClient.y) * scale.y
    })
  }

  const endHandler = endEvent => {
    if (
      pointerId !== null &&
      endEvent.pointerId !== undefined &&
      endEvent.pointerId !== pointerId
    ) {
      return
    }

    endEvent.preventDefault?.()
    endEvent.stopPropagation?.()
    document.removeEventListener('pointermove', moveHandler, true)
    document.removeEventListener('pointerup', endHandler, true)
    document.removeEventListener('pointercancel', endHandler, true)
    document.body.classList.remove('flow-page-node-header-dragging')
    window.dispatchEvent(new CustomEvent('testhub-flow-page-node-moved', {
      detail: {
        nodeId: props.node?.id || ''
      }
    }))
  }

  document.body.classList.add('flow-page-node-header-dragging')
  document.addEventListener('pointermove', moveHandler, { passive: false, capture: true })
  document.addEventListener('pointerup', endHandler, { passive: false, capture: true })
  document.addEventListener('pointercancel', endHandler, { passive: false, capture: true })
}

const selectExecutionConnection = (stepIndex) => {
  const nodeId = props.node?.id
  if (!nodeId) return
  window.dispatchEvent(new CustomEvent('testhub-flow-execution-step-select', {
    detail: {
      nodeId,
      stepIndex
    }
  }))
}

const removeDragListeners = () => {
  if (innerDragSession.moveHandler) {
    document.removeEventListener('pointermove', innerDragSession.moveHandler, true)
  }
  if (innerDragSession.endHandler) {
    document.removeEventListener('pointerup', innerDragSession.endHandler, true)
    document.removeEventListener('pointercancel', innerDragSession.endHandler, true)
    window.removeEventListener('blur', innerDragSession.endHandler)
  }
}

const findCurrentDragPageElement = () => {
  if (innerDragSession.pageElement?.isConnected) {
    return innerDragSession.pageElement
  }

  const draggingElement = document.querySelector('.flow-component.dragging')
  const pageNodeContent = draggingElement?.closest?.('.page-node-content')
  if (pageNodeContent) {
    innerDragSession.pageElement = pageNodeContent
  }
  return innerDragSession.pageElement
}

const getNodeLocalPointFromEvent = (event, pageElement = findCurrentDragPageElement()) => {
  if (!pageElement) return null

  const nodeRect = pageElement.getBoundingClientRect()
  if (!nodeRect.width || !nodeRect.height) return null

  const nodeSize = getNodeSize()
  return {
    x: (event.clientX - nodeRect.left) * ((nodeSize.width || nodeRect.width) / nodeRect.width),
    y: (event.clientY - nodeRect.top) * ((nodeSize.height || nodeRect.height) / nodeRect.height)
  }
}

// 开始拖动组件
const startDragComponent = (event, layout) => {
  if (event.button !== undefined && event.button !== 0) return
  if (!layout?.component?.id) return
  if (innerDragSession.componentId) {
    cleanupDraggingState({ force: true })
  }

  event.preventDefault()
  event.stopPropagation()

  const component = layout.component
  const componentElement = event.currentTarget
  const pageNodeContent = componentElement.closest('.page-node-content')

  if (!pageNodeContent) {
    console.error('无法找到 page-node-content 元素')
    return
  }

  const pointerLocal = getNodeLocalPointFromEvent(event, pageNodeContent)
  if (!pointerLocal) {
    return
  }

  Object.assign(innerDragSession, {
    nodeId: props.node?.id || null,
    componentId: component.id,
    pointerId: event.pointerId ?? null,
    pageElement: pageNodeContent,
    componentElement,
    startPos: {
      x: layout.rect.left,
      y: layout.rect.top
    },
    offset: {
      x: pointerLocal.x - layout.rect.left,
      y: pointerLocal.y - layout.rect.top
    },
    componentSize: {
      width: layout.rect.width,
      height: layout.rect.height
    },
    previewPosition: {
      componentId: component.id,
      left: layout.rect.left,
      top: layout.rect.top
    },
    moveHandler: handleDragMove,
    endHandler: handleDragEnd
  })

  document.body.classList.add('flow-inner-component-dragging')

  // 绑定全局事件
  document.addEventListener('pointermove', innerDragSession.moveHandler, { passive: false, capture: true })
  document.addEventListener('pointerup', innerDragSession.endHandler, { passive: false, capture: true })
  document.addEventListener('pointercancel', innerDragSession.endHandler, { passive: false, capture: true })
  window.addEventListener('blur', innerDragSession.endHandler)
}

// 拖动中
const handleDragMove = (event) => {
  if (!isCurrentNodeDragging() || !innerDragSession.componentId) return
  if (
    innerDragSession.pointerId !== null &&
    event.pointerId !== undefined &&
    event.pointerId !== innerDragSession.pointerId
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  // 如果页面元素引用丢失，尝试重新获取
  const pageElement = findCurrentDragPageElement()
  if (!pageElement) return

  const pointerLocal = getNodeLocalPointFromEvent(event, pageElement)
  if (!pointerLocal) return

  const newLeft = pointerLocal.x - innerDragSession.offset.x
  const newTop = pointerLocal.y - innerDragSession.offset.y

  innerDragSession.previewPosition = getClampedDragPreviewPosition(innerDragSession.componentId, newLeft, newTop)
}

// 结束拖动
const handleDragEnd = (event = {}) => {
  if (
    innerDragSession.pointerId !== null &&
    event.pointerId !== undefined &&
    event.pointerId !== innerDragSession.pointerId
  ) {
    return
  }

  event.preventDefault?.()
  event.stopPropagation?.()

  const commitComponentId = innerDragSession.componentId
  const commitPosition = innerDragSession.previewPosition

  // 无论如何都要清理事件监听器
  removeDragListeners()

  if (innerDragSession.pointerId !== null) {
    innerDragSession.componentElement?.releasePointerCapture?.(innerDragSession.pointerId)
  }
  document.body.classList.remove('flow-inner-component-dragging')
  resetInnerDragSession()

  if (!commitComponentId) return

  if (commitPosition) {
    updateComponentPositionByRect(commitComponentId, commitPosition.left, commitPosition.top)
  }
  dispatchNodeSelect(commitComponentId)
}

const resizeNode = (width, height) => {
  if (!props.node) return
  if (typeof props.node.resize === 'function') {
    props.node.resize(width, height)
  } else if (typeof props.node.setSize === 'function') {
    props.node.setSize({ width, height })
  }
}

const ensurePageNodeContainsRect = (rect, margin = 24) => {
  const nodeSize = getNodeSize()
  const pageInnerRect = getPageInnerRect(nodeSize)
  const overflowRight = rect.right + margin - pageInnerRect.right
  const overflowBottom = rect.bottom + margin - pageInnerRect.bottom

  if (overflowRight <= 0 && overflowBottom <= 0) {
    return nodeSize
  }

  const nextSize = {
    width: Math.ceil(nodeSize.width + Math.max(0, overflowRight)),
    height: Math.ceil(nodeSize.height + Math.max(0, overflowBottom))
  }
  resizeNode(nextSize.width, nextSize.height)
  return nextSize
}

const buildRectFromPosition = (left, top, size) => ({
  left,
  top,
  width: size.width,
  height: size.height,
  right: left + size.width,
  bottom: top + size.height
})

// 更新组件位置
const getClampedDragPreviewPosition = (componentId, left, top) => {
  const nodeSize = getNodeSize()
  const layouts = buildComponentLayouts(innerComponents.value, nodeSize)
  const componentLayout = layouts.find(layout => layout.component.id === componentId)

  if (!componentLayout) {
    return {
      componentId,
      left,
      top
    }
  }

  const parentRect = componentLayout.parentRect || getPageInnerRect(nodeSize)
  return {
    componentId,
    left: Math.max(parentRect.left + 4, left),
    top: Math.max(parentRect.top + 4, top)
  }
}

const updateComponentPositionByRect = (componentId, left, top) => {
  if (!props.node) return

  const currentData = props.node.getData()
  const currentComponents = currentData?.config?.innerComponents || []
  if (!currentComponents.length) return

  const nextComponents = currentComponents.map(component => ({
    ...component,
    position: {
      ...(component.position || {})
    },
    size: component.size ? { ...component.size } : undefined,
    config: component.config ? { ...component.config } : component.config
  }))

  // 查找并更新组件位置
  const componentIndex = nextComponents.findIndex(c => c.id === componentId)
  if (componentIndex === -1) return

  const component = nextComponents[componentIndex]
  const componentSize = getComponentSize(component)
  const margin = 24

  let nodeSize = getNodeSize()
  let layouts = buildComponentLayouts(nextComponents, nodeSize)
  let componentLayout = layouts.find(layout => layout.component.id === componentId)
  if (!componentLayout) return

  const parentComponent = component.parentId
    ? nextComponents.find(item => item.id === component.parentId && item.type === 'iframe')
    : null

  let nextLeft = left
  let nextTop = top

  if (parentComponent) {
    const parentLayout = layouts.find(layout => layout.component.id === parentComponent.id)
    const parentInnerRect = parentLayout?.innerRect

    if (parentLayout && parentInnerRect) {
      nextLeft = Math.max(parentInnerRect.left + 4, nextLeft)
      nextTop = Math.max(parentInnerRect.top + 4, nextTop)

      const desiredRect = buildRectFromPosition(nextLeft, nextTop, componentSize)
      const overflowRight = desiredRect.right + margin - parentInnerRect.right
      const overflowBottom = desiredRect.bottom + margin - parentInnerRect.bottom

      if (overflowRight > 0 || overflowBottom > 0) {
        const parentSize = getComponentSize(parentComponent)
        const nextParentSize = {
          width: Math.ceil(parentSize.width + Math.max(0, overflowRight)),
          height: Math.ceil(parentSize.height + Math.max(0, overflowBottom))
        }
        parentComponent.size = {
          ...nextParentSize
        }

        const parentFrameRect = parentLayout.parentRect || getPageInnerRect(nodeSize)
        const nextParentCenterX = parentLayout.rect.left + nextParentSize.width / 2
        const nextParentCenterY = parentLayout.rect.top + nextParentSize.height / 2
        parentComponent.position = {
          x: Math.max(0, Math.min(((nextParentCenterX - parentFrameRect.left) / parentFrameRect.width) * 100, 100)),
          y: Math.max(0, Math.min(((nextParentCenterY - parentFrameRect.top) / parentFrameRect.height) * 100, 100))
        }
      }
    }
  }

  nodeSize = getNodeSize()
  layouts = buildComponentLayouts(nextComponents, nodeSize)
  componentLayout = layouts.find(layout => layout.component.id === componentId)
  let parentRect = componentLayout?.parentRect || getPageInnerRect(nodeSize)

  if (parentComponent) {
    const parentLayout = layouts.find(layout => layout.component.id === parentComponent.id)
    if (parentLayout?.rect) {
      nodeSize = ensurePageNodeContainsRect(parentLayout.rect, margin)
      layouts = buildComponentLayouts(nextComponents, nodeSize)
      componentLayout = layouts.find(layout => layout.component.id === componentId)
      parentRect = componentLayout?.parentRect || parentRect
    }
  } else {
    nodeSize = ensurePageNodeContainsRect(buildRectFromPosition(nextLeft, nextTop, componentSize), margin)
    layouts = buildComponentLayouts(nextComponents, nodeSize)
    componentLayout = layouts.find(layout => layout.component.id === componentId)
    parentRect = componentLayout?.parentRect || getPageInnerRect(nodeSize)
  }

  nextLeft = Math.max(parentRect.left + 4, nextLeft)
  nextTop = Math.max(parentRect.top + 4, nextTop)
  const maxLeft = parentRect.right - componentSize.width - 4
  const maxTop = parentRect.bottom - componentSize.height - 4
  nextLeft = Math.min(nextLeft, Math.max(parentRect.left + 4, maxLeft))
  nextTop = Math.min(nextTop, Math.max(parentRect.top + 4, maxTop))

  const centerX = nextLeft + componentSize.width / 2
  const centerY = nextTop + componentSize.height / 2
  const percentX = ((centerX - parentRect.left) / parentRect.width) * 100
  const percentY = ((centerY - parentRect.top) / parentRect.height) * 100

  const clampedX = Math.max(0, Math.min(percentX, 100))
  const clampedY = Math.max(0, Math.min(percentY, 100))

  // 更新位置
  nextComponents[componentIndex] = {
    ...nextComponents[componentIndex],
    position: {
      x: clampedX,
      y: clampedY
    }
  }

  const nextData = {
    ...currentData,
    config: {
      ...(currentData.config || {}),
      innerComponents: nextComponents
    }
  }

  // 通知节点数据更新
  props.node.setData(nextData, { overwrite: true })
  window.dispatchEvent(new CustomEvent('testhub-flow-page-node-components-updated', {
    detail: {
      nodeId: props.node?.id || '',
      componentId
    }
  }))
}

const cleanupDraggingState = ({ force = false } = {}) => {
  if (!force && innerDragSession.nodeId && innerDragSession.nodeId !== props.node?.id) {
    return
  }

  removeDragListeners()
  if (innerDragSession.pointerId !== null) {
    innerDragSession.componentElement?.releasePointerCapture?.(innerDragSession.pointerId)
  }
  document.body.classList.remove('flow-inner-component-dragging')
  resetInnerDragSession()
}

// 处理点击 overlay 空白区域
const handleOverlayClick = (event) => {
  // 点击空白区域时不做任何操作，或者可以取消节点选择等
  event.stopPropagation()
}

// 组件卸载前清理事件监听器
onBeforeUnmount(() => {
  Object.entries(expandedExecutionResults.value || {}).forEach(([key, expanded]) => {
    if (expanded) {
      notifyExecutionResultVisibility(key, false)
    }
  })
  floatingExecutionAnchors.value = {}
  document.body.classList.remove('flow-page-node-header-dragging')
  if (isCurrentNodeDragging()) {
    return
  }
  cleanupDraggingState()
})
</script>

<style scoped>
.page-node-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 2px solid #3b82f6;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
}

.page-node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #fff;
  cursor: move;
  touch-action: none;
  user-select: none;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.page-icon {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
  font-weight: 700;
}

.page-name {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-stats {
  display: flex;
  gap: 6px;
  margin-left: 12px;
}

.page-stat {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 11px;
  white-space: nowrap;
}

.page-node-body {
  position: relative;
  flex: 1;
  padding: 12px;
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.04) 0%, rgba(37, 99, 235, 0) 100%),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: auto, 18px 18px, 18px 18px;
  overflow: hidden;
}

.execution-result-strip {
  border-bottom: 1px solid #dbeafe;
  background: #f8fafc;
}

.execution-result-toggle,
.component-execution-toggle {
  width: 100%;
  min-height: 28px;
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.execution-result-toggle {
  padding: 5px 12px;
}

.execution-result-icon {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-flex;
  flex-shrink: 0;
  background: #94a3b8;
}

.execution-result-icon-success {
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.12);
}

.execution-result-icon-failed {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
}

.execution-result-icon-running {
  background: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12);
}

.execution-result-detail,
.component-execution-detail,
.floating-execution-detail {
  padding: 8px 10px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  max-height: min(420px, 60vh);
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.floating-execution-detail {
  position: fixed;
  z-index: 10001;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.24);
  max-height: min(520px, 72vh);
}

.floating-execution-detail-success {
  border-color: #86efac;
}

.floating-execution-detail-failed {
  border-color: #fca5a5;
}

.floating-execution-detail-running {
  border-color: #fcd34d;
}

.execution-payload {
  display: grid;
  gap: 4px;
  margin-bottom: 8px;
  color: #475569;
  font-size: 11px;
}

.execution-payload span {
  font-weight: 700;
  color: #0f172a;
}

.execution-payload pre {
  margin: 0;
  padding: 6px;
  max-height: min(220px, 34vh);
  overflow: auto;
  border-radius: 6px;
  background: #f1f5f9;
  color: #334155;
  font-size: 10px;
  white-space: pre-wrap;
  word-break: break-word;
}

.execution-payload-error pre {
  max-height: min(260px, 38vh);
  background: #fef2f2;
  color: #991b1b;
}

.execution-screenshot-button {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  cursor: zoom-in;
}

.execution-screenshot {
  width: 100%;
  max-height: 120px;
  object-fit: contain;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
}

.execution-screenshot-preview {
  position: fixed;
  inset: 0;
  z-index: 10020;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: rgba(15, 23, 42, 0.78);
  cursor: zoom-out;
}

.execution-screenshot-preview-image {
  max-width: min(1280px, 92vw);
  max-height: 88vh;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  object-fit: contain;
  cursor: default;
}

.execution-screenshot-preview-close {
  position: fixed;
  top: 18px;
  right: 22px;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.65);
  color: #ffffff;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.component-canvas {
  position: relative;
  width: 100%;
  height: 100%;
}

.component-overlay {
  position: absolute;
  inset: 0;
  z-index: 30;
  pointer-events: none;
  overflow: visible;
}

.execution-connection-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 18;
  overflow: visible;
  pointer-events: none;
}

.execution-connection-item {
  pointer-events: visiblePainted;
  cursor: pointer;
}

.execution-connection-halo {
  fill: none;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 7;
  stroke-linecap: round;
  stroke-linejoin: round;
  pointer-events: stroke;
}

.execution-connection-path {
  fill: none;
  stroke: #2563eb;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 1px 2px rgba(37, 99, 235, 0.35));
  pointer-events: stroke;
}

.execution-connection-marker {
  fill: #2563eb;
}

.execution-connection-label {
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.95);
  stroke-width: 4;
  fill: #1d4ed8;
  font-size: 11px;
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: middle;
  pointer-events: auto;
  cursor: pointer;
}

.flow-component {
  position: absolute;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #dbeafe;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  pointer-events: auto;
  cursor: grab;
  transition: box-shadow 0.2s ease, transform 0.1s ease;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

.flow-component:hover {
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.15);
  transform: translateY(-1px);
}

.flow-component:active {
  cursor: grabbing;
}

.flow-component.dragging {
  cursor: grabbing !important;
  opacity: 0.8;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.2);
  z-index: 1000 !important;
  transition: none;
}

.component-shell {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 8px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  pointer-events: none;
}

.component-execution-toggle {
  min-height: 22px;
  justify-content: flex-start;
  padding: 4px 8px;
  font-size: 11px;
}

.component-execution-detail {
  padding: 8px;
  max-height: min(440px, 62vh);
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

.component-execution-result {
  position: absolute;
  border: 1px solid #cbd5e1;
  border-top: 0;
  border-radius: 0 0 8px 8px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
  pointer-events: auto;
  cursor: default;
  overflow: hidden;
}

.component-execution-result * {
  pointer-events: auto;
}

.component-execution-result-success {
  border-color: #86efac;
}

.component-execution-result-failed {
  border-color: #fca5a5;
}

.component-execution-result-running {
  border-color: #fcd34d;
}

.component-shell * {
  pointer-events: none;
}

.component-shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
  font-size: 10px;
  color: #475569;
}

.component-shell-title-group {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.component-shell-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-component-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.component-shell-preview {
  flex: 1;
  min-height: 28px;
  display: flex;
  align-items: center;
}

.component-preview-input,
.component-preview-select,
.component-preview-button,
.component-preview-link,
.component-preview-generic {
  width: 100%;
}

.component-preview-input {
  min-height: 26px;
  height: auto;
  padding: 5px 8px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  font-size: 11px;
  outline: none;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.35;
}

.component-preview-input.is-reference {
  color: #1d4ed8;
  font-style: italic;
}

.component-preview-input.is-placeholder {
  color: #94a3b8;
}

.component-preview-button {
  min-height: 28px;
  height: auto;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
  padding: 6px 8px;
}

.component-preview-select {
  min-height: 28px;
  height: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 8px;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  background: #fffbeb;
  color: #78350f;
  font-size: 11px;
}

.component-preview-select-value {
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.35;
}

.component-preview-caret {
  flex-shrink: 0;
  color: #b45309;
}

.component-preview-checkbox {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: #312e81;
  font-size: 11px;
  line-height: 1.35;
}

.component-preview-checkbox-box {
  width: 15px;
  height: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #a78bfa;
  border-radius: 4px;
  background: #fff;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.component-preview-checkbox-box.checked {
  background: #8b5cf6;
  border-color: #7c3aed;
}

.component-preview-radio-dot {
  border-radius: 50%;
}

.component-preview-radio-dot.checked {
  background: #ffffff;
  border-color: #2563eb;
}

.component-preview-radio-dot.checked span {
  width: 7px;
  height: 7px;
  display: block;
  border-radius: 50%;
  background: #2563eb;
}

.component-preview-checkbox-text {
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.component-preview-link {
  display: block;
  color: #0284c7;
  text-decoration: underline;
  font-size: 11px;
  font-weight: 600;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.35;
}

.component-preview-file {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}

.component-preview-file-button {
  flex-shrink: 0;
  padding: 4px 7px;
  border-radius: 6px;
  background: #f59e0b;
  color: #ffffff;
  font-size: 10px;
  font-weight: 600;
}

.component-preview-file-name {
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  color: #92400e;
  font-size: 11px;
  line-height: 1.35;
}

.component-preview-generic {
  min-height: 28px;
  height: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px 8px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #334155;
  font-size: 11px;
  font-weight: 600;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.35;
}

.component-shell-caption {
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.3;
  font-size: 10px;
  color: #475569;
}

.component-shell-action {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 9px;
  font-weight: 600;
}

.flow-component-input {
  border-color: #93c5fd;
}

.flow-component-button {
  border-color: #86efac;
}

.flow-component-select {
  border-color: #fcd34d;
}

.flow-component-checkbox {
  border-color: #c4b5fd;
}

.flow-component-radio {
  border-color: #93c5fd;
}

.flow-component-link {
  border-color: #67e8f9;
}

.flow-component-tab,
.flow-component-menuitem,
.flow-component-clickable {
  border-color: #bae6fd;
}

.flow-component-file {
  border-color: #fbbf24;
}

.flow-component-iframe {
  border-color: #f59e0b;
  background: rgba(255, 251, 235, 0.88);
}

.iframe-shell {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  pointer-events: none;
}

.iframe-shell * {
  pointer-events: none;
}

.iframe-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #fff;
}

.iframe-badge {
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  font-size: 10px;
  font-weight: 700;
}

.iframe-title {
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.iframe-body {
  position: relative;
  flex: 1;
  margin: 10px;
  border: 1px dashed rgba(217, 119, 6, 0.5);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
}

.iframe-hint {
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 10px;
  color: #9a3412;
}

.page-node-footer {
  display: flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.footer-text {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #64748b;
}

.mapped-empty {
  border: 1px dashed #bfdbfe;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
}

.empty-icon {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.empty-state p {
  margin: 8px 0 0;
  font-size: 13px;
}

.empty-hint {
  max-width: 220px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}
</style>
