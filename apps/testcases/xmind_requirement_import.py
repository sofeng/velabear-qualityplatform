import json
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from apps.projects.models import Project
from apps.testcases.models import ManualTestCaseCategory, ManualTestCaseMindmap
from apps.users.models import User
from apps.versions.models import Version

from .mindmap_category_matching import match_mindmap_modules_to_categories
from .requirement_parsing import split_requirement_identifier_and_title


DEFAULT_MINDMAP_THEME = {
    'template': 'default',
    'theme': 'fresh-blue',
    'version': '1.4.43',
}
TYPE_RESOURCE_MAP = {
    'module': [],
    'case': ['C'],
    'requirement': ['R'],
    'testpoint': ['P'],
}
TERMINAL_STATUS_TEXT_MAP = {
    'pass': 'pass',
    'fail': 'fail',
}

ROOT_TITLE_PATTERN = re.compile(r'^(?P<version>\d{8}|\d{6})(?P<tester>.+?)测试分析$')


class XMindImportError(ValueError):
    """Raised when the XMind file cannot be imported with the expected rules."""


@dataclass(frozen=True)
class ImportContext:
    source_path: Path
    root_title: str
    version_code: str
    tester_name: str
    author: User
    version: Version
    project: Project
    category: ManualTestCaseCategory | None


@dataclass(frozen=True)
class RequirementMindmap:
    name: str
    jira_key: str
    requirement_title: str
    mindmap_data: dict


@dataclass(frozen=True)
class ParsedXMindImport:
    mode: str
    root_title: str
    requirement_items: list[RequirementMindmap]


def _normalize_node_text(value) -> str:
    text = str(value or '').strip()
    return text or '未命名节点'


def _strip_node_text(value) -> str:
    return str(value or '').strip()


def _set_node_type(data: dict, node_type: str):
    data['nodeType'] = node_type
    resource = list(TYPE_RESOURCE_MAP.get(node_type, []))
    if resource:
        data['resource'] = resource
    else:
        data.pop('resource', None)


def _clear_node_type(data: dict):
    data.pop('nodeType', None)
    data.pop('resource', None)


def strip_module_resource_markers(mindmap_data: dict):
    if not isinstance(mindmap_data, dict):
        return {}

    def walk(node):
        if not isinstance(node, dict):
            return

        data = node.get('data')
        if isinstance(data, dict) and data.get('nodeType') == 'module':
            data.pop('resource', None)

        for child in node.get('children') or []:
            walk(child)

    root = mindmap_data.get('root')
    if isinstance(root, dict):
        walk(root)
    return mindmap_data


def _normalize_match_value(value: str) -> str:
    return str(value or '').strip().replace(' ', '').lower()


def _pick_terminal_status(statuses: list[str]) -> str | None:
    if 'fail' in statuses:
        return 'fail'
    if 'pass' in statuses:
        return 'pass'
    return None


def build_project_module_name_set(project: Project | None) -> set[str]:
    if project is None:
        return set()

    normalized_names = set()
    for name in ManualTestCaseCategory.objects.filter(project=project).values_list('name', flat=True):
        normalized_name = _normalize_match_value(name)
        if normalized_name:
            normalized_names.add(normalized_name)
    return normalized_names


def _strip_namespace(tag: str) -> str:
    return str(tag or '').split('}', 1)[-1].lower()


def _find_direct_child(element, local_name: str):
    if element is None:
        return None
    for child in list(element):
        if _strip_namespace(child.tag) == local_name:
            return child
    return None


def _find_direct_children(element, local_name: str):
    if element is None:
        return []
    return [child for child in list(element) if _strip_namespace(child.tag) == local_name]


def _get_direct_text(element, local_name: str) -> str:
    child = _find_direct_child(element, local_name)
    return ''.join(child.itertext()) if child is not None else ''


def _get_attached_xml_topics(topic_element):
    children_element = _find_direct_child(topic_element, 'children')
    if children_element is None:
        return []

    topics_element = None
    for candidate in _find_direct_children(children_element, 'topics'):
        if str(candidate.attrib.get('type') or '').lower() == 'attached':
            topics_element = candidate
            break

    return _find_direct_children(topics_element, 'topic')


def _normalize_priority(marker_id: str):
    match = re.search(r'(\d+)', str(marker_id or ''))
    if not match:
        return None
    priority = int(match.group(1))
    if 1 <= priority <= 4:
        return priority - 1
    return None


