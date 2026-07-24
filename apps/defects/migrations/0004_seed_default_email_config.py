from django.db import migrations


DEFAULT_EMAIL_CONFIG = {
    'host': '',
    'port': 465,
    'username': '',
    'password': '',
    'from_name': '缺陷管理平台',
    'from_email': '',
    'new_bug_template': '您好，您有一个新的缺陷待处理。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'resolved_bug_template': '您好，缺陷已解决。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'rejected_bug_template': '您好，缺陷已拒绝。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'reopened_bug_template': '您好，缺陷已重新打开。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'is_active': True,
}

TEMPLATE_FIELDS = [
    'new_bug_template',
    'resolved_bug_template',
    'rejected_bug_template',
    'reopened_bug_template',
]


def seed_default_email_config(apps, schema_editor):
    DefectEmailConfig = apps.get_model('defects', 'DefectEmailConfig')

    if not DefectEmailConfig.objects.exists():
        DefectEmailConfig.objects.create(**DEFAULT_EMAIL_CONFIG)
        return

    for config in DefectEmailConfig.objects.all():
        changed_fields = []
        for field_name in TEMPLATE_FIELDS:
            if getattr(config, field_name, ''):
                continue
            setattr(config, field_name, DEFAULT_EMAIL_CONFIG[field_name])
            changed_fields.append(field_name)

        if changed_fields:
            config.save(update_fields=changed_fields + ['updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('defects', '0003_defectemailconfig'),
    ]

    operations = [
        migrations.RunPython(seed_default_email_config, migrations.RunPython.noop),
    ]
