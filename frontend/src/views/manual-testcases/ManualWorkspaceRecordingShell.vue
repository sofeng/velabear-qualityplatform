<template>
  <div class="manual-workspace-recording-shell manual-workspace-density-scope">
    <ManualWorkspaceContextProvider
      :model-value="modelValue"
      :directory-title="directoryTitle"
      @update:model-value="value => emit('update:modelValue', value)"
      @change="value => emit('change', value)"
    >
      <template #default="{ toolbarProps, directoryProps, actions }">
        <ManualWorkspaceSectionTabs
          class="workspace-section-tabs"
          :items="items"
          :active-name="activeName"
          @select="value => emit('select', value)"
        >
          <template #context>
            <ManualWorkspaceContextToolbar
              v-bind="toolbarProps"
              @select-project="actions.selectProject"
              @select-version="actions.selectVersion"
              @set-default-project="actions.setDefaultProject"
              @manage-versions="actions.manageVersions"
            />
          </template>
          <template v-if="$slots.summary" #summary>
            <slot name="summary" />
          </template>
        </ManualWorkspaceSectionTabs>

        <slot name="after-tabs" />

        <div :class="['manual-workspace-recording-shell__body', bodyClass]">
          <ManualWorkspaceDirectoryPanel
            v-if="showBodyDirectory"
            v-bind="directoryProps"
            :title="directoryTitle || directoryProps.title"
            @update:filter-text="actions.updateTreeFilterText"
            @toggle="actions.toggleDirectoryCollapsed"
            @node-click="actions.selectCategory"
            @node-contextmenu="actions.nodeContextmenu"
            @add-category="actions.addCategory"
            @edit-category="actions.editCategory"
            @delete-category="actions.deleteCategory"
            @import-xmind="actions.importXMind"
          />
          <slot :directory-props="directoryProps" :actions="actions" />
        </div>
      </template>
    </ManualWorkspaceContextProvider>
  </div>
</template>

<script setup>
import ManualWorkspaceContextProvider from '@/views/manual-testcases/ManualWorkspaceContextProvider.vue'
import ManualWorkspaceContextToolbar from '@/views/manual-testcases/ManualWorkspaceContextToolbar.vue'
import ManualWorkspaceDirectoryPanel from '@/views/manual-testcases/ManualWorkspaceDirectoryPanel.vue'
import ManualWorkspaceSectionTabs from '@/views/manual-testcases/ManualWorkspaceSectionTabs.vue'

defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  items: {
    type: Array,
    default: () => []
  },
  activeName: {
    type: String,
    default: ''
  },
  directoryTitle: {
    type: String,
    default: '目录树'
  },
  bodyClass: {
    type: [String, Array, Object],
    default: ''
  },
  showBodyDirectory: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'change', 'select'])
</script>

<style scoped>
.manual-workspace-recording-shell {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workspace-section-tabs {
  flex-shrink: 0;
}

.manual-workspace-recording-shell__body {
  min-height: 0;
  flex: 1;
  display: flex;
  gap: 12px;
  overflow: hidden;
}

.manual-workspace-recording-shell__body > :deep(.manual-workspace-directory-panel) {
  width: 280px;
}

.manual-workspace-recording-shell__body > :deep(.manual-workspace-directory-panel.left-panel--collapsed) {
  width: 56px;
}

.manual-workspace-recording-shell__body.execution-workspace {
  padding: 12px 24px 0;
}

.manual-workspace-recording-shell__body.editor-workspace {
  padding: 0 12px 12px;
}

.manual-workspace-recording-shell__body > :deep(main),
.manual-workspace-recording-shell__body > :deep(.editor-container) {
  flex: 1;
  min-width: 0;
}
</style>
