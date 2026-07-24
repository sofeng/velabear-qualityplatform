<template>
  <div ref="rootRef" class="table-column-settings">
    <el-popover
      v-model:visible="popoverVisible"
      placement="bottom-end"
      trigger="manual"
      width="360"
      :popper-class="popoverClass"
      @show="handlePopoverShow"
    >
      <template #reference>
        <el-tooltip content="设置列表字段" placement="top">
          <el-button
            :icon="Setting"
            :size="size"
            circle
            @click.stop="togglePopover"
          />
        </el-tooltip>
      </template>

      <div class="column-settings">
        <template v-if="columns.length">
          <div class="column-settings__header">
            <div>
              <strong>列表字段设置</strong>
              <span>{{ backendDefaultLoaded ? '拖拽调整展示顺序，默认来自后台配置' : '拖拽调整展示顺序' }}</span>
            </div>
            <div class="column-settings__header-actions">
              <el-button link type="primary" :icon="RefreshLeft" @click="resetColumns">恢复后台默认</el-button>
              <el-button link :icon="RefreshLeft" @click="resetFactoryColumns">出厂默认</el-button>
            </div>
          </div>

          <draggable
            v-model="columns"
            item-key="key"
            tag="div"
            class="column-settings__list"
            handle=".column-settings__drag-handle"
            @change="handleOrderChange"
          >
            <template #item="{ element }">
              <div class="column-settings__item" :class="{ 'is-locked': element.locked }">
                <el-icon class="column-settings__drag-handle"><Rank /></el-icon>
                <el-checkbox
                  :model-value="element.visible"
                  :disabled="element.locked || isLastVisibleConfigurableColumn(element)"
                  @change="value => handleVisibleChange(element, value)"
                >
                  {{ element.label }}
                </el-checkbox>
                <el-tag v-if="element.locked" size="small" type="info">固定</el-tag>
              </div>
            </template>
          </draggable>
        </template>
        <div v-else class="column-settings__empty">
          表格字段尚未加载，请稍后重试。
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { Rank, RefreshLeft, Setting } from '@element-plus/icons-vue'
import { getManualWorkspacePageListConfig } from '@/api/testcases'
import {
  MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT,
  isManualPageListConfigUpdateForStorage,
} from '@/utils/manualPageListConfigEvents'

const props = defineProps({
  tableRef: {
    type: Object,
    default: null,
  },
  storageKey: {
    type: String,
    required: true,
  },
  size: {
    type: String,
    default: 'small',
  },
})

const STORAGE_PREFIX = 'testhub:table-column-settings:'

const rootRef = ref(null)
const popoverVisible = ref(false)
const columns = ref([])
const originalOrder = ref([])
const backendDefault = ref(null)
const backendDefaultLoaded = ref(false)
const initialized = ref(false)
const applying = ref(false)
const popoverClassName = `table-column-settings-popover-${Math.random().toString(36).slice(2)}`
const popoverClass = `table-column-settings-popover ${popoverClassName}`

const storageKey = computed(() => `${STORAGE_PREFIX}${props.storageKey}`)

const getBackendSignature = () => {
  const columns = Array.isArray(backendDefault.value?.columns) ? backendDefault.value.columns : []
  return columns
    .map(item => [
      item.field_key || '',
      item.visible === false ? '0' : '1',
      item.locked ? '1' : '0',
    ].join(':'))
    .join('|')
}

const getStoredSettings = () => {
  try {
    const stored = JSON.parse(window.localStorage.getItem(storageKey.value) || '{}')
    if (!stored || typeof stored !== 'object') {
      return {}
    }

    const backendVersion = Number(backendDefault.value?.version || 0)
    const storedBackendVersion = Number(stored.backendVersion || 0)
    const backendSignature = getBackendSignature()
    const storedBackendSignature = String(stored.backendSignature || '')
    const backendSignatureChanged = Boolean(backendSignature && backendSignature !== storedBackendSignature)
    if (backendDefaultLoaded.value && (backendVersion !== storedBackendVersion || backendSignatureChanged)) {
      window.localStorage.removeItem(storageKey.value)
      return {}
    }

    return stored
  } catch (error) {
    return {}
  }
}

const getBackendSettings = () => {
  const columns = Array.isArray(backendDefault.value?.columns) ? backendDefault.value.columns : []
  if (!columns.length) {
    return {}
  }
  return {
    order: columns.map(item => item.field_key).filter(Boolean),
    hidden: columns.filter(item => !item.locked && item.visible === false).map(item => item.field_key).filter(Boolean),
  }
}

