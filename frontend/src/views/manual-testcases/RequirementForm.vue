<template>
  <div class="page-container requirement-form-page">
    <div class="page-header">
      <div class="header-title">
        <h1 class="page-title">{{ isEdit ? '编辑需求' : '新建需求' }}</h1>
        <p v-if="contextText" class="page-subtitle">{{ contextText }}</p>
      </div>
      <div class="header-actions">
        <el-button v-if="isFromManualWorkspace" @click="goBackToManualWorkspace">返回思源研发管理</el-button>
        <el-button @click="goBackToList">返回列表</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存修改' : '创建需求' }}
        </el-button>
      </div>
    </div>

    <div v-loading="loading" class="card-container requirement-form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-tabs v-model="activeTab" class="requirement-form-tabs">
          <el-tab-pane label="需求详情" name="detail">
            <div class="tab-panel">
              <el-form-item label="需求标题" prop="summary">
                <el-input
                  v-model="form.summary"
                  maxlength="500"
                  show-word-limit
                  placeholder="请输入需求标题"
                />
              </el-form-item>

              <el-form-item label="需求描述" prop="description">
                <div class="rich-text-field">
                  <div class="rich-text-tip">
                    支持富文本、图片粘贴、工具栏插图；点击图片可全屏预览。
                  </div>
                  <DefectRichTextEditor
                    v-model="form.description"
                    placeholder="请输入需求描述"
                    :min-height="380"
                    @preview-images="openPreview"
                  />
                </div>
              </el-form-item>

              <el-form-item v-if="existingAttachments.length" label="已有附件">
                <div class="attachment-list">
                  <div
                    v-for="attachment in existingAttachments"
                    :key="attachment.id"
                    class="attachment-item"
                  >
                    <div class="attachment-item__meta">
                      <span class="attachment-item__name">{{ attachment.name }}</span>
                      <span class="attachment-item__time">{{ formatDate(attachment.uploaded_at) }}</span>
                    </div>
                    <div class="attachment-item__actions">
                      <el-button
                        v-if="isImageFile(attachment.file, attachment.name)"
                        link
                        type="primary"
                        @click="openExistingAttachmentPreview(attachment)"
                      >
                        预览
                      </el-button>
                      <el-button link type="primary" @click="openAttachment(attachment.file)">
                        打开
                      </el-button>
                      <el-button link type="danger" @click="removeExistingAttachment(attachment.id)">
                        移除
                      </el-button>
                    </div>
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="新增附件">
                <el-upload
                  v-model:file-list="uploadFileList"
                  drag
                  multiple
                  :auto-upload="false"
                  :before-upload="beforeAttachmentUpload"
                  :on-preview="handleNewAttachmentPreview"
                  class="attachment-upload"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">拖拽文件到这里，或点击选择附件</div>
                  <template #tip>
                    <div class="el-upload__tip">
                      支持图片、文档等文件，图片附件同样支持全屏预览。
                    </div>
                  </template>
                </el-upload>
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="需求处理" name="process">
            <div class="tab-panel">
              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="版本号" prop="version">
                    <el-select
                      v-model="form.version"
                      filterable
                      allow-create
                      default-first-option
                      placeholder="请输入或选择版本号"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="item in versionOptions"
                        :key="item.version"
                        :label="item.version"
                        :value="item.version"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="需求编号" prop="issue_key">
                    <el-input
                      v-model="form.issue_key"
                      maxlength="100"
                      placeholder="请输入需求编号"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="需求类型">
                    <el-input
                      v-model="form.issue_type"
                      maxlength="100"
                      placeholder="例如：功能需求"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="所属模块">
                    <div v-click-outside="handleModuleSelectorClickOutside" class="module-selector">
                      <el-input
                        v-model="form.module"
                        maxlength="255"
                        clearable
                        placeholder="请输入所属模块，或从目录树中选择"
                        @focus="openModuleSelector"
                        @click="openModuleSelector"
                      >
                        <template #append>
                          <el-button @click.stop="toggleModuleSelector">
                            目录树
                          </el-button>
                        </template>
                      </el-input>
                      <div v-if="moduleTreeVisible" v-loading="moduleCategoryLoading" class="module-selector__dropdown">
                        <div class="module-selector__hint">
                          当前项目目录树，可展开/收缩节点，也可直接输入非目录树模块名称
                        </div>
                        <el-tree
                          v-if="moduleCategoryTree.length"
                          :data="moduleCategoryTree"
                          node-key="id"
                          highlight-current
                          :current-node-key="selectedModuleCategoryId"
                          :default-expanded-keys="moduleExpandedKeys"
                          :expand-on-click-node="false"
                          class="module-selector__tree"
                          @node-click="handleModuleCategorySelect"
                        />
                        <div v-else class="module-selector__empty">
                          {{ currentProjectId ? '当前项目暂无目录节点，可直接输入模块名称' : '未获取到当前项目目录，可直接输入模块名称' }}
                        </div>
                      </div>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="客户">
                    <el-input
                      v-model="form.customer_name"
                      maxlength="255"
                      placeholder="请输入客户名称"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="优先级">
                    <el-select
                      v-model="form.priority"
                      clearable
                      placeholder="请选择优先级"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="option in priorityOptions"
                        :key="`priority-${option.value}`"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="状态">
                    <el-select
                      v-model="form.status"
                      clearable
                      placeholder="请选择状态"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="option in requirementStatusOptions"
                        :key="`status-${option.value}`"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="创建人">
                    <el-input
                      v-model="form.creator"
                      maxlength="100"
                      placeholder="请输入创建人"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="处理人">
                    <el-input
                      v-model="form.handler"
                      maxlength="100"
                      placeholder="请输入处理人"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="测试人员">
                    <el-select
                      v-model="form.tester"
                      filterable
                      allow-create
                      default-first-option
                      clearable
                      placeholder="请选择或输入测试人员"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="item in testerNameOptions"
                        :key="`tester-${item}`"
                        :label="item"
                        :value="item"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="组别">
                    <el-select
                      v-model="form.group_name"
                      placeholder="请选择组别"
                      clearable
                      filterable
                      style="width: 100%"
                    >
                      <el-option
                        v-for="group in groupOptions"
                        :key="group.id"
                        :label="group.name"
                        :value="group.name"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="前端开发">
                    <el-select
                      v-model="form.frontend_developer"
                      filterable
                      allow-create
                      default-first-option
                      clearable
                      placeholder="请选择或输入前端开发"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="item in frontendDeveloperNameOptions"
                        :key="`frontend-${item}`"
                        :label="item"
                        :value="item"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="后端开发">
                    <el-select
                      v-model="form.backend_developer"
                      filterable
                      allow-create
                      default-first-option
                      clearable
                      placeholder="请选择或输入后端开发"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="item in backendDeveloperNameOptions"
                        :key="`backend-${item}`"
                        :label="item"
                        :value="item"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="关联测试脑图">
                    <el-select
                      v-model="form.related_mindmaps"
                      multiple
                      filterable
                      remote
                      reserve-keyword
                      value-key="relation_key"
                      collapse-tags
                      collapse-tags-tooltip
                      :loading="relatedMindmapLoading"
                      placeholder="请选择关联测试脑图"
                      style="width: 100%"
                      @visible-change="handleMindmapSelectorVisible"
                      @remote-method="handleMindmapRemoteSearch"
                    >
                      <el-option
                        v-for="option in relatedMindmapOptions"
                        :key="option.relation_key"
                        :label="option.option_label"
                        :value="option"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="扩展字段 JSON" class="requirement-form-item--stacked">
                <el-input
                  v-model="form.raw_fields_text"
                  type="textarea"
                  :rows="8"
                  placeholder="可选，输入 JSON 对象，例如 {&quot;acceptance_criteria&quot;:&quot;...&quot;}"
                />
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-form>
    </div>

    <ImagePreviewViewer
      v-model:visible="previewVisible"
      :images="previewImages"
      :initial-index="previewIndex"
      @update:initial-index="handlePreviewIndexChange"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ClickOutside as vClickOutside, ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'
