from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testcases', '0015_playwright_automation_script'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualtestcasemindmap',
            name='mindmap_scope',
            field=models.CharField(
                choices=[
                    ('testing', 'Testing'),
                    ('requirement_analysis', 'Requirement analysis'),
                ],
                db_index=True,
                default='testing',
                max_length=40,
                verbose_name='Mindmap scope',
            ),
        ),
    ]
