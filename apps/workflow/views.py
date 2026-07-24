from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WorkflowDefinition, WorkflowInstance, WorkflowRule
from .serializers import (
    WorkflowDefinitionSerializer,
    WorkflowDefinitionSimulationSerializer,
    WorkflowInstanceSerializer,
    WorkflowInstanceTerminateSerializer,
    WorkflowRuleSerializer,
    WorkflowTaskActionSerializer,
    WorkflowTaskListSerializer,
)
from .services import (
    bootstrap_workflow_catalog,
    execute_task_action,
    filter_instance_queryset_for_user,
    get_business_object_if_accessible,
    get_workflow_definition_versions,
    get_user_open_tasks,
    get_workflow_summary,
    process_overdue_tasks,
    publish_workflow_definition_version,
    restore_workflow_definition_version,
    simulate_workflow_definition,
    start_workflow,
    terminate_workflow_instance,
)


class WorkflowAdminWritePermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class WorkflowDefinitionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = WorkflowDefinition.objects.filter(is_active=True).order_by("biz_type", "key", "-version")
    serializer_class = WorkflowDefinitionSerializer
    permission_classes = [WorkflowAdminWritePermission]
    pagination_class = None

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        published = publish_workflow_definition_version(instance.id, serializer.validated_data, request.user)
        response_serializer = self.get_serializer(published)
        return Response(response_serializer.data)

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        try:
            payload = get_workflow_definition_versions(pk)
        except WorkflowDefinition.DoesNotExist:
            return Response({"detail": "Workflow definition not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"results": payload})

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        try:
            restored = restore_workflow_definition_version(pk, request.user)
        except WorkflowDefinition.DoesNotExist:
            return Response({"detail": "Workflow definition not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(restored).data, status=status.HTTP_201_CREATED)


class WorkflowPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class WorkflowRuleViewSet(viewsets.ModelViewSet):
    queryset = WorkflowRule.objects.all().order_by("biz_type", "scene_key", "step_key", "priority", "id")
    serializer_class = WorkflowRuleSerializer
    permission_classes = [WorkflowAdminWritePermission]
    pagination_class = WorkflowPagination

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class WorkflowStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, biz_type, biz_id):
        try:
            obj = get_business_object_if_accessible(request.user, biz_type, biz_id)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        if not obj:
            return Response({"detail": "Business object not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            instance = start_workflow(biz_type, biz_id, request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        payload = get_workflow_summary(biz_type, biz_id, user=request.user)
        return Response({"instance_id": instance.id, "workflow": payload}, status=status.HTTP_201_CREATED)


class WorkflowInstanceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, biz_type, biz_id):
        try:
            obj = get_business_object_if_accessible(request.user, biz_type, biz_id)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        if not obj:
            return Response({"detail": "Business object not found"}, status=status.HTTP_404_NOT_FOUND)

        payload = get_workflow_summary(biz_type, biz_id, user=request.user)
        if not payload:
            return Response({"detail": "Workflow not started"}, status=status.HTTP_404_NOT_FOUND)
        return Response(payload)


class WorkflowInstanceTerminateView(APIView):
    permission_classes = [WorkflowAdminWritePermission]

    def post(self, request, instance_id):
        serializer = WorkflowInstanceTerminateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = terminate_workflow_instance(
                instance_id=instance_id,
                operator=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except WorkflowInstance.DoesNotExist:
            return Response({"detail": "Workflow instance not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(get_workflow_summary(instance.biz_type, instance.biz_id, user=request.user))


class WorkflowMyTaskListView(generics.ListAPIView):
    serializer_class = WorkflowTaskListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = WorkflowPagination

    def get_queryset(self):
        biz_type = self.request.query_params.get("biz_type") or None
        return get_user_open_tasks(self.request.user, biz_type=biz_type)


class WorkflowTaskActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id):
        serializer = WorkflowTaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = execute_task_action(
                task_id=task_id,
                action=serializer.validated_data["action"],
                operator=request.user,
                comment=serializer.validated_data.get("comment", ""),
                assignee_id=serializer.validated_data.get("assignee_id"),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(get_workflow_summary(instance.biz_type, instance.biz_id, user=request.user))


class WorkflowEscalationRunView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        result = process_overdue_tasks()
        return Response(result)


class WorkflowCatalogBootstrapView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        definitions = bootstrap_workflow_catalog(operator=request.user)
        serializer = WorkflowDefinitionSerializer(definitions, many=True)
        return Response({"definitions": serializer.data})


class WorkflowDefinitionSimulationView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = WorkflowDefinitionSimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = simulate_workflow_definition(
                serializer.validated_data["definition_id"],
                inputs=serializer.validated_data.get("inputs") or {},
            )
        except WorkflowDefinition.DoesNotExist:
            return Response({"detail": "Workflow definition not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class WorkflowInstanceListView(generics.ListAPIView):
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = WorkflowPagination

    def get_queryset(self):
        queryset = WorkflowInstance.objects.select_related("definition", "current_assignee").order_by("-started_at", "-id")
        biz_type = self.request.query_params.get("biz_type")
        status_value = self.request.query_params.get("status")
        if biz_type:
            queryset = queryset.filter(biz_type=biz_type)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return filter_instance_queryset_for_user(queryset, self.request.user)
