from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0011_expand_requirement_document_file_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessrequirement',
            name='accepted_context',
            field=models.JSONField(blank=True, default=dict, verbose_name='已接受需求上下文'),
        ),
    ]
