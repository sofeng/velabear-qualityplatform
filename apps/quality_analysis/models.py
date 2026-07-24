import re
import secrets
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.signals import post_delete
from django.utils import timezone
from django.dispatch import receiver

from .version_utils import normalize_jira_version


DEFAULT_JIRA_BROWSE_PREFIX = 'http://172.31.119.34:8080/browse/'
RICH_TEXT_IMAGE_PREFIX = 'defect_rich_text_images/'
RICH_TEXT_IMAGE_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


def normalize_jira_browse_prefix(value):
    normalized = str(value or '').strip()
    if not normalized:
        return DEFAULT_JIRA_BROWSE_PREFIX
    return normalized if normalized.endswith('/') else f'{normalized}/'


def normalize_media_relative_path(source):
    if not source:
        return ''

    parsed_url = urlparse(str(source))
    path = parsed_url.path if parsed_url.scheme or parsed_url.netloc else str(source)

    if path.startswith(settings.MEDIA_URL):
        path = path[len(settings.MEDIA_URL):]

    normalized_path = path.lstrip('/').replace('\\', '/')
    if normalized_path.startswith('../'):
        return ''

    return normalized_path


def extract_rich_text_image_paths(content):
    paths = set()

    if not content:
        return paths

    for source in RICH_TEXT_IMAGE_PATTERN.findall(str(content)):
        relative_path = normalize_media_relative_path(source)
        if relative_path.startswith(RICH_TEXT_IMAGE_PREFIX):
            paths.add(relative_path)

    return paths


def cleanup_rich_text_images(relative_paths):
    for relative_path in relative_paths:
        if not relative_path.startswith(RICH_TEXT_IMAGE_PREFIX):
            continue

        if default_storage.exists(relative_path):
            default_storage.delete(relative_path)


class QualityAnalysisSettings(models.Model):
    SINGLETON_KEY = 'default'

    singleton_key = models.CharField(max_length=32, unique=True, default=SINGLETON_KEY, editable=False)
    jira_browse_prefix = models.CharField(max_length=500, default=DEFAULT_JIRA_BROWSE_PREFIX)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quality_analysis_settings'
        verbose_name = 'Quality analysis settings'
        verbose_name_plural = 'Quality analysis settings'

    def save(self, *args, **kwargs):
        if not self.singleton_key:
            self.singleton_key = self.SINGLETON_KEY
        self.jira_browse_prefix = normalize_jira_browse_prefix(self.jira_browse_prefix)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'QualityAnalysisSettings<{self.singleton_key}>'

    @classmethod
    def get_solo(cls):
        instance, _ = cls.objects.get_or_create(
            singleton_key=cls.SINGLETON_KEY,
            defaults={'jira_browse_prefix': DEFAULT_JIRA_BROWSE_PREFIX},
        )
        return instance


class QualityReport(models.Model):
    STATUS_CHOICES = [
        ('uploaded', '已上传'),
        ('analyzing', '分析中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    version = models.CharField(max_length=100, unique=True, verbose_name='版本号')
    source_excel = models.FileField(
        upload_to='quality-analysis/source/%Y/%m/',
        verbose_name='缺陷数据 Excel',
    )
    processed_excel = models.FileField(
        upload_to='quality-analysis/processed/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='处理后的缺陷 Excel',
    )
    requirement_excel = models.FileField(
        upload_to='quality-analysis/requirements/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='需求清单 Excel',
    )
    testcase_excel = models.FileField(
        upload_to='quality-analysis/testcases/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='测试用例统计 Excel',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded',
        verbose_name='状态',
    )
    total_defects = models.PositiveIntegerField(default=0, verbose_name='缺陷总数')
    classified_defects = models.PositiveIntegerField(default=0, verbose_name='已分类缺陷数')
    analysis_result = models.JSONField(default=dict, blank=True, verbose_name='分析结果')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    share_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='分享令牌',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quality_reports',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name='分析完成时间')

    class Meta:
        db_table = 'quality_analysis_reports'
        verbose_name = '质量分析报告'
        verbose_name_plural = '质量分析报告'
        ordering = ['-created_at']

    def __str__(self):
        return self.version

    def ensure_share_token(self):
        if self.share_token:
            return self.share_token

        token = secrets.token_urlsafe(32)
        while QualityReport.objects.filter(share_token=token).exists():
            token = secrets.token_urlsafe(32)
        self.share_token = token
        self.save(update_fields=['share_token', 'updated_at'])
        return token

    def delete(self, *args, **kwargs):
        file_fields = [
            self.source_excel,
            self.processed_excel,
            self.requirement_excel,
            self.testcase_excel,
        ]
        for file_field in file_fields:
            if file_field:
                file_field.delete(save=False)
        super().delete(*args, **kwargs)


class JiraInterfaceConfig(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ]

    version = models.CharField(max_length=100, unique=True, verbose_name='版本号')
    name = models.CharField(max_length=100, default='JIRA线上BUG接口', verbose_name='配置名称')
    request_url = models.CharField(max_length=500, verbose_name='请求 URL')
    request_method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES,
        default='POST',
        verbose_name='请求方法',
    )
    request_headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')
    request_body = models.TextField(blank=True, verbose_name='请求体')
    timeout_seconds = models.PositiveIntegerField(default=60, verbose_name='超时时间(秒)')
    jira_login_enabled = models.BooleanField(default=False, verbose_name='启用JIRA登录')
    jira_login_url = models.CharField(
        max_length=500,
        blank=True,
        default='http://172.31.119.34:8080/login.jsp',
        verbose_name='JIRA登录URL',
    )
    jira_username = models.CharField(max_length=255, blank=True, default='', verbose_name='JIRA账号')
    jira_password_encrypted = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='JIRA密码(加密存储)',
    )
    is_active = models.BooleanField(default=True, verbose_name='启用状态')
    notes = models.TextField(blank=True, verbose_name='备注')
    last_executed_at = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')
    last_status_code = models.PositiveIntegerField(null=True, blank=True, verbose_name='最后响应状态码')
    last_record_count = models.PositiveIntegerField(default=0, verbose_name='最后同步记录数')
    last_execution_message = models.TextField(blank=True, verbose_name='最后执行结果')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jira_interface_configs',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'quality_analysis_jira_configs'
        verbose_name = 'JIRA接口配置'
        verbose_name_plural = 'JIRA接口配置'
        ordering = ['-updated_at', '-created_at']

    def save(self, *args, **kwargs):
        self.version = normalize_jira_version(self.version)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.version} - {self.name}'


