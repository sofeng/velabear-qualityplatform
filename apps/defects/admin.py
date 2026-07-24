from django.contrib import admin

from .models import Defect, DefectAttachment, DefectComment, DefectEmailConfig, DefectHistory


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ['code', 'record_type', 'title', 'project', 'version', 'severity', 'status', 'created_by', 'updated_at']
    list_filter = ['record_type', 'project', 'version', 'severity', 'status']
    search_fields = ['code', 'title', 'description', 'requirement_id']


@admin.register(DefectAttachment)
class DefectAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'defect', 'name', 'uploaded_by', 'uploaded_at']
    search_fields = ['name', 'defect__code', 'defect__title']


@admin.register(DefectComment)
class DefectCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'defect', 'author', 'created_at', 'updated_at']
    search_fields = ['defect__code', 'defect__title', 'content']


@admin.register(DefectHistory)
class DefectHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'defect', 'field', 'action', 'changed_by', 'created_at']
    list_filter = ['action', 'field']
    search_fields = ['defect__code', 'defect__title', 'field']


@admin.register(DefectEmailConfig)
class DefectEmailConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'port', 'from_name', 'from_email', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['host', 'username', 'from_name', 'from_email']
