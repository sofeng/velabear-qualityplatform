<template>
  <div class="manual-page-list-config-panel">
    <aside class="config-page-selector">
      <div class="selector-header">
        <span>目标页面</span>
        <el-button text :icon="Refresh" :loading="registryLoading" @click="loadRegistry" />
      </div>
      <el-input
        v-model="pageKeyword"
        clearable
        placeholder="搜索页面"
        size="small"
      />
      <div class="selector-list">
        <button
          v-for="page in filteredPages"
          :key="page.page_key"
          type="button"
          class="selector-item"
          :class="{ 'is-active': selectedPageKey === page.page_key }"
          @click="handleSelectPage(page.page_key)"
        >
          <span>{{ page.page_name }}</span>
          <small>{{ page.page_key }}</small>
        </button>
      </div>
    </aside>

    <section class="config-workbench" v-loading="configLoading || registryLoading">
      <div class="config-workbench__header">
        <div>
          <h2>{{ selectedPage?.page_name || '列表排序' }}</h2>
          <span>{{ selectedPage?.page_key || '-' }}</span>
        </div>
        <div class="config-actions">
          <el-tag v-if="configState.isFactory" effect="plain" type="info">默认配置</el-tag>
          <el-tag v-else effect="plain" type="success">后台配置 v{{ configState.version }}</el-tag>
          <el-button :loading="configLoading" @click="loadPageConfig">刷新</el-button>
          <el-button :loading="saving" @click="handleRestoreDefault">恢复出厂默认</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存后台默认</el-button>
        </div>
      </div>

      <el-tabs v-model="activeConfigTab" class="config-inner-tabs">
        <el-tab-pane label="筛选条件" name="filters">
          <div class="inner-toolbar">
            <div class="inner-toolbar__title">
              <strong>筛选条件配置</strong>
              <span>配置目标页面筛选栏的后台默认字段、控件类型与顺序</span>
            </div>
            <el-button type="primary" :icon="Plus" @click="addFilterCondition">新增筛选条件</el-button>
          </div>

          <draggable
            v-model="filterConditions"
            item-key="id"
            tag="div"
            class="config-list"
            handle=".drag-handle"
            @change="normalizeFilterOrder"
          >
            <template #item="{ element, index }">
              <div class="config-row">
                <el-icon class="drag-handle"><Rank /></el-icon>
                <span class="order-badge">{{ index + 1 }}</span>
                <el-select
                  v-model="element.field_key"
                  filterable
                  placeholder="选择字段"
                  class="field-select"
                  @change="handleFilterFieldChange(element)"
                >
                  <el-option
                    v-for="field in filterableFields"
                    :key="field.field_key"
                    :label="field.label"
                    :value="field.field_key"
                  />
                </el-select>
                <el-select v-model="element.filter_type" placeholder="控件类型" class="type-select">
                  <el-option
                    v-for="type in getFilterControlOptions(element.field_key)"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  />
                </el-select>
                <el-input v-model="element.label_override" clearable placeholder="显示名称" class="small-input" />
                <el-input v-model="element.placeholder" clearable placeholder="占位提示" class="placeholder-input" />
                <el-switch v-model="element.enabled" active-text="启用" inactive-text="停用" />
                <el-button link type="danger" :icon="Delete" @click="removeFilterCondition(index)">删除</el-button>
              </div>
            </template>
          </draggable>
          <el-empty v-if="!filterConditions.length" description="暂无筛选条件" :image-size="64" />
        </el-tab-pane>

        <el-tab-pane label="列表字段" name="columns">
          <div class="inner-toolbar">
            <div class="inner-toolbar__title">
              <strong>列表字段默认排序</strong>
              <span>配置新浏览器和未设置个人偏好的用户看到的后台默认列顺序</span>
            </div>
            <div class="inner-toolbar__actions">
              <el-button @click="showAllColumns">全部显示</el-button>
              <el-button @click="hideOptionalColumns">只保留固定字段</el-button>
            </div>
          </div>

          <draggable
            v-model="columns"
            item-key="field_key"
            tag="div"
            class="config-list config-list--columns"
            handle=".drag-handle"
            @change="normalizeColumnOrder"
          >
            <template #item="{ element, index }">
              <div class="config-row column-row" :class="{ 'is-locked': element.locked }">
                <el-icon class="drag-handle"><Rank /></el-icon>
                <span class="order-badge">{{ index + 1 }}</span>
                <span class="column-label">{{ getFieldLabel(element.field_key) }}</span>
                <span class="column-key">{{ element.field_key }}</span>
                <el-input v-model="element.label_override" clearable placeholder="显示名称" class="small-input" />
                <el-switch
                  v-model="element.visible"
                  :disabled="element.locked || isLastVisibleColumn(element)"
                  active-text="显示"
                  inactive-text="隐藏"
                />
                <el-tag v-if="element.locked" size="small" type="info">固定</el-tag>
              </div>
            </template>
          </draggable>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Rank, Refresh } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import {
  getManualWorkspacePageListConfig,
  getManualWorkspacePageListRegistry,
  restoreManualWorkspacePageListConfig,
  saveManualWorkspacePageListConfig,
} from '@/api/testcases'
import { notifyManualPageListConfigUpdated } from '@/utils/manualPageListConfigEvents'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
})