class JiraRequirementInterfaceConfig(models.Model):
    METHOD_CHOICES = JiraInterfaceConfig.METHOD_CHOICES

    version = models.CharField(max_length=100, unique=True, verbose_name='版本号')
    name = models.CharField(max_length=100, default='JIRA需求接口', verbose_name='配置名称')
    request_url = models.CharField(max_length=500, verbose_name='请求 URL')
    request_method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES,
        default='POST',
        verbose_name='请求方法',
    )
    request_headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')
    request_body = models.TextField(blank=True, verbose_name='请求体')
    timeout_seconds = models.PositiveIntegerField(default=60, verbose_name='超时时间(秒)')
    jira_login_enabled = models.BooleanField(default=False, verbose_name='启用JIRA登录')
    jira_login_url = models.CharField(
        max_length=500,
        blank=True,
        default='http://172.31.119.34:8080/login.jsp',
        verbose_name='JIRA登录URL',
    )
    jira_username = models.CharField(max_length=255, blank=True, default='', verbose_name='JIRA账号')
    jira_password_encrypted = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='JIRA密码(加密存储)',
    )
    is_active = models.BooleanField(default=True, verbose_name='启用状态')
    notes = models.TextField(blank=True, verbose_name='备注')
    last_executed_at = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')
    last_status_code = models.PositiveIntegerField(null=True, blank=True, verbose_name='最后响应状态码')
    last_record_count = models.PositiveIntegerField(default=0, verbose_name='最后同步记录数')
    last_execution_message = models.TextField(blank=True, verbose_name='最后执行结果')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jira_requirement_interface_configs',
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'quality_analysis_jira_requirement_configs'
        verbose_name = 'JIRA需求接口配置'
        verbose_name_plural = 'JIRA需求接口配置'
        ordering = ['-updated_at', '-created_at']

    def save(self, *args, **kwargs):
        self.version = normalize_jira_version(self.version)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.version} - {self.name}'


