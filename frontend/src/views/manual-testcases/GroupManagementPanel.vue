<template>
  <div class="group-management-panel">
    <div class="tab-toolbar">
      <el-form :inline="true" :model="filters" class="search-form group-search-form" @submit.prevent>
        <el-form-item label="组别">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索组别名称"
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
          :table-ref="groupTableRef"
          storage-key="manual-testcases.groups"
        />
        <el-tag effect="plain">组别 {{ pagination.total }}</el-tag>
        <el-button :loading="groupLoading" @click="loadGroups">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :disabled="!canManageGroups" @click="openCreateGroupDialog">
          <el-icon><Plus /></el-icon>
          新增组别
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canManageGroups"
      title="当前账号仅可查看组别和组员信息，新增、编辑、删除组别及维护组员需要管理员权限。"
      type="info"
      :closable="false"
      class="permission-alert"
    />

    <div class="workspace-grid">
      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">组别列表</h3>
            <p class="section-subtitle">维护测试平台中的组别定义</p>
          </div>
        </div>

        <el-table
          ref="groupTableRef"
          v-loading="groupLoading"
          :data="groups"
          row-key="id"
          stripe
          highlight-current-row
          class="group-table"
          :max-height="groupTableMaxHeight"
          style="width: 100%"
          empty-text="暂无组别数据"
          @row-click="handleGroupRowClick"
        >
          <el-table-column
            prop="id"
            label="ID"
            width="80"
            sortable
            :sort-method="createNumberSorter(row => row.id)"
            :filters="groupColumnFilters.id"
            :filter-method="createTableFilter(row => row.id)"
          />
          <el-table-column
            prop="name"
            label="组别名称"
            min-width="200"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.name)"
            :filters="groupColumnFilters.name"
            :filter-method="createTableFilter(row => row.name)"
          />
          <el-table-column
            label="组员数"
            width="100"
            align="center"
            sortable
            :sort-method="createNumberSorter(row => row.member_count)"
            :filters="groupColumnFilters.member_count"
            :filter-method="createTableFilter(row => row.member_count)"
          >
            <template #default="{ row }">{{ row.member_count || 0 }}</template>
          </el-table-column>
          <el-table-column
            label="组员概览"
            min-width="240"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(formatGroupMembers)"
            :filters="groupColumnFilters.members"
            :filter-method="createTableFilter(formatGroupMembers)"
          >
            <template #default="{ row }">{{ formatGroupMembers(row) }}</template>
          </el-table-column>
          <el-table-column v-if="canManageGroups" label="操作" :width="groupActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" @click.stop="openEditGroupDialog(row)">编辑</el-button>
                <el-button link type="danger" @click.stop="handleDeleteGroup(row)">删除</el-button>
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
          @current-change="loadGroups"
          @size-change="handlePageSizeChange"
        />
      </section>

      <section class="section-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">{{ selectedGroup ? `${selectedGroup.name} 组员` : '组员列表' }}</h3>
            <p class="section-subtitle">
              {{ selectedGroup ? `当前组别共 ${groupMembers.length} 名组员` : '请选择左侧组别后查看组员' }}
            </p>
          </div>
          <div class="section-actions">
            <TableColumnSettings
              :table-ref="groupMemberTableRef"
              storage-key="manual-testcases.group-members"
            />
            <el-button :disabled="!selectedGroup" :loading="memberLoading" @click="refreshSelectedGroupMembers">
              <el-icon><Refresh /></el-icon>
              刷新组员
            </el-button>
            <el-button
              type="primary"
              :disabled="!selectedGroup || !canManageGroups"
              @click="openCreateMemberDialog"
            >
              <el-icon><Plus /></el-icon>
              新增组员
            </el-button>
          </div>
        </div>

        <el-empty
          v-if="!selectedGroup && !groupLoading"
          description="请选择组别后查看组员"
          class="member-empty-state"
        />

        <el-table
          v-else
          ref="groupMemberTableRef"
          v-loading="memberLoading"
          :data="groupMembers"
          row-key="id"
          stripe
          class="member-table"
          :max-height="groupMemberTableMaxHeight"
          style="width: 100%"
          empty-text="当前组别暂无组员"
        >
          <el-table-column
            prop="username"
            label="用户名"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.username)"
            :filters="groupMemberColumnFilters.username"
            :filter-method="createTableFilter(row => row.username)"
          />
          <el-table-column
            label="姓名"
            min-width="140"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(getMemberName)"
            :filters="groupMemberColumnFilters.name"
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
            :filters="groupMemberColumnFilters.email"
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
            :filters="groupMemberColumnFilters.department"
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
            :filters="groupMemberColumnFilters.position"
            :filter-method="createTableFilter(row => row.position)"
          >
            <template #default="{ row }">{{ row.position || '-' }}</template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="100"
            align="center"
            sortable
            :sort-method="createTextSorter(getGroupMemberStatusLabel)"
            :filters="groupMemberColumnFilters.status"
            :filter-method="createTableFilter(getGroupMemberStatusLabel)"
          >
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="canManageGroups" label="操作" :width="groupActionColumnWidth" fixed="right">
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
      v-model="groupDialogVisible"
      :title="groupDialogTitle"
      width="520px"
      destroy-on-close
      @closed="handleGroupDialogClosed"
    >
      <el-form ref="groupFormRef" :model="groupForm" :rules="groupRules" label-position="top">
        <el-form-item label="组别名称" prop="name">
          <el-input v-model="groupForm.name" maxlength="150" placeholder="请输入组别名称" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="groupDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="groupSaving" @click="submitGroupForm">
            {{ groupDialogMode === 'create' ? '创建组别' : '保存修改' }}
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
        <el-form-item v-if="memberDialogMode === 'create'" label="组员" prop="user_ids">
          <el-select
            v-model="memberForm.user_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择组员"
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
        <el-form-item v-else label="组员" prop="user_id">
          <el-select
            v-model="memberForm.user_id"
            filterable
            placeholder="请选择组员"
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
            {{ memberDialogMode === 'create' ? '添加组员' : '保存修改' }}
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

