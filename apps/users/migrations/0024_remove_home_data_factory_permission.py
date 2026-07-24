from django.db import migrations


def remove_home_data_factory_permission(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code='menu:home:data-factory').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_retire_ai_assessment_module'),
        ('users', '0023_retire_ai_generation_toolbox_page'),
    ]

    operations = [
        migrations.RunPython(remove_home_data_factory_permission, migrations.RunPython.noop),
    ]
