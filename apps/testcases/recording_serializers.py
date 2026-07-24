from django.conf import settings
from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import (
    PlaywrightAutomationScript,
    PlaywrightAutomationScriptVersion,
    PlaywrightRecordingSession,
    PlaywrightRecordingStep,
    VisualFlow,
    VisualFlowExecution,
    VisualFlowExecutionStep,
)


class PlaywrightRecordingStepSerializer(serializers.ModelSerializer):
    screenshot_url = serializers.SerializerMethodField()
    resolved_snapshot_filename = serializers.SerializerMethodField()

    class Meta:
        model = PlaywrightRecordingStep
        fields = [
            'id',
            'step_number',
            'action_type',
            'action_value',
            'page_url',
            'page_title',
            'element',
            'selectors',
            'snapshot_filename',
            'resolved_snapshot_filename',
            'screenshot_path',
            'screenshot_url',
            'raw_event',
            'created_at',
        ]
        read_only_fields = fields

    def get_resolved_snapshot_filename(self, obj):
        if obj.snapshot_filename:
            return obj.snapshot_filename
        session_id = getattr(getattr(obj, 'session', None), 'session_id', '')
        if session_id and obj.step_number:
            return f'recording-{session_id}-step-{obj.step_number:04d}.yml'
        return ''

    def get_screenshot_url(self, obj):
        if not obj.screenshot_path:
            return ''

        request = self.context.get('request')
        if obj.screenshot_path.startswith(('http://', 'https://', '/')):
            path = obj.screenshot_path
        else:
            path = f'/media/{obj.screenshot_path.lstrip("/")}'

        if request is not None:
            return request.build_absolute_uri(path)
        return path


