from rest_framework import serializers
from django.db.models import Q

from apps.users.serializers import UserSimpleSerializer
from apps.ui_automation.models import UiProject

from .models import (
    TestPlan,
    TestRun,
    TestRunCase,
    TestRunCaseHistory,
    TestCaseUiAutomationRecord,
    TestRunUiAutomationBatch,
    TestRunUiAutomationCandidate,
)
from .services import ACTION_TYPE_CHOICES, ASSERT_TYPE_CHOICES


class TestRunCaseHistorySerializer(serializers.ModelSerializer):
    executed_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = TestRunCaseHistory
        fields = ("id", "status", "actual_result", "comments", "executed_by", "executed_at")


class TestRunCaseSimpleSerializer(serializers.ModelSerializer):
    testcase = serializers.StringRelatedField()
    testcase_id = serializers.IntegerField(source="testcase.id", read_only=True)
    executed_by_name = serializers.CharField(source="executed_by.username", read_only=True)

    class Meta:
        model = TestRunCase
        fields = (
            "id",
            "testcase_id",
            "testcase",
            "status",
            "priority",
            "comments",
            "actual_result",
            "executed_by_name",
            "executed_at",
        )


class TestRunCaseDetailSerializer(serializers.ModelSerializer):
    testcase = serializers.StringRelatedField()
    testcase_id = serializers.IntegerField(source="testcase.id", read_only=True)
    executed_by = UserSimpleSerializer(read_only=True)
    history = TestRunCaseHistorySerializer(many=True, read_only=True)

    class Meta:
        model = TestRunCase
        fields = (
            "id",
            "testcase_id",
            "testcase",
            "status",
            "priority",
            "actual_result",
            "comments",
            "defects",
            "elapsed_time",
            "executed_by",
            "executed_at",
            "created_at",
            "updated_at",
            "history",
        )


class UiAutomationCandidateStepSerializer(serializers.Serializer):
    step_number = serializers.IntegerField(required=False, min_value=1)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    action_type = serializers.ChoiceField(choices=sorted(ACTION_TYPE_CHOICES))
    element_id = serializers.IntegerField(required=False, allow_null=True)
    element_name = serializers.CharField(required=False, allow_blank=True, default="")
    input_value = serializers.CharField(required=False, allow_blank=True, default="")
    wait_time = serializers.IntegerField(required=False, min_value=0, default=1000)
    assert_type = serializers.ChoiceField(
        choices=sorted(ASSERT_TYPE_CHOICES),
        required=False,
        allow_blank=True,
        default="",
    )
    assert_value = serializers.CharField(required=False, allow_blank=True, default="")
    match_type = serializers.CharField(required=False, allow_blank=True, default="")
    match_score = serializers.FloatField(required=False, default=0)
    match_reason = serializers.CharField(required=False, allow_blank=True, default="")