import DefectRichTextEditor from '@/components/defects/DefectRichTextEditor.vue'
import ImagePreviewViewer from '@/components/defects/ImagePreviewViewer.vue'
import { uploadDefectRichTextImages } from '@/api/defects'
import {
  createRequirementRecord,
  getRequirementRecordDetail,
  updateRequirementRecord,
} from '@/api/requirements'
import { hasRichTextContent, replaceInlineImageDataUrls } from '@/utils/defectRichText'
import { fetchAllGroupOptions } from '@/utils/groupOptions'
import { fetchRoleMemberOptions } from '@/utils/roleOptions'
import { useUserStore } from '@/stores/user'
import { getUserDisplayName } from '@/utils/userDisplay'

const VERSION_ENDPOINT = '/quality-analysis/jira-requirement-records/versions/'
const MANUAL_MINDMAP_ENDPOINT = '/testcases/manual-mindmaps/'
const MODULE_CATEGORY_ENDPOINT = '/testcases/manual-categories/'
const REQUIREMENT_PRIORITY_VALUES = ['P1', 'P2', 'P3', 'P4']
const REQUIREMENT_STATUS_VALUES = [
  '问题创建',
  '需求评审',
  '二开成本确认',
  '待排产需求',
  'PMO排产协调中',
  '产品需求待接收',
  '产品规划设计中',
  '产品设计完成',
  '待启动研发任务',
  '功能研发中',
  '研发技术评审',
  '代码开发完成',
  '功能测试中',
  '测试完成待发版',
  '开发任务完结',
  '需求报告人验收中',
  '已交付上线',
  '已关闭问题',
  '已挂起问题',
  '需求领导特批',
  '需求转换关闭',
]
const REQUIREMENT_DEFAULT_STATUS = '新创建'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const activeTab = ref('detail')
const versionSummaries = ref([])
const groupOptions = ref([])
const testerUsers = ref([])
const frontendUsers = ref([])
const backendUsers = ref([])
const existingAttachments = ref([])
const uploadFileList = ref([])
const relatedMindmapLoading = ref(false)
const relatedMindmapOptions = ref([])
let relatedMindmapRequestSerial = 0
const moduleTreeVisible = ref(false)
const moduleCategoryLoading = ref(false)
const moduleCategoryTree = ref([])
const moduleExpandedKeys = ref([])
const selectedModuleCategoryId = ref(null)

