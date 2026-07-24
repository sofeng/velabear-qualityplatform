from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quality_analysis', '0015_remove_legacy_jira_cookie_headers'),
    ]

    operations = [
        migrations.AddField(
            model_name='jirainterfaceconfig',
            name='jira_login_enabled',
            field=models.BooleanField(default=False, verbose_name='启用JIRA登录'),
        ),
        migrations.AddField(
            model_name='jirainterfaceconfig',
            name='jira_login_url',
            field=models.CharField(
                blank=True,
                default='http://172.31.119.34:8080/login.jsp',
                max_length=500,
                verbose_name='JIRA登录URL',
            ),
        ),
        migrations.AddField(
            model_name='jirainterfaceconfig',
            name='jira_username',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='JIRA账号'),
        ),
        migrations.AddField(
            model_name='jirainterfaceconfig',
            name='jira_password_encrypted',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='JIRA密码(加密存储)'),
        ),
        migrations.AddField(
            model_name='jirarequirementinterfaceconfig',
            name='jira_login_enabled',
            field=models.BooleanField(default=False, verbose_name='启用JIRA登录'),
        ),
        migrations.AddField(
            model_name='jirarequirementinterfaceconfig',
            name='jira_login_url',
            field=models.CharField(
                blank=True,
                default='http://172.31.119.34:8080/login.jsp',
                max_length=500,
                verbose_name='JIRA登录URL',
            ),
        ),
        migrations.AddField(
            model_name='jirarequirementinterfaceconfig',
            name='jira_username',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='JIRA账号'),
        ),
        migrations.AddField(
            model_name='jirarequirementinterfaceconfig',
            name='jira_password_encrypted',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='JIRA密码(加密存储)'),
        ),
    ]
