import re
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import serializers

from apps.projects.serializers import ProjectSimpleSerializer
from apps.users.serializers import UserSimpleSerializer
from apps.versions.serializers import VersionSimpleSerializer
from apps.workflow.services import get_workflow_summary

from .models import Defect, DefectAttachment, DefectComment, DefectEmailConfig, DefectHistory, WikiDirectory

RICH_TEXT_IMAGE_PREFIX = 'defect_rich_text_images/'
RICH_TEXT_IMAGE_TAG_PATTERN = re.compile(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', re.IGNORECASE)


def normalize_media_relative_path(source):
    if not source:
        return ''

    parsed_url = urlparse(str(source))
    path = parsed_url.path if parsed_url.scheme or parsed_url.netloc else str(source)

    if path.startswith(settings.MEDIA_URL):
        path = path[len(settings.MEDIA_URL):]

    normalized_path = path.lstrip('/').replace('\\', '/')
    if normalized_path.startswith('../'):
        return ''

    return normalized_path


def normalize_rich_text_media_html(content, request=None):
    normalized_content = str(content or '')
    if not normalized_content:
        return normalized_content

    def replace_image_source(match):
        current_source = match.group(2)
        relative_path = normalize_media_relative_path(current_source)
        if not relative_path.startswith(RICH_TEXT_IMAGE_PREFIX):
            return match.group(0)

        next_source = f"{settings.MEDIA_URL.rstrip('/')}/{relative_path.lstrip('/')}"
        return f'{match.group(1)}{next_source}{match.group(3)}'

    return RICH_TEXT_IMAGE_TAG_PATTERN.sub(replace_image_source, normalized_content)


class DefectAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = DefectAttachment
        fields = ['id', 'name', 'file', 'uploaded_by', 'uploaded_at']


class DefectCommentSerializer(serializers.ModelSerializer):
    author = UserSimpleSerializer(read_only=True)

    class Meta:
        model = DefectComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['content'] = normalize_rich_text_media_html(
            representation.get('content'),
            self.context.get('request'),
        )
        return representation


class DefectHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = DefectHistory
        fields = ['id', 'field', 'action', 'from_value', 'to_value', 'changed_by', 'created_at']


class DefectRelationItemSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    mindmap_id = serializers.IntegerField(required=False, allow_null=True)
    mindmap_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    node_text = serializers.CharField(required=False, allow_blank=True, max_length=500)
    node_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    path = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    parent_text = serializers.CharField(required=False, allow_blank=True, max_length=500)
    case_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    responsibility_group = serializers.CharField(required=False, allow_blank=True, max_length=255)


class DefectListSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    version = VersionSimpleSerializer(read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    assignees = UserSimpleSerializer(many=True, read_only=True)
    attachments_count = serializers.SerializerMethodField()
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = Defect
        fields = [
            'id',
            'record_type',
            'code',
            'project',
            'version',
            'title',
            'problem_reason',
            'root_cause',
            'frontend_developer',
            'backend_developer',
            'priority',
            'severity',
            'status',
            'requirement_id',
            'modules',
            'related_testcases',
            'related_testpoints',
            'labels',
            'created_by',
            'assignees',
            'attachments_count',
            'workflow',
            'created_at',
            'updated_at',
        ]

    def get_attachments_count(self, obj):
        return obj.attachments.count()

    def get_workflow(self, obj):
        request = self.context.get('request')
        workflow_biz_type = self.context.get('workflow_biz_type', 'defect')
        return get_workflow_summary(workflow_biz_type, obj.id, user=getattr(request, 'user', None))


class DefectDetailSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    version = VersionSimpleSerializer(read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    assignees = UserSimpleSerializer(many=True, read_only=True)
    resolved_by = UserSimpleSerializer(read_only=True)
    closed_by = UserSimpleSerializer(read_only=True)
    attachments = DefectAttachmentSerializer(many=True, read_only=True)
    comments = DefectCommentSerializer(many=True, read_only=True)
    history_records = DefectHistorySerializer(many=True, read_only=True)
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = Defect
        fields = [
            'id',
            'record_type',
            'code',
            'project',
            'version',
            'title',
            'description',
            'problem_reason',
            'root_cause',
            'frontend_developer',
            'backend_developer',
            'priority',
            'severity',
            'status',
            'requirement_id',
            'modules',
            'related_testcases',
            'related_testpoints',
            'labels',
            'created_by',
            'assignees',
            'resolved_by',
            'closed_by',
            'resolved_at',
            'closed_at',
            'attachments',
            'comments',
            'history_records',
            'workflow',
            'created_at',
            'updated_at',
        ]

    def get_workflow(self, obj):
        request = self.context.get('request')
        workflow_biz_type = self.context.get('workflow_biz_type', 'defect')
        return get_workflow_summary(workflow_biz_type, obj.id, user=getattr(request, 'user', None))

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['description'] = normalize_rich_text_media_html(
            representation.get('description'),
            self.context.get('request'),
        )
        return representation


class DefectCreateUpdateSerializer(serializers.ModelSerializer):
    record_type = serializers.ChoiceField(choices=Defect.RECORD_TYPE_CHOICES, required=False)
    project_id = serializers.IntegerField(required=True)
    version_id = serializers.IntegerField(required=False, allow_null=True)
    assignee_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    labels = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    retain_attachment_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    modules = DefectRelationItemSerializer(many=True, required=False)
    related_testcases = DefectRelationItemSerializer(many=True, required=False)
    related_testpoints = DefectRelationItemSerializer(many=True, required=False)

    class Meta:
        model = Defect
        fields = [
            'project_id',
            'record_type',
            'version_id',
            'title',
            'description',
            'problem_reason',
            'root_cause',
            'frontend_developer',
            'backend_developer',
            'priority',
            'severity',
            'status',
            'requirement_id',
            'modules',
            'related_testcases',
            'related_testpoints',
            'labels',
            'assignee_ids',
            'retain_attachment_ids',
        ]

    def validate_labels(self, value):
        return [str(item).strip() for item in value if str(item).strip()]

    def _normalize_relation_items(self, value, *, default_node_type=''):
        normalized_items = []
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
            }

            if not any([
                normalized_item['mindmap_id'],
                normalized_item['mindmap_name'],
                normalized_item['node_text'],
                normalized_item['path'],
            ]):
                continue

            normalized_items.append(normalized_item)

        return normalized_items

    def validate_modules(self, value):
        return self._normalize_relation_items(value, default_node_type='module')

    def validate_related_testcases(self, value):
        return self._normalize_relation_items(value, default_node_type='case')

    def validate_related_testpoints(self, value):
        return self._normalize_relation_items(value, default_node_type='testpoint')

    def validate(self, attrs):
        title = str(attrs.get('title', getattr(self.instance, 'title', '') or '')).strip()
        description = str(attrs.get('description', getattr(self.instance, 'description', '') or '')).strip()

        if not title:
            raise serializers.ValidationError({'title': '标题不能为空'})
        if not description:
            raise serializers.ValidationError({'description': '描述不能为空'})
        return attrs


class DefectStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Defect.STATUS_CHOICES)


class DefectAssigneeUpdateSerializer(serializers.Serializer):
    assignee_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)


class DefectCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False, trim_whitespace=True)


class DefectEmailConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectEmailConfig
        fields = [
            'id',
            'host',
            'port',
            'username',
            'password',
            'from_name',
            'from_email',
            'new_bug_template',
            'resolved_bug_template',
            'rejected_bug_template',
            'reopened_bug_template',
            'is_active',
            'created_by',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'updated_by', 'created_at', 'updated_at']


class DefectEmailTestSerializer(serializers.Serializer):
    to = serializers.EmailField()
    subject = serializers.CharField(required=False, allow_blank=True, max_length=255)
    text = serializers.CharField(required=False, allow_blank=True)


class DefectNotificationSettingsSerializer(serializers.Serializer):
    types = serializers.ListField(
        child=serializers.ChoiceField(choices=['new', 'assign', 'title', 'description', 'status', 'comment']),
        allow_empty=True,
    )


class WikiDirectorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = WikiDirectory
        fields = [
            'id',
            'project',
            'project_name',
            'parent',
            'name',
            'description',
            'sort_order',
            'children',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'project_name', 'children', 'created_by', 'created_at', 'updated_at']

    def get_children(self, obj):
        children = getattr(obj, 'prefetched_children', None)
        if children is None:
            children = obj.children.all().order_by('sort_order', 'id')
        return WikiDirectorySerializer(children, many=True, context=self.context).data


class WikiDirectoryCreateUpdateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = WikiDirectory
        fields = ['project_id', 'parent_id', 'name', 'description', 'sort_order']

    def validate_name(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('目录名称不能为空')
        return normalized
