<template>
  <div class="layout" :style="layoutStyle">
    <header v-if="!hideLayoutTopbar" class="topbar" :class="topbarClass">
      <div class="topbar-left">
        <button class="brand" type="button" @click="goBrandHome">{{ brandLabel }}</button>
      </div>

      <div class="topbar-center" :class="{ 'topbar-center--floating-active': showFloatingAiControl }">
        <div v-if="showTopbarModuleMenu" class="module-menu-track">
          <button
            v-for="item in currentModuleMenuItems"
            :key="item.path"
            class="nav-pill"
            :class="getNavPillClass(item.path)"
            type="button"
            @click="goToPath(item.path)"
          >
            <span class="nav-pill__label">{{ item.label }}</span>
          </button>
        </div>
      </div>

      <div class="topbar-home">
        <el-popover placement="bottom" :width="680" trigger="click">
          <template #reference>
            <button class="theme-trigger" type="button" :aria-label="THEME_LABEL">
              <el-icon><BrushFilled /></el-icon>
            </button>
          </template>

          <div class="theme-panel">
            <div class="theme-panel__title">{{ THEME_LABEL }}</div>
            <div class="theme-panel__body">
              <nav class="theme-panel__tabs" :aria-label="THEME_LABEL">
                <button
                  v-for="tab in THEME_PANEL_TABS"
                  :key="tab.key"
                  class="theme-panel__tab"
                  :class="{ active: activeThemeTab === tab.key }"
                  type="button"
                  @click="activeThemeTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </nav>

              <div class="theme-panel__content">
                <template v-if="activeThemeTab === THEME_TAB_BACKGROUND">
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">{{ MENU_BACKGROUND_LABEL }}</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ MENU_BACKGROUND_MODE_LABEL }}</span>
                      <el-radio-group v-model="navigationTheme.menuBarMode" size="small">
                        <el-radio-button :label="MENU_BAR_MODE_SOLID">{{ MENU_BACKGROUND_SOLID_LABEL }}</el-radio-button>
                        <el-radio-button :label="MENU_BAR_MODE_GRADIENT">{{ MENU_BACKGROUND_GRADIENT_LABEL }}</el-radio-button>
                        <el-radio-button :label="MENU_BAR_MODE_ANIMATED">{{ MENU_BACKGROUND_ANIMATED_LABEL }}</el-radio-button>
                      </el-radio-group>
                    </div>
                    <template v-if="navigationTheme.menuBarMode === MENU_BAR_MODE_SOLID">
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme.menuBarColor" :teleported="false" />
                      </div>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in SOLID_COLOR_PRESETS"
                            :key="preset.key"
                            class="theme-preset"
                            :class="{ active: isSolidPresetActive(preset) }"
                            type="button"
                            @click="applySolidPreset(preset)"
                          >
                            <span class="theme-preset__swatch" :style="{ background: preset.color }" />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <template v-else-if="navigationTheme.menuBarMode === MENU_BAR_MODE_GRADIENT">
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_DIRECTION_LABEL }}</span>
                        <el-select v-model="navigationTheme.menuBarGradientDirection" size="small" class="theme-panel__select">
                          <el-option
                            v-for="option in GRADIENT_DIRECTION_OPTIONS"
                            :key="option.value"
                            :label="option.label"
                            :value="option.value"
                          />
                        </el-select>
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_START_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme.menuBarGradientStartColor" :teleported="false" />
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_MIDDLE_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme.menuBarGradientMiddleColor" :teleported="false" />
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_END_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme.menuBarGradientEndColor" :teleported="false" />
                      </div>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in GRADIENT_COLOR_PRESETS"
                            :key="preset.key"
                            class="theme-preset"
                            :class="{ active: isGradientPresetActive(preset) }"
                            type="button"
                            @click="applyGradientPreset(preset)"
                          >
                            <span
                              class="theme-preset__swatch"
                              :style="{ background: buildLinearGradient(preset.direction, preset.colors) }"
                            />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_ANIMATED_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in ANIMATED_COLOR_PRESETS"
                            :key="preset.key"
                            class="theme-preset"
                            :class="{ active: isAnimatedPresetActive(preset) }"
                            type="button"
                            @click="applyAnimatedPreset(preset)"
                          >
                            <span
                              class="theme-preset__swatch theme-preset__swatch--animated"
                              :style="{ background: buildLinearGradient(preset.direction, preset.colors) }"
                            />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                  </div>
                </template>

                <template v-else-if="activeThemeTab === THEME_TAB_AI_CONVERSATION">
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">最右侧菜单</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_RIGHT_MENU_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiRightRailColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_RIGHT_MENU_TEXT_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiRightRailTextColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_SELECTED_MENU_TEXT_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiSelectedMenuTextColor" :teleported="false" />
                    </div>
                  </div>
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">会话窗口</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CONVERSATION_WINDOW_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiConversationWindowColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CONVERSATION_WINDOW_TEXT_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiConversationWindowTextColor" :teleported="false" />
                    </div>
                  </div>
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">问题消息</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_QUESTION_PANEL_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiQuestionPanelColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_QUESTION_PANEL_TEXT_COLOR_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiQuestionPanelTextColor" :teleported="false" />
                    </div>
                  </div>
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">主对话区</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CHAT_COMPOSER_BG_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiChatComposerBgColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CHAT_COMPOSER_TEXT_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiChatComposerTextColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CHAT_CONTENT_BG_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiChatContentBgColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_CHAT_CONTENT_TEXT_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiChatContentTextColor" :teleported="false" />
                    </div>
                  </div>
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">消息气泡</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_USER_MESSAGE_BG_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiUserMessageBgColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_USER_MESSAGE_TEXT_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiUserMessageTextColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_ASSISTANT_MESSAGE_BG_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiAssistantMessageBgColor" :teleported="false" />
                    </div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ AI_ASSISTANT_MESSAGE_TEXT_LABEL }}</span>
                      <el-color-picker v-model="navigationTheme.aiAssistantMessageTextColor" :teleported="false" />
                    </div>
                  </div>
                  <div class="theme-panel__section">
                    <div class="theme-panel__section-title">头像图标</div>
                    <div class="theme-panel__row theme-panel__row--stack">
                      <span class="theme-panel__label">{{ AI_USER_ICON_LABEL }}</span>
                      <div class="theme-icon-choice-list">
                        <button
                          v-for="item in AI_USER_ICON_OPTIONS"
                          :key="item.key"
                          class="theme-icon-choice"
                          :class="{ active: navigationTheme.aiUserMessageIcon === item.key }"
                          type="button"
                          @click="navigationTheme.aiUserMessageIcon = item.key"
                        >
                          <el-icon><component :is="item.icon" /></el-icon>
                          <span>{{ item.label }}</span>
                        </button>
                      </div>
                    </div>
                    <div class="theme-panel__row theme-panel__row--stack">
                      <span class="theme-panel__label">{{ AI_ASSISTANT_ICON_LABEL }}</span>
                      <div class="theme-icon-choice-list">
                        <button
                          v-for="item in AI_ASSISTANT_ICON_OPTIONS"
                          :key="item.key"
                          class="theme-icon-choice"
                          :class="{ active: navigationTheme.aiAssistantMessageIcon === item.key }"
                          type="button"
                          @click="navigationTheme.aiAssistantMessageIcon = item.key"
                        >
                          <el-icon><component :is="item.icon" /></el-icon>
                          <span>{{ item.label }}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </template>

                <template v-else>
                  <div
                    v-for="group in activeThemeEffectGroups"
                    :key="group.key"
                    class="theme-panel__section"
                  >
                    <div class="theme-panel__section-title">{{ group.title }}</div>
                    <div class="theme-panel__row">
                      <span class="theme-panel__label">{{ MENU_EFFECT_MODE_LABEL }}</span>
                      <el-radio-group v-model="navigationTheme[group.modeKey]" size="small">
                        <el-radio-button :label="MENU_BAR_MODE_SOLID">{{ MENU_BACKGROUND_SOLID_LABEL }}</el-radio-button>
                        <el-radio-button :label="MENU_BAR_MODE_GRADIENT">{{ MENU_BACKGROUND_GRADIENT_LABEL }}</el-radio-button>
                        <el-radio-button :label="MENU_BAR_MODE_ANIMATED">{{ MENU_BACKGROUND_ANIMATED_LABEL }}</el-radio-button>
                      </el-radio-group>
                    </div>
                    <template v-if="navigationTheme[group.modeKey] === MENU_BAR_MODE_SOLID">
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ group.colorLabel }}</span>
                        <el-color-picker v-model="navigationTheme[group.colorKey]" :teleported="false" />
                      </div>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in SOLID_COLOR_PRESETS"
                            :key="`${group.key}-${preset.key}`"
                            class="theme-preset"
                            :class="{ active: isEffectSolidPresetActive(group.key, preset) }"
                            type="button"
                            @click="applyEffectSolidPreset(group.key, preset)"
                          >
                            <span class="theme-preset__swatch" :style="{ background: preset.color }" />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <template v-else-if="navigationTheme[group.modeKey] === MENU_BAR_MODE_GRADIENT">
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_DIRECTION_LABEL }}</span>
                        <el-select
                          v-model="navigationTheme[group.gradientDirectionKey]"
                          size="small"
                          class="theme-panel__select"
                        >
                          <el-option
                            v-for="option in GRADIENT_DIRECTION_OPTIONS"
                            :key="`${group.key}-${option.value}`"
                            :label="option.label"
                            :value="option.value"
                          />
                        </el-select>
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_START_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme[group.gradientStartColorKey]" :teleported="false" />
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_MIDDLE_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme[group.gradientMiddleColorKey]" :teleported="false" />
                      </div>
                      <div class="theme-panel__row">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_GRADIENT_END_LABEL }}</span>
                        <el-color-picker v-model="navigationTheme[group.gradientEndColorKey]" :teleported="false" />
                      </div>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in GRADIENT_COLOR_PRESETS"
                            :key="`${group.key}-${preset.key}`"
                            class="theme-preset"
                            :class="{ active: isEffectGradientPresetActive(group.key, preset) }"
                            type="button"
                            @click="applyEffectGradientPreset(group.key, preset)"
                          >
                            <span
                              class="theme-preset__swatch"
                              :style="{ background: buildLinearGradient(preset.direction, preset.colors) }"
                            />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="theme-panel__row theme-panel__row--stack">
                        <span class="theme-panel__label">{{ MENU_BACKGROUND_ANIMATED_PRESET_LABEL }}</span>
                        <div class="theme-panel__preset-list">
                          <button
                            v-for="preset in ANIMATED_COLOR_PRESETS"
                            :key="`${group.key}-${preset.key}`"
                            class="theme-preset"
                            :class="{ active: isEffectAnimatedPresetActive(group.key, preset) }"
                            type="button"
                            @click="applyEffectAnimatedPreset(group.key, preset)"
                          >
                            <span
                              class="theme-preset__swatch theme-preset__swatch--animated"
                              :style="{ background: buildLinearGradient(preset.direction, preset.colors) }"
                            />
                            <span class="theme-preset__text">{{ preset.label }}</span>
                          </button>
                        </div>
                      </div>
                    </template>
                  </div>
                </template>
              </div>
            </div>
            <div class="theme-panel__actions">
              <el-button size="small" @click="resetNavigationTheme">{{ RESET_THEME_LABEL }}</el-button>
            </div>
          </div>
        </el-popover>

        <el-dropdown
          class="home-switcher"
          :class="{ 'is-home-active': route.path === '/home' }"
          split-button
          trigger="click"
          @click="goHome"
          @command="handleHomeCommand"
        >
          <span class="home-switcher-label">
            <el-icon><HomeFilled /></el-icon>
            <span>{{ HOME_LABEL }}</span>
          </span>

          <template #dropdown>
            <el-dropdown-menu class="home-dropdown">
              <el-dropdown-item command="home">{{ HOME_LABEL }}</el-dropdown-item>
              <el-dropdown-item v-if="moduleSwitcherItems.length" divided disabled>
                {{ MODULE_SWITCHER_LABEL }}
              </el-dropdown-item>
              <el-dropdown-item
                v-for="module in moduleSwitcherItems"
                :key="module.key"
                :command="`module:${module.key}`"
                :disabled="!module.path"
              >
                {{ module.label }}{{ module.path ? '' : UNDER_DEVELOPMENT_LABEL }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="topbar-right">
        <el-dropdown trigger="click" @command="handleUserCommand">
          <div class="user-trigger">
            <el-avatar :size="34" :src="userStore.user?.avatar" :icon="UserFilled" />
            <span class="username">{{ userStore.user?.username || DEFAULT_USERNAME }}</span>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>

          <template #dropdown>
            <el-dropdown-menu class="user-dropdown">
              <el-dropdown-item command="profile">{{ PROFILE_LABEL }}</el-dropdown-item>
              <el-dropdown-item divided command="logout">{{ LOGOUT_LABEL }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div
      v-if="showFloatingAiControl"
      class="ai-floating-control"
      :class="{
        'ai-floating-control--expanded': floatingAiControlExpanded,
        'ai-floating-control--dragging': floatingAiControlDragging,
        'ai-floating-control--product-hero': shouldAnchorFloatingAiControlToProductHero,
      }"
      :style="floatingAiControlStyle"
    >
      <svg
        v-if="floatingAiControlExpanded"
        class="ai-floating-control__radial"
        :viewBox="floatingAiRadialViewBox"
        aria-label="思源质量扇形菜单"
      >
        <defs>
          <path
            v-for="path in floatingAiSectorLabelPaths"
            :key="path.id"
            :id="path.id"
            :d="path.d"
          />
        </defs>
        <g
          v-for="ring in floatingAiRadialRings"
          :key="ring.key"
          class="ai-floating-control__ring"
          :class="[
            ring.level === 0 ? 'ai-floating-control__ring--primary' : 'ai-floating-control__ring--submenu',
            `ai-floating-control__ring--level-${ring.level}`,
          ]"
        >
          <g
            v-for="item in ring.items"
            :key="item.pathKey"
            class="ai-floating-control__sector"
            :class="[
              ring.level > 0 ? 'ai-floating-control__sector--submenu' : '',
              `ai-floating-control__sector--level-${ring.level}`,
              {
                active: item.active,
                'has-children': hasFloatingSubmenu(item),
                disabled: item.disabled,
              },
            ]"
            role="button"
            tabindex="0"
            :aria-label="item.label"
            :data-floating-key="item.key"
            :data-floating-path="item.pathKey"
            @mouseenter="handleFloatingSectorEnter(item)"
            @mouseleave="handleFloatingSectorLeave(item)"
            @click.stop="handleFloatingSectorClick(item)"
            @keydown.enter.prevent="handleFloatingSectorClick(item)"
            @keydown.space.prevent="handleFloatingSectorClick(item)"
          >
            <path :d="item.sectorPath" />
            <text
              v-if="item.labelPathId"
              class="ai-floating-control__sector-label ai-floating-control__sector-label--arc"
              dominant-baseline="middle"
            >
              <textPath
                :href="`#${item.labelPathId}`"
                startOffset="50%"
                text-anchor="middle"
              >{{ item.label }}</textPath>
            </text>
            <text
              v-else
              class="ai-floating-control__sector-label"
              :x="item.labelX"
              :y="item.labelY"
              text-anchor="middle"
              dominant-baseline="central"
            >
              <tspan
                v-for="(line, lineIndex) in item.labelLines"
                :key="`${item.key}-label-${lineIndex}`"
                :x="item.labelX"
                :dy="getFloatingSectorLabelDy(item.labelLines, lineIndex)"
              >{{ line }}</tspan>
            </text>
          </g>
        </g>
      </svg>

      <button
        class="ai-floating-control__core"
        type="button"
        aria-label="思源质量控制菜单"
        :aria-expanded="floatingAiControlExpanded"
        @pointerdown="handleFloatingCorePointerDown"
        @click.stop="handleFloatingCoreClick"
      >
        <span>思源质量</span>
      </button>

    </div>

    <div class="layout-main" :class="{ 'layout-main--topbar-hidden': hideLayoutTopbar }">
      <div class="layout-content" :class="layoutContentClass">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Avatar,
  BrushFilled,
  ChatDotRound,
  ChatLineRound,
  Cpu,
  Headset,
  HomeFilled,
  MagicStick,
  Monitor,
  Opportunity,
  Service,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  APP_TOPBAR_HEIGHT,
  getModuleKeyFromPath,
  getModuleMenuItems,
  getVisibleModuleSwitcherItems,
} from '@/utils/appNavigation'
import {
  buildManualTestcaseLocationFromPath,
  getManualTestcasePrimaryMenuPathByRoute,
} from '@/utils/manualTestcaseWorkspace'
import {
  AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES,
  AI_WORKSHOP_TAB_PERMISSION_CANDIDATES,
  hasPermissionAccess,
} from '@/utils/permissions'