const previewVisible = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

const createDefaultForm = () => ({
  version: '',
  issue_id: '',
  issue_key: '',
  issue_type: '',
  summary: '',
  description: '',
  module: '',
  customer_name: '',
  priority: '',
  status: '',
  creator: '',
  handler: '',
  tester: '',
  group_name: '',
  frontend_developer: '',
  backend_developer: '',
  related_mindmaps: [],
  raw_fields_text: '',
})

const form = reactive(createDefaultForm())

const normalizeText = (value) => String(value ?? '').trim()
const normalizeApiList = (data) => (Array.isArray(data) ? data : data?.results || [])
const getQueryValue = (value) => (Array.isArray(value) ? value[0] : value)
const parsePositiveInteger = (value) => {
  const rawValue = getQueryValue(value)
  const parsedValue = Number(rawValue)

  if (!Number.isInteger(parsedValue) || parsedValue <= 0) {
    return null
  }

  return parsedValue
}
const buildSelectOptions = (values, currentValue = '') => {
  const normalizedCurrentValue = normalizeText(currentValue)
  const baseValues = Array.isArray(values) ? values : []
  const optionValues = (
    normalizedCurrentValue && !baseValues.includes(normalizedCurrentValue)
      ? [normalizedCurrentValue, ...baseValues]
      : baseValues
  )

  return optionValues.map(value => ({
    label: value,
    value,
  }))
}

const isEdit = computed(() => Boolean(route.params.id))
const preservedQuery = computed(() => ({ ...route.query }))
const isFromManualWorkspace = computed(() => getQueryValue(route.query.source) === 'manual-testcases')
const currentProjectId = computed(() => parsePositiveInteger(route.query.project_id))
const currentUserDisplayName = computed(() => normalizeText(getUserDisplayName(userStore.user)))
const priorityOptions = computed(() => buildSelectOptions(REQUIREMENT_PRIORITY_VALUES, form.priority))
const requirementStatusOptions = computed(() => buildSelectOptions(REQUIREMENT_STATUS_VALUES, form.status))
const selectedVersionText = computed(() => normalizeText(form.version || getQueryValue(route.query.version)))
const versionOptions = computed(() => (
  [...versionSummaries.value].sort((left, right) => {
    const rightTime = right.latest_synced_at ? new Date(right.latest_synced_at).getTime() : 0
    const leftTime = left.latest_synced_at ? new Date(left.latest_synced_at).getTime() : 0
    if (rightTime !== leftTime) {
      return rightTime - leftTime
    }
    return String(right.version).localeCompare(String(left.version), 'zh-CN')
  })
))
const buildUserNameOptions = (users) => (
  Array.from(
    new Set(
      (Array.isArray(users) ? users : [])
        .map((user) => getUserDisplayName(user, `用户${user.id}`))
        .map(normalizeText)
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right, 'zh-CN'))
)
const testerNameOptions = computed(() => buildUserNameOptions(testerUsers.value))
const frontendDeveloperNameOptions = computed(() => buildUserNameOptions(frontendUsers.value))
const backendDeveloperNameOptions = computed(() => buildUserNameOptions(backendUsers.value))
const contextText = computed(() => {
  const parts = []
  if (selectedVersionText.value) {
    parts.push(`当前版本 ${selectedVersionText.value}`)
  }
  if (isEdit.value && normalizeText(form.issue_key)) {
    parts.push(`需求编号 ${normalizeText(form.issue_key)}`)
  }
  return parts.join(' / ')
})

