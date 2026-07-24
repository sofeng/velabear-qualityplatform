<template>
  <section
    class="asset-insight-panel"
    :class="{
      'asset-insight-panel--embedded': embedded,
      'asset-insight-panel--compact': compact,
    }"
  >
    <header v-if="showHeader" class="asset-insight-header">
      <div>
        <h2>资产图谱</h2>
        <span>基于项目代码仓库、接口、数据库库表字段和知识库对象，建立页面、接口、代码、数据的全链路关系</span>
      </div>
      <div class="asset-insight-header__actions">
        <el-button :loading="loading" @click="loadAll">刷新</el-button>
        <el-button
          type="primary"
          :loading="enableLoading"
          @click="handleEnableProjectKnowledge"
        >
          {{ projectKnowledgeStatus.enabled ? '重新生成知识库' : '创建项目知识库' }}
        </el-button>
      </div>
    </header>

    <section v-if="showStatus" class="asset-insight-status">
      <div>
        <strong>{{ projectKnowledgeStatus.space?.name || '项目知识库未创建' }}</strong>
        <span>{{ projectKnowledgeStatus.message || insight.status?.build_status_message || '配置代码仓库和数据库后，可生成项目全维度知识库。' }}</span>
      </div>
      <div class="asset-insight-status__meta">
        <el-tag :type="getBuildStatusType(projectKnowledgeStatus.space?.build_status || insight.status?.build_status)" effect="plain">
          {{ getBuildStatusLabel(projectKnowledgeStatus.space?.build_status || insight.status?.build_status) }}
        </el-tag>
        <span>就绪数据源 {{ projectKnowledgeStatus.ready_config_count || 0 }}/{{ projectKnowledgeStatus.repository_configs?.length || 0 }}</span>
      </div>
    </section>

    <section v-if="showSummary" class="asset-insight-summary">
      <div v-for="item in summaryCards" :key="item.key">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </section>

    <section
      v-if="showToolbar && (!isActiveGraphTab || (showTabSwitcher && !fixedTab))"
      class="asset-insight-toolbar"
    >
      <el-segmented v-if="showTabSwitcher && !fixedTab" v-model="activeTab" :options="tabOptions" />
      <el-input
        v-model="keyword"
        class="asset-insight-toolbar__search"
        clearable
        placeholder="搜索页面、接口、表、字段、代码文件"
        @keyup.enter="loadInsight"
      />
      <el-button :loading="loading" @click="loadInsight">检索</el-button>
    </section>

    <section
      v-show="isActiveGraphTab"
      class="asset-insight-workbench"
      :class="{
        'asset-insight-workbench--side-expanded': graphSideExpanded,
        'asset-insight-workbench--maximized': graphMaximized,
      }"
    >
      <header class="asset-insight-graph-header">
        <div class="asset-insight-graph-node-info">
          <template v-if="activeGraphInfoNode">
            <div class="asset-insight-graph-node-info__main">
              <strong>{{ getGraphNodeLabel(activeGraphInfoNode) }}</strong>
              <el-tag size="small" effect="plain">{{ getGraphNodeTypeLabel(activeGraphInfoNode) }}</el-tag>
              <span v-if="activeGraphInfoPath">{{ activeGraphInfoPath }}</span>
            </div>
            <div
              v-if="activeGraphInfoNode.summary"
              class="asset-insight-graph-node-info__summary"
            >
              {{ activeGraphInfoNode.summary }}
            </div>
            <div
              v-if="activeGraphParentNodes.length || activeGraphChildNodes.length"
              class="asset-insight-graph-node-info__relations"
            >
              <div v-if="activeGraphParentNodes.length" class="asset-insight-graph-node-info__relation-group">
                <span>上游</span>
                <button
                  v-for="node in activeGraphParentNodes"
                  :key="`parent-${getGraphNodeId(node)}`"
                  type="button"
                  @click="centerGraphNode(getGraphNodeId(node))"
                >
                  {{ getGraphNodeLabel(node) }}
                </button>
              </div>
              <div v-if="activeGraphChildNodes.length" class="asset-insight-graph-node-info__relation-group">
                <span>下游</span>
                <button
                  v-for="node in activeGraphChildNodes"
                  :key="`child-${getGraphNodeId(node)}`"
                  type="button"
                  @click="centerGraphNode(getGraphNodeId(node))"
                >
                  {{ getGraphNodeLabel(node) }}
                </button>
              </div>
            </div>
          </template>
          <span v-else>{{ activeGraphTitle }}：{{ activeGraphDescription }}</span>
        </div>
        <div class="asset-insight-graph-actions">
          <el-tooltip :content="graphSideExpanded ? '收起详情' : '展开详情'" placement="bottom">
            <el-button
              size="small"
              :icon="graphSideExpanded ? Fold : Expand"
              :disabled="!graphNodeCount"
              :aria-label="graphSideExpanded ? '收起图谱详情' : '展开图谱详情'"
              @click="toggleGraphSideExpanded"
            />
          </el-tooltip>
          <el-tooltip :content="graphMaximized ? '恢复原形' : '最大化'" placement="bottom">
            <el-button
              size="small"
              :icon="graphMaximized ? ScaleToOriginal : FullScreen"
              :disabled="!graphNodeCount"
              :aria-label="graphMaximized ? '恢复关系图' : '最大化关系图'"
              @click="toggleGraphMaximized"
            />
          </el-tooltip>
          <el-popover
            v-model:visible="graphSearchPopoverVisible"
            placement="bottom-end"
            trigger="click"
            width="420"
            popper-class="asset-insight-graph-search-popover"
          >
            <template #reference>
              <el-button
                size="small"
                :icon="Search"
                :disabled="!graphNodeCount"
              >
                搜索节点
              </el-button>
            </template>
            <div class="asset-insight-graph-search-panel">
              <el-input
                v-model="graphSearchKeyword"
                clearable
                placeholder="搜索图谱节点"
                :prefix-icon="Search"
                @keyup.enter="centerActiveGraphSearchNode"
              />
              <div class="asset-insight-graph-search-panel__meta">
                <span>{{ graphSearchSummary }}</span>
                <div class="asset-insight-graph-search-panel__nav">
                  <el-button
                    size="small"
                    text
                    :icon="ArrowLeft"
                    :disabled="graphSearchMatches.length <= 1"
                    @click="activatePreviousGraphSearchMatch"
                  />
                  <el-button
                    size="small"
                    text
                    :icon="ArrowRight"
                    :disabled="graphSearchMatches.length <= 1"
                    @click="activateNextGraphSearchMatch"
                  />
                </div>
              </div>
              <el-scrollbar class="asset-insight-graph-search-tree-scroll">
                <el-tree
                  ref="graphSearchTreeRef"
                  class="asset-insight-graph-search-tree"
                  node-key="id"
                  :data="graphSearchTreeData"
                  :props="graphSearchTreeProps"
                  :default-expanded-keys="graphSearchDefaultExpandedKeys"
                  :expand-on-click-node="false"
                  :highlight-current="true"
                  @node-click="handleGraphSearchTreeNodeClick"
                >
                  <template #default="{ data }">
                    <span
                      class="asset-insight-graph-search-tree-node"
                      :class="{
                        'is-search-matched': isGraphSearchMatchedNode(data.nodeId),
                        'is-search-active': selectedGraphNodeId === data.nodeId,
                      }"
                    >
                      <span class="asset-insight-graph-search-tree-node__label">{{ data.label }}</span>
                      <span class="asset-insight-graph-search-tree-node__type">{{ data.typeLabel }}</span>
                    </span>
                  </template>
                </el-tree>
              </el-scrollbar>
            </div>
          </el-popover>
          <div v-if="graphSearchMatches.length" class="asset-insight-graph-search-status">
            <span>{{ graphActiveSearchMatchDisplayIndex }}/{{ graphSearchMatches.length }}</span>
            <el-button size="small" text :icon="ArrowLeft" @click="activatePreviousGraphSearchMatch" />
            <el-button size="small" text :icon="ArrowRight" @click="activateNextGraphSearchMatch" />
          </div>
          <el-tag v-if="loading" size="small" type="warning" effect="plain">检索中</el-tag>
          <el-tag v-else size="small" type="success" effect="plain">{{ graphNodeCount }} 个对象</el-tag>
        </div>
      </header>

      <div v-if="activeTab === 'er'" class="asset-insight-er-filter">
        <el-segmented v-model="erView" :options="erViewOptions" />
        <el-input
          v-model="centerTable"
          clearable
          placeholder="输入中心表名，按局部关系展开"
          @keyup.enter="loadInsight({ force: true })"
        />
        <el-button :loading="loading" @click="loadInsight({ force: true })">展开</el-button>
      </div>

      <div class="asset-insight-graph-body">
        <div class="asset-insight-graph-main">
          <div v-show="chainGraphTabs.includes(activeTab)" ref="pageApiGraphRef" class="asset-insight-graph" />
          <div v-show="activeTab === 'er'" ref="erGraphRef" class="asset-insight-graph asset-insight-graph--er" />
          <div v-show="activeTab === 'code'" ref="codeGraphRef" class="asset-insight-graph" />
          <el-empty v-if="!graphNodeCount && !loading" description="暂无项目资产关系图" />
        </div>
        <aside v-if="graphSideExpanded" class="asset-insight-side">
          <h3>{{ activeGraphTitle }}</h3>
          <p>{{ activeGraphDescription }}</p>
          <el-scrollbar class="asset-insight-side__scroll">
            <div
              v-for="node in selectedGraphNodes"
              :key="getGraphNodeId(node)"
              class="asset-insight-node-card"
              :class="{ 'is-active': getGraphNodeId(node) === selectedGraphNodeId }"
              @click="centerGraphNode(getGraphNodeId(node))"
            >
              <div>
                <strong>{{ getGraphNodeLabel(node) }}</strong>
                <el-tag size="small" effect="plain">{{ getGraphNodeTypeLabel(node) }}</el-tag>
              </div>
              <p>{{ getGraphNodePath(node) || node.summary || '-' }}</p>
            </div>
          </el-scrollbar>
        </aside>
      </div>
    </section>

    <section v-show="activeTab === 'ghost'" class="asset-insight-table-section">
      <header>
        <h3>幽灵代码与闲置资产排查</h3>
        <span>仅作为疑似结果，删除或下线前必须结合动态调用、外部系统、定时任务和业务负责人复核</span>
      </header>
      <div class="asset-insight-table-body">
        <el-table v-loading="loading && activeTab === 'ghost'" :data="insight.ghost_code.findings" height="100%" border>
        <el-table-column prop="type_label" label="类型" width="170" />
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="getSeverityTagType(row.severity)" effect="plain">{{ getSeverityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="对象" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.object?.label || '-' }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="判断依据" min-width="260" show-overflow-tooltip />
        <el-table-column prop="suggestion" label="建议" min-width="300" show-overflow-tooltip />
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="ghostPagination.page"
        v-model:page-size="ghostPagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        :total="ghostPagination.total"
        class="tab-pagination asset-insight-pagination"
        @current-change="loadInsight({ force: true })"
        @size-change="handleGhostPageSizeChange"
      />
    </section>

    <section v-show="activeTab === 'fields'" class="asset-insight-table-section">
      <header>
        <h3>库表字段检索</h3>
        <span>用于快速定位字段归属、字段类型、字段备注和来源配置</span>
      </header>
      <div class="asset-insight-table-body">
        <el-table v-loading="loading && activeTab === 'fields'" :data="insight.fields.fields" height="100%" border>
        <el-table-column prop="db_table" label="表名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="field_name" label="字段" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.metadata?.column_type || row.metadata?.field_type || '-' }}</template>
        </el-table-column>
        <el-table-column label="键" width="90">
          <template #default="{ row }">{{ row.metadata?.column_key || '-' }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="说明" min-width="260" show-overflow-tooltip />
        <el-table-column prop="source_ref" label="来源" min-width="220" show-overflow-tooltip />
        </el-table>
      </div>
      <el-pagination
        v-model:current-page="fieldPagination.page"
        v-model:page-size="fieldPagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        :total="fieldPagination.total"
        class="tab-pagination asset-insight-pagination"
        @current-change="loadInsight({ force: true })"
        @size-change="handleFieldPageSizeChange"
      />
    </section>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  Expand,
  Fold,
  FullScreen,
  ScaleToOriginal,
  Search,
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import {
  enableProjectKnowledge,
  getKnowledgeAssetInsight,
  getProjectKnowledgeStatus,
} from '@/api/knowledge'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  currentProjectId: {
    type: [String, Number],
    default: '',
  },
  initialTab: {
    type: String,
    default: 'page_api_table',
  },
  fixedTab: {
    type: String,
    default: '',
  },
  embedded: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  showHeader: {
    type: Boolean,
    default: true,
  },
  showStatus: {
    type: Boolean,
    default: true,
  },
  showSummary: {
    type: Boolean,
    default: true,
  },
  showToolbar: {
    type: Boolean,
    default: true,
  },
  showTabSwitcher: {
    type: Boolean,
    default: true,
  },
})

