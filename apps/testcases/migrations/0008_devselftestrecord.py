from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('testcases', '0007_manualtestcasemindmap_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='DevSelfTestRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_id', models.CharField(max_length=255, verbose_name='脑图节点ID')),
                ('module', models.CharField(blank=True, max_length=255, verbose_name='模块')),
                ('module_path', models.TextField(blank=True, verbose_name='模块路径')),
                ('testpoint', models.TextField(blank=True, verbose_name='测试点')),
                ('priority', models.PositiveIntegerField(blank=True, null=True, verbose_name='优先级')),
                ('preconditions', models.TextField(blank=True, verbose_name='前置条件')),
                ('expected_result', models.TextField(blank=True, verbose_name='期望结果')),
                ('steps', models.TextField(blank=True, verbose_name='测试步骤')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('status', models.CharField(choices=[('not_run', '未执行'), ('pass', '通过'), ('fail', '失败'), ('block', '阻塞')], default='not_run', max_length=20, verbose_name='状态')),
                ('audit_status', models.CharField(choices=[('pending', '待审核'), ('approved', '审核通过'), ('rejected', '审核驳回')], default='pending', max_length=20, verbose_name='审核状态')),
                ('audited_at', models.DateTimeField(blank=True, null=True, verbose_name='审核时间')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('audited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audited_dev_self_test_records', to=settings.AUTH_USER_MODEL, verbose_name='审核人')),
                ('mindmap', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dev_self_test_records', to='testcases.manualtestcasemindmap', verbose_name='关联脑图')),
            ],
            options={
                'verbose_name': '开发自测记录',
                'verbose_name_plural': '开发自测记录',
                'db_table': 'dev_self_test_records',
                'ordering': ['-updated_at', '-id'],
                'unique_together': {('mindmap', 'node_id')},
            },
        ),
    ]
