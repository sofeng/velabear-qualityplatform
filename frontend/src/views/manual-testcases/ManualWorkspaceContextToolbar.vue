<template>
  <div class="workspace-context-toolbar">
    <div class="workspace-context-row">
      <div class="workspace-context-field">
        <span class="workspace-context-label">项目</span>
        <div class="workspace-context-group">
          <el-select
            :model-value="projectId"
            placeholder="请选择项目"
            class="workspace-context-select workspace-context-select--project"
            :style="projectSelectStyle"
            size="small"
            @change="value => emit('select-project', value)"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            >
              <span>{{ project.name }}</span>
              <span v-if="project.is_default" class="default-mark">(默认)</span>
            </el-option>
          </el-select>
          <el-button
            v-if="canSetDefaultProject"
            size="small"
            type="warning"
            plain
            :loading="defaultProjectLoading"
            :disabled="!selectedProject || selectedProject.is_default"
            @click="emit('set-default-project')"
          >
            {{ selectedProject?.is_default ? '默认项目' : '设为默认' }}
          </el-button>
        </div>
      </div>

      <div class="workspace-context-field">
        <span class="workspace-context-label">版本号</span>
        <div class="workspace-context-group">
          <el-select
            :model-value="versionId || 'all'"
            placeholder="请选择版本号"
            class="workspace-context-select workspace-context-select--version"
            :style="versionSelectStyle"
            size="small"
            :disabled="versionDisabled"
            @change="value => emit('select-version', value)"
          >
            <el-option label="全部" value="all" />
            <el-option
              v-for="version in versions"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            >
              <span>{{ version.name }}</span>
              <span v-if="version.is_default" class="default-mark">(默认)</span>
            </el-option>
          </el-select>
          <el-button type="primary" size="small" :disabled="versionDisabled" @click="emit('manage-versions')">
            管理版本
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  projectId: {
    type: [String, Number],
    default: ''
  },
  projects: {
    type: Array,
    default: () => []
  },
  selectedProject: {
    type: Object,
    default: null
  },
  projectSelectStyle: {
    type: Object,
    default: () => ({})
  },
  versionId: {
    type: [String, Number],
    default: 'all'
  },
  versions: {
    type: Array,
    default: () => []
  },
  versionSelectStyle: {
    type: Object,
    default: () => ({})
  },
  versionDisabled: {
    type: Boolean,
    default: false
  },
  canSetDefaultProject: {
    type: Boolean,
    default: false
  },
  defaultProjectLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'select-project',
  'select-version',
  'set-default-project',
  'manage-versions'
])
</script>

<style scoped>
.workspace-context-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  padding: 4px 0;
}

.workspace-context-row {
  min-width: 0;
  width: 100%;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 10px 12px;
}

.workspace-context-field {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 1 auto;
}

.workspace-context-label {
  color: #5f6f85;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  text-align: right;
  white-space: nowrap;
}

.workspace-context-group {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.workspace-context-group :deep(.el-button) {
  flex-shrink: 0;
}

.workspace-context-select {
  flex: 0 1 auto;
}

.workspace-context-select--project {
  min-width: 132px;
  max-width: 180px;
}

.workspace-context-select--version {
  min-width: 96px;
  max-width: 140px;
}

.default-mark {
  color: #67c23a;
  margin-left: 8px;
}

@media (max-width: 720px) {
  .workspace-context-row,
  .workspace-context-field {
    align-items: stretch;
  }

  .workspace-context-row,
  .workspace-context-field {
    flex-wrap: wrap;
  }

  .workspace-context-row {
    gap: 12px;
  }
}
</style>
