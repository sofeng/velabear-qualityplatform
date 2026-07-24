<template>
  <div ref="editorRootRef" class="manual-testcase-editor" :class="{ 'is-readonly': isReadonlyMindmap }">
    <el-card>
      <div class="editor-body">
        <transition name="toolbar-fold">
          <!-- 脑图工具栏 -->
          <div v-show="showToolbar" class="minder-toolbar">
        <div v-if="!externalToolbar" class="toolbar-section toolbar-page-actions">
          <el-tooltip content="返回" placement="bottom">
            <el-button size="small" aria-label="返回" @click="handleBack">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="showMaximizeAction" :content="maximized ? '恢复原形' : '最大化'" placement="bottom">
            <el-button
              size="small"
              :aria-label="maximized ? '恢复原形' : '最大化'"
              @click="emit('toggle-maximized')"
            >
              <el-icon>
                <component :is="maximized ? ScaleToOriginal : FullScreen" />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="showDefectAction" content="提缺陷" placement="bottom">
            <el-button size="small" :disabled="!hasSelection" aria-label="提缺陷" @click="handleCreateDefect">
              <el-icon><Warning /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip :content="showDetailPanel ? '隐藏节点详情' : '展开节点详情'" placement="bottom">
            <el-button
              size="small"
              :type="showDetailPanel ? 'primary' : 'default'"
              :plain="!showDetailPanel"
              :aria-label="showDetailPanel ? '隐藏详情' : '展开详情'"
              @click="toggleDetailPanel"
            >
              <el-icon>
                <component :is="showDetailPanel ? ArrowRight : ArrowLeft" />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="保存" placement="bottom">
            <el-button
              size="small"
              type="primary"
              :disabled="isReadonlyMindmap"
              aria-label="保存"
              @click="handleSave"
            >
              <el-icon><DocumentAdd /></el-icon>
            </el-button>
          </el-tooltip>

          <!-- 导出下拉菜单 -->
          <el-tooltip content="导出" placement="bottom">
            <el-dropdown @command="handleExportCommand" trigger="click">
              <el-button size="small" aria-label="导出">
                <el-icon><Download /></el-icon>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">
                    <el-icon><Document /></el-icon> JSON格式
                  </el-dropdown-item>
                  <el-dropdown-item command="xmind">
                    <el-icon><Document /></el-icon> XMind文件
                  </el-dropdown-item>
                  <el-dropdown-item command="png">
                    <el-icon><Picture /></el-icon> PNG图片
                  </el-dropdown-item>
                  <el-dropdown-item command="svg">
                    <el-icon><PictureFilled /></el-icon> SVG矢量图
                  </el-dropdown-item>
                  <el-dropdown-item divided command="markdown">
                    <el-icon><Document /></el-icon> Markdown
                  </el-dropdown-item>
                  <el-dropdown-item command="text">
                    <el-icon><Document /></el-icon> 纯文本
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </el-tooltip>

          <!-- 导入下拉菜单 -->
          <el-tooltip content="导入" placement="bottom">
            <el-dropdown @command="handleImportCommand" trigger="click">
              <el-button size="small" :disabled="isReadonlyMindmap" aria-label="导入">
                <el-icon><Upload /></el-icon>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">
                    <el-icon><Document /></el-icon> JSON格式
                  </el-dropdown-item>
                  <el-dropdown-item command="xmind">
                    <el-icon><Document /></el-icon> XMind文件
                  </el-dropdown-item>
                  <el-dropdown-item command="markdown">
                    <el-icon><Document /></el-icon> Markdown
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </el-tooltip>
        </div>

        <el-divider v-if="!externalToolbar" direction="vertical" />

        <!-- 文件操作 -->
        <el-button-group>
          <el-button size="small" @click="handleUndo" :disabled="isReadonlyMindmap || !canUndo">
            <el-icon><RefreshLeft /></el-icon> 撤销
          </el-button>
          <el-button size="small" @click="handleRedo" :disabled="isReadonlyMindmap || !canRedo">
            <el-icon><RefreshRight /></el-icon> 重做
          </el-button>
        </el-button-group>

        <el-divider direction="vertical" />

        <!-- 基础编辑 -->
        <el-dropdown @command="handleNodeInsertCommand" trigger="click">
          <el-button
            size="small"
            class="toolbar-icon-dropdown-button"
            :disabled="isReadonlyMindmap || !hasSelection"
            aria-label="添加节点"
          >
            <el-icon><Plus /></el-icon>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="child" :disabled="isReadonlyMindmap || !hasSelection">
                <el-icon><Plus /></el-icon> 添加子节点 (Tab)
              </el-dropdown-item>
              <el-dropdown-item command="sibling" :disabled="isReadonlyMindmap || !hasSelection">
                <el-icon><Plus /></el-icon> 添加同级 (Enter)
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-tooltip content="删除节点" placement="bottom">
          <el-button
            size="small"
            :disabled="isReadonlyMindmap || !hasSelection || isRootSelected"
            aria-label="删除节点"
            @click="execCommand('RemoveNode')"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>

        <el-divider direction="vertical" />

        <!-- 复制粘贴 -->
        <el-dropdown @command="handleClipboardCommand" trigger="click">
          <el-button
            size="small"
            class="toolbar-icon-dropdown-button"
            :disabled="!hasSelection"
            aria-label="剪贴板操作"
          >
            <el-icon><CopyDocument /></el-icon>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="copy" :disabled="!hasSelection">
                <el-icon><CopyDocument /></el-icon> 复制 (Ctrl+C)
              </el-dropdown-item>
              <el-dropdown-item command="cut" :disabled="isReadonlyMindmap || !hasSelection || isRootSelected">
                <el-icon><Scissor /></el-icon> 剪切 (Ctrl+X)
              </el-dropdown-item>
              <el-dropdown-item command="paste" :disabled="isReadonlyMindmap || !hasSelection">
                <el-icon><DocumentCopy /></el-icon> 粘贴 (Ctrl+V)
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-divider direction="vertical" />

        <!-- 过滤 -->
        <el-dropdown @command="handleFilterCommand" trigger="click">
          <el-button size="small" class="toolbar-icon-dropdown-button" aria-label="过滤">
            <el-icon><Filter /></el-icon>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="open">
                <el-icon><Filter /></el-icon> 过滤
              </el-dropdown-item>
              <el-dropdown-item command="clear" :disabled="!hasFilter">
                <el-icon><RefreshLeft /></el-icon> 清除过滤
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-divider direction="vertical" />

        <!-- 布局模板 -->
        <el-tooltip :content="`脑图类型：${currentTemplateLabel}`" placement="bottom">
          <el-dropdown @command="handleTemplateCommand" trigger="click" popper-class="minder-toolbar-dropdown">
            <el-button
              size="small"
              class="toolbar-icon-dropdown-button"
              :disabled="isReadonlyMindmap"
              aria-label="脑图类型"
            >
              <el-icon><Grid /></el-icon>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="option in templateOptions"
                  :key="option.value"
                  :command="option.value"
                  :class="{ 'is-active': currentTemplate === option.value }"
                >
                  {{ option.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-tooltip>

        <!-- 主题 -->
        <el-tooltip :content="`颜色：${currentThemeLabel}`" placement="bottom">
          <el-dropdown @command="handleThemeCommand" trigger="click" popper-class="minder-toolbar-dropdown">
            <el-button
              size="small"
              class="toolbar-icon-dropdown-button"
              :disabled="isReadonlyMindmap"
              aria-label="颜色"
            >
              <el-icon><Brush /></el-icon>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="option in themeOptions"
                  :key="option.value"
                  :command="option.value"
                  :class="{ 'is-active': currentTheme === option.value }"
                >
                  {{ option.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-tooltip>

        <el-divider direction="vertical" />

        <!-- 样式设置 -->
        <el-dropdown @command="handleStyleCommand" trigger="click">
          <el-button size="small" :disabled="isReadonlyMindmap">
            <el-icon><Brush /></el-icon> 样式
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="bold">
                <strong>B</strong> 加粗
              </el-dropdown-item>
              <el-dropdown-item command="italic">
                <em>I</em> 斜体
              </el-dropdown-item>
              <el-dropdown-item divided command="forecolor">
                <el-icon><Brush /></el-icon> 文字颜色
              </el-dropdown-item>
              <el-dropdown-item command="background">
                <el-icon><Grid /></el-icon> 背景颜色
              </el-dropdown-item>
              <el-dropdown-item divided command="fontsize">
                <el-icon><Setting /></el-icon> 字体大小
              </el-dropdown-item>
              <el-dropdown-item command="fontfamily">
                <el-icon><Reading /></el-icon> 字体
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 备注 -->
        <el-button size="small" @click="showNoteDialog" :disabled="isReadonlyMindmap || !canUseScopedPointActions">
          <el-icon><Memo /></el-icon> 备注
        </el-button>

        <!-- 图标 -->
        <el-dropdown @command="handleIconCommand" trigger="click">
          <el-button size="small" :disabled="isReadonlyMindmap || !canUseScopedPointActions">
            <el-icon><Star /></el-icon> 图标
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="check">✅ 完成</el-dropdown-item>
              <el-dropdown-item command="cross">❌ 失败</el-dropdown-item>
              <el-dropdown-item command="question">❓ 疑问</el-dropdown-item>
              <el-dropdown-item command="star">⭐ 重要</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-divider direction="vertical" />

        <!-- 视图控制 -->
        <el-button-group>
          <el-button size="small" @click="execCommand('ZoomIn')">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
          <el-button size="small" @click="execCommand('ZoomOut')">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <el-button size="small" @click="execCommand('Camera')">
            <el-icon><Location /></el-icon> 居中
          </el-button>
        </el-button-group>

        <!-- 节点属性控制 -->
        <div class="toolbar-section toolbar-scope-section">
          <el-tooltip :content="scopeToolbarTip" placement="bottom">
            <el-dropdown @command="handleScopeCommand" trigger="click" popper-class="minder-toolbar-dropdown">
              <el-button
                size="small"
                class="toolbar-icon-dropdown-button"
                :type="batchOperationMode === BATCH_OPERATION_MODE.selection ? 'default' : 'primary'"
                :plain="batchOperationMode === BATCH_OPERATION_MODE.selection"
                aria-label="处理范围"
              >
                <el-icon><Setting /></el-icon>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    command="selected-leaf-descendants"
                    :disabled="!hasSelection"
                    :class="{ 'is-active': isSelectedLeafBatchMode }"
                  >
                    批量处理测试点
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="all-leaf-nodes"
                    :class="{ 'is-active': isAllLeafBatchMode }"
                  >
                    处理全部测试点
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </el-tooltip>
        </div>

          <el-divider direction="vertical" />
          <!-- 节点类型 -->
          <div class="toolbar-section">
            <el-radio-group
              v-model="currentNodeType"
              size="small"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @change="setNodeType"
              class="toolbar-radio-group toolbar-radio-group--compact"
            >
              <el-radio
                v-for="option in nodeTypeOptions"
                :key="option.value"
                :value="option.value"
                border
                :title="option.name"
              >
                <span class="toolbar-node-type-code">{{ option.code }}</span>
              </el-radio>
            </el-radio-group>
            <el-button
              text
              size="small"
              class="toolbar-clear-button"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @click="clearNodeType"
            >
              清除
            </el-button>
          </div>

          <el-divider direction="vertical" />

          <!-- 优先级 -->
          <div class="toolbar-section">
            <el-radio-group
              v-model="currentPriority"
              size="small"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @change="setPriority"
              class="toolbar-radio-group toolbar-radio-group--compact"
            >
              <el-radio
                v-for="option in contextPriorityOptions"
                :key="option.value"
                :value="option.value"
                border
                :title="option.label"
              >
                <span class="priority-marker toolbar-priority-marker" :aria-label="option.label">
                  <svg viewBox="0 0 21 21" focusable="false" aria-hidden="true">
                    <path
                      :fill="option.darkColor"
                      d="M0,13c0,3.866,3.134,7,7,7h6c3.866,0,7-3.134,7-7V7H0V13z"
                      transform="translate(0.5 0.5)"
                    />
                    <path
                      :fill="option.lightColor"
                      d="M20,10c0,3.866-3.134,7-7,7H7c-3.866,0-7-3.134-7-7V7c0-3.866,3.134-7,7-7h6c3.866,0,7,3.134,7,7V10z"
                      opacity="0.8"
                      transform="translate(0.5 0.5)"
                    />
                    <text
                      x="10"
                      y="10.5"
                      text-anchor="middle"
                      font-style="italic"
                      font-size="12"
                      fill="white"
                      dy="5"
                    >{{ option.number }}</text>
                  </svg>
                </span>
              </el-radio>
            </el-radio-group>
            <el-button
              text
              size="small"
              class="toolbar-clear-button"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @click="clearPriority"
            >
              清除
            </el-button>
          </div>

          <el-divider direction="vertical" />

          <!-- 用例状态 -->
          <div class="toolbar-section">
            <el-radio-group
              v-model="currentStatus"
              size="small"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @change="setStatus"
              class="toolbar-radio-group toolbar-radio-group--compact"
            >
              <el-radio value="not_run" border title="未执行">⚪</el-radio>
              <el-radio value="pass" border title="通过">✅</el-radio>
              <el-radio value="fail" border title="失败">❌</el-radio>
              <el-radio value="block" border title="阻塞">🚫</el-radio>
              <el-radio value="not_test" border title="本版本不测"><span class="not-test-status-icon">⊘</span></el-radio>
            </el-radio-group>
            <el-button
              text
              size="small"
              class="toolbar-clear-button"
              :disabled="isReadonlyMindmap || !canUseScopedPointActions"
              @click="clearStatus"
            >
              清除
            </el-button>
          </div>

          </div>
        </transition>

        <!-- 主内容区：脑图 + 详情面板 -->
        <div class="main-content">
        <!-- 脑图容器 -->
        <div class="minder-container" :class="{ 'with-panel': showDetailPanel }">
          <div id="minder-editor" tabindex="0"></div>
          <div
            class="mindmap-overview"
            :class="{ 'is-collapsed': mindmapOverviewCollapsed }"
            aria-label="脑图统计与节点定位"
            :aria-expanded="!mindmapOverviewCollapsed"
            :data-collapsed="mindmapOverviewCollapsed"
            :data-navigation-key="mindmapOverviewNavigation.key"
            :data-navigation-index="mindmapOverviewNavigation.index + 1"
            :data-navigation-node-text="mindmapOverviewNavigation.nodeText"
          >
            <section
              v-for="group in mindmapOverviewGroups"
              :key="group.key"
              v-show="!mindmapOverviewCollapsed || group.key === 'modules'"
              class="mindmap-overview__group"
            >
              <div class="mindmap-overview__group-title">
                <el-icon><component :is="mindmapOverviewGroupIcons[group.key]" /></el-icon>
                <span class="mindmap-overview__group-label">{{ group.label }}</span>
                <el-tooltip
                  v-if="group.key === 'modules'"
                  :content="mindmapOverviewCollapsed ? '展开统计' : '收起统计'"
                  placement="right"
                >
                  <button
                    type="button"
                    class="mindmap-overview__toggle"
                    :aria-label="mindmapOverviewCollapsed ? '展开统计' : '收起统计'"
                    :aria-expanded="!mindmapOverviewCollapsed"
                    @click.stop="toggleMindmapOverview"
                  >
                    <el-icon>
                      <component :is="mindmapOverviewCollapsed ? ArrowDown : ArrowUp" />
                    </el-icon>
                  </button>
                </el-tooltip>
              </div>
              <div
                v-for="item in group.items"
                :key="item.key"
                v-show="!mindmapOverviewCollapsed"
                class="mindmap-overview__item"
                :class="[
                  `mindmap-overview__item--${item.tone}`,
                  {
                    'is-active': isMindmapOverviewItemActive(item.key),
                    'is-disabled': item.count === 0,
                  },
                ]"
                :data-overview-key="item.key"
                :data-overview-count="item.count"
                :data-overview-active="isMindmapOverviewItemActive(item.key)"
              >
                <button
                  type="button"
                  class="mindmap-overview__trigger"
                  :disabled="item.count === 0"
                  :title="`定位到第一个${item.label}节点`"
                  @click.stop="activateMindmapOverviewItem(item)"
                >
                  <span class="mindmap-overview__indicator" aria-hidden="true"></span>
                  <span class="mindmap-overview__item-label">{{ item.label }}</span>
                  <strong>{{ item.count }}</strong>
                </button>
                <div class="mindmap-overview__navigation">
                  <button
                    type="button"
                    class="mindmap-overview__arrow"
                    :disabled="item.count === 0"
                    :title="`上一个${item.label}节点`"
                    :aria-label="`上一个${item.label}节点`"
                    @click.stop="stepMindmapOverviewItem(item, -1)"
                  >
                    <el-icon><ArrowLeft /></el-icon>
                  </button>
                  <span class="mindmap-overview__position" aria-live="polite">
                    {{ getMindmapOverviewItemPosition(item) }}
                  </span>
                  <button
                    type="button"
                    class="mindmap-overview__arrow"
                    :disabled="item.count === 0"
                    :title="`下一个${item.label}节点`"
                    :aria-label="`下一个${item.label}节点`"
                    @click.stop="stepMindmapOverviewItem(item, 1)"
                  >
                    <el-icon><ArrowRight /></el-icon>
                  </button>
                </div>
              </div>
            </section>
          </div>
          <div
            v-if="mindmapContextMenu.visible"
            class="mindmap-context-menu"
            :class="{ 'open-left': mindmapContextMenu.openLeft }"
            :style="{ left: `${mindmapContextMenu.x}px`, top: `${mindmapContextMenu.y}px` }"
            @mousedown.stop
            @click.stop
          >
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">编辑</div>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuKityCommand('AppendChildNode')"
              >
                子节点
                <span class="mindmap-context-menu__shortcut">Tab</span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuKityCommand('AppendSiblingNode')"
              >
                同级节点
                <span class="mindmap-context-menu__shortcut">Enter</span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap || isRootSelected"
                @click="handleContextMenuKityCommand('RemoveNode')"
              >
                删除
                <span class="mindmap-context-menu__shortcut">Del</span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                @click="handleContextMenuCopy"
              >
                复制
                <span class="mindmap-context-menu__shortcut">Ctrl+C</span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap || isRootSelected"
                @click="handleContextMenuCut"
              >
                剪切
                <span class="mindmap-context-menu__shortcut">Ctrl+X</span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuPaste"
              >
                粘贴
                <span class="mindmap-context-menu__shortcut">Ctrl+V</span>
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">样式</div>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('bold')"
              >
                加粗
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('italic')"
              >
                斜体
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('forecolor')"
              >
                文字颜色
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('background')"
              >
                背景颜色
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('fontsize')"
              >
                字体大小
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuStyleCommand('fontfamily')"
              >
                字体
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">节点类型</div>
              <button
                v-for="option in nodeTypeOptions"
                :key="option.value"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuSetNodeType(option.value)"
              >
                {{ option.code }} {{ option.name }}
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuClearNodeType"
              >
                清除类型
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">状态</div>
              <button
                v-for="option in contextStatusOptions"
                :key="option.value"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuSetStatus(option.value)"
              >
                {{ option.icon }} {{ option.label }}
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuClearStatus"
              >
                清除状态
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">优先级</div>
              <button
                v-for="option in contextPriorityOptions"
                :key="option.value"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuSetPriority(option.value)"
              >
                <span class="mindmap-context-menu__label">
                  <span class="priority-marker priority-marker--context" :aria-label="option.label">
                    <svg viewBox="0 0 21 21" focusable="false" aria-hidden="true">
                      <path
                        :fill="option.darkColor"
                        d="M0,13c0,3.866,3.134,7,7,7h6c3.866,0,7-3.134,7-7V7H0V13z"
                        transform="translate(0.5 0.5)"
                      />
                      <path
                        :fill="option.lightColor"
                        d="M20,10c0,3.866-3.134,7-7,7H7c-3.866,0-7-3.134-7-7V7c0-3.866,3.134-7,7-7h6c3.866,0,7,3.134,7,7V10z"
                        opacity="0.8"
                        transform="translate(0.5 0.5)"
                      />
                      <text
                        x="10"
                        y="10.5"
                        text-anchor="middle"
                        font-style="italic"
                        font-size="12"
                        fill="white"
                        dy="5"
                      >{{ option.number }}</text>
                    </svg>
                  </span>
                  <span>{{ option.label }}</span>
                </span>
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuClearPriority"
              >
                清除优先级
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">图标</div>
              <button
                v-for="(option, command) in customIconOptions"
                :key="command"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuSetIcon(command)"
              >
                {{ option.icon }} {{ option.label }}
              </button>
            </div>
            <div class="mindmap-context-menu__section">
              <div class="mindmap-context-menu__title" tabindex="0" role="menuitem" aria-haspopup="menu">更多</div>
              <button
                v-if="isRequirementAnalysisMindmap"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuTestPointRefine"
              >
                测试点细化
              </button>
              <button
                v-if="isRequirementClarificationContextNode"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuRequirementClarificationAction('refine')"
              >
                需求打磨
              </button>
              <button
                v-if="isRequirementClarificationContextNode"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuRequirementClarificationAction('rewrite')"
              >
                需求重写
              </button>
              <button
                v-if="isRequirementClarificationContextNode"
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuRequirementClarificationAction('accept')"
              >
                确认需求
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                :disabled="isReadonlyMindmap"
                @click="handleContextMenuNote"
              >
                备注
              </button>
              <button
                type="button"
                class="mindmap-context-menu__item"
                @click="handleContextMenuKityCommand('Camera')"
              >
                居中
              </button>
            </div>
          </div>
        </div>

        <!-- 节点详情面板 -->
        <transition name="slide-left">
          <div v-if="showDetailPanel" class="detail-panel">
            <div class="panel-header">
              <h3>节点详情</h3>
            </div>

            <div class="panel-content" v-if="hasSelection">
              <el-tabs v-model="detailPanelActiveTab" class="detail-panel-tabs">
                <el-tab-pane label="节点详情" name="node">
                  <!-- 用例详细信息 -->
                  <el-form label-width="90px" size="small" :disabled="isReadonlyMindmap">
                    <h4 style="margin-top: 0;">用例详细信息</h4>

                    <el-form-item label="用例ID">
                      <el-input v-model="nodeData.caseId" @blur="updateNodeData" placeholder="TC-XXX-001" />
                    </el-form-item>

                    <el-form-item label="前置条件">
                      <el-input
                        v-model="nodeData.preCondition"
                        type="textarea"
                        :rows="4"
                        @blur="updateNodeData"
                        placeholder="执行此用例前需要满足的条件"
                        :autosize="{ minRows: 4, maxRows: 8 }"
                      />
                    </el-form-item>

                    <el-form-item label="测试步骤">
                      <el-input
                        v-model="nodeData.steps"
                        type="textarea"
                        :rows="8"
                        @blur="updateNodeData"
                        placeholder="1. 步骤一&#10;2. 步骤二&#10;3. 步骤三"
                        :autosize="{ minRows: 8, maxRows: 16 }"
                      />
                    </el-form-item>

                    <el-form-item label="期望结果">
                      <el-input
                        v-model="nodeData.expect"
                        type="textarea"
                        :rows="5"
                        @blur="updateNodeData"
                        placeholder="期望的测试结果"
                        :autosize="{ minRows: 5, maxRows: 10 }"
                      />
                    </el-form-item>

                    <el-form-item label="备注">
                      <el-input
                        v-model="nodeData.remark"
                        type="textarea"
                        :rows="4"
                        @blur="updateNodeData"
                        placeholder="其他补充说明"
                        :autosize="{ minRows: 4, maxRows: 8 }"
                      />
                    </el-form-item>

                    <template v-if="currentNodeType === 'testpoint'">
                      <el-divider content-position="left">评审信息</el-divider>

                      <el-form-item label="评审意见">
                        <el-input
                          v-model="nodeData.reviewOpinion"
                          type="textarea"
                          :rows="4"
                          @input="handleReviewOpinionInput"
                          @blur="updateNodeData"
                          placeholder="请输入评审意见"
                          :autosize="{ minRows: 4, maxRows: 8 }"
                        />
                      </el-form-item>

                      <el-form-item label="评审时间">
                        <el-date-picker
                          v-model="nodeData.reviewTime"
                          type="datetime"
                          value-format="YYYY-MM-DD HH:mm:ss"
                          format="YYYY-MM-DD HH:mm:ss"
                          placeholder="选择评审时间"
                          @change="updateNodeData"
                        />
                      </el-form-item>

                      <el-form-item label="评审人">
                        <el-select
                          v-model="nodeData.reviewerId"
                          filterable
                          clearable
                          placeholder="请选择评审人"
                          @change="handleReviewerChange"
                        >
                          <el-option
                            v-for="user in reviewerOptions"
                            :key="user.id"
                            :label="resolveUserDisplayName(user, '未知')"
                            :value="user.id"
                          />
                        </el-select>
                      </el-form-item>

                      <el-form-item label="是否已处理">
                        <el-switch
                          v-model="nodeData.reviewStatus"
                          :active-value="'未处理'"
                          :inactive-value="'已处理'"
                          :active-text="hasReviewOpinion ? '未处理' : ''"
                          :inactive-text="hasReviewOpinion ? '已处理' : ''"
                          :disabled="!hasReviewOpinion"
                          @change="handleReviewStatusChange"
                        />
                      </el-form-item>
                    </template>
                  </el-form>
                </el-tab-pane>
                <el-tab-pane label="需求事实" name="facts">
                  <div v-if="currentRequirementFacts.length" class="requirement-facts">
                    <div
                      v-for="fact in currentRequirementFacts"
                      :key="fact.id || `${fact.factType}-${fact.title}`"
                      class="requirement-fact-card"
                    >
                      <div class="fact-card-header">
                        <el-tag size="small" effect="plain">{{ formatRequirementFactType(fact.factType) }}</el-tag>
                        <strong>{{ fact.title || fact.name || '未命名需求事实' }}</strong>
                      </div>
                      <div v-if="fact.nodePath.length" class="fact-path">{{ fact.nodePath.join(' / ') }}</div>
                      <div v-if="formatRequirementFactSource(fact.source)" class="fact-source">
                        来源：{{ formatRequirementFactSource(fact.source) }}
                      </div>
                      <div v-if="requirementFactPropertyEntries(fact.properties).length" class="fact-section">
                        <div class="fact-section-title">属性</div>
                        <div
                          v-for="entry in requirementFactPropertyEntries(fact.properties)"
                          :key="entry.key"
                          class="fact-property-row"
                        >
                          <span>{{ entry.label }}</span>
                          <b>{{ entry.value }}</b>
                        </div>
                      </div>
                      <div v-if="requirementFactPropertyEntries(fact.verificationHints).length" class="fact-section">
                        <div class="fact-section-title">验证提示</div>
                        <div
                          v-for="entry in requirementFactPropertyEntries(fact.verificationHints)"
                          :key="entry.key"
                          class="fact-property-row"
                        >
                          <span>{{ entry.label }}</span>
                          <b>{{ entry.value }}</b>
                        </div>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="当前节点暂无需求事实" />
                </el-tab-pane>
              </el-tabs>
            </div>

            <div class="panel-content" v-else>
              <el-empty description="请选择一个节点" />
            </div>
          </div>
        </transition>
      </div>
      </div>
    </el-card>

    <!-- 标签管理对话框 -->
    <el-dialog v-model="tagDialogVisible" title="管理标签" width="500px">
      <el-form>
        <el-form-item label="添加标签">
          <el-input
            v-model="newTag"
            placeholder="输入标签名称"
            @keyup.enter="addTag"
          >
            <template #append>
              <el-button @click="addTag">添加</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="当前标签">
          <div class="tags-container">
            <el-tag
              v-for="tag in currentTags"
              :key="tag"
              closable
              @close="removeTag(tag)"
              style="margin-right: 5px; margin-bottom: 5px"
              :type="getTagType(tag)"
            >
              {{ tag }}
            </el-tag>
            <span v-if="currentTags.length === 0" style="color: #999">暂无标签</span>
          </div>
        </el-form-item>
        <el-form-item label="常用标签">
          <el-button-group>
            <el-button size="small" @click="addPresetTag('正向')">正向</el-button>
            <el-button size="small" @click="addPresetTag('负向')">负向</el-button>
            <el-button size="small" @click="addPresetTag('接口')">接口</el-button>
            <el-button size="small" @click="addPresetTag('UI')">UI</el-button>
            <el-button size="small" @click="addPresetTag('冒烟')">冒烟</el-button>
            <el-button size="small" @click="addPresetTag('核心')">核心</el-button>
            <el-button size="small" @click="addPresetTag('性能')">性能</el-button>
            <el-button size="small" @click="addPresetTag('安全')">安全</el-button>
          </el-button-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 过滤对话框 -->
    <el-dialog v-model="filterDialogVisible" title="过滤用例" width="500px">
      <el-form label-width="80px">
        <el-form-item label="优先级">
          <el-checkbox-group v-model="filterOptions.priorities">
            <el-checkbox :value="1">🔴 P1</el-checkbox>
            <el-checkbox :value="2">🟠 P2</el-checkbox>
            <el-checkbox :value="3">🟡 P3</el-checkbox>
            <el-checkbox :value="4">🔵 P4</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-checkbox-group v-model="filterOptions.statuses">
            <el-checkbox value="not_run">⚪ 未执行</el-checkbox>
            <el-checkbox value="pass">✅ 通过</el-checkbox>
            <el-checkbox value="fail">❌ 失败</el-checkbox>
            <el-checkbox value="block">🚫 阻塞</el-checkbox>
            <el-checkbox value="not_test">⊘ 本版本不测</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filterOptions.tag" placeholder="输入标签名称（留空表示不过滤）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="filterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyFilter">应用过滤</el-button>
      </template>
    </el-dialog>

    <!-- 备注对话框 -->
    <el-dialog v-model="noteDialogVisible" title="编辑备注" width="600px">
      <el-tabs v-model="noteTab" type="border-card">
        <el-tab-pane label="Markdown" name="markdown">
          <el-input
            v-model="currentNote"
            type="textarea"
            :rows="10"
            placeholder="支持Markdown语法&#10;&#10;# 标题&#10;- 列表项&#10;**粗体** *斜体*&#10;```代码块```"
          />
        </el-tab-pane>
        <el-tab-pane label="预览" name="preview">
          <div class="note-preview" v-html="renderedNote"></div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="noteDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNote">保存备注</el-button>
      </template>
    </el-dialog>

    <!-- 颜色选择对话框 -->
    <el-dialog v-model="colorDialogVisible" :title="colorDialogTitle" width="400px">
      <div class="color-picker-container">
        <el-color-picker v-model="selectedColor" show-alpha />
        <div class="color-presets">
          <h4>预设颜色</h4>
          <div class="color-grid">
            <div
              v-for="color in presetColors"
              :key="color"
              class="color-item"
              :style="{ backgroundColor: color }"
              @click="selectedColor = color"
            ></div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="colorDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyColor">应用</el-button>
      </template>
    </el-dialog>

    <!-- 字体大小对话框 -->
    <el-dialog v-model="fontSizeDialogVisible" title="设置字体大小" width="300px">
      <el-slider v-model="fontSize" :min="12" :max="48" :step="2" show-stops />
      <div style="text-align: center; margin-top: 10px">
        当前大小: {{ fontSize }}px
      </div>
      <template #footer>
        <el-button @click="fontSizeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyFontSize">应用</el-button>
      </template>
    </el-dialog>

    <!-- 字体选择对话框 -->
    <el-dialog v-model="fontFamilyDialogVisible" title="设置字体" width="400px">
      <el-radio-group v-model="fontFamily" style="display: flex; flex-direction: column; gap: 10px">
        <el-radio value="Microsoft YaHei, 微软雅黑">微软雅黑</el-radio>
        <el-radio value="SimSun, 宋体">宋体</el-radio>
        <el-radio value="SimHei, 黑体">黑体</el-radio>
        <el-radio value="KaiTi, 楷体">楷体</el-radio>
        <el-radio value="Arial, sans-serif">Arial</el-radio>
        <el-radio value="Times New Roman, serif">Times New Roman</el-radio>
        <el-radio value="Courier New, monospace">Courier New (等宽)</el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="fontFamilyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyFontFamily">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, watch } from 'vue'
import { ElLoading, ElMessage } from 'element-plus'
import {
  DocumentAdd, Download, Upload, Edit, ZoomIn, ZoomOut,
  Plus, Delete, PriceTag, Filter, RefreshLeft, RefreshRight,
  CopyDocument, Scissor, DocumentCopy, ArrowDown, ArrowUp, Document, Picture, PictureFilled,
  Brush, EditPen, Grid, Reading, Memo, Star, Setting, Location, ArrowLeft, ArrowRight, Warning,
  FullScreen, ScaleToOriginal
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import { useRoute, useRouter } from 'vue-router'
import { exportMindmapDataToXMindBlob, getMindmapRootText, parseXMindFileToMindmapData } from '@/utils/xmindMinder'
import {
  annotateMindmapModuleMatches,
  buildManualCategoryMatchIndex,
  collectMindmapOverview,
} from '@/utils/mindmapCategoryMatching'
import { getUserDisplayName as resolveUserDisplayName } from '@/utils/userDisplay'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const props = defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
  initialMindmapId: {
    type: [String, Number],
    default: '',
  },
  initialProjectId: {
    type: [String, Number],
    default: '',
  },
  initialMindmapScope: {
    type: String,
    default: '',
  },
  returnPath: {
    type: String,
    default: '',
  },
  returnQuery: {
    type: Object,
    default: null,
  },
  maximized: {
    type: Boolean,
    default: false,
  },
  showMaximizeAction: {
    type: Boolean,
    default: false,
  },
  showDefectAction: {
    type: Boolean,
    default: true,
  },
  externalToolbar: {
    type: Boolean,
    default: false,
  },
  initialToolbarVisible: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['back', 'loaded', 'saved', 'testpoint-refine-request', 'requirement-clarification-action-request', 'toggle-maximized', 'toolbar-state-change'])

const editorRootRef = ref(null)

const getSingleQueryValue = value => (Array.isArray(value) ? value[0] : value)
const isTruthyQueryFlag = value => {
  const normalizedValue = String(getSingleQueryValue(value) || '').trim().toLowerCase()
  return ['1', 'true', 'yes', 'readonly', 'view'].includes(normalizedValue)
}
const isReadonlyMindmap = computed(() => (
  isTruthyQueryFlag(route.query.readonly) ||
  String(getSingleQueryValue(route.query.mode) || '').trim().toLowerCase() === 'view'
))
const READONLY_MINDMAP_MESSAGE = '当前为只读查看模式，不能编辑脑图'
const ensureMindmapEditable = (message = READONLY_MINDMAP_MESSAGE) => {
  if (!isReadonlyMindmap.value) {
    return true
  }
  ElMessage.warning(message)
  return false
}
const MUTATING_MINDER_COMMANDS = new Set([
  'AppendChildNode',
  'AppendSiblingNode',
  'RemoveNode',
  'Bold',
  'Italic',
  'ForeColor',
  'Background',
  'FontSize',
  'FontFamily',
  'Theme',
  'Template',
  'text',
])
const isMutatingMinderCommand = command => MUTATING_MINDER_COMMANDS.has(String(command || ''))

const parseReturnQuery = () => {
  if (props.returnQuery && typeof props.returnQuery === 'object') {
    return props.returnQuery
  }

  const rawReturnQuery = route.query.return_query
  const rawValue = getSingleQueryValue(rawReturnQuery)
  if (!rawValue) return null

  try {
    const parsed = JSON.parse(decodeURIComponent(String(rawValue)))
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch (error) {
    console.log('解析返回筛选条件失败:', error)
    return null
  }
}

const getContextQueryValue = key => {
  const propLookup = {
    project_id: props.initialProjectId,
  }
  const propValue = propLookup[key]
  if (propValue !== undefined && propValue !== null && propValue !== '') {
    return propValue
  }

  const directValue = getSingleQueryValue(route.query[key])
  if (directValue !== undefined && directValue !== null && directValue !== '') {
    return directValue
  }

  const returnQuery = parseReturnQuery()
  return getSingleQueryValue(returnQuery?.[key])
}

const normalizeMindmapScope = value =>
  String(value || '').trim() === 'requirement_analysis' ? 'requirement_analysis' : 'testing'

const loadedMindmapScope = ref('')
const currentMindmapScope = computed(() => normalizeMindmapScope(
  props.initialMindmapScope ||
  loadedMindmapScope.value ||
  getSingleQueryValue(route.query.mindmap_scope) ||
  getSingleQueryValue(route.query.scope),
))
const isRequirementAnalysisMindmap = computed(() => currentMindmapScope.value === 'requirement_analysis')

const nodeTypeOptions = computed(() => {
  const baseOptions = [
    { value: 'module', code: 'M', name: '模块' },
    { value: 'case', code: 'C', name: '用例' },
    { value: 'requirement', code: 'R', name: '需求' },
    { value: 'page', code: 'PG', name: '页面' },
    { value: 'function', code: 'F', name: '功能' },
    { value: 'testpoint', code: 'P', name: '测试点' },
  ]

  if (!isRequirementAnalysisMindmap.value) {
    return baseOptions
  }

  return baseOptions.filter(option => option.value !== 'case')
})

const nodeTypeLabels = {
  module: 'M',
  case: 'C',
  requirement: 'R',
  page: 'PG',
  function: 'F',
  testpoint: 'P',
}
const validNodeTypes = new Set(Object.keys(nodeTypeLabels))

const customIconOptions = {
  check: { icon: '✅', label: '完成' },
  cross: { icon: '❌', label: '失败' },
  question: { icon: '❓', label: '疑问' },
  star: { icon: '⭐', label: '重要' },
}
const customIconCommands = new Set(Object.keys(customIconOptions))
const contextPriorityOptions = [
  { value: 1, number: '1', label: 'P1', lightColor: '#FF1200', darkColor: '#840023' },
  { value: 2, number: '2', label: 'P2', lightColor: '#0074FF', darkColor: '#01467F' },
  { value: 3, number: '3', label: 'P3', lightColor: '#00AF00', darkColor: '#006300' },
  { value: 4, number: '4', label: 'P4', lightColor: '#FF962E', darkColor: '#B25000' },
]
const contextStatusOptions = [
  { value: 'not_run', icon: '⚪', label: '未执行' },
  { value: 'pass', icon: '✅', label: '通过' },
  { value: 'fail', icon: '❌', label: '失败' },
  { value: 'block', icon: '🚫', label: '阻塞' },
  { value: 'not_test', icon: '⊘', label: '本版本不测' },
]

const parsePowerShellObjectString = value => {
  const text = String(value || '').trim()
  if (!text.startsWith('@{') || !text.endsWith('}')) {
    return null
  }

  const result = {}
  text.slice(2, -1).split(';').forEach(part => {
    const separatorIndex = part.indexOf('=')
    if (separatorIndex < 0) return
    const key = part.slice(0, separatorIndex).trim()
    const rawValue = part.slice(separatorIndex + 1).trim()
    if (key) {
      result[key] = rawValue
    }
  })
  return Object.keys(result).length ? result : null
}

const normalizeMindmapNodeData = (value, fallbackText = '未命名节点') => {
  let data = value

  if (typeof data === 'string') {
    data = parsePowerShellObjectString(data) || { text: data }
  }

  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    data = {}
  }

  const normalized = { ...data }
  const text = String(normalized.text || fallbackText || '未命名节点').trim()
  normalized.text = text || '未命名节点'

  if (normalized.nodeType && !validNodeTypes.has(normalized.nodeType)) {
    normalized.nodeType = 'module'
  }

  if (Array.isArray(normalized.resource)) {
    normalized.resource = normalized.resource
      .map(item => String(item || '').trim())
      .filter(Boolean)
  }

  return normalized
}

const normalizeMindmapNode = (node, fallbackText = '未命名节点') => {
  if (typeof node === 'string') {
    const parsedData = parsePowerShellObjectString(node)
    return {
      data: normalizeMindmapNodeData(parsedData || { text: node }, fallbackText),
      children: [],
    }
  }

  const source = node && typeof node === 'object' && !Array.isArray(node) ? node : {}
  const data = normalizeMindmapNodeData(source.data, fallbackText)
  const rawChildren = Array.isArray(source.children) ? source.children : []
  const children = rawChildren
    .map(child => normalizeMindmapNode(child))
    .filter(child => String(child?.data?.text || '').trim())

  return {
    ...source,
    data,
    children,
  }
}

const normalizeMindmapData = value => {
  const source = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const root = normalizeMindmapNode(source.root, '新建脑图')
  root.data.nodeType = root.data.nodeType || 'module'
  return {
    ...source,
    root,
    template: source.template || 'right',
    theme: source.theme || 'fresh-blue',
    version: source.version || '1.4.43',
  }
}

const countMindmapNodes = node => {
  if (!node || typeof node !== 'object') return 0
  return 1 + (Array.isArray(node.children) ? node.children : [])
    .reduce((total, child) => total + countMindmapNodes(child), 0)
}

const countMindmapDescendants = mindmapData =>
  Math.max(0, countMindmapNodes(mindmapData?.root) - 1)

const hasMalformedMindmapNode = node => {
  if (!node || typeof node !== 'object' || Array.isArray(node)) {
    return true
  }
  if (!node.data || typeof node.data !== 'object' || Array.isArray(node.data)) {
    return true
  }
  if (!Array.isArray(node.children)) {
    return true
  }
  return node.children.some(child => hasMalformedMindmapNode(child))
}

const isMalformedMindmapData = value => (
  !value ||
  typeof value !== 'object' ||
  Array.isArray(value) ||
  hasMalformedMindmapNode(value.root)
)

// KityMinder实例
let minder = null
const normalizeListResponse = (data) => {
  if (Array.isArray(data)) {
    return { results: data, count: data.length }
  }

  return {
    results: data?.results || [],
    count: data?.count ?? data?.results?.length ?? 0,
  }
}

const padDatePart = value => String(value).padStart(2, '0')

const formatDateTimeForPicker = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(String(value || '').replace(' ', 'T'))
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return ''
  }

  return [
    date.getFullYear(),
    padDatePart(date.getMonth() + 1),
    padDatePart(date.getDate())
  ].join('-') + ` ${[
    padDatePart(date.getHours()),
    padDatePart(date.getMinutes()),
    padDatePart(date.getSeconds())
  ].join(':')}`
}

