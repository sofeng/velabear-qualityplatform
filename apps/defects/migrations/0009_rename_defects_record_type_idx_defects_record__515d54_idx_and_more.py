from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defects', '0008_defect_record_type'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='defect',
            new_name='defects_record__515d54_idx',
            old_name='defects_record_type_idx',
        ),
        migrations.AlterField(
            model_name='defect',
            name='code',
            field=models.CharField(blank=True, max_length=32, unique=True, verbose_name='编号'),
        ),
    ]
