import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import quote

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.defects.models import Defect
from apps.projects.models import Project
from apps.testcases.models import DevSelfTestRecord, ManualTestCaseMindmap
from apps.users.models import Role
from apps.versions.models import Version

from .models import JiraBugRecord, JiraRequirementRecord, QualityAnalysisSettings
from .version_utils import jira_version_timeline_sort_key, normalize_jira_version


HIGH_PRIORITY_KEYWORDS = ('P0', 'P1', '高', '紧急', 'critical', 'high')
OPEN_DEFECT_STATUSES = {
    'new',
    'in_progress',
    'returned_pending',
    'customer_validation',
    'pending_requirement',
    'reopened',
}
HIGH_SEVERITY_VALUES = {'critical', 'high'}
TESTING_MINDMAP_SCOPE = ManualTestCaseMindmap.SCOPE_TESTING
OVERVIEW_WEEK_LABELS = ['日', '一', '二', '三', '四', '五', '六']
ONLINE_ANALYSIS_EMPTY_VERSION_LABEL = '未关联版本'
ONLINE_DEFECT_ALL_VERSION_EXCLUDED_STATUS = '已关闭问题'
ONLINE_DEFECT_ALL_VERSION_EXCLUDED_ROLE_NAMES = ('产品', '前端', '后端', '测试', '管理')
ONLINE_DEFECT_FIXED_STATUS_KEYWORDS = {
    'resolved',
    'regression_verified',
    'requirement_created',
    'closed',
    'done',
    'fixed',
    'finish',
    'finished',
    'completed',
    '已解决',
    '已关闭',
    '关闭',
    '完成',
    '修复',
}
ONLINE_BUG_FIX_RD_ESTIMATE_FIELDS = [
    '版本线上缺陷修复的研发预估工时',
    '线上缺陷修复研发预估工时',
    '线上缺陷修复的研发预估工时',
    '研发预估工时',
    '开发预估工时',
    '修复预估工时',
    '前端预估工时',
    '后端预估工时',
    'customfield_10749',
    'customfield_10748',
]
ONLINE_BUG_REGRESSION_TEST_ACTUAL_FIELDS = [
    '线上缺陷回归的测试实际工时',
    '线上缺陷回归测试实际工时',
    '回归测试实际工时',
    '测试实际投入工时',
    '测试实际工时',
    '测试预估工时',
    'customfield_10761',
]
ONLINE_BUG_ROOT_CAUSE_FIELDS = (
    'customfield_11102',
    'BUG产生根因',
    'BUG产生原因',
    '缺陷产生根因',
    '问题根因',
    '根因',
)
REQUIREMENT_DEV_ESTIMATE_HOUR_FIELDS = [
    '需求开发预估投入工时',
    '开发预估投入工时',
    '研发预估投入工时',
    '前端预估工时',
    '后端预估工时',
    'customfield_10749',
    'customfield_10748',
]
REQUIREMENT_TEST_ESTIMATE_HOUR_FIELDS = [
    '需求测试预估投入工时',
    '测试预估投入工时',
    '测试预估工时',
    'customfield_10761',
]
ONLINE_DEFECT_ANALYSIS_SERIES = [
    ('requirement_dev_estimated_hours', '需求开发预估投入工时'),
    ('requirement_test_estimated_hours', '需求测试预估投入工时'),
    ('bug_fix_rd_estimated_hours', '版本线上缺陷修复的研发预估工时'),
    ('bug_regression_test_actual_hours', '线上缺陷回归的测试实际工时'),
    ('bug_created_count', '线上缺陷创建量'),
    ('bug_fixed_count', '线上缺陷修复量'),
]
REQUIREMENT_TIMELINE_FIELD_CANDIDATES = {
    'frontend_start': ('frontend_start_time', 'frontend_start_date', 'customfield_10523'),
    'frontend_end': ('frontend_end_time', 'frontend_end_date', 'customfield_11017', 'customfield_11018'),
    'backend_start': ('backend_start_time', 'backend_start_date', 'customfield_10522'),
    'backend_end': ('backend_end_time', 'backend_end_date', 'customfield_11019', 'customfield_11018'),
}
REQUIREMENT_COMPLETED_STATUS_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in ('完结', '完成', '已完成', 'done', 'closed', 'resolved')
)
REQUIREMENT_ACTIVE_STATUS_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in ('研发中', '开发中', '处理中', '联调', '进行中', '测试中', '分析中')
)
REQUIREMENT_PENDING_STATUS_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in ('规划', '待', '未开始')
)
TESTING_STATUS_ORDER = ('not_run', 'pass', 'fail', 'block', 'not_test')
DEFECT_STATUS_ORDER = tuple(key for key, _ in Defect.STATUS_CHOICES)
DEFECT_STATUS_LABELS = dict(Defect.STATUS_CHOICES)
NO_GROUP_LABEL = '无组别'
MINDMAP_JIRA_KEY_PATTERN = re.compile(r'^\s*(?P<jira>[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)\b')
DIRECTOR_VIEW_BLOCK_PRIORITY_RULES = {
    'overview': [
        ('模块质量总表', 10),
        ('线上缺陷状态分布', 20),
        ('版本缺陷严重程度分布', 30),
        ('需求状态分布', 40),
    ],
    'requirements': [
        ('优先级 × 状态', 10),
        ('模块分布', 20),
        ('优先级分布', 30),
        ('状态分布', 40),
        ('组别分布', 50),
        ('产品经理分布', 60),
        ('关键信息', 70),
        ('产品经理视角', 80),
    ],
    'dev-self-test': [
        ('审核状态 × 执行状态', 10),
        ('模块自测覆盖', 20),
        ('自测执行状态分布', 30),
        ('自测审核状态分布', 40),
        ('前端开发视角', 50),
        ('后端开发视角', 60),
    ],
    'test-assets': [
        ('各版本测试点统计', 15),
        ('优先级 × 状态', 10),
        ('模块测试资产分布', 20),
        ('测试点状态分布', 30),
        ('测试用例状态分布', 40),
        ('测试用例优先级分布', 50),
        ('脑图资产分布', 60),
    ],
    'version-defects': [
        ('严重程度 × 状态', 10),
        ('模块缺陷分布', 20),
        ('严重程度分布', 30),
        ('状态分布', 40),
        ('缺陷关联情况', 50),
    ],
    'online-defects': [
        ('投入与修复统计', 5),
        ('根因 × 组别', 10),
        ('模块线上缺陷分布', 20),
        ('线上缺陷根因分析统计', 30),
        ('根因分布', 30),
        ('优先级分布', 40),
        ('状态分布', 50),
        ('测试人员视角', 60),
    ],
    'modules': [
        ('模块质量看板', 10),
        ('有需求无用例模块', 20),
    ],
    'people': [
        ('组别视角', 10),
        ('前端开发视角', 20),
        ('后端开发视角', 30),
        ('产品经理视角', 40),
    ],
    'workload': [
        ('模块工时分布', 10),
        ('测试人员工时视角', 20),
        ('产品经理工时视角', 30),
    ],
    'combinations': [
        ('模块风险链路', 10),
        ('严重程度 × 状态', 20),
        ('优先级 × 状态', 30),
        ('组别 × 阶段资产', 40),
    ],
}


def _normalize_text(value):
    return str(value or '').strip()


def _normalize_lower(value):
    return _normalize_text(value).casefold()


def _user_display_name(user):
    if not user:
        return ''
    full_name = _normalize_text(getattr(user, 'full_name', ''))
    if full_name:
        return full_name
    for field_name in ('username', 'email'):
        candidate = _normalize_text(getattr(user, field_name, ''))
        if candidate:
            return candidate
    return ''


def _dedupe_preserve_order(values):
    result = []
    seen = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _split_multi_value(value):
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return _dedupe_preserve_order(re.split(r'[\n,，、;；|]+', normalized))


def _coalesce(*values):
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            return normalized
    return ''


def _normalize_group_name(value):
    return _normalize_text(value) or NO_GROUP_LABEL


