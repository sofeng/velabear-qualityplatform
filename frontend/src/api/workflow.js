import api from '@/utils/api'

export const startWorkflow = (bizType, bizId) => api.post(`/workflow/${bizType}/${bizId}/start/`)

export const getWorkflowInstance = (bizType, bizId) => api.get(`/workflow/${bizType}/${bizId}/instance/`)

export const getMyWorkflowTasks = (params = {}) => api.get('/workflow/tasks/my/', { params })

export const getWorkflowInstances = (params = {}) => api.get('/workflow/instances/', { params })

export const getWorkflowDefinitions = (params = {}) => api.get('/workflow/definitions/', { params })
export const updateWorkflowDefinition = (definitionId, payload = {}) => api.put(`/workflow/definitions/${definitionId}/`, payload)
export const getWorkflowDefinitionVersions = (definitionId) => api.get(`/workflow/definitions/${definitionId}/versions/`)
export const restoreWorkflowDefinition = (definitionId) => api.post(`/workflow/definitions/${definitionId}/restore/`)
export const simulateWorkflowDefinition = (payload = {}) => api.post('/workflow/definitions/simulate/', payload)
export const bootstrapWorkflowCatalog = () => api.post('/workflow/bootstrap/')

export const getWorkflowRules = (params = {}) => api.get('/workflow/rules/', { params })

export const createWorkflowRule = (payload = {}) => api.post('/workflow/rules/', payload)

export const updateWorkflowRule = (ruleId, payload = {}) => api.put(`/workflow/rules/${ruleId}/`, payload)

export const deleteWorkflowRule = (ruleId) => api.delete(`/workflow/rules/${ruleId}/`)

export const executeWorkflowTaskAction = (taskId, payload = {}) =>
  api.post(`/workflow/tasks/${taskId}/action/`, payload)

export const terminateWorkflowInstance = (instanceId, payload = {}) =>
  api.post(`/workflow/instances/${instanceId}/terminate/`, payload)

export const runWorkflowEscalations = () => api.post('/workflow/run-escalations/')

export default {
  startWorkflow,
  getWorkflowInstance,
  getMyWorkflowTasks,
  getWorkflowInstances,
  getWorkflowDefinitions,
  updateWorkflowDefinition,
  getWorkflowDefinitionVersions,
  restoreWorkflowDefinition,
  simulateWorkflowDefinition,
  bootstrapWorkflowCatalog,
  getWorkflowRules,
  createWorkflowRule,
  updateWorkflowRule,
  deleteWorkflowRule,
  executeWorkflowTaskAction,
  terminateWorkflowInstance,
  runWorkflowEscalations,
}
