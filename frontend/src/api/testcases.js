/**
 * 测试用例模块相关 API
 */
import request from '@/utils/api'

export function getPlaywrightRecordings(params) {
  return request({
    url: '/testcases/playwright-recordings/',
    method: 'get',
    params
  })
}

export function startPlaywrightRecording(data) {
  return request({
    url: '/testcases/playwright-recordings/',
    method: 'post',
    data,
    timeout: 60000
  })
}

export function generatePlaywrightRecordingScript(data) {
  return request({
    url: '/testcases/playwright-recording-scripts/generate/',
    method: 'post',
    data,
    timeout: 120000
  })
}

export function getPlaywrightAutomationScripts(params) {
  return request({
    url: '/testcases/playwright-automation-scripts/',
    method: 'get',
    params
  })
}

export function createPlaywrightAutomationScript(data) {
  return request({
    url: '/testcases/playwright-automation-scripts/',
    method: 'post',
    data
  })
}

export function getPlaywrightAutomationScriptDetail(scriptId) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/`,
    method: 'get'
  })
}

export function updatePlaywrightAutomationScript(scriptId, data) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/`,
    method: 'patch',
    data
  })
}

export function deletePlaywrightAutomationScript(scriptId) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/`,
    method: 'delete'
  })
}

export function getPlaywrightAutomationScriptVersions(scriptId) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/versions/`,
    method: 'get'
  })
}

export function createPlaywrightAutomationScriptVersion(scriptId, data) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/versions/`,
    method: 'post',
    data
  })
}

export function restorePlaywrightAutomationScriptVersion(scriptId, version, data = {}) {
  return request({
    url: `/testcases/playwright-automation-scripts/${encodeURIComponent(scriptId)}/versions/${encodeURIComponent(version)}/restore/`,
    method: 'post',
    data
  })
}

export function getLocalAgentRecordingPayload(sessionId, token) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/agent/`,
    method: 'get',
    params: { token }
  })
}

export function downloadLocalAgentPackage() {
  return request({
    url: '/testcases/local-agent/package/',
    method: 'get',
    responseType: 'blob',
    timeout: 60000
  })
}

export function getPlaywrightRecordingSettings() {
  return request({
    url: '/testcases/playwright-recordings/settings/',
    method: 'get'
  })
}

export function updatePlaywrightRecordingSettings(data) {
  return request({
    url: '/testcases/playwright-recordings/settings/',
    method: 'patch',
    data
  })
}

export function getManualWorkspacePageListRegistry() {
  return request({
    url: '/testcases/manual-workspace-page-list-registry/',
    method: 'get'
  })
}

export function getManualWorkspacePageListConfig(params = {}) {
  return request({
    url: '/testcases/manual-workspace-page-list-config/',
    method: 'get',
    params
  })
}

export function saveManualWorkspacePageListConfig(data) {
  return request({
    url: '/testcases/manual-workspace-page-list-config/',
    method: 'put',
    data
  })
}

export function restoreManualWorkspacePageListConfig(data) {
  return request({
    url: '/testcases/manual-workspace-page-list-config/restore-default/',
    method: 'post',
    data
  })
}

export function getPlaywrightRecordingDetail(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/`,
    method: 'get'
  })
}

export function updatePlaywrightRecording(sessionId, data) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/`,
    method: 'patch',
    data
  })
}

export function createPlaywrightRecordingFlow(sessionId, data = {}) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/create-flow/`,
    method: 'post',
    data
  })
}

export function deletePlaywrightRecordingStep(sessionId, stepId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/steps/${encodeURIComponent(stepId)}/`,
    method: 'delete'
  })
}

export function identifyPlaywrightRecordingJunkSteps(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/identify-junk-steps/`,
    method: 'post'
  })
}

export function batchDeletePlaywrightRecordingSteps(sessionId, stepIds) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/steps/batch-delete/`,
    method: 'post',
    data: { step_ids: stepIds }
  })
}

export function dedupePlaywrightRecordingSnapshots(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/dedupe-snapshots/`,
    method: 'post'
  })
}

export function generatePlaywrightRecordingAllureReport(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/allure-report/`,
    method: 'post',
    timeout: 120000
  })
}

export function getVisualFlows(params) {
  return request({
    url: '/testcases/visual-flows/',
    method: 'get',
    params
  })
}

export function createVisualFlow(data) {
  return request({
    url: '/testcases/visual-flows/',
    method: 'post',
    data
  })
}

export function getVisualFlowDetail(flowId) {
  return request({
    url: `/testcases/visual-flows/${encodeURIComponent(flowId)}/`,
    method: 'get'
  })
}

export function updateVisualFlow(flowId, data) {
  return request({
    url: `/testcases/visual-flows/${encodeURIComponent(flowId)}/`,
    method: 'patch',
    data
  })
}

export function copyVisualFlow(flowId, data) {
  return request({
    url: `/testcases/visual-flows/${encodeURIComponent(flowId)}/copy/`,
    method: 'post',
    data
  })
}

export function batchCopyVisualFlows(data) {
  return request({
    url: '/testcases/visual-flows/batch-copy/',
    method: 'post',
    data
  })
}

export function deleteVisualFlow(flowId) {
  return request({
    url: `/testcases/visual-flows/${encodeURIComponent(flowId)}/`,
    method: 'delete'
  })
}

