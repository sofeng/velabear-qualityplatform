from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0009_alter_prompt_config_prompt_type_length'),
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
                ],
                max_length=10,
                verbose_name='文档类型',
            ),
        ),
    ]
