<template>
  <section class="quality-knowledge-assistant">
    <aside v-if="$slots['knowledge-rail-before']" class="quality-knowledge-assistant__rail">
      <slot name="knowledge-rail-before" />
    </aside>
    <div class="quality-knowledge-assistant__body">
      <el-empty description="思源质量源码版未包含 AI 会话底座，知识库助手暂不可用。">
        <template #description>
          <p class="quality-knowledge-assistant__hint">
            思源质量源码版未包含 AI 会话底座，知识库助手暂不可用。
          </p>
          <p class="quality-knowledge-assistant__hint">
            你仍可使用资产图谱、Wiki、JIRA 数据与质量报告等能力。
          </p>
        </template>
      </el-empty>
    </div>
  </section>
</template>

<script setup>
defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  linkedProjectId: {
    type: [Number, String],
    default: '',
  },
  linkedProjectName: {
    type: String,
    default: '',
  },
  linkedVersionId: {
    type: [Number, String],
    default: '',
  },
  linkedVersionName: {
    type: String,
    default: '',
  },
  linkedCategoryId: {
    type: [Number, String],
    default: '',
  },
})
</script>

<style scoped>
.quality-knowledge-assistant {
  display: flex;
  gap: 12px;
  height: 100%;
  min-height: 420px;
}

.quality-knowledge-assistant__rail {
  flex: 0 0 auto;
}

.quality-knowledge-assistant__body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
}

.quality-knowledge-assistant__hint {
  margin: 0 0 8px;
  line-height: 1.7;
  color: #607489;
}
</style>
