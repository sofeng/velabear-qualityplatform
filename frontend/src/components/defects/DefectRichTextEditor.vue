<template>
  <div class="defect-rich-text-editor">
    <QuillEditor
      ref="editorRef"
      :content="modelValue"
      content-type="html"
      theme="snow"
      toolbar="full"
      :placeholder="placeholder"
      :options="editorOptions"
      @update:content="handleContentChange"
      @ready="handleReady"
    />

    <input
      ref="imageInputRef"
      class="defect-rich-text-editor__image-input"
      type="file"
      accept="image/*"
      multiple
      @change="handleImageInputChange"
    >
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '请输入内容',
  },
  minHeight: {
    type: Number,
    default: 320,
  },
})

const emit = defineEmits(['update:modelValue', 'preview-images', 'ready'])

const editorRef = ref()
const imageInputRef = ref()
const quillRef = ref(null)

const editorOptions = {
  modules: {
    clipboard: {
      matchVisual: false,
    },
  },
}

const readFileAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })

const insertImageAtCursor = async (file) => {
  if (!quillRef.value || !file) {
    return
  }

  const imageDataUrl = await readFileAsDataUrl(file)
  const quill = quillRef.value
  const selection = quill.getSelection(true)
  const insertIndex = selection?.index ?? quill.getLength()

  quill.insertEmbed(insertIndex, 'image', imageDataUrl, 'user')
  quill.setSelection(insertIndex + 1, 0, 'user')
}

const collectEditorImages = () => {
  if (!quillRef.value?.root) {
    return []
  }

  return Array.from(quillRef.value.root.querySelectorAll('img'))
    .map((image) => image.getAttribute('src') || '')
    .filter(Boolean)
}

const emitPreviewImages = (source) => {
  const images = collectEditorImages()
  const currentIndex = Math.max(images.findIndex((item) => item === source), 0)

  emit('preview-images', {
    images,
    currentIndex,
  })
}

const handleEditorPaste = async (event) => {
  const clipboardItems = Array.from(event.clipboardData?.items || [])
  const imageItems = clipboardItems.filter((item) => item.type?.startsWith('image/'))

  if (!imageItems.length) {
    return
  }

  event.preventDefault()

  for (const item of imageItems) {
    const file = item.getAsFile()
    if (file) {
      await insertImageAtCursor(file)
    }
  }
}

const handleEditorClick = (event) => {
  const target = event.target
  if (target?.tagName === 'IMG') {
    emitPreviewImages(target.getAttribute('src') || '')
  }
}

const registerToolbarHandlers = () => {
  const toolbarModule = quillRef.value?.getModule('toolbar')
  if (!toolbarModule) {
    return
  }

  toolbarModule.addHandler('image', () => {
    imageInputRef.value?.click()
  })
}

const handleReady = (quill) => {
  quillRef.value = quill
  quill.root.style.minHeight = `${props.minHeight}px`
  quill.root.addEventListener('paste', handleEditorPaste)
  quill.root.addEventListener('click', handleEditorClick)
  registerToolbarHandlers()
  emit('ready', quill)
}

const handleContentChange = (content) => {
  emit('update:modelValue', content || '')
}

const handleImageInputChange = async (event) => {
  const files = Array.from(event.target?.files || [])
  for (const file of files) {
    await insertImageAtCursor(file)
  }

  if (imageInputRef.value) {
    imageInputRef.value.value = ''
  }
}

onBeforeUnmount(() => {
  if (!quillRef.value?.root) {
    return
  }

  quillRef.value.root.removeEventListener('paste', handleEditorPaste)
  quillRef.value.root.removeEventListener('click', handleEditorClick)
})
</script>

<style scoped lang="scss">
.defect-rich-text-editor {
  width: 100%;
}

.defect-rich-text-editor__image-input {
  display: none;
}

.defect-rich-text-editor :deep(.ql-container) {
  font-size: 14px;
}

.defect-rich-text-editor :deep(.ql-editor) {
  min-height: 320px;
  line-height: 1.75;
}

.defect-rich-text-editor :deep(.ql-editor img) {
  max-width: 100%;
  height: auto;
  cursor: pointer;
  border-radius: 6px;
}
</style>
