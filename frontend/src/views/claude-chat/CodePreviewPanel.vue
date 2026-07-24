<template>
  <div class="code-preview-panel">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="panel-tabs">
        <el-tabs v-model="activeTab" class="preview-tabs">
          <el-tab-pane label="预览" name="preview">
            <template #label>
              <span class="tab-label">
                <el-icon><View /></el-icon>
                预览
              </span>
            </template>
          </el-tab-pane>
          <el-tab-pane label="代码" name="code">
            <template #label>
              <span class="tab-label">
                <el-icon><Document /></el-icon>
                代码
              </span>
            </template>
          </el-tab-pane>
        </el-tabs>
      </div>
      <div class="panel-actions">
        <el-tooltip content="刷新预览" placement="bottom">
          <el-button size="small" :icon="Refresh" circle @click="refreshPreview" />
        </el-tooltip>
        <el-tooltip content="复制代码" placement="bottom">
          <el-button size="small" :icon="CopyDocument" circle @click="copyCode" />
        </el-tooltip>
        <el-tooltip content="在新窗口打开" placement="bottom">
          <el-button size="small" :icon="TopRight" circle @click="openInNewWindow" />
        </el-tooltip>
        <el-tooltip content="关闭面板" placement="bottom">
          <el-button size="small" :icon="Close" circle @click="$emit('close')" />
        </el-tooltip>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="panel-content">
      <!-- 预览 Tab -->
      <div v-show="activeTab === 'preview'" class="preview-area">
        <div class="preview-toolbar">
          <el-radio-group v-model="viewportSize" size="small">
            <el-radio-button label="desktop">
              <el-icon><Monitor /></el-icon>
            </el-radio-button>
            <el-radio-button label="tablet">
              <el-icon><Iphone /></el-icon>
            </el-radio-button>
            <el-radio-button label="mobile">
              <el-icon><Cellphone /></el-icon>
            </el-radio-button>
          </el-radio-group>
          <span class="viewport-label">{{ viewportLabel }}</span>
        </div>
        <div class="preview-container" :class="viewportSize">
          <iframe
            ref="previewFrame"
            class="preview-iframe"
            :srcdoc="fullHtmlDocument"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            @load="onIframeLoad"
          />
        </div>
      </div>

      <!-- 代码 Tab -->
      <div v-show="activeTab === 'code'" class="code-area">
        <div class="code-toolbar">
          <span class="code-label">HTML</span>
          <el-button size="small" text @click="formatCode">
            <el-icon><MagicStick /></el-icon>
            格式化
          </el-button>
        </div>
        <div class="code-editor-wrapper">
          <textarea
            ref="codeEditor"
            v-model="editableCode"
            class="code-editor"
            spellcheck="false"
            @input="onCodeChange"
          />
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="panel-footer">
      <span class="status-text">
        <el-icon :class="{ 'is-loading': isLoading }"><Loading /></el-icon>
        {{ statusText }}
      </span>
      <span class="code-size">{{ codeSize }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  View,
  Document,
  Refresh,
  CopyDocument,
  TopRight,
  Close,
  Monitor,
  Iphone,
  Cellphone,
  MagicStick,
  Loading
} from '@element-plus/icons-vue'

const props = defineProps({
  code: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'update:code'])

// 状态
const activeTab = ref('preview')
const viewportSize = ref('desktop')
const editableCode = ref('')
const isLoading = ref(false)
const previewFrame = ref(null)
const codeEditor = ref(null)

// 视口标签
const viewportLabel = computed(() => {
  const labels = {
    desktop: '桌面 (100%)',
    tablet: '平板 (768px)',
    mobile: '手机 (375px)'
  }
  return labels[viewportSize.value]
})

// 代码大小
const codeSize = computed(() => {
  const size = new Blob([editableCode.value]).size
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
})

// 状态文本
const statusText = computed(() => {
  if (isLoading.value) return '加载中...'
  return '预览就绪'
})