const HOME_LABEL = '\u9996\u9875'
const MODULE_SWITCHER_LABEL = '\u6A21\u5757\u5207\u6362'
const UNDER_DEVELOPMENT_LABEL = '\uFF08\u5F00\u53D1\u4E2D\uFF09'
const DEFAULT_USERNAME = '\u7528\u6237'
const PROFILE_LABEL = '\u4E2A\u4EBA\u8BBE\u7F6E'
const LOGOUT_LABEL = '\u9000\u51FA\u767B\u5F55'
const MODULE_IN_DEVELOPMENT_MESSAGE = '\u8BE5\u6A21\u5757\u6B63\u5728\u5F00\u53D1\u4E2D'
const LOGOUT_SUCCESS_MESSAGE = '\u9000\u51FA\u767B\u5F55\u6210\u529F'
const THEME_LABEL = '\u6362\u80A4'
const MENU_BACKGROUND_LABEL = '\u83DC\u5355\u80CC\u666F\u8272'
const MENU_BACKGROUND_MODE_LABEL = '\u80CC\u666F\u6A21\u5F0F'
const MENU_BACKGROUND_SOLID_LABEL = '\u7EAF\u8272'
const MENU_BACKGROUND_GRADIENT_LABEL = '\u6E10\u53D8'
const MENU_BACKGROUND_ANIMATED_LABEL = '\u52A8\u6001'
const MENU_BACKGROUND_GRADIENT_DIRECTION_LABEL = '\u6E10\u53D8\u65B9\u5411'
const MENU_BACKGROUND_GRADIENT_START_LABEL = '\u8D77\u59CB\u8272'
const MENU_BACKGROUND_GRADIENT_MIDDLE_LABEL = '\u4E2D\u95F4\u8272'
const MENU_BACKGROUND_GRADIENT_END_LABEL = '\u7ED3\u675F\u8272'
const MENU_BACKGROUND_PRESET_LABEL = '\u591A\u5F69\u9884\u8BBE'
const MENU_BACKGROUND_ANIMATED_PRESET_LABEL = '\u52A8\u6001\u6548\u679C'
const MENU_EFFECT_MODE_LABEL = '\u6548\u679C\u6A21\u5F0F'
const MENU_BUTTON_BACKGROUND_LABEL = '\u83DC\u5355\u540D\u80CC\u666F\u8272'
const MENU_BUTTON_TEXT_LABEL = '\u83DC\u5355\u540D\u5B57\u4F53\u989C\u8272'
const MENU_BUTTON_ACTIVE_BACKGROUND_LABEL = '\u9009\u4E2D\u83DC\u5355\u80CC\u666F\u8272'
const MENU_BUTTON_ACTIVE_TEXT_LABEL = '\u9009\u4E2D\u83DC\u5355\u5B57\u4F53\u989C\u8272'
const MENU_BUTTON_BACKGROUND_SECTION_LABEL = '\u83DC\u5355\u540D\u80CC\u666F\u6548\u679C'
const MENU_BUTTON_TEXT_SECTION_LABEL = '\u83DC\u5355\u540D\u5B57\u4F53\u6548\u679C'
const MENU_BUTTON_ACTIVE_BACKGROUND_SECTION_LABEL = '\u9009\u4E2D\u83DC\u5355\u80CC\u666F\u6548\u679C'
const MENU_BUTTON_ACTIVE_TEXT_SECTION_LABEL = '\u9009\u4E2D\u83DC\u5355\u5B57\u4F53\u6548\u679C'
const PAGE_BACKGROUND_LABEL = '\u975E\u83DC\u5355\u533A\u57DF\u80CC\u666F\u8272'
const PAGE_BUTTON_BACKGROUND_LABEL = '\u9875\u9762\u6309\u94AE\u80CC\u666F\u8272'
const PAGE_BUTTON_TEXT_LABEL = '\u9875\u9762\u6309\u94AE\u5B57\u4F53\u989C\u8272'
const PAGE_BACKGROUND_SECTION_LABEL = '\u975E\u83DC\u5355\u533A\u57DF\u6548\u679C'
const PAGE_BUTTON_BACKGROUND_SECTION_LABEL = '\u9875\u9762\u6309\u94AE\u80CC\u666F\u6548\u679C'
const PAGE_BUTTON_TEXT_SECTION_LABEL = '\u9875\u9762\u6309\u94AE\u5B57\u4F53\u6548\u679C'
const AI_RIGHT_MENU_COLOR_LABEL = '最右菜单栏背景色'
const AI_RIGHT_MENU_TEXT_COLOR_LABEL = '未选中字体色'
const AI_SELECTED_MENU_TEXT_COLOR_LABEL = '被选择菜单字体色'
const AI_CONVERSATION_WINDOW_COLOR_LABEL = '会话窗口背景色'
const AI_CONVERSATION_WINDOW_TEXT_COLOR_LABEL = '会话窗口字体色'
const AI_QUESTION_PANEL_COLOR_LABEL = '问题消息背景色'
const AI_QUESTION_PANEL_TEXT_COLOR_LABEL = '问题消息字体色'
const AI_CHAT_COMPOSER_BG_LABEL = '对话框背景色'
const AI_CHAT_COMPOSER_TEXT_LABEL = '对话框字体色'
const AI_CHAT_CONTENT_BG_LABEL = '内容展示框背景色'
const AI_CHAT_CONTENT_TEXT_LABEL = '内容展示框字体色'
const AI_USER_MESSAGE_BG_LABEL = '我发送消息背景色'
const AI_USER_MESSAGE_TEXT_LABEL = '我发送消息字体色'
const AI_ASSISTANT_MESSAGE_BG_LABEL = 'AI返回信息背景色'
const AI_ASSISTANT_MESSAGE_TEXT_LABEL = 'AI返回信息字体色'
const AI_USER_ICON_LABEL = '我的图标'
const AI_ASSISTANT_ICON_LABEL = 'AI图标'
const RESET_THEME_LABEL = '\u6062\u590D\u9ED8\u8BA4'
const NAVIGATION_THEME_STORAGE_KEY = 'testhub-navigation-theme'
const NAVIGATION_THEME_CHANGE_EVENT = 'testhub-navigation-theme-change'
const AI_FLOATING_CONTROL_STORAGE_KEY = 'testhub-ai-floating-control-position'
const AI_FLOATING_CONTROL_SIZE = 96
const AI_FLOATING_CONTROL_MOBILE_SIZE = 82
const AI_FLOATING_CONTROL_MARGIN = 14
const AI_FLOATING_MENU_EDGE_GAP = 10
const AI_FLOATING_RADIAL_VIEWBOX_SIZE = 720
const AI_FLOATING_RADIAL_DISPLAY_SIZE = 720
const AI_FLOATING_MOBILE_RADIAL_DISPLAY_SIZE = 460
const AI_FLOATING_PRIMARY_INNER_RADIUS = 58
const AI_FLOATING_PRIMARY_OUTER_RADIUS = 150
const AI_FLOATING_SUBMENU_INNER_RADIUS = 156
const AI_FLOATING_SUBMENU_OUTER_RADIUS = 236
const AI_FLOATING_TERTIARY_INNER_RADIUS = 242
const AI_FLOATING_TERTIARY_OUTER_RADIUS = 306
const AI_FLOATING_MOBILE_PRIMARY_INNER_RADIUS = 50
const AI_FLOATING_MOBILE_PRIMARY_OUTER_RADIUS = 124
const AI_FLOATING_MOBILE_SUBMENU_INNER_RADIUS = 130
const AI_FLOATING_MOBILE_SUBMENU_OUTER_RADIUS = 204
const AI_FLOATING_MOBILE_TERTIARY_INNER_RADIUS = 210
const AI_FLOATING_MOBILE_TERTIARY_OUTER_RADIUS = 278
const AI_FLOATING_SECTOR_GAP_RADIANS = 0.025
const AI_FLOATING_LABEL_ARC_PADDING_RADIANS = 0.035
const AI_FLOATING_HOVER_SUPPRESSION_MS = 320
const AI_FLOATING_MOBILE_BREAKPOINT = 768
const AI_FLOATING_SAFE_RING_COUNT = 3
const AI_FLOATING_MAX_RENDERED_MENU_LEVELS = 3
const AI_FLOATING_SAVED_POSITION_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000
const AI_FLOATING_POSITION_SOURCE_MANUAL = 'manual'
const AI_PRODUCT_COMPOSER_FLOATING_ANCHOR_SELECTOR = '.product-composer'
const MENU_BAR_MODE_SOLID = 'solid'
const MENU_BAR_MODE_GRADIENT = 'gradient'
const MENU_BAR_MODE_ANIMATED = 'animated'
const THEME_TAB_BACKGROUND = 'background'
const THEME_TAB_MENU_NAME = 'menu-name'
const THEME_TAB_ACTIVE_MENU = 'active-menu'
const THEME_TAB_NON_MENU = 'non-menu'
const THEME_TAB_PAGE_BUTTON = 'page-button'
const THEME_TAB_AI_CONVERSATION = 'ai-conversation'
const THEME_PANEL_TABS = Object.freeze([
  { key: THEME_TAB_BACKGROUND, label: '\u80CC\u666F' },
  { key: THEME_TAB_MENU_NAME, label: '\u83DC\u5355\u540D' },
  { key: THEME_TAB_ACTIVE_MENU, label: '\u9009\u4E2D\u83DC\u5355' },
  { key: THEME_TAB_NON_MENU, label: '\u975E\u83DC\u5355\u533A\u57DF' },
  { key: THEME_TAB_PAGE_BUTTON, label: '\u9875\u9762\u6309\u94AE' },
  { key: THEME_TAB_AI_CONVERSATION, label: 'AI\u4F1A\u8BDD' },
])
const MENU_NAME_THEME_GROUPS = Object.freeze([
  createThemeEffectGroup('menuButtonBg', MENU_BUTTON_BACKGROUND_SECTION_LABEL, MENU_BUTTON_BACKGROUND_LABEL),
  createThemeEffectGroup('menuButtonText', MENU_BUTTON_TEXT_SECTION_LABEL, MENU_BUTTON_TEXT_LABEL),
])
const ACTIVE_MENU_THEME_GROUPS = Object.freeze([
  createThemeEffectGroup(
    'menuButtonActiveBg',
    MENU_BUTTON_ACTIVE_BACKGROUND_SECTION_LABEL,
    MENU_BUTTON_ACTIVE_BACKGROUND_LABEL
  ),
  createThemeEffectGroup('menuButtonActiveText', MENU_BUTTON_ACTIVE_TEXT_SECTION_LABEL, MENU_BUTTON_ACTIVE_TEXT_LABEL),
])
const NON_MENU_THEME_GROUPS = Object.freeze([
  createThemeEffectGroup('pageBg', PAGE_BACKGROUND_SECTION_LABEL, PAGE_BACKGROUND_LABEL),
])
const PAGE_BUTTON_THEME_GROUPS = Object.freeze([
  createThemeEffectGroup('pageButtonBg', PAGE_BUTTON_BACKGROUND_SECTION_LABEL, PAGE_BUTTON_BACKGROUND_LABEL),
  createThemeEffectGroup('pageButtonText', PAGE_BUTTON_TEXT_SECTION_LABEL, PAGE_BUTTON_TEXT_LABEL),
])
const MENU_BUTTON_THEME_GROUPS = Object.freeze([
  ...MENU_NAME_THEME_GROUPS,
  ...ACTIVE_MENU_THEME_GROUPS,
])
const CONTENT_THEME_GROUPS = Object.freeze([
  ...NON_MENU_THEME_GROUPS,
  ...PAGE_BUTTON_THEME_GROUPS,
])
const THEME_EFFECT_GROUPS = Object.freeze([
  ...MENU_BUTTON_THEME_GROUPS,
  ...CONTENT_THEME_GROUPS,
])
const THEME_EFFECT_GROUPS_BY_TAB = Object.freeze({
  [THEME_TAB_MENU_NAME]: MENU_NAME_THEME_GROUPS,
  [THEME_TAB_ACTIVE_MENU]: ACTIVE_MENU_THEME_GROUPS,
  [THEME_TAB_NON_MENU]: NON_MENU_THEME_GROUPS,
  [THEME_TAB_PAGE_BUTTON]: PAGE_BUTTON_THEME_GROUPS,
})
const AI_USER_ICON_OPTIONS = Object.freeze([
  { key: 'user', label: '线框用户', icon: User },
  { key: 'user-filled', label: '实心用户', icon: UserFilled },
  { key: 'avatar', label: '头像', icon: Avatar },
  { key: 'headset', label: '耳机', icon: Headset },
])
const AI_ASSISTANT_ICON_OPTIONS = Object.freeze([
  { key: 'chat-dot', label: '对话', icon: ChatDotRound },
  { key: 'chat-line', label: '消息', icon: ChatLineRound },
  { key: 'service', label: '服务', icon: Service },
  { key: 'cpu', label: '芯片', icon: Cpu },
  { key: 'magic', label: '魔法', icon: MagicStick },
  { key: 'monitor', label: '终端', icon: Monitor },
  { key: 'opportunity', label: '灵感', icon: Opportunity },
])
const AI_WORKSHOP_FLOATING_SUBMENU_ITEMS = Object.freeze([
  {
    key: 'workshop-skills',
    label: '\u6280\u80FD',
    path: '/ai-generation/workshop?workshop_tab=skills',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES.skills,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'skills', defaultWhenMissing: true },
  },
  {
    key: 'workshop-plugins',
    label: '\u63D2\u4EF6',
    path: '/ai-generation/workshop?workshop_tab=plugins',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES.plugins,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'plugins' },
  },
  {
    key: 'workshop-prompts',
    label: '\u63D0\u793A\u8BCD',
    path: '/ai-generation/workshop?workshop_tab=prompts',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES.prompts,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'prompts' },
  },
  {
    key: 'workshop-design-engineering',
    label: '\u8BBE\u8BA1\u5DE5\u7A0B',
    path: '/ai-generation/workshop?workshop_tab=design-engineering',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES['design-engineering'],
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'design-engineering' },
  },
  {
    key: 'workshop-agents',
    label: '\u667A\u80FD\u4F53',
    path: '/ai-generation/workshop?workshop_tab=agents',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES.agents,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'agents' },
  },
  {
    key: 'workshop-flows',
    label: '\u5DE5\u4F5C\u6D41',
    path: '/ai-generation/workshop?workshop_tab=flows',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES.flows,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'flows' },
  },
  {
    key: 'workshop-ai-session',
    label: 'AI\u4F1A\u8BDD',
    path: '/ai-generation/workshop?workshop_tab=ai-session&config_tab=robots',
    permissionCodes: AI_WORKSHOP_TAB_PERMISSION_CANDIDATES['ai-session'],
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'ai-session' },
  },
  {
    key: 'workshop-models',
    label: '\u5927\u6A21\u578B',
    path: '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    permissionCodes: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.llm,
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'models' },
  },
  {
    key: 'workshop-test-tools',
    label: '\u6D4B\u8BD5\u5DE5\u5177',
    path: '/ai-generation/workshop?workshop_tab=test-tools&config_tab=test-tools',
    permissionCodes: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES['test-tools'],
    match: { path: '/ai-generation/workshop', queryKey: 'workshop_tab', queryValue: 'test-tools' },
  },
  {
    key: 'workshop-ui-env',
    label: 'UI\u73AF\u5883',
    path: '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env',
    permissionCodes: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES['ui-env'],
    match: { path: '/ai-generation/workshop', queryKey: 'config_tab', queryValue: 'ui-env' },
  },
  {
    key: 'workshop-integrations',
    label: 'Git\u4ED3\u5E93',
    path: '/ai-generation/workshop/git-repositories',
    permissionCodes: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.git,
  },
  {
    key: 'workshop-notifications',
    label: '\u901A\u77E5\u673A\u5668\u4EBA',
    path: '/ai-generation/workshop/notification-robots',
    permissionCodes: AI_WORKSHOP_CONFIG_TAB_PERMISSION_CANDIDATES.notifications,
  },
])
const GRADIENT_DIRECTION_OPTIONS = Object.freeze([
  { label: '\u5411\u53F3', value: 'to right' },
  { label: '\u5411\u5DE6', value: 'to left' },
  { label: '\u5411\u4E0B', value: 'to bottom' },
  { label: '\u5411\u4E0A', value: 'to top' },
  { label: '\u53F3\u4E0B\u659C\u5411', value: 'to bottom right' },
  { label: '\u5DE6\u4E0B\u659C\u5411', value: 'to bottom left' },
  { label: '\u53F3\u4E0A\u659C\u5411', value: 'to top right' },
  { label: '\u5DE6\u4E0A\u659C\u5411', value: 'to top left' },
])
const SOLID_COLOR_PRESETS = Object.freeze([
  { key: 'classic-blue', label: '\u7ECF\u5178\u84DD', color: '#2396ea' },
  { key: 'deep-sea', label: '\u6DF1\u6D77\u84DD', color: '#0f4c81' },
  { key: 'emerald', label: '\u7FE0\u7EFF', color: '#0f9d7a' },
  { key: 'sunset', label: '\u6696\u6A59', color: '#ef6c3c' },
  { key: 'berry', label: '\u8393\u7D2B', color: '#8b5cf6' },
  { key: 'graphite', label: '\u77F3\u58A8', color: '#334155' },
])
const GRADIENT_COLOR_PRESETS = Object.freeze([
  { key: 'ocean', label: '\u6D77\u6D0B', direction: 'to right', colors: ['#37b4ff', '#23c6ff', '#2f7cf6'] },
  { key: 'sunrise', label: '\u65E5\u51FA', direction: 'to right', colors: ['#f97316', '#fb7185', '#8b5cf6'] },
  { key: 'forest', label: '\u68EE\u6797', direction: 'to right', colors: ['#16a34a', '#22c55e', '#0f766e'] },
  { key: 'aurora', label: '\u6781\u5149', direction: 'to bottom right', colors: ['#0ea5e9', '#22c55e', '#8b5cf6'] },
  { key: 'candy', label: '\u7F24\u7EB7', direction: 'to bottom', colors: ['#ec4899', '#f59e0b', '#3b82f6'] },
  { key: 'volcano', label: '\u706B\u5C71', direction: 'to top right', colors: ['#ef4444', '#f97316', '#facc15'] },
])
const ANIMATED_COLOR_PRESETS = Object.freeze([
  {
    key: 'rainbow',
    label: '\u6D41\u5149\u5F69\u8679',
    direction: 'to right',
    colors: ['#2563eb', '#06b6d4', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'],
    duration: '12s',
    backgroundSize: '260% 260%',
  },
  {
    key: 'aurora-wave',
    label: '\u6781\u5149\u6CE2',
    direction: 'to bottom right',
    colors: ['#0f766e', '#14b8a6', '#0ea5e9', '#6366f1', '#a855f7'],
    duration: '14s',
    backgroundSize: '240% 240%',
  },
  {
    key: 'sunset-flow',
    label: '\u665A\u971E\u6D41\u52A8',
    direction: 'to right',
    colors: ['#f97316', '#ef4444', '#ec4899', '#8b5cf6', '#3b82f6'],
    duration: '16s',
    backgroundSize: '260% 260%',
  },
  {
    key: 'mint-shift',
    label: '\u85C4\u96FE\u8584\u8377',
    direction: 'to top right',
    colors: ['#10b981', '#2dd4bf', '#38bdf8', '#6366f1'],
    duration: '11s',
    backgroundSize: '220% 220%',
  },
])
const DEFAULT_NAVIGATION_THEME = Object.freeze({
  menuBarMode: MENU_BAR_MODE_SOLID,
  menuBarColor: '#2396ea',
  menuBarGradientDirection: 'to right',
  menuBarGradientStartColor: '#79d2ff',
  menuBarGradientMiddleColor: '#54bbff',
  menuBarGradientEndColor: '#2396ea',
  menuBarAnimatedPreset: 'rainbow',
  menuButtonBgMode: MENU_BAR_MODE_SOLID,
  menuButtonBgColor: '#ffffff',
  menuButtonBgGradientDirection: 'to right',
  menuButtonBgGradientStartColor: '#ffffff',
  menuButtonBgGradientMiddleColor: '#f5f9ff',
  menuButtonBgGradientEndColor: '#dbeafe',
  menuButtonBgAnimatedPreset: 'aurora-wave',
  menuButtonTextMode: MENU_BAR_MODE_SOLID,
  menuButtonTextColor: '#2396ea',
  menuButtonTextGradientDirection: 'to right',
  menuButtonTextGradientStartColor: '#2396ea',
  menuButtonTextGradientMiddleColor: '#3b82f6',
  menuButtonTextGradientEndColor: '#1d4ed8',
  menuButtonTextAnimatedPreset: 'rainbow',
  menuButtonActiveBgMode: MENU_BAR_MODE_SOLID,
  menuButtonActiveBgColor: '#2396ea',
  menuButtonActiveBgGradientDirection: 'to right',
  menuButtonActiveBgGradientStartColor: '#1d4ed8',
  menuButtonActiveBgGradientMiddleColor: '#2396ea',
  menuButtonActiveBgGradientEndColor: '#60a5fa',
  menuButtonActiveBgAnimatedPreset: 'sunset-flow',
  menuButtonActiveTextMode: MENU_BAR_MODE_SOLID,
  menuButtonActiveTextColor: '#ffffff',
  menuButtonActiveTextGradientDirection: 'to right',
  menuButtonActiveTextGradientStartColor: '#ffffff',
  menuButtonActiveTextGradientMiddleColor: '#dbeafe',
  menuButtonActiveTextGradientEndColor: '#bfdbfe',
  menuButtonActiveTextAnimatedPreset: 'mint-shift',
  pageBgMode: MENU_BAR_MODE_SOLID,
  pageBgColor: '#f5f7fa',
  pageBgGradientDirection: 'to bottom right',
  pageBgGradientStartColor: '#f8fbff',
  pageBgGradientMiddleColor: '#edf6ff',
  pageBgGradientEndColor: '#f5f7fa',
  pageBgAnimatedPreset: 'aurora-wave',
  pageButtonBgMode: MENU_BAR_MODE_SOLID,
  pageButtonBgColor: '#409eff',
  pageButtonBgGradientDirection: 'to right',
  pageButtonBgGradientStartColor: '#60a5fa',
  pageButtonBgGradientMiddleColor: '#409eff',
  pageButtonBgGradientEndColor: '#2563eb',
  pageButtonBgAnimatedPreset: 'rainbow',
  pageButtonTextMode: MENU_BAR_MODE_SOLID,
  pageButtonTextColor: '#ffffff',
  pageButtonTextGradientDirection: 'to right',
  pageButtonTextGradientStartColor: '#ffffff',
  pageButtonTextGradientMiddleColor: '#eff6ff',
  pageButtonTextGradientEndColor: '#dbeafe',
  pageButtonTextAnimatedPreset: 'mint-shift',
  aiRightRailColor: '#e8f2ff',
  aiRightRailTextColor: '#526c84',
  aiSelectedMenuTextColor: '#1f4f82',
  aiConversationWindowColor: '#f4f9ff',
  aiConversationWindowTextColor: '#16324f',
  aiQuestionPanelColor: '#ffffff',
  aiQuestionPanelTextColor: '#26384b',
  aiChatComposerBgColor: '#ffffff',
  aiChatComposerTextColor: '#16324f',
  aiChatContentBgColor: '#f4f7fb',
  aiChatContentTextColor: '#1e2f42',
  aiUserMessageBgColor: '#173d67',
  aiUserMessageTextColor: '#ffffff',
  aiAssistantMessageBgColor: '#ffffff',
  aiAssistantMessageTextColor: '#1e2f42',
  aiUserMessageIcon: 'user',
  aiAssistantMessageIcon: 'chat-dot',
})

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const isEmbeddedFrame = getIsEmbeddedFrame()
const navigationTheme = reactive(loadNavigationTheme())
const activeThemeTab = ref(THEME_TAB_BACKGROUND)
const activeThemeEffectGroups = computed(() => THEME_EFFECT_GROUPS_BY_TAB[activeThemeTab.value] || [])
const hideLayoutTopbar = computed(() => Boolean(route.meta.hideLayoutTopbar))
const topbarClass = computed(() => ({
  'topbar--animated': navigationTheme.menuBarMode === MENU_BAR_MODE_ANIMATED,
}))
const layoutContentClass = computed(() => ({
  'layout-content--animated': getThemeEffectMode(navigationTheme, 'pageBg') === MENU_BAR_MODE_ANIMATED,
  'layout-content--button-bg-animated': getThemeEffectMode(navigationTheme, 'pageButtonBg') === MENU_BAR_MODE_ANIMATED,
  'layout-content--button-text-gradient': [MENU_BAR_MODE_GRADIENT, MENU_BAR_MODE_ANIMATED].includes(
    getThemeEffectMode(navigationTheme, 'pageButtonText')
  ),
  'layout-content--button-text-animated': getThemeEffectMode(navigationTheme, 'pageButtonText') === MENU_BAR_MODE_ANIMATED,
}))

const currentModule = computed(() => getModuleKeyFromPath(route.path))
const floatingAiControlViewport = reactive(getFloatingAiControlViewport())
const floatingAiControlPosition = reactive(loadFloatingAiControlPosition())
const floatingAiControlExpanded = ref(false)
const floatingAiControlDragging = ref(false)
const floatingAiControlSuppressClick = ref(false)
const floatingAiControlPinnedPath = ref([])
const floatingAiControlHoverPath = ref([])
let floatingAiControlDragState = null
let floatingAiControlSubmenuCloseTimer = null
let floatingAiControlSuppressHoverUntil = 0

const layoutStyle = computed(() => {
  const topbarBaseColor = getTopbarBaseColor(navigationTheme)
  const animatedPreset = getAnimatedPreset(navigationTheme.menuBarAnimatedPreset)
  const isAnimated = navigationTheme.menuBarMode === MENU_BAR_MODE_ANIMATED
  const menuButtonBgBaseColor = getThemeEffectBaseColor(
    navigationTheme,
    'menuButtonBg',
    DEFAULT_NAVIGATION_THEME.menuButtonBgColor
  )
  const menuButtonActiveBgBaseColor = getThemeEffectBaseColor(
    navigationTheme,
    'menuButtonActiveBg',
    DEFAULT_NAVIGATION_THEME.menuButtonActiveBgColor
  )
  const pageButtonBgBaseColor = getThemeEffectBaseColor(
    navigationTheme,
    'pageButtonBg',
    DEFAULT_NAVIGATION_THEME.pageButtonBgColor
  )

  return {
    '--topbar-height': `${APP_TOPBAR_HEIGHT}px`,
    '--topbar-background': buildTopbarBackground(navigationTheme),
    '--topbar-background-size': isAnimated ? animatedPreset.backgroundSize : '100% 100%',
    '--topbar-animation-duration': isAnimated ? animatedPreset.duration : '0s',
    '--topbar-base-color': topbarBaseColor,
    '--topbar-shadow-color': rgbaFromHex(topbarBaseColor, 0.18),
    ...buildThemeEffectVariables(
      navigationTheme,
      'menuButtonBg',
      'nav-pill-bg',
      DEFAULT_NAVIGATION_THEME.menuButtonBgColor
    ),
    ...buildThemeEffectVariables(
      navigationTheme,
      'menuButtonText',
      'nav-pill-text',
      DEFAULT_NAVIGATION_THEME.menuButtonTextColor
    ),
    '--nav-pill-hover-bg': buildThemeEffectHoverBackground(
      navigationTheme,
      'menuButtonBg',
      DEFAULT_NAVIGATION_THEME.menuButtonBgColor,
      topbarBaseColor
    ),
    '--nav-pill-hover-shadow-color': rgbaFromHex(menuButtonBgBaseColor, 0.18),
    ...buildThemeEffectVariables(
      navigationTheme,
      'menuButtonActiveBg',
      'nav-pill-active-bg',
      DEFAULT_NAVIGATION_THEME.menuButtonActiveBgColor
    ),
    ...buildThemeEffectVariables(
      navigationTheme,
      'menuButtonActiveText',
      'nav-pill-active-text',
      DEFAULT_NAVIGATION_THEME.menuButtonActiveTextColor
    ),
    '--nav-pill-active-shadow-color': rgbaFromHex(menuButtonActiveBgBaseColor, 0.3),
    ...buildThemeEffectVariables(
      navigationTheme,
      'pageBg',
      'page-bg',
      DEFAULT_NAVIGATION_THEME.pageBgColor
    ),
    ...buildThemeEffectVariables(
      navigationTheme,
      'pageButtonBg',
      'page-button-bg',
      DEFAULT_NAVIGATION_THEME.pageButtonBgColor
    ),
    ...buildThemeEffectVariables(
      navigationTheme,
      'pageButtonText',
      'page-button-text',
      DEFAULT_NAVIGATION_THEME.pageButtonTextColor
    ),
    '--page-button-border-color': pageButtonBgBaseColor,
    '--page-button-hover-bg': buildThemeEffectHoverBackground(
      navigationTheme,
      'pageButtonBg',
      DEFAULT_NAVIGATION_THEME.pageButtonBgColor,
      '#ffffff'
    ),
    '--page-button-active-bg': mixHexColor(pageButtonBgBaseColor, '#000000', 0.12),
    '--page-button-shadow-color': rgbaFromHex(pageButtonBgBaseColor, 0.22),
    '--page-button-focus-shadow-color': rgbaFromHex(pageButtonBgBaseColor, 0.24),
    '--ai-right-rail-bg': normalizeHexColor(
      navigationTheme.aiRightRailColor,
      DEFAULT_NAVIGATION_THEME.aiRightRailColor
    ),
    '--ai-right-rail-text-color': normalizeHexColor(
      navigationTheme.aiRightRailTextColor,
      DEFAULT_NAVIGATION_THEME.aiRightRailTextColor
    ),
    '--ai-selected-menu-text-color': normalizeHexColor(
      navigationTheme.aiSelectedMenuTextColor,
      DEFAULT_NAVIGATION_THEME.aiSelectedMenuTextColor
    ),
    '--ai-conversation-window-bg': normalizeHexColor(
      navigationTheme.aiConversationWindowColor,
      DEFAULT_NAVIGATION_THEME.aiConversationWindowColor
    ),
    '--ai-conversation-window-text-color': normalizeHexColor(
      navigationTheme.aiConversationWindowTextColor,
      DEFAULT_NAVIGATION_THEME.aiConversationWindowTextColor
    ),
    '--ai-question-panel-bg': normalizeHexColor(
      navigationTheme.aiQuestionPanelColor,
      DEFAULT_NAVIGATION_THEME.aiQuestionPanelColor
    ),
    '--ai-question-panel-text-color': normalizeHexColor(
      navigationTheme.aiQuestionPanelTextColor,
      DEFAULT_NAVIGATION_THEME.aiQuestionPanelTextColor
    ),
    '--ai-chat-composer-bg': normalizeHexColor(
      navigationTheme.aiChatComposerBgColor,
      DEFAULT_NAVIGATION_THEME.aiChatComposerBgColor
    ),
    '--ai-chat-composer-text-color': normalizeHexColor(
      navigationTheme.aiChatComposerTextColor,
      DEFAULT_NAVIGATION_THEME.aiChatComposerTextColor
    ),
    '--ai-chat-content-bg': normalizeHexColor(
      navigationTheme.aiChatContentBgColor,
      DEFAULT_NAVIGATION_THEME.aiChatContentBgColor
    ),
    '--ai-chat-content-text-color': normalizeHexColor(
      navigationTheme.aiChatContentTextColor,
      DEFAULT_NAVIGATION_THEME.aiChatContentTextColor
    ),
    '--ai-user-message-bg': normalizeHexColor(
      navigationTheme.aiUserMessageBgColor,
      DEFAULT_NAVIGATION_THEME.aiUserMessageBgColor
    ),
    '--ai-user-message-text-color': normalizeHexColor(
      navigationTheme.aiUserMessageTextColor,
      DEFAULT_NAVIGATION_THEME.aiUserMessageTextColor
    ),
    '--ai-assistant-message-bg': normalizeHexColor(
      navigationTheme.aiAssistantMessageBgColor,
      DEFAULT_NAVIGATION_THEME.aiAssistantMessageBgColor
    ),
    '--ai-assistant-message-text-color': normalizeHexColor(
      navigationTheme.aiAssistantMessageTextColor,
      DEFAULT_NAVIGATION_THEME.aiAssistantMessageTextColor
    ),
  }
})

const activeMenuPath = computed(() => {
  if (route.path.startsWith('/manual-testcases')) {
    return getManualTestcasePrimaryMenuPathByRoute(route)
  }

  return route.path
})

const currentModuleMenuItems = computed(() => getModuleMenuItems(currentModule.value, userStore.hasPermissionCode))
const moduleSwitcherItems = computed(() => getVisibleModuleSwitcherItems(userStore.hasPermissionCode))
const brandLabel = computed(() => (
  currentModule.value === 'manual-testcases' ? '思源质量平台' : 'AIOps'
))
const filterFloatingMenuChildren = children => (children || []).filter(item => (
  !item.permissionCodes || hasPermissionAccess(item.permissionCodes, userStore.hasPermissionCode)
))
const showTopbarModuleMenu = computed(() => (
  !showFloatingAiControl.value ||
  currentModule.value === 'manual-testcases'
))
const hideFloatingAiControlForRoute = computed(() => (
  route.path === '/manual-testcases/list' &&
  String(route.query?.tab || '') === 'quality-knowledge-assistant'
))
const showFloatingAiControl = computed(() => (
  !isEmbeddedFrame &&
  !hideFloatingAiControlForRoute.value &&
  (
    route.meta.showFloatingAiControl ||
    (
      !hideLayoutTopbar.value &&
      currentModule.value === 'manual-testcases'
    )
  )
))
const shouldAnchorFloatingAiControlToProductHero = computed(() => false)
const floatingUsernameLabel = computed(() => userStore.user?.username || DEFAULT_USERNAME)
const floatingAiControlStyle = computed(() => ({
  left: `${floatingAiControlPosition.x}px`,
  top: `${floatingAiControlPosition.y}px`,
}))
const floatingAiRadialViewBox = computed(() => {
  const half = AI_FLOATING_RADIAL_VIEWBOX_SIZE / 2
  return `${-half} ${-half} ${AI_FLOATING_RADIAL_VIEWBOX_SIZE} ${AI_FLOATING_RADIAL_VIEWBOX_SIZE}`
})
const floatingAiControlItems = computed(() => {
  const manualTestcaseMenuItems = getModuleMenuItems('manual-testcases', userStore.hasPermissionCode)
  const moduleItemsByKeyValue = new Map(moduleSwitcherItems.value.map(item => [item.key, item]))
  const manualModule = moduleItemsByKeyValue.get('manual-testcases')
  const desiredItems = [
    manualModule && {
      key: 'module-manual-testcases',
      label: manualModule.label,
      path: manualModule.path || '/manual-testcases/list',
      pathPrefix: '/manual-testcases',
      children: manualTestcaseMenuItems.map(item => ({
        key: `manual-${item.key}`,
        label: item.label,
        path: item.path,
        permissionCodes: item.permissionCodes,
      })).filter(item => !item.permissionCodes || hasPermissionAccess(item.permissionCodes, userStore.hasPermissionCode)),
    },
    {
      key: 'profile',
      label: floatingUsernameLabel.value,
      action: 'profile',
      children: [
        { key: 'profile-settings', label: PROFILE_LABEL, action: 'profile' },
        { key: 'profile-logout', label: LOGOUT_LABEL, action: 'logout' },
      ],
    },
  ].filter(Boolean)
  const primaryLayout = buildFloatingAiSectorLayout(desiredItems.length, 'primary')

  return desiredItems.map((item, index) => ({
    ...item,
    ...(primaryLayout[index] || primaryLayout[primaryLayout.length - 1]),
    labelLines: splitFloatingSectorLabel(item.label),
    active: isFloatingControlItemActive(item),
  }))
})
const activeFloatingMenuPath = computed(() => {
  const pinnedPath = normalizeFloatingMenuPath(floatingAiControlPinnedPath.value)
  return pinnedPath.length
    ? pinnedPath
    : normalizeFloatingMenuPath(floatingAiControlHoverPath.value)
})
const activeFloatingSubmenuKey = computed(() => (
  activeFloatingMenuPath.value[activeFloatingMenuPath.value.length - 1] || ''
))
const activeFloatingSubmenuItem = computed(() => (
  findFloatingMenuItemByPath(floatingAiControlItems.value, activeFloatingMenuPath.value) || null
))
const floatingAiRadialRings = computed(() => {
  const rings = []
  let parentPath = []
  let currentItems = floatingAiControlItems.value
  const activePath = activeFloatingMenuPath.value

  for (let level = 0; level < AI_FLOATING_MAX_RENDERED_MENU_LEVELS; level += 1) {
    if (!currentItems.length) {
      break
    }

    const layout = buildFloatingAiSectorLayout(currentItems.length, level)
    const ringItems = currentItems.map((item, index) => {
      const itemMenuPath = [...parentPath, item.key]
      const sectorLayout = layout[index] || layout[layout.length - 1]
      return {
        ...item,
        level,
        parentPath,
        parentKey: parentPath[parentPath.length - 1] || '',
        menuPath: itemMenuPath,
        pathKey: buildFloatingMenuPathKey(itemMenuPath),
        ...sectorLayout,
        labelPathId: sectorLayout.labelPath ? buildFloatingSectorLabelPathId(itemMenuPath) : '',
        labelLines: splitFloatingSectorLabel(item.label),
        active: isFloatingControlItemActive(item),
      }
    })

    rings.push({
      key: `ring-${level}-${buildFloatingMenuPathKey(parentPath) || 'root'}`,
      level,
      items: ringItems,
    })

    if (!floatingAiControlExpanded.value) {
      break
    }

    const nextKey = activePath[level]
    if (!nextKey) {
      break
    }

    const nextParent = ringItems.find(item => item.key === nextKey && hasFloatingSubmenu(item))
    if (!nextParent) {
      break
    }

    parentPath = nextParent.menuPath
    currentItems = nextParent.children || []
  }

  return rings
})
const floatingAiSectorLabelPaths = computed(() => (
  floatingAiRadialRings.value.flatMap(ring => (
    ring.items
      .filter(item => item.labelPath && item.labelPathId)
      .map(item => ({
        id: item.labelPathId,
        d: item.labelPath,
      }))
  ))
))
const floatingAiSubmenuItems = computed(() => {
  const submenuRing = floatingAiRadialRings.value.find(ring => ring.level === 1)
  return submenuRing?.items || []
})

const isMenuItemActive = menuPath => (
  activeMenuPath.value === menuPath
)

const isFloatingControlItemActive = item => {
  if (item.children?.some(child => isFloatingControlItemActive(child))) {
    return true
  }

  if (item.match) {
    if (route.path !== item.match.path) {
      return false
    }

    const queryValue = getRouteQueryValue(item.match.queryKey)
    return queryValue
      ? queryValue === item.match.queryValue
      : Boolean(item.match.defaultWhenMissing)
  }

  if (item.action === 'home') {
    return route.path === '/home'
  }

  if (item.action === 'profile') {
    return route.path === '/profile'
  }

  if (item.action === 'logout') {
    return false
  }

  return Boolean(item.path && (route.fullPath === item.path || isMenuItemActive(getPathWithoutQuery(item.path))))
}

const getNavPillClass = menuPath => {
  const isActive = isMenuItemActive(menuPath)
  const backgroundMode = getThemeEffectMode(
    navigationTheme,
    isActive ? 'menuButtonActiveBg' : 'menuButtonBg'
  )
  const textMode = getThemeEffectMode(
    navigationTheme,
    isActive ? 'menuButtonActiveText' : 'menuButtonText'
  )

  return {
    active: isActive,
    'nav-pill--bg-animated': backgroundMode === MENU_BAR_MODE_ANIMATED,
    'nav-pill--text-gradient': [MENU_BAR_MODE_GRADIENT, MENU_BAR_MODE_ANIMATED].includes(textMode),
    'nav-pill--text-animated': textMode === MENU_BAR_MODE_ANIMATED,
  }
}

const goToPath = path => {
  if (!path || route.fullPath === path) {
    return
  }

  if (String(path).startsWith('/manual-testcases')) {
    router.push(buildManualTestcaseLocationFromPath(path, route.query))
    return
  }

  router.push(path)
}

const goHome = () => {
  if (route.path !== '/home') {
    router.push('/home')
  }
}

const goBrandHome = () => {
  if (currentModule.value === 'manual-testcases') {
    goToPath('/manual-testcases/list?tab=requirement-overview')
    return
  }

  goHome()
}

const handleFloatingSectorClick = item => {
  if (item.disabled) {
    return
  }

  if (hasFloatingSubmenu(item)) {
    toggleFloatingSubmenuPin(item.menuPath)
    return
  }

  handleFloatingLeafItemClick(item, {
    preserveSubmenu: Boolean(floatingAiControlPinnedPath.value.length && item.level > 0),
  })
  if (!floatingAiControlPinnedPath.value.length && item.level > 0) {
    floatingAiControlHoverPath.value = []
  }
}

const handleFloatingLeafItemClick = (item, options = {}) => {
  if (!options.preserveSubmenu && !hasFloatingSubmenu(item)) {
    floatingAiControlPinnedPath.value = []
    floatingAiControlHoverPath.value = []
  }

  if (item.action === 'home') {
    goHome()
    return
  }

  if (item.action === 'profile') {
    handleUserCommand('profile')
    return
  }

  if (item.action === 'logout') {
    handleUserCommand('logout')
    return
  }

  if (item.path) {
    goToPath(item.path)
  }
}

const handleFloatingCoreClick = () => {
  if (floatingAiControlSuppressClick.value) {
    return
  }

  const nextExpanded = !floatingAiControlExpanded.value
  clearFloatingSubmenus()
  if (nextExpanded) {
    setFloatingAiControlPosition(floatingAiControlPosition.x, floatingAiControlPosition.y, false, {
      reserveExpandedRadius: true,
      ringCount: AI_FLOATING_SAFE_RING_COUNT,
    })
  }
  floatingAiControlExpanded.value = nextExpanded
  if (nextExpanded) {
    suppressFloatingSubmenuHover()
  }
}

const handleFloatingSectorEnter = item => {
  if (!floatingAiControlExpanded.value) {
    return
  }

  cancelFloatingSubmenuClose()
  if (!hasFloatingSubmenu(item)) {
    if (!floatingAiControlPinnedPath.value.length && item.parentPath?.length) {
      floatingAiControlHoverPath.value = item.parentPath
    }
    return
  }

  if (item.level === 0 && isFloatingSubmenuHoverSuppressed()) {
    return
  }

  if (
    floatingAiControlPinnedPath.value.length &&
    !areFloatingMenuPathsEqual(floatingAiControlPinnedPath.value, item.menuPath)
  ) {
    floatingAiControlPinnedPath.value = []
  }
  floatingAiControlHoverPath.value = item.menuPath
  setFloatingAiControlPosition(floatingAiControlPosition.x, floatingAiControlPosition.y, false, {
    reserveExpandedRadius: true,
    ringCount: AI_FLOATING_SAFE_RING_COUNT,
  })
}

const handleFloatingSectorLeave = item => {
  if (!hasFloatingSubmenu(item) && !item.parentPath?.length) {
    return
  }

  scheduleFloatingSubmenuClose(hasFloatingSubmenu(item) ? item.menuPath : item.parentPath)
}

const toggleFloatingSubmenuPin = path => {
  cancelFloatingSubmenuClose()
  const nextPath = normalizeFloatingMenuPath(path)
  if (areFloatingMenuPathsEqual(floatingAiControlPinnedPath.value, nextPath)) {
    floatingAiControlPinnedPath.value = []
    floatingAiControlHoverPath.value = []
    return
  }

  floatingAiControlPinnedPath.value = nextPath
  floatingAiControlHoverPath.value = nextPath
  setFloatingAiControlPosition(floatingAiControlPosition.x, floatingAiControlPosition.y, false, {
    reserveExpandedRadius: true,
    ringCount: AI_FLOATING_SAFE_RING_COUNT,
  })
}

const scheduleFloatingSubmenuClose = path => {
  const targetPath = normalizeFloatingMenuPath(path)
  if (!targetPath.length || areFloatingMenuPathsEqual(floatingAiControlPinnedPath.value, targetPath)) {
    return
  }

  cancelFloatingSubmenuClose()
  floatingAiControlSubmenuCloseTimer = window.setTimeout(() => {
    if (
      !floatingAiControlPinnedPath.value.length &&
      isFloatingMenuPathPrefix(targetPath, floatingAiControlHoverPath.value)
    ) {
      floatingAiControlHoverPath.value = []
    }
  }, 160)
}

const cancelFloatingSubmenuClose = () => {
  if (floatingAiControlSubmenuCloseTimer) {
    window.clearTimeout(floatingAiControlSubmenuCloseTimer)
    floatingAiControlSubmenuCloseTimer = null
  }
}

const clearFloatingSubmenus = () => {
  cancelFloatingSubmenuClose()
  floatingAiControlPinnedPath.value = []
  floatingAiControlHoverPath.value = []
}

const suppressFloatingSubmenuHover = () => {
  floatingAiControlSuppressHoverUntil = Date.now() + AI_FLOATING_HOVER_SUPPRESSION_MS
}

const isFloatingSubmenuHoverSuppressed = () => Date.now() < floatingAiControlSuppressHoverUntil

const hasFloatingSubmenu = item => Array.isArray(item?.children) && item.children.length > 0

function normalizeFloatingMenuPath(path) {
  return Array.isArray(path)
    ? path.filter(value => typeof value === 'string' && value)
    : []
}

function buildFloatingMenuPathKey(path) {
  return normalizeFloatingMenuPath(path).join('__')
}

function areFloatingMenuPathsEqual(firstPath, secondPath) {
  const first = normalizeFloatingMenuPath(firstPath)
  const second = normalizeFloatingMenuPath(secondPath)
  return first.length === second.length && first.every((value, index) => value === second[index])
}

function isFloatingMenuPathPrefix(prefixPath, path) {
  const prefix = normalizeFloatingMenuPath(prefixPath)
  const target = normalizeFloatingMenuPath(path)
  return prefix.length <= target.length && prefix.every((value, index) => value === target[index])
}

function findFloatingMenuItemByPath(items, path) {
  const normalizedPath = normalizeFloatingMenuPath(path)
  if (!normalizedPath.length) {
    return null
  }

  let currentItems = items || []
  let currentItem = null
  for (const key of normalizedPath) {
    currentItem = currentItems.find(item => item.key === key) || null
    if (!currentItem) {
      return null
    }
    currentItems = currentItem.children || []
  }

  return currentItem
}

const getRouteQueryValue = key => {
  const value = route.query[key]
  return Array.isArray(value) ? value[0] : value
}

const getPathWithoutQuery = path => String(path || '').split('?')[0]

const handleFloatingCorePointerDown = event => {
  startFloatingAiControlDrag(event)
}

const startFloatingAiControlDrag = event => {
  if (event.button !== undefined && event.button !== 0) {
    return
  }

  floatingAiControlDragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: floatingAiControlPosition.x,
    originY: floatingAiControlPosition.y,
    moved: false,
    target: event.currentTarget,
  }
  floatingAiControlDragging.value = true
  floatingAiControlSuppressClick.value = false
  event.currentTarget?.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleFloatingAiControlMove)
  window.addEventListener('pointerup', stopFloatingAiControlDrag, { once: true })
  window.addEventListener('pointercancel', stopFloatingAiControlDrag, { once: true })
}

