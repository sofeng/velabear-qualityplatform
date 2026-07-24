from django.db import migrations


def remove_manual_report_excel_permission(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code='menu:manual-testcases:quality-report-excel').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_reorganize_manual_workspace_navigation'),
    ]

    operations = [
        migrations.RunPython(remove_manual_report_excel_permission, migrations.RunPython.noop),
    ]
