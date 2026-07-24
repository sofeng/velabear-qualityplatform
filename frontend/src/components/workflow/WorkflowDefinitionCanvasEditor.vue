<template>
  <div ref="editorRootRef" class="workflow-canvas-editor" data-testid="workflow-definition-editor">
    <div class="workflow-canvas-toolbar">
      <div class="workflow-canvas-toolbar-main">
        <div class="workflow-canvas-title">流程画布</div>
        <div class="workflow-canvas-subtitle">拖拽投放审批节点、连线配置动作，并通过撤销重做与画布概览提升设计效率。</div>
      </div>
      <div class="workflow-canvas-toolbar-actions">
        <el-button
          type="primary"
          plain
          data-testid="workflow-definition-add-step"
          @click="handleAddStepNode"
        >
          新增审批节点
        </el-button>
        <el-button plain data-testid="workflow-definition-auto-layout" @click="handleAutoLayout">
          自动布局
        </el-button>
        <el-button plain data-testid="workflow-definition-fit-canvas" @click="handleFitCanvas">
          适配画布
        </el-button>
        <el-button
          plain
          :disabled="!historyState.canUndo"
          data-testid="workflow-definition-undo"
          @click="handleUndo"
        >
          撤销
        </el-button>
        <el-button
          plain
          :disabled="!historyState.canRedo"
          data-testid="workflow-definition-redo"
          @click="handleRedo"
        >
          重做
        </el-button>
        <div class="workflow-toolbar-zoom">
          <el-button plain circle data-testid="workflow-definition-zoom-out" @click="handleZoomOut">-</el-button>
          <span class="workflow-toolbar-zoom-label" data-testid="workflow-definition-zoom-label">
            {{ viewportState.zoomPercent }}%
          </span>
          <el-button plain circle data-testid="workflow-definition-zoom-in" @click="handleZoomIn">+</el-button>
        </div>
        <el-button
          plain
          type="danger"
          :disabled="!canDeleteSelection"
          data-testid="workflow-definition-delete-selected"
          @click="handleDeleteSelected"
        >
          删除选中
        </el-button>
      </div>
    </div>

    <div class="workflow-canvas-layout">
      <aside class="workflow-canvas-sidebar">
        <div class="workflow-canvas-sidecard">
          <div class="workflow-canvas-sidecard-title">节点库</div>
          <button class="workflow-palette-item workflow-palette-item-start" type="button" disabled>
            <span class="workflow-palette-dot"></span>
            <div>
              <strong>开始节点</strong>
              <span>系统固定保留，作为流程入口。</span>
            </div>
          </button>
          <button
            class="workflow-palette-item workflow-palette-item-step"
            type="button"
            data-testid="workflow-definition-palette-step"
            @mousedown.prevent="handleStepPaletteMouseDown"
          >
            <span class="workflow-palette-dot"></span>
            <div>
              <strong>审批节点</strong>
              <span>按住拖到画布中投放，或使用上方“新增审批节点”。</span>
            </div>
          </button>
          <button class="workflow-palette-item workflow-palette-item-end" type="button" disabled>
            <span class="workflow-palette-dot"></span>
            <div>
              <strong>结束节点</strong>
              <span>系统固定保留，连到此节点即表示流程结束。</span>
            </div>
          </button>
        </div>

        <div class="workflow-canvas-sidecard">
          <div class="workflow-canvas-sidecard-title">操作指引</div>
          <ol class="workflow-guide-list">
            <li>按住左侧“审批节点”拖到画布中，或点击顶部“新增审批节点”。</li>
            <li>从节点右侧圆点拖到目标节点左侧圆点，建立动作连线。</li>
            <li>选中节点或连线，在右侧填写步骤键、动作键、业务状态等属性。</li>
            <li>需要整理版式时，使用“自动布局”或直接拖动画布中的节点。</li>
            <li>快捷键：`Delete` 删除，`Ctrl/Cmd + Z` 撤销，`Ctrl/Cmd + Shift + Z` 重做。</li>
          </ol>
        </div>

        <div class="workflow-canvas-sidecard">
          <div class="workflow-canvas-sidecard-title">当前概况</div>
          <div class="workflow-stats-grid">
            <div class="workflow-stats-item">
              <span>审批节点</span>
              <strong data-testid="workflow-definition-step-count">{{ graphStats.steps }}</strong>
            </div>
            <div class="workflow-stats-item">
              <span>动作连线</span>
              <strong data-testid="workflow-definition-action-count">{{ graphStats.actions }}</strong>
            </div>
          </div>
        </div>
      </aside>

      <div class="workflow-canvas-stage">
        <div ref="containerRef" class="workflow-canvas-graph" data-testid="workflow-definition-canvas"></div>
        <div class="workflow-canvas-hint">
          连线规则：开始节点只能连出一条主线；审批节点右出左进；连到结束节点表示该动作结束流程。
        </div>
      </div>

      <aside class="workflow-canvas-inspector">
        <div class="workflow-canvas-sidecard">
          <div class="workflow-canvas-sidecard-title">属性面板</div>

          <template v-if="selectedState.kind === 'step'">
            <div class="workflow-selected-title">
              <strong>{{ stepForm.name || '未命名审批节点' }}</strong>
              <span>{{ stepForm.key || '未配置步骤键' }}</span>
            </div>
            <el-form label-position="top" class="workflow-inspector-form">
              <el-form-item label="步骤键">
                <div data-testid="workflow-definition-step-key-0">
                  <el-input
                    v-model="stepForm.key"
                    placeholder="例如 triage"
                    @input="handleStepFormChange"
                  />
                </div>
              </el-form-item>
              <el-form-item label="步骤名称">
                <div data-testid="workflow-definition-step-name-0">
                  <el-input
                    v-model="stepForm.name"
                    placeholder="例如 Defect Triage"
                    @input="handleStepFormChange"
                  />
                </div>
              </el-form-item>
              <el-form-item label="候选角色">
                <el-select
                  v-model="stepForm.candidate_roles"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择角色"
                  @change="handleStepFormChange"
                >
                  <el-option
                    v-for="item in roleOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="回退字段">
                <el-select
                  v-model="stepForm.fallback_field"
                  clearable
                  placeholder="不使用回退字段"
                  @change="handleStepFormChange"
                >
                  <el-option
                    v-for="item in fallbackOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="SLA 小时">
                <el-input-number
                  v-model="stepForm.sla_hours"
                  :min="1"
                  :max="9999"
                  controls-position="right"
                  @change="handleStepFormChange"
                />
              </el-form-item>
              <el-form-item label="启用条件">
                <el-input
                  v-model="stepForm.enabled_if"
                  placeholder="例如 need_qa_review"
                  @input="handleStepFormChange"
                />
              </el-form-item>
              <el-form-item label="业务状态">
                <el-input
                  v-model="stepForm.business_status"
                  placeholder="例如 in_progress / resolved"
                  @input="handleStepFormChange"
                />
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="selectedState.kind === 'edge'">
            <div class="workflow-selected-title">
              <strong>{{ actionForm.label || actionForm.key || '未命名动作' }}</strong>
              <span>{{ selectedEdgeSummary }}</span>
            </div>
            <el-form label-position="top" class="workflow-inspector-form">
              <el-form-item label="来源节点">
                <el-tag>{{ selectedEdgeSourceLabel }}</el-tag>
              </el-form-item>
              <el-form-item label="动作键">
                <el-input
                  v-model="actionForm.key"
                  placeholder="例如 approve"
                  @input="handleActionFormChange"
                />
              </el-form-item>
              <el-form-item label="动作名称">
                <el-input
                  v-model="actionForm.label"
                  placeholder="例如 Approve"
                  @input="handleActionFormChange"
                />
              </el-form-item>
              <el-form-item label="流向">
                <el-radio-group v-model="actionForm.target_mode" @change="handleActionTargetModeChange">
                  <el-radio label="step">下一审批节点</el-radio>
                  <el-radio label="end">结束流程</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="actionForm.target_mode === 'step'" label="目标节点">
                <el-select
                  v-model="actionForm.target_node_id"
                  placeholder="选择目标审批节点"
                  :disabled="!selectableTargetOptions.length"
                  @change="handleActionFormChange"
                >
                  <el-option
                    v-for="item in selectableTargetOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-else label="当前流向">
                <el-tag type="success">结束节点</el-tag>
              </el-form-item>
              <el-form-item label="业务状态">
                <el-input
                  v-model="actionForm.business_status"
                  placeholder="例如 closed / reopened"
                  @input="handleActionFormChange"
                />
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="selectedState.kind === 'start' || selectedState.kind === 'end'">
            <div class="workflow-fixed-hint">
              <strong>{{ selectedState.kind === 'start' ? '开始节点' : '结束节点' }}</strong>
              <span>该节点由系统固定保留，支持拖动调整位置，但不支持删除或编辑业务属性。</span>
            </div>
          </template>

          <template v-else>
            <div class="workflow-empty-inspector">
              <strong>未选中元素</strong>
              <span>点击审批节点可编辑步骤属性，点击连线可编辑动作属性。</span>
            </div>
          </template>
        </div>

        <div class="workflow-canvas-sidecard">
          <div class="workflow-canvas-sidecard-title">画布概览</div>
          <div ref="minimapContainerRef" class="workflow-minimap-container" data-testid="workflow-definition-minimap"></div>
          <div class="workflow-minimap-footer">
            <span>概览支持拖动视口和滚轮缩放，适合大流程快速定位。</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Dnd, Graph, History, Keyboard, MiniMap, Snapline } from '@antv/x6'

