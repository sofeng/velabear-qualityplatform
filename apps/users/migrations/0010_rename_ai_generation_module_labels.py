from django.db import migrations


RENAME_MAP = {
    'module:ai-generation': 'AI研发平台',
    'menu:ai-generation:list': 'AI研发平台',
    'menu:home:ai-generation': 'AI研发平台',
}

REVERSE_RENAME_MAP = {
    'module:ai-generation': 'AI用例生成',
    'menu:ai-generation:list': 'AI用例生成',
    'menu:home:ai-generation': 'AI用例生成',
}


def rename_ai_generation_labels(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    for code, name in RENAME_MAP.items():
        PermissionItem.objects.filter(code=code).update(name=name)


def revert_ai_generation_labels(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    for code, name in REVERSE_RENAME_MAP.items():
        PermissionItem.objects.filter(code=code).update(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_add_ai_generation_operations_permissions'),
    ]

    operations = [
        migrations.RunPython(rename_ai_generation_labels, revert_ai_generation_labels),
    ]
