import os
import re
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import requests
from django.db import transaction
from django.utils import timezone
from lxml import html

from apps.core.plaintext_secrets import decrypt_password, encrypt_password, is_serialized_fernet_secret
from apps.users.models import Role

from .models import JiraBugRecord, JiraRequirementRecord
from .version_utils import normalize_jira_version


DEFAULT_JIRA_REQUEST_URL = 'http://172.31.119.34:8080/rest/issueNav/1/issueTable'
DEFAULT_JIRA_LOGIN_URL = 'http://172.31.119.34:8080/login.jsp'
DEFAULT_JIRA_REQUEST_METHOD = 'POST'
DEFAULT_JIRA_TIMEOUT_SECONDS = 60
DEFAULT_JIRA_VERSION = '26-04.15发版（8.2.0）'

BUG_PROFILE = 'bug'
REQUIREMENT_PROFILE = 'requirement'
DEFAULT_BUG_FILTER_ID = '16128'
DEFAULT_REQUIREMENT_FILTER_ID = '15943'

DEFAULT_BUG_JIRA_COOKIE = (
    'seraph.rememberme.cookie=21537%3Af94e4b6896599b9e0fab7a3a0b3d86d765ef4e0a; '
    'atlassian.xsrf.token=BYAD-0586-UEY0-GUQV|ac2d3e63651efedad8852ca6cd3069a649039c55|lin; '
    'JSESSIONID=66553A36BE0F50792BC74055E4C1D96C'
)
DEFAULT_REQUIREMENT_JIRA_COOKIE = (
    'seraph.rememberme.cookie=21537%3Af94e4b6896599b9e0fab7a3a0b3d86d765ef4e0a; '
    'atlassian.xsrf.token=BYAD-0586-UEY0-GUQV|ac2d3e63651efedad8852ca6cd3069a649039c55|lin; '
    'JSESSIONID=3F4093AC153C08047C70416F21B0EEB2'
)
DEFAULT_JIRA_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
)
JIRA_REST_LOGIN_USER_AGENT = 'Mozilla/5.0'
JIRA_GENERAL_COOKIE_ENV = 'QUALITY_ANALYSIS_JIRA_COOKIE'
JIRA_GENERAL_AUTHORIZATION_ENV = 'QUALITY_ANALYSIS_JIRA_AUTHORIZATION'
JIRA_BUG_COOKIE_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_COOKIE'
JIRA_BUG_AUTHORIZATION_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_AUTHORIZATION'
JIRA_REQUIREMENT_COOKIE_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_COOKIE'
JIRA_REQUIREMENT_AUTHORIZATION_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_AUTHORIZATION'
JIRA_GENERAL_LOGIN_ENABLED_ENV = 'QUALITY_ANALYSIS_JIRA_LOGIN_ENABLED'
JIRA_GENERAL_LOGIN_URL_ENV = 'QUALITY_ANALYSIS_JIRA_LOGIN_URL'
JIRA_GENERAL_USERNAME_ENV = 'QUALITY_ANALYSIS_JIRA_USERNAME'
JIRA_GENERAL_PASSWORD_ENV = 'QUALITY_ANALYSIS_JIRA_PASSWORD'
JIRA_BUG_LOGIN_ENABLED_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_LOGIN_ENABLED'
JIRA_BUG_LOGIN_URL_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_LOGIN_URL'
JIRA_BUG_USERNAME_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_USERNAME'
JIRA_BUG_PASSWORD_ENV = 'QUALITY_ANALYSIS_JIRA_BUG_PASSWORD'
JIRA_REQUIREMENT_LOGIN_ENABLED_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_LOGIN_ENABLED'
JIRA_REQUIREMENT_LOGIN_URL_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_LOGIN_URL'
JIRA_REQUIREMENT_USERNAME_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_USERNAME'
JIRA_REQUIREMENT_PASSWORD_ENV = 'QUALITY_ANALYSIS_JIRA_REQUIREMENT_PASSWORD'

BUG_JQL_TEMPLATE = (
    'project = SYSWIN AND issuetype = BUG AND fixVersion = {version} '
    'ORDER BY created DESC, cf[10747] DESC, cf[10741] ASC, key ASC, '
    'cf[10762] DESC, reporter ASC, assignee ASC, cf[10708] ASC, '
    'issuetype DESC, cf[10738] DESC'
)
REQUIREMENT_JQL_TEMPLATE = (
    'project = SYSWIN AND issuetype in (任务, 实施需求（二次开发）, 实施需求（合同内）, '
    '标准化需求, 子任务-需求分拆) AND status in '
    '(产品需求待接收, 产品规划设计中, 产品设计完成, 待启动研发任务, 功能研发中, 研发技术评审, '
    '代码开发完成, 功能测试中, 测试完成待发版, 开发任务完结, 需求报告人验收中, 已交付上线, '
    '已关闭问题, 已挂起问题) AND fixVersion = {version} '
    'ORDER BY cf[10761] DESC, cf[10747] DESC, cf[10741] ASC, key ASC, '
    'cf[10762] DESC, reporter ASC, assignee ASC, cf[10708] ASC, '
    'issuetype DESC, cf[10738] DESC'
)


def _normalize_profile(profile):
    return REQUIREMENT_PROFILE if profile == REQUIREMENT_PROFILE else BUG_PROFILE


def _get_jira_env_override(*names):
    for name in names:
        value = str(os.getenv(name, '') or '').strip()
        if value:
            return value
    return ''


def _get_profiled_jira_cookie_override(profile):
    profile = _normalize_profile(profile)
    if profile == REQUIREMENT_PROFILE:
        return _get_jira_env_override(JIRA_REQUIREMENT_COOKIE_ENV, JIRA_GENERAL_COOKIE_ENV)
    return _get_jira_env_override(JIRA_BUG_COOKIE_ENV, JIRA_GENERAL_COOKIE_ENV)


def _get_profiled_jira_authorization_override(profile):
    profile = _normalize_profile(profile)
    if profile == REQUIREMENT_PROFILE:
        return _get_jira_env_override(JIRA_REQUIREMENT_AUTHORIZATION_ENV, JIRA_GENERAL_AUTHORIZATION_ENV)
    return _get_jira_env_override(JIRA_BUG_AUTHORIZATION_ENV, JIRA_GENERAL_AUTHORIZATION_ENV)


def _get_configured_jira_cookie(config, profile):
    runtime_cookie = _get_profiled_jira_cookie_override(profile)
    if runtime_cookie:
        return runtime_cookie
    headers = getattr(config, 'request_headers', {}) or {}
    cookie = str(_get_header_case_insensitive(headers, 'cookie') or '').strip()
    if cookie and not _is_legacy_jira_cookie_value(cookie):
        return cookie
    return ''


def _get_profiled_jira_login_env(profile, suffix):
    profile = _normalize_profile(profile)
    suffix = str(suffix or '').strip().upper()
    if profile == REQUIREMENT_PROFILE:
        return _get_jira_env_override(
            f'QUALITY_ANALYSIS_JIRA_REQUIREMENT_{suffix}',
            f'QUALITY_ANALYSIS_JIRA_{suffix}',
        )
    return _get_jira_env_override(
        f'QUALITY_ANALYSIS_JIRA_BUG_{suffix}',
        f'QUALITY_ANALYSIS_JIRA_{suffix}',
    )


def _parse_bool_env(value):
    text = str(value or '').strip().lower()
    if text in {'1', 'true', 'yes', 'y', 'on', 'enabled'}:
        return True
    if text in {'0', 'false', 'no', 'n', 'off', 'disabled'}:
        return False
    return None


def _get_config_jira_password(config):
    encrypted_value = str(getattr(config, 'jira_password_encrypted', '') or '').strip()
    if not encrypted_value:
        return ''

    if is_serialized_fernet_secret(encrypted_value):
        try:
            return decrypt_password(encrypted_value)
        except ValueError as exc:
            config_id = getattr(config, 'pk', '')
            raise ValueError(f'JIRA登录密码（配置ID：{config_id}）解密失败，请在JIRA接口配置中重新保存密码。') from exc

    plain_text = encrypted_value
    if hasattr(config, 'jira_password_encrypted'):
        config.jira_password_encrypted = encrypt_password(plain_text)
        update_fields = ['jira_password_encrypted']
        if hasattr(config, 'updated_at'):
            update_fields.append('updated_at')
        config.save(update_fields=update_fields)
    return plain_text


def _get_jira_login_config(config, profile):
    profile = _normalize_profile(profile)
    enabled_override = _parse_bool_env(_get_profiled_jira_login_env(profile, 'LOGIN_ENABLED'))
    env_login_url = _get_profiled_jira_login_env(profile, 'LOGIN_URL')
    env_username = _get_profiled_jira_login_env(profile, 'USERNAME')
    env_password = _get_profiled_jira_login_env(profile, 'PASSWORD')

    login_url = env_login_url or str(getattr(config, 'jira_login_url', '') or '').strip() or DEFAULT_JIRA_LOGIN_URL
    username = env_username or str(getattr(config, 'jira_username', '') or '').strip()
    has_env_login_config = bool(env_login_url or env_username or env_password)
    enabled = bool(getattr(config, 'jira_login_enabled', False))
    if enabled_override is not None:
        enabled = enabled_override
    elif has_env_login_config:
        enabled = True
    password = env_password
    if enabled and not password:
        password = _get_config_jira_password(config)

    return {
        'enabled': enabled,
        'login_url': login_url,
        'username': username,
        'password': password,
        'profile': profile,
    }


def _raise_incomplete_jira_login_config(login_config):
    missing = []
    if not login_config.get('login_url'):
        missing.append('登录URL')
    if not login_config.get('username'):
        missing.append('账号')
    if not login_config.get('password'):
        missing.append('密码')
    if missing:
        raise ValueError(
            'JIRA登录已启用，但缺少'
            + '、'.join(missing)
            + '。请在JIRA接口配置中补齐登录URL、账号、密码，'
            f'或通过环境变量 {JIRA_GENERAL_LOGIN_URL_ENV}/{JIRA_GENERAL_USERNAME_ENV}/{JIRA_GENERAL_PASSWORD_ENV} '
            '以及 QUALITY_ANALYSIS_JIRA_BUG_*、QUALITY_ANALYSIS_JIRA_REQUIREMENT_* 按接口类型覆盖。'
        )


