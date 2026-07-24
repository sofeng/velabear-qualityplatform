<template>
  <div class="permission-management-panel">
    <el-tabs v-model="activePermissionSubTab" class="permission-sub-tabs">
      <el-tab-pane
        v-for="tab in accessiblePermissionSubTabs"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name"
      />
    </el-tabs>

    <div v-if="activePermissionSubTab === 'ui-role-permissions'" class="tab-toolbar">
      <el-form :inline="true" :model="roleFilters" class="search-form role-search-form" @submit.prevent>
        <el-form-item label="角色">
          <el-input
            v-model="roleFilters.keyword"
            clearable
            placeholder="请输入角色名称"
            style="width: 280px"
            @keyup.enter="handleRoleSearch"
            @clear="handleRoleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleRoleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleRoleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-actions">
        <TableColumnSettings
          :table-ref="roleTableRef"
          storage-key="manual-testcases.permission-roles"
        />
        <el-tag effect="plain">角色 {{ rolePagination.total }}</el-tag>
        <el-button :loading="roleLoading" @click="loadRoles">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!canManagePermissions"
      title="当前账号仅可查看角色权限与权限目录信息，新增、编辑、删除权限项及维护角色权限需要对应授权。"
      type="info"
      :closable="false"
      class="permission-alert"
    />

    <div v-if="activePermissionSubTab === 'ui-role-permissions'" class="workspace-grid">
      <section class="section-panel permission-role-panel">
        <div class="section-header">
          <div>
            <h3 class="section-title">角色列表</h3>
            <p class="section-subtitle">选择角色后维护该角色的平台权限</p>
          </div>
        </div>

        <div class="permission-role-table-wrapper">
          <el-table
            ref="roleTableRef"
            v-loading="roleLoading"
            :data="roles"
            row-key="id"
            stripe
            highlight-current-row
            class="role-table"
            height="100%"
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
              :filters="permissionRoleColumnFilters.id"
              :filter-method="createTableFilter(row => row.id)"
            />
            <el-table-column
              prop="name"
              label="角色名称"
              min-width="180"
              show-overflow-tooltip
              sortable
              :sort-method="createTextSorter(row => row.name)"
              :filters="permissionRoleColumnFilters.name"
              :filter-method="createTableFilter(row => row.name)"
            />
            <el-table-column
              label="角色成员数"
              width="120"
              align="center"
              sortable
              :sort-method="createNumberSorter(row => row.member_count)"
              :filters="permissionRoleColumnFilters.member_count"
              :filter-method="createTableFilter(row => row.member_count)"
            >
              <template #default="{ row }">{{ row.member_count || 0 }}</template>
            </el-table-column>
          </el-table>
        </div>

        <el-pagination
          v-model:current-page="rolePagination.page"
          v-model:page-size="rolePagination.pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[10, 20, 50, 100]"
          :total="rolePagination.total"
          class="tab-pagination"
          @current-change="loadRoles"
          @size-change="handleRolePageSizeChange"
        />
      </section>

      <div class="permission-right-column permission-right-column--single">
        <section class="section-panel permission-assignment-panel">
          <div class="section-header">
            <div>
              <h3 class="section-title">{{ selectedRole ? `${selectedRole.name} 角色权限` : '角色权限分配' }}</h3>
              <p class="section-subtitle">
                {{ selectedRole ? '勾选后保存，支持模块、菜单、按钮、操作项四类权限' : '请先选择左侧角色后再维护权限' }}
              </p>
            </div>
            <div class="section-actions">
              <el-button :disabled="!selectedRole" :loading="assignmentLoading" @click="refreshRolePermissions">
                <el-icon><Refresh /></el-icon>
                刷新权限
              </el-button>
              <el-button :disabled="!selectedRole" @click="checkAllPermissions">全选</el-button>
              <el-button :disabled="!selectedRole" @click="clearAllPermissions">清空</el-button>
              <el-button
                type="primary"
                :disabled="!selectedRole || !canAssignRolePermissions"
                :loading="assignmentSaving"
                @click="saveRolePermissions"
              >
                <el-icon><Check /></el-icon>
                保存权限
              </el-button>
            </div>
          </div>

          <el-empty
            v-if="!selectedRole && !roleLoading"
            description="请选择角色后查看权限树"
            class="tree-empty-state"
          />

          <template v-else>
            <div class="summary-tags">
              <el-tag effect="plain">模块 {{ rolePermissionSummary.module }}</el-tag>
              <el-tag effect="plain" type="success">菜单 {{ rolePermissionSummary.menu }}</el-tag>
              <el-tag effect="plain" type="warning">按钮 {{ rolePermissionSummary.button }}</el-tag>
              <el-tag effect="plain" type="danger">操作项 {{ rolePermissionSummary.action }}</el-tag>
            </div>

            <div
              v-loading="assignmentLoading || permissionTreeLoading"
              class="permission-tree-wrapper permission-tree-wrapper--table"
            >
              <div class="permission-tree-table__header">
                <div class="permission-tree-table__header-content">
                  <span>节点名称</span>
                  <span>标签</span>
                  <span>权限控制路径</span>
                </div>
              </div>
              <el-tree
                ref="permissionTreeRef"
                :data="permissionTreeData"
                node-key="id"
                show-checkbox
                check-on-click-node
                class="permission-tree permission-tree--table"
                empty-text="暂无权限目录，请先在“权限目录”中新增权限项"
              >
                <template #default="{ data }">
                  <div class="permission-tree-node">
                    <div class="permission-tree-node__cell permission-tree-node__cell--name">
                      <span class="permission-tree-node__name">{{ data.name }}</span>
                      <span class="permission-tree-node__code">{{ data.code }}</span>
                    </div>
                    <div class="permission-tree-node__cell permission-tree-node__cell--tags">
                      <el-tag size="small" effect="plain">{{ formatPermissionType(data.item_type) }}</el-tag>
                      <el-tag v-if="!data.is_active" size="small" type="info">停用</el-tag>
                    </div>
                    <div class="permission-tree-node__cell permission-tree-node__cell--path">
                      <span class="permission-tree-node__path">{{ data.route_path || '-' }}</span>
                    </div>
                  </div>
                </template>
              </el-tree>
            </div>
          </template>
        </section>
      </div>
    </div>

    <section v-if="activePermissionSubTab === 'permission-catalog'" class="section-panel permission-catalog-panel">
      <div class="section-header">
        <div>
          <h3 class="section-title">权限目录</h3>
          <p class="section-subtitle">维护平台模块、菜单、按钮、操作项的权限目录</p>
        </div>
        <div class="section-actions">
          <TableColumnSettings
            :table-ref="permissionItemTableRef"
            storage-key="manual-testcases.permission-items"
          />
          <el-button :loading="permissionItemLoading" @click="loadPermissionItems">
            <el-icon><Refresh /></el-icon>
            刷新目录
          </el-button>
          <el-button type="primary" :disabled="!canCreatePermissionItem" @click="openCreatePermissionDialog">
            <el-icon><Plus /></el-icon>
            新增权限项
          </el-button>
        </div>
      </div>

      <el-form :inline="true" :model="permissionFilters" class="search-form permission-search-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="permissionFilters.keyword"
            clearable
            placeholder="请输入权限名称、编码或路由"
            style="width: 280px"
            @keyup.enter="handlePermissionSearch"
            @clear="handlePermissionSearch"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="permissionFilters.itemType"
            clearable
            placeholder="全部"
            style="width: 140px"
          >
            <el-option
              v-for="option in permissionTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="permissionFilters.isActive"
            clearable
            placeholder="全部"
            style="width: 140px"
          >
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handlePermissionSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handlePermissionReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <el-table
        ref="permissionItemTableRef"
        v-loading="permissionItemLoading"
        :data="permissionItems"
        row-key="id"
        stripe
        class="permission-item-table"
        :max-height="permissionItemTableMaxHeight"
        style="width: 100%"
        empty-text="暂无权限项数据"
      >
        <el-table-column
          prop="id"
          label="ID"
          width="80"
          sortable
          :sort-method="createNumberSorter(row => row.id)"
          :filters="permissionItemColumnFilters.id"
          :filter-method="createTableFilter(row => row.id)"
        />
        <el-table-column
          prop="name"
          label="权限名称"
          min-width="160"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.name)"
          :filters="permissionItemColumnFilters.name"
          :filter-method="createTableFilter(row => row.name)"
        />
        <el-table-column
          label="类型"
          width="120"
          sortable
          :sort-method="createTextSorter(getPermissionItemTypeLabel)"
          :filters="permissionItemColumnFilters.item_type"
          :filter-method="createTableFilter(getPermissionItemTypeLabel)"
        >
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ formatPermissionType(row.item_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="code"
          label="权限编码"
          min-width="220"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.code)"
          :filters="permissionItemColumnFilters.code"
          :filter-method="createTableFilter(row => row.code)"
        />
        <el-table-column
          prop="parent_name"
          label="父级权限"
          min-width="150"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.parent_name)"
          :filters="permissionItemColumnFilters.parent_name"
          :filter-method="createTableFilter(row => row.parent_name)"
        >
          <template #default="{ row }">{{ row.parent_name || '-' }}</template>
        </el-table-column>
        <el-table-column
          prop="route_path"
          label="路由路径"
          min-width="220"
          show-overflow-tooltip
          sortable
          :sort-method="createTextSorter(row => row.route_path)"
          :filters="permissionItemColumnFilters.route_path"
          :filter-method="createTableFilter(row => row.route_path)"
        >
          <template #default="{ row }">{{ row.route_path || '-' }}</template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="100"
          align="center"
          sortable
          :sort-method="createTextSorter(getPermissionItemStatusLabel)"
          :filters="permissionItemColumnFilters.status"
          :filter-method="createTableFilter(getPermissionItemStatusLabel)"
        >
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="sort_order"
          label="排序"
          width="90"
          align="center"
          sortable
          :sort-method="createNumberSorter(row => row.sort_order)"
          :filters="permissionItemColumnFilters.sort_order"
          :filter-method="createTableFilter(row => row.sort_order)"
        />
        <el-table-column v-if="canOperatePermissionItems" label="操作" :width="permissionItemActionColumnWidth" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button v-if="canEditPermissionItem" link type="primary" @click="openEditPermissionDialog(row)">编辑</el-button>
              <el-button v-if="canDeletePermissionItem" link type="danger" @click="handleDeletePermissionItem(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="permissionPagination.page"
        v-model:page-size="permissionPagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        :total="permissionPagination.total"
        class="tab-pagination"
        @current-change="loadPermissionItems"
        @size-change="handlePermissionPageSizeChange"
      />
    </section>

    <el-dialog
      v-model="permissionDialogVisible"
      :title="permissionDialogTitle"
      width="680px"
      destroy-on-close
      @closed="handlePermissionDialogClosed"
    >
      <el-form ref="permissionFormRef" :model="permissionForm" :rules="permissionRules" label-position="top">
        <div class="dialog-grid">
          <el-form-item label="权限名称" prop="name">
            <el-input v-model="permissionForm.name" maxlength="100" placeholder="请输入权限名称" />
          </el-form-item>
          <el-form-item label="权限编码" prop="code">
            <el-input
              v-model="permissionForm.code"
              maxlength="150"
              placeholder="请输入权限编码，例如 menu:manual-testcases:permissions"
            />
          </el-form-item>
          <el-form-item label="权限类型" prop="item_type">
            <el-select v-model="permissionForm.item_type" placeholder="请选择权限类型" style="width: 100%">
              <el-option
                v-for="option in permissionTypeOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="父级权限" prop="parent">
            <el-select
              v-model="permissionForm.parent"
              clearable
              :disabled="permissionForm.item_type === 'module'"
              placeholder="请选择父级权限"
              style="width: 100%"
            >
              <el-option
                v-for="item in parentPermissionOptions"
                :key="item.id"
                :label="item.optionLabel"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="路由路径" prop="route_path">
            <el-input
              v-model="permissionForm.route_path"
              maxlength="255"
              placeholder="可选，例如 /manual-testcases/list?tab=permissions"
            />
          </el-form-item>
          <el-form-item label="排序值" prop="sort_order">
            <el-input-number v-model="permissionForm.sort_order" :min="0" :max="99999" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item label="权限状态" prop="is_active">
          <el-switch v-model="permissionForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="permissionForm.description"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="可选，用于说明该权限项的用途"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="permissionDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="permissionSaving" @click="submitPermissionForm">
            {{ permissionDialogMode === 'create' ? '创建权限项' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { Check, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import {
  buildTableFilters,
  compareTableNumber,
  createNumberSorter,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { PERMISSION_CODES, hasPermissionAccess } from '@/utils/permissions'

const props = defineProps({
  active: {
    type: Boolean,
    default: true,
  },
})

const ROLE_ENDPOINT = '/auth/roles/'
const PERMISSION_ITEM_ENDPOINT = '/auth/permission-items/'

const userStore = useUserStore()

const permissionTypeOptions = [
  { label: '模块', value: 'module' },
  { label: '菜单', value: 'menu' },
  { label: '按钮', value: 'button' },
  { label: '操作项', value: 'action' },
]

const roleTableRef = ref(null)
const permissionItemTableRef = ref(null)
const permissionTreeRef = ref(null)
const permissionFormRef = ref(null)

const roleLoading = ref(false)
const permissionTreeLoading = ref(false)
const assignmentLoading = ref(false)
const assignmentSaving = ref(false)
const permissionItemLoading = ref(false)
const permissionSaving = ref(false)

const activePermissionSubTab = ref('ui-role-permissions')
const permissionDialogVisible = ref(false)
const permissionDialogMode = ref('create')

const roleFilters = reactive({
  keyword: '',
})

const permissionFilters = reactive({
  keyword: '',
  itemType: '',
  isActive: '',
})

const rolePagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const permissionPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const roles = ref([])
const selectedRoleId = ref(null)
const selectedRole = ref(null)
const permissionTreeData = ref([])
const permissionItems = ref([])
const assignedPermissionIds = ref([])
const rolePermissionSummary = reactive({
  module: 0,
  menu: 0,
  button: 0,
  action: 0,
})

const createDefaultPermissionForm = () => ({
  id: null,
  name: '',
  code: '',
  item_type: 'menu',
  parent: null,
  route_path: '',
  sort_order: 0,
  is_active: true,
  description: '',
})

const permissionForm = reactive(createDefaultPermissionForm())

const canAssignRolePermissions = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.permissionAssign))
const canCreatePermissionItem = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.permissionCreate))
const canEditPermissionItem = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.permissionEdit))
const canDeletePermissionItem = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.permissionDelete))
const canManagePermissions = computed(() => (
  canAssignRolePermissions.value ||
  canCreatePermissionItem.value ||
  canEditPermissionItem.value ||
  canDeletePermissionItem.value
))
const canOperatePermissionItems = computed(() => canEditPermissionItem.value || canDeletePermissionItem.value)
const permissionItemActionColumnWidth = computed(() => buildActionColumnWidth([[
  ...(canEditPermissionItem.value ? ['编辑'] : []),
  ...(canDeletePermissionItem.value ? ['删除'] : []),
]], {
  variant: 'link',
}))
const permissionDialogTitle = computed(() => (permissionDialogMode.value === 'create' ? '新增权限项' : '编辑权限项'))
const permissionItemTableMaxHeight = 'calc(100vh - 540px)'
const permissionSubTabOptions = Object.freeze([
  {
    name: 'ui-role-permissions',
    label: 'UI角色权限',
    code: PERMISSION_CODES.manualTestcases.permissionUiRolePermissions,
  },
  {
    name: 'permission-catalog',
    label: '权限目录',
    code: PERMISSION_CODES.manualTestcases.permissionCatalog,
  },
])
const accessiblePermissionSubTabs = computed(() => {
  const matchedTabs = permissionSubTabOptions.filter(tab => hasPermissionAccess(tab.code, userStore.hasPermissionCode))
  if (matchedTabs.length) {
    return matchedTabs
  }

  if (hasPermissionAccess(PERMISSION_CODES.manualTestcases.permissions, userStore.hasPermissionCode)) {
    return permissionSubTabOptions
  }

  return []
})