const handleFloatingAiControlMove = event => {
  if (!floatingAiControlDragState) {
    return
  }

  event.preventDefault()
  const deltaX = event.clientX - floatingAiControlDragState.startX
  const deltaY = event.clientY - floatingAiControlDragState.startY
  if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
    floatingAiControlDragState.moved = true
  }

  setFloatingAiControlPosition(
    floatingAiControlDragState.originX + deltaX,
    floatingAiControlDragState.originY + deltaY,
    false,
    {
      reserveExpandedRadius: floatingAiControlExpanded.value,
      ringCount: AI_FLOATING_SAFE_RING_COUNT,
    }
  )
}

const stopFloatingAiControlDrag = event => {
  window.removeEventListener('pointermove', handleFloatingAiControlMove)
  window.removeEventListener('pointerup', stopFloatingAiControlDrag)
  window.removeEventListener('pointercancel', stopFloatingAiControlDrag)

  if (floatingAiControlDragState?.target && floatingAiControlDragState.pointerId !== undefined) {
    floatingAiControlDragState.target.releasePointerCapture?.(floatingAiControlDragState.pointerId)
  }

  if (floatingAiControlDragState?.moved) {
    floatingAiControlSuppressClick.value = true
    window.setTimeout(() => {
      floatingAiControlSuppressClick.value = false
    }, 0)
  }

  setFloatingAiControlPosition(floatingAiControlPosition.x, floatingAiControlPosition.y, true, {
    source: AI_FLOATING_POSITION_SOURCE_MANUAL,
    reserveExpandedRadius: floatingAiControlExpanded.value,
    ringCount: AI_FLOATING_SAFE_RING_COUNT,
  })
  floatingAiControlDragState = null
  floatingAiControlDragging.value = false
}

