import json
import os
import re
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.db import models, transaction
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import get_valid_filename
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from apps.projects.models import Project
from apps.testcases.models import ManualTestCaseMindmap
from apps.testcases.mindmap_node_utils import (
    parse_public_node_id,
    relation_item_matches_public_node_id,
    resolve_public_node_descriptor,
)
from apps.users.models import User
from apps.versions.models import Version
from apps.workflow.models import WorkflowInstance
from .excel_import import import_defects_from_excel_file
from .models import Defect, DefectAttachment, DefectComment, DefectHistory, WikiDirectory
from .notification_services import (
    notify_defect_assignees_updated,
    notify_defect_comment_created,
    notify_defect_created,
    notify_defect_status_updated,
    notify_defect_updated,
    resolve_frontend_base_url,
    safely_execute_notification,
)
from .serializers import (
    DefectAssigneeUpdateSerializer,
    DefectCommentCreateSerializer,
    DefectCommentSerializer,
    DefectCreateUpdateSerializer,
    DefectDetailSerializer,
    DefectHistorySerializer,
    DefectListSerializer,
    DefectStatusUpdateSerializer,
    WikiDirectoryCreateUpdateSerializer,
    WikiDirectorySerializer,
)

TESTING_MINDMAP_SCOPE = ManualTestCaseMindmap.SCOPE_TESTING

RICH_TEXT_IMAGE_PREFIX = 'defect_rich_text_images/'
RICH_TEXT_IMAGE_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


class DefectPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_accessible_projects(user):
    return Project.objects.all().distinct()


def normalize_record_type(value):
    normalized = str(value or '').strip()
    allowed_record_types = {item[0] for item in Defect.RECORD_TYPE_CHOICES}
    return normalized if normalized in allowed_record_types else Defect.RECORD_TYPE_DEFECT


def get_record_type_from_request(request):
    data_value = ''
    if getattr(request, 'method', '').upper() in {'POST', 'PUT', 'PATCH'}:
        data_value = request.data.get('record_type') if hasattr(request, 'data') else ''
    return normalize_record_type(request.query_params.get('record_type') or data_value)


def get_accessible_defects(user, record_type=Defect.RECORD_TYPE_DEFECT):
    accessible_projects = get_accessible_projects(user)
    queryset = Defect.objects.filter(project__in=accessible_projects)
    if record_type:
        queryset = queryset.filter(record_type=normalize_record_type(record_type))
    return (
        queryset
        .select_related('project', 'version', 'created_by', 'resolved_by', 'closed_by')
        .prefetch_related('assignees')
        .distinct()
    )


ANALYSIS_EMPTY_LABEL = '未填写'
ANALYSIS_EMPTY_VERSION_LABEL = '未关联版本'
DEFECT_STATUS_LABELS = dict(Defect.STATUS_CHOICES)
DEFECT_STATUS_ORDER = [item[0] for item in Defect.STATUS_CHOICES]


def normalize_analysis_label(value, fallback=ANALYSIS_EMPTY_LABEL):
    normalized = str(value or '').strip()
    return normalized or fallback


def increment_analysis_matrix(matrix, category, series_key, count):
    if not category or not series_key:
        return
    matrix.setdefault(category, {})
    matrix[category][series_key] = matrix[category].get(series_key, 0) + int(count or 0)


def sort_analysis_labels(labels):
    return sorted(labels, key=lambda item: str(item).lower())


def build_analysis_matrix_payload(matrix, *, categories=None, series_order=None, series_labels=None):
    normalized_categories = list(categories or sort_analysis_labels(matrix.keys()))
    series_keys = []
    seen_keys = set()

    for item in series_order or []:
        if item in seen_keys:
            continue
        seen_keys.add(item)
        series_keys.append(item)

    extra_keys = {
        series_key
        for values in matrix.values()
        for series_key, count in values.items()
        if int(count or 0) > 0 and series_key not in seen_keys
    }
    series_keys.extend(sort_analysis_labels(extra_keys))

    label_lookup = series_labels or {}
    series = [
        {
            'key': series_key,
            'name': label_lookup.get(series_key, series_key),
            'data': [int(matrix.get(category, {}).get(series_key, 0) or 0) for category in normalized_categories],
        }
        for series_key in series_keys
    ]

    return {
        'categories': normalized_categories,
        'series': series,
        'total': sum(sum(item['data']) for item in series),
    }


def is_all_version_value(value):
    normalized = str(value or '').strip().lower()
    return normalized in {'', 'all', 'null', 'none', 'undefined'}


def get_accessible_wiki_directories(user):
    accessible_projects = get_accessible_projects(user)
    return (
        WikiDirectory.objects
        .filter(project__in=accessible_projects)
        .select_related('project', 'parent', 'created_by')
        .order_by('sort_order', 'id')
    )


def get_wiki_directory_path(directory):
    parts = []
    current = directory
    seen_ids = set()
    while current and current.id not in seen_ids:
        seen_ids.add(current.id)
        parts.append(current.name)
        current = current.parent
    return ' / '.join(reversed(parts))


def wiki_page_matches_directory(wiki_page, directory_ids):
    normalized_ids = {str(item) for item in directory_ids if item}
    if not normalized_ids:
        return True

    for relation_item in wiki_page.modules or []:
        if not isinstance(relation_item, dict):
            continue
        relation_id = str(relation_item.get('id') or relation_item.get('directory_id') or '').strip()
        if relation_id in normalized_ids:
            return True
    return False