const validateDescription = (_rule, value, callback) => {
  if (!hasRichTextContent(value)) {
    callback(new Error('请输入需求描述'))
    return
  }
  callback()
}

const rules = {
  version: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  issue_key: [{ required: true, message: '请输入需求编号', trigger: 'blur' }],
  summary: [{ required: true, message: '请输入需求标题', trigger: 'blur' }],
  description: [{ validator: validateDescription, trigger: 'change' }],
}

const formatDate = (value) => {
  const normalized = normalizeText(value)
  if (!normalized) {
    return '-'
  }
  const parsed = dayjs(normalized)
  return parsed.isValid() ? parsed.format('YYYY/MM/DD HH:mm:ss') : normalized
}

const buildManualWorkspaceQuery = (overrides = {}, keysToClear = []) => {
  const query = {
    ...route.query,
    ...overrides,
  }

  keysToClear.forEach((key) => {
    delete query[key]
  })

  Object.keys(query).forEach((key) => {
    const value = query[key]
    if (value === undefined || value === null || value === '') {
      delete query[key]
      return
    }
    query[key] = String(value)
  })

  return query
}

const goBackToList = () => {
  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery({
      tab: 'version-requirements',
      version: normalizeText(form.version) || normalizeText(getQueryValue(route.query.version)),
    }),
  })
}

const goBackToManualWorkspace = () => {
  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery({
      version: normalizeText(form.version) || normalizeText(getQueryValue(route.query.version)),
    }),
  })
}

const buildRequirementMindmapRelationKey = (item = {}) => {
  const mindmapId = Number(item?.mindmap_id) || 0
  const nodeType = normalizeText(item?.node_type || 'mindmap')
  const path = normalizeText(item?.path || item?.mindmap_name || item?.node_text)
  if (!mindmapId && !path) {
    return ''
  }
  return [mindmapId, nodeType, path].join('::')
}

const buildRequirementMindmapOptionLabel = (item = {}) => {
  const requirementPart = [item.requirement_key, item.requirement_title || item.mindmap_name]
    .map(normalizeText)
    .filter(Boolean)
    .join(' - ')
  const baseLabel = requirementPart || normalizeText(item.mindmap_name) || normalizeText(item.node_text) || '未命名脑图'
  const suffixParts = [normalizeText(item.mindmap_name), normalizeText(item.version_name)]
    .filter(Boolean)

  if (!suffixParts.length) {
    return baseLabel
  }

  const suffix = suffixParts.join(' / ')
  return baseLabel === suffix ? baseLabel : `${baseLabel}（${suffix}）`
}

const decorateRequirementMindmapItem = (item = {}) => {
  const mindmapId = Number(item?.mindmap_id ?? item?.id) || null
  const mindmapName = normalizeText(item?.mindmap_name || item?.name)
  const nodeText = normalizeText(item?.node_text || item?.name || item?.mindmap_name)
  const path = normalizeText(item?.path || item?.name || item?.mindmap_name || item?.node_text)
  const relationKey = buildRequirementMindmapRelationKey({
    mindmap_id: mindmapId,
    node_type: 'mindmap',
    path,
    mindmap_name: mindmapName,
    node_text: nodeText,
  })

  if (!relationKey) {
    return null
  }

  const normalized = {
    mindmap_id: mindmapId,
    mindmap_name: mindmapName,
    node_text: nodeText,
    node_type: 'mindmap',
    path,
    parent_text: normalizeText(item?.parent_text),
    case_id: normalizeText(item?.case_id),
    responsibility_group: normalizeText(item?.responsibility_group),
    version_name: normalizeText(item?.version_name || item?.version?.name),
    requirement_key: normalizeText(item?.requirement_key),
    requirement_title: normalizeText(item?.requirement_title),
  }

  return {
    ...normalized,
    relation_key: relationKey,
    short_label: normalized.requirement_key || normalized.requirement_title || normalized.mindmap_name || normalized.node_text,
    option_label: buildRequirementMindmapOptionLabel(normalized),
  }
}

