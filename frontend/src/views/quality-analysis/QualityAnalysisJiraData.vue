<template>
  <div class="jira-data-page" :class="{ 'jira-data-page--embedded': embedded }">
    <section class="content-card" :class="{ 'content-card--embedded': embedded }">
      <el-tabs
        v-model="activeTab"
        class="jira-tabs"
        :class="{ 'jira-tabs--embedded': embedded }"
      >
        <el-tab-pane label="线上缺陷" name="bug-records">
          <div class="toolbar">
            <div class="toolbar-left">
              <el-select
                v-if="!useLinkedVersion"
                v-model="datasets.bug.filters.version"
                clearable
                filterable
                placeholder="按版本号筛选"
                style="width: 260px"
                @change="handleVersionChange('bug')"
              >
                <el-option
                  v-for="item in versionOptions.bug"
                  :key="item.version"
                  :label="`${item.version}${item.record_count ? ` (${item.record_count}条)` : ''}`"
                  :value="item.version"
                />
              </el-select>
              <el-select
                v-model="datasets.bug.extraVisibleFields"
                multiple
                clearable
                collapse-tags
                collapse-tags-tooltip
                filterable
                placeholder="扩展字段"
                class="extra-field-select"
              >
                <el-option
                  v-for="item in bugExtraFieldOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <el-input
                v-model="datasets.bug.filters.keyword"
                clearable
                placeholder="搜索缺陷编号或缺陷标题"
                style="width: 320px"
                @keyup.enter="handleRecordFilterChange('bug')"
                @clear="handleRecordFilterChange('bug')"
              />
              <el-input
                v-model="datasets.bug.filters.testpointId"
                clearable
                placeholder="请输入测试点ID"
                style="width: 220px"
                @keyup.enter="handleRecordFilterChange('bug')"
                @clear="handleRecordFilterChange('bug')"
              />
            </div>
            <div class="toolbar-right">
              <TableColumnSettings
                :table-ref="bugTableRef"
                storage-key="manual-testcases.bug-records"
              />
              <span class="selection-hint">已选 {{ datasets.bug.selectedRows.length }} 条</span>
              <el-button @click="selectAllRecords('bug')" :disabled="!datasets.bug.records.length">全选</el-button>
              <el-button
                type="danger"
                plain
                :disabled="!datasets.bug.selectedRows.length"
                :loading="datasets.bug.clearingRecords"
                @click="clearSelectedRecords('bug')"
              >
                清空所选
              </el-button>
              <el-button @click="refreshRecords('bug')" :loading="datasets.bug.loadingRecords">刷新数据</el-button>
            </div>
          </div>

          <section
            v-if="showOnlineDefectAnalysis"
            class="online-analysis-panel"
            v-loading="onlineDefectAnalysis.loading"
          >
            <div class="online-analysis-panel__header">
              <div>
                <h3>线上缺陷质量统计</h3>
                <span>{{ onlineAnalysisScopeLabel }}</span>
              </div>
              <el-button size="small" @click="loadOnlineDefectAnalysis" :loading="onlineDefectAnalysis.loading">
                刷新统计
              </el-button>
            </div>
            <div
              v-if="onlineDefectAnalysisHasData"
              ref="onlineDefectAnalysisChartRef"
              class="online-analysis-chart"
            />
            <el-empty v-else description="暂无线上缺陷统计数据" />
          </section>

          <div class="table-panel">
            <el-table
              ref="bugTableRef"
              v-loading="datasets.bug.loadingRecords"
              :data="datasets.bug.records"
              :max-height="recordTableMaxHeight"
              row-key="id"
              stripe
              class="records-table"
              @selection-change="selection => handleSelectionChange('bug', selection)"
            >
              <el-table-column type="selection" width="52" fixed="left" />
              <el-table-column
                v-if="!useLinkedVersion"
                prop="version"
                label="版本号"
                min-width="160"
                sortable
                :filters="bugColumnFilters.version"
                :filter-method="filterByField('version')"
              />
              <el-table-column
                v-for="field in JIRA_BUG_VISIBLE_FIELD_DEFINITIONS"
                :key="`bug-${field.key}`"
                :prop="field.key"
                :label="field.label"
                :min-width="field.minWidth || 160"
                :fixed="field.fixed"
                :show-overflow-tooltip="Boolean(field.overflow)"
                sortable
                :sort-method="sortByResolver(row => getBugFieldValue(row, field.key))"
                :filters="bugColumnFilters[field.key]"
                :filter-method="filterByResolver(row => getBugFieldValue(row, field.key))"
              >
                <template #default="{ row }">
                  <a
                    v-if="field.key === 'issuekey' && getBugFieldValue(row, field.key)"
                    :href="getJiraBrowseUrl(getBugFieldValue(row, field.key))"
                    class="jira-link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ getBugFieldValue(row, field.key) }}
                  </a>
                  <span v-else>{{ getBugFieldValue(row, field.key) || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column
                v-for="field in datasets.bug.extraVisibleFields"
                :key="`bug-extra-${field}`"
                :label="getRawFieldLabel('bug', field)"
                min-width="180"
                show-overflow-tooltip
                sortable
                :sort-method="sortByRawField(field)"
                :filters="getExtraFieldFilters('bug', field)"
                :filter-method="filterByRawField(field)"
              >
                <template #default="{ row }">{{ getRawField(row, field) || '-' }}</template>
              </el-table-column>
              <el-table-column
                prop="synced_at"
                label="同步时间"
                min-width="180"
                sortable
                :sort-method="sortByDateField('synced_at')"
                :filters="bugColumnFilters.synced_at"
                :filter-method="filterByFormattedField('synced_at', formatDate)"
              >
                <template #default="{ row }">{{ formatDate(row.synced_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openAssociationDialog(row)">关联</el-button>
                  <el-button link type="primary" @click="openRecordDetail('bug', row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-model:current-page="datasets.bug.pagination.page"
              v-model:page-size="datasets.bug.pagination.pageSize"
              layout="total, sizes, prev, pager, next, jumper"
              :page-sizes="[10, 20, 50, 100]"
              :total="datasets.bug.pagination.total"
              class="tab-pagination"
              @current-change="handleRecordPageChange('bug')"
              @size-change="handleRecordPageSizeChange('bug')"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="JIRA需求数据" name="requirement-records">
          <div class="toolbar">
            <div class="toolbar-left">
              <el-select
                v-if="!useLinkedVersion"
                v-model="datasets.requirement.filters.version"
                clearable
                filterable
                placeholder="按版本号筛选"
                style="width: 260px"
                @change="handleVersionChange('requirement')"
              >
                <el-option
                  v-for="item in versionOptions.requirement"
                  :key="item.version"
                  :label="`${item.version}${item.record_count ? ` (${item.record_count}条)` : ''}`"
                  :value="item.version"
                />
              </el-select>
              <el-select
                v-model="datasets.requirement.extraVisibleFields"
                multiple
                clearable
                collapse-tags
                collapse-tags-tooltip
                filterable
                placeholder="扩展字段"
                class="extra-field-select"
              >
                <el-option
                  v-for="item in requirementExtraFieldOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <el-input
                v-model="datasets.requirement.filters.keyword"
                clearable
                placeholder="搜索需求编号或需求标题"
                style="width: 320px"
                @keyup.enter="handleRecordFilterChange('requirement')"
                @clear="handleRecordFilterChange('requirement')"
              />
            </div>
            <div class="toolbar-right">
              <TableColumnSettings
                :table-ref="requirementTableRef"
                storage-key="manual-testcases.requirement-records"
              />
              <span class="selection-hint">已选 {{ datasets.requirement.selectedRows.length }} 条</span>
              <el-button @click="selectAllRecords('requirement')" :disabled="!datasets.requirement.records.length">
                全选
              </el-button>
              <el-button
                type="danger"
                plain
                :disabled="!datasets.requirement.selectedRows.length"
                :loading="datasets.requirement.clearingRecords"
                @click="clearSelectedRecords('requirement')"
              >
                清空所选
              </el-button>
              <el-button @click="refreshRecords('requirement')" :loading="datasets.requirement.loadingRecords">
                刷新数据
              </el-button>
            </div>
          </div>

          <div class="table-panel">
            <el-table
              ref="requirementTableRef"
              v-loading="datasets.requirement.loadingRecords"
              :data="datasets.requirement.records"
              :max-height="recordTableMaxHeight"
              row-key="id"
              stripe
              class="records-table"
              @selection-change="selection => handleSelectionChange('requirement', selection)"
            >
              <el-table-column type="selection" width="52" fixed="left" />
              <el-table-column
                v-if="!useLinkedVersion"
                prop="version"
                label="版本号"
                min-width="160"
                sortable
                :filters="requirementColumnFilters.version"
                :filter-method="filterByField('version')"
              />
              <el-table-column
                v-for="field in JIRA_REQUIREMENT_VISIBLE_FIELD_DEFINITIONS"
                :key="`requirement-${field.key}`"
                :prop="field.key"
                :label="field.label"
                :min-width="field.minWidth || 160"
                :fixed="field.fixed"
                :show-overflow-tooltip="Boolean(field.overflow)"
                sortable
                :sort-method="sortByResolver(row => getRequirementFieldValue(row, field.key))"
                :filters="requirementColumnFilters[field.key]"
                :filter-method="filterByResolver(row => getRequirementFieldValue(row, field.key))"
              >
                <template #default="{ row }">
                  <a
                    v-if="field.key === 'issuekey' && getRequirementFieldValue(row, field.key)"
                    :href="getJiraBrowseUrl(getRequirementFieldValue(row, field.key))"
                    class="jira-link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ getRequirementFieldValue(row, field.key) }}
                  </a>
                  <span v-else>{{ getRequirementFieldValue(row, field.key) || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column
                prop="synced_at"
                label="同步时间"
                min-width="180"
                sortable
                :sort-method="sortByDateField('synced_at')"
                :filters="requirementColumnFilters.synced_at"
                :filter-method="filterByFormattedField('synced_at', formatDate)"
              >
                <template #default="{ row }">{{ formatDate(row.synced_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="230" fixed="right">
                <template #default="{ row }">
                  <div class="record-operation-actions">
                    <el-tooltip
                      :disabled="hasRequirementMindmap(row)"
                      content="没有关联的测试脑图"
                      placement="top"
                    >
                      <span class="record-operation-actions__item">
                        <el-button
                          link
                          type="primary"
                          :disabled="!hasRequirementMindmap(row)"
                          @click="jumpToRequirementTestpoints(row)"
                        >
                          测试点
                        </el-button>
                      </span>
                    </el-tooltip>
                    <el-tooltip
                      :disabled="hasRequirementVersionDefect(row)"
                      content="没有关联的版本缺陷"
                      placement="top"
                    >
                      <span class="record-operation-actions__item">
                        <el-button
                          link
                          type="primary"
                          :disabled="!hasRequirementVersionDefect(row)"
                          @click="jumpToRequirementDefects(row)"
                        >
                          版本缺陷
                        </el-button>
                      </span>
                    </el-tooltip>
                    <el-tooltip
                      :disabled="hasRequirementBugRecord(row)"
                      content="没有关联的线上缺陷"
                      placement="top"
                    >
                      <span class="record-operation-actions__item">
                        <el-button
                          link
                          type="primary"
                          :disabled="!hasRequirementBugRecord(row)"
                          @click="jumpToRequirementBugRecords(row)"
                        >
                          线上缺陷
                        </el-button>
                      </span>
                    </el-tooltip>
                    <el-button link type="primary" @click="openRecordDetail('requirement', row)">详情</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-model:current-page="datasets.requirement.pagination.page"
              v-model:page-size="datasets.requirement.pagination.pageSize"
              layout="total, sizes, prev, pager, next, jumper"
              :page-sizes="[10, 20, 50, 100]"
              :total="datasets.requirement.pagination.total"
              class="tab-pagination"
              @current-change="handleRecordPageChange('requirement')"
              @size-change="handleRecordPageSizeChange('requirement')"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="JIRA接口" name="configs">
          <section class="config-section">
            <div class="config-section-header">
              <div>
                <h3>JIRA接口</h3>
                <p>BUG 接口配置与 JIRA 需求接口配置已合并为统一列表，可按接口类型区分；执行前会先清空当前版本历史数据。</p>
              </div>
              <div class="toolbar-right">
                <TableColumnSettings
                  :table-ref="configTableRef"
                  storage-key="manual-testcases.jira-configs"
                />
                <el-button type="primary" @click="openCreateDialog()">新增配置</el-button>
                <el-button @click="refreshConfigList" :loading="loadingCombinedConfigs">刷新配置</el-button>
              </div>
            </div>

            <div class="table-panel">
              <el-table
                ref="configTableRef"
                v-loading="loadingCombinedConfigs"
                :data="mergedConfigs"
                :max-height="recordTableMaxHeight"
                stripe
                class="config-table"
              >
                <el-table-column
                  label="接口类型"
                  width="110"
                  align="center"
                  sortable
                  :sort-method="sortByResolver(getConfigInterfaceType)"
                  :filters="configColumnFilters.interface_type"
                  :filter-method="filterByResolver(getConfigInterfaceType)"
                >
                  <template #default="{ row }">
                    <el-tag :type="row.interface_type === 'bug' ? 'danger' : 'success'">
                      {{ formatInterfaceType(row.interface_type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="version"
                  label="版本号"
                  min-width="160"
                  sortable
                  :sort-method="sortByTextField('version')"
                  :filters="configColumnFilters.version"
                  :filter-method="filterByField('version')"
                />
                <el-table-column
                  prop="name"
                  label="配置名称"
                  min-width="150"
                  sortable
                  :sort-method="sortByTextField('name')"
                  :filters="configColumnFilters.name"
                  :filter-method="filterByField('name')"
                />
                <el-table-column
                  prop="request_method"
                  label="方法"
                  width="90"
                  sortable
                  :sort-method="sortByTextField('request_method')"
                  :filters="configColumnFilters.request_method"
                  :filter-method="filterByField('request_method')"
                />
                <el-table-column
                  prop="request_url"
                  label="请求 URL"
                  min-width="260"
                  show-overflow-tooltip
                  sortable
                  :sort-method="sortByTextField('request_url')"
                  :filters="configColumnFilters.request_url"
                  :filter-method="filterByField('request_url')"
                />
                <el-table-column
                  prop="timeout_seconds"
                  label="超时(秒)"
                  width="100"
                  align="center"
                  sortable
                  :sort-method="sortByNumberField('timeout_seconds')"
                  :filters="configColumnFilters.timeout_seconds"
                  :filter-method="filterByResolver(getConfigTimeoutSeconds)"
                />
                <el-table-column
                  label="启用"
                  width="90"
                  align="center"
                  sortable
                  :sort-method="sortByResolver(getConfigActiveLabel)"
                  :filters="configColumnFilters.is_active"
                  :filter-method="filterByResolver(getConfigActiveLabel)"
                >
                  <template #default="{ row }">
                    <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column
                  label="同步记录"
                  width="100"
                  align="center"
                  sortable
                  :sort-method="sortByNumberField('last_record_count')"
                  :filters="configColumnFilters.last_record_count"
                  :filter-method="filterByResolver(getConfigLastRecordCount)"
                >
                  <template #default="{ row }">{{ row.last_record_count || 0 }}</template>
                </el-table-column>
                <el-table-column
                  label="最后状态码"
                  width="120"
                  align="center"
                  sortable
                  :sort-method="sortByNumberField('last_status_code')"
                  :filters="configColumnFilters.last_status_code"
                  :filter-method="filterByResolver(getConfigLastStatusCode)"
                >
                  <template #default="{ row }">{{ row.last_status_code || '-' }}</template>
                </el-table-column>
                <el-table-column
                  label="最后执行时间"
                  min-width="180"
                  sortable
                  :sort-method="sortByDateField('last_executed_at')"
                  :filters="configColumnFilters.last_executed_at"
                  :filter-method="filterByResolver(getConfigLastExecutedAt)"
                >
                  <template #default="{ row }">{{ formatDate(row.last_executed_at) }}</template>
                </el-table-column>
                <el-table-column
                  label="最后执行结果"
                  min-width="260"
                  show-overflow-tooltip
                  sortable
                  :sort-method="sortByTextField('last_execution_message')"
                  :filters="configColumnFilters.last_execution_message"
                  :filter-method="filterByField('last_execution_message')"
                >
                  <template #default="{ row }">{{ row.last_execution_message || '-' }}</template>
                </el-table-column>
                <el-table-column label="操作" width="280" fixed="right">
                  <template #default="{ row }">
                    <div class="action-group config-action-group">
                      <el-button
                        size="small"
                        type="primary"
                        :loading="datasets[row.interface_type].executingId === row.id"
                        @click="executeConfig(row.interface_type, row)"
                      >
                        执行
                      </el-button>
                      <el-button size="small" @click="openEditDialog(row.interface_type, row)">编辑</el-button>
                      <el-button size="small" @click="openCopyDialog(row.interface_type, row)">复制</el-button>
                      <el-button size="small" type="danger" plain @click="deleteConfig(row.interface_type, row)">
                        删除
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="JIRA编号URL" name="other-settings">
          <section class="config-section">
            <div class="config-section-header">
              <div>
                <h3>JIRA编号URL</h3>
                <p>配置 JIRA 编号跳转链接的 URL 前缀。列表中点击 JIRA 编号时，会在新标签页打开拼接后的地址。</p>
              </div>
            </div>

            <div class="other-config-form">
              <el-form label-position="top">
                <el-form-item label="JIRA编号URL前缀">
                  <el-input
                    v-model="jiraBrowsePrefix"
                    placeholder="例如：http://172.31.119.34:8080/browse/"
                    clearable
                    :disabled="loadingJiraBrowsePrefix || savingJiraBrowsePrefix"
                    @keyup.enter="saveJiraBrowsePrefix"
                  />
                </el-form-item>
              </el-form>

              <div class="action-group">
                <el-button type="primary" :loading="savingJiraBrowsePrefix" :disabled="loadingJiraBrowsePrefix" @click="saveJiraBrowsePrefix">保存配置</el-button>
              </div>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog
      v-model="configDialogVisible"
      :title="isEditing ? `编辑${currentDialogMeta.label}接口配置` : `新增${currentDialogMeta.label}接口配置`"
      width="820px"
      destroy-on-close
    >
      <el-form ref="configFormRef" :model="configForm" :rules="configRules" label-position="top">
        <el-form-item label="接口类型" prop="interface_type">
          <el-select
            v-model="configForm.interface_type"
            style="width: 100%"
            :disabled="isEditing"
            @change="handleConfigTypeChange"
          >
            <el-option label="BUG" value="bug" />
            <el-option label="需求" value="requirement" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号" prop="version">
          <el-input v-model="configForm.version" maxlength="100" placeholder="例如：26-04.15" />
        </el-form-item>
        <el-form-item label="配置名称">
          <el-input v-model="configForm.name" maxlength="100" :placeholder="`默认：${currentDialogMeta.defaultConfigName}`" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="请求方法">
            <el-select v-model="configForm.request_method" style="width: 100%">
              <el-option label="POST" value="POST" />
              <el-option label="GET" value="GET" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
            </el-select>
          </el-form-item>
          <el-form-item label="超时时间（秒）">
            <el-input-number v-model="configForm.timeout_seconds" :min="1" :max="300" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="auth-section">
          <div class="auth-section__header">
            <h3>JIRA登录认证</h3>
            <p>JIRA要求登录时启用，同步前会先登录并复用会话。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="启用登录">
              <el-switch v-model="configForm.jira_login_enabled" />
            </el-form-item>
            <el-form-item label="登录 URL">
              <el-input v-model="configForm.jira_login_url" placeholder="例如：http://172.31.119.34:8080/login.jsp" />
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="账号">
              <el-input v-model="configForm.jira_username" maxlength="255" placeholder="JIRA登录账号" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="configForm.jira_password"
                type="password"
                show-password
                :placeholder="configForm.has_jira_password ? '已配置，留空则保持原密码不变' : 'JIRA登录密码'"
              />
            </el-form-item>
          </div>
        </div>
        <el-form-item label="请求 URL">
          <el-input v-model="configForm.request_url" placeholder="留空时使用系统默认 URL" />
        </el-form-item>
        <el-form-item label="请求头 JSON">
          <el-input
            v-model="configForm.request_headers_text"
            type="textarea"
            :rows="10"
            placeholder="留空时使用系统默认请求头；编辑时请输入合法 JSON"
          />
        </el-form-item>
        <el-form-item label="表单数据 / 请求体">
          <el-input
            v-model="configForm.request_body"
            type="textarea"
            :rows="8"
            placeholder="留空时根据版本号生成默认请求体"
          />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="是否启用">
            <el-switch v-model="configForm.is_active" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="configForm.notes" placeholder="可选" />
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingConfig" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="associationDialogVisible"
      title="缺陷关联"
      width="880px"
      destroy-on-close
      @close="closeAssociationDialog"
    >
      <div class="association-dialog">
        <div class="association-section">
          <div class="association-section__header">
            <h3>关联需求</h3>
            <p>可按版本搜索并关联历史任一版本的 JIRA 需求。</p>
          </div>
          <div class="association-toolbar">
            <el-select
              v-model="associationForm.requirementVersion"
              clearable
              filterable
              placeholder="选择需求版本"
              style="width: 220px"
              :loading="associationLoadingRequirementVersions"
              @change="loadAssociationRequirementOptions('')"
            >
              <el-option
                v-for="item in associationRequirementVersionOptions"
                :key="item.version"
                :label="item.version"
                :value="item.version"
              />
            </el-select>
            <el-select
              v-model="associationForm.relatedRequirements"
              value-key="issue_key"
              multiple
              filterable
              remote
              reserve-keyword
              clearable
              collapse-tags
              collapse-tags-tooltip
              default-first-option
              placeholder="搜索并选择需求"
              class="association-select"
              :loading="associationLoadingRequirements"
              :remote-method="loadAssociationRequirementOptions"
              @visible-change="visible => visible && loadAssociationRequirementOptions('')"
            >
              <el-option
                v-for="item in associationRequirementOptions"
                :key="item.issue_key"
                :label="formatRequirementAssociationLabel(item)"
                :value="item"
              />
            </el-select>
          </div>
        </div>

        <div class="association-section">
          <div class="association-section__header">
            <h3>关联测试用例</h3>
            <p>基于左侧当前项目，按版本检索历史测试用例节点。</p>
          </div>
          <div class="association-toolbar">
            <el-select
              v-model="associationForm.manualVersionId"
              clearable
              filterable
              placeholder="选择测试版本"
              style="width: 220px"
              :loading="associationLoadingManualVersions"
              @change="handleAssociationManualVersionChange"
            >
              <el-option
                v-for="item in associationManualVersionOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
            <el-select
              v-model="associationForm.relatedTestcases"
              value-key="relation_key"
              multiple
              filterable
              remote
              reserve-keyword
              clearable
              collapse-tags
              collapse-tags-tooltip
              default-first-option
              placeholder="搜索并选择测试用例"
              class="association-select"
              :loading="associationLoadingTestcases"
              :remote-method="keyword => loadAssociationManualOptions('case', keyword)"
              @visible-change="visible => visible && loadAssociationManualOptions('case')"
            >
              <el-option
                v-for="item in associationTestcaseOptions"
                :key="item.relation_key"
                :label="formatManualAssociationLabel(item, 'case')"
                :value="item"
              />
            </el-select>
          </div>
        </div>

        <div class="association-section">
          <div class="association-section__header">
            <h3>关联测试点</h3>
            <p>支持从历史版本测试点中选择并保存关联。</p>
          </div>
          <div class="association-toolbar">
            <el-input
              :model-value="getAssociationManualVersionName() || '测试点与测试用例共用所选测试版本'"
              disabled
              style="width: 220px"
            />
            <el-select
              v-model="associationForm.relatedTestpoints"
              value-key="relation_key"
              multiple
              filterable
              remote
              reserve-keyword
              clearable
              collapse-tags
              collapse-tags-tooltip
              default-first-option
              placeholder="搜索并选择测试点"
              class="association-select"
              :loading="associationLoadingTestpoints"
              :remote-method="keyword => loadAssociationManualOptions('testpoint', keyword)"
              @visible-change="visible => visible && loadAssociationManualOptions('testpoint')"
            >
              <el-option
                v-for="item in associationTestpointOptions"
                :key="item.relation_key"
                :label="formatManualAssociationLabel(item, 'testpoint')"
                :value="item"
              />
            </el-select>
          </div>
        </div>

        <div v-if="!linkedProjectId" class="association-tip">
          当前未关联项目，暂时只能保存需求关联；测试用例和测试点关联需要先选中左侧项目。
        </div>
      </div>

      <template #footer>
        <el-button @click="closeAssociationDialog">取消</el-button>
        <el-button type="primary" :loading="associationSaving" @click="saveBugAssociations">保存关联</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" :title="currentDetailTitle" :size="currentDetailDrawerSize">
      <template v-if="detailRecord">
        <el-descriptions
          v-if="currentDetailFields.length"
          :column="currentDetailColumns"
          border
          class="detail-descriptions"
        >
          <el-descriptions-item v-for="item in currentDetailFields" :key="item.key" :label="item.label">
            {{ item.value }}
          </el-descriptions-item>
        </el-descriptions>
        <div v-else class="detail-empty">当前记录暂无更多未在列表中展示的字段</div>

        <div v-if="currentAssociationSections.length" class="association-summary">
          <div
            v-for="section in currentAssociationSections"
            :key="section.key"
            class="association-summary__section"
          >
            <h3>{{ section.title }}</h3>
            <div class="association-summary__list">
              <div
                v-for="item in section.items"
                :key="item.key"
                class="association-summary__item"
              >
                <a
                  v-if="section.key === 'requirements'"
                  :href="getJiraBrowseUrl(item.key)"
                  class="jira-link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ item.label }}
                </a>
                <span v-else>{{ item.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="raw-panel">
          <h3>原始字段</h3>
          <pre>{{ formattedRawFields }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import TableColumnSettings from '@/components/common/TableColumnSettings.vue'
import {
  DEFECT_RELATION_FIELD_LIMITS,
  decorateDefectRelationItem,
  getDefectRelationOptionLabel,
} from '@/utils/defectRelations'
import {
  JIRA_REQUIREMENT_ALL_FIELD_KEYS,
  JIRA_REQUIREMENT_FIELD_LABELS,
  JIRA_REQUIREMENT_VISIBLE_FIELD_DEFINITIONS,
} from '@/utils/jiraRequirementFields'
import {
  JIRA_BUG_ALL_FIELD_KEYS,
  JIRA_BUG_FIELD_LABELS,
  JIRA_BUG_VISIBLE_FIELD_DEFINITIONS,
} from '@/utils/jiraBugFields'

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  defaultTab: {
    type: String,
    default: 'bug-records',
  },
  active: {
    type: Boolean,
    default: true,
  },
  useLinkedVersion: {
    type: Boolean,
    default: false,
  },
  linkedVersion: {
    type: String,
    default: '',
  },
  linkedKeyword: {
    type: String,
    default: '',
  },
  linkedBugKeyword: {
    type: String,
    default: '',
  },
  linkedBugTestpointId: {
    type: String,
    default: '',
  },
  linkedModules: {
    type: Array,
    default: () => [],
  },
  linkedProjectId: {
    type: [Number, String],
    default: null,
  },
  showOnlineDefectAnalysis: {
    type: Boolean,
    default: true,
  },
})

const route = useRoute()
const router = useRouter()

const AVAILABLE_TABS = new Set(['bug-records', 'requirement-records', 'configs', 'other-settings'])

const COMBINED_CONFIG_ENDPOINT = '/quality-analysis/jira-configs/combined/'
const QUALITY_ANALYSIS_SETTINGS_ENDPOINT = '/quality-analysis/settings/'

const DATASET_META = {
  bug: {
    label: '线上缺陷',
    detailTitle: '线上缺陷详情',
    issueTypeLabel: '问题类型',
    summaryLabel: '标题',
    defaultConfigName: 'JIRA线上BUG接口',
    recordEndpoint: '/quality-analysis/jira-bug-records/',
    versionEndpoint: '/quality-analysis/jira-bug-records/versions/',
    configEndpoint: '/quality-analysis/jira-configs/',
  },
  requirement: {
    label: 'JIRA需求',
    detailTitle: 'JIRA需求详情',
    issueTypeLabel: '需求类型',
    summaryLabel: '需求标题',
    defaultConfigName: 'JIRA需求接口',
    recordEndpoint: '/quality-analysis/jira-requirement-records/',
    versionEndpoint: '/quality-analysis/jira-requirement-records/versions/',
    configEndpoint: '/quality-analysis/jira-requirement-configs/',
  },
}

const createDatasetState = () => ({
  loadingRecords: false,
  clearingRecords: false,
  loadingConfigs: false,
  executingId: null,
  records: [],
  configs: [],
  versionSummaries: [],
  selectedRows: [],
  extraVisibleFields: [],
  knownExtraFields: [],
  hasInitializedExtraFields: false,
  filters: {
    version: '',
    keyword: '',
    testpointId: '',
  },
  pagination: {
    page: 1,
    pageSize: 10,
    total: 0,
  },
})

const activeTab = ref(AVAILABLE_TABS.has(props.defaultTab) ? props.defaultTab : 'bug-records')
const jiraBrowsePrefix = ref('')
const loadingJiraBrowsePrefix = ref(false)
const savingJiraBrowsePrefix = ref(false)
const recordTableMaxHeight = 'calc(100vh - 250px)'
const combinedConfigs = ref([])
const loadingCombinedConfigs = ref(false)
const savingConfig = ref(false)
const detailVisible = ref(false)
const configDialogVisible = ref(false)
const associationDialogVisible = ref(false)
const configFormRef = ref(null)
const bugTableRef = ref(null)
const requirementTableRef = ref(null)
const configTableRef = ref(null)
const associationSaving = ref(false)
const associationLoadingRequirementVersions = ref(false)
const associationLoadingManualVersions = ref(false)
const associationLoadingRequirements = ref(false)
const associationLoadingTestcases = ref(false)
const associationLoadingTestpoints = ref(false)

const datasets = reactive({
  bug: createDatasetState(),
  requirement: createDatasetState(),
})

const dialogState = reactive({
  datasetType: 'bug',
  editingId: null,
})

const detailState = reactive({
  datasetType: 'bug',
  record: null,
})

const associationState = reactive({
  record: null,
})

const configForm = reactive({
  interface_type: 'bug',
  version: '',
  name: '',
  request_url: '',
  request_method: 'POST',
  request_headers_text: '',
  request_body: '',
  timeout_seconds: 60,
  jira_login_enabled: true,
  jira_login_url: DEFAULT_JIRA_LOGIN_URL,
  jira_username: '',
  jira_password: '',
  has_jira_password: false,
  is_active: true,
  notes: '',
})

const associationForm = reactive({
  requirementVersion: '',
  manualVersionId: '',
  relatedRequirements: [],
  relatedTestcases: [],
  relatedTestpoints: [],
})

const associationRequirementVersionOptions = ref([])
const associationManualVersionOptions = ref([])
const associationRequirementOptions = ref([])
const associationTestcaseOptions = ref([])
const associationTestpointOptions = ref([])
const onlineDefectAnalysisChartRef = ref(null)
let onlineDefectAnalysisChart = null

const onlineDefectAnalysis = reactive({
  loading: false,
  data: null,
})

const configRules = {
  interface_type: [{ required: true, message: '请选择接口类型', trigger: 'change' }],
  version: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
}

const bugRawFieldMap = {
  tester: 'customfield_10222',
  productManager: 'customfield_10737',
  bugOwner: 'customfield_10731',
  rootCause: 'customfield_11102',
  bugCategory: 'customfield_11101',
  directRole: 'customfield_11103',
  createdDate: 'created',
  devPriority: 'customfield_11100',
  frontendEstimate: 'customfield_10749',
  backendEstimate: 'customfield_10748',
  testEstimate: 'customfield_10761',
  testProgress: 'customfield_10746',
  overallProgress: 'customfield_10765',
  pmProgress: 'customfield_10738',
  frontendDeveloper: 'customfield_10743',
  backendDeveloper: 'customfield_10741',
  bugFeedback: 'customfield_10754',
  reopenCount: 'customfield_10019',
}

const RAW_FIELD_LABELS = {
  issuekey: '编号',
  key: '编号',
  keyword: '关键字',
  issuetype: '问题类型',
  summary: '概要',
  components: '模块',
  status: '状态',
  creator: '创建人',
  reporter: '报告人',
  assignee: '经办人',
  created: '创建日期',
  updated: '更新时间',
  due: '到期日期',
  resolution: '解决结果',
  versions: '影响版本',
  fixforversions: '修复版本',
  customfield_10762: '客户或项目名称',
  customfield_10702: '任务优先级',
  customfield_10222: '测试人员',
  customfield_10100: '必须发版',
  customfield_10737: 'PM',
  customfield_10731: 'BUG责任人',
  customfield_11102: 'BUG产生根因',
  customfield_11101: 'BUG定性分类',
  customfield_11103: 'BUG直接责任岗位',
  customfield_11100: '版本内研发优先级别',
  customfield_10014: '预计提测日期',
  customfield_10015: '用例预估完成时间',
  customfield_10602: '前端是否完成',
  customfield_10603: '后端是否完成',
  customfield_10749: '前端预估工时',
  customfield_10748: '后端预估工时',
  customfield_10761: '测试预估工时',
  customfield_10746: '测试进度',
  customfield_10765: '整体进度|延期原因',
  customfield_10738: 'PM进度',
  customfield_10743: '前端',
  customfield_10741: '后端',
  customfield_11017: '前端结束日期',
  customfield_11018: '提测时间',
  customfield_10754: 'BUG处理反馈',
  customfield_10019: 'BUG重新打开次数',
  customfield_11000: '组别',
  customfield_11020: '测试进展',
  customfield_10522: '后端开始日期',
  customfield_10523: '前端开始日期',
  customfield_11019: '后端结束日期',
}

const RAW_FIELD_EXCLUDED_KEYS = {
  bug: new Set([
    'key',
    'keyword',
    'assignee',
    ...JIRA_BUG_ALL_FIELD_KEYS,
  ]),
  requirement: new Set([
    'assignee',
    ...JIRA_REQUIREMENT_ALL_FIELD_KEYS,
  ]),
}

const RAW_FIELD_LABELS_META_KEY = '__field_labels'

const BUG_FIXED_FIELD_ALIASES = {
  issue_key: ['issuekey', 'key', 'keyword', '关键字', '缺陷编号', '问题编号', 'BUG编号', 'JIRA编号'],
  issue_type: ['issuetype', '问题类型', '类型', '缺陷类型', 'BUG类型'],
  summary: ['summary', '概要', '标题', '缺陷标题', '问题标题'],
  module: ['components', 'component', '模块', '所属模块', '功能模块'],
  customer_name: ['customfield_10762', '客户或项目名称', '客户', '项目名称'],
  priority: ['customfield_10702', '任务优先级', '优先级', '严重级别', '缺陷等级'],
  status: ['status', '状态', '处理状态'],
  creator: ['creator', 'reporter', '创建者', '创建人', '报告人'],
  tester: ['customfield_10222', '测试人员', '测试工程师', '测试'],
  product_manager: ['customfield_10737', 'PM', '产品经理', '产品负责人'],
  group_name: ['customfield_11000', 'group_name', '责任小组', '组别', '负责小组', '所属组别'],
  bug_owner: ['customfield_10731', 'assignee', 'BUG责任人', '缺陷责任人', '责任人', '经办人'],
  root_cause: ['customfield_11102', 'BUG产生原因', 'BUG产生根因', '问题原因', '问题根因', '根因'],
  bug_category: ['customfield_11101', 'BUG定性分类', '缺陷分类'],
  direct_role: ['customfield_11103', 'BUG直接责任岗位', '直接责任岗位'],
  frontend_developer: ['customfield_10743', 'frontend', 'front_end', '前端', '前端开发', '前端开发工程师'],
  backend_developer: ['customfield_10741', 'backend', 'back_end', '后端', '后端开发', '后端开发工程师'],
  created_date: ['created', '创建日期'],
}

const SEMANTIC_DISPLAY_LABELS = {
  bug: {
    issue_key: '缺陷编号',
    group_name: '组别',
    frontend_developer: '前端',
    backend_developer: '后端',
  },
}

const INTERFACE_TYPE_LABELS = {
  bug: 'BUG',
  requirement: '需求',
}

const isEditing = computed(() => Boolean(dialogState.editingId))
const currentDialogMeta = computed(() => DATASET_META[dialogState.datasetType])
const currentDetailMeta = computed(() => DATASET_META[detailState.datasetType])
const detailRecord = computed(() => detailState.record)
const normalizedLinkedVersion = computed(() => normalizeText(props.linkedVersion))
const normalizedLinkedKeyword = computed(() => normalizeText(props.linkedKeyword))
const normalizedLinkedBugKeyword = computed(() => normalizeText(props.linkedBugKeyword))
const normalizedLinkedBugTestpointId = computed(() => normalizeText(props.linkedBugTestpointId))
const normalizedLinkedModules = computed(() => (
  Array.from(
    new Set(
      (Array.isArray(props.linkedModules) ? props.linkedModules : [])
        .map(normalizeText)
        .filter(Boolean)
    )
  )
))
const currentBugAnalysisVersion = computed(() => (
  props.useLinkedVersion ? normalizedLinkedVersion.value : normalizeText(datasets.bug.filters.version)
))
const onlineAnalysisScopeLabel = computed(() => (
  currentBugAnalysisVersion.value
    ? `当前版本：${currentBugAnalysisVersion.value}`
    : '全部版本，近12个月'
))
const onlineDefectAnalysisHasData = computed(() => {
  const payload = onlineDefectAnalysis.data
  if (!payload || !Array.isArray(payload.categories) || !Array.isArray(payload.series)) {
    return false
  }
  return payload.series.some(item => Array.isArray(item.data) && item.data.some(value => Number(value || 0) > 0))
})

const syncLinkedRecordKeywords = () => {
  if (!props.embedded) {
    return
  }

  datasets.bug.filters.keyword = normalizedLinkedBugKeyword.value
  datasets.bug.filters.testpointId = normalizedLinkedBugTestpointId.value
  datasets.requirement.filters.keyword = normalizedLinkedKeyword.value
}
const mergedConfigs = computed(() =>
  [...combinedConfigs.value].sort((left, right) => {
    const rightTime = new Date(right.updated_at || right.last_executed_at || 0).getTime() || 0
    const leftTime = new Date(left.updated_at || left.last_executed_at || 0).getTime() || 0
    if (rightTime !== leftTime) {
      return rightTime - leftTime
    }
    return compareText(left.version, right.version)
  })
)
const currentDetailTitle = computed(() => {
  const title = currentDetailMeta.value.detailTitle
  const issueKey = normalizeText(detailRecord.value?.issue_key)
  return issueKey ? `${title} · ${issueKey}` : title
})
const currentDetailDrawerSize = computed(() => (currentDetailColumns.value === 3 ? '1080px' : '900px'))

const formattedRawFields = computed(() => {
  if (!detailRecord.value) {
    return '{}'
  }
  const rawFields = detailRecord.value.raw_fields || {}
  const visibleRawFields = Object.fromEntries(
    Object.entries(rawFields).filter(([fieldKey]) => !normalizeText(fieldKey).startsWith('__'))
  )
  return JSON.stringify(visibleRawFields, null, 2)
})

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  return date.toLocaleString('zh-CN')
}

const normalizeText = value => String(value ?? '').trim()
const compareText = (left, right) => normalizeText(left).localeCompare(normalizeText(right), 'zh-CN')
const formatInterfaceType = type => INTERFACE_TYPE_LABELS[type] || '-'
const getConfigInterfaceType = row => formatInterfaceType(row?.interface_type)
const getConfigActiveLabel = row => (row?.is_active ? '启用' : '停用')
const getConfigTimeoutSeconds = row => String(Number(row?.timeout_seconds || 0))
const getConfigLastRecordCount = row => String(Number(row?.last_record_count || 0))
const getConfigLastStatusCode = row => normalizeText(row?.last_status_code) || '-'
const getConfigLastExecutedAt = row => formatDate(row?.last_executed_at)
const normalizeApiList = data => (Array.isArray(data) ? data : data?.results || [])
const getApiListTotal = data => {
  if (Array.isArray(data)) {
    return data.length
  }
  const count = Number(data?.count)
  return Number.isFinite(count) ? count : normalizeApiList(data).length
}
const linkedProjectId = computed(() => {
  const parsedValue = Number(props.linkedProjectId)
  if (Number.isNaN(parsedValue) || parsedValue <= 0) {
    return null
  }
  return parsedValue
})

const normalizeRequirementAssociationItem = item => {
  const issueKey = normalizeText(item?.issue_key)
  if (!issueKey) {
    return null
  }

  return {
    issue_key: issueKey,
    summary: normalizeText(item?.summary),
    version: normalizeText(item?.version),
  }
}

const ensureUniqueRequirementAssociationItems = items => {
  const itemMap = new Map()

  ;(Array.isArray(items) ? items : []).forEach(item => {
    const normalizedItem = normalizeRequirementAssociationItem(item)
    if (!normalizedItem) {
      return
    }
    itemMap.set(normalizedItem.issue_key, normalizedItem)
  })

  return [...itemMap.values()]
}

const formatRequirementAssociationLabel = item => {
  const normalizedItem = normalizeRequirementAssociationItem(item)
  if (!normalizedItem) {
    return '-'
  }

  const title = normalizedItem.summary ? `${normalizedItem.issue_key} - ${normalizedItem.summary}` : normalizedItem.issue_key
  return normalizedItem.version ? `${title} [${normalizedItem.version}]` : title
}

const decorateJiraManualRelationItem = (item = {}, defaultNodeType = '') => {
  const decoratedItem = decorateDefectRelationItem(item, defaultNodeType)
  if (!decoratedItem) {
    return null
  }

  return {
    ...decoratedItem,
    version_name: normalizeText(item?.version_name).slice(0, DEFECT_RELATION_FIELD_LIMITS.version_name),
  }
}

const ensureUniqueJiraManualRelationItems = (items = [], defaultNodeType = '') => {
  const itemMap = new Map()

  ;(Array.isArray(items) ? items : []).forEach(item => {
    const decoratedItem = decorateJiraManualRelationItem(item, defaultNodeType)
    if (!decoratedItem) {
      return
    }
    itemMap.set(decoratedItem.relation_key, decoratedItem)
  })

  return [...itemMap.values()]
}

const serializeJiraManualRelationItems = (items = [], defaultNodeType = '') =>
  ensureUniqueJiraManualRelationItems(items, defaultNodeType).map(item => ({
    id: item.id,
    mindmap_id: item.mindmap_id,
    mindmap_name: item.mindmap_name,
    node_text: item.node_text,
    node_type: item.node_type || defaultNodeType,
    path: item.path,
    parent_text: item.parent_text,
    case_id: item.case_id,
    responsibility_group: item.responsibility_group,
    version_name: item.version_name,
  }))

const formatManualAssociationLabel = (item = {}, defaultNodeType = '') => {
  const decoratedItem = decorateJiraManualRelationItem(item, defaultNodeType)
  if (!decoratedItem) {
    return '-'
  }

  const baseLabel = getDefectRelationOptionLabel(decoratedItem, defaultNodeType)
  return decoratedItem.version_name ? `${baseLabel} [${decoratedItem.version_name}]` : baseLabel
}

const DEFAULT_JIRA_BROWSE_BASE_URL = 'http://172.31.119.34:8080/browse/'
const DEFAULT_JIRA_LOGIN_URL = 'http://172.31.119.34:8080/login.jsp'

const normalizeJiraBrowsePrefix = value => {
  const normalized = normalizeText(value)
  if (!normalized) {
    return DEFAULT_JIRA_BROWSE_BASE_URL
  }
  return normalized.endsWith('/') ? normalized : `${normalized}/`
}

const getJiraBrowseUrl = issueKey => `${normalizeJiraBrowsePrefix(jiraBrowsePrefix.value)}${encodeURIComponent(normalizeText(issueKey))}`

const normalizeSemanticText = value => normalizeText(value)
  .toLowerCase()
  .replace(/[\s_\-:：|/\\.,;，。；、()\[\]{}（）【】<>《》]+/g, '')
const isRawFieldMetadataKey = fieldKey => normalizeText(fieldKey).startsWith('__')
const getRawFields = row => row?.raw_fields || {}
const getRawFieldLabelsFromRow = row => {
  const rawFields = getRawFields(row)
  const labels = row?.raw_field_labels || rawFields[RAW_FIELD_LABELS_META_KEY] || {}
  return labels && typeof labels === 'object' && !Array.isArray(labels) ? labels : {}
}
const findRawFieldKey = (row, fieldKey) => {
  const normalized = normalizeText(fieldKey)
  if (!normalized || isRawFieldMetadataKey(normalized)) {
    return ''
  }

  const rawFields = getRawFields(row)
  if (Object.prototype.hasOwnProperty.call(rawFields, normalized)) {
    return normalized
  }

  return Object.keys(rawFields).find(key => normalizeText(key) === normalized && !isRawFieldMetadataKey(key)) || ''
}
const getRawField = (row, fieldKey) => {
  const resolvedKey = findRawFieldKey(row, fieldKey)
  if (!resolvedKey) {
    return ''
  }
  return normalizeText(getRawFields(row)[resolvedKey])
}
const semanticMatches = (candidates, aliases) => {
  const aliasTokens = (Array.isArray(aliases) ? aliases : [aliases]).map(normalizeSemanticText).filter(Boolean)
  if (!aliasTokens.length) {
    return false
  }

  return (Array.isArray(candidates) ? candidates : [candidates]).some(candidate => {
    const candidateToken = normalizeSemanticText(candidate)
    if (!candidateToken) {
      return false
    }
    return aliasTokens.some(aliasToken => (
      candidateToken === aliasToken ||
      (aliasToken.length >= 2 && (candidateToken.includes(aliasToken) || aliasToken.includes(candidateToken)))
    ))
  })
}
const getKnownRawFieldLabel = (fieldKey, type = '') => {
  const normalized = normalizeText(fieldKey)
  if (!normalized) {
    return ''
  }
  if (type === 'requirement' && JIRA_REQUIREMENT_FIELD_LABELS[normalized]) {
    return JIRA_REQUIREMENT_FIELD_LABELS[normalized]
  }
  if (type === 'bug' && JIRA_BUG_FIELD_LABELS[normalized]) {
    return JIRA_BUG_FIELD_LABELS[normalized]
  }
  if (type === 'bug' && semanticMatches(normalized, BUG_FIXED_FIELD_ALIASES.issue_key)) {
    return '缺陷编号'
  }
  if (RAW_FIELD_LABELS[normalized]) {
    return RAW_FIELD_LABELS[normalized]
  }
  return ''
}
const getRawFieldLabelFromRow = (row, fieldKey, type = '') => {
  const resolvedKey = findRawFieldKey(row, fieldKey) || normalizeText(fieldKey)
  const dynamicLabels = getRawFieldLabelsFromRow(row)
  const dynamicLabel = normalizeText(dynamicLabels[resolvedKey] || dynamicLabels[normalizeText(resolvedKey)])
  const knownLabel = getKnownRawFieldLabel(resolvedKey, type)
  return normalizeSemanticDisplayLabel(type, dynamicLabel || knownLabel || resolvedKey)
}
const getSemanticRawFieldKey = (row, aliases, type = '') => {
  const rawFields = getRawFields(row)
  return Object.keys(rawFields).find(fieldKey => {
    if (isRawFieldMetadataKey(fieldKey)) {
      return false
    }
    return semanticMatches([
      fieldKey,
      getRawFieldLabelFromRow(row, fieldKey, type),
      getKnownRawFieldLabel(fieldKey, type),
    ], aliases)
  }) || ''
}
const getSemanticRawField = (row, aliases, type = '') => {
  const resolvedKey = getSemanticRawFieldKey(row, aliases, type)
  return resolvedKey ? getRawField(row, resolvedKey) : ''
}
const getMappedField = (row, fieldKey) => normalizeText(row?.mapped_fields?.[fieldKey])
const normalizeSemanticDisplayLabel = (type, label) => {
  const normalized = normalizeText(label)
  if (!normalized || type !== 'bug') {
    return normalized
  }
  if (semanticMatches(normalized, BUG_FIXED_FIELD_ALIASES.issue_key)) {
    return SEMANTIC_DISPLAY_LABELS.bug.issue_key
  }
  if (semanticMatches(normalized, BUG_FIXED_FIELD_ALIASES.group_name)) {
    return SEMANTIC_DISPLAY_LABELS.bug.group_name
  }
  if (semanticMatches(normalized, BUG_FIXED_FIELD_ALIASES.frontend_developer)) {
    return SEMANTIC_DISPLAY_LABELS.bug.frontend_developer
  }
  if (semanticMatches(normalized, BUG_FIXED_FIELD_ALIASES.backend_developer)) {
    return SEMANTIC_DISPLAY_LABELS.bug.backend_developer
  }
  return normalized
}
const formatRawFieldLabel = (fieldKey, type = '') => {
  const normalized = normalizeText(fieldKey)
  if (!normalized) {
    return '-'
  }
  const knownLabel = getKnownRawFieldLabel(normalized, type)
  if (knownLabel) {
    return normalizeSemanticDisplayLabel(type, knownLabel)
  }

  const customFieldMatched = normalized.match(/^customfield_(\d+)$/)
  if (customFieldMatched) {
    return `自定义字段${customFieldMatched[1]}`
  }

  return normalizeSemanticDisplayLabel(type, normalized.replace(/_/g, ' '))
}
const getRawFieldLabel = (type, fieldKey) => {
  const labelMap = type === 'bug' ? bugRawFieldLabelMap.value : requirementRawFieldLabelMap.value
  return labelMap[normalizeText(fieldKey)] || formatRawFieldLabel(fieldKey, type)
}
const getExtraFieldOptionLabel = (fieldKey, type = '', label = '') => {
  const displayLabel = normalizeSemanticDisplayLabel(type, normalizeText(label)) || formatRawFieldLabel(fieldKey, type)
  const normalizedFieldKey = normalizeText(fieldKey)
  if (!normalizedFieldKey || displayLabel === normalizedFieldKey) {
    return displayLabel || normalizedFieldKey
  }
  return `${displayLabel} (${normalizedFieldKey})`
}
const getBugDefectCode = row => getMappedField(row, 'defect_code') || normalizeText(row?.issue_key) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.issue_key, 'bug')
const getBugIssueType = row => getMappedField(row, 'issue_type') || normalizeText(row?.issue_type) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.issue_type, 'bug')
const getBugSummary = row => getMappedField(row, 'summary') || normalizeText(row?.summary) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.summary, 'bug')
const getBugModule = row => getMappedField(row, 'module') || normalizeText(row?.module) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.module, 'bug')
const getBugCustomerName = row => getMappedField(row, 'customer_name') || normalizeText(row?.customer_name) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.customer_name, 'bug')
const getBugPriority = row => getMappedField(row, 'priority') || normalizeText(row?.priority) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.priority, 'bug')
const getBugStatus = row => getMappedField(row, 'status') || normalizeText(row?.status) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.status, 'bug')
const getBugCreator = row => getMappedField(row, 'creator') || normalizeText(row?.creator) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.creator, 'bug')
const getBugTester = row => getMappedField(row, 'tester') || normalizeText(row?.tester) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.tester, 'bug')
const getBugProductManager = row => getMappedField(row, 'product_manager') || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.product_manager, 'bug') || getRawField(row, bugRawFieldMap.productManager)
const getBugGroupName = row => getMappedField(row, 'group_name') || normalizeText(row?.group_name) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.group_name, 'bug')
const getBugOwner = row => getMappedField(row, 'handler') || normalizeText(row?.handler) || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.bug_owner, 'bug')
const getBugRootCause = row => getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.root_cause, 'bug') || getRawField(row, bugRawFieldMap.rootCause)
const getBugCategory = row => getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.bug_category, 'bug') || getRawField(row, bugRawFieldMap.bugCategory)
const getBugDirectRole = row => getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.direct_role, 'bug') || getRawField(row, bugRawFieldMap.directRole)
const getBugCreatedDate = row => getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.created_date, 'bug') || getRawField(row, bugRawFieldMap.createdDate)
const getBugDevPriority = row => getRawField(row, bugRawFieldMap.devPriority)
const getBugFrontendEstimate = row => getRawField(row, bugRawFieldMap.frontendEstimate)
const getBugBackendEstimate = row => getRawField(row, bugRawFieldMap.backendEstimate)
const getBugTestEstimate = row => getRawField(row, bugRawFieldMap.testEstimate)
const getBugTestProgress = row => getRawField(row, bugRawFieldMap.testProgress)
const getBugOverallProgress = row => getRawField(row, bugRawFieldMap.overallProgress)
const getBugPmProgress = row => getRawField(row, bugRawFieldMap.pmProgress)
const getBugFrontendDeveloper = row => getMappedField(row, 'frontend_developer') || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.frontend_developer, 'bug') || getRawField(row, bugRawFieldMap.frontendDeveloper)
const getBugBackendDeveloper = row => getMappedField(row, 'backend_developer') || getSemanticRawField(row, BUG_FIXED_FIELD_ALIASES.backend_developer, 'bug') || getRawField(row, bugRawFieldMap.backendDeveloper)
const getBugFeedback = row => getRawField(row, bugRawFieldMap.bugFeedback)
const getBugReopenCount = row => getRawField(row, bugRawFieldMap.reopenCount)
const getBugFieldValue = (row, fieldKey) => {
  const normalizedKey = normalizeText(fieldKey)
  if (!normalizedKey) {
    return ''
  }
  const rawValue = getRawField(row, normalizedKey)
  if (rawValue) {
    return rawValue
  }
  if (normalizedKey === 'issuekey') {
    return normalizeText(row?.issue_key)
  }
  if (normalizedKey === 'summary') {
    return normalizeText(row?.summary)
  }
  return ''
}
const getRequirementModule = row => normalizeText(row?.module) || '无模块'
const getRelationCount = (row, countField, listField) => {
  const count = Number(row?.[countField])
  if (Number.isFinite(count)) {
    return count
  }
  const listValue = row?.[listField]
  return Array.isArray(listValue) ? listValue.length : 0
}
const hasRequirementMindmap = row => getRelationCount(row, 'related_mindmap_count', 'related_mindmaps') > 0
const hasRequirementVersionDefect = row => getRelationCount(row, 'version_defect_count', 'version_defects') > 0
const hasRequirementBugRecord = row => getRelationCount(row, 'bug_record_count', 'bug_records') > 0
const getRequirementFieldValue = (row, fieldKey) => {
  const normalizedKey = normalizeText(fieldKey)
  if (!normalizedKey) {
    return ''
  }
  const rawValue = getRawField(row, normalizedKey)
  if (rawValue) {
    return rawValue
  }
  if (normalizedKey === 'issuekey') {
    return normalizeText(row?.issue_key)
  }
  if (normalizedKey === 'summary') {
    return normalizeText(row?.summary)
  }
  return ''
}
const getRequirementTester = row =>
  getMappedField(row, 'tester') || normalizeText(row?.tester) || getRawField(row, 'customfield_10222')
