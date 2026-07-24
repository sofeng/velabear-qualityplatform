from django.db import models
from django.utils import timezone

from apps.projects.models import Project
from apps.testcases.models import TestCase
from apps.ui_automation.models import TestExecution, TestSuite, TestCase as UiAutomationTestCase, UiProject
from apps.users.models import User
from apps.versions.models import Version


class TestPlan(models.Model):
    """Manual test plan."""

    name = models.CharField(max_length=200, verbose_name="计划名称")
    description = models.TextField(blank=True, verbose_name="计划描述")
    projects = models.ManyToManyField(
        Project,
        blank=True,
        related_name="test_plans",
        verbose_name="关联项目",
    )
    version = models.ForeignKey(
        Version,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="test_plans",
        verbose_name="关联版本",
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_plans",
        verbose_name="创建者",
    )
    assignees = models.ManyToManyField(
        User,
        blank=True,
        related_name="assigned_plans",
        verbose_name="指派给",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "test_plans"
        verbose_name = "测试计划"
        verbose_name_plural = "测试计划"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class TestRun(models.Model):
    """Manual execution run generated from a test plan."""

    STATUS_CHOICES = [
        ("untested", "未测试"),
        ("in_progress", "进行中"),
        ("completed", "已完成"),
        ("blocked", "阻塞"),
    ]

    name = models.CharField(max_length=200, verbose_name="执行名称")
    description = models.TextField(blank=True, verbose_name="执行描述")
    test_plan = models.ForeignKey(
        TestPlan,
        on_delete=models.CASCADE,
        related_name="test_runs",
        verbose_name="测试计划",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="test_runs",
        verbose_name="关联项目",
    )
    version = models.ForeignKey(
        Version,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="test_runs",
        verbose_name="关联版本",
    )
    testcases = models.ManyToManyField(
        TestCase,
        through="TestRunCase",
        related_name="test_runs",
        verbose_name="测试用例",
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_runs",
        verbose_name="执行人",
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_runs",
        verbose_name="创建者",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="untested", verbose_name="状态")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="截止时间")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "test_runs"
        verbose_name = "测试执行"
        verbose_name_plural = "测试执行"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def progress_stats(self):
        total = self.run_cases.count()
        if total == 0:
            return {
                "total": 0,
                "untested": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "retest": 0,
                "tested": 0,
                "progress": 0,
            }

        stats = {
            "total": total,
            "untested": self.run_cases.filter(status="untested").count(),
            "passed": self.run_cases.filter(status="passed").count(),
            "failed": self.run_cases.filter(status="failed").count(),
            "blocked": self.run_cases.filter(status="blocked").count(),
            "retest": self.run_cases.filter(status="retest").count(),
        }
        stats["tested"] = stats["passed"] + stats["failed"] + stats["blocked"] + stats["retest"]
        stats["progress"] = round((stats["tested"] / total) * 100, 1) if total > 0 else 0
        return stats


class TestRunCase(models.Model):
    """Manual case inside a run."""

    STATUS_CHOICES = [
        ("untested", "未测试"),
        ("passed", "通过"),
        ("failed", "失败"),
        ("blocked", "阻塞"),
        ("retest", "重测"),
    ]

    PRIORITY_CHOICES = [
        ("low", "低"),
        ("medium", "中"),
        ("high", "高"),
        ("critical", "紧急"),
    ]

    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name="run_cases",
        verbose_name="测试执行",
    )
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, verbose_name="测试用例")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="untested", verbose_name="执行状态")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium", verbose_name="优先级")
    actual_result = models.TextField(blank=True, verbose_name="实际结果")
    comments = models.TextField(blank=True, verbose_name="备注")
    defects = models.JSONField(default=list, verbose_name="关联缺陷")
    elapsed_time = models.DurationField(null=True, blank=True, verbose_name="执行耗时")
    executed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="执行者",
    )
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name="执行时间")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "test_run_cases"
        unique_together = ["test_run", "testcase"]
        verbose_name = "测试执行用例"
        verbose_name_plural = "测试执行用例"
        ordering = ["testcase__id"]

    def __str__(self):
        return f"{self.test_run.name} - {self.testcase.title}"


class TestRunCaseHistory(models.Model):
    """Execution history for a manual run case."""

    run_case = models.ForeignKey(
        TestRunCase,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="执行用例",
    )
    status = models.CharField(max_length=20, choices=TestRunCase.STATUS_CHOICES, verbose_name="执行状态")
    actual_result = models.TextField(blank=True, verbose_name="实际结果")
    comments = models.TextField(blank=True, verbose_name="备注")
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="执行者")
    executed_at = models.DateTimeField(default=timezone.now, verbose_name="执行时间")

    class Meta:
        db_table = "test_run_case_history"
        verbose_name = "测试执行历史"
        verbose_name_plural = "测试执行历史"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.run_case_id} - {self.status}"


