<template>
  <slot
    :context="context"
    :toolbar-props="toolbarProps"
    :directory-props="directoryProps"
    :actions="actions"
  />

  <el-dialog
    v-model="categoryDialogVisible"
    :title="categoryDialogTitle"
    width="420px"
    append-to-body
  >
    <el-form ref="categoryFormRef" :model="categoryFormData" :rules="categoryFormRules" label-width="80px">
      <el-form-item label="目录名称" prop="name">
        <el-input v-model="categoryFormData.name" placeholder="请输入目录名称" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="categoryFormData.description" type="textarea" :rows="3" placeholder="请输入描述" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="categoryDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleCategorySubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import { getManualCategories, getProjectList, importManualCategoriesFromXMind } from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import { PERMISSION_CODES } from '@/utils/permissions'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  directoryTitle: {
    type: String,
    default: '目录树'
  },
  syncRoute: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const projects = ref([])
const versions = ref([])
const categoryTree = ref([])
const expandedCategoryKeys = ref([])
const currentCategory = ref(null)
const treeSearchText = ref('')
const isDirectoryCollapsed = ref(false)
const projectsLoading = ref(false)
const versionsLoading = ref(false)
const categoriesLoading = ref(false)
const categoryImporting = ref(false)
const workspaceProjectDefaultLoading = ref(false)

const context = reactive({
  project_id: '',
  project_name: '',
  version_id: 'all',
  version_name: '',
  module_id: '',
  module_name: '',
  module_path: '',
  category_id: '',
  category_name: '',
  category_path: ''
})

const treeProps = {
  children: 'children',
  label: 'label'
}

const categoryDialogVisible = ref(false)
const categoryDialogTitle = ref('添加目录')
const categoryFormRef = ref(null)
const categoryFormData = reactive({
  id: null,
  name: '',
  description: '',
  parentId: null
})
const categoryFormRules = {
  name: [
    { required: true, message: '请输入目录名称', trigger: 'blur' }
  ]
}

const normalizeListResponse = payload => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const normalizeValue = value => (Array.isArray(value) ? value[0] : value)
const normalizeText = value => String(value ?? '').trim()
const isAllRouteValue = value => normalizeText(normalizeValue(value)).toLowerCase() === 'all'

const normalizeContextValue = value => {
  const source = value && typeof value === 'object' ? value : {}
  const moduleId = source.module_id ?? source.category_id ?? ''
  const moduleName = source.module_name ?? source.category_name ?? ''
  const modulePath = source.module_path ?? source.category_path ?? ''
  return {
    project_id: source.project_id || '',
    project_name: source.project_name || '',
    version_id: source.version_id || 'all',
    version_name: source.version_name || '',
    module_id: moduleId || '',
    module_name: moduleName || '',
    module_path: modulePath || '',
    category_id: moduleId || '',
    category_name: moduleName || '',
    category_path: modulePath || ''
  }
}

const applyContext = value => {
  Object.assign(context, normalizeContextValue(value))
}

const buildContextPayload = () => ({ ...context })

const hasQueryChanged = (left, right) => {
  const leftKeys = Object.keys(left || {})
  const rightKeys = Object.keys(right || {})
  if (leftKeys.length !== rightKeys.length) return true
  return leftKeys.some(key => String(normalizeValue(left[key]) ?? '') !== String(normalizeValue(right[key]) ?? ''))
}

const syncRouteQuery = () => {
  if (!props.syncRoute) return
  const nextQuery = { ...route.query }
  if (context.project_id) {
    nextQuery.project_id = String(context.project_id)
  } else {
    delete nextQuery.project_id
  }
  if (context.version_id === 'all') {
    nextQuery.version_id = 'all'
  } else if (context.version_id) {
    nextQuery.version_id = String(context.version_id)
  } else {
    delete nextQuery.version_id
  }
  if (context.module_id) {
    nextQuery.category_id = String(context.module_id)
  } else {
    delete nextQuery.category_id
  }
  if (hasQueryChanged(route.query, nextQuery)) {
    router.replace({ path: route.path, query: nextQuery }).catch(() => {})
  }
}

const emitContext = ({ routeSync = true } = {}) => {
  const payload = buildContextPayload()
  emit('update:modelValue', payload)
  emit('change', payload)
  if (routeSync) {
    syncRouteQuery()
  }
}

watch(
  () => props.modelValue,
  value => {
    applyContext(value)
  },
  { deep: true, immediate: true }
)

const parseRouteId = value => {
  const rawValue = normalizeValue(value)
  if (rawValue === undefined || rawValue === null || rawValue === '' || rawValue === 'all') {
    return ''
  }
  return String(rawValue)
}

const findById = (items, id) => {
  if (id === undefined || id === null || id === '') return null
  return items.find(item => String(item?.id) === String(id)) || null
}