const switchToModule = moduleKey => {
  const targetModule = moduleSwitcherItems.value.find(item => item.key === moduleKey)

  if (!targetModule?.path) {
    ElMessage.info(MODULE_IN_DEVELOPMENT_MESSAGE)
    return
  }

  goToPath(targetModule.path)
}

const handleHomeCommand = command => {
  if (command === 'home') {
    goHome()
    return
  }

  if (typeof command === 'string' && command.startsWith('module:')) {
    switchToModule(command.slice('module:'.length))
  }
}

const handleUserCommand = command => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success(LOGOUT_SUCCESS_MESSAGE)
    router.push('/login')
    return
  }

  if (command === 'profile') {
    router.push('/profile')
  }
}

onMounted(() => {
  syncFloatingAiControlPositionForRoute()
  window.addEventListener('resize', handleFloatingAiControlResize)
})

onBeforeUnmount(() => {
  cancelFloatingSubmenuClose()
  window.removeEventListener('resize', handleFloatingAiControlResize)
  window.removeEventListener('pointermove', handleFloatingAiControlMove)
  window.removeEventListener('pointerup', stopFloatingAiControlDrag)
  window.removeEventListener('pointercancel', stopFloatingAiControlDrag)
})

watch(
  navigationTheme,
  value => {
    persistNavigationTheme(value)
  },
  { deep: true }
)

