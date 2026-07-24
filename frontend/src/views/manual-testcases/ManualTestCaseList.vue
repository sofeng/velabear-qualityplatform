<template>
  <div
    class="manual-testcase-list manual-workspace-density-scope"
    :class="{
      'manual-testcase-list--allow-page-scroll': NOTIFICATION_TABS.has(activeTab),
      'manual-testcase-list--with-directory': showDirectoryPanel,
      'manual-testcase-list--directory-collapsed': showDirectoryPanel && isDirectoryCollapsed
    }"
  >
    <div class="workspace-toolbar-panel">
      <el-card shadow="never">
        <ManualWorkspaceSectionTabs
          :items="visibleWorkspaceSectionTabs"
          :active-name="activeTab"
          :show-context="!showKnowledgeAssistantContextMenu"
          @select="handleWorkspaceSectionSelect"
        >
          <template #context>
            <ManualWorkspaceContextToolbar
              :project-id="currentProjectId"
              :projects="workspaceProjects"
              :selected-project="selectedWorkspaceProject"
              :project-select-style="workspaceProjectSelectStyle"
              :version-id="currentVersionId"
              :versions="versionList"
              :version-select-style="workspaceVersionSelectStyle"
              :version-disabled="!currentProjectId"
              :can-set-default-project="canSetDefaultWorkspaceProject"
              :default-project-loading="workspaceProjectDefaultLoading"
              @select-project="handleWorkspaceProjectSelection"
              @select-version="handleWorkspaceVersionSelection"
              @set-default-project="handleSetCurrentProjectDefault"
              @manage-versions="handleManageVersions"
            />
          </template>
          <template #summary>
            <div v-if="showResearchProgressSummary" class="research-progress-toolbar-summary">
              <div
                v-for="item in researchProgressToolbarSummaryItems"
                :key="item.key"
                class="research-progress-toolbar-summary__group"
              >
                <span class="research-progress-toolbar-summary__label">{{ item.label }}</span>
                <el-tag type="info" size="small">总数:{{ item.total }}</el-tag>
                <div class="research-progress-toolbar-summary__tags">
                  <el-tag
                    v-for="tag in item.tags"
                    :key="`${item.key}-${tag.key}`"
                    :type="tag.type"
                    size="small"
                  >
                    {{ tag.label }}:{{ tag.count }}
                  </el-tag>
                </div>
              </div>
            </div>
            <div v-else-if="showQualityLiveToolbar" class="quality-live-toolbar-summary">
              <div v-if="qualityLiveToolbarState.scopeItems.length" class="quality-live-toolbar-summary__meta">
                <span
                  v-for="item in qualityLiveToolbarState.scopeItems"
                  :key="item.key"
                  class="quality-live-toolbar-summary__chip"
                >
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </span>
              </div>
              <div class="quality-live-toolbar-summary__actions">
                <el-button
                  :disabled="!qualityLiveToolbarState.canShare || qualityLiveToolbarState.loading"
                  @click="handleQualityLiveShare"
                >
                  复制分享链接
                </el-button>
                <el-button
                  type="primary"
                  :icon="Refresh"
                  :loading="qualityLiveToolbarState.loading"
                  :disabled="!qualityLiveToolbarState.canRefresh"
                  @click="handleQualityLiveRefresh"
                >
                  刷新
                </el-button>
              </div>
            </div>
          </template>
        </ManualWorkspaceSectionTabs>
      </el-card>
    </div>

    <div class="workspace-content-shell">
      <!-- 左侧目录树 -->
      <ManualWorkspaceDirectoryPanel
        v-if="showDirectoryPanel"
        ref="treeRef"
        :collapsed="isDirectoryCollapsed"
        :show-category-tree="showCategoryTree"
        :title="showCategoryTree ? '目录树' : '联动说明'"
        :rail-label="showCategoryTree ? '目录树' : '联动'"
        :hint="versionLinkedHint"
        v-model:filter-text="treeSearchText"
        :category-tree="categoryTree"
        :tree-props="treeProps"
        :expanded-category-keys="expandedCategoryKeys"
        :current-category="currentCategory"
        :category-importing="categoryImporting"
        :filter-node-method="filterNode"
        @toggle="toggleDirectoryCollapsed"
        @add-category="handleAddCategory"
        @node-click="handleNodeClick"
        @node-contextmenu="handleNodeContextmenu"
        @edit-category="handleEditCategory"
        @delete-category="handleDeleteCategory"
        @import-xmind="handleCategoryXMindImport"
      />

      <!-- 右侧内容区 -->
      <div class="right-panel">
        <el-card>
          <div class="workspace-tab-shell">
            <el-tabs v-model="activeTab" class="mindmap-tabs mindmap-tabs--header-hidden" @tab-change="handleTabChange">
            <el-tab-pane v-if="isPrimaryTabVisible('mindmaps')" label="测试脑图" name="mindmaps">
            <div class="tab-panel">
              <div class="tab-toolbar">
                <ManualConfiguredFilterForm
                  v-model="mindmapConfiguredFilters"
                  storage-key="manual-testcases.mindmaps"
                  class="mindmap-search-form"
                  :fallback-conditions="mindmapFallbackFilterConditions"
                  :fallback-fields-registry="mindmapFallbackFieldsRegistry"
                  :filter-option-map="mindmapFilterOptionMap"
                  @search="handleSearch"
                  @reset="handleReset"
                />
                <div class="tab-toolbar-actions">
                  <TableColumnSettings
                    :table-ref="mindmapTableRef"
                    storage-key="manual-testcases.mindmaps"
                  />
                  <el-button
                    type="danger"
                    plain
                    :disabled="!mindmapSelectedRows.length"
                    @click="handleBatchDeleteMindmaps"
                  >
                    <el-icon><Delete /></el-icon>
                    批量删除
                  </el-button>
                  <el-button type="primary" @click="handleCreate">
                    <el-icon><Plus /></el-icon>
                    新建脑图
                  </el-button>
                </div>
              </div>

              <el-table
                ref="mindmapTableRef"
                :data="mindmapTableData"
                stripe
                :max-height="workspaceTableMaxHeight"
                class="workspace-list-table"
                style="width: 100%"
                @selection-change="handleMindmapSelectionChange"
              >
                <el-table-column type="selection" width="52" />
                <el-table-column
                  prop="id"
                  column-key="prop:id"
                  label="ID"
                  width="80"
                  sortable
                  :sort-method="createNumberSorter(row => row.id)"
                  :filters="mindmapColumnFilters.id"
                  :filter-method="createTableFilter(row => row.id)"
                />
                <el-table-column
                  prop="requirement_key"
                  column-key="prop:requirement_key"
                  label="需求编号"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_key)"
                  :filters="mindmapColumnFilters.requirement_key"
                  :filter-method="createTableFilter(row => row.requirement_key)"
                >
                  <template #default="{ row }">
                    <a
                      v-if="row.requirement_key"
                      href="javascript:void(0)"
                      class="requirement-link"
                      @click.stop="jumpToJiraRequirement(row.requirement_key)"
                    >
                      {{ row.requirement_key }}
                    </a>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="requirement_title"
                  column-key="prop:requirement_title"
                  label="需求标题"
                  min-width="300"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_title)"
                  :filters="mindmapColumnFilters.requirement_title"
                  :filter-method="createTableFilter(row => row.requirement_title)"
                >
                  <template #default="{ row }">
                    <el-tooltip
                      :content="getRequirementTitleText(row.requirement_title)"
                      :disabled="!getRequirementTitleText(row.requirement_title)"
                      effect="dark"
                      placement="top"
                      popper-class="requirement-title-tooltip"
                    >
                      <div class="requirement-title-cell">
                        {{ formatRequirementTitle(row.requirement_title) }}
                      </div>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="module"
                  column-key="prop:module"
                  label="模块"
                  min-width="180"
                  sortable
                  :sort-method="createTextSorter(getMindmapModule)"
                  :filters="mindmapColumnFilters.module"
                  :filter-method="createTableFilter(getMindmapModule)"
                >
                  <template #default="{ row }">
                    {{ getMindmapModule(row) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="responsibility_group"
                  column-key="prop:responsibility_group"
                  label="组别"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(getMindmapResponsibilityGroup)"
                  :filters="mindmapColumnFilters.responsibility_group"
                  :filter-method="createTableFilter(getMindmapResponsibilityGroup)"
                >
                  <template #default="{ row }">
                    {{ getMindmapResponsibilityGroup(row) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="frontend_name"
                  column-key="prop:frontend_name"
                  label="前端"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(getMindmapFrontendName)"
                  :filters="mindmapColumnFilters.frontend"
                  :filter-method="createTableFilter(getMindmapFrontendName)"
                >
                  <template #default="{ row }">
                    {{ getMindmapFrontendName(row) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="backend_name"
                  column-key="prop:backend_name"
                  label="后端"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(getMindmapBackendName)"
                  :filters="mindmapColumnFilters.backend"
                  :filter-method="createTableFilter(getMindmapBackendName)"
                >
                  <template #default="{ row }">
                    {{ getMindmapBackendName(row) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="case_count"
                  column-key="prop:case_count"
                  label="用例数"
                  width="200"
                  align="center"
                  sortable
                  :sort-method="createNumberSorter(getMindmapCaseCountTotal)"
                  :filters="mindmapColumnFilters.case_count"
                  :filter-method="createTableFilter(getMindmapCaseCountTotal)"
                >
                  <template #default="{ row }">
                    <div class="status-tags">
                      <el-tag v-if="row.case_count?.not_run" type="info" size="small">未执行:{{ row.case_count.not_run }}</el-tag>
                      <el-tag v-if="row.case_count?.pass" type="success" size="small">通过:{{ row.case_count.pass }}</el-tag>
                      <el-tag v-if="row.case_count?.fail" type="danger" size="small">失败:{{ row.case_count.fail }}</el-tag>
                      <el-tag v-if="row.case_count?.block" type="warning" size="small">阻塞:{{ row.case_count.block }}</el-tag>
                      <el-tag v-if="row.case_count?.not_test" type="info" effect="plain" size="small">不测:{{ row.case_count.not_test }}</el-tag>
                      <span v-if="!row.case_count || (!row.case_count.not_run && !row.case_count.pass && !row.case_count.fail && !row.case_count.block && !row.case_count.not_test)">0</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="testpoint_count"
                  column-key="prop:testpoint_count"
                  label="测试点数"
                  width="200"
                  align="center"
                  sortable
                  :sort-method="createNumberSorter(getMindmapTestpointCountTotal)"
                  :filters="mindmapColumnFilters.testpoint_count"
                  :filter-method="filterMindmapByTestpointStatus"
                >
                  <template #default="{ row }">
                    <div class="status-tags">
                      <el-tag v-if="row.testpoint_count?.not_run" type="info" size="small">未执行:{{ row.testpoint_count.not_run }}</el-tag>
                      <el-tag v-if="row.testpoint_count?.pass" type="success" size="small">通过:{{ row.testpoint_count.pass }}</el-tag>
                      <el-tag v-if="row.testpoint_count?.fail" type="danger" size="small">失败:{{ row.testpoint_count.fail }}</el-tag>
                      <el-tag v-if="row.testpoint_count?.block" type="warning" size="small">阻塞:{{ row.testpoint_count.block }}</el-tag>
                      <el-tag v-if="row.testpoint_count?.not_test" type="info" effect="plain" size="small">不测:{{ row.testpoint_count.not_test }}</el-tag>
                      <span v-if="!row.testpoint_count || (!row.testpoint_count.not_run && !row.testpoint_count.pass && !row.testpoint_count.fail && !row.testpoint_count.block && !row.testpoint_count.not_test)">0</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="review_testpoint_count"
                  column-key="prop:review_testpoint_count"
                  label="评审测试点数"
                  width="160"
                  align="center"
                  sortable
                  :sort-method="createNumberSorter(getMindmapReviewTestpointCountTotal)"
                  :filters="mindmapColumnFilters.review_testpoint_count"
                  :filter-method="createTableFilter(getMindmapReviewTestpointCountTotal)"
                >
                  <template #default="{ row }">
                    {{ getMindmapReviewTestpointCountText(row) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="dev_self_test_count"
                  column-key="prop:dev_self_test_count"
                  label="自测点数"
                  width="200"
                  align="center"
                  sortable
                  :sort-method="createNumberSorter(getMindmapDevSelfTestCountTotal)"
                  :filters="mindmapColumnFilters.dev_self_test_count"
                  :filter-method="createTableFilter(getMindmapDevSelfTestCountTotal)"
                >
                  <template #default="{ row }">
                    <div class="status-tags">
                      <el-tag v-if="row.dev_self_test_count?.not_run" type="info" size="small">未执行:{{ row.dev_self_test_count.not_run }}</el-tag>
                      <el-tag v-if="row.dev_self_test_count?.pass" type="success" size="small">通过:{{ row.dev_self_test_count.pass }}</el-tag>
                      <el-tag v-if="row.dev_self_test_count?.fail" type="danger" size="small">失败:{{ row.dev_self_test_count.fail }}</el-tag>
                      <el-tag v-if="row.dev_self_test_count?.block" type="warning" size="small">阻塞:{{ row.dev_self_test_count.block }}</el-tag>
                      <el-tag v-if="row.dev_self_test_count?.not_test" type="info" effect="plain" size="small">不测:{{ row.dev_self_test_count.not_test }}</el-tag>
                      <span v-if="!row.dev_self_test_count || (!row.dev_self_test_count.not_run && !row.dev_self_test_count.pass && !row.dev_self_test_count.fail && !row.dev_self_test_count.block && !row.dev_self_test_count.not_test)">0</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="executor"
                  column-key="prop:executor"
                  label="执行人"
                  width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.executor)"
                  :filters="mindmapColumnFilters.executor"
                  :filter-method="createTableFilter(row => row.executor)"
                />
                <el-table-column
                  prop="creator"
                  column-key="prop:author"
                  label="创建人"
                  width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.creator)"
                  :filters="mindmapColumnFilters.creator"
                  :filter-method="createTableFilter(row => row.creator)"
                />
                <el-table-column
                  prop="created_at"
                  column-key="prop:created_at"
                  label="创建时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.created_at)"
                  :filters="mindmapColumnFilters.created_at"
                  :filter-method="createTableFilter(row => row.created_at)"
                />
                <el-table-column
                  prop="updated_at"
                  column-key="prop:updated_at"
                  label="更新时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.updated_at)"
                  :filters="mindmapColumnFilters.updated_at"
                  :filter-method="createTableFilter(row => row.updated_at)"
                />
                <el-table-column
                  prop="version"
                  column-key="prop:version"
                  label="版本号"
                  width="140"
                  sortable
                  :sort-method="createTextSorter(row => row.version)"
                  :filters="mindmapColumnFilters.version"
                  :filter-method="createTableFilter(row => row.version)"
                />
                <el-table-column
                  prop="name"
                  column-key="prop:name"
                  label="脑图名称"
                  min-width="300"
                  sortable
                  :sort-method="createTextSorter(row => row.name)"
                  :filters="mindmapColumnFilters.name"
                  :filter-method="createTableFilter(row => row.name)"
                >
                  <template #default="{ row }">
                    <el-tooltip
                      :content="getTextCellContent(row.name)"
                      :disabled="!getTextCellContent(row.name)"
                      effect="dark"
                      placement="top"
                      popper-class="requirement-title-tooltip"
                    >
                      <a
                        v-if="row.url"
                        :href="row.url"
                        target="_blank"
                        class="mindmap-link requirement-title-cell"
                        @click.stop
                      >
                        {{ formatTextCell(row.name) }}
                      </a>
                      <span v-else class="requirement-title-cell">{{ formatTextCell(row.name) }}</span>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column label="操作" column-key="label:操作" :width="mindmapActionColumnWidth" fixed="right">
                  <template #default="{ row }">
                    <div class="action-stack">
                      <div class="action-line">
                        <el-button type="success" size="small" @click.stop="handleEdit(row)">
                          <el-icon><Edit /></el-icon>
                          编辑脑图
                        </el-button>
                        <el-button size="small" @click.stop="jumpToMindmapTestpoints(row)">
                          测试点
                        </el-button>
                      </div>
                      <div class="action-line">
                        <el-button size="small" @click.stop="jumpToMindmapDevSelfTests(row)">
                          自测测试点
                        </el-button>
                        <el-button type="primary" size="small" @click="handleEditInfo(row)">
                          <el-icon><Edit /></el-icon>
                          编辑
                        </el-button>
                        <el-button type="danger" size="small" @click="handleDelete(row)">
                          <el-icon><Delete /></el-icon>
                          删除
                        </el-button>
                      </div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <el-pagination
                v-model:current-page="mindmapPagination.page"
                v-model:page-size="mindmapPagination.pageSize"
                :total="mindmapPagination.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                class="tab-pagination"
                @size-change="handleMindmapPageChange"
                @current-change="handleMindmapPageChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('testcases')" label="测试用例" name="testcases">
            <div class="tab-panel">
              <div class="tab-toolbar">
                <el-form :inline="true" :model="testcaseFilters" class="search-form">
                  <el-form-item label="关键字">
                    <el-input
                      v-model="testcaseFilters.keyword"
                      placeholder="请输入测试用例、需求编号、需求标题或模块路径"
                      clearable
                      @keyup.enter="handleSearch"
                      @clear="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="脑图名称">
                    <el-input
                      v-model="testcaseFilters.mindmapName"
                      placeholder="请输入脑图名称"
                      clearable
                      @keyup.enter="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="组别">
                    <el-select
                      v-model="testcaseFilters.responsibilityGroup"
                      placeholder="请选择组别"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="group in groupOptions"
                        :key="group.id"
                        :label="group.name"
                        :value="group.name"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="创建人">
                    <el-select
                      v-model="testcaseFilters.authorId"
                      placeholder="请选择创建人"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="user in testcaseCreatorList"
                        :key="user.id"
                        :label="getUserDisplayName(user)"
                        :value="user.id"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="优先级">
                    <el-select
                      v-model="testcaseFilters.priority"
                      placeholder="全部"
                      clearable
                      style="width: 120px"
                    >
                      <el-option
                        v-for="option in priorityOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="状态">
                    <el-select
                      v-model="testcaseFilters.status"
                      placeholder="全部"
                      clearable
                      style="width: 140px"
                    >
                      <el-option
                        v-for="option in statusOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="handleSearch">
                      <el-icon><Search /></el-icon>
                      搜索
                    </el-button>
                    <el-button @click="handleReset">
                      <el-icon><Refresh /></el-icon>
                      重置
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="tab-toolbar-actions">
                  <TableColumnSettings
                    :table-ref="testcaseTableRef"
                    storage-key="manual-testcases.testcases"
                  />
                </div>
              </div>

              <el-table
                ref="testcaseTableRef"
                :data="testcaseTableData"
                stripe
                style="width: 100%"
                class="workspace-list-table"
                :max-height="workspaceTableMaxHeight"
              >
                <el-table-column
                  prop="node_text"
                  label="测试用例"
                  min-width="220"
                  sortable
                  :sort-method="createTextSorter(row => row.node_text)"
                  :filters="testcaseColumnFilters.node_text"
                  :filter-method="createTableFilter(row => row.node_text)"
                />
                <el-table-column
                  prop="requirement_key"
                  label="需求编号"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_key)"
                  :filters="testcaseColumnFilters.requirement_key"
                  :filter-method="createTableFilter(row => row.requirement_key)"
                >
                  <template #default="{ row }">
                    <a
                      v-if="row.requirement_key"
                      href="javascript:void(0)"
                      class="requirement-link"
                      @click.stop="jumpToJiraRequirement(row.requirement_key)"
                    >
                      {{ row.requirement_key }}
                    </a>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="requirement_title"
                  label="需求标题"
                  min-width="300"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_title)"
                  :filters="testcaseColumnFilters.requirement_title"
                  :filter-method="createTableFilter(row => row.requirement_title)"
                >
                  <template #default="{ row }">
                    <el-tooltip
                      :content="getRequirementTitleText(row.requirement_title)"
                      :disabled="!getRequirementTitleText(row.requirement_title)"
                      effect="dark"
                      placement="top"
                      popper-class="requirement-title-tooltip"
                    >
                      <div class="requirement-title-cell">
                        {{ formatRequirementTitle(row.requirement_title) }}
                      </div>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="responsibility_group"
                  label="组别"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.responsibility_group)"
                  :filters="testcaseColumnFilters.responsibility_group"
                  :filter-method="createTableFilter(row => row.responsibility_group)"
                />
                <el-table-column
                  prop="module_path"
                  label="模块路径"
                  min-width="260"
                  sortable
                  :sort-method="createTextSorter(row => row.module_path)"
                  :filters="testcaseColumnFilters.module_path"
                  :filter-method="createTableFilter(row => row.module_path)"
                >
                  <template #default="{ row }">
                    <span class="path-text">{{ row.module_path || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  label="优先级"
                  label-class-name="nowrap-header"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatPriority(row.priority))"
                  :filters="testcaseColumnFilters.priority"
                  :filter-method="createTableFilter(row => formatPriority(row.priority))"
                >
                  <template #default="{ row }">
                    {{ formatPriority(row.priority) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="状态"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatStatus(row.status))"
                  :filters="testcaseColumnFilters.status"
                  :filter-method="createTableFilter(row => formatStatus(row.status))"
                >
                  <template #default="{ row }">
                    {{ formatStatus(row.status) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="自测状态"
                  width="110"
                  sortable
                  :sort-method="createTextSorter(getNodeSelfTestStatusText)"
                  :filters="testcaseColumnFilters.self_test_status"
                  :filter-method="createTableFilter(getNodeSelfTestStatusText)"
                >
                  <template #default="{ row }">
                    <span>{{ getNodeSelfTestStatusText(row) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  label="标签"
                  min-width="180"
                  sortable
                  :sort-method="createTextSorter(getNodeTags)"
                  :filters="testcaseColumnFilters.tags"
                  :filter-method="createTableFilter(getNodeTags)"
                >
                  <template #default="{ row }">
                    <div v-if="row.tags && row.tags.length" class="node-tags">
                      <el-tag
                        v-for="tag in row.tags"
                        :key="`${row.id}-${tag}`"
                        size="small"
                      >
                        {{ tag }}
                      </el-tag>
                    </div>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="updated_at"
                  label="脑图更新时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.updated_at)"
                  :filters="testcaseColumnFilters.updated_at"
                  :filter-method="createTableFilter(row => row.updated_at)"
                />
                <el-table-column
                  prop="mindmap_name"
                  label="所属脑图"
                  min-width="180"
                  sortable
                  :sort-method="createTextSorter(row => row.mindmap_name)"
                  :filters="testcaseColumnFilters.mindmap_name"
                  :filter-method="createTableFilter(row => row.mindmap_name)"
                />
                <el-table-column label="操作" :width="testcaseActionColumnWidth" fixed="right">
                  <template #default="{ row }">
                    <div class="row-actions">
                      <el-button type="primary" size="small" @click.stop="handleNodeEdit(row)">
                        <el-icon><Edit /></el-icon>
                        编辑脑图
                      </el-button>
                      <el-button type="success" size="small" @click.stop="handleNodeView(row)">
                        <el-icon><View /></el-icon>
                        查看脑图
                      </el-button>
                      <el-button size="small" plain @click="handleCreateTestcaseDefect(row)">
                        提缺陷
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <el-pagination
                v-model:current-page="testcasePagination.page"
                v-model:page-size="testcasePagination.pageSize"
                :total="testcasePagination.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                class="tab-pagination"
                @size-change="handleTestcasePageChange"
                @current-change="handleTestcasePageChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('testpoints')" label="测试点" name="testpoints">
            <div class="tab-panel">
              <div class="tab-toolbar">
                <el-form :inline="true" :model="testpointFilters" class="search-form">
                  <el-form-item label="关键字">
                    <el-input
                      v-model="testpointFilters.keyword"
                      placeholder="请输入测试点、需求编号、需求标题或模块路径"
                      clearable
                      @keyup.enter="handleSearch"
                      @clear="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="脑图ID">
                    <el-input
                      v-model="testpointFilters.mindmapId"
                      placeholder="请输入脑图ID"
                      clearable
                      @keyup.enter="handleSearch"
                      @clear="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="所属脑图">
                    <el-input
                      v-model="testpointFilters.mindmapName"
                      placeholder="请输入脑图名称"
                      clearable
                      @keyup.enter="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="标签">
                    <el-input
                      v-model="testpointFilters.tag"
                      placeholder="请输入标签"
                      clearable
                      @keyup.enter="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="状态">
                    <el-select
                      v-model="testpointFilters.status"
                      placeholder="请选择状态"
                      clearable
                      style="width: 160px"
                    >
                      <el-option
                        v-for="option in statusOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="组别">
                    <el-select
                      v-model="testpointFilters.responsibilityGroup"
                      placeholder="请选择组别"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="group in groupOptions"
                        :key="group.id"
                        :label="group.name"
                        :value="group.name"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="创建人">
                    <el-select
                      v-model="testpointFilters.authorId"
                      placeholder="请选择创建人"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="user in testpointCreatorList"
                        :key="user.id"
                        :label="getUserDisplayName(user)"
                        :value="user.id"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="handleSearch">
                      <el-icon><Search /></el-icon>
                      搜索
                    </el-button>
                    <el-button @click="handleReset">
                      <el-icon><Refresh /></el-icon>
                      重置
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="tab-toolbar-actions">
                  <TableColumnSettings
                    :table-ref="testpointTableRef"
                    storage-key="manual-testcases.testpoints"
                  />
                </div>
              </div>

              <el-table
                ref="testpointTableRef"
                :data="testpointTableData"
                stripe
                style="width: 100%"
                class="workspace-list-table"
                :max-height="workspaceTableMaxHeight"
              >
                <el-table-column
                  prop="id"
                  label="ID"
                  min-width="160"
                  sortable
                  :sort-method="createTextSorter(row => row.id)"
                  :filters="testpointColumnFilters.id"
                  :filter-method="createTableFilter(row => row.id)"
                />
                <el-table-column
                  prop="node_text"
                  label="测试点"
                  min-width="220"
                  sortable
                  :sort-method="createTextSorter(row => row.node_text)"
                  :filters="testpointColumnFilters.node_text"
                  :filter-method="createTableFilter(row => row.node_text)"
                />
                <el-table-column
                  prop="requirement_key"
                  label="需求编号"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_key)"
                  :filters="testpointColumnFilters.requirement_key"
                  :filter-method="createTableFilter(row => row.requirement_key)"
                >
                  <template #default="{ row }">
                    <a
                      v-if="row.requirement_key"
                      href="javascript:void(0)"
                      class="requirement-link"
                      @click.stop="jumpToJiraRequirement(row.requirement_key)"
                    >
                      {{ row.requirement_key }}
                    </a>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="requirement_title"
                  label="需求标题"
                  min-width="300"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_title)"
                  :filters="testpointColumnFilters.requirement_title"
                  :filter-method="createTableFilter(row => row.requirement_title)"
                >
                  <template #default="{ row }">
                    <el-tooltip
                      :content="getRequirementTitleText(row.requirement_title)"
                      :disabled="!getRequirementTitleText(row.requirement_title)"
                      effect="dark"
                      placement="top"
                      popper-class="requirement-title-tooltip"
                    >
                      <div class="requirement-title-cell">
                        {{ formatRequirementTitle(row.requirement_title) }}
                      </div>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="creator"
                  label="创建人"
                  width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.creator)"
                  :filters="testpointColumnFilters.creator"
                  :filter-method="createTableFilter(row => row.creator)"
                />
                <el-table-column
                  prop="reviewer_name"
                  label="评审人"
                  width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.reviewer_name)"
                  :filters="testpointColumnFilters.reviewer_name"
                  :filter-method="createTableFilter(row => row.reviewer_name)"
                >
                  <template #default="{ row }">
                    {{ row.reviewer_name || '-' }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="review_time"
                  label="评审时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.review_time)"
                  :filters="testpointColumnFilters.review_time"
                  :filter-method="createTableFilter(row => row.review_time)"
                >
                  <template #default="{ row }">
                    {{ row.review_time ? formatDateTime(row.review_time) : '-' }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="review_status"
                  label="评审状态"
                  width="110"
                  sortable
                  :sort-method="createTextSorter(row => row.review_status)"
                  :filters="testpointColumnFilters.review_status"
                  :filter-method="createTableFilter(row => row.review_status)"
                >
                  <template #default="{ row }">
                    {{ row.review_status || '-' }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="responsibility_group"
                  label="组别"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.responsibility_group)"
                  :filters="testpointColumnFilters.responsibility_group"
                  :filter-method="createTableFilter(row => row.responsibility_group)"
                />
                <el-table-column
                  label="优先级"
                  label-class-name="nowrap-header"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatPriority(row.priority))"
                  :filters="testpointColumnFilters.priority"
                  :filter-method="createTableFilter(row => formatPriority(row.priority))"
                >
                  <template #default="{ row }">
                    {{ formatPriority(row.priority) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="状态"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatStatus(row.status))"
                  :filters="testpointColumnFilters.status"
                  :filter-method="createTableFilter(row => formatStatus(row.status))"
                >
                  <template #default="{ row }">
                    {{ formatStatus(row.status) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="自测状态"
                  width="110"
                  sortable
                  :sort-method="createTextSorter(getNodeSelfTestStatusText)"
                  :filters="testpointColumnFilters.self_test_status"
                  :filter-method="createTableFilter(getNodeSelfTestStatusText)"
                >
                  <template #default="{ row }">
                    <span>{{ getNodeSelfTestStatusText(row) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="module_path"
                  label="模块路径"
                  min-width="260"
                  sortable
                  :sort-method="createTextSorter(row => row.module_path)"
                  :filters="testpointColumnFilters.module_path"
                  :filter-method="createTableFilter(row => row.module_path)"
                >
                  <template #default="{ row }">
                    <span class="path-text">{{ row.module_path || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  label="标签"
                  min-width="180"
                  sortable
                  :sort-method="createTextSorter(getNodeTags)"
                  :filters="testpointColumnFilters.tags"
                  :filter-method="createTableFilter(getNodeTags)"
                >
                  <template #default="{ row }">
                    <div v-if="row.tags && row.tags.length" class="node-tags">
                      <el-tag
                        v-for="tag in row.tags"
                        :key="`${row.id}-${tag}`"
                        size="small"
                      >
                        {{ tag }}
                      </el-tag>
                    </div>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="updated_at"
                  label="脑图更新时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.updated_at)"
                  :filters="testpointColumnFilters.updated_at"
                  :filter-method="createTableFilter(row => row.updated_at)"
                />
                <el-table-column
                  prop="mindmap_id"
                  label="脑图ID"
                  min-width="120"
                  sortable
                  :sort-method="createNumberSorter(row => row.mindmap_id)"
                  :filters="testpointColumnFilters.mindmap_id"
                  :filter-method="createTableFilter(row => row.mindmap_id)"
                >
                  <template #default="{ row }">
                    <el-button
                      v-if="row.mindmap_id"
                      link
                      type="primary"
                      @click.stop="jumpToTestpointMindmap(row)"
                    >
                      {{ row.mindmap_id }}
                    </el-button>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" :width="testpointActionColumnWidth" fixed="right">
                  <template #default="{ row }">
                    <div class="action-stack">
                      <div class="action-line">
                        <el-button type="primary" size="small" @click.stop="handleNodeEdit(row)">
                          <el-icon><Edit /></el-icon>
                          编辑脑图
                        </el-button>
                        <el-button size="small" plain @click="handleCreateTestpointDefect(row)">
                          提缺陷
                        </el-button>
                      </div>
                      <div class="action-line">
                        <el-button size="small" @click.stop="openTestpointDefectDialog(row)">
                          关联缺陷
                        </el-button>
                        <el-button size="small" @click.stop="jumpToVersionDefectsByTestpoint(row)">
                          版本缺陷
                        </el-button>
                        <el-button size="small" @click.stop="jumpToBugRecordsByTestpoint(row)">
                          线上缺陷
                        </el-button>
                      </div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <el-pagination
                v-model:current-page="testpointPagination.page"
                v-model:page-size="testpointPagination.pageSize"
                :total="testpointPagination.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                class="tab-pagination"
                @size-change="handleTestpointPageChange"
                @current-change="handleTestpointPageChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('devselftest')" label="自测测试点" name="devselftest">
            <div class="tab-panel">
              <div class="tab-toolbar">
                <el-form :inline="true" :model="devSelfTestFilters" class="search-form">
                  <el-form-item label="脑图名称">
                    <el-input
                      v-model="devSelfTestFilters.mindmapName"
                      placeholder="请输入脑图名称"
                      clearable
                      @keyup.enter="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="需求编号">
                    <el-input
                      v-model="devSelfTestFilters.requirementKey"
                      placeholder="请输入需求编号"
                      clearable
                      @keyup.enter="handleSearch"
                      @clear="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="需求标题">
                    <el-input
                      v-model="devSelfTestFilters.requirementTitle"
                      placeholder="请输入需求标题"
                      clearable
                      @keyup.enter="handleSearch"
                      @clear="handleSearch"
                    />
                  </el-form-item>
                  <el-form-item label="状态">
                    <el-select
                      v-model="devSelfTestFilters.status"
                      placeholder="请选择状态"
                      clearable
                      style="width: 160px"
                    >
                      <el-option label="未执行" value="not_run" />
                      <el-option label="通过" value="pass" />
                      <el-option label="失败" value="fail" />
                      <el-option label="阻塞" value="block" />
                      <el-option label="本版本不测" value="not_test" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="组别">
                    <el-select
                      v-model="devSelfTestFilters.responsibilityGroup"
                      placeholder="请选择组别"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="group in groupOptions"
                        :key="group.id"
                        :label="group.name"
                        :value="group.name"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="前端">
                    <el-select
                      v-model="devSelfTestFilters.frontendDeveloperId"
                      placeholder="请选择前端"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="user in frontendDeveloperOptions"
                        :key="user.id"
                        :label="getUserDisplayName(user)"
                        :value="user.id"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="后端">
                    <el-select
                      v-model="devSelfTestFilters.backendDeveloperId"
                      placeholder="请选择后端"
                      clearable
                      filterable
                    >
                      <el-option
                        v-for="user in backendDeveloperOptions"
                        :key="user.id"
                        :label="getUserDisplayName(user)"
                        :value="user.id"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="handleSearch">
                      <el-icon><Search /></el-icon>
                      搜索
                    </el-button>
                    <el-button @click="handleReset">
                      <el-icon><Refresh /></el-icon>
                      重置
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="tab-toolbar-actions">
                  <TableColumnSettings
                    :table-ref="devSelfTestTableRef"
                    storage-key="manual-testcases.devselftest"
                  />
                  <el-dropdown
                    trigger="click"
                    @command="handleDevSelfTestAuditCommand"
                  >
                    <el-button type="primary" :disabled="!devSelfTestSelectedRows.length">
                      审核
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="approved">审核通过</el-dropdown-item>
                        <el-dropdown-item command="rejected">审核驳回</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>

              <el-table
                ref="devSelfTestTableRef"
                :data="devSelfTestTableData"
                stripe
                style="width: 100%"
                class="workspace-list-table"
                :max-height="workspaceTableMaxHeight"
                @selection-change="handleDevSelfTestSelectionChange"
              >
                <el-table-column type="selection" width="52" />
                <el-table-column
                  prop="testpoint"
                  label="测试点"
                  min-width="200"
                  sortable
                  :sort-method="createTextSorter(row => row.testpoint)"
                  :filters="devSelfTestColumnFilters.testpoint"
                  :filter-method="createTableFilter(row => row.testpoint)"
                />
                <el-table-column
                  prop="requirement_key"
                  label="需求编号"
                  min-width="140"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_key)"
                  :filters="devSelfTestColumnFilters.requirement_key"
                  :filter-method="createTableFilter(row => row.requirement_key)"
                >
                  <template #default="{ row }">
                    <a
                      v-if="row.requirement_key"
                      href="javascript:void(0)"
                      class="requirement-link"
                      @click.stop="jumpToJiraRequirement(row.requirement_key)"
                    >
                      {{ row.requirement_key }}
                    </a>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="requirement_title"
                  label="需求标题"
                  min-width="300"
                  sortable
                  :sort-method="createTextSorter(row => row.requirement_title)"
                  :filters="devSelfTestColumnFilters.requirement_title"
                  :filter-method="createTableFilter(row => row.requirement_title)"
                >
                  <template #default="{ row }">
                    <el-tooltip
                      :content="getRequirementTitleText(row.requirement_title)"
                      :disabled="!getRequirementTitleText(row.requirement_title)"
                      effect="dark"
                      placement="top"
                      popper-class="requirement-title-tooltip"
                    >
                      <div class="requirement-title-cell">
                        {{ formatRequirementTitle(row.requirement_title) }}
                      </div>
                    </el-tooltip>
                  </template>
                </el-table-column>
                <el-table-column
                  label="优先级"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatPriority(row.priority))"
                  :filters="devSelfTestColumnFilters.priority"
                  :filter-method="createTableFilter(row => formatPriority(row.priority))"
                >
                  <template #default="{ row }">
                    {{ formatPriority(row.priority) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="状态"
                  width="100"
                  sortable
                  :sort-method="createTextSorter(row => formatStatus(row.status))"
                  :filters="devSelfTestColumnFilters.status"
                  :filter-method="createTableFilter(row => formatStatus(row.status))"
                >
                  <template #default="{ row }">
                    {{ formatStatus(row.status) }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="审核状态"
                  width="110"
                  sortable
                  :sort-method="createTextSorter(row => formatAuditStatus(row.audit_status))"
                  :filters="devSelfTestColumnFilters.audit_status"
                  :filter-method="createTableFilter(row => formatAuditStatus(row.audit_status))"
                >
                  <template #default="{ row }">
                    {{ formatAuditStatus(row.audit_status) }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="responsibility_group"
                  label="组别"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(row => row.responsibility_group)"
                  :filters="devSelfTestColumnFilters.responsibility_group"
                  :filter-method="createTableFilter(row => row.responsibility_group)"
                />
                <el-table-column
                  label="前端"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(getDevSelfTestFrontendName)"
                  :filters="devSelfTestColumnFilters.frontend"
                  :filter-method="createTableFilter(getDevSelfTestFrontendName)"
                >
                  <template #default="{ row }">
                    {{ getUserDisplayName(row.frontend_developer, '-') }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="后端"
                  min-width="120"
                  sortable
                  :sort-method="createTextSorter(getDevSelfTestBackendName)"
                  :filters="devSelfTestColumnFilters.backend"
                  :filter-method="createTableFilter(getDevSelfTestBackendName)"
                >
                  <template #default="{ row }">
                    {{ getUserDisplayName(row.backend_developer, '-') }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="module_path"
                  label="模块路径"
                  min-width="260"
                  sortable
                  :sort-method="createTextSorter(row => row.module_path)"
                  :filters="devSelfTestColumnFilters.module_path"
                  :filter-method="createTableFilter(row => row.module_path)"
                >
                  <template #default="{ row }">
                    <span class="path-text">{{ row.module_path || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="updated_at"
                  label="更新时间"
                  width="180"
                  sortable
                  :sort-method="createDateSorter(row => row.updated_at)"
                  :filters="devSelfTestColumnFilters.updated_at"
                  :filter-method="createTableFilter(row => row.updated_at)"
                />
                <el-table-column label="操作" :width="devSelfTestActionColumnWidth" fixed="right">
                  <template #default="{ row }">
                    <div class="row-actions">
                      <el-button size="small" type="success" @click.stop="handleViewDevSelfTestMindmap(row)">
                        <el-icon><View /></el-icon>
                        查看脑图
                      </el-button>
                      <el-button
                        size="small"
                        type="primary"
                        plain
                        :disabled="!row.can_edit"
                        @click="handleEditDevSelfTest(row)"
                      >
                        编辑
                      </el-button>
                      <el-button size="small" plain @click="handleCreateDevSelfTestDefect(row)">
                        提缺陷
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <el-pagination
                v-model:current-page="devSelfTestPagination.page"
                v-model:page-size="devSelfTestPagination.pageSize"
                :total="devSelfTestPagination.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                class="tab-pagination"
                @size-change="handleDevSelfTestPageChange"
                @current-change="handleDevSelfTestPageChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('technical-solution-designs')"
              label="技术方案设计"
              name="technical-solution-designs"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="defect-tab-embed">
              <TechnicalSolutionDesignList
                embedded
                :active="activeTab === 'technical-solution-designs'"
                :linked-category-id="currentRealCategoryId"
                :linked-keyword="linkedTechnicalSolutionDesignKeyword"
                :linked-testpoint-id="linkedTechnicalSolutionDesignTestpointId"
                :linked-project-id="currentProjectId"
                :linked-category-name="currentRealCategoryLabel"
                :linked-category-path="currentRealCategoryPath"
                :linked-version-id="currentVersionId === 'all' ? null : currentVersionId"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('quality-report-list')" label="报告列表" name="quality-report-list" class="embedded-scroll-pane" lazy>
            <div class="report-list-tab-embed">
              <QualityAnalysisReportListPanel
                :active="activeTab === 'quality-report-list'"
                use-linked-version
                :linked-version="currentLinkedVersionName"
                :linked-project-id="currentProjectId"
                detail-view-mode="route"
                detail-route-name="ManualTestCaseList"
                :detail-query="{ tab: 'quality-report-live' }"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('quality-report-live')"
              label="实时质量分析"
              name="quality-report-live"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="report-detail-tab-embed">
              <QualityAnalysisReportDetailPanel
                ref="qualityReportLivePanelRef"
                embedded
                :active="activeTab === 'quality-report-live'"
                compact-header
                fixed-detail-tab="live"
                use-linked-version
                :linked-version="currentLinkedVersionName"
                :linked-project-id="currentProjectId"
                :show-back-button="false"
                external-toolbar
                @toolbar-state-change="handleQualityLiveToolbarStateChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('version-defect-analysis')"
              label="版本缺陷分析"
              name="version-defect-analysis"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="defect-tab-embed">
              <VersionDefectAnalysisPanel
                :active="activeTab === 'version-defect-analysis'"
                :linked-project-id="currentProjectId"
                :linked-version-id="currentVersionId === 'all' ? null : currentVersionId"
                :linked-version-name="currentLinkedVersionName"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('version-defects')" label="版本缺陷" name="version-defects" class="embedded-scroll-pane" lazy>
            <div class="defect-tab-embed">
              <DefectList
                embedded
                :active="activeTab === 'version-defects'"
                :linked-category-id="currentRealCategoryId"
                :linked-keyword="linkedDefectKeyword"
                :linked-testpoint-id="linkedVersionDefectTestpointId"
                :linked-project-id="currentProjectId"
                :linked-category-name="currentRealCategoryLabel"
                :linked-category-path="currentRealCategoryPath"
                :linked-version-id="currentVersionId === 'all' ? null : currentVersionId"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('bug-records')" label="线上缺陷" name="bug-records" class="embedded-scroll-pane" lazy>
            <div class="jira-tab-embed">
              <QualityAnalysisJiraData
                embedded
                default-tab="bug-records"
                :active="activeTab === 'bug-records'"
                :show-online-defect-analysis="false"
                use-linked-version
                :linked-version="currentLinkedVersionName"
                :linked-bug-keyword="linkedBugKeyword"
                :linked-bug-testpoint-id="linkedBugTestpointId"
                :linked-project-id="currentProjectId"
                :linked-modules="linkedJiraModules"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('quality-knowledge-assistant')" label="知识库助手" name="quality-knowledge-assistant" class="embedded-scroll-pane" lazy>
            <div class="knowledge-assistant-tab-embed">
              <ManualQualityKnowledgeAssistant
                :active="activeTab === 'quality-knowledge-assistant'"
                :linked-project-id="currentProjectId"
                :linked-project-name="selectedWorkspaceProject?.name || ''"
                :linked-version-id="currentVersionId"
                :linked-version-name="currentLinkedVersionName"
                :linked-category-id="currentRealCategoryId"
              >
                <template #knowledge-rail-before>
                  <el-popover
                    v-model:visible="knowledgeProjectPopoverVisible"
                    placement="right-start"
                    trigger="click"
                    width="300"
                    popper-class="knowledge-context-popover"
                  >
                    <template #reference>
                      <button type="button" class="knowledge-context-menu__item">
                        <el-icon><Collection /></el-icon>
                        <span class="knowledge-context-menu__label">项目</span>
                      </button>
                    </template>
                    <div class="knowledge-context-panel">
                      <div class="knowledge-context-panel__title">选择项目</div>
                      <div class="knowledge-context-panel__list">
                        <button
                          v-for="project in workspaceProjects"
                          :key="project.id"
                          type="button"
                          class="knowledge-context-option"
                          :class="{ 'knowledge-context-option--active': String(project.id) === String(currentProjectId || '') }"
                          @click="handleKnowledgeProjectSelection(project.id)"
                        >
                          <span class="knowledge-context-option__text">{{ project.name }}</span>
                          <el-tag v-if="project.is_default" size="small" type="success" effect="plain">默认</el-tag>
                        </button>
                        <el-empty
                          v-if="!workspaceProjects.length"
                          description="暂无项目"
                          :image-size="48"
                        />
                      </div>
                      <div v-if="canSetDefaultWorkspaceProject" class="knowledge-context-panel__footer">
                        <el-button
                          size="small"
                          type="warning"
                          plain
                          :loading="workspaceProjectDefaultLoading"
                          :disabled="!selectedWorkspaceProject || selectedWorkspaceProject.is_default"
                          @click="handleSetCurrentProjectDefault"
                        >
                          {{ selectedWorkspaceProject?.is_default ? '默认项目' : '设为默认' }}
                        </el-button>
                      </div>
                    </div>
                  </el-popover>

                  <el-popover
                    v-model:visible="knowledgeVersionPopoverVisible"
                    placement="right-start"
                    trigger="click"
                    width="300"
                    popper-class="knowledge-context-popover"
                    :disabled="!currentProjectId"
                  >
                    <template #reference>
                      <button
                        type="button"
                        class="knowledge-context-menu__item"
                        :class="{ 'knowledge-context-menu__item--disabled': !currentProjectId }"
                      >
                        <el-icon><Files /></el-icon>
                        <span class="knowledge-context-menu__label">版本号</span>
                      </button>
                    </template>
                    <div class="knowledge-context-panel">
                      <div class="knowledge-context-panel__title">选择版本号</div>
                      <div class="knowledge-context-panel__list">
                        <button
                          type="button"
                          class="knowledge-context-option"
                          :class="{ 'knowledge-context-option--active': !currentVersionId || currentVersionId === 'all' }"
                          @click="handleKnowledgeVersionSelection('all')"
                        >
                          <span class="knowledge-context-option__text">全部</span>
                        </button>
                        <button
                          v-for="version in versionList"
                          :key="version.id"
                          type="button"
                          class="knowledge-context-option"
                          :class="{ 'knowledge-context-option--active': String(version.id) === String(currentVersionId || '') }"
                          @click="handleKnowledgeVersionSelection(version.id)"
                        >
                          <span class="knowledge-context-option__text">{{ version.name }}</span>
                          <el-tag v-if="version.is_default" size="small" type="success" effect="plain">默认</el-tag>
                        </button>
                        <el-empty
                          v-if="!versionList.length"
                          description="暂无版本"
                          :image-size="48"
                        />
                      </div>
                      <div class="knowledge-context-panel__footer">
                        <el-button type="primary" size="small" :disabled="!currentProjectId" @click="handleManageVersions">
                          管理版本
                        </el-button>
                      </div>
                    </div>
                  </el-popover>
                </template>
              </ManualQualityKnowledgeAssistant>
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('requirement-overview')" label="总览" name="requirement-overview" class="embedded-scroll-pane" lazy>
            <div class="overview-tab-embed">
              <ResearchProgressOverviewPanel
                embedded
                :active="activeTab === 'requirement-overview'"
                :linked-version="currentLinkedVersionName"
                :linked-project-id="currentProjectId"
                @summary-change="handleResearchProgressSummaryChange"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('version-requirements')" label="版本需求" name="version-requirements" class="embedded-scroll-pane" lazy>
            <div class="jira-tab-embed">
              <VersionRequirementList
                embedded
                :active="activeTab === 'version-requirements'"
                use-linked-version
                :linked-version="currentLinkedVersionName"
                :linked-keyword="linkedRequirementKeyword"
                :linked-modules="linkedJiraModules"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('requirement-records')" label="JIRA需求数据" name="requirement-records" class="embedded-scroll-pane" lazy>
            <div class="jira-tab-embed">
              <QualityAnalysisJiraData
                embedded
                default-tab="requirement-records"
                :active="activeTab === 'requirement-records'"
                use-linked-version
                :linked-version="currentLinkedVersionName"
                :linked-project-id="currentProjectId"
                :linked-keyword="linkedRequirementKeyword"
                :linked-modules="linkedJiraModules"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('project-environments')" label="项目环境" name="project-environments" class="embedded-scroll-pane" lazy>
            <div class="project-environment-tab-embed">
              <ProjectEnvironmentPanel
                :active="activeTab === 'project-environments'"
                :current-project-id="currentProjectId"
                :workspace-projects="workspaceProjects"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('knowledge-repositories')" label="代码仓库" name="knowledge-repositories" class="embedded-scroll-pane" lazy>
            <div class="knowledge-repository-tab-embed">
              <KnowledgeRepositoryConfigPanel
                :active="activeTab === 'knowledge-repositories'"
                :current-project-id="currentProjectId"
                :workspace-projects="workspaceProjects"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('project-asset-insight')" label="资产图谱" name="project-asset-insight" class="embedded-scroll-pane" lazy>
            <div class="project-asset-insight-tab-embed">
              <ProjectAssetInsightPanel
                :active="activeTab === 'project-asset-insight'"
                :current-project-id="currentProjectId"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('configs')" label="JIRA接口" name="configs" class="embedded-scroll-pane" lazy>
            <div class="jira-tab-embed">
              <QualityAnalysisJiraData
                embedded
                default-tab="configs"
                :active="activeTab === 'configs'"
                use-linked-version
                :linked-version="currentLinkedVersionName"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane v-if="isPrimaryTabVisible('other-settings')" label="JIRA编号URL" name="other-settings" class="embedded-scroll-pane" lazy>
            <div class="jira-tab-embed">
              <QualityAnalysisJiraData embedded default-tab="other-settings" :active="activeTab === 'other-settings'" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('email-config')"
              label="邮件配置"
              name="email-config"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="defect-notification-tab-embed">
              <DefectNotificationSettings fixed-sub-tab="email-config" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('email-template-config')"
              label="邮件模板"
              name="email-template-config"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="defect-notification-tab-embed">
              <DefectNotificationSettings fixed-sub-tab="email-template-config" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('notification-settings')"
              label="消息提醒"
              name="notification-settings"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="defect-notification-tab-embed">
              <DefectNotificationSettings fixed-sub-tab="notification-settings" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('list-sort-config')"
              label="列表排序"
              name="list-sort-config"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="list-sort-config-tab-embed">
              <ManualPageListConfigPanel :active="activeTab === 'list-sort-config'" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('members')"
              label="成员"
              name="members"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="member-tab-embed">
              <MemberManagementPanel :active="activeTab === 'members'" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('groups')"
              label="组别"
              name="groups"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="group-tab-embed">
              <GroupManagementPanel :active="activeTab === 'groups'" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('roles')"
              label="角色"
              name="roles"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="role-tab-embed">
              <RoleManagementPanel :active="activeTab === 'roles'" />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('projects')"
              label="项目"
              name="projects"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="project-tab-embed">
              <ProjectManagementPanel
                :active="activeTab === 'projects'"
                :current-project-id="currentProjectId"
                @projects-updated="handleWorkspaceProjectsUpdated"
                @switch-project="handleWorkspaceProjectSelection"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('versions')"
              label="版本"
              name="versions"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="version-tab-embed">
              <VersionManagementPanel
                :active="activeTab === 'versions'"
                :current-project-id="currentProjectId"
                :current-version-id="currentVersionId"
                :workspace-projects="workspaceProjects"
                :versions="versionList"
                :loading="versionListLoading"
                @switch-project="handleWorkspaceProjectSelection"
                @select-version="handleWorkspaceVersionSelection"
                @create-version="handleAddVersion"
                @edit-version="handleEditVersion"
                @delete-version="handleDeleteVersion"
                @set-default-version="handleSetDefault"
                @refresh="handleWorkspaceProjectsUpdated"
              />
            </div>
            </el-tab-pane>

            <el-tab-pane
              v-if="isPrimaryTabVisible('permissions')"
              label="权限"
              name="permissions"
              class="embedded-scroll-pane"
              lazy
            >
            <div class="permission-tab-embed">
              <PermissionManagementPanel :active="activeTab === 'permissions'" />
            </div>
            </el-tab-pane>
          </el-tabs>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 测试脑图对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      @close="handleDialogClose"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="脑图名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入脑图名称"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item label="创建人">
          <el-input
            v-model="formData.creator_name"
            disabled
            placeholder="当前登录人"
          />
        </el-form-item>
        <el-form-item label="执行人">
          <el-select
            v-model="formData.executor_id"
            placeholder="请选择执行人"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="user in executorOptions"
              :key="user.id"
              :label="getUserDisplayName(user)"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!formData.id" label="导入XMind">
          <div class="xmind-import-field">
            <div class="xmind-import-row">
              <el-button type="primary" plain :loading="xmindImporting" @click="triggerXMindImport">
                <el-icon><Upload /></el-icon>
                上传 XMind
              </el-button>
              <span class="xmind-import-name">{{ importedXMindName || '未选择文件' }}</span>
              <el-button v-if="importedXMindName" link type="danger" @click="clearImportedXMind">清空</el-button>
            </div>
            <div class="xmind-import-tip">
              创建时由后台解析 XMind。若根节点是“版本号+用户名+测试分析”，会按其下需求子节点拆分为多条脑图；
              若根节点本身就是需求节点，则创建 1 条测试脑图。
            </div>
            <input
              ref="xmindFileInputRef"
              type="file"
              accept=".xmind"
              class="xmind-file-input"
              @change="handleXMindFileChange"
            >
          </div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入描述"
          />
        </el-form-item>
        <el-form-item label="版本号" prop="version_id">
          <el-select
            v-model="formData.version_id"
            placeholder="请选择版本"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="version in versionList"
              :key="version.id"
              :label="version.name"
              :value="version.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="组别">
          <el-select
            v-model="formData.responsibility_group"
            placeholder="请选择组别"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="group in groupOptions"
              :key="group.id"
              :label="group.name"
              :value="group.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="前端">
          <el-select
            v-model="formData.frontend_developer_id"
            placeholder="请选择前端人员"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="user in frontendDeveloperOptions"
              :key="user.id"
              :label="getUserDisplayName(user)"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="后端">
          <el-select
            v-model="formData.backend_developer_id"
            placeholder="请选择后端人员"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="user in backendDeveloperOptions"
              :key="user.id"
              :label="getUserDisplayName(user)"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关联URL">
          <el-input
            v-model="formData.url"
            placeholder="请输入关联的URL地址（可选）"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑目录对话框 -->
    <el-dialog
      v-model="categoryDialogVisible"
      :title="categoryDialogTitle"
      width="500px"
    >
      <el-form :model="categoryFormData" :rules="categoryFormRules" ref="categoryFormRef" label-width="100px">
        <el-form-item label="目录名称" prop="name">
          <el-input
            v-model="categoryFormData.name"
            placeholder="请输入目录名称"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="categoryFormData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCategorySubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 版本管理对话框 -->
    <el-dialog
      v-model="versionDialogVisible"
      title="版本管理"
      width="900px"
      @close="handleVersionDialogClose"
    >
        <div class="version-management">
          <div class="version-toolbar">
            <el-button type="primary" @click="handleAddVersion">
              <el-icon><Plus /></el-icon>
              添加版本
            </el-button>
            <TableColumnSettings
              :table-ref="versionDialogTableRef"
              storage-key="manual-testcases.version-dialog"
            />
          </div>

        <el-table
          ref="versionDialogTableRef"
          :data="versionList"
          stripe
          style="width: 100%; margin-top: 16px;"
          class="workspace-list-table"
          :max-height="versionManagementTableMaxHeight"
        >
          <el-table-column
            prop="name"
            label="版本名称"
            min-width="150"
            sortable
            :sort-method="createTextSorter(row => row.name)"
            :filters="versionColumnFilters.name"
            :filter-method="createTableFilter(row => row.name)"
          />
          <el-table-column
            prop="description"
            label="描述"
            min-width="200"
            sortable
            :sort-method="createTextSorter(row => row.description)"
            :filters="versionColumnFilters.description"
            :filter-method="createTableFilter(row => row.description)"
          />
          <el-table-column
            label="默认版本"
            width="100"
            align="center"
            sortable
            :sort-method="createTextSorter(getVersionDefaultLabel)"
            :filters="versionColumnFilters.is_default"
            :filter-method="createTableFilter(getVersionDefaultLabel)"
          >
            <template #default="{ row }">
              <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
              <el-button
                v-else
                type="primary"
                link
                size="small"
                @click="handleSetDefault(row)"
              >
                设为默认
              </el-button>
            </template>
          </el-table-column>
          <el-table-column
            label="基线版本"
            width="100"
            align="center"
            sortable
            :sort-method="createTextSorter(getVersionBaselineLabel)"
            :filters="versionColumnFilters.is_baseline"
            :filter-method="createTableFilter(getVersionBaselineLabel)"
          >
            <template #default="{ row }">
              <el-tag v-if="row.is_baseline" type="warning" size="small">基线</el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="180"
            sortable
            :sort-method="createDateSorter(row => row.created_at)"
            :filters="versionColumnFilters.created_at"
            :filter-method="createTableFilter(row => row.created_at)"
          />
          <el-table-column label="操作" :width="versionDialogActionColumnWidth" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="handleEditVersion(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button type="danger" size="small" @click="handleDeleteVersion(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 添加/编辑版本对话框 -->
    <el-dialog
      v-model="versionFormDialogVisible"
      :title="versionFormTitle"
      width="600px"
      @close="handleVersionFormDialogClose"
    >
      <el-form :model="versionFormData" :rules="versionFormRules" ref="versionFormRef" label-width="100px">
        <el-form-item label="版本名称" prop="name">
          <el-input
            v-model="versionFormData.name"
            placeholder="请输入版本名称，如：v1.0.0"
            @keyup.enter="handleVersionFormSubmit"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="versionFormData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入版本描述"
          />
        </el-form-item>
        <el-form-item label="基线版本">
          <el-switch
            v-model="versionFormData.is_baseline"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
        <el-form-item label="默认版本">
          <el-switch
            v-model="versionFormData.is_default"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionFormDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleVersionFormSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="testpointDefectDialogVisible"
      title="关联缺陷"
      width="560px"
      @close="closeTestpointDefectDialog"
    >
      <div v-loading="testpointDefectDialogLoading">
        <el-form label-width="90px">
          <el-form-item label="测试点ID">
            <span>{{ currentTestpointDefectRow?.id || '-' }}</span>
          </el-form-item>
          <el-form-item label="测试点">
            <span>{{ currentTestpointDefectRow?.node_text || '-' }}</span>
          </el-form-item>
          <el-form-item label="关联缺陷" required>
            <el-select
              v-model="testpointDefectForm.defectId"
              placeholder="请选择缺陷"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="item in testpointDefectOptions"
                :key="item.id"
                :label="`${item.code} - ${item.title}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <el-empty
          v-if="!testpointDefectDialogLoading && !testpointDefectOptions.length"
          description="当前需求下暂无可关联缺陷"
        />
      </div>
      <template #footer>
        <el-button @click="closeTestpointDefectDialog">取消</el-button>
        <el-button type="primary" :loading="testpointDefectDialogSaving" @click="handleSaveTestpointDefect">
          确定
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="devSelfTestDrawerVisible"
      :title="devSelfTestDrawerTitle"
      direction="rtl"
      size="680px"
      :destroy-on-close="false"
      class="dev-self-test-drawer"
      @closed="handleDevSelfTestDrawerClosed"
    >
      <div v-loading="devSelfTestDrawerLoading" class="dev-self-test-drawer__body">
        <el-descriptions :column="2" border size="small" class="dev-self-test-drawer__summary">
          <el-descriptions-item label="脑图名称">
            {{ devSelfTestEditForm.mindmap_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="模块路径">
            {{ devSelfTestEditForm.module_path || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="测试点" :span="2">
            {{ devSelfTestEditForm.testpoint || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-form label-position="top" class="dev-self-test-drawer__form">
          <el-form-item label="前置条件">
            <el-input
              v-model="devSelfTestEditForm.preconditions"
              type="textarea"
              readonly
              :autosize="getDevSelfTestTextareaAutosize(devSelfTestEditForm.preconditions, { minRows: 4, maxRows: 8 })"
            />
          </el-form-item>
          <el-form-item label="测试步骤">
            <el-input
              v-model="devSelfTestEditForm.steps"
              type="textarea"
              :autosize="getDevSelfTestTextareaAutosize(devSelfTestEditForm.steps, { minRows: 4, maxRows: 10 })"
              placeholder="请输入测试步骤"
            />
          </el-form-item>
          <el-form-item label="期望结果">
            <el-input
              v-model="devSelfTestEditForm.expected_result"
              type="textarea"
              readonly
              :autosize="getDevSelfTestTextareaAutosize(devSelfTestEditForm.expected_result, { minRows: 3, maxRows: 6 })"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input
              v-model="devSelfTestEditForm.remark"
              type="textarea"
              :autosize="getDevSelfTestTextareaAutosize(devSelfTestEditForm.remark, { minRows: 3, maxRows: 8 })"
              placeholder="请输入备注"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="devSelfTestEditForm.status" placeholder="请选择状态" style="width: 100%">
              <el-option
                v-for="option in statusOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <div class="dev-self-test-drawer__footer">
          <el-button @click="devSelfTestDrawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="devSelfTestDrawerSaving" @click="handleSaveDevSelfTest">
            保存
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Files, Plus, Search, Refresh, Edit, View, Delete, Upload } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { importManualCategoriesFromXMind } from '@/api/testcases'
import DefectList from '@/views/manual-testcases/DefectList.vue'
import VersionDefectAnalysisPanel from '@/views/manual-testcases/VersionDefectAnalysisPanel.vue'
import TechnicalSolutionDesignList from '@/views/manual-testcases/TechnicalSolutionDesignList.vue'
import ManualQualityKnowledgeAssistant from '@/views/manual-testcases/ManualQualityKnowledgeAssistant.vue'
import ManualPageListConfigPanel from '@/views/manual-testcases/ManualPageListConfigPanel.vue'
import ResearchProgressOverviewPanel from '@/views/manual-testcases/ResearchProgressOverviewPanel.vue'
import VersionRequirementList from '@/views/manual-testcases/VersionRequirementList.vue'
import QualityAnalysisReportDetailPanel from '@/views/quality-analysis/QualityAnalysisReportDetailPanel.vue'
import QualityAnalysisReportListPanel from '@/views/quality-analysis/QualityAnalysisReportListPanel.vue'
import QualityAnalysisJiraData from '@/views/quality-analysis/QualityAnalysisJiraData.vue'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import DefectNotificationSettings from '@/views/manual-testcases/DefectNotificationSettings.vue'
import GroupManagementPanel from '@/views/manual-testcases/GroupManagementPanel.vue'
import KnowledgeRepositoryConfigPanel from '@/views/manual-testcases/KnowledgeRepositoryConfigPanel.vue'
import ManualConfiguredFilterForm from '@/views/manual-testcases/ManualConfiguredFilterForm.vue'
import ManualWorkspaceSectionTabs from '@/views/manual-testcases/ManualWorkspaceSectionTabs.vue'
import ManualWorkspaceContextToolbar from '@/views/manual-testcases/ManualWorkspaceContextToolbar.vue'
import ManualWorkspaceDirectoryPanel from '@/views/manual-testcases/ManualWorkspaceDirectoryPanel.vue'
import MemberManagementPanel from '@/views/manual-testcases/MemberManagementPanel.vue'
import PermissionManagementPanel from '@/views/manual-testcases/PermissionManagementPanel.vue'
import ProjectAssetInsightPanel from '@/views/manual-testcases/ProjectAssetInsightPanel.vue'
import ProjectEnvironmentPanel from '@/views/manual-testcases/ProjectEnvironmentPanel.vue'
import ProjectManagementPanel from '@/views/manual-testcases/ProjectManagementPanel.vue'
import RoleManagementPanel from '@/views/manual-testcases/RoleManagementPanel.vue'
import VersionManagementPanel from '@/views/manual-testcases/VersionManagementPanel.vue'
import { getDefectDetail, getDefects, patchDefect } from '@/api/defects'
import { useUserStore } from '@/stores/user'
import { ensureUniqueDefectRelationItems, serializeDefectRelationItems } from '@/utils/defectRelations'
import {
  PERMISSION_CODES,
  isManualTestcaseSectionAccessible,
  isManualTestcaseTabAccessible,
  resolveAuthorizedManualTestcaseTab,
} from '@/utils/permissions'
import {
  buildTableFilters,
  compareTableNumber,
  createDateSorter,
  createNumberSorter,
  createTableFilter,
  createTextSorter,
} from '@/utils/tableUtils'
import { buildActionColumnWidth } from '@/utils/actionColumnWidth'
import { fetchAllGroupOptions } from '@/utils/groupOptions'
import { fetchRoleMemberOptions } from '@/utils/roleOptions'
import {
  buildManualTestcaseSectionLocation,
  getManualTestcasePrimaryTab,
  getManualTestcaseSectionDef,
  getManualTestcaseSectionsByPrimary,
  getManualTestcaseWorkspaceSectionsByPrimary,
} from '@/utils/manualTestcaseWorkspace'
import { getUserDisplayName as resolveUserDisplayName } from '@/utils/userDisplay'
import { defectStatusTagTypes } from '@/utils/defectStatus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const MANUAL_TABS = new Set(['mindmaps', 'testcases', 'testpoints', 'devselftest'])
const REPORT_TABS = new Set(['quality-report-list', 'quality-report-live'])
const NOTIFICATION_TABS = new Set(['email-config', 'email-template-config', 'notification-settings'])
const VERSION_LINKED_TABS = new Set([
  'bug-records',
  'version-requirements',
  'requirement-records',
  'version-defect-analysis',
  'version-defects',
  'technical-solution-designs',
])
const AVAILABLE_TABS = new Set([
  'mindmaps',
  'testcases',
  'testpoints',
  'devselftest',
  'quality-knowledge-assistant',
  'requirement-overview',
  'quality-report-list',
  'quality-report-live',
  'bug-records',
  'version-defect-analysis',
  'version-defects',
  'technical-solution-designs',
  'version-requirements',
  'requirement-records',
  'project-environments',
  'knowledge-repositories',
  'project-asset-insight',
  'configs',
  'other-settings',
  'email-config',
  'email-template-config',
  'notification-settings',
  'list-sort-config',
  'members',
  'groups',
  'roles',
  'projects',
  'versions',
  'permissions'
])

const MINDMAP_FILTER_FIELD_ID = 'prop:id'
const MINDMAP_FILTER_FIELD_REQUIREMENT_KEY = 'prop:requirement_key'
const MINDMAP_FILTER_FIELD_REQUIREMENT_TITLE = 'prop:requirement_title'
const MINDMAP_FILTER_FIELD_MODULE = 'prop:module'
const MINDMAP_FILTER_FIELD_NAME = 'prop:name'
const MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP = 'prop:responsibility_group'
const MINDMAP_FILTER_FIELD_FRONTEND = 'prop:frontend_name'
const MINDMAP_FILTER_FIELD_BACKEND = 'prop:backend_name'
const MINDMAP_FILTER_FIELD_AUTHOR = 'prop:author'
const MINDMAP_FILTER_FIELD_EXECUTOR = 'prop:executor'
const MINDMAP_FILTER_FIELD_VERSION = 'prop:version'
const MINDMAP_FILTER_FIELD_CREATED_AT = 'prop:created_at'
const MINDMAP_FILTER_FIELD_UPDATED_AT = 'prop:updated_at'

const mindmapFallbackFieldsRegistry = Object.freeze([
  { field_key: MINDMAP_FILTER_FIELD_ID, label: 'ID', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_REQUIREMENT_KEY, label: '需求编号', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_REQUIREMENT_TITLE, label: '需求标题', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_MODULE, label: '模块', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_NAME, label: '脑图名称', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP, label: '组别', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_FRONTEND, label: '前端', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_BACKEND, label: '后端', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_AUTHOR, label: '创建人', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_EXECUTOR, label: '执行人', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_VERSION, label: '版本号', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_CREATED_AT, label: '创建时间', options: [] },
  { field_key: MINDMAP_FILTER_FIELD_UPDATED_AT, label: '更新时间', options: [] },
])

const mindmapFallbackFilterConditions = Object.freeze([
  { id: 'fallback-mindmap-id', field_key: MINDMAP_FILTER_FIELD_ID, filter_type: 'text', operator: 'contains', placeholder: '请输入脑图ID', enabled: true, order: 1 },
  { id: 'fallback-mindmap-name', field_key: MINDMAP_FILTER_FIELD_NAME, filter_type: 'text', operator: 'contains', placeholder: '请输入脑图名称', enabled: true, order: 2 },
  { id: 'fallback-mindmap-requirement', field_key: MINDMAP_FILTER_FIELD_REQUIREMENT_KEY, filter_type: 'text', operator: 'contains', placeholder: '请输入需求编号', enabled: true, order: 3 },
  { id: 'fallback-mindmap-group', field_key: MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP, filter_type: 'text', operator: 'contains', placeholder: '请输入组别', enabled: true, order: 4 },
])

const mindmapActionColumnWidth = buildActionColumnWidth([
  [
    { label: '编辑脑图', icon: true },
    '测试点',
  ],
  [
    '自测测试点',
    { label: '编辑', icon: true },
    { label: '删除', icon: true },
  ],
])
const testcaseActionColumnWidth = buildActionColumnWidth([[
  { label: '编辑脑图', icon: true },
  { label: '查看脑图', icon: true },
  '提缺陷',
]])
const testpointActionColumnWidth = buildActionColumnWidth([
  [
    { label: '编辑脑图', icon: true },
    '提缺陷',
  ],
  [
    '关联缺陷',
    '版本缺陷',
    '线上缺陷',
  ],
], {
  padding: 0,
  min: 240,
})
const devSelfTestActionColumnWidth = buildActionColumnWidth([[
  { label: '查看脑图', icon: true },
  '编辑',
  '提缺陷',
]])
const versionDialogActionColumnWidth = buildActionColumnWidth([[
  { label: '编辑', icon: true },
  { label: '删除', icon: true },
]])

// 目录树相关
const treeRef = ref(null)
const treeSearchText = ref('')
const categoryTree = ref([])
const currentCategory = ref(null)
const expandedCategoryKeys = ref([])
const categoryImporting = ref(false)
const workspaceProjects = ref([])
const workspaceProjectDefaultLoading = ref(false)
const NO_MODULE_CATEGORY_ID_PREFIX = '__jira_no_module__:'
const NO_MODULE_CATEGORY_LABEL = '无模块'
const normalizeText = value => String(value ?? '').trim()
const firstText = (...values) => {
  for (const value of values) {
    const normalized = normalizeText(value)
    if (normalized) {
      return normalized
    }
  }
  return ''
}
const getSingleQueryValue = value => (Array.isArray(value) ? value[0] : value)
const isAllRouteValue = value => String(getSingleQueryValue(value) ?? '').trim().toLowerCase() === 'all'
const parseRouteId = value => {
  const rawValue = getSingleQueryValue(value)

  if (rawValue === undefined || rawValue === null || rawValue === '' || rawValue === 'all') {
    return null
  }

  const parsedValue = Number(rawValue)
  if (Number.isNaN(parsedValue) || parsedValue <= 0) {
    return null
  }

  return parsedValue
}

const isVirtualCategoryNode = category => Boolean(category?.isVirtual)
const getCurrentCategoryRouteId = () => {
  const categoryId = currentCategory.value?.id
  if (categoryId === undefined || categoryId === null || categoryId === '') {
    return ''
  }
  return String(categoryId)
}
const getCurrentRealCategoryId = () => (isVirtualCategoryNode(currentCategory.value) ? null : currentCategory.value?.id ?? null)

const resolveWorkspaceProjectId = projectId => {
  if (!projectId) {
    return null
  }

  return workspaceProjects.value.some(item => String(item.id) === String(projectId))
    ? projectId
    : null
}

const getWorkspaceProjectDataScore = project => {
  const versionCount = Number(project?.version_count || 0)
  const categoryCount = Number(project?.manual_category_count || 0)
  const mindmapCount = Number(project?.mindmap_count || 0)

  return (mindmapCount * 10000) + (categoryCount * 100) + versionCount
}

const defaultWorkspaceProject = computed(() => (
  workspaceProjects.value.find(item => item?.is_default) || null
))
const defaultWorkspaceVersion = computed(() => (
  versionList.value.find(item => item?.is_default) || null
))

const selectedWorkspaceProject = computed(() => {
  if (!currentProjectId.value) {
    return null
  }

  return workspaceProjects.value.find(item => String(item?.id) === String(currentProjectId.value)) || null
})

const canSetDefaultWorkspaceProject = computed(() => (
  userStore.hasPermissionCode(PERMISSION_CODES.manualTestcases.projectEdit)
))

const preferredWorkspaceProject = computed(() => {
  if (!workspaceProjects.value.length) {
    return null
  }

  return [...workspaceProjects.value].sort((left, right) => {
    const scoreDiff = getWorkspaceProjectDataScore(right) - getWorkspaceProjectDataScore(left)
    if (scoreDiff !== 0) {
      return scoreDiff
    }

    return String(left?.name || '').localeCompare(String(right?.name || ''), 'zh-CN')
  })[0]
})

const currentProjectId = computed(() => {
  const routeProjectId = resolveWorkspaceProjectId(parseRouteId(route.query.project_id))
  if (routeProjectId) {
    return routeProjectId
  }

  if (defaultWorkspaceProject.value?.id) {
    return defaultWorkspaceProject.value.id
  }

  return preferredWorkspaceProject.value?.id || workspaceProjects.value[0]?.id || null
})

const treeProps = {
  children: 'children',
  label: 'label'
}

const currentRealCategoryId = computed(() => getCurrentRealCategoryId())
const currentRealCategoryLabel = computed(() => (
  isVirtualCategoryNode(currentCategory.value) ? '' : currentCategory.value?.label ?? ''
))
const currentRealCategoryPath = computed(() => (
  isVirtualCategoryNode(currentCategory.value) ? '' : currentCategory.value?.fullPath ?? ''
))

const createNoModuleCategoryNode = parentNode => ({
  id: `${NO_MODULE_CATEGORY_ID_PREFIX}${parentNode.id ?? 'root'}`,
  label: NO_MODULE_CATEGORY_LABEL,
  description: 'JIRA需求模块为空',
  parentId: parentNode.id ?? null,
  fullPath: `${parentNode.fullPath || parentNode.label} / ${NO_MODULE_CATEGORY_LABEL}`,
  isVirtual: true,
  children: [],
})

const attachNoModuleCategoryNodes = nodes =>
  nodes.map(node => {
    const children = attachNoModuleCategoryNodes(node.children || [])

    if (node.parentId !== null) {
      return {
        ...node,
        children,
      }
    }

    const hasNoModuleNode = children.some(child => child.isVirtual && child.label === NO_MODULE_CATEGORY_LABEL)

    return {
      ...node,
      children: hasNoModuleNode ? children : [...children, createNoModuleCategoryNode(node)],
    }
  })

const findCategoryNode = (nodes, matcher) => {
  for (const node of nodes) {
    if (matcher(node)) {
      return node
    }

    if (node.children?.length) {
      const matchedChild = findCategoryNode(node.children, matcher)
      if (matchedChild) {
        return matchedChild
      }
    }
  }

  return null
}

const findCategoryPath = (nodes, matcher, ancestors = []) => {
  for (const node of nodes) {
    const currentPath = [...ancestors, node]
    if (matcher(node)) return currentPath
    const childPath = findCategoryPath(node.children || [], matcher, currentPath)
    if (childPath.length) return childPath
  }
  return []
}

const resetAllPaginationPages = () => {
  mindmapPagination.page = 1
  testcasePagination.page = 1
  testpointPagination.page = 1
  devSelfTestPagination.page = 1
}

// 目录对话框
const categoryDialogVisible = ref(false)
const categoryDialogTitle = ref('添加目录')
const categoryFormRef = ref(null)
const categoryFormData = reactive({
  id: null,
  name: '',
  description: '',
  parentId: null
})

const categoryFormRules = {
  name: [
    { required: true, message: '请输入目录名称', trigger: 'blur' }
  ]
}

// 版本管理对话框
const versionDialogVisible = ref(false)
const versionFormDialogVisible = ref(false)
const versionFormTitle = ref('添加版本')
const versionFormRef = ref(null)
const versionFormData = reactive({
  id: null,
  name: '',
  description: '',
  is_baseline: false,
  is_default: false
})

const versionFormRules = {
  name: [
    { required: true, message: '请输入版本名称', trigger: 'blur' }
  ]
}

// 各标签页筛选条件
const mindmapFilters = reactive({
  id: '',
  keyword: '',
  requirementKey: '',
  requirementTitle: '',
  nameKeyword: '',
  module: '',
  frontendName: '',
  backendName: '',
  authorId: null,
  authorName: '',
  executor: '',
  versionName: '',
  createdAt: '',
  updatedAt: '',
  responsibilityGroup: '',
})

const testcaseFilters = reactive({
  keyword: '',
  mindmapName: '',
  responsibilityGroup: '',
  authorId: null,
  priority: null,
  status: ''
})

const testpointFilters = reactive({
  keyword: '',
  requirementKey: '',
  mindmapId: '',
  mindmapName: '',
  tag: '',
  status: '',
  responsibilityGroup: '',
  authorId: null
})

const devSelfTestFilters = reactive({
  mindmapName: '',
  requirementKey: '',
  requirementTitle: '',
  status: '',
  responsibilityGroup: '',
  frontendDeveloperId: null,
  backendDeveloperId: null
})

const createDefaultDevSelfTestEditForm = () => ({
  id: '',
  mindmap_id: null,
  mindmap_name: '',
  module_path: '',
  testpoint: '',
  preconditions: '',
  steps: '',
  expected_result: '',
  remark: '',
  status: 'not_run'
})

const isTabAccessible = tab => AVAILABLE_TABS.has(tab) && isManualTestcaseTabAccessible(tab, userStore.hasPermissionCode)
const resolveWorkspaceTab = tab => resolveAuthorizedManualTestcaseTab(tab, userStore.hasPermissionCode)
const accessibleTabSet = computed(() => new Set([...AVAILABLE_TABS].filter(tab => isTabAccessible(tab))))
const activeTab = ref(resolveWorkspaceTab('mindmaps') || 'mindmaps')
const activePrimaryTab = computed(() => getManualTestcasePrimaryTab(activeTab.value))
const visibleWorkspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary(activePrimaryTab.value)
    .filter(item => !item.hidden)
    .filter(item => !(activePrimaryTab.value === 'overview' && item.name === 'requirement-overview'))
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))
const mindmapTableData = ref([])
const mindmapTableRef = ref(null)
const mindmapSelectedRows = ref([])
const mindmapCreators = ref([]) // 存储当前筛选条件下的所有创建人
const testcaseTableData = ref([])
const testcaseTableRef = ref(null)
const testcaseCreators = ref([]) // 存储测试用例的所有创建人
const testpointTableData = ref([])
const testpointTableRef = ref(null)
const testpointCreators = ref([]) // 存储测试点的所有创建人
const devSelfTestTableData = ref([])
const devSelfTestCreators = ref([]) // 存储自测测试点的所有创建人
const devSelfTestTableRef = ref(null)
const devSelfTestSelectedRows = ref([])
const devSelfTestDrawerVisible = ref(false)
const devSelfTestDrawerLoading = ref(false)
const devSelfTestDrawerSaving = ref(false)
const devSelfTestEditForm = reactive(createDefaultDevSelfTestEditForm())
const versionDialogTableRef = ref(null)
const testpointDefectDialogVisible = ref(false)
const testpointDefectDialogLoading = ref(false)
const testpointDefectDialogSaving = ref(false)
const testpointDefectOptions = ref([])
const currentTestpointDefectRow = ref(null)
const testpointDefectForm = reactive({
  defectId: '',
})
const visibleSecondaryTabs = computed(() => (
  new Set(getManualTestcaseWorkspaceSectionsByPrimary(activePrimaryTab.value).map(item => item.name))
))
const isPrimaryTabVisible = secondaryTab => accessibleTabSet.value.has(secondaryTab) && visibleSecondaryTabs.value.has(secondaryTab)
const devSelfTestDrawerTitle = computed(() => (
  devSelfTestEditForm.testpoint
    ? `编辑自测测试点 - ${devSelfTestEditForm.testpoint}`
    : '编辑自测测试点'
))

const mindmapPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const testcasePagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const testpointPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const devSelfTestPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const showDirectoryPanel = computed(() => (
  MANUAL_TABS.has(activeTab.value) ||
  REPORT_TABS.has(activeTab.value) ||
  VERSION_LINKED_TABS.has(activeTab.value)
))
const showCategoryTree = computed(() => (
  MANUAL_TABS.has(activeTab.value) ||
  REPORT_TABS.has(activeTab.value) ||
  activeTab.value === 'bug-records' ||
  activeTab.value === 'version-defect-analysis' ||
  activeTab.value === 'version-defects' ||
  activeTab.value === 'technical-solution-designs' ||
  activeTab.value === 'version-requirements' ||
  activeTab.value === 'requirement-records'
))
const isDirectoryCollapsed = ref(false)
const versionLinkedHint = computed(() => (
  activeTab.value === 'version-defect-analysis'
    ? '版本缺陷分析将根据左侧当前版本自动联动'
    : activeTab.value === 'version-defects'
    ? '版本缺陷将根据左侧当前版本和目录树自动联动'
    : activeTab.value === 'technical-solution-designs'
      ? '技术方案设计将根据左侧当前版本和目录树自动联动'
    : activeTab.value === 'bug-records'
      ? '线上缺陷将根据左侧当前版本和目录树自动联动'
    : activeTab.value === 'version-requirements'
      ? '版本需求将根据左侧当前版本和目录树自动联动'
    : activeTab.value === 'requirement-records'
      ? 'JIRA需求数据将根据左侧当前版本和目录树自动联动'
      : 'JIRA 数据将根据左侧当前版本自动联动'
))

const toggleDirectoryCollapsed = () => {
  if (!showDirectoryPanel.value) {
    return
  }

  isDirectoryCollapsed.value = !isDirectoryCollapsed.value
}

const priorityOptions = [
  { label: 'P1', value: 1 },
  { label: 'P2', value: 2 },
  { label: 'P3', value: 3 },
  { label: 'P4', value: 4 }
]

const statusOptions = [
  { label: '未执行', value: 'not_run' },
  { label: '通过', value: 'pass' },
  { label: '失败', value: 'fail' },
  { label: '阻塞', value: 'block' },
  { label: '本版本不测', value: 'not_test' }
]

const auditStatusOptions = [
  { label: '待审核', value: 'pending' },
  { label: '审核通过', value: 'approved' },
  { label: '审核驳回', value: 'rejected' }
]

// 版本列表和用户列表
const versionList = ref([])
const versionListLoading = ref(false)
const groupOptions = ref([])
const frontendDeveloperOptions = ref([])
const backendDeveloperOptions = ref([])
const executorOptions = ref([])
const currentVersionId = ref('all')  // 当前选中的版本号
const knowledgeProjectPopoverVisible = ref(false)
const knowledgeVersionPopoverVisible = ref(false)
const currentLinkedVersionName = computed(() => {
  if (!currentVersionId.value || currentVersionId.value === 'all') {
    return ''
  }

  const matchedVersion = versionList.value.find(item => String(item.id) === String(currentVersionId.value))
  return matchedVersion?.name || ''
})
const showKnowledgeAssistantContextMenu = computed(() => activeTab.value === 'quality-knowledge-assistant')
const buildAdaptiveSelectStyle = (text, {
  minWidth = 132,
  maxWidth = 320,
  characterWidth = 14,
  padding = 72,
} = {}) => {
  const content = String(text || '').trim()
  const width = Math.min(maxWidth, Math.max(minWidth, (content.length * characterWidth) + padding))

  return {
    width: `${width}px`
  }
}
const workspaceProjectSelectStyle = computed(() => (
  buildAdaptiveSelectStyle(selectedWorkspaceProject.value?.name || '请选择项目')
))
const workspaceVersionSelectStyle = computed(() => (
  buildAdaptiveSelectStyle(currentLinkedVersionName.value || '请选择版本号', {
    minWidth: 96,
    maxWidth: 220,
    characterWidth: 11,
    padding: 52,
  })
))
const linkedRequirementKeyword = computed(() => String(getSingleQueryValue(route.query.jira_keyword) || ''))
const linkedMindmapId = computed(() => String(getSingleQueryValue(route.query.mindmap_id) || ''))
const linkedMindmapKeyword = computed(() => String(getSingleQueryValue(route.query.mindmap_keyword) || ''))
const linkedMindmapRequirementKey = computed(() => String(getSingleQueryValue(route.query.mindmap_requirement_key) || ''))
const linkedTestpointKeyword = computed(() => String(getSingleQueryValue(route.query.testpoint_keyword) || ''))
const linkedTestpointMindmapId = computed(() => String(getSingleQueryValue(route.query.testpoint_mindmap_id) || ''))
const linkedTestpointRequirementKey = computed(() => String(getSingleQueryValue(route.query.testpoint_requirement_key) || ''))
const linkedDevSelfTestRequirementKey = computed(() => String(getSingleQueryValue(route.query.devselftest_requirement_key) || ''))
const linkedDefectKeyword = computed(() => (
  String(getSingleQueryValue(route.query.defect_keyword) || '') ||
  (activeTab.value === 'version-defects' ? String(getSingleQueryValue(route.query.keyword) || '') : '')
))
const linkedVersionDefectTestpointId = computed(() => String(getSingleQueryValue(route.query.defect_testpoint_id) || ''))
const linkedTechnicalSolutionDesignKeyword = computed(() => (
  String(getSingleQueryValue(route.query.technical_solution_design_keyword) || '') ||
  (activeTab.value === 'technical-solution-designs' ? String(getSingleQueryValue(route.query.keyword) || '') : '')
))
const linkedTechnicalSolutionDesignTestpointId = computed(() => (
  String(getSingleQueryValue(route.query.technical_solution_design_testpoint_id) || '')
))
const linkedBugKeyword = computed(() => (
  String(getSingleQueryValue(route.query.bug_keyword) || '') ||
  (activeTab.value === 'bug-records' ? String(getSingleQueryValue(route.query.keyword) || '') : '')
))
const linkedBugTestpointId = computed(() => String(getSingleQueryValue(route.query.bug_testpoint_id) || ''))
const collectCategoryLabels = (node, labels = []) => {
  if (!node) {
    return labels
  }

  const normalizedLabel = String(node.label || '').trim()
  if (normalizedLabel) {
    labels.push(normalizedLabel)
  }

  ;(node.children || []).forEach(child => {
    collectCategoryLabels(child, labels)
  })

  return labels
}

const buildLinkedJiraModules = category => {
  if (!category) {
    return []
  }

  if (isVirtualCategoryNode(category)) {
    return category.label === NO_MODULE_CATEGORY_LABEL ? [NO_MODULE_CATEGORY_LABEL] : []
  }

  if (category.parentId === null) {
    return []
  }

  return Array.from(new Set(collectCategoryLabels(category)))
}

const linkedJiraModules = computed(() => {
  return buildLinkedJiraModules(currentCategory.value)
})

const buildWorkspaceQuery = () => {
  const query = {
    ...route.query,
    tab: activeTab.value
  }
  ;['id', 'node_text', 'node_path', 'from_tab', 'return_query'].forEach(key => {
    delete query[key]
  })

  if (currentProjectId.value) {
    query.project_id = String(currentProjectId.value)
  } else {
    delete query.project_id
  }

  if (currentVersionId.value === 'all') {
    query.version_id = 'all'
  } else if (currentVersionId.value) {
    query.version_id = String(currentVersionId.value)
  } else {
    delete query.version_id
  }

  const categoryRouteId = getCurrentCategoryRouteId()
  if (categoryRouteId) {
    query.category_id = categoryRouteId
  } else {
    delete query.category_id
  }

  if (activeTab.value === 'mindmaps') {
    const normalizedMindmapId = String(mindmapFilters.id || '').trim()
    const normalizedMindmapKeyword = String(mindmapFilters.nameKeyword || '').trim()
    const normalizedMindmapRequirementKey = String(mindmapFilters.requirementKey || mindmapFilters.keyword || '').trim()
    const normalizedMindmapAuthorId = String(mindmapFilters.authorId || '').trim()
    const normalizedMindmapResponsibilityGroup = String(mindmapFilters.responsibilityGroup || '').trim()
    if (normalizedMindmapId) {
      query.mindmap_id = normalizedMindmapId
    } else {
      delete query.mindmap_id
    }
    if (normalizedMindmapKeyword) {
      query.mindmap_keyword = normalizedMindmapKeyword
    } else {
      delete query.mindmap_keyword
    }
    if (normalizedMindmapRequirementKey) {
      query.mindmap_requirement_key = normalizedMindmapRequirementKey
    } else {
      delete query.mindmap_requirement_key
    }
    if (normalizedMindmapAuthorId) {
      query.mindmap_author_id = normalizedMindmapAuthorId
    } else {
      delete query.mindmap_author_id
    }
    if (normalizedMindmapResponsibilityGroup) {
      query.mindmap_responsibility_group = normalizedMindmapResponsibilityGroup
    } else {
      delete query.mindmap_responsibility_group
    }
  } else {
    delete query.mindmap_id
    delete query.mindmap_keyword
    delete query.mindmap_requirement_key
    delete query.mindmap_author_id
    delete query.mindmap_responsibility_group
  }

  if (activeTab.value === 'testcases') {
    const normalizedTestcaseKeyword = String(testcaseFilters.keyword || '').trim()
    const normalizedTestcaseMindmapName = String(testcaseFilters.mindmapName || '').trim()
    const normalizedTestcaseResponsibilityGroup = String(testcaseFilters.responsibilityGroup || '').trim()
    const normalizedTestcaseAuthorId = String(testcaseFilters.authorId || '').trim()
    const normalizedTestcasePriority = testcaseFilters.priority === null || testcaseFilters.priority === undefined
      ? ''
      : String(testcaseFilters.priority).trim()
    const normalizedTestcaseStatus = String(testcaseFilters.status || '').trim()
    if (normalizedTestcaseKeyword) {
      query.testcase_keyword = normalizedTestcaseKeyword
    } else {
      delete query.testcase_keyword
    }
    if (normalizedTestcaseMindmapName) {
      query.testcase_mindmap_name = normalizedTestcaseMindmapName
    } else {
      delete query.testcase_mindmap_name
    }
    if (normalizedTestcaseResponsibilityGroup) {
      query.testcase_responsibility_group = normalizedTestcaseResponsibilityGroup
    } else {
      delete query.testcase_responsibility_group
    }
    if (normalizedTestcaseAuthorId) {
      query.testcase_author_id = normalizedTestcaseAuthorId
    } else {
      delete query.testcase_author_id
    }
    if (normalizedTestcasePriority) {
      query.testcase_priority = normalizedTestcasePriority
    } else {
      delete query.testcase_priority
    }
    if (normalizedTestcaseStatus) {
      query.testcase_status = normalizedTestcaseStatus
    } else {
      delete query.testcase_status
    }
  } else {
    delete query.testcase_keyword
    delete query.testcase_mindmap_name
    delete query.testcase_responsibility_group
    delete query.testcase_author_id
    delete query.testcase_priority
    delete query.testcase_status
  }

  if (activeTab.value === 'testpoints') {
    const normalizedTestpointKeyword = String(testpointFilters.keyword || '').trim()
    const normalizedTestpointMindmapId = String(testpointFilters.mindmapId || '').trim()
    const normalizedTestpointRequirementKey = String(testpointFilters.requirementKey || '').trim()
    const normalizedTestpointMindmapName = String(testpointFilters.mindmapName || '').trim()
    const normalizedTestpointTag = String(testpointFilters.tag || '').trim()
    const normalizedTestpointStatus = String(testpointFilters.status || '').trim()
    const normalizedTestpointResponsibilityGroup = String(testpointFilters.responsibilityGroup || '').trim()
    const normalizedTestpointAuthorId = String(testpointFilters.authorId || '').trim()
    if (normalizedTestpointKeyword) {
      query.testpoint_keyword = normalizedTestpointKeyword
    } else {
      delete query.testpoint_keyword
    }
    if (normalizedTestpointMindmapId) {
      query.testpoint_mindmap_id = normalizedTestpointMindmapId
    } else {
      delete query.testpoint_mindmap_id
    }
    if (normalizedTestpointRequirementKey) {
      query.testpoint_requirement_key = normalizedTestpointRequirementKey
    } else {
      delete query.testpoint_requirement_key
    }
    if (normalizedTestpointMindmapName) {
      query.testpoint_mindmap_name = normalizedTestpointMindmapName
    } else {
      delete query.testpoint_mindmap_name
    }
    if (normalizedTestpointTag) {
      query.testpoint_tag = normalizedTestpointTag
    } else {
      delete query.testpoint_tag
    }
    if (normalizedTestpointStatus) {
      query.testpoint_status = normalizedTestpointStatus
    } else {
      delete query.testpoint_status
    }
    if (normalizedTestpointResponsibilityGroup) {
      query.testpoint_responsibility_group = normalizedTestpointResponsibilityGroup
    } else {
      delete query.testpoint_responsibility_group
    }
    if (normalizedTestpointAuthorId) {
      query.testpoint_author_id = normalizedTestpointAuthorId
    } else {
      delete query.testpoint_author_id
    }
  } else {
    delete query.testpoint_keyword
    delete query.testpoint_mindmap_id
    delete query.testpoint_requirement_key
    delete query.testpoint_mindmap_name
    delete query.testpoint_tag
    delete query.testpoint_status
    delete query.testpoint_responsibility_group
    delete query.testpoint_author_id
  }

  if (activeTab.value === 'devselftest') {
    const normalizedDevSelfTestRequirementKey = String(devSelfTestFilters.requirementKey || '').trim()
    const normalizedDevSelfTestMindmapName = String(devSelfTestFilters.mindmapName || '').trim()
    const normalizedDevSelfTestRequirementTitle = String(devSelfTestFilters.requirementTitle || '').trim()
    const normalizedDevSelfTestStatus = String(devSelfTestFilters.status || '').trim()
    const normalizedDevSelfTestResponsibilityGroup = String(devSelfTestFilters.responsibilityGroup || '').trim()
    const normalizedDevSelfTestFrontendDeveloperId = String(devSelfTestFilters.frontendDeveloperId || '').trim()
    const normalizedDevSelfTestBackendDeveloperId = String(devSelfTestFilters.backendDeveloperId || '').trim()
    if (normalizedDevSelfTestRequirementKey) {
      query.devselftest_requirement_key = normalizedDevSelfTestRequirementKey
    } else {
      delete query.devselftest_requirement_key
    }
    if (normalizedDevSelfTestMindmapName) {
      query.devselftest_mindmap_name = normalizedDevSelfTestMindmapName
    } else {
      delete query.devselftest_mindmap_name
    }
    if (normalizedDevSelfTestRequirementTitle) {
      query.devselftest_requirement_title = normalizedDevSelfTestRequirementTitle
    } else {
      delete query.devselftest_requirement_title
    }
    if (normalizedDevSelfTestStatus) {
      query.devselftest_status = normalizedDevSelfTestStatus
    } else {
      delete query.devselftest_status
    }
    if (normalizedDevSelfTestResponsibilityGroup) {
      query.devselftest_responsibility_group = normalizedDevSelfTestResponsibilityGroup
    } else {
      delete query.devselftest_responsibility_group
    }
    if (normalizedDevSelfTestFrontendDeveloperId) {
      query.devselftest_frontend_developer = normalizedDevSelfTestFrontendDeveloperId
    } else {
      delete query.devselftest_frontend_developer
    }
    if (normalizedDevSelfTestBackendDeveloperId) {
      query.devselftest_backend_developer = normalizedDevSelfTestBackendDeveloperId
    } else {
      delete query.devselftest_backend_developer
    }
  } else {
    delete query.devselftest_requirement_key
    delete query.devselftest_mindmap_name
    delete query.devselftest_requirement_title
    delete query.devselftest_status
    delete query.devselftest_responsibility_group
    delete query.devselftest_frontend_developer
    delete query.devselftest_backend_developer
  }

  if (activeTab.value !== 'version-defects') {
    delete query.defect_keyword
    delete query.defect_testpoint_id
  } else if (!linkedVersionDefectTestpointId.value) {
    delete query.defect_testpoint_id
  }

  if (activeTab.value !== 'technical-solution-designs') {
    delete query.technical_solution_design_keyword
    delete query.technical_solution_design_testpoint_id
  } else if (!linkedTechnicalSolutionDesignTestpointId.value) {
    delete query.technical_solution_design_testpoint_id
  }

  if (activeTab.value !== 'bug-records') {
    delete query.bug_keyword
    delete query.bug_testpoint_id
  } else if (!linkedBugTestpointId.value) {
    delete query.bug_testpoint_id
  }

  return query
}

const replaceWorkspaceQuery = async (overrides = {}) => {
  const query = {
    ...route.query,
    ...overrides
  }

  Object.keys(query).forEach(key => {
    const value = query[key]

    if (value === undefined || value === null || value === '') {
      delete query[key]
    }
  })

  await router.replace({
    path: route.path,
    query
  })
}

const syncRouteDrivenFilters = (targetTab = activeTab.value) => {
  if (targetTab === 'mindmaps') {
    mindmapFilters.id = linkedMindmapId.value
    mindmapFilters.nameKeyword = linkedMindmapKeyword.value
    mindmapFilters.keyword = linkedMindmapRequirementKey.value
    mindmapFilters.requirementKey = linkedMindmapRequirementKey.value
    mindmapFilters.requirementTitle = ''
    mindmapFilters.module = ''
    mindmapFilters.frontendName = ''
    mindmapFilters.backendName = ''
    mindmapFilters.authorId = parseRouteId(route.query.mindmap_author_id)
    mindmapFilters.authorName = ''
    mindmapFilters.executor = ''
    mindmapFilters.versionName = ''
    mindmapFilters.createdAt = ''
    mindmapFilters.updatedAt = ''
    mindmapFilters.responsibilityGroup = String(getSingleQueryValue(route.query.mindmap_responsibility_group) || '')
  }

  if (targetTab === 'testcases') {
    testcaseFilters.keyword = String(getSingleQueryValue(route.query.testcase_keyword) || '')
    testcaseFilters.mindmapName = String(getSingleQueryValue(route.query.testcase_mindmap_name) || '')
    testcaseFilters.responsibilityGroup = String(getSingleQueryValue(route.query.testcase_responsibility_group) || '')
    testcaseFilters.authorId = parseRouteId(route.query.testcase_author_id)
    testcaseFilters.priority = parseRouteId(route.query.testcase_priority)
    testcaseFilters.status = String(getSingleQueryValue(route.query.testcase_status) || '')
  }

  if (targetTab === 'testpoints') {
    testpointFilters.keyword = linkedTestpointKeyword.value
    testpointFilters.mindmapId = linkedTestpointMindmapId.value
    testpointFilters.requirementKey = linkedTestpointRequirementKey.value
    testpointFilters.mindmapName = String(getSingleQueryValue(route.query.testpoint_mindmap_name) || '')
    testpointFilters.tag = String(getSingleQueryValue(route.query.testpoint_tag) || '')
    testpointFilters.status = String(getSingleQueryValue(route.query.testpoint_status) || '')
    testpointFilters.responsibilityGroup = String(getSingleQueryValue(route.query.testpoint_responsibility_group) || '')
    testpointFilters.authorId = parseRouteId(route.query.testpoint_author_id)
  }

  if (targetTab === 'devselftest') {
    devSelfTestFilters.requirementKey = linkedDevSelfTestRequirementKey.value
    devSelfTestFilters.mindmapName = String(getSingleQueryValue(route.query.devselftest_mindmap_name) || '')
    devSelfTestFilters.requirementTitle = String(getSingleQueryValue(route.query.devselftest_requirement_title) || '')
    devSelfTestFilters.status = String(getSingleQueryValue(route.query.devselftest_status) || '')
    devSelfTestFilters.responsibilityGroup = String(getSingleQueryValue(route.query.devselftest_responsibility_group) || '')
    devSelfTestFilters.frontendDeveloperId = parseRouteId(route.query.devselftest_frontend_developer)
    devSelfTestFilters.backendDeveloperId = parseRouteId(route.query.devselftest_backend_developer)
  }
}

const syncWorkspaceRouteQuery = async () => {
  await router.replace({
    path: route.path,
    query: buildWorkspaceQuery()
  })
}

const buildWorkspaceNavigationQuery = (targetTab, overrides = {}) => {
  const query = {
    ...route.query,
    tab: targetTab
  }

  if (currentProjectId.value) {
    query.project_id = String(currentProjectId.value)
  } else {
    delete query.project_id
  }

  if (currentVersionId.value === 'all') {
    query.version_id = 'all'
  } else if (currentVersionId.value) {
    query.version_id = String(currentVersionId.value)
  } else {
    delete query.version_id
  }

  const categoryRouteId = getCurrentCategoryRouteId()
  if (categoryRouteId) {
    query.category_id = categoryRouteId
  } else {
    delete query.category_id
  }

  ;[
    'code',
    'keyword',
    'status',
    'severity',
    'assignee_id',
    'page',
    'page_size',
    'testpoint_id',
    'mindmap_id',
    'mindmap_keyword',
    'mindmap_requirement_key',
    'mindmap_author_id',
    'mindmap_responsibility_group',
    'testcase_keyword',
    'testcase_mindmap_name',
    'testcase_responsibility_group',
    'testcase_author_id',
    'testcase_priority',
    'testcase_status',
    'testpoint_keyword',
    'testpoint_mindmap_id',
    'testpoint_requirement_key',
    'testpoint_mindmap_name',
    'testpoint_tag',
    'testpoint_status',
    'testpoint_responsibility_group',
    'testpoint_author_id',
    'devselftest_requirement_key',
    'devselftest_mindmap_name',
    'devselftest_requirement_title',
    'devselftest_status',
    'devselftest_responsibility_group',
    'devselftest_frontend_developer',
    'devselftest_backend_developer',
    'defect_keyword',
    'defect_testpoint_id',
    'technical_solution_design_keyword',
    'technical_solution_design_testpoint_id',
    'bug_keyword',
    'bug_testpoint_id',
  ].forEach(key => {
    delete query[key]
  })

  Object.assign(query, overrides)

  Object.keys(query).forEach(key => {
    const value = query[key]
    if (value === undefined || value === null || value === '') {
      delete query[key]
    }
  })

  return query
}

const buildDefectRouteQuery = (targetTab = activeTab.value) => {
  const query = {
    tab: targetTab,
    source: 'manual-testcases'
  }

  if (currentProjectId.value) {
    query.project_id = String(currentProjectId.value)
  }

  if (currentVersionId.value && currentVersionId.value !== 'all') {
    query.version_id = String(currentVersionId.value)
  }

  if (currentRealCategoryId.value) {
    query.category_id = String(currentRealCategoryId.value)
  }

  return query
}

const buildDefectDraftQuery = (extraQuery = {}) => {
  const query = {
    ...buildDefectRouteQuery(),
    ...extraQuery
  }

  Object.keys(query).forEach(key => {
    const value = query[key]

    if (value === undefined || value === null || value === '') {
      delete query[key]
      return
    }

    query[key] = String(value)
  })

  return query
}

const buildSourceDefectTitle = (sourceLabel, sourceName, mindmapName = '') => {
  const titleParts = [mindmapName, sourceName].filter(Boolean)
  const titleBody = titleParts.length ? titleParts.join(' - ') : '待补充标题'
  return `【${sourceLabel}】${titleBody}`
}

const getLastPathSegment = pathText =>
  String(pathText || '')
    .split(' / ')
    .map(item => item.trim())
    .filter(Boolean)
    .pop() || ''

const buildSelectedCategoryModulePath = category => {
  if (!category || isVirtualCategoryNode(category)) {
    return ''
  }

  const pathSegments = String(category?.fullPath || '')
    .split(' / ')
    .map(item => item.trim())
    .filter(Boolean)

  if (pathSegments.length <= 1) {
    return ''
  }

  return pathSegments.slice(1).join(' / ')
}

const getUserDisplayName = (user, fallback = '') => resolveUserDisplayName(user, fallback)
const currentUserDisplayName = computed(() => getUserDisplayName(userStore.user, ''))

const resetDevSelfTestEditForm = () => {
  Object.assign(devSelfTestEditForm, createDefaultDevSelfTestEditForm())
}

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('测试脑图')
const formRef = ref(null)
const formData = reactive({
  id: null,
  name: '',
  description: '',
  creator_name: '',
  executor_id: null,
  category_id: null,
  version_id: null,
  responsibility_group: '',
  frontend_developer_id: null,
  backend_developer_id: null,
  url: ''
})

const DEFAULT_MINDMAP_THEME = Object.freeze({
  template: 'default',
  theme: 'fresh-blue',
  version: '1.4.43'
})

const buildDefaultMindmapData = (name = '') => ({
  root: {
    data: {
      text: name,
      nodeType: 'module'
    },
    children: []
  },
  ...DEFAULT_MINDMAP_THEME
})

const cloneMindmapData = (data) => {
  if (!data) {
    return null
  }

  return JSON.parse(JSON.stringify(data))
}

const findUserOptionById = userId => {
  const normalizedId = Number(userId)
  if (!Number.isInteger(normalizedId) || normalizedId <= 0) {
    return null
  }

  const options = [
    userStore.user,
    ...executorOptions.value,
    ...frontendDeveloperOptions.value,
    ...backendDeveloperOptions.value,
    ...mindmapCreators.value,
  ]

  return options.find(user => Number(user?.id) === normalizedId) || null
}

const resolveMindmapCreator = mindmap => mindmap.author || findUserOptionById(mindmap.author_id) || userStore.user
const resolveMindmapExecutor = mindmap => mindmap.executor || findUserOptionById(mindmap.executor_id) || resolveMindmapCreator(mindmap)

const currentMindmapData = ref(buildDefaultMindmapData())
const xmindFileInputRef = ref(null)
const importedXMindName = ref('')
const importedXMindFile = ref(null)
const xmindImporting = ref(false)
const hasImportedXMind = computed(() => Boolean(importedXMindFile.value))

const populateMindmapForm = (mindmap = {}) => {
  const creator = resolveMindmapCreator(mindmap)
  const executor = resolveMindmapExecutor(mindmap)
  formData.id = mindmap.id ?? null
  formData.name = mindmap.name ?? ''
  formData.description = mindmap.description ?? ''
  formData.creator_name = getUserDisplayName(creator, currentUserDisplayName.value)
  formData.executor_id = executor?.id ?? creator?.id ?? null
  formData.category_id = mindmap.category_id ?? getCurrentRealCategoryId()
  formData.version_id = mindmap.version_id ?? null
  formData.responsibility_group = mindmap.responsibility_group ?? ''
  formData.frontend_developer_id = mindmap.frontend_developer_id ?? null
  formData.backend_developer_id = mindmap.backend_developer_id ?? null
  formData.url = mindmap.url ?? ''
  currentMindmapData.value = cloneMindmapData(mindmap.mindmap_data) || buildDefaultMindmapData(formData.name)
  importedXMindName.value = ''
  importedXMindFile.value = null
  if (xmindFileInputRef.value) {
    xmindFileInputRef.value.value = ''
  }
}

const resetMindmapForm = () => {
  populateMindmapForm({
    category_id: getCurrentRealCategoryId(),
    version_id: currentVersionId.value === 'all' ? null : currentVersionId.value
  })
  formRef.value?.clearValidate()
}

const formRules = {
  name: [
    {
      trigger: 'blur',
      validator: (_rule, value, callback) => {
        if (!formData.id && hasImportedXMind.value) {
          callback()
          return
        }

        if (String(value || '').trim()) {
          callback()
          return
        }

        callback(new Error('请输入脑图名称'))
      }
    }
  ]
}

// 监听搜索文本变化，过滤树节点
watch(treeSearchText, (val) => {
  treeRef.value?.filter(val)
})

// 过滤树节点
const filterNode = (value, data) => {
  if (!value) return true
  return data.label.includes(value)
}

// 目录树节点点击
const handleNodeClick = async (data) => {
  currentCategory.value = data
  console.log('选中目录:', data)
  resetAllPaginationPages()
  await syncWorkspaceRouteQuery()
  await loadActiveTabData()
}

// 加载目录树
const loadCategories = async (preferredCategoryId = null) => {
  if (!currentProjectId.value) {
    categoryTree.value = []
    currentCategory.value = null
    return
  }

  try {
    const response = await api.get('/testcases/manual-categories/', {
      params: {
        project: currentProjectId.value
      },
      timeout: 0
    })

    // 转换 API 返回的数据为树形结构
    const convertToTreeData = (categories, parentPath = []) => {
      return categories.map(category => ({
        id: category.id,
        label: category.name,
        description: category.description,
        parentId: category.parent,
        fullPath: [...parentPath, category.name].join(' / '),
        children: category.children ? convertToTreeData(category.children, [...parentPath, category.name]) : []
      }))
    }

    categoryTree.value = attachNoModuleCategoryNodes(convertToTreeData(response.data.results || response.data))
    const defaultExpandedRoot = findCategoryNode(
      categoryTree.value,
      node => node.parentId === null && node.label === '物业通'
    )
    const preferredPath = preferredCategoryId
      ? findCategoryPath(categoryTree.value, node => String(node.id) === String(preferredCategoryId))
      : []
    expandedCategoryKeys.value = [...new Set([
      ...(defaultExpandedRoot?.id ? [defaultExpandedRoot.id] : []),
      ...preferredPath.map(node => node.id).filter(Boolean)
    ])]
    const routeCategoryId = getSingleQueryValue(route.query.category_id)

    const selectedCategory =
      (preferredCategoryId && findCategoryNode(categoryTree.value, node => String(node.id) === String(preferredCategoryId))) ||
      (currentCategory.value?.id && findCategoryNode(categoryTree.value, node => String(node.id) === String(currentCategory.value.id))) ||
      (routeCategoryId && findCategoryNode(categoryTree.value, node => String(node.id) === String(routeCategoryId))) ||
      findCategoryNode(categoryTree.value, node => node.parentId === null && node.label === '物业通') ||
      categoryTree.value[0] ||
      null

    currentCategory.value = selectedCategory

    await nextTick()
    if (selectedCategory) {
      treeRef.value?.setCurrentKey(selectedCategory.id)
    }
  } catch (error) {
    console.error('加载目录失败:', error)
    ElMessage.error('加载目录失败')
  }
}

// 目录树节点右键菜单
const handleNodeContextmenu = (event, data) => {
  event.preventDefault()
  currentCategory.value = data
}

// 添加目录
const handleAddCategory = (command) => {
  categoryDialogTitle.value = command === 'root' ? '添加一级目录' : '添加子目录'
  categoryFormData.id = null
  categoryFormData.name = ''
  categoryFormData.description = ''
  categoryFormData.parentId = command === 'root' ? null : getCurrentRealCategoryId()
  categoryDialogVisible.value = true
}

const handleCategoryXMindImport = async file => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  if (!file) return

  categoryImporting.value = true
  try {
    const response = await importManualCategoriesFromXMind({
      projectId: currentProjectId.value,
      parentId: getCurrentRealCategoryId(),
      xmindFile: file
    })
    const importedRootId = response.data?.root_category?.id || null
    await loadCategories(importedRootId)
    resetAllPaginationPages()
    await syncWorkspaceRouteQuery()
    await loadActiveTabData()
    ElMessage.success(response.data?.message || 'XMind 目录导入成功')
  } catch (error) {
    const responseData = error.response?.data || {}
    const fileError = Array.isArray(responseData.xmind_file) ? responseData.xmind_file[0] : responseData.xmind_file
    ElMessage.error('导入 XMind 失败：' + (fileError || responseData.detail || error.message))
  } finally {
    categoryImporting.value = false
  }
}

// 编辑目录
const handleEditCategory = (data) => {
  categoryDialogTitle.value = '编辑目录'
  categoryFormData.id = data.id
  categoryFormData.name = data.label
  categoryFormData.description = data.description || ''
  categoryFormData.parentId = data.parentId
  categoryDialogVisible.value = true
}

// 删除目录
const handleDeleteCategory = (data) => {
  ElMessageBox.confirm('确定要删除该目录吗？删除后其子目录也将被删除。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/testcases/manual-categories/${data.id}/`)
      ElMessage.success('删除成功')
      await loadCategories()
      resetAllPaginationPages()
      await loadActiveTabData()
    } catch (error) {
      console.error('删除目录失败:', error)
      ElMessage.error('删除目录失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 提交目录表单
const handleCategorySubmit = async () => {
  categoryFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (categoryFormData.id) {
          // 编辑目录
          await api.put(`/testcases/manual-categories/${categoryFormData.id}/`, {
            name: categoryFormData.name,
            description: categoryFormData.description,
            parent_id: categoryFormData.parentId
          })
          ElMessage.success('编辑成功')
        } else {
          // 添加目录
          await api.post('/testcases/manual-categories/', {
            name: categoryFormData.name,
            description: categoryFormData.description,
            parent_id: categoryFormData.parentId,
            project_id: currentProjectId.value
          })
          ElMessage.success('添加成功')
        }

        await loadCategories()
        categoryDialogVisible.value = false
        resetAllPaginationPages()
        await loadActiveTabData()
      } catch (error) {
        console.error('保存目录失败:', error)
        ElMessage.error('保存目录失败：' + (error.response?.data?.detail || error.message))
      }
    }
  })
}

// 递归删除树节点
const removeNodeFromTree = (tree, id) => {
  for (let i = 0; i < tree.length; i++) {
    if (tree[i].id === id) {
      tree.splice(i, 1)
      return true
    }
    if (tree[i].children && tree[i].children.length > 0) {
      if (removeNodeFromTree(tree[i].children, id)) {
        return true
      }
    }
  }
  return false
}

// 递归更新树节点
const updateNodeInTree = (tree, id, name, description) => {
  for (let i = 0; i < tree.length; i++) {
    if (tree[i].id === id) {
      tree[i].label = name
      tree[i].description = description
      return true
    }
    if (tree[i].children && tree[i].children.length > 0) {
      if (updateNodeInTree(tree[i].children, id, name, description)) {
        return true
      }
    }
  }
  return false
}

// 递归添加树节点
const addNodeToTree = (tree, parentId, newNode) => {
  for (let i = 0; i < tree.length; i++) {
    if (tree[i].id === parentId) {
      if (!tree[i].children) {
        tree[i].children = []
      }
      tree[i].children.push(newNode)
      return true
    }
    if (tree[i].children && tree[i].children.length > 0) {
      if (addNodeToTree(tree[i].children, parentId, newNode)) {
        return true
      }
    }
  }
  return false
}

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) {
    return { results: data, count: data.length }
  }

  return {
    results: data?.results || [],
    count: data?.count ?? data?.results?.length ?? 0
  }
}

const buildBaseParams = (paginationState, extraParams = {}) => {
  const params = {
    page: paginationState.page,
    page_size: paginationState.pageSize,
    ...extraParams
  }

  if (currentProjectId.value) {
    params.project = currentProjectId.value
  }

  if (currentRealCategoryId.value) {
    params.category = currentRealCategoryId.value
  }

  return params
}

const buildMindmapParams = () => {
  const params = buildBaseParams(mindmapPagination)

  delete params.category

  if (currentRealCategoryId.value) {
    params.selected_category_id = currentRealCategoryId.value
  }

  if (currentRealCategoryLabel.value) {
    params.selected_category_name = currentRealCategoryLabel.value
  }

  if (mindmapFilters.nameKeyword) {
    params.mindmap_name = mindmapFilters.nameKeyword
  }

  if (mindmapFilters.id) {
    params.mindmap_id = String(mindmapFilters.id).trim()
  }

  if (mindmapFilters.authorId) {
    params.author = mindmapFilters.authorId
  } else if (mindmapFilters.authorName) {
    params.author_name = mindmapFilters.authorName
  }

  if (mindmapFilters.requirementKey) {
    params.requirement_key = mindmapFilters.requirementKey
  }

  if (mindmapFilters.requirementTitle) {
    params.requirement_title = mindmapFilters.requirementTitle
  }

  if (!mindmapFilters.requirementKey && !mindmapFilters.requirementTitle && mindmapFilters.keyword) {
    params.requirement_keyword = mindmapFilters.keyword
  }

  if (mindmapFilters.responsibilityGroup) {
    params.responsibility_group = mindmapFilters.responsibilityGroup
  }

  if (mindmapFilters.module) {
    params.module = mindmapFilters.module
  }

  if (mindmapFilters.frontendName) {
    params.frontend_name = mindmapFilters.frontendName
  }

  if (mindmapFilters.backendName) {
    params.backend_name = mindmapFilters.backendName
  }

  if (mindmapFilters.executor) {
    const executorId = Number(mindmapFilters.executor)
    if (Number.isInteger(executorId) && executorId > 0) {
      params.executor = executorId
    } else {
      params.executor_name = mindmapFilters.executor
    }
  }

  if (mindmapFilters.versionName) {
    const filterVersionId = Number(mindmapFilters.versionName)
    if (Number.isInteger(filterVersionId) && filterVersionId > 0) {
      params.version = filterVersionId
    } else {
      params.version_name = mindmapFilters.versionName
    }
  }

  const applyDateFilterParams = (value, paramName) => {
    if (Array.isArray(value)) {
      if (value[0]) {
        params[`${paramName}_start`] = value[0]
      }
      if (value[1]) {
        params[`${paramName}_end`] = value[1]
      }
    } else if (value) {
      params[paramName] = value
    }
  }

  applyDateFilterParams(mindmapFilters.createdAt, 'created_at')
  applyDateFilterParams(mindmapFilters.updatedAt, 'updated_at')

  // 添加版本过滤
  if (currentVersionId.value && currentVersionId.value !== 'all') {
    params.version = currentVersionId.value
  }

  return params
}

const buildNodeParams = (paginationState, nodeType) => {
  const params = buildBaseParams(paginationState, { node_type: nodeType })
  const filters = nodeType === 'case' ? testcaseFilters : testpointFilters

  delete params.category

  if (currentRealCategoryId.value) {
    params.selected_category_id = currentRealCategoryId.value
  }

  const selectedCategoryPath = buildSelectedCategoryModulePath(currentCategory.value)
  if (selectedCategoryPath) {
    params.selected_category_path = selectedCategoryPath
  }

  if (filters.keyword) {
    params.search = filters.keyword
  }

  if (nodeType === 'case') {
    if (filters.mindmapName) {
      params.mindmap_name = filters.mindmapName
    }
    if (filters.responsibilityGroup) {
      params.responsibility_group = filters.responsibilityGroup
    }
    if (filters.authorId) {
      params.author = filters.authorId
    }
    if (filters.priority !== null && filters.priority !== undefined && filters.priority !== '') {
      params.priority = filters.priority
    }
    if (filters.status) {
      params.status = filters.status
    }
  }

  if (nodeType === 'testpoint') {
    if (filters.mindmapId) {
      params.mindmap_id = filters.mindmapId
    }
    if (filters.requirementKey) {
      params.requirement_key = filters.requirementKey
    }
    if (filters.mindmapName) {
      params.mindmap_name = filters.mindmapName
    }
    if (filters.tag) {
      params.tag = filters.tag
    }
    if (filters.status) {
      params.status = filters.status
    }
    if (filters.responsibilityGroup) {
      params.responsibility_group = filters.responsibilityGroup
    }
    if (filters.authorId) {
      params.author = filters.authorId
    }
  }

  // 添加版本过滤
  if (currentVersionId.value && currentVersionId.value !== 'all') {
    params.version = currentVersionId.value
  }

  return params
}

const loadMindmaps = async () => {
  try {
    const response = await api.get('/testcases/manual-mindmaps/', {
      params: buildMindmapParams()
    })
    const { results, count } = normalizeListResponse(response.data)

    // 提取创建人列表
    if (response.data.creators) {
      mindmapCreators.value = response.data.creators
    } else {
      mindmapCreators.value = []
    }

    mindmapTableData.value = results.map(item => {
      return {
        id: item.id,
        requirement_key: item.requirement_key,
        requirement_title: item.requirement_title,
        name: item.name,
        url: item.url,
        module: firstText(item.module),
        responsibility_group: firstText(item.requirement_group_name),
        frontend_name: firstText(item.requirement_frontend_developer),
        backend_name: firstText(item.requirement_backend_developer),
        frontend_developer: item.frontend_developer,
        backend_developer: item.backend_developer,
        case_count: normalizeStatusCountValue(item.case_count),
        testpoint_count: normalizeStatusCountValue(item.testpoint_count),
        review_testpoint_count: item.review_testpoint_count || { unprocessed: 0, processed: 0, total: 0 },
        dev_self_test_count: normalizeStatusCountValue(item.dev_self_test_count),
        executor: getUserDisplayName(item.executor || item.author, '未知'),
        creator: getUserDisplayName(item.author, '未知'),
        version: item.version?.name || '-',
        created_at: formatDateTime(item.created_at),
        updated_at: formatDateTime(item.updated_at),
        project: item.project
      }
    })

    mindmapPagination.total = count
    mindmapSelectedRows.value = []
    await nextTick()
    mindmapTableRef.value?.clearSelection()
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载脑图数据失败：' + (error.response?.data?.detail || error.message))
  }
}

const loadNodeList = async (nodeType, tableRef, paginationState) => {
  try {
    const response = await api.get('/testcases/manual-mindmap-nodes/', {
      params: buildNodeParams(paginationState, nodeType)
    })
    const { results, count } = normalizeListResponse(response.data)

    // 提取创建人列表
    if (response.data.creators) {
      if (nodeType === 'case') {
        testcaseCreators.value = response.data.creators
      } else if (nodeType === 'testpoint') {
        testpointCreators.value = response.data.creators
      }
    } else {
      if (nodeType === 'case') {
        testcaseCreators.value = []
      } else if (nodeType === 'testpoint') {
        testpointCreators.value = []
      }
    }

    tableRef.value = results.map(item => ({
      ...item,
      creator: getUserDisplayName(item.author, '未知'),
      review_opinion: item.review_opinion || '',
      reviewer_id: item.reviewer_id ?? null,
      reviewer_name: item.reviewer_name || '',
      review_time: item.review_time || '',
      review_status: item.review_status || '',
      created_at: formatDateTime(item.created_at),
      updated_at: formatDateTime(item.updated_at)
    }))
    paginationState.total = count
  } catch (error) {
    console.error('加载节点数据失败:', error)
    ElMessage.error('加载节点数据失败：' + (error.response?.data?.detail || error.message))
  }
}

const loadDevSelfTest = async () => {
  try {
    const params = buildBaseParams(devSelfTestPagination)

    if (currentVersionId.value && currentVersionId.value !== 'all') {
      params.version = currentVersionId.value
    }

    if (devSelfTestFilters.mindmapName) {
      params.mindmap_name = devSelfTestFilters.mindmapName
    }
    if (devSelfTestFilters.requirementKey) {
      params.requirement_key = devSelfTestFilters.requirementKey
    }
    if (devSelfTestFilters.requirementTitle) {
      params.requirement_title = devSelfTestFilters.requirementTitle
    }
    if (devSelfTestFilters.status) {
      params.status = devSelfTestFilters.status
    }
    if (devSelfTestFilters.responsibilityGroup) {
      params.responsibility_group = devSelfTestFilters.responsibilityGroup
    }
    if (devSelfTestFilters.frontendDeveloperId) {
      params.frontend_developer = devSelfTestFilters.frontendDeveloperId
    }
    if (devSelfTestFilters.backendDeveloperId) {
      params.backend_developer = devSelfTestFilters.backendDeveloperId
    }

    const response = await api.get('/testcases/dev-self-test/', { params })
    const { results, count } = normalizeListResponse(response.data)

    // 提取创建人列表
    if (response.data.creators) {
      devSelfTestCreators.value = response.data.creators
    } else {
      devSelfTestCreators.value = []
    }

    devSelfTestTableData.value = results.map(item => ({
      ...item,
      created_at: formatDateTime(item.created_at),
      updated_at: formatDateTime(item.updated_at)
    }))
    devSelfTestPagination.total = count
    devSelfTestSelectedRows.value = []
    await nextTick()
    devSelfTestTableRef.value?.clearSelection()
  } catch (error) {
    console.error('加载开发自测数据失败:', error)
    ElMessage.error('加载开发自测数据失败：' + (error.response?.data?.detail || error.message))
  }
}

const getDevSelfTestNodeId = row => {
  const nodeId = row?.id ?? row?.node_id ?? ''
  return String(nodeId || '').trim()
}

const getDevSelfTestTextareaAutosize = (value, emptyAutosize) => {
  const hasValue = String(value || '').trim().length > 0
  if (!hasValue) {
    return emptyAutosize
  }

  return { minRows: emptyAutosize.minRows }
}

const loadDevSelfTestDetail = async (row) => {
  devSelfTestDrawerLoading.value = true

  try {
    const response = await api.get('/testcases/dev-self-test/detail/', {
      params: {
        mindmap_id: row.mindmap_id,
        node_id: getDevSelfTestNodeId(row)
      }
    })

    Object.assign(devSelfTestEditForm, createDefaultDevSelfTestEditForm(), response.data, {
      status: response.data?.status || 'not_run'
    })
  } catch (error) {
    console.error('加载自测测试点详情失败:', error)
    ElMessage.error('加载自测测试点详情失败：' + (error.response?.data?.detail || error.message))
    throw error
  } finally {
    devSelfTestDrawerLoading.value = false
  }
}

const handleEditDevSelfTest = async (row) => {
  if (!row.can_edit) {
    ElMessage.warning('请先完成审核通过，再进行编辑')
    return
  }

  resetDevSelfTestEditForm()
  Object.assign(devSelfTestEditForm, {
    id: getDevSelfTestNodeId(row),
    mindmap_id: row.mindmap_id,
    mindmap_name: row.mindmap_name,
    module_path: row.module_path,
    testpoint: row.testpoint,
    status: row.status || 'not_run'
  })
  devSelfTestDrawerVisible.value = true

  try {
    await loadDevSelfTestDetail(row)
  } catch (error) {
    devSelfTestDrawerVisible.value = false
  }
}

const handleSaveDevSelfTest = async () => {
  if (!devSelfTestEditForm.mindmap_id || !devSelfTestEditForm.id) {
    ElMessage.warning('当前自测测试点信息不完整')
    return
  }

  devSelfTestDrawerSaving.value = true
  try {
    const response = await api.patch(
      '/testcases/dev-self-test/detail/',
      {
        steps: devSelfTestEditForm.steps,
        remark: devSelfTestEditForm.remark,
        status: devSelfTestEditForm.status || 'not_run'
      },
      {
        params: {
          mindmap_id: devSelfTestEditForm.mindmap_id,
          node_id: devSelfTestEditForm.id
        }
      }
    )

    Object.assign(devSelfTestEditForm, createDefaultDevSelfTestEditForm(), response.data, {
      status: response.data?.status || 'not_run'
    })
    ElMessage.success('保存成功')
    devSelfTestDrawerVisible.value = false
    await loadDevSelfTest()
  } catch (error) {
    console.error('保存自测测试点失败:', error)
    ElMessage.error('保存自测测试点失败：' + (error.response?.data?.detail || error.message))
  } finally {
    devSelfTestDrawerSaving.value = false
  }
}

const handleDevSelfTestDrawerClosed = () => {
  devSelfTestDrawerLoading.value = false
  devSelfTestDrawerSaving.value = false
  resetDevSelfTestEditForm()
}

const handleDevSelfTestSelectionChange = rows => {
  devSelfTestSelectedRows.value = rows
}

const handleDevSelfTestAuditCommand = auditStatus => {
  if (!devSelfTestSelectedRows.value.length) {
    ElMessage.warning('请先选择要审核的自测测试点')
    return
  }

  const auditStatusLabel = formatAuditStatus(auditStatus)
  ElMessageBox.confirm(
    `确定将当前选中的 ${devSelfTestSelectedRows.value.length} 条自测测试点设置为“${auditStatusLabel}”吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await api.post('/testcases/dev-self-test/audit/', {
        audit_status: auditStatus,
        items: devSelfTestSelectedRows.value.map(row => ({
          mindmap_id: row.mindmap_id,
          node_id: getDevSelfTestNodeId(row)
        }))
      })
      ElMessage.success('审核完成')
      await loadDevSelfTest()
    } catch (error) {
      console.error('批量审核自测测试点失败:', error)
      ElMessage.error('批量审核失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    ElMessage.info('已取消审核')
  })
}

const getActivePagination = () => {
  if (activeTab.value === 'testcases') return testcasePagination
  if (activeTab.value === 'testpoints') return testpointPagination
  if (activeTab.value === 'devselftest') return devSelfTestPagination
  return mindmapPagination
}

const loadActiveTabData = async () => {
  if (!MANUAL_TABS.has(activeTab.value)) {
    return
  }

  if (activeTab.value === 'testcases') {
    await loadNodeList('case', testcaseTableData, testcasePagination)
    return
  }

  if (activeTab.value === 'testpoints') {
    await loadNodeList('testpoint', testpointTableData, testpointPagination)
    return
  }

  if (activeTab.value === 'devselftest') {
    await loadDevSelfTest()
    return
  }

  await loadMindmaps()
}

// 搜索和加载数据
const handleSearch = async () => {
  getActivePagination().page = 1
  await syncWorkspaceRouteQuery()
  await loadActiveTabData()
}

const handleTabChange = async () => {
  syncRouteDrivenFilters(activeTab.value)
  await syncWorkspaceRouteQuery()

  if (!MANUAL_TABS.has(activeTab.value)) {
    return
  }

  await loadGroupOptions()
  await loadActiveTabData()
}

const handleWorkspaceSectionSelect = async sectionName => {
  const sectionDef = getManualTestcaseSectionDef(sectionName)
  if (!sectionDef) {
    return
  }

  if (sectionDef.workspace) {
    if (sectionDef.name === activeTab.value) {
      return
    }

    activeTab.value = sectionDef.name
    await handleTabChange()
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionDef.name, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

watch(
  () => route.query.tab,
  async newTab => {
    const requestedTab = Array.isArray(newTab) ? newTab[0] : newTab
    const nextTab = resolveWorkspaceTab(requestedTab || activeTab.value)

    if (!nextTab || nextTab === activeTab.value) {
      return
    }

    activeTab.value = nextTab
    syncRouteDrivenFilters(nextTab)

    if (MANUAL_TABS.has(nextTab)) {
      await loadActiveTabData()
    }
  }
)

watch(
  () => route.query.mindmap_id,
  async newMindmapId => {
    if (activeTab.value !== 'mindmaps') {
      return
    }

    const nextMindmapId = String(getSingleQueryValue(newMindmapId) || '')
    if (mindmapFilters.id === nextMindmapId) {
      return
    }

    mindmapFilters.id = nextMindmapId
    mindmapPagination.page = 1
    await loadMindmaps()
  }
)

watch(
  () => route.query.mindmap_keyword,
  async newKeyword => {
    if (activeTab.value !== 'mindmaps') {
      return
    }

    const nextKeyword = String(getSingleQueryValue(newKeyword) || '')
    if (mindmapFilters.nameKeyword === nextKeyword) {
      return
    }

    mindmapFilters.nameKeyword = nextKeyword
    mindmapPagination.page = 1
    await loadMindmaps()
  }
)

watch(
  () => route.query.mindmap_requirement_key,
  async newRequirementKey => {
    if (activeTab.value !== 'mindmaps') {
      return
    }

    const nextRequirementKey = String(getSingleQueryValue(newRequirementKey) || '')
    if (mindmapFilters.keyword === nextRequirementKey) {
      return
    }

    mindmapFilters.keyword = nextRequirementKey
    mindmapPagination.page = 1
    await loadMindmaps()
  }
)

watch(
  () => route.query.testpoint_keyword,
  async newKeyword => {
    if (activeTab.value !== 'testpoints') {
      return
    }

    const nextKeyword = String(getSingleQueryValue(newKeyword) || '')
    if (testpointFilters.keyword === nextKeyword) {
      return
    }

    testpointFilters.keyword = nextKeyword
    testpointPagination.page = 1
    await loadNodeList('testpoint', testpointTableData, testpointPagination)
  }
)

watch(
  () => route.query.testpoint_mindmap_id,
  async newMindmapId => {
    if (activeTab.value !== 'testpoints') {
      return
    }

    const nextMindmapId = String(getSingleQueryValue(newMindmapId) || '')
    if (testpointFilters.mindmapId === nextMindmapId) {
      return
    }

    testpointFilters.mindmapId = nextMindmapId
    testpointPagination.page = 1
    await loadNodeList('testpoint', testpointTableData, testpointPagination)
  }
)

watch(
  () => route.query.testpoint_requirement_key,
  async newRequirementKey => {
    if (activeTab.value !== 'testpoints') {
      return
    }

    const nextRequirementKey = String(getSingleQueryValue(newRequirementKey) || '')
    if (testpointFilters.requirementKey === nextRequirementKey) {
      return
    }

    testpointFilters.requirementKey = nextRequirementKey
    testpointPagination.page = 1
    await loadNodeList('testpoint', testpointTableData, testpointPagination)
  }
)

watch(
  () => route.query.devselftest_requirement_key,
  async newRequirementKey => {
    if (activeTab.value !== 'devselftest') {
      return
    }

    const nextRequirementKey = String(getSingleQueryValue(newRequirementKey) || '')
    if (devSelfTestFilters.requirementKey === nextRequirementKey) {
      return
    }

    devSelfTestFilters.requirementKey = nextRequirementKey
    devSelfTestPagination.page = 1
    await loadDevSelfTest()
  }
)

const handleMindmapPageChange = async () => {
  await loadMindmaps()
}

const handleTestcasePageChange = async () => {
  await loadNodeList('case', testcaseTableData, testcasePagination)
}

const handleTestpointPageChange = async () => {
  await loadNodeList('testpoint', testpointTableData, testpointPagination)
}

const handleDevSelfTestPageChange = async () => {
  await loadDevSelfTest()
}

const handleVersionChange = async () => {
  // 重置所有分页
  resetAllPaginationPages()
  await syncWorkspaceRouteQuery()
  // 重新加载当前tab的数据
  await loadActiveTabData()
}

const buildTestpointRelationItem = row => ({
  id: String(row?.id || '').trim(),
  mindmap_id: row?.mindmap_id || null,
  mindmap_name: row?.mindmap_name || '',
  node_text: row?.node_text || '',
  node_type: 'testpoint',
  path: row?.path || '',
  parent_text: row?.parent_text || '',
  case_id: row?.case_id || '',
  responsibility_group: row?.responsibility_group || '',
})

const jumpToMindmapTestpoints = row => {
  const normalizedMindmapId = String(row?.id || row?.mindmap_id || '').trim()
  if (!normalizedMindmapId) {
    ElMessage.warning('当前脑图缺少脑图ID')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildWorkspaceNavigationQuery('testpoints', {
      testpoint_mindmap_id: normalizedMindmapId,
    }),
  })
}

const jumpToTestpointMindmap = row => {
  const normalizedMindmapId = String(row?.mindmap_id || '').trim()
  if (!normalizedMindmapId) {
    ElMessage.warning('当前测试点缺少脑图ID')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildWorkspaceNavigationQuery('mindmaps', {
      mindmap_id: normalizedMindmapId,
    }),
  })
}

const jumpToMindmapDevSelfTests = row => {
  if (!row?.requirement_key) {
    ElMessage.warning('当前脑图缺少需求编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildWorkspaceNavigationQuery('devselftest', {
      devselftest_requirement_key: row.requirement_key,
    }),
  })
}

const jumpToVersionDefectsByTestpoint = row => {
  if (!row?.id) {
    ElMessage.warning('当前测试点缺少ID')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildWorkspaceNavigationQuery('version-defects', {
      defect_testpoint_id: row.id,
    }),
  })
}

const jumpToBugRecordsByTestpoint = row => {
  if (!row?.id) {
    ElMessage.warning('当前测试点缺少ID')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildWorkspaceNavigationQuery('bug-records', {
      bug_testpoint_id: row.id,
    }),
  })
}

const closeTestpointDefectDialog = () => {
  testpointDefectDialogVisible.value = false
  testpointDefectDialogLoading.value = false
  testpointDefectDialogSaving.value = false
  testpointDefectForm.defectId = ''
  testpointDefectOptions.value = []
  currentTestpointDefectRow.value = null
}

const openTestpointDefectDialog = async row => {
  if (!row?.requirement_key) {
    ElMessage.warning('当前测试点缺少需求编号')
    return
  }

  currentTestpointDefectRow.value = row
  testpointDefectDialogVisible.value = true
  testpointDefectDialogLoading.value = true
  testpointDefectForm.defectId = ''
  testpointDefectOptions.value = []

  try {
    const params = {
      project: currentProjectId.value,
      requirement_id: row.requirement_key,
      page_size: 200,
      ordering: '-updated_at',
    }

    if (currentVersionId.value && currentVersionId.value !== 'all') {
      params.version = currentVersionId.value
    }

    const response = await getDefects(params)
    testpointDefectOptions.value = response.data?.results || []
  } catch (error) {
    ElMessage.error('加载可关联缺陷失败')
  } finally {
    testpointDefectDialogLoading.value = false
  }
}

const handleSaveTestpointDefect = async () => {
  if (!currentTestpointDefectRow.value?.id) {
    ElMessage.warning('当前测试点信息不完整')
    return
  }

  if (!testpointDefectForm.defectId) {
    ElMessage.warning('请选择要关联的缺陷')
    return
  }

  testpointDefectDialogSaving.value = true
  try {
    const detailResponse = await getDefectDetail(testpointDefectForm.defectId)
    const detail = detailResponse.data || {}
    const relatedTestpoints = ensureUniqueDefectRelationItems(
      [
        ...(detail.related_testpoints || []),
        buildTestpointRelationItem(currentTestpointDefectRow.value),
      ],
      'testpoint',
    )

    await patchDefect(testpointDefectForm.defectId, {
      related_testpoints: serializeDefectRelationItems(relatedTestpoints, 'testpoint'),
      retain_attachment_ids: (detail.attachments || []).map(item => item.id),
    })

    ElMessage.success('关联缺陷成功')
    closeTestpointDefectDialog()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '关联缺陷失败')
  } finally {
    testpointDefectDialogSaving.value = false
  }
}

const handleCreateTestcaseDefect = row => {
  router.push({
    path: '/manual-testcases/defects/create',
    query: buildDefectDraftQuery({
      title: buildSourceDefectTitle('测试用例', row.node_text, row.mindmap_name),
      source_tab_name: '测试用例',
      source_mindmap_id: row.mindmap_id,
      source_mindmap: row.mindmap_name,
      source_name: row.node_text,
      source_parent_name: row.parent_text,
      source_module: getLastPathSegment(row.module_path) || row.parent_text,
      source_module_path: row.module_path,
      source_path: row.path,
      source_case_id: row.case_id,
      source_node_id: row.id,
      source_responsibility_group: row.responsibility_group
    })
  })
}

const handleCreateTestpointDefect = row => {
  router.push({
    path: '/manual-testcases/defects/create',
    query: buildDefectDraftQuery({
      title: buildSourceDefectTitle('测试点', row.node_text, row.mindmap_name),
      source_tab_name: '测试点',
      source_mindmap_id: row.mindmap_id,
      source_mindmap: row.mindmap_name,
      source_name: row.node_text,
      source_parent_name: row.parent_text,
      source_module: getLastPathSegment(row.module_path) || row.parent_text,
      source_module_path: row.module_path,
      source_path: row.path,
      source_case_id: row.case_id,
      source_node_id: row.id,
      source_responsibility_group: row.responsibility_group
    })
  })
}

const handleCreateDevSelfTestDefect = row => {
  router.push({
    path: '/manual-testcases/defects/create',
    query: buildDefectDraftQuery({
      title: buildSourceDefectTitle('自测测试点', row.testpoint, row.mindmap_name),
      source_tab_name: '自测测试点',
      source_mindmap_id: row.mindmap_id,
      source_mindmap: row.mindmap_name,
      source_name: row.testpoint,
      source_module: getLastPathSegment(row.module_path) || row.module,
      source_module_path: row.module_path,
      source_responsibility_group: row.responsibility_group,
      source_frontend_owner: getUserDisplayName(row.frontend_developer),
      source_backend_owner: getUserDisplayName(row.backend_developer)
    })
  })
}

const handleManageVersions = async () => {
  versionDialogVisible.value = true
  await loadVersions()
}

const handleVersionDialogClose = () => {
  // 关闭对话框
}

const handleAddVersion = () => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目后再新增版本')
    return
  }

  versionFormTitle.value = '添加版本'
  versionFormData.id = null
  versionFormData.name = ''
  versionFormData.description = ''
  versionFormData.is_baseline = false
  versionFormData.is_default = false
  versionFormDialogVisible.value = true
}

const handleEditVersion = (row) => {
  versionFormTitle.value = '编辑版本'
  versionFormData.id = row.id
  versionFormData.name = row.name
  versionFormData.description = row.description
  versionFormData.is_baseline = row.is_baseline
  versionFormData.is_default = row.is_default
  versionFormDialogVisible.value = true
}

const handleDeleteVersion = (row) => {
  ElMessageBox.confirm(`确定要删除版本"${row.name}"吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/versions/${row.id}/`)
      ElMessage.success('删除成功')
      await loadVersions()
      // 如果删除的是当前选中的版本，切换到"全部"
      if (currentVersionId.value === row.id) {
        currentVersionId.value = 'all'
        await handleVersionChange()
      }
    } catch (error) {
      console.error('删除版本失败:', error)
      ElMessage.error('删除版本失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

const handleSetDefault = async (row) => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目后再设置默认版本')
    return
  }

  try {
    await api.put(`/versions/${row.id}/`, {
      name: row.name,
      description: row.description,
      is_baseline: row.is_baseline,
      is_default: true,
      project_ids: [currentProjectId.value]
    })
    ElMessage.success('设置默认版本成功')
    await loadVersions()
    currentVersionId.value = row.id
    await handleVersionChange()
  } catch (error) {
    console.error('设置默认版本失败:', error)
    ElMessage.error('设置默认版本失败：' + (error.response?.data?.detail || error.message))
  }
}

const handleVersionFormDialogClose = () => {
  versionFormRef.value?.resetFields()
}

const handleVersionFormSubmit = () => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目后再保存版本')
    return
  }

  versionFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const data = {
          name: versionFormData.name,
          description: versionFormData.description,
          is_baseline: versionFormData.is_baseline,
          is_default: versionFormData.is_default,
          project_ids: [currentProjectId.value]
        }

        if (versionFormData.id) {
          // 编辑版本
          await api.put(`/versions/${versionFormData.id}/`, data)
          ElMessage.success('编辑成功')
        } else {
          // 创建版本
          await api.post('/versions/', data)
          ElMessage.success('创建成功')
        }

        versionFormDialogVisible.value = false
        await loadVersions()
      } catch (error) {
        console.error('保存版本失败:', error)
        ElMessage.error('保存版本失败：' + (error.response?.data?.detail || error.message))
      }
    }
  })
}

const formatPriority = (priority) => {
  return priority ? `P${priority}` : '-'
}

const getTextCellContent = value => String(value || '').trim()

const formatTextCell = value => getTextCellContent(value) || '-'

const getRequirementTitleText = value => getTextCellContent(value)

const formatRequirementTitle = value => formatTextCell(value)

const formatDateTime = (value) => {
  if (!value) {
    return '-'
  }

  let date = null

  if (value instanceof Date) {
    date = value
  } else if (typeof value === 'string') {
    const normalizedValue = value.includes('T') ? value : value.replace(' ', 'T')
    date = new Date(normalizedValue)

    if (Number.isNaN(date.getTime())) {
      date = new Date(value.replace(/-/g, '/'))
    }
  } else {
    date = new Date(value)
  }

  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return value
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')

  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`
}

const formatStatus = (status) => {
  const statusMap = {
    not_run: '未执行',
    pass: '通过',
    fail: '失败',
    block: '阻塞',
    not_test: '本版本不测'
  }

  return statusMap[status] || String(status || '').trim() || '-'
}

const formatAuditStatus = (auditStatus) => {
  const matchedOption = auditStatusOptions.find(option => option.value === auditStatus)
  return matchedOption?.label || '待审核'
}

const workspaceTableMaxHeight = 'calc(100vh - 360px)'
const versionManagementTableMaxHeight = 'calc(100vh - 340px)'
const STATUS_COUNT_KEYS = ['not_run', 'pass', 'fail', 'block', 'not_test']
const STATUS_COUNT_META = Object.freeze({
  not_run: { label: '未执行', type: 'info' },
  pass: { label: '通过', type: 'success' },
  fail: { label: '失败', type: 'danger' },
  block: { label: '阻塞', type: 'warning' },
  not_test: { label: '本版本不测', type: 'info' },
})
const DEFECT_STATUS_TYPE = defectStatusTagTypes
const researchProgressSummary = ref(null)
const qualityReportLivePanelRef = ref(null)
const qualityLiveToolbarState = ref({
  visible: false,
  loading: false,
  canShare: false,
  canRefresh: false,
  scopeItems: [],
})

const normalizeStatusCountValue = (countValue) => {
  if (typeof countValue === 'number') {
    return {
      not_run: countValue,
      pass: 0,
      fail: 0,
      block: 0,
      not_test: 0
    }
  }

  const source = countValue && typeof countValue === 'object' ? countValue : {}
  return STATUS_COUNT_KEYS.reduce((result, key) => {
    result[key] = Number(source[key]) || 0
    return result
  }, {})
}

const normalizeDefectCountItems = items => (
  (Array.isArray(items) ? items : [])
    .map(item => ({
      key: normalizeText(item?.key || item?.label) || 'unknown',
      label: normalizeText(item?.label || item?.key) || '未填写',
      count: Number(item?.count) || 0
    }))
    .filter(item => item.count > 0)
)

const buildStatusSummaryTags = counts => {
  const normalizedCounts = normalizeStatusCountValue(counts)
  return STATUS_COUNT_KEYS
    .filter(key => normalizedCounts[key] > 0)
    .map(key => ({
      key,
      label: STATUS_COUNT_META[key]?.label || key,
      count: normalizedCounts[key],
      type: STATUS_COUNT_META[key]?.type || ''
    }))
}

const buildDefectSummaryTags = items => (
  normalizeDefectCountItems(items).map(item => ({
    key: item.key,
    label: item.label,
    count: item.count,
    type: DEFECT_STATUS_TYPE[item.key] || ''
  }))
)

const sumStatusSummaryTotal = counts => {
  const normalizedCounts = normalizeStatusCountValue(counts)
  return STATUS_COUNT_KEYS.reduce((sum, key) => sum + normalizedCounts[key], 0)
}

const sumDefectSummaryTotal = items => (
  normalizeDefectCountItems(items).reduce((sum, item) => sum + item.count, 0)
)

const showResearchProgressSummary = computed(() => activeTab.value === 'requirement-overview')
const researchProgressToolbarSummaryItems = computed(() => {
  const summary = researchProgressSummary.value || {}
  return [
    {
      key: 'requirements',
      label: '需求',
      total: Number(summary.requirement_count_total) || sumDefectSummaryTotal(summary.requirement_count),
      tags: buildDefectSummaryTags(summary.requirement_count)
    },
    {
      key: 'dev-self-tests',
      label: '自测测试点',
      total: Number(summary.dev_self_test_count_total) || sumStatusSummaryTotal(summary.dev_self_test_count),
      tags: buildStatusSummaryTags(summary.dev_self_test_count)
    },
    {
      key: 'testpoints',
      label: '测试点',
      total: Number(summary.testpoint_count_total) || sumStatusSummaryTotal(summary.testpoint_count),
      tags: buildStatusSummaryTags(summary.testpoint_count)
    },
    {
      key: 'version-defects',
      label: '版本缺陷',
      total: Number(summary.version_defect_count_total) || sumDefectSummaryTotal(summary.version_defect_count),
      tags: buildDefectSummaryTags(summary.version_defect_count)
    },
    {
      key: 'online-defects',
      label: '线上缺陷',
      total: Number(summary.online_defect_count_total) || sumDefectSummaryTotal(summary.online_defect_count),
      tags: buildDefectSummaryTags(summary.online_defect_count)
    }
  ]
})

const handleResearchProgressSummaryChange = summary => {
  researchProgressSummary.value = summary || null
}

const showQualityLiveToolbar = computed(() => (
  activeTab.value === 'quality-report-live' &&
  Boolean(qualityLiveToolbarState.value?.visible)
))

const handleQualityLiveToolbarStateChange = state => {
  qualityLiveToolbarState.value = {
    visible: Boolean(state?.visible),
    loading: Boolean(state?.loading),
    canShare: Boolean(state?.canShare),
    canRefresh: Boolean(state?.canRefresh),
    scopeItems: Array.isArray(state?.scopeItems) ? state.scopeItems : [],
  }
}

const handleQualityLiveShare = async () => {
  await qualityReportLivePanelRef.value?.shareReport?.()
}

const handleQualityLiveRefresh = async () => {
  await qualityReportLivePanelRef.value?.refreshCurrentReport?.()
}

const getCountTotal = (countValue) => {
  if (typeof countValue === 'number') {
    return countValue
  }

  if (!countValue || typeof countValue !== 'object') {
    return 0
  }

  return STATUS_COUNT_KEYS
    .map(key => Number(countValue[key]) || 0)
    .reduce((sum, current) => sum + current, 0)
}

const getMindmapCaseCountTotal = row => getCountTotal(row?.case_count)
const getMindmapTestpointCountTotal = row => getCountTotal(row?.testpoint_count)
const getStatusOptionValue = value => {
  const normalizedValue = String(value || '').trim()
  if (!normalizedValue) {
    return ''
  }

  const matchedOption = statusOptions.find(option => (
    option.value === normalizedValue || option.label === normalizedValue
  ))
  return matchedOption?.value || normalizedValue
}
const getMindmapTestpointStatusText = row => {
  const counts = normalizeStatusCountValue(row?.testpoint_count)
  return STATUS_COUNT_KEYS
    .filter(key => counts[key] > 0)
    .map(key => STATUS_COUNT_META[key]?.label || key)
    .join(' ')
}
const filterMindmapByTestpointStatus = (value, row) => {
  const filterText = String(value || '').trim()
  if (!filterText) {
    return true
  }

  const statusValue = getStatusOptionValue(filterText)
  const counts = normalizeStatusCountValue(row?.testpoint_count)
  if (STATUS_COUNT_KEYS.includes(statusValue)) {
    return counts[statusValue] > 0
  }

  return getMindmapTestpointStatusText(row).includes(filterText)
}
const getMindmapReviewTestpointCountTotal = row => Number(row?.review_testpoint_count?.total) || 0
const getMindmapReviewTestpointCountUnprocessed = row => Number(row?.review_testpoint_count?.unprocessed) || 0
const getMindmapReviewTestpointCountText = row => (
  `${getMindmapReviewTestpointCountUnprocessed(row)}/${getMindmapReviewTestpointCountTotal(row)}`
)
const getMindmapDevSelfTestCountTotal = row => getCountTotal(row?.dev_self_test_count)
const getMindmapModule = row => row?.module || '-'
const getMindmapResponsibilityGroup = row => row?.responsibility_group || '-'
const getMindmapFrontendName = row => row?.frontend_name || '-'
const getMindmapBackendName = row => row?.backend_name || '-'
const getNodeTags = row => (Array.isArray(row?.tags) ? row.tags : []).filter(Boolean)
const getNodeSelfTestStatusText = row => (row?.is_dev_self_test ? formatStatus(row.self_test_status) : '-')
const getDevSelfTestFrontendName = row => getUserDisplayName(row?.frontend_developer, '-')
const getDevSelfTestBackendName = row => getUserDisplayName(row?.backend_developer, '-')
const getVersionDefaultLabel = row => (row?.is_default ? '默认' : '非默认')
const getVersionBaselineLabel = row => (row?.is_baseline ? '基线' : '非基线')
const buildStaticFilterOptions = values => (
  Array.from(new Set((Array.isArray(values) ? values : []).map(value => String(value || '').trim()).filter(Boolean)))
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
    .map(value => ({ text: value, value }))
)
const buildStatusColumnFilterOptions = () => (
  statusOptions.map(option => ({
    text: option.label,
    value: option.label
  }))
)
const buildUserFilterOptions = users => (
  Array.from(
    new Map(
      (Array.isArray(users) ? users : [])
        .map(user => [String(user?.id || ''), getUserDisplayName(user)])
        .filter(([id, name]) => id && name)
    ).values()
  )
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
    .map(value => ({ text: value, value }))
)

const mindmapColumnFilters = computed(() => {
  // 从API返回的创建人列表构建筛选选项（而非从当前分页数据中提取）
  const creatorFilters = mindmapCreators.value.map(user => {
    const displayName = getUserDisplayName(user)
    return {
      text: displayName,
      value: displayName
    }
  }).sort((a, b) => a.text.localeCompare(b.text, 'zh-CN'))

  return {
    id: buildTableFilters(mindmapTableData.value, row => row.id, 20, compareTableNumber),
    requirement_key: buildTableFilters(mindmapTableData.value, row => row.requirement_key, 20),
    requirement_title: buildTableFilters(mindmapTableData.value, row => row.requirement_title, 20),
    name: buildTableFilters(mindmapTableData.value, row => row.name, 20),
    module: buildTableFilters(mindmapTableData.value, getMindmapModule, 20),
    responsibility_group: buildTableFilters(mindmapTableData.value, getMindmapResponsibilityGroup, 20),
    frontend: buildTableFilters(mindmapTableData.value, getMindmapFrontendName, 20),
    backend: buildTableFilters(mindmapTableData.value, getMindmapBackendName, 20),
    case_count: buildTableFilters(mindmapTableData.value, getMindmapCaseCountTotal, 20, compareTableNumber),
    testpoint_count: buildStatusColumnFilterOptions(),
    review_testpoint_count: buildTableFilters(mindmapTableData.value, getMindmapReviewTestpointCountTotal, 20, compareTableNumber),
    dev_self_test_count: buildTableFilters(mindmapTableData.value, getMindmapDevSelfTestCountTotal, 20, compareTableNumber),
    executor: buildTableFilters(mindmapTableData.value, row => row.executor, 20),
    creator: creatorFilters,
    version: buildTableFilters(mindmapTableData.value, row => row.version, 20),
    created_at: buildTableFilters(mindmapTableData.value, row => row.created_at, 20),
    updated_at: buildTableFilters(mindmapTableData.value, row => row.updated_at, 20),
  }
})

// 测试脑图的创建人列表（从API响应中获取当前筛选条件下的所有创建人）
const mindmapCreatorList = computed(() => {
  if (!mindmapCreators.value || !mindmapCreators.value.length) {
    return []
  }

  // mindmapCreators.value 已经是从后端返回的用户对象列表
  // 格式：[{id, username, first_name, last_name, email, full_name}, ...]
  return mindmapCreators.value
})

const normalizeMindmapFilterValue = value => {
  if (Array.isArray(value)) {
    return value.filter(item => item !== null && item !== undefined && item !== '')
  }
  return value ?? ''
}

const mindmapConfiguredFilters = computed({
  get: () => ({
    [MINDMAP_FILTER_FIELD_ID]: mindmapFilters.id,
    [MINDMAP_FILTER_FIELD_REQUIREMENT_KEY]: mindmapFilters.requirementKey || mindmapFilters.keyword,
    [MINDMAP_FILTER_FIELD_REQUIREMENT_TITLE]: mindmapFilters.requirementTitle,
    [MINDMAP_FILTER_FIELD_MODULE]: mindmapFilters.module,
    [MINDMAP_FILTER_FIELD_NAME]: mindmapFilters.nameKeyword,
    [MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP]: mindmapFilters.responsibilityGroup,
    [MINDMAP_FILTER_FIELD_FRONTEND]: mindmapFilters.frontendName,
    [MINDMAP_FILTER_FIELD_BACKEND]: mindmapFilters.backendName,
    [MINDMAP_FILTER_FIELD_AUTHOR]: mindmapFilters.authorId || mindmapFilters.authorName,
    [MINDMAP_FILTER_FIELD_EXECUTOR]: mindmapFilters.executor,
    [MINDMAP_FILTER_FIELD_VERSION]: mindmapFilters.versionName,
    [MINDMAP_FILTER_FIELD_CREATED_AT]: mindmapFilters.createdAt,
    [MINDMAP_FILTER_FIELD_UPDATED_AT]: mindmapFilters.updatedAt,
  }),
  set: value => {
    const nextValue = value || {}
    mindmapFilters.id = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_ID])
    mindmapFilters.requirementKey = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_REQUIREMENT_KEY])
    mindmapFilters.requirementTitle = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_REQUIREMENT_TITLE])
    mindmapFilters.keyword = ''
    mindmapFilters.module = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_MODULE])
    mindmapFilters.nameKeyword = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_NAME])
    mindmapFilters.responsibilityGroup = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP])
    mindmapFilters.frontendName = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_FRONTEND])
    mindmapFilters.backendName = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_BACKEND])
    const authorValue = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_AUTHOR])
    const authorId = Number(authorValue)
    mindmapFilters.authorId = Number.isInteger(authorId) && authorId > 0 ? authorId : null
    mindmapFilters.authorName = mindmapFilters.authorId ? '' : authorValue
    mindmapFilters.executor = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_EXECUTOR])
    mindmapFilters.versionName = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_VERSION])
    mindmapFilters.createdAt = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_CREATED_AT])
    mindmapFilters.updatedAt = normalizeMindmapFilterValue(nextValue[MINDMAP_FILTER_FIELD_UPDATED_AT])
  },
})

