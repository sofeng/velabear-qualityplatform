<template>
  <div
    class="manual-workspace-section-tabs"
    :class="{
      'manual-workspace-section-tabs--with-context': hasContext,
      'manual-workspace-section-tabs--with-summary': hasSummary,
      'manual-workspace-section-tabs--without-tabs': !hasTabs,
    }"
  >
    <div v-if="hasContext" class="manual-workspace-section-tabs__context">
      <slot name="context" />
    </div>

    <el-tabs
      v-if="hasTabs"
      :model-value="activeName"
      class="manual-workspace-section-tabs__tabs"
      @tab-change="handleTabChange"
    >
      <el-tab-pane
        v-for="item in items"
        :key="item.name"
        :label="item.label"
        :name="item.name"
      />
    </el-tabs>

    <div v-if="hasSummary" class="manual-workspace-section-tabs__summary">
      <slot name="summary" />
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  activeName: {
    type: String,
    default: '',
  },
  showContext: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['select'])
const slots = useSlots()

const hasContext = computed(() => props.showContext && Boolean(slots.context))
const hasSummary = computed(() => Boolean(slots.summary))
const hasTabs = computed(() => props.items.length > 0)

const handleTabChange = value => {
  emit('select', String(value || '').trim())
}
</script>

<style scoped lang="scss">
.manual-workspace-section-tabs {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 20px;
  min-width: 0;
}

.manual-workspace-section-tabs--with-context {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content minmax(0, 1fr);
  align-items: center;
  justify-content: stretch;
  column-gap: 16px;
}

.manual-workspace-section-tabs--with-context::after {
  content: '';
}

.manual-workspace-section-tabs--with-summary::after {
  display: none;
}

.manual-workspace-section-tabs--with-context.manual-workspace-section-tabs--with-summary.manual-workspace-section-tabs--without-tabs {
  grid-template-columns: max-content minmax(0, 1fr);
  column-gap: 16px;
}

.manual-workspace-section-tabs--with-context.manual-workspace-section-tabs--with-summary.manual-workspace-section-tabs--without-tabs .manual-workspace-section-tabs__summary {
  grid-column: 2;
}

.manual-workspace-section-tabs__context {
  grid-column: 1;
  flex: 0 1 auto;
  min-width: 0;
  justify-self: start;
  width: 100%;
}

.manual-workspace-section-tabs__tabs {
  grid-column: 2;
  flex: 1 1 auto;
  min-width: 0;
  justify-self: center;
}

.manual-workspace-section-tabs__summary {
  grid-column: 3;
  min-width: 0;
  display: flex;
  justify-content: flex-end;
  width: 100%;
  justify-self: end;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__header) {
  margin: 0;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__nav-wrap::after) {
  display: none;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__nav-scroll) {
  display: flex;
  justify-content: center;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__nav) {
  display: flex;
  gap: 8px;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__active-bar) {
  background-color: var(--topbar-base-color, #2396ea);
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__item) {
  height: 34px;
  line-height: 34px;
  padding: 0 16px;
  background: transparent;
  color: #606266;
  font-weight: 700;
  transition: background-color 0.2s ease, color 0.2s ease;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__item:hover) {
  background: transparent;
  color: var(--topbar-base-color, #2396ea);
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__item.is-active) {
  background: transparent;
  color: var(--topbar-base-color, #2396ea);
  box-shadow: none;
}

:deep(.manual-workspace-section-tabs__tabs .el-tabs__content) {
  display: none;
}

@media (max-width: 960px) {
  .manual-workspace-section-tabs,
  .manual-workspace-section-tabs--with-context {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
}
</style>
