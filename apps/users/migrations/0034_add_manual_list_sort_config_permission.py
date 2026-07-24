from django.db import migrations


MENU_CODE = 'menu:manual-testcases:list-sort-config'
VIEW_CODE = 'button:manual-testcases:list-sort-config:view'
MANAGE_CODE = 'action:manual-testcases:list-sort-config:manage'
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


def add_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    config_permission = PermissionItem.objects.filter(code='menu:manual-testcases:config').first()
    menu_permission, _ = PermissionItem.objects.update_or_create(
        code=MENU_CODE,
        defaults={
            'name': '列表排序',
            'item_type': 'menu',
            'parent': config_permission,
            'route_path': '/manual-testcases/list?tab=list-sort-config',
            'sort_order': 36,
            'is_active': True,
            'description': '维护思源质量平台页面筛选条件与列表字段后台默认排序。',
        },
    )
    view_permission, _ = PermissionItem.objects.update_or_create(
        code=VIEW_CODE,
        defaults={
            'name': '查看',
            'item_type': 'button',
            'parent': menu_permission,
            'route_path': '',
            'sort_order': 1,
            'is_active': True,
        },
    )
    manage_permission, _ = PermissionItem.objects.update_or_create(
        code=MANAGE_CODE,
        defaults={
            'name': '维护配置',
            'item_type': 'action',
            'parent': menu_permission,
            'route_path': '',
            'sort_order': 2,
            'is_active': True,
        },
    )

    for source_code in SOURCE_PERMISSION_CODES:
        copy_role_permissions(source_code, menu_permission, RolePermission, PermissionItem)
        copy_role_permissions(source_code, view_permission, RolePermission, PermissionItem)
        copy_role_permissions(source_code, manage_permission, RolePermission, PermissionItem)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0033_add_project_asset_insight_permission'),
    ]

    operations = [
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
    ]