def _percent(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _safe_divide(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator, 2)


def _parse_numeric(value):
    normalized = _normalize_text(value)
    if not normalized:
        return 0.0
    matched = re.search(r'-?\d+(?:\.\d+)?', normalized)
    if not matched:
        return 0.0
    try:
        return float(matched.group())
    except ValueError:
        return 0.0


def _normalize_raw_lookup_key(value):
    return re.sub(r'\s+', '', _normalize_text(value)).casefold()


def _iter_raw_field_values(raw_fields):
    if not isinstance(raw_fields, dict):
        return

    labels = raw_fields.get('__field_labels') if isinstance(raw_fields.get('__field_labels'), dict) else {}
    for field_key, field_value in raw_fields.items():
        if str(field_key or '').startswith('__'):
            continue
        yield str(field_key or ''), str(labels.get(field_key) or labels.get(str(field_key)) or ''), field_value


def _sum_raw_numeric_fields(raw_fields, candidates):
    candidate_keys = {_normalize_raw_lookup_key(item) for item in candidates if _normalize_text(item)}
    total = 0.0

    for field_key, field_label, field_value in _iter_raw_field_values(raw_fields):
        lookup_keys = {
            _normalize_raw_lookup_key(field_key),
            _normalize_raw_lookup_key(field_label),
        }
        if lookup_keys & candidate_keys:
            total += _parse_numeric(field_value)

    return total


ONLINE_DEFECT_FIXED_STATUS = '\u5df2\u4ea4\u4ed8\u4e0a\u7ebf'


def _is_online_bug_fixed(status_value):
    return _normalize_text(status_value) == ONLINE_DEFECT_FIXED_STATUS


def _build_excluded_online_bug_creator_names_for_all_versions():
    excluded_roles = Role.objects.filter(name__in=ONLINE_DEFECT_ALL_VERSION_EXCLUDED_ROLE_NAMES).prefetch_related(
        'members',
        'role_memberships__user',
    )
    excluded_names = set()
    for role in excluded_roles:
        users = list(role.members.all())
        users.extend(membership.user for membership in role.role_memberships.all())
        for user in users:
            for name in (
                _user_display_name(user),
                getattr(user, 'username', ''),
                getattr(user, 'email', ''),
            ):
                normalized_name = _normalize_lower(name)
                if normalized_name:
                    excluded_names.add(normalized_name)
    return excluded_names


def _is_online_bug_excluded_for_all_versions(record, excluded_creator_names=None):
    if _normalize_text(getattr(record, 'status', '')) == ONLINE_DEFECT_ALL_VERSION_EXCLUDED_STATUS:
        return True

    normalized_creator = _normalize_lower(getattr(record, 'creator', ''))
    return bool(normalized_creator and normalized_creator in (excluded_creator_names or set()))


def filter_online_bugs_for_all_version_analysis(online_bugs, excluded_creator_names=None):
    if excluded_creator_names is None:
        excluded_creator_names = _build_excluded_online_bug_creator_names_for_all_versions()
    return [
        record
        for record in online_bugs or []
        if not _is_online_bug_excluded_for_all_versions(record, excluded_creator_names)
    ]


def _normalize_online_analysis_version(value):
    return normalize_jira_version(value) or ONLINE_ANALYSIS_EMPTY_VERSION_LABEL


def _format_number(value):
    if value is None:
        return '-'
    if isinstance(value, (int, float)):
        rounded = round(float(value), 2)
        if abs(rounded - int(rounded)) < 1e-9:
            return str(int(rounded))
        return f'{rounded:.2f}'.rstrip('0').rstrip('.')
    normalized = _normalize_text(value)
    return normalized or '-'


def _format_ratio(value):
    return f'{_format_number(value)}%'


def _is_high_priority(value):
    normalized = _normalize_text(value)
    if not normalized:
        return False
    upper_value = normalized.upper()
    return any(keyword.upper() in upper_value for keyword in HIGH_PRIORITY_KEYWORDS)


def _normalize_module_display(value):
    normalized = _normalize_text(value).replace('\\', '/')
    if not normalized:
        return ''
    parts = [item.strip() for item in re.split(r'\s*/\s*', normalized) if item.strip()]
    return ' / '.join(parts) if parts else normalized


def _module_entry_from_value(value):
    display = _normalize_module_display(value)
    if not display:
        return None
    module_key = display.split(' / ')[-1].strip() or display
    return {
        'key': module_key,
        'display': display,
    }


def _extract_module_entries(value):
    if isinstance(value, list):
        entries = []
        for item in value:
            if isinstance(item, dict):
                candidate = (
                    item.get('path')
                    or item.get('module_path')
                    or item.get('node_text')
                    or item.get('label')
                    or item.get('name')
                )
            else:
                candidate = item
            entry = _module_entry_from_value(candidate)
            if entry:
                entries.append(entry)
        unique_entries = []
        seen = set()
        for entry in entries:
            if entry['display'] in seen:
                continue
            seen.add(entry['display'])
            unique_entries.append(entry)
        return unique_entries

    return [
        entry
        for entry in (_module_entry_from_value(item) for item in _split_multi_value(value))
        if entry
    ]


def _build_distribution_rows(counter, *, limit=12):
    total = sum(counter.values())
    return [
        {
            'label': label,
            'count': count,
            'ratio': _percent(count, total),
        }
        for label, count in counter.most_common(limit)
    ]


def _build_columns(column_defs):
    columns = []
    for column in column_defs:
        columns.append(
            {
                'key': column[0],
                'label': column[1],
                'minWidth': column[2] if len(column) > 2 else 120,
                'align': column[3] if len(column) > 3 else 'center',
            }
        )
    return columns


def _make_metrics_block(items):
    return {
        'type': 'metrics',
        'items': items,
    }


def _make_distribution_block(title, counter, *, description='', limit=12):
    return {
        'type': 'distribution',
        'title': title,
        'description': description,
        'rows': _build_distribution_rows(counter, limit=limit),
    }


def _make_table_block(title, columns, rows, *, description=''):
    return {
        'type': 'table',
        'title': title,
        'description': description,
        'columns': _build_columns(columns),
        'rows': rows,
    }


def _make_multi_series_bar_block(title, categories, series, *, description=''):
    return {
        'type': 'multi-series-bar',
        'title': title,
        'description': description,
        'categories': list(categories or []),
        'series': [
            {
                'key': item.get('key') or item.get('name') or '',
                'name': item.get('name') or item.get('key') or '',
                'data': list(item.get('data') or []),
            }
            for item in series or []
            if item.get('key') or item.get('name')
        ],
    }


def _make_multi_series_line_block(title, categories, series, *, description=''):
    block = _make_multi_series_bar_block(title, categories, series, description=description)
    block['type'] = 'multi-series-line'
    return block


def _make_bullets_block(title, items, *, description=''):
    return {
        'type': 'bullets',
        'title': title,
        'description': description,
        'items': [item for item in items if _normalize_text(item)],
    }


def _resolve_director_block_priority(tab_key, block, index):
    block_type = _normalize_text(block.get('type'))
    if block_type == 'bullets':
        return 900 + index

    title = _normalize_text(block.get('title'))
    for keyword, priority in DIRECTOR_VIEW_BLOCK_PRIORITY_RULES.get(tab_key, []):
        if keyword in title:
            return priority

    return 500 + index


def _apply_director_view_block_order(tabs):
    for tab in tabs:
        blocks = list(tab.get('blocks') or [])
        tab_key = _normalize_text(tab.get('key'))
        tab['blocks'] = [
            block
            for _, _, block in sorted(
                (
                    _resolve_director_block_priority(tab_key, block, index),
                    index,
                    block,
                )
                for index, block in enumerate(blocks)
            )
        ]
    return tabs


def _build_matrix_block(title, items, row_resolver, column_resolver, *, row_label='维度', description='', limit_rows=12, limit_columns=8):
    matrix = defaultdict(Counter)
    row_totals = Counter()
    column_totals = Counter()

    for item in items:
        row_values = _dedupe_preserve_order(row_resolver(item))
        column_values = _dedupe_preserve_order(column_resolver(item))
        if not row_values or not column_values:
            continue
        for row_value in row_values:
            for column_value in column_values:
                matrix[row_value][column_value] += 1
                row_totals[row_value] += 1
                column_totals[column_value] += 1

    row_names = [label for label, _ in row_totals.most_common(limit_rows)]
    column_names = [label for label, _ in column_totals.most_common(limit_columns)]

    columns = [{'key': 'dimension', 'label': row_label, 'minWidth': 180, 'align': 'left'}]
    columns.append({'key': 'total', 'label': '合计', 'minWidth': 100, 'align': 'center'})

    column_key_map = {}
    for index, column_name in enumerate(column_names, start=1):
        key = f'c{index}'
        column_key_map[column_name] = key
        columns.append({'key': key, 'label': column_name, 'minWidth': 120, 'align': 'center'})

    rows = []
    for row_name in row_names:
        row = {
            'dimension': row_name,
            'total': row_totals[row_name],
        }
        for column_name in column_names:
            row[column_key_map[column_name]] = matrix[row_name].get(column_name, 0)
        rows.append(row)

    return {
        'type': 'matrix',
        'title': title,
        'description': description,
        'columns': columns,
        'rows': rows,
    }


def _walk_mindmap_nodes(node, *, mindmap, nodes, path_parts=None, module_parts=None):
    if not isinstance(node, dict):
        return

    path_parts = path_parts or []
    module_parts = module_parts or []

    data = node.get('data') or {}
    text = _normalize_text(data.get('text'))
    current_path = [*path_parts, text] if text else list(path_parts)
    current_module_parts = (
        [*module_parts, text]
        if data.get('nodeType') == 'module' and text
        else list(module_parts)
    )
    module_path = ' / '.join(current_module_parts)
    module_leaf = current_module_parts[-1] if current_module_parts else ''

    node_type = _normalize_text(data.get('nodeType'))
    common_payload = {
        'mindmap_id': mindmap.id,
        'mindmap_name': mindmap.name,
        'mindmap_author': _user_display_name(mindmap.author),
        'responsibility_group': _normalize_text(mindmap.responsibility_group),
        'frontend_developer': _user_display_name(mindmap.frontend_developer),
        'backend_developer': _user_display_name(mindmap.backend_developer),
        'version_name': _normalize_text(getattr(mindmap.version, 'name', '')),
        'category_name': _normalize_text(getattr(mindmap.category, 'name', '')),
        'node_id': _normalize_text(node.get('id')),
        'node_text': text,
        'path': ' / '.join(current_path),
        'module_path': module_path,
        'module_leaf': module_leaf,
        'priority': data.get('priority'),
        'status': _normalize_text(data.get('status')),
        'case_id': _normalize_text(data.get('caseId')),
        'tags': [str(tag).strip() for tag in (data.get('tags') or []) if str(tag).strip()],
        'updated_at': max(mindmap.created_at, mindmap.updated_at),
    }

    if node_type == 'module':
        nodes['modules'].append(common_payload)
    elif node_type == 'case':
        nodes['cases'].append(common_payload)
    elif node_type == 'testpoint':
        nodes['testpoints'].append(common_payload)

    for child in node.get('children') or []:
        _walk_mindmap_nodes(
            child,
            mindmap=mindmap,
            nodes=nodes,
            path_parts=current_path,
            module_parts=current_module_parts,
        )


def _build_live_dev_self_test_items(mindmaps):
    mindmap_ids = [mindmap.id for mindmap in mindmaps]
    record_map = {
        (record.mindmap_id, str(record.node_id)): record
        for record in DevSelfTestRecord.objects.filter(mindmap_id__in=mindmap_ids).select_related(
            'mindmap',
            'mindmap__frontend_developer',
            'mindmap__backend_developer',
        )
    }

    items = []
    seen_keys = set()

    def collect_live_testpoints(node, *, mindmap, node_path=None):
        if not isinstance(node, dict):
            return

        current_path = [*(node_path or []), node]
        data = node.get('data') or {}
        node_type = _normalize_text(data.get('nodeType'))
        try:
            priority_value = int(data.get('priority') or 1)
        except (TypeError, ValueError):
            priority_value = 1

        if node_type == 'testpoint' and priority_value == 1:
            module_parts = []
            for current_node in current_path[:-1]:
                current_data = current_node.get('data') or {}
                current_text = _normalize_text(current_data.get('text'))
                if current_data.get('nodeType') == 'module' and current_text:
                    module_parts.append(current_text)

            module_path = ' / '.join(module_parts)
            live_item = {
                'id': _normalize_text(node.get('id')),
                'mindmap_id': mindmap.id,
                'mindmap_name': mindmap.name,
                'module_path': module_path,
                'module_leaf': module_parts[-1] if module_parts else '',
                'testpoint': _normalize_text(data.get('text')),
                'priority': priority_value,
                'status': _normalize_text(data.get('status')) or 'not_run',
                'audit_status': 'pending',
                'responsibility_group': _normalize_text(mindmap.responsibility_group),
                'frontend_developer': _user_display_name(mindmap.frontend_developer),
                'backend_developer': _user_display_name(mindmap.backend_developer),
                'updated_at': max(mindmap.created_at, mindmap.updated_at),
            }
            key = (mindmap.id, live_item['id'])
            record = record_map.get(key)
            if record and _normalize_text(record.audit_status) == 'approved':
                live_item.update(
                    {
                        'module_path': _normalize_text(record.module_path) or module_path,
                        'module_leaf': (_normalize_text(record.module_path).split(' / ')[-1] if _normalize_text(record.module_path) else live_item['module_leaf']),
                        'testpoint': _normalize_text(record.testpoint) or live_item['testpoint'],
                        'priority': record.priority or live_item['priority'],
                        'status': _normalize_text(record.status) or live_item['status'],
                        'audit_status': 'approved',
                        'updated_at': record.updated_at,
                    }
                )
            elif record:
                live_item['audit_status'] = _normalize_text(record.audit_status) or 'pending'

            items.append(live_item)
            seen_keys.add(key)

        for child in node.get('children') or []:
            collect_live_testpoints(child, mindmap=mindmap, node_path=current_path)

    for mindmap in mindmaps:
        root = (mindmap.mindmap_data or {}).get('root')
        collect_live_testpoints(root, mindmap=mindmap)

    for key, record in record_map.items():
        if key in seen_keys or _normalize_text(record.audit_status) != 'approved':
            continue
        module_path = _normalize_text(record.module_path)
        items.append(
            {
                'id': _normalize_text(record.node_id),
                'mindmap_id': record.mindmap_id,
                'mindmap_name': record.mindmap.name,
                'module_path': module_path,
                'module_leaf': module_path.split(' / ')[-1] if module_path else _normalize_text(record.module),
                'testpoint': _normalize_text(record.testpoint),
                'priority': record.priority or 1,
                'status': _normalize_text(record.status) or 'not_run',
                'audit_status': 'approved',
                'responsibility_group': _normalize_text(record.mindmap.responsibility_group),
                'frontend_developer': _user_display_name(record.mindmap.frontend_developer),
                'backend_developer': _user_display_name(record.mindmap.backend_developer),
                'updated_at': record.updated_at,
            }
        )

    return items


def _resolve_accessible_project(user, project_id):
    accessible_projects = Project.objects.all().distinct()
    if not project_id:
        return None

    project = accessible_projects.filter(id=project_id).first()
    if not project:
        raise ValueError('未找到当前用户可访问的项目')
    return project


def _collect_workspace_context(report, *, user, project_id=None):
    normalized_version = normalize_jira_version(report.version)
    project = _resolve_accessible_project(user, project_id)

    version_queryset = Version.objects.filter(name=normalized_version)
    if project:
        version_queryset = version_queryset.filter(projects=project)
    version_ids = list(version_queryset.values_list('id', flat=True))

    mindmaps = (
        ManualTestCaseMindmap.objects.filter(
            version_id__in=version_ids,
            mindmap_scope=TESTING_MINDMAP_SCOPE,
        )
        .select_related('version', 'category', 'author', 'frontend_developer', 'backend_developer')
        .order_by('-updated_at')
    )
    if project:
        mindmaps = mindmaps.filter(project=project)
    mindmaps = list(mindmaps)

    node_buckets = {
        'modules': [],
        'cases': [],
        'testpoints': [],
    }
    for mindmap in mindmaps:
        root = (mindmap.mindmap_data or {}).get('root')
        _walk_mindmap_nodes(root, mindmap=mindmap, nodes=node_buckets)

    dev_self_tests = _build_live_dev_self_test_items(mindmaps)

    defects = (
        Defect.objects.filter(
            version__name=normalized_version,
            record_type=Defect.RECORD_TYPE_DEFECT,
        )
        .select_related('project', 'version', 'created_by', 'resolved_by', 'closed_by')
        .prefetch_related('assignees')
        .order_by('-updated_at', '-id')
    )
    if project:
        defects = defects.filter(project=project)
    defects = list(defects)

    requirements = list(
        JiraRequirementRecord.objects.filter(version=normalized_version)
        .select_related('config')
        .order_by('-synced_at', 'row_index', 'issue_key')
    )
    online_bugs = list(
        JiraBugRecord.objects.filter(version=normalized_version)
        .select_related('config')
        .order_by('-synced_at', 'row_index', 'issue_key')
    )

    return {
        'project': project,
        'version': normalized_version,
        'version_ids': version_ids,
        'mindmaps': mindmaps,
        'modules': node_buckets['modules'],
        'cases': node_buckets['cases'],
        'testpoints': node_buckets['testpoints'],
        'dev_self_tests': dev_self_tests,
        'version_defects': defects,
        'requirements': requirements,
        'online_bugs': online_bugs,
    }


def _build_online_defect_effort_buckets(requirements, online_bugs):
    bucket_map = {}
    version_latest_time = {}

    def ensure_bucket(version):
        version_label = _normalize_online_analysis_version(version)
        if version_label not in bucket_map:
            bucket_map[version_label] = {key: 0 for key, _ in ONLINE_DEFECT_ANALYSIS_SERIES}
        return version_label

    for record in requirements or []:
        version_label = ensure_bucket(getattr(record, 'version', ''))
        raw_fields = getattr(record, 'raw_fields', None) or {}
        bucket_map[version_label]['requirement_dev_estimated_hours'] += _sum_raw_numeric_fields(
            raw_fields,
            REQUIREMENT_DEV_ESTIMATE_HOUR_FIELDS,
        )
        bucket_map[version_label]['requirement_test_estimated_hours'] += _sum_raw_numeric_fields(
            raw_fields,
            REQUIREMENT_TEST_ESTIMATE_HOUR_FIELDS,
        )
        synced_at = getattr(record, 'synced_at', None)
        if synced_at:
            version_latest_time[version_label] = max(version_latest_time.get(version_label, synced_at), synced_at)

    for record in online_bugs or []:
        version_label = ensure_bucket(getattr(record, 'version', ''))
        raw_fields = getattr(record, 'raw_fields', None) or {}
        bucket_map[version_label]['bug_created_count'] += 1
        if _is_online_bug_fixed(getattr(record, 'status', '')):
            bucket_map[version_label]['bug_fixed_count'] += 1
        bucket_map[version_label]['bug_fix_rd_estimated_hours'] += _sum_raw_numeric_fields(
            raw_fields,
            ONLINE_BUG_FIX_RD_ESTIMATE_FIELDS,
        )
        bucket_map[version_label]['bug_regression_test_actual_hours'] += _sum_raw_numeric_fields(
            raw_fields,
            ONLINE_BUG_REGRESSION_TEST_ACTUAL_FIELDS,
        )
        synced_at = getattr(record, 'synced_at', None)
        if synced_at:
            version_latest_time[version_label] = max(version_latest_time.get(version_label, synced_at), synced_at)

    return bucket_map, version_latest_time


def _build_online_defect_effort_block(requirements, online_bugs, *, categories=None, title='线上缺陷投入与修复统计', description=''):
    bucket_map, version_latest_time = _build_online_defect_effort_buckets(requirements, online_bugs)
    if categories is None:
        fallback_time = timezone.now() - timedelta(days=36500)
        categories = sorted(
            bucket_map.keys(),
            key=lambda item: jira_version_timeline_sort_key(
                item,
                version_latest_time.get(item),
                fallback_time,
            ),
        )

    return _make_multi_series_line_block(
        title,
        categories,
        [
            {
                'key': key,
                'name': name,
                'data': [
                    round(float(bucket_map.get(category, {}).get(key, 0) or 0), 2)
                    for category in categories
                ],
            }
            for key, name in ONLINE_DEFECT_ANALYSIS_SERIES
        ],
        description=description,
    )


def _build_all_version_test_asset_snapshot(project=None):
    mindmaps = (
        ManualTestCaseMindmap.objects.filter(mindmap_scope=TESTING_MINDMAP_SCOPE)
        .select_related('version', 'category', 'author', 'frontend_developer', 'backend_developer', 'project')
        .order_by('-updated_at', '-id')
    )
    if project:
        mindmaps = mindmaps.filter(project=project)
    mindmaps = list(mindmaps)

    node_buckets = {
        'modules': [],
        'cases': [],
        'testpoints': [],
    }
    for mindmap in mindmaps:
        root = (mindmap.mindmap_data or {}).get('root')
        _walk_mindmap_nodes(root, mindmap=mindmap, nodes=node_buckets)

    version_testpoint_counts = Counter()
    version_case_counts = Counter()
    version_mindmap_counts = Counter()
    version_latest_time = {}

    def resolve_version_label(value):
        return normalize_jira_version(value) or '未关联版本'

    def touch_version(label, updated_at):
        if updated_at:
            version_latest_time[label] = max(version_latest_time.get(label, updated_at), updated_at)

    for mindmap in mindmaps:
        label = resolve_version_label(getattr(getattr(mindmap, 'version', None), 'name', ''))
        version_mindmap_counts[label] += 1
        touch_version(label, max(mindmap.created_at, mindmap.updated_at))

    for item in node_buckets['cases']:
        label = resolve_version_label(item.get('version_name'))
        version_case_counts[label] += 1
        touch_version(label, item.get('updated_at'))

    for item in node_buckets['testpoints']:
        label = resolve_version_label(item.get('version_name'))
        version_testpoint_counts[label] += 1
        touch_version(label, item.get('updated_at'))

    fallback_time = timezone.now() - timedelta(days=36500)
    categories = sorted(
        version_testpoint_counts.keys(),
        key=lambda item: jira_version_timeline_sort_key(
            item,
            version_latest_time.get(item),
            fallback_time,
        ),
    )

    return {
        'mindmaps': mindmaps,
        'modules': node_buckets['modules'],
        'cases': node_buckets['cases'],
        'testpoints': node_buckets['testpoints'],
        'categories': categories,
        'version_testpoint_counts': version_testpoint_counts,
        'version_case_counts': version_case_counts,
        'version_mindmap_counts': version_mindmap_counts,
        'block': _make_multi_series_bar_block(
            '各版本测试点统计',
            categories,
            [
                {
                    'key': 'testpoint_count',
                    'name': '测试点数量',
                    'data': [version_testpoint_counts.get(category, 0) for category in categories],
                },
            ],
            description='按测试脑图中 testpoint 节点关联版本统计，用于观察各版本测试点资产沉淀情况。',
        ),
    }


def build_all_versions_online_defect_analysis_payload(*, user, project_id=None, months=12):
    project = _resolve_accessible_project(user, project_id)
    since = timezone.now() - timedelta(days=365)
    requirements = list(
        JiraRequirementRecord.objects.filter(synced_at__gte=since)
        .select_related('config')
        .order_by('-synced_at', 'row_index', 'issue_key')
    )
    online_bugs = list(
        JiraBugRecord.objects.filter(synced_at__gte=since)
        .select_related('config')
        .order_by('-synced_at', 'row_index', 'issue_key')
    )
    online_bugs = filter_online_bugs_for_all_version_analysis(online_bugs)
    normalized_online_bugs = _normalize_bug_records(online_bugs)
    online_bug_root_cause_counter = Counter(
        item.get('root_cause') or '未填写'
        for item in normalized_online_bugs
    )
    fixed_online_bug_count = sum(1 for record in online_bugs if _is_online_bug_fixed(getattr(record, 'status', '')))
    remaining_online_bug_count = max(len(online_bugs) - fixed_online_bug_count, 0)
    test_asset_snapshot = _build_all_version_test_asset_snapshot(project)

    block = _build_online_defect_effort_block(
        requirements,
        online_bugs,
        title='近12个月线上缺陷投入与修复统计',
        description='版本选择全部时，按近12个月所有同步版本统计。需求工时来自JIRA需求数据的前端、后端、测试预估工时；线上缺陷工时来自JIRA线上BUG原始字段。',
    )
    online_root_cause_block = _make_distribution_block(
        '线上缺陷根因分析统计',
        online_bug_root_cause_counter,
        description='按线上缺陷字段“BUG产生根因”统计近12个月线上缺陷根因分布。',
    )
    categories = block.get('categories') or []
    testpoint_categories = test_asset_snapshot['categories']

    return {
        'report_id': None,
        'report_version': '全部版本',
        'project': {
            'id': getattr(project, 'id', None),
            'name': _normalize_text(getattr(project, 'name', '')) if project else '',
        },
        'jira_browse_prefix': QualityAnalysisSettings.get_solo().jira_browse_prefix,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'requirements': len(requirements),
            'cases': len(test_asset_snapshot['cases']),
            'testpoints': len(test_asset_snapshot['testpoints']),
            'version_defects': 0,
            'online_defects': len(online_bugs),
            'modules': len({_normalize_online_analysis_version(getattr(record, 'version', '')) for record in online_bugs}),
            'groups': 0,
            'scope_mode': 'all',
            'since': since.isoformat(),
        },
        'tabs': [
            {
                'key': 'online-defects',
                'label': '线上缺陷',
                'metrics': [
                    {'label': '统计版本', 'value': len(categories), 'description': '近12个月有同步数据的版本'},
                    {'label': '需求记录', 'value': len(requirements), 'description': '近12个月JIRA需求记录'},
                    {'label': '线上缺陷', 'value': len(online_bugs), 'description': '近12个月JIRA线上BUG'},
                    {'label': '累计修复缺陷', 'value': fixed_online_bug_count, 'description': '近12个月已修复线上缺陷'},
                    {'label': '剩余缺陷', 'value': remaining_online_bug_count, 'description': '线上缺陷总数减累计修复缺陷'},
                ],
                'blocks': [block, online_root_cause_block],
            },
            {
                'key': 'test-assets',
                'label': '测试资产',
                'metrics': [
                    {'label': '统计版本', 'value': len(testpoint_categories), 'description': '存在测试点资产的版本数'},
                    {'label': '测试脑图', 'value': len(test_asset_snapshot['mindmaps']), 'description': '测试脑图总数'},
                    {'label': '测试用例', 'value': len(test_asset_snapshot['cases']), 'description': 'case节点总数'},
                    {'label': '测试点', 'value': len(test_asset_snapshot['testpoints']), 'description': 'testpoint节点总数'},
                ],
                'blocks': [test_asset_snapshot['block']],
            },
        ],
    }


