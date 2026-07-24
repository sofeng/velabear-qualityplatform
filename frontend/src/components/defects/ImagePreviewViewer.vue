<template>
  <teleport to="body">
    <div v-if="visible" class="image-preview-viewer" @click.self="handleClose">
      <button class="image-preview-viewer__close" type="button" @click="handleClose">
        ×
      </button>

      <button
        v-if="imageCount > 1"
        class="image-preview-viewer__nav image-preview-viewer__nav--left"
        type="button"
        @click.stop="showPrevious"
      >
        ‹
      </button>

      <div class="image-preview-viewer__stage">
        <img
          v-if="currentImage"
          :src="currentImage"
          class="image-preview-viewer__image"
          alt="preview"
          @click.stop
        >
        <div v-if="imageCount > 1" class="image-preview-viewer__counter">
          {{ currentIndex + 1 }} / {{ imageCount }}
        </div>
      </div>

      <button
        v-if="imageCount > 1"
        class="image-preview-viewer__nav image-preview-viewer__nav--right"
        type="button"
        @click.stop="showNext"
      >
        ›
      </button>
    </div>
  </teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  images: {
    type: Array,
    default: () => [],
  },
  initialIndex: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['update:visible', 'update:initialIndex', 'close'])

const imageCount = computed(() => props.images.length)
const normalizedIndex = computed(() => {
  if (!imageCount.value) {
    return 0
  }

  const rawIndex = Number(props.initialIndex) || 0
  return ((rawIndex % imageCount.value) + imageCount.value) % imageCount.value
})
const currentIndex = computed(() => normalizedIndex.value)
const currentImage = computed(() => props.images[currentIndex.value] || '')

const updateIndex = (nextIndex) => {
  emit('update:initialIndex', nextIndex)
}

const showPrevious = () => {
  if (!imageCount.value) {
    return
  }

  updateIndex((currentIndex.value - 1 + imageCount.value) % imageCount.value)
}

const showNext = () => {
  if (!imageCount.value) {
    return
  }

  updateIndex((currentIndex.value + 1) % imageCount.value)
}

const handleClose = () => {
  emit('update:visible', false)
  emit('close')
}

const handleKeydown = (event) => {
  if (!props.visible) {
    return
  }

  if (event.key === 'Escape') {
    handleClose()
    return
  }

  if (imageCount.value <= 1) {
    return
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    showPrevious()
  }

  if (event.key === 'ArrowRight') {
    event.preventDefault()
    showNext()
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      window.addEventListener('keydown', handleKeydown)
      document.body.style.overflow = 'hidden'
      return
    }

    window.removeEventListener('keydown', handleKeydown)
    document.body.style.overflow = ''
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped lang="scss">
.image-preview-viewer {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.92);
}

.image-preview-viewer__stage {
  position: relative;
  width: min(92vw, 1400px);
  height: min(88vh, 900px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview-viewer__image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
}

.image-preview-viewer__nav,
.image-preview-viewer__close {
  position: absolute;
  z-index: 1;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.image-preview-viewer__nav:hover,
.image-preview-viewer__close:hover {
  background: rgba(255, 255, 255, 0.24);
}

.image-preview-viewer__close {
  top: 24px;
  right: 24px;
  width: 44px;
  height: 44px;
  font-size: 28px;
  line-height: 1;
}

.image-preview-viewer__nav {
  top: 50%;
  width: 56px;
  height: 56px;
  margin-top: -28px;
  font-size: 40px;
  line-height: 1;
}

.image-preview-viewer__nav--left {
  left: 24px;
}

.image-preview-viewer__nav--right {
  right: 24px;
}

.image-preview-viewer__counter {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 13px;
}
</style>
