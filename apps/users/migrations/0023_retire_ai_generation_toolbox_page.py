from django.db import migrations


RETIRED_TOOLBOX_CODES = [
    'menu:ai-generation:tools',
    'menu:ai-generation:ai-dev-test-tool-configs',
    'menu:ai-generation:prompt-config',
    'menu:ai-generation:skill',
    'menu:ai-generation:agent',
    'menu:ai-generation:flow',
    'menu:ai-generation:mcp',
    'menu:ai-generation:marketplace',
    'menu:ai-generation:ai-dev-llm-configs',
    'menu:ai-generation:ai-dev-repository-configs',
    'menu:ai-generation:ci-cd',
]


def get_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def retire_ai_generation_toolbox_page(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    module_permission = PermissionItem.objects.filter(code='module:ai-generation').first()
    workshop_permission, _ = PermissionItem.objects.update_or_create(
        code='menu:ai-generation:workshop',
        defaults={
            'name': 'AI工坊',
            'item_type': 'menu',
            'parent': module_permission,
            'route_path': '/ai-generation/workshop',
            'sort_order': 80,
            'is_active': True,
            'description': 'AI研发平台能力主数据入口，承接原工具箱 Prompt、Skill、MCP、Agent、Flow、Model、TestTools、Git 等能力。',
        },
    )
    workshop_view_permission, _ = PermissionItem.objects.update_or_create(
        code='button:ai-generation:workshop:view',
        defaults={
            'name': '查看',
            'item_type': 'button',
            'parent': workshop_permission,
            'route_path': '',
            'sort_order': 5,
            'is_active': True,
            'description': '具备查看 AI工坊能力主数据的权限。',
        },
    )

    def copy_role_permissions(source_code, target_permission):
        source_permission = PermissionItem.objects.filter(code=source_code).first()
        if not source_permission:
            return

        source_role_ids = list(
            RolePermission.objects
            .filter(permission_item=source_permission)
            .values_list('role_id', flat=True)
            .distinct()
        )
        if not source_role_ids:
            return

        existing_role_ids = set(
            RolePermission.objects
            .filter(permission_item=target_permission, role_id__in=source_role_ids)
            .values_list('role_id', flat=True)
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role_id=role_id, permission_item=target_permission)
                for role_id in source_role_ids
                if role_id not in existing_role_ids
            ],
            ignore_conflicts=True,
        )

    for code in RETIRED_TOOLBOX_CODES:
        copy_role_permissions(code, workshop_permission)
        view_code = get_view_permission_code(code)
        if view_code:
            copy_role_permissions(view_code, workshop_view_permission)

    retired_descriptions = {
        'menu:ai-generation:tools': 'AI工具箱页面已退役，能力已迁移到 AI工坊；旧入口重定向到 AI工坊。',
        'menu:ai-generation:ai-dev-test-tool-configs': '原工具箱 TestTools 已迁移到 AI工坊-测试工具；旧入口重定向到 AI工坊。',
        'menu:ai-generation:prompt-config': '原工具箱 Prompt 已迁移到 AI工坊-提示词；旧入口重定向到 AI工坊。',
        'menu:ai-generation:skill': '原工具箱 Skill 已迁移到 AI工坊-技能；旧入口重定向到 AI工坊。',
        'menu:ai-generation:agent': '原工具箱 Agent 已迁移到 AI工坊-智能体；旧入口重定向到 AI工坊。',
        'menu:ai-generation:flow': '原工具箱 Flow 已迁移到 AI工坊-工作流；旧入口重定向到 AI工坊。',
        'menu:ai-generation:mcp': '原工具箱 MCP 已迁移到 AI工坊-插件；旧入口重定向到 AI工坊。',
        'menu:ai-generation:marketplace': '原工具箱能力市场已迁移到 AI工坊-技能商城；旧入口重定向到 AI工坊。',
        'menu:ai-generation:ai-dev-llm-configs': '原工具箱 Model 已迁移到 AI工坊-大模型；旧入口重定向到 AI工坊。',
        'menu:ai-generation:ai-dev-repository-configs': '原工具箱 Git 已迁移到 AI工坊-集成；旧入口重定向到 AI工坊。',
        'menu:ai-generation:ci-cd': '原工具箱 CI/CD 入口已退役；旧入口重定向到 AI工坊-集成。',
    }

    for code in RETIRED_TOOLBOX_CODES:
        PermissionItem.objects.filter(code=code).update(
            route_path='/ai-generation/workshop',
            is_active=False,
            description=retired_descriptions.get(code, 'AI工具箱页面已退役，旧入口重定向到 AI工坊。'),
        )
        view_code = get_view_permission_code(code)
        if view_code:
            PermissionItem.objects.filter(code=view_code).update(
                is_active=False,
                description='AI工具箱页面已退役；查看权限已迁移到 AI工坊查看权限。',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_retire_ai_generation_workflow_workbench_page'),
    ]

    operations = [
        migrations.RunPython(retire_ai_generation_toolbox_page, migrations.RunPython.noop),
    ]