const START_NODE_ID = '__workflow_start__'
const END_NODE_ID = '__workflow_end__'
const START_POSITION_KEY = '__workflow_start_position__'
const END_POSITION_KEY = '__workflow_end_position__'
const SHAPE_START = 'workflow-start-node'
const SHAPE_STEP = 'workflow-step-node'
const SHAPE_END = 'workflow-end-node'
const DEFAULT_START_POSITION = Object.freeze({ x: 56, y: 210 })
const DEFAULT_END_POSITION = Object.freeze({ x: 920, y: 210 })
const DEFAULT_STEP_POSITION = Object.freeze({ x: 280, y: 210 })
const RESERVED_STEP_KEYS = new Set([START_POSITION_KEY, END_POSITION_KEY])

let workflowShapesRegistered = false

const props = defineProps({
  initialConfig: {
    type: Object,
    default: () => ({}),
  },
  roleOptions: {
    type: Array,
    default: () => [],
  },
  fallbackOptions: {
    type: Array,
    default: () => [],
  },
})

const editorRootRef = ref(null)
const containerRef = ref(null)
const minimapContainerRef = ref(null)
const selectedState = reactive({
  kind: 'none',
  cellId: '',
})
const graphStats = reactive({
  steps: 0,
  actions: 0,
})
const historyState = reactive({
  canUndo: false,
  canRedo: false,
})
const viewportState = reactive({
  zoomPercent: 100,
})

const stepForm = reactive(createEmptyStepForm())
const actionForm = reactive(createEmptyActionForm())
const graphRevision = ref(0)
const canDeleteSelection = computed(() => selectedState.kind === 'step' || selectedState.kind === 'edge')

let graph = null
let resizeObserver = null
let dnd = null
let historySuspendLevel = 0
let hydratingGraph = false
let stepSequenceCounter = 0
let edgeSequenceCounter = 0

const roleOptions = computed(() => props.roleOptions || [])
const fallbackOptions = computed(() => props.fallbackOptions || [])

const selectedEdgeCell = computed(() => {
  graphRevision.value
  if (selectedState.kind !== 'edge' || !graph) {
    return null
  }
  return graph.getCellById(selectedState.cellId) || null
})

const selectedEdgeSourceLabel = computed(() => {
  graphRevision.value
  const edge = selectedEdgeCell.value
  if (!edge) {
    return '-'
  }
  const sourceNode = edge.getSourceNode()
  return getStepLabelFromNode(sourceNode)
})

const selectedEdgeSummary = computed(() => {
  graphRevision.value
  const edge = selectedEdgeCell.value
  if (!edge) {
    return '未选中动作'
  }
  const targetNode = edge.getTargetNode()
  return isEndNode(targetNode) ? '流向结束节点' : `流向 ${getStepLabelFromNode(targetNode)}`
})

const selectableTargetOptions = computed(() => {
  graphRevision.value
  if (!graph || selectedState.kind !== 'edge') {
    return []
  }
  const edge = graph.getCellById(selectedState.cellId)
  if (!edge) {
    return []
  }
  const sourceNode = edge.getSourceNode()
  return getStepNodes()
    .filter((node) => node.id !== sourceNode?.id)
    .sort(sortNodesBySequence)
    .map((node) => ({
      value: node.id,
      label: getStepLabelFromNode(node),
    }))
})

const handleStepPaletteMouseDown = (event) => {
  if (!graph || !dnd) {
    return
  }
  const paletteNode = graph.createNode(createPaletteStepNodeConfig())
  dnd.start(paletteNode, event)
}

const handleAddStepNode = () => {
  if (!graph) {
    return
  }
  const visibleCenter = getVisibleCenter()
  graph.batchUpdate('workflow-insert-step', () => {
    graph.addNode(createStepNodeConfig(visibleCenter), {
      ui: 'toolbar-add',
    })
  })
}

const handleDeleteSelected = () => {
  if (!graph || !selectedState.cellId) {
    ElMessage.info('请先选中要删除的节点或连线')
    return
  }

  if (selectedState.kind === 'edge') {
    graph.batchUpdate('workflow-delete-edge', () => {
      const edge = graph.getCellById(selectedState.cellId)
      edge?.remove()
      clearSelection()
      reindexAllEdgeOrders()
      syncGraphState()
    })
    return
  }

  if (selectedState.kind === 'step') {
    graph.batchUpdate('workflow-delete-step', () => {
      const node = graph.getCellById(selectedState.cellId)
      node?.remove()
      clearSelection()
      reindexAllEdgeOrders()
      syncGraphState()
    })
    return
  }

  ElMessage.info('开始节点和结束节点不能删除')
}

const handleAutoLayout = () => {
  autoLayoutGraph()
  refreshSelectionStyles()
}

const handleFitCanvas = () => {
  fitCanvas()
}

const handleUndo = () => {
  if (!graph?.canUndo?.()) {
    return
  }
  graph.undo()
  syncHistoryState()
  syncGraphState()
}

const handleRedo = () => {
  if (!graph?.canRedo?.()) {
    return
  }
  graph.redo()
  syncHistoryState()
  syncGraphState()
}