const getWorkspaceProjectDataScore = project => {
  const versionCount = Number(project?.version_count || 0)
  const categoryCount = Number(project?.manual_category_count || 0)
  const mindmapCount = Number(project?.mindmap_count || 0)
  return (mindmapCount * 10000) + (categoryCount * 100) + versionCount
}

const selectedWorkspaceProject = computed(() => findById(projects.value, context.project_id))
const canSetDefaultWorkspaceProject = computed(() => (
  userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.projectEdit)
))
const currentLinkedVersionName = computed(() => {
  if (!context.version_id || context.version_id === 'all') return ''
  return findById(versions.value, context.version_id)?.name || ''
})

const buildAdaptiveSelectStyle = (text, {
  minWidth = 132,
  maxWidth = 320,
  characterWidth = 14,
  padding = 72
} = {}) => {
  const content = normalizeText(text)
  const width = Math.min(maxWidth, Math.max(minWidth, (content.length * characterWidth) + padding))
  return { width: `${width}px` }
}

const workspaceProjectSelectStyle = computed(() => (
  buildAdaptiveSelectStyle(selectedWorkspaceProject.value?.name || '请选择项目', {
    minWidth: 132,
    maxWidth: 180,
    characterWidth: 10,
    padding: 64
  })
))
const workspaceVersionSelectStyle = computed(() => (
  buildAdaptiveSelectStyle(currentLinkedVersionName.value || '请选择版本号', {
    minWidth: 96,
    maxWidth: 140,
    characterWidth: 11,
    padding: 52
  })
))

const toolbarProps = computed(() => ({
  projectId: context.project_id,
  projects: projects.value,
  selectedProject: selectedWorkspaceProject.value,
  projectSelectStyle: workspaceProjectSelectStyle.value,
  versionId: context.version_id || 'all',
  versions: versions.value,
  versionSelectStyle: workspaceVersionSelectStyle.value,
  versionDisabled: !context.project_id,
  canSetDefaultProject: canSetDefaultWorkspaceProject.value,
  defaultProjectLoading: workspaceProjectDefaultLoading.value,
  projectsLoading: projectsLoading.value,
  versionsLoading: versionsLoading.value
}))

const directoryProps = computed(() => ({
  collapsed: isDirectoryCollapsed.value,
  showCategoryTree: true,
  title: props.directoryTitle,
  railLabel: '目录树',
  hint: '',
  filterText: treeSearchText.value,
  categoryTree: categoryTree.value,
  treeProps,
  expandedCategoryKeys: expandedCategoryKeys.value,
  currentCategory: currentCategory.value,
  showAddActions: true,
  canEditCategory: true,
  categoryImporting: categoryImporting.value,
  loading: categoriesLoading.value,
  emptyDescription: '暂无目录数据'
}))

const normalizeCategoryTree = (categories = [], parentPath = []) =>
  normalizeListResponse(categories).map(category => {
    const label = normalizeText(category?.name || category?.label)
    const currentPath = [...parentPath, label].filter(Boolean)
    return {
      id: category?.id,
      label,
      description: category?.description || '',
      parentId: category?.parent ?? category?.parentId ?? null,
      fullPath: currentPath.join(' / '),
      children: normalizeCategoryTree(category?.children || [], currentPath)
    }
  })

const findCategoryNode = (nodes, matcher) => {
  for (const node of nodes) {
    if (matcher(node)) return node
    const child = findCategoryNode(node.children || [], matcher)
    if (child) return child
  }
  return null
}

const findCategoryPath = (nodes, matcher, ancestors = []) => {
  for (const node of nodes) {
    const currentPath = [...ancestors, node]
    if (matcher(node)) return currentPath
    const childPath = findCategoryPath(node.children || [], matcher, currentPath)
    if (childPath.length) return childPath
  }
  return []
}

const assignCategoryToContext = node => {
  context.module_id = node?.id || ''
  context.module_name = node?.label || ''
  context.module_path = node?.fullPath || node?.label || ''
  context.category_id = context.module_id
  context.category_name = context.module_name
  context.category_path = context.module_path
}

const resolveInitialProject = () => {
  const routeProject = findById(projects.value, parseRouteId(route.query.project_id))
  if (routeProject) return routeProject
  const currentProject = findById(projects.value, context.project_id)
  if (currentProject) return currentProject
  const defaultProject = projects.value.find(project => project?.is_default)
  if (defaultProject) return defaultProject
  return [...projects.value].sort((left, right) => {
    const scoreDiff = getWorkspaceProjectDataScore(right) - getWorkspaceProjectDataScore(left)
    if (scoreDiff !== 0) return scoreDiff
    return normalizeText(left?.name).localeCompare(normalizeText(right?.name), 'zh-CN')
  })[0] || null
}

