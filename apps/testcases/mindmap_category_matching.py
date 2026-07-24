from copy import deepcopy

from .models import ManualTestCaseCategory


MODULE_MATCH_FIELDS = (
    'moduleCategoryMatched',
    'moduleCategoryId',
    'moduleCategoryPath',
    'moduleCategoryMatchMode',
)


def normalize_module_name(value):
    return ' '.join(str(value or '').strip().split()).casefold()


def _common_suffix_length(left, right):
    matched = 0
    for left_item, right_item in zip(reversed(left), reversed(right)):
        if left_item != right_item:
            break
        matched += 1
    return matched


def _build_category_index(project):
    rows = list(
        ManualTestCaseCategory.objects.filter(project=project)
        .order_by('order', 'id')
        .values('id', 'name', 'parent_id')
    )
    rows_by_id = {row['id']: row for row in rows}
    path_cache = {}

    def resolve_path(category_id, visiting=None):
        if category_id in path_cache:
            return path_cache[category_id]

        row = rows_by_id.get(category_id)
        if not row:
            return []

        visiting = set(visiting or ())
        if category_id in visiting:
            return [str(row.get('name') or '').strip()]
        visiting.add(category_id)

        parent_path = resolve_path(row.get('parent_id'), visiting) if row.get('parent_id') else []
        path = [*parent_path, str(row.get('name') or '').strip()]
        path_cache[category_id] = path
        return path

    descriptors = []
    by_name = {}
    for row in rows:
        path = [segment for segment in resolve_path(row['id']) if segment]
        normalized_path = tuple(normalize_module_name(segment) for segment in path if normalize_module_name(segment))
        normalized_name = normalize_module_name(row.get('name'))
        descriptor = {
            'id': row['id'],
            'name': str(row.get('name') or '').strip(),
            'path': path,
            'normalized_path': normalized_path,
        }
        descriptors.append(descriptor)
        if normalized_name:
            by_name.setdefault(normalized_name, []).append(descriptor)

    return {
        'descriptors': descriptors,
        'by_name': by_name,
    }


def _resolve_category_match(module_path, category_index):
    normalized_path = tuple(
        normalize_module_name(segment)
        for segment in module_path
        if normalize_module_name(segment)
    )
    if not normalized_path:
        return None, ''

    candidates = list(category_index['by_name'].get(normalized_path[-1], []))
    if not candidates:
        return None, ''

    scored_candidates = [
        (_common_suffix_length(normalized_path, candidate['normalized_path']), candidate)
        for candidate in candidates
    ]
    best_score = max(score for score, _candidate in scored_candidates)
    best_candidates = [
        candidate for score, candidate in scored_candidates if score == best_score
    ]

    if best_score >= 2 and len(best_candidates) == 1:
        return best_candidates[0], 'path'
    if len(candidates) == 1:
        return candidates[0], 'unique_name'
    return None, ''


def match_mindmap_modules_to_categories(project, mindmap_data):
    matched_data = deepcopy(mindmap_data) if isinstance(mindmap_data, dict) else {}
    category_index = _build_category_index(project)
    summary = {
        'total': 0,
        'matched': 0,
        'unmatched': 0,
    }

    def walk(node, module_path):
        if not isinstance(node, dict):
            return

        data = node.get('data')
        if not isinstance(data, dict):
            data = {}
            node['data'] = data

        current_module_path = list(module_path)
        if data.get('nodeType') == 'module':
            module_name = str(data.get('text') or '').strip()
            if module_name:
                current_module_path.append(module_name)

            category, match_mode = _resolve_category_match(current_module_path, category_index)
            is_matched = category is not None
            data['moduleCategoryMatched'] = is_matched
            data['moduleCategoryId'] = category['id'] if category else None
            data['moduleCategoryPath'] = list(category['path']) if category else []
            data['moduleCategoryMatchMode'] = match_mode
            summary['total'] += 1
            summary['matched' if is_matched else 'unmatched'] += 1
        else:
            for field_name in MODULE_MATCH_FIELDS:
                data.pop(field_name, None)

        for child in node.get('children') or []:
            walk(child, current_module_path)

    walk(matched_data.get('root'), [])
    return matched_data, summary
