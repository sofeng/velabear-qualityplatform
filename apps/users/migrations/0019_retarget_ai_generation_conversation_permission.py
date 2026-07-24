from django.db import migrations


def retarget_ai_generation_conversation_permission(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code='menu:ai-generation:conversation').update(
        name='AI产品',
        route_path='/ai-generation/products',
        is_active=True,
        description='AI产品与 CodexChat 会话入口权限；旧 AI会话页面已移除。',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_add_page_view_permissions'),
    ]

    operations = [
        migrations.RunPython(retarget_ai_generation_conversation_permission, migrations.RunPython.noop),
    ]
