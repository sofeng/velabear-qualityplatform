"""
Notification robot connection helpers.

The notification page stores both legacy Webhook config and app-authorized
connection config in UnifiedNotificationConfig.webhook_bots for backward
compatibility with existing UI/API automation callers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import json
import secrets
import time
from datetime import datetime, timezone
from copy import deepcopy
from typing import Any
from urllib.parse import quote_plus, urlencode

import requests

from apps.core.plaintext_secrets import decrypt_password, encrypt_password, is_serialized_fernet_secret


logger = logging.getLogger(__name__)

CONNECTION_MODE_WEBHOOK = 'webhook'
CONNECTION_MODE_AUTH = 'auth'
CONNECTION_STATUS_CONNECTED = 'connected'
CONNECTION_STATUS_DISCONNECTED = 'disconnected'
CONNECTION_STATUS_ERROR = 'error'
CONNECTION_STATUS_PENDING = 'pending'
CONNECTION_STATUS_AUTHORIZING = 'authorizing'

SECRET_PRESERVE_MARKERS = {'********', '******', '••••••••', '已配置，留空不变'}
BOT_TOP_LEVEL_SECRET_FIELDS = {'secret'}
BOT_AUTH_SECRET_FIELDS = {
    'app_secret',
    'client_secret',
    'corp_secret',
    'suite_secret',
    'access_token',
    'refresh_token',
    'tenant_access_token',
}

BOT_AUTH_AUTHORIZE_REQUIRED_FIELDS = {
    'feishu': ('app_id', 'app_secret'),
    'dingtalk': ('app_key', 'app_secret'),
    'wechat': ('corp_id', 'corp_secret', 'agent_id'),
}

BOT_AUTH_REQUIRED_FIELDS = {
    'feishu': ('app_id', 'app_secret', 'default_receive_id'),
    'dingtalk': ('app_key', 'app_secret', 'robot_code', 'open_conversation_id'),
    'wechat': ('corp_id', 'corp_secret', 'agent_id', 'default_to_user'),
}

BOT_AUTH_FIELD_LABELS = {
    'app_id': 'App ID',
    'app_key': 'AppKey',
    'app_secret': 'App Secret',
    'corp_id': '企业 ID',
    'corp_secret': '应用 Secret',
    'agent_id': '应用 Agent ID',
    'robot_code': '机器人编码',
    'open_conversation_id': '群会话 ID',
    'default_receive_id': '默认会话 ID',
    'default_to_user': '默认接收成员',
    'oauth_scope': '授权范围',
}

BOT_AUTH_PUBLIC_INFO_FIELDS = {
    'provider',
    'status',
    'last_test_detail',
    'tenant_name',
    'corp_name',
    'app_id',
    'app_key',
    'corp_id',
    'agent_id',
    'robot_code',
    'open_conversation_id',
    'default_receive_id',
    'default_to_user',
    'receive_id_type',
    'oauth_scope',
    'oauth_callback_url',
    'last_authorized_at',
    'authorized_user_id',
    'authorized_open_id',
    'authorized_union_id',
    'authorized_user_name',
}

BOT_AUTH_RESPONSE_PRIVATE_FIELDS = {'oauth_state'}

BOT_AUTH_DEFAULT_SCOPES = {
    'feishu': '',
    'dingtalk': 'openid corpid',
    'wechat': 'snsapi_privateinfo',
}


def normalize_bot_config(bot_type: str, incoming: dict[str, Any] | None, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize and encrypt sensitive values before saving JSON config."""
    incoming = deepcopy(incoming or {})
    existing = existing or {}
    incoming.pop('type', None)
    for field in BOT_TOP_LEVEL_SECRET_FIELDS:
        incoming.pop(f'has_{field}', None)

    connection_mode = str(incoming.get('connection_mode') or existing.get('connection_mode') or CONNECTION_MODE_WEBHOOK)
    if connection_mode not in {CONNECTION_MODE_WEBHOOK, CONNECTION_MODE_AUTH}:
        connection_mode = CONNECTION_MODE_WEBHOOK
    incoming['connection_mode'] = connection_mode

    for field in BOT_TOP_LEVEL_SECRET_FIELDS:
        if field in incoming or field in existing:
            incoming[field] = _normalize_secret_value(incoming.get(field), existing.get(field))

    auth_connection = incoming.get('auth_connection') or {}
    existing_auth = existing.get('auth_connection') or {}
    if auth_connection or existing_auth or connection_mode == CONNECTION_MODE_AUTH:
        incoming['auth_connection'] = normalize_auth_connection(bot_type, auth_connection, existing_auth)

    return incoming


