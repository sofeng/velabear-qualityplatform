import re


PUBLIC_NODE_ID_PATTERN = re.compile(r'^(?P<mindmap_id>\d+):(?P<node_type>[a-z_]+):(?P<sequence>\d+)$')


def normalize_public_node_id(value):
    return str(value or '').strip()


def build_public_node_id(mindmap_id, node_type, sequence):
    return f'{int(mindmap_id)}:{str(node_type or "").strip()}:{int(sequence)}'


def get_mindmap_node_native_id(node):
    if not isinstance(node, dict):
        return ''

    data = node.get('data') if isinstance(node.get('data'), dict) else {}
    return str(node.get('id') or data.get('id') or '').strip()


def parse_public_node_id(value):
    normalized_value = normalize_public_node_id(value)
    if not normalized_value:
        return None

    matched = PUBLIC_NODE_ID_PATTERN.fullmatch(normalized_value)
    if not matched:
        return None

    return {
        'public_id': normalized_value,
        'mindmap_id': int(matched.group('mindmap_id')),
        'node_type': matched.group('node_type'),
        'sequence': int(matched.group('sequence')),
    }


def iter_mindmap_target_nodes(node, *, mindmap_id, target_type, path_parts=None, module_parts=None, sequence_state=None, node_path=None):
    if not isinstance(node, dict):
        return

    path_parts = path_parts or []
    module_parts = module_parts or []
    sequence_state = sequence_state or {'value': 0}
    current_node_path = [*(node_path or []), node]

    data = node.get('data') or {}
    text = str(data.get('text') or '').strip()
    current_path = [*path_parts, text] if text else list(path_parts)
    current_module_parts = (
        [*module_parts, text]
        if data.get('nodeType') == 'module' and text
        else list(module_parts)
    )

    if data.get('nodeType') == target_type:
        sequence_state['value'] += 1
        yield {
            'sequence': sequence_state['value'],
            'public_id': build_public_node_id(mindmap_id, target_type, sequence_state['value']),
            'mindmap_id': int(mindmap_id),
            'node_id': get_mindmap_node_native_id(node),
            'node_text': text,
            'node_type': str(target_type or '').strip(),
            'path': ' / '.join(current_path),
            'module_path': ' / '.join(
                current_module_parts if data.get('nodeType') == 'module' else module_parts
            ),
            'parent_text': path_parts[-1] if path_parts else '',
            'node': node,
            'node_path': current_node_path,
            'data': data,
            'path_parts': current_path,
            'module_parts': current_module_parts,
        }

    for child in node.get('children') or []:
        yield from iter_mindmap_target_nodes(
            child,
            mindmap_id=mindmap_id,
            target_type=target_type,
            path_parts=current_path,
            module_parts=current_module_parts,
            sequence_state=sequence_state,
            node_path=current_node_path,
        )


def resolve_public_node_descriptor(mindmap, public_node_id):
    parsed_node_id = parse_public_node_id(public_node_id)
    if not parsed_node_id or not mindmap:
        return None
    if int(getattr(mindmap, 'id', 0) or 0) != parsed_node_id['mindmap_id']:
        return None

    root_node = (getattr(mindmap, 'mindmap_data', None) or {}).get('root')
    for descriptor in iter_mindmap_target_nodes(
        root_node,
        mindmap_id=mindmap.id,
        target_type=parsed_node_id['node_type'],
    ):
        if descriptor['public_id'] == parsed_node_id['public_id']:
            return descriptor

    return None


def normalize_relation_path(value):
    return ' / '.join(
        segment.strip()
        for segment in str(value or '').split('/')
        if segment and segment.strip()
    )


def get_relation_item_public_id(item):
    if not isinstance(item, dict):
        return ''
    return normalize_public_node_id(item.get('id') or item.get('node_id'))


def relation_item_matches_public_node_id(item, public_node_id, descriptor=None):
    if not isinstance(item, dict):
        return False

    normalized_public_id = normalize_public_node_id(public_node_id)
    if not normalized_public_id:
        return False

    if get_relation_item_public_id(item) == normalized_public_id:
        return True

    if not descriptor:
        return False

    relation_mindmap_id = item.get('mindmap_id')
    if relation_mindmap_id not in (None, '') and str(relation_mindmap_id) != str(descriptor.get('mindmap_id')):
        return False

    descriptor_node_type = str(descriptor.get('node_type') or '').strip()
    relation_node_type = str(item.get('node_type') or '').strip()
    if relation_node_type and descriptor_node_type and relation_node_type != descriptor_node_type:
        return False

    descriptor_path = normalize_relation_path(descriptor.get('path'))
    relation_path = normalize_relation_path(item.get('path'))
    if descriptor_path and relation_path and descriptor_path == relation_path:
        return True

    descriptor_node_text = str(descriptor.get('node_text') or '').strip()
    relation_node_text = str(item.get('node_text') or '').strip()
    if descriptor_node_text and relation_node_text and descriptor_node_text == relation_node_text:
        descriptor_parent_text = str(descriptor.get('parent_text') or '').strip()
        relation_parent_text = str(item.get('parent_text') or '').strip()
        if not descriptor_parent_text or not relation_parent_text or descriptor_parent_text == relation_parent_text:
            return True

    return False