const handleZoomIn = () => {
  if (!graph) {
    return
  }
  graph.zoom(0.1, { absolute: false, minScale: 0.4, maxScale: 1.8 })
  syncViewportState()
}

const handleZoomOut = () => {
  if (!graph) {
    return
  }
  graph.zoom(-0.1, { absolute: false, minScale: 0.4, maxScale: 1.8 })
  syncViewportState()
}

const handleStepFormChange = () => {
  if (!graph || selectedState.kind !== 'step') {
    return
  }
  const node = graph.getCellById(selectedState.cellId)
  if (!node) {
    return
  }

  const nextStep = sanitizeStepData(stepForm)
  graph.batchUpdate('workflow-update-step', () => {
    node.setData({
      ...node.getData(),
      step: nextStep,
    })
    applyNodePresentation(node)
    syncGraphState()
  })
}

const handleActionTargetModeChange = (value) => {
  if (value === 'end') {
    actionForm.target_node_id = ''
  } else if (!actionForm.target_node_id && selectableTargetOptions.value.length) {
    actionForm.target_node_id = selectableTargetOptions.value[0].value
  }
  handleActionFormChange()
}

const handleActionFormChange = () => {
  if (!graph || selectedState.kind !== 'edge') {
    return
  }
  const edge = graph.getCellById(selectedState.cellId)
  if (!edge) {
    return
  }

  const sourceNode = edge.getSourceNode()
  if (!sourceNode) {
    return
  }

  const nextAction = sanitizeActionData(actionForm)
  graph.batchUpdate('workflow-update-edge', () => {
    edge.setData({
      ...edge.getData(),
      key: nextAction.key,
      label: nextAction.label,
      business_status: nextAction.business_status,
    })

    if (actionForm.target_mode === 'end') {
      edge.setTarget({
        cell: END_NODE_ID,
        port: 'in',
      })
    } else if (actionForm.target_node_id) {
      edge.setTarget({
        cell: actionForm.target_node_id,
        port: 'in',
      })
    }

    edge.setData({
      ...edge.getData(),
      order: getEdgeOrder(edge),
    })

    applyEdgePresentation(edge)
    selectEdge(edge)
    reindexAllEdgeOrders()
    syncGraphState()
  })
}

const buildConfig = () => {
  if (!graph) {
    throw new Error('流程画布尚未初始化完成')
  }

  const stepNodes = getStepNodes().sort(sortNodesBySequence)
  if (!stepNodes.length) {
    throw new Error('至少需要一个审批节点')
  }

  const startNode = getStartNode()
  const startEdges = getOutgoingEdges(startNode)
  if (startEdges.length !== 1) {
    throw new Error('开始节点必须且只能连出一条主线')
  }

  const firstStepNode = startEdges[0].getTargetNode()
  if (!isStepNode(firstStepNode)) {
    throw new Error('开始节点必须连接到审批节点')
  }

  const reachable = collectReachableStepIds(firstStepNode)
  if (reachable.size !== stepNodes.length) {
    const unreachableNodes = stepNodes
      .filter((node) => !reachable.has(node.id))
      .map((node) => getStepLabelFromNode(node))
    throw new Error(`存在未接入主流程的审批节点：${unreachableNodes.join('、')}`)
  }

  const orderedNodes = orderStepNodes(firstStepNode)
  const stepKeys = new Set()
  const hasCompleteEdge = getActionEdges().some((edge) => isEndNode(edge.getTargetNode()))
  if (!hasCompleteEdge) {
    throw new Error('至少需要一条动作连到结束节点')
  }

  const steps = orderedNodes.map((node) => {
    const step = sanitizeStepData(node.getData()?.step)
    const stepLabel = step.name || step.key || '未命名审批节点'

    if (!step.key) {
      throw new Error(`审批节点“${stepLabel}”缺少步骤键`)
    }
    if (!step.name) {
      throw new Error(`步骤键 ${step.key} 缺少步骤名称`)
    }
    if (RESERVED_STEP_KEYS.has(step.key)) {
      throw new Error(`步骤键 ${step.key} 为系统保留名，请更换`)
    }
    if (stepKeys.has(step.key)) {
      throw new Error(`存在重复的步骤键：${step.key}`)
    }
    stepKeys.add(step.key)

    const outgoingEdges = getOutgoingEdges(node).sort(sortEdgesByOrder)
    if (!outgoingEdges.length) {
      throw new Error(`审批节点“${stepLabel}”至少需要一条动作连线`)
    }

    const actionKeys = new Set()
    const actions = outgoingEdges.map((edge) => {
      const action = sanitizeActionData(edge.getData())
      const targetNode = edge.getTargetNode()

      if (!action.key) {
        throw new Error(`审批节点“${stepLabel}”存在未填写动作键的连线`)
      }
      if (actionKeys.has(action.key)) {
        throw new Error(`审批节点“${stepLabel}”中存在重复动作键：${action.key}`)
      }
      actionKeys.add(action.key)

      if (isEndNode(targetNode)) {
        return {
          key: action.key,
          ...(action.label ? { label: action.label } : {}),
          complete: true,
          ...(action.business_status ? { business_status: action.business_status } : {}),
        }
      }

      if (!isStepNode(targetNode)) {
        throw new Error(`审批节点“${stepLabel}”存在无效的目标节点`)
      }

      const targetStep = sanitizeStepData(targetNode.getData()?.step)
      if (!targetStep.key) {
        throw new Error(`审批节点“${stepLabel}”指向的目标节点缺少步骤键`)
      }

      return {
        key: action.key,
        ...(action.label ? { label: action.label } : {}),
        next: targetStep.key,
        ...(action.business_status ? { business_status: action.business_status } : {}),
      }
    })

    return {
      key: step.key,
      name: step.name,
      ...(step.candidate_roles.length ? { candidate_roles: step.candidate_roles } : {}),
      ...(step.fallback_field ? { fallback_field: step.fallback_field } : {}),
      ...(step.sla_hours != null ? { sla_hours: step.sla_hours } : {}),
      ...(step.enabled_if ? { enabled_if: step.enabled_if } : {}),
      ...(step.business_status ? { business_status: step.business_status } : {}),
      actions,
    }
  })

  return {
    steps,
    editor: {
      positions: buildEditorPositions(),
    },
  }
}

defineExpose({
  buildConfig,
})

onMounted(async () => {
  await nextTick()
  initGraph()
  loadInitialConfig(props.initialConfig)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  dnd?.dispose?.()
  dnd = null
  graph?.dispose()
  graph = null
})

