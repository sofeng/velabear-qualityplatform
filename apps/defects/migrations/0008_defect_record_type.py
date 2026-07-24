from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defects', '0007_defect_frontend_developer_defect_backend_developer'),
    ]

    operations = [
        migrations.AddField(
            model_name='defect',
            name='record_type',
            field=models.CharField(
                choices=[
                    ('defect', '缺陷'),
                    ('technical_solution_design', '技术方案设计'),
                ],
                default='defect',
                max_length=40,
                verbose_name='记录类型',
            ),
        ),
        migrations.AddIndex(
            model_name='defect',
            index=models.Index(fields=['record_type'], name='defects_record_type_idx'),
        ),
    ]