// 生成完整的 HTML 文档
const fullHtmlDocument = computed(() => {
  const code = editableCode.value

  // 检查是否已经是完整的 HTML 文档
  if (code.trim().toLowerCase().startsWith('<!doctype') ||
      code.trim().toLowerCase().startsWith('<html')) {
    return code
  }

  // 包装为完整的 HTML 文档
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <!-- TailwindCSS -->
  <script src="https://cdn.tailwindcss.com"><\/script>
  <!-- 基础样式 -->
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
    }
  </style>
</head>
<body>
${code}
</body>
</html>`
})

// 监听 props.code 变化
watch(() => props.code, (newCode) => {
  if (newCode !== editableCode.value) {
    editableCode.value = newCode
  }
}, { immediate: true })

// 代码变化时通知父组件
const onCodeChange = () => {
  emit('update:code', editableCode.value)
}

// iframe 加载完成
const onIframeLoad = () => {
  isLoading.value = false
}

// 刷新预览
const refreshPreview = () => {
  isLoading.value = true
  if (previewFrame.value) {
    // 强制刷新 iframe
    const doc = fullHtmlDocument.value
    previewFrame.value.srcdoc = ''
    setTimeout(() => {
      previewFrame.value.srcdoc = doc
    }, 50)
  }
}

// 复制代码
const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(editableCode.value)
    ElMessage.success('代码已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

// 在新窗口打开
const openInNewWindow = () => {
  const newWindow = window.open('', '_blank')
  if (newWindow) {
    newWindow.document.write(fullHtmlDocument.value)
    newWindow.document.close()
  }
}

// 格式化代码（简单实现）
const formatCode = () => {
  // 简单的格式化：调整缩进
  let formatted = editableCode.value
    .replace(/></g, '>\n<')
    .replace(/\n\s*\n/g, '\n')

  // 简单缩进处理
  const lines = formatted.split('\n')
  let indent = 0
  const result = []

  for (let line of lines) {
    line = line.trim()
    if (!line) continue

    // 减少缩进的标签
    if (line.startsWith('</') || line.startsWith('/>')) {
      indent = Math.max(0, indent - 1)
    }

    result.push('  '.repeat(indent) + line)

    // 增加缩进的标签
    if (line.match(/^<[^/!][^>]*[^/]>$/) && !line.match(/^<(br|hr|img|input|meta|link)/i)) {
      indent++
    }
  }

  editableCode.value = result.join('\n')
  ElMessage.success('代码已格式化')
}

onMounted(() => {
  isLoading.value = true
})
</script>

<style scoped lang="scss">
.code-preview-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 50px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafbfc;

  .panel-tabs {
    .preview-tabs {
      :deep(.el-tabs__header) {
        margin: 0;
      }
      :deep(.el-tabs__nav-wrap::after) {
        display: none;
      }
      :deep(.el-tabs__item) {
        height: 50px;
        line-height: 50px;
        padding: 0 16px;
      }
    }

    .tab-label {
      display: flex;
      align-items: center;
      gap: 6px;
    }
  }

  .panel-actions {
    display: flex;
    gap: 8px;
  }
}

.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 预览区域 */
.preview-area {
  height: 100%;
  display: flex;
  flex-direction: column;

  .preview-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;

    .viewport-label {
      font-size: 12px;
      color: #909399;
    }
  }

  .preview-container {
    flex: 1;
    padding: 16px;
    background: #e4e7ed;
    overflow: auto;
    display: flex;
    justify-content: center;

    &.desktop {
      .preview-iframe {
        width: 100%;
        max-width: none;
      }
    }

    &.tablet {
      .preview-iframe {
        width: 768px;
        max-width: 768px;
      }
    }

    &.mobile {
      .preview-iframe {
        width: 375px;
        max-width: 375px;
      }
    }

    .preview-iframe {
      height: 100%;
      border: none;
      background: #fff;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      border-radius: 8px;
    }
  }
}

/* 代码区域 */
.code-area {
  height: 100%;
  display: flex;
  flex-direction: column;

  .code-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background: #1e1e1e;
    border-bottom: 1px solid #333;

    .code-label {
      font-size: 12px;
      color: #808080;
      font-family: monospace;
    }

    .el-button {
      color: #808080;
      &:hover {
        color: #fff;
      }
    }
  }

  .code-editor-wrapper {
    flex: 1;
    overflow: hidden;

    .code-editor {
      width: 100%;
      height: 100%;
      padding: 16px;
      background: #1e1e1e;
      color: #d4d4d4;
      border: none;
      outline: none;
      resize: none;
      font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
      font-size: 14px;
      line-height: 1.6;
      tab-size: 2;

      &::-webkit-scrollbar {
        width: 8px;
        height: 8px;
      }
      &::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 4px;
      }
      &::-webkit-scrollbar-track {
        background: #1e1e1e;
      }
    }
  }
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fafbfc;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;

  .status-text {
    display: flex;
    align-items: center;
    gap: 6px;

    .is-loading {
      animation: rotating 1s linear infinite;
    }
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