def normalize_auth_connection(bot_type: str, incoming: dict[str, Any] | None, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    incoming = deepcopy(incoming or {})
    existing = existing or {}
    incoming.pop('required_fields', None)
    for field in BOT_AUTH_SECRET_FIELDS:
        incoming.pop(f'has_{field}', None)

    auth = {
        **existing,
        **incoming,
        'provider': bot_type,
    }
    auth['status'] = str(auth.get('status') or CONNECTION_STATUS_DISCONNECTED)
    if auth['status'] not in {
        CONNECTION_STATUS_CONNECTED,
        CONNECTION_STATUS_DISCONNECTED,
        CONNECTION_STATUS_ERROR,
        CONNECTION_STATUS_PENDING,
        CONNECTION_STATUS_AUTHORIZING,
    }:
        auth['status'] = CONNECTION_STATUS_DISCONNECTED

    for field in BOT_AUTH_SECRET_FIELDS:
        if field in auth or field in existing:
            auth[field] = _normalize_secret_value(incoming.get(field), existing.get(field))

    return auth


def mask_bot_config(bot_config: dict[str, Any] | None) -> dict[str, Any]:
    """Return config for API responses without exposing stored secrets."""
    masked = deepcopy(bot_config or {})
    for field in BOT_TOP_LEVEL_SECRET_FIELDS:
        if field in masked:
            masked[f'has_{field}'] = bool(masked.get(field))
            masked[field] = ''

    auth = masked.get('auth_connection')
    if isinstance(auth, dict):
        for field in BOT_AUTH_RESPONSE_PRIVATE_FIELDS:
            auth.pop(field, None)
        for field in BOT_AUTH_SECRET_FIELDS:
            if field in auth:
                auth[f'has_{field}'] = bool(auth.get(field))
                auth[field] = ''
        auth['required_fields'] = list(BOT_AUTH_REQUIRED_FIELDS.get(masked.get('type') or auth.get('provider') or '', ()))
        auth['authorize_required_fields'] = list(BOT_AUTH_AUTHORIZE_REQUIRED_FIELDS.get(masked.get('type') or auth.get('provider') or '', ()))

    return masked


def decrypt_bot_config(bot_config: dict[str, Any] | None) -> dict[str, Any]:
    decrypted = deepcopy(bot_config or {})
    for field in BOT_TOP_LEVEL_SECRET_FIELDS:
        if decrypted.get(field):
            decrypted[field] = decrypt_secret_value(decrypted[field])

    auth = decrypted.get('auth_connection')
    if isinstance(auth, dict):
        for field in BOT_AUTH_SECRET_FIELDS:
            if auth.get(field):
                auth[field] = decrypt_secret_value(auth[field])

    return decrypted


def decrypt_secret_value(value: str) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    if not is_serialized_fernet_secret(text):
        return text
    return decrypt_password(text)


def get_missing_auth_fields(bot_type: str, auth_connection: dict[str, Any] | None, purpose: str = 'send') -> list[str]:
    auth = auth_connection or {}
    missing = []
    required_fields = BOT_AUTH_AUTHORIZE_REQUIRED_FIELDS if purpose == 'authorize' else BOT_AUTH_REQUIRED_FIELDS
    for field in required_fields.get(bot_type, ()):
        if not str(auth.get(field) or '').strip():
            missing.append(field)
    return missing


def build_auth_connection_status(bot_type: str, auth_connection: dict[str, Any] | None) -> dict[str, Any]:
    auth = auth_connection or {}
    status_value = auth.get('status') or (CONNECTION_STATUS_PENDING if auth else CONNECTION_STATUS_DISCONNECTED)
    missing = get_missing_auth_fields(bot_type, auth)
    missing_authorize = get_missing_auth_fields(bot_type, auth, purpose='authorize')
    return {
        'provider': bot_type,
        'status': status_value,
        'missing_fields': missing,
        'missing_labels': [BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing],
        'missing_authorize_fields': missing_authorize,
        'missing_authorize_labels': [BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing_authorize],
        'authorizable': not missing_authorize,
        'ready': status_value == CONNECTION_STATUS_CONNECTED and not missing,
        'authorized_user_name': auth.get('authorized_user_name') or '',
        'last_authorized_at': auth.get('last_authorized_at') or '',
    }


def build_oauth_authorization_url(
    bot_type: str,
    auth_connection: dict[str, Any] | None,
    *,
    callback_url: str,
    state: str | None = None,
) -> dict[str, Any]:
    """Build a provider OAuth URL that the browser can open in a popup."""
    auth = decrypt_auth_connection(auth_connection or {})
    missing = get_missing_auth_fields(bot_type, auth, purpose='authorize')
    if missing:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_PENDING,
            'detail': '缺少发起授权所需字段：' + '、'.join(BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing),
            'missing_fields': missing,
        }

    state = state or secrets.token_urlsafe(32)
    if bot_type == 'feishu':
        params = {
            'app_id': auth.get('app_id'),
            'redirect_uri': callback_url,
            'state': state,
        }
        if auth.get('oauth_scope'):
            params['scope'] = auth.get('oauth_scope')
        authorization_url = 'https://open.feishu.cn/open-apis/authen/v1/authorize?' + urlencode(params)
    elif bot_type == 'dingtalk':
        params = {
            'redirect_uri': callback_url,
            'response_type': 'code',
            'client_id': auth.get('app_key'),
            'scope': auth.get('oauth_scope') or BOT_AUTH_DEFAULT_SCOPES['dingtalk'],
            'state': state,
            'prompt': 'consent',
        }
        authorization_url = 'https://login.dingtalk.com/oauth2/auth?' + urlencode(params)
    elif bot_type == 'wechat':
        params = {
            'appid': auth.get('corp_id'),
            'agentid': auth.get('agent_id'),
            'redirect_uri': callback_url,
            'state': state,
        }
        authorization_url = 'https://open.work.weixin.qq.com/wwopen/sso/qrConnect?' + urlencode(params)
    else:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': '暂不支持该机器人类型的授权页面。',
        }

    return {
        'ok': True,
        'status': CONNECTION_STATUS_AUTHORIZING,
        'authorization_url': authorization_url,
        'callback_url': callback_url,
        'state': state,
        'detail': '请在弹出的三方授权页面完成授权。',
    }


