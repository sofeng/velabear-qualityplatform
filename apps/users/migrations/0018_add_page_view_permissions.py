from django.db import migrations


VIEW_PERMISSION_NAME = '\u67e5\u770b'
VIEW_PERMISSION_DESCRIPTION = '\u5177\u5907\u67e5\u770b\u6743\u9650\uff0c\u53ef\u67e5\u770b\u5217\u8868\u6570\u636e\u548c\u9875\u9762\u6570\u636e'
VIEW_PERMISSION_SORT_ORDER = 5
EXCLUDED_MENU_PREFIXES = (
    'menu:home',
)


def build_view_permission_code(menu_code):
    normalized_code = str(menu_code or '').strip()
    if not normalized_code.startswith('menu:'):
        return ''
    return f'button:{normalized_code[5:]}:view'


def should_create_view_permission(permission_item):
    code = str(permission_item.code or '').strip()
    if not code:
        return False
    if any(code.startswith(prefix) for prefix in EXCLUDED_MENU_PREFIXES):
        return False
    if not str(permission_item.route_path or '').strip():
        return False
    return True


def sync_page_view_permissions(apps, schema_editor):
    PermissionItem = apps.get_model('users', 'PermissionItem')
    page_permissions = PermissionItem.objects.filter(
        item_type='menu',
        is_active=True,
    ).order_by('code', 'id')

    for page_permission in page_permissions:
        if not should_create_view_permission(page_permission):
            continue

        view_permission_code = build_view_permission_code(page_permission.code)
        if not view_permission_code:
            continue

        PermissionItem.objects.update_or_create(
            code=view_permission_code,
            defaults={
                'name': VIEW_PERMISSION_NAME,
                'item_type': 'button',
                'parent': page_permission,
                'route_path': '',
                'sort_order': VIEW_PERMISSION_SORT_ORDER,
                'is_active': True,
                'description': VIEW_PERMISSION_DESCRIPTION,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_remove_manual_report_excel_permission'),
    ]

    operations = [
        migrations.RunPython(sync_page_view_permissions, migrations.RunPython.noop),
    ]
