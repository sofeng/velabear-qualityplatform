from django.db import models
from django.utils import timezone
import uuid
from apps.users.models import User
from apps.projects.models import Project
from apps.versions.models import Version

from .requirement_parsing import split_requirement_identifier_and_title

SELF_TEST_STATUS_CHOICES = [
    ('not_run', '未执行'),
    ('pass', '通过'),
    ('fail', '失败'),
    ('block', '阻塞'),
    ('not_test', '本版本不测'),
]

DEV_SELF_TEST_AUDIT_STATUS_CHOICES = [
    ('pending', '待审核'),
    ('approved', '审核通过'),
    ('rejected', '审核驳回'),
]


def generate_playwright_automation_script_id():
    return uuid.uuid4().hex

class TestCase(models.Model):
    """测试用例模型"""
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '激活'),
        ('deprecated', '废弃'),
    ]
    
    TYPE_CHOICES = [
        ('functional', '功能测试'),
        ('integration', '集成测试'),
        ('api', 'API测试'),
        ('ui', 'UI测试'),
        ('performance', '性能测试'),
        ('security', '安全测试'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='testcases')
    versions = models.ManyToManyField(Version, blank=True, related_name='testcases', verbose_name='关联版本')
    title = models.CharField(max_length=500, verbose_name='用例标题')
    description = models.TextField(blank=True, verbose_name='用例描述')
    preconditions = models.TextField(blank=True, verbose_name='前置条件')
    steps = models.TextField(blank=True, max_length=1000, verbose_name='操作步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    test_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='functional', verbose_name='测试类型')
    tags = models.JSONField(default=list, verbose_name='标签')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_testcases', verbose_name='作者')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_testcases', verbose_name='指派人')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'testcases'
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_at']

class TestCaseStep(models.Model):
    """测试用例步骤"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='step_details')
    step_number = models.PositiveIntegerField(verbose_name='步骤序号')
    action = models.TextField(verbose_name='操作')
    expected = models.TextField(verbose_name='预期结果')
    
    class Meta:
        db_table = 'testcase_steps'
        unique_together = ['testcase', 'step_number']
        ordering = ['step_number']
        verbose_name = '测试用例步骤'
        verbose_name_plural = '测试用例步骤'

class TestCaseAttachment(models.Model):
    """测试用例附件"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(max_length=255, verbose_name='附件名称')
    file = models.FileField(upload_to='testcase_attachments/', verbose_name='文件')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='上传者')
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    
    class Meta:
        db_table = 'testcase_attachments'
        verbose_name = '测试用例附件'
        verbose_name_plural = '测试用例附件'

class TestCaseComment(models.Model):
    """测试用例评论"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论者')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='评论时间')

    class Meta:
        db_table = 'testcase_comments'
        verbose_name = '测试用例评论'
        verbose_name_plural = '测试用例评论'
        ordering = ['-created_at']


class ManualTestCaseCategory(models.Model):
    """手工用例目录"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='manual_categories',
        verbose_name='所属项目'
    )
    name = models.CharField(max_length=200, verbose_name='目录名称')
    description = models.TextField(blank=True, verbose_name='描述')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父目录'
    )
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'manual_testcase_categories'
        verbose_name = '手工用例目录'
        verbose_name_plural = '手工用例目录'
        ordering = ['order', 'id']


