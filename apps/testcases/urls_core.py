from django.urls import path

from . import page_list_config_views, views


urlpatterns = [
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    path('manual-categories/', views.ManualTestCaseCategoryListCreateView.as_view(), name='manual-category-list'),
    path('manual-categories/import-xmind/', views.ManualTestCaseCategoryXMindImportView.as_view(), name='manual-category-import-xmind'),
    path('manual-categories/<int:pk>/', views.ManualTestCaseCategoryDetailView.as_view(), name='manual-category-detail'),
    path('manual-mindmaps/', views.ManualTestCaseMindmapListCreateView.as_view(), name='manual-mindmap-list'),
    path('manual-mindmaps/<int:pk>/', views.ManualTestCaseMindmapDetailView.as_view(), name='manual-mindmap-detail'),
    path('manual-mindmap-nodes/', views.ManualTestCaseNodeListView.as_view(), name='manual-mindmap-node-list'),
    path('dev-self-test/', views.DevSelfTestListView.as_view(), name='dev-self-test-list'),
    path('dev-self-test/detail/', views.DevSelfTestDetailView.as_view(), name='dev-self-test-detail'),
    path('dev-self-test/audit/', views.DevSelfTestAuditView.as_view(), name='dev-self-test-audit'),
    path(
        'manual-workspace-page-list-registry/',
        page_list_config_views.ManualWorkspacePageListRegistryView.as_view(),
        name='manual-workspace-page-list-registry',
    ),
    path(
        'manual-workspace-page-list-config/',
        page_list_config_views.ManualWorkspacePageListConfigView.as_view(),
        name='manual-workspace-page-list-config',
    ),
    path(
        'manual-workspace-page-list-config/restore-default/',
        page_list_config_views.ManualWorkspacePageListConfigRestoreView.as_view(),
        name='manual-workspace-page-list-config-restore-default',
    ),
]
