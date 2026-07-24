import api from '@/utils/api'

export const getWikiDirectories = (params = {}) =>
  api.get('/defects/wiki-directories/', { params })

export const createWikiDirectory = (payload = {}) =>
  api.post('/defects/wiki-directories/', payload)

export const updateWikiDirectory = (id, payload = {}) =>
  api.patch(`/defects/wiki-directories/${id}/`, payload)

export const deleteWikiDirectory = id =>
  api.delete(`/defects/wiki-directories/${id}/`)

export const getWikiPages = (params = {}) =>
  api.get('/defects/wiki-pages/', { params })

export const getWikiPageDetail = id =>
  api.get(`/defects/wiki-pages/${id}/`)

export const createWikiPage = (payload = {}) =>
  api.post('/defects/wiki-pages/', payload)

export const updateWikiPage = (id, payload = {}) =>
  api.patch(`/defects/wiki-pages/${id}/`, payload)

export const deleteWikiPage = id =>
  api.delete(`/defects/wiki-pages/${id}/`)

export default {
  getWikiDirectories,
  createWikiDirectory,
  updateWikiDirectory,
  deleteWikiDirectory,
  getWikiPages,
  getWikiPageDetail,
  createWikiPage,
  updateWikiPage,
  deleteWikiPage,
}
