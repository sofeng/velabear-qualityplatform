from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0008_jira_record_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='jirabugrecord',
            name='related_requirements',
            field=models.JSONField(blank=True, default=list, verbose_name='关联需求'),
        ),
        migrations.AddField(
            model_name='jirabugrecord',
            name='related_testcases',
            field=models.JSONField(blank=True, default=list, verbose_name='关联测试用例'),
        ),
        migrations.AddField(
            model_name='jirabugrecord',
            name='related_testpoints',
            field=models.JSONField(blank=True, default=list, verbose_name='关联测试点'),
        ),
    ]
