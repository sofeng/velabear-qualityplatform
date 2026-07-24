<template>
  <section class="knowledge-repository-panel">
    <header class="knowledge-repository-panel__header">
      <div>
        <h2>代码仓库</h2>
        <span>为知识库对象配置代码事实源、授权方式、索引目录和 roadmap 生成范围</span>
      </div>
      <div class="knowledge-repository-panel__actions">
        <el-button :loading="loading" @click="loadData">刷新</el-button>
        <el-button :loading="seedLoading" @click="handleSeedCurrentPlatform">使用本平台仓库</el-button>
        <el-button type="primary" @click="openCreateDialog">新增仓库配置</el-button>
      </div>
    </header>

    <section class="knowledge-repository-panel__summary">
      <div>
        <span>仓库配置</span>
        <strong>{{ repositories.length }}</strong>
      </div>
      <div>
        <span>知识空间</span>
        <strong>{{ spaces.length }}</strong>
      </div>
      <div>
        <span>索引任务</span>
        <strong>{{ indexRuns.length }}</strong>
      </div>
      <div>
        <span>最近状态</span>
        <strong>{{ latestRun?.status || '-' }}</strong>
      </div>
    </section>

    <section v-if="currentSpace" class="knowledge-repository-panel__status">
      <div>
        <strong>{{ currentSpace.name }}</strong>
        <span>{{ currentSpace.build_status_message || '项目知识库对象已创建，完成仓库和数据库配置后会自动生成 roadmap、组织结构图和关系图。' }}</span>
      </div>
      <el-tag :type="getBuildStatusType(currentSpace.build_status)" effect="plain">
        {{ getBuildStatusLabel(currentSpace.build_status) }}
      </el-tag>
    </section>

    <el-table
      v-loading="loading"
      :data="repositories"
      class="knowledge-repository-panel__table"
      height="360"
      border
    >
      <el-table-column prop="name" label="名称" min-width="180" fixed="left" />
      <el-table-column prop="project_name" label="项目" min-width="120" />
      <el-table-column label="仓库类型" width="120">
        <template #default="{ row }">{{ getProviderLabel(row.provider) }}</template>
      </el-table-column>
      <el-table-column label="连接方式" width="120">
        <template #default="{ row }">{{ getAuthModeLabel(row.auth_mode) }}</template>
      </el-table-column>
      <el-table-column label="仓库地址/路径" min-width="260">
        <template #default="{ row }">
          <span class="repository-location">{{ row.repository_location || row.repository_url || row.local_path || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="default_branch" label="分支" width="110" />
      <el-table-column label="Schema" width="110">
        <template #default="{ row }">{{ getDatabaseEngineLabel(row.database_engine) }}</template>
      </el-table-column>
      <el-table-column label="授权" width="110">
        <template #default="{ row }">
          <el-tag :type="getAuthorizationStatusType(row.authorization_status)" effect="plain">
            {{ getAuthorizationStatusLabel(row.authorization_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近索引" width="180">
        <template #default="{ row }">{{ formatTime(row.last_indexed_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="310" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="primary" :loading="actionLoadingKey === `auth:${row.id}`" @click="handleAuthorize(row)">授权</el-button>
          <el-button link type="primary" :loading="actionLoadingKey === `test:${row.id}`" @click="handleTestConnection(row)">测试</el-button>
          <el-button link type="primary" :loading="actionLoadingKey === `schema:${row.id}`" @click="handleTestDatabaseSchema(row)">测Schema</el-button>
          <el-button link type="primary" :loading="actionLoadingKey === `index:${row.id}`" @click="handleIndex(row)">索引</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <section class="knowledge-repository-panel__runs">
      <header>
        <h3>索引记录</h3>
        <span>索引完成后会生成 knowledge_objects 和 knowledge_relations，供知识库助手问答和右侧双链图谱使用</span>
      </header>
      <el-table :data="indexRuns" height="220" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="repository_config_name" label="仓库" min-width="180" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getRunStatusType(row.status)" effect="plain">{{ getRunStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="object_count" label="对象" width="90" />
        <el-table-column prop="relation_count" label="关系" width="90" />
        <el-table-column prop="index_ref" label="分支/Ref" width="120" />
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" width="180">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增仓库配置' : '编辑仓库配置'"
      width="760px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="128px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="例如：思源质量源码仓库" />
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="formData.project" clearable filterable placeholder="选择知识库对象所属项目" style="width: 100%">
            <el-option
              v-for="project in workspaceProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="仓库类型" prop="provider">
          <el-radio-group v-model="formData.provider">
            <el-radio-button
              v-for="option in providerOptions"
              :key="option.value"
              :label="option.value"
            >
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="仓库模式" prop="repository_mode">
          <el-radio-group v-model="formData.repository_mode">
            <el-radio-button label="local_path">本地路径</el-radio-button>
            <el-radio-button label="remote">远程仓库</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="formData.repository_mode === 'remote'" label="仓库地址" prop="repository_url">
          <el-input v-model="formData.repository_url" placeholder="https://github.com/org/repo.git" />
        </el-form-item>
        <el-form-item v-else label="本地路径" prop="local_path">
          <el-input v-model="formData.local_path" placeholder="D:/AI/syswin-testhub/testhub-platform-src 或 /workspace/source-repo" />
        </el-form-item>
        <el-form-item label="连接方式" prop="auth_mode">
          <el-select v-model="formData.auth_mode" style="width: 100%">
            <el-option
              v-for="option in authModeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="['token', 'oauth', 'github_app'].includes(formData.auth_mode)" label="用户名">
          <el-input v-model="formData.username" placeholder="Git/GitHub 用户名，可选" />
        </el-form-item>
        <el-form-item v-if="['token', 'oauth', 'github_app'].includes(formData.auth_mode)" label="Token">
          <el-input v-model="formData.access_token" type="password" show-password placeholder="留空表示不修改已有 Token" />
        </el-form-item>
        <el-form-item v-if="formData.auth_mode === 'ssh'" label="SSH Key">
          <el-input v-model="formData.ssh_key" type="textarea" :rows="4" placeholder="留空表示不修改已有 SSH Key" />
        </el-form-item>
        <el-form-item label="默认分支" prop="default_branch">
          <el-input v-model="formData.default_branch" placeholder="main" />
        </el-form-item>
        <div class="knowledge-repository-form-grid">
          <el-form-item label="代码根目录">
            <el-input v-model="formData.code_root" placeholder="." />
          </el-form-item>
          <el-form-item label="前端目录">
            <el-input v-model="formData.frontend_root" placeholder="frontend" />
          </el-form-item>
          <el-form-item label="后端目录">
            <el-input v-model="formData.backend_root" placeholder="apps" />
          </el-form-item>
          <el-form-item label="文档目录">
            <el-input v-model="formData.docs_root" placeholder="docs" />
          </el-form-item>
        </div>
        <el-divider content-position="left">数据库 Schema 建模</el-divider>
        <div class="knowledge-repository-form-grid">
          <el-form-item label="Schema来源">
            <el-select v-model="formData.database_engine" style="width: 100%">
              <el-option label="不读取数据库" value="none" />
              <el-option label="当前平台数据库" value="current" />
              <el-option label="外部 MySQL" value="mysql" />
            </el-select>
          </el-form-item>
          <el-form-item label="自动建模">
            <el-switch
              v-model="formData.auto_index_on_ready"
              active-text="配置就绪后自动生成"
              inactive-text="仅手动生成"
            />
          </el-form-item>
          <template v-if="formData.database_engine === 'mysql'">
            <el-form-item label="数据库主机">
              <el-input v-model="formData.database_host" placeholder="127.0.0.1" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="formData.database_port" placeholder="3306" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="formData.database_name" placeholder="schema name" />
            </el-form-item>
            <el-form-item label="只读用户名">
              <el-input v-model="formData.database_username" placeholder="readonly_user" />
            </el-form-item>
            <el-form-item label="只读密码">
              <el-input v-model="formData.database_password" type="password" show-password placeholder="留空表示不修改已有密码" />
            </el-form-item>
            <el-form-item label="Schema名">
              <el-input v-model="formData.database_schema" placeholder="默认同数据库名" />
            </el-form-item>
          </template>
          <el-form-item label="表白名单">
            <el-input v-model="formData.database_include_patterns_text" placeholder="一行一个表名或通配符，如 defects*" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="表黑名单">
            <el-input v-model="formData.database_exclude_patterns_text" placeholder="一行一个表名或通配符，如 *_history" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="样例数据">
            <el-switch
              v-model="formData.allow_sample_data"
              active-text="允许少量样例"
              inactive-text="仅读取Schema"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  authorizeKnowledgeRepository,
  createKnowledgeRepositoryConfig,
  deleteKnowledgeRepositoryConfig,
  getKnowledgeAuthModeChoices,
  getKnowledgeIndexRuns,
  getKnowledgeProviderChoices,
  getKnowledgeRepositoryConfigs,
  getKnowledgeSpaces,
  indexKnowledgeRepository,
  seedCurrentPlatformKnowledgeRepository,
  testKnowledgeRepositoryConnection,
  testKnowledgeRepositoryDatabaseSchema,
  updateKnowledgeRepositoryConfig,
} from '@/api/knowledge'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  currentProjectId: {
    type: [String, Number],
    default: '',
  },
  workspaceProjects: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['indexed'])

const providerOptions = getKnowledgeProviderChoices()
const authModeOptions = getKnowledgeAuthModeChoices()
const repositories = ref([])
const indexRuns = ref([])
const spaces = ref([])
const loading = ref(false)
const saving = ref(false)
const seedLoading = ref(false)
const actionLoadingKey = ref('')
const dialogVisible = ref(false)
const dialogMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)

const createDefaultForm = () => ({
  name: '',
  project: props.currentProjectId || null,
  provider: 'local',
  repository_mode: 'local_path',
  auth_mode: 'none',
  repository_url: '',
  local_path: '',
  username: '',
  access_token: '',
  ssh_key: '',
  default_branch: 'main',
  code_root: '.',
  frontend_root: 'frontend',
  backend_root: 'apps',
  docs_root: 'docs',
  database_engine: 'none',
  database_host: '',
  database_port: '3306',
  database_name: '',
  database_schema: '',
  database_username: '',
  database_password: '',
  database_include_patterns_text: '',
  database_exclude_patterns_text: '',
  allow_sample_data: false,
  auto_index_on_ready: true,
})

const formData = reactive(createDefaultForm())

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择仓库类型', trigger: 'change' }],
  repository_mode: [{ required: true, message: '请选择仓库模式', trigger: 'change' }],
  repository_url: [{
    validator: (_rule, value, callback) => {
      if (formData.repository_mode === 'remote' && !String(value || '').trim()) {
        callback(new Error('请输入仓库地址'))
        return
      }
      callback()
    },
    trigger: 'blur',
  }],
  local_path: [{
    validator: (_rule, value, callback) => {
      if (formData.repository_mode === 'local_path' && !String(value || '').trim()) {
        callback(new Error('请输入本地路径'))
        return
      }
      callback()
    },
    trigger: 'blur',
  }],
  default_branch: [{ required: true, message: '请输入默认分支', trigger: 'blur' }],
}

const latestRun = computed(() => indexRuns.value[0] || null)
const currentSpace = computed(() => {
  if (!spaces.value.length) {
    return null
  }
  if (!props.currentProjectId) {
    return spaces.value[0] || null
  }
  return spaces.value.find(item => String(item.project || '') === String(props.currentProjectId)) || spaces.value[0] || null
})

const parsePatternText = value => String(value || '')
  .split(/\r?\n|,/)
  .map(item => item.trim())
  .filter(Boolean)

const formatPatternText = value => (Array.isArray(value) ? value.join('\n') : '')

const resetForm = next => {
  Object.assign(formData, createDefaultForm(), next || {})
}

const loadData = async () => {
  loading.value = true
  try {
    const [repositoryResponse, runResponse, spaceResponse] = await Promise.all([
      getKnowledgeRepositoryConfigs({ page_size: 200, ordering: '-updated_at' }),
      getKnowledgeIndexRuns({ page_size: 50, ordering: '-started_at' }),
      getKnowledgeSpaces({ page_size: 200 }),
    ])
    repositories.value = repositoryResponse.data.results || repositoryResponse.data || []
    indexRuns.value = runResponse.data.results || runResponse.data || []
    spaces.value = spaceResponse.data.results || spaceResponse.data || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '加载仓库配置失败')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = row => {
  dialogMode.value = 'edit'
  editingId.value = row.id
  resetForm({
    name: row.name || '',
    project: row.project || props.currentProjectId || null,
    provider: row.provider || 'local',
    repository_mode: row.repository_mode || 'local_path',
    auth_mode: row.auth_mode || 'none',
    repository_url: row.repository_url || '',
    local_path: row.local_path || '',
    username: row.username || '',
    access_token: '',
    ssh_key: '',
    default_branch: row.default_branch || 'main',
    code_root: row.code_root || '.',
    frontend_root: row.frontend_root || 'frontend',
    backend_root: row.backend_root || 'apps',
    docs_root: row.docs_root || 'docs',
    database_engine: row.database_engine || 'none',
    database_host: row.database_host || '',
    database_port: row.database_port || '3306',
    database_name: row.database_name || '',
    database_schema: row.database_schema || '',
    database_username: row.database_username || '',
    database_password: '',
    database_include_patterns_text: formatPatternText(row.database_include_patterns),
    database_exclude_patterns_text: formatPatternText(row.database_exclude_patterns),
    allow_sample_data: Boolean(row.allow_sample_data),
    auto_index_on_ready: row.auto_index_on_ready !== false,
  })
  dialogVisible.value = true
}

const buildSavePayload = () => {
  const payload = {
    name: formData.name,
    project: formData.project || null,
    provider: formData.provider,
    repository_mode: formData.repository_mode,
    auth_mode: formData.auth_mode,
    repository_url: formData.repository_mode === 'remote' ? formData.repository_url : '',
    local_path: formData.repository_mode === 'local_path' ? formData.local_path : '',
    username: formData.username,
    default_branch: formData.default_branch || 'main',
    code_root: formData.code_root || '.',
    frontend_root: formData.frontend_root || 'frontend',
    backend_root: formData.backend_root || 'apps',
    docs_root: formData.docs_root || 'docs',
    database_engine: formData.database_engine || 'none',
    database_host: formData.database_engine === 'mysql' ? formData.database_host : '',
    database_port: formData.database_engine === 'mysql' ? formData.database_port || '3306' : '',
    database_name: formData.database_engine === 'mysql' ? formData.database_name : '',
    database_schema: formData.database_engine === 'mysql' ? formData.database_schema : '',
    database_username: formData.database_engine === 'mysql' ? formData.database_username : '',
    database_include_patterns: parsePatternText(formData.database_include_patterns_text),
    database_exclude_patterns: parsePatternText(formData.database_exclude_patterns_text),
    allow_sample_data: Boolean(formData.allow_sample_data),
    auto_index_on_ready: Boolean(formData.auto_index_on_ready),
  }
  if (formData.access_token) {
    payload.access_token = formData.access_token
  }
  if (formData.ssh_key) {
    payload.ssh_key = formData.ssh_key
  }
  if (formData.database_password) {
    payload.database_password = formData.database_password
  }
  return payload
}

const handleSave = async () => {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await createKnowledgeRepositoryConfig(buildSavePayload())
      ElMessage.success('仓库配置已创建')
    } else {
      await updateKnowledgeRepositoryConfig(editingId.value, buildSavePayload())
      ElMessage.success('仓库配置已更新')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '保存仓库配置失败')
  } finally {
    saving.value = false
  }
}