const loading = ref(false)
const enableLoading = ref(false)
const activeTab = ref(props.fixedTab || props.initialTab || 'page_api_table')
const keyword = ref('')
const centerTable = ref('')
const erView = ref('macro')
const graphSideExpanded = ref(false)
const graphMaximized = ref(false)
const graphSearchPopoverVisible = ref(false)
const graphSearchKeyword = ref('')
const activeGraphSearchIndex = ref(-1)
const selectedGraphNodeId = ref('')
const graphSearchTreeRef = ref(null)
const ghostPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})
const fieldPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})
const loadedSections = reactive({
  summary: false,
  page_api_table: false,
  page_function: false,
  api: false,
  er: false,
  code: false,
  ghost: false,
  fields: false,
})
const pageApiGraphRef = ref(null)
const erGraphRef = ref(null)
const codeGraphRef = ref(null)
let pageApiChart = null
let erChart = null
let codeChart = null

const projectKnowledgeStatus = reactive({
  enabled: false,
  space: null,
  repository_configs: [],
  ready_config_count: 0,
  latest_run: null,
  message: '',
})

const insight = reactive({
  space: null,
  summary: {},
  graph: { nodes: [], edges: [], categories: [] },
  ghost_code: { findings: [], summary: {}, total: 0 },
  fields: { tables: [], fields: [] },
  status: {},
})

