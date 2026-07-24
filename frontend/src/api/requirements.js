import api from '@/utils/api'

const hasOwn = (target, key) => Object.prototype.hasOwnProperty.call(target, key)
const normalizeArray = (value) => (Array.isArray(value) ? value : [])

const buildRequirementFormData = (payload = {}) => {
  if (payload instanceof FormData) {
    return payload
  }

  const formData = new FormData()
  const scalarFields = [
    'version',
    'issue_id',
    'issue_key',
    'issue_type',
    'summary',
    'description',
    'module',
    'customer_name',
    'priority',
    'status',
    'creator',
    'handler',
    'tester',
    'group_name',
    'frontend_developer',
    'backend_developer',
    'row_index',
  ]

  scalarFields.forEach((field) => {
    if (!hasOwn(payload, field)) {
      return
    }

    const value = payload[field]
    formData.append(field, value === null || value === undefined ? '' : String(value))
  })

  if (hasOwn(payload, 'raw_fields')) {
    formData.append('raw_fields', JSON.stringify(payload.raw_fields || {}))
  }

  ;['related_mindmaps', 'retain_attachment_ids'].forEach((field) => {
    if (!hasOwn(payload, field)) {
      return
    }

    formData.append(field, JSON.stringify(normalizeArray(payload[field])))
  })

  normalizeArray(payload.attachments).forEach((file) => {
    if (file) {
      formData.append('attachments', file)
    }
  })

  return formData
}

export const getRequirementRecordDetail = (id) =>
  api.get(`/quality-analysis/jira-requirement-records/${id}/`)

export const createRequirementRecord = (payload) =>
  api.post('/quality-analysis/jira-requirement-records/', buildRequirementFormData(payload))

export const updateRequirementRecord = (id, payload) =>
  api.put(`/quality-analysis/jira-requirement-records/${id}/`, buildRequirementFormData(payload))

export const deleteRequirementRecord = (id) =>
  api.delete(`/quality-analysis/jira-requirement-records/${id}/`)

export default {
  getRequirementRecordDetail,
  createRequirementRecord,
  updateRequirementRecord,
  deleteRequirementRecord,
}
