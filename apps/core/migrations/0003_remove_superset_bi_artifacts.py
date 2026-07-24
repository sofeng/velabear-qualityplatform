from django.db import DatabaseError, migrations


BI_VIEWS = (
    "bi_manual_node_tag_fact",
    "bi_manual_node_fact",
    "bi_dev_self_test_fact",
)

BI_TABLES = (
    "bi_manual_node_snapshot_daily",
)

BI_EVENTS = (
    "ev_bi_manual_node_snapshot_daily",
)


def remove_superset_bi_artifacts(apps, schema_editor):
    if schema_editor.connection.vendor not in {"mysql", "mariadb"}:
        return

    with schema_editor.connection.cursor() as cursor:
        for event_name in BI_EVENTS:
            try:
                cursor.execute(f"DROP EVENT IF EXISTS `{event_name}`")
            except DatabaseError:
                pass

        for view_name in BI_VIEWS:
            cursor.execute(f"DROP VIEW IF EXISTS `{view_name}`")

        for table_name in BI_TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(remove_superset_bi_artifacts, migrations.RunPython.noop),
    ]