def _convert_xml_topic(topic_element):
    node = {
        'data': {
            'text': _strip_node_text(_get_direct_text(topic_element, 'title')),
        }
    }

    notes_element = _find_direct_child(topic_element, 'notes')
    plain_note = _get_direct_text(notes_element, 'plain').strip()
    if plain_note:
        node['data']['note'] = plain_note

    labels_element = _find_direct_child(topic_element, 'labels')
    labels = [
        ''.join(label.itertext()).strip()
        for label in _find_direct_children(labels_element, 'label')
        if ''.join(label.itertext()).strip()
    ]
    if labels:
        node['data']['tags'] = labels

    children = [_convert_xml_topic(child) for child in _get_attached_xml_topics(topic_element)]
    if children:
        node['children'] = children

    return node


def _get_json_root_topic(xmind_data):
    if isinstance(xmind_data, list):
        for item in xmind_data:
            if isinstance(item, dict) and item.get('rootTopic'):
                return item['rootTopic']
        return None

    if isinstance(xmind_data, dict) and xmind_data.get('rootTopic'):
        return xmind_data['rootTopic']

    sheets = xmind_data.get('sheets') if isinstance(xmind_data, dict) else None
    if isinstance(sheets, list):
        for item in sheets:
            if isinstance(item, dict) and item.get('rootTopic'):
                return item['rootTopic']
    return None


def _convert_json_topic(topic: dict):
    node = {
        'data': {
            'text': _strip_node_text(topic.get('title')),
        }
    }

    labels = [str(label).strip() for label in topic.get('labels') or [] if str(label).strip()]
    if labels:
        node['data']['tags'] = labels

    notes = topic.get('notes') or {}
    plain_note = (
        (notes.get('plain') or {}).get('content')
        if isinstance(notes.get('plain'), dict)
        else None
    )
    if not plain_note and isinstance(notes.get('plain'), list):
        plain_note = next((item.get('content') for item in notes['plain'] if item.get('content')), None)
    if plain_note:
        node['data']['note'] = str(plain_note)

    for marker in topic.get('markers') or []:
        marker_id = str((marker or {}).get('markerId') or '')
        if 'priority' not in marker_id:
            continue
        priority = _normalize_priority(marker_id)
        if priority is not None:
            node['data']['priority'] = priority
            break

    attached_children = (((topic.get('children') or {}).get('attached')) or [])
    children = [_convert_json_topic(child) for child in attached_children if isinstance(child, dict)]
    if children:
        node['children'] = children

    return node


def _build_mindmap_data(root_node: dict) -> dict:
    return {
        'root': root_node,
        **DEFAULT_MINDMAP_THEME,
    }


def _normalize_requirement_subtree(
    node: dict,
    *,
    is_root: bool = False,
    module_name_set: set[str] | None = None,
):
    if not isinstance(node, dict):
        return None

    if module_name_set is None:
        module_name_set = set()

    data = node.get('data')
    if not isinstance(data, dict):
        data = {}
        node['data'] = data
    raw_text = _strip_node_text(data.get('text'))

    normalized_children = []
    terminal_statuses = []
    for child in node.get('children') or []:
        normalized_child = _normalize_requirement_subtree(
            child,
            is_root=False,
            module_name_set=module_name_set,
        )
        if normalized_child is not None:
            child_data = normalized_child.get('data')
            child_has_children = bool(normalized_child.get('children'))
            child_text = _normalize_match_value(
                child_data.get('text') if isinstance(child_data, dict) else ''
            )
            child_status = TERMINAL_STATUS_TEXT_MAP.get(child_text)
            if child_status and not child_has_children:
                terminal_statuses.append(child_status)
                continue
            normalized_children.append(normalized_child)

    if normalized_children:
        node['children'] = normalized_children
    else:
        node.pop('children', None)

    if not is_root and not normalized_children and not raw_text and not terminal_statuses:
        return None

    data['text'] = _normalize_node_text(raw_text)
    terminal_status = _pick_terminal_status(terminal_statuses)
    if terminal_status:
        data['status'] = terminal_status

    if is_root:
        _set_node_type(data, 'requirement')
    elif terminal_status:
        _set_node_type(data, 'testpoint')
    elif normalized_children:
        if _normalize_match_value(data.get('text')) in module_name_set:
            _set_node_type(data, 'module')
        else:
            _clear_node_type(data)
    else:
        _set_node_type(data, 'testpoint')
    return node