const ensureUniqueRequirementMindmaps = (items = []) => {
  const itemMap = new Map()

  ;(Array.isArray(items) ? items : []).forEach((item) => {
    const decoratedItem = decorateRequirementMindmapItem(item)
    if (!decoratedItem) {
      return
    }
    itemMap.set(decoratedItem.relation_key, decoratedItem)
  })

  return [...itemMap.values()]
}

const serializeRequirementMindmaps = (items = []) => (
  ensureUniqueRequirementMindmaps(items).map((item) => ({
    mindmap_id: item.mindmap_id,
    mindmap_name: item.mindmap_name,
    node_text: item.node_text,
    node_type: 'mindmap',
    path: item.path,
    parent_text: item.parent_text,
    case_id: item.case_id,
    responsibility_group: item.responsibility_group,
    version_name: item.version_name,
  }))
)

const resetMindmapOptionPool = () => {
  relatedMindmapOptions.value = ensureUniqueRequirementMindmaps(form.related_mindmaps)
}

const mergeRelatedMindmapOptions = (items = [], { autoSelect = false } = {}) => {
  const nextOptions = ensureUniqueRequirementMindmaps(items)

  if (autoSelect) {
    form.related_mindmaps = ensureUniqueRequirementMindmaps([
      ...form.related_mindmaps,
      ...nextOptions,
    ])
  }

  relatedMindmapOptions.value = ensureUniqueRequirementMindmaps([
    ...form.related_mindmaps,
    ...nextOptions,
  ])
}

const buildModuleValueFromPath = (pathText = '') => {
  const pathSegments = String(pathText || '')
    .split(' / ')
    .map(item => item.trim())
    .filter(Boolean)

  if (pathSegments.length <= 1) {
    return pathSegments[0] || ''
  }

  return pathSegments.slice(1).join(' / ')
}

const normalizeModuleCategoryTree = (categories = [], parentPath = []) => (
  (Array.isArray(categories) ? categories : []).map(category => {
    const label = normalizeText(category?.name)
    const nextPath = [...parentPath, label].filter(Boolean)

    return {
      id: category.id,
      label,
      fullPath: nextPath.join(' / '),
      moduleValue: buildModuleValueFromPath(nextPath.join(' / ')) || label,
      children: normalizeModuleCategoryTree(category?.children || [], nextPath),
    }
  })
)

const findModuleCategoryNode = (nodes, predicate) => {
  for (const node of (Array.isArray(nodes) ? nodes : [])) {
    if (predicate(node)) {
      return node
    }

    const childNode = findModuleCategoryNode(node.children, predicate)
    if (childNode) {
      return childNode
    }
  }

  return null
}

const syncModuleCategorySelection = () => {
  const moduleValue = normalizeText(form.module)

  if (!moduleValue) {
    selectedModuleCategoryId.value = null
    return
  }

  const matchedNode = findModuleCategoryNode(
    moduleCategoryTree.value,
    node => [node.moduleValue, node.fullPath, node.label].some(
      candidate => normalizeText(candidate) === moduleValue
    )
  )

  selectedModuleCategoryId.value = matchedNode?.id || null
}

const loadModuleCategories = async () => {
  if (!currentProjectId.value) {
    moduleCategoryTree.value = []
    moduleExpandedKeys.value = []
    selectedModuleCategoryId.value = null
    return
  }

  moduleCategoryLoading.value = true
  try {
    const response = await api.get(MODULE_CATEGORY_ENDPOINT, {
      params: {
        project: currentProjectId.value,
      },
      timeout: 0,
    })

    moduleCategoryTree.value = normalizeModuleCategoryTree(normalizeApiList(response.data))
    moduleExpandedKeys.value = moduleCategoryTree.value.map(node => node.id)
    syncModuleCategorySelection()
  } catch (error) {
    moduleCategoryTree.value = []
    moduleExpandedKeys.value = []
    selectedModuleCategoryId.value = null
    ElMessage.error('获取当前项目目录树失败')
  } finally {
    moduleCategoryLoading.value = false
  }
}

const openModuleSelector = () => {
  moduleTreeVisible.value = true
}

