from django.db import migrations


def add_missing_element_order_column(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "ui_elements"
    column_name = "order"
    index_name = "ui_elem_proj_group_order_idx"
    quoted_table = schema_editor.quote_name(table_name)
    quoted_column = schema_editor.quote_name(column_name)
    quoted_index = schema_editor.quote_name(index_name)

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            column_exists = any(row[1] == column_name for row in cursor.fetchall())
        else:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND COLUMN_NAME = %s
                """,
                [table_name, column_name],
            )
            column_exists = cursor.fetchone()[0] > 0

        if not column_exists:
            cursor.execute(
                f"ALTER TABLE {quoted_table} "
                f"ADD COLUMN {quoted_column} INTEGER NOT NULL DEFAULT 0"
            )

        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA index_list({quoted_table})")
            index_exists = any(row[1] == index_name for row in cursor.fetchall())
        else:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND INDEX_NAME = %s
                """,
                [table_name, index_name],
            )
            index_exists = cursor.fetchone()[0] > 0

        if not index_exists:
            cursor.execute(
                f"CREATE INDEX {quoted_index} "
                f"ON {quoted_table} ("
                f"{schema_editor.quote_name('project_id')}, "
                f"{schema_editor.quote_name('group_id')}, "
                f"{quoted_column})"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("ui_automation", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(add_missing_element_order_column, migrations.RunPython.noop),
    ]