class TestRunUiAutomationCandidateSerializer(serializers.ModelSerializer):
    source_testcase_id = serializers.IntegerField(source="run_case.testcase.id", read_only=True)
    source_testcase_title = serializers.CharField(source="run_case.testcase.title", read_only=True)
    generated_test_case_name = serializers.CharField(source="generated_test_case.name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True)
    steps_data = serializers.ListField(child=serializers.DictField(), required=False)

    class Meta:
        model = TestRunUiAutomationCandidate
        fields = (
            "id",
            "batch",
            "run_case",
            "source_testcase_id",
            "source_testcase_title",
            "name",
            "description",
            "preconditions",
            "priority",
            "source_snapshot",
            "steps_data",
            "step_count",
            "review_status",
            "review_comment",
            "generation_source",
            "generation_error",
            "generated_test_case",
            "generated_test_case_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "batch",
            "run_case",
            "source_testcase_id",
            "source_testcase_title",
            "step_count",
            "generation_source",
            "generation_error",
            "generated_test_case",
            "generated_test_case_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def validate_steps_data(self, value):
        step_serializer = UiAutomationCandidateStepSerializer(data=value, many=True)
        step_serializer.is_valid(raise_exception=True)
        validated_steps = sorted(
            step_serializer.validated_data,
            key=lambda item: item.get("step_number") or 10**6,
        )
        normalized = []
        for index, step in enumerate(validated_steps, start=1):
            normalized.append(
                {
                    "step_number": index,
                    "description": step.get("description", ""),
                    "action_type": step["action_type"],
                    "element_id": step.get("element_id"),
                    "element_name": step.get("element_name", ""),
                    "input_value": step.get("input_value", ""),
                    "wait_time": step.get("wait_time", 1000),
                    "assert_type": step.get("assert_type", ""),
                    "assert_value": step.get("assert_value", ""),
                    "match_type": step.get("match_type", ""),
                    "match_score": step.get("match_score", 0),
                    "match_reason": step.get("match_reason", ""),
                }
            )
        return normalized


class TestCaseUiAutomationRecordSerializer(serializers.ModelSerializer):
    source_testcase_title = serializers.CharField(source="source_testcase.title", read_only=True)
    source_project_id = serializers.IntegerField(source="source_testcase.project.id", read_only=True)
    source_project_name = serializers.CharField(source="source_testcase.project.name", read_only=True)
    generated_test_case_name = serializers.CharField(source="generated_test_case.name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.username", read_only=True)
    target_ui_project_name = serializers.CharField(source="target_ui_project.name", read_only=True)
    steps_data = serializers.ListField(child=serializers.DictField(), required=False)

    class Meta:
        model = TestCaseUiAutomationRecord
        fields = (
            "id",
            "source_testcase",
            "source_testcase_title",
            "source_project_id",
            "source_project_name",
            "target_ui_project",
            "target_ui_project_name",
            "generated_test_case",
            "generated_test_case_name",
            "engine",
            "status",
            "name",
            "description",
            "preconditions",
            "priority",
            "source_snapshot",
            "steps_data",
            "step_count",
            "review_comment",
            "generation_source",
            "generation_error",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "source_testcase",
            "source_testcase_title",
            "source_project_id",
            "source_project_name",
            "generated_test_case",
            "generated_test_case_name",
            "step_count",
            "generation_source",
            "generation_error",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        )

    def validate_steps_data(self, value):
        step_serializer = UiAutomationCandidateStepSerializer(data=value, many=True)
        step_serializer.is_valid(raise_exception=True)
        validated_steps = sorted(
            step_serializer.validated_data,
            key=lambda item: item.get("step_number") or 10**6,
        )
        normalized = []
        for index, step in enumerate(validated_steps, start=1):
            normalized.append(
                {
                    "step_number": index,
                    "description": step.get("description", ""),
                    "action_type": step["action_type"],
                    "element_id": step.get("element_id"),
                    "element_name": step.get("element_name", ""),
                    "input_value": step.get("input_value", ""),
                    "wait_time": step.get("wait_time", 1000),
                    "assert_type": step.get("assert_type", ""),
                    "assert_value": step.get("assert_value", ""),
                    "match_type": step.get("match_type", ""),
                    "match_score": step.get("match_score", 0),
                    "match_reason": step.get("match_reason", ""),
                }
            )
        return normalized

    def validate_target_ui_project(self, value):
        if value is None:
            return value

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            has_permission = UiProject.objects.filter(Q(owner=user) | Q(members=user), id=value.id).distinct().exists()
            if not has_permission:
                raise serializers.ValidationError("请选择有权限访问的 UI 自动化项目")

        source_testcase = getattr(self.instance, "source_testcase", None)
        source_project_name = (getattr(getattr(source_testcase, "project", None), "name", "") or "").strip().casefold()
        target_project_name = (getattr(value, "name", "") or "").strip().casefold()
        if source_project_name and target_project_name and source_project_name != target_project_name:
            raise serializers.ValidationError("目标 UI 项目需与源测试用例所属项目同名")

        return value


class TestRunUiAutomationBatchSerializer(serializers.ModelSerializer):
    target_ui_project_name = serializers.CharField(source="target_ui_project.name", read_only=True)
    generated_suite_name = serializers.CharField(source="generated_suite.name", read_only=True)
    last_execution_status = serializers.CharField(source="last_execution.status", read_only=True)
    last_execution_id = serializers.IntegerField(source="last_execution.id", read_only=True)
    last_execution_created_at = serializers.DateTimeField(source="last_execution.created_at", read_only=True)
    candidates = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta:
        model = TestRunUiAutomationBatch
        fields = (
            "id",
            "test_run",
            "target_ui_project",
            "target_ui_project_name",
            "generated_suite",
            "generated_suite_name",
            "last_execution",
            "last_execution_id",
            "last_execution_status",
            "last_execution_created_at",
            "engine",
            "status",
            "generation_summary",
            "counts",
            "candidates",
            "created_at",
            "updated_at",
        )

    def get_counts(self, obj):
        queryset = obj.candidates.all()
        return {
            "total": queryset.count(),
            "pending": queryset.filter(review_status="pending").count(),
            "approved": queryset.filter(review_status="approved").count(),
            "rejected": queryset.filter(review_status="rejected").count(),
            "warnings": queryset.exclude(generation_error="").count(),
        }

    def get_candidates(self, obj):
        queryset = obj.candidates.select_related("run_case__testcase", "generated_test_case", "reviewed_by").order_by("run_case__id")
        return TestRunUiAutomationCandidateSerializer(queryset, many=True).data


class TestRunSerializer(serializers.ModelSerializer):
    run_cases = TestRunCaseSimpleSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.name", read_only=True)
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    ui_automation_batch = TestRunUiAutomationBatchSerializer(read_only=True)

    class Meta:
        model = TestRun
        fields = (
            "id",
            "name",
            "description",
            "status",
            "project",
            "project_name",
            "assignee",
            "assignee_name",
            "progress",
            "run_cases",
            "ui_automation_batch",
        )

    def get_progress(self, obj):
        return obj.progress_stats


class TestPlanSerializer(serializers.ModelSerializer):
    creator = UserSimpleSerializer(read_only=True)
    projects = serializers.StringRelatedField(many=True, read_only=True)
    version = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TestPlan
        fields = ("id", "name", "projects", "version", "creator", "created_at", "is_active")


class TestPlanDetailSerializer(serializers.ModelSerializer):
    test_runs = TestRunSerializer(many=True, read_only=True)
    creator = UserSimpleSerializer(read_only=True)
    projects = serializers.StringRelatedField(many=True, read_only=True)
    version = serializers.StringRelatedField(read_only=True)
    assignees = UserSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = TestPlan
        fields = (
            "id",
            "name",
            "description",
            "projects",
            "version",
            "creator",
            "assignees",
            "is_active",
            "created_at",
            "updated_at",
            "test_runs",
        )


class TestRunCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRunCase
        fields = "__all__"
