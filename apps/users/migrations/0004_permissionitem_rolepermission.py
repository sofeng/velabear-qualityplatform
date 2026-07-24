from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


SEEDED_PERMISSION_ITEMS = [
    {'code': 'module:home', 'name': '首页', 'item_type': 'module', 'sort_order': 10, 'route_path': '/home'},
    {'code': 'menu:home', 'name': '首页', 'item_type': 'menu', 'parent_code': 'module:home', 'sort_order': 10, 'route_path': '/home'},

    {'code': 'module:ai-generation', 'name': 'AI生成', 'item_type': 'module', 'sort_order': 20},
    {'code': 'menu:ai-generation:projects', 'name': '项目管理', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 10, 'route_path': '/ai-generation/projects'},
    {'code': 'menu:ai-generation:requirement-analysis', 'name': '需求分析', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 20, 'route_path': '/ai-generation/requirement-analysis'},
    {'code': 'menu:ai-generation:ai-requirements', 'name': '需求管理', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 30, 'route_path': '/ai-generation/ai-requirements'},
    {'code': 'menu:ai-generation:generated-testcases', 'name': '生成记录', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 40, 'route_path': '/ai-generation/generated-testcases'},
    {'code': 'menu:ai-generation:ui-automation-cases', 'name': 'UI自动化用例', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 50, 'route_path': '/ai-generation/ui-automation-cases'},
    {'code': 'menu:ai-generation:ai-dev-tasks', 'name': 'AI开发任务', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 60, 'route_path': '/ai-generation/ai-dev-tasks'},
    {'code': 'menu:ai-generation:workflow-workbench', 'name': '流程工作台', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 70, 'route_path': '/ai-generation/workflow-workbench'},
    {'code': 'menu:ai-generation:prompt-config', 'name': '提示词配置', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 80, 'route_path': '/ai-generation/prompt-config'},
    {'code': 'menu:ai-generation:testcases', 'name': '测试用例', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 90, 'route_path': '/ai-generation/testcases'},
    {'code': 'menu:ai-generation:versions', 'name': '版本管理', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 100, 'route_path': '/ai-generation/versions'},
    {'code': 'menu:ai-generation:reviews', 'name': '评审列表', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 110, 'route_path': '/ai-generation/reviews'},
    {'code': 'menu:ai-generation:review-templates', 'name': '评审模板', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 120, 'route_path': '/ai-generation/review-templates'},
    {'code': 'menu:ai-generation:executions', 'name': '测试计划', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 130, 'route_path': '/ai-generation/executions'},
    {'code': 'menu:ai-generation:reports', 'name': '测试报告', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 140, 'route_path': '/ai-generation/reports'},
    {'code': 'menu:ai-generation:ai-dev-configs', 'name': 'AI开发配置', 'item_type': 'menu', 'parent_code': 'module:ai-generation', 'sort_order': 150, 'route_path': '/ai-generation/ai-dev-configs'},

    {'code': 'module:api-testing', 'name': '接口测试', 'item_type': 'module', 'sort_order': 30},
    {'code': 'menu:api-testing:dashboard', 'name': '数据看板', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 10, 'route_path': '/api-testing/dashboard'},
    {'code': 'menu:api-testing:projects', 'name': '项目管理', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 20, 'route_path': '/api-testing/projects'},
    {'code': 'menu:api-testing:interfaces', 'name': '接口管理', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 30, 'route_path': '/api-testing/interfaces'},
    {'code': 'menu:api-testing:automation', 'name': '自动化测试', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 40, 'route_path': '/api-testing/automation'},
    {'code': 'menu:api-testing:history', 'name': '请求历史', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 50, 'route_path': '/api-testing/history'},
    {'code': 'menu:api-testing:environments', 'name': '环境管理', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 60, 'route_path': '/api-testing/environments'},
    {'code': 'menu:api-testing:reports', 'name': '测试报告', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 70, 'route_path': '/api-testing/reports'},
    {'code': 'menu:api-testing:scheduled-tasks', 'name': '定时任务', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 80, 'route_path': '/api-testing/scheduled-tasks'},
    {'code': 'menu:api-testing:notification-logs', 'name': '通知列表', 'item_type': 'menu', 'parent_code': 'module:api-testing', 'sort_order': 90, 'route_path': '/api-testing/notification-logs'},

    {'code': 'module:ui-automation', 'name': 'UI自动化', 'item_type': 'module', 'sort_order': 40},
    {'code': 'menu:ui-automation:dashboard', 'name': '数据看板', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 10, 'route_path': '/ui-automation/dashboard'},
    {'code': 'menu:ui-automation:projects', 'name': '项目管理', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 20, 'route_path': '/ui-automation/projects'},
    {'code': 'menu:ui-automation:elements-enhanced', 'name': '元素管理', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 30, 'route_path': '/ui-automation/elements-enhanced'},
    {'code': 'menu:ui-automation:test-cases', 'name': '用例管理', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 40, 'route_path': '/ui-automation/test-cases'},
    {'code': 'menu:ui-automation:scripts-enhanced', 'name': '脚本生成', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 50, 'route_path': '/ui-automation/scripts-enhanced'},
    {'code': 'menu:ui-automation:scripts', 'name': '脚本列表', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 60, 'route_path': '/ui-automation/scripts'},
    {'code': 'menu:ui-automation:suites', 'name': '套件管理', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 70, 'route_path': '/ui-automation/suites'},
    {'code': 'menu:ui-automation:executions', 'name': '执行记录', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 80, 'route_path': '/ui-automation/executions'},
    {'code': 'menu:ui-automation:reports', 'name': '测试报告', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 90, 'route_path': '/ui-automation/reports'},
    {'code': 'menu:ui-automation:scheduled-tasks', 'name': '定时任务', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 100, 'route_path': '/ui-automation/scheduled-tasks'},
    {'code': 'menu:ui-automation:notification-logs', 'name': '通知列表', 'item_type': 'menu', 'parent_code': 'module:ui-automation', 'sort_order': 110, 'route_path': '/ui-automation/notification-logs'},

    {'code': 'module:ai-intelligent-mode', 'name': 'AI智能模式', 'item_type': 'module', 'sort_order': 50},
    {'code': 'menu:ai-intelligent-mode:testing', 'name': 'AI智能测试', 'item_type': 'menu', 'parent_code': 'module:ai-intelligent-mode', 'sort_order': 10, 'route_path': '/ai-intelligent-mode/testing'},
    {'code': 'menu:ai-intelligent-mode:cases', 'name': 'AI用例管理', 'item_type': 'menu', 'parent_code': 'module:ai-intelligent-mode', 'sort_order': 20, 'route_path': '/ai-intelligent-mode/cases'},
    {'code': 'menu:ai-intelligent-mode:execution-records', 'name': 'AI测试报告', 'item_type': 'menu', 'parent_code': 'module:ai-intelligent-mode', 'sort_order': 30, 'route_path': '/ai-intelligent-mode/execution-records'},

    {'code': 'module:configuration', 'name': '配置中心', 'item_type': 'module', 'sort_order': 60},
    {'code': 'menu:configuration:ai-model', 'name': 'AI模型配置', 'item_type': 'menu', 'parent_code': 'module:configuration', 'sort_order': 10, 'route_path': '/configuration/ai-model'},
    {'code': 'menu:configuration:ui-env', 'name': 'UI环境配置', 'item_type': 'menu', 'parent_code': 'module:configuration', 'sort_order': 20, 'route_path': '/configuration/ui-env'},
    {'code': 'menu:configuration:ai-mode', 'name': 'AI模式配置', 'item_type': 'menu', 'parent_code': 'module:configuration', 'sort_order': 30, 'route_path': '/configuration/ai-mode'},
    {'code': 'menu:configuration:scheduled-task', 'name': '定时任务配置', 'item_type': 'menu', 'parent_code': 'module:configuration', 'sort_order': 40, 'route_path': '/configuration/scheduled-task'},
    {'code': 'menu:configuration:dify', 'name': 'Dify配置', 'item_type': 'menu', 'parent_code': 'module:configuration', 'sort_order': 50, 'route_path': '/configuration/dify'},

    {'code': 'module:manual-testcases', 'name': '手工用例', 'item_type': 'module', 'sort_order': 70},
    {'code': 'menu:manual-testcases:list', 'name': '手工用例工作台', 'item_type': 'menu', 'parent_code': 'module:manual-testcases', 'sort_order': 10, 'route_path': '/manual-testcases/list'},
    {'code': 'menu:manual-testcases:reports', 'name': '质量报告', 'item_type': 'menu', 'parent_code': 'module:manual-testcases', 'sort_order': 20, 'route_path': '/manual-testcases/reports'},
    {'code': 'menu:manual-testcases:snapshots', 'name': '快照文件管理', 'item_type': 'menu', 'parent_code': 'module:manual-testcases', 'sort_order': 30, 'route_path': '/manual-testcases/snapshots'},
    {'code': 'menu:manual-testcases:visual-flow', 'name': '可视化流程', 'item_type': 'menu', 'parent_code': 'module:manual-testcases', 'sort_order': 40, 'route_path': '/manual-testcases/visual-flow'},
    {'code': 'menu:manual-testcases:workflow-workbench', 'name': '流程工作台', 'item_type': 'menu', 'parent_code': 'module:manual-testcases', 'sort_order': 50, 'route_path': '/manual-testcases/workflow-workbench'},
    {'code': 'menu:manual-testcases:members', 'name': '成员', 'item_type': 'menu', 'parent_code': 'menu:manual-testcases:list', 'sort_order': 60, 'route_path': '/manual-testcases/list?tab=members'},
    {'code': 'menu:manual-testcases:groups', 'name': '组别', 'item_type': 'menu', 'parent_code': 'menu:manual-testcases:list', 'sort_order': 70, 'route_path': '/manual-testcases/list?tab=groups'},
    {'code': 'menu:manual-testcases:roles', 'name': '角色', 'item_type': 'menu', 'parent_code': 'menu:manual-testcases:list', 'sort_order': 80, 'route_path': '/manual-testcases/list?tab=roles'},
    {'code': 'menu:manual-testcases:permissions', 'name': '权限', 'item_type': 'menu', 'parent_code': 'menu:manual-testcases:list', 'sort_order': 90, 'route_path': '/manual-testcases/list?tab=permissions'},

    {'code': 'button:manual-testcases:members:create', 'name': '新增成员', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:members', 'sort_order': 10},
    {'code': 'button:manual-testcases:members:edit', 'name': '编辑成员', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:members', 'sort_order': 20},
    {'code': 'button:manual-testcases:members:delete', 'name': '删除成员', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:members', 'sort_order': 30},
    {'code': 'button:manual-testcases:groups:create', 'name': '新增组别', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:groups', 'sort_order': 10},
    {'code': 'button:manual-testcases:groups:edit', 'name': '编辑组别', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:groups', 'sort_order': 20},
    {'code': 'button:manual-testcases:groups:delete', 'name': '删除组别', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:groups', 'sort_order': 30},
    {'code': 'button:manual-testcases:roles:create', 'name': '新增角色', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:roles', 'sort_order': 10},
    {'code': 'button:manual-testcases:roles:edit', 'name': '编辑角色', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:roles', 'sort_order': 20},
    {'code': 'button:manual-testcases:roles:delete', 'name': '删除角色', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:roles', 'sort_order': 30},
    {'code': 'button:manual-testcases:permissions:create', 'name': '新增权限项', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:permissions', 'sort_order': 10},
    {'code': 'button:manual-testcases:permissions:edit', 'name': '编辑权限项', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:permissions', 'sort_order': 20},
    {'code': 'button:manual-testcases:permissions:delete', 'name': '删除权限项', 'item_type': 'button', 'parent_code': 'menu:manual-testcases:permissions', 'sort_order': 30},
    {'code': 'action:manual-testcases:permissions:assign', 'name': '分配角色权限', 'item_type': 'action', 'parent_code': 'menu:manual-testcases:permissions', 'sort_order': 40},
    {'code': 'action:manual-testcases:permissions:view', 'name': '查看权限树', 'item_type': 'action', 'parent_code': 'menu:manual-testcases:permissions', 'sort_order': 50},
]


def seed_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    item_mapping = {}

    for item in SEEDED_PERMISSION_ITEMS:
        defaults = {
            'name': item['name'],
            'item_type': item['item_type'],
            'route_path': item.get('route_path', ''),
            'sort_order': item.get('sort_order', 0),
            'is_active': True,
            'description': item.get('description', ''),
        }
        permission_item, _ = PermissionItem.objects.update_or_create(
            code=item['code'],
            defaults=defaults,
        )
        item_mapping[item['code']] = permission_item

    for item in SEEDED_PERMISSION_ITEMS:
        permission_item = item_mapping[item['code']]
        parent_code = item.get('parent_code')
        parent_item = item_mapping.get(parent_code) if parent_code else None
        parent_id = parent_item.id if parent_item else None
        if permission_item.parent_id != parent_id:
            permission_item.parent_id = parent_id
            permission_item.save(update_fields=['parent'])


def rollback_seed_permission_items(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    PermissionItem.objects.filter(code__in=[item['code'] for item in SEEDED_PERMISSION_ITEMS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_rolemembership'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermissionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='权限名称')),
                ('code', models.CharField(max_length=150, unique=True, verbose_name='权限编码')),
                ('item_type', models.CharField(choices=[('module', '模块'), ('menu', '菜单'), ('button', '按钮'), ('action', '操作项')], max_length=20, verbose_name='权限类型')),
                ('route_path', models.CharField(blank=True, max_length=255, verbose_name='路由路径')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='排序值')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='描述')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='users.permissionitem', verbose_name='父级权限')),
            ],
            options={
                'verbose_name': '权限项',
                'verbose_name_plural': '权限项',
                'db_table': 'users_permission_item',
                'ordering': ['sort_order', 'name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('permission_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='users.permissionitem', verbose_name='权限项')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='users.role', verbose_name='角色')),
            ],
            options={
                'verbose_name': '角色权限',
                'verbose_name_plural': '角色权限',
                'db_table': 'users_role_permission',
                'ordering': ['role_id', 'permission_item_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='rolepermission',
            constraint=models.UniqueConstraint(fields=('role', 'permission_item'), name='users_role_permission_unique'),
        ),
        migrations.RunPython(seed_permission_items, rollback_seed_permission_items),
    ]
