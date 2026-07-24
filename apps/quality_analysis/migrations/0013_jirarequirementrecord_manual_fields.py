from django.db import migrations, models


def backfill_requirement_manual_fields(apps, schema_editor):
    JiraRequirementRecord = apps.get_model('quality_analysis', 'JiraRequirementRecord')

    for record in JiraRequirementRecord.objects.all().iterator():
        raw_fields = record.raw_fields or {}
        updates = []

        if not getattr(record, 'frontend_developer', ''):
            frontend_developer = str(raw_fields.get('customfield_10743') or '').strip()
            if frontend_developer:
                record.frontend_developer = frontend_developer
                updates.append('frontend_developer')

        if not getattr(record, 'backend_developer', ''):
            backend_developer = (
                str(raw_fields.get('customfield_10741') or '').strip() or
                str(raw_fields.get('customfield_10222') or '').strip() or
                str(record.tester or '').strip()
            )
            if backend_developer:
                record.backend_developer = backend_developer
                updates.append('backend_developer')

        if not getattr(record, 'description', ''):
            description = str(raw_fields.get('description') or '').strip()
            if description:
                record.description = description
                updates.append('description')

        if updates:
            record.save(update_fields=updates)


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0012_qualityanalysissettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='jirarequirementrecord',
            name='backend_developer',
            field=models.CharField(blank=True, max_length=100, verbose_name='后端开发'),
        ),
        migrations.AddField(
            model_name='jirarequirementrecord',
            name='description',
            field=models.TextField(blank=True, verbose_name='需求描述'),
        ),
        migrations.AddField(
            model_name='jirarequirementrecord',
            name='frontend_developer',
            field=models.CharField(blank=True, max_length=100, verbose_name='前端开发'),
        ),
        migrations.AddField(
            model_name='jirarequirementrecord',
            name='related_mindmaps',
            field=models.JSONField(blank=True, default=list, verbose_name='关联测试脑图'),
        ),
        migrations.RunPython(backfill_requirement_manual_fields, migrations.RunPython.noop),
    ]