const handleSeedCurrentPlatform = async () => {
  seedLoading.value = true
  try {
    const response = await seedCurrentPlatformKnowledgeRepository({ project: props.currentProjectId || null })
    ElMessage.success(response.data.created ? '已创建本平台仓库配置' : '已更新本平台仓库配置')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '创建本平台仓库配置失败')
  } finally {
    seedLoading.value = false
  }
}

const handleAuthorize = async row => {
  actionLoadingKey.value = `auth:${row.id}`
  try {
    const response = await authorizeKnowledgeRepository(row.id)
    const url = response.data.authorization_url
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer,width=860,height=720')
      ElMessage.success('已打开授权页面，请在弹窗中点击授权')
    } else {
      ElMessage.warning(response.data.message || '未返回授权页面地址')
    }
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '发起授权失败')
  } finally {
    actionLoadingKey.value = ''
  }
}

const handleTestConnection = async row => {
  actionLoadingKey.value = `test:${row.id}`
  try {
    const response = await testKnowledgeRepositoryConnection(row.id)
    ElMessage.success(response.data.message || '连接测试成功')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.detail || '连接测试失败')
  } finally {
    actionLoadingKey.value = ''
  }
}

const handleTestDatabaseSchema = async row => {
  actionLoadingKey.value = `schema:${row.id}`
  try {
    const response = await testKnowledgeRepositoryDatabaseSchema(row.id)
    ElMessage.success(response.data.message || '数据库 Schema 测试成功')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.detail || '数据库 Schema 测试失败')
  } finally {
    actionLoadingKey.value = ''
  }
}

