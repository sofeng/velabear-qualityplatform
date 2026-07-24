from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0003_asset_insight_object_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='knowledgerelation',
            name='relation_type',
            field=models.CharField(
                choices=[
                    ('contains', 'Contains'),
                    ('belongs_to', 'Belongs To'),
                    ('opens', 'Opens'),
                    ('implements', 'Implements'),
                    ('calls', 'Calls'),
                    ('reads', 'Reads'),
                    ('writes', 'Writes'),
                    ('references', 'References'),
                    ('depends_on', 'Depends On'),
                    ('uses', 'Uses'),
                    ('same_as', 'Same As'),
                    ('related_to', 'Related To'),
                ],
                max_length=32,
                verbose_name='Relation Type',
            ),
        ),
    ]
