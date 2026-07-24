from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defects', '0006_defect_priority_defect_defects_priorit_04277e_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='defect',
            name='backend_developer',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='后端开发'),
        ),
        migrations.AddField(
            model_name='defect',
            name='frontend_developer',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='前端开发'),
        ),
    ]
