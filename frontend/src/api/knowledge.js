import request from '@/utils/api'

const createListGetter = url => params => request({
  url,
  method: 'get',
  params,
})

const createCreator = url => data => request({
  url,
  method: 'post',
  data,
})

const createUpdater = url => (id, data) => request({
  url: `${url}${id}/`,
  method: 'patch',
  data,
})

const createDeleter = url => id => request({
  url: `${url}${id}/`,
  method: 'delete',
})

const SPACES_URL = '/knowledge/spaces/'
const REPOSITORY_CONFIGS_URL = '/knowledge/repository-configs/'
const INDEX_RUNS_URL = '/knowledge/index-runs/'
const OBJECTS_URL = '/knowledge/objects/'
const GRAPH_URL = '/knowledge/graph/'
const ASSET_INSIGHT_URL = '/knowledge/asset-insight/'
const QUERY_CONTEXT_URL = '/knowledge/query-context/'
const PROJECT_KNOWLEDGE_STATUS_URL = '/knowledge/project-knowledge/status/'
const PROJECT_KNOWLEDGE_ENABLE_URL = '/knowledge/project-knowledge/enable/'
const FEEDBACK_URL = '/knowledge/feedback/'

export const getKnowledgeSpaces = createListGetter(SPACES_URL)
export const getKnowledgeRepositoryConfigs = createListGetter(REPOSITORY_CONFIGS_URL)
export const createKnowledgeRepositoryConfig = createCreator(REPOSITORY_CONFIGS_URL)
export const updateKnowledgeRepositoryConfig = createUpdater(REPOSITORY_CONFIGS_URL)
export const deleteKnowledgeRepositoryConfig = createDeleter(REPOSITORY_CONFIGS_URL)
export const getKnowledgeIndexRuns = createListGetter(INDEX_RUNS_URL)
export const getKnowledgeObjects = createListGetter(OBJECTS_URL)
export const getKnowledgeFeedback = createListGetter(FEEDBACK_URL)
export const createKnowledgeFeedback = createCreator(FEEDBACK_URL)

export function testKnowledgeRepositoryConnection(id) {
  return request({
    url: `${REPOSITORY_CONFIGS_URL}${id}/test-connection/`,
    method: 'post',
  })
}

export function testKnowledgeRepositoryDatabaseSchema(id) {
  return request({
    url: `${REPOSITORY_CONFIGS_URL}${id}/test-database-schema/`,
    method: 'post',
  })
}

export function authorizeKnowledgeRepository(id) {
  return request({
    url: `${REPOSITORY_CONFIGS_URL}${id}/authorize/`,
    method: 'post',
  })
}

export function indexKnowledgeRepository(id) {
  return request({
    url: `${REPOSITORY_CONFIGS_URL}${id}/index/`,
    method: 'post',
    timeout: 120000,
  })
}

export function seedCurrentPlatformKnowledgeRepository(data = {}) {
  return request({
    url: `${REPOSITORY_CONFIGS_URL}seed-current-platform/`,
    method: 'post',
    data,
  })
}

export function getKnowledgeGraph(params) {
  return request({
    url: GRAPH_URL,
    method: 'get',
    params,
  })
}

export function getKnowledgeAssetInsight(params) {
  return request({
    url: ASSET_INSIGHT_URL,
    method: 'get',
    params,
    timeout: 60000,
  })
}

export function getProjectKnowledgeStatus(params) {
  return request({
    url: PROJECT_KNOWLEDGE_STATUS_URL,
    method: 'get',
    params,
  })
}

export function enableProjectKnowledge(data) {
  return request({
    url: PROJECT_KNOWLEDGE_ENABLE_URL,
    method: 'post',
    data,
    timeout: 60000,
  })
}

export function queryKnowledgeContext(data) {
  return request({
    url: QUERY_CONTEXT_URL,
    method: 'post',
    data,
    timeout: 30000,
  })
}

export function getKnowledgeRepositoryModeChoices() {
  return [
    { value: 'local_path', label: '本地路径仓库' },
    { value: 'remote', label: '远程 Git 仓库' },
  ]
}

export function getKnowledgeProviderChoices() {
  return [
    { value: 'local', label: '本地仓库' },
    { value: 'git', label: 'Git' },
    { value: 'github', label: 'GitHub' },
    { value: 'gitlab', label: 'GitLab' },
    { value: 'gitee', label: 'Gitee' },
  ]
}

export function getKnowledgeAuthModeChoices() {
  return [
    { value: 'none', label: '无需凭据' },
    { value: 'token', label: 'Token' },
    { value: 'ssh', label: 'SSH Key' },
    { value: 'oauth', label: '授权页面' },
    { value: 'github_app', label: 'GitHub App' },
  ]
}
