import logging
import random
import re
import time

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 300
SEND_COOLDOWN_SECONDS = 60
CODE_LENGTH = 6

_memory_store = {}


def normalize_email(email):
    return str(email or '').strip().lower()


def _code_key(email):
    return f'email_verification:code:{normalize_email(email)}'


def _cooldown_key(email):
    return f'email_verification:cooldown:{normalize_email(email)}'


_redis_client = None
_redis_unavailable = False


def _get_redis_client():
    global _redis_client, _redis_unavailable

    if _redis_unavailable:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        import redis

        _redis_client = redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as error:
        logger.warning('Redis unavailable for email verification, using memory store: %s', error)
        _redis_unavailable = True
        _redis_client = None
        return None


def _store_set(key, value, ttl_seconds):
    client = _get_redis_client()
    if client is not None:
        try:
            client.setex(key, ttl_seconds, value)
            return
        except Exception as error:
            logger.warning('Redis set failed for email verification, using memory store: %s', error)

    expires_at = time.time() + ttl_seconds
    _memory_store[key] = (value, expires_at)


def _store_get(key):
    client = _get_redis_client()
    if client is not None:
        try:
            return client.get(key)
        except Exception as error:
            logger.warning('Redis get failed for email verification, using memory store: %s', error)

    item = _memory_store.get(key)
    if not item:
        return None

    value, expires_at = item
    if time.time() > expires_at:
        _memory_store.pop(key, None)
        return None
    return value


def _store_exists(key):
    return _store_get(key) is not None


def _store_delete(key):
    client = _get_redis_client()
    if client is not None:
        try:
            client.delete(key)
            return
        except Exception as error:
            logger.warning('Redis delete failed for email verification, using memory store: %s', error)
    _memory_store.pop(key, None)


def generate_verification_code():
    return f'{random.randint(0, 10 ** CODE_LENGTH - 1):0{CODE_LENGTH}d}'


def _should_expose_verification_code():
    return bool(getattr(settings, 'EMAIL_VERIFICATION_EXPOSE_CODE', settings.DEBUG))


def _is_placeholder_email_setting(value):
    normalized = str(value or '').strip().lower()
    if not normalized:
        return True

    placeholder_markers = (
        'your-email',
        'example.com',
        '你的邮箱',
        '你的密码',
        '默认发件人',
        'webmaster@localhost',
    )
    return any(marker in normalized for marker in placeholder_markers)


def is_email_delivery_configured():
    host_user = str(getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    host_password = str(getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').strip()
    from_email = str(getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()

    if _is_placeholder_email_setting(host_user):
        return False
    if _is_placeholder_email_setting(host_password):
        return False
    if _is_placeholder_email_setting(from_email):
        return False

    return bool(host_user and host_password and from_email)


def send_email_verification_code(email):
    normalized_email = normalize_email(email)
    if not normalized_email or '@' not in normalized_email:
        raise ValueError('请输入正确的邮箱')

    if _store_exists(_cooldown_key(normalized_email)):
        raise ValueError('请求过于频繁，请稍后再试')

    code = generate_verification_code()
    _store_set(_code_key(normalized_email), code, CODE_TTL_SECONDS)
    _store_set(_cooldown_key(normalized_email), '1', SEND_COOLDOWN_SECONDS)

    subject = 'BearAI 登录验证码'
    message = (
        f'您的 BearAI 登录验证码是 {code}，5 分钟内有效。'
        '如非本人操作，请忽略此邮件。'
    )

    email_sent = False
    delivery_configured = is_email_delivery_configured()
    if delivery_configured:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[normalized_email],
                fail_silently=False,
            )
            email_sent = True
        except Exception as error:
            logger.exception('Failed to send verification email to %s: %s', normalized_email, error)

    debug_code = None
    if not email_sent and _should_expose_verification_code():
        debug_code = code
        logger.info('Email verification code for %s: %s', normalized_email, code)

    if not email_sent and not debug_code:
        raise ValueError('验证码发送失败，请稍后重试或联系管理员配置邮件服务')

    return {
        'email': normalized_email,
        'email_sent': email_sent,
        'debug_code': debug_code,
        'delivery_configured': delivery_configured,
        'expires_in': CODE_TTL_SECONDS,
        'cooldown_seconds': SEND_COOLDOWN_SECONDS,
    }


def verify_email_code(email, code):
    normalized_email = normalize_email(email)
    normalized_code = str(code or '').strip()
    stored_code = _store_get(_code_key(normalized_email))
    if not stored_code or stored_code != normalized_code:
        raise ValueError('验证码错误或已过期')
    _store_delete(_code_key(normalized_email))
    return normalized_email


def generate_username_from_email(email):
    local_part = normalize_email(email).split('@', 1)[0]
    base = re.sub(r'[^a-zA-Z0-9_]', '', local_part)[:20] or 'user'
    username = base
    suffix = 1
    from .models import User

    while User.objects.filter(username=username).exists():
        username = f'{base}{suffix}'
        suffix += 1
    return username
