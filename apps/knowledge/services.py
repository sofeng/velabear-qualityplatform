import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import pymysql
from django.apps import apps as django_apps
from django.conf import settings
from django.db import connections, transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from apps.knowledge.repository_support import (
    LOCAL_PATH_REPOSITORY_MODE,
    REMOTE_REPOSITORY_MODE,
    normalize_local_repository_path,
)
from apps.core.branding import PLATFORM_BRAND_NAME
from apps.core.plaintext_secrets import decrypt_password
from apps.projects.models import Project

from .models import (
    KnowledgeIndexRun,
    KnowledgeObject,
    KnowledgeQueryTrace,
    KnowledgeRelation,
    KnowledgeRepositoryConfig,
    KnowledgeSpace,
)
from .asset_scanner import scan_code_assets, scan_database_assets


MANUAL_QUALITY_SPACE_KEY = 'manual_quality'
MANUAL_QUALITY_NAME = '思源质量知识库'
DEFAULT_SOURCE_REPO_CANDIDATES = [
    os.environ.get('BEARAI_SOURCE_REPO_DIR', ''),
    os.environ.get('TESTHUB_SOURCE_REPO_DIR', ''),
    '/workspace/source-repo',
]
EXCLUDED_SCAN_DIRS = {
    '.git',
    'node_modules',
    'dist',
    'build',
    '.venv',
    'venv',
    '__pycache__',
    '.docker-data',
    'media',
    'static',
}


def get_queryset_for_user(queryset, user):
    if user and (user.is_superuser or user.is_staff):
        return queryset
    if queryset.model is KnowledgeSpace:
        return queryset.filter(Q(owner=user) | Q(project__owner=user) | Q(project__members=user)).distinct()
    if queryset.model is KnowledgeRepositoryConfig:
        return queryset.filter(Q(created_by=user) | Q(project__owner=user) | Q(project__members=user)).distinct()
    if queryset.model in (KnowledgeObject, KnowledgeQueryTrace):
        return queryset.filter(Q(project__owner=user) | Q(project__members=user) | Q(space__owner=user) | Q(space__project__owner=user) | Q(space__project__members=user)).distinct()
    if queryset.model is KnowledgeIndexRun:
        return queryset.filter(Q(created_by=user) | Q(space__owner=user) | Q(space__project__owner=user) | Q(space__project__members=user) | Q(repository_config__created_by=user)).distinct()
    return queryset


def ensure_default_knowledge_space(user=None, project=None, key=None, name=None):
    normalized_key = str(key or '').strip()
    if not normalized_key:
        normalized_key = f'project_{project.id}_knowledge' if project else MANUAL_QUALITY_SPACE_KEY
    normalized_name = str(name or '').strip()
    if not normalized_name:
        normalized_name = f'{project.name}知识库' if project else MANUAL_QUALITY_NAME
    space_type = 'project' if project else 'module'
    space, created = KnowledgeSpace.objects.get_or_create(
        key=normalized_key,
        defaults={
            'name': normalized_name,
            'description': '由平台仓库、roadmap、页面、接口和数据库表自动生成的知识库对象。',
            'space_type': space_type,
            'project': project,
            'owner': user if getattr(user, 'is_authenticated', False) else None,
            'metadata': {
                'seed': 'default',
                'roadmap_scope': 'menu-page-tab-function-operation-field-api-table',
            },
            'build_status': 'pending_config',
            'build_status_message': 'Knowledge object created. Configure Git repository and database schema, then run indexing.',
        },
    )
    changed = False
    if project and space.project_id != project.id:
        space.project = project
        changed = True
    if user and getattr(user, 'is_authenticated', False) and not space.owner_id:
        space.owner = user
        changed = True
    if not space.name:
        space.name = normalized_name
        changed = True
    if changed:
        space.save(update_fields=['project', 'owner', 'name', 'updated_at'])
    return space


def ensure_repository_space(config, user=None):
    if config.space_id:
        return config.space
    space = ensure_default_knowledge_space(user=user or config.created_by, project=config.project)
    config.space = space
    config.save(update_fields=['space', 'updated_at'])
    return space


def ensure_project_knowledge_space(project, user=None):
    return ensure_default_knowledge_space(user=user or getattr(project, 'owner', None), project=project)


def set_space_build_status(space, status, message='', *, last_indexed_at=None):
    if not space:
        return
    space.build_status = status
    space.build_status_message = str(message or '')[:500]
    update_fields = ['build_status', 'build_status_message', 'updated_at']
    if last_indexed_at is not None:
        space.last_indexed_at = last_indexed_at
        update_fields.append('last_indexed_at')
    space.save(update_fields=update_fields)


def is_repository_config_ready(config):
    if not config or not config.is_active:
        return False
    if config.repository_mode == LOCAL_PATH_REPOSITORY_MODE:
        repository_ready = bool(str(config.local_path or '').strip())
    else:
        repository_ready = bool(str(config.repository_url or '').strip()) and (
            config.auth_mode in {'none', 'ssh'} or
            bool(config.access_token_encrypted) or
            config.authorization_status == 'authorized'
        )
    if not repository_ready:
        return False
    if config.database_engine == 'mysql':
        return bool(config.database_host and config.database_name and config.database_username)
    return True


def get_current_database_schema_config():
    default = connections.databases.get('default') or {}
    engine = default.get('ENGINE') or ''
    if 'mysql' not in engine.lower():
        return None
    return {
        'engine': 'current',
        'host': default.get('HOST') or '127.0.0.1',
        'port': str(default.get('PORT') or '3306'),
        'name': default.get('NAME') or '',
        'schema': default.get('NAME') or '',
        'user': default.get('USER') or '',
        'password': default.get('PASSWORD') or '',
    }


def get_repository_database_schema_config(config):
    if config.database_engine == 'none':
        return None
    if config.database_engine == 'current':
        return get_current_database_schema_config()
    if config.database_engine == 'mysql':
        return {
            'engine': 'mysql',
            'host': config.database_host,
            'port': config.database_port or '3306',
            'name': config.database_name,
            'schema': config.database_schema or config.database_name,
            'user': config.database_username,
            'password': decrypt_password(config.database_password_encrypted) if config.database_password_encrypted else '',
        }
    return None


def compile_name_patterns(values):
    patterns = []
    for value in values or []:
        text = str(value or '').strip()
        if not text:
            continue
        regex = '^' + re.escape(text).replace('\\*', '.*') + '$'
        patterns.append(re.compile(regex, re.IGNORECASE))
    return patterns


def is_name_allowed_by_patterns(name, include_patterns=None, exclude_patterns=None):
    normalized = str(name or '').strip()
    if not normalized:
        return False
    include = compile_name_patterns(include_patterns)
    exclude = compile_name_patterns(exclude_patterns)
    if include and not any(pattern.search(normalized) for pattern in include):
        return False
    if exclude and any(pattern.search(normalized) for pattern in exclude):
        return False
    return True