const permissionRules = {
  name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入权限编码', trigger: 'blur' }],
  item_type: [{ required: true, message: '请选择权限类型', trigger: 'change' }],
}

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

const formatPermissionType = value => {
  const matchedOption = permissionTypeOptions.find(option => option.value === value)
  return matchedOption?.label || value || '-'
}
const getPermissionItemTypeLabel = item => formatPermissionType(item?.item_type)
const getPermissionItemStatusLabel = item => (item?.is_active ? '启用' : '停用')

const resetRolePermissionSummary = () => {
  rolePermissionSummary.module = 0
  rolePermissionSummary.menu = 0
  rolePermissionSummary.button = 0
  rolePermissionSummary.action = 0
}

const applyRolePermissionSummary = summary => {
  resetRolePermissionSummary()
  if (!summary || typeof summary !== 'object') {
    return
  }

  rolePermissionSummary.module = Number(summary.module || 0)
  rolePermissionSummary.menu = Number(summary.menu || 0)
  rolePermissionSummary.button = Number(summary.button || 0)
  rolePermissionSummary.action = Number(summary.action || 0)
}

const normalizeCheckedPermissionIds = () => {
  const treeRefValue = permissionTreeRef.value
  if (!treeRefValue) {
    return []
  }

  return treeRefValue
    .getCheckedKeys(false)
    .map(item => Number(item))
    .filter(item => Number.isInteger(item) && item > 0)
}

