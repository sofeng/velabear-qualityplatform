from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='是否默认项目'),
        ),
    ]
