import re

from django.db import models, transaction
from django.utils import timezone

from apps.projects.models import Project
from apps.users.models import User
from apps.versions.models import Version


class Defect(models.Model):
    RECORD_TYPE_DEFECT = 'defect'
    RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN = 'technical_solution_design'
    RECORD_TYPE_WIKI = 'wiki'
    RECORD_TYPE_CHOICES = [
        (RECORD_TYPE_DEFECT, '缺陷'),
        (RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN, '技术方案设计'),
        (RECORD_TYPE_WIKI, 'Wiki'),
    ]

    CODE_PREFIX = 'BUG'
    TECHNICAL_SOLUTION_DESIGN_CODE_PREFIX = 'TSD'
    WIKI_CODE_PREFIX = 'WIKI'
    CODE_SERIAL_LENGTH = 4
    LEGACY_CODE_PATTERN = re.compile(r'^BUG\d{14}$')
    VERSION_CODE_PATTERN = re.compile(r'^BUG.*?(\d{4})$')
    CODE_PREFIX_BY_RECORD_TYPE = {
        RECORD_TYPE_DEFECT: CODE_PREFIX,
        RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN: TECHNICAL_SOLUTION_DESIGN_CODE_PREFIX,
        RECORD_TYPE_WIKI: WIKI_CODE_PREFIX,
    }

    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]

    STATUS_CHOICES = [
        ('new', '待处理'),
        ('in_progress', '处理中'),
        ('resolved', '提测'),
        ('returned_pending', '打回待处理'),
        ('regression_verified', '回归验证完成'),
        ('rejected', '已拒绝'),
        ('deferred', '暂不处理'),
        ('customer_validation', '待客户环境验证'),
        ('pending_requirement', '待转新需求'),
        ('requirement_created', '已转新需求'),
        ('closed', '已关闭'),
        ('reopened', '重新打开'),
        ('invalid', '已作废'),
    ]

    PRIORITY_CHOICES = [
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
        ('P4', 'P4'),
    ]

    record_type = models.CharField(
        max_length=40,
        choices=RECORD_TYPE_CHOICES,
        default=RECORD_TYPE_DEFECT,
        verbose_name='记录类型',
    )
    code = models.CharField(max_length=32, unique=True, blank=True, verbose_name='编号')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='defects', verbose_name='所属项目')
    version = models.ForeignKey(
        Version,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='defects',
        verbose_name='关联版本',
    )
    title = models.CharField(max_length=500, verbose_name='标题')
    description = models.TextField(verbose_name='描述')
    problem_reason = models.TextField(blank=True, default='', verbose_name='问题原因')
    root_cause = models.TextField(blank=True, default='', verbose_name='问题根因')
    frontend_developer = models.CharField(max_length=100, blank=True, default='', verbose_name='前端开发')
    backend_developer = models.CharField(max_length=100, blank=True, default='', verbose_name='后端开发')
    priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES, default='P3', verbose_name='优先级')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', verbose_name='严重程度')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='状态')
    requirement_id = models.CharField(max_length=255, blank=True, verbose_name='JIRA编号')
    modules = models.JSONField(default=list, blank=True, verbose_name='关联模块')
    related_testcases = models.JSONField(default=list, blank=True, verbose_name='关联测试用例')
    related_testpoints = models.JSONField(default=list, blank=True, verbose_name='关联测试点')
    labels = models.JSONField(default=list, blank=True, verbose_name='标签')
    assignees = models.ManyToManyField(User, blank=True, related_name='assigned_defects', verbose_name='处理人')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_defects', verbose_name='创建人')
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_defects',
        verbose_name='解决人',
    )
    closed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='closed_defects',
        verbose_name='关闭人',
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解决时间')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='关闭时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'defects'
        verbose_name = '缺陷'
        verbose_name_plural = '缺陷'
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['record_type']),
            models.Index(fields=['project']),
            models.Index(fields=['version']),
            models.Index(fields=['priority']),
            models.Index(fields=['severity']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return self.code or self.title

    def get_code_prefix(self):
        return self.CODE_PREFIX_BY_RECORD_TYPE.get(self.record_type, self.CODE_PREFIX)

    def _get_max_version_segment_length(self):
        return type(self)._meta.get_field('code').max_length - len(self.get_code_prefix()) - self.CODE_SERIAL_LENGTH

    def normalize_version_code_segment(self, version_name):
        normalized = re.sub(r'\s+', '', str(version_name or ''))
        if not normalized:
            return ''
        return normalized[:self._get_max_version_segment_length()]

    def _generate_legacy_code(self):
        created_date = timezone.localtime(self.created_at).strftime('%Y%m%d')
        return f'{self.get_code_prefix()}{created_date}{self.pk:06d}'

    def _generate_version_code(self):
        version_segment = self.normalize_version_code_segment(getattr(self.version, 'name', ''))
        if not version_segment:
            return self._generate_legacy_code()

        code_prefix = self.get_code_prefix()
        prefix = f'{code_prefix}{version_segment}'
        legacy_code_pattern = re.compile(rf'^{re.escape(code_prefix)}\d{{14}}$')
        version_code_pattern = re.compile(rf'^{re.escape(code_prefix)}.*?(\d{{{self.CODE_SERIAL_LENGTH}}})$')

        Version.objects.select_for_update().filter(pk=self.version_id).values('id').first()
        existing_codes = list(
            type(self).objects
            .filter(record_type=self.record_type, version_id=self.version_id)
            .exclude(pk=self.pk)
            .values_list('code', flat=True)
        )

        next_sequence = len(existing_codes) + 1
        for current_code in existing_codes:
            normalized_code = str(current_code or '')
            if legacy_code_pattern.match(normalized_code):
                continue

            matched = version_code_pattern.match(normalized_code)
            if not matched:
                continue
            next_sequence = max(next_sequence, int(matched.group(1)) + 1)

        return f'{prefix}{next_sequence:0{self.CODE_SERIAL_LENGTH}d}'

    def generate_code(self):
        if self.version_id:
            return self._generate_version_code()
        return self._generate_legacy_code()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.code:
            with transaction.atomic():
                current = type(self).objects.select_related('version').select_for_update().get(pk=self.pk)
                if current.code:
                    self.code = current.code
                    return

                generated_code = current.generate_code()
                type(self).objects.filter(pk=self.pk, code='').update(code=generated_code)
                self.code = generated_code


class DefectAttachment(models.Model):
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='attachments', verbose_name='关联缺陷')
    name = models.CharField(max_length=255, verbose_name='附件名称')
    file = models.FileField(upload_to='defect_attachments/%Y/%m/', verbose_name='文件')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_defect_attachments', verbose_name='上传人')
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='上传时间')

    class Meta:
        db_table = 'defect_attachments'
        verbose_name = '缺陷附件'
        verbose_name_plural = '缺陷附件'
        ordering = ['uploaded_at', 'id']

    def __str__(self):
        return self.name