def get_wiki_directory_descendant_ids(directory):
    descendant_ids = []
    pending_ids = [directory.id]
    while pending_ids:
        children = list(WikiDirectory.objects.filter(parent_id__in=pending_ids).values_list('id', flat=True))
        descendant_ids.extend(children)
        pending_ids = children
    return descendant_ids


def parse_request_list(data, key, cast=str):
    if hasattr(data, 'getlist') and key in data:
        values = data.getlist(key)
        if len(values) > 1:
            return [cast(item) for item in values if str(item).strip()]

    if key not in data:
        return None

    value = data.get(key)
    if value in (None, '', []):
        return []

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            values = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            values = [item.strip() for item in stripped.split(',') if item.strip()]
    else:
        values = [value]

    parsed_values = []
    for item in values:
        item_str = str(item).strip()
        if not item_str:
            continue
        parsed_values.append(cast(item))
    return parsed_values


def parse_request_json_list(data, key):
    if key not in data:
        return None

    value = data.get(key)
    if value in (None, '', []):
        return []

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError({key: '关联数据格式不正确'}) from exc
        values = parsed if isinstance(parsed, list) else [parsed]
    else:
        values = [value]

    normalized_values = []
    for item in values:
        if isinstance(item, dict):
            normalized_values.append(item)

    return normalized_values


def normalize_request_data(request):
    data = {}
    for key in [
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
    ]:
        if key in request.data:
            data[key] = request.data.get(key)

    labels = parse_request_list(request.data, 'labels', str)
    if labels is not None:
        data['labels'] = labels

    assignee_ids = parse_request_list(request.data, 'assignee_ids', int)
    if assignee_ids is not None:
        data['assignee_ids'] = assignee_ids

    retain_attachment_ids = parse_request_list(request.data, 'retain_attachment_ids', int)
    if retain_attachment_ids is not None:
        data['retain_attachment_ids'] = retain_attachment_ids

    for key in ['modules', 'related_testcases', 'related_testpoints']:
        relation_items = parse_request_json_list(request.data, key)
        if relation_items is not None:
            data[key] = relation_items

    if data.get('version_id') in ('', 'null', 'None'):
        data['version_id'] = None

    return data


def resolve_project_for_user(user, project_id):
    project = get_accessible_projects(user).filter(id=project_id).first()
    if not project:
        raise serializers.ValidationError({'project_id': '没有权限访问该项目'})
    return project


def resolve_version_for_project(project, version_id):
    if version_id in (None, '', 'null', 'None'):
        return None
    version = Version.objects.filter(id=version_id, projects__id=project.id).first()
    if not version:
        raise serializers.ValidationError({'version_id': '版本不存在或不属于当前项目'})
    return version


def resolve_default_version_for_project(project):
    return (
        Version.objects
        .filter(projects__id=project.id, is_default=True)
        .order_by('id')
        .first()
    )


def get_user_map_by_ids(user_ids):
    if not user_ids:
        return {}
    return {user.id: user for user in User.objects.filter(id__in=user_ids)}


def normalize_labels(labels):
    if not isinstance(labels, list):
        return []
    return [str(item).strip() for item in labels if str(item).strip()]


def format_relation_history_items(items):
    if not isinstance(items, list):
        return []

    labels = []
    for item in items:
        if not isinstance(item, dict):
            continue

        path = str(item.get('path') or '').strip()
        node_text = str(item.get('node_text') or '').strip()
        mindmap_name = str(item.get('mindmap_name') or '').strip()
        case_id = str(item.get('case_id') or '').strip()

        label = path or node_text or mindmap_name
        if case_id and case_id not in label:
            label = f'{label} ({case_id})' if label else case_id

        if label:
            labels.append(label)

    return labels


def normalize_relation_segment(value):
    return str(value or '').strip()


def split_relation_path(path_value):
    return [
        segment.strip()
        for segment in str(path_value or '').split('/')
        if segment and segment.strip()
    ]


def relation_path_contains(target_parts, relation_parts):
    if not target_parts or len(relation_parts) < len(target_parts):
        return False

    for index in range(len(relation_parts) - len(target_parts) + 1):
        if relation_parts[index:index + len(target_parts)] == target_parts:
            return True

    return False


def defect_matches_module_category(defect, *, category_name='', category_path=''):
    normalized_name = normalize_relation_segment(category_name)
    target_parts = split_relation_path(category_path)

    if not normalized_name and not target_parts:
        return True

    for relation_item in defect.modules or []:
        if not isinstance(relation_item, dict):
            continue

        relation_parts = split_relation_path(relation_item.get('path'))
        relation_node_text = normalize_relation_segment(relation_item.get('node_text'))
        relation_parent_text = normalize_relation_segment(relation_item.get('parent_text'))

        if target_parts and relation_path_contains(target_parts, relation_parts):
            return True

        if normalized_name and (
            relation_node_text == normalized_name or
            relation_parent_text == normalized_name or
            normalized_name in relation_parts
        ):
            return True

    return False


def resolve_testpoint_descriptor_from_queryset(mindmap_queryset, public_node_id):
    parsed_node_id = parse_public_node_id(public_node_id)
    if not parsed_node_id or parsed_node_id.get('node_type') != 'testpoint':
        return None

    mindmap = mindmap_queryset.filter(id=parsed_node_id['mindmap_id']).first()
    if not mindmap:
        return None

    return resolve_public_node_descriptor(mindmap, public_node_id)


def defect_matches_testpoint_id(defect, public_node_id, descriptor=None):
    return any(
        relation_item_matches_public_node_id(relation_item, public_node_id, descriptor)
        for relation_item in (defect.related_testpoints or [])
    )


