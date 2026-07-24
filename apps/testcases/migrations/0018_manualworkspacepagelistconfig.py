from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('testcases', '0017_alter_devselftestrecord_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManualWorkspacePageListConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('module_key', models.CharField(default='manual-testcases', max_length=80, verbose_name='Module key')),
                ('page_key', models.CharField(max_length=120, verbose_name='Page key')),
                ('filter_conditions', models.JSONField(blank=True, default=list, verbose_name='Filter conditions')),
                ('columns', models.JSONField(blank=True, default=list, verbose_name='List columns')),
                ('version', models.PositiveIntegerField(default=1, verbose_name='Config version')),
                ('created_at', models.DateTimeField(default=timezone.now, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='updated_manual_workspace_page_list_configs',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Updated by',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Manual workspace page list config',
                'verbose_name_plural': 'Manual workspace page list configs',
                'db_table': 'manual_workspace_page_list_configs',
                'ordering': ['module_key', 'page_key'],
            },
        ),
        migrations.AddConstraint(
            model_name='manualworkspacepagelistconfig',
            constraint=models.UniqueConstraint(
                fields=('module_key', 'page_key'),
                name='manual_workspace_page_list_config_unique',
            ),
        ),
    ]
