from django.contrib.auth.models import Group
from rest_framework import serializers


def normalize_existing_group_name(value, *, field_label='组别'):
    normalized = str(value or '').strip()
    if not normalized:
        return ''

    if not Group.objects.filter(name=normalized).exists():
        raise serializers.ValidationError(f'{field_label}不存在，请先在管理页的“组别”中维护')

    return normalized