class ManualTestCaseMindmap(models.Model):
    SCOPE_TESTING = 'testing'
    SCOPE_REQUIREMENT_ANALYSIS = 'requirement_analysis'
    SCOPE_CHOICES = (
        (SCOPE_TESTING, 'Testing'),
        (SCOPE_REQUIREMENT_ANALYSIS, 'Requirement analysis'),
    )

    """手工用例脑图"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='manual_mindmaps',
        verbose_name='所属项目'
    )
    name = models.CharField(max_length=200, verbose_name='脑图名称')
    description = models.TextField(blank=True, verbose_name='描述')
    category = models.ForeignKey(
        ManualTestCaseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mindmaps',
        verbose_name='关联目录'
    )
    version = models.ForeignKey(
        Version,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_mindmaps',
        verbose_name='关联版本'
    )
    responsibility_group = models.CharField(max_length=200, blank=True, verbose_name='责任小组')
    frontend_developer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='frontend_mindmaps',
        verbose_name='前端开发'
    )
    backend_developer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backend_mindmaps',
        verbose_name='后端开发'
    )
    url = models.URLField(max_length=500, blank=True, verbose_name='关联URL')
    mindmap_data = models.JSONField(default=dict, verbose_name='脑图数据')
    requirement_key = models.CharField(max_length=50, blank=True, verbose_name='需求编号')
    requirement_title = models.CharField(max_length=200, blank=True, verbose_name='需求标题')
    mindmap_scope = models.CharField(
        max_length=40,
        choices=SCOPE_CHOICES,
        default=SCOPE_TESTING,
        db_index=True,
        verbose_name='Mindmap scope',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manual_mindmaps',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    executor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_manual_mindmaps',
        verbose_name='执行人'
    )

    def extract_requirement_info(self):
        """从脑图名称提取需求编号和标题"""
        return split_requirement_identifier_and_title(self.name)

    def save(self, *args, **kwargs):
        if not self.executor_id and self.author_id:
            self.executor_id = self.author_id

        # 自动提取需求信息；如果脑图名称无法拆分，则保留显式传入的值
        extracted_key, extracted_title = self.extract_requirement_info()
        if extracted_key:
            self.requirement_key = extracted_key
            self.requirement_title = extracted_title
        else:
            self.requirement_key = self.requirement_key or ''
            self.requirement_title = self.requirement_title or ''
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'manual_testcase_mindmaps'
        verbose_name = '手工用例脑图'
        verbose_name_plural = '手工用例脑图'
        ordering = ['-updated_at']


class DevSelfTestRecord(models.Model):
    """开发自测测试点独立记录"""

    mindmap = models.ForeignKey(
        ManualTestCaseMindmap,
        on_delete=models.CASCADE,
        related_name='dev_self_test_records',
        verbose_name='关联脑图'
    )
    node_id = models.CharField(max_length=255, verbose_name='脑图节点ID')
    module = models.CharField(max_length=255, blank=True, verbose_name='模块')
    module_path = models.TextField(blank=True, verbose_name='模块路径')
    testpoint = models.TextField(blank=True, verbose_name='测试点')
    priority = models.PositiveIntegerField(null=True, blank=True, verbose_name='优先级')
    preconditions = models.TextField(blank=True, verbose_name='前置条件')
    expected_result = models.TextField(blank=True, verbose_name='期望结果')
    steps = models.TextField(blank=True, verbose_name='测试步骤')
    remark = models.TextField(blank=True, verbose_name='备注')
    status = models.CharField(
        max_length=20,
        choices=SELF_TEST_STATUS_CHOICES,
        default='not_run',
        verbose_name='状态'
    )
    audit_status = models.CharField(
        max_length=20,
        choices=DEV_SELF_TEST_AUDIT_STATUS_CHOICES,
        default='pending',
        verbose_name='审核状态'
    )
    audited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audited_dev_self_test_records',
        verbose_name='审核人'
    )
    audited_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.mindmap_id}:{self.node_id}'

    class Meta:
        db_table = 'dev_self_test_records'
        verbose_name = '开发自测记录'
        verbose_name_plural = '开发自测记录'
        ordering = ['-updated_at', '-id']
        unique_together = ['mindmap', 'node_id']


class PlaywrightRecordingSession(models.Model):
    """A Playwright recording session."""

    STATUS_STARTING = 'starting'
    STATUS_RECORDING = 'recording'
    STATUS_STOPPING = 'stopping'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI = 'server_playwright_cli'
    RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT = 'local_agent_playwright'

    STATUS_CHOICES = [
        (STATUS_STARTING, 'Starting'),
        (STATUS_RECORDING, 'Recording'),
        (STATUS_STOPPING, 'Stopping'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    RECORDING_METHOD_CHOICES = [
        (RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI, '服务端Playwright CLI录制'),
        (RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT, '本地Agent- Playwright录制'),
    ]

    session_id = models.CharField(max_length=64, unique=True, verbose_name='Recording session id')
    name = models.CharField(max_length=200, blank=True, verbose_name='Recording name')
    target_url = models.URLField(max_length=1000, verbose_name='Target URL')
    browser_type = models.CharField(max_length=30, default='chromium', verbose_name='Browser type')
    recording_method = models.CharField(
        max_length=40,
        choices=RECORDING_METHOD_CHOICES,
        default=RECORDING_METHOD_SERVER_PLAYWRIGHT_CLI,
        verbose_name='Recording method'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_STARTING,
        verbose_name='Recording status'
    )
    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='playwright_recording_sessions',
        verbose_name='Started by'
    )
    started_at = models.DateTimeField(default=timezone.now, verbose_name='Started at')
    stopped_at = models.DateTimeField(null=True, blank=True, verbose_name='Stopped at')
    error_message = models.TextField(blank=True, verbose_name='Error message')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Recording metadata')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return self.name or self.session_id

    class Meta:
        db_table = 'playwright_recording_sessions'
        verbose_name = 'Playwright recording session'
        verbose_name_plural = 'Playwright recording sessions'
        ordering = ['-started_at', '-id']


class PlaywrightRecordingStep(models.Model):
    """One captured user action with its snapshot and target element data."""

    session = models.ForeignKey(
        PlaywrightRecordingSession,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='Recording session'
    )
    step_number = models.PositiveIntegerField(verbose_name='Step number')
    action_type = models.CharField(max_length=40, verbose_name='Action type')
    action_value = models.TextField(blank=True, verbose_name='Action value')
    page_url = models.TextField(blank=True, verbose_name='Page URL')
    page_title = models.CharField(max_length=500, blank=True, verbose_name='Page title')
    element = models.JSONField(default=dict, blank=True, verbose_name='Element data')
    selectors = models.JSONField(default=list, blank=True, verbose_name='Selector candidates')
    snapshot_filename = models.CharField(max_length=255, blank=True, verbose_name='Snapshot filename')
    screenshot_path = models.CharField(max_length=500, blank=True, verbose_name='Screenshot path')
    raw_event = models.JSONField(default=dict, blank=True, verbose_name='Raw event data')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')

    def __str__(self):
        return f'{self.session.session_id}:{self.step_number}:{self.action_type}'

    class Meta:
        db_table = 'playwright_recording_steps'
        verbose_name = 'Playwright recording step'
        verbose_name_plural = 'Playwright recording steps'
        ordering = ['session', 'step_number']
        unique_together = ['session', 'step_number']


class PlaywrightAutomationScript(models.Model):
    """A generated Playwright automation script with latest-version materialized fields."""

    script_id = models.CharField(
        max_length=64,
        unique=True,
        default=generate_playwright_automation_script_id,
        verbose_name='Automation script id'
    )
    name = models.CharField(max_length=200, verbose_name='Script name')
    description = models.TextField(blank=True, verbose_name='Description')
    target_url = models.TextField(blank=True, verbose_name='Target URL')
    instruction = models.TextField(blank=True, verbose_name='Natural language instruction')
    script = models.TextField(blank=True, verbose_name='Current Playwright script')
    summary = models.TextField(blank=True, verbose_name='Generation summary')
    warnings = models.JSONField(default=list, blank=True, verbose_name='Generation warnings')
    planned_actions = models.JSONField(default=list, blank=True, verbose_name='Planned actions')
    generation_source = models.CharField(max_length=60, blank=True, verbose_name='Generation source')
    fallback_reason = models.TextField(blank=True, verbose_name='Fallback reason')
    module = models.JSONField(default=dict, blank=True, verbose_name='Module metadata')
    model = models.JSONField(default=dict, blank=True, verbose_name='Model snapshot')
    capability = models.JSONField(default=dict, blank=True, verbose_name='Skill snapshot')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Extra metadata')
    latest_version = models.PositiveIntegerField(default=0, verbose_name='Latest version number')
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='playwright_automation_scripts',
        verbose_name='Project'
    )
    version = models.ForeignKey(
        Version,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='playwright_automation_scripts',
        verbose_name='Version'
    )
    module_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='Module id')
    module_name = models.CharField(max_length=200, blank=True, verbose_name='Module name')
    module_path = models.TextField(blank=True, verbose_name='Module path')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_playwright_automation_scripts',
        verbose_name='Created by'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_playwright_automation_scripts',
        verbose_name='Updated by'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return self.name or self.script_id

    class Meta:
        db_table = 'playwright_automation_scripts'
        verbose_name = 'Playwright automation script'
        verbose_name_plural = 'Playwright automation scripts'
        ordering = ['-updated_at', '-id']


class PlaywrightAutomationScriptVersion(models.Model):
    """An immutable saved version of a generated Playwright automation script."""

    script = models.ForeignKey(
        PlaywrightAutomationScript,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Automation script'
    )
    version = models.PositiveIntegerField(verbose_name='Version number')
    name = models.CharField(max_length=200, blank=True, verbose_name='Script name at version')
    target_url = models.TextField(blank=True, verbose_name='Target URL')
    instruction = models.TextField(blank=True, verbose_name='Natural language instruction')
    script_content = models.TextField(blank=True, verbose_name='Playwright script content')
    summary = models.TextField(blank=True, verbose_name='Generation summary')
    warnings = models.JSONField(default=list, blank=True, verbose_name='Generation warnings')
    planned_actions = models.JSONField(default=list, blank=True, verbose_name='Planned actions')
    generation_source = models.CharField(max_length=60, blank=True, verbose_name='Generation source')
    fallback_reason = models.TextField(blank=True, verbose_name='Fallback reason')
    module = models.JSONField(default=dict, blank=True, verbose_name='Module metadata')
    model = models.JSONField(default=dict, blank=True, verbose_name='Model snapshot')
    capability = models.JSONField(default=dict, blank=True, verbose_name='Skill snapshot')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Extra metadata')
    change_summary = models.CharField(max_length=500, blank=True, verbose_name='Change summary')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='playwright_automation_script_versions',
        verbose_name='Created by'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')

    def __str__(self):
        parent_script_id = self.script.script_id if self.script_id and self.script else ''
        return f'{parent_script_id}:v{self.version}'

    class Meta:
        db_table = 'playwright_automation_script_versions'
        verbose_name = 'Playwright automation script version'
        verbose_name_plural = 'Playwright automation script versions'
        ordering = ['-version', '-id']
        unique_together = ['script', 'version']


class ManualWorkspacePageListConfig(models.Model):
    """Server-side defaults for manual workspace page filters and list columns."""

    module_key = models.CharField(max_length=80, default='manual-testcases', verbose_name='Module key')
    page_key = models.CharField(max_length=120, verbose_name='Page key')
    filter_conditions = models.JSONField(default=list, blank=True, verbose_name='Filter conditions')
    columns = models.JSONField(default=list, blank=True, verbose_name='List columns')
    version = models.PositiveIntegerField(default=1, verbose_name='Config version')
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_manual_workspace_page_list_configs',
        verbose_name='Updated by',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return f'{self.module_key}:{self.page_key}'

    class Meta:
        db_table = 'manual_workspace_page_list_configs'
        verbose_name = 'Manual workspace page list config'
        verbose_name_plural = 'Manual workspace page list configs'
        ordering = ['module_key', 'page_key']
        constraints = [
            models.UniqueConstraint(
                fields=['module_key', 'page_key'],
                name='manual_workspace_page_list_config_unique',
            ),
        ]


class VisualFlow(models.Model):
    """A persisted visual flow graph for the manual testcase flow editor."""

    SOURCE_MANUAL = 'manual'
    SOURCE_RECORDING = 'recording'

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Manual'),
        (SOURCE_RECORDING, 'Recording'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    flow_id = models.CharField(max_length=64, unique=True, verbose_name='Visual flow id')
    name = models.CharField(max_length=200, verbose_name='Flow name')
    description = models.TextField(blank=True, verbose_name='Flow description')
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        verbose_name='Flow source'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Flow status'
    )
    target_url = models.TextField(blank=True, verbose_name='Target URL')
    browser_type = models.CharField(max_length=30, default='chromium', blank=True, verbose_name='Browser type')
    recording_session = models.ForeignKey(
        PlaywrightRecordingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visual_flows',
        verbose_name='Recording session'
    )
    graph_data = models.JSONField(default=dict, blank=True, verbose_name='X6 graph data')
    snapshot_summary = models.JSONField(default=dict, blank=True, verbose_name='Snapshot summary')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Flow metadata')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visual_flows',
        verbose_name='Created by'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return self.name or self.flow_id

    class Meta:
        db_table = 'visual_flows'
        verbose_name = 'Visual flow'
        verbose_name_plural = 'Visual flows'
        ordering = ['-updated_at', '-id']


class VisualFlowExecution(models.Model):
    """A replay execution record for a visual flow."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_ABORTED = 'aborted'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_ABORTED, 'Aborted'),
    ]

    RUN_TYPE_BACKEND = 'backend'
    RUN_TYPE_LOCAL = 'local'

    RUN_TYPE_CHOICES = [
        (RUN_TYPE_BACKEND, 'Backend'),
        (RUN_TYPE_LOCAL, 'Local'),
    ]

    execution_id = models.CharField(max_length=64, unique=True, verbose_name='Execution id')
    flow = models.ForeignKey(
        VisualFlow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='Visual flow',
    )
    flow_id_text = models.CharField(max_length=64, blank=True, verbose_name='Flow id text')
    flow_name = models.CharField(max_length=200, blank=True, verbose_name='Flow name')
    run_type = models.CharField(max_length=20, choices=RUN_TYPE_CHOICES, default=RUN_TYPE_BACKEND, verbose_name='Run type')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Status')
    graph_snapshot = models.JSONField(default=dict, blank=True, verbose_name='Graph snapshot')
    summary = models.JSONField(default=dict, blank=True, verbose_name='Execution summary')
    stdout = models.TextField(blank=True, verbose_name='Stdout')
    stderr = models.TextField(blank=True, verbose_name='Stderr')
    error_message = models.TextField(blank=True, verbose_name='Error message')
    returncode = models.IntegerField(null=True, blank=True, verbose_name='Return code')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started at')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Finished at')
    duration = models.FloatField(default=0, verbose_name='Duration seconds')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visual_flow_executions',
        verbose_name='Created by',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return f'{self.flow_name or self.flow_id_text or self.execution_id} - {self.status}'

    class Meta:
        db_table = 'visual_flow_executions'
        verbose_name = 'Visual flow execution'
        verbose_name_plural = 'Visual flow executions'
        ordering = ['-created_at', '-id']


