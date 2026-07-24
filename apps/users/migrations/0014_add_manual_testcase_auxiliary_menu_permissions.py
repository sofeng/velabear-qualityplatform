from django.db import migrations


MANUAL_TESTCASE_AUXILIARY_PERMISSION_ITEMS = [
    {
        'code': 'menu:manual-testcases:snapshots',
        'name': '快照文件管理',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 20,
        'route_path': '/manual-testcases/snapshots',
    },
    {
        'code': 'menu:manual-testcases:recordings',
        'name': '录制结果管理',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 30,
        'route_path': '/manual-testcases/recordings',
    },
    {
        'code': 'menu:manual-testcases:controlled-browser-lab',
        'name': '受控浏览器控件测试',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 40,
        'route_path': '/manual-testcases/controlled-browser-lab',
    },
    {
        'code': 'menu:manual-testcases:flows',
        'name': '流程管理',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 50,
        'route_path': '/manual-testcases/flows',
    },
    {
        'code': 'menu:manual-testcases:visual-flow',
        'name': '可视化流程编辑器',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 60,
        'route_path': '/manual-testcases/visual-flow',
    },
    {
        'code': 'menu:manual-testcases:workflow-workbench',
        'name': '流程工作台',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 70,
        'route_path': '/manual-testcases/workflow-workbench',
    },
]


def sync_manual_testcase_auxiliary_menu_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in MANUAL_TESTCASE_AUXILIARY_PERMISSION_ITEMS:
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

    for item in MANUAL_TESTCASE_AUXILIARY_PERMISSION_ITEMS:
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
        ('users', '0013_add_ai_generation_file_permission'),
    ]

    operations = [
        migrations.RunPython(sync_manual_testcase_auxiliary_menu_permissions, migrations.RunPython.noop),
    ]