const GROUP_ENDPOINT = '/auth/groups/'
const USER_ENDPOINT = '/auth/users/'

const userStore = useUserStore()

const groupTableRef = ref(null)
const groupMemberTableRef = ref(null)
const groupFormRef = ref(null)
const memberFormRef = ref(null)

const groupLoading = ref(false)
const memberLoading = ref(false)
const groupSaving = ref(false)
const memberSaving = ref(false)
const userOptionsLoading = ref(false)

const groupDialogVisible = ref(false)
const memberDialogVisible = ref(false)
const groupDialogMode = ref('create')
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

const groups = ref([])
const selectedGroupId = ref(null)
const selectedGroup = ref(null)
const groupMembers = ref([])
const userOptions = ref([])

const createDefaultGroupForm = () => ({
  id: null,
  name: '',
})

const createDefaultMemberForm = () => ({
  user_id: null,
  user_ids: [],
})

const groupForm = reactive(createDefaultGroupForm())
const memberForm = reactive(createDefaultMemberForm())

const canManageGroups = computed(() => Boolean(userStore.user?.is_staff || userStore.user?.is_superuser))
const groupActionColumnWidth = buildActionColumnWidth([['编辑', '删除']], {
  variant: 'link',
})
const groupDialogTitle = computed(() => (groupDialogMode.value === 'create' ? '新增组别' : '编辑组别'))
const memberDialogTitle = computed(() => (memberDialogMode.value === 'create' ? '新增组员' : '编辑组员'))
const groupTableMaxHeight = 'calc(100vh - 380px)'
const groupMemberTableMaxHeight = 'calc(100vh - 380px)'

const groupRules = {
  name: [{ required: true, message: '请输入组别名称', trigger: 'blur' }],
}

const memberRules = {
  user_id: [{ required: true, message: '请选择组员', trigger: 'change' }],
  user_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一名组员', trigger: 'change' }],
}

