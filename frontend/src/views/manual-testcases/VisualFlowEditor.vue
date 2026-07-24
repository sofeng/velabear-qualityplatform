<template>
  <div class="visual-flow-editor">
    <ManualWorkspaceRecordingShell
      v-model="researchContext"
      :items="workspaceSectionTabs"
      active-name="visual-flow"
      directory-title="流程录制页面目录"
      body-class="editor-workspace"
      :show-body-directory="false"
      @select="handleWorkspaceSectionSelect"
      @change="handleResearchContextChange"
    >
      <template #default="{ directoryProps, actions }">

    <!-- 脚本预览对话框 -->
    <el-dialog
      v-model="scriptDialogVisible"
      title="生成的Playwright脚本"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="script-preview">
        <div class="script-toolbar">
          <el-alert
            v-if="isGeneratedScriptStale"
            class="script-stale-alert"
            title="流程图已调整，当前脚本不是最新版本"
            type="warning"
            :closable="false"
            show-icon
          />
          <el-button size="small" @click="copyScript">
            <el-icon><DocumentCopy /></el-icon>
            复制脚本
          </el-button>
          <el-button size="small" type="primary" plain @click="() => generateScript()">
            重新生成脚本
          </el-button>
          <el-button size="small" @click="downloadScript">
            <el-icon><Download /></el-icon>
            下载脚本
          </el-button>
        </div>
        <el-scrollbar height="500px">
          <pre class="script-code">{{ generatedScript }}</pre>
        </el-scrollbar>
      </div>
      <template #footer>
        <el-button @click="scriptDialogVisible = false">关闭</el-button>
        <el-button :loading="backendExecuting" type="primary" @click="executeScript">后台回放</el-button>
        <el-button :loading="localExecuting" type="success" plain @click="executeLocalScript">本地回放</el-button>
      </template>
    </el-dialog>

    <!-- 组件配置对话框 -->
    <el-dialog
      v-model="componentConfigDialogVisible"
      :title="`配置${getComponentTypeName(currentComponentConfig.type)}`"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="currentComponentConfig" label-width="120px">
        <!-- 基本信息 -->
        <el-form-item label="组件类型">
          <el-tag>{{ getComponentTypeName(currentComponentConfig.type) }}</el-tag>
        </el-form-item>

        <!-- YML 元素选择器 -->
        <el-form-item label="映射元素" required>
          <el-select
            v-model="currentComponentConfig.elementId"
            placeholder="选择页面元素"
            filterable
          >
            <el-option
              v-for="element in availableElements"
              :key="element.id"
              :label="`${element.type}: ${element.text || '无文本'}`"
              :value="element.id"
            >
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="color: #999; min-width: 60px;">{{ element.type }}</span>
                <span>{{ element.text || '无文本' }}</span>
                <el-tag v-if="element.selectors && element.selectors.length > 0" size="small" type="info">
                  {{ element.selectors[0]?.value }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
          <el-alert
            title="选择此组件要映射的页面元素"
            type="info"
            :closable="false"
            style="margin-top: 8px"
          />
        </el-form-item>

        <!-- 操作类型配置，根据组件类型动态显示 -->
        <template v-if="currentComponentConfig.type === 'input'">
          <el-form-item label="测试数据">
            <el-input
              v-model="currentComponentConfig.value"
              placeholder="输入测试数据"
            />
          </el-form-item>
        </template>

        <template v-else-if="['button', 'tab', 'menuitem', 'clickable'].includes(currentComponentConfig.type)">
          <el-form-item label="点击方式">
            <el-radio-group v-model="currentComponentConfig.action">
              <el-radio value="click">单击</el-radio>
              <el-radio value="dblclick">双击</el-radio>
              <el-radio value="contextmenu">右键</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>

        <template v-else-if="currentComponentConfig.type === 'select'">
          <el-form-item label="选择值">
            <el-input
              v-model="currentComponentConfig.selectedValue"
              placeholder="输入要选择的选项值"
            />
          </el-form-item>
        </template>

        <template v-else-if="currentComponentConfig.type === 'checkbox'">
          <el-form-item label="选中状态">
            <el-switch v-model="currentComponentConfig.checked" />
          </el-form-item>
        </template>

        <template v-else-if="currentComponentConfig.type === 'radio'">
          <el-form-item label="选中状态">
            <el-switch v-model="currentComponentConfig.checked" />
          </el-form-item>
        </template>

        <template v-else-if="currentComponentConfig.type === 'link'">
          <el-form-item label="点击方式">
            <el-radio-group v-model="currentComponentConfig.action">
              <el-radio value="click">单击</el-radio>
              <el-radio value="contextmenu">右键</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>

        <template v-else-if="currentComponentConfig.type === 'file'">
          <el-form-item label="文件路径">
            <el-input
              v-model="currentComponentConfig.filePath"
              placeholder="输入执行机可访问的文件路径"
            />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="componentConfigDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmComponentConfig">确定</el-button>
      </template>
    </el-dialog>

      <div class="editor-container">
        <div
          class="editor-header"
          :class="{
            'editor-header--left-panel-open': activeLeftPanelVisible,
            'editor-header--detail-panel-open': activeDetailPanelVisible
          }"
        >
          <el-tag v-if="isLiveRecordingFlow && liveFlowActive" type="success">
            录制实时生成中
          </el-tag>
          <div class="header-actions">
            <el-button @click="router.push('/manual-testcases/flows')">流程管理</el-button>
            <el-button type="danger" plain :disabled="!canDeleteSelection" @click="deleteSelectedGraphItem">
              <el-icon><Delete /></el-icon>
              {{ selectedDeleteLabel }}
            </el-button>
            <el-button type="info" plain @click="optimizeFlowLayout">
              优化流程图排版
            </el-button>
            <el-button :loading="recordingStarting" :disabled="liveFlowActive" type="primary" plain @click="startVisualFlowRecording">
              开始录制
            </el-button>
            <el-button class="continue-recording-button" :loading="recordingContinuing" :disabled="liveFlowActive" type="warning" plain @click="continueVisualFlowRecording">
              继续录制
            </el-button>
            <el-button :loading="recordingStopping" :disabled="!isLiveRecordingFlow || !liveFlowActive" type="danger" plain @click="stopVisualFlowRecording">
              停止录制
            </el-button>
            <el-button @click="() => generateScript()">生成脚本</el-button>
            <el-button :loading="flowLoading" @click="saveFlow">保存</el-button>
            <el-button :loading="backendExecuting" @click="executeFlow" type="primary">后台回放</el-button>
            <el-button :loading="localExecuting" type="success" plain @click="executeLocalScript">本地回放</el-button>
          </div>
        </div>
        <!-- 左侧固定栏 -->
        <aside class="flow-left-sidebar">
        <div class="flow-left-tabs">
          <button
            v-for="item in flowLeftMenuItems"
            :key="item.key"
            class="flow-left-tab"
            :class="{ active: activeLeftPanel === item.key }"
            type="button"
            @click="toggleLeftPanel(item.key)"
          >
            <span>{{ item.label }}</span>
          </button>
        </div>

        <div class="flow-left-panel" v-show="activeLeftPanelVisible">
          <div class="flow-left-panel-header">
            <h3>{{ activeLeftPanelTitle }}</h3>
            <el-button text @click="collapseLeftPanel">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <div v-show="activeLeftPanel === 'directory'" class="flow-left-panel-content flow-left-directory">
            <ManualWorkspaceDirectoryPanel
              v-bind="directoryProps"
              :collapsed="false"
              title="流程录制页面目录"
              @update:filter-text="actions.updateTreeFilterText"
              @toggle="collapseLeftPanel"
              @node-click="actions.selectCategory"
              @node-contextmenu="actions.nodeContextmenu"
              @add-category="actions.addCategory"
              @edit-category="actions.editCategory"
              @delete-category="actions.deleteCategory"
            />
          </div>

          <div v-show="activeLeftPanel === 'library'" class="toolbar flow-left-panel-content">
        <div class="toolbar-title">节点库</div>
        <div class="node-palette">
          <div class="palette-item" @mousedown="(e) => startDrag(e, 'start')">
            <el-icon><VideoPlay /></el-icon>
            <span>开始</span>
          </div>
          <div class="palette-item" @mousedown="(e) => startDrag(e, 'page')">
            <el-icon><Document /></el-icon>
            <span>页面</span>
          </div>
          <div class="palette-item" @mousedown="(e) => startDrag(e, 'operation')">
            <el-icon><Setting /></el-icon>
            <span>操作</span>
          </div>
          <div class="palette-item" @mousedown="(e) => startDrag(e, 'end')">
            <el-icon><CircleClose /></el-icon>
            <span>结束</span>
          </div>
        </div>

        <!-- 组件库 -->
        <div class="toolbar-title" style="margin-top: 20px;">组件库</div>
        <div class="component-palette">
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'input')">
            <el-icon><Edit /></el-icon>
            <span>输入框</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'button')">
            <el-icon><VideoPlay /></el-icon>
            <span>按钮</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'select')">
            <el-icon><ArrowDown /></el-icon>
            <span>下拉框</span>
          </div>
        <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'checkbox')">
          <el-icon><Check /></el-icon>
          <span>复选框</span>
        </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'radio')">
            <el-icon><Check /></el-icon>
            <span>单选框</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'link')">
            <el-icon><Link /></el-icon>
            <span>链接</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'tab')">
            <el-icon><Document /></el-icon>
            <span>标签页</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'menuitem')">
            <el-icon><Setting /></el-icon>
            <span>菜单项</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'clickable')">
            <el-icon><Link /></el-icon>
            <span>可点击元素</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'file')">
            <el-icon><Document /></el-icon>
            <span>文件上传</span>
          </div>
          <div class="palette-component" @mousedown="(e) => startComponentDrag(e, 'iframe')">
            <el-icon><Document /></el-icon>
            <span>Iframe 容器</span>
          </div>
        </div>
      </div>
        </div>
      </aside>

      <!-- 中间画布 -->
      <div class="canvas-wrapper">
        <div ref="containerRef" class="graph-container"></div>
      </div>

      <!-- 右侧详情栏 -->
      <aside class="flow-detail-sidebar">
        <div class="flow-detail-tabs">
          <button
            v-for="item in flowDetailMenuItems"
            :key="item.key"
            class="flow-detail-tab"
            :class="{ active: activeDetailMenu === item.key }"
            :disabled="item.disabled"
            type="button"
            @click="setActiveDetailMenu(item.key)"
          >
            <span>{{ item.label }}</span>
          </button>
        </div>

      <div class="config-panel flow-detail-panel" v-show="activeDetailPanelVisible">
        <div class="panel-header">
          <h3>{{ activeDetailMenuTitle }}</h3>
          <el-button text @click="clearSelection">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <el-scrollbar class="panel-content">
          <template v-if="activeDetailMenu === 'node'">
          <template v-if="selectedNode && selectedNode.type !== 'component'">
          <!-- 开始节点配置 -->
          <el-form v-if="selectedNode.type === 'start'" label-width="120px">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.config.name" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="浏览器类型">
              <el-select v-model="selectedNode.config.browserType" @change="updateNodeConfig">
                <el-option label="Chromium" value="chromium" />
                <el-option label="Firefox" value="firefox" />
                <el-option label="WebKit" value="webkit" />
              </el-select>
            </el-form-item>
            <el-form-item label="启动URL">
              <el-input v-model="selectedNode.config.url" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="登录态策略">
              <el-select v-model="selectedNode.config.authStateStrategy" @change="updateNodeConfig">
                <el-option label="自动判断" value="auto" />
                <el-option label="清洁会话" value="clean" />
                <el-option label="注入平台登录态" value="inject" />
              </el-select>
              <div class="form-help-text">
                自动模式下，流程包含掩码密码时注入当前平台登录态并跳过已登录步骤，否则按流程配置执行。
              </div>
            </el-form-item>
            <el-form-item label="无头模式">
              <el-switch v-model="selectedNode.config.headless" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="浏览器最大化">
              <el-switch v-model="selectedNode.config.maximize" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="视窗宽度">
              <el-input-number v-model="selectedNode.config.viewportWidth" @change="updateNodeConfig" :min="800" :max="3840" />
            </el-form-item>
            <el-form-item label="视窗高度">
              <el-input-number v-model="selectedNode.config.viewportHeight" @change="updateNodeConfig" :min="600" :max="2160" />
            </el-form-item>
          </el-form>

          <div v-if="['start', 'page', 'operation'].includes(selectedNode.type)" class="node-io-panel">
            <el-divider content-position="left">变量输入输出</el-divider>
            <el-form label-width="120px">
              <el-form-item :label="selectedNode.type === 'start' ? '启动参数' : '输入模式'">
                <el-radio-group v-model="selectedNode.config.inputMode" @change="updateNodeConfig">
                  <el-radio
                    v-for="mode in inputModes"
                    :key="mode.value"
                    :value="mode.value"
                  >
                    {{ mode.label }}
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selectedNode.config.inputMode === 'literal'" :label="selectedNode.type === 'start' ? '动态URL' : '输入值'">
                <el-input
                  v-model="selectedNode.config.inputValue"
                  :placeholder="selectedNode.type === 'start' ? '留空则使用上方 URL' : '节点输入值，可供后续脚本使用'"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item v-else label="引用变量">
                <el-select
                  v-model="selectedNode.config.inputReference"
                  :placeholder="selectedNodeReferenceOptions.length ? '选择已有变量或直接输入' : (selectedNode.type === 'start' ? '例如 env_url' : '例如 current_case_id')"
                  filterable
                  clearable
                  allow-create
                  default-first-option
                  @change="updateNodeConfig"
                >
                  <el-option
                    v-for="option in selectedNodeReferenceOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  >
                    <div class="reference-option">
                      <span class="reference-option-name">{{ option.value }}</span>
                      <span class="reference-option-source">{{ option.sourceName }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div v-if="selectedNodeReferenceOptions.length" class="reference-option-hint">
                  可引用 {{ selectedNodeReferenceOptions.length }} 个前序变量
                </div>
              </el-form-item>
              <el-form-item label="输入别名">
                <el-input
                  v-model="selectedNode.config.inputAlias"
                  :placeholder="selectedNode.type === 'page' ? '页面内组件可引用该变量' : '例如 node_input'"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input
                  v-model="selectedNode.config.outputName"
                  placeholder="例如 current_result"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item label="输出来源">
                <el-select v-model="selectedNode.config.outputSource" @change="updateNodeConfig">
                  <el-option
                    v-for="option in variableSources"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="selectedNode.config.outputSource === 'custom'" label="输出表达式">
                <el-input
                  v-model="selectedNode.config.outputValue"
                  placeholder="例如 page.url"
                  @change="updateNodeConfig"
                />
              </el-form-item>
            </el-form>
          </div>

          <el-form v-if="false" label-width="120px">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.config.name" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="浏览器类型">
              <el-select v-model="selectedNode.config.browserType" @change="updateNodeConfig">
                <el-option label="Chromium" value="chromium" />
                <el-option label="Firefox" value="firefox" />
                <el-option label="WebKit" value="webkit" />
              </el-select>
            </el-form-item>
            <el-form-item label="启动URL">
              <el-input v-model="selectedNode.config.url" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="无头模式">
              <el-switch v-model="selectedNode.config.headless" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="浏览器最大化">
              <el-switch v-model="selectedNode.config.maximize" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="视窗宽度">
              <el-input-number v-model="selectedNode.config.viewportWidth" @change="updateNodeConfig" :min="800" :max="3840" />
            </el-form-item>
            <el-form-item label="视窗高度">
              <el-input-number v-model="selectedNode.config.viewportHeight" @change="updateNodeConfig" :min="600" :max="2160" />
            </el-form-item>
            <el-divider content-position="left">变量输入输出</el-divider>
            <el-form-item label="启动参数">
              <el-radio-group v-model="selectedNode.config.inputMode" @change="updateNodeConfig">
                <el-radio
                  v-for="mode in inputModes"
                  :key="mode.value"
                  :value="mode.value"
                >
                  {{ mode.label }}
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.inputMode === 'literal'" label="动态URL">
              <el-input
                v-model="selectedNode.config.inputValue"
                placeholder="留空则使用上方 URL"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-divider content-position="left">变量输入输出</el-divider>
            <el-form-item label="输入模式">
              <el-radio-group v-model="selectedNode.config.inputMode" @change="updateNodeConfig">
                <el-radio
                  v-for="mode in inputModes"
                  :key="mode.value"
                  :value="mode.value"
                >
                  {{ mode.label }}
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.inputMode === 'literal'" label="输入值">
              <el-input
                v-model="selectedNode.config.inputValue"
                placeholder="可作为操作参数"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item v-else label="引用变量">
              <el-input
                v-model="selectedNode.config.inputReference"
                placeholder="例如 wait_selector"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输入别名">
              <el-input
                v-model="selectedNode.config.inputAlias"
                placeholder="例如 node_input"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出变量">
              <el-input
                v-model="selectedNode.config.outputName"
                placeholder="例如 wait_result"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出来源">
              <el-select v-model="selectedNode.config.outputSource" @change="updateNodeConfig">
                <el-option
                  v-for="option in variableSources"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.outputSource === 'custom'" label="输出表达式">
              <el-input
                v-model="selectedNode.config.outputValue"
                placeholder="例如 'done'"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-divider content-position="left">节点变量</el-divider>
            <el-form-item label="输入模式">
              <el-radio-group v-model="selectedNode.config.inputMode" @change="updateNodeConfig">
                <el-radio
                  v-for="mode in inputModes"
                  :key="mode.value"
                  :value="mode.value"
                >
                  {{ mode.label }}
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.inputMode === 'literal'" label="输入值">
              <el-input
                v-model="selectedNode.config.inputValue"
                placeholder="用于当前页面内组件引用"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item v-else label="引用变量">
              <el-input
                v-model="selectedNode.config.inputReference"
                placeholder="例如 current_case_id"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输入别名">
              <el-input
                v-model="selectedNode.config.inputAlias"
                placeholder="页面内组件可引用这个变量名"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出变量">
              <el-input
                v-model="selectedNode.config.outputName"
                placeholder="例如 page_result"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出来源">
              <el-select v-model="selectedNode.config.outputSource" @change="updateNodeConfig">
                <el-option
                  v-for="option in variableSources"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.outputSource === 'custom'" label="输出表达式">
              <el-input
                v-model="selectedNode.config.outputValue"
                placeholder="例如 flow_vars.get('token', '')"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item v-else label="引用变量">
              <el-input
                v-model="selectedNode.config.inputReference"
                placeholder="例如 env_url"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输入别名">
              <el-input
                v-model="selectedNode.config.inputAlias"
                placeholder="例如 start_url"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出变量">
              <el-input
                v-model="selectedNode.config.outputName"
                placeholder="例如 current_url"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出来源">
              <el-select v-model="selectedNode.config.outputSource" @change="updateNodeConfig">
                <el-option
                  v-for="option in variableSources"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.outputSource === 'custom'" label="输出表达式">
              <el-input
                v-model="selectedNode.config.outputValue"
                placeholder="例如 page.url"
                @change="updateNodeConfig"
              />
            </el-form-item>
          </el-form>

          <!-- 页面节点配置 -->
          <el-form v-else-if="selectedNode.type === 'page'" label-width="120px">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.config.name" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="页面名称">
              <el-select
                v-model="selectedNode.config.pageName"
                filterable
                placeholder="请选择页面名称"
                no-data-text="暂无已配置页面名称"
                no-match-text="未找到匹配页面名称"
                @change="handlePageNameChange"
              >
                <el-option
                  v-for="option in pageNameOptions"
                  :key="option.filename"
                  :label="option.page_name"
                  :value="option.page_name"
                >
                  <div class="snapshot-page-option">
                    <span class="snapshot-page-option-name">{{ option.page_name }}</span>
                    <span class="snapshot-page-option-file">{{ option.filename }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="关联快照">
              <el-input :model-value="selectedNode.config.snapshotFile || '未关联快照'" disabled />
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="selectedNode.config.description"
                type="textarea"
                :rows="3"
                @change="updateNodeConfig"
              />
            </el-form-item>

            <!-- 执行路径显示 -->
            <el-divider content-position="left">组件映射</el-divider>
            <el-alert
              :title="`已解析 ${selectedNode.config.snapshotData?.interactiveElements?.length || 0} 个可交互元素，已映射 ${selectedNode.config.innerComponents?.length || 0} 个页面组件`"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            />

            <div class="mapped-components-panel">
              <div v-if="selectedNode.config.innerComponents?.length" class="mapped-components-list">
                <div
                  v-for="(component, index) in selectedNode.config.innerComponents"
                  :key="component.id"
                  class="mapped-component-card"
                  :class="{
                    active: activeInnerComponent?.id === component.id,
                    invalid: !component.elementData
                  }"
                  @click="setActiveInnerComponent(component.id)"
                >
                  <div class="mapped-component-card-header">
                    <el-tag :type="getComponentTagType(component.type)">
                      {{ getComponentTypeName(component.type) }}
                    </el-tag>
                    <div class="mapped-component-card-actions">
                      <el-button link size="small" :disabled="index === 0" @click.stop="moveInnerComponent(component.id, -1)">上移</el-button>
                      <el-button link size="small" :disabled="index === selectedNode.config.innerComponents.length - 1" @click.stop="moveInnerComponent(component.id, 1)">下移</el-button>
                      <el-button link size="small" type="danger" @click.stop="removeInnerComponent(component.id)">删除</el-button>
                    </div>
                  </div>
                  <div class="mapped-component-card-title">{{ getComponentDisplayText(component) }}</div>
                  <div class="mapped-component-card-meta">
                    <span>{{ component.elementData?.type || '未映射元素' }}</span>
                    <span>{{ getComponentSelectorPreview(component) || '未生成选择器' }}</span>
                  </div>
                </div>
              </div>
              <el-empty
                v-else
                description="从左侧组件库拖拽组件到当前页面节点"
                :image-size="72"
              />
            </div>

            <div v-if="false && activeInnerComponent" class="mapped-component-editor">
              <el-divider content-position="left">当前组件配置</el-divider>
              <el-form-item label="组件类型">
                <el-tag :type="getComponentTagType(activeInnerComponent.type)">
                  {{ getComponentTypeName(activeInnerComponent.type) }}
                </el-tag>
              </el-form-item>
              <el-form-item label="映射元素" required>
                <el-select
                  :model-value="activeInnerComponent.elementId"
                  placeholder="请选择 YML 元素"
                  filterable
                  @change="handleActiveComponentElementChange"
                >
                  <el-option
                    v-for="element in getEditableElementsForComponent(activeInnerComponent)"
                    :key="element.id"
                    :label="`${element.type}: ${element.text || element.ref || element.id}`"
                    :value="element.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="选择器">
                <el-input :model-value="getComponentSelectorPreview(activeInnerComponent)" disabled />
              </el-form-item>
              <el-form-item label="输入模式">
                <el-radio-group v-model="activeInnerComponent.config.inputMode" @change="updateActiveInnerComponent">
                  <el-radio
                    v-for="mode in inputModes"
                    :key="mode.value"
                    :value="mode.value"
                  >
                    {{ mode.label }}
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="activeInnerComponent.config.inputMode === 'reference'" label="引用变量">
                <el-select
                  v-model="activeInnerComponent.config.inputReference"
                  :placeholder="activeInnerComponentReferenceOptions.length ? '选择已有变量或直接输入' : '例如 login_token'"
                  filterable
                  clearable
                  allow-create
                  default-first-option
                  @change="updateActiveInnerComponent"
                >
                  <el-option
                    v-for="option in activeInnerComponentReferenceOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  >
                    <div class="reference-option">
                      <span class="reference-option-name">{{ option.value }}</span>
                      <span class="reference-option-source">{{ option.sourceName }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div v-if="activeInnerComponentReferenceOptions.length" class="reference-option-hint">
                  可引用 {{ activeInnerComponentReferenceOptions.length }} 个前序变量
                </div>
              </el-form-item>

              <template v-if="activeInnerComponent.type === 'input'">
                <el-form-item label="执行动作">
                  <el-radio-group v-model="activeInnerComponent.config.action" @change="updateActiveInnerComponent">
                    <el-radio value="fill">填充</el-radio>
                    <el-radio value="press">按键</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item :label="activeInnerComponent.config.action === 'press' ? '按键值' : '输入值'">
                  <el-input v-model="activeInnerComponent.config.value" @change="updateActiveInnerComponent" />
                </el-form-item>
              </template>

              <template v-else-if="['button', 'link', 'tab', 'menuitem', 'clickable'].includes(activeInnerComponent.type)">
                <el-form-item label="执行动作">
                  <el-radio-group v-model="activeInnerComponent.config.action" @change="updateActiveInnerComponent">
                    <el-radio value="click">单击</el-radio>
                    <el-radio value="dblclick">双击</el-radio>
                    <el-radio value="contextmenu">右键</el-radio>
                    <el-radio value="hover">悬停</el-radio>
                  </el-radio-group>
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'select'">
                <el-form-item label="选择值">
                  <el-input v-model="activeInnerComponent.config.selectedValue" @change="updateActiveInnerComponent" />
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'checkbox' || activeInnerComponent.type === 'radio'">
                <el-form-item label="目标状态">
                  <el-switch
                    v-model="activeInnerComponent.config.checked"
                    active-text="勾选"
                    inactive-text="取消勾选"
                    @change="updateActiveInnerComponent"
                  />
                </el-form-item>
              </template>
              <template v-else-if="activeInnerComponent.type === 'file'">
                <el-form-item label="文件路径">
                  <el-input
                    v-model="activeInnerComponent.config.filePath"
                    placeholder="输入执行机可访问的文件路径"
                    @change="updateActiveInnerComponent"
                  />
                </el-form-item>
              </template>
              <template v-else-if="activeInnerComponent.type === 'iframe'">
                <el-form-item label="脚本作用域">
                  <el-input model-value="切入 iframe / 退出 iframe" disabled />
                </el-form-item>
              </template>

              <el-divider content-position="left">输出配置</el-divider>
              <el-form-item label="输出变量">
                <el-input
                  v-model="activeInnerComponent.config.outputName"
                  placeholder="例如 current_user"
                  @change="updateActiveInnerComponent"
                />
              </el-form-item>
              <el-form-item label="输出来源">
                <el-select v-model="activeInnerComponent.config.outputSource" @change="updateActiveInnerComponent">
                  <el-option
                    v-for="option in variableSources"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="activeInnerComponent.config.outputSource === 'custom'" label="输出表达式">
                <el-input
                  v-model="activeInnerComponent.config.outputValue"
                  placeholder="自定义输出表达式"
                  @change="updateActiveInnerComponent"
                />
              </el-form-item>
              <el-divider content-position="left">组件操作</el-divider>
              <el-form-item>
                <el-button type="danger" plain @click="removeInnerComponent(activeInnerComponent.id)">
                  删除当前组件
                </el-button>
              </el-form-item>
            </div>

            <div v-if="selectedNode.config.executionPath && selectedNode.config.executionPath.length" class="execution-path">
              <el-divider content-position="left">执行路径</el-divider>
              <el-scrollbar max-height="300px">
                <div class="path-list">
                  <div
                    v-for="(step, index) in selectedNode.config.executionPath"
                    :key="index"
                    class="path-step"
                    :class="{ active: selectedExecutionStepIndex === index }"
                    @click="selectExecutionStep(index)"
                  >
                    <div class="step-header">
                      <div class="step-title">
                        <span class="step-number">{{ index + 1 }}</span>
                        <span class="step-action">{{ step.action }}</span>
                      </div>
                      <el-button link size="small" type="danger" @click.stop="removeExecutionStep(index)">删除</el-button>
                    </div>
                    <div class="step-from">
                      <el-icon><Right /></el-icon>
                      <span>{{ step.from.elementType }}: {{ step.from.elementText }}</span>
                    </div>
                    <div class="step-to" v-if="step.to">
                      <el-icon><Right /></el-icon>
                      <span>{{ step.to.elementType }}: {{ step.to.elementText }}</span>
                    </div>
                    <div class="step-config">
                      <el-select
                        v-model="step.action"
                        size="small"
                        @change="updateExecutionStep(index, step)"
                      >
                        <el-option label="点击 (click)" value="click" />
                        <el-option label="填充 (fill)" value="fill" />
                        <el-option label="选择 (select)" value="select" />
                        <el-option label="悬停 (hover)" value="hover" />
                        <el-option label="双击 (dblclick)" value="dblclick" />
                      </el-select>
                      <el-input
                        v-if="step.action === 'fill'"
                        v-model="step.value"
                        size="small"
                        placeholder="输入值"
                        @change="updateExecutionStep(index, step)"
                        style="margin-top: 4px;"
                      />
                    </div>
                  </div>
                </div>
              </el-scrollbar>
            </div>

            <!-- 快照元素树显示 -->
            <div v-if="selectedNode.config.snapshotData" class="snapshot-elements">
              <el-divider content-position="left">页面元素</el-divider>
              <el-alert
                :title="`共 ${selectedNode.config.snapshotData.interactiveElements.length} 个可交互元素`"
                type="success"
                :closable="false"
                style="margin-bottom: 12px"
              />
              <el-scrollbar max-height="300px">
                <div class="elements-list">
                  <div
                    v-for="element in selectedNode.config.snapshotData.interactiveElements"
                    :key="element.id"
                    class="element-item"
                    @click="selectElement(element)"
                  >
                    <div class="element-type">{{ element.type }}</div>
                    <div class="element-text" v-if="element.text">{{ element.text }}</div>
                    <div class="element-ref" v-if="element.ref">ref: {{ element.ref }}</div>
                    <div class="element-selectors" v-if="element.selectors && element.selectors.length">
                      <el-tag size="small" type="info">
                        {{ element.selectors[0].value }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </el-scrollbar>
            </div>
          </el-form>

          <!-- 操作节点配置 -->
          <el-form v-else-if="selectedNode.type === 'operation'" label-width="120px">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.config.name" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="操作类型">
              <el-select v-model="selectedNode.config.operationType" @change="updateNodeConfig">
                <el-option label="等待(Sleep)" value="sleep" />
                <el-option label="等待元素出现" value="waitForSelector" />
                <el-option label="等待导航" value="waitForNavigation" />
                <el-option label="等待页面加载" value="waitForLoadState" />
                <el-option label="截图" value="screenshot" />
                <el-option label="值断言" value="assertValue" />
                <el-option label="自定义代码" value="custom" />
              </el-select>
            </el-form-item>
            <el-form-item label="等待时间(ms)" v-if="selectedNode.config.operationType === 'sleep'">
              <el-input-number v-model="selectedNode.config.timeout" @change="updateNodeConfig" :min="0" />
            </el-form-item>
            <el-form-item label="选择器" v-if="['waitForSelector'].includes(selectedNode.config.operationType)">
              <el-input v-model="selectedNode.config.selector" @change="updateNodeConfig" />
            </el-form-item>
            <template v-if="selectedNode.config.operationType === 'assertValue'">
              <el-form-item label="实际值来源">
                <el-select v-model="selectedNode.config.assertionTarget" @change="updateNodeConfig">
                  <el-option
                    v-for="option in assertionTargets"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item
                v-if="['selectorText', 'selectorValue', 'selectorChecked'].includes(selectedNode.config.assertionTarget)"
                label="选择器"
              >
                <el-input
                  v-model="selectedNode.config.assertionSelector"
                  placeholder="例如 .el-table__row:first-child td:nth-child(2)"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item v-if="selectedNode.config.assertionTarget === 'variable'" label="变量名">
                <el-select
                  v-model="selectedNode.config.assertionActualReference"
                  :placeholder="selectedNodeReferenceOptions.length ? '选择已有变量或直接输入' : '例如 edited_name'"
                  filterable
                  clearable
                  allow-create
                  default-first-option
                  @change="updateNodeConfig"
                >
                  <el-option
                    v-for="option in selectedNodeReferenceOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="selectedNode.config.assertionTarget === 'custom'" label="实际值表达式">
                <el-input
                  v-model="selectedNode.config.assertionActualExpression"
                  placeholder="例如 flow_vars.get('edited_name', '')"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item label="比较方式">
                <el-select v-model="selectedNode.config.assertionOperator" @change="updateNodeConfig">
                  <el-option
                    v-for="option in assertionOperators"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="预期值模式">
                <el-radio-group v-model="selectedNode.config.expectedMode" @change="updateNodeConfig">
                  <el-radio value="literal">固定值</el-radio>
                  <el-radio value="reference">引用变量</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="selectedNode.config.expectedMode === 'reference'" label="预期变量">
                <el-select
                  v-model="selectedNode.config.expectedReference"
                  :placeholder="selectedNodeReferenceOptions.length ? '选择已有变量或直接输入' : '例如 expected_name'"
                  filterable
                  clearable
                  allow-create
                  default-first-option
                  @change="updateNodeConfig"
                >
                  <el-option
                    v-for="option in selectedNodeReferenceOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-else label="预期值">
                <el-input v-model="selectedNode.config.expectedValue" @change="updateNodeConfig" />
              </el-form-item>
              <el-form-item label="超时时间(ms)">
                <el-input-number v-model="selectedNode.config.assertionTimeout" @change="updateNodeConfig" :min="0" />
              </el-form-item>
            </template>
            <el-form-item label="自定义代码" v-if="selectedNode.config.operationType === 'custom'">
              <el-input
                v-model="selectedNode.config.customCode"
                type="textarea"
                :rows="6"
                @change="updateNodeConfig"
              />
            </el-form-item>
          </el-form>

          <!-- 结束节点配置 -->
          <el-form v-else-if="selectedNode.type === 'end'" label-width="120px">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.config.name" @change="updateNodeConfig" />
            </el-form-item>
            <el-form-item label="生成报告">
              <el-switch v-model="selectedNode.config.generateReport" @change="updateNodeConfig" />
            </el-form-item>
            <el-divider content-position="left">变量输入输出</el-divider>
            <el-form-item label="输入模式">
              <el-radio-group v-model="selectedNode.config.inputMode" @change="updateNodeConfig">
                <el-radio
                  v-for="mode in inputModes"
                  :key="mode.value"
                  :value="mode.value"
                >
                  {{ mode.label }}
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.inputMode === 'literal'" label="输入值">
              <el-input
                v-model="selectedNode.config.inputValue"
                placeholder="结束节点输入值"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item v-else label="引用变量">
              <el-select
                v-model="selectedNode.config.inputReference"
                :placeholder="selectedNodeReferenceOptions.length ? '选择已有变量或直接输入' : '例如 final_summary'"
                filterable
                clearable
                allow-create
                default-first-option
                @change="updateNodeConfig"
              >
                <el-option
                  v-for="option in selectedNodeReferenceOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                >
                  <div class="reference-option">
                    <span class="reference-option-name">{{ option.value }}</span>
                    <span class="reference-option-source">{{ option.sourceName }}</span>
                  </div>
                </el-option>
              </el-select>
              <div v-if="selectedNodeReferenceOptions.length" class="reference-option-hint">
                可引用 {{ selectedNodeReferenceOptions.length }} 个前序变量
              </div>
            </el-form-item>
            <el-form-item label="输入别名">
              <el-input
                v-model="selectedNode.config.inputAlias"
                placeholder="例如 final_input"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出变量">
              <el-input
                v-model="selectedNode.config.outputName"
                placeholder="例如 final_result"
                @change="updateNodeConfig"
              />
            </el-form-item>
            <el-form-item label="输出来源">
              <el-select v-model="selectedNode.config.outputSource" @change="updateNodeConfig">
                <el-option
                  v-for="option in variableSources"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item v-if="selectedNode.config.outputSource === 'custom'" label="输出表达式">
              <el-input
                v-model="selectedNode.config.outputValue"
                placeholder="例如 'success'"
                @change="updateNodeConfig"
              />
            </el-form-item>
          </el-form>

          <!-- 组件节点配置 -->
          <el-form v-else-if="selectedNode.type === 'component'" label-width="120px">
            <el-form-item label="组件类型">
              <el-tag :type="getComponentTagType(selectedNode.componentType)">
                {{ getComponentTypeName(selectedNode.componentType) }}
              </el-tag>
            </el-form-item>

            <el-form-item label="组件标识">
              <el-input v-model="selectedNode.config.text" disabled />
            </el-form-item>

            <el-form-item label="所属页面">
              <el-input v-model="selectedNode.config.pageName" disabled />
            </el-form-item>

            <el-divider content-position="left">操作配置</el-divider>

            <!-- 输入框配置 -->
            <template v-if="selectedNode.componentType === 'input'">
              <el-form-item label="输入值">
                <el-input
                  v-model="selectedNode.config.value"
                  :placeholder="selectedNode.config.placeholder"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-alert
                title="此值将作为测试数据填充到输入框"
                type="info"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </template>

            <!-- 按钮配置 -->
            <template v-else-if="selectedNode.componentType === 'button'">
              <el-form-item label="点击方式">
                <el-radio-group v-model="selectedNode.config.action" @change="updateNodeConfig">
                  <el-radio value="click">单击</el-radio>
                  <el-radio value="dblclick">双击</el-radio>
                  <el-radio value="contextmenu">右键</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-alert
                :title="`将执行 ${selectedNode.config.action === 'click' ? '单击' : selectedNode.config.action === 'dblclick' ? '双击' : '右键'} 操作`"
                type="info"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </template>

            <!-- 下拉框配置 -->
            <template v-else-if="selectedNode.componentType === 'select'">
              <el-form-item label="下拉选项">
                <el-tag
                  v-for="(option, index) in selectedNode.config.options"
                  :key="index"
                  size="small"
                  style="margin-right: 4px; margin-bottom: 4px;"
                >
                  {{ option }}
                </el-tag>
                <el-text v-if="!selectedNode.config.options || selectedNode.config.options.length === 0" type="info">
                  暂无选项数据
                </el-text>
              </el-form-item>
              <el-form-item label="选择值">
                <el-select v-model="selectedNode.config.selectedValue" @change="updateNodeConfig">
                  <el-option
                    v-for="(option, index) in selectedNode.config.options"
                    :key="index"
                    :label="option"
                    :value="option"
                  />
                </el-select>
              </el-form-item>
              <el-alert
                title="选择的值将作为测试数据设置到下拉框"
                type="info"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </template>

            <!-- 复选框配置 -->
            <template v-else-if="selectedNode.componentType === 'checkbox'">
              <el-form-item label="选中状态">
                <el-switch v-model="selectedNode.config.checked" @change="updateNodeConfig" />
              </el-form-item>
              <el-alert
                :title="`将${selectedNode.config.checked ? '勾选' : '取消勾选'}此复选框`"
                type="info"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </template>

            <!-- 链接配置 -->
            <template v-else-if="selectedNode.componentType === 'link'">
              <el-form-item label="点击方式">
                <el-radio-group v-model="selectedNode.config.action" @change="updateNodeConfig">
                  <el-radio value="click">单击</el-radio>
                  <el-radio value="contextmenu">右键</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-alert
                title="点击链接将导航到新页面"
                type="warning"
                :closable="false"
                style="margin-bottom: 12px"
              />
            </template>

            <!-- 元素数据 -->
            <el-divider content-position="left">元素信息</el-divider>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="元素ID">
                {{ selectedNode.config.elementId }}
              </el-descriptions-item>
              <el-descriptions-item label="元素类型">
                {{ selectedNode.config.elementData?.type }}
              </el-descriptions-item>
              <el-descriptions-item label="选择器" v-if="selectedNode.config.elementData?.selectors">
                <el-text size="small" type="info">
                  {{ selectedNode.config.elementData.selectors[0]?.value }}
                </el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-form>
          </template>
          <el-empty v-else description="点击画布节点查看节点详情" :image-size="72" />
          </template>

          <template v-else-if="activeDetailMenu === 'component'">
            <el-form v-if="activeInnerComponent" label-width="120px">
              <el-descriptions class="detail-summary" :column="1" size="small" border>
                <el-descriptions-item label="组件ID">
                  {{ activeInnerComponent.id }}
                </el-descriptions-item>
                <el-descriptions-item label="所属页面">
                  {{ selectedNode?.config?.pageName || selectedNode?.config?.name || '页面节点' }}
                </el-descriptions-item>
                <el-descriptions-item label="父级组件" v-if="activeInnerComponent.parentId">
                  {{ activeInnerComponent.parentId }}
                </el-descriptions-item>
              </el-descriptions>

              <el-divider content-position="left">组件配置</el-divider>
              <el-form-item label="组件类型">
                <el-tag :type="getComponentTagType(activeInnerComponent.type)">
                  {{ getComponentTypeName(activeInnerComponent.type) }}
                </el-tag>
              </el-form-item>
              <el-form-item label="映射元素" required>
                <el-select
                  :model-value="activeInnerComponent.elementId"
                  placeholder="请选择 YML 元素"
                  filterable
                  @change="handleActiveComponentElementChange"
                >
                  <el-option
                    v-for="element in getEditableElementsForComponent(activeInnerComponent)"
                    :key="element.id"
                    :label="`${element.type}: ${element.text || element.ref || element.id}`"
                    :value="element.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="选择器">
                <el-input :model-value="getComponentSelectorPreview(activeInnerComponent)" disabled />
              </el-form-item>
              <el-form-item label="输入模式">
                <el-radio-group v-model="activeInnerComponent.config.inputMode" @change="updateActiveInnerComponent">
                  <el-radio
                    v-for="mode in inputModes"
                    :key="mode.value"
                    :value="mode.value"
                  >
                    {{ mode.label }}
                  </el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="activeInnerComponent.config.inputMode === 'reference'" label="引用变量">
                <el-select
                  v-model="activeInnerComponent.config.inputReference"
                  :placeholder="activeInnerComponentReferenceOptions.length ? '选择已有变量或直接输入' : '例如 login_token'"
                  filterable
                  clearable
                  allow-create
                  default-first-option
                  @change="updateActiveInnerComponent"
                >
                  <el-option
                    v-for="option in activeInnerComponentReferenceOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  >
                    <div class="reference-option">
                      <span class="reference-option-name">{{ option.value }}</span>
                      <span class="reference-option-source">{{ option.sourceName }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div v-if="activeInnerComponentReferenceOptions.length" class="reference-option-hint">
                  可引用 {{ activeInnerComponentReferenceOptions.length }} 个前序变量
                </div>
              </el-form-item>

              <template v-if="activeInnerComponent.type === 'input'">
                <el-form-item label="执行动作">
                  <el-radio-group v-model="activeInnerComponent.config.action" @change="updateActiveInnerComponent">
                    <el-radio value="fill">填充</el-radio>
                    <el-radio value="press">按键</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item :label="activeInnerComponent.config.action === 'press' ? '按键值' : '输入值'">
                  <el-input v-model="activeInnerComponent.config.value" @change="updateActiveInnerComponent" />
                </el-form-item>
              </template>

              <template v-else-if="['button', 'link', 'tab', 'menuitem', 'clickable'].includes(activeInnerComponent.type)">
                <el-form-item label="执行动作">
                  <el-radio-group v-model="activeInnerComponent.config.action" @change="updateActiveInnerComponent">
                    <el-radio value="click">单击</el-radio>
                    <el-radio value="dblclick">双击</el-radio>
                    <el-radio value="contextmenu">右键</el-radio>
                    <el-radio value="hover">悬停</el-radio>
                  </el-radio-group>
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'select'">
                <el-form-item label="选择值">
                  <el-input v-model="activeInnerComponent.config.selectedValue" @change="updateActiveInnerComponent" />
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'checkbox' || activeInnerComponent.type === 'radio'">
                <el-form-item label="目标状态">
                  <el-switch
                    v-model="activeInnerComponent.config.checked"
                    active-text="勾选"
                    inactive-text="取消勾选"
                    @change="updateActiveInnerComponent"
                  />
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'file'">
                <el-form-item label="文件路径">
                  <el-input
                    v-model="activeInnerComponent.config.filePath"
                    placeholder="输入执行机可访问的文件路径"
                    @change="updateActiveInnerComponent"
                  />
                </el-form-item>
              </template>

              <template v-else-if="activeInnerComponent.type === 'iframe'">
                <el-form-item label="脚本作用域">
                  <el-input model-value="切入 iframe / 退出 iframe" disabled />
                </el-form-item>
              </template>

              <el-divider content-position="left">输出配置</el-divider>
              <el-form-item label="输出变量">
                <el-input
                  v-model="activeInnerComponent.config.outputName"
                  placeholder="例如 current_user"
                  @change="updateActiveInnerComponent"
                />
              </el-form-item>
              <el-form-item label="输出来源">
                <el-select v-model="activeInnerComponent.config.outputSource" @change="updateActiveInnerComponent">
                  <el-option
                    v-for="option in variableSources"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-if="activeInnerComponent.config.outputSource === 'custom'" label="输出表达式">
                <el-input
                  v-model="activeInnerComponent.config.outputValue"
                  placeholder="自定义输出表达式"
                  @change="updateActiveInnerComponent"
                />
              </el-form-item>
              <el-divider content-position="left">组件操作</el-divider>
              <el-form-item>
                <el-button type="danger" plain @click="removeInnerComponent(activeInnerComponent.id)">
                  删除当前组件
                </el-button>
              </el-form-item>
            </el-form>

            <el-form v-else-if="selectedNode?.type === 'component'" label-width="120px">
              <el-form-item label="组件类型">
                <el-tag :type="getComponentTagType(selectedNode.componentType)">
                  {{ getComponentTypeName(selectedNode.componentType) }}
                </el-tag>
              </el-form-item>
              <el-form-item label="组件标识">
                <el-input v-model="selectedNode.config.text" disabled />
              </el-form-item>
              <el-form-item label="所属页面">
                <el-input v-model="selectedNode.config.pageName" disabled />
              </el-form-item>
              <el-divider content-position="left">组件配置</el-divider>
              <el-form-item v-if="selectedNode.componentType === 'input'" label="输入值">
                <el-input
                  v-model="selectedNode.config.value"
                  :placeholder="selectedNode.config.placeholder"
                  @change="updateNodeConfig"
                />
              </el-form-item>
              <el-form-item v-else-if="['button', 'link'].includes(selectedNode.componentType)" label="点击方式">
                <el-radio-group v-model="selectedNode.config.action" @change="updateNodeConfig">
                  <el-radio value="click">单击</el-radio>
                  <el-radio value="dblclick" v-if="selectedNode.componentType === 'button'">双击</el-radio>
                  <el-radio value="contextmenu">右键</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-else-if="selectedNode.componentType === 'select'" label="选择值">
                <el-select v-model="selectedNode.config.selectedValue" @change="updateNodeConfig">
                  <el-option
                    v-for="(option, index) in selectedNode.config.options"
                    :key="index"
                    :label="option"
                    :value="option"
                  />
                </el-select>
              </el-form-item>
              <el-form-item v-else-if="selectedNode.componentType === 'checkbox'" label="选中状态">
                <el-switch v-model="selectedNode.config.checked" @change="updateNodeConfig" />
              </el-form-item>
              <el-divider content-position="left">元素信息</el-divider>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="元素ID">
                  {{ selectedNode.config.elementId || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="元素类型">
                  {{ selectedNode.config.elementData?.type || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="选择器" v-if="selectedNode.config.elementData?.selectors">
                  <el-text size="small" type="info">
                    {{ selectedNode.config.elementData.selectors[0]?.value }}
                  </el-text>
                </el-descriptions-item>
              </el-descriptions>
            </el-form>

            <el-empty v-else description="点击页面组件查看组件详情" :image-size="72" />
          </template>

          <template v-else-if="activeDetailMenu === 'execution'">
            <div v-if="selectedExecutionResultDetail" class="execution-detail-panel">
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="执行状态">
                  <el-tag :type="getExecutionStatusTagType(selectedExecutionResultDetail.result.status)">
                    {{ formatExecutionResultStatus(selectedExecutionResultDetail.result.status) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="节点">
                  {{ selectedExecutionResultDetail.nodeName }}
                </el-descriptions-item>
                <el-descriptions-item label="组件" v-if="selectedExecutionResultDetail.componentName">
                  {{ selectedExecutionResultDetail.componentName }}
                </el-descriptions-item>
                <el-descriptions-item label="标题" v-if="selectedExecutionResultDetail.result.title">
                  {{ selectedExecutionResultDetail.result.title }}
                </el-descriptions-item>
                <el-descriptions-item label="耗时">
                  {{ selectedExecutionResultDetail.result.duration || 0 }} ms
                </el-descriptions-item>
                <el-descriptions-item label="开始时间" v-if="selectedExecutionResultDetail.result.startedAt">
                  {{ selectedExecutionResultDetail.result.startedAt }}
                </el-descriptions-item>
                <el-descriptions-item label="结束时间" v-if="selectedExecutionResultDetail.result.finishedAt">
                  {{ selectedExecutionResultDetail.result.finishedAt }}
                </el-descriptions-item>
                <el-descriptions-item label="执行ID" v-if="selectedExecutionResultDetail.result.executionId">
                  {{ selectedExecutionResultDetail.result.executionId }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="hasExecutionPayload(selectedExecutionResultDetail.result.input)" class="execution-detail-section">
                <div class="execution-detail-title">输入</div>
                <pre>{{ formatExecutionPayload(selectedExecutionResultDetail.result.input) }}</pre>
              </div>
              <div v-if="hasExecutionPayload(selectedExecutionResultDetail.result.output)" class="execution-detail-section">
                <div class="execution-detail-title">输出</div>
                <pre>{{ formatExecutionPayload(selectedExecutionResultDetail.result.output) }}</pre>
              </div>
              <div v-if="selectedExecutionResultDetail.result.errorLog" class="execution-detail-section execution-detail-error">
                <div class="execution-detail-title">失败日志</div>
                <pre>{{ selectedExecutionResultDetail.result.errorLog }}</pre>
              </div>
              <div v-if="selectedExecutionResultDetail.result.screenshotUrl" class="execution-detail-section">
                <div class="execution-detail-title">截图</div>
                <el-image
                  class="execution-detail-screenshot"
                  :src="selectedExecutionResultDetail.result.screenshotUrl"
                  :preview-src-list="[selectedExecutionResultDetail.result.screenshotUrl]"
                  fit="contain"
                  preview-teleported
                />
              </div>
            </div>
            <el-empty v-else description="点击组件执行结果查看详情" :image-size="72" />
          </template>

          <template v-else-if="activeDetailMenu === 'edge'">
            <template v-if="selectedEdge">
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="连线ID">
                  {{ selectedEdgeSummary.id }}
                </el-descriptions-item>
                <el-descriptions-item label="起点节点">
                  {{ selectedEdgeSummary.sourceNode }}
                </el-descriptions-item>
                <el-descriptions-item label="起点端口">
                  {{ selectedEdgeSummary.sourcePort || '默认端口' }}
                </el-descriptions-item>
                <el-descriptions-item label="终点节点">
                  {{ selectedEdgeSummary.targetNode }}
                </el-descriptions-item>
                <el-descriptions-item label="终点端口">
                  {{ selectedEdgeSummary.targetPort || '默认端口' }}
                </el-descriptions-item>
              </el-descriptions>
              <div class="panel-actions">
                <el-button type="danger" plain @click="deleteSelectedGraphItem">删除连线</el-button>
              </div>
            </template>
            <el-empty v-else description="点击连线查看连线详情" :image-size="72" />
          </template>

        </el-scrollbar>
      </div>
      </aside>
      </div>
      </template>
    </ManualWorkspaceRecordingShell>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Graph, Path } from '@antv/x6'
import { register } from '@antv/x6-vue-shape'
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus'
import {
  VideoPlay, Document, Setting, CircleClose, Close, Right, DocumentCopy, Download,
  Edit, ArrowDown, Check, Link, Delete
} from '@element-plus/icons-vue'
import {
  getPlaywrightSnapshots,
  getPlaywrightSnapshotContent,
  getPlaywrightRecordingFlow,
  downloadLocalAgentPackage,
  createPlaywrightRecordingFlow,
  createVisualFlow,
  createVisualFlowExecution,
  executeVisualFlowScript,
  finalizeVisualFlowExecution,
  getVisualFlowExecutionDetail,
  getVisualFlowDetail,
  startPlaywrightRecording,
  stopPlaywrightRecording,
  updateVisualFlow,
  savePlaywrightSnapshotParseResult
} from '@/api/testcases'
import playwrightGenerator from '@/utils/playwrightGenerator'
import {
  analyzeSnapshotContent,
  buildSnapshotParsePayload,
  buildSnapshotRuntimeData,
  hasPersistedParsedSnapshot
} from '@/utils/snapshotParseUtils'
import { useUserStore } from '@/stores/user'
import ManualWorkspaceDirectoryPanel from '@/views/manual-testcases/ManualWorkspaceDirectoryPanel.vue'
import ManualWorkspaceRecordingShell from '@/views/manual-testcases/ManualWorkspaceRecordingShell.vue'
import { buildManualTestcaseSectionLocation, getManualTestcaseSectionsByPrimary } from '@/utils/manualTestcaseWorkspace'
import { isManualTestcaseSectionAccessible } from '@/utils/permissions'
import PageNodeContent from './PageNodeContent.vue'
import ComponentNode from './ComponentNode.vue'
import {
  COMPONENT_LIBRARY,
  FLOW_ASSERTION_OPERATORS,
  FLOW_ASSERTION_TARGETS,
  FLOW_INPUT_MODES,
  FLOW_PORT_GROUPS,
  FLOW_VARIABLE_SOURCES,
  PAGE_NODE_LAYOUT,
  buildComponentDefaultConfig as buildFlowComponentDefaultConfig,
  buildComponentLayouts,
  buildIframeSharedPortId,
  buildPageNodePorts,
  clampPercent,
  ensureFlowConfig,
  findIframeDropTarget,
  getComponentActionText as getFlowComponentActionText,
  getComponentDisplayText as getFlowComponentDisplayText,
  getComponentIcon as getFlowComponentIcon,
  getComponentSelectorPreview as getFlowComponentSelectorPreview,
  getComponentSize,
  getComponentTagType as getFlowComponentTagType,
  getComponentTypeName as getFlowComponentTypeName,
  getDefaultComponentAction as getFlowDefaultComponentAction,
  getPageInnerRect,
  isElementCompatible as isFlowElementCompatible,
  isElementInsideElement,
  normalizeExecutionConnectionPorts,
  normalizeIframePortId,
  normalizeInnerComponents as normalizeFlowInnerComponents
} from './visualFlowUtils'

const containerRef = ref(null)
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
let graph = null
let executionPollingTimer = null
const selectedNode = ref(null)
const selectedEdge = ref(null)
const selectedExecutionStepIndex = ref(null)
const selectedInnerComponentId = ref(null)
const activeLeftPanel = ref('')
const activeDetailMenu = ref('node')
const selectedExecutionResultRef = ref({
  nodeId: '',
  key: '',
  componentId: ''
})
const snapshotCatalog = ref([])
const snapshotData = ref({}) // 已加载的快照数据缓存
const scriptDialogVisible = ref(false)
const generatedScript = ref('')
const generatedScriptSignature = ref('')
const flowScriptRevision = ref(0)
const currentFlowId = ref('')
const currentFlowMeta = ref(null)
const flowLoading = ref(false)
const backendExecuting = ref(false)
const localExecuting = ref(false)
const activeExecutionId = ref('')
const activeExecutionRunType = ref('')
const recordingStarting = ref(false)
const recordingContinuing = ref(false)
const recordingStopping = ref(false)
const activeInnerComponentId = ref(null)
const highlightedPageNodeId = ref(null)
const liveRecordingSessionId = ref('')
const liveRecordingMode = ref('')
const continueRecordingAnchor = ref(null)
const continueRecordingMergeState = ref({
  sessionId: '',
  mergedPageIds: [],
  mergedPageMap: {},
  mergedComponentMap: {},
  lastSignature: '',
  appendAfterNodeId: '',
  detachedSuccessorEdges: [],
  lastComponentByPageId: {}
})
const liveFlowActive = ref(false)
const researchContext = ref({
  project_id: '',
  version_id: 'all',
  module_id: '',
  module_name: '',
  module_path: ''
})
let liveFlowTimer = null
const LOCAL_AGENT_SERVICE_URL = 'http://127.0.0.1:18765'
const LOCAL_AGENT_PROTOCOL = 'testhub-agent://'
const RECORDING_METHOD_LOCAL_AGENT = 'local_agent_playwright'
const workspaceSectionTabs = computed(() => (
  getManualTestcaseSectionsByPrimary('recording')
    .filter(item => isManualTestcaseSectionAccessible(item.name, userStore.hasPermissionCode))
))
const isLiveRecordingFlow = computed(() => Boolean(liveRecordingSessionId.value))

// 组件配置对话框状态
const componentConfigDialogVisible = ref(false)
const currentComponentConfig = ref({
  pageNodeId: null,
  type: null,
  elementId: null,
  parentId: null,
  position: { x: 0, y: 0 },
  // 特定配置
  value: '',
  action: 'click',
  selectedValue: '',
  checked: false,
  filePath: ''
})

const clampPosition = clampPercent

const getDefaultComponentAction = getFlowDefaultComponentAction

const buildComponentDefaultConfig = buildFlowComponentDefaultConfig

const handleWorkspaceSectionSelect = sectionName => {
  if (sectionName === 'visual-flow') {
    return
  }

  const targetLocation = buildManualTestcaseSectionLocation(sectionName, route.query)
  if (targetLocation) {
    router.push(targetLocation)
  }
}

const handleResearchContextChange = context => {
  researchContext.value = { ...(context || {}) }
}

const syncResearchContextFromModule = module => {
  if (!module || typeof module !== 'object') {
    return
  }
  researchContext.value = {
    ...researchContext.value,
    project_id: module.project_id || researchContext.value.project_id || '',
    module_id: module.module_id || researchContext.value.module_id || '',
    module_name: module.module_name || researchContext.value.module_name || '',
    module_path: module.module_path || researchContext.value.module_path || ''
  }
}

const extractSnapshotResults = (response) => {
  if (Array.isArray(response?.data?.results)) {
    return response.data.results
  }
  if (Array.isArray(response?.results)) {
    return response.results
  }
  return []
}

const extractSnapshotPayload = (response) => response?.data || response || {}

const updateSnapshotCatalogEntry = snapshot => {
  const filename = snapshot?.filename
  if (!filename) return

  const nextSnapshot = {
    ...snapshot,
    page_name: snapshot.page_name || ''
  }

  const index = snapshotCatalog.value.findIndex(item => item.filename === filename)
  if (index >= 0) {
    snapshotCatalog.value[index] = {
      ...snapshotCatalog.value[index],
      ...nextSnapshot
    }
  } else {
    snapshotCatalog.value.push(nextSnapshot)
  }
}

const cacheSnapshotRuntimeData = (payload, filename) => {
  const normalizedPayload = {
    ...payload,
    filename: payload?.filename || filename
  }
  const runtimeData = buildSnapshotRuntimeData(normalizedPayload)
  const resolvedFilename = runtimeData.filename || filename
  if (!resolvedFilename) return null

  snapshotData.value[resolvedFilename] = runtimeData
  updateSnapshotCatalogEntry({
    filename: resolvedFilename,
    page_name: normalizedPayload.page_name || runtimeData.pageName || '',
    parse_status: normalizedPayload.parsed_snapshot?.parse_status || normalizedPayload.parse_status || runtimeData.parseStatus,
    parsed_at: normalizedPayload.parsed_snapshot?.parsed_at || normalizedPayload.parsed_at || runtimeData.parsedAt,
    interactive_count: normalizedPayload.parsed_snapshot?.interactive_count || normalizedPayload.interactive_count || runtimeData.interactiveElements.length,
    line_count: normalizedPayload.parsed_snapshot?.line_count || normalizedPayload.line_count || 0,
    parse_error: normalizedPayload.parsed_snapshot?.error || normalizedPayload.parse_error || ''
  })

  return runtimeData
}

const ensureSnapshotRuntimeData = async (filename, payload = null) => {
  if (!filename) return null

  if (snapshotData.value[filename]) {
    return snapshotData.value[filename]
  }

  const snapshotPayload = payload || extractSnapshotPayload(await getPlaywrightSnapshotContent(filename))
  if (hasPersistedParsedSnapshot(snapshotPayload)) {
    return cacheSnapshotRuntimeData(snapshotPayload, filename)
  }

  const analysis = analyzeSnapshotContent(snapshotPayload.content || '')
  const parseResponse = await savePlaywrightSnapshotParseResult(filename, buildSnapshotParsePayload(analysis))
  const mergedPayload = {
    ...snapshotPayload,
    ...(parseResponse?.data || parseResponse || {}),
    filename
  }

  return cacheSnapshotRuntimeData(mergedPayload, filename)
}

const getSnapshotMetaByFilename = (filename) => {
  return snapshotCatalog.value.find(item => item.filename === filename) || null
}

const getSnapshotByPageName = (pageName) => {
  return snapshotCatalog.value.find(item => item.page_name === pageName) || null
}

const getSnapshotDisplayName = (filename) => {
  return getSnapshotMetaByFilename(filename)?.page_name || filename
}

const getSnapshotToolbarTitle = (filename) => {
  const snapshot = getSnapshotMetaByFilename(filename)
  if (!snapshot?.page_name) {
    return filename
  }
  return `${snapshot.page_name} (${filename})`
}

const pageNameOptions = computed(() => {
  return [...snapshotCatalog.value]
    .filter(item => item.page_name)
    .sort((left, right) => left.page_name.localeCompare(right.page_name, 'zh-CN'))
})

const ensurePageNodeConfig = (config = {}) => ensureFlowConfig(config)

const getSnapshotElementById = (pageConfig, elementId) => {
  return pageConfig?.snapshotData?.interactiveElements?.find(element => element.id === elementId) || null
}

const getComponentDisplayTextLegacy = (component) => {
  return component?.elementData?.text || component?.elementData?.ref || component?.elementId || '未映射元素'
}

const getComponentSelectorPreviewLegacy = (component) => {
  const primarySelector = component?.elementData?.selectors?.[0]?.value
  if (primarySelector) {
    return primarySelector
  }
  if (component?.elementData?.ref) {
    return `[data-ref="${component.elementData.ref}"]`
  }
  return ''
}

const getComponentDisplayText = getFlowComponentDisplayText
const getComponentSelectorPreview = getFlowComponentSelectorPreview
const getComponentActionText = getFlowComponentActionText
const getComponentIcon = getFlowComponentIcon
const flowNodeTypes = new Set(['start', 'page', 'operation', 'end'])
const CONTINUE_RECORDING_MODE_NEW = 'new'
const CONTINUE_RECORDING_MODE_APPEND = 'continue'
const FLOW_COMPONENT_GRID = {
  cellWidth: 240,
  cellHeight: 150,
  minWidth: 420,
  minHeight: 450,
  maxColumns: 6
}

const CONTINUATION_COMPONENT_LAYOUT = {
  xMin: 10,
  xMax: 90,
  yMin: 16,
  yMax: 88,
  defaultY: 50,
  rowGap: 22,
  minExistingRowGap: 16
}

const normalizeInnerComponents = (pageConfig) => {
  normalizeFlowInnerComponents(pageConfig, getSnapshotElementById)
}

const buildPageNodeDataPayload = (data = {}) => {
  const config = data?.config || {}
  return {
    ...data,
    config: {
      ...config,
      innerComponents: [...(config.innerComponents || [])],
      executionPath: Array.isArray(config.executionPath) ? [...config.executionPath] : []
    }
  }
}

const refreshPageNodeView = (node, { syncPorts = false, delay = 0 } = {}) => {
  if (!node || node.shape !== 'page-node') {
    return
  }

  setTimeout(() => {
    const view = graph?.findViewByCell?.(node)
    if (typeof view?.renderVueComponent === 'function') {
      view.renderVueComponent()
    }
    if (syncPorts) {
      syncPageNodePorts(node)
    }
  }, delay)
}

const refreshConnectedEdges = (node) => {
  if (!graph || !node) {
    return
  }

  const connectedEdges = graph.getConnectedEdges?.(node) || []
  connectedEdges.forEach(edge => {
    normalizeEdgeDirection(edge)
    applyStandardEdgeStyle(edge)
    ensureEdgeVisible(edge)
    const view = graph.findViewByCell?.(edge)
    view?.update?.()
  })
}

const getGraphCellsSnapshot = () => {
  const cells = graph?.toJSON?.()?.cells
  return Array.isArray(cells) ? cells : []
}

const getGraphPageNodes = () => graph?.getNodes?.().filter(node => node.getData?.()?.type === 'page') || []

const getGraphNodeMap = () => {
  const cells = getGraphCellsSnapshot()
  return new Map(
    cells
      .filter(cell => flowNodeTypes.has(cell?.data?.type) && cell.shape !== 'edge')
      .map(cell => [cell.id, cell])
  )
}

const getGraphExecutionOrder = () => {
  const cells = getGraphCellsSnapshot()
  const nodes = cells.filter(cell => flowNodeTypes.has(cell?.data?.type) && cell.shape !== 'edge')
  const edges = cells.filter(cell => cell?.shape === 'edge')
  return playwrightGenerator.topologicalSort(nodes, edges)
}

const buildVariableEntry = ({ value, sourceName, sourceType, variableType }) => {
  const variableName = String(value || '').trim()
  if (!variableName) {
    return null
  }

  const typeLabel = variableType === 'inputAlias' ? '输入别名' : '输出变量'
  return {
    value: variableName,
    label: `${variableName} (${sourceName} · ${typeLabel})`,
    sourceName,
    sourceType,
    variableType
  }
}

const mergeVariableEntries = (entries = []) => {
  const latestByName = new Map()

  entries.forEach((entry, index) => {
    if (!entry?.value) {
      return
    }
    latestByName.set(entry.value, {
      ...entry,
      order: index
    })
  })

  return [...latestByName.values()].sort((left, right) => left.order - right.order)
}

const getFlowNodeName = (nodeCell) => {
  const nodeData = nodeCell?.data || nodeCell?.getData?.() || {}
  return nodeData?.config?.name || nodeData?.config?.pageName || `${nodeData?.type || 'node'}-${nodeCell?.id || ''}`
}

const collectNodeVariableEntries = (nodeCell) => {
  if (!nodeCell) {
    return []
  }

  const nodeData = nodeCell.data || nodeCell.getData?.() || {}
  const nodeConfig = ensureNodeIOConfig(nodeData.config || {})
  const nodeName = getFlowNodeName(nodeCell)
  const entries = []

  if (nodeConfig.inputAlias) {
    entries.push(buildVariableEntry({
      value: nodeConfig.inputAlias,
      sourceName: nodeName,
      sourceType: nodeData.type,
      variableType: 'inputAlias'
    }))
  }

  if (nodeConfig.outputName) {
    entries.push(buildVariableEntry({
      value: nodeConfig.outputName,
      sourceName: nodeName,
      sourceType: nodeData.type,
      variableType: 'output'
    }))
  }

  return entries.filter(Boolean)
}

const collectPageComponentVariableEntries = (pageConfig, stopComponentId = null) => {
  if (!pageConfig) {
    return []
  }

  const normalizedConfig = {
    ...pageConfig,
    innerComponents: (pageConfig.innerComponents || []).map(component => ({
      ...component,
      position: {
        ...(component.position || {})
      },
      config: {
        ...(component.config || {})
      },
      elementData: component.elementData || null
    })),
    executionPath: Array.isArray(pageConfig.executionPath)
      ? pageConfig.executionPath.map(step => ({
        ...step,
        from: step?.from ? { ...step.from } : step?.from,
        to: step?.to ? { ...step.to } : step?.to
      }))
      : []
  }

  ensurePageNodeConfig(normalizedConfig)
  normalizeInnerComponents(normalizedConfig)

  const pageName = normalizedConfig.pageName || normalizedConfig.name || '页面节点'
  const entries = []
  if (normalizedConfig.inputAlias) {
    entries.push(buildVariableEntry({
      value: normalizedConfig.inputAlias,
      sourceName: `${pageName} / 页面输入`,
      sourceType: 'page',
      variableType: 'inputAlias'
    }))
  }

  const { components = [] } = playwrightGenerator.resolvePageComponents(normalizedConfig)
  const stopIndex = stopComponentId
    ? components.findIndex(component => component.id === stopComponentId)
    : components.length
  const scopedComponents = stopIndex >= 0 ? components.slice(0, stopIndex) : components

  scopedComponents.forEach(component => {
    const outputName = component?.config?.outputName?.trim()
    if (!outputName) {
      return
    }

    entries.push(buildVariableEntry({
      value: outputName,
      sourceName: `${getFlowComponentTypeName(component.type)} / ${getFlowComponentDisplayText(component)}`,
      sourceType: component.type,
      variableType: 'output'
    }))
  })

  return entries.filter(Boolean)
}

const selectedNodeReferenceOptions = computed(() => {
  if (!selectedNode.value?.id || !graph || !flowNodeTypes.has(selectedNode.value.type)) {
    return []
  }

  const nodeMap = getGraphNodeMap()
  const executionOrder = getGraphExecutionOrder()
  const currentIndex = executionOrder.indexOf(selectedNode.value.id)
  if (currentIndex <= 0) {
    return []
  }

  const entries = executionOrder
    .slice(0, currentIndex)
    .flatMap(nodeId => collectNodeVariableEntries(nodeMap.get(nodeId)))

  return mergeVariableEntries(entries)
})

const activeInnerComponentReferenceOptions = computed(() => {
  if (selectedNode.value?.type !== 'page' || !activeInnerComponent.value) {
    return []
  }

  const upstreamNodeEntries = selectedNodeReferenceOptions.value
  const pageEntries = collectPageComponentVariableEntries(selectedNode.value.config, activeInnerComponent.value.id)
  return mergeVariableEntries([...upstreamNodeEntries, ...pageEntries])
})

const syncActiveInnerComponent = ({ keepEmpty = false } = {}) => {
  if (selectedNode.value?.type !== 'page') {
    activeInnerComponentId.value = null
    selectedInnerComponentId.value = null
    return
  }

  const components = selectedNode.value.config?.innerComponents || []
  if (!components.length) {
    activeInnerComponentId.value = null
    selectedInnerComponentId.value = null
    return
  }

  if (!components.some(component => component.id === activeInnerComponentId.value)) {
    activeInnerComponentId.value = keepEmpty ? null : components[0].id
  }

  if (selectedInnerComponentId.value && !components.some(component => component.id === selectedInnerComponentId.value)) {
    selectedInnerComponentId.value = null
  }
}

const activeInnerComponent = computed(() => {
  if (selectedNode.value?.type !== 'page') {
    return null
  }

  const components = selectedNode.value.config?.innerComponents || []
  if (!activeInnerComponentId.value) {
    return null
  }
  return components.find(component => component.id === activeInnerComponentId.value) || null
})

const flowLeftMenuItems = [
  { key: 'directory', label: '目录树' },
  { key: 'library', label: '节点组件库' }
]

const activeLeftPanelVisible = computed(() => Boolean(activeLeftPanel.value))

const activeLeftPanelTitle = computed(() => (
  flowLeftMenuItems.find(item => item.key === activeLeftPanel.value)?.label || ''
))

const toggleLeftPanel = key => {
  activeLeftPanel.value = activeLeftPanel.value === key ? '' : key
}

const collapseLeftPanel = () => {
  activeLeftPanel.value = ''
}

const flowDetailMenuItems = computed(() => [
  {
    key: 'node',
    label: '节点详情',
    disabled: !selectedNode.value || selectedNode.value.type === 'component'
  },
  {
    key: 'component',
    label: '组件详情',
    disabled: !(activeInnerComponent.value || selectedNode.value?.type === 'component')
  },
  {
    key: 'execution',
    label: '执行结果',
    disabled: !selectedExecutionResultDetail.value
  },
  {
    key: 'edge',
    label: '连线详情',
    disabled: !selectedEdge.value
  }
])

const activeDetailMenuTitle = computed(() => (
  flowDetailMenuItems.value.find(item => item.key === activeDetailMenu.value)?.label || '详情'
))

const activeDetailPanelVisible = computed(() => {
  const item = flowDetailMenuItems.value.find(menuItem => menuItem.key === activeDetailMenu.value)
  return Boolean(item && !item.disabled)
})

const setActiveDetailMenu = key => {
  const item = flowDetailMenuItems.value.find(menuItem => menuItem.key === key)
  if (!item || item.disabled) {
    return
  }
  activeDetailMenu.value = key
}

const getNodeDetailName = (node) => {
  const data = node?.getData?.() || node?.data || {}
  return data.config?.pageName || data.config?.name || data.config?.text || data.type || node?.id || ''
}

const resolveExecutionResultDetail = ({ nodeId = '', key = '', componentId = '' } = {}) => {
  if (!graph || !nodeId || !key) {
    return null
  }

  const node = graph.getCellById?.(nodeId)
  const data = node?.getData?.() || {}
  const config = data.config || {}
  const resolvedComponentId = componentId || (key !== 'node' ? key : '')
  if (resolvedComponentId) {
    const component = (config.innerComponents || []).find(item => item.id === resolvedComponentId)
    const result = component?.executionResult || null
    if (!component || !result) {
      return null
    }
    return {
      nodeId,
      key,
      componentId: resolvedComponentId,
      nodeName: getNodeDetailName(node),
      componentName: `${getComponentTypeName(component.type)} / ${getComponentDisplayText(component) || component.id}`,
      component,
      result
    }
  }

  const result = config.executionResult || null
  if (!result) {
    return null
  }
  return {
    nodeId,
    key,
    componentId: '',
    nodeName: getNodeDetailName(node),
    componentName: '',
    component: null,
    result
  }
}

const selectedExecutionResultDetail = computed(() => resolveExecutionResultDetail(selectedExecutionResultRef.value))

const inputModes = FLOW_INPUT_MODES
const variableSources = FLOW_VARIABLE_SOURCES
const assertionTargets = FLOW_ASSERTION_TARGETS
const assertionOperators = FLOW_ASSERTION_OPERATORS
const componentLibrary = COMPONENT_LIBRARY
const expandedExecutionResultKeysByNode = new Map()

const STANDARD_EDGE_ROUTER = { name: 'normal' }
const STANDARD_EDGE_CONNECTOR_NAME = 'testhub-horizontal-s'
const STANDARD_EDGE_CONNECTOR = {
  name: STANDARD_EDGE_CONNECTOR_NAME,
  args: {
    sourceOffset: 64,
    targetOffset: 72,
    minOffset: 48,
    maxOffset: 180
  }
}
const STANDARD_EDGE_MARKER = {
  name: 'classic',
  size: 9,
  offset: 1
}

const clampEdgeOffset = (value, minValue, maxValue) => Math.max(minValue, Math.min(maxValue, value))

const getConnectorSideVector = side => {
  if (side === 'left') return { x: -1, y: 0 }
  if (side === 'right') return { x: 1, y: 0 }
  if (side === 'top') return { x: 0, y: -1 }
  if (side === 'bottom') return { x: 0, y: 1 }
  return { x: 1, y: 0 }
}

const getEndpointSideFromPort = (edge, terminalType) => {
  const endpoint = terminalType === 'source'
    ? (edge?.getSource?.() || edge?.prop?.('source') || {})
    : (edge?.getTarget?.() || edge?.prop?.('target') || {})
  const portId = endpoint?.port || endpoint?.portId || ''
  const node = terminalType === 'source'
    ? edge?.getSourceNode?.()
    : edge?.getTargetNode?.()
  const port = node?.getPort?.(portId)

  if (port?.data?.side) {
    return port.data.side
  }

  const group = port?.group || ''
  if ([FLOW_PORT_GROUPS.in, 'in', 'left'].includes(group)) return 'left'
  if ([FLOW_PORT_GROUPS.out, 'out', 'right'].includes(group)) return 'right'
  if (group === 'top') return 'top'
  if (group === 'bottom') return 'bottom'

  const normalizedPortId = String(portId || '')
  if (/-left(?:-|$)|^in\d*$|^port-left$/.test(normalizedPortId)) return 'left'
  if (/-right(?:-|$)|^out\d*$|^port-right$/.test(normalizedPortId)) return 'right'
  if (/-top(?:-|$)|^port-top$/.test(normalizedPortId)) return 'top'
  if (/-bottom(?:-|$)|^port-bottom$/.test(normalizedPortId)) return 'bottom'

  return ''
}

const buildHorizontalSPath = (sourcePoint, targetPoint, options = {}) => {
  const sourceX = Number(sourcePoint?.x || 0)
  const sourceY = Number(sourcePoint?.y || 0)
  const targetX = Number(targetPoint?.x || 0)
  const targetY = Number(targetPoint?.y || 0)
  const dx = targetX - sourceX
  const dy = targetY - sourceY
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)
  const minOffset = Number(options.minOffset || 48)
  const maxOffset = Number(options.maxOffset || 180)
  const sameRow = absDy <= 18
  const sourceOffset = sameRow
    ? clampEdgeOffset(absDx * 0.42, minOffset, maxOffset)
    : clampEdgeOffset(Number(options.sourceOffset || 64), minOffset, maxOffset)
  const targetOffset = sameRow
    ? clampEdgeOffset(absDx * 0.42, minOffset, maxOffset)
    : clampEdgeOffset(Math.max(Number(options.targetOffset || 72), absDy * 0.28), minOffset, maxOffset)
  const fallbackDirection = dx >= 0 ? 1 : -1
  const sourceVector = getConnectorSideVector(options.sourceSide || (fallbackDirection >= 0 ? 'right' : 'left'))
  const targetVector = getConnectorSideVector(options.targetSide || (fallbackDirection >= 0 ? 'left' : 'right'))
  const path = new Path()
  path.appendSegment(Path.createSegment('M', sourceX, sourceY))
  path.appendSegment(Path.createSegment(
    'C',
    sourceX + sourceVector.x * sourceOffset,
    sourceY + sourceVector.y * sourceOffset,
    targetX + targetVector.x * targetOffset,
    targetY + targetVector.y * targetOffset,
    targetX,
    targetY
  ))
  return path
}

const registerFlowEdgeConnector = () => {
  try {
    Graph.registerConnector(
      STANDARD_EDGE_CONNECTOR_NAME,
      function (sourcePoint, targetPoint, routePoints = [], options = {}, edgeView) {
        if (Array.isArray(routePoints) && routePoints.length > 0) {
          const points = [sourcePoint, ...routePoints, targetPoint]
          const path = new Path()
          points.forEach((point, index) => {
            if (index === 0) {
              path.appendSegment(Path.createSegment('M', point.x || 0, point.y || 0))
            } else {
              path.appendSegment(Path.createSegment('L', point.x || 0, point.y || 0))
            }
          })
          return options.raw ? path : path.serialize()
        }

        const edge = edgeView?.cell || this?.cell
        const path = buildHorizontalSPath(sourcePoint, targetPoint, {
          ...options,
          sourceSide: getEndpointSideFromPort(edge, 'source') || options.sourceSide,
          targetSide: getEndpointSideFromPort(edge, 'target') || options.targetSide
        })
        return options.raw ? path : path.serialize()
      },
      true
    )
  } catch (error) {
    console.warn('register flow edge connector failed:', error)
  }
}

const getStandardEdgeStyle = (selected = false) => ({
  line: {
    stroke: selected ? '#f56c6c' : '#5F95FF',
    strokeWidth: selected ? 4 : 3,
    strokeOpacity: selected ? 1 : 0.95,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    sourceMarker: null,
    targetMarker: { ...STANDARD_EDGE_MARKER }
  }
})

const registerDynamicPageNodeShape = () => {
  try {
    if (typeof Graph.unregisterNode === 'function') {
      Graph.unregisterNode('page-node')
    }
  } catch (error) {
    console.warn('page-node unregister skipped:', error)
  }

  try {
    register({
      shape: 'page-node',
      width: 320,
      height: 450,
      component: PageNodeContent,
      ports: {
        groups: {
          [FLOW_PORT_GROUPS.in]: {
            position: {
              name: 'absolute'
            },
            markup: [
              {
                tagName: 'circle',
                selector: 'portBody'
              }
            ],
            attrs: {
              portBody: {
                r: 6,
                magnet: true,
                stroke: '#1d4ed8',
                fill: '#eff6ff',
                strokeWidth: 2
              }
            }
          },
          [FLOW_PORT_GROUPS.out]: {
            position: {
              name: 'absolute'
            },
            markup: [
              {
                tagName: 'circle',
                selector: 'portBody'
              }
            ],
            attrs: {
              portBody: {
                r: 6,
                magnet: true,
                stroke: '#059669',
                fill: '#ecfdf5',
                strokeWidth: 2
              }
            }
          },
          element: {
            position: {
              name: 'absolute'
            },
            markup: [
              {
                tagName: 'circle',
                selector: 'portBody'
              }
            ],
            attrs: {
              portBody: {
                r: 6,
                magnet: true,
                stroke: '#faad14',
                fill: '#fff',
                strokeWidth: 2
              }
            }
          }
        }
      }
    })
  } catch (error) {
    console.error('registerDynamicPageNodeShape failed:', error)
  }
}

const isEnhancedPageFlowEdge = (sourceNode, targetNode, sourcePort, targetPort) => {
  if (!sourceNode || !targetNode || !sourcePort || !targetPort) {
    return false
  }

  return sourceNode.id === targetNode.id && sourceNode.getData()?.type === 'page'
}

const getFlowPortLabel = (portData) => {
  if (!portData) {
    return ''
  }

  const sideLabelMap = {
    left: '左侧',
    top: '顶部',
    right: '右侧',
    bottom: '底部'
  }
  const sideLabel = sideLabelMap[portData.side] || '端口'

  if (portData.scopeType === 'page') {
    return `页面${sideLabel}`
  }

  if (portData.scopeType === 'iframe') {
    return `${portData.elementText || 'iframe'}${sideLabel}`
  }

  return portData.elementText || portData.componentType || '组件'
}

const buildEnhancedExecutionEndpoint = (portId, portData) => ({
  portId,
  scopeType: portData.scopeType,
  scopeId: portData.scopeId,
  wall: portData.wall,
  side: portData.side,
  direction: portData.direction,
  componentId: portData.componentId || null,
  componentType: portData.componentType || portData.scopeType,
  elementId: portData.elementId || null,
  elementType: portData.elementType || portData.componentType || portData.scopeType,
  elementText: portData.elementText || getFlowPortLabel(portData),
  parentId: portData.parentId || null
})

const getNormalizedExecutionConnection = (node, sourcePort, targetPort) => {
  const sourcePortConfig = node?.getPort(sourcePort)
  const targetPortConfig = node?.getPort(targetPort)
  const sourcePortData = sourcePortConfig?.data
  const targetPortData = targetPortConfig?.data
  if (!sourcePortData || !targetPortData) {
    return null
  }

  const normalizedPorts = normalizeExecutionConnectionPorts(sourcePortConfig, targetPortConfig)
  if (!normalizedPorts.sourcePort || !normalizedPorts.targetPort) {
    return null
  }

  return {
    sourcePortId: normalizedPorts.reversed ? targetPort : sourcePort,
    targetPortId: normalizedPorts.reversed ? sourcePort : targetPort,
    sourcePortData: normalizedPorts.sourcePort.data,
    targetPortData: normalizedPorts.targetPort.data,
    reversed: normalizedPorts.reversed
  }
}

const upsertEnhancedExecutionPath = (node, sourcePort, targetPort) => {
  if (!node || node.getData()?.type !== 'page') {
    return
  }

  const data = node.getData()
  ensurePageNodeConfig(data.config)

  const normalizedConnection = getNormalizedExecutionConnection(node, sourcePort, targetPort)
  if (!normalizedConnection) {
    return
  }
  const { sourcePortId, targetPortId, sourcePortData, targetPortData } = normalizedConnection

  const existingStep = data.config.executionPath.find(
    step =>
      (step?.from?.portId === sourcePortId && step?.to?.portId === targetPortId) ||
      (step?.from?.portId === targetPortId && step?.to?.portId === sourcePortId)
  )

  data.config.executionPath = data.config.executionPath.filter(
    step =>
      !(step?.from?.portId === sourcePortId && step?.to?.portId === targetPortId) &&
      !(step?.from?.portId === targetPortId && step?.to?.portId === sourcePortId)
  )

  data.config.executionPath.push({
    from: buildEnhancedExecutionEndpoint(sourcePortId, sourcePortData),
    to: buildEnhancedExecutionEndpoint(targetPortId, targetPortData),
    action: existingStep?.action || sourcePortData.action || 'next',
    value: existingStep?.value || '',
    createdAt: existingStep?.createdAt || Date.now()
  })

  node.setData(data, { overwrite: true })

  if (selectedNode.value?.id === node.id) {
    selectedNode.value.config = data.config
  }
}

const removeEnhancedExecutionPath = (node, sourcePort, targetPort) => {
  if (!node || node.getData()?.type !== 'page') {
    return
  }

  const data = node.getData()
  if (!Array.isArray(data?.config?.executionPath)) {
    return
  }

  data.config.executionPath = data.config.executionPath.filter(
    step =>
      !(step?.from?.portId === sourcePort && step?.to?.portId === targetPort) &&
      !(step?.from?.portId === targetPort && step?.to?.portId === sourcePort)
  )

  node.setData(data, { overwrite: true })
  if (selectedNode.value?.id === node.id) {
    selectedNode.value.config = data.config
  }
}

const getEnhancedEdgeLabel = (node, sourcePort, targetPort) => {
  if (!node) {
    return ''
  }

  const normalizedConnection = getNormalizedExecutionConnection(node, sourcePort, targetPort)
  if (!normalizedConnection) {
    return ''
  }
  const { sourcePortData, targetPortData } = normalizedConnection

  if (sourcePortData.componentId && targetPortData.componentId) {
    return sourcePortData.action || 'next'
  }

  return `${getFlowPortLabel(sourcePortData)} -> ${getFlowPortLabel(targetPortData)}`
}

const getDynamicPortAttrs = (port) => {
  const isInput = port.group === FLOW_PORT_GROUPS.in
  const isPage = port.data?.scopeType === 'page'
  const isIframe = port.data?.scopeType === 'iframe'
  const stroke = isPage
    ? (isInput ? '#1d4ed8' : '#059669')
    : isIframe
      ? (isInput ? '#d97706' : '#b45309')
      : (isInput ? '#0f766e' : '#15803d')
  const fill = isInput ? '#ffffff' : '#f0fdf4'

  return {
    portBody: {
      r: isIframe ? 6 : 5,
      magnet: true,
      stroke,
      fill,
      strokeWidth: 2
    }
  }
}

const syncPageNodePorts = (node) => {
  if (!node || node.getData()?.type !== 'page') {
    return
  }

  const data = node.getData()
  ensurePageNodeConfig(data.config)
  normalizeInnerComponents(data.config)

  const components = data.config.innerComponents || []
  const { ports } = buildPageNodePorts(node.getSize(), components)
  const nextPorts = ports.map(port => ({
    ...port,
    attrs: {
      ...(port.attrs || {}),
      ...getDynamicPortAttrs(port)
    }
  }))
  const validPortIds = new Set()
  const validComponentIds = new Set(components.map(component => component.id))

  nextPorts.forEach(port => {
    validPortIds.add(port.id)
  })
  node.setPropByPath?.('ports/items', nextPorts, { rewrite: true })

  if (Array.isArray(data.config.executionPath)) {
    const portMap = new Map(nextPorts.map(port => [port.id, port]))
    const buildEndpointFromPort = (endpoint = {}, port) => ({
      ...endpoint,
      ...buildEnhancedExecutionEndpoint(port.id, port.data)
    })

    data.config.executionPath = data.config.executionPath.map(step => {
      const sourcePortId = normalizeIframePortId(step?.from?.portId, components)
      const targetPortId = normalizeIframePortId(step?.to?.portId, components)
      const sourcePort = portMap.get(sourcePortId)
      const targetPort = portMap.get(targetPortId)
      if (!sourcePort || !targetPort) {
        return {
          ...step,
          from: {
            ...(step?.from || {}),
            portId: sourcePortId
          },
          to: {
            ...(step?.to || {}),
            portId: targetPortId
          }
        }
      }

      const normalizedPorts = normalizeExecutionConnectionPorts(sourcePort, targetPort)
      return {
        ...step,
        from: buildEndpointFromPort(normalizedPorts.reversed ? step?.to : step?.from, normalizedPorts.sourcePort),
        to: buildEndpointFromPort(normalizedPorts.reversed ? step?.from : step?.to, normalizedPorts.targetPort)
      }
    }).filter(step => {
      const fromPortValid = validPortIds.has(step?.from?.portId)
      const toPortValid = validPortIds.has(step?.to?.portId)
      const fromComponentValid = !step?.from?.componentId || validComponentIds.has(step.from.componentId)
      const toComponentValid = !step?.to?.componentId || validComponentIds.has(step.to.componentId)
      return fromPortValid && toPortValid && fromComponentValid && toComponentValid
    })
  }

  node.setData(data, { overwrite: true })
  if (selectedNode.value?.id === node.id) {
    selectedNode.value.config = data.config
  }
}

const getRouteFlowId = () => {
  const rawFlowId = route.query.flow_id
  return Array.isArray(rawFlowId) ? rawFlowId[0] : (rawFlowId || '')
}

const getRouteRecordingSessionId = () => {
  const rawSessionId = route.query.recording_session_id || route.query.session_id
  return Array.isArray(rawSessionId) ? rawSessionId[0] : (rawSessionId || '')
}

const normalizeFlowGraphData = (graphData) => {
  if (graphData && Array.isArray(graphData.cells)) {
    return graphData
  }
  return { cells: [] }
}

const cloneFlowCellData = (cell) => JSON.parse(JSON.stringify(cell || {}))

const splitFlowGraphCells = (graphData) => {
  const normalizedGraphData = normalizeFlowGraphData(graphData)
  const cells = normalizedGraphData.cells || []
  return {
    nodes: cells.filter(cell => cell?.shape !== 'edge'),
    edges: cells.filter(cell => cell?.shape === 'edge')
  }
}

const getFlowMetadataStepSignature = flow => {
  const metadata = flow?.metadata || {}
  const summary = flow?.snapshot_summary || {}
  return [
    metadata.recording_status || '',
    metadata.recording_step_count ?? summary.total_step_count ?? 0,
    metadata.recording_flow_step_count ?? summary.flow_step_count ?? 0,
    metadata.recording_filtered_step_count ?? summary.filtered_step_count ?? 0,
    flow?.updated_at || ''
  ].join(':')
}

const getRecordingFlowStepSignature = payload => {
  const session = payload?.session || {}
  const flow = payload?.flow || {}
  const summary = flow.snapshot_summary || {}
  return [
    session.status || '',
    Array.isArray(payload?.steps) ? payload.steps.length : summary.total_step_count || 0,
    summary.flow_step_count || 0,
    summary.filtered_step_count || 0
  ].join(':')
}

const isRecordingFlowStatusActive = status => ['starting', 'recording', 'stopping'].includes(String(status || ''))

const getVisualFlowRecordingStatus = flow => (
  flow?.metadata?.recording_status ||
  flow?.recording_session?.status ||
  ''
)

const getPageRecordingIdentity = (pageNodeOrConfig) => {
  const data = typeof pageNodeOrConfig?.getData === 'function'
    ? pageNodeOrConfig.getData()
    : null
  const config = data?.config || pageNodeOrConfig?.config || pageNodeOrConfig || {}
  return String(config.recordingPageIdentity || config.recordingPagePath || config.pageName || config.name || '').trim()
}

const getPageNodeRightX = node => {
  if (!node) return 320
  const position = node.getPosition?.() || { x: 0, y: 0 }
  const size = node.getSize?.() || { width: 0, height: 0 }
  return (position.x || 0) + (size.width || 0)
}

const getAppendBasePageNode = () => {
  const state = continueRecordingMergeState.value
  const appendAfter = graph?.getCellById?.(state.appendAfterNodeId)
  if (appendAfter?.getData?.()?.type === 'page') {
    return appendAfter
  }
  const anchorNode = graph?.getCellById?.(continueRecordingAnchor.value?.nodeId)
  if (anchorNode?.getData?.()?.type === 'page') {
    return anchorNode
  }
  return getGraphPageNodes().sort((left, right) => getPageNodeRightX(right) - getPageNodeRightX(left))[0]
    || null
}

const buildContinuationNodePosition = (baseNode, index = 0, nodeSize = {}) => {
  if (baseNode) {
    const position = baseNode.getPosition?.() || { x: 320, y: 80 }
    const size = baseNode.getSize?.() || { width: 420, height: 450 }
    return {
      x: (position.x || 0) + (size.width || 420) + 180 + index * ((nodeSize.width || 420) + 180),
      y: position.y || 80
    }
  }

  const pageNodes = getGraphPageNodes()
  if (!pageNodes.length) {
    return { x: 320, y: 80 }
  }

  const maxRightNode = pageNodes.sort((left, right) => getPageNodeRightX(right) - getPageNodeRightX(left))[0]
  const position = maxRightNode.getPosition?.() || { x: 320, y: 80 }
  return {
    x: getPageNodeRightX(maxRightNode) + 180 + index * ((nodeSize.width || 420) + 180),
    y: position.y || 80
  }
}

const buildComponentGrid = total => {
  const count = Math.max(Number(total) || 0, 1)
  const columns = Math.min(count, FLOW_COMPONENT_GRID.maxColumns)
  const rows = Math.max(1, Math.ceil(count / columns))
  return { columns, rows }
}

const buildContinuationColumnX = (columnIndex, columnCount, xMin = CONTINUATION_COMPONENT_LAYOUT.xMin, xMax = CONTINUATION_COMPONENT_LAYOUT.xMax) => {
  const count = Math.max(Number(columnCount) || 1, 1)
  if (count === 1) {
    return clampPosition((xMin + xMax) / 2, xMin, xMax)
  }
  const step = (xMax - xMin) / (count - 1)
  return clampPosition(xMin + step * columnIndex, xMin, xMax)
}

const normalizeComponentLayoutY = component => clampPosition(
  component?.position?.y ?? CONTINUATION_COMPONENT_LAYOUT.defaultY,
  CONTINUATION_COMPONENT_LAYOUT.yMin,
  CONTINUATION_COMPONENT_LAYOUT.yMax
)

const buildContinuationRowCandidates = (rowCount, preferredStart) => {
  const layout = CONTINUATION_COMPONENT_LAYOUT
  const rows = Math.max(Number(rowCount) || 1, 1)
  const maxStart = layout.yMax - (rows - 1) * layout.rowGap
  const minStart = layout.yMin
  const candidates = []
  const addCandidate = value => {
    const normalized = clampPosition(value, minStart, Math.max(minStart, maxStart))
    if (!candidates.some(candidate => Math.abs(candidate - normalized) < 1)) {
      candidates.push(normalized)
    }
  }

  addCandidate(preferredStart)
  addCandidate(layout.defaultY)
  for (let value = minStart; value <= maxStart; value += layout.rowGap) {
    addCandidate(value)
  }
  for (let value = maxStart; value >= minStart; value -= layout.rowGap) {
    addCandidate(value)
  }
  return candidates
}

const scoreContinuationRows = (rowStart, rowCount, existingRows = []) => {
  const layout = CONTINUATION_COMPONENT_LAYOUT
  let score = 0
  for (let index = 0; index < rowCount; index += 1) {
    const rowY = rowStart + index * layout.rowGap
    existingRows.forEach(existingY => {
      const distance = Math.abs(rowY - existingY)
      if (distance < layout.minExistingRowGap) {
        score += (layout.minExistingRowGap - distance) * 100
      } else {
        score += Math.max(0, layout.rowGap - distance)
      }
    })
  }
  return score
}

const buildContinuationRowYs = (existingComponents = [], rowCount = 1) => {
  const layout = CONTINUATION_COMPONENT_LAYOUT
  const rows = Math.max(Number(rowCount) || 1, 1)
  const existingRows = existingComponents
    .map(normalizeComponentLayoutY)
    .filter(value => Number.isFinite(value))
  const preferredStart = existingRows.length
    ? Math.max(...existingRows) + layout.rowGap
    : layout.defaultY - ((rows - 1) * layout.rowGap) / 2
  const candidates = buildContinuationRowCandidates(rows, preferredStart)
  const selectedStart = candidates
    .map(start => ({
      start,
      score: scoreContinuationRows(start, rows, existingRows),
      distance: Math.abs(start - preferredStart)
    }))
    .sort((left, right) => left.score - right.score || left.distance - right.distance)[0]?.start ?? layout.defaultY

  return Array.from({ length: rows }, (_, index) => clampPosition(
    selectedStart + index * layout.rowGap,
    layout.yMin,
    layout.yMax
  ))
}

const layoutContinuationComponentGroup = (existingComponents = [], newComponents = [], bounds = {}) => {
  if (!newComponents.length) {
    return
  }

  const xMin = bounds.xMin ?? CONTINUATION_COMPONENT_LAYOUT.xMin
  const xMax = bounds.xMax ?? CONTINUATION_COMPONENT_LAYOUT.xMax
  const columns = Math.min(newComponents.length, FLOW_COMPONENT_GRID.maxColumns)
  const rowCount = Math.max(1, Math.ceil(newComponents.length / columns))
  const rowYs = buildContinuationRowYs(existingComponents, rowCount)

  newComponents.forEach((component, index) => {
    const rowIndex = Math.floor(index / columns)
    const rowStartIndex = rowIndex * columns
    const rowItemCount = Math.min(columns, newComponents.length - rowStartIndex)
    const columnIndex = index - rowStartIndex
    component.position = {
      x: buildContinuationColumnX(columnIndex, rowItemCount, xMin, xMax),
      y: rowYs[rowIndex] ?? CONTINUATION_COMPONENT_LAYOUT.defaultY
    }
  })
}

const buildContinuationIframeSize = totalComponents => {
  const { columns, rows } = buildComponentGrid(totalComponents)
  return {
    width: Math.max(260, 24 + columns * 300),
    height: Math.max(220, 54 + rows * 230)
  }
}

const normalizeComponentMergeText = value => String(value ?? '')
  .trim()
  .replace(/\s+/g, ' ')
  .toLowerCase()

const normalizeComponentSelectorForMerge = value => {
  const normalized = normalizeComponentMergeText(value)
    .replace(/el-id-\d+-\d+/g, 'el-id')
    .replace(/recorded[_-]step[_-]?\d+/g, 'recorded-step')
    .replace(/recorded_component_\d+/g, 'recorded-component')
  return normalized && !normalized.includes('recorded-step') ? normalized : ''
}

const getComponentActionValue = component => {
  const config = component?.config || {}
  return String(config.value ?? config.inputValue ?? config.selectedValue ?? config.checked ?? '').trim()
}

const getComponentMergeAction = component => {
  const action = normalizeComponentMergeText(component?.config?.action || component?.config?.recordingActionType || '')
  if (component?.type === 'input' && ['fill', 'press', 'input'].includes(action)) {
    return 'fill'
  }
  if (component?.type === 'select') {
    return 'select'
  }
  if (['checkbox', 'radio'].includes(component?.type)) {
    return 'check'
  }
  return action || getDefaultComponentAction(component?.type)
}

const buildComponentElementMergeKey = component => {
  const elementData = component?.elementData || {}
  const attributes = elementData.attributes || {}
  const selectors = Array.isArray(elementData.selectors) ? elementData.selectors : []
  const stableSelectors = selectors
    .map(selector => normalizeComponentSelectorForMerge(selector?.value))
    .filter(Boolean)
    .filter(value => !/^#?el-id(?:$|[^a-z0-9_-])/i.test(value))
    .slice(0, 4)
  const stableParts = [
    component?.type || '',
    attributes.placeholder,
    attributes.name,
    attributes['aria-label'] || attributes.ariaLabel,
    attributes.title,
    elementData.text,
    attributes.role,
    attributes.tag,
    attributes.type,
    normalizeComponentMergeText(attributes.class || '').split(' ').filter(Boolean).slice(0, 2).join('.'),
    ...stableSelectors
  ].map(normalizeComponentMergeText).filter(Boolean)

  if (stableParts.length) {
    return stableParts.join('::')
  }

  return [
    component?.type || '',
    component?.elementId || '',
    elementData.ref || ''
  ].map(normalizeComponentMergeText).filter(Boolean).join('::')
}

const isComponentEquivalentForMerge = (left, right) => {
  if (!left || !right || left.type !== right.type) {
    return false
  }
  if ((left.parentId || '') !== (right.parentId || '')) {
    return false
  }

  const leftKey = buildComponentElementMergeKey(left)
  const rightKey = buildComponentElementMergeKey(right)
  if (!leftKey || !rightKey || leftKey !== rightKey) {
    return false
  }

  const leftAction = getComponentMergeAction(left)
  const rightAction = getComponentMergeAction(right)
  if (leftAction !== rightAction) {
    return false
  }

  if (left.type === 'input') {
    return true
  }
  return getComponentActionValue(left) === getComponentActionValue(right)
}

const mergeEquivalentComponentConfig = (target, source) => {
  if (!target || !source) {
    return false
  }

  const before = JSON.stringify({
    config: target.config,
    elementData: target.elementData,
    elementId: target.elementId
  })
  target.config = {
    ...(target.config || {}),
    ...(source.config || {})
  }
  if (source.elementData) {
    target.elementData = {
      ...(target.elementData || {}),
      ...source.elementData,
      attributes: {
        ...((target.elementData || {}).attributes || {}),
        ...(source.elementData.attributes || {})
      },
      selectors: source.elementData.selectors || target.elementData?.selectors || []
    }
  }
  target.elementId = target.elementId || source.elementId
  return before !== JSON.stringify({
    config: target.config,
    elementData: target.elementData,
    elementId: target.elementId
  })
}

const findEquivalentExistingComponent = (component, existingComponents = [], { adjacentOnly = false } = {}) => {
  if (!component) {
    return null
  }

  const candidates = adjacentOnly
    ? existingComponents.slice(-1)
    : [...existingComponents].reverse()
  return candidates.find(existing => isComponentEquivalentForMerge(component, existing)) || null
}

const applyContinuationComponentLayout = (existingComponents = [], newComponents = []) => {
  if (!newComponents.length) {
    return
  }

  const anchor = continueRecordingAnchor.value || {}
  const anchorComponent = anchor.componentId
    ? existingComponents.find(component => component.id === anchor.componentId)
    : null
  const insertAfterAnchor = Boolean(anchorComponent)
  const anchorOrder = Number(anchorComponent?.order ?? anchorComponent?.zIndex ?? -1)
  const insertionOrder = insertAfterAnchor
    ? anchorOrder + 1
    : getNextComponentOrderBase(existingComponents)

  if (insertAfterAnchor) {
    existingComponents.forEach(component => {
      const order = Number(component.order ?? component.zIndex ?? 0)
      if (order >= insertionOrder) {
        component.order = order + newComponents.length
        component.zIndex = Number(component.zIndex ?? order) + newComponents.length
      }
    })
  }

  newComponents.forEach((component, index) => {
    const order = insertionOrder + index
    component.order = order
    component.zIndex = order
  })

  const rootExisting = existingComponents.filter(component => !component.parentId)
  const rootNew = newComponents.filter(component => !component.parentId)
  layoutContinuationComponentGroup(rootExisting, rootNew)

  const allComponents = [...existingComponents, ...newComponents]
  const parentIds = new Set(newComponents.map(component => component.parentId).filter(Boolean))
  parentIds.forEach(parentId => {
    const existingChildren = existingComponents.filter(component => component.parentId === parentId)
    const newChildren = newComponents.filter(component => component.parentId === parentId)
    const total = existingChildren.length + newChildren.length
    layoutContinuationComponentGroup(existingChildren, newChildren, {
      xMin: 12,
      xMax: 88
    })
    const parentComponent = allComponents.find(component => component.id === parentId)
    if (parentComponent?.type === 'iframe') {
      const nextSize = buildContinuationIframeSize(total)
      const currentSize = getComponentSize(parentComponent)
      parentComponent.size = {
        width: Math.max(currentSize.width, nextSize.width),
        height: Math.max(currentSize.height, nextSize.height)
      }
    }
  })
}

const estimatePageNodeSizeForComponents = (components = []) => {
  const rootComponents = components.filter(component => !component.parentId)
  const total = Math.max(rootComponents.length || components.length || 1, 1)
  const { columns, rows } = buildComponentGrid(total)
  const maxComponentWidth = Math.max(...rootComponents.map(component => getComponentSize(component).width), 150)
  const maxComponentHeight = Math.max(...rootComponents.map(component => getComponentSize(component).height), 82)
  const cellWidth = Math.max(FLOW_COMPONENT_GRID.cellWidth, maxComponentWidth + 88)
  const cellHeight = Math.max(FLOW_COMPONENT_GRID.cellHeight, maxComponentHeight + 80)
  return {
    width: Math.max(FLOW_COMPONENT_GRID.minWidth, PAGE_NODE_LAYOUT.paddingX * 2 + columns * cellWidth),
    height: Math.max(
      FLOW_COMPONENT_GRID.minHeight,
      PAGE_NODE_LAYOUT.headerHeight + PAGE_NODE_LAYOUT.footerHeight + PAGE_NODE_LAYOUT.paddingY * 2 + rows * cellHeight
    )
  }
}

const remapPortIdForContinuation = (portId = '', componentIdMap = {}) => {
  let nextPortId = String(portId || '')
  Object.entries(componentIdMap).forEach(([oldId, newId]) => {
    nextPortId = nextPortId.replaceAll(oldId, newId)
  })
  return nextPortId
}

const remapExecutionEndpointForContinuation = (endpoint = {}, componentIdMap = {}) => {
  const oldComponentId = endpoint?.componentId || ''
  const newComponentId = oldComponentId ? (componentIdMap[oldComponentId] || oldComponentId) : oldComponentId
  return {
    ...endpoint,
    portId: remapPortIdForContinuation(endpoint?.portId || '', componentIdMap),
    componentId: newComponentId,
    scopeId: endpoint?.scopeId && componentIdMap[endpoint.scopeId] ? componentIdMap[endpoint.scopeId] : endpoint?.scopeId
  }
}

const remapExecutionPathForContinuation = (executionPath = [], componentIdMap = {}) => {
  if (!Array.isArray(executionPath)) {
    return []
  }

  return executionPath.map(step => ({
    ...step,
    from: remapExecutionEndpointForContinuation(step?.from || {}, componentIdMap),
    to: remapExecutionEndpointForContinuation(step?.to || {}, componentIdMap)
  }))
}

const buildComponentExecutionEndpoint = (component, direction = 'out') => {
  if (!component) {
    return null
  }

  const suffix = direction === 'out' ? 'right-out' : 'left-in'
  const isIframe = component.type === 'iframe'

  return {
    portId: isIframe ? buildIframeSharedPortId(component.id, suffix) : `component-${component.id}-${suffix}`,
    scopeType: isIframe ? 'iframe' : 'component',
    scopeId: component.id,
    wall: isIframe ? 'shared' : 'component',
    side: direction === 'out' ? 'right' : 'left',
    direction,
    componentId: component.id,
    componentType: component.type,
    elementId: component.elementId || null,
    elementType: component.elementData?.type || component.type,
    elementText: getComponentDisplayText(component),
    parentId: component.parentId || null
  }
}

const buildPageExecutionEndpoint = (direction = 'out') => ({
  portId: direction === 'out' ? 'page-right-out' : 'page-left-in',
  scopeType: 'page',
  scopeId: 'page',
  wall: 'shared',
  side: direction === 'out' ? 'right' : 'left',
  direction,
  componentId: null,
  componentType: 'page',
  elementId: null,
  elementType: 'page',
  elementText: 'page',
  parentId: null
})

const getFirstActionableComponent = (components = []) => [...components]
  .filter(component => component?.type && component.type !== 'iframe' && component.elementId)
  .sort((left, right) => (left.order ?? left.zIndex ?? 0) - (right.order ?? right.zIndex ?? 0))[0] || null

const getLastActionableComponent = (components = []) => [...components]
  .filter(component => component?.type && component.type !== 'iframe' && component.elementId)
  .sort((left, right) => (left.order ?? left.zIndex ?? 0) - (right.order ?? right.zIndex ?? 0))
  .slice(-1)[0] || null

const resolveContinuationPageAnchorComponent = (pageConfig, pageNodeId = '') => {
  const state = continueRecordingMergeState.value || {}
  const anchor = continueRecordingAnchor.value || {}
  const components = pageConfig?.innerComponents || []
  const lastComponentId = state.lastComponentByPageId?.[pageNodeId] || state.lastComponentByPageId?.[anchor.nodeId] || ''
  const lastComponent = lastComponentId
    ? components.find(component => component.id === lastComponentId)
    : null
  if (lastComponent) {
    return lastComponent
  }
  return anchor.componentId
    ? components.find(component => component.id === anchor.componentId) || null
    : null
}

const ensureContinuationBranchExecutionPath = (pageConfig, newComponents = [], pageNodeId = '') => {
  if (!pageConfig || !Array.isArray(pageConfig.innerComponents) || !newComponents.length) {
    return null
  }

  const anchorComponent = resolveContinuationPageAnchorComponent(pageConfig, pageNodeId)
  const firstNewComponent = getFirstActionableComponent(newComponents)
  if (!firstNewComponent) {
    return null
  }

  const existingPath = Array.isArray(pageConfig.executionPath) ? pageConfig.executionPath : []
  const appendStep = (from, to, action = 'next', value = '') => {
    if (!from?.portId || !to?.portId) {
      return
    }
    const exists = existingPath.some(step =>
      step?.from?.portId === from.portId &&
      step?.to?.portId === to.portId
    )
    if (exists) {
      return
    }
    existingPath.push({
      from,
      to,
      action,
      value,
      createdAt: Date.now()
    })
  }

  if (anchorComponent) {
    const anchorOutPortId = buildComponentExecutionEndpoint(anchorComponent, 'out').portId
    existingPath.splice(0, existingPath.length, ...existingPath.filter(step => !(
      step?.from?.portId === anchorOutPortId &&
      step?.to?.portId === 'page-right-out'
    )))
    appendStep(
      buildComponentExecutionEndpoint(anchorComponent, 'out'),
      buildComponentExecutionEndpoint(firstNewComponent, 'in'),
      anchorComponent.config?.action || 'branch',
      anchorComponent.config?.inputValue || anchorComponent.config?.value || ''
    )
  } else if (!existingPath.length) {
    appendStep(
      buildPageExecutionEndpoint('in'),
      buildComponentExecutionEndpoint(firstNewComponent, 'in'),
      'enter'
    )
  }

  const actionableNewComponents = [...newComponents]
    .filter(component => component?.type && component.type !== 'iframe' && component.elementId)
    .sort((left, right) => (left.order ?? left.zIndex ?? 0) - (right.order ?? right.zIndex ?? 0))

  actionableNewComponents.slice(1).forEach((component, index) => {
    const previous = actionableNewComponents[index]
    appendStep(
      buildComponentExecutionEndpoint(previous, 'out'),
      buildComponentExecutionEndpoint(component, 'in'),
      previous.config?.action || 'next',
      previous.config?.inputValue || previous.config?.value || ''
    )
  })

  const lastNewComponent = actionableNewComponents[actionableNewComponents.length - 1]
  if (lastNewComponent) {
    appendStep(
      buildComponentExecutionEndpoint(lastNewComponent, 'out'),
      buildPageExecutionEndpoint('out'),
      lastNewComponent.config?.action || 'exit',
      lastNewComponent.config?.inputValue || lastNewComponent.config?.value || ''
    )
  }

  pageConfig.executionPath = existingPath
  return lastNewComponent || firstNewComponent
}

const cloneContinuationPageConfig = (sourceConfig = {}, sessionId = '') => {
  const idPrefix = `continue_${sessionId || Date.now()}`
  const componentIdMap = {}
  const components = (sourceConfig.innerComponents || []).map(component => {
    const nextId = `${idPrefix}_${component.id}`
    componentIdMap[component.id] = nextId
    return {
      ...cloneFlowCellData(component),
      id: nextId
    }
  }).map(component => ({
    ...component,
    parentId: component.parentId ? (componentIdMap[component.parentId] || component.parentId) : null
  }))
  applyContinuationComponentLayout([], components)

  return {
    config: {
      ...cloneFlowCellData(sourceConfig),
      innerComponents: components,
      executionPath: remapExecutionPathForContinuation(sourceConfig.executionPath || [], componentIdMap)
    },
    componentIdMap
  }
}

const getNextComponentOrderBase = (components = []) => {
  if (!components.length) {
    return 0
  }
  return Math.max(...components.map(component => Number(component.order ?? component.zIndex ?? 0))) + 1
}

const buildSequentialExecutionPath = (components = []) => {
  const actionable = components
    .filter(component => component?.type && component.type !== 'iframe' && component.elementId)
    .sort((left, right) => (left.order ?? left.zIndex ?? 0) - (right.order ?? right.zIndex ?? 0))

  if (!actionable.length) {
    return []
  }

  const buildEndpoint = (portId, component, direction) => {
    if (!component) {
      return {
        portId,
        scopeType: 'page',
        scopeId: 'page',
        wall: 'shared',
        side: direction === 'out' ? 'right' : 'left',
        direction,
        componentId: null,
        componentType: 'page',
        elementId: null,
        elementType: 'page',
        elementText: 'page',
        parentId: null
      }
    }

    return {
      portId,
      scopeType: component.type === 'iframe' ? 'iframe' : 'component',
      scopeId: component.id,
      wall: 'component',
      side: direction === 'out' ? 'right' : 'left',
      direction,
      componentId: component.id,
      componentType: component.type,
      elementId: component.elementId,
      elementType: component.elementData?.type || component.type,
      elementText: getComponentDisplayText(component),
      parentId: component.parentId || null
    }
  }

  const path = [{
    from: buildEndpoint('page-left-in', null, 'in'),
    to: buildEndpoint(`component-${actionable[0].id}-left-in`, actionable[0], 'in'),
    action: 'enter',
    value: '',
    createdAt: Date.now()
  }]

  actionable.slice(1).forEach((component, index) => {
    const previous = actionable[index]
    path.push({
      from: buildEndpoint(`component-${previous.id}-right-out`, previous, 'out'),
      to: buildEndpoint(`component-${component.id}-left-in`, component, 'in'),
      action: previous.config?.action || 'next',
      value: previous.config?.inputValue || previous.config?.value || '',
      createdAt: Date.now()
    })
  })

  const lastComponent = actionable[actionable.length - 1]
  path.push({
    from: buildEndpoint(`component-${lastComponent.id}-right-out`, lastComponent, 'out'),
    to: buildEndpoint('page-right-out', null, 'out'),
    action: lastComponent.config?.action || 'exit',
    value: lastComponent.config?.inputValue || lastComponent.config?.value || '',
    createdAt: Date.now()
  })

  return path
}

const appendComponentsToExistingPageNode = (targetPageNode, sourcePageCell, sessionId = '') => {
  if (!targetPageNode || !sourcePageCell?.data?.config) {
    return false
  }

  const sourceConfig = sourcePageCell.data.config
  const sourceComponents = sourceConfig.innerComponents || []
  if (!sourceComponents.length) {
    return false
  }
  const state = continueRecordingMergeState.value
  const globalMergedComponentMap = { ...(state.mergedComponentMap || {}) }

  const targetData = targetPageNode.getData()
  ensurePageNodeConfig(targetData.config)
  normalizeInnerComponents(targetData.config)

  const existingComponents = targetData.config.innerComponents || []
  const idPrefix = `continue_${sessionId || Date.now()}_${sourcePageCell.id}`
  const componentIdMap = {}
  const copiedComponents = []
  const workingComponents = [...existingComponents]
  let updatedEquivalent = false

  sourceComponents.forEach(component => {
    if (globalMergedComponentMap[component.id]) {
      componentIdMap[component.id] = globalMergedComponentMap[component.id]
      return
    }
    const equivalent = findEquivalentExistingComponent(component, workingComponents, {
      adjacentOnly: component.type !== 'iframe'
    })
    if (equivalent) {
      updatedEquivalent = mergeEquivalentComponentConfig(equivalent, component) || updatedEquivalent
      componentIdMap[component.id] = equivalent.id
      globalMergedComponentMap[component.id] = equivalent.id
      return
    }
    const nextId = `${idPrefix}_${component.id}`
    componentIdMap[component.id] = nextId
    globalMergedComponentMap[component.id] = nextId
    const copiedComponent = {
      ...cloneFlowCellData(component),
      id: nextId
    }
    copiedComponents.push(copiedComponent)
    workingComponents.push(copiedComponent)
  })

  const mappedComponents = copiedComponents.map(component => ({
    ...component,
    parentId: component.parentId ? (componentIdMap[component.parentId] || component.parentId) : null
  }))

  applyContinuationComponentLayout(existingComponents, mappedComponents)

  if (!mappedComponents.length && !updatedEquivalent) {
    continueRecordingMergeState.value = {
      ...state,
      mergedComponentMap: globalMergedComponentMap
    }
    return false
  }

  const existingExecutionPath = Array.isArray(targetData.config.executionPath) && targetData.config.executionPath.length
    ? targetData.config.executionPath
    : buildSequentialExecutionPath(existingComponents)

  targetData.config.innerComponents = [...existingComponents, ...mappedComponents]
  targetData.config.snapshotFile = targetData.config.snapshotFile || sourceConfig.snapshotFile || null
  targetData.config.snapshotData = targetData.config.snapshotData || sourceConfig.snapshotData || null
  targetData.config.recordingPageIdentity = targetData.config.recordingPageIdentity || sourceConfig.recordingPageIdentity || ''
  targetData.config.recordingPagePath = targetData.config.recordingPagePath || sourceConfig.recordingPagePath || ''
  targetData.config.executionPath = existingExecutionPath
  const lastAppendedComponent = ensureContinuationBranchExecutionPath(targetData.config, mappedComponents, targetPageNode.id)

  const nextSize = estimatePageNodeSizeForComponents(targetData.config.innerComponents)
  targetPageNode.resize(
    Math.max(targetPageNode.getSize?.().width || 0, nextSize.width),
    Math.max(targetPageNode.getSize?.().height || 0, nextSize.height)
  )
  const nextData = buildPageNodeDataPayload(targetData)
  targetPageNode.setData(nextData, { overwrite: true })
  syncPageNodePorts(targetPageNode)
  refreshPageNodeView(targetPageNode, { syncPorts: false, delay: 80 })
  if (selectedNode.value?.id === targetPageNode.id) {
    selectedNode.value.config = nextData.config
  }
  continueRecordingMergeState.value = {
    ...continueRecordingMergeState.value,
    mergedComponentMap: globalMergedComponentMap,
    lastComponentByPageId: {
      ...(continueRecordingMergeState.value.lastComponentByPageId || {}),
      ...(lastAppendedComponent?.id ? { [targetPageNode.id]: lastAppendedComponent.id } : {})
    }
  }
  return true
}

const layoutComponentGroupEvenly = (components = [], bounds = {}) => {
  if (!components.length) {
    return
  }

  const xMin = bounds.xMin ?? CONTINUATION_COMPONENT_LAYOUT.xMin
  const xMax = bounds.xMax ?? CONTINUATION_COMPONENT_LAYOUT.xMax
  const yMin = bounds.yMin ?? CONTINUATION_COMPONENT_LAYOUT.yMin
  const yMax = bounds.yMax ?? CONTINUATION_COMPONENT_LAYOUT.yMax
  const columns = Math.min(components.length, FLOW_COMPONENT_GRID.maxColumns)
  const rows = Math.max(1, Math.ceil(components.length / columns))
  const rowHeight = (yMax - yMin) / rows

  components.forEach((component, index) => {
    const rowIndex = Math.floor(index / columns)
    const rowStartIndex = rowIndex * columns
    const rowItemCount = Math.min(columns, components.length - rowStartIndex)
    const columnIndex = index - rowStartIndex
    component.position = {
      x: buildContinuationColumnX(columnIndex, rowItemCount, xMin, xMax),
      y: clampPosition(yMin + rowHeight * (rowIndex + 0.5), yMin, yMax)
    }
  })
}

const dedupeConsecutivePageComponents = (components = []) => {
  const orderedComponents = [...components]
    .filter(component => component?.id)
    .sort((left, right) => (left.order ?? left.zIndex ?? 0) - (right.order ?? right.zIndex ?? 0))
  const keptComponents = []
  const componentIdMap = {}

  orderedComponents.forEach(component => {
    const cloned = cloneFlowCellData(component)
    const previous = keptComponents[keptComponents.length - 1]
    if (previous && isComponentEquivalentForMerge(cloned, previous)) {
      mergeEquivalentComponentConfig(previous, cloned)
      componentIdMap[component.id] = previous.id
      return
    }

    componentIdMap[component.id] = cloned.id
    keptComponents.push(cloned)
  })

  keptComponents.forEach((component, index) => {
    component.parentId = component.parentId ? (componentIdMap[component.parentId] || component.parentId) : null
    component.order = index
    component.zIndex = index
  })

  return keptComponents
}

const optimizePageNodeComponents = pageNode => {
  const data = pageNode?.getData?.()
  if (!data?.config) {
    return false
  }

  ensurePageNodeConfig(data.config)
  normalizeInnerComponents(data.config)
  const dedupedComponents = dedupeConsecutivePageComponents(data.config.innerComponents || [])
  const rootComponents = dedupedComponents.filter(component => !component.parentId)
  layoutComponentGroupEvenly(rootComponents, {
    xMin: 12,
    xMax: 88,
    yMin: 24,
    yMax: 78
  })

  const childrenByParent = new Map()
  dedupedComponents
    .filter(component => component.parentId)
    .forEach(component => {
      if (!childrenByParent.has(component.parentId)) {
        childrenByParent.set(component.parentId, [])
      }
      childrenByParent.get(component.parentId).push(component)
    })

  childrenByParent.forEach((children, parentId) => {
    layoutComponentGroupEvenly(children, {
      xMin: 14,
      xMax: 86,
      yMin: 26,
      yMax: 84
    })
    const parentComponent = dedupedComponents.find(component => component.id === parentId)
    if (parentComponent?.type === 'iframe') {
      const nextSize = buildContinuationIframeSize(children.length)
      const currentSize = getComponentSize(parentComponent)
      parentComponent.size = {
        width: Math.max(currentSize.width, nextSize.width),
        height: Math.max(currentSize.height, nextSize.height)
      }
    }
  })

  data.config.innerComponents = dedupedComponents
  data.config.executionPath = buildSequentialExecutionPath(dedupedComponents)
  const nextSize = estimatePageNodeSizeForComponents(dedupedComponents)
  pageNode.resize(nextSize.width, nextSize.height)
  pageNode.setData(buildPageNodeDataPayload(data), { overwrite: true })
  syncPageNodePorts(pageNode)
  refreshPageNodeView(pageNode, { syncPorts: false, delay: 80 })
  return true
}

const optimizeFlowLayout = () => {
  if (!graph) {
    return
  }

  const nodeMap = new Map(graph.getNodes().map(node => [node.id, node]))
  const orderedIds = getGraphExecutionOrder()
  const orderedNodes = orderedIds
    .map(nodeId => nodeMap.get(nodeId))
    .filter(Boolean)
  const remainingNodes = graph.getNodes().filter(node => !orderedIds.includes(node.id))
  const flowNodes = [...orderedNodes, ...remainingNodes]
    .filter(node => flowNodeTypes.has(node.getData?.()?.type))

  const startNode = flowNodes.find(node => node.getData?.()?.type === 'start')
  const endNode = flowNodes.find(node => node.getData?.()?.type === 'end')
  const middleNodes = flowNodes.filter(node => !['start', 'end'].includes(node.getData?.()?.type))
  const pageNodes = middleNodes.filter(node => node.getData?.()?.type === 'page')
  pageNodes.forEach(optimizePageNodeComponents)

  let currentX = 80
  const baseY = 100
  if (startNode) {
    const size = startNode.getSize?.() || { width: 150, height: 50 }
    startNode.setPosition(currentX, baseY + 200 - size.height / 2)
    currentX += size.width + 140
  }

  middleNodes.forEach(node => {
    const size = node.getSize?.() || { width: FLOW_COMPONENT_GRID.minWidth, height: FLOW_COMPONENT_GRID.minHeight }
    const y = node.getData?.()?.type === 'page'
      ? baseY
      : baseY + 200 - size.height / 2
    node.setPosition(currentX, y)
    currentX += size.width + 180
  })

  if (endNode) {
    const size = endNode.getSize?.() || { width: 150, height: 50 }
    endNode.setPosition(currentX, baseY + 200 - size.height / 2)
  }

  graph.getEdges().forEach(edge => {
    normalizeEdgeDirection(edge)
    applyStandardEdgeStyle(edge)
    ensureEdgeVisible(edge)
  })
  clearSelection()
  markGeneratedScriptStale()
  requestAnimationFrame(() => focusLoadedFlowContent())
  ElMessage.success('流程图排版已优化')
}

const getContinuationSourceEndpoint = (sourceNode) => {
  const anchor = continueRecordingAnchor.value || {}
  if (!sourceNode || !anchor.componentId || sourceNode.id !== anchor.nodeId) {
    return {
      cell: sourceNode?.id || '',
      port: getDefaultPortForEndpoint(sourceNode, 'source')
    }
  }

  const anchorComponent = (sourceNode.getData?.()?.config?.innerComponents || [])
    .find(component => component.id === anchor.componentId)
  const componentPortId = anchorComponent
    ? buildComponentExecutionEndpoint(anchorComponent, 'out').portId
    : `component-${anchor.componentId}-right-out`
  const portIds = new Set((sourceNode.getPorts?.() || []).map(port => port.id))
  return {
    cell: sourceNode.id,
    port: portIds.has(componentPortId) ? componentPortId : getDefaultPortForEndpoint(sourceNode, 'source')
  }
}

const addContinuationEdge = (sourceNodeId, targetNodeId, edgeId = '') => {
  if (!graph || !sourceNodeId || !targetNodeId || sourceNodeId === targetNodeId) {
    return
  }
  const sourceNode = graph.getCellById(sourceNodeId)
  const targetNode = graph.getCellById(targetNodeId)
  if (!sourceNode || !targetNode) {
    return
  }
  const edgeData = {
    id: edgeId || `continue-edge-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    shape: 'edge',
    source: getContinuationSourceEndpoint(sourceNode),
    target: {
      cell: targetNodeId,
      port: getDefaultPortForEndpoint(targetNode, 'target')
    },
    router: { ...STANDARD_EDGE_ROUTER },
    connector: {
      name: STANDARD_EDGE_CONNECTOR.name,
      args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
    },
    zIndex: 1000
  }
  addLoadedFlowEdges([edgeData])
}

const cloneContinuationSuccessorEdge = edge => {
  const edgeData = cloneFlowCellData(edge?.toJSON?.() || {})
  const targetCellId = getEndpointCellId(edge, 'target')
  const targetPortId = getEndpointPortId(edge, 'target')
  return {
    target: targetPortId ? { cell: targetCellId, port: targetPortId } : { cell: targetCellId },
    router: edgeData.router || { ...STANDARD_EDGE_ROUTER },
    connector: edgeData.connector || {
      name: STANDARD_EDGE_CONNECTOR.name,
      args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
    },
    attrs: edgeData.attrs,
    labels: edgeData.labels,
    zIndex: edgeData.zIndex ?? 1000
  }
}

const detachContinuationSuccessorEdges = baseNode => {
  if (!graph || !baseNode) {
    return []
  }

  const state = continueRecordingMergeState.value || {}
  const existingSuccessors = Array.isArray(state.detachedSuccessorEdges)
    ? state.detachedSuccessorEdges
    : []
  const anchor = continueRecordingAnchor.value || {}
  const anchorComponent = (baseNode.getData?.()?.config?.innerComponents || [])
    .find(component => component.id === anchor.componentId)
  const anchorComponentPortId = anchor.componentId
    ? (anchorComponent ? buildComponentExecutionEndpoint(anchorComponent, 'out').portId : `component-${anchor.componentId}-right-out`)
    : ''
  const isComponentAnchorNode = Boolean(anchorComponentPortId && baseNode.id === anchor.nodeId)
  const getComponentIdFromPortId = portId => {
    const match = String(portId || '').match(/^(?:component|iframe)-(.+?)-(?:top|left|bottom|right)-(?:in|out)$/)
    return match ? match[1] : ''
  }
  const outgoingEdges = (graph.getOutgoingEdges?.(baseNode) || []).filter(edge => {
    const sourceCellId = getEndpointCellId(edge, 'source')
    const targetCellId = getEndpointCellId(edge, 'target')
    if (sourceCellId !== baseNode.id || !targetCellId || targetCellId === baseNode.id) {
      return false
    }
    if (!isComponentAnchorNode) {
      return true
    }
    const sourcePortId = getEndpointPortId(edge, 'source')
    return sourcePortId === anchorComponentPortId || !getComponentIdFromPortId(sourcePortId)
  })

  if (!outgoingEdges.length) {
    return existingSuccessors
  }

  const nextSuccessors = existingSuccessors.length
    ? existingSuccessors
    : outgoingEdges.map(cloneContinuationSuccessorEdge)

  if (!isComponentAnchorNode) {
    outgoingEdges.forEach(edge => edge.remove({ skipContinuationRewire: true }))
  }
  continueRecordingMergeState.value = {
    ...state,
    detachedSuccessorEdges: nextSuccessors
  }

  return nextSuccessors
}

const reattachContinuationSuccessorEdges = sourceNodeId => {
  if (!graph || !sourceNodeId) {
    return
  }

  const state = continueRecordingMergeState.value || {}
  const successors = Array.isArray(state.detachedSuccessorEdges)
    ? state.detachedSuccessorEdges
    : []
  if (!successors.length) {
    return
  }

  const sourceNode = graph.getCellById(sourceNodeId)
  if (!sourceNode) {
    return
  }

  const edges = successors.map((successor, index) => {
    const targetCellId = getEndpointCellIdFromData(successor.target || {})
    if (!targetCellId || !graph.getCellById(targetCellId)) {
      return null
    }
    const targetPortId = getEndpointPortIdFromData(successor.target || {})
    return {
      id: `continue-successor-edge-${state.sessionId || Date.now()}-${sourceNodeId}-${targetCellId}-${index}`,
      shape: 'edge',
      source: getContinuationSourceEndpoint(sourceNode),
      target: targetPortId
        ? { cell: targetCellId, port: targetPortId }
        : { cell: targetCellId },
        router: successor.router || { ...STANDARD_EDGE_ROUTER },
        connector: successor.connector || {
          name: STANDARD_EDGE_CONNECTOR.name,
          args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
        },
      attrs: successor.attrs,
      labels: successor.labels,
      zIndex: successor.zIndex ?? 1000
    }
  }).filter(Boolean)

  addLoadedFlowEdges(edges)
}

const addContinuationPageNode = (sourcePageCell, sessionId = '', index = 0, options = {}) => {
  if (!graph || !sourcePageCell?.data?.config) {
    return null
  }

  const { config, componentIdMap } = cloneContinuationPageConfig(sourcePageCell.data.config, sessionId)
  if (options.applyResearchContext) {
    applyResearchContextToPageConfig(config)
  }
  const nextSize = estimatePageNodeSizeForComponents(config.innerComponents || [])
  const sourceSize = {
    width: sourcePageCell.width || sourcePageCell.size?.width || nextSize.width,
    height: sourcePageCell.height || sourcePageCell.size?.height || nextSize.height
  }
  const nodeSize = {
    width: Math.max(nextSize.width, sourceSize.width || 0),
    height: Math.max(nextSize.height, sourceSize.height || 0)
  }
  const baseNode = getAppendBasePageNode()
  detachContinuationSuccessorEdges(baseNode)
  const position = buildContinuationNodePosition(baseNode, index, nodeSize)
  const nodeId = `continue-page-${sessionId || Date.now()}-${sourcePageCell.id}`

  const node = graph.addNode({
    ...cloneFlowCellData(sourcePageCell),
    id: nodeId,
    x: position.x,
    y: position.y,
    width: nodeSize.width,
    height: nodeSize.height,
    shape: 'page-node',
    data: {
      ...cloneFlowCellData(sourcePageCell.data || {}),
      type: 'page',
      config
    },
    ports: []
  })

  syncPageNodePorts(node)
  refreshPageNodeView(node, { syncPorts: false, delay: 80 })
  addContinuationEdge(baseNode?.id, node.id, `continue-edge-${sessionId}-${baseNode?.id || 'anchor'}-${node.id}`)
  reattachContinuationSuccessorEdges(node.id)
  const lastComponent = getLastActionableComponent(config.innerComponents || [])
  continueRecordingMergeState.value = {
    ...continueRecordingMergeState.value,
    mergedComponentMap: {
      ...(continueRecordingMergeState.value.mergedComponentMap || {}),
      ...componentIdMap
    },
    appendAfterNodeId: node.id,
    lastComponentByPageId: {
      ...(continueRecordingMergeState.value.lastComponentByPageId || {}),
      ...(lastComponent?.id ? { [node.id]: lastComponent.id } : {})
    }
  }
  return node
}

const findMatchingExistingPageNode = (sourcePageCell, anchorNode = null, allowAnchorFallback = false) => {
  const sourceIdentity = getPageRecordingIdentity(sourcePageCell.data?.config || {})
  const pageNodes = getGraphPageNodes()
  if (sourceIdentity) {
    const exact = pageNodes.find(node => getPageRecordingIdentity(node) === sourceIdentity)
    if (exact) {
      return exact
    }
  }
  if (allowAnchorFallback && anchorNode?.getData?.()?.type === 'page') {
    return anchorNode
  }
  return null
}

const shouldApplyResearchContextToContinuationPage = (pageCell, pageIndex = 0, anchorNode = null) => {
  if (!getSelectedResearchPageIdentity()) {
    return false
  }
  const config = pageCell?.data?.config || {}
  const sourceIdentity = getPageRecordingIdentity(config)
  const sourcePath = String(config.recordingPagePath || '').trim()
  const sourceName = String(config.pageName || config.name || '').trim()
  const anchorIdentity = anchorNode ? getPageRecordingIdentity(anchorNode) : ''
  if (pageIndex === 0 && (!sourceIdentity || sourceIdentity === anchorIdentity)) {
    return false
  }
  return !sourcePath || sourcePath === sourceName
}

const mergeContinuationRecordingFlow = (recordingPayload = {}) => {
  if (!graph) {
    return false
  }

  const flow = recordingPayload.flow || {}
  const graphData = normalizeFlowGraphData(flow.graph_data)
  const pageCells = (graphData.cells || []).filter(cell => cell?.shape !== 'edge' && cell?.data?.type === 'page')
  const sessionId = recordingPayload.session?.session_id || flow.session_id || liveRecordingSessionId.value
  const state = continueRecordingMergeState.value
  const mergedPageIds = new Set(state.mergedPageIds || [])
  const mergedPageMap = { ...(state.mergedPageMap || {}) }
  const mergedComponentMap = { ...(state.mergedComponentMap || {}) }
  const anchor = continueRecordingAnchor.value || {}
  const anchorNode = anchor.nodeId ? graph.getCellById(anchor.nodeId) : null
  let changed = false
  let appendedIndex = 0

  pageCells.forEach((pageCell, pageIndex) => {
    const hasComponents = Boolean(pageCell?.data?.config?.innerComponents?.length)
    if (!hasComponents) {
      return
    }

    if (mergedPageIds.has(pageCell.id)) {
      const targetPageId = mergedPageMap[pageCell.id]
      const targetPageNode = targetPageId ? graph.getCellById(targetPageId) : null
      const sourceIdentity = getPageRecordingIdentity(pageCell.data?.config || {})
      if (targetPageNode) {
        const beforeCount = targetPageNode.getData()?.config?.innerComponents?.length || 0
        const appended = appendComponentsToExistingPageNode(targetPageNode, pageCell, sessionId)
        const afterCount = targetPageNode.getData()?.config?.innerComponents?.length || 0
        changed = changed || appended || beforeCount !== afterCount
      }
      if (!targetPageNode && sourceIdentity) {
        const fallbackPageNode = findMatchingExistingPageNode(pageCell, anchorNode, false)
        if (fallbackPageNode) {
          const appended = appendComponentsToExistingPageNode(fallbackPageNode, pageCell, sessionId)
          mergedPageMap[pageCell.id] = fallbackPageNode.id
          changed = changed || appended
        }
      }
      return
    }

    const sourceIdentity = getPageRecordingIdentity(pageCell.data?.config || {})
    const firstPageMatchesAnchor =
      pageIndex === 0 &&
      anchorNode?.getData?.()?.type === 'page' &&
      (!sourceIdentity || !getPageRecordingIdentity(anchorNode) || getPageRecordingIdentity(anchorNode) === sourceIdentity)
    const targetPageNode = findMatchingExistingPageNode(pageCell, anchorNode, firstPageMatchesAnchor)
    if (targetPageNode) {
      const appended = appendComponentsToExistingPageNode(targetPageNode, pageCell, sessionId)
      mergedPageMap[pageCell.id] = targetPageNode.id
      mergedPageIds.add(pageCell.id)
      changed = changed || appended
      return
    }

    const applyResearchContext = shouldApplyResearchContextToContinuationPage(pageCell, pageIndex, anchorNode)
    const researchContextPageNode = applyResearchContext ? findExistingPageNodeByResearchContext() : null
    if (researchContextPageNode) {
      const appended = appendComponentsToExistingPageNode(researchContextPageNode, pageCell, sessionId)
      mergedPageMap[pageCell.id] = researchContextPageNode.id
      mergedPageIds.add(pageCell.id)
      changed = changed || appended
      return
    }

    const newNode = addContinuationPageNode(pageCell, sessionId, appendedIndex, { applyResearchContext })
    appendedIndex += 1
    if (newNode) {
      mergedPageMap[pageCell.id] = newNode.id
      mergedPageIds.add(pageCell.id)
      changed = true
    }
  })

  if (changed || mergedPageIds.size !== (state.mergedPageIds || []).length) {
    continueRecordingMergeState.value = {
      ...state,
      mergedPageIds: Array.from(mergedPageIds),
      mergedPageMap,
      mergedComponentMap: {
        ...mergedComponentMap,
        ...(continueRecordingMergeState.value.mergedComponentMap || {})
      },
      appendAfterNodeId: continueRecordingMergeState.value.appendAfterNodeId || state.appendAfterNodeId,
      detachedSuccessorEdges: continueRecordingMergeState.value.detachedSuccessorEdges || state.detachedSuccessorEdges || [],
      lastComponentByPageId: {
        ...(state.lastComponentByPageId || {}),
        ...(continueRecordingMergeState.value.lastComponentByPageId || {})
      }
    }
    syncLoadedPageNodes()
    normalizeLoadedEdges()
    markGeneratedScriptStale()
  }

  return changed
}

const syncContinuationRecordingFlow = async ({ final = false } = {}) => {
  const sessionId = liveRecordingSessionId.value
  if (!sessionId || flowLoading.value) {
    return
  }

  try {
    const response = await getPlaywrightRecordingFlow(sessionId)
    const payload = unwrapApiData(response)
    const signature = getRecordingFlowStepSignature(payload)
    if (!final && signature === continueRecordingMergeState.value.lastSignature) {
      return
    }

    mergeContinuationRecordingFlow(payload)
    continueRecordingMergeState.value = {
      ...continueRecordingMergeState.value,
      lastSignature: signature
    }

    const sessionStatus = payload.session?.status || ''
    liveFlowActive.value = isRecordingFlowStatusActive(sessionStatus)
    if (!liveFlowActive.value) {
      stopLiveFlowPolling()
    }
  } catch (error) {
    console.warn('同步继续录制流程失败:', error)
    if (final) {
      ElMessage.error(error.response?.data?.error || '同步继续录制流程失败')
    }
  }
}

const persistCurrentFlowSilently = async () => {
  if (!currentFlowId.value || !graph) {
    return
  }
  const graphData = normalizeGraphDataForPersistence(graph.toJSON())
  const modulePayload = buildFlowRecordingModulePayload()
  const payload = {
    graph_data: graphData,
    ...modulePayload
  }
  if (currentFlowMeta.value?.name) {
    payload.name = currentFlowMeta.value.name
  }
  const response = await updateVisualFlow(currentFlowId.value, payload)
  currentFlowMeta.value = response.data || response
}

const getEndpointCellIdFromData = (endpoint = {}) => {
  return endpoint.cell || endpoint.cellId || endpoint.id || ''
}

const getEndpointPortIdFromData = (endpoint = {}) => {
  return endpoint.port || endpoint.portId || ''
}

const getEdgeDataEndpointKey = (edgeData = {}) => [
  getEndpointCellIdFromData(edgeData.source || {}),
  getEndpointPortIdFromData(edgeData.source || {}),
  getEndpointCellIdFromData(edgeData.target || {}),
  getEndpointPortIdFromData(edgeData.target || {})
].join('::')

const isPageSelfExecutionEdgeData = (edgeData = {}, nodeMap = new Map()) => {
  const sourceCellId = getEndpointCellIdFromData(edgeData.source || {})
  const targetCellId = getEndpointCellIdFromData(edgeData.target || {})
  if (!sourceCellId || sourceCellId !== targetCellId) {
    return false
  }

  const nodeData = nodeMap.get(sourceCellId)?.data || graph?.getCellById?.(sourceCellId)?.getData?.()
  return nodeData?.type === 'page'
}

const normalizeGraphDataForPersistence = (graphData = {}) => {
  const cells = Array.isArray(graphData.cells) ? graphData.cells : []
  const nodeMap = new Map(cells.filter(cell => cell?.shape !== 'edge').map(cell => [cell.id, cell]))
  const seenEdgeKeys = new Set()
  const normalizedCells = cells.filter(cell => {
    if (cell?.shape !== 'edge') {
      return true
    }
    if (isPageSelfExecutionEdgeData(cell, nodeMap)) {
      return false
    }

    const edgeKey = getEdgeDataEndpointKey(cell)
    if (seenEdgeKeys.has(edgeKey)) {
      return false
    }
    seenEdgeKeys.add(edgeKey)
    return true
  })

  return {
    ...graphData,
    cells: normalizedCells
  }
}

const getCurrentGraphDataForScript = () => {
  if (!graph) {
    return { cells: [] }
  }
  return normalizeGraphDataForPersistence(graph.toJSON())
}

const isMaskedFlowInputComponent = component => {
  if (component?.type !== 'input') {
    return false
  }
  const config = component.config || {}
  const value = String(config.value ?? config.inputValue ?? config.recordingActionValue ?? '')
  if (!/^\*{4,}$/.test(value)) {
    return false
  }
  const elementData = component.elementData || {}
  const attributes = elementData.attributes || {}
  const label = [
    component.label,
    component.name,
    config.label,
    config.placeholder,
    elementData.text,
    attributes.placeholder,
    attributes['aria-label'],
    attributes.name,
    attributes.type
  ].filter(Boolean).join(' ').toLowerCase()
  return label.includes('password') || label.includes('密码')
}

const getFlowInputVariableName = component => {
  const explicitName = String(component?.config?.inputReference || '').trim()
  if (explicitName) {
    return explicitName
  }
  const componentId = String(component?.id || component?.componentId || '').trim()
  return componentId ? `secret_${componentId.replace(/[^A-Za-z0-9_]/g, '_')}` : 'secret_password'
}

const collectMaskedFlowInputVariables = (graphData = getCurrentGraphDataForScript()) => {
  const variables = []
  const seen = new Set()
  ;(graphData.cells || []).forEach(cell => {
    const components = cell?.data?.config?.innerComponents || []
    components.forEach(component => {
      if (!isMaskedFlowInputComponent(component)) {
        return
      }
      const variableName = getFlowInputVariableName(component)
      if (seen.has(variableName)) {
        return
      }
      seen.add(variableName)
      variables.push({
        name: variableName,
        label: component.label || component.name || component.config?.placeholder || '敏感输入'
      })
    })
  })
  return variables
}

const collectProducedFlowVariableNames = (graphData = getCurrentGraphDataForScript()) => {
  const produced = new Set()
  ;(graphData.cells || [])
    .filter(cell => cell?.shape !== 'edge')
    .forEach(cell => {
      const config = cell?.data?.config || {}
      ;[config.inputAlias, config.outputName].forEach(name => {
        const normalized = String(name || '').trim()
        if (normalized) produced.add(normalized)
      })
      ;(config.innerComponents || []).forEach(component => {
        const outputName = String(component?.config?.outputName || '').trim()
        if (outputName) produced.add(outputName)
      })
    })
  return produced
}

const addFlowVariableRequirement = (requirements, seen, { name, label, sensitive = false }) => {
  const variableName = String(name || '').trim()
  if (!variableName) {
    return
  }
  const existing = requirements.find(item => item.name === variableName)
  if (existing) {
    existing.sensitive = existing.sensitive || sensitive
    if (!existing.label && label) {
      existing.label = label
    }
    return
  }
  if (seen.has(variableName)) {
    return
  }
  seen.add(variableName)
  requirements.push({
    name: variableName,
    label: label || variableName,
    sensitive
  })
}

const collectReferencedFlowVariables = (graphData = getCurrentGraphDataForScript()) => {
  const produced = collectProducedFlowVariableNames(graphData)
  const requirements = []
  const seen = new Set()

  ;(graphData.cells || [])
    .filter(cell => cell?.shape !== 'edge')
    .forEach(cell => {
      const data = cell?.data || {}
      const config = data.config || {}
      const nodeName = config.name || config.pageName || data.type || cell.id || '节点'

      if (config.inputMode === 'reference' && !produced.has(String(config.inputReference || '').trim())) {
        addFlowVariableRequirement(requirements, seen, {
          name: config.inputReference,
          label: `${nodeName} 输入`
        })
      }

      if (data.type === 'operation' && config.operationType === 'assertValue') {
        if (config.assertionTarget === 'variable' && !produced.has(String(config.assertionActualReference || '').trim())) {
          addFlowVariableRequirement(requirements, seen, {
            name: config.assertionActualReference,
            label: `${nodeName} 实际值变量`
          })
        }
        if (config.expectedMode === 'reference' && !produced.has(String(config.expectedReference || '').trim())) {
          addFlowVariableRequirement(requirements, seen, {
            name: config.expectedReference,
            label: `${nodeName} 预期值变量`
          })
        }
      }

      ;(config.innerComponents || []).forEach(component => {
        const componentConfig = component?.config || {}
        const componentLabel = getFlowComponentDisplayText(component) || component?.id || '组件'
        if (componentConfig.inputMode === 'reference' && !produced.has(String(componentConfig.inputReference || '').trim())) {
          addFlowVariableRequirement(requirements, seen, {
            name: componentConfig.inputReference,
            label: `${componentLabel} 输入`
          })
        }
        if (isMaskedFlowInputComponent(component)) {
          addFlowVariableRequirement(requirements, seen, {
            name: getFlowInputVariableName(component),
            label: component.label || component.name || component.config?.placeholder || componentLabel || '敏感输入',
            sensitive: true
          })
        }
      })
    })

  return requirements
}

const buildFlowExecutionVariables = async (graphData = getCurrentGraphDataForScript()) => {
  const variables = {}
  const requiredVariables = collectReferencedFlowVariables(graphData)
  const maskedVariables = collectMaskedFlowInputVariables(graphData)
  maskedVariables.forEach(variable => {
    addFlowVariableRequirement(requiredVariables, new Set(requiredVariables.map(item => item.name)), {
      ...variable,
      sensitive: true
    })
  })

  for (const variable of requiredVariables) {
    const envKey = `VITE_TESTHUB_FLOW_VAR_${variable.name.toUpperCase()}`
    const envValue = import.meta.env?.[envKey]
    if (envValue) {
      variables[variable.name] = envValue
      continue
    }
    const result = await ElMessageBox.prompt(`请输入「${variable.label}」的真实值`, '回放参数', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: variable.sensitive ? 'password' : 'text',
      inputPattern: /.+/,
      inputErrorMessage: '该参数不能为空'
    })
    variables[variable.name] = result.value || ''
  }
  return variables
}

const buildGraphScriptSignature = () => {
  const graphData = getCurrentGraphDataForScript()
  return JSON.stringify(graphData)
}

const isGeneratedScriptStale = computed(() => {
  flowScriptRevision.value
  return Boolean(generatedScript.value) && generatedScriptSignature.value !== buildGraphScriptSignature()
})

const markGeneratedScriptStale = () => {
  flowScriptRevision.value += 1
}

const addLoadedFlowEdges = (edges = []) => {
  if (!graph || !Array.isArray(edges) || edges.length === 0) {
    return
  }

  const existingEdgeIds = new Set(graph.getEdges().map(edge => edge.id))
  const existingEdgeKeys = new Set(graph.getEdges().map(edge => getEdgeEndpointKey(edge)))

  edges.forEach(rawEdge => {
    const edgeData = cloneFlowCellData(rawEdge)
    const sourceCellId = getEndpointCellIdFromData(edgeData.source || {})
    const targetCellId = getEndpointCellIdFromData(edgeData.target || {})

    if (!sourceCellId || !targetCellId) {
      return
    }
    const sourceNode = graph.getCellById(sourceCellId)
    const targetNode = graph.getCellById(targetCellId)
    if (!sourceNode || !targetNode) {
      return
    }
    if (sourceCellId === targetCellId && sourceNode.getData?.()?.type === 'page') {
      return
    }
    if (edgeData.id && existingEdgeIds.has(edgeData.id)) {
      return
    }
    const edgeKey = getEdgeDataEndpointKey(edgeData)
    if (existingEdgeKeys.has(edgeKey)) {
      return
    }

    try {
      edgeData.shape = edgeData.shape || 'edge'
      const edge = graph.addEdge(edgeData)
      normalizeEdgeDirection(edge)
      applyStandardEdgeStyle(edge)
      ensureEdgeVisible(edge)
      existingEdgeIds.add(edge.id)
      existingEdgeKeys.add(getEdgeEndpointKey(edge))
    } catch (error) {
      console.warn('加载流程连线失败:', {
        edgeId: edgeData.id,
        source: edgeData.source,
        target: edgeData.target,
        error
      })
    }
  })
}

const syncLoadedPageNodes = () => {
  if (!graph) return

  graph.getNodes().forEach(node => {
    const data = node.getData()
    if (data?.type !== 'page') {
      return
    }

    ensurePageNodeConfig(data.config)
    normalizeInnerComponents(data.config)
    node.setData(buildPageNodeDataPayload(data), { overwrite: true })
    syncPageNodePorts(node)
    refreshPageNodeView(node, { syncPorts: false, delay: 80 })
  })
}

const applyStandardEdgeStyle = (edge) => {
  if (!edge) {
    return
  }

  edge.setAttrs(getStandardEdgeStyle(false))
  edge.prop('router', { ...STANDARD_EDGE_ROUTER })
  edge.prop('connector', {
    name: STANDARD_EDGE_CONNECTOR.name,
    args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
  })
}

const applySelectedEdgeStyle = (edge) => {
  if (!edge) {
    return
  }

  edge.setAttrs(getStandardEdgeStyle(true))
  edge.prop('router', { ...STANDARD_EDGE_ROUTER })
  edge.prop('connector', {
    name: STANDARD_EDGE_CONNECTOR.name,
    args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
  })
  ensureEdgeVisible(edge)
}

const resetSelectedEdgeStyle = () => {
  if (selectedEdge.value && graph?.getCellById?.(selectedEdge.value.id)) {
    applyStandardEdgeStyle(selectedEdge.value)
    ensureEdgeVisible(selectedEdge.value)
  }
}

const getCellDisplayName = (cellId) => {
  const cell = graph?.getCellById?.(cellId)
  if (!cell) {
    return cellId || '未知节点'
  }

  const data = cell.getData?.() || {}
  return data.config?.name || data.config?.pageName || data.config?.text || data.type || cellId
}

const selectedEdgeSummary = computed(() => {
  if (!selectedEdge.value) {
    return {
      id: '',
      sourceNode: '',
      sourcePort: '',
      targetNode: '',
      targetPort: ''
    }
  }

  const sourceCellId = getEndpointCellId(selectedEdge.value, 'source')
  const targetCellId = getEndpointCellId(selectedEdge.value, 'target')
  return {
    id: selectedEdge.value.id,
    sourceNode: getCellDisplayName(sourceCellId),
    sourcePort: getEndpointPortId(selectedEdge.value, 'source'),
    targetNode: getCellDisplayName(targetCellId),
    targetPort: getEndpointPortId(selectedEdge.value, 'target')
  }
})

const canDeleteSelection = computed(() => Boolean(
  selectedEdge.value ||
  selectedExecutionStepIndex.value !== null ||
  (selectedNode.value?.type === 'page' && selectedInnerComponentId.value) ||
  selectedNode.value
))

const selectedDeleteLabel = computed(() => {
  if (selectedEdge.value) return '删除连线'
  if (selectedExecutionStepIndex.value !== null) return '删除路径'
  if (selectedNode.value?.type === 'page' && selectedInnerComponentId.value) return '删除组件'
  if (selectedNode.value) return '删除节点'
  return '删除选中'
})

const clearSelection = () => {
  resetSelectedEdgeStyle()
  selectedNode.value = null
  selectedEdge.value = null
  selectedExecutionStepIndex.value = null
  selectedInnerComponentId.value = null
  activeInnerComponentId.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  activeDetailMenu.value = 'node'
}

const selectGraphEdge = (edge) => {
  if (!edge) return

  resetSelectedEdgeStyle()
  selectedEdge.value = edge
  selectedNode.value = null
  selectedExecutionStepIndex.value = null
  selectedInnerComponentId.value = null
  activeInnerComponentId.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  activeDetailMenu.value = 'edge'
  applySelectedEdgeStyle(edge)
}

const captureDetailSelectionState = () => ({
  activeMenu: activeDetailMenu.value,
  nodeId: selectedNode.value?.id || '',
  edgeId: selectedEdge.value?.id || '',
  selectedInnerComponentId: selectedInnerComponentId.value || '',
  activeInnerComponentId: activeInnerComponentId.value || '',
  selectedExecutionStepIndex: selectedExecutionStepIndex.value,
  executionResultRef: {
    ...(selectedExecutionResultRef.value || {})
  }
})

const restoreDetailSelectionState = (selectionState) => {
  if (!selectionState || !graph) {
    return false
  }

  if (selectionState.activeMenu === 'edge' && selectionState.edgeId) {
    const edge = graph.getCellById?.(selectionState.edgeId)
    if (edge?.isEdge?.() || edge?.shape === 'edge') {
      selectGraphEdge(edge)
      return true
    }
  }

  const executionRef = selectionState.executionResultRef || {}
  const nodeId = selectionState.nodeId || executionRef.nodeId || ''
  if (!nodeId) {
    return false
  }

  const node = graph.getCellById?.(nodeId)
  if (!node) {
    return false
  }

  const executionComponentId = executionRef.componentId || (executionRef.key && executionRef.key !== 'node' ? executionRef.key : '')
  const componentId = selectionState.selectedInnerComponentId || selectionState.activeInnerComponentId || executionComponentId || ''
  selectFlowNode(node, componentId)

  if (
    Number.isInteger(selectionState.selectedExecutionStepIndex) &&
    selectedNode.value?.type === 'page' &&
    selectedNode.value.config?.executionPath?.[selectionState.selectedExecutionStepIndex]
  ) {
    selectedExecutionStepIndex.value = selectionState.selectedExecutionStepIndex
  }

  if (selectionState.activeMenu === 'execution' && executionRef.nodeId && executionRef.key) {
    selectedExecutionResultRef.value = {
      nodeId: executionRef.nodeId,
      key: executionRef.key,
      componentId: executionRef.componentId || ''
    }
    if (resolveExecutionResultDetail(selectedExecutionResultRef.value)) {
      activeDetailMenu.value = 'execution'
      return true
    }
    selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  }

  if (selectionState.activeMenu === 'component') {
    const hasComponentDetail = Boolean(activeInnerComponent.value || selectedNode.value?.type === 'component')
    activeDetailMenu.value = hasComponentDetail ? 'component' : 'node'
    return hasComponentDetail || activeDetailPanelVisible.value
  }

  activeDetailMenu.value = 'node'
  return activeDetailPanelVisible.value
}

const normalizeLoadedEdges = () => {
  if (!graph) return

  graph.getEdges().forEach(edge => {
    applyStandardEdgeStyle(edge)
    ensureEdgeVisible(edge)
  })
}

const focusLoadedFlowContent = () => {
  if (!graph || graph.getCells().length === 0) {
    return
  }

  if (typeof graph.zoomToFit === 'function') {
    graph.zoomToFit({
      padding: 80,
      maxScale: 1
    })
    return
  }

  graph.centerContent?.()
}

const getEndpointCellId = (edge, direction) => {
  const endpoint = direction === 'source'
    ? (edge.getSource?.() || edge.prop?.('source') || {})
    : (edge.getTarget?.() || edge.prop?.('target') || {})
  return endpoint?.cell || endpoint?.cellId || endpoint?.id || (
    direction === 'source' ? edge.getSourceCellId?.() : edge.getTargetCellId?.()
  )
}

const getEndpointPortId = (edge, direction) => {
  const endpoint = direction === 'source'
    ? (edge.getSource?.() || edge.prop?.('source') || {})
    : (edge.getTarget?.() || edge.prop?.('target') || {})
  return endpoint?.port || (
    direction === 'source' ? edge.getSourcePortId?.() : edge.getTargetPortId?.()
  )
}

const getPortSemanticRole = (node, portId) => {
  const port = node?.getPort?.(portId)
  const direction = port?.data?.direction
  if (direction === 'in' || direction === 'out') {
    return direction
  }

  const group = port?.group || ''
  if ([FLOW_PORT_GROUPS.in, 'in', 'top', 'left'].includes(group)) {
    return 'in'
  }
  if ([FLOW_PORT_GROUPS.out, 'out', 'bottom', 'right'].includes(group)) {
    return 'out'
  }

  const id = String(portId || '')
  if (/(?:^|-)in\d*$|-(?:top|left)-in$|^port-(?:top|left)$/.test(id)) {
    return 'in'
  }
  if (/(?:^|-)out\d*$|-(?:bottom|right)-out$|^port-(?:bottom|right)$/.test(id)) {
    return 'out'
  }

  return ''
}

const normalizeEdgeDirection = (edge) => {
  if (!edge) {
    return
  }

  const sourceNode = edge.getSourceNode?.()
  const targetNode = edge.getTargetNode?.()
  const sourcePortId = getEndpointPortId(edge, 'source')
  const targetPortId = getEndpointPortId(edge, 'target')
  if (!sourceNode || !targetNode || !sourcePortId || !targetPortId) {
    return
  }

  const sourceRole = getPortSemanticRole(sourceNode, sourcePortId)
  const targetRole = getPortSemanticRole(targetNode, targetPortId)
  if (sourceRole === 'in' && targetRole === 'out') {
    edge.setSource({ cell: targetNode.id, port: targetPortId })
    edge.setTarget({ cell: sourceNode.id, port: sourcePortId })
  }
}

const getDefaultPortForEndpoint = (node, direction) => {
  const type = node?.getData?.()?.type || ''
  const portIds = new Set((node?.getPorts?.() || []).map(port => port.id))
  const preferred = direction === 'source'
    ? [
        type === 'page' ? 'page-right-out' : 'out1',
        'out1',
        'port-right',
        'page-bottom-out'
      ]
    : [
        type === 'page' ? 'page-left-in' : 'in1',
        'in1',
        'port-left',
        'page-top-in'
      ]

  return preferred.find(portId => portIds.has(portId)) || ''
}

const repairLoadedFlowEdges = () => {
  if (!graph) return

  graph.getEdges().forEach(edge => {
    const sourceCellId = getEndpointCellId(edge, 'source')
    const targetCellId = getEndpointCellId(edge, 'target')
    const sourceNode = sourceCellId ? graph.getCellById(sourceCellId) : null
    const targetNode = targetCellId ? graph.getCellById(targetCellId) : null

    if (!sourceNode || !targetNode) {
      return
    }

    const sourcePorts = new Set((sourceNode.getPorts?.() || []).map(port => port.id))
    const targetPorts = new Set((targetNode.getPorts?.() || []).map(port => port.id))
    let sourcePortId = normalizeIframePortId(
      getEndpointPortId(edge, 'source'),
      sourceNode.getData?.()?.config?.innerComponents || []
    )
    let targetPortId = normalizeIframePortId(
      getEndpointPortId(edge, 'target'),
      targetNode.getData?.()?.config?.innerComponents || []
    )

    if (!sourcePortId || !sourcePorts.has(sourcePortId)) {
      sourcePortId = getDefaultPortForEndpoint(sourceNode, 'source')
    }
    if (!targetPortId || !targetPorts.has(targetPortId)) {
      targetPortId = getDefaultPortForEndpoint(targetNode, 'target')
    }

    edge.setSource(sourcePortId ? { cell: sourceNode.id, port: sourcePortId } : { cell: sourceNode.id })
    edge.setTarget(targetPortId ? { cell: targetNode.id, port: targetPortId } : { cell: targetNode.id })
    normalizeEdgeDirection(edge)
    applyStandardEdgeStyle(edge)
    ensureEdgeVisible(edge)
  })
}

const getEdgeEndpointKey = (edge) => [
  getEndpointCellId(edge, 'source'),
  getEndpointPortId(edge, 'source'),
  getEndpointCellId(edge, 'target'),
  getEndpointPortId(edge, 'target')
].join('::')

const renderLoadedPageExecutionPathEdges = () => {
  // 页面内部步骤线由 PageNodeContent 的 SVG 覆盖层根据 executionPath 绘制。
  // 不再额外生成 X6 自连边，避免录制流程出现重复连线。
}

const applyBackendFlow = (flow, { focus = true } = {}) => {
  if (!flow || !graph) {
    return
  }

  currentFlowId.value = flow.flow_id || currentFlowId.value
  currentFlowMeta.value = flow
  syncResearchContextFromModule(flow.module || flow.metadata?.module || flow.recording_session?.metadata?.module || {})
  const recordingSessionId = flow.recording_session_id || flow.metadata?.recording_session_id || ''
  if (recordingSessionId) {
    liveRecordingSessionId.value = recordingSessionId
    liveFlowActive.value = isRecordingFlowStatusActive(getVisualFlowRecordingStatus(flow))
  }

  const { nodes, edges } = splitFlowGraphCells(flow.graph_data)
  const detailSelectionState = captureDetailSelectionState()
  graph.fromJSON({ cells: nodes.map(cloneFlowCellData) })
  selectedNode.value = null
  selectedEdge.value = null
  selectedExecutionStepIndex.value = null
  selectedInnerComponentId.value = null
  activeInnerComponentId.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  activeDetailMenu.value = 'node'
  syncLoadedPageNodes()
  addLoadedFlowEdges(edges)
  renderLoadedPageExecutionPathEdges()
  repairLoadedFlowEdges()
  normalizeLoadedEdges()
  restoreDetailSelectionState(detailSelectionState)
  if (focus) {
    requestAnimationFrame(() => focusLoadedFlowContent())
  }
}

const loadBackendFlow = async () => {
  const flowId = getRouteFlowId()
  if (!flowId) {
    return
  }

  flowLoading.value = true
  try {
    const response = await getVisualFlowDetail(flowId)
    applyBackendFlow(response.data || response)
  } catch (error) {
    console.error('加载流程失败:', error)
    ElMessage.error(error.response?.data?.error || '加载流程失败')
  } finally {
    flowLoading.value = false
  }
}

const syncRecordingFlow = async ({ initial = false } = {}) => {
  const sessionId = liveRecordingSessionId.value || getRouteRecordingSessionId()
  if (!sessionId || flowLoading.value) {
    return
  }

  if (initial) {
    flowLoading.value = true
  }

  try {
    const routeFlowId = getRouteFlowId()
    const currentFlowSessionId =
      currentFlowMeta.value?.recording_session_id ||
      currentFlowMeta.value?.metadata?.recording_session_id ||
      ''
    const flowIdForRefresh = currentFlowId.value || routeFlowId
    const shouldLoadCurrentFlow = Boolean(flowIdForRefresh && (
      !sessionId ||
      !currentFlowSessionId ||
      currentFlowSessionId === sessionId ||
      flowIdForRefresh === routeFlowId
    ))
    const response = shouldLoadCurrentFlow
      ? await getVisualFlowDetail(flowIdForRefresh)
      : await createPlaywrightRecordingFlow(sessionId, {
          force_new: false,
          allow_empty: true
        })
    const flow = response.data?.flow || response.flow
      || response.data
      || response
    if (!flow?.flow_id) {
      return
    }

    const previousSignature = getFlowMetadataStepSignature(currentFlowMeta.value)
    const nextSignature = getFlowMetadataStepSignature(flow)
    const isFirstFlow = !currentFlowId.value
    applyBackendFlow(flow, { focus: initial || isFirstFlow })

    if (flow.flow_id && route.query.flow_id !== flow.flow_id) {
      router.replace({
        path: '/manual-testcases/visual-flow',
        query: {
          ...route.query,
          flow_id: flow.flow_id,
          recording_session_id: sessionId
        }
      })
    }

    liveFlowActive.value = isRecordingFlowStatusActive(getVisualFlowRecordingStatus(flow))
    if (!liveFlowActive.value) {
      stopLiveFlowPolling()
    }
    if (!initial && previousSignature !== nextSignature) {
      const filteredCount = flow.metadata?.recording_filtered_step_count || flow.snapshot_summary?.filtered_step_count || 0
      if (filteredCount) {
        console.info(`录制流程已刷新，已过滤 ${filteredCount} 个无效/重复步骤`)
      }
    }
  } catch (error) {
    console.warn('同步录制流程失败:', error)
    if (initial) {
      ElMessage.error(error.response?.data?.error || '同步录制流程失败')
    }
  } finally {
    if (initial) {
      flowLoading.value = false
    }
  }
}

const startLiveFlowPolling = () => {
  const sessionId = liveRecordingSessionId.value || getRouteRecordingSessionId()
  if (!sessionId) {
    return
  }
  liveRecordingSessionId.value = sessionId
  stopLiveFlowPolling()
  if (!liveFlowActive.value) {
    return
  }
  liveFlowTimer = window.setInterval(() => {
    if (!liveFlowActive.value) {
      stopLiveFlowPolling()
      return
    }
    if (liveRecordingMode.value === CONTINUE_RECORDING_MODE_APPEND) {
      syncContinuationRecordingFlow()
      return
    }
    syncRecordingFlow()
  }, 2500)
}

const stopLiveFlowPolling = () => {
  if (liveFlowTimer) {
    window.clearInterval(liveFlowTimer)
    liveFlowTimer = null
  }
}

const setupEnhancedFlowEvents = () => {
  graph.on('edge:connected', ({ edge }) => {
    const sourceNode = edge.getSourceNode()
    const targetNode = edge.getTargetNode()
    const sourcePort = edge.getSourcePortId()
    const targetPort = edge.getTargetPortId()

    if (!isEnhancedPageFlowEdge(sourceNode, targetNode, sourcePort, targetPort)) {
      normalizeEdgeDirection(edge)
      applyStandardEdgeStyle(edge)
      ensureEdgeVisible(edge)
      return
    }

    upsertEnhancedExecutionPath(sourceNode, sourcePort, targetPort)
    edge.remove({ skipExecutionPathSync: true })
    return
  })

  graph.on('edge:removed', ({ edge, options }) => {
    if (options?.skipExecutionPathSync) {
      return
    }

    const sourceNode = edge.getSourceNode()
    const targetNode = edge.getTargetNode()
    const sourcePort = edge.getSourcePortId()
    const targetPort = edge.getTargetPortId()

    if (!isEnhancedPageFlowEdge(sourceNode, targetNode, sourcePort, targetPort)) {
      return
    }

    removeEnhancedExecutionPath(sourceNode, sourcePort, targetPort)
  })
}

const setPageNodePortsVisible = (nodeId, visible = true) => {
  if (!containerRef.value || !nodeId) {
    return
  }

  const nodeEl = containerRef.value.querySelector(`[data-cell-id="${nodeId}"]`)
  if (!nodeEl) {
    return
  }

  const portsContainers = nodeEl.querySelectorAll('[data-port-group-node-id], .x6-graph-svg-ports, g[data-type="port-container"]')
  portsContainers.forEach(container => {
    container.style.visibility = visible ? '' : 'hidden'
    container.style.pointerEvents = visible ? '' : 'none'
  })
}

const handleEmbeddedExecutionResultExpanded = (event) => {
  const { nodeId, key, expanded, detailOnly } = event?.detail || {}
  if (!nodeId) {
    return
  }

  if (detailOnly) {
    if (expanded && key && graph) {
      const sameExecutionResult =
        selectedExecutionResultRef.value.nodeId === nodeId &&
        selectedExecutionResultRef.value.key === key
      if (sameExecutionResult) {
        selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
        activeDetailMenu.value = 'execution'
        return
      }

      const node = graph.getCellById?.(nodeId)
      if (node) {
        selectFlowNode(node, key === 'node' ? '' : key)
        selectedExecutionResultRef.value = {
          nodeId,
          key,
          componentId: key === 'node' ? '' : key
        }
        activeDetailMenu.value = 'execution'
      }
    }
    return
  }

  const expandedKeys = expandedExecutionResultKeysByNode.get(nodeId) || new Set()
  if (expanded && key) {
    expandedKeys.add(key)
  } else if (key) {
    expandedKeys.delete(key)
  } else if (!expanded) {
    expandedKeys.clear()
  }

  if (expandedKeys.size > 0) {
    expandedExecutionResultKeysByNode.set(nodeId, expandedKeys)
  } else {
    expandedExecutionResultKeysByNode.delete(nodeId)
  }

  setPageNodePortsVisible(nodeId, expandedKeys.size === 0)

  if (expanded && key && graph) {
    const node = graph.getCellById?.(nodeId)
    if (node) {
      selectFlowNode(node, key === 'node' ? '' : key)
      selectedExecutionResultRef.value = {
        nodeId,
        key,
        componentId: key === 'node' ? '' : key
      }
      activeDetailMenu.value = 'execution'
    }
  } else if (selectedExecutionResultRef.value.nodeId === nodeId && selectedExecutionResultRef.value.key === key) {
    selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
    if (key && key !== 'node') {
      activeDetailMenu.value = 'component'
    }
  }
}

const handlePageNodeComponentsUpdated = (event) => {
  const nodeId = event?.detail?.nodeId || ''
  if (!graph || !nodeId) {
    return
  }

  const node = graph.getCellById?.(nodeId)
  if (!node || node.getData?.()?.type !== 'page') {
    return
  }

  syncPageNodePorts(node)
  refreshPageNodeView(node, { syncPorts: false, delay: 0 })
  refreshConnectedEdges(node)
  markGeneratedScriptStale()
}

const handlePageNodeMoved = (event) => {
  const nodeId = event?.detail?.nodeId || ''
  if (!graph || !nodeId) {
    return
  }

  const node = graph.getCellById?.(nodeId)
  if (!node || node.getData?.()?.type !== 'page') {
    return
  }

  refreshConnectedEdges(node)
  markGeneratedScriptStale()
}

const ensureEdgeVisible = (edge) => {
  if (!edge) {
    return
  }

  edge.setZIndex(1000)
  edge.toFront()
}

// 可用元素列表（计算属性）
const availableElements = computed(() => {
  if (!currentComponentConfig.value.pageNodeId) return []

  const pageNode = graph?.getCellById(currentComponentConfig.value.pageNodeId)
  const snapshotData = pageNode?.getData()?.config?.snapshotData
  const pageConfig = pageNode?.getData()?.config

  if (!snapshotData) return []

  // 过滤已经映射过的元素
  const mappedElementIds = getMappedElementIds(pageNode)
  const parentComponent = pageConfig?.innerComponents?.find(component => component.id === currentComponentConfig.value.parentId)
  const mappedIframeComponents = (pageConfig?.innerComponents || []).filter(component => component.type === 'iframe')

  return snapshotData.interactiveElements.filter(element => {
    // 过滤已映射的元素
    if (mappedElementIds.includes(element.id)) return false

    // 根据组件类型过滤可适配的元素
    if (!isFlowElementCompatible(element, currentComponentConfig.value.type)) {
      return false
    }

    if (parentComponent?.elementId) {
      return isElementInsideElement(element, parentComponent.elementId)
    }

    if (currentComponentConfig.value.type !== 'iframe') {
      return !mappedIframeComponents.some(component => component.elementId && isElementInsideElement(element, component.elementId))
    }

    return true
  })
})

// 节点输入输出默认配置
const nodeIODefaults = {
  inputMode: 'literal',
  inputValue: '',
  inputReference: '',
  inputAlias: '',
  outputName: '',
  outputSource: 'none',
  outputValue: ''
}

const ensureNodeIOConfig = (config = {}) => {
  Object.entries(nodeIODefaults).forEach(([key, value]) => {
    if (config[key] === undefined) {
      config[key] = value
    }
  })
  return config
}

const ensureStartNodeConfig = (config = {}) => {
  if (!['auto', 'clean', 'inject'].includes(config.authStateStrategy)) {
    config.authStateStrategy = 'auto'
  }
  return config
}

const nodeDefaults = {
  start: {
    ...nodeIODefaults,
    name: '开始',
    browserType: 'chromium',
    url: 'https://example.com',
    authStateStrategy: 'auto',
    headless: false,
    maximize: true,
    viewportWidth: 1920,
    viewportHeight: 1080
  },
  page: {
    ...nodeIODefaults,
    name: '页面节点',
    pageName: '未命名页面',
    snapshotFile: null,
    description: '',
    elements: [],
    innerComponents: [],
    executionPath: []
  },
  operation: {
    ...nodeIODefaults,
    name: '操作节点',
    operationType: 'sleep',
    timeout: 1000,
    selector: '',
    assertionTarget: 'selectorText',
    assertionSelector: '',
    assertionActualReference: '',
    assertionActualExpression: '',
    assertionOperator: 'equals',
    expectedMode: 'literal',
    expectedValue: '',
    expectedReference: '',
    assertionTimeout: 5000,
    customCode: ''
  },
  end: {
    ...nodeIODefaults,
    name: '结束',
    generateReport: true
  }
}

// 初始化图形编辑器
onMounted(async () => {
  await loadSnapshotFiles()
  registerFlowEdgeConnector()
  initGraph()
  registerNodes()
  registerDynamicPageNodeShape()
  setupEvents()
  setupEnhancedFlowEvents()
  const recordingSessionId = getRouteRecordingSessionId()
  if (recordingSessionId) {
    liveRecordingSessionId.value = recordingSessionId
    if (getRouteFlowId()) {
      await loadBackendFlow()
    } else {
      await syncRecordingFlow({ initial: true })
    }
    if (liveFlowActive.value) {
      startLiveFlowPolling()
    }
  } else {
    await loadBackendFlow()
  }

  // 监听展开组件事件
  window.addEventListener('expand-components', handleExpandComponents)
  window.addEventListener('testhub-flow-node-select', handleEmbeddedPageNodeSelect)
  window.addEventListener('testhub-flow-execution-step-select', handleEmbeddedExecutionStepSelect)
  window.addEventListener('testhub-flow-execution-result-expanded', handleEmbeddedExecutionResultExpanded)
  window.addEventListener('testhub-flow-page-node-components-updated', handlePageNodeComponentsUpdated)
  window.addEventListener('testhub-flow-page-node-moved', handlePageNodeMoved)
  window.addEventListener('keydown', handleEditorKeydown)
})

onBeforeUnmount(() => {
  stopLiveFlowPolling()
  stopExecutionPolling()
  expandedExecutionResultKeysByNode.clear()
  document.body.classList.remove('flow-inner-component-dragging')
  if (graph) {
    graph.dispose()
  }

  // 移除事件监听
  window.removeEventListener('expand-components', handleExpandComponents)
  window.removeEventListener('testhub-flow-node-select', handleEmbeddedPageNodeSelect)
  window.removeEventListener('testhub-flow-execution-step-select', handleEmbeddedExecutionStepSelect)
  window.removeEventListener('testhub-flow-execution-result-expanded', handleEmbeddedExecutionResultExpanded)
  window.removeEventListener('testhub-flow-page-node-components-updated', handlePageNodeComponentsUpdated)
  window.removeEventListener('testhub-flow-page-node-moved', handlePageNodeMoved)
  window.removeEventListener('keydown', handleEditorKeydown)
})

// 加载快照文件列表
const loadSnapshotFiles = async () => {
  try {
    const response = await getPlaywrightSnapshots()
    const results = extractSnapshotResults(response)
    snapshotCatalog.value = results.map(item => ({
      ...item,
      page_name: item.page_name || ''
    }))
  } catch (error) {
    console.error('加载快照文件失败:', error)
    ElMessage.error('加载快照文件失败: ' + (error.message || '未知错误'))
  }
}

// 初始化画布
const initGraph = () => {
  graph = new Graph({
    container: containerRef.value,
    width: containerRef.value.offsetWidth,
    height: containerRef.value.offsetHeight,
    grid: {
      size: 10,
      visible: true,
      type: 'dot',
      args: {
        color: '#e0e0e0',
        thickness: 1
      }
    },
    panning: {
      enabled: true,
      eventTypes: ['leftMouseDown', 'mouseWheel']
    },
    guard: (event) => {
      const target = event?.target
      return Boolean(
        target?.closest?.('.flow-component') ||
        document.body.classList.contains('flow-page-node-header-dragging') ||
        document.body.classList.contains('flow-inner-component-dragging')
      )
    },
    interacting: {
      edgeLabelMovable: false,
      nodeMovable: () => !document.body.classList.contains('flow-inner-component-dragging')
    },
    mousewheel: {
      enabled: true,
      modifiers: 'ctrl',
      factor: 1.1,
      maxScale: 1.5,
      minScale: 0.5
    },
    highlighting: {
      magnetAdsorbed: {
        name: 'stroke',
        args: {
          attrs: {
            fill: '#5F95FF',
            stroke: '#5F95FF'
          }
        }
      }
    },
    connecting: {
      snap: true,
      allowBlank: false,
      // 页面节点内部组件连线属于同一节点内的连接，需在此放开，
      // 再由 validateConnection 细分限制非页面节点的自连行为。
      allowLoop: true,
      allowNode: true,  // 允许节点之间连线
      allowEdge: false,  // 不允许边连到边
      allowPort: true,   // 允许通过端口连线
      highlight: true,
      router: STANDARD_EDGE_ROUTER,
      connector: STANDARD_EDGE_CONNECTOR,
      connectionPoint: 'anchor',
      anchor: 'center',
      // 验证端口是否可以参与连接（作为源或目标）
      validateMagnet({ magnet, e, view }) {
        const magnetAttr = magnet.getAttribute('magnet')
        const portGroup = magnet.getAttribute('port-group')
        const portId = magnet.getAttribute('port')

        console.log('validateMagnet 调用:', {
          magnetAttr,
          magnetAttrType: typeof magnetAttr,
          portGroup,
          portId,
          element: magnet.tagName,
          classList: magnet.classList ? Array.from(magnet.classList) : [],
          nodeId: view?.cell?.id,
          eventType: e?.type
        })

        // 所有带 magnet 属性的端口都允许连接
        // 不再区分输入输出，让 validateConnection 处理方向性验证
        return true
      },
      // 验证连接是否有效
      validateConnection({ sourceView, targetView, sourceMagnet, targetMagnet }) {
        console.log('validateConnection 被调用')

        // 必须有源端口和目标端口
        if (!sourceMagnet || !targetMagnet) {
          console.log('拒绝：缺少源端口或目标端口')
          return false
        }

        const sourcePortId = sourceMagnet.getAttribute('port')
        const targetPortId = targetMagnet.getAttribute('port')
        const sourcePortGroup = sourceMagnet.getAttribute('port-group')
        const targetPortGroup = targetMagnet.getAttribute('port-group')
        const isSameNode = sourceView === targetView
        const sourcePortData = sourceView?.cell?.getPort?.(sourcePortId)?.data
        const targetPortData = targetView?.cell?.getPort?.(targetPortId)?.data

        console.log('连接验证:', {
          sourcePort: sourcePortGroup,
          targetPort: targetPortGroup,
          sourcePortId,
          targetPortId,
          sourceNode: sourceView?.cell?.id,
          targetNode: targetView?.cell?.id,
          isSameNode,
          sourcePortData,
          targetPortData
        })

        // 检查是否是页面节点内部的连接（组件间或组件到页面端口）
        const isPageNode = sourceView?.cell?.getData()?.type === 'page'

        if (isSameNode) {
          if (isPageNode) {
            // 页面节点内部允许连接，但不能端口连到自己
            if (sourcePortId === targetPortId) {
              console.log('拒绝：不能连接到同一个端口')
              return false
            }
            console.log('允许：页面节点内部连接')
            const isPageEntryToInnerEntry =
              sourcePortData?.scopeType === 'page' &&
              sourcePortData?.direction === 'in' &&
              targetPortData?.scopeType !== 'page' &&
              targetPortData?.direction === 'in'

            const isInnerExitToPageExit =
              sourcePortData?.scopeType !== 'page' &&
              sourcePortData?.direction === 'out' &&
              targetPortData?.scopeType === 'page' &&
              targetPortData?.direction === 'out'

            const isIframeEntryToChildEntry =
              sourcePortData?.scopeType === 'iframe' &&
              sourcePortData?.direction === 'in' &&
              targetPortData?.scopeType !== 'page' &&
              targetPortData?.parentId === sourcePortData?.scopeId &&
              targetPortData?.direction === 'in'

            const isChildExitToIframeExit =
              sourcePortData?.scopeType !== 'page' &&
              sourcePortData?.parentId === targetPortData?.scopeId &&
              sourcePortData?.direction === 'out' &&
              targetPortData?.scopeType === 'iframe' &&
              targetPortData?.direction === 'out'

            if (isPageEntryToInnerEntry || isInnerExitToPageExit || isIframeEntryToChildEntry || isChildExitToIframeExit) {
              console.log('允许：页面/iframe 共享端口与内部组件连接', {
                isPageEntryToInnerEntry,
                isInnerExitToPageExit,
                isIframeEntryToChildEntry,
                isChildExitToIframeExit
              })
              return true
            }

            // 其他情况继续后面的方向性检查
          } else {
            // 非页面节点不允许连到自己
            console.log('拒绝：源和目标是同一个节点（非页面节点）')
            return false
          }
        }

        // 定义输入端口和输出端口
        const inputPorts = [FLOW_PORT_GROUPS.in, 'in', 'top', 'left']
        const outputPorts = [FLOW_PORT_GROUPS.out, 'out', 'bottom', 'right']

        // 如果源和目标都是页面节点或操作节点，严格检查输入输出
        const isPageOrOpNode = (portGroup) => {
          return portGroup === FLOW_PORT_GROUPS.in ||
                 portGroup === FLOW_PORT_GROUPS.out ||
                 portGroup === 'in' ||
                 portGroup === 'out'
        }

        if (isPageOrOpNode(sourcePortGroup) && isPageOrOpNode(targetPortGroup)) {
          // 页面节点/操作节点之间：必须从输出连到输入
          const isSourceOut = outputPorts.includes(sourcePortGroup)
          const isTargetIn = inputPorts.includes(targetPortGroup)
          const result = isSourceOut && isTargetIn
          console.log('页面/操作节点连接:', { isSourceOut, isTargetIn, result })
          return result
        }

        // 组件节点与其他节点：更灵活的连接规则
        // 允许组件之间、组件与页面节点之间自由连接
        // 但仍然阻止明显不合理的连接（比如两个输入端口连接）
        if (sourcePortGroup === 'in' || targetPortGroup === 'out') {
          console.log('拒绝：不合理的端口组合')
          return false
        }

        console.log('允许连接')
        return true
      },
      createEdge() {
        return graph.createEdge({
          shape: 'edge',
          router: { ...STANDARD_EDGE_ROUTER },
          connector: {
            name: STANDARD_EDGE_CONNECTOR.name,
            args: { ...(STANDARD_EDGE_CONNECTOR.args || {}) }
          },
          attrs: getStandardEdgeStyle(false),
          zIndex: 1000
        })
      }
    }
  })
}

// 注册自定义节点
const registerNodes = () => {
  // 注意：page-node 已经在 registerDynamicPageNodeShape() 中注册过了
  // 不要在这里重复注册，否则会覆盖配置
  console.log('跳过页面节点注册（已在registerDynamicPageNodeShape中注册）')

  // 检查是否已注册，避免重复注册，使用 try-catch 处理已注册场景
  const registerNodeSafe = (name, config) => {
    try {
      Graph.registerNode(name, config)
    } catch (error) {
      // 如果节点已注册，先注销后重新注册
      if (error.message && error.message.includes('already registered')) {
        console.log(`节点 ${name} 已注册，先注销再重新注册`)
        Graph.unregisterNode(name)
        Graph.registerNode(name, config)
      } else {
        throw error
      }
    }
  }

  // 开始节点
  registerNodeSafe('start-node', {
    inherit: 'rect',
    width: 150,
    height: 50,
    attrs: {
      body: {
        stroke: '#52c41a',
        fill: '#f6ffed',
        rx: 25,
        ry: 25,
        strokeWidth: 2
      },
      label: {
        fontSize: 14,
        fill: '#000',
        refX: 0.5,
        refY: 0.5
      }
    },
    ports: {
      groups: {
        out: {
          position: 'right',
          markup: [{ tagName: 'circle', selector: 'portBody' }],
          attrs: {
            portBody: {
              r: 6,
              magnet: true,
              stroke: '#52c41a',
              fill: '#fff',
              strokeWidth: 2
            }
          }
        }
      },
      items: [{ group: 'out', id: 'out1' }]
    }
  })

  // 页面节点使用 Vue 组件渲染，真正可视化内容在组件内部
  // 操作节点使用普通节点配置，page-node 已通过 register 注册，无需重复注册
  registerNodeSafe('operation-node', {
    inherit: 'rect',
    width: 160,
    height: 60,
    attrs: {
      body: {
        stroke: '#faad14',
        fill: '#fffbe6',
        rx: 4,
        ry: 4,
        strokeWidth: 2
      },
      label: {
        fontSize: 14,
        fill: '#000',
        refX: 0.5,
        refY: 0.5
      }
    },
    ports: {
      groups: {
        in: {
          position: 'left',
          markup: [{ tagName: 'circle', selector: 'portBody' }],
          attrs: {
            portBody: {
              r: 6,
              magnet: true,
              stroke: '#faad14',
              fill: '#fff',
              strokeWidth: 2
            }
          }
        },
        out: {
          position: 'right',
          markup: [{ tagName: 'circle', selector: 'portBody' }],
          attrs: {
            portBody: {
              r: 6,
              magnet: true,
              stroke: '#faad14',
              fill: '#fff',
              strokeWidth: 2
            }
          }
        }
      },
      items: [
        { group: 'in', id: 'in1' },
        { group: 'out', id: 'out1' }
      ]
    }
  })

  // 结束节点
  registerNodeSafe('end-node', {
    inherit: 'rect',
    width: 150,
    height: 50,
    attrs: {
      body: {
        stroke: '#ff4d4f',
        fill: '#fff1f0',
        rx: 25,
        ry: 25,
        strokeWidth: 2
      },
      label: {
        fontSize: 14,
        fill: '#000',
        refX: 0.5,
        refY: 0.5
      }
    },
    ports: {
      groups: {
        in: {
          position: 'left',
          markup: [{ tagName: 'circle', selector: 'portBody' }],
          attrs: {
            portBody: {
              r: 6,
              magnet: true,
              stroke: '#ff4d4f',
              fill: '#fff',
              strokeWidth: 2
            }
          }
        }
      },
      items: [{ group: 'in', id: 'in1' }]
    }
  })

  // 组件节点使用 Vue 组件，并支持四向端口
  console.log('开始注册组件节点类型')

  // 定义 4 个方向端口配置
  const componentPortsConfig = {
    groups: {
      top: {
        position: 'top',
        markup: [{ tagName: 'circle', selector: 'portBody' }],
        attrs: {
          portBody: {
            r: 5,
            magnet: true,
            stroke: '#52c41a',
            fill: '#fff',
            strokeWidth: 2
          }
        }
      },
      bottom: {
        position: 'bottom',
        markup: [{ tagName: 'circle', selector: 'portBody' }],
        attrs: {
          portBody: {
            r: 5,
            magnet: true,
            stroke: '#52c41a',
            fill: '#fff',
            strokeWidth: 2
          }
        }
      },
      left: {
        position: 'left',
        markup: [{ tagName: 'circle', selector: 'portBody' }],
        attrs: {
          portBody: {
            r: 5,
            magnet: true,
            stroke: '#52c41a',
            fill: '#fff',
            strokeWidth: 2
          }
        }
      },
      right: {
        position: 'right',
        markup: [{ tagName: 'circle', selector: 'portBody' }],
        attrs: {
          portBody: {
            r: 5,
            magnet: true,
            stroke: '#52c41a',
            fill: '#fff',
            strokeWidth: 2
          }
        }
      }
    },
    items: [
      { group: 'top', id: 'port-top' },
      { group: 'bottom', id: 'port-bottom' },
      { group: 'left', id: 'port-left' },
      { group: 'right', id: 'port-right' }
    ]
  }

  // 注册各类组件节点类型
  try {
    // 输入框节点
    register({
      shape: 'input-node',
      width: 160,
      height: 80,
      component: ComponentNode,
      ports: componentPortsConfig
    })

    // 按钮节点
    register({
      shape: 'button-node',
      width: 140,
      height: 70,
      component: ComponentNode,
      ports: componentPortsConfig
    })

    // 下拉框节点
    register({
      shape: 'select-node',
      width: 160,
      height: 80,
      component: ComponentNode,
      ports: componentPortsConfig
    })

    // 复选框节点
    register({
      shape: 'checkbox-node',
      width: 140,
      height: 60,
      component: ComponentNode,
      ports: componentPortsConfig
    })

    ;['radio', 'tab', 'menuitem', 'clickable', 'file'].forEach(type => {
      register({
        shape: `${type}-node`,
        width: type === 'file' ? 160 : 140,
        height: type === 'file' ? 70 : 60,
        component: ComponentNode,
        ports: componentPortsConfig
      })
    })

    // 链接节点
    register({
      shape: 'link-node',
      width: 130,
      height: 60,
      component: ComponentNode,
      ports: componentPortsConfig
    })

    console.log('所有组件节点类型注册成功')
  } catch (error) {
    console.error('注册组件节点失败:', error)
  }
}

const selectFlowNode = (node, componentId = '') => {
  if (!node) return

  resetSelectedEdgeStyle()
  selectedEdge.value = null
  selectedExecutionStepIndex.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  const hasComponentSelection = Boolean(componentId)
  selectedInnerComponentId.value = hasComponentSelection ? componentId : null

  const data = node.getData() || {}
  const nodeType = data.type || (node.shape || '').replace(/-node$/, '')

  if (nodeType === 'component') {
    selectedNode.value = {
      id: node.id,
      type: nodeType,
      componentType: data.componentType,
      config: data.config || {}
    }
    activeInnerComponentId.value = null
    selectedInnerComponentId.value = null
    activeDetailMenu.value = 'component'
    return
  }

  const defaultConfig = nodeDefaults[nodeType] ? { ...nodeDefaults[nodeType] } : {}
  const config = ensureNodeIOConfig({ ...defaultConfig, ...(data.config || {}) })
  if (nodeType === 'start') {
    ensureStartNodeConfig(config)
  }
  if (nodeType === 'page') {
    ensurePageNodeConfig(config)
    normalizeInnerComponents(config)
  }

  selectedNode.value = {
    id: node.id,
    type: nodeType,
    config
  }

  if (nodeType === 'page') {
    activeInnerComponentId.value = hasComponentSelection ? componentId : ''
    selectedInnerComponentId.value = hasComponentSelection ? componentId : null
    activeDetailMenu.value = hasComponentSelection ? 'component' : 'node'
  } else {
    activeInnerComponentId.value = null
    selectedInnerComponentId.value = null
    activeDetailMenu.value = 'node'
  }
}

const handleEmbeddedPageNodeSelect = (event) => {
  const nodeId = event?.detail?.nodeId
  if (!nodeId || !graph) return

  const node = graph.getCellById(nodeId)
  selectFlowNode(node, event.detail?.componentId || '')
}

const handleEmbeddedExecutionStepSelect = (event) => {
  const nodeId = event?.detail?.nodeId
  const stepIndex = Number(event?.detail?.stepIndex)
  if (!nodeId || !Number.isInteger(stepIndex) || !graph) {
    return
  }

  const node = graph.getCellById(nodeId)
  selectFlowNode(node)
  selectExecutionStep(stepIndex)
}

// 设置事件监听
const setupEvents = () => {
  // 节点选中事件
  graph.on('node:click', ({ node }) => {
    console.log('节点被点击:', node.id)
    const data = node.getData()
    console.log('节点数据:', data)
    console.log('节点类型:', data?.type)
    console.log('默认配置:', nodeDefaults[data?.type])
    selectFlowNode(node)
    console.log('设置selectedNode:', selectedNode.value)
  })

  graph.on('edge:click', ({ edge }) => {
    selectGraphEdge(edge)
  })

  // 画布点击事件，用于取消选中
  graph.on('blank:click', () => {
    clearSelection()
  })

  // 双击节点编辑
  graph.on('node:dblclick', ({ node }) => {
    // 如有需要，可在这里扩展更复杂的编辑交互
  })

  // 修复：将端口容器移到foreignObject之上
  const fixPortLayering = (node) => {
    setTimeout(() => {
      const nodeData = node.getData()
      if (nodeData?.type === 'page' || nodeData?.type === 'component') {
        const nodeEl = containerRef.value.querySelector(`[data-cell-id="${node.id}"]`)
        if (nodeEl) {
          // 查找端口容器 - X6 使用 data-port-group-node-id 属性
          const portsContainers = nodeEl.querySelectorAll('[data-port-group-node-id], .x6-graph-svg-ports, g[data-type="port-container"]')
          portsContainers.forEach(container => {
            // 将端口容器移到最后（SVG中最后的元素渲染在最上层）
            nodeEl.appendChild(container)
          })
          if (expandedExecutionResultKeysByNode.has(node.id)) {
            setPageNodePortsVisible(node.id, false)
          }
          if (portsContainers.length > 0) {
            console.log(`已调整节点 ${node.id} 的端口层级，共 ${portsContainers.length} 个容器`)
          }
        }
      }
    }, 100)
  }

  graph.on('node:added', ({ node }) => {
    fixPortLayering(node)
    markGeneratedScriptStale()
  })

  // 端口改变时也需要调整层级
  graph.on('node:port:added', ({ node }) => {
    fixPortLayering(node)
  })

  graph.on('node:change:ports', ({ node }) => {
    fixPortLayering(node)
  })

  graph.on('node:change:size', ({ node }) => {
    markGeneratedScriptStale()
    if (node.getData()?.type === 'page') {
      syncPageNodePorts(node)
      refreshPageNodeView(node, { syncPorts: false, delay: 80 })
      refreshConnectedEdges(node)
    }
  })

  graph.on('node:change:position', ({ node }) => {
    markGeneratedScriptStale()
    if (node.getData()?.type === 'page') {
      refreshConnectedEdges(node)
    }
  })

  // 监听节点数据变化，用于同步组件拖动后的端口位置
  graph.on('node:change:data', ({ node, current, previous }) => {
    markGeneratedScriptStale()
    const nodeData = node.getData()
    if (nodeData?.type === 'page') {
      // 检查是否是组件位置变化
      const currentComponents = current?.config?.innerComponents || []
      const previousComponents = previous?.config?.innerComponents || []

      // 简单检查：如果组件数量相同，可能是位置更新
      if (currentComponents.length === previousComponents.length && currentComponents.length > 0) {
        // 检查是否有位置变化
        let positionChanged = false
        for (let i = 0; i < currentComponents.length; i++) {
          const curr = currentComponents[i]
          const prev = previousComponents[i]
          if (curr.id === prev.id) {
            if (
              curr.position?.x !== prev.position?.x ||
              curr.position?.y !== prev.position?.y ||
              curr.parentId !== prev.parentId ||
              curr.size?.width !== prev.size?.width ||
              curr.size?.height !== prev.size?.height
            ) {
              positionChanged = true
              break
            }
          }
        }

        // 如果位置变化，同步端口
        if (positionChanged) {
          syncPageNodePorts(node)
          refreshPageNodeView(node, { syncPorts: false, delay: 0 })
          refreshConnectedEdges(node)
        }
      }
    }
  })

  // 调试：监听端口进入事件
  graph.on('node:port:mouseenter', ({ port, node }) => {
    const portData = node.getPort(port)
    console.log('鼠标进入端口:', {
      nodeId: node.id,
      nodeType: node.getData()?.type,
      portId: port,
      portGroup: portData?.group,
      portData
    })
  })

  // 调试：监听端口离开事件
  graph.on('node:port:mouseleave', ({ port, node }) => {
    console.log('鼠标离开端口:', {
      nodeId: node.id,
      portId: port
    })
  })

  // 调试：监听连线移动事件
  graph.on('edge:moving', ({ e, x, y, edge }) => {
    console.log('连线正在移动:', { x, y, edgeId: edge?.id })
  })

  // 调试：监听连线添加事件
  graph.on('edge:added', ({ edge }) => {
    markGeneratedScriptStale()
    console.log('连线被添加到画布:', {
      edgeId: edge.id,
      source: edge.getSourceCellId(),
      target: edge.getTargetCellId(),
      sourcePort: edge.getSourcePortId(),
      targetPort: edge.getTargetPortId()
    })
  })

  // 调试：监听连线鼠标悬停事件
  graph.on('edge:mouseenter', ({ edge }) => {
    console.log('鼠标悬停在连线上:', { edgeId: edge.id })
  })

  // 调试：监听节点鼠标移动事件
  graph.on('node:mousemove', ({ node, e }) => {
    // 检查鼠标是否在端口上
    const target = e.target
    if (target && target.hasAttribute && target.hasAttribute('port')) {
      console.log('鼠标在端口上移动:', {
        nodeId: node.id,
        portId: target.getAttribute('port'),
        portGroup: target.getAttribute('port-group'),
        hasMagnet: target.getAttribute('magnet'),
        tagName: target.tagName,
        className: target.getAttribute('class')
      })
    }
  })

  // 调试函数：打印节点的所有端口信息
  window.debugPorts = (nodeId) => {
    const node = graph.getCellById(nodeId)
    if (!node) {
      console.error('节点不存在:', nodeId)
      return
    }
    const ports = node.getPorts()
    const nodeData = node.getData()
    console.log(`节点 ${nodeId} 的信息:`)
    console.log('- 节点类型:', nodeData?.type)
    console.log('- 端口总数:', ports.length)

    // 按端口组分类
    const portsByGroup = {}
    ports.forEach(port => {
      const group = port.group || 'unknown'
      if (!portsByGroup[group]) {
        portsByGroup[group] = []
      }
      portsByGroup[group].push(port)
    })

    console.log('- 端口分组:')
    Object.keys(portsByGroup).forEach(group => {
      console.log(`  ${group}: ${portsByGroup[group].length} 个端口`)
      portsByGroup[group].forEach(port => {
        const portEl = containerRef.value.querySelector(`[port="${port.id}"]`)
        console.log(`    - ${port.id}:`, {
          group: port.group,
          args: port.args,
          hasDOM: !!portEl,
          DOMattrs: portEl ? {
            magnet: portEl.getAttribute('magnet'),
            portGroup: portEl.getAttribute('port-group'),
            tagName: portEl.tagName
          } : null
        })
      })
    })
  }

  // 调试函数：列出所有页面节点
  window.listPageNodes = () => {
    const nodes = graph.getNodes()
    const pageNodes = nodes.filter(n => n.getData()?.type === 'page')
    console.log(`找到 ${pageNodes.length} 个页面节点:`)
    pageNodes.forEach(node => {
      console.log(`- ${node.id}:`, {
        ports: node.getPorts().length,
        components: node.getData()?.config?.innerComponents?.length || 0
      })
    })
    return pageNodes.map(n => n.id)
  }

  // 调试函数：检查节点的 SVG 结构
  window.inspectNodeStructure = (nodeId) => {
    const nodeEl = containerRef.value.querySelector(`[data-cell-id="${nodeId}"]`)
    if (!nodeEl) {
      console.error('节点 DOM 不存在:', nodeId)
      return
    }

    console.log(`节点 ${nodeId} 的 SVG 结构:`)
    console.log('完整元素:', nodeEl)

    const children = Array.from(nodeEl.children)
    console.log(`子元素数量: ${children.length}`)

    children.forEach((child, index) => {
      const rect = child.getBoundingClientRect()
      console.log(`[${index}] ${child.tagName}:`, {
        class: child.getAttribute('class'),
        pointerEvents: window.getComputedStyle(child).pointerEvents,
        zIndex: window.getComputedStyle(child).zIndex,
        width: rect.width,
        height: rect.height,
        visible: rect.width > 0 && rect.height > 0
      })
    })

    // 检查端口容器
    const portsContainer = nodeEl.querySelector('.x6-graph-svg-ports')
    if (portsContainer) {
      console.log('端口容器找到:', {
        portCount: portsContainer.children.length,
        pointerEvents: window.getComputedStyle(portsContainer).pointerEvents,
        zIndex: window.getComputedStyle(portsContainer).zIndex
      })
    } else {
      console.warn('端口容器未找到')
    }

    return nodeEl
  }

  // 调试函数：检查端口的可交互性
  window.checkPortInteraction = (portId) => {
    const portEl = containerRef.value.querySelector(`[port="${portId}"]`)
    if (!portEl) {
      console.error('端口 DOM 元素不存在:', portId)
      return
    }

    const rect = portEl.getBoundingClientRect()
    const styles = window.getComputedStyle(portEl)
    const parentStyles = window.getComputedStyle(portEl.parentElement)

    console.log(`端口 ${portId} 的交互性检查:`)
    console.log('- 位置和尺寸:', {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      visible: rect.width > 0 && rect.height > 0
    })
    console.log('- 样式:', {
      pointerEvents: styles.pointerEvents,
      display: styles.display,
      visibility: styles.visibility,
      opacity: styles.opacity,
      zIndex: styles.zIndex
    })
    console.log('- 父元素样式:', {
      pointerEvents: parentStyles.pointerEvents,
      overflow: parentStyles.overflow
    })
    console.log('- 元素:', portEl)

    // 检查该位置是否有其他元素覆盖
    const centerX = rect.x + rect.width / 2
    const centerY = rect.y + rect.height / 2
    const elementAtPoint = document.elementFromPoint(centerX, centerY)
    console.log('- 该位置的最顶层元素:', elementAtPoint)
    console.log('- 是否是端口本身:', elementAtPoint === portEl)
  }

  // 连线完成事件
  graph.on('edge:connected', ({ edge }) => {
    markGeneratedScriptStale()
    const sourceNode = edge.getSourceNode()
    const targetNode = edge.getTargetNode()
    const sourcePort = edge.getSourcePortId()
    const targetPort = edge.getTargetPortId()

    console.log('连线完成:', {
      source: sourceNode?.id,
      target: targetNode?.id,
      sourcePort,
      targetPort
    })

    applyStandardEdgeStyle(edge)
    ensureEdgeVisible(edge)

    // 如果连接的是元素端口，则附加动作标签
    if (
      sourceNode?.id !== targetNode?.id &&
      sourcePort?.startsWith('element-') &&
      targetPort?.startsWith('element-')
    ) {
      edge.setLabels([{
        attrs: {
          text: {
            text: sourceNode?.getPort(sourcePort)?.data?.action || 'next',
            fill: '#fff',
            fontSize: 12
          },
          rect: {
            fill: '#1890ff',
            stroke: '#096dd9',
            strokeWidth: 1,
            rx: 4,
            ry: 4,
            refWidth: '100%',
            refHeight: '100%',
            refX: 0,
            refY: 0
          }
        },
        position: {
          distance: 0.5
        }
      }])
    }
  })

  // 边被移除事件
  graph.on('edge:removed', ({ edge }) => {
    markGeneratedScriptStale()
    if (selectedEdge.value?.id === edge.id) {
      selectedEdge.value = null
    }

    const sourceNode = edge.getSourceNode()
    const targetNode = edge.getTargetNode()
    const sourcePort = edge.getSourcePortId()
    const targetPort = edge.getTargetPortId()

    if (isEnhancedPageFlowEdge(sourceNode, targetNode, sourcePort, targetPort)) {
      return
    }

    if (sourceNode && sourceNode?.id !== targetNode?.id && sourcePort?.startsWith('element-')) {
      removeFromExecutionPath(sourceNode, sourcePort, targetPort)
    }
  })
}

// 更新执行路径
const updateExecutionPath = (node, sourcePort, targetPort) => {
  const data = node.getData()
  if (!data.config) data.config = {}
  if (!data.config.executionPath) data.config.executionPath = []

  const sourcePortData = node.getPort(sourcePort)?.data
  const targetPortData = node.getPort(targetPort)?.data

  if (sourcePortData && targetPortData) {
    data.config.executionPath = data.config.executionPath.filter(
      step => !(step.from.portId === sourcePort && step.to.portId === targetPort)
    )
    data.config.executionPath.push({
      from: {
        portId: sourcePort,
        componentId: sourcePortData.componentId,
        componentType: sourcePortData.componentType,
        elementId: sourcePortData.elementId,
        elementType: sourcePortData.elementType,
        elementText: sourcePortData.elementText
      },
      to: {
        portId: targetPort,
        componentId: targetPortData.componentId,
        componentType: targetPortData.componentType,
        elementId: targetPortData.elementId,
        elementType: targetPortData.elementType,
        elementText: targetPortData.elementText
      },
      action: 'click' // 默认动作
    })

    node.setData(data)

    // 如果当前选中的是这个节点，更新selectedNode
    if (selectedNode.value?.id === node.id) {
      selectedNode.value.config = data.config
    }
  }
}

// 从执行路径中移除
const removeFromExecutionPath = (node, sourcePort, targetPort) => {
  const data = node.getData()
  if (!data.config?.executionPath) return

  data.config.executionPath = data.config.executionPath.filter(
    step => !(step.from.portId === sourcePort && step.to.portId === targetPort)
  )

  node.setData(data)

  if (selectedNode.value?.id === node.id) {
    selectedNode.value.config = data.config
  }
}

// 开始拖拽节点
const startDrag = (event, nodeType) => {
  // 阻止默认行为，防止文本选择
  event.preventDefault()

  // 在工具栏按下鼠标后，准备开始拖拽
  const startDnd = (e) => {
    const { clientX, clientY } = e

    // 创建拖拽中的节点副本
    const dndNode = graph.addNode({
      shape: `${nodeType}-node`,
      x: clientX,
      y: clientY,
      label: nodeDefaults[nodeType].name,
      data: {
        type: nodeType,
        config: { ...nodeDefaults[nodeType] }
      }
    })

    // 监听鼠标移动
    const handleMouseMove = (moveEvent) => {
      const { x, y } = graph.clientToLocal(moveEvent.clientX, moveEvent.clientY)
      dndNode.setPosition(x - 75, y - 40)
    }

    // 监听鼠标释放
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      if (nodeType === 'page') {
        syncPageNodePorts(dndNode)
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  startDnd({ clientX: 0, clientY: 0 })
}

// ==================== 组件拖拽相关函数 ====================

// 获取组件拖拽预览 HTML
const getComponentPreviewHTML = (type) => {
  const previewMap = {
    'input': '<div class="preview-input">📝 输入框</div>',
    'button': '<div class="preview-button">🔘 按钮</div>',
    'select': '<div class="preview-select">📋 下拉框</div>',
    'checkbox': '<div class="preview-checkbox">☑️ 复选框</div>',
    'radio': '<div class="preview-checkbox">◉ 单选框</div>',
    'link': '<div class="preview-link">🔗 链接</div>',
    'tab': '<div class="preview-button">标签页</div>',
    'menuitem': '<div class="preview-button">菜单项</div>',
    'clickable': '<div class="preview-button">可点击元素</div>',
    'file': '<div class="preview-select">文件上传</div>',
    'iframe': '<div class="preview-select">Iframe 容器</div>'
  }
  return previewMap[type] || '<div>组件</div>'
}

// 获取鼠标位置下的页面节点
const getPageNodeAtPoint = (clientX, clientY) => {
  const point = graph.clientToLocal(clientX, clientY)
  const nodes = graph.getNodesFromPoint(point.x, point.y)
  return nodes.find(node => node.getData()?.type === 'page')
}

const getPageNodeView = (nodeOrId) => {
  if (!graph || !nodeOrId) {
    return null
  }

  return graph.findViewByCell(typeof nodeOrId === 'string' ? nodeOrId : nodeOrId.id)
}

// 高亮页面节点
const highlightPageNode = (node, highlight) => {
  const view = getPageNodeView(node)
  if (!view) {
    return
  }

  if (highlight) {
    view.addClass('drop-target-highlight')
    highlightedPageNodeId.value = node.id
    return
  }

  view.removeClass('drop-target-highlight')
  if (highlightedPageNodeId.value === node.id) {
    highlightedPageNodeId.value = null
  }
}

// 清除所有高亮
const clearAllHighlights = () => {
  if (highlightedPageNodeId.value) {
    const highlightedView = getPageNodeView(highlightedPageNodeId.value)
    highlightedView?.removeClass('drop-target-highlight')
    highlightedPageNodeId.value = null
  }
}

// 开始拖拽组件
const startComponentDrag = (event, componentType) => {
  // 阻止默认行为，防止文本选择
  event.preventDefault()

  console.log('开始拖拽组件:', componentType)

  // 创建拖拽预览元素
  const preview = document.createElement('div')
  preview.className = `drag-preview drag-preview-${componentType}`
  preview.innerHTML = getComponentPreviewHTML(componentType)
  preview.style.cssText = `
    position: fixed;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.8;
    transform: translate(-50%, -50%);
  `
  document.body.appendChild(preview)

  // 监听鼠标移动
  const handleMouseMove = (e) => {
    preview.style.left = e.clientX + 'px'
    preview.style.top = e.clientY + 'px'

    // 检测当前是否悬停在页面节点上
    const pageNode = getPageNodeAtPoint(e.clientX, e.clientY)
    if (pageNode) {
      if (highlightedPageNodeId.value !== pageNode.id) {
        clearAllHighlights()
        highlightPageNode(pageNode, true)
      }
    } else {
      clearAllHighlights()
    }
  }

  // 监听鼠标释放
  const handleMouseUp = (e) => {
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
    document.body.removeChild(preview)

    // 检查释放位置是否位于页面节点中
    const pageNode = getPageNodeAtPoint(e.clientX, e.clientY)
    if (pageNode) {
      handleComponentDrop(pageNode, e, componentType)
    }

    clearAllHighlights()
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const FLOW_COMPONENT_DROP_MARGIN = 24

const buildLocalRectFromCenter = (centerX, centerY, size) => ({
  left: centerX - size.width / 2,
  top: centerY - size.height / 2,
  width: size.width,
  height: size.height,
  right: centerX + size.width / 2,
  bottom: centerY + size.height / 2
})

const resizePageNodeIfNeeded = (pageNode, rect, nodeSize = pageNode.getSize(), margin = FLOW_COMPONENT_DROP_MARGIN) => {
  const pageInnerRect = getPageInnerRect(nodeSize)
  const overflowRight = rect.right + margin - pageInnerRect.right
  const overflowBottom = rect.bottom + margin - pageInnerRect.bottom

  if (overflowRight <= 0 && overflowBottom <= 0) {
    return nodeSize
  }

  const nextSize = {
    width: Math.ceil(nodeSize.width + Math.max(0, overflowRight)),
    height: Math.ceil(nodeSize.height + Math.max(0, overflowBottom))
  }
  pageNode.resize(nextSize.width, nextSize.height)
  return nextSize
}

const prepareComponentDropLayout = (pageNode, pageData, componentType, localX, localY) => {
  let nodeSize = pageNode.getSize()
  let iframeTarget = findIframeDropTarget(pageData.config.innerComponents || [], nodeSize, localX, localY)
  const componentSize = getComponentSize(componentType)
  const droppedRect = buildLocalRectFromCenter(localX, localY, componentSize)

  if (iframeTarget?.component) {
    const parentComponent = pageData.config.innerComponents.find(component => component.id === iframeTarget.component.id)
    if (parentComponent) {
      const overflowRight = droppedRect.right + FLOW_COMPONENT_DROP_MARGIN - iframeTarget.innerRect.right
      const overflowBottom = droppedRect.bottom + FLOW_COMPONENT_DROP_MARGIN - iframeTarget.innerRect.bottom

      if (overflowRight > 0 || overflowBottom > 0) {
        const parentSize = getComponentSize(parentComponent)
        parentComponent.size = {
          width: Math.ceil(parentSize.width + Math.max(0, overflowRight)),
          height: Math.ceil(parentSize.height + Math.max(0, overflowBottom))
        }
        pageNode.setData(buildPageNodeDataPayload(pageData), { overwrite: true })
        refreshPageNodeView(pageNode, { syncPorts: true, delay: 80 })
      }
    }

    nodeSize = pageNode.getSize()
    const layouts = buildComponentLayouts(pageData.config.innerComponents || [], nodeSize)
    const expandedIframeLayout = layouts.find(layout => layout.component.id === iframeTarget.component.id)
    if (expandedIframeLayout?.rect) {
      nodeSize = resizePageNodeIfNeeded(pageNode, expandedIframeLayout.rect, nodeSize)
      iframeTarget = findIframeDropTarget(pageData.config.innerComponents || [], nodeSize, localX, localY) || expandedIframeLayout
    }
  } else {
    nodeSize = resizePageNodeIfNeeded(pageNode, droppedRect, nodeSize)
  }

  const targetRect = iframeTarget?.innerRect || getPageInnerRect(nodeSize)
  return {
    parentId: iframeTarget?.component?.id || null,
    targetRect
  }
}

// 处理组件释放到页面节点
const handleComponentDrop = (pageNode, event, componentType) => {
  console.log('组件释放到页面节点:', pageNode.id)

  // 检查页面节点是否已加载快照数据
  const pageData = pageNode.getData()
  if (!pageData?.config?.snapshotData) {
    ElMessage.warning('请先为页面节点加载快照文件')
    return
  }

  // 计算组件在页面节点内部的相对位置
  const pageNodeBBox = pageNode.getBBox()
  const dropPoint = graph.clientToLocal(event.clientX, event.clientY)
  const localX = dropPoint.x - pageNodeBBox.x
  const localY = dropPoint.y - pageNodeBBox.y
  const dropLayout = prepareComponentDropLayout(pageNode, pageData, componentType, localX, localY)
  const targetRect = dropLayout.targetRect

  // 转换为相对位置百分比
  const relativeX = ((localX - targetRect.left) / targetRect.width) * 100
  const relativeY = ((localY - targetRect.top) / targetRect.height) * 100

  // 显示组件配置对话框
  showComponentConfigDialog({
    pageNode: pageNode,
    componentType: componentType,
    parentId: dropLayout.parentId,
    position: { x: relativeX, y: relativeY }
  })
}

// 获取组件类型名称
const getComponentTypeNameLegacy = (type) => {
  return getFlowComponentTypeName(type)
  /*
  const nameMap = {
    'input': '输入框',
    'button': '按钮',
    'select': '下拉框',
    'checkbox': '复选框',
    'link': '链接'
  }
  return nameMap[type] || type
  */
}

// 判断元素是否与组件类型兼容
const isElementCompatible = isFlowElementCompatible

// 获取已映射的元素ID列表
const getMappedElementIds = (pageNode, excludeComponentId = null) => {
  const data = pageNode.getData()
  const innerComponents = data?.config?.innerComponents || []
  return innerComponents
    .filter(component => component.id !== excludeComponentId)
    .map(component => component.elementId)
    .filter(Boolean)
}

const getEditableElementsForComponent = (component) => {
  if (!selectedNode.value?.config?.snapshotData) {
    return []
  }

  const pageNode = graph?.getCellById(selectedNode.value.id)
  const mappedElementIds = pageNode ? getMappedElementIds(pageNode, component.id) : []
  const parentComponent = selectedNode.value.config?.innerComponents?.find(item => item.id === component.parentId)
  const mappedIframeComponents = (selectedNode.value.config?.innerComponents || []).filter(item => item.type === 'iframe' && item.id !== component.id)

  return selectedNode.value.config.snapshotData.interactiveElements.filter(element => {
    if (!isElementCompatible(element, component.type)) {
      return false
    }

    if (mappedElementIds.includes(element.id) && element.id !== component.elementId) {
      return false
    }

    if (parentComponent?.elementId) {
      return isElementInsideElement(element, parentComponent.elementId) || element.id === component.elementId
    }

    if (component.type !== 'iframe') {
      return !mappedIframeComponents.some(item => item.elementId && isElementInsideElement(element, item.elementId))
    }

    return true
  })
}

const setActiveInnerComponent = (componentId) => {
  activeInnerComponentId.value = componentId
  selectedInnerComponentId.value = componentId
  selectedExecutionStepIndex.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  activeDetailMenu.value = 'component'
  resetSelectedEdgeStyle()
  selectedEdge.value = null
}

const moveInnerComponent = (componentId, direction) => {
  if (!selectedNode.value?.config?.innerComponents?.length) {
    return
  }

  const components = [...selectedNode.value.config.innerComponents]
  const currentIndex = components.findIndex(component => component.id === componentId)
  const targetIndex = currentIndex + direction

  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= components.length) {
    return
  }

  const [currentComponent] = components.splice(currentIndex, 1)
  components.splice(targetIndex, 0, currentComponent)
  selectedNode.value.config.innerComponents = components.map((component, index) => ({
    ...component,
    order: index,
    zIndex: index
  }))

  activeInnerComponentId.value = componentId
  selectedInnerComponentId.value = componentId
  updateNodeConfig()
}

const removeInnerComponent = (componentId) => {
  if (!selectedNode.value?.config?.innerComponents) {
    return
  }

  const currentComponents = selectedNode.value.config.innerComponents
  if (!currentComponents.some(component => component.id === componentId)) {
    return
  }

  const removedIds = new Set([componentId])
  let hasChildren = true

  while (hasChildren) {
    hasChildren = false
    selectedNode.value.config.innerComponents.forEach(component => {
      if (component.parentId && removedIds.has(component.parentId) && !removedIds.has(component.id)) {
        removedIds.add(component.id)
        hasChildren = true
      }
    })
  }

  selectedNode.value.config.innerComponents = selectedNode.value.config.innerComponents
    .filter(component => !removedIds.has(component.id))
    .map((component, index) => ({
      ...component,
      order: index,
      zIndex: index
    }))

  if (Array.isArray(selectedNode.value.config.executionPath)) {
    selectedNode.value.config.executionPath = selectedNode.value.config.executionPath.filter(step => {
      return !removedIds.has(step?.from?.componentId) && !removedIds.has(step?.to?.componentId)
    })
  }

  selectedInnerComponentId.value = null
  selectedExecutionStepIndex.value = null
  syncActiveInnerComponent({ keepEmpty: true })
  updateNodeConfig()
  ElMessage.success('组件已删除')
}

const handleActiveComponentElementChange = (elementId) => {
  if (!activeInnerComponent.value || !selectedNode.value?.config) {
    return
  }

  activeInnerComponent.value.elementId = elementId
  activeInnerComponent.value.elementData = getSnapshotElementById(selectedNode.value.config, elementId)
  updateNodeConfig()
}

const updateActiveInnerComponent = () => {
  if (!activeInnerComponent.value) {
    return
  }

  const defaultConfig = buildComponentDefaultConfig(activeInnerComponent.value.type)
  activeInnerComponent.value.config = {
    ...defaultConfig,
    ...(activeInnerComponent.value.config || {})
  }
  updateNodeConfig()
}

// 显示配置对话框
const showComponentConfigDialog = ({ pageNode, componentType, position, parentId = null }) => {
  currentComponentConfig.value = {
    pageNodeId: pageNode.id,
    type: componentType,
    elementId: null,
    parentId,
    position: {
      x: clampPosition(position.x, 6, 94),
      y: clampPosition(position.y, 8, 92)
    },
    ...buildComponentDefaultConfig(componentType)
  }

  componentConfigDialogVisible.value = true
}

// 确认组件配置
const confirmComponentConfig = () => {
  if (!currentComponentConfig.value.elementId) {
    ElMessage.warning('请选择要映射的元素')
    return
  }

  // 获取完整的元素数据
  const pageNode = graph.getCellById(currentComponentConfig.value.pageNodeId)
  const snapshotData = pageNode.getData()?.config?.snapshotData
  const elementData = snapshotData.interactiveElements.find(
    el => el.id === currentComponentConfig.value.elementId
  )

  // 将组件添加到页面节点
  const componentId = addComponentToPageNode(pageNode, {
    ...currentComponentConfig.value,
    elementData: elementData
  })

  componentConfigDialogVisible.value = false
  activeInnerComponentId.value = componentId
  selectedInnerComponentId.value = componentId
  ElMessage.success('组件添加成功')
}

// 添加组件到页面节点
const addComponentToPageNode = (pageNode, componentConfig) => {
  const data = pageNode.getData()
  if (!data.config) data.config = {}
  ensurePageNodeConfig(data.config)
  normalizeInnerComponents(data.config)
  const {
    pageNodeId,
    type,
    elementId,
    parentId,
    position,
    elementData,
    ...componentOptions
  } = componentConfig

  // 创建组件对象
  const component = {
    id: `component_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
    type: componentConfig.type,
    parentId: componentConfig.parentId || null,
    elementId: componentConfig.elementId,
    elementData: componentConfig.elementData,
    position: {
      x: clampPosition(componentConfig.position?.x, 6, 94),
      y: clampPosition(componentConfig.position?.y, 8, 92)
    },
    zIndex: data.config.innerComponents.length,
    order: data.config.innerComponents.length,
    config: {
      ...buildComponentDefaultConfig(componentConfig.type),
      ...componentOptions,
      action: componentOptions.action || getDefaultComponentAction(componentConfig.type)
    }
  }

  data.config.innerComponents.push(component)
  normalizeInnerComponents(data.config)
  const nextData = buildPageNodeDataPayload(data)
  pageNode.setData(nextData, { overwrite: true })
  refreshPageNodeView(pageNode, { syncPorts: true })

  // 如果当前正在编辑这个页面节点，同步刷新 selectedNode
  if (selectedNode.value?.id === pageNode.id) {
    selectedNode.value.config = nextData.config
  }

  return component.id
}

// ==================== 组件拖拽相关函数结束 ====================

// 更新节点配置
const updateNodeConfig = () => {
  const node = graph.getCellById(selectedNode.value.id)
  if (node) {
    if (selectedNode.value.type !== 'component') {
      ensureNodeIOConfig(selectedNode.value.config)
    }
    if (selectedNode.value.type === 'start') {
      ensureStartNodeConfig(selectedNode.value.config)
    }
    if (selectedNode.value.type === 'page') {
      ensurePageNodeConfig(selectedNode.value.config)
      normalizeInnerComponents(selectedNode.value.config)
    }
    console.log('updateNodeConfig called')
    console.log('节点类型:', selectedNode.value.type)
    console.log('节点shape:', node.shape)
    console.log('是否包含快照数据:', !!selectedNode.value.config.snapshotData)

    // 对于 Vue Shape 节点，直接更新 data 即可触发 Vue 响应式刷新
    const newData = {
      type: selectedNode.value.type,
      config: selectedNode.value.config
    }

    // 组件节点需要保留 componentType
    if (selectedNode.value.componentType) {
      newData.componentType = selectedNode.value.componentType
    }

    node.setData(newData, { overwrite: true })

    // 页面节点加载了快照后，需要同步内部组件端口
    if (selectedNode.value.type === 'page' && selectedNode.value.config.snapshotData) {
      console.log('页面节点已加载快照数据，触发端口同步')
      refreshPageNodeView(node, { syncPorts: true, delay: 100 })
    } else if (selectedNode.value.type !== 'page' && selectedNode.value.type !== 'component') {
      // 更新普通节点标签
      node.setAttrByPath('label/text', selectedNode.value.config.name)
    }
  }
}

// 更新页面节点端口
const updatePageNodePorts = (node) => {
  const data = node.getData()
  const innerComponents = data?.config?.innerComponents || []

  const currentPorts = node.getPorts()
  currentPorts.forEach(port => {
    if (port.group === 'element') {
      node.removePort(port.id)
    }
  })

  if (innerComponents.length === 0) {
    return
  }

  const nodeSize = node.getSize()
  const headerHeight = 58
  const footerHeight = 34
  const paddingX = 20
  const paddingY = 16
  const usableWidth = Math.max(nodeSize.width - paddingX * 2, 40)
  const usableHeight = Math.max(nodeSize.height - headerHeight - footerHeight - paddingY * 2, 40)

  innerComponents.forEach(component => {
    node.addPort({
      id: `component-${component.id}`,
      group: 'element',
      // 不指定 markup 和 attrs，使用端口组的默认配置
      args: {
        x: paddingX + (clampPosition(component.position?.x, 6, 94) / 100) * usableWidth,
        y: headerHeight + paddingY + (clampPosition(component.position?.y, 8, 92) / 100) * usableHeight
      },
      data: {
        componentId: component.id,
        componentType: component.type,
        elementId: component.elementId,
        elementType: component.elementData?.type || component.type,
        elementText: getComponentDisplayText(component),
        action: component.config?.action || getDefaultComponentAction(component.type)
      }
    })
  })
  return

  const snapshotData = data?.config?.snapshotData

  if (!snapshotData || !snapshotData.interactiveElements) {
    console.log('updatePageNodePorts: skip without snapshot data')
    return
  }

  console.log('updatePageNodePorts: start sync ports')

  // 移除旧的元素端口
  const existingPorts = node.getPorts()
  existingPorts.forEach(port => {
    if (port.group === 'element') {
      node.removePort(port.id)
    }
  })

  // 元素类型判断函数，与 PageNodeContent.vue 保持一致
  const isInputElement = (element) => {
    return ['textbox', 'input', 'searchbox'].includes(element.type)
  }
  const isSelectElement = (element) => {
    return ['select', 'combobox', 'listbox'].includes(element.type)
  }
  const isLinkElement = (element) => {
    return ['link', 'a'].includes(element.type)
  }

  // 过滤可交互元素，与 PageNodeContent.vue 保持一致，并排除 img 和 generic
  const filteredElements = snapshotData.interactiveElements.filter(element => {
    const type = element.type?.toLowerCase() || ''
    // 排除 img 类型
    if (type === 'img' || type === 'image') {
      return false
    }
    // 排除没有明确类型的 generic 元素
    if (!isInputElement(element) &&
        !isSelectElement(element) &&
        !isLinkElement(element) &&
        type !== 'button' &&
        type !== 'checkbox') {
      return false
    }
    return true
  })

  // 为每个可交互元素添加端口，最多 10 个
  const elements = filteredElements.slice(0, 10)
  elements.forEach((element, index) => {
    const portId = `element-${element.id}`

    // 计算端口位置，按 Vue 节点内容区布局
    // Header 高度: 约 40px
    // Body padding-top: 8px
    // 每个元素高度: 约 32px（包含 6px margin-bottom）
    const headerHeight = 40
    const bodyPadding = 8
    const elementHeight = 32

    // 端口位于元素垂直中心
    const y = headerHeight + bodyPadding + (index * elementHeight) + (elementHeight / 2)
    // 端口 x 位置按组件宽度约 270px 计算
    const x = 270

    console.log(`元素 ${index + 1} "${element.text || element.type}" 端口位置: x=${x}, y=${y}`)

    node.addPort({
      id: portId,
      group: 'element',
      // 不指定 markup 和 attrs，使用端口组的默认配置
      args: {
        x: x,
        y: y
      },
      data: {
        elementId: element.id,
        elementType: element.type,
        elementText: element.text
      }
    })
  })

  console.log(`共添加 ${elements.length} 个元素端口（已过滤图片和 generic）`)
}

const handlePageNameChange = async (pageName) => {
  if (!selectedNode.value || selectedNode.value.type !== 'page') {
    return
  }

  const snapshot = getSnapshotByPageName(pageName)
  if (!snapshot) {
    selectedNode.value.config.snapshotFile = null
    selectedNode.value.config.snapshotData = null
    updateNodeConfig()
    return
  }

  const previousSnapshotFile = selectedNode.value.config.snapshotFile
  selectedNode.value.config.pageName = snapshot.page_name
  selectedNode.value.config.snapshotFile = snapshot.filename

  if (
    previousSnapshotFile &&
    previousSnapshotFile !== snapshot.filename &&
    selectedNode.value.config.innerComponents?.length
  ) {
    ElMessage.warning('已切换页面快照，请检查已有组件映射是否仍然有效')
  }

  await loadPageSnapshot()
}

// 加载页面快照，在配置面板中选择快照文件时调用
const loadPageSnapshot = async () => {
  if (!selectedNode.value || !selectedNode.value.config.snapshotFile) {
    return
  }

  const filename = selectedNode.value.config.snapshotFile
  const snapshotMeta = getSnapshotMetaByFilename(filename)
  if (!selectedNode.value.config.pageName && snapshotMeta?.page_name) {
    selectedNode.value.config.pageName = snapshotMeta.page_name
  }

  // 如果已经加载过，直接使用缓存
  if (snapshotData.value[filename]) {
    console.log('使用缓存的快照数据:', filename)
    // 将快照数据关联到当前节点
    selectedNode.value.config.snapshotData = snapshotData.value[filename]
    ensurePageNodeConfig(selectedNode.value.config)
    normalizeInnerComponents(selectedNode.value.config)
    updateNodeConfig()

    // 强制刷新节点视图
    const node = graph.getCellById(selectedNode.value.id)
    if (node) {
      console.log('触发节点重新渲染（缓存）')
      console.log('缓存的可交互元素数量:', snapshotData.value[filename].interactiveElements.length)
      console.log('节点shape:', node.shape)

      // 对于 Vue Shape 节点，直接更新 data 即可触发 Vue 响应式刷新
      const newData = {
        type: 'page',
        config: selectedNode.value.config
      }

      console.log('设置新的节点数据（缓存）:', newData)
      node.setData(newData, { overwrite: true })

      // 等待 Vue 组件完成刷新后再同步端口
      setTimeout(() => {
        console.log('Vue 组件已刷新，开始同步元素端口（缓存）')
        syncPageNodePorts(node)
      }, 200)

      console.log('节点数据已更新（缓存）')
    }

    ElMessage.success('快照已加载')
    return
  }

  // 从后端加载快照内容
  const loading = ElLoading.service({
    lock: true,
    text: '正在加载快照文件...',
    background: 'rgba(0, 0, 0, 0.7)'
  })

  try {
    const response = await getPlaywrightSnapshotContent(filename)
    console.log('快照内容 API 响应:', response)
    console.log('response.content存在?', !!response?.content)
    console.log('response.data存在?', !!response?.data)
    console.log('response.data.content存在?', !!response?.data?.content)

    const payload = extractSnapshotPayload(response)
    const content = payload.content
    const size = payload.size
    const created_at = payload.created_at
    const modified_at = payload.modified_at
    const page_name = payload.page_name || snapshotMeta?.page_name || ''

    if (content) {
      console.log('准备加载页面快照，长度:', content.length)
      const data = await ensureSnapshotRuntimeData(filename, {
        ...payload,
        filename,
        page_name,
        size,
        created_at,
        modified_at
      })

      // 将快照数据关联到当前节点
      if (page_name) {
        selectedNode.value.config.pageName = page_name
      }
      selectedNode.value.config.snapshotData = data
      ensurePageNodeConfig(selectedNode.value.config)
      normalizeInnerComponents(selectedNode.value.config)
      updateNodeConfig()

      // 直接更新节点数据，不重新创建节点，避免拖动时出现 bug
      const node = graph.getCellById(selectedNode.value.id)
      if (node) {
        console.log('更新节点数据')
        console.log('快照数据:', data)
        console.log('可交互元素数量:', data.interactiveElements.length)
        console.log('节点shape:', node.shape)

        // 对于 Vue Shape 节点，直接更新 data 即可触发 Vue 响应式刷新
        const newData = {
          type: 'page',
          config: selectedNode.value.config
        }

        console.log('设置新的节点数据:', newData)
        node.setData(newData, { overwrite: true })

        refreshPageNodeView(node, { syncPorts: true, delay: 200 })

        console.log('节点数据已更新')
      }

      ElMessage.success(`快照加载成功，共解析 ${data.interactiveElements.length} 个可交互元素`)
    } else {
      console.error('快照内容为空，响应:', response)
      ElMessage.error('快照文件内容为空')
    }
  } catch (error) {
    console.error('快照加载失败:', error)
    ElMessage.error('快照加载失败: ' + (error.message || '未知错误'))
  } finally {
    loading.close()
  }
}

// 选择元素
const selectElement = (element) => {
  console.log('选中元素:', element)
  ElMessage.success(`选中元素: ${element.type} ${element.text || element.ref}`)
  // 如有需要，可在这里扩展更多元素选中后的交互，例如在页面节点中高亮对应元素
}

// 更新执行步骤配置
const updateExecutionStep = (index, step) => {
  const node = graph.getCellById(selectedNode.value.id)
  if (node) {
    const data = node.getData()
    if (data.config && data.config.executionPath) {
      data.config.executionPath[index] = step
      node.setData(data)
    }
  }
}

const selectExecutionStep = (index) => {
  if (!selectedNode.value?.config?.executionPath?.[index]) {
    return
  }

  selectedExecutionStepIndex.value = index
  selectedInnerComponentId.value = null
  activeInnerComponentId.value = null
  selectedExecutionResultRef.value = { nodeId: '', key: '', componentId: '' }
  activeDetailMenu.value = 'node'
  resetSelectedEdgeStyle()
  selectedEdge.value = null
}

const removeExecutionStep = (index = selectedExecutionStepIndex.value) => {
  if (selectedNode.value?.type !== 'page' || !Array.isArray(selectedNode.value.config?.executionPath)) {
    return
  }
  if (index === null || index < 0 || index >= selectedNode.value.config.executionPath.length) {
    return
  }

  selectedNode.value.config.executionPath.splice(index, 1)
  selectedExecutionStepIndex.value = null
  updateNodeConfig()
  ElMessage.success('执行路径已删除')
}

const deleteGraphEdge = (edge) => {
  if (!edge || !graph?.getCellById?.(edge.id)) {
    selectedEdge.value = null
    return
  }

  if (typeof edge.remove === 'function') {
    edge.remove()
  } else {
    graph.removeCell?.(edge)
  }
  selectedEdge.value = null
  ElMessage.success('连线已删除')
}

const deleteGraphNode = (node) => {
  if (!node || !graph?.getCellById?.(node.id)) {
    selectedNode.value = null
    return
  }

  const connectedEdges = [
    ...(graph.getIncomingEdges?.(node) || []),
    ...(graph.getOutgoingEdges?.(node) || [])
  ]
  const uniqueEdges = [...new Map(connectedEdges.map(edge => [edge.id, edge])).values()]
  uniqueEdges.forEach(edge => edge.remove())
  if (typeof node.remove === 'function') {
    node.remove()
  } else {
    graph.removeCell?.(node)
  }
  clearSelection()
  ElMessage.success('节点已删除')
}

const deleteSelectedGraphItem = () => {
  if (selectedEdge.value) {
    deleteGraphEdge(selectedEdge.value)
    return
  }

  if (selectedExecutionStepIndex.value !== null) {
    removeExecutionStep()
    return
  }

  if (selectedNode.value?.type === 'page' && selectedInnerComponentId.value) {
    removeInnerComponent(selectedInnerComponentId.value)
    return
  }

  if (selectedNode.value?.id) {
    deleteGraphNode(graph?.getCellById?.(selectedNode.value.id))
  }
}

const isEditableKeyboardTarget = (target) => {
  if (!target) {
    return false
  }

  const tagName = String(target.tagName || '').toLowerCase()
  return (
    target.isContentEditable ||
    ['input', 'textarea', 'select'].includes(tagName) ||
    Boolean(target.closest?.('.el-input, .el-textarea, .el-select, .el-input-number'))
  )
}

const handleEditorKeydown = (event) => {
  if (!['Delete', 'Backspace'].includes(event.key)) {
    return
  }
  if (isEditableKeyboardTarget(event.target) || !canDeleteSelection.value) {
    return
  }

  event.preventDefault()
  deleteSelectedGraphItem()
}

// 处理展开组件事件
const handleExpandComponents = (event) => {
  const { nodeId, elements, pageName } = event.detail

  console.log('展开组件:', { nodeId, elements: elements.length, pageName })

  // 获取页面节点
  const pageNode = graph.getCellById(nodeId)
  if (!pageNode) {
    console.error('找不到页面节点:', nodeId)
    return
  }

  // 获取页面节点的位置和尺寸
  const pagePos = pageNode.getPosition()
  const pageSize = pageNode.getSize()

  console.log('页面节点位置:', pagePos)
  console.log('页面节点尺寸:', pageSize)

  // 在页面节点右侧创建组件节点
  const startX = pagePos.x + pageSize.width + 100 // 与页面节点右侧保持 100px 间距
  let currentY = pagePos.y
  const verticalGap = 20 // 组件之间的垂直间距

  // 组件类型映射
  const componentTypeMap = {
    'textbox': 'input',
    'input': 'input',
    'searchbox': 'input',
    'button': 'button',
    'select': 'select',
    'combobox': 'select',
    'listbox': 'select',
    'checkbox': 'checkbox',
    'radio': 'radio',
    'link': 'link',
    'a': 'link',
    'tab': 'tab',
    'menuitem': 'menuitem',
    'clickable': 'clickable',
    'file': 'file'
  }

  // 记录已创建的组件节点
  const createdNodes = []

  elements.forEach((element, index) => {
    const componentType = componentTypeMap[element.type] || 'generic'
    const shapeName = `${componentType}-node`

    console.log(`创建组件节点 ${index + 1}:`, {
      type: element.type,
      componentType,
      shapeName,
      text: element.text
    })

    try {
      // 创建组件节点
      const componentNode = graph.addNode({
        shape: shapeName,
        x: startX,
        y: currentY,
        data: {
          type: 'component',
          componentType: componentType,
          config: {
            text: element.text || element.type,
            elementId: element.id,
            elementData: element,
            pageName: pageName,
            pageNodeId: nodeId,
            // 默认配置
            action: 'click', // 按钮默认执行点击
            value: '', // 输入框默认值
            placeholder: element.text || '输入内容...',
            selectedValue: '', // 下拉框选中值
            options: element.options || [], // 下拉框选项
            checked: false // 复选框选中状态
          }
        }
      })

      createdNodes.push(componentNode)

      // 更新下一个节点的 Y 坐标
      currentY += componentNode.getSize().height + verticalGap

      console.log(`组件节点创建成功:`, componentNode.id)
    } catch (error) {
      console.error(`创建组件节点失败:`, error)
    }
  })

  // 提示
  ElMessage.success(`已展开 ${createdNodes.length} 个组件节点`)

  console.log(`共创建 ${createdNodes.length} 个组件节点`)
}

// 获取组件类型名称
const getComponentTypeName = (type) => {
  return getFlowComponentTypeName(type)
  /*
  const nameMap = {
    'input': '输入框',
    'button': '按钮',
    'select': '下拉框',
    'checkbox': '复选框',
    'link': '链接'
  }
  return nameMap[type] || type
  */
}

// 获取组件标签类型
const getComponentTagType = (type) => {
  return getFlowComponentTagType(type)
  /*
  const tagMap = {
    'input': 'primary',
    'button': 'success',
    'select': 'warning',
    'checkbox': '',
    'link': 'info'
  }
  return tagMap[type] || ''
  */
}

// 生成脚本
const generateScript = ({ openDialog = true, silent = false, throwOnError = false } = {}) => {
  const data = getCurrentGraphDataForScript()

  // 验证流程
  if (!data.cells || data.cells.length === 0) {
    if (!silent) {
      ElMessage.warning('流程图为空，请先添加节点')
    }
    return ''
  }

  try {
    generatedScript.value = playwrightGenerator.generate(data)
    generatedScriptSignature.value = JSON.stringify(data)
    if (openDialog) {
      scriptDialogVisible.value = true
    }
    if (!silent) {
      ElMessage.success('脚本生成成功')
    }
    return generatedScript.value
  } catch (error) {
    console.error('生成脚本失败:', error)
    if (!silent) {
      ElMessage.error('生成脚本失败: ' + (error.message || '未知错误'))
    }
    if (throwOnError) {
      throw error
    }
    return ''
  }
}

// 复制脚本
const copyScript = async () => {
  try {
    await navigator.clipboard.writeText(generatedScript.value)
    ElMessage.success('脚本已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

// 下载脚本
const downloadScript = () => {
  const blob = new Blob([generatedScript.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `playwright_test_${Date.now()}.py`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('脚本下载成功')
}

const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const showScriptExecutionResult = (result, titlePrefix = '') => {
  const title = titlePrefix ? `${titlePrefix}执行结果` : '执行结果'
  const failedTitle = titlePrefix ? `${titlePrefix}执行失败` : '执行失败'
  const stdout = escapeHtml(result.stdout || '无输出')
  const stderr = escapeHtml(result.stderr || result.error || '未知错误')

  if (result.success) {
    ElMessage.success(`${titlePrefix || ''}脚本执行成功`)
    ElMessageBox.alert(
      `<div style="max-height: 400px; overflow-y: auto;">
        <h4>标准输出：</h4>
        <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px;">${stdout}</pre>
        ${result.stderr ? `<h4>错误输出：</h4><pre style="background: #fff2e8; padding: 12px; border-radius: 4px; color: #fa8c16;">${escapeHtml(result.stderr)}</pre>` : ''}
      </div>`,
      title,
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '确定'
      }
    )
    return
  }

  ElMessage.error(`${titlePrefix || ''}脚本执行失败`)
  ElMessageBox.alert(
    `<div style="max-height: 400px; overflow-y: auto;">
      <h4>错误输出：</h4>
      <pre style="background: #fff1f0; padding: 12px; border-radius: 4px; color: #cf1322;">${stderr}</pre>
      ${result.stdout ? `<h4>标准输出：</h4><pre style="background: #f5f5f5; padding: 12px; border-radius: 4px;">${escapeHtml(result.stdout)}</pre>` : ''}
    </div>`,
    failedTitle,
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '确定',
      type: 'error'
    }
  )
}

const normalizeExecutionResultStatus = status => {
  const normalized = String(status || '').toLowerCase()
  if (['success', 'passed', 'pass'].includes(normalized)) return 'success'
  if (['failed', 'fail', 'error'].includes(normalized)) return 'failed'
  if (['running', 'pending'].includes(normalized)) return normalized
  return normalized || 'pending'
}

const formatExecutionResultStatus = status => {
  const normalized = normalizeExecutionResultStatus(status)
  if (normalized === 'success') return '成功'
  if (normalized === 'failed') return '失败'
  if (normalized === 'running') return '执行中'
  return '待执行'
}

const getExecutionStatusTagType = status => {
  const normalized = normalizeExecutionResultStatus(status)
  if (normalized === 'success') return 'success'
  if (normalized === 'failed') return 'danger'
  if (normalized === 'running') return 'warning'
  return 'info'
}

const hasExecutionPayload = payload => {
  if (payload === null || payload === undefined) {
    return false
  }
  if (typeof payload === 'string') {
    return payload.trim().length > 0
  }
  if (Array.isArray(payload)) {
    return payload.length > 0
  }
  if (typeof payload === 'object') {
    return Object.keys(payload).length > 0
  }
  return Boolean(payload)
}

const formatExecutionPayload = payload => {
  if (typeof payload === 'string') {
    return payload
  }
  try {
    return JSON.stringify(payload ?? {}, null, 2)
  } catch (error) {
    return String(payload ?? '')
  }
}

const summarizeExecutionResult = step => {
  const status = normalizeExecutionResultStatus(step?.status)
  return {
    executionId: activeExecutionId.value,
    status,
    title: step?.title || '',
    input: step?.input_data || {},
    output: step?.output_data || {},
    errorLog: step?.error_log || '',
    screenshotUrl: step?.screenshot_url || '',
    startedAt: step?.started_at || '',
    finishedAt: step?.finished_at || '',
    duration: step?.duration || 0
  }
}

const clearGraphExecutionResults = () => {
  graph?.getNodes?.().forEach(node => {
    const data = node.getData?.()
    if (!data?.config) return
    const nextData = {
      ...data,
      config: {
        ...data.config,
        executionResult: null
      }
    }
    if (Array.isArray(data.config.innerComponents)) {
      nextData.config.innerComponents = data.config.innerComponents.map(component => ({
        ...component,
        executionResult: null
      }))
    }
    node.setData(nextData, { overwrite: true })
    if (data.type === 'page') {
      refreshPageNodeView(node)
    }
  })
}

const applyExecutionStepToGraph = step => {
  if (!graph || !step) return
  const result = summarizeExecutionResult(step)
  const nodeId = step.node_id || step.input_data?.node_id || ''
  const componentId = step.component_id || ''

  if (componentId) {
    const targetPageNode = graph.getNodes?.().find(node => {
      const config = node.getData?.()?.config || {}
      return Array.isArray(config.innerComponents) && config.innerComponents.some(component => component.id === componentId)
    })
    if (!targetPageNode) return
    const data = targetPageNode.getData()
    const nextComponents = (data.config.innerComponents || []).map(component => (
      component.id === componentId
        ? { ...component, executionResult: result }
        : component
    ))
    targetPageNode.setData({
      ...data,
      config: {
        ...data.config,
        innerComponents: nextComponents
      }
    }, { overwrite: true })
    refreshPageNodeView(targetPageNode)
    return
  }

  const node = graph.getCellById?.(nodeId)
  if (!node?.getData) return
  const data = node.getData()
  node.setData({
    ...data,
    config: {
      ...(data.config || {}),
      executionResult: result
    }
  }, { overwrite: true })
  if (data.type === 'page') {
    refreshPageNodeView(node)
  }
}

const applyExecutionResultToGraph = execution => {
  const steps = Array.isArray(execution?.steps) ? execution.steps : []
  steps.forEach(applyExecutionStepToGraph)
}

const stopExecutionPolling = () => {
  if (executionPollingTimer) {
    window.clearInterval(executionPollingTimer)
    executionPollingTimer = null
  }
}

const loadExecutionResult = async executionId => {
  if (!executionId) return null
  const response = await getVisualFlowExecutionDetail(executionId)
  const execution = response?.data || response || {}
  applyExecutionResultToGraph(execution)
  if (['success', 'failed', 'aborted'].includes(normalizeExecutionResultStatus(execution.status))) {
    stopExecutionPolling()
    backendExecuting.value = false
    localExecuting.value = false
    const message = execution.status === 'success'
      ? `${activeExecutionRunType.value === 'local' ? '本地' : '后台'}回放成功`
      : `${activeExecutionRunType.value === 'local' ? '本地' : '后台'}回放失败`
    if (execution.status === 'success') {
      ElMessage.success(message)
    } else {
      ElMessage.error(message)
    }
  }
  return execution
}

const startExecutionPolling = executionId => {
  stopExecutionPolling()
  activeExecutionId.value = executionId || ''
  if (!executionId) return
  executionPollingTimer = window.setInterval(() => {
    loadExecutionResult(executionId).catch(error => {
      console.warn('刷新流程执行结果失败:', error)
    })
  }, 1200)
  loadExecutionResult(executionId).catch(() => {})
}

const buildVisualFlowExecutionPayload = async () => {
  const graphData = getCurrentGraphDataForScript()
  return {
    script: generatedScript.value,
    flow_variables: await buildFlowExecutionVariables(graphData),
    visual_flow: {
      flow_id: currentFlowId.value || '',
      flow_name: currentFlowMeta.value?.name || '',
      graph_data: graphData
    }
  }
}

const generateScriptForReplay = options => playwrightGenerator.generate(getCurrentGraphDataForScript(), options)

const ensureGeneratedScriptReady = () => {
  if (!generatedScript.value || isGeneratedScriptStale.value) {
    generateScript({ openDialog: false, silent: true, throwOnError: true })
  }

  if (!generatedScript.value) {
    throw new Error('请先生成脚本')
  }
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

const buildLocalAgentPackageBlob = response => (
  response.data instanceof Blob
    ? response.data
    : new Blob([response.data], { type: response.data?.type || 'application/zip' })
)

const normalizeLocalAgentError = error => {
  const message = error?.message || ''
  if (!message || message === 'Failed to fetch' || message.includes('NetworkError')) {
    return '本地 Agent 服务未连接。若已安装，请允许浏览器打开 testhub-agent 协议；若未安装，请先到录制管理页下载本地 Agent 安装包。'
  }
  return message
}

const isLocalAgentPlatformBindingError = error => {
  const message = String(error?.message || '')
  return message.includes('尚未绑定当前平台') || message.includes('绑定的平台不一致')
}

const repairLocalAgentPlatformBinding = async () => {
  const response = await downloadLocalAgentPackage()
  const updateResponse = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/update`, {
    method: 'POST',
    mode: 'cors',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/zip',
      'X-TestHub-Platform-Url': window.location.origin
    },
    body: buildLocalAgentPackageBlob(response)
  }, 45000)
  const payload = await updateResponse.json().catch(() => ({}))
  if (!updateResponse.ok) {
    if (updateResponse.status === 403) {
      throw new Error('本地 Agent 拒绝自动修复，通常是 Agent 版本过旧或已绑定其他平台，请从当前平台重新下载安装本地 Agent 后再回放')
    }
    throw new Error(payload.error || `本地 Agent 平台绑定修复失败：HTTP ${updateResponse.status}`)
  }
  const ready = await waitForLocalAgentReady(90000)
  if (!ready) {
    throw new Error('本地 Agent 已修复平台绑定，但服务重启后未恢复，请手动启动 Agent 后重试')
  }
  return payload
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

const detectLocalAgent = async () => {
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
  return payload
}

const waitForLocalAgentReady = async (timeoutMs = 18000) => {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    try {
      await detectLocalAgent()
      return true
    } catch (error) {
      await new Promise(resolve => window.setTimeout(resolve, 1200))
    }
  }
  return false
}

const ensureLocalAgentReady = async () => {
  try {
    await detectLocalAgent()
    return true
  } catch (error) {
    invokeLocalAgentProtocol('start')
  }

  const ready = await waitForLocalAgentReady(18000)
  if (!ready) {
    throw new Error('未检测到本地 Agent。若已安装，请允许浏览器打开 testhub-agent 协议；若未安装，请先到录制管理页下载并安装本地 Agent。')
  }
  return true
}

const unwrapApiData = response => response?.data || response || {}

const getStartNodeCell = () => {
  if (!graph) return null
  return graph.getNodes().find(node => node.getData()?.type === 'start') || null
}

const getStartNodeConfig = () => getStartNodeCell()?.getData()?.config || null

const getFlowRecordingStartUrl = () => {
  const config = getStartNodeConfig()
  if (!config) {
    throw new Error('请先在画布中添加开始节点，并配置启动URL')
  }

  const url = String(
    config.inputMode === 'literal' && config.inputValue
      ? config.inputValue
      : config.url || ''
  ).trim()
  if (!/^https?:\/\//i.test(url)) {
    throw new Error('开始节点的启动URL需要以 http:// 或 https:// 开头')
  }
  return url
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

const buildFlowRecordingModulePayload = () => {
  const meta = currentFlowMeta.value || {}
  const moduleMeta = meta.module || meta.metadata?.module || meta.metadata?.recording_scope || {}
  const selectedContext = researchContext.value || {}
  return {
    project_id: selectedContext.project_id || meta.project_id || moduleMeta.project_id || null,
    module_id: selectedContext.module_id || meta.module_id || moduleMeta.module_id || null,
    module_name: selectedContext.module_name || meta.module_name || moduleMeta.module_name || '可视化流程编辑器',
    module_path: selectedContext.module_path || meta.module_path || moduleMeta.module_path || meta.module_name || moduleMeta.module_name || '可视化流程编辑器'
  }
}

const getSelectedResearchPageIdentity = () => {
  const context = researchContext.value || {}
  const pagePath = String(context.module_path || context.module_name || '').trim()
  if (!pagePath) {
    return ''
  }
  return `system-page:${pagePath.toLowerCase()}`
}

const findExistingPageNodeByResearchContext = () => {
  const identity = getSelectedResearchPageIdentity()
  const context = researchContext.value || {}
  const pageName = String(context.module_name || '').trim()
  const pagePath = String(context.module_path || '').trim()
  return getGraphPageNodes().find(node => {
    const data = node.getData?.() || {}
    const config = data.config || {}
    return (
      (identity && getPageRecordingIdentity(node) === identity) ||
      (pagePath && String(config.recordingPagePath || '').trim() === pagePath) ||
      (pageName && String(config.pageName || config.name || '').trim() === pageName)
    )
  }) || null
}

const applyResearchContextToPageConfig = config => {
  const context = researchContext.value || {}
  const pageName = String(context.module_name || '').trim()
  const pagePath = String(context.module_path || pageName).trim()
  if (!config || !pageName) {
    return config
  }
  config.name = pageName
  config.pageName = pageName
  config.recordingPageIdentity = getSelectedResearchPageIdentity() || config.recordingPageIdentity || ''
  config.recordingPagePath = pagePath || config.recordingPagePath || ''
  config.recordingPageSource = config.recordingPageSource || 'selected_directory'
  return config
}

const buildLocalAgentRecordingPayload = (session, agent = {}, options = {}) => ({
  pairing_url: buildBrowserReachablePairingUrl(
    session?.session_id,
    agent.pairing_url || session?.metadata?.local_agent_pairing_url || ''
  ),
  token: agent.token || '',
  browser: 'chromium',
  headless: false,
  replay_script: options.replayScript || '',
  record_replay_events: options.recordReplayEvents !== false,
  maximize: getStartNodeConfig()?.maximize !== false,
  viewport_width: getStartNodeConfig()?.viewportWidth || 1920,
  viewport_height: getStartNodeConfig()?.viewportHeight || 1080,
  api_origin: `${window.location.origin}/api`,
  access_token: userStore.accessToken || '',
  refresh_token: userStore.refreshToken || '',
  token_expires_at: String(userStore.tokenExpiresAt || ''),
  user: userStore.user || null,
  flow_variables: options.flowVariables || {},
  timeout_seconds: 300
})

const createLocalFlowRecordingSession = async ({ targetUrl, name }) => {
  const response = await startPlaywrightRecording({
    name,
    target_url: targetUrl,
    browser_type: 'chromium',
    recording_method: RECORDING_METHOD_LOCAL_AGENT,
    ...buildFlowRecordingModulePayload()
  })
  const payload = unwrapApiData(response)
  const session = payload.session || payload.data?.session
  if (!session?.session_id) {
    throw new Error('创建录制会话失败：后端未返回会话ID')
  }
  return {
    session,
    agent: payload.agent || {}
  }
}

const startLocalAgentRecordingBrowser = async (session, agent = {}, options = {}) => {
  const payload = buildLocalAgentRecordingPayload(session, agent, options)
  if (!payload.pairing_url || !payload.token) {
    throw new Error('本地 Agent 配对信息不完整')
  }

  await ensureLocalAgentReady()
  const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/recordings/start`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }, options.timeoutMs || 180000)
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(result.error || `本地 Agent 启动浏览器失败：HTTP ${response.status}`)
  }
  if (result.recording?.status && result.recording.status !== 'recording') {
    throw new Error(result.recording.error || '本地 Agent 尚未进入录制状态')
  }
  return result
}

const switchEditorToRecordingSession = async (sessionId) => {
  liveRecordingSessionId.value = sessionId
  liveRecordingMode.value = CONTINUE_RECORDING_MODE_NEW
  continueRecordingAnchor.value = null
  continueRecordingMergeState.value = {
    sessionId,
    mergedPageIds: [],
    mergedPageMap: {},
    mergedComponentMap: {},
    lastSignature: '',
    appendAfterNodeId: '',
    detachedSuccessorEdges: [],
    lastComponentByPageId: {}
  }
  liveFlowActive.value = true
  currentFlowId.value = ''
  currentFlowMeta.value = null
  await router.replace({
    path: '/manual-testcases/visual-flow',
    query: {
      ...route.query,
      flow_id: undefined,
      recording_session_id: sessionId
    }
  })
  await syncRecordingFlow({ initial: true })
  startLiveFlowPolling()
}

const startVisualFlowRecording = async () => {
  if (recordingStarting.value || liveFlowActive.value) return

  let createdSessionId = ''
  recordingStarting.value = true
  try {
    const targetUrl = getFlowRecordingStartUrl()
    const { session, agent } = await createLocalFlowRecordingSession({
      targetUrl,
      name: `流程开始录制 ${new Date().toLocaleString()}`
    })
    createdSessionId = session.session_id
    await startLocalAgentRecordingBrowser(session, agent)
    await switchEditorToRecordingSession(session.session_id)
    ElMessage.success('本地浏览器已启动，请在浏览器中继续操作')
  } catch (error) {
    console.error('启动流程录制失败:', error)
    if (createdSessionId) {
      try {
        await stopPlaywrightRecording(createdSessionId)
      } catch (stopError) {
        console.warn('清理录制会话失败:', stopError)
      }
    }
    ElMessage.error(error.message?.startsWith('请先') || error.message?.startsWith('开始节点')
      ? error.message
      : '启动流程录制失败: ' + normalizeLocalAgentError(error))
  } finally {
    recordingStarting.value = false
  }
}

const buildContinueRecordingReplayScript = () => {
  if (!selectedNode.value?.id) {
    throw new Error('请先点击流程图中的节点或组件，再点击继续录制')
  }
  const graphData = getCurrentGraphDataForScript()
  if (!graphData.cells?.length) {
    throw new Error('流程图为空，无法继续录制')
  }
  return playwrightGenerator.generate(graphData, {
    mode: 'cdp-replay',
    targetNodeId: selectedNode.value.id,
    targetComponentId: selectedNode.value.type === 'page'
      ? (selectedInnerComponentId.value || activeInnerComponentId.value || '')
      : ''
  })
}

const buildContinueRecordingAnchor = () => {
  if (!selectedNode.value?.id) {
    throw new Error('请先点击流程图中的节点或组件，再点击继续录制')
  }
  const node = graph?.getCellById?.(selectedNode.value.id)
  const componentId = selectedNode.value.type === 'page'
    ? (selectedInnerComponentId.value || activeInnerComponentId.value || '')
    : ''
  return {
    nodeId: selectedNode.value.id,
    nodeType: selectedNode.value.type,
    componentId,
    pageIdentity: node?.getData?.()?.type === 'page' ? getPageRecordingIdentity(node) : '',
    graphData: getCurrentGraphDataForScript()
  }
}

const continueVisualFlowRecording = async () => {
  if (recordingContinuing.value || liveFlowActive.value) return

  let createdSessionId = ''
  recordingContinuing.value = true
  try {
    const targetUrl = getFlowRecordingStartUrl()
    const anchor = buildContinueRecordingAnchor()
    const replayScript = buildContinueRecordingReplayScript()
    const flowVariables = await buildFlowExecutionVariables(anchor.graphData)
    const { session, agent } = await createLocalFlowRecordingSession({
      targetUrl,
      name: `流程继续录制 ${new Date().toLocaleString()}`
    })
    createdSessionId = session.session_id
    await startLocalAgentRecordingBrowser(session, agent, {
      replayScript,
      flowVariables,
      recordReplayEvents: false,
      timeoutMs: 240000
    })
    continueRecordingAnchor.value = anchor
    continueRecordingMergeState.value = {
      sessionId: session.session_id,
      mergedPageIds: [],
      mergedPageMap: {},
      mergedComponentMap: {},
      lastSignature: '',
      appendAfterNodeId: anchor.nodeId,
      detachedSuccessorEdges: [],
      lastComponentByPageId: anchor.componentId ? { [anchor.nodeId]: anchor.componentId } : {}
    }
    liveRecordingSessionId.value = session.session_id
    liveRecordingMode.value = CONTINUE_RECORDING_MODE_APPEND
    liveFlowActive.value = true
    startLiveFlowPolling()
    ElMessage.success('已回放到选中位置，请在本地浏览器中继续操作')
  } catch (error) {
    console.error('继续流程录制失败:', error)
    if (createdSessionId) {
      try {
        await stopPlaywrightRecording(createdSessionId)
      } catch (stopError) {
        console.warn('清理录制会话失败:', stopError)
      }
    }
    ElMessage.error(error.message?.startsWith('请先') || error.message?.startsWith('流程') || error.message?.startsWith('开始节点')
      ? error.message
      : '继续流程录制失败: ' + normalizeLocalAgentError(error))
  } finally {
    recordingContinuing.value = false
  }
}

const stopVisualFlowRecording = async () => {
  const sessionId = liveRecordingSessionId.value || getRouteRecordingSessionId()
  if (!sessionId || recordingStopping.value) return

  recordingStopping.value = true
  try {
    const isContinuation = liveRecordingMode.value === CONTINUE_RECORDING_MODE_APPEND
    await stopPlaywrightRecording(sessionId)
    liveFlowActive.value = false
    stopLiveFlowPolling()
    if (isContinuation) {
      await syncContinuationRecordingFlow({ final: true })
      await new Promise(resolve => window.setTimeout(resolve, 1200))
      await syncContinuationRecordingFlow({ final: true })
      await persistCurrentFlowSilently()
      liveRecordingSessionId.value = ''
      liveRecordingMode.value = ''
      continueRecordingAnchor.value = null
    } else {
      await syncRecordingFlow({ initial: false })
    }
    ElMessage.success('录制已停止')
  } catch (error) {
    console.error('停止流程录制失败:', error)
    ElMessage.error(error.response?.data?.error || '停止录制失败')
  } finally {
    recordingStopping.value = false
  }
}

const buildLocalScriptExecutePayload = async () => {
  const graphData = getCurrentGraphDataForScript()
  return {
    script: generateScriptForReplay({ forceHeaded: true }),
    flow_variables: await buildFlowExecutionVariables(graphData),
    api_origin: `${window.location.origin}/api`,
    access_token: userStore.accessToken || '',
    refresh_token: userStore.refreshToken || '',
    token_expires_at: String(userStore.tokenExpiresAt || ''),
    user: userStore.user || null,
    visual_flow: {
      flow_id: currentFlowId.value || '',
      flow_name: currentFlowMeta.value?.name || '',
      graph_data: graphData
    },
    timeout_seconds: 300
  }
}

const executeLocalScriptThroughAgent = async payload => {
  const response = await fetchWithTimeout(`${LOCAL_AGENT_SERVICE_URL}/scripts/execute`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }, 330000)
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(result.error || `本地 Agent 执行失败：HTTP ${response.status}`)
  }
  if (result.execution_sync_error) {
    throw new Error(result.execution_sync_error)
  }
  return result
}

const executeLocalScript = async () => {
  if (localExecuting.value) {
    return
  }

  localExecuting.value = true
  activeExecutionRunType.value = 'local'
  let localExecutionId = ''

  try {
    ensureGeneratedScriptReady()
    clearGraphExecutionResults()
    await ensureLocalAgentReady()
    const executionResponse = await createVisualFlowExecution({
      run_type: 'local',
      visual_flow: {
        flow_id: currentFlowId.value || '',
        flow_name: currentFlowMeta.value?.name || '',
        graph_data: getCurrentGraphDataForScript()
      }
    })
    const execution = executionResponse?.data || executionResponse || {}
    if (!execution.execution_id) {
      throw new Error('创建本地回放执行记录失败')
    }
    localExecutionId = execution.execution_id
    activeExecutionId.value = localExecutionId
    startExecutionPolling(localExecutionId)
    ElMessage.success('本地回放已启动')
    const agentPayload = {
      ...(await buildLocalScriptExecutePayload()),
      execution_id: localExecutionId
    }
    let result
    try {
      result = await executeLocalScriptThroughAgent(agentPayload)
    } catch (error) {
      if (!isLocalAgentPlatformBindingError(error)) {
        throw error
      }
      ElMessage.warning('本地 Agent 未绑定当前平台，正在自动修复后重试回放')
      await repairLocalAgentPlatformBinding()
      result = await executeLocalScriptThroughAgent(agentPayload)
    }
    if (result.execution_id || execution.execution_id) {
      startExecutionPolling(result.execution_id || execution.execution_id)
    } else {
      showScriptExecutionResult(result, '本地')
      localExecuting.value = false
    }
  } catch (error) {
    console.error('本地执行脚本失败:', error)
    stopExecutionPolling()
    if (localExecutionId) {
      try {
        await finalizeVisualFlowExecution(localExecutionId, {
          success: false,
          stdout: '',
          stderr: error.message || '本地回放失败',
          error: error.message || '本地回放失败',
          returncode: -1
        })
        await loadExecutionResult(localExecutionId)
      } catch (syncError) {
        console.warn('同步本地回放失败状态失败:', syncError)
      }
    }
    ElMessage.error(
      error.message?.startsWith('流程') || error.message?.startsWith('生成脚本失败') || error.message?.startsWith('请先生成脚本')
        ? error.message
        : '本地回放失败: ' + normalizeLocalAgentError(error)
    )
    localExecuting.value = false
  }
}

// 执行脚本，调用后端 API
const executeScript = async () => {
  if (backendExecuting.value) {
    return
  }

  backendExecuting.value = true
  activeExecutionRunType.value = 'backend'
  try {
    ensureGeneratedScriptReady()
    clearGraphExecutionResults()
    const response = await executeVisualFlowScript(await buildVisualFlowExecutionPayload())
    const result = response?.data || response || {}
    if (result.execution_id) {
      startExecutionPolling(result.execution_id)
      ElMessage.success('后台回放已启动')
    } else {
      showScriptExecutionResult(result, '')
      backendExecuting.value = false
    }
  } catch (error) {
    console.error('执行脚本失败:', error)
    ElMessage.error(
      error.message?.startsWith('流程') || error.message?.startsWith('生成脚本失败')
        ? error.message
        : '后台回放失败: ' + (error.message || '未知错误')
    )
    backendExecuting.value = false
  }
}

const resolveNewFlowName = async () => {
  try {
    const result = await ElMessageBox.prompt('请输入流程名称', '保存流程', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: `流程 ${new Date().toLocaleString()}`,
      inputPattern: /\S+/,
      inputErrorMessage: '流程名称不能为空'
    })
    return String(result.value || '').trim()
  } catch (error) {
    return ''
  }
}

// 保存流程
const saveFlow = async () => {
  if (!graph || flowLoading.value) {
    return
  }

  const graphData = normalizeGraphDataForPersistence(graph.toJSON())
  if (!graphData.cells || graphData.cells.length === 0) {
    ElMessage.warning('流程图为空，请先添加节点')
    return
  }

  const isNewFlow = !currentFlowId.value
  const flowName = isNewFlow
    ? await resolveNewFlowName()
    : (currentFlowMeta.value?.name || '')

  if (isNewFlow && !flowName) {
    return
  }

  flowLoading.value = true
  try {
    const modulePayload = buildFlowRecordingModulePayload()
    const payload = {
      graph_data: graphData,
      ...modulePayload,
      metadata: {
        ...(currentFlowMeta.value?.metadata || {}),
        module: {
          project_id: modulePayload.project_id,
          module_id: modulePayload.module_id,
          module_name: modulePayload.module_name,
          module_path: modulePayload.module_path
        }
      }
    }

    let response
    if (currentFlowId.value) {
      if (flowName) {
        payload.name = flowName
      }
      response = await updateVisualFlow(currentFlowId.value, payload)
    } else {
      response = await createVisualFlow({
        name: flowName,
        source: 'manual',
        status: 'draft',
        graph_data: graphData,
        ...modulePayload,
        metadata: {
          created_from: 'visual_flow_editor',
          module: {
            project_id: modulePayload.project_id,
            module_id: modulePayload.module_id,
            module_name: modulePayload.module_name,
            module_path: modulePayload.module_path
          }
        }
      })
    }

    const flow = response.data || response
    currentFlowId.value = flow.flow_id || currentFlowId.value
    currentFlowMeta.value = flow

    if (currentFlowId.value && route.query.flow_id !== currentFlowId.value) {
      router.replace({
        path: '/manual-testcases/visual-flow',
        query: {
          ...route.query,
          flow_id: currentFlowId.value
        }
      })
    }

    ElMessage.success('流程保存成功')
  } catch (error) {
    console.error('保存流程失败:', error)
    ElMessage.error(error.response?.data?.error || '流程保存失败')
  } finally {
    flowLoading.value = false
  }
}

// 后台回放
const executeFlow = () => {
  executeScript()
}
</script>

<style scoped lang="scss">
.visual-flow-editor {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #f5f5f5;

  .workspace-section-tabs {
    padding: 16px 24px 0;
  }

  .editor-header {
    --flow-header-left-clearance: 56px;
    --flow-header-right-clearance: 56px;

    position: absolute;
    top: 10px;
    left: calc(var(--flow-header-left-clearance) + (100% - var(--flow-header-left-clearance) - var(--flow-header-right-clearance)) / 2);
    right: auto;
    z-index: 25;
    width: max-content;
    max-width: calc(100% - var(--flow-header-left-clearance) - var(--flow-header-right-clearance) - 24px);
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #d8dee8;
    border-radius: 6px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
    backdrop-filter: blur(6px);
    pointer-events: auto;
    transform: translateX(-50%);
    transition: left 0.2s ease, max-width 0.2s ease;

    &.editor-header--left-panel-open {
      --flow-header-left-clearance: 368px;
    }

    &.editor-header--detail-panel-open {
      --flow-header-right-clearance: 420px;
    }

    :deep(.el-tag) {
      height: 26px;
      line-height: 24px;
      padding: 0 8px;
      font-size: 13px;
    }

    :deep(.el-button) {
      height: 32px;
      min-height: 32px;
      padding: 0 12px;
      border-radius: 4px;
      font-size: 13px;
    }

    :deep(.el-button + .el-button) {
      margin-left: 0;
    }

    :deep(.el-button .el-icon) {
      font-size: 15px;
    }

    .header-actions {
      display: flex;
      flex: 0 1 auto;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-start;
      gap: 8px;

      .continue-recording-button {
        color: #92400e;
        font-weight: 700;
      }
    }
  }

  .editor-workspace {
    min-height: 0;
    flex: 1;
    display: flex;
    padding: 0 12px 12px;
    overflow: hidden;
  }

  .editor-container {
    min-width: 0;
    min-height: 0;
    flex: 1;
    display: flex;
    position: relative;
    overflow: hidden;
    background: #fff;
    border: 1px solid #e5e7eb;

    .flow-left-sidebar {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 30;
      width: 368px;
      display: flex;
      align-items: stretch;
      background: transparent;
      pointer-events: none;
    }

    .flow-left-tabs {
      width: 48px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      padding: 0;
      background: #fff;
      border-right: 1px solid #d8dee8;
      box-shadow: 2px 0 10px rgba(15, 23, 42, 0.08);
      pointer-events: auto;
    }

    .flow-left-tab {
      width: 100%;
      min-height: 104px;
      padding: 10px 0;
      border: 0;
      border-right: 3px solid transparent;
      border-bottom: 1px solid #eef2f7;
      background: #fff;
      color: #111827;
      font-size: 13px;
      font-weight: 700;
      line-height: 1;
      text-align: center;
      cursor: pointer;
      transition: background 0.2s, color 0.2s, border-color 0.2s;

      span {
        display: inline-block;
        writing-mode: vertical-rl;
        text-orientation: upright;
        letter-spacing: 2px;
        word-break: keep-all;
      }

      &:hover {
        background: #f8fafc;
      }

      &.active {
        border-right-color: #2563eb;
        background: #f8fafc;
      }
    }

    .flow-left-panel {
      width: 320px;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: #fff;
      border-right: 1px solid #d8dee8;
      box-shadow: 8px 0 24px rgba(15, 23, 42, 0.14);
      pointer-events: auto;
    }

    .flow-left-panel-header {
      height: 56px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 14px 0 16px;
      border-bottom: 1px solid #e8e8e8;

      h3 {
        margin: 0;
        color: #111827;
        font-size: 16px;
        font-weight: 700;
      }
    }

    .flow-left-panel-content {
      flex: 1;
      min-height: 0;
      overflow: auto;
    }

    .flow-left-directory {
      display: flex;
      overflow: hidden;

      :deep(.manual-workspace-directory-panel) {
        width: 100%;
        height: 100%;
        border-right: 0;
      }
    }

    .toolbar {
      width: 100%;
      background: #fff;
      padding: 16px;
      overflow-y: auto;
      user-select: none;
      -webkit-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;

      .toolbar-title {
        font-size: 14px;
        font-weight: 600;
        color: #333;
        margin-bottom: 12px;
      }

      .node-palette,
      .component-palette {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;

        .palette-item,
        .palette-component {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 10px 8px;
          border: 1px solid #d9d9d9;
          border-radius: 4px;
          cursor: grab;
          transition: all 0.3s;
          background: #fff;
          user-select: none;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;

          &:hover {
            border-color: #52c41a;
            background: #f6ffed;
          }

          &:active {
            cursor: grabbing;
          }

          .el-icon {
            font-size: 20px;
            color: #52c41a;
          }

          span {
            font-size: 11px;
            color: #666;
            text-align: center;
          }
        }
      }
    }

    .canvas-wrapper {
      flex: 1;
      min-width: 0;
      position: relative;
      overflow: hidden;

      .graph-container {
        width: 100%;
        height: 100%;
      }
    }

    .flow-detail-sidebar {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 30;
      width: 420px;
      display: flex;
      flex-direction: row-reverse;
      align-items: stretch;
      background: transparent;
      border-left: 0;
      pointer-events: none;
    }

    .flow-detail-tabs {
      width: 48px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      gap: 0;
      padding: 0;
      background: #fff;
      border-left: 1px solid #d8dee8;
      box-shadow: -2px 0 10px rgba(15, 23, 42, 0.08);
      pointer-events: auto;
    }

    .flow-detail-tab {
      width: 100%;
      min-height: 92px;
      padding: 10px 0;
      border: 0;
      border-left: 3px solid transparent;
      border-bottom: 1px solid #eef2f7;
      background: #fff;
      color: #111827;
      font-size: 13px;
      font-weight: 700;
      line-height: 1;
      text-align: center;
      cursor: pointer;
      transition: background 0.2s, color 0.2s, border-color 0.2s;

      span {
        display: inline-block;
        writing-mode: vertical-rl;
        text-orientation: upright;
        letter-spacing: 2px;
        word-break: keep-all;
      }

      &:hover:not(:disabled) {
        background: #f8fafc;
        color: #111827;
      }

      &.active {
        border-left-color: #2563eb;
        background: #f8fafc;
        color: #111827;
        font-weight: 700;
      }

      &:disabled {
        color: #111827;
        cursor: not-allowed;
        opacity: 0.35;
      }
    }

    .config-panel {
      width: 320px;
      background: #fff;
      border-left: 1px solid #e8e8e8;
      display: flex;
      flex-direction: column;
      min-height: 0;

      &.flow-detail-panel {
        width: 372px;
        height: 100%;
        border-left: 1px solid #d8dee8;
        border-right: 1px solid #d8dee8;
        box-shadow: -8px 0 24px rgba(15, 23, 42, 0.14);
        pointer-events: auto;
      }

      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #e8e8e8;

        h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }
      }

      .panel-content {
        flex: 1;
        padding: 16px;

        .panel-actions {
          margin-top: 16px;
          display: flex;
          justify-content: flex-end;
        }

        .detail-summary {
          margin-bottom: 14px;
        }

        .execution-detail-panel {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .execution-detail-section {
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          background: #f8fafc;
          overflow: hidden;

          .execution-detail-title {
            padding: 8px 10px;
            background: #eef2f7;
            color: #334155;
            font-size: 13px;
            font-weight: 700;
            border-bottom: 1px solid #e5e7eb;
          }

          pre {
            max-height: 240px;
            margin: 0;
            padding: 10px;
            overflow: auto;
            color: #111827;
            font-size: 12px;
            line-height: 1.45;
            white-space: pre-wrap;
            word-break: break-word;
          }

          &.execution-detail-error {
            border-color: #fecaca;
            background: #fff7f7;

            .execution-detail-title {
              background: #fee2e2;
              color: #b91c1c;
              border-bottom-color: #fecaca;
            }

            pre {
              color: #991b1b;
            }
          }
        }

        .execution-detail-screenshot {
          display: block;
          width: calc(100% - 20px);
          height: 180px;
          margin: 10px;
          border: 1px solid #e5e7eb;
          border-radius: 4px;
          background: #fff;
        }

        .reference-option {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .reference-option-name {
          color: #111827;
          font-weight: 600;
        }

        .reference-option-source {
          color: #6b7280;
          font-size: 12px;
          text-align: right;
        }

        .reference-option-hint {
          margin-top: 6px;
          color: #6b7280;
          font-size: 12px;
          line-height: 1.4;
        }

        .form-help-text {
          margin-top: 6px;
          color: #6b7280;
          font-size: 12px;
          line-height: 1.4;
        }

        .snapshot-page-option {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .snapshot-page-option-name {
          color: #111827;
          font-weight: 600;
        }

        .snapshot-page-option-file {
          color: #6b7280;
          font-size: 12px;
          text-align: right;
        }

        .execution-path {
          margin-bottom: 20px;

          .path-list {
            .path-step {
              padding: 12px;
              margin-bottom: 12px;
              background: #fff;
              border: 1px solid #d9d9d9;
              border-radius: 4px;
              cursor: pointer;

              &.active {
                border-color: #f56c6c;
                background: #fff5f5;
                box-shadow: 0 0 0 2px rgba(245, 108, 108, 0.12);
              }

              .step-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                margin-bottom: 8px;

                .step-title {
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  min-width: 0;
                }

                .step-number {
                  display: inline-flex;
                  align-items: center;
                  justify-content: center;
                  width: 24px;
                  height: 24px;
                  background: #1890ff;
                  color: #fff;
                  border-radius: 50%;
                  font-size: 12px;
                  font-weight: 600;
                }

                .step-action {
                  font-size: 14px;
                  font-weight: 600;
                  color: #1890ff;
                  text-transform: uppercase;
                }
              }

              .step-from,
              .step-to {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                color: #666;
                margin-bottom: 6px;

                .el-icon {
                  color: #1890ff;
                }
              }

              .step-config {
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px dashed #e8e8e8;
              }
            }
          }
        }

        .snapshot-elements {
          margin-top: 16px;

          .elements-list {
            .element-item {
              padding: 12px;
              margin-bottom: 8px;
              border: 1px solid #e8e8e8;
              border-radius: 4px;
              cursor: pointer;
              transition: all 0.3s;
              background: #fafafa;

              &:hover {
                border-color: #1890ff;
                background: #e6f7ff;
                box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
              }

              .element-type {
                font-size: 12px;
                font-weight: 600;
                color: #1890ff;
                margin-bottom: 4px;
                text-transform: uppercase;
              }

              .element-text {
                font-size: 14px;
                color: #333;
                margin-bottom: 4px;
                font-weight: 500;
              }

              .element-ref {
                font-size: 11px;
                color: #8c8c8c;
                margin-bottom: 6px;
                font-family: monospace;
              }

              .element-selectors {
                margin-top: 6px;

                .el-tag {
                  font-family: monospace;
                  font-size: 11px;
                  max-width: 100%;
                  overflow: hidden;
                  text-overflow: ellipsis;
                }
              }
            }
          }
        }
      }
    }
  }
}

// 页面节点内部元素样式
:deep(.page-node-container) {
  width: 100%;
  height: 100%;
  background: #fff;
  border: 2px solid #1890ff;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .page-node-header {
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
    color: #fff;
    padding: 10px 12px;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    border-bottom: 2px solid #0050b3;
  }

  .page-node-body {
    flex: 1;
    padding: 10px;
    overflow-y: auto;
    background: #fafafa;
  }

  .page-element-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    margin-bottom: 6px;
    background: #fff;
    border: 1px solid #d9d9d9;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 12px;

    &:hover {
      border-color: #1890ff;
      background: #e6f7ff;
      box-shadow: 0 2px 4px rgba(24, 144, 255, 0.2);
    }

    .element-type-badge {
      display: inline-block;
      padding: 2px 6px;
      background: #1890ff;
      color: #fff;
      border-radius: 2px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .element-text {
      flex: 1;
      color: #333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .page-node-empty {
    text-align: center;
    color: #999;
    padding: 40px 20px;
    font-size: 13px;
  }

  .page-element-more {
    text-align: center;
    color: #1890ff;
    padding: 8px;
    font-size: 12px;
    background: #e6f7ff;
    border-radius: 3px;
    margin-top: 6px;
  }
}

// 脚本预览对话框样式
.script-preview {
  .script-toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e8e8e8;
    align-items: center;
    flex-wrap: wrap;

    .script-stale-alert {
      flex-basis: 100%;
    }
  }

  .script-code {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    background: #f5f5f5;
    padding: 16px;
    border-radius: 4px;
    color: #333;
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
}

/* 拖拽预览样式 */
.drag-preview {
  padding: 8px 16px;
  background: white;
  border: 2px dashed #52c41a;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: 13px;
  font-weight: 500;
}

/* 页面节点高亮样式 */
:deep(.drop-target-highlight) {
  box-shadow: 0 0 0 3px rgba(82, 196, 26, 0.3) !important;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.mapped-components-panel {
  margin-bottom: 16px;
}

.mapped-components-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mapped-component-card {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mapped-component-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.08);
}

.mapped-component-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.mapped-component-card.invalid {
  border-color: #fca5a5;
  background: #fff5f5;
}

.mapped-component-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mapped-component-card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.mapped-component-card-title {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}

.mapped-component-card-meta {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.mapped-component-editor {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
}
</style>