def normalize_requirement_mindmap_data(
    mindmap_data: dict,
    *,
    module_name_set: set[str] | None = None,
):
    if not isinstance(mindmap_data, dict):
        mindmap_data = {}

    root = mindmap_data.get('root')
    if not isinstance(root, dict):
        raise XMindImportError('脑图数据缺少有效的 root 节点')

    mindmap_data['root'] = _normalize_requirement_subtree(
        root,
        is_root=True,
        module_name_set=module_name_set,
    )
    for key, value in DEFAULT_MINDMAP_THEME.items():
        mindmap_data.setdefault(key, value)
    return mindmap_data


def _parse_xmind_root(path: Path):
    with zipfile.ZipFile(path) as archive:
        if 'content.json' in archive.namelist():
            data = json.loads(archive.read('content.json').decode('utf-8'))
            root_topic = _get_json_root_topic(data)
            if not root_topic:
                raise XMindImportError('未在 XMind content.json 中找到根节点')
            return 'json', root_topic

        if 'content.xml' in archive.namelist():
            xml_root = ElementTree.fromstring(archive.read('content.xml'))
            sheet_element = _find_direct_child(xml_root, 'sheet')
            topic_element = _find_direct_child(sheet_element, 'topic')
            if topic_element is None:
                raise XMindImportError('未在 XMind content.xml 中找到根节点')
            return 'xml', topic_element

    raise XMindImportError('不支持的 XMind 文件格式，缺少 content.json 或 content.xml')


def _parse_xmind_root_bytes(file_bytes: bytes):
    with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
        if 'content.json' in archive.namelist():
            data = json.loads(archive.read('content.json').decode('utf-8'))
            root_topic = _get_json_root_topic(data)
            if not root_topic:
                raise XMindImportError('未在 XMind content.json 中找到根节点')
            return 'json', root_topic

        if 'content.xml' in archive.namelist():
            xml_root = ElementTree.fromstring(archive.read('content.xml'))
            sheet_element = _find_direct_child(xml_root, 'sheet')
            topic_element = _find_direct_child(sheet_element, 'topic')
            if topic_element is None:
                raise XMindImportError('未在 XMind content.xml 中找到根节点')
            return 'xml', topic_element

    raise XMindImportError('不支持的 XMind 文件格式，缺少 content.json 或 content.xml')


def _iter_requirement_nodes(
    file_format: str,
    root_topic,
    *,
    module_name_set: set[str] | None = None,
) -> Iterable[RequirementMindmap]:
    if file_format == 'json':
        root_title = _normalize_node_text(root_topic.get('title'))
        children = (((root_topic.get('children') or {}).get('attached')) or [])
        for child in children:
            if not isinstance(child, dict):
                continue
            raw_name = _normalize_node_text(child.get('title'))
            jira_key, requirement_title = split_requirement_title(raw_name)
            yield RequirementMindmap(
                name=raw_name,
                jira_key=jira_key,
                requirement_title=requirement_title,
                mindmap_data=normalize_requirement_mindmap_data(
                    _build_mindmap_data(_convert_json_topic(child)),
                    module_name_set=module_name_set,
                ),
            )
        return root_title

    root_title = _normalize_node_text(_get_direct_text(root_topic, 'title'))
    for child in _get_attached_xml_topics(root_topic):
        raw_name = _normalize_node_text(_get_direct_text(child, 'title'))
        jira_key, requirement_title = split_requirement_title(raw_name)
        yield RequirementMindmap(
            name=raw_name,
            jira_key=jira_key,
            requirement_title=requirement_title,
            mindmap_data=normalize_requirement_mindmap_data(
                _build_mindmap_data(_convert_xml_topic(child)),
                module_name_set=module_name_set,
            ),
        )
    return root_title


def _get_root_title(file_format: str, root_topic) -> str:
    if file_format == 'json':
        return _normalize_node_text(root_topic.get('title'))
    return _normalize_node_text(_get_direct_text(root_topic, 'title'))


def _build_single_requirement_item(
    file_format: str,
    root_topic,
    *,
    module_name_set: set[str] | None = None,
) -> RequirementMindmap:
    raw_name = _get_root_title(file_format, root_topic)
    jira_key, requirement_title = split_requirement_title(raw_name)
    if file_format == 'json':
        root_node = _convert_json_topic(root_topic)
    else:
        root_node = _convert_xml_topic(root_topic)
    return RequirementMindmap(
        name=raw_name,
        jira_key=jira_key,
        requirement_title=requirement_title,
        mindmap_data=normalize_requirement_mindmap_data(
            _build_mindmap_data(root_node),
            module_name_set=module_name_set,
        ),
    )