const applyCheckedPermissionIds = async () => {
  await nextTick()
  permissionTreeRef.value?.setCheckedKeys(assignedPermissionIds.value, false)
}

const collapseAllPermissionNodes = async () => {
  await nextTick()

  const nodesMap = permissionTreeRef.value?.store?.nodesMap
  if (!nodesMap) {
    return
  }

  Object.values(nodesMap).forEach(node => {
    if (node?.level > 0) {
      node.expanded = false
    }
  })
}

const flattenPermissionTree = (nodes, depth = 0, parentPath = '') => {
  const flattenedItems = []

  ;(Array.isArray(nodes) ? nodes : []).forEach(node => {
    const nodeName = String(node?.name || '').trim()
    const currentPath = parentPath ? `${parentPath} / ${nodeName}` : nodeName
    flattenedItems.push({
      ...node,
      depth,
      optionLabel: `${'  '.repeat(depth)}[${formatPermissionType(node.item_type)}] ${nodeName}`,
      fullPath: currentPath,
    })

    if (Array.isArray(node.children) && node.children.length) {
      flattenedItems.push(...flattenPermissionTree(node.children, depth + 1, currentPath))
    }
  })

  return flattenedItems
}

const collectDescendantIds = targetId => {
  const descendantIds = new Set()

  const visit = nodes => {
    for (const node of nodes || []) {
      if (node.id === targetId) {
        collectNodeChildren(node.children, descendantIds)
        return true
      }

      if (visit(node.children)) {
        return true
      }
    }

    return false
  }

  const collectNodeChildren = (nodes, bucket) => {
    for (const node of nodes || []) {
      bucket.add(node.id)
      collectNodeChildren(node.children, bucket)
    }
  }

  visit(permissionTreeData.value)
  return descendantIds
}

