import api from '@/utils/api'

const hasOwn = (target, key) => Object.prototype.hasOwnProperty.call(target, key)

const normalizeArray = (value) => (Array.isArray(value) ? value : [])

const buildDefectFormData = (payload = {}) => {
  if (payload instanceof FormData) {
    return payload
  }

  const formData = new FormData()
  const scalarFields = [
    'project_id',
    'version_id',
    'title',
    'description',
    'problem_reason',
    'root_cause',
    'frontend_developer',
    'backend_developer',
    'priority',
    'severity',
    'status',
    'requirement_id',
  ]

  scalarFields.forEach((field) => {
    if (!hasOwn(payload, field)) {
      return
    }

    const value = payload[field]
    formData.append(field, value === null || value === undefined ? '' : String(value))
  })

  ;['labels', 'assignee_ids', 'retain_attachment_ids'].forEach((field) => {
    if (!hasOwn(payload, field)) {
      return
    }

    formData.append(field, JSON.stringify(normalizeArray(payload[field])))
  })

  ;['modules', 'related_testcases', 'related_testpoints'].forEach((field) => {
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

export const getDefects = (params = {}) => api.get('/defects/', { params })

export const getDefectDetail = (id) => api.get(`/defects/${id}/`)

export const createDefect = (payload) => api.post('/defects/', buildDefectFormData(payload))

export const updateDefect = (id, payload) => api.put(`/defects/${id}/`, buildDefectFormData(payload))

export const patchDefect = (id, payload) => api.patch(`/defects/${id}/`, buildDefectFormData(payload))

export const deleteDefect = (id) => api.delete(`/defects/${id}/`)

export const importDefectExcel = ({ projectId, versionId, file }) => {
  const formData = new FormData()
  formData.append('project_id', String(projectId || ''))
  formData.append('version_id', String(versionId || ''))
  if (file) {
    formData.append('file', file)
  }
  return api.post('/defects/import-excel/', formData, {
    timeout: 10 * 60 * 1000,
  })
}

export const updateDefectStatus = (id, status) => api.post(`/defects/${id}/status/`, { status })

export const updateDefectAssignees = (id, assigneeIds = []) =>
  api.post(`/defects/${id}/assignees/`, { assignee_ids: assigneeIds })

export const addDefectComment = (id, content) => api.post(`/defects/${id}/comments/`, { content })

export const updateDefectComment = (id, commentId, content) =>
  api.put(`/defects/${id}/comments/${commentId}/`, { content })

export const getDefectHistory = (id, params = {}) => api.get(`/defects/${id}/history/`, { params })

export const getDefectEmailConfig = () => api.get('/defects/email-config/')

export const saveDefectEmailConfig = (payload) => api.put('/defects/email-config/', payload)

export const testDefectEmailConfig = (payload) => api.post('/defects/email-config/test-send/', payload)

export const verifyDefectEmailConfig = () => api.post('/defects/email-config/verify-smtp/')

export const getDefectNotificationSettings = () => api.get('/defects/notification-settings/')

export const saveDefectNotificationSettings = (payload) => api.put('/defects/notification-settings/', payload)

export const searchJiraRequirementRecords = (params = {}) =>
  api.get('/quality-analysis/jira-requirement-records/', { params })

export const getManualCategories = (params = {}) =>
  api.get('/testcases/manual-categories/', { params, timeout: 0 })

export const searchManualMindmapNodes = (params = {}) =>
  api.get('/testcases/manual-mindmap-nodes/', { params })

export const uploadDefectRichTextImages = (files = []) => {
  const formData = new FormData()
  normalizeArray(files).forEach((file) => {
    if (file) {
      formData.append('images', file)
    }
  })
  return api.post('/defects/rich-text-images/', formData)
}

export default {
  getDefects,
  getDefectDetail,
  createDefect,
  updateDefect,
  patchDefect,
  deleteDefect,
  importDefectExcel,
  updateDefectStatus,
  updateDefectAssignees,
  addDefectComment,
  updateDefectComment,
  getDefectHistory,
  getDefectEmailConfig,
  saveDefectEmailConfig,
  testDefectEmailConfig,
  verifyDefectEmailConfig,
  getDefectNotificationSettings,
  saveDefectNotificationSettings,
  searchJiraRequirementRecords,
  getManualCategories,
  searchManualMindmapNodes,
  uploadDefectRichTextImages,
}