function initGraph() {
  if (!containerRef.value) {
    return
  }

  registerWorkflowShapes()
  graph = new Graph({
    container: containerRef.value,
    grid: {
      size: 12,
      visible: true,
      type: 'dot',
      args: {
        color: '#dbe2ea',
        thickness: 1,
      },
    },
    background: {
      color: '#f8fafc',
    },
    panning: {
      enabled: true,
      eventTypes: ['leftMouseDown', 'mouseWheel'],
    },
    mousewheel: {
      enabled: true,
      modifiers: ['ctrl', 'meta'],
      factor: 1.1,
      minScale: 0.4,
      maxScale: 1.8,
    },
    connecting: {
      snap: true,
      allowBlank: false,
      allowLoop: false,
      allowNode: false,
      allowEdge: false,
      allowPort: true,
      connector: 'rounded',
      connectionPoint: 'anchor',
      anchor: 'center',
      highlight: true,
      validateMagnet({ magnet }) {
        return magnet?.getAttribute('port-group') === 'out'
      },
      validateConnection({ sourceCell, targetCell, sourceMagnet, targetMagnet, edge }) {
        if (!sourceCell || !targetCell || !sourceMagnet || !targetMagnet) {
          return false
        }
        if (sourceCell.id === targetCell.id) {
          return false
        }
        if (sourceMagnet.getAttribute('port-group') !== 'out' || targetMagnet.getAttribute('port-group') !== 'in') {
          return false
        }

        if (isEndNode(sourceCell) || isStartNode(targetCell)) {
          return false
        }

        if (isStartNode(sourceCell)) {
          const existingStartEdges = getOutgoingEdges(sourceCell).filter((item) => item.id !== edge?.id)
          return isStepNode(targetCell) && existingStartEdges.length < 1
        }

        if (isStepNode(sourceCell)) {
          return isStepNode(targetCell) || isEndNode(targetCell)
        }

        return false
      },
      createEdge() {
        return graph.createEdge(createEdgeConfig())
      },
    },
  })

  installGraphPlugins()
  bindGraphShortcuts()

  graph.on('node:click', ({ node }) => {
    if (isStepNode(node)) {
      selectNode(node)
      return
    }
    if (isStartNode(node)) {
      selectFixedNode('start', node.id)
      return
    }
    if (isEndNode(node)) {
      selectFixedNode('end', node.id)
    }
  })

  graph.on('edge:click', ({ edge }) => {
    selectEdge(edge)
  })

  graph.on('blank:click', () => {
    clearSelection()
  })

  graph.on('node:added', ({ node, options }) => {
    if (!isStepNode(node)) {
      return
    }
    applyNodePresentation(node)
    if (hydratingGraph) {
      return
    }
    if (options?.ui === 'toolbar-add' || options?.stencil) {
      finalizeInsertedStepNode(node)
    }
  })

  graph.on('edge:connected', ({ edge }) => {
    const sourceNode = edge.getSourceNode()
    const targetNode = edge.getTargetNode()
    if (!isWorkflowConnection(sourceNode, targetNode)) {
      edge.remove()
      return
    }

    const currentData = sanitizeActionData(edge.getData())
    edge.setData({
      key: currentData.key || generateActionKey(sourceNode),
      label: currentData.label || '',
      business_status: currentData.business_status || '',
      order: currentData.order || getNextEdgeSequence(),
    })
    applyEdgePresentation(edge)
    selectEdge(edge)
    reindexAllEdgeOrders()
    syncGraphState()
  })

  graph.on('edge:removed', () => {
    syncGraphState()
  })

  graph.on('node:removed', ({ node }) => {
    if (selectedState.cellId === node.id) {
      clearSelection()
    }
    syncGraphState()
  })

  graph.on('edge:change:target', ({ edge }) => {
    applyEdgePresentation(edge)
    syncGraphState()
  })

  graph.on('history:change', () => {
    syncHistoryState()
  })

  graph.on('scale', () => {
    syncViewportState()
  })

  resizeObserver = new ResizeObserver(() => {
    resizeGraph()
  })
  resizeObserver.observe(containerRef.value)
  resizeGraph()
  syncHistoryState()
  syncViewportState()
}

function installGraphPlugins() {
  if (!graph) {
    return
  }

  graph.use(new History({ stackSize: 100 }))
  graph.use(new Keyboard({
    global: true,
    guard(e) {
      return shouldHandleGraphKeyboardEvent(e)
    },
  }))
  graph.use(new Snapline({
    enabled: true,
    sharp: true,
  }))

  if (minimapContainerRef.value) {
    minimapContainerRef.value.innerHTML = ''
    graph.use(new MiniMap({
      container: minimapContainerRef.value,
      width: 248,
      height: 156,
      padding: 8,
      scalable: true,
    }))
  }

  dnd = new Dnd({
    target: graph,
    scaled: false,
    getDropNode(_, options) {
      return options.targetGraph.createNode(createStepNodeConfig({ x: 0, y: 0 }))
    },
    validateNode(droppingNode) {
      return isStepNode(droppingNode)
    },
  })
}

function bindGraphShortcuts() {
  if (!graph?.bindKey) {
    return
  }

  graph.bindKey(['delete', 'backspace'], (event) => {
    if (!canDeleteSelection.value) {
      return
    }
    event.preventDefault()
    handleDeleteSelected()
  })

  graph.bindKey(['ctrl+z', 'meta+z'], (event) => {
    event.preventDefault()
    handleUndo()
  })

  graph.bindKey(['ctrl+shift+z', 'meta+shift+z', 'ctrl+y', 'meta+y'], (event) => {
    event.preventDefault()
    handleRedo()
  })

  graph.bindKey(['ctrl+0', 'meta+0'], (event) => {
    event.preventDefault()
    handleFitCanvas()
  })
}

function registerWorkflowShapes() {
  if (workflowShapesRegistered) {
    return
  }

  const registerNodeSafe = (name, config) => {
    try {
      Graph.registerNode(name, config, true)
    } catch {
      Graph.unregisterNode?.(name)
      Graph.registerNode(name, config, true)
    }
  }

  registerNodeSafe(SHAPE_START, {
    inherit: 'rect',
    width: 112,
    height: 56,
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'label' },
    ],
    attrs: {
      body: {
        rx: 28,
        ry: 28,
        fill: '#ecfdf3',
        stroke: '#22c55e',
        strokeWidth: 2,
      },
      label: {
        text: '开始',
        refX: '50%',
        refY: '50%',
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        fontSize: 14,
        fontWeight: 700,
        fill: '#166534',
      },
    },
    ports: {
      groups: {
        out: createPortGroup('#22c55e', 'right'),
      },
      items: [{ id: 'out', group: 'out' }],
    },
  })

  registerNodeSafe(SHAPE_STEP, {
    inherit: 'rect',
    width: 228,
    height: 108,
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'title' },
      { tagName: 'text', selector: 'subtitle' },
      { tagName: 'text', selector: 'meta' },
    ],
    attrs: {
      body: {
        rx: 18,
        ry: 18,
        fill: '#ffffff',
        stroke: '#2563eb',
        strokeWidth: 2,
      },
      title: {
        refX: '50%',
        refY: 28,
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        fontSize: 15,
        fontWeight: 700,
        fill: '#0f172a',
      },
      subtitle: {
        refX: '50%',
        refY: 56,
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        fontSize: 12,
        fill: '#475569',
      },
      meta: {
        refX: '50%',
        refY: 84,
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        fontSize: 11,
        fill: '#64748b',
      },
    },
    ports: {
      groups: {
        in: createPortGroup('#2563eb', 'left'),
        out: createPortGroup('#2563eb', 'right'),
      },
      items: [
        { id: 'in', group: 'in' },
        { id: 'out', group: 'out' },
      ],
    },
  })

  registerNodeSafe(SHAPE_END, {
    inherit: 'rect',
    width: 112,
    height: 56,
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'label' },
    ],
    attrs: {
      body: {
        rx: 28,
        ry: 28,
        fill: '#fff1f2',
        stroke: '#ef4444',
        strokeWidth: 2,
      },
      label: {
        text: '结束',
        refX: '50%',
        refY: '50%',
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        fontSize: 14,
        fontWeight: 700,
        fill: '#991b1b',
      },
    },
    ports: {
      groups: {
        in: createPortGroup('#ef4444', 'left'),
      },
      items: [{ id: 'in', group: 'in' }],
    },
  })

  workflowShapesRegistered = true
}

