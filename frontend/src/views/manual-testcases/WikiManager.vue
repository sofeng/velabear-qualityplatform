<template>
  <div class="wiki-manager-page manual-workspace-density-scope">
    <aside class="wiki-directory-panel">
      <div class="wiki-directory-toolbar">
        <el-select
          v-model="selectedProjectId"
          filterable
          placeholder="选择项目"
          class="wiki-project-select"
          @change="handleProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
      </div>

      <div class="wiki-directory-actions">
        <el-button type="primary" plain :icon="Plus" @click="openDirectoryDialog('root')">目录</el-button>
        <el-button plain :disabled="!currentDirectory" :icon="FolderAdd" @click="openDirectoryDialog('child')">子目录</el-button>
      </div>

      <button
        class="wiki-directory-all"
        :class="{ active: !selectedDirectoryId }"
        type="button"
        @click="selectAllDirectories"
      >
        全部 Wiki
      </button>

      <el-input
        v-model="directoryKeyword"
        clearable
        placeholder="搜索目录"
        class="wiki-directory-search"
      />

      <el-scrollbar class="wiki-directory-tree">
        <el-tree
          ref="directoryTreeRef"
          :data="directoryTree"
          node-key="id"
          :props="treeProps"
          :highlight-current="true"
          :filter-node-method="filterDirectoryNode"
          default-expand-all
          @node-click="handleDirectoryNodeClick"
        >
          <template #default="{ data }">
            <div class="wiki-directory-node">
              <span class="wiki-directory-node__label">{{ data.label }}</span>
              <span class="wiki-directory-node__actions">
                <el-icon @click.stop="openDirectoryDialog('edit', data)"><Edit /></el-icon>
                <el-icon @click.stop="confirmDeleteDirectory(data)"><Delete /></el-icon>
              </span>
            </div>
          </template>
        </el-tree>
      </el-scrollbar>
    </aside>

    <main class="wiki-main-panel">
      <header class="wiki-main-toolbar">
        <div class="wiki-filter-group">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索标题或正文"
            class="wiki-keyword-input"
            @keyup.enter="loadWikiPages"
            @clear="loadWikiPages"
          />
          <el-button type="primary" :icon="Search" @click="loadWikiPages">搜索</el-button>
          <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
        </div>
        <div class="wiki-action-group">
          <el-button :icon="Refresh" @click="loadWikiPages">刷新</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateWiki">新建 Wiki</el-button>
        </div>
      </header>

      <section class="wiki-content-layout">
        <div class="wiki-list-panel">
          <el-table
            v-loading="wikiLoading"
            :data="wikiPages"
            row-key="id"
            height="100%"
            highlight-current-row
            class="wiki-table"
            empty-text="暂无 Wiki"
            @row-click="handleWikiRowClick"
          >
            <el-table-column prop="code" label="编号" width="150" show-overflow-tooltip />
            <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
            <el-table-column label="目录" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ getWikiDirectoryLabel(row) }}</template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="170" show-overflow-tooltip />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="openWikiDetail(row, true)">编辑</el-button>
                <el-button link type="danger" @click.stop="confirmDeleteWiki(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            class="wiki-pagination"
            @size-change="handlePageChange"
            @current-change="handlePageChange"
          />
        </div>

        <div class="wiki-detail-panel">
          <template v-if="detailMode === 'empty'">
            <el-empty description="选择 Wiki 或新建 Wiki" />
          </template>

          <template v-else-if="detailMode === 'view'">
            <div class="wiki-detail-header">
              <div>
                <h2>{{ selectedWiki?.title }}</h2>
                <p>{{ selectedWiki?.code }} · {{ getWikiDirectoryLabel(selectedWiki) }}</p>
              </div>
              <div class="wiki-detail-actions">
                <el-button type="primary" plain :icon="Edit" @click="startEditSelectedWiki">编辑</el-button>
                <el-button :icon="Plus" @click="openCreateWiki">新建</el-button>
              </div>
            </div>
            <el-scrollbar class="wiki-rich-content">
              <DefectRichTextContent :html="selectedWiki?.description || ''" empty-text="暂无内容" />
            </el-scrollbar>
          </template>

          <template v-else>
            <div class="wiki-editor-header">
              <h2>{{ editingWikiId ? '编辑 Wiki' : '新建 Wiki' }}</h2>
              <div class="wiki-detail-actions">
                <el-button @click="cancelEdit">取消</el-button>
                <el-button type="primary" :loading="savingWiki" @click="saveWiki">保存</el-button>
              </div>
            </div>

            <el-form ref="wikiFormRef" :model="wikiForm" :rules="wikiRules" label-width="82px" class="wiki-editor-form">
              <el-form-item label="标题" prop="title">
                <el-input v-model="wikiForm.title" maxlength="500" show-word-limit placeholder="请输入 Wiki 标题" />
              </el-form-item>
              <el-form-item label="目录">
                <el-select v-model="wikiForm.directoryId" clearable filterable placeholder="选择 Wiki 目录" class="wiki-form-select">
                  <el-option
                    v-for="directory in flatDirectories"
                    :key="directory.id"
                    :label="directory.path"
                    :value="directory.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="摘要">
                <el-input v-model="wikiForm.summary" maxlength="500" show-word-limit placeholder="用于列表快速识别，可选" />
              </el-form-item>
              <el-form-item label="标签">
                <el-select
                  v-model="wikiForm.labels"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="输入后回车生成标签"
                  class="wiki-form-select"
                />
              </el-form-item>
              <el-form-item label="内容" prop="description">
                <div class="wiki-editor-field">
                  <DefectRichTextEditor
                    v-model="wikiForm.description"
                    placeholder="编写操作手册内容，可直接粘贴截图或通过工具栏插入图片"
                    :min-height="460"
                  />
                </div>
              </el-form-item>
            </el-form>
          </template>
        </div>
      </section>
    </main>

    <el-dialog
      v-model="directoryDialogVisible"
      :title="directoryDialogTitle"
      width="460px"
      @closed="resetDirectoryForm"
    >
      <el-form ref="directoryFormRef" :model="directoryForm" :rules="directoryRules" label-width="82px">
        <el-form-item label="目录名称" prop="name">
          <el-input v-model="directoryForm.name" maxlength="200" show-word-limit placeholder="请输入目录名称" />
        </el-form-item>
        <el-form-item label="上级目录">
          <el-select v-model="directoryForm.parentId" clearable filterable placeholder="根目录" class="wiki-form-select">
            <el-option
              v-for="directory in selectableParentDirectories"
              :key="directory.id"
              :label="directory.path"
              :value="directory.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="directoryForm.sortOrder" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="directoryForm.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="directoryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingDirectory" @click="saveDirectory">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, FolderAdd, Plus, Refresh, Search } from '@element-plus/icons-vue'
