<template>
  <div class="home-container">
    <div class="content-wrapper">
      <h1 class="main-title">思源质量平台</h1>
      <p class="subtitle">围绕版本、脑图、测试点与缺陷进行研发测试协同管理</p>

      <div class="cards-container">
        <div
          v-if="isCardVisible('manual')"
          class="nav-card"
          role="button"
          tabindex="0"
          @click="handleNavigate('manual')"
          @keydown.enter.prevent="handleNavigate('manual')"
        >
          <div class="card-icon manual-icon">
            <el-icon><Document /></el-icon>
          </div>
          <h3>思源质量</h3>
          <p>围绕版本、脑图、测试点和缺陷进行研发测试协同管理。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { isHomeCardVisible } from '@/utils/permissions'
import { getModuleLandingPathByCardKey } from '@/utils/appNavigation'

const router = useRouter()
const userStore = useUserStore()

const isCardVisible = cardKey => isHomeCardVisible(cardKey, userStore.hasPermissionCode)

const handleNavigate = cardKey => {
  const targetPath = getModuleLandingPathByCardKey(cardKey, userStore.hasPermissionCode)

  if (!targetPath) {
    ElMessage.info('该模块正在开发中')
    return
  }

  router.push(targetPath)
}
</script>

<style scoped lang="scss">
.home-container {
  min-height: 100%;
  background:
    radial-gradient(circle at top, rgba(121, 210, 255, 0.35), transparent 40%),
    linear-gradient(135deg, #f6fbff 0%, #edf5ff 45%, #f8fbff 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  box-sizing: border-box;
}

.content-wrapper {
  width: 100%;
  max-width: 1280px;
  text-align: center;
}

.main-title {
  margin: 0 0 14px;
  font-size: 3.4rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #154a77;
}

.subtitle {
  margin: 0 0 46px;
  font-size: 1.2rem;
  color: #5d748a;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 26px;
}

.nav-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 34px 24px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(125, 181, 223, 0.18);
  box-shadow: 0 16px 32px rgba(31, 92, 141, 0.08);
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, background-color 0.25s ease;
  outline: none;

  &:hover,
  &:focus-visible {
    transform: translateY(-8px);
    background: #fff;
    box-shadow: 0 22px 36px rgba(31, 92, 141, 0.14);
  }

  h3 {
    margin: 20px 0 12px;
    font-size: 1.42rem;
    color: #1f3d57;
  }

  p {
    margin: 0;
    line-height: 1.7;
    color: #6a8095;
  }
}

.card-icon {
  width: 78px;
  height: 78px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 38px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.4);

  &.ai-icon {
    background: #e8f4ff;
    color: #409eff;
  }

  &.manual-icon {
    background: #fff0f6;
    color: #eb2f96;
  }
}

@media screen and (max-width: 1440px) {
  .main-title {
    font-size: 3rem;
  }

  .cards-container {
    gap: 22px;
  }

  .nav-card {
    padding: 30px 20px;
  }
}

@media screen and (max-width: 1024px) {
  .home-container {
    padding: 20px;
  }

  .main-title {
    font-size: 2.6rem;
  }

  .subtitle {
    margin-bottom: 34px;
  }

  .cards-container {
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 18px;
  }
}

@media screen and (max-width: 768px) {
  .home-container {
    align-items: flex-start;
    padding: 18px 14px;
  }

  .main-title {
    font-size: 2.1rem;
  }

  .subtitle {
    font-size: 1rem;
  }

  .cards-container {
    grid-template-columns: 1fr;
  }

  .nav-card {
    padding: 28px 18px;
  }
}
</style>
