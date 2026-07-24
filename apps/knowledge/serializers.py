from rest_framework import serializers

from apps.knowledge.repository_support import (
    LOCAL_REPOSITORY_ABSOLUTE_PATH_MESSAGE,
    LOCAL_PATH_REPOSITORY_MODE,
    REMOTE_REPOSITORY_MODE,
    is_supported_local_repository_path,
    normalize_local_repository_path,
    normalize_repository_mode,
)
from apps.core.plaintext_secrets import encrypt_password

from .models import (
    KnowledgeFeedback,
    KnowledgeIndexRun,
    KnowledgeObject,
    KnowledgeQueryTrace,
    KnowledgeRelation,
    KnowledgeRepositoryConfig,
    KnowledgeSpace,
)


class KnowledgeSpaceSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    object_count = serializers.IntegerField(read_only=True)
    relation_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeSpace
        fields = [
            'id',
            'key',
            'name',
            'description',
            'space_type',
            'project',
            'project_name',
            'owner',
            'owner_name',
            'metadata',
            'build_status',
            'build_status_message',
            'last_indexed_at',
            'is_active',
            'object_count',
            'relation_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']


class KnowledgeRepositoryConfigSerializer(serializers.ModelSerializer):
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ssh_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    database_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    repository_location = serializers.CharField(read_only=True)
    has_access_token = serializers.SerializerMethodField()
    has_ssh_key = serializers.SerializerMethodField()
    has_database_password = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeRepositoryConfig
        fields = [
            'id',
            'name',
            'project',
            'project_name',
            'space',
            'space_name',
            'provider',
            'repository_mode',
            'auth_mode',
            'repository_url',
            'local_path',
            'username',
            'access_token',
            'ssh_key',
            'default_branch',
            'index_ref',
            'code_root',
            'frontend_root',
            'backend_root',
            'docs_root',
            'include_patterns',
            'exclude_patterns',
            'database_engine',
            'database_host',
            'database_port',
            'database_name',
            'database_schema',
            'database_username',
            'database_password',
            'database_include_patterns',
            'database_exclude_patterns',
            'allow_sample_data',
            'auto_index_on_ready',
            'authorization_status',
            'authorization_state',
            'authorization_scopes',
            'authorization_message',
            'last_test_result',
            'last_schema_test_result',
            'last_indexed_at',
            'is_active',
            'created_by',
            'created_by_name',
            'repository_location',
            'has_access_token',
            'has_ssh_key',
            'has_database_password',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_by',
            'authorization_state',
            'authorization_status',
            'authorization_message',
            'last_test_result',
            'last_schema_test_result',
            'last_indexed_at',
            'created_at',
            'updated_at',
        ]

    def get_has_access_token(self, obj):
        return bool(obj.access_token_encrypted)

    def get_has_ssh_key(self, obj):
        return bool(obj.ssh_key_encrypted)

    def get_has_database_password(self, obj):
        return bool(obj.database_password_encrypted)

    def validate(self, attrs):
        instance = self.instance
        repository_mode = normalize_repository_mode(
            attrs.get('repository_mode') or getattr(instance, 'repository_mode', LOCAL_PATH_REPOSITORY_MODE)
        )
        repository_url = attrs.get('repository_url', getattr(instance, 'repository_url', '') if instance else '') or ''
        local_path = attrs.get('local_path', getattr(instance, 'local_path', '') if instance else '') or ''

        errors = {}
        if repository_mode == LOCAL_PATH_REPOSITORY_MODE:
            if not local_path.strip():
                errors['local_path'] = '本地路径模式必须填写本地 Git 仓库路径。'
            elif not is_supported_local_repository_path(local_path):
                errors['local_path'] = LOCAL_REPOSITORY_ABSOLUTE_PATH_MESSAGE
            else:
                attrs['local_path'] = normalize_local_repository_path(local_path)
            attrs['auth_mode'] = attrs.get('auth_mode') or getattr(instance, 'auth_mode', 'none') or 'none'
        elif repository_mode == REMOTE_REPOSITORY_MODE:
            if not repository_url.strip():
                errors['repository_url'] = '远程仓库模式必须填写 Git/GitHub 仓库地址。'
        else:
            errors['repository_mode'] = '不支持的仓库模式。'

        database_engine = attrs.get('database_engine', getattr(instance, 'database_engine', 'none') if instance else 'none') or 'none'
        if database_engine == 'mysql':
            database_host = attrs.get('database_host', getattr(instance, 'database_host', '') if instance else '') or ''
            database_name = attrs.get('database_name', getattr(instance, 'database_name', '') if instance else '') or ''
            database_username = attrs.get('database_username', getattr(instance, 'database_username', '') if instance else '') or ''
            if not database_host.strip():
                errors['database_host'] = 'Database host is required for MySQL schema indexing.'
            if not database_name.strip():
                errors['database_name'] = 'Database name is required for MySQL schema indexing.'
            if not database_username.strip():
                errors['database_username'] = 'Database read-only username is required for MySQL schema indexing.'

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        access_token = validated_data.pop('access_token', '')
        ssh_key = validated_data.pop('ssh_key', '')
        database_password = validated_data.pop('database_password', '')
        if access_token:
            validated_data['access_token_encrypted'] = encrypt_password(access_token)
            if not validated_data.get('auth_mode') or validated_data.get('auth_mode') == 'none':
                validated_data['auth_mode'] = 'token'
        if ssh_key:
            validated_data['ssh_key_encrypted'] = encrypt_password(ssh_key)
            validated_data['auth_mode'] = 'ssh'
        if database_password:
            validated_data['database_password_encrypted'] = encrypt_password(database_password)
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        access_token = validated_data.pop('access_token', None)
        ssh_key = validated_data.pop('ssh_key', None)
        database_password = validated_data.pop('database_password', None)
        if access_token:
            validated_data['access_token_encrypted'] = encrypt_password(access_token)
            if not validated_data.get('auth_mode') or validated_data.get('auth_mode') == 'none':
                validated_data['auth_mode'] = 'token'
        if ssh_key:
            validated_data['ssh_key_encrypted'] = encrypt_password(ssh_key)
            validated_data['auth_mode'] = 'ssh'
        if database_password:
            validated_data['database_password_encrypted'] = encrypt_password(database_password)
        return super().update(instance, validated_data)


