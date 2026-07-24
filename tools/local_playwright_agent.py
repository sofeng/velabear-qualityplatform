#!/usr/bin/env python
"""Local TestHub Playwright recorder agent.

This agent pairs with a TestHub local-agent recording session, launches a local
Playwright browser, injects the platform recording script, and posts captured
steps back to TestHub.
"""

import argparse
import base64
import csv
import ctypes
import json
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from io import StringIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, urlunparse

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_SERVICE_HOST = '127.0.0.1'
DEFAULT_SERVICE_PORT = 18765
AGENT_VERSION = '0.4.1'
AGENT_STARTED_AT = time.time()
AGENT_SESSIONS = {}
AGENT_SESSIONS_LOCK = threading.Lock()
LOCALHOST_NAMES = {'localhost', '127.0.0.1', '::1', '0.0.0.0'}
VISUAL_FLOW_EVENT_PREFIX = '__TESTHUB_FLOW_EVENT__'
SYSTEM_CHROME_PATHS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
]
LOCAL_AGENT_PACKAGE_FILES = {
    'local_playwright_agent.py',
    'start_local_playwright_agent.ps1',
    'start_local_playwright_agent.bat',
    'stop_local_playwright_agent.ps1',
    'stop_local_playwright_agent.bat',
    'register_local_playwright_agent.ps1',
    'testhub_agent_protocol.ps1',
    'uninstall_local_playwright_agent.ps1',
    'install_local_playwright_agent.ps1',
    'install.ps1',
    'install.bat',
    'README.md',
}


def load_agent_config():
    install_dir_func = globals().get('agent_install_dir')
    install_dir = install_dir_func() if callable(install_dir_func) else os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(install_dir, 'agent_config.json')
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8-sig') as file_obj:
            data = json.load(file_obj)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def agent_install_dir():
    return os.path.dirname(os.path.abspath(__file__))


def safe_join_install_path(base_dir, relative_name):
    normalized = str(relative_name or '').replace('\\', '/').strip('/')
    if not normalized or normalized.startswith('../') or '/..' in normalized:
        raise ValueError(f'Invalid package entry: {relative_name}')
    if '/' in normalized:
        raise ValueError(f'Nested package entries are not supported: {relative_name}')
    target_path = os.path.abspath(os.path.join(base_dir, normalized))
    base_path = os.path.abspath(base_dir)
    if os.path.commonpath([base_path, target_path]) != base_path:
        raise ValueError(f'Package entry escapes install directory: {relative_name}')
    return target_path, normalized


