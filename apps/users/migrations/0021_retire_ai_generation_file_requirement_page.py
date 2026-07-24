from django.db import migrations


def retire_ai_generation_file_requirement_page(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')

    PermissionItem.objects.filter(code='menu:ai-generation:requirement').update(
        route_path='/ai-generation/list?tab=ai-requirements',
        description='AI需求入口已退役文件创建需求页签，默认进入需求管理。',
    )
    PermissionItem.objects.filter(code='menu:ai-generation:ai-requirements').update(
        route_path='/ai-generation/list?tab=ai-requirements',
        is_active=True,
    )
    PermissionItem.objects.filter(code='menu:ai-generation:requirement-analysis').update(
        route_path='/ai-generation/list?tab=ai-requirements',
        is_active=True,
        description='文件创建需求页面已退役；保留权限编码用于历史兼容，旧链接重定向到需求管理。',
    )
    PermissionItem.objects.filter(code='button:ai-generation:requirement-analysis:view').update(
        is_active=True,
        description='文件创建需求页面已退役；查看权限保留用于历史角色访问需求管理。',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_retarget_ai_generation_manual_requirement_permission'),
    ]

    operations = [
        migrations.RunPython(retire_ai_generation_file_requirement_page, migrations.RunPython.noop),
    ]
