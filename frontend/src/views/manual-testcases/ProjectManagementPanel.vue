<template>
  <div class="project-management-panel">
    <div class="tab-toolbar">
      <el-form :inline="true" :model="filters" class="search-form project-search-form" @submit.prevent>
        <el-form-item label="项目">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="请输入项目名称或描述"
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            clearable
            placeholder="全部状态"
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-actions">
        <TableColumnSettings
          :table-ref="projectTableRef"
          storage-key="manual-testcases.projects"
        />
        <el-tag effect="plain">项目 {{ pagination.total }}</el-tag>
        <el-button :loading="loading" @click="loadProjects">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :disabled="!canCreateProject" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增项目
        </el-button>
      </div>
    </div>

    <div class="workspace-grid">
      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">项目列表</h3>
            <p class="section-subtitle">维护项目基础信息，并选择右侧要管理成员的项目</p>
          </div>
        </div>

        <el-table
          ref="projectTableRef"
          v-loading="loading"
          :data="projects"
          row-key="id"
          stripe
          highlight-current-row
          class="project-table"
          :max-height="projectTableMaxHeight"
          style="width: 100%"
          empty-text="暂无项目数据"
          @row-click="handleProjectRowClick"
        >
          <el-table-column prop="name" label="项目名称" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="project-name-cell">
                <span>{{ row.name || '-' }}</span>
                <el-tag v-if="row.is_default" size="small" type="warning" effect="plain">默认</el-tag>
                <el-tag v-if="isCurrentProject(row)" size="small" type="success">当前工作区</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="负责人" width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ getOwnerName(row.owner) }}</template>
          </el-table-column>
          <el-table-column label="创建时间" width="180">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" :width="projectActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button
                  v-if="canSetDefaultProject && !row.is_default"
                  link
                  type="warning"
                  @click.stop="handleSetDefaultProject(row)"
                >
                  设为默认
                </el-button>
                <el-button
                  link
                  type="primary"
                  :disabled="isCurrentProject(row)"
                  @click.stop="switchProject(row)"
                >
                  {{ isCurrentProject(row) ? '当前项目' : '切换工作区' }}
                </el-button>
                <el-button v-if="canEditProject" link type="primary" @click.stop="openEditDialog(row)">编辑</el-button>
                <el-button v-if="canDeleteProject" link type="danger" @click.stop="handleDelete(row)">删除</el-button>
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
          @current-change="loadProjects"
          @size-change="handlePageSizeChange"
        />
      </section>

      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">{{ selectedProject ? `${selectedProject.name} 成员` : '项目成员' }}</h3>
            <p class="section-subtitle">
              {{
                selectedProject
                  ? `当前项目共 ${projectMembers.length} 名成员，负责人默认包含在成员列表中`
                  : '请选择左侧项目后查看和维护成员'
              }}
            </p>
          </div>
          <div class="section-actions">
            <TableColumnSettings
              :table-ref="projectMemberTableRef"
              storage-key="manual-testcases.project-members"
            />
            <el-button :disabled="!selectedProject" :loading="memberLoading" @click="refreshSelectedProjectMembers">
              <el-icon><Refresh /></el-icon>
              刷新成员
            </el-button>
            <el-button
              type="primary"
              :disabled="!selectedProject || !canManageSelectedProjectMembers"
              @click="openCreateMemberDialog"
            >
              <el-icon><Plus /></el-icon>
              新增成员
            </el-button>
          </div>
        </div>

        <el-alert
          v-if="selectedProject && !canManageSelectedProjectMembers"
          title="当前账号可查看项目成员，但仅项目负责人或管理员可维护成员。"
          type="info"
          :closable="false"
          class="permission-alert"
        />

        <el-empty
          v-if="!selectedProject && !loading"
          description="请选择项目后查看成员"
          class="member-empty-state"
        />

        <el-table
          v-else
          ref="projectMemberTableRef"
          v-loading="memberLoading"
          :data="projectMembers"
          row-key="user_id"
          stripe
          class="member-table"
          :max-height="projectMemberTableMaxHeight"
          style="width: 100%"
          empty-text="当前项目暂无成员"
        >
          <el-table-column prop="username" label="用户名" min-width="160" show-overflow-tooltip />
          <el-table-column label="姓名" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ getMemberName(row) }}</template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.email || '-' }}</template>
          </el-table-column>
          <el-table-column prop="department" label="部门" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.department || '-' }}</template>
          </el-table-column>
          <el-table-column prop="position" label="职位" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.position || '-' }}</template>
          </el-table-column>
          <el-table-column label="角色" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="getProjectRoleTagType(row.role)">
                {{ getProjectRoleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="加入时间" width="180">
            <template #default="{ row }">{{ formatDate(row.joined_at) }}</template>
          </el-table-column>
          <el-table-column v-if="canManageSelectedProjectMembers" label="操作" :width="projectMemberActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <template v-if="row.is_owner">
                  <span class="owner-text">负责人</span>
                </template>
                <template v-else>
                  <el-button link type="primary" @click="openEditMemberDialog(row)">编辑</el-button>
                  <el-button link type="danger" @click="handleRemoveMember(row)">移除</el-button>
                </template>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="640px"
      destroy-on-close
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="项目名称" prop="name">
              <el-input v-model="form.name" maxlength="200" placeholder="请输入项目名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
                <el-option
                  v-for="option in statusOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="请输入项目描述"
          />
        </el-form-item>
        <el-form-item v-if="canSetDefaultProject" label="默认项目">
          <el-switch
            v-model="form.is_default"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitForm">
            {{ dialogMode === 'create' ? '创建项目' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="memberDialogVisible"
      :title="memberDialogTitle"
      width="560px"
      destroy-on-close
      @closed="handleMemberDialogClosed"
    >
      <el-form ref="memberFormRef" :model="memberForm" :rules="memberRules" label-position="top">
        <el-form-item v-if="memberDialogMode === 'create'" label="成员" prop="user_ids">
          <el-select
            v-model="memberForm.user_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择成员"
            style="width: 100%"
            :loading="userOptionsLoading"
          >
            <el-option
              v-for="user in availableUserOptions"
              :key="user.id"
              :label="getUserDisplayName(user, user.username)"
              :value="user.id"
            >
              <div class="member-option">
                <span>{{ getUserDisplayName(user, user.username) }}</span>
                <span class="member-option__meta">{{ user.username }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-else label="成员" prop="user_id">
          <el-select
            v-model="memberForm.user_id"
            filterable
            placeholder="请选择成员"
            style="width: 100%"
            :loading="userOptionsLoading"
          >
            <el-option
              v-for="user in availableUserOptions"
              :key="user.id"
              :label="getUserDisplayName(user, user.username)"
              :value="user.id"
            >
              <div class="member-option">
                <span>{{ getUserDisplayName(user, user.username) }}</span>
                <span class="member-option__meta">{{ user.username }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="memberDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="memberSaving" @click="submitMemberForm">
            {{ memberDialogMode === 'create' ? '添加成员' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useUserStore } from '@/stores/user'
import api from '@/utils/api'
import { PERMISSION_CODES } from '@/utils/permissions'
import { getUserDisplayName, getUserFullName } from '@/utils/userDisplay'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
  currentProjectId: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['projects-updated', 'switch-project'])

const PROJECT_ENDPOINT = '/projects/'
const USER_ENDPOINT = '/auth/users/'

const userStore = useUserStore()

const projectTableRef = ref(null)
const projectMemberTableRef = ref(null)
const formRef = ref(null)
const memberFormRef = ref(null)

const loading = ref(false)
const saving = ref(false)
const memberLoading = ref(false)
const memberSaving = ref(false)
const userOptionsLoading = ref(false)

const dialogVisible = ref(false)
const memberDialogVisible = ref(false)
const dialogMode = ref('create')
const memberDialogMode = ref('create')
const editingMemberId = ref(null)

const filters = reactive({
  keyword: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const projects = ref([])
const selectedProjectId = ref(null)
const selectedProject = ref(null)
const projectMembers = ref([])
const userOptions = ref([])

const createDefaultForm = () => ({
  id: null,
  name: '',
  description: '',
  status: 'active',
  is_default: false,
})

const createDefaultMemberForm = () => ({
  user_id: null,
  user_ids: [],
})

const form = reactive(createDefaultForm())
const memberForm = reactive(createDefaultMemberForm())

const statusOptions = [
  { label: '进行中', value: 'active' },
  { label: '已暂停', value: 'paused' },
  { label: '已完成', value: 'completed' },
  { label: '已归档', value: 'archived' },
]

const projectRoleLabelMap = Object.freeze({
  owner: '负责人',
  admin: '管理员',
  developer: '开发',
  tester: '测试',
  viewer: '观察者',
})

const projectRoleTagTypeMap = Object.freeze({
  owner: 'success',
  admin: 'warning',
  developer: '',
  tester: 'info',
  viewer: 'info',
})

const normalizedCurrentProjectId = computed(() => {
  const parsedValue = Number(props.currentProjectId)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : null
})

const currentUserId = computed(() => {
  const parsedValue = Number(userStore.user?.id)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : null
})

const canCreateProject = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.projectCreate))
const canEditProject = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.projectEdit))
const canDeleteProject = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.projectDelete))
const canSetDefaultProject = computed(() => canEditProject.value)
const projectActionColumnWidth = computed(() => buildActionColumnWidth([[
  ...(canSetDefaultProject.value ? ['设为默认'] : []),
  '切换工作区',
  ...(canEditProject.value ? ['编辑'] : []),
  ...(canDeleteProject.value ? ['删除'] : []),
]], {
  variant: 'link',
}))
const projectMemberActionColumnWidth = buildActionColumnWidth([['编辑', '移除']], {
  variant: 'link',
})
const canManageSelectedProjectMembers = computed(() => {
  if (!selectedProject.value) {
    return false
  }

  return Boolean(
    userStore.user?.is_staff ||
      userStore.user?.is_superuser ||
      Number(selectedProject.value.owner?.id) === currentUserId.value
  )
})
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增项目' : '编辑项目'))
const memberDialogTitle = computed(() => (memberDialogMode.value === 'create' ? '新增项目成员' : '编辑项目成员'))
const projectTableMaxHeight = 'calc(100vh - 380px)'
const projectMemberTableMaxHeight = 'calc(100vh - 380px)'

const rules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择项目状态', trigger: 'change' }],
}

const memberRules = {
  user_id: [{ required: true, message: '请选择成员', trigger: 'change' }],
  user_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一名成员', trigger: 'change' }],
}

const availableUserOptions = computed(() => {
  const occupiedUserIds = new Set(projectMembers.value.map(item => item.user_id))
  if (memberDialogMode.value === 'edit' && editingMemberId.value) {
    occupiedUserIds.delete(editingMemberId.value)
  }

  return userOptions.value.filter(user => !occupiedUserIds.has(user.id))
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

const normalizeSelectedUserIds = value => {
  const normalizedIds = []
  const seenIds = new Set()

  ;(Array.isArray(value) ? value : []).forEach(item => {
    const userId = Number(item)
    if (!Number.isInteger(userId) || userId <= 0 || seenIds.has(userId)) {
      return
    }

    seenIds.add(userId)
    normalizedIds.push(userId)
  })

  return normalizedIds
}

const isCurrentProject = project => Number(project?.id) === normalizedCurrentProjectId.value
const getMemberName = member => getUserFullName(member) || '-'
const getOwnerName = owner => getUserDisplayName(owner, owner?.username || '-') || '-'
const getProjectRoleLabel = role => projectRoleLabelMap[role] || role || '-'
const getProjectRoleTagType = role => projectRoleTagTypeMap[role] || 'info'

const getStatusType = status => {
  const statusMap = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info',
  }

  return statusMap[status] || 'info'
}

const getStatusLabel = status => {
  const matchedOption = statusOptions.find(option => option.value === status)
  return matchedOption?.label || status || '-'
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

const buildListParams = () => {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: '-created_at',
  }

  const keyword = String(filters.keyword || '').trim()
  if (keyword) {
    params.search = keyword
  }

  if (filters.status) {
    params.status = filters.status
  }

  return params
}

const setCurrentProjectRow = async row => {
  await nextTick()
  projectTableRef.value?.setCurrentRow(row || null)
}

const syncSelectedProject = async preferredProjectId => {
  const nextSelectedProject =
    projects.value.find(item => item.id === preferredProjectId) ||
    projects.value.find(item => item.id === normalizedCurrentProjectId.value) ||
    projects.value[0] ||
    null

  selectedProject.value = nextSelectedProject
  selectedProjectId.value = nextSelectedProject?.id ?? null
  await setCurrentProjectRow(nextSelectedProject)
  return nextSelectedProject
}

const loadUserOptions = async () => {
  userOptionsLoading.value = true
  try {
    const response = await api.get(USER_ENDPOINT, {
      params: {
        page_size: 1000,
        ordering: 'username',
      },
    })
    userOptions.value = normalizePagedData(response.data).results
  } catch (error) {
    userOptions.value = []
    ElMessage.error(extractErrorMessage(error, '获取成员候选列表失败'))
  } finally {
    userOptionsLoading.value = false
  }
}

const loadProjectMembers = async (projectId = selectedProjectId.value) => {
  if (!projectId) {
    projectMembers.value = []
    return
  }

  memberLoading.value = true
  try {
    const response = await api.get(`${PROJECT_ENDPOINT}${projectId}/members/`)
    projectMembers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    projectMembers.value = []
    ElMessage.error(extractErrorMessage(error, '获取项目成员失败'))
  } finally {
    memberLoading.value = false
  }
}

const loadProjects = async ({ preserveSelection = true } = {}) => {
  loading.value = true
  try {
    const response = await api.get(PROJECT_ENDPOINT, {
      params: buildListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    projects.value = results
    pagination.total = count

    const preferredProjectId = preserveSelection ? selectedProjectId.value : normalizedCurrentProjectId.value
    const nextSelectedProject = await syncSelectedProject(preferredProjectId)

    if (nextSelectedProject) {
      await loadProjectMembers(nextSelectedProject.id)
    } else {
      projectMembers.value = []
    }
  } catch (error) {
    projects.value = []
    projectMembers.value = []
    selectedProject.value = null
    selectedProjectId.value = null
    pagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取项目列表失败'))
  } finally {
    loading.value = false
  }
}

const handleProjectRowClick = async row => {
  if (!row || row.id === selectedProjectId.value) {
    return
  }

  selectedProject.value = row
  selectedProjectId.value = row.id
  await setCurrentProjectRow(row)
  await loadProjectMembers(row.id)
}

const refreshSelectedProjectMembers = async () => {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  await loadProjectMembers(selectedProjectId.value)
}

const resetForm = () => {
  Object.assign(form, createDefaultForm())
}

const resetMemberForm = () => {
  Object.assign(memberForm, createDefaultMemberForm())
  editingMemberId.value = null
}

const handleDialogClosed = () => {
  resetForm()
  formRef.value?.clearValidate()
}

const handleMemberDialogClosed = () => {
  resetMemberForm()
  memberFormRef.value?.clearValidate()
}

const openCreateDialog = () => {
  if (!canCreateProject.value) {
    ElMessage.warning('当前账号没有新增项目权限')
    return
  }

  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

const openEditDialog = project => {
  if (!canEditProject.value) {
    ElMessage.warning('当前账号没有编辑项目权限')
    return
  }

  dialogMode.value = 'edit'
  Object.assign(form, {
    id: project.id,
    name: project.name || '',
    description: project.description || '',
    status: project.status || 'active',
    is_default: Boolean(project.is_default),
  })
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

const submitForm = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = {
      name: String(form.name || '').trim(),
      description: String(form.description || '').trim(),
      status: form.status,
      is_default: Boolean(form.is_default),
    }

    let response
    if (dialogMode.value === 'create') {
      response = await api.post(PROJECT_ENDPOINT, payload)
      ElMessage.success('项目已创建')
    } else {
      response = await api.put(`${PROJECT_ENDPOINT}${form.id}/`, payload)
      ElMessage.success('项目已更新')
    }

    selectedProjectId.value = response.data?.id || selectedProjectId.value || form.id
    dialogVisible.value = false
    await loadProjects({ preserveSelection: true })
    if (response.data?.is_default && response.data?.id) {
      emit('switch-project', response.data.id)
    }
    emit('projects-updated')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存项目失败'))
  } finally {
    saving.value = false
  }
}

const handleDelete = async project => {
  if (!canDeleteProject.value) {
    ElMessage.warning('当前账号没有删除项目权限')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除项目“${project.name}”吗？删除后关联的版本与目录数据也可能受到影响。`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${PROJECT_ENDPOINT}${project.id}/`)

    if (selectedProjectId.value === project.id) {
      selectedProjectId.value = null
      selectedProject.value = null
    }

    if (projects.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }

    ElMessage.success('项目已删除')
    await loadProjects({ preserveSelection: true })
    emit('projects-updated')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除项目失败'))
    }
  }
}

const switchProject = project => {
  emit('switch-project', project.id)
}

const handleSetDefaultProject = async project => {
  if (!canSetDefaultProject.value) {
    ElMessage.warning('当前账号没有设置默认项目权限')
    return
  }

  try {
    await api.patch(`${PROJECT_ENDPOINT}${project.id}/`, {
      is_default: true,
    })
    ElMessage.success('默认项目设置成功')
    selectedProjectId.value = project.id
    await loadProjects({ preserveSelection: true })
    emit('switch-project', project.id)
    emit('projects-updated')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '设置默认项目失败'))
  }
}

