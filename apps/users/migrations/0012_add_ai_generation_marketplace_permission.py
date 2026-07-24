from django.db import migrations


AI_GENERATION_MARKETPLACE_PERMISSION_ITEM = {
    'code': 'menu:ai-generation:marketplace',
    'name': '能力市场',
    'item_type': 'menu',
    'parent_code': 'menu:ai-generation:foundation',
    'sort_order': 95,
    'route_path': '/ai-generation/list?tab=marketplace',
    'description': '管理 AI研发平台工具箱能力来源、市场目录和导入记录。',
}


def sync_ai_generation_marketplace_permission_item(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    parent = PermissionItem.objects.filter(code=AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['parent_code']).first()
    PermissionItem.objects.update_or_create(
        code=AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['code'],
        defaults={
            'name': AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['name'],
            'item_type': AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['item_type'],
            'parent': parent,
            'route_path': AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['route_path'],
            'sort_order': AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['sort_order'],
            'is_active': True,
            'description': AI_GENERATION_MARKETPLACE_PERMISSION_ITEM['description'],
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_add_ai_generation_capability_permissions'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_marketplace_permission_item, migrations.RunPython.noop),
    ]
