from django.db import migrations


HOME_PERMISSION_ITEMS = [
    {
        'code': 'module:home',
        'name': '首页',
        'item_type': 'module',
        'sort_order': 5,
    },
    {
        'code': 'menu:home:view',
        'name': '首页',
        'item_type': 'menu',
        'parent_code': 'module:home',
        'sort_order': 10,
        'route_path': '/home',
    },
    {
        'code': 'menu:home:ai-generation',
        'name': 'AI用例生成',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 10,
        'route_path': '/ai-generation/requirement-analysis',
    },
    {
        'code': 'menu:home:api-testing',
        'name': '接口测试',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 20,
        'route_path': '/api-testing/dashboard',
    },
    {
        'code': 'menu:home:ui-automation',
        'name': 'UI自动化测试',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 30,
        'route_path': '/ui-automation/dashboard',
    },
    {
        'code': 'menu:home:data-factory',
        'name': '数据工厂',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 40,
        'route_path': '',
    },
    {
        'code': 'menu:home:ai-intelligent-mode',
        'name': 'AI智能模式',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 50,
        'route_path': '/ai-intelligent-mode/testing',
    },
    {
        'code': 'menu:home:assistant',
        'name': 'AI评测师',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 60,
        'route_path': '/ai-generation/assistant',
    },
    {
        'code': 'menu:home:configuration',
        'name': '配置中心',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 70,
        'route_path': '/configuration/ai-model',
    },
    {
        'code': 'menu:home:manual-testcases',
        'name': '思源研发管理',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 80,
        'route_path': '/manual-testcases/list',
    },
]


def sync_home_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in HOME_PERMISSION_ITEMS:
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

    for item in HOME_PERMISSION_ITEMS:
        permission_item = item_mapping[item['code']]
        parent_code = item.get('parent_code')
        parent_item = item_mapping.get(parent_code) if parent_code else None
        parent_id = parent_item.id if parent_item else None
        if permission_item.parent_id != parent_id:
            permission_item.parent_id = parent_id
            permission_item.save(update_fields=['parent'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_sync_manual_testcase_permission_tree'),
    ]

    operations = [
        migrations.RunPython(sync_home_permission_items, migrations.RunPython.noop),
    ]
