from django.db import migrations


AI_GENERATION_PERMISSION_ITEMS = [
    {
        'code': 'module:ai-generation',
        'name': 'AI用例生成',
        'item_type': 'module',
        'sort_order': 20,
    },
    {
        'code': 'menu:ai-generation:list',
        'name': 'AI用例生成',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 10,
        'route_path': '/ai-generation/list',
    },
    {
        'code': 'menu:ai-generation:foundation',
        'name': '基础配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:list',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=projects',
    },
    {
        'code': 'menu:ai-generation:projects',
        'name': '项目管理',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=projects',
    },
    {
        'code': 'menu:ai-generation:versions',
        'name': '版本管理',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=versions',
    },
    {
        'code': 'menu:ai-generation:prompt-config',
        'name': '提示词配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=prompt-config',
    },
    {
        'code': 'menu:ai-generation:ai-dev-configs',
        'name': 'AI开发配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=ai-dev-configs',
    },
    {
        'code': 'menu:ai-generation:requirement',
        'name': '需求分析',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:list',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=requirement-analysis',
    },
    {
        'code': 'menu:ai-generation:requirement-analysis',
        'name': '创建需求',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:requirement',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=requirement-analysis',
    },
    {
        'code': 'menu:ai-generation:ai-requirements',
        'name': '需求管理',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:requirement',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=ai-requirements',
    },
    {
        'code': 'menu:ai-generation:generated-testcases',
        'name': '用例生成记录',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:requirement',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=generated-testcases',
    },
    {
        'code': 'menu:ai-generation:testing',
        'name': '测试交付',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:list',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=testcases',
    },
    {
        'code': 'menu:ai-generation:testcases',
        'name': '测试用例',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=testcases',
    },
    {
        'code': 'menu:ai-generation:ui-automation-cases',
        'name': 'UI自动化用例',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=ui-automation-cases',
    },
    {
        'code': 'menu:ai-generation:reviews',
        'name': '评审列表',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=reviews',
    },
    {
        'code': 'menu:ai-generation:review-templates',
        'name': '评审模板',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=review-templates',
    },
    {
        'code': 'menu:ai-generation:executions',
        'name': '测试计划',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=executions',
    },
    {
        'code': 'menu:ai-generation:reports',
        'name': '测试报告',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:testing',
        'sort_order': 60,
        'route_path': '/ai-generation/list?tab=reports',
    },
    {
        'code': 'menu:ai-generation:development',
        'name': 'AI开发',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:list',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=ai-dev-tasks',
    },
    {
        'code': 'menu:ai-generation:ai-dev-tasks',
        'name': 'AI开发任务',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:development',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=ai-dev-tasks',
    },
    {
        'code': 'menu:ai-generation:workflow-workbench',
        'name': '流程工作台',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:development',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=workflow-workbench',
    },
    {
        'code': 'menu:home:ai-generation',
        'name': 'AI用例生成',
        'item_type': 'menu',
        'parent_code': 'menu:home:view',
        'sort_order': 10,
        'route_path': '/ai-generation/list',
    },
]


def sync_ai_generation_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in AI_GENERATION_PERMISSION_ITEMS:
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

    for item in AI_GENERATION_PERMISSION_ITEMS:
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
        ('users', '0007_add_manual_management_project_version_permissions'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_permission_items, migrations.RunPython.noop),
    ]
