from django.db import migrations


KNOWLEDGE_REPOSITORY_PERMISSIONS = [
    {
        'code': 'menu:manual-testcases:knowledge-repositories',
        'name': 'Git/GitHub仓库配置',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'route_path': '/manual-testcases/list?tab=knowledge-repositories',
        'sort_order': 13,
        'description': '配置知识库对象的 Git/GitHub 仓库、本地仓库、授权和索引范围。',
    },
    {
        'code': 'button:manual-testcases:knowledge-repositories:view',
        'name': '查看',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 5,
        'description': '查看仓库配置、索引记录和知识图谱来源。',
    },
    {
        'code': 'button:manual-testcases:knowledge-repositories:create',
        'name': '新增',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 10,
        'description': '新增知识库对象仓库配置。',
    },
    {
        'code': 'button:manual-testcases:knowledge-repositories:edit',
        'name': '编辑',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 20,
        'description': '编辑知识库对象仓库配置。',
    },
    {
        'code': 'button:manual-testcases:knowledge-repositories:delete',
        'name': '删除',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 30,
        'description': '删除知识库对象仓库配置。',
    },
    {
        'code': 'action:manual-testcases:knowledge-repositories:test-connection',
        'name': '测试连接',
        'item_type': 'action',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 40,
        'description': '测试 Git/GitHub 或本地仓库连接。',
    },
    {
        'code': 'action:manual-testcases:knowledge-repositories:index',
        'name': '触发索引',
        'item_type': 'action',
        'parent_code': 'menu:manual-testcases:knowledge-repositories',
        'route_path': '',
        'sort_order': 50,
        'description': '触发仓库索引并生成 roadmap 与双链图谱。',
    },
]

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


def add_manual_knowledge_repository_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    created_permissions = {}
    for item in KNOWLEDGE_REPOSITORY_PERMISSIONS:
        parent = PermissionItem.objects.filter(code=item['parent_code']).first()
        permission, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'item_type': item['item_type'],
                'parent': parent,
                'route_path': item['route_path'],
                'sort_order': item['sort_order'],
                'is_active': True,
                'description': item['description'],
            },
        )
        created_permissions[item['code']] = permission

    for permission in created_permissions.values():
        for source_code in SOURCE_PERMISSION_CODES:
            copy_role_permissions(source_code, permission, RolePermission, PermissionItem)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0031_consolidate_configuration_center_into_ai_workshop'),
    ]

    operations = [
        migrations.RunPython(add_manual_knowledge_repository_permissions, migrations.RunPython.noop),
    ]
