from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.branding import PLATFORM_BRAND_NAME
from .asset_insight import (
    build_asset_insight_payload,
    get_project_knowledge_status,
    set_project_knowledge_enabled,
)
from .models import (
    KnowledgeFeedback,
    KnowledgeIndexRun,
    KnowledgeObject,
    KnowledgeQueryTrace,
    KnowledgeRelation,
    KnowledgeRepositoryConfig,
    KnowledgeSpace,
)
from .serializers import (
    KnowledgeFeedbackSerializer,
    KnowledgeIndexRunSerializer,
    KnowledgeObjectSerializer,
    KnowledgeQueryTraceSerializer,
    KnowledgeRelationSerializer,
    KnowledgeRepositoryConfigSerializer,
    KnowledgeSpaceSerializer,
)
from .services import (
    annotate_spaces_queryset,
    build_authorization_payload,
    build_graph_payload,
    confirm_local_authorization,
    dispatch_repository_index,
    get_queryset_for_user,
    index_repository,
    maybe_auto_index_repository,
    query_knowledge_context,
    seed_current_platform_repository,
    test_database_schema_connection,
    test_repository_connection,
)


class UserScopedViewSetMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering = ['-id']

    def get_queryset(self):
        return get_queryset_for_user(self.queryset, self.request.user)


