"""
Core 应用序列化器
"""
from rest_framework import serializers
from .models import UnifiedNotificationConfig
from .notification_connections import (
    build_auth_connection_status,
    mask_bot_config,
    normalize_bot_config,
)


class UnifiedNotificationConfigSerializer(serializers.ModelSerializer):
    """统一通知配置序列化器"""

    webhook_bots_display = serializers.SerializerMethodField()
    auth_connections_display = serializers.SerializerMethodField()

    class Meta:
        model = UnifiedNotificationConfig
        fields = [
            'id', 'name', 'config_type', 'webhook_bots',
            'is_default', 'is_active', 'created_at', 'updated_at',
            'created_by', 'webhook_bots_display', 'auth_connections_display'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'created_by',
            'webhook_bots_display', 'auth_connections_display',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['webhook_bots'] = {
            bot_type: mask_bot_config({
                **(bot_config or {}),
                'type': bot_type,
            })
            for bot_type, bot_config in (instance.webhook_bots or {}).items()
        }
        return data

    def validate_webhook_bots(self, value):
        existing = {}
        if self.instance and self.instance.webhook_bots:
            existing = self.instance.webhook_bots

        normalized = {}
        for bot_type, bot_config in (value or {}).items():
            normalized[bot_type] = normalize_bot_config(
                bot_type,
                bot_config,
                existing.get(bot_type) or {},
            )
        return normalized

    def get_webhook_bots_display(self, obj):
        """获取webhook机器人显示信息"""
        bots = obj.get_webhook_bots()
        display_list = []
        for bot in bots:
            display_list.append({
                'type': bot.get('type'),
                'name': bot.get('name'),
                'enabled': bot.get('enabled'),
                'connection_mode': bot.get('connection_mode'),
                'enable_ui_automation': bot.get('enable_ui_automation'),
                'enable_api_testing': bot.get('enable_api_testing')
            })
        return display_list

    def get_auth_connections_display(self, obj):
        """获取授权连接显示信息"""
        display_list = []
        for bot_type, bot_config in (obj.webhook_bots or {}).items():
            auth_connection = (bot_config or {}).get('auth_connection') or {}
            display_list.append({
                'type': bot_type,
                'name': (bot_config or {}).get('name', f'{bot_type}机器人'),
                'connection_mode': (bot_config or {}).get('connection_mode', 'webhook'),
                **build_auth_connection_status(bot_type, auth_connection),
            })
        return display_list
