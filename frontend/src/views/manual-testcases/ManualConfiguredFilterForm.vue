<template>
  <el-form :inline="true" :model="modelValue" class="manual-configured-filter-form search-form" @submit.prevent>
    <el-form-item
      v-for="filter in visibleFilters"
      :key="filter.id || filter.field_key"
      :label="filter.label"
    >
      <el-select
        v-if="shouldRenderSelect(filter)"
        :model-value="getValue(filter.field_key)"
        :multiple="filter.filter_type === 'multi_select'"
        clearable
        filterable
        collapse-tags
        collapse-tags-tooltip
        :placeholder="filter.placeholder || `请选择${filter.label}`"
        @change="value => commitFilterValue(filter.field_key, value)"
        @clear="() => handleClear(filter.field_key)"
      >
        <el-option
          v-for="option in getFilterOptions(filter)"
          :key="String(option.value)"
          :label="option.label"
          :value="option.value"
        />
      </el-select>

      <el-select
        v-else-if="filter.filter_type === 'boolean'"
        :model-value="getValue(filter.field_key)"
        clearable
        :placeholder="filter.placeholder || `请选择${filter.label}`"
        @change="value => commitFilterValue(filter.field_key, value)"
        @clear="() => handleClear(filter.field_key)"
      >
        <el-option label="是" :value="true" />
        <el-option label="否" :value="false" />
      </el-select>

      <el-date-picker
        v-else-if="filter.filter_type === 'date_range'"
        :model-value="getValue(filter.field_key)"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @update:model-value="value => updateFilterValue(filter.field_key, value)"
        @change="value => commitFilterValue(filter.field_key, value)"
      />

      <el-date-picker
        v-else-if="filter.filter_type === 'date'"
        :model-value="getValue(filter.field_key)"
        type="date"
        value-format="YYYY-MM-DD"
        :placeholder="filter.placeholder || `请选择${filter.label}`"
        @update:model-value="value => updateFilterValue(filter.field_key, value)"
        @change="value => commitFilterValue(filter.field_key, value)"
      />

      <div v-else-if="filter.filter_type === 'number_range'" class="manual-configured-filter-form__range">
        <el-input-number
          :model-value="getRangeValue(filter.field_key, 0)"
          controls-position="right"
          :placeholder="filter.placeholder || '最小值'"
          @change="value => commitRangeValue(filter.field_key, 0, value)"
        />
        <span>-</span>
        <el-input-number
          :model-value="getRangeValue(filter.field_key, 1)"
          controls-position="right"
          placeholder="最大值"
          @change="value => commitRangeValue(filter.field_key, 1, value)"
        />
      </div>

      <el-input-number
        v-else-if="filter.filter_type === 'number'"
        :model-value="getValue(filter.field_key)"
        controls-position="right"
        :placeholder="filter.placeholder || `请输入${filter.label}`"
        @change="value => commitFilterValue(filter.field_key, value)"
      />

      <el-input
        v-else
        :model-value="getValue(filter.field_key)"
        clearable
        :placeholder="filter.placeholder || `请输入${filter.label}`"
        @update:model-value="value => updateFilterValue(filter.field_key, value)"
        @keyup.enter="emitSearch"
        @clear="() => handleClear(filter.field_key)"
      />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :loading="loading" @click="emitSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-button :loading="loading" @click="handleReset">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { getManualWorkspacePageListConfig } from '@/api/testcases'
import {
  MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT,
  isManualPageListConfigUpdateForStorage,
} from '@/utils/manualPageListConfigEvents'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({}),
  },
  storageKey: {
    type: String,
    required: true,
  },
  filterOptionMap: {
    type: Object,
    default: () => ({}),
  },
  fallbackConditions: {
    type: Array,
    default: () => [],
  },
  fallbackFieldsRegistry: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'search', 'reset', 'loaded'])

const loading = ref(false)
const configLoaded = ref(false)
const configPayload = ref(null)

const normalizeRows = rows => (Array.isArray(rows) ? rows : [])

const fieldsRegistry = computed(() => (
  configLoaded.value
    ? normalizeRows(configPayload.value?.fields_registry)
    : props.fallbackFieldsRegistry
))

const fieldMap = computed(() => new Map(fieldsRegistry.value.map(field => [field.field_key, field])))

const configuredConditions = computed(() => (
  configLoaded.value
    ? normalizeRows(configPayload.value?.filter_conditions)
    : props.fallbackConditions
))