const getRequirementGroupName = row => getMappedField(row, 'group_name') || normalizeText(row?.group_name) || getRawField(row, 'customfield_11000')

const buildVersionOptions = dataset => {
  const summaryMap = new Map()

  dataset.versionSummaries.forEach(item => {
    summaryMap.set(item.version, { ...item })
  })

  dataset.configs.forEach(item => {
    if (!summaryMap.has(item.version)) {
      summaryMap.set(item.version, {
        version: item.version,
        record_count: item.record_count || 0,
        latest_synced_at: item.last_executed_at || '',
      })
    }
  })

  return Array.from(summaryMap.values()).sort((left, right) => {
    const rightTime = right.latest_synced_at ? new Date(right.latest_synced_at).getTime() : 0
    const leftTime = left.latest_synced_at ? new Date(left.latest_synced_at).getTime() : 0
    if (rightTime !== leftTime) {
      return rightTime - leftTime
    }
    return String(right.version).localeCompare(String(left.version), 'zh-CN')
  })
}

const buildValueFilters = (records, resolver, limit = 20) => {
  const values = []
  const seen = new Set()

  records.forEach(row => {
    const normalized = normalizeText(resolver(row))
    if (!normalized || seen.has(normalized)) {
      return
    }
    seen.add(normalized)
    values.push(normalized)
  })

  return values
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
    .slice(0, limit)
    .map(item => ({ text: item, value: item }))
}