const handleIndex = async row => {
  actionLoadingKey.value = `index:${row.id}`
  try {
    const response = await indexKnowledgeRepository(row.id)
    if (response.data?.queued) {
      ElMessage.success('索引任务已提交，完成后会自动生成 roadmap、组织结构图和关系图')
    } else {
      ElMessage.success(`索引完成：${response.data.object_count || 0} 个对象，${response.data.relation_count || 0} 条关系`)
    }
    emit('indexed', response.data)
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.response?.data?.error || '索引失败')
    await loadData()
  } finally {
    actionLoadingKey.value = ''
  }
}

const handleDelete = async row => {
  await ElMessageBox.confirm(`确定删除仓库配置「${row.name}」？`, '删除确认', {
    type: 'warning',
  })
  await deleteKnowledgeRepositoryConfig(row.id)
  ElMessage.success('仓库配置已删除')
  await loadData()
}

const getProviderLabel = value => providerOptions.find(item => item.value === value)?.label || value || '-'
const getAuthModeLabel = value => authModeOptions.find(item => item.value === value)?.label || value || '-'
const getDatabaseEngineLabel = value => ({
  none: '不读取',
  current: '当前库',
  mysql: 'MySQL',
}[value] || value || '-')

const getBuildStatusLabel = value => ({
  pending_config: '待配置',
  ready: '已就绪',
  queued: '排队中',
  indexing: '建模中',
  indexed: '已建模',
  stale: '需刷新',
  failed: '失败',
}[value] || value || '-')

