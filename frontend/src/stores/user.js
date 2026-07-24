import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api from '@/utils/api'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const TOKEN_EXPIRES_AT_KEY = 'token_expires_at'
const USER_KEY = 'user'
const AUTH_EVENT_KEY = 'auth_state_event'
const REFRESH_LOCK_KEY = 'auth_refresh_lock'
const AUTH_CHANNEL_NAME = 'testhub-auth-state'
const DEFAULT_AUTHENTICATED_PATH = '/manual-testcases/list'

const REFRESH_BUFFER_MS = 5 * 60 * 1000
const REFRESH_LOCK_TTL_MS = 15 * 1000
const WAIT_FOR_SHARED_REFRESH_MS = 15 * 1000
const FALLBACK_ACCESS_TOKEN_TTL_MS = 55 * 60 * 1000
const TAB_ID = `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`
const AUTH_STORAGE_KEYS = new Set([
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  USER_KEY,
  AUTH_EVENT_KEY,
])

const hasWindow = () => typeof window !== 'undefined'

const readStorageItem = key => {
  if (!hasWindow()) {
    return ''
  }

  try {
    return window.localStorage.getItem(key) || ''
  } catch (error) {
    console.error('Failed to read auth storage:', error)
    return ''
  }
}

const writeStorageItem = (key, value) => {
  if (!hasWindow()) {
    return
  }

  try {
    window.localStorage.setItem(key, value)
  } catch (error) {
    console.error('Failed to write auth storage:', error)
  }
}

const removeStorageItem = key => {
  if (!hasWindow()) {
    return
  }

  try {
    window.localStorage.removeItem(key)
  } catch (error) {
    console.error('Failed to remove auth storage:', error)
  }
}

const parseJson = (value, fallback = null) => {
  if (!value) {
    return fallback
  }

  try {
    return JSON.parse(value)
  } catch (error) {
    console.error('Failed to parse auth storage JSON:', error)
    return fallback
  }
}

const parseStoredInteger = value => {
  const parsedValue = Number.parseInt(value || '0', 10)
  return Number.isFinite(parsedValue) ? parsedValue : 0
}

const decodeBase64Url = value => {
  if (!value) {
    return ''
  }

  const normalizedValue = value.replace(/-/g, '+').replace(/_/g, '/')
  const padding = normalizedValue.length % 4
  const paddedValue = padding ? `${normalizedValue}${'='.repeat(4 - padding)}` : normalizedValue

  if (hasWindow() && typeof window.atob === 'function') {
    return window.atob(paddedValue)
  }

  if (typeof atob === 'function') {
    return atob(paddedValue)
  }

  return ''
}

const decodeJwtExpiresAt = token => {
  if (!token) {
    return 0
  }

  try {
    const [, payload] = token.split('.')
    const decodedPayload = parseJson(decodeBase64Url(payload), {})
    const expiresAt = Number(decodedPayload?.exp || 0) * 1000
    return Number.isFinite(expiresAt) ? expiresAt : 0
  } catch (error) {
    console.error('Failed to decode auth token expiry:', error)
    return 0
  }
}

const resolveTokenExpiresAt = token => (
  decodeJwtExpiresAt(token) || Date.now() + FALLBACK_ACCESS_TOKEN_TTL_MS
)

const readStoredAuthState = () => ({
  accessToken: readStorageItem(ACCESS_TOKEN_KEY),
  refreshToken: readStorageItem(REFRESH_TOKEN_KEY),
  tokenExpiresAt: parseStoredInteger(readStorageItem(TOKEN_EXPIRES_AT_KEY)),
  user: parseJson(readStorageItem(USER_KEY), null),
})

const isStoredAccessTokenFresh = (state, bufferMs = 0) => {
  if (!state.accessToken) {
    return false
  }

  if (!state.tokenExpiresAt) {
    return true
  }

  return state.tokenExpiresAt - Date.now() > bufferMs
}

const readRefreshLock = () => parseJson(readStorageItem(REFRESH_LOCK_KEY), null)

const hasActiveRefreshLock = lock => (
  Boolean(lock?.owner) && Number(lock.expiresAt || 0) > Date.now()
)

const acquireRefreshLock = () => {
  const currentLock = readRefreshLock()
  if (hasActiveRefreshLock(currentLock) && currentLock.owner !== TAB_ID) {
    return false
  }

  const nextLock = {
    owner: TAB_ID,
    expiresAt: Date.now() + REFRESH_LOCK_TTL_MS,
  }
  writeStorageItem(REFRESH_LOCK_KEY, JSON.stringify(nextLock))

  return readRefreshLock()?.owner === TAB_ID
}