const CONTROL_LABELS = {
  text: '文本',
  single_select: '单选',
  multi_select: '多选',
  number: '数字',
  number_range: '数字范围',
  date: '日期',
  date_range: '日期范围',
  boolean: '布尔',
}

const registryLoading = ref(false)
const configLoading = ref(false)
const saving = ref(false)
const initialized = ref(false)
const pageKeyword = ref('')
const selectedPageKey = ref('')
const activeConfigTab = ref('filters')
const pages = ref([])
const filterConditions = ref([])
const columns = ref([])
const configState = reactive({
  version: 0,
  isFactory: true,
})

const filteredPages = computed(() => {
  const keyword = pageKeyword.value.trim().toLowerCase()
  if (!keyword) return pages.value
  return pages.value.filter(page => (
    page.page_name.toLowerCase().includes(keyword) ||
    page.page_key.toLowerCase().includes(keyword)
  ))
})

const selectedPage = computed(() => pages.value.find(page => page.page_key === selectedPageKey.value) || null)
const fields = computed(() => selectedPage.value?.fields || [])
const fieldMap = computed(() => new Map(fields.value.map(field => [field.field_key, field])))
const filterableFields = computed(() => fields.value.filter(field => field.filterable))

const cloneRows = rows => JSON.parse(JSON.stringify(rows || []))

const getFieldLabel = fieldKey => fieldMap.value.get(fieldKey)?.label || fieldKey

const getFilterControlOptions = fieldKey => {
  const field = fieldMap.value.get(fieldKey)
  const controls = field?.supported_filter_controls || ['text']
  return controls.map(value => ({ value, label: CONTROL_LABELS[value] || value }))
}

const normalizeFilterOrder = () => {
  filterConditions.value = filterConditions.value.map((item, index) => ({ ...item, order: index + 1 }))
}

const normalizeColumnOrder = () => {
  columns.value = columns.value.map((item, index) => ({ ...item, order: index + 1 }))
}

const applyConfigPayload = payload => {
  configState.version = Number(payload?.version || 0)
  configState.isFactory = Boolean(payload?.is_factory)
  filterConditions.value = cloneRows(payload?.filter_conditions).sort((a, b) => (a.order || 0) - (b.order || 0))
  columns.value = cloneRows(payload?.columns).sort((a, b) => (a.order || 0) - (b.order || 0))
  normalizeFilterOrder()
  normalizeColumnOrder()
}