const getBuildStatusType = value => ({
  ready: 'success',
  indexed: 'success',
  queued: 'warning',
  indexing: 'warning',
  stale: 'warning',
  failed: 'danger',
}[value] || 'info')

const getAuthorizationStatusLabel = value => ({
  not_configured: '未配置',
  pending: '待授权',
  authorized: '已授权',
  failed: '失败',
}[value] || value || '-')

const getAuthorizationStatusType = value => ({
  authorized: 'success',
  pending: 'warning',
  failed: 'danger',
}[value] || 'info')

const getRunStatusLabel = value => ({
  queued: '排队',
  running: '运行中',
  success: '成功',
  failed: '失败',
}[value] || value || '-')

const getRunStatusType = value => ({
  success: 'success',
  running: 'warning',
  queued: 'info',
  failed: 'danger',
}[value] || 'info')

const formatTime = value => {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString()
}

watch(
  () => props.active,
  value => {
    if (value && !repositories.value.length) {
      loadData()
    }
  }
)

onMounted(() => {
  if (props.active) {
    loadData()
  }
})
</script>

<style scoped>
.knowledge-repository-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  background: #f6f8fb;
  color: #1f2d3d;
}

.knowledge-repository-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.knowledge-repository-panel__header h2,
.knowledge-repository-panel__runs h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.4;
}

.knowledge-repository-panel__header span,
.knowledge-repository-panel__runs span {
  color: #66778a;
  font-size: 13px;
}

.knowledge-repository-panel__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.knowledge-repository-panel__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 10px;
}

.knowledge-repository-panel__summary > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #dce5ee;
  border-radius: 6px;
  background: #ffffff;
}

.knowledge-repository-panel__summary span {
  color: #66778a;
  font-size: 12px;
}

.knowledge-repository-panel__summary strong {
  font-size: 22px;
  line-height: 1;
}

.knowledge-repository-panel__status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #cddff3;
  border-radius: 6px;
  background: #ffffff;
}

.knowledge-repository-panel__status > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.knowledge-repository-panel__status strong {
  font-size: 14px;
  color: #1f2d3d;
}

.knowledge-repository-panel__status span {
  overflow: hidden;
  color: #66778a;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-repository-panel__table,
.knowledge-repository-panel__runs {
  background: #ffffff;
}

.knowledge-repository-panel__runs {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.knowledge-repository-panel__runs header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.repository-location {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-repository-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 12px;
}

@media (max-width: 900px) {
  .knowledge-repository-panel__header,
  .knowledge-repository-panel__runs header {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-repository-panel__summary,
  .knowledge-repository-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