def apply_agent_update(package_bytes, platform_url=''):
    if not package_bytes:
        raise ValueError('安装包为空')

    install_dir = agent_install_dir()
    updated_files = []

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_file.write(package_bytes)
        temp_path = temp_file.name

    try:
        with zipfile.ZipFile(temp_path) as archive:
            names = archive.namelist()
            if 'local_playwright_agent.py' not in names:
                raise ValueError('安装包缺少 local_playwright_agent.py')
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target_path, normalized = safe_join_install_path(install_dir, member.filename)
                if normalized not in LOCAL_AGENT_PACKAGE_FILES:
                    continue
                with archive.open(member) as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                updated_files.append(normalized)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    config = load_agent_config()
    if platform_url:
        config['platform_url'] = platform_url
    config['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime())
    config_path = os.path.join(install_dir, 'agent_config.json')
    with open(config_path, 'w', encoding='utf-8') as file_obj:
        json.dump(config, file_obj, ensure_ascii=False, indent=2)

    register_script = os.path.join(install_dir, 'register_local_playwright_agent.ps1')
    if is_windows() and os.path.exists(register_script):
        register_command = [
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            register_script,
            '-InstallDir',
            install_dir,
        ]
        python_path = str(config.get('python_path') or '').strip()
        if python_path:
            register_command.extend(['-Python', python_path])
        subprocess.run(
            register_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )

    return {
        'updated_files': updated_files,
        'install_dir': install_dir,
        'version': AGENT_VERSION,
    }


def restart_agent_service_soon(delay_seconds=1.0, platform_url=''):
    if not is_windows():
        return

    install_dir = agent_install_dir()
    install_script = os.path.join(install_dir, 'install_local_playwright_agent.ps1')
    start_script = os.path.join(install_dir, 'start_local_playwright_agent.ps1')
    if not os.path.exists(install_script) and not os.path.exists(start_script):
        return

    config = load_agent_config()
    python_path = str(config.get('python_path') or '').strip() or sys.executable
    platform_value = platform_url or str(config.get('platform_url') or '').strip()
    encoded_install_dir = base64.b64encode(install_dir.encode('utf-16-le')).decode('ascii')
    encoded_python = base64.b64encode(python_path.encode('utf-16-le')).decode('ascii')
    encoded_platform = base64.b64encode(platform_value.encode('utf-16-le')).decode('ascii')
    command = (
        f'Start-Sleep -Seconds {max(1, int(delay_seconds))}; '
        f'$deadline = (Get-Date).AddSeconds(15); '
        f'while ((Get-Date) -lt $deadline) {{ '
        f'try {{ Invoke-RestMethod -Uri "http://127.0.0.1:{DEFAULT_SERVICE_PORT}/health" -Method Get -TimeoutSec 1 | Out-Null; Start-Sleep -Seconds 1 }} '
        f'catch {{ break }} '
        f'}}; '
        f'$installDir = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String("{encoded_install_dir}")); '
        f'$python = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String("{encoded_python}")); '
        f'$platformUrl = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String("{encoded_platform}")); '
        f'$installer = Join-Path $installDir "install_local_playwright_agent.ps1"; '
        f'$starter = Join-Path $installDir "start_local_playwright_agent.ps1"; '
        f'if (Test-Path -LiteralPath $installer) {{ '
        f'  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $installer -InstallDir $installDir -Python $python -PlatformUrl $platformUrl '
        f'}} elseif (Test-Path -LiteralPath $starter) {{ '
        f'  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $starter -Python $python '
        f'}}'
    )
    subprocess.Popen(
        [
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-WindowStyle',
            'Hidden',
            '-Command',
            command,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def default_port_for_scheme(scheme):
    return 443 if str(scheme or '').lower() == 'https' else 80


def url_origin_tuple(url_value):
    parsed = urlparse(str(url_value or '').strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    return (
        parsed.scheme.lower(),
        (parsed.hostname or '').lower(),
        parsed.port or default_port_for_scheme(parsed.scheme),
    )


def same_url_origin(left, right):
    left_origin = url_origin_tuple(left)
    right_origin = url_origin_tuple(right)
    return bool(left_origin and right_origin and left_origin == right_origin)


def is_localhost_name(hostname):
    return (hostname or '').lower() in LOCALHOST_NAMES


def build_platform_api_origin(platform_url):
    value = str(platform_url or '').strip().rstrip('/')
    if not value:
        return ''
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return ''

    path = (parsed.path or '').rstrip('/')
    api_path = path if path == '/api' or path.endswith('/api') else f'{path}/api'
    if not api_path.startswith('/'):
        api_path = f'/{api_path}'
    return urlunparse((parsed.scheme, parsed.netloc, api_path, '', '', '')).rstrip('/')


def resolve_trusted_api_origin(payload, request_origin=''):
    config = load_agent_config()
    configured_platform_url = str(config.get('platform_url') or '').strip().rstrip('/')
    configured_api_origin = build_platform_api_origin(configured_platform_url)
    requested_api_origin = build_platform_api_origin(payload.get('api_origin') or '')

    if configured_api_origin:
        if request_origin and not same_url_origin(request_origin, configured_platform_url):
            raise PermissionError('请求来源与本地 Agent 绑定的平台不一致')
        if requested_api_origin and not same_url_origin(requested_api_origin, configured_api_origin):
            raise PermissionError('API 地址与本地 Agent 绑定的平台不一致')
        return configured_api_origin

    fallback_origin = requested_api_origin or build_platform_api_origin(request_origin)
    parsed = urlparse(fallback_origin)
    if not fallback_origin or not is_localhost_name(parsed.hostname):
        raise PermissionError('本地 Agent 尚未绑定当前平台，请从平台下载安装本地 Agent 后再执行')
    return fallback_origin


def get_configured_platform_url():
    config = load_agent_config()
    return str(config.get('platform_url') or '').strip().rstrip('/')


def origin_matches_platform_url(origin, platform_url):
    return bool(origin and platform_url and same_url_origin(origin, platform_url))


def validate_platform_access_token(api_origin, access_token):
    token = str(access_token or '').strip()
    if not token:
        raise PermissionError('缺少平台登录授权，无法执行本地脚本')

    headers = {'Authorization': f'Bearer {token}'}
    last_error = ''
    for path in ('auth/profile/', 'users/me/'):
        url = f'{api_origin.rstrip("/")}/{path}'
        try:
            response = requests.get(url, headers=headers, timeout=15)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                return {}
        if response.status_code in (401, 403):
            raise PermissionError('平台登录授权已失效，请重新登录后再执行')
        last_error = f'HTTP {response.status_code}'

    raise PermissionError(f'无法校验平台登录授权：{last_error or "未知错误"}')


def build_local_script_env(payload, verified_user=None):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    api_origin = str(payload.get('api_origin') or '').strip()
    if api_origin:
        env['TESTHUB_PLAYWRIGHT_API_ORIGIN'] = api_origin

    flow_variables = payload.get('flow_variables')
    if isinstance(flow_variables, dict):
        env['TESTHUB_FLOW_VARIABLES_JSON'] = json.dumps(flow_variables, ensure_ascii=False, default=str)

    access_token = str(payload.get('access_token') or '').strip()
    refresh_token = str(payload.get('refresh_token') or '').strip()
    token_expires_at = str(payload.get('token_expires_at') or '').strip()
    if access_token:
        env['TESTHUB_PLAYWRIGHT_ACCESS_TOKEN'] = access_token
    if refresh_token:
        env['TESTHUB_PLAYWRIGHT_REFRESH_TOKEN'] = refresh_token
    if token_expires_at:
        env['TESTHUB_PLAYWRIGHT_TOKEN_EXPIRES_AT'] = token_expires_at

    user_value = payload.get('user')
    if isinstance(user_value, (dict, list)):
        user_json = json.dumps(user_value, ensure_ascii=False, default=str)
    elif isinstance(user_value, str) and user_value.strip():
        user_json = user_value.strip()
    elif verified_user:
        user_json = json.dumps(verified_user, ensure_ascii=False, default=str)
    else:
        user_json = '{}'
    env['TESTHUB_PLAYWRIGHT_USER_JSON'] = user_json
    return env


def normalize_generated_script_content(script_content):
    # Older generated visual-flow scripts embed JavaScript regexes such as
    # /\s+/g inside normal Python triple-quoted strings. Python 3.12 warns on
    # that source form, so keep the JavaScript regex semantics while escaping
    # the Python source correctly.
    return str(script_content or '').replace('/\\s+/g', '/\\\\s+/g')


def extract_visual_flow_events(stdout):
    events = []
    clean_lines = []
    for line in str(stdout or '').splitlines():
        if line.startswith(VISUAL_FLOW_EVENT_PREFIX):
            raw_payload = line[len(VISUAL_FLOW_EVENT_PREFIX):].strip()
            try:
                payload = json.loads(raw_payload)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                events.append(payload)
            continue
        clean_lines.append(line)
    return events, '\n'.join(clean_lines).strip()


def post_visual_flow_execution_events(api_origin, access_token, execution_id, events):
    if not execution_id or not events:
        return
    url = f'{api_origin.rstrip("/")}/testcases/visual-flow-executions/{execution_id}/events/'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json={'events': events}, timeout=60)
    response.raise_for_status()


def finalize_visual_flow_execution(api_origin, access_token, execution_id, result):
    if not execution_id:
        return
    url = f'{api_origin.rstrip("/")}/testcases/visual-flow-executions/{execution_id}/finalize/'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {
        'success': bool(result.get('success')),
        'stdout': result.get('stdout') or '',
        'stderr': result.get('stderr') or '',
        'returncode': result.get('returncode'),
        'error': result.get('error') or '',
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()


def enqueue_process_stream(stream, output_queue):
    try:
        for line in iter(stream.readline, ''):
            if line:
                output_queue.put(line)
    except Exception as exc:
        output_queue.put(exc)
    finally:
        try:
            stream.close()
        except Exception:
            pass


def execute_local_playwright_script(payload, request_origin=''):
    if not isinstance(payload, dict):
        raise ValueError('Invalid JSON payload')

    script_content = payload.get('script')
    if not isinstance(script_content, str) or not script_content.strip():
        raise ValueError('script must be a non-empty string')
    script_content = normalize_generated_script_content(script_content)

    api_origin = resolve_trusted_api_origin(payload, request_origin=request_origin)
    verified_user = validate_platform_access_token(api_origin, payload.get('access_token'))

    script_id = str(uuid.uuid4())
    timeout_seconds = payload.get('timeout_seconds') or 300
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 300
    timeout_seconds = min(max(timeout_seconds, 10), 1800)

    fd, script_path = tempfile.mkstemp(prefix=f'testhub_local_{script_id}_', suffix='.py')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file_obj:
            file_obj.write(script_content)

        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=build_local_script_env(payload, verified_user=verified_user),
        )
        execution_id = str(payload.get('execution_id') or '').strip()
        stdout_lines = []
        stderr_lines = []
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        if process.stdout is not None:
            threading.Thread(target=enqueue_process_stream, args=(process.stdout, stdout_queue), daemon=True).start()
        if process.stderr is not None:
            threading.Thread(target=enqueue_process_stream, args=(process.stderr, stderr_queue), daemon=True).start()

        def drain_stdout_events():
            drained = False
            while True:
                try:
                    item = stdout_queue.get_nowait()
                except queue.Empty:
                    break
                drained = True
                if isinstance(item, Exception):
                    stderr_lines.append(str(item))
                    continue
                events, clean_stdout = extract_visual_flow_events(item)
                if execution_id and events:
                    try:
                        post_visual_flow_execution_events(api_origin, payload.get('access_token'), execution_id, events)
                    except Exception:
                        pass
                if clean_stdout:
                    stdout_lines.append(clean_stdout)
            return drained

        def drain_stderr_lines():
            drained = False
            while True:
                try:
                    item = stderr_queue.get_nowait()
                except queue.Empty:
                    break
                drained = True
                stderr_lines.append(str(item))
            return drained

        started = time.time()
        while True:
            drain_stdout_events()
            drain_stderr_lines()
            if process.poll() is not None:
                break
            if time.time() - started > timeout_seconds:
                process.kill()
                try:
                    process.wait(timeout=5)
                except Exception:
                    pass
                drain_stdout_events()
                drain_stderr_lines()
                raise subprocess.TimeoutExpired(
                    [sys.executable, script_path],
                    timeout_seconds,
                    output='\n'.join(stdout_lines),
                    stderr=''.join(stderr_lines),
                )
            time.sleep(0.1)

        drain_stdout_events()
        drain_stderr_lines()
        stderr_text = ''.join(stderr_lines)
        returncode = process.wait(timeout=5)
        response_payload = {
            'script_id': script_id,
            'success': returncode == 0,
            'stdout': '\n'.join(line for line in stdout_lines if line),
            'stderr': stderr_text,
            'returncode': returncode,
        }
        if execution_id:
            response_payload['execution_id'] = execution_id
            try:
                finalize_visual_flow_execution(api_origin, payload.get('access_token'), execution_id, response_payload)
            except Exception as exc:
                response_payload['execution_sync_error'] = str(exc)
        return response_payload
    except subprocess.TimeoutExpired as exc:
        response_payload = {
            'script_id': script_id,
            'success': False,
            'stdout': exc.stdout or '',
            'stderr': exc.stderr or f'脚本执行超时（超过 {timeout_seconds} 秒）',
            'returncode': -1,
        }
        execution_id = str(payload.get('execution_id') or '').strip()
        if execution_id:
            response_payload['execution_id'] = execution_id
            try:
                finalize_visual_flow_execution(api_origin, payload.get('access_token'), execution_id, response_payload)
            except Exception as sync_exc:
                response_payload['execution_sync_error'] = str(sync_exc)
        return response_payload
    finally:
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass


class RecordingStopped(RuntimeError):
    """Raised when TestHub reports that the recording session is already closed."""


def is_windows():
    return platform.system().lower() == 'windows'


def parse_args():
    parser = argparse.ArgumentParser(description='TestHub local Playwright recording agent')
    parser.add_argument('--pairing-url', default='', help='Pairing URL from TestHub')
    parser.add_argument('--token', default='', help='Short-lived pairing token from TestHub')
    parser.add_argument('--browser', default='', help='Override browser type: chromium, firefox, webkit')
    parser.add_argument('--headless', action='store_true', help='Run the browser headless')
    parser.add_argument(
        '--serve',
        action='store_true',
        help='Run a local HTTP service so TestHub frontend can start recordings automatically',
    )
    parser.add_argument('--host', default=DEFAULT_SERVICE_HOST, help='Local service host')
    parser.add_argument('--port', type=int, default=DEFAULT_SERVICE_PORT, help='Local service port')
    args = parser.parse_args()
    if not args.serve and (not args.pairing_url or not args.token):
        parser.error('--pairing-url and --token are required unless --serve is used')
    return args


def request_headers(token):
    return {'X-TestHub-Agent-Token': token}


def pair_session(pairing_url, token):
    response = requests.get(pairing_url, headers=request_headers(token), timeout=20)
    response.raise_for_status()
    return response.json()


def is_frame_detached(frame):
    try:
        is_detached = getattr(frame, 'is_detached', None)
        return bool(is_detached()) if callable(is_detached) else False
    except Exception:
        return True


def drain_frame_events(frame, flush_pending=False):
    try:
        events = frame.evaluate(
            """flushPending => window.__testhub_recording_drainEvents
                ? window.__testhub_recording_drainEvents(Boolean(flushPending))
                : []""",
            flush_pending,
        )
        return events if isinstance(events, list) else []
    except Exception:
        return []


def drain_page_events(page, flush_pending=False):
    if page.is_closed():
        return []

    drained = []
    for frame in list(page.frames):
        if page.is_closed() or is_frame_detached(frame):
            continue
        for event in drain_frame_events(frame, flush_pending=flush_pending):
            if isinstance(event, dict):
                drained.append((frame, event))
    return drained


def is_main_frame(page, frame):
    try:
        return frame == page.main_frame
    except Exception:
        return False


def safe_page_url(page, event=None):
    event = event if isinstance(event, dict) else {}
    event_url = event.get('url') or ''
    if event_url:
        return event_url
    try:
        return page.url or ''
    except Exception:
        return ''


def safe_page_title(page, event=None):
    event = event if isinstance(event, dict) else {}
    event_title = event.get('title') or ''
    if event_title:
        return event_title
    try:
        return page.title()
    except Exception:
        return ''


def attach_frame_runtime_data(page, frame, event):
    if not isinstance(event, dict) or frame is None:
        return event

    frame_payload = event.get('frame') if isinstance(event.get('frame'), dict) else {}
    is_main = is_main_frame(page, frame)
    frame_url = frame_payload.get('url') or event.get('url') or ''
    if not frame_url:
        try:
            frame_url = frame.url or ''
        except Exception:
            frame_url = ''
    try:
        frame_name = frame.name or frame_payload.get('name') or ''
    except Exception:
        frame_name = frame_payload.get('name') or ''
    try:
        parent_frame = frame.parent_frame
        parent_url = parent_frame.url if parent_frame else ''
    except Exception:
        parent_url = ''

    frame_payload.update({
        'url': frame_url,
        'name': frame_name,
        'isMain': is_main,
        'parentUrl': parent_url,
    })
    event['frame'] = frame_payload
    event['frame_url'] = frame_url
    event['frame_name'] = frame_name
    event['frame_is_main'] = is_main
    event['is_iframe_event'] = not is_main
    return event


def capture_snapshot(page, frame=None, snapshot_script=''):
    snapshot_target = frame or page
    try:
        locator = snapshot_target.locator('body')
        aria_snapshot = getattr(locator, 'aria_snapshot', None)
        if callable(aria_snapshot):
            content = aria_snapshot(timeout=2500)
            if isinstance(content, str) and content.strip():
                return content
    except Exception:
        pass
    if snapshot_script:
        try:
            content = snapshot_target.evaluate(snapshot_script)
            if isinstance(content, str) and content.strip():
                return content
        except Exception:
            pass
    return ''


def capture_screenshot_base64(page):
    try:
        data = page.screenshot(full_page=True, timeout=4000)
        return base64.b64encode(data).decode('ascii')
    except Exception:
        return ''


def post_step(submit_url, token, page, event, snapshot_script='', frame=None):
    event = attach_frame_runtime_data(page, frame, event)
    payload = {
        'event': event,
        'page_url': safe_page_url(page, event=event),
        'page_title': safe_page_title(page, event=event),
        'snapshot_content': capture_snapshot(page, frame=frame, snapshot_script=snapshot_script),
        'screenshot_base64': capture_screenshot_base64(page),
    }
    last_error = None
    for attempt in range(1, 5):
        try:
            response = requests.post(submit_url, headers=request_headers(token), json=payload, timeout=60)
            if response.status_code == 409:
                raise RecordingStopped(response.text or 'Recording session has already stopped')
            if response.status_code < 500:
                response.raise_for_status()
                return
            last_error = requests.HTTPError(f'{response.status_code} Server Error for url: {submit_url}')
        except RecordingStopped:
            raise
        except requests.RequestException as exc:
            last_error = exc
        if attempt < 4:
            time.sleep(min(8, 2 ** attempt))
    if last_error:
        raise last_error


def stop_session(stop_url, token):
    try:
        requests.post(stop_url, headers=request_headers(token), json={}, timeout=20).raise_for_status()
    except Exception as exc:
        print(f'Failed to notify TestHub stop endpoint: {exc}', file=sys.stderr)


def is_remote_stop_requested(status_url, token):
    if not status_url:
        return False
    try:
        response = requests.get(status_url, headers=request_headers(token), timeout=10)
        if response.status_code == 404:
            return True
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get('stop_requested')) or payload.get('status') in ('completed', 'failed')
    except Exception as exc:
        print(f'Failed to poll TestHub recording status: {exc}', file=sys.stderr)
        return False


def find_system_chrome():
    for path in SYSTEM_CHROME_PATHS:
        if os.path.exists(path):
            return path
    for executable in ('chrome.exe', 'chrome'):
        path = shutil.which(executable)
        if path:
            return path
    return ''


def list_browser_process_ids():
    if not is_windows():
        return set()
    process_ids = set()
    for image_name in ('chrome.exe', 'msedge.exe'):
        try:
            output = subprocess.check_output(
                ['tasklist', '/FI', f'IMAGENAME eq {image_name}', '/FO', 'CSV', '/NH'],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except Exception:
            continue
        for row in csv.reader(StringIO(output)):
            if len(row) < 2 or row[0].upper().startswith('INFO:'):
                continue
            try:
                process_ids.add(int(row[1]))
            except (TypeError, ValueError):
                continue
    return process_ids


def bring_windows_browser_to_front(process_ids=None, title_hint=''):
    if not is_windows():
        return False
    target_process_ids = set(process_ids or [])
    normalized_hint = str(title_hint or '').strip().casefold()
    user32 = ctypes.windll.user32
    hwnd_matches = []

    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def collect_window(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value or ''
        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        pid = int(process_id.value)
        if target_process_ids and pid not in target_process_ids:
            return True
        if normalized_hint and normalized_hint not in title.casefold():
            hwnd_matches.append((1, hwnd, title))
        else:
            hwnd_matches.append((0, hwnd, title))
        return True

    try:
        user32.EnumWindows(enum_windows_proc(collect_window), 0)
    except Exception:
        return False
    if not hwnd_matches:
        return False

    hwnd_matches.sort(key=lambda item: item[0])
    hwnd = hwnd_matches[0][1]
    try:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        return True
    except Exception:
        return False


def find_free_local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def parse_payload_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return default


def parse_payload_int(value, default, minimum=1, maximum=10000):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    return min(max(parsed, minimum), maximum)


def build_launch_options(browser_type, headless=False, cdp_port=0, maximize=True, viewport_width=1440, viewport_height=1000):
    options = {
        'headless': headless,
    }
    args = []
    if browser_type == 'chromium' and cdp_port:
        args.extend([
            '--remote-debugging-address=127.0.0.1',
            f'--remote-debugging-port={cdp_port}',
        ])
    if headless:
        if args:
            options['args'] = args
        return options

    if maximize:
        args.extend([
            '--start-maximized',
            '--window-position=0,0',
        ])
    else:
        args.extend([
            '--window-position=80,80',
            f'--window-size={int(viewport_width)},{int(viewport_height)}',
        ])
    options['args'] = args
    if browser_type == 'chromium' and platform.system().lower() == 'windows':
        chrome_path = find_system_chrome()
        if chrome_path:
            options['executable_path'] = chrome_path
            print(f'Using system Chrome for local recording: {chrome_path}')
        else:
            print('System Chrome was not found; falling back to Playwright bundled Chromium.', file=sys.stderr)
    return options


def apply_chromium_window_geometry(context, page, maximize=True, viewport_width=1440, viewport_height=1000):
    geometry = {
        'maximize': bool(maximize),
        'requested_width': int(viewport_width),
        'requested_height': int(viewport_height),
    }
    try:
        cdp_session = context.new_cdp_session(page)
        window_info = cdp_session.send('Browser.getWindowForTarget')
        window_id = window_info.get('windowId')
        if not window_id:
            return geometry
        if maximize:
            cdp_session.send('Browser.setWindowBounds', {
                'windowId': window_id,
                'bounds': {'windowState': 'maximized'},
            })
        else:
            try:
                cdp_session.send('Browser.setWindowBounds', {
                    'windowId': window_id,
                    'bounds': {'windowState': 'normal'},
                })
            except Exception:
                pass
            cdp_session.send('Browser.setWindowBounds', {
                'windowId': window_id,
                'bounds': {
                    'left': 80,
                    'top': 80,
                    'width': int(viewport_width),
                    'height': int(viewport_height),
                },
            })
            try:
                page.set_viewport_size({'width': int(viewport_width), 'height': int(viewport_height)})
            except Exception as exc:
                geometry['viewport_resize_warning'] = str(exc)
        try:
            current_bounds = cdp_session.send('Browser.getWindowBounds', {'windowId': window_id})
            if isinstance(current_bounds, dict):
                geometry['window_bounds'] = current_bounds.get('bounds') or current_bounds
        except Exception:
            pass
    except Exception as exc:
        geometry['error'] = str(exc)
    return geometry


def bring_page_to_front(page):
    try:
        page.bring_to_front()
    except Exception:
        pass


def bring_recording_browser_to_front(page, browser_process_ids=None):
    bring_page_to_front(page)
    title_hint = ''
    try:
        title_hint = page.title()
    except Exception:
        title_hint = ''
    for _ in range(10):
        if bring_windows_browser_to_front(browser_process_ids, title_hint=title_hint):
            return True
        time.sleep(0.2)
    return False


def run_replay_script(replay_script, cdp_url, payload=None):
    script_content = normalize_generated_script_content(replay_script)
    if not script_content.strip():
        return
    if not cdp_url:
        raise RuntimeError('CDP URL is required for replay')

    payload = payload if isinstance(payload, dict) else {}
    script_id = str(uuid.uuid4())
    timeout_seconds = payload.get('replay_timeout_seconds') or payload.get('timeout_seconds') or 300
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 300
    timeout_seconds = min(max(timeout_seconds, 10), 1800)

    fd, script_path = tempfile.mkstemp(prefix=f'testhub_replay_{script_id}_', suffix='.py')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file_obj:
            file_obj.write(script_content)

        env = build_local_script_env(payload)
        env['TESTHUB_REPLAY_CDP_URL'] = cdp_url
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            timeout=timeout_seconds,
        )
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        if result.returncode != 0:
            message = (result.stderr or result.stdout or f'Replay script exited with {result.returncode}').strip()
            raise RuntimeError(message)
    except subprocess.TimeoutExpired as exc:
        message = exc.stderr or exc.stdout or f'Replay script timed out after {timeout_seconds} seconds'
        raise RuntimeError(str(message).strip())
    finally:
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass


def install_recording_script_on_existing_context(context, recording_script):
    context.add_init_script(recording_script)
    for current_page in list(context.pages):
        if current_page.is_closed():
            continue
        for frame in list(current_page.frames):
            if current_page.is_closed() or is_frame_detached(frame):
                continue
            try:
                frame.evaluate(recording_script)
            except Exception:
                pass
        drain_page_events(current_page, flush_pending=True)


class RecordingState:
    def __init__(self, request_id):
        self.request_id = request_id
        self.status = 'starting'
        self.session_id = ''
        self.browser_type = ''
        self.target_url = ''
        self.cdp_url = ''
        self.error = ''
        self.started_at = time.time()
        self.updated_at = self.started_at
        self.ready = threading.Event()
        self.done = threading.Event()
        self.lock = threading.Lock()

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.updated_at = time.time()

    def to_dict(self):
        with self.lock:
            return {
                'request_id': self.request_id,
                'status': self.status,
                'session_id': self.session_id,
                'browser_type': self.browser_type,
                'target_url': self.target_url,
                'cdp_url': self.cdp_url,
                'error': self.error,
                'started_at': self.started_at,
                'updated_at': self.updated_at,
            }


def run_recording(
    pairing_url,
    token,
    browser_override='',
    headless=False,
    state=None,
    replay_script='',
    replay_payload=None,
    record_replay_events=True,
):
    if state:
        state.update(status='pairing')
    session = pair_session(pairing_url, token)
    browser_type = browser_override or session.get('browser_type') or 'chromium'
    target_url = session.get('target_url') or 'about:blank'
    submit_url = session.get('submit_url')
    status_url = session.get('status_url')
    stop_url = session.get('stop_url')
    recording_script = session.get('recording_script') or ''
    dom_snapshot_script = session.get('dom_snapshot_script') or ''
    poll_interval = max(int(session.get('poll_interval_ms') or 600), 100) / 1000

    if not submit_url or not stop_url or not recording_script:
        raise RuntimeError('Pairing payload is incomplete')

    replay_script = str(replay_script or '')
    replay_payload = replay_payload if isinstance(replay_payload, dict) else {}
    maximize = parse_payload_bool(replay_payload.get('maximize'), default=True)
    viewport_width = parse_payload_int(replay_payload.get('viewport_width'), 1440, minimum=800, maximum=3840)
    viewport_height = parse_payload_int(replay_payload.get('viewport_height'), 1000, minimum=600, maximum=2160)
    if replay_script and browser_type != 'chromium':
        browser_type = 'chromium'

    cdp_port = find_free_local_port() if browser_type == 'chromium' else 0
    cdp_url = f'http://127.0.0.1:{cdp_port}' if cdp_port else ''
    if state:
        state.update(
            status='launching',
            session_id=session.get('session_id') or '',
            browser_type=browser_type,
            target_url=target_url,
            cdp_url=cdp_url,
        )

    print(f'Paired TestHub session {session.get("session_id")}. Launching {browser_type}...')
    try:
        with sync_playwright() as playwright:
            if browser_type not in ('chromium', 'firefox', 'webkit'):
                raise RuntimeError(f'Unsupported browser type: {browser_type}')
            launcher = getattr(playwright, browser_type)
            existing_browser_process_ids = list_browser_process_ids()
            browser = launcher.launch(**build_launch_options(
                browser_type,
                headless=headless,
                cdp_port=cdp_port,
                maximize=maximize,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
            ))
            context = browser.new_context(ignore_https_errors=True, no_viewport=True)
            if record_replay_events or not replay_script:
                context.add_init_script(recording_script)
            page = context.new_page()
            if browser_type == 'chromium' and not headless:
                geometry = apply_chromium_window_geometry(
                    context,
                    page,
                    maximize=maximize,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                )
                if geometry.get('error'):
                    print(f'Could not apply local browser geometry: {geometry.get("error")}', file=sys.stderr)

            if replay_script:
                if not cdp_url:
                    raise RuntimeError('Replay recording requires Chromium CDP')
                if state:
                    state.update(status='replaying')
                print('Replaying visual flow before continuing recording...')
                run_replay_script(replay_script, cdp_url, replay_payload)
                if not record_replay_events:
                    install_recording_script_on_existing_context(context, recording_script)
            else:
                if state:
                    state.update(status='recording')
                    state.ready.set()
                try:
                    page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                except PlaywrightTimeoutError:
                    print('Initial navigation timed out; keeping browser open for manual operation.', file=sys.stderr)
                except Exception as exc:
                    print(f'Initial navigation failed: {exc}', file=sys.stderr)

            browser_process_ids = list_browser_process_ids() - existing_browser_process_ids
            active_page = context.pages[-1] if context.pages else page
            bring_recording_browser_to_front(active_page, browser_process_ids=browser_process_ids)
            if state:
                state.update(status='recording')
                state.ready.set()

            try:
                while browser.is_connected():
                    if is_remote_stop_requested(status_url, token):
                        print('TestHub recording stop requested; closing local browser.')
                        break
                    for current_page in list(context.pages):
                        if current_page.is_closed():
                            continue
                        for frame, event in drain_page_events(current_page):
                            if isinstance(event, dict):
                                post_step(
                                    submit_url,
                                    token,
                                    current_page,
                                    event,
                                    snapshot_script=dom_snapshot_script,
                                    frame=frame,
                                )
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                print('Stopping local recording...')
            except RecordingStopped as exc:
                print(f'TestHub recording session is already stopped: {exc}', file=sys.stderr)
            finally:
                for current_page in list(context.pages):
                    if current_page.is_closed():
                        continue
                    try:
                        for frame, event in drain_page_events(current_page, flush_pending=True):
                            if isinstance(event, dict):
                                post_step(
                                    submit_url,
                                    token,
                                    current_page,
                                    event,
                                    snapshot_script=dom_snapshot_script,
                                    frame=frame,
                                )
                    except RecordingStopped:
                        break
                stop_session(stop_url, token)
                browser.close()
        if state:
            state.update(status='completed')
    except Exception as exc:
        if state:
            state.update(status='failed', error=str(exc))
            state.ready.set()
        raise
    finally:
        if state:
            state.done.set()


def run_recording_worker(
    state,
    pairing_url,
    token,
    browser_override='',
    headless=False,
    replay_script='',
    replay_payload=None,
    record_replay_events=True,
):
    try:
        run_recording(
            pairing_url,
            token,
            browser_override=browser_override,
            headless=headless,
            state=state,
            replay_script=replay_script,
            replay_payload=replay_payload,
            record_replay_events=record_replay_events,
        )
    except Exception as exc:
        print(f'Local recording failed: {exc}', file=sys.stderr)


class LocalAgentHandler(BaseHTTPRequestHandler):
    server_version = 'TestHubLocalAgent/1.0'

    def log_message(self, fmt, *args):
        print(f'{self.address_string()} - {fmt % args}')

    def send_cors_headers(self):
        origin = self.headers.get('Origin') or '*'
        request_headers = self.headers.get('Access-Control-Request-Headers')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', request_headers or 'content-type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Vary', 'Origin, Access-Control-Request-Headers, Access-Control-Request-Method')

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_cors_headers()
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def read_json_payload(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
            raw_body = self.rfile.read(length).decode('utf-8') if length else '{}'
            return json.loads(raw_body or '{}')
        except (ValueError, json.JSONDecodeError):
            return None

    def read_binary_payload(self, max_bytes=20 * 1024 * 1024):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            raise ValueError('请求体为空')
        if length > max_bytes:
            raise ValueError('安装包过大')
        return self.rfile.read(length)

    def build_health_payload(self):
        with AGENT_SESSIONS_LOCK:
            sessions = [state.to_dict() for state in AGENT_SESSIONS.values()]
        host, port = self.server.server_address
        configured_platform_url = get_configured_platform_url()
        return {
            'status': 'ok',
            'service': 'testhub-local-playwright-agent',
            'version': AGENT_VERSION,
            'pid': os.getpid(),
            'host': host,
            'port': port,
            'platform': platform.platform(),
            'python': sys.version.split()[0],
            'configured_platform_url': configured_platform_url,
            'platform_bound': bool(configured_platform_url),
            'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(AGENT_STARTED_AT)),
            'uptime_seconds': max(0, int(time.time() - AGENT_STARTED_AT)),
            'sessions': sessions,
        }

    def is_loopback_client(self):
        host = str((self.client_address or ('', 0))[0] or '').strip().lower()
        return host in {'127.0.0.1', 'localhost', '::1'} or host.startswith('127.')

    def is_allowed_local_origin(self):
        origin = str(self.headers.get('Origin') or '').strip()
        if not origin:
            return True
        try:
            host = (urlparse(origin).hostname or '').strip().lower()
        except Exception:
            return False
        if host in {'localhost', '127.0.0.1', '::1', 'host.docker.internal'} or host.startswith('127.'):
            return True
        config = load_agent_config()
        configured_platform_url = str(config.get('platform_url') or '').strip()
        return bool(configured_platform_url and same_url_origin(origin, configured_platform_url))

    def is_allowed_agent_update_origin(self, platform_url=''):
        if self.is_allowed_local_origin():
            return True

        origin = str(self.headers.get('Origin') or '').strip()
        configured_platform_url = get_configured_platform_url()
        if configured_platform_url:
            return False
        return origin_matches_platform_url(origin, platform_url)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path != '/health':
            self.send_json(404, {'error': 'Not found'})
            return
        self.send_json(200, self.build_health_payload())

    def do_POST(self):
        path = urlparse(self.path).path
        if path in ('/shutdown', '/stop-service'):
            if not self.is_loopback_client() or not self.is_allowed_local_origin():
                self.send_json(403, {'error': 'Shutdown is only allowed from the local machine'})
                return
            self.send_json(200, {
                'message': 'TestHub local Playwright agent service is stopping',
                'service': 'testhub-local-playwright-agent',
            })
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if path == '/update':
            platform_url = self.headers.get('X-TestHub-Platform-Url') or ''
            if not self.is_loopback_client() or not self.is_allowed_agent_update_origin(platform_url):
                self.send_json(403, {'error': 'Update is only allowed from the local machine'})
                return
            try:
                package_bytes = self.read_binary_payload()
                result = apply_agent_update(
                    package_bytes,
                    platform_url=platform_url,
                )
            except ValueError as exc:
                self.send_json(400, {'error': str(exc)})
                return
            except Exception as exc:
                self.send_json(500, {'error': f'本地 Agent 升级失败: {exc}'})
                return

            self.send_json(200, {
                'message': '本地 Agent 已更新，服务将自动重启',
                **result,
            })
            restart_agent_service_soon(platform_url=platform_url)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if path == '/scripts/execute':
            payload = self.read_json_payload()
            if payload is None:
                self.send_json(400, {'error': 'Invalid JSON payload'})
                return
            try:
                result = execute_local_playwright_script(
                    payload,
                    request_origin=self.headers.get('Origin') or '',
                )
            except PermissionError as exc:
                self.send_json(403, {'error': str(exc)})
                return
            except ValueError as exc:
                self.send_json(400, {'error': str(exc)})
                return
            except Exception as exc:
                self.send_json(500, {'error': f'本地脚本执行失败: {exc}'})
                return
            self.send_json(200, result)
            return

        if path not in ('/recordings/start', '/start'):
            self.send_json(404, {'error': 'Not found'})
            return

        payload = self.read_json_payload()
        if payload is None:
            self.send_json(400, {'error': 'Invalid JSON payload'})
            return

        pairing_url = str(payload.get('pairing_url') or '').strip()
        token = str(payload.get('token') or '').strip()
        browser = str(payload.get('browser') or '').strip()
        headless = bool(payload.get('headless') or False)
        replay_script = str(payload.get('replay_script') or '')
        record_replay_events = payload.get('record_replay_events')
        record_replay_events = True if record_replay_events is None else bool(record_replay_events)
        if not pairing_url or not token:
            self.send_json(400, {'error': 'pairing_url and token are required'})
            return

        state = RecordingState(uuid.uuid4().hex[:12])
        with AGENT_SESSIONS_LOCK:
            AGENT_SESSIONS[state.request_id] = state

        thread = threading.Thread(
            target=run_recording_worker,
            args=(state, pairing_url, token, browser, headless, replay_script, payload, record_replay_events),
            daemon=True,
        )
        thread.start()
        state.ready.wait(timeout=240 if replay_script else 30)
        state_payload = state.to_dict()
        if state_payload['status'] == 'failed':
            self.send_json(500, {
                'error': state_payload['error'] or 'Failed to launch local browser',
                'recording': state_payload,
            })
            return
        if state_payload['status'] != 'recording':
            self.send_json(202, {
                'error': 'Local Playwright browser is not ready yet',
                'recording': state_payload,
            })
            return
        self.send_json(200 if state_payload['status'] == 'recording' else 202, {
            'message': 'Local Playwright browser is recording',
            'recording': state_payload,
        })


def serve_local_agent(host, port):
    server = ThreadingHTTPServer((host, port), LocalAgentHandler)
    print(f'TestHub local Playwright agent service listening on http://{host}:{port}')
    print('Keep this process running while using local Agent recording.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping TestHub local Playwright agent service...')
    finally:
        server.server_close()


def main():
    args = parse_args()
    if args.serve:
        serve_local_agent(args.host, args.port)
        return
    run_recording(
        args.pairing_url,
        args.token,
        browser_override=args.browser,
        headless=args.headless,
    )


if __name__ == '__main__':
    main()