const visibleFilters = computed(() => configuredConditions.value
  .filter(item => item && item.enabled !== false)
  .map((item, index) => {
    const field = fieldMap.value.get(item.field_key) || {}
    return {
      ...item,
      id: item.id || `${item.field_key}-${index}`,
      label: item.label_override || field.label || item.field_key,
      filter_type: item.filter_type || 'text',
      placeholder: item.placeholder || '',
      options: normalizeRows(field.options),
      order: Number(item.order || index + 1),
    }
  })
  .sort((a, b) => (a.order || 0) - (b.order || 0)))

const isEmptyValue = value => (
  value === null ||
  value === undefined ||
  value === '' ||
  (Array.isArray(value) && value.length === 0)
)

const getValue = fieldKey => props.modelValue?.[fieldKey]

const getRangeValue = (fieldKey, index) => {
  const value = props.modelValue?.[fieldKey]
  return Array.isArray(value) ? value[index] : undefined
}

const getFilterOptions = filter => {
  const overrideOptions = props.filterOptionMap?.[filter.field_key]
  const options = Array.isArray(overrideOptions) ? overrideOptions : filter.options
  return normalizeRows(options)
    .map(option => {
      if (option && typeof option === 'object') {
        return {
          label: String(option.label ?? option.name ?? option.value ?? ''),
          value: option.value ?? option.id ?? option.label,
        }
      }
      return { label: String(option), value: option }
    })
    .filter(option => option.label !== '' && option.value !== undefined)
}

const shouldRenderSelect = filter => (
  ['single_select', 'multi_select'].includes(filter.filter_type) && getFilterOptions(filter).length > 0
)

const updateModel = nextValue => {
  emit('update:modelValue', nextValue)
}

const updateFilterValue = (fieldKey, value) => {
  const nextValue = { ...(props.modelValue || {}) }
  if (isEmptyValue(value)) {
    delete nextValue[fieldKey]
  } else {
    nextValue[fieldKey] = value
  }
  updateModel(nextValue)
  return nextValue
}

const updateRangeValue = (fieldKey, index, value) => {
  const currentValue = Array.isArray(props.modelValue?.[fieldKey]) ? [...props.modelValue[fieldKey]] : []
  currentValue[index] = value
  return updateFilterValue(fieldKey, currentValue.filter(item => !isEmptyValue(item)).length ? currentValue : [])
}

const commitFilterValue = (fieldKey, value) => {
  emit('search', updateFilterValue(fieldKey, value))
}

const commitRangeValue = (fieldKey, index, value) => {
  emit('search', updateRangeValue(fieldKey, index, value))
}

const pruneModelValue = () => {
  const allowedKeys = new Set(visibleFilters.value.map(filter => filter.field_key))
  const nextValue = {}
  Object.entries(props.modelValue || {}).forEach(([key, value]) => {
    if (allowedKeys.has(key) && !isEmptyValue(value)) {
      nextValue[key] = value
    }
  })

  const currentKeys = Object.keys(props.modelValue || {})
  const nextKeys = Object.keys(nextValue)
  const changed = currentKeys.length !== nextKeys.length || currentKeys.some(key => props.modelValue[key] !== nextValue[key])
  if (changed) {
    updateModel(nextValue)
  }
}

const emitSearch = () => {
  emit('search', props.modelValue || {})
}

const handleClear = fieldKey => {
  emit('search', updateFilterValue(fieldKey, undefined))
}

const handleReset = () => {
  updateModel({})
  emit('reset')
}

const loadConfig = async () => {
  loading.value = true
  try {
    const response = await getManualWorkspacePageListConfig({ storage_key: props.storageKey })
    configPayload.value = response.data || null
    configLoaded.value = true
    pruneModelValue()
    emit('loaded', configPayload.value)
  } catch (error) {
    configPayload.value = null
    configLoaded.value = false
    emit('loaded', null)
  } finally {
    loading.value = false
  }
}

const handleConfigUpdated = async event => {
  if (!isManualPageListConfigUpdateForStorage(event, props.storageKey)) {
    return
  }
  await loadConfig()
}

watch(visibleFilters, pruneModelValue, { immediate: true })

onMounted(() => {
  loadConfig()
  window.addEventListener(MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT, handleConfigUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener(MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT, handleConfigUpdated)
})
</script>

<style scoped lang="scss">
.manual-configured-filter-form {
  min-width: min(100%, 640px);
}

.manual-configured-filter-form__range {
  display: flex;
  align-items: center;
  gap: 4px;
}

.manual-configured-filter-form__range :deep(.el-input-number) {
  width: 86px;
}

:deep(.el-form-item) {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .manual-configured-filter-form,
  .manual-configured-filter-form :deep(.el-input),
  .manual-configured-filter-form :deep(.el-select),
  .manual-configured-filter-form :deep(.el-date-editor) {
    width: 100%;
  }
}
</style>
