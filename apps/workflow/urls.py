from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    WorkflowCatalogBootstrapView,
    WorkflowDefinitionViewSet,
    WorkflowDefinitionSimulationView,
    WorkflowEscalationRunView,
    WorkflowInstanceDetailView,
    WorkflowInstanceListView,
    WorkflowInstanceTerminateView,
    WorkflowMyTaskListView,
    WorkflowRuleViewSet,
    WorkflowStartView,
    WorkflowTaskActionView,
)


router = DefaultRouter()
router.register("definitions", WorkflowDefinitionViewSet, basename="workflow-definition")
router.register("rules", WorkflowRuleViewSet, basename="workflow-rule")


urlpatterns = [
    path("definitions/simulate/", WorkflowDefinitionSimulationView.as_view(), name="workflow-definition-simulate"),
]

urlpatterns += router.urls + [
    path("bootstrap/", WorkflowCatalogBootstrapView.as_view(), name="workflow-bootstrap"),
    path("instances/", WorkflowInstanceListView.as_view(), name="workflow-instance-list"),
    path("instances/<int:instance_id>/terminate/", WorkflowInstanceTerminateView.as_view(), name="workflow-instance-terminate"),
    path("tasks/my/", WorkflowMyTaskListView.as_view(), name="workflow-task-my"),
    path("tasks/<int:task_id>/action/", WorkflowTaskActionView.as_view(), name="workflow-task-action"),
    path("run-escalations/", WorkflowEscalationRunView.as_view(), name="workflow-run-escalations"),
    path("<str:biz_type>/<int:biz_id>/start/", WorkflowStartView.as_view(), name="workflow-start"),
    path("<str:biz_type>/<int:biz_id>/instance/", WorkflowInstanceDetailView.as_view(), name="workflow-instance-detail"),
]
