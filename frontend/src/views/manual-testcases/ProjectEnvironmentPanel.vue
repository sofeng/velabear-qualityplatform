<template>
  <div class="project-environment-panel">
    <div class="tab-toolbar">
      <ManualConfiguredFilterForm
        v-model="filters"
        storage-key="manual-testcases.project-environments"
        class="environment-search-form"
        :fallback-conditions="fallbackFilterConditions"
        :fallback-fields-registry="fallbackFieldsRegistry"
        :filter-option-map="filterOptionMap"
        @search="handleSearch"
        @reset="handleReset"
        @loaded="handleFilterConfigLoaded"
      />

      <div class="toolbar-actions">
        <TableColumnSettings
          :table-ref="environmentTableRef"
          storage-key="manual-testcases.project-environments"
        />
        <el-tag effect="plain">项目环境 {{ pagination.total }}</el-tag>
        <el-button :loading="loading" @click="loadEnvironments">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增项目环境
        </el-button>
      </div>
    </div>

    <section class="section-panel environment-section">
      <el-table
        ref="environmentTableRef"
        v-loading="loading"
        :data="environments"
        row-key="id"
        stripe
        class="environment-table"
        :max-height="tableMaxHeight"
        style="width: 100%"
        empty-text="暂无项目环境数据"
      >
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="name" label="环境名称" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="environment-name-cell">
              <span>{{ row.name || '-' }}</span>
              <el-tag v-if="row.is_default" size="small" type="warning" effect="plain">默认</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="base_url" label="URL地址" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link
              v-if="row.base_url"
              type="primary"
              :href="row.base_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ row.base_url }}
            </el-link>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="account" label="账号" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.account || '-' }}</template>
        </el-table-column>
        <el-table-column label="密码" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.has_password ? 'success' : 'info'" size="small">
              {{ row.has_password ? '已配置' : '未配置' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at || row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" :width="actionColumnWidth" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button v-if="!row.is_default" link type="warning" @click="handleSetDefault(row)">设为默认</el-button>
              <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        class="tab-pagination"
        @current-change="loadEnvironments"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      destroy-on-close
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="项目名称" prop="project">
              <el-select
                v-model="form.project"
                filterable
                placeholder="请选择项目"
                style="width: 100%"
                :loading="projectLoading"
              >
                <el-option
                  v-for="project in projectOptions"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="环境名称" prop="name">
              <el-input v-model="form.name" maxlength="100" placeholder="请输入环境名称" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="URL地址" prop="base_url">
          <el-input v-model="form.base_url" maxlength="500" placeholder="请输入URL地址" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="账号" prop="account">
              <el-input v-model="form.account" maxlength="200" placeholder="请输入账号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                maxlength="200"
                :placeholder="dialogMode === 'edit' && form.has_password ? '留空则保留原密码' : '请输入密码'"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="默认环境">
          <el-switch v-model="form.is_default" active-text="是" inactive-text="否" />
        </el-form-item>

        <el-form-item label="说明" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            placeholder="请输入环境说明"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitForm">
            {{ dialogMode === 'create' ? '创建环境' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import ManualConfiguredFilterForm from '@/views/manual-testcases/ManualConfiguredFilterForm.vue'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import api from '@/utils/api'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
  currentProjectId: {
    type: [Number, String],
    default: null,
  },
  workspaceProjects: {
    type: Array,
    default: () => [],
  },
})

const PROJECT_ENVIRONMENT_ENDPOINT = '/projects/environments/'
const PROJECT_OPTION_ENDPOINTS = Object.freeze([
  { url: '/projects/all/' },
  { url: '/projects/list/', config: { params: { page_size: 1000 } } },
  { url: '/projects/', config: { params: { page_size: 1000, ordering: '-is_default,name,id' } } },
])

const FIELD_PROJECT_NAME = 'prop:project_name'
const FIELD_ENVIRONMENT_NAME = 'prop:name'
const FIELD_BASE_URL = 'prop:base_url'
const FIELD_ACCOUNT = 'prop:account'
const FIELD_HAS_PASSWORD = 'label:密码'
const FIELD_DESCRIPTION = 'prop:description'
const FIELD_UPDATED_AT = 'label:更新时间'

const fallbackFieldsRegistry = Object.freeze([
  { field_key: FIELD_PROJECT_NAME, label: '项目名称', options: [] },
  { field_key: FIELD_ENVIRONMENT_NAME, label: '环境名称', options: [] },
  { field_key: FIELD_BASE_URL, label: 'URL地址', options: [] },
  { field_key: FIELD_ACCOUNT, label: '账号', options: [] },
  { field_key: FIELD_HAS_PASSWORD, label: '密码', options: [] },
  { field_key: FIELD_DESCRIPTION, label: '说明', options: [] },
  { field_key: FIELD_UPDATED_AT, label: '更新时间', options: [] },
])

const fallbackFilterConditions = Object.freeze([
  {
    id: 'factory-filter-project-environment-project',
    field_key: FIELD_PROJECT_NAME,
    filter_type: 'single_select',
    operator: 'eq',
    placeholder: '全部项目',
    enabled: true,
    order: 1,
  },
  {
    id: 'factory-filter-project-environment-name',
    field_key: FIELD_ENVIRONMENT_NAME,
    filter_type: 'text',
    operator: 'contains',
    placeholder: '搜索环境名称',
    enabled: true,
    order: 2,
  },
])

const environmentTableRef = ref(null)
const formRef = ref(null)

const loading = ref(false)
const saving = ref(false)
const projectLoading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref('create')
const initialized = ref(false)

const environments = ref([])
const projectOptions = ref([])

const filters = ref({})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const createDefaultForm = () => ({
  id: null,
  project: null,
  name: '',
  base_url: '',
  account: '',
  password: '',
  has_password: false,
  description: '',
  is_default: false,
})

const form = reactive(createDefaultForm())

const rules = {
  project: [{ required: true, message: '请选择项目', trigger: 'change' }],
  name: [{ required: true, message: '请输入环境名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入URL地址', trigger: 'blur' }],
}

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增项目环境' : '编辑项目环境'))
const actionColumnWidth = buildActionColumnWidth([['设为默认', '编辑', '删除']], { variant: 'link' })
const tableMaxHeight = 'calc(100vh - 360px)'

const filterOptionMap = computed(() => ({
  [FIELD_PROJECT_NAME]: projectOptions.value.map(project => ({
    label: project.name,
    value: project.id,
  })),
}))

const normalizedCurrentProjectId = computed(() => {
  const parsedValue = Number(props.currentProjectId)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : null
})

const normalizePagedData = data => {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
    }
  }

  return {
    results: data?.results || [],
    count: Number(data?.count ?? 0),
  }
}

const extractErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data

  if (typeof responseData?.detail === 'string' && responseData.detail) {
    return responseData.detail
  }

  if (typeof responseData?.error === 'string' && responseData.error) {
    return responseData.error
  }

  if (typeof responseData?.message === 'string' && responseData.message) {
    return responseData.message
  }

  if (responseData && typeof responseData === 'object') {
    const firstValue = Object.values(responseData)[0]
    if (Array.isArray(firstValue) && firstValue.length) {
      return String(firstValue[0])
    }
    if (typeof firstValue === 'string' && firstValue) {
      return firstValue
    }
  }

  return fallback
}

const formatDate = value => {
  if (!value) {
    return '-'
  }

  const parsedValue = new Date(value)
  if (Number.isNaN(parsedValue.getTime())) {
    return value
  }

  return parsedValue.toLocaleString('zh-CN')
}

const normalizeProjectOptions = items => (
  (Array.isArray(items) ? items : [])
    .map(item => ({
      id: Number(item?.id),
      name: item?.name || '',
      is_default: Boolean(item?.is_default),
    }))
    .filter(item => Number.isInteger(item.id) && item.id > 0)
)

const normalizeProjectOptionsResponse = data => normalizeProjectOptions(data?.results || data || [])

const requestProjectOptions = async () => {
  let lastError = null
  let hasSuccessfulResponse = false

  for (const endpoint of PROJECT_OPTION_ENDPOINTS) {
    try {
      const response = await api.get(endpoint.url, endpoint.config)
      const options = normalizeProjectOptionsResponse(response.data)
      hasSuccessfulResponse = true
      if (options.length) {
        return options
      }
    } catch (error) {
      lastError = error
    }
  }

  if (hasSuccessfulResponse) {
    return []
  }

  throw lastError || new Error('Unable to load project options')
}