const tabOptions = Object.freeze([
  { label: '页面功能', value: 'page_function' },
  { label: '页面-接口-库表', value: 'page_api_table' },
  { label: '接口关系', value: 'api' },
  { label: '数据库ER', value: 'er' },
  { label: '代码调用', value: 'code' },
  { label: '幽灵代码', value: 'ghost' },
  { label: '库表字段', value: 'fields' },
])
const chainGraphTabs = Object.freeze(['page_api_table', 'page_function', 'api'])
const graphTabs = Object.freeze([...chainGraphTabs, 'er', 'code'])
const erViewOptions = Object.freeze([
  { label: '宏观', value: 'macro' },
  { label: '中观', value: 'meso' },
  { label: '微观', value: 'micro' },
])
const graphSearchTreeProps = Object.freeze({
  children: 'children',
  label: 'label',
})

const graphCopy = Object.freeze({
  page_api_table: {
    title: '页面功能-接口-库表字段链路',
    description: '按页面、页签、功能、操作项、组件、接口、代码文件、库表和字段串联业务链路。',
  },
  page_function: {
    title: '页面功能链路',
    description: '聚焦菜单、页签、页面、功能、操作项和前端组件，定位功能入口与页面实现。',
  },
  api: {
    title: '接口关系图',
    description: '聚焦接口、代码文件、调用符号、读写库表和字段引用，定位接口上下游。',
  },
  er: {
    title: '数据库ER图',
    description: '宏观看库表边界，中观看中心表邻域，微观看表字段和字段级引用。',
  },
  code: {
    title: '代码调用图',
    description: '基于 ctags、semgrep 与内置扫描结果展示仓库、文件、符号、接口和库表字段关系。',
  },
})

const summaryCards = computed(() => [
  { key: 'objects', label: '知识对象', value: insight.summary.object_count || 0 },
  { key: 'relations', label: '关系', value: insight.summary.relation_count || 0 },
  { key: 'pages', label: '页面/页签', value: insight.summary.page_count || 0 },
  { key: 'apis', label: '接口', value: insight.summary.api_count || 0 },
  { key: 'tables', label: '库表', value: insight.summary.table_count || 0 },
  { key: 'fields', label: '字段', value: insight.summary.field_count || 0 },
  { key: 'code', label: '代码文件', value: insight.summary.code_file_count || 0 },
  { key: 'ghost', label: '疑似问题', value: insight.ghost_code.total || 0 },
])

const isActiveGraphTab = computed(() => graphTabs.includes(activeTab.value))
const graphNodes = computed(() => (Array.isArray(insight.graph.nodes) ? insight.graph.nodes : []))
const graphEdges = computed(() => (Array.isArray(insight.graph.edges) ? insight.graph.edges : []))
const graphNodeCount = computed(() => graphNodes.value.length)
const graphNodeIdMap = computed(() => {
  const map = new Map()
  graphNodes.value.forEach((node, index) => {
    map.set(getGraphNodeId(node, index), node)
  })
  return map
})
const selectedGraphNodes = computed(() => {
  const activeId = selectedGraphNodeId.value
  const nodes = graphNodes.value.slice(0, 120)
  if (!activeId || nodes.some(node => getGraphNodeId(node) === activeId)) {
    return nodes
  }
  const activeNode = graphNodeIdMap.value.get(activeId)
  return activeNode ? [activeNode, ...nodes.slice(0, 119)] : nodes
})
const activeGraphTitle = computed(() => graphCopy[activeTab.value]?.title || '资产关系图')
const activeGraphDescription = computed(() => graphCopy[activeTab.value]?.description || '基于已索引知识对象展示当前图谱。')
const activeGraphInfoNode = computed(() => (
  graphNodeIdMap.value.get(selectedGraphNodeId.value) || graphNodes.value[0] || null
))
const activeGraphInfoPath = computed(() => getGraphNodePath(activeGraphInfoNode.value))
const graphNodeRelationModel = computed(() => {
  const parents = new Map()
  const children = new Map()
  graphEdges.value.forEach(edge => {
    const sourceId = String(edge.source || edge.source_key || '')
    const targetId = String(edge.target || edge.target_key || '')
    if (!sourceId || !targetId || sourceId === targetId) {
      return
    }
    if (!children.has(sourceId)) children.set(sourceId, [])
    if (!parents.has(targetId)) parents.set(targetId, [])
    children.get(sourceId).push(targetId)
    parents.get(targetId).push(sourceId)
  })
  return { parents, children }
})
const activeGraphParentNodes = computed(() => {
  const ids = graphNodeRelationModel.value.parents.get(selectedGraphNodeId.value) || []
  return ids.map(id => graphNodeIdMap.value.get(id)).filter(Boolean).slice(0, 6)
})
const activeGraphChildNodes = computed(() => {
  const ids = graphNodeRelationModel.value.children.get(selectedGraphNodeId.value) || []
  return ids.map(id => graphNodeIdMap.value.get(id)).filter(Boolean).slice(0, 6)
})
const graphSearchNormalizedKeyword = computed(() => normalizeGraphSearchText(graphSearchKeyword.value))
const graphSearchMatches = computed(() => {
  const keywordValue = graphSearchNormalizedKeyword.value
  if (!keywordValue) {
    return []
  }
  return graphNodes.value
    .map((node, index) => ({ node, id: getGraphNodeId(node, index), index }))
    .filter(item => normalizeGraphSearchText([
      getGraphNodeLabel(item.node),
      getGraphNodeTypeLabel(item.node),
      item.node.summary,
      item.node.page_path,
      item.node.api_path,
      item.node.db_table,
      item.node.field_name,
      item.node.source_ref,
    ].filter(Boolean).join(' ')).includes(keywordValue))
})
const graphSearchMatchedNodeIds = computed(() => new Set(graphSearchMatches.value.map(item => item.id)))
const graphActiveSearchMatchDisplayIndex = computed(() => {
  if (!graphSearchMatches.value.length) {
    return 0
  }
  const activeIndex = graphSearchMatches.value.findIndex(item => item.id === selectedGraphNodeId.value)
  if (activeIndex >= 0) {
    return activeIndex + 1
  }
  return Math.min(Math.max(activeGraphSearchIndex.value + 1, 1), graphSearchMatches.value.length)
})
const graphSearchSummary = computed(() => {
  if (!graphSearchNormalizedKeyword.value) {
    return `当前图谱 ${graphNodeCount.value} 个节点`
  }
  if (!graphSearchMatches.value.length) {
    return '未找到匹配节点'
  }
  return `已找到 ${graphSearchMatches.value.length} 个节点，当前 ${graphActiveSearchMatchDisplayIndex.value}/${graphSearchMatches.value.length}`
})
const graphSearchTreeData = computed(() => {
  const grouped = new Map()
  graphNodes.value.forEach((node, index) => {
    const typeLabel = getGraphNodeTypeLabel(node)
    if (!grouped.has(typeLabel)) {
      grouped.set(typeLabel, {
        id: `group-${typeLabel}`,
        label: typeLabel,
        typeLabel: '类型',
        nodeId: '',
        children: [],
      })
    }
    grouped.get(typeLabel).children.push({
      id: getGraphNodeId(node, index),
      nodeId: getGraphNodeId(node, index),
      label: getGraphNodeLabel(node),
      typeLabel,
      children: [],
    })
  })
  return Array.from(grouped.values()).map(group => ({
    ...group,
    children: group.children.sort((a, b) => a.label.localeCompare(b.label, 'zh-Hans-CN')),
  }))
})
const graphSearchDefaultExpandedKeys = computed(() => {
  if (graphSearchNormalizedKeyword.value) {
    return graphSearchTreeData.value.map(item => item.id)
  }
  return graphSearchTreeData.value.slice(0, 4).map(item => item.id)
})