const normalizeReviewTimeValue = (value) => {
  const normalizedValue = String(value || '').trim()
  if (!normalizedValue) {
    return ''
  }

  const parsedValue = new Date(normalizedValue.includes('T') ? normalizedValue : normalizedValue.replace(' ', 'T'))
  if (!(parsedValue instanceof Date) || Number.isNaN(parsedValue.getTime())) {
    return normalizedValue
  }

  return formatDateTimeForPicker(parsedValue)
}

// 当前选中的节点文本
const nodeText = ref('')
// 是否有选中的节点
const hasSelection = ref(false)
// 是否选中了根节点
const isRootSelected = ref(false)
// 当前主题和布局
const currentTheme = ref('fresh-blue')
const currentTemplate = ref('right')
const templateOptions = Object.freeze([
  { label: '思维导图', value: 'default' },
  { label: '组织结构图', value: 'structure' },
  { label: '目录组织图', value: 'filetree' },
  { label: '右侧逻辑图', value: 'right' },
  { label: '天盘图', value: 'tianpan' }
])
const themeOptions = Object.freeze([
  { label: '天空蓝', value: 'fresh-blue' },
  { label: '文艺绿', value: 'fresh-green' },
  { label: '脑残粉', value: 'fresh-pink' },
  { label: '清新红', value: 'fresh-red' },
  { label: '简约黑', value: 'classic' },
  { label: '简约白', value: 'classic-compact' },
  { label: '鱼骨图', value: 'fish' },
  { label: '线条图', value: 'wire' }
])
const currentTemplateLabel = computed(() => (
  templateOptions.find(option => option.value === currentTemplate.value)?.label || '脑图类型'
))
const currentThemeLabel = computed(() => (
  themeOptions.find(option => option.value === currentTheme.value)?.label || '颜色'
))

// 编辑状态
const canUndo = ref(false)
const canRedo = ref(false)
const hasClipboard = ref(false)
let mindmapClipboardNodes = []
const SYSTEM_CLIPBOARD_TEXT_PENDING = Symbol('system-clipboard-text-pending')
let systemClipboardTextWhenMindmapClipboardSet = null

// 节点属性
const currentNodeType = ref('')
const currentPriority = ref(null)
const currentStatus = ref('')
const currentTags = ref([])
const reviewerOptions = ref([])
const currentUserDisplayName = computed(() => resolveUserDisplayName(userStore.user, '当前用户'))
const currentUserId = computed(() => userStore.user?.id ?? null)

const BATCH_OPERATION_MODE = {
  selection: 'selection',
  selectedLeafDescendants: 'selected-leaf-descendants',
  allLeafNodes: 'all-leaf-nodes'
}

const batchOperationMode = ref(BATCH_OPERATION_MODE.selection)
const isSelectedLeafBatchMode = computed(() => batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants)
const isAllLeafBatchMode = computed(() => batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes)
const canUseScopedPointActions = computed(() => {
  return batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes || hasSelection.value
})
const scopeToolbarTip = computed(() => {
  if (batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants) {
    return '处理范围：所选节点下全部末级节点'
  }

  if (batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes) {
    return '处理范围：整张脑图全部末级节点'
  }

  return '处理范围'
})
const noteDialogTitle = computed(() => {
  if (batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants) {
    return '批量处理测试点备注'
  }

  if (batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes) {
    return '处理全部测试点备注'
  }

  return '编辑备注'
})

// 备注
const currentNote = ref('')
const noteTab = ref('markdown')
const detailPanelActiveTab = ref('node')
const renderedNote = computed(() => {
  // 简单的Markdown渲染（实际项目可用marked库）
  return currentNote.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/\n/g, '<br>')
})

// 节点详细数据
const nodeData = ref({
  caseId: '',
  preCondition: '',
  steps: '',
  expect: '',
  remark: '',
  reviewOpinion: '',
  reviewTime: '',
  reviewerId: null,
  reviewerName: '',
  reviewStatus: '',
  note: '',
  requirementFacts: []
})
const hasReviewOpinion = computed(() => Boolean(String(nodeData.value.reviewOpinion || '').trim()))
const currentRequirementFacts = computed(() => normalizeRequirementFacts(nodeData.value.requirementFacts))

const REQUIREMENT_FACT_TYPE_LABELS = {
  page_context: '页面上下文',
  navigation: '菜单导航',
  tab: '页签',
  scope_control: '数据范围',
  query_control: '查询控件',
  filter_field: '筛选字段',
  list_field: '列表字段',
  action: '操作',
  row_action: '行操作',
  more_menu: '更多菜单',
  menu_action: '菜单操作',
  dialog_prompt: '弹窗提示',
  requirement_rule: '需求规则',
  visual_emphasis: '视觉标注',
}

const REQUIREMENT_FACT_PROPERTY_LABELS = {
  control_type: '控件类型',
  raw_control_type: '原始控件类型',
  field_type: '字段类型',
  display_name: '显示名称',
  placeholder: '提示文本',
  default_value: '默认值',
  default_state: '默认状态',
  current_value: '当前值',
  option_format: '选项格式',
  options: '选项值',
  supported_query_fields: '支持查询字段',
  related_table_field: '关联列表字段',
  rule: '规则',
  text: '需求描述',
  category: '分类',
  target_kind: '目标类型',
  target_name: '目标名称',
  confidence: '置信度',
  match_reason: '匹配原因',
  owner_action: '归属操作',
  prompt_type: '提示类型',
  trigger_scenario: '触发场景',
  operation: '操作',
  expected: '预期结果',
  check: '检查点',
  visual_mark: '视觉标注',
  visual_mark_reason: '标注原因',
}

const normalizeRequirementFacts = value => {
  const facts = Array.isArray(value) ? value : []
  return facts
    .filter(fact => fact && typeof fact === 'object')
    .map(fact => ({
      id: String(fact.id || '').trim(),
      factType: String(fact.fact_type || fact.factType || '').trim(),
      title: String(fact.title || '').trim(),
      name: String(fact.name || '').trim(),
      nodePath: Array.isArray(fact.node_path)
        ? fact.node_path.map(item => String(item || '').trim()).filter(Boolean)
        : (Array.isArray(fact.nodePath) ? fact.nodePath.map(item => String(item || '').trim()).filter(Boolean) : []),
      source: fact.source && typeof fact.source === 'object' ? fact.source : {},
      properties: fact.properties && typeof fact.properties === 'object' ? fact.properties : {},
      verificationHints: fact.verification_hints && typeof fact.verification_hints === 'object'
        ? fact.verification_hints
        : (fact.verificationHints && typeof fact.verificationHints === 'object' ? fact.verificationHints : {}),
      relations: Array.isArray(fact.relations) ? fact.relations : [],
      evidence: Array.isArray(fact.evidence) ? fact.evidence : [],
    }))
}

const formatRequirementFactType = type => REQUIREMENT_FACT_TYPE_LABELS[type] || String(type || '需求事实')

const formatRequirementFactSource = source => {
  if (!source || typeof source !== 'object') return ''
  const labels = []
  if (source.prototype) labels.push('原型')
  if (source.text_requirement) labels.push('需求文字')
  if (source.red_visual) labels.push('红色标注')
  return labels.join('、')
}

const formatRequirementFactValue = value => {
  if (Array.isArray(value)) {
    return value
      .map(item => formatRequirementFactValue(item))
      .filter(Boolean)
      .join('、')
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
      .filter(([, entryValue]) => entryValue !== null && entryValue !== undefined && entryValue !== '')
      .slice(0, 8)
      .map(([key, entryValue]) => `${REQUIREMENT_FACT_PROPERTY_LABELS[key] || key}：${formatRequirementFactValue(entryValue)}`)
    return entries.join('；')
  }
  return String(value ?? '').trim()
}

const requirementFactPropertyEntries = properties => {
  if (!properties || typeof properties !== 'object') return []
  return Object.entries(properties)
    .filter(([key, value]) => {
      if (['raw', 'source_geometry', 'color_fields', 'dialog_structure'].includes(key)) return false
      if (value === null || value === undefined || value === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return false
      return true
    })
    .map(([key, value]) => ({
      key,
      label: REQUIREMENT_FACT_PROPERTY_LABELS[key] || key,
      value: formatRequirementFactValue(value),
    }))
    .filter(entry => entry.value)
}

const findReviewerOptionById = (userId) => {
  const normalizedUserId = String(userId ?? '').trim()
  if (!normalizedUserId) {
    return null
  }

  return reviewerOptions.value.find(user => String(user?.id ?? '').trim() === normalizedUserId) || null
}

const resolveReviewerName = (userId, fallback = '') => {
  const matchedUser = findReviewerOptionById(userId)
  return resolveUserDisplayName(matchedUser, fallback)
}

const loadReviewerOptions = async () => {
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
    reviewerOptions.value = [...optionMap.values()]
  } catch (error) {
    reviewerOptions.value = userStore.user?.id ? [userStore.user] : []
    console.error('加载评审人列表失败:', error)
  }
}

// UI控制
const showToolbar = ref(props.initialToolbarVisible !== false)
const showDetailPanel = ref(false)
const tagDialogVisible = ref(false)
const filterDialogVisible = ref(false)
const noteDialogVisible = ref(false)
const colorDialogVisible = ref(false)
const colorDialogTitle = ref('')
const colorDialogType = ref('') // 'forecolor' or 'background'
const fontSizeDialogVisible = ref(false)
const fontFamilyDialogVisible = ref(false)
const newTag = ref('')

watch([tagDialogVisible, filterDialogVisible, noteDialogVisible, colorDialogVisible, fontSizeDialogVisible, fontFamilyDialogVisible], (values, previousValues = []) => {
  const wasAnyDialogOpen = previousValues.some(Boolean)
  const isAnyDialogOpen = values.some(Boolean)

  if (wasAnyDialogOpen && !isAnyDialogOpen) {
    scheduleEditorRefocus(80)
  }
})

// 过滤选项
const filterOptions = ref({
  priorities: [],
  statuses: [],
  tag: ''
})
const hasFilter = ref(false)

// 脑图数据
const minderData = ref({
  root: {
    data: {
      text: '新建脑图',
      nodeType: 'module'
    },
    children: []
  }
})

// 当前脑图ID（编辑模式时使用）
const currentMindmapId = ref(null)
const currentProjectId = ref('')
const currentVersionId = ref('')
const currentCategoryId = ref('')
const currentRequirementKey = ref('')
const currentResponsibilityGroup = ref('')
const currentFrontendDeveloper = ref('')
const currentBackendDeveloper = ref('')
const manualCategoryTree = ref([])
let manualCategoryMatchIndex = buildManualCategoryMatchIndex([])
let moduleCategoryMatchReady = false
let moduleOverviewRefreshTimer = null
const mindmapOverview = ref(collectMindmapOverview(null))
const mindmapOverviewCollapsed = ref(true)
const mindmapOverviewNavigation = ref({
  key: '',
  index: -1,
  nodeText: '',
})
const mindmapOverviewGroupIcons = Object.freeze({
  modules: Grid,
  testpoints: PriceTag,
  reviews: Memo,
})
const mindmapOverviewGroups = computed(() => [
  {
    key: 'modules',
    label: '模块',
    items: [
      { key: 'module-unmatched', label: '未匹配', count: mindmapOverview.value.modules.unmatched, tone: 'danger' },
      { key: 'module-all', label: '全部模块', count: mindmapOverview.value.modules.total, tone: 'module' },
    ],
  },
  {
    key: 'testpoints',
    label: '测试点',
    items: [
      { key: 'testpoint-not_run', label: '未执行', count: mindmapOverview.value.testpoints.not_run, tone: 'not-run' },
      { key: 'testpoint-pass', label: '通过', count: mindmapOverview.value.testpoints.pass, tone: 'pass' },
      { key: 'testpoint-fail', label: '失败', count: mindmapOverview.value.testpoints.fail, tone: 'fail' },
      { key: 'testpoint-block', label: '阻塞', count: mindmapOverview.value.testpoints.block, tone: 'block' },
      { key: 'testpoint-not_test', label: '本版本不测', count: mindmapOverview.value.testpoints.not_test, tone: 'not-test' },
    ],
  },
  {
    key: 'reviews',
    label: '评审',
    items: [
      { key: 'review-unprocessed', label: '未处理', count: mindmapOverview.value.reviews.unprocessed, tone: 'review' },
      { key: 'review-all', label: '全部评审', count: mindmapOverview.value.reviews.total, tone: 'review-all' },
    ],
  },
])
const toggleMindmapOverview = () => {
  mindmapOverviewCollapsed.value = !mindmapOverviewCollapsed.value
}
// 脑图名称
const mindmapName = ref('新建脑图')
// 脑图描述
const mindmapDescription = ref('')
const MINDMAP_AUTO_SAVE_DELAY = 600
const HISTORY_MAX_STEPS = 100

const refreshOverviewFromMindmapData = data => {
  mindmapOverview.value = collectMindmapOverview(data?.root)
}

const annotateModuleMatchesInData = data => {
  if (moduleCategoryMatchReady) {
    annotateMindmapModuleMatches(data, manualCategoryMatchIndex)
  }
  refreshOverviewFromMindmapData(data)
  return data
}

const loadManualCategoryMatchIndex = async projectId => {
  const normalizedProjectId = String(projectId || '').trim()
  if (!normalizedProjectId) {
    manualCategoryTree.value = []
    manualCategoryMatchIndex = buildManualCategoryMatchIndex([])
    moduleCategoryMatchReady = true
    annotateModuleMatchesInData(minderData.value)
    return
  }

  try {
    const response = await api.get('/testcases/manual-categories/', {
      params: { project: normalizedProjectId },
      timeout: 0,
    })
    const categories = Array.isArray(response.data)
      ? response.data
      : (Array.isArray(response.data?.results) ? response.data.results : [])
    manualCategoryTree.value = categories
    manualCategoryMatchIndex = buildManualCategoryMatchIndex(categories)
    moduleCategoryMatchReady = true
    annotateModuleMatchesInData(minderData.value)
  } catch (error) {
    moduleCategoryMatchReady = false
    console.error('加载目录树模块匹配索引失败:', error)
    ElMessage.warning('目录树加载失败，暂时无法更新模块匹配状态')
    refreshOverviewFromMindmapData(minderData.value)
  }
}

// 获取当前选中的节点
const getCurrentNode = () => {
  if (!minder) return null
  return minder.getSelectedNode()
}

const getNodeChildren = (node) => {
  if (!node) return []

  if (typeof node.getChildren === 'function') {
    return node.getChildren() || []
  }

  return Array.isArray(node.children) ? node.children : []
}

const resetMindmapOverviewNavigation = () => {
  mindmapOverviewNavigation.value = {
    key: '',
    index: -1,
    nodeText: '',
  }
}

const isMindmapOverviewItemActive = key => mindmapOverviewNavigation.value.key === key

const getMindmapOverviewItemPosition = item => {
  const count = Number(item?.count || 0)
  if (count <= 0) return '0/0'
  if (!isMindmapOverviewItemActive(item.key)) return `-/${count}`

  const currentPosition = Math.min(Math.max(mindmapOverviewNavigation.value.index + 1, 1), count)
  return `${currentPosition}/${count}`
}

const hasMindmapReviewData = data => {
  const reviewOpinion = String(data?.reviewOpinion || '').trim()
  const reviewStatus = String(data?.reviewStatus || '').trim()
  return Boolean(reviewOpinion) || ['未处理', '已处理'].includes(reviewStatus)
}

const isMindmapOverviewNodeMatch = (node, key) => {
  const data = getNodeData(node)

  if (key === 'module-unmatched') {
    return data.nodeType === 'module' && data.moduleCategoryMatched !== true
  }
  if (key === 'module-all') {
    return data.nodeType === 'module'
  }
  if (key === 'review-unprocessed') {
    return data.nodeType === 'testpoint' && hasMindmapReviewData(data) && data.reviewStatus !== '已处理'
  }
  if (key === 'review-all') {
    return data.nodeType === 'testpoint' && hasMindmapReviewData(data)
  }
  if (String(key || '').startsWith('testpoint-')) {
    const targetStatus = String(key).slice('testpoint-'.length)
    const nodeStatus = ['not_run', 'pass', 'fail', 'block', 'not_test'].includes(data.status)
      ? data.status
      : 'not_run'
    return data.nodeType === 'testpoint' && nodeStatus === targetStatus
  }

  return false
}

const getMindmapOverviewNavigationNodes = key => {
  if (!minder?.getRoot?.() || !key) return []

  const matches = []
  const walk = node => {
    if (!node) return
    if (isMindmapOverviewNodeMatch(node, key)) {
      matches.push(node)
    }
    getNodeChildren(node).forEach(walk)
  }
  walk(minder.getRoot())
  return matches
}

let mindmapOverviewFocusTimer = null

const focusMindmapOverviewNode = (key, nodes, index) => {
  const targetNode = nodes[index]
  if (!targetNode || !minder) return false

  expandNodeAncestors(targetNode)
  mindmapOverviewNavigation.value = {
    key,
    index,
    nodeText: String(targetNode.getText?.() || '').trim(),
  }
  batchOperationMode.value = BATCH_OPERATION_MODE.selection
  minder.select(targetNode, true)
  loadNodeDetails(targetNode)

  if (mindmapOverviewFocusTimer) {
    clearTimeout(mindmapOverviewFocusTimer)
  }
  mindmapOverviewFocusTimer = setTimeout(() => {
    mindmapOverviewFocusTimer = null
    const navigation = mindmapOverviewNavigation.value
    if (navigation.key !== key || navigation.index !== index) return

    if (!centerMinderNodeInWorkspace(targetNode, 320)) {
      try {
        minder.execCommand('camera', targetNode, 320)
      } catch (error) {
        minder.execCommand('Camera')
      }
    }
    focusEditor()
  }, 100)
  return true
}

const navigateMindmapOverviewItem = (item, direction = 0, resetToFirst = false) => {
  const key = String(item?.key || '')
  const nodes = getMindmapOverviewNavigationNodes(key)
  if (!nodes.length) {
    resetMindmapOverviewNavigation()
    return false
  }

  const navigation = mindmapOverviewNavigation.value
  let nextIndex = 0
  if (!resetToFirst && navigation.key === key && navigation.index >= 0) {
    nextIndex = (navigation.index + direction + nodes.length) % nodes.length
  }
  return focusMindmapOverviewNode(key, nodes, nextIndex)
}

const activateMindmapOverviewItem = item => navigateMindmapOverviewItem(item, 0, true)
const stepMindmapOverviewItem = (item, direction) => navigateMindmapOverviewItem(item, direction, false)

const syncMindmapOverviewNavigationWithSelectedNode = node => {
  const key = mindmapOverviewNavigation.value.key
  if (!key) return

  const nodes = getMindmapOverviewNavigationNodes(key)
  const index = nodes.indexOf(node)
  if (index < 0) {
    resetMindmapOverviewNavigation()
    return
  }

  mindmapOverviewNavigation.value = {
    key,
    index,
    nodeText: String(node.getText?.() || '').trim(),
  }
}

const reconcileMindmapOverviewNavigation = () => {
  const navigation = mindmapOverviewNavigation.value
  if (!navigation.key) return

  const nodes = getMindmapOverviewNavigationNodes(navigation.key)
  if (!nodes.length) {
    resetMindmapOverviewNavigation()
    return
  }

  const index = Math.min(Math.max(navigation.index, 0), nodes.length - 1)
  mindmapOverviewNavigation.value = {
    key: navigation.key,
    index,
    nodeText: String(nodes[index].getText?.() || '').trim(),
  }
}

const collectLeafNodes = (node, bucket, seen) => {
  if (!node || seen.has(node)) return

  const children = getNodeChildren(node)
  if (children.length === 0) {
    seen.add(node)
    bucket.push(node)
    return
  }

  children.forEach(child => collectLeafNodes(child, bucket, seen))
}

const pruneAncestorSelections = (nodes) => {
  return (nodes || []).filter(node => {
    return !(nodes || []).some(other => {
      return other !== node &&
        typeof other?.isAncestorOf === 'function' &&
        other.isAncestorOf(node)
    })
  })
}

const getSelectedLeafNodes = () => {
  if (!minder) return []

  const leafNodes = []
  const seen = new Set()
  const selectedNodes = pruneAncestorSelections(minder.getSelectedNodes() || [])
  selectedNodes.forEach(node => collectLeafNodes(node, leafNodes, seen))
  return leafNodes
}

const getAllLeafNodes = () => {
  if (!minder) return []

  const root = minder.getRoot()
  if (!root) return []

  const leafNodes = []
  collectLeafNodes(root, leafNodes, new Set())
  return leafNodes
}