def format_user_list(users):
    return [user.username or user.email for user in users]


RESOLVED_DEFECT_STATUSES = {'resolved', 'regression_verified', 'requirement_created', 'closed'}
REOPENED_DEFECT_STATUSES = {'new', 'returned_pending', 'reopened'}


def update_status_metadata(defect, operator, next_status):
    if next_status in RESOLVED_DEFECT_STATUSES:
        defect.resolved_by = operator
        defect.resolved_at = timezone.now()
    if next_status == 'closed':
        defect.closed_by = operator
        defect.closed_at = timezone.now()
    elif next_status in REOPENED_DEFECT_STATUSES:
        defect.resolved_by = None
        defect.resolved_at = None
        defect.closed_by = None
        defect.closed_at = None


def clear_attachment_file(attachment):
    storage = attachment.file.storage
    file_name = attachment.file.name
    attachment.delete()
    if file_name and storage.exists(file_name):
        storage.delete(file_name)


def build_media_url(relative_path, request=None):
    return f"{settings.MEDIA_URL.rstrip('/')}/{relative_path.lstrip('/')}"


def normalize_media_relative_path(source):
    if not source:
        return ''

    parsed_url = urlparse(str(source))
    path = parsed_url.path if parsed_url.scheme or parsed_url.netloc else str(source)

    if path.startswith(settings.MEDIA_URL):
        path = path[len(settings.MEDIA_URL):]

    path = path.lstrip('/')
    normalized_path = os.path.normpath(path).replace('\\', '/')

    if normalized_path.startswith('../'):
        return ''

    return normalized_path


def extract_rich_text_image_paths(content):
    paths = set()

    if not content:
        return paths

    for source in RICH_TEXT_IMAGE_PATTERN.findall(str(content)):
        relative_path = normalize_media_relative_path(source)
        if relative_path.startswith(RICH_TEXT_IMAGE_PREFIX):
            paths.add(relative_path)

    return paths


def cleanup_rich_text_images(relative_paths):
    for relative_path in relative_paths:
        if not relative_path.startswith(RICH_TEXT_IMAGE_PREFIX):
            continue

        if default_storage.exists(relative_path):
            default_storage.delete(relative_path)


def collect_comment_rich_text_image_paths(comments):
    paths = set()

    for comment in comments:
        paths.update(extract_rich_text_image_paths(comment.content))

    return paths


def create_history(defect, *, changed_by, field, action, from_value=None, to_value=None):
    DefectHistory.objects.create(
        defect=defect,
        field=field,
        action=action,
        from_value=from_value,
        to_value=to_value,
        changed_by=changed_by,
    )


def apply_attachment_changes(defect, request, operator, retain_attachment_ids=None):
    history_messages = []
    retain_attachment_ids = set(retain_attachment_ids or [])

    if retain_attachment_ids:
        removable_attachments = defect.attachments.exclude(id__in=retain_attachment_ids)
    elif retain_attachment_ids == set():
        removable_attachments = defect.attachments.all()
    else:
        removable_attachments = DefectAttachment.objects.none()

    removed_names = list(removable_attachments.values_list('name', flat=True))
    for attachment in removable_attachments:
        clear_attachment_file(attachment)
    if removed_names:
        history_messages.append(('removed', removed_names))

    uploaded_files = request.FILES.getlist('attachments')
    added_names = []
    for uploaded_file in uploaded_files:
        attachment = DefectAttachment.objects.create(
            defect=defect,
            name=uploaded_file.name,
            file=uploaded_file,
            uploaded_by=operator,
        )
        added_names.append(attachment.name)
    if added_names:
        history_messages.append(('added', added_names))

    for direction, names in history_messages:
        if direction == 'added':
            create_history(
                defect,
                changed_by=operator,
                field='attachments',
                action='attachment',
                from_value=None,
                to_value={'added': names},
            )
        else:
            create_history(
                defect,
                changed_by=operator,
                field='attachments',
                action='attachment',
                from_value={'removed': names},
                to_value=None,
            )


class DefectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefectPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'version', 'priority', 'severity', 'status', 'assignees']
    search_fields = [
        'code',
        'title',
        'description',
        'problem_reason',
        'root_cause',
        'frontend_developer',
        'backend_developer',
        'priority',
        'requirement_id',
    ]
    ordering_fields = ['created_at', 'updated_at', 'priority', 'severity', 'status', 'code']
    ordering = ['-updated_at']
    item_label = '缺陷'
    history_create_field = 'defect'
    workflow_biz_type = 'defect'
    notification_enabled = True

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DefectCreateUpdateSerializer
        return DefectListSerializer

    def get_record_type(self):
        return get_record_type_from_request(self.request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workflow_biz_type'] = self.workflow_biz_type
        return context

    def get_queryset(self):
        queryset = get_accessible_defects(self.request.user, record_type=self.get_record_type())
        created_by = self.request.query_params.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        requirement_id = str(self.request.query_params.get('requirement_id') or '').strip()
        if requirement_id:
            queryset = queryset.filter(requirement_id__iexact=requirement_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        category_name = str(request.query_params.get('module_category_name') or '').strip()
        category_path = str(request.query_params.get('module_category_path') or '').strip()
        testpoint_id = str(request.query_params.get('testpoint_id') or '').strip()

        if category_name or category_path:
            matched_ids = [
                defect.id
                for defect in queryset
                if defect_matches_module_category(
                    defect,
                    category_name=category_name,
                    category_path=category_path,
                )
            ]
            queryset = queryset.filter(id__in=matched_ids)

        if testpoint_id:
            accessible_projects = get_accessible_projects(request.user)
            mindmap_queryset = ManualTestCaseMindmap.objects.filter(
                project__in=accessible_projects,
                mindmap_scope=TESTING_MINDMAP_SCOPE,
            )
            descriptor = resolve_testpoint_descriptor_from_queryset(mindmap_queryset, testpoint_id)
            matched_ids = [
                defect.id
                for defect in queryset
                if defect_matches_testpoint_id(defect, testpoint_id, descriptor)
            ]
            queryset = queryset.filter(id__in=matched_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=normalize_request_data(request))
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        operator = request.user
        frontend_base_url = resolve_frontend_base_url(request)

        project = resolve_project_for_user(operator, validated_data['project_id'])
        version = (
            resolve_version_for_project(project, validated_data.get('version_id')) or
            resolve_default_version_for_project(project)
        )

        defect = Defect.objects.create(
            record_type=normalize_record_type(validated_data.get('record_type') or self.get_record_type()),
            project=project,
            version=version,
            title=validated_data['title'],
            description=validated_data['description'],
            problem_reason=validated_data.get('problem_reason') or '',
            root_cause=validated_data.get('root_cause') or '',
            frontend_developer=validated_data.get('frontend_developer') or '',
            backend_developer=validated_data.get('backend_developer') or '',
            priority=validated_data.get('priority') or 'P3',
            severity=validated_data.get('severity', 'medium'),
            status=validated_data.get('status', 'new'),
            requirement_id=validated_data.get('requirement_id') or '',
            modules=validated_data.get('modules', []),
            related_testcases=validated_data.get('related_testcases', []),
            related_testpoints=validated_data.get('related_testpoints', []),
            labels=normalize_labels(validated_data.get('labels', [])),
            created_by=operator,
        )

        assignee_ids = validated_data.get('assignee_ids', [])
        if assignee_ids:
            user_map = get_user_map_by_ids(assignee_ids)
            defect.assignees.set(user_map.values())
            create_history(
                defect,
                changed_by=operator,
                field='assignees',
                action='assign',
                from_value=[],
                to_value=format_user_list(user_map.values()),
            )

        update_status_metadata(defect, operator, defect.status)
        defect.save()

        create_history(
            defect,
            changed_by=operator,
            field=self.history_create_field,
            action='create',
            from_value=None,
            to_value={
                'code': defect.code,
                'title': defect.title,
                'status': defect.status,
            },
        )

        apply_attachment_changes(defect, request, operator)

        if self.notification_enabled:
            transaction.on_commit(
                lambda: safely_execute_notification(
                    notify_defect_created,
                    defect.id,
                    frontend_base_url=frontend_base_url,
                )
            )

        output = DefectDetailSerializer(
            defect,
            context={'request': request, 'workflow_biz_type': self.workflow_biz_type},
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class DefectVersionAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        queryset = get_accessible_defects(request.user, record_type=Defect.RECORD_TYPE_DEFECT)
        project_id = str(request.query_params.get('project') or request.query_params.get('project_id') or '').strip()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)
        raw_version = request.query_params.get('version') or request.query_params.get('version_id')
        selected_version = not is_all_version_value(raw_version)

        if selected_version:
            queryset = queryset.filter(version_id=raw_version)

        rows = (
            queryset
            .values('version_id', 'version__name', 'frontend_developer', 'backend_developer', 'status', 'root_cause')
            .annotate(record_count=models.Count('id'))
            .order_by('version__name', 'frontend_developer', 'backend_developer', 'status', 'root_cause')
        )

        developer_status_matrix = {}
        developer_root_cause_matrix = {}
        developer_total_by_version_matrix = {}
        root_cause_by_version_matrix = {}
        developer_labels = set()
        root_cause_labels = set()
        version_labels = set()

        for row in rows:
            count = int(row.get('record_count') or 0)
            if count <= 0:
                continue

            version_label = normalize_analysis_label(row.get('version__name'), ANALYSIS_EMPTY_VERSION_LABEL)
            status_key = normalize_analysis_label(row.get('status'))
            root_cause = normalize_analysis_label(row.get('root_cause'))
            frontend_developer = normalize_analysis_label(row.get('frontend_developer'))
            backend_developer = normalize_analysis_label(row.get('backend_developer'))
            role_developers = [
                ('前端', frontend_developer),
                ('后端', backend_developer),
            ]

            version_labels.add(version_label)
            root_cause_labels.add(root_cause)
            increment_analysis_matrix(root_cause_by_version_matrix, version_label, root_cause, count)

            for role_label, developer_name in role_developers:
                developer_label = f'{role_label}-{developer_name}'
                developer_labels.add(developer_label)
                increment_analysis_matrix(developer_status_matrix, developer_label, status_key, count)
                increment_analysis_matrix(developer_root_cause_matrix, developer_label, root_cause, count)
                increment_analysis_matrix(developer_total_by_version_matrix, version_label, developer_label, count)

        developer_categories = sort_analysis_labels(developer_labels)
        version_categories = sort_analysis_labels(version_labels)
        root_cause_series_order = sort_analysis_labels(root_cause_labels)

        return Response(
            {
                'scope': {
                    'mode': 'selected' if selected_version else 'all',
                    'version_id': str(raw_version or '').strip() if selected_version else '',
                },
                'selected_version': {
                    'developer_status': build_analysis_matrix_payload(
                        developer_status_matrix,
                        categories=developer_categories,
                        series_order=DEFECT_STATUS_ORDER,
                        series_labels=DEFECT_STATUS_LABELS,
                    ),
                    'developer_root_cause': build_analysis_matrix_payload(
                        developer_root_cause_matrix,
                        categories=developer_categories,
                        series_order=root_cause_series_order,
                    ),
                },
                'all_versions': {
                    'developer_totals_by_version': build_analysis_matrix_payload(
                        developer_total_by_version_matrix,
                        categories=version_categories,
                        series_order=sort_analysis_labels(developer_labels),
                    ),
                    'root_cause_by_version': build_analysis_matrix_payload(
                        root_cause_by_version_matrix,
                        categories=version_categories,
                        series_order=root_cause_series_order,
                    ),
                },
            }
        )


class DefectRichTextImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_images = request.FILES.getlist('images')
        if not uploaded_images:
            return Response({'detail': '请至少上传一张图片'}, status=status.HTTP_400_BAD_REQUEST)

        upload_results = []
        current_time = timezone.now()
        upload_directory = current_time.strftime(f'{RICH_TEXT_IMAGE_PREFIX}%Y/%m')

        for uploaded_image in uploaded_images:
            content_type = uploaded_image.content_type or ''
            if not content_type.startswith('image/'):
                return Response({'detail': f'{uploaded_image.name} 不是图片文件'}, status=status.HTTP_400_BAD_REQUEST)

            original_name = get_valid_filename(uploaded_image.name or 'image')
            _, file_extension = os.path.splitext(original_name)
            file_extension = file_extension.lower() or '.png'
            file_name = f'{uuid.uuid4().hex}{file_extension}'
            relative_path = default_storage.save(f'{upload_directory}/{file_name}', uploaded_image)

            upload_results.append({
                'name': original_name,
                'url': build_media_url(relative_path, request=request),
                'path': relative_path,
            })

        return Response({'results': upload_results}, status=status.HTTP_201_CREATED)


class DefectExcelImportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    item_label = '缺陷'
    history_create_field = 'defect'

    def get_record_type(self, request):
        return get_record_type_from_request(request)

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'detail': f'请上传{self.item_label} Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not str(uploaded_file.name or '').lower().endswith('.xlsx'):
            return Response({'detail': '仅支持 .xlsx 格式的 Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)

        project_id = request.data.get('project_id')
        version_id = request.data.get('version_id')
        if not project_id:
            return Response({'project_id': '请选择所属项目'}, status=status.HTTP_400_BAD_REQUEST)
        if not version_id:
            return Response({'version_id': '请选择关联版本'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = resolve_project_for_user(request.user, project_id)
            version = resolve_version_for_project(project, version_id)
            result = import_defects_from_excel_file(
                uploaded_file=uploaded_file,
                project=project,
                version=version,
                operator=request.user,
                record_type=self.get_record_type(request),
                history_create_field=self.history_create_field,
                update_status_metadata=update_status_metadata,
                create_history=create_history,
            )
        except serializers.ValidationError:
            raise
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if result['created_count'] <= 0:
            return Response(
                {
                    'detail': f'Excel 中没有可导入的{self.item_label}记录',
                    **result,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class DefectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    history_create_field = 'defect'
    workflow_biz_type = 'defect'
    notification_enabled = True

    def get_record_type(self):
        return get_record_type_from_request(self.request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workflow_biz_type'] = self.workflow_biz_type
        return context

    def get_queryset(self):
        return get_accessible_defects(self.request.user, record_type=self.get_record_type()).prefetch_related(
            'attachments__uploaded_by',
            'comments__author',
            'history_records__changed_by',
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return DefectCreateUpdateSerializer
        return DefectDetailSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        defect = self.get_object()
        serializer = self.get_serializer(defect, data=normalize_request_data(request), partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        operator = request.user
        frontend_base_url = resolve_frontend_base_url(request)

        previous_state = {
            'project_id': defect.project_id,
            'project_name': defect.project.name,
            'version_id': defect.version_id,
            'version_name': defect.version.name if defect.version else '',
            'title': defect.title,
            'description': defect.description,
            'problem_reason': defect.problem_reason,
            'root_cause': defect.root_cause,
            'frontend_developer': defect.frontend_developer,
            'backend_developer': defect.backend_developer,
            'priority': defect.priority,
            'severity': defect.severity,
            'status': defect.status,
            'requirement_id': defect.requirement_id,
            'modules': list(defect.modules or []),
            'related_testcases': list(defect.related_testcases or []),
            'related_testpoints': list(defect.related_testpoints or []),
            'labels': list(defect.labels or []),
            'assignees': list(defect.assignees.all()),
        }
        current_assignee_ids = [user.id for user in previous_state['assignees']]

        if 'project_id' in validated_data:
            defect.project = resolve_project_for_user(operator, validated_data['project_id'])

        if 'version_id' in validated_data:
            defect.version = resolve_version_for_project(defect.project, validated_data.get('version_id'))

        for field in [
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
        ]:
            if field in validated_data:
                if field == 'status':
                    running_instance = WorkflowInstance.objects.filter(
                        biz_type=self.workflow_biz_type,
                        biz_id=defect.id,
                        status='running',
                    ).exists()
                    if running_instance and validated_data.get(field) != defect.status:
                        raise serializers.ValidationError({'status': 'Workflow is running. Use workflow actions instead of editing status directly.'})
                setattr(defect, field, validated_data.get(field) or '')

        for field in ['modules', 'related_testcases', 'related_testpoints']:
            if field in validated_data:
                setattr(defect, field, validated_data.get(field) or [])

        if 'labels' in validated_data:
            defect.labels = normalize_labels(validated_data.get('labels', []))

        if previous_state['status'] != defect.status:
            update_status_metadata(defect, operator, defect.status)

        defect.save()

        if previous_state['description'] != defect.description:
            previous_image_paths = extract_rich_text_image_paths(previous_state['description'])
            next_image_paths = extract_rich_text_image_paths(defect.description)
            cleanup_rich_text_images(previous_image_paths - next_image_paths)

        field_changes = []
        if previous_state['project_id'] != defect.project_id:
            field_changes.append(('project', previous_state['project_name'], defect.project.name, 'update'))
        if previous_state['version_id'] != defect.version_id:
            field_changes.append(('version', previous_state['version_name'], defect.version.name if defect.version else '', 'update'))
        if previous_state['title'] != defect.title:
            field_changes.append(('title', previous_state['title'], defect.title, 'update'))
        if previous_state['description'] != defect.description:
            field_changes.append(('description', previous_state['description'], defect.description, 'update'))
        if previous_state['problem_reason'] != defect.problem_reason:
            field_changes.append(('problem_reason', previous_state['problem_reason'], defect.problem_reason, 'update'))
        if previous_state['root_cause'] != defect.root_cause:
            field_changes.append(('root_cause', previous_state['root_cause'], defect.root_cause, 'update'))
        if previous_state['frontend_developer'] != defect.frontend_developer:
            field_changes.append((
                'frontend_developer',
                previous_state['frontend_developer'],
                defect.frontend_developer,
                'update',
            ))
        if previous_state['backend_developer'] != defect.backend_developer:
            field_changes.append((
                'backend_developer',
                previous_state['backend_developer'],
                defect.backend_developer,
                'update',
            ))
        if previous_state['priority'] != defect.priority:
            field_changes.append(('priority', previous_state['priority'], defect.priority, 'update'))
        if previous_state['severity'] != defect.severity:
            field_changes.append(('severity', previous_state['severity'], defect.severity, 'update'))
        if previous_state['status'] != defect.status:
            field_changes.append(('status', previous_state['status'], defect.status, 'status'))
        if previous_state['requirement_id'] != defect.requirement_id:
            field_changes.append(('requirement_id', previous_state['requirement_id'], defect.requirement_id, 'update'))
        if previous_state['modules'] != list(defect.modules or []):
            field_changes.append((
                'modules',
                format_relation_history_items(previous_state['modules']),
                format_relation_history_items(list(defect.modules or [])),
                'update',
            ))
        if previous_state['related_testcases'] != list(defect.related_testcases or []):
            field_changes.append((
                'related_testcases',
                format_relation_history_items(previous_state['related_testcases']),
                format_relation_history_items(list(defect.related_testcases or [])),
                'update',
            ))
        if previous_state['related_testpoints'] != list(defect.related_testpoints or []):
            field_changes.append((
                'related_testpoints',
                format_relation_history_items(previous_state['related_testpoints']),
                format_relation_history_items(list(defect.related_testpoints or [])),
                'update',
            ))
        if previous_state['labels'] != list(defect.labels or []):
            field_changes.append(('labels', previous_state['labels'], list(defect.labels or []), 'update'))

        for field, from_value, to_value, action in field_changes:
            create_history(
                defect,
                changed_by=operator,
                field=field,
                action=action,
                from_value=from_value,
                to_value=to_value,
            )

        if 'assignee_ids' in validated_data:
            assignee_ids = validated_data.get('assignee_ids', [])
            user_map = get_user_map_by_ids(assignee_ids)
            next_assignees = list(user_map.values())
            previous_assignee_names = format_user_list(previous_state['assignees'])
            next_assignee_names = format_user_list(next_assignees)
            defect.assignees.set(next_assignees)
            current_assignee_ids = [user.id for user in next_assignees]
            if previous_assignee_names != next_assignee_names:
                create_history(
                    defect,
                    changed_by=operator,
                    field='assignees',
                    action='assign',
                    from_value=previous_assignee_names,
                    to_value=next_assignee_names,
                )

        if 'retain_attachment_ids' in validated_data or request.FILES.getlist('attachments'):
            retain_attachment_ids = validated_data.get('retain_attachment_ids')
            apply_attachment_changes(defect, request, operator, retain_attachment_ids=retain_attachment_ids)

        title_changed = previous_state['title'] != defect.title
        description_changed = previous_state['description'] != defect.description
        status_changed = previous_state['status'] != defect.status
        previous_assignee_ids = [user.id for user in previous_state['assignees']]
        new_assignee_ids = [user_id for user_id in current_assignee_ids if user_id not in previous_assignee_ids]

        if self.notification_enabled and (title_changed or description_changed or status_changed or new_assignee_ids):
            transaction.on_commit(
                lambda: safely_execute_notification(
                    notify_defect_updated,
                    defect.id,
                    title_changed=title_changed,
                    description_changed=description_changed,
                    status_changed=status_changed,
                    new_assignee_ids=new_assignee_ids,
                    frontend_base_url=frontend_base_url,
                )
            )

        output = DefectDetailSerializer(
            defect,
            context={'request': request, 'workflow_biz_type': self.workflow_biz_type},
        )
        return Response(output.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def perform_destroy(self, instance):
        cleanup_rich_text_images(extract_rich_text_image_paths(instance.description))
        cleanup_rich_text_images(collect_comment_rich_text_image_paths(instance.comments.all()))
        for attachment in list(instance.attachments.all()):
            clear_attachment_file(attachment)
        instance.delete()


class DefectStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    workflow_biz_type = 'defect'

    def get_record_type(self, request):
        return get_record_type_from_request(request)

    @transaction.atomic
    def post(self, request, pk):
        defect = generics.get_object_or_404(get_accessible_defects(request.user, record_type=self.get_record_type(request)), pk=pk)
        running_instance = WorkflowInstance.objects.filter(
            biz_type=self.workflow_biz_type,
            biz_id=defect.id,
            status='running',
        ).exists()
        if running_instance:
            return Response(
                {'detail': 'Workflow is running. Use workflow actions instead of direct status updates.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = DefectStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_status = serializer.validated_data['status']
        previous_status = defect.status
        frontend_base_url = resolve_frontend_base_url(request)

        if previous_status != next_status:
            defect.status = next_status
            update_status_metadata(defect, request.user, next_status)
            defect.save()
            create_history(
                defect,
                changed_by=request.user,
                field='status',
                action='status',
                from_value=previous_status,
                to_value=next_status,
            )
            transaction.on_commit(
                lambda: safely_execute_notification(
                    notify_defect_status_updated,
                    defect.id,
                    frontend_base_url=frontend_base_url,
                )
            )

        output = DefectDetailSerializer(
            defect,
            context={'request': request, 'workflow_biz_type': self.workflow_biz_type},
        )
        return Response(output.data)


class DefectAssigneeUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    workflow_biz_type = 'defect'

    def get_record_type(self, request):
        return get_record_type_from_request(request)

    @transaction.atomic
    def post(self, request, pk):
        defect = generics.get_object_or_404(get_accessible_defects(request.user, record_type=self.get_record_type(request)), pk=pk)
        serializer = DefectAssigneeUpdateSerializer(data={'assignee_ids': parse_request_list(request.data, 'assignee_ids', int) or []})
        serializer.is_valid(raise_exception=True)
        frontend_base_url = resolve_frontend_base_url(request)

        assignee_ids = serializer.validated_data.get('assignee_ids', [])
        user_map = get_user_map_by_ids(assignee_ids)
        previous_assignee_ids = list(defect.assignees.values_list('id', flat=True))
        previous_assignee_names = format_user_list(defect.assignees.all())
        next_assignee_names = format_user_list(user_map.values())
        defect.assignees.set(user_map.values())

        if previous_assignee_names != next_assignee_names:
            create_history(
                defect,
                changed_by=request.user,
                field='assignees',
                action='assign',
                from_value=previous_assignee_names,
                to_value=next_assignee_names,
            )
            new_assignee_ids = [user_id for user_id in assignee_ids if user_id not in previous_assignee_ids]
            if new_assignee_ids:
                transaction.on_commit(
                    lambda: safely_execute_notification(
                        notify_defect_assignees_updated,
                        defect.id,
                        new_assignee_ids=new_assignee_ids,
                        frontend_base_url=frontend_base_url,
                    )
                )

        output = DefectDetailSerializer(
            defect,
            context={'request': request, 'workflow_biz_type': self.workflow_biz_type},
        )
        return Response(output.data)


class DefectCommentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    history_create_field = 'comment'

    def get_record_type(self, request):
        return get_record_type_from_request(request)

    @transaction.atomic
    def post(self, request, pk):
        defect = generics.get_object_or_404(get_accessible_defects(request.user, record_type=self.get_record_type(request)), pk=pk)
        serializer = DefectCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        frontend_base_url = resolve_frontend_base_url(request)

        comment = DefectComment.objects.create(
            defect=defect,
            author=request.user,
            content=serializer.validated_data['content'],
        )
        create_history(
            defect,
            changed_by=request.user,
            field='comment',
            action='comment',
            from_value=None,
            to_value={'content': comment.content},
        )
        transaction.on_commit(
            lambda: safely_execute_notification(
                notify_defect_comment_created,
                defect.id,
                frontend_base_url=frontend_base_url,
            )
        )

        output = DefectCommentSerializer(comment, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class DefectCommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_record_type(self, request):
        return get_record_type_from_request(request)

    @transaction.atomic
    def put(self, request, pk, comment_pk):
        defect = generics.get_object_or_404(get_accessible_defects(request.user, record_type=self.get_record_type(request)), pk=pk)
        comment = generics.get_object_or_404(defect.comments.select_related('author'), pk=comment_pk)

        if comment.author_id != request.user.id:
            return Response({'detail': '仅支持评论创建人编辑该评论'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DefectCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        next_content = serializer.validated_data['content']
        previous_content = comment.content

        if previous_content != next_content:
            comment.content = next_content
            comment.save(update_fields=['content', 'updated_at'])

            previous_image_paths = extract_rich_text_image_paths(previous_content)
            next_image_paths = extract_rich_text_image_paths(next_content)
            cleanup_rich_text_images(previous_image_paths - next_image_paths)

            create_history(
                defect,
                changed_by=request.user,
                field='comment',
                action='update',
                from_value={'comment_id': comment.id, 'type': 'content_updated'},
                to_value={'comment_id': comment.id, 'type': 'content_updated'},
            )

        output = DefectCommentSerializer(comment, context={'request': request})
        return Response(output.data)

    def patch(self, request, pk, comment_pk):
        return self.put(request, pk, comment_pk)


class DefectHistoryListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DefectHistorySerializer

    def get_record_type(self):
        return get_record_type_from_request(self.request)

    def get_queryset(self):
        defect = generics.get_object_or_404(
            get_accessible_defects(self.request.user, record_type=self.get_record_type()),
            pk=self.kwargs['pk'],
        )
        return defect.history_records.select_related('changed_by').all()


class WikiDirectoryListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project')
        queryset = get_accessible_wiki_directories(request.user)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        else:
            queryset = queryset.none()

        roots = queryset.filter(parent__isnull=True)
        serializer = WikiDirectorySerializer(roots, many=True, context={'request': request})
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        serializer = WikiDirectoryCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = resolve_project_for_user(request.user, data['project_id'])
        parent = None
        if data.get('parent_id'):
            parent = get_accessible_wiki_directories(request.user).filter(
                id=data['parent_id'],
                project=project,
            ).first()
            if not parent:
                raise serializers.ValidationError({'parent_id': '父级目录不存在或不属于当前项目'})

        if WikiDirectory.objects.filter(project=project, parent=parent, name=data['name']).exists():
            raise serializers.ValidationError({'name': '同级目录下已存在同名 Wiki 目录'})

        directory = WikiDirectory.objects.create(
            project=project,
            parent=parent,
            name=data['name'],
            description=data.get('description') or '',
            sort_order=data.get('sort_order') or 0,
            created_by=request.user if request.user.is_authenticated else None,
        )
        return Response(WikiDirectorySerializer(directory, context={'request': request}).data, status=status.HTTP_201_CREATED)


class WikiDirectoryDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return get_accessible_wiki_directories(request.user).get(pk=pk)
        except WikiDirectory.DoesNotExist:
            raise NotFound('Wiki目录不存在')

    def get(self, request, pk):
        directory = self.get_object(request, pk)
        return Response(WikiDirectorySerializer(directory, context={'request': request}).data)

    @transaction.atomic
    def put(self, request, pk):
        return self.update(request, pk)

    @transaction.atomic
    def patch(self, request, pk):
        return self.update(request, pk)

    def update(self, request, pk):
        directory = self.get_object(request, pk)
        serializer = WikiDirectoryCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = directory.project
        if 'project_id' in data:
            project = resolve_project_for_user(request.user, data['project_id'])

        parent = directory.parent
        if 'parent_id' in data:
            parent = None
            if data.get('parent_id'):
                parent = get_accessible_wiki_directories(request.user).filter(
                    id=data['parent_id'],
                    project=project,
                ).first()
                if not parent:
                    raise serializers.ValidationError({'parent_id': '父级目录不存在或不属于当前项目'})
                if parent.id == directory.id or parent.id in get_wiki_directory_descendant_ids(directory):
                    raise serializers.ValidationError({'parent_id': '不能将目录移动到自身或其子目录下'})

        next_name = data.get('name', directory.name)
        if WikiDirectory.objects.filter(project=project, parent=parent, name=next_name).exclude(pk=directory.pk).exists():
            raise serializers.ValidationError({'name': '同级目录下已存在同名 Wiki 目录'})

        directory.project = project
        directory.parent = parent
        directory.name = next_name
        if 'description' in data:
            directory.description = data.get('description') or ''
        if 'sort_order' in data:
            directory.sort_order = data.get('sort_order') or 0
        directory.save()
        return Response(WikiDirectorySerializer(directory, context={'request': request}).data)

    def delete(self, request, pk):
        directory = self.get_object(request, pk)
        directory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPageMixin:
    item_label = 'Wiki'
    history_create_field = 'wiki'
    workflow_biz_type = 'defect'
    notification_enabled = False

    def get_record_type(self, *args, **kwargs):
        return Defect.RECORD_TYPE_WIKI


class WikiPageListCreateView(WikiPageMixin, DefectListCreateView):
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        directory_id = str(request.query_params.get('wiki_directory') or '').strip()
        include_children = str(request.query_params.get('include_children') or 'true').lower() != 'false'

        if directory_id:
            directory = get_accessible_wiki_directories(request.user).filter(id=directory_id).first()
            if not directory:
                queryset = queryset.none()
            else:
                directory_ids = [directory.id]
                if include_children:
                    directory_ids.extend(get_wiki_directory_descendant_ids(directory))
                matched_ids = [wiki_page.id for wiki_page in queryset if wiki_page_matches_directory(wiki_page, directory_ids)]
                queryset = queryset.filter(id__in=matched_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WikiPageDetailView(WikiPageMixin, DefectDetailView):
    pass


class TechnicalSolutionDesignMixin:
    item_label = '技术方案设计'
    history_create_field = 'technical_solution_design'
    workflow_biz_type = 'technical_solution_design'

    def get_record_type(self, *args, **kwargs):
        return Defect.RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN


class TechnicalSolutionDesignListCreateView(TechnicalSolutionDesignMixin, DefectListCreateView):
    pass


class TechnicalSolutionDesignExcelImportView(TechnicalSolutionDesignMixin, DefectExcelImportView):
    pass


class TechnicalSolutionDesignDetailView(TechnicalSolutionDesignMixin, DefectDetailView):
    pass


class TechnicalSolutionDesignStatusUpdateView(TechnicalSolutionDesignMixin, DefectStatusUpdateView):
    pass


class TechnicalSolutionDesignAssigneeUpdateView(TechnicalSolutionDesignMixin, DefectAssigneeUpdateView):
    pass


class TechnicalSolutionDesignCommentCreateView(TechnicalSolutionDesignMixin, DefectCommentCreateView):
    pass


class TechnicalSolutionDesignCommentDetailView(TechnicalSolutionDesignMixin, DefectCommentDetailView):
    pass


class TechnicalSolutionDesignHistoryListView(TechnicalSolutionDesignMixin, DefectHistoryListView):
    pass
