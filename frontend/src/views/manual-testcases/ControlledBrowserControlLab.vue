<template>
  <div class="control-lab manual-workspace-density-scope">
    <ManualWorkspaceSectionTabs
      class="workspace-section-tabs"
      :items="workspaceSectionTabs"
      active-name="controlled-browser-lab"
      @select="handleWorkspaceSectionSelect"
    />

    <div class="lab-header">
      <div>
        <h2>模拟页面组件</h2>
        <p>用于验证平台受控浏览器录制时，各类页面控件是否能真实交互并被捕获。</p>
      </div>
      <div class="header-actions">
        <el-button @click="resetAll">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
        <el-button type="primary" @click="submitAll">
          <el-icon><Check /></el-icon>
          提交测试
        </el-button>
      </div>
    </div>

    <div class="lab-grid">
      <section class="lab-section">
        <div class="section-title">原生表单控件</div>
        <div class="native-grid">
          <label class="field">
            <span>文本输入</span>
            <input v-model="nativeForm.text" type="text" placeholder="输入中文、英文、符号" @input="logChange('文本输入', nativeForm.text)" />
          </label>
          <label class="field">
            <span>密码输入</span>
            <input v-model="nativeForm.password" type="password" placeholder="password" @input="logChange('密码输入', '******')" />
          </label>
          <label class="field">
            <span>搜索框</span>
            <input v-model="nativeForm.search" type="search" list="search-suggestions" placeholder="输入关键词" @change="logChange('搜索框', nativeForm.search)" />
            <datalist id="search-suggestions">
              <option value="登录流程" />
              <option value="订单查询" />
              <option value="用户管理" />
            </datalist>
          </label>
          <label class="field">
            <span>数字</span>
            <input v-model.number="nativeForm.number" type="number" min="0" max="100" step="1" @change="logChange('数字', nativeForm.number)" />
          </label>
          <label class="field">
            <span>日期</span>
            <input v-model="nativeForm.date" type="date" @change="logChange('日期', nativeForm.date)" />
          </label>
          <label class="field">
            <span>时间</span>
            <input v-model="nativeForm.time" type="time" @change="logChange('时间', nativeForm.time)" />
          </label>
          <label class="field">
            <span>颜色</span>
            <input v-model="nativeForm.color" type="color" @input="logChange('颜色', nativeForm.color)" />
          </label>
          <label class="field">
            <span>范围</span>
            <input v-model.number="nativeForm.range" type="range" min="0" max="10" @input="logChange('范围', nativeForm.range)" />
          </label>
          <label class="field wide">
            <span>文本域</span>
            <textarea v-model="nativeForm.textarea" rows="4" placeholder="多行文本输入" @input="logChange('文本域', nativeForm.textarea)" />
          </label>
          <label class="field">
            <span>原生下拉</span>
            <select v-model="nativeForm.select" @change="logChange('原生下拉', nativeForm.select)">
              <option value="">请选择</option>
              <option value="draft">草稿</option>
              <option value="active">启用</option>
              <option value="archived">归档</option>
            </select>
          </label>
          <label class="field">
            <span>多选下拉</span>
            <select multiple :value="nativeForm.multiSelect" @change="handleNativeMultiSelect">
              <option value="input">输入框</option>
              <option value="select">下拉框</option>
              <option value="dialog">弹窗</option>
              <option value="table">表格</option>
            </select>
          </label>
          <div class="field inline-field">
            <span>复选框</span>
            <label><input v-model="nativeForm.checkboxA" type="checkbox" @change="logChange('复选框A', nativeForm.checkboxA)" /> A</label>
            <label><input v-model="nativeForm.checkboxB" type="checkbox" @change="logChange('复选框B', nativeForm.checkboxB)" /> B</label>
          </div>
          <div class="field inline-field">
            <span>单选框</span>
            <label><input v-model="nativeForm.radio" type="radio" value="male" @change="logChange('单选框', nativeForm.radio)" /> 男</label>
            <label><input v-model="nativeForm.radio" type="radio" value="female" @change="logChange('单选框', nativeForm.radio)" /> 女</label>
          </div>
          <label class="field">
            <span>文件上传</span>
            <input type="file" multiple @change="handleFileChange" />
          </label>
          <div class="field wide">
            <span>contenteditable</span>
            <div class="editable" contenteditable="true" @input="handleEditableInput">可编辑文本区域，测试输入法和光标。</div>
          </div>
        </div>

        <div class="native-actions">
          <button type="button" @click="logChange('原生按钮', '普通按钮')">普通按钮</button>
          <button type="button" @dblclick="logChange('原生按钮', '双击按钮')">双击按钮</button>
          <a href="#event-log" @click="logChange('链接点击', '跳转到日志')">锚点链接</a>
          <button type="button" @click="openNativeDialog">打开原生 dialog</button>
        </div>

        <details class="details-box" @toggle="logChange('details', $event.target.open ? '展开' : '收起')">
          <summary>展开更多原生控件说明</summary>
          <div class="details-content">这里用于测试 summary/details 的展开收起事件。</div>
        </details>

        <dialog ref="nativeDialog" class="native-dialog" @close="logChange('dialog', '关闭')">
          <div class="dialog-title">原生 dialog</div>
          <p>用于验证受控浏览器是否能操作浏览器原生弹层。</p>
          <button type="button" @click="closeNativeDialog">关闭</button>
        </dialog>
      </section>

      <section class="lab-section">
        <div class="section-title">Element Plus 组件</div>
        <el-form label-position="top" class="element-form">
          <el-form-item label="输入框">
            <el-input v-model="elementForm.input" clearable placeholder="Element 输入框" @input="logChange('Element 输入框', elementForm.input)" />
          </el-form-item>
          <el-form-item label="带建议输入">
            <el-autocomplete
              v-model="elementForm.autocomplete"
              :fetch-suggestions="querySuggestions"
              clearable
              placeholder="输入 l / o / u"
              @select="item => logChange('Autocomplete', item.value)"
            />
          </el-form-item>
          <el-form-item label="下拉框">
            <el-select v-model="elementForm.select" filterable clearable placeholder="请选择状态" @change="value => logChange('Element 下拉', value)">
              <el-option label="草稿" value="draft" />
              <el-option label="启用" value="active" />
              <el-option label="归档" value="archived" />
            </el-select>
          </el-form-item>
          <el-form-item label="级联选择">
            <el-cascader v-model="elementForm.cascader" :options="cascaderOptions" clearable @change="value => logChange('级联选择', value)" />
          </el-form-item>
          <el-form-item label="日期时间">
            <el-date-picker
              v-model="elementForm.datetime"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择日期时间"
              @change="value => logChange('日期时间', value)"
            />
          </el-form-item>
          <el-form-item label="时间">
            <el-time-picker
              v-model="elementForm.time"
              value-format="HH:mm:ss"
              placeholder="选择时间"
              @change="value => logChange('时间选择器', value)"
            />
          </el-form-item>
          <el-form-item label="数字步进">
            <el-input-number v-model="elementForm.number" :min="0" :max="50" @change="value => logChange('数字步进', value)" />
          </el-form-item>
          <el-form-item label="开关">
            <el-switch v-model="elementForm.switch" active-text="启用" inactive-text="关闭" @change="value => logChange('开关', value)" />
          </el-form-item>
          <el-form-item label="滑块">
            <el-slider v-model="elementForm.slider" show-input @change="value => logChange('滑块', value)" />
          </el-form-item>
          <el-form-item label="评分">
            <el-rate v-model="elementForm.rate" @change="value => logChange('评分', value)" />
          </el-form-item>
          <el-form-item label="复选框组">
            <el-checkbox-group v-model="elementForm.checkboxGroup" @change="value => logChange('复选框组', value)">
              <el-checkbox label="输入框" value="input" />
              <el-checkbox label="下拉框" value="select" />
              <el-checkbox label="弹窗" value="dialog" />
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="单选框组">
            <el-radio-group v-model="elementForm.radio" @change="value => logChange('单选框组', value)">
              <el-radio value="smoke">冒烟测试</el-radio>
              <el-radio value="regression">回归测试</el-radio>
              <el-radio value="acceptance">验收测试</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div class="component-actions">
          <el-dropdown @command="command => logChange('Dropdown', command)">
            <el-button>
              Dropdown
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="create">新建</el-dropdown-item>
                <el-dropdown-item command="edit">编辑</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="warning" @click="elDialogVisible = true">
            <el-icon><Bell /></el-icon>
            打开弹窗
          </el-button>
        </div>
      </section>
    </div>

    <section class="lab-section">
      <div class="section-title">
        <span>表格与标签页</span>
        <TableColumnSettings
          :table-ref="controlLabTableRef"
          storage-key="manual-testcases.controlled-browser-lab"
        />
      </div>
      <el-tabs v-model="activeTab" @tab-change="name => logChange('标签页', name)">
        <el-tab-pane label="流程步骤" name="steps">
          <el-table ref="controlLabTableRef" :data="tableRows" border stripe>
            <el-table-column prop="name" label="控件" min-width="160" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === '通过' ? 'success' : 'warning'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button link type="primary" @click="logChange('表格编辑', row.name)">编辑</el-button>
                <el-button link type="danger" @click="removeRow(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="结果汇总" name="summary">
          <pre class="summary-preview">{{ summaryText }}</pre>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section id="event-log" class="lab-section event-log-section">
      <div class="section-title">
        事件日志
        <el-button link type="danger" @click="clearLogs">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </div>
      <div class="event-log">
        <div v-for="item in eventLogs" :key="item.id" class="event-item">
          <span class="event-time">{{ item.time }}</span>
          <span class="event-name">{{ item.name }}</span>
          <span class="event-value">{{ item.value }}</span>
        </div>
        <el-empty v-if="!eventLogs.length" description="暂无事件" :image-size="72" />
      </div>
    </section>

    <el-dialog v-model="elDialogVisible" title="Element Plus 弹窗" width="420px">
      <el-form label-position="top">
        <el-form-item label="弹窗输入">
          <el-input v-model="elementForm.dialogInput" placeholder="在弹窗中输入内容" />
        </el-form-item>
        <el-form-item label="弹窗下拉">
          <el-select v-model="elementForm.dialogSelect" placeholder="请选择">
            <el-option label="选项 A" value="a" />
            <el-option label="选项 B" value="b" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="elDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDialog">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Bell, Check, Delete, Refresh } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceSectionTabs from '@/views/manual-testcases/ManualWorkspaceSectionTabs.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const nativeDialog = ref(null)