const toggleModuleSelector = () => {
  moduleTreeVisible.value = !moduleTreeVisible.value
}

const handleModuleSelectorClickOutside = () => {
  moduleTreeVisible.value = false
}

const handleModuleCategorySelect = (node) => {
  form.module = node?.moduleValue || node?.label || ''
  selectedModuleCategoryId.value = node?.id || null
  moduleTreeVisible.value = false
}

const loadVersionSummaries = async () => {
  try {
    const response = await api.get(VERSION_ENDPOINT)
    versionSummaries.value = normalizeApiList(response.data)
  } catch (error) {
    versionSummaries.value = []
    ElMessage.error('获取版本需求版本列表失败')
  }
}

const loadGroupOptions = async () => {
  try {
    groupOptions.value = await fetchAllGroupOptions()
  } catch (error) {
    groupOptions.value = []
    ElMessage.error('获取组别列表失败')
  }
}

const loadUsers = async () => {
  try {
    const [testerMembers, frontendMembers, backendMembers] = await Promise.all([
      fetchRoleMemberOptions('测试'),
      fetchRoleMemberOptions('前端'),
      fetchRoleMemberOptions('后端'),
    ])
    testerUsers.value = testerMembers
    frontendUsers.value = frontendMembers
    backendUsers.value = backendMembers
  } catch (error) {
    testerUsers.value = []
    frontendUsers.value = []
    backendUsers.value = []
    ElMessage.error('获取成员列表失败')
  }
}

const cleanupUploadPreviewUrls = () => {
  uploadFileList.value.forEach((item) => {
    if (item?.previewUrl) {
      URL.revokeObjectURL(item.previewUrl)
    }
  })
}

const resetFormState = () => {
  cleanupUploadPreviewUrls()
  Object.assign(form, createDefaultForm())
  existingAttachments.value = []
  uploadFileList.value = []
  activeTab.value = 'detail'
  moduleTreeVisible.value = false
  selectedModuleCategoryId.value = null
  resetMindmapOptionPool()
}

const applyCreateDefaultsFromQuery = () => {
  resetFormState()
  form.version = normalizeText(getQueryValue(route.query.version))
  form.issue_key = normalizeText(getQueryValue(route.query.issue_key))
  form.summary = normalizeText(getQueryValue(route.query.summary))
  form.status = REQUIREMENT_DEFAULT_STATUS
  form.creator = currentUserDisplayName.value
}

const applyDetailData = (detail = {}) => {
  resetFormState()
  Object.assign(form, {
    version: detail.version || '',
    issue_id: detail.issue_id || '',
    issue_key: detail.issue_key || '',
    issue_type: detail.issue_type || '',
    summary: detail.summary || '',
    description: detail.description || '',
    module: detail.module || '',
    customer_name: detail.customer_name || '',
    priority: detail.priority || '',
    status: detail.status || '',
    creator: detail.creator || '',
    handler: detail.handler || '',
    tester: detail.tester || '',
    group_name: detail.group_name || '',
    frontend_developer: detail.frontend_developer || '',
    backend_developer: detail.backend_developer || '',
    related_mindmaps: ensureUniqueRequirementMindmaps(detail.related_mindmaps || []),
    raw_fields_text: JSON.stringify(detail.raw_fields || {}, null, 2),
  })
  existingAttachments.value = detail.attachments || []
  resetMindmapOptionPool()
}

const loadRequirement = async () => {
  if (!isEdit.value) {
    applyCreateDefaultsFromQuery()
    return
  }

  loading.value = true
  try {
    const response = await getRequirementRecordDetail(route.params.id)
    applyDetailData(response.data)
  } catch (error) {
    ElMessage.error('获取需求详情失败')
    goBackToList()
  } finally {
    loading.value = false
  }
}

const loadRelatedMindmapOptions = async (keyword = '', { autoSelect = false } = {}) => {
  const searchKeyword = normalizeText(keyword)
  const requirementKey = normalizeText(form.issue_key)
  const params = { page_size: 50 }

  if (searchKeyword) {
    params.search = searchKeyword
  }
  if (requirementKey) {
    params.requirement_key = requirementKey
  }

  if (!searchKeyword && !requirementKey) {
    relatedMindmapRequestSerial += 1
    resetMindmapOptionPool()
    return
  }

  const requestSerial = ++relatedMindmapRequestSerial
  relatedMindmapLoading.value = true
  try {
    const response = await api.get(MANUAL_MINDMAP_ENDPOINT, { params })
    if (requestSerial !== relatedMindmapRequestSerial) {
      return
    }
    const nextOptions = normalizeApiList(response.data).map(decorateRequirementMindmapItem).filter(Boolean)
    mergeRelatedMindmapOptions(nextOptions, { autoSelect })
  } catch (error) {
    if (requestSerial === relatedMindmapRequestSerial) {
      resetMindmapOptionPool()
    ElMessage.error('获取测试脑图列表失败')
    }
  } finally {
    if (requestSerial === relatedMindmapRequestSerial) {
      relatedMindmapLoading.value = false
    }
  }
}

