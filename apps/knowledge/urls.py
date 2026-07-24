from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    KnowledgeAssetInsightView,
    KnowledgeFeedbackViewSet,
    KnowledgeGraphView,
    KnowledgeIndexRunViewSet,
    KnowledgeObjectViewSet,
    KnowledgeQueryContextView,
    KnowledgeQueryTraceViewSet,
    KnowledgeRelationViewSet,
    KnowledgeRepositoryConfigViewSet,
    KnowledgeSpaceViewSet,
    ProjectKnowledgeEnableView,
    ProjectKnowledgeStatusView,
    github_oauth_callback,
    local_authorization_confirm,
)


router = DefaultRouter()
router.register(r'spaces', KnowledgeSpaceViewSet, basename='knowledge-space')
router.register(r'repository-configs', KnowledgeRepositoryConfigViewSet, basename='knowledge-repository-config')
router.register(r'index-runs', KnowledgeIndexRunViewSet, basename='knowledge-index-run')
router.register(r'objects', KnowledgeObjectViewSet, basename='knowledge-object')
router.register(r'relations', KnowledgeRelationViewSet, basename='knowledge-relation')
router.register(r'query-traces', KnowledgeQueryTraceViewSet, basename='knowledge-query-trace')
router.register(r'feedback', KnowledgeFeedbackViewSet, basename='knowledge-feedback')

urlpatterns = [
    path('', include(router.urls)),
    path('graph/', KnowledgeGraphView.as_view(), name='knowledge-graph'),
    path('asset-insight/', KnowledgeAssetInsightView.as_view(), name='knowledge-asset-insight'),
    path('query-context/', KnowledgeQueryContextView.as_view(), name='knowledge-query-context'),
    path('project-knowledge/status/', ProjectKnowledgeStatusView.as_view(), name='project-knowledge-status'),
    path('project-knowledge/enable/', ProjectKnowledgeEnableView.as_view(), name='project-knowledge-enable'),
    path('authorization/<int:pk>/confirm/', local_authorization_confirm, name='knowledge-local-authorization-confirm'),
    path('oauth/github/callback/', github_oauth_callback, name='knowledge-github-oauth-callback'),
]