watch(
  () => [route.path, getFloatingAiControlLayoutMode(), showFloatingAiControl.value],
  ([path, layoutMode, visible], previous = []) => {
    if (!visible) {
      return
    }

    const [, previousLayoutMode, wasVisible] = previous
    if (layoutMode !== previousLayoutMode || (path === '/home' && !wasVisible)) {
      syncFloatingAiControlPositionForRoute()
      return
    }

    syncFloatingAiControlPositionForRoute()
  },
  { immediate: true }
)

function loadFloatingAiControlPosition() {
  const fallback = getFloatingAiControlFallbackPosition()
  const savedValue = getStoredFloatingAiControlPosition()
  if (shouldUseStoredFloatingAiControlPosition(savedValue)) {
    return clampFloatingAiControlPosition(Number(savedValue.x), Number(savedValue.y))
  }

  return fallback
}

function getStoredFloatingAiControlPosition() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const savedValue = JSON.parse(localStorage.getItem(AI_FLOATING_CONTROL_STORAGE_KEY) || 'null')
    if (
      savedValue &&
      Number.isFinite(Number(savedValue.x)) &&
      Number.isFinite(Number(savedValue.y)) &&
      savedValue.layoutMode === getFloatingAiControlLayoutMode() &&
      Date.now() - Number(savedValue.savedAt || 0) < AI_FLOATING_SAVED_POSITION_MAX_AGE_MS
    ) {
      return savedValue
    }
  } catch (error) {
    localStorage.removeItem(AI_FLOATING_CONTROL_STORAGE_KEY)
  }

  return null
}

function shouldUseStoredFloatingAiControlPosition(savedValue) {
  if (!savedValue) {
    return false
  }

  if (isFloatingAiControlProductPage()) {
    return savedValue.source === AI_FLOATING_POSITION_SOURCE_MANUAL
  }

  return true
}

function isFloatingAiControlProductPage() {
  return false
}

function getFloatingAiControlFallbackPosition(options = {}) {
  if (typeof window === 'undefined') {
    return { x: 24, y: 120 }
  }

  const controlSize = getFloatingAiControlSizeForViewport(window.innerWidth)
  if (getFloatingAiControlLayoutMode() === 'immersive') {
    return clampFloatingAiControlPosition(
      window.innerWidth - controlSize - 24,
      window.innerHeight - controlSize - 24,
      options
    )
  }

  const defaultX = window.innerWidth <= AI_FLOATING_MOBILE_BREAKPOINT
    ? (window.innerWidth - controlSize) / 2
    : Math.max(32, window.innerWidth - 300)

  return clampFloatingAiControlPosition(
    defaultX,
    APP_TOPBAR_HEIGHT + 28,
    options
  )
}

function syncFloatingAiControlPositionForRoute() {
  nextTick(() => {
    if (!showFloatingAiControl.value) {
      return
    }

    const savedValue = getStoredFloatingAiControlPosition()
    if (shouldUseStoredFloatingAiControlPosition(savedValue)) {
      setFloatingAiControlPosition(Number(savedValue.x), Number(savedValue.y), false, {
        reserveExpandedRadius: floatingAiControlExpanded.value,
        ringCount: AI_FLOATING_SAFE_RING_COUNT,
      })
      return
    }

    if (shouldAnchorFloatingAiControlToProductHero.value) {
      window.requestAnimationFrame(() => {
        const nextPosition = getFloatingAiProductComposerPosition()
        setFloatingAiControlPosition(nextPosition.x, nextPosition.y, false, {
          reserveExpandedRadius: true,
          ringCount: AI_FLOATING_SAFE_RING_COUNT,
        })
      })
      return
    }

    setFloatingAiControlPosition(floatingAiControlPosition.x, floatingAiControlPosition.y, false)
  })
}

function getFloatingAiControlLayoutMode() {
  return hideLayoutTopbar.value ? 'immersive' : 'standard'
}

function clampFloatingAiControlPosition(x, y, options = {}) {
  if (typeof window === 'undefined') {
    return { x, y }
  }

  const controlSize = getFloatingAiControlSizeForViewport(window.innerWidth)
  const minTop = hideLayoutTopbar.value ? AI_FLOATING_CONTROL_MARGIN : APP_TOPBAR_HEIGHT + AI_FLOATING_CONTROL_MARGIN
  let minX = AI_FLOATING_CONTROL_MARGIN
  let minY = minTop
  let maxX = Math.max(minX, window.innerWidth - controlSize - AI_FLOATING_CONTROL_MARGIN)
  let maxY = Math.max(minY, window.innerHeight - controlSize - AI_FLOATING_CONTROL_MARGIN)

  if (options.reserveExpandedRadius) {
    const radius = getFloatingAiExpandedRadiusForViewport(
      window.innerWidth,
      options.ringCount || getFloatingAiRenderedRingCount()
    )
    const centerMargin = Math.max(AI_FLOATING_MENU_EDGE_GAP, AI_FLOATING_CONTROL_MARGIN)
    const centerMinX = radius + centerMargin
    const centerMaxX = Math.max(centerMinX, window.innerWidth - radius - centerMargin)
    const centerMinY = radius + centerMargin + (hideLayoutTopbar.value ? 0 : APP_TOPBAR_HEIGHT)
    const centerMaxY = Math.max(centerMinY, window.innerHeight - radius - centerMargin)
    minX = Math.max(minX, centerMinX - controlSize / 2)
    maxX = Math.min(maxX, centerMaxX - controlSize / 2)
    minY = Math.max(minY, centerMinY - controlSize / 2)
    maxY = Math.min(maxY, centerMaxY - controlSize / 2)
  }

  return {
    x: Math.min(Math.max(minX, x), Math.max(minX, maxX)),
    y: Math.min(Math.max(minY, y), Math.max(minY, maxY)),
  }
}

function setFloatingAiControlPosition(x, y, persist = true, options = {}) {
  const nextPosition = clampFloatingAiControlPosition(x, y, options)
  floatingAiControlPosition.x = nextPosition.x
  floatingAiControlPosition.y = nextPosition.y
  if (persist) {
    localStorage.setItem(AI_FLOATING_CONTROL_STORAGE_KEY, JSON.stringify({
      ...nextPosition,
      layoutMode: getFloatingAiControlLayoutMode(),
      source: options.source || 'auto',
      savedAt: Date.now(),
    }))
  }
}

function handleFloatingAiControlResize() {
  const nextViewport = getFloatingAiControlViewport()
  floatingAiControlViewport.width = nextViewport.width
  floatingAiControlViewport.height = nextViewport.height
  syncFloatingAiControlPositionForRoute()
}

function getFloatingAiProductComposerPosition() {
  if (typeof window === 'undefined') {
    return getFloatingAiControlFallbackPosition()
  }

  const controlSize = getFloatingAiControlSizeForViewport(window.innerWidth)
  const composer = document.querySelector(AI_PRODUCT_COMPOSER_FLOATING_ANCHOR_SELECTOR)
  if (!composer) {
    return getFloatingAiControlFallbackPosition({
      reserveExpandedRadius: true,
      ringCount: AI_FLOATING_SAFE_RING_COUNT,
    })
  }

  const rect = composer.getBoundingClientRect()
  if (!rect.width || !rect.height) {
    return getFloatingAiControlFallbackPosition({
      reserveExpandedRadius: true,
      ringCount: AI_FLOATING_SAFE_RING_COUNT,
    })
  }

  const nextX = rect.right - controlSize * 0.34
  const nextY = rect.top - controlSize * 0.82
  return clampFloatingAiControlPosition(nextX, nextY, {
    reserveExpandedRadius: true,
    ringCount: AI_FLOATING_SAFE_RING_COUNT,
  })
}

function getIsEmbeddedFrame() {
  if (typeof window === 'undefined') {
    return false
  }

  try {
    return window.self !== window.top
  } catch (error) {
    return true
  }
}

function getFloatingAiControlViewport() {
  if (typeof window === 'undefined') {
    return { width: 1440, height: 900 }
  }

  return {
    width: window.innerWidth,
    height: window.innerHeight,
  }
}

function getFloatingAiControlSizeForViewport(width) {
  return width <= AI_FLOATING_MOBILE_BREAKPOINT
    ? AI_FLOATING_CONTROL_MOBILE_SIZE
    : AI_FLOATING_CONTROL_SIZE
}

function getFloatingAiRenderedRingCount() {
  return Math.max(1, floatingAiRadialRings.value?.length || 1)
}

function getFloatingAiExpandedRadiusForViewport(width, ringCount = AI_FLOATING_SAFE_RING_COUNT) {
  const displayScale = getFloatingAiRadialDisplayScaleForViewport(width)
  return getFloatingAiRingRadiiByWidth(width, Math.max(0, ringCount - 1)).outer * displayScale
}

function getFloatingAiRadialDisplayScaleForViewport(width) {
  const displaySize = width <= AI_FLOATING_MOBILE_BREAKPOINT
    ? AI_FLOATING_MOBILE_RADIAL_DISPLAY_SIZE
    : AI_FLOATING_RADIAL_DISPLAY_SIZE
  return displaySize / AI_FLOATING_RADIAL_VIEWBOX_SIZE
}

function getFloatingAiRingRadiiByWidth(width, ring = 0) {
  const mobile = width <= AI_FLOATING_MOBILE_BREAKPOINT
  if (ring === 'primary') {
    ring = 0
  } else if (ring === 'submenu') {
    ring = 1
  }

  if (ring >= 2) {
    return mobile
      ? { inner: AI_FLOATING_MOBILE_TERTIARY_INNER_RADIUS, outer: AI_FLOATING_MOBILE_TERTIARY_OUTER_RADIUS }
      : { inner: AI_FLOATING_TERTIARY_INNER_RADIUS, outer: AI_FLOATING_TERTIARY_OUTER_RADIUS }
  }

  if (ring === 1) {
    return mobile
      ? { inner: AI_FLOATING_MOBILE_SUBMENU_INNER_RADIUS, outer: AI_FLOATING_MOBILE_SUBMENU_OUTER_RADIUS }
      : { inner: AI_FLOATING_SUBMENU_INNER_RADIUS, outer: AI_FLOATING_SUBMENU_OUTER_RADIUS }
  }

  return mobile
    ? { inner: AI_FLOATING_MOBILE_PRIMARY_INNER_RADIUS, outer: AI_FLOATING_MOBILE_PRIMARY_OUTER_RADIUS }
    : { inner: AI_FLOATING_PRIMARY_INNER_RADIUS, outer: AI_FLOATING_PRIMARY_OUTER_RADIUS }
}