const loadProjectKnowledgeStatus = async () => {
  if (!props.currentProjectId) {
    Object.assign(projectKnowledgeStatus, {
      enabled: false,
      space: null,
      repository_configs: [],
      ready_config_count: 0,
      latest_run: null,
      message: '请选择项目后创建项目知识库。',
    })
    return
  }
  const response = await getProjectKnowledgeStatus({ project_id: props.currentProjectId })
  Object.assign(projectKnowledgeStatus, response.data || {})
}

const getGraphTypeForActiveTab = () => {
  if (activeTab.value === 'er') {
    return 'er'
  }
  if (activeTab.value === 'code') {
    return 'code'
  }
  if (activeTab.value === 'page_function') {
    return 'page_function'
  }
  if (activeTab.value === 'api') {
    return 'api'
  }
  return 'page_api_table'
}

const getSectionForActiveTab = () => {
  if (graphTabs.includes(activeTab.value)) {
    return 'graph'
  }
  return activeTab.value
}

const getGraphRequestLimit = () => {
  if (!graphTabs.includes(activeTab.value)) {
    return 220
  }
  if (props.embedded || props.compact) {
    return activeTab.value === 'page_api_table' ? 220 : 140
  }
  if (activeTab.value === 'page_api_table') {
    return 220
  }
  return 220
}

const getLoadedSectionKey = () => {
  if (activeTab.value === 'er') {
    return `er:${erView.value}:${centerTable.value || ''}`
  }
  if (activeTab.value === 'ghost') {
    return `ghost:${ghostPagination.page}:${ghostPagination.pageSize}`
  }
  if (activeTab.value === 'fields') {
    return `fields:${fieldPagination.page}:${fieldPagination.pageSize}`
  }
  return activeTab.value
}

const resetLoadedSections = () => {
  Object.keys(loadedSections).forEach(key => {
    loadedSections[key] = false
  })
}

const mergeInsightPayload = (data = {}) => {
  if ('space' in data) insight.space = data.space || null
  if ('summary' in data) insight.summary = data.summary || {}
  if ('graph' in data) insight.graph = data.graph || { nodes: [], edges: [], categories: [] }
  if ('ghost_code' in data) {
    insight.ghost_code = data.ghost_code || { findings: [], summary: {}, total: 0 }
    ghostPagination.total = insight.ghost_code.total || 0
    ghostPagination.page = insight.ghost_code.page || ghostPagination.page
    ghostPagination.pageSize = insight.ghost_code.page_size || ghostPagination.pageSize
  }
  if ('fields' in data) {
    insight.fields = data.fields || { tables: [], fields: [] }
    fieldPagination.total = insight.fields.total || insight.fields.total_fields || 0
    fieldPagination.page = insight.fields.page || fieldPagination.page
    fieldPagination.pageSize = insight.fields.page_size || fieldPagination.pageSize
  }
  if ('status' in data) insight.status = data.status || {}
}

const loadSummary = async ({ force = false } = {}) => {
  if (loadedSections.summary && !force) {
    return
  }
  const response = await getKnowledgeAssetInsight({
    project_id: props.currentProjectId || undefined,
    section: 'summary',
    limit: 1,
  })
  mergeInsightPayload(response.data || {})
  loadedSections.summary = true
}

const loadInsight = async ({ force = false } = {}) => {
  const sectionKey = getLoadedSectionKey()
  if (loadedSections[sectionKey] && !force && !keyword.value) {
    await nextTick()
    renderActiveGraph()
    return
  }
  loading.value = true
  try {
    const response = await getKnowledgeAssetInsight({
      project_id: props.currentProjectId || undefined,
      section: getSectionForActiveTab(),
      graph_type: getGraphTypeForActiveTab(),
      q: keyword.value || undefined,
      center_table: activeTab.value === 'er' ? centerTable.value || undefined : undefined,
      er_view: activeTab.value === 'er' ? erView.value : undefined,
      page: activeTab.value === 'ghost' ? ghostPagination.page : (activeTab.value === 'fields' ? fieldPagination.page : undefined),
      page_size: activeTab.value === 'ghost' ? ghostPagination.pageSize : (activeTab.value === 'fields' ? fieldPagination.pageSize : undefined),
      limit: getGraphRequestLimit(),
    })
    mergeInsightPayload(response.data || {})
    loadedSections[sectionKey] = !keyword.value
    await nextTick()
    renderActiveGraph()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '加载资产图谱失败')
  } finally {
    loading.value = false
  }
}

const loadAll = async () => {
  loading.value = true
  try {
    resetLoadedSections()
    await loadProjectKnowledgeStatus()
    await loadSummary({ force: true })
    await loadInsight({ force: true })
  } finally {
    loading.value = false
  }
}