def _extract_jira_login_form(login_url, page_text):
    try:
        root = html.fromstring(page_text or '<html></html>')
    except (TypeError, ValueError):
        return login_url, {}

    forms = (
        root.xpath('//form[@id="login-form"]')
        or root.xpath('//form[contains(@action, "login.jsp")]')
        or root.xpath('//form[.//input[@name="os_username"] or .//input[@name="os_password"]]')
        or root.xpath('//form[1]')
    )
    if not forms:
        return login_url, {}

    form = forms[0]
    action = form.get('action') or login_url
    form_data = {}
    for input_node in form.xpath('.//input[@name]'):
        input_type = str(input_node.get('type') or '').strip().lower()
        if input_type in {'button', 'image', 'reset'}:
            continue
        name = input_node.get('name')
        if not name:
            continue
        form_data[name] = input_node.get('value') or ''
    return urljoin(login_url, action), form_data


def _build_jira_rest_session_url(login_url):
    parsed = urlparse(_normalize_text(login_url) or DEFAULT_JIRA_LOGIN_URL)
    fallback = urlparse(DEFAULT_JIRA_LOGIN_URL)
    scheme = parsed.scheme or fallback.scheme
    netloc = parsed.netloc or fallback.netloc
    path = parsed.path or fallback.path
    if path.lower().endswith('/login.jsp'):
        context_path = path[:-len('/login.jsp')]
    else:
        context_path = path.rsplit('/', 1)[0]
    rest_path = f'{context_path.rstrip("/")}/rest/auth/1/session'
    return urlunparse((scheme, netloc, rest_path, '', '', ''))


def _extract_jira_rest_login_error(response):
    messages = []
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    for item in payload.get('errorMessages') or []:
        text = _normalize_text(item)
        if text and text not in messages:
            messages.append(text)
    for value in (payload.get('errors') or {}).values():
        text = _normalize_text(value)
        if text and text not in messages:
            messages.append(text)

    seraph_reason = _normalize_text(response.headers.get('X-Seraph-LoginReason'))
    if seraph_reason:
        messages.append(f'X-Seraph-LoginReason={seraph_reason}')
    if seraph_reason == 'AUTHENTICATION_DENIED':
        messages.append('JIRA拒绝认证，通常表示密码错误、账号被锁定、触发验证码/失败登录保护，或该账号不允许API登录。')

    if not messages:
        body = _normalize_text((getattr(response, 'text', '') or '')[:500])
        if body:
            messages.append(body)

    return '；'.join(messages[:4])


def _try_jira_rest_session_login(session, login_config, timeout):
    login_response = session.post(
        _build_jira_rest_session_url(login_config['login_url']),
        json={
            'username': login_config['username'],
            'password': login_config['password'],
        },
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': JIRA_REST_LOGIN_USER_AGENT,
            'X-Atlassian-Token': 'no-check',
        },
        timeout=timeout,
        allow_redirects=True,
    )
    if 200 <= login_response.status_code < 300:
        return True, ''
    if login_response.status_code in {404, 405}:
        return False, ''
    return False, _extract_jira_rest_login_error(login_response)


def _looks_like_jira_login_page(response):
    response_url = str(getattr(response, 'url', '') or '')
    path = urlparse(response_url).path.lower()
    try:
        body = str(getattr(response, 'text', '') or '').lower()
    except Exception:
        body = ''
    has_login_form = 'name="os_username"' in body and 'name="os_password"' in body
    has_login_error = 'login-form-authenticate' in body or 'os_username' in body and 'os_password' in body
    return path.endswith('/login.jsp') and (has_login_form or has_login_error)


def _extract_jira_login_error_text(response):
    try:
        root = html.fromstring(getattr(response, 'text', '') or '<html></html>')
    except (TypeError, ValueError):
        return ''

    messages = []
    selectors = [
        '//*[contains(@class, "aui-message")]',
        '//*[contains(@class, "error")]',
        '//*[@id="login-form"]//*[contains(@class, "field-group")]',
    ]
    for selector in selectors:
        for node in root.xpath(selector):
            text = _normalize_text(' '.join(node.xpath('.//text()')))
            if text and text not in messages:
                messages.append(text)

    has_captcha = bool(
        root.xpath(
            '//input[contains(translate(@name, "CAPTCHA", "captcha"), "captcha") '
            'or contains(translate(@id, "CAPTCHA", "captcha"), "captcha")]'
        )
    )
    if has_captcha:
        messages.append('JIRA登录页要求输入验证码，请先在JIRA侧解除失败登录锁定/验证码校验，或改用免验证码的同步服务账号。')

    return '；'.join(messages[:3])