class KnowledgeObjectSerializer(serializers.ModelSerializer):
    space_name = serializers.CharField(source='space.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = KnowledgeObject
        fields = [
            'id',
            'space',
            'space_name',
            'project',
            'project_name',
            'repository_config',
            'object_type',
            'key',
            'name',
            'summary',
            'content',
            'roadmap_path',
            'page_path',
            'tab_key',
            'component_path',
            'api_path',
            'db_table',
            'field_name',
            'source_type',
            'source_ref',
            'metadata',
            'indexed_at',
            'created_at',
            'updated_at',
        ]


class KnowledgeRelationSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(source='source.object_type', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    target_type = serializers.CharField(source='target.object_type', read_only=True)

    class Meta:
        model = KnowledgeRelation
        fields = [
            'id',
            'space',
            'source',
            'source_name',
            'source_type',
            'target',
            'target_name',
            'target_type',
            'relation_type',
            'label',
            'weight',
            'source_ref',
            'metadata',
            'created_at',
        ]


class KnowledgeIndexRunSerializer(serializers.ModelSerializer):
    space_name = serializers.CharField(source='space.name', read_only=True)
    repository_config_name = serializers.CharField(source='repository_config.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = KnowledgeIndexRun
        fields = [
            'id',
            'space',
            'space_name',
            'repository_config',
            'repository_config_name',
            'status',
            'trigger',
            'index_ref',
            'started_at',
            'finished_at',
            'object_count',
            'relation_count',
            'changed_object_count',
            'report',
            'log',
            'error_message',
            'created_by',
            'created_by_name',
        ]


class KnowledgeQueryTraceSerializer(serializers.ModelSerializer):
    space_name = serializers.CharField(source='space.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = KnowledgeQueryTrace
        fields = [
            'id',
            'space',
            'space_name',
            'project',
            'project_name',
            'question',
            'normalized_query',
            'matched_objects',
            'evidence_nodes',
            'evidence_edges',
            'roadmap_paths',
            'data_sources',
            'context_payload',
            'confidence_score',
            'created_by',
            'created_by_name',
            'created_at',
        ]


class KnowledgeFeedbackSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = KnowledgeFeedback
        fields = [
            'id',
            'trace',
            'knowledge_object',
            'feedback_type',
            'content',
            'status',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