def complete_oauth_authorization(
    bot_type: str,
    auth_connection: dict[str, Any] | None,
    *,
    code: str,
    callback_url: str | None = None,
) -> dict[str, Any]:
    """Exchange provider OAuth code and return an updated auth_connection."""
    auth = decrypt_auth_connection(auth_connection or {})
    missing = get_missing_auth_fields(bot_type, auth, purpose='authorize')
    if missing:
        auth['status'] = CONNECTION_STATUS_PENDING
        auth['last_test_detail'] = '缺少完成授权所需字段：' + '、'.join(BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing)
        return {
            'ok': False,
            'status': CONNECTION_STATUS_PENDING,
            'detail': auth['last_test_detail'],
            'auth_connection': auth,
        }

    try:
        if bot_type == 'feishu':
            result = _complete_feishu_oauth(auth, code, callback_url=callback_url)
        elif bot_type == 'dingtalk':
            result = _complete_dingtalk_oauth(auth, code)
        elif bot_type == 'wechat':
            result = _complete_wechat_oauth(auth, code)
        else:
            result = {
                'ok': False,
                'status': CONNECTION_STATUS_ERROR,
                'detail': '暂不支持该机器人类型的授权回调。',
                'auth_connection': auth,
            }
    except requests.RequestException as exc:
        logger.warning('通知机器人 OAuth 授权回调失败: bot_type=%s error=%s', bot_type, exc)
        auth['status'] = CONNECTION_STATUS_ERROR
        auth['last_test_detail'] = f'连接三方授权服务失败：{exc}'
        result = {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': auth['last_test_detail'],
            'auth_connection': auth,
        }
    except Exception as exc:
        logger.exception('通知机器人 OAuth 授权回调异常: bot_type=%s', bot_type)
        auth['status'] = CONNECTION_STATUS_ERROR
        auth['last_test_detail'] = f'授权回调处理异常：{exc}'
        result = {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': auth['last_test_detail'],
            'auth_connection': auth,
        }

    result['auth_connection']['oauth_state'] = ''
    result['auth_connection']['last_authorized_at'] = _utc_now_iso() if result.get('ok') else result['auth_connection'].get('last_authorized_at', '')
    return result


