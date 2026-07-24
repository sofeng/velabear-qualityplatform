from django.db import migrations


def retire_ai_assessment_module(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')

    PermissionItem.objects.filter(code='menu:home:assistant').update(
        route_path='/home',
        is_active=False,
        description='AI assessment module retired; historical links redirect to home.',
    )
    PermissionItem.objects.filter(code='menu:configuration:dify').update(
        route_path='/configuration/ai-model',
        is_active=False,
        description='Dify configuration page retired with the AI assessment module.',
    )
    PermissionItem.objects.filter(code='button:configuration:dify:view').update(
        is_active=False,
        description='Dify configuration page retired with the AI assessment module.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_retire_ai_generation_workflow_workbench_page'),
    ]

    operations = [
        migrations.RunPython(retire_ai_assessment_module, migrations.RunPython.noop),
    ]
