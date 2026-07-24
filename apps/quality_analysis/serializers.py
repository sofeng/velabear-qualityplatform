from django.db.models import Max
from django.utils import timezone
from rest_framework import serializers
from apps.core.plaintext_secrets import encrypt_password
from apps.users.group_utils import normalize_existing_group_name
from apps.users.serializers import UserSimpleSerializer

from .jira_services import (
    BUG_PROFILE,
    REQUIREMENT_PROFILE,
    build_jira_record_mapped_fields,
    build_default_jira_config,
    build_default_jira_headers,
    build_default_jira_request_body,
    build_default_requirement_jira_config,
    build_default_requirement_jira_headers,
    build_default_requirement_jira_request_body,
    get_jira_raw_field_labels,
)
from .models import (
    JiraBugRecord,
    JiraInterfaceConfig,
    JiraRequirementInterfaceConfig,
    JiraRequirementRecord,
    JiraRequirementRecordAttachment,
    QualityAnalysisSettings,
    QualityReport,
    normalize_jira_browse_prefix,
)
from .services import get_default_user
from .version_utils import normalize_jira_version


class QualityReportSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    source_excel_name = serializers.SerializerMethodField()
    processed_excel_name = serializers.SerializerMethodField()
    requirement_excel_name = serializers.SerializerMethodField()
    testcase_excel_name = serializers.SerializerMethodField()

    class Meta:
        model = QualityReport
        fields = [
            'id',
            'version',
            'status',
            'status_display',
            'total_defects',
            'classified_defects',
            'analysis_result',
            'error_message',
            'share_token',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'analyzed_at',
            'source_excel',
            'source_excel_name',
            'processed_excel',
            'processed_excel_name',
            'requirement_excel',
            'requirement_excel_name',
            'testcase_excel',
            'testcase_excel_name',
        ]
        read_only_fields = [
            'status',
            'status_display',
            'total_defects',
            'classified_defects',
            'analysis_result',
            'error_message',
            'share_token',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'analyzed_at',
            'processed_excel',
            'processed_excel_name',
        ]

    def get_source_excel_name(self, obj):
        return obj.source_excel.name.split('/')[-1] if obj.source_excel else ''

    def get_processed_excel_name(self, obj):
        return obj.processed_excel.name.split('/')[-1] if obj.processed_excel else ''

    def get_requirement_excel_name(self, obj):
        return obj.requirement_excel.name.split('/')[-1] if obj.requirement_excel else ''

    def get_testcase_excel_name(self, obj):
        return obj.testcase_excel.name.split('/')[-1] if obj.testcase_excel else ''


class QualityReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityReport
        fields = ['id', 'version', 'source_excel']

    def validate_version(self, value):
        normalized = normalize_jira_version(value)
        if not normalized:
            raise serializers.ValidationError('请输入版本号')
        return normalized

    def validate_source_excel(self, value):
        if not value.name.lower().endswith('.xlsx'):
            raise serializers.ValidationError('仅支持 .xlsx 格式的 Excel 文件')
        return value

    def create(self, validated_data):
        validated_data['created_by'] = get_default_user(self.context['request'].user)
        return super().create(validated_data)


class SupplementalExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.lower().endswith('.xlsx'):
            raise serializers.ValidationError('仅支持 .xlsx 格式的 Excel 文件')
        return value


class QualityAnalysisSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityAnalysisSettings
        fields = ['id', 'jira_browse_prefix', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_jira_browse_prefix(self, value):
        return normalize_jira_browse_prefix(value)


JIRA_CONFIG_FIELDS = [
    'id',
    'version',
    'name',
    'request_url',
    'request_method',
    'request_headers',
    'request_body',
    'timeout_seconds',
    'jira_login_enabled',
    'jira_login_url',
    'jira_username',
    'jira_password',
    'has_jira_password',
    'is_active',
    'notes',
    'last_executed_at',
    'last_status_code',
    'last_record_count',
    'last_execution_message',
    'record_count',
    'created_by',
    'created_by_name',
    'created_at',
    'updated_at',
]

JIRA_RECORD_FIELDS = [
    'id',
    'config',
    'config_version',
    'version',
    'issue_id',
    'issue_key',
    'issue_type',
    'summary',
    'module',
    'customer_name',
    'priority',
    'status',
    'creator',
    'handler',
    'tester',
    'group_name',
    'row_index',
    'raw_fields',
    'synced_at',
    'created_at',
    'updated_at',
]

JIRA_REQUIREMENT_RECORD_EXTRA_FIELDS = [
    'description',
    'frontend_developer',
    'backend_developer',
    'related_mindmaps',
    'attachments_count',
    'attachments',
]

JIRA_BUG_RECORD_RELATION_FIELDS = [
    'related_requirements',
    'related_testcases',
    'related_testpoints',
]


class BaseJiraInterfaceConfigSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    record_count = serializers.SerializerMethodField()
    jira_password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    has_jira_password = serializers.SerializerMethodField()

    record_model = None
    default_config_builder = None
    default_headers_builder = None
    default_body_builder = None

    def get_record_count(self, obj):
        return self.record_model.objects.filter(version=normalize_jira_version(obj.version)).count()

    def get_has_jira_password(self, obj):
        return bool(getattr(obj, 'jira_password_encrypted', ''))

    def validate_request_method(self, value):
        return (value or 'POST').upper()

    def validate_version(self, value):
        normalized = normalize_jira_version(value)
        if not normalized:
            raise serializers.ValidationError('请输入版本号')
        return normalized

    def _get_request_template_version(self, fallback=''):
        raw_version = self.initial_data.get('version') if hasattr(self, 'initial_data') else ''
        raw_version = str(raw_version or '').strip()
        return raw_version or fallback

    def create(self, validated_data):
        jira_password = validated_data.pop('jira_password', '')
        version = validated_data['version']
        defaults = self.default_config_builder(self._get_request_template_version(version))

        validated_data.setdefault('name', defaults['name'])
        validated_data.setdefault('request_url', defaults['request_url'])
        validated_data.setdefault('request_method', defaults['request_method'])
        validated_data.setdefault('request_headers', defaults['request_headers'])
        validated_data.setdefault('request_body', defaults['request_body'])
        validated_data.setdefault('timeout_seconds', defaults['timeout_seconds'])
        validated_data.setdefault('jira_login_url', defaults.get('jira_login_url', ''))
        if jira_password:
            validated_data['jira_password_encrypted'] = encrypt_password(jira_password)
        validated_data['created_by'] = get_default_user(self.context['request'].user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        jira_password = validated_data.pop('jira_password', None)
        old_version = instance.version
        new_version = validated_data.get('version', old_version)
        request_template_version = self._get_request_template_version(new_version)

        if old_version != new_version:
            if 'request_body' not in validated_data:
                validated_data['request_body'] = self.default_body_builder(request_template_version)
            if 'request_headers' not in validated_data:
                headers = dict(instance.request_headers or self.default_headers_builder(request_template_version))
                headers['referer'] = self.default_headers_builder(request_template_version).get('referer', '')
                validated_data['request_headers'] = headers

        if jira_password:
            validated_data['jira_password_encrypted'] = encrypt_password(jira_password)

        instance = super().update(instance, validated_data)

        if old_version != instance.version:
            self.record_model.objects.filter(version=old_version).update(version=instance.version, config=instance)

        return instance


class JiraInterfaceConfigSerializer(BaseJiraInterfaceConfigSerializer):
    record_model = JiraBugRecord
    default_config_builder = staticmethod(build_default_jira_config)
    default_headers_builder = staticmethod(build_default_jira_headers)
    default_body_builder = staticmethod(build_default_jira_request_body)

    class Meta:
        model = JiraInterfaceConfig
        fields = JIRA_CONFIG_FIELDS
        read_only_fields = [
            'last_executed_at',
            'last_status_code',
            'last_record_count',
            'last_execution_message',
            'record_count',
            'has_jira_password',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]


class JiraRequirementInterfaceConfigSerializer(BaseJiraInterfaceConfigSerializer):
    record_model = JiraRequirementRecord
    default_config_builder = staticmethod(build_default_requirement_jira_config)
    default_headers_builder = staticmethod(build_default_requirement_jira_headers)
    default_body_builder = staticmethod(build_default_requirement_jira_request_body)

    class Meta:
        model = JiraRequirementInterfaceConfig
        fields = JIRA_CONFIG_FIELDS
        read_only_fields = JiraInterfaceConfigSerializer.Meta.read_only_fields


class BaseJiraRecordSerializer(serializers.ModelSerializer):
    config_version = serializers.CharField(source='config.version', read_only=True)
    raw_field_labels = serializers.SerializerMethodField()

    def get_raw_field_labels(self, obj):
        return get_jira_raw_field_labels(obj.raw_fields or {})

    class Meta:
        fields = JIRA_RECORD_FIELDS + ['raw_field_labels']
        read_only_fields = fields


class JiraRequirementRecordAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = JiraRequirementRecordAttachment
        fields = ['id', 'name', 'file', 'uploaded_by', 'uploaded_at']


class JiraRequirementRelationItemSerializer(serializers.Serializer):
    issue_key = serializers.CharField(required=False, allow_blank=True, max_length=100)
    summary = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    version = serializers.CharField(required=False, allow_blank=True, max_length=100)


class JiraManualRelationItemSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    mindmap_id = serializers.IntegerField(required=False, allow_null=True)
    mindmap_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    node_text = serializers.CharField(required=False, allow_blank=True, max_length=500)
    node_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    path = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    parent_text = serializers.CharField(required=False, allow_blank=True, max_length=500)
    case_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    responsibility_group = serializers.CharField(required=False, allow_blank=True, max_length=255)
    version_name = serializers.CharField(required=False, allow_blank=True, max_length=100)


class JiraBugRecordAssociationSerializer(serializers.Serializer):
    related_requirements = JiraRequirementRelationItemSerializer(many=True, required=False)
    related_testcases = JiraManualRelationItemSerializer(many=True, required=False)
    related_testpoints = JiraManualRelationItemSerializer(many=True, required=False)

    def _normalize_requirement_items(self, value):
        normalized_items = []
        seen_issue_keys = set()

        for item in value or []:
            if not isinstance(item, dict):
                item = dict(item)

            normalized_item = {
                'issue_key': str(item.get('issue_key') or '').strip(),
                'summary': str(item.get('summary') or '').strip(),
                'version': normalize_jira_version(item.get('version') or ''),
            }

            issue_key = normalized_item['issue_key']
            if not issue_key or issue_key in seen_issue_keys:
                continue

            seen_issue_keys.add(issue_key)
            normalized_items.append(normalized_item)

        return normalized_items

    def _normalize_manual_relation_items(self, value, *, default_node_type=''):
        normalized_items = []
        seen_keys = set()

        for item in value or []:
            if not isinstance(item, dict):
                item = dict(item)

            normalized_item = {
                'id': str(item.get('id') or item.get('node_id') or '').strip(),
                'mindmap_id': item.get('mindmap_id') or None,
                'mindmap_name': str(item.get('mindmap_name') or '').strip(),
                'node_text': str(item.get('node_text') or '').strip(),
                'node_type': str(item.get('node_type') or default_node_type).strip(),
                'path': str(item.get('path') or '').strip(),
                'parent_text': str(item.get('parent_text') or '').strip(),
                'case_id': str(item.get('case_id') or '').strip(),
                'responsibility_group': str(item.get('responsibility_group') or '').strip(),
                'version_name': str(item.get('version_name') or '').strip(),
            }

            if not any([
                normalized_item['mindmap_id'],
                normalized_item['mindmap_name'],
                normalized_item['node_text'],
                normalized_item['path'],
            ]):
                continue

            unique_key = '::'.join([
                str(normalized_item['mindmap_id'] or 0),
                normalized_item['node_type'] or default_node_type or 'node',
                normalized_item['path'] or normalized_item['node_text'] or normalized_item['mindmap_name'],
            ])
            if unique_key in seen_keys:
                continue

            seen_keys.add(unique_key)
            normalized_items.append(normalized_item)

        return normalized_items

    def validate_related_requirements(self, value):
        return self._normalize_requirement_items(value)

    def validate_related_testcases(self, value):
        return self._normalize_manual_relation_items(value, default_node_type='case')

    def validate_related_testpoints(self, value):
        return self._normalize_manual_relation_items(value, default_node_type='testpoint')


class JiraBugRecordSerializer(BaseJiraRecordSerializer):
    mapped_fields = serializers.SerializerMethodField()

    class Meta(BaseJiraRecordSerializer.Meta):
        model = JiraBugRecord
        fields = BaseJiraRecordSerializer.Meta.fields + ['mapped_fields'] + JIRA_BUG_RECORD_RELATION_FIELDS
        read_only_fields = fields

    def get_mapped_fields(self, obj):
        return build_jira_record_mapped_fields(
            obj,
            BUG_PROFILE,
            role_member_lookup=self.context.get('role_member_lookup'),
        )


class JiraRequirementRecordSerializer(BaseJiraRecordSerializer):
    attachments = JiraRequirementRecordAttachmentSerializer(many=True, read_only=True)
    attachments_count = serializers.SerializerMethodField()
    related_mindmap_count = serializers.SerializerMethodField()
    version_defect_count = serializers.SerializerMethodField()
    bug_record_count = serializers.SerializerMethodField()
    mapped_fields = serializers.SerializerMethodField()

    class Meta(BaseJiraRecordSerializer.Meta):
        model = JiraRequirementRecord
        fields = BaseJiraRecordSerializer.Meta.fields + [
            'mapped_fields',
            'related_mindmap_count',
            'version_defect_count',
            'bug_record_count',
        ] + JIRA_REQUIREMENT_RECORD_EXTRA_FIELDS
        read_only_fields = fields

    def get_mapped_fields(self, obj):
        return build_jira_record_mapped_fields(
            obj,
            REQUIREMENT_PROFILE,
            role_member_lookup=self.context.get('role_member_lookup'),
        )

    def get_attachments_count(self, obj):
        prefetched_attachments = getattr(obj, '_prefetched_objects_cache', {}).get('attachments')
        if prefetched_attachments is not None:
            return len(prefetched_attachments)
        return obj.attachments.count()

    def get_related_mindmap_count(self, obj):
        return len(obj.related_mindmaps or [])

    def get_version_defect_count(self, obj):
        lookup = self.context.get('requirement_version_defect_count_lookup') or {}
        lookup_key = (str(getattr(obj, 'version', '') or '').strip(), str(getattr(obj, 'issue_key', '') or '').strip())
        return int(lookup.get(lookup_key, getattr(obj, 'version_defect_count', 0)) or 0)

    def get_bug_record_count(self, obj):
        lookup = self.context.get('requirement_bug_record_count_lookup') or {}
        lookup_key = (str(getattr(obj, 'version', '') or '').strip(), str(getattr(obj, 'issue_key', '') or '').strip())
        return int(lookup.get(lookup_key, getattr(obj, 'bug_record_count', 0)) or 0)


class JiraRequirementRecordCreateUpdateSerializer(serializers.ModelSerializer):
    retain_attachment_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )

    class Meta:
        model = JiraRequirementRecord
        fields = [
            'version',
            'issue_id',
            'issue_key',
            'issue_type',
            'summary',
            'module',
            'customer_name',
            'priority',
            'status',
            'description',
            'creator',
            'handler',
            'tester',
            'group_name',
            'frontend_developer',
            'backend_developer',
            'related_mindmaps',
            'row_index',
            'raw_fields',
            'retain_attachment_ids',
        ]

    def validate_version(self, value):
        normalized = normalize_jira_version(value)
        if not normalized:
            raise serializers.ValidationError('请输入版本号')
        return normalized

    def validate_issue_key(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入需求编号')
        return normalized

    def validate_summary(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入需求标题')
        return normalized

    def validate_group_name(self, value):
        return normalize_existing_group_name(value)

    def validate_related_mindmaps(self, value):
        return JiraBugRecordAssociationSerializer()._normalize_manual_relation_items(
            value,
            default_node_type='mindmap',
        )

    def validate_raw_fields(self, value):
        return value or {}

    def validate_retain_attachment_ids(self, value):
        return [int(item) for item in (value or []) if int(item) > 0]

    def validate(self, attrs):
        version = attrs.get('version') or getattr(self.instance, 'version', '')
        issue_key = attrs.get('issue_key') or getattr(self.instance, 'issue_key', '')

        queryset = JiraRequirementRecord.objects.filter(version=version, issue_key=issue_key)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if version and issue_key and queryset.exists():
            raise serializers.ValidationError({'issue_key': '该版本下已存在相同需求编号'})

        return attrs

    def create(self, validated_data):
        if not validated_data.get('row_index'):
            max_row_index = (
                JiraRequirementRecord.objects
                .filter(version=validated_data['version'])
                .aggregate(max_row_index=Max('row_index'))
                .get('max_row_index') or 0
            )
            validated_data['row_index'] = max_row_index + 1

        validated_data.setdefault('synced_at', timezone.now())
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'version' in validated_data or 'issue_key' in validated_data:
            validated_data['synced_at'] = timezone.now()

        return super().update(instance, validated_data)
