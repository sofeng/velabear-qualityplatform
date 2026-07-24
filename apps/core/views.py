"""
Core 应用视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.http import HttpResponse
from django.urls import reverse

from apps.core.branding import PLATFORM_BRAND_NAME
from .models import UnifiedNotificationConfig
from .serializers import UnifiedNotificationConfigSerializer
from .notification_connections import (
    CONNECTION_MODE_AUTH,
    CONNECTION_STATUS_AUTHORIZING,
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_DISCONNECTED,
    CONNECTION_STATUS_ERROR,
    build_auth_connection_status,
    build_oauth_authorization_url,
    complete_oauth_authorization,
    normalize_bot_config,
    test_authorized_connection,
)

import logging
from html import escape
from urllib.parse import urlparse
logger = logging.getLogger(__name__)


class UnifiedNotificationConfigViewSet(viewsets.ModelViewSet):
    """统一通知配置视图集"""
    queryset = UnifiedNotificationConfig.objects.all()
    serializer_class = UnifiedNotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config_type', 'is_default', 'is_active']
    search_fields = ['name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'authorized_oauth_callback':
            return [AllowAny()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """创建通知配置"""
        instance = serializer.save(created_by=self.request.user)
        logger.info(f"创建统一通知配置: {instance.name}")

    def perform_update(self, serializer):
        """更新通知配置"""
        instance = serializer.save()
        logger.info(f"更新统一通知配置: {instance.name}")

    def perform_destroy(self, instance):
        """删除通知配置"""
        logger.info(f"删除统一通知配置: {instance.name}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        # 取消其他默认配置
        UnifiedNotificationConfig.objects.filter(is_default=True).update(is_default=False)
        # 设置当前为默认
        config.is_default = True
        config.save()
        return Response({'message': '已设置为默认配置'})

    @action(detail=False, methods=['get'])
    def active_configs(self, request):
        """获取所有启用的配置"""
        configs = UnifiedNotificationConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start_authorized_oauth(self, request, pk=None):
        """生成三方 OAuth 授权页面地址。"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        if not bot_type:
            return Response({'detail': 'bot_type 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        webhook_bots = {**(config.webhook_bots or {})}
        bot_config = {**(webhook_bots.get(bot_type) or {})}
        auth_connection = {**(bot_config.get('auth_connection') or {})}
        state = self._build_oauth_state(config.id, bot_type)
        callback_url = self._build_oauth_callback_url(request)
        result = build_oauth_authorization_url(
            bot_type,
            auth_connection,
            callback_url=callback_url,
            state=state,
        )
        if not result.get('ok'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        auth_connection['oauth_state'] = state
        auth_connection['oauth_callback_url'] = callback_url
        auth_connection['status'] = CONNECTION_STATUS_AUTHORIZING
        auth_connection['last_test_detail'] = '等待用户在三方授权页面完成授权。'
        bot_config['connection_mode'] = CONNECTION_MODE_AUTH
        bot_config['auth_connection'] = auth_connection
        webhook_bots[bot_type] = normalize_bot_config(bot_type, bot_config, webhook_bots.get(bot_type) or {})
        config.webhook_bots = webhook_bots
        config.save(update_fields=['webhook_bots', 'updated_at'])

        return Response({
            **result,
            'auth_status': build_auth_connection_status(bot_type, config.webhook_bots[bot_type].get('auth_connection')),
        })

    @action(detail=False, methods=['get'], url_path='authorized-oauth-callback')
    def authorized_oauth_callback(self, request):
        """三方 OAuth 授权回调入口，用于弹窗授权完成后写回本地状态。"""
        state_value = request.query_params.get('state') or ''
        code = request.query_params.get('code') or request.query_params.get('authCode') or request.query_params.get('auth_code') or ''
        error = request.query_params.get('error') or request.query_params.get('errmsg') or ''
        parsed_state = self._parse_oauth_state(state_value)
        if not parsed_state:
            return self._oauth_popup_response(False, '授权回调缺少有效 state，无法匹配通知机器人配置。')

        config_id, bot_type = parsed_state
        try:
            config = UnifiedNotificationConfig.objects.get(pk=config_id)
        except UnifiedNotificationConfig.DoesNotExist:
            return self._oauth_popup_response(False, '授权回调对应的通知机器人配置不存在。')

        webhook_bots = {**(config.webhook_bots or {})}
        bot_config = {**(webhook_bots.get(bot_type) or {})}
        auth_connection = {**(bot_config.get('auth_connection') or {})}
        if auth_connection.get('oauth_state') != state_value:
            return self._oauth_popup_response(False, '授权回调 state 校验失败，请重新发起授权。')

        if error:
            auth_connection['status'] = CONNECTION_STATUS_ERROR
            auth_connection['last_test_detail'] = f'三方授权失败：{error}'
            auth_connection['oauth_state'] = ''
            ok = False
            detail = auth_connection['last_test_detail']
        elif not code:
            auth_connection['status'] = CONNECTION_STATUS_ERROR
            auth_connection['last_test_detail'] = '三方授权回调缺少授权码。'
            auth_connection['oauth_state'] = ''
            ok = False
            detail = auth_connection['last_test_detail']
        else:
            result = complete_oauth_authorization(
                bot_type,
                auth_connection,
                code=code,
                callback_url=auth_connection.get('oauth_callback_url') or self._build_oauth_callback_url(request),
            )
            auth_connection = result.get('auth_connection') or auth_connection
            ok = bool(result.get('ok'))
            detail = result.get('detail') or ('授权完成。' if ok else '授权失败。')

        bot_config['connection_mode'] = CONNECTION_MODE_AUTH
        bot_config['auth_connection'] = auth_connection
        webhook_bots[bot_type] = normalize_bot_config(bot_type, bot_config, webhook_bots.get(bot_type) or {})
        config.webhook_bots = webhook_bots
        config.save(update_fields=['webhook_bots', 'updated_at'])

        return self._oauth_popup_response(ok, detail)

    @action(detail=True, methods=['post'])
    def test_authorized_connection(self, request, pk=None):
        """测试授权连接配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        if not bot_type:
            return Response({'detail': 'bot_type 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        bot_config = (config.webhook_bots or {}).get(bot_type) or {}
        auth_connection = bot_config.get('auth_connection') or {}
        result = test_authorized_connection(bot_type, auth_connection)

        bot_config['connection_mode'] = CONNECTION_MODE_AUTH
        auth_connection['status'] = result.get('status') or (CONNECTION_STATUS_CONNECTED if result.get('ok') else CONNECTION_STATUS_ERROR)
        auth_connection['last_test_detail'] = result.get('detail') or ''
        bot_config['auth_connection'] = auth_connection

        webhook_bots = {**(config.webhook_bots or {}), bot_type: normalize_bot_config(bot_type, bot_config, bot_config)}
        config.webhook_bots = webhook_bots
        config.save(update_fields=['webhook_bots', 'updated_at'])

        return Response({
            **result,
            'auth_status': build_auth_connection_status(bot_type, config.webhook_bots[bot_type].get('auth_connection')),
        })

    @action(detail=True, methods=['post'])
    def disconnect_authorized_connection(self, request, pk=None):
        """撤销本地授权连接配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        if not bot_type:
            return Response({'detail': 'bot_type 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        webhook_bots = {**(config.webhook_bots or {})}
        bot_config = {**(webhook_bots.get(bot_type) or {})}
        auth_connection = {**(bot_config.get('auth_connection') or {})}
        for field in ('access_token', 'refresh_token', 'tenant_access_token'):
            auth_connection.pop(field, None)
        for field in ('oauth_state', 'last_authorized_at', 'authorized_user_id', 'authorized_open_id', 'authorized_union_id', 'authorized_user_name'):
            auth_connection.pop(field, None)
        auth_connection['status'] = CONNECTION_STATUS_DISCONNECTED
        auth_connection['last_test_detail'] = f'已在 {PLATFORM_BRAND_NAME} 断开本地授权连接。'
        bot_config['auth_connection'] = auth_connection
        bot_config['connection_mode'] = 'webhook' if bot_config.get('webhook_url') else CONNECTION_MODE_AUTH
        webhook_bots[bot_type] = normalize_bot_config(bot_type, bot_config, webhook_bots.get(bot_type) or {})
        config.webhook_bots = webhook_bots
        config.save(update_fields=['webhook_bots', 'updated_at'])

        return Response({
            'ok': True,
            'status': CONNECTION_STATUS_DISCONNECTED,
            'detail': '已断开授权连接。',
            'auth_status': build_auth_connection_status(bot_type, auth_connection),
        })

    @action(detail=True, methods=['get'])
    def authorized_connection_status(self, request, pk=None):
        """获取授权连接状态"""
        config = self.get_object()
        bot_type = request.query_params.get('bot_type')
        if not bot_type:
            return Response({'detail': 'bot_type 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        bot_config = (config.webhook_bots or {}).get(bot_type) or {}
        return Response(build_auth_connection_status(bot_type, bot_config.get('auth_connection') or {}))

    @staticmethod
    def _build_oauth_state(config_id, bot_type):
        import secrets
        return f'{config_id}:{bot_type}:{secrets.token_urlsafe(24)}'

    @staticmethod
    def _parse_oauth_state(state_value):
        parts = str(state_value or '').split(':', 2)
        if len(parts) != 3:
            return None
        config_id, bot_type, token = parts
        if not config_id.isdigit() or bot_type not in {'feishu', 'wechat', 'dingtalk'} or not token:
            return None
        return int(config_id), bot_type

    @staticmethod
    def _build_oauth_callback_url(request):
        callback_path = reverse('unified-notification-config-authorized-oauth-callback')
        for header_name in ('Origin', 'Referer'):
            raw_value = request.headers.get(header_name)
            if not raw_value:
                continue
            parsed = urlparse(raw_value)
            if parsed.scheme in {'http', 'https'} and parsed.netloc:
                return f'{parsed.scheme}://{parsed.netloc}{callback_path}'
        return request.build_absolute_uri(callback_path)

    @staticmethod
    def _oauth_popup_response(ok, detail):
        status_text = '授权成功' if ok else '授权失败'
        detail_text = str(detail or '')
        html_detail = escape(detail_text)
        js_detail = (
            detail_text
            .replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace('\r', ' ')
            .replace('\n', ' ')
            .replace('</', '<\\/')
        )
        html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{status_text}</title>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1f2937; background: #f8fafc; }}
    main {{ width: min(420px, calc(100vw - 40px)); padding: 28px; border: 1px solid #e5e7eb; border-radius: 8px; background: white; box-shadow: 0 18px 45px rgba(15, 23, 42, .12); }}
    h1 {{ margin: 0 0 12px; font-size: 20px; }}
    p {{ margin: 0; color: #667085; line-height: 1.6; }}
  </style>
</head>
<body>
  <main>
    <h1>{status_text}</h1>
    <p>{html_detail}</p>
  </main>
  <script>
    const payload = {{ source: 'testhub-notification-oauth', ok: {str(bool(ok)).lower()}, detail: '{js_detail}' }};
    if (window.opener) {{
      window.opener.postMessage(payload, '*');
      setTimeout(() => window.close(), 900);
    }}
  </script>
</body>
</html>"""
        return HttpResponse(html, content_type='text/html; charset=utf-8')
