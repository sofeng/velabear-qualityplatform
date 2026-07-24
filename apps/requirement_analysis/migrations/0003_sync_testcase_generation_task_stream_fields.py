from django.db import migrations, models


def _has_column(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(column.name == column_name for column in columns)


def _add_field_if_missing(schema_editor, model, name, field):
    if _has_column(schema_editor, model._meta.db_table, name):
        return

    field.set_attributes_from_name(name)
    field.model = model
    schema_editor.add_field(model, field)


def sync_testcase_generation_task_stream_fields(apps, schema_editor):
    model = apps.get_model('requirement_analysis', 'TestCaseGenerationTask')

    _add_field_if_missing(
        schema_editor,
        model,
        'output_mode',
        models.CharField(
            max_length=10,
            choices=[('batch', '批量输出'), ('stream', '流式输出')],
            default='batch',
            verbose_name='输出模式',
        ),
    )
    _add_field_if_missing(
        schema_editor,
        model,
        'stream_buffer',
        models.TextField(blank=True, default='', verbose_name='流式输出缓存'),
    )
    _add_field_if_missing(
        schema_editor,
        model,
        'stream_position',
        models.IntegerField(default=0, verbose_name='流式输出位置'),
    )
    _add_field_if_missing(
        schema_editor,
        model,
        'last_stream_update',
        models.DateTimeField(null=True, blank=True, verbose_name='最近一次流式更新时间'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0002_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    sync_testcase_generation_task_stream_fields,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='testcasegenerationtask',
                    name='output_mode',
                    field=models.CharField(
                        choices=[('batch', '批量输出'), ('stream', '流式输出')],
                        default='batch',
                        max_length=10,
                        verbose_name='输出模式',
                    ),
                ),
                migrations.AddField(
                    model_name='testcasegenerationtask',
                    name='stream_buffer',
                    field=models.TextField(blank=True, default='', verbose_name='流式输出缓存'),
                ),
                migrations.AddField(
                    model_name='testcasegenerationtask',
                    name='stream_position',
                    field=models.IntegerField(default=0, verbose_name='流式输出位置'),
                ),
                migrations.AddField(
                    model_name='testcasegenerationtask',
                    name='last_stream_update',
                    field=models.DateTimeField(blank=True, null=True, verbose_name='最近一次流式更新时间'),
                ),
            ],
        ),
    ]
