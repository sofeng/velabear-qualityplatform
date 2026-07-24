<template>
  <div class="version-management-panel">
    <div class="tab-toolbar">
      <el-form :inline="true" :model="filters" class="search-form version-search-form" @submit.prevent>
        <el-form-item label="项目">
          <el-select
            :model-value="normalizedCurrentProjectId || undefined"
            placeholder="请选择项目"
            style="width: 220px"
            @change="handleProjectChange"
          >
            <el-option
              v-for="project in workspaceProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="版本">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="请输入版本名称或描述"
            style="width: 280px"
            @keyup.enter="handleFilterChange"
            @clear="handleFilterChange"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="filters.type"
            placeholder="全部类型"
            clearable
            style="width: 160px"
            @change="handleFilterChange"
          >
            <el-option label="基线版本" value="baseline" />
            <el-option label="普通版本" value="normal" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilterChange">
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
          :table-ref="versionTableRef"
          storage-key="manual-testcases.versions"
        />
        <el-tag effect="plain">当前项目 {{ currentProjectName || '-' }}</el-tag>
        <el-tag effect="plain" type="success">当前版本 {{ currentVersionLabel }}</el-tag>
        <el-button :loading="loading" @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button :disabled="normalizedCurrentVersionId === 'all'" @click="selectAllVersions">切换为全部版本</el-button>
        <el-button
          type="primary"
          :disabled="!canCreateVersion || !normalizedCurrentProjectId"
          @click="$emit('create-version')"
        >
          <el-icon><Plus /></el-icon>
          新增版本
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!normalizedCurrentProjectId"
      title="请先选择项目后管理版本。这里选择的项目与版本会同步到左侧版本号和后续目录树上下文。"
      type="info"
      :closable="false"
      class="context-alert"
    />

    <el-empty
      v-else-if="!visibleVersions.length && !loading"
      description="当前项目暂无版本数据"
      class="version-empty-state"
    />

    <el-table
      v-else
      ref="versionTableRef"
      v-loading="loading"
      :data="visibleVersions"
      row-key="id"
      stripe
      highlight-current-row
      class="version-table"
      :max-height="versionTableMaxHeight"
      style="width: 100%"
      empty-text="暂无版本数据"
      @row-click="handleRowClick"
    >
      <el-table-column label="版本名称" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="version-name-cell">
            <span>{{ row.name || '-' }}</span>
            <el-tag v-if="isCurrentVersion(row)" size="small" type="success">当前版本</el-tag>
            <el-tag v-if="row.is_default" size="small" type="success" effect="plain">默认</el-tag>
            <el-tag v-if="row.is_baseline" size="small" type="warning" effect="plain">基线</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="关联项目" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ formatProjects(row.projects) }}</template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column label="测试用例数" width="110" align="center">
        <template #default="{ row }">{{ row.testcases_count || 0 }}</template>
      </el-table-column>
      <el-table-column label="创建人" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ getCreatedByName(row.created_by) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" :width="versionActionColumnWidth" fixed="right">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button
              link
              type="primary"
              :disabled="isCurrentVersion(row)"
              @click.stop="selectVersion(row)"
            >
              {{ isCurrentVersion(row) ? '当前版本' : '切换当前' }}
            </el-button>
            <el-button
              v-if="canSetDefaultVersion && !row.is_default"
              link
              type="warning"
              @click.stop="$emit('set-default-version', row)"
            >
              设为默认
            </el-button>
            <el-button v-if="canEditVersion" link type="primary" @click.stop="$emit('edit-version', row)">编辑</el-button>
            <el-button v-if="canDeleteVersion" link type="danger" @click.stop="$emit('delete-version', row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'
import { PERMISSION_CODES } from '@/utils/permissions'
import { getUserDisplayName } from '@/utils/userDisplay'
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
  currentVersionId: {
    type: [Number, String],
    default: 'all',
  },
  workspaceProjects: {
    type: Array,
    default: () => [],
  },
  versions: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'refresh',
  'create-version',
  'edit-version',
  'delete-version',
  'set-default-version',
  'switch-project',
  'select-version',
])

const userStore = useUserStore()

const versionTableRef = ref(null)

const filters = reactive({
  keyword: '',
  type: '',
})

