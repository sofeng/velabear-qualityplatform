from django.db import migrations


AI_INTELLIGENT_MODE_CODES = [
    'module:ai-intelligent-mode',
    'menu:ai-intelligent-mode:testing',
    'menu:ai-intelligent-mode:cases',
    'menu:ai-intelligent-mode:execution-records',
]

AI_INTELLIGENT_MODE_HOME_CARD_CODE = 'menu:home:ai-intelligent-mode'
AI_INTELLIGENT_MODE_CONFIG_CODE = 'menu:configuration:ai-mode'


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def retire_ai_intelligent_mode_module(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')

    PermissionItem.objects.filter(code__in=AI_INTELLIGENT_MODE_CODES).update(
        route_path='/home',
        is_active=False,
        description='AI intelligent mode standalone module retired; historical links redirect to home.',
    )
    PermissionItem.objects.filter(code=AI_INTELLIGENT_MODE_HOME_CARD_CODE).update(
        route_path='/home',
        is_active=False,
        description='AI intelligent mode home card retired.',
    )
    PermissionItem.objects.filter(code=AI_INTELLIGENT_MODE_CONFIG_CODE).update(
        route_path='/configuration/ai-model',
        is_active=False,
        description='AI intelligent mode configuration page retired; historical links redirect to AI model configuration.',
    )

    view_permission_codes = [
        code
        for code in (build_view_permission_code(item) for item in AI_INTELLIGENT_MODE_CODES)
        if code
    ]
    view_permission_codes.append('button:configuration:ai-mode:view')
    PermissionItem.objects.filter(code__in=view_permission_codes).update(
        is_active=False,
        description='AI intelligent mode module retired.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_retire_api_testing_module'),
    ]

    operations = [
        migrations.RunPython(retire_ai_intelligent_mode_module, migrations.RunPython.noop),
    ]
