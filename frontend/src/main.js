import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '@fortawesome/fontawesome-free/css/all.min.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import axios from 'axios'
import { initDefectNotificationService } from '@/services/defectNotifications'
import { useUserStore } from '@/stores/user'

import App from './App.vue'
import router from './router'
import './assets/css/global.scss'
import './assets/css/manual-workspace-density.scss'
import 'kityminder-core/dist/kityminder.core.css'

// Axios aÃ¥ÂÂºÃ§Â½Â®
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true; // Ã¥ÂÂÃ¨Â®Â¸Ã¨Â·Â¨Ã¨Â¯Â·Ã¥Â¸Â¦ Cookie

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

const userStore = useUserStore(pinia)

async function init() {
  try {
    await userStore.initAuth()
  } catch (error) {
    // 获取用户信息失败，说明未登录，无需处理
  }

  // 注册所有图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.use(router)
  app.use(ElementPlus, {
    locale: zhCn,
  })
  initDefectNotificationService(userStore)

  app.mount('#app')
}

init()