const getScopedPointActionTargets = (actionLabel = '操作', options = {}) => {
  const { silent = false } = options

  if (!minder) {
    return []
  }

  if (batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes) {
    const allLeafNodes = getAllLeafNodes()
    if (!allLeafNodes.length && !silent) {
      ElMessage.warning(`当前脑图没有可${actionLabel}的末级节点`)
    }
    return allLeafNodes
  }

  if (batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants) {
    const selectedLeafNodes = getSelectedLeafNodes()
    if (!selectedLeafNodes.length && !silent) {
      ElMessage.warning(`请先选择包含测试点的节点，再执行${actionLabel}`)
    }
    return selectedLeafNodes
  }

  const selectedNodes = minder.getSelectedNodes() || []
  if (!selectedNodes.length && !silent) {
    ElMessage.warning(`请先选择节点，再执行${actionLabel}`)
  }
  return selectedNodes
}

const getUniformNodeDataValue = (nodes, key, emptyValue) => {
  if (!nodes.length) return emptyValue

  const firstValue = getNodeData(nodes[0])[key]
  const hasSameValue = nodes.every(node => getNodeData(node)[key] === firstValue)
  return hasSameValue ? (firstValue ?? emptyValue) : emptyValue
}

const syncToolbarStateForScope = () => {
  if (!minder || batchOperationMode.value === BATCH_OPERATION_MODE.selection) {
    return
  }

  const targetNodes = getScopedPointActionTargets('', { silent: true })
  if (!targetNodes.length) {
    currentNodeType.value = ''
    currentPriority.value = null
    currentStatus.value = ''
    return
  }

  currentNodeType.value = getUniformNodeDataValue(targetNodes, 'nodeType', '')

  const uniformPriority = getUniformNodeDataValue(targetNodes, 'priority', null)
  currentPriority.value = [1, 2, 3, 4].includes(uniformPriority) ? uniformPriority : null

  const uniformStatus = getUniformNodeDataValue(targetNodes, 'status', '')
  currentStatus.value = ['not_run', 'pass', 'fail', 'block', 'not_test'].includes(uniformStatus) ? uniformStatus : ''
}

const toggleSelectedLeafBatchMode = () => {
  if (!hasSelection.value) {
    ElMessage.warning('请先选择一个父节点或测试点')
    return
  }

  batchOperationMode.value = batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants
    ? BATCH_OPERATION_MODE.selection
    : BATCH_OPERATION_MODE.selectedLeafDescendants

  syncToolbarStateForScope()
  scheduleEditorRefocus()
}

const toggleAllLeafBatchMode = () => {
  batchOperationMode.value = batchOperationMode.value === BATCH_OPERATION_MODE.allLeafNodes
    ? BATCH_OPERATION_MODE.selection
    : BATCH_OPERATION_MODE.allLeafNodes

  syncToolbarStateForScope()
  scheduleEditorRefocus()
}

const handleNodeInsertCommand = (command) => {
  const commandMap = {
    child: 'AppendChildNode',
    sibling: 'AppendSiblingNode'
  }
  const minderCommand = commandMap[command]
  if (!minderCommand) {
    return
  }
  execCommand(minderCommand)
}

const handleClipboardCommand = (command) => {
  if (command === 'copy') {
    copySelectedMindmapNodes()
    return
  }

  if (command === 'cut') {
    cutSelectedMindmapNodes()
    return
  }

  if (command === 'paste') {
    void pasteMindmapClipboard()
  }
}

const handleFilterCommand = (command) => {
  if (command === 'open') {
    showFilterDialog()
    return
  }

  if (command === 'clear') {
    clearFilter()
  }
}

const handleScopeCommand = (command) => {
  if (command === BATCH_OPERATION_MODE.selectedLeafDescendants) {
    toggleSelectedLeafBatchMode()
    return
  }

  if (command === BATCH_OPERATION_MODE.allLeafNodes) {
    toggleAllLeafBatchMode()
  }
}

const focusEditor = () => {
  if (currentEditInput) return

  const editorElement = document.getElementById('minder-editor')
  if (editorElement) {
    editorElement.focus()
  }
}

const scheduleEditorRefocus = (delay = 40) => {
  if (currentEditInput) return

  if (editorRefocusTimer) {
    clearTimeout(editorRefocusTimer)
  }

  editorRefocusTimer = setTimeout(() => {
    editorRefocusTimer = null

    const activeElement = document.activeElement
    if (activeElement instanceof HTMLElement && activeElement !== document.body) {
      activeElement.blur()
    }

    requestAnimationFrame(() => {
      focusEditor()
    })
  }, delay)
}

let viewportSyncTimer = null
let editorRefocusTimer = null
let mindmapAutoSaveTimer = null
let minderInitTimer = null
let minderResizeObserver = null
let isMindmapAutoSaving = false
let pendingMindmapAutoSave = false
let hasShownMindmapAutoSaveError = false
let canvasPanMouseDownHandler = null
let canvasPanMouseMoveHandler = null
let canvasPanMouseUpHandler = null
let contextMenuHandler = null
let contextMenuGlobalClickHandler = null
let contextMenuKeydownHandler = null
let isCanvasPanning = false
let lastPanClientX = 0
let lastPanClientY = 0
let editBlankCanvasMouseDownState = null
let previousBodyUserSelect = ''
let previousBodyCursor = ''
let isApplyingHistoryState = false
let lastPersistedMindmapDescendantCount = 0
let contextMenuNode = null
const undoHistoryStack = []
const redoHistoryStack = []
const EDIT_BLANK_CANVAS_CLICK_TOLERANCE = 4

const mindmapContextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  openLeft: false,
  sourceRequirementClarificationKey: '',
})

const isRequirementClarificationContextNode = computed(() => {
  return Boolean(mindmapContextMenu.value.sourceRequirementClarificationKey)
})

const hideMindmapContextMenu = () => {
  mindmapContextMenu.value.visible = false
  mindmapContextMenu.value.openLeft = false
  mindmapContextMenu.value.sourceRequirementClarificationKey = ''
  contextMenuNode = null
}

const getSelectedNodeIndexPath = () => {
  if (!minder) return []

  const selectedNode = typeof minder.getSelectedNode === 'function'
    ? minder.getSelectedNode()
    : null

  if (!selectedNode) return []

  const path = []
  let currentNode = selectedNode

  while (currentNode && !currentNode.isRoot?.()) {
    const parent = currentNode.parent || currentNode.getParent?.()
    if (!parent) break

    const siblings = getNodeChildren(parent)
    const currentIndex = siblings.indexOf(currentNode)
    if (currentIndex < 0) break

    path.unshift(currentIndex)
    currentNode = parent
  }

  return path
}

const getNodeByIndexPath = (path = []) => {
  if (!minder) return null

  let currentNode = minder.getRoot?.()
  if (!currentNode) return null

  for (const index of path) {
    const children = getNodeChildren(currentNode)
    if (!children[index]) {
      return currentNode
    }
    currentNode = children[index]
  }

  return currentNode
}

const captureHistoryEntry = () => {
  if (!minder) return null

  return {
    snapshot: JSON.stringify(normalizeMindmapData(minder.exportJson())),
    selectedPath: getSelectedNodeIndexPath()
  }
}

const updateHistoryState = () => {
  if (!minder) {
    canUndo.value = false
    canRedo.value = false
    return
  }

  canUndo.value = undoHistoryStack.length > 1
  canRedo.value = redoHistoryStack.length > 0
}

const pushHistorySnapshot = () => {
  if (!minder || isApplyingHistoryState) return

  const entry = captureHistoryEntry()
  if (!entry) return

  const lastEntry = undoHistoryStack[undoHistoryStack.length - 1]
  if (lastEntry?.snapshot === entry.snapshot) {
    lastEntry.selectedPath = entry.selectedPath
    updateHistoryState()
    return
  }

  undoHistoryStack.push(entry)
  if (undoHistoryStack.length > HISTORY_MAX_STEPS) {
    undoHistoryStack.shift()
  }

  redoHistoryStack.length = 0
  updateHistoryState()
}

const resetHistorySnapshots = () => {
  undoHistoryStack.length = 0
  redoHistoryStack.length = 0

  const entry = captureHistoryEntry()
  if (entry) {
    undoHistoryStack.push(entry)
  }

  updateHistoryState()
}

const restoreHistoryEntry = (entry) => {
  if (!minder || !entry) return

  isApplyingHistoryState = true
  try {
    minder.importJson(normalizeMindmapData(JSON.parse(entry.snapshot)))
    syncMindmapNameWithRootNode()

    const targetNode = getNodeByIndexPath(entry.selectedPath)
    if (targetNode) {
      minder.select(targetNode, true)
      loadNodeDetails(targetNode)
    }
  } finally {
    isApplyingHistoryState = false
  }

  updateHistoryState()
  scheduleEditorRefocus()
}

const handleUndo = () => {
  if (!ensureMindmapEditable()) return
  if (!minder || undoHistoryStack.length <= 1) return

  if (currentEditInput) {
    currentEditInput.saveAndRemove()
  }

  const currentEntry = undoHistoryStack.pop()
  const previousEntry = undoHistoryStack[undoHistoryStack.length - 1]

  if (!currentEntry || !previousEntry) {
    if (currentEntry) {
      undoHistoryStack.push(currentEntry)
    }
    updateHistoryState()
    return
  }

  redoHistoryStack.push(currentEntry)
  restoreHistoryEntry(previousEntry)
}

const handleRedo = () => {
  if (!ensureMindmapEditable()) return
  if (!minder || redoHistoryStack.length === 0) return

  if (currentEditInput) {
    currentEditInput.saveAndRemove()
  }

  const nextEntry = redoHistoryStack.pop()
  if (!nextEntry) {
    updateHistoryState()
    return
  }

  undoHistoryStack.push(nextEntry)
  restoreHistoryEntry(nextEntry)
}

const clearMindmapAutoSaveTimer = () => {
  if (!mindmapAutoSaveTimer) return

  clearTimeout(mindmapAutoSaveTimer)
  mindmapAutoSaveTimer = null
}

const buildMindmapSaveData = () => {
  syncMindmapNameWithRootNode()
  refreshLiveModuleMatchesAndOverview()
  minderData.value = annotateModuleMatchesInData(normalizeMindmapData(minder.exportJson()))

  return {
    name: mindmapName.value,
    description: mindmapDescription.value,
    mindmap_data: minderData.value,
    mindmap_scope: currentMindmapScope.value,
    project_id: currentProjectId.value || getContextQueryValue('project_id') || getContextQueryValue('project') || props.initialProjectId || undefined,
    version_id: currentVersionId.value || getContextQueryValue('version_id') || getContextQueryValue('version') || undefined,
    category_id: isRequirementAnalysisMindmap.value
      ? undefined
      : (currentCategoryId.value || getContextQueryValue('category_id') || getContextQueryValue('category') || undefined),
  }
}

const persistMindmap = async ({ createIfMissing = true } = {}) => {
  if (isReadonlyMindmap.value) {
    throw new Error('当前为只读查看模式，不能保存脑图')
  }

  if (!minder) {
    throw new Error('脑图未初始化')
  }

  const saveData = buildMindmapSaveData()
  const saveDescendantCount = countMindmapDescendants(saveData.mindmap_data)
  if (
    isRequirementAnalysisMindmap.value &&
    currentMindmapId.value &&
    lastPersistedMindmapDescendantCount > 0 &&
    saveDescendantCount === 0
  ) {
    throw new Error('已阻止空需求分析脑图覆盖已有分析结果')
  }

  console.log('准备保存脑图, currentMindmapId:', currentMindmapId.value)
  console.log('route.query.id:', route.query.id)

  let response
  if (currentMindmapId.value) {
    console.log('执行更新操作, ID:', currentMindmapId.value)
    response = await api.put(`/testcases/manual-mindmaps/${currentMindmapId.value}/`, {
      name: saveData.name,
      description: saveData.description,
      mindmap_data: saveData.mindmap_data,
      mindmap_scope: saveData.mindmap_scope
    })
  } else if (createIfMissing) {
    console.log('执行创建操作')
    response = await api.post('/testcases/manual-mindmaps/', saveData)
    currentMindmapId.value = response.data.id
    currentProjectId.value = response.data.project?.id || response.data.project_id || getContextQueryValue('project_id') || ''
    currentVersionId.value = response.data.version?.id || response.data.version_id || getContextQueryValue('version_id') || ''
    currentCategoryId.value = response.data.category || response.data.category_id || getContextQueryValue('category_id') || ''
    currentRequirementKey.value = response.data.requirement_key || ''
    currentResponsibilityGroup.value = response.data.responsibility_group || ''
    currentFrontendDeveloper.value = resolveUserDisplayName(response.data.frontend_developer, '')
    currentBackendDeveloper.value = resolveUserDisplayName(response.data.backend_developer, '')
  } else {
    return null
  }

  hasShownMindmapAutoSaveError = false
  lastPersistedMindmapDescendantCount = countMindmapDescendants(normalizeMindmapData(response.data.mindmap_data))
  loadedMindmapScope.value = response.data.mindmap_scope || currentMindmapScope.value
  emit('saved', response.data)
  console.log('保存成功:', response.data)
  return response
}

const runMindmapAutoSave = async () => {
  clearMindmapAutoSaveTimer()

  if (isReadonlyMindmap.value) {
    return
  }

  if (!minder || !currentMindmapId.value) {
    return
  }

  if (isMindmapAutoSaving) {
    pendingMindmapAutoSave = true
    return
  }

  isMindmapAutoSaving = true
  try {
    await persistMindmap({ createIfMissing: false })
  } catch (error) {
    console.error('脑图自动保存失败:', error)
    if (!hasShownMindmapAutoSaveError) {
      hasShownMindmapAutoSaveError = true
      ElMessage.warning('节点已更新，但自动保存失败，请手动点击保存')
    }
  } finally {
    isMindmapAutoSaving = false

    if (pendingMindmapAutoSave) {
      pendingMindmapAutoSave = false
      scheduleMindmapAutoSave(200)
    }
  }
}

const scheduleMindmapAutoSave = (delay = MINDMAP_AUTO_SAVE_DELAY) => {
  if (isReadonlyMindmap.value) {
    return
  }

  if (!minder || !currentMindmapId.value) {
    return
  }

  clearMindmapAutoSaveTimer()
  mindmapAutoSaveTimer = setTimeout(() => {
    void runMindmapAutoSave()
  }, delay)
}

const scheduleViewportSync = (delay = 120) => {
  if (viewportSyncTimer) {
    clearTimeout(viewportSyncTimer)
  }

  viewportSyncTimer = setTimeout(() => {
    viewportSyncTimer = null

    if (!minder) return

    requestAnimationFrame(() => {
      try {
        if (typeof minder.fire === 'function') {
          minder.fire('resize')
        }
        if (!centerMinderNodeInWorkspace(null, 0)) {
          const root = typeof minder.getRoot === 'function' ? minder.getRoot() : null
          minder.execCommand('camera', root, 0)
        }
      } catch (error) {
        console.log('同步脑图视口失败:', error)
      }
    })
  }, delay)
}

const getMinderEditorElement = () => document.getElementById('minder-editor')

const isMinderEditorReady = () => {
  const editorElement = getMinderEditorElement()
  if (!editorElement) {
    return false
  }
  const rect = editorElement.getBoundingClientRect()
  return rect.width > 80 && rect.height > 80
}

const scheduleMinderInitialization = (delay = 100) => {
  if (minderInitTimer) {
    clearTimeout(minderInitTimer)
  }

  minderInitTimer = setTimeout(() => {
    minderInitTimer = null

    if (minder) {
      scheduleViewportSync(80)
      return
    }

    if (!isMinderEditorReady()) {
      scheduleMinderInitialization(120)
      return
    }

    console.log('开始初始化 Minder')
    initMinder()

    if (pendingLocateParams) {
      console.log('检测到节点定位参数')
      setTimeout(() => {
        console.log('准备定位节点，minder实例存在?', !!minder)
        if (minder) {
          console.log('minder根节点:', minder.getRoot())
          runPendingLocate()
        } else {
          console.error('minder实例不存在，无法定位节点')
        }
      }, 400)
    } else {
      console.log('没有节点定位参数，跳过节点定位')
    }
  }, delay)
}

const toggleDetailPanel = () => {
  showDetailPanel.value = !showDetailPanel.value
  requestAnimationFrame(() => {
    focusEditor()
  })
  scheduleViewportSync(320)
}

const setToolbarVisible = visible => {
  const nextVisible = Boolean(visible)
  if (showToolbar.value === nextVisible) {
    return
  }
  showToolbar.value = nextVisible
  requestAnimationFrame(() => {
    focusEditor()
  })
  scheduleViewportSync(280)
}

const toggleToolbar = () => setToolbarVisible(!showToolbar.value)

const getToolbarState = () => ({
  showToolbar: showToolbar.value,
  showDetailPanel: showDetailPanel.value,
})

watch(
  [showToolbar, showDetailPanel],
  () => emit('toolbar-state-change', getToolbarState()),
  { immediate: true }
)

const handleWindowResize = () => {
  scheduleViewportSync(120)
}

const moveCanvasViewBy = (deltaX, deltaY) => {
  const viewDragger = typeof minder?.getViewDragger === 'function'
    ? minder.getViewDragger()
    : minder?._viewDragger

  if (!viewDragger || typeof viewDragger.move !== 'function') {
    return
  }

  // Keep the canvas movement aligned with the pointer drag direction.
  viewDragger.move({ x: deltaX, y: deltaY }, 0)
}

const centerMinderNodeInWorkspace = (node = null, duration = 0) => {
  if (!minder) {
    return false
  }

  const targetNode = node || (typeof minder.getRoot === 'function' ? minder.getRoot() : null)
  const paper = typeof minder.getPaper === 'function' ? minder.getPaper() : null
  const viewDragger = typeof minder.getViewDragger === 'function'
    ? minder.getViewDragger()
    : minder?._viewDragger

  if (!targetNode || !paper || !viewDragger || typeof viewDragger.move !== 'function') {
    return false
  }

  try {
    const viewport = paper.getViewPort()
    const renderBox = targetNode.getRenderContainer().getRenderBox('view')
    const dx = viewport.center.x - renderBox.x - renderBox.width / 2
    const dy = viewport.center.y - renderBox.y - renderBox.height / 2
    const PointCtor = window.kity?.Point
    const offset = PointCtor ? new PointCtor(dx, dy) : { x: dx, y: dy }
    viewDragger.move(offset, duration)
    return true
  } catch (error) {
    console.log('按工作区居中脑图节点失败:', error)
    return false
  }
}

const stopCanvasPanning = (shouldRefocus = true) => {
  if (!isCanvasPanning) {
    return
  }

  isCanvasPanning = false
  document.body.style.userSelect = previousBodyUserSelect
  document.body.style.cursor = previousBodyCursor

  if (editorElementRef) {
    editorElementRef.classList.remove('is-panning')
  }

  if (shouldRefocus) {
    requestAnimationFrame(() => {
      focusEditor()
    })
  }
}

const getMinderNodeFromEventTarget = target => {
  if (!(target instanceof Element) || typeof target.closest !== 'function') {
    return null
  }

  let currentElement = target
  while (currentElement && currentElement !== editorElementRef) {
    let currentShape = currentElement.shape

    while (currentShape) {
      if (currentShape.minderNode) {
        return currentShape.minderNode
      }

      currentShape = currentShape.container
    }

    currentElement = currentElement.parentElement
  }

  return null
}

const isBlankCanvasTarget = target => {
  if (!(target instanceof Element) || typeof target.closest !== 'function') {
    return false
  }

  return !getMinderNodeFromEventTarget(target) &&
    !target.closest('.km-node') &&
    !target.closest('.km-hotbox') &&
    !target.closest('.km-edit-input')
}

const stopMindmapMouseEvent = event => {
  if (!event) return
  event.preventDefault()
  event.stopPropagation()
  if (typeof event.stopImmediatePropagation === 'function') {
    event.stopImmediatePropagation()
  }
}

const getNodeChildrenSummary = (node, depth = 0, maxDepth = 2) => {
  if (!node || depth >= maxDepth) {
    return []
  }

  return getNodeChildren(node)
    .map(child => {
      const childData = getNodeData(child)
      return {
        text: getNodeDisplayText(child),
        nodeType: childData.nodeType || '',
        children: getNodeChildrenSummary(child, depth + 1, maxDepth),
      }
    })
    .filter(item => item.text || item.children.length)
}

const buildTestPointRefinePayload = node => {
  const data = getNodeData(node)
  return {
    nodeText: getNodeDisplayText(node),
    nodeType: data.nodeType || '',
    nodePath: buildNodePathText(node),
    nodeModulePath: buildNodeModulePath(node),
    mindmapId: currentMindmapId.value,
    mindmapName: mindmapName.value,
    mindmapScope: currentMindmapScope.value,
    existingChildren: getNodeChildrenSummary(node),
  }
}

const buildRequirementClarificationActionPayload = (node, action) => {
  const data = getNodeData(node)
  return {
    action,
    sourceRequirementClarificationKey: data.sourceRequirementClarificationKey || data.source_requirement_clarification_key || '',
    nodeText: getNodeDisplayText(node),
    nodePath: buildNodePathText(node),
    mindmapId: currentMindmapId.value,
    mindmapName: mindmapName.value,
    mindmapScope: currentMindmapScope.value,
  }
}

const selectContextMenuNode = () => {
  const node = contextMenuNode || getCurrentNode()
  if (!node || !minder) {
    return null
  }

  batchOperationMode.value = BATCH_OPERATION_MODE.selection
  minder.select(node, true)
  loadNodeDetails(node)
  return node
}

const handleContextMenuSetNodeType = type => {
  const node = selectContextMenuNode()
  if (!node) {
    hideMindmapContextMenu()
    ElMessage.warning('请先选择脑图节点')
    return
  }

  currentNodeType.value = type
  setNodeType()
  hideMindmapContextMenu()
}

const runContextMenuAction = action => {
  const node = selectContextMenuNode()
  if (!node) {
    hideMindmapContextMenu()
    ElMessage.warning('请先选择脑图节点')
    return null
  }

  hideMindmapContextMenu()
  return action(node)
}

const handleContextMenuKityCommand = command => {
  if (isMutatingMinderCommand(command) && !ensureMindmapEditable()) return
  runContextMenuAction(node => {
    if (command === 'RemoveNode' && node === minder?.getRoot?.()) {
      ElMessage.warning('根节点不能删除')
      return
    }
    execCommand(command)
  })
}

const handleContextMenuCopy = () => {
  runContextMenuAction(() => {
    copySelectedMindmapNodes()
  })
}

const handleContextMenuCut = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(node => {
    if (node === minder?.getRoot?.()) {
      ElMessage.warning('根节点不能剪切')
      return
    }
    cutSelectedMindmapNodes()
  })
}

const handleContextMenuPaste = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    void pasteMindmapClipboard()
  })
}

const handleContextMenuStyleCommand = command => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    handleStyleCommand(command)
  })
}

const handleContextMenuClearNodeType = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    currentNodeType.value = ''
    setNodeType({ clear: true })
  })
}

const handleContextMenuSetPriority = priority => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    currentPriority.value = priority
    setPriority()
  })
}

const handleContextMenuClearPriority = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    currentPriority.value = null
    setPriority({ clear: true })
  })
}

const handleContextMenuSetStatus = status => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    currentStatus.value = status
    setStatus()
  })
}

const handleContextMenuClearStatus = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    currentStatus.value = ''
    setStatus({ clear: true })
  })
}

const handleContextMenuSetIcon = command => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    handleIconCommand(command)
  })
}

const handleContextMenuNote = () => {
  if (!ensureMindmapEditable()) return
  runContextMenuAction(() => {
    showNoteDialog()
  })
}

const handleContextMenuTestPointRefine = () => {
  if (!ensureMindmapEditable()) return
  if (!isRequirementAnalysisMindmap.value) {
    hideMindmapContextMenu()
    return
  }

  const node = selectContextMenuNode()
  if (!node) {
    hideMindmapContextMenu()
    ElMessage.warning('请先选择要细化的页面或功能节点')
    return
  }

  emit('testpoint-refine-request', buildTestPointRefinePayload(node))
  hideMindmapContextMenu()
}

const handleContextMenuRequirementClarificationAction = action => {
  if (!ensureMindmapEditable()) return
  const node = selectContextMenuNode()
  if (!node) {
    hideMindmapContextMenu()
    ElMessage.warning('请先选择需求澄清节点')
    return
  }
  const payload = buildRequirementClarificationActionPayload(node, action)
  if (!payload.sourceRequirementClarificationKey) {
    hideMindmapContextMenu()
    ElMessage.warning('当前节点不是需求澄清同步节点')
    return
  }
  emit('requirement-clarification-action-request', payload)
  hideMindmapContextMenu()
}

// 样式设置
const selectedColor = ref('#000000')
const fontSize = ref(14)
const fontFamily = ref('Microsoft YaHei, 微软雅黑')

// 预设颜色
const presetColors = [
  '#000000', '#333333', '#666666', '#999999', '#CCCCCC', '#FFFFFF',
  '#f5222d', '#fa541c', '#fa8c16', '#faad14', '#fadb14', '#a0d911',
  '#52c41a', '#13c2c2', '#1890ff', '#2f54eb', '#722ed1', '#eb2f96'
]

// 获取节点数据
const getNodeData = (node) => {
  if (!node) return {}
  return node.getData() || {}
}

const MODULE_MATCH_DATA_FIELDS = [
  'moduleCategoryMatched',
  'moduleCategoryId',
  'moduleCategoryPath',
  'moduleCategoryMatchMode',
]

const buildLiveMindmapMirror = node => ({
  node,
  data: { ...getNodeData(node) },
  children: getNodeChildren(node).map(buildLiveMindmapMirror),
})

const applyLiveModuleMatchData = mirror => {
  const targetData = getNodeData(mirror.node)
  MODULE_MATCH_DATA_FIELDS.forEach(fieldName => {
    if (Object.prototype.hasOwnProperty.call(mirror.data, fieldName)) {
      setNodeDataSilently(mirror.node, fieldName, mirror.data[fieldName])
    } else {
      delete targetData[fieldName]
      mirror.node.setData(fieldName, undefined)
    }
  })
  mirror.children.forEach(applyLiveModuleMatchData)
}

const refreshLiveModuleMatchesAndOverview = () => {
  if (!minder?.getRoot?.()) {
    refreshOverviewFromMindmapData(minderData.value)
    return
  }

  const mirrorRoot = buildLiveMindmapMirror(minder.getRoot())
  const mirrorData = { root: mirrorRoot }
  if (moduleCategoryMatchReady) {
    annotateMindmapModuleMatches(mirrorData, manualCategoryMatchIndex)
    applyLiveModuleMatchData(mirrorRoot)
  }
  mindmapOverview.value = collectMindmapOverview(mirrorRoot)
  reconcileMindmapOverviewNavigation()

  const updateMarkers = mirror => {
    applyModuleMatchMarkerStyle(mirror.node)
    updateNodeReviewBadge(mirror.node)
    mirror.children.forEach(updateMarkers)
  }
  updateMarkers(mirrorRoot)
}

const scheduleModuleOverviewRefresh = (delay = 60) => {
  if (moduleOverviewRefreshTimer) {
    clearTimeout(moduleOverviewRefreshTimer)
  }
  moduleOverviewRefreshTimer = setTimeout(() => {
    moduleOverviewRefreshTimer = null
    refreshLiveModuleMatchesAndOverview()
  }, delay)
}

const normalizeMindmapColorValue = value => {
  if (typeof value !== 'string') {
    return ''
  }
  const color = value.trim()
  if (!color) {
    return ''
  }
  if (/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(color)) {
    return color
  }
  if (/^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$/i.test(color)) {
    return color
  }
  const semanticRedValues = new Set([
    'red',
    'ruby',
    'crimson',
    '红',
    '红色',
    '红色字体',
    '红色标注',
  ])
  if (semanticRedValues.has(color.toLowerCase())) {
    return '#d93025'
  }
  return ''
}

const getNodeTextColor = data => {
  const candidates = [
    data?.forecolor,
    data?.text_color,
    data?.textColor,
    data?.font_color,
    data?.fontColor,
    data?.color,
    data?.style?.color,
    data?.style?.text_color,
    data?.style?.textColor,
    data?.visual_style?.text_color,
    data?.visualStyle?.textColor,
  ]
  for (const candidate of candidates) {
    const normalized = normalizeMindmapColorValue(candidate)
    if (normalized) {
      return normalized
    }
  }
  const mark = String(
    data?.source_visual_mark ||
      data?.sourceVisualMark ||
      data?.visual_mark ||
      data?.visualMark ||
      data?.red_visual_mark ||
      data?.redVisualMark ||
      ''
  ).toLowerCase()
  return mark.includes('red') ? '#d93025' : ''
}

const getNodeSvgTextElements = (node) => {
  const renderNode = node?.getRenderContainer?.()?.node
  if (!renderNode) {
    return []
  }
  const elements = Array.from(renderNode.querySelectorAll('text'))
  const nodeText = String(node?.getText?.() || getNodeData(node).text || '').trim()
  if (!nodeText) {
    return elements
  }
  const matched = elements.filter(element => String(element.textContent || '').trim() === nodeText)
  return matched.length ? matched : elements
}

const applyNodeTextColor = (node, color) => {
  if (!node || !color) {
    return
  }
  setNodeDataSilently(node, 'forecolor', color)
  setNodeDataSilently(node, 'textColor', color)
  setNodeDataSilently(node, 'text_color', color)
  requestAnimationFrame(() => {
    getNodeSvgTextElements(node).forEach(element => {
      element.setAttribute('fill', color)
      element.style.fill = color
    })
  })
}

// 设置节点数据
const setNodeData = (node, key, value) => {
  if (isReadonlyMindmap.value) return
  if (!node) return
  const data = getNodeData(node)
  data[key] = value
  node.setData(key, value)
  minder.fire('contentchange')
}

const setNodeDataSilently = (node, key, value) => {
  if (!node) return
  const data = getNodeData(node)
  data[key] = value
  node.setData(key, value)
}

const emitMindmapContentChange = () => {
  if (isReadonlyMindmap.value) return
  if (minder) {
    minder.fire('contentchange')
  }
}

const cloneClipboardPayload = value => {
  if (value === undefined || value === null) {
    return value
  }
  return JSON.parse(JSON.stringify(value))
}

const getSelectedMindmapNodes = ({ allowRoot = true } = {}) => {
  if (!minder) return []
  const selectedNodes = typeof minder.getSelectedNodes === 'function'
    ? minder.getSelectedNodes() || []
    : [minder.getSelectedNode()].filter(Boolean)
  const root = typeof minder.getRoot === 'function' ? minder.getRoot() : null
  return pruneAncestorSelections(selectedNodes)
    .filter(node => node && (allowRoot || node !== root))
}

const readBrowserClipboardText = async () => {
  try {
    if (typeof navigator === 'undefined') {
      return null
    }
    const clipboard = navigator.clipboard
    if (!clipboard || typeof clipboard.readText !== 'function') {
      return null
    }
    const text = await clipboard.readText()
    return typeof text === 'string' ? text : null
  } catch (error) {
    return null
  }
}

const rememberSystemClipboardForMindmapClipboard = () => {
  systemClipboardTextWhenMindmapClipboardSet = SYSTEM_CLIPBOARD_TEXT_PENDING
  void readBrowserClipboardText().then(text => {
    systemClipboardTextWhenMindmapClipboardSet = text
  })
}

const exportMindmapNodeForClipboard = node => {
  if (!node || !minder) return null
  if (typeof minder.exportNode === 'function') {
    return cloneClipboardPayload(minder.exportNode(node))
  }

  const data = cloneClipboardPayload(getNodeData(node) || {}) || {}
  data.text = String(node.getText?.() || data.text || '分支主题')
  return {
    data,
    children: getNodeChildren(node)
      .map(child => exportMindmapNodeForClipboard(child))
      .filter(Boolean),
  }
}

