from django.db import migrations


RETIRED_AI_LIFECYCLE_MENU_CODES = [
    'menu:ai-generation:files',
    'menu:ai-generation:new-project-blueprints',
    'menu:ai-generation:requirement',
    'menu:ai-generation:requirement-analysis',
    'menu:ai-generation:ai-requirements',
    'menu:ai-generation:generated-testcases',
    'menu:ai-generation:development',
    'menu:ai-generation:ai-dev-tasks',
    'menu:ai-generation:workflow-workbench',
    'menu:ai-generation:defect',
    'menu:ai-generation:operations',
    'menu:ai-generation:ai-dev-build-configs',
    'menu:ai-generation:deployment-targets',
    'menu:ai-generation:deployment-templates',
    'menu:ai-generation:build-artifacts',
    'menu:ai-generation:deployment-executions',
    'menu:ai-generation:rollback-records',
]


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def copy_role_permissions(source_code, target_permission, RolePermission, PermissionItem):
    source_permission = PermissionItem.objects.filter(code=source_code).first()
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


def retire_ai_generation_legacy_lifecycle_modules(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    RolePermission = apps.get_model('users', 'RolePermission')

    conversation_permission = PermissionItem.objects.filter(code='menu:ai-generation:conversation').first()
    if conversation_permission:
        for source_code in RETIRED_AI_LIFECYCLE_MENU_CODES:
            copy_role_permissions(source_code, conversation_permission, RolePermission, PermissionItem)
            view_permission_code = build_view_permission_code(source_code)
            if view_permission_code:
                copy_role_permissions(view_permission_code, conversation_permission, RolePermission, PermissionItem)

    PermissionItem.objects.filter(code__in=RETIRED_AI_LIFECYCLE_MENU_CODES).update(
        route_path='/ai-generation/codex-chat',
        is_active=False,
        description=(
            'Retired legacy AI lifecycle menu/page shape. The capability is kept in backend services '
            'and will be rebuilt inside the AI conversation detail workspace.'
        ),
    )

    view_permission_codes = [
        code
        for code in (build_view_permission_code(item) for item in RETIRED_AI_LIFECYCLE_MENU_CODES)
        if code
    ]
    PermissionItem.objects.filter(code__in=view_permission_codes).update(
        route_path='/ai-generation/codex-chat',
        is_active=False,
        description=(
            'Retired legacy AI lifecycle page view permission. Access is migrated to AI conversation.'
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_retire_ai_generation_testing_menu'),
    ]

    operations = [
        migrations.RunPython(retire_ai_generation_legacy_lifecycle_modules, migrations.RunPython.noop),
    ]
