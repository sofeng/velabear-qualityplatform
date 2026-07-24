<template>
  <div class="canvas-editor">
    <!-- 头部工具栏 -->
    <div class="editor-header">
      <div class="header-left">
        <el-tabs v-model="activeTab" class="editor-tabs">
          <el-tab-pane label="设计" name="design">
            <template #label>
              <span class="tab-label">
                <el-icon><Edit /></el-icon>
                设计
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
      <div class="header-actions">
        <el-button-group>
          <el-tooltip content="桌面视图" placement="bottom">
            <el-button :type="viewportSize === 'desktop' ? 'primary' : 'default'" size="small" @click="viewportSize = 'desktop'">
              <el-icon><Monitor /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="平板视图" placement="bottom">
            <el-button :type="viewportSize === 'tablet' ? 'primary' : 'default'" size="small" @click="viewportSize = 'tablet'">
              <el-icon><Iphone /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="手机视图" placement="bottom">
            <el-button :type="viewportSize === 'mobile' ? 'primary' : 'default'" size="small" @click="viewportSize = 'mobile'">
              <el-icon><Cellphone /></el-icon>
            </el-button>
          </el-tooltip>
        </el-button-group>
        <el-divider direction="vertical" />
        <el-tooltip content="刷新预览" placement="bottom">
          <el-button size="small" :icon="Refresh" @click="refreshPreview" />
        </el-tooltip>
        <el-tooltip content="复制代码" placement="bottom">
          <el-button size="small" :icon="CopyDocument" @click="copyCode" />
        </el-tooltip>
        <el-tooltip content="新窗口打开" placement="bottom">
          <el-button size="small" :icon="TopRight" @click="openInNewWindow" />
        </el-tooltip>
        <el-tooltip content="关闭" placement="bottom">
          <el-button size="small" :icon="Close" @click="$emit('close')" />
        </el-tooltip>
      </div>
    </div>

    <!-- 选中元素信息栏 -->
    <div v-if="selectedElement && activeTab === 'design'" class="selection-bar">
      <div class="selection-info">
        <el-tag size="small" type="primary">{{ selectedElement.tagName }}</el-tag>
        <span v-if="selectedElement.id" class="element-id">#{{ selectedElement.id }}</span>
        <span v-if="selectedElement.className" class="element-class">.{{ selectedElement.className.split(' ')[0] }}</span>
      </div>
      <div class="selection-actions">
        <el-button size="small" type="primary" @click="openAIEditDialog">
          <el-icon><MagicStick /></el-icon>
          AI 编辑
        </el-button>
        <el-button size="small" @click="duplicateElement">
          <el-icon><CopyDocument /></el-icon>
          复制
        </el-button>
        <el-button size="small" type="danger" @click="deleteElement">
          <el-icon><Delete /></el-icon>
          删除
        </el-button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="editor-content">
      <!-- 设计视图 -->
      <div v-show="activeTab === 'design'" class="design-view">
        <div class="canvas-container" :class="viewportSize">
          <iframe
            ref="previewFrame"
            class="preview-iframe"
            :srcdoc="fullHtmlWithEditor"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            @load="onIframeLoad"
          />
        </div>
      </div>

      <!-- 代码视图 -->
      <div v-show="activeTab === 'code'" class="code-view">
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

    <!-- AI 编辑对话框 -->
    <el-dialog
      v-model="aiEditDialogVisible"
      title="AI 编辑元素"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="ai-edit-dialog">
        <div class="selected-element-preview">
          <div class="preview-label">选中的元素:</div>
          <div class="preview-code">{{ selectedElementHtml }}</div>
        </div>
        <el-input
          v-model="aiEditPrompt"
          type="textarea"
          :rows="4"
          placeholder="描述您想要的修改，例如：&#10;- 把文字改成红色&#10;- 添加一个边框&#10;- 把按钮变大一点"
        />
      </div>
      <template #footer>
        <el-button @click="aiEditDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="aiEditing" @click="applyAIEdit">
          <el-icon><MagicStick /></el-icon>
          应用修改
        </el-button>
      </template>
    </el-dialog>

    <!-- 底部状态栏 -->
    <div class="editor-footer">
      <span class="status-text">
        <template v-if="selectedElement">
          已选中: &lt;{{ selectedElement.tagName.toLowerCase() }}&gt;
        </template>
        <template v-else>
          点击选中元素 | 双击编辑文字 | 拖拽调整位置
        </template>
      </span>
      <span class="code-size">{{ codeSize }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Edit,
  Document,
  Refresh,
  CopyDocument,
  TopRight,
  Close,
  Monitor,
  Iphone,
  Cellphone,
  MagicStick,
  Delete
} from '@element-plus/icons-vue'