const mindmapFilterOptionMap = computed(() => ({
  [MINDMAP_FILTER_FIELD_AUTHOR]: mindmapCreatorList.value.map(user => ({
    label: getUserDisplayName(user),
    value: user.id,
  })),
  [MINDMAP_FILTER_FIELD_RESPONSIBILITY_GROUP]: groupOptions.value.map(group => ({
    label: group.name,
    value: group.name,
  })),
  [MINDMAP_FILTER_FIELD_VERSION]: versionList.value.map(version => ({
    label: version.name,
    value: version.id,
  })),
}))

// 测试用例的创建人列表（从API响应中获取当前筛选条件下的所有创建人）
const testcaseCreatorList = computed(() => {
  if (!testcaseCreators.value || !testcaseCreators.value.length) {
    return []
  }
  return testcaseCreators.value
})

// 测试点的创建人列表（从API响应中获取当前筛选条件下的所有创建人）
const testpointCreatorList = computed(() => {
  if (!testpointCreators.value || !testpointCreators.value.length) {
    return []
  }
  return testpointCreators.value
})

// 自测测试点的创建人列表（从API响应中获取当前筛选条件下的所有创建人）
const devSelfTestCreatorList = computed(() => {
  if (!devSelfTestCreators.value || !devSelfTestCreators.value.length) {
    return []
  }
  return devSelfTestCreators.value
})