const availableUserOptions = computed(() => {
  const occupiedUserIds = new Set(groupMembers.value.map(item => item.id))
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

const getMemberName = member => getUserFullName(member) || '-'
const getGroupMemberStatusLabel = member => (member?.is_active ? '启用' : '停用')

const formatGroupMembers = group => {
  const members = Array.isArray(group?.members) ? group.members : []
  if (!members.length) {
    return '暂无组员'
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
const groupColumnFilters = computed(() => ({
  id: buildTableFilters(groups.value, row => row.id, 20, compareTableNumber),
  name: buildTableFilters(groups.value, row => row.name, 20),
  member_count: buildTableFilters(groups.value, row => row.member_count, 20, compareTableNumber),
  members: buildTableFilters(groups.value, formatGroupMembers, 20),
}))
const groupMemberColumnFilters = computed(() => ({
  username: buildTableFilters(groupMembers.value, row => row.username, 20),
  name: buildTableFilters(groupMembers.value, getMemberName, 20),
  email: buildTableFilters(groupMembers.value, row => row.email, 20),
  department: buildTableFilters(groupMembers.value, row => row.department, 20),
  position: buildTableFilters(groupMembers.value, row => row.position, 20),
  status: buildTableFilters(groupMembers.value, getGroupMemberStatusLabel, 10),
}))

const buildGroupListParams = () => {
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

const setCurrentGroupRow = async row => {
  await nextTick()
  groupTableRef.value?.setCurrentRow(row || null)
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

const loadGroupMembers = async (groupId = selectedGroupId.value) => {
  if (!groupId) {
    groupMembers.value = []
    return
  }

  memberLoading.value = true
  try {
    const response = await api.get(`${GROUP_ENDPOINT}${groupId}/members/`)
    groupMembers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    groupMembers.value = []
    ElMessage.error(extractErrorMessage(error, '获取组员列表失败'))
  } finally {
    memberLoading.value = false
  }
}

const syncSelectedGroup = async (preferredGroupId = null) => {
  const nextSelectedGroup =
    groups.value.find(item => item.id === preferredGroupId) ||
    groups.value[0] ||
    null

  selectedGroup.value = nextSelectedGroup
  selectedGroupId.value = nextSelectedGroup?.id ?? null
  await setCurrentGroupRow(nextSelectedGroup)
  return nextSelectedGroup
}

const loadGroups = async ({ preserveSelection = true } = {}) => {
  groupLoading.value = true
  try {
    const response = await api.get(GROUP_ENDPOINT, {
      params: buildGroupListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    groups.value = results
    pagination.total = count

    const preferredGroupId = preserveSelection ? selectedGroupId.value : null
    const nextSelectedGroup = await syncSelectedGroup(preferredGroupId)

    if (nextSelectedGroup) {
      await loadGroupMembers(nextSelectedGroup.id)
    } else {
      groupMembers.value = []
    }
  } catch (error) {
    groups.value = []
    groupMembers.value = []
    selectedGroup.value = null
    selectedGroupId.value = null
    pagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取组别列表失败'))
  } finally {
    groupLoading.value = false
  }
}

const handleGroupRowClick = async row => {
  if (!row || row.id === selectedGroupId.value) {
    return
  }

  selectedGroup.value = row
  selectedGroupId.value = row.id
  await setCurrentGroupRow(row)
  await loadGroupMembers(row.id)
}

const refreshSelectedGroupMembers = async () => {
  if (!selectedGroupId.value) {
    ElMessage.warning('请先选择组别')
    return
  }

  await loadGroupMembers(selectedGroupId.value)
}

const resetGroupForm = () => {
  Object.assign(groupForm, createDefaultGroupForm())
}

const resetMemberForm = () => {
  Object.assign(memberForm, createDefaultMemberForm())
  editingMemberId.value = null
}

const handleGroupDialogClosed = () => {
  resetGroupForm()
  groupFormRef.value?.clearValidate()
}

const handleMemberDialogClosed = () => {
  resetMemberForm()
  memberFormRef.value?.clearValidate()
}

const openCreateGroupDialog = () => {
  if (!canManageGroups.value) {
    ElMessage.warning('当前账号没有组别管理权限')
    return
  }

  groupDialogMode.value = 'create'
  resetGroupForm()
  groupDialogVisible.value = true
  nextTick(() => {
    groupFormRef.value?.clearValidate()
  })
}

const openEditGroupDialog = row => {
  if (!canManageGroups.value) {
    ElMessage.warning('当前账号没有组别管理权限')
    return
  }

  groupDialogMode.value = 'edit'
  Object.assign(groupForm, {
    id: row.id,
    name: row.name || '',
  })
  groupDialogVisible.value = true
  nextTick(() => {
    groupFormRef.value?.clearValidate()
  })
}

const submitGroupForm = async () => {
  try {
    await groupFormRef.value?.validate()
  } catch {
    return
  }

  groupSaving.value = true
  try {
    const payload = {
      name: String(groupForm.name || '').trim(),
    }

    let response
    if (groupDialogMode.value === 'create') {
      response = await api.post(GROUP_ENDPOINT, payload)
      ElMessage.success('组别已创建')
    } else {
      response = await api.patch(`${GROUP_ENDPOINT}${groupForm.id}/`, payload)
      ElMessage.success('组别已更新')
    }

    selectedGroupId.value = response.data?.id || selectedGroupId.value
    groupDialogVisible.value = false
    await loadGroups({ preserveSelection: true })
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存组别失败'))
  } finally {
    groupSaving.value = false
  }
}

const handleDeleteGroup = async row => {
  try {
    await ElMessageBox.confirm(
      `确认删除组别“${row.name}”吗？删除后该组别下的组员关系也会解除。`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${GROUP_ENDPOINT}${row.id}/`)
    if (selectedGroupId.value === row.id) {
      selectedGroupId.value = null
      selectedGroup.value = null
    }
    ElMessage.success('组别已删除')
    await loadGroups({ preserveSelection: true })
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除组别失败'))
    }
  }
}

const openCreateMemberDialog = async () => {
  if (!selectedGroupId.value) {
    ElMessage.warning('请先选择组别')
    return
  }
  if (!canManageGroups.value) {
    ElMessage.warning('当前账号没有组员管理权限')
    return
  }

  memberDialogMode.value = 'create'
  resetMemberForm()
  await loadUserOptions()
  if (!availableUserOptions.value.length) {
    ElMessage.warning('当前没有可添加的组员')
    return
  }
  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const openEditMemberDialog = async row => {
  if (!selectedGroupId.value) {
    ElMessage.warning('请先选择组别')
    return
  }
  if (!canManageGroups.value) {
    ElMessage.warning('当前账号没有组员管理权限')
    return
  }

  memberDialogMode.value = 'edit'
  editingMemberId.value = row.id
  memberForm.user_id = row.id
  await loadUserOptions()
  memberDialogVisible.value = true
  nextTick(() => {
    memberFormRef.value?.clearValidate()
  })
}

const submitMemberForm = async () => {
  if (!selectedGroupId.value) {
    ElMessage.warning('请先选择组别')
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
          api.post(`${GROUP_ENDPOINT}${selectedGroupId.value}/members/`, {
            user_id: userId,
          })
        )
      )
      const successCount = results.filter(item => item.status === 'fulfilled').length
      const failedResults = results.filter(item => item.status === 'rejected')

      if (!successCount) {
        throw failedResults[0]?.reason || new Error('添加组员失败')
      }

      memberDialogVisible.value = false
      await loadGroups({ preserveSelection: true })

      if (failedResults.length) {
        ElMessage.warning(
          `已添加 ${successCount} 名组员，${failedResults.length} 名添加失败：${extractErrorMessage(
            failedResults[0]?.reason,
            '请稍后重试'
          )}`
        )
      } else {
        ElMessage.success(`已添加 ${successCount} 名组员`)
      }

      return
    } else {
      const payload = {
        user_id: memberForm.user_id,
      }
      await api.patch(`${GROUP_ENDPOINT}${selectedGroupId.value}/members/${editingMemberId.value}/`, payload)
      ElMessage.success('组员已更新')
    }

    memberDialogVisible.value = false
    await loadGroups({ preserveSelection: true })
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存组员失败'))
  } finally {
    memberSaving.value = false
  }
}

const handleRemoveMember = async row => {
  if (!selectedGroupId.value) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认将“${getUserDisplayName(row, row.username)}”移出组别“${selectedGroup.value?.name || ''}”吗？`,
      '移除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${GROUP_ENDPOINT}${selectedGroupId.value}/members/${row.id}/`)
    ElMessage.success('组员已移除')
    await loadGroups({ preserveSelection: true })
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '移除组员失败'))
    }
  }
}

const handleSearch = async () => {
  pagination.page = 1
  await loadGroups({ preserveSelection: false })
}

const handleReset = async () => {
  filters.keyword = ''
  pagination.page = 1
  pagination.pageSize = 20
  await loadGroups({ preserveSelection: false })
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  await loadGroups({ preserveSelection: true })
}

watch(
  () => props.active,
  async active => {
    if (active) {
      await loadGroups({ preserveSelection: true })
    }
  }
)

onMounted(async () => {
  if (props.active) {
    await loadGroups({ preserveSelection: true })
  }
})
</script>

<style scoped lang="scss">
.group-management-panel {
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

.group-search-form {
  min-width: min(100%, 520px);
}

:deep(.group-search-form .el-form-item) {
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

.group-table,
.member-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.group-table :deep(.el-table__inner-wrapper),
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

  .group-search-form,
  .group-search-form :deep(.el-input) {
    width: 100%;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
