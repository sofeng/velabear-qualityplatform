from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.projects.models import Project
from apps.testcases.models import TestCase
from apps.ui_automation.models import UiProject

from .models import (
    TestCaseUiAutomationRecord,
    TestPlan,
    TestRun,
    TestRunCase,
    TestRunCaseHistory,
    TestRunUiAutomationCandidate,
)
from .serializers import (
    TestCaseUiAutomationRecordSerializer,
    TestPlanDetailSerializer,
    TestPlanSerializer,
    TestRunCaseDetailSerializer,
    TestRunCaseHistorySerializer,
    TestRunCaseSerializer,
    TestRunSerializer,
    TestRunUiAutomationCandidateSerializer,
)
from .services import TestCaseUiAutomationService, TestRunUiAutomationService


def get_accessible_ui_projects(user):
    return UiProject.objects.filter(Q(owner=user) | Q(members=user)).distinct()


def get_accessible_testcases(user):
    accessible_projects = Project.objects.filter(Q(owner=user) | Q(members=user)).distinct()
    return TestCase.objects.filter(project__in=accessible_projects)


class TestPlanViewSet(viewsets.ModelViewSet):
    queryset = TestPlan.objects.all().order_by("-created_at")
    serializer_class = TestPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        candidate_queryset = TestRunUiAutomationCandidate.objects.select_related(
            "run_case__testcase",
            "generated_test_case",
            "reviewed_by",
        ).order_by("run_case__id")
        batch_prefetch = Prefetch(
            "ui_automation_batch__candidates",
            queryset=candidate_queryset,
        )
        run_queryset = (
            TestRun.objects.select_related(
                "project",
                "assignee",
                "ui_automation_batch__target_ui_project",
                "ui_automation_batch__generated_suite",
                "ui_automation_batch__last_execution",
            )
            .prefetch_related(
                Prefetch(
                    "run_cases",
                    queryset=TestRunCase.objects.select_related("testcase", "executed_by").order_by("testcase__id"),
                ),
                batch_prefetch,
            )
            .order_by("-created_at")
        )
        return (
            TestPlan.objects.select_related("creator", "version")
            .prefetch_related("projects", Prefetch("test_runs", queryset=run_queryset))
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TestPlanDetailSerializer
        return TestPlanSerializer

    def perform_create(self, serializer):
        version = None
        version_id = self.request.data.get("version")
        if version_id:
            from apps.versions.models import Version

            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                version = None

        test_plan = serializer.save(creator=self.request.user, version=version)

        project_ids = self.request.data.get("projects", [])
        testcase_ids = self.request.data.get("testcases", [])
        if not project_ids:
            return

        test_plan.projects.set(project_ids)
        for project_id in project_ids:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                continue

            test_run = TestRun.objects.create(
                name=f"{test_plan.name} - {project.name} Execution",
                test_plan=test_plan,
                project=project,
                version=test_plan.version,
                creator=test_plan.creator,
                assignee=test_plan.creator,
            )

            if testcase_ids:
                test_run_cases = []
                for case_id in testcase_ids:
                    try:
                        testcase = TestCase.objects.get(id=case_id)
                    except TestCase.DoesNotExist:
                        continue
                    test_run_cases.append(TestRunCase(test_run=test_run, testcase=testcase))
                TestRunCase.objects.bulk_create(test_run_cases)
                test_run.testcases.set(testcase_ids)

    def perform_update(self, serializer):
        version = None
        version_id = self.request.data.get("version")
        if version_id:
            from apps.versions.models import Version

            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                version = None

        test_plan = serializer.save(version=version)

        project_ids = self.request.data.get("projects")
        if project_ids is not None:
            test_plan.projects.set(project_ids)

        assignee_ids = self.request.data.get("assignees")
        if assignee_ids is not None:
            test_plan.assignees.set(assignee_ids)

    @action(detail=False, methods=["get"])
    def testcases_by_projects(self, request):
        project_ids = request.query_params.getlist("project_ids")
        if not project_ids:
            return Response(
                {"error": "请先选择项目", "detail": "请选择项目后再加载测试用例"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project_ids = [int(project_id) for project_id in project_ids if project_id and str(project_id).isdigit()]
        except ValueError:
            project_ids = []

        if not project_ids:
            return Response(
                {"error": "无效的项目 ID", "detail": "请提供有效的项目 ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        testcases = TestCase.objects.filter(project_id__in=project_ids, status__in=["draft", "active"]).values(
            "id",
            "title",
            "priority",
            "test_type",
            "project__name",
        )
        return Response({"results": list(testcases)})


class TestRunViewSet(viewsets.ModelViewSet):
    queryset = TestRun.objects.all().order_by("-created_at")
    serializer_class = TestRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            TestRun.objects.select_related(
                "test_plan",
                "project",
                "assignee",
                "ui_automation_batch__target_ui_project",
                "ui_automation_batch__generated_suite",
                "ui_automation_batch__last_execution",
            )
            .prefetch_related(
                Prefetch(
                    "run_cases",
                    queryset=TestRunCase.objects.select_related("testcase", "executed_by").order_by("testcase__id"),
                ),
                Prefetch(
                    "ui_automation_batch__candidates",
                    queryset=TestRunUiAutomationCandidate.objects.select_related(
                        "run_case__testcase",
                        "generated_test_case",
                        "reviewed_by",
                    ).order_by("run_case__id"),
                ),
            )
            .order_by("-created_at")
        )

    @action(detail=True, methods=["post"])
    def generate_ui_automation(self, request, pk=None):
        test_run = self.get_object()
        target_ui_project_id = request.data.get("target_ui_project")
        engine = request.data.get("engine", "playwright")

        if target_ui_project_id:
            target_ui_project = get_accessible_ui_projects(request.user).filter(id=target_ui_project_id).first()
        else:
            target_ui_project = TestRunUiAutomationService.auto_match_ui_project(test_run)
            if target_ui_project and not get_accessible_ui_projects(request.user).filter(id=target_ui_project.id).exists():
                target_ui_project = None

        if target_ui_project is None:
            return Response(
                {"error": "请选择目标 UI 项目", "detail": "当前执行无法自动匹配可访问的 UI 自动化项目"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch = TestRunUiAutomationService.generate_candidates(
            test_run=test_run,
            target_ui_project=target_ui_project,
            engine=engine,
            user=request.user,
        )
        return Response(TestRunSerializer(test_run, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def execute_ui_automation(self, request, pk=None):
        test_run = self.get_object()
        batch = getattr(test_run, "ui_automation_batch", None)
        if batch is None:
            return Response(
                {"error": "当前执行还没有生成 UI 自动化候选用例"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        browser = request.data.get("browser", "chrome")
        headless = request.data.get("headless", True)
        try:
            result = TestRunUiAutomationService.execute_batch(
                batch=batch,
                user=request.user,
                browser=browser,
                headless=headless,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class TestCaseUiAutomationRecordViewSet(viewsets.ModelViewSet):
    queryset = TestCaseUiAutomationRecord.objects.all().order_by("-updated_at")
    serializer_class = TestCaseUiAutomationRecordSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options", "post"]

    def get_queryset(self):
        queryset = (
            TestCaseUiAutomationRecord.objects.select_related(
                "source_testcase",
                "source_testcase__project",
                "target_ui_project",
                "generated_test_case",
                "reviewed_by",
            )
            .filter(source_testcase__in=get_accessible_testcases(self.request.user))
            .order_by("-updated_at")
        )

        source_project = self.request.query_params.get("source_project")
        if source_project:
            queryset = queryset.filter(source_testcase__project_id=source_project)

        source_testcase = self.request.query_params.get("source_testcase")
        if source_testcase:
            queryset = queryset.filter(source_testcase_id=source_testcase)

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        target_ui_project = self.request.query_params.get("target_ui_project")
        if target_ui_project:
            queryset = queryset.filter(target_ui_project_id=target_ui_project)

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(source_testcase__title__icontains=search)
                | Q(name__icontains=search)
                | Q(generated_test_case__name__icontains=search)
            )

        return queryset

    def partial_update(self, request, *args, **kwargs):
        record = self.get_object()
        was_approved = record.status == "approved"
        serializer = self.get_serializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        record = serializer.save(step_count=len(serializer.validated_data.get("steps_data", record.steps_data)))

        editable_fields = {"name", "description", "preconditions", "priority", "steps_data", "target_ui_project"}
        if was_approved and editable_fields.intersection(serializer.validated_data.keys()):
            record = TestCaseUiAutomationService.mark_record_pending_if_needed(record)

        return Response(self.get_serializer(record).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        queryset = self.get_queryset()
        return Response(
            {
                "total": queryset.count(),
                "pending_review": queryset.filter(status="pending_review").count(),
                "approved": queryset.filter(status="approved").count(),
                "rejected": queryset.filter(status="rejected").count(),
                "warnings": queryset.exclude(generation_error="").count(),
                "generated": queryset.exclude(generated_test_case__isnull=True).count(),
            }
        )

    @action(detail=False, methods=["get"])
    def by_testcase(self, request):
        testcase_id = request.query_params.get("source_testcase")
        if not testcase_id:
            return Response({"record": None})

        testcase = get_accessible_testcases(request.user).filter(id=testcase_id).first()
        if testcase is None:
            return Response({"error": "测试用例不存在或无权限访问"}, status=status.HTTP_404_NOT_FOUND)

        record = self.get_queryset().filter(source_testcase_id=testcase.id).first()
        if record is None:
            return Response({"record": None})
        return Response(self.get_serializer(record).data)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        source_testcase_id = request.data.get("source_testcase")
        target_ui_project_id = request.data.get("target_ui_project")
        engine = request.data.get("engine", "playwright")

        if not source_testcase_id:
            return Response({"error": "请先选择测试用例"}, status=status.HTTP_400_BAD_REQUEST)

        source_testcase = (
            get_accessible_testcases(request.user)
            .prefetch_related("step_details")
            .filter(id=source_testcase_id)
            .first()
        )
        if source_testcase is None:
            return Response({"error": "测试用例不存在或无权限访问"}, status=status.HTTP_404_NOT_FOUND)

        if target_ui_project_id:
            target_ui_project = get_accessible_ui_projects(request.user).filter(id=target_ui_project_id).first()
        else:
            target_ui_project = TestCaseUiAutomationService.auto_match_ui_project(source_testcase)
            if target_ui_project and not get_accessible_ui_projects(request.user).filter(id=target_ui_project.id).exists():
                target_ui_project = None

        if target_ui_project is None:
            return Response(
                {"error": "请选择目标 UI 项目", "detail": "当前测试用例无法自动匹配可访问的 UI 自动化项目"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            record = TestCaseUiAutomationService.generate_record(
                source_testcase=source_testcase,
                target_ui_project=target_ui_project,
                engine=engine,
                user=request.user,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = self.get_object()
        if request.data:
            serializer = self.get_serializer(record, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            record = serializer.save(step_count=len(serializer.validated_data.get("steps_data", record.steps_data)))

        try:
            record = TestCaseUiAutomationService.approve_record(record, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(record).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        record = self.get_object()
        review_comment = request.data.get("review_comment", "")
        record = TestCaseUiAutomationService.reject_record(record, request.user, review_comment)
        return Response(self.get_serializer(record).data)


class TestRunCaseViewSet(viewsets.ModelViewSet):
    queryset = TestRunCase.objects.all()
    serializer_class = TestRunCaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TestRunCase.objects.select_related("testcase", "test_run", "executed_by").prefetch_related("history")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TestRunCaseDetailSerializer
        return TestRunCaseSerializer

    @action(detail=True, methods=["patch"])
    def update_status(self, request, pk=None):
        run_case = self.get_object()
        new_status = request.data.get("status")
        actual_result = request.data.get("actual_result", "")
        comments = request.data.get("comments", "")

        if not new_status:
            return Response({"error": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)

        TestRunCaseHistory.objects.create(
            run_case=run_case,
            status=new_status,
            actual_result=actual_result,
            comments=comments,
            executed_by=request.user,
            executed_at=timezone.now(),
        )

        run_case.status = new_status
        run_case.actual_result = actual_result
        run_case.comments = comments
        run_case.executed_by = request.user
        run_case.executed_at = timezone.now()
        run_case.save()

        return Response(TestRunCaseDetailSerializer(run_case).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        run_case = self.get_object()
        history = run_case.history.all().order_by("-executed_at")
        serializer = TestRunCaseHistorySerializer(history, many=True)
        return Response(serializer.data)


class TestRunUiAutomationCandidateViewSet(viewsets.ModelViewSet):
    queryset = TestRunUiAutomationCandidate.objects.all()
    serializer_class = TestRunUiAutomationCandidateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options", "post"]

    def get_queryset(self):
        return TestRunUiAutomationCandidate.objects.select_related(
            "batch",
            "batch__target_ui_project",
            "run_case",
            "run_case__testcase",
            "generated_test_case",
            "reviewed_by",
        ).order_by("run_case__id")

    def partial_update(self, request, *args, **kwargs):
        candidate = self.get_object()
        was_approved = candidate.review_status == "approved"
        serializer = self.get_serializer(candidate, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save(step_count=len(serializer.validated_data.get("steps_data", candidate.steps_data)))

        editable_fields = {"name", "description", "preconditions", "priority", "steps_data"}
        if was_approved and editable_fields.intersection(serializer.validated_data.keys()):
            candidate = TestRunUiAutomationService.mark_candidate_pending_if_needed(candidate)

        return Response(self.get_serializer(candidate).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        candidate = self.get_object()
        if request.data:
            serializer = self.get_serializer(candidate, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            candidate = serializer.save(step_count=len(serializer.validated_data.get("steps_data", candidate.steps_data)))

        try:
            candidate = TestRunUiAutomationService.approve_candidate(candidate, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(candidate).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        candidate = self.get_object()
        review_comment = request.data.get("review_comment", "")
        candidate = TestRunUiAutomationService.reject_candidate(candidate, request.user, review_comment)
        return Response(self.get_serializer(candidate).data)


class TestRunCaseHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TestRunCaseHistory.objects.all().order_by("-executed_at")
    serializer_class = TestRunCaseHistorySerializer
    permission_classes = [IsAuthenticated]