function getFloatingAiRingRadii(ring = 0) {
  const mobile = floatingAiControlViewport.width <= AI_FLOATING_MOBILE_BREAKPOINT
  if (ring === 'primary') {
    ring = 0
  } else if (ring === 'submenu') {
    ring = 1
  }

  if (ring >= 2) {
    return mobile
      ? { inner: AI_FLOATING_MOBILE_TERTIARY_INNER_RADIUS, outer: AI_FLOATING_MOBILE_TERTIARY_OUTER_RADIUS }
      : { inner: AI_FLOATING_TERTIARY_INNER_RADIUS, outer: AI_FLOATING_TERTIARY_OUTER_RADIUS }
  }

  if (ring === 1) {
    return mobile
      ? { inner: AI_FLOATING_MOBILE_SUBMENU_INNER_RADIUS, outer: AI_FLOATING_MOBILE_SUBMENU_OUTER_RADIUS }
      : { inner: AI_FLOATING_SUBMENU_INNER_RADIUS, outer: AI_FLOATING_SUBMENU_OUTER_RADIUS }
  }

  return mobile
    ? { inner: AI_FLOATING_MOBILE_PRIMARY_INNER_RADIUS, outer: AI_FLOATING_MOBILE_PRIMARY_OUTER_RADIUS }
    : { inner: AI_FLOATING_PRIMARY_INNER_RADIUS, outer: AI_FLOATING_PRIMARY_OUTER_RADIUS }
}

function buildFloatingAiSectorLayout(itemCount = 1, ring = 0) {
  const count = Math.max(1, itemCount)
  const radii = getFloatingAiRingRadii(ring)
  const step = (Math.PI * 2) / count
  const startOffset = -Math.PI / 2
  return Array.from({ length: count }, (_, index) => {
    const startAngle = startOffset + step * index + AI_FLOATING_SECTOR_GAP_RADIANS
    const endAngle = startOffset + step * (index + 1) - AI_FLOATING_SECTOR_GAP_RADIANS
    const midAngle = (startAngle + endAngle) / 2
    const labelRadius = (radii.inner + radii.outer) / 2
    const labelX = Math.round(Math.cos(midAngle) * labelRadius)
    const labelY = Math.round(Math.sin(midAngle) * labelRadius)
    const labelPath = shouldUseFloatingSectorLabelPath(ring)
      ? buildFloatingAiLabelArcPath(
        labelRadius,
        startAngle + AI_FLOATING_LABEL_ARC_PADDING_RADIANS,
        endAngle - AI_FLOATING_LABEL_ARC_PADDING_RADIANS,
        midAngle
      )
      : ''
    return {
      startAngle,
      endAngle,
      midAngle,
      innerRadius: radii.inner,
      outerRadius: radii.outer,
      sectorPath: buildFloatingAiSectorPath(radii.inner, radii.outer, startAngle, endAngle),
      labelX,
      labelY,
      labelPath,
      labelLines: [],
    }
  })
}

function buildFloatingAiSectorPath(innerRadius, outerRadius, startAngle, endAngle) {
  const outerStart = polarToCartesian(outerRadius, startAngle)
  const outerEnd = polarToCartesian(outerRadius, endAngle)
  const innerEnd = polarToCartesian(innerRadius, endAngle)
  const innerStart = polarToCartesian(innerRadius, startAngle)
  const largeArcFlag = endAngle - startAngle > Math.PI ? 1 : 0
  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x} ${innerStart.y}`,
    'Z',
  ].join(' ')
}

function buildFloatingAiLabelArcPath(radius, startAngle, endAngle, midAngle) {
  const reverse = shouldReverseFloatingLabelPath(midAngle)
  const pathStart = polarToCartesian(radius, reverse ? endAngle : startAngle)
  const pathEnd = polarToCartesian(radius, reverse ? startAngle : endAngle)
  const largeArcFlag = Math.abs(endAngle - startAngle) > Math.PI ? 1 : 0
  const sweepFlag = reverse ? 0 : 1
  return [
    `M ${pathStart.x} ${pathStart.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} ${sweepFlag} ${pathEnd.x} ${pathEnd.y}`,
  ].join(' ')
}

function polarToCartesian(radius, angle) {
  return {
    x: Number((Math.cos(angle) * radius).toFixed(2)),
    y: Number((Math.sin(angle) * radius).toFixed(2)),
  }
}

function shouldUseFloatingSectorLabelPath(ring) {
  if (ring === 'primary') {
    return true
  }
  if (ring === 'submenu') {
    return true
  }
  return Number(ring) <= 1
}

function shouldReverseFloatingLabelPath(midAngle) {
  const tangentDegrees = normalizeFloatingLabelDegrees((midAngle * 180) / Math.PI + 90)
  return tangentDegrees > 90 || tangentDegrees < -90
}

function normalizeFloatingLabelDegrees(degrees) {
  return ((((degrees + 180) % 360) + 360) % 360) - 180
}

function buildFloatingSectorLabelPathId(path) {
  const pathKey = buildFloatingMenuPathKey(path) || 'root'
  return `ai-floating-sector-label-${pathKey.replace(/[^a-zA-Z0-9_-]/g, '-')}`
}

function splitFloatingSectorLabel(label) {
  const text = String(label || '').trim()
  if (!text) {
    return ['']
  }
  const chars = Array.from(text)
  const first = chars.slice(0, 4).join('')
  const second = chars.slice(4, 8).join('')
  return second ? [first, second] : [first]
}

function getFloatingSectorLabelDy(lines, index) {
  const count = Array.isArray(lines) ? lines.length : 1
  if (count <= 1) {
    return index === 0 ? '0' : '1.1em'
  }
  return index === 0 ? '-0.55em' : '1.1em'
}

function resetNavigationTheme() {
  applyNavigationTheme(DEFAULT_NAVIGATION_THEME)
}

function applySolidPreset(preset) {
  applyNavigationTheme({
    ...navigationTheme,
    menuBarMode: MENU_BAR_MODE_SOLID,
    menuBarColor: preset.color,
  })
}

function applyGradientPreset(preset) {
  applyNavigationTheme({
    ...navigationTheme,
    menuBarMode: MENU_BAR_MODE_GRADIENT,
    menuBarGradientDirection: preset.direction,
    menuBarGradientStartColor: preset.colors[0],
    menuBarGradientMiddleColor: preset.colors[1],
    menuBarGradientEndColor: preset.colors[2],
  })
}

function applyAnimatedPreset(preset) {
  applyNavigationTheme({
    ...navigationTheme,
    menuBarMode: MENU_BAR_MODE_ANIMATED,
    menuBarAnimatedPreset: preset.key,
  })
}

function applyEffectSolidPreset(effectKey, preset) {
  const colorKey = getThemeEffectFieldKey(effectKey, 'Color')
  const modeKey = getThemeEffectFieldKey(effectKey, 'Mode')

  applyNavigationTheme({
    ...navigationTheme,
    [modeKey]: MENU_BAR_MODE_SOLID,
    [colorKey]: preset.color,
  })
}

function applyEffectGradientPreset(effectKey, preset) {
  const modeKey = getThemeEffectFieldKey(effectKey, 'Mode')
  const directionKey = getThemeEffectFieldKey(effectKey, 'GradientDirection')
  const startKey = getThemeEffectFieldKey(effectKey, 'GradientStartColor')
  const middleKey = getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')
  const endKey = getThemeEffectFieldKey(effectKey, 'GradientEndColor')

  applyNavigationTheme({
    ...navigationTheme,
    [modeKey]: MENU_BAR_MODE_GRADIENT,
    [directionKey]: preset.direction,
    [startKey]: preset.colors[0],
    [middleKey]: preset.colors[1],
    [endKey]: preset.colors[2],
  })
}

function applyEffectAnimatedPreset(effectKey, preset) {
  const modeKey = getThemeEffectFieldKey(effectKey, 'Mode')
  const animatedPresetKey = getThemeEffectFieldKey(effectKey, 'AnimatedPreset')

  applyNavigationTheme({
    ...navigationTheme,
    [modeKey]: MENU_BAR_MODE_ANIMATED,
    [animatedPresetKey]: preset.key,
  })
}

function isSolidPresetActive(preset) {
  return navigationTheme.menuBarMode === MENU_BAR_MODE_SOLID && navigationTheme.menuBarColor === preset.color
}

function isGradientPresetActive(preset) {
  return (
    navigationTheme.menuBarMode === MENU_BAR_MODE_GRADIENT
    && navigationTheme.menuBarGradientStartColor === preset.colors[0]
    && navigationTheme.menuBarGradientMiddleColor === preset.colors[1]
    && navigationTheme.menuBarGradientEndColor === preset.colors[2]
  )
}

function isAnimatedPresetActive(preset) {
  return navigationTheme.menuBarMode === MENU_BAR_MODE_ANIMATED && navigationTheme.menuBarAnimatedPreset === preset.key
}

function isEffectSolidPresetActive(effectKey, preset) {
  return (
    getThemeEffectMode(navigationTheme, effectKey) === MENU_BAR_MODE_SOLID
    && navigationTheme[getThemeEffectFieldKey(effectKey, 'Color')] === preset.color
  )
}

function isEffectGradientPresetActive(effectKey, preset) {
  return (
    getThemeEffectMode(navigationTheme, effectKey) === MENU_BAR_MODE_GRADIENT
    && navigationTheme[getThemeEffectFieldKey(effectKey, 'GradientStartColor')] === preset.colors[0]
    && navigationTheme[getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')] === preset.colors[1]
    && navigationTheme[getThemeEffectFieldKey(effectKey, 'GradientEndColor')] === preset.colors[2]
  )
}

function isEffectAnimatedPresetActive(effectKey, preset) {
  return (
    getThemeEffectMode(navigationTheme, effectKey) === MENU_BAR_MODE_ANIMATED
    && navigationTheme[getThemeEffectFieldKey(effectKey, 'AnimatedPreset')] === preset.key
  )
}

function loadNavigationTheme() {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_NAVIGATION_THEME }
  }

  try {
    const rawTheme = window.localStorage.getItem(NAVIGATION_THEME_STORAGE_KEY)
    if (!rawTheme) {
      return { ...DEFAULT_NAVIGATION_THEME }
    }

    return sanitizeNavigationTheme(JSON.parse(rawTheme))
  } catch {
    return { ...DEFAULT_NAVIGATION_THEME }
  }
}

function persistNavigationTheme(theme) {
  if (typeof window === 'undefined') {
    return
  }

  const sanitizedTheme = sanitizeNavigationTheme(theme)
  window.localStorage.setItem(
    NAVIGATION_THEME_STORAGE_KEY,
    JSON.stringify(sanitizedTheme)
  )
  window.dispatchEvent(new CustomEvent(NAVIGATION_THEME_CHANGE_EVENT, { detail: sanitizedTheme }))
}

function applyNavigationTheme(theme) {
  const nextTheme = sanitizeNavigationTheme(theme)
  navigationTheme.menuBarMode = nextTheme.menuBarMode
  navigationTheme.menuBarColor = nextTheme.menuBarColor
  navigationTheme.menuBarGradientDirection = nextTheme.menuBarGradientDirection
  navigationTheme.menuBarGradientStartColor = nextTheme.menuBarGradientStartColor
  navigationTheme.menuBarGradientMiddleColor = nextTheme.menuBarGradientMiddleColor
  navigationTheme.menuBarGradientEndColor = nextTheme.menuBarGradientEndColor
  navigationTheme.menuBarAnimatedPreset = nextTheme.menuBarAnimatedPreset

  for (const group of THEME_EFFECT_GROUPS) {
    applyThemeEffect(navigationTheme, nextTheme, group.key)
  }

  navigationTheme.aiRightRailColor = nextTheme.aiRightRailColor
  navigationTheme.aiRightRailTextColor = nextTheme.aiRightRailTextColor
  navigationTheme.aiSelectedMenuTextColor = nextTheme.aiSelectedMenuTextColor
  navigationTheme.aiConversationWindowColor = nextTheme.aiConversationWindowColor
  navigationTheme.aiConversationWindowTextColor = nextTheme.aiConversationWindowTextColor
  navigationTheme.aiQuestionPanelColor = nextTheme.aiQuestionPanelColor
  navigationTheme.aiQuestionPanelTextColor = nextTheme.aiQuestionPanelTextColor
  navigationTheme.aiChatComposerBgColor = nextTheme.aiChatComposerBgColor
  navigationTheme.aiChatComposerTextColor = nextTheme.aiChatComposerTextColor
  navigationTheme.aiChatContentBgColor = nextTheme.aiChatContentBgColor
  navigationTheme.aiChatContentTextColor = nextTheme.aiChatContentTextColor
  navigationTheme.aiUserMessageBgColor = nextTheme.aiUserMessageBgColor
  navigationTheme.aiUserMessageTextColor = nextTheme.aiUserMessageTextColor
  navigationTheme.aiAssistantMessageBgColor = nextTheme.aiAssistantMessageBgColor
  navigationTheme.aiAssistantMessageTextColor = nextTheme.aiAssistantMessageTextColor
  navigationTheme.aiUserMessageIcon = nextTheme.aiUserMessageIcon
  navigationTheme.aiAssistantMessageIcon = nextTheme.aiAssistantMessageIcon
}

function sanitizeNavigationTheme(theme = {}) {
  return {
    menuBarMode: normalizeMenuBarMode(theme.menuBarMode),
    menuBarColor: normalizeHexColor(theme.menuBarColor, DEFAULT_NAVIGATION_THEME.menuBarColor),
    menuBarGradientDirection: normalizeGradientDirection(theme.menuBarGradientDirection),
    menuBarGradientStartColor: normalizeHexColor(
      theme.menuBarGradientStartColor,
      DEFAULT_NAVIGATION_THEME.menuBarGradientStartColor
    ),
    menuBarGradientMiddleColor: normalizeHexColor(
      theme.menuBarGradientMiddleColor,
      DEFAULT_NAVIGATION_THEME.menuBarGradientMiddleColor
    ),
    menuBarGradientEndColor: normalizeHexColor(
      theme.menuBarGradientEndColor,
      DEFAULT_NAVIGATION_THEME.menuBarGradientEndColor
    ),
    menuBarAnimatedPreset: normalizeAnimatedPreset(theme.menuBarAnimatedPreset),
    ...THEME_EFFECT_GROUPS.reduce(
      (result, group) => ({
        ...result,
        ...sanitizeThemeEffect(theme, group.key, DEFAULT_NAVIGATION_THEME),
      }),
      {}
    ),
    aiRightRailColor: normalizeHexColor(
      theme.aiRightRailColor,
      DEFAULT_NAVIGATION_THEME.aiRightRailColor
    ),
    aiRightRailTextColor: normalizeHexColor(
      theme.aiRightRailTextColor,
      DEFAULT_NAVIGATION_THEME.aiRightRailTextColor
    ),
    aiSelectedMenuTextColor: normalizeHexColor(
      theme.aiSelectedMenuTextColor,
      DEFAULT_NAVIGATION_THEME.aiSelectedMenuTextColor
    ),
    aiConversationWindowColor: normalizeHexColor(
      theme.aiConversationWindowColor,
      DEFAULT_NAVIGATION_THEME.aiConversationWindowColor
    ),
    aiConversationWindowTextColor: normalizeHexColor(
      theme.aiConversationWindowTextColor,
      DEFAULT_NAVIGATION_THEME.aiConversationWindowTextColor
    ),
    aiQuestionPanelColor: normalizeHexColor(
      theme.aiQuestionPanelColor,
      DEFAULT_NAVIGATION_THEME.aiQuestionPanelColor
    ),
    aiQuestionPanelTextColor: normalizeHexColor(
      theme.aiQuestionPanelTextColor,
      DEFAULT_NAVIGATION_THEME.aiQuestionPanelTextColor
    ),
    aiChatComposerBgColor: normalizeHexColor(
      theme.aiChatComposerBgColor,
      DEFAULT_NAVIGATION_THEME.aiChatComposerBgColor
    ),
    aiChatComposerTextColor: normalizeHexColor(
      theme.aiChatComposerTextColor,
      DEFAULT_NAVIGATION_THEME.aiChatComposerTextColor
    ),
    aiChatContentBgColor: normalizeHexColor(
      theme.aiChatContentBgColor,
      DEFAULT_NAVIGATION_THEME.aiChatContentBgColor
    ),
    aiChatContentTextColor: normalizeHexColor(
      theme.aiChatContentTextColor,
      DEFAULT_NAVIGATION_THEME.aiChatContentTextColor
    ),
    aiUserMessageBgColor: normalizeHexColor(
      theme.aiUserMessageBgColor,
      DEFAULT_NAVIGATION_THEME.aiUserMessageBgColor
    ),
    aiUserMessageTextColor: normalizeHexColor(
      theme.aiUserMessageTextColor,
      DEFAULT_NAVIGATION_THEME.aiUserMessageTextColor
    ),
    aiAssistantMessageBgColor: normalizeHexColor(
      theme.aiAssistantMessageBgColor,
      DEFAULT_NAVIGATION_THEME.aiAssistantMessageBgColor
    ),
    aiAssistantMessageTextColor: normalizeHexColor(
      theme.aiAssistantMessageTextColor,
      DEFAULT_NAVIGATION_THEME.aiAssistantMessageTextColor
    ),
    aiUserMessageIcon: normalizeThemeOptionKey(
      theme.aiUserMessageIcon,
      AI_USER_ICON_OPTIONS,
      DEFAULT_NAVIGATION_THEME.aiUserMessageIcon
    ),
    aiAssistantMessageIcon: normalizeThemeOptionKey(
      theme.aiAssistantMessageIcon,
      AI_ASSISTANT_ICON_OPTIONS,
      DEFAULT_NAVIGATION_THEME.aiAssistantMessageIcon
    ),
  }
}

function normalizeMenuBarMode(value) {
  if ([MENU_BAR_MODE_SOLID, MENU_BAR_MODE_GRADIENT, MENU_BAR_MODE_ANIMATED].includes(value)) {
    return value
  }

  return DEFAULT_NAVIGATION_THEME.menuBarMode
}

function normalizeGradientDirection(value, fallback = DEFAULT_NAVIGATION_THEME.menuBarGradientDirection) {
  if (GRADIENT_DIRECTION_OPTIONS.some(option => option.value === value)) {
    return value
  }

  return fallback
}

function normalizeAnimatedPreset(value, fallback = DEFAULT_NAVIGATION_THEME.menuBarAnimatedPreset) {
  if (ANIMATED_COLOR_PRESETS.some(preset => preset.key === value)) {
    return value
  }

  return fallback
}

function normalizeThemeOptionKey(value, options, fallback) {
  if (options.some(option => option.key === value)) {
    return value
  }

  return fallback
}

function getThemeEffectMode(theme, effectKey) {
  return normalizeMenuBarMode(theme[getThemeEffectFieldKey(effectKey, 'Mode')])
}

function getThemeEffectAnimatedPreset(theme, effectKey) {
  const animatedPresetKey = getThemeEffectFieldKey(effectKey, 'AnimatedPreset')
  return normalizeAnimatedPreset(theme[animatedPresetKey], DEFAULT_NAVIGATION_THEME[animatedPresetKey])
}

function getThemeEffectBaseColor(theme, effectKey, fallbackColor) {
  const mode = getThemeEffectMode(theme, effectKey)

  if (mode === MENU_BAR_MODE_GRADIENT) {
    return normalizeHexColor(theme[getThemeEffectFieldKey(effectKey, 'GradientEndColor')], fallbackColor)
  }

  if (mode === MENU_BAR_MODE_ANIMATED) {
    return normalizeHexColor(getAnimatedPreset(getThemeEffectAnimatedPreset(theme, effectKey)).colors[0], fallbackColor)
  }

  return normalizeHexColor(theme[getThemeEffectFieldKey(effectKey, 'Color')], fallbackColor)
}

function buildThemeEffectFill(theme, effectKey, fallbackColor) {
  const mode = getThemeEffectMode(theme, effectKey)

  if (mode === MENU_BAR_MODE_GRADIENT) {
    return buildLinearGradient(theme[getThemeEffectFieldKey(effectKey, 'GradientDirection')], [
      theme[getThemeEffectFieldKey(effectKey, 'GradientStartColor')],
      theme[getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')],
      theme[getThemeEffectFieldKey(effectKey, 'GradientEndColor')],
    ])
  }

  if (mode === MENU_BAR_MODE_ANIMATED) {
    const preset = getAnimatedPreset(getThemeEffectAnimatedPreset(theme, effectKey))
    return buildLinearGradient(preset.direction, preset.colors)
  }

  return normalizeHexColor(theme[getThemeEffectFieldKey(effectKey, 'Color')], fallbackColor)
}

function buildThemeEffectVariables(theme, effectKey, cssKey, fallbackColor) {
  const mode = getThemeEffectMode(theme, effectKey)
  const animatedPreset = getAnimatedPreset(getThemeEffectAnimatedPreset(theme, effectKey))

  return {
    [`--${cssKey}`]: buildThemeEffectFill(theme, effectKey, fallbackColor),
    [`--${cssKey}-size`]: mode === MENU_BAR_MODE_ANIMATED ? animatedPreset.backgroundSize : '100% 100%',
    [`--${cssKey}-duration`]: mode === MENU_BAR_MODE_ANIMATED ? animatedPreset.duration : '0s',
    [`--${cssKey}-color`]: getThemeEffectBaseColor(theme, effectKey, fallbackColor),
  }
}

function buildThemeEffectHoverBackground(theme, effectKey, fallbackColor, accentColor) {
  const mode = getThemeEffectMode(theme, effectKey)
  const baseColor = getThemeEffectBaseColor(theme, effectKey, fallbackColor)

  if (mode === MENU_BAR_MODE_SOLID) {
    return mixHexColor(baseColor, accentColor, 0.1)
  }

  return buildThemeEffectFill(theme, effectKey, fallbackColor)
}

function normalizeHexColor(value, fallback) {
  if (typeof value !== 'string') {
    return fallback
  }

  const trimmed = value.trim()
  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed
  }

  if (/^#[0-9a-fA-F]{3}$/.test(trimmed)) {
    return `#${trimmed.slice(1).split('').map(char => `${char}${char}`).join('')}`
  }

  return fallback
}

