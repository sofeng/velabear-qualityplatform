<template>
  <div class="ai-requirements-page">
    <div class="page-header toolbar-card">
      <div class="header-filters">
        <div class="filter-item">
          <label>需求名称</label>
          <input v-model="filters.keyword" placeholder="输入需求名称关键字" @keyup.enter="loadRequirements" />
        </div>
        <div class="filter-item">
          <label>项目</label>
          <select v-model="filters.projectId" @change="loadRequirements">
            <option value="">全部项目</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
          </select>
        </div>
        <button class="search-btn" @click="loadRequirements">查询</button>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="loadRequirements" :disabled="isLoading">刷新</button>
        <button class="batch-generate-btn" @click="batchGenerateTestCases" :disabled="selectedIds.length === 0 || isGeneratingCases">
          {{ isGeneratingCases ? '生成中...' : `批量生成测试用例(${selectedIds.length})` }}
        </button>
        <button class="create-btn" @click="openCreateDialog">+ 新增需求</button>
      </div>
    </div>

    <div class="table-card">
      <div v-if="isLoading" class="empty">加载中...</div>
      <div v-else-if="filteredRequirements.length === 0" class="empty">暂无AI需求</div>
      <table v-else>
        <thead>
          <tr>
            <th style="width: 46px;"><input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll($event)"></th>
            <th>需求编号</th>
            <th>需求名称</th>
            <th>类型</th>
            <th>级别</th>
            <th>所属模块</th>
            <th>项目</th>
            <th>用例生成状态</th>
            <th>审核状态</th>
            <th>审核人</th>
            <th>审核时间</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredRequirements" :key="item.id">
            <td><input type="checkbox" :checked="selectedIds.includes(item.id)" @change="toggleSelect(item.id)" /></td>
            <td>{{ item.requirement_id }}</td>
            <td>
              <span class="requirement-name-link" @click="viewDetail(item)" :title="'点击查看需求详情'">
                {{ item.requirement_name }}
              </span>
            </td>
            <td>{{ item.requirement_type_display || item.requirement_type }}</td>
            <td>{{ item.requirement_level_display || item.requirement_level }}</td>
            <td>{{ item.module }}</td>
            <td>{{ item.project_name || '-' }}</td>
            <td>
              <span class="status-tag" :class="item.case_generation_status">
                {{ item.case_generation_status_display || mapCaseStatus(item.case_generation_status) }}
              </span>
            </td>
            <td>
              <span class="audit-status-tag" :class="item.audit_status || 'pending'">
                {{ item.audit_status_display || mapAuditStatus(item.audit_status) }}
              </span>
            </td>
            <td>{{ item.audited_by_name || '-' }}</td>
            <td>{{ formatDateTime(item.audited_at) }}</td>
            <td>{{ formatDateTime(item.updated_at) }}</td>
            <td class="actions">
              <button class="view-btn" @click="viewDetail(item)" title="查看详情">查看</button>
              <button class="ai-dev-btn" @click="openAIDevDialogFromList(item)" title="创建AI开发任务">AI开发</button>
              <button class="generate-btn" @click="generateSingle(item)" :disabled="isGeneratingCases">生成测试用例</button>
              <button class="audit-btn" @click="auditRequirement(item)" :disabled="isAuditing || item.audit_status === 'approved'">
                {{ item.audit_status === 'approved' ? '已审核' : '审核' }}
              </button>
              <button class="edit-btn" @click="openEditDialog(item)">编辑</button>
              <button class="delete-btn" @click="deleteRequirement(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑对话框 -->
    <div v-if="showDialog" class="dialog-mask" @click="closeDialog">
      <div class="dialog edit-dialog" @click.stop>
        <div class="dialog-header">
          <h3>{{ form.id ? '编辑需求' : '新增需求' }}</h3>
          <button class="close-btn" @click="closeDialog">×</button>
        </div>

        <div class="dialog-body">
          <!-- 主要信息区 -->
          <div class="main-section">
            <div class="form-group">
              <label>需求标题<span class="required">*</span></label>
              <input
                v-model="form.requirement_name"
                type="text"
                class="form-input"
                placeholder="请输入需求标题，例如：用户登录功能需求" />
            </div>

            <div class="form-group">
              <label>需求描述<span class="required">*</span></label>
              <textarea
                v-model="form.description"
                class="form-textarea"
                rows="8"
                placeholder="请详细描述您的需求，包括功能描述、使用场景、业务流程等"></textarea>
              <div class="char-count">{{ form.description.length }}/2000</div>
            </div>

            <div class="form-group">
              <label>验收标准</label>
              <textarea
                v-model="form.acceptance_criteria"
                class="form-textarea"
                rows="4"
                placeholder="请输入验收标准"></textarea>
            </div>
          </div>

          <!-- 文档上传区 -->
          <div class="upload-section" v-if="!form.id">
            <div class="section-title">上传需求文档（可选）</div>
            <div class="upload-area"
                 @dragover.prevent
                 @drop="handleDrop"
                 :class="{ 'drag-over': isDragOver }"
                 @dragenter="isDragOver = true"
                 @dragleave="isDragOver = false">
              <div v-if="!selectedFile" class="upload-placeholder">
                <i class="upload-icon">↑</i>
                <p>拖拽文件到此处或点击选择文件</p>
                <p class="upload-hint">支持 PDF、Word、TXT 格式</p>
                <input
                  type="file"
                  ref="fileInput"
                  @change="handleFileSelect"
                  accept=".pdf,.doc,.docx,.txt"
                  style="display: none;">
                <button class="select-file-btn" @click="$refs.fileInput.click()">
                  选择文件
                </button>
              </div>

              <div v-else class="file-selected">
                <div class="file-info">
                  <i class="file-icon">文</i>
                  <div class="file-details">
                    <p class="file-name">{{ selectedFile.name }}</p>
                    <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                  </div>
                  <button class="remove-file" @click="removeFile">×</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 配置信息区 -->
          <div class="config-section">
            <div class="section-title">配置信息</div>
            <div class="config-grid">
              <div class="form-group">
                <label>需求编号</label>
                <input v-model="form.requirement_id" type="text" class="form-input" placeholder="自动生成" readonly />
              </div>

              <div class="form-group">
                <label>关联项目 <span class="required">*</span></label>
                <select v-model="form.project" class="form-select" required>
                  <option value="">请选择项目</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>需求类型</label>
                <select v-model="form.requirement_type" class="form-select">
                  <option value="functional">功能需求</option>
                  <option value="performance">性能需求</option>
                  <option value="security">安全需求</option>
                  <option value="usability">可用性需求</option>
                  <option value="interface">接口需求</option>
                  <option value="other">其他需求</option>
                </select>
              </div>

              <div class="form-group">
                <label>需求级别</label>
                <select v-model="form.requirement_level" class="form-select">
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
              </div>

              <div class="form-group">
                <label>所属模块</label>
                <input v-model="form.module" type="text" class="form-input" placeholder="请输入所属模块" />
              </div>

              <div class="form-group">
                <label>评审人</label>
                <input v-model="form.reviewer" type="text" class="form-input" placeholder="请输入评审人" />
              </div>

              <div class="form-group">
                <label>预计工时（小时）</label>
                <input v-model.number="form.estimated_hours" type="number" min="1" class="form-input" placeholder="8" />
              </div>
            </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="cancel-btn" @click="closeDialog">取消</button>
          <button class="save-btn" @click="saveRequirement" :disabled="isSaving">
            {{ isSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 需求详情对话框 -->
    <div v-if="showDetailDialog" class="dialog-mask" @click="closeDetailDialog">
      <div class="dialog detail-dialog" @click.stop>
        <h3>需求详情</h3>
        <div class="detail-content">
          <div class="detail-row"><label>需求编号：</label><span>{{ detailData.requirement_id }}</span></div>
          <div class="detail-row"><label>需求名称：</label><span>{{ detailData.requirement_name }}</span></div>
          <div class="detail-row"><label>需求类型：</label><span>{{ detailData.requirement_type_display || detailData.requirement_type }}</span></div>
          <div class="detail-row"><label>需求级别：</label><span>{{ detailData.requirement_level_display || detailData.requirement_level }}</span></div>
          <div class="detail-row"><label>所属模块：</label><span>{{ detailData.module }}</span></div>
          <div class="detail-row"><label>评审人：</label><span>{{ detailData.reviewer }}</span></div>
          <div class="detail-row"><label>预计工时：</label><span>{{ detailData.estimated_hours }} 小时</span></div>
          <div class="detail-row"><label>项目：</label><span>{{ detailData.project_name || '-' }}</span></div>
          <div class="detail-row"><label>用例生成状态：</label><span class="status-tag" :class="detailData.case_generation_status">{{ detailData.case_generation_status_display || mapCaseStatus(detailData.case_generation_status) }}</span></div>
          <div class="detail-row"><label>审核状态：</label><span class="audit-status-tag" :class="detailData.audit_status || 'pending'">{{ detailData.audit_status_display || mapAuditStatus(detailData.audit_status) }}</span></div>
          <div class="detail-row"><label>审核人：</label><span>{{ detailData.audited_by_name || '-' }}</span></div>
          <div class="detail-row"><label>审核时间：</label><span>{{ formatDateTime(detailData.audited_at) }}</span></div>
          <div class="detail-row full-width"><label>需求描述：</label><div class="detail-text">{{ detailData.description }}</div></div>
          <div class="detail-row full-width"><label>验收标准：</label><div class="detail-text">{{ detailData.acceptance_criteria }}</div></div>
          <div class="detail-row"><label>创建时间：</label><span>{{ formatDateTime(detailData.created_at) }}</span></div>
          <div class="detail-row"><label>更新时间：</label><span>{{ formatDateTime(detailData.updated_at) }}</span></div>
        </div>
        <WorkflowPanel
          v-if="detailData.id"
          class="workflow-detail-panel"
          title="流程流转"
          subtitle="需求进入流程后，将按节点驱动评审和状态流转。"
          biz-type="requirement"
          :biz-id="detailData.id"
          :workflow="detailData.workflow"
          workbench-path="/manual-testcases/workflow-workbench"
          @changed="handleWorkflowChanged"
        />
        <div class="dialog-actions">
          <button class="generate-btn" @click="openAIDevDialogFromDetail">AI开发</button>
          <button v-if="detailData.task_id" class="view-btn" @click="goToTaskDetail(detailData.task_id)">查看测试用例</button>
          <button class="edit-btn" @click="editFromDetail">编辑需求</button>
          <button class="cancel-btn" @click="closeDetailDialog">关闭</button>
        </div>
      </div>
    </div>

    <!-- AI开发任务创建对话框 -->
    <div v-if="showAIDevDialog" class="dialog-mask" @click="closeAIDevDialog">
      <div class="dialog" @click.stop>
        <h3>创建AI开发任务</h3>
        <div class="detail-content">
          <div class="detail-row"><label>需求编号：</label><span>{{ selectedRequirementForAIDev?.requirement_id }}</span></div>
          <div class="detail-row"><label>需求名称：</label><span>{{ selectedRequirementForAIDev?.requirement_name }}</span></div>
          <div class="form-item" style="margin-top: 16px;">
            <label>AI开发项目配置<span style="color: #f56c6c;">*</span></label>
            <select v-model="aiDevForm.config_id" required>
              <option value="">请选择 AI 开发项目配置</option>
              <option v-for="config in aiDevConfigs" :key="config.id" :value="config.id">
                {{ config.name }} ({{ config.ai_tool }}) - {{ config.is_active ? '启用' : '禁用' }}
              </option>
            </select>
            <small style="color: #909399; margin-top: 4px;">
              如果没有配置，请先到
              <a href="/ai-generation/list?tab=ai-dev-configs" target="_blank" style="color: #409eff;">AI开发项目配置页面</a>
              创建
            </small>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="cancel-btn" @click="closeAIDevDialog">取消</button>
          <button class="save-btn" @click="createAIDevTask" :disabled="isCreatingAIDev || !aiDevForm.config_id">
            {{ isCreatingAIDev ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import WorkflowPanel from '@/components/workflow/WorkflowPanel.vue'

export default {
  name: 'AIRequirementsList',
  components: {
    WorkflowPanel
  },
  data() {
    return {
      isLoading: false,
      isSaving: false,
      isGeneratingCases: false,
      isCreatingAIDev: false,
      isAuditing: false,
      showDialog: false,
      showDetailDialog: false,
      showAIDevDialog: false,
      isDragOver: false,
      selectedFile: null,
      requirements: [],
      selectedIds: [],
      projects: [],
      aiDevConfigs: [],
      filters: { keyword: '', projectId: '' },
      form: {
        id: null,
        project: '',
        requirement_id: '', requirement_name: '', requirement_type: 'functional', requirement_level: 'medium',
         module: 'AI需求', reviewer: 'AI助手', estimated_hours: 8, description: '', acceptance_criteria: ''
      },
      detailData: {},
      selectedRequirementForAIDev: null,
      aiDevForm: {
        config_id: ''
      }
    }
  },
  computed: {
    filteredRequirements() {
      const keyword = this.filters.keyword.trim().toLowerCase()
      if (!keyword) return this.requirements
      return this.requirements.filter(item => (item.requirement_name || '').toLowerCase().includes(keyword))
    },
    isAllSelected() {
      return this.filteredRequirements.length > 0 && this.filteredRequirements.every(item => this.selectedIds.includes(item.id))
    }
  },
  watch: {
    '$route.query.detail_id': {
      immediate: true,
      handler(value) {
        if (value) {
          this.openDetailById(value)
        }
      }
    }
  },
  mounted() { this.loadProjects(); this.loadRequirements(); this.loadAIDevConfigs() },
  methods: {
    async loadProjects() {
      try { const response = await api.get('/projects/'); this.projects = response.data.results || response.data } catch (error) { console.error(error) }
    },
    async loadAIDevConfigs() {
      try {
        const response = await api.get('/ai-development/configs/', { params: { is_active: true } })
        this.aiDevConfigs = response.data.results || response.data
      } catch (error) {
        console.error('加载 AI 开发项目配置失败:', error)
      }
    },
    async loadRequirements() {
      this.isLoading = true
      try {
        const params = {}
        if (this.filters.projectId) params.project_id = this.filters.projectId
        const response = await api.get('/requirement-analysis/api/requirements/', { params })
        this.requirements = response.data.results || response.data
      } catch (error) { ElMessage.error('加载需求失败') }
      finally { this.isLoading = false }
    },
    toggleSelect(id) { this.selectedIds = this.selectedIds.includes(id) ? this.selectedIds.filter(item => item !== id) : [...this.selectedIds, id] },
    toggleSelectAll(event) {
      const currentPageIds = this.filteredRequirements.map(item => item.id)
      this.selectedIds = event.target.checked ? Array.from(new Set([...this.selectedIds, ...currentPageIds])) : this.selectedIds.filter(id => !currentPageIds.includes(id))
    },
    async generateSingle(item) { await this.generateForIds([item.id]) },
    async batchGenerateTestCases() { await this.generateForIds(this.selectedIds) },
    async generateForIds(ids) {
      if (!ids || ids.length === 0) return ElMessage.warning('请先选择需求')
      this.isGeneratingCases = true
      try {
        const response = await api.post('/requirement-analysis/api/requirements/generate_testcase_tasks/', { requirement_ids: ids })
        ElMessage.success(response.data.message || '已创建测试用例生成任务')
        await this.loadRequirements()
      } catch (error) { ElMessage.error('生成测试用例失败: ' + (error.response?.data?.error || error.message)) }
      finally { this.isGeneratingCases = false }
    },
    mapCaseStatus(status) { return { not_generated: '未生成', generating: '生成中', generated: '已生成', failed: '生成失败' }[status] || '-' },
    mapAuditStatus(status) { return { pending: '待审核', approved: '已审核', rejected: '已驳回' }[status] || '待审核' },
    async openDetailById(id) {
      try {
        const response = await api.get(`/requirement-analysis/api/requirements/${id}/`)
        this.detailData = response.data
        this.showDetailDialog = true
      } catch (error) {
        ElMessage.error('加载需求详情失败')
        console.error(error)
      }
    },
    async viewDetail(item) {
      await this.openDetailById(item.id)
    },
    closeDetailDialog() {
      this.showDetailDialog = false
      this.detailData = {}
      if (this.$route.query.detail_id) {
        const query = { ...this.$route.query }
        delete query.detail_id
        this.$router.replace({ query })
      }
    },
    async refreshDetailData() {
      if (!this.detailData?.id) return
      const response = await api.get(`/requirement-analysis/api/requirements/${this.detailData.id}/`)
      this.detailData = response.data
    },
    async handleWorkflowChanged() {
      await this.refreshDetailData()
      await this.loadRequirements()
    },
    goToTaskDetail(taskId) {
      this.closeDetailDialog()
      this.$router.push({ name: 'TaskDetail', params: { taskId } })
    },
    editFromDetail() {
      this.form = {
        id: this.detailData.id,
        project: this.detailData.project || '',
        requirement_id: this.detailData.requirement_id,
        requirement_name: this.detailData.requirement_name,
        requirement_type: this.detailData.requirement_type,
        requirement_level: this.detailData.requirement_level,
        module: this.detailData.module,
        reviewer: this.detailData.reviewer,
        estimated_hours: this.detailData.estimated_hours,
        description: this.detailData.description,
        acceptance_criteria: this.detailData.acceptance_criteria || ''
      }
      this.closeDetailDialog()
      this.showDialog = true
    },
    openAIDevDialogFromDetail() {
      this.selectedRequirementForAIDev = this.detailData
      this.aiDevForm.config_id = ''
      this.showAIDevDialog = true
    },
    openAIDevDialogFromList(item) {
      this.selectedRequirementForAIDev = item
      this.aiDevForm.config_id = ''
      this.showAIDevDialog = true
    },
    closeAIDevDialog() {
      this.showAIDevDialog = false
      this.selectedRequirementForAIDev = null
      this.aiDevForm.config_id = ''
    },
    async createAIDevTask() {
      if (!this.aiDevForm.config_id) {
        ElMessage.error('请选择 AI 开发项目配置')
        return
      }
      if (!this.selectedRequirementForAIDev) {
        ElMessage.error('未选择需求')
        return
      }

      this.isCreatingAIDev = true
      try {
        const response = await api.post('/ai-development/tasks/create_task/', {
          requirement_id: this.selectedRequirementForAIDev.id,
          config_id: this.aiDevForm.config_id
        })
        ElMessage.success(`AI开发任务已创建: ${response.data.task_id}`)
        this.closeAIDevDialog()
        this.closeDetailDialog()

        // 询问是否跳转到任务列表
        try {
          await ElMessageBox.confirm('任务已创建，是否前往任务列表查看?', '提示', {
            confirmButtonText: '前往查看',
            cancelButtonText: '留在当前页',
            type: 'success'
          })
          this.$router.push('/ai-generation/list?tab=ai-dev-tasks')
        } catch (error) {
          // 用户选择留在当前页
        }
      } catch (error) {
        console.error('创建AI开发任务失败:', error)
        ElMessage.error(error.response?.data?.detail || '创建任务失败')
      } finally {
        this.isCreatingAIDev = false
      }
    },
    openCreateDialog() {
      this.form = { id: null, project: '', requirement_id: '', requirement_name: '', requirement_type: 'functional', requirement_level: 'medium', module: 'AI需求', reviewer: 'AI助手', estimated_hours: 8, description: '', acceptance_criteria: '' }
      this.selectedFile = null
      this.isDragOver = false
      this.showDialog = true
    },
    openEditDialog(item) {
      this.form = { id: item.id, project: item.project || '', requirement_id: item.requirement_id, requirement_name: item.requirement_name, requirement_type: item.requirement_type, requirement_level: item.requirement_level, module: item.module, reviewer: item.reviewer, estimated_hours: item.estimated_hours, description: item.description, acceptance_criteria: item.acceptance_criteria || '' }
      this.selectedFile = null
      this.isDragOver = false
      this.showDialog = true
    },
    closeDialog() {
      this.showDialog = false
      this.selectedFile = null
      this.isDragOver = false
    },
    handleDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.handleFileSelect({ target: { files } })
      }
    },
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx|txt)$/i)) {
          ElMessage.error('仅支持 PDF、Word、TXT 格式的文件')
          return
        }
        if (file.size > 10 * 1024 * 1024) {
          ElMessage.error('文件大小不能超过 10MB')
          return
        }
        this.selectedFile = file
      }
    },
    removeFile() {
      this.selectedFile = null
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = ''
      }
    },
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    async saveRequirement() {
      if (!this.form.requirement_name || !this.form.description) {
        return ElMessage.error('请填写需求名称和需求描述')
      }
      if (!this.form.project) {
        return ElMessage.error('请选择关联项目')
      }
      if (this.form.description.length > 2000) {
        return ElMessage.error('需求描述不能超过 2000 字符')
      }

      this.isSaving = true
      try {
        // 如果有文件上传，先上传文档
        if (this.selectedFile && !this.form.id) {
          const formData = new FormData()
          formData.append('file', this.selectedFile)
          formData.append('title', this.form.requirement_name)
          formData.append('project', this.form.project)

          try {
            await api.post('/requirement-analysis/api/documents/upload/', formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
            })
            ElMessage.success('文档上传成功')
          } catch (error) {
            console.error('文档上传失败:', error)
            ElMessage.warning('文档上传失败，将仅保存需求信息')
          }
        }

        // 保存需求
        const payload = {
          project: this.form.project,
          requirement_id: this.form.requirement_id,
          requirement_name: this.form.requirement_name,
          requirement_type: this.form.requirement_type,
          requirement_level: this.form.requirement_level,
          module: this.form.module,
          reviewer: this.form.reviewer,
          estimated_hours: this.form.estimated_hours,
          description: this.form.description,
          acceptance_criteria: this.form.acceptance_criteria || ''
        }

        if (this.form.id) {
          await api.patch(`/requirement-analysis/api/requirements/${this.form.id}/`, payload)
          ElMessage.success('需求更新成功')
        }
        else {
          await api.post('/requirement-analysis/api/requirements/', payload)
          ElMessage.success('需求创建成功')
        }

        this.showDialog = false
        this.selectedFile = null
        await this.loadRequirements()
      } catch (error) {
        ElMessage.error('保存需求失败: ' + (error.response?.data?.error || error.message))
      }
      finally {
        this.isSaving = false
      }
    },
    async deleteRequirement(item) {
      try {
        await ElMessageBox.confirm(`确定删除需求「${item.requirement_name}」吗？`, '确认删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
        await api.delete(`/requirement-analysis/api/requirements/${item.id}/`)
        ElMessage.success('删除成功')
        await this.loadRequirements()
      } catch (error) { if (error !== 'cancel') ElMessage.error('删除失败') }
    },
    async auditRequirement(item) {
      try {
        await ElMessageBox.confirm(`确定审核通过需求「${item.requirement_name}」吗？`, '需求审核', { confirmButtonText: '审核通过', cancelButtonText: '取消', type: 'warning' })
        this.isAuditing = true
        const response = await api.post(`/requirement-analysis/api/requirements/${item.id}/audit/`, { audit_status: 'approved' })
        ElMessage.success(response.data.message || '审核成功')
        const updatedRequirement = response.data.requirement
        const index = this.requirements.findIndex(requirement => requirement.id === item.id)
        if (index !== -1 && updatedRequirement) {
          this.requirements.splice(index, 1, updatedRequirement)
        } else {
          await this.loadRequirements()
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('审核失败: ' + (error.response?.data?.error || error.message))
        }
      } finally {
        this.isAuditing = false
      }
    },
    formatDateTime(dateTimeString) {
      if (!dateTimeString) return '-'
      const d = new Date(dateTimeString)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    }
  }
}
</script>

