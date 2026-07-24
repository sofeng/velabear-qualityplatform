from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.defects.models import Defect
from apps.projects.models import Project, ProjectMember
from apps.requirement_analysis.models import (
    BusinessRequirement,
    RequirementAnalysis,
    RequirementDocument,
)
from apps.users.models import User

from .models import WorkflowActionLog, WorkflowDefinition, WorkflowRule
from .services import (
    ensure_rules_and_definition,
    execute_task_action,
    get_open_task_for_instance,
    get_workflow_definition_versions,
    get_user_open_tasks,
    publish_workflow_definition_version,
    process_overdue_tasks,
    restore_workflow_definition_version,
    simulate_workflow_definition,
    start_workflow,
    terminate_workflow_instance,
)


class WorkflowTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="owner", password="pass123", first_name="Owner")
        self.developer = User.objects.create_user(username="dev", password="pass123", first_name="Dev")
        self.tester = User.objects.create_user(username="tester", password="pass123", first_name="Tester")
        self.outsider = User.objects.create_user(username="outsider", password="pass123", first_name="Outsider")
        self.workflow_admin = User.objects.create_user(
            username="workflow_admin",
            password="pass123",
            first_name="Workflow",
            is_staff=True,
        )

        self.project = Project.objects.create(name="Workflow Project", owner=self.owner)
        ProjectMember.objects.create(project=self.project, user=self.developer, role="developer")
        ProjectMember.objects.create(project=self.project, user=self.tester, role="tester")

    def create_defect(self, **overrides):
        defect = Defect.objects.create(
            project=self.project,
            title=overrides.get("title", "Payment bug"),
            description=overrides.get("description", "Defect detail"),
            severity=overrides.get("severity", "high"),
            created_by=overrides.get("created_by", self.tester),
        )
        defect.assignees.set(overrides.get("assignees", [self.developer]))
        return defect

    def create_requirement(self, **overrides):
        document = RequirementDocument.objects.create(
            title=overrides.get("title", "Workflow requirement doc"),
            file="",
            document_type="txt",
            status="analyzed",
            uploaded_by=overrides.get("uploaded_by", self.owner),
            project=overrides.get("project", self.project),
            extracted_text=overrides.get("description", "Requirement detail"),
        )
        analysis = RequirementAnalysis.objects.create(
            document=document,
            analysis_report="analysis",
            requirements_count=1,
            analysis_time=0.2,
        )
        return BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id=overrides.get("requirement_id", "REQ-001"),
            requirement_name=overrides.get("requirement_name", "Workflow requirement"),
            requirement_type="functional",
            module="Workflow",
            requirement_level=overrides.get("requirement_level", "medium"),
            reviewer=overrides.get("reviewer", self.owner.username),
            estimated_hours=8,
            description=overrides.get("description", "Requirement detail"),
            acceptance_criteria=overrides.get("acceptance_criteria", "done"),
        )