function createPortGroup(color, position) {
  return {
    position,
    markup: [{ tagName: 'circle', selector: 'portBody' }],
    attrs: {
      portBody: {
        r: 6,
        magnet: true,
        stroke: color,
        fill: '#ffffff',
        strokeWidth: 2,
      },
    },
  }
}

function loadInitialConfig(config = {}) {
  if (!graph) {
    return
  }

  hydratingGraph = true
  runWithoutHistory(() => {
    clearGraph()
    clearSelection(false)
    stepSequenceCounter = 0
    edgeSequenceCounter = 0

    const positions = normalizeEditorPositions(config?.editor?.positions)
    const startNode = graph.addNode({
      id: START_NODE_ID,
      shape: SHAPE_START,
      x: positions[START_POSITION_KEY]?.x ?? DEFAULT_START_POSITION.x,
      y: positions[START_POSITION_KEY]?.y ?? DEFAULT_START_POSITION.y,
      data: {
        kind: 'start',
      },
    })
    const endNode = graph.addNode({
      id: END_NODE_ID,
      shape: SHAPE_END,
      x: positions[END_POSITION_KEY]?.x ?? DEFAULT_END_POSITION.x,
      y: positions[END_POSITION_KEY]?.y ?? DEFAULT_END_POSITION.y,
      data: {
        kind: 'end',
      },
    })
    applyNodePresentation(startNode)
    applyNodePresentation(endNode)

    const normalizedSteps = normalizeSteps(config?.steps)
    const nodeByKey = new Map()

    normalizedSteps.forEach((step, index) => {
      const node = graph.addNode(
        createStepNodeConfig(
          {
            x: positions[step.key]?.x ?? DEFAULT_STEP_POSITION.x + index * 280,
            y: positions[step.key]?.y ?? DEFAULT_STEP_POSITION.y,
          },
          {
            sequence: index + 1,
            stepData: step,
          },
        ),
        {
          hydrate: true,
        },
      )
      stepSequenceCounter = Math.max(stepSequenceCounter, index + 1)
      nodeByKey.set(step.key, node)
      applyNodePresentation(node)
    })

    const orderedStepNodes = normalizedSteps
      .map((step) => nodeByKey.get(step.key))
      .filter(Boolean)

    if (!orderedStepNodes.length) {
      const node = graph.addNode(createStepNodeConfig(DEFAULT_STEP_POSITION), {
        hydrate: true,
      })
      applyNodePresentation(node)
      createStartEdge(node)
      createStepEdge(node, endNode)
    } else {
      createStartEdge(orderedStepNodes[0])
      normalizedSteps.forEach((step) => {
        const sourceNode = nodeByKey.get(step.key)
        ;(step.actions || []).forEach((action, actionIndex) => {
          const targetNode = action.complete ? endNode : nodeByKey.get(action.next)
          if (!sourceNode || !targetNode) {
            return
          }
          const edge = graph.addEdge(
            createEdgeConfig({
              source: {
                cell: sourceNode.id,
                port: 'out',
              },
              target: {
                cell: targetNode.id,
                port: 'in',
              },
              data: {
                key: String(action.key || '').trim(),
                label: String(action.label || '').trim(),
                business_status: String(action.business_status || '').trim(),
                order: actionIndex + 1,
              },
            }),
          )
          edgeSequenceCounter = Math.max(edgeSequenceCounter, actionIndex + 1)
          applyEdgePresentation(edge)
        })
      })
    }

    if (!Object.keys(positions).length) {
      autoLayoutGraph()
    } else {
      fitCanvas()
    }

    reindexAllEdgeOrders()
    syncGraphState()
    selectInitialStep()
  })
  hydratingGraph = false
  graph.cleanHistory?.()
  syncHistoryState()
  syncViewportState()
}

function normalizeSteps(steps) {
  if (!Array.isArray(steps) || !steps.length) {
    return []
  }
  return steps.map((step, index) => ({
    key: String(step?.key || '').trim() || `step_${index + 1}`,
    name: String(step?.name || '').trim() || `审批节点 ${index + 1}`,
    candidate_roles: Array.isArray(step?.candidate_roles)
      ? step.candidate_roles.map((item) => String(item || '').trim()).filter(Boolean)
      : [],
    fallback_field: String(step?.fallback_field || '').trim(),
    sla_hours:
      step?.sla_hours === '' || step?.sla_hours == null || Number.isNaN(Number(step?.sla_hours))
        ? null
        : Number(step.sla_hours),
    enabled_if: String(step?.enabled_if || '').trim(),
    business_status: String(step?.business_status || '').trim(),
    actions: Array.isArray(step?.actions)
      ? step.actions.map((action) => ({
          key: String(action?.key || '').trim(),
          label: String(action?.label || '').trim(),
          next: String(action?.next || '').trim(),
          complete: Boolean(action?.complete),
          business_status: String(action?.business_status || '').trim(),
        }))
      : [],
  }))
}

function normalizeEditorPositions(positions) {
  if (!positions || typeof positions !== 'object') {
    return {}
  }
  return Object.entries(positions).reduce((result, [key, value]) => {
    if (!value || typeof value !== 'object') {
      return result
    }
    const x = Number(value.x)
    const y = Number(value.y)
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      return result
    }
    result[key] = { x, y }
    return result
  }, {})
}

function createStepNodeConfig(position = DEFAULT_STEP_POSITION, options = {}) {
  const sequence = options.sequence ?? getNextStepSequence()
  return {
    shape: SHAPE_STEP,
    x: position.x,
    y: position.y,
    width: 228,
    height: 108,
    data: {
      kind: 'step',
      sequence,
      step: sanitizeStepData(options.stepData || createDefaultStepData(sequence)),
    },
  }
}

function createPaletteStepNodeConfig() {
  return {
    shape: SHAPE_STEP,
    x: 0,
    y: 0,
    width: 228,
    height: 108,
    data: {
      kind: 'step',
      sequence: 0,
      step: {
        key: '',
        name: '审批节点',
        candidate_roles: [],
        fallback_field: '',
        sla_hours: null,
        enabled_if: '',
        business_status: '',
      },
    },
  }
}

function clearGraph() {
  if (!graph) {
    return
  }
  graph.getCells().forEach((cell) => {
    cell.remove()
  })
}

function resizeGraph() {
  if (!graph || !containerRef.value) {
    return
  }
  const width = Math.max(containerRef.value.clientWidth, 720)
  const height = Math.max(containerRef.value.clientHeight, 480)
  graph.resize(width, height)
}

function createDefaultStepData(sequence = stepSequenceCounter + 1) {
  const stepKey = generateStepKey()
  return {
    key: stepKey,
    name: `审批节点 ${sequence}`,
    candidate_roles: [],
    fallback_field: '',
    sla_hours: null,
    enabled_if: '',
    business_status: '',
  }
}

function createEmptyStepForm() {
  return {
    key: '',
    name: '',
    candidate_roles: [],
    fallback_field: '',
    sla_hours: null,
    enabled_if: '',
    business_status: '',
  }
}

function createEmptyActionForm() {
  return {
    key: '',
    label: '',
    business_status: '',
    target_mode: 'step',
    target_node_id: '',
  }
}

