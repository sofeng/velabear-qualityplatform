import apiTestLogo from '@/assets/images/workshop-skill-logo/api_test.png'
import businessLogo from '@/assets/images/workshop-skill-logo/business.png'
import canvasDesignLogo from '@/assets/images/workshop-skill-logo/canvas_design.png'
import commonLogo from '@/assets/images/workshop-skill-logo/common.png'
import datatableLogo from '@/assets/images/workshop-skill-logo/datatable.png'
import devLogo from '@/assets/images/workshop-skill-logo/dev.png'
import docLogo from '@/assets/images/workshop-skill-logo/doc.png'
import docxLogo from '@/assets/images/workshop-skill-logo/docx.png'
import htmlLogo from '@/assets/images/workshop-skill-logo/html.png'
import imageLogo from '@/assets/images/workshop-skill-logo/image.png'
import internalChatLogo from '@/assets/images/workshop-skill-logo/internal_chat.png'
import mcpLogo from '@/assets/images/workshop-skill-logo/mcp.png'
import newsLogo from '@/assets/images/workshop-skill-logo/news.png'
import pdfLogo from '@/assets/images/workshop-skill-logo/pdf.png'
import pptxLogo from '@/assets/images/workshop-skill-logo/pptx.png'
import prototypeLogo from '@/assets/images/workshop-skill-logo/prototype.png'
import skillLogo from '@/assets/images/workshop-skill-logo/skill.png'
import skillPromptLogo from '@/assets/images/workshop-skill-logo/skill_prompt.png'
import socialLogo from '@/assets/images/workshop-skill-logo/social.png'
import testCaseLogo from '@/assets/images/workshop-skill-logo/test_case.png'
import testExecuteLogo from '@/assets/images/workshop-skill-logo/test_excute.png'
import themeFactoryLogo from '@/assets/images/workshop-skill-logo/theme_factory.png'
import toolLogo from '@/assets/images/workshop-skill-logo/tool.png'
import uiTestLogo from '@/assets/images/workshop-skill-logo/ui_test.png'
import videoLogo from '@/assets/images/workshop-skill-logo/video.png'
import webpageLogo from '@/assets/images/workshop-skill-logo/webpage.png'
import webExportToolLogo from '@/assets/images/workshop-skill-logo/web_export_tool.png'
import webTestExpertLogo from '@/assets/images/workshop-skill-logo/web_test_expert.png'
import xlsxLogo from '@/assets/images/workshop-skill-logo/xlsx.png'

const LOGO_URLS = Object.freeze({
  api_test: apiTestLogo,
  business: businessLogo,
  canvas_design: canvasDesignLogo,
  common: commonLogo,
  datatable: datatableLogo,
  dev: devLogo,
  doc: docLogo,
  docx: docxLogo,
  html: htmlLogo,
  image: imageLogo,
  internal_chat: internalChatLogo,
  mcp: mcpLogo,
  news: newsLogo,
  pdf: pdfLogo,
  pptx: pptxLogo,
  prototype: prototypeLogo,
  skill: skillLogo,
  skill_prompt: skillPromptLogo,
  social: socialLogo,
  test_case: testCaseLogo,
  test_excute: testExecuteLogo,
  theme_factory: themeFactoryLogo,
  tool: toolLogo,
  ui_test: uiTestLogo,
  video: videoLogo,
  webpage: webpageLogo,
  web_export_tool: webExportToolLogo,
  web_test_expert: webTestExpertLogo,
  xlsx: xlsxLogo,
})

const LOGO_ALIASES = Object.freeze({
  agent: 'internal_chat',
  api: 'api_test',
  api_testing: 'api_test',
  code: 'dev',
  database: 'datatable',
  db: 'datatable',
  design: 'canvas_design',
  document: 'doc',
  execution: 'test_excute',
  executions: 'test_excute',
  flow: 'business',
  git: 'web_export_tool',
  integration: 'web_export_tool',
  integrations: 'web_export_tool',
  llm: 'internal_chat',
  mcp_plugin: 'mcp',
  model: 'internal_chat',
  page_design: 'canvas_design',
  plug: 'mcp',
  plugin: 'mcp',
  prompt: 'skill_prompt',
  prompts: 'skill_prompt',
  repository: 'web_export_tool',
  runtime: 'dev',
  test: 'test_case',
  test_execute: 'test_excute',
  test_tool: 'tool',
  test_tools: 'tool',
  testtool: 'tool',
  testtools: 'tool',
  tools: 'tool',
  workflow: 'business',
})