const resolvePreferredProjectId = () => (
  normalizedCurrentProjectId.value ||
  projectOptions.value.find(item => item.is_default)?.id ||
  projectOptions.value[0]?.id ||
  null
)

const loadProjectOptions = async () => {
  if (props.workspaceProjects.length) {
    projectOptions.value = normalizeProjectOptions(props.workspaceProjects)
    return
  }

  projectLoading.value = true
  try {
    projectOptions.value = await requestProjectOptions()
  } catch (error) {
    projectOptions.value = []
    ElMessage.error(extractErrorMessage(error, '获取项目列表失败'))
  } finally {
    projectLoading.value = false
  }
}

const buildListParams = () => {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: 'project__name,-is_default,name,id',
  }

  const activeFilters = filters.value || {}
  const projectId = activeFilters[FIELD_PROJECT_NAME]
  if (projectId !== undefined && projectId !== null && projectId !== '') {
    const numericProjectId = Number(projectId)
    if (Number.isInteger(numericProjectId) && numericProjectId > 0) {
      params.project = numericProjectId
    } else {
      params.project_name = String(projectId).trim()
    }
  }

  const fieldParamMap = {
    [FIELD_ENVIRONMENT_NAME]: 'name',
    [FIELD_BASE_URL]: 'base_url',
    [FIELD_ACCOUNT]: 'account',
    [FIELD_DESCRIPTION]: 'description',
  }

  Object.entries(fieldParamMap).forEach(([fieldKey, paramKey]) => {
    const value = String(activeFilters[fieldKey] || '').trim()
    if (value) {
      params[paramKey] = value
    }
  })

  if (activeFilters[FIELD_HAS_PASSWORD] === true || activeFilters[FIELD_HAS_PASSWORD] === false) {
    params.has_password = activeFilters[FIELD_HAS_PASSWORD] ? 'true' : 'false'
  }

  const updatedAt = activeFilters[FIELD_UPDATED_AT]
  if (Array.isArray(updatedAt)) {
    if (updatedAt[0]) {
      params.updated_at_start = updatedAt[0]
    }
    if (updatedAt[1]) {
      params.updated_at_end = updatedAt[1]
    }
  } else if (updatedAt) {
    params.updated_at = updatedAt
  }

  return params
}

const loadEnvironments = async () => {
  loading.value = true
  try {
    const response = await api.get(PROJECT_ENVIRONMENT_ENDPOINT, {
      params: buildListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    environments.value = results
    pagination.total = count
  } catch (error) {
    environments.value = []
    pagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取项目环境失败'))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, createDefaultForm())
}

const handleDialogClosed = () => {
  resetForm()
  formRef.value?.clearValidate()
}

const openCreateDialog = async () => {
  dialogMode.value = 'create'
  resetForm()
  if (!projectOptions.value.length) {
    await loadProjectOptions()
  }
  form.project = filters.value?.[FIELD_PROJECT_NAME] || resolvePreferredProjectId()
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

const openEditDialog = row => {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id,
    project: row.project,
    name: row.name || '',
    base_url: row.base_url || '',
    account: row.account || '',
    password: '',
    has_password: Boolean(row.has_password),
    description: row.description || '',
    is_default: Boolean(row.is_default),
  })
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

const buildPayload = () => {
  const payload = {
    project: form.project,
    name: String(form.name || '').trim(),
    base_url: String(form.base_url || '').trim(),
    account: String(form.account || '').trim(),
    description: String(form.description || '').trim(),
    is_default: Boolean(form.is_default),
  }

  const password = String(form.password || '')
  if (password) {
    payload.password = password
  }

  return payload
}

const submitForm = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()
    if (dialogMode.value === 'create') {
      await api.post(PROJECT_ENVIRONMENT_ENDPOINT, payload)
      ElMessage.success('项目环境已创建')
    } else {
      await api.put(`${PROJECT_ENVIRONMENT_ENDPOINT}${form.id}/`, payload)
      ElMessage.success('项目环境已更新')
    }

    dialogVisible.value = false
    await loadEnvironments()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存项目环境失败'))
  } finally {
    saving.value = false
  }
}

const handleSetDefault = async row => {
  try {
    await api.patch(`${PROJECT_ENVIRONMENT_ENDPOINT}${row.id}/`, {
      is_default: true,
    })
    ElMessage.success('默认环境设置成功')
    await loadEnvironments()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '设置默认环境失败'))
  }
}

