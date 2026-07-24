<template>
  <div
    class="version-requirement-page"
    :class="{ 'version-requirement-page--embedded': embedded }"
  >
    <div v-if="!embedded" class="page-header">
      <div class="header-title">
        <h1 class="page-title">版本需求管理</h1>
        <p v-if="selectedVersionText" class="page-subtitle">当前版本 {{ selectedVersionText }}</p>
      </div>
    </div>

    <div class="version-requirement-panel">
      <div class="tab-toolbar">
        <div class="toolbar-left">
          <el-select
            v-if="!useLinkedVersion"
            v-model="filters.version"
            clearable
            filterable
            placeholder="按版本筛选"
            style="width: 240px"
            @change="loadRecords"
          >
            <el-option
              v-for="item in versionOptions"
              :key="item.version"
              :label="`${item.version}${item.record_count ? ` (${item.record_count}条)` : ''}`"
              :value="item.version"
            />
          </el-select>

          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索需求编号、标题或模块"
            style="width: 320px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
        </div>

        <div class="toolbar-right">
          <TableColumnSettings
            :table-ref="requirementTableRef"
            storage-key="manual-testcases.version-requirements"
          />
          <span class="selection-hint">已选 {{ selectedRows.length }} 条</span>
          <el-button
            type="primary"
            :disabled="createDisabled"
            @click="openCreateDialog"
          >
            创建需求
          </el-button>
          <el-button @click="selectAllRecords" :disabled="!records.length">
            全选
          </el-button>
          <el-button
            type="danger"
            plain
            :disabled="!selectedRows.length"
            :loading="clearingRecords"
            @click="clearSelectedRecords"
          >
            清空所选
          </el-button>
          <el-button :loading="loadingRecords" @click="refreshDataset">
            刷新数据
          </el-button>
        </div>
      </div>

      <div class="table-panel">
        <el-table
          ref="requirementTableRef"
          v-loading="loadingRecords"
          :data="records"
          row-key="id"
          stripe
          class="records-table"
          max-height="calc(100vh - 320px)"
          empty-text="暂无版本需求数据"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="52" fixed="left" />
          <el-table-column
            v-if="!useLinkedVersion"
            prop="version"
            label="版本号"
            min-width="140"
            sortable
            :sort-method="createTextSorter(row => row.version)"
            :filters="requirementTableFilters.version"
            :filter-method="createTableFilter(row => row.version)"
          />
          <el-table-column
            prop="issue_key"
            label="需求编号"
            min-width="140"
            sortable
            :sort-method="createTextSorter(row => row.issue_key)"
            :filters="requirementTableFilters.issue_key"
            :filter-method="createTableFilter(row => row.issue_key)"
          />
          <el-table-column
            prop="summary"
            label="需求标题"
            min-width="280"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.summary)"
            :filters="requirementTableFilters.summary"
            :filter-method="createTableFilter(row => row.summary)"
          />
          <el-table-column
            prop="issue_type"
            label="需求类型"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.issue_type)"
            :filters="requirementTableFilters.issue_type"
            :filter-method="createTableFilter(row => row.issue_type)"
          />
          <el-table-column
            prop="module"
            label="所属模块"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.module)"
            :filters="requirementTableFilters.module"
            :filter-method="createTableFilter(row => row.module)"
          />
          <el-table-column
            prop="customer_name"
            label="客户"
            min-width="160"
            show-overflow-tooltip
            sortable
            :sort-method="createTextSorter(row => row.customer_name)"
            :filters="requirementTableFilters.customer_name"
            :filter-method="createTableFilter(row => row.customer_name)"
          />
          <el-table-column
            prop="priority"
            label="优先级"
            min-width="110"
            sortable
            :sort-method="createTextSorter(row => row.priority)"
            :filters="requirementTableFilters.priority"
            :filter-method="createTableFilter(row => row.priority)"
          />
          <el-table-column
            prop="status"
            label="状态"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.status)"
            :filters="requirementTableFilters.status"
            :filter-method="createTableFilter(row => row.status)"
          />
          <el-table-column
            prop="creator"
            label="创建人"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.creator)"
            :filters="requirementTableFilters.creator"
            :filter-method="createTableFilter(row => row.creator)"
          />
          <el-table-column
            prop="handler"
            label="处理人"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.handler)"
            :filters="requirementTableFilters.handler"
            :filter-method="createTableFilter(row => row.handler)"
          />
          <el-table-column
            prop="tester"
            label="测试人员"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.tester)"
            :filters="requirementTableFilters.tester"
            :filter-method="createTableFilter(row => row.tester)"
          />
          <el-table-column
            prop="group_name"
            label="组别"
            min-width="120"
            sortable
            :sort-method="createTextSorter(row => row.group_name)"
            :filters="requirementTableFilters.group_name"
            :filter-method="createTableFilter(row => row.group_name)"
          />
          <el-table-column
            label="更新时间"
            min-width="170"
            sortable
            :sort-method="sortByUpdatedAt"
            :filters="requirementTableFilters.updated_at"
            :filter-method="createTableFilter(getRequirementUpdatedAt)"
          >
            <template #default="{ row }">{{ formatDate(row.updated_at || row.synced_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" :width="requirementActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <div class="row-actions row-actions--stacked">
                <div class="action-row">
                  <el-tooltip
                    :disabled="hasRequirementMindmap(row)"
                    content="没有关联的测试脑图"
                    placement="top"
                  >
                    <span>
                      <el-button
                        link
                        type="primary"
                        :disabled="!hasRequirementMindmap(row)"
                        @click="jumpToRequirementTestpoints(row)"
                      >
                        测试点
                      </el-button>
                    </span>
                  </el-tooltip>
                  <el-tooltip
                    :disabled="hasRequirementVersionDefect(row)"
                    content="没有关联的版本缺陷"
                    placement="top"
                  >
                    <span>
                      <el-button
                        link
                        type="primary"
                        :disabled="!hasRequirementVersionDefect(row)"
                        @click="jumpToRequirementDefects(row)"
                      >
                        版本缺陷
                      </el-button>
                    </span>
                  </el-tooltip>
                  <el-tooltip
                    :disabled="hasRequirementBugRecord(row)"
                    content="没有关联的线上缺陷"
                    placement="top"
                  >
                    <span>
                      <el-button
                        link
                        type="primary"
                        :disabled="!hasRequirementBugRecord(row)"
                        @click="jumpToRequirementBugRecords(row)"
                      >
                        线上缺陷
                      </el-button>
                    </span>
                  </el-tooltip>
                </div>
                <div class="action-row">
                  <el-button link type="primary" @click="openRecordDetail(row)">详情</el-button>
                  <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                  <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
                </div>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      width="1120px"
      top="4vh"
      class="version-requirement-dialog"
      destroy-on-close
    >
      <div class="page-container version-requirement-form-page">
        <div class="page-header version-requirement-form-header">
          <div class="header-title">
            <h1 class="page-title">{{ dialogFormTitle }}</h1>
            <p v-if="dialogContextText" class="page-subtitle">{{ dialogContextText }}</p>
          </div>
          <div class="header-actions">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSubmit">
              {{ isEdit ? '保存修改' : '创建需求' }}
            </el-button>
          </div>
        </div>

        <div v-loading="saving" class="card-container version-requirement-form-card">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-tabs v-model="dialogActiveTab" class="version-requirement-form-tabs">
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
                </div>
              </el-tab-pane>

              <el-tab-pane label="需求处理" name="process">
                <div class="tab-panel">
                  <el-row :gutter="20">
                    <el-col :xs="24" :md="12">
                      <el-form-item label="版本号" prop="version">
                        <el-input
                          v-if="useLinkedVersion"
                          :model-value="form.version"
                          disabled
                        />
                        <el-select
                          v-else
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
                        <el-input
                          v-model="form.module"
                          maxlength="255"
                          placeholder="请输入所属模块"
                        />
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
                        <el-input
                          v-model="form.priority"
                          maxlength="100"
                          placeholder="例如：P1"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :xs="24" :md="12">
                      <el-form-item label="状态">
                        <el-input
                          v-model="form.status"
                          maxlength="100"
                          placeholder="例如：进行中"
                        />
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

                  <el-form-item label="扩展字段 JSON" class="version-requirement-form-item--stacked">
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
      </div>
    </el-dialog>

    <el-drawer v-model="detailVisible" :title="detailTitle" size="920px">
      <template v-if="detailRecord">
        <el-descriptions :column="2" border class="detail-descriptions">
          <el-descriptions-item label="版本号">{{ detailRecord.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="需求编号">{{ detailRecord.issue_key || '-' }}</el-descriptions-item>
          <el-descriptions-item label="需求标题" :span="2">{{ detailRecord.summary || '-' }}</el-descriptions-item>
          <el-descriptions-item label="需求类型">{{ detailRecord.issue_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="所属模块">{{ detailRecord.module || '-' }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ detailRecord.customer_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ detailRecord.priority || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detailRecord.status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailRecord.creator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ detailRecord.handler || '-' }}</el-descriptions-item>
          <el-descriptions-item label="测试人员">{{ detailRecord.tester || '-' }}</el-descriptions-item>
          <el-descriptions-item label="组别">{{ detailRecord.group_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="前端开发">{{ detailRecord.frontend_developer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="后端开发">{{ detailRecord.backend_developer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detailRecord.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(detailRecord.updated_at || detailRecord.synced_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="drawer-actions">
          <el-button type="primary" @click="openEditDialog(detailRecord)">编辑需求</el-button>
          <el-tooltip
            :disabled="hasRequirementMindmap(detailRecord)"
            content="没有关联的测试脑图"
            placement="top"
          >
            <span>
              <el-button
                :disabled="!hasRequirementMindmap(detailRecord)"
                @click="jumpToRequirementTestpoints(detailRecord)"
              >
                测试点
              </el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            :disabled="hasRequirementVersionDefect(detailRecord)"
            content="没有关联的版本缺陷"
            placement="top"
          >
            <span>
              <el-button
                :disabled="!hasRequirementVersionDefect(detailRecord)"
                @click="jumpToRequirementDefects(detailRecord)"
              >
                版本缺陷
              </el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            :disabled="hasRequirementBugRecord(detailRecord)"
            content="没有关联的线上缺陷"
            placement="top"
          >
            <span>
              <el-button
                :disabled="!hasRequirementBugRecord(detailRecord)"
                @click="jumpToRequirementBugRecords(detailRecord)"
              >
                线上缺陷
              </el-button>
            </span>
          </el-tooltip>
        </div>
        <div class="detail-section">
          <h3>需求描述</h3>
          <DefectRichTextContent :html="detailRecord.description" empty-text="-" />
        </div>

        <div class="detail-section">
          <h3>关联测试脑图</h3>
          <div v-if="detailMindmaps.length" class="relation-tag-list">
            <el-tag
              v-for="item in detailMindmaps"
              :key="item.relation_key"
              class="relation-tag"
              type="info"
              effect="plain"
            >
              {{ item.option_label }}
            </el-tag>
          </div>
          <span v-else class="detail-empty-text">-</span>
        </div>

        <div class="raw-panel">
          <h3>扩展字段</h3>
          <pre>{{ formattedRawFields }}</pre>
        </div>
      </template>
    </el-drawer>

    <ImagePreviewViewer
      v-model:visible="previewVisible"
      :images="previewImages"
      :initial-index="previewIndex"
      @update:initial-index="handlePreviewIndexChange"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '@/utils/api'
import DefectRichTextEditor from '@/components/defects/DefectRichTextEditor.vue'
import DefectRichTextContent from '@/components/defects/DefectRichTextContent.vue'
import ImagePreviewViewer from '@/components/defects/ImagePreviewViewer.vue'
import { uploadDefectRichTextImages } from '@/api/defects'
import { hasRichTextContent, replaceInlineImageDataUrls } from '@/utils/defectRichText'
import {
  buildTableFilters,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { fetchAllGroupOptions } from '@/utils/groupOptions'
import { fetchRoleMemberOptions } from '@/utils/roleOptions'
import { getUserDisplayName } from '@/utils/userDisplay'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  active: {
    type: Boolean,
    default: true,
  },
  useLinkedVersion: {
    type: Boolean,
    default: false,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
  linkedKeyword: {
    type: String,
    default: '',
  },
  linkedModules: {
    type: Array,
    default: () => [],
  },
})

const RECORD_ENDPOINT = '/quality-analysis/jira-requirement-records/'
const VERSION_ENDPOINT = '/quality-analysis/jira-requirement-records/versions/'
const MANUAL_MINDMAP_ENDPOINT = '/testcases/manual-mindmaps/'

const route = useRoute()
const router = useRouter()

const requirementTableRef = ref(null)
const formRef = ref(null)
const loadingRecords = ref(false)
const saving = ref(false)
const clearingRecords = ref(false)
const dialogVisible = ref(false)
const dialogActiveTab = ref('detail')
const detailVisible = ref(false)
const detailRecord = ref(null)
const versionSummaries = ref([])
const records = ref([])
const selectedRows = ref([])
const editingId = ref(null)
const groupOptions = ref([])
const testerUsers = ref([])
const frontendUsers = ref([])
const backendUsers = ref([])
const relatedMindmapLoading = ref(false)
const relatedMindmapOptions = ref([])

const previewVisible = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

const filters = reactive({
  version: '',
  keyword: '',
})

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
const requirementActionColumnWidth = buildActionColumnWidth([
  ['测试点', '版本缺陷', '线上缺陷'],
  ['详情', '编辑', '删除'],
], {
  variant: 'link',
  min: 220,
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

const normalizedLinkedVersion = computed(() => normalizeText(props.linkedVersion))
const normalizedLinkedKeyword = computed(() => normalizeText(props.linkedKeyword))
const normalizedLinkedModules = computed(() => (
  Array.from(
    new Set(
      (Array.isArray(props.linkedModules) ? props.linkedModules : [])
        .map(normalizeText)
        .filter(Boolean)
    )
  )
))

const selectedVersionText = computed(() => (
  props.useLinkedVersion ? normalizedLinkedVersion.value : normalizeText(filters.version)
))
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
        .map(user => getUserDisplayName(user, `用户${user.id}`))
        .map(normalizeText)
        .filter(Boolean)
    )
  ).sort((left, right) => left.localeCompare(right, 'zh-CN'))
)
const testerNameOptions = computed(() => buildUserNameOptions(testerUsers.value))
const frontendDeveloperNameOptions = computed(() => buildUserNameOptions(frontendUsers.value))
const backendDeveloperNameOptions = computed(() => buildUserNameOptions(backendUsers.value))
const createDisabled = computed(() => props.useLinkedVersion && !normalizedLinkedVersion.value)
const isEdit = computed(() => Boolean(editingId.value))
const dialogFormTitle = computed(() => (isEdit.value ? '编辑需求' : '创建需求'))
const dialogContextText = computed(() => {
  const parts = []
  const version = normalizeText(form.version)
  const issueKey = normalizeText(form.issue_key)

  if (version) {
    parts.push(`当前版本 ${version}`)
  }
  if (isEdit.value && issueKey) {
    parts.push(`需求编号 ${issueKey}`)
  }

  return parts.join(' / ')
})
const detailTitle = computed(() => {
  const issueKey = normalizeText(detailRecord.value?.issue_key)
  return issueKey ? `需求详情 / ${issueKey}` : '需求详情'
})
const formattedRawFields = computed(() => {
  return detailRecord.value ? JSON.stringify(detailRecord.value.raw_fields || {}, null, 2) : '{}'
})
const detailMindmaps = computed(() => ensureUniqueRequirementMindmaps(detailRecord.value?.related_mindmaps || []))
const getRequirementUpdatedAt = row => formatDate(row?.updated_at || row?.synced_at)

const formatDate = (value) => {
  const normalized = normalizeText(value)
  if (!normalized) {
    return '-'
  }
  const parsed = dayjs(normalized)
  return parsed.isValid() ? parsed.format('YYYY/MM/DD HH:mm:ss') : normalized
}

const sortByUpdatedAt = (left, right) => {
  const leftTime = new Date(left.updated_at || left.synced_at || 0).getTime() || 0
  const rightTime = new Date(right.updated_at || right.synced_at || 0).getTime() || 0
  return leftTime - rightTime
}

const buildStaticFilterOptions = values => (
  Array.from(new Set((Array.isArray(values) ? values : []).map(value => String(value || '').trim()).filter(Boolean)))
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
    .map(value => ({ text: value, value }))
)

const requirementTableFilters = computed(() => ({
  version: buildTableFilters(records.value, row => row.version, 20),
  issue_key: buildTableFilters(records.value, row => row.issue_key, 30),
  summary: buildTableFilters(records.value, row => row.summary, 20),
  issue_type: buildTableFilters(records.value, row => row.issue_type, 20),
  module: buildTableFilters(records.value, row => row.module, 20),
  customer_name: buildTableFilters(records.value, row => row.customer_name, 20),
  priority: buildTableFilters(records.value, row => row.priority, 20),
  status: buildTableFilters(records.value, row => row.status, 20),
  creator: buildTableFilters(records.value, row => row.creator, 20),
  handler: buildTableFilters(records.value, row => row.handler, 20),
  tester: buildTableFilters(records.value, row => row.tester, 20),
  group_name: buildStaticFilterOptions(groupOptions.value.map(group => group.name)),
  updated_at: buildTableFilters(records.value, getRequirementUpdatedAt, 20),
}))

const getRelationCount = (row, countField, listField) => {
  const count = Number(row?.[countField])
  if (Number.isFinite(count)) {
    return count
  }
  const listValue = row?.[listField]
  return Array.isArray(listValue) ? listValue.length : 0
}

const hasRequirementMindmap = row => getRelationCount(row, 'related_mindmap_count', 'related_mindmaps') > 0
const hasRequirementVersionDefect = row => getRelationCount(row, 'version_defect_count', 'version_defects') > 0
const hasRequirementBugRecord = row => getRelationCount(row, 'bug_record_count', 'bug_records') > 0

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

const syncLinkedKeyword = () => {
  if (!props.embedded) {
    return
  }
  filters.keyword = normalizedLinkedKeyword.value
}

const syncSelectedVersion = () => {
  if (props.useLinkedVersion) {
    filters.version = normalizedLinkedVersion.value
    return
  }

  const availableVersions = versionOptions.value.map(item => item.version)
  if (!availableVersions.length) {
    filters.version = ''
    return
  }

  if (!filters.version || !availableVersions.includes(filters.version)) {
    filters.version = availableVersions[0]
  }
}

const buildRequestParams = (options = {}) => {
  const params = {}
  const effectiveVersion = props.useLinkedVersion ? normalizedLinkedVersion.value : normalizeText(filters.version)
  const keyword = normalizeText(filters.keyword)

  if (effectiveVersion) {
    params.version = effectiveVersion
  }
  if (keyword) {
    params.keyword = keyword
  }
  if (props.embedded && route.query.project_id) {
    params.project_id = String(route.query.project_id)
  }
  if (props.embedded && route.query.version_id && route.query.version_id !== 'all') {
    params.manual_version_id = String(route.query.version_id)
  }
  if (props.embedded && normalizedLinkedModules.value.length && !options.skipModuleNames) {
    params.module_names = JSON.stringify(normalizedLinkedModules.value)
  }

  return params
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

const clearTableSelection = async () => {
  selectedRows.value = []
  await nextTick()
  requirementTableRef.value?.clearSelection()
}

const loadRecords = async () => {
  loadingRecords.value = true
  try {
    const requestParams = buildRequestParams()
    const response = await api.get(RECORD_ENDPOINT, { params: requestParams })
    let nextRecords = normalizeApiList(response.data)
    if (!nextRecords.length && requestParams.module_names) {
      const fallbackResponse = await api.get(RECORD_ENDPOINT, { params: buildRequestParams({ skipModuleNames: true }) })
      nextRecords = normalizeApiList(fallbackResponse.data)
    }
    records.value = nextRecords
    await clearTableSelection()
  } catch (error) {
    records.value = []
    await clearTableSelection()
    ElMessage.error('获取版本需求列表失败')
  } finally {
    loadingRecords.value = false
  }
}

const refreshDataset = async () => {
  await loadVersionSummaries()
  syncSelectedVersion()
  await loadRecords()
}

const handleSearch = async () => {
  await loadRecords()
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const selectAllRecords = async () => {
  if (!records.value.length || !requirementTableRef.value) {
    return
  }

  requirementTableRef.value.clearSelection()
  await nextTick()
  requirementTableRef.value.toggleAllSelection()
}

const resetForm = () => {
  Object.assign(form, createDefaultForm())
  editingId.value = null

  const defaultVersion = props.useLinkedVersion
    ? normalizedLinkedVersion.value
    : normalizeText(filters.version)

  if (defaultVersion) {
    form.version = defaultVersion
  }

  resetMindmapOptionPool()
}

const openCreateDialog = () => {
  if (createDisabled.value) {
    ElMessage.warning('请先在左侧选择版本后再创建需求')
    return
  }

  router.push({
    path: '/manual-testcases/requirements/create',
    query: buildManualWorkspaceQuery(
      {
        tab: 'version-requirements',
        source: 'manual-testcases',
        version: selectedVersionText.value,
        keyword: normalizeText(filters.keyword),
      },
      ['mindmap_keyword', 'mindmap_requirement_key', 'jira_keyword', 'testpoint_keyword', 'defect_keyword', 'bug_keyword']
    ),
  })
}

const openEditDialog = (row) => {
  router.push({
    path: `/manual-testcases/requirements/${row.id}/edit`,
    query: buildManualWorkspaceQuery(
      {
        tab: 'version-requirements',
        source: 'manual-testcases',
        version: normalizeText(row?.version) || selectedVersionText.value,
        keyword: normalizeText(filters.keyword),
      },
      ['mindmap_keyword', 'mindmap_requirement_key', 'jira_keyword', 'testpoint_keyword', 'defect_keyword', 'bug_keyword']
    ),
  })
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
})

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = await buildPayload()

    if (editingId.value) {
      await api.patch(`${RECORD_ENDPOINT}${editingId.value}/`, payload)
      ElMessage.success('需求已更新')
    } else {
      await api.post(RECORD_ENDPOINT, payload)
      ElMessage.success('需求已创建')
    }

    dialogVisible.value = false
    await refreshDataset()
  } catch (error) {
    if (error instanceof Error && error.message.includes('JSON')) {
      ElMessage.error(error.message)
      return
    }
    ElMessage.error(error.response?.data?.detail || '保存需求失败')
  } finally {
    saving.value = false
  }
}

const openRecordDetail = (row) => {
  detailRecord.value = {
    ...row,
    related_mindmaps: ensureUniqueRequirementMindmaps(row.related_mindmaps || []),
  }
  detailVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除需求“${row.issue_key || row.summary}”吗？`,
      '删除确认',
      {
        type: 'warning',
      }
    )

    await api.delete(`${RECORD_ENDPOINT}${row.id}/`)
    ElMessage.success('需求已删除')
    await refreshDataset()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除需求失败')
    }
  }
}

const clearSelectedRecords = async () => {
  const ids = selectedRows.value.map(item => item.id).filter(Boolean)
  if (!ids.length) {
    ElMessage.warning('请先选择需要清空的记录')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认清空当前所选 ${ids.length} 条版本需求数据吗？`,
      '清空确认',
      {
        type: 'warning',
      }
    )

    clearingRecords.value = true
    const response = await api.post(`${RECORD_ENDPOINT}clear-selected/`, { ids })
    ElMessage.success(response.data?.message || '清空成功')
    await refreshDataset()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('清空版本需求失败')
    }
  } finally {
    clearingRecords.value = false
  }
}

const buildManualWorkspaceQuery = (overrides = {}, keysToClear = []) => {
  const query = {
    ...route.query,
    ...overrides,
  }

  keysToClear.forEach(key => {
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

const jumpToRequirementDefects = (row) => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前需求缺少编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'version-defects',
        defect_keyword: issueKey,
      },
      ['mindmap_keyword', 'mindmap_requirement_key', 'jira_keyword', 'testpoint_keyword', 'bug_keyword', 'keyword']
    ),
  })
}

const jumpToRequirementTestpoints = (row) => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前需求缺少编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'testpoints',
        testpoint_requirement_key: issueKey,
      },
      ['keyword', 'jira_keyword', 'mindmap_keyword', 'mindmap_requirement_key', 'defect_keyword', 'bug_keyword']
    ),
  })
}