def _create_jira_session(config, profile):
    login_config = _get_jira_login_config(config, profile)
    if not login_config['enabled']:
        return None
    if _get_configured_jira_cookie(config, profile):
        return None

    _raise_incomplete_jira_login_config(login_config)
    timeout = getattr(config, 'timeout_seconds', None) or DEFAULT_JIRA_TIMEOUT_SECONDS
    session = requests.Session()
    rest_login_success, rest_login_error = _try_jira_rest_session_login(session, login_config, timeout)
    if rest_login_success:
        return session
    if rest_login_error and (
        'AUTHENTICATION_DENIED' in rest_login_error
        or '登陆被拒绝' in rest_login_error
        or '登录被拒绝' in rest_login_error
        or 'CAPTCHA' in rest_login_error.upper()
    ):
        raise ValueError(
            'JIRA登录失败，JIRA已拒绝该账号的后台认证。'
            f'JIRA REST登录提示：{rest_login_error}。'
            '请先在JIRA侧确认账号密码是否正确，并由JIRA管理员解除失败登录锁定/CAPTCHA校验，'
            '或改用允许API登录且不会触发验证码的同步服务账号。'
        )

    headers = {
        'user-agent': DEFAULT_JIRA_USER_AGENT,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    login_page = session.get(login_config['login_url'], headers=headers, timeout=timeout)
    if login_page.status_code >= 400:
        error = ValueError(f'JIRA登录页访问失败，HTTP {login_page.status_code}：{(getattr(login_page, "text", "") or "")[:1000]}')
        error.response = login_page
        raise error

    post_url, form_data = _extract_jira_login_form(login_config['login_url'], getattr(login_page, 'text', ''))
    form_data.update(
        {
            'os_username': login_config['username'],
            'os_password': login_config['password'],
            'os_cookie': 'true',
        }
    )
    form_data.setdefault('login', 'Log In')

    login_response = session.post(
        post_url,
        data=form_data,
        headers={
            'user-agent': DEFAULT_JIRA_USER_AGENT,
            'referer': login_config['login_url'],
            'origin': f"{urlparse(login_config['login_url']).scheme}://{urlparse(login_config['login_url']).netloc}",
        },
        timeout=timeout,
        allow_redirects=True,
    )
    if login_response.status_code >= 400:
        error = ValueError(
            f'JIRA登录失败，HTTP {login_response.status_code}：'
            f'{(getattr(login_response, "text", "") or "")[:1000]}'
        )
        error.response = login_response
        raise error
    if _looks_like_jira_login_page(login_response):
        error_detail = _extract_jira_login_error_text(login_response)
        message = 'JIRA登录失败，请检查JIRA账号、密码或登录URL是否正确。'
        if rest_login_error:
            message += f'JIRA REST登录提示：{rest_login_error}。'
        if error_detail:
            message += f'JIRA登录页提示：{error_detail}'
        error = ValueError(message)
        error.response = login_response
        raise error

    return session


def _get_header_case_insensitive(headers, header_name):
    target = str(header_name or '').lower()
    for key, value in (headers or {}).items():
        if str(key).lower() == target:
            return value
    return None


def _remove_header_case_insensitive(headers, header_name):
    target = str(header_name or '').lower()
    for key in list((headers or {}).keys()):
        if str(key).lower() == target:
            headers.pop(key, None)


def _set_header_case_insensitive(headers, header_name, value):
    _remove_header_case_insensitive(headers, header_name)
    headers[str(header_name).lower()] = value


def _is_legacy_jira_cookie_value(value):
    cookie_value = str(value or '').strip()
    return cookie_value in {DEFAULT_BUG_JIRA_COOKIE, DEFAULT_REQUIREMENT_JIRA_COOKIE}


def _uses_legacy_jira_cookie(headers):
    cookie_value = _get_header_case_insensitive(headers, 'cookie')
    return _is_legacy_jira_cookie_value(cookie_value)


def _sanitize_jira_headers(headers):
    sanitized = dict(headers or {})
    for key, value in list(sanitized.items()):
        if str(key).lower() == 'cookie' and _is_legacy_jira_cookie_value(value):
            sanitized.pop(key, None)
    return sanitized


def _build_jira_auth_error_message(headers, profile, response=None):
    profile_label = 'JIRA需求' if _normalize_profile(profile) == REQUIREMENT_PROFILE else '线上BUG'
    used_authorization = bool(str(_get_header_case_insensitive(headers, 'authorization') or '').strip())
    used_cookie = bool(str(_get_header_case_insensitive(headers, 'cookie') or '').strip())
    used_legacy_cookie = _uses_legacy_jira_cookie(headers)
    challenge = str(response.headers.get('WWW-Authenticate') or '').strip() if response is not None else ''

    details = [f'{profile_label}接口认证失败，JIRA 返回 401。']
    if used_legacy_cookie:
        details.append('当前请求仍在使用源码内置的旧 Cookie，会话已失效。')
    elif used_cookie and not used_authorization:
        details.append('当前请求仅携带 Cookie，JIRA 会话很可能已过期。')
    elif used_authorization:
        details.append('当前请求已携带 Authorization，请检查令牌或 OAuth 凭据是否有效。')
    else:
        details.append('当前请求未携带可用的 Cookie 或 Authorization 认证信息。')

    if challenge:
        details.append(f'WWW-Authenticate: {challenge}')

    details.append(
        '请优先在接口配置中启用JIRA登录并配置登录URL、账号、密码，'
        f'或通过环境变量 {JIRA_GENERAL_LOGIN_URL_ENV}/{JIRA_GENERAL_USERNAME_ENV}/{JIRA_GENERAL_PASSWORD_ENV} '
        '以及 QUALITY_ANALYSIS_JIRA_BUG_*、QUALITY_ANALYSIS_JIRA_REQUIREMENT_* 注入运行时登录信息。'
        '如仍需沿用旧方式，也可以在接口配置的请求头中更新 cookie/authorization，'
        f'或通过环境变量 {JIRA_GENERAL_COOKIE_ENV}、{JIRA_GENERAL_AUTHORIZATION_ENV} '
        f'以及按类型覆盖的 {JIRA_BUG_COOKIE_ENV}/{JIRA_REQUIREMENT_COOKIE_ENV}、'
        f'{JIRA_BUG_AUTHORIZATION_ENV}/{JIRA_REQUIREMENT_AUTHORIZATION_ENV} 注入运行时认证。'
    )
    return ''.join(details)


def build_jira_jql(version, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    version_value = version or DEFAULT_JIRA_VERSION
    template = REQUIREMENT_JQL_TEMPLATE if profile == REQUIREMENT_PROFILE else BUG_JQL_TEMPLATE
    return template.format(version=version_value)


def build_default_jira_jql(version):
    return build_jira_jql(version, BUG_PROFILE)


def build_default_requirement_jira_jql(version):
    return build_jira_jql(version, REQUIREMENT_PROFILE)


def build_jira_referer(version, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    if profile == BUG_PROFILE:
        return f'http://172.31.119.34:8080/issues/?filter={DEFAULT_BUG_FILTER_ID}'
    if profile == REQUIREMENT_PROFILE:
        return f'http://172.31.119.34:8080/issues/?filter={DEFAULT_REQUIREMENT_FILTER_ID}'
    return f"http://172.31.119.34:8080/issues/?jql={quote(build_jira_jql(version, profile), safe='')}"


def build_default_jira_referer(version):
    return build_jira_referer(version, BUG_PROFILE)


def build_default_requirement_jira_referer(version):
    return build_jira_referer(version, REQUIREMENT_PROFILE)


def build_jira_headers(version, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    headers = {
        '__amdmodulename': 'jira/issue/utils/xsrf-token-header',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'connection': 'keep-alive',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'http://172.31.119.34:8080',
        'referer': build_jira_referer(version, profile),
        'user-agent': DEFAULT_JIRA_USER_AGENT,
        'x-atlassian-token': 'no-check',
        'x-requested-with': 'XMLHttpRequest',
    }
    runtime_authorization = _get_profiled_jira_authorization_override(profile)
    runtime_cookie = _get_profiled_jira_cookie_override(profile)
    if runtime_authorization:
        _set_header_case_insensitive(headers, 'authorization', runtime_authorization)
    if runtime_cookie:
        _set_header_case_insensitive(headers, 'cookie', runtime_cookie)
    return headers


def build_default_jira_headers(version):
    return build_jira_headers(version, BUG_PROFILE)


def build_default_requirement_jira_headers(version):
    return build_jira_headers(version, REQUIREMENT_PROFILE)


def build_jira_request_body(version, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    body = [('startIndex', 0)]
    if profile == BUG_PROFILE:
        body.append(('filterId', DEFAULT_BUG_FILTER_ID))
    if profile == REQUIREMENT_PROFILE:
        body.append(('filterId', DEFAULT_REQUIREMENT_FILTER_ID))
    body.extend(
        [
            ('jql', build_jira_jql(version, profile)),
            ('layoutKey', 'list-view'),
        ]
    )
    return urlencode(body)


def build_default_jira_request_body(version):
    return build_jira_request_body(version, BUG_PROFILE)


def build_default_requirement_jira_request_body(version):
    return build_jira_request_body(version, REQUIREMENT_PROFILE)


def build_default_jira_config(version, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    return {
        'name': 'JIRA需求接口' if profile == REQUIREMENT_PROFILE else 'JIRA线上BUG接口',
        'request_url': DEFAULT_JIRA_REQUEST_URL,
        'request_method': DEFAULT_JIRA_REQUEST_METHOD,
        'request_headers': build_jira_headers(version, profile),
        'request_body': build_jira_request_body(version, profile),
        'timeout_seconds': DEFAULT_JIRA_TIMEOUT_SECONDS,
        'jira_login_url': DEFAULT_JIRA_LOGIN_URL,
    }


def build_default_requirement_jira_config(version):
    return build_default_jira_config(version, REQUIREMENT_PROFILE)


def _normalize_text(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def _normalize_jira_field_key(value):
    normalized = _normalize_text(str(value or ''))
    return normalized.strip('"\'')


RAW_FIELD_LABELS_META_KEY = '__field_labels'
RAW_FIELD_ORDER_META_KEY = '__field_order'

REQUIREMENT_ENRICHMENT_FIELD_LABELS = {
    'issuetype': '任务类型',
    'issuekey': '需求编号',
    'summary': '需求标题',
    'customfield_10762': '客户或项目名称',
    'customfield_10702': '任务优先级',
    'status': '状态',
    'creator': '创建人',
    'customfield_10222': '测试人员',
    'customfield_11100': '版本内研发优先级别',
    'customfield_10761': '测试预估工时',
    'customfield_10738': 'PM进度',
    'customfield_10100': '必须发版',
    'customfield_10737': 'PM',
    'customfield_11000': '组别',
    'customfield_10743': '前端',
    'customfield_10523': '前端开始日期',
    'customfield_11017': '前端结束日期',
    'customfield_10741': '后端',
    'customfield_10522': '后端开始日期',
    'customfield_11019': '后端结束日期',
    'created': '创建日期',
    'customfield_10014': '预计提测日期',
    'customfield_11018': '提测时间',
    'customfield_10765': '整体进度|延期原因',
    'customfield_10015': '用例预估完成时间',
    'customfield_11020': '测试进展',
    'customfield_10746': '测试进度',
    'components': '模块',
    'customfield_10602': '前端是否完成',
    'customfield_10749': '前端预估工时',
    'customfield_10603': '后端是否完成',
    'customfield_10748': '后端预估工时',
}
REQUIREMENT_ENRICHMENT_SUPPORT_FIELD_LABELS = {
}
REQUIREMENT_ENRICHMENT_FIELD_KEYS = tuple(REQUIREMENT_ENRICHMENT_FIELD_LABELS.keys())
REQUIREMENT_ENRICHMENT_ALL_FIELD_KEYS = (
    *REQUIREMENT_ENRICHMENT_FIELD_KEYS,
)
REQUIREMENT_DATE_ONLY_FIELD_KEYS = {
    'created',
    'customfield_10014',
    'customfield_10015',
    'customfield_10522',
    'customfield_10523',
    'customfield_11017',
    'customfield_11019',
}
REQUIREMENT_DATETIME_FIELD_KEYS = {'customfield_11018'}

BUG_DOCUMENTED_FIELD_LABELS = {
    'issuetype': '任务类型',
    'issuekey': '缺陷编号',
    'summary': '缺陷标题',
    'customfield_10762': '客户或项目名称',
    'customfield_10702': '任务优先级',
    'customfield_10754': 'BUG处理反馈',
    'customfield_11101': 'BUG定性分类',
    'customfield_11102': 'BUG产生根因',
    'customfield_11103': 'BUG直接责任岗位',
    'components': '模块',
    'status': '状态',
    'creator': '创建人',
    'customfield_10222': '测试人员',
    'customfield_11100': '版本内研发优先级别',
    'customfield_10743': '前端',
    'customfield_10741': '后端',
    'customfield_10746': '测试进度',
    'customfield_10761': '测试预估工时',
    'customfield_10738': 'PM进度',
    'customfield_10100': '必须发版',
    'customfield_10737': 'PM',
    'customfield_11000': '组别',
    'customfield_10523': '前端开始日期',
    'customfield_11017': '前端结束日期',
    'customfield_10522': '后端开始日期',
    'customfield_11019': '后端结束日期',
    'created': '创建日期',
    'customfield_10014': '预计提测日期',
    'customfield_11018': '提测时间',
    'customfield_10765': '整体进度|延期原因',
    'customfield_10015': '用例预估完成时间',
    'customfield_11020': '测试进展',
    'customfield_10749': '前端预估工时',
    'customfield_10748': '后端预估工时',
    'customfield_10731': 'BUG责任人',
    'customfield_10019': 'BUG重新打开次数',
}
BUG_DOCUMENTED_FIELD_KEYS = tuple(BUG_DOCUMENTED_FIELD_LABELS.keys())
BUG_DATE_ONLY_FIELD_KEYS = {
    'created',
    'customfield_10014',
    'customfield_10015',
    'customfield_10522',
    'customfield_10523',
    'customfield_11017',
    'customfield_11019',
}
BUG_DATETIME_FIELD_KEYS = {'customfield_11018'}

SEMANTIC_FIELD_ALIASES = {
    'issue_key': (
        'issuekey',
        'key',
        'keyword',
        '关键字',
        '缺陷编号',
        '问题编号',
        'BUG编号',
        'JIRA编号',
    ),
    'issue_type': ('issuetype', '问题类型', '类型', '缺陷类型', 'BUG类型'),
    'summary': ('summary', '概要', '标题', '需求标题', '缺陷标题', '问题标题'),
    'module': ('components', 'component', '模块', '所属模块', '功能模块'),
    'customer_name': ('customfield_10762', '客户或项目名称', '客户', '项目名称'),
    'priority': ('customfield_10702', '任务优先级', '优先级', '严重级别', '缺陷等级'),
    'requirement_priority': (
        'customfield_11100',
        '版本内研发优先级别',
        '版本内研发优先级',
        '研发优先级别',
        '研发优先级',
    ),
    'status': ('status', '状态', '处理状态'),
    'creator': ('creator', 'reporter', '创建者', '创建人', '报告人'),
    'assignee': ('assignee', '经办人', '处理人', '负责人'),
    'bug_owner': ('customfield_10731', 'BUG责任人', '缺陷责任人', '责任人'),
    'bug_tester': ('customfield_10222', '测试人员', '测试工程师', '测试'),
    'product_manager': ('customfield_10737', 'PM', '产品经理', '产品负责人', '产品'),
    'requirement_handler': ('assignee', '经办人', '处理人', '负责人'),
    'requirement_tester': ('customfield_10222', '测试人员', '测试工程师', '测试'),
    'group_name': ('customfield_11000', 'group_name', '责任小组', '组别', '负责小组', '所属组别'),
    'frontend_developer': (
        'customfield_10743',
        'frontend',
        'front_end',
        '前端',
        '前端开发',
        '前端开发工程师',
    ),
    'backend_developer': (
        'customfield_10741',
        'backend',
        'back_end',
        '后端',
        '后端开发',
        '后端开发工程师',
    ),
    'requirement_backend_developer': (
        'customfield_10741',
        'backend',
        'back_end',
        '后端',
        '后端开发',
        '后端开发工程师',
    ),
    'description': ('description', '描述', '详细描述'),
}

ROLE_MEMBER_FIELD_ALIASES = {
    'product_manager': ('\u4ea7\u54c1', 'pm', 'product', 'productmanager'),
    'tester': ('\u6d4b\u8bd5', 'tester', 'test'),
    'frontend_developer': ('\u524d\u7aef', 'frontend', 'front-end', 'fe'),
    'backend_developer': ('\u540e\u7aef', 'backend', 'back-end', 'be'),
}


def _normalize_semantic_token(value):
    normalized = str(value or '').casefold()
    return re.sub(r'[\s_\-:：|/\\.,;，。；、()\[\]{}（）【】<>《》]+', '', normalized)


def _first_non_empty(*values):
    for value in values:
        normalized = _normalize_text(str(value or ''))
        if normalized:
            return normalized
    return ''


def _get_documented_raw_field(raw_fields, field_key):
    normalized_key = _normalize_jira_field_key(field_key)
    if not normalized_key:
        return ''
    return _normalize_text(str((raw_fields or {}).get(normalized_key) or ''))


def _is_raw_field_meta_key(field_key):
    return str(field_key or '').startswith('__')


def _normalize_person_lookup_key(value):
    normalized = _normalize_text(value).casefold()
    return re.sub(r'[\s_\-:：|/\\.,;，。；、()\[\]{}（）【】<>《》]+', '', normalized)


def _split_person_field_value(value):
    normalized = _normalize_text(value)
    if not normalized:
        return []

    parts = [
        _normalize_text(item)
        for item in re.split(r'[\n\r,，/\\|;；、]+', normalized)
    ]
    result = []
    seen = set()
    for item in parts:
        if not item:
            continue
        normalized_item = _normalize_person_lookup_key(item)
        if normalized_item in seen:
            continue
        seen.add(normalized_item)
        result.append(item)
    return result


def _build_role_member_summary(user):
    return {
        'id': user.id,
        'username': _normalize_text(getattr(user, 'username', '')),
        'email': _normalize_text(getattr(user, 'email', '')),
        'full_name': _normalize_text(getattr(user, 'full_name', '')) or _normalize_text(getattr(user, 'username', '')),
    }


def _iter_member_lookup_candidates(user):
    candidates = [
        getattr(user, 'username', ''),
        getattr(user, 'email', ''),
        str(getattr(user, 'email', '') or '').split('@', 1)[0],
        getattr(user, 'first_name', ''),
        getattr(user, 'last_name', ''),
        f"{getattr(user, 'first_name', '')}{getattr(user, 'last_name', '')}",
        f"{getattr(user, 'last_name', '')}{getattr(user, 'first_name', '')}",
        getattr(user, 'full_name', ''),
    ]
    for candidate in candidates:
        normalized_candidate = _normalize_person_lookup_key(candidate)
        if normalized_candidate:
            yield normalized_candidate


def build_role_member_lookup_bundle():
    roles = list(Role.objects.prefetch_related('members').all())
    normalized_roles = [
        {
            'name': _normalize_text(role.name),
            'token': _normalize_person_lookup_key(role.name),
            'members': list(role.members.all()),
        }
        for role in roles
    ]

    bundle = {}
    for field_key, aliases in ROLE_MEMBER_FIELD_ALIASES.items():
        alias_tokens = {
            _normalize_person_lookup_key(alias)
            for alias in aliases
            if _normalize_person_lookup_key(alias)
        }
        matched_roles = [
            role_item for role_item in normalized_roles
            if role_item['token'] in alias_tokens
        ]

        member_map = {}
        for role_item in matched_roles:
            for user in role_item['members']:
                summary = _build_role_member_summary(user)
                for candidate in _iter_member_lookup_candidates(user):
                    member_map.setdefault(candidate, summary)

        bundle[field_key] = {
            'role_names': [item['name'] for item in matched_roles if item['name']],
            'member_map': member_map,
        }

    return bundle


def _resolve_role_member_field_value(value, field_key, role_member_lookup=None):
    original_value = _normalize_text(value)
    if not original_value:
        return {
            'display_value': '',
            'members': [],
            'role_names': [],
        }

    lookup_bundle = role_member_lookup or build_role_member_lookup_bundle()
    lookup = lookup_bundle.get(field_key) or {}
    member_map = lookup.get('member_map') or {}
    role_names = lookup.get('role_names') or []
    if not member_map:
        return {
            'display_value': original_value,
            'members': [],
            'role_names': role_names,
        }

    members = []
    member_ids = set()
    display_parts = []
    seen_display_tokens = set()
    parts = _split_person_field_value(original_value) or [original_value]

    for part in parts:
        resolved_member = member_map.get(_normalize_person_lookup_key(part))
        display_value = _normalize_text((resolved_member or {}).get('full_name')) or part
        normalized_display = _normalize_person_lookup_key(display_value)
        if normalized_display and normalized_display not in seen_display_tokens:
            seen_display_tokens.add(normalized_display)
            display_parts.append(display_value)

        member_id = (resolved_member or {}).get('id')
        if member_id and member_id not in member_ids:
            member_ids.add(member_id)
            members.append(resolved_member)

    return {
        'display_value': ' / '.join(display_parts) if display_parts else original_value,
        'members': members,
        'role_names': role_names,
    }


def _iter_user_raw_fields(raw_fields):
    for field_key, field_value in (raw_fields or {}).items():
        if _is_raw_field_meta_key(field_key):
            continue
        yield str(field_key), field_value


def _get_raw_field_order(raw_fields):
    order = (raw_fields or {}).get(RAW_FIELD_ORDER_META_KEY) or []
    if not isinstance(order, list):
        return []
    return [
        _normalize_jira_field_key(field_key)
        for field_key in order
        if _normalize_jira_field_key(field_key)
    ]


def get_jira_raw_field_labels(raw_fields):
    labels = (raw_fields or {}).get(RAW_FIELD_LABELS_META_KEY) or {}
    if not isinstance(labels, dict):
        return {}
    return {
        _normalize_jira_field_key(field_key): _normalize_text(str(label))
        for field_key, label in labels.items()
        if _normalize_jira_field_key(field_key) and _normalize_text(str(label))
    }


def _extract_column_key_and_label(column):
    if isinstance(column, str):
        column_key = _normalize_jira_field_key(column)
        return column_key, ''

    if not isinstance(column, dict):
        return '', ''

    key_candidates = (
        'id',
        'key',
        'fieldKey',
        'field_key',
        'fieldId',
        'field_id',
        'field',
        'value',
    )
    label_candidates = ('label', 'displayName', 'display_name', 'title', 'text', 'name')

    column_key = ''
    for candidate in key_candidates:
        column_key = _normalize_jira_field_key(column.get(candidate))
        if column_key:
            break

    label = ''
    for candidate in label_candidates:
        label = _normalize_text(str(column.get(candidate) or ''))
        if label:
            break

    return column_key or _normalize_jira_field_key(label), label


def _extract_header_field_key(header):
    for attr_name in ('data-id', 'data-column-key', 'data-field-id', 'data-field-key'):
        attr_value = _normalize_jira_field_key(header.get(attr_name))
        if attr_value:
            return attr_value

    for class_name in (header.get('class') or '').split():
        normalized = _normalize_jira_field_key(class_name)
        if normalized and normalized not in {'sortable', 'nav', 'issue_actions'}:
            return normalized
    return ''


def _extract_issue_table_field_metadata(issue_table, root):
    field_labels = {}
    field_order = []

    for column in issue_table.get('columns') or []:
        field_key, label = _extract_column_key_and_label(column)
        if field_key and field_key not in field_order:
            field_order.append(field_key)
        if field_key and label and _normalize_semantic_token(field_key) != _normalize_semantic_token(label):
            field_labels[field_key] = label

    for header in root.xpath('.//th'):
        field_key = _extract_header_field_key(header)
        label = _normalize_text(' '.join(header.xpath('.//text()')))
        if not field_key or not label:
            continue
        if field_key not in field_order:
            field_order.append(field_key)
        field_labels.setdefault(field_key, label)

    return field_labels, field_order


def _attach_raw_field_metadata(raw_fields, field_labels, field_order):
    available_keys = {
        _normalize_jira_field_key(field_key)
        for field_key in raw_fields.keys()
        if not _is_raw_field_meta_key(field_key)
    }
    labels = {
        _normalize_jira_field_key(field_key): _normalize_text(str(label))
        for field_key, label in (field_labels or {}).items()
        if _normalize_jira_field_key(field_key) in available_keys and _normalize_text(str(label))
    }
    order = [
        _normalize_jira_field_key(field_key)
        for field_key in (field_order or [])
        if _normalize_jira_field_key(field_key) in available_keys
    ]

    if labels:
        raw_fields[RAW_FIELD_LABELS_META_KEY] = labels
    if order:
        raw_fields[RAW_FIELD_ORDER_META_KEY] = order


def _merge_raw_field_metadata(raw_fields, field_labels=None, field_order=None):
    merged_labels = dict(get_jira_raw_field_labels(raw_fields))
    for field_key, label in (field_labels or {}).items():
        normalized_field_key = _normalize_jira_field_key(field_key)
        normalized_label = _normalize_text(str(label))
        if not normalized_field_key or not normalized_label:
            continue
        merged_labels[normalized_field_key] = normalized_label

    merged_order = []
    seen = set()
    for field_key in [*_get_raw_field_order(raw_fields), *(field_order or [])]:
        normalized_field_key = _normalize_jira_field_key(field_key)
        if not normalized_field_key or normalized_field_key in seen:
            continue
        seen.add(normalized_field_key)
        merged_order.append(normalized_field_key)

    _attach_raw_field_metadata(raw_fields, merged_labels, merged_order)


def _normalize_jira_raw_fields(raw_fields):
    normalized_raw_fields = {}
    field_labels = {}
    field_order = []

    for field_key, field_value in (raw_fields or {}).items():
        if field_key == RAW_FIELD_LABELS_META_KEY and isinstance(field_value, dict):
            for label_key, label_value in field_value.items():
                normalized_label_key = _normalize_jira_field_key(label_key)
                normalized_label_value = _normalize_text(str(label_value))
                if normalized_label_key and normalized_label_value:
                    field_labels[normalized_label_key] = normalized_label_value
            continue

        if field_key == RAW_FIELD_ORDER_META_KEY and isinstance(field_value, list):
            for order_key in field_value:
                normalized_order_key = _normalize_jira_field_key(order_key)
                if normalized_order_key and normalized_order_key not in field_order:
                    field_order.append(normalized_order_key)
            continue

        if _is_raw_field_meta_key(field_key):
            continue

        normalized_field_key = _normalize_jira_field_key(field_key)
        if not normalized_field_key:
            continue

        existing_value = normalized_raw_fields.get(normalized_field_key)
        if existing_value and not _normalize_text(str(field_value or '')):
            continue
        normalized_raw_fields[normalized_field_key] = field_value

    if field_labels:
        normalized_raw_fields[RAW_FIELD_LABELS_META_KEY] = field_labels
    if field_order:
        normalized_raw_fields[RAW_FIELD_ORDER_META_KEY] = field_order
    return normalized_raw_fields


def _semantic_candidate_matches(candidates, aliases):
    alias_tokens = [_normalize_semantic_token(alias) for alias in aliases]
    alias_tokens = [alias for alias in alias_tokens if alias]
    if not alias_tokens:
        return False

    for candidate in candidates:
        candidate_token = _normalize_semantic_token(candidate)
        if not candidate_token:
            continue
        for alias_token in alias_tokens:
            if candidate_token == alias_token:
                return True
            if len(alias_token) >= 2 and (alias_token in candidate_token or candidate_token in alias_token):
                return True
    return False


def resolve_jira_raw_field(raw_fields, aliases, field_labels=None):
    field_labels = field_labels if field_labels is not None else get_jira_raw_field_labels(raw_fields)
    normalized_label_lookup = {
        _normalize_text(field_key): label
        for field_key, label in (field_labels or {}).items()
        if _normalize_text(field_key) and _normalize_text(label)
    }

    for alias in aliases:
        alias_key = _normalize_text(str(alias))
        if alias_key in (raw_fields or {}) and not _is_raw_field_meta_key(alias_key):
            resolved_value = _normalize_text(str(raw_fields.get(alias_key) or ''))
            if resolved_value:
                return resolved_value

    for field_key, field_value in _iter_user_raw_fields(raw_fields):
        label = (
            normalized_label_lookup.get(field_key)
            or normalized_label_lookup.get(_normalize_text(field_key))
            or ''
        )
        if not _semantic_candidate_matches((field_key, label), aliases):
            continue

        resolved_value = _normalize_text(str(field_value or ''))
        if resolved_value:
            return resolved_value

    return ''


def build_jira_record_mapped_fields(record, profile=BUG_PROFILE, role_member_lookup=None):
    profile = _normalize_profile(profile)
    raw_fields = getattr(record, 'raw_fields', None) or {}

    if profile == BUG_PROFILE:
        issue_key = _first_non_empty(_get_documented_raw_field(raw_fields, 'issuekey'), getattr(record, 'issue_key', ''))
        return {
            'defect_code': issue_key,
            'issue_key': issue_key,
            'issue_type': _get_documented_raw_field(raw_fields, 'issuetype'),
            'summary': _first_non_empty(_get_documented_raw_field(raw_fields, 'summary'), getattr(record, 'summary', '')),
            'module': _get_documented_raw_field(raw_fields, 'components'),
            'customer_name': _get_documented_raw_field(raw_fields, 'customfield_10762'),
            'priority': _get_documented_raw_field(raw_fields, 'customfield_10702'),
            'status': _get_documented_raw_field(raw_fields, 'status'),
            'creator': _get_documented_raw_field(raw_fields, 'creator'),
            'handler': _get_documented_raw_field(raw_fields, 'customfield_10731'),
            'product_manager': _get_documented_raw_field(raw_fields, 'customfield_10737'),
            'product_manager_members': [],
            'product_manager_roles': [],
            'tester': _get_documented_raw_field(raw_fields, 'customfield_10222'),
            'tester_members': [],
            'tester_roles': [],
            'group_name': _get_documented_raw_field(raw_fields, 'customfield_11000'),
            'frontend_developer': _get_documented_raw_field(raw_fields, 'customfield_10743'),
            'frontend_developer_members': [],
            'frontend_developer_roles': [],
            'backend_developer': _get_documented_raw_field(raw_fields, 'customfield_10741'),
            'backend_developer_members': [],
            'backend_developer_roles': [],
        }

    if profile == REQUIREMENT_PROFILE:
        issue_key = _first_non_empty(_get_documented_raw_field(raw_fields, 'issuekey'), getattr(record, 'issue_key', ''))
        product_manager_resolution = _resolve_role_member_field_value(
            _get_documented_raw_field(raw_fields, 'customfield_10737'),
            'product_manager',
            role_member_lookup=role_member_lookup,
        )
        tester_resolution = _resolve_role_member_field_value(
            _get_documented_raw_field(raw_fields, 'customfield_10222'),
            'tester',
            role_member_lookup=role_member_lookup,
        )
        frontend_resolution = _resolve_role_member_field_value(
            _get_documented_raw_field(raw_fields, 'customfield_10743'),
            'frontend_developer',
            role_member_lookup=role_member_lookup,
        )
        backend_resolution = _resolve_role_member_field_value(
            _get_documented_raw_field(raw_fields, 'customfield_10741'),
            'backend_developer',
            role_member_lookup=role_member_lookup,
        )
        return {
            'defect_code': issue_key,
            'issue_key': issue_key,
            'issue_type': _get_documented_raw_field(raw_fields, 'issuetype'),
            'summary': _first_non_empty(_get_documented_raw_field(raw_fields, 'summary'), getattr(record, 'summary', '')),
            'module': _get_documented_raw_field(raw_fields, 'components'),
            'customer_name': _get_documented_raw_field(raw_fields, 'customfield_10762'),
            'priority': _get_documented_raw_field(raw_fields, 'customfield_11100'),
            'status': _get_documented_raw_field(raw_fields, 'status'),
            'creator': _get_documented_raw_field(raw_fields, 'creator'),
            'handler': '',
            'product_manager': product_manager_resolution['display_value'],
            'product_manager_members': product_manager_resolution['members'],
            'product_manager_roles': product_manager_resolution['role_names'],
            'tester': tester_resolution['display_value'],
            'tester_members': tester_resolution['members'],
            'tester_roles': tester_resolution['role_names'],
            'group_name': _get_documented_raw_field(raw_fields, 'customfield_11000'),
            'frontend_developer': frontend_resolution['display_value'],
            'frontend_developer_members': frontend_resolution['members'],
            'frontend_developer_roles': frontend_resolution['role_names'],
            'backend_developer': backend_resolution['display_value'],
            'backend_developer_members': backend_resolution['members'],
            'backend_developer_roles': backend_resolution['role_names'],
        }

    issue_key = _first_non_empty(
        getattr(record, 'issue_key', ''),
        resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['issue_key']),
    )
    handler_aliases = (
        SEMANTIC_FIELD_ALIASES['requirement_handler']
        if profile == REQUIREMENT_PROFILE
        else SEMANTIC_FIELD_ALIASES['bug_owner'] + SEMANTIC_FIELD_ALIASES['assignee']
    )
    tester_aliases = (
        SEMANTIC_FIELD_ALIASES['requirement_tester']
        if profile == REQUIREMENT_PROFILE
        else SEMANTIC_FIELD_ALIASES['bug_tester']
    )
    product_manager_value = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['product_manager'])
    tester_value = _first_non_empty(getattr(record, 'tester', ''), resolve_jira_raw_field(raw_fields, tester_aliases))
    frontend_value = _first_non_empty(
        getattr(record, 'frontend_developer', ''),
        resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['frontend_developer']),
    )
    backend_value = _first_non_empty(
        getattr(record, 'backend_developer', ''),
        resolve_jira_raw_field(
            raw_fields,
            SEMANTIC_FIELD_ALIASES['requirement_backend_developer']
            if profile == REQUIREMENT_PROFILE
            else SEMANTIC_FIELD_ALIASES['backend_developer'],
        ),
    )

    if profile == REQUIREMENT_PROFILE:
        product_manager_resolution = _resolve_role_member_field_value(
            product_manager_value,
            'product_manager',
            role_member_lookup=role_member_lookup,
        )
        tester_resolution = _resolve_role_member_field_value(
            tester_value,
            'tester',
            role_member_lookup=role_member_lookup,
        )
        frontend_resolution = _resolve_role_member_field_value(
            frontend_value,
            'frontend_developer',
            role_member_lookup=role_member_lookup,
        )
        backend_resolution = _resolve_role_member_field_value(
            backend_value,
            'backend_developer',
            role_member_lookup=role_member_lookup,
        )
        product_manager_mapped = product_manager_resolution['display_value']
        product_manager_members = product_manager_resolution['members']
        product_manager_roles = product_manager_resolution['role_names']
        tester_mapped = tester_resolution['display_value']
        tester_members = tester_resolution['members']
        tester_roles = tester_resolution['role_names']
        frontend_mapped = frontend_resolution['display_value']
        frontend_members = frontend_resolution['members']
        frontend_roles = frontend_resolution['role_names']
        backend_mapped = backend_resolution['display_value']
        backend_members = backend_resolution['members']
        backend_roles = backend_resolution['role_names']
    else:
        product_manager_mapped = product_manager_value
        product_manager_members = []
        product_manager_roles = []
        tester_mapped = tester_value
        tester_members = []
        tester_roles = []
        frontend_mapped = frontend_value
        frontend_members = []
        frontend_roles = []
        backend_mapped = backend_value
        backend_members = []
        backend_roles = []

    return {
        'defect_code': issue_key,
        'issue_key': issue_key,
        'issue_type': _first_non_empty(
            getattr(record, 'issue_type', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['issue_type']),
        ),
        'summary': _first_non_empty(
            getattr(record, 'summary', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['summary']),
        ),
        'module': _first_non_empty(
            getattr(record, 'module', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['module']),
        ),
        'customer_name': _first_non_empty(
            getattr(record, 'customer_name', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['customer_name']),
        ),
        'priority': _first_non_empty(
            getattr(record, 'priority', ''),
            resolve_jira_raw_field(
                raw_fields,
                SEMANTIC_FIELD_ALIASES['requirement_priority']
                if profile == REQUIREMENT_PROFILE
                else SEMANTIC_FIELD_ALIASES['priority'],
            ),
        ),
        'status': _first_non_empty(
            getattr(record, 'status', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['status']),
        ),
        'creator': _first_non_empty(
            getattr(record, 'creator', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['creator']),
        ),
        'handler': _first_non_empty(
            getattr(record, 'handler', ''),
            resolve_jira_raw_field(raw_fields, handler_aliases),
        ),
        'product_manager': product_manager_mapped,
        'product_manager_members': product_manager_members,
        'product_manager_roles': product_manager_roles,
        'tester': tester_mapped,
        'tester_members': tester_members,
        'tester_roles': tester_roles,
        'group_name': _first_non_empty(
            getattr(record, 'group_name', ''),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['group_name']),
        ),
        'frontend_developer': frontend_mapped,
        'frontend_developer_members': frontend_members,
        'frontend_developer_roles': frontend_roles,
        'backend_developer': backend_mapped,
        'backend_developer_members': backend_members,
        'backend_developer_roles': backend_roles,
    }


def _build_jira_record_from_raw_fields(raw_fields, profile, *, issue_id='', issue_key='', row_index=0):
    profile = _normalize_profile(profile)
    raw_field_labels = get_jira_raw_field_labels(raw_fields)

    if profile == BUG_PROFILE:
        resolved_issue_key = _first_non_empty(issue_key, _get_documented_raw_field(raw_fields, 'issuekey'))
        if not resolved_issue_key:
            return None
        return {
            'issue_id': _normalize_text(issue_id),
            'issue_key': resolved_issue_key,
            'issue_type': _get_documented_raw_field(raw_fields, 'issuetype'),
            'summary': _get_documented_raw_field(raw_fields, 'summary'),
            'module': _get_documented_raw_field(raw_fields, 'components'),
            'customer_name': _get_documented_raw_field(raw_fields, 'customfield_10762'),
            'priority': _get_documented_raw_field(raw_fields, 'customfield_10702'),
            'status': _get_documented_raw_field(raw_fields, 'status'),
            'description': _get_documented_raw_field(raw_fields, 'description'),
            'creator': _get_documented_raw_field(raw_fields, 'creator'),
            'handler': _get_documented_raw_field(raw_fields, 'customfield_10731'),
            'tester': _get_documented_raw_field(raw_fields, 'customfield_10222'),
            'group_name': _get_documented_raw_field(raw_fields, 'customfield_11000'),
            'frontend_developer': _get_documented_raw_field(raw_fields, 'customfield_10743'),
            'backend_developer': _get_documented_raw_field(raw_fields, 'customfield_10741'),
            'row_index': row_index,
            'raw_fields': raw_fields,
        }

    if profile == REQUIREMENT_PROFILE:
        resolved_issue_key = _first_non_empty(issue_key, _get_documented_raw_field(raw_fields, 'issuekey'))
        if not resolved_issue_key:
            return None
        return {
            'issue_id': _normalize_text(issue_id),
            'issue_key': resolved_issue_key,
            'issue_type': _get_documented_raw_field(raw_fields, 'issuetype'),
            'summary': _get_documented_raw_field(raw_fields, 'summary'),
            'module': _get_documented_raw_field(raw_fields, 'components'),
            'customer_name': _get_documented_raw_field(raw_fields, 'customfield_10762'),
            'priority': _get_documented_raw_field(raw_fields, 'customfield_11100'),
            'status': _get_documented_raw_field(raw_fields, 'status'),
            'description': '',
            'creator': _get_documented_raw_field(raw_fields, 'creator'),
            'handler': '',
            'tester': _get_documented_raw_field(raw_fields, 'customfield_10222'),
            'group_name': _get_documented_raw_field(raw_fields, 'customfield_11000'),
            'frontend_developer': _get_documented_raw_field(raw_fields, 'customfield_10743'),
            'backend_developer': _get_documented_raw_field(raw_fields, 'customfield_10741'),
            'row_index': row_index,
            'raw_fields': raw_fields,
        }

    resolved_issue_key = (
        _normalize_text(issue_key)
        or resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['issue_key'], raw_field_labels)
    )
    if not resolved_issue_key:
        return None

    issue_type = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['issue_type'], raw_field_labels)
    summary = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['summary'], raw_field_labels)
    module = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['module'], raw_field_labels)
    customer_name = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['customer_name'], raw_field_labels)
    priority = resolve_jira_raw_field(
        raw_fields,
        SEMANTIC_FIELD_ALIASES['requirement_priority']
        if profile == REQUIREMENT_PROFILE
        else SEMANTIC_FIELD_ALIASES['priority'],
        raw_field_labels,
    )
    status = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['status'], raw_field_labels)
    description = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['description'], raw_field_labels)
    creator = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['creator'], raw_field_labels)
    group_name = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['group_name'], raw_field_labels)
    frontend_developer = resolve_jira_raw_field(
        raw_fields,
        SEMANTIC_FIELD_ALIASES['frontend_developer'],
        raw_field_labels,
    )
    backend_developer = resolve_jira_raw_field(
        raw_fields,
        SEMANTIC_FIELD_ALIASES['requirement_backend_developer']
        if profile == REQUIREMENT_PROFILE
        else SEMANTIC_FIELD_ALIASES['backend_developer'],
        raw_field_labels,
    )

    if profile == REQUIREMENT_PROFILE:
        handler = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['requirement_handler'], raw_field_labels)
        tester = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['requirement_tester'], raw_field_labels)
    else:
        handler = _first_non_empty(
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['bug_owner'], raw_field_labels),
            resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['assignee'], raw_field_labels),
        )
        tester = resolve_jira_raw_field(raw_fields, SEMANTIC_FIELD_ALIASES['bug_tester'], raw_field_labels)

    return {
        'issue_id': _normalize_text(issue_id),
        'issue_key': resolved_issue_key,
        'issue_type': issue_type,
        'summary': summary,
        'module': module,
        'customer_name': customer_name,
        'priority': priority,
        'status': status,
        'description': description,
        'creator': creator,
        'handler': handler,
        'tester': tester,
        'group_name': group_name,
        'frontend_developer': frontend_developer,
        'backend_developer': backend_developer,
        'row_index': row_index,
        'raw_fields': raw_fields,
    }


