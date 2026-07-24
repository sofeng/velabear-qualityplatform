from urllib.parse import urlencode

from django.db import migrations


BUG_FILTER_ID = '16128'


def update_bug_config_request_body(apps, schema_editor):
    JiraInterfaceConfig = apps.get_model('quality_analysis', 'JiraInterfaceConfig')

    for config in JiraInterfaceConfig.objects.all():
        version = config.version or '26-04.15发版（8.2.0）'
        config.request_body = urlencode(
            {
                'startIndex': 0,
                'filterId': BUG_FILTER_ID,
                'jql': (
                    'project = SYSWIN AND issuetype = BUG AND '
                    f'fixVersion = {version} '
                    'ORDER BY created DESC, cf[10747] DESC, cf[10741] ASC, key ASC, '
                    'cf[10762] DESC, reporter ASC, assignee ASC, cf[10708] ASC, '
                    'issuetype DESC, cf[10738] DESC'
                ),
                'layoutKey': 'list-view',
            }
        )

        headers = dict(config.request_headers or {})
        headers['referer'] = f'http://172.31.119.34:8080/issues/?filter={BUG_FILTER_ID}'
        config.request_headers = headers
        config.save(update_fields=['request_body', 'request_headers', 'updated_at'])


class Migration(migrations.Migration):
    dependencies = [
        ('quality_analysis', '0004_seed_jira_requirement_config'),
    ]

    operations = [
        migrations.RunPython(update_bug_config_request_body, migrations.RunPython.noop),
    ]
