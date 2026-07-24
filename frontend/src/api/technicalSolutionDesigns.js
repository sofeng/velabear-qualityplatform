import api from '@/utils/api'

const hasOwn = (target, key) => Object.prototype.hasOwnProperty.call(target, key)

const normalizeArray = (value) => (Array.isArray(value) ? value : [])

const buildTechnicalSolutionDesignFormData = (payload = {}) => {
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

export const getTechnicalSolutionDesigns = (params = {}) =>
  api.get('/defects/technical-solution-designs/', { params })

export const getTechnicalSolutionDesignDetail = (id) =>
  api.get(`/defects/technical-solution-designs/${id}/`)

export const createTechnicalSolutionDesign = (payload) =>
  api.post('/defects/technical-solution-designs/', buildTechnicalSolutionDesignFormData(payload))

export const updateTechnicalSolutionDesign = (id, payload) =>
  api.put(`/defects/technical-solution-designs/${id}/`, buildTechnicalSolutionDesignFormData(payload))

export const patchTechnicalSolutionDesign = (id, payload) =>
  api.patch(`/defects/technical-solution-designs/${id}/`, buildTechnicalSolutionDesignFormData(payload))

export const deleteTechnicalSolutionDesign = (id) =>
  api.delete(`/defects/technical-solution-designs/${id}/`)

export const importTechnicalSolutionDesignExcel = ({ projectId, versionId, file }) => {
  const formData = new FormData()
  formData.append('project_id', String(projectId || ''))
  formData.append('version_id', String(versionId || ''))
  if (file) {
    formData.append('file', file)
  }
  return api.post('/defects/technical-solution-designs/import-excel/', formData, {
    timeout: 10 * 60 * 1000,
  })
}

export const updateTechnicalSolutionDesignStatus = (id, status) =>
  api.post(`/defects/technical-solution-designs/${id}/status/`, { status })

export const updateTechnicalSolutionDesignAssignees = (id, assigneeIds = []) =>
  api.post(`/defects/technical-solution-designs/${id}/assignees/`, { assignee_ids: assigneeIds })

export const addTechnicalSolutionDesignComment = (id, content) =>
  api.post(`/defects/technical-solution-designs/${id}/comments/`, { content })

export const updateTechnicalSolutionDesignComment = (id, commentId, content) =>
  api.put(`/defects/technical-solution-designs/${id}/comments/${commentId}/`, { content })

export const getTechnicalSolutionDesignHistory = (id, params = {}) =>
  api.get(`/defects/technical-solution-designs/${id}/history/`, { params })

export const searchJiraRequirementRecords = (params = {}) =>
  api.get('/quality-analysis/jira-requirement-records/', { params })

export const getManualCategories = (params = {}) =>
  api.get('/testcases/manual-categories/', { params, timeout: 0 })

export const searchManualMindmapNodes = (params = {}) =>
  api.get('/testcases/manual-mindmap-nodes/', { params })

export const uploadTechnicalSolutionDesignRichTextImages = (files = []) => {
  const formData = new FormData()
  normalizeArray(files).forEach((file) => {
    if (file) {
      formData.append('images', file)
    }
  })
  return api.post('/defects/rich-text-images/', formData)
}

export default {
  getTechnicalSolutionDesigns,
  getTechnicalSolutionDesignDetail,
  createTechnicalSolutionDesign,
  updateTechnicalSolutionDesign,
  patchTechnicalSolutionDesign,
  deleteTechnicalSolutionDesign,
  importTechnicalSolutionDesignExcel,
  updateTechnicalSolutionDesignStatus,
  updateTechnicalSolutionDesignAssignees,
  addTechnicalSolutionDesignComment,
  updateTechnicalSolutionDesignComment,
  getTechnicalSolutionDesignHistory,
  searchJiraRequirementRecords,
  getManualCategories,
  searchManualMindmapNodes,
  uploadTechnicalSolutionDesignRichTextImages,
}
