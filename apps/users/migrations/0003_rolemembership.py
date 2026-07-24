from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def backfill_role_memberships(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    RoleMembership = apps.get_model('users', 'RoleMembership')

    for role in Role.objects.prefetch_related('members').all():
        for member in role.members.all():
            RoleMembership.objects.get_or_create(
                role_id=role.id,
                user_id=member.id,
                defaults={'tags': []},
            )


def rollback_role_memberships(apps, schema_editor):
    RoleMembership = apps.get_model('users', 'RoleMembership')
    RoleMembership.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoleMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tags', models.JSONField(blank=True, default=list, verbose_name='标签')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_memberships', to='users.role', verbose_name='角色')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_memberships', to='users.user', verbose_name='角色成员')),
            ],
            options={
                'verbose_name': '角色成员关系',
                'verbose_name_plural': '角色成员关系',
                'db_table': 'users_role_membership',
                'ordering': ['role_id', 'user_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='rolemembership',
            constraint=models.UniqueConstraint(fields=('role', 'user'), name='users_role_membership_unique'),
        ),
        migrations.RunPython(backfill_role_memberships, rollback_role_memberships),
    ]