function mixHexColor(baseColor, targetColor, ratio) {
  const safeRatio = Math.max(0, Math.min(1, Number(ratio) || 0))
  const base = parseHexColor(baseColor)
  const target = parseHexColor(targetColor)

  if (!base || !target) {
    return normalizeHexColor(baseColor, DEFAULT_NAVIGATION_THEME.menuBarColor)
  }

  const mixed = {
    r: Math.round(base.r + ((target.r - base.r) * safeRatio)),
    g: Math.round(base.g + ((target.g - base.g) * safeRatio)),
    b: Math.round(base.b + ((target.b - base.b) * safeRatio)),
  }

  return `#${toHex(mixed.r)}${toHex(mixed.g)}${toHex(mixed.b)}`
}

function rgbaFromHex(color, alpha) {
  const parsed = parseHexColor(color)
  const safeAlpha = Math.max(0, Math.min(1, Number(alpha) || 0))

  if (!parsed) {
    return `rgba(35, 150, 234, ${safeAlpha})`
  }

  return `rgba(${parsed.r}, ${parsed.g}, ${parsed.b}, ${safeAlpha})`
}

function getAnimatedPreset(presetKey) {
  return ANIMATED_COLOR_PRESETS.find(item => item.key === presetKey) || ANIMATED_COLOR_PRESETS[0]
}

function sanitizeThemeEffect(theme, effectKey, defaultTheme) {
  const modeKey = getThemeEffectFieldKey(effectKey, 'Mode')
  const colorKey = getThemeEffectFieldKey(effectKey, 'Color')
  const directionKey = getThemeEffectFieldKey(effectKey, 'GradientDirection')
  const startKey = getThemeEffectFieldKey(effectKey, 'GradientStartColor')
  const middleKey = getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')
  const endKey = getThemeEffectFieldKey(effectKey, 'GradientEndColor')
  const animatedPresetKey = getThemeEffectFieldKey(effectKey, 'AnimatedPreset')

  return {
    [modeKey]: normalizeMenuBarMode(theme[modeKey]),
    [colorKey]: normalizeHexColor(theme[colorKey], defaultTheme[colorKey]),
    [directionKey]: normalizeGradientDirection(theme[directionKey], defaultTheme[directionKey]),
    [startKey]: normalizeHexColor(theme[startKey], defaultTheme[startKey]),
    [middleKey]: normalizeHexColor(theme[middleKey], defaultTheme[middleKey]),
    [endKey]: normalizeHexColor(theme[endKey], defaultTheme[endKey]),
    [animatedPresetKey]: normalizeAnimatedPreset(theme[animatedPresetKey], defaultTheme[animatedPresetKey]),
  }
}

function applyThemeEffect(targetTheme, sourceTheme, effectKey) {
  targetTheme[getThemeEffectFieldKey(effectKey, 'Mode')] = sourceTheme[getThemeEffectFieldKey(effectKey, 'Mode')]
  targetTheme[getThemeEffectFieldKey(effectKey, 'Color')] = sourceTheme[getThemeEffectFieldKey(effectKey, 'Color')]
  targetTheme[getThemeEffectFieldKey(effectKey, 'GradientDirection')] = sourceTheme[
    getThemeEffectFieldKey(effectKey, 'GradientDirection')
  ]
  targetTheme[getThemeEffectFieldKey(effectKey, 'GradientStartColor')] = sourceTheme[
    getThemeEffectFieldKey(effectKey, 'GradientStartColor')
  ]
  targetTheme[getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')] = sourceTheme[
    getThemeEffectFieldKey(effectKey, 'GradientMiddleColor')
  ]
  targetTheme[getThemeEffectFieldKey(effectKey, 'GradientEndColor')] = sourceTheme[
    getThemeEffectFieldKey(effectKey, 'GradientEndColor')
  ]
  targetTheme[getThemeEffectFieldKey(effectKey, 'AnimatedPreset')] = sourceTheme[
    getThemeEffectFieldKey(effectKey, 'AnimatedPreset')
  ]
}

function getThemeEffectFieldKey(effectKey, suffix) {
  return `${effectKey}${suffix}`
}

function createThemeEffectGroup(key, title, colorLabel) {
  return Object.freeze({
    key,
    title,
    colorLabel,
    modeKey: getThemeEffectFieldKey(key, 'Mode'),
    colorKey: getThemeEffectFieldKey(key, 'Color'),
    gradientDirectionKey: getThemeEffectFieldKey(key, 'GradientDirection'),
    gradientStartColorKey: getThemeEffectFieldKey(key, 'GradientStartColor'),
    gradientMiddleColorKey: getThemeEffectFieldKey(key, 'GradientMiddleColor'),
    gradientEndColorKey: getThemeEffectFieldKey(key, 'GradientEndColor'),
    animatedPresetKey: getThemeEffectFieldKey(key, 'AnimatedPreset'),
  })
}

function getTopbarBaseColor(theme) {
  if (theme.menuBarMode === MENU_BAR_MODE_GRADIENT) {
    return normalizeHexColor(theme.menuBarGradientEndColor, DEFAULT_NAVIGATION_THEME.menuBarColor)
  }

  if (theme.menuBarMode === MENU_BAR_MODE_ANIMATED) {
    return normalizeHexColor(getAnimatedPreset(theme.menuBarAnimatedPreset).colors[0], DEFAULT_NAVIGATION_THEME.menuBarColor)
  }

  return normalizeHexColor(theme.menuBarColor, DEFAULT_NAVIGATION_THEME.menuBarColor)
}

function buildTopbarBackground(theme) {
  if (theme.menuBarMode === MENU_BAR_MODE_GRADIENT) {
    return buildLinearGradient(theme.menuBarGradientDirection, [
      theme.menuBarGradientStartColor,
      theme.menuBarGradientMiddleColor,
      theme.menuBarGradientEndColor,
    ])
  }

  if (theme.menuBarMode === MENU_BAR_MODE_ANIMATED) {
    const preset = getAnimatedPreset(theme.menuBarAnimatedPreset)
    return buildLinearGradient(preset.direction, preset.colors)
  }

  return normalizeHexColor(theme.menuBarColor, DEFAULT_NAVIGATION_THEME.menuBarColor)
}

function buildLinearGradient(direction, colors) {
  const safeDirection = normalizeGradientDirection(direction)
  const safeColors = colors
    .map(color => normalizeHexColor(color, ''))
    .filter(Boolean)

  if (!safeColors.length) {
    return DEFAULT_NAVIGATION_THEME.menuBarColor
  }

  if (safeColors.length === 1) {
    return safeColors[0]
  }

  const step = 100 / (safeColors.length - 1)
  const stops = safeColors.map((color, index) => `${color} ${Math.round(step * index)}%`)
  return `linear-gradient(${safeDirection}, ${stops.join(', ')})`
}

function parseHexColor(color) {
  const normalized = normalizeHexColor(color, '')
  if (!normalized) {
    return null
  }

  return {
    r: Number.parseInt(normalized.slice(1, 3), 16),
    g: Number.parseInt(normalized.slice(3, 5), 16),
    b: Number.parseInt(normalized.slice(5, 7), 16),
  }
}

function toHex(value) {
  return value.toString(16).padStart(2, '0')
}
</script>