const importMindmapNodeFromClipboard = (parentNode, payload) => {
  if (!minder || !parentNode || !payload) return null
  if (typeof minder.createNode !== 'function') {
    throw new Error('当前脑图库不支持创建节点')
  }

  const clonedPayload = cloneClipboardPayload(payload)
  const newNode = minder.createNode(null, parentNode)
  if (typeof minder.importNode === 'function') {
    minder.importNode(newNode, clonedPayload)
  } else {
    const data = clonedPayload?.data || {}
    Object.entries(data).forEach(([key, value]) => {
      newNode.setData(key, value)
    })
    if (typeof newNode.setText === 'function') {
      newNode.setText(String(data.text || '分支主题'))
    }
    ;(clonedPayload?.children || []).forEach(childPayload => {
      importMindmapNodeFromClipboard(newNode, childPayload)
    })
  }

  parentNode.appendChild(newNode)
  return newNode
}

const importMindmapTextNodeAsChild = (parentNode, text) => {
  const nodeText = String(text || '').trim()
  if (!nodeText) return null

  return importMindmapNodeFromClipboard(parentNode, {
    data: {
      text: nodeText,
    },
    children: [],
  })
}

const selectMindmapNodes = nodes => {
  if (!minder || !nodes?.length) return
  try {
    minder.select(nodes.length === 1 ? nodes[0] : nodes, true)
  } catch (error) {
    minder.select(nodes[0], true)
  }
}

const refreshMindmapAfterClipboardMutation = (selectedNodes = []) => {
  if (!minder) return
  try {
    if (typeof minder.refresh === 'function') {
      minder.refresh()
    }
  } catch (error) {
    console.warn('刷新脑图失败:', error)
  }

  if (selectedNodes.length) {
    selectMindmapNodes(selectedNodes)
  }

  emitMindmapContentChange()
  updateClipboardState()
  updateHistoryState()
  const currentNode = getCurrentNode()
  if (currentNode) {
    hasSelection.value = true
    isRootSelected.value = currentNode === minder.getRoot()
    loadNodeDetails(currentNode)
  }
  setTimeout(() => {
    updateAllNodeStyles()
    updateAllNodeCounts()
  }, 80)
  scheduleEditorRefocus()
}

const copySelectedMindmapNodes = () => {
  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return false
  }
  const selectedNodes = getSelectedMindmapNodes({ allowRoot: true })
  if (!selectedNodes.length) {
    ElMessage.warning('请先选择要复制的节点')
    return false
  }

  mindmapClipboardNodes = selectedNodes
    .map(node => exportMindmapNodeForClipboard(node))
    .filter(Boolean)
  rememberSystemClipboardForMindmapClipboard()
  updateClipboardState()
  scheduleEditorRefocus()
  ElMessage.success(`已复制 ${mindmapClipboardNodes.length} 个节点`)
  return true
}

const cutSelectedMindmapNodes = () => {
  if (!ensureMindmapEditable()) return false
  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return false
  }
  const selectedNodes = getSelectedMindmapNodes({ allowRoot: false })
  if (!selectedNodes.length) {
    ElMessage.warning('根节点不能剪切，请选择普通节点')
    return false
  }

  mindmapClipboardNodes = selectedNodes
    .map(node => exportMindmapNodeForClipboard(node))
    .filter(Boolean)
  rememberSystemClipboardForMindmapClipboard()
  updateClipboardState()

  try {
    selectMindmapNodes(selectedNodes)
    minder.execCommand('RemoveNode')
    refreshMindmapAfterClipboardMutation()
    ElMessage.success(`已剪切 ${mindmapClipboardNodes.length} 个节点`)
    return true
  } catch (error) {
    console.error('剪切节点失败:', error)
    ElMessage.error('剪切节点失败')
    return false
  }
}

const pasteTextClipboardAsMindmapChildren = (text, targetNodes) => {
  if (isReadonlyMindmap.value) return false
  if (!minder) return false
  const nodeText = String(text || '').trim()
  if (!nodeText || !targetNodes.length) {
    return false
  }

  const pastedNodes = targetNodes
    .map(targetNode => importMindmapTextNodeAsChild(targetNode, nodeText))
    .filter(Boolean)

  if (!pastedNodes.length) {
    return false
  }

  refreshMindmapAfterClipboardMutation(pastedNodes)
  ElMessage.success(`已将剪贴板文本粘贴为 ${pastedNodes.length} 个子节点`)
  return true
}

const pasteMindmapClipboard = async () => {
  if (!ensureMindmapEditable()) return false
  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return false
  }

  const targetNodes = getSelectedMindmapNodes({ allowRoot: true })
  if (!targetNodes.length) {
    ElMessage.warning('请先选择粘贴目标节点')
    return false
  }

  const systemClipboardText = await readBrowserClipboardText()
  const hasSystemClipboardText = typeof systemClipboardText === 'string' && systemClipboardText.trim()
  const hasKnownClipboardSnapshot = typeof systemClipboardTextWhenMindmapClipboardSet === 'string'
  const shouldPasteSystemText = hasSystemClipboardText &&
    (!mindmapClipboardNodes.length || (hasKnownClipboardSnapshot && systemClipboardText !== systemClipboardTextWhenMindmapClipboardSet))

  if (shouldPasteSystemText) {
    return pasteTextClipboardAsMindmapChildren(systemClipboardText, targetNodes)
  }

  if (!mindmapClipboardNodes.length) {
    ElMessage.warning('剪贴板中没有可粘贴的节点')
    updateClipboardState()
    return false
  }

  try {
    const pastedNodes = []
    targetNodes.forEach(targetNode => {
      for (let index = mindmapClipboardNodes.length - 1; index >= 0; index -= 1) {
        const pastedNode = importMindmapNodeFromClipboard(targetNode, mindmapClipboardNodes[index])
        if (pastedNode) {
          pastedNodes.push(pastedNode)
        }
      }
    })
    refreshMindmapAfterClipboardMutation(pastedNodes)
    ElMessage.success(`已粘贴 ${pastedNodes.length} 个节点`)
    return true
  } catch (error) {
    console.error('粘贴节点失败:', error)
    ElMessage.error('粘贴节点失败')
    return false
  }
}

// 执行KityMinder命令
const execCommand = (command) => {
  if (isMutatingMinderCommand(command) && !ensureMindmapEditable()) {
    return
  }

  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return
  }
  try {
    minder.execCommand(command)
    scheduleEditorRefocus()
  } catch (error) {
    console.error('执行命令失败:', command, error)
  }
}

// 更新节点文本
const syncMindmapNameWithRootNode = () => {
  if (minder?.getRoot) {
    const rootText = String(minder.getRoot()?.getText?.() || '').trim()
    if (rootText) {
      mindmapName.value = rootText
      return
    }
  }

  const rootText = String(minderData.value?.root?.data?.text || '').trim()
  if (rootText) {
    mindmapName.value = rootText
  }
}

const markNodeTextEditCommitted = () => {
  if (isReadonlyMindmap.value) return
  const currentNode = getCurrentNode()
  if (currentNode && getNodeData(currentNode).nodeType === 'testpoint') {
    applySelfTestDetailDefaultsToNode(currentNode)
    loadNodeDetails(currentNode)
  }
  syncMindmapNameWithRootNode()
  if (minder) {
    minderData.value = normalizeMindmapData(minder.exportJson())
    scheduleMindmapAutoSave(120)
  }
}

const updateNodeText = () => {
  if (!ensureMindmapEditable()) return
  if (!minder || !hasSelection.value || !nodeText.value.trim()) {
    return
  }
  try {
    minder.execCommand('text', nodeText.value)
    markNodeTextEditCommitted()
    scheduleEditorRefocus()
  } catch (error) {
    console.error('更新节点文本失败:', error)
  }
}

// 更新节点数据
const getReviewFormDefaults = () => ({
  reviewerId: currentUserId.value ?? null,
  reviewerName: currentUserDisplayName.value || '',
  reviewTime: formatDateTimeForPicker(new Date()),
})

const resetReviewFields = () => {
  nodeData.value.reviewerId = null
  nodeData.value.reviewerName = ''
  nodeData.value.reviewTime = ''
  nodeData.value.reviewStatus = ''
}

const ensureReviewDefaultsForOpinion = () => {
  const defaults = getReviewFormDefaults()
  if (!nodeData.value.reviewerId) {
    nodeData.value.reviewerId = defaults.reviewerId
  }
  if (!nodeData.value.reviewerName) {
    nodeData.value.reviewerName = defaults.reviewerName
  }
  if (!nodeData.value.reviewTime) {
    nodeData.value.reviewTime = defaults.reviewTime
  }
  if (nodeData.value.reviewStatus !== '已处理') {
    nodeData.value.reviewStatus = '未处理'
  }
}

const handleReviewOpinionInput = () => {
  const opinion = String(nodeData.value.reviewOpinion || '').trim()
  if (opinion) {
    ensureReviewDefaultsForOpinion()
    return
  }

  nodeData.value.reviewOpinion = ''
  resetReviewFields()
}

const handleReviewerChange = (value) => {
  if (!value) {
    nodeData.value.reviewerName = ''
    updateNodeData()
    return
  }

  nodeData.value.reviewerName = resolveReviewerName(
    value,
    String(value) === String(currentUserId.value) ? currentUserDisplayName.value : String(value)
  )
  updateNodeData()
}

const handleReviewStatusChange = (value) => {
  const opinion = String(nodeData.value.reviewOpinion || '').trim()
  if (!opinion) {
    nodeData.value.reviewStatus = ''
    return
  }

  if (value === '未处理' || value === '已处理') {
    ensureReviewDefaultsForOpinion()
  }

  updateNodeData()
}

const buildReviewFieldsForSave = () => {
  if (currentNodeType.value !== 'testpoint') {
    return {
      reviewOpinion: '',
      reviewTime: '',
      reviewerId: null,
      reviewerName: '',
      reviewStatus: '',
    }
  }

  const opinion = String(nodeData.value.reviewOpinion || '').trim()
  if (!opinion) {
    return {
      reviewOpinion: '',
      reviewTime: '',
      reviewerId: null,
      reviewerName: '',
      reviewStatus: '',
    }
  }

  const rawReviewerId = nodeData.value.reviewerId
  const fallbackReviewerId = currentUserId.value ?? null
  const reviewerIdValue = rawReviewerId === '' || rawReviewerId === null || rawReviewerId === undefined
    ? fallbackReviewerId
    : rawReviewerId
  const reviewerIdNumber = reviewerIdValue === null || reviewerIdValue === undefined || reviewerIdValue === ''
    ? NaN
    : Number(reviewerIdValue)
  const reviewerId = Number.isFinite(reviewerIdNumber) ? reviewerIdNumber : fallbackReviewerId
  const reviewerName = nodeData.value.reviewerName || resolveReviewerName(
    reviewerId,
    String(reviewerId) === String(currentUserId.value) ? currentUserDisplayName.value : ''
  )
  const reviewTime = normalizeReviewTimeValue(nodeData.value.reviewTime) || formatDateTimeForPicker(new Date())
  const reviewStatus = nodeData.value.reviewStatus === '已处理' ? '已处理' : '未处理'

  return {
    reviewOpinion: opinion,
    reviewTime,
    reviewerId,
    reviewerName,
    reviewStatus,
  }
}

const updateNodeData = () => {
  if (!ensureMindmapEditable()) return
  const node = getCurrentNode()
  if (!node) return

  setNodeData(node, 'caseId', nodeData.value.caseId)
  setNodeData(node, 'preCondition', nodeData.value.preCondition)
  setNodeData(node, 'preconditions', nodeData.value.preCondition)
  setNodeData(node, 'steps', nodeData.value.steps)
  setNodeData(node, 'expect', nodeData.value.expect)
  setNodeData(node, 'expected_result', nodeData.value.expect)
  setNodeData(node, 'remark', nodeData.value.remark)
  const reviewFields = buildReviewFieldsForSave()
  if (currentNodeType.value === 'testpoint') {
    if (reviewFields.reviewOpinion) {
      nodeData.value.reviewOpinion = reviewFields.reviewOpinion
      nodeData.value.reviewTime = reviewFields.reviewTime
      nodeData.value.reviewerId = reviewFields.reviewerId
      nodeData.value.reviewerName = reviewFields.reviewerName
      nodeData.value.reviewStatus = reviewFields.reviewStatus
    }

    setNodeData(node, 'reviewOpinion', reviewFields.reviewOpinion)
    setNodeData(node, 'reviewTime', reviewFields.reviewTime)
    setNodeData(node, 'reviewerId', reviewFields.reviewerId)
    setNodeData(node, 'reviewerName', reviewFields.reviewerName)
    setNodeData(node, 'reviewStatus', reviewFields.reviewStatus)
  }
  setNodeData(node, 'note', nodeData.value.note)
  updateNodeNoteBadge(node)
  updateNodeReviewBadge(node)
  scheduleModuleOverviewRefresh(40)
}

// 切换主题
const changeTheme = () => {
  if (!ensureMindmapEditable()) return
  if (minder) {
    minder.execCommand('Theme', currentTheme.value)
    scheduleEditorRefocus()
  }
}

const handleThemeCommand = (themeValue) => {
  if (!themeOptions.some(option => option.value === themeValue)) {
    return
  }
  if (!ensureMindmapEditable()) return

  currentTheme.value = themeValue
  changeTheme()
}

// 切换布局模板
const changeTemplate = () => {
  if (!ensureMindmapEditable()) return
  if (minder) {
    minder.execCommand('Template', currentTemplate.value)
    setTimeout(() => {
      minder.execCommand('Camera')
    }, 100)
    scheduleEditorRefocus(140)
  }
}

const handleTemplateCommand = (templateValue) => {
  if (!templateOptions.some(option => option.value === templateValue)) {
    return
  }
  if (!ensureMindmapEditable()) return

  currentTemplate.value = templateValue
  changeTemplate()
}

// 递归统计子节点中指定类型节点的数量
const countDescendantNodesByType = (node, nodeType) => {
  if (!node) return 0

  let count = 0
  const data = getNodeData(node)

  // 如果当前节点类型匹配，计数+1
  if (data.nodeType === nodeType) {
    count++
  }

  // 递归统计所有子节点
  const children = node.getChildren()
  if (children && children.length > 0) {
    children.forEach(child => {
      count += countDescendantNodesByType(child, nodeType)
    })
  }

  return count
}

// 创建统计数标记 - 带背景色块的数字
const createCountBadge = (count, bgColor, textColor, x, y) => {
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  g.classList.add('custom-badge')
  g.classList.add('custom-count-badge')

  // 计算文字宽度，调整背景矩形宽度
  const textWidth = count.length * 7 + 6  // 每个字符约7px，加上左右padding

  // 背景矩形 - 圆角矩形
  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  rect.setAttribute('x', x)
  rect.setAttribute('y', y - 7)
  rect.setAttribute('width', textWidth)
  rect.setAttribute('height', '14')
  rect.setAttribute('rx', '7')  // 圆角半径
  rect.setAttribute('ry', '7')
  rect.setAttribute('fill', bgColor)
  g.appendChild(rect)

  // 文字
  const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text')
  textEl.setAttribute('text-rendering', 'geometricPrecision')
  textEl.setAttribute('x', x + textWidth / 2)
  textEl.setAttribute('y', y)
  textEl.setAttribute('text-anchor', 'middle')
  textEl.setAttribute('font-size', '11')
  textEl.setAttribute('font-weight', 'bold')
  textEl.setAttribute('fill', textColor)
  textEl.setAttribute('dy', '4')
  textEl.textContent = count
  g.appendChild(textEl)

  return g
}

const INLINE_MARKER_GAP = 4
const INLINE_MARKER_MAX_CHAIN_WIDTH = 160

const svgClientPointToContainerLocal = (container, clientX, clientY) => {
  const svg = container?.ownerSVGElement
  const ctm = container?.getScreenCTM?.()
  if (!svg || typeof svg.createSVGPoint !== 'function' || !ctm) {
    return null
  }

  const point = svg.createSVGPoint()
  point.x = clientX
  point.y = clientY
  try {
    return point.matrixTransform(ctm.inverse())
  } catch (error) {
    return null
  }
}

const getSvgElementBoxInContainer = (container, element) => {
  if (!container || !element) return null

  try {
    const rect = element.getBoundingClientRect?.()
    if (rect && (rect.width || rect.height)) {
      const topLeft = svgClientPointToContainerLocal(container, rect.left, rect.top)
      const bottomRight = svgClientPointToContainerLocal(container, rect.right, rect.bottom)
      if (topLeft && bottomRight) {
        const x = Math.min(topLeft.x, bottomRight.x)
        const y = Math.min(topLeft.y, bottomRight.y)
        const right = Math.max(topLeft.x, bottomRight.x)
        const bottom = Math.max(topLeft.y, bottomRight.y)
        return {
          x,
          y,
          width: right - x,
          height: bottom - y,
          right,
          bottom,
        }
      }
    }
  } catch (error) {
    // Fall back to getBBox below.
  }

  try {
    const bbox = element.getBBox()
    return {
      x: bbox.x,
      y: bbox.y,
      width: bbox.width,
      height: bbox.height,
      right: bbox.x + bbox.width,
      bottom: bbox.y + bbox.height,
    }
  } catch (error) {
    return null
  }
}

const isCustomInlineBadgeElement = element => Boolean(
  element?.closest?.('.custom-count-badge, .custom-status-badge, .custom-note-badge, .custom-icon-badge, .custom-review-badge')
)

const getNodeMainTextElement = (node, container) => {
  if (!container) return null

  const expectedText = String(node?.getText?.() || getNodeData(node).text || '').trim()
  const textElements = Array.from(container.querySelectorAll('text'))
    .filter(element => !isCustomInlineBadgeElement(element))

  if (expectedText) {
    const matched = textElements.find(element => String(element.textContent || '').trim() === expectedText)
    if (matched) return matched
  }

  return textElements[0] || container.querySelector('text')
}

const applyModuleMatchMarkerStyle = node => {
  if (!node) return

  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const container = node.getRenderContainer?.()?.node
    if (!container) return

    const resourceText = Array.from(container.querySelectorAll('text')).find(element => (
      String(element.textContent || '').trim() === 'M' &&
      element.parentElement?.querySelector('path, rect')
    ))
    const resourceGroup = resourceText?.parentElement
    const resourceShape = resourceGroup?.querySelector('path, rect')
    if (!resourceGroup || !resourceShape || !resourceText) return

    const originalFillAttribute = 'data-testhub-original-fill'
    const originalTextFillAttribute = 'data-testhub-original-text-fill'
    const oldTitle = resourceGroup.querySelector('.testhub-module-match-title')

    if (data.nodeType === 'module' && data.moduleCategoryMatched === false) {
      if (!resourceShape.hasAttribute(originalFillAttribute)) {
        resourceShape.setAttribute(originalFillAttribute, resourceShape.getAttribute('fill') || '')
      }
      if (!resourceText.hasAttribute(originalTextFillAttribute)) {
        resourceText.setAttribute(originalTextFillAttribute, resourceText.getAttribute('fill') || '')
      }
      resourceShape.setAttribute('fill', '#f56c6c')
      resourceText.setAttribute('fill', '#ffffff')
      resourceGroup.classList.add('module-resource-unmatched')
      resourceGroup.setAttribute('data-module-match', 'unmatched')
      resourceGroup.setAttribute('data-module-node-text', String(data.text || node.getText?.() || '').trim())

      if (!oldTitle) {
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title')
        title.classList.add('testhub-module-match-title')
        title.textContent = '未匹配到目录树节点'
        resourceGroup.prepend(title)
      }
      return
    }

    if (resourceShape.hasAttribute(originalFillAttribute)) {
      resourceShape.setAttribute('fill', resourceShape.getAttribute(originalFillAttribute) || '')
      resourceShape.removeAttribute(originalFillAttribute)
    }
    if (resourceText.hasAttribute(originalTextFillAttribute)) {
      resourceText.setAttribute('fill', resourceText.getAttribute(originalTextFillAttribute) || '')
      resourceText.removeAttribute(originalTextFillAttribute)
    }
    resourceGroup.classList.remove('module-resource-unmatched')
    if (data.nodeType === 'module' && data.moduleCategoryMatched === true) {
      resourceGroup.setAttribute('data-module-match', 'matched')
      resourceGroup.setAttribute('data-module-node-text', String(data.text || node.getText?.() || '').trim())
    } else {
      resourceGroup.removeAttribute('data-module-match')
      resourceGroup.removeAttribute('data-module-node-text')
    }
    oldTitle?.remove()
  })
}

const getRightmostInlineMarkerX = (container, startX, {
  includeCustomIcon = true,
  includeStatus = true,
  includeNote = true,
  includeReview = true,
  includeCount = true,
  includeNativeResource = true,
} = {}) => {
  if (!container) return startX

  const selectors = []
  if (includeNativeResource) selectors.push('[data-resource]', 'text')
  if (includeCount) selectors.push('.custom-count-badge')
  if (includeCustomIcon) selectors.push('.custom-icon-badge')
  if (includeStatus) selectors.push('.custom-status-badge')
  if (includeNote) selectors.push('.custom-note-badge')
  if (includeReview) selectors.push('.custom-review-badge')
  if (!selectors.length) return startX

  let rightmostX = startX
  const maxMarkerRight = startX + INLINE_MARKER_MAX_CHAIN_WIDTH
  container.querySelectorAll(selectors.join(',')).forEach(element => {
    if (element.tagName?.toLowerCase() === 'text' && isCustomInlineBadgeElement(element)) {
      return
    }

    const box = getSvgElementBoxInContainer(container, element)
    const rightEdge = box?.right
    if (Number.isFinite(rightEdge) && rightEdge > rightmostX && rightEdge < maxMarkerRight) {
      rightmostX = rightEdge
    }
  })
  return rightmostX
}

const updateNodeCustomIconBadge = (node) => {
  if (!node) return

  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const rc = node.getRenderContainer?.()
    if (!rc || !rc.node) return

    const oldBadges = rc.node.querySelectorAll('.custom-icon-badge')
    oldBadges.forEach(badge => badge.remove())

    const config = customIconOptions[data.customIcon]
    if (!config) return

    const textElement = getNodeMainTextElement(node, rc.node)
    if (!textElement) return

    try {
      const textBox = getSvgElementBoxInContainer(rc.node, textElement)
      if (!textBox) return
      const textEndX = textBox.right
      const textY = textBox.y + textBox.height / 2
      const badgeX = getRightmostInlineMarkerX(rc.node, textEndX, {
        includeCustomIcon: false,
        includeStatus: true,
        includeNote: true,
      }) + INLINE_MARKER_GAP
      const namespace = 'http://www.w3.org/2000/svg'
      const badge = document.createElementNS(namespace, 'g')
      badge.classList.add('custom-icon-badge')
      badge.setAttribute('data-custom-icon', data.customIcon)
      badge.setAttribute('pointer-events', 'none')

      const title = document.createElementNS(namespace, 'title')
      title.textContent = config.label
      badge.appendChild(title)

      const iconText = document.createElementNS(namespace, 'text')
      iconText.setAttribute('x', badgeX)
      iconText.setAttribute('y', textY + 5)
      iconText.setAttribute('font-size', '16')
      iconText.setAttribute('text-anchor', 'start')
      iconText.setAttribute('text-rendering', 'geometricPrecision')
      iconText.textContent = config.icon

      badge.appendChild(iconText)
      rc.node.appendChild(badge)
    } catch (error) {
      console.log('updateNodeCustomIconBadge error:', error)
    }
  })
}

const updateNodeReviewBadge = node => {
  if (!node) return

  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const container = node.getRenderContainer?.()?.node
    if (!container) return

    container.querySelectorAll('.custom-review-badge').forEach(badge => badge.remove())
    if (data.nodeType !== 'testpoint' || data.reviewStatus !== '未处理') return

    const textElement = getNodeMainTextElement(node, container)
    const textBox = getSvgElementBoxInContainer(container, textElement)
    if (!textBox) return

    const namespace = 'http://www.w3.org/2000/svg'
    const centerX = getRightmostInlineMarkerX(container, textBox.right, {
      includeReview: false,
    }) + INLINE_MARKER_GAP + 8
    const centerY = textBox.y + textBox.height / 2
    const badge = document.createElementNS(namespace, 'g')
    badge.classList.add('custom-review-badge')
    badge.setAttribute('data-review-status', 'unprocessed')
    badge.setAttribute('pointer-events', 'none')

    const title = document.createElementNS(namespace, 'title')
    title.textContent = '评审待处理'
    const circle = document.createElementNS(namespace, 'circle')
    circle.setAttribute('cx', centerX)
    circle.setAttribute('cy', centerY)
    circle.setAttribute('r', '8')
    circle.setAttribute('fill', '#fa8c16')
    circle.setAttribute('stroke', '#ffffff')
    circle.setAttribute('stroke-width', '1')
    const text = document.createElementNS(namespace, 'text')
    text.setAttribute('x', centerX)
    text.setAttribute('y', centerY + 4)
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('font-size', '12')
    text.setAttribute('font-weight', '700')
    text.setAttribute('fill', '#ffffff')
    text.textContent = '!'

    badge.appendChild(title)
    badge.appendChild(circle)
    badge.appendChild(text)
    container.appendChild(badge)
  })
}

// 更新节点统计标记
const updateNodeTypeBadge = (node) => {
  if (!node) return

  // 使用 requestAnimationFrame 确保在渲染后执行
  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const rc = node.getRenderContainer()
    if (!rc || !rc.node) return

    // 删除所有旧的自定义统计标记
    const oldCountBadges = rc.node.querySelectorAll('.custom-count-badge')
    oldCountBadges.forEach(badge => badge.remove())

  // 只对容器型节点添加统计数
  if (!['module', 'requirement', 'page', 'function'].includes(data.nodeType)) return

  const countBadges = []
  const pageCount = countDescendantNodesByType(node, 'page')
  const functionCount = countDescendantNodesByType(node, 'function')
  const caseCount = countDescendantNodesByType(node, 'case')
  const testpointCount = countDescendantNodesByType(node, 'testpoint')

  if (pageCount > 0) {
    countBadges.push({
      count: pageCount.toString(),
      bgColor: '#13c2c2',
      textColor: 'white'
    })
  }

  if (functionCount > 0) {
    countBadges.push({
      count: functionCount.toString(),
      bgColor: '#722ed1',
      textColor: 'white'
    })
  }

  if (caseCount > 0) {
    countBadges.push({
      count: caseCount.toString(),
        bgColor: '#1890ff',
        textColor: 'white'
      })
    }

    if (testpointCount > 0) {
      countBadges.push({
        count: testpointCount.toString(),
        bgColor: '#ff4d4f',
        textColor: 'white'
      })
    }

    if (countBadges.length === 0) return

    // 查找类型标记（resource）的位置
    // resource 标记通常在文本右侧
    const textElement = getNodeMainTextElement(node, rc.node)
    if (!textElement) return

    try {
      const textBox = getSvgElementBoxInContainer(rc.node, textElement)
      if (!textBox) return
      const textEndX = textBox.right
      const textY = textBox.y + textBox.height / 2

      let currentX = getRightmostInlineMarkerX(rc.node, textEndX, {
        includeCustomIcon: false,
        includeStatus: false,
        includeNote: false,
        includeCount: false,
      }) + INLINE_MARKER_GAP

      countBadges.forEach(badgeConfig => {
        const countBadge = createCountBadge(
          badgeConfig.count,
          badgeConfig.bgColor,
          badgeConfig.textColor,
          currentX,
          textY
        )
        countBadge.classList.add('custom-count-badge')
        rc.node.appendChild(countBadge)
        currentX += badgeConfig.count.length * 7 + 6 + INLINE_MARKER_GAP
      })
    } catch (e) {
      console.log('updateNodeTypeBadge error:', e)
    }
  })
}

// 更新节点及其所有祖先节点的统计标记和状态标记
const updateNodeAndAncestors = (node) => {
  if (!node) return

  // 更新当前节点
  updateNodeTypeBadge(node)
  updateNodeStatusBadge(node)
  updateNodeNoteBadge(node)
  updateNodeCustomIconBadge(node)
  updateNodeReviewBadge(node)
  applyModuleMatchMarkerStyle(node)

  // 递归更新所有祖先节点（父节点、祖父节点等）
  let parent = node.parent
  while (parent) {
    updateNodeTypeBadge(parent)
    updateNodeStatusBadge(parent)
    updateNodeNoteBadge(parent)
    updateNodeCustomIconBadge(parent)
    updateNodeReviewBadge(parent)
    applyModuleMatchMarkerStyle(parent)
    parent = parent.parent
  }
}

// 设置节点类型（支持多选批量操作）
const setNodeType = (payload) => {
  if (!ensureMindmapEditable()) return
  if (!minder) return
  const isClearing = Boolean(payload && typeof payload === 'object' && payload.clear)

  // 获取所有选中的节点（支持多选）
  const targetNodes = getScopedPointActionTargets('设置节点类型')
  if (!targetNodes.length) return
  const selectedNodes = targetNodes

  // 批量设置所有选中节点的类型
  targetNodes.forEach(node => {
    // 保存节点类型数据
    setNodeDataSilently(node, 'nodeType', currentNodeType.value)

    const typeLabel = nodeTypeLabels[currentNodeType.value]
    if (typeLabel) {
      // 设置resource数组，显示类型标记
      node.setData('resource', [typeLabel])
    } else {
      node.setData('resource', [])
    }

    if (typeLabel) {
      node.setData('resource', [typeLabel])
    }

    if (currentNodeType.value === 'testpoint') {
      applySelfTestDetailDefaultsToNode(node)
    }

    minder.renderNode(node)
  })

  // 更新所有选中节点及其祖先节点的统计数
  emitMindmapContentChange()
  const currentNode = getCurrentNode()
  if (currentNode) {
    loadNodeDetails(currentNode)
  }

  setTimeout(() => {
    targetNodes.forEach(node => {
      updateNodeAndAncestors(node)
    })
  }, 50)
  scheduleModuleOverviewRefresh(80)

  // 提示用户
  if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection || targetNodes.length > 1) {
    ElMessage.success(isClearing
      ? `已批量清除 ${selectedNodes.length} 个节点的类型标记`
      : `已批量设置 ${selectedNodes.length} 个节点的类型`)
  }
  scheduleEditorRefocus()
}

// 设置优先级（支持多选批量操作）
const setPriority = (payload) => {
  if (!ensureMindmapEditable()) return
  if (!minder) return
  const isClearing = Boolean(payload && typeof payload === 'object' && payload.clear)

  // 获取所有选中的节点（支持多选）
  const targetNodes = getScopedPointActionTargets('设置优先级')
  if (!targetNodes.length) return
  const selectedNodes = targetNodes

  // 批量设置所有选中节点的优先级
  targetNodes.forEach(node => {
    // 保存优先级数据（值为1-4）
    setNodeDataSilently(node, 'priority', currentPriority.value)

    // 使用KityMinder原生的优先级标记（直接使用1-4的值，对应P1-P4）
    if (currentPriority.value !== undefined && currentPriority.value !== null) {
      node.setData('priority', currentPriority.value)
    } else {
      node.setData('priority', null)  // null表示清除优先级
    }

    minder.renderNode(node)
  })

  // 优先级标记会影响状态标记的位置，渲染后需要同步刷新
  setTimeout(() => {
    targetNodes.forEach(node => {
      updateNodeStatusBadge(node)
    })
  }, 50)
  scheduleModuleOverviewRefresh(80)

  // 提示用户
  emitMindmapContentChange()
  if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection || targetNodes.length > 1) {
    ElMessage.success(isClearing
      ? `已批量清除 ${selectedNodes.length} 个节点的优先级标记`
      : `已批量设置 ${selectedNodes.length} 个节点的优先级`)
  }
  scheduleEditorRefocus()
}