const buildColumnFilters = (records, field, formatter = value => value, limit = 20) =>
  buildValueFilters(records, row => formatter(row?.[field], row), limit)

const buildBugColumnFilters = records => ({
  version: buildColumnFilters(records, 'version'),
  synced_at: buildColumnFilters(records, 'synced_at', value => formatDate(value)),
  ...Object.fromEntries(
    JIRA_BUG_VISIBLE_FIELD_DEFINITIONS.map(field => [
      field.key,
      buildValueFilters(
        records,
        row => getBugFieldValue(row, field.key),
        field.filterLimit || 20,
      ),
    ]),
  ),
})

const buildRequirementColumnFilters = records => ({
  version: buildColumnFilters(records, 'version'),
  synced_at: buildColumnFilters(records, 'synced_at', value => formatDate(value)),
  ...Object.fromEntries(
    JIRA_REQUIREMENT_VISIBLE_FIELD_DEFINITIONS.map(field => [
      field.key,
      buildValueFilters(
        records,
        row => getRequirementFieldValue(row, field.key),
        field.filterLimit || 20,
      ),
    ]),
  ),
})

const buildRawFieldLabelMap = (records, type) => {
  const labelMap = {}
  records.forEach(row => {
    Object.keys(getRawFields(row)).forEach(fieldKey => {
      const normalizedKey = normalizeText(fieldKey)
      if (!normalizedKey || isRawFieldMetadataKey(normalizedKey) || labelMap[normalizedKey]) {
        return
      }
      labelMap[normalizedKey] = getRawFieldLabelFromRow(row, fieldKey, type)
    })
  })
  return labelMap
}