def _normalize_jira_api_datetime_text(value, *, with_time=False):
    normalized = _normalize_text(str(value or ''))
    if not normalized:
        return ''

    matched = re.match(
        r'^(?P<date>\d{4}-\d{2}-\d{2})(?:[T\s](?P<time>\d{2}:\d{2})(?::\d{2})?(?:\.\d+)?)?',
        normalized,
    )
    if not matched:
        return normalized

    if with_time and matched.group('time'):
        return f"{matched.group('date')} {matched.group('time')}"
    return matched.group('date')


def _normalize_jira_api_field_value(field_key, value):
    if value is None:
        return ''

    if isinstance(value, bool):
        return '是' if value else '否'

    if isinstance(value, list):
        parts = [
            _normalize_jira_api_field_value(field_key, item)
            for item in value
        ]
        return _normalize_text(' / '.join(part for part in parts if _normalize_text(part)))

    if isinstance(value, dict):
        for candidate in ('displayName', 'display_name', 'name', 'value', 'label'):
            resolved = _normalize_text(value.get(candidate))
            if resolved:
                return _normalize_jira_api_field_value(field_key, resolved)
        if value.get('child') is not None:
            return _normalize_jira_api_field_value(field_key, value.get('child'))
        return _normalize_text(str(value))

    normalized = _normalize_text(str(value))
    if not normalized:
        return ''

    normalized_field_key = _normalize_jira_field_key(field_key)
    if normalized_field_key in REQUIREMENT_DATE_ONLY_FIELD_KEYS or normalized_field_key in BUG_DATE_ONLY_FIELD_KEYS:
        return _normalize_jira_api_datetime_text(normalized, with_time=False)
    if normalized_field_key in REQUIREMENT_DATETIME_FIELD_KEYS or normalized_field_key in BUG_DATETIME_FIELD_KEYS:
        return _normalize_jira_api_datetime_text(normalized, with_time=True)
    return normalized


