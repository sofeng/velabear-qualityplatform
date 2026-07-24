export const PLATFORM_BRAND_NAME = 'BearAI'
export const PLATFORM_BRAND_AI_NAME = 'BearAI AI'
export const LEGACY_PLATFORM_BRAND_NAME = 'TestHub'

export const normalizeBrandProvider = value => (
  String(value || '').trim() === LEGACY_PLATFORM_BRAND_NAME ? PLATFORM_BRAND_NAME : value
)

export const BRAND_PROVIDER_OPTIONS = Object.freeze([
  PLATFORM_BRAND_NAME,
  'Codex',
  'Claude',
  'Trae',
  'Coze',
  'GitHub',
  'OpenAI',
  'Anthropic',
  'Enterprise',
])
