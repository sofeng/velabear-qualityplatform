from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    JiraBugRecordViewSet,
    JiraInterfaceConfigViewSet,
    JiraRequirementInterfaceConfigViewSet,
    JiraRequirementRecordViewSet,
    QualityAnalysisSettingsView,
    QualityReportViewSet,
    shared_live_report_version_analysis,
    shared_report_chart,
    shared_report_detail,
)


router = DefaultRouter()
router.register(r'reports', QualityReportViewSet, basename='quality-report')
router.register(r'jira-configs', JiraInterfaceConfigViewSet, basename='jira-interface-config')
router.register(r'jira-bug-records', JiraBugRecordViewSet, basename='jira-bug-record')
router.register(r'jira-requirement-configs', JiraRequirementInterfaceConfigViewSet, basename='jira-requirement-interface-config')
router.register(r'jira-requirement-records', JiraRequirementRecordViewSet, basename='jira-requirement-record')


urlpatterns = [
    path('', include(router.urls)),
    path('settings/', QualityAnalysisSettingsView.as_view(), name='quality-analysis-settings'),
    path('share/live/<slug:share_token>/version-analysis/', shared_live_report_version_analysis, name='quality-share-live-version-analysis'),
    path('share/<slug:share_token>/', shared_report_detail, name='quality-share-detail'),
    path('share/<slug:share_token>/charts/<slug:chart_name>/', shared_report_chart, name='quality-share-chart'),
]
