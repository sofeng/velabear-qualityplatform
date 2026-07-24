<template>
  <div class="page-container defect-form-page">
    <div class="page-header">
      <div class="header-title">
        <h1 class="page-title">{{ isEdit ? '编辑技术方案设计' : '新建技术方案设计' }}</h1>
        <p v-if="contextText" class="page-subtitle">{{ contextText }}</p>
      </div>
      <div class="header-actions">
        <el-button v-if="isFromManualWorkspace" @click="goBackToManualWorkspace">返回思源研发管理</el-button>
        <el-button @click="goBackToList">返回列表</el-button>
        <el-button
          v-if="showSubmitAction"
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ isEdit ? '保存修改' : '创建技术方案设计' }}
        </el-button>
      </div>
    </div>

    <div v-loading="loading" class="card-container defect-form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-tabs v-model="activeTab" class="defect-form-tabs">
          <el-tab-pane label="方案详情" name="detail">
            <div class="tab-panel">
              <el-form-item label="方案标题" prop="title">
                <el-input
                  v-model="form.title"
                  maxlength="500"
                  show-word-limit
                  placeholder="请输入方案标题"
                />
              </el-form-item>

              <el-form-item label="方案描述" prop="description">
                <div class="rich-text-field">
                  <div class="rich-text-tip">
                    支持富文本、图片粘贴、工具栏插图；点击图片可全屏预览，预览时支持左右方向键切换。
                  </div>
                  <DefectRichTextEditor
                    v-model="form.description"
                    placeholder="请输入方案描述"
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

          <el-tab-pane label="方案设计" name="process">
            <div class="tab-panel">
              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="所属项目" prop="project_id">
                    <el-select
                      v-model="form.project_id"
                      filterable
                      clearable
                      placeholder="请选择项目"
                      style="width: 100%"
                      @change="handleProjectChange"
                    >
                      <el-option
                        v-for="project in projects"
                        :key="project.id"
                        :label="project.name"
                        :value="project.id"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="关联版本">
                    <el-select
                      v-model="form.version_id"
                      filterable
                      clearable
                      placeholder="可不选择"
                      style="width: 100%"
                      :disabled="!form.project_id"
                      @change="handleVersionChange"
                    >
                      <el-option
                        v-for="version in versions"
                        :key="version.id"
                        :label="version.name"
                        :value="version.id"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="8">
                  <el-form-item label="优先级" prop="priority">
                    <el-select v-model="form.priority" style="width: 100%">
                      <el-option
                        v-for="option in priorityOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="8">
                  <el-form-item label="复杂度" prop="severity">
                    <el-select v-model="form.severity" style="width: 100%">
                      <el-option
                        v-for="option in severityOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="8">
                  <el-form-item label="状态" prop="status">
                    <el-select v-model="form.status" style="width: 100%">
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

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="关联需求编号">
                    <el-select
                      v-model="form.requirement_id"
                      filterable
                      remote
                      clearable
                      reserve-keyword
                      :loading="jiraRequirementLoading"
                      placeholder="请输入 JIRA 编号或标题搜索"
                      style="width: 100%"
                      @visible-change="handleRequirementSelectorVisible"
                      @change="handleRequirementChange"
                      @clear="handleRequirementClear"
                      :remote-method="handleRequirementRemoteSearch"
                    >
                      <el-option
                        v-for="option in jiraRequirementOptions"
                        :key="option.issue_key"
                        :label="formatJiraRequirementOptionLabel(option)"
                        :value="option.issue_key"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="标签">
                    <el-input
                      v-model="form.labels_text"
                      clearable
                      placeholder="多个标签请用逗号分隔"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="前端方案负责人">
                    <el-input
                      v-model="form.frontend_developer"
                      clearable
                      placeholder="请输入前端方案负责人"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="后端方案负责人">
                    <el-input
                      v-model="form.backend_developer"
                      clearable
                      placeholder="请输入后端方案负责人"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :xs="24" :md="12">
                  <el-form-item label="设计背景">
                    <el-input
                      v-model="form.problem_reason"
                      type="textarea"
                      :autosize="{ minRows: 3, maxRows: 6 }"
                      placeholder="请输入设计背景"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="方案说明">
                    <el-input
                      v-model="form.root_cause"
                      type="textarea"
                      :autosize="{ minRows: 3, maxRows: 6 }"
                      placeholder="请输入方案说明"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="模块">
                <div class="module-selector">
                  <div class="module-selector__toolbar">
                    <el-input
                      v-model="moduleDraftValue"
                      clearable
                      :disabled="!form.project_id"
                      placeholder="可手动输入模块路径，例如：物业通 / 客户端 / 登录"
                      @keyup.enter="handleAddModuleFromInput"
                    >
                      <template #append>
                        <el-button :disabled="!form.project_id" @click="handleAddModuleFromInput">
                          添加
                        </el-button>
                      </template>
                    </el-input>
                    <el-popover
                      v-model:visible="moduleTreeVisible"
                      placement="bottom-start"
                      trigger="click"
                      :width="420"
                      @show="handleModuleSelectorOpen"
                    >
                      <template #reference>
                        <el-button :disabled="!form.project_id">
                          目录树选择
                        </el-button>
                      </template>
                      <div v-loading="moduleCategoryLoading" class="module-selector__dropdown">
                        <el-input
                          v-model="moduleTreeFilterText"
                          clearable
                          placeholder="搜索目录节点"
                          class="module-selector__search"
                        />
                        <el-tree
                          ref="moduleTreeRef"
                          :data="moduleCategoryTree"
                          node-key="id"
                          default-expand-all
                          :expand-on-click-node="false"
                          :highlight-current="false"
                          :filter-node-method="filterModuleTreeNode"
                          class="module-selector__tree"
                          @node-click="handleModuleTreeNodeClick"
                        >
                          <template #default="{ data }">
                            <div class="module-selector__tree-node">
                              <span>{{ data.label }}</span>
                              <span class="module-selector__tree-path">{{ data.fullPath }}</span>
                            </div>
                          </template>
                        </el-tree>
                        <el-empty
                          v-if="!moduleCategoryTree.length && !moduleCategoryLoading"
                          description="当前项目暂无目录树"
                        />
                      </div>
                    </el-popover>
                  </div>
                  <div v-if="form.modules.length" class="module-selector__tags">
                    <el-tag
                      v-for="item in form.modules"
                      :key="item.relation_key"
                      closable
                      effect="plain"
                      class="module-selector__tag"
                      @close="removeModuleRelationItem(item.relation_key)"
                    >
                      {{ item.path || item.short_label }}
                    </el-tag>
                  </div>
                  <div v-else class="module-selector__empty">暂无已选模块</div>
                </div>
              </el-form-item>

              <el-form-item label="关联测试用例">
                <el-select
                  v-model="form.related_testcases"
                  multiple
                  filterable
                  remote
                  reserve-keyword
                  value-key="relation_key"
                  collapse-tags
                  collapse-tags-tooltip
                  :loading="testcaseOptionsLoading"
                  :disabled="!form.project_id || !form.requirement_id"
                  placeholder="请先选择关联需求编号"
                  style="width: 100%"
                  @visible-change="(visible) => handleRelationSelectorVisible('case', visible)"
                  :remote-method="(keyword) => handleRelationRemoteSearch('case', keyword)"
                >
                  <el-option
                    v-for="option in testcaseOptions"
                    :key="option.relation_key"
                    :label="getRelationSelectorLabel(option, 'case')"
                    :value="option"
                  >
                    <div class="relation-option">
                      <span class="relation-option__title">{{ getRelationSelectorTitle(option, 'case') }}</span>
                      <span class="relation-option__meta">{{ option.path || option.mindmap_name || '-' }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="关联测试点">
                <el-select
                  v-model="form.related_testpoints"
                  multiple
                  filterable
                  remote
                  reserve-keyword
                  value-key="relation_key"
                  collapse-tags
                  collapse-tags-tooltip
                  :loading="testpointOptionsLoading"
                  :disabled="!form.project_id || !form.requirement_id"
                  placeholder="请先选择关联需求编号"
                  style="width: 100%"
                  @visible-change="(visible) => handleRelationSelectorVisible('testpoint', visible)"
                  :remote-method="(keyword) => handleRelationRemoteSearch('testpoint', keyword)"
                >
                  <el-option
                    v-for="option in testpointOptions"
                    :key="option.relation_key"
                    :label="getRelationSelectorLabel(option, 'testpoint')"
                    :value="option"
                  >
                    <div class="relation-option">
                      <span class="relation-option__title">{{ getRelationSelectorTitle(option, 'testpoint') }}</span>
                      <span class="relation-option__meta">{{ option.path || option.mindmap_name || '-' }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="负责人">
                <el-select
                  v-model="form.assignee_ids"
                  multiple
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="请选择负责人"
                  style="width: 100%"
                >
                  <el-option
                    v-for="user in users"
                    :key="user.id"
                    :label="getUserDisplayName(user, `用户${user.id}`)"
                    :value="user.id"
                  />
                </el-select>
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="评论信息" name="comments">
            <div class="tab-panel">
              <div class="tab-card">
                <div class="tab-card__title">添加评论</div>
                <DefectRichTextEditor
                  v-model="commentContent"
                  placeholder="请输入评论内容"
                  :min-height="220"
                  @preview-images="openPreview"
                />
                <div class="tab-card__actions">
                  <el-button type="primary" :loading="commentSubmitting" @click="handleCommentSubmit">
                    发布评论
                  </el-button>
                </div>
              </div>

              <div class="tab-card">
                <div class="tab-card__title">评论记录</div>
                <div v-if="comments.length" class="comment-list">
                  <div v-for="comment in comments" :key="comment.id" class="comment-item">
                    <div class="comment-item__head">
                      <div class="comment-item__meta">
                        <strong>{{ getUserDisplayName(comment.author, '-') }}</strong>
                        <span>{{ formatDate(comment.created_at) }}</span>
                      </div>
                      <div v-if="canEditComment(comment)" class="comment-item__actions">
                        <el-button link type="primary" @click="startEditingComment(comment)">
                          编辑
                        </el-button>
                      </div>
                    </div>
                    <div v-if="editingCommentId === comment.id" class="comment-edit-panel">
                      <DefectRichTextEditor
                        v-model="editingCommentContent"
                        placeholder="请输入评论内容"
                        :min-height="180"
                        @preview-images="openPreview"
                      />
                      <div class="comment-edit-panel__actions">
                        <el-button @click="cancelEditingComment">取消</el-button>
                        <el-button
                          type="primary"
                          :loading="editingCommentSubmitting"
                          @click="handleCommentEditSubmit(comment)"
                        >
                          保存
                        </el-button>
                      </div>
                    </div>
                    <DefectRichTextContent v-else :html="comment.content" empty-text="-" />
                  </div>
                </div>
                <el-empty v-else description="暂无评论" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="变更记录" name="history">
            <div class="tab-panel">
              <el-table :data="historyRecords" border stripe empty-text="暂无变更记录">
                <el-table-column label="变更时间" width="180">
                  <template #default="{ row }">
                    {{ formatDate(row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="变更人" width="140">
                  <template #default="{ row }">
                    {{ getUserDisplayName(row.changed_by, '-') }}
                  </template>
                </el-table-column>
                <el-table-column label="字段" width="140">
                  <template #default="{ row }">
                    {{ getHistoryFieldText(row.field) }}
                  </template>
                </el-table-column>
                <el-table-column label="动作" width="120">
                  <template #default="{ row }">
                    {{ getHistoryActionText(row.action) }}
                  </template>
                </el-table-column>
                <el-table-column label="变更详情" min-width="260" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ formatHistoryDetail(row) }}
                  </template>
                </el-table-column>
              </el-table>
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
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'
import DefectRichTextEditor from '@/components/defects/DefectRichTextEditor.vue'
import DefectRichTextContent from '@/components/defects/DefectRichTextContent.vue'
import ImagePreviewViewer from '@/components/defects/ImagePreviewViewer.vue'
import {
  addTechnicalSolutionDesignComment,
  createTechnicalSolutionDesign,
  getManualCategories,
  getTechnicalSolutionDesignDetail,
  searchJiraRequirementRecords,
  searchManualMindmapNodes,
  updateTechnicalSolutionDesign,
  updateTechnicalSolutionDesignComment,
  uploadTechnicalSolutionDesignRichTextImages,
} from '@/api/technicalSolutionDesigns'
import { hasRichTextContent, replaceInlineImageDataUrls } from '@/utils/defectRichText'
import { getUserDisplayName } from '@/utils/userDisplay'
import {
  decorateDefectRelationItem,
  ensureUniqueDefectRelationItems,
  serializeDefectRelationItems,
} from '@/utils/defectRelations'

const DEFAULT_DESCRIPTION_SECTIONS = [
  '【版本号】',
  '',
  '【设计背景】',
  '',
  '【业务目标】',
  '',
  '【方案概述】',
  '',
  '【技术实现】',
  '',
  '【影响范围】',
  '',
  '【风险与验证】',
]

const severityOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '关键', value: 'critical' },
]

const priorityOptions = [
  { label: 'P1', value: 'P1' },
  { label: 'P2', value: 'P2' },
  { label: 'P3', value: 'P3' },
  { label: 'P4', value: 'P4' },
]

const statusOptions = [
  { label: '草稿', value: 'new' },
  { label: '设计中', value: 'in_progress' },
  { label: '已评审', value: 'resolved' },
  { label: '已驳回', value: 'rejected' },
  { label: '已归档', value: 'closed' },
  { label: '重新设计', value: 'reopened' },
  { label: '作废', value: 'invalid' },
]

const historyActionMap = {
  create: '创建',
  update: '更新',
  status: '状态变更',
  assign: '指派',
  comment: '评论',
  attachment: '附件',
}

const historyFieldMap = {
  defect: '技术方案设计',
  technical_solution_design: '技术方案设计',
  project: '项目',
  version: '版本',
  title: '标题',
  description: '描述',
  problem_reason: '设计背景',
  root_cause: '方案说明',
  frontend_developer: '前端方案负责人',
  backend_developer: '后端方案负责人',
  priority: '优先级',
  severity: '复杂度',
  status: '状态',
  requirement_id: '关联需求编号',
  modules: '模块',
  related_testcases: '关联测试用例',
  related_testpoints: '关联测试点',
  labels: '标签',
  assignees: '负责人',
  attachments: '附件',
  comment: '评论',
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const submitting = ref(false)
const commentSubmitting = ref(false)
const editingCommentSubmitting = ref(false)
const activeTab = ref('detail')

const projects = ref([])
const versions = ref([])
const users = ref([])
const comments = ref([])
const historyRecords = ref([])
const existingAttachments = ref([])
const uploadFileList = ref([])
const commentContent = ref('')
const editingCommentId = ref(null)
const editingCommentContent = ref('')

const jiraRequirementLoading = ref(false)
const jiraRequirementOptions = ref([])
const moduleCategoryLoading = ref(false)
const moduleCategoryTree = ref([])
const moduleTreeVisible = ref(false)
const moduleDraftValue = ref('')
const moduleTreeFilterText = ref('')
const moduleTreeRef = ref(null)
const testcaseOptionsLoading = ref(false)
const testcaseOptions = ref([])
const testpointOptionsLoading = ref(false)
const testpointOptions = ref([])

const previewVisible = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

const form = reactive({
  project_id: null,
  version_id: null,
  title: '',
  description: '',
  problem_reason: '',
  root_cause: '',
  frontend_developer: '',
  backend_developer: '',
  priority: 'P3',
  severity: 'medium',
  status: 'new',
  requirement_id: '',
  modules: [],
  related_testcases: [],
  related_testpoints: [],
  labels_text: '',
  assignee_ids: [],
})

const getQueryValue = (value) => (Array.isArray(value) ? value[0] : value)

const parseNumberQuery = (value, fallback = null) => {
  const normalized = getQueryValue(value)
  if (normalized === undefined || normalized === null || normalized === '') {
    return fallback
  }

  const parsed = Number(normalized)
  return Number.isNaN(parsed) ? fallback : parsed
}

const normalizeListResponse = (data) => (Array.isArray(data) ? data : data?.results || [])

const isEdit = computed(() => Boolean(route.params.id))
const isFromManualWorkspace = computed(() => getQueryValue(route.query.source) === 'manual-testcases')
const showSubmitAction = computed(() => !isEdit.value || ['detail', 'process'].includes(activeTab.value))

const selectedProjectName = computed(() => {
  const matchedProject = projects.value.find((item) => String(item.id) === String(form.project_id))
  return matchedProject?.name || ''
})

const selectedVersionName = computed(() => {
  const matchedVersion = versions.value.find((item) => String(item.id) === String(form.version_id))
  return matchedVersion?.name || ''
})

const sourceContext = computed(() => ({
  tabName: String(getQueryValue(route.query.source_tab_name) || ''),
  mindmapId: parseNumberQuery(route.query.source_mindmap_id),
  nodeId: String(getQueryValue(route.query.source_node_id) || ''),
  mindmapName: String(getQueryValue(route.query.source_mindmap) || ''),
  sourceName: String(getQueryValue(route.query.source_name) || ''),
  parentName: String(getQueryValue(route.query.source_parent_name) || ''),
  path: String(getQueryValue(route.query.source_path) || ''),
  moduleName: String(getQueryValue(route.query.source_module) || ''),
  modulePath: String(getQueryValue(route.query.source_module_path) || ''),
  caseId: String(getQueryValue(route.query.source_case_id) || ''),
  responsibilityGroup: String(getQueryValue(route.query.source_responsibility_group) || ''),
  frontendOwner: String(getQueryValue(route.query.source_frontend_owner) || ''),
  backendOwner: String(getQueryValue(route.query.source_backend_owner) || ''),
}))

const buildSourceContextText = (source = {}) => {
  const parts = [source.tabName, source.mindmapName, source.sourceName].filter(Boolean)
  return parts.length ? `来源：${parts.join(' / ')}` : ''
}

const contextText = computed(() => {
  const parts = []

  if (selectedProjectName.value) {
    parts.push(`当前上下文项目：${selectedProjectName.value}`)
  }
  if (selectedVersionName.value) {
    parts.push(`版本：${selectedVersionName.value}`)
  }

  const sourceText = buildSourceContextText(sourceContext.value)
  if (sourceText) {
    parts.push(sourceText)
  }

  return parts.join(' / ')
})

const manualWorkspaceQuery = computed(() => {
  const query = {}
  const projectId = form.project_id || parseNumberQuery(route.query.project_id)
  const versionId = form.version_id || parseNumberQuery(route.query.version_id)
  const tab = String(getQueryValue(route.query.tab) || '')
  const testpointId = String(getQueryValue(route.query.testpoint_id) || '')

  if (projectId) {
    query.project_id = String(projectId)
  }
  if (versionId) {
    query.version_id = String(versionId)
  }
  if (tab) {
    query.tab = tab
  }
  if (tab === 'technical-solution-designs' && testpointId) {
    query.technical_solution_design_testpoint_id = testpointId
  }

  return query
})

const validateDescription = (_rule, value, callback) => {
  if (!hasRichTextContent(value)) {
    callback(new Error('请输入方案描述'))
    return
  }

  callback()
}

const rules = {
  project_id: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  title: [{ required: true, message: '请输入方案标题', trigger: 'blur' }],
  description: [{ validator: validateDescription, trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  severity: [{ required: true, message: '请选择复杂度', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const parseLabels = (value) =>
  String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

const buildSourceDescriptionLines = (source = {}) => {
  const lines = []

  if (!buildSourceContextText(source)) {
    return lines
  }

  lines.push('【来源信息】')
  lines.push(`来源页签：${source.tabName}`)

  if (source.mindmapName) {
    lines.push(`所属脑图：${source.mindmapName}`)
  }
  if (source.sourceName) {
    lines.push(`来源节点：${source.sourceName}`)
  }
  if (source.parentName) {
    lines.push(`父节点：${source.parentName}`)
  }
  if (source.path) {
    lines.push(`节点路径：${source.path}`)
  }
  if (source.moduleName) {
    lines.push(`所属模块：${source.moduleName}`)
  }
  if (source.caseId) {
    lines.push(`用例编号：${source.caseId}`)
  }
  if (source.responsibilityGroup) {
    lines.push(`组别：${source.responsibilityGroup}`)
  }
  if (source.frontendOwner) {
    lines.push(`前端方案负责人：${source.frontendOwner}`)
  }
  if (source.backendOwner) {
    lines.push(`后端方案负责人：${source.backendOwner}`)
  }

  lines.push('')
  return lines
}

const buildDefaultDescription = (versionName = '', source = null) => {
  const descriptionLines = []
  const sourceLines = buildSourceDescriptionLines(source || {})

  if (sourceLines.length) {
    descriptionLines.push(...sourceLines)
  }

  const sections = [...DEFAULT_DESCRIPTION_SECTIONS]
  if (versionName) {
    sections[0] = `【版本号】${versionName}`
  }
  descriptionLines.push(...sections)

  return descriptionLines
    .map((line) => `<p>${line || '<br>'}</p>`)
    .join('')
}

const formatDate = (value) => (value ? dayjs(value).format('YYYY/MM/DD HH:mm:ss') : '-')
const getHistoryActionText = (value) => historyActionMap[value] || value || '-'
const getHistoryFieldText = (value) => historyFieldMap[value] || value || '-'

const formatHistoryValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  if (Array.isArray(value)) {
    const normalizedValues = value
      .map((item) => {
        if (item === null || item === undefined || item === '') {
          return ''
        }

        if (typeof item === 'object') {
          return item.path || item.node_text || JSON.stringify(item)
        }

        return String(item)
      })
      .filter(Boolean)

    return normalizedValues.length ? normalizedValues.join('、') : '-'
  }

  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, currentValue]) => `${key}：${formatHistoryValue(currentValue)}`)
      .join('；')
  }

  return String(value)
}

const formatHistoryDetail = (row) => {
  if (row.field === 'description') {
    return '描述内容已更新'
  }

  if (row.field === 'comment') {
    return row.action === 'update' ? '评论内容已更新' : '新增评论'
  }

  if (row.field === 'attachments') {
    return formatHistoryValue(row.to_value || row.from_value)
  }

  if (row.action === 'create') {
    return '技术方案设计已创建'
  }

  return `由 ${formatHistoryValue(row.from_value)} 变更为 ${formatHistoryValue(row.to_value)}`
}

const openPreview = ({ images = [], currentIndex = 0 } = {}) => {
  if (!images.length) {
    return
  }

  previewImages.value = images
  previewIndex.value = currentIndex
  previewVisible.value = true
}

const handlePreviewIndexChange = (nextIndex) => {
  previewIndex.value = nextIndex
}

const goBackToList = () => {
  const query = {
    tab: 'technical-solution-designs',
  }

  const projectId = form.project_id || parseNumberQuery(route.query.project_id)
  const versionId = form.version_id || parseNumberQuery(route.query.version_id)
  const categoryId = parseNumberQuery(route.query.category_id)
  const currentTab = String(getQueryValue(route.query.tab) || '')

  if (projectId) {
    query.project_id = String(projectId)
  }
  if (versionId) {
    query.version_id = String(versionId)
  }
  if (categoryId) {
    query.category_id = String(categoryId)
  }
  if (currentTab === 'technical-solution-designs' && getQueryValue(route.query.testpoint_id)) {
    query.technical_solution_design_testpoint_id = String(getQueryValue(route.query.testpoint_id))
  }

  router.push({
    path: '/manual-testcases/list',
    query,
  })
}

const goBackToManualWorkspace = () => {
  router.push({
    path: '/manual-testcases/list',
    query: manualWorkspaceQuery.value,
  })
}

const ensureJiraRequirementOption = (option = {}) => {
  const issueKey = String(option.issue_key || '').trim()
  if (!issueKey) {
    return
  }

  const optionMap = new Map(jiraRequirementOptions.value.map((item) => [item.issue_key, item]))
  optionMap.set(issueKey, {
    issue_key: issueKey,
    summary: String(option.summary || '').trim(),
    version: String(option.version || '').trim(),
  })
  jiraRequirementOptions.value = [...optionMap.values()]
}

const resetRelationOptionPools = () => {
  jiraRequirementOptions.value = form.requirement_id
    ? [{ issue_key: form.requirement_id, summary: '', version: '' }]
    : []
  testcaseOptions.value = ensureUniqueDefectRelationItems(form.related_testcases, 'case')
  testpointOptions.value = ensureUniqueDefectRelationItems(form.related_testpoints, 'testpoint')
}

const formatJiraRequirementOptionLabel = (option = {}) => {
  const issueKey = String(option.issue_key || '').trim()
  const summary = String(option.summary || '').trim()
  return summary ? `${issueKey} - ${summary}` : issueKey || '-'
}

const normalizePathText = (value = '') =>
  String(value || '')
    .split('/')
    .map((item) => item.trim())
    .filter(Boolean)
    .join(' / ')

const normalizeModuleCategoryTree = (categories = [], parentPath = []) =>
  (Array.isArray(categories) ? categories : []).map((category) => {
    const label = String(category?.name || '').trim()
    const currentPath = [...parentPath, label].filter(Boolean)
    return {
      id: category?.id,
      label,
      fullPath: currentPath.join(' / '),
      children: normalizeModuleCategoryTree(category?.children || [], currentPath),
    }
  })

const filterModuleTreeNode = (keyword, data) => {
  const normalizedKeyword = String(keyword || '').trim().toLowerCase()
  if (!normalizedKeyword) {
    return true
  }

  return [data?.label, data?.fullPath].some((value) =>
    String(value || '').toLowerCase().includes(normalizedKeyword)
  )
}

const buildModuleRelationItem = (value = '') => {
  const normalizedPath = normalizePathText(value)
  if (!normalizedPath) {
    return null
  }

  const pathSegments = normalizedPath
    .split(' / ')
    .map((item) => item.trim())
    .filter(Boolean)

  return decorateDefectRelationItem(
    {
      node_text: pathSegments[pathSegments.length - 1] || normalizedPath,
      node_type: 'module',
      path: normalizedPath,
      parent_text: pathSegments.length > 1 ? pathSegments[pathSegments.length - 2] : '',
    },
    'module',
  )
}

const addModuleRelationItem = (item) => {
  const nextItem = decorateDefectRelationItem(item, 'module')
  if (!nextItem) {
    return false
  }

  form.modules = ensureUniqueDefectRelationItems([...form.modules, nextItem], 'module')
  return true
}

const getRelationSelectorTitle = (item = {}, nodeType = '') => {
  if (nodeType === 'case' || nodeType === 'testpoint') {
    return String(item?.node_text || item?.short_label || item?.option_label || '-')
  }
  return String(item?.path || item?.option_label || item?.short_label || '-')
}

const getRelationSelectorLabel = (item = {}, nodeType = '') => {
  return getRelationSelectorTitle(item, nodeType)
}

const loadProjects = async () => {
  try {
    const response = await api.get('/projects/list/')
    projects.value = response.data?.results || response.data || []
  } catch (error) {
    projects.value = []
    ElMessage.error('获取项目列表失败')
  }
}

const loadVersions = async (projectId) => {
  if (!projectId) {
    versions.value = []
    return
  }

  try {
    const response = await api.get(`/versions/projects/${projectId}/versions/`)
    versions.value = response.data || []
  } catch (error) {
    versions.value = []
    ElMessage.error('获取版本列表失败')
  }
}

const loadUsers = async () => {
  try {
    const response = await api.get('/auth/users/', {
      params: { page_size: 500 },
    })
    users.value = response.data?.results || response.data || []
  } catch (error) {
    users.value = []
    ElMessage.error('获取用户列表失败')
  }
}

const loadModuleCategories = async (projectId = form.project_id) => {
  if (!projectId) {
    moduleCategoryTree.value = []
    moduleTreeVisible.value = false
    return
  }

  moduleCategoryLoading.value = true
  try {
    const response = await getManualCategories({ project: projectId })
    moduleCategoryTree.value = normalizeModuleCategoryTree(normalizeListResponse(response.data))
  } catch (error) {
    moduleCategoryTree.value = []
    ElMessage.error('获取当前项目目录树失败')
  } finally {
    moduleCategoryLoading.value = false
  }
}

const loadJiraRequirementOptions = async (keyword = '') => {
  const effectiveKeyword = String(keyword || form.requirement_id || '').trim()
  if (!selectedVersionName.value && !effectiveKeyword) {
    resetRelationOptionPools()
    return
  }

  jiraRequirementLoading.value = true
  try {
    const params = {}
    if (selectedVersionName.value) {
      params.version = selectedVersionName.value
    }
    if (effectiveKeyword) {
      params.keyword = effectiveKeyword
    }

    const response = await searchJiraRequirementRecords(params)
    normalizeListResponse(response.data).forEach((item) => ensureJiraRequirementOption(item))
    if (form.requirement_id) {
      ensureJiraRequirementOption({ issue_key: form.requirement_id })
    }
  } catch (error) {
    ElMessage.error('获取 JIRA 需求数据失败')
  } finally {
    jiraRequirementLoading.value = false
  }
}

const getRelationState = (nodeType) => {
  if (nodeType === 'case') {
    return {
      loadingRef: testcaseOptionsLoading,
      optionsRef: testcaseOptions,
      selectedItems: () => form.related_testcases,
    }
  }

  return {
    loadingRef: testpointOptionsLoading,
    optionsRef: testpointOptions,
    selectedItems: () => form.related_testpoints,
  }
}

const loadRelationOptions = async (nodeType, keyword = '') => {
  const relationState = getRelationState(nodeType)
  const isRequirementScoped = nodeType === 'case' || nodeType === 'testpoint'
  if (!form.project_id || (isRequirementScoped && !form.requirement_id)) {
    relationState.optionsRef.value = ensureUniqueDefectRelationItems(relationState.selectedItems(), nodeType)
    return
  }

  relationState.loadingRef.value = true
  try {
    const searchKeyword = String(keyword || '').trim()
    const pageSize = 100
    let page = 1
    let totalCount = 0
    const nextOptions = []

    do {
      const params = {
        project: form.project_id,
        node_type: nodeType,
        page,
        page_size: pageSize,
      }

      if (form.version_id) {
        params.version = form.version_id
      }
      if (isRequirementScoped) {
        params.requirement_key = form.requirement_id
      }
      if (searchKeyword) {
        params.search = searchKeyword
      }

      const response = await searchManualMindmapNodes(params)
      const pageItems = normalizeListResponse(response.data)
      nextOptions.push(...pageItems)
      totalCount = Number(response.data?.count || pageItems.length || 0)
      page += 1
    } while ((page - 1) * pageSize < totalCount)

    relationState.optionsRef.value = ensureUniqueDefectRelationItems(
      [...relationState.selectedItems(), ...nextOptions],
      nodeType,
    )
  } catch (error) {
    ElMessage.error('获取关联节点失败')
  } finally {
    relationState.loadingRef.value = false
  }
}

const handleRequirementSelectorVisible = async (visible) => {
  if (!visible) {
    return
  }

  await loadJiraRequirementOptions()
}

const handleRequirementRemoteSearch = async (keyword) => {
  await loadJiraRequirementOptions(keyword)
}

const handleRequirementChange = async () => {
  form.related_testcases = []
  form.related_testpoints = []
  resetRelationOptionPools()

  if (!form.requirement_id) {
    return
  }

  ensureJiraRequirementOption({ issue_key: form.requirement_id })
  await Promise.all([
    loadRelationOptions('case'),
    loadRelationOptions('testpoint'),
  ])
}

const handleRequirementClear = () => {
  jiraRequirementOptions.value = []
  form.related_testcases = []
  form.related_testpoints = []
  resetRelationOptionPools()
}

const handleRelationSelectorVisible = async (nodeType, visible) => {
  if (!visible) {
    return
  }

  await loadRelationOptions(nodeType)
}

const handleRelationRemoteSearch = async (nodeType, keyword) => {
  await loadRelationOptions(nodeType, keyword)
}

const handleModuleSelectorOpen = async () => {
  moduleTreeVisible.value = true
  if (!moduleCategoryTree.value.length && form.project_id) {
    await loadModuleCategories(form.project_id)
  }
}

const handleAddModuleFromInput = () => {
  if (!form.project_id) {
    return
  }

  if (addModuleRelationItem(buildModuleRelationItem(moduleDraftValue.value))) {
    moduleDraftValue.value = ''
  }
}

const handleModuleTreeNodeClick = (node) => {
  if (addModuleRelationItem(buildModuleRelationItem(node?.fullPath || node?.label || ''))) {
    moduleTreeVisible.value = false
  }
}

const removeModuleRelationItem = (relationKey) => {
  form.modules = form.modules.filter((item) => item.relation_key !== relationKey)
}

const buildPathText = (...parts) => parts.filter(Boolean).join(' / ')

const buildSourceModuleRelationItem = (source) => {
  if (!source.moduleName) {
    return null
  }

  const sourcePathParts = String(source.path || '')
    .split(' / ')
    .map((item) => item.trim())
    .filter(Boolean)

  let modulePath = String(source.modulePath || '').trim()
  if (!modulePath && sourcePathParts.length) {
    if (source.tabName === '测试用例' && sourcePathParts.length >= 2) {
      modulePath = sourcePathParts.slice(0, -1).join(' / ')
    } else if (['测试点', '自测测试点'].includes(source.tabName) && sourcePathParts.length >= 2) {
      modulePath = source.parentName && source.parentName !== source.moduleName && sourcePathParts.length > 2
        ? sourcePathParts.slice(0, -2).join(' / ')
        : sourcePathParts.slice(0, -1).join(' / ')
    }
  }

  return decorateDefectRelationItem(
    {
      mindmap_id: source.mindmapId,
      mindmap_name: source.mindmapName,
      node_text: source.moduleName,
      node_type: 'module',
      path: modulePath || buildPathText(source.mindmapName, source.moduleName),
      responsibility_group: source.responsibilityGroup,
    },
    'module',
  )
}

const buildSourceNodeRelationItem = (source, nodeType) => {
  const nodeText = nodeType === 'testpoint' ? source.sourceName : source.sourceName
  if (!nodeText) {
    return null
  }

  const path =
    source.path ||
    buildPathText(
      source.mindmapName,
      source.moduleName || source.parentName,
      nodeText,
    )

  return decorateDefectRelationItem(
    {
      id: source.nodeId,
      mindmap_id: source.mindmapId,
      mindmap_name: source.mindmapName,
      node_text: nodeText,
      node_type: nodeType,
      path,
      parent_text: source.parentName || source.moduleName,
      case_id: source.caseId,
      responsibility_group: source.responsibilityGroup,
    },
    nodeType,
  )
}

const applySourceDefaultRelations = () => {
  const modules = []
  const relatedTestcases = []
  const relatedTestpoints = []

  const sourceModule = buildSourceModuleRelationItem(sourceContext.value)
  if (sourceModule) {
    modules.push(sourceModule)
  }

  if (sourceContext.value.tabName === '测试用例') {
    const relationItem = buildSourceNodeRelationItem(sourceContext.value, 'case')
    if (relationItem) {
      relatedTestcases.push(relationItem)
    }
  }

  if (['测试点', '自测测试点'].includes(sourceContext.value.tabName)) {
    const relationItem = buildSourceNodeRelationItem(sourceContext.value, 'testpoint')
    if (relationItem) {
      relatedTestpoints.push(relationItem)
    }
  }

  form.modules = ensureUniqueDefectRelationItems([...form.modules, ...modules], 'module')
  form.related_testcases = ensureUniqueDefectRelationItems([...form.related_testcases, ...relatedTestcases], 'case')
  form.related_testpoints = ensureUniqueDefectRelationItems([...form.related_testpoints, ...relatedTestpoints], 'testpoint')

  resetRelationOptionPools()
}

const applyCreateDefaultsFromQuery = async () => {
  if (isEdit.value) {
    return
  }

  const projectId = parseNumberQuery(route.query.project_id)
  const versionId = parseNumberQuery(route.query.version_id)
  const title = String(getQueryValue(route.query.title) || '')
  const requirementId = String(getQueryValue(route.query.requirement_id) || '')

  if (projectId) {
    form.project_id = projectId
    await loadVersions(projectId)
    await loadModuleCategories(projectId)
  }

  if (versionId) {
    form.version_id = versionId
  }

  if (title) {
    form.title = title
  }

  if (requirementId) {
    form.requirement_id = requirementId
    ensureJiraRequirementOption({ issue_key: requirementId })
    await Promise.all([
      loadRelationOptions('case'),
      loadRelationOptions('testpoint'),
    ])
  }

  applySourceDefaultRelations()

  if (!form.frontend_developer && sourceContext.value.frontendOwner) {
    form.frontend_developer = sourceContext.value.frontendOwner
  }
  if (!form.backend_developer && sourceContext.value.backendOwner) {
    form.backend_developer = sourceContext.value.backendOwner
  }

  if (!hasRichTextContent(form.description)) {
    form.description = buildDefaultDescription(selectedVersionName.value, sourceContext.value)
  }
}

const applyDetailData = async (detail) => {
  form.project_id = detail.project?.id || null
  await loadVersions(form.project_id)
  await loadModuleCategories(form.project_id)
  form.version_id = detail.version?.id || null
  form.title = detail.title || ''
  form.description = detail.description || ''
  form.problem_reason = detail.problem_reason || ''
  form.root_cause = detail.root_cause || ''
  form.frontend_developer = detail.frontend_developer || ''
  form.backend_developer = detail.backend_developer || ''
  form.priority = detail.priority || 'P3'
  form.severity = detail.severity || 'medium'
  form.status = detail.status || 'new'
  form.requirement_id = detail.requirement_id || ''
  form.modules = ensureUniqueDefectRelationItems(detail.modules || [], 'module')
  form.related_testcases = ensureUniqueDefectRelationItems(detail.related_testcases || [], 'case')
  form.related_testpoints = ensureUniqueDefectRelationItems(detail.related_testpoints || [], 'testpoint')
  form.labels_text = Array.isArray(detail.labels) ? detail.labels.join(', ') : ''
  form.assignee_ids = Array.isArray(detail.assignees) ? detail.assignees.map((item) => item.id) : []

  existingAttachments.value = detail.attachments || []
  uploadFileList.value = []
  comments.value = detail.comments || []
  historyRecords.value = detail.history_records || []

  resetRelationOptionPools()
  if (form.requirement_id) {
    ensureJiraRequirementOption({ issue_key: form.requirement_id })
    await loadJiraRequirementOptions(form.requirement_id)
    await Promise.all([
      loadRelationOptions('case'),
      loadRelationOptions('testpoint'),
    ])
  }

  cancelEditingComment()
}

const loadDefect = async () => {
  if (!isEdit.value) {
    return
  }

  loading.value = true
  try {
    const response = await getTechnicalSolutionDesignDetail(route.params.id)
    await applyDetailData(response.data)
  } catch (error) {
    ElMessage.error('获取方案详情失败')
    goBackToList()
  } finally {
    loading.value = false
  }
}

const handleProjectChange = async (projectId) => {
  form.version_id = null
  form.modules = []
  form.related_testcases = []
  form.related_testpoints = []
  moduleDraftValue.value = ''
  moduleTreeFilterText.value = ''
  moduleTreeVisible.value = false
  await loadVersions(projectId)
  await loadModuleCategories(projectId)
  resetRelationOptionPools()
}

const handleVersionChange = async () => {
  resetRelationOptionPools()
  if (form.requirement_id) {
    ensureJiraRequirementOption({ issue_key: form.requirement_id })
    await loadJiraRequirementOptions(form.requirement_id)
  }
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

const prepareRichTextHtml = async (html) =>
  replaceInlineImageDataUrls(html, async (files) => {
    const response = await uploadTechnicalSolutionDesignRichTextImages(files)
    return response.data?.results || []
  })

const canEditComment = (comment) =>
  Boolean(userStore.user?.id) && String(comment?.author?.id || '') === String(userStore.user?.id)

const startEditingComment = (comment) => {
  editingCommentId.value = comment?.id || null
  editingCommentContent.value = comment?.content || ''
}

const cancelEditingComment = () => {
  editingCommentId.value = null
  editingCommentContent.value = ''
}

const buildPayload = async () => ({
  project_id: form.project_id,
  version_id: form.version_id || null,
  title: form.title.trim(),
  description: await prepareRichTextHtml(form.description),
  problem_reason: form.problem_reason.trim(),
  root_cause: form.root_cause.trim(),
  frontend_developer: form.frontend_developer.trim(),
  backend_developer: form.backend_developer.trim(),
  priority: form.priority,
  severity: form.severity,
  status: form.status,
  requirement_id: form.requirement_id.trim(),
  modules: serializeDefectRelationItems(form.modules, 'module'),
  related_testcases: serializeDefectRelationItems(form.related_testcases, 'case'),
  related_testpoints: serializeDefectRelationItems(form.related_testpoints, 'testpoint'),
  labels: parseLabels(form.labels_text),
  assignee_ids: [...form.assignee_ids],
  retain_attachment_ids: existingAttachments.value.map((item) => item.id),
  attachments: uploadFileList.value.map((item) => item.raw).filter(Boolean),
})

const handleCommentSubmit = async () => {
  if (!isEdit.value) {
    return
  }

  if (!hasRichTextContent(commentContent.value)) {
    ElMessage.warning('请输入评论内容')
    return
  }

  commentSubmitting.value = true
  try {
    const preparedCommentContent = await prepareRichTextHtml(commentContent.value)
    await addTechnicalSolutionDesignComment(route.params.id, preparedCommentContent)
    commentContent.value = ''
    ElMessage.success('评论已发布')
    await loadDefect()
  } catch (error) {
    ElMessage.error('发布评论失败')
  } finally {
    commentSubmitting.value = false
  }
}

const handleCommentEditSubmit = async (comment) => {
  if (!isEdit.value || !comment?.id) {
    return
  }

  if (!hasRichTextContent(editingCommentContent.value)) {
    ElMessage.warning('请输入评论内容')
    return
  }

  editingCommentSubmitting.value = true
  try {
    const preparedCommentContent = await prepareRichTextHtml(editingCommentContent.value)
    await updateTechnicalSolutionDesignComment(route.params.id, comment.id, preparedCommentContent)
    cancelEditingComment()
    ElMessage.success('评论更新成功')
    await loadDefect()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '更新评论失败')
  } finally {
    editingCommentSubmitting.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) {
    return
  }

  try {
    await formRef.value.validate()
    submitting.value = true

    const payload = await buildPayload()
    const response = isEdit.value
      ? await updateTechnicalSolutionDesign(route.params.id, payload)
      : await createTechnicalSolutionDesign(payload)

    ElMessage.success(isEdit.value ? '技术方案设计更新成功' : '技术方案设计创建成功')

    if (isEdit.value) {
      await applyDetailData(response.data)
      activeTab.value = 'detail'
      return
    }

    goBackToList()
  } catch (error) {
    if (error?.response?.data) {
      const errorMessage = Object.values(error.response.data).flat().find(Boolean)
      ElMessage.error(errorMessage || '保存技术方案设计失败')
    } else if (error?.message) {
      ElMessage.error(error.message)
    }
  } finally {
    submitting.value = false
  }
}

watch(moduleTreeFilterText, (value) => {
  moduleTreeRef.value?.filter(value)
})

onMounted(async () => {
  await Promise.all([loadProjects(), loadUsers()])

  if (isEdit.value) {
    await loadDefect()
    return
  }

  await applyCreateDefaultsFromQuery()
})

onBeforeUnmount(() => {
  uploadFileList.value.forEach((item) => {
    if (item?.previewUrl) {
      URL.revokeObjectURL(item.previewUrl)
    }
  })
})
</script>

<style scoped lang="scss">
.defect-form-page {
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

.defect-form-card {
  overflow: hidden;
}

.defect-form-tabs {
  :deep(.el-tabs__content) {
    padding-top: 8px;
  }
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.module-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.module-selector__toolbar {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.module-selector__toolbar .el-input {
  flex: 1;
}

.module-selector__dropdown {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}

.module-selector__search {
  width: 100%;
}

.module-selector__tree {
  max-height: 320px;
  overflow: auto;
  padding-right: 4px;
}

.module-selector__tree-node {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  padding: 2px 0;
}

.module-selector__tree-path {
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-all;
}

.module-selector__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-selector__tag {
  max-width: 100%;
}

.module-selector__empty {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.relation-option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
}

.relation-option__title {
  color: #303133;
  line-height: 1.5;
}

.relation-option__meta {
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-all;
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

.tab-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
}

.tab-card__title {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.tab-card__actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-item {
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f2f5;
}

.comment-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.comment-item__head {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  color: #606266;
  font-size: 13px;
}

.comment-item__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.comment-item__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.comment-edit-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-edit-panel__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .attachment-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .comment-item__head {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
