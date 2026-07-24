from rest_framework import serializers

from apps.workflow.services import get_workflow_summary

from .models import (
    AIModelConfig,
    AnalysisTask,
    BusinessRequirement,
    GeneratedTestCase,
    PromptConfig,
    RequirementAnalysis,
    RequirementDocument,
    TestCaseGenerationTask,
)



def _get_default_user(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return user

    from apps.users.models import User

    default_user = User.objects.filter(is_superuser=True).first()
    return default_user or User.objects.first()


class RequirementDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    relationship_summary = serializers.SerializerMethodField()

    class Meta:
        model = RequirementDocument
        fields = [
            'id',
            'title',
            'file',
            'file_url',
            'document_type',
            'document_type_display',
            'status',
            'status_display',
            'uploaded_by',
            'uploaded_by_name',
            'project',
            'project_name',
            'created_at',
            'updated_at',
            'file_size',
            'extracted_text',
            'relationship_summary',
        ]
        read_only_fields = ['uploaded_by', 'file_size', 'extracted_text']

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_relationship_summary(self, obj):
        try:
            analysis = obj.analysis
        except RequirementAnalysis.DoesNotExist:
            analysis = None
        requirement_count = 0
        generated_case_count = 0
        generation_task_count = 0

        if analysis:
            requirements = list(analysis.requirements.all())
            requirement_count = len(requirements)
            requirement_ids = [item.requirement_id for item in requirements if item.requirement_id]
            generated_case_count = GeneratedTestCase.objects.filter(requirement__in=requirements).count()
            if requirement_ids:
                query = None
                from django.db.models import Q
                for requirement_id in requirement_ids:
                    condition = Q(requirement_text__icontains=requirement_id)
                    query = condition if query is None else query | condition
                generation_task_count = TestCaseGenerationTask.objects.filter(query).count() if query is not None else 0

        return {
            'analysis_count': 1 if analysis else 0,
            'requirement_count': requirement_count,
            'analysis_task_count': obj.tasks.count() if obj.pk else 0,
            'generated_case_count': generated_case_count,
            'generation_task_count': generation_task_count,
            'has_extracted_text': bool(obj.extracted_text),
        }


class BusinessRequirementSerializer(serializers.ModelSerializer):
    requirement_type_display = serializers.CharField(source='get_requirement_type_display', read_only=True)
    requirement_level_display = serializers.CharField(source='get_requirement_level_display', read_only=True)
    case_generation_status_display = serializers.CharField(source='get_case_generation_status_display', read_only=True)
    audit_status_display = serializers.CharField(source='get_audit_status_display', read_only=True)
    audited_by_name = serializers.CharField(source='audited_by.username', read_only=True)
    parent_requirement_name = serializers.CharField(source='parent_requirement.requirement_name', read_only=True)
    analysis = serializers.PrimaryKeyRelatedField(
        queryset=RequirementAnalysis.objects.all(),
        required=False,
        allow_null=True,
    )
    project = serializers.IntegerField(source='analysis.document.project_id', read_only=True)
    project_name = serializers.CharField(source='analysis.document.project.name', read_only=True)
    task_id = serializers.SerializerMethodField()
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = BusinessRequirement
        fields = [
            'id',
            'analysis',
            'project',
            'project_name',
            'requirement_id',
            'requirement_name',
            'requirement_type',
            'requirement_type_display',
            'parent_requirement',
            'parent_requirement_name',
            'module',
            'requirement_level',
            'requirement_level_display',
            'reviewer',
            'estimated_hours',
            'description',
            'acceptance_criteria',
            'accepted_context',
            'case_generation_status',
            'case_generation_status_display',
            'audit_status',
            'audit_status_display',
            'audited_by',
            'audited_by_name',
            'audited_at',
            'task_id',
            'workflow',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['audit_status', 'audited_by', 'audited_at']

    def get_task_id(self, obj):
        if obj.analysis and obj.analysis.document:
            task = obj.analysis.document.tasks.filter(task_type='requirement_analysis').order_by('-created_at').first()
            if task:
                return task.task_id
        return None

    def get_workflow(self, obj):
        request = self.context.get('request')
        return get_workflow_summary('requirement', obj.id, user=getattr(request, 'user', None))


class RequirementAnalysisSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.IntegerField(source='document.id', read_only=True)
    requirements = BusinessRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = RequirementAnalysis
        fields = [
            'id',
            'document_id',
            'document_title',
            'analysis_report',
            'requirements_count',
            'analysis_time',
            'created_at',
            'updated_at',
            'requirements',
        ]


class GeneratedTestCaseSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requirement_name = serializers.CharField(source='requirement.requirement_name', read_only=True)
    requirement_id_display = serializers.CharField(source='requirement.requirement_id', read_only=True)

    class Meta:
        model = GeneratedTestCase
        fields = [
            'id',
            'case_id',
            'title',
            'priority',
            'priority_display',
            'precondition',
            'test_steps',
            'expected_result',
            'status',
            'status_display',
            'generated_by_ai',
            'reviewed_by_ai',
            'review_comments',
            'requirement',
            'requirement_name',
            'requirement_id_display',
            'created_at',
            'updated_at',
        ]


class AnalysisTaskSerializer(serializers.ModelSerializer):
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisTask
        fields = [
            'id',
            'task_id',
            'task_type',
            'task_type_display',
            'document',
            'document_title',
            'status',
            'status_display',
            'progress',
            'result',
            'error_message',
            'started_at',
            'completed_at',
            'created_at',
            'duration',
        ]
        read_only_fields = ['task_id', 'result', 'error_message', 'started_at', 'completed_at']

    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'project']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['uploaded_by'] = _get_default_user(request)

        file_obj = validated_data['file']
        filename = file_obj.name.lower()
        if filename.endswith('.pdf'):
            validated_data['document_type'] = 'pdf'
        elif filename.endswith(('.doc', '.docx')):
            validated_data['document_type'] = 'docx'
        elif filename.endswith('.xmind'):
            validated_data['document_type'] = 'xmind'
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            validated_data['document_type'] = 'image'
        elif filename.endswith(('.zip', '.tar', '.tar.gz', '.tgz', '.rar')):
            validated_data['document_type'] = 'archive'
        elif filename.endswith(('.xls', '.xlsx')):
            validated_data['document_type'] = 'excel'
        elif filename.endswith(('.ppt', '.pptx')):
            validated_data['document_type'] = 'ppt'
        elif filename.endswith(('.txt', '.md')):
            validated_data['document_type'] = 'txt'
        else:
            validated_data['document_type'] = 'txt'

        validated_data['file_size'] = file_obj.size
        return super().create(validated_data)


class TestCaseGenerationRequestSerializer(serializers.Serializer):
    requirement_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
        help_text='Requirement ids for batch generation.',
    )
    test_level = serializers.ChoiceField(
        choices=[('unit', 'unit'), ('integration', 'integration'), ('system', 'system'), ('acceptance', 'acceptance')],
        required=False,
        default='system',
        help_text='Test level for batch generation.',
    )
    test_priority = serializers.ChoiceField(
        choices=[('P0', 'P0'), ('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3')],
        required=False,
        default='P1',
        help_text='Priority for generated test cases.',
    )
    test_case_count = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=50,
        default=10,
        help_text='Number of test cases per requirement.',
    )
    title = serializers.CharField(required=False, max_length=200, allow_blank=False, help_text='Task title.')
    requirement_text = serializers.CharField(required=False, allow_blank=False, help_text='Requirement content.')
    use_writer_model = serializers.BooleanField(required=False, default=True)
    use_reviewer_model = serializers.BooleanField(required=False, default=True)
    project = serializers.IntegerField(required=False, allow_null=True, help_text='Related project id.')

    def validate(self, attrs):
        if attrs.get('requirement_ids'):
            attrs.setdefault('test_level', 'system')
            attrs.setdefault('test_priority', 'P1')
            attrs.setdefault('test_case_count', 10)
            return attrs

        title = attrs.get('title')
        requirement_text = attrs.get('requirement_text')
        if title and requirement_text:
            attrs.setdefault('use_writer_model', True)
            attrs.setdefault('use_reviewer_model', True)
            return attrs

        raise serializers.ValidationError('Payload must provide requirement_ids or both title and requirement_text.')


