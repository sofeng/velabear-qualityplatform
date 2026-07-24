<template>
  <div class="member-management-panel">
    <div class="tab-toolbar">
      <el-form :inline="true" :model="filters" class="search-form member-search-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索用户名、姓名、邮箱、部门或职位"
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
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option label="启用" value="true" />
            <el-option label="停用" value="false" />
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
          :table-ref="memberTableRef"
          storage-key="manual-testcases.members"
        />
        <el-tag effect="plain">成员 {{ pagination.total }}</el-tag>
        <el-button :loading="loading" @click="loadMembers">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :disabled="!canManageUsers" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新增成员
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canManageUsers"
      title="当前账号仅可查看成员列表，新增、编辑、启停和删除成员需要管理员权限。"
      type="info"
      :closable="false"
      class="permission-alert"
    />

    <el-table
      ref="memberTableRef"
      v-loading="loading"
      :data="members"
      row-key="id"
      stripe
      class="member-table"
      :max-height="memberTableMaxHeight"
      style="width: 100%"
      empty-text="暂无成员数据"
    >
      <el-table-column
        prop="id"
        label="ID"
        width="80"
        sortable
        :sort-method="createNumberSorter(row => row.id)"
        :filters="memberColumnFilters.id"
        :filter-method="createTableFilter(row => row.id)"
      />
      <el-table-column
        label="用户名"
        min-width="180"
        sortable
        :sort-method="createTextSorter(row => row.username)"
        :filters="memberColumnFilters.username"
        :filter-method="createTableFilter(row => row.username)"
      >
        <template #default="{ row }">
          <div class="member-identity">
            <span>{{ row.username || '-' }}</span>
            <el-tag v-if="isCurrentUser(row)" size="small" type="info">当前登录</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="姓名"
        min-width="140"
        show-overflow-tooltip
        sortable
        :sort-method="createTextSorter(getMemberName)"
        :filters="memberColumnFilters.name"
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
        :filters="memberColumnFilters.email"
        :filter-method="createTableFilter(row => row.email)"
      >
        <template #default="{ row }">{{ row.email || '-' }}</template>
      </el-table-column>
      <el-table-column
        prop="phone"
        label="手机号"
        min-width="140"
        sortable
        :sort-method="createTextSorter(row => row.phone)"
        :filters="memberColumnFilters.phone"
        :filter-method="createTableFilter(row => row.phone)"
      >
        <template #default="{ row }">{{ row.phone || '-' }}</template>
      </el-table-column>
      <el-table-column
        prop="department"
        label="部门"
        min-width="160"
        show-overflow-tooltip
        sortable
        :sort-method="createTextSorter(row => row.department)"
        :filters="memberColumnFilters.department"
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
        :filters="memberColumnFilters.position"
        :filter-method="createTableFilter(row => row.position)"
      >
        <template #default="{ row }">{{ row.position || '-' }}</template>
      </el-table-column>
      <el-table-column
        label="状态"
        width="100"
        align="center"
        sortable
        :sort-method="createTextSorter(getMemberStatusLabel)"
        :filters="memberColumnFilters.status"
        :filter-method="createTableFilter(getMemberStatusLabel)"
      >
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="权限"
        min-width="180"
        sortable
        :sort-method="createTextSorter(getMemberPermissionLabel)"
        :filters="memberColumnFilters.permission"
        :filter-method="createTableFilter(getMemberPermissionLabel)"
      >
        <template #default="{ row }">
          <div class="role-tags">
            <el-tag v-if="row.is_superuser" type="danger">超级管理员</el-tag>
            <el-tag v-else-if="row.is_staff" type="warning">管理员</el-tag>
            <el-tag v-else type="info">成员</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="加入时间"
        min-width="180"
        sortable
        :sort-method="createDateSorter(row => row.date_joined || row.created_at)"
        :filters="memberColumnFilters.date_joined"
        :filter-method="createTableFilter(getMemberJoinedAt)"
      >
        <template #default="{ row }">{{ formatDate(row.date_joined || row.created_at) }}</template>
      </el-table-column>
      <el-table-column v-if="canManageUsers" label="操作" :width="memberActionColumnWidth" fixed="right">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              link
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleMemberStatus(row)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button
              link
              type="warning"
              @click="openResetPasswordDialog(row)"
            >
              重置密码
            </el-button>
            <el-button
              link
              type="danger"
              :disabled="isCurrentUser(row)"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
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
      @current-change="loadMembers"
      @size-change="handlePageSizeChange"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="820px"
      destroy-on-close
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="member-form">
        <el-divider content-position="left">基础信息</el-divider>
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" maxlength="150" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" maxlength="254" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
          <el-col v-if="dialogMode === 'create'" :xs="24" :md="12">
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                maxlength="128"
                placeholder="不少于 6 位"
              />
            </el-form-item>
          </el-col>
          <el-col v-if="dialogMode === 'create'" :xs="24" :md="12">
            <el-form-item label="确认密码" prop="password_confirm">
              <el-input
                v-model="form.password_confirm"
                type="password"
                show-password
                maxlength="128"
                placeholder="请再次输入密码"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="姓" prop="first_name">
              <el-input v-model="form.first_name" maxlength="150" placeholder="请输入姓" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="名" prop="last_name">
              <el-input v-model="form.last_name" maxlength="150" placeholder="请输入名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" maxlength="11" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="部门" prop="department">
              <el-input v-model="form.department" maxlength="100" placeholder="请输入部门" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="职位" prop="position">
              <el-input v-model="form.position" maxlength="100" placeholder="请输入职位" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">权限设置</el-divider>
        <el-row :gutter="16">
          <el-col :xs="24" :md="8">
            <el-form-item label="启用状态">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="管理员">
              <el-switch v-model="form.is_staff" :disabled="form.is_superuser" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="超级管理员">
              <el-switch v-model="form.is_superuser" @change="handleSuperuserChange" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            {{ dialogMode === 'create' ? '创建成员' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="resetPasswordDialogVisible"
      title="重置密码"
      width="500px"
      destroy-on-close
      @closed="handleResetPasswordDialogClosed"
    >
      <el-alert
        :title="`正在为用户 ${resetPasswordForm.username} 重置密码`"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordRules"
        label-position="top"
      >
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="resetPasswordForm.password"
            type="password"
            show-password
            maxlength="128"
            placeholder="不少于 6 位"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="password_confirm">
          <el-input
            v-model="resetPasswordForm.password_confirm"
            type="password"
            show-password
            maxlength="128"
            placeholder="请再次输入密码"
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="resettingPassword" @click="handleResetPassword">
            确认重置
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
  createDateSorter,
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

const USER_ENDPOINT = '/auth/users/'

const userStore = useUserStore()

const loading = ref(false)
const memberTableRef = ref(null)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref('create')
const members = ref([])
const formRef = ref(null)

// 重置密码相关
const resetPasswordDialogVisible = ref(false)
const resetPasswordFormRef = ref(null)
const resettingPassword = ref(false)

const filters = reactive({
  keyword: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const createDefaultForm = () => ({
  id: null,
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
  phone: '',
  department: '',
  position: '',
  is_active: true,
  is_staff: false,
  is_superuser: false,
})

const form = reactive(createDefaultForm())

// 重置密码表单
const createDefaultResetPasswordForm = () => ({
  id: null,
  username: '',
  password: '',
  password_confirm: '',
})

const resetPasswordForm = reactive(createDefaultResetPasswordForm())

const canManageUsers = computed(() => Boolean(userStore.user?.is_staff || userStore.user?.is_superuser))
const memberActionColumnWidth = buildActionColumnWidth([[
  '编辑',
  '停用',
  '重置密码',
  '删除',
]], {
  variant: 'link',
})
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增成员' : '编辑成员'))
const memberTableMaxHeight = 'calc(100vh - 340px)'

const validatePassword = (_rule, value, callback) => {
  if (dialogMode.value !== 'create') {
    callback()
    return
  }

  if (!value) {
    callback(new Error('请输入密码'))
    return
  }

  if (String(value).length < 6) {
    callback(new Error('密码长度不能少于 6 位'))
    return
  }

  callback()
}

const validatePasswordConfirm = (_rule, value, callback) => {
  if (dialogMode.value !== 'create') {
    callback()
    return
  }

  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }

  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }

  callback()
}

// 重置密码验证函数
const validateResetPassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入新密码'))
    return
  }

  if (String(value).length < 6) {
    callback(new Error('密码长度不能少于 6 位'))
    return
  }

  callback()
}

