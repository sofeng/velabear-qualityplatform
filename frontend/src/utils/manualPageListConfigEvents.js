export const MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT = 'testhub-manual-page-list-config-updated'

export function notifyManualPageListConfigUpdated(payload = {}) {
  if (typeof window === 'undefined') {
    return
  }

  window.dispatchEvent(new CustomEvent(MANUAL_PAGE_LIST_CONFIG_UPDATED_EVENT, {
    detail: payload,
  }))
}

export function isManualPageListConfigUpdateForStorage(event, storageKey) {
  const detail = event?.detail || {}
  const storageKeys = Array.isArray(detail.storage_keys) ? detail.storage_keys : []
  return Boolean(
    storageKey && (
      detail.storage_key === storageKey ||
      storageKeys.includes(storageKey)
    )
  )
}