const handleEnableProjectKnowledge = async () => {
  if (!props.currentProjectId) {
    ElMessage.warning('请先选择项目')
    return
  }
  enableLoading.value = true
  try {
    const response = await enableProjectKnowledge({
      project_id: props.currentProjectId,
      enabled: true,
      trigger_index: true,
    })
    Object.assign(projectKnowledgeStatus, response.data || {})
    ElMessage.success(response.data?.index?.queued ? '项目知识库已启用，建模任务已提交' : '项目知识库已启用')
    resetLoadedSections()
    await loadSummary({ force: true })
    await loadInsight({ force: true })
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '创建项目知识库失败')
  } finally {
    enableLoading.value = false
  }
}

const ensureChart = (type) => {
  const chartType = chainGraphTabs.includes(type) ? 'page_api_table' : type
  const refMap = {
    page_api_table: pageApiGraphRef,
    er: erGraphRef,
    code: codeGraphRef,
  }
  const chartMap = {
    page_api_table: pageApiChart,
    er: erChart,
    code: codeChart,
  }
  const element = refMap[chartType]?.value
  if (!element) {
    return null
  }
  if (!chartMap[chartType]) {
    const chart = echarts.init(element, null, { renderer: 'canvas' })
    if (chartType === 'page_api_table') pageApiChart = chart
    if (chartType === 'er') erChart = chart
    if (chartType === 'code') codeChart = chart
    return chart
  }
  chartMap[chartType].resize()
  return chartMap[chartType]
}

const normalizeGraphSearchText = value => String(value || '').trim().toLowerCase()

const getGraphNodeId = (node, index = 0) => String(node?.id || node?.key || index)

const getGraphNodeLabel = node => String(node?.label || node?.name || node?.key || node?.id || '未命名节点')

const getGraphNodeTypeLabel = node => node?.node_type_label || getObjectTypeLabel(node?.type) || node?.type || '对象'

const getGraphNodePath = node => {
  if (!node) {
    return ''
  }
  const roadmapPath = Array.isArray(node.roadmap_path) ? node.roadmap_path.filter(Boolean).join(' > ') : ''
  return roadmapPath || node.page_path || node.api_path || [
    node.db_table,
    node.field_name,
  ].filter(Boolean).join('.') || node.component_path || node.source_ref || ''
}

const getObjectTypeLabel = type => ({
  platform: '平台',
  project: '项目',
  module: '模块',
  menu: '菜单',
  page: '页面',
  tab: '页签',
  section: '板块',
  function: '功能',
  operation: '操作项',
  field: '字段',
  api: '接口',
  database: '数据库',
  table: '表',
  component: '组件',
  route: '路由',
  repository: '仓库',
  document: '文档',
  business_data: '业务数据',
  file: '文件',
  class: '类',
  method: '方法',
}[type] || type || '对象')

const getGraphNodeColor = type => ({
  project: '#1d5fd1',
  platform: '#1d5fd1',
  module: '#1f6fb2',
  menu: '#3c7a4f',
  page: '#7a5b1f',
  tab: '#7a5b1f',
  section: '#9a6316',
  function: '#7f5fb5',
  operation: '#8f4f1f',
  component: '#2f6f73',
  api: '#0f766e',
  route: '#0e7490',
  database: '#1d4ed8',
  table: '#3c7a4f',
  field: '#64748b',
  repository: '#475569',
  file: '#526a82',
  class: '#7c3aed',
  method: '#8b5cf6',
}[type] || '#526a82')

const getGraphEdgeColor = branch => ({
  root: '#64748b',
  ui: '#3c7a4f',
  code: '#2563eb',
  data: '#7c3aed',
  bridge: '#f97316',
}[branch] || '#9ab0c4')

const isGraphSearchMatchedNode = nodeId => graphSearchMatchedNodeIds.value.has(String(nodeId || ''))

const getGraphNodeVisualConfig = (node, type, nodeId) => {
  const searchMatched = isGraphSearchMatchedNode(nodeId)
  const searchActive = selectedGraphNodeId.value === String(nodeId || '')
  const color = getGraphNodeColor(type)
  const highlighted = searchMatched || searchActive
  return {
    searchMatched,
    searchActive,
    symbolSize: searchActive
      ? 62
      : Math.max(searchMatched ? 48 : getNodeSymbolSize(type), highlighted ? 48 : getNodeSymbolSize(type)),
    itemStyle: {
      color: searchActive ? '#2563eb' : color,
      borderColor: searchActive ? '#f97316' : (searchMatched ? '#f59e0b' : '#ffffff'),
      borderWidth: searchActive ? 5 : (searchMatched ? 4 : 2),
      shadowBlur: searchActive ? 24 : (searchMatched ? 18 : 8),
      shadowColor: searchActive
        ? 'rgba(249, 115, 22, 0.42)'
        : (searchMatched ? 'rgba(245, 158, 11, 0.34)' : 'rgba(34, 62, 92, 0.16)'),
    },
  }
}

const shouldShowGraphNodeLabel = (node, type, nodeId, totalCount) => {
  if (selectedGraphNodeId.value === String(nodeId || '') || isGraphSearchMatchedNode(nodeId)) {
    return true
  }
  if (activeTab.value === 'page_api_table') {
    const chainPrimaryTypes = new Set(['platform', 'project', 'module', 'menu', 'page', 'tab', 'section', 'api', 'table', 'database'])
    if (!chainPrimaryTypes.has(type)) {
      return false
    }
    const rank = Number(node?.asset_graph_rank ?? node?.metadata?.asset_graph?.rank ?? 99)
    return totalCount <= 120 ? rank <= 8 : rank <= 6
  }
  const primaryTypes = new Set(['platform', 'project', 'module', 'menu', 'page', 'tab', 'section', 'function', 'operation', 'api', 'table', 'database'])
  if (!primaryTypes.has(type)) {
    return false
  }
  if (totalCount <= 90) {
    return true
  }
  const rank = Number(node?.asset_graph_rank ?? node?.metadata?.asset_graph?.rank ?? 99)
  return rank <= 8 && type !== 'field'
}

const getChartForActiveGraph = () => {
  if (chainGraphTabs.includes(activeTab.value)) {
    return pageApiChart
  }
  if (activeTab.value === 'er') {
    return erChart
  }
  if (activeTab.value === 'code') {
    return codeChart
  }
  return null
}

const getActiveGraphRefElement = () => {
  if (chainGraphTabs.includes(activeTab.value)) {
    return pageApiGraphRef.value
  }
  if (activeTab.value === 'er') {
    return erGraphRef.value
  }
  if (activeTab.value === 'code') {
    return codeGraphRef.value
  }
  return null
}

