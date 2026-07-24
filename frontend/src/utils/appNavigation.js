import {
  getManualTestcasePrimaryTabMenuItems,
  hasPermissionAccess,
  isHomeCardVisible,
} from '@/utils/permissions'

export const APP_TOPBAR_HEIGHT = 68

export const MODULE_SWITCHER_ITEMS = Object.freeze([
  {
    key: 'manual-testcases',
    cardKey: 'manual',
    label: '思源质量',
  },
])

export const MODULE_MENU_MAP = Object.freeze({
  'manual-testcases': Object.freeze(getManualTestcasePrimaryTabMenuItems()),
})

export const getModuleKeyFromPath = rawPath => {
  const path = String(rawPath || '').trim()
  if (path.startsWith('/manual-testcases')) return 'manual-testcases'
  if (path.startsWith('/profile')) return 'manual-testcases'
  if (path.startsWith('/home')) return 'home'
  return ''
}

export const getModuleLabel = moduleKey => (
  MODULE_SWITCHER_ITEMS.find(item => item.key === moduleKey)?.label || ''
)

export const getModuleMenuItems = (moduleKey, hasPermissionCode) => {
  const menuItems = MODULE_MENU_MAP[moduleKey] || []
  return menuItems.filter(item => {
    if (typeof hasPermissionCode !== 'function') return false
    const permissionCandidates = item.permissionCodes || item.permissionCode
    if (!permissionCandidates) return true
    return hasPermissionAccess(permissionCandidates, hasPermissionCode)
  })
}

export const getModuleLandingPath = (moduleKey, hasPermissionCode) => {
  const moduleConfig = MODULE_SWITCHER_ITEMS.find(item => item.key === moduleKey)
  if (!moduleConfig) return null
  return getModuleMenuItems(moduleKey, hasPermissionCode)[0]?.path || '/manual-testcases/list'
}

export const getModuleLandingPathByCardKey = (cardKey, hasPermissionCode) => {
  const moduleConfig = MODULE_SWITCHER_ITEMS.find(item => item.cardKey === cardKey)
  return moduleConfig ? getModuleLandingPath(moduleConfig.key, hasPermissionCode) : null
}

export const getVisibleModuleSwitcherItems = hasPermissionCode => (
  MODULE_SWITCHER_ITEMS
    .filter(item => isHomeCardVisible(item.cardKey, hasPermissionCode))
    .map(item => ({
      ...item,
      path: getModuleLandingPath(item.key, hasPermissionCode),
    }))
)

export const getAiGenerationMenuPathByTab = () => '/manual-testcases/list'