const getConsumedRawFieldKeys = (records, type) => {
  return new Set(RAW_FIELD_EXCLUDED_KEYS[type] || [])
}

const buildExtraFieldOptions = (records, type) => {
  const seen = new Set()
  const excludedKeys = getConsumedRawFieldKeys(records, type)
  const labelMap = buildRawFieldLabelMap(records, type)

  records.forEach(row => {
    Object.entries(getRawFields(row)).forEach(([fieldKey, fieldValue]) => {
      const normalizedKey = normalizeText(fieldKey)
      const missingRequiredValue = type !== 'bug' && !normalizeText(fieldValue)
      if (
        !normalizedKey ||
        isRawFieldMetadataKey(normalizedKey) ||
        excludedKeys.has(normalizedKey) ||
        missingRequiredValue ||
        seen.has(normalizedKey)
      ) {
        return
      }
      seen.add(normalizedKey)
    })
  })

  return Array.from(seen)
    .sort((left, right) => {
      const labelCompare = compareText(labelMap[left] || formatRawFieldLabel(left, type), labelMap[right] || formatRawFieldLabel(right, type))
      if (labelCompare !== 0) {
        return labelCompare
      }
      return compareText(left, right)
    })
    .map(value => ({
      value,
      label: getExtraFieldOptionLabel(value, type, labelMap[value]),
    }))
}

