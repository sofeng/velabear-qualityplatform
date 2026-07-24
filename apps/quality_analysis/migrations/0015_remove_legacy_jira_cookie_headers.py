import hashlib

from django.db import migrations


LEGACY_JIRA_COOKIE_HASHES = {
    '5b2d2b41a001a321eff1bb4379a35602f63e56acc94260afad9e51d4a85cc322',
    'a5a1272a9f9851b05bfdbfc5866001316630e610abe11dde9193ed8343df090d',
}


def _is_legacy_cookie(value):
    cookie_value = str(value or '').strip()
    if not cookie_value:
        return False
    return hashlib.sha256(cookie_value.encode('utf-8')).hexdigest() in LEGACY_JIRA_COOKIE_HASHES


def _clean_config_model(model):
    for config in model.objects.all():
        headers = dict(config.request_headers or {})
        changed = False
        for key, value in list(headers.items()):
            if str(key).lower() == 'cookie' and _is_legacy_cookie(value):
                headers.pop(key, None)
                changed = True
        if changed:
            config.request_headers = headers
            config.save(update_fields=['request_headers', 'updated_at'])


def remove_legacy_jira_cookie_headers(apps, schema_editor):
    _clean_config_model(apps.get_model('quality_analysis', 'JiraInterfaceConfig'))
    _clean_config_model(apps.get_model('quality_analysis', 'JiraRequirementInterfaceConfig'))


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0014_jirarequirementrecordattachment'),
    ]

    operations = [
        migrations.RunPython(remove_legacy_jira_cookie_headers, migrations.RunPython.noop),
    ]
