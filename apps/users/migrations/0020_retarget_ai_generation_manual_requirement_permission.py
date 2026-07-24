from django.db import migrations


def retarget_ai_generation_manual_requirement_permission(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code='menu:ai-generation:requirement').update(
        route_path='/ai-generation/list?tab=requirement-file-create',
        description='AI需求入口已清理手动创建需求页签，默认进入文件创建需求。',
    )
    PermissionItem.objects.filter(code='menu:ai-generation:requirement-analysis').update(
        name='文件创建需求',
        route_path='/ai-generation/list?tab=requirement-file-create',
        is_active=True,
        description='旧手动创建需求入口已退役，保留权限编码并重定向到文件创建需求。',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_retarget_ai_generation_conversation_permission'),
    ]

    operations = [
        migrations.RunPython(retarget_ai_generation_manual_requirement_permission, migrations.RunPython.noop),
    ]