class TestRunUiAutomationBatch(models.Model):
    """Bridge record from a manual test run to generated UI automation cases."""

    STATUS_CHOICES = [
        ("draft", "未生成"),
        ("generating", "生成中"),
        ("pending_review", "待审核"),
        ("partially_approved", "部分已审核"),
        ("approved", "已审核"),
        ("running", "执行中"),
        ("completed", "已完成"),
        ("failed", "失败"),
    ]

    ENGINE_CHOICES = [
        ("playwright", "Playwright"),
        ("selenium", "Selenium"),
    ]

    test_run = models.OneToOneField(
        TestRun,
        on_delete=models.CASCADE,
        related_name="ui_automation_batch",
        verbose_name="测试执行",
    )
    target_ui_project = models.ForeignKey(
        UiProject,
        on_delete=models.CASCADE,
        related_name="execution_batches",
        verbose_name="目标 UI 项目",
    )
    generated_suite = models.ForeignKey(
        TestSuite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_batches",
        verbose_name="生成套件",
    )
    last_execution = models.ForeignKey(
        TestExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_batches",
        verbose_name="最近执行记录",
    )
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES, default="playwright", verbose_name="执行引擎")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", verbose_name="状态")
    generation_summary = models.JSONField(default=dict, blank=True, verbose_name="生成摘要")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_execution_batches",
        verbose_name="创建者",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_execution_batches",
        verbose_name="更新者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "test_run_ui_automation_batches"
        verbose_name = "执行 UI 自动化批次"
        verbose_name_plural = "执行 UI 自动化批次"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.test_run.name} -> {self.target_ui_project.name}"


class TestRunUiAutomationCandidate(models.Model):
    """Generated UI automation candidate for a manual run case."""

    REVIEW_STATUS_CHOICES = [
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已驳回"),
    ]

    GENERATION_SOURCE_CHOICES = [
        ("ai", "AI"),
        ("heuristic", "规则"),
    ]

    batch = models.ForeignKey(
        TestRunUiAutomationBatch,
        on_delete=models.CASCADE,
        related_name="candidates",
        verbose_name="批次",
    )
    run_case = models.OneToOneField(
        TestRunCase,
        on_delete=models.CASCADE,
        related_name="ui_automation_candidate",
        verbose_name="执行用例",
    )
    name = models.CharField(max_length=255, verbose_name="候选用例名称")
    description = models.TextField(blank=True, verbose_name="候选描述")
    preconditions = models.TextField(blank=True, verbose_name="前置条件")
    priority = models.CharField(max_length=10, default="medium", verbose_name="优先级")
    source_snapshot = models.JSONField(default=dict, blank=True, verbose_name="源用例快照")
    steps_data = models.JSONField(default=list, blank=True, verbose_name="候选步骤")
    step_count = models.PositiveIntegerField(default=0, verbose_name="步骤数")
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default="pending", verbose_name="审核状态")
    review_comment = models.TextField(blank=True, verbose_name="审核备注")
    generation_source = models.CharField(
        max_length=20,
        choices=GENERATION_SOURCE_CHOICES,
        default="ai",
        verbose_name="生成来源",
    )
    generation_error = models.TextField(blank=True, verbose_name="生成告警")
    generated_test_case = models.ForeignKey(
        UiAutomationTestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_candidates",
        verbose_name="落地 UI 用例",
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_execution_candidates",
        verbose_name="审核人",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "test_run_ui_automation_candidates"
        verbose_name = "执行 UI 自动化候选"
        verbose_name_plural = "执行 UI 自动化候选"
        ordering = ["run_case__id"]

    def __str__(self):
        return self.name


class TestCaseUiAutomationRecord(models.Model):
    """Bridge record from a manual testcase to a generated UI automation case."""

    STATUS_CHOICES = [
        ("draft", "未生成"),
        ("generating", "生成中"),
        ("pending_review", "待审核"),
        ("approved", "已审核"),
        ("rejected", "已驳回"),
        ("failed", "失败"),
    ]

    ENGINE_CHOICES = [
        ("playwright", "Playwright"),
        ("selenium", "Selenium"),
    ]

    GENERATION_SOURCE_CHOICES = [
        ("ai", "AI"),
        ("heuristic", "规则"),
    ]

    source_testcase = models.OneToOneField(
        TestCase,
        on_delete=models.CASCADE,
        related_name="ui_automation_record",
        verbose_name="源测试用例",
    )
    target_ui_project = models.ForeignKey(
        UiProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testcase_ui_automation_records",
        verbose_name="目标 UI 项目",
    )
    generated_test_case = models.ForeignKey(
        UiAutomationTestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testcase_ui_automation_records",
        verbose_name="落地 UI 用例",
    )
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES, default="playwright", verbose_name="执行引擎")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", verbose_name="状态")
    name = models.CharField(max_length=255, blank=True, default="", verbose_name="候选用例名称")
    description = models.TextField(blank=True, default="", verbose_name="候选描述")
    preconditions = models.TextField(blank=True, default="", verbose_name="前置条件")
    priority = models.CharField(max_length=10, default="medium", verbose_name="优先级")
    source_snapshot = models.JSONField(default=dict, blank=True, verbose_name="源用例快照")
    steps_data = models.JSONField(default=list, blank=True, verbose_name="候选步骤")
    step_count = models.PositiveIntegerField(default=0, verbose_name="步骤数")
    review_comment = models.TextField(blank=True, verbose_name="审核备注")
    generation_source = models.CharField(
        max_length=20,
        choices=GENERATION_SOURCE_CHOICES,
        default="ai",
        verbose_name="生成来源",
    )
    generation_error = models.TextField(blank=True, verbose_name="生成告警")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_testcase_ui_automation_records",
        verbose_name="审核人",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_testcase_ui_automation_records",
        verbose_name="创建者",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_testcase_ui_automation_records",
        verbose_name="更新者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "testcase_ui_automation_records"
        verbose_name = "测试用例 UI 自动化记录"
        verbose_name_plural = "测试用例 UI 自动化记录"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name or self.source_testcase.title
