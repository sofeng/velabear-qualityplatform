from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.projects.models import Project, ProjectMember
from apps.requirement_analysis.models import BusinessRequirement, RequirementAnalysis, RequirementDocument
from apps.users.models import User
from apps.defects.models import Defect

from .models import (
    WorkflowActionLog,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowRule,
    WorkflowTask,
)

RESOLVED_DEFECT_STATUSES = {"resolved", "regression_verified", "requirement_created", "closed"}
REOPENED_DEFECT_STATUSES = {"new", "returned_pending", "reopened"}


DEFAULT_DEFINITIONS = {
    "defect": {
        "key": "defect_lifecycle",
        "scene_key": "default",
        "name": "Defect Lifecycle",
        "steps": [
            {
                "key": "triage",
                "name": "Defect Triage",
                "candidate_roles": ["owner", "admin"],
                "sla_hours": 12,
                "business_status": "new",
                "actions": [
                    {"key": "approve", "label": "Accept", "next": "fixing", "business_status": "in_progress"},
                    {"key": "reject", "label": "Reject", "complete": True, "business_status": "rejected"},
                    {"key": "invalid", "label": "Invalidate", "complete": True, "business_status": "invalid"},
                ],
            },
            {
                "key": "fixing",
                "name": "Development Fix",
                "candidate_roles": ["developer"],
                "fallback_field": "assignees",
                "sla_hours": 24,
                "business_status": "in_progress",
                "actions": [
                    {"key": "resolve", "label": "Resolve", "next": "regression", "business_status": "resolved"},
                    {"key": "return", "label": "Return To Triage", "next": "triage", "business_status": "new"},
                ],
            },
            {
                "key": "regression",
                "name": "Regression Validation",
                "candidate_roles": ["tester"],
                "fallback_field": "created_by",
                "sla_hours": 24,
                "business_status": "resolved",
                "actions": [
                    {"key": "approve", "label": "Close", "complete": True, "business_status": "closed"},
                    {"key": "reject", "label": "Reopen", "next": "fixing", "business_status": "reopened"},
                ],
            },
        ],
    },
    "requirement": {
        "key": "requirement_lifecycle",
        "scene_key": "default",
        "name": "Requirement Lifecycle",
        "steps": [
            {
                "key": "product_review",
                "name": "Product Review",
                "candidate_roles": ["owner", "admin"],
                "fallback_field": "reviewer_or_owner",
                "sla_hours": 24,
                "actions": [
                    {"key": "approve", "label": "Approve", "next": "tech_review"},
                    {"key": "reject", "label": "Reject", "complete": True},
                ],
            },
            {
                "key": "tech_review",
                "name": "Technical Review",
                "candidate_roles": ["developer", "admin"],
                "enabled_if": "need_tech_review",
                "sla_hours": 24,
                "actions": [
                    {"key": "approve", "label": "Approve", "next": "qa_review"},
                    {"key": "return", "label": "Return To Product Review", "next": "product_review"},
                ],
            },
            {
                "key": "qa_review",
                "name": "QA Review",
                "candidate_roles": ["tester"],
                "enabled_if": "need_qa_review",
                "sla_hours": 24,
                "actions": [
                    {"key": "approve", "label": "Approve", "next": "acceptance"},
                    {"key": "return", "label": "Return To Tech Review", "next": "tech_review"},
                ],
            },
            {
                "key": "acceptance",
                "name": "Acceptance",
                "fallback_field": "created_by",
                "sla_hours": 48,
                "actions": [
                    {"key": "approve", "label": "Complete", "complete": True},
                    {"key": "return", "label": "Return To Product Review", "next": "product_review"},
                ],
            },
        ],
    },
}


DEFAULT_RULES = [
    {
        "biz_type": "defect",
        "scene_key": "default",
        "step_key": "triage",
        "name": "Critical Defect Triage SLA",
        "priority": 10,
        "conditions": {"severity": ["critical"]},
        "outputs": {"sla_hours": 4, "remind_after_hours": 2, "escalation_after_hours": 6, "candidate_roles": ["owner", "admin"]},
    },
    {
        "biz_type": "defect",
        "scene_key": "default",
        "step_key": "fixing",
        "name": "High Defect Fixing SLA",
        "priority": 20,
        "conditions": {"severity": ["high", "critical"]},
        "outputs": {"sla_hours": 16, "remind_after_hours": 8, "escalation_after_hours": 20},
    },
    {
        "biz_type": "requirement",
        "scene_key": "default",
        "step_key": "*",
        "name": "Low Level Requirement Fast Track",
        "priority": 10,
        "conditions": {"requirement_level": ["low"]},
        "outputs": {"set_variables": {"need_tech_review": False, "need_qa_review": False}},
    },
    {
        "biz_type": "requirement",
        "scene_key": "default",
        "step_key": "*",
        "name": "Medium Requirement Tech Review",
        "priority": 20,
        "conditions": {"requirement_level": ["medium"]},
        "outputs": {"set_variables": {"need_tech_review": True, "need_qa_review": False}},
    },
    {
        "biz_type": "requirement",
        "scene_key": "default",
        "step_key": "*",
        "name": "High Requirement Full Review",
        "priority": 30,
        "conditions": {"requirement_level": ["high"]},
        "outputs": {"set_variables": {"need_tech_review": True, "need_qa_review": True, "priority_flag": "high"}},
    },
]


def unique_users(users):
    seen = set()
    ordered = []
    for user in users:
        if not user or user.pk in seen:
            continue
        seen.add(user.pk)
        ordered.append(user)
    return ordered