const openCreateMemberDialog = async () => {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!canManageSelectedProjectMembers.value) {
    ElMessage.warning('当前账号没有项目成员管理权限')
    return
  }

  memberDialogMode.value = 'create'
  resetMemberForm()
  await loadUserOptions()

  if (!availableUserOptions.value.length) {
    ElMessage.warning('当前没有可添加的成员')
    return
  }

  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const openEditMemberDialog = async row => {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!canManageSelectedProjectMembers.value) {
    ElMessage.warning('当前账号没有项目成员管理权限')
    return
  }
  if (row?.is_owner) {
    ElMessage.warning('项目负责人无需编辑')
    return
  }

  memberDialogMode.value = 'edit'
  editingMemberId.value = row.user_id
  memberForm.user_id = row.user_id
  await loadUserOptions()
  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const submitMemberForm = async () => {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  try {
    await memberFormRef.value?.validate()
  } catch {
    return
  }

  memberSaving.value = true
  try {
    if (memberDialogMode.value === 'create') {
      const selectedUserIds = normalizeSelectedUserIds(memberForm.user_ids)
      const results = await Promise.allSettled(
        selectedUserIds.map(userId =>
          api.post(`${PROJECT_ENDPOINT}${selectedProjectId.value}/members/add/`, {
            user_id: userId,
          })
        )
      )
      const successCount = results.filter(item => item.status === 'fulfilled').length
      const failedResults = results.filter(item => item.status === 'rejected')

      if (!successCount) {
        throw failedResults[0]?.reason || new Error('添加项目成员失败')
      }

      memberDialogVisible.value = false
      await loadProjectMembers(selectedProjectId.value)

      if (failedResults.length) {
        ElMessage.warning(
          `已添加 ${successCount} 名成员，${failedResults.length} 名添加失败：${extractErrorMessage(
            failedResults[0]?.reason,
            '请稍后重试'
          )}`
        )
      } else {
        ElMessage.success(`已添加 ${successCount} 名成员`)
      }

      return
    } else {
      const payload = {
        user_id: memberForm.user_id,
      }
      await api.patch(`${PROJECT_ENDPOINT}${selectedProjectId.value}/members/${editingMemberId.value}/`, payload)
      ElMessage.success('项目成员已更新')
    }

    memberDialogVisible.value = false
    await loadProjectMembers(selectedProjectId.value)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存项目成员失败'))
  } finally {
    memberSaving.value = false
  }
}

