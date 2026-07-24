export const JIRA_BUG_FIELD_DEFINITIONS = [
  { key: 'issuetype', label: '任务类型', visible: false },
  { key: 'issuekey', label: '缺陷编号', visible: true, minWidth: 140, filterLimit: 40, fixed: 'left' },
  { key: 'summary', label: '缺陷标题', visible: true, minWidth: 320, filterLimit: 20, overflow: true },
  { key: 'customfield_10762', label: '客户或项目名称', visible: true, minWidth: 180, filterLimit: 20, overflow: true },
  { key: 'customfield_10702', label: '任务优先级', visible: false },
  { key: 'customfield_10754', label: 'BUG处理反馈', visible: true, minWidth: 180, filterLimit: 20, overflow: true },
  { key: 'customfield_11101', label: 'BUG定性分类', visible: true, minWidth: 140, filterLimit: 20, overflow: true },
  { key: 'customfield_11102', label: 'BUG产生根因', visible: true, minWidth: 180, filterLimit: 20, overflow: true },
  { key: 'customfield_11103', label: 'BUG直接责任岗位', visible: true, minWidth: 160, filterLimit: 20, overflow: true },
  { key: 'components', label: '模块', visible: true, minWidth: 140, filterLimit: 20, overflow: true },
  { key: 'status', label: '状态', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'creator', label: '创建人', visible: true, minWidth: 110, filterLimit: 20 },
  { key: 'customfield_10222', label: '测试人员', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_11100', label: '版本内研发优先级别', visible: true, minWidth: 160, filterLimit: 20 },
  { key: 'customfield_10743', label: '前端', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10741', label: '后端', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10746', label: '测试进度', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10761', label: '测试预估工时', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10738', label: 'PM进度', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10100', label: '必须发版', visible: true, minWidth: 110, filterLimit: 20 },
  { key: 'customfield_10737', label: 'PM', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_11000', label: '组别', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10523', label: '前端开始日期', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'customfield_11017', label: '前端结束日期', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'customfield_10522', label: '后端开始日期', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'customfield_11019', label: '后端结束日期', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'created', label: '创建日期', visible: true, minWidth: 180, filterLimit: 20 },
  { key: 'customfield_10014', label: '预计提测日期', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'customfield_11018', label: '提测时间', visible: true, minWidth: 140, filterLimit: 20 },
  { key: 'customfield_10765', label: '整体进度|延期原因', visible: true, minWidth: 180, filterLimit: 20, overflow: true },
  { key: 'customfield_10015', label: '用例预估完成时间', visible: true, minWidth: 160, filterLimit: 20 },
  { key: 'customfield_11020', label: '测试进展', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10749', label: '前端预估工时', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10748', label: '后端预估工时', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10731', label: 'BUG责任人', visible: true, minWidth: 120, filterLimit: 20 },
  { key: 'customfield_10019', label: 'BUG重新打开次数', visible: true, minWidth: 140, filterLimit: 20 },
]

export const JIRA_BUG_VISIBLE_FIELD_DEFINITIONS = JIRA_BUG_FIELD_DEFINITIONS.filter(
  field => field.visible !== false
)

export const JIRA_BUG_VISIBLE_FIELD_KEYS = JIRA_BUG_VISIBLE_FIELD_DEFINITIONS.map(field => field.key)

export const JIRA_BUG_HIDDEN_FIELD_KEYS = JIRA_BUG_FIELD_DEFINITIONS
  .filter(field => field.visible === false)
  .map(field => field.key)

export const JIRA_BUG_FIELD_LABELS = JIRA_BUG_FIELD_DEFINITIONS.reduce((labels, field) => {
  labels[field.key] = field.label
  return labels
}, {})

export const JIRA_BUG_ALL_FIELD_KEYS = new Set([
  ...JIRA_BUG_VISIBLE_FIELD_KEYS,
  ...JIRA_BUG_HIDDEN_FIELD_KEYS,
])