function shouldHandleGraphKeyboardEvent(event) {
  const root = editorRootRef.value
  if (!root) {
    return false
  }

  const target = event.target instanceof Element ? event.target : null
  const activeElement = document.activeElement instanceof Element ? document.activeElement : null
  const withinEditor = (target && root.contains(target)) || (activeElement && root.contains(activeElement))
  if (!withinEditor) {
    return false
  }

  const isFormLike = (element) =>
    Boolean(
      element?.closest?.(
        'input, textarea, select, [contenteditable="true"], .el-input__inner, .el-textarea__inner, .el-select__input',
      ),
    )

  return !isFormLike(target) && !isFormLike(activeElement)
}

function syncHistoryState() {
  historyState.canUndo = Boolean(graph?.canUndo?.())
  historyState.canRedo = Boolean(graph?.canRedo?.())
}

function syncViewportState() {
  viewportState.zoomPercent = graph ? Math.round((graph.zoom?.() || 1) * 100) : 100
}

function runWithoutHistory(execute) {
  if (!graph?.disableHistory || !graph?.enableHistory || !graph?.isHistoryEnabled) {
    return execute()
  }

  const shouldSuspend = historySuspendLevel === 0 && graph.isHistoryEnabled()
  if (shouldSuspend) {
    graph.disableHistory()
  }
  historySuspendLevel += 1
  try {
    return execute()
  } finally {
    historySuspendLevel -= 1
    if (shouldSuspend && historySuspendLevel === 0) {
      graph.enableHistory()
    }
  }
}

function finalizeInsertedStepNode(node) {
  if (!graph || !node) {
    return
  }

  if (!getOutgoingEdges(getStartNode()).length && getStepNodes().length === 1) {
    createStartEdge(node)
    createStepEdge(node, getEndNode())
  }

  selectNode(node)
  syncGraphState()
}

function sanitizeStepData(step = {}) {
  return {
    key: String(step.key || '').trim(),
    name: String(step.name || '').trim(),
    candidate_roles: Array.isArray(step.candidate_roles)
      ? step.candidate_roles.map((item) => String(item || '').trim()).filter(Boolean)
      : [],
    fallback_field: String(step.fallback_field || '').trim(),
    sla_hours:
      step.sla_hours === '' || step.sla_hours == null || Number.isNaN(Number(step.sla_hours))
        ? null
        : Number(step.sla_hours),
    enabled_if: String(step.enabled_if || '').trim(),
    business_status: String(step.business_status || '').trim(),
  }
}

function sanitizeActionData(action = {}) {
  return {
    key: String(action.key || '').trim(),
    label: String(action.label || '').trim(),
    business_status: String(action.business_status || '').trim(),
  }
}

function generateStepKey() {
  const existingKeys = new Set(
    getStepNodes()
      .map((node) => String(node.getData()?.step?.key || '').trim())
      .filter(Boolean),
  )
  let index = existingKeys.size + 1
  while (existingKeys.has(`step_${index}`)) {
    index += 1
  }
  return `step_${index}`
}

function generateActionKey(sourceNode) {
  const existingKeys = new Set(
    getOutgoingEdges(sourceNode)
      .map((edge) => String(edge.getData()?.key || '').trim())
      .filter(Boolean),
  )
  let index = existingKeys.size + 1
  while (existingKeys.has(`action_${index}`)) {
    index += 1
  }
  return `action_${index}`
}

function getNextStepSequence() {
  stepSequenceCounter += 1
  return stepSequenceCounter
}

function getNextEdgeSequence() {
  edgeSequenceCounter += 1
  return edgeSequenceCounter
}

function getVisibleCenter() {
  const width = containerRef.value?.clientWidth || 960
  const height = containerRef.value?.clientHeight || 520
  return {
    x: Math.max(220, width / 2 - 114),
    y: Math.max(80, height / 2 - 54),
  }
}

function createEdgeConfig(extra = {}) {
  return {
    shape: 'edge',
    zIndex: 1,
    attrs: {
      line: {
        stroke: '#2563eb',
        strokeWidth: 2,
        targetMarker: {
          name: 'classic',
          size: 8,
        },
      },
    },
    ...extra,
  }
}

function createStartEdge(targetNode) {
  const existingEdges = getOutgoingEdges(getStartNode())
  if (existingEdges.length) {
    existingEdges.forEach((edge) => edge.remove())
  }
  const edge = graph.addEdge(
    createEdgeConfig({
      source: {
        cell: START_NODE_ID,
        port: 'out',
      },
      target: {
        cell: targetNode.id,
        port: 'in',
      },
      data: {
        key: 'start',
        label: '开始',
        business_status: '',
        order: 0,
      },
    }),
  )
  applyEdgePresentation(edge)
  return edge
}

function createStepEdge(sourceNode, targetNode) {
  const edge = graph.addEdge(
    createEdgeConfig({
      source: {
        cell: sourceNode.id,
        port: 'out',
      },
      target: {
        cell: targetNode.id,
        port: 'in',
      },
      data: {
        key: generateActionKey(sourceNode),
        label: '',
        business_status: '',
        order: getNextEdgeSequence(),
      },
    }),
  )
  applyEdgePresentation(edge)
  return edge
}

function isWorkflowConnection(sourceNode, targetNode) {
  if (!sourceNode || !targetNode) {
    return false
  }
  if (isStartNode(sourceNode)) {
    return isStepNode(targetNode)
  }
  if (isStepNode(sourceNode)) {
    return isStepNode(targetNode) || isEndNode(targetNode)
  }
  return false
}

function isStartNode(node) {
  return node?.id === START_NODE_ID || node?.getData?.()?.kind === 'start'
}

function isEndNode(node) {
  return node?.id === END_NODE_ID || node?.getData?.()?.kind === 'end'
}

function isStepNode(node) {
  return node?.getData?.()?.kind === 'step'
}

function getStartNode() {
  return graph?.getCellById(START_NODE_ID) || null
}

function getEndNode() {
  return graph?.getCellById(END_NODE_ID) || null
}

function getStepNodes() {
  if (!graph) {
    return []
  }
  return graph.getNodes().filter((node) => isStepNode(node))
}

function getActionEdges() {
  if (!graph) {
    return []
  }
  return graph.getEdges().filter((edge) => isStepNode(edge.getSourceNode()))
}

function getOutgoingEdges(node) {
  if (!graph || !node) {
    return []
  }
  return (graph.getOutgoingEdges(node) || []).filter((edge) => edge.getSourceCellId() === node.id)
}

function getEdgeOrder(edge) {
  const order = Number(edge?.getData?.()?.order)
  return Number.isFinite(order) ? order : 0
}

function sortNodesBySequence(a, b) {
  const aSeq = Number(a.getData()?.sequence) || 0
  const bSeq = Number(b.getData()?.sequence) || 0
  return aSeq - bSeq
}

function sortEdgesByOrder(a, b) {
  return getEdgeOrder(a) - getEdgeOrder(b)
}

function syncGraphState() {
  graphStats.steps = getStepNodes().length
  graphStats.actions = getActionEdges().length
  graphRevision.value += 1
  refreshSelectionStyles()
  syncHistoryState()
  syncViewportState()
}

