from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('testcases', '0016_manualtestcasemindmap_mindmap_scope'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devselftestrecord',
            name='status',
            field=models.CharField(
                choices=[
                    ('not_run', '未执行'),
                    ('pass', '通过'),
                    ('fail', '失败'),
                    ('block', '阻塞'),
                    ('not_test', '本版本不测'),
                ],
                default='not_run',
                max_length=20,
                verbose_name='状态',
            ),
        ),
    ]
