<template>
  <div class="role-management-panel">
    <div class="tab-toolbar">
      <el-form :inline="true" :model="filters" class="search-form role-search-form" @submit.prevent>
        <el-form-item label="角色">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索角色名称"
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
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
          :table-ref="roleTableRef"
          storage-key="manual-testcases.roles"
        />
        <el-tag effect="plain">角色 {{ pagination.total }}</el-tag>
        <el-button :loading="roleLoading" @click="loadRoles">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :disabled="!canManageRoles" @click="openCreateRoleDialog">
          <el-icon><Plus /></el-icon>
          新增角色
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canManageRoles"
      title="当前账号仅可查看角色和角色成员信息，新增、编辑、删除角色及维护角色成员需要管理员权限。"
      type="info"
      :closable="false"
      class="permission-alert"
    />

    <div class="workspace-grid">
      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">角色列表</h3>
            <p class="section-subtitle">维护测试平台中的角色定义</p>
          </div>
        </div>

        <el-table
          ref="roleTableRef"
          v-loading="roleLoading"
          :data="roles"
          row-key="id"
          stripe
          highlight-current-row
          class="role-table"
          :max-height="roleTableMaxHeight"
          style="width: 100%"
          empty-text="暂无角色数据"
          @row-click="handleRoleRowClick"
        >
          <el-table-column
            prop="id"
            label="ID"
            width="80"
            sortable
            :sort-method="createNumberSorter(row => row.id)"
            :filters="roleColumnFilters.id"
            :filter-method="createTableFilter(row => row.id)"
          />
          <el-table-column
            prop="name"
            label="角色名称"
            min-width="200"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.name)"
            :filters="roleColumnFilters.name"
            :filter-method="createTableFilter(row => row.name)"
          />
          <el-table-column
            label="角色成员数"
            width="120"
            align="center"
            sortable
            :sort-method="createNumberSorter(row => row.member_count)"
            :filters="roleColumnFilters.member_count"
            :filter-method="createTableFilter(row => row.member_count)"
          >
            <template #default="{ row }">{{ row.member_count || 0 }}</template>
          </el-table-column>
          <el-table-column
            label="角色成员概览"
            min-width="240"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(formatRoleMembers)"
            :filters="roleColumnFilters.members"
            :filter-method="createTableFilter(formatRoleMembers)"
          >
            <template #default="{ row }">{{ formatRoleMembers(row) }}</template>
          </el-table-column>
          <el-table-column v-if="canManageRoles" label="操作" :width="roleActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" @click.stop="openEditRoleDialog(row)">编辑</el-button>
                <el-button link type="danger" @click.stop="handleDeleteRole(row)">删除</el-button>
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
          @current-change="loadRoles"
          @size-change="handlePageSizeChange"
        />
      </section>

      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">{{ selectedRole ? `${selectedRole.name} 角色成员` : '角色成员列表' }}</h3>
            <p class="section-subtitle">
              {{ selectedRole ? `当前角色共 ${roleMembers.length} 名角色成员` : '请选择左侧角色后查看角色成员' }}
            </p>
          </div>
          <div class="section-actions">
            <TableColumnSettings
              :table-ref="roleMemberTableRef"
              storage-key="manual-testcases.role-members"
            />
            <el-button :disabled="!selectedRole" :loading="memberLoading" @click="refreshSelectedRoleMembers">
              <el-icon><Refresh /></el-icon>
              刷新角色成员
            </el-button>
            <el-button
              type="primary"
              :disabled="!selectedRole || !canManageRoles"
              @click="openCreateMemberDialog"
            >
              <el-icon><Plus /></el-icon>
              新增角色成员
            </el-button>
          </div>
        </div>

        <el-empty
          v-if="!selectedRole && !roleLoading"
          description="请选择角色后查看角色成员"
          class="member-empty-state"
        />

        <el-table
          v-else
          ref="roleMemberTableRef"
          v-loading="memberLoading"
          :data="roleMembers"
          row-key="id"
          stripe
          class="member-table"
          :max-height="roleMemberTableMaxHeight"
          style="width: 100%"
          empty-text="当前角色暂无角色成员"
        >
          <el-table-column
            prop="username"
            label="用户名"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.username)"
            :filters="roleMemberColumnFilters.username"
            :filter-method="createTableFilter(row => row.username)"
          />
          <el-table-column
            label="姓名"
            min-width="140"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(getMemberName)"
            :filters="roleMemberColumnFilters.name"
            :filter-method="createTableFilter(getMemberName)"
          >
            <template #default="{ row }">{{ getMemberName(row) }}</template>
          </el-table-column>
          <el-table-column
            prop="email"
            label="邮箱"
            min-width="220"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.email)"
            :filters="roleMemberColumnFilters.email"
            :filter-method="createTableFilter(row => row.email)"
          >
            <template #default="{ row }">{{ row.email || '-' }}</template>
          </el-table-column>
          <el-table-column
            prop="department"
            label="部门"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.department)"
            :filters="roleMemberColumnFilters.department"
            :filter-method="createTableFilter(row => row.department)"
          >
            <template #default="{ row }">{{ row.department || '-' }}</template>
          </el-table-column>
          <el-table-column
            prop="position"
            label="职位"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.position)"
            :filters="roleMemberColumnFilters.position"
            :filter-method="createTableFilter(row => row.position)"
          >
            <template #default="{ row }">{{ row.position || '-' }}</template>
          </el-table-column>
          <el-table-column
            label="标签"
            min-width="220"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(getRoleMemberTags)"
            :filters="roleMemberColumnFilters.tags"
            :filter-method="createTableFilter(getRoleMemberTags)"
          >
            <template #default="{ row }">
              <div v-if="Array.isArray(row.tags) && row.tags.length" class="member-tag-list">
                <el-tag v-for="tag in row.tags" :key="`${row.id}-${tag}`" size="small" effect="plain">
                  {{ tag }}
                </el-tag>
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="100"
            align="center"
            sortable
            :sort-method="createTextSorter(getRoleMemberStatusLabel)"
            :filters="roleMemberColumnFilters.status"
            :filter-method="createTableFilter(getRoleMemberStatusLabel)"
          >
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="canManageRoles" label="操作" :width="roleActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" @click="openEditMemberDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="handleRemoveMember(row)">移除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-dialog
      v-model="roleDialogVisible"
      :title="roleDialogTitle"
      width="520px"
      destroy-on-close
      @closed="handleRoleDialogClosed"
    >
      <el-form ref="roleFormRef" :model="roleForm" :rules="roleRules" label-position="top">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleForm.name" maxlength="150" placeholder="请输入角色名称" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="roleDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="roleSaving" @click="submitRoleForm">
            {{ roleDialogMode === 'create' ? '创建角色' : '保存修改' }}
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
        <el-form-item v-if="memberDialogMode === 'create'" label="角色成员" prop="user_ids">
          <el-select
            v-model="memberForm.user_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择角色成员"
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
        <el-form-item v-else label="角色成员" prop="user_id">
          <el-select
            v-model="memberForm.user_id"
            filterable
            placeholder="请选择角色成员"
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
        <el-form-item label="成员标签" prop="tags">
          <el-select
            v-model="memberForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择或输入成员标签，回车添加"
            style="width: 100%"
          >
            <el-option
              v-for="tag in memberTagOptions"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
          <div class="form-hint">支持多个标签，输入后按回车可直接新增标签</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="memberDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="memberSaving" @click="submitMemberForm">
            {{ memberDialogMode === 'create' ? '添加角色成员' : '保存修改' }}
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
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import {
  buildTableFilters,
  compareTableNumber,
  createNumberSorter,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { getUserDisplayName, getUserFullName } from '@/utils/userDisplay'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
})