class KnowledgeSpaceViewSet(UserScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeSpace.objects.select_related('project', 'owner').all()
    serializer_class = KnowledgeSpaceSerializer
    filterset_fields = ['space_type', 'project', 'is_active', 'key']
    search_fields = ['key', 'name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        return annotate_spaces_queryset(super().get_queryset())


class KnowledgeRepositoryConfigViewSet(UserScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = KnowledgeRepositoryConfig.objects.select_related('project', 'space', 'created_by').all()
    serializer_class = KnowledgeRepositoryConfigSerializer
    filterset_fields = ['project', 'space', 'provider', 'repository_mode', 'auth_mode', 'authorization_status', 'is_active']
    search_fields = ['name', 'repository_url', 'local_path', 'username']
    ordering_fields = ['created_at', 'updated_at', 'last_indexed_at', 'name']
    ordering = ['-updated_at', '-id']

    def perform_create(self, serializer):
        config = serializer.save()
        maybe_auto_index_repository(config, user=self.request.user, trigger='auto_config_created')

    def perform_update(self, serializer):
        config = serializer.save()
        maybe_auto_index_repository(config, user=self.request.user, trigger='auto_config_updated')

    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        config = self.get_object()
        payload, status_code = test_repository_connection(config)
        config.last_test_result = payload
        config.save(update_fields=['last_test_result', 'updated_at'])
        return Response(payload, status=status_code)

    @action(detail=True, methods=['post'], url_path='test-database-schema')
    def test_database_schema(self, request, pk=None):
        config = self.get_object()
        payload, status_code = test_database_schema_connection(config)
        config.last_schema_test_result = payload
        config.save(update_fields=['last_schema_test_result', 'updated_at'])
        return Response(payload, status=status_code)

    @action(detail=True, methods=['post'])
    def authorize(self, request, pk=None):
        config = self.get_object()
        payload = build_authorization_payload(config, request)
        return Response(payload)

    @action(detail=True, methods=['post'])
    def index(self, request, pk=None):
        config = self.get_object()
        async_payload = dispatch_repository_index(config, user=request.user, trigger='manual')
        if isinstance(async_payload, dict) and async_payload.get('queued'):
            return Response(
                {
                    'queued': True,
                    'task_id': async_payload.get('task_id'),
                    'space': config.space_id,
                    'status': 'queued',
                },
                status=status.HTTP_202_ACCEPTED,
            )
        if isinstance(async_payload, dict) and async_payload.get('error'):
            return Response(
                {
                    'queued': False,
                    'status': async_payload.get('status') or 'failed',
                    'detail': async_payload.get('error'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        run = async_payload.get('run') if isinstance(async_payload, dict) else index_repository(config, user=request.user, trigger='manual')
        if not run:
            return Response(
                {'queued': False, 'status': 'pending_config', 'detail': '仓库或数据库配置未就绪。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(KnowledgeIndexRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='seed-current-platform')
    def seed_current_platform(self, request):
        config, created = seed_current_platform_repository(
            user=request.user,
            project_id=request.data.get('project') or request.data.get('project_id'),
        )
        index_payload = maybe_auto_index_repository(config, user=request.user, trigger='auto_seed_current_platform')
        if isinstance(index_payload, dict) and index_payload.get('run'):
            run = index_payload['run']
            index_payload = {
                'queued': False,
                'run_id': run.id,
                'status': run.status,
                'object_count': run.object_count,
                'relation_count': run.relation_count,
            }
        serializer = self.get_serializer(config)
        return Response(
            {
                'created': created,
                'config': serializer.data,
                'index': index_payload,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class KnowledgeIndexRunViewSet(UserScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeIndexRun.objects.select_related('space', 'repository_config', 'created_by').all()
    serializer_class = KnowledgeIndexRunSerializer
    filterset_fields = ['space', 'repository_config', 'status', 'trigger']
    search_fields = ['repository_config__name', 'log', 'error_message']
    ordering_fields = ['started_at', 'finished_at', 'object_count', 'relation_count']
    ordering = ['-started_at', '-id']


class KnowledgeObjectViewSet(UserScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeObject.objects.select_related('space', 'project', 'repository_config').all()
    serializer_class = KnowledgeObjectSerializer
    filterset_fields = ['space', 'project', 'repository_config', 'object_type', 'tab_key', 'db_table']
    search_fields = ['key', 'name', 'summary', 'content', 'search_text', 'page_path', 'api_path', 'db_table', 'field_name']
    ordering_fields = ['object_type', 'name', 'indexed_at', 'updated_at']
    ordering = ['object_type', 'name', 'id']


class KnowledgeRelationViewSet(UserScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeRelation.objects.select_related('space', 'source', 'target').all()
    serializer_class = KnowledgeRelationSerializer
    filterset_fields = ['space', 'source', 'target', 'relation_type']
    search_fields = ['label', 'source__name', 'target__name', 'source_ref']
    ordering_fields = ['created_at', 'weight']
    ordering = ['source_id', 'target_id', 'relation_type']

    def get_queryset(self):
        spaces = get_queryset_for_user(KnowledgeSpace.objects.all(), self.request.user)
        return self.queryset.filter(space__in=spaces)


class KnowledgeQueryTraceViewSet(UserScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeQueryTrace.objects.select_related('space', 'project', 'created_by').all()
    serializer_class = KnowledgeQueryTraceSerializer
    filterset_fields = ['space', 'project', 'created_by']
    search_fields = ['question', 'normalized_query']
    ordering_fields = ['created_at', 'confidence_score']
    ordering = ['-created_at', '-id']


class KnowledgeFeedbackViewSet(UserScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = KnowledgeFeedback.objects.select_related('trace', 'knowledge_object', 'created_by').all()
    serializer_class = KnowledgeFeedbackSerializer
    filterset_fields = ['trace', 'knowledge_object', 'feedback_type', 'status']
    search_fields = ['content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(created_by=user)


class KnowledgeGraphView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        space_id = request.query_params.get('space') or request.query_params.get('space_id')
        space_key = request.query_params.get('space_key')
        spaces = get_queryset_for_user(KnowledgeSpace.objects.all(), request.user)
        if space_id:
            space = get_object_or_404(spaces, id=space_id)
        elif space_key:
            space = get_object_or_404(spaces, key=space_key)
        else:
            space = spaces.order_by('id').first()
        if not space:
            return Response({'space': None, 'nodes': [], 'edges': []})
        payload = build_graph_payload(
            space,
            center_object_id=request.query_params.get('center_object'),
            limit=int(request.query_params.get('limit') or 120),
        )
        return Response(payload)


class KnowledgeQueryContextView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = query_knowledge_context(request.data if isinstance(request.data, dict) else {}, user=request.user)
        return Response(payload)


class KnowledgeAssetInsightView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = build_asset_insight_payload(request.user, request.query_params)
        return Response(payload)


class ProjectKnowledgeStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id') or request.query_params.get('project')
        return Response(get_project_knowledge_status(request.user, project_id=project_id))


class ProjectKnowledgeEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_id = request.data.get('project_id') or request.data.get('project')
        enabled = request.data.get('enabled', True)
        trigger_index = request.data.get('trigger_index', True)
        payload, status_code = set_project_knowledge_enabled(
            request.user,
            project_id=project_id,
            enabled=enabled,
            trigger_index=trigger_index,
        )
        return Response(payload, status=status_code)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def local_authorization_confirm(request, pk):
    config = get_object_or_404(KnowledgeRepositoryConfig, pk=pk)
    state = request.GET.get('state') or request.POST.get('state')
    if request.method == 'POST':
        success, message = confirm_local_authorization(config, state)
        if success:
            maybe_auto_index_repository(config, user=config.created_by, trigger='auto_authorized')
        status_text = '授权成功' if success else '授权失败'
        return HttpResponse(
            f"""
            <!doctype html>
            <html lang="zh-CN">
              <head><meta charset="utf-8"><title>{status_text}</title></head>
              <body style="font-family: Arial, sans-serif; padding: 32px;">
                <h2>{status_text}</h2>
                <p>{message}</p>
                <button onclick="window.close()">关闭窗口</button>
              </body>
            </html>
            """,
            status=200 if success else 400,
        )
    return HttpResponse(
        f"""
        <!doctype html>
        <html lang="zh-CN">
          <head><meta charset="utf-8"><title>仓库授权</title></head>
          <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h2>授权 {PLATFORM_BRAND_NAME} 读取仓库知识对象</h2>
            <p>仓库：{config.name}</p>
            <p>权限范围：只读读取代码、路由、接口、模型、文档，用于生成知识库 roadmap 和双链图谱。</p>
            <form method="post">
              <input type="hidden" name="state" value="{state or ''}" />
              <button type="submit" style="height: 36px; padding: 0 18px;">授权</button>
            </form>
          </body>
        </html>
        """
    )


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def github_oauth_callback(request):
    state = request.GET.get('state') or ''
    code = request.GET.get('code') or ''
    config = KnowledgeRepositoryConfig.objects.filter(authorization_state=state).first()
    if not config:
        return HttpResponse('授权 state 无效，请重新发起授权。', status=400)
    if not code:
        config.authorization_status = 'failed'
        config.authorization_message = 'GitHub 授权未返回 code。'
        config.save(update_fields=['authorization_status', 'authorization_message', 'updated_at'])
        return HttpResponse('GitHub 授权失败，未返回 code。', status=400)
    config.authorization_status = 'authorized'
    config.authorization_message = 'GitHub OAuth 已完成。请在仓库配置中保存 token 或接入服务端换 token 逻辑。'
    config.authorization_scopes = ['repo']
    config.save(update_fields=['authorization_status', 'authorization_message', 'authorization_scopes', 'updated_at'])
    return HttpResponse(
        '<!doctype html><meta charset="utf-8"><h2>GitHub 授权成功</h2><p>可以关闭窗口。</p><button onclick="window.close()">关闭窗口</button>'
    )