const loadProjects = async () => {
  projectsLoading.value = true
  try {
    const response = await getProjectList()
    projects.value = normalizeListResponse(response.data)
  } catch (error) {
    projects.value = []
    ElMessage.error('加载项目失败')
  } finally {
    projectsLoading.value = false
  }
}

const loadVersions = async (projectId, preferredVersionId = '') => {
  if (!projectId) {
    versions.value = []
    context.version_id = 'all'
    context.version_name = ''
    return
  }
  versionsLoading.value = true
  try {
    const response = await api.get('/versions/', { params: { projects: projectId } })
    versions.value = normalizeListResponse(response.data)
    const routeRequestsAllVersions = isAllRouteValue(route.query.version_id)
    const requestedVersionId = routeRequestsAllVersions
      ? 'all'
      : (preferredVersionId || parseRouteId(route.query.version_id) || context.version_id)
    const requestedVersion = requestedVersionId && requestedVersionId !== 'all'
      ? findById(versions.value, requestedVersionId)
      : null
    const defaultVersion = versions.value.find(version => version?.is_default)
    const selectedVersion = requestedVersionId === 'all' ? null : (requestedVersion || defaultVersion || null)
    context.version_id = selectedVersion?.id || 'all'
    context.version_name = selectedVersion?.name || ''
  } catch (error) {
    versions.value = []
    context.version_id = 'all'
    context.version_name = ''
  } finally {
    versionsLoading.value = false
  }
}

const selectDefaultCategory = async (preferredCategoryId = '') => {
  const routeCategoryId = parseRouteId(route.query.category_id)
  const selectedCategory =
    (preferredCategoryId && findCategoryNode(categoryTree.value, node => String(node.id) === String(preferredCategoryId))) ||
    (context.module_id && findCategoryNode(categoryTree.value, node => String(node.id) === String(context.module_id))) ||
    (routeCategoryId && findCategoryNode(categoryTree.value, node => String(node.id) === String(routeCategoryId))) ||
    findCategoryNode(categoryTree.value, node => node.parentId === null && node.label === '物业通') ||
    categoryTree.value[0] ||
    null

  currentCategory.value = selectedCategory
  assignCategoryToContext(selectedCategory)
  await nextTick()
}

const loadCategories = async (projectId, preferredCategoryId = '') => {
  if (!projectId) {
    categoryTree.value = []
    currentCategory.value = null
    assignCategoryToContext(null)
    return
  }
  categoriesLoading.value = true
  try {
    const response = await getManualCategories({ project: projectId })
    categoryTree.value = normalizeCategoryTree(normalizeListResponse(response.data))
    const defaultExpandedRoot = findCategoryNode(
      categoryTree.value,
      node => node.parentId === null && node.label === '物业通'
    )
    const preferredPath = preferredCategoryId
      ? findCategoryPath(categoryTree.value, node => String(node.id) === String(preferredCategoryId))
      : []
    expandedCategoryKeys.value = [...new Set([
      ...(defaultExpandedRoot?.id ? [defaultExpandedRoot.id] : []),
      ...preferredPath.map(node => node.id).filter(Boolean)
    ])]
    await selectDefaultCategory(preferredCategoryId)
  } catch (error) {
    categoryTree.value = []
    currentCategory.value = null
    assignCategoryToContext(null)
    ElMessage.error('加载目录失败')
  } finally {
    categoriesLoading.value = false
  }
}

const selectProject = async (projectId, { preferredVersionId = '', preferredCategoryId = '' } = {}) => {
  const project = findById(projects.value, projectId)
  context.project_id = project?.id || ''
  context.project_name = project?.name || ''
  if (!project) {
    versions.value = []
    categoryTree.value = []
    currentCategory.value = null
    context.version_id = 'all'
    context.version_name = ''
    assignCategoryToContext(null)
    emitContext()
    return
  }
  await Promise.all([
    loadVersions(project.id, preferredVersionId),
    loadCategories(project.id, preferredCategoryId)
  ])
  emitContext()
}

const handleProjectSelection = projectId => {
  context.version_id = 'all'
  context.version_name = ''
  assignCategoryToContext(null)
  selectProject(projectId)
}

const handleVersionSelection = versionId => {
  const normalizedVersionId = versionId || 'all'
  const selectedVersion = normalizedVersionId === 'all' ? null : findById(versions.value, normalizedVersionId)
  context.version_id = selectedVersion?.id || 'all'
  context.version_name = selectedVersion?.name || ''
  emitContext()
}

const handleCategorySelect = node => {
  currentCategory.value = node
  assignCategoryToContext(node)
  emitContext()
}

const handleNodeContextmenu = (event, data) => {
  event?.preventDefault?.()
  currentCategory.value = data
}

