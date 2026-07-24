import re
import shlex
from urllib.parse import quote, urlsplit, urlunsplit


REMOTE_REPOSITORY_MODE = 'remote'
LOCAL_PATH_REPOSITORY_MODE = 'local_path'
DEFAULT_LOCAL_REPOSITORY_TEST_IMAGE = 'testhub/ai-dev:latest'
LOCAL_REPOSITORY_ABSOLUTE_PATH_MESSAGE = (
    '本地路径模式必须填写宿主机绝对路径，例如 D:\\repo\\project 或 /srv/git/project。'
)

WINDOWS_DRIVE_PATH_RE = re.compile(r'^[A-Za-z]:[\\/]')


def normalize_repository_mode(mode):
    return mode or REMOTE_REPOSITORY_MODE


def is_local_repository_mode(mode):
    return normalize_repository_mode(mode) == LOCAL_PATH_REPOSITORY_MODE


def is_remote_repository_mode(mode):
    return normalize_repository_mode(mode) == REMOTE_REPOSITORY_MODE


def is_http_repository_location(value):
    return bool(value) and value.startswith(('http://', 'https://'))


def normalize_local_repository_path(local_path):
    path = (local_path or '').strip().strip('"')
    if not path:
        return ''

    if WINDOWS_DRIVE_PATH_RE.match(path):
        normalized = re.sub(r'/+', '/', path.replace('\\', '/'))
        drive = normalized[0]
        remainder = normalized[2:].lstrip('/')
        return f'{drive}:/{remainder}' if remainder else f'{drive}:/'

    if path.startswith('/'):
        normalized = re.sub(r'/+', '/', path)
        return normalized.rstrip('/') or '/'

    return path


def is_supported_local_repository_path(local_path):
    path = normalize_local_repository_path(local_path)
    return bool(path) and (WINDOWS_DRIVE_PATH_RE.match(path) or path.startswith('/'))


def get_repository_location(repository_mode, repository_url, local_path):
    if is_local_repository_mode(repository_mode):
        return local_path or ''
    return repository_url or ''


def build_remote_repository_url(repository_url, username, password):
    if not repository_url:
        return ''
    if not username or not password:
        return repository_url

    parsed = urlsplit(repository_url)
    if not parsed.scheme or not parsed.netloc or '@' in parsed.netloc:
        return repository_url

    netloc = f'{quote(username, safe="")}:{quote(password, safe="")}@{parsed.netloc}'
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def translate_local_repository_path_for_docker(local_path):
    path = normalize_local_repository_path(local_path)
    if not path:
        return ''
    if path.startswith('/run/desktop/mnt/host/'):
        return path
    if WINDOWS_DRIVE_PATH_RE.match(path):
        drive = path[0].lower()
        remainder = path[2:].lstrip('/')
        return f'/run/desktop/mnt/host/{drive}/{remainder}'
    return path


def build_git_identity(username, fallback_username, fallback_email):
    resolved_username = (username or fallback_username or 'testhub-ai').strip() or 'testhub-ai'
    resolved_email = (fallback_email or '').strip()
    if not resolved_email:
        sanitized = re.sub(r'[^a-zA-Z0-9_.-]+', '-', resolved_username).strip('-') or 'testhub-ai'
        resolved_email = f'{sanitized}@local.testhub'
    return resolved_username, resolved_email


def inspect_local_repository(local_path, default_branch, docker_image=DEFAULT_LOCAL_REPOSITORY_TEST_IMAGE):
    import docker

    mount_source = translate_local_repository_path_for_docker(local_path)
    if not mount_source:
        return {
            'success': False,
            'message': '未提供本地 Git 仓库路径。',
            'branches': [],
        }

    branch_ref = shlex.quote(f'refs/heads/{default_branch}')
    command = '\n'.join(
        [
            'set -e',
            'git -C /repo rev-parse --is-inside-work-tree >/dev/null',
            f'git -C /repo show-ref --verify --quiet {branch_ref}',
            "git -C /repo for-each-ref --format='%(refname:short)' refs/heads | head -n 10",
        ]
    )

    client = docker.from_env()
    output = client.containers.run(
        image=docker_image,
        command=['bash', '-lc', command],
        remove=True,
        volumes={
            mount_source: {'bind': '/repo', 'mode': 'ro'},
        },
    )
    branches = [line.strip() for line in output.decode('utf-8', errors='ignore').splitlines() if line.strip()]
    return {
        'success': True,
        'message': '本地 Git 仓库校验成功',
        'branches': branches[:10],
        'docker_mount_source': mount_source,
    }