def test_database_schema_connection(config):
    schema_config = get_repository_database_schema_config(config)
    if not schema_config:
        return {
            'success': True,
            'message': 'Database schema indexing is disabled.',
            'tables': [],
            'table_count': 0,
        }, 200
    try:
        connection = pymysql.connect(
            host=schema_config['host'],
            port=int(schema_config['port'] or 3306),
            user=schema_config['user'],
            password=schema_config['password'],
            database=schema_config['name'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=8,
            read_timeout=12,
            write_timeout=12,
        )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT TABLE_NAME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    LIMIT 50
                    """,
                    [schema_config.get('schema') or schema_config['name']],
                )
                rows = cursor.fetchall()
        table_names = [
            row['TABLE_NAME']
            for row in rows
            if is_name_allowed_by_patterns(
                row.get('TABLE_NAME'),
                config.database_include_patterns,
                config.database_exclude_patterns,
            )
        ]
        return {
            'success': True,
            'message': 'Database schema connection succeeded.',
            'tables': table_names[:30],
            'table_count': len(table_names),
            'database_name': schema_config['name'],
            'database_schema': schema_config.get('schema') or schema_config['name'],
        }, 200
    except Exception as exc:
        return {
            'success': False,
            'message': f'Database schema connection failed: {exc}',
            'tables': [],
            'table_count': 0,
        }, 400


def dispatch_repository_index(config, user=None, trigger='auto_ready'):
    if not config or not is_repository_config_ready(config):
        space = ensure_repository_space(config, user=user) if config else None
        message = 'Repository or database configuration is incomplete.'
        if space:
            set_space_build_status(space, 'pending_config', message)
        return {'queued': False, 'status': 'pending_config', 'error': message}
    space = ensure_repository_space(config, user=user)
    set_space_build_status(space, 'queued', 'Knowledge object indexing has been queued.')
    try:
        from .tasks import index_knowledge_repository_task
        async_result = index_knowledge_repository_task.apply_async(args=[config.id, getattr(user, 'id', None), trigger], countdown=1)
        return {'queued': True, 'task_id': async_result.id}
    except Exception:
        try:
            run = index_repository(config, user=user, trigger=trigger)
            return {'queued': False, 'run': run}
        except Exception as exc:
            return {'queued': False, 'status': 'failed', 'error': str(exc)}


def maybe_auto_index_repository(config, user=None, trigger='auto_ready'):
    if not config.auto_index_on_ready:
        space = ensure_repository_space(config, user=user)
        if is_repository_config_ready(config):
            set_space_build_status(space, 'ready', 'Configuration is ready. Manual indexing is available.')
        return None
    return dispatch_repository_index(config, user=user, trigger=trigger)


def get_default_source_repository_path():
    for candidate in DEFAULT_SOURCE_REPO_CANDIDATES:
        candidate = str(candidate or '').strip()
        if candidate and Path(candidate).exists():
            return normalize_local_repository_path(candidate)
    return normalize_local_repository_path(str(settings.BASE_DIR))


def seed_current_platform_repository(user=None, project_id=None):
    project = None
    if project_id:
        project = Project.objects.filter(id=project_id).first()
    if not project and user and getattr(user, 'is_authenticated', False):
        project, _ = Project.objects.get_or_create(
            name=f'{PLATFORM_BRAND_NAME}平台自身',
            defaults={
                'description': '平台自身源码与当前数据库的项目级知识库，用于代码图谱、数据库图谱和知识库助手验证。',
                'owner': user,
                'status': 'active',
            },
        )
    space = (
        ensure_project_knowledge_space(project, user=user)
        if project
        else ensure_default_knowledge_space(user=user, key=MANUAL_QUALITY_SPACE_KEY, name=MANUAL_QUALITY_NAME)
    )
    local_path = get_default_source_repository_path()
    config, created = KnowledgeRepositoryConfig.objects.get_or_create(
        name=f'{PLATFORM_BRAND_NAME}平台源码仓库',
        space=space,
        defaults={
            'project': project,
            'provider': 'local',
            'repository_mode': LOCAL_PATH_REPOSITORY_MODE,
            'auth_mode': 'none',
            'local_path': local_path,
            'default_branch': get_git_branch(local_path) or 'main',
            'code_root': '.',
            'frontend_root': 'frontend',
            'backend_root': 'apps',
            'docs_root': 'docs',
            'database_engine': 'current',
            'auto_index_on_ready': True,
            'authorization_status': 'authorized',
            'authorization_message': '本平台源码仓库作为本地知识库对象，已授权只读索引。',
            'created_by': user if getattr(user, 'is_authenticated', False) else None,
        },
    )
    update_fields = []
    if not created:
        desired = {
            'project': project,
            'provider': 'local',
            'repository_mode': LOCAL_PATH_REPOSITORY_MODE,
            'auth_mode': 'none',
            'local_path': local_path,
            'database_engine': 'current',
            'auto_index_on_ready': True,
            'authorization_status': 'authorized',
            'authorization_message': '本平台源码仓库作为本地知识库对象，已授权只读索引。',
        }
        branch = get_git_branch(local_path)
        if branch:
            desired['default_branch'] = branch
        for field, value in desired.items():
            current = getattr(config, f'{field}_id', None) if field == 'project' else getattr(config, field)
            desired_value = value.id if field == 'project' and value else value
            if current != desired_value:
                setattr(config, field, value)
                update_fields.append(field)
        if update_fields:
            update_fields.append('updated_at')
            config.save(update_fields=update_fields)
    return config, created


def get_git_branch(path):
    try:
        result = subprocess.run(
            ['git', '-C', str(path), 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return ''
    return ''


def build_authenticated_repository_url(repository_url, username='', token=''):
    if not repository_url or not token:
        return repository_url or ''
    parsed = urlsplit(repository_url)
    if not parsed.scheme or not parsed.netloc or '@' in parsed.netloc:
        return repository_url
    auth_user = quote(username or 'oauth2', safe='')
    auth_token = quote(token, safe='')
    return urlunsplit((parsed.scheme, f'{auth_user}:{auth_token}@{parsed.netloc}', parsed.path, parsed.query, parsed.fragment))


def resolve_repository_worktree(config):
    if config.repository_mode == LOCAL_PATH_REPOSITORY_MODE:
        return Path(normalize_local_repository_path(config.local_path))

    cache_root = Path(settings.MEDIA_ROOT) / 'knowledge' / 'repositories'
    cache_root.mkdir(parents=True, exist_ok=True)
    target_dir = cache_root / f'config-{config.id}'
    token = decrypt_password(config.access_token_encrypted) if config.access_token_encrypted else ''
    repository_url = build_authenticated_repository_url(config.repository_url, config.username, token)
    if target_dir.exists() and (target_dir / '.git').exists():
        subprocess.run(['git', '-C', str(target_dir), 'fetch', '--all', '--prune'], check=True, timeout=60)
    else:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        clone_args = ['git', 'clone', '--depth', '1']
        if config.default_branch:
            clone_args.extend(['--branch', config.default_branch])
        clone_args.extend([repository_url, str(target_dir)])
        subprocess.run(clone_args, check=True, timeout=120)
    if config.index_ref:
        subprocess.run(['git', '-C', str(target_dir), 'checkout', config.index_ref], check=True, timeout=60)
    return target_dir


def test_repository_connection(config):
    if config.repository_mode == LOCAL_PATH_REPOSITORY_MODE:
        path = Path(normalize_local_repository_path(config.local_path))
        if not path.exists():
            return {
                'success': False,
                'message': f'本地仓库路径不存在：{path}',
                'branches': [],
            }, 400
        result = subprocess.run(
            ['git', '-C', str(path), 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {
                'success': False,
                'message': f'本地路径不是 Git 仓库：{result.stderr.strip()}',
                'branches': [],
            }, 400
        branch_result = subprocess.run(
            ['git', '-C', str(path), 'for-each-ref', '--format=%(refname:short)', 'refs/heads'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        branches = [line.strip() for line in branch_result.stdout.splitlines() if line.strip()][:20]
        return {
            'success': True,
            'message': '本地 Git 仓库连接测试成功。',
            'branches': branches,
            'current_branch': get_git_branch(path),
            'repository_location': str(path),
        }, 200

    token = decrypt_password(config.access_token_encrypted) if config.access_token_encrypted else ''
    repository_url = build_authenticated_repository_url(config.repository_url, config.username, token)
    result = subprocess.run(
        ['git', 'ls-remote', repository_url],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        return {
            'success': False,
            'message': f'远程 Git 仓库连接失败：{result.stderr.strip()}',
            'branches': [],
        }, 400
    branches = []
    for line in result.stdout.splitlines():
        if 'refs/heads/' in line:
            branches.append(line.split('refs/heads/')[-1].strip())
    return {
        'success': True,
        'message': '远程 Git 仓库连接测试成功。',
        'branches': branches[:20],
        'repository_location': config.repository_url,
    }, 200


def build_authorization_payload(config, request):
    state = secrets.token_urlsafe(24)
    config.authorization_state = state
    config.authorization_status = 'pending'
    config.authorization_message = '已生成授权请求，等待用户在弹出授权页确认。'
    config.save(update_fields=['authorization_state', 'authorization_status', 'authorization_message', 'updated_at'])

    provider = config.provider or 'local'
    if provider == 'github' and os.environ.get('GITHUB_OAUTH_CLIENT_ID'):
        redirect_uri = request.build_absolute_uri(reverse('knowledge-github-oauth-callback'))
        query = urlencode({
            'client_id': os.environ['GITHUB_OAUTH_CLIENT_ID'],
            'redirect_uri': redirect_uri,
            'scope': 'repo',
            'state': state,
        })
        authorization_url = f'https://github.com/login/oauth/authorize?{query}'
        mode = 'github_oauth'
    else:
        authorization_url = request.build_absolute_uri(
            reverse('knowledge-local-authorization-confirm', kwargs={'pk': config.id})
        )
        authorization_url = f'{authorization_url}?{urlencode({"state": state})}'
        mode = 'local_confirm'

    return {
        'success': True,
        'provider': provider,
        'authorization_mode': mode,
        'authorization_url': authorization_url,
        'state': state,
        'message': '请在弹出的授权页面中点击授权。GitHub OAuth 需要配置 GITHUB_OAUTH_CLIENT_ID/GITHUB_OAUTH_CLIENT_SECRET；本地仓库使用平台只读确认授权。',
    }


def confirm_local_authorization(config, state):
    if not state or state != config.authorization_state:
        return False, '授权 state 不匹配，请重新发起授权。'
    config.authorization_status = 'authorized'
    config.authorization_message = '用户已在授权页面确认，平台可对该仓库执行只读索引。'
    config.authorization_scopes = ['repository:read', 'metadata:read']
    config.save(update_fields=['authorization_status', 'authorization_message', 'authorization_scopes', 'updated_at'])
    return True, '授权成功，可以关闭窗口。'


def normalize_source_hash(*parts):
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, (dict, list, tuple)):
            value = json.dumps(part, ensure_ascii=False, sort_keys=True)
        else:
            value = str(part or '')
        digest.update(value.encode('utf-8', errors='ignore'))
        digest.update(b'\0')
    return digest.hexdigest()


def normalize_object_key(object_type, key, name='', source_ref=''):
    normalized_key = str(key or '').strip()
    if not normalized_key:
        normalized_key = normalize_source_hash(object_type, name, source_ref)[:24]
    normalized_key = normalized_key.lower()
    if len(normalized_key) <= 255:
        return normalized_key
    digest = hashlib.sha1(normalized_key.encode('utf-8', errors='ignore')).hexdigest()[:16]
    return f'{normalized_key[:232]}:{digest}'


class KnowledgeIndexBuilder:
    def __init__(self, config, repository_root, run):
        self.config = config
        self.repository_root = Path(repository_root)
        self.run = run
        self.space = run.space
        self.project = config.project
        self.objects_by_key = {}
        self.relations = []
        self.report = {
            'sources': [],
            'warnings': [],
            'repository_root': str(self.repository_root),
        }

    def add_object(self, object_type, key, name, **kwargs):
        normalized_key = normalize_object_key(object_type, key, name, kwargs.get('source_ref'))
        if normalized_key in self.objects_by_key:
            existing = self.objects_by_key[normalized_key]
            for field in ['summary', 'content', 'page_path', 'tab_key', 'component_path', 'api_path', 'db_table', 'field_name', 'source_ref', 'source_type']:
                value = kwargs.get(field)
                if value and not getattr(existing, field, ''):
                    setattr(existing, field, value)
            metadata = kwargs.get('metadata') or {}
            if metadata:
                existing.metadata = {**(existing.metadata or {}), **metadata}
            existing.search_text = self.build_search_text(existing)
            existing.source_hash = normalize_source_hash(
                existing.object_type,
                existing.key,
                existing.name,
                existing.summary,
                existing.content,
                existing.roadmap_path,
                existing.page_path,
                existing.tab_key,
                existing.component_path,
                existing.api_path,
                existing.db_table,
                existing.field_name,
                existing.source_type,
                existing.source_ref,
                existing.metadata,
                existing.search_text,
            )
            return existing
        obj = KnowledgeObject(
            space=self.space,
            project=self.project,
            repository_config=self.config,
            object_type=object_type,
            key=normalized_key,
            name=str(name or normalized_key).strip()[:255],
            summary=kwargs.get('summary') or '',
            content=kwargs.get('content') or '',
            roadmap_path=kwargs.get('roadmap_path') or [],
            page_path=kwargs.get('page_path') or '',
            tab_key=kwargs.get('tab_key') or '',
            component_path=kwargs.get('component_path') or '',
            api_path=kwargs.get('api_path') or '',
            db_table=kwargs.get('db_table') or '',
            field_name=kwargs.get('field_name') or '',
            source_type=kwargs.get('source_type') or '',
            source_ref=kwargs.get('source_ref') or '',
            metadata=kwargs.get('metadata') or {},
        )
        obj.search_text = self.build_search_text(obj)
        obj.source_hash = normalize_source_hash(
            object_type,
            normalized_key,
            obj.name,
            obj.summary,
            obj.content,
            obj.roadmap_path,
            obj.page_path,
            obj.tab_key,
            obj.component_path,
            obj.api_path,
            obj.db_table,
            obj.field_name,
            obj.source_type,
            obj.source_ref,
            obj.metadata,
            obj.search_text,
        )
        self.objects_by_key[normalized_key] = obj
        return obj

    def build_search_text(self, obj):
        parts = [
            obj.object_type,
            obj.key,
            obj.name,
            obj.summary,
            obj.content,
            obj.page_path,
            obj.tab_key,
            obj.component_path,
            obj.api_path,
            obj.db_table,
            obj.field_name,
            obj.source_ref,
            ' '.join(str(item) for item in obj.roadmap_path or []),
        ]
        metadata = obj.metadata or {}
        for value in metadata.values():
            if isinstance(value, (str, int, float)):
                parts.append(str(value))
            elif isinstance(value, list):
                parts.extend(str(item) for item in value[:20])
        return '\n'.join(part for part in parts if part)

    def add_relation(self, source, target, relation_type, label='', **kwargs):
        if not source or not target:
            return
        self.relations.append({
            'source': source,
            'target': target,
            'relation_type': relation_type,
            'label': label or relation_type,
            'weight': float(kwargs.get('weight') or 1.0),
            'source_ref': kwargs.get('source_ref') or source.source_ref or target.source_ref,
            'metadata': kwargs.get('metadata') or {},
        })

    def build(self):
        self.seed_core_manual_quality_objects()
        self.index_roadmap()
        self.index_frontend_workspace()
        self.index_backend_urls()
        self.index_database_schema()
        if self.should_index_runtime_django_models():
            self.index_django_models()
        self.index_code_assets()
        self.persist()

    def should_index_runtime_django_models(self):
        schema_config = get_repository_database_schema_config(self.config)
        if not schema_config or schema_config.get('engine') != 'current':
            return False
        try:
            configured_root = Path(self.config.code_root or '.')
            root = (self.repository_root / configured_root).resolve()
            return (root / 'manage.py').exists() or (self.repository_root / 'manage.py').exists()
        except Exception:
            return False

    def rel_path(self, path):
        try:
            return str(Path(path).resolve().relative_to(self.repository_root.resolve())).replace('\\', '/')
        except Exception:
            return str(path).replace('\\', '/')

    def read_text(self, relative_path, max_chars=500000):
        path = self.repository_root / relative_path
        if not path.exists() or not path.is_file():
            return ''
        try:
            return path.read_text(encoding='utf-8', errors='ignore')[:max_chars]
        except Exception as exc:
            self.report['warnings'].append(f'读取文件失败 {relative_path}: {exc}')
            return ''

    def seed_core_manual_quality_objects(self):
        platform = self.add_object('platform', 'platform:testhub', f'{PLATFORM_BRAND_NAME}平台', summary='AI研发全链路平台。')
        module = self.add_object(
            'module',
            'module:manual-quality',
            '思源质量',
            summary='思源质量模块，承载需求、研发、自测、测试、缺陷、报告、配置、管理和知识库助手。',
            page_path='/manual-testcases/list',
            roadmap_path=[f'{PLATFORM_BRAND_NAME}平台', '思源质量'],
        )
        repository = self.add_object(
            'repository',
            f'repository:{self.config.id}',
            self.config.name,
            summary='知识库对象的代码事实来源仓库。',
            source_type='repository_config',
            source_ref=self.config.repository_location,
            metadata={
                'provider': self.config.provider,
                'repository_mode': self.config.repository_mode,
                'default_branch': self.config.default_branch,
            },
        )
        self.add_relation(platform, module, 'contains', '包含模块')
        self.add_relation(module, repository, 'uses', '使用仓库事实源')

        config_menu = self.add_object(
            'menu',
            'menu:manual-quality:config',
            '配置',
            summary='思源质量配置一级菜单。',
            roadmap_path=['思源质量', '配置'],
            page_path='/manual-testcases/list?tab=configs',
        )
        repo_tab = self.add_object(
            'tab',
            'tab:manual-quality:knowledge-repositories',
            'Git/GitHub仓库配置',
            summary='维护知识库对象的 Git/GitHub 仓库、本地仓库、授权方式、索引范围和索引任务。',
            content='用于生成 roadmap、代码事实图谱和可靠问答的必要前置配置页签。',
            roadmap_path=['思源质量', '配置', 'Git/GitHub仓库配置'],
            page_path='/manual-testcases/list?tab=knowledge-repositories',
            tab_key='knowledge-repositories',
            component_path='frontend/src/views/manual-testcases/KnowledgeRepositoryConfigPanel.vue',
            source_type='manual_seed',
            source_ref='知识库助手建设方案.md',
            metadata={
                'operations': ['新增仓库配置', '编辑仓库配置', '弹出授权页面', '测试连接', '触发索引', '查看索引报告'],
                'fields': ['仓库名称', '项目', '仓库类型', '连接方式', '仓库地址', '本地路径', '默认分支', '前端目录', '后端目录', '文档目录'],
            },
        )
        api_config = self.add_object('api', 'api:/api/knowledge/repository-configs/', '知识库仓库配置API', api_path='/api/knowledge/repository-configs/', summary='知识库对象仓库配置 CRUD、授权、测试连接和索引。')
        table_config = self.add_object('table', 'table:knowledge_repository_configs', 'knowledge_repository_configs', db_table='knowledge_repository_configs', summary='知识库对象仓库配置表。')
        self.add_relation(module, config_menu, 'contains', '包含菜单')
        self.add_relation(config_menu, repo_tab, 'contains', '包含页签')
        self.add_relation(repo_tab, api_config, 'calls', '调用接口')
        self.add_relation(repo_tab, table_config, 'writes', '写入配置表')

    def index_roadmap(self):
        roadmap_path = Path(self.config.docs_root or 'docs') / 'manual-quality-knowledge-roadmap.md'
        text = self.read_text(roadmap_path)
        if not text:
            return
        self.report['sources'].append(str(roadmap_path).replace('\\', '/'))
        module = self.objects_by_key.get('module:manual-quality')
        table_count = 0
        for line in text.splitlines():
            raw = line.strip()
            if not raw.startswith('|') or raw.startswith('| ---'):
                continue
            cells = [cell.strip().strip('`') for cell in raw.strip('|').split('|')]
            if len(cells) < 3 or any(cell in {'---', ''} for cell in cells[:2]):
                continue
            if any(header in cells[0] for header in ['一级菜单', '上下文', '分组', '页面路径']):
                continue
            menu_name = cells[0]
            page_name = cells[1] if len(cells) > 1 else ''
            tab_or_path = cells[2] if len(cells) > 2 else ''
            component = cells[3] if len(cells) > 3 else ''
            tables_cell = cells[4] if len(cells) > 4 else ''
            if not page_name or len(page_name) > 120:
                continue
            table_count += 1
            menu = self.add_object(
                'menu',
                f'menu:manual-quality:{slugify(menu_name)}',
                menu_name,
                summary=f'思源质量菜单：{menu_name}',
                roadmap_path=['思源质量', menu_name],
                source_type='roadmap',
                source_ref=str(roadmap_path).replace('\\', '/'),
            )
            page_path = extract_page_path(tab_or_path)
            object_type = 'tab' if tab_or_path and not tab_or_path.startswith('/') else 'page'
            page = self.add_object(
                object_type,
                f'{object_type}:manual-quality:{slugify(tab_or_path or page_name)}',
                page_name,
                summary=f'{menu_name} / {page_name}',
                content=raw,
                roadmap_path=['思源质量', menu_name, page_name],
                page_path=page_path,
                tab_key=tab_or_path if page_path.startswith('/manual-testcases/list?tab=') else '',
                component_path=component if component.endswith(('.vue', '.js', '.py')) else '',
                source_type='roadmap',
                source_ref=str(roadmap_path).replace('\\', '/'),
                metadata={'raw_cells': cells},
            )
            if module:
                self.add_relation(module, menu, 'contains', '包含菜单')
            self.add_relation(menu, page, 'contains', '包含页面')
            for api_path in extract_api_paths(raw):
                api = self.add_object('api', f'api:{api_path}', api_path, api_path=api_path, summary=f'{page_name} 使用的接口。', source_type='roadmap', source_ref=str(roadmap_path).replace('\\', '/'))
                self.add_relation(page, api, 'calls', '调用接口')
            for table in extract_table_names(tables_cell or raw):
                table_obj = self.add_object('table', f'table:{table}', table, db_table=table, summary=f'{page_name} 相关数据表。', source_type='roadmap', source_ref=str(roadmap_path).replace('\\', '/'))
                self.add_relation(page, table_obj, 'reads', '读取/写入数据表')
        self.report['roadmap_table_rows'] = table_count

    def index_frontend_workspace(self):
        workspace_file = Path(self.config.frontend_root or 'frontend') / 'src/utils/manualTestcaseWorkspace.js'
        text = self.read_text(workspace_file)
        if text:
            self.report['sources'].append(str(workspace_file).replace('\\', '/'))
            module = self.objects_by_key.get('module:manual-quality')
            for match in re.finditer(r"\{\s*name:\s*'([^']+)'\s*,\s*label:\s*'([^']*)'\s*,\s*primary:\s*'([^']+)'([^}]*)\}", text):
                name, label, primary, rest = match.groups()
                page_path = f'/manual-testcases/list?tab={name}' if 'workspace: true' in rest else extract_path_from_js_object(rest) or ''
                menu = self.add_object('menu', f'menu:manual-quality:{primary}', primary, summary=f'一级菜单 {primary}', roadmap_path=['思源质量', primary], source_type='frontend_workspace', source_ref=str(workspace_file).replace('\\', '/'))
                tab = self.add_object(
                    'tab',
                    f'tab:manual-quality:{name}',
                    decode_label(label) or name,
                    summary=f'前端工作区页签 {name}',
                    tab_key=name,
                    page_path=page_path,
                    roadmap_path=['思源质量', primary, decode_label(label) or name],
                    source_type='frontend_workspace',
                    source_ref=str(workspace_file).replace('\\', '/'),
                    metadata={'primary': primary},
                )
                if module:
                    self.add_relation(module, menu, 'contains', '包含菜单')
                self.add_relation(menu, tab, 'contains', '包含页签')

        list_file = Path(self.config.frontend_root or 'frontend') / 'src/views/manual-testcases/ManualTestCaseList.vue'
        text = self.read_text(list_file)
        if not text:
            return
        self.report['sources'].append(str(list_file).replace('\\', '/'))
        for match in re.finditer(r'<el-tab-pane[^>]*label="([^"]+)"[^>]*name="([^"]+)"([\s\S]*?)</el-tab-pane>', text):
            label, name, block = match.groups()
            tab = self.add_object(
                'tab',
                f'tab:manual-quality:{name}',
                decode_label(label) or name,
                summary=f'ManualTestCaseList 页面页签：{decode_label(label) or name}',
                tab_key=name,
                page_path=f'/manual-testcases/list?tab={name}',
                component_path='frontend/src/views/manual-testcases/ManualTestCaseList.vue',
                source_type='frontend_component',
                source_ref=str(list_file).replace('\\', '/'),
                metadata={'vue_tab_name': name},
            )
            for component_name in sorted(set(re.findall(r'<([A-Z][A-Za-z0-9_]+)\b', block))):
                component = self.add_object(
                    'component',
                    f'component:{component_name}',
                    component_name,
                    summary=f'{decode_label(label) or name} 页签使用的前端组件。',
                    component_path=component_name,
                    source_type='frontend_component',
                    source_ref=str(list_file).replace('\\', '/'),
                )
                self.add_relation(tab, component, 'implements', '由组件实现')

    def index_backend_urls(self):
        candidates = [Path('backend/urls.py')]
        apps_dir = self.repository_root / (self.config.backend_root or 'apps')
        if apps_dir.exists():
            candidates.extend(Path(self.rel_path(path)) for path in apps_dir.glob('*/urls.py'))
        mount_prefixes = self.build_url_mount_prefixes()
        count = 0
        for relative_path in candidates:
            text = self.read_text(relative_path)
            if not text:
                continue
            source_ref = str(relative_path).replace('\\', '/')
            mount_prefix = '' if source_ref == 'backend/urls.py' else mount_prefixes.get(source_ref, '')
            self.report['sources'].append(source_ref)
            for prefix in re.findall(r"path\(\s*['\"]([^'\"]+)['\"]", text):
                api_path = normalize_indexed_api_path(prefix, mount_prefix)
                if not api_path:
                    continue
                api = self.add_object('api', f'api:{api_path}', api_path, api_path=api_path, summary='Django URL 路由。', source_type='backend_url', source_ref=source_ref)
                count += 1
                if 'knowledge' in api_path:
                    repo_tab = self.objects_by_key.get('tab:manual-quality:knowledge-repositories')
                    if repo_tab:
                        self.add_relation(repo_tab, api, 'calls', '调用知识库接口')
            for prefix in re.findall(r"router\.register\(\s*r?['\"]([^'\"]+)['\"]", text):
                api_path = normalize_indexed_api_path(prefix, mount_prefix)
                if not api_path:
                    continue
                api = self.add_object('api', f'api:{api_path}', api_path, api_path=api_path, summary='DRF ViewSet 路由。', source_type='backend_url', source_ref=source_ref)
                count += 1
        self.report['backend_api_route_count'] = count

    def index_code_assets(self):
        scan = scan_code_assets(self.repository_root, self.config)
        self.report['asset_scanner_code'] = {
            'summary': scan.get('summary') or {},
            'tool_status': scan.get('tool_status') or {},
            'warnings': scan.get('warnings') or [],
        }
        self.report['warnings'].extend(scan.get('warnings') or [])

        repository = self.objects_by_key.get(f'repository:{self.config.id}')
        api_objects = {
            obj.api_path: obj
            for obj in self.objects_by_key.values()
            if obj.object_type == 'api' and obj.api_path
        }
        file_objects = {}
        symbol_objects = {}
        table_objects = {
            (obj.db_table or obj.name): obj
            for obj in self.objects_by_key.values()
            if obj.object_type == 'table' and (obj.db_table or obj.name)
        }
        field_objects = {
            (obj.db_table, obj.field_name or obj.name): obj
            for obj in self.objects_by_key.values()
            if obj.object_type == 'field' and obj.db_table and (obj.field_name or obj.name)
        }
        field_objects_by_name = defaultdict(list)
        for (table_name, field_name), field_obj in field_objects.items():
            field_objects_by_name[field_name].append(field_obj)
        api_refs_by_file = defaultdict(list)
        table_refs_by_file = defaultdict(list)
        field_refs_by_file = defaultdict(list)

        for item in scan.get('files') or []:
            rel_path = item.get('path') or ''
            if not rel_path:
                continue
            file_obj = self.add_object(
                'file',
                f'file:{rel_path}',
                rel_path,
                summary=f'{item.get("language") or "代码"} 文件，{item.get("line_count") or 0} 行。',
                source_type='code_file',
                source_ref=rel_path,
                metadata={
                    'language': item.get('language') or '',
                    'size': item.get('size') or 0,
                    'line_count': item.get('line_count') or 0,
                    'symbol_count': item.get('symbol_count') or 0,
                    'api_reference_count': len(item.get('api_refs') or []),
                    'table_reference_count': len(item.get('table_refs') or []),
                    'field_reference_count': len(item.get('field_refs') or []),
                    'import_count': len(item.get('imports') or []),
                },
            )
            file_objects[rel_path] = file_obj
            if repository:
                self.add_relation(repository, file_obj, 'contains', '包含代码文件')

        for symbol in scan.get('symbols') or []:
            rel_path = symbol.get('file') or ''
            name = symbol.get('name') or ''
            object_type = symbol.get('type') if symbol.get('type') in {'class', 'function', 'method'} else 'function'
            if not rel_path or not name:
                continue
            symbol_obj = self.add_object(
                object_type,
                symbol.get('key') or f'{object_type}:{rel_path}:{name}:{symbol.get("line") or ""}',
                name,
                summary=f'{rel_path} 中的 {get_code_symbol_type_label(object_type)}。',
                source_type='code_symbol',
                source_ref=f'{rel_path}:{symbol.get("line") or ""}',
                metadata={
                    'file': rel_path,
                    'language': symbol.get('language') or '',
                    'line': symbol.get('line') or 0,
                    'scope': symbol.get('scope') or '',
                    'signature': symbol.get('signature') or '',
                    'scanner_tool': symbol.get('tool') or 'internal',
                },
            )
            symbol_objects[symbol.get('key')] = symbol_obj
            file_obj = file_objects.get(rel_path)
            if file_obj:
                self.add_relation(file_obj, symbol_obj, 'contains', '包含代码符号')

        for item in scan.get('imports') or []:
            file_obj = file_objects.get(item.get('file') or '')
            module = item.get('module') or ''
            if file_obj and module:
                self.add_relation(
                    file_obj,
                    repository,
                    'uses',
                    '导入模块',
                    source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                    metadata={'module': module, 'line': item.get('line') or 0},
                )

        for item in scan.get('api_references') or []:
            file_obj = file_objects.get(item.get('file') or '')
            api_path = item.get('api_path') or ''
            api_obj = api_objects.get(api_path)
            if not api_obj and api_path:
                api_obj = self.add_object(
                    'api',
                    f'api:{api_path}',
                    api_path,
                    api_path=api_path,
                    summary=f'代码中识别到的接口引用：{api_path}',
                    source_type='code_api_reference',
                    source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                    metadata={'scanner': 'asset_scanner'},
                )
                api_objects[api_path] = api_obj
            if file_obj and api_obj:
                self.add_relation(
                    file_obj,
                    api_obj,
                    'calls',
                    '引用接口路径',
                    source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                    metadata={'line': item.get('line') or 0, 'scanner': 'asset_scanner'},
                )
                api_refs_by_file[item.get('file') or ''].append((api_obj, item))

        for item in scan.get('table_references') or []:
            file_obj = file_objects.get(item.get('file') or '')
            table_name = item.get('table') or ''
            table_obj = table_objects.get(table_name) or self.add_object(
                'table',
                f'table:{table_name}',
                table_name,
                db_table=table_name,
                summary=f'代码中识别到的数据表引用：{table_name}',
                source_type='code_table_reference',
                source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                metadata={'scanner': 'asset_scanner'},
            )
            table_objects[table_name] = table_obj
            if file_obj and table_obj:
                relation_type = 'writes' if item.get('mode') == 'writes' else 'reads'
                self.add_relation(
                    file_obj,
                    table_obj,
                    relation_type,
                    '写入数据表' if relation_type == 'writes' else '读取数据表',
                    source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                    metadata={'line': item.get('line') or 0, 'scanner': 'asset_scanner'},
                )
                table_refs_by_file[item.get('file') or ''].append((table_obj, item))

        for item in scan.get('field_references') or []:
            file_obj = file_objects.get(item.get('file') or '')
            field_name = item.get('field') or ''
            if not file_obj or not field_name:
                continue
            candidates = field_objects_by_name.get(field_name) or []
            for field_obj in candidates[:3]:
                self.add_relation(
                    file_obj,
                    field_obj,
                    'uses',
                    '引用字段',
                    source_ref=f'{item.get("file")}:{item.get("line") or ""}',
                    metadata={
                        'line': item.get('line') or 0,
                        'table_or_alias': item.get('table_or_alias') or '',
                        'confidence': 'field-name-match',
                        'scanner': 'asset_scanner',
                    },
                )
                field_refs_by_file[item.get('file') or ''].append((field_obj, item))

        self.link_api_data_references(api_refs_by_file, table_refs_by_file, field_refs_by_file)

        for call in scan.get('calls') or []:
            file_obj = file_objects.get(call.get('file') or '')
            target_obj = symbol_objects.get(call.get('target_key') or '')
            if file_obj and target_obj:
                self.add_relation(
                    file_obj,
                    target_obj,
                    'calls',
                    '调用代码符号',
                    source_ref=f'{call.get("file")}:{call.get("line") or ""}',
                    metadata={
                        'callee': call.get('callee') or '',
                        'raw': call.get('raw') or '',
                        'confidence': call.get('confidence') or '',
                    },
                )

        for finding in scan.get('semantic_findings') or []:
            rel_path = finding.get('file') or ''
            file_obj = file_objects.get(rel_path)
            finding_obj = self.add_object(
                'business_data',
                f'semgrep:{finding.get("rule_id") or "rule"}:{rel_path}:{finding.get("line") or ""}',
                finding.get('rule_id') or 'semgrep finding',
                summary=finding.get('message') or 'Semgrep 语义扫描发现。',
                source_type='semgrep_finding',
                source_ref=f'{rel_path}:{finding.get("line") or ""}',
                metadata={
                    'line': finding.get('line') or 0,
                    'severity': finding.get('severity') or '',
                    'rule_id': finding.get('rule_id') or '',
                    'metadata': finding.get('metadata') or {},
                },
            )
            if file_obj:
                self.add_relation(file_obj, finding_obj, 'related_to', '存在语义扫描发现')

        summary = scan.get('summary') or {}
        self.report['code_file_count'] = summary.get('file_count') or len(file_objects)
        self.report['code_symbol_count'] = summary.get('symbol_count') or len(symbol_objects)
        self.report['code_api_reference_count'] = summary.get('api_reference_count') or 0
        self.report['code_table_reference_count'] = summary.get('table_reference_count') or 0
        self.report['code_call_count'] = summary.get('call_count') or 0

    def link_api_data_references(self, api_refs_by_file, table_refs_by_file, field_refs_by_file):
        inferred_count = 0
        for rel_path, api_entries in api_refs_by_file.items():
            if not api_entries:
                continue
            table_entries = table_refs_by_file.get(rel_path) or []
            field_entries = field_refs_by_file.get(rel_path) or []
            if not table_entries and not field_entries:
                continue
            for api_obj, api_ref in api_entries[:20]:
                for table_obj, table_ref in table_entries[:30]:
                    relation_type = 'writes' if table_ref.get('mode') == 'writes' else 'reads'
                    self.add_relation(
                        api_obj,
                        table_obj,
                        relation_type,
                        '接口写入数据表' if relation_type == 'writes' else '接口读取数据表',
                        source_ref=f'{rel_path}:{table_ref.get("line") or api_ref.get("line") or ""}',
                        metadata={
                            'inferred_from_file': rel_path,
                            'api_line': api_ref.get('line') or 0,
                            'table_line': table_ref.get('line') or 0,
                            'confidence': 'same-file-api-sql-reference',
                            'scanner': 'asset_scanner',
                        },
                    )
                    inferred_count += 1
                for field_obj, field_ref in field_entries[:50]:
                    self.add_relation(
                        api_obj,
                        field_obj,
                        'references',
                        '接口引用字段',
                        source_ref=f'{rel_path}:{field_ref.get("line") or api_ref.get("line") or ""}',
                        metadata={
                            'inferred_from_file': rel_path,
                            'api_line': api_ref.get('line') or 0,
                            'field_line': field_ref.get('line') or 0,
                            'table_or_alias': field_ref.get('table_or_alias') or '',
                            'confidence': 'same-file-api-field-reference',
                            'scanner': 'asset_scanner',
                        },
                    )
                    inferred_count += 1
        self.report['api_data_reference_inferred_count'] = inferred_count

    def build_url_mount_prefixes(self):
        text = self.read_text(Path('backend/urls.py'))
        mounts = {}
        if not text:
            return mounts
        pattern = r"path\(\s*['\"]([^'\"]*)['\"]\s*,\s*include\(\s*['\"]apps\.([A-Za-z0-9_]+)\.urls['\"]"
        for prefix, app_label in re.findall(pattern, text):
            api_path = normalize_indexed_api_path(prefix)
            if api_path:
                mounts[f'apps/{app_label}/urls.py'] = api_path
        return mounts

    def index_django_models(self):
        table_count = 0
        field_count = 0
        for model in django_apps.get_models():
            app_label = model._meta.app_label
            if app_label in {'admin', 'auth', 'contenttypes', 'sessions', 'token_blacklist'}:
                continue
            table_name = model._meta.db_table
            table = self.add_object(
                'table',
                f'table:{table_name}',
                table_name,
                db_table=table_name,
                summary=f'Django 模型 {app_label}.{model.__name__} 对应的数据表。',
                source_type='django_model',
                source_ref=f'{app_label}.{model.__name__}',
                metadata={'app_label': app_label, 'model': model.__name__},
            )
            table_count += 1
            for field in model._meta.fields:
                field_obj = self.add_object(
                    'field',
                    f'field:{table_name}.{field.name}',
                    field.name,
                    db_table=table_name,
                    field_name=field.name,
                    summary=f'{table_name}.{field.name}',
                    source_type='django_model',
                    source_ref=f'{app_label}.{model.__name__}.{field.name}',
                    metadata={'field_type': field.__class__.__name__},
                )
                self.add_relation(table, field_obj, 'contains', '包含字段')
                field_count += 1
        self.report['django_table_count'] = table_count
        self.report['django_field_count'] = field_count

    def index_database_schema(self):
        schema_config = get_repository_database_schema_config(self.config)
        if not schema_config:
            self.report['database_schema_indexing'] = 'disabled'
            return
        try:
            scan = scan_database_assets(self.config, schema_config)
            self.report['asset_scanner_database'] = {
                'summary': scan.get('summary') or {},
                'source': scan.get('source') or '',
                'tool_status': scan.get('tool_status') or {},
                'warnings': scan.get('warnings') or [],
            }
            self.report['warnings'].extend(scan.get('warnings') or [])
            database_info = scan.get('database') or {}
            schema_name = database_info.get('schema') or schema_config.get('schema') or schema_config['name']
            database = self.add_object(
                'database',
                f'database:{schema_name}',
                schema_name,
                summary='Project database schema configured for the knowledge object.',
                roadmap_path=[self.config.project.name if self.config.project else 'Project', 'Database'],
                source_type='database_schema',
                source_ref=schema_name,
                metadata={
                    'engine': database_info.get('engine') or schema_config['engine'],
                    'database': database_info.get('name') or schema_config['name'],
                    'schema': schema_name,
                    'source': scan.get('source') or '',
                    'allow_sample_data': self.config.allow_sample_data,
                },
            )
            table_objects = {}
            for table_info in scan.get('tables') or []:
                table_name = table_info.get('name') or ''
                if not table_name:
                    continue
                table = self.add_object(
                    'table',
                    f'table:{table_name}',
                    table_name,
                    summary=table_info.get('comment') or f'Database table {table_name}.',
                    db_table=table_name,
                    roadmap_path=[self.config.project.name if self.config.project else 'Project', 'Database', table_name],
                    source_type='database_schema',
                    source_ref=f'{schema_name}.{table_name}',
                    metadata={
                        'database': database_info.get('name') or schema_config['name'],
                        'schema': schema_name,
                        'engine': table_info.get('engine') or '',
                        'table_type': table_info.get('table_type') or '',
                        'row_estimate': table_info.get('row_estimate') or 0,
                        'scanner_source': scan.get('source') or '',
                    },
                )
                table_objects[table_name] = table
                self.add_relation(database, table, 'contains', 'contains table')
            field_count = 0
            for column in scan.get('fields') or []:
                table_name = column.get('table') or ''
                table = table_objects.get(table_name)
                if not table:
                    continue
                column_name = column.get('name') or ''
                if not column_name:
                    continue
                field = self.add_object(
                    'field',
                    f'field:{table_name}.{column_name}',
                    column_name,
                    summary=column.get('comment') or f'{table_name}.{column_name}',
                    db_table=table_name,
                    field_name=column_name,
                    roadmap_path=[
                        self.config.project.name if self.config.project else 'Project',
                        'Database',
                        table_name,
                        column_name,
                    ],
                    source_type='database_schema',
                    source_ref=f'{schema_name}.{table_name}.{column_name}',
                    metadata={
                        'column_type': column.get('column_type') or '',
                        'data_type': column.get('data_type') or '',
                        'is_nullable': column.get('nullable') or '',
                        'column_key': column.get('column_key') or '',
                        'default': column.get('default'),
                        'extra': column.get('extra') or '',
                        'ordinal': column.get('ordinal') or 0,
                        'scanner_source': scan.get('source') or '',
                    },
                )
                self.add_relation(table, field, 'contains', 'contains field')
                field_count += 1

            for fk in scan.get('foreign_keys') or []:
                source_table = table_objects.get(fk.get('table') or '')
                target_table = table_objects.get(fk.get('referenced_table') or '')
                if source_table and target_table:
                    self.add_relation(
                        source_table,
                        target_table,
                        'related_to',
                        '外键关联',
                        source_ref=f'{schema_name}.{fk.get("table") or ""}.{fk.get("column") or ""}',
                        metadata={
                            'constraint_name': fk.get('name') or '',
                            'column': fk.get('column') or '',
                            'referenced_column': fk.get('referenced_column') or '',
                            'update_rule': fk.get('update_rule') or '',
                            'delete_rule': fk.get('delete_rule') or '',
                            'relation_kind': 'foreign_key',
                        },
                    )

            self.report['database_schema_table_count'] = len(table_objects)
            self.report['database_schema_field_count'] = field_count
            self.report['database_schema_index_count'] = len(scan.get('indexes') or [])
            self.report['database_schema_foreign_key_count'] = len(scan.get('foreign_keys') or [])
            self.report['database_schema_name'] = database_info.get('name') or schema_config['name']
            self.report['database_schema'] = schema_name
        except Exception as exc:
            self.report['warnings'].append(f'Database schema indexing failed: {exc}')
            self.report['database_schema_error'] = str(exc)

    @transaction.atomic
    def persist(self):
        objects = list(self.objects_by_key.values())
        now = timezone.now()
        incoming_keys = [obj.key for obj in objects]
        existing_by_key = {
            obj.key: obj
            for obj in KnowledgeObject.objects.filter(space=self.space, key__in=incoming_keys)
        }
        stale_objects = KnowledgeObject.objects.filter(repository_config=self.config).exclude(key__in=incoming_keys)
        stale_ids = list(stale_objects.values_list('id', flat=True))
        if stale_ids:
            KnowledgeRelation.objects.filter(Q(source_id__in=stale_ids) | Q(target_id__in=stale_ids)).delete()
            stale_objects.delete()

        create_rows = []
        update_rows = []
        changed_count = len(stale_ids)
        updatable_fields = [
            'project',
            'repository_config',
            'object_type',
            'name',
            'summary',
            'content',
            'roadmap_path',
            'page_path',
            'tab_key',
            'component_path',
            'api_path',
            'db_table',
            'field_name',
            'source_type',
            'source_ref',
            'source_hash',
            'metadata',
            'search_text',
            'indexed_at',
            'updated_at',
        ]
        for obj in objects:
            existing = existing_by_key.get(obj.key)
            obj.indexed_at = now
            if not existing:
                create_rows.append(obj)
                changed_count += 1
                continue
            if existing.source_hash == obj.source_hash and existing.repository_config_id == self.config.id:
                continue
            for field in updatable_fields:
                setattr(existing, field, getattr(obj, field))
            existing.updated_at = now
            update_rows.append(existing)
            changed_count += 1

        if create_rows:
            KnowledgeObject.objects.bulk_create(create_rows, batch_size=500)
        if update_rows:
            KnowledgeObject.objects.bulk_update(update_rows, updatable_fields, batch_size=500)

        persisted = {
            item.key: item
            for item in KnowledgeObject.objects.filter(space=self.space, key__in=incoming_keys)
        }
        object_ids = [obj.id for obj in persisted.values()]
        if object_ids:
            KnowledgeRelation.objects.filter(
                space=self.space,
            ).filter(Q(source_id__in=object_ids) | Q(target_id__in=object_ids)).delete()
        relation_rows = []
        seen = set()
        for relation in self.relations:
            source = persisted.get(relation['source'].key)
            target = persisted.get(relation['target'].key)
            if not source or not target:
                continue
            identity = (source.id, target.id, relation['relation_type'])
            if identity in seen:
                continue
            seen.add(identity)
            relation_rows.append(KnowledgeRelation(
                space=self.space,
                source=source,
                target=target,
                relation_type=relation['relation_type'],
                label=relation['label'],
                weight=relation['weight'],
                source_ref=relation['source_ref'],
                metadata=relation['metadata'],
            ))
        KnowledgeRelation.objects.bulk_create(relation_rows, batch_size=500, ignore_conflicts=True)
        self.run.object_count = len(objects)
        self.run.relation_count = len(relation_rows)
        self.run.changed_object_count = changed_count
        self.report['incremental'] = {
            'created_object_count': len(create_rows),
            'updated_object_count': len(update_rows),
            'deleted_object_count': len(stale_ids),
            'unchanged_object_count': max(0, len(objects) - len(create_rows) - len(update_rows)),
        }
        self.run.report = self.report
        self.run.save(update_fields=['object_count', 'relation_count', 'changed_object_count', 'report'])


def index_repository(config, user=None, trigger='manual'):
    space = ensure_repository_space(config, user=user)
    set_space_build_status(space, 'indexing', f'Indexing knowledge object from repository config #{config.id}.')
    run = KnowledgeIndexRun.objects.create(
        space=space,
        repository_config=config,
        status='running',
        trigger=trigger,
        index_ref=config.index_ref or config.default_branch,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    try:
        repository_root = resolve_repository_worktree(config)
        builder = KnowledgeIndexBuilder(config, repository_root, run)
        builder.build()
        run.status = 'success'
        run.finished_at = timezone.now()
        run.log = f'索引完成：{run.object_count} 个知识对象，{run.relation_count} 条双链关系。'
        run.save(update_fields=['status', 'finished_at', 'log'])
        config.last_indexed_at = run.finished_at
        config.save(update_fields=['last_indexed_at', 'updated_at'])
        set_space_build_status(
            space,
            'indexed',
            f'Index completed: {run.object_count} objects, {run.relation_count} relations.',
            last_indexed_at=run.finished_at,
        )
    except Exception as exc:
        run.status = 'failed'
        run.finished_at = timezone.now()
        run.error_message = str(exc)
        run.save(update_fields=['status', 'finished_at', 'error_message'])
        set_space_build_status(space, 'failed', str(exc))
        raise
    return run


def slugify(value):
    text = str(value or '').strip()
    if not text:
        return 'unknown'
    ascii_text = re.sub(r'[^A-Za-z0-9_.-]+', '-', text).strip('-').lower()
    if ascii_text:
        return ascii_text[:80]
    return hashlib.sha1(text.encode('utf-8', errors='ignore')).hexdigest()[:16]


def decode_label(value):
    return str(value or '').strip()


def extract_path_from_js_object(text):
    match = re.search(r"path:\s*'([^']+)'", text or '')
    return match.group(1) if match else ''


def extract_page_path(value):
    text = str(value or '').strip().strip('`')
    if not text:
        return ''
    if text.startswith('/'):
        return text
    if re.fullmatch(r'[A-Za-z0-9_-]+', text):
        return f'/manual-testcases/list?tab={text}'
    return ''


def normalize_indexed_api_path(path, mount_prefix=''):
    raw = str(path or '').strip().strip('`')
    mount = str(mount_prefix or '').strip()
    if raw in {'', '<int:pk>/', '<slug:slug>/'} and not mount:
        return ''
    parts = []
    if mount:
        parts.append(mount.strip('/'))
    parts.append(raw.strip('/'))
    joined = '/'.join(part for part in parts if part)
    if not joined:
        return ''
    while joined.startswith('api/api/'):
        joined = joined[len('api/'):]
    if not joined.startswith('api/'):
        return ''
    return '/' + joined.strip('/') + '/'


def extract_api_paths(text):
    return sorted(set(re.findall(r'(/api/[A-Za-z0-9_./{}?=&:-]+)', str(text or ''))))


def extract_table_names(text):
    candidates = set()
    for token in re.findall(r'`([^`]+)`', str(text or '')):
        for part in re.split(r'[、,\s]+', token):
            if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,}', part) and ('_' in part or part.endswith('s')):
                candidates.add(part)
    for part in re.findall(r'\b[A-Za-z][A-Za-z0-9_]{2,}\b', str(text or '')):
        if '_' in part and not part.startswith('/api'):
            candidates.add(part)
    return sorted(candidates)[:20]


SUPPORTED_CODE_EXTENSIONS = {
    '.py',
    '.js',
    '.jsx',
    '.ts',
    '.tsx',
    '.vue',
    '.java',
    '.go',
    '.php',
    '.rb',
    '.cs',
    '.c',
    '.cc',
    '.cpp',
    '.cxx',
    '.h',
    '.hpp',
    '.rs',
    '.sql',
}


def is_supported_code_file(path):
    return Path(path).suffix.lower() in SUPPORTED_CODE_EXTENSIONS


def safe_file_size(path):
    try:
        return Path(path).stat().st_size
    except Exception:
        return 0


def is_path_included(rel_path, include_patterns=None):
    patterns = [str(item or '').strip() for item in include_patterns or [] if str(item or '').strip()]
    if not patterns:
        return True
    normalized = str(rel_path or '').replace('\\', '/')
    return any(match_path_pattern(normalized, pattern) for pattern in patterns)


def is_path_excluded(rel_path, exclude_patterns=None):
    normalized = str(rel_path or '').replace('\\', '/')
    default_excludes = ['node_modules', 'dist', 'build', '__pycache__', '.git', '.venv', 'venv']
    if any(part and part in normalized.split('/') for part in default_excludes):
        return True
    return any(match_path_pattern(normalized, str(pattern or '').strip()) for pattern in exclude_patterns or [])


def match_path_pattern(path, pattern):
    if not pattern:
        return False
    normalized_pattern = pattern.replace('\\', '/').strip()
    if normalized_pattern in path:
        return True
    regex = '^' + re.escape(normalized_pattern).replace('\\*', '.*') + '$'
    return re.search(regex, path, re.IGNORECASE) is not None


def infer_code_language(path):
    suffix = Path(path).suffix.lower()
    return {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript',
        '.vue': 'Vue',
        '.java': 'Java',
        '.go': 'Go',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.cs': 'C#',
        '.c': 'C',
        '.cc': 'C++',
        '.cpp': 'C++',
        '.cxx': 'C++',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.rs': 'Rust',
        '.sql': 'SQL',
    }.get(suffix, suffix.lstrip('.').upper() if suffix else 'Text')


def extract_lightweight_symbols(rel_path, text, language, max_symbols_per_file=30):
    patterns = []
    if language == 'Python':
        patterns = [
            ('class', r'^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b'),
            ('function', r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language in {'JavaScript', 'TypeScript', 'Vue'}:
        patterns = [
            ('class', r'\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*)\b'),
            ('function', r'\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\('),
            ('function', r'\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'),
            ('function', r'\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:computed|ref|reactive|watch|onMounted)\b'),
        ]
    elif language == 'Java':
        patterns = [
            ('class', r'\b(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b'),
            ('method', r'\b(?:public|private|protected)\s+[\w<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language == 'Go':
        patterns = [
            ('function', r'\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\('),
        ]
    elif language == 'SQL':
        patterns = [
            ('function', r'\b(?:CREATE|ALTER)\s+(?:PROCEDURE|FUNCTION|VIEW)\s+([A-Za-z_][A-Za-z0-9_.]*)\b'),
        ]
    symbols = []
    seen = set()
    for symbol_type, pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            name = match.group(1)
            if not name or (symbol_type in {'function', 'method'} and name.startswith('_')):
                continue
            identity = (symbol_type, name)
            if identity in seen:
                continue
            seen.add(identity)
            line = text.count('\n', 0, match.start()) + 1
            symbols.append({'type': symbol_type, 'name': name, 'line': line, 'file': rel_path})
            if len(symbols) >= max_symbols_per_file:
                return symbols
    return symbols


def get_code_symbol_type_label(object_type):
    return {
        'class': '类/接口',
        'function': '函数',
        'method': '方法',
    }.get(object_type, '代码符号')


def tokenize_query(text):
    normalized = str(text or '').lower()
    tokens = set()
    for token in re.findall(r'[a-z0-9_./:-]{2,}', normalized):
        tokens.add(token)
    for chunk in re.findall(r'[\u4e00-\u9fff]{2,}', str(text or '')):
        tokens.add(chunk)
        for size in (2, 3, 4):
            for index in range(0, max(0, len(chunk) - size + 1)):
                tokens.add(chunk[index:index + size])
    synonyms = {
        '授权': ['oauth', 'github_app', 'access_token', '仓库配置', 'Git/GitHub仓库配置'],
        '仓库': ['repository', 'git', 'github', 'Git/GitHub仓库配置'],
        '图谱': ['双链', '关系图', 'knowledge_relations'],
        '缺陷': ['version-defects', 'bug-records', 'defects'],
        '线上缺陷': ['bug-records', 'quality_analysis_jira_bug_records'],
        '版本缺陷': ['version-defects', 'defects'],
        '实时质量分析': ['quality-report-live', 'live-version-analysis'],
        '配置': ['configs', 'project-environments', 'knowledge-repositories'],
        '知识库': ['knowledge', 'knowledge_objects', 'knowledge_relations', 'quality-knowledge-assistant'],
        '页面功能': ['page_function', 'assetPageFunction', 'tab', 'page', 'operation', 'component'],
        '接口关系': ['api', 'assetApiGraph', 'calls', 'reads', 'writes'],
        '库表字段': ['table', 'field', 'assetFields', 'db_table', 'field_name'],
        'ER图': ['er', 'assetErGraph', 'foreign_key', 'database_schema'],
        '幽灵代码': ['ghost', 'assetGhostCode', 'orphan_api', 'unlinked_file'],
        '代码调用': ['code', 'assetCodeGraph', 'ctags', 'semgrep', 'calls'],
    }
    for keyword, values in synonyms.items():
        if keyword in str(text or ''):
            tokens.update(value.lower() for value in values)
    return [token for token in tokens if token]


def get_space_for_query(payload, user=None):
    space_id = payload.get('space') or payload.get('space_id')
    if space_id:
        space = KnowledgeSpace.objects.filter(id=space_id).first()
        if space:
            return space
    knowledge_base = payload.get('knowledge_base') if isinstance(payload.get('knowledge_base'), dict) else {}
    key = str(knowledge_base.get('key') or payload.get('space_key') or '').strip()
    project_id = payload.get('project_id') or knowledge_base.get('project_id')
    project = Project.objects.filter(id=project_id).first() if project_id else None
    if project:
        project_space = KnowledgeSpace.objects.filter(project=project).order_by('-updated_at', '-id').first()
        if project_space:
            return project_space
        return ensure_default_knowledge_space(user=user, project=project)
    if key:
        space = KnowledgeSpace.objects.filter(key=key).first()
        if space:
            return space
    return ensure_default_knowledge_space(user=user, key=key or MANUAL_QUALITY_SPACE_KEY, name=MANUAL_QUALITY_NAME)


def score_object(obj, question, tokens):
    text = (obj.search_text or '').lower()
    name = (obj.name or '').lower()
    score = 0
    question_lower = str(question or '').lower()
    if question_lower and question_lower in text:
        score += 12
    for token in tokens:
        normalized = token.lower()
        if not normalized:
            continue
        if normalized == name:
            score += 10
        elif normalized in name:
            score += 6
        elif normalized in text:
            score += 2
    type_boost = {
        'tab': 2.0,
        'page': 2.0,
        'menu': 1.5,
        'function': 1.0,
        'operation': 1.0,
        'api': 0.5,
        'table': 0.5,
    }
    score += type_boost.get(obj.object_type, 0)
    return score


def serialize_node(obj, score=None):
    return {
        'id': obj.id,
        'key': obj.key,
        'type': obj.object_type,
        'label': obj.name,
        'summary': obj.summary,
        'roadmap_path': obj.roadmap_path or [],
        'page_path': obj.page_path,
        'tab_key': obj.tab_key,
        'component_path': obj.component_path,
        'api_path': obj.api_path,
        'db_table': obj.db_table,
        'field_name': obj.field_name,
        'source_type': obj.source_type,
        'source_ref': obj.source_ref,
        'metadata': obj.metadata or {},
        'score': score,
    }


def serialize_edge(relation):
    return {
        'id': relation.id,
        'source': relation.source_id,
        'target': relation.target_id,
        'source_key': relation.source.key,
        'target_key': relation.target.key,
        'type': relation.relation_type,
        'label': relation.label or relation.relation_type,
        'weight': relation.weight,
        'source_ref': relation.source_ref,
        'metadata': relation.metadata or {},
    }


def build_graph_payload(space, center_object_id=None, limit=120):
    limit = max(1, int(limit or 120))
    objects_qs = KnowledgeObject.objects.filter(space=space)
    if center_object_id:
        center_ids = {int(center_object_id)}
        neighbor_ids = set(KnowledgeRelation.objects.filter(space=space).filter(Q(source_id=center_object_id) | Q(target_id=center_object_id)).values_list('source_id', flat=True))
        neighbor_ids.update(KnowledgeRelation.objects.filter(space=space).filter(Q(source_id=center_object_id) | Q(target_id=center_object_id)).values_list('target_id', flat=True))
        objects_qs = objects_qs.filter(id__in=center_ids | neighbor_ids)
        objects = list(objects_qs.order_by('object_type', 'id')[:limit])
        object_ids = [obj.id for obj in objects]
        relations = list(
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id__in=object_ids, target_id__in=object_ids)
            .order_by('-weight', 'id')[:limit * 2]
        )
    else:
        relations = []
        object_ids = []
        seen_ids = set()
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space)
            .order_by('-weight', 'id')[:limit * 4]
        ):
            candidate_ids = [relation.source_id, relation.target_id]
            new_ids = [obj_id for obj_id in candidate_ids if obj_id not in seen_ids]
            if len(seen_ids) + len(new_ids) > limit:
                continue
            relations.append(relation)
            for obj_id in candidate_ids:
                if obj_id not in seen_ids:
                    seen_ids.add(obj_id)
                    object_ids.append(obj_id)
            if len(seen_ids) >= limit:
                break
        if len(object_ids) < limit:
            for obj_id in (
                objects_qs
                .exclude(id__in=object_ids)
                .order_by('object_type', 'id')
                .values_list('id', flat=True)[:limit - len(object_ids)]
            ):
                object_ids.append(obj_id)
        objects_by_id = {
            obj.id: obj
            for obj in objects_qs.filter(id__in=object_ids)
        }
        objects = [objects_by_id[obj_id] for obj_id in object_ids if obj_id in objects_by_id]
        object_id_set = set(objects_by_id)
        relations = [relation for relation in relations if relation.source_id in object_id_set and relation.target_id in object_id_set]
    return {
        'space': {'id': space.id, 'key': space.key, 'name': space.name},
        'nodes': [serialize_node(obj) for obj in objects],
        'edges': [serialize_edge(relation) for relation in relations],
    }


def query_knowledge_context(payload, user=None):
    question = str(payload.get('question') or payload.get('message') or '').strip()
    space = get_space_for_query(payload, user=user)
    asset_summary = build_query_asset_summary(space)
    if not KnowledgeObject.objects.filter(space=space).exists():
        context_payload = {
            'knowledge_evidence': {
                'space': {'id': space.id, 'key': space.key, 'name': space.name},
                'question': question,
                'matched_objects': [],
                'nodes': [],
                'edges': [],
                'roadmap_paths': [],
                'data_sources': [],
                'confidence_score': 0.0,
                'status': space.build_status,
                'message': space.build_status_message,
                'asset_summary': asset_summary,
            },
            'files': [
                {
                    'name': '知识库对象证据包.md',
                    'type': 'text/markdown',
                    'tag': '知识库证据',
                    'description': '当前知识库对象尚未完成建模，无法提供可靠证据。',
                    'content': '\n'.join([
                        '# 知识库对象证据包',
                        '',
                        f'用户问题：{question or "-"}',
                        '',
                        '当前知识库对象尚未完成 roadmap、组织结构图和关系图建模。',
                        '请先在【配置 -> Git/GitHub仓库配置】完成仓库与数据库 Schema 配置并触发索引。',
                    ]),
                },
            ],
        }
        trace = KnowledgeQueryTrace.objects.create(
            space=space,
            project=space.project,
            question=question or '(empty)',
            normalized_query='',
            matched_objects=[],
            evidence_nodes=[],
            evidence_edges=[],
            roadmap_paths=[],
            data_sources=[],
            context_payload=context_payload,
            confidence_score=0.0,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )
        return {
            'trace_id': trace.id,
            'space': {'id': space.id, 'key': space.key, 'name': space.name},
            'question': question,
            'confidence_score': 0.0,
            'matched_objects': [],
            'evidence': {
                'nodes': [],
                'edges': [],
                'roadmap_paths': [],
                'data_sources': [],
                'asset_summary': asset_summary,
            },
            'asset_summary': asset_summary,
            'context_payload': context_payload,
            'answer_contract': [
                '当前知识库对象尚未完成建模，不能编造操作步骤、页面路径、接口或数据。',
                '请先完成项目 Git/GitHub 仓库与数据库 Schema 配置，并等待索引状态变为已建模。',
            ],
        }
    tokens = tokenize_query(question)
    objects = list(KnowledgeObject.objects.filter(space=space).order_by('object_type', 'id')[:5000])
    scored = []
    for obj in objects:
        score = score_object(obj, question, tokens)
        if score > 0:
            scored.append((score, obj))
    scored.sort(key=lambda item: (-item[0], item[1].object_type, item[1].id))
    if not scored:
        fallback_types = ['module', 'menu', 'tab', 'page']
        scored = [(1, obj) for obj in objects if obj.object_type in fallback_types][:12]
    top = scored[:12]
    top_objects = [obj for _, obj in top]
    top_ids = [obj.id for obj in top_objects]
    relations = list(
        KnowledgeRelation.objects
        .select_related('source', 'target')
        .filter(space=space)
        .filter(Q(source_id__in=top_ids) | Q(target_id__in=top_ids))
        .order_by('-weight', 'id')[:80]
    )
    neighbor_ids = set(top_ids)
    for relation in relations:
        neighbor_ids.add(relation.source_id)
        neighbor_ids.add(relation.target_id)
    node_map = {
        obj.id: obj
        for obj in KnowledgeObject.objects.filter(space=space, id__in=neighbor_ids)
    }
    scores_by_id = {obj.id: score for score, obj in top}
    nodes = [serialize_node(node_map[obj_id], scores_by_id.get(obj_id)) for obj_id in node_map]
    edges = [serialize_edge(relation) for relation in relations if relation.source_id in node_map and relation.target_id in node_map]
    roadmap_paths = dedupe_jsonable([node.get('roadmap_path') for node in nodes if node.get('roadmap_path')])
    data_sources = build_data_sources(nodes, edges)
    matched = [serialize_node(obj, score) for score, obj in top]
    confidence = min(0.95, max(0.15, (top[0][0] / 20.0) if top else 0.15))
    evidence_content = build_evidence_markdown(question, matched, nodes, edges, roadmap_paths, data_sources, asset_summary)
    context_payload = {
        'knowledge_evidence': {
            'space': {'id': space.id, 'key': space.key, 'name': space.name},
            'question': question,
            'matched_objects': matched,
            'nodes': nodes,
            'edges': edges,
            'roadmap_paths': roadmap_paths,
            'data_sources': data_sources,
            'confidence_score': confidence,
            'asset_summary': asset_summary,
        },
        'files': [
            {
                'name': '知识库对象证据包.md',
                'type': 'text/markdown',
                'tag': '知识库证据',
                'description': '本轮回答必须优先引用的菜单、页面、操作项、接口和数据库表证据。',
                'content': evidence_content,
            },
        ],
    }
    knowledge_base = payload.get('knowledge_base') if isinstance(payload.get('knowledge_base'), dict) else {}
    project_id = payload.get('project_id') or knowledge_base.get('project_id')
    project = Project.objects.filter(id=project_id).first() if project_id else space.project
    trace = KnowledgeQueryTrace.objects.create(
        space=space,
        project=project,
        question=question or '(empty)',
        normalized_query=' '.join(tokens[:50]),
        matched_objects=matched,
        evidence_nodes=nodes,
        evidence_edges=edges,
        roadmap_paths=roadmap_paths,
        data_sources=data_sources,
        context_payload=context_payload,
        confidence_score=confidence,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    return {
        'trace_id': trace.id,
        'space': {'id': space.id, 'key': space.key, 'name': space.name},
        'question': question,
        'confidence_score': confidence,
        'matched_objects': matched,
        'evidence': {
            'nodes': nodes,
            'edges': edges,
            'roadmap_paths': roadmap_paths,
            'data_sources': data_sources,
            'asset_summary': asset_summary,
        },
        'asset_summary': asset_summary,
        'context_payload': context_payload,
        'answer_contract': [
            '只能基于证据包、roadmap、已索引代码、接口和数据库表回答。',
            '涉及操作步骤时，必须输出真实页面路径、菜单路径、按钮/操作项和字段。',
            '证据不足时必须说明缺少哪个知识库对象或数据来源，不得编造。',
        ],
    }


def dedupe_jsonable(items):
    result = []
    seen = set()
    for item in items:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_data_sources(nodes, edges):
    sources = []
    for node in nodes:
        ref = node.get('source_ref') or node.get('component_path') or node.get('api_path') or node.get('db_table')
        if not ref:
            continue
        sources.append({
            'type': node.get('source_type') or node.get('type'),
            'ref': ref,
            'label': node.get('label'),
        })
    for edge in edges:
        if edge.get('source_ref'):
            sources.append({'type': 'relation', 'ref': edge['source_ref'], 'label': edge.get('label')})
    return dedupe_jsonable(sources)[:40]


def build_query_asset_summary(space):
    type_counts = Counter(KnowledgeObject.objects.filter(space=space).values_list('object_type', flat=True))
    latest_run = (
        KnowledgeIndexRun.objects
        .filter(space=space)
        .order_by('-started_at', '-id')
        .first()
    )
    report = latest_run.report if latest_run else {}
    return {
        'object_count': sum(type_counts.values()),
        'relation_count': KnowledgeRelation.objects.filter(space=space).count(),
        'type_counts': dict(type_counts),
        'graph_tabs': [
            {'key': 'assetPageFunction', 'label': '页面功能图', 'graph_type': 'page_function'},
            {'key': 'assetPageApiTable', 'label': '页面功能-接口-库表字段图', 'graph_type': 'page_api_table'},
            {'key': 'assetApiGraph', 'label': '接口关系图', 'graph_type': 'api'},
            {'key': 'assetErGraph', 'label': '数据库ER图', 'graph_type': 'er'},
            {'key': 'assetCodeGraph', 'label': '代码调用图', 'graph_type': 'code'},
            {'key': 'assetGhostCode', 'label': '幽灵代码排查', 'section': 'ghost'},
            {'key': 'assetFields', 'label': '库表字段检索', 'section': 'fields'},
        ],
        'latest_run': {
            'id': latest_run.id,
            'status': latest_run.status,
            'object_count': latest_run.object_count,
            'relation_count': latest_run.relation_count,
            'finished_at': latest_run.finished_at.isoformat() if latest_run and latest_run.finished_at else '',
        } if latest_run else None,
        'code_scan': (report or {}).get('asset_scanner_code') or {},
        'database_scan': (report or {}).get('asset_scanner_database') or {},
    }


def build_evidence_markdown(question, matched, nodes, edges, roadmap_paths, data_sources, asset_summary=None):
    asset_summary = asset_summary or {}
    type_counts = asset_summary.get('type_counts') or {}
    lines = [
        '# 知识库对象证据包',
        '',
        f'用户问题：{question or "-"}',
        '',
        '## 回答约束',
        '- 回答必须基于本证据包中的菜单、页面、页签、操作项、字段、接口和数据库表。',
        '- 如果证据包未覆盖用户问题，必须明确说明缺少的知识库对象或业务数据，不得编造。',
        '- 页面操作步骤必须包含页面路径或菜单路径；业务数据必须说明接口或表来源。',
        '- 若问题涉及代码、接口、库表、字段、幽灵代码或ER图，优先使用项目资产图谱扫描结果。',
        '',
        '## 项目资产摘要',
        f'- 知识对象：{asset_summary.get("object_count") or 0}',
        f'- 关系：{asset_summary.get("relation_count") or 0}',
        f'- 页面/页签：{(type_counts.get("page") or 0) + (type_counts.get("tab") or 0)}',
        f'- 接口：{type_counts.get("api") or 0}',
        f'- 代码文件：{type_counts.get("file") or 0}',
        f'- 数据表：{type_counts.get("table") or 0}',
        f'- 字段：{type_counts.get("field") or 0}',
        '',
        '## 可用资产图谱',
        '- 页面功能图：菜单、页签、页面、功能、操作项、组件。',
        '- 页面功能-接口-库表字段图：页面功能、接口、代码文件、库表、字段。',
        '- 接口关系图：接口、调用代码、读写库表、字段引用。',
        '- 数据库ER图：数据库、库表、字段、外键。',
        '- 代码调用图：仓库、文件、类、函数、方法、接口、库表字段。',
        '- 幽灵代码排查：疑似无调用接口、组件、文件、库表字段。',
        '- 库表字段检索：字段归属、类型、备注、来源。',
        '',
        '## 命中对象',
    ]
    for item in matched[:12]:
        path = ' > '.join(item.get('roadmap_path') or [])
        details = []
        if item.get('page_path'):
            details.append(f'页面：{item["page_path"]}')
        if item.get('api_path'):
            details.append(f'接口：{item["api_path"]}')
        if item.get('db_table'):
            details.append(f'表：{item["db_table"]}')
        lines.append(f'- [{item.get("type")}] {item.get("label")}；{path or item.get("summary") or ""}；{"；".join(details)}')
    lines.extend(['', '## Roadmap路径'])
    for path in roadmap_paths[:20]:
        lines.append(f'- {" > ".join(path) if isinstance(path, list) else path}')
    lines.extend(['', '## 双链关系'])
    node_by_id = {node['id']: node for node in nodes}
    for edge in edges[:30]:
        source = node_by_id.get(edge.get('source'), {})
        target = node_by_id.get(edge.get('target'), {})
        lines.append(f'- {source.get("label", edge.get("source_key"))} --{edge.get("label") or edge.get("type")}--> {target.get("label", edge.get("target_key"))}')
    lines.extend(['', '## 数据来源'])
    for source in data_sources[:30]:
        lines.append(f'- {source.get("type")}: {source.get("label") or ""} {source.get("ref")}')
    return '\n'.join(lines)


def annotate_spaces_queryset(queryset):
    object_count = (
        KnowledgeObject.objects
        .filter(space=OuterRef('pk'))
        .values('space')
        .annotate(total=Count('pk'))
        .values('total')
    )
    relation_count = (
        KnowledgeRelation.objects
        .filter(space=OuterRef('pk'))
        .values('space')
        .annotate(total=Count('pk'))
        .values('total')
    )
    return queryset.annotate(
        object_count=Coalesce(Subquery(object_count, output_field=IntegerField()), 0),
        relation_count=Coalesce(Subquery(relation_count, output_field=IntegerField()), 0),
    )
