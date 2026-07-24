<template>
  <div class="login-container">
    <div class="showcase-section">
      <div class="showcase-content">
        <div class="brand-header">
          <div class="logo-wrapper">
            <div class="logo-icon">
              <span>B</span>
            </div>
            <div>
              <h1 class="brand-title">BearAI</h1>
              <p class="brand-subtitle">AI软件开发平台</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-section">
      <div class="login-form-wrapper">
        <div class="form-header">
          <h2>每个人都是FDE</h2>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          @submit.prevent="handleLogin"
          class="login-form"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
              class="login-button"
            >
              <span v-if="!loading">登录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form-item>

          <div class="form-footer">
            <router-link to="/register" class="register-link">
              还没有账号？<span>立即注册</span>
            </router-link>
          </div>
        </el-form>

        <!-- 底部信息 -->
        <div class="bottom-info">
          <p>© 2026 BearAI. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        console.log('开始登录...')
        const result = await userStore.login(form)
        console.log('登录结果:', result)
        console.log('用户store状态:', {
          token: userStore.token,
          user: userStore.user,
          isAuthenticated: userStore.isAuthenticated
        })

        ElMessage.success('登录成功')
        console.log('准备跳转到 /ai-generation/products')

        // 使用replace而不是push，避免返回登录页
        await router.replace('/manual-testcases/list')
        console.log('跳转完成')

      } catch (error) {
        console.error('登录失败:', error)
        ElMessage.error(error.response?.data?.error || '登录失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  height: 100vh;
  display: flex;
  background: #f4f7fb;
  overflow: hidden;
}

.showcase-section {
  flex: 1;
  background:
    linear-gradient(145deg, rgba(17, 24, 39, 0.96), rgba(22, 46, 68, 0.94)),
    url("data:image/svg+xml,%3Csvg width='160' height='160' viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%2384a2c5' stroke-opacity='.18'%3E%3Cpath d='M0 40h160M0 80h160M0 120h160M40 0v160M80 0v160M120 0v160'/%3E%3C/g%3E%3C/svg%3E");
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 56px;

  .showcase-content {
    position: relative;
    width: 100%;
    max-width: 680px;
    color: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .brand-header {
    animation: fadeInDown 0.8s ease-out;

    .logo-wrapper {
      display: flex;
      align-items: center;
      gap: 16px;

      .logo-icon {
        width: 58px;
        height: 58px;
        flex: 0 0 58px;
        background: #f8fafc;
        color: #102033;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.22);

        span {
          font-size: 30px;
          font-weight: 800;
          line-height: 1;
        }
      }

      .brand-title {
        font-size: 42px;
        font-weight: 800;
        margin: 0 0 4px;
        color: #ffffff;
        letter-spacing: 0;
      }
    }

    .brand-subtitle {
      font-size: 18px;
      color: #dbe6f2;
      margin: 0;
      font-weight: 500;
      letter-spacing: 0;
    }
  }
}

/* 右侧登录表单 */
.login-section {
  width: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  padding: 60px;
  position: relative;

  .login-form-wrapper {
    width: 100%;
    max-width: 400px;
  }

  .form-header {
    text-align: center;
    margin-bottom: 40px;
    animation: fadeIn 0.8s ease-out;

    h2 {
      font-size: 28px;
      font-weight: 700;
      color: #303133;
      margin: 0;
    }
  }

  .login-form {
    :deep(.el-input__wrapper) {
      padding: 8px 16px;
      box-shadow: 0 0 0 1px #dcdfe6 inset;
      transition: all 0.3s ease;

      &:hover {
        box-shadow: 0 0 0 1px #c0c4cc inset;
      }

      &.is-focus {
        box-shadow: 0 0 0 1px #667eea inset;
      }
    }

    :deep(.el-form-item) {
      margin-bottom: 24px;
    }

    .login-button {
      width: 100%;
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
      }

      &:active {
        transform: translateY(0);
      }
    }
  }

  .form-footer {
    text-align: center;
    margin-top: 24px;

    .register-link {
      color: #909399;
      text-decoration: none;
      font-size: 14px;
      transition: all 0.3s ease;

      span {
        color: #667eea;
        font-weight: 600;
      }

      &:hover {
        color: #667eea;
      }
    }
  }

  .bottom-info {
    margin-top: 60px;
    text-align: center;

    p {
      font-size: 12px;
      color: #c0c4cc;
      margin: 0;
    }
  }
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }

  .showcase-section {
    min-height: 40vh;
    padding: 28px;

    .brand-header {
      .logo-wrapper {
        align-items: flex-start;

        .brand-title {
          font-size: 32px;
        }
      }
    }
  }

  .login-section {
    width: 100%;
    padding: 30px;
  }
}
</style>
