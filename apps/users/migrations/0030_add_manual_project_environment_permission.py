from django.db import migrations


PROJECT_ENVIRONMENT_MENU_CODE = 'menu:manual-testcases:project-environments'
PROJECT_ENVIRONMENT_VIEW_CODE = 'button:manual-testcases:project-environments:view'
SOURCE_PERMISSION_CODES = [
    'menu:manual-testcases:config',
    'menu:manual-testcases:configs',
    'button:manual-testcases:configs:view',
]


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


def add_manual_project_environment_permission(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    config_permission = PermissionItem.objects.filter(code='menu:manual-testcases:config').first()
    environment_permission, _ = PermissionItem.objects.update_or_create(
        code=PROJECT_ENVIRONMENT_MENU_CODE,
        defaults={
            'name': '项目环境',
            'item_type': 'menu',
            'parent': config_permission,
            'route_path': '/manual-testcases/list?tab=project-environments',
            'sort_order': 8,
            'is_active': True,
            'description': '维护项目环境的URL地址、账号和密码。',
        },
    )
    view_permission, _ = PermissionItem.objects.update_or_create(
        code=PROJECT_ENVIRONMENT_VIEW_CODE,
        defaults={
            'name': '查看',
            'item_type': 'button',
            'parent': environment_permission,
            'route_path': '',
            'sort_order': 5,
            'is_active': True,
            'description': '具备查看权限，可查看项目环境列表和页面数据。',
        },
    )

    for source_code in SOURCE_PERMISSION_CODES:
        copy_role_permissions(source_code, environment_permission, RolePermission, PermissionItem)
        copy_role_permissions(source_code, view_permission, RolePermission, PermissionItem)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0029_retire_ai_generation_legacy_lifecycle_modules'),
    ]

    operations = [
        migrations.RunPython(add_manual_project_environment_permission, migrations.RunPython.noop),
    ]
