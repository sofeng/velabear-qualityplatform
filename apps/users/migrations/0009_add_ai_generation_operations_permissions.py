from django.db import migrations


AI_GENERATION_OPERATION_PERMISSION_ITEMS = [
    {
        'code': 'menu:ai-generation:operations',
        'name': '自动化运维',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:list',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=deployment-targets',
    },
    {
        'code': 'menu:ai-generation:deployment-targets',
        'name': '发布目标',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=deployment-targets',
    },
    {
        'code': 'menu:ai-generation:deployment-templates',
        'name': '部署模板',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=deployment-templates',
    },
    {
        'code': 'menu:ai-generation:build-artifacts',
        'name': '构建制品',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=build-artifacts',
    },
    {
        'code': 'menu:ai-generation:deployment-executions',
        'name': '发布任务',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=deployment-executions',
    },
    {
        'code': 'menu:ai-generation:rollback-records',
        'name': '回滚记录',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=rollback-records',
    },
]


def sync_ai_generation_operation_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in AI_GENERATION_OPERATION_PERMISSION_ITEMS:
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

    for item in AI_GENERATION_OPERATION_PERMISSION_ITEMS:
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
        ('users', '0008_sync_ai_generation_workspace_permission_tree'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_operation_permission_items, migrations.RunPython.noop),
    ]
