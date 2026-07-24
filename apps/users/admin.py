from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ['username', 'email', 'full_name_display', 'department', 'position', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'department', 'position']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at']

    fieldsets = (
        ('账号信息', {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('full_name', 'email', 'avatar', 'phone', 'department', 'position')}),
        ('权限信息', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('时间信息', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        ('账号信息', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('个人信息', {
            'classes': ('wide',),
            'fields': ('full_name', 'email', 'avatar', 'phone', 'department', 'position'),
        }),
        ('权限信息', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    @admin.display(description='姓名')
    def full_name_display(self, obj):
        return obj.full_name


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'language', 'timezone']