const resolveInitialSettings = () => {
  const stored = getStoredSettings()
  const hasStoredOrder = Array.isArray(stored.order) && stored.order.length
  const hasStoredHidden = Array.isArray(stored.hidden) && stored.hidden.length
  if (hasStoredOrder || hasStoredHidden) {
    return stored
  }
  return getBackendSettings()
}

const saveSettings = () => {
  const payload = {
    order: columns.value.map(item => item.key),
    hidden: columns.value.filter(item => !item.locked && !item.visible).map(item => item.key),
    backendVersion: Number(backendDefault.value?.version || 0),
    backendSignature: getBackendSignature(),
  }
  window.localStorage.setItem(storageKey.value, JSON.stringify(payload))
}

const getTableColumns = () => props.tableRef?.store?.states?._columns?.value || []

const normalizeColumnLabel = column => {
  if (column?.label) {
    return String(column.label)
  }
  if (column?.type === 'selection') {
    return '选择'
  }
  if (column?.type === 'index') {
    return '序号'
  }
  if (column?.type === 'expand') {
    return '展开'
  }
  return column?.property || column?.id || '未命名字段'
}

const getColumnBaseKey = column => {
  if (column?.type && column.type !== 'default') {
    return `type:${column.type}`
  }
  if (column?.columnKey) {
    const explicitKey = String(column.columnKey)
    if (/^(prop|label|type):/.test(explicitKey)) {
      return explicitKey
    }
    return `key:${explicitKey}`
  }
  if (column?.property) {
    return `prop:${column.property}`
  }
  return `label:${normalizeColumnLabel(column)}`
}

const ensureColumnKey = (column, usedKeys) => {
  if (column.__tableColumnSettingsKey && !usedKeys.has(column.__tableColumnSettingsKey)) {
    usedKeys.add(column.__tableColumnSettingsKey)
    return column.__tableColumnSettingsKey
  }

  const baseKey = getColumnBaseKey(column)
  let key = baseKey
  let index = 2
  while (usedKeys.has(key)) {
    key = `${baseKey}:${index}`
    index += 1
  }
  usedKeys.add(key)
  Object.defineProperty(column, '__tableColumnSettingsKey', {
    value: key,
    configurable: true,
    writable: true,
    enumerable: false,
  })
  return key
}

const isLockedColumn = column => (
  Boolean(column?.type && column.type !== 'default') ||
  normalizeColumnLabel(column) === '操作'
)

const orderColumns = (items, order) => {
  const itemMap = new Map(items.map(item => [item.key, item]))
  const ordered = []
  ;(Array.isArray(order) ? order : []).forEach(key => {
    if (itemMap.has(key)) {
      ordered.push(itemMap.get(key))
      itemMap.delete(key)
    }
  })
  return [...ordered, ...itemMap.values()]
}

const syncColumnsFromTable = () => {
  if (!props.tableRef || applying.value) {
    return
  }

  const tableColumns = getTableColumns()
  if (!tableColumns.length && !columns.value.length) {
    return
  }

  const stored = resolveInitialSettings()
  const hiddenSet = new Set(Array.isArray(stored.hidden) ? stored.hidden : [])
  const currentByKey = new Map(columns.value.map(item => [item.key, item]))
  const usedKeys = new Set()
  const nextColumns = columns.value.map(item => ({ ...item, present: false }))

  tableColumns.forEach(column => {
    const key = ensureColumnKey(column, usedKeys)
    const existingIndex = nextColumns.findIndex(item => item.key === key)
    const locked = isLockedColumn(column)
    const visible = locked ? true : !hiddenSet.has(key)
    const nextItem = {
      ...(currentByKey.get(key) || {}),
      key,
      label: normalizeColumnLabel(column),
      column,
      locked,
      visible: currentByKey.has(key) ? currentByKey.get(key).visible : visible,
      present: true,
    }

    if (existingIndex >= 0) {
      nextColumns.splice(existingIndex, 1, nextItem)
    } else {
      nextColumns.push(nextItem)
    }
  })

  if (!originalOrder.value.length) {
    originalOrder.value = nextColumns.map(item => item.key)
  }

  columns.value = orderColumns(nextColumns, initialized.value ? columns.value.map(item => item.key) : stored.order)
  initialized.value = true
  applyColumns()
}