const validateResetPasswordConfirm = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }

  if (value !== resetPasswordForm.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }

  callback()
}

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] }],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  password_confirm: [{ validator: validatePasswordConfirm, trigger: 'blur' }],
}

// 重置密码验证规则
const resetPasswordRules = {
  password: [{ validator: validateResetPassword, trigger: 'blur' }],
  password_confirm: [{ validator: validateResetPasswordConfirm, trigger: 'blur' }],
}

const normalizeApiList = data => {
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

const getMemberName = member => getUserFullName(member) || '-'
const isCurrentUser = member => Number(member?.id) === Number(userStore.user?.id)
const getMemberStatusLabel = member => (member?.is_active ? '启用' : '停用')
const getMemberPermissionLabel = member => (
  member?.is_superuser ? '超级管理员' : member?.is_staff ? '管理员' : '成员'
)

const formatDate = value => {
  if (!value) {
    return '-'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString('zh-CN')
}
const getMemberJoinedAt = member => formatDate(member?.date_joined || member?.created_at)
const memberColumnFilters = computed(() => ({
  id: buildTableFilters(members.value, row => row.id, 20, compareTableNumber),
  username: buildTableFilters(members.value, row => row.username, 20),
  name: buildTableFilters(members.value, getMemberName, 20),
  email: buildTableFilters(members.value, row => row.email, 20),
  phone: buildTableFilters(members.value, row => row.phone, 20),
  department: buildTableFilters(members.value, row => row.department, 20),
  position: buildTableFilters(members.value, row => row.position, 20),
  status: buildTableFilters(members.value, getMemberStatusLabel, 10),
  permission: buildTableFilters(members.value, getMemberPermissionLabel, 10),
  date_joined: buildTableFilters(members.value, getMemberJoinedAt, 20),
}))

const buildListParams = () => {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: 'username',
  }

  const keyword = String(filters.keyword || '').trim()
  if (keyword) {
    params.search = keyword
  }

  if (filters.status === 'true' || filters.status === 'false') {
    params.is_active = filters.status
  }

  return params
}

const loadMembers = async () => {
  loading.value = true
  try {
    const response = await api.get(USER_ENDPOINT, {
      params: buildListParams(),
    })
    const { results, count } = normalizeApiList(response.data)
    members.value = results
    pagination.total = count
  } catch (error) {
    members.value = []
    pagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取成员列表失败'))
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

const openCreateDialog = () => {
  if (!canManageUsers.value) {
    ElMessage.warning('当前账号没有成员管理权限')
    return
  }

  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

const openEditDialog = member => {
  if (!canManageUsers.value) {
    ElMessage.warning('当前账号没有成员管理权限')
    return
  }

  dialogMode.value = 'edit'
  Object.assign(form, {
    id: member.id,
    username: member.username || '',
    email: member.email || '',
    password: '',
    password_confirm: '',
    first_name: member.first_name || '',
    last_name: member.last_name || '',
    phone: member.phone || '',
    department: member.department || '',
    position: member.position || '',
    is_active: member.is_active !== false,
    is_staff: Boolean(member.is_staff),
    is_superuser: Boolean(member.is_superuser),
  })
  dialogVisible.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 重置密码相关函数
const openResetPasswordDialog = member => {
  if (!canManageUsers.value) {
    ElMessage.warning('当前账号没有成员管理权限')
    return
  }

  if (isCurrentUser(member)) {
    ElMessage.warning('不能重置当前登录账号的密码，请使用个人中心的修改密码功能')
    return
  }

  Object.assign(resetPasswordForm, {
    id: member.id,
    username: member.username || '',
    password: '',
    password_confirm: '',
  })

  resetPasswordDialogVisible.value = true
  nextTick(() => {
    resetPasswordFormRef.value?.clearValidate()
  })
}

const handleResetPasswordDialogClosed = () => {
  Object.assign(resetPasswordForm, createDefaultResetPasswordForm())
  resetPasswordFormRef.value?.clearValidate()
}

const handleResetPassword = async () => {
  try {
    await resetPasswordFormRef.value?.validate()
  } catch {
    return
  }

  resettingPassword.value = true
  try {
    const payload = {
      password: resetPasswordForm.password,
      password_confirm: resetPasswordForm.password_confirm,
    }

    await api.post(`${USER_ENDPOINT}${resetPasswordForm.id}/reset_password/`, payload)
    ElMessage.success(`用户 ${resetPasswordForm.username} 的密码已重置`)
    resetPasswordDialogVisible.value = false
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '重置密码失败'))
  } finally {
    resettingPassword.value = false
  }
}

const buildPayload = () => {
  const payload = {
    username: String(form.username || '').trim(),
    email: String(form.email || '').trim(),
    first_name: String(form.first_name || '').trim(),
    last_name: String(form.last_name || '').trim(),
    phone: String(form.phone || '').trim(),
    department: String(form.department || '').trim(),
    position: String(form.position || '').trim(),
    is_active: Boolean(form.is_active),
    is_staff: Boolean(form.is_superuser || form.is_staff),
    is_superuser: Boolean(form.is_superuser),
  }

  if (dialogMode.value === 'create') {
    payload.password = form.password
    payload.password_confirm = form.password_confirm
  }

  return payload
}

const handleSuperuserChange = value => {
  if (value) {
    form.is_staff = true
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()

    if (dialogMode.value === 'create') {
      await api.post(USER_ENDPOINT, payload)
      ElMessage.success(`成员 ${payload.username} 已创建`)
    } else {
      await api.patch(`${USER_ENDPOINT}${form.id}/`, payload)
      ElMessage.success(`成员 ${getUserDisplayName(form, form.username)} 已更新`)
    }

    dialogVisible.value = false
    await loadMembers()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存成员失败'))
  } finally {
    saving.value = false
  }
}

const toggleMemberStatus = async member => {
  try {
    const nextStatus = !member.is_active
    await ElMessageBox.confirm(
      `确认将成员“${getUserDisplayName(member, member.username)}”设为${nextStatus ? '启用' : '停用'}吗？`,
      '状态变更确认',
      {
        type: 'warning',
      }
    )

    await api.patch(`${USER_ENDPOINT}${member.id}/`, {
      is_active: nextStatus,
    })
    ElMessage.success(`成员已${nextStatus ? '启用' : '停用'}`)
    await loadMembers()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '更新成员状态失败'))
    }
  }
}

