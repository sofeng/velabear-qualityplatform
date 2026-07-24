from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import close_old_connections, models, transaction
from django.db.models import Prefetch
from django.db.models.functions import Cast
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone
import ast
import html
import os
import io
import base64
import binascii
import platform
import copy
import shutil
import subprocess
import tempfile
import threading
import uuid
import json
import zipfile
import time
import hashlib
import secrets
import re
import yaml
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit
from apps.core.branding import PLATFORM_BRAND_NAME
from apps.users.group_utils import normalize_existing_group_name
from apps.users.serializers import UserSerializer
from .models import (
    DevSelfTestRecord,
    ManualTestCaseCategory,
    ManualTestCaseMindmap,
    PlaywrightAutomationScript,
    PlaywrightAutomationScriptVersion,
    PlaywrightRecordingSession,
    PlaywrightRecordingStep,
    TestCase,
    TestCaseAttachment,
    TestCaseComment,
    TestCaseStep,
    VisualFlow,
    VisualFlowExecution,
    VisualFlowExecutionStep,
)
from .serializers import (
    TestCaseSerializer, TestCaseCreateSerializer, TestCaseUpdateSerializer,
    ManualTestCaseMindmapSerializer, ManualTestCaseMindmapCreateSerializer, ManualTestCaseMindmapUpdateSerializer,
    ManualTestCaseNodeSerializer, ManualTestCaseCategorySerializer, ManualTestCaseCategoryCreateSerializer,
    ManualTestCaseCategoryUpdateSerializer,
    normalize_node_priority,
    normalize_node_status,
    user_can_see_dev_self_test_record,
)
from .dev_self_test_serializer import (
    DevSelfTestAuditSerializer,
    DevSelfTestDetailSerializer,
    DevSelfTestSerializer,
    DevSelfTestUpdateSerializer,
)
from .recording_serializers import (
    PlaywrightAutomationScriptSerializer,
    PlaywrightAutomationScriptVersionSerializer,
    PlaywrightRecordingSessionSerializer,
    PlaywrightRecordingStepSerializer,
    VisualFlowExecutionSerializer,
    VisualFlowSerializer,
)
from .snapshot_sanitizer import (
    normalize_snapshot_inline_text,
    sanitize_recording_payload,
    sanitize_snapshot_content,
)
from .playwright_recorder import (
    DOM_SNAPSHOT_SCRIPT,
    RECORDING_SCRIPT,
    RecordingStartError,
    cleanup_stale_recording_sessions,
    get_active_recording_ids,
    get_recorder_max_sessions_config,
    get_recorder_xvfb_screen_spec,
    rewrite_localhost_target_url_for_recorder,
    normalize_browser_type,
    normalize_target_url,
    set_recorder_max_sessions,
    start_recording_session,
    stop_recording_session,
)
from .mindmap_node_utils import (
    get_mindmap_node_native_id,
    iter_mindmap_target_nodes,
    parse_public_node_id,
    resolve_public_node_descriptor,
)
from .mindmap_category_matching import match_mindmap_modules_to_categories
from .xmind_requirement_import import (
    XMindImportError,
    parse_uploaded_xmind,
    parse_uploaded_xmind_category_tree,
)
from types import SimpleNamespace

from apps.core.plaintext_secrets import decrypt_or_repair_secret
from apps.projects.models import Project
from apps.versions.models import Version


def resolve_manual_category(project, category_id):
    if category_id in (None, ''):
        return None
    return ManualTestCaseCategory.objects.filter(project=project, id=category_id).first()


def extract_requirement_keys_from_mindmap(mindmap_data):
    """
    从脑图数据中提取需求类型节点的需求编号

    遍历脑图的所有节点，找到nodeType为'requirement'的节点，
    从节点文本中提取SYSWIN-格式的需求编号

    返回: list of str - 需求编号列表
    """
    import re

    requirement_keys = []
    pattern = r'(SYSWIN-\d+)'

    def traverse_node(node):
        if not node or not isinstance(node, dict):
            return

        # 检查当前节点
        node_data = node.get('data', {})
        node_type = node_data.get('nodeType')
        node_text = node_data.get('text', '')

        if node_type == 'requirement' and node_text:
            # 尝试从节点文本中提取需求编号
            match = re.search(pattern, node_text)
            if match:
                requirement_key = match.group(1)
                if requirement_key not in requirement_keys:
                    requirement_keys.append(requirement_key)

        # 递归处理子节点
        children = node.get('children', [])
        for child in children:
            traverse_node(child)

    # 从root开始遍历
    root = mindmap_data.get('root')
    if root:
        traverse_node(root)

    return requirement_keys


def query_jira_requirement_by_key(requirement_key):
    """
    根据需求编号查询JIRA需求数据

    参数:
        requirement_key: str - 需求编号（如SYSWIN-123）

    返回:
        dict - 包含组别、前端开发、后端开发的字段，如果未找到则返回None
        {
            'group_name': str,
            'frontend_developer_name': str,
            'backend_developer_name': str
        }
    """
    from apps.quality_analysis.models import JiraRequirementRecord

    try:
        # 查询JIRA需求记录（按更新时间倒序，获取最新的记录）
        jira_record = JiraRequirementRecord.objects.filter(
            issue_key=requirement_key
        ).order_by('-updated_at').first()

        if not jira_record:
            return None

        # 提取组别
        group_name = jira_record.group_name or ''

        # 优先使用需求记录上的专用字段，兼容历史数据再回退到 raw_fields
        raw_fields = jira_record.raw_fields or {}

        # customfield_10743: 前端开发
        frontend_developer_name = (
            jira_record.frontend_developer or
            raw_fields.get('customfield_10743', '')
        )

        # customfield_10741: 后端开发
        backend_developer_name = (
            jira_record.backend_developer or
            raw_fields.get('customfield_10741', '') or
            jira_record.handler or  # handler字段作为后备
            ''
        )

        return {
            'group_name': group_name,
            'frontend_developer_name': frontend_developer_name,
            'backend_developer_name': backend_developer_name,
        }
    except Exception as e:
        # 查询失败，返回None
        return None


def match_user_by_name(name):
    """
    根据姓名匹配用户

    尝试按以下顺序匹配：
    1. username完全匹配
    2. first_name或last_name匹配
    3. first_name+last_name组合匹配（检查full_name属性）

    参数:
        name: str - 用户姓名

    返回:
        User对象或None
    """
    from apps.users.models import User

    if not name or not isinstance(name, str):
        return None

    name = name.strip()
    if not name:
        return None

    # 尝试按username匹配
    user = User.objects.filter(username=name).first()
    if user:
        return user

    # 尝试按first_name或last_name匹配
    user = User.objects.filter(
        models.Q(first_name=name) | models.Q(last_name=name)
    ).first()
    if user:
        return user

    # 尝试按first_name+last_name组合匹配
    # 因为full_name是@property，不能在数据库查询中使用
    # 需要查询所有用户并在Python层面检查
    # 为了提高效率，只检查有first_name或last_name的用户
    candidates = User.objects.filter(
        models.Q(first_name__isnull=False) | models.Q(last_name__isnull=False)
    ).exclude(
        models.Q(first_name='') & models.Q(last_name='')
    )

    for user in candidates:
        if user.full_name == name:
            return user

    return None


def get_visible_manual_workspace_projects():
    return Project.objects.all().distinct()


TESTING_MINDMAP_SCOPE = ManualTestCaseMindmap.SCOPE_TESTING
REQUIREMENT_ANALYSIS_MINDMAP_SCOPE = ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS
MINDMAP_SCOPE_VALUES = {
    TESTING_MINDMAP_SCOPE,
    REQUIREMENT_ANALYSIS_MINDMAP_SCOPE,
}


def normalize_mindmap_scope(value, default=TESTING_MINDMAP_SCOPE):
    normalized = str(value or '').strip()
    return normalized if normalized in MINDMAP_SCOPE_VALUES else default


def get_requested_mindmap_scope(request, default=TESTING_MINDMAP_SCOPE):
    value = None
    if request is not None:
        value = request.query_params.get('mindmap_scope')
        if value in (None, '') and hasattr(request, 'data'):
            value = request.data.get('mindmap_scope')
    return normalize_mindmap_scope(value, default)


class ManualTestCasePagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_page_window(request, default_page_size=20, max_page_size=200):
    params = request.query_params
    has_page = 'page' in params or 'page_size' in params
    has_limit = 'limit' in params
    if not has_page and not has_limit:
        return None

    try:
        page = max(1, int(params.get('page') or 1))
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(params.get('page_size') or params.get('limit') or default_page_size)
    except (TypeError, ValueError):
        page_size = default_page_size
    page_size = max(1, min(page_size, max_page_size))
    offset = (page - 1) * page_size
    return {
        'page': page,
        'page_size': page_size,
        'offset': offset,
        'limit': offset + page_size,
    }


def paginate_queryset(request, queryset, default_page_size=20, max_page_size=200):
    total = queryset.count()
    window = get_page_window(request, default_page_size=default_page_size, max_page_size=max_page_size)
    if not window:
        return queryset, {
            'count': total,
            'page': 1,
            'page_size': total,
        }
    return queryset[window['offset']:window['limit']], {
        'count': total,
        'page': window['page'],
        'page_size': window['page_size'],
    }


def paginate_list(request, items, default_page_size=20, max_page_size=200):
    total = len(items)
    window = get_page_window(request, default_page_size=default_page_size, max_page_size=max_page_size)
    if not window:
        return items, {
            'count': total,
            'page': 1,
            'page_size': total,
        }
    return items[window['offset']:window['limit']], {
        'count': total,
        'page': window['page'],
        'page_size': window['page_size'],
    }


class TestCaseListCreateView(generics.ListCreateAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'test_type', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestCaseCreateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试用例
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        return TestCase.objects.filter(project__in=accessible_projects)
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_visible_manual_workspace_projects()
    
    def perform_create(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        # 获取用户有权限的项目
        accessible_projects = self.get_user_accessible_projects(user)
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                project = accessible_projects.first()
                if not project:
                    # 如果用户没有任何项目，创建默认项目
                    project = Project.objects.create(
                        name="默认项目",
                        owner=user,
                        description='系统自动创建的默认项目'
                    )
        else:
            # 没有指定项目，使用第一个可访问的项目
            project = accessible_projects.first()
            if not project:
                # 如果用户没有任何项目，创建默认项目
                project = Project.objects.create(
                    name="默认项目",
                    owner=user,
                    description='系统自动创建的默认项目'
                )
        
        serializer.save(author=user, project=project)

class TestCaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TestCaseUpdateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        return TestCase.objects.filter(project__in=accessible_projects)
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_visible_manual_workspace_projects()
    
    def perform_update(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            accessible_projects = self.get_user_accessible_projects(user)
            try:
                project = accessible_projects.get(id=project_id)
                serializer.save(project=project)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，保持原项目不变
                serializer.save()
        else:
            # 没有指定项目，保持原项目不变
            serializer.save()


class ManualTestCaseMindmapListCreateView(generics.ListCreateAPIView):
    """手工用例脑图列表和创建"""
    queryset = ManualTestCaseMindmap.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ManualTestCasePagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'category']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ManualTestCaseMindmapCreateSerializer
        return ManualTestCaseMindmapSerializer

    def _normalize_module_label(self, value):
        return str(value or '').strip().replace(' ', '').lower()

    def _mindmap_has_matching_module(self, node, target_label):
        if not isinstance(node, dict) or not target_label:
            return False

        data = node.get('data')
        if isinstance(data, dict):
            node_text = self._normalize_module_label(data.get('text'))
            if data.get('nodeType') == 'module' and node_text == target_label:
                return True

        for child in node.get('children') or []:
            if self._mindmap_has_matching_module(child, target_label):
                return True

        return False

    def _filter_by_linked_requirement_text(self, queryset, field_name, keyword):
        normalized_keyword = str(keyword or '').strip().casefold()
        if not normalized_keyword:
            return queryset

        from apps.quality_analysis.models import JiraRequirementRecord

        requirement_cache = {}
        matched_ids = []
        for mindmap_id, requirement_key in queryset.exclude(requirement_key='').values_list('id', 'requirement_key'):
            normalized_key = str(requirement_key or '').strip()
            if not normalized_key:
                continue

            if normalized_key not in requirement_cache:
                requirement_cache[normalized_key] = (
                    JiraRequirementRecord.objects
                    .filter(issue_key=normalized_key)
                    .order_by('-updated_at')
                    .first()
                )

            requirement = requirement_cache[normalized_key]
            requirement_value = str(getattr(requirement, field_name, '') or '').strip().casefold() if requirement else ''
            if normalized_keyword in requirement_value:
                matched_ids.append(mindmap_id)

        return queryset.filter(id__in=matched_ids)

    def get_queryset(self):
        # 只显示用户有权限访问的项目的脑图
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        queryset = ManualTestCaseMindmap.objects.filter(
            project__in=accessible_projects,
            mindmap_scope=get_requested_mindmap_scope(self.request),
        ).select_related('author', 'executor')

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        selected_category_id = str(self.request.query_params.get('selected_category_id') or '').strip()
        selected_category_name = self._normalize_module_label(
            self.request.query_params.get('selected_category_name')
        )
        category_id = self.request.query_params.get('category')
        if category_id not in (None, ''):
            queryset = queryset.filter(category_id=category_id)

        # 版本过滤
        version_id = self.request.query_params.get('version')
        if version_id and version_id != 'all':
            queryset = queryset.filter(version_id=version_id)

        version_name = (self.request.query_params.get('version_name') or '').strip()
        if version_name:
            queryset = queryset.filter(version__name__icontains=version_name)

        updated_at = (self.request.query_params.get('updated_at') or '').strip()
        updated_at_start = (self.request.query_params.get('updated_at_start') or '').strip()
        updated_at_end = (self.request.query_params.get('updated_at_end') or '').strip()
        created_at = (self.request.query_params.get('created_at') or '').strip()
        created_at_start = (self.request.query_params.get('created_at_start') or '').strip()
        created_at_end = (self.request.query_params.get('created_at_end') or '').strip()
        if created_at:
            queryset = queryset.filter(created_at__date=created_at)
        if created_at_start:
            queryset = queryset.filter(created_at__date__gte=created_at_start)
        if created_at_end:
            queryset = queryset.filter(created_at__date__lte=created_at_end)
        if updated_at:
            queryset = queryset.filter(updated_at__date=updated_at)
        if updated_at_start:
            queryset = queryset.filter(updated_at__date__gte=updated_at_start)
        if updated_at_end:
            queryset = queryset.filter(updated_at__date__lte=updated_at_end)

        # 创建人过滤
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        author_name = (self.request.query_params.get('author_name') or '').strip()
        if author_name:
            queryset = queryset.filter(
                models.Q(author__username__icontains=author_name) |
                models.Q(author__first_name__icontains=author_name) |
                models.Q(author__last_name__icontains=author_name) |
                models.Q(author__email__icontains=author_name)
            )

        executor_id = self.request.query_params.get('executor')
        if executor_id:
            queryset = queryset.filter(executor_id=executor_id)

        executor_name = (self.request.query_params.get('executor_name') or '').strip()
        if executor_name:
            queryset = queryset.filter(
                models.Q(executor__username__icontains=executor_name) |
                models.Q(executor__first_name__icontains=executor_name) |
                models.Q(executor__last_name__icontains=executor_name) |
                models.Q(executor__email__icontains=executor_name)
            )

        mindmap_name = (self.request.query_params.get('mindmap_name') or '').strip()
        if mindmap_name:
            queryset = queryset.filter(name__icontains=mindmap_name)

        requirement_key = (self.request.query_params.get('requirement_key') or '').strip()
        if requirement_key:
            queryset = queryset.filter(requirement_key__icontains=requirement_key)

        requirement_title = (self.request.query_params.get('requirement_title') or '').strip()
        if requirement_title:
            queryset = queryset.filter(requirement_title__icontains=requirement_title)

        requirement_keyword = (self.request.query_params.get('requirement_keyword') or '').strip()
        if requirement_keyword:
            queryset = queryset.filter(
                models.Q(requirement_key__icontains=requirement_keyword) |
                models.Q(requirement_title__icontains=requirement_keyword)
            )

        mindmap_id = (self.request.query_params.get('mindmap_id') or '').strip()
        if mindmap_id:
            try:
                queryset = queryset.filter(id=int(mindmap_id))
            except (TypeError, ValueError):
                queryset = queryset.none()

        responsibility_group = (self.request.query_params.get('responsibility_group') or '').strip()
        if responsibility_group:
            queryset = self._filter_by_linked_requirement_text(queryset, 'group_name', responsibility_group)

        requirement_module = (self.request.query_params.get('module') or '').strip()
        if requirement_module:
            queryset = self._filter_by_linked_requirement_text(queryset, 'module', requirement_module)

        frontend_name = (self.request.query_params.get('frontend_name') or '').strip()
        if frontend_name:
            queryset = self._filter_by_linked_requirement_text(queryset, 'frontend_developer', frontend_name)

        backend_name = (self.request.query_params.get('backend_name') or '').strip()
        if backend_name:
            queryset = self._filter_by_linked_requirement_text(queryset, 'backend_developer', backend_name)

        search_keyword = (self.request.query_params.get('search') or '').strip()
        if search_keyword:
            # 同时支持原始关键词和去除空格后的关键词搜索，以便更好地匹配带空格的脑图名称
            keyword_without_spaces = search_keyword.replace(' ', '')

            queryset = queryset.annotate(
                mindmap_data_text=Cast('mindmap_data', output_field=models.TextField())
            ).filter(
                models.Q(name__icontains=search_keyword) |
                models.Q(name__icontains=keyword_without_spaces) |
                models.Q(description__icontains=search_keyword) |
                models.Q(description__icontains=keyword_without_spaces) |
                models.Q(mindmap_data_text__icontains=search_keyword)
            )

        if selected_category_id or selected_category_name:
            matched_ids = []
            for mindmap in queryset:
                if selected_category_id and str(mindmap.category_id or '') == selected_category_id:
                    matched_ids.append(mindmap.id)
                    continue

                if selected_category_name and self._mindmap_has_matching_module(
                    (mindmap.mindmap_data or {}).get('root'),
                    selected_category_name,
                ):
                    matched_ids.append(mindmap.id)

            queryset = queryset.filter(id__in=matched_ids)

        return queryset

    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_visible_manual_workspace_projects()

    def _resolve_create_project(self, user, project_id):
        accessible_projects = self.get_user_accessible_projects(user)

        if project_id:
            try:
                return accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                project = accessible_projects.first()
                if project:
                    return project

        project = accessible_projects.first()
        if project:
            return project

        return Project.objects.create(
            name="默认项目",
            owner=user,
            description='系统自动创建的默认项目'
        )

    def _parse_optional_int(self, value):
        if value in (None, '', 'null', 'undefined'):
            return None

        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('请求参数包含无效的整数值') from exc

    def _build_mindmap_create_kwargs(self, request, user, project):
        category_id = self._parse_optional_int(request.data.get('category_id'))
        version_id = self._parse_optional_int(request.data.get('version_id'))
        frontend_developer_id = self._parse_optional_int(request.data.get('frontend_developer_id'))
        backend_developer_id = self._parse_optional_int(request.data.get('backend_developer_id'))
        try:
            responsibility_group = normalize_existing_group_name(request.data.get('responsibility_group'))
        except ValidationError as exc:
            raise ValidationError({'responsibility_group': exc.detail})

        mindmap_scope = get_requested_mindmap_scope(request)
        save_kwargs = {
            'author': user,
            'executor': user,
            'project': project,
            'category': resolve_manual_category(project, category_id) if mindmap_scope == TESTING_MINDMAP_SCOPE else None,
            'responsibility_group': responsibility_group,
            'url': (request.data.get('url') or '').strip(),
            'mindmap_scope': mindmap_scope,
        }

        if version_id:
            from apps.versions.models import Version
            try:
                version = Version.objects.get(id=version_id)
                save_kwargs['version'] = version
            except Version.DoesNotExist:
                pass

        if frontend_developer_id:
            from apps.users.models import User
            try:
                frontend_dev = User.objects.get(id=frontend_developer_id)
                save_kwargs['frontend_developer'] = frontend_dev
            except User.DoesNotExist:
                pass

        if backend_developer_id:
            from apps.users.models import User
            try:
                backend_dev = User.objects.get(id=backend_developer_id)
                save_kwargs['backend_developer'] = backend_dev
            except User.DoesNotExist:
                pass

        return save_kwargs

    def _build_xmind_description(self, request, *, file_name, root_title, split_mode):
        user_description = (request.data.get('description') or '').strip()
        if user_description:
            return user_description

        if split_mode:
            return f'由 XMind 文件《{file_name}》按需求节点拆分创建；原始根节点：{root_title}'

        return f'由 XMind 文件《{file_name}》导入创建'

    def _delete_existing_xmind_requirement_mindmaps(self, *, project, requirement_items, mindmap_scope):
        requirement_keys = {
            str(item.jira_key).strip().upper()
            for item in requirement_items
            if str(item.jira_key or '').strip()
        }
        if not requirement_keys:
            return

        ManualTestCaseMindmap.objects.filter(
            project=project,
            mindmap_scope=mindmap_scope,
            requirement_key__in=requirement_keys,
        ).delete()

    def _create_from_xmind(self, request, *, xmind_file):
        user = request.user
        project_id = self._parse_optional_int(request.data.get('project_id'))
        project = self._resolve_create_project(user, project_id)

        try:
            parsed_xmind = parse_uploaded_xmind(xmind_file, project=project)
        except XMindImportError as exc:
            raise ValidationError({'xmind_file': [str(exc)]}) from exc

        save_kwargs = self._build_mindmap_create_kwargs(request, user, project)
        created_records = []
        shared_description = self._build_xmind_description(
            request,
            file_name=getattr(xmind_file, 'name', '上传脑图.xmind'),
            root_title=parsed_xmind.root_title,
            split_mode=parsed_xmind.mode == 'split_requirements',
        )

        with transaction.atomic():
            self._delete_existing_xmind_requirement_mindmaps(
                project=project,
                requirement_items=parsed_xmind.requirement_items,
                mindmap_scope=save_kwargs.get('mindmap_scope', TESTING_MINDMAP_SCOPE),
            )
            for item in parsed_xmind.requirement_items:
                matched_mindmap_data, _match_summary = match_mindmap_modules_to_categories(
                    project,
                    item.mindmap_data,
                )
                # 准备创建参数，直接使用已经提取好的需求编号和标题
                create_kwargs = {
                    'name': item.name,
                    'description': shared_description,
                    'mindmap_data': matched_mindmap_data,
                    'requirement_key': item.jira_key,  # 直接使用XMind解析时提取的JIRA编号
                    'requirement_title': item.requirement_title,  # 直接使用XMind解析时提取的需求标题
                    **save_kwargs,
                }

                # 自动从JIRA需求数据中填充组别、前端开发、后端开发字段
                if item.jira_key:
                    jira_data = query_jira_requirement_by_key(item.jira_key)
                    if jira_data:
                        # 填充组别
                        if jira_data.get('group_name'):
                            create_kwargs['responsibility_group'] = jira_data['group_name']

                        # 填充前端开发
                        frontend_name = jira_data.get('frontend_developer_name')
                        if frontend_name:
                            frontend_user = match_user_by_name(frontend_name)
                            if frontend_user:
                                create_kwargs['frontend_developer'] = frontend_user

                        # 填充后端开发
                        backend_name = jira_data.get('backend_developer_name')
                        if backend_name:
                            backend_user = match_user_by_name(backend_name)
                            if backend_user:
                                create_kwargs['backend_developer'] = backend_user

                # 创建脑图记录
                created_record = ManualTestCaseMindmap.objects.create(**create_kwargs)
                created_records.append(created_record)

        serializer = ManualTestCaseMindmapSerializer(
            created_records,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response({
            'import_mode': parsed_xmind.mode,
            'root_title': parsed_xmind.root_title,
            'created_count': len(created_records),
            'created_records': serializer.data,
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """重写list方法，在返回分页数据的同时，返回当前筛选条件下的所有创建人列表"""
        queryset = self.filter_queryset(self.get_queryset())

        # 获取当前筛选条件下的所有创建人（去重）
        from apps.users.models import User
        creator_ids = queryset.values_list('author_id', flat=True).distinct()
        creators_qs = User.objects.filter(id__in=creator_ids)

        # 构建创建人列表，包含完整的用户信息
        creators = []
        for user in creators_qs:
            creators.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'full_name': user.full_name  # 使用User模型的full_name属性
            })

        # 分页处理
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            # 在响应中添加创建人列表
            response.data['creators'] = creators
            return response

        serializer = self.get_serializer(queryset, many=True)
        from rest_framework.response import Response
        return Response({
            'results': serializer.data,
            'creators': creators
        })

    def create(self, request, *args, **kwargs):
        xmind_file = request.FILES.get('xmind_file')
        if xmind_file is not None:
            return self._create_from_xmind(request, xmind_file=xmind_file)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        project_id = self._parse_optional_int(self.request.data.get('project_id'))
        project = self._resolve_create_project(user, project_id)
        save_kwargs = self._build_mindmap_create_kwargs(self.request, user, project)
        mindmap_data = serializer.validated_data.get('mindmap_data')
        if isinstance(mindmap_data, dict):
            save_kwargs['mindmap_data'], _match_summary = match_mindmap_modules_to_categories(
                project,
                mindmap_data,
            )
        serializer.save(**save_kwargs)


class ManualTestCaseMindmapDetailView(generics.RetrieveUpdateDestroyAPIView):
    """手工用例脑图详情、更新和删除"""
    queryset = ManualTestCaseMindmap.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ManualTestCaseMindmapUpdateSerializer
        return ManualTestCaseMindmapSerializer

    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        queryset = ManualTestCaseMindmap.objects.filter(project__in=accessible_projects).select_related('author', 'executor')

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        category_id = self.request.query_params.get('category')
        if category_id not in (None, ''):
            queryset = queryset.filter(category_id=category_id)

        return queryset

    def perform_update(self, serializer):
        save_kwargs = {}

        # 处理目录
        if 'category_id' in self.request.data:
            category_id = self.request.data.get('category_id')
            save_kwargs['category'] = resolve_manual_category(serializer.instance.project, category_id)

        # 处理版本
        if 'version_id' in self.request.data:
            version_id = self.request.data.get('version_id')
            if version_id:
                from apps.versions.models import Version
                try:
                    version = Version.objects.get(id=version_id)
                    save_kwargs['version'] = version
                except Version.DoesNotExist:
                    pass
            else:
                save_kwargs['version'] = None

        # 处理前端开发人员
        if 'frontend_developer_id' in self.request.data:
            frontend_developer_id = self.request.data.get('frontend_developer_id')
            if frontend_developer_id:
                from apps.users.models import User
                try:
                    frontend_dev = User.objects.get(id=frontend_developer_id)
                    save_kwargs['frontend_developer'] = frontend_dev
                except User.DoesNotExist:
                    pass
            else:
                save_kwargs['frontend_developer'] = None

        # 处理后端开发人员
        if 'backend_developer_id' in self.request.data:
            backend_developer_id = self.request.data.get('backend_developer_id')
            if backend_developer_id:
                from apps.users.models import User
                try:
                    backend_dev = User.objects.get(id=backend_developer_id)
                    save_kwargs['backend_developer'] = backend_dev
                except User.DoesNotExist:
                    pass
            else:
                save_kwargs['backend_developer'] = None

        mindmap_data = serializer.validated_data.get('mindmap_data')
        if isinstance(mindmap_data, dict):
            save_kwargs['mindmap_data'], _match_summary = match_mindmap_modules_to_categories(
                serializer.instance.project,
                mindmap_data,
            )

        serializer.save(**save_kwargs)


class ManualTestCaseNodeListView(generics.GenericAPIView):
    """手工用例脑图节点平铺列表"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ManualTestCaseNodeSerializer
    pagination_class = ManualTestCasePagination

    def _normalize_path_segments(self, value):
        return [
            str(segment).strip().lower()
            for segment in str(value or '').split('/')
            if str(segment).strip()
        ]

    def _matches_selected_category(self, item, *, request):
        selected_category_id = str(request.query_params.get('selected_category_id') or '').strip()
        selected_category_path = request.query_params.get('selected_category_path')
        selected_path_segments = self._normalize_path_segments(selected_category_path)

        if not selected_category_id and not selected_path_segments:
            return True

        if selected_category_id and str(item.get('category_id') or '') == selected_category_id:
            return True

        if not selected_path_segments:
            return False

        module_path_segments = self._normalize_path_segments(item.get('module_path'))
        if len(module_path_segments) < len(selected_path_segments):
            return False

        return module_path_segments[:len(selected_path_segments)] == selected_path_segments

    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        queryset = ManualTestCaseMindmap.objects.filter(
            project__in=accessible_projects,
            mindmap_scope=TESTING_MINDMAP_SCOPE,
        ).order_by('-updated_at')

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        category_id = self.request.query_params.get('category')
        if category_id not in (None, ''):
            queryset = queryset.filter(category_id=category_id)

        # 版本过滤
        version_id = self.request.query_params.get('version')
        if version_id and version_id != 'all':
            queryset = queryset.filter(version_id=version_id)

        mindmap_id = (self.request.query_params.get('mindmap_id') or '').strip()
        if mindmap_id:
            try:
                queryset = queryset.filter(id=int(mindmap_id))
            except (TypeError, ValueError):
                return queryset.none()

        # 脑图名称过滤
        mindmap_name = self.request.query_params.get('mindmap_name')
        if mindmap_name:
            queryset = queryset.filter(name__icontains=mindmap_name)

        # 责任小组过滤
        responsibility_group = self.request.query_params.get('responsibility_group')
        if responsibility_group:
            queryset = queryset.filter(responsibility_group__icontains=responsibility_group)

        # 创建人过滤
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author_id=author)

        return queryset

    def _build_dev_self_test_record_map(self, mindmap):
        return {
            str(record.node_id): record
            for record in DevSelfTestRecord.objects.filter(mindmap=mindmap)
        }

    def _resolve_self_test_fields(self, *, descriptor, data, record_map, user):
        if normalize_node_priority(data.get('priority')) != 1:
            return {
                'is_dev_self_test': False,
                'self_test_status': '',
                'self_test_audit_status': '',
            }

        aliases = {
            str(descriptor.get('public_id') or '').strip(),
            str(descriptor.get('node_id') or '').strip(),
        }
        aliases.discard('')
        record = next((record_map.get(alias) for alias in aliases if record_map.get(alias)), None)
        status_value = (
            record.status
            if user_can_see_dev_self_test_record(user, record)
            else data.get('status')
        )

        return {
            'is_dev_self_test': True,
            'self_test_status': normalize_node_status(status_value),
            'self_test_audit_status': str(record.audit_status or '') if record else '',
        }

    @staticmethod
    def _resolve_review_fields(data):
        empty_fields = {
            'review_opinion': '',
            'reviewer_id': None,
            'reviewer_name': '',
            'review_time': '',
            'review_status': '',
        }

        if data.get('nodeType') != 'testpoint':
            return empty_fields

        review_opinion = str(data.get('reviewOpinion') or '').strip()
        if not review_opinion:
            return empty_fields

        reviewer_id = None
        raw_reviewer_id = data.get('reviewerId')
        if raw_reviewer_id not in (None, ''):
            try:
                reviewer_id = int(raw_reviewer_id)
            except (TypeError, ValueError):
                reviewer_id = None

        review_status = str(data.get('reviewStatus') or '').strip()
        if review_status not in {'未处理', '已处理'}:
            review_status = '未处理'

        return {
            'review_opinion': review_opinion,
            'reviewer_id': reviewer_id,
            'reviewer_name': str(data.get('reviewerName') or '').strip(),
            'review_time': str(data.get('reviewTime') or '').strip(),
            'review_status': review_status,
        }

    def _collect_nodes(self, node, *, target_type, mindmap, search_text, nodes, user=None):
        record_map = self._build_dev_self_test_record_map(mindmap) if target_type == 'testpoint' else {}
        for descriptor in iter_mindmap_target_nodes(
            node,
            mindmap_id=mindmap.id,
            target_type=target_type,
        ):
            data = descriptor.get('data') or {}
            text = descriptor.get('node_text') or ''
            current_path = descriptor.get('path_parts') or ([text] if text else [])
            module_parts = [part for part in str(descriptor.get('module_path') or '').split(' / ') if part]
            current_module_parts = list(module_parts)
            path_parts = current_path[:-1]
            node = descriptor.get('node') or {}

            if data.get('nodeType') == target_type:
                tags = data.get('tags')
                if not isinstance(tags, list):
                    tags = []

                item = {
                    'id': descriptor['public_id'],
                    'mindmap_id': mindmap.id,
                    'category_id': mindmap.category_id,
                    'mindmap_name': mindmap.name,
                    'version_name': mindmap.version.name if getattr(mindmap, 'version', None) else '',
                    'node_text': text or '未命名节点',
                    'node_type': target_type,
                    'case_id': str(data.get('caseId') or ''),
                    'priority': data.get('priority'),
                    'status': str(data.get('status') or ''),
                    **self._resolve_self_test_fields(
                        descriptor=descriptor,
                        data=data,
                        record_map=record_map,
                        user=user,
                    ),
                    **self._resolve_review_fields(data),
                    'responsibility_group': mindmap.responsibility_group or '',
                    'requirement_key': mindmap.requirement_key or '',
                    'requirement_title': mindmap.requirement_title or '',
                    'tags': [str(tag) for tag in tags if tag],
                    'path': ' / '.join(current_path),
                    'module_path': ' / '.join(
                        current_module_parts if data.get('nodeType') == 'module' else module_parts
                    ),
                    'parent_text': path_parts[-1] if path_parts else '',
                    'author': mindmap.author,
                    'created_at': mindmap.created_at,
                    'updated_at': mindmap.updated_at,
                }

                if search_text:
                    search_blob = ' '.join([
                        mindmap.name or '',
                        mindmap.description or '',
                        item['node_text'],
                        item['case_id'],
                        item['path'],
                        item['module_path'],
                        item['parent_text'],
                        item['requirement_key'],
                        item['requirement_title'],
                        item['review_opinion'],
                        item['reviewer_name'],
                        item['review_status'],
                        ' '.join(item['tags']),
                    ]).lower()
                    if search_text not in search_blob:
                        continue

                nodes.append(item)

    def _matches_filters(self, item, *, node_type, request, include_status=True):
        if node_type == 'module':
            return True

        if node_type in {'case', 'testpoint'} and not self._matches_selected_category(item, request=request):
            return False

        if node_type == 'case':
            priority = request.query_params.get('priority')
            status_value = request.query_params.get('status') if include_status else ''
            requirement_key = (request.query_params.get('requirement_key') or '').strip().lower()
            requirement_title = (request.query_params.get('requirement_title') or '').strip().lower()

            if priority not in (None, '') and str(item.get('priority')) != str(priority):
                return False
            if status_value and item.get('status') != status_value:
                return False
            if requirement_key and requirement_key not in (item.get('requirement_key') or '').lower():
                return False
            if requirement_title and requirement_title not in (item.get('requirement_title') or '').lower():
                return False

        if node_type == 'testpoint':
            mindmap_name = (request.query_params.get('mindmap_name') or '').strip().lower()
            requirement_key = (request.query_params.get('requirement_key') or '').strip().lower()
            requirement_title = (request.query_params.get('requirement_title') or '').strip().lower()
            tag = (request.query_params.get('tag') or '').strip().lower()
            status_value = request.query_params.get('status') if include_status else ''

            if mindmap_name and mindmap_name not in (item.get('mindmap_name') or '').lower():
                return False
            if requirement_key and requirement_key not in (item.get('requirement_key') or '').lower():
                return False
            if requirement_title and requirement_title not in (item.get('requirement_title') or '').lower():
                return False
            if tag:
                tags = [str(current_tag).lower() for current_tag in (item.get('tags') or [])]
                if tag not in tags:
                    return False
            if status_value and item.get('status') != status_value:
                return False

        return True

    @staticmethod
    def _collect_statuses(items):
        statuses = []
        seen_statuses = set()

        for item in items:
            status_value = str(item.get('status') or '').strip()
            if not status_value or status_value in seen_statuses:
                continue
            seen_statuses.add(status_value)
            statuses.append(status_value)

        return statuses

    def get(self, request, *args, **kwargs):
        node_type = request.query_params.get('node_type')
        if node_type not in {'module', 'case', 'testpoint'}:
            return Response({'detail': 'node_type 仅支持 case 或 testpoint'}, status=status.HTTP_400_BAD_REQUEST)

        search_text = (request.query_params.get('search') or '').strip().lower()
        nodes = []

        queryset = self.get_queryset()

        for mindmap in queryset:
            root = (mindmap.mindmap_data or {}).get('root')
            self._collect_nodes(
                root,
                target_type=node_type,
                mindmap=mindmap,
                search_text=search_text,
                nodes=nodes,
                user=request.user,
            )

        base_nodes = [
            item for item in nodes
            if self._matches_filters(
                item,
                node_type=node_type,
                request=request,
                include_status=node_type != 'testpoint',
            )
        ]
        statuses = self._collect_statuses(base_nodes) if node_type == 'testpoint' else []
        nodes = [
            item for item in base_nodes
            if self._matches_filters(item, node_type=node_type, request=request)
        ]

        creators = []
        seen_creator_ids = set()
        for item in nodes:
            author = item.get('author')
            if not author or not getattr(author, 'id', None) or author.id in seen_creator_ids:
                continue
            seen_creator_ids.add(author.id)
            creators.append({
                'id': author.id,
                'username': author.username,
                'first_name': author.first_name,
                'last_name': author.last_name,
                'email': author.email,
                'full_name': author.full_name,
            })

        page = self.paginate_queryset(nodes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['creators'] = creators
            response.data['statuses'] = statuses
            return response

        serializer = self.get_serializer(nodes, many=True)
        return Response({
            'results': serializer.data,
            'creators': creators,
            'statuses': statuses,
        })


class ManualTestCaseCategoryListCreateView(generics.ListCreateAPIView):
    """手工用例目录列表和创建"""
    queryset = ManualTestCaseCategory.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'parent']
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'id']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ManualTestCaseCategoryCreateSerializer
        return ManualTestCaseCategorySerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的目录
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        queryset = ManualTestCaseCategory.objects.filter(project__in=accessible_projects)

        # 如果没有指定parent参数，只返回顶级目录
        if 'parent' not in self.request.query_params:
            queryset = queryset.filter(parent__isnull=True)

        return queryset

    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return get_visible_manual_workspace_projects()

    def perform_create(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')

        # 获取用户有权限的项目
        accessible_projects = self.get_user_accessible_projects(user)

        if project_id:
            # 检查指定的项目是否存在且用户有权限
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                project = accessible_projects.first()
                if not project:
                    # 如果用户没有任何项目，创建默认项目
                    project = Project.objects.create(
                        name="默认项目",
                        owner=user,
                        description='系统自动创建的默认项目'
                    )
        else:
            # 没有指定项目，使用第一个可访问的项目
            project = accessible_projects.first()
            if not project:
                # 如果用户没有任何项目，创建默认项目
                project = Project.objects.create(
                    name="默认项目",
                    owner=user,
                    description='系统自动创建的默认项目'
                )

        serializer.save(project=project)


class ManualTestCaseCategoryXMindImportView(APIView):
    """将 XMind 的完整节点层级导入为手工用例目录树。"""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    max_file_size = 20 * 1024 * 1024
    max_node_count = 5000
    max_depth = 100

    def _resolve_project(self, project_id):
        try:
            normalized_id = int(project_id)
        except (TypeError, ValueError):
            raise ValidationError({'project_id': ['请选择有效项目']})

        project = get_visible_manual_workspace_projects().filter(id=normalized_id).first()
        if not project:
            raise ValidationError({'project_id': ['项目不存在或无权访问']})
        return project

    def _resolve_parent(self, project, parent_id):
        if parent_id in (None, ''):
            return None
        try:
            normalized_id = int(parent_id)
        except (TypeError, ValueError):
            raise ValidationError({'parent_id': ['所选父目录无效']})

        parent = ManualTestCaseCategory.objects.filter(
            id=normalized_id,
            project=project,
        ).first()
        if not parent:
            raise ValidationError({'parent_id': ['所选父目录不属于当前项目或已被删除']})
        return parent

    def _validate_tree(self, root):
        node_count = 0
        stack = [(root, 1)]
        while stack:
            node, depth = stack.pop()
            node_count += 1
            if node_count > self.max_node_count:
                raise ValidationError({'xmind_file': [f'XMind 节点数不能超过 {self.max_node_count} 个']})
            if depth > self.max_depth:
                raise ValidationError({'xmind_file': [f'XMind 目录层级不能超过 {self.max_depth} 层']})

            name = str(node.get('name') or '').strip()
            if len(name) > ManualTestCaseCategory._meta.get_field('name').max_length:
                raise ValidationError({'xmind_file': [f'目录名称“{name[:40]}...”超过 200 个字符']})
            stack.extend((child, depth + 1) for child in node.get('children') or [])
        return node_count

    def _create_tree(self, project, node, parent, order, source_name):
        category = ManualTestCaseCategory.objects.create(
            project=project,
            parent=parent,
            name=node['name'],
            description=f'由 XMind 文件《{source_name}》导入' if parent is None else '',
            order=order,
        )
        for child_order, child in enumerate(node.get('children') or []):
            self._create_tree(project, child, category, child_order, source_name)
        return category

    def post(self, request):
        project = self._resolve_project(request.data.get('project_id'))
        parent = self._resolve_parent(project, request.data.get('parent_id'))
        xmind_file = request.FILES.get('xmind_file')
        if not xmind_file:
            raise ValidationError({'xmind_file': ['请选择要导入的 XMind 文件']})
        if not str(getattr(xmind_file, 'name', '')).lower().endswith('.xmind'):
            raise ValidationError({'xmind_file': ['仅支持 .xmind 文件']})
        if getattr(xmind_file, 'size', 0) > self.max_file_size:
            raise ValidationError({'xmind_file': ['XMind 文件不能超过 20MB']})

        try:
            category_tree = parse_uploaded_xmind_category_tree(xmind_file)
        except XMindImportError as exc:
            raise ValidationError({'xmind_file': [str(exc)]}) from exc
        node_count = self._validate_tree(category_tree)

        sibling_max_order = ManualTestCaseCategory.objects.filter(
            project=project,
            parent=parent,
        ).aggregate(max_order=models.Max('order'))['max_order']
        root_order = (sibling_max_order if sibling_max_order is not None else -1) + 1
        with transaction.atomic():
            root_category = self._create_tree(
                project,
                category_tree,
                parent,
                root_order,
                str(xmind_file.name),
            )

        return Response(
            {
                'message': f'已导入 {node_count} 个目录节点',
                'imported_count': node_count,
                'parent_id': parent.id if parent else None,
                'root_category': ManualTestCaseCategorySerializer(root_category).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ManualTestCaseCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """手工用例目录详情、更新和删除"""
    queryset = ManualTestCaseCategory.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ManualTestCaseCategoryUpdateSerializer
        return ManualTestCaseCategorySerializer

    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        return ManualTestCaseCategory.objects.filter(project__in=accessible_projects)


SNAPSHOT_META_FILENAME = '.snapshot-meta.json'
SNAPSHOT_PAGE_NAME_UNSET = object()
SNAPSHOT_PARSE_DATA_UNSET = object()
SNAPSHOT_PARSE_STATUS_IDLE = 'idle'
SNAPSHOT_PARSE_STATUS_SUCCESS = 'success'
SNAPSHOT_PARSE_STATUS_ERROR = 'error'
SNAPSHOT_CREATION_METHOD_MANUAL = 'manual'
SNAPSHOT_CREATION_METHOD_SERVER_PLAYWRIGHT_CLI = 'server_playwright_cli'
SNAPSHOT_CREATION_METHOD_LOCAL_AGENT_PLAYWRIGHT = 'local_agent_playwright'
SNAPSHOT_CREATION_METHOD_LABELS = {
    SNAPSHOT_CREATION_METHOD_MANUAL: '手工创建',
    SNAPSHOT_CREATION_METHOD_SERVER_PLAYWRIGHT_CLI: '服务端Playwright CLI录制',
    SNAPSHOT_CREATION_METHOD_LOCAL_AGENT_PLAYWRIGHT: '本地Agent- Playwright录制',
}
SNAPSHOT_CREATION_METHOD_VALUES = set(SNAPSHOT_CREATION_METHOD_LABELS.keys())
LOCAL_AGENT_PAIRING_TTL_SECONDS = 3600
LOCAL_AGENT_STALE_STOP_GRACE_SECONDS = 10
SNAPSHOT_PARSE_KEYS = (
    'parse_status',
    'parsed_at',
    'parsed_source_mtime',
    'parse_error',
    'line_count',
    'interactive_count',
    'sample_elements',
    'interactive_elements',
)
SNAPSHOT_METADATA_TEXT_KEYS = (
    'alias',
    'creation_method',
    'module_name',
    'module_path',
    'version_name',
)
SNAPSHOT_METADATA_INT_KEYS = (
    'project_id',
    'module_id',
    'version_id',
)


def get_playwright_snapshot_dir():
    snapshot_dir = os.path.join(settings.BASE_DIR, 'playwright_snapshot')
    os.makedirs(snapshot_dir, exist_ok=True)
    return snapshot_dir


def get_playwright_snapshot_meta_path():
    return os.path.join(get_playwright_snapshot_dir(), SNAPSHOT_META_FILENAME)


def load_playwright_snapshot_metadata():
    meta_path = get_playwright_snapshot_meta_path()
    if not os.path.exists(meta_path):
        return {}

    try:
        with open(meta_path, 'r', encoding='utf-8') as meta_file:
            raw_metadata = json.load(meta_file) or {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}

    if not isinstance(raw_metadata, dict):
        return {}

    metadata = {}
    for filename, value in raw_metadata.items():
        entry = {}

        if isinstance(value, dict):
            page_name = value.get('page_name', '')
            for key in SNAPSHOT_METADATA_TEXT_KEYS:
                if key == 'creation_method':
                    continue
                normalized_text = normalize_recording_scalar(value.get(key), 500)
                if normalized_text:
                    entry[key] = normalized_text
            entry['creation_method'] = normalize_snapshot_creation_method(value.get('creation_method'))
            for key in SNAPSHOT_METADATA_INT_KEYS:
                normalized_int = normalize_optional_int(value.get(key))
                if normalized_int is not None:
                    entry[key] = normalized_int
            entry.update(extract_snapshot_parse_entry(value))
        else:
            page_name = value

        normalized_page_name = normalize_snapshot_page_name(page_name)
        if normalized_page_name:
            entry['page_name'] = normalized_page_name

        if entry:
            metadata[str(filename)] = entry

    return metadata


def save_playwright_snapshot_metadata(metadata):
    meta_path = get_playwright_snapshot_meta_path()
    cleaned_metadata = {}
    for filename, value in (metadata or {}).items():
        entry = {}
        page_name = normalize_snapshot_page_name((value or {}).get('page_name'))
        if page_name:
            entry['page_name'] = page_name

        if isinstance(value, dict):
            for key in SNAPSHOT_METADATA_TEXT_KEYS:
                if key == 'creation_method':
                    continue
                normalized_text = normalize_recording_scalar(value.get(key), 500)
                if normalized_text:
                    entry[key] = normalized_text
            creation_method = normalize_snapshot_creation_method(value.get('creation_method'))
            entry['creation_method'] = creation_method
            for key in SNAPSHOT_METADATA_INT_KEYS:
                normalized_int = normalize_optional_int(value.get(key))
                if normalized_int is not None:
                    entry[key] = normalized_int
        else:
            entry['creation_method'] = SNAPSHOT_CREATION_METHOD_MANUAL

        entry.update(extract_snapshot_parse_entry(value))

        if entry:
            cleaned_metadata[str(filename)] = entry

    with open(meta_path, 'w', encoding='utf-8') as meta_file:
        json.dump(cleaned_metadata, meta_file, ensure_ascii=False, indent=2)


def normalize_snapshot_page_name(page_name):
    if page_name is None:
        return ''
    return str(page_name).strip()


def normalize_snapshot_creation_method(value, default=SNAPSHOT_CREATION_METHOD_MANUAL):
    normalized = str(value or '').strip().lower()
    return normalized if normalized in SNAPSHOT_CREATION_METHOD_VALUES else default


def normalize_recording_method(value):
    normalized = str(value or '').strip().lower()
    valid_methods = {
        PlaywrightRecordingSession.RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI,
        PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
    }
    return (
        normalized
        if normalized in valid_methods
        else PlaywrightRecordingSession.RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI
    )


def get_recording_method_label(recording_method):
    return dict(PlaywrightRecordingSession.RECORDING_METHOD_CHOICES).get(recording_method, recording_method or '')


DEFAULT_RECORDING_SCRIPT_SKILL_CODE = 'skill_playwright_recording_script_agent'

DEFAULT_RECORDING_SCRIPT_SKILL = {
    'code': DEFAULT_RECORDING_SCRIPT_SKILL_CODE,
    'name': 'Playwright 半自动录制脚本 Skill',
    'kind': 'skill',
    'provider': PLATFORM_BRAND_NAME,
    'description': '为录制脚本管理页生成可由本地 Agent 执行的 Playwright CDP 脚本。',
    'content': """
你负责把自然语言录制需求转换为 BearAI 本地 Playwright Agent 可执行的 Python async Playwright 脚本。

硬性运行合约：
1. 脚本必须读取环境变量 TESTHUB_REPLAY_CDP_URL。
2. 脚本必须使用 async_playwright 和 p.chromium.connect_over_cdp(cdp_url) 连接本地 Agent 已启动的 Chromium。
3. 脚本必须复用已有 browser.contexts[0] 和已有页面，不允许 playwright.chromium.launch，不允许 browser.close。
4. 脚本必须通过真实的 page.goto/page.click/page.fill/page.select_option/page.check/page.press 等 Playwright 操作推进页面，让 BearAI 录制脚本能采集事件。
5. 优先使用 role、label、placeholder、text 等语义定位；必要时再使用 CSS/XPath fallback。
6. 每次点击、输入、选择后要等待页面稳定；不要用直接 DOM 赋值、dispatchEvent 或 JS 注入伪造操作。
7. 对删除、支付、提交生产数据等破坏性动作保持保守，除非用户明确要求。
8. 如果自然语言缺少账号、数据、按钮名等关键参数，只生成安全可执行的高置信步骤，并把缺口写入 warnings。
""".strip(),
    'risk_level': 'medium',
    'tags': ['Playwright', '录制脚本', '自动录制', '半自动可靠模式', 'Local Agent'],
    'source': 'builtin',
    'version': '1.0.0',
    'review_status': 'approved',
    'is_builtin': True,
    'is_active': True,
}

RECORDING_SCRIPT_SKILL_KEYWORDS = (
    'playwright',
    '录制脚本',
    '自动录制',
    '半自动可靠',
    '半自动',
    'recording script',
    'recording',
    'local agent',
    'TESTHUB_REPLAY_CDP_URL',
    'connect_over_cdp',
)


def _recording_script_skill_namespace(**overrides):
    payload = dict(DEFAULT_RECORDING_SCRIPT_SKILL)
    payload.update(overrides)
    return SimpleNamespace(
        pk=None,
        id=None,
        code=payload['code'],
        name=payload['name'],
        kind=payload['kind'],
        provider=payload['provider'],
        description=payload['description'],
        content=payload['content'],
        risk_level=payload['risk_level'],
        tags=payload['tags'],
        source=payload['source'],
        version=payload['version'],
        review_status=payload['review_status'],
        is_builtin=payload['is_builtin'],
        is_active=payload['is_active'],
    )


def ensure_default_recording_script_skill():
    return _recording_script_skill_namespace()


def normalize_recording_script_generation_text(value, limit=12000):
    text = str(value or '').strip()
    if len(text) <= limit:
        return text
    return f'{text[:limit]}\n\n...(内容已截断)'


def select_recording_script_skill(capability_id=None):
    if capability_id:
        raise ValidationError('思源质量版未启用 AI 军火库 Skill 选择，请使用内置录制 Skill')
    return ensure_default_recording_script_skill()


def touch_recording_script_skill(skill):
    return None


def select_recording_script_llm_config(model_config_id=None):
    raise ValidationError('思源质量版未启用 AI 模型配置，录制脚本将使用确定性模板生成')


def map_recording_script_deepseek_model(model):
    model_map = {
        'deepseek-chat': 'deepseek-chat',
        'deepseek-coder': 'deepseek-chat',
        'chat': 'deepseek-chat',
        'coder': 'deepseek-chat',
    }
    normalized = str(model or '').strip()
    return model_map.get(normalized, normalized or 'deepseek-chat')


def map_recording_script_anthropic_model(model):
    model_map = {
        'sonnet': 'claude-sonnet-4-5-20250929',
        'opus': 'claude-opus-4-5-20251101',
        'haiku': 'claude-3-5-haiku-20241022',
    }
    normalized = str(model or '').strip()
    return model_map.get(normalized, normalized or 'claude-sonnet-4-5-20250929')


def build_recording_script_generation_prompt(*, instruction, target_url, module, skill):
    module_payload = module if isinstance(module, dict) else {}
    skill_content = normalize_recording_script_generation_text(
        skill.content or skill.description or skill.name if skill else '',
        limit=16000,
    )
    skill_label = f'{skill.name} ({skill.code})' if skill else '未匹配到专用 Skill'
    system_prompt = f"""
你是 BearAI 可视化流程录制的 Playwright 脚本生成 Agent。必须严格按照平台 Skill 对过程进行管理和把控。

已启用 Skill：{skill_label}
Skill 内容：
{skill_content or '无专用 Skill 内容，请按 BearAI 半自动可靠录制规则执行。'}

输出要求：
1. 只输出一个 JSON 对象，不要 Markdown，不要解释。
2. JSON 字段必须包含 script、summary、warnings。
3. script 必须是完整 Python async Playwright 脚本。
4. script 必须连接本地 Agent 已启动的 Chromium CDP：读取 TESTHUB_REPLAY_CDP_URL，并使用 p.chromium.connect_over_cdp(cdp_url)。
5. script 必须复用已有 browser/context/page，不允许 launch 新浏览器，不允许调用 browser.close()。
6. script 可以 page.goto 目标地址，但所有操作都应使用稳健定位器：role、label、placeholder、text、CSS fallback，并配合 wait_for_load_state 或 expect。
7. 操作要保守，不要执行删除、支付、提交生产数据等破坏性动作，除非用户需求明确要求。
8. 为了让本地 Agent 能采集步骤，脚本应通过真实 page.click/fill/select_option/check/press 等 Playwright 操作完成流程，不要直接改 DOM。
""".strip()
    user_prompt = {
        'target_url': target_url,
        'module': module_payload,
        'natural_language_instruction': instruction,
        'script_runtime_contract': {
            'cdp_env': 'TESTHUB_REPLAY_CDP_URL',
            'must_not_launch_browser': True,
            'must_not_close_browser': True,
            'recording_events_are_enabled_by_agent': True,
        },
        'recommended_script_skeleton': """
import asyncio
import os
from playwright.async_api import async_playwright, expect

TARGET_URL = "..."

async def main():
    cdp_url = os.environ.get("TESTHUB_REPLAY_CDP_URL", "").strip()
    if not cdp_url:
        raise RuntimeError("TESTHUB_REPLAY_CDP_URL is required")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError("No existing browser context from BearAI Local Agent")
        context = browser.contexts[0]
        page = context.pages[-1] if context.pages else await context.new_page()
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        # Add real user-like operations here.

if __name__ == "__main__":
    asyncio.run(main())
""".strip(),
    }
    return system_prompt, json.dumps(user_prompt, ensure_ascii=False, indent=2)


def call_recording_script_llm(config, *, system_prompt, user_prompt):
    if not config:
        raise ValidationError('请先配置可用的 AI 模型')
    if config.ai_tool in {'codex_cli', 'claude_code'}:
        raise ValidationError('录制脚本生成暂不使用本地 CLI 配置，请选择 DeepSeek 或 Anthropic API 模型配置')
    api_key = decrypt_or_repair_secret(
        config.llm_api_key_encrypted,
        model_instance=config,
        field_name='llm_api_key_encrypted',
    )
    if not api_key:
        raise ValidationError('选择的 AI 模型配置缺少 API Key')

    if config.ai_tool == 'anthropic':
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=map_recording_script_anthropic_model(config.llm_model),
            max_tokens=6000,
            temperature=0.2,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
        return ''.join(
            block.text for block in response.content
            if getattr(block, 'type', '') == 'text'
        ).strip()

    from openai import OpenAI

    base_url = config.llm_base_url or 'https://api.deepseek.com'
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=map_recording_script_deepseek_model(config.llm_model),
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        max_tokens=6000,
        temperature=0.2,
        stream=False,
    )
    return (response.choices[0].message.content or '').strip()


def parse_recording_script_generation_json(raw_text):
    text = str(raw_text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```$', '', text).strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def strip_recording_script_code_fence(script):
    text = str(script or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:python|py)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```$', '', text).strip()
    return text


def validate_recording_script_contract(script):
    try:
        ast.parse(script)
    except SyntaxError as exc:
        raise ValueError(f'生成脚本不是合法 Python：第 {exc.lineno or "-"} 行 {exc.msg}')
    if 'connect_over_cdp' not in script or 'TESTHUB_REPLAY_CDP_URL' not in script:
        raise ValueError('生成脚本未按本地 Agent CDP 连接规范输出')
    if re.search(r'\.launch\s*\(', script):
        raise ValueError('生成脚本包含启动新浏览器的逻辑')
    if re.search(r'browser\.close\s*\(', script):
        raise ValueError('生成脚本包含关闭本地 Agent 浏览器的逻辑')


def clean_recording_action_text(value):
    text = normalize_recording_script_generation_text(value, limit=300)
    text = re.sub(r'^(?:按钮|菜单|页面|模块|页签|标签|链接|字段|输入框)\s*', '', text)
    text = re.sub(r'(?:按钮|菜单|页面|模块|页签|标签|链接|字段|输入框)$', '', text)
    return text.strip(' "\'“”‘’`：:，,。.;；')


def split_recording_instruction_clauses(instruction):
    text = normalize_recording_script_generation_text(instruction, limit=8000)
    text = re.sub(r'(?:然后|接着|随后|之后|并且|再)', '，', text)
    text = re.sub(r'并(?=(?:保存|提交|点击|单击|进入|打开|新增|新建|添加|查询|搜索|输入|填写|填入|选择|勾选|选中|取消|按))', '，', text)
    return [
        item.strip()
        for item in re.split(r'[\n\r，,。；;]+', text)
        if item and item.strip()
    ]


def parse_fill_recording_clause(clause):
    patterns = [
        r'^(?:在|向)?(.+?)(?:中|里)?(?:输入|填写|填入)(.+)$',
        r'^(?:输入|填写|填入)(.+?)(?:到|至|在)(.+?)(?:中|里)?$',
        r'^将(.+?)(?:设置为|设为|改为|填写为|输入为)(.+)$',
    ]
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, clause)
        if not match:
            continue
        first = clean_recording_action_text(match.group(1))
        second = clean_recording_action_text(match.group(2))
        if not first or not second:
            continue
        if index == 1:
            return {'label': second, 'value': first}
        return {'label': first, 'value': second}
    return None


def parse_select_recording_clause(clause):
    patterns = [
        r'^(?:在|从)?(.+?)(?:下拉框|选择框|列表|中|里)?选择(.+)$',
        r'^选择(.+?)(?:为|作为)(.+)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, clause)
        if not match:
            continue
        label = clean_recording_action_text(match.group(1))
        value = clean_recording_action_text(match.group(2))
        if label and value:
            return {'label': label, 'value': value}
    return None


def parse_click_recording_label(clause):
    direct_labels = (
        '保存',
        '提交',
        '查询',
        '搜索',
        '新增',
        '新建',
        '添加',
        '确认',
        '确定',
        '登录',
        '下一步',
        '返回',
        '取消',
    )
    for label in direct_labels:
        if clause == label or re.search(rf'(?:点击|单击|按下|选择)?{re.escape(label)}(?:按钮)?$', clause):
            return label
    match = re.search(r'(?:点击|单击|打开|进入|选择|切换到)(.+)$', clause)
    if match:
        return clean_recording_action_text(match.group(1))
    match = re.search(r'^(?:新增|新建|添加)(?:一条|一个|1条|1个)?(.+)$', clause)
    if match:
        return '新增'
    return ''


def parse_recording_instruction_actions(instruction):
    actions = []
    for clause in split_recording_instruction_clauses(instruction):
        if len(actions) >= 40:
            break
        fill_payload = parse_fill_recording_clause(clause)
        if fill_payload:
            actions.append({'action': 'fill', **fill_payload, 'source': clause})
            continue
        select_payload = parse_select_recording_clause(clause)
        if select_payload:
            actions.append({'action': 'select', **select_payload, 'source': clause})
            continue
        match = re.search(r'^(?:取消勾选|取消选中)(.+)$', clause)
        if match:
            label = clean_recording_action_text(match.group(1))
            if label:
                actions.append({'action': 'uncheck', 'label': label, 'source': clause})
                continue
        match = re.search(r'^(?:勾选|选中)(.+)$', clause)
        if match:
            label = clean_recording_action_text(match.group(1))
            if label:
                actions.append({'action': 'check', 'label': label, 'source': clause})
                continue
        match = re.search(r'^(?:按下|按)(Enter|Tab|Escape|Esc|Backspace|Delete|ArrowUp|ArrowDown|ArrowLeft|ArrowRight)$', clause, flags=re.IGNORECASE)
        if match:
            key = 'Escape' if match.group(1).lower() == 'esc' else match.group(1)
            actions.append({'action': 'press', 'key': key, 'source': clause})
            continue
        click_label = parse_click_recording_label(clause)
        if click_label:
            actions.append({'action': 'click', 'label': click_label, 'source': clause})
            continue
        actions.append({'action': 'note', 'text': clause, 'source': clause})
    return actions


def build_recording_script_fallback_payload(*, instruction, target_url, module=None, skill=None, ai_error=''):
    actions = parse_recording_instruction_actions(instruction)
    executable_actions = [item for item in actions if item.get('action') != 'note']
    warnings = []
    if ai_error:
        warnings.append(f'AI 脚本生成不可用，已使用本地可靠兜底生成器：{ai_error}')
    skipped = [item.get('text') or item.get('source') for item in actions if item.get('action') == 'note']
    if skipped:
        warnings.append('以下描述未能解析为高置信 Playwright 操作，脚本会跳过：' + '；'.join(skipped[:5]))
    if not executable_actions:
        warnings.append('未解析到明确的点击、输入、选择等操作，脚本只会打开目标页面；请补充更具体的录制步骤。')

    actions_literal = repr(json.dumps(executable_actions, ensure_ascii=False))
    module_literal = repr(json.dumps(module if isinstance(module, dict) else {}, ensure_ascii=False))
    script = f'''
import asyncio
import json
import os
import re
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

TARGET_URL = {json.dumps(target_url, ensure_ascii=False)}
INSTRUCTION = {json.dumps(instruction, ensure_ascii=False)}
MODULE = json.loads({module_literal})
ACTIONS = json.loads({actions_literal})


def xpath_literal(text):
    value = str(text or "")
    if "'" not in value:
        return "'" + value + "'"
    if '"' not in value:
        return '"' + value + '"'
    return "concat(" + ', "\\'", '.join("'" + part + "'" for part in value.split("'")) + ")"


async def settle(page):
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    try:
        await page.wait_for_timeout(350)
    except Exception:
        pass


async def first_visible(candidates, timeout=1800):
    for locator in candidates:
        try:
            candidate = locator.first
            await candidate.wait_for(state="visible", timeout=timeout)
            return candidate
        except Exception:
            continue
    return None


def fuzzy_pattern(label):
    return re.compile(re.escape(str(label or "").strip()), re.IGNORECASE)


async def click_label(page, label):
    label = str(label or "").strip()
    if not label:
        raise RuntimeError("点击操作缺少目标名称")
    pattern = fuzzy_pattern(label)
    candidates = [
        page.get_by_role("button", name=pattern),
        page.get_by_role("link", name=pattern),
        page.get_by_role("menuitem", name=pattern),
        page.get_by_role("tab", name=pattern),
        page.get_by_text(label, exact=True),
        page.get_by_text(label),
    ]
    target = await first_visible(candidates)
    if not target:
        raise RuntimeError(f"未找到可点击元素：{{label}}")
    try:
        await target.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    await target.click(timeout=10000)
    await settle(page)


async def fill_field(page, label, value):
    label = str(label or "").strip()
    value = str(value or "")
    literal = xpath_literal(label)
    candidates = []
    if label:
        candidates.extend([
            page.get_by_label(label, exact=False),
            page.get_by_placeholder(label, exact=False),
            page.get_by_role("textbox", name=fuzzy_pattern(label)),
            page.locator(
                "xpath=//input[contains(@placeholder, " + literal + ") or contains(@aria-label, " + literal + ") or contains(@name, " + literal + ")]"
                " | //textarea[contains(@placeholder, " + literal + ") or contains(@aria-label, " + literal + ") or contains(@name, " + literal + ")]"
                " | //*[@contenteditable='true' and (contains(@aria-label, " + literal + ") or contains(normalize-space(.), " + literal + "))]"
            ),
        ])
    candidates.append(page.get_by_role("textbox"))
    target = await first_visible(candidates)
    if not target:
        raise RuntimeError(f"未找到输入框：{{label}}")
    try:
        await target.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    await target.fill(value, timeout=10000)
    await settle(page)


async def select_value(page, label, value):
    label = str(label or "").strip()
    value = str(value or "").strip()
    literal = xpath_literal(label)
    candidates = [
        page.get_by_label(label, exact=False),
        page.locator("xpath=//select[contains(@aria-label, " + literal + ") or contains(@name, " + literal + ")]"),
    ]
    target = await first_visible(candidates)
    if target:
        try:
            await target.select_option(label=value, timeout=10000)
            await settle(page)
            return
        except Exception:
            pass
    await click_label(page, label)
    await click_label(page, value)


async def set_checked(page, label, checked=True):
    label = str(label or "").strip()
    pattern = fuzzy_pattern(label)
    candidates = [
        page.get_by_label(label, exact=False),
        page.get_by_role("checkbox", name=pattern),
        page.get_by_role("radio", name=pattern),
    ]
    target = await first_visible(candidates)
    if not target:
        raise RuntimeError(f"未找到可勾选控件：{{label}}")
    try:
        if checked:
            await target.check(timeout=10000)
        else:
            await target.uncheck(timeout=10000)
    except Exception:
        await target.click(timeout=10000)
    await settle(page)


async def run_action(page, action):
    action_type = action.get("action")
    if action_type == "fill":
        await fill_field(page, action.get("label"), action.get("value"))
    elif action_type == "click":
        await click_label(page, action.get("label"))
    elif action_type == "select":
        await select_value(page, action.get("label"), action.get("value"))
    elif action_type == "check":
        await set_checked(page, action.get("label"), True)
    elif action_type == "uncheck":
        await set_checked(page, action.get("label"), False)
    elif action_type == "press":
        await page.keyboard.press(str(action.get("key") or "Enter"))
        await settle(page)


async def main():
    cdp_url = os.environ.get("TESTHUB_REPLAY_CDP_URL", "").strip()
    if not cdp_url:
        raise RuntimeError("TESTHUB_REPLAY_CDP_URL is required")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError("No existing browser context from BearAI Local Agent")
        context = browser.contexts[0]
        pages = [item for item in context.pages if not item.is_closed()]
        page = pages[-1] if pages else await context.new_page()
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except PlaywrightTimeoutError:
            pass
        for action in ACTIONS:
            await run_action(page, action)


if __name__ == "__main__":
    asyncio.run(main())
'''.strip()
    normalized = normalize_recording_script_generation_payload({
        'script': script,
        'summary': (
            f'已按 {skill.name if skill else "BearAI 默认录制规则"} 生成本地 Agent 可执行脚本，'
            f'解析出 {len(executable_actions)} 个自动录制操作。'
        ),
        'warnings': warnings,
    })
    normalized['planned_actions'] = executable_actions
    return normalized


def normalize_recording_script_generation_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('AI 未返回 JSON 对象')
    script = strip_recording_script_code_fence(payload.get('script') or payload.get('code') or '')
    if not script:
        raise ValueError('AI 未返回 script 字段')
    validate_recording_script_contract(script)

    summary = payload.get('summary') or ''
    if isinstance(summary, list):
        summary = '\n'.join(str(item).strip() for item in summary if str(item).strip())
    else:
        summary = str(summary or '').strip()

    warnings = payload.get('warnings') or []
    if isinstance(warnings, str):
        warnings = [warnings] if warnings.strip() else []
    if not isinstance(warnings, list):
        warnings = []
    warnings = [str(item).strip() for item in warnings if str(item).strip()]
    return {
        'script': script,
        'summary': summary,
        'warnings': warnings,
    }


def create_local_agent_token():
    return secrets.token_urlsafe(32)


def hash_local_agent_token(token):
    return hashlib.sha256(str(token or '').encode('utf-8')).hexdigest()


def get_local_agent_pairing_url(request, session_id):
    return request.build_absolute_uri(
        f'/api/testcases/playwright-recordings/{session_id}/agent/'
    )


def verify_local_agent_token(session, request):
    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    expected_hash = metadata.get('local_agent_token_hash') or ''
    raw_token = (
        request.headers.get('X-TestHub-Agent-Token')
        or request.query_params.get('token')
        or request.data.get('token')
        or ''
    )
    if not expected_hash or not raw_token:
        return False

    expires_at = normalize_snapshot_timestamp(metadata.get('local_agent_token_expires_at'))
    if expires_at is not None and time.time() > expires_at:
        return False

    return secrets.compare_digest(expected_hash, hash_local_agent_token(raw_token))


def json_safe_recording_value(value):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def extract_recording_action_value(event):
    if 'value' in event:
        value = event.get('value')
    elif 'checked' in event:
        value = event.get('checked')
    elif 'key' in event:
        value = event.get('key')
    else:
        value = ''

    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ''
    return normalize_recording_scalar(value)


def normalize_snapshot_parse_status(parse_status):
    normalized = str(parse_status or '').strip().lower()
    if normalized in (SNAPSHOT_PARSE_STATUS_SUCCESS, SNAPSHOT_PARSE_STATUS_ERROR):
        return normalized
    return SNAPSHOT_PARSE_STATUS_IDLE


def normalize_snapshot_timestamp(value):
    if value in (None, ''):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_snapshot_non_negative_int(value):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def normalize_snapshot_json_scalar(value):
    if value is None:
        return ''

    if isinstance(value, str):
        return normalize_snapshot_inline_text(value)

    if isinstance(value, (int, float, bool)):
        return value

    return normalize_snapshot_inline_text(value)


def sanitize_snapshot_selectors(selectors):
    if not isinstance(selectors, list):
        return []

    sanitized = []
    for selector in selectors:
        if not isinstance(selector, dict):
            continue

        value = normalize_snapshot_inline_text(selector.get('value') or '')
        if not value:
            continue

        item = {
            'type': normalize_snapshot_inline_text(selector.get('type') or 'selector') or 'selector',
            'value': value
        }

        priority = selector.get('priority')
        if priority not in (None, ''):
            try:
                item['priority'] = int(priority)
            except (TypeError, ValueError):
                pass

        sanitized.append(item)

    return sanitized


def sanitize_snapshot_attributes(attributes):
    if not isinstance(attributes, dict):
        return {}

    sanitized = {}
    for key, value in attributes.items():
        key_text = str(key or '').strip()
        if not key_text or value is None:
            continue
        sanitized[key_text] = normalize_snapshot_json_scalar(value)

    return sanitized


def sanitize_snapshot_sample_elements(sample_elements):
    if not isinstance(sample_elements, list):
        return []

    sanitized = []
    for item in sample_elements[:20]:
        if not isinstance(item, dict):
            continue

        sanitized.append({
            'type': str(item.get('type') or '-'),
            'text': str(item.get('text') or '-'),
            'selector': str(item.get('selector') or '-')
        })

    return sanitized


def sanitize_snapshot_interactive_elements(interactive_elements):
    if not isinstance(interactive_elements, list):
        return []

    sanitized = []
    for index, element in enumerate(interactive_elements):
        if not isinstance(element, dict):
            continue

        sanitized.append({
            'id': str(element.get('id') or f'element_{index}'),
            'type': str(element.get('type') or 'generic'),
            'text': str(element.get('text') or ''),
            'ref': str(element.get('ref') or ''),
            'attributes': sanitize_snapshot_attributes(element.get('attributes')),
            'selectors': sanitize_snapshot_selectors(element.get('selectors')),
        })

    return sanitized


def clear_snapshot_parse_metadata(entry):
    sanitized_entry = dict(entry or {})
    for key in SNAPSHOT_PARSE_KEYS:
        sanitized_entry.pop(key, None)
    return sanitized_entry


def extract_snapshot_parse_entry(raw_entry):
    if not isinstance(raw_entry, dict):
        return {}

    parse_status = normalize_snapshot_parse_status(raw_entry.get('parse_status'))
    if parse_status == SNAPSHOT_PARSE_STATUS_IDLE:
        return {}

    line_count = normalize_snapshot_non_negative_int(raw_entry.get('line_count'))
    parsed_at = normalize_snapshot_timestamp(raw_entry.get('parsed_at'))
    parsed_source_mtime = normalize_snapshot_timestamp(raw_entry.get('parsed_source_mtime'))
    sample_elements = sanitize_snapshot_sample_elements(raw_entry.get('sample_elements'))
    interactive_elements = sanitize_snapshot_interactive_elements(raw_entry.get('interactive_elements'))

    entry = {
        'parse_status': parse_status,
        'line_count': line_count,
        'interactive_count': len(interactive_elements) if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS else 0,
        'sample_elements': sample_elements if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS else [],
        'interactive_elements': interactive_elements if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS else [],
    }

    if parsed_at is not None:
        entry['parsed_at'] = parsed_at

    if parsed_source_mtime is not None:
        entry['parsed_source_mtime'] = parsed_source_mtime

    if parse_status == SNAPSHOT_PARSE_STATUS_ERROR:
        entry['parse_error'] = str(raw_entry.get('parse_error') or '').strip() or '快照解析失败'
    else:
        entry['parse_error'] = ''

    return entry


def prepare_snapshot_parse_entry(parse_data, *, parsed_source_mtime=None):
    if not isinstance(parse_data, dict):
        return {}

    parse_status = normalize_snapshot_parse_status(parse_data.get('parse_status'))
    if parse_status == SNAPSHOT_PARSE_STATUS_IDLE:
        return {}

    interactive_elements = sanitize_snapshot_interactive_elements(parse_data.get('interactive_elements'))
    line_count = normalize_snapshot_non_negative_int(parse_data.get('line_count'))
    parsed_at = normalize_snapshot_timestamp(parse_data.get('parsed_at')) or time.time()
    source_mtime = normalize_snapshot_timestamp(parsed_source_mtime)
    if source_mtime is None:
        source_mtime = normalize_snapshot_timestamp(parse_data.get('parsed_source_mtime'))

    entry = {
        'parse_status': parse_status,
        'parsed_at': parsed_at,
        'line_count': line_count,
    }

    if source_mtime is not None:
        entry['parsed_source_mtime'] = source_mtime

    if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS:
        entry['interactive_elements'] = interactive_elements
        entry['interactive_count'] = len(interactive_elements)
        entry['sample_elements'] = sanitize_snapshot_sample_elements(parse_data.get('sample_elements'))
        entry['parse_error'] = ''
    else:
        entry['interactive_elements'] = []
        entry['interactive_count'] = 0
        entry['sample_elements'] = []
        entry['parse_error'] = str(parse_data.get('parse_error') or '').strip() or '快照解析失败'

    return entry


def build_empty_snapshot_parse_data():
    return {
        'parse_status': SNAPSHOT_PARSE_STATUS_IDLE,
        'parsed_at': None,
        'parse_error': '',
        'line_count': 0,
        'interactive_count': 0,
        'sample_elements': [],
        'interactive_elements': [],
    }


def get_snapshot_parse_data(entry, *, file_mtime=None):
    parse_data = build_empty_snapshot_parse_data()
    if not isinstance(entry, dict):
        return parse_data

    parse_status = normalize_snapshot_parse_status(entry.get('parse_status'))
    if parse_status == SNAPSHOT_PARSE_STATUS_IDLE:
        return parse_data

    parsed_source_mtime = normalize_snapshot_timestamp(entry.get('parsed_source_mtime'))
    if file_mtime is not None:
        current_mtime = normalize_snapshot_timestamp(file_mtime)
        if current_mtime is not None and (
            parsed_source_mtime is None or abs(parsed_source_mtime - current_mtime) > 1e-6
        ):
            return parse_data

    parse_data.update({
        'parse_status': parse_status,
        'parsed_at': normalize_snapshot_timestamp(entry.get('parsed_at')),
        'parse_error': str(entry.get('parse_error') or '').strip(),
        'line_count': normalize_snapshot_non_negative_int(entry.get('line_count')),
        'interactive_count': normalize_snapshot_non_negative_int(entry.get('interactive_count')),
        'sample_elements': sanitize_snapshot_sample_elements(entry.get('sample_elements')),
        'interactive_elements': sanitize_snapshot_interactive_elements(entry.get('interactive_elements')),
    })

    if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS:
        parse_data['interactive_count'] = len(parse_data['interactive_elements'])
        parse_data['parse_error'] = ''
    else:
        parse_data['interactive_count'] = 0
        parse_data['sample_elements'] = []
        parse_data['interactive_elements'] = []
        parse_data['parse_error'] = parse_data['parse_error'] or '快照解析失败'

    return parse_data


def build_snapshot_parse_summary(entry, *, file_mtime=None):
    parse_data = get_snapshot_parse_data(entry, file_mtime=file_mtime)
    return {
        'parse_status': parse_data['parse_status'],
        'parsed_at': parse_data['parsed_at'],
        'parse_error': parse_data['parse_error'],
        'line_count': parse_data['line_count'],
        'interactive_count': parse_data['interactive_count'],
    }


def build_snapshot_parsed_result(entry, *, file_mtime=None):
    parse_data = get_snapshot_parse_data(entry, file_mtime=file_mtime)
    parse_status = parse_data['parse_status']
    return {
        'parse_status': parse_status,
        'valid': True if parse_status == SNAPSHOT_PARSE_STATUS_SUCCESS else False if parse_status == SNAPSHOT_PARSE_STATUS_ERROR else None,
        'parsed_at': parse_data['parsed_at'],
        'error': parse_data['parse_error'],
        'line_count': parse_data['line_count'],
        'interactive_count': parse_data['interactive_count'],
        'sample_elements': parse_data['sample_elements'],
        'interactive_elements': parse_data['interactive_elements'],
    }


def find_snapshot_filename_by_page_name(page_name, metadata=None, exclude_filenames=None):
    normalized_page_name = normalize_snapshot_page_name(page_name)
    if not normalized_page_name:
        return None

    metadata = metadata if metadata is not None else load_playwright_snapshot_metadata()
    exclude_filenames = {str(filename) for filename in (exclude_filenames or set()) if filename}
    target_page_name = normalized_page_name.casefold()

    for filename, item in metadata.items():
        if filename in exclude_filenames:
            continue
        current_page_name = normalize_snapshot_page_name((item or {}).get('page_name'))
        if current_page_name and current_page_name.casefold() == target_page_name:
            return filename

    return None


def cleanup_snapshot_metadata(existing_filenames, metadata=None):
    metadata = dict(metadata if metadata is not None else load_playwright_snapshot_metadata())
    existing_filenames = set(existing_filenames or [])
    stale_filenames = [filename for filename in metadata.keys() if filename not in existing_filenames]
    if not stale_filenames:
        return metadata

    for filename in stale_filenames:
        metadata.pop(filename, None)
    save_playwright_snapshot_metadata(metadata)
    return metadata


def upsert_snapshot_metadata(
    filename,
    *,
    page_name=SNAPSHOT_PAGE_NAME_UNSET,
    previous_filename=None,
    parse_data=SNAPSHOT_PARSE_DATA_UNSET,
    parsed_source_mtime=None,
    alias=SNAPSHOT_PAGE_NAME_UNSET,
    module=SNAPSHOT_PAGE_NAME_UNSET,
    creation_method=SNAPSHOT_PAGE_NAME_UNSET
):
    metadata = load_playwright_snapshot_metadata()

    if previous_filename and previous_filename != filename and previous_filename in metadata:
        metadata[filename] = dict(metadata.pop(previous_filename) or {})

    entry = dict(metadata.get(filename) or {})

    if page_name is not SNAPSHOT_PAGE_NAME_UNSET:
        normalized_page_name = normalize_snapshot_page_name(page_name)
        duplicate_filename = find_snapshot_filename_by_page_name(
            normalized_page_name,
            metadata=metadata,
            exclude_filenames={filename, previous_filename}
        )
        if duplicate_filename:
            raise ValueError(f'页面名称“{normalized_page_name}”已绑定快照文件 {duplicate_filename}')

        if normalized_page_name:
            entry['page_name'] = normalized_page_name
        else:
            entry.pop('page_name', None)

    if alias is not SNAPSHOT_PAGE_NAME_UNSET:
        normalized_alias = normalize_recording_scalar(alias, 200)
        if normalized_alias:
            entry['alias'] = normalized_alias
        else:
            entry.pop('alias', None)

    if module is not SNAPSHOT_PAGE_NAME_UNSET:
        normalized_module = normalize_module_metadata(module if isinstance(module, dict) else {})
        for key in ('project_id', 'module_id', 'module_name', 'module_path', 'version_id', 'version_name'):
            entry.pop(key, None)
        entry.update(normalized_module)

    if creation_method is not SNAPSHOT_PAGE_NAME_UNSET:
        entry['creation_method'] = normalize_snapshot_creation_method(creation_method)

    if parse_data is not SNAPSHOT_PARSE_DATA_UNSET:
        entry = clear_snapshot_parse_metadata(entry)
        entry.update(prepare_snapshot_parse_entry(parse_data, parsed_source_mtime=parsed_source_mtime))

    if entry:
        metadata[filename] = entry
    else:
        metadata.pop(filename, None)

    save_playwright_snapshot_metadata(metadata)
    return metadata.get(filename, {})


def delete_snapshot_metadata(filename):
    metadata = load_playwright_snapshot_metadata()
    if filename in metadata:
        metadata.pop(filename, None)
        save_playwright_snapshot_metadata(metadata)


def normalize_snapshot_filename(filename):
    normalized = (filename or '').strip()
    if not normalized:
        raise ValueError('快照文件名不能为空')

    if normalized != os.path.basename(normalized):
        raise ValueError('文件名不合法')

    lower_name = normalized.lower()
    if not (lower_name.endswith('.yml') or lower_name.endswith('.yaml')):
        raise ValueError('仅支持 .yml 或 .yaml 格式的快照文件')

    return normalized


def resolve_snapshot_file_path(filename, must_exist=True):
    snapshot_dir = get_playwright_snapshot_dir()
    normalized = normalize_snapshot_filename(filename)
    file_path = os.path.join(snapshot_dir, normalized)

    if not os.path.abspath(file_path).startswith(os.path.abspath(snapshot_dir)):
        raise ValueError('非法的文件路径')

    if must_exist and not os.path.exists(file_path):
        raise FileNotFoundError('快照文件不存在')

    return normalized, file_path


def build_snapshot_file_info(filename, metadata=None):
    _, file_path = resolve_snapshot_file_path(filename, must_exist=True)
    file_stat = os.stat(file_path)
    metadata = metadata if metadata is not None else load_playwright_snapshot_metadata()
    entry = metadata.get(filename) or {}
    page_name = normalize_snapshot_page_name(entry.get('page_name'))
    alias = normalize_recording_scalar(entry.get('alias'), 200)
    project_id = normalize_optional_int(entry.get('project_id'))
    version_id = normalize_version_id(entry.get('version_id'))
    version_name = normalize_recording_scalar(entry.get('version_name'), 200)
    module_id = normalize_optional_int(entry.get('module_id'))
    module_name = normalize_recording_scalar(entry.get('module_name'), 200)
    module_path = normalize_recording_scalar(entry.get('module_path'), 500)
    creation_method = normalize_snapshot_creation_method(entry.get('creation_method'))
    return {
        'filename': filename,
        'page_name': page_name,
        'alias': alias,
        'creation_method': creation_method,
        'creation_method_label': SNAPSHOT_CREATION_METHOD_LABELS.get(creation_method, creation_method),
        'project_id': project_id,
        'version_id': version_id,
        'version_name': version_name,
        'module_id': module_id,
        'module_name': module_name,
        'module_path': module_path,
        'module': {
            'project_id': project_id,
            'version_id': version_id,
            'version_name': version_name,
            'module_id': module_id,
            'module_name': module_name,
            'module_path': module_path,
        } if any([project_id is not None, version_id is not None, version_name, module_id is not None, module_name, module_path]) else None,
        'size': file_stat.st_size,
        'created_at': file_stat.st_ctime,
        'modified_at': file_stat.st_mtime,
        'extension': os.path.splitext(filename)[1].lower(),
        **build_snapshot_parse_summary(entry, file_mtime=file_stat.st_mtime)
    }


RECORDING_STEP_SNAPSHOT_FILENAME_PATTERN = re.compile(
    r'^recording-(?P<session_id>.+)-step-(?P<step_number>\d{4})\.ya?ml$',
    re.IGNORECASE,
)
RECORDING_FLOW_SNAPSHOT_FILENAME_PATTERN = re.compile(
    r'^recording-(?P<session_id>.+)-flow-page-(?P<page_number>\d{4})\.ya?ml$',
    re.IGNORECASE,
)
SNAPSHOT_MODULE_METADATA_KEYS = (
    'project_id',
    'version_id',
    'version_name',
    'module_id',
    'module_name',
    'module_path',
)


def normalize_snapshot_module_metadata(data):
    if not isinstance(data, dict):
        data = {}

    module = {}
    project_id = normalize_optional_int(data.get('project_id'))
    version_id = normalize_version_id(data.get('version_id'))
    module_id = normalize_optional_int(data.get('module_id'))
    version_name = normalize_recording_scalar(data.get('version_name'), 200)
    module_name = normalize_recording_scalar(data.get('module_name'), 200)
    module_path = normalize_recording_scalar(data.get('module_path'), 500)

    if project_id is not None:
        module['project_id'] = project_id
    if version_id is not None:
        module['version_id'] = version_id
    if version_name:
        module['version_name'] = version_name
    if module_id is not None:
        module['module_id'] = module_id
    if module_name:
        module['module_name'] = module_name
    if module_path:
        module['module_path'] = module_path
    return module


def merge_snapshot_module_metadata(entry, module):
    merged = dict(entry or {})
    normalized_module = normalize_snapshot_module_metadata(module if isinstance(module, dict) else {})
    for key in SNAPSHOT_MODULE_METADATA_KEYS:
        value = normalized_module.get(key)
        if value not in (None, '') and merged.get(key) in (None, ''):
            merged[key] = value
    return merged


def build_recording_snapshot_module_metadata_map(filenames):
    filenames = {str(filename) for filename in (filenames or []) if filename}
    if not filenames:
        return {}

    module_by_filename = {}
    parsed_filenames_by_session_id = {}
    explicit_step_filenames = set()
    session_ids = set()
    normalized_module_by_session_id = {}

    def get_normalized_session_module(session):
        session_id = getattr(session, 'session_id', '')
        if not session_id:
            return {}
        if session_id not in normalized_module_by_session_id:
            normalized_module_by_session_id[session_id] = normalize_snapshot_module_metadata(
                get_recording_session_module_metadata(session)
            )
        return normalized_module_by_session_id[session_id]

    for filename in filenames:
        step_match = RECORDING_STEP_SNAPSHOT_FILENAME_PATTERN.match(filename)
        if step_match:
            session_id = step_match.group('session_id')
            parsed_filenames_by_session_id.setdefault(session_id, []).append(filename)
            session_ids.add(session_id)
            continue

        flow_match = RECORDING_FLOW_SNAPSHOT_FILENAME_PATTERN.match(filename)
        if flow_match:
            session_id = flow_match.group('session_id')
            parsed_filenames_by_session_id.setdefault(session_id, []).append(filename)
            session_ids.add(session_id)
            continue

        explicit_step_filenames.add(filename)

    explicit_steps = []
    if explicit_step_filenames:
        for step in PlaywrightRecordingStep.objects.filter(
            snapshot_filename__in=explicit_step_filenames
        ).exclude(
            snapshot_filename=''
        ).select_related('session'):
            explicit_steps.append(step)
            session_ids.add(step.session.session_id)

    session_module_by_id = {}
    if session_ids:
        for session in PlaywrightRecordingSession.objects.filter(
            session_id__in=session_ids
        ).only('session_id', 'metadata'):
            module = get_normalized_session_module(session)
            if module:
                session_module_by_id[session.session_id] = module

    for session_id, session_filenames in parsed_filenames_by_session_id.items():
        module = session_module_by_id.get(session_id)
        if not module:
            continue
        for filename in session_filenames:
            module_by_filename.setdefault(filename, module)

    for step in explicit_steps:
        module = session_module_by_id.get(step.session.session_id) or get_normalized_session_module(step.session)
        if module:
            module_by_filename.setdefault(step.snapshot_filename, module)

    return module_by_filename


def build_effective_snapshot_metadata(metadata, filenames):
    metadata = dict(metadata or {})
    module_by_filename = build_recording_snapshot_module_metadata_map(filenames)
    if not module_by_filename:
        return metadata

    effective_metadata = dict(metadata)
    for filename, module in module_by_filename.items():
        effective_entry = merge_snapshot_module_metadata(effective_metadata.get(filename), module)
        if effective_entry:
            effective_metadata[filename] = effective_entry
    return effective_metadata


def parse_boolean_value(value, default=False):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def write_snapshot_file(
    filename,
    content,
    overwrite=True,
    page_name=SNAPSHOT_PAGE_NAME_UNSET,
    alias=SNAPSHOT_PAGE_NAME_UNSET,
    module=SNAPSHOT_PAGE_NAME_UNSET,
    creation_method=SNAPSHOT_PAGE_NAME_UNSET
):
    normalized, file_path = resolve_snapshot_file_path(filename, must_exist=False)
    if os.path.exists(file_path) and not overwrite:
        raise FileExistsError('快照文件已存在')

    content = sanitize_snapshot_content(content)
    with open(file_path, 'w', encoding='utf-8') as snapshot_file:
        snapshot_file.write(content)

    upsert_snapshot_metadata(
        normalized,
        page_name=page_name,
        parse_data={},
        alias=alias,
        module=module,
        creation_method=creation_method,
    )
    return build_snapshot_file_info(normalized)


class PlaywrightSnapshotListView(APIView):
    """Playwright快照文件列表"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        """获取所有快照文件列表"""
        # 快照文件存储在项目根目录的 playwright_snapshot 目录
        snapshot_dir = get_playwright_snapshot_dir()
        keyword = (request.query_params.get('keyword') or request.query_params.get('search') or '').strip().lower()
        extension = (request.query_params.get('extension') or '').strip().lower()
        page_name_filter = normalize_snapshot_page_name(request.query_params.get('page_name')).lower()
        module_id_filter = normalize_optional_int(request.query_params.get('module_id'))
        module_path_filter = normalize_recording_system_page_path(request.query_params.get('module_path')).lower()
        module_name_filter = normalize_recording_scalar(request.query_params.get('module_name'), 200).lower()
        project_id_filter = normalize_optional_int(request.query_params.get('project_id'))
        version_id_filter = normalize_version_id(request.query_params.get('version_id') or request.query_params.get('version'))
        include_descendants = parse_boolean_value(request.query_params.get('include_descendants'), default=False)
        sort_by = (request.query_params.get('sort_by') or request.query_params.get('sortBy') or 'modified_desc').strip()
        snapshot_filenames = [
            filename for filename in os.listdir(snapshot_dir)
            if filename.lower().endswith(('.yml', '.yaml'))
        ]
        metadata = cleanup_snapshot_metadata(
            existing_filenames=snapshot_filenames
        )
        should_derive_recording_modules = any([
            keyword,
            module_id_filter is not None,
            module_path_filter,
            module_name_filter,
            project_id_filter is not None,
            version_id_filter is not None,
        ])
        if should_derive_recording_modules:
            metadata = build_effective_snapshot_metadata(metadata, snapshot_filenames)
        descendant_module_ids = (
            set(build_descendant_module_ids(module_id_filter))
            if include_descendants and module_id_filter is not None
            else None
        )

        snapshot_files = []
        for filename in snapshot_filenames:
            lower_name = filename.lower()
            page_name = normalize_snapshot_page_name((metadata.get(filename) or {}).get('page_name')).lower()
            entry = metadata.get(filename) or {}
            alias = normalize_recording_scalar(entry.get('alias'), 200).lower()
            module_name = normalize_recording_scalar(entry.get('module_name'), 200).lower()
            module_path = normalize_recording_scalar(entry.get('module_path'), 500).lower()

            if keyword and not any(
                keyword in value
                for value in (lower_name, page_name, alias, module_name, module_path)
            ):
                continue

            if extension and extension not in ('yml', 'yaml', '.yml', '.yaml'):
                continue

            if extension and os.path.splitext(lower_name)[1] != (extension if extension.startswith('.') else f'.{extension}'):
                continue

            if page_name_filter and page_name_filter not in page_name:
                continue

            if not snapshot_module_matches(
                entry,
                module_id_filter=module_id_filter,
                module_path_filter=module_path_filter,
                module_name_filter=module_name_filter,
                project_id_filter=project_id_filter,
                include_descendants=include_descendants,
                descendant_module_ids=descendant_module_ids,
            ):
                continue
            if not snapshot_version_matches(entry, version_id_filter=version_id_filter):
                continue

            snapshot_files.append(build_snapshot_file_info(filename, metadata=metadata))

        sorters = {
            'modified_asc': (lambda item: item.get('modified_at') or 0, False),
            'name_asc': (lambda item: str(item.get('filename') or '').lower(), False),
            'name_desc': (lambda item: str(item.get('filename') or '').lower(), True),
            'size_desc': (lambda item: item.get('size') or 0, True),
            'size_asc': (lambda item: item.get('size') or 0, False),
        }
        sort_key, reverse = sorters.get(sort_by, (lambda item: item.get('modified_at') or 0, True))
        snapshot_files.sort(key=sort_key, reverse=reverse)
        page_results, page_meta = paginate_list(request, snapshot_files, default_page_size=20)

        return Response({
            **page_meta,
            'results': page_results
        })

    def post(self, request):
        """导入或创建快照文件"""
        files = request.FILES.getlist('files') or ([request.FILES.get('file')] if request.FILES.get('file') else [])
        overwrite = parse_boolean_value(request.data.get('overwrite'), default=False)
        page_name = request.data.get('page_name', SNAPSHOT_PAGE_NAME_UNSET)
        alias = request.data.get('alias', SNAPSHOT_PAGE_NAME_UNSET)
        creation_method = normalize_snapshot_creation_method(
            request.data.get('creation_method'),
            default=SNAPSHOT_CREATION_METHOD_MANUAL,
        )
        module = extract_module_payload(request.data)
        module_value = module if module else SNAPSHOT_PAGE_NAME_UNSET

        if files:
            imported_files = []
            for uploaded_file in files:
                try:
                    filename = normalize_snapshot_filename(uploaded_file.name)
                    content = uploaded_file.read().decode('utf-8')
                    imported_files.append(
                        write_snapshot_file(
                            filename,
                            content,
                            overwrite=overwrite,
                            page_name=page_name if len(files) == 1 else SNAPSHOT_PAGE_NAME_UNSET,
                            alias=alias if len(files) == 1 else SNAPSHOT_PAGE_NAME_UNSET,
                            module=module_value,
                            creation_method=creation_method,
                        )
                    )
                except UnicodeDecodeError:
                    return Response(
                        {'error': f'文件 {uploaded_file.name} 不是有效的 UTF-8 文本'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except FileExistsError:
                    return Response(
                        {'error': f'文件 {uploaded_file.name} 已存在，请开启覆盖后重试'},
                        status=status.HTTP_409_CONFLICT
                    )
                except ValueError as exc:
                    return Response(
                        {'error': str(exc)},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response({
                'message': '快照文件导入成功',
                'count': len(imported_files),
                'results': imported_files
            }, status=status.HTTP_201_CREATED)

        filename = request.data.get('filename')
        content = request.data.get('content', '')
        if not filename:
            return Response(
                {'error': '请提供文件名或上传文件'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            snapshot_file = write_snapshot_file(
                filename,
                content,
                overwrite=overwrite,
                page_name=page_name,
                alias=alias,
                module=module_value,
                creation_method=creation_method,
            )
            return Response(snapshot_file, status=status.HTTP_201_CREATED)
        except FileExistsError:
            return Response(
                {'error': '快照文件已存在，请更换文件名或启用覆盖'},
                status=status.HTTP_409_CONFLICT
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PlaywrightSnapshotDetailView(APIView):
    """Playwright快照文件详情"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, filename):
        """获取快照文件内容"""
        try:
            normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = sanitize_snapshot_content(f.read())

            metadata = load_playwright_snapshot_metadata()
            file_stat = os.stat(file_path)
            return Response({
                'filename': normalized_filename,
                'content': content,
                **build_snapshot_file_info(normalized_filename, metadata=metadata),
                'parsed_snapshot': build_snapshot_parsed_result(
                    metadata.get(normalized_filename),
                    file_mtime=file_stat.st_mtime
                )
            })
        except FileNotFoundError:
            return Response(
                {'error': '快照文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'读取文件失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, filename):
        """更新快照文件内容或文件名"""
        try:
            original_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
            normalized_filename = original_filename
            new_filename = request.data.get('filename', original_filename)
            new_filename = normalize_snapshot_filename(new_filename)
            content = request.data.get('content')
            page_name = request.data.get('page_name', SNAPSHOT_PAGE_NAME_UNSET) if 'page_name' in request.data else SNAPSHOT_PAGE_NAME_UNSET
            alias = request.data.get('alias', SNAPSHOT_PAGE_NAME_UNSET) if 'alias' in request.data else SNAPSHOT_PAGE_NAME_UNSET
            creation_method = (
                normalize_snapshot_creation_method(request.data.get('creation_method'))
                if 'creation_method' in request.data
                else SNAPSHOT_PAGE_NAME_UNSET
            )
            module = extract_module_payload(request.data) if any(
                key in request.data for key in ('module', 'project_id', 'version_id', 'version_name', 'module_id', 'module_name', 'module_path')
            ) else SNAPSHOT_PAGE_NAME_UNSET
            existing_content = None

            if content is None:
                return Response(
                    {'error': '缺少快照文件内容'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            content = sanitize_snapshot_content(content)
            with open(file_path, 'r', encoding='utf-8') as snapshot_file:
                existing_content = sanitize_snapshot_content(snapshot_file.read())

            if new_filename != normalized_filename:
                _, new_file_path = resolve_snapshot_file_path(new_filename, must_exist=False)
                if os.path.exists(new_file_path):
                    return Response(
                        {'error': '目标文件名已存在'},
                        status=status.HTTP_409_CONFLICT
                    )
                os.replace(file_path, new_file_path)
                file_path = new_file_path
                normalized_filename = new_filename

            content_changed = content != existing_content
            if content_changed:
                with open(file_path, 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)

            upsert_snapshot_metadata(
                normalized_filename,
                page_name=page_name,
                previous_filename=original_filename if new_filename != original_filename else None,
                parse_data={} if content_changed else SNAPSHOT_PARSE_DATA_UNSET,
                alias=alias,
                module=module,
                creation_method=creation_method,
            )

            metadata = load_playwright_snapshot_metadata()
            file_stat = os.stat(file_path)

            return Response({
                'message': '快照文件更新成功',
                'filename': normalized_filename,
                'content': content,
                **build_snapshot_file_info(normalized_filename, metadata=metadata),
                'parsed_snapshot': build_snapshot_parsed_result(
                    metadata.get(normalized_filename),
                    file_mtime=file_stat.st_mtime
                )
            })
        except FileNotFoundError:
            return Response(
                {'error': '快照文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {'error': f'更新快照文件失败: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, filename):
        """删除快照文件"""
        try:
            normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
            os.remove(file_path)
            delete_snapshot_metadata(normalized_filename)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FileNotFoundError:
            return Response(
                {'error': '快照文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {'error': f'删除快照文件失败: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlaywrightSnapshotParseView(APIView):
    """Persist snapshot parse result."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, filename):
        try:
            normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
            file_stat = os.stat(file_path)
            parse_entry = prepare_snapshot_parse_entry(
                request.data or {},
                parsed_source_mtime=file_stat.st_mtime
            )

            upsert_snapshot_metadata(
                normalized_filename,
                parse_data=parse_entry,
                parsed_source_mtime=file_stat.st_mtime
            )

            metadata = load_playwright_snapshot_metadata()
            return Response({
                'message': 'Snapshot parse result updated',
                **build_snapshot_file_info(normalized_filename, metadata=metadata),
                'parsed_snapshot': build_snapshot_parsed_result(
                    metadata.get(normalized_filename),
                    file_mtime=file_stat.st_mtime
                )
            })
        except FileNotFoundError:
            return Response(
                {'error': 'Snapshot file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {'error': f'Failed to save snapshot parse result: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlaywrightSnapshotDownloadView(APIView):
    """下载单个 Playwright 快照文件"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, filename):
        try:
            normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
            with open(file_path, 'r', encoding='utf-8') as snapshot_file:
                content = sanitize_snapshot_content(snapshot_file.read())
            response = HttpResponse(content, content_type='application/x-yaml; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{normalized_filename}"'
            return response
        except FileNotFoundError:
            return Response(
                {'error': '快照文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PlaywrightSnapshotBatchExportView(APIView):
    """批量导出 Playwright 快照文件"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        filenames = request.data.get('filenames') or []
        if not isinstance(filenames, list) or not filenames:
            return Response(
                {'error': '请至少选择一个快照文件'},
                status=status.HTTP_400_BAD_REQUEST
            )

        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                for filename in filenames:
                    normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
                    with open(file_path, 'r', encoding='utf-8') as snapshot_file:
                        archive.writestr(normalized_filename, sanitize_snapshot_content(snapshot_file.read()))

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="playwright-snapshots.zip"'
            return response
        except FileNotFoundError:
            return Response(
                {'error': '包含不存在的快照文件，请刷新列表后重试'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

SNAPSHOT_INTERACTIVE_TYPES = {
    'button', 'link', 'a', 'textbox', 'input', 'searchbox', 'checkbox',
    'radio', 'select', 'combobox', 'listbox', 'tab', 'menuitem',
    'iframe', 'frame', 'file', 'clickable',
}

COMPONENT_TYPE_BY_ELEMENT_TYPE = {
    'textbox': 'input',
    'input': 'input',
    'searchbox': 'input',
    'textarea': 'input',
    'select': 'select',
    'combobox': 'select',
    'listbox': 'select',
    'checkbox': 'checkbox',
    'radio': 'radio',
    'link': 'link',
    'a': 'link',
    'button': 'button',
    'tab': 'tab',
    'menuitem': 'menuitem',
    'iframe': 'iframe',
    'frame': 'iframe',
    'file': 'file',
    'clickable': 'clickable',
}

FLOW_COMPONENT_SIZES = {
    'input': {'width': 148, 'height': 82},
    'button': {'width': 140, 'height': 76},
    'select': {'width': 152, 'height': 82},
    'checkbox': {'width': 152, 'height': 72},
    'radio': {'width': 152, 'height': 72},
    'link': {'width': 144, 'height': 68},
    'tab': {'width': 142, 'height': 66},
    'menuitem': {'width': 150, 'height': 68},
    'clickable': {'width': 150, 'height': 68},
    'file': {'width': 160, 'height': 76},
    'iframe': {'width': 232, 'height': 176},
}

PAGE_NODE_LAYOUT = {
    'header_height': 58,
    'footer_height': 34,
    'padding_x': 20,
    'padding_y': 16,
}

FLOW_COMPONENT_GRID = {
    'cell_width': 240,
    'cell_height': 150,
    'iframe_cell_width': 300,
    'iframe_cell_height': 230,
    'min_width': 420,
    'min_height': 450,
    'max_columns': 6,
}


def normalize_recording_scalar(value, max_length=None):
    if value is None:
        return ''
    if isinstance(value, bool):
        text = 'true' if value else 'false'
    elif isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = normalize_snapshot_inline_text(text)
    return text[:max_length] if max_length is not None else text


def normalize_optional_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_version_id(value):
    if value in (None, '', 'all'):
        return None
    return normalize_optional_int(value)


def normalize_module_metadata(data):
    if not isinstance(data, dict):
        data = {}

    project_id = normalize_optional_int(data.get('project_id'))
    module_id = normalize_optional_int(data.get('module_id'))
    module_name = normalize_recording_scalar(data.get('module_name'), 200)
    module_path = normalize_recording_scalar(data.get('module_path'), 500)
    version_id = normalize_version_id(data.get('version_id'))
    version_name = normalize_recording_scalar(data.get('version_name'), 200)

    if module_id is not None:
        category = ManualTestCaseCategory.objects.select_related('project', 'parent').filter(id=module_id).first()
        if category:
            module_name = module_name or category.name
            module_path = module_path or build_manual_category_path(category)
            project_id = project_id or category.project_id
    if version_id is not None and not version_name:
        version = Version.objects.filter(id=version_id).first()
        if version:
            version_name = version.name

    module = {}
    if project_id is not None:
        module['project_id'] = project_id
    if module_id is not None:
        module['module_id'] = module_id
    if version_id is not None:
        module['version_id'] = version_id
    if version_name:
        module['version_name'] = version_name
    if module_name:
        module['module_name'] = module_name
    if module_path:
        module['module_path'] = module_path
    return module


def normalize_module_path_filter(value):
    return normalize_recording_system_page_path(value)


def build_descendant_module_paths(module_id=None, module_path=''):
    normalized_path = normalize_module_path_filter(module_path)
    paths = set([normalized_path] if normalized_path else [])

    if module_id is None:
        return paths

    root = ManualTestCaseCategory.objects.filter(id=module_id).first()
    if not root:
        return paths

    children_by_parent = {}
    for category in ManualTestCaseCategory.objects.filter(project_id=root.project_id).only('id', 'parent_id', 'name', 'project_id'):
        children_by_parent.setdefault(category.parent_id, []).append(category)

    stack = [(root, build_manual_category_path(root))]
    while stack:
        category, path = stack.pop()
        normalized_child_path = normalize_module_path_filter(path)
        if normalized_child_path:
            paths.add(normalized_child_path)
        for child in children_by_parent.get(category.id, []):
            child_path = f'{path} / {child.name}' if path else normalize_recording_scalar(child.name, 200)
            stack.append((child, child_path))
    return paths


def build_descendant_module_ids(module_id=None):
    if module_id is None:
        return []

    root = ManualTestCaseCategory.objects.filter(id=module_id).first()
    if not root:
        return [module_id]

    ids = [root.id]
    parent_ids = [root.id]
    while parent_ids:
        child_ids = list(ManualTestCaseCategory.objects.filter(parent_id__in=parent_ids).values_list('id', flat=True))
        if not child_ids:
            break
        ids.extend(child_ids)
        parent_ids = child_ids
    return ids


def build_json_module_scope_q(
    request,
    module_id=None,
    module_path='',
    module_name='',
    project_id=None,
    version_id=None,
    flow_prefix='metadata__module',
    recording_prefix=None,
):
    include_descendants = parse_boolean_value(request.query_params.get('include_descendants'), default=False)
    q = models.Q()

    prefixes = [flow_prefix]
    if recording_prefix:
        prefixes.append(recording_prefix)

    if module_id is not None:
        ids = build_descendant_module_ids(module_id) if include_descendants else [module_id]
        for prefix in prefixes:
            q |= models.Q(**{f'{prefix}__module_id__in': ids})

    normalized_module_path = normalize_module_path_filter(module_path)
    module_paths = build_descendant_module_paths(module_id=module_id, module_path=normalized_module_path) if include_descendants else set()
    if normalized_module_path:
        module_paths.add(normalized_module_path)
    if module_paths:
        for prefix in prefixes:
            for path in module_paths:
                q |= models.Q(**{f'{prefix}__module_path': path})
                if include_descendants:
                    q |= models.Q(**{f'{prefix}__module_path__startswith': f'{path} / '})

    if module_name:
        for prefix in prefixes:
            q |= models.Q(**{f'{prefix}__module_name': module_name})

    if project_id is not None:
        project_q = models.Q()
        for prefix in prefixes:
            project_q |= models.Q(**{f'{prefix}__project_id': project_id})
        q = q & project_q if q else project_q

    if version_id is not None:
        version_q = models.Q()
        for prefix in prefixes:
            version_q |= models.Q(**{f'{prefix}__version_id': version_id})
        q = q & version_q if q else version_q

    return q


def build_automation_script_module_scope_q(
    request,
    module_id=None,
    module_path='',
    module_name='',
    project_id=None,
    version_id=None,
):
    include_descendants = parse_boolean_value(request.query_params.get('include_descendants'), default=False)
    scope_q = models.Q()

    if module_id is not None:
        ids = build_descendant_module_ids(module_id) if include_descendants else [module_id]
        scope_q |= models.Q(module_id__in=ids) | models.Q(module__module_id__in=ids)

    normalized_module_path = normalize_module_path_filter(module_path)
    module_paths = build_descendant_module_paths(
        module_id=module_id,
        module_path=normalized_module_path,
    ) if include_descendants else set()
    if normalized_module_path:
        module_paths.add(normalized_module_path)
    for path in module_paths:
        scope_q |= models.Q(module_path=path) | models.Q(module__module_path=path)
        if include_descendants:
            scope_q |= (
                models.Q(module_path__startswith=f'{path} / ') |
                models.Q(module__module_path__startswith=f'{path} / ')
            )

    if module_name:
        scope_q |= models.Q(module_name=module_name) | models.Q(module__module_name=module_name)

    filter_q = scope_q
    if project_id is not None:
        project_q = models.Q(project_id=project_id) | models.Q(module__project_id=project_id)
        filter_q = filter_q & project_q if filter_q else project_q
    if version_id is not None:
        version_q = models.Q(version_id=version_id) | models.Q(module__version_id=version_id)
        filter_q = filter_q & version_q if filter_q else version_q
    return filter_q


def snapshot_module_matches(
    entry,
    module_id_filter=None,
    module_path_filter='',
    module_name_filter='',
    project_id_filter=None,
    include_descendants=False,
    descendant_module_ids=None,
):
    module_id = normalize_optional_int(entry.get('module_id'))
    module_name = normalize_recording_scalar(entry.get('module_name'), 200).lower()
    module_path = normalize_recording_scalar(entry.get('module_path'), 500).lower()
    project_id = normalize_optional_int(entry.get('project_id'))

    if project_id_filter is not None and project_id != project_id_filter:
        return False

    filters = []
    if module_id_filter is not None:
        if include_descendants:
            descendant_ids = (
                descendant_module_ids
                if descendant_module_ids is not None
                else set(build_descendant_module_ids(module_id_filter))
            )
            filters.append(module_id in descendant_ids)
        else:
            filters.append(module_id == module_id_filter)
    if module_path_filter:
        normalized_path = module_path_filter.lower()
        filters.append(module_path == normalized_path or (include_descendants and module_path.startswith(f'{normalized_path} / ')))
    if module_name_filter:
        filters.append(module_name == module_name_filter)
    return any(filters) if filters else True


def snapshot_version_matches(entry, version_id_filter=None):
    if version_id_filter is None:
        return True
    return normalize_optional_int(entry.get('version_id')) == version_id_filter


def build_manual_category_path(category):
    if not category:
        return ''

    names = []
    current = category
    guard = 0
    while current is not None and guard < 50:
        name = normalize_recording_scalar(getattr(current, 'name', ''), 200)
        if name:
            names.append(name)
        current = getattr(current, 'parent', None)
        guard += 1

    return ' / '.join(reversed(names))


def apply_recording_module_metadata(metadata, module):
    metadata = dict(metadata or {})
    for key in ('project_id', 'module_id', 'module_name', 'module_path', 'version_id', 'version_name'):
        metadata.pop(key, None)

    if module:
        metadata['module'] = dict(module)
        metadata['recording_scope'] = {
            'project_id': module.get('project_id'),
            'version_id': module.get('version_id'),
            'version_name': module.get('version_name') or '',
            'module_id': module.get('module_id'),
            'module_name': module.get('module_name') or '',
            'module_path': module.get('module_path') or module.get('module_name') or '',
        }
    else:
        metadata.pop('module', None)
        metadata.pop('recording_scope', None)
    return metadata


def apply_module_metadata(metadata, module):
    metadata = dict(metadata or {})
    for key in ('project_id', 'module_id', 'module_name', 'module_path', 'version_id', 'version_name'):
        metadata.pop(key, None)

    if module:
        metadata['module'] = dict(module)
    else:
        metadata.pop('module', None)
    return metadata


def apply_flow_copy_version_metadata(metadata, version):
    metadata = dict(metadata or {})
    if not version:
        metadata.pop('version_id', None)
        metadata.pop('version_name', None)
        module = dict(metadata.get('module') or {})
        module.pop('version_id', None)
        module.pop('version_name', None)
        if module:
            metadata['module'] = module
        return metadata

    metadata['version_id'] = version.id
    metadata['version_name'] = version.name
    module = dict(metadata.get('module') or {})
    module['version_id'] = version.id
    module['version_name'] = version.name
    metadata['module'] = module
    return metadata


def extract_module_payload(data):
    if not isinstance(data, dict):
        return {}

    payload = {}
    module = data.get('module')
    if isinstance(module, dict):
        payload.update(module)
    for key in ('project_id', 'module_id', 'module_name', 'module_path', 'version_id', 'version_name'):
        if key in data:
            payload[key] = data.get(key)
    return normalize_module_metadata(payload)


def normalize_match_text(value):
    return normalize_recording_scalar(value).casefold()


def normalize_snapshot_content_for_hash(content):
    normalized = str(content or '').replace('\r\n', '\n').replace('\r', '\n')
    normalized = '\n'.join(line.rstrip() for line in normalized.split('\n')).strip()
    return normalized


def build_snapshot_content_hash(content):
    normalized = normalize_snapshot_content_for_hash(content)
    if not normalized:
        return ''
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def normalize_snapshot_content_for_interaction_hash(content):
    normalized = sanitize_snapshot_content(str(content or '')).replace('\r\n', '\n').replace('\r', '\n')
    if not normalized.strip():
        return ''

    lines = []
    ignored_prefixes = (
        '- alert:',
        '  - alert:',
        '- img',
        '  - img',
    )
    ignored_fragments = (
        '登录成功',
        '加载成功',
        '操作成功',
        '保存成功',
        '更新成功',
    )
    for raw_line in normalized.split('\n'):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('# testhub-recorded-elements'):
            break
        if any(stripped.startswith(prefix) for prefix in ignored_prefixes):
            continue
        if any(fragment in stripped for fragment in ignored_fragments):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()


def build_snapshot_interaction_hash(content):
    normalized = normalize_snapshot_content_for_interaction_hash(content)
    if not normalized:
        return ''
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def build_recording_step_snapshot_filename(step):
    return f'recording-{step.session.session_id}-step-{step.step_number:04d}.yml'


def read_snapshot_content(filename):
    if not filename:
        return '', ''
    try:
        normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
        with open(file_path, 'r', encoding='utf-8') as snapshot_file:
            return normalized_filename, sanitize_snapshot_content(snapshot_file.read())
    except (FileNotFoundError, ValueError, OSError):
        return '', ''


def resolve_recording_step_snapshot(step):
    filename, content = read_snapshot_content(step.snapshot_filename)
    if filename:
        return filename, content

    return read_snapshot_content(build_recording_step_snapshot_filename(step))


def normalize_recording_page_url_for_identity(value):
    normalized = normalize_recording_scalar(value)
    if not normalized:
        return ''
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        base, _, fragment = normalized.partition('#')
        base = base.split('?', 1)[0].rstrip('/')
        hash_route = fragment.split('?', 1)[0].split('&', 1)[0].rstrip('/')
        return f'{base}#{hash_route}'.rstrip('#').casefold()

    fragment_path = ''
    if parsed.fragment.startswith(('/', '!/')):
        fragment_path = parsed.fragment.split('?', 1)[0].split('&', 1)[0].rstrip('/')
    normalized_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', fragment_path))
    return normalized_url.rstrip('#').casefold()


def normalize_recording_page_url_for_group(value):
    return normalize_recording_page_url_for_identity(value)


def is_recording_login_page_url(value):
    normalized = normalize_recording_scalar(value)
    if not normalized:
        return False
    candidates = []
    try:
        parsed = urlsplit(normalized)
        candidates.append(parsed.path)
        if parsed.fragment:
            candidates.append(parsed.fragment.split('?', 1)[0].split('&', 1)[0])
    except ValueError:
        base, _, fragment = normalized.partition('#')
        candidates.append(base.split('?', 1)[0])
        candidates.append(fragment.split('?', 1)[0].split('&', 1)[0])

    for candidate in candidates:
        path = normalize_recording_scalar(candidate).strip().rstrip('/').casefold()
        if path == '/login' or path.endswith('/login'):
            return True
    return False


def build_recording_page_identity(step):
    return ':'.join([
        normalize_recording_page_url_for_group(step.page_url),
        normalize_match_text(step.page_title),
    ])


def is_same_recording_page_url(left, right):
    left_normalized = normalize_recording_page_url_for_group(left)
    right_normalized = normalize_recording_page_url_for_group(right)
    return bool(left_normalized and right_normalized and left_normalized == right_normalized)


def normalize_recording_system_page_path(value):
    normalized = normalize_recording_scalar(value, 500)
    if not normalized:
        return ''
    parts = [
        part.strip()
        for part in re.split(r'\s*/\s*|[>＞]+|\\+', normalized)
        if part and part.strip()
    ]
    return ' / '.join(parts)


def get_recording_session_module_metadata(session):
    metadata = getattr(session, 'metadata', {}) if session else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
    return {
        'project_id': module.get('project_id') or metadata.get('project_id') or '',
        'version_id': module.get('version_id') or metadata.get('version_id') or '',
        'version_name': module.get('version_name') or metadata.get('version_name') or '',
        'module_id': module.get('module_id') or metadata.get('module_id') or '',
        'module_name': module.get('module_name') or metadata.get('module_name') or '',
        'module_path': module.get('module_path') or metadata.get('module_path') or '',
    }


def get_recording_allure_report_relative_dir(session_id):
    safe_session_id = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(session_id or '').strip()) or 'unknown'
    return os.path.join('allure-reports', f'recording_{safe_session_id}')


def get_recording_allure_results_relative_dir(session_id):
    safe_session_id = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(session_id or '').strip()) or 'unknown'
    return os.path.join('allure-results', f'recording_{safe_session_id}')


def build_media_url(relative_path):
    normalized = str(relative_path or '').replace('\\', '/').lstrip('/')
    return f'{settings.MEDIA_URL.rstrip("/")}/{normalized}'


def get_allure_command_path():
    executable = 'allure.bat' if os.name == 'nt' else 'allure'
    candidates = [
        os.path.join(settings.BASE_DIR, 'allure', 'bin', executable),
        os.path.join('/usr/local/bin', 'allure'),
        os.path.join('/usr/bin', 'allure'),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def to_allure_time_ms(value=None):
    if value is None:
        dt_value = timezone.now()
    else:
        dt_value = value
    try:
        if timezone.is_naive(dt_value):
            dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())
        return int(dt_value.timestamp() * 1000)
    except Exception:
        return int(time.time() * 1000)


def build_allure_attachment_source(session_id, step_number, suffix):
    safe_session_id = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(session_id or '').strip()) or 'recording'
    return f'{safe_session_id}-step-{int(step_number or 0):04d}-{suffix}'


def write_allure_attachment(results_dir, source, content, *, binary=False):
    os.makedirs(results_dir, exist_ok=True)
    attachment_path = os.path.join(results_dir, source)
    if binary:
        with open(attachment_path, 'wb') as attachment_file:
            attachment_file.write(content)
    else:
        with open(attachment_path, 'w', encoding='utf-8') as attachment_file:
            attachment_file.write(str(content or ''))
    return source


def resolve_media_file_path(relative_or_url):
    path = normalize_recording_scalar(relative_or_url)
    if not path:
        return ''
    if path.startswith(('http://', 'https://')):
        return ''
    media_url = settings.MEDIA_URL or '/media/'
    if path.startswith(media_url):
        path = path[len(media_url):]
    path = path.lstrip('/\\')
    absolute_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT, path))
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    if not absolute_path.startswith(media_root):
        return ''
    return absolute_path if os.path.exists(absolute_path) else ''


def build_recording_step_display_name(step):
    element = step.element if isinstance(step.element, dict) else {}
    label = (
        element.get('text')
        or element.get('ariaLabel')
        or element.get('aria_label')
        or element.get('placeholder')
        or element.get('name')
        or element.get('id')
        or element.get('tag')
        or ''
    )
    action = normalize_recording_scalar(step.action_type, 40) or 'action'
    if label:
        return f'步骤 {step.step_number}: {action} {normalize_recording_scalar(label, 80)}'
    return f'步骤 {step.step_number}: {action}'


def build_recording_step_parameters(step):
    element = step.element if isinstance(step.element, dict) else {}
    selectors = step.selectors if isinstance(step.selectors, list) else []
    parameters = [
        {'name': '动作类型', 'value': normalize_recording_scalar(step.action_type)},
        {'name': '操作值', 'value': normalize_recording_scalar(step.action_value) or '-'},
        {'name': '页面标题', 'value': normalize_recording_scalar(step.page_title) or '-'},
        {'name': '页面地址', 'value': normalize_recording_scalar(step.page_url) or '-'},
        {'name': '快照文件', 'value': normalize_recording_scalar(step.snapshot_filename) or build_recording_step_snapshot_filename(step)},
    ]
    for key, label in (
        ('tag', '元素标签'),
        ('text', '元素文本'),
        ('role', '元素角色'),
        ('id', '元素ID'),
        ('placeholder', '占位文本'),
    ):
        value = normalize_recording_scalar(element.get(key), 500)
        if value:
            parameters.append({'name': label, 'value': value})
    if selectors:
        parameters.append({'name': '选择器数量', 'value': str(len(selectors))})
    return parameters


def build_recording_step_result(session, step, results_dir, start_ms):
    uuid_text = f'{session.session_id}-{step.step_number:04d}'
    attachments = []
    snapshot_filename, snapshot_content = resolve_recording_step_snapshot(step)
    if snapshot_content:
        source = build_allure_attachment_source(session.session_id, step.step_number, 'snapshot.yml')
        write_allure_attachment(results_dir, source, snapshot_content)
        attachments.append({
            'name': 'Playwright快照',
            'source': source,
            'type': 'text/yaml',
        })

    if isinstance(step.raw_event, dict) and step.raw_event:
        source = build_allure_attachment_source(session.session_id, step.step_number, 'raw-event.json')
        write_allure_attachment(results_dir, source, json.dumps(step.raw_event, ensure_ascii=False, indent=2))
        attachments.append({
            'name': '原始事件',
            'source': source,
            'type': 'application/json',
        })

    screenshot_path = resolve_media_file_path(step.screenshot_path)
    if screenshot_path:
        try:
            with open(screenshot_path, 'rb') as screenshot_file:
                source = build_allure_attachment_source(session.session_id, step.step_number, 'screenshot.png')
                write_allure_attachment(results_dir, source, screenshot_file.read(), binary=True)
                attachments.append({
                    'name': '截图',
                    'source': source,
                    'type': 'image/png',
                })
        except OSError:
            pass

    step_start = to_allure_time_ms(step.created_at) if step.created_at else start_ms + step.step_number * 10
    step_stop = max(step_start + 1, step_start + 10)
    module = get_recording_session_module_metadata(session)
    labels = [
        {'name': 'suite', 'value': session.name or session.session_id},
        {'name': 'parentSuite', 'value': module.get('module_path') or module.get('module_name') or '录制结果管理'},
        {'name': 'subSuite', 'value': '录制步骤'},
        {'name': 'package', 'value': 'testhub.playwright_recording'},
        {'name': 'testClass', 'value': session.session_id},
        {'name': 'framework', 'value': 'BearAI Playwright Recording'},
        {'name': 'language', 'value': 'python'},
    ]
    return {
        'uuid': uuid_text,
        'historyId': hashlib.sha256(f'{session.session_id}:{step.step_number}'.encode('utf-8')).hexdigest(),
        'name': build_recording_step_display_name(step),
        'fullName': f'{session.session_id}.{step.step_number:04d}',
        'status': 'passed',
        'stage': 'finished',
        'description': '\n'.join([
            f'动作类型: {normalize_recording_scalar(step.action_type) or "-"}',
            f'操作值: {normalize_recording_scalar(step.action_value) or "-"}',
            f'页面: {normalize_recording_scalar(step.page_title) or normalize_recording_scalar(step.page_url) or "-"}',
            f'快照: {snapshot_filename or "-"}',
        ]),
        'parameters': build_recording_step_parameters(step),
        'attachments': attachments,
        'labels': labels,
        'links': [{'name': '目标页面', 'type': 'custom', 'url': step.page_url}] if step.page_url else [],
        'start': step_start,
        'stop': step_stop,
    }


def build_recording_summary_html(session, steps, summary, report_url):
    module = get_recording_session_module_metadata(session)
    generated_at = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
    status_label = dict(PlaywrightRecordingSession.STATUS_CHOICES).get(session.status, session.status or '-')
    action_rows = []
    for step in steps[:300]:
        element = step.element if isinstance(step.element, dict) else {}
        element_label = normalize_recording_scalar(
            element.get('text')
            or element.get('ariaLabel')
            or element.get('placeholder')
            or element.get('id')
            or element.get('tag')
            or '-',
            200,
        )
        snapshot_name, _ = resolve_recording_step_snapshot(step)
        action_rows.append(
            '<tr>'
            f'<td>{step.step_number}</td>'
            f'<td>{html.escape(normalize_recording_scalar(step.action_type) or "-")}</td>'
            f'<td>{html.escape(normalize_recording_scalar(step.action_value) or "-")}</td>'
            f'<td>{html.escape(element_label or "-")}</td>'
            f'<td>{html.escape(normalize_recording_scalar(step.page_title) or "-")}</td>'
            f'<td>{html.escape(snapshot_name or "-")}</td>'
            '</tr>'
        )

    if not action_rows:
        action_rows.append('<tr><td colspan="6" class="empty">暂无录制步骤</td></tr>')

    truncated_note = ''
    if len(steps) > 300:
        truncated_note = f'<div class="note">步骤明细仅展示前 300 条，完整数据请查看 Allure 报告。</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>录制 Allure 报告 - {html.escape(session.name or session.session_id)}</title>
  <style>
    body {{ margin: 0; background: #f6f8fb; color: #1f2937; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .header {{ background: #1f2937; color: #fff; padding: 28px 36px; }}
    .header h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 650; }}
    .header p {{ margin: 4px 0; color: #d1d5db; }}
    .actions {{ margin-top: 16px; }}
    .button {{ display: inline-block; padding: 9px 14px; border-radius: 6px; background: #2563eb; color: #fff; text-decoration: none; font-weight: 600; }}
    .container {{ padding: 24px 36px 40px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 14px; margin-bottom: 18px; }}
    .metric {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }}
    .metric .num {{ font-size: 26px; font-weight: 700; }}
    .metric .label {{ margin-top: 4px; color: #6b7280; font-size: 13px; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 18px; margin-bottom: 18px; }}
    .info {{ display: grid; grid-template-columns: 130px 1fr; gap: 8px 12px; }}
    .info dt {{ color: #6b7280; }}
    .info dd {{ margin: 0; word-break: break-all; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; color: #374151; font-weight: 650; }}
    .empty {{ text-align: center; color: #6b7280; }}
    .note {{ margin: 8px 0 0; color: #92400e; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{html.escape(session.name or session.session_id)}</h1>
    <p>录制会话：{html.escape(session.session_id)} · 状态：{html.escape(status_label)} · 生成时间：{html.escape(generated_at)}</p>
    <p>目标地址：{html.escape(session.target_url or "-")}</p>
    <div class="actions"><a class="button" href="{html.escape(report_url)}" target="_blank" rel="noopener">打开完整 Allure 报告</a></div>
  </div>
  <div class="container">
    <div class="grid">
      <div class="metric"><div class="num">{summary['total']}</div><div class="label">总步骤</div></div>
      <div class="metric"><div class="num">{summary['passed']}</div><div class="label">已通过</div></div>
      <div class="metric"><div class="num">{summary['failed']}</div><div class="label">失败</div></div>
      <div class="metric"><div class="num">{summary['attachment_count']}</div><div class="label">附件</div></div>
    </div>
    <div class="card">
      <dl class="info">
        <dt>模块路径</dt><dd>{html.escape(module.get('module_path') or module.get('module_name') or '-')}</dd>
        <dt>浏览器</dt><dd>{html.escape(session.browser_type or '-')}</dd>
        <dt>录制方式</dt><dd>{html.escape(get_recording_method_label(session.recording_method) or '-')}</dd>
        <dt>开始时间</dt><dd>{html.escape(timezone.localtime(session.started_at).strftime('%Y-%m-%d %H:%M:%S') if session.started_at else '-')}</dd>
        <dt>结束时间</dt><dd>{html.escape(timezone.localtime(session.stopped_at).strftime('%Y-%m-%d %H:%M:%S') if session.stopped_at else '-')}</dd>
      </dl>
    </div>
    <div class="card">
      <h2>录制步骤明细</h2>
      <table>
        <thead><tr><th>#</th><th>动作</th><th>操作值</th><th>元素</th><th>页面</th><th>快照</th></tr></thead>
        <tbody>{''.join(action_rows)}</tbody>
      </table>
      {truncated_note}
    </div>
  </div>
</body>
</html>
"""


def generate_recording_allure_report(session, request=None):
    steps = list(session.steps.order_by('step_number', 'id'))
    if not steps:
        raise ValidationError('录制会话没有可生成报告的步骤')

    results_relative_dir = get_recording_allure_results_relative_dir(session.session_id)
    report_relative_dir = get_recording_allure_report_relative_dir(session.session_id)
    results_dir = os.path.join(settings.MEDIA_ROOT, results_relative_dir)
    report_dir = os.path.join(settings.MEDIA_ROOT, report_relative_dir)
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    start_ms = to_allure_time_ms(session.started_at)
    child_uuids = []
    attachment_count = 0
    for step in steps:
        result = build_recording_step_result(session, step, results_dir, start_ms)
        child_uuids.append(result['uuid'])
        attachment_count += len(result.get('attachments') or [])
        result_path = os.path.join(results_dir, f'{result["uuid"]}-result.json')
        with open(result_path, 'w', encoding='utf-8') as result_file:
            json.dump(result, result_file, ensure_ascii=False, indent=2)

    container = {
        'uuid': f'{session.session_id}-container',
        'name': session.name or session.session_id,
        'children': child_uuids,
        'description': f'BearAI录制会话 {session.session_id}',
        'start': start_ms,
        'stop': to_allure_time_ms(session.stopped_at or timezone.now()),
    }
    with open(os.path.join(results_dir, f'{session.session_id}-container.json'), 'w', encoding='utf-8') as container_file:
        json.dump(container, container_file, ensure_ascii=False, indent=2)

    summary = {
        'total': len(steps),
        'passed': len(steps),
        'failed': 0,
        'attachment_count': attachment_count,
    }
    executor = {
        'name': 'BearAI',
        'type': 'testhub-playwright-recording',
        'url': request.build_absolute_uri('/') if request else '',
    }
    with open(os.path.join(results_dir, 'executor.json'), 'w', encoding='utf-8') as executor_file:
        json.dump(executor, executor_file, ensure_ascii=False, indent=2)
    with open(os.path.join(results_dir, 'environment.properties'), 'w', encoding='utf-8') as env_file:
        env_file.write('\n'.join([
            f'Session={session.session_id}',
            f'TargetUrl={session.target_url or ""}',
            f'Browser={session.browser_type or ""}',
            f'RecordingMethod={session.recording_method or ""}',
        ]))

    allure_cmd = get_allure_command_path()
    allure_generated = False
    allure_error = ''
    if allure_cmd:
        try:
            subprocess.run(
                [allure_cmd, 'generate', results_dir, '--clean', '--output', report_dir],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            allure_generated = os.path.exists(os.path.join(report_dir, 'index.html'))
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            allure_error = str(exc)

    if not allure_generated:
        static_dir = os.path.join(settings.MEDIA_ROOT, 'allure-static')
        if os.path.exists(static_dir):
            for item in os.listdir(static_dir):
                source = os.path.join(static_dir, item)
                destination = os.path.join(report_dir, item)
                if os.path.isdir(source):
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, destination)
        fallback_index = os.path.join(report_dir, 'index.html')
        if not os.path.exists(fallback_index):
            with open(fallback_index, 'w', encoding='utf-8') as index_file:
                index_file.write(build_recording_summary_html(session, steps, summary, 'summary.html'))

    index_url = build_media_url(os.path.join(report_relative_dir, 'index.html'))
    summary_url = build_media_url(os.path.join(report_relative_dir, 'summary.html'))
    summary_html = build_recording_summary_html(session, steps, summary, 'index.html')
    with open(os.path.join(report_dir, 'summary.html'), 'w', encoding='utf-8') as summary_file:
        summary_file.write(summary_html)

    metadata = dict(session.metadata or {})
    metadata['allure_report'] = {
        'generated_at': timezone.now().isoformat(),
        'summary_url': summary_url,
        'report_url': index_url,
        'results_dir': results_relative_dir.replace('\\', '/'),
        'report_dir': report_relative_dir.replace('\\', '/'),
        'step_count': len(steps),
        'attachment_count': attachment_count,
        'allure_generated': allure_generated,
        'allure_error': allure_error,
    }
    session.metadata = metadata
    session.save(update_fields=['metadata', 'updated_at'])

    return {
        'message': 'Allure报告生成成功' if allure_generated else 'Allure报告摘要已生成，完整报告使用静态兜底页面',
        'summary': summary,
        'summary_url': summary_url,
        'report_url': index_url,
        'results_dir': results_relative_dir.replace('\\', '/'),
        'report_dir': report_relative_dir.replace('\\', '/'),
        'allure_generated': allure_generated,
        'allure_error': allure_error,
    }


def get_visual_flow_module_metadata(flow):
    metadata = getattr(flow, 'metadata', {}) if flow else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
    if not module and getattr(flow, 'recording_session', None):
        return get_recording_session_module_metadata(flow.recording_session)
    return {
        'project_id': module.get('project_id') or metadata.get('project_id') or '',
        'version_id': module.get('version_id') or metadata.get('version_id') or '',
        'version_name': module.get('version_name') or metadata.get('version_name') or '',
        'module_id': module.get('module_id') or metadata.get('module_id') or '',
        'module_name': module.get('module_name') or metadata.get('module_name') or '',
        'module_path': module.get('module_path') or metadata.get('module_path') or '',
    }


def get_nested_recording_value(data, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return ''
        current = current.get(key)
    return current


def build_recording_system_page_info(session, step):
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    agent_event = get_nested_recording_value(raw_event, 'agent_payload', 'event')
    agent_event = agent_event if isinstance(agent_event, dict) else {}
    module = get_recording_session_module_metadata(session)

    event_path = next((
        normalize_recording_system_page_path(value)
        for value in (
            raw_event.get('system_page_path'),
            raw_event.get('page_menu_path'),
            raw_event.get('menu_path'),
            raw_event.get('module_path'),
            raw_event.get('recording_scope_path'),
            get_nested_recording_value(raw_event, 'recording_scope', 'module_path'),
            get_nested_recording_value(raw_event, 'recording_scope', 'path'),
            get_nested_recording_value(raw_event, 'context', 'module_path'),
            get_nested_recording_value(raw_event, 'context', 'page_path'),
            agent_event.get('system_page_path'),
            agent_event.get('page_menu_path'),
            agent_event.get('menu_path'),
            agent_event.get('module_path'),
        )
        if normalize_recording_system_page_path(value)
    ), '')
    session_path = normalize_recording_system_page_path(module.get('module_path'))
    session_page_matches_step = is_same_recording_page_url(step.page_url, getattr(session, 'target_url', ''))
    page_url = normalize_recording_page_url_for_identity(step.page_url)
    page_title = normalize_recording_scalar(step.page_title, 200)
    event_page_name = (
        normalize_recording_scalar(raw_event.get('system_page_name'), 200) or
        normalize_recording_scalar(raw_event.get('page_menu_name'), 200) or
        normalize_recording_scalar(raw_event.get('menu_name'), 200) or
        normalize_recording_scalar(raw_event.get('module_name'), 200) or
        normalize_recording_scalar(get_nested_recording_value(raw_event, 'recording_scope', 'module_name'), 200) or
        normalize_recording_scalar(get_nested_recording_value(raw_event, 'context', 'system_page_name'), 200) or
        normalize_recording_scalar(get_nested_recording_value(raw_event, 'context', 'page_name'), 200) or
        normalize_recording_scalar(get_nested_recording_value(raw_event, 'context', 'module_name'), 200) or
        normalize_recording_scalar(agent_event.get('system_page_name'), 200) or
        normalize_recording_scalar(agent_event.get('page_menu_name'), 200) or
        normalize_recording_scalar(agent_event.get('menu_name'), 200) or
        normalize_recording_scalar(agent_event.get('module_name'), 200) or
        normalize_recording_scalar(get_nested_recording_value(agent_event, 'context', 'module_name'), 200)
    )
    if event_path:
        page_name = event_page_name or page_title or page_url or f'椤甸潰 {step.step_number}'
        identity_parts = ['system-page', normalize_match_text(event_path)]
        identity = ':'.join(part for part in identity_parts if part)
        return {
            'identity': identity or f'step:{step.step_number}',
            'name': page_name,
            'path': event_path,
            'source': 'step_event',
            'project_id': (
                raw_event.get('project_id') or
                get_nested_recording_value(raw_event, 'recording_scope', 'project_id') or
                get_nested_recording_value(raw_event, 'context', 'project_id') or
                module.get('project_id') or
                ''
            ),
            'module_id': (
                raw_event.get('module_id') or
                get_nested_recording_value(raw_event, 'recording_scope', 'module_id') or
                get_nested_recording_value(raw_event, 'context', 'module_id') or
                module.get('module_id') or
                ''
            ),
            'module_name': event_page_name or module.get('module_name') or page_name,
        }

    login_url = (
        normalize_recording_scalar(raw_event.get('url')) or
        normalize_recording_scalar(get_nested_recording_value(raw_event, 'frame', 'url')) or
        normalize_recording_scalar(step.page_url)
    )
    if is_recording_login_page_url(login_url) or is_recording_login_page_url(step.page_url):
        identity_url = normalize_recording_page_url_for_identity(login_url or step.page_url) or 'login'
        login_page_name = page_title if page_title and 'login' not in page_title.casefold() else '登录页'
        return {
            'identity': f'url:{normalize_match_text(identity_url)}',
            'name': login_page_name or '登录页',
            'path': normalize_recording_scalar(login_url or step.page_url, 500) or '/login',
            'source': 'login',
            'project_id': module.get('project_id') or '',
            'module_id': '',
            'module_name': '登录页',
        }

    page_scope_path = event_path or (session_path if session_page_matches_step else '')
    session_module_name = normalize_recording_scalar(module.get('module_name'), 200) if session_page_matches_step else ''
    page_name = (
        normalize_recording_scalar(raw_event.get('system_page_name'), 200) or
        normalize_recording_scalar(raw_event.get('page_menu_name'), 200) or
        normalize_recording_scalar(raw_event.get('menu_name'), 200) or
        normalize_recording_scalar(raw_event.get('module_name'), 200) or
        session_module_name or
        page_title or
        page_url or
        f'页面 {step.step_number}'
    )

    if page_scope_path:
        identity_parts = ['system-page', normalize_match_text(page_scope_path)]
        identity = ':'.join(part for part in identity_parts if part)
        return {
            'identity': identity or f'step:{step.step_number}',
            'name': page_name,
            'path': page_scope_path,
            'source': 'step_event' if event_path else 'recording_scope',
            'project_id': module.get('project_id') or '',
            'module_id': module.get('module_id') or '',
            'module_name': module.get('module_name') or page_name,
        }

    if page_url:
        identity = f'url:{normalize_match_text(page_url)}'
        source = 'url'
    else:
        identity = f'title:{normalize_match_text(page_title)}'
        source = 'title'
    return {
        'identity': identity or f'step:{step.step_number}',
        'name': page_name,
        'path': page_scope_path or page_title or normalize_recording_scalar(step.page_url, 500) or '',
        'source': source,
        'project_id': module.get('project_id') or '',
        'module_id': module.get('module_id') or '',
        'module_name': module.get('module_name') or '',
    }


def get_recording_step_action(step):
    return normalize_recording_scalar(getattr(step, 'action_type', '')).lower()


def get_recording_step_action_value(step):
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    if 'value' in raw_event:
        return normalize_recording_scalar(raw_event.get('value'))
    if 'selectedValue' in raw_event:
        return normalize_recording_scalar(raw_event.get('selectedValue'))
    return parse_recording_action_value(getattr(step, 'action_value', ''))


def get_recording_step_element_value(step):
    element = step.element if isinstance(step.element, dict) else {}
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    raw_element = raw_event.get('element') if isinstance(raw_event.get('element'), dict) else {}
    for source in (raw_element, element):
        if 'value' in source:
            value = normalize_recording_scalar(source.get('value'))
            if value:
                return value
        if 'selectedValue' in source:
            value = normalize_recording_scalar(source.get('selectedValue'))
            if value:
                return value
    return ''


def get_recording_step_effective_page_url(step):
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    frame = raw_event.get('frame') if isinstance(raw_event.get('frame'), dict) else {}
    return (
        normalize_recording_scalar(frame.get('url')) or
        normalize_recording_scalar(raw_event.get('frame_url')) or
        normalize_recording_scalar(raw_event.get('url')) or
        normalize_recording_scalar(step.page_url)
    )


def build_recording_step_element_key(step):
    element = step.element if isinstance(step.element, dict) else {}
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    frame = raw_event.get('frame') if isinstance(raw_event.get('frame'), dict) else {}
    selectors = step.selectors if isinstance(step.selectors, list) else []
    selector_values = [
        normalize_recording_scalar(selector.get('value'))
        for selector in selectors
        if isinstance(selector, dict) and selector.get('value')
    ]
    locators = get_recorded_locator_values(element)
    key_parts = [
        normalize_recording_page_url_for_group(get_recording_step_effective_page_url(step)),
        normalize_recording_scalar(element.get('id') or locators.get('id')),
        normalize_recording_scalar(element.get('name') or locators.get('name')),
        normalize_recording_scalar(element.get('cssSelector') or locators.get('cssselector')),
        normalize_recording_scalar(element.get('xpath') or locators.get('xpath')),
        normalize_recording_scalar(element.get('tag') or locators.get('tagname')),
        normalize_recording_scalar(element.get('placeholder') or element.get('ariaLabel') or element.get('text')),
        '|'.join(selector_values[:4]),
    ]
    return '::'.join(normalize_match_text(part) for part in key_parts if part)


def mark_junk_step(results, step, reason, reason_label, group_key=''):
    if not step or step.id in results:
        return
    results[step.id] = {
        'step_id': step.id,
        'step_number': step.step_number,
        'reason': reason,
        'reason_label': reason_label,
        'group_key': group_key,
    }


def is_recording_step_editable_target(step):
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_match_text(element.get('role'))
    tag = normalize_match_text(element.get('tag') or element.get('tagName'))
    element_type = normalize_match_text(element.get('type'))
    return (
        tag in {'input', 'textarea'} or
        role in {'textbox', 'searchbox', 'combobox'} or
        element_type in {'text', 'password', 'email', 'number', 'search', 'tel', 'url'}
    )


def is_recording_step_plain_textbox_target(step):
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_match_text(element.get('role'))
    tag = normalize_match_text(element.get('tag') or element.get('tagName'))
    element_type = normalize_match_text(element.get('type'))
    class_name = normalize_match_text(element.get('className') or element.get('classname'))
    if role in {'combobox', 'listbox', 'option', 'button', 'checkbox', 'radio', 'switch', 'tab', 'menuitem'}:
        return False
    if tag in {'select', 'option', 'button', 'a', 'li', 'label'}:
        return False
    if 'el-select__input' in class_name:
        return False
    return (
        tag in {'textarea'} or
        (tag == 'input' and element_type not in {'button', 'submit', 'reset', 'checkbox', 'radio', 'file', 'hidden'}) or
        role in {'textbox', 'searchbox'} or
        element_type in {'text', 'password', 'email', 'number', 'search', 'tel', 'url'}
    )


def is_recording_step_meaningful_click_target(step):
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_match_text(element.get('role'))
    tag = normalize_match_text(element.get('tag') or element.get('tagName'))
    text = normalize_recording_scalar(
        element.get('text') or element.get('ariaLabel') or element.get('title') or element.get('placeholder'),
        160,
    )
    return (
        tag in {'button', 'a', 'li', 'label', 'select', 'option'} or
        role in {'button', 'link', 'tab', 'menuitem', 'option', 'checkbox', 'radio', 'switch', 'combobox', 'listbox'} or
        bool(text)
    )


def is_recording_step_command_button_click(step):
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_match_text(element.get('role'))
    tag = normalize_match_text(element.get('tag') or element.get('tagName'))
    text = normalize_recording_scalar(
        element.get('text') or element.get('ariaLabel') or element.get('title') or element.get('value'),
        80,
    )
    compact_text = re.sub(r'\s+', '', text)
    if not compact_text or len(compact_text) > 24:
        return False
    if tag != 'button' and role != 'button':
        return False
    command_keywords = {
        '确定', '确认', '保存', '提交', '登录', '查询', '搜索', '重置',
        '新增', '新建', '编辑', '删除', '下一页', '上一页', '首页', '尾页',
        'OK', 'Ok', 'ok', 'Save', 'Submit', 'Search', 'Login',
    }
    return any(keyword in compact_text for keyword in command_keywords)


def is_recording_step_generic_container_click(step):
    if get_recording_step_action(step) != 'click':
        return False
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_match_text(element.get('role'))
    tag = normalize_match_text(element.get('tag') or element.get('tagName'))
    if role or tag not in {'html', 'body', 'main', 'section', 'div'}:
        return False
    if any(normalize_recording_scalar(element.get(key), 120) for key in ('id', 'name', 'ariaLabel', 'title', 'placeholder', 'value')):
        return False

    text = normalize_recording_scalar(element.get('text'), 400)
    class_name = normalize_match_text(element.get('className') or element.get('classname'))
    rect = element.get('rect') if isinstance(element.get('rect'), dict) else {}
    width = float(rect.get('width') or 0)
    height = float(rect.get('height') or 0)
    area = width * height
    is_large_surface = (
        tag in {'html', 'body'} or
        width >= 600 or
        height >= 360 or
        area >= 220000
    )
    is_layout_class = any(token in class_name for token in (
        'board', 'container', 'layout', 'wrapper', 'content', 'sidebar', 'scrollbar'
    ))
    has_broad_text = len(text) >= 32 and len(set(re.split(r'\s+', text))) >= 4
    return is_large_surface and (tag in {'html', 'body'} or is_layout_class or has_broad_text)


def recording_step_snapshot_contains_element(step):
    _, content = resolve_recording_step_snapshot(step)
    if not content:
        return True
    original_content = str(content).split('# testhub-recorded-elements', 1)[0]
    parsed = parse_snapshot_content(original_content)
    interactive_elements = list(parsed.get('interactive_elements') or [])
    if not interactive_elements:
        return True
    recorded_element = build_recorded_snapshot_element(step)
    return any(
        snapshot_element_matches_step(snapshot_element, step, recorded_element)
        for snapshot_element in interactive_elements
    )


def identify_continuous_fill_junk_steps(steps, results):
    pending = []

    def flush_group():
        if len(pending) < 2:
            pending.clear()
            return
        values = [get_recording_step_action_value(step) for step in pending]
        final_value = values[-1]
        if not final_value:
            pending.clear()
            return
        is_same_value = all(value == final_value for value in values)
        is_progressive = True
        previous_length = -1
        for value in values:
            if not value or len(value) < previous_length or not final_value.startswith(value):
                is_progressive = False
                break
            previous_length = len(value)
        if is_same_value or is_progressive:
            group_key = build_recording_step_element_key(pending[-1])
            for step in pending[:-1]:
                mark_junk_step(
                    results,
                    step,
                    'duplicate_fill_same_element' if is_same_value else 'continuous_fill_intermediate',
                    '同一输入框重复输入相同内容，仅保留最后一次输入' if is_same_value else '同一输入框连续输入的中间值，仅保留最后完整输入',
                    group_key=group_key,
                )
        pending.clear()

    for step in steps:
        action = get_recording_step_action(step)
        if action == 'fill':
            key = build_recording_step_element_key(step)
            if pending and build_recording_step_element_key(pending[-1]) != key:
                flush_group()
            pending.append(step)
            continue
        flush_group()
    flush_group()


def identify_focus_click_junk_steps(steps, results):
    pending_clicks = []

    def flush_pending():
        pending_clicks.clear()

    for step in steps:
        action = get_recording_step_action(step)
        if action == 'click' and is_recording_step_editable_target(step):
            if pending_clicks and build_recording_step_element_key(pending_clicks[-1]) != build_recording_step_element_key(step):
                flush_pending()
            pending_clicks.append(step)
            continue

        if action == 'fill' and pending_clicks:
            fill_key = build_recording_step_element_key(step)
            matching_clicks = [
                click_step
                for click_step in pending_clicks
                if build_recording_step_element_key(click_step) == fill_key
            ]
            for click_step in matching_clicks:
                mark_junk_step(
                    results,
                    click_step,
                    'focus_click_before_input',
                    '输入框点击仅用于聚焦，后续输入步骤已表达真实操作',
                    group_key=fill_key,
                )
            flush_pending()
            continue

        flush_pending()


def identify_redundant_form_steps(steps, results):
    last_effect_by_element = {}
    previous_step = None
    previous_content_hash = ''
    previous_interaction_hash = ''
    previous_page_identity = ''

    for step in steps:
        _, content = resolve_recording_step_snapshot(step)
        content_hash = build_snapshot_content_hash(content)
        interaction_hash = build_snapshot_interaction_hash(content)
        page_identity = build_recording_page_identity(step)
        action = get_recording_step_action(step)
        element_key = build_recording_step_element_key(step)
        action_value = get_recording_step_action_value(step)
        element_value = get_recording_step_element_value(step)

        if action == 'click' and is_recording_step_plain_textbox_target(step) and not action_value:
            mark_junk_step(
                results,
                step,
                'empty_textbox_focus_click',
                '文本输入区域仅获得焦点且未产生输入内容，视为无效聚焦点击',
                group_key=element_key,
            )

        if (
            action == 'click' and
            previous_step and
            get_recording_step_action(previous_step) == 'click' and
            element_key and
            element_key == build_recording_step_element_key(previous_step)
        ):
            mark_junk_step(
                results,
                step,
                'duplicate_click_same_element',
                '同一元素连续重复点击，后一次未形成新的有效操作',
                group_key=element_key,
            )

        if (
            action == 'click' and
            previous_step and
            get_recording_step_action(previous_step) == 'fill' and
            element_key and
            element_key == build_recording_step_element_key(previous_step)
        ):
            mark_junk_step(
                results,
                step,
                'click_after_fill_same_input',
                '输入后再次点击同一输入框，未形成新的有效操作',
                group_key=element_key,
            )

        if action == 'press':
            normalized_key = normalize_match_text(action_value)
            same_interaction_state = (
                interaction_hash and
                previous_interaction_hash and
                interaction_hash == previous_interaction_hash and
                page_identity == previous_page_identity
            )
            if normalized_key in {'tab', 'shift+tab', 'escape', 'esc'} or same_interaction_state:
                mark_junk_step(
                    results,
                    step,
                    'noop_press_same_snapshot',
                    '按键后页面可交互状态无变化，疑似无效按键步骤',
                    group_key=f'{page_identity}:{interaction_hash or content_hash}',
                )

        if action in {'fill', 'select', 'check', 'uncheck'} and element_key:
            effect_value = action_value or element_value
            effect_key = (action, effect_value)
            if step.id not in results and last_effect_by_element.get(element_key) == effect_key:
                mark_junk_step(
                    results,
                    step,
                    'duplicate_value_same_element',
                    '同一组件重复设置相同值，未形成新的有效操作',
                    group_key=element_key,
                )
            if step.id not in results:
                last_effect_by_element[element_key] = effect_key

        if content_hash:
            previous_content_hash = content_hash
        if interaction_hash:
            previous_interaction_hash = interaction_hash
        previous_page_identity = page_identity
        previous_step = step


def identify_noop_click_junk_steps(steps, results):
    previous_hash = ''
    previous_interaction_hash = ''
    previous_page_identity = ''
    page_identity_by_step_id = {
        step.id: build_recording_page_identity(step)
        for step in steps
    }
    next_page_identity_by_step_id = {}
    next_page_identity = ''
    for step in reversed(steps):
        next_page_identity_by_step_id[step.id] = next_page_identity
        if step.id not in results:
            next_page_identity = page_identity_by_step_id.get(step.id) or ''

    for step in steps:
        if step.id in results:
            continue

        _, content = resolve_recording_step_snapshot(step)
        content_hash = build_snapshot_content_hash(content)
        interaction_hash = build_snapshot_interaction_hash(content)
        page_identity = page_identity_by_step_id.get(step.id) or build_recording_page_identity(step)
        action = get_recording_step_action(step)
        same_page = page_identity == previous_page_identity
        next_page_identity = next_page_identity_by_step_id.get(step.id) or ''
        followed_by_page_change = bool(next_page_identity and next_page_identity != page_identity)
        same_content = content_hash and previous_hash and content_hash == previous_hash
        same_interaction = (
            interaction_hash and
            previous_interaction_hash and
            interaction_hash == previous_interaction_hash
        )
        if (
            action == 'click' and
            same_page and
            not followed_by_page_change and
            (same_content or same_interaction) and
            not is_recording_step_command_button_click(step)
        ):
            mark_junk_step(
                results,
                step,
                'noop_click_same_snapshot',
                '点击前后页面快照无变化，疑似无效点击',
                group_key=f'{page_identity}:{interaction_hash or content_hash}',
            )
        if content_hash:
            previous_hash = content_hash
        if interaction_hash:
            previous_interaction_hash = interaction_hash
            previous_page_identity = page_identity


def identify_generic_container_click_junk_steps(steps, results):
    for step in steps:
        if step.id in results:
            continue
        if is_recording_step_generic_container_click(step):
            mark_junk_step(
                results,
                step,
                'generic_container_click',
                '点击页面容器或浮层空白区域，仅用于关闭浮层或转移焦点，不生成流程组件',
                group_key=build_recording_page_identity(step),
            )


def identify_recording_junk_steps(session):
    steps = list(session.steps.order_by('step_number', 'id'))
    results = {}
    identify_focus_click_junk_steps(steps, results)
    identify_continuous_fill_junk_steps(steps, results)
    identify_redundant_form_steps(steps, results)
    identify_generic_container_click_junk_steps(steps, results)
    identify_noop_click_junk_steps(steps, results)
    return [results[key] for key in sorted(results, key=lambda step_id: results[step_id]['step_number'])]


def get_recording_junk_step_map(steps):
    results = {}
    identify_focus_click_junk_steps(steps, results)
    identify_continuous_fill_junk_steps(steps, results)
    identify_redundant_form_steps(steps, results)
    identify_generic_container_click_junk_steps(steps, results)
    identify_noop_click_junk_steps(steps, results)
    return results


def get_recording_steps_for_flow(session):
    steps = list(session.steps.order_by('step_number', 'id'))
    junk_steps = get_recording_junk_step_map(steps)
    junk_step_ids = set(junk_steps.keys())
    flow_steps = [step for step in steps if step.id not in junk_step_ids]
    return flow_steps, junk_steps


def quote_snapshot_text(value):
    return str(value or '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').strip()


def quote_snapshot_attr(value):
    return str(value or '').replace(']', '').replace('\n', ' ').strip()


def generate_snapshot_element_selectors(element):
    selectors = []

    def push(selector_type, value, priority):
        value = normalize_recording_scalar(value)
        if not value or any(item.get('type') == selector_type and item.get('value') == value for item in selectors):
            return
        selectors.append({'type': selector_type, 'value': value, 'priority': priority})

    element_type = normalize_recording_scalar(element.get('type')).lower()
    text = normalize_recording_scalar(element.get('text'))
    ref = normalize_recording_scalar(element.get('ref'))
    attrs = element.get('attributes') if isinstance(element.get('attributes'), dict) else {}

    if ref:
        push('data-ref', f'[data-ref="{quote_snapshot_attr(ref)}"]', 1)
    if attrs.get('id'):
        push('id', f'#{quote_snapshot_attr(attrs.get("id"))}', 2)
    if attrs.get('name'):
        base = 'input' if element_type in ('textbox', 'input', 'searchbox') else element_type
        push('name', f'{base or "*"}[name="{quote_snapshot_attr(attrs.get("name"))}"]', 3)
    if attrs.get('placeholder'):
        base = 'input' if element_type in ('textbox', 'input', 'searchbox') else element_type
        push('placeholder', f'{base or "input"}[placeholder="{quote_snapshot_attr(attrs.get("placeholder"))}"]', 4)
    if attrs.get('class'):
        class_name = normalize_recording_scalar(attrs.get('class')).split()[0]
        if class_name:
            base = attrs.get('tag') or element_type or ''
            push('class', f'{quote_snapshot_attr(base)}.{quote_snapshot_attr(class_name)}' if base else f'.{quote_snapshot_attr(class_name)}', 4)
    if text:
        escaped_text = quote_snapshot_attr(text)
        if element_type == 'button':
            push('text', f'button:has-text("{escaped_text}")', 5)
        elif element_type in ('link', 'a'):
            push('text', f'a:has-text("{escaped_text}")', 5)
        else:
            push('text', f'text="{escaped_text}"', 6)

    role_map = {
        'button': 'button',
        'link': 'link',
        'a': 'link',
        'textbox': 'textbox',
        'input': 'textbox',
        'searchbox': 'textbox',
        'checkbox': 'checkbox',
        'radio': 'radio',
        'tab': 'tab',
        'menuitem': 'menuitem',
        'select': 'combobox',
        'combobox': 'combobox',
        'listbox': 'listbox',
        'iframe': 'iframe',
        'frame': 'iframe',
    }
    if role_map.get(element_type):
        push('role', f'role={role_map[element_type]}', 5)

    return sorted(selectors, key=lambda item: item.get('priority', 99))


def parse_snapshot_element_string(raw_value):
    value = normalize_recording_scalar(raw_value)
    result = {
        'type': 'generic',
        'text': '',
        'ref': '',
        'attributes': {},
        'selectors': [],
    }
    if not value:
        return result

    type_match = re.match(r'^([A-Za-z0-9_-]+)', value)
    if type_match:
        result['type'] = type_match.group(1).lower()

    text_match = re.search(r'"((?:\\"|[^"])*)"', value)
    if text_match:
        result['text'] = text_match.group(1).replace('\\"', '"')

    for attr_match in re.finditer(r'\[([^\]=]+)(?:=([^\]]+))?\]', value):
        key = normalize_recording_scalar(attr_match.group(1))
        attr_value = attr_match.group(2)
        attr_value = True if attr_value is None else normalize_recording_scalar(attr_value)
        if key == 'ref':
            result['ref'] = normalize_recording_scalar(attr_value)
        elif key:
            result['attributes'][key] = attr_value

    result['selectors'] = generate_snapshot_element_selectors(result)
    return result


def build_snapshot_element_tree(raw_nodes, path=None):
    path = path or []
    if raw_nodes is None:
        return []
    if not isinstance(raw_nodes, list):
        raw_nodes = [raw_nodes]

    elements = []
    for index, node in enumerate(raw_nodes):
        current_path = [*path, index]
        children = []
        parsed = {
            'id': f'element_{"_".join(str(item) for item in current_path)}',
            'type': 'generic',
            'text': '',
            'ref': '',
            'attributes': {},
            'selectors': [],
            'children': [],
        }

        if isinstance(node, str):
            parsed.update(parse_snapshot_element_string(node))
        elif isinstance(node, dict):
            keys = list(node.keys())
            if keys:
                parsed.update(parse_snapshot_element_string(keys[0]))
            for value in node.values():
                if isinstance(value, list):
                    children.extend(build_snapshot_element_tree(value, current_path))
        else:
            parsed.update(parse_snapshot_element_string(str(node)))

        parsed['children'] = children
        elements.append(parsed)

    return elements


def flatten_snapshot_elements(elements):
    flattened = []
    for element in elements or []:
        flattened.append(element)
        flattened.extend(flatten_snapshot_elements(element.get('children') or []))
    return flattened


def sanitize_backend_snapshot_element(element, index):
    return {
        'id': str(element.get('id') or f'element_{index}'),
        'type': str(element.get('type') or 'generic').lower(),
        'text': str(element.get('text') or ''),
        'ref': str(element.get('ref') or ''),
        'attributes': sanitize_snapshot_attributes(element.get('attributes')),
        'selectors': sanitize_snapshot_selectors(element.get('selectors')),
    }


def parse_snapshot_content(content):
    normalized_content = content if isinstance(content, str) else ''
    line_count = len(normalized_content.splitlines()) if normalized_content else 0
    if not normalized_content.strip():
        return {'valid': True, 'line_count': line_count, 'interactive_elements': [], 'error': ''}

    try:
        raw_data = yaml.safe_load(normalized_content) or []
        tree = build_snapshot_element_tree(raw_data)
        interactive_elements = []
        for element in flatten_snapshot_elements(tree):
            element_type = str(element.get('type') or '').lower()
            attributes = element.get('attributes') if isinstance(element.get('attributes'), dict) else {}
            if (
                element_type in SNAPSHOT_INTERACTIVE_TYPES or
                attributes.get('cursor') == 'pointer' or
                bool(attributes.get('role'))
            ):
                interactive_elements.append(sanitize_backend_snapshot_element(element, len(interactive_elements)))

        return {
            'valid': True,
            'line_count': line_count,
            'interactive_elements': interactive_elements,
            'error': '',
        }
    except Exception as exc:
        return {
            'valid': False,
            'line_count': line_count,
            'interactive_elements': [],
            'error': str(exc),
        }


def build_snapshot_parse_payload(content, interactive_elements):
    sample_elements = []
    for element in (interactive_elements or [])[:20]:
        selector = ''
        for selector_item in element.get('selectors') or []:
            if selector_item.get('type') != 'data-ref':
                selector = selector_item.get('value') or ''
                break
        sample_elements.append({
            'type': element.get('type') or '-',
            'text': element.get('text') or element.get('attributes', {}).get('placeholder') or element.get('id') or '-',
            'selector': selector or element.get('type') or '-',
        })

    return {
        'parse_status': SNAPSHOT_PARSE_STATUS_SUCCESS,
        'line_count': len(str(content or '').splitlines()),
        'interactive_count': len(interactive_elements or []),
        'parse_error': '',
        'sample_elements': sample_elements,
        'interactive_elements': interactive_elements or [],
    }


def update_snapshot_parse_metadata(filename, content, interactive_elements):
    if not filename:
        return
    try:
        normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
        file_stat = os.stat(file_path)
        upsert_snapshot_metadata(
            normalized_filename,
            parse_data=build_snapshot_parse_payload(content, interactive_elements),
            parsed_source_mtime=file_stat.st_mtime
        )
    except Exception:
        pass


def infer_recorded_snapshot_element_type(step):
    element = step.element if isinstance(step.element, dict) else {}
    role = normalize_recording_scalar(element.get('role')).lower()
    tag = normalize_recording_scalar(element.get('tag')).lower()
    html_type = normalize_recording_scalar(element.get('type')).lower()
    action = normalize_recording_scalar(step.action_type).lower()

    if role in SNAPSHOT_INTERACTIVE_TYPES:
        return 'textbox' if role == 'searchbox' else role
    if tag == 'a':
        return 'link'
    if tag == 'button':
        return 'button'
    if tag == 'textarea':
        return 'textbox'
    if tag == 'select':
        return 'combobox'
    if tag == 'iframe':
        return 'iframe'
    if tag == 'input':
        if html_type in ('button', 'submit', 'reset'):
            return 'button'
        if html_type == 'checkbox':
            return 'checkbox'
        if html_type == 'radio':
            return 'radio'
        if html_type == 'file':
            return 'file'
        return 'textbox'
    if action in ('fill', 'press'):
        return 'textbox'
    if action in ('check', 'uncheck'):
        return 'checkbox'
    if action == 'select':
        return 'radio' if html_type == 'radio' or role == 'radio' else 'combobox'
    return 'clickable'


def get_recorded_locator_values(element):
    element = element if isinstance(element, dict) else {}
    locators = element.get('locatorValues') or element.get('locator_values') or {}
    locators = locators if isinstance(locators, dict) else {}

    def pick(*keys):
        for key in keys:
            value = locators.get(key)
            if value in (None, ''):
                value = element.get(key)
            if value not in (None, ''):
                return normalize_recording_scalar(value)
        return ''

    class_name = pick('classname', 'className', 'class_name')
    if class_name and ' ' in class_name:
        class_name = class_name.split()[0]

    tag_name = pick('tagname', 'tagName', 'tag')
    return {
        'id': pick('id'),
        'name': pick('name'),
        'classname': class_name,
        'tagname': tag_name,
        'linktext': pick('linktext', 'linkText'),
        'partiallinktext': pick('partiallinktext', 'partialLinkText'),
        'xpath': pick('xpath'),
        'cssselector': pick('cssselector', 'cssSelector'),
    }


def normalize_recorded_step_selectors(step, element_type):
    raw_selectors = step.selectors if isinstance(step.selectors, list) else []
    selectors = sanitize_snapshot_selectors(raw_selectors)
    element = step.element if isinstance(step.element, dict) else {}
    locators = get_recorded_locator_values(element)
    tag = normalize_recording_scalar(element.get('tag')).lower()
    tag = tag or locators.get('tagname') or ('input' if element_type in ('textbox', 'input', 'searchbox') else element_type)

    def push(selector_type, value, priority):
        value = normalize_recording_scalar(value)
        if not value or any(item.get('value') == value for item in selectors):
            return
        selectors.append({'type': selector_type, 'value': value, 'priority': priority})

    if element.get('id'):
        push('id', f'#{quote_snapshot_attr(element.get("id"))}', 2)
    if element.get('name'):
        push('name', f'{tag}[name="{quote_snapshot_attr(element.get("name"))}"]', 3)
    if element.get('placeholder'):
        push('placeholder', f'{tag}[placeholder="{quote_snapshot_attr(element.get("placeholder"))}"]', 4)
    text = (
        element.get('text') or
        element.get('ariaLabel') or
        element.get('title') or
        element.get('placeholder') or
        element.get('name') or
        element.get('id') or
        ''
    )
    if text and element_type in ('button', 'link', 'tab', 'menuitem', 'clickable'):
        push('text', f'text="{quote_snapshot_attr(text)}"', 6)
    push('by_id', locators.get('id'), 10)
    push('by_name', locators.get('name'), 11)
    push('by_classname', locators.get('classname'), 12)
    push('by_tagname', locators.get('tagname'), 13)
    push('by_linktext', locators.get('linktext'), 14)
    push('by_partiallinktext', locators.get('partiallinktext'), 15)
    push('by_xpath', locators.get('xpath'), 16)
    push('by_cssselector', locators.get('cssselector'), 17)
    selectors.sort(key=lambda item: item.get('priority', 99))
    return selectors


def build_recorded_snapshot_element(step):
    recorded = step.element if isinstance(step.element, dict) else {}
    locators = get_recorded_locator_values(recorded)
    element_type = infer_recorded_snapshot_element_type(step)
    text = (
        recorded.get('text') or
        recorded.get('placeholder') or
        recorded.get('ariaLabel') or
        recorded.get('title') or
        recorded.get('name') or
        recorded.get('id') or
        locators.get('linktext') or
        element_type
    )
    attributes = {}
    attr_sources = {
        'id': recorded.get('id') or locators.get('id'),
        'name': recorded.get('name') or locators.get('name'),
        'class': recorded.get('className') or locators.get('classname'),
        'label': recorded.get('text'),
        'placeholder': recorded.get('placeholder'),
        'aria-label': recorded.get('ariaLabel'),
        'title': recorded.get('title'),
        'role': recorded.get('role') or element_type,
        'tag': recorded.get('tag') or locators.get('tagname'),
        'type': recorded.get('type'),
        'linktext': locators.get('linktext'),
        'partiallinktext': locators.get('partiallinktext'),
    }
    for key, value in attr_sources.items():
        value = normalize_recording_scalar(value)
        if value:
            attributes[key] = value
    if 'checked' in recorded:
        attributes['checked'] = bool(recorded.get('checked'))
    if step.action_type:
        attributes['recorded-action'] = step.action_type

    return {
        'id': f'recorded_step_{step.step_number:04d}',
        'type': element_type,
        'text': normalize_recording_scalar(text, 160),
        'ref': f'recorded-step-{step.step_number:04d}',
        'attributes': sanitize_snapshot_attributes(attributes),
        'selectors': normalize_recorded_step_selectors(step, element_type),
    }


def get_visual_component_type(element_type, action_type=''):
    normalized_type = str(element_type or '').lower()
    action = str(action_type or '').lower()
    component_type = COMPONENT_TYPE_BY_ELEMENT_TYPE.get(normalized_type)
    if component_type:
        return component_type
    if action in ('fill', 'press'):
        return 'input'
    if action in ('check', 'uncheck'):
        return 'checkbox'
    if action == 'select':
        if normalized_type == 'radio':
            return 'radio'
        return 'select'
    return 'clickable'


def snapshot_element_matches_step(snapshot_element, step, recorded_element):
    element_type = str(snapshot_element.get('type') or '').lower()
    recorded_type = str(recorded_element.get('type') or '').lower()
    component_type = get_visual_component_type(recorded_type, step.action_type)
    if get_visual_component_type(element_type, step.action_type) != component_type and element_type != recorded_type:
        return False

    snapshot_selectors = {
        normalize_match_text(selector.get('value'))
        for selector in (snapshot_element.get('selectors') or [])
        if selector.get('value')
    }
    recorded_selectors = {
        normalize_match_text(selector.get('value'))
        for selector in (recorded_element.get('selectors') or [])
        if selector.get('value')
    }
    if snapshot_selectors and recorded_selectors and snapshot_selectors.intersection(recorded_selectors):
        return True

    snapshot_attrs = snapshot_element.get('attributes') if isinstance(snapshot_element.get('attributes'), dict) else {}
    recorded_attrs = recorded_element.get('attributes') if isinstance(recorded_element.get('attributes'), dict) else {}
    for attr_name in ('id', 'name', 'placeholder', 'aria-label', 'title'):
        left = normalize_match_text(snapshot_attrs.get(attr_name))
        right = normalize_match_text(recorded_attrs.get(attr_name))
        if left and right and left == right:
            return True

    snapshot_text = normalize_match_text(
        snapshot_element.get('text') or snapshot_attrs.get('placeholder') or snapshot_attrs.get('name')
    )
    recorded_text = normalize_match_text(
        recorded_element.get('text') or recorded_attrs.get('placeholder') or recorded_attrs.get('name')
    )
    return bool(snapshot_text and recorded_text and snapshot_text == recorded_text)


def merge_recorded_snapshot_element(snapshot_element, recorded_element):
    if not isinstance(snapshot_element, dict) or not isinstance(recorded_element, dict):
        return snapshot_element, False

    changed = False
    snapshot_attrs = snapshot_element.get('attributes') if isinstance(snapshot_element.get('attributes'), dict) else {}
    recorded_attrs = recorded_element.get('attributes') if isinstance(recorded_element.get('attributes'), dict) else {}
    merged_attrs = dict(snapshot_attrs)
    for key, value in recorded_attrs.items():
        if value in (None, ''):
            continue
        if not merged_attrs.get(key):
            merged_attrs[key] = value
            changed = True

    snapshot_selectors = snapshot_element.get('selectors') if isinstance(snapshot_element.get('selectors'), list) else []
    recorded_selectors = recorded_element.get('selectors') if isinstance(recorded_element.get('selectors'), list) else []
    merged_selectors = sanitize_snapshot_selectors(snapshot_selectors)
    existing_selector_values = {
        normalize_match_text(selector.get('value'))
        for selector in merged_selectors
        if isinstance(selector, dict) and selector.get('value')
    }
    for selector in sanitize_snapshot_selectors(recorded_selectors):
        selector_value = normalize_match_text(selector.get('value'))
        if selector_value and selector_value not in existing_selector_values:
            merged_selectors.append(selector)
            existing_selector_values.add(selector_value)
            changed = True
    merged_selectors.sort(key=lambda item: item.get('priority', 99))

    if not snapshot_element.get('ref') and recorded_element.get('ref'):
        snapshot_element['ref'] = recorded_element.get('ref')
        changed = True
    if not snapshot_element.get('text') and recorded_element.get('text'):
        snapshot_element['text'] = recorded_element.get('text')
        changed = True

    if changed:
        snapshot_element['attributes'] = sanitize_snapshot_attributes(merged_attrs)
        snapshot_element['selectors'] = merged_selectors
    return snapshot_element, changed


def ensure_recorded_element_in_snapshot(interactive_elements, step):
    recorded_element = build_recorded_snapshot_element(step)
    for snapshot_element in interactive_elements:
        if snapshot_element_matches_step(snapshot_element, step, recorded_element):
            merged_element, _ = merge_recorded_snapshot_element(snapshot_element, recorded_element)
            return merged_element, False

    existing_ids = {item.get('id') for item in interactive_elements}
    base_id = recorded_element['id']
    next_id = base_id
    suffix = 1
    while next_id in existing_ids:
        suffix += 1
        next_id = f'{base_id}_{suffix}'
    recorded_element['id'] = next_id
    interactive_elements.append(recorded_element)
    return recorded_element, True


def build_recording_snapshot_element_signature(element):
    if not isinstance(element, dict):
        return ''

    attributes = element.get('attributes') if isinstance(element.get('attributes'), dict) else {}
    selectors = element.get('selectors') if isinstance(element.get('selectors'), list) else []
    selector_values = [
        normalize_match_text(selector.get('value'))
        for selector in selectors
        if isinstance(selector, dict) and selector.get('value')
    ]
    key_parts = [
        normalize_match_text(element.get('type')),
        normalize_match_text(element.get('text')),
        normalize_match_text(element.get('ref')),
        normalize_match_text(attributes.get('id')),
        normalize_match_text(attributes.get('name')),
        normalize_match_text(attributes.get('placeholder')),
        normalize_match_text(attributes.get('aria-label') or attributes.get('ariaLabel')),
        normalize_match_text(attributes.get('title')),
        normalize_match_text(attributes.get('tag')),
        '|'.join(selector_values[:4]),
    ]
    return '::'.join(part for part in key_parts if part)


def build_recorded_snapshot_line(element):
    element_type = re.sub(r'[^A-Za-z0-9_-]', '', str(element.get('type') or 'generic')) or 'generic'
    text = quote_snapshot_text(element.get('text') or element_type)
    attrs = []
    ref = quote_snapshot_attr(element.get('ref') or element.get('id'))
    if ref:
        attrs.append(f'[ref={ref}]')
    attributes = element.get('attributes') if isinstance(element.get('attributes'), dict) else {}
    for key in ('id', 'name', 'class', 'placeholder', 'aria-label', 'title', 'role', 'tag', 'type', 'recorded-action'):
        value = attributes.get(key)
        if value not in (None, ''):
            attrs.append(f'[{key}={quote_snapshot_attr(value)}]')
    if attributes.get('checked') in (True, 'true', 'True', '1', 1):
        attrs.append('[checked]')
    if element_type in ('button', 'link', 'tab', 'menuitem', 'clickable'):
        attrs.append('[cursor=pointer]')
    return f'- {element_type} "{text}" {" ".join(attrs)}'.rstrip()


def append_recorded_elements_to_snapshot_content(content, elements):
    base = str(content or '').rstrip()
    if not base:
        base = '- document:'
    lines = [base, '', '# testhub-recorded-elements']
    lines.extend(build_recorded_snapshot_line(element) for element in elements)
    return '\n'.join(lines).rstrip() + '\n'


def write_snapshot_content(filename, content):
    normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=False)
    with open(file_path, 'w', encoding='utf-8') as snapshot_file:
        snapshot_file.write(sanitize_snapshot_content(content))
    return normalized_filename


def create_recording_flow_snapshot_file(session, group_index, content):
    filename = f'recording-{session.session_id}-flow-page-{group_index:04d}.yml'
    page_name = f'{session.name or session.session_id} page {group_index}'
    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
    try:
        snapshot_info = write_snapshot_file(
            filename,
            content,
            overwrite=True,
            page_name=page_name,
            alias=page_name,
            module=module if module else SNAPSHOT_PAGE_NAME_UNSET,
        )
        return snapshot_info.get('filename') or filename
    except ValueError:
        write_snapshot_content(filename, content)
        return filename


def parse_recording_action_value(value):
    raw_value = value
    if isinstance(value, str):
        try:
            raw_value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_value = value
    if isinstance(raw_value, list):
        return normalize_recording_scalar(raw_value[0] if raw_value else '')
    if isinstance(raw_value, dict):
        return normalize_recording_scalar(raw_value)
    return normalize_recording_scalar(raw_value)


def parse_recording_bool(value, default=False):
    if isinstance(value, bool):
        return value
    normalized = normalize_recording_scalar(value).lower()
    if normalized in ('true', '1', 'yes', 'on', 'checked'):
        return True
    if normalized in ('false', '0', 'no', 'off', 'unchecked'):
        return False
    return default


def build_component_config_for_step(component_type, step, element_data):
    action = str(step.action_type or '').lower()
    action_value = parse_recording_action_value(step.action_value)
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    raw_event_selectors = raw_event.get('selectors') if isinstance(raw_event.get('selectors'), list) else []
    recording_selectors = sanitize_snapshot_selectors(raw_event_selectors or (step.selectors if isinstance(step.selectors, list) else []))
    config = {
        'action': 'click',
        'inputMode': 'literal',
        'inputValue': action_value,
        'inputReference': '',
        'outputName': '',
        'outputSource': 'none',
        'outputValue': '',
        'recordingStepId': step.id,
        'recordingStepNumber': step.step_number,
        'recordingActionType': step.action_type,
        'recordingActionValue': step.action_value,
        'recordingSelectors': recording_selectors,
    }

    if component_type == 'input':
        config.update({
            'action': 'press' if action == 'press' else 'fill',
            'value': action_value,
            'placeholder': element_data.get('attributes', {}).get('placeholder') or '',
        })
    elif component_type == 'select':
        config.update({'action': 'select', 'selectedValue': action_value})
    elif component_type == 'checkbox':
        config.update({'action': 'check', 'checked': parse_recording_bool(step.action_value, default=True)})
    elif component_type == 'radio':
        config.update({'action': 'check', 'checked': parse_recording_bool(step.action_value, default=True)})
    elif component_type == 'iframe':
        config.update({'action': 'scope'})
    else:
        config.update({'action': action if action in ('click', 'dblclick', 'contextmenu', 'hover') else 'click'})
    return config


def build_recording_component_grid(total):
    total = max(int(total or 0), 1)
    columns = min(total, FLOW_COMPONENT_GRID['max_columns'])
    rows = max(1, (total + columns - 1) // columns)
    return {'columns': columns, 'rows': rows}


def build_recording_page_node_size(total_components, components=None):
    components = components if isinstance(components, list) else None
    root_components = [
        component for component in (components or [])
        if isinstance(component, dict) and not component.get('parentId')
    ]
    layout_total = len(root_components) if components is not None else total_components
    grid = build_recording_component_grid(layout_total)
    max_component_width = max(
        (get_flow_component_size(component)['width'] for component in root_components),
        default=150,
    )
    max_component_height = max(
        (get_flow_component_size(component)['height'] for component in root_components),
        default=82,
    )
    cell_width = max(FLOW_COMPONENT_GRID['cell_width'], max_component_width + 88)
    cell_height = max(FLOW_COMPONENT_GRID['cell_height'], max_component_height + 80)
    inner_width = grid['columns'] * cell_width
    inner_height = grid['rows'] * cell_height
    return {
        'width': max(
            FLOW_COMPONENT_GRID['min_width'],
            PAGE_NODE_LAYOUT['padding_x'] * 2 + inner_width,
        ),
        'height': max(
            FLOW_COMPONENT_GRID['min_height'],
            PAGE_NODE_LAYOUT['header_height'] + PAGE_NODE_LAYOUT['footer_height'] +
            PAGE_NODE_LAYOUT['padding_y'] * 2 + inner_height,
        ),
    }


def build_recording_iframe_size(total_components):
    grid = build_recording_component_grid(total_components)
    inner_width = grid['columns'] * FLOW_COMPONENT_GRID['iframe_cell_width']
    inner_height = grid['rows'] * FLOW_COMPONENT_GRID['iframe_cell_height']
    return {
        'width': max(260, 24 + inner_width),
        'height': max(220, 30 + 24 + inner_height),
    }


def normalize_flow_component_size_value(value, fallback):
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return fallback
    if normalized <= 0:
        return fallback
    return max(normalized, fallback)


def get_flow_component_size(component):
    component = component if isinstance(component, dict) else {}
    base_size = FLOW_COMPONENT_SIZES.get(component.get('type'), {'width': 150, 'height': 68})
    custom_size = component.get('size') if isinstance(component.get('size'), dict) else {}
    return {
        'width': normalize_flow_component_size_value(custom_size.get('width'), base_size['width']),
        'height': normalize_flow_component_size_value(custom_size.get('height'), base_size['height']),
    }


def build_grid_component_position(index, total, x_min=10, x_max=90, y_min=12, y_max=88):
    grid = build_recording_component_grid(total)
    columns = grid['columns']
    rows = grid['rows']
    row = index // columns
    column = index % columns
    x = (x_min + x_max) / 2 if columns <= 1 else x_min + ((x_max - x_min) * column / (columns - 1))
    y = y_min + ((y_max - y_min) * (row + 0.5) / max(rows, 1))
    return {
        'x': max(x_min, min(x_max, x)),
        'y': max(y_min, min(y_max, y)),
    }


def build_component_position(index, total):
    return build_grid_component_position(index, total)


def build_iframe_component_position(index, total):
    return build_grid_component_position(index, total, x_min=8, x_max=92, y_min=10, y_max=90)


def build_nested_component_position(index, total):
    return build_grid_component_position(index, total, x_min=10, x_max=90, y_min=12, y_max=88)


def get_recording_step_frame_payload(step):
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    frame = raw_event.get('frame') if isinstance(raw_event.get('frame'), dict) else {}
    if not frame and isinstance(raw_event.get('agent_payload'), dict):
        agent_event = raw_event.get('agent_payload', {}).get('event')
        if isinstance(agent_event, dict) and isinstance(agent_event.get('frame'), dict):
            frame = agent_event.get('frame')
    return frame if isinstance(frame, dict) else {}


def is_recording_step_inside_iframe(step):
    raw_event = step.raw_event if isinstance(step.raw_event, dict) else {}
    frame = get_recording_step_frame_payload(step)
    if raw_event.get('is_iframe_event') is True or raw_event.get('frame_is_main') is False:
        return True
    if frame.get('isMain') is False or frame.get('is_main') is False:
        return True
    return bool(frame.get('element') or frame.get('selectors'))


def build_recording_iframe_key(step):
    frame = get_recording_step_frame_payload(step)
    element = frame.get('element') if isinstance(frame.get('element'), dict) else {}
    selectors = frame.get('selectors') if isinstance(frame.get('selectors'), list) else []
    selector_values = [
        normalize_recording_scalar(selector.get('value'))
        for selector in selectors
        if isinstance(selector, dict) and selector.get('value')
    ]
    key_parts = [
        normalize_recording_page_url_for_group(step.page_url),
        normalize_recording_scalar(frame.get('url')),
        normalize_recording_scalar(frame.get('name')),
        normalize_recording_scalar(element.get('id')),
        normalize_recording_scalar(element.get('name')),
        normalize_recording_scalar(element.get('cssSelector')),
        '|'.join(selector_values[:4]),
    ]
    return '::'.join(normalize_match_text(part) for part in key_parts if part) or f'iframe:{step.step_number}'


def build_recorded_iframe_element(step, index):
    frame = get_recording_step_frame_payload(step)
    frame_element = frame.get('element') if isinstance(frame.get('element'), dict) else {}
    selectors = frame.get('selectors') if isinstance(frame.get('selectors'), list) else []
    text = (
        frame_element.get('text') or
        frame_element.get('title') or
        frame_element.get('name') or
        frame.get('name') or
        frame.get('url') or
        f'iframe {index + 1}'
    )
    attributes = {
        'role': 'iframe',
        'tag': frame_element.get('tag') or 'iframe',
        'id': frame_element.get('id') or '',
        'name': frame_element.get('name') or frame.get('name') or '',
        'title': frame_element.get('title') or '',
        'src': frame.get('url') or '',
    }
    attributes = {
        key: normalize_recording_scalar(value, 500)
        for key, value in attributes.items()
        if normalize_recording_scalar(value, 500)
    }
    return {
        'id': f'recorded_iframe_{step.step_number:04d}_{index + 1}',
        'type': 'iframe',
        'text': normalize_recording_scalar(text, 160),
        'ref': f'recorded-iframe-{step.step_number:04d}',
        'attributes': sanitize_snapshot_attributes(attributes),
        'selectors': sanitize_snapshot_selectors(selectors),
    }


def build_iframe_components_for_steps(group_steps):
    iframe_components = []
    iframe_by_key = {}
    step_iframe_map = {}
    iframe_step_totals = {}
    for step in group_steps:
        if is_recording_step_inside_iframe(step):
            iframe_key = build_recording_iframe_key(step)
            iframe_step_totals[iframe_key] = iframe_step_totals.get(iframe_key, 0) + 1

    for step in group_steps:
        if not is_recording_step_inside_iframe(step):
            continue
        iframe_key = build_recording_iframe_key(step)
        if iframe_key not in iframe_by_key:
            iframe_index = len(iframe_components)
            iframe_id = f'recorded_iframe_component_{step.step_number:04d}_{iframe_index + 1}'
            element_data = build_recorded_iframe_element(step, iframe_index)
            iframe_size = build_recording_iframe_size(iframe_step_totals.get(iframe_key, 1))
            iframe_component = {
                'id': iframe_id,
                'type': 'iframe',
                'parentId': None,
                'elementId': element_data.get('id'),
                'elementData': element_data,
                'size': iframe_size,
                'position': build_iframe_component_position(iframe_index, max(1, len(group_steps))),
                'zIndex': iframe_index,
                'order': iframe_index,
                'config': {
                    'action': 'scope',
                    'inputMode': 'literal',
                    'inputValue': '',
                    'inputReference': '',
                    'outputName': '',
                    'outputSource': 'none',
                    'outputValue': '',
                    'recordingFrameUrl': get_recording_step_frame_payload(step).get('url') or '',
                    'recordingFrameName': get_recording_step_frame_payload(step).get('name') or '',
                },
            }
            iframe_by_key[iframe_key] = iframe_component
            iframe_components.append(iframe_component)
        step_iframe_map[step.step_number] = iframe_by_key[iframe_key]['id']
    return iframe_components, step_iframe_map


def build_flow_endpoint(port_id, component=None, direction='out'):
    if component is None:
        return {
            'portId': port_id,
            'scopeType': 'page',
            'scopeId': 'page',
            'wall': 'shared',
            'side': 'right' if direction == 'out' else 'left',
            'direction': direction,
            'componentId': None,
            'componentType': 'page',
            'elementId': None,
            'elementType': 'page',
            'elementText': 'page',
            'parentId': None,
        }

    element_data = component.get('elementData') or {}
    is_iframe = component.get('type') == 'iframe'
    return {
        'portId': port_id,
        'scopeType': 'iframe' if is_iframe else 'component',
        'scopeId': component.get('id'),
        'wall': 'shared' if is_iframe else 'component',
        'side': 'right' if direction == 'out' else 'left',
        'direction': direction,
        'componentId': component.get('id'),
        'componentType': component.get('type'),
        'elementId': component.get('elementId'),
        'elementType': element_data.get('type') or component.get('type'),
        'elementText': element_data.get('text') or element_data.get('ref') or component.get('elementId') or component.get('type'),
        'parentId': component.get('parentId'),
    }


def build_component_execution_port_id(component, direction='out'):
    suffix = 'right-out' if direction == 'out' else 'left-in'
    if component.get('type') == 'iframe':
        return f'iframe-{component["id"]}-{suffix}'
    return f'component-{component["id"]}-{suffix}'


def build_component_execution_endpoint(component, direction='out'):
    return build_flow_endpoint(
        build_component_execution_port_id(component, direction),
        component,
        direction,
    )


def build_page_execution_endpoint(direction='out'):
    return build_flow_endpoint('page-right-out' if direction == 'out' else 'page-left-in', None, direction)


def get_component_iframe_chain(component, component_map):
    chain = []
    parent_id = component.get('parentId')
    guard = 0
    while parent_id and guard < 20:
        parent = component_map.get(parent_id)
        if not parent:
            break
        if parent.get('type') == 'iframe':
            chain.insert(0, parent)
        parent_id = parent.get('parentId')
        guard += 1
    return chain


def common_iframe_chain_length(left_chain, right_chain):
    length = 0
    for left, right in zip(left_chain, right_chain):
        if left.get('id') != right.get('id'):
            break
        length += 1
    return length


def build_execution_path_step(source_endpoint, target_endpoint, action='next', value=''):
    return {
        'from': source_endpoint,
        'to': target_endpoint,
        'action': action or 'next',
        'value': value or '',
        'createdAt': int(time.time() * 1000),
    }


def build_execution_path_for_components(components):
    execution_path = []
    component_map = {
        component.get('id'): component
        for component in (components or [])
        if component.get('id')
    }
    actionable = [component for component in components if component.get('type') != 'iframe']
    if not actionable:
        return execution_path

    def append_step(source_endpoint, target_endpoint, action='next', value=''):
        if not source_endpoint or not target_endpoint:
            return
        if source_endpoint.get('portId') == target_endpoint.get('portId'):
            return
        step_key = (source_endpoint.get('portId'), target_endpoint.get('portId'))
        if any(
            existing.get('from', {}).get('portId') == step_key[0] and
            existing.get('to', {}).get('portId') == step_key[1]
            for existing in execution_path
        ):
            return
        execution_path.append(build_execution_path_step(source_endpoint, target_endpoint, action, value))

    first_component = actionable[0]
    source_endpoint = build_page_execution_endpoint('in')
    for iframe_component in get_component_iframe_chain(first_component, component_map):
        target_endpoint = build_component_execution_endpoint(iframe_component, 'in')
        append_step(source_endpoint, target_endpoint, 'enter')
        source_endpoint = target_endpoint
    append_step(source_endpoint, build_component_execution_endpoint(first_component, 'in'), 'enter')

    for previous, current in zip(actionable, actionable[1:]):
        previous_action = previous.get('config', {}).get('action') or 'next'
        previous_value = previous.get('config', {}).get('inputValue') or ''
        previous_chain = get_component_iframe_chain(previous, component_map)
        current_chain = get_component_iframe_chain(current, component_map)
        common_length = common_iframe_chain_length(previous_chain, current_chain)
        source_endpoint = build_component_execution_endpoint(previous, 'out')
        previous_action_used = False

        for iframe_component in reversed(previous_chain[common_length:]):
            target_endpoint = build_component_execution_endpoint(iframe_component, 'out')
            append_step(
                source_endpoint,
                target_endpoint,
                previous_action if not previous_action_used else 'exit_iframe',
                previous_value if not previous_action_used else '',
            )
            previous_action_used = True
            source_endpoint = target_endpoint

        for iframe_component in current_chain[common_length:]:
            target_endpoint = build_component_execution_endpoint(iframe_component, 'in')
            append_step(
                source_endpoint,
                target_endpoint,
                previous_action if not previous_action_used else 'enter_iframe',
                previous_value if not previous_action_used else '',
            )
            previous_action_used = True
            source_endpoint = target_endpoint

        append_step(
            source_endpoint,
            build_component_execution_endpoint(current, 'in'),
            'enter_iframe' if previous_action_used else previous_action,
            '' if previous_action_used else previous_value,
        )

    last_component = actionable[-1]
    last_action = last_component.get('config', {}).get('action') or 'exit'
    last_value = last_component.get('config', {}).get('inputValue') or ''
    source_endpoint = build_component_execution_endpoint(last_component, 'out')
    last_action_used = False
    for iframe_component in reversed(get_component_iframe_chain(last_component, component_map)):
        target_endpoint = build_component_execution_endpoint(iframe_component, 'out')
        append_step(
            source_endpoint,
            target_endpoint,
            last_action if not last_action_used else 'exit_iframe',
            last_value if not last_action_used else '',
        )
        last_action_used = True
        source_endpoint = target_endpoint
    append_step(
        source_endpoint,
        build_page_execution_endpoint('out'),
        'exit_iframe' if last_action_used else last_action,
        '' if last_action_used else last_value,
    )
    return execution_path


def build_flow_rect(left, top, width, height):
    return {
        'left': left,
        'top': top,
        'width': width,
        'height': height,
        'right': left + width,
        'bottom': top + height,
        'center_x': left + width / 2,
        'center_y': top + height / 2,
    }


def build_page_inner_rect(node_size):
    width = node_size.get('width') or 360
    height = node_size.get('height') or 450
    inner_width = max(width - PAGE_NODE_LAYOUT['padding_x'] * 2, 40)
    inner_height = max(
        height - PAGE_NODE_LAYOUT['header_height'] - PAGE_NODE_LAYOUT['footer_height'] -
        PAGE_NODE_LAYOUT['padding_y'] * 2,
        40,
    )
    return build_flow_rect(
        PAGE_NODE_LAYOUT['padding_x'],
        PAGE_NODE_LAYOUT['header_height'] + PAGE_NODE_LAYOUT['padding_y'],
        inner_width,
        inner_height,
    )


def build_iframe_inner_rect(outer_rect):
    return build_flow_rect(
        outer_rect['left'] + 12,
        outer_rect['top'] + 42,
        max(outer_rect['width'] - 24, 40),
        max(outer_rect['height'] - 54, 40),
    )


def create_flow_directional_ports(id_prefix, rect, wall='component', data=None):
    data = data or {}
    return [
        {
            'id': f'{id_prefix}-top-in',
            'group': 'dynamic-in',
            'args': {'x': rect['center_x'], 'y': rect['top']},
            'data': {**data, 'wall': wall, 'side': 'top', 'direction': 'in'},
        },
        {
            'id': f'{id_prefix}-left-in',
            'group': 'dynamic-in',
            'args': {'x': rect['left'], 'y': rect['center_y']},
            'data': {**data, 'wall': wall, 'side': 'left', 'direction': 'in'},
        },
        {
            'id': f'{id_prefix}-bottom-out',
            'group': 'dynamic-out',
            'args': {'x': rect['center_x'], 'y': rect['bottom']},
            'data': {**data, 'wall': wall, 'side': 'bottom', 'direction': 'out'},
        },
        {
            'id': f'{id_prefix}-right-out',
            'group': 'dynamic-out',
            'args': {'x': rect['right'], 'y': rect['center_y']},
            'data': {**data, 'wall': wall, 'side': 'right', 'direction': 'out'},
        },
    ]


def build_component_layouts_for_ports(components, node_size):
    ordered_components = sorted(
        components or [],
        key=lambda component: component.get('order', component.get('zIndex', 0)),
    )
    children_by_parent = {}
    for component in ordered_components:
        parent_id = component.get('parentId') or '__root__'
        children_by_parent.setdefault(parent_id, []).append(component)

    layouts = []

    def visit(parent_id, parent_rect, depth=0):
        for component in children_by_parent.get(parent_id, []):
            position = component.get('position') if isinstance(component.get('position'), dict) else {}
            size = get_flow_component_size(component)
            center_x = parent_rect['left'] + parent_rect['width'] * (float(position.get('x') or 50) / 100)
            center_y = parent_rect['top'] + parent_rect['height'] * (float(position.get('y') or 50) / 100)
            rect = build_flow_rect(
                center_x - size['width'] / 2,
                center_y - size['height'] / 2,
                size['width'],
                size['height'],
            )
            inner_rect = build_iframe_inner_rect(rect) if component.get('type') == 'iframe' else None
            layouts.append({
                'component': component,
                'rect': rect,
                'inner_rect': inner_rect,
                'depth': depth,
                'parent_id': component.get('parentId') or None,
            })
            if component.get('type') == 'iframe' and inner_rect:
                visit(component.get('id'), inner_rect, depth + 1)

    visit('__root__', build_page_inner_rect(node_size))
    return layouts


def build_page_ports(node_size, components):
    width = node_size.get('width') or 360
    height = node_size.get('height') or 450
    page_outer_rect = build_flow_rect(0, 0, width, height)
    ports = create_flow_directional_ports(
        'page',
        page_outer_rect,
        'shared',
        {'scopeType': 'page', 'scopeId': 'page'},
    )

    for layout in build_component_layouts_for_ports(components, node_size):
        component = layout['component']
        base_data = {
            'scopeType': 'iframe' if component.get('type') == 'iframe' else 'component',
            'scopeId': component.get('id'),
            'componentId': component.get('id'),
            'componentType': component.get('type'),
            'elementId': component.get('elementId'),
            'elementType': component.get('elementData', {}).get('type') or component.get('type'),
            'elementText': component.get('elementData', {}).get('text') or component.get('elementId') or component.get('type'),
            'parentId': component.get('parentId'),
        }
        if component.get('type') == 'iframe' and layout.get('inner_rect'):
            ports.extend(create_flow_directional_ports(
                f'iframe-{component["id"]}',
                layout['rect'],
                'shared',
                base_data,
            ))
            continue
        ports.extend(create_flow_directional_ports(
            f'component-{component["id"]}',
            layout['rect'],
            'component',
            base_data,
        ))
    return {'items': ports}


def build_flow_edge(edge_id, source_cell, source_port, target_cell, target_port, label=''):
    source = {'cell': source_cell}
    target = {'cell': target_cell}
    if source_port:
        source['port'] = source_port
    if target_port:
        target['port'] = target_port

    edge = {
        'id': edge_id,
        'shape': 'edge',
        'source': source,
        'target': target,
        'router': {'name': 'manhattan'},
        'connector': {'name': 'rounded'},
        'attrs': {
            'line': {
                'stroke': '#5F95FF',
                'strokeWidth': 3,
                'targetMarker': {'name': 'classic', 'size': 8},
            }
        },
        'zIndex': 1000,
    }
    if label:
        edge['labels'] = [{'attrs': {'text': {'text': label}}}]
    return edge


def build_recording_page_layout(group_index, node_size, current_layout):
    column_gap = 180
    row_gap = 140
    start_x = 320
    max_row_width = 2600
    current_layout.setdefault('x', start_x)

    if (
        current_layout['column'] > 0 and
        current_layout['x'] + node_size['width'] > start_x + max_row_width
    ):
        current_layout['y'] += current_layout['row_height'] + row_gap
        current_layout['row'] += 1
        current_layout['column'] = 0
        current_layout['row_height'] = 0
        current_layout['x'] = start_x

    position = {
        'x': current_layout['x'],
        'y': current_layout['y'],
        'row': current_layout['row'],
        'column': current_layout['column'],
        'width': node_size['width'],
        'height': node_size['height'],
    }

    current_layout['row_height'] = max(current_layout['row_height'], node_size['height'])
    current_layout['x'] += node_size['width'] + column_gap
    current_layout['column'] += 1
    return position


def collect_recording_system_page_groups(session, steps):
    groups_by_key = {}
    groups = []
    for step in steps:
        filename, content = resolve_recording_step_snapshot(step)
        page_info = build_recording_system_page_info(session, step)
        group_key = page_info.get('identity') or f'step:{step.step_number}'

        if group_key not in groups_by_key:
            groups_by_key[group_key] = {
                'key': group_key,
                'page_info': page_info,
                'steps': [],
                'step_snapshots': [],
                'step_element_map': {},
                'step_snapshot_data_map': {},
                'step_snapshot_elements_map': {},
                'canonical_filename': '',
                'content': '',
                'snapshot_files': [],
                'snapshot_contents': {},
                'enriched_element_signatures': set(),
            }
            groups.append(groups_by_key[group_key])

        group = groups_by_key[group_key]
        group['steps'].append(step)
        if filename:
            group['step_snapshots'].append({
                'step_id': step.id,
                'step_number': step.step_number,
                'filename': filename,
            })
            if filename not in group['snapshot_files']:
                group['snapshot_files'].append(filename)
        if filename and content:
            group['snapshot_contents'][step.step_number] = {
                'filename': filename,
                'content': content,
            }

    return groups


def prepare_recording_system_page_group(session, group, group_index):
    group_steps = group.get('steps') or []
    page_info = group.get('page_info') or {}
    canonical_filename = ''
    canonical_content = ''
    canonical_interactive_elements = []
    canonical_snapshot_metadata = {}
    group['step_snapshot_data_map'] = {}
    group['step_snapshot_elements_map'] = {}
    group['step_element_map'] = {}
    group['enriched_element_signatures'] = set()

    for step in group_steps:
        step_filename, step_content = resolve_recording_step_snapshot(step)
        parsed_content = step_content or '- document:\n'
        parsed = parse_snapshot_content(parsed_content)
        interactive_elements = list(parsed.get('interactive_elements') or [])
        enriched_elements = []

        element_data, was_added = ensure_recorded_element_in_snapshot(interactive_elements, step)
        group['step_element_map'][step.step_number] = element_data
        group['step_snapshot_elements_map'][step.step_number] = interactive_elements

        if was_added:
            enriched_elements.append(element_data)
            group['enriched_element_signatures'].add(build_recording_snapshot_element_signature(element_data))

        if enriched_elements:
            parsed_content = append_recorded_elements_to_snapshot_content(parsed_content, enriched_elements)
            if step_filename:
                write_snapshot_content(step_filename, parsed_content)

        if step_filename:
            update_snapshot_parse_metadata(step_filename, parsed_content, interactive_elements)
            try:
                _, file_path = resolve_snapshot_file_path(step_filename, must_exist=True)
                file_stat = os.stat(file_path)
                metadata = {
                    'size': file_stat.st_size,
                    'createdAt': file_stat.st_ctime,
                    'modifiedAt': file_stat.st_mtime,
                }
            except Exception:
                metadata = {}
            step_snapshot_data = {
                'filename': step_filename,
                'pageName': page_info.get('name') or step.page_title or step.page_url or step_filename,
                'content': parsed_content,
                'interactiveElements': interactive_elements,
                'metadata': {
                    **metadata,
                    'contentHash': build_snapshot_content_hash(parsed_content),
                    'enrichedElementCount': len(enriched_elements),
                },
                'parseStatus': SNAPSHOT_PARSE_STATUS_SUCCESS,
                'parsedAt': time.time(),
            }
            group['step_snapshot_data_map'][step.step_number] = step_snapshot_data
            if not canonical_filename:
                canonical_filename = step_filename
                canonical_content = parsed_content
                canonical_interactive_elements = interactive_elements
                canonical_snapshot_metadata = dict(step_snapshot_data.get('metadata') or {})

    if not canonical_filename:
        fallback_content = canonical_content or '- document:\n'
        canonical_filename = create_recording_flow_snapshot_file(session, group_index, fallback_content)
        canonical_content = fallback_content
        canonical_interactive_elements = list((parse_snapshot_content(fallback_content).get('interactive_elements') or []))
        update_snapshot_parse_metadata(canonical_filename, canonical_content, canonical_interactive_elements)
        try:
            _, file_path = resolve_snapshot_file_path(canonical_filename, must_exist=True)
            file_stat = os.stat(file_path)
            canonical_snapshot_metadata = {
                'size': file_stat.st_size,
                'createdAt': file_stat.st_ctime,
                'modifiedAt': file_stat.st_mtime,
            }
        except Exception:
            canonical_snapshot_metadata = {}

    group['canonical_filename'] = canonical_filename
    group['content'] = canonical_content
    group['snapshot_data'] = {
        'filename': canonical_filename,
        'pageName': page_info.get('name') or canonical_filename,
        'content': canonical_content,
        'interactiveElements': canonical_interactive_elements,
        'metadata': {
            **canonical_snapshot_metadata,
            'contentHash': build_snapshot_content_hash(canonical_content),
            'enrichedElementCount': len(group['enriched_element_signatures']),
            'snapshotCount': len(group.get('snapshot_files') or []),
        },
        'parseStatus': SNAPSHOT_PARSE_STATUS_SUCCESS,
        'parsedAt': time.time(),
    }
    return group


def build_recording_snapshot_reference(step, snapshot_data):
    snapshot_data = snapshot_data if isinstance(snapshot_data, dict) else {}
    metadata = snapshot_data.get('metadata') if isinstance(snapshot_data.get('metadata'), dict) else {}
    return {
        'filename': snapshot_data.get('filename') or '',
        'pageName': snapshot_data.get('pageName') or '',
        'contentHash': metadata.get('contentHash') or '',
        'stepNumber': getattr(step, 'step_number', None),
        'stepId': getattr(step, 'id', None),
        'parseStatus': snapshot_data.get('parseStatus') or '',
        'parsedAt': snapshot_data.get('parsedAt') or '',
    }


def build_recording_flow_data(session, steps=None, junk_steps=None):
    if steps is None:
        steps, junk_steps = get_recording_steps_for_flow(session)
    elif junk_steps is None:
        junk_steps = {}
    start_node_id = f'flow-start-{session.session_id}'
    end_node_id = f'flow-end-{session.session_id}'
    cells = [
        {
            'id': start_node_id,
            'shape': 'start-node',
            'x': 80,
            'y': 180,
            'width': 150,
            'height': 50,
            'label': '开始',
            'data': {
                'type': 'start',
                'config': {
                    'name': '开始',
                    'browserType': session.browser_type or 'chromium',
                    'url': session.target_url,
                    'headless': False,
                    'maximize': True,
                    'viewportWidth': 1920,
                    'viewportHeight': 1080,
                    'inputMode': 'literal',
                    'inputValue': '',
                    'inputReference': '',
                    'inputAlias': '',
                    'outputName': '',
                    'outputSource': 'none',
                    'outputValue': '',
                },
            },
        }
    ]

    groups = collect_recording_system_page_groups(session, steps)
    snapshot_summary_items = []
    page_node_infos = []
    page_layout = {
        'row': 0,
        'column': 0,
        'y': 80,
        'row_height': 0,
    }

    for group_index, group in enumerate(groups, start=1):
        prepared_group = prepare_recording_system_page_group(session, group, group_index)
        group_steps = prepared_group.get('steps') or []
        components = []
        iframe_components, step_iframe_map = build_iframe_components_for_steps(group_steps)
        nested_totals = {}
        root_step_total = 0
        for step in group_steps:
            parent_id = step_iframe_map.get(step.step_number)
            if parent_id:
                nested_totals[parent_id] = nested_totals.get(parent_id, 0) + 1
            else:
                root_step_total += 1
        total_components = root_step_total + len(iframe_components)
        nested_indexes = {}
        for iframe_index, iframe_component in enumerate(iframe_components):
            iframe_component['position'] = build_component_position(iframe_index, total_components)
        components.extend(iframe_components)
        root_component_index = len(iframe_components)

        for component_index, step in enumerate(group_steps):
            element_data = prepared_group['step_element_map'].get(step.step_number) or build_recorded_snapshot_element(step)
            component_type = get_visual_component_type(element_data.get('type'), step.action_type)
            component_id = f'recorded_component_{step.step_number:04d}'
            parent_id = step_iframe_map.get(step.step_number)
            step_snapshot_data = (prepared_group.get('step_snapshot_data_map') or {}).get(step.step_number) or {}
            snapshot_reference = build_recording_snapshot_reference(step, step_snapshot_data)
            if parent_id:
                nested_index = nested_indexes.get(parent_id, 0)
                nested_indexes[parent_id] = nested_index + 1
                position = build_nested_component_position(nested_index, nested_totals.get(parent_id, 1))
                z_index = 20 + nested_index
            else:
                position = build_component_position(root_component_index, total_components)
                z_index = root_component_index
                root_component_index += 1
            components.append({
                'id': component_id,
                'type': component_type,
                'parentId': parent_id or None,
                'elementId': element_data.get('id'),
                'elementData': element_data,
                'position': position,
                'zIndex': z_index,
                'order': z_index,
                'config': {
                    **build_component_config_for_step(component_type, step, element_data),
                    'recordingSnapshotFile': snapshot_reference.get('filename') or '',
                    'recordingSnapshotRef': snapshot_reference,
                    'recordingPageIdentity': prepared_group.get('page_info', {}).get('identity') or '',
                    'recordingPageName': prepared_group.get('page_info', {}).get('name') or '',
                    'recordingPagePath': prepared_group.get('page_info', {}).get('path') or '',
                },
            })

        execution_path = build_execution_path_for_components(components)
        node_size = build_recording_page_node_size(total_components, components)
        node_position = build_recording_page_layout(group_index, node_size, page_layout)
        page_node_id = f'flow-page-{session.session_id}-{group_index:04d}'
        page_node_infos.append({
            'id': page_node_id,
            **node_position,
        })
        page_name = prepared_group.get('page_info', {}).get('name') or prepared_group['snapshot_data']['pageName'] or f'页面 {group_index}'
        cells.append({
            'id': page_node_id,
            'shape': 'page-node',
            'x': node_position['x'],
            'y': node_position['y'],
            'width': node_size['width'],
            'height': node_size['height'],
            'data': {
                'type': 'page',
                'config': {
                    'name': page_name,
                    'pageName': page_name,
                    'snapshotFile': prepared_group.get('canonical_filename'),
                    'snapshotData': prepared_group['snapshot_data'],
                    'recordingPageIdentity': prepared_group.get('page_info', {}).get('identity') or '',
                    'recordingPagePath': prepared_group.get('page_info', {}).get('path') or '',
                    'recordingPageSource': prepared_group.get('page_info', {}).get('source') or '',
                    'description': f'由录制会话 {session.session_id} 自动创建',
                    'elements': [],
                    'innerComponents': components,
                    'executionPath': execution_path,
                    'inputMode': 'literal',
                    'inputValue': '',
                    'inputReference': '',
                    'inputAlias': '',
                    'outputName': '',
                    'outputSource': 'none',
                    'outputValue': '',
                },
            },
            'ports': build_page_ports(node_size, components),
        })
        snapshot_summary_items.append({
            'key': prepared_group.get('key'),
            'filename': prepared_group.get('canonical_filename'),
            'page_name': page_name,
            'page_identity': prepared_group.get('page_info', {}).get('identity') or '',
            'page_path': prepared_group.get('page_info', {}).get('path') or '',
            'snapshot_files': prepared_group.get('snapshot_files') or [],
            'steps': [step.step_number for step in group_steps],
            'step_count': len(group_steps),
            'enriched_element_count': len(prepared_group.get('enriched_element_signatures') or []),
            'snapshot_count': len(prepared_group.get('snapshot_files') or []),
        })

    if page_node_infos:
        first_page = page_node_infos[0]
        cells[0]['y'] = first_page['y'] + first_page['height'] / 2 - cells[0]['height'] / 2

    for index, page_node_info in enumerate(page_node_infos, start=1):
        if index == 1:
            source_cell = start_node_id
            source_port = 'out1'
            target_port = 'page-left-in'
        else:
            previous_page = page_node_infos[index - 2]
            source_cell = previous_page['id']
            if previous_page['row'] != page_node_info['row']:
                source_port = 'page-bottom-out'
                target_port = 'page-top-in'
            else:
                source_port = 'page-right-out'
                target_port = 'page-left-in'

        cells.append(build_flow_edge(
            f'flow-edge-{session.session_id}-{index:04d}',
            source_cell,
            source_port,
            page_node_info['id'],
            target_port
        ))

    if page_node_infos:
        last_page = page_node_infos[-1]
        end_x = last_page['x'] + last_page['width'] + 120
        end_y = last_page['y'] + last_page['height'] / 2 - 25
        previous_cell = last_page['id']
        previous_port = 'page-right-out'
    else:
        end_x = 320
        end_y = cells[0]['y']
        previous_cell = start_node_id
        previous_port = 'out1'

    cells.append({
        'id': end_node_id,
        'shape': 'end-node',
        'x': end_x,
        'y': end_y,
        'width': 150,
        'height': 50,
        'label': '结束',
        'data': {
            'type': 'end',
            'config': {
                'name': '结束',
                'generateReport': True,
                'inputMode': 'literal',
                'inputValue': '',
                'inputReference': '',
                'inputAlias': '',
                'outputName': '',
                'outputSource': 'none',
                'outputValue': '',
            },
        },
    })
    cells.append(build_flow_edge(
        f'flow-edge-{session.session_id}-end',
        previous_cell,
        previous_port,
        end_node_id,
        'in1'
    ))

    graph_data = {'cells': cells}
    snapshot_summary = {
        'unique_snapshot_count': len(snapshot_summary_items),
        'total_step_count': session.steps.count(),
        'flow_step_count': len(steps),
        'filtered_step_count': len(junk_steps or {}),
        'filtered_steps': [
            {
                'step_id': item.get('step_id'),
                'step_number': item.get('step_number'),
                'reason': item.get('reason'),
                'reason_label': item.get('reason_label'),
                'group_key': item.get('group_key') or '',
            }
            for item in sorted((junk_steps or {}).values(), key=lambda value: value.get('step_number') or 0)
        ],
        'deduplicated_snapshot_count': sum(max(0, len(item.get('snapshot_files') or []) - 1) for item in snapshot_summary_items),
        'enriched_element_count': sum(item['enriched_element_count'] for item in snapshot_summary_items),
        'snapshots': snapshot_summary_items,
        'grouping_strategy': 'system_page',
    }
    return {
        'session_id': session.session_id,
        'name': session.name,
        'target_url': session.target_url,
        'graph_data': graph_data,
        'snapshot_summary': snapshot_summary,
    }


def create_or_update_visual_flow_from_recording(session, user=None, flow_name='', force_new=False, allow_empty=False):
    if not allow_empty and not session.steps.exists():
        raise ValidationError('Recording session has no captured steps')

    flow_payload = build_recording_flow_data(session)
    existing_flow = None
    if not force_new:
        existing_flow = VisualFlow.objects.filter(
            source=VisualFlow.SOURCE_RECORDING,
            recording_session=session
        ).order_by('-updated_at', '-id').first()

    name = normalize_recording_scalar(flow_name) or f'{session.name or session.session_id} 自动流程'
    module = get_recording_session_module_metadata(session)
    module = {key: value for key, value in module.items() if value not in (None, '')}
    values = {
        'name': name,
        'description': f'由录制会话 {session.session_id} 自动创建',
        'source': VisualFlow.SOURCE_RECORDING,
        'status': VisualFlow.STATUS_DRAFT,
        'target_url': session.target_url or '',
        'browser_type': session.browser_type or 'chromium',
        'recording_session': session,
        'graph_data': flow_payload['graph_data'],
        'snapshot_summary': flow_payload['snapshot_summary'],
        'metadata': {
            'module': module,
            'recording_session_id': session.session_id,
            'recording_status': session.status,
            'recording_step_count': flow_payload['snapshot_summary'].get('total_step_count', 0),
            'recording_flow_step_count': flow_payload['snapshot_summary'].get('flow_step_count', 0),
            'recording_filtered_step_count': flow_payload['snapshot_summary'].get('filtered_step_count', 0),
            'generated_at': timezone.now().isoformat(),
        },
    }

    if existing_flow:
        for field, value in values.items():
            if field == 'name' and existing_flow.name and not flow_name:
                continue
            setattr(existing_flow, field, value)
        existing_flow.save()
        return existing_flow, False

    flow = VisualFlow.objects.create(
        flow_id=uuid.uuid4().hex[:16],
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        **values
    )
    return flow, True


def get_visual_flow_graph_cells(flow):
    graph_data = flow.graph_data if isinstance(flow.graph_data, dict) else {}
    cells = graph_data.get('cells')
    return cells if isinstance(cells, list) else []


def recording_page_iframe_execution_path_missing(config):
    if not isinstance(config, dict):
        return False
    components = config.get('innerComponents')
    if not isinstance(components, list):
        return False

    iframe_ids = {
        str(component.get('id'))
        for component in components
        if isinstance(component, dict) and component.get('type') == 'iframe' and component.get('id')
    }
    if not iframe_ids:
        return False

    has_iframe_child_action = any(
        isinstance(component, dict) and
        component.get('type') != 'iframe' and
        str(component.get('parentId') or '') in iframe_ids
        for component in components
    )
    if not has_iframe_child_action:
        return False

    execution_path = config.get('executionPath')
    if not isinstance(execution_path, list) or not execution_path:
        return True

    def endpoint_references_iframe(endpoint):
        if not isinstance(endpoint, dict):
            return False
        component_id = str(endpoint.get('componentId') or endpoint.get('scopeId') or '')
        port_id = str(endpoint.get('portId') or '')
        if component_id in iframe_ids:
            return True
        return any(port_id.startswith(f'iframe-{iframe_id}-') for iframe_id in iframe_ids)

    return not any(
        endpoint_references_iframe(step.get('from')) or endpoint_references_iframe(step.get('to'))
        for step in execution_path
        if isinstance(step, dict)
    )


def should_refresh_recording_visual_flow(flow):
    if flow.source != VisualFlow.SOURCE_RECORDING or not flow.recording_session_id:
        return False

    metadata = flow.metadata if isinstance(flow.metadata, dict) else {}
    snapshot_summary = flow.snapshot_summary if isinstance(flow.snapshot_summary, dict) else {}
    recorded_status = normalize_recording_scalar(metadata.get('recording_status'))
    current_status = normalize_recording_scalar(flow.recording_session.status)
    if recorded_status != current_status:
        return True

    current_step_count = flow.recording_session.steps.count()
    recorded_step_count = normalize_optional_int(metadata.get('recording_step_count'))
    if recorded_step_count is None:
        recorded_step_count = normalize_optional_int(snapshot_summary.get('total_step_count'))
    if recorded_step_count is None or recorded_step_count != current_step_count:
        return True

    cells = get_visual_flow_graph_cells(flow)
    if not cells:
        return True

    if current_step_count == 0:
        return False

    edges = [cell for cell in cells if cell.get('shape') == 'edge']
    page_cells = [
        cell for cell in cells
        if cell.get('data', {}).get('type') == 'page'
    ]
    if not page_cells:
        return True

    page_ids = {cell.get('id') for cell in page_cells if cell.get('id')}
    cross_cell_edges = [
        edge for edge in edges
        if (edge.get('source') or {}).get('cell') != (edge.get('target') or {}).get('cell')
    ]
    if not edges:
        return True
    if len(cross_cell_edges) < len(page_cells):
        return True

    pages_with_components = 0
    pages_with_execution_path = 0
    for page_cell in page_cells:
        config = page_cell.get('data', {}).get('config', {})
        components = config.get('innerComponents')
        execution_path = config.get('executionPath')
        if isinstance(components, list) and components:
            pages_with_components += 1
            if recording_page_iframe_execution_path_missing(config):
                return True
            if isinstance(execution_path, list) and execution_path:
                pages_with_execution_path += 1
            else:
                return True

    return pages_with_components != pages_with_execution_path


def refresh_recording_visual_flow_if_needed(flow):
    if not should_refresh_recording_visual_flow(flow):
        return flow, False

    flow_payload = build_recording_flow_data(flow.recording_session)
    metadata = flow.metadata if isinstance(flow.metadata, dict) else {}
    flow.graph_data = flow_payload['graph_data']
    flow.snapshot_summary = flow_payload['snapshot_summary']
    flow.metadata = {
        **metadata,
        'recording_session_id': flow.recording_session.session_id,
        'recording_status': flow.recording_session.status,
        'recording_step_count': flow_payload['snapshot_summary'].get('total_step_count', 0),
        'recording_flow_step_count': flow_payload['snapshot_summary'].get('flow_step_count', 0),
        'recording_filtered_step_count': flow_payload['snapshot_summary'].get('filtered_step_count', 0),
        'auto_refreshed_at': timezone.now().isoformat(),
        'auto_refreshed_reason': 'missing_recording_flow_edges',
    }
    flow.save(update_fields=['graph_data', 'snapshot_summary', 'metadata', 'updated_at'])
    return flow, True


def resolve_flow_copy_version(version_id):
    normalized_version_id = normalize_version_id(version_id)
    if normalized_version_id is None:
        raise ValidationError('请选择版本号')
    version = Version.objects.prefetch_related('projects').filter(id=normalized_version_id).first()
    if not version:
        raise NotFound('版本不存在')
    return version


def get_flow_copy_source_id(flow):
    metadata = flow.metadata if isinstance(flow.metadata, dict) else {}
    return str(metadata.get('copy_source_flow_id') or flow.flow_id or '').strip()


def visual_flow_copy_exists(source_flow, version):
    source_key = get_flow_copy_source_id(source_flow)
    if not source_key or not version:
        return False
    source_module = get_visual_flow_module_metadata(source_flow)
    if str(source_module.get('version_id') or '') == str(version.id):
        return True
    return VisualFlow.objects.filter(
        models.Q(metadata__copy_source_flow_id=source_key) |
        models.Q(metadata__copied_from_flow_id=source_key),
    ).filter(
        models.Q(metadata__module__version_id=version.id) |
        models.Q(metadata__version_id=version.id)
    ).exists()


def build_visual_flow_copy_payload(source_flow, request_data, version, *, batch=False):
    data = request_data if isinstance(request_data, dict) else {}
    metadata = copy.deepcopy(source_flow.metadata if isinstance(source_flow.metadata, dict) else {})
    module_payload = extract_module_payload({
        **get_visual_flow_module_metadata(source_flow),
        **data,
        'version_id': version.id,
        'version_name': version.name,
    })
    metadata = apply_module_metadata(metadata, module_payload)
    metadata = apply_flow_copy_version_metadata(metadata, version)
    metadata['copy_source_flow_id'] = get_flow_copy_source_id(source_flow)
    metadata['copied_from_flow_id'] = source_flow.flow_id
    metadata['copied_at'] = timezone.now().isoformat()

    name = source_flow.name
    if not batch and 'name' in data:
        name = normalize_recording_scalar(data.get('name'), 200)
        if not name:
            raise ValidationError('流程名称不能为空')

    flow_status = data.get('status') if not batch else source_flow.status
    if flow_status not in dict(VisualFlow.STATUS_CHOICES):
        flow_status = source_flow.status or VisualFlow.STATUS_DRAFT

    return {
        'flow_id': uuid.uuid4().hex[:16],
        'name': name,
        'description': data.get('description') if (not batch and 'description' in data) else source_flow.description,
        'source': source_flow.source,
        'status': flow_status,
        'target_url': data.get('target_url') if (not batch and 'target_url' in data) else source_flow.target_url,
        'browser_type': data.get('browser_type') if (not batch and 'browser_type' in data) else source_flow.browser_type,
        'recording_session': source_flow.recording_session,
        'graph_data': copy.deepcopy(source_flow.graph_data if isinstance(source_flow.graph_data, dict) else {'cells': []}),
        'snapshot_summary': copy.deepcopy(source_flow.snapshot_summary if isinstance(source_flow.snapshot_summary, dict) else {}),
        'metadata': metadata,
    }


def create_visual_flow_copy(source_flow, request, version, *, batch=False):
    if visual_flow_copy_exists(source_flow, version):
        raise ValidationError('该版本下已存在同样流程')
    payload = build_visual_flow_copy_payload(source_flow, request.data if request else {}, version, batch=batch)
    return VisualFlow.objects.create(
        created_by=request.user if request and request.user.is_authenticated else None,
        **payload,
    )


def is_recording_step_snapshot_file(session, filename):
    normalized = normalize_recording_scalar(filename)
    if not normalized:
        return False
    pattern = rf'recording-{re.escape(session.session_id)}-step-\d{{4}}\.ya?ml'
    return re.fullmatch(pattern, normalized, flags=re.IGNORECASE) is not None


def is_snapshot_file_referenced_by_flow(session, filename):
    if not filename:
        return False
    flows = VisualFlow.objects.filter(recording_session=session).only('graph_data', 'snapshot_summary')
    for flow in flows:
        payload = json.dumps({
            'graph_data': flow.graph_data,
            'snapshot_summary': flow.snapshot_summary,
        }, ensure_ascii=False)
        if filename in payload:
            return True
    return False


def can_delete_deduped_snapshot_file(session, filename):
    if not is_recording_step_snapshot_file(session, filename):
        return False
    if PlaywrightRecordingStep.objects.filter(snapshot_filename=filename).exists():
        return False
    for step in PlaywrightRecordingStep.objects.filter(session=session).order_by('step_number'):
        resolved_filename, _ = resolve_recording_step_snapshot(step)
        if resolved_filename == filename:
            return False
    return not is_snapshot_file_referenced_by_flow(session, filename)


def delete_deduped_snapshot_file_if_unused(session, filename):
    if not can_delete_deduped_snapshot_file(session, filename):
        return False
    try:
        normalized_filename, file_path = resolve_snapshot_file_path(filename, must_exist=True)
        os.remove(file_path)
        delete_snapshot_metadata(normalized_filename)
        return True
    except (FileNotFoundError, ValueError, OSError):
        return False


def dedupe_recording_snapshots(session):
    steps = list(session.steps.order_by('step_number'))
    canonical_by_key = {}
    duplicate_groups = []
    duplicate_filenames = set()
    updated_step_ids = set()

    for step in steps:
        filename, content = resolve_recording_step_snapshot(step)
        if filename and step.snapshot_filename != filename:
            step.snapshot_filename = filename
            step.save(update_fields=['snapshot_filename'])
            updated_step_ids.add(step.id)

        content_hash = build_snapshot_content_hash(content)
        if not filename or not content_hash:
            continue

        key = f'{build_recording_page_identity(step)}:{content_hash}'
        group = canonical_by_key.get(key)
        if not group:
            group = {
                'key': key,
                'page_url': step.page_url,
                'page_title': step.page_title,
                'content_hash': content_hash,
                'canonical_step_id': step.id,
                'canonical_step_number': step.step_number,
                'canonical_filename': filename,
                'duplicate_step_ids': [],
                'duplicate_step_numbers': [],
                'duplicate_filenames': set(),
            }
            canonical_by_key[key] = group
            continue

        group['duplicate_step_ids'].append(step.id)
        group['duplicate_step_numbers'].append(step.step_number)
        if filename != group['canonical_filename']:
            group['duplicate_filenames'].add(filename)
            duplicate_filenames.add(filename)
        if step.snapshot_filename != group['canonical_filename']:
            step.snapshot_filename = group['canonical_filename']
            step.save(update_fields=['snapshot_filename'])
            updated_step_ids.add(step.id)

    deleted_filenames = []
    kept_duplicate_filenames = []
    for filename in sorted(duplicate_filenames):
        if delete_deduped_snapshot_file_if_unused(session, filename):
            deleted_filenames.append(filename)
        else:
            kept_duplicate_filenames.append(filename)

    for group in canonical_by_key.values():
        if not group['duplicate_step_ids']:
            continue
        duplicate_groups.append({
            **group,
            'duplicate_filenames': sorted(group['duplicate_filenames']),
        })

    summary = {
        'total_step_count': len(steps),
        'duplicate_group_count': len(duplicate_groups),
        'updated_step_count': len(updated_step_ids),
        'deleted_snapshot_count': len(deleted_filenames),
        'kept_duplicate_snapshot_count': len(kept_duplicate_filenames),
        'deleted_filenames': deleted_filenames,
        'kept_duplicate_filenames': kept_duplicate_filenames,
        'groups': duplicate_groups,
    }

    metadata = dict(session.metadata or {})
    metadata['last_snapshot_dedupe'] = {
        **summary,
        'deduped_at': timezone.now().isoformat(),
    }
    session.metadata = metadata
    session.save(update_fields=['metadata', 'updated_at'])
    return summary


def build_local_agent_metadata(request, session_id, token):
    now = time.time()
    expires_at = now + LOCAL_AGENT_PAIRING_TTL_SECONDS
    pairing_url = get_local_agent_pairing_url(request, session_id)
    api_origin = request.build_absolute_uri('/api').rstrip('/')
    return {
        'active_recorder': True,
        'browser_access_mode': 'local_agent',
        'local_agent_status': 'waiting',
        'local_agent_pairing_url': pairing_url,
        'local_agent_api_origin': api_origin,
        'local_agent_token_hash': hash_local_agent_token(token),
        'local_agent_token_expires_at': expires_at,
        'local_agent_token_expires_at_iso': datetime.fromtimestamp(expires_at).isoformat(),
        'local_agent_pairing_ttl_seconds': LOCAL_AGENT_PAIRING_TTL_SECONDS,
    }


def serialize_local_agent_session_payload(session, request):
    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    return {
        'session_id': session.session_id,
        'target_url': session.target_url,
        'browser_type': session.browser_type,
        'recording_method': session.recording_method,
        'recording_method_label': get_recording_method_label(session.recording_method),
        'recording_script': RECORDING_SCRIPT,
        'dom_snapshot_script': DOM_SNAPSHOT_SCRIPT,
        'poll_interval_ms': 600,
        'submit_url': request.build_absolute_uri(
            f'/api/testcases/playwright-recordings/{session.session_id}/agent/steps/'
        ),
        'status_url': request.build_absolute_uri(
            f'/api/testcases/playwright-recordings/{session.session_id}/agent/status/'
        ),
        'stop_url': request.build_absolute_uri(
            f'/api/testcases/playwright-recordings/{session.session_id}/agent/stop/'
        ),
        'token_expires_at': metadata.get('local_agent_token_expires_at_iso') or '',
    }


def local_agent_stop_request_is_stale(session):
    if session.status != PlaywrightRecordingSession.STATUS_STOPPING:
        return False

    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    if not metadata.get('stop_requested') and metadata.get('local_agent_status') != 'stop_requested':
        return False

    updated_at = session.updated_at
    if not updated_at:
        return False
    return timezone.now() - updated_at >= timedelta(seconds=LOCAL_AGENT_STALE_STOP_GRACE_SECONDS)


def complete_stale_local_agent_recording(session):
    metadata = dict(session.metadata or {})
    metadata['local_agent_status'] = 'stopped'
    metadata['active_recorder'] = False
    metadata['stop_requested'] = True
    metadata['stop_reason'] = 'local_agent_session_missing'
    session.status = PlaywrightRecordingSession.STATUS_COMPLETED
    session.stopped_at = timezone.now()
    session.metadata = metadata
    session.save(update_fields=['status', 'stopped_at', 'metadata', 'updated_at'])
    return session


LOCAL_AGENT_PACKAGE_FILES = [
    'local_playwright_agent.py',
    'start_local_playwright_agent.ps1',
    'start_local_playwright_agent.bat',
    'stop_local_playwright_agent.ps1',
    'stop_local_playwright_agent.bat',
    'register_local_playwright_agent.ps1',
    'testhub_agent_protocol.ps1',
    'uninstall_local_playwright_agent.ps1',
    'install_local_playwright_agent.ps1',
]

LOCAL_AGENT_PACKAGE_REQUIRED_MARKERS = {
    'local_playwright_agent.py': [
        "encoding='utf-8-sig'",
        "'platform_bound': bool(configured_platform_url)",
        'def is_allowed_agent_update_origin(self, platform_url',
        'return origin_matches_platform_url(origin, platform_url)',
    ],
    'install_local_playwright_agent.ps1': [
        '$configUtf8NoBom = New-Object System.Text.UTF8Encoding($false)',
        '[System.IO.File]::WriteAllText((Join-Path $InstallDir "agent_config.json"), $configJson, $configUtf8NoBom)',
    ],
}


def local_agent_package_dir_is_current(package_dir):
    for file_name, markers in LOCAL_AGENT_PACKAGE_REQUIRED_MARKERS.items():
        source_path = os.path.join(package_dir, file_name)
        try:
            with open(source_path, 'r', encoding='utf-8') as source_file:
                source = source_file.read()
        except OSError:
            return False
        if not all(marker in source for marker in markers):
            return False
    return True


def get_local_agent_package_dir():
    package_dir = os.path.join(settings.BASE_DIR, 'local-agent-package')
    if os.path.isdir(package_dir) and all(
        os.path.isfile(os.path.join(package_dir, file_name))
        for file_name in LOCAL_AGENT_PACKAGE_FILES
    ) and local_agent_package_dir_is_current(package_dir):
        return package_dir
    return os.path.join(settings.BASE_DIR, 'tools')


def build_local_agent_install_readme(platform_url):
    return '\n'.join([
        '# BearAI Local Agent 安装说明',
        '',
        '1. 解压本安装包。',
        '2. 双击 install.bat，或右键 install.ps1 选择“使用 PowerShell 运行”。',
        '3. 安装脚本会按顺序检查 Python 3.10+、pip 23.0+、requests 2.31.0+、playwright 1.44.0+、Playwright Chromium；缺失或版本过低时会自动安装/升级。',
        '4. 如果检测到 Python、pip、PyPI 或 Playwright 浏览器下载源超时、连接失败、域名解析失败，安装脚本会自动切换到可用国内镜像源并重试。',
        '5. 安装脚本会注册 testhub-agent:// 协议、用户登录自启动项，并启动本地 Agent。',
        '6. 安装完成后会自动检查 Agent 健康状态；回到 BearAI 页面也可点击“检测 Agent”确认状态。',
        '',
        f'平台地址: {platform_url}',
        '本地 Agent 健康检查: http://127.0.0.1:18765/health',
        '',
        '说明：浏览器网页不能无提示安装本机程序，首次安装需要用户确认系统安全提示。',
        '如果系统没有 Python，安装脚本会优先使用 winget 安装 Python；winget 不可用时会下载 python.org 官方安装器，并在源不可达时自动切换到国内镜像。',
        '后续可在平台页面直接启动、重启、升级或卸载本地 Agent。',
    ])


class PlaywrightLocalAgentPackageDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tools_dir = get_local_agent_package_dir()
        platform_url = request.build_absolute_uri('/').rstrip('/')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            missing_files = []
            for file_name in LOCAL_AGENT_PACKAGE_FILES:
                file_path = os.path.join(tools_dir, file_name)
                if not os.path.exists(file_path):
                    missing_files.append(file_name)
                    continue
                archive.write(file_path, arcname=file_name)

            if missing_files:
                return Response(
                    {
                        'error': '本地 Agent 安装包文件缺失：' + ', '.join(missing_files),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            bootstrap_script = '\n'.join([
                'param(',
                '    [string]$InstallDir = "",',
                '    [string]$Python = "python",',
                '    [switch]$SkipDependencyInstall',
                ')',
                '',
                '$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path',
                '$installer = Join-Path $scriptDir "install_local_playwright_agent.ps1"',
                'if (!(Test-Path -LiteralPath $installer)) { throw "install_local_playwright_agent.ps1 not found" }',
                '$installArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $installer, "-Python", $Python, "-PlatformUrl", "' + platform_url.replace('"', '`"') + '")',
                'if (![string]::IsNullOrWhiteSpace($InstallDir)) { $installArgs += @("-InstallDir", $InstallDir) }',
                'if ($SkipDependencyInstall) { $installArgs += "-SkipDependencyInstall" }',
                '& powershell @installArgs',
                'exit $LASTEXITCODE',
                '',
            ])
            bootstrap_batch = '\r\n'.join([
                '@echo off',
                'setlocal',
                'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*',
                'set EXIT_CODE=%ERRORLEVEL%',
                'if not "%EXIT_CODE%"=="0" pause',
                'exit /b %EXIT_CODE%',
                '',
            ])
            archive.writestr('install.ps1', bootstrap_script)
            archive.writestr('install.bat', bootstrap_batch)
            archive.writestr('README.md', build_local_agent_install_readme(platform_url))

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="testhub-local-agent.zip"'
        return response


def build_agent_step_snapshot_content(raw_payload):
    content = raw_payload.get('snapshot_content') or raw_payload.get('snapshot') or ''
    if isinstance(content, dict):
        content = content.get('content') or ''
    return sanitize_snapshot_content(content) if content else ''


def build_agent_screenshot_path(session, step_number, raw_payload):
    screenshot_path = normalize_recording_scalar(raw_payload.get('screenshot_path'), 500)
    screenshot_url = normalize_recording_scalar(raw_payload.get('screenshot_url'), 500)
    screenshot_base64 = raw_payload.get('screenshot_base64') or ''
    if screenshot_path:
        return screenshot_path
    if screenshot_url:
        return screenshot_url
    if not screenshot_base64:
        return ''

    try:
        if ',' in str(screenshot_base64)[:80]:
            screenshot_base64 = str(screenshot_base64).split(',', 1)[1]
        binary = base64.b64decode(screenshot_base64, validate=True)
    except (binascii.Error, ValueError, TypeError):
        return ''

    date_path = datetime.now().strftime('%Y/%m')
    relative_dir = os.path.join('playwright_recordings', date_path)
    screenshot_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
    os.makedirs(screenshot_dir, exist_ok=True)
    filename = f'{session.session_id}-step-{step_number:04d}.png'
    absolute_path = os.path.join(screenshot_dir, filename)
    try:
        with open(absolute_path, 'wb') as screenshot_file:
            screenshot_file.write(binary)
        return os.path.join(relative_dir, filename).replace('\\', '/')
    except OSError:
        return ''


def persist_local_agent_recording_step(session, raw_payload):
    event = raw_payload.get('event') if isinstance(raw_payload.get('event'), dict) else raw_payload
    event = sanitize_recording_payload(event if isinstance(event, dict) else {})
    page_title = normalize_snapshot_inline_text(
        raw_payload.get('page_title') or event.get('title') or event.get('page_title') or ''
    )[:500]
    page_url = normalize_recording_scalar(
        raw_payload.get('page_url') or event.get('url') or event.get('page_url') or '',
        4000,
    )
    action_type = normalize_recording_scalar(
        raw_payload.get('action_type') or event.get('action_type') or event.get('type') or 'action',
        40,
    ) or 'action'
    action_value = extract_recording_action_value(event)
    element = json_safe_recording_value(event.get('element') or raw_payload.get('element') or {})
    selectors = json_safe_recording_value(event.get('selectors') or raw_payload.get('selectors') or [])
    safe_agent_payload = {
        key: value
        for key, value in raw_payload.items()
        if key not in ('screenshot_base64', 'screenshot', 'snapshot_content', 'snapshot')
    }
    raw_event = json_safe_recording_value({**event, 'agent_payload': safe_agent_payload})

    with transaction.atomic():
        locked_session = PlaywrightRecordingSession.objects.select_for_update().get(id=session.id)
        if locked_session.status in (
            PlaywrightRecordingSession.STATUS_COMPLETED,
            PlaywrightRecordingSession.STATUS_FAILED,
        ):
            raise ValueError('录制会话已结束')
        max_step = locked_session.steps.aggregate(max_step=models.Max('step_number')).get('max_step') or 0
        step_number = max_step + 1
        snapshot_filename = f'recording-{locked_session.session_id}-step-{step_number:04d}.yml'
        snapshot_content = build_agent_step_snapshot_content(raw_payload)
        session_module = {}
        metadata = locked_session.metadata if isinstance(locked_session.metadata, dict) else {}
        if isinstance(metadata.get('module'), dict):
            session_module = metadata.get('module')

        if snapshot_content:
            step_label = f'{page_title or page_url or locked_session.session_id} step {step_number}'
            try:
                write_snapshot_file(
                    snapshot_filename,
                    snapshot_content,
                    overwrite=True,
                    page_name=step_label,
                    alias=step_label,
                    module=session_module if session_module else None,
                    creation_method=SNAPSHOT_CREATION_METHOD_LOCAL_AGENT_PLAYWRIGHT,
                )
            except Exception:
                snapshot_filename = ''
        else:
            snapshot_filename = ''

        screenshot_path = build_agent_screenshot_path(locked_session, step_number, raw_payload)
        step = PlaywrightRecordingStep.objects.create(
            session=locked_session,
            step_number=step_number,
            action_type=action_type,
            action_value=action_value,
            page_url=page_url,
            page_title=page_title,
            element=element if isinstance(element, dict) else {},
            selectors=selectors if isinstance(selectors, list) else [],
            snapshot_filename=snapshot_filename,
            screenshot_path=screenshot_path,
            raw_event=raw_event if isinstance(raw_event, dict) else {},
        )
        metadata = dict(locked_session.metadata or {})
        stop_requested = bool(metadata.get('stop_requested')) or metadata.get('local_agent_status') == 'stop_requested'
        metadata['last_step_number'] = step_number
        metadata['last_event_at'] = timezone.now().isoformat()
        metadata['local_agent_status'] = 'stop_requested' if stop_requested else 'recording'
        metadata['active_recorder'] = not stop_requested
        locked_session.metadata = metadata
        locked_session.status = (
            PlaywrightRecordingSession.STATUS_STOPPING
            if stop_requested else
            PlaywrightRecordingSession.STATUS_RECORDING
        )
        locked_session.save(update_fields=['metadata', 'status', 'updated_at'])
        return step


class PlaywrightRecordingSessionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cleanup_stale_recording_sessions()
        queryset = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related(
            Prefetch(
                'visual_flows',
                queryset=VisualFlow.objects.order_by('-updated_at', '-id'),
                to_attr='prefetched_visual_flows'
            )
        ).order_by('-started_at', '-id')

        keyword = (request.query_params.get('keyword') or request.query_params.get('search') or '').strip()
        recording_status = (request.query_params.get('status') or '').strip()
        recording_method = normalize_recording_method(request.query_params.get('recording_method'))
        if keyword:
            queryset = queryset.filter(
                models.Q(name__icontains=keyword) |
                models.Q(session_id__icontains=keyword) |
                models.Q(target_url__icontains=keyword) |
                models.Q(metadata__module__module_name__icontains=keyword) |
                models.Q(metadata__module__module_path__icontains=keyword)
            )
        if recording_status:
            queryset = queryset.filter(status=recording_status)
        if request.query_params.get('recording_method'):
            queryset = queryset.filter(recording_method=recording_method)
        module_path = normalize_recording_system_page_path(request.query_params.get('module_path'))
        module_name = normalize_recording_scalar(request.query_params.get('module_name'), 200)
        module_id = normalize_optional_int(request.query_params.get('module_id'))
        project_id = normalize_optional_int(request.query_params.get('project_id'))
        version_id = normalize_version_id(request.query_params.get('version_id') or request.query_params.get('version'))
        module_filter = build_json_module_scope_q(
            request,
            module_id=module_id,
            module_path=module_path,
            module_name=module_name,
            project_id=project_id,
            version_id=version_id,
            flow_prefix='metadata__module',
        )
        if module_filter:
            queryset = queryset.filter(module_filter)

        queryset, page_meta = paginate_queryset(request, queryset, default_page_size=20)

        serializer = PlaywrightRecordingSessionSerializer(
            queryset,
            many=True,
            context={
                'request': request,
                'include_steps': False,
                'include_latest_step': False,
            },
        )
        return Response({
            **page_meta,
            'active_session_ids': get_active_recording_ids(),
            'recorder_settings': build_recorder_settings_payload(),
            'results': serializer.data,
        })

    def post(self, request):
        try:
            target_url = normalize_target_url(request.data.get('target_url'))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        browser_type = normalize_browser_type(request.data.get('browser_type'))
        recording_method = normalize_recording_method(request.data.get('recording_method'))
        name = str(request.data.get('name') or '').strip()
        module = extract_module_payload(request.data)
        if not module.get('module_path') and not module.get('module_name'):
            return Response({'error': '启动录制前请先选择左侧目录树中的页面菜单节点'}, status=status.HTTP_400_BAD_REQUEST)
        metadata = {
            'client_ip': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'recording_method': recording_method,
        }
        metadata = apply_recording_module_metadata(metadata, module)
        session_id = uuid.uuid4().hex[:16]
        if recording_method == PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT:
            token = create_local_agent_token()
            metadata.update(build_local_agent_metadata(request, session_id, token))
        session = PlaywrightRecordingSession.objects.create(
            session_id=session_id,
            name=name or f'录制 {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
            target_url=target_url,
            browser_type=browser_type,
            recording_method=recording_method,
            status=PlaywrightRecordingSession.STATUS_STARTING,
            started_by=request.user if request.user.is_authenticated else None,
            metadata=metadata,
        )

        if recording_method == PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT:
            serializer = PlaywrightRecordingSessionSerializer(
                session,
                context={
                    'request': request,
                    'include_steps': False,
                    'include_latest_step': False,
                },
            )
            return Response({
                'message': '本地Agent- Playwright录制会话已创建，请启动本地 Agent 并使用配对 token 连接平台',
                'session': serializer.data,
                'agent': {
                    'token': token,
                    'pairing_url': metadata.get('local_agent_pairing_url'),
                    'api_origin': metadata.get('local_agent_api_origin'),
                    'expires_at': metadata.get('local_agent_token_expires_at_iso'),
                },
            }, status=status.HTTP_201_CREATED)

        try:
            start_recording_session(session)
            session.refresh_from_db()
        except RecordingStartError as exc:
            session.status = PlaywrightRecordingSession.STATUS_FAILED
            session.error_message = str(exc)
            session.stopped_at = timezone.now()
            session.save(update_fields=['status', 'error_message', 'stopped_at', 'updated_at'])
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            session.status = PlaywrightRecordingSession.STATUS_FAILED
            session.error_message = str(exc)
            session.stopped_at = timezone.now()
            session.save(update_fields=['status', 'error_message', 'stopped_at', 'updated_at'])
            return Response({'error': f'启动录制失败: {str(exc)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = PlaywrightRecordingSessionSerializer(
            session,
            context={
                'request': request,
                'include_steps': False,
                'include_latest_step': False,
            },
        )
        return Response({
            'message': '录制任务已启动，请在平台弹出的受控浏览器中操作',
            'session': serializer.data,
        }, status=status.HTTP_201_CREATED)


class PlaywrightRecordingScriptGenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        instruction = normalize_recording_script_generation_text(request.data.get('instruction'), limit=8000)
        if not instruction:
            return Response({'error': '请输入自然语言录制需求'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_url = normalize_target_url(request.data.get('target_url'))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        module = request.data.get('module') if isinstance(request.data.get('module'), dict) else extract_module_payload(request.data)
        capability_id = request.data.get('capability_id') or request.data.get('skill_id')
        model_config_id = request.data.get('model_config_id')

        try:
            skill = select_recording_script_skill(capability_id)
        except ValidationError as exc:
            detail = exc.detail if hasattr(exc, 'detail') else str(exc)
            if isinstance(detail, list):
                detail = '；'.join(str(item) for item in detail)
            return Response({'error': str(detail)}, status=status.HTTP_400_BAD_REQUEST)

        if not skill:
            skill = ensure_default_recording_script_skill()

        model_config = None
        generation_source = 'llm'
        fallback_reason = ''
        try:
            model_config = select_recording_script_llm_config(model_config_id)
            system_prompt, user_prompt = build_recording_script_generation_prompt(
                instruction=instruction,
                target_url=target_url,
                module=module,
                skill=skill,
            )
            raw_answer = call_recording_script_llm(
                model_config,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            parsed = parse_recording_script_generation_json(raw_answer)
            normalized = normalize_recording_script_generation_payload(parsed)
        except ValidationError as exc:
            detail = exc.detail if hasattr(exc, 'detail') else str(exc)
            if isinstance(detail, list):
                detail = '；'.join(str(item) for item in detail)
            fallback_reason = str(detail)
            generation_source = 'deterministic_fallback'
            normalized = build_recording_script_fallback_payload(
                instruction=instruction,
                target_url=target_url,
                module=module,
                skill=skill,
                ai_error=fallback_reason,
            )
        except Exception as exc:
            fallback_reason = str(exc)
            generation_source = 'deterministic_fallback'
            normalized = build_recording_script_fallback_payload(
                instruction=instruction,
                target_url=target_url,
                module=module,
                skill=skill,
                ai_error=fallback_reason,
            )

        touch_recording_script_skill(skill)
        return Response({
            **normalized,
            'generation_source': generation_source,
            'fallback_reason': fallback_reason,
            'model': {
                'id': model_config.id,
                'name': model_config.name,
                'ai_tool': model_config.ai_tool,
                'llm_model': model_config.llm_model,
            } if model_config else None,
            'capability': {
                'id': skill.id,
                'code': skill.code,
                'name': skill.name,
                'kind': skill.kind,
                'version': skill.version,
            },
            'target_url': target_url,
            'module': module,
        })


def format_drf_validation_error(exc):
    detail = exc.detail if hasattr(exc, 'detail') else str(exc)
    if isinstance(detail, dict):
        return '；'.join(f'{key}: {value}' for key, value in detail.items())
    if isinstance(detail, list):
        return '；'.join(str(item) for item in detail)
    return str(detail)


def normalize_automation_script_json(value):
    return dict(value) if isinstance(value, dict) else {}


def normalize_automation_script_list(value):
    return list(value) if isinstance(value, list) else []


def build_automation_script_default_name(module):
    module_name = ''
    if isinstance(module, dict):
        module_name = module.get('module_name') or module.get('module_path') or ''
    if module_name:
        return f'{module_name} 自动化脚本'
    return f'自动化脚本 {timezone.now().strftime("%Y-%m-%d %H:%M")}'


def normalize_automation_script_payload(data, existing=None):
    if not isinstance(data, dict):
        data = {}

    raw_script = data.get('script') if data.get('script') is not None else data.get('script_content')
    if raw_script is None and existing is not None:
        script_content = existing.script or ''
    else:
        script_content = str(raw_script or '').strip()
    if not script_content:
        raise ValidationError('脚本内容不能为空')

    raw_target_url = data.get('target_url')
    if raw_target_url in (None, ''):
        target_url = existing.target_url if existing is not None else ''
    else:
        try:
            target_url = normalize_target_url(raw_target_url)
        except ValueError as exc:
            raise ValidationError(str(exc))

    module = extract_module_payload(data)
    if not module and existing is not None:
        module = existing.module if isinstance(existing.module, dict) else {}

    default_name = existing.name if existing is not None else build_automation_script_default_name(module)
    name = normalize_recording_scalar(data.get('name') or default_name, 200) or default_name
    description = normalize_recording_script_generation_text(
        data.get('description') if data.get('description') is not None else getattr(existing, 'description', ''),
        limit=4000,
    )
    instruction = normalize_recording_script_generation_text(
        data.get('instruction') if data.get('instruction') is not None else getattr(existing, 'instruction', ''),
        limit=12000,
    )
    summary = normalize_recording_script_generation_text(
        data.get('summary') if data.get('summary') is not None else getattr(existing, 'summary', ''),
        limit=8000,
    )

    warnings = (
        normalize_automation_script_list(data.get('warnings'))
        if 'warnings' in data
        else normalize_automation_script_list(getattr(existing, 'warnings', []))
    )
    planned_actions = (
        normalize_automation_script_list(data.get('planned_actions'))
        if 'planned_actions' in data
        else normalize_automation_script_list(getattr(existing, 'planned_actions', []))
    )
    generation_source = normalize_recording_scalar(
        data.get('generation_source') if data.get('generation_source') is not None else getattr(existing, 'generation_source', ''),
        60,
    )
    fallback_reason = normalize_recording_script_generation_text(
        data.get('fallback_reason') if data.get('fallback_reason') is not None else getattr(existing, 'fallback_reason', ''),
        limit=4000,
    )
    model_payload = (
        normalize_automation_script_json(data.get('model'))
        if 'model' in data
        else normalize_automation_script_json(getattr(existing, 'model', {}))
    )
    capability_payload = (
        normalize_automation_script_json(data.get('capability'))
        if 'capability' in data
        else normalize_automation_script_json(getattr(existing, 'capability', {}))
    )
    metadata = (
        normalize_automation_script_json(data.get('metadata'))
        if 'metadata' in data
        else normalize_automation_script_json(getattr(existing, 'metadata', {}))
    )
    metadata = apply_module_metadata(metadata, module)
    change_summary = normalize_recording_scalar(data.get('change_summary'), 500)

    project_id = normalize_optional_int(module.get('project_id'))
    version_id = normalize_version_id(module.get('version_id'))
    project = Project.objects.filter(pk=project_id).first() if project_id is not None else None
    version = Version.objects.filter(pk=version_id).first() if version_id is not None else None

    return {
        'name': name,
        'description': description,
        'target_url': target_url,
        'instruction': instruction,
        'script': script_content,
        'summary': summary,
        'warnings': warnings,
        'planned_actions': planned_actions,
        'generation_source': generation_source,
        'fallback_reason': fallback_reason,
        'module': module,
        'model': model_payload,
        'capability': capability_payload,
        'metadata': metadata,
        'project': project,
        'version_obj': version,
        'module_id': normalize_optional_int(module.get('module_id')),
        'module_name': normalize_recording_scalar(module.get('module_name'), 200),
        'module_path': normalize_recording_scalar(module.get('module_path'), 500),
        'change_summary': change_summary,
    }


def apply_automation_script_payload(script_obj, payload, user):
    script_obj.name = payload['name']
    script_obj.description = payload['description']
    script_obj.target_url = payload['target_url']
    script_obj.instruction = payload['instruction']
    script_obj.script = payload['script']
    script_obj.summary = payload['summary']
    script_obj.warnings = payload['warnings']
    script_obj.planned_actions = payload['planned_actions']
    script_obj.generation_source = payload['generation_source']
    script_obj.fallback_reason = payload['fallback_reason']
    script_obj.module = payload['module']
    script_obj.model = payload['model']
    script_obj.capability = payload['capability']
    script_obj.metadata = payload['metadata']
    script_obj.project = payload['project']
    script_obj.version = payload['version_obj']
    script_obj.module_id = payload['module_id']
    script_obj.module_name = payload['module_name']
    script_obj.module_path = payload['module_path']
    script_obj.updated_by = user if getattr(user, 'is_authenticated', False) else None
    return script_obj


def create_automation_script_version(script_obj, payload, user):
    latest_version = script_obj.versions.aggregate(max_version=models.Max('version')).get('max_version') or 0
    next_version = max(latest_version, script_obj.latest_version or 0) + 1
    version_record = PlaywrightAutomationScriptVersion.objects.create(
        script=script_obj,
        version=next_version,
        name=payload['name'],
        target_url=payload['target_url'],
        instruction=payload['instruction'],
        script_content=payload['script'],
        summary=payload['summary'],
        warnings=payload['warnings'],
        planned_actions=payload['planned_actions'],
        generation_source=payload['generation_source'],
        fallback_reason=payload['fallback_reason'],
        module=payload['module'],
        model=payload['model'],
        capability=payload['capability'],
        metadata=payload['metadata'],
        change_summary=payload.get('change_summary') or f'保存 v{next_version}',
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    apply_automation_script_payload(script_obj, payload, user)
    script_obj.latest_version = next_version
    script_obj.save(update_fields=[
        'name',
        'description',
        'target_url',
        'instruction',
        'script',
        'summary',
        'warnings',
        'planned_actions',
        'generation_source',
        'fallback_reason',
        'module',
        'model',
        'capability',
        'metadata',
        'project',
        'version',
        'module_id',
        'module_name',
        'module_path',
        'updated_by',
        'latest_version',
        'updated_at',
    ])
    return version_record


def get_automation_script_or_404(script_id):
    script = PlaywrightAutomationScript.objects.select_related(
        'created_by',
        'updated_by',
        'project',
        'version',
    ).filter(script_id=script_id).first()
    if not script:
        raise NotFound('自动化脚本不存在')
    return script


class PlaywrightAutomationScriptListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = PlaywrightAutomationScript.objects.select_related(
            'created_by',
            'updated_by',
            'project',
            'version',
        ).annotate(
            versions_count=models.Count('versions')
        ).order_by('-updated_at', '-id')

        keyword = (request.query_params.get('keyword') or request.query_params.get('search') or '').strip()
        if keyword:
            queryset = queryset.filter(
                models.Q(name__icontains=keyword) |
                models.Q(script_id__icontains=keyword) |
                models.Q(target_url__icontains=keyword) |
                models.Q(instruction__icontains=keyword) |
                models.Q(summary__icontains=keyword) |
                models.Q(module_name__icontains=keyword) |
                models.Q(module_path__icontains=keyword)
            )

        project_id = normalize_optional_int(request.query_params.get('project_id'))
        version_id = normalize_version_id(request.query_params.get('version_id') or request.query_params.get('version'))
        module_id = normalize_optional_int(request.query_params.get('module_id'))
        module_name = normalize_recording_scalar(request.query_params.get('module_name'), 200)
        module_path = normalize_recording_system_page_path(request.query_params.get('module_path'))

        module_filter = build_automation_script_module_scope_q(
            request,
            module_id=module_id,
            module_path=module_path,
            module_name=module_name,
            project_id=project_id,
            version_id=version_id,
        )
        if module_filter:
            queryset = queryset.filter(module_filter)

        queryset, page_meta = paginate_queryset(request, queryset, default_page_size=20, max_page_size=100)
        serializer = PlaywrightAutomationScriptSerializer(
            queryset,
            many=True,
            context={'request': request, 'include_latest_version': False},
        )
        return Response({
            **page_meta,
            'results': serializer.data,
        })

    def post(self, request):
        script_id = normalize_recording_scalar(request.data.get('script_id'), 64)
        try:
            with transaction.atomic():
                if script_id:
                    script_obj = PlaywrightAutomationScript.objects.select_for_update().filter(script_id=script_id).first()
                    if not script_obj:
                        return Response({'error': '自动化脚本不存在'}, status=status.HTTP_404_NOT_FOUND)
                    payload = normalize_automation_script_payload(request.data, existing=script_obj)
                    version_record = create_automation_script_version(script_obj, payload, request.user)
                    response_status = status.HTTP_200_OK
                else:
                    payload = normalize_automation_script_payload(request.data)
                    script_obj = PlaywrightAutomationScript.objects.create(
                        name=payload['name'],
                        description=payload['description'],
                        created_by=request.user if request.user.is_authenticated else None,
                        updated_by=request.user if request.user.is_authenticated else None,
                    )
                    version_record = create_automation_script_version(script_obj, payload, request.user)
                    response_status = status.HTTP_201_CREATED
        except ValidationError as exc:
            return Response({'error': format_drf_validation_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PlaywrightAutomationScriptSerializer(
            script_obj,
            context={'request': request, 'include_latest_version': True},
        )
        version_serializer = PlaywrightAutomationScriptVersionSerializer(version_record, context={'request': request})
        return Response({
            **serializer.data,
            'version_record': version_serializer.data,
        }, status=response_status)


class PlaywrightAutomationScriptDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, script_id):
        script_obj = get_automation_script_or_404(script_id)
        serializer = PlaywrightAutomationScriptSerializer(
            script_obj,
            context={'request': request, 'include_latest_version': True},
        )
        return Response(serializer.data)

    def patch(self, request, script_id):
        try:
            with transaction.atomic():
                script_obj = PlaywrightAutomationScript.objects.select_for_update().filter(script_id=script_id).first()
                if not script_obj:
                    raise NotFound('自动化脚本不存在')
                has_script_content = request.data.get('script') is not None or request.data.get('script_content') is not None
                create_version = bool(request.data.get('create_version', has_script_content))
                if create_version:
                    payload = normalize_automation_script_payload(request.data, existing=script_obj)
                    version_record = create_automation_script_version(script_obj, payload, request.user)
                else:
                    payload = normalize_automation_script_payload({**request.data, 'script': script_obj.script}, existing=script_obj)
                    apply_automation_script_payload(script_obj, payload, request.user)
                    script_obj.save()
                    version_record = None
        except ValidationError as exc:
            return Response({'error': format_drf_validation_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PlaywrightAutomationScriptSerializer(
            script_obj,
            context={'request': request, 'include_latest_version': True},
        )
        data = dict(serializer.data)
        if version_record is not None:
            data['version_record'] = PlaywrightAutomationScriptVersionSerializer(version_record, context={'request': request}).data
        return Response(data)

    def put(self, request, script_id):
        return self.patch(request, script_id)

    def delete(self, request, script_id):
        script_obj = get_automation_script_or_404(script_id)
        script_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlaywrightAutomationScriptVersionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, script_id):
        script_obj = get_automation_script_or_404(script_id)
        queryset = script_obj.versions.select_related('created_by').order_by('-version', '-id')
        serializer = PlaywrightAutomationScriptVersionSerializer(queryset, many=True, context={'request': request})
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
        })

    def post(self, request, script_id):
        try:
            with transaction.atomic():
                script_obj = PlaywrightAutomationScript.objects.select_for_update().filter(script_id=script_id).first()
                if not script_obj:
                    raise NotFound('自动化脚本不存在')
                payload = normalize_automation_script_payload(request.data, existing=script_obj)
                version_record = create_automation_script_version(script_obj, payload, request.user)
        except ValidationError as exc:
            return Response({'error': format_drf_validation_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

        script_serializer = PlaywrightAutomationScriptSerializer(
            script_obj,
            context={'request': request, 'include_latest_version': True},
        )
        version_serializer = PlaywrightAutomationScriptVersionSerializer(version_record, context={'request': request})
        return Response({
            'script': script_serializer.data,
            'version': version_serializer.data,
        }, status=status.HTTP_201_CREATED)


class PlaywrightAutomationScriptVersionRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, script_id, version):
        try:
            version_number = int(version)
        except (TypeError, ValueError):
            return Response({'error': '版本号无效'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                script_obj = PlaywrightAutomationScript.objects.select_for_update().filter(script_id=script_id).first()
                if not script_obj:
                    raise NotFound('自动化脚本不存在')
                source_version = script_obj.versions.filter(version=version_number).first()
                if not source_version:
                    return Response({'error': '脚本版本不存在'}, status=status.HTTP_404_NOT_FOUND)
                payload = {
                    'name': source_version.name or script_obj.name,
                    'target_url': source_version.target_url,
                    'instruction': source_version.instruction,
                    'script': source_version.script_content,
                    'summary': source_version.summary,
                    'warnings': source_version.warnings,
                    'planned_actions': source_version.planned_actions,
                    'generation_source': source_version.generation_source,
                    'fallback_reason': source_version.fallback_reason,
                    'module': source_version.module,
                    'model': source_version.model,
                    'capability': source_version.capability,
                    'metadata': source_version.metadata,
                    'change_summary': request.data.get('change_summary') or f'从 v{version_number} 恢复',
                }
                normalized = normalize_automation_script_payload(payload, existing=script_obj)
                version_record = create_automation_script_version(script_obj, normalized, request.user)
        except ValidationError as exc:
            return Response({'error': format_drf_validation_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'script': PlaywrightAutomationScriptSerializer(
                script_obj,
                context={'request': request, 'include_latest_version': True},
            ).data,
            'version': PlaywrightAutomationScriptVersionSerializer(version_record, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


def get_active_recording_count():
    return PlaywrightRecordingSession.objects.filter(
        recording_method=PlaywrightRecordingSession.RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI,
        status__in=[
            PlaywrightRecordingSession.STATUS_STARTING,
            PlaywrightRecordingSession.STATUS_RECORDING,
            PlaywrightRecordingSession.STATUS_STOPPING,
        ]
    ).count()


def build_recorder_settings_payload():
    payload = get_recorder_max_sessions_config()
    payload['active_count'] = get_active_recording_count()
    return payload


class PlaywrightRecordingSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(build_recorder_settings_payload())

    def put(self, request):
        return self.update(request)

    def patch(self, request):
        return self.update(request)

    def update(self, request):
        try:
            max_sessions = int(request.data.get('max_sessions'))
        except (TypeError, ValueError):
            return Response({'error': '请输入有效的并发录制数量'}, status=status.HTTP_400_BAD_REQUEST)

        active_count = get_active_recording_count()
        if max_sessions < 1:
            return Response({'error': '并发录制数量不能小于 1'}, status=status.HTTP_400_BAD_REQUEST)
        if max_sessions < active_count:
            return Response(
                {'error': f'当前有 {active_count} 个活动录制会话，并发数不能小于活动会话数'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            set_recorder_max_sessions(max_sessions)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(build_recorder_settings_payload())


class PlaywrightRecordingSessionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, session_id):
        try:
            return PlaywrightRecordingSession.objects.annotate(
                steps_count=models.Count('steps')
            ).prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

    def get(self, request, session_id):
        session = self.get_object(session_id)
        serializer = PlaywrightRecordingSessionSerializer(session, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, session_id):
        session = self.get_object(session_id)
        update_fields = []

        if 'name' in request.data:
            name = normalize_recording_scalar(request.data.get('name'), 200)
            if not name:
                return Response({'error': '录制名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            session.name = name
            update_fields.append('name')

        if any(key in request.data for key in ('module', 'project_id', 'version_id', 'version_name', 'module_id', 'module_name', 'module_path')):
            module = extract_module_payload(request.data)
            session.metadata = apply_recording_module_metadata(session.metadata, module)
            update_fields.append('metadata')

        if update_fields:
            update_fields.append('updated_at')
            session.save(update_fields=update_fields)

        refreshed_session = self.get_object(session_id)
        serializer = PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, session_id):
        session = self.get_object(session_id)
        if session.status in (
            PlaywrightRecordingSession.STATUS_STARTING,
            PlaywrightRecordingSession.STATUS_RECORDING,
            PlaywrightRecordingSession.STATUS_STOPPING,
        ):
            stop_recording_session(session_id)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlaywrightRecordingSessionJunkStepsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        junk_steps = identify_recording_junk_steps(session)
        return Response({
            'message': f'已识别 {len(junk_steps)} 个疑似垃圾步骤',
            'junk_steps': junk_steps,
            'step_ids': [item['step_id'] for item in junk_steps],
        })


class PlaywrightRecordingStepBatchDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        raw_step_ids = request.data.get('step_ids') if isinstance(request.data, dict) else None
        if not isinstance(raw_step_ids, list) or not raw_step_ids:
            return Response({'error': '请选择需要删除的录制步骤'}, status=status.HTTP_400_BAD_REQUEST)

        step_ids = []
        for raw_step_id in raw_step_ids:
            try:
                step_id = int(raw_step_id)
            except (TypeError, ValueError):
                continue
            if step_id not in step_ids:
                step_ids.append(step_id)

        if not step_ids:
            return Response({'error': '请选择有效的录制步骤'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            queryset = PlaywrightRecordingStep.objects.filter(session=session, id__in=step_ids)
            deleted_count = queryset.count()
            queryset.delete()
            for index, step in enumerate(session.steps.order_by('step_number', 'id'), start=1):
                if step.step_number != index:
                    step.step_number = index
                    step.save(update_fields=['step_number'])

        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        return Response({
            'message': f'已删除 {deleted_count} 个录制步骤',
            'deleted_count': deleted_count,
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
        })


class PlaywrightRecordingStepDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id, step_id):
        try:
            session = PlaywrightRecordingSession.objects.get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        step = PlaywrightRecordingStep.objects.filter(session=session, id=step_id).first()
        if not step:
            raise NotFound('录制步骤不存在')

        step.delete()
        session.updated_at = timezone.now()
        session.save(update_fields=['updated_at'])
        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        return Response({
            'message': '录制步骤已删除',
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
        })


class PlaywrightRecordingSessionDedupeSnapshotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        with transaction.atomic():
            summary = dedupe_recording_snapshots(session)

        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        return Response({
            'message': '快照文件去重完成',
            'summary': summary,
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
        })


class PlaywrightRecordingSessionAllureReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        try:
            report = generate_recording_allure_report(session, request=request)
        except ValidationError as exc:
            return Response(
                {'error': str(exc.detail if hasattr(exc, 'detail') else exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response({'error': f'生成Allure报告失败: {str(exc)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        return Response({
            **report,
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
        })


class PlaywrightRecordingLocalAgentView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_session(self, session_id):
        session = PlaywrightRecordingSession.objects.filter(
            session_id=session_id,
            recording_method=PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
        ).first()
        if not session:
            raise NotFound('本地 Agent 录制会话不存在')
        return session

    def ensure_agent(self, request, session):
        if not verify_local_agent_token(session, request):
            raise PermissionDenied('本地 Agent token 无效或已过期')

    def get(self, request, session_id):
        session = self.get_session(session_id)
        self.ensure_agent(request, session)
        metadata = dict(session.metadata or {})
        metadata['local_agent_status'] = 'paired'
        metadata['local_agent_paired_at'] = timezone.now().isoformat()
        metadata['active_recorder'] = True
        session.status = PlaywrightRecordingSession.STATUS_RECORDING
        session.metadata = metadata
        session.save(update_fields=['status', 'metadata', 'updated_at'])
        return Response(serialize_local_agent_session_payload(session, request))


class PlaywrightRecordingLocalAgentStepView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_session(self, session_id):
        session = PlaywrightRecordingSession.objects.filter(
            session_id=session_id,
            recording_method=PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
        ).first()
        if not session:
            raise NotFound('本地 Agent 录制会话不存在')
        return session

    def post(self, request, session_id):
        session = self.get_session(session_id)
        if not verify_local_agent_token(session, request):
            raise PermissionDenied('本地 Agent token 无效或已过期')

        payload = request.data or {}
        raw_steps = payload.get('steps') if isinstance(payload, dict) else None
        if raw_steps is None:
            raw_steps = [payload]
        if not isinstance(raw_steps, list) or not raw_steps:
            return Response({'error': '请提供录制步骤数据'}, status=status.HTTP_400_BAD_REQUEST)

        created_steps = []
        try:
            for raw_step in raw_steps:
                if not isinstance(raw_step, dict):
                    continue
                created_steps.append(persist_local_agent_recording_step(session, raw_step))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)

        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        return Response({
            'message': f'已接收 {len(created_steps)} 个本地 Agent 录制步骤',
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
            'steps': PlaywrightRecordingStepSerializer(created_steps, many=True, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


class PlaywrightRecordingLocalAgentStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, session_id):
        return self.get(request, session_id)

    def get(self, request, session_id):
        session = PlaywrightRecordingSession.objects.filter(
            session_id=session_id,
            recording_method=PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
        ).first()
        if not session:
            raise NotFound('本地 Agent 录制会话不存在')
        if not verify_local_agent_token(session, request):
            raise PermissionDenied('本地 Agent token 无效或已过期')

        metadata = session.metadata if isinstance(session.metadata, dict) else {}
        stopped = (
            session.status in (
                PlaywrightRecordingSession.STATUS_COMPLETED,
                PlaywrightRecordingSession.STATUS_FAILED,
            )
            or bool(metadata.get('stop_requested'))
            or metadata.get('local_agent_status') in ('stop_requested', 'stopped')
        )
        return Response({
            'session_id': session.session_id,
            'status': session.status,
            'stop_requested': stopped,
            'local_agent_status': metadata.get('local_agent_status') or '',
        })


class PlaywrightRecordingLocalAgentStopView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, session_id):
        session = PlaywrightRecordingSession.objects.filter(
            session_id=session_id,
            recording_method=PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
        ).first()
        if not session:
            raise NotFound('本地 Agent 录制会话不存在')
        if not verify_local_agent_token(session, request):
            raise PermissionDenied('本地 Agent token 无效或已过期')

        metadata = dict(session.metadata or {})
        metadata['local_agent_status'] = 'stopped'
        metadata['active_recorder'] = False
        metadata['stop_requested'] = True
        session.status = PlaywrightRecordingSession.STATUS_COMPLETED
        session.stopped_at = timezone.now()
        session.metadata = metadata
        session.save(update_fields=['status', 'stopped_at', 'metadata', 'updated_at'])

        flow = None
        if session.steps.exists():
            try:
                flow, _ = create_or_update_visual_flow_from_recording(session, user=session.started_by)
            except Exception:
                flow = None

        refreshed_session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).prefetch_related('steps').get(id=session.id)
        payload = {
            'message': '本地 Agent 录制已停止',
            'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
        }
        if flow:
            payload['flow'] = VisualFlowSerializer(
                flow,
                context={'request': request, 'include_graph': False}
            ).data
        return Response(payload)


class PlaywrightRecordingSessionStopView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = PlaywrightRecordingSession.objects.filter(session_id=session_id).first()
        if not session:
            raise NotFound('录制会话不存在')

        if session.recording_method == PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT:
            metadata = dict(session.metadata or {})
            metadata['local_agent_status'] = 'stop_requested'
            metadata['active_recorder'] = False
            metadata['stop_requested'] = True
            if local_agent_stop_request_is_stale(session):
                session = complete_stale_local_agent_recording(session)
            elif session.status not in (
                PlaywrightRecordingSession.STATUS_COMPLETED,
                PlaywrightRecordingSession.STATUS_FAILED,
            ):
                session.status = PlaywrightRecordingSession.STATUS_STOPPING
                session.metadata = metadata
                session.save(update_fields=['status', 'metadata', 'updated_at'])
            flow = None
            if session.status in (
                PlaywrightRecordingSession.STATUS_COMPLETED,
                PlaywrightRecordingSession.STATUS_FAILED,
            ) and session.steps.exists():
                try:
                    flow, _ = create_or_update_visual_flow_from_recording(session, user=request.user)
                except Exception:
                    flow = None
            refreshed_session = PlaywrightRecordingSession.objects.annotate(
                steps_count=models.Count('steps')
            ).get(session_id=session_id)
            payload = {
                'message': '本地 Agent 录制已停止',
                'session': PlaywrightRecordingSessionSerializer(refreshed_session, context={'request': request}).data,
            }
            if flow:
                payload['flow'] = VisualFlowSerializer(
                    flow,
                    context={'request': request, 'include_graph': False}
                ).data
            return Response(payload)

        if session.status in (
            PlaywrightRecordingSession.STATUS_COMPLETED,
            PlaywrightRecordingSession.STATUS_FAILED,
        ):
            flow = None
            if session.steps.exists():
                try:
                    flow, _ = create_or_update_visual_flow_from_recording(session, user=request.user)
                except Exception:
                    flow = None
            serializer = PlaywrightRecordingSessionSerializer(
                PlaywrightRecordingSession.objects.annotate(
                    steps_count=models.Count('steps')
                ).get(session_id=session_id),
                context={'request': request},
            )
            payload = {'message': '录制已结束', 'session': serializer.data}
            if flow:
                payload['flow'] = VisualFlowSerializer(
                    flow,
                    context={'request': request, 'include_graph': False}
                ).data
            return Response(payload)

        stop_recording_session(session_id)
        session = PlaywrightRecordingSession.objects.annotate(
            steps_count=models.Count('steps')
        ).get(session_id=session_id)
        flow = None
        if session.steps.exists():
            try:
                flow, _ = create_or_update_visual_flow_from_recording(session, user=request.user)
            except Exception:
                flow = None
        serializer = PlaywrightRecordingSessionSerializer(session, context={'request': request})
        payload = {'message': '录制已停止', 'session': serializer.data}
        if flow:
            payload['flow'] = VisualFlowSerializer(
                flow,
                context={'request': request, 'include_graph': False}
            ).data
        return Response(payload)


class PlaywrightRecordingSessionFlowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.annotate(
                steps_count=models.Count('steps')
            ).prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        return Response({
            'session': PlaywrightRecordingSessionSerializer(session, context={'request': request}).data,
            'steps': PlaywrightRecordingStepSerializer(
                session.steps.order_by('step_number'),
                many=True,
                context={'request': request},
            ).data,
            'flow': build_recording_flow_data(session),
        })


class PlaywrightRecordingSessionCreateFlowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = PlaywrightRecordingSession.objects.prefetch_related('steps').get(session_id=session_id)
        except PlaywrightRecordingSession.DoesNotExist:
            raise NotFound('录制会话不存在')

        try:
            flow, created = create_or_update_visual_flow_from_recording(
                session,
                user=request.user,
                flow_name=request.data.get('name') or '',
                force_new=parse_boolean_value(request.data.get('force_new'), default=False),
                allow_empty=parse_boolean_value(request.data.get('allow_empty'), default=False)
            )
        except ValidationError as exc:
            return Response({'error': str(exc.detail if hasattr(exc, 'detail') else exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'创建流程失败: {str(exc)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'message': '流程已创建' if created else '流程已更新',
            'created': created,
            'flow': VisualFlowSerializer(flow, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class VisualFlowListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = VisualFlow.objects.select_related('created_by', 'recording_session').order_by('-updated_at', '-id')
        keyword = (request.query_params.get('keyword') or request.query_params.get('search') or '').strip()
        source = (request.query_params.get('source') or '').strip()
        flow_status = (request.query_params.get('status') or '').strip()
        recording_session = (request.query_params.get('recording_session') or '').strip()
        module_path = normalize_recording_system_page_path(request.query_params.get('module_path'))
        module_name = normalize_recording_scalar(request.query_params.get('module_name'), 200)
        module_id = normalize_optional_int(request.query_params.get('module_id'))
        project_id = normalize_optional_int(request.query_params.get('project_id'))
        version_id = normalize_version_id(request.query_params.get('version_id') or request.query_params.get('version'))

        if keyword:
            queryset = queryset.filter(
                models.Q(name__icontains=keyword) |
                models.Q(description__icontains=keyword) |
                models.Q(flow_id__icontains=keyword) |
                models.Q(target_url__icontains=keyword) |
                models.Q(metadata__module__module_name__icontains=keyword) |
                models.Q(metadata__module__module_path__icontains=keyword) |
                models.Q(recording_session__metadata__module__module_name__icontains=keyword) |
                models.Q(recording_session__metadata__module__module_path__icontains=keyword)
            )
        if source:
            queryset = queryset.filter(source=source)
        if flow_status:
            queryset = queryset.filter(status=flow_status)
        if recording_session:
            queryset = queryset.filter(recording_session__session_id=recording_session)
        module_filter = build_json_module_scope_q(
            request,
            module_id=module_id,
            module_path=module_path,
            module_name=module_name,
            project_id=project_id,
            version_id=version_id,
            flow_prefix='metadata__module',
            recording_prefix='recording_session__metadata__module',
        )
        if module_filter:
            queryset = queryset.filter(module_filter)

        queryset, page_meta = paginate_queryset(request, queryset, default_page_size=20)

        serializer = VisualFlowSerializer(
            queryset,
            many=True,
            context={'request': request, 'include_graph': False},
        )
        return Response({
            **page_meta,
            'results': serializer.data,
        })

    def post(self, request):
        name = normalize_recording_scalar(request.data.get('name'), 200)
        if not name:
            return Response({'error': '流程名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        source = request.data.get('source') or VisualFlow.SOURCE_MANUAL
        if source not in dict(VisualFlow.SOURCE_CHOICES):
            source = VisualFlow.SOURCE_MANUAL

        flow_status = request.data.get('status') or VisualFlow.STATUS_DRAFT
        if flow_status not in dict(VisualFlow.STATUS_CHOICES):
            flow_status = VisualFlow.STATUS_DRAFT
        metadata = request.data.get('metadata') if isinstance(request.data.get('metadata'), dict) else {}
        metadata = apply_module_metadata(metadata, extract_module_payload(request.data))

        flow = VisualFlow.objects.create(
            flow_id=uuid.uuid4().hex[:16],
            name=name,
            description=request.data.get('description') or '',
            source=source,
            status=flow_status,
            target_url=request.data.get('target_url') or '',
            browser_type=request.data.get('browser_type') or 'chromium',
            graph_data=request.data.get('graph_data') if isinstance(request.data.get('graph_data'), dict) else {'cells': []},
            snapshot_summary=request.data.get('snapshot_summary') if isinstance(request.data.get('snapshot_summary'), dict) else {},
            metadata=metadata,
            created_by=request.user if request.user.is_authenticated else None,
        )
        return Response(
            VisualFlowSerializer(flow, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class VisualFlowDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, flow_id):
        try:
            return VisualFlow.objects.select_related('created_by', 'recording_session').get(flow_id=flow_id)
        except VisualFlow.DoesNotExist:
            raise NotFound('流程不存在')

    def get(self, request, flow_id):
        flow = self.get_object(flow_id)
        flow, _ = refresh_recording_visual_flow_if_needed(flow)
        return Response(VisualFlowSerializer(flow, context={'request': request}).data)

    def put(self, request, flow_id):
        return self.update(request, flow_id)

    def patch(self, request, flow_id):
        return self.update(request, flow_id)

    def update(self, request, flow_id):
        flow = self.get_object(flow_id)
        data = request.data or {}
        if 'name' in data:
            name = normalize_recording_scalar(data.get('name'), 200)
            if not name:
                return Response({'error': '流程名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            flow.name = name
        if 'description' in data:
            flow.description = data.get('description') or ''
        if data.get('source') in dict(VisualFlow.SOURCE_CHOICES):
            flow.source = data.get('source')
        if data.get('status') in dict(VisualFlow.STATUS_CHOICES):
            flow.status = data.get('status')
        if 'target_url' in data:
            flow.target_url = data.get('target_url') or ''
        if 'browser_type' in data:
            flow.browser_type = data.get('browser_type') or 'chromium'
        if isinstance(data.get('graph_data'), dict):
            flow.graph_data = data.get('graph_data')
        if isinstance(data.get('snapshot_summary'), dict):
            flow.snapshot_summary = data.get('snapshot_summary')
        if isinstance(data.get('metadata'), dict):
            flow.metadata = data.get('metadata')
        if any(key in data for key in ('module', 'project_id', 'version_id', 'version_name', 'module_id', 'module_name', 'module_path')):
            flow.metadata = apply_module_metadata(flow.metadata, extract_module_payload(data))
        flow.save()
        return Response(VisualFlowSerializer(flow, context={'request': request}).data)

    def delete(self, request, flow_id):
        flow = self.get_object(flow_id)
        flow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisualFlowCopyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, flow_id):
        try:
            source_flow = VisualFlow.objects.select_related('recording_session').get(flow_id=flow_id)
        except VisualFlow.DoesNotExist:
            raise NotFound('流程不存在')

        try:
            version = resolve_flow_copy_version(request.data.get('version_id'))
            copied_flow = create_visual_flow_copy(source_flow, request, version, batch=False)
        except ValidationError as exc:
            return Response({'error': str(exc.detail[0] if isinstance(exc.detail, list) else exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(VisualFlowSerializer(copied_flow, context={'request': request}).data, status=status.HTTP_201_CREATED)


class VisualFlowBatchCopyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        flow_ids = request.data.get('flow_ids') if isinstance(request.data, dict) else []
        if not isinstance(flow_ids, list) or not flow_ids:
            return Response({'error': '请选择要复制的流程'}, status=status.HTTP_400_BAD_REQUEST)

        normalized_flow_ids = [str(flow_id or '').strip() for flow_id in flow_ids if str(flow_id or '').strip()]
        if not normalized_flow_ids:
            return Response({'error': '请选择要复制的流程'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            version = resolve_flow_copy_version(request.data.get('version_id'))
        except ValidationError as exc:
            return Response({'error': str(exc.detail[0] if isinstance(exc.detail, list) else exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        source_flows = list(
            VisualFlow.objects.select_related('recording_session').filter(flow_id__in=normalized_flow_ids)
        )
        if len(source_flows) != len(set(normalized_flow_ids)):
            return Response({'error': '部分流程不存在'}, status=status.HTTP_404_NOT_FOUND)

        if any(visual_flow_copy_exists(flow, version) for flow in source_flows):
            return Response({'error': '该版本下已存在同样流程'}, status=status.HTTP_400_BAD_REQUEST)

        copied_flows = []
        with transaction.atomic():
            for flow in source_flows:
                copied_flows.append(create_visual_flow_copy(flow, request, version, batch=True))

        return Response({
            'count': len(copied_flows),
            'results': VisualFlowSerializer(copied_flows, many=True, context={'request': request, 'include_graph': False}).data,
        }, status=status.HTTP_201_CREATED)


VISUAL_FLOW_EVENT_PREFIX = '__TESTHUB_FLOW_EVENT__'
VISUAL_FLOW_EXECUTION_TIMEOUT_SECONDS = 360


def normalize_visual_flow_execution_status(value):
    value = str(value or '').strip().lower()
    aliases = {
        'passed': VisualFlowExecution.STATUS_SUCCESS,
        'pass': VisualFlowExecution.STATUS_SUCCESS,
        'success': VisualFlowExecution.STATUS_SUCCESS,
        'ok': VisualFlowExecution.STATUS_SUCCESS,
        'failed': VisualFlowExecution.STATUS_FAILED,
        'fail': VisualFlowExecution.STATUS_FAILED,
        'error': VisualFlowExecution.STATUS_FAILED,
        'running': VisualFlowExecution.STATUS_RUNNING,
        'pending': VisualFlowExecution.STATUS_PENDING,
        'aborted': VisualFlowExecution.STATUS_ABORTED,
    }
    return aliases.get(value, VisualFlowExecution.STATUS_FAILED)


def normalize_visual_flow_step_status(value):
    value = str(value or '').strip().lower()
    aliases = {
        'passed': VisualFlowExecutionStep.STATUS_SUCCESS,
        'pass': VisualFlowExecutionStep.STATUS_SUCCESS,
        'success': VisualFlowExecutionStep.STATUS_SUCCESS,
        'ok': VisualFlowExecutionStep.STATUS_SUCCESS,
        'failed': VisualFlowExecutionStep.STATUS_FAILED,
        'fail': VisualFlowExecutionStep.STATUS_FAILED,
        'error': VisualFlowExecutionStep.STATUS_FAILED,
        'running': VisualFlowExecutionStep.STATUS_RUNNING,
        'pending': VisualFlowExecutionStep.STATUS_PENDING,
        'skipped': VisualFlowExecutionStep.STATUS_SKIPPED,
    }
    return aliases.get(value, VisualFlowExecutionStep.STATUS_FAILED)


def safe_visual_flow_event_value(value, fallback):
    value = str(value or '').strip()
    return value[:500] if value else fallback


def build_visual_flow_execution_screenshot_path(execution, event):
    screenshot_base64 = ''
    if isinstance(event, dict):
        screenshot_base64 = event.get('screenshot_base64') or event.get('screenshot') or ''
    if not screenshot_base64:
        return ''

    if isinstance(screenshot_base64, str) and ',' in screenshot_base64[:80]:
        screenshot_base64 = screenshot_base64.split(',', 1)[1]

    try:
        binary = base64.b64decode(str(screenshot_base64), validate=False)
    except (binascii.Error, ValueError, TypeError):
        return ''

    if not binary:
        return ''

    date_path = timezone.now().strftime('%Y/%m')
    relative_dir = os.path.join('visual_flow_executions', date_path)
    screenshot_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
    os.makedirs(screenshot_dir, exist_ok=True)
    step_key = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(event.get('step_key') or event.get('node_id') or 'step'))[:80]
    filename = f'{execution.execution_id}-{step_key}-{uuid.uuid4().hex[:8]}.png'
    absolute_path = os.path.join(screenshot_dir, filename)
    try:
        with open(absolute_path, 'wb') as screenshot_file:
            screenshot_file.write(binary)
        return os.path.join(relative_dir, filename).replace('\\', '/')
    except OSError:
        return ''


def parse_visual_flow_stdout_events(stdout):
    events = []
    clean_lines = []
    for line in str(stdout or '').splitlines():
        if line.startswith(VISUAL_FLOW_EVENT_PREFIX):
            raw_payload = line[len(VISUAL_FLOW_EVENT_PREFIX):].strip()
            try:
                payload = json.loads(raw_payload)
            except (TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                events.append(payload)
            continue
        clean_lines.append(line)
    return events, '\n'.join(clean_lines).strip()


def upsert_visual_flow_execution_step(execution, event):
    if not isinstance(event, dict):
        return None

    step_key = str(event.get('step_key') or '').strip()
    if not step_key:
        node_id = str(event.get('node_id') or '').strip()
        component_id = str(event.get('component_id') or '').strip()
        step_key = f"{node_id}:{component_id}" if component_id else node_id
    if not step_key:
        return None

    now = timezone.now()
    event_type = str(event.get('event') or event.get('event_type') or '').strip().lower()
    status_value = normalize_visual_flow_step_status(event.get('status') or event_type)
    started_at = now if event_type == 'start' or status_value == VisualFlowExecutionStep.STATUS_RUNNING else None
    finished_at = now if status_value in (
        VisualFlowExecutionStep.STATUS_SUCCESS,
        VisualFlowExecutionStep.STATUS_FAILED,
        VisualFlowExecutionStep.STATUS_SKIPPED,
    ) else None

    defaults = {
        'step_order': max(0, int(event.get('step_order') or 0)),
        'item_type': str(event.get('item_type') or VisualFlowExecutionStep.ITEM_TYPE_NODE)[:20],
        'node_id': str(event.get('node_id') or '')[:120],
        'component_id': str(event.get('component_id') or '')[:120],
        'title': safe_visual_flow_event_value(event.get('title'), step_key),
        'status': status_value,
        'input_data': event.get('input') if isinstance(event.get('input'), dict) else {},
        'output_data': event.get('output') if isinstance(event.get('output'), dict) else {},
        'error_log': str(event.get('error') or event.get('error_log') or '')[:20000],
    }
    if started_at:
        defaults['started_at'] = started_at
    if finished_at:
        defaults['finished_at'] = finished_at

    try:
        duration = float(event.get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration:
        defaults['duration'] = max(0, duration)

    screenshot_path = build_visual_flow_execution_screenshot_path(execution, event)
    if screenshot_path:
        defaults['screenshot_path'] = screenshot_path

    with transaction.atomic():
        step, created = VisualFlowExecutionStep.objects.select_for_update().get_or_create(
            execution=execution,
            step_key=step_key[:200],
            defaults=defaults,
        )
        if not created:
            for key, value in defaults.items():
                if key == 'started_at' and step.started_at:
                    continue
                if key == 'screenshot_path' and not value:
                    continue
                setattr(step, key, value)
            if step.started_at and step.finished_at and not step.duration:
                step.duration = max(0, (step.finished_at - step.started_at).total_seconds())
            step.save()
        return step


def update_visual_flow_execution_summary(execution):
    steps = list(execution.steps.all())
    success_count = len([step for step in steps if step.status == VisualFlowExecutionStep.STATUS_SUCCESS])
    failed_count = len([step for step in steps if step.status == VisualFlowExecutionStep.STATUS_FAILED])
    running_count = len([step for step in steps if step.status == VisualFlowExecutionStep.STATUS_RUNNING])
    pending_count = len([step for step in steps if step.status == VisualFlowExecutionStep.STATUS_PENDING])
    execution.summary = {
        **(execution.summary if isinstance(execution.summary, dict) else {}),
        'step_count': len(steps),
        'success_count': success_count,
        'failed_count': failed_count,
        'running_count': running_count,
        'pending_count': pending_count,
    }
    execution.save(update_fields=['summary', 'updated_at'])


def fail_timed_out_visual_flow_execution(execution):
    if execution.status != VisualFlowExecution.STATUS_RUNNING or not execution.started_at:
        return False

    now = timezone.now()
    elapsed = (now - execution.started_at).total_seconds()
    if elapsed < VISUAL_FLOW_EXECUTION_TIMEOUT_SECONDS:
        return False

    timeout_message = f'回放执行超过 {VISUAL_FLOW_EXECUTION_TIMEOUT_SECONDS} 秒未完成，已自动标记失败。'
    execution.status = VisualFlowExecution.STATUS_FAILED
    execution.finished_at = now
    execution.duration = max(0, elapsed)
    execution.error_message = timeout_message
    execution.stderr = execution.stderr or timeout_message
    execution.returncode = execution.returncode if execution.returncode is not None else -1
    execution.save(update_fields=[
        'status',
        'finished_at',
        'duration',
        'error_message',
        'stderr',
        'returncode',
        'updated_at',
    ])
    execution.steps.filter(status=VisualFlowExecutionStep.STATUS_RUNNING).update(
        status=VisualFlowExecutionStep.STATUS_FAILED,
        finished_at=now,
        error_log=timeout_message,
    )
    update_visual_flow_execution_summary(execution)
    return True


def fail_timed_out_visual_flow_executions(queryset=None):
    running_queryset = queryset if queryset is not None else VisualFlowExecution.objects.all()
    threshold = timezone.now() - timedelta(seconds=VISUAL_FLOW_EXECUTION_TIMEOUT_SECONDS)
    for execution in running_queryset.filter(
        status=VisualFlowExecution.STATUS_RUNNING,
        started_at__lt=threshold,
    ):
        fail_timed_out_visual_flow_execution(execution)


def ingest_visual_flow_execution_events(execution, events):
    for event in events or []:
        upsert_visual_flow_execution_step(execution, event)
    update_visual_flow_execution_summary(execution)


def finalize_visual_flow_execution(execution, result_payload):
    events, clean_stdout = parse_visual_flow_stdout_events(result_payload.get('stdout') or '')
    ingest_visual_flow_execution_events(execution, events)

    success = bool(result_payload.get('success'))
    finished_at = timezone.now()
    execution.stdout = clean_stdout
    execution.stderr = str(result_payload.get('stderr') or '')
    execution.returncode = result_payload.get('returncode')
    execution.error_message = str(result_payload.get('error') or result_payload.get('stderr') or '')[:20000] if not success else ''
    execution.status = VisualFlowExecution.STATUS_SUCCESS if success else VisualFlowExecution.STATUS_FAILED
    execution.finished_at = finished_at
    if execution.started_at:
        execution.duration = max(0, (finished_at - execution.started_at).total_seconds())
    execution.save()

    if not success:
        running_steps = execution.steps.filter(status=VisualFlowExecutionStep.STATUS_RUNNING)
        running_steps.update(
            status=VisualFlowExecutionStep.STATUS_FAILED,
            finished_at=finished_at,
            error_log=execution.error_message or execution.stderr,
        )
    update_visual_flow_execution_summary(execution)


def create_visual_flow_execution_record(request, run_type, flow_id='', graph_data=None, flow_name=''):
    flow = None
    flow_id = str(flow_id or '').strip()
    if flow_id:
        flow = VisualFlow.objects.filter(flow_id=flow_id).first()

    if flow:
        flow_name = flow_name or flow.name
    elif flow_id:
        flow_name = flow_name or flow_id

    return VisualFlowExecution.objects.create(
        execution_id=uuid.uuid4().hex,
        flow=flow,
        flow_id_text=flow.flow_id if flow else flow_id,
        flow_name=flow_name or '未保存流程回放',
        run_type=run_type,
        status=VisualFlowExecution.STATUS_PENDING,
        graph_snapshot=graph_data if isinstance(graph_data, dict) else {},
        created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
    )


class PlaywrightScriptExecuteView(APIView):
    """执行Playwright脚本"""
    permission_classes = [permissions.IsAuthenticated]
    GENERATED_VISUAL_FLOW_SCRIPT_MARKER = '自动生成的 Playwright 测试脚本'

    def _needs_virtual_display(self):
        if platform.system() != 'Linux':
            return False
        return not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))

    def _prepare_script_content(self, script_content):
        if not self._needs_virtual_display():
            return self._rewrite_script_localhost_urls(script_content)

        if 'resolve_browser_runtime_options(' in script_content:
            return self._rewrite_script_localhost_urls(script_content)

        if self.GENERATED_VISUAL_FLOW_SCRIPT_MARKER not in script_content:
            return self._rewrite_script_localhost_urls(script_content)

        patched_script = re.sub(
            r'\.launch\(headless=False(?P<tail>\s*(?:,|\)))',
            lambda match: f".launch(headless=True{match.group('tail')}",
            script_content,
        )
        if patched_script == script_content:
            return self._rewrite_script_localhost_urls(script_content)

        patched_script = patched_script.replace(", args=['--start-maximized']", '')
        patched_script = patched_script.replace(
            'new_context(viewport=None)',
            "new_context(viewport={'width': 1920, 'height': 1080})",
        )
        return self._rewrite_script_localhost_urls(patched_script)

    def _rewrite_script_localhost_urls(self, script_content):
        def replace_url(match):
            quote = match.group('quote')
            url = match.group('url')
            rewritten_url = rewrite_localhost_target_url_for_recorder(url)
            return f'{quote}{rewritten_url}{quote}'

        return re.sub(
            r'(?P<quote>[\'"])(?P<url>https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|::1)(?::\d+)?[^\'"]*)(?P=quote)',
            replace_url,
            script_content,
        )

    def _build_script_command(self, script_path):
        command = ['python', script_path]
        if not self._needs_virtual_display():
            return command

        xvfb_run = shutil.which('xvfb-run')
        if not xvfb_run:
            return command

        return [
            xvfb_run,
            '-a',
            '-s',
            f'-screen 0 {get_recorder_xvfb_screen_spec()}',
            *command,
        ]

    def _build_script_env(self, request, flow_variables=None):
        env = dict(os.environ)
        try:
            env['TESTHUB_PLAYWRIGHT_API_ORIGIN'] = request.build_absolute_uri('/api').rstrip('/')
        except Exception:
            pass
        if isinstance(flow_variables, dict):
            try:
                env['TESTHUB_FLOW_VARIABLES_JSON'] = json.dumps(flow_variables, ensure_ascii=False, default=str)
            except Exception:
                pass
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            return env

        try:
            refresh = RefreshToken.for_user(user)
            env['TESTHUB_PLAYWRIGHT_ACCESS_TOKEN'] = str(refresh.access_token)
            env['TESTHUB_PLAYWRIGHT_REFRESH_TOKEN'] = str(refresh)
            env['TESTHUB_PLAYWRIGHT_TOKEN_EXPIRES_AT'] = str(int((time.time() + 30 * 60) * 1000))
            env['TESTHUB_PLAYWRIGHT_USER_JSON'] = json.dumps(
                UserSerializer(user).data,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            pass
        return env

    def _run_script_content(self, request, script_content, script_id=None, flow_variables=None):
        script_id = script_id or str(uuid.uuid4())

        if not script_content:
            raise ValueError('脚本内容不能为空')
        if not isinstance(script_content, str):
            raise ValueError('script must be a string')

        script_content = self._prepare_script_content(script_content)
        script_path = os.path.join(tempfile.gettempdir(), f'playwright_test_{script_id}.py')

        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            result = subprocess.run(
                self._build_script_command(script_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=self._build_script_env(request, flow_variables=flow_variables),
                timeout=300,
            )
            return {
                'script_id': script_id,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                'script_id': script_id,
                'success': False,
                'stdout': '',
                'stderr': '脚本执行超时（超过 5 分钟）',
                'returncode': -1,
                'error': '脚本执行超时（超过 5 分钟）',
            }
        except Exception as exc:
            return {
                'script_id': script_id,
                'success': False,
                'stdout': '',
                'stderr': str(exc),
                'returncode': -1,
                'error': f'执行脚本失败: {exc}',
            }
        finally:
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except Exception:
                pass

    def _run_script_content_streaming(self, request, script_content, execution, flow_variables=None):
        script_id = execution.execution_id

        if not script_content:
            raise ValueError('脚本内容不能为空')
        if not isinstance(script_content, str):
            raise ValueError('script must be a string')

        script_content = self._prepare_script_content(script_content)
        script_path = os.path.join(tempfile.gettempdir(), f'playwright_test_{script_id}.py')
        stdout_lines = []
        stderr_text = ''
        returncode = -1

        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            process = subprocess.Popen(
                self._build_script_command(script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=self._build_script_env(request, flow_variables=flow_variables),
            )

            start_time = time.time()
            while True:
                if process.stdout is None:
                    break
                line = process.stdout.readline()
                if line:
                    events, clean_stdout = parse_visual_flow_stdout_events(line)
                    if events:
                        ingest_visual_flow_execution_events(execution, events)
                    if clean_stdout:
                        stdout_lines.append(clean_stdout)
                    continue

                if process.poll() is not None:
                    break
                if time.time() - start_time > 300:
                    process.kill()
                    stderr_text = '脚本执行超时（超过 5 分钟）'
                    returncode = -1
                    return {
                        'script_id': script_id,
                        'success': False,
                        'stdout': '\n'.join(stdout_lines),
                        'stderr': stderr_text,
                        'returncode': returncode,
                        'error': stderr_text,
                    }
                time.sleep(0.1)

            if process.stdout is not None:
                remaining_stdout = process.stdout.read() or ''
                events, clean_stdout = parse_visual_flow_stdout_events(remaining_stdout)
                if events:
                    ingest_visual_flow_execution_events(execution, events)
                if clean_stdout:
                    stdout_lines.append(clean_stdout)
            stderr_text = process.stderr.read() if process.stderr is not None else ''
            returncode = process.wait(timeout=5)
            return {
                'script_id': script_id,
                'success': returncode == 0,
                'stdout': '\n'.join(line for line in stdout_lines if line),
                'stderr': stderr_text,
                'returncode': returncode,
            }
        except Exception as exc:
            return {
                'script_id': script_id,
                'success': False,
                'stdout': '\n'.join(stdout_lines),
                'stderr': str(exc),
                'returncode': returncode,
                'error': f'执行脚本失败: {exc}',
            }
        finally:
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except Exception:
                pass

    def _run_visual_flow_execution_worker(self, execution_id, script_content, user_id, flow_variables=None):
        close_old_connections()
        try:
            execution = VisualFlowExecution.objects.get(execution_id=execution_id)
            execution.status = VisualFlowExecution.STATUS_RUNNING
            execution.started_at = timezone.now()
            execution.save(update_fields=['status', 'started_at', 'updated_at'])

            class RequestStub:
                def __init__(self, user):
                    self.user = user

            user = None
            if user_id:
                try:
                    from apps.users.models import User
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    user = None
            result_payload = self._run_script_content_streaming(
                RequestStub(user),
                script_content,
                execution,
                flow_variables=flow_variables,
            )
            execution.refresh_from_db()
            finalize_visual_flow_execution(execution, result_payload)
        except Exception as exc:
            try:
                execution = VisualFlowExecution.objects.get(execution_id=execution_id)
                execution.status = VisualFlowExecution.STATUS_FAILED
                execution.error_message = str(exc)
                execution.stderr = str(exc)
                execution.finished_at = timezone.now()
                if execution.started_at:
                    execution.duration = max(0, (execution.finished_at - execution.started_at).total_seconds())
                execution.save()
                update_visual_flow_execution_summary(execution)
            except Exception:
                pass
        finally:
            close_old_connections()

    def post(self, request):
        """执行Python脚本"""
        script_content = request.data.get('script')
        async_mode = bool(request.data.get('async') or request.data.get('async_mode'))
        visual_flow_payload = request.data.get('visual_flow') if isinstance(request.data.get('visual_flow'), dict) else {}
        flow_variables = request.data.get('flow_variables') if isinstance(request.data.get('flow_variables'), dict) else {}

        if async_mode:
            try:
                execution = create_visual_flow_execution_record(
                    request,
                    VisualFlowExecution.RUN_TYPE_BACKEND,
                    flow_id=visual_flow_payload.get('flow_id') or request.data.get('flow_id') or '',
                    graph_data=visual_flow_payload.get('graph_data') or request.data.get('graph_data') or {},
                    flow_name=visual_flow_payload.get('flow_name') or request.data.get('flow_name') or '',
                )
                thread = threading.Thread(
                    target=self._run_visual_flow_execution_worker,
                    args=(execution.execution_id, script_content, getattr(request.user, 'id', None), flow_variables),
                    daemon=True,
                )
                thread.start()
                return Response(
                    VisualFlowExecutionSerializer(execution, context={'request': request}).data,
                    status=status.HTTP_202_ACCEPTED,
                )
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            return Response(self._run_script_content(request, script_content, flow_variables=flow_variables))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not script_content:
            return Response(
                {'error': '脚本内容不能为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(script_content, str):
            return Response(
                {'error': 'script must be a string'},
                status=status.HTTP_400_BAD_REQUEST
            )

        script_content = self._prepare_script_content(script_content)

        # 生成唯一的脚本文件名
        script_id = str(uuid.uuid4())
        script_filename = f'playwright_test_{script_id}.py'

        # 创建临时目录
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, script_filename)

        try:
            # 写入脚本文件
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            # 执行脚本
            result = subprocess.run(
                self._build_script_command(script_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=self._build_script_env(request),
                timeout=300  # 5分钟超时
            )

            # 清理临时文件
            if os.path.exists(script_path):
                os.remove(script_path)

            # 返回执行结果
            return Response({
                'script_id': script_id,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            })

        except subprocess.TimeoutExpired:
            # 清理临时文件
            if os.path.exists(script_path):
                os.remove(script_path)

            return Response(
                {'error': '脚本执行超时（超过5分钟）'},
                status=status.HTTP_408_REQUEST_TIMEOUT
            )

        except Exception as e:
            # 清理临时文件
            if os.path.exists(script_path):
                os.remove(script_path)

            return Response(
                {'error': f'执行脚本失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VisualFlowExecutionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        queryset = VisualFlowExecution.objects.select_related('flow', 'created_by').prefetch_related(
            Prefetch(
                'steps',
                queryset=VisualFlowExecutionStep.objects.order_by('step_order', 'id'),
                to_attr='prefetched_steps',
            )
        ).order_by('-created_at', '-id')

        flow_id = str(request.query_params.get('flow_id') or '').strip()
        if flow_id:
            queryset = queryset.filter(models.Q(flow__flow_id=flow_id) | models.Q(flow_id_text=flow_id))

        status_value = str(request.query_params.get('status') or '').strip()
        if status_value:
            queryset = queryset.filter(status=status_value)

        run_type = str(request.query_params.get('run_type') or '').strip()
        if run_type:
            queryset = queryset.filter(run_type=run_type)

        module_path = normalize_recording_system_page_path(request.query_params.get('module_path'))
        module_name = normalize_recording_scalar(request.query_params.get('module_name'), 200)
        module_id = normalize_optional_int(request.query_params.get('module_id'))
        project_id = normalize_optional_int(request.query_params.get('project_id'))
        version_id = normalize_version_id(request.query_params.get('version_id') or request.query_params.get('version'))
        module_filter = build_json_module_scope_q(
            request,
            module_id=module_id,
            module_path=module_path,
            module_name=module_name,
            project_id=project_id,
            version_id=version_id,
            flow_prefix='flow__metadata__module',
            recording_prefix='flow__recording_session__metadata__module',
        )
        if module_filter:
            queryset = queryset.filter(module_filter)

        search = str(request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                models.Q(flow_name__icontains=search) |
                models.Q(flow_id_text__icontains=search) |
                models.Q(execution_id__icontains=search)
            )
        return queryset

    def get(self, request):
        fail_timed_out_visual_flow_executions()
        queryset = self.get_queryset(request)
        page_queryset, page_meta = paginate_queryset(request, queryset, default_page_size=20, max_page_size=100)
        serializer = VisualFlowExecutionSerializer(page_queryset, many=True, context={'request': request})
        return Response({**page_meta, 'results': serializer.data})

    def post(self, request):
        run_type = request.data.get('run_type') or VisualFlowExecution.RUN_TYPE_LOCAL
        if run_type not in dict(VisualFlowExecution.RUN_TYPE_CHOICES):
            run_type = VisualFlowExecution.RUN_TYPE_LOCAL
        visual_flow_payload = request.data.get('visual_flow') if isinstance(request.data.get('visual_flow'), dict) else {}
        execution = create_visual_flow_execution_record(
            request,
            run_type,
            flow_id=visual_flow_payload.get('flow_id') or request.data.get('flow_id') or '',
            graph_data=visual_flow_payload.get('graph_data') or request.data.get('graph_data') or {},
            flow_name=visual_flow_payload.get('flow_name') or request.data.get('flow_name') or '',
        )
        execution.status = VisualFlowExecution.STATUS_RUNNING
        execution.started_at = timezone.now()
        execution.save(update_fields=['status', 'started_at', 'updated_at'])
        return Response(
            VisualFlowExecutionSerializer(execution, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class VisualFlowExecutionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, execution_id):
        try:
            return VisualFlowExecution.objects.select_related('flow', 'created_by').prefetch_related(
                Prefetch(
                    'steps',
                    queryset=VisualFlowExecutionStep.objects.order_by('step_order', 'id'),
                    to_attr='prefetched_steps',
                )
            ).get(execution_id=execution_id)
        except VisualFlowExecution.DoesNotExist:
            raise NotFound('执行结果不存在')

    def get(self, request, execution_id):
        execution = self.get_object(execution_id)
        if fail_timed_out_visual_flow_execution(execution):
            execution = self.get_object(execution_id)
        return Response(VisualFlowExecutionSerializer(execution, context={'request': request}).data)


class VisualFlowExecutionIngestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, execution_id):
        try:
            execution = VisualFlowExecution.objects.get(execution_id=execution_id)
        except VisualFlowExecution.DoesNotExist:
            raise NotFound('执行结果不存在')

        events = request.data.get('events')
        if isinstance(request.data.get('event'), dict):
            events = [request.data.get('event')]
        if not isinstance(events, list):
            return Response({'error': 'events must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        ingest_visual_flow_execution_events(execution, events)
        execution.refresh_from_db()
        return Response(VisualFlowExecutionSerializer(execution, context={'request': request}).data)


class VisualFlowExecutionFinalizeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, execution_id):
        try:
            execution = VisualFlowExecution.objects.get(execution_id=execution_id)
        except VisualFlowExecution.DoesNotExist:
            raise NotFound('执行结果不存在')

        result_payload = {
            'success': bool(request.data.get('success')),
            'stdout': request.data.get('stdout') or '',
            'stderr': request.data.get('stderr') or request.data.get('error') or '',
            'returncode': request.data.get('returncode'),
            'error': request.data.get('error') or '',
        }
        finalize_visual_flow_execution(execution, result_payload)
        execution.refresh_from_db()
        return Response(VisualFlowExecutionSerializer(execution, context={'request': request}).data)


DEV_SELF_TEST_AUDIT_PENDING = 'pending'
DEV_SELF_TEST_AUDIT_APPROVED = 'approved'
DEV_SELF_TEST_AUDIT_REJECTED = 'rejected'
DEV_SELF_TEST_EDIT_PERMISSION_CODE = 'button:manual-testcases:devselftest:edit'


def can_user_edit_dev_self_test(user, audit_status=None):
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True

    if hasattr(user, 'has_permission_code') and user.has_permission_code(DEV_SELF_TEST_EDIT_PERMISSION_CODE):
        return True

    return audit_status == DEV_SELF_TEST_AUDIT_APPROVED


def get_dev_self_test_queryset_for_user(user, query_params):
    accessible_projects = get_visible_manual_workspace_projects()
    queryset = ManualTestCaseMindmap.objects.filter(
        project__in=accessible_projects,
        mindmap_scope=TESTING_MINDMAP_SCOPE,
    ).order_by('-updated_at')

    project_id = query_params.get('project')
    if project_id:
        queryset = queryset.filter(project_id=project_id)

    category_id = query_params.get('category')
    if category_id not in (None, ''):
        queryset = queryset.filter(category_id=category_id)

    version_id = query_params.get('version')
    if version_id and version_id != 'all':
        queryset = queryset.filter(version_id=version_id)

    mindmap_name = query_params.get('mindmap_name')
    if mindmap_name:
        queryset = queryset.filter(name__icontains=mindmap_name)

    requirement_key = query_params.get('requirement_key')
    if requirement_key:
        queryset = queryset.filter(requirement_key__icontains=requirement_key)

    requirement_title = query_params.get('requirement_title')
    if requirement_title:
        queryset = queryset.filter(requirement_title__icontains=requirement_title)

    responsibility_group = query_params.get('responsibility_group')
    if responsibility_group:
        queryset = queryset.filter(responsibility_group__icontains=responsibility_group)

    frontend_developer = query_params.get('frontend_developer')
    if frontend_developer:
        queryset = queryset.filter(frontend_developer_id=frontend_developer)

    backend_developer = query_params.get('backend_developer')
    if backend_developer:
        queryset = queryset.filter(backend_developer_id=backend_developer)

    return queryset


def find_dev_self_test_node_path(node, node_id, ancestors=None):
    if not isinstance(node, dict):
        return None

    current_path = [*(ancestors or []), node]
    if get_mindmap_node_native_id(node) == str(node_id):
        return current_path

    for child in node.get('children') or []:
        matched_path = find_dev_self_test_node_path(child, node_id, current_path)
        if matched_path:
            return matched_path

    return None


def resolve_dev_self_test_node_descriptor(mindmap, node_id):
    node_id = str(node_id or '').strip()
    if not node_id or not mindmap:
        return None

    parsed_public_id = parse_public_node_id(node_id)
    if parsed_public_id:
        descriptor = resolve_public_node_descriptor(mindmap, node_id)
        if descriptor and descriptor.get('node_type') == 'testpoint':
            return descriptor
        return None

    node_path = find_dev_self_test_node_path((mindmap.mindmap_data or {}).get('root'), node_id)
    if not node_path:
        return None

    target_node = node_path[-1]
    target_data = target_node.get('data') or {}
    if target_data.get('nodeType') != 'testpoint':
        return None

    return {
        'public_id': '',
        'node_id': get_mindmap_node_native_id(target_node),
        'node_path': node_path,
        'node': target_node,
        'data': target_data,
        'node_type': 'testpoint',
    }


def build_dev_self_test_preconditions(node_path):
    module_parts = []
    last_module_index = -1

    for index, node in enumerate(node_path[:-1]):
        data = node.get('data') or {}
        text = str(data.get('text') or '').strip()
        if data.get('nodeType') == 'module' and text:
            module_parts.append(text)
            last_module_index = index

    lines = []
    module_path = ' / '.join(module_parts)
    if module_path:
        lines.append(f'1. {module_path}')

    start_index = last_module_index + 1 if last_module_index >= 0 else 0
    between_nodes = []
    for node in node_path[start_index:-1]:
        data = node.get('data') or {}
        text = str(data.get('text') or '').strip()
        if text:
            between_nodes.append(text)

    next_number = len(lines) + 1
    for offset, text in enumerate(between_nodes, start=next_number):
        lines.append(f'{offset}. {text}')

    return module_path, '\n'.join(lines)


def normalize_dev_self_test_priority(value):
    try:
        normalized_value = int(value)
    except (TypeError, ValueError):
        return 1

    return normalized_value or 1


def build_dev_self_test_path(node_path):
    return ' / '.join(
        str((node.get('data') or {}).get('text') or '').strip()
        for node in (node_path or [])
        if str((node.get('data') or {}).get('text') or '').strip()
    )


def build_dev_self_test_record_path(mindmap, record):
    root_text = str((((mindmap.mindmap_data or {}).get('root') or {}).get('data') or {}).get('text') or '').strip()
    path_parts = [root_text]
    path_parts.extend(
        segment.strip()
        for segment in str(record.module_path or '').split('/')
        if segment.strip()
    )
    if record.testpoint:
        path_parts.append(str(record.testpoint).strip())
    return ' / '.join(part for part in path_parts if part)


def build_dev_self_test_live_snapshot(mindmap, node_path, *, node_identifier=None, public_id='', native_node_id=''):
    target_node = node_path[-1]
    target_data = target_node.get('data') or {}
    target_text = str(target_data.get('text') or '').strip()
    module_path, preconditions = build_dev_self_test_preconditions(node_path)
    native_node_id = str(native_node_id or get_mindmap_node_native_id(target_node)).strip()
    public_id = str(public_id or '').strip()
    node_identifier = str(node_identifier or native_node_id or public_id).strip()

    return {
        'id': node_identifier,
        'node_id': native_node_id,
        'public_id': public_id,
        'mindmap_id': mindmap.id,
        'mindmap_name': mindmap.name,
        'requirement_key': mindmap.requirement_key or '',
        'requirement_title': mindmap.requirement_title or '',
        'module': module_path.split(' / ')[-1] if module_path else '',
        'module_path': module_path,
        'path': build_dev_self_test_path(node_path),
        'testpoint': target_text,
        'priority': normalize_dev_self_test_priority(target_data.get('priority')),
        'preconditions': preconditions,
        'steps': str(target_data.get('steps') or ''),
        'expected_result': target_text,
        'remark': str(target_data.get('remark') or ''),
        'status': str(target_data.get('status') or 'not_run'),
        'responsibility_group': mindmap.responsibility_group or '',
        'frontend_developer': mindmap.frontend_developer,
        'backend_developer': mindmap.backend_developer,
        'updated_at': max(mindmap.created_at, mindmap.updated_at),
    }


def build_dev_self_test_record_snapshot(record):
    mindmap = record.mindmap
    return {
        'id': str(record.node_id),
        'mindmap_id': mindmap.id,
        'mindmap_name': mindmap.name,
        'requirement_key': mindmap.requirement_key or '',
        'requirement_title': mindmap.requirement_title or '',
        'module': record.module or '',
        'module_path': record.module_path or '',
        'path': build_dev_self_test_record_path(mindmap, record),
        'testpoint': record.testpoint or '',
        'priority': record.priority or 1,
        'preconditions': record.preconditions or '',
        'steps': record.steps or '',
        'expected_result': record.expected_result or '',
        'remark': record.remark or '',
        'status': record.status or 'not_run',
        'responsibility_group': mindmap.responsibility_group or '',
        'frontend_developer': mindmap.frontend_developer,
        'backend_developer': mindmap.backend_developer,
        'updated_at': record.updated_at,
    }


def build_dev_self_test_response_payload(*, user=None, live_snapshot=None, record=None):
    if record and live_snapshot and can_user_edit_dev_self_test(user, record.audit_status):
        payload = dict(live_snapshot)
        payload.update({
            'preconditions': record.preconditions or payload.get('preconditions') or '',
            'steps': record.steps or '',
            'expected_result': record.expected_result or payload.get('expected_result') or payload.get('testpoint') or '',
            'remark': record.remark or '',
            'status': record.status or payload.get('status') or 'not_run',
            'updated_at': record.updated_at,
        })
        payload['audit_status'] = record.audit_status
        payload['can_edit'] = True
        return payload

    if record and can_user_edit_dev_self_test(user, record.audit_status):
        payload = build_dev_self_test_record_snapshot(record)
        payload['audit_status'] = record.audit_status
        payload['can_edit'] = True
        return payload

    if live_snapshot:
        payload = dict(live_snapshot)
        payload['audit_status'] = record.audit_status if record else DEV_SELF_TEST_AUDIT_PENDING
        payload['can_edit'] = can_user_edit_dev_self_test(user, payload['audit_status'])
        return payload

    if record:
        payload = build_dev_self_test_record_snapshot(record)
        payload['audit_status'] = record.audit_status
        payload['can_edit'] = can_user_edit_dev_self_test(user, record.audit_status)
        return payload

    return None


def assign_snapshot_to_dev_self_test_record(record, snapshot, *, refresh_execution_fields):
    record.module = snapshot.get('module') or ''
    record.module_path = snapshot.get('module_path') or ''
    record.testpoint = snapshot.get('testpoint') or ''
    record.priority = snapshot.get('priority') or 1
    record.preconditions = snapshot.get('preconditions') or ''
    record.expected_result = snapshot.get('expected_result') or snapshot.get('testpoint') or ''

    if refresh_execution_fields:
        record.steps = snapshot.get('steps') or ''
        record.remark = snapshot.get('remark') or ''
        record.status = snapshot.get('status') or 'not_run'


class DevSelfTestListView(generics.GenericAPIView):
    """开发自测列表 - 提取P1优先级的测试点"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DevSelfTestSerializer
    pagination_class = ManualTestCasePagination

    def get_queryset(self):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        queryset = ManualTestCaseMindmap.objects.filter(
            project__in=accessible_projects,
            mindmap_scope=TESTING_MINDMAP_SCOPE,
        ).order_by('-updated_at')

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        category_id = self.request.query_params.get('category')
        if category_id not in (None, ''):
            queryset = queryset.filter(category_id=category_id)

        # 版本过滤
        version_id = self.request.query_params.get('version')
        if version_id and version_id != 'all':
            queryset = queryset.filter(version_id=version_id)

        # 脑图名称过滤
        mindmap_name = self.request.query_params.get('mindmap_name')
        if mindmap_name:
            queryset = queryset.filter(name__icontains=mindmap_name)

        # 责任小组过滤
        responsibility_group = self.request.query_params.get('responsibility_group')
        if responsibility_group:
            queryset = queryset.filter(responsibility_group__icontains=responsibility_group)

        # 前端开发过滤
        frontend_developer = self.request.query_params.get('frontend_developer')
        if frontend_developer:
            queryset = queryset.filter(frontend_developer_id=frontend_developer)

        # 后端开发过滤
        backend_developer = self.request.query_params.get('backend_developer')
        if backend_developer:
            queryset = queryset.filter(backend_developer_id=backend_developer)

        return queryset

    def _collect_p1_testpoints(self, node, *, mindmap, path_parts=None, module_parts=None):
        """递归收集P1优先级的测试点"""
        if not isinstance(node, dict):
            return []

        result = []
        path_parts = path_parts or []
        module_parts = module_parts or []
        data = node.get('data') or {}
        text = str(data.get('text') or '').strip()
        current_path = [*path_parts, text] if text else list(path_parts)
        current_module_parts = (
            [*module_parts, text]
            if data.get('nodeType') == 'module' and text
            else list(module_parts)
        )

        # 如果是测试点且优先级为P1
        if data.get('nodeType') == 'testpoint' and data.get('priority') == 1:
            # 提取模块名称（父节点的文本）
            module = current_module_parts[-1] if current_module_parts else ''
            module_path = ' / '.join(current_module_parts)

            item = {
                'id': node.get('id', ''),
                'mindmap_id': mindmap.id,
                'mindmap_name': mindmap.name,
                'version_name': mindmap.version.name if getattr(mindmap, 'version', None) else '',
                'module': module,
                'module_path': module_path,
                'testpoint': text,
                'priority': 1,
                'status': data.get('status') or 'not_run',
                'responsibility_group': mindmap.responsibility_group or '',
                'frontend_developer': mindmap.frontend_developer,
                'backend_developer': mindmap.backend_developer,
                'updated_at': max(mindmap.created_at, mindmap.updated_at)
            }
            result.append(item)

        # 递归处理子节点
        for child in node.get('children', []):
            result.extend(
                self._collect_p1_testpoints(
                    child,
                    mindmap=mindmap,
                    path_parts=current_path,
                    module_parts=current_module_parts,
                )
            )

        return result

    def get(self, request, *args, **kwargs):
        mindmaps = self.get_queryset()

        # 获取当前筛选条件下的所有创建人（去重）
        from apps.users.models import User
        creator_ids = mindmaps.values_list('author_id', flat=True).distinct()
        creators_qs = User.objects.filter(id__in=creator_ids)

        # 构建创建人列表
        creators = []
        for user in creators_qs:
            creators.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'full_name': user.full_name
            })

        all_testpoints = []
        for mindmap in mindmaps:
            mindmap_data = mindmap.mindmap_data
            if not mindmap_data or not isinstance(mindmap_data, dict):
                continue

            root = mindmap_data.get('root', {})
            testpoints = self._collect_p1_testpoints(root, mindmap=mindmap)
            all_testpoints.extend(testpoints)

        # 状态过滤（在收集完所有测试点后过滤）
        status = self.request.query_params.get('status')
        if status:
            all_testpoints = [tp for tp in all_testpoints if tp.get('status') == status]

        # 分页
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(all_testpoints, request)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            response.data['creators'] = creators
            return response

        serializer = self.get_serializer(all_testpoints, many=True)
        return Response({
            'results': serializer.data,
            'creators': creators
        })

    def get_queryset(self):
        return get_dev_self_test_queryset_for_user(self.request.user, self.request.query_params)

    def _collect_live_testpoints(self, node, *, mindmap):
        if not isinstance(node, dict):
            return []

        result = []
        for descriptor in iter_mindmap_target_nodes(
            node,
            mindmap_id=mindmap.id,
            target_type='testpoint',
        ):
            data = descriptor.get('data') or {}
            if normalize_dev_self_test_priority(data.get('priority')) != 1:
                continue

            node_identifier = descriptor.get('node_id') or descriptor.get('public_id') or ''
            result.append(build_dev_self_test_live_snapshot(
                mindmap,
                descriptor.get('node_path') or [],
                node_identifier=node_identifier,
                public_id=descriptor.get('public_id') or '',
                native_node_id=descriptor.get('node_id') or '',
            ))

        return result

    def get(self, request, *args, **kwargs):
        mindmaps = list(self.get_queryset().select_related('frontend_developer', 'backend_developer'))
        mindmap_ids = [mindmap.id for mindmap in mindmaps]
        record_map = {
            (record.mindmap_id, str(record.node_id)): record
            for record in DevSelfTestRecord.objects.filter(mindmap_id__in=mindmap_ids).select_related(
                'mindmap',
                'mindmap__frontend_developer',
                'mindmap__backend_developer',
            )
        }

        all_testpoints = []
        seen_keys = set()

        for mindmap in mindmaps:
            mindmap_data = mindmap.mindmap_data
            if not mindmap_data or not isinstance(mindmap_data, dict):
                continue

            live_items = self._collect_live_testpoints(mindmap_data.get('root', {}), mindmap=mindmap)
            for live_item in live_items:
                aliases = {
                    str(live_item.get('id') or '').strip(),
                    str(live_item.get('node_id') or '').strip(),
                    str(live_item.get('public_id') or '').strip(),
                }
                aliases.discard('')
                record = next(
                    (record_map.get((mindmap.id, alias)) for alias in aliases if record_map.get((mindmap.id, alias))),
                    None,
                )
                payload = build_dev_self_test_response_payload(
                    user=request.user,
                    live_snapshot=live_item,
                    record=record,
                )
                if payload:
                    all_testpoints.append(payload)
                    for alias in aliases:
                        seen_keys.add((mindmap.id, alias))

        for key, record in record_map.items():
            if key in seen_keys or record.audit_status != DEV_SELF_TEST_AUDIT_APPROVED:
                continue

            payload = build_dev_self_test_response_payload(user=request.user, record=record)
            if payload:
                all_testpoints.append(payload)

        status_value = self.request.query_params.get('status')
        if status_value:
            all_testpoints = [item for item in all_testpoints if item.get('status') == status_value]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(all_testpoints, request)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(all_testpoints, many=True)
        return Response(serializer.data)


class DevSelfTestDetailView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DevSelfTestDetailSerializer

    def _get_accessible_mindmap(self, mindmap_id):
        user = self.request.user
        accessible_projects = get_visible_manual_workspace_projects()
        mindmap = ManualTestCaseMindmap.objects.filter(
            project__in=accessible_projects,
            mindmap_scope=TESTING_MINDMAP_SCOPE,
            id=mindmap_id,
        ).first()

        if not mindmap:
            raise NotFound('Mindmap not found')

        return mindmap

    def _get_request_identifiers(self):
        mindmap_id = self.request.query_params.get('mindmap_id')
        node_id = self.request.query_params.get('node_id')

        if not mindmap_id:
            raise ValidationError({'mindmap_id': ['This field is required.']})

        if not node_id:
            raise ValidationError({'node_id': ['This field is required.']})

        try:
            normalized_mindmap_id = int(mindmap_id)
        except (TypeError, ValueError):
            raise ValidationError({'mindmap_id': ['A valid integer is required.']})

        return normalized_mindmap_id, str(node_id)

    def _find_node_path(self, node, node_id, ancestors=None):
        if not isinstance(node, dict):
            return None

        current_path = [*(ancestors or []), node]
        if str(node.get('id') or '') == str(node_id):
            return current_path

        for child in node.get('children') or []:
            matched_path = self._find_node_path(child, node_id, current_path)
            if matched_path:
                return matched_path

        return None

    def _resolve_target(self):
        mindmap_id, node_id = self._get_request_identifiers()
        mindmap = self._get_accessible_mindmap(mindmap_id)
        mindmap_data = mindmap.mindmap_data if isinstance(mindmap.mindmap_data, dict) else {}
        root = mindmap_data.get('root')
        node_path = self._find_node_path(root, node_id)

        if not node_path:
            raise NotFound('Node not found')

        target_node = node_path[-1]
        target_data = target_node.get('data') or {}
        if target_data.get('nodeType') != 'testpoint':
            raise ValidationError({'node_id': ['The selected node is not a testpoint.']})

        return mindmap, node_path, target_node

    def _build_preconditions(self, node_path):
        module_parts = []
        last_module_index = -1

        for index, node in enumerate(node_path[:-1]):
            data = node.get('data') or {}
            text = str(data.get('text') or '').strip()
            if data.get('nodeType') == 'module' and text:
                module_parts.append(text)
                last_module_index = index

        lines = []
        module_path = ' / '.join(module_parts)
        if module_path:
            lines.append(f'1. {module_path}')

        start_index = last_module_index + 1 if last_module_index >= 0 else 0
        between_nodes = []
        for node in node_path[start_index:-1]:
            data = node.get('data') or {}
            text = str(data.get('text') or '').strip()
            if text:
                between_nodes.append(text)

        next_number = len(lines) + 1
        for offset, text in enumerate(between_nodes, start=next_number):
            lines.append(f'{offset}. {text}')

        return module_path, '\n'.join(lines)

    def _build_detail_payload(self, mindmap, node_path):
        target_node = node_path[-1]
        target_data = target_node.get('data') or {}
        target_text = str(target_data.get('text') or '').strip()
        module_path, preconditions = self._build_preconditions(node_path)

        return {
            'id': str(target_node.get('id') or ''),
            'mindmap_id': mindmap.id,
            'mindmap_name': mindmap.name,
            'module': module_path.split(' / ')[-1] if module_path else '',
            'module_path': module_path,
            'testpoint': target_text,
            'preconditions': preconditions,
            'steps': str(target_data.get('steps') or ''),
            'expected_result': target_text,
            'remark': str(target_data.get('remark') or ''),
            'status': str(target_data.get('status') or 'not_run'),
            'responsibility_group': mindmap.responsibility_group or '',
            'frontend_developer': mindmap.frontend_developer,
            'backend_developer': mindmap.backend_developer,
            'updated_at': max(mindmap.created_at, mindmap.updated_at),
        }

    def get(self, request, *args, **kwargs):
        mindmap, node_path, _target_node = self._resolve_target()
        serializer = self.get_serializer(self._build_detail_payload(mindmap, node_path))
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        mindmap, node_path, target_node = self._resolve_target()
        update_serializer = DevSelfTestUpdateSerializer(data=request.data, partial=True)
        update_serializer.is_valid(raise_exception=True)

        target_data = target_node.get('data')
        if not isinstance(target_data, dict):
            target_data = {}
            target_node['data'] = target_data

        validated_data = update_serializer.validated_data
        if 'steps' in validated_data:
            target_data['steps'] = validated_data.get('steps') or ''
        if 'remark' in validated_data:
            target_data['remark'] = validated_data.get('remark') or ''
        if 'status' in validated_data:
            target_data['status'] = validated_data.get('status') or 'not_run'

        mindmap.mindmap_data = mindmap.mindmap_data
        mindmap.save()

        serializer = self.get_serializer(self._build_detail_payload(mindmap, node_path))
        return Response(serializer.data)

    def _get_accessible_mindmap(self, mindmap_id):
        mindmap = get_dev_self_test_queryset_for_user(self.request.user, {}).filter(
            id=mindmap_id
        ).select_related('frontend_developer', 'backend_developer').first()

        if not mindmap:
            raise NotFound('Mindmap not found')

        return mindmap

    def _get_request_identifiers(self):
        mindmap_id = self.request.query_params.get('mindmap_id')
        node_id = self.request.query_params.get('node_id')

        if not mindmap_id:
            raise ValidationError({'mindmap_id': ['This field is required.']})

        if not node_id:
            raise ValidationError({'node_id': ['This field is required.']})

        try:
            normalized_mindmap_id = int(mindmap_id)
        except (TypeError, ValueError):
            raise ValidationError({'mindmap_id': ['A valid integer is required.']})

        return normalized_mindmap_id, str(node_id)

    def _resolve_payload(self):
        mindmap_id, node_id = self._get_request_identifiers()
        mindmap = self._get_accessible_mindmap(mindmap_id)

        descriptor = resolve_dev_self_test_node_descriptor(mindmap, node_id)
        node_id_aliases = [str(node_id)]
        if descriptor:
            for alias in (descriptor.get('node_id'), descriptor.get('public_id')):
                alias = str(alias or '').strip()
                if alias and alias not in node_id_aliases:
                    node_id_aliases.append(alias)

        records = {
            str(record.node_id): record
            for record in DevSelfTestRecord.objects.filter(mindmap=mindmap, node_id__in=node_id_aliases)
        }
        record = next((records.get(alias) for alias in node_id_aliases if records.get(alias)), None)

        if record and can_user_edit_dev_self_test(self.request.user, record.audit_status):
            payload = build_dev_self_test_response_payload(user=self.request.user, record=record)
            return mindmap, record, payload

        live_snapshot = None

        if descriptor:
            node_path = descriptor.get('node_path') or []
            target_data = descriptor.get('data') or {}
            if target_data.get('nodeType') == 'testpoint' and normalize_dev_self_test_priority(target_data.get('priority')) == 1:
                node_identifier = descriptor.get('node_id') or descriptor.get('public_id') or node_id
                live_snapshot = build_dev_self_test_live_snapshot(
                    mindmap,
                    node_path,
                    node_identifier=node_identifier,
                    public_id=descriptor.get('public_id') or '',
                    native_node_id=descriptor.get('node_id') or '',
                )

        payload = build_dev_self_test_response_payload(
            user=self.request.user,
            live_snapshot=live_snapshot,
            record=record,
        )
        if not payload:
            raise NotFound('Node not found')

        return mindmap, record, payload

    def get(self, request, *args, **kwargs):
        _mindmap, _record, payload = self._resolve_payload()
        serializer = self.get_serializer(payload)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        mindmap, record, payload = self._resolve_payload()
        current_audit_status = record.audit_status if record else payload.get('audit_status')

        if not can_user_edit_dev_self_test(request.user, current_audit_status):
            raise ValidationError({'detail': ['仅审核通过的自测测试点允许编辑。']})

        if not record:
            record = DevSelfTestRecord(
                mindmap=mindmap,
                node_id=str(payload.get('id') or ''),
                audit_status=current_audit_status or DEV_SELF_TEST_AUDIT_PENDING,
            )
            assign_snapshot_to_dev_self_test_record(record, payload, refresh_execution_fields=True)

        update_serializer = DevSelfTestUpdateSerializer(data=request.data, partial=True)
        update_serializer.is_valid(raise_exception=True)

        validated_data = update_serializer.validated_data
        if 'steps' in validated_data:
            record.steps = validated_data.get('steps') or ''
        if 'remark' in validated_data:
            record.remark = validated_data.get('remark') or ''
        if 'status' in validated_data:
            record.status = validated_data.get('status') or 'not_run'
        record.save()

        serializer = self.get_serializer(build_dev_self_test_response_payload(user=request.user, record=record))
        return Response(serializer.data)


class DevSelfTestAuditView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DevSelfTestAuditSerializer

    def _build_accessible_mindmap_map(self, items):
        mindmap_ids = {item['mindmap_id'] for item in items}
        mindmaps = get_dev_self_test_queryset_for_user(self.request.user, {}).filter(
            id__in=mindmap_ids
        ).select_related('frontend_developer', 'backend_developer')
        return {mindmap.id: mindmap for mindmap in mindmaps}

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        audit_status = validated_data['audit_status']
        items = validated_data['items']
        accessible_mindmaps = self._build_accessible_mindmap_map(items)

        processed = 0
        missing_items = []
        audit_time = timezone.now()

        for item in items:
            node_id = str(item['node_id'])
            mindmap = accessible_mindmaps.get(item['mindmap_id'])
            if not mindmap:
                missing_items.append({'mindmap_id': item['mindmap_id'], 'node_id': node_id})
                continue

            descriptor = resolve_dev_self_test_node_descriptor(mindmap, node_id)
            node_id_aliases = [node_id]
            if descriptor:
                for alias in (descriptor.get('node_id'), descriptor.get('public_id')):
                    alias = str(alias or '').strip()
                    if alias and alias not in node_id_aliases:
                        node_id_aliases.append(alias)

            records = {
                str(record.node_id): record
                for record in DevSelfTestRecord.objects.filter(mindmap=mindmap, node_id__in=node_id_aliases)
            }
            record = next((records.get(alias) for alias in node_id_aliases if records.get(alias)), None)
            if record and record.audit_status == DEV_SELF_TEST_AUDIT_APPROVED:
                snapshot = build_dev_self_test_record_snapshot(record)
                refresh_execution_fields = False
            else:
                if descriptor:
                    node_path = descriptor.get('node_path') or []
                    target_data = descriptor.get('data') or {}
                    if target_data.get('nodeType') != 'testpoint':
                        missing_items.append({'mindmap_id': item['mindmap_id'], 'node_id': node_id})
                        continue
                    snapshot = build_dev_self_test_live_snapshot(
                        mindmap,
                        node_path,
                        node_identifier=descriptor.get('node_id') or descriptor.get('public_id') or node_id,
                        public_id=descriptor.get('public_id') or '',
                        native_node_id=descriptor.get('node_id') or '',
                    )
                    refresh_execution_fields = not record or record.audit_status != DEV_SELF_TEST_AUDIT_APPROVED
                elif record:
                    snapshot = build_dev_self_test_record_snapshot(record)
                    refresh_execution_fields = False
                else:
                    missing_items.append({'mindmap_id': item['mindmap_id'], 'node_id': node_id})
                    continue

            if not record:
                record = DevSelfTestRecord(mindmap=mindmap, node_id=str(snapshot.get('id') or node_id))
                refresh_execution_fields = True

            assign_snapshot_to_dev_self_test_record(
                record,
                snapshot,
                refresh_execution_fields=refresh_execution_fields,
            )
            record.audit_status = audit_status
            record.audited_by = request.user
            record.audited_at = audit_time
            record.save()
            processed += 1

        return Response({
            'processed_count': processed,
            'skipped_count': len(missing_items),
            'skipped_items': missing_items,
        })
