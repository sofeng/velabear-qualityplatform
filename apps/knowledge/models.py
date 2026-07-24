from django.db import models
from django.utils import timezone

from apps.projects.models import Project
from apps.users.models import User


class KnowledgeSpace(models.Model):
    SPACE_TYPE_CHOICES = [
        ('platform', 'Platform'),
        ('module', 'Module'),
        ('project', 'Project'),
        ('repository', 'Repository'),
        ('system', 'System'),
    ]
    BUILD_STATUS_CHOICES = [
        ('pending_config', 'Pending Config'),
        ('ready', 'Ready'),
        ('queued', 'Queued'),
        ('indexing', 'Indexing'),
        ('indexed', 'Indexed'),
        ('stale', 'Stale'),
        ('failed', 'Failed'),
    ]

    key = models.CharField(max_length=100, unique=True, verbose_name='Space Key')
    name = models.CharField(max_length=200, verbose_name='Name')
    description = models.TextField(blank=True, default='', verbose_name='Description')
    space_type = models.CharField(max_length=32, choices=SPACE_TYPE_CHOICES, default='project', verbose_name='Space Type')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name='knowledge_spaces', verbose_name='Project')
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_knowledge_spaces', verbose_name='Owner')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    build_status = models.CharField(max_length=32, choices=BUILD_STATUS_CHOICES, default='pending_config', verbose_name='Build Status')
    build_status_message = models.CharField(max_length=500, blank=True, default='', verbose_name='Build Status Message')
    last_indexed_at = models.DateTimeField(null=True, blank=True, verbose_name='Last Indexed At')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'knowledge_spaces'
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class KnowledgeRepositoryConfig(models.Model):
    PROVIDER_CHOICES = [
        ('local', 'Local'),
        ('git', 'Git'),
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('gitee', 'Gitee'),
    ]
    REPOSITORY_MODE_CHOICES = [
        ('remote', 'Remote Repository'),
        ('local_path', 'Local Path Repository'),
    ]
    AUTH_MODE_CHOICES = [
        ('none', 'None'),
        ('token', 'Token'),
        ('ssh', 'SSH'),
        ('oauth', 'OAuth'),
        ('github_app', 'GitHub App'),
    ]
    AUTH_STATUS_CHOICES = [
        ('not_configured', 'Not Configured'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('failed', 'Failed'),
    ]
    DATABASE_ENGINE_CHOICES = [
        ('none', 'None'),
        ('current', 'Current Platform Database'),
        ('mysql', 'MySQL'),
    ]

    name = models.CharField(max_length=200, verbose_name='Name')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name='knowledge_repository_configs', verbose_name='Project')
    space = models.ForeignKey(KnowledgeSpace, null=True, blank=True, on_delete=models.SET_NULL, related_name='repository_configs', verbose_name='Knowledge Space')
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default='local', verbose_name='Provider')
    repository_mode = models.CharField(max_length=20, choices=REPOSITORY_MODE_CHOICES, default='local_path', verbose_name='Repository Mode')
    auth_mode = models.CharField(max_length=32, choices=AUTH_MODE_CHOICES, default='none', verbose_name='Auth Mode')
    repository_url = models.CharField(max_length=500, blank=True, default='', verbose_name='Repository URL')
    local_path = models.CharField(max_length=500, blank=True, default='', verbose_name='Local Repository Path')
    username = models.CharField(max_length=150, blank=True, default='', verbose_name='Username')
    access_token_encrypted = models.CharField(max_length=1000, blank=True, default='', verbose_name='Encrypted Access Token')
    ssh_key_encrypted = models.TextField(blank=True, default='', verbose_name='Encrypted SSH Key')
    default_branch = models.CharField(max_length=100, default='main', verbose_name='Default Branch')
    index_ref = models.CharField(max_length=100, blank=True, default='', verbose_name='Index Ref')
    code_root = models.CharField(max_length=255, blank=True, default='.', verbose_name='Code Root')
    frontend_root = models.CharField(max_length=255, blank=True, default='frontend', verbose_name='Frontend Root')
    backend_root = models.CharField(max_length=255, blank=True, default='apps', verbose_name='Backend Root')
    docs_root = models.CharField(max_length=255, blank=True, default='docs', verbose_name='Docs Root')
    include_patterns = models.JSONField(default=list, blank=True, verbose_name='Include Patterns')
    exclude_patterns = models.JSONField(default=list, blank=True, verbose_name='Exclude Patterns')
    database_engine = models.CharField(max_length=32, choices=DATABASE_ENGINE_CHOICES, default='none', verbose_name='Database Engine')
    database_host = models.CharField(max_length=255, blank=True, default='', verbose_name='Database Host')
    database_port = models.CharField(max_length=20, blank=True, default='', verbose_name='Database Port')
    database_name = models.CharField(max_length=200, blank=True, default='', verbose_name='Database Name')
    database_schema = models.CharField(max_length=200, blank=True, default='', verbose_name='Database Schema')
    database_username = models.CharField(max_length=150, blank=True, default='', verbose_name='Database Username')
    database_password_encrypted = models.CharField(max_length=1000, blank=True, default='', verbose_name='Encrypted Database Password')
    database_include_patterns = models.JSONField(default=list, blank=True, verbose_name='Database Include Patterns')
    database_exclude_patterns = models.JSONField(default=list, blank=True, verbose_name='Database Exclude Patterns')
    allow_sample_data = models.BooleanField(default=False, verbose_name='Allow Sample Data')
    auto_index_on_ready = models.BooleanField(default=True, verbose_name='Auto Index On Ready')
    authorization_status = models.CharField(max_length=32, choices=AUTH_STATUS_CHOICES, default='not_configured', verbose_name='Authorization Status')
    authorization_state = models.CharField(max_length=128, blank=True, default='', verbose_name='Authorization State')
    authorization_scopes = models.JSONField(default=list, blank=True, verbose_name='Authorization Scopes')
    authorization_message = models.CharField(max_length=500, blank=True, default='', verbose_name='Authorization Message')
    last_test_result = models.JSONField(default=dict, blank=True, verbose_name='Last Test Result')
    last_schema_test_result = models.JSONField(default=dict, blank=True, verbose_name='Last Schema Test Result')
    last_indexed_at = models.DateTimeField(null=True, blank=True, verbose_name='Last Indexed At')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_repository_configs', verbose_name='Created By')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'knowledge_repository_configs'
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return self.name

    @property
    def repository_location(self):
        return self.local_path if self.repository_mode == 'local_path' else self.repository_url