def test_authorized_connection(bot_type: str, auth_connection: dict[str, Any] | None) -> dict[str, Any]:
    """Validate an already authorized connection with the provider token API."""
    auth = decrypt_auth_connection(auth_connection or {})
    if auth.get('status') != CONNECTION_STATUS_CONNECTED:
        return {
            'ok': False,
            'status': auth.get('status') or CONNECTION_STATUS_DISCONNECTED,
            'detail': '尚未完成三方授权，请先在通知机器人页面打开授权页并完成授权。',
        }

    missing = get_missing_auth_fields(bot_type, auth)
    if missing:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_PENDING,
            'detail': '缺少授权连接字段：' + '、'.join(BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing),
            'missing_fields': missing,
        }

    try:
        if bot_type == 'feishu':
            return _test_feishu_connection(auth)
        if bot_type == 'wechat':
            return _test_wechat_connection(auth)
        if bot_type == 'dingtalk':
            return _test_dingtalk_connection(auth)
    except requests.RequestException as exc:
        logger.warning('通知机器人授权连接测试失败: bot_type=%s error=%s', bot_type, exc)
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': f'连接三方授权服务失败：{exc}',
        }
    except Exception as exc:
        logger.exception('通知机器人授权连接测试异常: bot_type=%s', bot_type)
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': f'授权连接校验异常：{exc}',
        }

    return {
        'ok': False,
        'status': CONNECTION_STATUS_ERROR,
        'detail': '暂不支持该机器人类型的授权连接校验。',
    }


def decrypt_auth_connection(auth_connection: dict[str, Any]) -> dict[str, Any]:
    auth = deepcopy(auth_connection or {})
    for field in BOT_AUTH_SECRET_FIELDS:
        if auth.get(field):
            auth[field] = decrypt_secret_value(auth[field])
    return auth


def sanitize_bot_for_log(bot: dict[str, Any] | None) -> dict[str, Any]:
    bot = deepcopy(bot or {})
    for field in BOT_TOP_LEVEL_SECRET_FIELDS:
        if field in bot:
            bot[f'has_{field}'] = bool(bot.get(field))
            bot.pop(field, None)

    auth = bot.get('auth_connection')
    if isinstance(auth, dict):
        bot['auth_connection'] = {
            key: value
            for key, value in auth.items()
            if key in BOT_AUTH_PUBLIC_INFO_FIELDS
        }
        for field in BOT_AUTH_SECRET_FIELDS:
            if auth.get(field):
                bot['auth_connection'][f'has_{field}'] = True
    return bot


