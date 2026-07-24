from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgespace',
            name='build_status',
            field=models.CharField(
                choices=[
                    ('pending_config', 'Pending Config'),
                    ('ready', 'Ready'),
                    ('queued', 'Queued'),
                    ('indexing', 'Indexing'),
                    ('indexed', 'Indexed'),
                    ('stale', 'Stale'),
                    ('failed', 'Failed'),
                ],
                default='pending_config',
                max_length=32,
                verbose_name='Build Status',
            ),
        ),
        migrations.AddField(
            model_name='knowledgespace',
            name='build_status_message',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='Build Status Message'),
        ),
        migrations.AddField(
            model_name='knowledgespace',
            name='last_indexed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Last Indexed At'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_engine',
            field=models.CharField(
                choices=[
                    ('none', 'None'),
                    ('current', 'Current Platform Database'),
                    ('mysql', 'MySQL'),
                ],
                default='none',
                max_length=32,
                verbose_name='Database Engine',
            ),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_host',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Database Host'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_port',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Database Port'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_name',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Database Name'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_schema',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Database Schema'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_username',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='Database Username'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_password_encrypted',
            field=models.CharField(blank=True, default='', max_length=1000, verbose_name='Encrypted Database Password'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_include_patterns',
            field=models.JSONField(blank=True, default=list, verbose_name='Database Include Patterns'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='database_exclude_patterns',
            field=models.JSONField(blank=True, default=list, verbose_name='Database Exclude Patterns'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='allow_sample_data',
            field=models.BooleanField(default=False, verbose_name='Allow Sample Data'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='auto_index_on_ready',
            field=models.BooleanField(default=True, verbose_name='Auto Index On Ready'),
        ),
        migrations.AddField(
            model_name='knowledgerepositoryconfig',
            name='last_schema_test_result',
            field=models.JSONField(blank=True, default=dict, verbose_name='Last Schema Test Result'),
        ),
    ]
