<template>
  <div class="manual-workflow-workbench manual-workspace-density-scope">
    <ManualWorkspaceSectionTabs
      class="workspace-section-tabs"
      :items="workspaceSectionTabs"
      active-name="workflow-workbench"
      @select="handleWorkspaceSectionSelect"
    />

    <WorkflowWorkbench />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import WorkflowWorkbench from '@/views/workflow/WorkflowWorkbench.vue'
import ManualWorkspaceSectionTabs from '@/views/manual-testcases/ManualWorkspaceSectionTabs.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('config')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'workflow-workbench') {
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}
</script>

<style scoped lang="scss">
.manual-workflow-workbench {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px 20px;
  background: #f5f7fb;
}
</style>