const loadRegistry = async () => {
  registryLoading.value = true
  try {
    const response = await getManualWorkspacePageListRegistry()
    pages.value = response.data?.pages || []
    if (!selectedPageKey.value && pages.value.length) {
      selectedPageKey.value = pages.value[0].page_key
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载页面字段注册表失败')
  } finally {
    registryLoading.value = false
  }
}

const loadPageConfig = async () => {
  if (!selectedPageKey.value) return
  configLoading.value = true
  try {
    const response = await getManualWorkspacePageListConfig({ page_key: selectedPageKey.value })
    applyConfigPayload(response.data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载列表排序配置失败')
  } finally {
    configLoading.value = false
  }
}

const handleSelectPage = pageKey => {
  if (selectedPageKey.value === pageKey) return
  selectedPageKey.value = pageKey
}

const buildNewFilterCondition = field => {
  const control = field?.supported_filter_controls?.[0] || 'text'
  return {
    id: `filter-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    field_key: field?.field_key || '',
    label_override: '',
    filter_type: control,
    operator: control === 'text' ? 'contains' : 'eq',
    placeholder: field?.label ? `请输入${field.label}` : '',
    option_source: field?.option_source || '',
    enabled: true,
    order: filterConditions.value.length + 1,
  }
}

const addFilterCondition = () => {
  const used = new Set(filterConditions.value.map(item => item.field_key))
  const field = filterableFields.value.find(item => !used.has(item.field_key)) || filterableFields.value[0]
  if (!field) {
    ElMessage.warning('当前页面没有可配置的筛选字段')
    return
  }
  filterConditions.value.push(buildNewFilterCondition(field))
  normalizeFilterOrder()
}

const removeFilterCondition = index => {
  filterConditions.value.splice(index, 1)
  normalizeFilterOrder()
}

const handleFilterFieldChange = row => {
  const field = fieldMap.value.get(row.field_key)
  if (!field) return
  const controls = field.supported_filter_controls || ['text']
  if (!controls.includes(row.filter_type)) {
    row.filter_type = controls[0]
  }
  if (!row.placeholder) {
    row.placeholder = `请输入${field.label}`
  }
  row.option_source = field.option_source || row.option_source || ''
}

const visibleColumnCount = computed(() => columns.value.filter(item => item.visible).length)
const isLastVisibleColumn = item => item.visible && !item.locked && visibleColumnCount.value <= 1

const showAllColumns = () => {
  columns.value = columns.value.map(item => ({ ...item, visible: true }))
}

const hideOptionalColumns = () => {
  columns.value = columns.value.map(item => ({ ...item, visible: Boolean(item.locked) }))
  if (!columns.value.some(item => item.visible) && columns.value.length) {
    columns.value[0].visible = true
  }
}

const buildPayload = () => ({
  module_key: 'manual-testcases',
  page_key: selectedPageKey.value,
  version: configState.version || undefined,
  filter_conditions: filterConditions.value,
  columns: columns.value,
})

const notifyCurrentPageConfigUpdated = payload => {
  notifyManualPageListConfigUpdated({
    module_key: payload?.module_key || 'manual-testcases',
    page_key: payload?.page_key || selectedPageKey.value,
    storage_keys: selectedPage.value?.storage_keys || [],
    version: payload?.version,
  })
}

const handleSave = async () => {
  saving.value = true
  try {
    normalizeFilterOrder()
    normalizeColumnOrder()
    const response = await saveManualWorkspacePageListConfig(buildPayload())
    applyConfigPayload(response.data)
    notifyCurrentPageConfigUpdated(response.data)
    ElMessage.success('列表排序配置已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.columns || error.response?.data?.filter_conditions || '保存列表排序配置失败')
  } finally {
    saving.value = false
  }
}

const handleRestoreDefault = async () => {
  try {
    await ElMessageBox.confirm('确定恢复当前页面的出厂默认筛选条件和列表字段顺序？', '恢复默认', {
      type: 'warning',
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
    })
  } catch (error) {
    return
  }

  saving.value = true
  try {
    const response = await restoreManualWorkspacePageListConfig({
      module_key: 'manual-testcases',
      page_key: selectedPageKey.value,
      version: configState.version || undefined,
    })
    applyConfigPayload(response.data)
    notifyCurrentPageConfigUpdated(response.data)
    ElMessage.success('已恢复出厂默认')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '恢复默认失败')
  } finally {
    saving.value = false
  }
}

watch(selectedPageKey, () => {
  if (selectedPageKey.value) {
    loadPageConfig()
  }
})

watch(
  () => props.active,
  value => {
    if (value && !initialized.value) {
      initialized.value = true
      loadRegistry()
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.active && !initialized.value) {
    initialized.value = true
    loadRegistry()
  }
})
</script>

<style scoped lang="scss">
.manual-page-list-config-panel {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 12px;
  min-height: calc(100vh - 180px);
}

.config-page-selector,
.config-workbench {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.config-page-selector {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.selector-header,
.config-workbench__header,
.inner-toolbar,
.config-actions,
.inner-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-header,
.config-workbench__header,
.inner-toolbar {
  justify-content: space-between;
}

.selector-header span {
  font-weight: 600;
  color: #1f2937;
}

.selector-list {
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 2px;
}

.selector-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 5px;
  background: transparent;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
}

.selector-item span,
.selector-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-item span {
  color: #1f2937;
  font-weight: 500;
}

.selector-item small {
  margin-top: 2px;
  color: #8a96a3;
}

.selector-item.is-active {
  border-color: #409eff;
  background: #ecf5ff;
}

.config-workbench {
  padding: 12px;
  min-width: 0;
  overflow: hidden;
}

.config-workbench__header {
  margin-bottom: 10px;
}

.config-workbench__header h2 {
  margin: 0;
  font-size: 15px;
  color: #1f2937;
}

.config-workbench__header span,
.inner-toolbar__title span {
  color: #7b8794;
  font-size: 12px;
}

.inner-toolbar {
  margin-bottom: 10px;
  min-height: 32px;
}

.inner-toolbar__title strong,
.inner-toolbar__title span {
  display: block;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: calc(100vh - 300px);
  overflow: auto;
  padding-right: 2px;
}

.config-row {
  min-height: 40px;
  display: grid;
  grid-template-columns: 22px 34px minmax(160px, 1.2fr) 110px minmax(100px, .8fr) minmax(140px, 1fr) 86px 52px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.column-row {
  grid-template-columns: 22px 34px minmax(120px, 1fr) minmax(160px, 1fr) minmax(110px, .8fr) 86px 52px;
}

.column-row.is-locked {
  background: #f8fafc;
}

.drag-handle {
  color: #8a96a3;
  cursor: grab;
}

.order-badge {
  color: #667085;
  text-align: center;
}

.field-select,
.type-select,
.small-input,
.placeholder-input {
  width: 100%;
}

.column-label {
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-key {
  color: #8a96a3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .manual-page-list-config-panel {
    grid-template-columns: 1fr;
  }

  .selector-list {
    max-height: 220px;
  }

  .config-row,
  .column-row {
    grid-template-columns: 22px 34px minmax(160px, 1fr) minmax(110px, 1fr);
  }
}
</style>