def _build_jira_search_url(request_url):
    parsed = urlparse(_normalize_text(request_url) or DEFAULT_JIRA_REQUEST_URL)
    fallback = urlparse(DEFAULT_JIRA_REQUEST_URL)
    scheme = parsed.scheme or fallback.scheme
    netloc = parsed.netloc or fallback.netloc
    return urlunparse((scheme, netloc, '/rest/api/2/search', '', '', ''))


def _iter_chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _build_jira_search_request(config, issue_keys, field_keys, profile, use_login_session=False):
    headers = _sanitize_jira_headers(
        {str(key): str(value) for key, value in (config.request_headers or {}).items() if value is not None}
    )
    runtime_authorization = _get_profiled_jira_authorization_override(profile)
    runtime_cookie = _get_profiled_jira_cookie_override(profile)
    if runtime_authorization:
        _set_header_case_insensitive(headers, 'authorization', runtime_authorization)
    if runtime_cookie:
        _set_header_case_insensitive(headers, 'cookie', runtime_cookie)
    if use_login_session:
        _remove_header_case_insensitive(headers, 'cookie')
    _set_header_case_insensitive(headers, 'accept', 'application/json')
    _set_header_case_insensitive(headers, 'content-type', 'application/json; charset=UTF-8')

    normalized_field_keys = []
    seen_field_keys = set()
    for field_key in field_keys:
        normalized_field_key = _normalize_jira_field_key(field_key)
        if (
            not normalized_field_key
            or normalized_field_key == 'issuekey'
            or normalized_field_key in seen_field_keys
        ):
            continue
        seen_field_keys.add(normalized_field_key)
        normalized_field_keys.append(normalized_field_key)

    return {
        'method': 'POST',
        'url': _build_jira_search_url(config.request_url),
        'headers': headers,
        'timeout': config.timeout_seconds or DEFAULT_JIRA_TIMEOUT_SECONDS,
        'params': {'expand': 'names'},
        'json': {
            'jql': f"key in ({', '.join(issue_keys)})",
            'startAt': 0,
            'maxResults': len(issue_keys),
            'fields': normalized_field_keys,
        },
    }


