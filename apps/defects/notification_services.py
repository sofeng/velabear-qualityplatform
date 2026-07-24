import json
import logging
import queue
import threading
from collections import defaultdict
from email.utils import formataddr
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.html import escape
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.api_testing.custom_email_backend import CustomEmailBackend
from apps.users.models import User, UserProfile

from .models import Defect, DefectEmailConfig

logger = logging.getLogger(__name__)

DEFECT_NOTIFICATION_TYPES = ['new', 'assign', 'title', 'description', 'status', 'comment']
EMAIL_TRIGGER_STATUSES = {'new', 'resolved', 'rejected', 'reopened'}
STATUS_TO_EMAIL_TYPE = {
    'new': 'new',
    'resolved': 'resolved',
    'rejected': 'rejected',
    'reopened': 'reopened',
}
DEFAULT_EMAIL_TEMPLATES = {
    'new_bug_template': '您好，您有一个新的缺陷待处理。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'resolved_bug_template': '您好，缺陷已解决。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'rejected_bug_template': '您好，缺陷已拒绝。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
    'reopened_bug_template': '您好，缺陷已重新打开。\n\nID: ${ID}\n标题: ${标题}\n创建人: ${创建人}\n处理人: ${处理人}',
}
DEFAULT_EMAIL_SUBJECTS = {
    'new': '[新缺陷] {title}',
    'resolved': '[已解决] {title}',
    'rejected': '[已拒绝] {title}',
    'reopened': '[已重新打开] {title}',
}


class DefectNotificationBroker:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers = defaultdict(set)

    def subscribe(self, user_id):
        subscription = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers[str(user_id)].add(subscription)
        return subscription

    def unsubscribe(self, user_id, subscription):
        with self._lock:
            user_subscribers = self._subscribers.get(str(user_id))
            if not user_subscribers:
                return
            user_subscribers.discard(subscription)
            if not user_subscribers:
                self._subscribers.pop(str(user_id), None)

    def publish(self, user_id, payload):
        with self._lock:
            subscriptions = list(self._subscribers.get(str(user_id), ()))

        for subscription in subscriptions:
            try:
                subscription.put_nowait(payload)
            except queue.Full:
                try:
                    subscription.get_nowait()
                except queue.Empty:
                    pass
                try:
                    subscription.put_nowait(payload)
                except queue.Full:
                    logger.warning('Defect notification queue is full for user %s', user_id)


notification_broker = DefectNotificationBroker()


def get_default_defect_email_config_data():
    return {
        'host': '',
        'port': 465,
        'username': '',
        'password': '',
        'from_name': '缺陷管理平台',
        'from_email': '',
        'new_bug_template': DEFAULT_EMAIL_TEMPLATES['new_bug_template'],
        'resolved_bug_template': DEFAULT_EMAIL_TEMPLATES['resolved_bug_template'],
        'rejected_bug_template': DEFAULT_EMAIL_TEMPLATES['rejected_bug_template'],
        'reopened_bug_template': DEFAULT_EMAIL_TEMPLATES['reopened_bug_template'],
        'is_active': True,
    }


def build_default_defect_email_config_instance():
    return DefectEmailConfig(**get_default_defect_email_config_data())


def get_defect_email_config():
    return DefectEmailConfig.objects.order_by('-updated_at', '-id').first()


def get_or_build_defect_email_config():
    config = get_defect_email_config()
    if config is not None:
        return config
    return DefectEmailConfig.objects.create(**get_default_defect_email_config_data())


def save_defect_email_config(validated_data, operator):
    config = get_defect_email_config()
    if config is None:
        config = DefectEmailConfig(created_by=operator)

    for field, value in validated_data.items():
        setattr(config, field, value)

    if not config.pk and not config.created_by_id:
        config.created_by = operator
    config.updated_by = operator
    config.save()
    return config


def validate_email_config(config):
    missing_fields = []
    for field in ['host', 'port', 'username', 'password', 'from_email']:
        value = getattr(config, field, None)
        if value in (None, ''):
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(f'邮件配置不完整：{", ".join(missing_fields)}')