const testcaseColumnFilters = computed(() => {
  // 从API返回的创建人列表构建筛选选项
  const creatorFilters = testcaseCreators.value.map(user => {
    const displayName = getUserDisplayName(user)
    return {
      text: displayName,
      value: displayName
    }
  }).sort((a, b) => a.text.localeCompare(b.text, 'zh-CN'))

  return {
    node_text: buildTableFilters(testcaseTableData.value, row => row.node_text, 20),
    requirement_key: buildTableFilters(testcaseTableData.value, row => row.requirement_key, 20),
    requirement_title: buildTableFilters(testcaseTableData.value, row => row.requirement_title, 20),
    mindmap_name: buildTableFilters(testcaseTableData.value, row => row.mindmap_name, 20),
    responsibility_group: buildStaticFilterOptions(groupOptions.value.map(group => group.name)),
    module_path: buildTableFilters(testcaseTableData.value, row => row.module_path, 20),
    priority: buildTableFilters(testcaseTableData.value, row => formatPriority(row.priority), 20),
    status: buildStatusColumnFilterOptions(),
    self_test_status: buildTableFilters(testcaseTableData.value, getNodeSelfTestStatusText, 20),
    tags: buildTableFilters(testcaseTableData.value, row => getNodeTags(row), 30),
    creator: creatorFilters,
    updated_at: buildTableFilters(testcaseTableData.value, row => row.updated_at, 20),
  }
})

