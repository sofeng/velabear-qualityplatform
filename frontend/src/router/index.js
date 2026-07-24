import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  hasRoutePermission,
  resolveAuthorizedManualTestcaseTab,
} from '@/utils/permissions'

import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import Layout from '@/layout/index.vue'

const DEFAULT_AUTHENTICATED_PATH = '/manual-testcases/list'

const routes = [
  { path: '/', redirect: DEFAULT_AUTHENTICATED_PATH },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true },
  },
  {
    path: '/home',
    redirect: DEFAULT_AUTHENTICATED_PATH,
  },
  {
    path: '/ai-generation',
    redirect: DEFAULT_AUTHENTICATED_PATH,
  },
  {
    path: '/ai-generation/:pathMatch(.*)*',
    redirect: DEFAULT_AUTHENTICATED_PATH,
  },
  {
    path: '/configuration/:pathMatch(.*)*',
    redirect: DEFAULT_AUTHENTICATED_PATH,
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'UserProfile',
        component: () => import('@/views/profile/UserProfile.vue'),
        meta: { title: '个人设置', hideLayoutTopbar: true, showFloatingAiControl: true },
      },
    ],
  },
  {
    path: '/manual-testcases',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'list' },
      {
        path: 'list',
        name: 'ManualTestCaseList',
        component: () => import('@/views/manual-testcases/ManualTestCaseList.vue'),
        meta: { title: '思源研发管理', showFloatingAiControl: true },
      },
      {
        path: 'reports',
        redirect: to => {
          const rawTab = Array.isArray(to.query.tab) ? to.query.tab[0] : to.query.tab
          const tab = ['quality-report-list', 'quality-report-live'].includes(rawTab)
            ? rawTab
            : (['quality-report-excel', 'excel-import'].includes(rawTab)
              ? 'quality-report-live'
              : (to.query.reportId ? 'quality-report-live' : 'quality-report-list'))
          return { path: '/manual-testcases/list', query: { ...to.query, tab } }
        },
      },
      {
        path: 'reports/:id',
        redirect: to => ({
          path: '/manual-testcases/list',
          query: { ...to.query, tab: 'quality-report-live', reportId: String(to.params.id) },
        }),
      },
      {
        path: 'defects',
        redirect: to => ({ path: '/manual-testcases/list', query: { ...to.query, tab: 'version-defects' } }),
      },
      {
        path: 'technical-solution-designs',
        redirect: to => ({ path: '/manual-testcases/list', query: { ...to.query, tab: 'technical-solution-designs' } }),
      },
      {
        path: 'technical-solution-designs/create',
        name: 'ManualTechnicalSolutionDesignCreate',
        component: () => import('@/views/manual-testcases/TechnicalSolutionDesignForm.vue'),
        meta: { title: '新建技术方案设计' },
      },
      {
        path: 'technical-solution-designs/:id/edit',
        name: 'ManualTechnicalSolutionDesignEdit',
        component: () => import('@/views/manual-testcases/TechnicalSolutionDesignForm.vue'),
        meta: { title: '编辑技术方案设计' },
      },
      {
        path: 'technical-solution-designs/:id',
        redirect: to => ({ path: `/manual-testcases/technical-solution-designs/${to.params.id}/edit`, query: to.query }),
      },
      {
        path: 'defects/create',
        name: 'ManualDefectCreate',
        component: () => import('@/views/manual-testcases/DefectForm.vue'),
        meta: { title: '新建缺陷' },
      },
      {
        path: 'defects/:id/edit',
        name: 'ManualDefectEdit',
        component: () => import('@/views/manual-testcases/DefectForm.vue'),
        meta: { title: '编辑缺陷' },
      },
      {
        path: 'defects/:id',
        redirect: to => ({ path: `/manual-testcases/defects/${to.params.id}/edit`, query: to.query }),
      },
      {
        path: 'requirements',
        redirect: to => ({ path: '/manual-testcases/list', query: { ...to.query, tab: 'requirement-records' } }),
      },
      {
        path: 'requirements/create',
        name: 'ManualRequirementCreate',
        component: () => import('@/views/manual-testcases/RequirementForm.vue'),
        meta: { title: '新建需求' },
      },
      {
        path: 'requirements/:id/edit',
        name: 'ManualRequirementEdit',
        component: () => import('@/views/manual-testcases/RequirementForm.vue'),
        meta: { title: '编辑需求' },
      },
      {
        path: 'recording-scripts',
        name: 'RecordingScriptManager',
        component: () => import('@/views/manual-testcases/RecordingScriptManager.vue'),
        meta: { title: '脚本生成' },
      },
      {
        path: 'automation-scripts',
        name: 'AutomationScriptManager',
        component: () => import('@/views/manual-testcases/AutomationScriptManager.vue'),
        meta: { title: '脚本管理' },
      },
      {
        path: 'snapshots',
        name: 'SnapshotManager',
        component: () => import('@/views/manual-testcases/SnapshotManager.vue'),
        meta: { title: '快照管理' },
      },
      {
        path: 'recordings',
        name: 'SnapshotRecordingManager',
        component: () => import('@/views/manual-testcases/SnapshotRecordingManager.vue'),
        meta: { title: '录制管理' },
      },
      {
        path: 'controlled-browser-lab',
        name: 'ControlledBrowserControlLab',
        component: () => import('@/views/manual-testcases/ControlledBrowserControlLab.vue'),
        meta: { title: '模拟页面组件' },
      },
      {
        path: 'editor',
        name: 'ManualTestCaseEditor',
        component: () => import('@/views/manual-testcases/ManualTestCaseEditor.vue'),
        meta: { title: '脑图编辑器', hidden: true, hideLayoutTopbar: true },
      },
      {
        path: 'view',
        name: 'ManualTestCaseView',
        component: () => import('@/views/manual-testcases/ManualTestCaseView.vue'),
        meta: { title: '用例查看', hidden: true, hideLayoutTopbar: true },
      },
      {
        path: 'visual-flow',
        name: 'VisualFlowEditor',
        component: () => import('@/views/manual-testcases/VisualFlowEditor.vue'),
        meta: { title: '流程图' },
      },
      {
        path: 'flows',
        name: 'VisualFlowManager',
        component: () => import('@/views/manual-testcases/VisualFlowManager.vue'),
        meta: { title: '流程管理' },
      },
      {
        path: 'visual-flow-executions',
        name: 'VisualFlowExecutionManager',
        component: () => import('@/views/manual-testcases/VisualFlowExecutionManager.vue'),
        meta: { title: '测试结果' },
      },
      {
        path: 'wiki',
        name: 'WikiManager',
        component: () => import('@/views/manual-testcases/WikiManager.vue'),
        meta: { title: 'Wiki' },
      },
      {
        path: 'workflow-workbench',
        name: 'ManualWorkflowWorkbench',
        component: () => import('@/views/manual-testcases/ManualWorkflowWorkbench.vue'),
        meta: { title: '流程工作台' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  userStore.syncAuthStateFromStorage?.()

  if (to.meta.publicShare) {
    next()
    return
  }

  if (userStore.accessToken && (!userStore.user || userStore.isTokenExpired)) {
    try {
      await userStore.initAuth()
    } catch (error) {
      console.error('认证初始化失败:', error)
    }
  }

  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    next('/login')
    return
  }

  if (to.meta.requiresGuest && userStore.isAuthenticated) {
    next(DEFAULT_AUTHENTICATED_PATH)
    return
  }

  if (to.path === '/manual-testcases/list') {
    const authorizedTab = resolveAuthorizedManualTestcaseTab(to.query.tab, userStore.hasPermissionCode)
    const currentTab = Array.isArray(to.query.tab) ? to.query.tab[0] : to.query.tab
    if (!authorizedTab) {
      next(DEFAULT_AUTHENTICATED_PATH)
      return
    }
    if (currentTab !== authorizedTab) {
      next({ path: to.path, query: { ...to.query, tab: authorizedTab }, replace: true })
      return
    }
  }

  if (!hasRoutePermission(to, userStore.hasPermissionCode)) {
    next(DEFAULT_AUTHENTICATED_PATH)
    return
  }

  next()
})

export default router
