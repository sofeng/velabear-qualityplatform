from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0002_project_knowledge_build_and_database_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='knowledgeobject',
            name='object_type',
            field=models.CharField(
                choices=[
                    ('platform', 'Platform'),
                    ('module', 'Module'),
                    ('menu', 'Menu'),
                    ('page', 'Page'),
                    ('tab', 'Tab'),
                    ('function', 'Function'),
                    ('operation', 'Operation'),
                    ('field', 'Field'),
                    ('api', 'API'),
                    ('database', 'Database'),
                    ('table', 'Table'),
                    ('file', 'File'),
                    ('class', 'Class'),
                    ('method', 'Method'),
                    ('component', 'Component'),
                    ('route', 'Route'),
                    ('repository', 'Repository'),
                    ('document', 'Document'),
                    ('business_data', 'Business Data'),
                ],
                max_length=32,
                verbose_name='Object Type',
            ),
        ),
    ]