const getGraphNodeDataIndex = nodeId => {
  const targetId = String(nodeId || '').trim()
  if (!targetId) {
    return -1
  }
  return graphNodes.value.findIndex((node, index) => getGraphNodeId(node, index) === targetId)
}

const getGraphNodePixelPosition = (chart, dataIndex) => {
  if (!chart || dataIndex < 0) {
    return null
  }
  try {
    const model = chart.getModel?.()
    const seriesModel = model?.getSeriesByIndex?.(0)
    const data = seriesModel?.getData?.()
    const element = data?.getItemGraphicEl?.(dataIndex)
    if (!element) {
      return null
    }
    const point = typeof element.transformCoordToGlobal === 'function'
      ? element.transformCoordToGlobal(0, 0)
      : [Number(element.x || 0), Number(element.y || 0)]
    if (!Number.isFinite(point?.[0]) || !Number.isFinite(point?.[1])) {
      return null
    }
    return point
  } catch (error) {
    return null
  }
}

const centerGraphChartNode = ({ retry = true } = {}) => {
  const nodeId = selectedGraphNodeId.value
  const chart = getChartForActiveGraph()
  const element = getActiveGraphRefElement()
  const dataIndex = getGraphNodeDataIndex(nodeId)
  if (!nodeId || !chart || !element || dataIndex < 0) {
    return
  }
  const point = getGraphNodePixelPosition(chart, dataIndex)
  const { clientWidth, clientHeight } = element
  if (!point || !clientWidth || !clientHeight) {
    if (retry) {
      window.setTimeout(() => centerGraphChartNode({ retry: false }), 260)
    }
    return
  }
  const dx = clientWidth / 2 - point[0]
  const dy = clientHeight / 2 - point[1]
  if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
    chart.dispatchAction({
      type: 'graphRoam',
      seriesIndex: 0,
      dx,
      dy,
    })
    if (retry) {
      window.setTimeout(() => centerGraphChartNode({ retry: false }), 420)
    }
  }
}

const centerGraphNode = async nodeId => {
  const id = String(nodeId || '').trim()
  if (!id) {
    return
  }
  selectedGraphNodeId.value = id
  await nextTick()
  renderActiveGraph()
  await nextTick()
  centerGraphChartNode()
  graphSearchTreeRef.value?.setCurrentKey?.(id)
}

const activateGraphSearchMatch = nextIndex => {
  const matches = graphSearchMatches.value
  if (!matches.length) {
    activeGraphSearchIndex.value = -1
    return
  }
  const normalizedIndex = ((nextIndex % matches.length) + matches.length) % matches.length
  activeGraphSearchIndex.value = normalizedIndex
  centerGraphNode(matches[normalizedIndex].id)
}

const activatePreviousGraphSearchMatch = () => {
  if (graphSearchMatches.value.length) {
    activateGraphSearchMatch(activeGraphSearchIndex.value - 1)
  }
}

const activateNextGraphSearchMatch = () => {
  if (graphSearchMatches.value.length) {
    activateGraphSearchMatch(activeGraphSearchIndex.value + 1)
  }
}

const centerActiveGraphSearchNode = () => {
  if (graphSearchMatches.value.length) {
    activateGraphSearchMatch(Math.max(activeGraphSearchIndex.value, 0))
  }
}

const handleGraphSearchTreeNodeClick = data => {
  if (data?.nodeId) {
    const matchIndex = graphSearchMatches.value.findIndex(item => item.id === data.nodeId)
    if (matchIndex >= 0) {
      activeGraphSearchIndex.value = matchIndex
    }
    centerGraphNode(data.nodeId)
  }
}

const handleGraphChartClick = params => {
  if (params?.dataType === 'node' && params?.data?.id) {
    centerGraphNode(params.data.id)
  }
}

const toggleGraphSideExpanded = () => {
  graphSideExpanded.value = !graphSideExpanded.value
  nextTick(resizeCharts)
}

const toggleGraphMaximized = () => {
  graphMaximized.value = !graphMaximized.value
  nextTick(() => {
    resizeCharts()
    window.setTimeout(resizeCharts, 160)
  })
}

const handleGhostPageSizeChange = () => {
  ghostPagination.page = 1
  loadInsight({ force: true })
}

const handleFieldPageSizeChange = () => {
  fieldPagination.page = 1
  loadInsight({ force: true })
}

const renderActiveGraph = () => {
  if (!props.active) {
    return
  }
  if (!graphTabs.includes(activeTab.value)) {
    return
  }
  const graphType = getGraphTypeForActiveTab()
  const chart = ensureChart(graphType)
  if (!chart) {
    return
  }
  const nodes = graphNodes.value
  const edges = graphEdges.value
  if (nodes.length && (!selectedGraphNodeId.value || !graphNodeIdMap.value.has(selectedGraphNodeId.value))) {
    selectedGraphNodeId.value = getGraphNodeId(nodes[0], 0)
  }
  const categories = (insight.graph.categories || []).map(item => ({
    name: item.name,
    label: item.label,
  }))
  const categoryIndexByType = new Map(categories.map((item, index) => [item.name, index]))
  const nodeIds = new Set(nodes.map((node, index) => getGraphNodeId(node, index)))
  const fixedLayout = Boolean(insight.graph.layout?.fixed_positions) && nodes.some(node => Number.isFinite(Number(node.x)) && Number.isFinite(Number(node.y)))
  chart.setOption({
    backgroundColor: '#f8fbfd',
    animation: true,
    animationDurationUpdate: 500,
    tooltip: {
      show: false,
    },
    legend: {
      top: 10,
      left: 12,
      orient: 'horizontal',
      textStyle: { color: '#526a82', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
      data: categories.map(item => item.name),
      formatter: name => categories.find(item => item.name === name)?.label || name,
    },
    series: [{
      type: 'graph',
      layout: fixedLayout ? 'none' : 'force',
      roam: true,
      draggable: true,
      focusNodeAdjacency: false,
      force: fixedLayout ? undefined : {
        initLayout: 'circular',
        repulsion: nodes.length > 80 ? 180 : 260,
        edgeLength: nodes.length > 80 ? [80, 150] : [90, 180],
        gravity: 0.08,
        friction: 0.58,
      },
      categories,
      data: nodes.map((node, index) => {
        const nodeId = getGraphNodeId(node, index)
        const type = node.type || 'object'
        const visual = getGraphNodeVisualConfig(node, type, nodeId)
        const showLabel = shouldShowGraphNodeLabel(node, type, nodeId, nodes.length)
        return {
          id: nodeId,
          name: getGraphNodeLabel(node),
          category: categoryIndexByType.get(type) || 0,
          x: fixedLayout ? Number(node.x || 0) : undefined,
          y: fixedLayout ? Number(node.y || 0) : undefined,
          fixed: fixedLayout ? Boolean(node.fixed) : undefined,
          draggable: true,
          symbolSize: visual.symbolSize,
          itemStyle: visual.itemStyle,
          raw: node,
          data: {
            type,
            searchMatched: visual.searchMatched,
            searchActive: visual.searchActive,
          },
          label: {
            show: showLabel,
            position: 'right',
            color: visual.searchActive ? '#7c2d12' : '#1f2d3d',
            fontSize: 12,
            fontWeight: visual.searchActive || visual.searchMatched ? 800 : 700,
            formatter: params => params.data?.name || '',
          },
        }
      }),
      links: edges
        .map(edge => ({
          source: String(edge.source || edge.source_key),
          target: String(edge.target || edge.target_key),
          name: edge.label || edge.type || '',
          lineStyle: {
            color: getGraphEdgeColor(edge.asset_graph_branch || edge.metadata?.asset_graph?.branch),
            opacity: edge.inferred ? 0.42 : 0.7,
            width: edge.inferred ? 1 : 1.4,
            curveness: edge.asset_graph_branch === 'bridge' ? 0.22 : 0.1,
            type: edge.inferred ? 'dashed' : 'solid',
          },
        }))
        .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target) && edge.source !== edge.target),
      lineStyle: {
        color: '#9ab0c4',
        opacity: 0.62,
        width: 1.2,
        curveness: 0.12,
      },
      edgeLabel: {
        show: edges.length <= (fixedLayout ? 42 : 28),
        fontSize: 10,
        color: '#657b90',
        formatter: params => params.data?.name || '',
      },
      emphasis: {
        focus: 'none',
        scale: 1.08,
        label: {
          show: true,
          color: '#0f4c81',
          fontWeight: 800,
        },
        itemStyle: {
          borderColor: '#38bdf8',
          borderWidth: 5,
          shadowBlur: 24,
          shadowColor: 'rgba(14, 165, 233, 0.42)',
        },
        lineStyle: { width: 1.2, opacity: 0.62 },
      },
    }],
  }, true)
  chart.off('click', handleGraphChartClick)
  chart.on('click', handleGraphChartClick)
  chart.resize()
}

