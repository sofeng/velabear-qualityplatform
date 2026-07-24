from django.db import migrations


WORKSHOP_CONFIG_MENU_DEFS = [
    {
        'code': 'menu:ai-generation:workshop-models',
        'view_code': 'button:ai-generation:workshop-models:view',
        'name': 'AI军火库-大模型',
        'route_path': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
        'sort_order': 10,
        'source_codes': [
            'menu:configuration:ai-model',
            'button:configuration:ai-model:view',
            'menu:configuration:ai-mode',
            'button:configuration:ai-mode:view',
            'menu:configuration:dify',
            'button:configuration:dify:view',
            'menu:ai-generation:ai-dev-llm-configs',
            'button:ai-generation:ai-dev-llm-configs:view',
        ],
    },
    {
        'code': 'menu:ai-generation:workshop-test-tools',
        'view_code': 'button:ai-generation:workshop-test-tools:view',
        'name': 'AI军火库-测试工具',
        'route_path': '/ai-generation/workshop?workshop_tab=test-tools&config_tab=test-tools',
        'sort_order': 20,
        'source_codes': [
            'menu:ai-generation:ai-dev-test-tool-configs',
            'button:ai-generation:ai-dev-test-tool-configs:view',
        ],
    },
    {
        'code': 'menu:ai-generation:workshop-ui-env',
        'view_code': 'button:ai-generation:workshop-ui-env:view',
        'name': 'AI军火库-UI环境',
        'route_path': '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env',
        'sort_order': 30,
        'source_codes': [
            'menu:configuration:ui-env',
            'button:configuration:ui-env:view',
        ],
    },
    {
        'code': 'menu:ai-generation:workshop-integrations',
        'view_code': 'button:ai-generation:workshop-integrations:view',
        'name': 'AI军火库-Git集成',
        'route_path': '/ai-generation/workshop?workshop_tab=integrations&config_tab=git',
        'sort_order': 40,
        'source_codes': [
            'menu:ai-generation:ai-dev-repository-configs',
            'button:ai-generation:ai-dev-repository-configs:view',
            'menu:ai-generation:ci-cd',
            'button:ai-generation:ci-cd:view',
        ],
    },
    {
        'code': 'menu:ai-generation:workshop-notifications',
        'view_code': 'button:ai-generation:workshop-notifications:view',
        'name': 'AI军火库-通知机器人',
        'route_path': '/ai-generation/workshop?workshop_tab=integrations&config_tab=notifications',
        'sort_order': 50,
        'source_codes': [
            'menu:configuration:scheduled-task',
            'button:configuration:scheduled-task:view',
        ],
    },
]

RETIRED_CONFIGURATION_CODES = {
    'module:configuration': '/ai-generation/workshop',
    'menu:home:configuration': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'menu:configuration:ai-model': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'button:configuration:ai-model:view': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'menu:configuration:ai-mode': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'button:configuration:ai-mode:view': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'menu:configuration:dify': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'button:configuration:dify:view': '/ai-generation/workshop?workshop_tab=models&config_tab=llm',
    'menu:configuration:ui-env': '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env',
    'button:configuration:ui-env:view': '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env',
    'menu:configuration:scheduled-task': '/ai-generation/workshop?workshop_tab=integrations&config_tab=notifications',
    'button:configuration:scheduled-task:view': '/ai-generation/workshop?workshop_tab=integrations&config_tab=notifications',
}


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


def consolidate_configuration_center_into_ai_workshop(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    ai_generation_module = PermissionItem.objects.filter(code='module:ai-generation').first()
    workshop_permission, _ = PermissionItem.objects.update_or_create(
        code='menu:ai-generation:workshop',
        defaults={
            'name': 'AI军火库',
            'item_type': 'menu',
            'parent': ai_generation_module,
            'route_path': '/ai-generation/workshop',
            'sort_order': 80,
            'is_active': True,
            'description': 'AI研发能力、工具、配置与企业集成的统一入口。',
        },
    )

    for item in WORKSHOP_CONFIG_MENU_DEFS:
        menu_permission, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'item_type': 'menu',
                'parent': workshop_permission,
                'route_path': item['route_path'],
                'sort_order': item['sort_order'],
                'is_active': True,
                'description': '配置中心能力已整合到 AI军火库。',
            },
        )
        view_permission, _ = PermissionItem.objects.update_or_create(
            code=item['view_code'],
            defaults={
                'name': '查看',
                'item_type': 'button',
                'parent': menu_permission,
                'route_path': '',
                'sort_order': 5,
                'is_active': True,
                'description': '查看 AI军火库配置页签。',
            },
        )

        for source_code in item['source_codes']:
            copy_role_permissions(source_code, menu_permission, RolePermission, PermissionItem)
            copy_role_permissions(source_code, view_permission, RolePermission, PermissionItem)

    for code, route_path in RETIRED_CONFIGURATION_CODES.items():
        PermissionItem.objects.filter(code=code).update(
            route_path=route_path,
            is_active=False,
            description='Standalone configuration center retired; capability consolidated into AI军火库.',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0030_add_manual_project_environment_permission'),
    ]

    operations = [
        migrations.RunPython(consolidate_configuration_center_into_ai_workshop, migrations.RunPython.noop),
    ]