class WorkflowServiceTests(WorkflowTestBase):
    def prepare_unassigned_requirement_review(self, requirement_id="REQ-CLAIM"):
        ProjectMember.objects.create(project=self.project, user=self.workflow_admin, role="admin")
        requirement = self.create_requirement(requirement_id=requirement_id, requirement_level="high")
        instance = start_workflow("requirement", requirement.id, self.owner)
        product_task = get_open_task_for_instance(instance)
        execute_task_action(product_task.id, "approve", self.owner, comment="product ok")
        instance.refresh_from_db()
        return instance, get_open_task_for_instance(instance)

    def test_defect_workflow_full_lifecycle_updates_status_and_audit_users(self):
        defect = self.create_defect()

        instance = start_workflow("defect", defect.id, self.owner)
        self.assertEqual(instance.current_step_key, "triage")

        triage_task = get_open_task_for_instance(instance)
        execute_task_action(triage_task.id, "approve", self.owner, comment="accept")

        instance.refresh_from_db()
        defect.refresh_from_db()
        self.assertEqual(instance.current_step_key, "fixing")
        self.assertEqual(defect.status, "in_progress")

        fixing_task = get_open_task_for_instance(instance)
        self.assertEqual(fixing_task.assignee_id, self.developer.id)
        execute_task_action(fixing_task.id, "resolve", self.developer, comment="fixed")

        instance.refresh_from_db()
        defect.refresh_from_db()
        self.assertEqual(instance.current_step_key, "regression")
        self.assertEqual(defect.status, "resolved")
        self.assertEqual(defect.resolved_by_id, self.developer.id)

        regression_task = get_open_task_for_instance(instance)
        self.assertEqual(regression_task.assignee_id, self.tester.id)
        execute_task_action(regression_task.id, "approve", self.tester, comment="verified")

        instance.refresh_from_db()
        defect.refresh_from_db()
        self.assertEqual(instance.status, "completed")
        self.assertEqual(defect.status, "closed")
        self.assertEqual(defect.closed_by_id, self.tester.id)

    def test_low_level_requirement_fast_tracks_to_acceptance(self):
        requirement = self.create_requirement(requirement_id="REQ-LOW", requirement_level="low")

        instance = start_workflow("requirement", requirement.id, self.owner)
        self.assertEqual(instance.current_step_key, "product_review")

        review_task = get_open_task_for_instance(instance)
        self.assertEqual(review_task.assignee_id, self.owner.id)
        execute_task_action(review_task.id, "approve", self.owner, comment="ok")

        instance.refresh_from_db()
        self.assertEqual(instance.current_step_key, "acceptance")
        self.assertFalse(instance.variables["need_tech_review"])
        self.assertFalse(instance.variables["need_qa_review"])

    def test_high_level_requirement_routes_through_tech_and_qa_review(self):
        requirement = self.create_requirement(requirement_id="REQ-HIGH", requirement_level="high")

        instance = start_workflow("requirement", requirement.id, self.owner)
        product_task = get_open_task_for_instance(instance)
        execute_task_action(product_task.id, "approve", self.owner, comment="product ok")

        instance.refresh_from_db()
        self.assertEqual(instance.current_step_key, "tech_review")
        tech_task = get_open_task_for_instance(instance)
        self.assertEqual(tech_task.assignee_id, self.developer.id)

        execute_task_action(tech_task.id, "approve", self.developer, comment="tech ok")

        instance.refresh_from_db()
        self.assertEqual(instance.current_step_key, "qa_review")
        qa_task = get_open_task_for_instance(instance)
        self.assertEqual(qa_task.assignee_id, self.tester.id)

    def test_overdue_processing_marks_reminders_and_escalations(self):
        defect = self.create_defect(severity="critical")
        instance = start_workflow("defect", defect.id, self.owner)
        task = get_open_task_for_instance(instance)

        result = process_overdue_tasks(now=task.created_at + timedelta(hours=7))

        task.refresh_from_db()
        self.assertEqual(result, {"reminders": 1, "escalations": 1})
        self.assertIsNotNone(task.reminded_at)
        self.assertIsNotNone(task.escalated_at)
        self.assertEqual(
            WorkflowActionLog.objects.filter(instance=instance, action__in=["remind", "escalate"]).count(),
            2,
        )

    def test_defect_regression_reject_reopens_fixing_and_clears_resolution_fields(self):
        defect = self.create_defect()
        instance = start_workflow("defect", defect.id, self.owner)

        triage_task = get_open_task_for_instance(instance)
        execute_task_action(triage_task.id, "approve", self.owner, comment="accept")

        fixing_task = get_open_task_for_instance(instance)
        execute_task_action(fixing_task.id, "resolve", self.developer, comment="fixed")

        regression_task = get_open_task_for_instance(instance)
        execute_task_action(regression_task.id, "reject", self.tester, comment="reopen")

        instance.refresh_from_db()
        defect.refresh_from_db()
        reopened_task = get_open_task_for_instance(instance)

        self.assertEqual(instance.current_step_key, "fixing")
        self.assertEqual(defect.status, "reopened")
        self.assertIsNone(defect.resolved_at)
        self.assertIsNone(defect.resolved_by_id)
        self.assertIsNone(defect.closed_at)
        self.assertIsNone(defect.closed_by_id)
        self.assertEqual(reopened_task.assignee_id, self.developer.id)

    def test_high_level_requirement_return_paths_move_back_to_previous_stage(self):
        requirement = self.create_requirement(requirement_id="REQ-RETURN", requirement_level="high")
        instance = start_workflow("requirement", requirement.id, self.owner)

        product_task = get_open_task_for_instance(instance)
        execute_task_action(product_task.id, "approve", self.owner, comment="product ok")

        tech_task = get_open_task_for_instance(instance)
        execute_task_action(tech_task.id, "return", self.developer, comment="need product clarification")

        instance.refresh_from_db()
        self.assertEqual(instance.current_step_key, "product_review")
        self.assertEqual(get_open_task_for_instance(instance).assignee_id, self.owner.id)

        product_task = get_open_task_for_instance(instance)
        execute_task_action(product_task.id, "approve", self.owner, comment="updated")

        tech_task = get_open_task_for_instance(instance)
        execute_task_action(tech_task.id, "approve", self.developer, comment="tech ok")

        qa_task = get_open_task_for_instance(instance)
        execute_task_action(qa_task.id, "return", self.tester, comment="need more detail")

        instance.refresh_from_db()
        self.assertEqual(instance.current_step_key, "tech_review")
        self.assertEqual(get_open_task_for_instance(instance).assignee_id, self.developer.id)

    def test_execute_task_action_rejects_operator_without_task_permission(self):
        defect = self.create_defect()
        instance = start_workflow("defect", defect.id, self.owner)
        triage_task = get_open_task_for_instance(instance)

        with self.assertRaisesMessage(PermissionError, "You cannot act on this task"):
            execute_task_action(triage_task.id, "approve", self.outsider)

    def test_claim_assigns_candidate_and_removes_task_from_other_candidates_queue(self):
        instance, tech_task = self.prepare_unassigned_requirement_review(requirement_id="REQ-CLAIM-QUEUE")

        self.assertIsNone(tech_task.assignee_id)
        self.assertCountEqual(
            list(tech_task.candidate_users.values_list("id", flat=True)),
            [self.developer.id, self.workflow_admin.id],
        )

        execute_task_action(tech_task.id, "claim", self.workflow_admin, comment="taking ownership")

        tech_task.refresh_from_db()
        instance.refresh_from_db()
        self.assertEqual(tech_task.assignee_id, self.workflow_admin.id)
        self.assertEqual(instance.current_assignee_id, self.workflow_admin.id)
        self.assertFalse(get_user_open_tasks(self.developer).filter(id=tech_task.id).exists())

        with self.assertRaisesMessage(PermissionError, "You cannot act on this task"):
            execute_task_action(tech_task.id, "approve", self.developer, comment="should be blocked")

    def test_transfer_requires_current_assignee_and_candidate_target(self):
        instance, tech_task = self.prepare_unassigned_requirement_review(requirement_id="REQ-TRANSFER")

        execute_task_action(tech_task.id, "claim", self.workflow_admin, comment="claimed")

        with self.assertRaisesMessage(ValueError, "candidate user"):
            execute_task_action(tech_task.id, "transfer", self.workflow_admin, assignee_id=self.outsider.id)

        execute_task_action(tech_task.id, "transfer", self.workflow_admin, assignee_id=self.developer.id, comment="handoff")

        tech_task.refresh_from_db()
        instance.refresh_from_db()
        self.assertEqual(tech_task.assignee_id, self.developer.id)
        self.assertEqual(instance.current_assignee_id, self.developer.id)
        self.assertTrue(get_user_open_tasks(self.developer).filter(id=tech_task.id).exists())
        self.assertFalse(get_user_open_tasks(self.workflow_admin).filter(id=tech_task.id).exists())

    def test_terminate_instance_cancels_open_task_and_records_action_log(self):
        defect = self.create_defect(title="Terminate target")
        instance = start_workflow("defect", defect.id, self.owner)
        task = get_open_task_for_instance(instance)

        terminate_workflow_instance(instance.id, self.workflow_admin, comment="stop workflow")

        instance.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(instance.status, "terminated")
        self.assertEqual(task.status, "cancelled")
        self.assertIsNone(instance.current_task_id)
        self.assertEqual(instance.metadata["terminated"], True)
        self.assertEqual(instance.metadata["termination_comment"], "stop workflow")
        self.assertTrue(WorkflowActionLog.objects.filter(instance=instance, action="terminate").exists())

    def test_can_start_new_instance_after_terminated_instance(self):
        defect = self.create_defect(title="Restart after terminate")
        first_instance = start_workflow("defect", defect.id, self.owner)

        terminate_workflow_instance(first_instance.id, self.workflow_admin, comment="stop first run")
        second_instance = start_workflow("defect", defect.id, self.owner)

        self.assertNotEqual(first_instance.id, second_instance.id)
        self.assertEqual(first_instance.business_key, second_instance.business_key)
        self.assertEqual(first_instance.run_number, 1)
        self.assertEqual(second_instance.run_number, 2)
        self.assertEqual(second_instance.status, "running")
        self.assertEqual(get_open_task_for_instance(second_instance).step_key, "triage")

    def test_restore_workflow_definition_version_republishes_historical_config(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        v2 = publish_workflow_definition_version(
            definition.id,
            {
                "name": "Defect Lifecycle V2",
                "config": {
                    "steps": [
                        {
                            "key": "triage",
                            "name": "Defect Review",
                            "candidate_roles": ["owner", "admin"],
                            "actions": [{"key": "approve", "label": "Accept", "next": "fixing"}],
                        },
                        {
                            "key": "fixing",
                            "name": "Development Fix",
                            "candidate_roles": ["developer"],
                            "actions": [{"key": "resolve", "label": "Resolve", "complete": True}],
                        },
                    ],
                },
            },
            self.workflow_admin,
        )

        restored = restore_workflow_definition_version(definition.id, self.workflow_admin)

        definition.refresh_from_db()
        v2.refresh_from_db()
        self.assertFalse(definition.is_active)
        self.assertFalse(v2.is_active)
        self.assertTrue(restored.is_active)
        self.assertEqual(restored.version, 3)
        self.assertEqual(restored.name, definition.name)
        self.assertEqual(restored.config, definition.config)

        defect = self.create_defect(title="Uses restored definition")
        instance = start_workflow("defect", defect.id, self.owner)
        self.assertEqual(instance.definition_id, restored.id)
        self.assertEqual(instance.current_step_name, definition.config["steps"][0]["name"])

    def test_simulate_workflow_definition_returns_effective_rule_outputs(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)

        preview = simulate_workflow_definition(definition.id, inputs={"severity": "critical"})

        self.assertEqual(preview["definition"]["id"], definition.id)
        self.assertEqual(preview["first_step_key"], "triage")
        self.assertEqual(preview["active_step_count"], 3)
        self.assertEqual(preview["start_rules"], [])
        triage_step = next(item for item in preview["steps"] if item["key"] == "triage")
        self.assertEqual(triage_step["sla_hours"], 4)
        self.assertEqual(triage_step["remind_after_hours"], 2)
        self.assertEqual(triage_step["escalation_after_hours"], 6)
        self.assertEqual(triage_step["matched_rules"][0]["name"], "Critical Defect Triage SLA")
        self.assertEqual(triage_step["candidate_roles"], ["owner", "admin"])


class WorkflowApiTests(WorkflowTestBase):
    def test_direct_defect_status_update_is_blocked_when_workflow_is_running(self):
        defect = self.create_defect()
        start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/defects/{defect.id}/status/", {"status": "closed"}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Workflow is running", response.data["detail"])

    def test_my_tasks_api_returns_workbench_summary_fields(self):
        defect = self.create_defect()
        start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/workflow/tasks/my/")

        self.assertEqual(response.status_code, 200)
        payload = response.data["results"][0]
        self.assertEqual(payload["biz_type"], "defect")
        self.assertEqual(payload["biz_id"], defect.id)
        self.assertEqual(payload["biz_code"], defect.code)
        self.assertEqual(payload["biz_title"], defect.title)
        self.assertEqual(payload["instance_status"], "running")
        self.assertEqual(payload["business_key"], f"defect:{defect.id}")
        self.assertEqual(payload["summary"]["step_key"], "triage")
        self.assertTrue(payload["summary"]["can_act"])

    def test_workflow_start_requires_project_access(self):
        defect = self.create_defect()

        self.client.force_authenticate(self.outsider)
        response = self.client.post(f"/api/workflow/defect/{defect.id}/start/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("access", response.data["detail"].lower())

    def test_workflow_instance_list_only_returns_accessible_instances(self):
        own_defect = self.create_defect(title="Own defect")
        start_workflow("defect", own_defect.id, self.owner)

        other_owner = User.objects.create_user(username="other_owner", password="pass123")
        other_project = Project.objects.create(name="Other Project", owner=other_owner)
        other_defect = Defect.objects.create(
            project=other_project,
            title="Other defect",
            description="Other detail",
            severity="medium",
            created_by=other_owner,
        )
        start_workflow("defect", other_defect.id, other_owner)

        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/workflow/instances/")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["biz_id"] for item in response.data["results"]}
        self.assertIn(own_defect.id, returned_ids)
        self.assertNotIn(other_defect.id, returned_ids)

    def test_workflow_instance_detail_requires_project_access(self):
        defect = self.create_defect()
        start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.outsider)
        response = self.client.get(f"/api/workflow/defect/{defect.id}/instance/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("access", response.data["detail"].lower())

    def test_staff_user_can_monitor_all_instances(self):
        defect = self.create_defect(title="Admin monitor target")
        instance = start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.get("/api/workflow/instances/")

        self.assertEqual(response.status_code, 200)
        matched = next(item for item in response.data["results"] if item["id"] == instance.id)
        self.assertEqual(matched["status"], "running")

    def test_instance_list_returns_row_specific_workflow_summary_when_multiple_runs_exist(self):
        defect = self.create_defect(title="Instance row summary target")
        first_instance = start_workflow("defect", defect.id, self.owner)
        terminate_workflow_instance(first_instance.id, self.workflow_admin, comment="first run stopped")
        second_instance = start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.get("/api/workflow/instances/", {"biz_type": "defect"})

        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        first_row = next(item for item in results if item["id"] == first_instance.id)
        second_row = next(item for item in results if item["id"] == second_instance.id)
        self.assertEqual(first_row["run_number"], 1)
        self.assertEqual(first_row["workflow"]["instance_id"], first_instance.id)
        self.assertEqual(first_row["workflow"]["status"], "terminated")
        self.assertIsNone(first_row["workflow"]["current_task"])
        self.assertEqual(second_row["run_number"], 2)
        self.assertEqual(second_row["workflow"]["instance_id"], second_instance.id)
        self.assertEqual(second_row["workflow"]["status"], "running")
        self.assertEqual(second_row["workflow"]["current_task"]["step_key"], "triage")

    def test_terminate_instance_requires_staff_user(self):
        defect = self.create_defect(title="Terminate permission target")
        instance = start_workflow("defect", defect.id, self.owner)

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/workflow/instances/{instance.id}/terminate/",
            {"comment": "no permission"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_terminate_running_instance(self):
        defect = self.create_defect(title="Terminate api target")
        instance = start_workflow("defect", defect.id, self.owner)
        task = get_open_task_for_instance(instance)

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post(
            f"/api/workflow/instances/{instance.id}/terminate/",
            {"comment": "manual stop"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "terminated")
        self.assertIsNone(response.data["current_task"])
        self.assertEqual(response.data["metadata"]["termination_comment"], "manual stop")

        instance.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(instance.status, "terminated")
        self.assertEqual(task.status, "cancelled")

    def test_terminate_instance_rejects_non_running_instance(self):
        defect = self.create_defect(title="Terminate completed target")
        instance = start_workflow("defect", defect.id, self.owner)
        triage_task = get_open_task_for_instance(instance)
        execute_task_action(triage_task.id, "reject", self.owner, comment="done")

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post(
            f"/api/workflow/instances/{instance.id}/terminate/",
            {"comment": "should fail"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not running", response.data["detail"].lower())

    def test_workflow_start_api_creates_new_instance_after_termination(self):
        defect = self.create_defect(title="Start api second run target")
        first_instance = start_workflow("defect", defect.id, self.owner)
        terminate_workflow_instance(first_instance.id, self.workflow_admin, comment="first run done")

        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/workflow/defect/{defect.id}/start/")

        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.data["instance_id"], first_instance.id)
        self.assertEqual(response.data["workflow"]["run_number"], 2)
        self.assertEqual(response.data["workflow"]["status"], "running")

    def test_workflow_rule_write_requires_staff_user(self):
        payload = {
            "biz_type": "defect",
            "scene_key": "default",
            "step_key": "triage",
            "name": "Custom Rule",
            "priority": 5,
            "conditions": {"severity": ["critical"]},
            "outputs": {"sla_hours": 2},
            "is_active": True,
        }

        self.client.force_authenticate(self.owner)
        forbidden_response = self.client.post("/api/workflow/rules/", payload, format="json")
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_authenticate(self.workflow_admin)
        created_response = self.client.post("/api/workflow/rules/", payload, format="json")
        self.assertEqual(created_response.status_code, 201)
        self.assertTrue(WorkflowRule.objects.filter(name="Custom Rule").exists())

    def test_workflow_definition_update_requires_staff_user(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        payload = {
            "name": "Updated without permission",
            "config": definition.config,
        }

        self.client.force_authenticate(self.owner)
        response = self.client.put(f"/api/workflow/definitions/{definition.id}/", payload, format="json")

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_publish_new_workflow_definition_version(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        updated_config = {
            "steps": [
                {
                    "key": "triage",
                    "name": "Defect Review",
                    "candidate_roles": ["owner", "admin"],
                    "sla_hours": 12,
                    "business_status": "new",
                    "actions": [
                        {"key": "approve", "label": "Accept", "next": "fixing", "business_status": "in_progress"},
                        {"key": "reject", "label": "Reject", "complete": True, "business_status": "rejected"},
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
            ]
        }
        payload = {
            "name": "Defect Lifecycle V2",
            "config": updated_config,
        }

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.put(f"/api/workflow/definitions/{definition.id}/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        definition.refresh_from_db()
        self.assertFalse(definition.is_active)

        new_definition = WorkflowDefinition.objects.get(id=response.data["id"])
        self.assertNotEqual(new_definition.id, definition.id)
        self.assertTrue(new_definition.is_active)
        self.assertEqual(new_definition.version, definition.version + 1)
        self.assertEqual(new_definition.name, "Defect Lifecycle V2")
        self.assertEqual(new_definition.config["steps"][0]["name"], "Defect Review")

        defect = self.create_defect(title="Uses latest definition")
        instance = start_workflow("defect", defect.id, self.owner)
        self.assertEqual(instance.definition_id, new_definition.id)
        self.assertEqual(instance.current_step_name, "Defect Review")

    def test_workflow_definition_versions_endpoint_returns_history_and_change_summary(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        publish_workflow_definition_version(
            definition.id,
            {
                "name": "Defect Lifecycle V2",
                "config": {
                    "steps": [
                        {
                            "key": "triage",
                            "name": "Defect Review",
                            "candidate_roles": ["owner", "admin"],
                            "actions": [
                                {"key": "approve", "label": "Accept", "next": "fixing"},
                                {"key": "reject", "label": "Reject", "complete": True},
                            ],
                        },
                        {
                            "key": "fixing",
                            "name": "Development Fix",
                            "candidate_roles": ["developer"],
                            "actions": [{"key": "resolve", "label": "Resolve", "complete": True}],
                        },
                    ],
                },
            },
            self.workflow_admin,
        )
        active_definition = WorkflowDefinition.objects.get(is_active=True, biz_type="defect")

        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/workflow/definitions/{active_definition.id}/versions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["version"] for item in response.data["results"]], [2, 1])
        latest_entry = response.data["results"][0]
        self.assertEqual(latest_entry["name"], "Defect Lifecycle V2")
        self.assertEqual(latest_entry["step_count"], 2)
        self.assertEqual(latest_entry["action_count"], 3)
        self.assertEqual(latest_entry["change_summary"]["step_delta"], -1)
        self.assertIn("regression", latest_entry["change_summary"]["removed_steps"])

    def test_restore_workflow_definition_requires_staff_user(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        publish_workflow_definition_version(
            definition.id,
            {"name": "Defect Lifecycle V2", "config": definition.config},
            self.workflow_admin,
        )

        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/workflow/definitions/{definition.id}/restore/", {}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_restore_historical_workflow_definition_version(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)
        publish_workflow_definition_version(
            definition.id,
            {
                "name": "Defect Lifecycle V2",
                "config": {
                    "steps": [
                        {
                            "key": "triage",
                            "name": "Defect Review",
                            "candidate_roles": ["owner", "admin"],
                            "actions": [{"key": "approve", "label": "Accept", "complete": True}],
                        },
                    ],
                },
            },
            self.workflow_admin,
        )

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post(f"/api/workflow/definitions/{definition.id}/restore/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        latest_definition = WorkflowDefinition.objects.get(id=response.data["id"])
        self.assertTrue(latest_definition.is_active)
        self.assertEqual(latest_definition.version, 3)
        self.assertEqual(latest_definition.name, definition.name)
        self.assertEqual(latest_definition.config, definition.config)

    def test_definition_simulation_requires_staff_user(self):
        definition = ensure_rules_and_definition("defect", operator=self.workflow_admin)

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/workflow/definitions/simulate/",
            {"definition_id": definition.id, "inputs": {"severity": "critical"}},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_simulate_requirement_workflow_definition(self):
        definition = ensure_rules_and_definition("requirement", operator=self.workflow_admin)

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post(
            "/api/workflow/definitions/simulate/",
            {"definition_id": definition.id, "inputs": {"requirement_level": "low"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["definition"]["id"], definition.id)
        self.assertEqual(response.data["first_step_key"], "product_review")
        self.assertEqual(response.data["active_step_count"], 2)
        self.assertEqual(response.data["skipped_step_count"], 2)
        self.assertEqual(response.data["start_rules"][0]["name"], "Low Level Requirement Fast Track")
        qa_step = next(item for item in response.data["steps"] if item["key"] == "qa_review")
        self.assertFalse(qa_step["enabled"])
        self.assertIn("need_qa_review", qa_step["skip_reason"])

    def test_staff_user_can_update_and_delete_workflow_rule(self):
        rule = WorkflowRule.objects.create(
            biz_type="defect",
            scene_key="default",
            step_key="triage",
            name="Editable Rule",
            priority=5,
            conditions={"severity": ["high"]},
            outputs={"sla_hours": 3},
            is_active=True,
            created_by=self.workflow_admin,
        )

        payload = {
            "biz_type": "defect",
            "scene_key": "default",
            "step_key": "triage",
            "name": "Editable Rule Updated",
            "priority": 15,
            "conditions": {"severity": ["critical"]},
            "outputs": {"sla_hours": 1, "remind_after_hours": 1},
            "is_active": False,
        }

        self.client.force_authenticate(self.workflow_admin)
        update_response = self.client.put(f"/api/workflow/rules/{rule.id}/", payload, format="json")

        self.assertEqual(update_response.status_code, 200)
        rule.refresh_from_db()
        self.assertEqual(rule.name, "Editable Rule Updated")
        self.assertEqual(rule.priority, 15)
        self.assertEqual(rule.outputs["remind_after_hours"], 1)
        self.assertFalse(rule.is_active)

        delete_response = self.client.delete(f"/api/workflow/rules/{rule.id}/")
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(WorkflowRule.objects.filter(id=rule.id).exists())

    def test_staff_user_can_bootstrap_default_workflow_catalog(self):
        self.assertEqual(WorkflowDefinition.objects.count(), 0)
        self.assertEqual(WorkflowRule.objects.count(), 0)

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post("/api/workflow/bootstrap/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WorkflowDefinition.objects.filter(is_active=True).count(), 2)
        self.assertGreater(WorkflowRule.objects.filter(is_active=True).count(), 0)
        self.assertSetEqual(
            {item["biz_type"] for item in response.data["definitions"]},
            {"defect", "requirement"},
        )

    def test_task_action_api_requires_task_permission(self):
        defect = self.create_defect()
        instance = start_workflow("defect", defect.id, self.owner)
        triage_task = get_open_task_for_instance(instance)

        self.client.force_authenticate(self.outsider)
        response = self.client.post(
            f"/api/workflow/tasks/{triage_task.id}/action/",
            {"action": "approve", "comment": "unauthorized"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("cannot act", response.data["detail"].lower())

    def test_task_action_api_rejects_unsupported_action(self):
        defect = self.create_defect()
        instance = start_workflow("defect", defect.id, self.owner)
        triage_task = get_open_task_for_instance(instance)

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/workflow/tasks/{triage_task.id}/action/",
            {"action": "ship_it"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("unsupported", response.data["detail"].lower())

    def test_run_escalations_requires_staff_user(self):
        self.client.force_authenticate(self.owner)
        forbidden_response = self.client.post("/api/workflow/run-escalations/")
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_authenticate(self.workflow_admin)
        allowed_response = self.client.post("/api/workflow/run-escalations/")
        self.assertEqual(allowed_response.status_code, 200)

    def test_run_escalations_returns_trigger_counts_for_overdue_task(self):
        defect = self.create_defect(severity="critical")
        instance = start_workflow("defect", defect.id, self.owner)
        task = get_open_task_for_instance(instance)
        now = timezone.now()
        task.remind_at = now - timedelta(minutes=5)
        task.escalation_due_at = now - timedelta(minutes=1)
        task.save(update_fields=["remind_at", "escalation_due_at"])

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.post("/api/workflow/run-escalations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"reminders": 1, "escalations": 1})
        task.refresh_from_db()
        self.assertIsNotNone(task.reminded_at)
        self.assertIsNotNone(task.escalated_at)
        self.assertEqual(
            WorkflowActionLog.objects.filter(instance=instance, action__in=["remind", "escalate"]).count(),
            2,
        )

    def test_my_tasks_api_surfaces_claim_and_transfer_state(self):
        ProjectMember.objects.create(project=self.project, user=self.workflow_admin, role="admin")
        requirement = self.create_requirement(requirement_id="REQ-TASK-STATE", requirement_level="high")
        instance = start_workflow("requirement", requirement.id, self.owner)
        product_task = get_open_task_for_instance(instance)
        execute_task_action(product_task.id, "approve", self.owner, comment="product ok")

        self.client.force_authenticate(self.workflow_admin)
        response = self.client.get("/api/workflow/tasks/my/", {"biz_type": "requirement"})

        self.assertEqual(response.status_code, 200)
        summary = response.data["results"][0]["summary"]
        self.assertTrue(summary["can_claim"])
        self.assertFalse(summary["can_transfer"])
        self.assertEqual(len(summary["transfer_candidates"]), 2)

        tech_task = get_open_task_for_instance(instance)
        claim_response = self.client.post(
            f"/api/workflow/tasks/{tech_task.id}/action/",
            {"action": "claim", "comment": "take ownership"},
            format="json",
        )

        self.assertEqual(claim_response.status_code, 200)
        summary = claim_response.data["current_task"]
        self.assertFalse(summary["can_claim"])
        self.assertTrue(summary["can_transfer"])
        self.assertEqual(summary["assignee"]["id"], self.workflow_admin.id)
