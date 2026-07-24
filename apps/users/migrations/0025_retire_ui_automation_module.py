from django.db import migrations


UI_AUTOMATION_MODULE_CODES = [
    'module:ui-automation',
    'menu:ui-automation:dashboard',
    'menu:ui-automation:projects',
    'menu:ui-automation:elements-enhanced',
    'menu:ui-automation:test-cases',
    'menu:ui-automation:scripts-enhanced',
    'menu:ui-automation:scripts',
    'menu:ui-automation:suites',
    'menu:ui-automation:executions',
    'menu:ui-automation:reports',
    'menu:ui-automation:scheduled-tasks',
    'menu:ui-automation:notification-logs',
]

UI_AUTOMATION_HOME_CARD_CODE = 'menu:home:ui-automation'


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def retire_ui_automation_module(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')

    PermissionItem.objects.filter(code__in=UI_AUTOMATION_MODULE_CODES).update(
        route_path='/home',
        is_active=False,
        description='UI automation standalone module retired; historical links redirect to home.',
    )
    PermissionItem.objects.filter(code=UI_AUTOMATION_HOME_CARD_CODE).update(
        route_path='/home',
        is_active=False,
        description='UI automation standalone home card retired.',
    )

    view_permission_codes = [
        code
        for code in (build_view_permission_code(item) for item in UI_AUTOMATION_MODULE_CODES)
        if code
    ]
    PermissionItem.objects.filter(code__in=view_permission_codes).update(
        is_active=False,
        description='UI automation standalone module retired.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_remove_home_data_factory_permission'),
    ]

    operations = [
        migrations.RunPython(retire_ui_automation_module, migrations.RunPython.noop),
    ]