const testpointColumnFilters = computed(() => {
  // 从API返回的创建人列表构建筛选选项
  const creatorFilters = testpointCreators.value.map(user => {
    const displayName = getUserDisplayName(user)
    return {
      text: displayName,
      value: displayName
    }
  }).sort((a, b) => a.text.localeCompare(b.text, 'zh-CN'))

  return {
    id: buildTableFilters(testpointTableData.value, row => row.id, 20),
    node_text: buildTableFilters(testpointTableData.value, row => row.node_text, 20),
    requirement_key: buildTableFilters(testpointTableData.value, row => row.requirement_key, 20),
    requirement_title: buildTableFilters(testpointTableData.value, row => row.requirement_title, 20),
    mindmap_name: buildTableFilters(testpointTableData.value, row => row.mindmap_name, 20),
    responsibility_group: buildStaticFilterOptions(groupOptions.value.map(group => group.name)),
    creator: creatorFilters,
    reviewer_name: buildTableFilters(testpointTableData.value, row => row.reviewer_name, 20),
    review_time: buildTableFilters(testpointTableData.value, row => row.review_time, 20),
    review_status: buildTableFilters(testpointTableData.value, row => row.review_status, 20),
    priority: buildTableFilters(testpointTableData.value, row => formatPriority(row.priority), 20),
    status: buildStatusColumnFilterOptions(),
    self_test_status: buildTableFilters(testpointTableData.value, getNodeSelfTestStatusText, 20),
    module_path: buildTableFilters(testpointTableData.value, row => row.module_path, 20),
    tags: buildTableFilters(testpointTableData.value, row => getNodeTags(row), 30),
    updated_at: buildTableFilters(testpointTableData.value, row => row.updated_at, 20),
  }
})

