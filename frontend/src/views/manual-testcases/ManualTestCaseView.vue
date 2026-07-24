<template>
  <div class="manual-testcase-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>手工用例查看</span>
          <div class="actions">
            <el-button type="primary" @click="handleEdit">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button @click="handleExport">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <el-button @click="handleBack">
              <el-icon><Back /></el-icon>
              返回
            </el-button>
          </div>
        </div>
      </template>

      <div class="mindmap-info-panel">
        <button class="mindmap-info-panel__toggle" type="button" @click="toggleInfoCollapsed">
          <div class="mindmap-info-panel__heading">
            <span class="mindmap-info-panel__title">脑图信息</span>
            <span v-if="isInfoCollapsed" class="mindmap-info-panel__summary">{{ caseInfo.name }}</span>
          </div>
          <div class="mindmap-info-panel__action">
            <span>{{ isInfoCollapsed ? '展开' : '收起' }}</span>
            <el-icon class="mindmap-info-panel__icon" :class="{ 'is-collapsed': isInfoCollapsed }">
              <ArrowDown />
            </el-icon>
          </div>
        </button>

        <el-collapse-transition>
          <div v-show="!isInfoCollapsed" class="mindmap-info-panel__content">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用例名称">{{ caseInfo.name }}</el-descriptions-item>
              <el-descriptions-item label="创建人">{{ caseInfo.creator }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">
                <span class="mindmap-info-panel__value--nowrap">{{ caseInfo.created_at }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="更新时间">
                <span class="mindmap-info-panel__value--nowrap">{{ caseInfo.updated_at }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ caseInfo.description }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-collapse-transition>
      </div>

      <div class="minder-container">
        <div id="minder-viewer" :style="{ height: editorHeight }"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Download, Back, ArrowDown } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { getUserDisplayName } from '@/utils/userDisplay'

const router = useRouter()
const route = useRoute()

let minder = null
let hasMounted = false

const createDefaultMindmapData = (name = '未命名脑图') => ({
  root: {
    data: {
      text: name,
      nodeType: 'module'
    },
    children: []
  },
  template: 'default',
  theme: 'fresh-blue',
  version: '1.4.43'
})

const createDefaultCaseInfo = () => ({
  id: null,
  name: '-',
  description: '-',
  creator: '-',
  created_at: '-',
  updated_at: '-'
})

const caseInfo = ref(createDefaultCaseInfo())
const minderData = ref(createDefaultMindmapData())
const isInfoCollapsed = ref(true)
const windowHeight = ref(window.innerHeight)

const editorHeight = computed(() => {
  const offset = isInfoCollapsed.value ? 280 : 400
  return `${Math.max(windowHeight.value - offset, 420)}px`
})

const normalizeQueryValue = (value) => Array.isArray(value) ? value[0] : value
const padDatePart = value => String(value).padStart(2, '0')

const formatDateTime = (value) => {
  const normalizedValue = String(value || '').trim()
  if (!normalizedValue || normalizedValue === '-') {
    return '-'
  }

  const parsedDate = new Date(normalizedValue)
  if (Number.isNaN(parsedDate.getTime())) {
    return normalizedValue
      .replace('T', ' ')
      .replace(/\.\d+/, '')
      .replace(/Z$/, '')
  }

  return [
    parsedDate.getFullYear(),
    padDatePart(parsedDate.getMonth() + 1),
    padDatePart(parsedDate.getDate())
  ].join('-') + ` ${[
    padDatePart(parsedDate.getHours()),
    padDatePart(parsedDate.getMinutes()),
    padDatePart(parsedDate.getSeconds())
  ].join(':')}`
}

const toggleInfoCollapsed = () => {
  isInfoCollapsed.value = !isInfoCollapsed.value
}

const syncWindowHeight = () => {
  windowHeight.value = window.innerHeight
}

const resetMinder = () => {
  if (minder) {
    try {
      const paper = minder.getPaper?.()
      paper?.remove?.()
    } catch (error) {
      console.error('清理脑图实例失败:', error)
    }
    minder = null
  }

  const viewer = document.getElementById('minder-viewer')
  if (viewer) {
    viewer.innerHTML = ''
  }
}

const handleEdit = () => {
  router.push({
    path: '/manual-testcases/editor',
    query: {
      id: normalizeQueryValue(route.query.id),
      from_tab: normalizeQueryValue(route.query.from_tab),
      return_query: normalizeQueryValue(route.query.return_query)
    }
  })
}

const handleExport = () => {
  const exportData = minder?.exportJson?.() || minderData.value
  const dataStr = JSON.stringify(exportData, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `${caseInfo.value.name}_${Date.now()}.json`
  link.click()

  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

const handleBack = () => {
  const fromTab = normalizeQueryValue(route.query.from_tab)
  const rawReturnQuery = normalizeQueryValue(route.query.return_query)
  let returnQuery = null
  if (rawReturnQuery) {
    try {
      const parsed = JSON.parse(decodeURIComponent(String(rawReturnQuery)))
      returnQuery = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
    } catch (error) {
      console.log('解析返回筛选条件失败:', error)
    }
  }
  router.push({
    path: '/manual-testcases/list',
    query: returnQuery || (fromTab ? { tab: fromTab } : {})
  })
}

const locateAndSelectNode = ({ text, path }) => {
  if (!minder || (!text && !path)) {
    return
  }

  const normalizePath = value => String(value || '').replace(/^\//, '')

  const getNodePath = (node) => {
    const pathParts = []
    let current = node
    while (current) {
      pathParts.unshift(current.getText())
      current = current.getParent()
    }
    return pathParts.join('/')
  }

  const findNode = (node) => {
    const nodeText = node.getText()
    const nodePath = normalizePath(getNodePath(node))
    const targetPath = normalizePath(path)

    const matched =
      (text && path && nodeText === text && nodePath === targetPath) ||
      (!text && path && nodePath === targetPath) ||
      (text && !path && nodeText === text)

    if (matched) {
      return node
    }

    const children = node.getChildren()
    for (let index = 0; index < children.length; index += 1) {
      const found = findNode(children[index])
      if (found) {
        return found
      }
    }

    return null
  }

  const targetNode = findNode(minder.getRoot())
  if (!targetNode) {
    ElMessage.warning('未找到指定的脑图节点')
    return
  }

  minder.select(targetNode, true)

  let parent = targetNode.getParent()
  while (parent) {
    if (parent.isExpanded && !parent.isExpanded()) {
      minder.execCommand('Expand', parent)
    }
    parent = parent.getParent()
  }

  setTimeout(() => {
    minder.execCommand('camera', targetNode, 600)
  }, 100)
}

const initMinder = () => {
  if (!window.kityminder) {
    ElMessage.error('脑图库加载失败，请刷新页面重试')
    return false
  }

  try {
    minder = new window.kityminder.Minder({
      renderTo: '#minder-viewer'
    })
    minder.importJson(minderData.value)
    minder.execCommand('Theme', minderData.value?.theme || 'fresh-blue')
    minder.execCommand('Template', minderData.value?.template || 'default')
    minder.disable()
    return true
  } catch (error) {
    console.error('初始化脑图失败:', error)
    ElMessage.error('脑图初始化失败：' + error.message)
    return false
  }
}

const loadCaseDetail = async (id) => {
  if (!id) {
    caseInfo.value = createDefaultCaseInfo()
    minderData.value = createDefaultMindmapData()
    ElMessage.warning('缺少脑图 ID')
    return false
  }

  try {
    const response = await api.get(`/testcases/manual-mindmaps/${id}/`)
    const detail = response.data
    const fallbackName = String(detail?.mindmap_data?.root?.data?.text || detail?.name || '未命名脑图').trim()

    caseInfo.value = {
      id: detail.id,
      name: detail.name || fallbackName,
      description: detail.description || '-',
      creator: getUserDisplayName(detail.author, '-'),
      created_at: formatDateTime(detail.created_at),
      updated_at: formatDateTime(detail.updated_at)
    }

    minderData.value = JSON.parse(JSON.stringify(detail.mindmap_data || createDefaultMindmapData(fallbackName)))
    if (!minderData.value?.root?.data?.text) {
      minderData.value.root = minderData.value.root || {}
      minderData.value.root.data = minderData.value.root.data || {}
      minderData.value.root.data.text = caseInfo.value.name
    }

    return true
  } catch (error) {
    console.error('加载脑图详情失败:', error)
    ElMessage.error('加载脑图详情失败：' + (error.response?.data?.detail || error.message))
    return false
  }
}

const renderMindmap = async () => {
  await nextTick()
  resetMinder()

  if (!initMinder()) {
    return
  }

  const targetNodeText = normalizeQueryValue(route.query.node_text)
  const targetNodePath = normalizeQueryValue(route.query.node_path)

  if (targetNodeText || targetNodePath) {
    setTimeout(() => {
      locateAndSelectNode({
        text: targetNodeText,
        path: targetNodePath
      })
    }, 300)
  }
}

const loadCurrentMindmap = async () => {
  const id = normalizeQueryValue(route.query.id)
  const loaded = await loadCaseDetail(id)
  if (!loaded) {
    resetMinder()
    return
  }

  await renderMindmap()
}

onMounted(async () => {
  window.addEventListener('resize', syncWindowHeight)
  await loadCurrentMindmap()
  hasMounted = true
})

watch(
  () => route.fullPath,
  async () => {
    if (!hasMounted) {
      return
    }

    await loadCurrentMindmap()
  }
)

onUnmounted(() => {
  window.removeEventListener('resize', syncWindowHeight)
  resetMinder()
})
</script>

<style scoped>
.manual-testcase-view {
  padding: 0;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 10px;
}

.mindmap-info-panel {
  margin-bottom: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
}

.mindmap-info-panel__toggle {
  width: 100%;
  padding: 14px 16px;
  border: none;
  border-radius: 6px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
  cursor: pointer;
}

.mindmap-info-panel__toggle:hover {
  background: #f5f7fa;
}

.mindmap-info-panel__heading {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mindmap-info-panel__title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.mindmap-info-panel__summary {
  min-width: 0;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mindmap-info-panel__action {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #409eff;
}

.mindmap-info-panel__icon {
  transition: transform 0.2s ease;
}

.mindmap-info-panel__icon.is-collapsed {
  transform: rotate(-90deg);
}

.mindmap-info-panel__content {
  padding: 0 16px 16px;
}

.mindmap-info-panel__value--nowrap {
  white-space: nowrap;
}

:deep(.mindmap-info-panel__content .el-descriptions__label) {
  white-space: nowrap;
}

.minder-container {
  width: 100%;
  min-height: 500px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.el-card) {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