const controlLabTableRef = ref(null)
const elDialogVisible = ref(false)
const activeTab = ref('steps')
const eventLogs = ref([])
const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const nativeForm = reactive({
  text: '',
  password: '',
  search: '',
  number: 5,
  date: '',
  time: '',
  color: '#2563eb',
  range: 4,
  textarea: '',
  select: '',
  multiSelect: [],
  checkboxA: false,
  checkboxB: true,
  radio: 'male',
  editable: ''
})

const elementForm = reactive({
  input: '',
  autocomplete: '',
  select: '',
  cascader: [],
  datetime: '',
  time: '',
  number: 8,
  switch: true,
  slider: 36,
  rate: 3,
  checkboxGroup: ['input'],
  radio: 'smoke',
  dialogInput: '',
  dialogSelect: ''
})

const cascaderOptions = [
  {
    value: 'manual-testcases',
    label: '思源研发管理',
    children: [
      { value: 'snapshots', label: '快照管理' },
      { value: 'recordings', label: '录制管理' },
      { value: 'flows', label: '流程管理' }
    ]
  },
  {
    value: 'automation',
    label: '自动化测试',
    children: [
      { value: 'case', label: '用例' },
      { value: 'execution', label: '执行' }
    ]
  }
]

const tableRows = ref([
  { id: 1, name: '文本输入', type: 'input', status: '通过' },
  { id: 2, name: '下拉选择', type: 'select', status: '待验证' },
  { id: 3, name: '弹窗提交', type: 'dialog', status: '待验证' }
])

