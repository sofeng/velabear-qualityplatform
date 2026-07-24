from django.db import migrations


MANAGEMENT_PERMISSION_ITEMS = [
    {
        'code': 'menu:manual-testcases:projects',
        'name': '项目',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 40,
        'route_path': '/manual-testcases/list?tab=projects',
    },
    {
        'code': 'button:manual-testcases:projects:create',
        'name': '新增项目',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:projects',
        'sort_order': 10,
    },
    {
        'code': 'button:manual-testcases:projects:edit',
        'name': '编辑项目',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:projects',
        'sort_order': 20,
    },
    {
        'code': 'button:manual-testcases:projects:delete',
        'name': '删除项目',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:projects',
        'sort_order': 30,
    },
    {
        'code': 'menu:manual-testcases:versions',
        'name': '版本',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 50,
        'route_path': '/manual-testcases/list?tab=versions',
    },
    {
        'code': 'button:manual-testcases:versions:create',
        'name': '新增版本',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:versions',
        'sort_order': 10,
    },
    {
        'code': 'button:manual-testcases:versions:edit',
        'name': '编辑版本',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:versions',
        'sort_order': 20,
    },
    {
        'code': 'button:manual-testcases:versions:delete',
        'name': '删除版本',
        'item_type': 'button',
        'parent_code': 'menu:manual-testcases:versions',
        'sort_order': 30,
    },
    {
        'code': 'action:manual-testcases:versions:set-default',
        'name': '设置默认版本',
        'item_type': 'action',
        'parent_code': 'menu:manual-testcases:versions',
        'sort_order': 40,
    },
    {
        'code': 'menu:manual-testcases:permissions',
        'name': '权限',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 60,
        'route_path': '/manual-testcases/list?tab=permissions',
    },
]


def sync_manual_management_project_version_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in MANAGEMENT_PERMISSION_ITEMS:
        defaults = {
            'name': item['name'],
            'item_type': item['item_type'],
            'route_path': item.get('route_path', ''),
            'sort_order': item.get('sort_order', 0),
            'is_active': item.get('is_active', True),
            'description': item.get('description', ''),
        }
        permission_item, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults=defaults,
        )
        item_mapping[item['code']] = permission_item

    for item in MANAGEMENT_PERMISSION_ITEMS:
        permission_item = item_mapping[item['code']]
        parent_code = item.get('parent_code')
        parent_item = (
            item_mapping.get(parent_code) or
            PermissionItem.objects.filter(code=parent_code).first()
        ) if parent_code else None
        parent_id = parent_item.id if parent_item else None
        if permission_item.parent_id != parent_id:
            permission_item.parent_id = parent_id
            permission_item.save(update_fields=['parent'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_home_card_permission_items'),
    ]

    operations = [
        migrations.RunPython(sync_manual_management_project_version_permissions, migrations.RunPython.noop),
    ]
