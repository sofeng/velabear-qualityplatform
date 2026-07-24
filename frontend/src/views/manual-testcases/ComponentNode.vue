<template>
  <div
    class="component-node"
    :class="`component-node-${componentType}`"
    @click.stop="handleClick"
  >
    <!-- 输入框节点 -->
    <div v-if="componentType === 'input'" class="component-content">
      <div class="component-label">📝 {{ truncate(config.text || '输入框', 12) }}</div>
      <input
        type="text"
        :placeholder="config.placeholder || '输入内容...'"
        :value="config.value || ''"
        readonly
        class="component-input"
      />
    </div>

    <!-- 按钮节点 -->
    <div v-else-if="componentType === 'button'" class="component-content">
      <button class="component-button">
        🔘 {{ truncate(config.text || '按钮', 12) }}
      </button>
      <div class="action-indicator">{{ getActionText(config.action) }}</div>
    </div>

    <!-- 下拉框节点 -->
    <div v-else-if="componentType === 'select'" class="component-content">
      <div class="component-label">📋 {{ truncate(config.text || '下拉框', 12) }}</div>
      <select class="component-select" disabled>
        <option>{{ config.selectedValue || '请选择...' }}</option>
      </select>
    </div>

    <!-- 复选框节点 -->
    <div v-else-if="componentType === 'checkbox'" class="component-content">
      <label class="component-checkbox-label">
        <input type="checkbox" :checked="config.checked" disabled class="component-checkbox-input" />
        <span>{{ truncate(config.text || '复选框', 12) }}</span>
      </label>
    </div>

    <!-- 链接节点 -->
    <div v-else-if="componentType === 'link'" class="component-content">
      <a href="javascript:void(0)" class="component-link">
        🔗 {{ truncate(config.text || '链接', 12) }}
      </a>
    </div>

    <!-- 通用节点 -->
    <div v-else class="component-content">
      <div class="component-label">📌 {{ truncate(config.text || componentType, 12) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: Object,
})

// 获取节点数据
const nodeData = computed(() => props.node?.data || {})
const componentType = computed(() => nodeData.value.componentType || 'generic')
const config = computed(() => nodeData.value.config || {})

// 文本截断
const truncate = (text, length) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

// 获取动作文本
const getActionText = (action) => {
  const actionMap = {
    'click': '单击',
    'dblclick': '双击',
    'contextmenu': '右键'
  }
  return actionMap[action] || '单击'
}

// 处理点击事件
const handleClick = () => {
  console.log('组件节点被点击:', props.node.id)

  // 触发自定义事件，通知父组件打开配置面板
  const event = new CustomEvent('component-node-click', {
    detail: {
      nodeId: props.node.id,
      componentType: componentType.value,
      config: config.value
    }
  })
  window.dispatchEvent(event)
}
</script>

<style scoped>
.component-node {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 2px solid #52c41a;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.component-node:hover {
  border-color: #73d13d;
  box-shadow: 0 4px 8px rgba(82, 196, 26, 0.2);
  transform: translateY(-1px);
}

.component-content {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.component-label {
  font-size: 11px;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  text-align: center;
}

/* 输入框样式 */
.component-input {
  width: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  background: #fafafa;
  color: #666;
  text-align: center;
}

/* 按钮样式 */
.component-button {
  width: 100%;
  background: linear-gradient(to bottom, #ffffff 0%, #f0f0f0 100%);
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  color: #333;
  cursor: pointer;
  font-weight: 500;
}

.action-indicator {
  font-size: 10px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 2px;
}

/* 下拉框样式 */
.component-select {
  width: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  background: #fafafa;
  color: #666;
  text-align: center;
}

/* 复选框样式 */
.component-checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #333;
  font-size: 12px;
}

.component-checkbox-input {
  width: 14px;
  height: 14px;
}

/* 链接样式 */
.component-link {
  color: #1890ff;
  text-decoration: none;
  font-size: 12px;
}

.component-link:hover {
  text-decoration: underline;
}

/* 不同类型的边框颜色 */
.component-node-input {
  border-color: #1890ff;
}

.component-node-button {
  border-color: #52c41a;
}

.component-node-select {
  border-color: #faad14;
}

.component-node-checkbox {
  border-color: #722ed1;
}

.component-node-link {
  border-color: #13c2c2;
}
</style>
