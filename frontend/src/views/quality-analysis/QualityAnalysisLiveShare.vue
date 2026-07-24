<template>
  <div class="quality-live-share-page">
    <div class="share-header">
      <div>
        <p class="eyebrow">Shared Live Analysis</p>
        <h1>实施质量分析分享</h1>
        <p class="description">公开查看当前版本的实施质量分析，无需登录即可访问。</p>
      </div>
    </div>

    <QualityAnalysisVersionLivePanel
      :share-token="shareToken"
      active
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import QualityAnalysisVersionLivePanel from './QualityAnalysisVersionLivePanel.vue'

const route = useRoute()
const shareToken = computed(() => String(route.params.token || '').trim())
</script>

<style scoped lang="scss">
.quality-live-share-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(73, 134, 176, 0.18), transparent 25%),
    linear-gradient(180deg, #f4f8fb 0%, #edf2f6 100%);
}

.share-header {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(17, 45, 67, 0.08);
  box-shadow: 0 16px 36px rgba(15, 45, 68, 0.08);
  padding: 30px;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #587189;
}

.share-header h1 {
  margin: 0;
  font-size: 34px;
  color: #17324d;
}

.description {
  margin: 10px 0 0;
  color: #60788d;
}

@media (max-width: 900px) {
  .quality-live-share-page {
    padding: 16px;
  }

  .share-header {
    padding: 22px;
  }

  .share-header h1 {
    font-size: 28px;
  }
}
</style>