const versionOptions = computed(() => ({
  bug: buildVersionOptions(datasets.bug),
  requirement: buildVersionOptions(datasets.requirement),
}))

const bugColumnFilters = computed(() => buildBugColumnFilters(datasets.bug.records))
const requirementColumnFilters = computed(() => buildRequirementColumnFilters(datasets.requirement.records))
const configColumnFilters = computed(() => ({
  interface_type: buildValueFilters(mergedConfigs.value, getConfigInterfaceType, 10),
  version: buildColumnFilters(mergedConfigs.value, 'version'),
  name: buildColumnFilters(mergedConfigs.value, 'name'),
  request_method: buildColumnFilters(mergedConfigs.value, 'request_method'),
  request_url: buildColumnFilters(mergedConfigs.value, 'request_url'),
  timeout_seconds: buildValueFilters(mergedConfigs.value, getConfigTimeoutSeconds),
  is_active: buildValueFilters(mergedConfigs.value, getConfigActiveLabel, 10),
  last_record_count: buildValueFilters(mergedConfigs.value, getConfigLastRecordCount),
  last_status_code: buildValueFilters(mergedConfigs.value, getConfigLastStatusCode),
  last_executed_at: buildValueFilters(mergedConfigs.value, getConfigLastExecutedAt),
  last_execution_message: buildColumnFilters(mergedConfigs.value, 'last_execution_message'),
}))
const bugRawFieldLabelMap = computed(() => buildRawFieldLabelMap(datasets.bug.records, 'bug'))
const requirementRawFieldLabelMap = computed(() => buildRawFieldLabelMap(datasets.requirement.records, 'requirement'))
const bugExtraFieldOptions = computed(() => buildExtraFieldOptions(datasets.bug.records, 'bug'))
const requirementExtraFieldOptions = computed(() => buildExtraFieldOptions(datasets.requirement.records, 'requirement'))

const parseIssueKey = value => {
  const normalized = normalizeText(value)
  const matched = normalized.match(/^(.*?)-(\d+)$/)
  if (!matched) {
    return { prefix: normalized, order: Number.MAX_SAFE_INTEGER }
  }

  return {
    prefix: matched[1],
    order: Number(matched[2]),
  }
}

const sortByTextField = field => (left, right) => compareText(left[field], right[field])
const sortByResolver = resolver => (left, right) => compareText(resolver(left), resolver(right))
const sortByRawField = field => sortByResolver(row => getRawField(row, field))
const sortByNumberField = field => (left, right) => Number(left?.[field] || 0) - Number(right?.[field] || 0)

const sortByDateField = field => (left, right) => {
  const leftTime = left[field] ? new Date(left[field]).getTime() : 0
  const rightTime = right[field] ? new Date(right[field]).getTime() : 0
  return leftTime - rightTime
}

const sortByIssueKey = (left, right) => {
  const leftIssue = parseIssueKey(left.issue_key)
  const rightIssue = parseIssueKey(right.issue_key)
  const prefixCompare = compareText(leftIssue.prefix, rightIssue.prefix)

  if (prefixCompare !== 0) {
    return prefixCompare
  }

  return leftIssue.order - rightIssue.order
}

const filterByField = field => (value, row) => normalizeText(row[field]) === normalizeText(value)
const filterByResolver = resolver => (value, row) => normalizeText(resolver(row)) === normalizeText(value)
const filterByRawField = field => filterByResolver(row => getRawField(row, field))
const filterByFormattedField = (field, formatter) => (value, row) =>
  normalizeText(formatter(row[field], row)) === normalizeText(value)
const getExtraFieldFilters = (type, field) => buildValueFilters(getDataset(type).records, row => getRawField(row, field), 30)

const getDataset = type => datasets[type]
const getMeta = type => DATASET_META[type]
const getTableRef = type => (type === 'bug' ? bugTableRef : requirementTableRef)
const getDatasetPagination = type => getDataset(type).pagination
const resetDatasetPagination = type => {
  getDatasetPagination(type).page = 1
}
const buildManualWorkspaceQuery = (overrides = {}, keysToClear = []) => {
  const query = {
    ...route.query,
    ...overrides,
  }

  keysToClear.forEach(key => {
    delete query[key]
  })

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

const jumpToRequirementTestpoints = row => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前记录缺少需求编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'testpoints',
        testpoint_requirement_key: issueKey,
      },
      ['keyword', 'jira_keyword', 'mindmap_keyword', 'mindmap_requirement_key', 'defect_keyword', 'bug_keyword']
    ),
  })
}

