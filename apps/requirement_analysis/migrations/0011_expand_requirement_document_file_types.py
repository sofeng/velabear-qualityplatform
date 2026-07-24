from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0010_support_xmind_requirement_document'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requirementdocument',
            name='document_type',
            field=models.CharField(
                choices=[
                    ('pdf', 'PDF文档'),
                    ('docx', 'Word文档'),
                    ('txt', '文本文档'),
                    ('xmind', 'XMind脑图'),
                    ('image', '图片文件'),
                    ('archive', '压缩包'),
                    ('excel', 'Excel表格'),
                    ('ppt', 'PPT演示文稿'),
                ],
                max_length=10,
                verbose_name='文档类型',
            ),
        ),
    ]