<style scoped>
.ai-requirements-page { padding: 20px; }
.page-header { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; margin-bottom:16px; flex-wrap:wrap; }
.toolbar-card, .table-card { background:#fff; border-radius:10px; padding:16px; margin-bottom:16px; }
.header-filters { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
.header-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-left:auto; }
.filter-item { display:flex; align-items:center; gap:8px; }
.filter-item label { white-space:nowrap; }
.filter-item input, .filter-item select { width:220px; padding:8px; border:1px solid #ddd; border-radius:6px; }
button { border:none; border-radius:6px; padding:8px 12px; cursor:pointer; transition:all .3s; }
button:disabled { opacity:.5; cursor:not-allowed; }
.create-btn, .save-btn { background:#27ae60; color:#fff; padding:10px 24px; font-size:14px; font-weight:500; }
.create-btn:hover:not(:disabled), .save-btn:hover:not(:disabled) { background:#2ecc71; }
.search-btn, .refresh-btn, .edit-btn, .view-btn { background:#409eff; color:#fff; }
.search-btn:hover:not(:disabled), .refresh-btn:hover:not(:disabled), .edit-btn:hover:not(:disabled), .view-btn:hover:not(:disabled) { background:#66b1ff; }
.generate-btn, .batch-generate-btn { background:#e67e22; color:#fff; }
.generate-btn:hover:not(:disabled), .batch-generate-btn:hover:not(:disabled) { background:#f39c12; }
.audit-btn { background:#13c2c2; color:#fff; }
.audit-btn:hover:not(:disabled) { background:#36cfc9; }
.ai-dev-btn { background:#9c27b0; color:#fff; }
.ai-dev-btn:hover:not(:disabled) { background:#ba68c8; }
.delete-btn, .cancel-btn { background:#f56c6c; color:#fff; padding:10px 24px; font-size:14px; }
.delete-btn:hover:not(:disabled), .cancel-btn:hover:not(:disabled) { background:#f78989; }
.requirement-name-link { color:#409eff; cursor:pointer; text-decoration:underline; }
.requirement-name-link:hover { color:#66b1ff; }
.table-card { overflow-x:auto; }
.empty { text-align:center; color:#999; padding:40px 0; }
table { width:100%; min-width:1320px; border-collapse:collapse; }
th, td { border-bottom:1px solid #f0f0f0; padding:10px 8px; text-align:left; font-size:14px; }
.actions { display:flex; gap:8px; flex-wrap:wrap; min-width:360px; }
.status-tag { display:inline-block; padding:4px 10px; border-radius:12px; font-size:12px; color:#fff; }
.status-tag.not_generated { background:#909399; }
.status-tag.generating { background:#e6a23c; }
.status-tag.generated { background:#67c23a; }
.status-tag.failed { background:#f56c6c; }
.audit-status-tag { display:inline-block; padding:4px 10px; border-radius:12px; font-size:12px; color:#fff; white-space:nowrap; }
.audit-status-tag.pending { background:#909399; }
.audit-status-tag.approved { background:#67c23a; }
.audit-status-tag.rejected { background:#f56c6c; }
.dialog-mask { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:1000; }
.dialog { width:640px; max-height:90vh; overflow:auto; background:#fff; border-radius:10px; padding:20px; }
.detail-dialog { width:800px; }
.edit-dialog { width:960px; max-height:90vh; }
.dialog-header { display:flex; justify-content:space-between; align-items:center; padding-bottom:16px; border-bottom:2px solid #e8e8e8; margin-bottom:20px; }
.dialog-header h3 { margin:0; font-size:20px; color:#303133; }
.close-btn { background:none; border:none; font-size:20px; color:#909399; cursor:pointer; padding:4px 8px; }
.close-btn:hover { color:#f56c6c; }
.dialog-body { max-height:calc(90vh - 180px); overflow-y:auto; padding:0 4px; }
.main-section { margin-bottom:24px; }
.config-section, .upload-section { margin-bottom:24px; padding:20px; background:#f5f7fa; border-radius:8px; }
.section-title { font-size:16px; font-weight:600; color:#303133; margin-bottom:16px; }
.config-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:16px; }
.form-group { margin-bottom:16px; }
.form-group label { display:block; margin-bottom:8px; font-weight:500; color:#606266; font-size:14px; }
.required { color:#f56c6c; margin-left:4px; }
.form-input, .form-select, .form-textarea { width:100%; padding:10px 12px; border:1px solid #dcdfe6; border-radius:6px; font-size:14px; transition:border-color .2s; }
.form-input:focus, .form-select:focus, .form-textarea:focus { outline:none; border-color:#409eff; }
.form-textarea { resize:vertical; min-height:120px; font-family:inherit; line-height:1.6; }
.char-count { text-align:right; font-size:12px; color:#909399; margin-top:4px; }
.upload-area { border:2px dashed #dcdfe6; border-radius:8px; padding:30px; text-align:center; transition:all .3s; cursor:pointer; background:#fafafa; }
.upload-area:hover, .upload-area.drag-over { border-color:#409eff; background:#f0f7ff; }
.upload-placeholder { display:flex; flex-direction:column; align-items:center; gap:12px; }
.upload-icon { font-size:48px; }
.upload-placeholder p { margin:0; color:#606266; }
.upload-hint { font-size:12px; color:#909399; }
.select-file-btn { padding:8px 20px; background:#409eff; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:14px; }
.select-file-btn:hover { background:#66b1ff; }
.file-selected { padding:20px; }
.file-info { display:flex; align-items:center; gap:12px; background:#fff; padding:16px; border-radius:8px; }
.file-icon { font-size:32px; }
.file-details { flex:1; }
.file-name { margin:0; font-weight:500; color:#303133; }
.file-size { margin:4px 0 0; font-size:12px; color:#909399; }
.remove-file { background:none; border:none; cursor:pointer; font-size:18px; }
.remove-file:hover { opacity:.7; }
.dialog-footer { display:flex; justify-content:flex-end; gap:12px; margin-top:20px; padding-top:16px; border-top:1px solid #e8e8e8; }
.form-item { margin-bottom:12px; display:flex; flex-direction:column; gap:6px; }
.form-item input, .form-item select, .form-item textarea { border:1px solid #ddd; border-radius:6px; padding:8px; }
.workflow-detail-panel { margin-top: 16px; }
.dialog-actions { display:flex; justify-content:flex-end; gap:8px; margin-top:12px; }
.detail-content { margin:16px 0; }
.detail-row { display:flex; margin-bottom:12px; }
.detail-row label { font-weight:600; min-width:100px; color:#606266; }
.detail-row span { flex:1; color:#303133; }
.detail-row.full-width { flex-direction:column; }
.detail-row.full-width label { margin-bottom:6px; }
.detail-text { white-space:pre-wrap; background:#f5f7fa; padding:12px; border-radius:6px; line-height:1.6; color:#303133; }
</style>

