from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('requirement_analysis', '0012_businessrequirement_accepted_context'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessrequirement',
            name='audit_status',
            field=models.CharField(
                choices=[
                    ('pending', '待审核'),
                    ('approved', '已审核'),
                    ('rejected', '已驳回'),
                ],
                default='pending',
                max_length=20,
                verbose_name='审核状态',
            ),
        ),
        migrations.AddField(
            model_name='businessrequirement',
            name='audited_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='审核时间'),
        ),
        migrations.AddField(
            model_name='businessrequirement',
            name='audited_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='audited_requirements',
                to=settings.AUTH_USER_MODEL,
                verbose_name='审核人',
            ),
        ),
    ]