def _parse_uploaded_xmind_root(file_obj):
    try:
        file_bytes = file_obj.read()
    finally:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

    if not file_bytes:
        raise XMindImportError('上传的 XMind 文件为空')

    try:
        return _parse_xmind_root_bytes(file_bytes)
    except zipfile.BadZipFile as exc:
        raise XMindImportError('上传文件不是合法的 XMind 压缩包') from exc
    except (json.JSONDecodeError, ElementTree.ParseError, UnicodeDecodeError) as exc:
        raise XMindImportError('XMind 内容解析失败，请检查文件是否损坏') from exc


def parse_uploaded_xmind_category_tree(file_obj) -> dict:
    """Parse an uploaded XMind into a plain title hierarchy for directory import."""
    file_format, root_topic = _parse_uploaded_xmind_root(file_obj)
    converted_root = (
        _convert_json_topic(root_topic)
        if file_format == 'json'
        else _convert_xml_topic(root_topic)
    )

    def normalize_category_node(node):
        data = node.get('data') if isinstance(node, dict) else {}
        children = node.get('children') if isinstance(node, dict) else []
        return {
            'name': _normalize_node_text((data or {}).get('text')),
            'children': [
                normalize_category_node(child)
                for child in (children or [])
                if isinstance(child, dict)
            ],
        }

    return normalize_category_node(converted_root)


def parse_uploaded_xmind(
    file_obj,
    *,
    project: Project | None = None,
    module_name_set: set[str] | None = None,
) -> ParsedXMindImport:
    file_format, root_topic = _parse_uploaded_xmind_root(file_obj)

    root_title = _get_root_title(file_format, root_topic)
    resolved_module_name_set = (
        module_name_set if module_name_set is not None else build_project_module_name_set(project)
    )

    try:
        parse_root_header(root_title)
    except XMindImportError:
        return ParsedXMindImport(
            mode='single_requirement',
            root_title=root_title,
            requirement_items=[
                _build_single_requirement_item(
                    file_format,
                    root_topic,
                    module_name_set=resolved_module_name_set,
                )
            ],
        )

    requirement_items = list(
        _iter_requirement_nodes(
            file_format,
            root_topic,
            module_name_set=resolved_module_name_set,
        )
    )
    if not requirement_items:
        raise XMindImportError('当前 XMind 根节点符合“版本号+用户名+测试分析”，但未找到任何需求子节点')

    return ParsedXMindImport(
        mode='split_requirements',
        root_title=root_title,
        requirement_items=requirement_items,
    )


def split_requirement_title(raw_title: str):
    return split_requirement_identifier_and_title(raw_title)


def parse_root_header(root_title: str):
    normalized_title = str(root_title or '').strip()
    match = ROOT_TITLE_PATTERN.match(normalized_title)
    if not match:
        raise XMindImportError(
            '根节点不符合“版本号+用户名+测试分析”规则，当前根节点为：'
            f'【{normalized_title or "<空>"}】'
        )
    return match.group('version'), match.group('tester').strip()


def _build_version_name_candidates(version_code: str):
    digits = ''.join(char for char in str(version_code or '') if char.isdigit())
    candidates = [digits]

    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) == 6:
        year, month, day = digits[:2], digits[2:4], digits[4:6]
        candidates.extend([
            f'{year}-{month}.{day}',
            f'{year}{month}{day}',
            f'{month}.{day}',
            f'{month}-{day}',
        ])

    deduped = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def resolve_version(version_code: str) -> Version:
    candidates = _build_version_name_candidates(version_code)
    versions = list(Version.objects.prefetch_related('projects').order_by('-id'))

    for candidate in candidates:
        version = next((item for item in versions if str(item.name).strip() == candidate), None)
        if version:
            return version

    for candidate in candidates:
        normalized_candidate = _normalize_match_value(candidate)
        version = next(
            (item for item in versions if normalized_candidate and normalized_candidate in _normalize_match_value(item.name)),
            None,
        )
        if version:
            return version

    raise XMindImportError(
        f'未找到与版本号【{version_code}】匹配的版本记录，已尝试：{", ".join(candidates)}'
    )