// 更新节点状态标记
const updateNodeStatusBadge = (node) => {
  if (!node) return

  // 使用 requestAnimationFrame 确保在渲染后执行
  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const rc = node.getRenderContainer()
    if (!rc || !rc.node) return

    // 删除旧的状态标记
    const oldStatusBadges = rc.node.querySelectorAll('.custom-status-badge')
    oldStatusBadges.forEach(badge => badge.remove())

    // 只对测试用例和测试点节点显示状态标记
    if (data.nodeType !== 'case' && data.nodeType !== 'testpoint') return
    if (!data.status || data.status === 'not_run') return // 未执行状态不显示标记

    const statusConfig = {
      'pass': { text: '✅通过', bgColor: '#52c41a', textColor: 'white' },
      'fail': { text: '❌失败', bgColor: '#ff4d4f', textColor: 'white' },
      'block': { text: '🚫阻塞', bgColor: '#faad14', textColor: 'white' },
      'not_test': { text: '⊘不测', bgColor: '#6b7280', textColor: 'white' }
    }

    const config = statusConfig[data.status]
    if (!config) return

    // 查找文本元素位置
    const textElement = getNodeMainTextElement(node, rc.node)
    if (!textElement) return

    try {
      const textBox = getSvgElementBoxInContainer(rc.node, textElement)
      if (!textBox) return
      let startX = textBox.right
      const textY = textBox.y + textBox.height / 2

      const rightmostX = getRightmostInlineMarkerX(rc.node, startX, {
        includeCustomIcon: false,
        includeStatus: false,
      })

      const badgeX = rightmostX + INLINE_MARKER_GAP

      // 创建状态标记
      const statusBadge = document.createElementNS('http://www.w3.org/2000/svg', 'g')
      statusBadge.classList.add('custom-status-badge')

      // 计算标记尺寸
      const badgeText = config.text
      const badgeWidth = badgeText.length * 9 + 16
      const badgeHeight = 20
      const badgeY = textY - badgeHeight / 2

      // 创建背景矩形
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      rect.setAttribute('x', badgeX)
      rect.setAttribute('y', badgeY)
      rect.setAttribute('width', badgeWidth)
      rect.setAttribute('height', badgeHeight)
      rect.setAttribute('fill', config.bgColor)
      rect.setAttribute('rx', 10)
      rect.setAttribute('ry', 10)

      // 创建文本
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      text.setAttribute('x', badgeX + badgeWidth / 2)
      text.setAttribute('y', badgeY + badgeHeight / 2 + 4)
      text.setAttribute('text-anchor', 'middle')
      text.setAttribute('fill', config.textColor)
      text.setAttribute('font-size', '11')
      text.setAttribute('font-weight', 'bold')
      text.textContent = badgeText

      statusBadge.appendChild(rect)
      statusBadge.appendChild(text)
      rc.node.appendChild(statusBadge)
    } catch (e) {
      console.log('updateNodeStatusBadge error:', e)
    }
  })
}

// 设置状态（支持多选批量操作）
const updateNodeNoteBadge = (node) => {
  if (!node) return

  requestAnimationFrame(() => {
    const data = getNodeData(node)
    const rc = node.getRenderContainer?.()
    if (!rc || !rc.node) return

    const oldBadges = rc.node.querySelectorAll('.custom-note-badge')
    oldBadges.forEach(badge => badge.remove())

    const noteText = String(data.note || '').trim()
    if (!noteText) return

    const textElement = getNodeMainTextElement(node, rc.node)
    if (!textElement) return

    try {
      const textBox = getSvgElementBoxInContainer(rc.node, textElement)
      if (!textBox) return
      const badgeSize = 16
      const badgeX = textBox.right + INLINE_MARKER_GAP
      const badgeY = textBox.y - badgeSize - 2
      const namespace = 'http://www.w3.org/2000/svg'
      const badge = document.createElementNS(namespace, 'g')
      badge.classList.add('custom-note-badge')

      const title = document.createElementNS(namespace, 'title')
      title.textContent = noteText.length > 120 ? `${noteText.slice(0, 120)}...` : noteText
      badge.appendChild(title)

      const rect = document.createElementNS(namespace, 'rect')
      rect.setAttribute('x', badgeX)
      rect.setAttribute('y', badgeY)
      rect.setAttribute('width', badgeSize)
      rect.setAttribute('height', badgeSize)
      rect.setAttribute('rx', 3)
      rect.setAttribute('ry', 3)
      rect.setAttribute('fill', '#fff7e6')
      rect.setAttribute('stroke', '#fa8c16')
      rect.setAttribute('stroke-width', '1')

      const foldedCorner = document.createElementNS(namespace, 'path')
      foldedCorner.setAttribute('d', `M ${badgeX + 11} ${badgeY} L ${badgeX + 16} ${badgeY + 5} L ${badgeX + 11} ${badgeY + 5} Z`)
      foldedCorner.setAttribute('fill', '#ffd591')
      foldedCorner.setAttribute('stroke', '#fa8c16')
      foldedCorner.setAttribute('stroke-width', '0.8')

      const line1 = document.createElementNS(namespace, 'line')
      line1.setAttribute('x1', badgeX + 4)
      line1.setAttribute('y1', badgeY + 7)
      line1.setAttribute('x2', badgeX + 12)
      line1.setAttribute('y2', badgeY + 7)
      line1.setAttribute('stroke', '#d46b08')
      line1.setAttribute('stroke-width', '1.2')

      const line2 = document.createElementNS(namespace, 'line')
      line2.setAttribute('x1', badgeX + 4)
      line2.setAttribute('y1', badgeY + 11)
      line2.setAttribute('x2', badgeX + 11)
      line2.setAttribute('y2', badgeY + 11)
      line2.setAttribute('stroke', '#d46b08')
      line2.setAttribute('stroke-width', '1.2')

      badge.appendChild(rect)
      badge.appendChild(foldedCorner)
      badge.appendChild(line1)
      badge.appendChild(line2)
      rc.node.appendChild(badge)
    } catch (error) {
      console.log('updateNodeNoteBadge error:', error)
    }
  })
}

const setStatus = (payload) => {
  if (!ensureMindmapEditable()) return
  if (!minder) return
  const isClearing = Boolean(payload && typeof payload === 'object' && payload.clear)

  // 获取所有选中的节点（支持多选）
  const targetNodes = getScopedPointActionTargets('设置状态')
  if (!targetNodes.length) return
  const selectedNodes = targetNodes

  // 批量设置所有选中节点的状态
  targetNodes.forEach(node => {
    setNodeDataSilently(node, 'status', currentStatus.value)
    updateNodeStyle(node)
  })

  // 更新所有选中节点的状态标记
  setTimeout(() => {
    targetNodes.forEach(node => {
      updateNodeStatusBadge(node)
    })
  }, 50)
  scheduleModuleOverviewRefresh(80)

  // 提示用户
  emitMindmapContentChange()
  if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection || targetNodes.length > 1) {
    ElMessage.success(isClearing
      ? `已批量清除 ${selectedNodes.length} 个节点的状态标记`
      : `已批量设置 ${selectedNodes.length} 个节点的状态`)
  }
  scheduleEditorRefocus()
}

const clearNodeType = () => {
  if (!ensureMindmapEditable()) return
  currentNodeType.value = ''
  setNodeType({ clear: true })
}

const clearPriority = () => {
  if (!ensureMindmapEditable()) return
  currentPriority.value = null
  setPriority({ clear: true })
}

const clearStatus = () => {
  if (!ensureMindmapEditable()) return
  currentStatus.value = ''
  setStatus({ clear: true })
}

// 更新节点样式（根据属性）- 用于加载脑图时初始化节点
const updateNodeStyle = (node) => {
  if (!node) return

  const data = getNodeData(node)

  // 设置优先级（使用KityMinder原生标记，直接使用1-4的值对应P1-P4）
  if (data.priority !== undefined && data.priority !== null) {
    node.setData('priority', data.priority)
  } else {
    node.setData('priority', null)
  }

  // 设置类型（使用KityMinder原生resource字段）
  const typeLabel = nodeTypeLabels[data.nodeType]
  if (typeLabel) {
    node.setData('resource', [typeLabel])
  } else {
    node.setData('resource', [])
  }

  const textColor = getNodeTextColor(data)
  if (textColor) {
    node.setData('forecolor', textColor)
    node.setData('textColor', textColor)
    node.setData('text_color', textColor)
  }

  // 渲染节点
  minder.renderNode(node)

  if (textColor) {
    applyNodeTextColor(node, textColor)
  }

  // 渲染后更新状态标记
  setTimeout(() => {
    if (textColor) {
      applyNodeTextColor(node, textColor)
    }
    updateNodeStatusBadge(node)
    updateNodeNoteBadge(node)
    updateNodeCustomIconBadge(node)
    updateNodeReviewBadge(node)
    applyModuleMatchMarkerStyle(node)
  }, 50)
}

// 标签相关方法
const showTagDialog = () => {
  tagDialogVisible.value = true
}

const addTag = () => {
  if (!newTag.value.trim()) {
    ElMessage.warning('请输入标签名称')
    return
  }

  if (!minder) return

  // 获取所有选中的节点（支持多选）
  const selectedNodes = minder.getSelectedNodes()
  if (!selectedNodes || selectedNodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }

  const tagToAdd = newTag.value.trim()
  let successCount = 0

  // 批量为所有选中节点添加标签
  selectedNodes.forEach(node => {
    const nodeData = getNodeData(node)
    const nodeTags = nodeData.tags || []

    // 只有当节点不包含该标签时才添加
    if (!nodeTags.includes(tagToAdd)) {
      nodeTags.push(tagToAdd)
      setNodeData(node, 'tags', [...nodeTags])
      successCount++
    }
  })

  newTag.value = ''

  if (successCount > 0) {
    // 刷新当前节点的标签显示
    if (selectedNodes.length === 1) {
      const node = selectedNodes[0]
      const nodeData = getNodeData(node)
      currentTags.value = nodeData.tags || []
    }

    if (selectedNodes.length > 1) {
      ElMessage.success(`已为 ${successCount} 个节点添加标签`)
    } else {
      ElMessage.success('标签添加成功')
    }
  } else {
    ElMessage.warning('所有选中节点均已包含该标签')
  }
}

const addPresetTag = (tag) => {
  if (!minder) return

  // 获取所有选中的节点（支持多选）
  const selectedNodes = minder.getSelectedNodes()
  if (!selectedNodes || selectedNodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }

  let successCount = 0

  // 批量为所有选中节点添加预设标签
  selectedNodes.forEach(node => {
    const nodeData = getNodeData(node)
    const nodeTags = nodeData.tags || []

    // 只有当节点不包含该标签时才添加
    if (!nodeTags.includes(tag)) {
      nodeTags.push(tag)
      setNodeData(node, 'tags', [...nodeTags])
      successCount++
    }
  })

  if (successCount > 0) {
    // 刷新当前节点的标签显示
    if (selectedNodes.length === 1) {
      const node = selectedNodes[0]
      const nodeData = getNodeData(node)
      currentTags.value = nodeData.tags || []
    }

    if (selectedNodes.length > 1) {
      ElMessage.success(`已为 ${successCount} 个节点添加标签`)
    } else {
      ElMessage.success('标签添加成功')
    }
  } else {
    ElMessage.warning('所有选中节点均已包含该标签')
  }
}

// 更新所有节点样式
const updateAllNodeStyles = () => {
  if (!minder) return

  const updateNodeRecursive = (node) => {
    if (!node) return
    updateNodeStyle(node)
    const children = node.getChildren()
    if (children) {
      children.forEach(child => updateNodeRecursive(child))
    }
  }

  const root = minder.getRoot()
  if (root) {
    updateNodeRecursive(root)
  }
}

// 更新所有节点的统计数和状态标记
const updateAllNodeCounts = () => {
  if (!minder) return

  const updateNodeRecursive = (node) => {
    if (!node) return
    updateNodeTypeBadge(node)
    updateNodeStatusBadge(node) // 同时更新状态标记
    updateNodeNoteBadge(node)
    updateNodeCustomIconBadge(node)
    updateNodeReviewBadge(node)
    applyModuleMatchMarkerStyle(node)
    const children = node.getChildren()
    if (children) {
      children.forEach(child => updateNodeRecursive(child))
    }
  }

  const root = minder.getRoot()
  if (root) {
    updateNodeRecursive(root)
  }
}

const removeTag = (tag) => {
  const node = getCurrentNode()
  if (!node) return

  currentTags.value = currentTags.value.filter(t => t !== tag)
  setNodeData(node, 'tags', [...currentTags.value])
  ElMessage.success('标签已删除')
}

const getTagType = (tag) => {
  const typeMap = {
    '正向': 'success',
    '负向': 'danger',
    '接口': 'primary',
    'UI': 'warning',
    '冒烟': 'danger',
    '核心': 'danger',
    '性能': 'warning',
    '安全': 'danger'
  }
  return typeMap[tag] || 'info'
}

// 过滤相关方法
const showFilterDialog = () => {
  filterDialogVisible.value = true
}

const applyFilter = () => {
  if (!minder) return

  const { priorities, statuses, tag } = filterOptions.value

  // 如果所有过滤条件都为空，则显示全部
  if (priorities.length === 0 && statuses.length === 0 && !tag) {
    clearFilter()
    return
  }

  hasFilter.value = true

  // 遍历所有节点，根据过滤条件显示/隐藏
  const root = minder.getRoot()
  filterNode(root)

  filterDialogVisible.value = false
  ElMessage.success('过滤已应用')
}

const filterNode = (node) => {
  if (!node) return true

  const data = getNodeData(node)
  const { priorities, statuses, tag } = filterOptions.value

  let visible = true

  // 优先级过滤
  if (priorities.length > 0 && data.priority !== undefined) {
    visible = visible && priorities.includes(data.priority)
  }

  // 状态过滤
  if (statuses.length > 0 && data.status) {
    visible = visible && statuses.includes(data.status)
  }

  // 标签过滤
  if (tag && data.tags) {
    visible = visible && data.tags.some(t => t.includes(tag))
  }

  // 递归处理子节点
  const children = node.getChildren()
  if (children && children.length > 0) {
    children.forEach(child => filterNode(child))
  }

  // 设置节点可见性
  if (node !== minder.getRoot()) {
    if (visible) {
      node.setData('_visible', true)
    } else {
      node.setData('_visible', false)
    }
  }

  return visible
}

const clearFilter = () => {
  if (!minder) return

  filterOptions.value = {
    priorities: [],
    statuses: [],
    tag: ''
  }
  hasFilter.value = false

  // 显示所有节点
  const root = minder.getRoot()
  showAllNodes(root)
  scheduleEditorRefocus()

  ElMessage.success('过滤已清除')
}

const showAllNodes = (node) => {
  if (!node) return
  node.setData('_visible', true)

  const children = node.getChildren()
  if (children && children.length > 0) {
    children.forEach(child => showAllNodes(child))
  }
}

// 样式命令处理
const handleStyleCommand = (command) => {
  if (!ensureMindmapEditable()) return
  const node = getCurrentNode()
  if (!node) {
    ElMessage.warning('请先选择节点')
    return
  }

  switch (command) {
    case 'bold':
      execCommand('Bold')
      break
    case 'italic':
      execCommand('Italic')
      break
    case 'forecolor':
      colorDialogType.value = 'forecolor'
      colorDialogTitle.value = '选择文字颜色'
      colorDialogVisible.value = true
      break
    case 'background':
      colorDialogType.value = 'background'
      colorDialogTitle.value = '选择背景颜色'
      colorDialogVisible.value = true
      break
    case 'fontsize':
      fontSizeDialogVisible.value = true
      break
    case 'fontfamily':
      fontFamilyDialogVisible.value = true
      break
  }
}

// 应用颜色
const applyColor = () => {
  if (!ensureMindmapEditable()) return
  if (!minder) return

  if (colorDialogType.value === 'forecolor') {
    minder.execCommand('ForeColor', selectedColor.value)
  } else if (colorDialogType.value === 'background') {
    minder.execCommand('Background', selectedColor.value)
  }

  colorDialogVisible.value = false
  scheduleEditorRefocus()
  ElMessage.success('颜色已应用')
}

// 应用字体大小
const applyFontSize = () => {
  if (!ensureMindmapEditable()) return
  if (minder) {
    minder.execCommand('FontSize', fontSize.value)
    fontSizeDialogVisible.value = false
    scheduleEditorRefocus()
    ElMessage.success('字体大小已应用')
  }
}

// 应用字体
const applyFontFamily = () => {
  if (!ensureMindmapEditable()) return
  if (minder) {
    minder.execCommand('FontFamily', fontFamily.value)
    fontFamilyDialogVisible.value = false
    scheduleEditorRefocus()
    ElMessage.success('字体已应用')
  }
}

// 图标命令处理
const handleIconCommand = (command) => {
  if (!ensureMindmapEditable()) return
  if (!minder) return

  const valueMap = {
    'priority-0': 0,
    'priority-1': 1,
    'priority-2': 2,
    'priority-3': 3,
  }
  const isPriorityCommand = Object.prototype.hasOwnProperty.call(valueMap, command)
  const isCustomIconCommand = customIconCommands.has(command)

  const targetNodes = getScopedPointActionTargets('设置图标')
  if (!targetNodes.length) return
  const selectedNodes = targetNodes

  if (isPriorityCommand || isCustomIconCommand) {
    targetNodes.forEach(node => {
      if (isPriorityCommand) {
        setNodeDataSilently(node, 'priority', valueMap[command])
        setNodeDataSilently(node, 'customIcon', null)
        node.setData('priority', valueMap[command])
      } else {
        setNodeDataSilently(node, 'customIcon', command)
        setNodeDataSilently(node, 'priority', null)
        node.setData('priority', null)
        node.setData('progress', null)
      }
      minder.renderNode(node)
    })

    emitMindmapContentChange()
    setTimeout(() => {
      targetNodes.forEach(node => {
        updateNodeStatusBadge(node)
        updateNodeNoteBadge(node)
        updateNodeCustomIconBadge(node)
      })
    }, 50)
    scheduleEditorRefocus()
    if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection || targetNodes.length > 1) {
      ElMessage.success(`已批量设置 ${selectedNodes.length} 个${batchOperationMode.value === BATCH_OPERATION_MODE.selection ? '节点' : '末级节点'}的图标`)
    } else {
      ElMessage.success('图标已设置')
    }
    return
  }
}

// 备注功能
const showNoteDialog = () => {
  if (!ensureMindmapEditable()) return
  const targetNodes = getScopedPointActionTargets('编辑备注')
  if (!targetNodes.length) return

  currentNote.value = getUniformNodeDataValue(targetNodes, 'note', '')
  noteTab.value = 'markdown'
  noteDialogVisible.value = true
}

const saveNote = () => {
  if (!ensureMindmapEditable()) return
  const targetNodes = getScopedPointActionTargets('保存备注')
  if (!targetNodes.length) return

  targetNodes.forEach(node => {
    setNodeDataSilently(node, 'note', currentNote.value)
    updateNodeNoteBadge(node)
  })

  emitMindmapContentChange()
  const currentNode = getCurrentNode()
  if (currentNode) {
    loadNodeDetails(currentNode)
  }
  noteDialogVisible.value = false
  scheduleEditorRefocus()
  if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection || targetNodes.length > 1) {
    ElMessage.success(`已批量保存 ${targetNodes.length} 个${batchOperationMode.value === BATCH_OPERATION_MODE.selection ? '节点' : '末级节点'}的备注`)
  } else {
    ElMessage.success('备注已保存')
  }
  return
  ElMessage.success('备注已保存')
}

const handleBack = () => {
  if (props.embedded) {
    emit('back')
    return
  }

  const returnPath = props.returnPath || getSingleQueryValue(route.query.return_path)
  if (returnPath) {
    router.push({
      path: returnPath,
      query: parseReturnQuery() || {}
    })
    return
  }

  const fromTab = route.query.from_tab
  const returnQuery = parseReturnQuery()
  router.push({
    path: '/manual-testcases/list',
    query: returnQuery || (fromTab ? { tab: fromTab } : {})
  })
}

// 保存脑图
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

const getNodeSourceLabel = nodeType => ({
  case: '测试用例',
  testpoint: '测试点',
  module: '模块',
  requirement: '需求',
  page: '页面',
  function: '功能',
}[nodeType] || '测试脑图节点')

const buildNodePathText = node => getNodePath(node)
  .map(currentNode => getNodeDisplayText(currentNode))
  .filter(Boolean)
  .join(' / ')

const buildNodeModulePath = node => getNodePath(node)
  .slice(0, -1)
  .filter(currentNode => ['module', 'page', 'function'].includes(getNodeData(currentNode).nodeType))
  .map(currentNode => getNodeDisplayText(currentNode))
  .filter(Boolean)
  .join(' / ')

const getNodePublicId = targetNode => {
  const nodeType = getNodeData(targetNode).nodeType
  if (!currentMindmapId.value || !['case', 'testpoint'].includes(nodeType)) {
    return String(getNodeData(targetNode).id || '').trim()
  }

  let sequence = 0
  let publicId = ''
  const visit = node => {
    if (!node || publicId) return

    if (getNodeData(node).nodeType === nodeType) {
      sequence += 1
      if (node === targetNode) {
        publicId = `${currentMindmapId.value}:${nodeType}:${sequence}`
        return
      }
    }

    getNodeChildren(node).forEach(child => visit(child))
  }

  visit(minder?.getRoot?.())
  return publicId || String(getNodeData(targetNode).id || '').trim()
}

const buildDefectDraftQuery = (extraQuery = {}) => {
  const query = {
    tab: 'version-defects',
    source: 'manual-testcases',
    project_id: currentProjectId.value || getContextQueryValue('project_id'),
    version_id: currentVersionId.value || getContextQueryValue('version_id'),
    category_id: currentCategoryId.value || getContextQueryValue('category_id'),
    requirement_id: currentRequirementKey.value,
    ...extraQuery
  }

  Object.keys(query).forEach(key => {
    const value = query[key]
    if (value === undefined || value === null || value === '' || value === 'all') {
      delete query[key]
      return
    }
    query[key] = String(value)
  })

  return query
}

const handleCreateDefect = async () => {
  if (!ensureMindmapEditable('当前为只读查看模式，不能从这里提缺陷')) return
  if (isRequirementAnalysisMindmap.value) {
    ElMessage.warning('\u9700\u6c42\u5206\u6790\u8111\u56fe\u4e0d\u5199\u5165\u6d4b\u8bd5\u8111\u56fe\uff0c\u4e0d\u652f\u6301\u5728\u8fd9\u91cc\u63d0\u7f3a\u9677')
    return
  }

  const node = getCurrentNode()
  if (!node) {
    ElMessage.warning('请先选择脑图节点')
    return
  }

  try {
    await persistMindmap({ createIfMissing: true })
  } catch (error) {
    console.error('提缺陷前保存脑图失败:', error)
    ElMessage.error('提缺陷前保存脑图失败：' + (error.response?.data?.detail || error.message))
    return
  }

  const data = getNodeData(node)
  const nodeType = data.nodeType || ''
  const sourceLabel = getNodeSourceLabel(nodeType)
  const nodeName = getNodeDisplayText(node)
  const nodePath = buildNodePathText(node)
  const modulePath = buildNodeModulePath(node)
  const parentNode = node.getParent?.() || node.parent || null
  const parentName = parentNode ? getNodeDisplayText(parentNode) : ''

  router.push({
    path: '/manual-testcases/defects/create',
    query: buildDefectDraftQuery({
      title: buildSourceDefectTitle(sourceLabel, nodeName, mindmapName.value),
      source_tab_name: sourceLabel,
      source_mindmap_id: currentMindmapId.value,
      source_mindmap: mindmapName.value,
      source_name: nodeName,
      source_parent_name: parentName,
      source_module: getLastPathSegment(modulePath) || parentName,
      source_module_path: modulePath,
      source_path: nodePath,
      source_case_id: data.caseId || '',
      source_node_id: getNodePublicId(node),
      source_responsibility_group: currentResponsibilityGroup.value,
      source_frontend_owner: currentFrontendDeveloper.value,
      source_backend_owner: currentBackendDeveloper.value
    })
  })
}

const handleSave = async () => {
  if (!ensureMindmapEditable('当前为只读查看模式，不能保存脑图')) return
  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return
  }

  clearMindmapAutoSaveTimer()
  pendingMindmapAutoSave = false

  try {
    const hadMindmapId = Boolean(currentMindmapId.value)
    const response = await persistMindmap({ createIfMissing: true })
    if (hadMindmapId) {
      ElMessage.success('脑图更新成功！')
    }
    if (response && !hadMindmapId) {
      ElMessage.success('脑图保存成功！')
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败：' + (error.response?.data?.message || error.message))
  }
}

// 导出命令处理
const handleExportCommand = async (command) => {
  if (!minder) {
    ElMessage.warning('脑图未初始化')
    return
  }

  switch (command) {
    case 'json':
      exportAsJson()
      break
    case 'xmind':
      await exportAsXMind()
      break
    case 'png':
      await exportAsPng()
      break
    case 'svg':
      exportAsSvg()
      break
    case 'markdown':
      exportAsMarkdown()
      break
    case 'text':
      exportAsText()
      break
  }
}

// 导出为JSON
const exportAsJson = () => {
  minderData.value = normalizeMindmapData(minder.exportJson())
  const dataStr = JSON.stringify(minderData.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  downloadFile(blob, `手工用例脑图_${Date.now()}.json`)
  ElMessage.success('导出JSON成功！')
}

// 导出为XMind
const exportAsXMind = async () => {
  try {
    minderData.value = normalizeMindmapData(minder.exportJson())
    const blob = await exportMindmapDataToXMindBlob(minderData.value, { title: mindmapName.value })
    downloadFile(blob, `手工用例脑图_${Date.now()}.xmind`)
    ElMessage.success('导出XMind成功！')
  } catch (error) {
    console.error('导出XMind失败:', error)
    ElMessage.error('导出XMind失败：' + (error.message || '请重试'))
  }
}

const PNG_BASE64_SIGNATURE = 'iVBORw0KGgo'
const PNG_BYTE_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]
const PNG_EXPORT_PAYLOAD_KEYS = ['data', 'dataUrl', 'dataURL', 'url', 'href', 'blob', 'file', 'content', 'value']
const MINDMAP_SVG_EXPORT_PADDING = 36
const MINDMAP_PNG_EXPORT_SCALE = 3
const MINDMAP_PNG_EXPORT_MAX_DIMENSION = 32760
const MINDMAP_PNG_EXPORT_MAX_PIXELS = 180000000
const MINDMAP_PNG_EXPORT_MAX_STREAM_PIXELS = 520000000
const MINDMAP_PNG_EXPORT_MAX_OUTPUT_DIMENSION = 240000
const MINDMAP_PNG_EXPORT_TILE_MAX_WIDTH = MINDMAP_PNG_EXPORT_MAX_DIMENSION
const MINDMAP_PNG_EXPORT_TILE_MAX_HEIGHT = 24000
const MINDMAP_PNG_EXPORT_TILE_MAX_PIXELS = 24000000
const MINDMAP_PNG_ENCODER_BATCH_MAX_BYTES = 24000000
const MINDMAP_PNG_IDAT_CHUNK_SIZE = 8 * 1024 * 1024
const MINDMAP_PNG_TILE_PRUNE_PADDING = 160
const MINDMAP_SVG_GRAPHIC_SELECTOR = [
  'path',
  'rect',
  'circle',
  'ellipse',
  'line',
  'polyline',
  'polygon',
  'text',
  'image',
  'use',
].join(',')
const MINDMAP_SVG_INLINE_STYLE_PROPERTIES = [
  'display',
  'visibility',
  'opacity',
  'fill',
  'fill-opacity',
  'fill-rule',
  'stroke',
  'stroke-opacity',
  'stroke-width',
  'stroke-linecap',
  'stroke-linejoin',
  'stroke-dasharray',
  'font-family',
  'font-size',
  'font-weight',
  'font-style',
  'text-anchor',
  'dominant-baseline',
]
const MINDMAP_SVG_EXPORT_BOUND_ATTRIBUTES = [
  'data-export-min-x',
  'data-export-min-y',
  'data-export-max-x',
  'data-export-max-y',
]

const isBlobValue = value => typeof Blob !== 'undefined' && value instanceof Blob
const isArrayBufferValue = value => typeof ArrayBuffer !== 'undefined' && value instanceof ArrayBuffer
const isArrayBufferViewValue = value => typeof ArrayBuffer !== 'undefined' && ArrayBuffer.isView?.(value)

const isHtmlDocumentLike = value => {
  const prefix = String(value || '').trimStart().slice(0, 80).toLowerCase()
  return prefix.startsWith('<!doctype html') || prefix.startsWith('<html')
}

const hasPngByteSignature = bytes => (
  bytes &&
  bytes.length >= PNG_BYTE_SIGNATURE.length &&
  PNG_BYTE_SIGNATURE.every((byte, index) => bytes[index] === byte)
)

const arrayBufferViewToUint8Array = value => new Uint8Array(value.buffer, value.byteOffset, value.byteLength)

const stringToAsciiBytes = value => {
  const bytes = new Uint8Array(String(value || '').length)
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = value.charCodeAt(index) & 0xff
  }
  return bytes
}

const concatUint8Arrays = arrays => {
  const totalLength = arrays.reduce((total, array) => total + array.length, 0)
  const result = new Uint8Array(totalLength)
  let offset = 0
  arrays.forEach(array => {
    result.set(array, offset)
    offset += array.length
  })
  return result
}

const writeUint32BigEndian = (target, offset, value) => {
  const normalized = Number(value) >>> 0
  target[offset] = (normalized >>> 24) & 0xff
  target[offset + 1] = (normalized >>> 16) & 0xff
  target[offset + 2] = (normalized >>> 8) & 0xff
  target[offset + 3] = normalized & 0xff
}

let pngCrcTable = null

const getPngCrcTable = () => {
  if (pngCrcTable) {
    return pngCrcTable
  }

  pngCrcTable = new Uint32Array(256)
  for (let index = 0; index < 256; index += 1) {
    let value = index
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1)
    }
    pngCrcTable[index] = value >>> 0
  }
  return pngCrcTable
}

const pngCrc32 = byteArrays => {
  const table = getPngCrcTable()
  let crc = 0xffffffff
  byteArrays.forEach(bytes => {
    for (let index = 0; index < bytes.length; index += 1) {
      crc = table[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8)
    }
  })
  return (crc ^ 0xffffffff) >>> 0
}

const createPngChunk = (type, data = new Uint8Array(0)) => {
  const typeBytes = stringToAsciiBytes(type)
  const payload = data instanceof Uint8Array ? data : new Uint8Array(data)
  const chunk = new Uint8Array(payload.length + 12)
  writeUint32BigEndian(chunk, 0, payload.length)
  chunk.set(typeBytes, 4)
  chunk.set(payload, 8)
  writeUint32BigEndian(chunk, payload.length + 8, pngCrc32([typeBytes, payload]))
  return chunk
}

const createPngIhdrData = (width, height) => {
  const data = new Uint8Array(13)
  writeUint32BigEndian(data, 0, width)
  writeUint32BigEndian(data, 4, height)
  data[8] = 8
  data[9] = 6
  data[10] = 0
  data[11] = 0
  data[12] = 0
  return data
}

const normalizeUint8Array = value => {
  if (value instanceof Uint8Array) {
    return value
  }
  if (isArrayBufferValue(value)) {
    return new Uint8Array(value)
  }
  if (isArrayBufferViewValue(value)) {
    return arrayBufferViewToUint8Array(value)
  }
  return new Uint8Array(value || [])
}

