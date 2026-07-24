import { effectScope, watch } from 'vue'
import { ElNotification } from 'element-plus'

let notificationScope = null
let eventSource = null
let activeToken = ''

const NOTIFICATION_TITLES = {
  new: '新缺陷提醒',
  assign: '缺陷指派提醒',
  title: '缺陷标题变更',
  description: '缺陷描述变更',
  status: '缺陷状态变更',
  comment: '缺陷评论提醒',
}

const isBrowserNotificationSupported = () =>
  typeof window !== 'undefined' &&
  typeof Notification !== 'undefined' &&
  window.isSecureContext !== false

export const getCurrentPlatformOrigin = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.location.origin || ''
}

const buildDefectUrl = payload => {
  if (typeof window === 'undefined') {
    return payload?.url || ''
  }

  const fallbackPath = `/manual-testcases/defects/${payload?.defect_id || ''}/edit`
  const rawUrl = payload?.url || fallbackPath
  const normalizeDefectEditPath = pathname => {
    const normalizedPath = String(pathname || '')
    if (/^\/manual-testcases\/defects\/[^/]+\/edit\/?$/.test(normalizedPath)) {
      return normalizedPath
    }
    return normalizedPath.replace(
      /^\/manual-testcases\/defects\/([^/]+)\/?$/,
      '/manual-testcases/defects/$1/edit'
    )
  }

  try {
    const platformOrigin = getCurrentPlatformOrigin()
    const targetUrl = new URL(rawUrl, platformOrigin ? `${platformOrigin}/` : window.location.href)
    const normalizedPath = normalizeDefectEditPath(targetUrl.pathname)
    return `${platformOrigin}${normalizedPath}${targetUrl.search}${targetUrl.hash}`
  } catch (_error) {
    const normalizedPath = normalizeDefectEditPath(rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`)
    return `${getCurrentPlatformOrigin()}${normalizedPath}`
  }
}

const openDefectEdit = payload => {
  const targetUrl = buildDefectUrl(payload)
  if (!targetUrl || typeof window === 'undefined') {
    return
  }

  window.open(targetUrl, '_blank', 'noopener,noreferrer')
}

const closeEventSource = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  activeToken = ''
}

const showBrowserNotification = payload => {
  if (!isBrowserNotificationSupported() || Notification.permission !== 'granted') {
    return
  }

  const notification = new Notification(NOTIFICATION_TITLES[payload.type] || '缺陷提醒', {
    body: payload.message || '',
  })

  notification.onclick = event => {
    if (event?.preventDefault) {
      event.preventDefault()
    }
    if (typeof window !== 'undefined' && typeof window.focus === 'function') {
      window.focus()
    }
    openDefectEdit(payload)
    notification.close()
  }
}

const showBottomRightNotification = payload => {
  ElNotification({
    title: NOTIFICATION_TITLES[payload.type] || '缺陷提醒',
    message: payload.message || '你有一条新的缺陷通知',
    position: 'bottom-right',
    duration: 6000,
    onClick: () => openDefectEdit(payload),
  })
}

const handleEventMessage = event => {
  try {
    const payload = JSON.parse(event.data || '{}')
    if (!payload || !payload.defect_id) {
      return
    }

    showBottomRightNotification(payload)
    showBrowserNotification(payload)
  } catch (error) {
    console.error('解析缺陷通知消息失败:', error)
  }
}

const connectEventSource = token => {
  if (typeof window === 'undefined' || typeof EventSource === 'undefined' || !token) {
    return
  }

  closeEventSource()
  activeToken = token
  eventSource = new EventSource(`/api/defects/notifications/stream/?token=${encodeURIComponent(token)}`)
  eventSource.onmessage = handleEventMessage
  eventSource.onerror = () => {
    if (!eventSource) {
      return
    }
    console.warn('缺陷通知连接出现异常，浏览器将自动尝试重连')
  }
}

export const getDefectNotificationPermissionState = () => {
  if (!isBrowserNotificationSupported()) {
    return 'unsupported'
  }
  return Notification.permission
}

export const requestDefectNotificationPermission = async () => {
  if (!isBrowserNotificationSupported()) {
    return 'unsupported'
  }

  if (Notification.permission === 'granted') {
    return 'granted'
  }

  try {
    return await Notification.requestPermission()
  } catch (error) {
    console.error('申请浏览器通知权限失败:', error)
    return Notification.permission
  }
}

export const showDefectNotificationPermissionPreview = () => {
  if (!isBrowserNotificationSupported() || Notification.permission !== 'granted') {
    return false
  }

  try {
    const notification = new Notification('BearAI 消息提醒已开启', {
      body: `${getCurrentPlatformOrigin()} 已允许弹出浏览器通知`,
      tag: 'testhub-defect-notification-permission',
    })
    notification.onclick = event => {
      if (event?.preventDefault) {
        event.preventDefault()
      }
      if (typeof window !== 'undefined' && typeof window.focus === 'function') {
        window.focus()
      }
      notification.close()
    }
    return true
  } catch (error) {
    console.error('显示浏览器通知预览失败:', error)
    return false
  }
}

export const initDefectNotificationService = userStore => {
  if (notificationScope || typeof window === 'undefined') {
    return
  }

  notificationScope = effectScope(true)
  notificationScope.run(() => {
    watch(
      () => [userStore.isAuthenticated, userStore.accessToken, userStore.user?.id],
      ([isAuthenticated, token]) => {
        if (!isAuthenticated || !token) {
          closeEventSource()
          return
        }

        if (token !== activeToken || !eventSource) {
          connectEventSource(token)
        }
      },
      { immediate: true }
    )
  })
}
