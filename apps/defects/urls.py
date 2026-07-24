from django.urls import path

from . import notification_views, views


urlpatterns = [
    path('', views.DefectListCreateView.as_view(), name='defect-list'),
    path('version-analysis/', views.DefectVersionAnalysisView.as_view(), name='defect-version-analysis'),
    path('import-excel/', views.DefectExcelImportView.as_view(), name='defect-import-excel'),
    path('wiki-directories/', views.WikiDirectoryListCreateView.as_view(), name='wiki-directory-list'),
    path('wiki-directories/<int:pk>/', views.WikiDirectoryDetailView.as_view(), name='wiki-directory-detail'),
    path('wiki-pages/', views.WikiPageListCreateView.as_view(), name='wiki-page-list'),
    path('wiki-pages/<int:pk>/', views.WikiPageDetailView.as_view(), name='wiki-page-detail'),
    path(
        'technical-solution-designs/',
        views.TechnicalSolutionDesignListCreateView.as_view(),
        name='technical-solution-design-list',
    ),
    path(
        'technical-solution-designs/import-excel/',
        views.TechnicalSolutionDesignExcelImportView.as_view(),
        name='technical-solution-design-import-excel',
    ),
    path(
        'technical-solution-designs/<int:pk>/',
        views.TechnicalSolutionDesignDetailView.as_view(),
        name='technical-solution-design-detail',
    ),
    path(
        'technical-solution-designs/<int:pk>/status/',
        views.TechnicalSolutionDesignStatusUpdateView.as_view(),
        name='technical-solution-design-status-update',
    ),
    path(
        'technical-solution-designs/<int:pk>/assignees/',
        views.TechnicalSolutionDesignAssigneeUpdateView.as_view(),
        name='technical-solution-design-assignee-update',
    ),
    path(
        'technical-solution-designs/<int:pk>/comments/',
        views.TechnicalSolutionDesignCommentCreateView.as_view(),
        name='technical-solution-design-comment-create',
    ),
    path(
        'technical-solution-designs/<int:pk>/comments/<int:comment_pk>/',
        views.TechnicalSolutionDesignCommentDetailView.as_view(),
        name='technical-solution-design-comment-detail',
    ),
    path(
        'technical-solution-designs/<int:pk>/history/',
        views.TechnicalSolutionDesignHistoryListView.as_view(),
        name='technical-solution-design-history-list',
    ),
    path('email-config/', notification_views.DefectEmailConfigView.as_view(), name='defect-email-config'),
    path(
        'email-config/test-send/',
        notification_views.DefectEmailConfigTestSendView.as_view(),
        name='defect-email-config-test-send',
    ),
    path(
        'email-config/verify-smtp/',
        notification_views.DefectEmailConfigVerifySMTPView.as_view(),
        name='defect-email-config-verify-smtp',
    ),
    path(
        'notification-settings/',
        notification_views.DefectNotificationSettingsView.as_view(),
        name='defect-notification-settings',
    ),
    path(
        'notifications/stream/',
        notification_views.DefectNotificationStreamView.as_view(),
        name='defect-notification-stream',
    ),
    path('rich-text-images/', views.DefectRichTextImageUploadView.as_view(), name='defect-rich-text-image-upload'),
    path('<int:pk>/', views.DefectDetailView.as_view(), name='defect-detail'),
    path('<int:pk>/status/', views.DefectStatusUpdateView.as_view(), name='defect-status-update'),
    path('<int:pk>/assignees/', views.DefectAssigneeUpdateView.as_view(), name='defect-assignee-update'),
    path('<int:pk>/comments/', views.DefectCommentCreateView.as_view(), name='defect-comment-create'),
    path('<int:pk>/comments/<int:comment_pk>/', views.DefectCommentDetailView.as_view(), name='defect-comment-detail'),
    path('<int:pk>/history/', views.DefectHistoryListView.as_view(), name='defect-history-list'),
]