def resolve_author(tester_name: str) -> User:
    normalized_target = _normalize_match_value(tester_name)
    users = list(User.objects.all().order_by('id'))

    for user in users:
        candidates = {
            _normalize_match_value(user.username),
            _normalize_match_value(user.email.split('@', 1)[0] if user.email else ''),
            _normalize_match_value(user.first_name),
            _normalize_match_value(user.last_name),
            _normalize_match_value(f'{user.first_name}{user.last_name}'),
            _normalize_match_value(f'{user.last_name}{user.first_name}'),
            _normalize_match_value(getattr(user, 'full_name', '')),
        }
        if normalized_target in candidates:
            return user

    raise XMindImportError(f'未找到与测试人员【{tester_name}】匹配的平台用户')


def resolve_project(version: Version, project_id: int | None = None) -> Project:
    if project_id:
        project = Project.objects.filter(id=project_id).first()
        if not project:
            raise XMindImportError(f'未找到项目ID={project_id} 对应的项目')
        return project

    version_projects = list(version.projects.order_by('id'))
    if len(version_projects) == 1:
        return version_projects[0]
    if len(version_projects) > 1:
        raise XMindImportError(
            f'版本【{version.name}】关联了多个项目，请使用 --project-id 显式指定项目'
        )

    project = Project.objects.filter(name='物业通').order_by('id').first()
    if project:
        return project

    raise XMindImportError(f'版本【{version.name}】未关联项目，且未找到默认项目【物业通】')


def build_import_context(file_path: str | Path, project_id: int | None = None, category_id: int | None = None):
    source_path = Path(file_path).expanduser().resolve()
    if not source_path.exists():
        raise XMindImportError(f'文件不存在：{source_path}')

    file_format, raw_root = _parse_xmind_root(source_path)
    if file_format == 'json':
        root_title = _normalize_node_text(raw_root.get('title'))
    else:
        root_title = _normalize_node_text(_get_direct_text(raw_root, 'title'))

    version_code, tester_name = parse_root_header(root_title)
    author = resolve_author(tester_name)
    version = resolve_version(version_code)
    project = resolve_project(version, project_id=project_id)
    category = ManualTestCaseCategory.objects.filter(project=project, id=category_id).first() if category_id else (
        ManualTestCaseCategory.objects.filter(project=project, parent__isnull=True)
        .order_by('order', 'id')
        .first()
    )
    if category_id and category is None:
        raise XMindImportError(f'项目【{project.name}】下未找到目录ID={category_id}')

    requirement_items = list(
        _iter_requirement_nodes(
            file_format,
            raw_root,
            module_name_set=build_project_module_name_set(project),
        )
    )
    if not requirement_items:
        raise XMindImportError('当前 XMind 根节点下未找到任何需求节点')

    context = ImportContext(
        source_path=source_path,
        root_title=root_title,
        version_code=version_code,
        tester_name=tester_name,
        author=author,
        version=version,
        project=project,
        category=category,
    )
    return context, requirement_items


def import_requirement_mindmaps(
    context: ImportContext,
    requirement_items: list[RequirementMindmap],
    *,
    dry_run: bool = False,
):
    created = []
    skipped = []

    for item in requirement_items:
        existing = ManualTestCaseMindmap.objects.filter(
            project=context.project,
            version=context.version,
            author=context.author,
            name=item.name,
        ).order_by('id').first()
        if existing:
            skipped.append({'id': existing.id, 'name': existing.name, 'reason': 'duplicate'})
            continue

        if dry_run:
            created.append({'id': None, 'name': item.name, 'jira_key': item.jira_key})
            continue

        matched_mindmap_data, _match_summary = match_mindmap_modules_to_categories(
            context.project,
            item.mindmap_data,
        )
        record = ManualTestCaseMindmap.objects.create(
            project=context.project,
            name=item.name,
            description=(
                f'由 XMind 文件《{context.source_path.name}》按需求拆分导入；'
                f'原始根节点：{context.root_title}'
            ),
            category=context.category,
            version=context.version,
            mindmap_data=matched_mindmap_data,
            author=context.author,
        )
        created.append({'id': record.id, 'name': record.name, 'jira_key': item.jira_key})

    return {
        'context': context,
        'total': len(requirement_items),
        'created': created,
        'skipped': skipped,
        'dry_run': dry_run,
    }
