<template>
  <aside
    class="manual-workspace-directory-panel"
    :class="{
      'left-panel': applyLegacyClass,
      'left-panel--version-only': !showCategoryTree,
      'left-panel--collapsed': collapsed
    }"
  >
    <template v-if="collapsed">
      <div class="directory-collapse-rail">
        <el-button
          circle
          text
          class="directory-toggle-button"
          title="展开左侧面板"
          @click="emit('toggle')"
        >
          <el-icon><ArrowRight /></el-icon>
        </el-button>
        <span class="directory-rail-label">{{ railLabel }}</span>
      </div>
    </template>
    <template v-else>
      <div class="tree-header">
        <div class="tree-header-top">
          <span class="tree-header-title">{{ title }}</span>
          <el-button
            circle
            text
            class="directory-toggle-button"
            title="收起左侧面板"
            @click="emit('toggle')"
          >
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
        </div>
        <template v-if="showCategoryTree">
          <el-divider class="tree-divider" />
          <div class="search-row">
            <el-input
              :model-value="filterText"
              placeholder="搜索目录"
              clearable
              size="small"
              class="tree-search"
              @update:model-value="value => emit('update:filterText', value)"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-tooltip v-if="showAddActions && currentCategory" content="清除目录选择" placement="top">
              <el-button
                circle
                plain
                size="small"
                class="tree-action-button"
                aria-label="清除目录选择"
                @click="clearCurrentCategory"
              >
                <el-icon><CircleClose /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="showAddActions" :content="categoryImportTooltip" placement="top">
              <el-button
                circle
                plain
                size="small"
                class="tree-action-button"
                :loading="categoryImporting"
                aria-label="导入 XMind"
                @click="triggerCategoryXMindImport"
              >
                <el-icon><Upload /></el-icon>
              </el-button>
            </el-tooltip>
            <el-dropdown v-if="showAddActions" trigger="click" @command="command => emit('add-category', command)">
              <el-button type="primary" size="small" class="tree-action-button">
                <el-icon><Plus /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="root">添加一级目录</el-dropdown-item>
                  <el-dropdown-item command="child" :disabled="!currentCategory || currentCategory.isVirtual">添加子目录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <input
              ref="categoryXMindInputRef"
              type="file"
              accept=".xmind"
              class="category-xmind-input"
              @change="handleCategoryXMindFileChange"
            />
          </div>
        </template>
        <div v-else class="version-link-hint">
          {{ hint }}
        </div>
      </div>

      <div v-if="showCategoryTree" class="tree-content">
        <el-tree
          ref="innerTreeRef"
          :data="categoryTree"
          :props="treeProps"
          :default-expanded-keys="expandedCategoryKeys"
          node-key="id"
          highlight-current
          :expand-on-click-node="false"
          :filter-node-method="resolveFilterNode"
          @node-click="data => emit('node-click', data)"
          @node-contextmenu="(event, data) => emit('node-contextmenu', event, data)"
        >
          <template #default="{ node, data }">
            <span class="custom-tree-node">
              <span>{{ node.label }}</span>
              <span v-if="canEditCategory && !data.isVirtual" class="node-actions">
                <el-icon @click.stop="emit('edit-category', data)"><Edit /></el-icon>
                <el-icon @click.stop="emit('delete-category', data)"><Delete /></el-icon>
              </span>
            </span>
          </template>
        </el-tree>
        <el-empty
          v-if="!categoryTree.length && !loading"
          :description="emptyDescription"
          :image-size="64"
        />
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight, CircleClose, Delete, Edit, Plus, Search, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  showCategoryTree: {
    type: Boolean,
    default: true
  },
  title: {
    type: String,
    default: '目录树'
  },
  railLabel: {
    type: String,
    default: '目录树'
  },
  hint: {
    type: String,
    default: ''
  },
  filterText: {
    type: String,
    default: ''
  },
  categoryTree: {
    type: Array,
    default: () => []
  },
  treeProps: {
    type: Object,
    default: () => ({ children: 'children', label: 'label' })
  },
  expandedCategoryKeys: {
    type: Array,
    default: () => []
  },
  currentCategory: {
    type: Object,
    default: null
  },
  showAddActions: {
    type: Boolean,
    default: true
  },
  canEditCategory: {
    type: Boolean,
    default: true
  },
  categoryImporting: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  emptyDescription: {
    type: String,
    default: '暂无目录数据'
  },
  filterNodeMethod: {
    type: Function,
    default: null
  },
  applyLegacyClass: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'toggle',
  'update:filterText',
  'add-category',
  'node-click',
  'node-contextmenu',
  'edit-category',
  'delete-category',
  'import-xmind'
])

const innerTreeRef = ref(null)
const categoryXMindInputRef = ref(null)
const categoryImportTooltip = computed(() => {
  if (props.currentCategory && !props.currentCategory.isVirtual) {
    return `导入 XMind 到“${props.currentCategory.label || '所选目录'}”下`
  }
  return '导入 XMind 到目录树根级'
})

const clearCurrentCategory = () => {
  innerTreeRef.value?.setCurrentKey?.(null)
  emit('node-click', null)
}

const triggerCategoryXMindImport = () => {
  if (props.categoryImporting) return
  if (categoryXMindInputRef.value) {
    categoryXMindInputRef.value.value = ''
    categoryXMindInputRef.value.click()
  }
}

const handleCategoryXMindFileChange = event => {
  const file = event?.target?.files?.[0]
  if (file) {
    emit('import-xmind', file)
  }
  if (event?.target) {
    event.target.value = ''
  }
}

const resolveFilterNode = (value, data) => {
  if (props.filterNodeMethod) {
    return props.filterNodeMethod(value, data)
  }
  const keyword = String(value || '').trim().toLowerCase()
  if (!keyword) return true
  return [data?.label, data?.fullPath].some(item => String(item || '').toLowerCase().includes(keyword))
}

watch(
  () => props.filterText,
  value => {
    innerTreeRef.value?.filter?.(value)
  }
)

watch(
  () => props.currentCategory?.id,
  async id => {
    await nextTick()
    if (id !== undefined && id !== null && id !== '') {
      innerTreeRef.value?.setCurrentKey?.(id)
    } else {
      innerTreeRef.value?.setCurrentKey?.(null)
    }
  },
  { immediate: true }
)

const filter = value => innerTreeRef.value?.filter?.(value)
const setCurrentKey = key => innerTreeRef.value?.setCurrentKey?.(key)

defineExpose({
  filter,
  setCurrentKey
})
</script>

<style scoped>
.manual-workspace-directory-panel {
  width: 260px;
  flex-shrink: 0;
  min-width: 0;
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  transition: width 0.2s ease;
}

.left-panel--collapsed {
  width: 56px;
  align-items: center;
}

.left-panel--version-only {
  justify-content: flex-start;
}

.tree-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tree-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tree-header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.tree-divider {
  margin: 0;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-search {
  flex: 1;
  min-width: 0;
}

.tree-action-button {
  flex: 0 0 28px;
  width: 28px;
  min-width: 28px;
  padding: 0;
}

.category-xmind-input {
  display: none;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-link-hint {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.directory-collapse-rail {
  width: 100%;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.directory-toggle-button {
  flex-shrink: 0;
}

.directory-rail-label {
  color: #909399;
  font-size: 12px;
  line-height: 1;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding-right: 8px;
}

.node-actions {
  display: none;
  gap: 8px;
}

.custom-tree-node:hover .node-actions {
  display: flex;
}

.node-actions .el-icon {
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
}

.node-actions .el-icon:hover {
  background-color: #f5f7fa;
  color: #409eff;
}
</style>