const props = defineProps({
  code: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'update:code', 'ai-edit-request'])

// 状态
const activeTab = ref('design')
const viewportSize = ref('desktop')
const editableCode = ref('')
const previewFrame = ref(null)
const codeEditor = ref(null)

// 选中元素状态
const selectedElement = ref(null)
const selectedElementPath = ref('')
const selectedElementHtml = ref('')

// AI 编辑状态
const aiEditDialogVisible = ref(false)
const aiEditPrompt = ref('')
const aiEditing = ref(false)

// 代码大小
const codeSize = computed(() => {
  const size = new Blob([editableCode.value]).size
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
})

// 编辑器注入脚本
const editorScript = `
<script>
(function() {
  let selectedEl = null;
  let hoveredEl = null;
  let isDragging = false;
  let dragStartX, dragStartY, dragElStartX, dragElStartY;
  let textEditToolbar = null;

  // 样式注入
  const style = document.createElement('style');
  style.textContent = \`
    [data-hover-highlight] {
      outline: 2px dashed #409eff !important;
      outline-offset: 2px;
    }
    [data-selected] {
      outline: 2px solid #409eff !important;
      outline-offset: 2px;
    }
    [data-dragging] {
      opacity: 0.7;
      cursor: grabbing !important;
    }
    .ce-text-toolbar {
      position: fixed;
      background: #1a1a2e;
      border-radius: 8px;
      padding: 6px 10px;
      display: flex;
      gap: 6px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      z-index: 99999;
      animation: fadeIn 0.15s ease;
    }
    .ce-text-toolbar button {
      background: transparent;
      border: none;
      color: #fff;
      width: 28px;
      height: 28px;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: bold;
    }
    .ce-text-toolbar button:hover {
      background: rgba(255,255,255,0.15);
    }
    .ce-text-toolbar button.active {
      background: #409eff;
    }
    .ce-text-toolbar .separator {
      width: 1px;
      background: rgba(255,255,255,0.2);
      margin: 0 4px;
    }
    .ce-color-picker {
      width: 28px;
      height: 28px;
      padding: 0;
      border: none;
      cursor: pointer;
    }
    [contenteditable="true"] {
      outline: 2px solid #67c23a !important;
      outline-offset: 2px;
      min-height: 1em;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-5px); }
      to { opacity: 1; transform: translateY(0); }
    }
  \`;
  document.head.appendChild(style);

  // 创建文字编辑工具栏
  function createTextToolbar() {
    if (textEditToolbar) return textEditToolbar;

    const toolbar = document.createElement('div');
    toolbar.className = 'ce-text-toolbar';
    toolbar.innerHTML = \`
      <button data-cmd="bold" title="加粗"><b>B</b></button>
      <button data-cmd="italic" title="斜体"><i>I</i></button>
      <button data-cmd="underline" title="下划线"><u>U</u></button>
      <div class="separator"></div>
      <button data-cmd="fontSize" data-value="3" title="小字">A-</button>
      <button data-cmd="fontSize" data-value="5" title="大字">A+</button>
      <div class="separator"></div>
      <input type="color" class="ce-color-picker" data-cmd="foreColor" value="#000000" title="文字颜色">
    \`;

    toolbar.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const btn = e.target.closest('button');
      const colorInput = e.target.closest('input[type="color"]');

      if (btn) {
        const cmd = btn.dataset.cmd;
        const value = btn.dataset.value;
        document.execCommand(cmd, false, value || null);
        updateToolbarState();
      }
    });

    const colorInput = toolbar.querySelector('input[type="color"]');
    colorInput.addEventListener('input', (e) => {
      document.execCommand('foreColor', false, e.target.value);
    });

    document.body.appendChild(toolbar);
    textEditToolbar = toolbar;
    return toolbar;
  }

  // 更新工具栏状态
  function updateToolbarState() {
    if (!textEditToolbar) return;
    const buttons = textEditToolbar.querySelectorAll('button');
    buttons.forEach(btn => {
      const cmd = btn.dataset.cmd;
      if (['bold', 'italic', 'underline'].includes(cmd)) {
        btn.classList.toggle('active', document.queryCommandState(cmd));
      }
    });
  }

  // 显示工具栏
  function showToolbar(el) {
    const toolbar = createTextToolbar();
    const rect = el.getBoundingClientRect();
    toolbar.style.left = rect.left + 'px';
    toolbar.style.top = (rect.top - 45) + 'px';
    toolbar.style.display = 'flex';
    updateToolbarState();
  }

  // 隐藏工具栏
  function hideToolbar() {
    if (textEditToolbar) {
      textEditToolbar.style.display = 'none';
    }
  }

  // 获取元素路径
  function getElementPath(el) {
    const path = [];
    while (el && el !== document.body) {
      let selector = el.tagName.toLowerCase();
      if (el.id) {
        selector += '#' + el.id;
      } else if (el.className && typeof el.className === 'string') {
        selector += '.' + el.className.split(' ').filter(c => c).join('.');
      }
      const siblings = Array.from(el.parentNode?.children || []).filter(c => c.tagName === el.tagName);
      if (siblings.length > 1) {
        selector += ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')';
      }
      path.unshift(selector);
      el = el.parentNode;
    }
    return path.join(' > ');
  }

  // 发送消息到父窗口
  function postMessage(type, data) {
    window.parent.postMessage({ type, ...data }, '*');
  }

  // 鼠标悬停
  document.addEventListener('mouseover', (e) => {
    if (isDragging) return;
    const el = e.target;
    if (el === document.body || el === document.documentElement) return;

    if (hoveredEl && hoveredEl !== el) {
      hoveredEl.removeAttribute('data-hover-highlight');
    }

    if (el !== selectedEl && !el.hasAttribute('contenteditable')) {
      el.setAttribute('data-hover-highlight', '');
      hoveredEl = el;
    }
  });

  document.addEventListener('mouseout', (e) => {
    if (hoveredEl) {
      hoveredEl.removeAttribute('data-hover-highlight');
    }
  });

  // 鼠标点击 - 选中元素
  document.addEventListener('click', (e) => {
    if (e.target.closest('.ce-text-toolbar')) return;

    const el = e.target;
    if (el === document.body || el === document.documentElement) return;

    // 取消之前的选中
    if (selectedEl) {
      selectedEl.removeAttribute('data-selected');
      selectedEl.removeAttribute('contenteditable');
      hideToolbar();
    }

    // 选中新元素
    el.removeAttribute('data-hover-highlight');
    el.setAttribute('data-selected', '');
    selectedEl = el;

    postMessage('element-selected', {
      tagName: el.tagName,
      id: el.id,
      className: el.className,
      path: getElementPath(el),
      outerHTML: el.outerHTML.substring(0, 500)
    });

    e.preventDefault();
    e.stopPropagation();
  });

  // 鼠标双击 - 编辑文字
  document.addEventListener('dblclick', (e) => {
    const el = e.target;
    if (el === document.body || el === document.documentElement) return;

    // 检查是否可以编辑文字
    const textNodes = Array.from(el.childNodes).filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
    const hasDirectText = textNodes.length > 0 || ['P', 'SPAN', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A', 'BUTTON', 'LI', 'TD', 'TH', 'LABEL'].includes(el.tagName);

    if (hasDirectText) {
      el.setAttribute('contenteditable', 'true');
      el.focus();
      showToolbar(el);

      // 监听内容变化
      el.addEventListener('input', () => {
        postMessage('content-changed', {
          path: getElementPath(el),
          html: document.body.innerHTML
        });
      });

      el.addEventListener('blur', () => {
        setTimeout(() => {
          if (!document.activeElement.closest('.ce-text-toolbar')) {
            el.removeAttribute('contenteditable');
            hideToolbar();
            postMessage('content-changed', {
              path: getElementPath(el),
              html: document.body.innerHTML
            });
          }
        }, 100);
      });
    }

    e.preventDefault();
    e.stopPropagation();
  });

  // 拖拽功能
  document.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('.ce-text-toolbar')) return;
    if (e.target.hasAttribute('contenteditable')) return;

    const el = selectedEl;
    if (!el || e.target !== el) return;

    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;

    const style = window.getComputedStyle(el);
    if (style.position === 'static') {
      el.style.position = 'relative';
    }
    dragElStartX = parseInt(style.left) || 0;
    dragElStartY = parseInt(style.top) || 0;

    el.setAttribute('data-dragging', '');
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging || !selectedEl) return;

    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;

    selectedEl.style.left = (dragElStartX + dx) + 'px';
    selectedEl.style.top = (dragElStartY + dy) + 'px';
  });

  document.addEventListener('mouseup', (e) => {
    if (!isDragging) return;

    isDragging = false;
    if (selectedEl) {
      selectedEl.removeAttribute('data-dragging');
      postMessage('content-changed', {
        path: getElementPath(selectedEl),
        html: document.body.innerHTML
      });
    }
  });

  // 监听选择变化以更新工具栏
  document.addEventListener('selectionchange', () => {
    if (textEditToolbar && textEditToolbar.style.display !== 'none') {
      updateToolbarState();
    }
  });

  // 监听来自父窗口的消息
  window.addEventListener('message', (e) => {
    const { type, path, html } = e.data || {};

    if (type === 'update-element' && path && html) {
      const el = document.querySelector(path);
      if (el) {
        el.outerHTML = html;
        postMessage('content-changed', {
          html: document.body.innerHTML
        });
      }
    }

    if (type === 'get-body-html') {
      postMessage('body-html', {
        html: document.body.innerHTML
      });
    }
  });
})();
<\/script>
`

