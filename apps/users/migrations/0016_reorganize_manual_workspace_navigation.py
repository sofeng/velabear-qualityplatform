from django.db import migrations


MANUAL_TESTCASE_NAVIGATION_PERMISSION_ITEMS = [
    {
        'code': 'module:manual-testcases',
        'name': '思源研发管理',
        'item_type': 'module',
        'sort_order': 70,
    },
    {
        'code': 'menu:manual-testcases:list',
        'name': '总览',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=requirement-overview',
    },
    {
        'code': 'menu:manual-testcases:requirement-overview',
        'name': '需求总览',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:list',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=requirement-overview',
    },
    {
        'code': 'menu:manual-testcases:testing-overview',
        'name': '测试总览',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:list',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=testing-overview',
    },
    {
        'code': 'menu:manual-testcases:product',
        'name': '需求',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=version-requirements',
    },
    {
        'code': 'menu:manual-testcases:version-requirements',
        'name': '版本需求',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:product',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=version-requirements',
    },
    {
        'code': 'menu:manual-testcases:requirement-records',
        'name': 'JIRA需求数据',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:product',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=requirement-records',
    },
    {
        'code': 'menu:manual-testcases:development',
        'name': '开发',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=devselftest',
    },
    {
        'code': 'menu:manual-testcases:devselftest',
        'name': '自测测试点',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:development',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=devselftest',
    },
    {
        'code': 'menu:manual-testcases:technical-solution-designs',
        'name': '技术方案设计',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:development',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=technical-solution-designs',
    },
    {
        'code': 'menu:manual-testcases:testing',
        'name': '测试',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 40,
        'route_path': '/manual-testcases/list?tab=mindmaps',
    },
    {
        'code': 'menu:manual-testcases:mindmaps',
        'name': '测试脑图',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:testing',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=mindmaps',
    },
    {
        'code': 'menu:manual-testcases:testcases',
        'name': '测试用例',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:testing',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=testcases',
    },
    {
        'code': 'menu:manual-testcases:testpoints',
        'name': '测试点',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:testing',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=testpoints',
    },
    {
        'code': 'menu:manual-testcases:defect',
        'name': '缺陷',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 50,
        'route_path': '/manual-testcases/list?tab=version-defects',
    },
    {
        'code': 'menu:manual-testcases:version-defects',
        'name': '版本缺陷',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:defect',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=version-defects',
    },
    {
        'code': 'menu:manual-testcases:bug-records',
        'name': '线上缺陷',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:defect',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=bug-records',
    },
    {
        'code': 'menu:manual-testcases:reports',
        'name': '报告',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 60,
        'route_path': '/manual-testcases/list?tab=quality-report-list',
    },
    {
        'code': 'menu:manual-testcases:quality-report-list',
        'name': '报告列表',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:reports',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=quality-report-list',
    },
    {
        'code': 'menu:manual-testcases:quality-report-live',
        'name': '实时质量分析',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:reports',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=quality-report-live',
    },
    {
        'code': 'menu:manual-testcases:quality-report-excel',
        'name': 'Excel专项图表',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:reports',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=quality-report-excel',
    },
    {
        'code': 'menu:manual-testcases:config',
        'name': '配置',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 70,
        'route_path': '/manual-testcases/list?tab=configs',
    },
    {
        'code': 'menu:manual-testcases:configs',
        'name': 'JIRA接口配置',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=configs',
    },
    {
        'code': 'menu:manual-testcases:other-settings',
        'name': 'JIRA编号URL前缀配置',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=other-settings',
    },
    {
        'code': 'menu:manual-testcases:defect-notifications',
        'name': '邮件模板配置',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=email-template-config',
    },
    {
        'code': 'menu:manual-testcases:defect-notifications:email-config',
        'name': '邮件配置',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:defect-notifications',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=email-config',
    },
    {
        'code': 'menu:manual-testcases:defect-notifications:test-email',
        'name': '测试邮件',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:defect-notifications',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=test-email',
    },
    {
        'code': 'menu:manual-testcases:defect-notifications:notification-settings',
        'name': '消息提醒',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:defect-notifications',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=notification-settings',
    },
    {
        'code': 'menu:manual-testcases:workflow-workbench',
        'name': '流程工作台',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:config',
        'sort_order': 40,
        'route_path': '/manual-testcases/workflow-workbench',
    },
    {
        'code': 'menu:manual-testcases:management',
        'name': '管理',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 80,
        'route_path': '/manual-testcases/list?tab=members',
    },
    {
        'code': 'menu:manual-testcases:members',
        'name': '成员',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=members',
    },
    {
        'code': 'menu:manual-testcases:groups',
        'name': '组别',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=groups',
    },
    {
        'code': 'menu:manual-testcases:roles',
        'name': '角色',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 30,
        'route_path': '/manual-testcases/list?tab=roles',
    },
    {
        'code': 'menu:manual-testcases:projects',
        'name': '项目',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 40,
        'route_path': '/manual-testcases/list?tab=projects',
    },
    {
        'code': 'menu:manual-testcases:versions',
        'name': '版本',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 50,
        'route_path': '/manual-testcases/list?tab=versions',
    },
    {
        'code': 'menu:manual-testcases:permissions',
        'name': '权限',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:management',
        'sort_order': 60,
        'route_path': '/manual-testcases/list?tab=permissions',
    },
    {
        'code': 'menu:manual-testcases:permissions:ui-role-permissions',
        'name': 'UI角色权限',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:permissions',
        'sort_order': 10,
        'route_path': '/manual-testcases/list?tab=permissions',
    },
    {
        'code': 'menu:manual-testcases:permissions:permission-catalog',
        'name': '权限目录',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:permissions',
        'sort_order': 20,
        'route_path': '/manual-testcases/list?tab=permissions',
    },
    {
        'code': 'menu:manual-testcases:recording',
        'name': '录制',
        'item_type': 'menu',
        'parent_code': 'module:manual-testcases',
        'sort_order': 90,
        'route_path': '/manual-testcases/snapshots',
    },
    {
        'code': 'menu:manual-testcases:snapshots',
        'name': '快照文件管理',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:recording',
        'sort_order': 10,
        'route_path': '/manual-testcases/snapshots',
    },
    {
        'code': 'menu:manual-testcases:recordings',
        'name': '录制结果管理',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:recording',
        'sort_order': 20,
        'route_path': '/manual-testcases/recordings',
    },
    {
        'code': 'menu:manual-testcases:controlled-browser-lab',
        'name': '受控浏览器控件测试',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:recording',
        'sort_order': 30,
        'route_path': '/manual-testcases/controlled-browser-lab',
    },
    {
        'code': 'menu:manual-testcases:flows',
        'name': '流程管理',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:recording',
        'sort_order': 40,
        'route_path': '/manual-testcases/flows',
    },
    {
        'code': 'menu:manual-testcases:visual-flow',
        'name': '可视化流程编辑器',
        'item_type': 'menu',
        'parent_code': 'menu:manual-testcases:recording',
        'sort_order': 50,
        'route_path': '/manual-testcases/visual-flow',
    },
]


def sync_manual_testcase_navigation_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in MANUAL_TESTCASE_NAVIGATION_PERMISSION_ITEMS:
        defaults = {
            'name': item['name'],
            'item_type': item['item_type'],
            'route_path': item.get('route_path', ''),
            'sort_order': item.get('sort_order', 0),
            'is_active': item.get('is_active', True),
            'description': item.get('description', ''),
        }
        permission_item, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults=defaults,
        )
        item_mapping[item['code']] = permission_item

    for item in MANUAL_TESTCASE_NAVIGATION_PERMISSION_ITEMS:
        permission_item = item_mapping[item['code']]
        parent_code = item.get('parent_code')
        parent_item = (
            item_mapping.get(parent_code) or
            PermissionItem.objects.filter(code=parent_code).first()
        ) if parent_code else None
        parent_id = parent_item.id if parent_item else None
        if permission_item.parent_id != parent_id:
            permission_item.parent_id = parent_id
            permission_item.save(update_fields=['parent'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_promote_ai_generation_primary_tabs'),
    ]

    operations = [
        migrations.RunPython(sync_manual_testcase_navigation_permissions, migrations.RunPython.noop),
    ]