class PlaywrightRecordingSessionSerializer(serializers.ModelSerializer):
    started_by = UserSerializer(read_only=True)
    started_by_name = serializers.SerializerMethodField()
    recording_method_label = serializers.SerializerMethodField()
    visual_flow_id = serializers.SerializerMethodField()
    visual_flow_name = serializers.SerializerMethodField()
    has_visual_flow = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()
    module_id = serializers.SerializerMethodField()
    module_name = serializers.SerializerMethodField()
    module_path = serializers.SerializerMethodField()
    version_id = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    steps_count = serializers.SerializerMethodField()
    latest_step = serializers.SerializerMethodField()
    steps = PlaywrightRecordingStepSerializer(many=True, read_only=True)

    class Meta:
        model = PlaywrightRecordingSession
        fields = [
            'id',
            'session_id',
            'name',
            'target_url',
            'browser_type',
            'recording_method',
            'recording_method_label',
            'status',
            'visual_flow_id',
            'visual_flow_name',
            'has_visual_flow',
            'started_by',
            'started_by_name',
            'project_id',
            'version_id',
            'version_name',
            'module_id',
            'module_name',
            'module_path',
            'module',
            'started_at',
            'stopped_at',
            'error_message',
            'metadata',
            'steps_count',
            'latest_step',
            'steps',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_fields(self):
        fields = super().get_fields()
        if not self.context.get('include_steps', True):
            fields.pop('steps', None)
        if not self.context.get('include_latest_step', True):
            fields.pop('latest_step', None)
        return fields

    def get_steps_count(self, obj):
        annotated_count = getattr(obj, 'steps_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.steps.count()

    def get_started_by_name(self, obj):
        user = getattr(obj, 'started_by', None)
        if not user:
            return ''
        return getattr(user, 'full_name', None) or getattr(user, 'username', '') or ''

    def get_recording_method_label(self, obj):
        return obj.get_recording_method_display() or obj.recording_method or ''

    def _get_latest_visual_flow(self, obj):
        flows = getattr(obj, 'prefetched_visual_flows', None)
        if flows is not None:
            return flows[0] if flows else None
        return obj.visual_flows.order_by('-updated_at', '-id').first()

    def get_visual_flow_id(self, obj):
        flow = self._get_latest_visual_flow(obj)
        return flow.flow_id if flow else ''

    def get_visual_flow_name(self, obj):
        flow = self._get_latest_visual_flow(obj)
        return flow.name if flow else ''

    def get_has_visual_flow(self, obj):
        return bool(self.get_visual_flow_id(obj))

    def _get_module_metadata(self, obj):
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
        return {
            'project_id': module.get('project_id') or metadata.get('project_id') or '',
            'version_id': module.get('version_id') or metadata.get('version_id') or '',
            'version_name': module.get('version_name') or metadata.get('version_name') or '',
            'module_id': module.get('module_id') or metadata.get('module_id') or '',
            'module_name': module.get('module_name') or metadata.get('module_name') or '',
            'module_path': module.get('module_path') or metadata.get('module_path') or '',
        }

    def get_project_id(self, obj):
        return self._get_module_metadata(obj).get('project_id') or ''

    def get_version_id(self, obj):
        return self._get_module_metadata(obj).get('version_id') or ''

    def get_version_name(self, obj):
        return self._get_module_metadata(obj).get('version_name') or ''

    def get_module_id(self, obj):
        return self._get_module_metadata(obj).get('module_id') or ''

    def get_module_name(self, obj):
        return self._get_module_metadata(obj).get('module_name') or ''

    def get_module_path(self, obj):
        return self._get_module_metadata(obj).get('module_path') or ''

    def get_module(self, obj):
        module = self._get_module_metadata(obj)
        if not any(module.values()):
            return None
        return module

    def get_latest_step(self, obj):
        latest_step = getattr(obj, 'latest_step_obj', None)
        if latest_step is None:
            latest_step = obj.steps.order_by('-step_number').first()
        if latest_step is None:
            return None
        return PlaywrightRecordingStepSerializer(latest_step, context=self.context).data


class PlaywrightAutomationScriptVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    parent_script_id = serializers.SerializerMethodField()

    class Meta:
        model = PlaywrightAutomationScriptVersion
        fields = [
            'id',
            'parent_script_id',
            'version',
            'name',
            'target_url',
            'instruction',
            'script_content',
            'summary',
            'warnings',
            'planned_actions',
            'generation_source',
            'fallback_reason',
            'module',
            'model',
            'capability',
            'metadata',
            'change_summary',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        user = getattr(obj, 'created_by', None)
        if not user:
            return ''
        return getattr(user, 'full_name', None) or getattr(user, 'username', '') or ''

    def get_parent_script_id(self, obj):
        parent = getattr(obj, 'script', None)
        return parent.script_id if parent else ''


class PlaywrightAutomationScriptSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()
    version_id = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    versions_count = serializers.SerializerMethodField()
    latest_version_record = serializers.SerializerMethodField()

    class Meta:
        model = PlaywrightAutomationScript
        fields = [
            'id',
            'script_id',
            'name',
            'description',
            'target_url',
            'instruction',
            'script',
            'summary',
            'warnings',
            'planned_actions',
            'generation_source',
            'fallback_reason',
            'module',
            'model',
            'capability',
            'metadata',
            'latest_version',
            'project_id',
            'version_id',
            'version_name',
            'module_id',
            'module_name',
            'module_path',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
            'versions_count',
            'latest_version_record',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        user = getattr(obj, 'created_by', None)
        if not user:
            return ''
        return getattr(user, 'full_name', None) or getattr(user, 'username', '') or ''

    def get_updated_by_name(self, obj):
        user = getattr(obj, 'updated_by', None)
        if not user:
            return ''
        return getattr(user, 'full_name', None) or getattr(user, 'username', '') or ''

    def get_project_id(self, obj):
        if obj.project_id:
            return obj.project_id
        module = obj.module if isinstance(obj.module, dict) else {}
        return module.get('project_id') or ''

    def get_version_id(self, obj):
        if obj.version_id:
            return obj.version_id
        module = obj.module if isinstance(obj.module, dict) else {}
        return module.get('version_id') or ''

    def get_version_name(self, obj):
        if obj.version_id and obj.version:
            return obj.version.name
        module = obj.module if isinstance(obj.module, dict) else {}
        return module.get('version_name') or ''

    def get_versions_count(self, obj):
        annotated_count = getattr(obj, 'versions_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.versions.count()

    def get_latest_version_record(self, obj):
        if not self.context.get('include_latest_version', False):
            return None
        latest = getattr(obj, 'latest_version_obj', None)
        if isinstance(latest, list):
            latest = latest[0] if latest else None
        if latest is None:
            latest = obj.versions.order_by('-version', '-id').first()
        if latest is None:
            return None
        return PlaywrightAutomationScriptVersionSerializer(latest, context=self.context).data


class VisualFlowSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    recording_session_id = serializers.SerializerMethodField()
    recording_session_name = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()
    version_id = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    module_id = serializers.SerializerMethodField()
    module_name = serializers.SerializerMethodField()
    module_path = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    graph_cell_count = serializers.SerializerMethodField()

    class Meta:
        model = VisualFlow
        fields = [
            'id',
            'flow_id',
            'name',
            'description',
            'source',
            'status',
            'target_url',
            'browser_type',
            'recording_session_id',
            'recording_session_name',
            'project_id',
            'version_id',
            'version_name',
            'module_id',
            'module_name',
            'module_path',
            'module',
            'graph_data',
            'snapshot_summary',
            'metadata',
            'created_by',
            'created_at',
            'updated_at',
            'graph_cell_count',
        ]
        read_only_fields = [
            'id',
            'flow_id',
            'recording_session_id',
            'recording_session_name',
            'project_id',
            'version_id',
            'version_name',
            'module_id',
            'module_name',
            'module_path',
            'module',
            'created_by',
            'created_at',
            'updated_at',
            'graph_cell_count',
        ]

    def get_fields(self):
        fields = super().get_fields()
        if not self.context.get('include_graph', True):
            fields.pop('graph_data', None)
        return fields

    def get_recording_session_id(self, obj):
        return obj.recording_session.session_id if obj.recording_session_id and obj.recording_session else ''

    def get_recording_session_name(self, obj):
        return obj.recording_session.name if obj.recording_session_id and obj.recording_session else ''

    def _get_module_metadata(self, obj):
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
        if not module and getattr(obj, 'recording_session', None):
            recording_metadata = obj.recording_session.metadata if isinstance(obj.recording_session.metadata, dict) else {}
            module = recording_metadata.get('module') if isinstance(recording_metadata.get('module'), dict) else {}
        return {
            'project_id': module.get('project_id') or metadata.get('project_id') or '',
            'version_id': module.get('version_id') or metadata.get('version_id') or '',
            'version_name': module.get('version_name') or metadata.get('version_name') or '',
            'module_id': module.get('module_id') or metadata.get('module_id') or '',
            'module_name': module.get('module_name') or metadata.get('module_name') or '',
            'module_path': module.get('module_path') or metadata.get('module_path') or '',
        }

    def get_project_id(self, obj):
        return self._get_module_metadata(obj).get('project_id') or ''

    def get_version_id(self, obj):
        return self._get_module_metadata(obj).get('version_id') or ''

    def get_version_name(self, obj):
        return self._get_module_metadata(obj).get('version_name') or ''

    def get_module_id(self, obj):
        return self._get_module_metadata(obj).get('module_id') or ''

    def get_module_name(self, obj):
        return self._get_module_metadata(obj).get('module_name') or ''

    def get_module_path(self, obj):
        return self._get_module_metadata(obj).get('module_path') or ''

    def get_module(self, obj):
        module = self._get_module_metadata(obj)
        if not any(module.values()):
            return None
        return module

    def get_graph_cell_count(self, obj):
        graph_data = obj.graph_data if isinstance(obj.graph_data, dict) else {}
        cells = graph_data.get('cells')
        return len(cells) if isinstance(cells, list) else 0


class VisualFlowExecutionStepSerializer(serializers.ModelSerializer):
    screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = VisualFlowExecutionStep
        fields = [
            'id',
            'step_key',
            'step_order',
            'item_type',
            'node_id',
            'component_id',
            'title',
            'status',
            'input_data',
            'output_data',
            'error_log',
            'screenshot_path',
            'screenshot_url',
            'started_at',
            'finished_at',
            'duration',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_screenshot_url(self, obj):
        if not obj.screenshot_path:
            return ''
        url = f"{settings.MEDIA_URL.rstrip('/')}/{str(obj.screenshot_path).lstrip('/')}"
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class VisualFlowExecutionSerializer(serializers.ModelSerializer):
    steps = VisualFlowExecutionStepSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    step_count = serializers.SerializerMethodField()
    success_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()

    class Meta:
        model = VisualFlowExecution
        fields = [
            'id',
            'execution_id',
            'flow_id_text',
            'flow_name',
            'run_type',
            'status',
            'summary',
            'stdout',
            'stderr',
            'error_message',
            'returncode',
            'started_at',
            'finished_at',
            'duration',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'step_count',
            'success_count',
            'failed_count',
            'steps',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by_id and obj.created_by else ''

    def _steps(self, obj):
        return getattr(obj, 'prefetched_steps', None)

    def get_step_count(self, obj):
        prefetched_steps = self._steps(obj)
        if prefetched_steps is not None:
            return len(prefetched_steps)
        return obj.steps.count()

    def _count_steps_by_status(self, obj, target_status):
        prefetched_steps = self._steps(obj)
        if prefetched_steps is not None:
            return len([step for step in prefetched_steps if step.status == target_status])
        return obj.steps.filter(status=target_status).count()

    def get_success_count(self, obj):
        return self._count_steps_by_status(obj, VisualFlowExecutionStep.STATUS_SUCCESS)

    def get_failed_count(self, obj):
        return self._count_steps_by_status(obj, VisualFlowExecutionStep.STATUS_FAILED)
