import re

from django.db import migrations


def normalize_jira_version(value):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if not text:
        return ''

    normalized = text.split('发版', 1)[0].strip()
    return normalized or text


def normalize_record_versions(apps, model_name):
    model = apps.get_model('quality_analysis', model_name)
    grouped_records = {}
    duplicate_ids = []

    records = list(model.objects.all().order_by('-synced_at', '-updated_at', '-id'))
    for record in records:
        normalized_version = normalize_jira_version(record.version)
        group_key = (normalized_version, record.issue_key)
        if group_key in grouped_records:
            duplicate_ids.append(record.id)
            continue
        grouped_records[group_key] = record.id

    if duplicate_ids:
        model.objects.filter(id__in=duplicate_ids).delete()

    for (normalized_version, _issue_key), record_id in grouped_records.items():
        model.objects.filter(id=record_id).exclude(version=normalized_version).update(version=normalized_version)


def normalize_config_versions(apps, config_model_name, record_model_name):
    config_model = apps.get_model('quality_analysis', config_model_name)
    record_model = apps.get_model('quality_analysis', record_model_name)
    keepers = {}
    duplicate_ids = []
    reassignments = []

    configs = list(config_model.objects.all().order_by('-updated_at', '-created_at', '-id'))
    for config in configs:
        normalized_version = normalize_jira_version(config.version)
        if normalized_version in keepers:
            duplicate_ids.append(config.id)
            reassignments.append((config.id, keepers[normalized_version]))
            continue
        keepers[normalized_version] = config.id

    for duplicate_id, keeper_id in reassignments:
        record_model.objects.filter(config_id=duplicate_id).update(config_id=keeper_id)

    if duplicate_ids:
        config_model.objects.filter(id__in=duplicate_ids).delete()

    for normalized_version, keeper_id in keepers.items():
        config_model.objects.filter(id=keeper_id).exclude(version=normalized_version).update(version=normalized_version)


def normalize_all_jira_versions(apps, schema_editor):
    normalize_record_versions(apps, 'JiraBugRecord')
    normalize_record_versions(apps, 'JiraRequirementRecord')
    normalize_config_versions(apps, 'JiraInterfaceConfig', 'JiraBugRecord')
    normalize_config_versions(apps, 'JiraRequirementInterfaceConfig', 'JiraRequirementRecord')


class Migration(migrations.Migration):
    dependencies = [
        ('quality_analysis', '0006_update_jira_requirement_config_request_body'),
    ]

    operations = [
        migrations.RunPython(normalize_all_jira_versions, migrations.RunPython.noop),
    ]
