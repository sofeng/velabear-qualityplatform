from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defects', '0010_wiki_directory_and_record_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='defect',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', '待处理'),
                    ('in_progress', '处理中'),
                    ('resolved', '提测'),
                    ('returned_pending', '打回待处理'),
                    ('regression_verified', '回归验证完成'),
                    ('rejected', '已拒绝'),
                    ('deferred', '暂不处理'),
                    ('customer_validation', '待客户环境验证'),
                    ('pending_requirement', '待转新需求'),
                    ('requirement_created', '已转新需求'),
                    ('closed', '已关闭'),
                    ('reopened', '重新打开'),
                    ('invalid', '已作废'),
                ],
                default='new',
                max_length=20,
                verbose_name='状态',
            ),
        ),
    ]