const ROLE_ENDPOINT = '/auth/roles/'
const USER_ENDPOINT = '/auth/users/'

const userStore = useUserStore()

const roleTableRef = ref(null)
const roleMemberTableRef = ref(null)
const roleFormRef = ref(null)
const memberFormRef = ref(null)

const roleLoading = ref(false)
const memberLoading = ref(false)
const roleSaving = ref(false)
const memberSaving = ref(false)
const userOptionsLoading = ref(false)

const roleDialogVisible = ref(false)
const memberDialogVisible = ref(false)
const roleDialogMode = ref('create')
const memberDialogMode = ref('create')
const editingMemberId = ref(null)

const filters = reactive({
  keyword: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const roles = ref([])
const selectedRoleId = ref(null)
const selectedRole = ref(null)
const roleMembers = ref([])
const userOptions = ref([])

const createDefaultRoleForm = () => ({
  id: null,
  name: '',
})

const createDefaultMemberForm = () => ({
  user_id: null,
  user_ids: [],
  tags: [],
})

const roleForm = reactive(createDefaultRoleForm())
const memberForm = reactive(createDefaultMemberForm())

const canManageRoles = computed(() => Boolean(userStore.user?.is_staff || userStore.user?.is_superuser))
const roleActionColumnWidth = buildActionColumnWidth([['编辑', '删除']], {
  variant: 'link',
})
const roleDialogTitle = computed(() => (roleDialogMode.value === 'create' ? '新增角色' : '编辑角色'))
const memberDialogTitle = computed(() => (memberDialogMode.value === 'create' ? '新增角色成员' : '编辑角色成员'))
const roleTableMaxHeight = 'calc(100vh - 380px)'
const roleMemberTableMaxHeight = 'calc(100vh - 380px)'

const roleRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
}

const memberRules = {
  user_id: [{ required: true, message: '请选择角色成员', trigger: 'change' }],
  user_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一名角色成员', trigger: 'change' }],
}

const availableUserOptions = computed(() => {
  const occupiedUserIds = new Set(roleMembers.value.map(item => item.id))
  if (memberDialogMode.value === 'edit' && editingMemberId.value) {
    occupiedUserIds.delete(editingMemberId.value)
  }

  return userOptions.value.filter(user => !occupiedUserIds.has(user.id))
})

const memberTagOptions = computed(() => {
  const tagSet = new Set()

  roleMembers.value.forEach(member => {
    const tags = Array.isArray(member?.tags) ? member.tags : []
    tags.forEach(tag => {
      const normalizedTag = String(tag || '').trim()
      if (normalizedTag) {
        tagSet.add(normalizedTag)
      }
    })
  })

  ;(Array.isArray(memberForm.tags) ? memberForm.tags : []).forEach(tag => {
    const normalizedTag = String(tag || '').trim()
    if (normalizedTag) {
      tagSet.add(normalizedTag)
    }
  })

  return Array.from(tagSet)
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

const normalizeMemberTags = tags => {
  const normalizedTags = []
  const seenTags = new Set()

  ;(Array.isArray(tags) ? tags : []).forEach(tag => {
    const normalizedTag = String(tag || '').trim()
    if (!normalizedTag || seenTags.has(normalizedTag)) {
      return
    }

    seenTags.add(normalizedTag)
    normalizedTags.push(normalizedTag)
  })

  return normalizedTags
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

const getMemberName = member => getUserFullName(member) || '-'
const getRoleMemberTags = member => (Array.isArray(member?.tags) ? member.tags.filter(Boolean) : [])
const getRoleMemberStatusLabel = member => (member?.is_active ? '启用' : '停用')

const formatRoleMembers = role => {
  const members = Array.isArray(role?.members) ? role.members : []
  if (!members.length) {
    return '暂无角色成员'
  }

  const preview = members
    .slice(0, 3)
    .map(item => getUserDisplayName(item, item.username))
    .join('、')

  if (members.length <= 3) {
    return preview
  }

  return `${preview} 等 ${members.length} 人`
}
const roleColumnFilters = computed(() => ({
  id: buildTableFilters(roles.value, row => row.id, 20, compareTableNumber),
  name: buildTableFilters(roles.value, row => row.name, 20),
  member_count: buildTableFilters(roles.value, row => row.member_count, 20, compareTableNumber),
  members: buildTableFilters(roles.value, formatRoleMembers, 20),
}))
const roleMemberColumnFilters = computed(() => ({
  username: buildTableFilters(roleMembers.value, row => row.username, 20),
  name: buildTableFilters(roleMembers.value, getMemberName, 20),
  email: buildTableFilters(roleMembers.value, row => row.email, 20),
  department: buildTableFilters(roleMembers.value, row => row.department, 20),
  position: buildTableFilters(roleMembers.value, row => row.position, 20),
  tags: buildTableFilters(roleMembers.value, getRoleMemberTags, 30),
  status: buildTableFilters(roleMembers.value, getRoleMemberStatusLabel, 10),
}))

const buildRoleListParams = () => {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: 'name',
  }

  const keyword = String(filters.keyword || '').trim()
  if (keyword) {
    params.search = keyword
  }

  return params
}

const setCurrentRoleRow = async row => {
  await nextTick()
  roleTableRef.value?.setCurrentRow(row || null)
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
    ElMessage.error(extractErrorMessage(error, '获取角色成员候选列表失败'))
  } finally {
    userOptionsLoading.value = false
  }
}

const loadRoleMembers = async (roleId = selectedRoleId.value) => {
  if (!roleId) {
    roleMembers.value = []
    return
  }

  memberLoading.value = true
  try {
    const response = await api.get(`${ROLE_ENDPOINT}${roleId}/members/`)
    roleMembers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    roleMembers.value = []
    ElMessage.error(extractErrorMessage(error, '获取角色成员列表失败'))
  } finally {
    memberLoading.value = false
  }
}

const syncSelectedRole = async (preferredRoleId = null) => {
  const nextSelectedRole =
    roles.value.find(item => item.id === preferredRoleId) ||
    roles.value[0] ||
    null

  selectedRole.value = nextSelectedRole
  selectedRoleId.value = nextSelectedRole?.id ?? null
  await setCurrentRoleRow(nextSelectedRole)
  return nextSelectedRole
}

const loadRoles = async ({ preserveSelection = true } = {}) => {
  roleLoading.value = true
  try {
    const response = await api.get(ROLE_ENDPOINT, {
      params: buildRoleListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    roles.value = results
    pagination.total = count

    const preferredRoleId = preserveSelection ? selectedRoleId.value : null
    const nextSelectedRole = await syncSelectedRole(preferredRoleId)

    if (nextSelectedRole) {
      await loadRoleMembers(nextSelectedRole.id)
    } else {
      roleMembers.value = []
    }
  } catch (error) {
    roles.value = []
    roleMembers.value = []
    selectedRole.value = null
    selectedRoleId.value = null
    pagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取角色列表失败'))
  } finally {
    roleLoading.value = false
  }
}

const handleRoleRowClick = async row => {
  if (!row || row.id === selectedRoleId.value) {
    return
  }

  selectedRole.value = row
  selectedRoleId.value = row.id
  await setCurrentRoleRow(row)
  await loadRoleMembers(row.id)
}

const refreshSelectedRoleMembers = async () => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
    return
  }

  await loadRoleMembers(selectedRoleId.value)
}

const resetRoleForm = () => {
  Object.assign(roleForm, createDefaultRoleForm())
}

const resetMemberForm = () => {
  Object.assign(memberForm, createDefaultMemberForm())
  editingMemberId.value = null
}

const handleRoleDialogClosed = () => {
  resetRoleForm()
  roleFormRef.value?.clearValidate()
}

const handleMemberDialogClosed = () => {
  resetMemberForm()
  memberFormRef.value?.clearValidate()
}

const openCreateRoleDialog = () => {
  if (!canManageRoles.value) {
    ElMessage.warning('当前账号没有角色管理权限')
    return
  }

  roleDialogMode.value = 'create'
  resetRoleForm()
  roleDialogVisible.value = true
  nextTick(() => {
    roleFormRef.value?.clearValidate()
  })
}

const openEditRoleDialog = row => {
  if (!canManageRoles.value) {
    ElMessage.warning('当前账号没有角色管理权限')
    return
  }

  roleDialogMode.value = 'edit'
  Object.assign(roleForm, {
    id: row.id,
    name: row.name || '',
  })
  roleDialogVisible.value = true
  nextTick(() => {
    roleFormRef.value?.clearValidate()
  })
}

const submitRoleForm = async () => {
  try {
    await roleFormRef.value?.validate()
  } catch {
    return
  }

  roleSaving.value = true
  try {
    const payload = {
      name: String(roleForm.name || '').trim(),
    }

    let response
    if (roleDialogMode.value === 'create') {
      response = await api.post(ROLE_ENDPOINT, payload)
      ElMessage.success('角色已创建')
    } else {
      response = await api.patch(`${ROLE_ENDPOINT}${roleForm.id}/`, payload)
      ElMessage.success('角色已更新')
    }

    selectedRoleId.value = response.data?.id || selectedRoleId.value
    roleDialogVisible.value = false
    await loadRoles({ preserveSelection: true })
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存角色失败'))
  } finally {
    roleSaving.value = false
  }
}

const handleDeleteRole = async row => {
  try {
    await ElMessageBox.confirm(
      `确认删除角色“${row.name}”吗？删除后该角色下的角色成员关系也会解除。`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${ROLE_ENDPOINT}${row.id}/`)
    if (selectedRoleId.value === row.id) {
      selectedRoleId.value = null
      selectedRole.value = null
    }
    ElMessage.success('角色已删除')
    await loadRoles({ preserveSelection: true })
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除角色失败'))
    }
  }
}

const openCreateMemberDialog = async () => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
    return
  }
  if (!canManageRoles.value) {
    ElMessage.warning('当前账号没有角色成员管理权限')
    return
  }

  memberDialogMode.value = 'create'
  resetMemberForm()
  await loadUserOptions()
  if (!availableUserOptions.value.length) {
    ElMessage.warning('当前没有可添加的角色成员')
    return
  }
  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const openEditMemberDialog = async row => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
    return
  }
  if (!canManageRoles.value) {
    ElMessage.warning('当前账号没有角色成员管理权限')
    return
  }

  memberDialogMode.value = 'edit'
  editingMemberId.value = row.id
  memberForm.user_id = row.id
  memberForm.tags = normalizeMemberTags(row.tags)
  await loadUserOptions()
  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const submitMemberForm = async () => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
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
      const normalizedTags = normalizeMemberTags(memberForm.tags)
      const results = await Promise.allSettled(
        selectedUserIds.map(userId =>
          api.post(`${ROLE_ENDPOINT}${selectedRoleId.value}/members/`, {
            user_id: userId,
            tags: normalizedTags,
          })
        )
      )
      const successCount = results.filter(item => item.status === 'fulfilled').length
      const failedResults = results.filter(item => item.status === 'rejected')

      if (!successCount) {
        throw failedResults[0]?.reason || new Error('添加角色成员失败')
      }

      memberDialogVisible.value = false
      await loadRoles({ preserveSelection: true })

      if (failedResults.length) {
        ElMessage.warning(
          `已添加 ${successCount} 名角色成员，${failedResults.length} 名添加失败：${extractErrorMessage(
            failedResults[0]?.reason,
            '请稍后重试'
          )}`
        )
      } else {
        ElMessage.success(`已添加 ${successCount} 名角色成员`)
      }

      return
    } else {
      const payload = {
        user_id: memberForm.user_id,
        tags: normalizeMemberTags(memberForm.tags),
      }
      await api.patch(`${ROLE_ENDPOINT}${selectedRoleId.value}/members/${editingMemberId.value}/`, payload)
      ElMessage.success('角色成员已更新')
    }

    memberDialogVisible.value = false
    await loadRoles({ preserveSelection: true })
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存角色成员失败'))
  } finally {
    memberSaving.value = false
  }
}

const handleRemoveMember = async row => {
  if (!selectedRoleId.value) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认将“${getUserDisplayName(row, row.username)}”移出角色“${selectedRole.value?.name || ''}”吗？`,
      '移除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${ROLE_ENDPOINT}${selectedRoleId.value}/members/${row.id}/`)
    ElMessage.success('角色成员已移除')
    await loadRoles({ preserveSelection: true })
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '移除角色成员失败'))
    }
  }
}

