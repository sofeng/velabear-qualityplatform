from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0006_alter_businessrequirement_analysis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='promptconfig',
            name='prompt_type',
            field=models.CharField(
                choices=[
                    ('writer', '用例编写提示词'),
                    ('reviewer', '用例评审提示词'),
                    ('requirement_writer', '需求分析与编写提示词'),
                    ('requirement_reviewer', '需求评审提示词'),
                ],
                max_length=20,
                verbose_name='提示词类型',
            ),
        ),
    ]
