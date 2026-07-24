from rest_framework import serializers

from apps.users.serializers import UserSerializer
from .models import DEV_SELF_TEST_AUDIT_STATUS_CHOICES, SELF_TEST_STATUS_CHOICES


class DevSelfTestSerializer(serializers.Serializer):
    id = serializers.CharField(help_text='Node ID')
    mindmap_id = serializers.IntegerField(help_text='Mindmap ID')
    mindmap_name = serializers.CharField(help_text='Mindmap name')
    requirement_key = serializers.CharField(allow_blank=True, help_text='Requirement key')
    requirement_title = serializers.CharField(allow_blank=True, help_text='Requirement title')
    module = serializers.CharField(help_text='Module name')
    module_path = serializers.CharField(allow_blank=True, help_text='Module path')
    path = serializers.CharField(allow_blank=True, help_text='Node path')
    testpoint = serializers.CharField(help_text='Test point')
    priority = serializers.IntegerField(help_text='Priority')
    status = serializers.ChoiceField(choices=SELF_TEST_STATUS_CHOICES, help_text='Status')
    audit_status = serializers.ChoiceField(choices=DEV_SELF_TEST_AUDIT_STATUS_CHOICES, help_text='Audit status')
    can_edit = serializers.BooleanField(help_text='Whether the item can be edited')
    responsibility_group = serializers.CharField(allow_blank=True, help_text='Responsibility group')
    frontend_developer = UserSerializer(allow_null=True, help_text='Frontend developer')
    backend_developer = UserSerializer(allow_null=True, help_text='Backend developer')
    updated_at = serializers.DateTimeField(help_text='Updated at')


class DevSelfTestDetailSerializer(serializers.Serializer):
    id = serializers.CharField(help_text='Node ID')
    mindmap_id = serializers.IntegerField(help_text='Mindmap ID')
    mindmap_name = serializers.CharField(help_text='Mindmap name')
    module = serializers.CharField(allow_blank=True, help_text='Module name')
    module_path = serializers.CharField(allow_blank=True, help_text='Module path')
    testpoint = serializers.CharField(help_text='Test point')
    preconditions = serializers.CharField(allow_blank=True, help_text='Preconditions')
    steps = serializers.CharField(allow_blank=True, help_text='Steps')
    expected_result = serializers.CharField(allow_blank=True, help_text='Expected result')
    remark = serializers.CharField(allow_blank=True, help_text='Remark')
    status = serializers.ChoiceField(choices=SELF_TEST_STATUS_CHOICES, help_text='Status')
    audit_status = serializers.ChoiceField(choices=DEV_SELF_TEST_AUDIT_STATUS_CHOICES, help_text='Audit status')
    can_edit = serializers.BooleanField(help_text='Whether the item can be edited')
    responsibility_group = serializers.CharField(allow_blank=True, help_text='Responsibility group')
    frontend_developer = UserSerializer(allow_null=True, help_text='Frontend developer')
    backend_developer = UserSerializer(allow_null=True, help_text='Backend developer')
    updated_at = serializers.DateTimeField(help_text='Updated at')


class DevSelfTestUpdateSerializer(serializers.Serializer):
    steps = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(required=False, choices=SELF_TEST_STATUS_CHOICES)


class DevSelfTestAuditItemSerializer(serializers.Serializer):
    mindmap_id = serializers.IntegerField()
    node_id = serializers.CharField(required=False, allow_blank=True)
    id = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        node_id = str(attrs.get('node_id') or attrs.get('id') or '').strip()
        if not node_id:
            raise serializers.ValidationError({'node_id': ['该字段不能为空。']})

        attrs['node_id'] = node_id
        attrs.pop('id', None)
        return attrs


class DevSelfTestAuditSerializer(serializers.Serializer):
    items = DevSelfTestAuditItemSerializer(many=True)
    audit_status = serializers.ChoiceField(choices=DEV_SELF_TEST_AUDIT_STATUS_CHOICES)