const handleMindmapSelectorVisible = (visible) => {
  if (!visible) {
    resetMindmapOptionPool()
    return
  }
  loadRelatedMindmapOptions()
}

const handleMindmapRemoteSearch = (keyword) => {
  loadRelatedMindmapOptions(keyword)
}

const removeExistingAttachment = (attachmentId) => {
  existingAttachments.value = existingAttachments.value.filter((item) => item.id !== attachmentId)
}

const beforeAttachmentUpload = () => false

const isImageFile = (filePath = '', fileName = '', fileType = '') => {
  const normalizedType = String(fileType || '').toLowerCase()
  if (normalizedType.startsWith('image/')) {
    return true
  }

  const normalizedPath = `${filePath || ''} ${fileName || ''}`.toLowerCase()
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/.test(normalizedPath)
}

const getUploadFileUrl = (file) => {
  if (!file) {
    return ''
  }

  if (file.url) {
    return file.url
  }

  if (file.previewUrl) {
    return file.previewUrl
  }

  if (file.raw) {
    file.previewUrl = URL.createObjectURL(file.raw)
    return file.previewUrl
  }

  return ''
}

const buildAttachmentPreviewItems = () => {
  const existingImageAttachments = existingAttachments.value
    .filter((item) => isImageFile(item.file, item.name))
    .map((item) => ({
      key: `existing-${item.id}`,
      url: item.file,
    }))

  const uploadImageAttachments = uploadFileList.value
    .filter((item) => isImageFile(item.url, item.name, item.raw?.type))
    .map((item) => ({
      key: item.uid,
      url: getUploadFileUrl(item),
    }))

  return [...existingImageAttachments, ...uploadImageAttachments].filter((item) => item.url)
}

const openPreview = ({ images = [], currentIndex = 0 } = {}) => {
  previewImages.value = Array.isArray(images) ? images : []
  previewIndex.value = Number(currentIndex) || 0
  previewVisible.value = Boolean(previewImages.value.length)
}

const handlePreviewIndexChange = (nextIndex) => {
  previewIndex.value = nextIndex
}

const openExistingAttachmentPreview = (attachment) => {
  const previewItems = buildAttachmentPreviewItems()
  openPreview({
    images: previewItems.map((item) => item.url),
    currentIndex: Math.max(previewItems.findIndex((item) => item.key === `existing-${attachment.id}`), 0),
  })
}

const handleNewAttachmentPreview = (file) => {
  if (!isImageFile(file.url, file.name, file.raw?.type)) {
    if (file.url) {
      window.open(file.url, '_blank', 'noopener,noreferrer')
    }
    return
  }

  const previewItems = buildAttachmentPreviewItems()
  openPreview({
    images: previewItems.map((item) => item.url),
    currentIndex: Math.max(previewItems.findIndex((item) => item.key === file.uid), 0),
  })
}

const openAttachment = (url) => {
  if (!url) {
    return
  }

  window.open(url, '_blank', 'noopener,noreferrer')
}

const parseRawFields = () => {
  const text = normalizeText(form.raw_fields_text)
  if (!text) {
    return {}
  }

  try {
    const parsed = JSON.parse(text)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed
    }
  } catch (error) {
    throw new Error('扩展字段必须是合法 JSON 对象')
  }

  throw new Error('扩展字段必须是合法 JSON 对象')
}

const prepareRichTextHtml = async (html) => (
  replaceInlineImageDataUrls(html, async (files) => {
    const response = await uploadDefectRichTextImages(files)
    return response.data?.results || []
  })
)