def send_authorized_notification(
    bot: dict[str, Any],
    *,
    title: str,
    markdown_text: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send notification through provider app authorization."""
    bot_type = bot.get('type')
    auth = decrypt_auth_connection(bot.get('auth_connection') or {})
    if auth.get('status') != CONNECTION_STATUS_CONNECTED:
        return {
            'ok': False,
            'status': auth.get('status') or CONNECTION_STATUS_DISCONNECTED,
            'channel': 'authorized',
            'detail': '尚未完成三方授权，请先在通知机器人页面打开授权页并完成授权。',
            'request_payload': {},
            'response_info': {},
        }

    missing = get_missing_auth_fields(bot_type, auth)
    if missing:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_PENDING,
            'channel': 'authorized',
            'detail': '缺少授权连接字段：' + '、'.join(BOT_AUTH_FIELD_LABELS.get(field, field) for field in missing),
            'request_payload': {},
            'response_info': {},
        }

    if bot_type == 'feishu':
        return _send_feishu_authorized_message(auth, title=title, markdown_text=markdown_text, timeout=timeout)
    if bot_type == 'wechat':
        return _send_wechat_authorized_message(auth, title=title, markdown_text=markdown_text, timeout=timeout)
    if bot_type == 'dingtalk':
        return _send_dingtalk_authorized_message(auth, title=title, markdown_text=markdown_text, timeout=timeout)

    return {
        'ok': False,
        'status': CONNECTION_STATUS_ERROR,
        'channel': 'authorized',
        'detail': '暂不支持该机器人类型的授权发送。',
        'request_payload': {},
        'response_info': {},
    }


def send_notification_bot(
    bot: dict[str, Any],
    *,
    title: str,
    markdown_text: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send a notification through the bot's configured connection mode."""
    connection_mode = bot.get('connection_mode') or CONNECTION_MODE_WEBHOOK
    if connection_mode == CONNECTION_MODE_AUTH:
        return send_authorized_notification(
            bot,
            title=title,
            markdown_text=markdown_text,
            timeout=timeout,
        )
    return send_webhook_notification(
        bot,
        title=title,
        markdown_text=markdown_text,
        timeout=timeout,
    )


def send_webhook_notification(
    bot: dict[str, Any],
    *,
    title: str,
    markdown_text: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send notification through a legacy incoming webhook robot."""
    bot = decrypt_bot_config(bot or {})
    bot_type = bot.get('type')
    if bot.get('enabled') is False:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_DISCONNECTED,
            'channel': 'webhook',
            'detail': '机器人未开启。',
            'request_payload': {},
            'response_info': {},
        }

    webhook_url = str(bot.get('webhook_url') or '').strip()
    if not webhook_url:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_PENDING,
            'channel': 'webhook',
            'detail': '机器人尚未配置 Webhook URL。',
            'request_payload': {},
            'response_info': {},
        }

    message_payload = build_webhook_notification_payload(bot_type, title=title, markdown_text=markdown_text)
    if bot_type == 'dingtalk' and bot.get('secret'):
        webhook_url = _append_dingtalk_webhook_signature(webhook_url, bot.get('secret'))

    try:
        response = requests.post(
            webhook_url,
            json=message_payload,
            headers={'Content-Type': 'application/json'},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning('Webhook notification failed: bot_type=%s error=%s', bot_type, exc)
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'channel': 'webhook',
            'detail': f'Webhook 请求失败：{exc}',
            'request_payload': _redact_message_payload(message_payload),
            'response_info': {},
        }

    payload = _safe_json(response)
    provider_code = payload.get('code') if 'code' in payload else payload.get('errcode', payload.get('StatusCode'))
    has_provider_code = provider_code is not None
    ok = response.ok and (not has_provider_code or provider_code in (0, '0'))
    detail = (
        'Webhook 消息发送成功。'
        if ok
        else payload.get('msg') or payload.get('errmsg') or payload.get('StatusMessage') or response.text[:200]
    )
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'channel': 'webhook',
        'detail': detail,
        'request_payload': _redact_message_payload(message_payload),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': provider_code,
        },
    }


def build_webhook_notification_payload(bot_type: str, *, title: str, markdown_text: str) -> dict[str, Any]:
    content = f'**{title}**\n\n{markdown_text}'.strip()
    if bot_type == 'feishu':
        return {
            'msg_type': 'interactive',
            'card': {
                'elements': [{
                    'tag': 'div',
                    'text': {
                        'content': content,
                        'tag': 'lark_md',
                    },
                }],
                'header': {
                    'title': {
                        'content': title,
                        'tag': 'plain_text',
                    },
                    'template': 'blue',
                },
            },
        }
    if bot_type == 'wechat':
        return {
            'msgtype': 'markdown',
            'markdown': {
                'content': content,
            },
        }
    if bot_type == 'dingtalk':
        return {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': content,
            },
        }
    return {
        'text': f'{title}\n\n{markdown_text}'.strip(),
    }


def _normalize_secret_value(incoming_value: Any, existing_value: Any = None) -> str:
    text = str(incoming_value or '').strip()
    if not text or text in SECRET_PRESERVE_MARKERS:
        return str(existing_value or '').strip()
    if is_serialized_fernet_secret(text):
        return text
    return encrypt_password(text)


def _test_feishu_connection(auth: dict[str, Any]) -> dict[str, Any]:
    token_result = _get_feishu_tenant_access_token(auth, timeout=10)
    ok = token_result.get('ok') and bool(token_result.get('tenant_access_token'))
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'detail': '飞书授权连接校验成功。' if ok else token_result.get('detail') or '飞书授权连接校验失败。',
        'provider_response_code': token_result.get('provider_response_code'),
    }


def _test_wechat_connection(auth: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
        params={
            'corpid': auth.get('corp_id'),
            'corpsecret': auth.get('corp_secret'),
        },
        timeout=10,
    )
    payload = _safe_json(response)
    ok = response.ok and payload.get('errcode') == 0 and bool(payload.get('access_token'))
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'detail': '企业微信授权连接校验成功。' if ok else payload.get('errmsg') or response.text[:200],
        'provider_response_code': payload.get('errcode'),
    }


def _test_dingtalk_connection(auth: dict[str, Any]) -> dict[str, Any]:
    token_result = _get_dingtalk_access_token(auth, timeout=10)
    ok = token_result.get('ok') and bool(token_result.get('access_token'))
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'detail': '钉钉授权连接校验成功。' if ok else token_result.get('detail', '钉钉授权连接校验失败。'),
        'provider_response_code': token_result.get('provider_response_code'),
    }


def _send_feishu_authorized_message(auth: dict[str, Any], *, title: str, markdown_text: str, timeout: int) -> dict[str, Any]:
    token_result = _get_feishu_tenant_access_token(auth, timeout=timeout)
    tenant_access_token = token_result.get('tenant_access_token')
    if not token_result.get('ok') or not tenant_access_token:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'channel': 'authorized',
            'detail': token_result.get('detail') or '获取飞书 tenant_access_token 失败。',
            'request_payload': {},
            'response_info': token_result.get('response_info') or {},
        }

    receive_id_type = auth.get('receive_id_type') or 'chat_id'
    message_payload = {
        'receive_id': auth.get('default_receive_id'),
        'msg_type': 'text',
        'content': json.dumps({'text': f'{title}\n\n{markdown_text}'}, ensure_ascii=False),
    }
    response = requests.post(
        f'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}',
        headers={
            'Authorization': f'Bearer {tenant_access_token}',
            'Content-Type': 'application/json',
        },
        json=message_payload,
        timeout=timeout,
    )
    payload = _safe_json(response)
    ok = response.ok and payload.get('code') == 0
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'channel': 'authorized',
        'detail': '飞书授权消息发送成功。' if ok else payload.get('msg') or response.text[:200],
        'request_payload': _redact_message_payload(message_payload),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('code'),
        },
    }


def _send_wechat_authorized_message(auth: dict[str, Any], *, title: str, markdown_text: str, timeout: int) -> dict[str, Any]:
    token_response = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
        params={
            'corpid': auth.get('corp_id'),
            'corpsecret': auth.get('corp_secret'),
        },
        timeout=timeout,
    )
    token_payload = _safe_json(token_response)
    access_token = token_payload.get('access_token')
    if not token_response.ok or token_payload.get('errcode') != 0 or not access_token:
        return _provider_result(False, 'authorized', token_response, token_payload, token_payload.get('errmsg') or '获取企业微信 access_token 失败。')

    message_payload = {
        'touser': auth.get('default_to_user'),
        'msgtype': 'text',
        'agentid': _safe_int(auth.get('agent_id')),
        'text': {
            'content': f'{title}\n\n{markdown_text}',
        },
        'safe': 0,
    }
    response = requests.post(
        'https://qyapi.weixin.qq.com/cgi-bin/message/send',
        params={'access_token': access_token},
        json=message_payload,
        timeout=timeout,
    )
    payload = _safe_json(response)
    ok = response.ok and payload.get('errcode') == 0
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'channel': 'authorized',
        'detail': '企业微信授权消息发送成功。' if ok else payload.get('errmsg') or response.text[:200],
        'request_payload': _redact_message_payload(message_payload),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('errcode'),
        },
    }


def _send_dingtalk_authorized_message(auth: dict[str, Any], *, title: str, markdown_text: str, timeout: int) -> dict[str, Any]:
    token_result = _get_dingtalk_access_token(auth, timeout=timeout)
    access_token = token_result.get('access_token')
    if not token_result.get('ok') or not access_token:
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'channel': 'authorized',
            'detail': token_result.get('detail') or '获取钉钉 accessToken 失败。',
            'request_payload': {},
            'response_info': token_result.get('response_info') or {},
        }

    message_payload = {
        'robotCode': auth.get('robot_code'),
        'openConversationId': auth.get('open_conversation_id'),
        'msgKey': 'sampleMarkdown',
        'msgParam': json.dumps({
            'title': title,
            'text': f'### {title}\n\n{markdown_text}',
        }, ensure_ascii=False),
    }
    response = requests.post(
        'https://api.dingtalk.com/v1.0/robot/groupMessages/send',
        headers={
            'x-acs-dingtalk-access-token': access_token,
            'Content-Type': 'application/json',
        },
        json=message_payload,
        timeout=timeout,
    )
    payload = _safe_json(response)
    ok = response.ok and not payload.get('code')
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'channel': 'authorized',
        'detail': '钉钉授权消息发送成功。' if ok else payload.get('message') or response.text[:200],
        'request_payload': _redact_message_payload(message_payload),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('code'),
        },
    }


def _get_dingtalk_access_token(auth: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    response = requests.post(
        'https://api.dingtalk.com/v1.0/oauth2/accessToken',
        json={
            'appKey': auth.get('app_key'),
            'appSecret': auth.get('app_secret'),
        },
        timeout=timeout,
    )
    payload = _safe_json(response)
    access_token = payload.get('accessToken')
    ok = response.ok and bool(access_token)
    return {
        'ok': ok,
        'access_token': access_token,
        'detail': '钉钉 accessToken 获取成功。' if ok else payload.get('message') or response.text[:200],
        'provider_response_code': payload.get('code'),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('code'),
        },
    }


def _get_feishu_tenant_access_token(auth: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    response = requests.post(
        'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
        json={
            'app_id': auth.get('app_id'),
            'app_secret': auth.get('app_secret'),
        },
        timeout=timeout,
    )
    payload = _safe_json(response)
    tenant_access_token = payload.get('tenant_access_token')
    ok = response.ok and payload.get('code') == 0 and bool(tenant_access_token)
    return {
        'ok': ok,
        'tenant_access_token': tenant_access_token,
        'detail': '飞书 tenant_access_token 获取成功。' if ok else payload.get('msg') or response.text[:200],
        'provider_response_code': payload.get('code'),
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('code'),
        },
    }


def _complete_feishu_oauth(auth: dict[str, Any], code: str, *, callback_url: str | None = None) -> dict[str, Any]:
    response = requests.post(
        'https://open.feishu.cn/open-apis/authen/v2/oauth/token',
        headers={'Content-Type': 'application/json'},
        json={
            'grant_type': 'authorization_code',
            'client_id': auth.get('app_id'),
            'client_secret': auth.get('app_secret'),
            'code': code,
            **({'redirect_uri': callback_url} if callback_url else {}),
        },
        timeout=10,
    )
    payload = _safe_json(response)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    user_access_token = data.get('access_token') or data.get('user_access_token')
    ok = response.ok and payload.get('code') in (0, None) and bool(user_access_token)
    updated = {
        **auth,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'last_test_detail': '飞书授权完成。' if ok else payload.get('msg') or response.text[:200],
    }
    if ok:
        updated.update({
            'access_token': user_access_token,
            'refresh_token': data.get('refresh_token') or '',
            'authorized_open_id': data.get('open_id') or '',
            'authorized_union_id': data.get('union_id') or '',
            'authorized_user_id': data.get('user_id') or '',
            'authorized_user_name': data.get('name') or data.get('en_name') or data.get('open_id') or '飞书授权用户',
            'expires_in': data.get('expires_in') or '',
        })
    return {
        'ok': ok,
        'status': updated['status'],
        'detail': updated['last_test_detail'],
        'auth_connection': updated,
        'provider_response_code': payload.get('code'),
    }


def _complete_dingtalk_oauth(auth: dict[str, Any], code: str) -> dict[str, Any]:
    response = requests.post(
        'https://api.dingtalk.com/v1.0/oauth2/userAccessToken',
        json={
            'clientId': auth.get('app_key'),
            'clientSecret': auth.get('app_secret'),
            'code': code,
            'grantType': 'authorization_code',
        },
        timeout=10,
    )
    payload = _safe_json(response)
    access_token = payload.get('accessToken')
    ok = response.ok and bool(access_token)
    updated = {
        **auth,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'last_test_detail': '钉钉授权完成。' if ok else payload.get('message') or response.text[:200],
    }
    if ok:
        updated.update({
            'access_token': access_token,
            'refresh_token': payload.get('refreshToken') or '',
            'authorized_union_id': payload.get('unionId') or '',
            'authorized_user_id': payload.get('userId') or payload.get('openId') or '',
            'authorized_open_id': payload.get('openId') or '',
            'authorized_user_name': payload.get('nick') or payload.get('unionId') or '钉钉授权用户',
            'expires_in': payload.get('expireIn') or '',
        })
    return {
        'ok': ok,
        'status': updated['status'],
        'detail': updated['last_test_detail'],
        'auth_connection': updated,
        'provider_response_code': payload.get('code'),
    }


def _complete_wechat_oauth(auth: dict[str, Any], code: str) -> dict[str, Any]:
    token_response = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
        params={
            'corpid': auth.get('corp_id'),
            'corpsecret': auth.get('corp_secret'),
        },
        timeout=10,
    )
    token_payload = _safe_json(token_response)
    access_token = token_payload.get('access_token')
    if not token_response.ok or token_payload.get('errcode') != 0 or not access_token:
        updated = {
            **auth,
            'status': CONNECTION_STATUS_ERROR,
            'last_test_detail': token_payload.get('errmsg') or token_response.text[:200],
        }
        return {
            'ok': False,
            'status': CONNECTION_STATUS_ERROR,
            'detail': updated['last_test_detail'],
            'auth_connection': updated,
            'provider_response_code': token_payload.get('errcode'),
        }

    user_response = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo',
        params={
            'access_token': access_token,
            'code': code,
        },
        timeout=10,
    )
    user_payload = _safe_json(user_response)
    ok = user_response.ok and user_payload.get('errcode') == 0
    updated = {
        **auth,
        'access_token': access_token if ok else auth.get('access_token', ''),
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'last_test_detail': '企业微信授权完成。' if ok else user_payload.get('errmsg') or user_response.text[:200],
    }
    if ok:
        updated.update({
            'authorized_user_id': user_payload.get('userid') or user_payload.get('UserId') or '',
            'authorized_open_id': user_payload.get('openid') or user_payload.get('OpenId') or '',
            'authorized_user_name': user_payload.get('userid') or user_payload.get('openid') or '企业微信授权用户',
        })
    return {
        'ok': ok,
        'status': updated['status'],
        'detail': updated['last_test_detail'],
        'auth_connection': updated,
        'provider_response_code': user_payload.get('errcode'),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _provider_result(ok: bool, channel: str, response: requests.Response, payload: dict[str, Any], detail: str) -> dict[str, Any]:
    return {
        'ok': ok,
        'status': CONNECTION_STATUS_CONNECTED if ok else CONNECTION_STATUS_ERROR,
        'channel': channel,
        'detail': detail,
        'request_payload': {},
        'response_info': {
            'status_code': response.status_code,
            'response_text': response.text[:500],
            'provider_response_code': payload.get('code') if 'code' in payload else payload.get('errcode'),
        },
    }


def _redact_message_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = deepcopy(payload or {})
    for key in ('access_token', 'app_secret', 'corp_secret'):
        if key in redacted:
            redacted[key] = '***'
    return redacted


def _safe_int(value: Any) -> int | str:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return value or ''


def _append_dingtalk_webhook_signature(webhook_url: str, secret: str) -> str:
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).digest()
    sign = quote_plus(base64.b64encode(hmac_code))
    separator = '&' if '?' in webhook_url else '?'
    return f'{webhook_url}{separator}timestamp={timestamp}&sign={sign}'


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}