const canvasToPngBlob = canvas => new Promise((resolve, reject) => {
  canvas.toBlob(blob => {
    if (blob) {
      resolve(blob)
      return
    }
    reject(new Error('无法从画布生成PNG图片'))
  }, 'image/png')
})

const getCurrentMindmapSvgElement = () => {
  const editorElement = getMinderEditorElement()
  return editorElement?.querySelector?.('svg') || null
}

const isSvgExportElementVisible = element => {
  if (!element || element.closest?.('defs,clipPath,mask,pattern,marker')) {
    return false
  }
  if (typeof window === 'undefined' || typeof window.getComputedStyle !== 'function') {
    return true
  }
  const style = window.getComputedStyle(element)
  return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) !== 0
}

const transformSvgPoint = (svgElement, matrix, x, y) => {
  const point = svgElement.createSVGPoint()
  point.x = x
  point.y = y
  return point.matrixTransform(matrix)
}

const getSvgElementBounds = (svgElement, element) => {
  if (typeof element.getBBox !== 'function' || typeof element.getCTM !== 'function') {
    return null
  }

  let bbox
  let matrix
  try {
    bbox = element.getBBox()
    matrix = element.getCTM()
  } catch {
    return null
  }

  if (!bbox || !matrix || (!bbox.width && !bbox.height)) {
    return null
  }

  const points = [
    transformSvgPoint(svgElement, matrix, bbox.x, bbox.y),
    transformSvgPoint(svgElement, matrix, bbox.x + bbox.width, bbox.y),
    transformSvgPoint(svgElement, matrix, bbox.x, bbox.y + bbox.height),
    transformSvgPoint(svgElement, matrix, bbox.x + bbox.width, bbox.y + bbox.height),
  ]

  return points.reduce((bounds, point) => ({
    minX: Math.min(bounds.minX, point.x),
    minY: Math.min(bounds.minY, point.y),
    maxX: Math.max(bounds.maxX, point.x),
    maxY: Math.max(bounds.maxY, point.y),
  }), {
    minX: Number.POSITIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
  })
}

const mergeSvgBounds = (baseBounds, nextBounds) => {
  if (!nextBounds) {
    return baseBounds
  }
  if (!baseBounds) {
    return { ...nextBounds }
  }
  return {
    minX: Math.min(baseBounds.minX, nextBounds.minX),
    minY: Math.min(baseBounds.minY, nextBounds.minY),
    maxX: Math.max(baseBounds.maxX, nextBounds.maxX),
    maxY: Math.max(baseBounds.maxY, nextBounds.maxY),
  }
}

const isFiniteSvgBounds = bounds => (
  bounds &&
  Number.isFinite(bounds.minX) &&
  Number.isFinite(bounds.minY) &&
  Number.isFinite(bounds.maxX) &&
  Number.isFinite(bounds.maxY)
)

const formatSvgExportCoordinate = value => String(Math.round(value * 100) / 100)

const setSvgExportBoundsAttributes = (targetElement, bounds) => {
  if (!targetElement || !isFiniteSvgBounds(bounds)) {
    return
  }
  targetElement.setAttribute('data-export-min-x', formatSvgExportCoordinate(bounds.minX))
  targetElement.setAttribute('data-export-min-y', formatSvgExportCoordinate(bounds.minY))
  targetElement.setAttribute('data-export-max-x', formatSvgExportCoordinate(bounds.maxX))
  targetElement.setAttribute('data-export-max-y', formatSvgExportCoordinate(bounds.maxY))
}

const annotateCurrentMindmapSvgExportBounds = (sourceSvgElement, clonedSvgElement) => {
  const sourceMinderElement = sourceSvgElement.querySelector('#minder1')
  const clonedMinderElement = clonedSvgElement.querySelector('#minder1')
  if (!sourceMinderElement || !clonedMinderElement) {
    return
  }

  const sourceChildren = Array.from(sourceMinderElement.children || [])
  const clonedChildren = Array.from(clonedMinderElement.children || [])
  sourceChildren.forEach((sourceChild, childIndex) => {
    const clonedChild = clonedChildren[childIndex]
    if (!clonedChild) {
      return
    }

    const childId = sourceChild.id || ''
    if (childId.startsWith('minder_connect_group')) {
      const sourceConnectors = Array.from(sourceChild.children || [])
      const clonedConnectors = Array.from(clonedChild.children || [])
      sourceConnectors.forEach((sourceConnector, connectorIndex) => {
        setSvgExportBoundsAttributes(
          clonedConnectors[connectorIndex],
          getSvgElementBounds(sourceSvgElement, sourceConnector)
        )
      })
      return
    }

    if (childId.startsWith('minder_node')) {
      setSvgExportBoundsAttributes(
        clonedChild,
        getSvgElementBounds(sourceSvgElement, sourceChild)
      )
    }
  })
}

const getCurrentMindmapSvgContentBounds = svgElement => {
  const elements = Array.from(svgElement.querySelectorAll(MINDMAP_SVG_GRAPHIC_SELECTOR))
    .filter(isSvgExportElementVisible)

  let bounds = null
  elements.forEach(element => {
    bounds = mergeSvgBounds(bounds, getSvgElementBounds(svgElement, element))
  })

  if (!bounds || !Number.isFinite(bounds.minX) || !Number.isFinite(bounds.minY) || !Number.isFinite(bounds.maxX) || !Number.isFinite(bounds.maxY)) {
    throw new Error('未获取到当前脑图画布内容范围')
  }

  const width = Math.max(1, bounds.maxX - bounds.minX)
  const height = Math.max(1, bounds.maxY - bounds.minY)
  return {
    x: bounds.minX - MINDMAP_SVG_EXPORT_PADDING,
    y: bounds.minY - MINDMAP_SVG_EXPORT_PADDING,
    width: width + MINDMAP_SVG_EXPORT_PADDING * 2,
    height: height + MINDMAP_SVG_EXPORT_PADDING * 2,
  }
}

const inlineSvgComputedStyles = (sourceElement, targetElement) => {
  if (!sourceElement || !targetElement || typeof window === 'undefined' || typeof window.getComputedStyle !== 'function') {
    return
  }

  const computedStyle = window.getComputedStyle(sourceElement)
  MINDMAP_SVG_INLINE_STYLE_PROPERTIES.forEach(property => {
    const value = computedStyle.getPropertyValue(property)
    if (value) {
      targetElement.style.setProperty(property, value)
    }
  })

  const sourceChildren = Array.from(sourceElement.children || [])
  const targetChildren = Array.from(targetElement.children || [])
  sourceChildren.forEach((sourceChild, index) => {
    inlineSvgComputedStyles(sourceChild, targetChildren[index])
  })
}

const serializeCurrentMindmapSvg = () => {
  const svgElement = getCurrentMindmapSvgElement()
  if (!svgElement) {
    throw new Error('未找到当前脑图SVG画布')
  }

  const bounds = getCurrentMindmapSvgContentBounds(svgElement)
  const clonedSvg = svgElement.cloneNode(true)
  inlineSvgComputedStyles(svgElement, clonedSvg)
  annotateCurrentMindmapSvgExportBounds(svgElement, clonedSvg)
  clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  clonedSvg.setAttribute('viewBox', `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`)
  clonedSvg.setAttribute('width', String(Math.ceil(bounds.width)))
  clonedSvg.setAttribute('height', String(Math.ceil(bounds.height)))
  clonedSvg.setAttribute('preserveAspectRatio', 'xMidYMid meet')
  clonedSvg.style.width = `${Math.ceil(bounds.width)}px`
  clonedSvg.style.height = `${Math.ceil(bounds.height)}px`
  clonedSvg.style.background = '#ffffff'

  const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  background.setAttribute('x', String(bounds.x))
  background.setAttribute('y', String(bounds.y))
  background.setAttribute('width', String(bounds.width))
  background.setAttribute('height', String(bounds.height))
  background.setAttribute('fill', '#ffffff')
  clonedSvg.insertBefore(background, clonedSvg.firstChild)

  return {
    svgText: new XMLSerializer().serializeToString(clonedSvg),
    bounds,
  }
}

const resolvePngExportPayload = async (payload, depth = 0) => {
  if (depth > 6 || payload === undefined || payload === null) return ''
  if (typeof payload?.then === 'function') {
    return resolvePngExportPayload(await payload, depth + 1)
  }
  if (isBlobValue(payload) || isArrayBufferValue(payload) || isArrayBufferViewValue(payload) || typeof payload === 'string') {
    return payload
  }
  if (typeof HTMLCanvasElement !== 'undefined' && payload instanceof HTMLCanvasElement) {
    return canvasToPngBlob(payload)
  }
  if (typeof payload?.toDataURL === 'function') {
    return payload.toDataURL('image/png')
  }
  if (typeof payload === 'object') {
    for (const key of PNG_EXPORT_PAYLOAD_KEYS) {
      if (Object.prototype.hasOwnProperty.call(payload, key) && payload[key] !== payload) {
        const resolved = await resolvePngExportPayload(payload[key], depth + 1)
        if (resolved) return resolved
      }
    }
  }
  return ''
}

const assertBlobIsPng = async blob => {
  if (typeof blob.arrayBuffer !== 'function') {
    return
  }

  const signature = new Uint8Array(await blob.slice(0, PNG_BYTE_SIGNATURE.length).arrayBuffer())
  if (!hasPngByteSignature(signature)) {
    throw new Error('导出的PNG数据不是有效图片')
  }
}

const normalizePngDataUrl = rawValue => {
  const raw = String(rawValue || '').trim()
  if (isHtmlDocumentLike(raw)) {
    throw new Error('导出的PNG数据返回了HTML页面')
  }
  if (raw.toLowerCase() === 'data:,') {
    throw new Error('浏览器画布导出PNG失败')
  }

  const dataUrlMatch = raw.match(/^data:([^;,]+)((?:;[^,]*)*),([\s\S]*)$/i)
  if (dataUrlMatch) {
    const mimeType = dataUrlMatch[1].toLowerCase()
    const metadata = dataUrlMatch[2] || ''
    const body = dataUrlMatch[3] || ''
    if (mimeType !== 'image/png' || !metadata.toLowerCase().includes(';base64')) {
      throw new Error('导出的PNG数据类型无效')
    }

    const base64Payload = body.replace(/\s+/g, '')
    if (!base64Payload.startsWith(PNG_BASE64_SIGNATURE) || !/^[A-Za-z0-9+/=]+$/.test(base64Payload)) {
      throw new Error('导出的PNG数据不是有效图片')
    }
    return `data:image/png;base64,${base64Payload}`
  }

  const base64Payload = raw.replace(/\s+/g, '')
  if (!base64Payload.startsWith(PNG_BASE64_SIGNATURE) || !/^[A-Za-z0-9+/=]+$/.test(base64Payload)) {
    throw new Error('导出的PNG数据不是有效图片')
  }
  return `data:image/png;base64,${base64Payload}`
}

const loadImageElement = url => new Promise((resolve, reject) => {
  const image = new Image()
  image.onload = () => resolve(image)
  image.onerror = () => reject(new Error('SVG转PNG图片加载失败'))
  image.src = url
})

const exportSvgData = async () => resolvePngExportPayload(await minder.exportData('svg'))

const svgPayloadToText = async payload => {
  const resolvedPayload = await resolvePngExportPayload(payload)
  if (isBlobValue(resolvedPayload)) {
    return resolvedPayload.text()
  }
  if (isArrayBufferValue(resolvedPayload) || isArrayBufferViewValue(resolvedPayload)) {
    const bytes = isArrayBufferValue(resolvedPayload) ? new Uint8Array(resolvedPayload) : arrayBufferViewToUint8Array(resolvedPayload)
    return new TextDecoder('utf-8').decode(bytes)
  }
  return String(resolvedPayload || '')
}

const parseSvgDimension = (svgText, attributeName) => {
  const attributeMatch = svgText.match(new RegExp(`${attributeName}=["']?([0-9.]+)`, 'i'))
  if (attributeMatch) {
    return Math.max(1, Math.ceil(Number(attributeMatch[1]) || 0))
  }

  const viewBoxMatch = svgText.match(/viewBox=["']?([0-9.,\s-]+)["']?/i)
  if (viewBoxMatch) {
    const parts = viewBoxMatch[1].trim().split(/[,\s]+/).map(value => Number(value))
    const index = attributeName === 'width' ? 2 : 3
    if (Number.isFinite(parts[index]) && parts[index] > 0) {
      return Math.max(1, Math.ceil(parts[index]))
    }
  }
  return 1
}

const encodeSvgTextAsDataUrl = svgText => {
  const bytes = new TextEncoder().encode(svgText)
  const chunks = []
  const chunkSize = 0x8000
  for (let index = 0; index < bytes.length; index += chunkSize) {
    chunks.push(String.fromCharCode(...bytes.subarray(index, index + chunkSize)))
  }
  return `data:image/svg+xml;base64,${btoa(chunks.join(''))}`
}

const parseSvgViewBox = (svgText, sourceWidth, sourceHeight) => {
  const viewBoxMatch = String(svgText || '').match(/viewBox=["']?([0-9.eE,\s-]+)["']?/i)
  if (viewBoxMatch) {
    const parts = viewBoxMatch[1].trim().split(/[,\s]+/).map(value => Number(value))
    if (parts.length >= 4 && parts.every(Number.isFinite) && parts[2] > 0 && parts[3] > 0) {
      return {
        x: parts[0],
        y: parts[1],
        width: parts[2],
        height: parts[3],
      }
    }
  }
  return {
    x: 0,
    y: 0,
    width: sourceWidth,
    height: sourceHeight,
  }
}

const getSvgExportBoundsFromAttributes = element => {
  const minX = Number(element.getAttribute('data-export-min-x'))
  const minY = Number(element.getAttribute('data-export-min-y'))
  const maxX = Number(element.getAttribute('data-export-max-x'))
  const maxY = Number(element.getAttribute('data-export-max-y'))
  const bounds = { minX, minY, maxX, maxY }
  return isFiniteSvgBounds(bounds) ? bounds : null
}

const svgBoundsIntersectsViewBox = (bounds, viewBox, padding = 0) => (
  bounds.maxX >= viewBox.x - padding &&
  bounds.minX <= viewBox.x + viewBox.width + padding &&
  bounds.maxY >= viewBox.y - padding &&
  bounds.minY <= viewBox.y + viewBox.height + padding
)

const pruneSvgElementForPngTile = (svgElement, viewBox) => {
  const exportElements = Array.from(svgElement.querySelectorAll('[data-export-min-x]'))
  exportElements.forEach(element => {
    const bounds = getSvgExportBoundsFromAttributes(element)
    if (bounds && !svgBoundsIntersectsViewBox(bounds, viewBox, MINDMAP_PNG_TILE_PRUNE_PADDING)) {
      element.remove()
      return
    }
    MINDMAP_SVG_EXPORT_BOUND_ATTRIBUTES.forEach(attributeName => {
      element.removeAttribute(attributeName)
    })
  })
}

const transformSvgTextForPngExport = (svgText, { width, height, viewBox, preserveAspectRatio = 'none' }) => {
  if (typeof DOMParser === 'undefined') {
    return svgText
  }

  const documentNode = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  const svgElement = documentNode.documentElement
  if (documentNode.querySelector('parsererror') || svgElement?.localName?.toLowerCase() !== 'svg') {
    return svgText
  }

  pruneSvgElementForPngTile(svgElement, viewBox)
  svgElement.setAttribute('viewBox', `${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`)
  svgElement.setAttribute('width', String(width))
  svgElement.setAttribute('height', String(height))
  svgElement.setAttribute('preserveAspectRatio', preserveAspectRatio)
  svgElement.style.width = `${width}px`
  svgElement.style.height = `${height}px`
  svgElement.style.overflow = 'hidden'
  svgElement.setAttribute('text-rendering', 'geometricPrecision')
  svgElement.setAttribute('shape-rendering', 'geometricPrecision')
  return new XMLSerializer().serializeToString(svgElement)
}

const resizeSvgTextForPngExport = (svgText, width, height, sourceWidth, sourceHeight) => {
  const viewBox = parseSvgViewBox(svgText, sourceWidth, sourceHeight)
  return transformSvgTextForPngExport(svgText, {
    width,
    height,
    viewBox,
  })
}

const sliceSvgTextForPngExport = (svgText, width, height, viewBox) => transformSvgTextForPngExport(svgText, {
  width,
  height,
  viewBox,
})

const getBoundedPngExportScale = (width, height, maxPixels, maxDimension) => {
  const safeWidth = Math.max(width, 1)
  const safeHeight = Math.max(height, 1)
  const scale = Math.min(
    MINDMAP_PNG_EXPORT_SCALE,
    maxDimension / safeWidth,
    maxDimension / safeHeight,
    Math.sqrt(maxPixels / Math.max(safeWidth * safeHeight, 1))
  )
  return Number.isFinite(scale) && scale > 0 ? scale : 1
}

const getPngExportScale = (width, height) => getBoundedPngExportScale(
  width,
  height,
  MINDMAP_PNG_EXPORT_MAX_PIXELS,
  MINDMAP_PNG_EXPORT_MAX_DIMENSION
)

const getMindmapPngExportPlan = svgText => {
  const svgWidth = parseSvgDimension(svgText, 'width')
  const svgHeight = parseSvgDimension(svgText, 'height')
  const singleScale = getPngExportScale(svgWidth, svgHeight)
  const singleWidth = Math.max(1, Math.ceil(svgWidth * singleScale))
  const singleHeight = Math.max(1, Math.ceil(svgHeight * singleScale))
  const outputScale = getBoundedPngExportScale(
    svgWidth,
    svgHeight,
    MINDMAP_PNG_EXPORT_MAX_STREAM_PIXELS,
    MINDMAP_PNG_EXPORT_MAX_OUTPUT_DIMENSION
  )
  const outputWidth = Math.max(1, Math.ceil(svgWidth * outputScale))
  const outputHeight = Math.max(1, Math.ceil(svgHeight * outputScale))
  const shouldStreamEncode = (
    outputWidth * outputHeight > MINDMAP_PNG_EXPORT_MAX_PIXELS ||
    outputWidth > MINDMAP_PNG_EXPORT_TILE_MAX_WIDTH ||
    outputHeight > MINDMAP_PNG_EXPORT_TILE_MAX_HEIGHT
  )
  return {
    svgWidth,
    svgHeight,
    viewBox: parseSvgViewBox(svgText, svgWidth, svgHeight),
    singleScale,
    singleWidth,
    singleHeight,
    outputScale,
    outputWidth,
    outputHeight,
    shouldStreamEncode,
  }
}

const svgTextToPngBlob = async svgText => {
  const normalizedSvgText = String(svgText || '').trim()
  if (!normalizedSvgText || !/^<svg[\s>]/i.test(normalizedSvgText)) {
    throw new Error('导出的SVG数据无效，无法转为PNG')
  }

  const svgWidth = parseSvgDimension(normalizedSvgText, 'width')
  const svgHeight = parseSvgDimension(normalizedSvgText, 'height')
  const scale = getPngExportScale(svgWidth, svgHeight)
  const canvasWidth = Math.max(1, Math.ceil(svgWidth * scale))
  const canvasHeight = Math.max(1, Math.ceil(svgHeight * scale))
  const resizedSvgText = resizeSvgTextForPngExport(normalizedSvgText, canvasWidth, canvasHeight, svgWidth, svgHeight)
  const image = await loadImageElement(encodeSvgTextAsDataUrl(resizedSvgText))
  const canvas = document.createElement('canvas')
  canvas.width = canvasWidth
  canvas.height = canvasHeight
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('无法创建PNG导出画布')
  }
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(image, 0, 0, canvasWidth, canvasHeight)
  return canvasToPngBlob(canvas)
}

const svgTextToPngTileCanvas = async (svgText, { outputWidth, outputHeight, viewBox }) => {
  const tileSvgText = sliceSvgTextForPngExport(svgText, outputWidth, outputHeight, viewBox)
  const image = await loadImageElement(encodeSvgTextAsDataUrl(tileSvgText))
  const canvas = document.createElement('canvas')
  canvas.width = outputWidth
  canvas.height = outputHeight
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('无法创建PNG导出切片画布')
  }
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(image, 0, 0, outputWidth, outputHeight)
  return canvas
}

const getPngExportTileSize = plan => {
  const tileWidth = Math.max(1, Math.min(plan.outputWidth, MINDMAP_PNG_EXPORT_TILE_MAX_WIDTH))
  const pixelLimitedHeight = Math.floor(MINDMAP_PNG_EXPORT_TILE_MAX_PIXELS / Math.max(tileWidth, 1))
  const tileHeight = Math.max(1, Math.min(plan.outputHeight, MINDMAP_PNG_EXPORT_TILE_MAX_HEIGHT, pixelLimitedHeight))
  return {
    width: tileWidth,
    height: tileHeight,
  }
}

const createPngScanlineBatch = (rows, width) => {
  const sourceRowBytes = width * 4
  const targetRowBytes = sourceRowBytes + 1
  const batch = new Uint8Array(rows.length * targetRowBytes)
  let offset = 0
  rows.forEach(row => {
    batch[offset] = 0
    offset += 1
    batch.set(row, offset)
    offset += sourceRowBytes
  })
  return batch
}

const createPngScanlineBatchFromImageData = (imageData, startRow, rowCount, width) => {
  const sourceRowBytes = width * 4
  const targetRowBytes = sourceRowBytes + 1
  const batch = new Uint8Array(rowCount * targetRowBytes)
  for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
    const targetOffset = rowIndex * targetRowBytes
    const sourceOffset = (startRow + rowIndex) * sourceRowBytes
    batch[targetOffset] = 0
    batch.set(imageData.subarray(sourceOffset, sourceOffset + sourceRowBytes), targetOffset + 1)
  }
  return batch
}

const streamPngTileRows = async (svgText, plan, onScanlines) => {
  const tileSize = getPngExportTileSize(plan)
  const fullWidthSingleTile = plan.outputWidth <= tileSize.width
  for (let tileTop = 0; tileTop < plan.outputHeight; tileTop += tileSize.height) {
    const tileOutputHeight = Math.min(tileSize.height, plan.outputHeight - tileTop)
    const sourceTileY = plan.viewBox.y + (tileTop / plan.outputScale)
    const sourceTileHeight = tileOutputHeight / plan.outputScale
    if (fullWidthSingleTile) {
      const tileCanvas = await svgTextToPngTileCanvas(svgText, {
        outputWidth: plan.outputWidth,
        outputHeight: tileOutputHeight,
        viewBox: {
          x: plan.viewBox.x,
          y: sourceTileY,
          width: plan.viewBox.width,
          height: sourceTileHeight,
        },
      })
      const context = tileCanvas.getContext('2d')
      if (!context) {
        throw new Error('无法读取PNG导出切片像素')
      }
      const tileData = context.getImageData(0, 0, plan.outputWidth, tileOutputHeight).data
      const rowsPerBatch = Math.max(1, Math.floor(MINDMAP_PNG_ENCODER_BATCH_MAX_BYTES / ((plan.outputWidth * 4) + 1)))
      for (let rowIndex = 0; rowIndex < tileOutputHeight; rowIndex += rowsPerBatch) {
        const rowCount = Math.min(rowsPerBatch, tileOutputHeight - rowIndex)
        await onScanlines(createPngScanlineBatchFromImageData(tileData, rowIndex, rowCount, plan.outputWidth), false)
      }
      tileCanvas.width = 1
      tileCanvas.height = 1
      continue
    }

    const rowParts = Array.from({ length: tileOutputHeight }, () => [])

    for (let tileLeft = 0; tileLeft < plan.outputWidth; tileLeft += tileSize.width) {
      const tileOutputWidth = Math.min(tileSize.width, plan.outputWidth - tileLeft)
      const sourceTileX = plan.viewBox.x + (tileLeft / plan.outputScale)
      const sourceTileWidth = tileOutputWidth / plan.outputScale
      const tileCanvas = await svgTextToPngTileCanvas(svgText, {
        outputWidth: tileOutputWidth,
        outputHeight: tileOutputHeight,
        viewBox: {
          x: sourceTileX,
          y: sourceTileY,
          width: sourceTileWidth,
          height: sourceTileHeight,
        },
      })
      const context = tileCanvas.getContext('2d')
      if (!context) {
        throw new Error('无法读取PNG导出切片像素')
      }
      const tileData = context.getImageData(0, 0, tileOutputWidth, tileOutputHeight).data
      const tileRowBytes = tileOutputWidth * 4
      for (let rowIndex = 0; rowIndex < tileOutputHeight; rowIndex += 1) {
        rowParts[rowIndex].push(tileData.slice(rowIndex * tileRowBytes, (rowIndex + 1) * tileRowBytes))
      }
      tileCanvas.width = 1
      tileCanvas.height = 1
    }

    let scanlineRows = []
    let scanlineByteCount = 0
    for (let rowIndex = 0; rowIndex < rowParts.length; rowIndex += 1) {
      const fullRow = rowParts[rowIndex].length === 1 ? rowParts[rowIndex][0] : concatUint8Arrays(rowParts[rowIndex])
      scanlineRows.push(fullRow)
      scanlineByteCount += fullRow.length + 1
      if (scanlineByteCount >= MINDMAP_PNG_ENCODER_BATCH_MAX_BYTES) {
        await onScanlines(createPngScanlineBatch(scanlineRows, plan.outputWidth), false)
        scanlineRows = []
        scanlineByteCount = 0
      }
    }
    if (scanlineRows.length) {
      await onScanlines(createPngScanlineBatch(scanlineRows, plan.outputWidth), false)
    }
  }
}

const svgTextToFullPngBlobByTiles = async (svgText, plan) => {
  const pakoModule = await import('pako')
  const PakoDeflate = pakoModule.Deflate || pakoModule.default?.Deflate
  if (!PakoDeflate) {
    throw new Error('PNG压缩模块未加载')
  }
  const pngParts = [
    new Uint8Array(PNG_BYTE_SIGNATURE),
    createPngChunk('IHDR', createPngIhdrData(plan.outputWidth, plan.outputHeight)),
  ]
  const deflator = new PakoDeflate({ level: 1 })

  deflator.onData = chunk => {
    const bytes = normalizeUint8Array(chunk)
    for (let offset = 0; offset < bytes.length; offset += MINDMAP_PNG_IDAT_CHUNK_SIZE) {
      pngParts.push(createPngChunk('IDAT', bytes.slice(offset, offset + MINDMAP_PNG_IDAT_CHUNK_SIZE)))
    }
  }

  await streamPngTileRows(svgText, plan, async (scanlines, isFinal) => {
    deflator.push(scanlines, isFinal)
    if (deflator.err) {
      throw new Error(deflator.msg || 'PNG图片压缩失败')
    }
    await new Promise(resolve => setTimeout(resolve, 0))
  })
  deflator.push(new Uint8Array(0), true)
  if (deflator.err) {
    throw new Error(deflator.msg || 'PNG图片压缩失败')
  }
  pngParts.push(createPngChunk('IEND'))
  return new Blob(pngParts, { type: 'image/png' })
}

const svgTextToExportPngBlob = async svgText => {
  const plan = getMindmapPngExportPlan(svgText)
  const pngBlob = plan.shouldStreamEncode
    ? await svgTextToFullPngBlobByTiles(svgText, plan)
    : await svgTextToPngBlob(svgText)
  return {
    blob: pngBlob,
    plan,
  }
}

const exportCurrentSvgToPng = async filename => {
  const { svgText } = serializeCurrentMindmapSvg()
  const { blob: pngBlob, plan } = await svgTextToExportPngBlob(svgText)
  await assertBlobIsPng(pngBlob)
  const exportFilename = plan.shouldStreamEncode ? filename.replace(/\.png$/i, '_高清全量.png') : filename
  downloadFile(pngBlob, exportFilename)
  return {
    type: 'png',
    outputWidth: plan.shouldStreamEncode ? plan.outputWidth : plan.singleWidth,
    outputHeight: plan.shouldStreamEncode ? plan.outputHeight : plan.singleHeight,
    scale: plan.shouldStreamEncode ? plan.outputScale : plan.singleScale,
    streamed: plan.shouldStreamEncode,
  }
}

const exportPngViaSvgFallback = async filename => {
  const svgText = await svgPayloadToText(await exportSvgData())
  const { blob: pngBlob } = await svgTextToExportPngBlob(svgText)
  await assertBlobIsPng(pngBlob)
  downloadFile(pngBlob, filename)
}

const shouldFallbackToSvgPngExport = error => {
  const message = String(error?.message || '')
  return (
    message.includes('画布导出PNG失败') ||
    message.includes('导出的PNG数据不是有效图片') ||
    message.includes('导出的PNG数据类型无效') ||
    message.includes('未获取到PNG导出数据')
  )
}

const downloadDataUrl = (dataUrl, filename) => {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const downloadPngPayload = async (payload, filename) => {
  const resolvedPayload = await resolvePngExportPayload(payload)

  if (isBlobValue(resolvedPayload)) {
    await assertBlobIsPng(resolvedPayload)
    const pngBlob = resolvedPayload.type.toLowerCase() === 'image/png'
      ? resolvedPayload
      : new Blob([resolvedPayload], { type: 'image/png' })
    downloadFile(pngBlob, filename)
    return
  }

  if (isArrayBufferValue(resolvedPayload) || isArrayBufferViewValue(resolvedPayload)) {
    const bytes = isArrayBufferValue(resolvedPayload) ? new Uint8Array(resolvedPayload) : arrayBufferViewToUint8Array(resolvedPayload)
    if (!hasPngByteSignature(bytes)) {
      throw new Error('导出的PNG数据不是有效图片')
    }
    downloadFile(new Blob([resolvedPayload], { type: 'image/png' }), filename)
    return
  }

  const rawPayload = String(resolvedPayload || '').trim()
  if (!rawPayload) {
    throw new Error('未获取到PNG导出数据')
  }

  if (rawPayload.startsWith('blob:')) {
    const response = await fetch(rawPayload)
    const blob = await response.blob()
    await assertBlobIsPng(blob)
    const pngBlob = blob.type.toLowerCase() === 'image/png'
      ? blob
      : new Blob([blob], { type: 'image/png' })
    downloadFile(pngBlob, filename)
    return
  }

  downloadDataUrl(normalizePngDataUrl(rawPayload), filename)
}

// 导出为PNG
const exportAsPng = async () => {
  const filename = `手工用例脑图_${Date.now()}.png`
  const loading = ElLoading.service({
    lock: true,
    text: '正在生成完整PNG图片，请稍候...',
    background: 'rgba(255, 255, 255, 0.72)',
  })
  try {
    const exportResult = await exportCurrentSvgToPng(filename)
    if (exportResult?.streamed) {
      const scaleText = exportResult.scale >= 1
        ? '高清全量PNG'
        : '完整PNG'
      ElMessage.success(`已导出${scaleText}：${exportResult.outputWidth} × ${exportResult.outputHeight}`)
    } else {
      ElMessage.success('导出PNG成功！')
    }
    return
  } catch (currentCanvasError) {
    console.error('当前脑图画布导出PNG失败:', currentCanvasError)
  }

  try {
    const exportResult = await minder.exportData('png')
    await downloadPngPayload(exportResult, filename)
    ElMessage.success('导出PNG成功！')
  } catch (error) {
    if (shouldFallbackToSvgPngExport(error)) {
      try {
        await exportPngViaSvgFallback(filename)
        ElMessage.success('导出PNG成功！')
        return
      } catch (fallbackError) {
        console.error('SVG降级导出PNG失败:', fallbackError)
      }
    }
    console.error('导出PNG失败:', error)
    ElMessage.error('导出PNG失败：' + (error.message || '请重试'))
  } finally {
    loading.close()
  }
}

// 导出为SVG
const exportAsSvg = () => {
  try {
    const { svgText } = serializeCurrentMindmapSvg()
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    downloadFile(blob, `手工用例脑图_${Date.now()}.svg`)
    ElMessage.success('导出SVG成功！')
  } catch (error) {
    console.error('导出SVG失败:', error)
    ElMessage.error('导出SVG失败，请重试')
  }
}

// 导出为Markdown
const exportAsMarkdown = () => {
  try {
    const mdData = minder.exportData('markdown')
    const blob = new Blob([mdData.data], { type: 'text/markdown' })
    downloadFile(blob, `手工用例脑图_${Date.now()}.md`)
    ElMessage.success('导出Markdown成功！')
  } catch (error) {
    console.error('导出Markdown失败:', error)
    ElMessage.error('导出Markdown失败，请重试')
  }
}

// 导出为纯文本
const exportAsText = () => {
  try {
    const textData = minder.exportData('text')
    const blob = new Blob([textData.data], { type: 'text/plain' })
    downloadFile(blob, `手工用例脑图_${Date.now()}.txt`)
    ElMessage.success('导出文本成功！')
  } catch (error) {
    console.error('导出文本失败:', error)
    ElMessage.error('导出文本失败，请重试')
  }
}

// 下载文件辅助方法
const downloadFile = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}

// 导入命令处理
const handleImportCommand = (command) => {
  if (!ensureMindmapEditable('当前为只读查看模式，不能导入脑图')) return
  const input = document.createElement('input')
  input.type = 'file'

  switch (command) {
    case 'json':
      input.accept = '.json'
      input.onchange = importJson
      break
    case 'xmind':
      input.accept = '.xmind'
      input.onchange = importXMind
      break
    case 'markdown':
      input.accept = '.md,.markdown'
      input.onchange = importMarkdown
      break
  }

  input.click()
}

// 导入JSON
const importJson = (e) => {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    try {
      const data = annotateModuleMatchesInData(normalizeMindmapData(JSON.parse(event.target.result)))
      resetMindmapOverviewNavigation()
      minderData.value = data
      if (minder) {
        minder.importJson(data)
        scheduleModuleOverviewRefresh(100)
      }
      ElMessage.success('导入JSON成功！')
    } catch (error) {
      console.error('导入失败:', error)
      ElMessage.error('导入失败，文件格式错误！')
    }
  }
  reader.readAsText(file)
}

