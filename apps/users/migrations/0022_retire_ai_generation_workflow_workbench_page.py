from django.db import migrations


def retire_ai_generation_workflow_workbench_page(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    def copy_role_permissions(source_code, target_code):
        source_permission = PermissionItem.objects.filter(code=source_code).first()
        target_permission = PermissionItem.objects.filter(code=target_code).first()
        if not source_permission or not target_permission:
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

    copy_role_permissions(
        'menu:ai-generation:workflow-workbench',
        'menu:ai-generation:ai-dev-tasks',
    )
    copy_role_permissions(
        'button:ai-generation:workflow-workbench:view',
        'button:ai-generation:ai-dev-tasks:view',
    )

    PermissionItem.objects.filter(code='menu:ai-generation:workflow-workbench').update(
        route_path='/ai-generation/list?tab=ai-dev-tasks',
        is_active=False,
        description='AI研发平台下的流程工作台页面已退役；历史角色已迁移到AI开发任务，旧链接重定向到AI开发任务。',
    )
    PermissionItem.objects.filter(code='button:ai-generation:workflow-workbench:view').update(
        is_active=False,
        description='AI研发平台下的流程工作台页面已退役；历史角色已迁移到AI开发任务查看权限。',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_retire_ai_generation_file_requirement_page'),
    ]

    operations = [
        migrations.RunPython(retire_ai_generation_workflow_workbench_page, migrations.RunPython.noop),
    ]