const handleDelete = async row => {
  try {
    await ElMessageBox.confirm(
      `确认删除项目“${row.project_name || '-'}”下的环境“${row.name || '-'}”吗？`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${PROJECT_ENVIRONMENT_ENDPOINT}${row.id}/`)
    if (environments.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    ElMessage.success('项目环境已删除')
    await loadEnvironments()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除项目环境失败'))
    }
  }
}

const handleSearch = async nextFilters => {
  if (nextFilters && typeof nextFilters === 'object') {
    filters.value = { ...nextFilters }
  }
  pagination.page = 1
  await loadEnvironments()
}

const handleReset = async () => {
  filters.value = {}
  pagination.page = 1
  pagination.pageSize = 20
  await loadEnvironments()
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  await loadEnvironments()
}

const handleFilterConfigLoaded = async () => {
  if (!initialized.value || !props.active) {
    return
  }
  pagination.page = 1
  await loadEnvironments()
}

const initialize = async () => {
  await loadProjectOptions()
  if (!initialized.value && !filters.value?.[FIELD_PROJECT_NAME] && normalizedCurrentProjectId.value) {
    filters.value = {
      ...filters.value,
      [FIELD_PROJECT_NAME]: normalizedCurrentProjectId.value,
    }
  }
  initialized.value = true
  await loadEnvironments()
}

watch(
  () => props.active,
  async active => {
    if (active) {
      await initialize()
    }
  }
)

watch(
  () => props.workspaceProjects,
  projects => {
    if (Array.isArray(projects) && projects.length) {
      projectOptions.value = normalizeProjectOptions(projects)
    }
  },
  { deep: true }
)

watch(
  () => props.currentProjectId,
  projectId => {
    const normalizedProjectId = Number(projectId)
    if (!initialized.value && Number.isInteger(normalizedProjectId) && normalizedProjectId > 0 && !filters.value?.[FIELD_PROJECT_NAME]) {
      filters.value = {
        ...filters.value,
        [FIELD_PROJECT_NAME]: normalizedProjectId,
      }
    }
  }
)

onMounted(async () => {
  if (props.active) {
    await initialize()
  }
})
</script>

<style scoped lang="scss">
.project-environment-panel {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-actions,
.row-actions,
.dialog-footer,
.environment-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions {
  flex-wrap: wrap;
  margin-left: auto;
}

.section-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
}

.environment-section {
  flex: 1;
}

.environment-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.environment-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.environment-name-cell {
  flex-wrap: wrap;
}

.row-actions {
  justify-content: flex-end;
  flex-wrap: nowrap;
  width: 100%;
  white-space: nowrap;
}

.row-actions :deep(.el-button) {
  margin-left: 0;
}

.tab-pagination {
  margin-top: auto;
  justify-content: flex-end;
}

.dialog-footer {
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .tab-toolbar,
  .toolbar-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .environment-search-form,
  .environment-search-form :deep(.el-input),
  .environment-search-form :deep(.el-select) {
    width: 100%;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
