<template>
  <div class="defect-rich-text-content">
    <div
      v-if="html"
      ref="contentRef"
      class="defect-rich-text-content__body"
      v-html="html"
      @click="handleClick"
    />
    <span v-else class="defect-rich-text-content__empty">{{ emptyText }}</span>

    <ImagePreviewViewer
      v-model:visible="previewVisible"
      :images="previewImages"
      :initial-index="previewIndex"
      @update:initial-index="handlePreviewIndexChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ImagePreviewViewer from './ImagePreviewViewer.vue'

defineProps({
  html: {
    type: String,
    default: '',
  },
  emptyText: {
    type: String,
    default: '-',
  },
})

const contentRef = ref()
const previewVisible = ref(false)
const previewImages = ref([])
const previewIndex = ref(0)

const handlePreviewIndexChange = (nextIndex) => {
  previewIndex.value = nextIndex
}

const handleClick = (event) => {
  const target = event.target
  if (target?.tagName !== 'IMG') {
    return
  }

  const images = Array.from(contentRef.value?.querySelectorAll('img') || [])
    .map((image) => image.getAttribute('src') || '')
    .filter(Boolean)

  previewImages.value = images
  previewIndex.value = Math.max(images.findIndex((item) => item === target.getAttribute('src')), 0)
  previewVisible.value = true
}
</script>

<style scoped lang="scss">
.defect-rich-text-content__body {
  line-height: 1.75;
  color: #303133;
  word-break: break-word;
}

.defect-rich-text-content__body :deep(p) {
  margin: 0 0 12px;
}

.defect-rich-text-content__body :deep(img) {
  max-width: 100%;
  height: auto;
  cursor: pointer;
  border-radius: 6px;
}

.defect-rich-text-content__body :deep(ul),
.defect-rich-text-content__body :deep(ol) {
  padding-left: 24px;
}

.defect-rich-text-content__empty {
  color: #909399;
}
</style>