function applyNodePresentation(node) {
  if (!node) {
    return
  }

  if (isStepNode(node)) {
    const selected = selectedState.cellId === node.id && selectedState.kind === 'step'
    const step = sanitizeStepData(node.getData()?.step)
    const metaParts = []
    if (step.candidate_roles.length) {
      metaParts.push(step.candidate_roles.join(' / '))
    }
    if (step.sla_hours != null) {
      metaParts.push(`SLA ${step.sla_hours}h`)
    }
    runWithoutHistory(() => {
      node.attr({
        body: {
          fill: selected ? '#eff6ff' : '#ffffff',
          stroke: selected ? '#1d4ed8' : '#2563eb',
          strokeWidth: selected ? 3 : 2,
        },
        title: {
          text: step.name || '未命名审批节点',
        },
        subtitle: {
          text: step.key || '未配置步骤键',
        },
        meta: {
          text: metaParts.join(' · ') || '配置处理角色 / SLA / 条件',
        },
      })
    })
    return
  }

  if (isStartNode(node)) {
    const selected = selectedState.cellId === node.id && selectedState.kind === 'start'
    runWithoutHistory(() => {
      node.attr({
        body: {
          fill: selected ? '#dcfce7' : '#ecfdf3',
          stroke: selected ? '#15803d' : '#22c55e',
          strokeWidth: selected ? 3 : 2,
        },
      })
    })
    return
  }

  if (isEndNode(node)) {
    const selected = selectedState.cellId === node.id && selectedState.kind === 'end'
    runWithoutHistory(() => {
      node.attr({
        body: {
          fill: selected ? '#ffe4e6' : '#fff1f2',
          stroke: selected ? '#dc2626' : '#ef4444',
          strokeWidth: selected ? 3 : 2,
        },
      })
    })
  }
}

function applyEdgePresentation(edge) {
  if (!edge) {
    return
  }
  const selected = selectedState.cellId === edge.id && selectedState.kind === 'edge'
  const action = sanitizeActionData(edge.getData())
  const targetNode = edge.getTargetNode()
  const baseColor = isEndNode(targetNode) ? '#059669' : '#2563eb'
  const activeColor = isEndNode(targetNode) ? '#047857' : '#1d4ed8'
  const stroke = selected ? activeColor : baseColor
  const text = action.label || action.key || (isEndNode(targetNode) ? '结束流程' : '新动作')
  runWithoutHistory(() => {
    edge.attr({
      line: {
        stroke,
        strokeWidth: selected ? 3 : 2,
        targetMarker: {
          name: 'classic',
          size: 8,
        },
      },
    })
    edge.setLabels([
      {
        attrs: {
          labelText: {
            text,
            fill: '#ffffff',
            fontSize: 12,
            fontWeight: 600,
          },
          labelBody: {
            ref: 'labelText',
            fill: stroke,
            stroke: stroke,
            rx: 10,
            ry: 10,
            refWidth: '120%',
            refHeight: '160%',
            refX: '-10%',
            refY: '-30%',
          },
        },
        markup: [
          { tagName: 'rect', selector: 'labelBody' },
          { tagName: 'text', selector: 'labelText' },
        ],
        position: {
          distance: 0.5,
        },
      },
    ])
  })
}

function refreshSelectionStyles() {
  if (!graph) {
    return
  }
  graph.getNodes().forEach((node) => applyNodePresentation(node))
  graph.getEdges().forEach((edge) => applyEdgePresentation(edge))
}

function selectNode(node) {
  if (!node) {
    return
  }
  const step = sanitizeStepData(node.getData()?.step)
  selectedState.kind = 'step'
  selectedState.cellId = node.id
  Object.assign(stepForm, createEmptyStepForm(), step)
  refreshSelectionStyles()
}

function selectEdge(edge) {
  if (!edge) {
    return
  }
  const action = sanitizeActionData(edge.getData())
  const targetNode = edge.getTargetNode()
  selectedState.kind = 'edge'
  selectedState.cellId = edge.id
  Object.assign(actionForm, createEmptyActionForm(), action, {
    target_mode: isEndNode(targetNode) ? 'end' : 'step',
    target_node_id: isStepNode(targetNode) ? targetNode.id : '',
  })
  refreshSelectionStyles()
}

function selectFixedNode(kind, cellId) {
  selectedState.kind = kind
  selectedState.cellId = cellId
  refreshSelectionStyles()
}

function clearSelection(refresh = true) {
  selectedState.kind = 'none'
  selectedState.cellId = ''
  Object.assign(stepForm, createEmptyStepForm())
  Object.assign(actionForm, createEmptyActionForm())
  if (refresh) {
    refreshSelectionStyles()
  }
}

function selectInitialStep() {
  const startNode = getStartNode()
  const startEdges = getOutgoingEdges(startNode)
  if (startEdges.length) {
    const node = startEdges[0].getTargetNode()
    if (isStepNode(node)) {
      selectNode(node)
      return
    }
  }
  const firstNode = getStepNodes().sort(sortNodesBySequence)[0]
  if (firstNode) {
    selectNode(firstNode)
  }
}

function getStepLabelFromNode(node) {
  if (!node) {
    return '-'
  }
  if (isStartNode(node)) {
    return '开始节点'
  }
  if (isEndNode(node)) {
    return '结束节点'
  }
  const step = sanitizeStepData(node.getData()?.step)
  const name = step.name || '未命名审批节点'
  return step.key ? `${name} (${step.key})` : name
}

function collectReachableStepIds(firstNode) {
  const visited = new Set()
  const queue = firstNode ? [firstNode] : []
  while (queue.length) {
    const node = queue.shift()
    if (!node || visited.has(node.id)) {
      continue
    }
    visited.add(node.id)
    getOutgoingEdges(node).forEach((edge) => {
      const targetNode = edge.getTargetNode()
      if (isStepNode(targetNode) && !visited.has(targetNode.id)) {
        queue.push(targetNode)
      }
    })
  }
  return visited
}

function orderStepNodes(firstNode) {
  const ordered = []
  const visited = new Set()

  const visit = (node) => {
    if (!node || visited.has(node.id)) {
      return
    }
    visited.add(node.id)
    ordered.push(node)
    getOutgoingEdges(node)
      .sort(sortEdgesByOrder)
      .forEach((edge) => {
        const targetNode = edge.getTargetNode()
        if (isStepNode(targetNode)) {
          visit(targetNode)
        }
      })
  }

  visit(firstNode)

  getStepNodes()
    .sort(sortNodesBySequence)
    .forEach((node) => visit(node))

  return ordered
}

function buildEditorPositions() {
  const positions = {
    [START_POSITION_KEY]: extractNodePosition(getStartNode()),
    [END_POSITION_KEY]: extractNodePosition(getEndNode()),
  }
  getStepNodes().forEach((node) => {
    const stepKey = String(node.getData()?.step?.key || '').trim()
    if (!stepKey) {
      return
    }
    positions[stepKey] = extractNodePosition(node)
  })
  return positions
}

function extractNodePosition(node) {
  if (!node) {
    return { x: 0, y: 0 }
  }
  const position = node.getPosition()
  return {
    x: Math.round(position.x),
    y: Math.round(position.y),
  }
}

function reindexAllEdgeOrders() {
  getStepNodes().forEach((node) => {
    getOutgoingEdges(node)
      .sort((a, b) => {
        const orderDiff = sortEdgesByOrder(a, b)
        if (orderDiff !== 0) {
          return orderDiff
        }
        return a.id.localeCompare(b.id)
      })
      .forEach((edge, index) => {
        edge.setData({
          ...edge.getData(),
          order: index + 1,
        })
        applyEdgePresentation(edge)
      })
  })
}