const parentPermissionOptions = computed(() => {
  const flattenedItems = flattenPermissionTree(permissionTreeData.value)
  if (!permissionForm.id) {
    return flattenedItems
  }

  const blockedIds = collectDescendantIds(permissionForm.id)
  blockedIds.add(permissionForm.id)
  return flattenedItems.filter(item => !blockedIds.has(item.id))
})

const buildRoleListParams = () => {
  const params = {
    page: rolePagination.page,
    page_size: rolePagination.pageSize,
    ordering: 'name',
  }

  const keyword = String(roleFilters.keyword || '').trim()
  if (keyword) {
    params.search = keyword
  }

  return params
}

const buildPermissionListParams = () => {
  const params = {
    page: permissionPagination.page,
    page_size: permissionPagination.pageSize,
    ordering: 'sort_order,name,id',
  }

  const keyword = String(permissionFilters.keyword || '').trim()
  if (keyword) {
    params.search = keyword
  }

  if (permissionFilters.itemType) {
    params.item_type = permissionFilters.itemType
  }

  if (permissionFilters.isActive !== '' && permissionFilters.isActive !== null && permissionFilters.isActive !== undefined) {
    params.is_active = permissionFilters.isActive
  }

  return params
}
const permissionRoleColumnFilters = computed(() => ({
  id: buildTableFilters(roles.value, row => row.id, 20, compareTableNumber),
  name: buildTableFilters(roles.value, row => row.name, 20),
  member_count: buildTableFilters(roles.value, row => row.member_count, 20, compareTableNumber),
}))
const permissionItemColumnFilters = computed(() => ({
  id: buildTableFilters(permissionItems.value, row => row.id, 20, compareTableNumber),
  name: buildTableFilters(permissionItems.value, row => row.name, 20),
  item_type: buildTableFilters(permissionItems.value, getPermissionItemTypeLabel, 10),
  code: buildTableFilters(permissionItems.value, row => row.code, 20),
  parent_name: buildTableFilters(permissionItems.value, row => row.parent_name, 20),
  route_path: buildTableFilters(permissionItems.value, row => row.route_path, 20),
  status: buildTableFilters(permissionItems.value, getPermissionItemStatusLabel, 10),
  sort_order: buildTableFilters(permissionItems.value, row => row.sort_order, 20, compareTableNumber),
}))