const releaseRefreshLock = () => {
  if (readRefreshLock()?.owner === TAB_ID) {
    removeStorageItem(REFRESH_LOCK_KEY)
  }
}

const sleep = ms => new Promise(resolve => window.setTimeout(resolve, ms))

const isPublicAuthFreePath = path => (
  path === '/login'
  || path === '/register'
  || path.startsWith('/quality-analysis/share/')
  || path.startsWith('/quality-analysis/live-share/')
)

const redirectToLoginIfNeeded = () => {
  if (!hasWindow()) {
    return
  }

  const { pathname } = window.location
  if (!isPublicAuthFreePath(pathname)) {
    window.location.replace('/login')
  }
}

const redirectAuthenticatedAuthPage = () => {
  if (!hasWindow()) {
    return
  }

  const { pathname } = window.location
  if (pathname === '/login' || pathname === '/register') {
    window.location.replace(DEFAULT_AUTHENTICATED_PATH)
  }
}

const authChannel = hasWindow() && typeof window.BroadcastChannel === 'function'
  ? new window.BroadcastChannel(AUTH_CHANNEL_NAME)
  : null

const publishAuthEvent = type => {
  const payload = {
    type,
    source: TAB_ID,
    at: Date.now(),
  }

  writeStorageItem(AUTH_EVENT_KEY, JSON.stringify(payload))

  try {
    authChannel?.postMessage(payload)
  } catch (error) {
    console.error('Failed to broadcast auth state:', error)
  }
}

const normalizePermissionCodes = value => {
  if (!Array.isArray(value)) {
    return []
  }

  const dedupedCodes = []
  const seenCodes = new Set()

  value.forEach(item => {
    const normalizedCode = String(item || '').trim()
    if (!normalizedCode || seenCodes.has(normalizedCode)) {
      return
    }

    seenCodes.add(normalizedCode)
    dedupedCodes.push(normalizedCode)
  })

  return dedupedCodes
}