// 生成完整的 HTML 文档（带编辑器脚本）
const fullHtmlWithEditor = computed(() => {
  const code = editableCode.value

  // 检查是否已经是完整的 HTML 文档
  if (code.trim().toLowerCase().startsWith('<!doctype') ||
      code.trim().toLowerCase().startsWith('<html')) {
    // 在 </body> 前注入编辑器脚本
    return code.replace('</body>', editorScript + '</body>')
  }

  // 包装为完整的 HTML 文档
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Canvas Editor</title>
  <script src="https://cdn.tailwindcss.com"><\/script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #333;
      padding: 20px;
    }
  </style>
</head>
<body>
${code}
${editorScript}
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
  setupIframeMessageListener()
}

// 设置 iframe 消息监听
const setupIframeMessageListener = () => {
  window.addEventListener('message', handleIframeMessage)
}

// 处理 iframe 消息
const handleIframeMessage = (e) => {
  const { type, tagName, id, className, path, outerHTML, html } = e.data || {}

  if (type === 'element-selected') {
    selectedElement.value = { tagName, id, className }
    selectedElementPath.value = path
    selectedElementHtml.value = outerHTML
  }

  if (type === 'content-changed' && html) {
    // 更新代码（只更新 body 内容）
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*)<\/body>/i)
    if (bodyMatch) {
      // 保留原有结构，只更新 body 内容
      editableCode.value = bodyMatch[1].trim()
      emit('update:code', editableCode.value)
    }
  }
}