// 导入Markdown
const importMarkdown = (e) => {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    try {
      resetMindmapOverviewNavigation()
      if (minder) {
        minder.importData('markdown', event.target.result)
      }
      ElMessage.success('导入Markdown成功！')
    } catch (error) {
      console.error('导入失败:', error)
      ElMessage.error('导入失败，请检查文件格式！')
    }
  }
  reader.readAsText(file)
}

// 导入XMind
const importXMind = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  try {
    ElMessage.info('正在解析XMind文件...')
    const importedMindmapData = annotateModuleMatchesInData(
      normalizeMindmapData(await parseXMindFileToMindmapData(file))
    )
    resetMindmapOverviewNavigation()
    minderData.value = importedMindmapData

    const importedName = getMindmapRootText(importedMindmapData)
    if (importedName) {
      mindmapName.value = importedName
    }

    if (minder) {
      minder.importJson(importedMindmapData)
      scheduleModuleOverviewRefresh(100)
    }

    ElMessage.success('导入XMind成功！')
  } catch (error) {
    console.error('导入XMind失败:', error)
    ElMessage.error('导入XMind失败：' + error.message)
  }
}

// 当前正在编辑的输入框
let currentEditInput = null

const createNodeEditTextarea = initialValue => {
  const input = document.createElement('textarea')
  input.value = initialValue
  input.rows = 1
  input.spellcheck = false
  input.className = 'km-edit-input'
  return input
}

const resizeEditInputToContent = input => {
  if (!(input instanceof HTMLTextAreaElement)) return
  const minHeight = Number(input.dataset.minHeight || 32)
  input.style.height = `${minHeight}px`
  input.style.height = `${Math.max(minHeight, input.scrollHeight)}px`
}

const insertEditInputLineBreak = input => {
  const start = input.selectionStart ?? input.value.length
  const end = input.selectionEnd ?? input.value.length
  input.value = `${input.value.slice(0, start)}\n${input.value.slice(end)}`
  const nextCaret = start + 1
  input.setSelectionRange(nextCaret, nextCaret)
  resizeEditInputToContent(input)
}

const handleEditInputKeydown = (event, input, getIsComposing, save, cancel, { saveOnTab = false } = {}) => {
  if (event.key === 'Enter') {
    if (getIsComposing()) return
    event.preventDefault()
    event.stopPropagation()
    if (event.altKey) {
      insertEditInputLineBreak(input)
      return
    }
    save()
    return
  }

  if (event.key === 'Tab' && saveOnTab) {
    event.preventDefault()
    event.stopPropagation()
    save()
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    cancel()
  }
}

// 创建双击编辑的输入框
const createEditInput = (node) => {
  if (!ensureMindmapEditable()) return
  if (!node || !minder) return

  // 如果已经有正在编辑的输入框，先保存并移除
  if (currentEditInput) {
    currentEditInput.saveAndRemove()
  }

  const box = node.getRenderBox()
  const container = document.getElementById('minder-editor')

  // 创建输入框
  const input = createNodeEditTextarea(node.getText())

  Object.assign(input.style, {
    position: 'absolute',
    left: box.x + 'px',
    top: box.y + 'px',
    width: Math.max(box.width + 20, 150) + 'px',
    height: Math.max(box.height, 32) + 'px',
    minHeight: Math.max(box.height, 32) + 'px',
    fontSize: '14px',
    lineHeight: '20px',
    padding: '5px 10px',
    border: '2px solid #409eff',
    borderRadius: '4px',
    outline: 'none',
    resize: 'none',
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    zIndex: '9999',
    backgroundColor: 'white',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)'
  })

  input.dataset.minHeight = String(Math.max(box.height, 32))
  resizeEditInputToContent(input)
  input.addEventListener('input', () => resizeEditInputToContent(input))

  let isSaved = false

  const save = () => {
    if (isSaved) return
    isSaved = true

    const newText = input.value.trim()
    if (newText && newText !== node.getText()) {
      minder.execCommand('text', newText)
      nodeText.value = newText
      markNodeTextEditCommitted()
    }

    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 编辑完成后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  const cancel = () => {
    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 取消后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  // 保存引用和方法
  currentEditInput = {
    element: input,
    saveAndRemove: save,
    cancel: cancel
  }

  container.appendChild(input)
  input.focus()
  input.select()

  let isComposing = false

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true
  })

  input.addEventListener('compositionend', () => {
    isComposing = false
  })

  input.addEventListener('keydown', event => {
    handleEditInputKeydown(event, input, () => isComposing, save, cancel)
  })

  // 失焦时自动保存
  input.addEventListener('blur', (e) => {
    // 延迟一点点，确保焦点已经转移
    setTimeout(() => {
      if (!isSaved) {
        save()
      }
    }, 100)
  })
}

// 编辑节点（用于快捷键调用）
const editNodeInline = (node) => {
  if (!ensureMindmapEditable()) return
  createEditInput(node)
}

// 创建编辑输入框并智能处理输入法
const createEditInputForTypingWithIME = (node, initialChar = '') => {
  if (!ensureMindmapEditable()) return null
  if (!node || !minder) return null

  // 如果已经有正在编辑的输入框，不再创建
  if (currentEditInput) {
    return null
  }

  const box = node.getRenderBox()
  const container = document.getElementById('minder-editor')

  // 创建输入框
  const input = createNodeEditTextarea(initialChar)

  Object.assign(input.style, {
    position: 'absolute',
    left: box.x + 'px',
    top: box.y + 'px',
    width: Math.max(box.width + 20, 150) + 'px',
    height: Math.max(box.height, 32) + 'px',
    minHeight: Math.max(box.height, 32) + 'px',
    fontSize: '14px',
    lineHeight: '20px',
    padding: '5px 10px',
    border: '2px solid #409eff',
    borderRadius: '4px',
    outline: 'none',
    resize: 'none',
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    zIndex: '9999',
    backgroundColor: 'white',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)'
  })

  input.dataset.minHeight = String(Math.max(box.height, 32))
  resizeEditInputToContent(input)
  input.addEventListener('input', () => resizeEditInputToContent(input))

  let isSaved = false
  let isComposing = false

  const save = () => {
    if (isSaved) return
    isSaved = true

    const newText = input.value.trim()
    if (newText) {
      minder.execCommand('text', newText)
      nodeText.value = newText
      markNodeTextEditCommitted()
    }

    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 编辑完成后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  const cancel = () => {
    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 取消后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  // 保存引用和方法
  currentEditInput = {
    element: input,
    saveAndRemove: save,
    cancel: cancel
  }

  container.appendChild(input)
  input.focus()
  // 将光标移到末尾
  input.setSelectionRange(input.value.length, input.value.length)

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true
    // 不清空初始字符，保留它，让输入法自然处理
  })

  input.addEventListener('compositionend', () => {
    isComposing = false
  })

  input.addEventListener('keydown', event => {
    handleEditInputKeydown(event, input, () => isComposing, save, cancel, { saveOnTab: true })
  })

  // 失焦时自动保存
  input.addEventListener('blur', (e) => {
    setTimeout(() => {
      if (!isSaved) {
        save()
      }
    }, 100)
  })

  // 返回输入框元素
  return input
}

// 立即创建编辑输入框用于直接输入（支持输入法）
const createEditInputForTypingImmediate = (node) => {
  if (!ensureMindmapEditable()) return
  if (!node || !minder) return

  // 如果已经有正在编辑的输入框，不再创建
  if (currentEditInput) {
    return
  }

  const box = node.getRenderBox()
  const container = document.getElementById('minder-editor')

  // 创建输入框
  const input = createNodeEditTextarea('')

  Object.assign(input.style, {
    position: 'absolute',
    left: box.x + 'px',
    top: box.y + 'px',
    width: Math.max(box.width + 20, 150) + 'px',
    height: Math.max(box.height, 32) + 'px',
    minHeight: Math.max(box.height, 32) + 'px',
    fontSize: '14px',
    lineHeight: '20px',
    padding: '5px 10px',
    border: '2px solid #409eff',
    borderRadius: '4px',
    outline: 'none',
    resize: 'none',
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    zIndex: '9999',
    backgroundColor: 'white',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)'
  })

  input.dataset.minHeight = String(Math.max(box.height, 32))
  resizeEditInputToContent(input)
  input.addEventListener('input', () => resizeEditInputToContent(input))

  let isSaved = false

  const save = () => {
    if (isSaved) return
    isSaved = true

    const newText = input.value.trim()
    if (newText) {
      minder.execCommand('text', newText)
      nodeText.value = newText
      markNodeTextEditCommitted()
    }

    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 编辑完成后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  const cancel = () => {
    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 取消后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  // 保存引用和方法
  currentEditInput = {
    element: input,
    saveAndRemove: save,
    cancel: cancel
  }

  container.appendChild(input)

  // 立即聚焦，让后续的输入事件能够进入这个输入框
  input.focus()

  let isComposing = false

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true
  })

  input.addEventListener('compositionend', () => {
    isComposing = false
  })

  input.addEventListener('keydown', event => {
    handleEditInputKeydown(event, input, () => isComposing, save, cancel, { saveOnTab: true })
  })

  // 失焦时自动保存
  input.addEventListener('blur', (e) => {
    setTimeout(() => {
      if (!isSaved) {
        save()
      }
    }, 100)
  })
}

// 创建编辑输入框用于直接输入
const createEditInputForTyping = (node, initialChar = '') => {
  if (!ensureMindmapEditable()) return
  if (!node || !minder) return

  // 如果已经有正在编辑的输入框，不再创建
  if (currentEditInput) {
    return
  }

  const box = node.getRenderBox()
  const container = document.getElementById('minder-editor')

  // 创建输入框
  const input = createNodeEditTextarea(initialChar)

  Object.assign(input.style, {
    position: 'absolute',
    left: box.x + 'px',
    top: box.y + 'px',
    width: Math.max(box.width + 20, 150) + 'px',
    height: Math.max(box.height, 32) + 'px',
    minHeight: Math.max(box.height, 32) + 'px',
    fontSize: '14px',
    lineHeight: '20px',
    padding: '5px 10px',
    border: '2px solid #409eff',
    borderRadius: '4px',
    outline: 'none',
    resize: 'none',
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    zIndex: '9999',
    backgroundColor: 'white',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)'
  })

  input.dataset.minHeight = String(Math.max(box.height, 32))
  resizeEditInputToContent(input)
  input.addEventListener('input', () => resizeEditInputToContent(input))

  let isSaved = false

  const save = () => {
    if (isSaved) return
    isSaved = true

    const newText = input.value.trim()
    if (newText) {
      minder.execCommand('text', newText)
      nodeText.value = newText
      markNodeTextEditCommitted()
    }

    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 编辑完成后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  const cancel = () => {
    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 取消后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  // 保存引用和方法
  currentEditInput = {
    element: input,
    saveAndRemove: save,
    cancel: cancel
  }

  container.appendChild(input)
  input.focus()
  // 将光标移到末尾
  input.setSelectionRange(input.value.length, input.value.length)

  let isComposing = false

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true
  })

  input.addEventListener('compositionend', () => {
    isComposing = false
  })

  input.addEventListener('keydown', event => {
    handleEditInputKeydown(event, input, () => isComposing, save, cancel, { saveOnTab: true })
  })

  // 失焦时自动保存
  input.addEventListener('blur', (e) => {
    setTimeout(() => {
      if (!isSaved) {
        save()
      }
    }, 100)
  })
}

// 创建编辑输入框并设置初始字符（用于直接输入编辑）
const createEditInputWithInitialChar = (node, initialChar) => {
  if (!ensureMindmapEditable()) return
  if (!node || !minder) return

  // 如果已经有正在编辑的输入框，先保存并移除
  if (currentEditInput) {
    currentEditInput.saveAndRemove()
  }

  const box = node.getRenderBox()
  const container = document.getElementById('minder-editor')

  // 创建输入框
  const input = createNodeEditTextarea(initialChar)

  Object.assign(input.style, {
    position: 'absolute',
    left: box.x + 'px',
    top: box.y + 'px',
    width: Math.max(box.width + 20, 150) + 'px',
    height: Math.max(box.height, 32) + 'px',
    minHeight: Math.max(box.height, 32) + 'px',
    fontSize: '14px',
    lineHeight: '20px',
    padding: '5px 10px',
    border: '2px solid #409eff',
    borderRadius: '4px',
    outline: 'none',
    resize: 'none',
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    zIndex: '9999',
    backgroundColor: 'white',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)'
  })

  input.dataset.minHeight = String(Math.max(box.height, 32))
  resizeEditInputToContent(input)
  input.addEventListener('input', () => resizeEditInputToContent(input))

  let isSaved = false

  const save = () => {
    if (isSaved) return
    isSaved = true

    const newText = input.value.trim()
    if (newText) {
      minder.execCommand('text', newText)
      nodeText.value = newText
      markNodeTextEditCommitted()
    }

    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 编辑完成后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  const cancel = () => {
    if (input.parentNode) {
      input.remove()
    }
    currentEditInput = null

    // 取消后重新聚焦到编辑器
    setTimeout(() => {
      const editorElement = document.getElementById('minder-editor')
      if (editorElement) {
        editorElement.focus()
      }
    }, 50)
  }

  // 保存引用和方法
  currentEditInput = {
    element: input,
    saveAndRemove: save,
    cancel: cancel
  }

  container.appendChild(input)
  input.focus()
  // 将光标移到末尾
  input.setSelectionRange(input.value.length, input.value.length)

  let isComposing = false

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true
  })

  input.addEventListener('compositionend', () => {
    isComposing = false
  })

  input.addEventListener('keydown', event => {
    handleEditInputKeydown(event, input, () => isComposing, save, cancel, { saveOnTab: true })
  })

  // 失焦时自动保存
  input.addEventListener('blur', (e) => {
    setTimeout(() => {
      if (!isSaved) {
        save()
      }
    }, 100)
  })
}

// 更新历史状态（撤销/重做）
const updateHistoryStateLegacy = () => {
  if (!minder) return
  try {
    const history = minder.getHistory()
    if (history) {
      canUndo.value = history.hasUndo()
      canRedo.value = history.hasRedo()
    }
  } catch (error) {
    console.log('History not available')
  }
}

// 更新剪贴板状态
const updateClipboardState = () => {
  hasClipboard.value = Array.isArray(mindmapClipboardNodes) && mindmapClipboardNodes.length > 0
}

const getNodeDisplayText = node => String(node?.getText?.() || getNodeData(node).text || '').trim()

const getNodePath = node => {
  const path = []
  let current = node
  const seen = new Set()

  while (current && !seen.has(current)) {
    seen.add(current)
    path.unshift(current)
    current = current.getParent?.() || current.parent || null
  }

  return path
}

const buildSelfTestDetailDefaults = node => {
  const nodePath = getNodePath(node)
  const moduleParts = []
  let lastModuleIndex = -1

  nodePath.slice(0, -1).forEach((currentNode, index) => {
    const data = getNodeData(currentNode)
    const text = getNodeDisplayText(currentNode)
    if (['module', 'page', 'function'].includes(data.nodeType) && text) {
      moduleParts.push(text)
      lastModuleIndex = index
    }
  })

  const lines = []
  const modulePath = moduleParts.join(' / ')
  if (modulePath) {
    lines.push(`1. ${modulePath}`)
  }

  const startIndex = lastModuleIndex >= 0 ? lastModuleIndex + 1 : 0
  const betweenNodes = nodePath.slice(startIndex, -1)
    .map(currentNode => getNodeDisplayText(currentNode))
    .filter(Boolean)

  const nextNumber = lines.length + 1
  betweenNodes.forEach((text, index) => {
    lines.push(`${nextNumber + index}. ${text}`)
  })

  return {
    preconditions: lines.join('\n'),
    expectedResult: getNodeDisplayText(node)
  }
}

const applySelfTestDetailDefaultsToNode = node => {
  if (!node || getNodeData(node).nodeType !== 'testpoint') return

  const defaults = buildSelfTestDetailDefaults(node)
  setNodeDataSilently(node, 'preCondition', defaults.preconditions)
  setNodeDataSilently(node, 'preconditions', defaults.preconditions)
  setNodeDataSilently(node, 'expect', defaults.expectedResult)
  setNodeDataSilently(node, 'expected_result', defaults.expectedResult)
}

// 加载节点数据到详情面板
const loadNodeDetails = (node) => {
  if (!node) return

  const data = getNodeData(node)

  // 基本信息
  nodeText.value = node.getText()
  currentNodeType.value = data.nodeType || ''
  currentPriority.value = data.priority !== undefined ? data.priority : null
  currentStatus.value = data.status || ''
  currentTags.value = data.tags || []

  const selfTestDefaults = data.nodeType === 'testpoint'
    ? buildSelfTestDetailDefaults(node)
    : null
  const reviewOpinion = String(data.reviewOpinion || '').trim()
  const reviewDefaults = getReviewFormDefaults()
  const reviewTime = normalizeReviewTimeValue(data.reviewTime)
  const reviewerIdValue = data.reviewerId ?? reviewDefaults.reviewerId
  const reviewerIdNumber = reviewerIdValue === null || reviewerIdValue === undefined || reviewerIdValue === ''
    ? NaN
    : Number(reviewerIdValue)
  const reviewerId = Number.isFinite(reviewerIdNumber) ? reviewerIdNumber : reviewDefaults.reviewerId
  const reviewerFallbackName = String(reviewerId) === String(reviewDefaults.reviewerId) ? reviewDefaults.reviewerName : ''
  const reviewerName = String(data.reviewerName || '').trim() || resolveReviewerName(reviewerId, reviewerFallbackName)

  // 详细信息
  nodeData.value = {
    caseId: data.caseId || '',
    preCondition: selfTestDefaults
      ? selfTestDefaults.preconditions
      : (data.preCondition || data.preconditions || ''),
    steps: data.steps || '',
    expect: selfTestDefaults
      ? selfTestDefaults.expectedResult
      : (data.expect || data.expected_result || ''),
    remark: data.remark || '',
    reviewOpinion,
    reviewTime: data.nodeType === 'testpoint'
      ? (reviewOpinion ? (reviewTime || reviewDefaults.reviewTime) : reviewDefaults.reviewTime)
      : '',
    reviewerId: data.nodeType === 'testpoint'
      ? (reviewOpinion ? reviewerId : reviewDefaults.reviewerId)
      : null,
    reviewerName: data.nodeType === 'testpoint'
      ? (reviewOpinion ? reviewerName : reviewDefaults.reviewerName)
      : '',
    reviewStatus: data.nodeType === 'testpoint'
      ? (reviewOpinion ? (data.reviewStatus || '未处理') : '')
      : '',
    note: data.note || '',
    requirementFacts: data.requirementFacts || data.requirement_facts || []
  }
}

// 初始化KityMinder
// 加载脑图数据
const loadMindmap = async (id) => {
  console.log('loadMindmap 被调用, ID:', id)
  resetMindmapOverviewNavigation()
  try {
    const response = await api.get(`/testcases/manual-mindmaps/${id}/`)
    console.log('loadMindmap 成功获取数据:', response.data)
    currentMindmapId.value = response.data.id
    currentProjectId.value = response.data.project?.id || response.data.project_id || getContextQueryValue('project_id') || ''
    currentVersionId.value = response.data.version?.id || response.data.version_id || getContextQueryValue('version_id') || ''
    currentCategoryId.value = response.data.category || response.data.category_id || getContextQueryValue('category_id') || ''
    currentRequirementKey.value = response.data.requirement_key || ''
    currentResponsibilityGroup.value = response.data.responsibility_group || ''
    currentFrontendDeveloper.value = resolveUserDisplayName(response.data.frontend_developer, '')
    currentBackendDeveloper.value = resolveUserDisplayName(response.data.backend_developer, '')
    mindmapDescription.value = response.data.description
    loadedMindmapScope.value = response.data.mindmap_scope || currentMindmapScope.value
    emit('loaded', response.data)
    await loadManualCategoryMatchIndex(currentProjectId.value)
    const normalizedMindmapData = annotateModuleMatchesInData(normalizeMindmapData(response.data.mindmap_data))
    minderData.value = normalizedMindmapData
    lastPersistedMindmapDescendantCount = countMindmapDescendants(normalizedMindmapData)
    mindmapName.value = String(normalizedMindmapData?.root?.data?.text || response.data.name || '').trim() || '新建脑图'
    console.log('currentMindmapId 已设置为:', currentMindmapId.value)
    ElMessage.success('加载成功')
  } catch (error) {
    console.error('loadMindmap 失败:', error)
    ElMessage.error('加载失败：' + (error.response?.data?.detail || error.message))
  }
}

// 保存事件监听器引用，用于清理
let keyboardHandler = null
let editorElementRef = null

const isEditableKeyboardTarget = target => {
  if (!(target instanceof Element)) {
    return false
  }
  if (target.closest('input, textarea, select, [contenteditable="true"], [contenteditable=""]')) {
    return true
  }
  return Boolean(target.isContentEditable)
}

const isMindmapKeyboardScope = event => {
  const editorElement = getMinderEditorElement()
  if (!editorElement) {
    return false
  }

  const target = event.target
  if (target instanceof Element && (target === editorElement || editorElement.contains(target))) {
    return true
  }

  const activeElement = document.activeElement
  return activeElement === editorElement || Boolean(activeElement && editorElement.contains(activeElement))
}

const setupMinderResizeObserver = () => {
  if (minderResizeObserver || typeof ResizeObserver === 'undefined') {
    return
  }

  const editorElement = getMinderEditorElement()
  if (!editorElement) {
    return
  }

  minderResizeObserver = new ResizeObserver(entries => {
    const entry = entries[0]
    const width = entry?.contentRect?.width || 0
    const height = entry?.contentRect?.height || 0
    if (width > 80 && height > 80) {
      scheduleViewportSync(80)
    }
  })
  minderResizeObserver.observe(editorElement)
}

const setupCanvasPanning = () => {
  const editorElement = getMinderEditorElement()
  if (!editorElement) return

  editorElementRef = editorElement

  canvasPanMouseDownHandler = event => {
    if (!minder) {
      return
    }

    if (event.button !== 0 || !isBlankCanvasTarget(event.target)) {
      return
    }

    if (currentEditInput) {
      editBlankCanvasMouseDownState = {
        x: event.clientX,
        y: event.clientY,
        moved: false,
      }
      stopMindmapMouseEvent(event)
      return
    }

    isCanvasPanning = true
    lastPanClientX = event.clientX
    lastPanClientY = event.clientY
    previousBodyUserSelect = document.body.style.userSelect
    previousBodyCursor = document.body.style.cursor
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'grabbing'
    editorElement.classList.add('is-panning')

    stopMindmapMouseEvent(event)
  }

  canvasPanMouseMoveHandler = event => {
    if (editBlankCanvasMouseDownState) {
      const deltaX = event.clientX - editBlankCanvasMouseDownState.x
      const deltaY = event.clientY - editBlankCanvasMouseDownState.y
      if (Math.hypot(deltaX, deltaY) > EDIT_BLANK_CANVAS_CLICK_TOLERANCE) {
        editBlankCanvasMouseDownState.moved = true
      }
      stopMindmapMouseEvent(event)
      return
    }

    if (!isCanvasPanning) {
      return
    }

    const deltaX = event.clientX - lastPanClientX
    const deltaY = event.clientY - lastPanClientY

    if (!deltaX && !deltaY) {
      return
    }

    lastPanClientX = event.clientX
    lastPanClientY = event.clientY
    moveCanvasViewBy(deltaX, deltaY)
    event.preventDefault()
  }

  canvasPanMouseUpHandler = event => {
    if (event?.type === 'blur') {
      editBlankCanvasMouseDownState = null
      stopCanvasPanning(true)
      return
    }

    if (editBlankCanvasMouseDownState) {
      const shouldSaveEdit = !editBlankCanvasMouseDownState.moved && currentEditInput
      editBlankCanvasMouseDownState = null
      if (shouldSaveEdit) {
        currentEditInput.saveAndRemove()
      }
      stopMindmapMouseEvent(event)
      return
    }

    stopCanvasPanning(true)
  }

  editorElement.addEventListener('mousedown', canvasPanMouseDownHandler, true)
  window.addEventListener('mousemove', canvasPanMouseMoveHandler, { passive: false })
  window.addEventListener('mouseup', canvasPanMouseUpHandler)
  window.addEventListener('blur', canvasPanMouseUpHandler)
}

const setupMindmapContextMenu = () => {
  const editorElement = getMinderEditorElement()
  if (!editorElement) return

  editorElementRef = editorElement

  contextMenuHandler = event => {
    if (!minder || currentEditInput) {
      return
    }

    const node = getMinderNodeFromEventTarget(event.target)
    if (!node) {
      hideMindmapContextMenu()
      return
    }

    event.preventDefault()
    event.stopPropagation()
    contextMenuNode = node
    batchOperationMode.value = BATCH_OPERATION_MODE.selection
    minder.select(node, true)
    hasSelection.value = true
    isRootSelected.value = node === minder.getRoot()
    loadNodeDetails(node)

    const containerBox = editorElement.getBoundingClientRect()
    const menuWidth = 176
    const menuHeight = 244
    const x = Math.min(Math.max(event.clientX - containerBox.left, 8), Math.max(containerBox.width - menuWidth - 8, 8))
    const y = Math.min(Math.max(event.clientY - containerBox.top, 8), Math.max(containerBox.height - menuHeight - 8, 8))
    mindmapContextMenu.value = {
      visible: true,
      x,
      y,
      openLeft: event.clientX - containerBox.left > containerBox.width * 0.58,
      sourceRequirementClarificationKey: getNodeData(node).sourceRequirementClarificationKey ||
        getNodeData(node).source_requirement_clarification_key ||
        '',
    }
  }

  contextMenuGlobalClickHandler = event => {
    const target = event.target
    if (target instanceof Element && target.closest('.mindmap-context-menu')) {
      return
    }
    hideMindmapContextMenu()
  }

  contextMenuKeydownHandler = event => {
    if (event.key === 'Escape') {
      hideMindmapContextMenu()
    }
  }

  editorElement.addEventListener('contextmenu', contextMenuHandler, true)
  window.addEventListener('click', contextMenuGlobalClickHandler, true)
  window.addEventListener('keydown', contextMenuKeydownHandler)
}