def _normalize_raw_field_value(value):
    if isinstance(value, (list, tuple)):
        return ' / '.join(
            item
            for item in (_normalize_raw_field_value(item) for item in value)
            if item
        )

    if isinstance(value, dict):
        return _normalize_raw_field_value(
            value.get('name')
            or value.get('value')
            or value.get('label')
            or value.get('displayName')
            or ''
        )

    return _normalize_text(value)


def _resolve_raw_field_value(raw_fields, field_keys):
    raw_fields = raw_fields or {}
    for field_key in field_keys:
        resolved_value = _normalize_raw_field_value(raw_fields.get(field_key))
        if resolved_value:
            return resolved_value

    candidate_keys = {
        _normalize_raw_lookup_key(field_key)
        for field_key in field_keys
        if _normalize_text(field_key)
    }
    for field_key, field_label, field_value in _iter_raw_field_values(raw_fields):
        lookup_keys = {
            _normalize_raw_lookup_key(field_key),
            _normalize_raw_lookup_key(field_label),
        }
        if lookup_keys & candidate_keys:
            resolved_value = _normalize_raw_field_value(field_value)
            if resolved_value:
                return resolved_value
    return ''


def _parse_overview_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    normalized_value = _normalize_text(value)
    if not normalized_value:
        return None

    parsed_datetime = parse_datetime(normalized_value)
    if parsed_datetime:
        return parsed_datetime.date()

    parsed_day = parse_date(normalized_value)
    if parsed_day:
        return parsed_day

    if 'T' in normalized_value:
        parsed_day = parse_date(normalized_value.split('T', 1)[0])
        if parsed_day:
            return parsed_day

    return None


def _resolve_requirement_status_state(status):
    normalized_status = _normalize_text(status)

    if any(pattern.search(normalized_status) for pattern in REQUIREMENT_COMPLETED_STATUS_PATTERNS):
        return 'completed'
    if any(keyword in normalized_status for keyword in ('\u5b8c\u6210', '\u5df2\u5b8c\u6210', '\u5b8c\u7ed3')):
        return 'completed'
    if any(pattern.search(normalized_status) for pattern in REQUIREMENT_ACTIVE_STATUS_PATTERNS):
        return 'active'
    if any(
        keyword in normalized_status
        for keyword in (
            '\u7814\u53d1\u4e2d',
            '\u5f00\u53d1\u4e2d',
            '\u5904\u7406\u4e2d',
            '\u8054\u8c03',
            '\u8fdb\u884c\u4e2d',
            '\u6d4b\u8bd5\u4e2d',
            '\u5206\u6790\u4e2d',
        )
    ):
        return 'active'
    if any(pattern.search(normalized_status) for pattern in REQUIREMENT_PENDING_STATUS_PATTERNS):
        return 'pending'
    if any(keyword in normalized_status for keyword in ('\u89c4\u5212', '\u5f85', '\u672a\u5f00\u59cb')):
        return 'pending'
    return 'active' if normalized_status else 'pending'


def _build_requirement_task(start_value, end_value, status_state):
    start_date = _parse_overview_date(start_value)
    end_date = _parse_overview_date(end_value)

    if not start_date and not end_date:
        return None
    if not start_date and end_date:
        start_date = end_date
    if not end_date:
        end_date = timezone.localdate() if status_state == 'active' else start_date
    if end_date < start_date:
        start_date, end_date = end_date, start_date

    return {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'startLabel': start_date.isoformat(),
        'endLabel': end_date.isoformat(),
        'spanDays': (end_date - start_date).days + 1,
    }


def _build_requirement_fallback_sort_date(record):
    raw_created_date = _parse_overview_date((getattr(record, 'raw_fields', None) or {}).get('created'))
    if raw_created_date:
        return raw_created_date

    for field_name in ('created_at', 'synced_at', 'updated_at'):
        field_value = _parse_overview_date(getattr(record, field_name, None))
        if field_value:
            return field_value

    return timezone.localdate()


def _extract_mindmap_issue_keys(mindmaps):
    issue_keys = set()
    for mindmap in mindmaps:
        requirement_key = _extract_mindmap_requirement_key(mindmap)
        if requirement_key:
            issue_keys.add(requirement_key)
    return issue_keys


def _scope_requirement_records_for_project(requirements, mindmaps):
    issue_keys = _extract_mindmap_issue_keys(mindmaps)
    if not issue_keys:
        return []

    filtered_requirements = [
        record
        for record in requirements
        if _normalize_text(getattr(record, 'issue_key', '')).upper() in issue_keys
    ]
    return filtered_requirements


def _extract_mindmap_requirement_key(mindmap):
    explicit_requirement_key = _normalize_text(getattr(mindmap, 'requirement_key', '')).upper()
    if explicit_requirement_key:
        return explicit_requirement_key

    match = MINDMAP_JIRA_KEY_PATTERN.match(_normalize_text(getattr(mindmap, 'name', '')))
    if match:
        return match.group('jira').upper()

    return ''


def _build_scoped_requirement_lookup(context):
    requirements = list(context.get('requirements') or [])
    return {
        _normalize_text(getattr(record, 'issue_key', '')).upper(): record
        for record in requirements
        if _normalize_text(getattr(record, 'issue_key', ''))
    }


def _build_requirement_overview_items(context):
    requirements = list(context['requirements'])

    items = []
    for record in requirements:
        raw_fields = getattr(record, 'raw_fields', None) or {}
        status_text = _normalize_text(getattr(record, 'status', ''))
        status_state = _resolve_requirement_status_state(status_text)
        frontend_task = _build_requirement_task(
            _resolve_raw_field_value(raw_fields, REQUIREMENT_TIMELINE_FIELD_CANDIDATES['frontend_start']),
            _resolve_raw_field_value(raw_fields, REQUIREMENT_TIMELINE_FIELD_CANDIDATES['frontend_end']),
            status_state,
        )
        backend_task = _build_requirement_task(
            _resolve_raw_field_value(raw_fields, REQUIREMENT_TIMELINE_FIELD_CANDIDATES['backend_start']),
            _resolve_raw_field_value(raw_fields, REQUIREMENT_TIMELINE_FIELD_CANDIDATES['backend_end']),
            status_state,
        )
        task_start_dates = [
            _parse_overview_date(task.get('startDate'))
            for task in (frontend_task, backend_task)
            if task
        ]
        sort_date = min(task_start_dates) if task_start_dates else _build_requirement_fallback_sort_date(record)

        items.append(
            {
                'id': getattr(record, 'id', None) or _normalize_text(getattr(record, 'issue_key', '')),
                'issue_key': _normalize_text(getattr(record, 'issue_key', '')) or '-',
                'issueKey': _normalize_text(getattr(record, 'issue_key', '')) or '-',
                'summary': _normalize_text(getattr(record, 'summary', '')),
                'group_name': _normalize_group_name(getattr(record, 'group_name', '')),
                'groupName': _normalize_group_name(getattr(record, 'group_name', '')),
                'frontend_developer': _resolve_raw_field_value(raw_fields, ('customfield_10743',)),
                'frontendDeveloper': _resolve_raw_field_value(raw_fields, ('customfield_10743',)),
                'backend_developer': _coalesce(
                    getattr(record, 'backend_developer', ''),
                    _resolve_raw_field_value(raw_fields, ('customfield_10741',)),
                    getattr(record, 'tester', ''),
                    _resolve_raw_field_value(raw_fields, ('customfield_10222',)),
                ),
                'backendDeveloper': _coalesce(
                    getattr(record, 'backend_developer', ''),
                    _resolve_raw_field_value(raw_fields, ('customfield_10741',)),
                    getattr(record, 'tester', ''),
                    _resolve_raw_field_value(raw_fields, ('customfield_10222',)),
                ),
                'status': status_text,
                'statusText': status_text,
                'statusState': status_state,
                'frontendTask': frontend_task,
                'backendTask': backend_task,
                'sortDate': sort_date.isoformat() if sort_date else '',
                'hasTimeline': bool(frontend_task or backend_task),
            }
        )

    items.sort(key=lambda item: (item.get('sortDate') or '9999-12-31', item.get('issueKey') or ''))
    return items