function autoLayoutGraph() {
  if (!graph) {
    return
  }

  const startNode = getStartNode()
  const endNode = getEndNode()
  const stepNodes = getStepNodes().sort(sortNodesBySequence)
  if (!startNode || !endNode || !stepNodes.length) {
    return
  }

  const levelMap = new Map()
  const startEdge = getOutgoingEdges(startNode)[0]
  const firstStep = startEdge?.getTargetNode()
  if (isStepNode(firstStep)) {
    levelMap.set(firstStep.id, 0)
    const queue = [firstStep]
    while (queue.length) {
      const node = queue.shift()
      const currentLevel = levelMap.get(node.id) ?? 0
      getOutgoingEdges(node).forEach((edge) => {
        const targetNode = edge.getTargetNode()
        if (!isStepNode(targetNode)) {
          return
        }
        const nextLevel = currentLevel + 1
        if (!levelMap.has(targetNode.id) || nextLevel < levelMap.get(targetNode.id)) {
          levelMap.set(targetNode.id, nextLevel)
          queue.push(targetNode)
        }
      })
    }
  }

  let maxLevel = levelMap.size ? Math.max(...levelMap.values()) : -1
  stepNodes.forEach((node) => {
    if (!levelMap.has(node.id)) {
      maxLevel += 1
      levelMap.set(node.id, maxLevel)
    }
  })

  const groups = new Map()
  stepNodes.forEach((node) => {
    const level = levelMap.get(node.id) || 0
    if (!groups.has(level)) {
      groups.set(level, [])
    }
    groups.get(level).push(node)
  })

  const containerHeight = containerRef.value?.clientHeight || 520
  const orderedLevels = [...groups.keys()].sort((a, b) => a - b)
  orderedLevels.forEach((level) => {
    const nodes = groups.get(level).sort(sortNodesBySequence)
    const gapY = 160
    const contentHeight = nodes.length * 108 + Math.max(0, nodes.length - 1) * (gapY - 108)
    const startY = Math.max(56, (containerHeight - contentHeight) / 2)
    nodes.forEach((node, index) => {
      node.setPosition(280 + level * 280, startY + index * gapY)
    })
  })

  const firstColumnNodes = groups.get(0) || []
  const firstCenterY =
    firstColumnNodes.reduce((sum, node) => sum + node.getPosition().y, 0) / Math.max(firstColumnNodes.length, 1)
  const lastLevel = orderedLevels.length ? orderedLevels[orderedLevels.length - 1] : 0
  const lastColumnNodes = groups.get(lastLevel) || []
  const lastCenterY =
    lastColumnNodes.reduce((sum, node) => sum + node.getPosition().y, 0) / Math.max(lastColumnNodes.length, 1)

  startNode.setPosition(56, Math.max(56, firstCenterY || DEFAULT_START_POSITION.y))
  endNode.setPosition(280 + (lastLevel + 1) * 280, Math.max(56, lastCenterY || DEFAULT_END_POSITION.y))

  fitCanvas()
  syncGraphState()
}

function fitCanvas() {
  if (!graph) {
    return
  }
  if (typeof graph.zoomToFit === 'function') {
    graph.zoomToFit({
      padding: 32,
      maxScale: 1,
    })
  }
  if (typeof graph.centerContent === 'function') {
    graph.centerContent()
  }
}
</script>

<style scoped>
.workflow-canvas-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workflow-canvas-toolbar,
.workflow-canvas-sidecard,
.workflow-canvas-stage {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #ffffff;
}

.workflow-canvas-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 34%),
    linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
}

.workflow-canvas-toolbar-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.workflow-canvas-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.workflow-canvas-subtitle {
  color: #475569;
  font-size: 13px;
}

.workflow-canvas-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}

.workflow-toolbar-zoom {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid #dbe3ef;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
}

.workflow-toolbar-zoom-label {
  min-width: 48px;
  text-align: center;
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
}

.workflow-canvas-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  gap: 16px;
  min-height: 620px;
}

.workflow-canvas-sidebar,
.workflow-canvas-inspector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workflow-canvas-stage {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workflow-canvas-graph {
  flex: 1;
  min-height: 560px;
}

.workflow-canvas-hint {
  padding: 12px 16px 14px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
}

.workflow-canvas-sidecard {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
}

.workflow-canvas-sidecard-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.workflow-palette-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.workflow-palette-item:disabled {
  cursor: default;
  opacity: 0.85;
}

.workflow-palette-item:not(:disabled):hover {
  transform: translateY(-1px);
  border-color: #93c5fd;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
}

.workflow-palette-item div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.workflow-palette-item strong {
  font-size: 14px;
  color: #111827;
}

.workflow-palette-item span:last-child {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.workflow-palette-dot {
  display: inline-flex;
  width: 14px;
  height: 14px;
  margin-top: 2px;
  border-radius: 999px;
  border: 3px solid currentColor;
}

.workflow-palette-item-start {
  color: #16a34a;
}

.workflow-palette-item-step {
  color: #2563eb;
}

.workflow-palette-item-end {
  color: #ef4444;
}

.workflow-palette-item-step {
  cursor: grab;
}

.workflow-palette-item-step:active {
  cursor: grabbing;
}

.workflow-guide-list {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.workflow-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.workflow-stats-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
}

.workflow-stats-item span {
  color: #64748b;
  font-size: 12px;
}

.workflow-stats-item strong {
  color: #0f172a;
  font-size: 22px;
}

.workflow-selected-title,
.workflow-fixed-hint,
.workflow-empty-inspector {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
}

.workflow-selected-title strong,
.workflow-fixed-hint strong,
.workflow-empty-inspector strong {
  color: #111827;
  font-size: 15px;
}

.workflow-selected-title span,
.workflow-fixed-hint span,
.workflow-empty-inspector span {
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.workflow-inspector-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.workflow-minimap-container {
  min-height: 176px;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.96) 0%, rgba(241, 245, 249, 0.92) 100%);
  overflow: hidden;
}

.workflow-minimap-footer {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.workflow-minimap-container :deep(.x6-widget-minimap) {
  width: 100% !important;
  height: 176px !important;
  padding: 0 !important;
  border: 0;
}

.workflow-minimap-container :deep(.x6-widget-minimap-viewport) {
  border: 1px solid rgba(37, 99, 235, 0.55);
  background: rgba(37, 99, 235, 0.12);
}

.workflow-minimap-container :deep(svg) {
  background: transparent;
}

@media (max-width: 1280px) {
  .workflow-canvas-layout {
    grid-template-columns: 240px minmax(0, 1fr) 300px;
  }
}

@media (max-width: 1024px) {
  .workflow-canvas-layout {
    grid-template-columns: 1fr;
  }

  .workflow-canvas-sidebar,
  .workflow-canvas-inspector {
    order: 2;
  }

  .workflow-canvas-stage {
    order: 1;
    min-height: 520px;
  }
}

@media (max-width: 768px) {
  .workflow-canvas-toolbar {
    flex-direction: column;
  }

  .workflow-canvas-toolbar-actions {
    justify-content: flex-start;
  }

  .workflow-canvas-graph {
    min-height: 420px;
  }
}
</style>
