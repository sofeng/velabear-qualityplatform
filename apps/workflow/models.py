from django.db import models
from django.utils import timezone

from apps.users.models import User


class WorkflowDefinition(models.Model):
    BIZ_TYPE_CHOICES = [
        ("defect", "Defect"),
        ("requirement", "Requirement"),
    ]

    biz_type = models.CharField(max_length=32, choices=BIZ_TYPE_CHOICES)
    key = models.CharField(max_length=100)
    scene_key = models.CharField(max_length=100, default="default")
    name = models.CharField(max_length=200)
    version = models.PositiveIntegerField(default=1)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_definitions_created",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_definitions"
        ordering = ["biz_type", "key", "-version", "-id"]
        unique_together = [("biz_type", "key", "version")]

    def __str__(self):
        return f"{self.biz_type}:{self.key}:v{self.version}"


class WorkflowRule(models.Model):
    biz_type = models.CharField(max_length=32, choices=WorkflowDefinition.BIZ_TYPE_CHOICES)
    scene_key = models.CharField(max_length=100, default="default")
    step_key = models.CharField(max_length=100, default="*")
    name = models.CharField(max_length=200)
    priority = models.PositiveIntegerField(default=100)
    conditions = models.JSONField(default=dict, blank=True)
    outputs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_rules_created",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_rules"
        ordering = ["biz_type", "scene_key", "step_key", "priority", "id"]

    def __str__(self):
        return f"{self.biz_type}:{self.step_key}:{self.name}"


class WorkflowInstance(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("completed", "Completed"),
        ("terminated", "Terminated"),
    ]

    definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    biz_type = models.CharField(max_length=32, choices=WorkflowDefinition.BIZ_TYPE_CHOICES)
    biz_id = models.PositiveIntegerField()
    biz_code = models.CharField(max_length=100, blank=True)
    biz_title = models.CharField(max_length=255, blank=True)
    business_key = models.CharField(max_length=150)
    run_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    current_step_key = models.CharField(max_length=100, blank=True)
    current_step_name = models.CharField(max_length=200, blank=True)
    current_task_id = models.PositiveBigIntegerField(null=True, blank=True)
    current_assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_instances_assigned",
    )
    scene_key = models.CharField(max_length=100, default="default")
    variables = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_instances_started",
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_instances"
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["biz_type", "biz_id"]),
            models.Index(fields=["biz_type", "biz_id", "run_number"]),
            models.Index(fields=["business_key"]),
            models.Index(fields=["status"]),
            models.Index(fields=["current_step_key"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["biz_type", "biz_id", "run_number"], name="workflow_instance_run_unique"),
        ]

    def __str__(self):
        return f"{self.business_key}#run{self.run_number}"


class WorkflowTask(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    step_key = models.CharField(max_length=100)
    step_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks_assigned",
    )
    candidate_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="workflow_tasks_candidate",
    )
    candidate_groups = models.JSONField(default=list, blank=True)
    available_actions = models.JSONField(default=list, blank=True)
    sla_hours = models.PositiveIntegerField(null=True, blank=True)
    remind_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    escalation_due_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_tasks_completed",
    )

    class Meta:
        db_table = "workflow_tasks"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["step_key"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self):
        return f"{self.instance.business_key}:{self.step_key}"


class WorkflowActionLog(models.Model):
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    task = models.ForeignKey(
        WorkflowTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="action_logs",
    )
    biz_type = models.CharField(max_length=32, choices=WorkflowDefinition.BIZ_TYPE_CHOICES)
    biz_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50)
    action_label = models.CharField(max_length=100, blank=True)
    from_step_key = models.CharField(max_length=100, blank=True)
    from_step_name = models.CharField(max_length=200, blank=True)
    to_step_key = models.CharField(max_length=100, blank=True)
    to_step_name = models.CharField(max_length=200, blank=True)
    operator = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_action_logs",
    )
    comment = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "workflow_action_logs"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["biz_type", "biz_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.instance.business_key}:{self.action}"