class JiraBugRecord(models.Model):
    config = models.ForeignKey(
        JiraInterfaceConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bug_records',
        verbose_name='来源配置',
    )
    version = models.CharField(max_length=100, db_index=True, verbose_name='版本号')
    issue_id = models.CharField(max_length=50, blank=True, verbose_name='JIRA内部ID')
    issue_key = models.CharField(max_length=100, db_index=True, verbose_name='问题编号')
    issue_type = models.CharField(max_length=100, blank=True, verbose_name='问题类型')
    summary = models.TextField(blank=True, verbose_name='标题')
    module = models.CharField(max_length=255, blank=True, verbose_name='模块')
    customer_name = models.CharField(max_length=255, blank=True, verbose_name='客户名称')
    priority = models.CharField(max_length=100, blank=True, verbose_name='优先级')
    status = models.CharField(max_length=100, blank=True, verbose_name='状态')
    creator = models.CharField(max_length=100, blank=True, verbose_name='创建人')
    handler = models.CharField(max_length=100, blank=True, verbose_name='处理人')
    tester = models.CharField(max_length=100, blank=True, verbose_name='测试人员')
    group_name = models.CharField(max_length=100, blank=True, verbose_name='责任组')
    related_requirements = models.JSONField(default=list, blank=True, verbose_name='关联需求')
    related_testcases = models.JSONField(default=list, blank=True, verbose_name='关联测试用例')
    related_testpoints = models.JSONField(default=list, blank=True, verbose_name='关联测试点')
    row_index = models.PositiveIntegerField(default=0, verbose_name='排序序号')
    raw_fields = models.JSONField(default=dict, blank=True, verbose_name='原始字段')
    synced_at = models.DateTimeField(default=timezone.now, verbose_name='同步时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'quality_analysis_jira_bug_records'
        verbose_name = 'JIRA线上BUG数据'
        verbose_name_plural = 'JIRA线上BUG数据'
        ordering = ['-synced_at', 'row_index', 'issue_key']
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'issue_key'],
                name='uq_quality_analysis_jira_bug_version_key',
            )
        ]

    def save(self, *args, **kwargs):
        self.version = normalize_jira_version(self.version)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.version} - {self.issue_key}'


class JiraRequirementRecord(models.Model):
    config = models.ForeignKey(
        JiraRequirementInterfaceConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requirement_records',
        verbose_name='来源配置',
    )
    version = models.CharField(max_length=100, db_index=True, verbose_name='版本号')
    issue_id = models.CharField(max_length=50, blank=True, verbose_name='JIRA内部ID')
    issue_key = models.CharField(max_length=100, db_index=True, verbose_name='问题编号')
    issue_type = models.CharField(max_length=100, blank=True, verbose_name='问题类型')
    summary = models.TextField(blank=True, verbose_name='标题')
    module = models.CharField(max_length=255, blank=True, verbose_name='模块')
    customer_name = models.CharField(max_length=255, blank=True, verbose_name='客户名称')
    priority = models.CharField(max_length=100, blank=True, verbose_name='优先级')
    status = models.CharField(max_length=100, blank=True, verbose_name='状态')
    description = models.TextField(blank=True, verbose_name='需求描述')
    creator = models.CharField(max_length=100, blank=True, verbose_name='创建人')
    handler = models.CharField(max_length=100, blank=True, verbose_name='处理人')
    tester = models.CharField(max_length=100, blank=True, verbose_name='测试人员')
    group_name = models.CharField(max_length=100, blank=True, verbose_name='责任组')
    frontend_developer = models.CharField(max_length=100, blank=True, verbose_name='前端开发')
    backend_developer = models.CharField(max_length=100, blank=True, verbose_name='后端开发')
    related_mindmaps = models.JSONField(default=list, blank=True, verbose_name='关联测试脑图')
    row_index = models.PositiveIntegerField(default=0, verbose_name='排序序号')
    raw_fields = models.JSONField(default=dict, blank=True, verbose_name='原始字段')
    synced_at = models.DateTimeField(default=timezone.now, verbose_name='同步时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'quality_analysis_jira_requirement_records'
        verbose_name = 'JIRA需求数据'
        verbose_name_plural = 'JIRA需求数据'
        ordering = ['-synced_at', 'row_index', 'issue_key']
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'issue_key'],
                name='uq_quality_analysis_jira_requirement_version_key',
            )
        ]

    def save(self, *args, **kwargs):
        self.version = normalize_jira_version(self.version)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.version} - {self.issue_key}'


class JiraRequirementRecordAttachment(models.Model):
    requirement = models.ForeignKey(
        JiraRequirementRecord,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='关联需求',
    )
    name = models.CharField(max_length=255, verbose_name='附件名称')
    file = models.FileField(upload_to='requirement_attachments/%Y/%m/', verbose_name='文件')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_requirement_attachments',
        verbose_name='上传人',
    )
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='上传时间')

    class Meta:
        db_table = 'quality_analysis_jira_requirement_record_attachments'
        verbose_name = '需求附件'
        verbose_name_plural = '需求附件'
        ordering = ['uploaded_at', 'id']

    def __str__(self):
        return self.name


@receiver(post_delete, sender=JiraRequirementRecord)
def cleanup_requirement_description_images(sender, instance, **kwargs):
    cleanup_rich_text_images(extract_rich_text_image_paths(instance.description))


@receiver(post_delete, sender=JiraRequirementRecordAttachment)
def cleanup_requirement_attachment_file(sender, instance, **kwargs):
    storage = instance.file.storage
    file_name = instance.file.name
    if file_name and storage.exists(file_name):
        storage.delete(file_name)