const devSelfTestColumnFilters = computed(() => ({
  module_path: buildTableFilters(devSelfTestTableData.value, row => row.module_path, 20),
  testpoint: buildTableFilters(devSelfTestTableData.value, row => row.testpoint, 20),
  requirement_key: buildTableFilters(devSelfTestTableData.value, row => row.requirement_key, 20),
  requirement_title: buildTableFilters(devSelfTestTableData.value, row => row.requirement_title, 20),
  priority: buildTableFilters(devSelfTestTableData.value, row => formatPriority(row.priority), 20),
  status: buildTableFilters(devSelfTestTableData.value, row => formatStatus(row.status), 20),
  audit_status: buildTableFilters(devSelfTestTableData.value, row => formatAuditStatus(row.audit_status), 20),
  responsibility_group: buildStaticFilterOptions(groupOptions.value.map(group => group.name)),
  frontend: buildUserFilterOptions(frontendDeveloperOptions.value),
  backend: buildUserFilterOptions(backendDeveloperOptions.value),
  updated_at: buildTableFilters(devSelfTestTableData.value, row => row.updated_at, 20),
}))

const versionColumnFilters = computed(() => ({
  name: buildTableFilters(versionList.value, row => row.name, 20),
  description: buildTableFilters(versionList.value, row => row.description, 20),
  is_default: buildTableFilters(versionList.value, getVersionDefaultLabel, 10),
  is_baseline: buildTableFilters(versionList.value, getVersionBaselineLabel, 10),
  created_at: buildTableFilters(versionList.value, row => row.created_at, 20),
}))

