from django.db import migrations


AI_GENERATION_PRIMARY_TAB_PERMISSION_ITEMS = [
    {
        'code': 'module:ai-generation',
        'name': 'AI研发平台',
        'item_type': 'module',
        'sort_order': 20,
    },
    {
        'code': 'menu:ai-generation:list',
        'name': 'AI研发平台',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 0,
        'route_path': '/ai-generation/list',
        'is_active': False,
        'description': '旧版AI研发平台入口，仅保留历史权限兼容；顶部菜单使用9个一级页签。',
    },
    {
        'code': 'menu:ai-generation:conversation',
        'name': 'AI会话',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=ai-conversations',
    },
    {
        'code': 'menu:ai-generation:files',
        'name': '文件',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=ai-files',
        'description': '管理AI会话和上传需求文档产生的文件及其研发链路关系。',
    },
    {
        'code': 'menu:ai-generation:requirement',
        'name': 'AI需求',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=requirement-analysis',
    },
    {
        'code': 'menu:ai-generation:development',
        'name': 'AI开发',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=ai-dev-tasks',
    },
    {
        'code': 'menu:ai-generation:testing',
        'name': 'AI测试',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=testcases',
    },
    {
        'code': 'menu:ai-generation:defect',
        'name': 'AI缺陷',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 60,
        'route_path': '/ai-generation/list?tab=ai-dev-defects',
    },
    {
        'code': 'menu:ai-generation:operations',
        'name': 'AI运维',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 70,
        'route_path': '/ai-generation/list?tab=deployment-targets',
    },
    {
        'code': 'menu:ai-generation:tools',
        'name': '工具箱',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 80,
        'route_path': '/ai-generation/list?tab=ai-dev-test-tool-configs',
    },
    {
        'code': 'menu:ai-generation:foundation',
        'name': '基础配置',
        'item_type': 'menu',
        'parent_code': 'module:ai-generation',
        'sort_order': 90,
        'route_path': '/ai-generation/list?tab=projects',
    },
    {
        'code': 'menu:ai-generation:new-project-blueprints',
        'name': '0到1基线',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:files',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=new-project-blueprints',
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
        'code': 'menu:ai-generation:ai-dev-build-configs',
        'name': '构建配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=ai-dev-build-configs',
    },
    {
        'code': 'menu:ai-generation:deployment-targets',
        'name': '发布目标',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=deployment-targets',
    },
    {
        'code': 'menu:ai-generation:deployment-templates',
        'name': '部署模板',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=deployment-templates',
    },
    {
        'code': 'menu:ai-generation:build-artifacts',
        'name': '构建制品',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=build-artifacts',
    },
    {
        'code': 'menu:ai-generation:deployment-executions',
        'name': '发布任务',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=deployment-executions',
    },
    {
        'code': 'menu:ai-generation:rollback-records',
        'name': '回滚记录',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:operations',
        'sort_order': 60,
        'route_path': '/ai-generation/list?tab=rollback-records',
    },
    {
        'code': 'menu:ai-generation:ai-dev-test-tool-configs',
        'name': 'TestTools',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 10,
        'route_path': '/ai-generation/list?tab=ai-dev-test-tool-configs',
    },
    {
        'code': 'menu:ai-generation:prompt-config',
        'name': 'Prompt',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 20,
        'route_path': '/ai-generation/list?tab=prompt-config',
    },
    {
        'code': 'menu:ai-generation:skill',
        'name': 'Skill',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=skill',
    },
    {
        'code': 'menu:ai-generation:agent',
        'name': 'Agent',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=agent',
    },
    {
        'code': 'menu:ai-generation:flow',
        'name': 'Flow',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 50,
        'route_path': '/ai-generation/list?tab=flow',
    },
    {
        'code': 'menu:ai-generation:mcp',
        'name': 'MCP',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 60,
        'route_path': '/ai-generation/list?tab=mcp',
    },
    {
        'code': 'menu:ai-generation:marketplace',
        'name': '能力市场',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 70,
        'route_path': '/ai-generation/list?tab=marketplace',
        'description': '管理 AI研发平台工具箱能力来源、市场目录和导入记录。',
    },
    {
        'code': 'menu:ai-generation:ai-dev-llm-configs',
        'name': 'Model',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 80,
        'route_path': '/ai-generation/list?tab=ai-dev-llm-configs',
    },
    {
        'code': 'menu:ai-generation:ai-dev-repository-configs',
        'name': 'Git',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 90,
        'route_path': '/ai-generation/list?tab=ai-dev-repository-configs',
    },
    {
        'code': 'menu:ai-generation:ci-cd',
        'name': 'CI/CD',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:tools',
        'sort_order': 100,
        'route_path': '/ai-generation/list?tab=ci-cd',
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
        'code': 'menu:ai-generation:ai-dev-configs',
        'name': 'AI开发项目配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 30,
        'route_path': '/ai-generation/list?tab=ai-dev-configs',
    },
    {
        'code': 'menu:ai-generation:ai-dev-runtime-configs',
        'name': 'AI开发环境配置',
        'item_type': 'menu',
        'parent_code': 'menu:ai-generation:foundation',
        'sort_order': 40,
        'route_path': '/ai-generation/list?tab=ai-dev-runtime-configs',
    },
]


def sync_ai_generation_primary_tab_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')
    item_mapping = {}

    for item in AI_GENERATION_PRIMARY_TAB_PERMISSION_ITEMS:
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

    for item in AI_GENERATION_PRIMARY_TAB_PERMISSION_ITEMS:
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

    legacy_workspace_item = item_mapping['menu:ai-generation:list']
    primary_tab_items = [
        item_mapping[item['code']]
        for item in AI_GENERATION_PRIMARY_TAB_PERMISSION_ITEMS
        if item.get('parent_code') == 'module:ai-generation' and item['code'] != 'menu:ai-generation:list'
    ]
    legacy_role_ids = (
        RolePermission.objects
        .filter(permission_item=legacy_workspace_item)
        .values_list('role_id', flat=True)
        .distinct()
    )

    for role_id in legacy_role_ids:
        for permission_item in primary_tab_items:
            RolePermission.objects.get_or_create(
                role_id=role_id,
                permission_item_id=permission_item.id,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_add_manual_testcase_auxiliary_menu_permissions'),
    ]

    operations = [
        migrations.RunPython(sync_ai_generation_primary_tab_permission_items, migrations.RunPython.noop),
    ]
