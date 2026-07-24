from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0007_extend_prompt_config_requirement_types'),
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
                    ('document_requirement_writer', '需求文档创建需求提示词'),
                    ('document_testcase_writer', '需求文档生成测试用例提示词'),
                ],
                max_length=30,
                verbose_name='提示词类型',
            ),
        ),
    ]