class KnowledgeObject(models.Model):
    OBJECT_TYPE_CHOICES = [
        ('platform', 'Platform'),
        ('module', 'Module'),
        ('menu', 'Menu'),
        ('page', 'Page'),
        ('tab', 'Tab'),
        ('function', 'Function'),
        ('operation', 'Operation'),
        ('field', 'Field'),
        ('api', 'API'),
        ('database', 'Database'),
        ('table', 'Table'),
        ('file', 'File'),
        ('class', 'Class'),
        ('method', 'Method'),
        ('component', 'Component'),
        ('route', 'Route'),
        ('repository', 'Repository'),
        ('document', 'Document'),
        ('business_data', 'Business Data'),
    ]

    space = models.ForeignKey(KnowledgeSpace, on_delete=models.CASCADE, related_name='knowledge_objects', verbose_name='Knowledge Space')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name='knowledge_objects', verbose_name='Project')
    repository_config = models.ForeignKey(KnowledgeRepositoryConfig, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_objects', verbose_name='Repository Config')
    object_type = models.CharField(max_length=32, choices=OBJECT_TYPE_CHOICES, verbose_name='Object Type')
    key = models.CharField(max_length=255, verbose_name='Object Key')
    name = models.CharField(max_length=255, verbose_name='Name')
    summary = models.TextField(blank=True, default='', verbose_name='Summary')
    content = models.TextField(blank=True, default='', verbose_name='Content')
    roadmap_path = models.JSONField(default=list, blank=True, verbose_name='Roadmap Path')
    page_path = models.CharField(max_length=500, blank=True, default='', verbose_name='Page Path')
    tab_key = models.CharField(max_length=100, blank=True, default='', verbose_name='Tab Key')
    component_path = models.CharField(max_length=500, blank=True, default='', verbose_name='Component Path')
    api_path = models.CharField(max_length=500, blank=True, default='', verbose_name='API Path')
    db_table = models.CharField(max_length=200, blank=True, default='', verbose_name='Database Table')
    field_name = models.CharField(max_length=200, blank=True, default='', verbose_name='Field Name')
    source_type = models.CharField(max_length=64, blank=True, default='', verbose_name='Source Type')
    source_ref = models.CharField(max_length=500, blank=True, default='', verbose_name='Source Reference')
    source_hash = models.CharField(max_length=64, blank=True, default='', verbose_name='Source Hash')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    search_text = models.TextField(blank=True, default='', verbose_name='Search Text')
    indexed_at = models.DateTimeField(default=timezone.now, verbose_name='Indexed At')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'knowledge_objects'
        ordering = ['object_type', 'name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['space', 'key'], name='knowledge_objects_space_key_unique'),
        ]
        indexes = [
            models.Index(fields=['space', 'object_type'], name='knowledge_obj_space_type_idx'),
            models.Index(fields=['project', 'object_type'], name='knowledge_obj_project_type_idx'),
            models.Index(fields=['tab_key'], name='knowledge_obj_tab_key_idx'),
            models.Index(fields=['db_table'], name='knowledge_obj_db_table_idx'),
        ]

    def __str__(self):
        return f'{self.object_type}:{self.name}'


class KnowledgeRelation(models.Model):
    RELATION_TYPE_CHOICES = [
        ('contains', 'Contains'),
        ('belongs_to', 'Belongs To'),
        ('opens', 'Opens'),
        ('implements', 'Implements'),
        ('calls', 'Calls'),
        ('reads', 'Reads'),
        ('writes', 'Writes'),
        ('references', 'References'),
        ('depends_on', 'Depends On'),
        ('uses', 'Uses'),
        ('same_as', 'Same As'),
        ('related_to', 'Related To'),
    ]

    space = models.ForeignKey(KnowledgeSpace, on_delete=models.CASCADE, related_name='relations', verbose_name='Knowledge Space')
    source = models.ForeignKey(KnowledgeObject, on_delete=models.CASCADE, related_name='outgoing_relations', verbose_name='Source Object')
    target = models.ForeignKey(KnowledgeObject, on_delete=models.CASCADE, related_name='incoming_relations', verbose_name='Target Object')
    relation_type = models.CharField(max_length=32, choices=RELATION_TYPE_CHOICES, verbose_name='Relation Type')
    label = models.CharField(max_length=150, blank=True, default='', verbose_name='Label')
    weight = models.FloatField(default=1.0, verbose_name='Weight')
    source_ref = models.CharField(max_length=500, blank=True, default='', verbose_name='Source Reference')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')

    class Meta:
        db_table = 'knowledge_relations'
        ordering = ['source_id', 'target_id', 'relation_type']
        constraints = [
            models.UniqueConstraint(fields=['space', 'source', 'target', 'relation_type'], name='knowledge_rel_space_edge_unique'),
        ]
        indexes = [
            models.Index(fields=['space', 'relation_type'], name='knowledge_rel_space_type_idx'),
        ]

    def __str__(self):
        return f'{self.source_id}->{self.target_id}:{self.relation_type}'


class KnowledgeIndexRun(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    space = models.ForeignKey(KnowledgeSpace, null=True, blank=True, on_delete=models.SET_NULL, related_name='index_runs', verbose_name='Knowledge Space')
    repository_config = models.ForeignKey(KnowledgeRepositoryConfig, null=True, blank=True, on_delete=models.SET_NULL, related_name='index_runs', verbose_name='Repository Config')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='queued', verbose_name='Status')
    trigger = models.CharField(max_length=64, blank=True, default='manual', verbose_name='Trigger')
    index_ref = models.CharField(max_length=100, blank=True, default='', verbose_name='Index Ref')
    started_at = models.DateTimeField(default=timezone.now, verbose_name='Started At')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Finished At')
    object_count = models.PositiveIntegerField(default=0, verbose_name='Object Count')
    relation_count = models.PositiveIntegerField(default=0, verbose_name='Relation Count')
    changed_object_count = models.PositiveIntegerField(default=0, verbose_name='Changed Object Count')
    report = models.JSONField(default=dict, blank=True, verbose_name='Report')
    log = models.TextField(blank=True, default='', verbose_name='Log')
    error_message = models.TextField(blank=True, default='', verbose_name='Error Message')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_index_runs', verbose_name='Created By')

    class Meta:
        db_table = 'knowledge_index_runs'
        ordering = ['-started_at', '-id']

    def __str__(self):
        return f'{self.repository_config_id}:{self.status}:{self.started_at}'


class KnowledgeQueryTrace(models.Model):
    space = models.ForeignKey(KnowledgeSpace, null=True, blank=True, on_delete=models.SET_NULL, related_name='query_traces', verbose_name='Knowledge Space')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_query_traces', verbose_name='Project')
    question = models.TextField(verbose_name='Question')
    normalized_query = models.TextField(blank=True, default='', verbose_name='Normalized Query')
    matched_objects = models.JSONField(default=list, blank=True, verbose_name='Matched Objects')
    evidence_nodes = models.JSONField(default=list, blank=True, verbose_name='Evidence Nodes')
    evidence_edges = models.JSONField(default=list, blank=True, verbose_name='Evidence Edges')
    roadmap_paths = models.JSONField(default=list, blank=True, verbose_name='Roadmap Paths')
    data_sources = models.JSONField(default=list, blank=True, verbose_name='Data Sources')
    context_payload = models.JSONField(default=dict, blank=True, verbose_name='Context Payload')
    confidence_score = models.FloatField(default=0.0, verbose_name='Confidence Score')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_query_traces', verbose_name='Created By')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')

    class Meta:
        db_table = 'knowledge_query_traces'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.pk}:{self.question[:40]}'


class KnowledgeFeedback(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('correction', 'Correction'),
        ('confirmation', 'Confirmation'),
        ('supplement', 'Supplement'),
    ]

    trace = models.ForeignKey(KnowledgeQueryTrace, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_items', verbose_name='Query Trace')
    knowledge_object = models.ForeignKey(KnowledgeObject, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_items', verbose_name='Knowledge Object')
    feedback_type = models.CharField(max_length=32, choices=FEEDBACK_TYPE_CHOICES, default='correction', verbose_name='Feedback Type')
    content = models.TextField(verbose_name='Content')
    status = models.CharField(max_length=32, default='open', verbose_name='Status')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='knowledge_feedback_items', verbose_name='Created By')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'knowledge_feedback'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.feedback_type}:{self.pk}'