const setCurrentRoleRow = async row => {
  await nextTick()
  roleTableRef.value?.setCurrentRow(row || null)
}

const syncSelectedRole = async preferredRoleId => {
  const nextSelectedRole =
    roles.value.find(item => item.id === preferredRoleId) ||
    roles.value[0] ||
    null

  selectedRole.value = nextSelectedRole
  selectedRoleId.value = nextSelectedRole?.id ?? null
  await setCurrentRoleRow(nextSelectedRole)
  return nextSelectedRole
}

const loadPermissionTree = async () => {
  permissionTreeLoading.value = true
  try {
    const response = await api.get(PERMISSION_ITEM_ENDPOINT, {
      params: {
        tree: 1,
        is_active: true,
      },
    })
    permissionTreeData.value = Array.isArray(response.data) ? response.data : []
    await applyCheckedPermissionIds()
    await collapseAllPermissionNodes()
  } catch (error) {
    permissionTreeData.value = []
    ElMessage.error(extractErrorMessage(error, '获取权限树失败'))
  } finally {
    permissionTreeLoading.value = false
  }
}

const loadPermissionItems = async () => {
  permissionItemLoading.value = true
  try {
    const response = await api.get(PERMISSION_ITEM_ENDPOINT, {
      params: buildPermissionListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    permissionItems.value = results
    permissionPagination.total = count
  } catch (error) {
    permissionItems.value = []
    permissionPagination.total = 0
    ElMessage.error(extractErrorMessage(error, '获取权限目录失败'))
  } finally {
    permissionItemLoading.value = false
  }
}

const loadRolePermissions = async roleId => {
  if (!roleId) {
    assignedPermissionIds.value = []
    resetRolePermissionSummary()
    await applyCheckedPermissionIds()
    await collapseAllPermissionNodes()
    return
  }

  assignmentLoading.value = true
  try {
    const response = await api.get(`${ROLE_ENDPOINT}${roleId}/permissions/`)
    assignedPermissionIds.value = Array.isArray(response.data?.permission_ids)
      ? response.data.permission_ids.map(item => Number(item)).filter(item => Number.isInteger(item) && item > 0)
      : []
    applyRolePermissionSummary(response.data?.summary)
    await applyCheckedPermissionIds()
    await collapseAllPermissionNodes()
  } catch (error) {
    assignedPermissionIds.value = []
    resetRolePermissionSummary()
    await applyCheckedPermissionIds()
    await collapseAllPermissionNodes()
    ElMessage.error(extractErrorMessage(error, '获取角色权限失败'))
  } finally {
    assignmentLoading.value = false
  }
}

const loadRoles = async ({ preserveSelection = true } = {}) => {
  roleLoading.value = true
  try {
    const response = await api.get(ROLE_ENDPOINT, {
      params: buildRoleListParams(),
    })
    const { results, count } = normalizePagedData(response.data)
    roles.value = results
    rolePagination.total = count

    const preferredRoleId = preserveSelection ? selectedRoleId.value : null
    const nextSelectedRole = await syncSelectedRole(preferredRoleId)

    if (nextSelectedRole) {
      await loadRolePermissions(nextSelectedRole.id)
    } else {
      assignedPermissionIds.value = []
      resetRolePermissionSummary()
      await applyCheckedPermissionIds()
      await collapseAllPermissionNodes()
    }
  } catch (error) {
    roles.value = []
    selectedRole.value = null
    selectedRoleId.value = null
    rolePagination.total = 0
    assignedPermissionIds.value = []
    resetRolePermissionSummary()
    await applyCheckedPermissionIds()
    await collapseAllPermissionNodes()
    ElMessage.error(extractErrorMessage(error, '获取角色列表失败'))
  } finally {
    roleLoading.value = false
  }
}

const refreshRolePermissions = async () => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
    return
  }

  await loadRolePermissions(selectedRoleId.value)
}