class TestCaseReviewRequestSerializer(serializers.Serializer):
    test_case_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Generated test case ids for review.',
    )
    review_criteria = serializers.CharField(
        max_length=500,
        default='Check completeness, correctness, and executability of the generated test cases.',
        help_text='Review criteria.',
    )


class AIModelConfigSerializer(serializers.ModelSerializer):
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AIModelConfig
        fields = [
            'id',
            'name',
            'model_type',
            'model_type_display',
            'role',
            'role_display',
            'api_key',
            'api_key_masked',
            'base_url',
            'model_name',
            'max_tokens',
            'temperature',
            'top_p',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_by_name']
        extra_kwargs = {
            'api_key': {'write_only': True},
        }

    def get_api_key_masked(self, obj):
        if not obj.api_key:
            return ''
        if len(obj.api_key) <= 7:
            return '*' * len(obj.api_key)
        return f"{obj.api_key[:3]}{'*' * (len(obj.api_key) - 7)}{obj.api_key[-4:]}"

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = _get_default_user(request)
        return super().create(validated_data)


class PromptConfigSerializer(serializers.ModelSerializer):
    prompt_type_display = serializers.CharField(source='get_prompt_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PromptConfig
        fields = [
            'id',
            'name',
            'prompt_type',
            'prompt_type_display',
            'content',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_by_name']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = _get_default_user(request)
        return super().create(validated_data)


class TestCaseGenerationTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    writer_model_name = serializers.CharField(source='writer_model_config.name', read_only=True)
    reviewer_model_name = serializers.CharField(source='reviewer_model_config.name', read_only=True)
    writer_prompt_name = serializers.CharField(source='writer_prompt_config.name', read_only=True)
    reviewer_prompt_name = serializers.CharField(source='reviewer_prompt_config.name', read_only=True)

    class Meta:
        model = TestCaseGenerationTask
        fields = [
            'id',
            'task_id',
            'title',
            'requirement_text',
            'status',
            'status_display',
            'progress',
            'output_mode',
            'stream_buffer',
            'stream_position',
            'last_stream_update',
            'project',
            'project_name',
            'writer_model_config',
            'writer_model_name',
            'reviewer_model_config',
            'reviewer_model_name',
            'writer_prompt_config',
            'writer_prompt_name',
            'reviewer_prompt_config',
            'reviewer_prompt_name',
            'generated_test_cases',
            'review_feedback',
            'final_test_cases',
            'generation_log',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'completed_at',
            'is_saved_to_records',
            'saved_at',
        ]
        read_only_fields = [
            'task_id',
            'status',
            'status_display',
            'progress',
            'stream_buffer',
            'stream_position',
            'last_stream_update',
            'generated_test_cases',
            'review_feedback',
            'final_test_cases',
            'generation_log',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'completed_at',
            'is_saved_to_records',
            'saved_at',
        ]

    def create(self, validated_data):
        import uuid

        request = self.context.get('request')
        validated_data['created_by'] = _get_default_user(request)
        validated_data['task_id'] = f"TASK_{uuid.uuid4().hex[:8].upper()}"
        return super().create(validated_data)
