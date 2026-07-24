<template>
  <div class="register-container">
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

    <div class="register-section">
      <div class="register-form-wrapper">
        <div class="form-header">
          <h2>邮箱登录 / 注册</h2>
          <p>输入邮箱并完成验证码校验，未注册邮箱将自动创建账号</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          @submit.prevent="handleSubmit"
          class="register-form"
        >
          <el-form-item prop="email">
            <el-input
              v-model="form.email"
              type="email"
              placeholder="请输入邮箱"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item prop="code">
            <div class="code-row">
              <el-input
                v-model="form.code"
                placeholder="请输入验证码"
                size="large"
                maxlength="6"
                :prefix-icon="Key"
                @keyup.enter="handleSubmit"
              />
              <el-button
                size="large"
                :disabled="sendingCode || countdown > 0"
                :loading="sendingCode"
                @click="handleSendCode"
              >
                {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              @click="handleSubmit"
              class="submit-button"
            >
              <span v-if="!loading">登录 / 注册</span>
              <span v-else>处理中...</span>
            </el-button>
          </el-form-item>

          <div class="form-footer">
            <router-link to="/login" class="login-link">
              已有账号密码？<span>返回登录</span>
            </router-link>
          </div>
        </el-form>

        <div class="bottom-info">
          <p>© 2026 BearAI. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Key } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)
let countdownTimer = null

const form = reactive({
  email: '',
  code: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位数字', trigger: 'blur' }
  ]
}

const startCountdown = (seconds = 60) => {
  countdown.value = seconds
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
  countdownTimer = setInterval(() => {
    if (countdown.value <= 1) {
      countdown.value = 0
      clearInterval(countdownTimer)
      countdownTimer = null
      return
    }
    countdown.value -= 1
  }, 1000)
}

const handleSendCode = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validateField('email')
  } catch (error) {
    return
  }

  sendingCode.value = true
  try {
    const result = await userStore.sendEmailVerificationCode(form.email)
    if (result.email_sent) {
      ElMessage.success(result.message || '验证码已发送，请查收邮箱')
    } else if (result.debug_code) {
      ElMessage.success('本地环境未配置邮件服务，请使用下方验证码')
      ElMessage({
        message: `验证码：${result.debug_code}`,
        type: 'info',
        duration: 15000,
        showClose: true
      })
    } else {
      ElMessage.success(result.message || '验证码已发送')
    }
    startCountdown(result.cooldown_seconds || 60)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '验证码发送失败')
  } finally {
    sendingCode.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const result = await userStore.loginWithEmailCode({
        email: form.email,
        code: form.code
      })
      ElMessage.success(result.message || (result.created ? '注册并登录成功' : '登录成功'))
      await router.replace('/manual-testcases/list')
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

onBeforeUnmount(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
})
</script>

<style lang="scss" scoped>
.register-container {
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56px;

  .showcase-content {
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
      }
    }

    .brand-subtitle {
      font-size: 18px;
      color: #dbe6f2;
      margin: 0;
      font-weight: 500;
    }
  }
}

.register-section {
  width: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  padding: 60px;

  .register-form-wrapper {
    width: 100%;
    max-width: 400px;
  }

  .form-header {
    text-align: center;
    margin-bottom: 40px;

    h2 {
      font-size: 28px;
      font-weight: 700;
      color: #303133;
      margin: 0 0 12px;
    }

    p {
      font-size: 14px;
      color: #909399;
      margin: 0;
      line-height: 1.6;
    }
  }

  .register-form {
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

    .code-row {
      display: flex;
      gap: 12px;
      width: 100%;

      .el-input {
        flex: 1;
      }

      .el-button {
        min-width: 118px;
        flex-shrink: 0;
      }
    }

    .submit-button {
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

    .login-link {
      color: #909399;
      text-decoration: none;
      font-size: 14px;

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

@media (max-width: 768px) {
  .register-container {
    flex-direction: column;
  }

  .showcase-section {
    min-height: 40vh;
    padding: 28px;

    .brand-header .logo-wrapper .brand-title {
      font-size: 32px;
    }
  }

  .register-section {
    width: 100%;
    padding: 30px;
  }
}
</style>