const jumpToRequirementDefects = row => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前记录缺少需求编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'version-defects',
        defect_keyword: issueKey,
      },
      ['mindmap_keyword', 'mindmap_requirement_key', 'jira_keyword', 'testpoint_keyword', 'bug_keyword', 'keyword']
    ),
  })
}

const jumpToRequirementBugRecords = row => {
  const issueKey = normalizeText(row?.issue_key)
  if (!issueKey) {
    ElMessage.warning('当前记录缺少需求编号')
    return
  }

  router.push({
    path: '/manual-testcases/list',
    query: buildManualWorkspaceQuery(
      {
        tab: 'bug-records',
        bug_keyword: issueKey,
      },
      ['keyword', 'jira_keyword', 'mindmap_keyword', 'mindmap_requirement_key', 'testpoint_keyword', 'defect_keyword']
    ),
  })
}
const DETAIL_FIELD_DEFINITIONS = {
  bug: JIRA_BUG_VISIBLE_FIELD_DEFINITIONS
    .filter(field => !['issuekey', 'summary'].includes(field.key))
    .map(field => ({
      key: field.key,
      label: field.label,
      resolver: row => getBugFieldValue(row, field.key),
    })),
  requirement: JIRA_REQUIREMENT_VISIBLE_FIELD_DEFINITIONS
    .filter(field => !['issuekey', 'summary'].includes(field.key))
    .map(field => ({
      key: field.key,
      label: field.label,
      resolver: row => getRequirementFieldValue(row, field.key),
    })),
}
const normalizeFieldKeys = keys => (Array.isArray(keys) ? keys : [keys]).map(normalizeText).filter(Boolean)
const buildDetailFields = (type, record) => {
  if (!record) {
    return []
  }

  const excludedRawKeys = getConsumedRawFieldKeys([record], type)
  const consumedRawKeys = new Set()
  const fields = []

  ;(DETAIL_FIELD_DEFINITIONS[type] || []).forEach(item => {
    const rawKeys = normalizeFieldKeys(item.rawKeys?.length ? item.rawKeys : item.key)
    rawKeys.forEach(key => consumedRawKeys.add(key))

    const value = normalizeText(item.resolver(record))
    if (!value) {
      return
    }

    fields.push({
      key: item.key,
      label: item.label,
      value,
    })
  })

  Object.keys(getRawFields(record))
    .map(normalizeText)
    .filter(Boolean)
    .filter(fieldKey => !isRawFieldMetadataKey(fieldKey))
    .sort((left, right) => compareText(getRawFieldLabelFromRow(record, left, type), getRawFieldLabelFromRow(record, right, type)) || compareText(left, right))
    .forEach(fieldKey => {
      if (excludedRawKeys.has(fieldKey) || consumedRawKeys.has(fieldKey)) {
        return
      }

      const value = getRawField(record, fieldKey)
      if (!value) {
        return
      }

      fields.push({
        key: fieldKey,
        label: getRawFieldLabelFromRow(record, fieldKey, type),
        value,
      })
    })

  return fields
}
const currentDetailFields = computed(() => buildDetailFields(detailState.datasetType, detailRecord.value))
const currentDetailColumns = computed(() => (currentDetailFields.value.length > 8 ? 3 : 2))
const currentAssociationSections = computed(() => {
  if (detailState.datasetType !== 'bug' || !detailRecord.value) {
    return []
  }

  const record = detailRecord.value
  return [
    {
      key: 'requirements',
      title: '关联需求',
      items: ensureUniqueRequirementAssociationItems(record.related_requirements).map(item => ({
        key: item.issue_key,
        label: formatRequirementAssociationLabel(item),
      })),
    },
    {
      key: 'testcases',
      title: '关联测试用例',
      items: ensureUniqueJiraManualRelationItems(record.related_testcases, 'case').map(item => ({
        key: item.relation_key,
        label: formatManualAssociationLabel(item, 'case'),
      })),
    },
    {
      key: 'testpoints',
      title: '关联测试点',
      items: ensureUniqueJiraManualRelationItems(record.related_testpoints, 'testpoint').map(item => ({
        key: item.relation_key,
        label: formatManualAssociationLabel(item, 'testpoint'),
      })),
    },
  ].filter(section => section.items.length)
})
const sanitizeExtraVisibleFields = type => {
  const dataset = getDataset(type)
  const optionList = type === 'bug' ? bugExtraFieldOptions.value : requirementExtraFieldOptions.value
  const nextAvailableFields = optionList.map(item => item.value)
  const availableFields = new Set(nextAvailableFields)
  const previousAvailableFields = new Set(dataset.knownExtraFields)
  const retainedVisibleFields = dataset.extraVisibleFields.filter(field => availableFields.has(field))
  const fieldsToAdd = dataset.hasInitializedExtraFields
    ? nextAvailableFields.filter(field => !previousAvailableFields.has(field))
    : nextAvailableFields

  dataset.extraVisibleFields = Array.from(new Set([...retainedVisibleFields, ...fieldsToAdd]))
  dataset.knownExtraFields = nextAvailableFields
  if (optionList.length) {
    dataset.hasInitializedExtraFields = true
  }
}

const isCancelError = error => error === 'cancel' || error === 'close'

const loadJiraBrowsePrefix = async () => {
  loadingJiraBrowsePrefix.value = true
  try {
    const response = await api.get(QUALITY_ANALYSIS_SETTINGS_ENDPOINT)
    jiraBrowsePrefix.value = normalizeJiraBrowsePrefix(response.data?.jira_browse_prefix)
  } catch (error) {
    jiraBrowsePrefix.value = DEFAULT_JIRA_BROWSE_BASE_URL
  } finally {
    loadingJiraBrowsePrefix.value = false
  }
}

const saveJiraBrowsePrefix = async () => {
  const normalized = normalizeJiraBrowsePrefix(jiraBrowsePrefix.value)
  savingJiraBrowsePrefix.value = true
  try {
    const response = await api.put(QUALITY_ANALYSIS_SETTINGS_ENDPOINT, {
      jira_browse_prefix: normalized,
    })
    jiraBrowsePrefix.value = normalizeJiraBrowsePrefix(response.data?.jira_browse_prefix)
  } finally {
    savingJiraBrowsePrefix.value = false
  }
  ElMessage.success('JIRA URL前缀已保存')
}

const resetConfigForm = () => {
  dialogState.editingId = null
  Object.assign(configForm, {
    interface_type: 'bug',
    version: '',
    name: '',
    request_url: '',
    request_method: 'POST',
    request_headers_text: '',
    request_body: '',
    timeout_seconds: 60,
    jira_login_enabled: true,
    jira_login_url: DEFAULT_JIRA_LOGIN_URL,
    jira_username: '',
    jira_password: '',
    has_jira_password: false,
    is_active: true,
    notes: '',
  })
}

const getAssociationManualVersionName = () => {
  const matchedVersion = associationManualVersionOptions.value.find(
    item => String(item.id) === String(associationForm.manualVersionId)
  )
  return normalizeText(matchedVersion?.name)
}

const resetAssociationForm = () => {
  associationState.record = null
  associationForm.requirementVersion = ''
  associationForm.manualVersionId = ''
  associationForm.relatedRequirements = []
  associationForm.relatedTestcases = []
  associationForm.relatedTestpoints = []
  associationRequirementOptions.value = []
  associationTestcaseOptions.value = []
  associationTestpointOptions.value = []
}

const loadAssociationRequirementVersions = async () => {
  associationLoadingRequirementVersions.value = true
  try {
    const response = await api.get(DATASET_META.requirement.versionEndpoint)
    associationRequirementVersionOptions.value = normalizeApiList(response.data)
  } finally {
    associationLoadingRequirementVersions.value = false
  }
}

const loadAssociationManualVersions = async () => {
  if (!linkedProjectId.value) {
    associationManualVersionOptions.value = []
    return
  }

  associationLoadingManualVersions.value = true
  try {
    const response = await api.get('/versions/', {
      params: {
        projects: linkedProjectId.value,
      },
    })
    associationManualVersionOptions.value = normalizeApiList(response.data)
  } finally {
    associationLoadingManualVersions.value = false
  }
}

const loadAssociationRequirementOptions = async keyword => {
  associationRequirementOptions.value = ensureUniqueRequirementAssociationItems(associationForm.relatedRequirements)

  const params = {}
  const normalizedVersion = normalizeText(associationForm.requirementVersion)
  const normalizedKeyword = normalizeText(keyword)

  if (normalizedVersion) {
    params.version = normalizedVersion
  }
  if (normalizedKeyword) {
    params.keyword = normalizedKeyword
  }
  if (!params.version && !params.keyword) {
    return
  }

  associationLoadingRequirements.value = true
  try {
    const response = await api.get(DATASET_META.requirement.recordEndpoint, { params })
    associationRequirementOptions.value = ensureUniqueRequirementAssociationItems([
      ...associationForm.relatedRequirements,
      ...normalizeApiList(response.data),
    ])
  } finally {
    associationLoadingRequirements.value = false
  }
}

const loadAssociationManualOptions = async (nodeType, keyword = '') => {
  const optionsRef = nodeType === 'case' ? associationTestcaseOptions : associationTestpointOptions
  const loadingRef = nodeType === 'case' ? associationLoadingTestcases : associationLoadingTestpoints
  const selectedItems = nodeType === 'case' ? associationForm.relatedTestcases : associationForm.relatedTestpoints

  optionsRef.value = ensureUniqueJiraManualRelationItems(selectedItems, nodeType)

  if (!linkedProjectId.value || !associationForm.manualVersionId) {
    return
  }

  loadingRef.value = true
  try {
    const params = {
      project: linkedProjectId.value,
      version: associationForm.manualVersionId,
      node_type: nodeType,
      page_size: 50,
    }

    const normalizedKeyword = normalizeText(keyword)
    if (normalizedKeyword) {
      params.search = normalizedKeyword
    }

    const response = await api.get('/testcases/manual-mindmap-nodes/', { params })
    optionsRef.value = ensureUniqueJiraManualRelationItems([
      ...selectedItems,
      ...normalizeApiList(response.data),
    ], nodeType)
  } finally {
    loadingRef.value = false
  }
}

const handleAssociationManualVersionChange = async () => {
  await Promise.all([
    loadAssociationManualOptions('case'),
    loadAssociationManualOptions('testpoint'),
  ])
}

const openAssociationDialog = async record => {
  resetAssociationForm()
  associationState.record = record
  associationDialogVisible.value = true

  await Promise.all([
    loadAssociationRequirementVersions(),
    loadAssociationManualVersions(),
  ])

  associationForm.relatedRequirements = ensureUniqueRequirementAssociationItems(record.related_requirements)
  associationForm.relatedTestcases = ensureUniqueJiraManualRelationItems(record.related_testcases, 'case')
  associationForm.relatedTestpoints = ensureUniqueJiraManualRelationItems(record.related_testpoints, 'testpoint')
  associationRequirementOptions.value = ensureUniqueRequirementAssociationItems(record.related_requirements)
  associationTestcaseOptions.value = ensureUniqueJiraManualRelationItems(record.related_testcases, 'case')
  associationTestpointOptions.value = ensureUniqueJiraManualRelationItems(record.related_testpoints, 'testpoint')

  const defaultVersion = normalizeText(record?.version || props.linkedVersion)
  if (defaultVersion) {
    associationForm.requirementVersion = defaultVersion
    const matchedManualVersion = associationManualVersionOptions.value.find(
      item => normalizeText(item?.name) === defaultVersion
    )
    associationForm.manualVersionId = matchedManualVersion?.id || ''
  }

  await Promise.all([
    loadAssociationRequirementOptions(''),
    loadAssociationManualOptions('case'),
    loadAssociationManualOptions('testpoint'),
  ])
}

const closeAssociationDialog = () => {
  associationDialogVisible.value = false
  associationSaving.value = false
  resetAssociationForm()
}

const updateBugRecordInState = updatedRecord => {
  datasets.bug.records = datasets.bug.records.map(item => (
    item.id === updatedRecord.id ? { ...item, ...updatedRecord } : item
  ))

  if (detailState.datasetType === 'bug' && detailState.record?.id === updatedRecord.id) {
    detailState.record = updatedRecord
  }
}