const handleRemoveMember = async row => {
  if (!selectedProjectId.value || row?.is_owner) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认将“${getUserDisplayName(row, row.username)}”移出项目“${selectedProject.value?.name || ''}”吗？`,
      '移除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${PROJECT_ENDPOINT}${selectedProjectId.value}/members/${row.user_id}/`)
    ElMessage.success('项目成员已移除')
    await loadProjectMembers(selectedProjectId.value)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '移除项目成员失败'))
    }
  }
}

const handleSearch = async () => {
  pagination.page = 1
  await loadProjects({ preserveSelection: false })
}

const handleReset = async () => {
  filters.keyword = ''
  filters.status = ''
  pagination.page = 1
  pagination.pageSize = 20
  await loadProjects({ preserveSelection: false })
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  await loadProjects({ preserveSelection: true })
}

watch(
  () => props.active,
  async active => {
    if (active) {
      await loadProjects({ preserveSelection: true })
      return
    }

    await setCurrentProjectRow(selectedProject.value)
  }
)

watch(
  () => props.currentProjectId,
  async () => {
    await setCurrentProjectRow(selectedProject.value)
  }
)

onMounted(async () => {
  if (props.active) {
    await loadProjects({ preserveSelection: true })
  }
})
</script>

<style scoped lang="scss">
.project-management-panel {
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

.project-search-form {
  min-width: min(100%, 560px);
}

:deep(.project-search-form .el-form-item) {
  margin-bottom: 0;
}

.toolbar-actions,
.section-actions,
.row-actions,
.dialog-footer,
.project-name-cell,
.member-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions {
  flex-wrap: wrap;
  margin-left: auto;
}

.permission-alert {
  margin-bottom: 4px;
}

.workspace-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(420px, 1.05fr) minmax(560px, 1.35fr);
  gap: 16px;
  flex: 1;
}

.section-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 38px rgba(15, 45, 68, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.section-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.project-table,
.member-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.project-table :deep(.el-table__inner-wrapper),
.member-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.project-name-cell {
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

.member-empty-state {
  margin: auto 0;
}

.member-option {
  justify-content: space-between;
}

.member-option__meta,
.owner-text {
  color: #909399;
  font-size: 12px;
}

@media (max-width: 1080px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .tab-toolbar,
  .toolbar-actions,
  .section-header,
  .section-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .project-search-form,
  .project-search-form :deep(.el-input),
  .project-search-form :deep(.el-select) {
    width: 100%;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