// 手动设置键盘快捷键
const setupKeyboardShortcuts = () => {
  const editorElement = getMinderEditorElement()
  if (!editorElement) return

  editorElementRef = editorElement

  keyboardHandler = (e) => {
    if (!isMindmapKeyboardScope(e) || currentEditInput) {
      return
    }

    if (isEditableKeyboardTarget(e.target) && !(e.target instanceof Element && editorElement.contains(e.target))) {
      return
    }

    // ========== 最高优先级：系统级按键，完全不拦截 ==========
    // 所有修饰键（Shift, Ctrl, Alt等）单独按下时，必须直接传递给系统
    const isModifierKey = e.key === 'Shift' || e.key === 'Control' || e.key === 'Alt' || e.key === 'Meta' || e.key === 'CapsLock'
    if (isModifierKey) {
      return
    }

    // 所有Ctrl、Shift组合键，不拦截，让KityMinder自己处理
    const normalizedKey = String(e.key || '').toLowerCase()
    const isUndoShortcut = (e.ctrlKey || e.metaKey) && !e.altKey && normalizedKey === 'z' && !e.shiftKey
    const isRedoShortcut = (e.ctrlKey || e.metaKey) && !e.altKey &&
      (normalizedKey === 'y' || (normalizedKey === 'z' && e.shiftKey))

    if (isUndoShortcut) {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      handleUndo()
      return
    }

    if (isRedoShortcut) {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      handleRedo()
      return
    }

    const isClipboardShortcut = (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey
    if (!currentEditInput && isClipboardShortcut && normalizedKey === 'c') {
      e.preventDefault()
      e.stopPropagation()
      copySelectedMindmapNodes()
      return
    }

    if (!currentEditInput && isClipboardShortcut && normalizedKey === 'v') {
      e.preventDefault()
      e.stopPropagation()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      void pasteMindmapClipboard()
      return
    }

    if (!currentEditInput && isClipboardShortcut && normalizedKey === 'x') {
      e.preventDefault()
      e.stopPropagation()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      cutSelectedMindmapNodes()
      return
    }

    if (e.ctrlKey || e.shiftKey) {
      return
    }

    // ========== 应用逻辑检查 ==========
    if (!minder) return

    const selectedNode = minder.getSelectedNode()
    if (!selectedNode) return

    const isRoot = selectedNode === minder.getRoot()

    // 方向键导航（仅在没有编辑框时）
    if (!currentEditInput && e.key === 'ArrowUp') {
      e.preventDefault()
      // 选中前一个兄弟节点
      const parent = selectedNode.parent
      if (parent) {
        const siblings = parent.children
        const currentIndex = siblings.indexOf(selectedNode)
        if (currentIndex > 0) {
          minder.select(siblings[currentIndex - 1], true)
        }
      }
      return
    }

    if (!currentEditInput && e.key === 'ArrowDown') {
      e.preventDefault()
      // 选中后一个兄弟节点
      const parent = selectedNode.parent
      if (parent) {
        const siblings = parent.children
        const currentIndex = siblings.indexOf(selectedNode)
        if (currentIndex < siblings.length - 1) {
          minder.select(siblings[currentIndex + 1], true)
        }
      }
      return
    }

    if (!currentEditInput && e.key === 'ArrowLeft') {
      e.preventDefault()
      // 选中父节点
      const parent = selectedNode.parent
      if (parent && parent !== minder.getRoot().parent) {
        minder.select(parent, true)
      }
      return
    }

    if (!currentEditInput && e.key === 'ArrowRight') {
      e.preventDefault()
      // 选中第一个子节点
      const children = selectedNode.children
      if (children && children.length > 0) {
        minder.select(children[0], true)
      }
      return
    }

    // Tab - 添加子节点（仅在没有编辑框时）
    if (!currentEditInput && e.key === 'Tab') {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      minder.execCommand('AppendChildNode')
      return
    }

    // Enter - 添加同级节点（仅在没有编辑框时）
    if (!currentEditInput && e.key === 'Enter') {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      if (!isRoot) {
        minder.execCommand('AppendSiblingNode')
      }
      return
    }

    // Delete/Backspace - 删除节点（仅在没有编辑框时）
    if ((e.key === 'Delete' || e.key === 'Backspace') && !isRoot && !currentEditInput) {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      minder.execCommand('RemoveNode')
      return
    }

    // F2 - 编辑节点（仅在没有编辑框时）
    if (!currentEditInput && e.key === 'F2') {
      e.preventDefault()
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      editNodeInline(selectedNode)
      return
    }

    // Space - 展开/折叠（仅在没有编辑框时）
    if (e.key === ' ' && !currentEditInput) {
      e.preventDefault()
      const isExpanded = selectedNode.isExpanded()
      if (isExpanded) {
        minder.execCommand('Collapse')
      } else {
        minder.execCommand('Expand')
      }
      return
    }

    // 直接输入字符编辑节点（F2或双击也可以编辑）
    if (!currentEditInput) {
      // 排除Alt/Meta组合键（Ctrl/Shift已在前面统一处理）
      if (!e.altKey && !e.metaKey) {
        // 普通可打印字符（排除特殊键）
        const isCharKey = (e.key.length === 1 || e.key === 'Process') &&
            e.key !== ' '  // 空格键用于展开/折叠

        if (isCharKey) {
          // 直接创建编辑框，让用户输入
          e.preventDefault()
          if (isReadonlyMindmap.value) {
            ElMessage.warning(READONLY_MINDMAP_MESSAGE)
            return
          }
          editNodeInline(selectedNode)
          return
        }
      }
    }
  }

  // 添加键盘事件监听器
  window.addEventListener('keydown', keyboardHandler, true)

  console.log('键盘快捷键已设置')
}

// 清理事件监听器
const cleanupEventListeners = () => {
  if (minderResizeObserver) {
    minderResizeObserver.disconnect()
    minderResizeObserver = null
  }

  // 清理键盘事件监听器
  if (keyboardHandler) {
    window.removeEventListener('keydown', keyboardHandler, true)
    console.log('已移除键盘事件监听器')
  }

  // 清空所有引用
  if (editorElementRef && canvasPanMouseDownHandler) {
    editorElementRef.removeEventListener('mousedown', canvasPanMouseDownHandler, true)
  }

  if (canvasPanMouseMoveHandler) {
    window.removeEventListener('mousemove', canvasPanMouseMoveHandler)
  }

  if (canvasPanMouseUpHandler) {
    window.removeEventListener('mouseup', canvasPanMouseUpHandler)
    window.removeEventListener('blur', canvasPanMouseUpHandler)
  }

  if (editorElementRef && contextMenuHandler) {
    editorElementRef.removeEventListener('contextmenu', contextMenuHandler, true)
  }

  if (contextMenuGlobalClickHandler) {
    window.removeEventListener('click', contextMenuGlobalClickHandler, true)
  }

  if (contextMenuKeydownHandler) {
    window.removeEventListener('keydown', contextMenuKeydownHandler)
  }

  stopCanvasPanning(false)
  editBlankCanvasMouseDownState = null
  hideMindmapContextMenu()

  keyboardHandler = null
  canvasPanMouseDownHandler = null
  canvasPanMouseMoveHandler = null
  canvasPanMouseUpHandler = null
  contextMenuHandler = null
  contextMenuGlobalClickHandler = null
  contextMenuKeydownHandler = null
  editorElementRef = null

  console.log('所有事件监听器已清理')
}

let pendingLocateParams = null

const normalizeNodePath = (path) => {
  return String(path || '')
    .split('/')
    .map(part => part.trim())
    .filter(Boolean)
    .join('/')
}

const buildNodePath = (node) => {
  const pathParts = []
  let current = node

  while (current) {
    const text = String(current.getText?.() || '').trim()
    if (text) {
      pathParts.unshift(text)
    }
    current = current.getParent?.()
  }

  return normalizeNodePath(pathParts.join('/'))
}

const expandNodeAncestors = (node) => {
  const ancestors = []
  let parent = node?.getParent?.()

  while (parent) {
    ancestors.unshift(parent)
    parent = parent.getParent?.()
  }

  ancestors.forEach((ancestor) => {
    if (typeof ancestor.isExpanded === 'function' && !ancestor.isExpanded()) {
      if (typeof ancestor.expand === 'function') {
        ancestor.expand()
      } else {
        minder.select(ancestor, true)
        minder.execCommand('Expand')
      }
    }
  })
}

const runPendingLocate = () => {
  if (!pendingLocateParams) {
    return
  }

  const located = locateAndSelectNode(pendingLocateParams)
  if (located) {
    pendingLocateParams = null
  }
}

// 定位并选中指定节点（通过文本和路径）
const locateAndSelectNode = (searchParams) => {
  if (!minder) {
    console.error('脑图实例未初始化')
    return false
  }

  console.log('========== 开始定位节点 ==========')
  console.log('搜索参数:', searchParams)

  const targetText = String(searchParams?.text || '').trim()
  const targetPath = normalizeNodePath(searchParams?.path)

  if (!targetText && !targetPath) {
    return false
  }

  // 收集所有节点信息用于调试
  const allNodes = []
  const candidates = []

  // 构建节点路径
  const getNodePath = (node) => buildNodePath(node)

  // 遍历所有节点查找目标节点
  const findNode = (node, depth = 0) => {
    const nodeText = String(node.getText?.() || '').trim()
    const nodePath = getNodePath(node)

    // 收集节点信息
    const nodeInfo = {
      depth: depth,
      text: nodeText,
      path: nodePath,
      match: false,
      matchType: '',
      score: 0
    }

    // 匹配策略：
    // 1. 优先级最高：路径和文本都匹配
    // 2. 次优先级：只有路径匹配
    // 3. 最低优先级：只有文本匹配
    const pathMatched = Boolean(targetPath) && nodePath === targetPath
    const textMatched = Boolean(targetText) && nodeText === targetText

    if (pathMatched && textMatched) {
      nodeInfo.match = true
      nodeInfo.matchType = 'path+text'
      nodeInfo.score = 3
    } else if (pathMatched) {
      nodeInfo.match = true
      nodeInfo.matchType = 'path'
      nodeInfo.score = 2
    } else if (textMatched) {
      nodeInfo.match = true
      nodeInfo.matchType = 'text'
      nodeInfo.score = 1
    }

    allNodes.push(nodeInfo)

    if (depth < 3 || nodeInfo.match) {
      console.log(`[深度${depth}] ${nodeInfo.match ? '✅' : '  '} ${nodeText}`, nodeInfo)
    }

    if (nodeInfo.match) {
      candidates.push({
        node,
        depth,
        score: nodeInfo.score,
        matchType: nodeInfo.matchType
      })
    }

    // 递归查找子节点
    const children = node.getChildren() || []
    for (let i = 0; i < children.length; i++) {
      findNode(children[i], depth + 1)
    }
  }

  // 从根节点开始查找
  const root = minder.getRoot()
  console.log('根节点:', root.getText())

  findNode(root)

  candidates.sort((left, right) => {
    if (right.score !== left.score) {
      return right.score - left.score
    }
    return right.depth - left.depth
  })

  const result = candidates[0]

  console.log('========== 查找结果 ==========')
  console.log('检查了', allNodes.length, '个节点')

  if (result) {
    const targetNode = result.node
    console.log('✅ 找到目标节点:', targetNode.getText())
    console.log('匹配方式:', result.matchType)

    // 选中节点
    expandNodeAncestors(targetNode)
    minder.select(targetNode, true)
    console.log('节点已选中')

    // 展开到该节点的所有父节点
    let parent = targetNode.getParent()
    while (parent) {
      if (parent.isExpanded && !parent.isExpanded()) {
        minder.execCommand('Expand', parent)
        console.log('展开父节点:', parent.getText())
      }
      parent = parent.getParent()
    }

    // 居中显示该节点
    setTimeout(() => {
      try {
        if (!centerMinderNodeInWorkspace(targetNode, 600)) {
          minder.execCommand('camera', targetNode, 600)
        }
      } catch (error) {
        console.error('节点居中失败:', error)
        minder.execCommand('Camera')
      }
      focusEditor()
      console.log('节点已居中显示')
      ElMessage.success('已定位到目标节点: ' + targetNode.getText())
    }, 120)
    return true
  } else {
    console.error('❌ 未找到匹配的节点')
    console.error('搜索条件:', { targetText, targetPath })
    console.error('所有节点列表:', allNodes.map(n => ({ text: n.text, path: n.path })))
    return false
  }
  console.log('========== 定位完成 ==========')
}

const handleTesthubLocateNodeEvent = event => {
  const detail = event?.detail && typeof event.detail === 'object' ? event.detail : {}
  const located = locateAndSelectNode({
    text: detail.text || '',
    path: detail.path || '',
  })
  if (detail.showDetailPanel !== false) {
    showDetailPanel.value = true
  }
  if (detail.activeTab === 'facts') {
    detailPanelActiveTab.value = 'facts'
  } else if (detail.activeTab === 'node') {
    detailPanelActiveTab.value = 'node'
  }
  detail.located = located
  if (event && typeof event.preventDefault === 'function') {
    event.preventDefault()
  }
  return located
}

const initMinder = () => {
  if (!window.kityminder) {
    ElMessage.error('KityMinder库未加载，请刷新页面')
    return
  }

  try {
    const editorElement = getMinderEditorElement()

    // 创建Minder实例
    minder = new window.kityminder.Minder({
      renderTo: '#minder-editor'
    })

    // 导入数据
    minderData.value = annotateModuleMatchesInData(normalizeMindmapData(minderData.value))
    minder.importJson(minderData.value)

    // 设置主题和模板
    minder.execCommand('Theme', currentTheme.value)
    minder.execCommand('Template', 'right')

    // 启用编辑
    minder.enable()

    // 选中根节点
    const root = minder.getRoot()
    minder.select(root, true)

    // 居中显示
    scheduleViewportSync(80)

    // 不使用 KityMinder 的 Receiver，因为它会全局拦截键盘事件
    // 包括输入法切换键，导致在整个应用中都无法切换输入法
    // 我们使用自己的键盘事件处理，只监听特定元素，并且正确放行系统级按键
    console.log('使用自定义键盘事件监听（放行输入法切换键）')
    setupKeyboardShortcuts()
    setupCanvasPanning()
    setupMindmapContextMenu()
    setupMinderResizeObserver()

    // 聚焦到编辑器容器以确保快捷键能够工作
    setTimeout(() => {
      if (editorElement) {
        editorElement.focus()
      }
    }, 200)

    const activeMinder = minder
    const isActiveMinder = () => minder && minder === activeMinder

    // 监听选中事件
    activeMinder.on('selectionchange', function() {
      if (!isActiveMinder()) {
        return
      }
      // 如果有正在编辑的输入框，先保存
      if (currentEditInput) {
        currentEditInput.saveAndRemove()
      }

      const node = activeMinder.getSelectedNode()
      if (node) {
        hasSelection.value = true
        isRootSelected.value = (node === activeMinder.getRoot())
        loadNodeDetails(node)
        syncMindmapOverviewNavigationWithSelectedNode(node)
        if (batchOperationMode.value !== BATCH_OPERATION_MODE.selection) {
          syncToolbarStateForScope()
        }
      } else {
        resetMindmapOverviewNavigation()
        hasSelection.value = false
        isRootSelected.value = false
        if (batchOperationMode.value === BATCH_OPERATION_MODE.selectedLeafDescendants) {
          batchOperationMode.value = BATCH_OPERATION_MODE.selection
        }
        nodeText.value = ''
        currentNodeType.value = ''
        currentPriority.value = null
        currentStatus.value = ''
        currentTags.value = []
        nodeData.value = {
          caseId: '',
          preCondition: '',
          steps: '',
          expect: '',
          remark: '',
          reviewOpinion: '',
          reviewTime: '',
          reviewerId: null,
          reviewerName: '',
          reviewStatus: '',
          note: '',
          requirementFacts: []
        }
      }
    })

    // 监听内容变化
    activeMinder.on('contentchange', function() {
      if (!isActiveMinder()) {
        return
      }
      if (isReadonlyMindmap.value) {
        return
      }
      minderData.value = normalizeMindmapData(activeMinder.exportJson())
      scheduleModuleOverviewRefresh()
      syncMindmapNameWithRootNode()
      pushHistorySnapshot()
      // 更新撤销/重做状态
      updateHistoryState()
      scheduleMindmapAutoSave()
    })

    // 监听布局完成，更新所有节点样式和统计数
    activeMinder.on('layoutallfinish', function() {
      if (!isActiveMinder()) {
        return
      }
      updateAllNodeStyles()
      scheduleModuleOverviewRefresh(80)
      // 延迟更新统计数
      setTimeout(() => {
        if (!isActiveMinder()) {
          return
        }
        updateAllNodeCounts()
      }, 100)
      setTimeout(() => {
        if (!isActiveMinder()) {
          return
        }
        runPendingLocate()
      }, 120)
    })

    // 监听双击编辑
    activeMinder.on('dblclick', function() {
      if (!isActiveMinder()) {
        return
      }
      if (isReadonlyMindmap.value) {
        ElMessage.warning(READONLY_MINDMAP_MESSAGE)
        return
      }
      const node = activeMinder.getSelectedNode()
      if (node) {
        createEditInput(node)
      }
    })

    // 监听剪贴板变化
    activeMinder.on('clipboardchanged', function() {
      if (!isActiveMinder()) {
        return
      }
      updateClipboardState()
    })

    // 初始状态更新
    resetHistorySnapshots()
    updateHistoryState()
    updateClipboardState()

    ElMessage.success('脑图加载成功！双击节点编辑，右侧面板设置属性')
  } catch (error) {
    console.error('初始化失败:', error)
    ElMessage.error('初始化失败: ' + error.message)
  }
}

onMounted(async () => {
  console.log('ManualTestCaseEditor onMounted, route.query:', route.query)
  await loadReviewerOptions()

  window.addEventListener('resize', handleWindowResize)
  editorRootRef.value?.addEventListener('testhub-locate-node', handleTesthubLocateNodeEvent)

  // 保存节点定位参数
  const targetNodeText = route.query.node_text
  const targetNodePath = route.query.node_path
  pendingLocateParams = (targetNodeText || targetNodePath)
    ? { text: targetNodeText, path: targetNodePath }
    : null

  console.log('节点定位参数:', { targetNodeText, targetNodePath })

  // 如果URL中有ID参数，先设置ID并加载脑图数据
  const initialMindmapId = props.initialMindmapId || route.query.id
  if (initialMindmapId) {
    console.log('检测到 route.query.id:', route.query.id)
    // 先设置ID，确保即使加载失败也能正确更新而不是创建新脑图
    currentMindmapId.value = parseInt(initialMindmapId)
    console.log('currentMindmapId 预先设置为:', currentMindmapId.value)
    await loadMindmap(initialMindmapId)
    console.log('loadMindmap 完成，当前脑图数据:', minderData.value)
  } else {
    console.log('未检测到 route.query.id，这是一个新脑图')
    currentProjectId.value = getContextQueryValue('project_id') || getContextQueryValue('project') || props.initialProjectId || ''
    await loadManualCategoryMatchIndex(currentProjectId.value)
    annotateModuleMatchesInData(minderData.value)
  }

  // 延迟初始化Minder以确保DOM已渲染并且嵌入工作区已有真实尺寸。
  scheduleMinderInitialization(100)
})

onUnmounted(() => {
  // 清理事件监听器
  cleanupEventListeners()
  window.removeEventListener('resize', handleWindowResize)
  editorRootRef.value?.removeEventListener('testhub-locate-node', handleTesthubLocateNodeEvent)
  if (viewportSyncTimer) {
    clearTimeout(viewportSyncTimer)
    viewportSyncTimer = null
  }
  if (minderInitTimer) {
    clearTimeout(minderInitTimer)
    minderInitTimer = null
  }
  if (editorRefocusTimer) {
    clearTimeout(editorRefocusTimer)
    editorRefocusTimer = null
  }
  if (moduleOverviewRefreshTimer) {
    clearTimeout(moduleOverviewRefreshTimer)
    moduleOverviewRefreshTimer = null
  }
  if (mindmapOverviewFocusTimer) {
    clearTimeout(mindmapOverviewFocusTimer)
    mindmapOverviewFocusTimer = null
  }

  // 清理正在编辑的输入框
  if (currentEditInput) {
    try {
      currentEditInput.saveAndRemove()
    } catch (e) {
      console.log('清理编辑框失败:', e)
    }
  }
  if (mindmapAutoSaveTimer) {
    clearMindmapAutoSaveTimer()
    void runMindmapAutoSave()
  }

  // 清理 minder 实例 - 不调用 destroy，直接清空引用
  // KityMinder 的 destroy 方法可能有问题，避免错误
  minder = null

  console.log('ManualTestCaseEditor 组件已卸载')
})

defineExpose({
  toggleToolbar,
  setToolbarVisible,
  toggleDetailPanel,
  save: handleSave,
  exportMindmap: handleExportCommand,
  importMindmap: handleImportCommand,
  locateAndSelectNode,
  getToolbarState,
})
</script>

<style scoped>
.manual-testcase-editor {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.el-card) {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.minder-toolbar {
  padding: 6px 8px;
  background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
  border: 1px solid #dee2e6;
  border-radius: 4px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 3px;
  overflow-x: auto;
  overflow-y: hidden;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.toolbar-section {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 3px;
}

.toolbar-page-actions {
  gap: 2px;
}

.toolbar-icon-dropdown-button {
  min-width: 30px;
}

.toolbar-icon-dropdown-button :deep(.el-icon--right),
.toolbar-page-actions :deep(.el-icon--right) {
  margin-left: 1px;
}

.toolbar-scope-section {
  gap: 0;
}

.toolbar-clear-button {
  padding: 0 2px;
  font-size: 12px;
}

.toolbar-radio-group {
  display: flex;
  flex: 0 0 auto;
  gap: 2px;
}

.toolbar-radio-group--compact :deep(.el-radio__input) {
  display: none;
}

.toolbar-radio-group--compact :deep(.el-radio__label) {
  padding-left: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  color: inherit;
  font-size: 13px;
}

.minder-toolbar :deep(.el-button--small) {
  min-height: 26px;
  padding: 4px 6px;
}

.minder-toolbar :deep(.el-button--small .el-icon + span) {
  margin-left: 3px;
}

.minder-toolbar :deep(.el-input__wrapper) {
  min-height: 26px;
  padding-top: 0;
  padding-bottom: 0;
}

.minder-toolbar :deep(.el-divider--vertical) {
  height: 16px;
  margin: 0;
}

.toolbar-radio-group :deep(.el-radio) {
  margin-right: 0;
}

.toolbar-radio-group :deep(.el-radio.is-bordered) {
  padding: 3px 5px;
  border-radius: 4px;
  transition: all 0.2s;
}

.toolbar-radio-group--compact :deep(.el-radio.is-bordered) {
  min-width: 26px;
  height: 26px;
  padding: 3px 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.priority-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  line-height: 1;
}

.priority-marker svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.priority-marker text {
  font-family: Arial, sans-serif;
  font-weight: 700;
  pointer-events: none;
}

.toolbar-priority-marker {
  width: 18px;
  height: 18px;
}

.toolbar-radio-group :deep(.el-radio.is-bordered:hover) {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.toolbar-radio-group :deep(.el-radio.is-bordered.is-checked) {
  border-color: #409eff;
  background-color: #409eff;
  color: #fff;
}

.toolbar-radio-group :deep(.el-radio.is-bordered.is-checked .el-radio__label) {
  color: #fff;
}

.toolbar-radio-group :deep(.el-radio.is-disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-node-type-code {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 14px;
  border-radius: 3px;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  font-size: 10px;
  font-weight: 700;
}

.toolbar-radio-group :deep(.el-radio.is-bordered.is-checked) .toolbar-node-type-code {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.toolbar-fold-enter-active,
.toolbar-fold-leave-active {
  overflow: hidden;
  transition: max-height 0.25s ease, opacity 0.2s ease, margin-bottom 0.25s ease;
}

.toolbar-fold-enter-from,
.toolbar-fold-leave-to {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
}

.toolbar-fold-enter-to,
.toolbar-fold-leave-from {
  max-height: 200px;
  opacity: 1;
  margin-bottom: 8px;
}

.main-content {
  display: flex;
  flex: 1;
  gap: 10px;
  min-height: 0;
  align-items: stretch;
  position: relative;
}

.minder-container {
  flex: 1;
  min-width: 0;
  min-height: 0;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  background-color: #fafafa;
  display: flex;
  transition: all 0.3s ease;
  position: relative;
}

#minder-editor {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  background-color: #fff;
  outline: none; /* 移除默认的焦点轮廓 */
  cursor: default;
}

#minder-editor.is-panning {
  cursor: grabbing;
}

#minder-editor:focus {
  /* 可选：添加自定义的焦点样式 */
  box-shadow: inset 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.mindmap-overview {
  position: absolute;
  z-index: 8;
  top: 12px;
  left: 12px;
  width: 228px;
  max-width: calc(100% - 24px);
  max-height: calc(100% - 24px);
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 14px rgba(31, 45, 61, 0.12);
  color: #303133;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  pointer-events: auto;
}

.mindmap-overview.is-collapsed {
  overflow: hidden;
}

.mindmap-overview__group + .mindmap-overview__group {
  border-top: 1px solid #dcdfe6;
}

.mindmap-overview__group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 9px;
  background: #f5f7fa;
  color: #303133;
  font-size: 12px;
  font-weight: 600;
  line-height: 30px;
  white-space: nowrap;
}

.mindmap-overview__group-title .el-icon {
  flex: 0 0 auto;
  color: #606266;
  font-size: 14px;
}

.mindmap-overview__group-label {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mindmap-overview__toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  margin-left: auto;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: #606266;
  cursor: pointer;
}

.mindmap-overview__toggle:hover {
  border-color: #b3d8ff;
  background: #fff;
  color: #1677ff;
}

.mindmap-overview__toggle .el-icon {
  color: inherit;
  font-size: 13px;
}

.mindmap-overview__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 82px;
  align-items: center;
  min-height: 32px;
  padding: 3px 5px 3px 8px;
  border-top: 1px solid #ebeef5;
  background: rgba(255, 255, 255, 0.92);
  transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.mindmap-overview__item:hover:not(.is-disabled) {
  background: #f5f9ff;
}

.mindmap-overview__item.is-active {
  background: #ecf5ff;
  box-shadow: inset 3px 0 0 #409eff;
}

.mindmap-overview__item.is-disabled {
  background: #fafafa;
  color: #a8abb2;
}

.mindmap-overview__trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  height: 26px;
  padding: 0 4px 0 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.mindmap-overview__trigger:disabled {
  color: #a8abb2;
  cursor: default;
}

.mindmap-overview__toggle:focus-visible,
.mindmap-overview__trigger:focus-visible,
.mindmap-overview__arrow:focus-visible {
  outline: 2px solid rgba(64, 158, 255, 0.45);
  outline-offset: 1px;
}

.mindmap-overview__indicator {
  flex: 0 0 auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
}

.mindmap-overview__item-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mindmap-overview__trigger strong {
  flex: 0 0 auto;
  margin-left: auto;
  color: #303133;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.mindmap-overview__item.is-disabled .mindmap-overview__trigger strong {
  color: #a8abb2;
}

.mindmap-overview__navigation {
  display: grid;
  grid-template-columns: 22px 34px 22px;
  align-items: center;
  justify-content: end;
  gap: 2px;
}

.mindmap-overview__arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: #606266;
  cursor: pointer;
}

.mindmap-overview__arrow:hover:not(:disabled) {
  border-color: #b3d8ff;
  background: #fff;
  color: #1677ff;
}

.mindmap-overview__arrow:disabled {
  color: #c0c4cc;
  cursor: default;
}

.mindmap-overview__arrow .el-icon {
  font-size: 13px;
}

.mindmap-overview__position {
  color: #606266;
  font-size: 11px;
  line-height: 22px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.mindmap-overview__item.is-active .mindmap-overview__position {
  color: #1677ff;
  font-weight: 600;
}

.mindmap-overview__item--danger .mindmap-overview__indicator,
.mindmap-overview__item--fail .mindmap-overview__indicator {
  background: #d93025;
}

.mindmap-overview__item--module .mindmap-overview__indicator {
  background: #409eff;
}

.mindmap-overview__item--pass .mindmap-overview__indicator {
  background: #2f8f46;
}

.mindmap-overview__item--block .mindmap-overview__indicator {
  background: #b35c00;
}

.mindmap-overview__item--not-test .mindmap-overview__indicator {
  background: #6b7280;
}

.mindmap-overview__item--review .mindmap-overview__indicator {
  background: #e46c0a;
}

.mindmap-overview__item--review-all .mindmap-overview__indicator {
  background: #8b5cf6;
}

.mindmap-context-menu {
  position: absolute;
  z-index: 20;
  width: 176px;
  padding: 6px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.16);
  overflow: visible;
}

.mindmap-context-menu__section {
  position: relative;
  padding: 0;
}

.mindmap-context-menu__section::after {
  position: absolute;
  top: 0;
  left: 100%;
  width: 8px;
  height: 32px;
  content: '';
}

.mindmap-context-menu.open-left .mindmap-context-menu__section::after {
  right: 100%;
  left: auto;
}

.mindmap-context-menu__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  padding: 0 10px;
  border-radius: 4px;
  color: #303133;
  font-size: 13px;
  line-height: 32px;
  cursor: default;
  outline: none;
}

.mindmap-context-menu__title::after {
  color: #909399;
  font-size: 16px;
  content: '›';
}

.mindmap-context-menu__section:hover > .mindmap-context-menu__title,
.mindmap-context-menu__section:focus-within > .mindmap-context-menu__title {
  background: #ecf5ff;
  color: #1677ff;
}

.mindmap-context-menu__item {
  position: absolute;
  z-index: 2;
  left: calc(100% + 5px);
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 220px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #dcdfe6;
  border-radius: 0;
  background: #fff;
  color: #303133;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
}

.mindmap-context-menu.open-left .mindmap-context-menu__item {
  right: calc(100% + 5px);
  left: auto;
}

.mindmap-context-menu__section:hover > .mindmap-context-menu__item,
.mindmap-context-menu__section:focus-within > .mindmap-context-menu__item {
  display: flex;
}

.mindmap-context-menu__item:nth-of-type(1) { top: 0; }
.mindmap-context-menu__item:nth-of-type(2) { top: 31px; }
.mindmap-context-menu__item:nth-of-type(3) { top: 62px; }
.mindmap-context-menu__item:nth-of-type(4) { top: 93px; }
.mindmap-context-menu__item:nth-of-type(5) { top: 124px; }
.mindmap-context-menu__item:nth-of-type(6) { top: 155px; }
.mindmap-context-menu__item:nth-of-type(7) { top: 186px; }
.mindmap-context-menu__item:nth-of-type(8) { top: 217px; }

.mindmap-context-menu__item:first-of-type {
  border-radius: 5px 5px 0 0;
}

.mindmap-context-menu__item:last-of-type {
  border-radius: 0 0 5px 5px;
}

.mindmap-context-menu__item:hover {
  background: #ecf5ff;
  color: #1677ff;
}

.mindmap-context-menu__item:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.mindmap-context-menu__item:disabled:hover {
  background: transparent;
  color: #c0c4cc;
}

.mindmap-context-menu__label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.priority-marker--context {
  width: 18px;
  height: 18px;
}

.mindmap-context-menu__shortcut {
  color: #909399;
  font-size: 12px;
}

.detail-panel {
  width: 400px;
  min-width: 400px;
  height: 100%;
  min-height: 0;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  padding: 15px;
  background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.panel-content {
  flex: 1;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.panel-content h4 {
  margin: 20px 0 15px 0;
  font-size: 14px;
  font-weight: 600;
  color: #666;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.detail-panel-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-panel-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: visible;
}

.detail-panel-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.requirement-facts {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.requirement-fact-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  background: #fff;
}

.fact-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.5;
}

.fact-card-header strong {
  flex: 1;
  min-width: 0;
  color: #303133;
  font-size: 13px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.fact-path,
.fact-source {
  margin-top: 8px;
  color: #606266;
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.fact-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.fact-section-title {
  margin-bottom: 6px;
  color: #303133;
  font-size: 12px;
  font-weight: 600;
}

.fact-property-row {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 8px;
  margin-bottom: 6px;
  color: #606266;
  font-size: 12px;
  line-height: 1.6;
}

.fact-property-row span {
  color: #909399;
}

.fact-property-row b {
  color: #303133;
  font-weight: 500;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.node-type-form-item :deep(.el-form-item__content) {
  line-height: 1.4;
}

.node-type-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  width: 100%;
}

.node-type-radio {
  display: inline-flex;
  align-items: center;
  margin-right: 0;
  min-width: 112px;
}

.node-type-radio :deep(.el-radio__label) {
  display: inline-flex;
  align-items: center;
  padding-left: 8px;
}

.node-type-radio-code {
  min-width: 16px;
  font-weight: 700;
  color: #409eff;
}

.node-type-radio-name {
  margin-left: 6px;
  color: #303133;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
}

/* 过渡动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 滚动条样式 */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 备注预览 */
.note-preview {
  padding: 15px;
  min-height: 200px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fafafa;
  line-height: 1.8;
}

.note-preview h1 {
  font-size: 24px;
  margin: 10px 0;
  color: #333;
}

.note-preview h2 {
  font-size: 20px;
  margin: 8px 0;
  color: #555;
}

.note-preview h3 {
  font-size: 16px;
  margin: 6px 0;
  color: #666;
}

/* 颜色选择器 */
.color-picker-container {
  padding: 10px;
}

.color-presets {
  margin-top: 20px;
}

.color-presets h4 {
  margin: 10px 0;
  font-size: 14px;
  color: #666;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}

.color-item {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid #e4e7ed;
  transition: all 0.2s;
}

.color-item:hover {
  transform: scale(1.1);
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

/* 响应式 */
@media (max-width: 1400px) {
  .detail-panel {
    width: 350px;
    min-width: 350px;
  }
}

@media (max-width: 1200px) {
  .detail-panel {
    width: 300px;
    min-width: 300px;
  }
}
</style>

<style>
.minder-toolbar-dropdown .el-dropdown-menu__item.is-active {
  color: #409eff;
  background: #ecf5ff;
  font-weight: 600;
}

/* 双击编辑输入框全局样式 */
.km-edit-input {
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  box-sizing: border-box;
}

/* KityMinder自定义样式 */
.km-node[data-priority="0"] text {
  fill: #f5222d !important;
  font-weight: bold;
}

.km-node[data-priority="1"] text {
  fill: #fa8c16 !important;
  font-weight: 600;
}

.km-node[data-priority="2"] text {
  fill: #fadb14 !important;
}

.km-node[data-priority="3"] text {
  fill: #1890ff !important;
}

.km-node[data-status="pass"] {
  background-color: #f6ffed;
}

.km-node[data-status="fail"] {
  background-color: #fff2f0;
}

.km-node[data-status="block"] {
  background-color: #fff7e6;
}
</style>