const saveBugAssociations = async () => {
  if (!associationState.record?.id) {
    return
  }

  associationSaving.value = true
  try {
    const response = await api.post(
      `${DATASET_META.bug.recordEndpoint}${associationState.record.id}/associations/`,
      {
        related_requirements: ensureUniqueRequirementAssociationItems(associationForm.relatedRequirements),
        related_testcases: serializeJiraManualRelationItems(associationForm.relatedTestcases, 'case'),
        related_testpoints: serializeJiraManualRelationItems(associationForm.relatedTestpoints, 'testpoint'),
      }
    )

    updateBugRecordInState(response.data)
    ElMessage.success('缺陷关联已保存')
    closeAssociationDialog()
  } finally {
    associationSaving.value = false
  }
}

const handleConfigTypeChange = type => {
  dialogState.datasetType = type || 'bug'
}

const clearTableSelection = async type => {
  const dataset = getDataset(type)
  dataset.selectedRows = []
  await nextTick()
  getTableRef(type).value?.clearSelection()
}

const syncSelectedVersion = type => {
  const dataset = getDataset(type)
  const availableVersions = versionOptions.value[type].map(item => item.version)

  if (!availableVersions.length) {
    dataset.filters.version = ''
    return
  }

  if (dataset.filters.version && availableVersions.includes(dataset.filters.version)) {
    return
  }

  dataset.filters.version = availableVersions[0]
}

const handleSelectionChange = (type, selection) => {
  getDataset(type).selectedRows = selection
}

const selectAllRecords = async type => {
  const table = getTableRef(type).value
  if (!table || !getDataset(type).records.length) {
    return
  }
  table.clearSelection()
  await nextTick()
  table.toggleAllSelection()
}

const loadVersionSummaries = async type => {
  const dataset = getDataset(type)
  const response = await api.get(getMeta(type).versionEndpoint)
  dataset.versionSummaries = response.data || []
}

const loadConfigs = async type => {
  const dataset = getDataset(type)
  dataset.loadingConfigs = true
  try {
    const params = {}
    const effectiveVersion = props.useLinkedVersion ? normalizedLinkedVersion.value : ''
    if (effectiveVersion) {
      params.version = effectiveVersion
    }

    const response = await api.get(getMeta(type).configEndpoint, { params })
    dataset.configs = response.data.results || response.data || []
  } finally {
    dataset.loadingConfigs = false
  }
}

const loadCombinedConfigs = async () => {
  loadingCombinedConfigs.value = true
  try {
    const params = {}
    const effectiveVersion = props.useLinkedVersion ? normalizedLinkedVersion.value : ''
    if (effectiveVersion) {
      params.version = effectiveVersion
    }

    const response = await api.get(COMBINED_CONFIG_ENDPOINT, { params })
    combinedConfigs.value = response.data.results || response.data || []
  } finally {
    loadingCombinedConfigs.value = false
  }
}

const refreshConfigList = async () => {
  await loadCombinedConfigs()
}

const buildRecordQueryParams = (type, options = {}) => {
  const dataset = getDataset(type)
  const pagination = getDatasetPagination(type)
  const params = {}
  params.page = pagination.page
  params.page_size = pagination.pageSize
  const effectiveVersion = props.useLinkedVersion ? normalizedLinkedVersion.value : normalizeText(dataset.filters.version)
  if (effectiveVersion) {
    params.version = effectiveVersion
  }
  if (dataset.filters.keyword.trim()) {
    params.keyword = dataset.filters.keyword.trim()
  }
  if (type === 'bug' && dataset.filters.testpointId.trim()) {
    params.testpoint_id = dataset.filters.testpointId.trim()
  }
  if (type === 'requirement' && props.embedded && route.query.project_id) {
    params.project_id = String(route.query.project_id)
  }
  if (type === 'requirement' && props.embedded && route.query.version_id && route.query.version_id !== 'all') {
    params.manual_version_id = String(route.query.version_id)
  }
  if (
    props.embedded &&
    normalizedLinkedModules.value.length &&
    (type === 'bug' || type === 'requirement') &&
    !options.skipModuleNames
  ) {
    params.module_names = JSON.stringify(normalizedLinkedModules.value)
  }
  return params
}

const buildOnlineDefectAnalysisOption = payload => {
  const categories = payload?.categories || []
  const series = (payload?.series || []).map(item => ({
    name: item.name,
    type: 'line',
    smooth: true,
    symbolSize: 7,
    data: item.data || [],
    label: {
      show: true,
      position: 'top',
      formatter: params => (Number(params.value || 0) > 0 ? params.value : ''),
    },
    emphasis: { focus: 'series' },
  }))

  return {
    color: ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'line' } },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { color: '#334155' },
    },
    grid: {
      top: 48,
      left: 54,
      right: 24,
      bottom: categories.length > 6 ? 88 : 48,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        color: '#475569',
        interval: 0,
        rotate: categories.length > 6 ? 32 : 0,
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#475569' },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series,
  }
}

const disposeOnlineDefectAnalysisChart = () => {
  if (onlineDefectAnalysisChart) {
    onlineDefectAnalysisChart.dispose()
    onlineDefectAnalysisChart = null
  }
}

const renderOnlineDefectAnalysis = async () => {
  await nextTick()

  if (!props.showOnlineDefectAnalysis || !onlineDefectAnalysisHasData.value || !onlineDefectAnalysisChartRef.value) {
    disposeOnlineDefectAnalysisChart()
    return
  }

  if (!onlineDefectAnalysisChart) {
    onlineDefectAnalysisChart = echarts.init(onlineDefectAnalysisChartRef.value)
  }
  onlineDefectAnalysisChart.setOption(buildOnlineDefectAnalysisOption(onlineDefectAnalysis.data), true)
  onlineDefectAnalysisChart.resize()
}

const loadOnlineDefectAnalysis = async () => {
  if (!props.showOnlineDefectAnalysis) {
    onlineDefectAnalysis.loading = false
    onlineDefectAnalysis.data = null
    disposeOnlineDefectAnalysisChart()
    return
  }

  if (!props.active || activeTab.value !== 'bug-records') {
    return
  }

  onlineDefectAnalysis.loading = true
  try {
    const params = {}
    if (currentBugAnalysisVersion.value) {
      params.version = currentBugAnalysisVersion.value
    }
    const response = await api.get('/quality-analysis/jira-bug-records/online-defect-analysis/', { params })
    onlineDefectAnalysis.data = response.data || null
    await renderOnlineDefectAnalysis()
  } catch (error) {
    onlineDefectAnalysis.data = null
    ElMessage.error('获取线上缺陷质量统计失败')
  } finally {
    onlineDefectAnalysis.loading = false
  }
}

const syncRecordsByConfig = async type => {
  const meta = getMeta(type)
  const params = {}
  const effectiveVersion = props.useLinkedVersion ? normalizedLinkedVersion.value : normalizeText(getDataset(type).filters.version)
  if (effectiveVersion) {
    params.version = effectiveVersion
  }

  const response = await api.post(`${meta.recordEndpoint}refresh/`, null, { params })
  ElMessage.success(response.data?.message || `${meta.label}同步完成`)
}

const loadRecords = async (type, options = {}) => {
  const { skipSync = false } = options
  const dataset = getDataset(type)
  dataset.loadingRecords = true

  try {
    if (!skipSync) {
      try {
        await syncRecordsByConfig(type)
        await Promise.all([loadConfigs(type), loadVersionSummaries(type), refreshConfigList()])
        if (!props.useLinkedVersion) {
          syncSelectedVersion(type)
        }
      } catch (error) {
        ElMessage.error(error?.response?.data?.detail || `${getMeta(type).label}同步失败`)
        return
      }
    }

    const requestParams = buildRecordQueryParams(type)
    const response = await api.get(getMeta(type).recordEndpoint, { params: requestParams })
    let responsePayload = response.data || {}
    let nextRecords = normalizeApiList(responsePayload)
    if (!nextRecords.length && requestParams.module_names) {
      const fallbackResponse = await api.get(getMeta(type).recordEndpoint, {
        params: buildRecordQueryParams(type, { skipModuleNames: true }),
      })
      responsePayload = fallbackResponse.data || {}
      nextRecords = normalizeApiList(responsePayload)
    }
    dataset.records = nextRecords
    dataset.pagination.total = getApiListTotal(responsePayload)
    sanitizeExtraVisibleFields(type)
    await clearTableSelection(type)
    if (type === 'bug') {
      await loadOnlineDefectAnalysis()
    }
  } catch (error) {
    dataset.records = []
    dataset.pagination.total = 0
    await clearTableSelection(type)
    ElMessage.error(`获取${getMeta(type).label}失败`)
  } finally {
    dataset.loadingRecords = false
  }
}

const handleRecordPageChange = async type => {
  await loadRecords(type, { skipSync: true })
}

const handleRecordPageSizeChange = async type => {
  resetDatasetPagination(type)
  await loadRecords(type, { skipSync: true })
}

const handleRecordFilterChange = async type => {
  resetDatasetPagination(type)
  await loadRecords(type, { skipSync: true })
}

const refreshRecords = async type => {
  resetDatasetPagination(type)
  await loadRecords(type)
}

const refreshDataset = async type => {
  await Promise.all([loadConfigs(type), loadVersionSummaries(type)])
  if (!props.useLinkedVersion) {
    syncSelectedVersion(type)
  }
  resetDatasetPagination(type)
  await loadRecords(type, { skipSync: true })
}

const refreshAllDatasets = async () => {
  await Promise.all([refreshDataset('bug'), refreshDataset('requirement'), refreshConfigList()])
}