<style scoped lang="scss">
.layout {
  --app-visual-scale: 0.9;
  width: calc(100vw / var(--app-visual-scale));
  height: calc(100vh / var(--app-visual-scale));
  zoom: var(--app-visual-scale);
  overflow: hidden;
  background: var(--page-bg, #f5f7fa);
  background-size: var(--page-bg-size, 100% 100%);
  background-position: 0% 50%;
}

@supports not (zoom: 1) {
  .layout {
    width: calc(100vw / var(--app-visual-scale));
    height: calc(100vh / var(--app-visual-scale));
    transform: scale(var(--app-visual-scale));
    transform-origin: 0 0;
  }
}

.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 24px;
  background: var(--topbar-background, #2396ea);
  background-size: var(--topbar-background-size, 100% 100%);
  box-shadow: 0 12px 28px var(--topbar-shadow-color, rgba(28, 116, 181, 0.18));
  color: #fff;
}

.topbar--animated {
  animation: topbarGradientShift var(--topbar-animation-duration, 12s) ease infinite;
}

.topbar-left,
.topbar-home,
.topbar-right {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  min-width: 0;
}

.topbar-left {
  justify-content: flex-start;
}

.topbar-center {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  justify-content: stretch;
  overflow: hidden;
}

.topbar-center--floating-active {
  justify-content: center;
}

.topbar-home {
  justify-content: flex-end;
  gap: 10px;
}

.topbar-right {
  justify-content: flex-end;
  gap: 12px;
}

.brand {
  border: none;
  background: transparent;
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  padding: 0;
}

.home-switcher {
  flex-shrink: 0;
}

.home-switcher-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.home-switcher :deep(.el-button) {
  height: 42px;
  border: none;
  color: rgba(255, 255, 255, 0.95);
  background: rgba(255, 255, 255, 0.14);
  box-shadow: none;
  transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;

  &:hover,
  &:focus {
    color: #fff;
    background: rgba(255, 255, 255, 0.22);
  }
}

.home-switcher :deep(.el-button:not(.el-dropdown__caret-button)) {
  border-radius: 999px 0 0 999px;
  padding: 0 16px 0 18px;
}

.home-switcher :deep(.el-dropdown__caret-button) {
  border-radius: 0 999px 999px 0;
  padding: 0 12px;
  border-left: 1px solid rgba(255, 255, 255, 0.18);
}

.home-switcher :deep(.el-button + .el-button) {
  margin-left: 0;
}

.home-switcher.is-home-active :deep(.el-button) {
  background: rgba(255, 255, 255, 0.3);
  box-shadow: 0 10px 24px rgba(28, 116, 181, 0.16);
}

.module-menu-track {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 6px 8px;
  scroll-padding-inline: 8px;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  background: var(--nav-pill-bg, #ffffff);
  background-size: var(--nav-pill-bg-size, 100% 100%);
  background-position: 0% 50%;
  color: var(--nav-pill-text-color, #2396ea);
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    background: var(--nav-pill-hover-bg, #eaf4ff);
    transform: translateY(-1px);
    box-shadow: 0 8px 18px var(--nav-pill-hover-shadow-color, rgba(35, 150, 234, 0.18));
  }

  &.active {
    background: var(--nav-pill-active-bg, #2396ea);
    background-size: var(--nav-pill-active-bg-size, 100% 100%);
    background-position: 0% 50%;
    color: var(--nav-pill-active-text-color, #ffffff);
    transform: none;
    box-shadow: 0 10px 24px var(--nav-pill-active-shadow-color, rgba(3, 35, 92, 0.3));
  }
}

.nav-pill--bg-animated {
  animation: topbarGradientShift var(--nav-pill-bg-duration, 12s) ease infinite;
}

.nav-pill.active.nav-pill--bg-animated {
  animation: topbarGradientShift var(--nav-pill-active-bg-duration, 12s) ease infinite;
}

.nav-pill__label {
  display: inline-block;
  color: inherit;
  background-repeat: no-repeat;
  background-position: 0% 50%;
}

.nav-pill--text-gradient .nav-pill__label,
.nav-pill--text-animated .nav-pill__label {
  background: var(--nav-pill-text, #2396ea);
  background-size: var(--nav-pill-text-size, 100% 100%);
  color: transparent;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-pill.active.nav-pill--text-gradient .nav-pill__label,
.nav-pill.active.nav-pill--text-animated .nav-pill__label {
  background: var(--nav-pill-active-text, #ffffff);
  background-size: var(--nav-pill-active-text-size, 100% 100%);
}

.nav-pill--text-animated .nav-pill__label {
  animation: topbarGradientShift var(--nav-pill-text-duration, 12s) ease infinite;
}

.nav-pill.active.nav-pill--text-animated .nav-pill__label {
  animation: topbarGradientShift var(--nav-pill-active-text-duration, 12s) ease infinite;
}

.ai-floating-control {
  position: fixed;
  z-index: 1900;
  width: 96px;
  height: 96px;
  pointer-events: none;
  touch-action: none;
  user-select: none;
}

.ai-floating-control--dragging + .layout-main :deep(iframe) {
  pointer-events: none !important;
}

.ai-floating-control__core {
  position: absolute;
  left: 50%;
  top: 50%;
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  text-align: center;
  transition:
    transform 0.22s ease,
    opacity 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.ai-floating-control__core {
  width: 84px;
  height: 84px;
  transform: translate(-50%, -50%);
  background: linear-gradient(145deg, #fff8d6 0%, #ffd166 55%, #f2a93b 100%);
  color: #4a3412;
  box-shadow: 0 18px 34px rgba(160, 107, 20, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(128, 83, 12, 0.18);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0;
}

.ai-floating-control__core:hover {
  box-shadow: 0 20px 38px rgba(160, 107, 20, 0.34), inset 0 1px 0 rgba(255, 255, 255, 0.74);
  transform: translate(-50%, -50%) scale(1.03);
}

.ai-floating-control--dragging .ai-floating-control__core {
  cursor: grabbing;
  transform: translate(-50%, -50%) scale(1.04);
}

.ai-floating-control__radial {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 720px;
  height: 720px;
  overflow: visible;
  transform: translate(-50%, -50%) scale(0.72);
  transform-origin: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.22s ease;
}

.ai-floating-control--expanded .ai-floating-control__radial {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
}

.ai-floating-control__sector {
  cursor: pointer;
  outline: none;
}

.ai-floating-control__sector path {
  fill: rgba(255, 255, 255, 0.96);
  stroke: rgba(180, 120, 24, 0.42);
  stroke-width: 1.4;
  filter: drop-shadow(0 12px 18px rgba(61, 69, 83, 0.14));
  transition: fill 0.18s ease, stroke 0.18s ease, transform 0.18s ease, filter 0.18s ease;
  transform-origin: center;
}

.ai-floating-control__sector text {
  pointer-events: none;
  fill: #26384b;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.82);
  stroke-width: 3px;
  stroke-linejoin: round;
}

.ai-floating-control__sector--submenu path {
  fill: rgba(255, 251, 236, 0.97);
  stroke: rgba(42, 157, 143, 0.38);
}

.ai-floating-control__sector--submenu text {
  font-size: 12px;
}

.ai-floating-control__sector--level-2 path {
  fill: rgba(239, 246, 255, 0.98);
  stroke: rgba(35, 150, 234, 0.36);
}

.ai-floating-control__sector--level-2 text {
  font-size: 11px;
}

.ai-floating-control__sector:hover path,
.ai-floating-control__sector:focus-visible path {
  fill: #fff0bf;
  stroke: rgba(190, 126, 22, 0.72);
  filter: drop-shadow(0 16px 24px rgba(160, 107, 20, 0.22));
}

.ai-floating-control__sector.active path {
  fill: #2a9d8f;
  stroke: rgba(24, 118, 108, 0.82);
  filter: drop-shadow(0 16px 24px rgba(42, 157, 143, 0.26));
}

.ai-floating-control__sector.active text {
  fill: #ffffff;
  stroke: rgba(42, 157, 143, 0.36);
}

.ai-floating-control__sector.disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.theme-trigger {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.28);
    transform: translateY(-1px);
  }
}

.theme-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 72vh;
  overflow: hidden;
}

.theme-panel__title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.theme-panel__body {
  display: flex;
  min-height: 360px;
  max-height: calc(72vh - 78px);
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.theme-panel__tabs {
  width: 118px;
  flex: 0 0 118px;
  display: flex;
  flex-direction: column;
  padding: 8px;
  background: #f5f7fb;
  border-right: 1px solid #e4e7ed;
}

.theme-panel__tab {
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #606266;
  font-size: 13px;
  line-height: 1.3;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.16s ease, color 0.16s ease;

  &:hover {
    background: #eaf2ff;
    color: #1f4f82;
  }

  &.active {
    background: #dfeeff;
    color: #145a9f;
    font-weight: 700;
  }
}

.theme-panel__content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 12px 14px;
}

.theme-panel__section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.theme-panel__content > .theme-panel__section:first-child {
  padding-top: 0;
  border-top: 0;
}

.theme-panel__section-title {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
}

.theme-panel__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.theme-panel__row--stack {
  align-items: flex-start;
  flex-direction: column;
}

.theme-panel__label {
  font-size: 13px;
  color: #606266;
}

.theme-panel__select {
  width: 168px;
}

.theme-panel__preset-list {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.theme-preset {
  flex: 1 1 calc(50% - 4px);
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 12px;
  background: #ffffff;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

  &:hover {
    border-color: #409eff;
    transform: translateY(-1px);
  }

  &.active {
    border-color: #409eff;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.16);
  }
}

.theme-preset__swatch {
  width: 44px;
  height: 20px;
  flex: 0 0 auto;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}

.theme-preset__swatch--animated {
  background-size: 220% 220% !important;
  animation: topbarGradientShift 6s ease infinite;
}

.theme-preset__text {
  min-width: 0;
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-icon-choice-list {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.theme-icon-choice {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  background: #ffffff;
  color: #303133;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, color 0.16s ease;

  .el-icon {
    flex: 0 0 auto;
    font-size: 18px;
  }

  span {
    min-width: 0;
    overflow: hidden;
    font-size: 12px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &:hover,
  &.active {
    border-color: #409eff;
    color: #145a9f;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.14);
  }
}

.theme-panel__actions {
  display: flex;
  justify-content: flex-end;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.22);
  }
}

.username {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #fff;
}

.dropdown-icon {
  color: rgba(255, 255, 255, 0.85);
}

.layout-main {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding-top: var(--topbar-height);
  overflow: hidden;
}

.layout-main--topbar-hidden {
  padding-top: 0;
}

.layout-content {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: var(--page-bg, #f5f7fa);
  background-size: var(--page-bg-size, 100% 100%);
  background-position: 0% 50%;
}

.layout-content--animated {
  animation: topbarGradientShift var(--page-bg-duration, 12s) ease infinite;
}

.layout-content > * {
  min-height: 100%;
  background: var(--page-bg, #f5f7fa) !important;
  background-size: var(--page-bg-size, 100% 100%) !important;
  background-position: 0% 50% !important;
}

.layout-content :deep(
  .page-container,
  .home-container,
  .dashboard-container,
  .ui-automation-container,
  .workflow-workbench-page,
  .marketplace-page,
  .capability-asset-page,
  .ai-generation-workspace,
  .execution-detail,
  .testcase-detail-page,
  .ui-automation-cases-page,
  .notification-configs-container,
  .notification-logs-container,
  .dify-config-container,
  .version-requirement-page,
  .defect-list-page,
  .testing-overview-page,
  .visual-flow-manager,
  .manual-testcase-list--allow-page-scroll,
  .quality-detail-page,
  .report-list-page,
  .jira-data-page,
  .assistant-layout,
  .ai-session-workspace
) {
  background: var(--page-bg, #f5f7fa) !important;
  background-size: var(--page-bg-size, 100% 100%) !important;
  background-position: 0% 50% !important;
}

.layout-content--animated :deep(
  .page-container,
  .home-container,
  .dashboard-container,
  .ui-automation-container,
  .workflow-workbench-page,
  .marketplace-page,
  .capability-asset-page,
  .ai-generation-workspace,
  .execution-detail,
  .testcase-detail-page,
  .ui-automation-cases-page,
  .notification-configs-container,
  .notification-logs-container,
  .dify-config-container,
  .version-requirement-page,
  .defect-list-page,
  .testing-overview-page,
  .visual-flow-manager,
  .manual-testcase-list--allow-page-scroll,
  .quality-detail-page,
  .report-list-page,
  .jira-data-page,
  .assistant-layout,
  .ai-session-workspace
) {
  animation: topbarGradientShift var(--page-bg-duration, 12s) ease infinite;
}

.layout-content--animated > * {
  animation: topbarGradientShift var(--page-bg-duration, 12s) ease infinite;
}

.layout-content :deep(
  .card-container,
  .page-header,
  .filter-card,
  .table-card,
  .el-card,
  .el-dialog,
  .el-drawer,
  .el-table,
  .el-tabs__content,
  .workspace-content-panel,
  .workspace-tab-shell
) {
  --el-bg-color: rgba(255, 255, 255, 0.94);
  --el-fill-color-blank: rgba(255, 255, 255, 0.94);
}

.layout-content :deep(
  .page-container > .el-tabs > .el-tabs__header .el-tabs__nav-scroll,
  .workspace-toolbar-panel .manual-workspace-section-tabs__tabs .el-tabs__nav-scroll,
  .workspace-section-tabs .el-tabs__nav-scroll
) {
  display: flex;
  justify-content: center;
}

.layout-content :deep(
  .page-container > .el-tabs > .el-tabs__header .el-tabs__nav-wrap,
  .workspace-toolbar-panel .manual-workspace-section-tabs__tabs .el-tabs__nav-wrap,
  .workspace-section-tabs .el-tabs__nav-wrap
) {
  display: flex;
  justify-content: center;
}

.layout-content :deep(
  .el-button--primary:not(.is-link),
  .search-btn,
  .refresh-btn,
  .edit-btn,
  .view-btn,
  .preview-btn,
  .confirm-btn
) {
  --el-button-bg-color: var(--page-button-bg, #409eff);
  --el-button-border-color: var(--page-button-border-color, #409eff);
  --el-button-hover-bg-color: var(--page-button-hover-bg, #66b1ff);
  --el-button-hover-border-color: var(--page-button-border-color, #409eff);
  --el-button-active-bg-color: var(--page-button-active-bg, #337ecc);
  --el-button-active-border-color: var(--page-button-active-bg, #337ecc);
  --el-button-text-color: var(--page-button-text-color, #ffffff);
  --el-button-hover-text-color: var(--page-button-text-color, #ffffff);
  background: var(--page-button-bg, #409eff) !important;
  background-size: var(--page-button-bg-size, 100% 100%) !important;
  background-position: 0% 50% !important;
  border-color: var(--page-button-border-color, #409eff) !important;
  color: var(--page-button-text-color, #ffffff) !important;
  box-shadow: 0 8px 18px var(--page-button-shadow-color, rgba(64, 158, 255, 0.22));
}

.layout-content :deep(
  .el-button--primary:not(.is-link):hover,
  .el-button--primary:not(.is-link):focus,
  .search-btn:hover:not(:disabled),
  .search-btn:focus,
  .refresh-btn:hover:not(:disabled),
  .refresh-btn:focus,
  .edit-btn:hover:not(:disabled),
  .edit-btn:focus,
  .view-btn:hover:not(:disabled),
  .view-btn:focus,
  .preview-btn:hover:not(:disabled),
  .preview-btn:focus,
  .confirm-btn:hover:not(:disabled),
  .confirm-btn:focus
) {
  background: var(--page-button-hover-bg, #66b1ff) !important;
  border-color: var(--page-button-border-color, #409eff) !important;
  color: var(--page-button-text-color, #ffffff) !important;
  box-shadow: 0 10px 22px var(--page-button-focus-shadow-color, rgba(64, 158, 255, 0.24));
}

.layout-content :deep(
  .el-button--primary:not(.is-link):active,
  .search-btn:active,
  .refresh-btn:active,
  .edit-btn:active,
  .view-btn:active,
  .preview-btn:active,
  .confirm-btn:active
) {
  background: var(--page-button-active-bg, #337ecc) !important;
  border-color: var(--page-button-active-bg, #337ecc) !important;
}

.layout-content--button-bg-animated :deep(
  .el-button--primary:not(.is-link),
  .search-btn,
  .refresh-btn,
  .edit-btn,
  .view-btn,
  .preview-btn,
  .confirm-btn
) {
  animation: topbarGradientShift var(--page-button-bg-duration, 12s) ease infinite;
}

.layout-content--button-text-gradient :deep(
  .el-button--primary:not(.is-link) > span
) {
  background: var(--page-button-text, #ffffff);
  background-size: var(--page-button-text-size, 100% 100%);
  background-position: 0% 50%;
  color: transparent !important;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.layout-content--button-text-animated :deep(
  .el-button--primary:not(.is-link) > span
) {
  animation: topbarGradientShift var(--page-button-text-duration, 12s) ease infinite;
}

.layout-content :deep(.assistant-layout) {
  height: 100% !important;
  min-height: 0;
}

.layout-content :deep(.assistant-layout .user-profile) {
  display: none !important;
}

@keyframes topbarGradientShift {
  0% {
    background-position: 0% 50%;
  }

  50% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0% 50%;
  }
}

@media screen and (max-width: 1440px) {
  .topbar {
    padding: 0 18px;
    gap: 16px;
  }

  .brand {
    font-size: 22px;
  }

  .nav-pill {
    padding: 9px 16px;
    font-size: 13px;
  }
}

@media screen and (max-width: 1024px) {
  .topbar {
    gap: 12px;
    padding: 0 14px;
  }

  .brand {
    font-size: 20px;
  }

  .username {
    max-width: 110px;
  }
}

@media screen and (max-width: 768px) {
  .topbar {
    padding: 0 12px;
  }

  .brand {
    font-size: 18px;
  }

  .nav-pill {
    padding: 8px 14px;
  }

  .username {
    display: none;
  }

  .user-trigger {
    padding: 8px;
  }

  .ai-floating-control {
    width: 82px;
    height: 82px;
  }

  .ai-floating-control__core {
    width: 72px;
    height: 72px;
    font-size: 13px;
  }

  .ai-floating-control__radial {
    width: 460px;
    height: 460px;
  }

  .ai-floating-control__sector text {
    font-size: 11px;
  }

  .ai-floating-control__sector--submenu text {
    font-size: 10px;
  }

  .ai-floating-control__sector--level-2 text {
    font-size: 9px;
  }
}
</style>