const jumpToRequirementBugRecords = (row) => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前需求缺少编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'bug-records',
        bug_keyword: issueKey,
      },
      ['keyword', 'jira_keyword', 'mindmap_keyword', 'mindmap_requirement_key', 'testpoint_keyword', 'defect_keyword']
    ),
  })
}

const loadRelatedMindmapOptions = async (keyword = '') => {
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
    resetMindmapOptionPool()
    return
  }

  relatedMindmapLoading.value = true
  try {
    const response = await api.get(MANUAL_MINDMAP_ENDPOINT, { params })
    const nextOptions = normalizeApiList(response.data).map(decorateRequirementMindmapItem).filter(Boolean)
    relatedMindmapOptions.value = ensureUniqueRequirementMindmaps([
      ...form.related_mindmaps,
      ...nextOptions,
    ])
  } catch (error) {
    resetMindmapOptionPool()
    ElMessage.error('获取测试脑图列表失败')
  } finally {
    relatedMindmapLoading.value = false
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

const openPreview = ({ images = [], currentIndex = 0 } = {}) => {
  previewImages.value = Array.isArray(images) ? images : []
  previewIndex.value = Number(currentIndex) || 0
  previewVisible.value = Boolean(previewImages.value.length)
}

const handlePreviewIndexChange = (nextIndex) => {
  previewIndex.value = nextIndex
}

onMounted(async () => {
  syncLinkedKeyword()
  await Promise.all([loadGroupOptions(), loadUsers()])
  if (!props.embedded || props.active) {
    await refreshDataset()
  }
})

watch(
  () => props.linkedVersion,
  async (nextVersion, previousVersion) => {
    if (!props.useLinkedVersion || !props.active || normalizeText(nextVersion) === normalizeText(previousVersion)) {
      return
    }
    filters.version = normalizeText(nextVersion)
    await refreshDataset()
  }
)

watch(
  () => props.linkedKeyword,
  async (nextKeyword, previousKeyword) => {
    if (!props.embedded || normalizeText(nextKeyword) === normalizeText(previousKeyword)) {
      return
    }
    syncLinkedKeyword()
    if (props.active) {
      await loadRecords()
    }
  }
)

watch(
  () => normalizedLinkedModules.value.join('||'),
  async (nextModules, previousModules) => {
    if (!props.embedded || nextModules === previousModules || !props.active) {
      return
    }
    await loadRecords()
  }
)

watch(
  () => props.active,
  async (active) => {
    if (!active) {
      return
    }
    syncLinkedKeyword()
    await Promise.all([loadGroupOptions(), loadUsers()])
    await refreshDataset()
  }
)
</script>

<style scoped lang="scss">
.version-requirement-page {
  flex: 1 1 0;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.version-requirement-page--embedded {
  padding: 0;
  height: 100%;
  min-height: 0;
}

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

.version-requirement-panel {
  min-height: 0;
  display: flex;
  flex: 1;
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

.toolbar-left {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.selection-hint {
  color: #606266;
  font-size: 13px;
}

.table-panel,
.raw-panel,
.detail-section {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 24px;
  box-shadow: 0 18px 38px rgba(15, 45, 68, 0.08);
}

.table-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.records-table {
  flex: 1 1 0;
  min-height: 0;
}

.records-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 8px;
  width: 100%;
  white-space: nowrap;
}

.row-actions--stacked {
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.action-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  line-height: 1.4;
  white-space: nowrap;
  width: 100%;
}

.action-row > span {
  display: inline-flex;
}

.detail-descriptions {
  margin-bottom: 16px;
}

.version-requirement-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    overflow: hidden;
  }

  :deep(.el-dialog__header) {
    display: none;
  }

  :deep(.el-dialog__body) {
    padding: 0;
    background: #f5f7fa;
  }
}

.version-requirement-form-page {
  padding: 24px;
}

.version-requirement-form-header {
  margin-bottom: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.version-requirement-form-card {
  overflow: hidden;
}

.version-requirement-form-tabs {
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

.version-requirement-form-item--stacked {
  :deep(.el-form-item__content) {
    display: block;
  }
}

.drawer-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.detail-section,
.raw-panel {
  padding: 20px;
  margin-bottom: 16px;
}

.detail-section h3,
.raw-panel h3 {
  margin: 0 0 12px;
}

.relation-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.relation-tag {
  max-width: 100%;
}

.relation-tag :deep(.el-tag__content) {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}

.detail-empty-text {
  color: #909399;
}

.raw-panel pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .version-requirement-form-page {
    padding: 16px;
  }

  .toolbar-right {
    width: 100%;
    margin-left: 0;
  }
}
</style>

