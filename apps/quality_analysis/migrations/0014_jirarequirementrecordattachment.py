from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0013_jirarequirementrecord_manual_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JiraRequirementRecordAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='附件名称')),
                ('file', models.FileField(upload_to='requirement_attachments/%Y/%m/', verbose_name='文件')),
                ('uploaded_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='上传时间')),
                (
                    'requirement',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='attachments',
                        to='quality_analysis.jirarequirementrecord',
                        verbose_name='关联需求',
                    ),
                ),
                (
                    'uploaded_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='uploaded_requirement_attachments',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='上传人',
                    ),
                ),
            ],
            options={
                'verbose_name': '需求附件',
                'verbose_name_plural': '需求附件',
                'db_table': 'quality_analysis_jira_requirement_record_attachments',
                'ordering': ['uploaded_at', 'id'],
            },
        ),
    ]
