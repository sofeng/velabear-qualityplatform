from django.db import migrations


BUG_ASSOCIATION_FIELD_NAMES = (
    'related_requirements',
    'related_testcases',
    'related_testpoints',
)


def _get_column_names(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return {getattr(column, 'name', column[0]) for column in description}


def reconcile_bug_association_columns(apps, schema_editor):
    JiraBugRecord = apps.get_model('quality_analysis', 'JiraBugRecord')
    bug_table = JiraBugRecord._meta.db_table
    bug_columns = _get_column_names(schema_editor, bug_table)

    for field_name in BUG_ASSOCIATION_FIELD_NAMES:
        if field_name in bug_columns:
            continue
        schema_editor.add_field(JiraBugRecord, JiraBugRecord._meta.get_field(field_name))

    requirement_table = 'quality_analysis_jira_requirement_records'
    requirement_columns = _get_column_names(schema_editor, requirement_table)
    quoted_requirement_table = schema_editor.quote_name(requirement_table)

    with schema_editor.connection.cursor() as cursor:
        for field_name in BUG_ASSOCIATION_FIELD_NAMES:
            if field_name not in requirement_columns:
                continue
            cursor.execute(
                f'ALTER TABLE {quoted_requirement_table} DROP COLUMN {schema_editor.quote_name(field_name)}'
            )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('quality_analysis', '0010_remove_jirabugrecord_related_requirements_and_more'),
    ]

    operations = [
        migrations.RunPython(reconcile_bug_association_columns, migrations.RunPython.noop),
    ]