const handleDelete = async member => {
  if (isCurrentUser(member)) {
    ElMessage.warning('不能删除当前登录账号')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除成员“${getUserDisplayName(member, member.username)}”吗？删除后将无法恢复。`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${USER_ENDPOINT}${member.id}/`)
    ElMessage.success('成员已删除')

    if (members.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }

    await loadMembers()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除成员失败'))
    }
  }
}

const handleSearch = async () => {
  pagination.page = 1
  await loadMembers()
}

const handleReset = async () => {
  filters.keyword = ''
  filters.status = ''
  pagination.page = 1
  pagination.pageSize = 20
  await loadMembers()
}

const handlePageSizeChange = async () => {
  pagination.page = 1
  await loadMembers()
}

watch(
  () => props.active,
  async active => {
    if (active) {
      await loadMembers()
    }
  }
)

onMounted(async () => {
  if (props.active) {
    await loadMembers()
  }
})
</script>

<style scoped lang="scss">
.member-management-panel {
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

.member-search-form {
  min-width: min(100%, 560px);
}

:deep(.member-search-form .el-form-item) {
  margin-bottom: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.permission-alert {
  margin-bottom: 4px;
}

.member-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.member-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.member-identity,
.role-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: nowrap;
  width: 100%;
  white-space: nowrap;
}

.row-actions :deep(.el-button) {
  margin-left: 0;
}

.member-form {
  padding-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.tab-pagination {
  margin-top: auto;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .tab-toolbar,
  .toolbar-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .member-search-form,
  .member-search-form :deep(.el-input),
  .member-search-form :deep(.el-select) {
    width: 100%;
  }

  .tab-pagination {
    justify-content: center;
  }
}
</style>