def build_email_backend(config):
    validate_email_config(config)
    return CustomEmailBackend(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        use_tls=bool(config.port == 587),
        use_ssl=bool(config.port == 465),
        timeout=15,
        fail_silently=False,
    )


def verify_defect_email_config(config):
    connection = build_email_backend(config)
    try:
        connection.open()
    finally:
        if getattr(connection, 'connection', None):
            connection.close()


def send_defect_test_email(config, to_email, subject='', text=''):
    connection = build_email_backend(config)
    subject_text = subject or '缺陷邮件配置测试'
    body_text = text or '这是一封测试邮件，表示缺陷邮件配置可正常使用。'
    from_email = formataddr((config.from_name, config.from_email))

    message = EmailMultiAlternatives(
        subject=subject_text,
        body=body_text,
        from_email=from_email,
        to=[to_email],
        connection=connection,
    )
    message.attach_alternative(f'<p>{escape(body_text).replace(chr(10), "<br>")}</p>', 'text/html')
    return message.send()


def get_user_defect_notification_types(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    notifications = profile.notifications if isinstance(profile.notifications, dict) else {}
    types = notifications.get('defect_types')
    if not isinstance(types, list):
        return list(DEFECT_NOTIFICATION_TYPES)
    return [item for item in types if item in DEFECT_NOTIFICATION_TYPES]


def update_user_defect_notification_types(user, types):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    notifications = profile.notifications if isinstance(profile.notifications, dict) else {}
    notifications = dict(notifications)
    notifications['defect_types'] = [item for item in types if item in DEFECT_NOTIFICATION_TYPES]
    profile.notifications = notifications
    profile.save(update_fields=['notifications'])
    return notifications['defect_types']


def get_stream_user_from_token(token):
    if not token:
        return None

    try:
        access_token = AccessToken(token)
    except TokenError:
        return None

    user_id = access_token.get('user_id')
    if not user_id:
        return None

    return User.objects.filter(id=user_id).first()


def resolve_frontend_base_url(request=None):
    if request is None:
        explicit_base_url = getattr(settings, 'FRONTEND_BASE_URL', '')
        return explicit_base_url.rstrip('/') if explicit_base_url else ''

    origin = (request.headers.get('Origin') or '').strip()
    if origin:
        return origin.rstrip('/')

    referer = (request.headers.get('Referer') or '').strip()
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}'

    explicit_base_url = getattr(settings, 'FRONTEND_BASE_URL', '')
    if explicit_base_url:
        return explicit_base_url.rstrip('/')

    return request.build_absolute_uri('/').rstrip('/')


def build_defect_frontend_url(defect, frontend_base_url=''):
    path = f'/manual-testcases/defects/{defect.id}/edit'
    if not frontend_base_url:
        return path
    return urljoin(f'{frontend_base_url.rstrip("/")}/', path.lstrip('/'))


def get_defect_status_label(status_value):
    return dict(Defect.STATUS_CHOICES).get(status_value, status_value or '')


def build_defect_notification_payload(defect, notification_type, message, frontend_base_url=''):
    return {
        'type': notification_type,
        'defect_id': defect.id,
        'defect_code': defect.code or '',
        'title': defect.title,
        'status': defect.status,
        'status_label': get_defect_status_label(defect.status),
        'message': message,
        'url': build_defect_frontend_url(defect, frontend_base_url),
        'sent_at': timezone.now().isoformat(),
    }


def publish_defect_notification(defect, notification_type, message, recipients, frontend_base_url=''):
    payload = build_defect_notification_payload(defect, notification_type, message, frontend_base_url)

    for recipient in recipients:
        if not recipient:
            continue
        allowed_types = get_user_defect_notification_types(recipient)
        if notification_type not in allowed_types:
            continue
        notification_broker.publish(recipient.id, payload)


def get_email_recipients(users):
    recipient_map = {}
    for user in users:
        email = (getattr(user, 'email', '') or '').strip()
        if email:
            recipient_map[email.lower()] = email
    return list(recipient_map.values())


