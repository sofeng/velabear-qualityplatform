import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTabsStore = defineStore('tabs', () => {
  // 从 localStorage 恢复标签页
  const savedTabs = localStorage.getItem('tabs')
  const savedActiveTab = localStorage.getItem('activeTab')

  const defaultTabs = [
    { path: '/manual-testcases/list', title: '思源质量', name: 'ManualTestCaseList', closable: false }
  ]
  const normalizeTab = tab => tab?.path === '/home'
    ? { ...tab, path: '/manual-testcases/list', title: '思源质量', name: 'ManualTestCaseList', closable: false }
    : tab
  const tabs = ref(savedTabs
    ? JSON.parse(savedTabs).map(normalizeTab)
    : defaultTabs.map(item => ({ ...item }))
  )
  const activeTab = ref(savedActiveTab === '/home' ? '/manual-testcases/list' : (savedActiveTab || '/manual-testcases/list'))

  // 添加标签页
  const addTab = (route) => {
    // 跳过登录页等不需要标签页的页面
    if (!route.path || route.path === '/login' || route.path === '/register') {
      return
    }

    // 检查标签页是否已存在
    const existingTab = tabs.value.find(tab => tab.path === route.path)
    if (!existingTab) {
      // 获取标题，优先使用 meta.title，其次使用 name
      let title = route.meta?.title || route.name || '未命名页面'

      // 特殊处理：历史首页链接会被重定向到思源质量首页
      if (route.path === '/home') {
        title = '思源质量'
      }

      tabs.value.push({
        path: route.path,
        title: title,
        name: route.name,
        closable: route.path !== '/home' && route.path !== '/manual-testcases/list'
      })
      saveTabs()
    }
    activeTab.value = route.path
    saveActiveTab()
  }

  // 关闭标签页
  const closeTab = (targetPath) => {
    const index = tabs.value.findIndex(tab => tab.path === targetPath)
    if (index === -1 || !tabs.value[index].closable) {
      return null
    }

    const removedTab = tabs.value.splice(index, 1)[0]
    saveTabs()

    // 如果关闭的是当前激活的标签页，需要切换到其他标签页
    if (activeTab.value === targetPath) {
      if (tabs.value.length > 0) {
        // 优先选择右侧标签页，没有则选择左侧
        const nextTab = tabs.value[index] || tabs.value[index - 1]
        activeTab.value = nextTab.path
        saveActiveTab()
        return nextTab.path
      }
    }
    return null
  }

  // 关闭其他标签页
  const closeOtherTabs = (targetPath) => {
    tabs.value = tabs.value.filter(tab => !tab.closable || tab.path === targetPath)
    saveTabs()
    if (activeTab.value !== targetPath) {
      activeTab.value = targetPath
      saveActiveTab()
    }
  }

  // 关闭所有可关闭的标签页
  const closeAllTabs = () => {
    tabs.value = tabs.value.filter(tab => !tab.closable)
    saveTabs()
    if (tabs.value.length > 0) {
      activeTab.value = tabs.value[0].path
      saveActiveTab()
      return tabs.value[0].path
    }
    return null
  }

  // 关闭左侧标签页
  const closeLeftTabs = (targetPath) => {
    const index = tabs.value.findIndex(tab => tab.path === targetPath)
    if (index === -1) return

    const leftTabs = tabs.value.slice(0, index)
    const closableTabs = leftTabs.filter(tab => tab.closable)
    closableTabs.forEach(tab => {
      const idx = tabs.value.findIndex(t => t.path === tab.path)
      if (idx !== -1) {
        tabs.value.splice(idx, 1)
      }
    })
    saveTabs()
  }

  // 关闭右侧标签页
  const closeRightTabs = (targetPath) => {
    const index = tabs.value.findIndex(tab => tab.path === targetPath)
    if (index === -1) return

    const rightTabs = tabs.value.slice(index + 1)
    const closableTabs = rightTabs.filter(tab => tab.closable)
    closableTabs.forEach(tab => {
      const idx = tabs.value.findIndex(t => t.path === tab.path)
      if (idx !== -1) {
        tabs.value.splice(idx, 1)
      }
    })
    saveTabs()
  }

  // 持久化标签页列表
  const saveTabs = () => {
    localStorage.setItem('tabs', JSON.stringify(tabs.value))
  }

  // 持久化当前激活标签页
  const saveActiveTab = () => {
    localStorage.setItem('activeTab', activeTab.value)
  }

  // 清除所有标签页（用于登出时）
  const clearTabs = () => {
    tabs.value = defaultTabs.map(item => ({ ...item }))
    activeTab.value = '/manual-testcases/list'
    localStorage.removeItem('tabs')
    localStorage.removeItem('activeTab')
  }

  return {
    tabs,
    activeTab,
    addTab,
    closeTab,
    closeOtherTabs,
    closeAllTabs,
    closeLeftTabs,
    closeRightTabs,
    clearTabs
  }
})