const suggestions = [
  { value: 'login' },
  { value: 'logout' },
  { value: 'order-create' },
  { value: 'user-search' }
]

const formatValue = value => {
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object' && value !== null) return JSON.stringify(value)
  if (value === '') return '空'
  return String(value)
}

const logChange = (name, value) => {
  eventLogs.value.unshift({
    id: `${Date.now()}-${Math.random()}`,
    time: new Date().toLocaleTimeString(),
    name,
    value: formatValue(value)
  })
  eventLogs.value = eventLogs.value.slice(0, 80)
}

const clearLogs = () => {
  eventLogs.value = []
}

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'controlled-browser-lab') {
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const handleNativeMultiSelect = event => {
  nativeForm.multiSelect = Array.from(event.target.selectedOptions).map(option => option.value)
  logChange('多选下拉', nativeForm.multiSelect)
}

const handleFileChange = event => {
  const files = Array.from(event.target.files || []).map(file => file.name)
  logChange('文件上传', files)
}

const handleEditableInput = event => {
  nativeForm.editable = event.target.innerText
  logChange('contenteditable', nativeForm.editable)
}

const openNativeDialog = () => {
  nativeDialog.value?.showModal?.()
  logChange('dialog', '打开')
}

const closeNativeDialog = () => {
  nativeDialog.value?.close?.()
}

const querySuggestions = (query, callback) => {
  const keyword = String(query || '').toLowerCase()
  callback(suggestions.filter(item => item.value.includes(keyword)))
}

const removeRow = row => {
  tableRows.value = tableRows.value.filter(item => item.id !== row.id)
  logChange('表格删除', row.name)
}

const resetAll = () => {
  Object.assign(nativeForm, {
    text: '',
    password: '',
    search: '',
    number: 5,
    date: '',
    time: '',
    color: '#2563eb',
    range: 4,
    textarea: '',
    select: '',
    multiSelect: [],
    checkboxA: false,
    checkboxB: true,
    radio: 'male',
    editable: ''
  })
  Object.assign(elementForm, {
    input: '',
    autocomplete: '',
    select: '',
    cascader: [],
    datetime: '',
    time: '',
    number: 8,
    switch: true,
    slider: 36,
    rate: 3,
    checkboxGroup: ['input'],
    radio: 'smoke',
    dialogInput: '',
    dialogSelect: ''
  })
  logChange('重置', '全部控件已恢复初始值')
}

const submitAll = () => {
  logChange('提交测试', '已提交当前控件状态')
  activeTab.value = 'summary'
}

const confirmDialog = () => {
  logChange('Element 弹窗确认', {
    input: elementForm.dialogInput,
    select: elementForm.dialogSelect
  })
  elDialogVisible.value = false
}

const summaryText = computed(() => JSON.stringify({
  nativeForm,
  elementForm,
  tableRows: tableRows.value
}, null, 2))
</script>

<style scoped>
.control-lab {
  min-height: 100%;
  padding: 20px;
  background: #f5f7fb;
  color: #1f2937;
}

.workspace-section-tabs {
  margin-bottom: 20px;
}

.lab-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.lab-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.lab-header p {
  margin: 6px 0 0;
  color: #6b7280;
}

.header-actions,
.native-actions,
.component-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.lab-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.lab-section {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  font-size: 16px;
  font-weight: 650;
}

.native-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  color: #4b5563;
}