import DefectRichTextContent from '@/components/defects/DefectRichTextContent.vue'
import DefectRichTextEditor from '@/components/defects/DefectRichTextEditor.vue'
import { getProjectList } from '@/api/testcases'
import {
  createWikiDirectory,
  createWikiPage,
  deleteWikiDirectory,
  deleteWikiPage,
  getWikiDirectories,
  getWikiPageDetail,
  getWikiPages,
  updateWikiDirectory,
  updateWikiPage,
} from '@/api/wiki'

const normalizeListResponse = data => {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

const projects = ref([])
const selectedProjectId = ref('')
const directoryTree = ref([])
const flatDirectories = ref([])
const directoryKeyword = ref('')
const selectedDirectoryId = ref('')
const currentDirectory = ref(null)
const wikiPages = ref([])
const wikiLoading = ref(false)
const savingWiki = ref(false)
const selectedWiki = ref(null)
const detailMode = ref('empty')
const editingWikiId = ref('')
const directoryDialogVisible = ref(false)
const directoryDialogMode = ref('root')
const editingDirectoryId = ref('')
const savingDirectory = ref(false)

const directoryTreeRef = ref()
const wikiFormRef = ref()
const directoryFormRef = ref()

const filters = reactive({
  keyword: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

const wikiForm = reactive({
  title: '',
  directoryId: '',
  summary: '',
  labels: [],
  description: '',
})

const directoryForm = reactive({
  name: '',
  parentId: '',
  description: '',
  sortOrder: 0,
})

const treeProps = {
  label: 'label',
  children: 'children',
}

const wikiRules = {
  title: [{ required: true, message: '请输入 Wiki 标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入 Wiki 内容', trigger: 'blur' }],
}

const directoryRules = {
  name: [{ required: true, message: '请输入目录名称', trigger: 'blur' }],
}

const directoryDialogTitle = computed(() => {
  if (directoryDialogMode.value === 'edit') return '编辑 Wiki 目录'
  if (directoryDialogMode.value === 'child') return '新增子目录'
  return '新增 Wiki 目录'
})

const selectableParentDirectories = computed(() => (
  flatDirectories.value.filter(directory => String(directory.id) !== String(editingDirectoryId.value))
))

const normalizeDirectoryTree = (items = [], parentPath = []) => {
  const normalized = []
  items.forEach(item => {
    const label = String(item?.name || '').trim()
    if (!label) return
    const currentPath = [...parentPath, label]
    const node = {
      ...item,
      label,
      path: currentPath.join(' / '),
      children: normalizeDirectoryTree(item.children || [], currentPath),
    }
    normalized.push(node)
  })
  return normalized
}

const flattenDirectories = (items = []) => {
  const result = []
  const walk = nodes => {
    nodes.forEach(node => {
      result.push(node)
      if (node.children?.length) walk(node.children)
    })
  }
  walk(items)
  return result
}

const getDirectoryById = id => (
  flatDirectories.value.find(item => String(item.id) === String(id)) || null
)

const buildWikiDirectoryRelation = directoryId => {
  const directory = getDirectoryById(directoryId)
  if (!directory) return []
  return [{
    id: String(directory.id),
    directory_id: directory.id,
    node_text: directory.label,
    node_type: 'wiki_directory',
    path: directory.path,
  }]
}

const getWikiDirectoryLabel = row => {
  const relation = Array.isArray(row?.modules) ? row.modules[0] : null
  return relation?.path || relation?.node_text || '未归档'
}

const loadProjects = async () => {
  const response = await getProjectList()
  projects.value = normalizeListResponse(response.data)
  if (!selectedProjectId.value && projects.value.length) {
    selectedProjectId.value = projects.value[0].id
  }
}

const loadDirectories = async () => {
  if (!selectedProjectId.value) {
    directoryTree.value = []
    flatDirectories.value = []
    return
  }
  const response = await getWikiDirectories({ project: selectedProjectId.value })
  directoryTree.value = normalizeDirectoryTree(normalizeListResponse(response.data))
  flatDirectories.value = flattenDirectories(directoryTree.value)
  if (selectedDirectoryId.value && !getDirectoryById(selectedDirectoryId.value)) {
    selectAllDirectories()
  }
}

const buildWikiParams = () => {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ordering: '-updated_at',
    project: selectedProjectId.value,
  }
  if (filters.keyword.trim()) {
    params.search = filters.keyword.trim()
  }
  if (selectedDirectoryId.value) {
    params.wiki_directory = selectedDirectoryId.value
    params.include_children = true
  }
  return params
}

const loadWikiPages = async () => {
  if (!selectedProjectId.value) {
    wikiPages.value = []
    pagination.total = 0
    return
  }
  wikiLoading.value = true
  try {
    const response = await getWikiPages(buildWikiParams())
    wikiPages.value = normalizeListResponse(response.data)
    pagination.total = Number(response.data?.count || wikiPages.value.length || 0)
  } catch (error) {
    wikiPages.value = []
    pagination.total = 0
    ElMessage.error('获取 Wiki 列表失败')
  } finally {
    wikiLoading.value = false
  }
}

const handleRefresh = async () => {
  await Promise.all([loadDirectories(), loadWikiPages()])
}

const handleProjectChange = async () => {
  selectedDirectoryId.value = ''
  currentDirectory.value = null
  selectedWiki.value = null
  detailMode.value = 'empty'
  pagination.page = 1
  await handleRefresh()
}

const selectAllDirectories = () => {
  selectedDirectoryId.value = ''
  currentDirectory.value = null
  directoryTreeRef.value?.setCurrentKey?.()
  pagination.page = 1
  loadWikiPages()
}

const handleDirectoryNodeClick = data => {
  selectedDirectoryId.value = data.id
  currentDirectory.value = data
  pagination.page = 1
  loadWikiPages()
}

const filterDirectoryNode = (value, data) => {
  if (!value) return true
  return String(data.label || '').includes(value) || String(data.path || '').includes(value)
}

const resetFilters = () => {
  filters.keyword = ''
  pagination.page = 1
  loadWikiPages()
}

const handlePageChange = () => {
  loadWikiPages()
}

const resetWikiForm = () => {
  editingWikiId.value = ''
  wikiForm.title = ''
  wikiForm.directoryId = selectedDirectoryId.value || ''
  wikiForm.summary = ''
  wikiForm.labels = []
  wikiForm.description = ''
  wikiFormRef.value?.clearValidate?.()
}

const openCreateWiki = () => {
  resetWikiForm()
  selectedWiki.value = null
  detailMode.value = 'edit'
}

const handleWikiRowClick = row => {
  openWikiDetail(row, false)
}

const openWikiDetail = async (row, edit = false) => {
  try {
    const response = await getWikiPageDetail(row.id)
    selectedWiki.value = response.data
    if (edit) {
      startEditSelectedWiki()
      return
    }
    detailMode.value = 'view'
  } catch (error) {
    ElMessage.error('获取 Wiki 详情失败')
  }
}

const startEditSelectedWiki = () => {
  if (!selectedWiki.value) return
  editingWikiId.value = selectedWiki.value.id
  wikiForm.title = selectedWiki.value.title || ''
  wikiForm.directoryId = selectedWiki.value.modules?.[0]?.id ? Number(selectedWiki.value.modules[0].id) : ''
  wikiForm.summary = selectedWiki.value.problem_reason || ''
  wikiForm.labels = Array.isArray(selectedWiki.value.labels) ? [...selectedWiki.value.labels] : []
  wikiForm.description = selectedWiki.value.description || ''
  detailMode.value = 'edit'
}

const cancelEdit = () => {
  if (selectedWiki.value) {
    detailMode.value = 'view'
    return
  }
  resetWikiForm()
  detailMode.value = 'empty'
}

const saveWiki = async () => {
  await wikiFormRef.value?.validate()
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  savingWiki.value = true
  try {
    const payload = {
      project_id: selectedProjectId.value,
      version_id: null,
      title: wikiForm.title.trim(),
      description: wikiForm.description,
      problem_reason: wikiForm.summary,
      root_cause: '',
      priority: 'P3',
      severity: 'medium',
      status: 'new',
      requirement_id: '',
      labels: wikiForm.labels,
      assignee_ids: [],
      modules: buildWikiDirectoryRelation(wikiForm.directoryId),
      related_testcases: [],
      related_testpoints: [],
    }
    const response = editingWikiId.value
      ? await updateWikiPage(editingWikiId.value, payload)
      : await createWikiPage(payload)
    selectedWiki.value = response.data
    detailMode.value = 'view'
    ElMessage.success('Wiki 已保存')
    await loadWikiPages()
  } catch (error) {
    if (error !== false) {
      ElMessage.error(error?.response?.data?.detail || error?.response?.data?.title?.[0] || '保存 Wiki 失败')
    }
  } finally {
    savingWiki.value = false
  }
}

const confirmDeleteWiki = async row => {
  await ElMessageBox.confirm(`确定删除 Wiki「${row.title}」吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteWikiPage(row.id)
    if (String(selectedWiki.value?.id) === String(row.id)) {
      selectedWiki.value = null
      detailMode.value = 'empty'
    }
    ElMessage.success('Wiki 已删除')
    await loadWikiPages()
  } catch (error) {
    ElMessage.error('删除 Wiki 失败')
  }
}

const resetDirectoryForm = () => {
  editingDirectoryId.value = ''
  directoryForm.name = ''
  directoryForm.parentId = ''
  directoryForm.description = ''
  directoryForm.sortOrder = 0
  directoryFormRef.value?.clearValidate?.()
}

const openDirectoryDialog = (mode, data = null) => {
  directoryDialogMode.value = mode
  resetDirectoryForm()
  if (mode === 'child' && currentDirectory.value) {
    directoryForm.parentId = currentDirectory.value.id
  }
  if (mode === 'edit' && data) {
    editingDirectoryId.value = data.id
    directoryForm.name = data.name
    directoryForm.parentId = data.parent || ''
    directoryForm.description = data.description || ''
    directoryForm.sortOrder = data.sort_order || 0
  }
  directoryDialogVisible.value = true
}

const saveDirectory = async () => {
  await directoryFormRef.value?.validate()
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  savingDirectory.value = true
  try {
    const payload = {
      project_id: selectedProjectId.value,
      parent_id: directoryForm.parentId || null,
      name: directoryForm.name.trim(),
      description: directoryForm.description,
      sort_order: directoryForm.sortOrder || 0,
    }
    const response = editingDirectoryId.value
      ? await updateWikiDirectory(editingDirectoryId.value, payload)
      : await createWikiDirectory(payload)
    directoryDialogVisible.value = false
    ElMessage.success('目录已保存')
    await loadDirectories()
    const savedId = response.data?.id
    if (savedId) {
      selectedDirectoryId.value = savedId
      currentDirectory.value = getDirectoryById(savedId)
      await nextTick()
      directoryTreeRef.value?.setCurrentKey?.(savedId)
      await loadWikiPages()
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.name?.[0] || '保存目录失败')
  } finally {
    savingDirectory.value = false
  }
}

const confirmDeleteDirectory = async data => {
  await ElMessageBox.confirm(`确定删除目录「${data.label}」及其子目录吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteWikiDirectory(data.id)
    if (String(selectedDirectoryId.value) === String(data.id)) {
      selectAllDirectories()
    }
    ElMessage.success('目录已删除')
    await loadDirectories()
    await loadWikiPages()
  } catch (error) {
    ElMessage.error('删除目录失败')
  }
}

watch(directoryKeyword, value => {
  directoryTreeRef.value?.filter?.(value)
})

onMounted(async () => {
  await loadProjects()
  await handleRefresh()
})
</script>

<style scoped lang="scss">
.wiki-manager-page {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  height: calc(100vh - var(--topbar-height, 68px));
  min-height: 640px;
  background: #f5f7fb;
}

.wiki-directory-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid #dcdfe6;
  background: #ffffff;
  padding: 14px;
  gap: 12px;
}

.wiki-directory-toolbar,
.wiki-main-toolbar,
.wiki-action-group,
.wiki-filter-group,
.wiki-detail-actions,
.wiki-directory-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wiki-project-select,
.wiki-form-select {
  width: 100%;
}

.wiki-directory-actions :deep(.el-button) {
  flex: 1 1 0;
}

.wiki-directory-all {
  border: 0;
  background: #eef5ff;
  color: #1f4f82;
  font-weight: 700;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.wiki-directory-all.active {
  background: #2563eb;
  color: #ffffff;
}

.wiki-directory-search {
  width: 100%;
}

.wiki-directory-tree {
  flex: 1 1 auto;
  min-height: 0;
}

.wiki-directory-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  gap: 8px;
}

.wiki-directory-node__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wiki-directory-node__actions {
  display: none;
  align-items: center;
  gap: 6px;
  color: #606266;
}

.wiki-directory-node:hover .wiki-directory-node__actions {
  display: inline-flex;
}

.wiki-main-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 14px;
  gap: 12px;
}

