<template>
  <div class="recording-manager">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="recordings"
      directory-title="录制页面目录"
      body-class="recording-workspace"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >

      <main class="recording-main-panel">
        <el-card class="toolbar-card" shadow="never">
          <div class="toolbar">
            <div class="toolbar-filters">
              <div class="toolbar-summary">
                <div>
                  <div class="list-title">录制管理</div>
                  <div class="list-subtitle">
                    共 {{ pagination.total }} 个录制会话，当前页 {{ recordings.length }} 个
                  </div>
                </div>
              </div>

              <el-input
                v-model="filters.keyword"
                clearable
                placeholder="搜索录制名称、会话ID或目标地址"
                style="width: 300px"
                @keyup.enter="resetAndLoadRecordings"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 150px" @change="resetAndLoadRecordings">
                <el-option label="启动中" value="starting" />
                <el-option label="录制中" value="recording" />
                <el-option label="停止中" value="stopping" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-button :loading="loading" @click="loadRecordings">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <TableColumnSettings
                :table-ref="recordingTableRef"
                storage-key="manual-testcases.snapshot-recordings"
              />
              <el-button :loading="settingsLoading" @click="openSettingsDialog">
                <el-icon><Setting /></el-icon>
                并发数设置
              </el-button>
              <el-button type="success" :loading="recordingStarting" @click="openStartDialog">
                <el-icon><VideoPlay /></el-icon>
                服务端Playwright CLI录制
              </el-button>
              <el-button type="primary" plain :loading="recordingStarting" @click="openLocalAgentStartDialog">
                <el-icon><VideoPlay /></el-icon>
                本地Agent-Playwright录制
              </el-button>
              <el-button :loading="localAgentState.checking" @click="openLocalAgentManager">
                <el-icon><Monitor /></el-icon>
                本地Agent
                <el-tag size="small" :type="localAgentStatusTagType">{{ localAgentStatusLabel }}</el-tag>
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card class="list-card" shadow="never">
          <div class="table-shell">
          <el-table ref="recordingTableRef" v-loading="loading" :data="recordings" height="100%" border stripe>
        <el-table-column prop="name" label="录制名称" min-width="220">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.session_id)">
              {{ row.name || row.session_id }}
            </el-button>
            <div class="row-subtext">{{ row.session_id }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="target_url" label="目标地址" min-width="260" show-overflow-tooltip />
        <el-table-column label="录制方式" min-width="180">
          <template #default="{ row }">
            <el-tag :type="getRecordingMethodTagType(row.recording_method)">
              {{ getRecordingMethodLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="browser_type" label="浏览器" width="110" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模块" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ getSessionModuleLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="创建人" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ getUserDisplayName(row.started_by) || row.started_by_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="steps_count" label="步骤数" width="90" align="right" />
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">{{ formatDate(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="180">
          <template #default="{ row }">{{ formatDate(row.stopped_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="390" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.session_id)">查看</el-button>
            <el-button link type="primary" @click="openRecordingEdit(row)">编辑</el-button>
            <el-button
              v-if="isActiveStatus(row.status)"
              link
              type="warning"
              :loading="stoppingSessionId === row.session_id"
              @click="stopRecording(row.session_id)"
            >
              停止
            </el-button>
            <el-button
              v-if="getRecordingBrowserUrl(row)"
              link
              type="primary"
              @click="openRecordingBrowser(row)"
            >
              打开浏览器
            </el-button>
            <el-button link type="success" :disabled="!row.steps_count" @click="showFlow(row.session_id)">
              流程数据
            </el-button>
            <el-button
              link
              type="warning"
              :disabled="!row.steps_count"
              :loading="generatingAllureSessionId === row.session_id"
              @click="generateAllureReport(row)"
            >
              Allure报告
            </el-button>
            <el-button
              v-if="isActiveStatus(row.status)"
              link
              type="success"
              @click="openLiveFlow(row)"
            >
              实时流程图
            </el-button>
            <el-button
              link
              type="primary"
              :disabled="!getRecordingFlowId(row)"
              @click="openCreatedFlow(row)"
            >
              查看流程
            </el-button>
            <el-button
              link
              type="primary"
              :disabled="!row.steps_count"
              :loading="creatingFlowSessionId === row.session_id"
              @click="createFlow(row)"
            >
              创建流程
            </el-button>
            <el-button link type="danger" @click="deleteRecording(row.session_id)">删除</el-button>
          </template>
        </el-table-column>
          </el-table>
          </div>

          <div class="table-footer">
            <div class="table-footer-text">
              活动录制 {{ recorderSettings.active_count || activeSessionIds.length }} 个
            </div>
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
            />
          </div>
        </el-card>
      </main>
    </ManualWorkspaceRecordingShell>

    <el-dialog
      v-model="settingsDialogVisible"
      title="并发数设置"
      width="420px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="最大并发录制数量" required>
          <el-input-number
            v-model="settingsForm.max_sessions"
            :min="settingsInputMin"
            :max="settingsInputMax"
            :step="1"
            step-strictly
            controls-position="right"
            style="width: 180px"
          />
        </el-form-item>
        <div class="settings-help">
          当前活动录制 {{ recorderSettings.active_count || 0 }} 个<span v-if="recorderSettings.capacity">，端口容量上限 {{ recorderSettings.capacity }} 个</span>。
        </div>
      </el-form>
      <template #footer>
        <el-button @click="settingsDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="settingsSaving" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="startDialogVisible"
      :title="startDialogTitle"
      width="520px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="录制名称">
          <el-input v-model="recordingForm.name" placeholder="例如 登录与下单流程" />
        </el-form-item>
        <el-form-item label="目标系统地址" required>
          <el-input v-model="recordingForm.target_url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="浏览器">
          <el-select v-model="recordingForm.browser_type" style="width: 180px">
            <el-option label="Chromium" value="chromium" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="WebKit" value="webkit" />
          </el-select>
        </el-form-item>
        <el-form-item label="录制页面（目录树节点）" required>
          <div class="module-picker">
            <div class="module-picker-row">
              <el-select
                v-model="recordingForm.project_id"
                clearable
                filterable
                placeholder="选择项目"
                style="width: 180px"
                @change="handleRecordingProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <el-button :loading="moduleCategoryLoading" @click="loadModuleCategories(recordingForm.project_id)">
                加载目录树
              </el-button>
            </div>
            <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选页面目录" />
            <div class="module-tree-box">
              <el-tree
                ref="moduleTreeRef"
                :data="moduleCategoryTree"
                node-key="id"
                :props="{ label: 'label', children: 'children' }"
                :filter-node-method="filterModuleTreeNode"
                highlight-current
                default-expand-all
                @node-click="node => applyModuleSelection(recordingForm, node)"
              />
              <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
            </div>
            <div class="module-current">录制范围：{{ recordingForm.module_path || recordingForm.module_name || '未选择目录树页面' }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="recordingStarting" @click="startRecording">
          启动录制
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="recordingEditDialogVisible"
      title="编辑录制信息"
      width="560px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="录制名称" required>
          <el-input v-model="recordingEditForm.name" placeholder="请输入录制名称" />
        </el-form-item>
        <el-form-item label="录制页面（目录树节点）">
          <div class="module-picker">
            <div class="module-picker-row">
              <el-select
                v-model="recordingEditForm.project_id"
                clearable
                filterable
                placeholder="选择项目"
                style="width: 180px"
                @change="handleRecordingEditProjectChange"
              >
                <el-option
                  v-for="project in projects"
                  :key="project.id"
                  :label="project.name"
                  :value="project.id"
                />
              </el-select>
              <el-button :loading="moduleCategoryLoading" @click="loadModuleCategories(recordingEditForm.project_id)">
                加载目录树
              </el-button>
              <el-button link type="danger" @click="clearModuleSelection(recordingEditForm)">清空目录选择</el-button>
            </div>
            <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选页面目录" />
            <div class="module-tree-box">
              <el-tree
                ref="moduleTreeRef"
                :data="moduleCategoryTree"
                node-key="id"
                :props="{ label: 'label', children: 'children' }"
                :filter-node-method="filterModuleTreeNode"
                highlight-current
                default-expand-all
                @node-click="node => applyModuleSelection(recordingEditForm, node)"
              />
              <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
            </div>
            <div class="module-current">录制范围：{{ recordingEditForm.module_path || recordingEditForm.module_name || '未选择目录树页面' }}</div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordingEditDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRecording" @click="saveRecordingEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="drawerVisible"
      :title="selectedSession?.name || '录制详情'"
      size="72%"
      direction="rtl"
      :destroy-on-close="false"
    >
      <div v-loading="detailLoading" class="detail-panel">
        <div v-if="selectedSession" class="detail-actions">
          <el-tag :type="getStatusType(selectedSession.status)">
            {{ getStatusLabel(selectedSession.status) }}
          </el-tag>
          <el-button
            v-if="getRecordingBrowserUrl(selectedSession)"
            type="primary"
            plain
            @click="openRecordingBrowser(selectedSession)"
          >
            打开受控浏览器
          </el-button>
          <el-button
            v-if="isActiveStatus(selectedSession.status)"
            type="warning"
            plain
            :loading="stoppingSessionId === selectedSession.session_id"
            @click="stopRecording(selectedSession.session_id)"
          >
            停止录制
          </el-button>
          <el-button
            type="success"
            plain
            :disabled="!selectedSession.steps?.length"
            :loading="generatingFlowSessionId === selectedSession.session_id"
            @click="showFlow(selectedSession, { syncCreatedFlow: true })"
          >
            {{ getRecordingFlowId(selectedSession) ? '重新生成流程数据' : '生成流程数据' }}
          </el-button>
          <el-button
            v-if="isActiveStatus(selectedSession.status)"
            type="success"
            plain
            @click="openLiveFlow(selectedSession)"
          >
            实时流程图
          </el-button>
          <el-button
            type="info"
            plain
            :disabled="!selectedSession.steps?.length"
            :loading="dedupingSessionId === selectedSession.session_id"
            @click="dedupeSnapshots(selectedSession)"
          >
            快照文件去重
          </el-button>
          <el-button
            type="warning"
            plain
            :disabled="!selectedSession.steps?.length"
            :loading="generatingAllureSessionId === selectedSession.session_id"
            @click="generateAllureReport(selectedSession)"
          >
            生成Allure报告
          </el-button>
          <el-button
            v-if="getAllureReportUrl(selectedSession)"
            type="primary"
            plain
            @click="openAllureReport(selectedSession)"
          >
            查看Allure报告
          </el-button>
          <el-button
            type="warning"
            plain
            :disabled="!selectedSession.steps?.length || isActiveStatus(selectedSession.status)"
            :loading="identifyingJunkSteps"
            @click="identifyJunkSteps"
          >
            识别垃圾步骤
          </el-button>
          <el-button
            type="danger"
            plain
            :disabled="!selectedStepIds.length"
            :loading="batchDeletingSteps"
            @click="deleteSelectedSteps"
          >
            批量删除{{ selectedStepIds.length ? `(${selectedStepIds.length})` : '' }}
          </el-button>
          <el-button
            type="primary"
            plain
            :disabled="!selectedSession.steps?.length"
            :loading="creatingFlowSessionId === selectedSession.session_id"
            @click="createFlow(selectedSession)"
          >
            创建流程
          </el-button>
        </div>

        <el-descriptions v-if="selectedSession" :column="2" border>
          <el-descriptions-item label="录制名称">
            <div class="description-action-cell">
              <span>{{ selectedSession.name || '-' }}</span>
              <el-button link type="primary" @click="openRecordingEdit(selectedSession)">编辑</el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">
            {{ getUserDisplayName(selectedSession.started_by) || selectedSession.started_by_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="会话ID">{{ selectedSession.session_id }}</el-descriptions-item>
          <el-descriptions-item label="录制方式">{{ getRecordingMethodLabel(selectedSession) }}</el-descriptions-item>
          <el-descriptions-item label="浏览器">{{ selectedSession.browser_type }}</el-descriptions-item>
          <el-descriptions-item label="目标地址">{{ selectedSession.target_url }}</el-descriptions-item>
          <el-descriptions-item label="模块">
            <div class="description-action-cell">
              <span>{{ getSessionModuleLabel(selectedSession) }}</span>
              <el-button link type="primary" @click="openRecordingEdit(selectedSession)">选择</el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="步骤数">{{ selectedSession.steps_count || selectedSession.steps?.length || 0 }}</el-descriptions-item>
          <el-descriptions-item v-if="getRecordingBrowserUrl(selectedSession)" label="受控浏览器" :span="2">
            <el-button link type="primary" @click="openRecordingBrowser(selectedSession)">
              {{ getRecordingBrowserUrl(selectedSession) }}
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item
            v-if="selectedSession.recording_method === RECORDING_METHOD_LOCAL_AGENT"
            label="本地Agent配对"
            :span="2"
          >
            <div class="agent-pairing-cell">
              <div>{{ selectedSession.metadata?.local_agent_pairing_url || '-' }}</div>
              <el-button link type="primary" @click="showLocalAgentGuide(selectedSession)">查看连接信息</el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatDate(selectedSession.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatDate(selectedSession.stopped_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedSession.error_message" label="错误信息" :span="2">
            <el-text type="danger">{{ selectedSession.error_message }}</el-text>
          </el-descriptions-item>
        </el-descriptions>

        <TableColumnSettings
          :table-ref="recordingStepTableRef"
          storage-key="manual-testcases.snapshot-recording-steps"
        />

        <el-table
          v-if="selectedSession"
          ref="recordingStepTableRef"
          class="steps-table"
          :data="selectedSession.steps || []"
          border
          stripe
          :row-class-name="getStepRowClassName"
          @selection-change="handleStepSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="step_number" label="#" width="70" align="right" />
          <el-table-column prop="action_type" label="动作" width="110">
            <template #default="{ row }">
              <el-tag>{{ getActionLabel(row.action_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作值" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ getActionValue(row) }}</template>
          </el-table-column>
          <el-table-column label="元素" min-width="240">
            <template #default="{ row }">
              <div class="element-cell">{{ getElementLabel(row.element) }}</div>
              <div class="row-subtext">{{ row.element?.tag || '-' }} {{ row.element?.role || '' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="页面" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <div>{{ row.page_title || '-' }}</div>
              <div class="row-subtext">{{ row.page_url }}</div>
            </template>
          </el-table-column>
          <el-table-column label="快照文件" min-width="210">
            <template #default="{ row }">
              <el-button
                v-if="getStepSnapshotFilename(row)"
                link
                type="primary"
                class="snapshot-file-link"
                @click="openSnapshotPreview(row)"
              >
                {{ getStepSnapshotFilename(row) }}
              </el-button>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="选择器" width="130">
            <template #default="{ row }">
              <el-popover width="460" trigger="click">
                <template #reference>
                  <el-button link type="primary">查看</el-button>
                </template>
                <div class="selector-popover">
                  <div v-if="getLocatorRows(row).length" class="locator-values">
                    <div class="locator-title">八大定位法</div>
                    <div v-for="locator in getLocatorRows(row)" :key="locator.type" class="locator-row">
                      <span class="locator-label">{{ locator.label }}</span>
                      <span class="locator-value">{{ locator.value }}</span>
                    </div>
                  </div>
                  <pre class="json-preview">{{ stringify(getDisplaySelectors(row)) }}</pre>
                  <div class="selector-actions">
                    <el-button
                      size="small"
                      type="danger"
                      :loading="deletingStepId === row.id"
                      @click="deleteStep(row)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" :loading="deletingStepId === row.id" @click="deleteStep(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <el-dialog v-model="flowDialogVisible" title="录制生成流程数据" width="760px">
      <pre class="flow-preview">{{ flowPreview }}</pre>
      <template #footer>
        <el-button @click="flowDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyText(flowPreview, '流程数据已复制')">
          复制 JSON
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="snapshotDialogVisible"
      :title="snapshotDialogTitle"
      width="880px"
      destroy-on-close
    >
      <div v-loading="snapshotLoading" class="snapshot-dialog-body">
        <el-form label-position="top">
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="快照文件">
                <el-input v-model="snapshotForm.filename" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="页面名称">
                <el-input v-model="snapshotForm.page_name" :disabled="!snapshotEditing" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="别名">
                <el-input v-model="snapshotForm.alias" :disabled="!snapshotEditing" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="模块">
            <div class="module-picker">
              <div class="module-picker-row">
                <el-select
                  v-model="snapshotForm.project_id"
                  clearable
                  filterable
                  :disabled="!snapshotEditing"
                  placeholder="选择项目"
                  style="width: 180px"
                  @change="handleSnapshotProjectChange"
                >
                  <el-option
                    v-for="project in projects"
                    :key="project.id"
                    :label="project.name"
                    :value="project.id"
                  />
                </el-select>
                <el-button :disabled="!snapshotEditing" :loading="moduleCategoryLoading" @click="loadModuleCategories(snapshotForm.project_id)">
                  加载目录
                </el-button>
                <el-button v-if="snapshotEditing" link type="danger" @click="clearModuleSelection(snapshotForm)">清空模块</el-button>
              </div>
              <template v-if="snapshotEditing">
                <el-input v-model="moduleTreeFilterText" clearable placeholder="筛选模块" />
                <div class="module-tree-box">
                  <el-tree
                    ref="moduleTreeRef"
                    :data="moduleCategoryTree"
                    node-key="id"
                    :props="{ label: 'label', children: 'children' }"
                    :filter-node-method="filterModuleTreeNode"
                    highlight-current
                    default-expand-all
                    @node-click="node => applyModuleSelection(snapshotForm, node)"
                  />
                  <el-empty v-if="!moduleCategoryTree.length && !moduleCategoryLoading" description="暂无目录数据" :image-size="64" />
                </div>
              </template>
              <div class="module-current">当前模块：{{ snapshotForm.module_path || snapshotForm.module_name || '-' }}</div>
            </div>
          </el-form-item>
          <el-form-item label="YAML 内容">
            <el-input
              v-if="snapshotEditing"
              v-model="snapshotForm.content"
              type="textarea"
              :autosize="{ minRows: 16, maxRows: 28 }"
            />
            <pre v-else class="snapshot-preview">{{ snapshotForm.content }}</pre>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="snapshotDialogVisible = false">关闭</el-button>
        <el-button v-if="!snapshotEditing" type="primary" @click="snapshotEditing = true">编辑</el-button>
        <el-button v-else type="primary" :loading="snapshotSaving" @click="saveSnapshotEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="localAgentDialogVisible"
      title="本地 Agent 管理与录制"
      width="840px"
      destroy-on-close
    >
      <div class="agent-guide">
        <div class="agent-status-panel">
          <div class="agent-status-main">
            <el-tag :type="localAgentStatusTagType" effect="dark">{{ localAgentStatusLabel }}</el-tag>
            <span>{{ localAgentStatusSummary }}</span>
          </div>
          <div class="agent-status-actions">
            <el-button size="small" :loading="localAgentState.checking" @click="detectLocalAgent">
              检测 Agent
            </el-button>
            <el-button size="small" type="primary" :loading="localAgentState.starting" @click="startInstalledLocalAgent">
              启动 Agent
            </el-button>
            <el-button size="small" :loading="localAgentState.restarting" @click="restartInstalledLocalAgent">
              重启 Agent
            </el-button>
            <el-button size="small" type="warning" plain :loading="localAgentState.stopping" @click="stopInstalledLocalAgent">
              停止 Agent
            </el-button>
            <el-button size="small" type="success" :loading="localAgentState.downloading" @click="downloadLocalAgentInstaller">
              下载安装器
            </el-button>
            <el-button size="small" type="success" plain :loading="localAgentState.updating" :disabled="localAgentState.status !== 'available'" @click="updateInstalledLocalAgent">
              升级/修复 Agent
            </el-button>
            <el-button size="small" type="danger" plain :loading="localAgentState.uninstalling" @click="uninstallLocalAgent">
              卸载 Agent
            </el-button>
          </div>
        </div>
        <el-alert
          :closable="false"
          :type="localAgentInfo.launch_status === 'failed' ? 'warning' : 'info'"
          :title="localAgentGuideTitle"
        />
        <el-descriptions :column="1" border>
          <el-descriptions-item label="本地服务">{{ LOCAL_AGENT_SERVICE_URL }}</el-descriptions-item>
          <el-descriptions-item label="运行状态">{{ localAgentStatusSummary }}</el-descriptions-item>
          <el-descriptions-item label="Agent版本">{{ localAgentRuntime.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="进程ID">{{ localAgentRuntime.pid || '-' }}</el-descriptions-item>
          <el-descriptions-item label="已运行">{{ localAgentRuntime.uptime_seconds ? `${localAgentRuntime.uptime_seconds} 秒` : '-' }}</el-descriptions-item>
          <el-descriptions-item label="会话ID">{{ localAgentInfo.session_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="启动状态">{{ localAgentLaunchStatusLabel }}</el-descriptions-item>
          <el-descriptions-item v-if="localAgentInfo.launch_error" label="启动提示">
            {{ localAgentInfo.launch_error }}
          </el-descriptions-item>
          <el-descriptions-item label="配对地址">{{ localAgentInfo.pairing_url || '-' }}</el-descriptions-item>
          <el-descriptions-item label="API地址">{{ localAgentInfo.api_origin || '-' }}</el-descriptions-item>
          <el-descriptions-item label="过期时间">{{ localAgentInfo.expires_at || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="agent-install-steps">
          <div class="agent-install-step">
            <span class="agent-install-step__index">1</span>
            <span>未安装时点击“下载安装器”，解压后双击 install.bat 完成首次安装。</span>
          </div>
          <div class="agent-install-step">
            <span class="agent-install-step__index">2</span>
            <span>安装器会自动检查 Python、pip、Playwright 等版本，缺失或过低时自动安装/升级。</span>
          </div>
          <div class="agent-install-step">
            <span class="agent-install-step__index">3</span>
            <span>安装后浏览器允许打开 testhub-agent 协议，已安装后可使用“升级/修复 Agent”。</span>
          </div>
        </div>
        <el-form label-position="top">
          <el-form-item label="本地 Agent 服务启动命令">
            <el-input
              :model-value="localAgentServiceCommand"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              readonly
            />
          </el-form-item>
          <el-form-item label="配对 Token">
            <el-input v-model="localAgentInfo.token" readonly show-password />
          </el-form-item>
          <el-form-item label="单次 Agent 启动命令">
            <el-input
              :model-value="localAgentCommand"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 5 }"
              readonly
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="localAgentDialogVisible = false">关闭</el-button>
        <el-button @click="copyText(localAgentServiceCommand, '本地 Agent 服务启动命令已复制')">复制服务命令</el-button>
        <el-button type="primary" @click="copyText(localAgentCommand, '单次 Agent 启动命令已复制')">复制单次命令</el-button>
        <el-button type="success" :disabled="!localAgentInfo.session_id" @click="openDetail(localAgentInfo.session_id)">
          查看录制详情
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Monitor, Refresh, Search, Setting, VideoPlay } from '@element-plus/icons-vue'
import {
  batchDeletePlaywrightRecordingSteps,
  createPlaywrightRecordingFlow,
  deletePlaywrightRecording,
  deletePlaywrightRecordingStep,
  dedupePlaywrightRecordingSnapshots,
  downloadLocalAgentPackage,
  getManualCategories,
  getPlaywrightSnapshotContent,
  getProjectList,
  generatePlaywrightRecordingAllureReport,
  getPlaywrightRecordingDetail,
  getPlaywrightRecordingFlow,
  getPlaywrightRecordings,
  getPlaywrightRecordingSettings,
  identifyPlaywrightRecordingJunkSteps,
  startPlaywrightRecording,
  stopPlaywrightRecording,
  updatePlaywrightRecording,
  updatePlaywrightRecordingSettings,
  updatePlaywrightSnapshot
} from '@/api/testcases'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const recordingTableRef = ref(null)
const recordingStepTableRef = ref(null)
const detailLoading = ref(false)
const recordingStarting = ref(false)
const startDialogVisible = ref(false)
const startRecordingMethod = ref('server_playwright_cli')
const localAgentDialogVisible = ref(false)
const settingsDialogVisible = ref(false)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const drawerVisible = ref(false)
const flowDialogVisible = ref(false)
const recordingEditDialogVisible = ref(false)
const savingRecording = ref(false)
const snapshotDialogVisible = ref(false)
const snapshotLoading = ref(false)
const snapshotSaving = ref(false)
const snapshotEditing = ref(false)
const stoppingSessionId = ref('')
const creatingFlowSessionId = ref('')
const generatingFlowSessionId = ref('')
const generatingAllureSessionId = ref('')
const dedupingSessionId = ref('')
const deletingStepId = ref(null)
const identifyingJunkSteps = ref(false)
const batchDeletingSteps = ref(false)
const selectedStepRows = ref([])
const junkStepMap = ref({})
const recordings = ref([])
const activeSessionIds = ref([])
const selectedSession = ref(null)
const flowPreview = ref('')
const projects = ref([])
const moduleCategoryTree = ref([])
const moduleCategoryLoading = ref(false)
const moduleTreeFilterText = ref('')
const moduleTreeRef = ref(null)
let pollTimer = null
let localAgentLastCheckedAt = 0
const openedBrowserSessionIds = new Set()

const RECORDING_METHOD_SERVER = 'server_playwright_cli'
const RECORDING_METHOD_LOCAL_AGENT = 'local_agent_playwright'
const LOCAL_AGENT_SERVICE_URL = 'http://127.0.0.1:18765'
const LOCAL_AGENT_PROTOCOL = 'testhub-agent://'

const filters = reactive({
  keyword: '',
  status: ''
})
const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'recordings') {
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const recorderSettings = reactive({
  max_sessions: 0,
  configured_max_sessions: null,
  default_max_sessions: 0,
  capacity: null,
  active_count: 0,
  source: ''
})

const settingsForm = reactive({
  max_sessions: 1
})

const emptyModuleFields = {
  project_id: '',
  module_id: '',
  module_name: '',
  module_path: ''
}

const recordingForm = reactive({
  name: '',
  target_url: '',
  browser_type: 'chromium',
  ...emptyModuleFields
})
const researchContext = ref({ ...emptyModuleFields, version_id: 'all', version_name: '' })

const localAgentInfo = reactive({
  session_id: '',
  pairing_url: '',
  api_origin: '',
  token: '',
  expires_at: '',
  launch_status: 'idle',
  launch_error: ''
})

const localAgentState = reactive({
  status: 'checking',
  checking: false,
  starting: false,
  stopping: false,
  restarting: false,
  downloading: false,
  updating: false,
  uninstalling: false,
  install_watch: false,
  error: '',
  last_checked_at: ''
})

const localAgentRuntime = reactive({
  version: '',
  pid: '',
  started_at: '',
  uptime_seconds: 0,
  platform: '',
  python: '',
  sessions: []
})

const recordingEditForm = reactive({
  session_id: '',
  name: '',
  ...emptyModuleFields
})

const snapshotForm = reactive({
  originalFilename: '',
  filename: '',
  page_name: '',
  alias: '',
  content: '',
  ...emptyModuleFields
})

const activeRecordings = computed(() => recordings.value.filter(item => isActiveStatus(item.status)))
const selectedStepIds = computed(() => selectedStepRows.value.map(row => row.id).filter(Boolean))

const snapshotDialogTitle = computed(() => `${snapshotEditing.value ? '编辑' : '预览'}快照文件`)
const startDialogTitle = computed(() => (
  startRecordingMethod.value === RECORDING_METHOD_LOCAL_AGENT
    ? '启动本地Agent-Playwright录制'
    : '启动服务端Playwright CLI录制'
))
const localAgentCommand = computed(() => {
  if (!localAgentInfo.pairing_url || !localAgentInfo.token) return ''
  return `python tools/local_playwright_agent.py --pairing-url "${localAgentInfo.pairing_url}" --token "${localAgentInfo.token}"`
})
const localAgentServiceCommand = computed(() => 'tools\\start_local_playwright_agent.bat')
const localAgentGuideTitle = computed(() => {
  if (localAgentInfo.launch_status === 'recording') {
    return '本地浏览器已由本地 Agent 服务拉起，请在新打开的浏览器中操作。'
  }
  if (localAgentInfo.launch_status === 'starting') {
    return '正在请求本地 Agent 服务启动本地浏览器。'
  }
  if (localAgentInfo.launch_status === 'failed') {
    return '未检测到可用的本地 Agent 服务。若未安装，请先下载安装器并双击 install.bat；若已安装，请允许浏览器打开 testhub-agent 协议。'
  }
  return '首次安装需要用户确认系统安全提示；安装器会自动检查 Python、pip、Playwright 等版本并补齐环境，完成后平台可启动、重启或升级本地 Agent。'
})
const localAgentLaunchStatusLabel = computed(() => {
  const labels = {
    idle: '未启动',
    starting: '启动中',
    recording: '已启动',
    failed: '未自动启动'
  }
  return labels[localAgentInfo.launch_status] || localAgentInfo.launch_status || '-'
})
const localAgentStatusTagType = computed(() => {
  const typeMap = {
    available: 'success',
    checking: 'info',
    starting: 'warning',
    unavailable: 'warning',
    error: 'danger'
  }
  return typeMap[localAgentState.status] || 'info'
})
const localAgentStatusLabel = computed(() => {
  const labels = {
    available: '可用',
    checking: '检测中',
    starting: '启动中',
    unavailable: '未运行',
    error: '异常'
  }
  return labels[localAgentState.status] || '未知'
})
const localAgentStatusSummary = computed(() => {
  if (localAgentState.status === 'available') {
    const version = localAgentRuntime.version ? ` v${localAgentRuntime.version}` : ''
    const pid = localAgentRuntime.pid ? `，PID ${localAgentRuntime.pid}` : ''
    return `本地 Agent 已连接${version}${pid}`
  }
  if (localAgentState.status === 'checking') {
    return '正在检测本地 Agent 服务'
  }
  if (localAgentState.status === 'starting') {
    return '正在尝试唤起本机已安装的 Agent'
  }
  if (localAgentState.install_watch) {
    return '安装器已下载，等待本机安装完成并自动检测 Agent'
  }
  return localAgentState.error || '未检测到本地 Agent，可启动已安装 Agent 或下载安装包'
})

const hasActiveRecordings = computed(() => {
  return activeRecordings.value.length > 0 || activeSessionIds.value.length > 0 || Number(recorderSettings.active_count || 0) > 0
})

const settingsInputMin = computed(() => Math.max(1, Number(recorderSettings.active_count || 0)))
const settingsInputMax = computed(() => {
  const capacity = Number(recorderSettings.capacity || 0)
  return capacity > 0 ? capacity : undefined
})

watch(
  () => [filters.keyword, filters.status],
  () => {
    if (pagination.page !== 1) {
      pagination.page = 1
    } else {
      loadRecordings()
    }
  }
)

watch(
  () => [pagination.page, pagination.pageSize],
  () => {
    loadRecordings()
  }
)

watch(
  () => pagination.total,
  total => {
    const maxPage = Math.max(1, Math.ceil(total / pagination.pageSize))
    if (pagination.page > maxPage) {
      pagination.page = maxPage
    }
  }
)

watch(moduleTreeFilterText, value => {
  moduleTreeRef.value?.filter?.(value)
})

watch(
  () => recordingForm.module_id,
  moduleId => {
    if (moduleId) {
      setTimeout(() => moduleTreeRef.value?.setCurrentKey?.(moduleId), 0)
    }
  }
)

const isActiveStatus = status => ['starting', 'recording', 'stopping'].includes(status)

const applyRecorderSettings = payload => {
  const settings = payload && typeof payload === 'object' ? payload : {}
  recorderSettings.max_sessions = Number(settings.max_sessions || 0)
  recorderSettings.configured_max_sessions = settings.configured_max_sessions ?? null
  recorderSettings.default_max_sessions = Number(settings.default_max_sessions || 0)
  recorderSettings.capacity = settings.capacity ?? null
  recorderSettings.active_count = Number(settings.active_count || 0)
  recorderSettings.source = settings.source || ''
}

const syncSettingsForm = () => {
  settingsForm.max_sessions = recorderSettings.max_sessions || 1
}

const loadRecordingSettings = async () => {
  settingsLoading.value = true
  try {
    const response = await getPlaywrightRecordingSettings()
    applyRecorderSettings(response.data || {})
    syncSettingsForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '加载并发设置失败')
  } finally {
    settingsLoading.value = false
  }
}

const resetAndLoadRecordings = () => {
  if (pagination.page !== 1) {
    pagination.page = 1
  } else {
    loadRecordings()
  }
}

const openSettingsDialog = async () => {
  settingsDialogVisible.value = true
  await loadRecordingSettings()
}

const saveSettings = async () => {
  const maxSessions = Number(settingsForm.max_sessions)
  const minSessions = Math.max(1, Number(recorderSettings.active_count || 0))
  const capacity = Number(recorderSettings.capacity || 0)
  if (!Number.isInteger(maxSessions) || maxSessions < minSessions) {
    ElMessage.warning(`并发录制数量不能小于 ${minSessions}`)
    return
  }
  if (capacity && maxSessions > capacity) {
    ElMessage.warning(`并发录制数量不能超过端口容量 ${capacity}`)
    return
  }

  settingsSaving.value = true
  try {
    const response = await updatePlaywrightRecordingSettings({ max_sessions: maxSessions })
    applyRecorderSettings(response.data || {})
    syncSettingsForm()
    settingsDialogVisible.value = false
    ElMessage.success('并发数设置已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存并发设置失败')
  } finally {
    settingsSaving.value = false
  }
}

const getStatusLabel = status => {
  const labels = {
    starting: '启动中',
    recording: '录制中',
    stopping: '停止中',
    completed: '已完成',
    failed: '失败'
  }
  return labels[status] || status || '-'
}

const getStatusType = status => {
  const types = {
    starting: 'warning',
    recording: 'success',
    stopping: 'warning',
    completed: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getRecordingMethodLabel = session => {
  const method = typeof session === 'string' ? session : session?.recording_method
  const labels = {
    [RECORDING_METHOD_SERVER]: '服务端Playwright CLI录制',
    [RECORDING_METHOD_LOCAL_AGENT]: '本地Agent-Playwright录制'
  }
  return session?.recording_method_label || labels[method] || method || '-'
}

const getRecordingMethodTagType = method => {
  if (method === RECORDING_METHOD_LOCAL_AGENT) return 'primary'
  return 'info'
}

const getActionLabel = action => {
  const labels = {
    click: '点击',
    fill: '输入',
    select: '选择',
    check: '勾选',
    uncheck: '取消勾选',
    press: '按键'
  }
  return labels[action] || action || '-'
}

const stringify = value => JSON.stringify(value || [], null, 2)

const normalizeListResponse = payload => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const getUserDisplayName = user => {
  if (!user || typeof user !== 'object') return ''
  return user.full_name || user.name || user.username || user.email || ''
}

const normalizeModuleCategoryTree = (categories = [], parentPath = []) =>
  normalizeListResponse(categories).map(category => {
    const label = String(category?.name || '').trim()
    const currentPath = [...parentPath, label].filter(Boolean)
    return {
      id: category?.id,
      label,
      fullPath: currentPath.join(' / '),
      children: normalizeModuleCategoryTree(category?.children || [], currentPath)
    }
  })

const filterModuleTreeNode = (keyword, data) => {
  const normalizedKeyword = String(keyword || '').trim().toLowerCase()
  if (!normalizedKeyword) return true
  return [data?.label, data?.fullPath].some(value => String(value || '').toLowerCase().includes(normalizedKeyword))
}

const assignModuleFields = (target, source = {}) => {
  target.project_id = source.project_id || ''
  target.module_id = source.module_id || ''
  target.module_name = source.module_name || ''
  target.module_path = source.module_path || ''
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
  assignModuleFields(recordingForm, context || {})
  resetAndLoadRecordings()
}

const clearModuleSelection = target => assignModuleFields(target, { project_id: target.project_id || '' })

const applyModuleSelection = (target, node) => {
  if (!target || !node) return
  target.module_id = node.id || ''
  target.module_name = node.label || ''
  target.module_path = node.fullPath || node.label || ''
}

const handleRecordingDirectorySelect = node => {
  applyModuleSelection(recordingForm, node)
  resetAndLoadRecordings()
}

const getSessionModule = session => session?.module || session?.metadata?.module || {}

const getSessionModuleLabel = session => {
  const module = getSessionModule(session)
  return module?.module_path || module?.module_name || '-'
}

const buildModulePayload = form => ({
  project_id: form.project_id || null,
  version_id: researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : null,
  version_name: researchContext.value?.version_name || '',
  module_id: form.module_id || null,
  module_name: form.module_name || '',
  module_path: form.module_path || ''
})

const loadProjects = async () => {
  try {
    const response = await getProjectList()
    projects.value = normalizeListResponse(response.data)
    if (!recordingForm.project_id && projects.value.length) {
      recordingForm.project_id = projects.value[0].id
    }
  } catch (error) {
    projects.value = []
  }
}

const loadModuleCategories = async projectId => {
  const effectiveProjectId = projectId || projects.value[0]?.id
  if (!effectiveProjectId) {
    moduleCategoryTree.value = []
    return
  }

  moduleCategoryLoading.value = true
  try {
    const response = await getManualCategories({ project: effectiveProjectId })
    moduleCategoryTree.value = normalizeModuleCategoryTree(normalizeListResponse(response.data))
  } catch (error) {
    moduleCategoryTree.value = []
    ElMessage.error('加载模块目录失败')
  } finally {
    moduleCategoryLoading.value = false
  }
}

const handleRecordingProjectChange = async projectId => {
  assignModuleFields(recordingForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
  resetAndLoadRecordings()
}

const handleRecordingEditProjectChange = async projectId => {
  assignModuleFields(recordingEditForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
}

const handleSnapshotProjectChange = async projectId => {
  assignModuleFields(snapshotForm, { project_id: projectId || '' })
  await loadModuleCategories(projectId)
}

const getElementLabel = element => {
  if (!element || typeof element !== 'object') return '-'
  if (element.tag === 'select') {
    const selected = Array.isArray(element.value) ? element.value[0] : element.value
    return element.text || element.placeholder || element.name || selected || element.ariaLabel || element.tag || '-'
  }
  return element.text || element.placeholder || element.name || element.id || element.ariaLabel || element.tag || '-'
}

const getActionValue = row => {
  const rawEvent = row?.raw_event || {}
  const action = String(row?.action_type || '').toLowerCase()
  if (Array.isArray(rawEvent.selectedOptions) && rawEvent.selectedOptions.length) {
    return rawEvent.selectedOptions.map(option => option.label || option.text || option.value).filter(Boolean).join(', ')
  }
  if (rawEvent.selectedValue) return rawEvent.selectedValue
  if (['check', 'uncheck'].includes(action)) {
    const checked = rawEvent.checked ?? row?.element?.checked ?? row?.action_value
    return checked === true || checked === 'true' ? '已勾选' : '未勾选'
  }
  if (action === 'select' && (rawEvent.controlType === 'radio' || row?.element?.type === 'radio' || row?.element?.role === 'radio')) {
    return rawEvent.checked === false || row?.action_value === 'false' ? '未选中' : '已选中'
  }
  if (row?.action_value) {
    try {
      const parsed = JSON.parse(row.action_value)
      if (Array.isArray(parsed)) return parsed.join(', ')
      if (parsed && typeof parsed === 'object') return JSON.stringify(parsed)
    } catch (error) {
      return row.action_value
    }
    return row.action_value
  }
  return ''
}

const LOCATOR_DEFINITIONS = [
  { type: 'id', label: 'ID', selectorTypes: ['by_id'] },
  { type: 'name', label: 'Name', selectorTypes: ['by_name'] },
  { type: 'classname', label: 'ClassName', selectorTypes: ['by_classname'] },
  { type: 'tagname', label: 'TagName', selectorTypes: ['by_tagname'] },
  { type: 'linktext', label: 'LinkText', selectorTypes: ['by_linktext'] },
  { type: 'partiallinktext', label: 'PartialLinkText', selectorTypes: ['by_partiallinktext'] },
  { type: 'xpath', label: 'XPath', selectorTypes: ['by_xpath'] },
  { type: 'cssselector', label: 'CssSelector', selectorTypes: ['by_cssselector', 'css'] }
]

const normalizeLocatorValue = value => {
  if (Array.isArray(value)) return value.filter(Boolean).join(' ')
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

const getSelectorValueByTypes = (selectors, types) => {
  const matched = selectors.find(selector => selector && types.includes(selector.type) && selector.value)
  return normalizeLocatorValue(matched?.value)
}

const getElementLocatorValues = row => {
  const element = row?.element && typeof row.element === 'object' ? row.element : {}
  const locators = element.locatorValues || element.locator_values || {}
  const selectors = Array.isArray(row?.selectors) ? row.selectors : []
  const className = normalizeLocatorValue(
    locators.classname ||
    element.classname ||
    (normalizeLocatorValue(element.className).split(/\s+/).find(Boolean) || '')
  )

  return {
    id: normalizeLocatorValue(locators.id || element.id || getSelectorValueByTypes(selectors, ['by_id'])),
    name: normalizeLocatorValue(locators.name || element.name || getSelectorValueByTypes(selectors, ['by_name'])),
    classname: className || getSelectorValueByTypes(selectors, ['by_classname']),
    tagname: normalizeLocatorValue(locators.tagname || element.tagname || element.tagName || element.tag || getSelectorValueByTypes(selectors, ['by_tagname'])),
    linktext: normalizeLocatorValue(locators.linktext || element.linktext || element.linkText || getSelectorValueByTypes(selectors, ['by_linktext'])),
    partiallinktext: normalizeLocatorValue(locators.partiallinktext || element.partiallinktext || element.partialLinkText || getSelectorValueByTypes(selectors, ['by_partiallinktext'])),
    xpath: normalizeLocatorValue(locators.xpath || element.xpath || getSelectorValueByTypes(selectors, ['by_xpath'])),
    cssselector: normalizeLocatorValue(locators.cssselector || element.cssselector || element.cssSelector || getSelectorValueByTypes(selectors, ['by_cssselector', 'css']))
  }
}

const getLocatorRows = row => {
  const values = getElementLocatorValues(row)
  return LOCATOR_DEFINITIONS
    .map(item => ({
      ...item,
      value: normalizeLocatorValue(values[item.type])
    }))
    .filter(item => item.value)
}

const getDisplaySelectors = row => {
  const selectors = Array.isArray(row?.selectors) ? row.selectors : []
  const selectedValue = getActionValue(row)
  if (!selectedValue || row?.action_type !== 'select') return selectors
  return selectors.map(selector => {
    if (!selector || typeof selector !== 'object') return selector
    if (selector.type !== 'role' || !String(selector.value || '').includes('role=combobox')) {
      return selector
    }
    return {
      ...selector,
      value: String(selector.value || '').replace(/name="[^"]*"/, `name="${selectedValue.replace(/"/g, '\\"')}"`)
    }
  })
}

const getStepSnapshotFilename = row => {
  if (!row) return ''
  if (row.snapshot_filename) return row.snapshot_filename
  if (row.resolved_snapshot_filename) return row.resolved_snapshot_filename
  if (row.raw_event?.snapshot_filename) return row.raw_event.snapshot_filename
  const sessionId = selectedSession.value?.session_id
  if (sessionId && row.step_number) {
    return `recording-${sessionId}-step-${String(row.step_number).padStart(4, '0')}.yml`
  }
  return ''
}

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

const getRecordingBrowserUrl = session => {
  const metadata = session?.metadata || {}
  return metadata.browser_url || metadata.devtools_url || ''
}

const writeBrowserPlaceholder = browserWindow => {
  if (!browserWindow || browserWindow.closed) return
  try {
    browserWindow.document.title = '受控浏览器启动中'
    browserWindow.document.body.innerHTML = '<div style="font-family: sans-serif; padding: 24px;">受控浏览器启动中，请稍候...</div>'
  } catch (error) {
    // The blank window can fail to write in some browser privacy modes.
  }
}

const navigateBrowserWindow = (url, browserWindow = null) => {
  if (!url) return false
  try {
    if (browserWindow && !browserWindow.closed) {
      browserWindow.location.href = url
      browserWindow.focus()
      return true
    }
    const opened = window.open(url, '_blank', 'noopener,noreferrer')
    if (opened) {
      opened.focus()
      return true
    }
  } catch (error) {
    return false
  }
  return false
}

const openRecordingBrowser = (session, options = {}) => {
  const url = getRecordingBrowserUrl(session)
  if (!url) {
    if (!options.silent) {
      ElMessage.warning('受控浏览器还未就绪')
    }
    return false
  }

  const opened = navigateBrowserWindow(url, options.browserWindow)
  if (opened) {
    if (session?.session_id) {
      openedBrowserSessionIds.add(session.session_id)
    }
    if (!options.silent) {
      ElMessage.success('受控浏览器已打开')
    }
  } else if (!options.silent) {
    ElMessage.warning('浏览器拦截了新窗口，请点击“打开受控浏览器”')
  }
  return opened
}

const waitForRecordingBrowser = async (sessionId, browserWindow = null) => {
  if (!sessionId) return false
  for (let index = 0; index < 24; index += 1) {
    const response = await getPlaywrightRecordingDetail(sessionId)
    const session = response.data
    if (selectedSession.value?.session_id === sessionId) {
      selectedSession.value = session
    }

    if (session?.status === 'failed') {
      if (browserWindow && !browserWindow.closed) {
        browserWindow.close()
      }
      ElMessage.error(session.error_message || '受控浏览器启动失败')
      return false
    }

    if (getRecordingBrowserUrl(session)) {
      return openRecordingBrowser(session, { browserWindow, silent: true })
    }

    await new Promise(resolve => window.setTimeout(resolve, 500))
  }

  if (browserWindow && !browserWindow.closed) {
    browserWindow.close()
  }
  ElMessage.warning('受控浏览器仍在启动，请稍后在详情中点击“打开受控浏览器”')
  return false
}

const loadRecordings = async ({ silent = false } = {}) => {
  if (!silent) loading.value = true
  try {
    const response = await getPlaywrightRecordings({
      keyword: filters.keyword.trim(),
      status: filters.status || undefined,
      module_id: recordingForm.module_id || undefined,
      module_path: recordingForm.module_path || undefined,
      module_name: recordingForm.module_name || undefined,
      project_id: recordingForm.project_id || undefined,
      version_id: researchContext.value?.version_id && researchContext.value.version_id !== 'all' ? researchContext.value.version_id : undefined,
      include_descendants: true,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    const results = response.data?.results || []
    recordings.value = results
    activeSessionIds.value = response.data?.active_session_ids || []
    pagination.total = response.data?.count ?? results.length
    if (response.data?.recorder_settings) {
      applyRecorderSettings(response.data.recorder_settings)
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error('加载录制结果失败')
    }
  } finally {
    loading.value = false
  }
}

const openStartDialog = () => {
  startRecordingMethod.value = RECORDING_METHOD_SERVER
  startDialogVisible.value = true
  if (!recordingForm.name) {
    recordingForm.name = `录制 ${new Date().toLocaleString()}`
  }
  if (!projects.value.length) {
    loadProjects().then(() => loadModuleCategories(recordingForm.project_id))
  } else if (!moduleCategoryTree.value.length) {
    loadModuleCategories(recordingForm.project_id)
  }
}

const openLocalAgentStartDialog = () => {
  startRecordingMethod.value = RECORDING_METHOD_LOCAL_AGENT
  startDialogVisible.value = true
  if (!recordingForm.name) {
    recordingForm.name = `本地录制 ${new Date().toLocaleString()}`
  }
  if (!projects.value.length) {
    loadProjects().then(() => loadModuleCategories(recordingForm.project_id))
  } else if (!moduleCategoryTree.value.length) {
    loadModuleCategories(recordingForm.project_id)
  }
}

const syncLocalAgentInfo = (session, agent = {}) => {
  const metadata = session?.metadata || {}
  localAgentInfo.session_id = session?.session_id || ''
  localAgentInfo.pairing_url = buildBrowserReachablePairingUrl(
    session?.session_id,
    agent.pairing_url || metadata.local_agent_pairing_url || ''
  )
  localAgentInfo.api_origin = agent.api_origin || metadata.local_agent_api_origin || ''
  localAgentInfo.token = agent.token || ''
  localAgentInfo.expires_at = agent.expires_at || metadata.local_agent_token_expires_at_iso || ''
  localAgentInfo.launch_status = 'idle'
  localAgentInfo.launch_error = ''
}

const buildBrowserReachablePairingUrl = (sessionId, fallbackUrl = '') => {
  const path = sessionId
    ? `/api/testcases/playwright-recordings/${encodeURIComponent(sessionId)}/agent/`
    : ''
  if (window.location?.origin && path) {
    return `${window.location.origin}${path}`
  }
  return fallbackUrl
}

const showLocalAgentGuide = session => {
  syncLocalAgentInfo(session)
  localAgentDialogVisible.value = true
  detectLocalAgent({ silent: true })
}

const openLocalAgentManager = () => {
  localAgentDialogVisible.value = true
  detectLocalAgent({ silent: true })
}

const resetLocalAgentRuntime = () => {
  Object.assign(localAgentRuntime, {
    version: '',
    pid: '',
    started_at: '',
    uptime_seconds: 0,
    platform: '',
    python: '',
    sessions: []
  })
}

const applyLocalAgentHealthPayload = payload => {
  Object.assign(localAgentRuntime, {
    version: payload?.version || '',
    pid: payload?.pid || '',
    started_at: payload?.started_at || '',
    uptime_seconds: Number(payload?.uptime_seconds || 0),
    platform: payload?.platform || '',
    python: payload?.python || '',
    sessions: Array.isArray(payload?.sessions) ? payload.sessions : []
  })
  localAgentState.status = 'available'
  localAgentState.error = ''
  localAgentState.last_checked_at = new Date().toISOString()
  localAgentLastCheckedAt = Date.now()
}

const LOCAL_AGENT_UNREACHABLE_MESSAGE = '本地 Agent 服务未连接。若已安装，可点击“启动 Agent”；若未安装，请下载本地 Agent 安装包完成安装。'

const normalizeLocalAgentError = error => {
  const message = error?.message || ''
  if (!message || message === 'Failed to fetch' || message.includes('NetworkError')) {
    return LOCAL_AGENT_UNREACHABLE_MESSAGE
  }
  return message
}

const fetchWithTimeout = async (url, options = {}, timeoutMs = 45000) => {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    })
  } finally {
    window.clearTimeout(timer)
  }
}

const detectLocalAgent = async (options = {}) => {
  if (localAgentState.checking) return localAgentState.status === 'available'
  localAgentState.checking = true
  localAgentState.status = localAgentState.status === 'available' ? 'available' : 'checking'
  try {
    const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/health`, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store'
    }, 5000)
    if (!response.ok) {
      throw new Error(`本地 Agent 服务健康检查失败：HTTP ${response.status}`)
    }
    const payload = await response.json().catch(() => ({}))
    if (payload?.service !== 'testhub-local-playwright-agent') {
      throw new Error('本地端口响应不是 BearAI Local Agent')
    }
    applyLocalAgentHealthPayload(payload)
    if (!options.silent) {
      ElMessage.success('本地 Agent 可用')
    }
    return true
  } catch (error) {
    resetLocalAgentRuntime()
    localAgentState.status = 'unavailable'
    localAgentState.error = normalizeLocalAgentError(error)
    localAgentState.last_checked_at = new Date().toISOString()
    localAgentLastCheckedAt = Date.now()
    if (!options.silent) {
      ElMessage.warning(localAgentState.error)
    }
    return false
  } finally {
    localAgentState.checking = false
  }
}

const waitForLocalAgentReady = async (timeoutMs = 18000) => {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await detectLocalAgent({ silent: true })) {
      return true
    }
    await new Promise(resolve => window.setTimeout(resolve, 1200))
  }
  return false
}

const invokeLocalAgentProtocol = action => {
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = `${LOCAL_AGENT_PROTOCOL}${action}`
  document.body.appendChild(iframe)
  window.setTimeout(() => {
    if (iframe.parentNode) {
      iframe.parentNode.removeChild(iframe)
    }
  }, 1500)
}

const downloadBlobFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const buildLocalAgentPackageBlob = response => (
  response.data instanceof Blob
    ? response.data
    : new Blob([response.data], { type: response.data?.type || 'application/zip' })
)

const startInstalledLocalAgent = async (options = {}) => {
  if (await detectLocalAgent({ silent: true })) {
    if (!options.silent) ElMessage.success('本地 Agent 已可用')
    return true
  }
  localAgentState.starting = true
  localAgentState.status = 'starting'
  localAgentState.error = ''
  try {
    invokeLocalAgentProtocol('start')
    const ready = await waitForLocalAgentReady(options.timeoutMs || 18000)
    if (!ready) {
      localAgentState.status = 'unavailable'
      localAgentState.error = '未能唤起本地 Agent。若未安装，请先下载安装包；若浏览器弹出协议确认，请允许打开。'
      if (!options.silent) ElMessage.warning(localAgentState.error)
      return false
    }
    if (!options.silent) ElMessage.success('本地 Agent 已启动')
    return true
  } finally {
    localAgentState.starting = false
  }
}

const restartInstalledLocalAgent = async () => {
  localAgentState.restarting = true
  localAgentState.status = 'starting'
  localAgentState.error = ''
  try {
    invokeLocalAgentProtocol('restart')
    const ready = await waitForLocalAgentReady(22000)
    if (!ready) {
      localAgentState.status = 'unavailable'
      localAgentState.error = '重启后未检测到本地 Agent，请确认本机已安装 Agent。'
      ElMessage.warning(localAgentState.error)
      return false
    }
    ElMessage.success('本地 Agent 已重启')
    return true
  } finally {
    localAgentState.restarting = false
  }
}

const stopInstalledLocalAgent = async () => {
  localAgentState.stopping = true
  localAgentState.error = ''
  try {
    try {
      const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/shutdown`, {
        method: 'POST',
        mode: 'cors',
        cache: 'no-store'
      }, 5000)
      if (!response.ok) {
        throw new Error(`本地 Agent 停止请求失败：HTTP ${response.status}`)
      }
    } catch (error) {
      invokeLocalAgentProtocol('stop')
    }
    await new Promise(resolve => window.setTimeout(resolve, 3000))
    const available = await detectLocalAgent({ silent: true })
    if (available) {
      localAgentState.error = '已发送停止请求，但仍检测到 Agent 运行，请稍后重试或手动停止。'
      ElMessage.warning(localAgentState.error)
      return false
    }
    localAgentState.status = 'unavailable'
    localAgentState.error = '本地 Agent 已停止'
    resetLocalAgentRuntime()
    ElMessage.success('本地 Agent 已停止')
    return true
  } finally {
    localAgentState.stopping = false
  }
}

const downloadLocalAgentInstaller = async () => {
  localAgentState.downloading = true
  try {
    const response = await downloadLocalAgentPackage()
    downloadBlobFile(buildLocalAgentPackageBlob(response), 'testhub-local-agent.zip')
    localAgentState.install_watch = true
    localAgentState.error = '安装包已下载。请解压后双击 install.bat，安装器会自动补齐运行环境；若检测到下载源超时或连接失败，会切换国内镜像并重试。'
    ElMessageBox.alert(
      '安装包已下载。请在 Windows 下载目录中解压 testhub-local-agent.zip，然后双击 install.bat。安装器会自动检查 Python、pip、requests、Playwright 和 Chromium，缺失或版本过低时自动安装/升级；若检测到 Python、PyPI 或 Playwright 下载源超时、连接失败、域名解析失败，会自动切换国内镜像并重试；完成后本页面会自动检测本地 Agent。',
      '本地 Agent 首次安装',
      { type: 'info', confirmButtonText: '知道了' }
    ).catch(() => {})
    const ready = await waitForLocalAgentReady(120000)
    if (ready) {
      localAgentState.install_watch = false
      ElMessage.success('本地 Agent 已安装并连接')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '下载本地 Agent 安装包失败')
  } finally {
    localAgentState.downloading = false
  }
}

const updateInstalledLocalAgent = async () => {
  localAgentState.updating = true
  localAgentState.error = ''
  try {
    if (!(await detectLocalAgent({ silent: true }))) {
      ElMessage.warning('未检测到已安装的本地 Agent，请先下载安装器完成首次安装')
      return false
    }

    const response = await downloadLocalAgentPackage()
    const blob = buildLocalAgentPackageBlob(response)
    const updateResponse = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/update`, {
      method: 'POST',
      mode: 'cors',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/zip',
        'X-TestHub-Platform-Url': window.location.origin
      },
      body: blob
    }, 45000)
    const payload = await updateResponse.json().catch(() => ({}))
    if (!updateResponse.ok) {
      throw new Error(payload.error || `本地 Agent 升级失败：HTTP ${updateResponse.status}`)
    }

    localAgentState.status = 'starting'
    localAgentState.error = '本地 Agent 已更新，正在检查并升级本机依赖环境，请稍候。'
    ElMessage.success('本地 Agent 已更新，正在检查依赖并等待服务重启')
    const ready = await waitForLocalAgentReady(300000)
    if (!ready) {
      localAgentState.status = 'unavailable'
      localAgentState.error = 'Agent 已更新，但依赖检查/重启尚未完成。请点击“启动 Agent”继续检测，或手动运行安装目录中的 install.bat。'
      ElMessage.warning(localAgentState.error)
      return false
    }
    ElMessage.success('本地 Agent 已升级并重新连接')
    return true
  } catch (error) {
    localAgentState.error = normalizeLocalAgentError(error)
    ElMessage.warning(localAgentState.error)
    return false
  } finally {
    localAgentState.updating = false
  }
}

const uninstallLocalAgent = async () => {
  try {
    await ElMessageBox.confirm('确定卸载本地 Agent 吗？卸载后客户端录制和客户端执行测试将不可用。', '提示', { type: 'warning' })
  } catch (error) {
    return false
  }

  localAgentState.uninstalling = true
  try {
    invokeLocalAgentProtocol('uninstall')
    await new Promise(resolve => window.setTimeout(resolve, 3000))
    const available = await detectLocalAgent({ silent: true })
    if (available) {
      localAgentState.error = '已发送卸载请求，但仍检测到 Agent 运行，请确认系统卸载提示。'
      ElMessage.warning(localAgentState.error)
      return false
    }
    localAgentState.status = 'unavailable'
    localAgentState.error = '本地 Agent 未运行或已卸载'
    ElMessage.success('已发送本地 Agent 卸载请求')
    return true
  } finally {
    localAgentState.uninstalling = false
  }
}

const ensureLocalAgentServiceReady = async () => {
  if (Date.now() - localAgentLastCheckedAt < 3000 && localAgentState.status === 'available') {
    return true
  }
  if (await detectLocalAgent({ silent: true })) {
    return true
  }
  const started = await startInstalledLocalAgent({ silent: true, timeoutMs: 16000 })
  if (!started) {
    throw new Error(localAgentState.error || LOCAL_AGENT_UNREACHABLE_MESSAGE)
  }
  return true
}

const startLocalAgentBrowser = async () => {
  if (!localAgentInfo.pairing_url || !localAgentInfo.token) {
    localAgentInfo.launch_status = 'failed'
    localAgentInfo.launch_error = '本地 Agent 配对信息不完整'
    return false
  }

  localAgentInfo.launch_status = 'starting'
  localAgentInfo.launch_error = ''
  try {
    await ensureLocalAgentServiceReady()
    const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/recordings/start`, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pairing_url: localAgentInfo.pairing_url,
        token: localAgentInfo.token,
        browser: recordingForm.browser_type
      })
    }, 45000)
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(payload.error || '本地 Agent 服务启动浏览器失败')
    }
    localAgentInfo.launch_status = payload.recording?.status || 'starting'
    localAgentInfo.launch_error = payload.recording?.error || ''
    if (localAgentInfo.launch_status === 'failed') {
      throw new Error(localAgentInfo.launch_error || '本地 Agent 服务启动浏览器失败')
    }
    if (localAgentInfo.launch_status !== 'recording') {
      throw new Error('本地 Agent 尚未完成配对，请检查平台访问地址是否可从本机访问')
    }
    ElMessage.success('本地浏览器已启动')
    return true
  } catch (error) {
    localAgentInfo.launch_status = 'failed'
    localAgentInfo.launch_error = normalizeLocalAgentError(error)
    ElMessage.warning(localAgentInfo.launch_error)
    return false
  }
}

const startRecording = async () => {
  const targetUrl = recordingForm.target_url.trim()
  if (!targetUrl) {
    ElMessage.warning('请输入目标系统地址')
    return
  }
  if (!/^https?:\/\//i.test(targetUrl)) {
    ElMessage.warning('目标系统地址需要以 http:// 或 https:// 开头')
    return
  }
  if (!recordingForm.module_path && !recordingForm.module_name && !recordingForm.module_id) {
    ElMessage.warning('请先选择左侧目录树中的页面菜单节点')
    return
  }

  recordingStarting.value = true
  let browserWindow = null
  if (startRecordingMethod.value === RECORDING_METHOD_SERVER) {
    try {
      browserWindow = window.open('', '_blank')
      writeBrowserPlaceholder(browserWindow)
    } catch (error) {
      browserWindow = null
    }
  }
  try {
    const response = await startPlaywrightRecording({
      name: recordingForm.name.trim(),
      target_url: targetUrl,
      browser_type: recordingForm.browser_type,
      recording_method: startRecordingMethod.value,
      ...buildModulePayload(recordingForm)
    })
    const session = response.data?.session
    startDialogVisible.value = false
    if (startRecordingMethod.value === RECORDING_METHOD_LOCAL_AGENT) {
      syncLocalAgentInfo(session, response.data?.agent || {})
      localAgentDialogVisible.value = true
      ElMessage.success('本地Agent-Playwright录制会话已创建')
      await startLocalAgentBrowser()
      await loadRecordings({ silent: true })
      if (session?.session_id) {
        router.replace({ query: { ...route.query, session_id: session.session_id } })
      }
      if (browserWindow && !browserWindow.closed) {
        browserWindow.close()
      }
      return
    }
    ElMessage.success('服务端Playwright CLI录制已启动')
    await loadRecordings({ silent: true })
    if (session?.session_id) {
      router.replace({ query: { ...route.query, session_id: session.session_id } })
      await openDetail(session.session_id)
      if (!openRecordingBrowser(selectedSession.value || session, { browserWindow, silent: true })) {
        await waitForRecordingBrowser(session.session_id, browserWindow)
      }
    }
  } catch (error) {
    if (browserWindow && !browserWindow.closed) {
      browserWindow.close()
    }
    ElMessage.error(error.response?.data?.error || '启动录制失败')
  } finally {
    recordingStarting.value = false
  }
}

const openRecordingEdit = async session => {
  if (!session?.session_id) return
  recordingEditForm.session_id = session.session_id
  recordingEditForm.name = session.name || ''
  assignModuleFields(recordingEditForm, getSessionModule(session))
  if (!recordingEditForm.project_id && projects.value.length) {
    recordingEditForm.project_id = projects.value[0].id
  }
  recordingEditDialogVisible.value = true
  if (!projects.value.length) {
    await loadProjects()
  }
  await loadModuleCategories(recordingEditForm.project_id)
}

const saveRecordingEdit = async () => {
  if (!recordingEditForm.session_id) return
  const name = recordingEditForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入录制名称')
    return
  }

  savingRecording.value = true
  try {
    const response = await updatePlaywrightRecording(recordingEditForm.session_id, {
      name,
      ...buildModulePayload(recordingEditForm)
    })
    const savedSession = response.data
    if (selectedSession.value?.session_id === savedSession.session_id) {
      selectedSession.value = savedSession
    }
    await loadRecordings({ silent: true })
    recordingEditDialogVisible.value = false
    ElMessage.success('录制信息已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存录制信息失败')
  } finally {
    savingRecording.value = false
  }
}

const openDetail = async sessionId => {
  if (!sessionId) return
  drawerVisible.value = true
  detailLoading.value = true
  clearStepSelection()
  junkStepMap.value = {}
  try {
    const response = await getPlaywrightRecordingDetail(sessionId)
    selectedSession.value = response.data
  } catch (error) {
    drawerVisible.value = false
    ElMessage.error(error.response?.data?.error || '加载录制详情失败')
  } finally {
    detailLoading.value = false
  }
}

const refreshSelectedSession = async () => {
  if (!selectedSession.value?.session_id) return
  try {
    const response = await getPlaywrightRecordingDetail(selectedSession.value.session_id)
    selectedSession.value = response.data
    if (Object.keys(junkStepMap.value).length) {
      setTimeout(selectJunkStepRows, 0)
    }
  } catch (error) {
    // Polling errors are ignored; manual refresh still reports failures.
  }
}

const handleStepSelectionChange = rows => {
  selectedStepRows.value = rows || []
}

const getStepRowClassName = ({ row }) => {
  return row?.id && junkStepMap.value[row.id] ? 'junk-step-row' : ''
}

const clearStepSelection = () => {
  selectedStepRows.value = []
  if (recordingStepTableRef.value?.clearSelection) {
    recordingStepTableRef.value.clearSelection()
  }
}

const selectJunkStepRows = () => {
  if (!recordingStepTableRef.value?.toggleRowSelection || !selectedSession.value?.steps?.length) return
  clearStepSelection()
  selectedSession.value.steps.forEach(row => {
    if (junkStepMap.value[row.id]) {
      recordingStepTableRef.value.toggleRowSelection(row, true)
    }
  })
}

const identifyJunkSteps = async () => {
  const sessionId = selectedSession.value?.session_id
  if (!sessionId) return

  identifyingJunkSteps.value = true
  try {
    const response = await identifyPlaywrightRecordingJunkSteps(sessionId)
    const junkSteps = response.data?.junk_steps || []
    junkStepMap.value = junkSteps.reduce((acc, item) => {
      acc[item.step_id] = item
      return acc
    }, {})
    await refreshSelectedSession()
    setTimeout(selectJunkStepRows, 0)
    ElMessage.success(response.data?.message || `已识别 ${junkSteps.length} 个疑似垃圾步骤`)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '识别垃圾步骤失败')
  } finally {
    identifyingJunkSteps.value = false
  }
}

const deleteSelectedSteps = async () => {
  const sessionId = selectedSession.value?.session_id
  const stepIds = [...selectedStepIds.value]
  if (!sessionId || !stepIds.length) return

  try {
    await ElMessageBox.confirm(`确定删除选中的 ${stepIds.length} 个录制步骤吗？`, '提示', { type: 'warning' })
    batchDeletingSteps.value = true
    const response = await batchDeletePlaywrightRecordingSteps(sessionId, stepIds)
    if (response.data?.session) {
      selectedSession.value = response.data.session
    } else {
      await refreshSelectedSession()
    }
    const deletedSet = new Set(stepIds)
    junkStepMap.value = Object.fromEntries(
      Object.entries(junkStepMap.value).filter(([stepId]) => !deletedSet.has(Number(stepId)))
    )
    clearStepSelection()
    await loadRecordings({ silent: true })
    ElMessage.success(response.data?.message || '录制步骤已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '批量删除录制步骤失败')
    }
  } finally {
    batchDeletingSteps.value = false
  }
}

const stopRecording = async sessionId => {
  if (!sessionId) return
  stoppingSessionId.value = sessionId
  try {
    const response = await stopPlaywrightRecording(sessionId)
    const flow = response.data?.flow
    ElMessage.success(flow?.flow_id ? '录制已停止，流程已自动创建' : (response.data?.message || '录制已停止'))
    await loadRecordings({ silent: true })
    if (selectedSession.value?.session_id === sessionId) {
      await refreshSelectedSession()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '停止录制失败')
  } finally {
    stoppingSessionId.value = ''
  }
}

const createFlow = async session => {
  const sessionId = session?.session_id
  if (!sessionId) return

  creatingFlowSessionId.value = sessionId
  try {
    const response = await createPlaywrightRecordingFlow(sessionId, {
      name: session?.name ? `${session.name} 自动流程` : '',
      force_new: false
    })
    const flow = response.data?.flow
    if (!flow?.flow_id) {
      throw new Error('流程ID为空')
    }
    ElMessage.success(response.data?.message || '流程已创建')
    router.push({
      path: '/manual-testcases/visual-flow',
      query: { flow_id: flow.flow_id }
    })
  } catch (error) {
    ElMessage.error(error.response?.data?.error || error.message || '创建流程失败')
  } finally {
    creatingFlowSessionId.value = ''
  }
}

const getRecordingFlowId = session => (
  session?.visual_flow_id ||
  session?.flow_id ||
  session?.flow?.flow_id ||
  session?.latest_flow?.flow_id ||
  ''
)

const openCreatedFlow = session => {
  const flowId = getRecordingFlowId(session)
  if (!flowId) return

  router.push({
    path: '/manual-testcases/visual-flow',
    query: { flow_id: flowId }
  })
}

const openLiveFlow = session => {
  const sessionId = session?.session_id
  if (!sessionId) return

  router.push({
    path: '/manual-testcases/visual-flow',
    query: { recording_session_id: sessionId }
  })
}

const normalizeReportUrl = url => {
  if (!url) return ''
  return String(url).startsWith('http') ? String(url) : String(url)
}

const getAllureReportUrl = session => {
  const report = session?.metadata?.allure_report || {}
  return normalizeReportUrl(report.summary_url || report.report_url || '')
}

const openAllureReport = session => {
  const reportUrl = getAllureReportUrl(session)
  if (!reportUrl) return
  window.open(reportUrl, '_blank', 'noopener')
}

const generateAllureReport = async session => {
  const sessionId = session?.session_id
  if (!sessionId) return

  generatingAllureSessionId.value = sessionId
  try {
    const response = await generatePlaywrightRecordingAllureReport(sessionId)
    const reportUrl = response.data?.summary_url || response.data?.report_url
    if (response.data?.session) {
      if (selectedSession.value?.session_id === sessionId) {
        selectedSession.value = response.data.session
      }
      const index = recordings.value.findIndex(item => item.session_id === sessionId)
      if (index >= 0) {
        recordings.value[index] = response.data.session
      }
    }
    await loadRecordings({ silent: true })
    ElMessage.success(response.data?.message || 'Allure报告已生成')
    if (reportUrl) {
      window.open(reportUrl, '_blank', 'noopener')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '生成Allure报告失败')
  } finally {
    generatingAllureSessionId.value = ''
  }
}

const deleteStep = async row => {
  const sessionId = selectedSession.value?.session_id
  if (!sessionId || !row?.id) return

  try {
    await ElMessageBox.confirm(`确定删除第 ${row.step_number} 步录制操作吗？`, '提示', { type: 'warning' })
    deletingStepId.value = row.id
    const response = await deletePlaywrightRecordingStep(sessionId, row.id)
    if (response.data?.session) {
      selectedSession.value = response.data.session
    } else {
      await refreshSelectedSession()
    }
    delete junkStepMap.value[row.id]
    clearStepSelection()
    await loadRecordings({ silent: true })
    ElMessage.success('录制步骤已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '删除录制步骤失败')
    }
  } finally {
    deletingStepId.value = null
  }
}

const syncSnapshotForm = payload => {
  snapshotForm.originalFilename = payload.filename || payload.originalFilename || ''
  snapshotForm.filename = payload.filename || ''
  snapshotForm.page_name = payload.page_name || ''
  snapshotForm.alias = payload.alias || ''
  snapshotForm.content = payload.content || ''
  assignModuleFields(snapshotForm, payload.module || payload)
}

const openSnapshotPreview = async row => {
  const filename = getStepSnapshotFilename(row)
  if (!filename) return

  snapshotDialogVisible.value = true
  snapshotLoading.value = true
  snapshotEditing.value = false
  try {
    const response = await getPlaywrightSnapshotContent(filename)
    syncSnapshotForm(response.data || {})
    if (!projects.value.length) {
      await loadProjects()
    }
    if (snapshotForm.project_id) {
      await loadModuleCategories(snapshotForm.project_id)
    }
  } catch (error) {
    snapshotDialogVisible.value = false
    ElMessage.error(error.response?.data?.error || '加载快照文件失败')
  } finally {
    snapshotLoading.value = false
  }
}

const saveSnapshotEdit = async () => {
  if (!snapshotForm.originalFilename) return
  snapshotSaving.value = true
  try {
    const response = await updatePlaywrightSnapshot(snapshotForm.originalFilename, {
      filename: snapshotForm.filename,
      page_name: snapshotForm.page_name,
      alias: snapshotForm.alias,
      content: snapshotForm.content,
      ...buildModulePayload(snapshotForm)
    })
    syncSnapshotForm(response.data || {})
    snapshotEditing.value = false
    await refreshSelectedSession()
    ElMessage.success('快照文件已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存快照文件失败')
  } finally {
    snapshotSaving.value = false
  }
}

const dedupeSnapshots = async session => {
  const sessionId = session?.session_id
  if (!sessionId) return

  dedupingSessionId.value = sessionId
  try {
    const response = await dedupePlaywrightRecordingSnapshots(sessionId)
    const summary = response.data?.summary || {}
    if (response.data?.session) {
      selectedSession.value = response.data.session
    } else if (selectedSession.value?.session_id === sessionId) {
      await refreshSelectedSession()
    }
    await loadRecordings({ silent: true })
    ElMessage.success(`快照文件去重完成，更新 ${summary.updated_step_count || 0} 个步骤，删除 ${summary.deleted_snapshot_count || 0} 个重复文件`)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '快照文件去重失败')
  } finally {
    dedupingSessionId.value = ''
  }
}

const deleteRecording = async sessionId => {
  try {
    await ElMessageBox.confirm('确定删除该录制会话及其步骤记录吗？', '提示', { type: 'warning' })
    await deletePlaywrightRecording(sessionId)
    if (selectedSession.value?.session_id === sessionId) {
      drawerVisible.value = false
      selectedSession.value = null
    }
    await loadRecordings({ silent: true })
    ElMessage.success('录制会话已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.error || '删除录制会话失败')
    }
  }
}

const showFlow = async (sessionOrId, options = {}) => {
  const session = typeof sessionOrId === 'object' ? sessionOrId : null
  const sessionId = session?.session_id || sessionOrId
  if (!sessionId) return

  const shouldSyncCreatedFlow = Boolean(options.syncCreatedFlow && getRecordingFlowId(session))
  generatingFlowSessionId.value = sessionId
  try {
    if (shouldSyncCreatedFlow) {
      await createPlaywrightRecordingFlow(sessionId, {
        name: session?.name ? `${session.name} 自动流程` : '',
        force_new: false
      })
      await loadRecordings({ silent: true })
      if (selectedSession.value?.session_id === sessionId) {
        await refreshSelectedSession()
      }
    }
    const response = await getPlaywrightRecordingFlow(sessionId)
    flowPreview.value = JSON.stringify(response.data?.flow || {}, null, 2)
    flowDialogVisible.value = true
    ElMessage.success(shouldSyncCreatedFlow ? '流程数据已重新生成' : '流程数据已生成')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '生成流程数据失败')
  } finally {
    generatingFlowSessionId.value = ''
  }
}

const copyText = async (text, message) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(message || '已复制')
  } catch (error) {
    ElMessage.warning('复制失败')
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    if (drawerVisible.value && selectedSession.value && isActiveStatus(selectedSession.value.status)) {
      await refreshSelectedSession()
    }
    if (hasActiveRecordings.value) {
      await loadRecordings({ silent: true })
    }
    if (Date.now() - localAgentLastCheckedAt > 15000) {
      await detectLocalAgent({ silent: true })
    }
  }, 2500)
}

const stopPolling = () => {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await loadProjects()
  if (recordingForm.project_id) {
    await loadModuleCategories(recordingForm.project_id)
  }
  await loadRecordings()
  const sessionId = route.query.session_id
  if (sessionId) {
    await openDetail(Array.isArray(sessionId) ? sessionId[0] : sessionId)
  }
  await detectLocalAgent({ silent: true })
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.recording-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f5f7fb;
  overflow: hidden;
}

.recording-workspace {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
}

.recording-directory-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}

.recording-directory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.recording-directory-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.recording-directory-project {
  width: 100%;
}

.recording-directory-tree {
  min-height: 0;
  flex: 1;
  overflow: auto;
  border: 1px solid #edf0f5;
  background: #fbfcfe;
}

.recording-directory-current {
  min-height: 34px;
  padding: 8px 10px;
  color: #3b82f6;
  font-size: 12px;
  line-height: 1.4;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.recording-main-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar-card,
.list-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.workspace-section-tabs {
  margin-bottom: 4px;
}

.toolbar,
.list-header,
.detail-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.toolbar-filters,
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-right: 4px;
}

.list-card {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-shell {
  flex: 1;
  min-height: 0;
}

.list-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.list-subtitle,
.row-subtext {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.list-header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.table-footer {
  flex-shrink: 0;
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.table-footer-text {
  color: #6b7280;
  font-size: 13px;
}

.settings-help {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-actions {
  justify-content: flex-start;
}

.description-action-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.agent-pairing-cell,
.agent-guide {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-status-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid #dbe4f0;
  background: #f8fafc;
}

.agent-status-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
}

.agent-status-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-install-steps {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.agent-install-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.5;
}

.agent-install-step__index {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.module-picker {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.module-picker-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.module-tree-box {
  max-height: 220px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  background: #fff;
}

.module-current {
  font-size: 12px;
  color: #6b7280;
}

.steps-table {
  margin-top: 4px;
}

.steps-table :deep(.junk-step-row) {
  --el-table-tr-bg-color: #fff7e6;
}

.steps-table :deep(.junk-step-row td) {
  background-color: #fff7e6 !important;
}

.element-cell {
  color: #1f2937;
  font-weight: 500;
}

.snapshot-file-link {
  max-width: 100%;
  white-space: normal;
  word-break: break-all;
  text-align: left;
}

.selector-popover {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.locator-values {
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
}

.locator-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.locator-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 8px;
  font-size: 12px;
}

.locator-label {
  color: #6b7280;
}

.locator-value {
  color: #111827;
  word-break: break-all;
}

.selector-actions {
  display: flex;
  justify-content: flex-end;
}

.json-preview,
.flow-preview {
  margin: 0;
  padding: 12px;
  max-height: 420px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #111827;
  color: #f9fafb;
  font-size: 12px;
  line-height: 1.55;
}

.flow-preview {
  min-height: 360px;
}

.snapshot-dialog-body {
  min-height: 360px;
}

.snapshot-preview {
  margin: 0;
  padding: 12px;
  max-height: 440px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #111827;
  color: #f9fafb;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.el-card__body) {
  padding: 12px 14px;
}

:deep(.list-card .el-card__body) {
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