const buildPayload = async () => ({
  version: normalizeText(form.version),
  issue_id: normalizeText(form.issue_id),
  issue_key: normalizeText(form.issue_key),
  issue_type: normalizeText(form.issue_type),
  summary: normalizeText(form.summary),
  description: await prepareRichTextHtml(form.description),
  module: normalizeText(form.module),
  customer_name: normalizeText(form.customer_name),
  priority: normalizeText(form.priority),
  status: normalizeText(form.status),
  creator: normalizeText(form.creator),
  handler: normalizeText(form.handler),
  tester: normalizeText(form.tester),
  group_name: normalizeText(form.group_name),
  frontend_developer: normalizeText(form.frontend_developer),
  backend_developer: normalizeText(form.backend_developer),
  related_mindmaps: serializeRequirementMindmaps(form.related_mindmaps),
  raw_fields: parseRawFields(),
  retain_attachment_ids: existingAttachments.value.map((item) => item.id),
  attachments: uploadFileList.value.map((item) => item.raw).filter(Boolean),
})

const handleSubmit = async () => {
  if (!formRef.value) {
    return
  }

  try {
    await formRef.value.validate()
    submitting.value = true

    const payload = await buildPayload()
    const response = isEdit.value
      ? await updateRequirementRecord(route.params.id, payload)
      : await createRequirementRecord(payload)

    ElMessage.success(isEdit.value ? '需求更新成功' : '需求创建成功')

    if (isEdit.value) {
      applyDetailData(response.data)
      activeTab.value = 'detail'
      return
    }

    const recordId = response.data?.id
    if (recordId) {
      router.push({
        path: `/manual-testcases/requirements/${recordId}/edit`,
        query: preservedQuery.value,
      })
      return
    }

    goBackToList()
  } catch (error) {
    if (error instanceof Error && error.message.includes('JSON')) {
      ElMessage.error(error.message)
      return
    }

    if (error?.response?.data) {
      const errorMessage = Object.values(error.response.data).flat().find(Boolean)
      ElMessage.error(errorMessage || '保存需求失败')
    } else if (error?.message) {
      ElMessage.error(error.message)
    }
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadVersionSummaries(), loadGroupOptions(), loadUsers(), loadModuleCategories()])
  await loadRequirement()
})

watch(
  () => route.params.id,
  async (nextId, previousId) => {
    if (String(nextId || '') === String(previousId || '')) {
      return
    }
    await loadRequirement()
  }
)

watch(
  () => route.query.project_id,
  async (nextProjectId, previousProjectId) => {
    if (String(getQueryValue(nextProjectId) || '') === String(getQueryValue(previousProjectId) || '')) {
      return
    }
    await loadModuleCategories()
  }
)

watch(
  () => form.module,
  () => {
    syncModuleCategorySelection()
  }
)

watch(
  () => normalizeText(form.issue_key),
  async (nextIssueKey, previousIssueKey) => {
    if (nextIssueKey === previousIssueKey) {
      return
    }

    if (!nextIssueKey) {
      resetMindmapOptionPool()
      return
    }

    await loadRelatedMindmapOptions('', { autoSelect: true })
  }
)

watch(
  currentUserDisplayName,
  (nextValue) => {
    if (!isEdit.value && !normalizeText(form.creator) && nextValue) {
      form.creator = nextValue
    }
  }
)

onBeforeUnmount(() => {
  cleanupUploadPreviewUrls()
})
</script>

<style scoped lang="scss">
.requirement-form-page {
  .header-title {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .page-subtitle {
    margin: 0;
    color: #606266;
    line-height: 1.6;
  }

  .header-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
}

.requirement-form-card {
  overflow: hidden;
}

.requirement-form-tabs {
  :deep(.el-tabs__content) {
    padding-top: 8px;
  }
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-selector {
  position: relative;
  width: 100%;
}

.module-selector__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 30;
  padding: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.14);
}

.module-selector__hint {
  margin-bottom: 10px;
  color: #909399;
  font-size: 12px;
  line-height: 1.6;
}

.module-selector__tree {
  max-height: 280px;
  overflow: auto;
}

.module-selector__empty {
  color: #909399;
  font-size: 13px;
  line-height: 1.7;
}

.rich-text-field {
  width: 100%;
}

.rich-text-tip {
  margin-bottom: 10px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.attachment-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafafa;
}

.attachment-item__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.attachment-item__name {
  color: #303133;
  word-break: break-all;
}

.attachment-item__time {
  color: #909399;
  font-size: 12px;
}

.attachment-item__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.attachment-upload {
  width: 100%;
}

.requirement-form-item--stacked {
  :deep(.el-form-item__content) {
    display: block;
  }
}
</style>
