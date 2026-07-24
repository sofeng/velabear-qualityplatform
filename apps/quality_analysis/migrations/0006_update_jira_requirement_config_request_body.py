from urllib.parse import urlencode

from django.db import migrations


REQUIREMENT_FILTER_ID = '15943'
REQUIREMENT_REFERER = f'http://172.31.119.34:8080/issues/?filter={REQUIREMENT_FILTER_ID}'
REQUIREMENT_JQL_TEMPLATE = (
    'project = SYSWIN AND issuetype in (任务, 实施需求（二次开发）, 实施需求（合同内）, 标准化需求, 子任务-需求分拆) '
    'AND status in (产品需求待接收, 产品规划设计中, 产品设计完成, 待启动研发任务, 功能研发中, 研发技术评审, '
    '代码开发完成, 功能测试中, 测试完成待发版, 开发任务完结, 需求报告人验收中, 已交付上线, 已关闭问题, 已挂起问题) '
    'AND fixVersion = {version} ORDER BY cf[10761] DESC, cf[10747] DESC, cf[10741] ASC, key ASC, '
    'cf[10762] DESC, reporter ASC, assignee ASC, cf[10708] ASC, issuetype DESC, cf[10738] DESC'
)


def update_requirement_config_request_body(apps, schema_editor):
    JiraRequirementInterfaceConfig = apps.get_model('quality_analysis', 'JiraRequirementInterfaceConfig')

    for config in JiraRequirementInterfaceConfig.objects.all():
        config.request_body = urlencode(
            [
                ('startIndex', 0),
                ('filterId', REQUIREMENT_FILTER_ID),
                ('jql', REQUIREMENT_JQL_TEMPLATE.format(version=config.version)),
                ('layoutKey', 'list-view'),
            ]
        )
        headers = dict(config.request_headers or {})
        headers['referer'] = REQUIREMENT_REFERER
        config.request_headers = headers
        config.save(update_fields=['request_body', 'request_headers', 'updated_at'])


class Migration(migrations.Migration):
    dependencies = [
        ('quality_analysis', '0005_update_jira_bug_config_request_body'),
    ]

    operations = [
        migrations.RunPython(update_requirement_config_request_body, migrations.RunPython.noop),
    ]
