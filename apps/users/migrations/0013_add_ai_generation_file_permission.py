from django.db import migrations


AI_GENERATION_FILE_PERMISSION_ITEM = {
    'code': 'menu:ai-generation:files',
    'name': '文件',
    'item_type': 'menu',
    'parent_code': 'menu:ai-generation:list',
    'sort_order': 15,
    'route_path': '/ai-generation/list?tab=ai-files',
    'description': '管理AI会话和上传需求文档产生的文件及其研发链路关系。',
}


def sync_ai_generation_file_permission_item(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    parent = PermissionItem.objects.filter(code=AI_GENERATION_FILE_PERMISSION_ITEM['parent_code']).first()
    PermissionItem.objects.update_or_create(
        code=AI_GENERATION_FILE_PERMISSION_ITEM['code'],
        defaults={
            'name': AI_GENERATION_FILE_PERMISSION_ITEM['name'],
            'item_type': AI_GENERATION_FILE_PERMISSION_ITEM['item_type'],
            'parent': parent,
            'route_path': AI_GENERATION_FILE_PERMISSION_ITEM['route_path'],
            'sort_order': AI_GENERATION_FILE_PERMISSION_ITEM['sort_order'],
            'is_active': True,
            'description': AI_GENERATION_FILE_PERMISSION_ITEM['description'],
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_add_ai_generation_marketplace_permission'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_file_permission_item, migrations.RunPython.noop),
    ]