export const WORKSHOP_LOGO_OPTIONS = Object.freeze([
  { value: 'skill', label: 'Skill', url: skillLogo },
  { value: 'skill_prompt', label: 'Prompt', url: skillPromptLogo },
  { value: 'mcp', label: 'MCP', url: mcpLogo },
  { value: 'api_test', label: 'API Test', url: apiTestLogo },
  { value: 'ui_test', label: 'UI Test', url: uiTestLogo },
  { value: 'test_case', label: 'Test Case', url: testCaseLogo },
  { value: 'test_excute', label: 'Execution', url: testExecuteLogo },
  { value: 'dev', label: 'Development', url: devLogo },
  { value: 'prototype', label: 'Prototype', url: prototypeLogo },
  { value: 'canvas_design', label: 'Design', url: canvasDesignLogo },
  { value: 'doc', label: 'Document', url: docLogo },
  { value: 'docx', label: 'Docx', url: docxLogo },
  { value: 'pdf', label: 'PDF', url: pdfLogo },
  { value: 'pptx', label: 'PPT', url: pptxLogo },
  { value: 'xlsx', label: 'Excel', url: xlsxLogo },
  { value: 'datatable', label: 'Data', url: datatableLogo },
  { value: 'html', label: 'HTML', url: htmlLogo },
  { value: 'webpage', label: 'Webpage', url: webpageLogo },
  { value: 'web_export_tool', label: 'Web Export', url: webExportToolLogo },
  { value: 'web_test_expert', label: 'Web Test', url: webTestExpertLogo },
  { value: 'image', label: 'Image', url: imageLogo },
  { value: 'video', label: 'Video', url: videoLogo },
  { value: 'news', label: 'News', url: newsLogo },
  { value: 'business', label: 'Business', url: businessLogo },
  { value: 'internal_chat', label: 'Chat', url: internalChatLogo },
  { value: 'theme_factory', label: 'Theme', url: themeFactoryLogo },
  { value: 'tool', label: 'Tool', url: toolLogo },
  { value: 'social', label: 'Social', url: socialLogo },
  { value: 'common', label: 'Common', url: commonLogo },
])

export const getWorkshopLogoOption = value => (
  WORKSHOP_LOGO_OPTIONS.find(item => item.value === normalizeWorkshopLogoKey(value)) ||
  WORKSHOP_LOGO_OPTIONS.find(item => item.value === 'common')
)

export const normalizeWorkshopLogoKey = value => {
  const rawValue = String(value || '').trim()
  if (!rawValue) {
    return ''
  }

  const filename = rawValue
    .split(/[\\/]/)
    .pop()
    .split('?')[0]
    .split('#')[0]
    .replace(/\.[A-Za-z0-9]+$/, '')
    .replace(/^\[|\]$/g, '')

  const normalized = filename
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .replace(/[^A-Za-z0-9_]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase()

  return LOGO_URLS[normalized] ? normalized : (LOGO_ALIASES[normalized] || '')
}

export const getWorkshopLogoUrl = (value, fallback = 'common') => {
  const key = normalizeWorkshopLogoKey(value) || normalizeWorkshopLogoKey(fallback) || 'common'
  return LOGO_URLS[key] || LOGO_URLS.common
}

export const resolveWorkshopLogoUrl = (...candidates) => {
  for (const candidate of candidates) {
    const key = normalizeWorkshopLogoKey(candidate)
    if (key && LOGO_URLS[key]) {
      return LOGO_URLS[key]
    }
  }
  return LOGO_URLS.common
}