const applyColumns = async () => {
  if (!props.tableRef?.store?.states?._columns) {
    return
  }

  applying.value = true
  const visibleColumns = columns.value
    .filter(item => item.visible && (item.present || item.column))
    .map(item => item.column)
    .filter(Boolean)

  props.tableRef.store.states._columns.value = visibleColumns
  props.tableRef.store.updateColumns?.()
  props.tableRef.store.scheduleLayout?.(true, true)
  await nextTick()
  props.tableRef?.doLayout?.()
  applying.value = false
}

const visibleConfigurableColumnCount = computed(() =>
  columns.value.filter(item => !item.locked && item.visible).length
)

const isLastVisibleConfigurableColumn = item => (
  !item.locked && item.visible && visibleConfigurableColumnCount.value <= 1
)

const handleVisibleChange = async (item, value) => {
  if (item.locked || (item.visible && !value && isLastVisibleConfigurableColumn(item))) {
    return
  }
  item.visible = Boolean(value)
  saveSettings()
  await applyColumns()
}

const handleOrderChange = async () => {
  saveSettings()
  await applyColumns()
}

const resetColumns = async () => {
  window.localStorage.removeItem(storageKey.value)
  const backend = getBackendSettings()
  columns.value = orderColumns(
    columns.value.map(item => ({
      ...item,
      visible: item.locked ? true : !(backend.hidden || []).includes(item.key),
    })),
    backend.order || originalOrder.value
  )
  await applyColumns()
}

const resetFactoryColumns = async () => {
  window.localStorage.removeItem(storageKey.value)
  columns.value = orderColumns(
    columns.value.map(item => ({
      ...item,
      visible: true,
    })),
    originalOrder.value
  )
  await applyColumns()
}

const loadBackendDefault = async () => {
  if (backendDefaultLoaded.value) {
    return
  }
  try {
    const response = await getManualWorkspacePageListConfig({ storage_key: props.storageKey })
    backendDefault.value = response.data || null
  } catch (error) {
    backendDefault.value = null
  } finally {
    backendDefaultLoaded.value = true
  }
}

const reloadBackendDefault = async () => {
  backendDefaultLoaded.value = false
  await loadBackendDefault()
  initialized.value = false
  syncColumnsFromTable()
}

const handleBackendConfigUpdated = async event => {
  if (!isManualPageListConfigUpdateForStorage(event, props.storageKey)) {
    return
  }
  await reloadBackendDefault()
}

const handlePopoverShow = async () => {
  await loadBackendDefault()
  await nextTick()
  syncColumnsFromTable()
}

const togglePopover = () => {
  popoverVisible.value = !popoverVisible.value
}

const isEventInsidePopover = target => {
  if (!(target instanceof Node)) {
    return false
  }

  if (rootRef.value?.contains(target)) {
    return true
  }

  const popper = document.querySelector(`.${popoverClassName}`)
  return Boolean(popper?.contains(target))
}

const handleDocumentPointerDown = event => {
  if (!popoverVisible.value) {
    return
  }
  if (isEventInsidePopover(event.target)) {
    return
  }
  popoverVisible.value = false
}

watch(
  () => props.tableRef,
  async tableRef => {
    if (tableRef) {
      await loadBackendDefault()
      await nextTick()
      syncColumnsFromTable()
    }
  },
  { immediate: true, flush: 'post' }
)

onMounted(async () => {
  await loadBackendDefault()
  await nextTick()
  syncColumnsFromTable()
  document.addEventListener('pointerdown', handleDocumentPointerDown, true)
  window.addEventListener(MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT, handleBackendConfigUpdated)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true)
  window.removeEventListener(MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT, handleBackendConfigUpdated)
})
</script>

<style scoped lang="scss">
.column-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.column-settings__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;

  strong,
  span {
    display: block;
  }

  strong {
    color: #1f2f3d;
    font-size: 14px;
  }

  span {
    margin-top: 3px;
    color: #7b8794;
    font-size: 12px;
  }
}

.column-settings__header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.column-settings__list {
  max-height: 360px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.column-settings__item {
  min-height: 36px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid #e3e8ef;
  border-radius: 6px;
  background: #fff;
}

.column-settings__item.is-locked {
  background: #f7f9fc;
}

.column-settings__drag-handle {
  flex-shrink: 0;
  color: #8a96a3;
  cursor: grab;
}

.column-settings__item :deep(.el-checkbox) {
  flex: 1;
  min-width: 0;
  margin-right: 0;
}

.column-settings__item :deep(.el-checkbox__label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-settings__empty {
  padding: 18px 8px;
  color: #7b8794;
  font-size: 13px;
  text-align: center;
}
</style>

<style lang="scss">
.table-column-settings-popover {
  padding: 14px !important;
}
</style>