def _create_empty_status_counts():
    return {status_key: 0 for status_key in TESTING_STATUS_ORDER}


def _normalize_testing_status(value):
    normalized_value = _normalize_text(value).casefold()
    return normalized_value if normalized_value in TESTING_STATUS_ORDER else 'not_run'


def _build_testing_segments(status_counts):
    segments = []
    offset = 0
    for status_key in TESTING_STATUS_ORDER:
        count = int(status_counts.get(status_key) or 0)
        if not count:
            continue
        segments.append(
            {
                'key': status_key,
                'count': count,
                'offset': offset,
            }
        )
        offset += count
    return segments


def _resolve_testing_progress_state(status_counts):
    total_count = sum(int(status_counts.get(status_key) or 0) for status_key in TESTING_STATUS_ORDER)
    not_test_count = int(status_counts.get('not_test') or 0)
    effective_total = total_count - not_test_count
    if total_count and effective_total == 0:
        return 'not_test'
    if not effective_total or int(status_counts.get('not_run') or 0) == effective_total:
        return 'pending'
    if int(status_counts.get('fail') or 0) > 0 or int(status_counts.get('block') or 0) > 0:
        return 'risk'
    if int(status_counts.get('pass') or 0) == effective_total:
        return 'completed'
    return 'active'


def _build_testing_overview_items(context):
    status_counts_by_mindmap = defaultdict(_create_empty_status_counts)
    for item in context.get('testpoints') or []:
        mindmap_id = item.get('mindmap_id')
        if not mindmap_id:
            continue
        status_counts_by_mindmap[mindmap_id][_normalize_testing_status(item.get('status'))] += 1

    mindmap_lookup = {}
    for mindmap in context.get('mindmaps') or []:
        linked_requirement_key = _extract_mindmap_requirement_key(mindmap)
        if linked_requirement_key and linked_requirement_key not in mindmap_lookup:
            mindmap_lookup[linked_requirement_key] = mindmap

    requirement_records = list(context.get('requirements') or [])
    if not requirement_records:
        requirement_records = [
            SimpleNamespace(
                id=getattr(mindmap, 'id', None),
                issue_key=_extract_mindmap_requirement_key(mindmap),
                summary=_normalize_text(getattr(mindmap, 'requirement_title', '')) or _normalize_text(getattr(mindmap, 'name', '')),
                group_name=_normalize_text(getattr(mindmap, 'responsibility_group', '')),
            )
            for mindmap in context.get('mindmaps') or []
            if _extract_mindmap_requirement_key(mindmap)
        ]

    items = []
    for requirement in requirement_records:
        issue_key = _normalize_text(getattr(requirement, 'issue_key', ''))
        linked_mindmap = mindmap_lookup.get(issue_key.upper())
        linked_group_name = _normalize_group_name(getattr(requirement, 'group_name', ''))
        requirement_title = _normalize_text(getattr(linked_mindmap, 'requirement_title', '')) or _normalize_text(getattr(requirement, 'summary', ''))
        requirement_name = ' '.join(part for part in (issue_key, requirement_title) if part) or _normalize_text(getattr(linked_mindmap, 'name', ''))
        if linked_mindmap is None:
            linked_mindmap = SimpleNamespace(
                id=getattr(requirement, 'id', None) or issue_key,
                name=requirement_name,
                requirement_key=issue_key,
                requirement_title=requirement_title,
                responsibility_group='',
                author=None,
                frontend_developer=None,
                backend_developer=None,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

        fallback_group_name = _normalize_group_name(getattr(linked_mindmap, 'responsibility_group', ''))
        raw_status_counts = status_counts_by_mindmap.get(getattr(linked_mindmap, 'id', None)) or _create_empty_status_counts()
        status_counts = {
            status_key: int(raw_status_counts.get(status_key) or 0)
            for status_key in TESTING_STATUS_ORDER
        }
        total_count = sum(status_counts.values())
        updated_at = max(linked_mindmap.created_at, linked_mindmap.updated_at).isoformat()
        mindmap = linked_mindmap
        items.append(
            {
                'id': getattr(linked_mindmap, 'id', None) or getattr(requirement, 'id', None) or issue_key,
                'name': requirement_name,
                'mindmapName': _normalize_text(getattr(linked_mindmap, 'name', '')),
                'requirement_key': issue_key,
                'requirementKey': issue_key,
                'requirement_title': requirement_title,
                'requirementTitle': requirement_title,
                'requirementName': _normalize_text(mindmap.name) or f'鑴戝浘 #{mindmap.id}',
                'responsibility_group': linked_group_name or fallback_group_name,
                'groupName': linked_group_name or fallback_group_name,
                'tester': _user_display_name(getattr(mindmap, 'author', None)),
                'testerName': _user_display_name(getattr(mindmap, 'author', None)),
                'frontend_developer': _user_display_name(getattr(mindmap, 'frontend_developer', None)),
                'frontendDeveloper': _user_display_name(getattr(mindmap, 'frontend_developer', None)),
                'backend_developer': _user_display_name(getattr(mindmap, 'backend_developer', None)),
                'backendDeveloper': _user_display_name(getattr(mindmap, 'backend_developer', None)),
                'testpoint_count': status_counts,
                'statusCounts': status_counts,
                'totalCount': total_count,
                'segments': _build_testing_segments(status_counts),
                'progressState': _resolve_testing_progress_state(status_counts),
                'failOrBlockCount': status_counts['fail'] + status_counts['block'],
                'updated_at': max(mindmap.created_at, mindmap.updated_at).isoformat(),
                'updatedAt': max(mindmap.created_at, mindmap.updated_at).isoformat(),
            }
        )

    items.sort(
        key=lambda item: (
            -(item.get('failOrBlockCount') or 0),
            -(item.get('totalCount') or 0),
            item.get('requirementName') or '',
        )
    )
    return items


def build_requirement_overview_payload(report, *, user, project_id=None):
    workspace_context = _collect_workspace_context(report, user=user, project_id=project_id)
    project = workspace_context.get('project')
    return {
        'report_id': getattr(report, 'id', None),
        'report_version': workspace_context.get('version') or '',
        'project': {
            'id': getattr(project, 'id', None),
            'name': _normalize_text(getattr(project, 'name', '')),
        },
        'generated_at': timezone.now().isoformat(),
        'requirements': _build_requirement_overview_items(workspace_context),
    }


def build_testing_overview_payload(report, *, user, project_id=None):
    workspace_context = _collect_workspace_context(report, user=user, project_id=project_id)
    project = workspace_context.get('project')
    return {
        'report_id': getattr(report, 'id', None),
        'report_version': workspace_context.get('version') or '',
        'project': {
            'id': getattr(project, 'id', None),
            'name': _normalize_text(getattr(project, 'name', '')),
        },
        'generated_at': timezone.now().isoformat(),
        'mindmaps': _build_testing_overview_items(workspace_context),
    }


def _add_status_counts(target, source):
    for status_key in TESTING_STATUS_ORDER:
        target[status_key] = int(target.get(status_key) or 0) + int((source or {}).get(status_key) or 0)
    return target


def _build_mindmap_node_status_count_lookup(items):
    lookup = defaultdict(_create_empty_status_counts)
    for item in items or []:
        mindmap_id = item.get('mindmap_id')
        if not mindmap_id:
            continue
        lookup[mindmap_id][_normalize_testing_status(item.get('status'))] += 1
    return lookup


def _build_review_testpoint_counts(node):
    counts = {
        'unprocessed': 0,
        'processed': 0,
        'total': 0,
    }

    if not isinstance(node, dict):
        return counts

    node_data = node.get('data') or {}
    if node_data.get('nodeType') == 'testpoint':
        review_opinion = _normalize_text(node_data.get('reviewOpinion'))
        review_status = _normalize_text(node_data.get('reviewStatus'))
        if review_opinion:
            counts['total'] += 1
            if review_status == '已处理':
                counts['processed'] += 1
            else:
                counts['unprocessed'] += 1

    for child in node.get('children') or []:
        child_counts = _build_review_testpoint_counts(child)
        for key, count in child_counts.items():
            counts[key] += count

    return counts


def _build_mindmap_review_testpoint_count_lookup(mindmaps):
    lookup = {}
    for mindmap in mindmaps or []:
        root = (getattr(mindmap, 'mindmap_data', None) or {}).get('root')
        lookup[mindmap.id] = _build_review_testpoint_counts(root)
    return lookup


def _build_mindmap_lookup_by_requirement(mindmaps):
    lookup = defaultdict(list)
    for mindmap in mindmaps or []:
        requirement_key = _extract_mindmap_requirement_key(mindmap)
        if requirement_key:
            lookup[requirement_key.upper()].append(mindmap)
    return lookup


def _extract_related_mindmap_ids(record):
    related_ids = []
    for item in getattr(record, 'related_mindmaps', None) or []:
        raw_mindmap_id = item.get('mindmap_id') or item.get('id') if isinstance(item, dict) else item
        normalized_mindmap_id = _normalize_text(raw_mindmap_id)
        if normalized_mindmap_id:
            related_ids.append(normalized_mindmap_id)
    return related_ids


def _resolve_requirement_mindmaps(record, *, mindmaps_by_id, mindmaps_by_requirement):
    linked_mindmaps = []
    seen_ids = set()

    for raw_mindmap_id in _extract_related_mindmap_ids(record):
        mindmap = mindmaps_by_id.get(str(raw_mindmap_id))
        if mindmap and mindmap.id not in seen_ids:
            linked_mindmaps.append(mindmap)
            seen_ids.add(mindmap.id)

    issue_key = _normalize_text(getattr(record, 'issue_key', '')).upper()
    for mindmap in mindmaps_by_requirement.get(issue_key, []):
        if mindmap.id not in seen_ids:
            linked_mindmaps.append(mindmap)
            seen_ids.add(mindmap.id)

    return linked_mindmaps


def _sum_mindmap_status_counts(mindmap_ids, lookup):
    counts = _create_empty_status_counts()
    for mindmap_id in mindmap_ids:
        _add_status_counts(counts, lookup.get(mindmap_id) or {})
    return counts


def _sum_review_testpoint_counts(mindmap_ids, lookup):
    counts = {
        'unprocessed': 0,
        'processed': 0,
        'total': 0,
    }
    for mindmap_id in mindmap_ids:
        source_counts = lookup.get(mindmap_id) or {}
        for key in counts:
            counts[key] += int(source_counts.get(key) or 0)
    return counts


def _record_links_any_mindmap(record, mindmap_ids):
    if not mindmap_ids:
        return False

    normalized_mindmap_ids = {str(mindmap_id) for mindmap_id in mindmap_ids}
    for relation_item in getattr(record, 'related_testpoints', None) or []:
        if not isinstance(relation_item, dict):
            continue
        if _normalize_text(relation_item.get('mindmap_id')) in normalized_mindmap_ids:
            return True

    return False


def _record_links_requirement_key(record, requirement_key):
    normalized_requirement_key = _normalize_text(requirement_key).upper()
    if not normalized_requirement_key:
        return False

    if _normalize_text(getattr(record, 'requirement_id', '')).upper() == normalized_requirement_key:
        return True

    for relation_item in getattr(record, 'related_requirements', None) or []:
        if not isinstance(relation_item, dict):
            continue
        if _normalize_text(relation_item.get('issue_key')).upper() == normalized_requirement_key:
            return True

    return False


def _record_links_requirement_scope(record, *, requirement_key, mindmap_ids):
    return _record_links_requirement_key(record, requirement_key) or _record_links_any_mindmap(record, mindmap_ids)


def _build_status_count_items(records, *, requirement_key, mindmap_ids, label_resolver, order=()):
    counter = Counter()
    for record in records or []:
        if _record_links_requirement_scope(record, requirement_key=requirement_key, mindmap_ids=mindmap_ids):
            counter[_normalize_text(getattr(record, 'status', '')) or 'unknown'] += 1

    ordered_keys = [
        *[status_key for status_key in order if counter.get(status_key)],
        *sorted(status_key for status_key in counter.keys() if status_key not in order),
    ]
    return [
        {
            'key': status_key,
            'label': label_resolver(status_key),
            'count': int(counter.get(status_key) or 0),
        }
        for status_key in ordered_keys
    ]


def _resolve_version_defect_status_label(status_key):
    return DEFECT_STATUS_LABELS.get(status_key) or ('未填写' if status_key == 'unknown' else status_key)


def _resolve_online_bug_status_label(status_key):
    return '未填写' if status_key == 'unknown' else status_key


def _build_version_defect_status_count_items(defects, *, requirement_key, mindmap_ids):
    return _build_status_count_items(
        defects,
        requirement_key=requirement_key,
        mindmap_ids=mindmap_ids,
        label_resolver=_resolve_version_defect_status_label,
        order=DEFECT_STATUS_ORDER,
    )


def _build_online_bug_status_count_items(online_bugs, *, requirement_key, mindmap_ids):
    return _build_status_count_items(
        online_bugs,
        requirement_key=requirement_key,
        mindmap_ids=mindmap_ids,
        label_resolver=_resolve_online_bug_status_label,
    )


def _build_all_status_count_items(records, *, label_resolver, order=()):
    counter = Counter(_normalize_text(getattr(record, 'status', '')) or 'unknown' for record in records or [])
    ordered_keys = [
        *[status_key for status_key in order if counter.get(status_key)],
        *sorted(status_key for status_key in counter.keys() if status_key not in order),
    ]
    return [
        {
            'key': status_key,
            'label': label_resolver(status_key),
            'count': int(counter.get(status_key) or 0),
        }
        for status_key in ordered_keys
        if int(counter.get(status_key) or 0) > 0
    ]


def _build_all_version_defect_status_count_items(defects):
    return _build_all_status_count_items(
        defects,
        label_resolver=_resolve_version_defect_status_label,
        order=DEFECT_STATUS_ORDER,
    )


def _build_all_online_bug_status_count_items(online_bugs):
    return _build_all_status_count_items(
        online_bugs,
        label_resolver=_resolve_online_bug_status_label,
    )


def _merge_status_count_items(rows, field_name):
    counter = Counter()
    labels = {}
    for row in rows or []:
        for item in row.get(field_name) or []:
            status_key = _normalize_text(item.get('key') or item.get('label')) or 'unknown'
            counter[status_key] += int(item.get('count') or 0)
            labels.setdefault(status_key, _normalize_text(item.get('label')) or status_key)

    return [
        {
            'key': status_key,
            'label': labels.get(status_key) or ('未填写' if status_key == 'unknown' else status_key),
            'count': int(count),
        }
        for status_key, count in counter.items()
        if int(count) > 0
    ]


def _build_requirement_status_count_items(rows):
    counter = Counter()
    for row in rows or []:
        status_key = _normalize_text(row.get('status')) or 'unknown'
        counter[status_key] += 1

    return [
        {
            'key': status_key,
            'label': '未填写' if status_key == 'unknown' else status_key,
            'count': int(count),
        }
        for status_key, count in sorted(counter.items(), key=lambda item: item[0])
        if int(count) > 0
    ]


def _sum_row_status_counts(rows, field_name):
    counts = _create_empty_status_counts()
    for row in rows or []:
        _add_status_counts(counts, row.get(field_name) or {})
    return counts


def _sum_status_count_total(counts):
    return sum(int(counts.get(status_key) or 0) for status_key in TESTING_STATUS_ORDER)


def _sum_count_items_total(items):
    return sum(int(item.get('count') or 0) for item in items or [])


def _build_rd_progress_summary(rows):
    requirement_count = _build_requirement_status_count_items(rows)
    dev_self_test_count = _sum_row_status_counts(rows, 'dev_self_test_count')
    testpoint_count = _sum_row_status_counts(rows, 'testpoint_count')
    version_defect_count = _merge_status_count_items(rows, 'version_defect_count')
    online_defect_count = _merge_status_count_items(rows, 'online_defect_count')
    return {
        'requirement_count': requirement_count,
        'requirement_count_total': _sum_count_items_total(requirement_count),
        'dev_self_test_count': dev_self_test_count,
        'dev_self_test_count_total': _sum_status_count_total(dev_self_test_count),
        'testpoint_count': testpoint_count,
        'testpoint_count_total': _sum_status_count_total(testpoint_count),
        'version_defect_count': version_defect_count,
        'version_defect_count_total': _sum_count_items_total(version_defect_count),
        'online_defect_count': online_defect_count,
        'online_defect_count_total': _sum_count_items_total(online_defect_count),
    }


def _build_rd_progress_summary_from_context(rows, context):
    requirement_count = _build_requirement_status_count_items(rows)
    dev_self_test_count = _sum_row_status_counts(rows, 'dev_self_test_count')
    testpoint_count = _sum_row_status_counts(rows, 'testpoint_count')
    version_defect_count = _build_all_version_defect_status_count_items(context.get('version_defects') or [])
    online_defect_count = _build_all_online_bug_status_count_items(context.get('online_bugs') or [])
    return {
        'requirement_count': requirement_count,
        'requirement_count_total': _sum_count_items_total(requirement_count),
        'dev_self_test_count': dev_self_test_count,
        'dev_self_test_count_total': _sum_status_count_total(dev_self_test_count),
        'testpoint_count': testpoint_count,
        'testpoint_count_total': _sum_status_count_total(testpoint_count),
        'version_defect_count': version_defect_count,
        'version_defect_count_total': _sum_count_items_total(version_defect_count),
        'online_defect_count': online_defect_count,
        'online_defect_count_total': _sum_count_items_total(online_defect_count),
    }


def _format_mindmap_link_items(mindmaps):
    return [
        {
            'id': mindmap.id,
            'name': _normalize_text(getattr(mindmap, 'name', '')),
        }
        for mindmap in mindmaps or []
        if getattr(mindmap, 'id', None)
    ]


def _build_requirement_issue_url(issue_key, jira_browse_prefix):
    normalized_issue_key = _normalize_text(issue_key)
    if not normalized_issue_key:
        return ''
    return f'{jira_browse_prefix}{quote(normalized_issue_key)}'


def _build_rd_progress_row(record, linked_mindmaps, *, context, lookups, jira_browse_prefix, fallback_issue_key=''):
    raw_fields = getattr(record, 'raw_fields', None) or {}
    primary_mindmap = linked_mindmaps[0] if linked_mindmaps else None
    issue_key = _coalesce(
        getattr(record, 'issue_key', '') if record else '',
        fallback_issue_key,
        _extract_mindmap_requirement_key(primary_mindmap) if primary_mindmap else '',
    )
    mindmap_ids = [mindmap.id for mindmap in linked_mindmaps if getattr(mindmap, 'id', None)]
    version_defect_count = _build_version_defect_status_count_items(
        context.get('version_defects') or [],
        requirement_key=issue_key,
        mindmap_ids=mindmap_ids,
    )
    online_defect_count = _build_online_bug_status_count_items(
        context.get('online_bugs') or [],
        requirement_key=issue_key,
        mindmap_ids=mindmap_ids,
    )

    return {
        'id': getattr(record, 'id', None) or issue_key or (mindmap_ids[0] if mindmap_ids else ''),
        'row_index': int(getattr(record, 'row_index', 999999) or 999999) if record else 999999,
        'requirement_key': issue_key,
        'requirement_url': _build_requirement_issue_url(issue_key, jira_browse_prefix),
        'requirement_title': _coalesce(
            getattr(record, 'summary', '') if record else '',
            getattr(primary_mindmap, 'requirement_title', '') if primary_mindmap else '',
            getattr(primary_mindmap, 'name', '') if primary_mindmap else '',
        ),
        'customer_name': _coalesce(
            getattr(record, 'customer_name', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('customfield_10762',)),
        ),
        'priority': _coalesce(
            _resolve_raw_field_value(raw_fields, ('customfield_11100',)),
            getattr(record, 'priority', '') if record else '',
        ),
        'status': _coalesce(getattr(record, 'status', '') if record else ''),
        'module': _coalesce(
            getattr(record, 'module', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('components',)),
        ),
        'group_name': _coalesce(
            getattr(record, 'group_name', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('customfield_11000',)),
            getattr(primary_mindmap, 'responsibility_group', '') if primary_mindmap else '',
        ),
        'pm': _resolve_raw_field_value(raw_fields, ('customfield_10737',)),
        'frontend_developer': _coalesce(
            getattr(record, 'frontend_developer', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('customfield_10743',)),
            _user_display_name(getattr(primary_mindmap, 'frontend_developer', None)) if primary_mindmap else '',
        ),
        'backend_developer': _coalesce(
            getattr(record, 'backend_developer', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('customfield_10741',)),
            _user_display_name(getattr(primary_mindmap, 'backend_developer', None)) if primary_mindmap else '',
        ),
        'tester': _coalesce(
            getattr(record, 'tester', '') if record else '',
            _resolve_raw_field_value(raw_fields, ('customfield_10222',)),
            _user_display_name(getattr(primary_mindmap, 'author', None)) if primary_mindmap else '',
        ),
        'dev_self_test_count': _sum_mindmap_status_counts(mindmap_ids, lookups['dev_self_test_counts']),
        'mindmaps': _format_mindmap_link_items(linked_mindmaps),
        'case_count': _sum_mindmap_status_counts(mindmap_ids, lookups['case_counts']),
        'testpoint_count': _sum_mindmap_status_counts(mindmap_ids, lookups['testpoint_counts']),
        'review_testpoint_count': _sum_review_testpoint_counts(mindmap_ids, lookups['review_testpoint_counts']),
        'version_defect_count': version_defect_count,
        'version_defect_count_total': sum(item['count'] for item in version_defect_count),
        'online_defect_count': online_defect_count,
        'online_defect_count_total': sum(item['count'] for item in online_defect_count),
    }


def build_rd_progress_overview_payload(report, *, user, project_id=None):
    workspace_context = _collect_workspace_context(report, user=user, project_id=project_id)
    project = workspace_context.get('project')
    mindmaps = list(workspace_context.get('mindmaps') or [])
    mindmaps_by_id = {str(mindmap.id): mindmap for mindmap in mindmaps}
    mindmaps_by_requirement = _build_mindmap_lookup_by_requirement(mindmaps)
    jira_browse_prefix = QualityAnalysisSettings.get_solo().jira_browse_prefix
    lookups = {
        'case_counts': _build_mindmap_node_status_count_lookup(workspace_context.get('cases')),
        'testpoint_counts': _build_mindmap_node_status_count_lookup(workspace_context.get('testpoints')),
        'dev_self_test_counts': _build_mindmap_node_status_count_lookup(workspace_context.get('dev_self_tests')),
        'review_testpoint_counts': _build_mindmap_review_testpoint_count_lookup(mindmaps),
    }

    rows = []
    seen_requirement_keys = set()
    for record in workspace_context.get('requirements') or []:
        issue_key = _normalize_text(getattr(record, 'issue_key', '')).upper()
        if issue_key:
            seen_requirement_keys.add(issue_key)
        linked_mindmaps = _resolve_requirement_mindmaps(
            record,
            mindmaps_by_id=mindmaps_by_id,
            mindmaps_by_requirement=mindmaps_by_requirement,
        )
        rows.append(
            _build_rd_progress_row(
                record,
                linked_mindmaps,
                context=workspace_context,
                lookups=lookups,
                jira_browse_prefix=jira_browse_prefix,
            )
        )

    for requirement_key, linked_mindmaps in mindmaps_by_requirement.items():
        if requirement_key in seen_requirement_keys:
            continue
        rows.append(
            _build_rd_progress_row(
                None,
                linked_mindmaps,
                context=workspace_context,
                lookups=lookups,
                jira_browse_prefix=jira_browse_prefix,
                fallback_issue_key=requirement_key,
            )
        )

    rows.sort(key=lambda item: (item.get('row_index', 999999), item.get('requirement_key') or ''))

    return {
        'report_id': getattr(report, 'id', None),
        'report_version': workspace_context.get('version') or '',
        'project': {
            'id': getattr(project, 'id', None),
            'name': _normalize_text(getattr(project, 'name', '')),
        },
        'jira_browse_prefix': jira_browse_prefix,
        'generated_at': timezone.now().isoformat(),
        'summary': _build_rd_progress_summary_from_context(rows, workspace_context),
        'rows': rows,
    }


def _normalize_requirement_records(records):
    normalized_records = []
    for record in records:
        raw_fields = record.raw_fields or {}
        normalized_records.append(
            {
                'issue_key': _normalize_text(record.issue_key),
                'summary': _normalize_text(record.summary),
                'issue_type': _normalize_text(record.issue_type),
                'status': _normalize_text(record.status),
                'priority': _normalize_text(record.priority),
                'module_entries': _extract_module_entries(record.module),
                'module': _normalize_text(record.module),
                'creator': _normalize_text(record.creator),
                'handler': _normalize_text(record.handler),
                'tester': _coalesce(record.tester, raw_fields.get('customfield_10222')),
                'group_name': _coalesce(record.group_name, raw_fields.get('customfield_11000')),
                'product_manager': _normalize_text(raw_fields.get('customfield_10737')),
                'frontend_estimate': _parse_numeric(raw_fields.get('customfield_10749')),
                'backend_estimate': _parse_numeric(raw_fields.get('customfield_10748')),
                'test_estimate': _parse_numeric(raw_fields.get('customfield_10761')),
                'overall_progress': _normalize_text(raw_fields.get('customfield_10765')),
            }
        )
    return normalized_records


def _normalize_bug_records(records):
    normalized_records = []
    for record in records:
        raw_fields = record.raw_fields or {}
        normalized_records.append(
            {
                'issue_key': _normalize_text(record.issue_key),
                'summary': _normalize_text(record.summary),
                'status': _normalize_text(record.status),
                'priority': _normalize_text(record.priority),
                'module_entries': _extract_module_entries(record.module),
                'module': _normalize_text(record.module),
                'creator': _normalize_text(record.creator),
                'handler': _normalize_text(record.handler),
                'tester': _coalesce(record.tester, raw_fields.get('customfield_10222'), raw_fields.get('customfield_10741')),
                'group_name': _coalesce(record.group_name, raw_fields.get('customfield_11000')),
                'product_manager': _normalize_text(raw_fields.get('customfield_10737')),
                'root_cause': _resolve_raw_field_value(raw_fields, ONLINE_BUG_ROOT_CAUSE_FIELDS),
                'bug_category': _normalize_text(raw_fields.get('customfield_11101')),
                'direct_role': _normalize_text(raw_fields.get('customfield_11103')),
                'frontend_estimate': _parse_numeric(raw_fields.get('customfield_10749')),
                'backend_estimate': _parse_numeric(raw_fields.get('customfield_10748')),
                'test_estimate': _parse_numeric(raw_fields.get('customfield_10761')),
                'frontend_developer': _normalize_text(raw_fields.get('customfield_10743')),
            }
        )
    return normalized_records


def _normalize_version_defects(defects):
    normalized_defects = []
    for defect in defects:
        module_entries = _extract_module_entries(defect.modules)
        normalized_defects.append(
            {
                'code': _normalize_text(defect.code),
                'title': _normalize_text(defect.title),
                'severity': _normalize_text(defect.severity),
                'severity_label': defect.get_severity_display(),
                'status': _normalize_text(defect.status),
                'status_label': defect.get_status_display(),
                'requirement_id': _normalize_text(defect.requirement_id),
                'module_entries': module_entries,
                'assignees': _dedupe_preserve_order(_user_display_name(user) for user in defect.assignees.all()),
                'created_by': _user_display_name(defect.created_by),
                'has_testcase_link': bool(defect.related_testcases),
                'has_testpoint_link': bool(defect.related_testpoints),
            }
        )
    return normalized_defects


def _module_stat_bucket():
    return {
        'requirements': 0,
        'high_priority_requirements': 0,
        'testcases': 0,
        'testpoints': 0,
        'dev_self_tests': 0,
        'dev_self_test_failed': 0,
        'dev_self_test_blocked': 0,
        'mindmaps': 0,
        'version_defects': 0,
        'open_version_defects': 0,
        'high_severity_version_defects': 0,
        'online_defects': 0,
        'high_priority_online_defects': 0,
        'frontend_hours': 0.0,
        'backend_hours': 0.0,
        'test_hours': 0.0,
    }


def _build_module_stats(context):
    module_stats = defaultdict(_module_stat_bucket)
    module_display_votes = defaultdict(Counter)

    def register_module(display):
        entry = _module_entry_from_value(display)
        if not entry:
            return None
        module_display_votes[entry['key']][entry['display']] += 1
        return entry

    for item in context['modules']:
        entry = register_module(item.get('module_path') or item.get('node_text'))
        if not entry:
            continue
        module_stats[entry['key']]['mindmaps'] += 1

    for item in context['cases']:
        entry = register_module(item.get('module_path'))
        if not entry:
            continue
        module_stats[entry['key']]['testcases'] += 1

    for item in context['testpoints']:
        entry = register_module(item.get('module_path'))
        if not entry:
            continue
        module_stats[entry['key']]['testpoints'] += 1

    for item in context['dev_self_tests']:
        entry = register_module(item.get('module_path'))
        if not entry:
            continue
        module_stats[entry['key']]['dev_self_tests'] += 1
        if item.get('status') == 'fail':
            module_stats[entry['key']]['dev_self_test_failed'] += 1
        if item.get('status') == 'block':
            module_stats[entry['key']]['dev_self_test_blocked'] += 1

    for item in context['requirements']:
        for entry in item.get('module_entries') or []:
            register_module(entry['display'])
            module_stats[entry['key']]['requirements'] += 1
            if _is_high_priority(item.get('priority')):
                module_stats[entry['key']]['high_priority_requirements'] += 1
            module_stats[entry['key']]['frontend_hours'] += item.get('frontend_estimate', 0.0)
            module_stats[entry['key']]['backend_hours'] += item.get('backend_estimate', 0.0)
            module_stats[entry['key']]['test_hours'] += item.get('test_estimate', 0.0)

    for item in context['version_defects']:
        for entry in item.get('module_entries') or []:
            register_module(entry['display'])
            module_stats[entry['key']]['version_defects'] += 1
            if item.get('status') in OPEN_DEFECT_STATUSES:
                module_stats[entry['key']]['open_version_defects'] += 1
            if item.get('severity') in HIGH_SEVERITY_VALUES:
                module_stats[entry['key']]['high_severity_version_defects'] += 1

    for item in context['online_bugs']:
        for entry in item.get('module_entries') or []:
            register_module(entry['display'])
            module_stats[entry['key']]['online_defects'] += 1
            if _is_high_priority(item.get('priority')):
                module_stats[entry['key']]['high_priority_online_defects'] += 1

    rows = []
    for module_key, bucket in module_stats.items():
        display_counter = module_display_votes.get(module_key) or Counter()
        display_name = display_counter.most_common(1)[0][0] if display_counter else module_key
        requirement_count = bucket['requirements']
        version_defect_count = bucket['version_defects']
        online_defect_count = bucket['online_defects']
        testpoint_count = bucket['testpoints']
        risk_score = (
            online_defect_count * 5
            + version_defect_count * 3
            + bucket['dev_self_test_failed'] * 2
            + bucket['dev_self_test_blocked'] * 2
            + max(requirement_count - bucket['testcases'], 0)
        )
        rows.append(
            {
                'module_key': module_key,
                'module': display_name,
                'requirements': requirement_count,
                'high_priority_requirements': bucket['high_priority_requirements'],
                'mindmaps': bucket['mindmaps'],
                'testcases': bucket['testcases'],
                'testpoints': testpoint_count,
                'dev_self_tests': bucket['dev_self_tests'],
                'dev_self_test_failed': bucket['dev_self_test_failed'],
                'dev_self_test_blocked': bucket['dev_self_test_blocked'],
                'version_defects': version_defect_count,
                'open_version_defects': bucket['open_version_defects'],
                'high_severity_version_defects': bucket['high_severity_version_defects'],
                'online_defects': online_defect_count,
                'high_priority_online_defects': bucket['high_priority_online_defects'],
                'defect_per_requirement': _safe_divide(version_defect_count + online_defect_count, requirement_count),
                'testpoint_per_requirement': _safe_divide(testpoint_count, requirement_count),
                'frontend_hours': round(bucket['frontend_hours'], 2),
                'backend_hours': round(bucket['backend_hours'], 2),
                'test_hours': round(bucket['test_hours'], 2),
                'risk_score': risk_score,
            }
        )

    rows.sort(key=lambda item: (-item['risk_score'], -item['online_defects'], -item['version_defects'], item['module']))
    return rows


def _build_people_tables(context):
    pm_map = defaultdict(lambda: {'requirements': 0, 'online_defects': 0, 'dev_hours': 0.0, 'test_hours': 0.0})
    tester_map = defaultdict(lambda: {'requirements': 0, 'online_defects': 0, 'test_hours': 0.0})
    frontend_map = defaultdict(lambda: {'mindmaps': 0, 'dev_self_tests': 0, 'failed_or_blocked': 0})
    backend_map = defaultdict(lambda: {'mindmaps': 0, 'dev_self_tests': 0, 'failed_or_blocked': 0})
    group_map = defaultdict(lambda: {'requirements': 0, 'dev_self_tests': 0, 'online_defects': 0})

    for item in context['requirements']:
        pm_name = item.get('product_manager')
        if pm_name:
            pm_map[pm_name]['requirements'] += 1
            pm_map[pm_name]['dev_hours'] += item.get('frontend_estimate', 0.0) + item.get('backend_estimate', 0.0)
            pm_map[pm_name]['test_hours'] += item.get('test_estimate', 0.0)

        tester_name = item.get('tester')
        if tester_name:
            tester_map[tester_name]['requirements'] += 1
            tester_map[tester_name]['test_hours'] += item.get('test_estimate', 0.0)

        group_map[_normalize_group_name(item.get('group_name'))]['requirements'] += 1

    for item in context['online_bugs']:
        pm_name = item.get('product_manager')
        if pm_name:
            pm_map[pm_name]['online_defects'] += 1

        tester_name = item.get('tester')
        if tester_name:
            tester_map[tester_name]['online_defects'] += 1

        group_map[_normalize_group_name(item.get('group_name'))]['online_defects'] += 1

    seen_frontend_mindmaps = set()
    seen_backend_mindmaps = set()
    for mindmap in context['mindmaps']:
        frontend_name = _user_display_name(mindmap.frontend_developer)
        if frontend_name and (frontend_name, mindmap.id) not in seen_frontend_mindmaps:
            frontend_map[frontend_name]['mindmaps'] += 1
            seen_frontend_mindmaps.add((frontend_name, mindmap.id))

        backend_name = _user_display_name(mindmap.backend_developer)
        if backend_name and (backend_name, mindmap.id) not in seen_backend_mindmaps:
            backend_map[backend_name]['mindmaps'] += 1
            seen_backend_mindmaps.add((backend_name, mindmap.id))

    for item in context['dev_self_tests']:
        frontend_name = item.get('frontend_developer')
        if frontend_name:
            frontend_map[frontend_name]['dev_self_tests'] += 1
            if item.get('status') in {'fail', 'block'}:
                frontend_map[frontend_name]['failed_or_blocked'] += 1

        backend_name = item.get('backend_developer')
        if backend_name:
            backend_map[backend_name]['dev_self_tests'] += 1
            if item.get('status') in {'fail', 'block'}:
                backend_map[backend_name]['failed_or_blocked'] += 1

        group_map[_normalize_group_name(item.get('responsibility_group'))]['dev_self_tests'] += 1

    pm_rows = sorted(
        [
            {
                'name': name,
                'requirements': values['requirements'],
                'online_defects': values['online_defects'],
                'dev_hours': round(values['dev_hours'], 2),
                'test_hours': round(values['test_hours'], 2),
            }
            for name, values in pm_map.items()
        ],
        key=lambda item: (-item['requirements'], -item['online_defects'], item['name']),
    )[:12]

    frontend_rows = sorted(
        [
            {
                'name': name,
                'mindmaps': values['mindmaps'],
                'dev_self_tests': values['dev_self_tests'],
                'failed_or_blocked': values['failed_or_blocked'],
            }
            for name, values in frontend_map.items()
        ],
        key=lambda item: (-item['dev_self_tests'], -item['mindmaps'], item['name']),
    )[:12]

    backend_rows = sorted(
        [
            {
                'name': name,
                'mindmaps': values['mindmaps'],
                'dev_self_tests': values['dev_self_tests'],
                'failed_or_blocked': values['failed_or_blocked'],
            }
            for name, values in backend_map.items()
        ],
        key=lambda item: (-item['dev_self_tests'], -item['mindmaps'], item['name']),
    )[:12]

    tester_rows = sorted(
        [
            {
                'name': name,
                'requirements': values['requirements'],
                'online_defects': values['online_defects'],
                'test_hours': round(values['test_hours'], 2),
            }
            for name, values in tester_map.items()
        ],
        key=lambda item: (-item['requirements'], -item['online_defects'], item['name']),
    )[:12]

    group_rows = sorted(
        [
            {
                'name': name,
                'requirements': values['requirements'],
                'dev_self_tests': values['dev_self_tests'],
                'online_defects': values['online_defects'],
            }
            for name, values in group_map.items()
        ],
        key=lambda item: (-item['requirements'] - item['dev_self_tests'] - item['online_defects'], item['name']),
    )[:12]

    return {
        'pm_rows': pm_rows,
        'frontend_rows': frontend_rows,
        'backend_rows': backend_rows,
        'tester_rows': tester_rows,
        'group_rows': group_rows,
        'counts': {
            'pm': len(pm_map),
            'frontend': len(frontend_map),
            'backend': len(backend_map),
            'tester': len(tester_map),
            'group': len(group_map),
        },
    }


def _generate_overview_insights(context, module_rows):
    insights = []

    total_requirements = len(context['requirements'])
    total_cases = len(context['cases'])
    total_testpoints = len(context['testpoints'])
    total_dev_self_tests = len(context['dev_self_tests'])
    total_version_defects = len(context['version_defects'])
    total_online_bugs = len(context['online_bugs'])

    if total_requirements:
        insights.append(
            f'当前版本共沉淀 {total_requirements} 条需求，配套 {total_cases} 条测试用例、{total_testpoints} 个测试点，平均每条需求对应 '
            f'{_format_number(_safe_divide(total_testpoints, total_requirements))} 个测试点。'
        )

    if total_dev_self_tests:
        pass_count = sum(1 for item in context['dev_self_tests'] if item.get('status') == 'pass')
        fail_or_block_count = sum(1 for item in context['dev_self_tests'] if item.get('status') in {'fail', 'block'})
        insights.append(
            f'开发自测测试点共 {total_dev_self_tests} 个，当前通过率 {_format_ratio(_percent(pass_count, total_dev_self_tests))}，'
            f'失败/阻塞 {fail_or_block_count} 个。'
        )

    if total_version_defects or total_online_bugs:
        insights.append(
            f'版本缺陷 {total_version_defects} 条，线上缺陷 {total_online_bugs} 条，线上问题规模约为版本内缺陷的 '
            f'{_format_number(_safe_divide(total_online_bugs, max(total_version_defects, 1)))} 倍。'
        )

    if module_rows:
        top_module = module_rows[0]
        insights.append(
            f'高风险模块推断为【{top_module["module"]}】，风险指数 {top_module["risk_score"]}，'
            f'包含线上缺陷 {top_module["online_defects"]} 条、版本缺陷 {top_module["version_defects"]} 条。'
        )

        uncovered_modules = [item for item in module_rows if item['requirements'] > 0 and item['testcases'] == 0]
        if uncovered_modules:
            insights.append(f'仍有 {len(uncovered_modules)} 个模块存在“有需求但无测试用例”情况，建议优先补齐。')

    return insights


def build_version_analysis_payload(report, *, user, project_id=None):
    workspace_context = _collect_workspace_context(report, user=user, project_id=project_id)

    online_defect_effort_block = _build_online_defect_effort_block(
        workspace_context['requirements'],
        workspace_context['online_bugs'],
        categories=[workspace_context.get('version') or '当前版本'],
        description='需求工时来自JIRA需求数据的前端、后端、测试预估工时累计；线上缺陷修复研发工时按前后端预估工时汇总。',
    )

    workspace_context['requirements'] = _normalize_requirement_records(workspace_context['requirements'])
    workspace_context['online_bugs'] = _normalize_bug_records(workspace_context['online_bugs'])
    workspace_context['version_defects'] = _normalize_version_defects(workspace_context['version_defects'])

    module_rows = _build_module_stats(workspace_context)
    people_tables = _build_people_tables(workspace_context)

    requirement_status_counter = Counter(item['status'] or '未填写' for item in workspace_context['requirements'])
    requirement_priority_counter = Counter(item['priority'] or '未填写' for item in workspace_context['requirements'])
    requirement_group_counter = Counter(_normalize_group_name(item.get('group_name')) for item in workspace_context['requirements'])
    requirement_pm_counter = Counter(item['product_manager'] or '未填写' for item in workspace_context['requirements'])

    dev_self_test_status_counter = Counter(item['status'] or '未填写' for item in workspace_context['dev_self_tests'])
    dev_self_test_audit_counter = Counter(item['audit_status'] or '未填写' for item in workspace_context['dev_self_tests'])

    case_status_counter = Counter(item['status'] or '未填写' for item in workspace_context['cases'])
    case_priority_counter = Counter(_coalesce(item.get('priority'), '未填写') for item in workspace_context['cases'])
    testpoint_status_counter = Counter(item['status'] or '未填写' for item in workspace_context['testpoints'])

    version_defect_status_counter = Counter(item['status_label'] or '未填写' for item in workspace_context['version_defects'])
    version_defect_severity_counter = Counter(item['severity_label'] or '未填写' for item in workspace_context['version_defects'])

    online_bug_status_counter = Counter(item['status'] or '未填写' for item in workspace_context['online_bugs'])
    online_bug_priority_counter = Counter(item['priority'] or '未填写' for item in workspace_context['online_bugs'])
    online_bug_root_cause_counter = Counter(item['root_cause'] or '未填写' for item in workspace_context['online_bugs'])

    dev_pass_count = sum(1 for item in workspace_context['dev_self_tests'] if item.get('status') == 'pass')
    case_pass_count = sum(1 for item in workspace_context['cases'] if item.get('status') == 'pass')
    testpoint_pass_count = sum(1 for item in workspace_context['testpoints'] if item.get('status') == 'pass')

    total_frontend_hours = round(sum(item.get('frontend_estimate', 0.0) for item in workspace_context['requirements']), 2)
    total_backend_hours = round(sum(item.get('backend_estimate', 0.0) for item in workspace_context['requirements']), 2)
    total_dev_hours = round(total_frontend_hours + total_backend_hours, 2)
    total_test_hours = round(sum(item.get('test_estimate', 0.0) for item in workspace_context['requirements']), 2)

    risk_module_rows = module_rows[:12]
    uncovered_module_rows = [row for row in module_rows if row['requirements'] > 0 and row['testcases'] == 0][:12]

    mindmap_rows = []
    for mindmap in workspace_context['mindmaps']:
        case_count = sum(1 for item in workspace_context['cases'] if item['mindmap_id'] == mindmap.id)
        testpoint_count = sum(1 for item in workspace_context['testpoints'] if item['mindmap_id'] == mindmap.id)
        mindmap_rows.append(
            {
                'mindmap_name': mindmap.name,
                'responsibility_group': _normalize_text(mindmap.responsibility_group) or '-',
                'frontend_developer': _user_display_name(mindmap.frontend_developer) or '-',
                'backend_developer': _user_display_name(mindmap.backend_developer) or '-',
                'case_count': case_count,
                'testpoint_count': testpoint_count,
            }
        )
    mindmap_rows.sort(key=lambda item: (-item['testpoint_count'], -item['case_count'], item['mindmap_name']))

    version_defect_module_rows = sorted(
        [
            {
                'module': row['module'],
                'version_defects': row['version_defects'],
                'open_version_defects': row['open_version_defects'],
                'high_severity': row['high_severity_version_defects'],
            }
            for row in module_rows
            if row['version_defects'] > 0
        ],
        key=lambda item: (-item['version_defects'], -item['high_severity'], item['module']),
    )[:12]

    online_bug_module_rows = sorted(
        [
            {
                'module': row['module'],
                'online_defects': row['online_defects'],
                'high_priority_online_defects': row['high_priority_online_defects'],
                'requirements': row['requirements'],
            }
            for row in module_rows
            if row['online_defects'] > 0
        ],
        key=lambda item: (-item['online_defects'], -item['high_priority_online_defects'], item['module']),
    )[:12]
    requirement_module_rows = sorted(
        [
            {
                'module': row['module'],
                'requirements': row['requirements'],
                'high_priority_requirements': row['high_priority_requirements'],
                'testcases': row['testcases'],
                'testpoints': row['testpoints'],
            }
            for row in module_rows
            if row['requirements'] > 0
        ],
        key=lambda item: (-item['requirements'], -item['high_priority_requirements'], item['module']),
    )[:12]
    requirement_detail_rows = workspace_context['requirements'][:12]

    workload_module_rows = sorted(
        [
            {
                'module': row['module'],
                'requirements': row['requirements'],
                'frontend_hours': row['frontend_hours'],
                'backend_hours': row['backend_hours'],
                'test_hours': row['test_hours'],
                'total_hours': round(row['frontend_hours'] + row['backend_hours'] + row['test_hours'], 2),
            }
            for row in module_rows
            if row['frontend_hours'] or row['backend_hours'] or row['test_hours']
        ],
        key=lambda item: (-item['total_hours'], -item['requirements'], item['module']),
    )[:12]

    overview_insights = _generate_overview_insights(workspace_context, module_rows)
    project = workspace_context['project']

    tabs = [
        {
            'key': 'overview',
            'label': '总览',
            'metrics': [
                {'label': '需求', 'value': len(workspace_context['requirements']), 'description': 'JIRA需求条数'},
                {'label': '开发自测测试点', 'value': len(workspace_context['dev_self_tests']), 'description': 'P1自测点规模'},
                {'label': '测试用例', 'value': len(workspace_context['cases']), 'description': '脑图中的用例节点'},
                {'label': '测试点', 'value': len(workspace_context['testpoints']), 'description': '脑图中的测试点节点'},
                {'label': '版本缺陷', 'value': len(workspace_context['version_defects']), 'description': '版本内缺陷数量'},
                {'label': '线上缺陷', 'value': len(workspace_context['online_bugs']), 'description': '同步的JIRA线上BUG'},
                {'label': '模块', 'value': len(module_rows), 'description': '参与分析的模块'},
                {'label': '组别', 'value': people_tables['counts']['group'], 'description': '需求/自测/JIRA组别汇总'},
            ],
            'blocks': [
                _make_bullets_block('版本洞察', overview_insights, description='以下结论基于当前平台真实数据自动归纳。'),
                _make_distribution_block('需求状态分布', requirement_status_counter),
                _make_distribution_block('线上缺陷状态分布', online_bug_status_counter),
                _make_distribution_block('版本缺陷严重程度分布', version_defect_severity_counter),
                _make_table_block(
                    '模块质量总表',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求', 90),
                        ('testcases', '测试用例', 100),
                        ('testpoints', '测试点', 100),
                        ('dev_self_tests', '自测点', 90),
                        ('version_defects', '版本缺陷', 100),
                        ('online_defects', '线上缺陷', 100),
                        ('defect_per_requirement', '缺陷/需求', 100),
                        ('risk_score', '风险指数', 100),
                    ],
                    risk_module_rows,
                    description='风险指数为平台推断值，综合考虑线上缺陷、版本缺陷、自测失败/阻塞以及需求与用例失衡情况。',
                ),
            ],
        },
        {
            'key': 'requirements',
            'label': '需求',
            'metrics': [
                {'label': '需求总数', 'value': len(workspace_context['requirements']), 'description': '当前版本JIRA需求条数'},
                {'label': '高优先级需求', 'value': sum(1 for item in workspace_context['requirements'] if _is_high_priority(item.get('priority'))), 'description': 'P0/P1或高优先级'},
                {'label': '产品经理', 'value': people_tables['counts']['pm'], 'description': '需求涉及的产品经理数'},
                {'label': '测试人员', 'value': people_tables['counts']['tester'], 'description': '需求涉及的测试人员数'},
                {'label': '开发预估工时', 'value': _format_number(total_dev_hours), 'description': '前后端预估工时累计'},
                {'label': '测试预估工时', 'value': _format_number(total_test_hours), 'description': '需求测试预估工时累计'},
            ],
            'blocks': [
                _make_distribution_block(
                    '版本需求状态分布',
                    requirement_status_counter,
                    description='复刻版本缺陷页签的状态分析能力，改为按当前版本需求状态统计。',
                ),
                _make_distribution_block(
                    '版本需求优先级分布',
                    requirement_priority_counter,
                    description='复刻版本缺陷严重程度分布能力，改为按需求优先级统计。',
                ),
                _make_distribution_block(
                    '版本需求组别分布',
                    requirement_group_counter,
                    description='查看当前版本需求在组别维度的分布情况。',
                ),
                _make_distribution_block(
                    '版本需求产品经理分布',
                    requirement_pm_counter,
                    description='查看当前版本需求在产品经理维度的分布情况。',
                ),
                _make_table_block(
                    '版本需求模块分布',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求数', 100),
                        ('high_priority_requirements', '高优先级', 100),
                        ('testcases', '测试用例', 100),
                        ('testpoints', '测试点', 100),
                    ],
                    requirement_module_rows,
                    description='复刻版本缺陷模块分布能力，改为按需求口径查看模块需求覆盖情况。',
                ),
                _make_table_block(
                    '版本需求关键信息',
                    [
                        ('issue_key', '需求编号', 140, 'left'),
                        ('summary', '需求标题', 260, 'left'),
                        ('issue_type', '需求类型', 120),
                        ('priority', '版本内研发优先级别', 140),
                        ('status', '状态', 120),
                        ('module', '模块', 200, 'left'),
                        ('product_manager', '产品经理', 120),
                        ('tester', '测试人员', 120),
                        ('group_name', '组别', 120),
                    ],
                    requirement_detail_rows,
                    description='复刻版本缺陷关联情况能力，改为查看版本需求关键信息的覆盖与完整度。',
                ),
                _make_table_block(
                    '版本需求产品经理视角',
                    [
                        ('name', '产品经理', 160, 'left'),
                        ('requirements', '需求数', 100),
                        ('online_defects', '线上缺陷', 100),
                        ('dev_hours', '开发工时', 100),
                        ('test_hours', '测试工时', 100),
                    ],
                    people_tables['pm_rows'],
                    description='从产品经理视角查看当前版本需求规模、线上问题和工时投入。',
                ),
                _build_matrix_block(
                    '版本需求优先级 × 状态',
                    workspace_context['requirements'],
                    row_resolver=lambda item: [item.get('priority') or '未填写'],
                    column_resolver=lambda item: [item.get('status') or '未填写'],
                    row_label='优先级',
                    description='复刻版本缺陷严重程度 × 状态能力，改为查看需求优先级与状态的组合分布。',
                ),
            ],
        },
        {
            'key': 'dev-self-test',
            'label': '开发自测测试点',
            'metrics': [
                {'label': '自测点总数', 'value': len(workspace_context['dev_self_tests']), 'description': 'P1自测点'},
                {'label': '审核通过', 'value': sum(1 for item in workspace_context['dev_self_tests'] if item.get('audit_status') == 'approved'), 'description': '已审核通过的自测点'},
                {'label': '待审核', 'value': sum(1 for item in workspace_context['dev_self_tests'] if item.get('audit_status') == 'pending'), 'description': '尚未审核'},
                {'label': '通过率', 'value': _format_ratio(_percent(dev_pass_count, max(len(workspace_context['dev_self_tests']), 1))), 'description': '按自测执行状态计算'},
                {'label': '失败/阻塞', 'value': sum(1 for item in workspace_context['dev_self_tests'] if item.get('status') in {'fail', 'block'}), 'description': '存在风险的自测点'},
                {'label': '组别', 'value': len({_normalize_group_name(item.get('responsibility_group')) for item in workspace_context['dev_self_tests']}), 'description': '参与自测的组别数'},
            ],
            'blocks': [
                _make_distribution_block('自测执行状态分布', dev_self_test_status_counter),
                _make_distribution_block('自测审核状态分布', dev_self_test_audit_counter),
                _make_table_block(
                    '前端开发视角',
                    [
                        ('name', '前端开发', 160, 'left'),
                        ('mindmaps', '脑图数', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('failed_or_blocked', '失败/阻塞', 100),
                    ],
                    people_tables['frontend_rows'],
                ),
                _make_table_block(
                    '后端开发视角',
                    [
                        ('name', '后端开发', 160, 'left'),
                        ('mindmaps', '脑图数', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('failed_or_blocked', '失败/阻塞', 100),
                    ],
                    people_tables['backend_rows'],
                ),
                _make_table_block(
                    '模块自测覆盖',
                    [
                        ('module', '模块', 220, 'left'),
                        ('dev_self_tests', '自测点', 90),
                        ('dev_self_test_failed', '失败', 90),
                        ('dev_self_test_blocked', '阻塞', 90),
                        ('testpoints', '测试点', 90),
                    ],
                    [
                        {
                            'module': row['module'],
                            'dev_self_tests': row['dev_self_tests'],
                            'dev_self_test_failed': row['dev_self_test_failed'],
                            'dev_self_test_blocked': row['dev_self_test_blocked'],
                            'testpoints': row['testpoints'],
                        }
                        for row in risk_module_rows
                        if row['dev_self_tests'] > 0
                    ],
                ),
                _build_matrix_block(
                    '审核状态 × 执行状态',
                    workspace_context['dev_self_tests'],
                    row_resolver=lambda item: [item.get('audit_status') or '未填写'],
                    column_resolver=lambda item: [item.get('status') or '未填写'],
                    row_label='审核状态',
                ),
            ],
        },
        {
            'key': 'test-assets',
            'label': '测试资产',
            'metrics': [
                {'label': '测试脑图', 'value': len(workspace_context['mindmaps']), 'description': '版本下的脑图数量'},
                {'label': '测试用例', 'value': len(workspace_context['cases']), 'description': 'case节点数'},
                {'label': '测试点', 'value': len(workspace_context['testpoints']), 'description': 'testpoint节点数'},
                {'label': '覆盖模块', 'value': sum(1 for row in module_rows if row['testcases'] or row['testpoints']), 'description': '至少存在测试资产的模块'},
                {'label': '用例通过率', 'value': _format_ratio(_percent(case_pass_count, max(len(workspace_context['cases']), 1))), 'description': '按用例执行状态计算'},
                {'label': '测试点通过率', 'value': _format_ratio(_percent(testpoint_pass_count, max(len(workspace_context['testpoints']), 1))), 'description': '按测试点执行状态计算'},
            ],
            'blocks': [
                _make_distribution_block('测试用例状态分布', case_status_counter),
                _make_distribution_block('测试点状态分布', testpoint_status_counter),
                _make_distribution_block('测试用例优先级分布', case_priority_counter),
                _make_table_block(
                    '脑图资产分布',
                    [
                        ('mindmap_name', '脑图名称', 220, 'left'),
                        ('responsibility_group', '组别', 120),
                        ('frontend_developer', '前端开发', 120),
                        ('backend_developer', '后端开发', 120),
                        ('case_count', '测试用例', 90),
                        ('testpoint_count', '测试点', 90),
                    ],
                    mindmap_rows[:12],
                ),
                _make_table_block(
                    '模块测试资产分布',
                    [
                        ('module', '模块', 220, 'left'),
                        ('mindmaps', '模块节点', 90),
                        ('testcases', '测试用例', 90),
                        ('testpoints', '测试点', 90),
                        ('testpoint_per_requirement', '测试点/需求', 100),
                    ],
                    [
                        {
                            'module': row['module'],
                            'mindmaps': row['mindmaps'],
                            'testcases': row['testcases'],
                            'testpoints': row['testpoints'],
                            'testpoint_per_requirement': row['testpoint_per_requirement'],
                        }
                        for row in risk_module_rows
                    ],
                ),
                _build_matrix_block(
                    '用例优先级 × 状态',
                    workspace_context['cases'],
                    row_resolver=lambda item: [_coalesce(item.get('priority'), '未填写')],
                    column_resolver=lambda item: [item.get('status') or '未填写'],
                    row_label='优先级',
                ),
            ],
        },
        {
            'key': 'version-defects',
            'label': '版本缺陷',
            'metrics': [
                {'label': '缺陷总数', 'value': len(workspace_context['version_defects']), 'description': '版本缺陷列表记录数'},
                {'label': '高严重度', 'value': sum(1 for item in workspace_context['version_defects'] if item.get('severity') in HIGH_SEVERITY_VALUES), 'description': '高/严重缺陷'},
                {'label': '待处理', 'value': sum(1 for item in workspace_context['version_defects'] if item.get('status') in OPEN_DEFECT_STATUSES), 'description': 'new/in_progress/reopened'},
                {'label': '需求已关联', 'value': _format_ratio(_percent(sum(1 for item in workspace_context['version_defects'] if item.get('requirement_id')), max(len(workspace_context['version_defects']), 1))), 'description': '已填写JIRA编号的占比'},
                {'label': '用例已关联', 'value': _format_ratio(_percent(sum(1 for item in workspace_context['version_defects'] if item.get('has_testcase_link')), max(len(workspace_context['version_defects']), 1))), 'description': '已关联测试用例占比'},
                {'label': '测试点已关联', 'value': _format_ratio(_percent(sum(1 for item in workspace_context['version_defects'] if item.get('has_testpoint_link')), max(len(workspace_context['version_defects']), 1))), 'description': '已关联测试点占比'},
            ],
            'blocks': [
                _make_distribution_block('版本缺陷状态分布', version_defect_status_counter),
                _make_distribution_block('版本缺陷严重程度分布', version_defect_severity_counter),
                _make_table_block(
                    '模块缺陷分布',
                    [
                        ('module', '模块', 220, 'left'),
                        ('version_defects', '缺陷数', 90),
                        ('open_version_defects', '待处理', 90),
                        ('high_severity', '高严重度', 100),
                    ],
                    version_defect_module_rows,
                ),
                _make_table_block(
                    '缺陷关联情况',
                    [
                        ('code', '缺陷编号', 140, 'left'),
                        ('title', '标题', 260, 'left'),
                        ('severity_label', '严重程度', 100),
                        ('status_label', '状态', 120),
                        ('requirement_id', 'JIRA编号', 140),
                    ],
                    workspace_context['version_defects'][:12],
                ),
                _build_matrix_block(
                    '严重程度 × 状态',
                    workspace_context['version_defects'],
                    row_resolver=lambda item: [item.get('severity_label') or '未填写'],
                    column_resolver=lambda item: [item.get('status_label') or '未填写'],
                    row_label='严重程度',
                ),
            ],
        },
        {
            'key': 'online-defects',
            'label': '线上缺陷',
            'metrics': [
                {'label': '线上缺陷', 'value': len(workspace_context['online_bugs']), 'description': '当前版本同步JIRA BUG'},
                {'label': '高优先级', 'value': sum(1 for item in workspace_context['online_bugs'] if _is_high_priority(item.get('priority'))), 'description': 'P0/P1或高优先级'},
                {'label': '根因类型', 'value': len({item.get('root_cause') for item in workspace_context['online_bugs'] if item.get('root_cause')}), 'description': '线上缺陷根因类型数'},
                {'label': '组别', 'value': len({_normalize_group_name(item.get('group_name')) for item in workspace_context['online_bugs']}), 'description': '线上缺陷组别数'},
                {'label': '产品经理', 'value': len({item.get('product_manager') for item in workspace_context['online_bugs'] if item.get('product_manager')}), 'description': '线上缺陷涉及产品经理数'},
                {'label': '测试人员', 'value': len({item.get('tester') for item in workspace_context['online_bugs'] if item.get('tester')}), 'description': '线上缺陷涉及测试人员数'},
            ],
            'blocks': [
                online_defect_effort_block,
                _make_distribution_block('线上缺陷优先级分布', online_bug_priority_counter),
                _make_distribution_block('线上缺陷状态分布', online_bug_status_counter),
                _make_distribution_block('线上缺陷根因分析统计', online_bug_root_cause_counter),
                _make_table_block(
                    '模块线上缺陷分布',
                    [
                        ('module', '模块', 220, 'left'),
                        ('online_defects', '线上缺陷', 100),
                        ('high_priority_online_defects', '高优先级', 100),
                        ('requirements', '需求数', 90),
                    ],
                    online_bug_module_rows,
                ),
                _make_table_block(
                    '测试人员视角',
                    [
                        ('name', '测试人员', 160, 'left'),
                        ('requirements', '需求数', 90),
                        ('online_defects', '线上缺陷', 100),
                        ('test_hours', '测试工时', 90),
                    ],
                    people_tables['tester_rows'],
                ),
                _build_matrix_block(
                    '根因 × 组别',
                    workspace_context['online_bugs'],
                    row_resolver=lambda item: [item.get('root_cause') or '未填写'],
                    column_resolver=lambda item: [_normalize_group_name(item.get('group_name'))],
                    row_label='根因',
                ),
            ],
        },
        {
            'key': 'modules',
            'label': '模块',
            'metrics': [
                {'label': '模块总数', 'value': len(module_rows), 'description': '参与质量分析的模块'},
                {'label': '有测试覆盖模块', 'value': sum(1 for row in module_rows if row['testcases'] or row['testpoints']), 'description': '至少具备用例或测试点'},
                {'label': '有缺陷模块', 'value': sum(1 for row in module_rows if row['version_defects'] or row['online_defects']), 'description': '版本缺陷或线上缺陷命中'},
                {'label': '零缺陷模块', 'value': sum(1 for row in module_rows if not row['version_defects'] and not row['online_defects']), 'description': '当前无缺陷命中'},
                {'label': '有需求无用例模块', 'value': len(uncovered_module_rows), 'description': '需求已存在但尚无测试用例'},
                {'label': '高风险模块', 'value': sum(1 for row in module_rows if row['risk_score'] >= 5), 'description': '风险指数大于等于5'},
            ],
            'blocks': [
                _make_table_block(
                    '模块质量看板',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求', 90),
                        ('testcases', '测试用例', 100),
                        ('testpoints', '测试点', 100),
                        ('dev_self_tests', '自测点', 90),
                        ('version_defects', '版本缺陷', 100),
                        ('online_defects', '线上缺陷', 100),
                        ('defect_per_requirement', '缺陷/需求', 100),
                        ('risk_score', '风险指数', 100),
                    ],
                    risk_module_rows,
                ),
                _make_table_block(
                    '有需求无用例模块',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求', 90),
                        ('testpoints', '测试点', 90),
                        ('version_defects', '版本缺陷', 100),
                        ('online_defects', '线上缺陷', 100),
                    ],
                    uncovered_module_rows,
                ),
                _make_bullets_block(
                    '模块维度结论',
                    [
                        f'Top1 风险模块为【{risk_module_rows[0]["module"]}】。' if risk_module_rows else '',
                        f'共 {len(uncovered_module_rows)} 个模块存在需求未被用例覆盖。' if uncovered_module_rows else '当前所有有需求模块均已建立测试用例。',
                        f'共有 {sum(1 for row in module_rows if row["online_defects"] > 0)} 个模块出现线上缺陷。' if module_rows else '',
                    ],
                ),
            ],
        },
        {
            'key': 'people',
            'label': '人员',
            'metrics': [
                {'label': '产品经理', 'value': people_tables['counts']['pm'], 'description': '需求侧涉及人员'},
                {'label': '前端开发', 'value': people_tables['counts']['frontend'], 'description': '脑图/自测侧涉及人员'},
                {'label': '后端开发', 'value': people_tables['counts']['backend'], 'description': '脑图/自测侧涉及人员'},
                {'label': '测试人员', 'value': people_tables['counts']['tester'], 'description': '需求/JIRA侧涉及人员'},
                {'label': '组别', 'value': people_tables['counts']['group'], 'description': '跨需求、自测、缺陷的责任主体'},
                {'label': '脑图作者', 'value': len({_user_display_name(item.author) for item in workspace_context["mindmaps"] if _user_display_name(item.author)}), 'description': '测试资产创建者'},
            ],
            'blocks': [
                _make_table_block(
                    '产品经理视角',
                    [
                        ('name', '产品经理', 160, 'left'),
                        ('requirements', '需求数', 90),
                        ('online_defects', '线上缺陷', 100),
                        ('dev_hours', '开发工时', 90),
                        ('test_hours', '测试工时', 90),
                    ],
                    people_tables['pm_rows'],
                ),
                _make_table_block(
                    '前端开发视角',
                    [
                        ('name', '前端开发', 160, 'left'),
                        ('mindmaps', '脑图数', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('failed_or_blocked', '失败/阻塞', 100),
                    ],
                    people_tables['frontend_rows'],
                ),
                _make_table_block(
                    '后端开发视角',
                    [
                        ('name', '后端开发', 160, 'left'),
                        ('mindmaps', '脑图数', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('failed_or_blocked', '失败/阻塞', 100),
                    ],
                    people_tables['backend_rows'],
                ),
                _make_table_block(
                    '组别视角',
                    [
                        ('name', '组别', 160, 'left'),
                        ('requirements', '需求', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('online_defects', '线上缺陷', 100),
                    ],
                    people_tables['group_rows'],
                ),
            ],
        },
        {
            'key': 'workload',
            'label': '工时',
            'metrics': [
                {'label': '开发预估总工时', 'value': _format_number(total_dev_hours), 'description': '前后端工时累计'},
                {'label': '测试预估总工时', 'value': _format_number(total_test_hours), 'description': '需求测试工时累计'},
                {'label': '前端工时', 'value': _format_number(total_frontend_hours), 'description': '前端预估工时'},
                {'label': '后端工时', 'value': _format_number(total_backend_hours), 'description': '后端预估工时'},
                {'label': '平均单需求开发工时', 'value': _format_number(_safe_divide(total_dev_hours, max(len(workspace_context['requirements']), 1))), 'description': '按需求平均'},
                {'label': '平均单需求测试工时', 'value': _format_number(_safe_divide(total_test_hours, max(len(workspace_context['requirements']), 1))), 'description': '按需求平均'},
            ],
            'blocks': [
                _make_table_block(
                    '模块工时分布',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求数', 90),
                        ('frontend_hours', '前端工时', 100),
                        ('backend_hours', '后端工时', 100),
                        ('test_hours', '测试工时', 100),
                        ('total_hours', '总工时', 100),
                    ],
                    workload_module_rows,
                ),
                _make_table_block(
                    '产品经理工时视角',
                    [
                        ('name', '产品经理', 160, 'left'),
                        ('requirements', '需求数', 90),
                        ('dev_hours', '开发工时', 100),
                        ('test_hours', '测试工时', 100),
                    ],
                    people_tables['pm_rows'],
                ),
                _make_table_block(
                    '测试人员工时视角',
                    [
                        ('name', '测试人员', 160, 'left'),
                        ('requirements', '需求数', 90),
                        ('test_hours', '测试工时', 100),
                        ('online_defects', '线上缺陷', 100),
                    ],
                    people_tables['tester_rows'],
                ),
            ],
        },
        {
            'key': 'combinations',
            'label': '组合分析',
            'metrics': [
                {'label': '需求/缺陷比', 'value': _format_number(_safe_divide(len(workspace_context['version_defects']) + len(workspace_context['online_bugs']), max(len(workspace_context['requirements']), 1))), 'description': '版本缺陷+线上缺陷 / 需求'},
                {'label': '需求/测试点比', 'value': _format_number(_safe_divide(len(workspace_context['testpoints']), max(len(workspace_context['requirements']), 1))), 'description': '测试点 / 需求'},
                {'label': '需求/自测点比', 'value': _format_number(_safe_divide(len(workspace_context['dev_self_tests']), max(len(workspace_context['requirements']), 1))), 'description': '自测点 / 需求'},
                {'label': '线上/版本缺陷比', 'value': _format_number(_safe_divide(len(workspace_context['online_bugs']), max(len(workspace_context['version_defects']), 1))), 'description': '线上缺陷 / 版本缺陷'},
            ],
            'blocks': [
                _build_matrix_block(
                    '需求优先级 × 状态',
                    workspace_context['requirements'],
                    row_resolver=lambda item: [item.get('priority') or '未填写'],
                    column_resolver=lambda item: [item.get('status') or '未填写'],
                    row_label='版本内研发优先级别',
                ),
                _build_matrix_block(
                    '版本缺陷严重程度 × 状态',
                    workspace_context['version_defects'],
                    row_resolver=lambda item: [item.get('severity_label') or '未填写'],
                    column_resolver=lambda item: [item.get('status_label') or '未填写'],
                    row_label='严重程度',
                ),
                _build_matrix_block(
                    '组别 × 阶段资产',
                    [
                        *({'group': _normalize_group_name(item.get('group_name')), 'stage': '需求'} for item in workspace_context['requirements']),
                        *({'group': _normalize_group_name(item.get('responsibility_group')), 'stage': '开发自测'} for item in workspace_context['dev_self_tests']),
                        *({'group': _normalize_group_name(item.get('group_name')), 'stage': '线上缺陷'} for item in workspace_context['online_bugs']),
                    ],
                    row_resolver=lambda item: [_normalize_group_name(item.get('group'))],
                    column_resolver=lambda item: [item.get('stage') or '未填写'],
                    row_label='组别',
                ),
                _make_table_block(
                    '模块风险链路',
                    [
                        ('module', '模块', 220, 'left'),
                        ('requirements', '需求', 90),
                        ('dev_self_tests', '自测点', 90),
                        ('testpoints', '测试点', 90),
                        ('version_defects', '版本缺陷', 100),
                        ('online_defects', '线上缺陷', 100),
                        ('risk_score', '风险指数', 100),
                    ],
                    risk_module_rows,
                    description='用于观察“需求 -> 开发自测 -> 测试资产 -> 缺陷”的质量链路完整度。',
                ),
                _make_bullets_block(
                    '专项结论',
                    [
                        f'当前版本平均每条需求对应 {_format_number(_safe_divide(len(workspace_context["dev_self_tests"]), max(len(workspace_context["requirements"]), 1)))} 个开发自测点。',
                        f'当前版本平均每条需求对应 {_format_number(_safe_divide(len(workspace_context["cases"]), max(len(workspace_context["requirements"]), 1)))} 条测试用例。',
                        f'当前版本平均每条需求对应 {_format_number(_safe_divide(len(workspace_context["version_defects"]), max(len(workspace_context["requirements"]), 1)))} 条版本缺陷。',
                    ],
                ),
            ],
        },
    ]
    tabs = _apply_director_view_block_order(tabs)

    summary = {
        'requirements': len(workspace_context['requirements']),
        'dev_self_tests': len(workspace_context['dev_self_tests']),
        'cases': len(workspace_context['cases']),
        'testpoints': len(workspace_context['testpoints']),
        'version_defects': len(workspace_context['version_defects']),
        'online_defects': len(workspace_context['online_bugs']),
        'modules': len(module_rows),
        'groups': people_tables['counts']['group'],
    }

    return {
        'report_id': getattr(report, 'id', None),
        'report_version': workspace_context['version'],
        'project': {
            'id': project.id if project else None,
            'name': project.name if project else '',
        },
        'summary': summary,
        'generated_at': timezone.now().isoformat(),
        'tabs': tabs,
    }