export const useUserStore = defineStore('user', () => {
  const initialAuthState = readStoredAuthState()
  const user = ref(initialAuthState.user)
  const accessToken = ref(initialAuthState.accessToken)
  const refreshToken = ref(initialAuthState.refreshToken)
  const tokenExpiresAt = ref(initialAuthState.tokenExpiresAt)

  let isLoggingOut = false
  let refreshPromise = null
  let initAuthPromise = null
  let authListenersRegistered = false

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))
  const isTokenExpiringSoon = computed(() => {
    if (!tokenExpiresAt.value) {
      return false
    }

    return tokenExpiresAt.value - Date.now() < REFRESH_BUFFER_MS
  })
  const isTokenExpired = computed(() => {
    if (!tokenExpiresAt.value) {
      return false
    }

    return Date.now() > tokenExpiresAt.value
  })
  const effectivePermissionCodes = computed(() => normalizePermissionCodes(user.value?.effective_permission_codes))
  const effectivePermissionCodeSet = computed(() => new Set(effectivePermissionCodes.value))

  const applyAuthState = state => {
    accessToken.value = state.accessToken || ''
    refreshToken.value = state.refreshToken || ''
    tokenExpiresAt.value = Number(state.tokenExpiresAt || 0)
    user.value = state.user || null
    return state
  }

  const syncAuthStateFromStorage = () => applyAuthState(readStoredAuthState())

  const persistAuthState = (eventType = 'update') => {
    if (accessToken.value) {
      writeStorageItem(ACCESS_TOKEN_KEY, accessToken.value)
    } else {
      removeStorageItem(ACCESS_TOKEN_KEY)
    }

    if (refreshToken.value) {
      writeStorageItem(REFRESH_TOKEN_KEY, refreshToken.value)
    } else {
      removeStorageItem(REFRESH_TOKEN_KEY)
    }

    if (tokenExpiresAt.value) {
      writeStorageItem(TOKEN_EXPIRES_AT_KEY, String(tokenExpiresAt.value))
    } else {
      removeStorageItem(TOKEN_EXPIRES_AT_KEY)
    }

    if (user.value) {
      writeStorageItem(USER_KEY, JSON.stringify(user.value))
    } else {
      removeStorageItem(USER_KEY)
    }

    publishAuthEvent(eventType)
  }

  const clearAuthState = ({ broadcast = true, redirectToLogin = false } = {}) => {
    accessToken.value = ''
    refreshToken.value = ''
    tokenExpiresAt.value = 0
    user.value = null

    removeStorageItem(ACCESS_TOKEN_KEY)
    removeStorageItem(REFRESH_TOKEN_KEY)
    removeStorageItem(TOKEN_EXPIRES_AT_KEY)
    removeStorageItem(USER_KEY)
    releaseRefreshLock()

    if (broadcast) {
      publishAuthEvent('logout')
    }

    if (redirectToLogin) {
      redirectToLoginIfNeeded()
    }
  }

  const handleExternalAuthEvent = payload => {
    if (payload?.source === TAB_ID) {
      return
    }

    const nextState = syncAuthStateFromStorage()
    if (payload?.type === 'logout' || (!nextState.accessToken && !nextState.refreshToken)) {
      redirectToLoginIfNeeded()
      return
    }

    if (payload?.type === 'login') {
      redirectAuthenticatedAuthPage()
    }
  }

  const registerAuthStateListeners = () => {
    if (!hasWindow() || authListenersRegistered) {
      return
    }

    authListenersRegistered = true

    window.addEventListener('storage', event => {
      if (event.key && !AUTH_STORAGE_KEYS.has(event.key)) {
        return
      }

      const payload = event.key === AUTH_EVENT_KEY ? parseJson(event.newValue, null) : null
      if (payload?.source === TAB_ID) {
        return
      }

      const nextState = syncAuthStateFromStorage()
      if (payload?.type === 'logout' || (!nextState.accessToken && !nextState.refreshToken)) {
        redirectToLoginIfNeeded()
        return
      }

      if (payload?.type === 'login') {
        redirectAuthenticatedAuthPage()
      }
    })

    authChannel?.addEventListener('message', event => {
      handleExternalAuthEvent(event.data)
    })
  }

  registerAuthStateListeners()

  const hasPermissionCode = code => {
    const normalizedCode = String(code || '').trim()
    if (!normalizedCode) {
      return false
    }

    if (user.value?.is_staff || user.value?.is_superuser) {
      return true
    }

    return effectivePermissionCodeSet.value.has(normalizedCode)
  }

  const hasAnyPermissionCode = codes => {
    const candidateCodes = Array.isArray(codes) ? codes : [codes]
    return candidateCodes.some(code => hasPermissionCode(code))
  }

  const login = async credentials => {
    const response = await api.post('/auth/login/', credentials)

    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    user.value = response.data.user
    tokenExpiresAt.value = resolveTokenExpiresAt(accessToken.value)

    persistAuthState('login')
    return response.data
  }

  const register = async userData => {
    const response = await api.post('/auth/test-register/', userData)
    return response.data
  }

  const sendEmailVerificationCode = async email => {
    const response = await api.post('/auth/send-email-code/', { email })
    return response.data
  }

  const loginWithEmailCode = async ({ email, code }) => {
    const response = await api.post('/auth/email-code-login/', { email, code })

    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    user.value = response.data.user
    tokenExpiresAt.value = resolveTokenExpiresAt(accessToken.value)

    persistAuthState('login')
    return response.data
  }

  const logout = async ({ notifyServer = true, redirectToLogin = true, broadcast = true } = {}) => {
    if (isLoggingOut) {
      return
    }

    isLoggingOut = true
    const currentRefreshToken = refreshToken.value || readStoredAuthState().refreshToken

    try {
      if (notifyServer && currentRefreshToken) {
        try {
          await api.post('/auth/logout/', { refresh: currentRefreshToken })
        } catch (apiError) {
          console.error('Logout API failed:', apiError)
        }
      }
    } finally {
      clearAuthState({ broadcast, redirectToLogin })
      isLoggingOut = false
    }
  }

  const waitForSharedRefresh = async (previousAccessToken, previousRefreshToken) => {
    const deadline = Date.now() + WAIT_FOR_SHARED_REFRESH_MS

    while (Date.now() < deadline) {
      const nextState = syncAuthStateFromStorage()
      const accessTokenChanged = nextState.accessToken && nextState.accessToken !== previousAccessToken
      const refreshTokenChanged = nextState.refreshToken && nextState.refreshToken !== previousRefreshToken

      if ((accessTokenChanged || refreshTokenChanged) && isStoredAccessTokenFresh(nextState, 0)) {
        return nextState.accessToken
      }

      if (!nextState.accessToken && !nextState.refreshToken) {
        throw new Error('Authentication state was cleared')
      }

      const currentLock = readRefreshLock()
      if (!hasActiveRefreshLock(currentLock) || currentLock.owner === TAB_ID) {
        return ''
      }

      await sleep(150)
    }

    return ''
  }

  const refreshAccessTokenWithSharedLock = async ({ force = false } = {}) => {
    const initialState = syncAuthStateFromStorage()
    if (!force && isStoredAccessTokenFresh(initialState, REFRESH_BUFFER_MS)) {
      return initialState.accessToken
    }

    if (!initialState.refreshToken) {
      await logout({ notifyServer: false })
      throw new Error('Missing refresh token')
    }

    let ownsRefreshLock = acquireRefreshLock()
    if (!ownsRefreshLock) {
      const sharedToken = await waitForSharedRefresh(initialState.accessToken, initialState.refreshToken)
      if (sharedToken) {
        return sharedToken
      }

      ownsRefreshLock = acquireRefreshLock()
    }

    if (!ownsRefreshLock) {
      throw new Error('Unable to acquire auth refresh lock')
    }

    try {
      const requestState = syncAuthStateFromStorage()
      if (!force && isStoredAccessTokenFresh(requestState, REFRESH_BUFFER_MS)) {
        return requestState.accessToken
      }

      const requestRefreshToken = requestState.refreshToken
      if (!requestRefreshToken) {
        await logout({ notifyServer: false })
        throw new Error('Missing refresh token')
      }

      const response = await api.post('/auth/token/refresh/', {
        refresh: requestRefreshToken,
      })

      accessToken.value = response.data.access
      refreshToken.value = response.data.refresh || requestRefreshToken
      tokenExpiresAt.value = resolveTokenExpiresAt(accessToken.value)
      persistAuthState('refresh')

      return accessToken.value
    } catch (error) {
      console.error('Token refresh failed:', error)
      const latestState = syncAuthStateFromStorage()
      const latestAccessChanged = latestState.accessToken && latestState.accessToken !== initialState.accessToken
      const latestRefreshChanged = latestState.refreshToken && latestState.refreshToken !== initialState.refreshToken

      if ((latestAccessChanged || latestRefreshChanged) && isStoredAccessTokenFresh(latestState, 0)) {
        return latestState.accessToken
      }

      if (error.response?.status === 401 || error.response?.status === 403) {
        await logout({ notifyServer: false })
      }

      throw error
    } finally {
      releaseRefreshLock()
    }
  }

  const refreshAccessToken = async (options = {}) => {
    if (!refreshPromise) {
      refreshPromise = refreshAccessTokenWithSharedLock(options)
        .finally(() => {
          refreshPromise = null
        })
    }

    return refreshPromise
  }

  const fetchUser = async () => {
    try {
      const response = await api.get('/users/me/')
      user.value = response.data
      persistAuthState('profile')
    } catch (error) {
      if (error.response?.status === 401 && !refreshToken.value && !readStoredAuthState().refreshToken) {
        clearAuthState({ broadcast: true, redirectToLogin: false })
      }
      throw error
    }
  }

  const fetchProfile = async () => {
    try {
      const response = await api.get('/auth/profile/')
      user.value = response.data
      persistAuthState('profile')
      return response.data
    } catch (error) {
      if (error.response?.status === 401 && !refreshToken.value && !readStoredAuthState().refreshToken) {
        clearAuthState({ broadcast: true, redirectToLogin: false })
      }
      throw error
    }
  }

  const initAuthOnce = async () => {
    syncAuthStateFromStorage()
    console.log('initAuth start', {
      hasAccessToken: Boolean(accessToken.value),
      hasRefreshToken: Boolean(refreshToken.value),
      hasUser: Boolean(user.value),
      isExpired: isTokenExpired.value,
    })

    if (!accessToken.value && refreshToken.value) {
      try {
        await refreshAccessToken({ force: true })
      } catch (error) {
        console.error('Token refresh during init failed:', error)
        return
      }
    }

    if (!accessToken.value) {
      console.log('No access token, skip auth init')
      return
    }

    if (isTokenExpired.value && refreshToken.value) {
      console.log('Access token expired, try refresh')
      try {
        await refreshAccessToken({ force: true })
      } catch (error) {
        console.error('Token refresh during init failed:', error)
        return
      }
    }

    try {
      await fetchProfile()
      console.log('Profile synced', {
        username: user.value?.username,
        permissionCount: effectivePermissionCodes.value.length,
      })
    } catch (error) {
      console.error('Profile sync failed:', error)
      if (!user.value && !refreshToken.value && !readStoredAuthState().refreshToken) {
        clearAuthState({ broadcast: true, redirectToLogin: false })
      }
    }
  }

  const initAuth = async () => {
    if (!initAuthPromise) {
      initAuthPromise = initAuthOnce()
        .finally(() => {
          initAuthPromise = null
        })
    }

    return initAuthPromise
  }

  return {
    user,
    accessToken,
    refreshToken,
    tokenExpiresAt,
    isAuthenticated,
    isTokenExpiringSoon,
    isTokenExpired,
    effectivePermissionCodes,
    effectivePermissionCodeSet,
    hasPermissionCode,
    hasAnyPermissionCode,
    login,
    register,
    sendEmailVerificationCode,
    loginWithEmailCode,
    logout,
    clearAuthState,
    syncAuthStateFromStorage,
    refreshAccessToken,
    fetchUser,
    fetchProfile,
    initAuth,
  }
})