const handleSearch = async () => {
  pagination.page = 1
  await loadRoles({ preserveSelection: false })
}

const handleReset = async () => {
  filters.keyword = ''
  pagination.page = 1
  pagination.pageSize = 20
  await loadRoles({ preserveSelection: false })
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  await loadRoles({ preserveSelection: true })
}

watch(
  () => props.active,
  async active => {
    if (active) {
      await loadRoles({ preserveSelection: true })
    }
  }
)

onMounted(async () => {
  if (props.active) {
    await loadRoles({ preserveSelection: true })
  }
})
</script>

<style scoped lang="scss">
.role-management-panel {
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

.role-search-form {
  min-width: min(100%, 520px);
}

:deep(.role-search-form .el-form-item) {
  margin-bottom: 0;
}

.toolbar-actions,
.section-actions,
.row-actions,
.dialog-footer,
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
  grid-template-columns: minmax(360px, 1fr) minmax(560px, 1.35fr);
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

.role-table,
.member-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.role-table :deep(.el-table__inner-wrapper),
.member-table :deep(.el-table__inner-wrapper) {
  height: 100%;
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

.member-empty-state {
  margin: auto 0;
}

.member-option {
  justify-content: space-between;
}

.member-option__meta {
  color: #909399;
  font-size: 12px;
}

.member-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.form-hint {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: #909399;
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

  .role-search-form,
  .role-search-form :deep(.el-input) {
    width: 100%;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