def _extract_jira_search_issue_raw_fields(issue, field_keys):
    issue_key = _normalize_text(issue.get('key'))
    fields = issue.get('fields') or {}
    raw_fields = {}

    for field_key in field_keys:
        normalized_field_key = _normalize_jira_field_key(field_key)
        if not normalized_field_key:
            continue
        if normalized_field_key == 'issuekey':
            raw_fields[normalized_field_key] = issue_key
            continue
        if normalized_field_key not in fields:
            raw_fields[normalized_field_key] = ''
            continue
        raw_fields[normalized_field_key] = _normalize_jira_api_field_value(
            normalized_field_key,
            fields.get(normalized_field_key),
        )

    return issue_key, _normalize_jira_raw_fields(raw_fields)


def _records_need_documented_field_enrichment(records, documented_field_keys):
    normalized_field_keys = [
        _normalize_jira_field_key(field_key)
        for field_key in documented_field_keys
        if _normalize_jira_field_key(field_key) and _normalize_jira_field_key(field_key) != 'issuekey'
    ]
    if not normalized_field_keys:
        return False

    for record in records or []:
        raw_fields = _normalize_jira_raw_fields(record.get('raw_fields') or {})
        if any(normalized_field_key not in raw_fields for normalized_field_key in normalized_field_keys):
            return True
    return False