.wiki-main-toolbar {
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e4e7ed;
  padding: 10px 12px;
}

.wiki-keyword-input {
  width: 260px;
}

.wiki-content-layout {
  display: grid;
  grid-template-columns: minmax(440px, 48%) minmax(420px, 1fr);
  flex: 1 1 auto;
  min-height: 0;
  gap: 12px;
}

.wiki-list-panel,
.wiki-detail-panel {
  min-width: 0;
  min-height: 0;
  background: #ffffff;
  border: 1px solid #e4e7ed;
}

.wiki-list-panel {
  display: flex;
  flex-direction: column;
}

.wiki-table {
  flex: 1 1 auto;
}

.wiki-pagination {
  flex: 0 0 auto;
  justify-content: flex-end;
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
}

.wiki-detail-panel {
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.wiki-detail-header,
.wiki-editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.wiki-detail-header h2,
.wiki-editor-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.wiki-detail-header p {
  margin: 6px 0 0;
  color: #667085;
}

.wiki-rich-content {
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 16px;
}

.wiki-editor-form {
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 16px;
  overflow: auto;
}

.wiki-editor-field {
  width: 100%;
}

@media (max-width: 1200px) {
  .wiki-manager-page {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .wiki-content-layout {
    grid-template-columns: 1fr;
  }

  .wiki-detail-panel {
    min-height: 520px;
  }
}
</style>