def render_defect_email_content(template_text, defect, recipients=None, frontend_base_url=''):
    recipients = list(recipients or [])
    defect_code = defect.code or str(defect.id)
    defect_url = build_defect_frontend_url(defect, frontend_base_url)
    creator_name = defect.created_by.username or defect.created_by.email or f'用户{defect.created_by_id}'
    assignee_names = ', '.join(
        [
            assignee.username or assignee.email or f'用户{assignee.id}'
            for assignee in recipients
        ]
    ) or '-'

    plain_text = (
        str(template_text or '')
        .replace('${ID}', defect_code)
        .replace('${标题}', defect.title or '')
        .replace('${创建人}', creator_name)
        .replace('${处理人}', assignee_names)
    )

    html_text = escape(str(template_text or ''))
    if defect_url:
        html_id = f'<a href="{escape(defect_url)}" target="_blank" rel="noopener noreferrer">{escape(defect_code)}</a>'
    else:
        html_id = escape(defect_code)

    html_text = (
        html_text
        .replace('${ID}', html_id)
        .replace('${标题}', escape(defect.title or ''))
        .replace('${创建人}', escape(creator_name))
        .replace('${处理人}', escape(assignee_names))
        .replace('\n', '<br>')
    )

    return plain_text, html_text


def send_defect_status_email(defect, email_type=None, recipients=None, frontend_base_url=''):
    config = get_defect_email_config()
    if not config or not config.is_active:
        return 0

    email_type = email_type or STATUS_TO_EMAIL_TYPE.get(defect.status)
    if email_type not in DEFAULT_EMAIL_SUBJECTS:
        return 0

    recipient_users = list(recipients or defect.assignees.all())
    to_emails = get_email_recipients(recipient_users)
    if not to_emails:
        return 0

    template_field = {
        'new': 'new_bug_template',
        'resolved': 'resolved_bug_template',
        'rejected': 'rejected_bug_template',
        'reopened': 'reopened_bug_template',
    }[email_type]
    template_text = getattr(config, template_field, '') or DEFAULT_EMAIL_TEMPLATES[template_field]
    subject_text = DEFAULT_EMAIL_SUBJECTS[email_type].format(title=defect.title or defect.code or f'#{defect.id}')
    body_text, body_html = render_defect_email_content(
        template_text,
        defect,
        recipients=recipient_users,
        frontend_base_url=frontend_base_url,
    )

    connection = build_email_backend(config)
    message = EmailMultiAlternatives(
        subject=subject_text,
        body=body_text,
        from_email=formataddr((config.from_name, config.from_email)),
        to=to_emails,
        connection=connection,
    )
    message.attach_alternative(body_html, 'text/html')
    return message.send()


def load_defect_for_notification(defect_id):
    return (
        Defect.objects
        .select_related('created_by', 'project', 'version')
        .prefetch_related('assignees')
        .filter(id=defect_id, record_type=Defect.RECORD_TYPE_DEFECT)
        .first()
    )


def notify_defect_created(defect_id, frontend_base_url=''):
    defect = load_defect_for_notification(defect_id)
    if not defect:
        return

    assignees = list(defect.assignees.all())
    if not assignees:
        return

    publish_defect_notification(
        defect,
        'new',
        f'你有新的缺陷 {defect.code or defect.id}',
        assignees,
        frontend_base_url=frontend_base_url,
    )

    if defect.status in EMAIL_TRIGGER_STATUSES:
        send_defect_status_email(
            defect,
            email_type=STATUS_TO_EMAIL_TYPE.get(defect.status, 'new'),
            recipients=assignees,
            frontend_base_url=frontend_base_url,
        )