def get_project_members_by_roles(project, roles):
    role_set = set(roles or [])
    if not project or not role_set:
        return []

    users = []
    if "owner" in role_set and project.owner_id:
        users.append(project.owner)

    member_user_ids = list(
        ProjectMember.objects.filter(project=project, role__in=role_set)
        .values_list("user_id", flat=True)
        .distinct()
    )
    if member_user_ids:
        users.extend(User.objects.filter(id__in=member_user_ids))
    return unique_users(users)


def is_rule_match(conditions, context):
    for key, expected in (conditions or {}).items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False
    return True


def merge_outputs(base, override):
    merged = deepcopy(base or {})
    for key, value in (override or {}).items():
        if key == "set_variables":
            variables = dict(merged.get("set_variables") or {})
            variables.update(value or {})
            merged["set_variables"] = variables
        else:
            merged[key] = value
    return merged


@dataclass
class StepResolution:
    step: dict
    index: int


class BaseWorkflowAdapter:
    biz_type = ""

    def get_queryset(self):
        raise NotImplementedError

    def get_object(self, biz_id):
        return self.get_queryset().get(pk=biz_id)

    def get_business_key(self, obj):
        return f"{self.biz_type}:{obj.pk}"

    def get_business_code(self, obj):
        return str(obj.pk)

    def get_business_title(self, obj):
        return str(obj)

    def get_project(self, obj):
        return None

    def get_project_id(self, obj):
        project = self.get_project(obj)
        return project.id if project else None

    def user_has_access(self, obj, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True

        project = self.get_project(obj)
        if project:
            if project.owner_id == user.id:
                return True
            return ProjectMember.objects.filter(project=project, user=user).exists()

        default_users = unique_users(self.get_default_fallback_users(obj))
        return any(item.id == user.id for item in default_users)

    def get_initial_variables(self, obj):
        return {}

    def build_context(self, obj):
        return {
            "biz_id": obj.pk,
            "project_id": self.get_project_id(obj),
        }

    def sync_business_status(self, obj, business_status, instance=None, actor=None):
        return None

    def get_default_fallback_users(self, obj):
        project = self.get_project(obj)
        if project and project.owner_id:
            return [project.owner]
        return []

    def get_fallback_users(self, obj, fallback_field):
        if not fallback_field:
            return []
        if fallback_field == "created_by":
            user = getattr(obj, "created_by", None)
            return [user] if user else self.get_default_fallback_users(obj)
        if fallback_field == "assignees":
            return list(getattr(obj, "assignees").all()) if hasattr(obj, "assignees") else []
        if fallback_field == "reviewer_or_owner":
            reviewer_name = str(getattr(obj, "reviewer", "") or "").strip()
            if reviewer_name:
                user = User.objects.filter(Q(username=reviewer_name) | Q(first_name=reviewer_name) | Q(last_name=reviewer_name)).first()
                if user:
                    return [user]
            return self.get_default_fallback_users(obj)
        return self.get_default_fallback_users(obj)


class DefectWorkflowAdapter(BaseWorkflowAdapter):
    biz_type = "defect"

    def get_queryset(self):
        return (
            Defect.objects
            .filter(record_type=Defect.RECORD_TYPE_DEFECT)
            .select_related("project", "created_by")
            .prefetch_related("assignees")
        )

    def get_business_code(self, obj):
        return obj.code or super().get_business_code(obj)

    def get_business_title(self, obj):
        return obj.title

    def get_project(self, obj):
        return obj.project

    def get_initial_variables(self, obj):
        return {"severity": obj.severity}

    def build_context(self, obj):
        context = super().build_context(obj)
        context.update({
            "severity": obj.severity,
            "creator_id": obj.created_by_id,
        })
        return context

    def sync_business_status(self, obj, business_status, instance=None, actor=None):
        if business_status and obj.status != business_status:
            operator = actor or (instance.current_assignee if instance else None)
            obj.status = business_status
            fields = ["status", "updated_at"]
            if business_status in RESOLVED_DEFECT_STATUSES:
                obj.resolved_at = timezone.now()
                obj.resolved_by = operator
                fields.extend(["resolved_at", "resolved_by"])
            if business_status == "closed":
                obj.closed_at = timezone.now()
                obj.closed_by = operator
                fields.extend(["closed_at", "closed_by"])
            if business_status in REOPENED_DEFECT_STATUSES:
                obj.resolved_at = None
                obj.resolved_by = None
                obj.closed_at = None
                obj.closed_by = None
                fields.extend(["resolved_at", "resolved_by", "closed_at", "closed_by"])
            obj.save(update_fields=list(dict.fromkeys(fields)))


class RequirementWorkflowAdapter(BaseWorkflowAdapter):
    biz_type = "requirement"

    def get_queryset(self):
        return BusinessRequirement.objects.select_related(
            "analysis",
            "analysis__document",
            "analysis__document__project",
        )

    def get_business_code(self, obj):
        return obj.requirement_id or super().get_business_code(obj)

    def get_business_title(self, obj):
        return obj.requirement_name

    def get_project(self, obj):
        if obj.analysis and obj.analysis.document:
            return obj.analysis.document.project
        return None

    def user_has_access(self, obj, user):
        if super().user_has_access(obj, user):
            return True

        document = obj.analysis.document if obj.analysis and obj.analysis.document else None
        if document and document.uploaded_by_id == getattr(user, "id", None):
            return True

        reviewer_name = str(getattr(obj, "reviewer", "") or "").strip()
        full_name = str(getattr(user, "full_name", "") or "").strip()
        return bool(reviewer_name and reviewer_name in {user.username, full_name})

    def get_initial_variables(self, obj):
        return {
            "requirement_level": obj.requirement_level,
            "need_tech_review": obj.requirement_level in {"medium", "high"},
            "need_qa_review": obj.requirement_level == "high",
        }

    def build_context(self, obj):
        context = super().build_context(obj)
        context.update({
            "requirement_level": obj.requirement_level,
            "reviewer": obj.reviewer,
        })
        return context

    def sync_business_status(self, obj, business_status, instance=None, actor=None):
        if not business_status:
            return None
        metadata = dict((instance.metadata or {}))
        metadata["business_status"] = business_status
        instance.metadata = metadata
        instance.save(update_fields=["metadata", "updated_at"])


ADAPTERS = {
    "defect": DefectWorkflowAdapter(),
    "requirement": RequirementWorkflowAdapter(),
}


def get_workflow_adapter(biz_type):
    if biz_type not in ADAPTERS:
        raise ValueError(f"Unsupported workflow type: {biz_type}")
    return ADAPTERS[biz_type]


def get_business_object_if_accessible(user, biz_type, biz_id):
    adapter = get_workflow_adapter(biz_type)
    obj = adapter.get_queryset().filter(pk=biz_id).first()
    if not obj:
        return None
    if not adapter.user_has_access(obj, user):
        raise PermissionError("You do not have access to this business object")
    return obj


def filter_instance_queryset_for_user(queryset, user):
    if not user or not getattr(user, "is_authenticated", False):
        return queryset.none()
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return queryset

    accessible_projects = Project.objects.filter(
        Q(owner=user) | Q(members=user)
    ).distinct()
    defect_ids = Defect.objects.filter(
        project__in=accessible_projects,
        record_type=Defect.RECORD_TYPE_DEFECT,
    ).values("id")
    requirement_ids = BusinessRequirement.objects.filter(
        Q(analysis__document__project__in=accessible_projects)
        | Q(analysis__document__project__isnull=True, analysis__document__uploaded_by=user)
    ).values("id")

    return queryset.filter(
        Q(biz_type="defect", biz_id__in=defect_ids)
        | Q(biz_type="requirement", biz_id__in=requirement_ids)
    ).distinct()


def ensure_default_definition(biz_type, operator=None):
    preset = DEFAULT_DEFINITIONS[biz_type]
    definition = WorkflowDefinition.objects.filter(
        biz_type=biz_type,
        key=preset["key"],
        scene_key=preset["scene_key"],
        is_active=True,
    ).order_by("-version", "-id").first()
    if definition:
        return definition

    definition = WorkflowDefinition.objects.create(
        biz_type=biz_type,
        key=preset["key"],
        scene_key=preset["scene_key"],
        name=preset["name"],
        version=1,
        config={"steps": deepcopy(preset["steps"])},
        is_active=True,
        created_by=operator if getattr(operator, "is_authenticated", False) else None,
    )
    return definition


def ensure_default_rules(operator=None):
    for preset in DEFAULT_RULES:
        WorkflowRule.objects.get_or_create(
            biz_type=preset["biz_type"],
            scene_key=preset["scene_key"],
            step_key=preset["step_key"],
            name=preset["name"],
            defaults={
                "priority": preset["priority"],
                "conditions": deepcopy(preset["conditions"]),
                "outputs": deepcopy(preset["outputs"]),
                "is_active": True,
                "created_by": operator if getattr(operator, "is_authenticated", False) else None,
            },
        )


def resolve_step(definition, step_key, variables=None):
    variables = variables or {}
    steps = definition.config.get("steps", [])
    for index, step in enumerate(steps):
        if step["key"] != step_key:
            continue
        if step.get("enabled_if") and not variables.get(step["enabled_if"], False):
            return None
        return StepResolution(step=step, index=index)
    return None


def resolve_first_step(definition, variables=None):
    variables = variables or {}
    steps = definition.config.get("steps", [])
    for index, step in enumerate(steps):
        if step.get("enabled_if") and not variables.get(step["enabled_if"], False):
            continue
        return StepResolution(step=step, index=index)
    return None


def resolve_next_step(definition, next_key, variables=None):
    if not next_key:
        return None
    variables = variables or {}
    steps = definition.config.get("steps", [])
    matched_index = None
    for index, step in enumerate(steps):
        if step["key"] == next_key:
            matched_index = index
            break
    if matched_index is None:
        return None
    for index in range(matched_index, len(steps)):
        step = steps[index]
        if step.get("enabled_if") and not variables.get(step["enabled_if"], False):
            continue
        return StepResolution(step=step, index=index)
    return None


def get_rule_outputs_and_matches(biz_type, scene_key, step_key, context):
    matched = {}
    matched_rules = []
    rules = WorkflowRule.objects.filter(
        biz_type=biz_type,
        scene_key=scene_key,
        is_active=True,
    ).filter(Q(step_key="*") | Q(step_key=step_key)).order_by("priority", "id")
    for rule in rules:
        if is_rule_match(rule.conditions, context):
            matched = merge_outputs(matched, rule.outputs)
            matched_rules.append({
                "id": rule.id,
                "name": rule.name,
                "step_key": rule.step_key,
                "priority": rule.priority,
                "conditions": deepcopy(rule.conditions or {}),
                "outputs": deepcopy(rule.outputs or {}),
            })
    return matched, matched_rules


def get_rule_outputs(biz_type, scene_key, step_key, context):
    matched, _ = get_rule_outputs_and_matches(biz_type, scene_key, step_key, context)
    return matched


def build_task_actions(step, rule_outputs):
    if rule_outputs.get("actions"):
        return deepcopy(rule_outputs["actions"])
    return deepcopy(step.get("actions") or [])


def get_simulation_defaults_for_biz_type(biz_type, inputs=None):
    inputs = inputs or {}
    if biz_type == "defect":
        severity = str(inputs.get("severity") or "critical").strip() or "critical"
        variables = {"severity": severity}
        context = {"severity": severity}
        return {
            "inputs": {"severity": severity},
            "variables": variables,
            "context": context,
        }

    if biz_type == "requirement":
        requirement_level = str(inputs.get("requirement_level") or "high").strip() or "high"
        variables = {
            "requirement_level": requirement_level,
            "need_tech_review": requirement_level in {"medium", "high"},
            "need_qa_review": requirement_level == "high",
        }
        context = {
            "requirement_level": requirement_level,
            **variables,
        }
        return {
            "inputs": {"requirement_level": requirement_level},
            "variables": variables,
            "context": context,
        }

    raise ValueError(f"Unsupported workflow type: {biz_type}")


def build_simulation_step_preview(definition, step, index, variables):
    enabled_if = str(step.get("enabled_if") or "").strip()
    is_enabled = not enabled_if or bool(variables.get(enabled_if))
    context = dict(variables or {})
    rule_outputs, matched_rules = get_rule_outputs_and_matches(
        definition.biz_type,
        definition.scene_key,
        step["key"],
        context,
    )
    actions = build_task_actions(step, rule_outputs)

    return {
        "index": index + 1,
        "key": step["key"],
        "name": step["name"],
        "enabled": is_enabled,
        "enabled_if": enabled_if,
        "skip_reason": f"条件 {enabled_if} 未命中" if enabled_if and not is_enabled else "",
        "candidate_roles": rule_outputs.get("candidate_roles", step.get("candidate_roles", [])),
        "fallback_field": step.get("fallback_field") or "",
        "sla_hours": rule_outputs.get("sla_hours", step.get("sla_hours")),
        "remind_after_hours": rule_outputs.get("remind_after_hours"),
        "escalation_after_hours": rule_outputs.get("escalation_after_hours"),
        "business_status": step.get("business_status") or "",
        "matched_rules": matched_rules,
        "actions": deepcopy(actions),
        "effective_outputs": deepcopy(rule_outputs),
    }


def simulate_workflow_definition(definition_id, inputs=None):
    definition = WorkflowDefinition.objects.get(pk=definition_id)
    simulation_defaults = get_simulation_defaults_for_biz_type(definition.biz_type, inputs=inputs)
    inputs = simulation_defaults["inputs"]
    variables = dict(simulation_defaults["variables"])
    context = dict(simulation_defaults["context"])

    start_outputs, start_rules = get_rule_outputs_and_matches(
        definition.biz_type,
        definition.scene_key,
        "*",
        context,
    )
    variables.update(start_outputs.get("set_variables") or {})
    context.update(variables)

    step_previews = [
        build_simulation_step_preview(definition, step, index, variables)
        for index, step in enumerate(definition.config.get("steps", []))
    ]
    active_steps = [step for step in step_previews if step["enabled"]]
    first_step = active_steps[0] if active_steps else None

    return {
        "definition": {
            "id": definition.id,
            "biz_type": definition.biz_type,
            "key": definition.key,
            "scene_key": definition.scene_key,
            "name": definition.name,
            "version": definition.version,
        },
        "inputs": inputs,
        "variables": variables,
        "start_rules": start_rules,
        "start_outputs": deepcopy(start_outputs),
        "first_step_key": first_step["key"] if first_step else "",
        "first_step_name": first_step["name"] if first_step else "",
        "active_step_count": len(active_steps),
        "skipped_step_count": len(step_previews) - len(active_steps),
        "steps": step_previews,
    }


def create_requirement_from_defect(defect, operator):
    if defect.requirement_id:
        return None

    project = defect.project
    uploaded_by = operator if getattr(operator, "is_authenticated", False) else defect.created_by
    document = RequirementDocument.objects.create(
        title=defect.title,
        file="",
        document_type="txt",
        status="analyzed",
        uploaded_by=uploaded_by,
        project=project,
        extracted_text=defect.description or "",
    )
    analysis = RequirementAnalysis.objects.create(
        document=document,
        analysis_report=f"Created from defect {defect.code or defect.pk}",
        requirements_count=1,
        analysis_time=0.1,
    )
    requirement = BusinessRequirement.objects.create(
        analysis=analysis,
        requirement_id=f"REQ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        requirement_name=defect.title[:200],
        requirement_type="functional",
        module="Defect Conversion",
        requirement_level="medium",
        reviewer=defect.created_by.username if defect.created_by_id else "admin",
        estimated_hours=8,
        description=defect.description or defect.title,
        acceptance_criteria=f"Created from defect {defect.code or defect.pk}",
    )
    defect.requirement_id = requirement.requirement_id
    defect.save(update_fields=["requirement_id", "updated_at"])
    return requirement


def create_task(instance, obj, step, operator=None):
    adapter = get_workflow_adapter(instance.biz_type)
    context = adapter.build_context(obj)
    context.update(instance.variables or {})
    rule_outputs = get_rule_outputs(instance.biz_type, instance.scene_key, step["key"], context)
    actions = build_task_actions(step, rule_outputs)

    project = adapter.get_project(obj)
    candidate_roles = rule_outputs.get("candidate_roles", step.get("candidate_roles", []))
    candidate_users = get_project_members_by_roles(project, candidate_roles)
    candidate_users.extend(adapter.get_fallback_users(obj, step.get("fallback_field")))
    candidate_users = unique_users(candidate_users)
    assignee = candidate_users[0] if len(candidate_users) == 1 else None

    sla_hours = rule_outputs.get("sla_hours", step.get("sla_hours"))
    remind_after_hours = rule_outputs.get("remind_after_hours")
    escalation_after_hours = rule_outputs.get("escalation_after_hours")

    now = timezone.now()
    task = WorkflowTask.objects.create(
        instance=instance,
        step_key=step["key"],
        step_name=step["name"],
        assignee=assignee,
        candidate_groups=candidate_roles,
        available_actions=actions,
        sla_hours=sla_hours,
        remind_at=(now + timedelta(hours=remind_after_hours)) if remind_after_hours else None,
        due_at=(now + timedelta(hours=sla_hours)) if sla_hours else None,
        escalation_due_at=(now + timedelta(hours=escalation_after_hours)) if escalation_after_hours else None,
    )
    if candidate_users:
        task.candidate_users.set(candidate_users)

    instance.current_step_key = task.step_key
    instance.current_step_name = task.step_name
    instance.current_task_id = task.id
    instance.current_assignee = task.assignee
    instance.save(update_fields=["current_step_key", "current_step_name", "current_task_id", "current_assignee", "updated_at"])
    return task


def get_open_task_for_instance(instance):
    return instance.tasks.filter(status="open").select_related("assignee").prefetch_related("candidate_users").order_by("-created_at", "-id").first()


def serialize_action_choice(action):
    return {
        "key": action.get("key"),
        "label": action.get("label") or action.get("key", "").replace("_", " ").title(),
        "next": action.get("next"),
        "complete": bool(action.get("complete")),
    }


def serialize_task_summary(task, user=None):
    available_actions = task.available_actions or []
    can_act = False
    can_claim = False
    can_transfer = False
    if user and getattr(user, "is_authenticated", False):
        candidate_ids = set(task.candidate_users.values_list("id", flat=True))
        is_candidate = bool(user.is_superuser or user.id in candidate_ids)
        is_assignee = bool(task.assignee_id == user.id)
        has_transfer_target = any(candidate_id != task.assignee_id for candidate_id in candidate_ids)
        if user.is_superuser:
            can_act = True
        elif task.assignee_id:
            can_act = is_assignee
        else:
            can_act = is_candidate
        can_claim = bool(not task.assignee_id and is_candidate)
        can_transfer = bool(task.assignee_id and has_transfer_target and (user.is_superuser or is_assignee))

    return {
        "id": task.id,
        "step_key": task.step_key,
        "step_name": task.step_name,
        "status": task.status,
        "assignee": {
            "id": task.assignee.id,
            "username": task.assignee.username,
            "full_name": task.assignee.full_name,
        } if task.assignee_id else None,
        "candidate_users": [
            {"id": item.id, "username": item.username, "full_name": item.full_name}
            for item in task.candidate_users.all()
        ],
        "candidate_groups": task.candidate_groups or [],
        "available_actions": [serialize_action_choice(action) for action in available_actions],
        "can_act": can_act,
        "can_claim": can_claim,
        "can_transfer": can_transfer,
        "transfer_candidates": [
            {"id": item.id, "username": item.username, "full_name": item.full_name}
            for item in task.candidate_users.all()
            if item.id != task.assignee_id
        ],
        "due_at": task.due_at,
        "remind_at": task.remind_at,
        "escalation_due_at": task.escalation_due_at,
        "created_at": task.created_at,
    }


def serialize_workflow_instance(instance, user=None):
    task = get_open_task_for_instance(instance)
    logs = list(instance.action_logs.select_related("operator").order_by("created_at", "id")[:200])
    return {
        "instance_id": instance.id,
        "run_number": instance.run_number,
        "definition_key": instance.definition.key,
        "definition_name": instance.definition.name,
        "status": instance.status,
        "scene_key": instance.scene_key,
        "current_step_key": instance.current_step_key,
        "current_step_name": instance.current_step_name,
        "current_task": serialize_task_summary(task, user=user) if task else None,
        "variables": instance.variables,
        "metadata": instance.metadata,
        "started_at": instance.started_at,
        "completed_at": instance.completed_at,
        "timeline": [
            {
                "id": log.id,
                "action": log.action,
                "action_label": log.action_label,
                "from_step_key": log.from_step_key,
                "from_step_name": log.from_step_name,
                "to_step_key": log.to_step_key,
                "to_step_name": log.to_step_name,
                "comment": log.comment,
                "operator": {
                    "id": log.operator.id,
                    "username": log.operator.username,
                    "full_name": log.operator.full_name,
                } if log.operator_id else None,
                "created_at": log.created_at,
                "payload": log.payload,
            }
            for log in logs
        ],
    }


def get_workflow_summary(biz_type, biz_id, user=None):
    instance = WorkflowInstance.objects.filter(
        biz_type=biz_type,
        biz_id=biz_id,
    ).order_by("-started_at", "-id").select_related("definition", "current_assignee").first()
    if not instance:
        return None
    return serialize_workflow_instance(instance, user=user)


def ensure_rules_and_definition(biz_type, operator=None):
    ensure_default_rules(operator=operator)
    return ensure_default_definition(biz_type, operator=operator)


def bootstrap_workflow_catalog(operator=None):
    ensure_default_rules(operator=operator)
    return [
        ensure_default_definition(biz_type, operator=operator)
        for biz_type in DEFAULT_DEFINITIONS.keys()
    ]


def get_definition_family_queryset(definition):
    return WorkflowDefinition.objects.filter(
        biz_type=definition.biz_type,
        key=definition.key,
        scene_key=definition.scene_key,
    )


def get_definition_steps(config):
    steps = (config or {}).get("steps") if isinstance(config, dict) else None
    return steps if isinstance(steps, list) else []


def get_definition_action_count(config):
    return sum(len(step.get("actions") or []) for step in get_definition_steps(config))


def build_definition_step_preview(step):
    return {
        "key": str(step.get("key") or "").strip(),
        "name": str(step.get("name") or "").strip(),
        "candidate_roles": [str(item).strip() for item in (step.get("candidate_roles") or []) if str(item).strip()],
        "fallback_field": str(step.get("fallback_field") or "").strip(),
        "sla_hours": step.get("sla_hours"),
        "enabled_if": str(step.get("enabled_if") or "").strip(),
        "business_status": str(step.get("business_status") or "").strip(),
        "actions": [
            {
                "key": str(action.get("key") or "").strip(),
                "label": str(action.get("label") or "").strip(),
                "next": str(action.get("next") or "").strip(),
                "complete": bool(action.get("complete")),
                "business_status": str(action.get("business_status") or "").strip(),
            }
            for action in (step.get("actions") or [])
            if isinstance(action, dict)
        ],
    }


def build_definition_change_summary(definition, previous_definition=None):
    current_steps = get_definition_steps(definition.config)
    if not previous_definition:
        return {
            "name_changed": False,
            "step_delta": len(current_steps),
            "action_delta": get_definition_action_count(definition.config),
            "added_steps": [str(step.get("key") or "").strip() for step in current_steps if str(step.get("key") or "").strip()],
            "removed_steps": [],
            "modified_steps": [],
        }

    previous_steps = get_definition_steps(previous_definition.config)
    current_by_key = {str(step.get("key") or "").strip(): step for step in current_steps if str(step.get("key") or "").strip()}
    previous_by_key = {str(step.get("key") or "").strip(): step for step in previous_steps if str(step.get("key") or "").strip()}

    shared_keys = set(current_by_key.keys()) & set(previous_by_key.keys())
    modified_steps = [
        key
        for key in sorted(shared_keys)
        if build_definition_step_preview(current_by_key[key]) != build_definition_step_preview(previous_by_key[key])
    ]

    return {
        "name_changed": definition.name != previous_definition.name,
        "step_delta": len(current_steps) - len(previous_steps),
        "action_delta": get_definition_action_count(definition.config) - get_definition_action_count(previous_definition.config),
        "added_steps": sorted(set(current_by_key.keys()) - set(previous_by_key.keys())),
        "removed_steps": sorted(set(previous_by_key.keys()) - set(current_by_key.keys())),
        "modified_steps": modified_steps,
    }


def serialize_definition_version(definition, previous_definition=None):
    steps = [build_definition_step_preview(step) for step in get_definition_steps(definition.config)]
    return {
        "id": definition.id,
        "biz_type": definition.biz_type,
        "key": definition.key,
        "scene_key": definition.scene_key,
        "name": definition.name,
        "version": definition.version,
        "is_active": definition.is_active,
        "created_by": {
            "id": definition.created_by.id,
            "username": definition.created_by.username,
            "full_name": definition.created_by.full_name,
        } if definition.created_by_id else None,
        "created_at": definition.created_at,
        "updated_at": definition.updated_at,
        "step_count": len(steps),
        "action_count": sum(len(step["actions"]) for step in steps),
        "steps": steps,
        "change_summary": build_definition_change_summary(definition, previous_definition=previous_definition),
    }


def get_workflow_definition_versions(definition_id):
    source = WorkflowDefinition.objects.select_related("created_by").get(pk=definition_id)
    versions = list(
        get_definition_family_queryset(source)
        .select_related("created_by")
        .order_by("-version", "-id")
    )
    previous_by_version = {
        item.version: next((candidate for candidate in versions if candidate.version == item.version - 1), None)
        for item in versions
    }
    return [
        serialize_definition_version(item, previous_definition=previous_by_version.get(item.version))
        for item in versions
    ]


def publish_workflow_definition_version(definition_id, payload, operator):
    source = WorkflowDefinition.objects.get(pk=definition_id)
    payload = payload or {}
    with transaction.atomic():
        family_queryset = get_definition_family_queryset(source).select_for_update()
        latest = (
            family_queryset
            .order_by("-version", "-id")
            .first()
        )
        next_version = (latest.version + 1) if latest else 1
        family_queryset.filter(is_active=True).update(is_active=False)
        return WorkflowDefinition.objects.create(
            biz_type=source.biz_type,
            key=source.key,
            scene_key=source.scene_key,
            name=(payload.get("name") or source.name).strip(),
            version=next_version,
            config=deepcopy(payload.get("config") or source.config or {}),
            is_active=True,
            created_by=operator if getattr(operator, "is_authenticated", False) else None,
        )


def restore_workflow_definition_version(definition_id, operator):
    source = WorkflowDefinition.objects.get(pk=definition_id)
    with transaction.atomic():
        family_queryset = get_definition_family_queryset(source).select_for_update()
        active_definition = family_queryset.filter(is_active=True).order_by("-version", "-id").first()
        latest_definition = family_queryset.order_by("-version", "-id").first()

        if active_definition and active_definition.id == source.id:
            raise ValueError("The selected definition version is already active")

        next_version = (latest_definition.version + 1) if latest_definition else 1
        family_queryset.filter(is_active=True).update(is_active=False)
        restored = WorkflowDefinition.objects.create(
            biz_type=source.biz_type,
            key=source.key,
            scene_key=source.scene_key,
            name=source.name,
            version=next_version,
            config=deepcopy(source.config or {}),
            is_active=True,
            created_by=operator if getattr(operator, "is_authenticated", False) else None,
        )
    return restored


def start_workflow(biz_type, biz_id, operator):
    adapter = get_workflow_adapter(biz_type)
    obj = adapter.get_object(biz_id)
    if not adapter.user_has_access(obj, operator):
        raise PermissionError("You do not have access to this business object")
    existing = WorkflowInstance.objects.filter(
        biz_type=biz_type,
        biz_id=biz_id,
        status="running",
    ).order_by("-started_at", "-id").first()
    if existing:
        return existing

    definition = ensure_rules_and_definition(biz_type, operator=operator)
    variables = adapter.get_initial_variables(obj)
    context = adapter.build_context(obj)
    context.update(variables)
    start_outputs = get_rule_outputs(biz_type, definition.scene_key, "*", context)
    variables.update(start_outputs.get("set_variables") or {})
    context.update(variables)

    step_resolution = resolve_first_step(definition, variables=variables)
    if not step_resolution:
        raise ValueError("Workflow definition has no active step")

    with transaction.atomic():
        latest_instance = (
            WorkflowInstance.objects.select_for_update()
            .filter(biz_type=biz_type, biz_id=obj.pk)
            .order_by("-run_number", "-id")
            .first()
        )
        next_run_number = (latest_instance.run_number + 1) if latest_instance else 1
        instance = WorkflowInstance.objects.create(
            definition=definition,
            biz_type=biz_type,
            biz_id=obj.pk,
            biz_code=adapter.get_business_code(obj),
            biz_title=adapter.get_business_title(obj),
            business_key=adapter.get_business_key(obj),
            run_number=next_run_number,
            status="running",
            scene_key=definition.scene_key,
            variables=variables,
            metadata={"business_status": step_resolution.step.get("business_status")},
            started_by=operator if getattr(operator, "is_authenticated", False) else None,
        )
        task = create_task(instance, obj, step_resolution.step, operator=operator)
        initial_status = step_resolution.step.get("business_status")
        adapter.sync_business_status(obj, initial_status, instance=instance, actor=operator)
        WorkflowActionLog.objects.create(
            instance=instance,
            task=task,
            biz_type=biz_type,
            biz_id=obj.pk,
            action="start",
            action_label="Start Workflow",
            to_step_key=task.step_key,
            to_step_name=task.step_name,
            operator=operator if getattr(operator, "is_authenticated", False) else None,
            payload={"business_status": initial_status},
        )
    return instance


def user_can_act_on_task(task, user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if task.assignee_id:
        return task.assignee_id == user.id
    return task.candidate_users.filter(id=user.id).exists()


def complete_instance(instance, task, operator, action_cfg, comment=""):
    adapter = get_workflow_adapter(instance.biz_type)
    obj = adapter.get_object(instance.biz_id)
    business_status = action_cfg.get("business_status") or instance.metadata.get("business_status")

    task.status = "completed"
    task.completed_at = timezone.now()
    task.completed_by = operator
    task.save(update_fields=["status", "completed_at", "completed_by"])

    if action_cfg.get("side_effect") == "create_requirement" and instance.biz_type == "defect":
        created_requirement = create_requirement_from_defect(obj, operator)
        if created_requirement:
            payload = dict(instance.metadata or {})
            payload["created_requirement_id"] = created_requirement.id
            payload["created_requirement_code"] = created_requirement.requirement_id
            instance.metadata = payload

    instance.status = "completed"
    instance.current_step_key = ""
    instance.current_step_name = ""
    instance.current_task_id = None
    instance.current_assignee = None
    instance.completed_at = timezone.now()
    if business_status:
        payload = dict(instance.metadata or {})
        payload["business_status"] = business_status
        instance.metadata = payload
    instance.save(
        update_fields=[
            "status",
            "current_step_key",
            "current_step_name",
            "current_task_id",
            "current_assignee",
            "completed_at",
            "metadata",
            "updated_at",
        ]
    )
    adapter.sync_business_status(obj, business_status, instance=instance, actor=operator)
    WorkflowActionLog.objects.create(
        instance=instance,
        task=task,
        biz_type=instance.biz_type,
        biz_id=instance.biz_id,
        action=action_cfg["key"],
        action_label=action_cfg.get("label") or action_cfg["key"],
        from_step_key=task.step_key,
        from_step_name=task.step_name,
        operator=operator,
        comment=comment,
        payload={"completed": True, "business_status": business_status},
    )
    return instance


def terminate_workflow_instance(instance_id, operator, comment=""):
    instance = WorkflowInstance.objects.select_related("definition", "current_assignee").get(pk=instance_id)
    if instance.status != "running":
        raise ValueError("Workflow instance is not running")

    now = timezone.now()
    comment = (comment or "").strip()

    with transaction.atomic():
        task = get_open_task_for_instance(instance)
        if task:
            task.status = "cancelled"
            task.completed_at = now
            task.completed_by = operator
            task.save(update_fields=["status", "completed_at", "completed_by"])

        payload = dict(instance.metadata or {})
        payload["terminated"] = True
        if comment:
            payload["termination_comment"] = comment

        instance.status = "terminated"
        instance.current_step_key = ""
        instance.current_step_name = ""
        instance.current_task_id = None
        instance.current_assignee = None
        instance.completed_at = now
        instance.metadata = payload
        instance.save(
            update_fields=[
                "status",
                "current_step_key",
                "current_step_name",
                "current_task_id",
                "current_assignee",
                "completed_at",
                "metadata",
                "updated_at",
            ]
        )

        WorkflowActionLog.objects.create(
            instance=instance,
            task=task,
            biz_type=instance.biz_type,
            biz_id=instance.biz_id,
            action="terminate",
            action_label="Terminate Workflow",
            from_step_key=task.step_key if task else instance.current_step_key,
            from_step_name=task.step_name if task else instance.current_step_name,
            operator=operator if getattr(operator, "is_authenticated", False) else None,
            comment=comment,
            payload={"terminated": True, "open_task_id": task.id if task else None},
        )
    return instance


def execute_task_action(task_id, action, operator, comment="", assignee_id=None):
    task = WorkflowTask.objects.select_related("instance", "instance__definition", "assignee").prefetch_related("candidate_users").get(pk=task_id)
    if task.status != "open":
        raise ValueError("Task is not open")
    if not user_can_act_on_task(task, operator):
        raise PermissionError("You cannot act on this task")

    instance = task.instance
    adapter = get_workflow_adapter(instance.biz_type)
    obj = adapter.get_object(instance.biz_id)

    if action == "claim":
        if task.assignee_id == operator.id:
            return instance
        if task.assignee_id:
            raise ValueError("Task has already been claimed")
        task.assignee = operator
        task.save(update_fields=["assignee"])
        instance.current_assignee = operator
        instance.save(update_fields=["current_assignee", "updated_at"])
        WorkflowActionLog.objects.create(
            instance=instance,
            task=task,
            biz_type=instance.biz_type,
            biz_id=instance.biz_id,
            action="claim",
            action_label="Claim Task",
            from_step_key=task.step_key,
            from_step_name=task.step_name,
            to_step_key=task.step_key,
            to_step_name=task.step_name,
            operator=operator,
            comment=comment,
        )
        return instance

    if action == "transfer":
        if not task.assignee_id:
            raise ValueError("Task must be claimed before transfer")
        if not (operator.is_superuser or task.assignee_id == operator.id):
            raise PermissionError("Only current assignee can transfer this task")
        if not assignee_id:
            raise ValueError("assignee_id is required")
        if assignee_id == task.assignee_id:
            raise ValueError("Target assignee must be different")
        new_assignee = task.candidate_users.filter(id=assignee_id).first()
        if not new_assignee:
            raise ValueError("Target assignee is not a candidate user")
        task.assignee = new_assignee
        task.save(update_fields=["assignee"])
        instance.current_assignee = new_assignee
        instance.save(update_fields=["current_assignee", "updated_at"])
        WorkflowActionLog.objects.create(
            instance=instance,
            task=task,
            biz_type=instance.biz_type,
            biz_id=instance.biz_id,
            action="transfer",
            action_label="Transfer Task",
            from_step_key=task.step_key,
            from_step_name=task.step_name,
            to_step_key=task.step_key,
            to_step_name=task.step_name,
            operator=operator,
            comment=comment,
            payload={"assignee_id": assignee_id},
        )
        return instance

    action_cfg = next((item for item in (task.available_actions or []) if item.get("key") == action), None)
    if not action_cfg:
        raise ValueError("Unsupported workflow action")

    with transaction.atomic():
        task.status = "completed"
        task.completed_at = timezone.now()
        task.completed_by = operator
        task.save(update_fields=["status", "completed_at", "completed_by"])

        instance.current_assignee = operator
        variables = dict(instance.variables or {})
        variables.update(action_cfg.get("set_variables") or {})
        instance.variables = variables

        if action_cfg.get("complete"):
            instance.save(update_fields=["variables", "current_assignee", "updated_at"])
            return complete_instance(instance, task, operator, action_cfg, comment=comment)

        next_resolution = resolve_next_step(instance.definition, action_cfg.get("next"), variables=variables)
        if not next_resolution:
            raise ValueError("Next step could not be resolved")

        next_task = create_task(instance, obj, next_resolution.step, operator=operator)
        business_status = action_cfg.get("business_status") or next_resolution.step.get("business_status")
        payload = dict(instance.metadata or {})
        if business_status:
            payload["business_status"] = business_status
        instance.metadata = payload
        instance.current_assignee = next_task.assignee
        instance.save(update_fields=["variables", "metadata", "current_assignee", "updated_at"])
        adapter.sync_business_status(obj, business_status, instance=instance, actor=operator)

        WorkflowActionLog.objects.create(
            instance=instance,
            task=task,
            biz_type=instance.biz_type,
            biz_id=instance.biz_id,
            action=action_cfg["key"],
            action_label=action_cfg.get("label") or action_cfg["key"],
            from_step_key=task.step_key,
            from_step_name=task.step_name,
            to_step_key=next_task.step_key,
            to_step_name=next_task.step_name,
            operator=operator,
            comment=comment,
            payload={"business_status": business_status},
        )

    return instance


def get_user_open_tasks(user, biz_type=None):
    queryset = WorkflowTask.objects.filter(status="open")
    if getattr(user, "is_superuser", False):
        queryset = queryset
    else:
        queryset = queryset.filter(Q(assignee=user) | Q(assignee__isnull=True, candidate_users=user))

    queryset = (
        queryset.select_related("instance", "instance__definition", "assignee")
        .prefetch_related("candidate_users")
        .distinct()
        .order_by("due_at", "created_at")
    )
    if biz_type:
        queryset = queryset.filter(instance__biz_type=biz_type)
    return queryset


def process_overdue_tasks(now=None):
    now = now or timezone.now()
    reminder_count = 0
    escalation_count = 0

    tasks = WorkflowTask.objects.filter(status="open").select_related("instance", "instance__definition")
    for task in tasks:
        instance = task.instance
        context = dict(instance.variables or {})
        context.update({"biz_id": instance.biz_id})

        if task.remind_at and task.reminded_at is None and task.remind_at <= now:
            task.reminded_at = now
            task.save(update_fields=["reminded_at"])
            reminder_count += 1
            WorkflowActionLog.objects.create(
                instance=instance,
                task=task,
                biz_type=instance.biz_type,
                biz_id=instance.biz_id,
                action="remind",
                action_label="Reminder Triggered",
                to_step_key=task.step_key,
                to_step_name=task.step_name,
                payload={"due_at": task.due_at.isoformat() if task.due_at else None},
            )

        if task.escalation_due_at and task.escalated_at is None and task.escalation_due_at <= now:
            task.escalated_at = now
            task.save(update_fields=["escalated_at"])
            escalation_count += 1
            WorkflowActionLog.objects.create(
                instance=instance,
                task=task,
                biz_type=instance.biz_type,
                biz_id=instance.biz_id,
                action="escalate",
                action_label="Escalation Triggered",
                to_step_key=task.step_key,
                to_step_name=task.step_name,
                payload={"escalation_due_at": task.escalation_due_at.isoformat()},
            )

    return {"reminders": reminder_count, "escalations": escalation_count}