def enrich_jira_requirement_records(config, records, session=None):
    if not records:
        return records

    if not _records_need_documented_field_enrichment(records, REQUIREMENT_ENRICHMENT_FIELD_KEYS):
        for record in records:
            raw_fields = _normalize_jira_raw_fields(record.get('raw_fields') or {})
            _merge_raw_field_metadata(raw_fields, REQUIREMENT_ENRICHMENT_FIELD_LABELS, REQUIREMENT_ENRICHMENT_FIELD_KEYS)
            rebuilt_record = _build_jira_record_from_raw_fields(
                raw_fields,
                REQUIREMENT_PROFILE,
                issue_id=record.get('issue_id', ''),
                issue_key=record.get('issue_key', ''),
                row_index=record.get('row_index', 0),
            )
            if rebuilt_record:
                record.update(rebuilt_record)
            else:
                record['raw_fields'] = raw_fields
        return records

    issue_keys = [
        _normalize_text(record.get('issue_key'))
        for record in records
        if _normalize_text(record.get('issue_key'))
    ]
    if not issue_keys:
        return records

    label_map = dict(REQUIREMENT_ENRICHMENT_FIELD_LABELS)
    issue_field_map = {}

    for chunk in _iter_chunks(issue_keys, 50):
        request_kwargs = _build_jira_search_request(
            config,
            chunk,
            REQUIREMENT_ENRICHMENT_ALL_FIELD_KEYS,
            REQUIREMENT_PROFILE,
            use_login_session=session is not None,
        )
        response = _send_jira_request(request_kwargs, session=session)
        if response.status_code == 401:
            error = ValueError(_build_jira_auth_error_message(request_kwargs.get('headers'), REQUIREMENT_PROFILE, response))
            error.response = response
            raise error
        if response.status_code == 400:
            error = ValueError(f'JIRA需求字段补全接口返回 400：{(getattr(response, "text", "") or "")[:1000]}')
            error.response = response
            raise error
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError('JIRA需求字段补全接口返回的不是合法 JSON 数据') from exc

        for field_key, label in (payload.get('names') or {}).items():
            normalized_field_key = _normalize_jira_field_key(field_key)
            normalized_label = _normalize_text(label)
            if normalized_field_key and normalized_label and normalized_field_key not in label_map:
                label_map[normalized_field_key] = normalized_label

        for issue in payload.get('issues') or []:
            resolved_issue_key, raw_fields = _extract_jira_search_issue_raw_fields(
                issue,
                REQUIREMENT_ENRICHMENT_ALL_FIELD_KEYS,
            )
            if resolved_issue_key:
                issue_field_map[resolved_issue_key] = raw_fields

    for record in records:
        issue_key = _normalize_text(record.get('issue_key'))
        raw_fields = _normalize_jira_raw_fields(record.get('raw_fields') or {})
        search_raw_fields = issue_field_map.get(issue_key, {})

        for field_key in REQUIREMENT_ENRICHMENT_FIELD_KEYS:
            normalized_field_key = _normalize_jira_field_key(field_key)
            if not normalized_field_key:
                continue
            value = issue_key if normalized_field_key == 'issuekey' else search_raw_fields.get(normalized_field_key, '')
            if value or normalized_field_key not in raw_fields:
                raw_fields[normalized_field_key] = value

        _merge_raw_field_metadata(raw_fields, label_map, REQUIREMENT_ENRICHMENT_FIELD_KEYS)
        rebuilt_record = _build_jira_record_from_raw_fields(
            raw_fields,
            REQUIREMENT_PROFILE,
            issue_id=record.get('issue_id', ''),
            issue_key=issue_key,
            row_index=record.get('row_index', 0),
        )
        if rebuilt_record:
            record.update(rebuilt_record)
        else:
            record['raw_fields'] = raw_fields

    return records


def enrich_jira_bug_records(config, records, session=None):
    if not records:
        return records

    if not _records_need_documented_field_enrichment(records, BUG_DOCUMENTED_FIELD_KEYS):
        for record in records:
            raw_fields = _normalize_jira_raw_fields(record.get('raw_fields') or {})
            _merge_raw_field_metadata(raw_fields, BUG_DOCUMENTED_FIELD_LABELS, BUG_DOCUMENTED_FIELD_KEYS)
            rebuilt_record = _build_jira_record_from_raw_fields(
                raw_fields,
                BUG_PROFILE,
                issue_id=record.get('issue_id', ''),
                issue_key=record.get('issue_key', ''),
                row_index=record.get('row_index', 0),
            )
            if rebuilt_record:
                record.update(rebuilt_record)
            else:
                record['raw_fields'] = raw_fields
        return records

    issue_keys = [
        _normalize_text(record.get('issue_key'))
        for record in records
        if _normalize_text(record.get('issue_key'))
    ]
    if not issue_keys:
        return records

    label_map = dict(BUG_DOCUMENTED_FIELD_LABELS)
    issue_field_map = {}

    for chunk in _iter_chunks(issue_keys, 50):
        request_kwargs = _build_jira_search_request(
            config,
            chunk,
            BUG_DOCUMENTED_FIELD_KEYS,
            BUG_PROFILE,
            use_login_session=session is not None,
        )
        response = _send_jira_request(request_kwargs, session=session)
        if response.status_code == 401:
            error = ValueError(_build_jira_auth_error_message(request_kwargs.get('headers'), BUG_PROFILE, response))
            error.response = response
            raise error
        if response.status_code == 400:
            error = ValueError(f'JIRA线上BUG字段补全接口返回 400：{(getattr(response, "text", "") or "")[:1000]}')
            error.response = response
            raise error
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError('JIRA线上BUG字段补全接口返回的不是合法 JSON 数据') from exc

        for field_key, label in (payload.get('names') or {}).items():
            normalized_field_key = _normalize_jira_field_key(field_key)
            normalized_label = _normalize_text(label)
            if normalized_field_key and normalized_label and normalized_field_key not in label_map:
                label_map[normalized_field_key] = normalized_label

        for issue in payload.get('issues') or []:
            resolved_issue_key, raw_fields = _extract_jira_search_issue_raw_fields(
                issue,
                BUG_DOCUMENTED_FIELD_KEYS,
            )
            if resolved_issue_key:
                issue_field_map[resolved_issue_key] = raw_fields

    for record in records:
        issue_key = _normalize_text(record.get('issue_key'))
        raw_fields = _normalize_jira_raw_fields(record.get('raw_fields') or {})
        search_raw_fields = issue_field_map.get(issue_key, {})

        for field_key in BUG_DOCUMENTED_FIELD_KEYS:
            normalized_field_key = _normalize_jira_field_key(field_key)
            if not normalized_field_key:
                continue
            value = issue_key if normalized_field_key == 'issuekey' else search_raw_fields.get(normalized_field_key, '')
            if value or normalized_field_key not in raw_fields:
                raw_fields[normalized_field_key] = value

        _merge_raw_field_metadata(raw_fields, label_map, BUG_DOCUMENTED_FIELD_KEYS)
        rebuilt_record = _build_jira_record_from_raw_fields(
            raw_fields,
            BUG_PROFILE,
            issue_id=record.get('issue_id', ''),
            issue_key=issue_key,
            row_index=record.get('row_index', 0),
        )
        if rebuilt_record:
            record.update(rebuilt_record)
        else:
            record['raw_fields'] = raw_fields

    return records


def _extract_cell_value(cell, field_key):
    if field_key == 'issuetype':
        issue_type = cell.xpath('.//img/@alt')
        if issue_type:
            return _normalize_text(issue_type[0])
    if field_key in {'issuekey', 'summary'}:
        link_texts = cell.xpath('.//a[@data-issue-key]/text()')
        if link_texts:
            return _normalize_text(' '.join(link_texts))
    if field_key == 'status':
        status_texts = cell.xpath('.//span/text()')
        if status_texts:
            return _normalize_text(' '.join(status_texts))
    return _normalize_text(' '.join(cell.xpath('.//text()')))