const toggleDirectoryCollapsed = () => {
  isDirectoryCollapsed.value = !isDirectoryCollapsed.value
}

const updateTreeFilterText = value => {
  treeSearchText.value = value || ''
}

const handleAddCategory = command => {
  categoryDialogTitle.value = command === 'root' ? '添加一级目录' : '添加子目录'
  categoryFormData.id = null
  categoryFormData.name = ''
  categoryFormData.description = ''
  categoryFormData.parentId = command === 'root' ? null : currentCategory.value?.id ?? null
  categoryDialogVisible.value = true
}

const handleEditCategory = data => {
  categoryDialogTitle.value = '编辑目录'
  categoryFormData.id = data.id
  categoryFormData.name = data.label
  categoryFormData.description = data.description || ''
  categoryFormData.parentId = data.parentId
  categoryDialogVisible.value = true
}

const handleDeleteCategory = data => {
  ElMessageBox.confirm('确定要删除该目录吗？删除后其子目录也将被删除。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    await api.delete(`/testcases/manual-categories/${data.id}/`)
    ElMessage.success('删除成功')
    await loadCategories(context.project_id)
    emitContext()
  }).catch(error => {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '删除目录失败')
    }
  })
}

const handleCategorySubmit = async () => {
  if (!categoryFormRef.value) return
  const valid = await categoryFormRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (categoryFormData.id) {
      await api.put(`/testcases/manual-categories/${categoryFormData.id}/`, {
        name: categoryFormData.name,
        description: categoryFormData.description,
        parent_id: categoryFormData.parentId
      })
      ElMessage.success('编辑成功')
    } else {
      await api.post('/testcases/manual-categories/', {
        name: categoryFormData.name,
        description: categoryFormData.description,
        parent_id: categoryFormData.parentId,
        project_id: context.project_id
      })
      ElMessage.success('添加成功')
    }
    categoryDialogVisible.value = false
    await loadCategories(context.project_id)
    emitContext()
  } catch (error) {
    ElMessage.error('保存目录失败：' + (error.response?.data?.detail || error.message))
  }
}

const handleCategoryXMindImport = async file => {
  if (!context.project_id) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!file) return

  categoryImporting.value = true
  try {
    const parentId = currentCategory.value?.isVirtual ? null : (currentCategory.value?.id ?? null)
    const response = await importManualCategoriesFromXMind({
      projectId: context.project_id,
      parentId,
      xmindFile: file
    })
    const importedRootId = response.data?.root_category?.id || ''
    await loadCategories(context.project_id, importedRootId)
    emitContext()
    ElMessage.success(response.data?.message || 'XMind 目录导入成功')
  } catch (error) {
    const responseData = error.response?.data || {}
    const fileError = Array.isArray(responseData.xmind_file) ? responseData.xmind_file[0] : responseData.xmind_file
    ElMessage.error('导入 XMind 失败：' + (fileError || responseData.detail || error.message))
  } finally {
    categoryImporting.value = false
  }
}

const handleSetCurrentProjectDefault = async () => {
  if (!context.project_id) {
    ElMessage.warning('请先选择项目')
    return
  }
  workspaceProjectDefaultLoading.value = true
  try {
    await api.patch(`/projects/${context.project_id}/`, { is_default: true })
    projects.value = projects.value.map(project => ({
      ...project,
      is_default: String(project.id) === String(context.project_id)
    }))
    ElMessage.success('默认项目已更新')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '设置默认项目失败')
  } finally {
    workspaceProjectDefaultLoading.value = false
  }
}

const handleManageVersions = () => {
  router.push({
    path: '/manual-testcases/list',
    query: {
      ...route.query,
      tab: 'versions',
      project_id: context.project_id || undefined,
      version_id: context.version_id === 'all'
        ? 'all'
        : (context.version_id ? context.version_id : undefined),
      category_id: context.module_id || undefined
    }
  })
}

const actions = {
  selectProject: handleProjectSelection,
  selectVersion: handleVersionSelection,
  selectCategory: handleCategorySelect,
  setDefaultProject: handleSetCurrentProjectDefault,
  manageVersions: handleManageVersions,
  toggleDirectoryCollapsed,
  updateTreeFilterText,
  addCategory: handleAddCategory,
  nodeContextmenu: handleNodeContextmenu,
  editCategory: handleEditCategory,
  deleteCategory: handleDeleteCategory,
  importXMind: handleCategoryXMindImport
}

onMounted(async () => {
  await loadProjects()
  const selectedProject = resolveInitialProject()
  if (selectedProject) {
    await selectProject(selectedProject.id, {
      preferredVersionId: parseRouteId(route.query.version_id) || context.version_id,
      preferredCategoryId: parseRouteId(route.query.category_id) || context.module_id
    })
  } else {
    emitContext()
  }
})
</script>