// 刷新预览
const refreshPreview = () => {
  if (previewFrame.value) {
    const doc = fullHtmlWithEditor.value
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

// 新窗口打开
const openInNewWindow = () => {
  const newWindow = window.open('', '_blank')
  if (newWindow) {
    newWindow.document.write(fullHtmlWithEditor.value)
    newWindow.document.close()
  }
}

// 格式化代码
const formatCode = () => {
  let formatted = editableCode.value
    .replace(/></g, '>\n<')
    .replace(/\n\s*\n/g, '\n')

  const lines = formatted.split('\n')
  let indent = 0
  const result = []

  for (let line of lines) {
    line = line.trim()
    if (!line) continue

    if (line.startsWith('</') || line.startsWith('/>')) {
      indent = Math.max(0, indent - 1)
    }

    result.push('  '.repeat(indent) + line)

    if (line.match(/^<[^/!][^>]*[^/]>$/) && !line.match(/^<(br|hr|img|input|meta|link)/i)) {
      indent++
    }
  }

  editableCode.value = result.join('\n')
  ElMessage.success('代码已格式化')
}

// 打开 AI 编辑对话框
const openAIEditDialog = () => {
  aiEditPrompt.value = ''
  aiEditDialogVisible.value = true
}

// 应用 AI 编辑
const applyAIEdit = () => {
  if (!aiEditPrompt.value.trim()) {
    ElMessage.warning('请输入修改描述')
    return
  }

  // 发送 AI 编辑请求给父组件
  emit('ai-edit-request', {
    elementPath: selectedElementPath.value,
    elementHtml: selectedElementHtml.value,
    prompt: aiEditPrompt.value,
    fullCode: editableCode.value
  })

  aiEditDialogVisible.value = false
}

// 复制元素
const duplicateElement = () => {
  if (!previewFrame.value || !selectedElementPath.value) return

  previewFrame.value.contentWindow.postMessage({
    type: 'duplicate-element',
    path: selectedElementPath.value
  }, '*')
}

// 删除元素
const deleteElement = () => {
  if (!previewFrame.value || !selectedElementPath.value) return

  previewFrame.value.contentWindow.postMessage({
    type: 'delete-element',
    path: selectedElementPath.value
  }, '*')

  selectedElement.value = null
  selectedElementPath.value = ''
  selectedElementHtml.value = ''
}

// 清理
onUnmounted(() => {
  window.removeEventListener('message', handleIframeMessage)
})
</script>

<style scoped lang="scss">
.canvas-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 50px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafbfc;

  .header-left {
    .editor-tabs {
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

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.selection-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;

  .selection-info {
    display: flex;
    align-items: center;
    gap: 8px;

    .element-id {
      color: #ffd700;
      font-family: monospace;
    }

    .element-class {
      color: #90ee90;
      font-family: monospace;
    }
  }

  .selection-actions {
    display: flex;
    gap: 8px;
  }
}

.editor-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.design-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #e4e7ed;

  .canvas-container {
    flex: 1;
    padding: 16px;
    overflow: auto;
    display: flex;
    justify-content: center;

    &.desktop .preview-iframe {
      width: 100%;
      max-width: none;
    }

    &.tablet .preview-iframe {
      width: 768px;
      max-width: 768px;
    }

    &.mobile .preview-iframe {
      width: 375px;
      max-width: 375px;
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

.code-view {
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

.ai-edit-dialog {
  .selected-element-preview {
    margin-bottom: 16px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 8px;

    .preview-label {
      font-size: 12px;
      color: #909399;
      margin-bottom: 8px;
    }

    .preview-code {
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: #303133;
      max-height: 100px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fafbfc;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}
</style>
