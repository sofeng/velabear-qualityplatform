from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TestPlanViewSet,
    TestCaseUiAutomationRecordViewSet,
    TestRunCaseHistoryViewSet,
    TestRunCaseViewSet,
    TestRunUiAutomationCandidateViewSet,
    TestRunViewSet,
)

router = DefaultRouter()
router.register(r"plans", TestPlanViewSet, basename="execution-plan")
router.register(r"runs", TestRunViewSet, basename="execution-run")
router.register(r"run_cases", TestRunCaseViewSet, basename="execution-run-case")
router.register(r"ui_automation_candidates", TestRunUiAutomationCandidateViewSet, basename="execution-ui-candidate")
router.register(r"testcase_ui_automation_records", TestCaseUiAutomationRecordViewSet, basename="testcase-ui-record")
router.register(r"history", TestRunCaseHistoryViewSet, basename="execution-history")

urlpatterns = [
    path("", include(router.urls)),
]