// 重置
const handleReset = async () => {
  if (activeTab.value === 'testcases') {
    testcaseFilters.keyword = ''
    testcaseFilters.mindmapName = ''
    testcaseFilters.responsibilityGroup = ''
    testcaseFilters.authorId = null
    testcaseFilters.priority = null
    testcaseFilters.status = ''
  } else if (activeTab.value === 'testpoints') {
    testpointFilters.keyword = ''
    testpointFilters.requirementKey = ''
    testpointFilters.mindmapId = ''
    testpointFilters.mindmapName = ''
    testpointFilters.tag = ''
    testpointFilters.status = ''
    testpointFilters.responsibilityGroup = ''
    testpointFilters.authorId = null
  } else if (activeTab.value === 'devselftest') {
    devSelfTestFilters.mindmapName = ''
    devSelfTestFilters.requirementKey = ''
    devSelfTestFilters.requirementTitle = ''
    devSelfTestFilters.status = ''
    devSelfTestFilters.responsibilityGroup = ''
    devSelfTestFilters.frontendDeveloperId = null
    devSelfTestFilters.backendDeveloperId = null
  } else {
    mindmapFilters.id = ''
    mindmapFilters.keyword = ''
    mindmapFilters.requirementKey = ''
    mindmapFilters.requirementTitle = ''
    mindmapFilters.nameKeyword = ''
    mindmapFilters.module = ''
    mindmapFilters.frontendName = ''
    mindmapFilters.backendName = ''
    mindmapFilters.authorId = null
    mindmapFilters.authorName = ''
    mindmapFilters.executor = ''
    mindmapFilters.versionName = ''
    mindmapFilters.createdAt = ''
    mindmapFilters.updatedAt = ''
    mindmapFilters.responsibilityGroup = ''
  }
  getActivePagination().page = 1
  await syncWorkspaceRouteQuery()
  await loadActiveTabData()
}