def notify_defect_updated(
    defect_id,
    *,
    title_changed=False,
    description_changed=False,
    status_changed=False,
    new_assignee_ids=None,
    frontend_base_url='',
):
    defect = load_defect_for_notification(defect_id)
    if not defect:
        return

    current_assignees = list(defect.assignees.all())
    current_assignee_map = {user.id: user for user in current_assignees}
    added_assignees = [
        current_assignee_map[user_id]
        for user_id in (new_assignee_ids or [])
        if user_id in current_assignee_map
    ]

    if title_changed and current_assignees:
        publish_defect_notification(
            defect,
            'title',
            f'你的缺陷 {defect.code or defect.id} 标题已变更',
            current_assignees,
            frontend_base_url=frontend_base_url,
        )

    if description_changed and current_assignees:
        publish_defect_notification(
            defect,
            'description',
            f'你的缺陷 {defect.code or defect.id} 描述已变更',
            current_assignees,
            frontend_base_url=frontend_base_url,
        )

    if status_changed and current_assignees:
        publish_defect_notification(
            defect,
            'status',
            f'你的缺陷 {defect.code or defect.id} 状态变更为 {get_defect_status_label(defect.status)}',
            current_assignees,
            frontend_base_url=frontend_base_url,
        )

    if added_assignees:
        publish_defect_notification(
            defect,
            'assign',
            f'你被指派了缺陷 {defect.code or defect.id}',
            added_assignees,
            frontend_base_url=frontend_base_url,
        )

    if status_changed and defect.status in EMAIL_TRIGGER_STATUSES and current_assignees:
        send_defect_status_email(defect, recipients=current_assignees, frontend_base_url=frontend_base_url)
    elif added_assignees and defect.status in EMAIL_TRIGGER_STATUSES:
        send_defect_status_email(defect, recipients=added_assignees, frontend_base_url=frontend_base_url)


def notify_defect_status_updated(defect_id, frontend_base_url=''):
    defect = load_defect_for_notification(defect_id)
    if not defect:
        return

    assignees = list(defect.assignees.all())
    if assignees:
        publish_defect_notification(
            defect,
            'status',
            f'你的缺陷 {defect.code or defect.id} 状态变更为 {get_defect_status_label(defect.status)}',
            assignees,
            frontend_base_url=frontend_base_url,
        )

    if defect.status in EMAIL_TRIGGER_STATUSES and assignees:
        send_defect_status_email(defect, recipients=assignees, frontend_base_url=frontend_base_url)


def notify_defect_assignees_updated(defect_id, new_assignee_ids=None, frontend_base_url=''):
    defect = load_defect_for_notification(defect_id)
    if not defect:
        return

    current_assignees = list(defect.assignees.all())
    current_assignee_map = {user.id: user for user in current_assignees}
    added_assignees = [
        current_assignee_map[user_id]
        for user_id in (new_assignee_ids or [])
        if user_id in current_assignee_map
    ]

    if not added_assignees:
        return

    publish_defect_notification(
        defect,
        'assign',
        f'你被指派了缺陷 {defect.code or defect.id}',
        added_assignees,
        frontend_base_url=frontend_base_url,
    )

    if defect.status in EMAIL_TRIGGER_STATUSES:
        send_defect_status_email(defect, recipients=added_assignees, frontend_base_url=frontend_base_url)


def notify_defect_comment_created(defect_id, frontend_base_url=''):
    defect = load_defect_for_notification(defect_id)
    if not defect:
        return

    assignees = list(defect.assignees.all())
    if not assignees:
        return

    publish_defect_notification(
        defect,
        'comment',
        f'你的缺陷 {defect.code or defect.id} 有新的评论',
        assignees,
        frontend_base_url=frontend_base_url,
    )


def safely_execute_notification(callback, *args, **kwargs):
    try:
        callback(*args, **kwargs)
    except Exception:
        logger.exception('Failed to execute defect notification callback')


def build_notification_stream_response(user):
    subscription = notification_broker.subscribe(user.id)

    def event_stream():
        yield 'retry: 10000\n\n'
        try:
            while True:
                try:
                    payload = subscription.get(timeout=25)
                    yield f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'
                except queue.Empty:
                    yield ': keep-alive\n\n'
        finally:
            notification_broker.unsubscribe(user.id, subscription)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
