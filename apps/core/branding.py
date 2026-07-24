import os


PLATFORM_BRAND_NAME = os.environ.get('BEARAI_BRAND_NAME', 'BearAI').strip() or 'BearAI'
PLATFORM_BRAND_AI_NAME = os.environ.get('BEARAI_BRAND_AI_NAME', f'{PLATFORM_BRAND_NAME} AI').strip() or f'{PLATFORM_BRAND_NAME} AI'
PLATFORM_LOG_PREFIX = f'[{PLATFORM_BRAND_NAME}]'
LEGACY_PLATFORM_BRAND_NAME = 'TestHub'


def display_brand_provider(value, default=PLATFORM_BRAND_NAME):
    normalized = str(value or '').strip()
    if not normalized:
        return default
    if normalized == LEGACY_PLATFORM_BRAND_NAME:
        return PLATFORM_BRAND_NAME
    return normalized


def provider_filter_values(value):
    normalized = str(value or '').strip()
    if not normalized:
        return []
    if normalized in {PLATFORM_BRAND_NAME, LEGACY_PLATFORM_BRAND_NAME}:
        return [PLATFORM_BRAND_NAME, LEGACY_PLATFORM_BRAND_NAME]
    return [normalized]