const getNodeSymbolSize = type => ({
  project: 44,
  module: 42,
  menu: 34,
  page: 34,
  tab: 32,
  section: 30,
  api: 30,
  table: 32,
  database: 42,
  field: 22,
  file: 26,
  class: 24,
  function: 22,
  method: 22,
  component: 28,
}[type] || 24)

const getBuildStatusLabel = value => ({
  pending_config: '待配置',
  ready: '已就绪',
  queued: '排队中',
  indexing: '建模中',
  indexed: '已建模',
  stale: '需刷新',
  failed: '失败',
}[value] || value || '未创建')

const getBuildStatusType = value => ({
  ready: 'success',
  indexed: 'success',
  queued: 'warning',
  indexing: 'warning',
  stale: 'warning',
  failed: 'danger',
}[value] || 'info')

const getSeverityLabel = value => ({
  high: '高',
  medium: '中',
  low: '低',
}[value] || value || '-')

const getSeverityTagType = value => ({
  high: 'danger',
  medium: 'warning',
  low: 'info',
}[value] || 'info')

const disposeCharts = () => {
  ;[pageApiChart, erChart, codeChart].forEach(chart => chart?.dispose?.())
  pageApiChart = null
  erChart = null
  codeChart = null
}

const resizeCharts = () => {
  pageApiChart?.resize?.()
  erChart?.resize?.()
  codeChart?.resize?.()
}

watch(graphSearchKeyword, () => {
  activeGraphSearchIndex.value = graphSearchMatches.value.length ? 0 : -1
  if (graphSearchMatches.value.length && !graphSearchMatches.value.some(item => item.id === selectedGraphNodeId.value)) {
    selectedGraphNodeId.value = graphSearchMatches.value[0].id
  }
  nextTick(renderActiveGraph)
})

watch(graphNodes, nodes => {
  if (!nodes.length) {
    selectedGraphNodeId.value = ''
    activeGraphSearchIndex.value = -1
    return
  }
  if (!selectedGraphNodeId.value || !graphNodeIdMap.value.has(selectedGraphNodeId.value)) {
    selectedGraphNodeId.value = getGraphNodeId(nodes[0], 0)
  }
})

watch(erView, async () => {
  if (props.active && activeTab.value === 'er') {
    await loadInsight({ force: true })
  }
})

watch(() => props.active, active => {
  if (active) {
    loadAll()
  }
})

watch(() => props.currentProjectId, () => {
  if (props.active) {
    loadAll()
  }
})

watch(
  () => props.fixedTab || props.initialTab,
  value => {
    const nextTab = value || 'page_api_table'
    if (activeTab.value !== nextTab) {
      activeTab.value = nextTab
    }
  }
)

watch(activeTab, async () => {
  graphSideExpanded.value = false
  graphSearchPopoverVisible.value = false
  graphSearchKeyword.value = ''
  activeGraphSearchIndex.value = -1
  selectedGraphNodeId.value = ''
  if (props.active) {
    await loadInsight()
  }
})

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  if (props.active) {
    loadAll()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
</script>

<style scoped>
.asset-insight-panel {
  height: 100%;
  min-height: 680px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #f5f7fb;
  color: #1f2d3d;
}

.asset-insight-panel--embedded.asset-insight-panel--compact {
  min-height: 0;
  padding: 0;
  gap: 0;
  background: #ffffff;
}

.asset-insight-header,
.asset-insight-status,
.asset-insight-toolbar,
.asset-insight-table-section,
.asset-insight-workbench {
  background: #fff;
  border: 1px solid #dbe4ee;
  border-radius: 6px;
}

.asset-insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  gap: 16px;
}

.asset-insight-header h2,
.asset-insight-table-section h3,
.asset-insight-side h3 {
  margin: 0;
  font-size: 16px;
  line-height: 24px;
}

.asset-insight-header span,
.asset-insight-status span,
.asset-insight-table-section header span,
.asset-insight-side p {
  color: #6b7f93;
  font-size: 13px;
}

.asset-insight-header__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.asset-insight-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  gap: 16px;
}

.asset-insight-status > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.asset-insight-status__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.asset-insight-summary {
  display: grid;
  grid-template-columns: repeat(8, minmax(96px, 1fr));
  gap: 10px;
}

.asset-insight-summary > div {
  min-height: 72px;
  padding: 12px;
  background: #fff;
  border: 1px solid #dbe4ee;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.asset-insight-summary span {
  color: #6b7f93;
  font-size: 12px;
}

.asset-insight-summary strong {
  font-size: 22px;
  line-height: 28px;
}

.asset-insight-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.asset-insight-toolbar__search {
  max-width: 360px;
}

