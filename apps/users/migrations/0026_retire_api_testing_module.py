from django.db import migrations


API_TESTING_MODULE_CODES = [
    'module:api-testing',
    'menu:api-testing:dashboard',
    'menu:api-testing:projects',
    'menu:api-testing:interfaces',
    'menu:api-testing:automation',
    'menu:api-testing:history',
    'menu:api-testing:environments',
    'menu:api-testing:reports',
    'menu:api-testing:scheduled-tasks',
    'menu:api-testing:notification-logs',
]

API_TESTING_HOME_CARD_CODE = 'menu:home:api-testing'


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def retire_api_testing_module(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')

    PermissionItem.objects.filter(code__in=API_TESTING_MODULE_CODES).update(
        route_path='/home',
        is_active=False,
        description='API testing standalone module retired; historical links redirect to home.',
    )
    PermissionItem.objects.filter(code=API_TESTING_HOME_CARD_CODE).update(
        route_path='/home',
        is_active=False,
        description='API testing standalone home card retired.',
    )

    view_permission_codes = [
        code
        for code in (build_view_permission_code(item) for item in API_TESTING_MODULE_CODES)
        if code
    ]
    PermissionItem.objects.filter(code__in=view_permission_codes).update(
        is_active=False,
        description='API testing standalone module retired.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_retire_ui_automation_module'),
    ]

    operations = [
        migrations.RunPython(retire_api_testing_module, migrations.RunPython.noop),
    ]