class WikiDirectory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='wiki_directories', verbose_name='所属项目')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name='父级目录',
    )
    name = models.CharField(max_length=200, verbose_name='目录名称')
    description = models.TextField(blank=True, default='', verbose_name='目录描述')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_wiki_directories',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'wiki_directories'
        verbose_name = 'Wiki目录'
        verbose_name_plural = 'Wiki目录'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['project', 'parent']),
            models.Index(fields=['project', 'name']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['project', 'parent', 'name'], name='uniq_wiki_directory_sibling_name'),
        ]

    def __str__(self):
        return self.name


class DefectComment(models.Model):
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='comments', verbose_name='关联缺陷')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='defect_comments', verbose_name='评论人')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'defect_comments'
        verbose_name = '缺陷评论'
        verbose_name_plural = '缺陷评论'
        ordering = ['-created_at', '-id']


class DefectHistory(models.Model):
    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('status', '状态变更'),
        ('assign', '指派'),
        ('comment', '评论'),
        ('attachment', '附件'),
    ]

    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='history_records', verbose_name='关联缺陷')
    field = models.CharField(max_length=50, verbose_name='字段')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='update', verbose_name='动作')
    from_value = models.JSONField(null=True, blank=True, verbose_name='变更前')
    to_value = models.JSONField(null=True, blank=True, verbose_name='变更后')
    changed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='defect_history_records',
        verbose_name='变更人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='变更时间')

    class Meta:
        db_table = 'defect_histories'
        verbose_name = '缺陷变更记录'
        verbose_name_plural = '缺陷变更记录'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['defect']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]


class DefectEmailConfig(models.Model):
    host = models.CharField(max_length=255, verbose_name='SMTP服务器')
    port = models.PositiveIntegerField(default=465, verbose_name='SMTP端口')
    username = models.CharField(max_length=255, verbose_name='SMTP用户名')
    password = models.CharField(max_length=255, verbose_name='SMTP密码或授权码')
    from_name = models.CharField(max_length=255, default='缺陷管理平台', verbose_name='发件人名称')
    from_email = models.EmailField(verbose_name='发件人邮箱')
    new_bug_template = models.TextField(blank=True, verbose_name='新缺陷邮件模板')
    resolved_bug_template = models.TextField(blank=True, verbose_name='已解决邮件模板')
    rejected_bug_template = models.TextField(blank=True, verbose_name='已拒绝邮件模板')
    reopened_bug_template = models.TextField(blank=True, verbose_name='重新打开邮件模板')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_defect_email_configs',
        verbose_name='创建人',
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_defect_email_configs',
        verbose_name='更新人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'defect_email_configs'
        verbose_name = '缺陷邮件配置'
        verbose_name_plural = '缺陷邮件配置'
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f'{self.from_name} <{self.from_email}>'
