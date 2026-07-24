import api from '@/utils/api'

const GROUP_ENDPOINT = '/auth/groups/'
const GROUP_PAGE_SIZE = 100

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

export const fetchAllGroupOptions = async () => {
  const allResults = []
  let page = 1
  let total = 0

  while (true) {
    const response = await api.get(GROUP_ENDPOINT, {
      params: {
        page,
        page_size: GROUP_PAGE_SIZE,
      },
    })

    const { results, count } = normalizePagedData(response.data)
    total = count
    allResults.push(...results)

    if (!results.length || allResults.length >= total || results.length < GROUP_PAGE_SIZE) {
      break
    }

    page += 1
  }

  const optionMap = new Map()
  allResults.forEach((item) => {
    const normalizedName = String(item?.name || '').trim()
    if (!normalizedName) {
      return
    }

    optionMap.set(normalizedName, {
      id: item.id,
      name: normalizedName,
    })
  })

  return [...optionMap.values()].sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'))
}