const handleRoleRowClick = async row => {
  if (!row || row.id === selectedRoleId.value) {
    return
  }

  selectedRole.value = row
  selectedRoleId.value = row.id
  await setCurrentRoleRow(row)
  await loadRolePermissions(row.id)
}

const handleRoleSearch = async () => {
  rolePagination.page = 1
  await loadRoles({ preserveSelection: false })
}

const handleRoleReset = async () => {
  roleFilters.keyword = ''
  rolePagination.page = 1
  rolePagination.pageSize = 20
  await loadRoles({ preserveSelection: false })
}

const handleRolePageSizeChange = async () => {
  rolePagination.page = 1
  await loadRoles({ preserveSelection: true })
}

const checkAllPermissions = async () => {
  if (!selectedRole.value) {
    ElMessage.warning('请先选择角色')
    return
  }

  await nextTick()
  permissionTreeRef.value?.setCheckedNodes(permissionTreeData.value)
}

const clearAllPermissions = async () => {
  if (!selectedRole.value) {
    ElMessage.warning('请先选择角色')
    return
  }

  await nextTick()
  permissionTreeRef.value?.setCheckedKeys([], false)
}

const saveRolePermissions = async () => {
  if (!selectedRoleId.value) {
    ElMessage.warning('请先选择角色')
    return
  }
  if (!canAssignRolePermissions.value) {
    ElMessage.warning('当前账号没有角色权限管理权限')
    return
  }

  assignmentSaving.value = true
  try {
    const response = await api.put(`${ROLE_ENDPOINT}${selectedRoleId.value}/permissions/`, {
      permission_ids: normalizeCheckedPermissionIds(),
    })

    assignedPermissionIds.value = Array.isArray(response.data?.permission_ids) ? response.data.permission_ids : []
    applyRolePermissionSummary(response.data?.summary)
    await applyCheckedPermissionIds()
    ElMessage.success('角色权限已更新')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存角色权限失败'))
  } finally {
    assignmentSaving.value = false
  }
}