def parse_jira_issue_table_payload(payload, profile=BUG_PROFILE):
    profile = _normalize_profile(profile)
    issue_table = payload.get('issueTable') or {}
    table_html = issue_table.get('table')
    if not table_html:
        raise ValueError('接口返回中缺少 issueTable.table 内容')

    root = html.fragment_fromstring(f'<div>{table_html}</div>', create_parent=True)
    rows = root.xpath('.//tr[contains(@class, "issuerow")]')
    field_labels, field_order = _extract_issue_table_field_metadata(issue_table, root)

    records = []
    for index, row in enumerate(rows, start=1):
        raw_fields = {}
        for cell in row.xpath('./td'):
            classes = (cell.get('class') or '').split()
            if not classes:
                continue
            field_key = _normalize_jira_field_key(classes[0])
            if field_key == 'issue_actions':
                continue
            raw_fields[field_key] = _extract_cell_value(cell, field_key)

        raw_fields = _normalize_jira_raw_fields(raw_fields)
        _attach_raw_field_metadata(raw_fields, field_labels, field_order)
        if profile == BUG_PROFILE:
            _merge_raw_field_metadata(raw_fields, BUG_DOCUMENTED_FIELD_LABELS, BUG_DOCUMENTED_FIELD_KEYS)
        parsed_record = _build_jira_record_from_raw_fields(
            raw_fields,
            profile,
            issue_id=row.get('rel') or '',
            issue_key=row.get('data-issuekey') or '',
            row_index=index,
        )
        if parsed_record:
            records.append(parsed_record)

    return {
        'total': int(issue_table.get('total') or len(records)),
        'displayed': int(issue_table.get('displayed') or len(records)),
        'start_index': int(issue_table.get('startIndex') or 0),
        'end': int(issue_table.get('end') or len(records)),
        'page': int(issue_table.get('page') or 0),
        'page_size': int(issue_table.get('pageSize') or len(records) or 1),
        'issue_keys': issue_table.get('issueKeys') or [],
        'issue_ids': issue_table.get('issueIds') or [],
        'columns': issue_table.get('columns') or [],
        'records': records,
    }


def _build_execution_request(config, start_index, use_login_session=False):
    method = (config.request_method or DEFAULT_JIRA_REQUEST_METHOD).upper()
    headers = _sanitize_jira_headers(
        {str(key): str(value) for key, value in (config.request_headers or {}).items() if value is not None}
    )
    request_profile = getattr(config, 'jira_profile', BUG_PROFILE)
    runtime_authorization = _get_profiled_jira_authorization_override(request_profile)
    runtime_cookie = _get_profiled_jira_cookie_override(request_profile)
    if runtime_authorization:
        _set_header_case_insensitive(headers, 'authorization', runtime_authorization)
    if runtime_cookie:
        _set_header_case_insensitive(headers, 'cookie', runtime_cookie)
    if use_login_session:
        _remove_header_case_insensitive(headers, 'cookie')
    body_data = dict(parse_qsl(config.request_body or '', keep_blank_values=True))
    body_data['startIndex'] = str(start_index)

    request_kwargs = {
        'method': method,
        'url': config.request_url,
        'headers': headers,
        'timeout': config.timeout_seconds or DEFAULT_JIRA_TIMEOUT_SECONDS,
    }
    if method == 'GET':
        request_kwargs['params'] = body_data
    else:
        request_kwargs['data'] = urlencode(body_data)
    return request_kwargs


def _send_jira_request(request_kwargs, session=None):
    if session is not None:
        return session.request(**request_kwargs)
    return requests.request(**request_kwargs)


def _request_issue_table(request_kwargs, session=None):
    return _send_jira_request(request_kwargs, session=session)


def _is_private_filter_400(response):
    if response is None or getattr(response, 'status_code', None) != 400:
        return False
    body = ''
    try:
        body = response.text or ''
    except Exception:
        body = ''
    return '筛选器不存在或是私用' in body or 'filter' in body.lower()


def _remove_filter_id_from_request(request_kwargs):
    cleaned = dict(request_kwargs)
    data = cleaned.get('data')
    params = cleaned.get('params')
    if data is not None:
        body_data = dict(parse_qsl(str(data), keep_blank_values=True))
        body_data.pop('filterId', None)
        cleaned['data'] = urlencode(body_data)
    if params is not None:
        body_data = dict(params)
        body_data.pop('filterId', None)
        cleaned['params'] = body_data
    return cleaned


def capture_preserved_jira_fields(record_model, version):
    normalized_version = normalize_jira_version(version)
    available_fields = {field.name for field in record_model._meta.fields}
    preserved_field_names = [
        field_name
        for field_name in (
            'related_requirements',
            'related_testcases',
            'related_testpoints',
            'related_mindmaps',
        )
        if field_name in available_fields
    ]
    if not preserved_field_names:
        return {}

    preserved_map = {}
    queryset = record_model.objects.filter(version=normalized_version).only('issue_key', *preserved_field_names)
    for item in queryset:
        preserved_values = {}
        for field_name in preserved_field_names:
            field_value = getattr(item, field_name, None)
            if field_value:
                preserved_values[field_name] = field_value

        if preserved_values:
            preserved_map[item.issue_key] = preserved_values

    return preserved_map


@transaction.atomic
def sync_jira_records(config, records, record_model, preserved_map=None):
    now = timezone.now()
    current_keys = []
    normalized_version = normalize_jira_version(config.version)
    preserved_map = preserved_map or {}
    available_fields = {field.name for field in record_model._meta.fields}

    for row_index, record in enumerate(records, start=1):
        issue_key = record.get('issue_key')
        if not issue_key:
            continue

        current_keys.append(issue_key)
        defaults = {
            'config': config,
            'version': normalized_version,
            'issue_id': record.get('issue_id', ''),
            'issue_type': record.get('issue_type', ''),
            'summary': record.get('summary', ''),
            'module': record.get('module', ''),
            'customer_name': record.get('customer_name', ''),
            'priority': record.get('priority', ''),
            'status': record.get('status', ''),
            'creator': record.get('creator', ''),
            'handler': record.get('handler', ''),
            'tester': record.get('tester', ''),
            'group_name': record.get('group_name', ''),
            'row_index': row_index,
            'raw_fields': record.get('raw_fields', {}),
            'synced_at': now,
        }
        if 'description' in available_fields:
            defaults['description'] = record.get('description', '')
        if 'frontend_developer' in available_fields:
            defaults['frontend_developer'] = record.get('frontend_developer', '')
        if 'backend_developer' in available_fields:
            defaults['backend_developer'] = record.get('backend_developer', '')
        if 'related_mindmaps' in available_fields:
            defaults['related_mindmaps'] = record.get('related_mindmaps', [])
        defaults.update(preserved_map.get(issue_key, {}))
        record_model.objects.update_or_create(
            version=normalized_version,
            issue_key=issue_key,
            defaults=defaults,
        )

    stale_queryset = record_model.objects.filter(version=normalized_version)
    if current_keys:
        stale_queryset = stale_queryset.exclude(issue_key__in=current_keys)
    stale_queryset.delete()

    return len(current_keys)


def sync_jira_bug_records(config, records):
    return sync_jira_records(config, records, JiraBugRecord)


def sync_jira_requirement_records(config, records):
    return sync_jira_records(config, records, JiraRequirementRecord)


def clear_jira_records_for_version(record_model, version):
    queryset = record_model.objects.filter(version=normalize_jira_version(version))
    deleted_count = queryset.count()
    if deleted_count:
        queryset.delete()
    return deleted_count


def execute_jira_sync(config, record_model, success_label, profile):
    all_records = []
    total = None
    next_start = 0
    last_status_code = None
    last_columns = []
    config.jira_profile = profile
    session = _create_jira_session(config, profile)

    while total is None or next_start < total:
        request_kwargs = _build_execution_request(config, next_start, use_login_session=session is not None)
        response = _request_issue_table(request_kwargs, session=session)
        if _is_private_filter_400(response):
            retry_request_kwargs = _remove_filter_id_from_request(request_kwargs)
            response = _request_issue_table(retry_request_kwargs, session=session)
        last_status_code = response.status_code
        if response.status_code == 401:
            error = ValueError(_build_jira_auth_error_message(request_kwargs.get('headers'), profile, response))
            error.response = response
            raise error
        if response.status_code == 400:
            error = ValueError(f'{success_label}接口返回 400：{(getattr(response, "text", "") or "")[:1000]}')
            error.response = response
            raise error
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError('接口返回不是合法 JSON 数据') from exc

        parsed = parse_jira_issue_table_payload(payload, profile=profile)
        page_records = parsed['records']
        if total is None:
            total = parsed['total']
            last_columns = parsed['columns']

        if not page_records:
            break

        all_records.extend(page_records)
        candidate_next = parsed['end'] or (next_start + parsed['page_size'])
        if candidate_next <= next_start:
            break
        next_start = candidate_next

        if len(all_records) >= total:
            break

    preserved_map = capture_preserved_jira_fields(record_model, config.version)
    if profile == BUG_PROFILE and all_records:
        all_records = enrich_jira_bug_records(config, all_records, session=session)
    if profile == REQUIREMENT_PROFILE and all_records:
        all_records = enrich_jira_requirement_records(config, all_records, session=session)
    cleared_count = clear_jira_records_for_version(record_model, config.version)
    synced_count = sync_jira_records(config, all_records, record_model, preserved_map=preserved_map)
    if cleared_count:
        message = f'接口执行成功，已清空当前版本 {cleared_count} 条历史数据，并同步 {synced_count} 条{success_label}数据'
    else:
        message = f'接口执行成功，共同步 {synced_count} 条{success_label}数据'

    config.last_executed_at = timezone.now()
    config.last_status_code = last_status_code
    config.last_record_count = synced_count
    config.last_execution_message = message
    config.save(
        update_fields=[
            'last_executed_at',
            'last_status_code',
            'last_record_count',
            'last_execution_message',
            'updated_at',
        ]
    )

    return {
        'message': message,
        'status_code': last_status_code,
        'total': total or 0,
        'cleared_count': cleared_count,
        'synced_count': synced_count,
        'columns': last_columns,
    }


def execute_jira_config(config):
    return execute_jira_sync(config, JiraBugRecord, '线上BUG', BUG_PROFILE)


def execute_jira_requirement_config(config):
    return execute_jira_sync(config, JiraRequirementRecord, 'JIRA需求', REQUIREMENT_PROFILE)