.asset-insight-workbench {
  flex: 1;
  min-width: 0;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.asset-insight-panel--embedded .asset-insight-workbench {
  min-height: 0;
  border: 0;
  border-radius: 0;
}

.asset-insight-workbench--maximized {
  position: fixed;
  inset: 14px;
  z-index: 3000;
  min-height: 0;
  border: 1px solid #cbd9e6;
  box-shadow: 0 22px 64px rgba(15, 35, 52, 0.24);
}

.asset-insight-graph-header {
  flex: 0 0 auto;
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid #dce6ef;
  background: #ffffff;
}

.asset-insight-graph-node-info {
  min-width: 0;
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 3px;
  overflow: hidden;
}

.asset-insight-graph-node-info > span {
  min-width: 0;
  overflow: hidden;
  color: #66798d;
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-insight-graph-node-info__main,
.asset-insight-graph-node-info__summary,
.asset-insight-graph-node-info__relations {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 7px;
  overflow: hidden;
}

.asset-insight-graph-node-info__main strong {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  color: #1e2f42;
  font-size: 13px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-insight-graph-node-info__main > span,
.asset-insight-graph-node-info__summary {
  min-width: 0;
  overflow: hidden;
  color: #66798d;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-insight-graph-node-info__summary {
  display: block;
}

.asset-insight-graph-node-info__relations {
  color: #66798d;
}

.asset-insight-graph-node-info__relation-group {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
}

.asset-insight-graph-node-info__relation-group > span {
  flex: 0 0 auto;
  color: #7b8da0;
  font-size: 11px;
  line-height: 1.2;
}

.asset-insight-graph-node-info__relation-group > button {
  flex: 0 1 auto;
  max-width: 132px;
  height: 22px;
  min-width: 0;
  padding: 0 7px;
  border: 1px solid #d5e3ef;
  border-radius: 6px;
  background: #f8fbfd;
  color: #2f5f8f;
  cursor: pointer;
  font-size: 11px;
  line-height: 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-insight-graph-node-info__relation-group > button:hover {
  border-color: #9fc6e8;
  background: #eef6fd;
  color: #1f6fb2;
}

.asset-insight-graph-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.asset-insight-graph-search-status {
  height: 24px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 4px 0 8px;
  border: 1px solid #d8e4ef;
  border-radius: 6px;
  background: #f8fbfd;
  color: #40566c;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.asset-insight-graph-search-status :deep(.el-button) {
  width: 22px;
  height: 22px;
  padding: 0;
}

.asset-insight-er-filter {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #e5edf5;
}

.asset-insight-er-filter .el-input {
  max-width: 360px;
}

.asset-insight-graph-body {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  overflow: hidden;
  background: #f8fbfd;
}

.asset-insight-workbench--side-expanded .asset-insight-graph-body {
  grid-template-columns: minmax(0, 1fr) 360px;
}

.asset-insight-graph-main {
  min-width: 0;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.asset-insight-graph-main :deep(.el-empty) {
  flex: 1 1 auto;
}

.asset-insight-graph {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
}

.asset-insight-graph--er {
  min-height: 0;
}

.asset-insight-side {
  min-width: 0;
  border-left: 1px solid #e5edf5;
  padding: 14px;
  overflow: hidden;
  background: #ffffff;
}

.asset-insight-side__scroll {
  height: calc(100% - 54px);
}

.asset-insight-node-card {
  border: 1px solid #e5edf5;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 8px;
  background: #fbfdff;
  cursor: pointer;
}

.asset-insight-node-card:hover,
.asset-insight-node-card.is-active {
  border-color: #9fc6e8;
  background: #eef6fd;
}

.asset-insight-node-card > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.asset-insight-node-card strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.asset-insight-node-card p {
  margin: 6px 0 0;
  color: #6b7f93;
  font-size: 12px;
  line-height: 18px;
  word-break: break-all;
}

.asset-insight-table-section {
  flex: 1;
  min-width: 0;
  min-height: 560px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.asset-insight-panel--embedded .asset-insight-table-section {
  min-height: 0;
  border: 0;
  border-radius: 0;
}

.asset-insight-table-section header {
  flex: 0 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.asset-insight-table-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.asset-insight-pagination {
  flex: 0 0 auto;
  margin-top: 12px;
  justify-content: flex-end;
}

@media (max-width: 1280px) {
  .asset-insight-summary {
    grid-template-columns: repeat(4, minmax(120px, 1fr));
  }

  .asset-insight-workbench--side-expanded .asset-insight-graph-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .asset-insight-side {
    display: none;
  }
}

:global(.asset-insight-graph-search-popover) {
  max-width: min(92vw, 420px);
  padding: 10px;
}

:global(.asset-insight-graph-search-popover .asset-insight-graph-search-panel) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:global(.asset-insight-graph-search-panel__meta) {
  min-height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #66798d;
  font-size: 12px;
  line-height: 1.3;
}

:global(.asset-insight-graph-search-panel__meta > span) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.asset-insight-graph-search-panel__nav) {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

:global(.asset-insight-graph-search-panel__nav .el-button) {
  width: 24px;
  height: 24px;
  padding: 0;
}

:global(.asset-insight-graph-search-tree-scroll) {
  max-height: min(48vh, 420px);
  border: 1px solid #e1e8f0;
  border-radius: 6px;
  background: #fbfdff;
}

:global(.asset-insight-graph-search-tree) {
  min-width: 100%;
  padding: 6px 0;
  background: transparent;
}

:global(.asset-insight-graph-search-tree .el-tree-node__content) {
  min-height: 30px;
  padding-right: 6px;
}

:global(.asset-insight-graph-search-tree-node) {
  min-width: 0;
  width: 100%;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  border-radius: 6px;
  color: #283b4d;
  line-height: 1.2;
}

:global(.asset-insight-graph-search-tree-node__label) {
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.asset-insight-graph-search-tree-node__type) {
  flex: 0 0 auto;
  padding: 1px 5px;
  border-radius: 4px;
  background: #edf4fa;
  color: #66798d;
  font-size: 11px;
}

:global(.asset-insight-graph-search-tree-node.is-search-matched) {
  background: #fff7df;
  color: #7a4b00;
}

:global(.asset-insight-graph-search-tree-node.is-search-matched .asset-insight-graph-search-tree-node__type) {
  background: #ffe8a8;
  color: #7a4b00;
}

:global(.asset-insight-graph-search-tree-node.is-search-active) {
  background: #ffe3c7;
  color: #7c2d12;
  box-shadow: inset 0 0 0 1px #fb923c;
}

:global(.asset-insight-graph-search-tree-node.is-search-active .asset-insight-graph-search-tree-node__type) {
  background: #fed7aa;
  color: #7c2d12;
}
</style>