const resetPermissionForm = () => {
  Object.assign(permissionForm, createDefaultPermissionForm())
}

const handlePermissionDialogClosed = () => {
  resetPermissionForm()
  permissionFormRef.value?.clearValidate()
}

const openCreatePermissionDialog = () => {
  if (!canCreatePermissionItem.value) {
    ElMessage.warning('当前账号没有权限目录管理权限')
    return
  }

  permissionDialogMode.value = 'create'
  resetPermissionForm()
  permissionDialogVisible.value = true
  nextTick(() => {
    permissionFormRef.value?.clearValidate()
  })
}

const openEditPermissionDialog = row => {
  if (!canEditPermissionItem.value) {
    ElMessage.warning('当前账号没有权限目录管理权限')
    return
  }

  permissionDialogMode.value = 'edit'
  Object.assign(permissionForm, {
    id: row.id,
    name: row.name || '',
    code: row.code || '',
    item_type: row.item_type || 'menu',
    parent: row.parent || null,
    route_path: row.route_path || '',
    sort_order: Number(row.sort_order || 0),
    is_active: Boolean(row.is_active),
    description: row.description || '',
  })
  permissionDialogVisible.value = true
  nextTick(() => {
    permissionFormRef.value?.clearValidate()
  })
}

const submitPermissionForm = async () => {
  if (permissionDialogMode.value === 'create' && !canCreatePermissionItem.value) {
    ElMessage.warning('当前账号没有新增权限项权限')
    return
  }

  if (permissionDialogMode.value === 'edit' && !canEditPermissionItem.value) {
    ElMessage.warning('当前账号没有编辑权限项权限')
    return
  }

  try {
    await permissionFormRef.value?.validate()
  } catch {
    return
  }

  permissionSaving.value = true
  try {
    const payload = {
      name: String(permissionForm.name || '').trim(),
      code: String(permissionForm.code || '').trim(),
      item_type: permissionForm.item_type,
      parent: permissionForm.item_type === 'module' ? null : permissionForm.parent,
      route_path: String(permissionForm.route_path || '').trim(),
      sort_order: Number(permissionForm.sort_order || 0),
      is_active: Boolean(permissionForm.is_active),
      description: String(permissionForm.description || '').trim(),
    }

    if (permissionDialogMode.value === 'create') {
      await api.post(PERMISSION_ITEM_ENDPOINT, payload)
      ElMessage.success('权限项已创建')
    } else {
      await api.patch(`${PERMISSION_ITEM_ENDPOINT}${permissionForm.id}/`, payload)
      ElMessage.success('权限项已更新')
    }

    permissionDialogVisible.value = false
    await Promise.all([loadPermissionTree(), loadPermissionItems()])
    if (selectedRoleId.value) {
      await loadRolePermissions(selectedRoleId.value)
    }
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '保存权限项失败'))
  } finally {
    permissionSaving.value = false
  }
}

const handleDeletePermissionItem = async row => {
  if (!canDeletePermissionItem.value) {
    ElMessage.warning('当前账号没有删除权限项权限')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除权限项“${row.name}”吗？删除后其下级权限和角色授权关系也会一并移除。`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${PERMISSION_ITEM_ENDPOINT}${row.id}/`)
    ElMessage.success('权限项已删除')
    await Promise.all([loadPermissionTree(), loadPermissionItems()])
    if (selectedRoleId.value) {
      await loadRolePermissions(selectedRoleId.value)
    }
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(extractErrorMessage(error, '删除权限项失败'))
    }
  }
}

const handlePermissionSearch = async () => {
  permissionPagination.page = 1
  await loadPermissionItems()
}

const handlePermissionReset = async () => {
  permissionFilters.keyword = ''
  permissionFilters.itemType = ''
  permissionFilters.isActive = ''
  permissionPagination.page = 1
  permissionPagination.pageSize = 20
  await loadPermissionItems()
}

const handlePermissionPageSizeChange = async () => {
  permissionPagination.page = 1
  await loadPermissionItems()
}

watch(
  () => permissionForm.item_type,
  itemType => {
    if (itemType === 'module') {
      permissionForm.parent = null
    }
  }
)

watch(
  () => props.active,
  async active => {
    if (active) {
      await Promise.all([loadPermissionTree(), loadPermissionItems(), loadRoles({ preserveSelection: true })])
    }
  }
)

watch(
  activePermissionSubTab,
  async tab => {
    if (tab === 'ui-role-permissions') {
      await collapseAllPermissionNodes()
    }
  }
)

watch(
  accessiblePermissionSubTabs,
  tabs => {
    if (tabs.some(tab => tab.name === activePermissionSubTab.value)) {
      return
    }

    activePermissionSubTab.value = tabs[0]?.name || 'ui-role-permissions'
  },
  { immediate: true }
)

