from uuid import uuid4

from rest_framework import serializers

from .models import ManualWorkspacePageListConfig
from .page_list_config_registry import (
    FILTER_CONTROL_TYPES,
    MODULE_KEY,
    build_factory_config,
    get_field_map,
    get_page_definition,
)


class ManualWorkspacePageListConfigSerializer(serializers.ModelSerializer):
    page_name = serializers.SerializerMethodField()
    columns = serializers.SerializerMethodField()
    factory_config = serializers.SerializerMethodField()
    fields_registry = serializers.SerializerMethodField()

    class Meta:
        model = ManualWorkspacePageListConfig
        fields = [
            'id',
            'module_key',
            'page_key',
            'page_name',
            'filter_conditions',
            'columns',
            'factory_config',
            'fields_registry',
            'version',
            'updated_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'page_name', 'factory_config', 'fields_registry', 'updated_by', 'created_at', 'updated_at']

    def get_page_name(self, obj):
        page_def = get_page_definition(obj.page_key)
        return page_def.get('page_name') if page_def else obj.page_key

    def get_columns(self, obj):
        page_def = get_page_definition(obj.page_key)
        return normalize_columns(page_def, obj.columns or [], strict=False) if page_def else obj.columns

    def get_factory_config(self, obj):
        page_def = get_page_definition(obj.page_key)
        return build_factory_config(page_def) if page_def else {'filter_conditions': [], 'columns': []}

    def get_fields_registry(self, obj):
        page_def = get_page_definition(obj.page_key)
        return page_def.get('fields', []) if page_def else []


def _normalize_bool(value, default=True):
    if value is None:
        return default
    return bool(value)


def _normalize_positive_order(value, fallback):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return parsed if parsed > 0 else fallback


def _normalize_text(value, max_length=500):
    text = str(value or '').strip()
    return text[:max_length]


def _validate_page(module_key, page_key):
    normalized_module = str(module_key or MODULE_KEY).strip() or MODULE_KEY
    if normalized_module != MODULE_KEY:
        raise serializers.ValidationError({'module_key': '不支持的模块标识'})

    page_def = get_page_definition(page_key)
    if not page_def:
        raise serializers.ValidationError({'page_key': '不支持的页面标识'})
    return normalized_module, page_def


def normalize_filter_conditions(page_def, conditions):
    field_map = get_field_map(page_def)
    normalized = []
    seen_ids = set()

    for index, item in enumerate(conditions or [], start=1):
        if not isinstance(item, dict):
            raise serializers.ValidationError({'filter_conditions': '筛选条件格式不正确'})

        field_key = _normalize_text(item.get('field_key'), 160)
        field_def = field_map.get(field_key)
        if not field_def or not field_def.get('filterable'):
            raise serializers.ValidationError({'filter_conditions': f'筛选字段未注册或不支持筛选: {field_key}'})

        filter_type = _normalize_text(item.get('filter_type'), 40)
        supported_controls = field_def.get('supported_filter_controls') or []
        if filter_type not in FILTER_CONTROL_TYPES or filter_type not in supported_controls:
            raise serializers.ValidationError({'filter_conditions': f'字段 {field_def.get("label")} 不支持筛选控件 {filter_type}'})

        item_id = _normalize_text(item.get('id'), 120) or f'filter-{uuid4().hex}'
        if item_id in seen_ids:
            item_id = f'{item_id}-{index}'
        seen_ids.add(item_id)

        normalized.append({
            'id': item_id,
            'field_key': field_key,
            'label_override': _normalize_text(item.get('label_override'), 80),
            'filter_type': filter_type,
            'operator': _normalize_text(item.get('operator'), 40) or ('contains' if filter_type == 'text' else 'eq'),
            'placeholder': _normalize_text(item.get('placeholder'), 120),
            'option_source': _normalize_text(item.get('option_source'), 120) or field_def.get('option_source') or '',
            'enabled': _normalize_bool(item.get('enabled'), True),
            'order': _normalize_positive_order(item.get('order'), index),
        })

    normalized.sort(key=lambda row: (row['order'], row['field_key']))
    for order, item in enumerate(normalized, start=1):
        item['order'] = order
    return normalized


def normalize_columns(page_def, columns, *, strict=True):
    field_map = get_field_map(page_def)
    normalized = []
    seen = set()

    for index, item in enumerate(columns or [], start=1):
        if not isinstance(item, dict):
            raise serializers.ValidationError({'columns': '列表字段格式不正确'})

        field_key = _normalize_text(item.get('field_key'), 160)
        field_def = field_map.get(field_key)
        if not field_def or not field_def.get('list_column'):
            if not strict:
                continue
            raise serializers.ValidationError({'columns': f'列表字段未注册或不支持展示: {field_key}'})
        if field_key in seen:
            continue
        seen.add(field_key)

        locked = bool(field_def.get('locked'))
        normalized.append({
            'field_key': field_key,
            'label_override': _normalize_text(item.get('label_override'), 80),
            'visible': True if locked else _normalize_bool(item.get('visible'), field_def.get('default_visible', True)),
            'locked': locked,
            'order': _normalize_positive_order(item.get('order'), index),
        })

    for field_def in page_def.get('fields', []):
        if not field_def.get('list_column') or field_def['field_key'] in seen:
            continue
        normalized.append({
            'field_key': field_def['field_key'],
            'label_override': '',
            'visible': bool(field_def.get('default_visible', True)),
            'locked': bool(field_def.get('locked', False)),
            'order': len(normalized) + 1,
        })

    def _column_sort_key(row):
        field_key = row.get('field_key')
        order = row.get('order') or 0
        if field_key == 'type:selection':
            return (-1, order, field_key)
        if row.get('locked') and str(field_key or '').startswith('label:'):
            return (1, order, field_key)
        return (0, order, field_key)

    normalized.sort(key=_column_sort_key)
    for order, item in enumerate(normalized, start=1):
        item['order'] = order
    return normalized


class ManualWorkspacePageListConfigUpsertSerializer(serializers.Serializer):
    module_key = serializers.CharField(required=False, allow_blank=True, default=MODULE_KEY)
    page_key = serializers.CharField(required=True)
    filter_conditions = serializers.ListField(required=False, default=list)
    columns = serializers.ListField(required=False, default=list)
    version = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        module_key, page_def = _validate_page(attrs.get('module_key'), attrs.get('page_key'))
        attrs['module_key'] = module_key
        attrs['page_key'] = page_def['page_key']
        attrs['filter_conditions'] = normalize_filter_conditions(page_def, attrs.get('filter_conditions') or [])
        attrs['columns'] = normalize_columns(page_def, attrs.get('columns') or [])
        return attrs


class ManualWorkspacePageListConfigRestoreSerializer(serializers.Serializer):
    module_key = serializers.CharField(required=False, allow_blank=True, default=MODULE_KEY)
    page_key = serializers.CharField(required=True)
    version = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        module_key, page_def = _validate_page(attrs.get('module_key'), attrs.get('page_key'))
        attrs['module_key'] = module_key
        attrs['page_key'] = page_def['page_key']
        attrs['factory_config'] = build_factory_config(page_def)
        return attrs