const refreshWorkspaceContext = async ({ reloadProjects = false, reloadActiveData = MANUAL_TABS.has(activeTab.value) } = {}) => {
  if (reloadProjects) {
    await loadWorkspaceProjects()
  }

  await loadCategories()
  await loadVersions()
  await syncWorkspaceRouteQuery()

  if (reloadActiveData) {
    resetAllPaginationPages()
    await loadActiveTabData()
  }
}

const handleWorkspaceProjectSelection = async (projectId, { force = false } = {}) => {
  const normalizedProjectId = resolveWorkspaceProjectId(parseRouteId(projectId))
  const currentProjectKey = currentProjectId.value ? String(currentProjectId.value) : ''
  const nextProjectKey = normalizedProjectId ? String(normalizedProjectId) : ''

  if (!force && currentProjectKey === nextProjectKey) {
    return
  }

  await replaceWorkspaceQuery({
    project_id: normalizedProjectId ? String(normalizedProjectId) : undefined,
    version_id: undefined,
    category_id: undefined,
  })

  await refreshWorkspaceContext()
}

const handleWorkspaceProjectsUpdated = async () => {
  await refreshWorkspaceContext({ reloadProjects: true })
}

const handleSetCurrentProjectDefault = async () => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目后再设置默认项目')
    return
  }

  if (!canSetDefaultWorkspaceProject.value) {
    ElMessage.warning('当前账号没有设置默认项目权限')
    return
  }

  if (selectedWorkspaceProject.value?.is_default) {
    return
  }

  workspaceProjectDefaultLoading.value = true
  try {
    await api.patch(`/projects/${currentProjectId.value}/`, {
      is_default: true,
    })
    ElMessage.success('默认项目设置成功')
    await handleWorkspaceProjectsUpdated()
  } catch (error) {
    ElMessage.error('设置默认项目失败：' + (error.response?.data?.detail || error.response?.data?.error || error.message))
  } finally {
    workspaceProjectDefaultLoading.value = false
  }
}

const handleWorkspaceVersionSelection = async versionId => {
  const normalizedVersionId = parseRouteId(versionId)
  currentVersionId.value = normalizedVersionId || 'all'
  await handleVersionChange()
}

const handleKnowledgeProjectSelection = async projectId => {
  knowledgeProjectPopoverVisible.value = false
  await handleWorkspaceProjectSelection(projectId)
}

const handleKnowledgeVersionSelection = async versionId => {
  knowledgeVersionPopoverVisible.value = false
  await handleWorkspaceVersionSelection(versionId)
}

// 创建
const handleCreate = () => {
  dialogTitle.value = '新建测试脑图'
  resetMindmapForm()
  dialogVisible.value = true
}

const triggerXMindImport = () => {
  if (xmindImporting.value) {
    return
  }

  if (xmindFileInputRef.value) {
    xmindFileInputRef.value.value = ''
    xmindFileInputRef.value.click()
  }
}

const clearImportedXMind = () => {
  importedXMindName.value = ''
  importedXMindFile.value = null
  currentMindmapData.value = buildDefaultMindmapData(formData.name || '新建脑图')
  if (xmindFileInputRef.value) {
    xmindFileInputRef.value.value = ''
  }
}

const handleXMindFileChange = async event => {
  const file = event.target?.files?.[0]
  if (!file) {
    return
  }

  xmindImporting.value = true
  try {
    importedXMindFile.value = file
    importedXMindName.value = file.name
    currentMindmapData.value = buildDefaultMindmapData(formData.name || '新建脑图')
    formRef.value?.clearValidate(['name'])
    ElMessage.success('XMind 已选择，创建时将由后台解析')
  } catch (error) {
    console.error('导入 XMind 失败:', error)
    ElMessage.error('导入 XMind 失败：' + (error.message || '请检查文件格式'))
  } finally {
    xmindImporting.value = false
    if (xmindFileInputRef.value) {
      xmindFileInputRef.value.value = ''
    }
  }
}