export function stopPlaywrightRecording(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/stop/`,
    method: 'post'
  })
}

export function deletePlaywrightRecording(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/`,
    method: 'delete'
  })
}

export function getPlaywrightRecordingFlow(sessionId) {
  return request({
    url: `/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/flow/`,
    method: 'get'
  })
}

export function getProjectList(params = {}) {
  return request({
    url: '/projects/list/',
    method: 'get',
    params
  })
}

export function getManualCategories(params = {}) {
  return request({
    url: '/testcases/manual-categories/',
    method: 'get',
    params,
    timeout: 0
  })
}

export function importManualCategoriesFromXMind({ projectId, parentId = null, xmindFile }) {
  const data = new FormData()
  data.append('project_id', projectId)
  if (parentId !== null && parentId !== undefined && parentId !== '') {
    data.append('parent_id', parentId)
  }
  data.append('xmind_file', xmindFile)
  return request({
    url: '/testcases/manual-categories/import-xmind/',
    method: 'post',
    data
  })
}

// ==================== 手工用例脑图 ====================

// 获取手工用例脑图列表
export function getManualMindmaps(params) {
  return request({
    url: '/testcases/manual-mindmaps/',
    method: 'get',
    params
  })
}

// 获取手工用例脑图详情
export function getManualMindmapDetail(id) {
  return request({
    url: `/testcases/manual-mindmaps/${id}/`,
    method: 'get'
  })
}

// 创建手工用例脑图
export function createManualMindmap(data) {
  return request({
    url: '/testcases/manual-mindmaps/',
    method: 'post',
    data
  })
}

// 更新手工用例脑图
export function updateManualMindmap(id, data) {
  return request({
    url: `/testcases/manual-mindmaps/${id}/`,
    method: 'put',
    data
  })
}

// 删除手工用例脑图
export function deleteManualMindmap(id) {
  return request({
    url: `/testcases/manual-mindmaps/${id}/`,
    method: 'delete'
  })
}

// ==================== Playwright快照文件 ====================

/**
 * 获取Playwright快照文件列表
 * @returns {Promise} 快照文件列表
 */
export function getPlaywrightSnapshots(params) {
  return request({
    url: '/testcases/playwright-snapshots/',
    method: 'get',
    params
  })
}

/**
 * 获取Playwright快照文件内容
 * @param {string} filename - 快照文件名
 * @returns {Promise} 快照文件内容和元数据
 */
export function getPlaywrightSnapshotContent(filename) {
  return request({
    url: `/testcases/playwright-snapshots/${encodeURIComponent(filename)}/`,
    method: 'get'
  })
}

export function createPlaywrightSnapshot(data) {
  return request({
    url: '/testcases/playwright-snapshots/',
    method: 'post',
    data
  })
}

export function uploadPlaywrightSnapshots(formData) {
  return request({
    url: '/testcases/playwright-snapshots/',
    method: 'post',
    data: formData
  })
}

export function updatePlaywrightSnapshot(filename, data) {
  return request({
    url: `/testcases/playwright-snapshots/${encodeURIComponent(filename)}/`,
    method: 'put',
    data
  })
}

export function savePlaywrightSnapshotParseResult(filename, data) {
  return request({
    url: `/testcases/playwright-snapshots/${encodeURIComponent(filename)}/parse/`,
    method: 'post',
    data
  })
}

export function deletePlaywrightSnapshot(filename) {
  return request({
    url: `/testcases/playwright-snapshots/${encodeURIComponent(filename)}/`,
    method: 'delete'
  })
}

export function downloadPlaywrightSnapshot(filename) {
  return request({
    url: `/testcases/playwright-snapshots/${encodeURIComponent(filename)}/download/`,
    method: 'get',
    responseType: 'blob'
  })
}

export function exportPlaywrightSnapshots(filenames) {
  return request({
    url: '/testcases/playwright-snapshots/export/',
    method: 'post',
    data: { filenames },
    responseType: 'blob'
  })
}

/**
 * 执行Playwright脚本
 * @param {string} script - Python脚本内容
 * @returns {Promise} 执行结果
 */
export function executePlaywrightScript(script) {
  return request({
    url: '/testcases/playwright-execute/',
    method: 'post',
    data: { script },
    timeout: 330000
  })
}

export function executeVisualFlowScript(data) {
  return request({
    url: '/testcases/playwright-execute/',
    method: 'post',
    data: {
      ...data,
      async: true
    },
    timeout: 60000
  })
}

export function getVisualFlowExecutions(params = {}) {
  return request({
    url: '/testcases/visual-flow-executions/',
    method: 'get',
    params
  })
}

export function createVisualFlowExecution(data = {}) {
  return request({
    url: '/testcases/visual-flow-executions/',
    method: 'post',
    data
  })
}

export function getVisualFlowExecutionDetail(executionId) {
  return request({
    url: `/testcases/visual-flow-executions/${encodeURIComponent(executionId)}/`,
    method: 'get'
  })
}

export function ingestVisualFlowExecutionEvents(executionId, events) {
  return request({
    url: `/testcases/visual-flow-executions/${encodeURIComponent(executionId)}/events/`,
    method: 'post',
    data: { events }
  })
}

export function finalizeVisualFlowExecution(executionId, data) {
  return request({
    url: `/testcases/visual-flow-executions/${encodeURIComponent(executionId)}/finalize/`,
    method: 'post',
    data
  })
}