const clearSelectedRecords = async type => {
  const dataset = getDataset(type)
  const meta = getMeta(type)
  const ids = dataset.selectedRows.map(item => item.id).filter(Boolean)

  if (!ids.length) {
    ElMessage.warning('请先选择需要清空的记录')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认清空当前所选 ${ids.length} 条${meta.label}数据吗？`,
      '清空确认',
      {
        type: 'warning',
      }
    )
    dataset.clearingRecords = true
    const response = await api.post(`${meta.recordEndpoint}clear-selected/`, { ids })
    ElMessage.success(response.data.message || '清空成功')
    await refreshDataset(type)
  } catch (error) {
    if (!isCancelError(error)) {
      throw error
    }
  } finally {
    dataset.clearingRecords = false
  }
}

const handleVersionChange = async type => {
  resetDatasetPagination(type)
  await loadRecords(type, { skipSync: true })
}

const resizeOnlineDefectAnalysis = () => {
  onlineDefectAnalysisChart?.resize()
}

const refreshCurrentEmbeddedTab = async () => {
  if (activeTab.value === 'bug-records') {
    await refreshDataset('bug')
    return
  }

  if (activeTab.value === 'requirement-records') {
    await refreshDataset('requirement')
    return
  }

  if (activeTab.value === 'configs') {
    await refreshConfigList()
    return
  }

  if (activeTab.value === 'other-settings') {
    await loadJiraBrowsePrefix()
  }
}

const openRecordDetail = (type, record) => {
  detailState.datasetType = type
  detailState.record = record
  detailVisible.value = true
}

const openCreateDialog = (type = 'bug') => {
  dialogState.datasetType = type
  resetConfigForm()
  configForm.interface_type = type
  configDialogVisible.value = true
}

const openEditDialog = (type, config) => {
  dialogState.datasetType = type
  dialogState.editingId = config.id
  Object.assign(configForm, {
    interface_type: type,
    version: config.version || '',
    name: config.name || '',
    request_url: config.request_url || '',
    request_method: config.request_method || 'POST',
    request_headers_text: JSON.stringify(config.request_headers || {}, null, 2),
    request_body: config.request_body || '',
    timeout_seconds: config.timeout_seconds || 60,
    jira_login_enabled: Boolean(config.jira_login_enabled),
    jira_login_url: config.jira_login_url || DEFAULT_JIRA_LOGIN_URL,
    jira_username: config.jira_username || '',
    jira_password: '',
    has_jira_password: Boolean(config.has_jira_password),
    is_active: config.is_active !== false,
    notes: config.notes || '',
  })
  configDialogVisible.value = true
}

const openCopyDialog = (type, config) => {
  dialogState.datasetType = type
  dialogState.editingId = null
  Object.assign(configForm, {
    interface_type: type,
    version: config.version || '',
    name: config.name || '',
    request_url: config.request_url || '',
    request_method: config.request_method || 'POST',
    request_headers_text: JSON.stringify(config.request_headers || {}, null, 2),
    request_body: config.request_body || '',
    timeout_seconds: config.timeout_seconds || 60,
    jira_login_enabled: Boolean(config.jira_login_enabled),
    jira_login_url: config.jira_login_url || DEFAULT_JIRA_LOGIN_URL,
    jira_username: config.jira_username || '',
    jira_password: '',
    has_jira_password: false,
    is_active: config.is_active !== false,
    notes: config.notes || '',
  })
  configDialogVisible.value = true
}

const buildConfigPayload = () => {
  const payload = {
    version: configForm.version.trim(),
    name: configForm.name.trim() || currentDialogMeta.value.defaultConfigName,
    request_method: configForm.request_method || 'POST',
    timeout_seconds: Number(configForm.timeout_seconds) || 60,
    jira_login_enabled: Boolean(configForm.jira_login_enabled),
    jira_login_url: configForm.jira_login_url.trim(),
    jira_username: configForm.jira_username.trim(),
    is_active: configForm.is_active,
    notes: configForm.notes.trim(),
  }

  if (configForm.jira_password) {
    payload.jira_password = configForm.jira_password
  }

  if (configForm.request_url.trim()) {
    payload.request_url = configForm.request_url.trim()
  }

  if (configForm.request_headers_text.trim()) {
    payload.request_headers = JSON.parse(configForm.request_headers_text)
  }

  if (configForm.request_body.trim()) {
    payload.request_body = configForm.request_body.trim()
  }

  return payload
}

const saveConfig = async () => {
  try {
    await configFormRef.value?.validate()
  } catch {
    return
  }

  savingConfig.value = true
  try {
    const payload = buildConfigPayload()
    const meta = currentDialogMeta.value

    if (isEditing.value) {
      await api.patch(`${meta.configEndpoint}${dialogState.editingId}/`, payload)
      ElMessage.success(`${meta.label}接口配置已更新`)
    } else {
      await api.post(meta.configEndpoint, payload)
      ElMessage.success(`${meta.label}接口配置已创建`)
    }

    configDialogVisible.value = false
    activeTab.value = 'configs'
    await Promise.all([
      loadConfigs(dialogState.datasetType),
      loadVersionSummaries(dialogState.datasetType),
      refreshConfigList(),
    ])
  } catch (error) {
    if (error instanceof SyntaxError) {
      ElMessage.error('请求头 JSON 格式不正确')
      return
    }
    throw error
  } finally {
    savingConfig.value = false
  }
}

const executeConfig = async (type, config) => {
  const dataset = getDataset(type)
  const meta = getMeta(type)

  try {
    await ElMessageBox.confirm(
      `确认执行版本 ${config.version} 的${meta.label}接口配置吗？执行前会先清空该版本的历史数据。`,
      '执行确认',
      {
        type: 'warning',
      }
    )
    dataset.executingId = config.id
    const response = await api.post(`${meta.configEndpoint}${config.id}/execute/`)
    ElMessage.success(response.data.message || '接口执行完成')
    if (props.embedded) {
      await refreshConfigList()
    } else {
      activeTab.value = `${type}-records`
      dataset.filters.version = config.version
      resetDatasetPagination(type)
      await refreshDataset(type)
    }
  } catch (error) {
    if (!isCancelError(error)) {
      throw error
    }
  } finally {
    dataset.executingId = null
  }
}

const deleteConfig = async (type, config) => {
  const meta = getMeta(type)

  try {
    await ElMessageBox.confirm(`确认删除版本 ${config.version} 的${meta.label}接口配置吗？`, '删除确认', {
      type: 'warning',
    })
    await api.delete(`${meta.configEndpoint}${config.id}/`)
    ElMessage.success(`${meta.label}接口配置已删除`)
    await Promise.all([loadConfigs(type), loadVersionSummaries(type), refreshConfigList()])
  } catch (error) {
    if (!isCancelError(error)) {
      throw error
    }
  }
}

onMounted(async () => {
  window.addEventListener('resize', resizeOnlineDefectAnalysis)
  await loadJiraBrowsePrefix()
  syncLinkedRecordKeywords()
  if (props.embedded) {
    if (activeTab.value === 'bug-records') {
      await refreshDataset('bug')
      return
    }

    if (activeTab.value === 'requirement-records') {
      await refreshDataset('requirement')
      return
    }

    if (activeTab.value === 'configs') {
      await refreshConfigList()
      return
    }

    if (activeTab.value === 'other-settings') {
      return
    }

    return
  }

  await refreshAllDatasets()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeOnlineDefectAnalysis)
  disposeOnlineDefectAnalysisChart()
})

watch(
  () => props.linkedVersion,
  async (nextVersion, previousVersion) => {
    if (!props.useLinkedVersion || !props.active || normalizeText(nextVersion) === normalizeText(previousVersion)) {
      return
    }
    await refreshCurrentEmbeddedTab()
  }
)

watch(
  () => props.linkedKeyword,
  async (nextKeyword, previousKeyword) => {
    if (!props.embedded || normalizeText(nextKeyword) === normalizeText(previousKeyword)) {
      return
    }

    syncLinkedRecordKeywords()
    if (props.active && activeTab.value === 'requirement-records') {
      resetDatasetPagination('requirement')
      await loadRecords('requirement', { skipSync: true })
    }
  }
)

watch(
  () => props.linkedBugKeyword,
  async (nextKeyword, previousKeyword) => {
    if (!props.embedded || normalizeText(nextKeyword) === normalizeText(previousKeyword)) {
      return
    }

    syncLinkedRecordKeywords()
    if (props.active && activeTab.value === 'bug-records') {
      resetDatasetPagination('bug')
      await loadRecords('bug', { skipSync: true })
    }
  }
)

watch(
  () => props.linkedBugTestpointId,
  async (nextTestpointId, previousTestpointId) => {
    if (!props.embedded || normalizeText(nextTestpointId) === normalizeText(previousTestpointId)) {
      return
    }

    syncLinkedRecordKeywords()
    if (props.active && activeTab.value === 'bug-records') {
      resetDatasetPagination('bug')
      await loadRecords('bug', { skipSync: true })
    }
  }
)

watch(
  () => normalizedLinkedModules.value.join('||'),
  async (nextModules, previousModules) => {
    if (!props.embedded || nextModules === previousModules) {
      return
    }

    if (props.active && activeTab.value === 'requirement-records') {
      resetDatasetPagination('requirement')
      await loadRecords('requirement', { skipSync: true })
      return
    }

    if (props.active && activeTab.value === 'bug-records') {
      resetDatasetPagination('bug')
      await loadRecords('bug', { skipSync: true })
    }
  }
)

watch(
  () => props.active,
  async active => {
    if (!active) {
      return
    }
    syncLinkedRecordKeywords()
    await refreshCurrentEmbeddedTab()
  }
)

watch(onlineDefectAnalysisHasData, async () => {
  if (props.showOnlineDefectAnalysis && props.active && activeTab.value === 'bug-records') {
    await renderOnlineDefectAnalysis()
  }
})

watch(
  () => props.showOnlineDefectAnalysis,
  async showOnlineDefectAnalysis => {
    if (!showOnlineDefectAnalysis) {
      onlineDefectAnalysis.loading = false
      onlineDefectAnalysis.data = null
      disposeOnlineDefectAnalysisChart()
      return
    }

    if (props.active && activeTab.value === 'bug-records') {
      await loadOnlineDefectAnalysis()
    }
  }
)
</script>

<style scoped lang="scss">
.jira-data-page {
  min-height: 100vh;
  padding: 0;
  background:
    radial-gradient(circle at top right, rgba(14, 116, 144, 0.14), transparent 24%),
    linear-gradient(180deg, #f5f9fc 0%, #edf3f8 100%);
}

.jira-data-page--embedded {
  flex: 1 1 0;
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.content-card,
.table-panel,
.raw-panel,
.config-section,
.online-analysis-panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 24px;
  box-shadow: 0 18px 38px rgba(15, 45, 68, 0.08);
}

.content-card {
  min-height: 100vh;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.content-card--embedded {
  flex: 1 1 0;
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.jira-tabs {
  min-height: 100vh;
}

.jira-tabs--embedded {
  flex: 1 1 0;
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.jira-tabs :deep(.el-tabs__header) {
  margin: 0 0 14px;
  padding: 0 18px 0 16px;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid rgba(15, 55, 82, 0.08);
}

.jira-tabs :deep(.el-tabs__content) {
  min-height: calc(100vh - 56px);
  padding: 0;
  background: rgba(255, 255, 255, 0.92);
}

.jira-tabs :deep(.el-tab-pane) {
  min-height: calc(100vh - 56px);
}

.jira-tabs--embedded :deep(.el-tabs__header) {
  display: none;
}

.jira-tabs--embedded :deep(.el-tabs__content) {
  flex: 1 1 0;
  height: 100%;
  min-height: 100%;
  background: transparent;
}

.jira-tabs--embedded :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.toolbar,
.config-section-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.toolbar {
  position: sticky;
  top: 0;
  z-index: 15;
  padding-bottom: 18px;
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.92);
}

.config-section {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.config-section + .config-section {
  margin-top: 24px;
}

.config-section-header {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.config-section-header h3 {
  margin: 0 0 6px;
  color: #17324d;
  font-size: 20px;
}

.config-section-header p {
  margin: 0;
  color: #5b7188;
  font-size: 13px;
}

.toolbar-left,
.toolbar-right,
.action-group,
.form-grid {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.config-action-group {
  flex-wrap: nowrap;
  gap: 8px;
  white-space: nowrap;
}

.config-action-group :deep(.el-button) {
  flex: 0 0 auto;
}

.record-operation-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0 8px;
}

.record-operation-actions__item {
  display: inline-flex;
  vertical-align: middle;
}

.form-grid {
  align-items: flex-start;
}

.form-grid :deep(.el-form-item) {
  flex: 1;
}

.auth-section {
  margin: 4px 0 18px;
  padding: 14px 16px 2px;
  border: 1px solid #e5edf5;
  border-radius: 8px;
  background: #f8fbff;
}

.auth-section__header {
  margin-bottom: 12px;
}

.auth-section__header h3 {
  margin: 0 0 4px;
  color: #17324d;
  font-size: 15px;
  font-weight: 600;
}

.auth-section__header p {
  margin: 0;
  color: #5b7188;
  font-size: 12px;
}

.selection-hint {
  color: #5b7188;
  font-size: 13px;
}

.online-analysis-panel {
  flex: 0 0 auto;
  margin-bottom: 18px;
  padding: 16px 18px;
  border-radius: 8px;
  box-shadow: none;
}

.online-analysis-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.online-analysis-panel__header h3 {
  margin: 0 0 4px;
  color: #17324d;
  font-size: 16px;
  font-weight: 600;
}

.online-analysis-panel__header span {
  color: #5b7188;
  font-size: 13px;
}

.online-analysis-chart {
  width: 100%;
  height: 360px;
}

.other-config-form {
  max-width: 720px;
}

.association-dialog {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.association-section,
.association-summary__section {
  padding: 18px 20px;
  border: 1px solid rgba(15, 55, 82, 0.08);
  border-radius: 18px;
  background: rgba(248, 251, 254, 0.92);
}

.association-section__header h3,
.association-summary__section h3 {
  margin: 0 0 6px;
  color: #17324d;
  font-size: 16px;
}

.association-section__header p {
  margin: 0 0 14px;
  color: #5b7188;
  font-size: 13px;
}

.association-toolbar {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.association-select {
  flex: 1;
}

.association-tip {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(245, 158, 11, 0.12);
  color: #92400e;
  font-size: 13px;
}

.extra-field-select {
  width: 360px;
}

.extra-field-select :deep(.el-select__wrapper) {
  min-height: 32px;
}

.extra-field-select :deep(.el-select__selection) {
  flex-wrap: nowrap;
  overflow: hidden;
}

.extra-field-select :deep(.el-select__selected-item) {
  min-width: 0;
  white-space: nowrap;
}

.extra-field-select :deep(.el-select__tags-text) {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 8px;
  overflow: hidden;
}

.records-table,
.config-table {
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
}

.records-table :deep(.el-table__inner-wrapper),
.config-table :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.records-table :deep(.el-table__header-wrapper .cell),
.config-table :deep(.el-table__header-wrapper .cell) {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  white-space: nowrap;
  word-break: keep-all;
}

.tab-pagination {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.jira-link {
  color: #0f6dba;
  text-decoration: none;
  font-weight: 500;
}

.jira-link:hover {
  text-decoration: underline;
}

.detail-descriptions :deep(.el-descriptions__table) {
  table-layout: fixed;
}

.detail-descriptions :deep(.el-descriptions__label),
.detail-descriptions :deep(.el-descriptions__content) {
  white-space: normal;
  word-break: break-word;
  vertical-align: top;
}

.detail-empty {
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(15, 109, 186, 0.08);
  color: #3f5870;
  font-size: 14px;
}

.association-summary {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}

.association-summary__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.association-summary__item {
  color: #334155;
  line-height: 1.6;
  word-break: break-word;
}

.raw-panel {
  margin-top: 20px;
  padding: 20px;
}

.raw-panel h3 {
  margin: 0 0 12px;
  color: #17324d;
}

.raw-panel pre {
  margin: 0;
  padding: 16px;
  border-radius: 16px;
  background: #0f172a;
  color: #dbeafe;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .jira-tabs :deep(.el-tabs__header) {
    margin-bottom: 12px;
    padding: 0 12px;
  }

  .association-toolbar,
  .toolbar,
  .toolbar-left,
  .toolbar-right,
  .form-grid,
  .config-section-header {
    flex-direction: column;
    align-items: stretch;
  }

  .tab-pagination {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>

