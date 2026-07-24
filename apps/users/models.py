from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    department = models.CharField(max_length=100, null=True, blank=True, verbose_name='部门')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='职位')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    @property
    def full_name(self):
        first_name = str(self.first_name or '').strip()
        last_name = str(self.last_name or '').strip()
        full_name = f'{first_name}{last_name}'.strip()
        return full_name or self.username or self.email or f'用户{self.pk}'

    def get_effective_permission_codes(self):
        permission_items = PermissionItem.objects.filter(is_active=True)

        if self.is_staff or self.is_superuser:
            return list(permission_items.values_list('code', flat=True))

        return list(
            permission_items
            .filter(role_permissions__role__members=self)
            .order_by('sort_order', 'name', 'id')
            .distinct()
            .values_list('code', flat=True)
        )

    def has_permission_code(self, code):
        normalized_code = str(code or '').strip()
        if not normalized_code:
            return False

        if self.is_staff or self.is_superuser:
            return True

        return PermissionItem.objects.filter(
            is_active=True,
            code=normalized_code,
            role_permissions__role__members=self,
        ).exists()

    class Meta:
        db_table = 'users_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'


class Role(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='角色名称')
    members = models.ManyToManyField(User, blank=True, related_name='roles', verbose_name='角色成员')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users_role'
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class PermissionItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('module', '模块'),
        ('menu', '菜单'),
        ('button', '按钮'),
        ('action', '操作项'),
    ]

    name = models.CharField(max_length=100, verbose_name='权限名称')
    code = models.CharField(max_length=150, unique=True, verbose_name='权限编码')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='权限类型')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name='父级权限',
    )
    route_path = models.CharField(max_length=255, blank=True, verbose_name='路由路径')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序值')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    description = models.CharField(max_length=255, blank=True, verbose_name='描述')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users_permission_item'
        verbose_name = '权限项'
        verbose_name_plural = '权限项'
        ordering = ['sort_order', 'name', 'id']

    def __str__(self):
        return f'{self.get_item_type_display()}:{self.name}'


class RoleMembership(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_memberships', verbose_name='角色')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_memberships', verbose_name='角色成员')
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users_role_membership'
        verbose_name = '角色成员关系'
        verbose_name_plural = '角色成员关系'
        ordering = ['role_id', 'user_id']
        constraints = [
            models.UniqueConstraint(fields=['role', 'user'], name='users_role_membership_unique'),
        ]

    def __str__(self):
        return f'{self.role_id}:{self.user_id}'


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions', verbose_name='角色')
    permission_item = models.ForeignKey(
        PermissionItem,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='权限项',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users_role_permission'
        verbose_name = '角色权限'
        verbose_name_plural = '角色权限'
        ordering = ['role_id', 'permission_item_id']
        constraints = [
            models.UniqueConstraint(fields=['role', 'permission_item'], name='users_role_permission_unique'),
        ]

    def __str__(self):
        return f'{self.role_id}:{self.permission_item_id}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, default='light', verbose_name='主题')
    language = models.CharField(max_length=10, default='zh-cn', verbose_name='语言')
    timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name='时区')
    notifications = models.JSONField(default=dict, verbose_name='通知设置')

    class Meta:
        db_table = 'user_profiles'
        verbose_name = '用户配置'
        verbose_name_plural = '用户配置'
