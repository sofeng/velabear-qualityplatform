from rest_framework import serializers

from apps.users.serializers import UserSimpleSerializer

from .models import WorkflowDefinition, WorkflowInstance, WorkflowRule, WorkflowTask
from .services import serialize_task_summary, serialize_workflow_instance


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    def validate_config(self, value):
        config = value or {}
        steps = config.get("steps") if isinstance(config, dict) else None
        if not isinstance(steps, list) or not steps:
            raise serializers.ValidationError("Workflow config must contain at least one step")

        step_keys = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise serializers.ValidationError(f"Step {index} must be an object")
            step_key = str(step.get("key") or "").strip()
            step_name = str(step.get("name") or "").strip()
            if not step_key:
                raise serializers.ValidationError(f"Step {index} key is required")
            if not step_name:
                raise serializers.ValidationError(f"Step {index} name is required")
            if step_key in step_keys:
                raise serializers.ValidationError(f"Duplicate step key: {step_key}")
            step_keys.append(step_key)

            candidate_roles = step.get("candidate_roles")
            if candidate_roles is not None and (
                not isinstance(candidate_roles, list) or any(not str(item).strip() for item in candidate_roles)
            ):
                raise serializers.ValidationError(f"Step {step_key} candidate_roles must be a string list")

            actions = step.get("actions")
            if not isinstance(actions, list) or not actions:
                raise serializers.ValidationError(f"Step {step_key} must contain at least one action")

            action_keys = set()
            for action_index, action in enumerate(actions, start=1):
                if not isinstance(action, dict):
                    raise serializers.ValidationError(f"Step {step_key} action {action_index} must be an object")
                action_key = str(action.get("key") or "").strip()
                if not action_key:
                    raise serializers.ValidationError(f"Step {step_key} action {action_index} key is required")
                if action_key in action_keys:
                    raise serializers.ValidationError(f"Duplicate action key in step {step_key}: {action_key}")
                action_keys.add(action_key)

        valid_step_keys = set(step_keys)
        for step in steps:
            for action in step.get("actions") or []:
                next_step = str(action.get("next") or "").strip()
                if next_step and next_step not in valid_step_keys:
                    raise serializers.ValidationError(
                        f"Action {action.get('key')} in step {step.get('key')} points to unknown step {next_step}"
                    )
        return config

    class Meta:
        model = WorkflowDefinition
        fields = [
            "id",
            "biz_type",
            "key",
            "scene_key",
            "name",
            "version",
            "config",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["biz_type", "key", "scene_key", "version", "is_active", "created_at", "updated_at"]


class WorkflowRuleSerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = WorkflowRule
        fields = [
            "id",
            "biz_type",
            "scene_key",
            "step_key",
            "name",
            "priority",
            "conditions",
            "outputs",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]


class WorkflowTaskActionSerializer(serializers.Serializer):
    action = serializers.CharField()
    comment = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)


class WorkflowDefinitionSimulationSerializer(serializers.Serializer):
    definition_id = serializers.IntegerField()
    inputs = serializers.JSONField(required=False)


class WorkflowInstanceTerminateSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class WorkflowTaskListSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    biz_type = serializers.CharField(source="instance.biz_type", read_only=True)
    biz_id = serializers.IntegerField(source="instance.biz_id", read_only=True)
    biz_code = serializers.CharField(source="instance.biz_code", read_only=True)
    biz_title = serializers.CharField(source="instance.biz_title", read_only=True)
    business_key = serializers.CharField(source="instance.business_key", read_only=True)
    instance_status = serializers.CharField(source="instance.status", read_only=True)

    class Meta:
        model = WorkflowTask
        fields = [
            "id",
            "biz_type",
            "biz_id",
            "biz_code",
            "biz_title",
            "business_key",
            "instance_status",
            "summary",
        ]

    def get_summary(self, obj):
        return serialize_task_summary(obj, user=self.context["request"].user)


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "biz_type",
            "biz_id",
            "biz_code",
            "biz_title",
            "business_key",
            "run_number",
            "status",
            "current_step_key",
            "current_step_name",
            "started_at",
            "completed_at",
            "workflow",
        ]

    def get_workflow(self, obj):
        return serialize_workflow_instance(obj, user=self.context["request"].user)
