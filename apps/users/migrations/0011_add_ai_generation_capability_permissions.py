from django.db import migrations


AI_GENERATION_CAPABILITY_PERMISSION_ITEMS = [
    {
        'code': 'menu:ai-generation:skill',
        'name': 'Skill',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 60,
        'route_path': '/ai-generation/list?tab=skill',
    },
    {
        'code': 'menu:ai-generation:agent',
        'name': 'Agent',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 70,
        'route_path': '/ai-generation/list?tab=agent',
    },
    {
        'code': 'menu:ai-generation:flow',
        'name': 'Flow',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 80,
        'route_path': '/ai-generation/list?tab=flow',
    },
    {
        'code': 'menu:ai-generation:mcp',
        'name': 'MCP',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 90,
        'route_path': '/ai-generation/list?tab=mcp',
    },
    {
        'code': 'menu:ai-generation:ci-cd',
        'name': 'CI/CD',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 100,
        'route_path': '/ai-generation/list?tab=ci-cd',
    },
]


def sync_ai_generation_capability_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in AI_GENERATION_CAPABILITY_PERMISSION_ITEMS:
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

    for item in AI_GENERATION_CAPABILITY_PERMISSION_ITEMS:
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
        ('users', '0010_rename_ai_generation_module_labels'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_capability_permission_items, migrations.RunPython.noop),
    ]
