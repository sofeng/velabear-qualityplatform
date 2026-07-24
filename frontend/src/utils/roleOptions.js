import api from '@/utils/api'

const ROLE_ENDPOINT = '/auth/roles/'
const ROLE_PAGE_SIZE = 100

const normalizePagedData = (data) => {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
    }
  }

  return {
    results: Array.isArray(data?.results) ? data.results : [],
    count: Number(data?.count ?? 0),
  }
}

const normalizeText = value => String(value ?? '').trim()

const fetchAllRoles = async () => {
  const allResults = []
  let page = 1
  let total = 0

  while (true) {
    const response = await api.get(ROLE_ENDPOINT, {
      params: {
        page,
        page_size: ROLE_PAGE_SIZE,
        ordering: 'name',
      },
    })

    const { results, count } = normalizePagedData(response.data)
    total = count
    allResults.push(...results)

    if (!results.length || allResults.length >= total || results.length < ROLE_PAGE_SIZE) {
      break
    }

    page += 1
  }

  return allResults
}

const dedupeUsers = users => {
  const optionMap = new Map()

  ;(Array.isArray(users) ? users : []).forEach(user => {
    const userId = Number(user?.id)
    if (!Number.isInteger(userId) || userId <= 0) {
      return
    }

    optionMap.set(userId, user)
  })

  return [...optionMap.values()]
}

export const fetchRoleMemberOptions = async (roleName) => {
  const normalizedRoleName = normalizeText(roleName)
  if (!normalizedRoleName) {
    return []
  }

  const roles = await fetchAllRoles()
  const targetRole = roles.find(role => normalizeText(role?.name) === normalizedRoleName)
  if (!targetRole) {
    return []
  }

  return dedupeUsers(targetRole.members)
}