const normalizedCurrentProjectId = computed(() => {
  const parsedValue = Number(props.currentProjectId)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : null
})

const normalizedCurrentVersionId = computed(() => {
  if (props.currentVersionId === 'all') {
    return 'all'
  }

  const parsedValue = Number(props.currentVersionId)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : 'all'
})

const canCreateVersion = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.versionCreate))
const canEditVersion = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.versionEdit))
const canDeleteVersion = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.versionDelete))
const canSetDefaultVersion = computed(() => userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.versionSetDefault))
const versionActionColumnWidth = computed(() => buildActionColumnWidth([[
  '切换当前',
  ...(canSetDefaultVersion.value ? ['设为默认'] : []),
  ...(canEditVersion.value ? ['编辑'] : []),
  ...(canDeleteVersion.value ? ['删除'] : []),
]], {
  variant: 'link',
}))
const versionTableMaxHeight = 'calc(100vh - 340px)'

const currentProjectName = computed(() => {
  const matchedProject = props.workspaceProjects.find(item => Number(item?.id) === normalizedCurrentProjectId.value)
  return matchedProject?.name || ''
})

const currentVersionLabel = computed(() => {
  if (normalizedCurrentVersionId.value === 'all') {
    return '全部版本'
  }

  const matchedVersion = props.versions.find(item => Number(item?.id) === normalizedCurrentVersionId.value)
  return matchedVersion?.name || '-'
})

const visibleVersions = computed(() => {
  const keyword = String(filters.keyword || '').trim().toLowerCase()

  return props.versions.filter(version => {
    if (filters.type === 'baseline' && !version?.is_baseline) {
      return false
    }

    if (filters.type === 'normal' && version?.is_baseline) {
      return false
    }

    if (!keyword) {
      return true
    }

    const searchableText = [
      version?.name,
      version?.description,
      formatProjects(version?.projects),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return searchableText.includes(keyword)
  })
})

const isCurrentVersion = version => Number(version?.id) === normalizedCurrentVersionId.value

const syncCurrentVersionRow = async () => {
  await nextTick()

  if (normalizedCurrentVersionId.value === 'all') {
    versionTableRef.value?.setCurrentRow(null)
    return
  }

  const currentVersion = visibleVersions.value.find(item => isCurrentVersion(item)) || null
  versionTableRef.value?.setCurrentRow(currentVersion)
}

const formatProjects = projects => {
  const normalizedProjects = Array.isArray(projects) ? projects : []
  if (!normalizedProjects.length) {
    return '-'
  }

  return normalizedProjects
    .map(project => String(project?.name || '').trim())
    .filter(Boolean)
    .join('、') || '-'
}

const getCreatedByName = createdBy => getUserDisplayName(createdBy, createdBy?.username || '-') || '-'

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

const handleProjectChange = value => {
  emit('switch-project', value)
}

const handleFilterChange = async () => {
  await syncCurrentVersionRow()
}

const handleReset = async () => {
  filters.keyword = ''
  filters.type = ''
  await syncCurrentVersionRow()
}

const selectAllVersions = () => {
  emit('select-version', null)
}

const selectVersion = version => {
  if (!version || isCurrentVersion(version)) {
    return
  }

  emit('select-version', version.id)
}

const handleRowClick = row => {
  selectVersion(row)
}

watch(
  () => [props.active, props.currentVersionId, props.versions.length, filters.keyword, filters.type],
  async ([active]) => {
    if (!active) {
      return
    }

    await syncCurrentVersionRow()
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.version-management-panel {
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

.version-search-form {
  min-width: min(100%, 760px);
}

:deep(.version-search-form .el-form-item) {
  margin-bottom: 0;
}

.toolbar-actions,
.version-name-cell,
.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions {
  flex-wrap: wrap;
  margin-left: auto;
}

.context-alert {
  margin-bottom: 4px;
}

.version-empty-state {
  margin: auto 0;
}

.version-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.version-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.version-name-cell {
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

@media (max-width: 768px) {
  .tab-toolbar,
  .toolbar-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .version-search-form,
  .version-search-form :deep(.el-input),
  .version-search-form :deep(.el-select) {
    width: 100%;
  }
}
</style>
