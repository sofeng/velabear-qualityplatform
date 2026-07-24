from django.db import migrations


RETIRED_AI_TESTING_CODES = [
    'menu:ai-generation:testing',
    'menu:ai-generation:testcases',
    'menu:ai-generation:ui-automation-cases',
    'menu:ai-generation:reviews',
    'menu:ai-generation:review-templates',
    'menu:ai-generation:executions',
    'menu:ai-generation:reports',
]

TESTCASE_CREATE_CODE = 'button:ai-generation:testcases:create'
TESTCASE_CREATE_SOURCE_CODES = [
    'menu:ai-generation:testing',
    'menu:ai-generation:testcases',
    'button:ai-generation:testcases:view',
]


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def copy_role_permissions(source_code, target_permission, RolePermission, PermissionItem):
    source_permission = PermissionItem.objects.filter(code=source_code).first()
    if not source_permission or not target_permission:
        return

    source_role_ids = list(
        RolePermission.objects
        .filter(permission_item=source_permission)
        .values_list('role_id', flat=True)
        .distinct()
    )
    if not source_role_ids:
        return

    existing_role_ids = set(
        RolePermission.objects
        .filter(permission_item=target_permission, role_id__in=source_role_ids)
        .values_list('role_id', flat=True)
    )
    RolePermission.objects.bulk_create(
        [
            RolePermission(role_id=role_id, permission_item=target_permission)
            for role_id in source_role_ids
            if role_id not in existing_role_ids
        ],
        ignore_conflicts=True,
    )


def retire_ai_generation_testing_menu(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    module_permission = PermissionItem.objects.filter(code='module:ai-generation').first()
    testcase_create_permission, _ = PermissionItem.objects.update_or_create(
        code=TESTCASE_CREATE_CODE,
        defaults={
            'name': '新建用例',
            'item_type': 'button',
            'parent': module_permission,
            'route_path': '/ai-generation/testcases/create',
            'sort_order': 55,
            'is_active': True,
            'description': 'AI研发平台保留的测试用例新建入口；原 AI测试菜单和列表页已退役。',
        },
    )

    for source_code in TESTCASE_CREATE_SOURCE_CODES:
        copy_role_permissions(source_code, testcase_create_permission, RolePermission, PermissionItem)

    PermissionItem.objects.filter(code__in=RETIRED_AI_TESTING_CODES).update(
        route_path='/home',
        is_active=False,
        description='AI测试菜单及其列表、评审、执行、报告等页面已退役；旧入口不再跳转到保留的新建用例页面。',
    )

    view_permission_codes = [
        code
        for code in (build_view_permission_code(item) for item in RETIRED_AI_TESTING_CODES)
        if code
    ]
    PermissionItem.objects.filter(code__in=view_permission_codes).update(
        is_active=False,
        description='AI测试菜单页面已退役；查看权限不再作为页面访问入口。',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_retire_ai_intelligent_mode_module'),
    ]

    operations = [
        migrations.RunPython(retire_ai_generation_testing_menu, migrations.RunPython.noop),
    ]
