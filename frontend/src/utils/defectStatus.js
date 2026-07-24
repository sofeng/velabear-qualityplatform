export const defectStatusOptions = Object.freeze([
  { label: '待处理', value: 'new' },
  { label: '处理中', value: 'in_progress' },
  { label: '提测', value: 'resolved' },
  { label: '打回待处理', value: 'returned_pending' },
  { label: '回归验证完成', value: 'regression_verified' },
  { label: '已拒绝', value: 'rejected' },
  { label: '暂不处理', value: 'deferred' },
  { label: '待客户环境验证', value: 'customer_validation' },
  { label: '待转新需求', value: 'pending_requirement' },
  { label: '已转新需求', value: 'requirement_created' },
  { label: '已关闭', value: 'closed' },
  { label: '重新打开', value: 'reopened' },
  { label: '已作废', value: 'invalid' },
])

const defectStatusLabelMap = Object.freeze(
  defectStatusOptions.reduce((result, option) => {
    result[option.value] = option.label
    return result
  }, {})
)

export const defectStatusTagTypes = Object.freeze({
  new: 'info',
  in_progress: 'warning',
  resolved: '',
  returned_pending: 'warning',
  regression_verified: 'success',
  rejected: 'danger',
  deferred: 'info',
  customer_validation: 'warning',
  pending_requirement: 'warning',
  requirement_created: 'success',
  closed: 'success',
  reopened: 'warning',
  invalid: 'info',
})

export const getDefectStatusLabel = value => defectStatusLabelMap[value] || value || '-'

export const getDefectStatusTagType = value => defectStatusTagTypes[value] ?? 'info'