// 编辑
const normalizeNavigationText = value => String(value || '').trim()

const buildMindmapNavigationTarget = ({ mindmapId, nodeText, nodePath, mode = 'view' }) => {
  const normalizedMindmapId = String(mindmapId || '').trim()
  if (!normalizedMindmapId) {
    return null
  }

  const query = {
    id: normalizedMindmapId,
    from_tab: activeTab.value
  }
  const returnQuery = buildWorkspaceQuery()
  query.return_query = encodeURIComponent(JSON.stringify(returnQuery))

  const normalizedNodeText = normalizeNavigationText(nodeText)
  const normalizedNodePath = normalizeNavigationText(nodePath)

  if (normalizedNodeText) {
    query.node_text = normalizedNodeText
  }
  if (normalizedNodePath) {
    query.node_path = normalizedNodePath
  }

  return {
    path: mode === 'edit' ? '/manual-testcases/editor' : '/manual-testcases/view',
    query
  }
}

const navigateToMindmapRoute = ({ mindmapId, nodeText, nodePath, mode = 'view' }) => {
  const target = buildMindmapNavigationTarget({ mindmapId, nodeText, nodePath, mode })

  if (!target) {
    ElMessage.warning('未找到脑图ID，无法跳转')
    return
  }

  const resolvedTarget = router.resolve(target)
  window.location.assign(resolvedTarget.href)
}

const navigateToReadonlyMindmapEditor = ({ mindmapId, nodeText, nodePath }) => {
  const target = buildMindmapNavigationTarget({ mindmapId, nodeText, nodePath, mode: 'edit' })

  if (!target) {
    ElMessage.warning('未找到脑图ID，无法跳转')
    return
  }

  target.query = {
    ...target.query,
    readonly: '1',
    mode: 'view',
  }

  const resolvedTarget = router.resolve(target)
  window.location.assign(resolvedTarget.href)
}

const handleEdit = (row) => {
  navigateToMindmapRoute({
    mindmapId: row.id,
    mode: 'edit'
  })
}

const handleEditInfo = async (row) => {
  try {
    const response = await api.get(`/testcases/manual-mindmaps/${row.id}/`)
    const detail = response.data

    dialogTitle.value = '编辑测试脑图'
    populateMindmapForm({
      id: detail.id,
      name: detail.name,
      description: detail.description,
      category_id: detail.category ?? null,
      version_id: detail.version?.id ?? detail.version_id ?? null,
      responsibility_group: detail.responsibility_group,
      frontend_developer_id: detail.frontend_developer?.id ?? detail.frontend_developer_id ?? null,
      backend_developer_id: detail.backend_developer?.id ?? detail.backend_developer_id ?? null,
      author: detail.author,
      author_id: detail.author?.id ?? detail.author_id ?? null,
      executor: detail.executor,
      executor_id: detail.executor?.id ?? detail.executor_id ?? null,
      url: detail.url,
      mindmap_data: detail.mindmap_data
    })
    dialogVisible.value = true
    await nextTick()
    formRef.value?.clearValidate()
  } catch (error) {
    console.error('加载脑图详情失败:', error)
    ElMessage.error('加载脑图详情失败：' + (error.response?.data?.detail || error.message))
  }
}

// 鏌ョ湅
const handleView = (row) => {
  navigateToMindmapRoute({
    mindmapId: row.id,
    mode: 'view'
  })
}

// 跳转到JIRA需求数据页签
const jumpToJiraRequirement = (requirementKey) => {
  if (!requirementKey) {
    ElMessage.warning('需求编号为空')
    return
  }

  // 跳转到【JIRA需求数据】页签，通过jira_keyword参数筛选
  router.push({
    path: '/manual-testcases/list',
    query: {
      tab: 'requirement-records',
      jira_keyword: requirementKey
    }
  })
}

const handleNodeEdit = (row) => {
  navigateToMindmapRoute({
    mindmapId: row.mindmap_id || row.id,
    nodeText: row.node_text,
    nodePath: row.path || row.node_path,
    mode: 'edit'
  })
}

const handleNodeView = (row) => {
  navigateToMindmapRoute({
    mindmapId: row.mindmap_id || row.id,
    nodeText: row.node_text,
    nodePath: row.path || row.node_path,
    mode: 'view'
  })
}

const handleViewDevSelfTestMindmap = (row) => {
  navigateToReadonlyMindmapEditor({
    mindmapId: row.mindmap_id || row.id,
    nodeText: row.testpoint || row.node_text,
    nodePath: row.path || row.node_path,
  })
}

const handleMindmapSelectionChange = rows => {
  mindmapSelectedRows.value = rows
}

const deleteMindmaps = async rows => {
  const deleteResults = await Promise.allSettled(
    rows.map(row => api.delete(`/testcases/manual-mindmaps/${row.id}/`))
  )

  const failedRows = deleteResults
    .map((result, index) => ({ result, row: rows[index] }))
    .filter(item => item.result.status === 'rejected')

  if (!failedRows.length) {
    ElMessage.success(rows.length === 1 ? '删除成功' : `已删除 ${rows.length} 条脑图`)
  } else if (failedRows.length === rows.length) {
    const firstError = failedRows[0].result.reason
    throw firstError
  } else {
    ElMessage.warning(`已删除 ${rows.length - failedRows.length} 条，${failedRows.length} 条删除失败`)
  }

  await handleSearch()
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除这个用例脑图吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteMindmaps([row])
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

const handleBatchDeleteMindmaps = () => {
  if (!mindmapSelectedRows.value.length) {
    ElMessage.warning('请先选择要删除的测试脑图')
    return
  }

  ElMessageBox.confirm(
    `确定要批量删除选中的 ${mindmapSelectedRows.value.length} 条测试脑图吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteMindmaps(mindmapSelectedRows.value)
    } catch (error) {
      console.error('批量删除脑图失败:', error)
      ElMessage.error('批量删除失败：' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 鎻愪氦琛ㄥ崟
const handleSubmit = () => {
  formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (formData.id) {
          const mindmapData = cloneMindmapData(currentMindmapData.value) || buildDefaultMindmapData(formData.name)
          if (!mindmapData.root || typeof mindmapData.root !== 'object') {
            mindmapData.root = { data: {}, children: [] }
          }
          if (!mindmapData.root.data || typeof mindmapData.root.data !== 'object') {
            mindmapData.root.data = {}
          }
          if (!Array.isArray(mindmapData.root.children)) {
            mindmapData.root.children = []
          }

          mindmapData.root.data.text = formData.name
          mindmapData.root.data.nodeType = mindmapData.root.data.nodeType || 'module'

          const data = {
            name: formData.name,
            description: formData.description,
            mindmap_data: mindmapData,
            category_id: formData.category_id,
            version_id: formData.version_id,
            responsibility_group: formData.responsibility_group,
            frontend_developer_id: formData.frontend_developer_id,
            backend_developer_id: formData.backend_developer_id,
            executor_id: formData.executor_id,
            url: formData.url
          }

          console.log('准备更新脑图信息:', { id: formData.id, ...data })
          await api.put(`/testcases/manual-mindmaps/${formData.id}/`, data)
          ElMessage.success('编辑成功')
          dialogVisible.value = false
          await loadCategories()
          await loadMindmaps()
          return
        }

        if (hasImportedXMind.value) {
          const payload = new FormData()
          payload.append('project_id', String(currentProjectId.value))
          payload.append('xmind_file', importedXMindFile.value)

          const appendOptionalField = (key, value) => {
            if (value === undefined || value === null) {
              return
            }

            const normalized = typeof value === 'string' ? value.trim() : value
            if (normalized === '') {
              return
            }

            payload.append(key, String(normalized))
          }

          appendOptionalField('name', formData.name)
          appendOptionalField('description', formData.description)
          appendOptionalField('category_id', formData.category_id)
          appendOptionalField('version_id', formData.version_id)
          appendOptionalField('responsibility_group', formData.responsibility_group)
          appendOptionalField('frontend_developer_id', formData.frontend_developer_id)
          appendOptionalField('backend_developer_id', formData.backend_developer_id)
          appendOptionalField('executor_id', formData.executor_id)
          appendOptionalField('url', formData.url)

          const response = await api.post('/testcases/manual-mindmaps/', payload)
          const createdRecords = Array.isArray(response.data?.created_records) ? response.data.created_records : []
          const importMode = response.data?.import_mode

          if (!createdRecords.length) {
            throw new Error('后台未返回已创建的脑图记录')
          }

          ElMessage.success(
            importMode === 'split_requirements'
              ? `已按需求拆分创建 ${createdRecords.length} 条测试脑图`
              : '创建成功'
          )
          dialogVisible.value = false
          await loadCategories()
          await loadMindmaps()

          if (createdRecords.length === 1 && createdRecords[0]?.id) {
            await router.push({
              name: 'ManualTestCaseEditor',
              query: {
                id: createdRecords[0].id,
                from_tab: activeTab.value,
                return_query: encodeURIComponent(JSON.stringify(buildWorkspaceQuery()))
              }
            })
          }
          return
        }

        const mindmapData = cloneMindmapData(currentMindmapData.value) || buildDefaultMindmapData(formData.name)
        if (!mindmapData.root || typeof mindmapData.root !== 'object') {
          mindmapData.root = { data: {}, children: [] }
        }
        if (!mindmapData.root.data || typeof mindmapData.root.data !== 'object') {
          mindmapData.root.data = {}
        }
        if (!Array.isArray(mindmapData.root.children)) {
          mindmapData.root.children = []
        }

        mindmapData.root.data.text = formData.name
        mindmapData.root.data.nodeType = mindmapData.root.data.nodeType || 'module'

        const data = {
          name: formData.name,
          description: formData.description,
          mindmap_data: mindmapData,
          category_id: formData.category_id,
          version_id: formData.version_id,
          responsibility_group: formData.responsibility_group,
          frontend_developer_id: formData.frontend_developer_id,
          backend_developer_id: formData.backend_developer_id,
          executor_id: formData.executor_id,
          url: formData.url,
          project_id: currentProjectId.value
        }

        console.log('准备创建脑图:', data)
        const response = await api.post('/testcases/manual-mindmaps/', data)
        console.log('创建成功，返回数据:', response.data)
        console.log('新创建的脑图 ID:', response.data.id)

        ElMessage.success('创建成功')
        dialogVisible.value = false
        await loadCategories()

        // 跳转到编辑器，带上新创建的 mindmap ID
        const targetId = response.data.id
        console.log('准备跳转到编辑器, ID:', targetId)
        console.log('跳转参数:', { name: 'ManualTestCaseEditor', query: { id: targetId } })

        await router.push({
          name: 'ManualTestCaseEditor',
          query: {
            id: targetId,
            from_tab: activeTab.value,
            return_query: encodeURIComponent(JSON.stringify(buildWorkspaceQuery()))
          }
        })

        console.log('跳转完成, 当前路由:', router.currentRoute.value)
      } catch (error) {
        console.error('保存脑图失败:', error)
        const responseData = error.response?.data || {}
        const firstXMindError = Array.isArray(responseData.xmind_file) ? responseData.xmind_file[0] : ''
        const errorText = firstXMindError || responseData.detail || error.message
        ElMessage.error((formData.id ? '编辑失败：' : '创建失败：') + errorText)
      }
    }
  })
}

// 关闭对话框
const handleDialogClose = () => {
  resetMindmapForm()
}

// 加载版本列表
const loadVersions = async () => {
  if (!currentProjectId.value) {
    versionList.value = []
    versionListLoading.value = false
    currentVersionId.value = 'all'
    return
  }

  versionListLoading.value = true
  try {
    const response = await api.get('/versions/', {
      params: {
        projects: currentProjectId.value
      }
    })
    versionList.value = response.data.results || response.data

    const routeRequestsAllVersions = isAllRouteValue(route.query.version_id)
    if (routeRequestsAllVersions) {
      currentVersionId.value = 'all'
      return
    }

    const requestedVersionId = parseRouteId(route.query.version_id)
    const matchedRequestedVersion = requestedVersionId
      ? versionList.value.find(item => String(item.id) === String(requestedVersionId))
      : null
    const matchedCurrentVersion =
      currentVersionId.value && currentVersionId.value !== 'all'
        ? versionList.value.find(item => String(item.id) === String(currentVersionId.value))
        : null

    if (matchedRequestedVersion) {
      currentVersionId.value = matchedRequestedVersion.id
      return
    }

    if (matchedCurrentVersion) {
      currentVersionId.value = matchedCurrentVersion.id
      return
    }

    // 设置默认版本
    const defaultVersion = versionList.value.find(v => v.is_default)
    if (defaultVersion) {
      currentVersionId.value = defaultVersion.id
      return
    }

    currentVersionId.value = 'all'
  } catch (error) {
    console.error('加载版本失败:', error)
  } finally {
    versionListLoading.value = false
  }
}

const loadGroupOptions = async () => {
  try {
    groupOptions.value = await fetchAllGroupOptions()
  } catch (error) {
    groupOptions.value = []
    console.error('加载组别列表失败:', error)
  }
}

const loadDeveloperOptions = async () => {
  try {
    const [frontendUsers, backendUsers] = await Promise.all([
      fetchRoleMemberOptions('前端'),
      fetchRoleMemberOptions('后端'),
    ])
    frontendDeveloperOptions.value = frontendUsers
    backendDeveloperOptions.value = backendUsers
  } catch (error) {
    frontendDeveloperOptions.value = []
    backendDeveloperOptions.value = []
    console.error('加载角色成员列表失败:', error)
  }
}

const loadExecutorOptions = async () => {
  try {
    const allUsers = []
    let page = 1
    let total = 0

    while (true) {
      const response = await api.get('/auth/users/', {
        params: {
          page,
          page_size: 100,
          is_active: true,
          ordering: 'username',
        },
      })
      const { results, count } = normalizeListResponse(response.data)
      allUsers.push(...results)
      total = count

      if (!results.length || allUsers.length >= total || results.length < 100) {
        break
      }

      page += 1
    }

    const optionMap = new Map()
    ;[userStore.user, ...allUsers].forEach(user => {
      const userId = Number(user?.id)
      if (Number.isInteger(userId) && userId > 0) {
        optionMap.set(userId, user)
      }
    })
    executorOptions.value = [...optionMap.values()]
  } catch (error) {
    executorOptions.value = userStore.user?.id ? [userStore.user] : []
    console.error('加载执行人列表失败:', error)
  }
}

const loadWorkspaceProjects = async () => {
  const endpoints = [
    { url: '/projects/all/' },
    { url: '/projects/list/' },
  ]

  try {
    for (const endpoint of endpoints) {
      try {
        const response = await api.get(endpoint.url)
        const projects = response.data?.results || response.data || []
        workspaceProjects.value = Array.isArray(projects) ? projects : []
        return
      } catch (error) {
        if (endpoint === endpoints[endpoints.length - 1]) {
          throw error
        }
      }
    }
  } catch (error) {
    workspaceProjects.value = []
    console.error('加载工作台项目失败:', error)
  }
}

onMounted(async () => {
  // 恢复tab状态（从编辑器/查看页面返回时）
  const tabFromQuery = Array.isArray(route.query.tab) ? route.query.tab[0] : route.query.tab
  activeTab.value = resolveWorkspaceTab(tabFromQuery || activeTab.value) || activeTab.value
  syncRouteDrivenFilters(activeTab.value)
  await loadWorkspaceProjects()
  await Promise.all([
    loadCategories(),
    loadVersions(),
    loadGroupOptions(),
    loadDeveloperOptions(),
    loadExecutorOptions()
  ])
  await syncWorkspaceRouteQuery()
  if (MANUAL_TABS.has(activeTab.value)) {
    await handleSearch()
  }
})
</script>

<style scoped>
.manual-testcase-list {
  --directory-width: 0px;
  --workspace-embed-scroll-height: calc(100vh - 148px);
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.manual-testcase-list--allow-page-scroll {
  min-height: 100%;
  height: auto;
}

.manual-testcase-list--with-directory {
  --directory-width: 260px;
}

.manual-testcase-list--directory-collapsed {
  --directory-width: 56px;
}

.workspace-toolbar-panel {
  flex-shrink: 0;
}

.workspace-content-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.manual-testcase-list--allow-page-scroll .workspace-content-shell,
.manual-testcase-list--allow-page-scroll .right-panel,
.manual-testcase-list--allow-page-scroll .workspace-tab-shell,
.manual-testcase-list--allow-page-scroll .mindmap-tabs,
.manual-testcase-list--allow-page-scroll .report-detail-tab-embed,
.manual-testcase-list--allow-page-scroll .defect-notification-tab-embed {
  min-height: 0;
  height: auto;
  overflow: visible;
}

.left-panel {
  width: var(--directory-width);
  flex-shrink: 0;
  min-width: 0;
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  transition: width 0.2s ease;
}

.left-panel--collapsed {
  align-items: center;
}

.left-panel--version-only {
  justify-content: flex-start;
}

.tree-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-link-hint {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}

.tree-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tree-header-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.directory-collapse-rail {
  width: 100%;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.directory-toggle-button {
  flex-shrink: 0;
}

.directory-rail-label {
  color: #909399;
  font-size: 12px;
  line-height: 1;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding-right: 8px;
}

.node-actions {
  display: none;
  gap: 8px;
}

.custom-tree-node:hover .node-actions {
  display: flex;
}

.node-actions .el-icon {
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
}

.node-actions .el-icon:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.knowledge-context-menu__item {
  width: 100%;
  min-height: 74px;
  border: 1px solid transparent;
  border-radius: 8px;
  background-color: transparent;
  color: #60768d;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  padding: 6px 4px;
  font-size: 12px;
  line-height: 1.15;
  text-align: center;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.knowledge-context-menu__item:hover {
  border-color: #b9d2ea;
  background-color: #fff;
  color: #1f6fb2;
}

.knowledge-context-menu__item--disabled {
  color: #a8abb2;
  cursor: not-allowed;
  background-color: #f5f7fa;
}

.knowledge-context-menu__item--disabled:hover {
  border-color: #e4e7ed;
  background-color: #f5f7fa;
  color: #a8abb2;
}

.knowledge-context-menu__label {
  max-width: 42px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.15;
  white-space: normal;
  word-break: break-all;
}

.knowledge-context-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.knowledge-context-panel__title {
  color: #303133;
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.knowledge-context-panel__list {
  max-height: 320px;
  overflow-y: auto;
  padding: 8px 0;
}

.knowledge-context-option {
  width: 100%;
  min-height: 34px;
  border: 0;
  border-radius: 4px;
  background-color: transparent;
  color: #303133;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 8px;
  text-align: left;
}

.knowledge-context-option:hover {
  background-color: #f5f7fa;
  color: var(--topbar-base-color, #2396ea);
}

.knowledge-context-option--active {
  background-color: #ecf5ff;
  color: var(--topbar-base-color, #2396ea);
  font-weight: 700;
}

.knowledge-context-option__text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-context-panel__footer {
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
}

:global(.knowledge-context-popover.el-popper) {
  padding: 12px;
}

.right-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-tab-shell {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.workspace-context-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  min-width: 0;
  padding: 4px 0;
}

.workspace-context-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workspace-context-select {
  flex-shrink: 0;
}

.workspace-context-select--project {
  min-width: 132px;
}

.workspace-context-select--version {
  min-width: 0;
}

.research-progress-toolbar-summary {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.research-progress-toolbar-summary__group {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 0 1 auto;
  flex-wrap: wrap;
  padding: 2px 0;
}

.research-progress-toolbar-summary__label {
  color: #5b7188;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.research-progress-toolbar-summary__tags {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  min-width: 0;
}

.quality-live-toolbar-summary {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
  min-width: 0;
  flex-wrap: wrap;
}

.quality-live-toolbar-summary__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-wrap: wrap;
}

.quality-live-toolbar-summary__chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  padding: 0 8px;
  border: 1px solid #dbe7f3;
  border-radius: 999px;
  background: #f6f9fc;
  color: #5b7188;
  font-size: 12px;
  white-space: nowrap;
}

.quality-live-toolbar-summary__chip strong {
  color: #17324d;
  font-weight: 700;
}

.quality-live-toolbar-summary__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.search-form {
  margin: 0;
  flex: 1;
}

:deep(.search-form .el-form-item) {
  margin-bottom: 0;
}

:deep(.workspace-toolbar-panel .el-card) {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  border-bottom: none;
}

:deep(.workspace-toolbar-panel .el-card__body) {
  padding: 12px 16px;
}

:deep(.right-panel .el-card) {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  border-bottom: none;
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.right-panel .el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

.manual-testcase-list--allow-page-scroll :deep(.right-panel .el-card__body) {
  overflow: visible;
}

:deep(.right-panel .el-card__header) {
  padding: 16px 20px;
  background-color: #fff;
}

.mindmap-tabs {
  flex: 1;
  width: 100%;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.tab-toolbar-actions {
  display: flex;
  justify-content: flex-end;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 8px;
  width: 100%;
  white-space: nowrap;
}

.row-actions :deep(.el-button) {
  margin-left: 0;
}

.action-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.action-line {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}

.action-line :deep(.el-button) {
  margin-left: 0;
}

.workspace-list-table :deep(th.nowrap-header .cell) {
  white-space: nowrap;
  word-break: keep-all;
}

.tab-panel {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}

.tab-pagination {
  margin-top: auto;
  justify-content: flex-end;
}

.jira-tab-embed,
.knowledge-assistant-tab-embed,
.overview-tab-embed,
.report-list-tab-embed,
.report-detail-tab-embed,
.defect-tab-embed,
.member-tab-embed,
.group-tab-embed,
.role-tab-embed,
.project-environment-tab-embed,
.project-tab-embed,
.version-tab-embed,
.permission-tab-embed,
.defect-notification-tab-embed {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.jira-tab-embed {
  margin: -16px -20px -20px;
}

.knowledge-assistant-tab-embed {
  margin: -16px -20px -20px;
}

.overview-tab-embed {
  margin: -16px -20px -20px;
}

.report-detail-tab-embed,
.defect-notification-tab-embed {
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}

.node-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.path-text {
  color: #606266;
}

.requirement-title-cell {
  display: -webkit-box;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
  max-height: 40px;
  line-height: 20px;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

:deep(.requirement-title-tooltip) {
  max-width: 520px;
  white-space: normal;
  line-height: 1.5;
  word-break: break-word;
  overflow-wrap: anywhere;
}

:deep(.mindmap-tabs .el-tabs__header) {
  margin: 0;
  padding: 0 20px;
}

:deep(.mindmap-tabs--header-hidden > .el-tabs__header) {
  display: none;
}

:deep(.mindmap-tabs .el-tabs__nav-scroll) {
  display: flex;
  justify-content: center;
}

:deep(.mindmap-tabs > .el-tabs__content) {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: 16px 20px 20px;
}

:deep(.mindmap-tabs > .el-tabs__content > .el-tab-pane) {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  height: 100%;
  min-height: 0;
}

.manual-testcase-list--allow-page-scroll :deep(.mindmap-tabs > .el-tabs__content) {
  overflow: visible;
}

:deep(.mindmap-tabs > .el-tabs__content > .embedded-scroll-pane) {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.manual-testcase-list--allow-page-scroll :deep(.mindmap-tabs > .el-tabs__content > .embedded-scroll-pane) {
  height: auto;
}

@media (max-width: 768px) {
  .manual-testcase-list {
    --workspace-embed-scroll-height: calc(100vh - 132px);
  }
}

:deep(.el-tree) {
  background-color: transparent;
}

:deep(.el-tree-node__content) {
  height: 32px;
}

:deep(.el-tree-node:focus > .el-tree-node__content) {
  background-color: #f5f7fa;
}

.status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-management {
  padding: 0;
}

.version-toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.xmind-import-field {
  width: 100%;
}

.xmind-import-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.xmind-import-name {
  flex: 1;
  min-width: 0;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.xmind-import-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.xmind-file-input {
  display: none;
}

.mindmap-link {
  display: block;
  width: 100%;
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
}

.mindmap-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.requirement-link {
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
}

.requirement-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.dev-self-test-drawer__body {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dev-self-test-drawer__summary {
  flex-shrink: 0;
}

.dev-self-test-drawer__form {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.dev-self-test-drawer__footer {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}

:deep(.dev-self-test-drawer .el-drawer__body) {
  padding: 20px;
}
</style>
