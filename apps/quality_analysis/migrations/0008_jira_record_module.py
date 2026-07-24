from django.db import migrations, models


def populate_module_from_raw_fields(apps, schema_editor):
    for model_name in ('JiraBugRecord', 'JiraRequirementRecord'):
        model = apps.get_model('quality_analysis', model_name)
        for record in model.objects.all().iterator():
            raw_fields = record.raw_fields or {}
            module = str(raw_fields.get('components') or '').strip()
            if not module:
                continue
            record.module = module
            record.save(update_fields=['module'])


def clear_module_field(apps, schema_editor):
    for model_name in ('JiraBugRecord', 'JiraRequirementRecord'):
        model = apps.get_model('quality_analysis', model_name)
        model.objects.exclude(module='').update(module='')


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0007_normalize_jira_versions'),
    ]

    operations = [
        migrations.AddField(
            model_name='jirabugrecord',
            name='module',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='模块'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='jirarequirementrecord',
            name='module',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='模块'),
            preserve_default=False,
        ),
        migrations.RunPython(populate_module_from_raw_fields, clear_module_field),
    ]