.field.wide {
  grid-column: span 2;
}

.field input,
.field select,
.field textarea,
.editable {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  color: #111827;
  background: #fff;
}

.field select[multiple] {
  min-height: 82px;
}

.inline-field {
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
}

.inline-field > span {
  width: 100%;
}

.editable {
  min-height: 72px;
  line-height: 1.6;
}

.native-actions {
  margin-top: 14px;
}

.native-actions button,
.native-actions a {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  color: #1f2937;
  text-decoration: none;
  cursor: pointer;
}

.details-box {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
}

.details-content {
  margin-top: 10px;
  color: #6b7280;
}

.native-dialog {
  max-width: 360px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 18px;
}

.dialog-title {
  margin-bottom: 8px;
  font-weight: 650;
}

.element-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 14px;
}

.component-actions {
  margin-top: 8px;
}

.summary-preview {
  margin: 0;
  padding: 12px;
  max-height: 360px;
  overflow: auto;
  border-radius: 6px;
  background: #111827;
  color: #f9fafb;
  font-size: 12px;
  line-height: 1.5;
}

.event-log-section {
  scroll-margin-top: 16px;
}

.event-log {
  min-height: 120px;
  max-height: 320px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.event-item {
  display: grid;
  grid-template-columns: 96px 160px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
}

.event-item:last-child {
  border-bottom: none;
}

.event-time {
  color: #6b7280;
}

.event-name {
  font-weight: 600;
}

.event-value {
  min-width: 0;
  color: #374151;
  word-break: break-all;
}

@media (max-width: 1180px) {
  .lab-grid,
  .native-grid,
  .element-form {
    grid-template-columns: 1fr;
  }

  .field.wide {
    grid-column: span 1;
  }
}

@media (max-width: 720px) {
  .lab-header {
    flex-direction: column;
  }

  .event-item {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
