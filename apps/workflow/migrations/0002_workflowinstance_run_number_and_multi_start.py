from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workflowinstance",
            name="run_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="workflowinstance",
            name="business_key",
            field=models.CharField(max_length=150),
        ),
        migrations.AddIndex(
            model_name="workflowinstance",
            index=models.Index(fields=["biz_type", "biz_id", "run_number"], name="workflow_in_biz_run_5df38f_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowinstance",
            index=models.Index(fields=["business_key"], name="workflow_in_busines_bdb688_idx"),
        ),
        migrations.AddConstraint(
            model_name="workflowinstance",
            constraint=models.UniqueConstraint(fields=("biz_type", "biz_id", "run_number"), name="workflow_instance_run_unique"),
        ),
    ]
