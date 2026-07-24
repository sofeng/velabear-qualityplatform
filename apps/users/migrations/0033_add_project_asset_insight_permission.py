from django.db import migrations


PERMISSIONS = [
    {
        'code': 'menu:manual-testcases:project-asset-insight',
        'name': '项目资产图谱',
        'permission_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'route_path': '/manual-testcases/list?tab=project-asset-insight',
        'sort_order': 34,
    },
    {
        'code': 'button:manual-testcases:project-asset-insight:view',
        'name': '查看项目资产图谱',
        'permission_type': 'button',
        'parent_code': 'menu:manual-testcases:project-asset-insight',
        'route_path': '/manual-testcases/list?tab=project-asset-insight',
        'sort_order': 1,
    },
    {
        'code': 'action:manual-testcases:project-asset-insight:enable',
        'name': '创建项目知识库',
        'permission_type': 'action',
        'parent_code': 'menu:manual-testcases:project-asset-insight',
        'route_path': '/manual-testcases/list?tab=project-asset-insight',
        'sort_order': 2,
    },
    {
        'code': 'action:manual-testcases:project-asset-insight:index',
        'name': '生成项目资产图谱',
        'permission_type': 'action',
        'parent_code': 'menu:manual-testcases:project-asset-insight',
        'route_path': '/manual-testcases/list?tab=project-asset-insight',
        'sort_order': 3,
    },
]

ROLE_NAMES = ['系统管理员', '管理员', '测试经理', '测试人员', '开发人员']
FALLBACK_PARENT_CODES = [
    'menu:manual-testcases:config',
    'menu:manual-testcases:knowledge-repositories',
    'button:manual-testcases:knowledge-repositories:view',
]


def add_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    Role = apps.get_model('users', 'Role')
    RolePermission = apps.get_model('users', 'RolePermission')
    parent_by_code = {
        item.code: item
        for item in PermissionItem.objects.filter(code__in={item['parent_code'] for item in PERMISSIONS})
    }
    created_items = []
    for item in PERMISSIONS:
        parent = parent_by_code.get(item['parent_code'])
        permission, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'item_type': item['permission_type'],
                'parent': parent,
                'route_path': item['route_path'],
                'sort_order': item['sort_order'],
                'is_active': True,
            },
        )
        parent_by_code[item['code']] = permission
        created_items.append(permission)

    role_ids = list(Role.objects.filter(name__in=ROLE_NAMES).values_list('id', flat=True))
    fallback_roles = RolePermission.objects.filter(
        permission_item__code__in=FALLBACK_PARENT_CODES,
    ).values_list('role_id', flat=True)
    role_ids.extend(fallback_roles)
    for role_id in set(role_ids):
        for permission in created_items:
            RolePermission.objects.get_or_create(
                role_id=role_id,
                permission_item=permission,
            )


def remove_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code__in=[item['code'] for item in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0032_add_manual_knowledge_repository_permissions'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
