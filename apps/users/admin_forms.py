from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserAdminNameMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk and 'full_name' in self.fields:
            self.fields['full_name'].initial = instance.full_name

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = str(self.cleaned_data.get('full_name') or '').strip()
        user.first_name = full_name
        user.last_name = ''

        if commit:
            user.save()
            if hasattr(self, 'save_m2m'):
                self.save_m2m()

        return user


class UserAdminCreationForm(UserAdminNameMixin, UserCreationForm):
    full_name = forms.CharField(label='姓名', required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'email',
            'avatar',
            'phone',
            'department',
            'position',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )


class UserAdminChangeForm(UserAdminNameMixin, UserChangeForm):
    full_name = forms.CharField(label='姓名', required=False)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