onMounted(async () => {
  if (props.active) {
    await Promise.all([loadPermissionTree(), loadPermissionItems(), loadRoles({ preserveSelection: true })])
  }
})
</script>

<style scoped lang="scss">
.permission-management-panel {
  flex: 1;
  height: calc(var(--workspace-embed-scroll-height) - 36px);
  min-height: calc(var(--workspace-embed-scroll-height) - 36px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.permission-sub-tabs {
  flex-shrink: 0;
}

:deep(.permission-sub-tabs .el-tabs__header) {
  margin: 0;
}

:deep(.permission-sub-tabs .el-tabs__content) {
  display: none;
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

.permission-search-form {
  width: 100%;
}

:deep(.role-search-form .el-form-item),
:deep(.permission-search-form .el-form-item) {
  margin-bottom: 0;
}

.toolbar-actions,
.section-actions,
.row-actions,
.dialog-footer,
.summary-tags {
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
  grid-template-columns: minmax(320px, 0.9fr) minmax(680px, 1.6fr);
  gap: 16px;
  flex: 1 1 0;
  align-items: stretch;
}

.permission-right-column {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(320px, 1fr) minmax(340px, 1.1fr);
  gap: 16px;
}

.permission-right-column--single {
  grid-template-rows: minmax(320px, 1fr);
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
.permission-item-table {
  width: 100%;
}

.permission-catalog-panel {
  flex: 1;
}

.tab-pagination {
  margin-top: auto;
  justify-content: flex-end;
}

.permission-role-panel,
.permission-assignment-panel {
  height: 100%;
}

.tree-empty-state {
  margin: auto 0;
}

.summary-tags {
  flex-wrap: wrap;
}

.permission-role-panel {
  overflow: hidden;
}

.permission-role-panel .section-header {
  flex-shrink: 0;
}

.permission-role-table-wrapper {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
}

.permission-role-table-wrapper :deep(.el-table) {
  flex: 1;
}

.permission-role-table-wrapper :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.permission-tree-wrapper {
  flex: 1 1 0;
  height: 0;
  min-height: 0;
  overflow-x: auto;
  overflow-y: auto;
  padding: 4px 2px 4px 0;
}

.permission-assignment-panel {
  overflow: hidden;
}

.permission-assignment-panel .section-header,
.permission-assignment-panel .summary-tags {
  flex-shrink: 0;
}

.permission-tree-wrapper--table {
  display: flex;
  flex-direction: column;
  padding: 0;
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 16px;
  background: #fff;
}

.permission-tree-table__header {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 2;
  border-bottom: 1px solid rgba(15, 55, 82, 0.08);
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fb 100%);
  padding: 10px 16px 10px 58px;
}

.permission-tree-table__header-content {
  min-width: 680px;
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) minmax(140px, 0.8fr) minmax(220px, 1.1fr);
  gap: 16px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.permission-tree {
  min-height: 100%;
}

.permission-tree--table {
  flex: 1 0 auto;
  min-width: 680px;
  padding: 8px 0;
}

.permission-tree--table :deep(.el-tree-node__content) {
  min-height: 44px;
  padding-right: 16px;
}

.permission-tree-node {
  min-width: 0;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) minmax(140px, 0.8fr) minmax(220px, 1.1fr);
  gap: 8px;
  align-items: center;
  padding: 4px 0;
}

.permission-tree-node__cell {
  min-width: 0;
}

.permission-tree-node__cell--name {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.permission-tree-node__cell--tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.permission-tree-node__name {
  font-weight: 500;
  color: #1f2937;
}

.permission-tree-node__code,
.permission-tree-node__path {
  font-size: 12px;
  color: #6b7280;
}

.permission-tree-node__path {
  word-break: break-all;
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

.dialog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

@media (max-width: 1240px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .permission-right-column {
    grid-template-rows: auto auto;
  }

  .permission-right-column--single {
    grid-template-rows: auto;
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
  .role-search-form :deep(.el-input),
  .permission-search-form :deep(.el-input),
  .permission-search-form :deep(.el-select) {
    width: 100%;
  }

  .dialog-grid {
    grid-template-columns: 1fr;
  }

  .tab-pagination {
    justify-content: center;
  }

  .permission-tree-table__header {
    padding-left: 52px;
  }

  .permission-tree-table__header-content,
  .permission-tree-node {
    min-width: 560px;
    grid-template-columns: minmax(180px, 1.4fr) minmax(130px, 0.9fr) minmax(180px, 1.2fr);
  }

  .permission-tree--table {
    min-width: 560px;
  }
}
</style>


