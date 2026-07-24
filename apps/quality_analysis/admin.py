from django.contrib import admin

from .models import JiraBugRecord, JiraInterfaceConfig, QualityReport


@admin.register(QualityReport)
class QualityReportAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'status',
        'total_defects',
        'classified_defects',
        'created_by',
        'created_at',
        'analyzed_at',
    )
    search_fields = ('version', 'share_token')
    list_filter = ('status', 'created_at', 'analyzed_at')


@admin.register(JiraInterfaceConfig)
class JiraInterfaceConfigAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'name',
        'request_method',
        'last_status_code',
        'last_record_count',
        'last_executed_at',
        'is_active',
    )
    search_fields = ('version', 'name', 'request_url')
    list_filter = ('request_method', 'is_active', 'last_executed_at')


@admin.register(JiraBugRecord)
class JiraBugRecordAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'issue_key',
        'issue_type',
        'priority',
        'status',
        'customer_name',
        'synced_at',
    )
    search_fields = ('version', 'issue_key', 'summary', 'customer_name')
    list_filter = ('version', 'status', 'priority', 'synced_at')