class VisualFlowExecutionStep(models.Model):
    """A node/component level replay result for a visual flow execution."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    ITEM_TYPE_NODE = 'node'
    ITEM_TYPE_COMPONENT = 'component'

    ITEM_TYPE_CHOICES = [
        (ITEM_TYPE_NODE, 'Node'),
        (ITEM_TYPE_COMPONENT, 'Component'),
    ]

    execution = models.ForeignKey(
        VisualFlowExecution,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='Execution',
    )
    step_key = models.CharField(max_length=200, verbose_name='Step key')
    step_order = models.PositiveIntegerField(default=0, verbose_name='Step order')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default=ITEM_TYPE_NODE, verbose_name='Item type')
    node_id = models.CharField(max_length=120, blank=True, verbose_name='Node id')
    component_id = models.CharField(max_length=120, blank=True, verbose_name='Component id')
    title = models.CharField(max_length=500, blank=True, verbose_name='Title')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='Status')
    input_data = models.JSONField(default=dict, blank=True, verbose_name='Input data')
    output_data = models.JSONField(default=dict, blank=True, verbose_name='Output data')
    error_log = models.TextField(blank=True, verbose_name='Error log')
    screenshot_path = models.CharField(max_length=500, blank=True, verbose_name='Screenshot path')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started at')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Finished at')
    duration = models.FloatField(default=0, verbose_name='Duration seconds')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    def __str__(self):
        return f'{self.execution.execution_id}:{self.step_key}:{self.status}'

    class Meta:
        db_table = 'visual_flow_execution_steps'
        verbose_name = 'Visual flow execution step'
        verbose_name_plural = 'Visual flow execution steps'
        ordering = ['execution', 'step_order', 'id']
        unique_together = ['execution', 'step_key']
