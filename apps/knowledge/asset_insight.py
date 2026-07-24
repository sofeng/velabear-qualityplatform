import re
from collections import Counter, defaultdict
from pathlib import Path

from django.db.models import Q
from django.utils import timezone

from apps.projects.models import Project

from .models import (
    KnowledgeIndexRun,
    KnowledgeObject,
    KnowledgeRelation,
    KnowledgeRepositoryConfig,
    KnowledgeSpace,
)
from .services import (
    ensure_project_knowledge_space,
    get_queryset_for_user,
    is_repository_config_ready,
    maybe_auto_index_repository,
    serialize_edge,
    serialize_node,
    tokenize_query,
)


GRAPH_TYPE_DEFS = {
    'page_function': {
        'label': '页面功能图',
        'types': {'project', 'module', 'menu', 'page', 'tab', 'section', 'function', 'operation', 'component', 'route'},
        'relation_types': {'contains', 'implements', 'uses', 'related_to'},
    },
    'page_api_table': {
        'label': '页面功能-接口-库表字段图',
        'types': {'platform', 'project', 'module', 'menu', 'page', 'tab', 'section', 'function', 'operation', 'component', 'repository', 'file', 'class', 'method', 'api', 'database', 'table', 'field'},
        'relation_types': {'contains', 'implements', 'calls', 'reads', 'writes', 'uses', 'references', 'related_to'},
    },
    'api': {
        'label': '接口关系图',
        'types': {'api', 'route', 'file', 'class', 'function', 'method', 'table', 'field', 'component', 'tab', 'page'},
        'relation_types': {'calls', 'reads', 'writes', 'uses', 'references', 'implements', 'related_to'},
    },
    'code': {
        'label': '代码调用图',
        'types': {'repository', 'file', 'class', 'function', 'method', 'component', 'api', 'route', 'table', 'field'},
        'relation_types': {'contains', 'implements', 'calls', 'uses', 'reads', 'writes', 'references', 'related_to'},
    },
    'er': {
        'label': '数据库ER图',
        'types': {'database', 'table', 'field'},
        'relation_types': {'contains', 'reads', 'writes', 'related_to'},
    },
    'all': {
        'label': '全量资产图谱',
        'types': set(),
        'relation_types': set(),
    },
}


GHOST_TYPE_LABELS = {
    'orphan_api': '疑似无页面调用接口',
    'orphan_component': '疑似无页签引用组件',
    'schema_only_table': '疑似仅存在Schema中的表',
    'schema_only_field': '疑似仅存在Schema中的字段',
    'unlinked_file': '疑似未关联代码文件',
}


ROADMAP_TREE_CACHE = None


DEFAULT_MANUAL_ROADMAP_ENTRIES = [
    ('知识库助手', '知识库助手', 'AI会话工作区', ['知识库对象问答', '历史会话查看', '右侧关系图', '命中路径与数据来源']),
    ('总览', '总览', '研发进展总览', ['需求进展统计', '自测与测试覆盖统计', '跳转测试脑图', '跳转版本缺陷']),
    ('需求', 'JIRA需求数据', '需求同步与列表', ['同步需求', '需求筛选', '查看需求详情', '跳转测试点', '跳转缺陷']),
    ('需求', '版本需求', '版本需求管理', ['新增版本需求', '编辑版本需求', '删除版本需求', '关联测试脑图', '跳转版本缺陷']),
    ('开发', '自测测试点', '自测测试点表格', ['查看脑图', '编辑自测测试点', '审核自测测试点', '提交缺陷']),
    ('开发', '技术方案设计', '技术方案设计列表', ['新增技术方案', '编辑技术方案', '导入Excel', '流转状态', '评论与附件']),
    ('测试', '测试脑图', '脑图列表与编辑器', ['新建脑图', '编辑脑图', '查看脑图', '批量删除脑图']),
    ('测试', '测试用例', '脑图用例抽取', ['用例查看', '按需求筛选', '跳转脑图']),
    ('测试', '测试点', '脑图测试点抽取', ['测试点查看', '按状态和模块筛选', '提交缺陷', '跳转脑图']),
    ('缺陷', '版本缺陷分析', '缺陷统计分析', ['按开发人员统计', '按缺陷状态统计', '按问题根因统计']),
    ('缺陷', '版本缺陷', '版本缺陷列表', ['新建缺陷', '编辑缺陷', '变更状态', '指派处理人', '评论与附件', '导入Excel']),
    ('缺陷', '线上缺陷', '线上BUG同步列表', ['同步线上BUG', '线上缺陷筛选', '关联需求', '关联测试用例或测试点']),
    ('报告', '报告列表', '质量报告列表', ['上传报告', '分析报告', '刷新实时快照', '分享报告']),
    ('报告', '实时质量分析', '实时质量分析看板', ['版本质量分析', '需求进展分析', '测试进展分析', '缺陷与工时分析', '复制分享链接']),
    ('配置', '项目环境', '项目环境配置', ['新增环境', '编辑环境', '启用停用环境']),
    ('配置', 'Git/GitHub仓库配置', '知识库仓库配置', ['新增仓库配置', '编辑仓库配置', '弹出授权页面', '测试连接', '触发索引', '查看索引报告']),
    ('配置', '项目资产图谱', '项目知识库与资产图谱', ['创建项目知识库', '页面接口库表关系图', '数据库ER图', '代码调用图', '幽灵代码排查', '库表字段检索']),
    ('配置', 'JIRA接口配置', 'JIRA同步接口配置', ['新增接口配置', '编辑接口配置', '执行同步配置', '查看同步记录']),
    ('配置', '通知配置', '邮件与消息提醒', ['配置邮件模板', '配置SMTP', '测试发送', '配置消息提醒']),
    ('配置', '邮件模板配置', '邮件模板配置', ['配置邮件模板']),
    ('配置', '邮件配置', 'SMTP邮件配置', ['配置SMTP']),
    ('配置', '测试发送', '邮件测试发送', ['测试发送']),
    ('配置', '消息提醒', '消息提醒配置', ['配置消息提醒']),
    ('配置', '流程工作台', '流程定义与待办', ['查看待办', '维护流程定义', '维护流程规则', '启动或处理流程']),
    ('管理', '成员', '成员管理', ['新增成员', '编辑成员', '停用启用成员', '重置密码']),
    ('管理', '组别', '组别管理', ['新增组别', '维护组成员']),
    ('管理', '角色', '角色管理', ['新增角色', '维护角色成员']),
    ('管理', '项目', '项目管理', ['新增项目', '设置默认项目', '维护项目成员']),
    ('管理', '版本', '版本管理', ['新增版本', '设置默认版本']),
    ('管理', '权限', '权限管理', ['权限目录', '角色授权', '维护权限项']),
    ('录制', '自动化脚本生成', '脚本生成', ['生成Playwright脚本']),
    ('录制', '自动化脚本管理', '脚本版本管理', ['查看脚本版本', '恢复版本']),
    ('录制', '快照文件管理', '快照管理', ['上传快照', '解析快照', '批量导出']),
    ('录制', '录制结果管理', '录制会话管理', ['本地Agent录制', '步骤去重', '转流程']),
    ('录制', '流程管理', '可视化流程列表', ['创建流程', '复制流程', '执行流程']),
    ('录制', '可视化流程编辑器', '流程画布', ['编排节点', '绑定录制步骤', '保存流程']),
    ('录制', '测试执行结果', '执行结果列表', ['查看执行结果', '查看步骤截图', '查看执行日志']),
    ('Wiki', 'Wiki', 'Wiki目录与页面', ['维护目录', '编辑页面内容', '上传附件图片']),
]


class VirtualAssetNode:
    def __init__(
        self,
        *,
        node_id,
        object_type,
        key,
        name,
        summary='',
        roadmap_path=None,
        page_path='',
        tab_key='',
        component_path='',
        api_path='',
        db_table='',
        field_name='',
        source_type='asset_graph_virtual',
        source_ref='',
        metadata=None,
    ):
        self.id = node_id
        self.object_type = object_type
        self.key = key
        self.name = name
        self.summary = summary
        self.content = summary
        self.roadmap_path = roadmap_path or []
        self.page_path = page_path
        self.tab_key = tab_key
        self.component_path = component_path
        self.api_path = api_path
        self.db_table = db_table
        self.field_name = field_name
        self.source_type = source_type
        self.source_ref = source_ref
        self.metadata = metadata or {}
        self.search_text = ' '.join([name or '', summary or '', source_ref or ''])


def get_accessible_space(user, *, space_id=None, space_key='', project_id=None):
    spaces = get_queryset_for_user(KnowledgeSpace.objects.select_related('project', 'owner').all(), user)
    if space_id:
        return spaces.filter(id=space_id).first()
    if space_key:
        return spaces.filter(key=space_key).first()
    if project_id:
        return spaces.filter(project_id=project_id).order_by('-updated_at', '-id').first()
    return spaces.order_by('-updated_at', '-id').first()


def get_project_repository_configs(user, project_id=None):
    queryset = get_queryset_for_user(
        KnowledgeRepositoryConfig.objects.select_related('project', 'space', 'created_by').all(),
        user,
    )
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    return queryset.order_by('-updated_at', '-id')


def get_project_knowledge_status(user, project_id=None):
    project = Project.objects.filter(id=project_id).first() if project_id else None
    space = get_accessible_space(user, project_id=project_id)
    configs = list(get_project_repository_configs(user, project_id=project_id)[:20])
    latest_run = (
        KnowledgeIndexRun.objects
        .filter(Q(space=space) | Q(repository_config__in=configs))
        .select_related('space', 'repository_config')
        .order_by('-started_at', '-id')
        .first()
        if space or configs else None
    )
    enabled = False
    if space:
        metadata = space.metadata or {}
        if 'project_knowledge_enabled' in metadata:
            enabled = bool(metadata.get('project_knowledge_enabled'))
        else:
            enabled = bool(configs or space.build_status in {'ready', 'queued', 'indexing', 'indexed', 'stale'})
    ready_configs = [config for config in configs if is_repository_config_ready(config)]
    return {
        'project': {'id': project.id, 'name': project.name} if project else None,
        'enabled': enabled,
        'space': serialize_space(space) if space else None,
        'repository_configs': [serialize_config(config) for config in configs],
        'ready_config_count': len(ready_configs),
        'latest_run': serialize_run(latest_run) if latest_run else None,
        'can_build': bool(ready_configs),
        'message': build_project_knowledge_status_message(space, configs, ready_configs),
    }


def set_project_knowledge_enabled(user, *, project_id, enabled=True, trigger_index=True):
    enabled = parse_bool(enabled, True)
    trigger_index = parse_bool(trigger_index, True)
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'error': '请选择要启用知识库的项目。'}, 400
    space = ensure_project_knowledge_space(project, user=user)
    metadata = dict(space.metadata or {})
    metadata['project_knowledge_enabled'] = enabled
    metadata['enabled_at'] = timezone.now().isoformat() if enabled else metadata.get('enabled_at', '')
    metadata['asset_insight_enabled'] = enabled
    space.metadata = metadata
    if enabled and space.build_status == 'pending_config':
        space.build_status = 'ready'
        space.build_status_message = '项目知识库已启用，请配置代码仓库和数据库后执行建模。'
    elif not enabled:
        space.build_status_message = '项目知识库已停用。'
    space.save(update_fields=['metadata', 'build_status', 'build_status_message', 'updated_at'])

    index_payload = None
    if enabled and trigger_index:
        ready_configs = [config for config in get_project_repository_configs(user, project_id=project.id) if is_repository_config_ready(config)]
        if ready_configs:
            index_payload = maybe_auto_index_repository(ready_configs[0], user=user, trigger='project_knowledge_enabled')

    payload = get_project_knowledge_status(user, project_id=project.id)
    payload['index'] = normalize_index_payload(index_payload)
    return payload, 200


def build_asset_insight_payload(user, params):
    project_id = params.get('project_id') or params.get('project')
    section = params.get('section') or params.get('payload') or 'all'
    space = get_accessible_space(
        user,
        space_id=params.get('space') or params.get('space_id'),
        space_key=params.get('space_key') or '',
        project_id=project_id,
    )
    if not space:
        return {
            'space': None,
            'summary': build_empty_summary(),
            'graphs': {},
            'ghost_code': {'findings': [], 'summary': {}},
            'fields': {'tables': [], 'fields': []},
            'message': '当前项目尚未创建知识库，请先启用项目知识库并完成仓库/数据库配置。',
        }

    graph_type = params.get('graph_type') or 'page_api_table'
    query = params.get('q') or params.get('query') or ''
    limit = safe_int(params.get('limit'), 180)
    page = max(1, safe_int(params.get('page'), 1))
    page_size = normalize_page_size(params.get('page_size') or params.get('pageSize') or limit)
    center_table = params.get('center_table') or ''
    er_view = normalize_er_view(params.get('er_view') or params.get('view') or 'macro')
    payload = {
        'space': serialize_space(space),
        'status': {
            'build_status': space.build_status,
            'build_status_message': space.build_status_message,
            'last_indexed_at': space.last_indexed_at,
        },
    }
    if section in {'all', 'summary'}:
        payload['summary'] = build_asset_summary(space)
    if section in {'all', 'graph'}:
        payload['graph'] = build_asset_graph(
            space,
            graph_type=graph_type,
            query=query,
            limit=limit,
            center_table=center_table,
            er_view=er_view,
        )
    if section in {'all', 'ghost'}:
        payload['ghost_code'] = build_ghost_code_payload(space, page=page, page_size=page_size)
    if section in {'all', 'fields'}:
        payload['fields'] = build_table_field_payload(space, query=query, page=page, page_size=page_size)
    return payload


def build_asset_summary(space):
    objects = KnowledgeObject.objects.filter(space=space)
    relations = KnowledgeRelation.objects.filter(space=space)
    type_counts = Counter(objects.values_list('object_type', flat=True))
    latest_run = (
        KnowledgeIndexRun.objects
        .filter(space=space)
        .select_related('repository_config')
        .order_by('-started_at', '-id')
        .first()
    )
    return {
        'object_count': sum(type_counts.values()),
        'relation_count': relations.count(),
        'type_counts': dict(type_counts),
        'page_count': type_counts.get('page', 0) + type_counts.get('tab', 0),
        'api_count': type_counts.get('api', 0),
        'table_count': type_counts.get('table', 0),
        'field_count': type_counts.get('field', 0),
        'component_count': type_counts.get('component', 0),
        'code_file_count': type_counts.get('file', 0),
        'code_symbol_count': type_counts.get('class', 0) + type_counts.get('function', 0) + type_counts.get('method', 0),
        'latest_run': serialize_run(latest_run) if latest_run else None,
    }


def build_empty_summary():
    return {
        'object_count': 0,
        'relation_count': 0,
        'type_counts': {},
        'page_count': 0,
        'api_count': 0,
        'table_count': 0,
        'field_count': 0,
        'component_count': 0,
        'code_file_count': 0,
        'code_symbol_count': 0,
        'latest_run': None,
    }


def build_asset_graph(space, *, graph_type='page_api_table', query='', limit=180, center_table='', er_view='macro'):
    graph_def = GRAPH_TYPE_DEFS.get(graph_type) or GRAPH_TYPE_DEFS['page_api_table']
    limit = max(20, min(safe_int(limit, 180), 500))
    object_types = set(graph_def.get('types') or [])
    relation_types = set(graph_def.get('relation_types') or [])
    objects_qs = KnowledgeObject.objects.filter(space=space)
    if object_types:
        objects_qs = objects_qs.filter(object_type__in=object_types)
    if graph_type == 'page_api_table' and not query:
        return build_page_api_table_chain_graph(space, objects_qs, graph_def=graph_def, limit=limit)
    if graph_type == 'er':
        objects_qs = objects_qs.filter(object_type__in=['database', 'table', 'field'])
        er_view = normalize_er_view(er_view)
        if er_view == 'macro':
            objects = select_er_macro_graph(space, objects_qs, query=query, limit=limit)
        elif er_view == 'meso':
            objects = select_er_neighborhood(space, objects_qs, center_table=center_table or query, limit=limit, include_fields=True, field_limit_per_table=6)
            if not objects:
                objects = select_er_macro_graph(space, objects_qs, query=query, limit=limit)
        else:
            objects = select_er_neighborhood(space, objects_qs, center_table=center_table or query, limit=limit, include_fields=True, field_limit_per_table=80)
            if not objects:
                objects = select_er_micro_graph(space, objects_qs, query=query, limit=limit)
    elif graph_type == 'page_function' and not query:
        objects = select_page_function_neighborhood(space, objects_qs, limit=limit)
    elif graph_type == 'api' and not query:
        objects = select_api_neighborhood(space, objects_qs, limit=limit)
    elif graph_type == 'code' and not query:
        objects = select_code_neighborhood(space, objects_qs, limit=limit)
    else:
        objects = select_graph_objects(objects_qs, query=query, limit=limit)

    object_ids = [obj.id for obj in objects]
    relation_qs = KnowledgeRelation.objects.select_related('source', 'target').filter(space=space)
    if relation_types:
        relation_qs = relation_qs.filter(relation_type__in=relation_types)
    relations = list(
        relation_qs
        .filter(source_id__in=object_ids, target_id__in=object_ids)
        .order_by('-weight', 'id')[:limit * 3]
    )
    return {
        'graph_type': graph_type,
        'label': graph_def['label'],
        'nodes': [serialize_asset_node(obj) for obj in objects],
        'edges': [serialize_edge(relation) for relation in relations],
        'categories': build_graph_categories(objects),
        'query': query,
        'center_table': center_table,
        'er_view': er_view if graph_type == 'er' else '',
        'truncated': KnowledgeObject.objects.filter(space=space).count() > len(objects),
    }


def build_page_api_table_chain_graph(space, objects_qs, *, graph_def, limit=180):
    limit = max(80, min(safe_int(limit, 180), 500))
    relation_types = {'contains', 'implements', 'calls', 'reads', 'writes', 'uses', 'references', 'related_to'}
    node_state = {}
    edges = []
    edge_seen = set()
    node_order = []
    virtual_node_index = 0
    virtual_node_cache = {}

    def node_count():
        return len(node_state)

    def touch_node(obj, *, branch='ui', lane='ui', rank=1, x=0, y=0, chain_index=None, evidence='indexed', roadmap_path=None):
        if not obj:
            return None
        state = node_state.get(obj.id)
        if not state:
            state = {
                'obj': obj,
                'branches': set(),
                'lanes': set(),
                'rank': rank,
                'positions': [],
                'chain_indices': set(),
                'evidence': set(),
                'display_roadmap_paths': [],
            }
            node_state[obj.id] = state
            node_order.append(obj.id)
        state['branches'].add(branch)
        state['lanes'].add(lane)
        state['rank'] = min(state['rank'], rank)
        state['positions'].append((x, y))
        if chain_index is not None:
            state['chain_indices'].add(chain_index)
        if evidence:
            state['evidence'].add(evidence)
        if roadmap_path:
            state['display_roadmap_paths'].append([str(item) for item in roadmap_path if str(item or '').strip()])
        return obj

    def add_edge(source, target, relation_type, label='', *, relation=None, branch='ui', inferred=False, evidence='indexed'):
        if not source or not target or source.id == target.id:
            return
        if source.id not in node_state or target.id not in node_state:
            return
        key = ('rel', relation.id) if relation else ('edge', source.id, target.id, relation_type, label, branch)
        if key in edge_seen:
            return
        edge_seen.add(key)
        if relation:
            payload = serialize_edge(relation)
        else:
            payload = {
                'id': f'page-api-table:{source.id}:{target.id}:{relation_type}:{len(edges) + 1}',
                'source': source.id,
                'target': target.id,
                'source_key': source.key,
                'target_key': target.key,
                'type': relation_type,
                'label': label or relation_type,
                'weight': 0.85 if inferred else 1.0,
                'source_ref': '',
                'metadata': {},
            }
        metadata = dict(payload.get('metadata') or {})
        metadata['asset_graph'] = {
            'graph_type': 'page_api_table',
            'branch': branch,
            'inferred': bool(inferred),
            'evidence': evidence,
        }
        payload['metadata'] = metadata
        payload['asset_graph_branch'] = branch
        payload['inferred'] = bool(inferred)
        edges.append(payload)

    def create_virtual_node(object_type, label, *, parent, chain_index, order, summary='', roadmap_path=None, metadata=None):
        nonlocal virtual_node_index
        path = [str(item).strip() for item in (roadmap_path or [*(parent.roadmap_path or []), label]) if str(item or '').strip()]
        cache_key = (object_type, tuple(normalize_roadmap_token(item) for item in path), normalize_roadmap_token(label))
        cached = virtual_node_cache.get(cache_key)
        if cached:
            return cached
        virtual_node_index += 1
        node_id = -(10000000 + virtual_node_index)
        key = f'virtual:{object_type}:{abs(parent.id)}:{slugify_asset_label("/".join(path))}'
        node = VirtualAssetNode(
            node_id=node_id,
            object_type=object_type,
            key=key,
            name=label,
            summary=summary or label,
            roadmap_path=path,
            page_path=parent.page_path,
            tab_key=parent.tab_key,
            component_path=parent.component_path,
            source_ref=parent.source_ref,
            metadata={
                'virtual': True,
                'parent_id': parent.id,
                'parent_key': parent.key,
                'chain_index': chain_index,
                **(metadata or {}),
            },
        )
        virtual_node_cache[cache_key] = node
        return node

    root = first_object(objects_qs, 'platform') or first_object(objects_qs, 'module') or first_object(objects_qs, 'repository') or first_object(objects_qs, 'database')
    module = first_object(objects_qs, 'module')
    repository = first_object(objects_qs, 'repository')
    database = first_object(objects_qs, 'database')
    project_label = getattr(space.project, 'name', '') or space.name or '项目'
    project_node = create_virtual_node(
        'project',
        project_label,
        parent=root or module or repository or database,
        chain_index=-1,
        order=0,
        summary='项目知识库业务根节点',
        roadmap_path=[project_label],
        metadata={'project_id': space.project_id, 'space_id': space.id},
    ) if project_label and (root or module or repository or database) else None

    x_root = 0
    x_project = 190
    x_module = 390
    x_menu = 610
    x_page = 830
    x_section = 1050
    x_function = 1270
    x_operation = 1490
    x_component = 1710
    x_file = 1930
    x_api = 2150
    x_backend_file = 2370
    x_symbol = 2540
    x_data = 2760
    x_field = 2950

    ui_objects = list(
        objects_qs
        .filter(object_type__in=['platform', 'module', 'menu', 'page', 'tab'])
        .order_by('object_type', 'name', 'id')[:2500]
    )
    ui_ids = [obj.id for obj in ui_objects]
    ui_by_id = {obj.id: obj for obj in ui_objects}
    ui_children = defaultdict(list)
    ui_relation_by_pair = {}
    if ui_ids:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id__in=ui_ids, target_id__in=ui_ids, relation_type='contains')
            .order_by('source_id', 'target__object_type', 'target__name', 'id')[:8000]
        ):
            ui_children[relation.source_id].append(relation)
            ui_relation_by_pair[(relation.source_id, relation.target_id, relation.relation_type)] = relation

    page_candidates = collect_page_chain_candidates(ui_by_id, ui_children, root=root, module=module)
    page_ids = [page.id for _, page in page_candidates]
    page_out_relations = []
    page_out_by_source = defaultdict(list)
    if page_ids:
        page_out_relations = list(
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id__in=page_ids)
            .filter(relation_type__in=['calls', 'implements', 'reads', 'writes', 'uses'])
            .filter(target__object_type__in=['api', 'component', 'table', 'field', 'file'])
            .order_by('-weight', 'id')[:10000]
        )
        for relation in page_out_relations:
            page_out_by_source[relation.source_id].append(relation)

    ui_blueprints_by_page = {}
    scored_candidates = []
    for menu, page in page_candidates:
        blueprint = build_ui_chain_blueprint(page, menu=menu, module=module)
        ui_blueprints_by_page[page.id] = blueprint
        score = score_page_chain(page, page_out_by_source.get(page.id) or [], has_menu=bool(menu), blueprint=blueprint)
        scored_candidates.append((score, menu, page))
    scored_candidates.sort(key=lambda item: (
        -item[0],
        asset_object_path(item[1]),
        asset_object_path(item[2]),
        item[2].id,
    ))
    max_chains = max(3, min(8, limit // 32))
    selected_candidates = []
    seen_pages = set()
    for score, menu, page in scored_candidates:
        if page.id in seen_pages:
            continue
        selected_candidates.append((menu, page, score))
        seen_pages.add(page.id)
        if len(selected_candidates) >= max_chains:
            break
    if not selected_candidates:
        fallback_pages = list(objects_qs.filter(object_type__in=['page', 'tab']).order_by('page_path', 'name', 'id')[:max_chains])
        selected_candidates = [(None, page, 1) for page in fallback_pages]

    file_objects = [
        obj for obj in objects_qs.filter(object_type='file').order_by('source_ref', 'name', 'id')[:5000]
        if is_primary_code_file(obj)
    ]
    files_by_path = {normalized_asset_path(obj.source_ref or obj.name): obj for obj in file_objects}
    files_by_basename = defaultdict(list)
    for obj in file_objects:
        files_by_basename[Path(obj.source_ref or obj.name).stem.lower()].append(obj)
    repo_file_relation_by_target = {}
    if repository and file_objects:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id=repository.id, relation_type='contains', target__object_type='file')
            .order_by('target__source_ref', 'id')[:8000]
        ):
            repo_file_relation_by_target[relation.target_id] = relation

    schema_tables = list(objects_qs.filter(object_type='table').order_by('db_table', 'name', 'id')[:5000])
    schema_table_ids = {obj.id for obj in schema_tables if is_confirmed_schema_table(obj)}
    schema_fields = list(objects_qs.filter(object_type='field').order_by('db_table', 'field_name', 'name', 'id')[:12000])
    schema_field_ids = {obj.id for obj in schema_fields if is_confirmed_schema_field(obj)}
    table_by_name = {}
    for table in schema_tables:
        name = table.db_table or table.name
        if not name:
            continue
        if name not in table_by_name or is_confirmed_schema_table(table):
            table_by_name[name] = table
    tables_by_app = defaultdict(list)
    for table in schema_tables:
        app_label = (table.metadata or {}).get('app_label') or infer_app_key_from_table_name(table.db_table or table.name)
        if app_label and is_confirmed_schema_table(table):
            tables_by_app[app_label].append(table)

    selected_page_ids = [page.id for _, page, _ in selected_candidates]
    selected_page_out_by_source = defaultdict(list)
    if selected_page_ids:
        for relation in page_out_relations:
            if relation.source_id in selected_page_ids:
                selected_page_out_by_source[relation.source_id].append(relation)

    candidate_file_ids = set()
    candidate_api_ids = set()
    for relations in selected_page_out_by_source.values():
        for relation in relations:
            if relation.target.object_type == 'api':
                candidate_api_ids.add(relation.target_id)
            if relation.target.object_type == 'file':
                candidate_file_ids.add(relation.target_id)
            if relation.target.object_type == 'component':
                for file_obj in find_files_for_component(relation.target, files_by_path, files_by_basename)[:2]:
                    candidate_file_ids.add(file_obj.id)
    for _, page, _ in selected_candidates:
        for file_obj in find_files_for_page(page, files_by_path, files_by_basename)[:2]:
            candidate_file_ids.add(file_obj.id)

    file_api_rels_by_source = defaultdict(list)
    if candidate_file_ids:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id__in=candidate_file_ids, relation_type='calls', target__object_type='api')
            .order_by('-weight', 'id')[:5000]
        ):
            file_api_rels_by_source[relation.source_id].append(relation)
            candidate_api_ids.add(relation.target_id)

    candidate_apis = list(objects_qs.filter(id__in=candidate_api_ids, object_type='api')) if candidate_api_ids else []
    for api in candidate_apis:
        for file_obj in find_backend_files_for_api(api, files_by_path)[:3]:
            candidate_file_ids.add(file_obj.id)

    code_rels_by_source = defaultdict(list)
    if candidate_file_ids or candidate_api_ids:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space)
            .filter(Q(source_id__in=candidate_file_ids) | Q(source_id__in=candidate_api_ids))
            .filter(relation_type__in=['contains', 'calls', 'reads', 'writes', 'uses', 'references'])
            .filter(target__object_type__in=['api', 'table', 'field', 'class', 'method', 'function'])
            .order_by('-weight', 'id')[:20000]
        ):
            if relation.target.object_type == 'api':
                candidate_api_ids.add(relation.target_id)
            code_rels_by_source[relation.source_id].append(relation)

    table_field_rels_by_source = defaultdict(list)
    table_ids_for_fields = set(schema_table_ids)
    db_table_relation_by_target = {}
    if database and table_ids_for_fields:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id=database.id, relation_type='contains', target_id__in=table_ids_for_fields)
            .order_by('target__db_table', 'id')[:10000]
        ):
            db_table_relation_by_target[relation.target_id] = relation
    if table_ids_for_fields:
        for relation in (
            KnowledgeRelation.objects
            .select_related('source', 'target')
            .filter(space=space, source_id__in=table_ids_for_fields, relation_type='contains', target__object_type='field')
            .order_by('source__db_table', 'target__metadata__ordinal', 'target__field_name', 'target__name', 'id')[:30000]
        ):
            table_field_rels_by_source[relation.source_id].append(relation)

    chain_count = max(1, len(selected_candidates))
    row_gap = 230
    y_origin = -((chain_count - 1) * row_gap) / 2
    if root:
        touch_node(root, branch='root', lane='root', rank=0, x=x_root, y=0, evidence='root')
    if project_node and root:
        touch_node(project_node, branch='ui', lane='ui', rank=1, x=x_project, y=0, evidence='project')
        add_edge(root, project_node, 'contains', '项目', branch='ui', inferred=True, evidence='root-project')
    elif project_node:
        touch_node(project_node, branch='ui', lane='ui', rank=1, x=x_project, y=0, evidence='project')
    module_parent = project_node or root
    if module and module_parent and module.id != module_parent.id:
        touch_node(module, branch='ui', lane='ui', rank=2, x=x_module, y=0, evidence='indexed')
        relation = ui_relation_by_pair.get((root.id, module.id, 'contains')) if root and module_parent is root else None
        add_edge(module_parent, module, 'contains', '包含模块', relation=relation, branch='ui', inferred=not bool(relation), evidence='project-module')
    elif module:
        touch_node(module, branch='ui', lane='ui', rank=2, x=x_module if module_parent and module.id != module_parent.id else x_project, y=0, evidence='indexed')
    if repository and root:
        touch_node(repository, branch='code', lane='code', rank=1, x=x_project, y=58, evidence='repository')
        add_edge(root, repository, 'uses', '代码仓库', branch='code', inferred=True, evidence='repository-config')
    if database and root:
        touch_node(database, branch='data', lane='data', rank=1, x=x_project, y=116, evidence='database')
        add_edge(root, database, 'uses', '数据库', branch='data', inferred=True, evidence='database-config')

    added_tables = set()
    compact_graph = limit <= 140
    api_limit_per_chain = 3 if compact_graph else 6
    component_limit_per_chain = 2 if compact_graph else 3
    file_limit_per_chain = 2 if compact_graph else 4
    table_limit_per_api = 1 if compact_graph else 3
    field_limit_per_table = 1 if compact_graph else 3
    symbol_limit_per_file = 1 if compact_graph else 2
    backend_symbol_limit = 1 if compact_graph else 3

    def add_code_file_node(file_obj, *, x, y, chain_index=None, evidence='code-file'):
        if not file_obj:
            return
        touch_node(file_obj, branch='code', lane='file', rank=5, x=x, y=y, chain_index=chain_index, evidence=evidence)
        if repository and repository.id != file_obj.id:
            relation = repo_file_relation_by_target.get(file_obj.id)
            add_edge(
                repository,
                file_obj,
                'contains',
                '仓库代码文件',
                relation=relation,
                branch='code',
                inferred=not bool(relation),
                evidence='repository-file',
            )

    def add_api_node(api_obj, *, x, y, chain_index=None, evidence='api'):
        if not api_obj:
            return
        touch_node(api_obj, branch='code', lane='api', rank=6, x=x, y=y, chain_index=chain_index, evidence=evidence)
        if repository and repository.id != api_obj.id:
            add_edge(
                repository,
                api_obj,
                'references',
                '仓库接口事实',
                branch='code',
                inferred=True,
                evidence='repository-api',
            )

    def add_database_table_node(table_obj, *, x, y, chain_index=None):
        if not table_obj or table_obj.object_type != 'table':
            return
        if database and database.id != table_obj.id:
            relation = db_table_relation_by_target.get(table_obj.id)
            add_edge(
                database,
                table_obj,
                'contains',
                '数据库表',
                relation=relation,
                branch='data',
                inferred=not bool(relation),
                evidence='database-table',
            )

    def add_data_target(source_obj, target_obj, relation=None, *, x=1680, y=0, chain_index=None, label='读写库表', branch='data'):
        if not source_obj or not target_obj:
            return
        if target_obj.object_type == 'field':
            table = table_by_name.get(target_obj.db_table)
            if table and (table.id in schema_table_ids or is_confirmed_schema_table(table)):
                touch_node(table, branch='data', lane='data', rank=8, x=x, y=y, chain_index=chain_index, evidence='schema')
                add_database_table_node(table, x=x, y=y, chain_index=chain_index)
                add_edge(source_obj, table, relation.relation_type if relation else 'uses', label, relation=relation if relation and relation.target_id == table.id else None, branch=branch, inferred=not bool(relation and relation.target_id == table.id), evidence='code-data')
                touch_node(target_obj, branch='data', lane='field', rank=9, x=x_field if x == x_data else x + 190, y=y, chain_index=chain_index, evidence='schema-field')
                add_edge(table, target_obj, 'contains', '包含字段', relation=find_table_field_relation(table_field_rels_by_source, table, target_obj), branch='data', inferred=False, evidence='schema-field')
                return
            if target_obj.id not in schema_field_ids:
                return
        if target_obj.object_type != 'table':
            return
        if target_obj.id not in schema_table_ids and not is_confirmed_schema_table(target_obj):
            return
        touch_node(target_obj, branch='data', lane='data', rank=8, x=x, y=y, chain_index=chain_index, evidence='schema')
        add_database_table_node(target_obj, x=x, y=y, chain_index=chain_index)
        added_tables.add(target_obj.id)
        add_edge(source_obj, target_obj, relation.relation_type if relation else 'uses', label, relation=relation, branch=branch, inferred=not bool(relation), evidence='code-data')
        for field_relation in pick_table_fields(table_field_rels_by_source.get(target_obj.id) or [], limit=field_limit_per_table):
            if node_count() >= limit:
                break
            field = field_relation.target
            touch_node(field, branch='data', lane='field', rank=9, x=x_field if x == x_data else x + 190, y=y, chain_index=chain_index, evidence='schema-field')
            add_edge(target_obj, field, 'contains', '包含字段', relation=field_relation, branch='data', evidence='schema-field')

    for index, (menu, page, _score) in enumerate(selected_candidates):
        if node_count() >= limit:
            break
        y = y_origin + index * row_gap
        code_y = y + 58
        ui_path_prefix = build_ui_display_prefix(space, module=module, menu=menu, page=page)
        parent = module if module else (project_node or root)
        if menu:
            menu_path = [*ui_path_prefix[:3]]
            touch_node(menu, branch='ui', lane='ui', rank=3, x=x_menu, y=y, chain_index=index, evidence='menu', roadmap_path=menu_path)
            if parent and parent.id != menu.id:
                relation = ui_relation_by_pair.get((parent.id, menu.id, 'contains'))
                add_edge(parent, menu, 'contains', '包含菜单', relation=relation, branch='ui', inferred=not bool(relation), evidence='menu-parent')
        page_path = [*ui_path_prefix[:4]]
        touch_node(page, branch='ui', lane='ui', rank=4, x=x_page, y=y, chain_index=index, evidence='page', roadmap_path=page_path)
        if menu:
            relation = ui_relation_by_pair.get((menu.id, page.id, 'contains'))
            add_edge(menu, page, 'contains', '页面/页签', relation=relation, branch='ui', inferred=not bool(relation), evidence='menu-page')
        elif parent and parent.id != page.id:
            add_edge(parent, page, 'contains', '页面/页签', branch='ui', inferred=True, evidence='page-parent')

        ui_branch_anchor = page
        ui_branch_anchors = []
        for child_relation in ui_children.get(page.id) or []:
            child = child_relation.target
            if child.object_type == 'function' and child.source_type == 'code_symbol':
                continue
            if child.object_type not in {'function', 'operation'} or node_count() >= limit:
                continue
            child_path = [*page_path, child.name]
            touch_node(child, branch='ui', lane='ui', rank=6 if child.object_type == 'function' else 7, x=x_function if child.object_type == 'function' else x_operation, y=y, chain_index=index, evidence='page-operation', roadmap_path=child_path)
            ui_branch_anchor = child
            ui_branch_anchors.append(child)
            add_edge(page, child, child_relation.relation_type, child_relation.label or '功能/操作项', relation=child_relation, branch='ui', evidence='page-operation')

        blueprint = ui_blueprints_by_page.get(page.id) or build_ui_chain_blueprint(page, menu=menu, module=module)
        operation_anchor_candidates = []
        for section_index, section in enumerate(blueprint.get('sections') or []):
            if node_count() >= limit:
                break
            section_label = normalize_virtual_label(section.get('label'), fallback=page.name or '页面板块')
            section_path = [*page_path, section_label]
            section_node = create_virtual_node(
                'section',
                section_label,
                parent=page,
                chain_index=index,
                order=section_index,
                summary=f'{page.name} 页面板块',
                roadmap_path=section_path,
                metadata={'source': blueprint.get('source')},
            )
            section_y = y + section_index * 34
            touch_node(section_node, branch='ui', lane='ui', rank=5, x=x_section, y=section_y, chain_index=index, evidence=f"{blueprint.get('source')}-section", roadmap_path=section_path)
            add_edge(page, section_node, 'contains', '页面板块', branch='ui', inferred=True, evidence=f"{blueprint.get('source')}-section")
            for function_index, function in enumerate(section.get('functions') or []):
                if node_count() >= limit:
                    break
                function_label = normalize_virtual_label(function.get('label'), fallback=section_label)
                function_path = [*section_path, function_label]
                function_node = create_virtual_node(
                    'function',
                    function_label,
                    parent=page,
                    chain_index=index,
                    order=(section_index + 1) * 100 + function_index,
                    summary=f'{section_label} 功能',
                    roadmap_path=function_path,
                    metadata={'source': blueprint.get('source')},
                )
                function_y = section_y + function_index * 32
                touch_node(function_node, branch='ui', lane='ui', rank=6, x=x_function, y=function_y, chain_index=index, evidence=f"{blueprint.get('source')}-function", roadmap_path=function_path)
                add_edge(section_node, function_node, 'contains', '功能', branch='ui', inferred=True, evidence=f"{blueprint.get('source')}-function")
                operation_items = function.get('operations') or [{'label': default_operation_label(function_label)}]
                for operation_index, operation in enumerate(operation_items):
                    if node_count() >= limit:
                        break
                    operation_label = normalize_virtual_label(operation.get('label') if isinstance(operation, dict) else operation, fallback=function_label)
                    operation_path = [*function_path, operation_label]
                    operation_node = create_virtual_node(
                        'operation',
                        operation_label,
                        parent=page,
                        chain_index=index,
                        order=(section_index + 1) * 10000 + (function_index + 1) * 100 + operation_index,
                        summary=f'{function_label} 操作项',
                        roadmap_path=operation_path,
                        metadata={'source': blueprint.get('source')},
                    )
                    operation_y = function_y + operation_index * 28
                    touch_node(operation_node, branch='ui', lane='ui', rank=7, x=x_operation, y=operation_y, chain_index=index, evidence=f"{blueprint.get('source')}-operation", roadmap_path=operation_path)
                    add_edge(function_node, operation_node, 'contains', '操作项', branch='ui', inferred=True, evidence=f"{blueprint.get('source')}-operation")
                    operation_anchor_candidates.append(operation_node)
        if operation_anchor_candidates:
            ui_branch_anchor = operation_anchor_candidates[0]
            ui_branch_anchors = operation_anchor_candidates
        elif ui_branch_anchors:
            ui_branch_anchor = ui_branch_anchors[0]
        else:
            ui_branch_anchors = [page]

        def add_edges_from_ui_anchors(target, relation_type, label, *, relation=None, evidence='ui-bridge'):
            if not target:
                return
            anchors = ui_branch_anchors or [ui_branch_anchor]
            for anchor_index, anchor in enumerate(anchors):
                add_edge(
                    anchor,
                    target,
                    relation_type,
                    label,
                    relation=relation if anchor_index == 0 else None,
                    branch='bridge',
                    inferred=anchor_index > 0 or not bool(relation),
                    evidence=evidence,
                )

        chain_files = []
        chain_apis = []
        chain_components = []
        chain_data_sources = []

        for relation in selected_page_out_by_source.get(page.id) or []:
            target = relation.target
            if target.object_type == 'component':
                component_y = code_y + len(chain_components) * 28
                touch_node(target, branch='code', lane='component', rank=8, x=x_component, y=component_y, chain_index=index, evidence='page-component')
                add_edge(page, target, relation.relation_type, relation.label or '实现组件', relation=relation, branch='bridge', evidence='page-component')
                if ui_branch_anchor.id != page.id:
                    add_edges_from_ui_anchors(target, relation.relation_type, '操作项-组件', evidence='operation-component')
                chain_components.append(target)
            elif target.object_type == 'api':
                api_y = code_y + len(chain_apis) * 30
                add_api_node(target, x=x_api, y=api_y, chain_index=index, evidence='page-api')
                add_edge(page, target, relation.relation_type, relation.label or '调用接口', relation=relation, branch='bridge', evidence='page-api')
                if ui_branch_anchor.id != page.id:
                    add_edges_from_ui_anchors(target, relation.relation_type, '操作项-接口', evidence='operation-api')
                chain_apis.append(target)
            elif target.object_type in {'table', 'field'}:
                chain_data_sources.append((ui_branch_anchor, target, relation))

        for file_obj in find_files_for_page(page, files_by_path, files_by_basename)[:2]:
            if node_count() >= limit:
                break
            file_y = code_y + len(chain_files) * 30
            add_code_file_node(file_obj, x=x_file, y=file_y, chain_index=index, evidence='page-file')
            add_edge(page, file_obj, 'implements', '页面代码', branch='bridge', inferred=True, evidence='page-component-path')
            if ui_branch_anchor.id != page.id:
                add_edges_from_ui_anchors(file_obj, 'implements', '操作项-代码文件', evidence='operation-file')
            chain_files.append(file_obj)

        for component in chain_components[:component_limit_per_chain]:
            for file_obj in find_files_for_component(component, files_by_path, files_by_basename)[:2]:
                if node_count() >= limit:
                    break
                file_y = code_y + len(chain_files) * 30
                add_code_file_node(file_obj, x=x_file, y=file_y, chain_index=index, evidence='component-file')
                add_edge(component, file_obj, 'implements', '组件代码', branch='code', inferred=True, evidence='component-file-match')
                chain_files.append(file_obj)

        chain_files = dedupe_objects(chain_files)[:file_limit_per_chain]
        for file_index, file_obj in enumerate(chain_files):
            for relation in file_api_rels_by_source.get(file_obj.id, [])[:4]:
                if node_count() >= limit:
                    break
                api = relation.target
                api_y = code_y + (len(chain_apis) + file_index) * 30
                add_api_node(api, x=x_api, y=api_y, chain_index=index, evidence='frontend-api')
                add_edge(file_obj, api, relation.relation_type, relation.label or '调用接口', relation=relation, branch='code', evidence='frontend-api')
                chain_apis.append(api)
            for symbol_index, relation in enumerate(pick_code_symbols(code_rels_by_source.get(file_obj.id) or [], limit=symbol_limit_per_file)):
                if node_count() >= limit:
                    break
                symbol = relation.target
                touch_node(symbol, branch='code', lane='symbol', rank=7, x=x_api, y=code_y + 88 + symbol_index * 28, chain_index=index, evidence='frontend-symbol')
                add_edge(file_obj, symbol, relation.relation_type, relation.label or '包含方法', relation=relation, branch='code', evidence='frontend-symbol')

        chain_apis = dedupe_objects(chain_apis)[:api_limit_per_chain]
        for api_index, api in enumerate(chain_apis):
            backend_files = find_backend_files_for_api(api, files_by_path)[:2]
            api_y = code_y + api_index * 34
            for backend_file_index, backend_file in enumerate(backend_files):
                if node_count() >= limit:
                    break
                backend_y = api_y + backend_file_index * 28
                add_code_file_node(backend_file, x=x_backend_file, y=backend_y, chain_index=index, evidence='backend-file')
                add_edge(api, backend_file, 'implements', '后端实现', branch='code', inferred=True, evidence='api-backend-file')
                chain_files.append(backend_file)
                for symbol_index, relation in enumerate(pick_code_symbols(code_rels_by_source.get(backend_file.id) or [], limit=backend_symbol_limit)):
                    if node_count() >= limit:
                        break
                    symbol = relation.target
                    touch_node(symbol, branch='code', lane='symbol', rank=8, x=x_symbol, y=backend_y + 34 + symbol_index * 26, chain_index=index, evidence='backend-symbol')
                    add_edge(backend_file, symbol, relation.relation_type, relation.label or '代码方法', relation=relation, branch='code', evidence='backend-symbol')

            data_relations = pick_data_relations(code_rels_by_source.get(api.id) or [], schema_table_ids, schema_field_ids, limit=2 if compact_graph else 5)
            for data_index, relation in enumerate(data_relations):
                if node_count() >= limit:
                    break
                add_data_target(api, relation.target, relation, x=x_data, y=api_y + data_index * 30, chain_index=index, label=relation.label or '接口读写库表')

            app_key = infer_app_key_from_api_path(api.api_path)
            for table_index, table in enumerate(tables_by_app.get(app_key, [])[:table_limit_per_api]):
                if node_count() >= limit:
                    break
                add_data_target(api, table, None, x=x_data, y=api_y + (len(data_relations) + table_index) * 30, chain_index=index, label='接口关联业务表')

        for file_index, file_obj in enumerate(dedupe_objects(chain_files)[:(3 if compact_graph else 6)]):
            data_relations = pick_data_relations(code_rels_by_source.get(file_obj.id) or [], schema_table_ids, schema_field_ids, limit=1 if compact_graph else 3)
            for data_index, relation in enumerate(data_relations):
                if node_count() >= limit:
                    break
                add_data_target(file_obj, relation.target, relation, x=x_data, y=code_y + 112 + file_index * 28 + data_index * 28, chain_index=index, label=relation.label or '代码读写库表')

        for data_index, (source_obj, target_obj, relation) in enumerate(chain_data_sources[:3]):
            if node_count() >= limit:
                break
            add_data_target(source_obj, target_obj, relation, x=x_data, y=code_y + 128 + data_index * 30, chain_index=index, label=relation.label or '页面关联库表', branch='bridge')

    nodes = []
    for obj_id in node_order[:limit]:
        state = node_state.get(obj_id)
        if not state:
            continue
        obj = state['obj']
        payload = serialize_asset_node(obj)
        positions = state['positions'] or [(0, 0)]
        x = sum(item[0] for item in positions) / len(positions)
        y = sum(item[1] for item in positions) / len(positions)
        metadata = dict(payload.get('metadata') or {})
        metadata['asset_graph'] = {
            'graph_type': 'page_api_table',
            'branches': sorted(state['branches']),
            'lanes': sorted(state['lanes']),
            'rank': state['rank'],
            'chain_indices': sorted(state['chain_indices']),
            'evidence': sorted(state['evidence']),
        }
        payload['metadata'] = metadata
        if state.get('display_roadmap_paths'):
            payload['roadmap_path'] = max(state['display_roadmap_paths'], key=len)
        payload['x'] = round(x, 2)
        payload['y'] = round(y, 2)
        payload['fixed'] = True
        payload['draggable'] = True
        payload['asset_graph_rank'] = state['rank']
        payload['asset_graph_lanes'] = sorted(state['lanes'])
        nodes.append(payload)

    visible_node_ids = {node['id'] for node in nodes}
    edges = [
        edge for edge in edges
        if edge.get('source') in visible_node_ids and edge.get('target') in visible_node_ids
    ][:limit * 4]
    return {
        'graph_type': 'page_api_table',
        'label': graph_def['label'],
        'nodes': nodes,
        'edges': edges,
        'categories': build_graph_categories_from_nodes(nodes),
        'query': '',
        'center_table': '',
        'er_view': '',
        'layout': {
            'type': 'layered_chain',
            'fixed_positions': True,
            'lanes': ['root', 'ui', 'component', 'file', 'symbol', 'api', 'data', 'field'],
        },
        'truncated': len(scored_candidates) > len(selected_candidates) or KnowledgeObject.objects.filter(space=space).count() > len(nodes),
        'summary': {
            'chain_count': len(selected_candidates),
            'selected_chain_count': min(len(selected_candidates), max_chains),
            'table_count': len(added_tables),
        },
    }


def first_object(objects_qs, object_type):
    return objects_qs.filter(object_type=object_type).order_by('name', 'id').first()


def collect_page_chain_candidates(ui_by_id, ui_children, *, root=None, module=None):
    parent = module or root
    menus = []
    if parent:
        menus = [relation.target for relation in ui_children.get(parent.id, []) if relation.target.object_type == 'menu']
    if not menus:
        menus = [obj for obj in ui_by_id.values() if obj.object_type == 'menu']
    records = []
    for menu in sorted(menus, key=asset_object_path):
        pages = [relation.target for relation in ui_children.get(menu.id, []) if relation.target.object_type in {'page', 'tab'}]
        for page in sorted(pages, key=asset_object_path):
            records.append((menu, page))
    existing_page_ids = {page.id for _, page in records}
    for page in sorted([obj for obj in ui_by_id.values() if obj.object_type in {'page', 'tab'} and obj.id not in existing_page_ids], key=asset_object_path):
        if page.page_path or page.tab_key or len(page.roadmap_path or []) >= 3:
            parent_menu = find_menu_for_page_by_path(page, menus)
            records.append((parent_menu, page))
    if not records:
        for page in sorted([obj for obj in ui_by_id.values() if obj.object_type in {'page', 'tab'}], key=asset_object_path):
            records.append((None, page))
    return records


def find_menu_for_page_by_path(page, menus):
    page_path = page.roadmap_path or []
    if len(page_path) >= 2:
        menu_label = normalize_roadmap_token(page_path[-2])
        for menu in menus:
            if normalize_roadmap_token(menu.name) == menu_label:
                return menu
    primary_label = normalize_roadmap_token((page.metadata or {}).get('primary') if isinstance(page.metadata, dict) else '')
    for menu in menus:
        if primary_label and normalize_roadmap_token(menu.name) == primary_label:
            return menu
    return None


def score_page_chain(page, relations, *, has_menu=False, blueprint=None):
    score = 1
    if has_menu:
        score += 3
    if page.page_path:
        score += 2
    if page.component_path:
        score += 2
    if page.tab_key:
        score += 3
    if page.roadmap_path and not any(looks_like_path_label(item) for item in page.roadmap_path):
        score += len(page.roadmap_path)
    if page.name and looks_like_path_label(page.name):
        score -= 10
    if blueprint and blueprint.get('source') == 'roadmap':
        score += 12
    score += count_blueprint_leaf_nodes(blueprint or build_ui_chain_blueprint(page)) * 2
    for relation in relations:
        target_type = relation.target.object_type
        if target_type == 'api':
            score += 8
        elif target_type == 'component':
            score += 5
        elif target_type in {'table', 'field'}:
            score += 3
        elif target_type == 'file':
            score += 2
    return score


def build_ui_display_prefix(space, *, module=None, menu=None, page=None):
    project_label = normalize_virtual_label(getattr(space.project, 'name', '') or space.name, fallback='项目')
    module_label = normalize_virtual_label(module.name if module else '', fallback='')
    menu_label = normalize_virtual_label(menu.name if menu else '', fallback='')
    page_label = normalize_virtual_label((page.name if page else '') or (page.page_path if page else ''), fallback='页面')
    path = [project_label]
    for label in [module_label, menu_label, page_label]:
        if label and normalize_roadmap_token(label) not in {normalize_roadmap_token(item) for item in path}:
            path.append(label)
    return path


def build_virtual_ui_chain(page, *, max_items=2):
    blueprint = build_ui_chain_blueprint(page)
    items = []
    for section in blueprint.get('sections') or []:
        items.append({'type': 'section', 'label': section.get('label')})
        for function in section.get('functions') or []:
            items.append({'type': 'function', 'label': function.get('label')})
            for operation in function.get('operations') or []:
                items.append({'type': 'operation', 'label': operation.get('label')})
    compacted = []
    seen = set()
    for item in items:
        label = normalize_virtual_label(item.get('label'), fallback=page.name or page.page_path or 'operation')
        key = (item.get('type') or 'function', normalize_roadmap_token(label))
        if not label or key in seen:
            continue
        seen.add(key)
        compacted.append({'type': item.get('type') or 'function', 'label': label})
        if max_items and len(compacted) >= max_items:
            break
    return compacted


def build_ui_chain_blueprint(page, *, menu=None, module=None):
    roadmap_node = find_roadmap_node_for_page(page, menu=menu, module=module)
    sections = build_sections_from_roadmap_node(roadmap_node) if roadmap_node else []
    source = 'roadmap' if sections else 'metadata'
    if not sections:
        sections = build_fallback_ui_sections(page)
    return {
        'sections': sections,
        'source': source,
        'roadmap_path': roadmap_node.get('path') if roadmap_node else [],
    }


def build_sections_from_roadmap_node(node):
    if not node:
        return []
    sections = []
    loose_operations = []
    for child in node.get('children') or []:
        label = normalize_virtual_label(child.get('label'))
        if not label:
            continue
        if child.get('children'):
            functions = []
            for function_or_operation in child.get('children') or []:
                child_label = normalize_virtual_label(function_or_operation.get('label'))
                if not child_label:
                    continue
                if function_or_operation.get('children'):
                    operations = [
                        {'label': normalize_virtual_label(operation.get('label'), fallback=child_label)}
                        for operation in function_or_operation.get('children') or []
                        if normalize_virtual_label(operation.get('label'), fallback='')
                    ]
                    functions.append({
                        'label': child_label,
                        'operations': dedupe_operation_items(operations or [{'label': default_operation_label(child_label)}]),
                    })
                else:
                    function_label, operation_label = infer_function_operation_pair(child_label)
                    functions.append({
                        'label': function_label,
                        'operations': [{'label': operation_label}],
                    })
            sections.append({
                'label': label,
                'functions': merge_function_operation_groups(functions),
            })
        else:
            loose_operations.append(label)
    if loose_operations:
        section_label = normalize_virtual_label(node.get('label'), fallback='页面功能')
        sections.append({
            'label': section_label,
            'functions': group_operation_labels(loose_operations),
        })
    return [section for section in sections if section.get('functions')]


def build_fallback_ui_sections(page):
    metadata = page.metadata or {}
    raw_cells = metadata.get('raw_cells') if isinstance(metadata.get('raw_cells'), list) else []
    operations = [
        normalize_virtual_label(item, fallback='')
        for item in (metadata.get('operations') if isinstance(metadata.get('operations'), list) else [])
        if normalize_virtual_label(item, fallback='')
    ]
    if not operations and raw_cells:
        operation_candidates = []
        if len(raw_cells) >= 7:
            operation_candidates.extend([raw_cells[0], raw_cells[3]])
        elif len(raw_cells) >= 4:
            operation_candidates.extend([raw_cells[1], raw_cells[3]])
        for value in operation_candidates:
            if value and not looks_like_path_label(value) and not looks_like_asset_reference(value):
                operations.append(normalize_virtual_label(value, fallback=''))
    page_label = normalize_virtual_label(page.name or page.page_path, fallback='页面')
    if not operations:
        operations = [default_operation_label(page_label)]
    return [{
        'label': page_label,
        'functions': group_operation_labels(operations),
    }]


def group_operation_labels(operation_labels):
    functions = []
    for operation_label in operation_labels:
        function_label, normalized_operation_label = infer_function_operation_pair(operation_label)
        functions.append({
            'label': function_label,
            'operations': [{'label': normalized_operation_label}],
        })
    return merge_function_operation_groups(functions)


def merge_function_operation_groups(functions):
    grouped = []
    by_label = {}
    for function in functions:
        function_label = normalize_virtual_label(function.get('label'), fallback='功能')
        function_key = normalize_roadmap_token(function_label)
        if not function_key:
            continue
        target = by_label.get(function_key)
        if not target:
            target = {'label': function_label, 'operations': []}
            by_label[function_key] = target
            grouped.append(target)
        target['operations'].extend(function.get('operations') or [])
    for function in grouped:
        function['operations'] = dedupe_operation_items(function.get('operations') or [])
        if not function['operations']:
            function['operations'] = [{'label': default_operation_label(function['label'])}]
    return grouped


def dedupe_operation_items(operations):
    result = []
    seen = set()
    for operation in operations:
        label = normalize_virtual_label(operation.get('label') if isinstance(operation, dict) else operation, fallback='')
        key = normalize_roadmap_token(label)
        if not label or key in seen:
            continue
        seen.add(key)
        result.append({'label': label})
    return result


def infer_function_operation_pair(label):
    operation_label = normalize_virtual_label(label, fallback='操作项')
    action_verbs = [
        '批量删除', '启用停用', '启动或处理', '复制分享',
        '新增', '新建', '创建', '编辑', '删除', '查看', '跳转', '同步', '导入', '导出',
        '配置', '测试', '触发', '分析', '刷新', '分享', '启用', '停用', '提交', '审核',
        '关联', '指派', '变更', '上传', '解析', '维护', '设置', '复制', '执行', '恢复',
        '生成', '流转', '处理',
    ]
    for verb in sorted(action_verbs, key=len, reverse=True):
        if operation_label.startswith(verb) and len(operation_label) > len(verb):
            function_label = operation_label[len(verb):].strip(' ：:-/')
            if function_label:
                return normalize_virtual_label(function_label, fallback=operation_label), operation_label
    return operation_label, default_operation_label(operation_label)


def default_operation_label(function_label):
    label = normalize_virtual_label(function_label, fallback='操作项')
    if label.startswith(('查看', '新增', '新建', '创建', '编辑', '删除', '同步', '提交', '配置', '测试', '执行')):
        return label
    return normalize_virtual_label(f'查看{label}', fallback=label)


def count_blueprint_leaf_nodes(blueprint):
    count = 0
    for section in blueprint.get('sections') or []:
        for function in section.get('functions') or []:
            count += max(1, len(function.get('operations') or []))
    return max(1, count)


def get_manual_roadmap_index():
    global ROADMAP_TREE_CACHE
    if ROADMAP_TREE_CACHE is not None:
        return ROADMAP_TREE_CACHE
    root_dir = Path(__file__).resolve().parents[2]
    roadmap_path = root_dir / 'docs' / 'manual-quality-knowledge-roadmap.md'
    nodes = []
    roots = []
    if roadmap_path.exists():
        try:
            text = roadmap_path.read_text(encoding='utf-8')
            blocks = re.findall(r'```text\s*(.*?)```', text, flags=re.S)
            tree_text = max(blocks, key=lambda block: block.count('├') + block.count('└')) if blocks else ''
            stack = {}
            for raw_line in tree_text.splitlines():
                label, depth = parse_roadmap_tree_line(raw_line)
                if not label:
                    continue
                parent = stack.get(depth - 1) if depth > 0 else None
                path = [*(parent.get('path') if parent else []), label]
                node = {'label': label, 'depth': depth, 'path': path, 'children': []}
                if parent:
                    parent.setdefault('children', []).append(node)
                else:
                    roots.append(node)
                stack[depth] = node
                for stale_depth in [item for item in stack if item > depth]:
                    stack.pop(stale_depth, None)
                nodes.append(node)
        except OSError:
            nodes = []
            roots = []
    if not nodes:
        roots, nodes = build_default_manual_roadmap_tree()
    ROADMAP_TREE_CACHE = {'roots': roots, 'nodes': nodes}
    return ROADMAP_TREE_CACHE


def build_default_manual_roadmap_tree():
    roots = []
    nodes = []
    by_path = {}

    def ensure_node(path):
        key = tuple(path)
        node = by_path.get(key)
        if node:
            return node
        parent = ensure_node(path[:-1]) if len(path) > 1 else None
        node = {
            'label': path[-1],
            'depth': len(path) - 1,
            'path': list(path),
            'children': [],
        }
        by_path[key] = node
        if parent:
            parent.setdefault('children', []).append(node)
        else:
            roots.append(node)
        nodes.append(node)
        return node

    ensure_node(['TestHub平台'])
    ensure_node(['TestHub平台', '思源质量'])
    for module_label, page_label, section_label, operations in DEFAULT_MANUAL_ROADMAP_ENTRIES:
        ensure_node(['TestHub平台', '思源质量', module_label])
        ensure_node(['TestHub平台', '思源质量', module_label, page_label])
        ensure_node(['TestHub平台', '思源质量', module_label, page_label, section_label])
        for operation_label in operations:
            ensure_node(['TestHub平台', '思源质量', module_label, page_label, section_label, operation_label])
    return roots, nodes


def parse_roadmap_tree_line(raw_line):
    line = str(raw_line or '').rstrip()
    if not line:
        return '', 0
    branch = re.search(r'[├└]─\s*(.+)$', line)
    if branch:
        prefix = line[:branch.start()]
        return normalize_virtual_label(branch.group(1), fallback=''), (len(prefix) // 3) + 1
    if '│' in line or '├' in line or '└' in line:
        return '', 0
    return normalize_virtual_label(line, fallback=''), 0


def find_roadmap_node_for_page(page, *, menu=None, module=None):
    nodes = get_manual_roadmap_index().get('nodes') or []
    if not nodes:
        return None
    candidates = []
    if page.roadmap_path:
        candidates.append(page.roadmap_path)
        if len(page.roadmap_path) >= 2:
            candidates.append(page.roadmap_path[-2:])
        if len(page.roadmap_path) >= 3:
            candidates.append(page.roadmap_path[-3:])
    if module and menu:
        candidates.append([module.name, menu.name, page.name])
    if menu:
        candidates.append([menu.name, page.name])
    if page.name:
        candidates.append([page.name])
    metadata = page.metadata or {}
    raw_cells = metadata.get('raw_cells') if isinstance(metadata.get('raw_cells'), list) else []
    if len(raw_cells) >= 2:
        candidates.append([raw_cells[0], raw_cells[1]])
    best = None
    best_score = (-1, -1, 0)
    for candidate in candidates:
        normalized_candidate = [normalize_roadmap_token(item) for item in candidate if normalize_roadmap_token(item)]
        if not normalized_candidate:
            continue
        for node in nodes:
            normalized_path = [normalize_roadmap_token(item) for item in node.get('path') or [] if normalize_roadmap_token(item)]
            if len(normalized_path) < len(normalized_candidate):
                continue
            if normalized_path[-len(normalized_candidate):] != normalized_candidate:
                continue
            score = (
                1 if node.get('children') else 0,
                len(normalized_candidate),
                len(node.get('path') or []),
            )
            if score > best_score:
                best = node
                best_score = score
    return best


def normalize_roadmap_token(value):
    text = normalize_virtual_label(value, fallback='').lower()
    text = re.sub(r'[`"\'\s/、，,：:;；()\[\]（）【】]+', '', text)
    return text


def normalize_virtual_label(value, *, fallback=''):
    text = re.sub(r'[`，、]+', ' / ', str(value or '').strip())
    text = re.sub(r'\s+', ' ', text).strip(' /')
    if not text:
        text = str(fallback or '').strip()
    return text[:80]


def looks_like_asset_reference(value):
    text = str(value or '').strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered.endswith(('.vue', '.js', '.ts', '.py')) or any(suffix in lowered for suffix in ['.vue', '.js', '.ts', '.py']):
        return True
    if lowered.startswith('/api/') or lowered.startswith('get /') or lowered.startswith('post /'):
        return True
    if 'schema' in lowered or 'endpoint' in lowered:
        return True
    if re.fullmatch(r'[a-z][a-z0-9_]*(?:[`/, ]+[a-z][a-z0-9_]*)*', lowered):
        return True
    return False


def looks_like_path_label(value):
    text = str(value or '').strip().lower()
    return text.startswith('/') or text.startswith('http') or text.startswith('api:')


def slugify_asset_label(value):
    text = str(value or '').strip().lower()
    text = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', text)
    text = text.strip('-')
    return text[:48] or 'node'


def asset_object_path(obj):
    if not obj:
        return ''
    return (
        obj.page_path
        or obj.api_path
        or obj.db_table
        or obj.component_path
        or obj.source_ref
        or obj.name
        or ''
    )


def normalized_asset_path(value):
    return str(value or '').replace('\\', '/').strip()


def is_primary_code_file(obj):
    path = normalized_asset_path(obj.source_ref or obj.name).lower()
    if not path:
        return False
    if path.startswith('.tmp') or path.startswith('tmp_') or path.startswith('.codex-temp/'):
        return False
    if '/.codex-temp/' in path or '/node_modules/' in path or '/dist/' in path:
        return False
    if path.endswith('tests.py') or '/tests/' in path or path.endswith('.spec.ts') or path.endswith('.spec.js'):
        return False
    return True


def find_files_for_page(page, files_by_path, files_by_basename):
    candidates = []
    component_path = normalized_asset_path(page.component_path)
    if component_path:
        exact = files_by_path.get(component_path)
        if exact:
            candidates.append(exact)
        stem = Path(component_path).stem.lower()
        candidates.extend(files_by_basename.get(stem) or [])
    tab_key = str(page.tab_key or '').strip().lower()
    if tab_key:
        candidates.extend(files_by_basename.get(tab_key) or [])
    return dedupe_objects(candidates)


def find_files_for_component(component, files_by_path, files_by_basename):
    candidates = []
    component_path = normalized_asset_path(component.component_path)
    source_ref = normalized_asset_path(component.source_ref)
    for path in [component_path, source_ref]:
        if path and path.endswith(('.vue', '.js', '.ts', '.jsx', '.tsx', '.py')):
            exact = files_by_path.get(path)
            if exact:
                candidates.append(exact)
            candidates.extend(files_by_basename.get(Path(path).stem.lower()) or [])
    for value in [component.name, component.component_path, component.key.replace('component:', '') if component.key else '']:
        name = str(value or '').strip()
        if not name:
            continue
        candidates.extend(files_by_basename.get(Path(name).stem.lower()) or [])
    return dedupe_objects(candidates)


def find_backend_files_for_api(api, files_by_path):
    candidates = []
    source_ref = normalized_asset_path(api.source_ref)
    if source_ref.endswith('.py'):
        direct = files_by_path.get(source_ref)
        if direct:
            candidates.append(direct)
    app_key = infer_app_key_from_api_path(api.api_path)
    if app_key:
        for suffix in ['urls.py', 'views.py', 'serializers.py', 'models.py']:
            direct = files_by_path.get(f'apps/{app_key}/{suffix}')
            if direct:
                candidates.append(direct)
    return dedupe_objects(candidates)


def infer_app_key_from_api_path(api_path):
    value = str(api_path or '').strip('/')
    if not value:
        return ''
    parts = [part for part in value.split('/') if part]
    if parts and parts[0] == 'api':
        parts = parts[1:]
    if not parts:
        return ''
    segment = parts[0].replace('-', '_')
    aliases = {
        'auth': 'users',
        'quality_analysis': 'quality_analysis',
        'manual_testcases': 'testcases',
        'testcase': 'testcases',
        'testcases': 'testcases',
        'defect': 'defects',
        'defects': 'defects',
        'knowledge': 'knowledge',
        'projects': 'projects',
        'versions': 'versions',
        'workflow': 'workflow',
    }
    return aliases.get(segment, segment)


def infer_app_key_from_table_name(table_name):
    value = str(table_name or '').strip().lower()
    if not value:
        return ''
    app_aliases = {
        'quality_analysis': 'quality_analysis',
        'manual_testcase': 'testcases',
        'dev_self_test': 'testcases',
        'testcase': 'testcases',
        'defect': 'defects',
        'defects': 'defects',
        'knowledge': 'knowledge',
        'project': 'projects',
        'projects': 'projects',
        'version': 'versions',
        'versions': 'versions',
        'workflow': 'workflow',
        'users': 'users',
        'user': 'users',
    }
    for prefix, app_key in app_aliases.items():
        if value == prefix or value.startswith(f'{prefix}_'):
            return app_key
    return value.split('_', 1)[0]


def dedupe_objects(objects):
    result = []
    seen = set()
    for obj in objects:
        if not obj or obj.id in seen:
            continue
        seen.add(obj.id)
        result.append(obj)
    return result


def is_confirmed_schema_table(obj):
    if not obj or obj.object_type != 'table':
        return False
    metadata = obj.metadata or {}
    return obj.source_type in {'database_schema', 'django_model'} or bool(metadata.get('app_label') or metadata.get('schema') or metadata.get('scanner_source') == 'information_schema')


def is_confirmed_schema_field(obj):
    if not obj or obj.object_type != 'field':
        return False
    metadata = obj.metadata or {}
    return obj.source_type in {'database_schema', 'django_model'} or bool(metadata.get('field_type') or metadata.get('column_type') or metadata.get('scanner_source') == 'information_schema')


def pick_code_symbols(relations, *, limit=3):
    symbols = [
        relation for relation in relations
        if relation.relation_type == 'contains' and relation.target.object_type in {'class', 'method', 'function'}
    ]
    symbols.sort(key=lambda relation: (
        {'class': 0, 'method': 1, 'function': 2}.get(relation.target.object_type, 9),
        safe_int((relation.target.metadata or {}).get('line'), 999999),
        relation.target.name,
        relation.id,
    ))
    return symbols[:limit]


def pick_data_relations(relations, schema_table_ids, schema_field_ids, *, limit=5):
    candidates = []
    for relation in relations:
        target = relation.target
        if relation.relation_type not in {'reads', 'writes', 'uses', 'references'}:
            continue
        if target.object_type == 'table' and (target.id in schema_table_ids or is_confirmed_schema_table(target)):
            candidates.append(relation)
        elif target.object_type == 'field' and (target.id in schema_field_ids or is_confirmed_schema_field(target)):
            candidates.append(relation)
    candidates.sort(key=lambda relation: (
        {'writes': 0, 'reads': 1, 'references': 2, 'uses': 3}.get(relation.relation_type, 9),
        relation.target.db_table or relation.target.name,
        relation.target.field_name or relation.target.name,
        relation.id,
    ))
    return candidates[:limit]


def pick_table_fields(relations, *, limit=3):
    def field_priority(relation):
        field = relation.target
        metadata = field.metadata or {}
        column_key = str(metadata.get('column_key') or '').upper()
        return (
            0 if column_key == 'PRI' else 1,
            safe_int(metadata.get('ordinal'), 999999),
            field.field_name or field.name,
            relation.id,
        )
    ordered = sorted(relations, key=field_priority)
    return ordered[:limit]


def find_table_field_relation(table_field_rels_by_source, table, field):
    for relation in table_field_rels_by_source.get(table.id) or []:
        if relation.target_id == field.id:
            return relation
    return None


def build_graph_categories_from_nodes(nodes):
    type_order = {
        'platform': 1,
        'project': 2,
        'module': 3,
        'menu': 4,
        'page': 5,
        'tab': 6,
        'section': 7,
        'function': 8,
        'operation': 9,
        'component': 10,
        'repository': 11,
        'file': 12,
        'class': 13,
        'method': 14,
        'api': 15,
        'database': 16,
        'table': 17,
        'field': 18,
    }
    types = sorted({node.get('type') for node in nodes if node.get('type')}, key=lambda item: (type_order.get(item, 99), item))
    return [{'name': item, 'label': get_object_type_label(item)} for item in types]


def select_er_macro_graph(space, objects_qs, *, query='', limit=180):
    query = str(query or '').strip()
    tables_qs = objects_qs.filter(object_type='table')
    if query:
        tables_qs = tables_qs.filter(Q(db_table__icontains=query) | Q(name__icontains=query) | Q(summary__icontains=query) | Q(search_text__icontains=query))
    table_ids = list(tables_qs.order_by('db_table', 'name', 'id').values_list('id', flat=True)[:max(20, limit - 4)])
    database_ids = list(objects_qs.filter(object_type='database').order_by('name', 'id').values_list('id', flat=True)[:4])
    related_ids = set(database_ids)
    related_ids.update(table_ids)
    for relation in (
        KnowledgeRelation.objects
        .filter(space=space)
        .filter(Q(source_id__in=table_ids) | Q(target_id__in=table_ids))
        .filter(relation_type__in=['contains', 'related_to'])
        .order_by('-weight', 'id')[:limit * 3]
    ):
        related_ids.add(relation.source_id)
        related_ids.add(relation.target_id)
        if len(related_ids) >= limit:
            break
    objects_by_id = {obj.id: obj for obj in objects_qs.exclude(object_type='field').filter(id__in=related_ids)}
    return order_er_objects(objects_by_id, limit=limit)


def select_er_micro_graph(space, objects_qs, *, query='', limit=180):
    query = str(query or '').strip()
    tables_qs = objects_qs.filter(object_type='table')
    if query:
        tables_qs = tables_qs.filter(Q(db_table__icontains=query) | Q(name__icontains=query) | Q(summary__icontains=query) | Q(search_text__icontains=query))
    table_ids = list(tables_qs.order_by('db_table', 'name', 'id').values_list('id', flat=True)[:max(4, min(16, limit // 10))])
    if not table_ids:
        table_ids = list(objects_qs.filter(object_type='table').order_by('db_table', 'name', 'id').values_list('id', flat=True)[:max(4, min(16, limit // 10))])
    related_ids = set(table_ids)
    database_ids = list(objects_qs.filter(object_type='database').order_by('name', 'id').values_list('id', flat=True)[:4])
    related_ids.update(database_ids)
    table_names = get_table_names_for_ids(space, table_ids)
    field_ids = list(
        objects_qs
        .filter(object_type='field', db_table__in=table_names)
        .order_by('db_table', 'name', 'id')
        .values_list('id', flat=True)[:max(0, limit - len(related_ids))]
    )
    related_ids.update(field_ids)
    objects_by_id = {obj.id: obj for obj in objects_qs.filter(id__in=related_ids)}
    return order_er_objects(objects_by_id, limit=limit)


def select_er_neighborhood(space, objects_qs, *, center_table='', limit=180, include_fields=True, field_limit_per_table=12):
    table_ids = list(
        objects_qs
        .filter(object_type='table')
        .filter(Q(db_table__icontains=center_table) | Q(name__icontains=center_table))
        .values_list('id', flat=True)[:24]
    )
    if not table_ids:
        return []
    related_ids = set(table_ids)
    database_ids = list(objects_qs.filter(object_type='database').order_by('name', 'id').values_list('id', flat=True)[:4])
    related_ids.update(database_ids)
    for relation in (
        KnowledgeRelation.objects
        .select_related('source', 'target')
        .filter(space=space)
        .filter(Q(source_id__in=table_ids) | Q(target_id__in=table_ids))
        .filter(relation_type__in=['contains', 'related_to'])
        .order_by('-weight', 'id')[:limit * 2]
    ):
        if relation.source.object_type != 'field':
            related_ids.add(relation.source_id)
        if relation.target.object_type != 'field':
            related_ids.add(relation.target_id)
        if len(related_ids) >= limit:
            break
    if include_fields and len(related_ids) < limit:
        table_names = get_table_names_for_ids(space, related_ids)
        field_ids = []
        for table_name in table_names:
            field_ids.extend(
                objects_qs
                .filter(object_type='field', db_table=table_name)
                .order_by('db_table', 'name', 'id')
                .values_list('id', flat=True)[:max(1, field_limit_per_table)]
            )
            if len(related_ids) + len(field_ids) >= limit:
                break
        related_ids.update(field_ids[:max(0, limit - len(related_ids))])
    objects_by_id = {obj.id: obj for obj in objects_qs.filter(id__in=related_ids)}
    return order_er_objects(objects_by_id, limit=limit)


def order_er_objects(objects_by_id, *, limit=180):
    ordered_ids = list(objects_by_id.keys())
    ordered_ids.sort(key=lambda obj_id: (
        {'database': 1, 'table': 2, 'field': 3}.get(objects_by_id[obj_id].object_type, 9),
        objects_by_id[obj_id].db_table or objects_by_id[obj_id].name or '',
        objects_by_id[obj_id].field_name or objects_by_id[obj_id].name or '',
        obj_id,
    ))
    return [objects_by_id[obj_id] for obj_id in ordered_ids[:limit]]


def select_code_neighborhood(space, objects_qs, *, limit=180):
    anchor_ids = list(
        objects_qs
        .filter(object_type__in=['repository', 'file'])
        .order_by('object_type', 'name', 'id')
        .values_list('id', flat=True)[:max(20, limit // 2)]
    )
    related_ids = set(anchor_ids)
    for relation in (
        KnowledgeRelation.objects
        .filter(space=space)
        .filter(Q(source_id__in=anchor_ids) | Q(target_id__in=anchor_ids))
        .filter(relation_type__in=['contains', 'calls', 'uses', 'related_to'])
        .order_by('-weight', 'id')[:limit * 3]
    ):
        related_ids.add(relation.source_id)
        related_ids.add(relation.target_id)
        if len(related_ids) >= limit:
            break
    objects_by_id = {
        obj.id: obj
        for obj in objects_qs.filter(id__in=related_ids)
    }
    ordered_ids = [obj_id for obj_id in related_ids if obj_id in objects_by_id]
    ordered_ids.sort(key=lambda obj_id: (
        {'repository': 1, 'file': 2, 'class': 3, 'method': 4, 'function': 5, 'api': 6, 'component': 7, 'route': 8}.get(objects_by_id[obj_id].object_type, 9),
        objects_by_id[obj_id].source_ref or objects_by_id[obj_id].name or '',
        obj_id,
    ))
    return [objects_by_id[obj_id] for obj_id in ordered_ids[:limit]]


def select_page_function_neighborhood(space, objects_qs, *, limit=180):
    anchor_ids = list(
        objects_qs
        .filter(object_type__in=['module', 'menu', 'tab', 'page'])
        .order_by('object_type', 'name', 'id')
        .values_list('id', flat=True)[:max(30, limit // 2)]
    )
    return select_relation_neighborhood(
        space,
        objects_qs,
        anchor_ids=anchor_ids,
        relation_types={'contains', 'implements', 'uses', 'related_to'},
        limit=limit,
        priority={'module': 1, 'menu': 2, 'tab': 3, 'page': 4, 'function': 5, 'operation': 6, 'component': 7, 'route': 8},
    )


def select_page_api_table_neighborhood(space, objects_qs, *, limit=180):
    anchor_ids = list(
        objects_qs
        .filter(object_type__in=['module', 'menu', 'tab', 'page'])
        .order_by('object_type', 'name', 'id')
        .values_list('id', flat=True)[:max(30, limit // 3)]
    )
    api_ids = list(
        KnowledgeRelation.objects
        .filter(space=space, source_id__in=anchor_ids, relation_type='calls', target__object_type='api')
        .order_by('-weight', 'id')
        .values_list('target_id', flat=True)[:max(30, limit // 3)]
    )
    related_ids = set(anchor_ids)
    related_ids.update(api_ids)
    expansion_anchor_ids = list(related_ids)
    for relation in (
        KnowledgeRelation.objects
        .filter(space=space)
        .filter(Q(source_id__in=expansion_anchor_ids) | Q(target_id__in=expansion_anchor_ids))
        .filter(relation_type__in={'contains', 'implements', 'calls', 'reads', 'writes', 'uses', 'references', 'related_to'})
        .order_by('-weight', 'id')[:limit * 5]
    ):
        related_ids.add(relation.source_id)
        related_ids.add(relation.target_id)
        if len(related_ids) >= limit:
            break
    objects_by_id = {
        obj.id: obj
        for obj in objects_qs.filter(id__in=related_ids)
    }
    priority = {
        'module': 1,
        'menu': 2,
        'tab': 3,
        'page': 4,
        'component': 5,
        'api': 6,
        'file': 7,
        'table': 8,
        'field': 9,
        'function': 10,
        'operation': 11,
    }
    ordered_ids = [obj_id for obj_id in related_ids if obj_id in objects_by_id]
    ordered_ids.sort(key=lambda obj_id: (
        priority.get(objects_by_id[obj_id].object_type, 50),
        objects_by_id[obj_id].page_path or objects_by_id[obj_id].api_path or objects_by_id[obj_id].db_table or objects_by_id[obj_id].source_ref or objects_by_id[obj_id].name or '',
        obj_id,
    ))
    return [objects_by_id[obj_id] for obj_id in ordered_ids[:limit]]


def select_api_neighborhood(space, objects_qs, *, limit=180):
    anchor_ids = list(
        objects_qs
        .filter(object_type='api')
        .order_by('api_path', 'name', 'id')
        .values_list('id', flat=True)[:max(40, limit // 2)]
    )
    return select_relation_neighborhood(
        space,
        objects_qs,
        anchor_ids=anchor_ids,
        relation_types={'calls', 'reads', 'writes', 'uses', 'references', 'implements', 'related_to'},
        limit=limit,
        priority={'tab': 1, 'page': 2, 'component': 3, 'api': 4, 'file': 5, 'class': 6, 'method': 7, 'function': 8, 'table': 9, 'field': 10},
    )


def select_relation_neighborhood(space, objects_qs, *, anchor_ids, relation_types, limit=180, priority=None):
    related_ids = set(anchor_ids)
    if not related_ids:
        return []
    for relation in (
        KnowledgeRelation.objects
        .filter(space=space)
        .filter(Q(source_id__in=anchor_ids) | Q(target_id__in=anchor_ids))
        .filter(relation_type__in=relation_types)
        .order_by('-weight', 'id')[:limit * 4]
    ):
        related_ids.add(relation.source_id)
        related_ids.add(relation.target_id)
        if len(related_ids) >= limit:
            break
    objects_by_id = {
        obj.id: obj
        for obj in objects_qs.filter(id__in=related_ids)
    }
    priority = priority or {}
    ordered_ids = [obj_id for obj_id in related_ids if obj_id in objects_by_id]
    ordered_ids.sort(key=lambda obj_id: (
        priority.get(objects_by_id[obj_id].object_type, 50),
        objects_by_id[obj_id].page_path or objects_by_id[obj_id].api_path or objects_by_id[obj_id].source_ref or objects_by_id[obj_id].db_table or objects_by_id[obj_id].name or '',
        obj_id,
    ))
    return [objects_by_id[obj_id] for obj_id in ordered_ids[:limit]]


def select_graph_objects(objects_qs, *, query='', limit=180):
    query = str(query or '').strip()
    if query:
        tokens = tokenize_query(query)
        matched_ids = []
        for obj in objects_qs.order_by('object_type', 'name', 'id')[:5000]:
            text = '\n'.join([
                obj.name or '',
                obj.summary or '',
                obj.search_text or '',
                obj.page_path or '',
                obj.api_path or '',
                obj.db_table or '',
                obj.field_name or '',
            ]).lower()
            if any(token.lower() in text for token in tokens):
                matched_ids.append(obj.id)
            if len(matched_ids) >= limit:
                break
        neighbor_ids = set(matched_ids)
        for relation in KnowledgeRelation.objects.filter(Q(source_id__in=matched_ids) | Q(target_id__in=matched_ids))[:limit * 4]:
            neighbor_ids.add(relation.source_id)
            neighbor_ids.add(relation.target_id)
        return list(objects_qs.filter(id__in=list(neighbor_ids)).order_by('object_type', 'name', 'id')[:limit])
    priority = {
        'module': 1,
        'menu': 2,
        'tab': 3,
        'page': 4,
        'function': 5,
        'operation': 6,
        'component': 7,
        'api': 8,
        'table': 9,
        'file': 10,
        'class': 11,
        'method': 12,
        'field': 13,
    }
    objects = list(objects_qs.order_by('object_type', 'name', 'id')[:5000])
    objects.sort(key=lambda obj: (priority.get(obj.object_type, 50), obj.name or '', obj.id))
    return objects[:limit]


def build_ghost_code_payload(space, *, page=1, page_size=20):
    findings = []
    page = max(1, safe_int(page, 1))
    page_size = normalize_page_size(page_size, default=20)
    objects = list(
        KnowledgeObject.objects
        .filter(space=space, object_type__in=['api', 'component', 'table', 'field', 'file'])
        .order_by('object_type', 'name', 'id')[:5000]
    )
    by_id = {obj.id: obj for obj in objects}
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for relation in (
        KnowledgeRelation.objects
        .filter(space=space)
        .filter(Q(source_id__in=by_id.keys()) | Q(target_id__in=by_id.keys()))
        .select_related('source', 'target')[:20000]
    ):
        incoming[relation.target_id].append(relation)
        outgoing[relation.source_id].append(relation)

    for obj in objects:
        if obj.object_type == 'api':
            callers = [rel for rel in incoming[obj.id] if rel.relation_type == 'calls' and by_id.get(rel.source_id, obj).object_type not in {'api', 'route'}]
            if not callers:
                findings.append(build_finding('orphan_api', obj, 'high', '未发现页面、组件或功能节点调用该接口。'))
        elif obj.object_type == 'component':
            renderers = [rel for rel in incoming[obj.id] if rel.relation_type in {'implements', 'uses'}]
            if not renderers:
                findings.append(build_finding('orphan_component', obj, 'medium', '未发现页签或页面引用该组件。'))
        elif obj.object_type == 'table':
            business_refs = [
                rel for rel in incoming[obj.id]
                if rel.relation_type in {'reads', 'writes'} and by_id.get(rel.source_id, obj).object_type not in {'database'}
            ]
            if obj.source_type == 'database_schema' and not business_refs:
                findings.append(build_finding('schema_only_table', obj, 'medium', '表来自数据库Schema，但未发现页面、接口或代码对象读写。'))
        elif obj.object_type == 'field':
            business_refs = [
                rel for rel in incoming[obj.id]
                if rel.relation_type in {'reads', 'writes', 'uses'} and by_id.get(rel.source_id, obj).object_type not in {'table'}
            ]
            if obj.source_type == 'database_schema' and not business_refs:
                findings.append(build_finding('schema_only_field', obj, 'low', '字段来自数据库Schema，但未发现代码或接口级读写证据。'))
        elif obj.object_type == 'file':
            refs = [rel for rel in incoming[obj.id] + outgoing[obj.id] if rel.relation_type not in {'contains'}]
            if not refs:
                findings.append(build_finding('unlinked_file', obj, 'low', '文件已被扫描到，但尚未识别到导入、调用或接口关系。'))

    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda item: (severity_order.get(item['severity'], 9), item['type'], item['object']['label']))
    total = len(findings)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        'summary': dict(Counter(item['type'] for item in findings)),
        'findings': findings[start:end],
        'total': total,
        'page': page,
        'page_size': page_size,
        'truncated': end < total,
    }


def build_table_field_payload(space, *, query='', page=1, page_size=20):
    query = str(query or '').strip().lower()
    page = max(1, safe_int(page, 1))
    page_size = normalize_page_size(page_size, default=20)
    start = (page - 1) * page_size
    end = start + page_size
    tables_qs = KnowledgeObject.objects.filter(space=space, object_type='table').order_by('db_table', 'name', 'id')
    fields_qs = KnowledgeObject.objects.filter(space=space, object_type='field').order_by('db_table', 'field_name', 'name', 'id')
    if query:
        tables_qs = tables_qs.filter(Q(name__icontains=query) | Q(db_table__icontains=query) | Q(summary__icontains=query) | Q(search_text__icontains=query))
        fields_qs = fields_qs.filter(Q(name__icontains=query) | Q(db_table__icontains=query) | Q(field_name__icontains=query) | Q(summary__icontains=query) | Q(search_text__icontains=query))
    fields = [serialize_field(obj) for obj in fields_qs[start:end]]
    visible_table_names = {item['db_table'] for item in fields if item.get('db_table')}
    table_slice = list(tables_qs.filter(db_table__in=visible_table_names)) if visible_table_names else []
    if len(table_slice) < page_size:
        seen_table_ids = {obj.id for obj in table_slice}
        for table in tables_qs[start:end]:
            if table.id not in seen_table_ids:
                table_slice.append(table)
                seen_table_ids.add(table.id)
    tables = [serialize_table(obj) for obj in table_slice[:page_size]]
    field_counts = Counter(item['db_table'] for item in fields if item.get('db_table'))
    for table in tables:
        table['visible_field_count'] = field_counts.get(table['db_table'], 0)
    total_fields = fields_qs.count()
    return {
        'tables': tables,
        'fields': fields,
        'total_tables': tables_qs.count(),
        'total_fields': total_fields,
        'total': total_fields,
        'page': page,
        'page_size': page_size,
        'query': query,
    }


def build_finding(finding_type, obj, severity, reason):
    return {
        'type': finding_type,
        'type_label': GHOST_TYPE_LABELS.get(finding_type, finding_type),
        'severity': severity,
        'reason': reason,
        'object': serialize_asset_node(obj),
        'suggestion': build_finding_suggestion(finding_type),
    }


def build_finding_suggestion(finding_type):
    return {
        'orphan_api': '确认是否有前端调用、外部系统调用或定时任务调用；确认无调用后再下线。',
        'orphan_component': '确认是否为动态组件、路由懒加载或历史遗留页面；确认无入口后再删除。',
        'schema_only_table': '确认是否由外部系统、报表、存储过程或历史归档使用；确认无使用后再治理。',
        'schema_only_field': '字段级误报可能较高，建议结合 SQL/ORM 扫描和线上查询日志复核。',
        'unlinked_file': '先通过全文搜索和构建入口复核，确认不是脚本、配置或动态导入文件。',
    }.get(finding_type, '请结合代码搜索、运行入口和业务负责人复核。')


def serialize_space(space):
    if not space:
        return None
    return {
        'id': space.id,
        'key': space.key,
        'name': space.name,
        'space_type': space.space_type,
        'project': space.project_id,
        'project_name': space.project.name if space.project_id else '',
        'build_status': space.build_status,
        'build_status_message': space.build_status_message,
        'last_indexed_at': space.last_indexed_at,
        'metadata': space.metadata or {},
        'is_active': space.is_active,
    }


def serialize_config(config):
    return {
        'id': config.id,
        'name': config.name,
        'project': config.project_id,
        'project_name': config.project.name if config.project_id else '',
        'space': config.space_id,
        'provider': config.provider,
        'repository_mode': config.repository_mode,
        'repository_location': config.repository_location,
        'default_branch': config.default_branch,
        'database_engine': config.database_engine,
        'database_name': config.database_name,
        'database_schema': config.database_schema,
        'ready': is_repository_config_ready(config),
        'last_indexed_at': config.last_indexed_at,
        'is_active': config.is_active,
    }


def serialize_run(run):
    if not run:
        return None
    return {
        'id': run.id,
        'status': run.status,
        'trigger': run.trigger,
        'index_ref': run.index_ref,
        'object_count': run.object_count,
        'relation_count': run.relation_count,
        'changed_object_count': run.changed_object_count,
        'started_at': run.started_at,
        'finished_at': run.finished_at,
        'error_message': run.error_message,
        'repository_config': run.repository_config_id,
        'repository_config_name': run.repository_config.name if run.repository_config_id else '',
    }


def serialize_asset_node(obj):
    payload = serialize_node(obj)
    payload['label'] = payload.get('label') or obj.name
    payload['name'] = obj.name
    payload['node_type_label'] = get_object_type_label(obj.object_type)
    return payload


def serialize_table(obj):
    return {
        'id': obj.id,
        'name': obj.name,
        'db_table': obj.db_table or obj.name,
        'summary': obj.summary,
        'source_type': obj.source_type,
        'source_ref': obj.source_ref,
        'metadata': obj.metadata or {},
    }


def serialize_field(obj):
    return {
        'id': obj.id,
        'name': obj.name,
        'db_table': obj.db_table,
        'field_name': obj.field_name or obj.name,
        'summary': obj.summary,
        'source_type': obj.source_type,
        'source_ref': obj.source_ref,
        'metadata': obj.metadata or {},
    }


def build_graph_categories(objects):
    return [
        {'name': object_type, 'label': get_object_type_label(object_type)}
        for object_type in sorted({obj.object_type for obj in objects})
    ]


def get_object_type_label(object_type):
    return {
        'platform': '平台',
        'project': '项目',
        'module': '模块',
        'menu': '菜单',
        'page': '页面',
        'tab': '页签',
        'section': '板块',
        'function': '功能',
        'operation': '操作项',
        'field': '字段',
        'api': '接口',
        'database': '数据库',
        'table': '表',
        'component': '组件',
        'route': '路由',
        'repository': '仓库',
        'document': '文档',
        'business_data': '业务数据',
        'file': '文件',
        'class': '类',
        'method': '方法',
    }.get(object_type, object_type or '对象')


def get_table_names_for_ids(space, table_ids):
    return list(
        KnowledgeObject.objects
        .filter(space=space, id__in=table_ids, object_type='table')
        .exclude(db_table='')
        .values_list('db_table', flat=True)
    )


def safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def normalize_page_size(value, default=20):
    page_size = safe_int(value, default)
    return max(10, min(page_size, 100))


def normalize_er_view(value):
    normalized = str(value or '').strip().lower()
    if normalized in {'macro', 'overview', 'all', '宏观'}:
        return 'macro'
    if normalized in {'meso', 'middle', 'neighborhood', 'local', '中观'}:
        return 'meso'
    if normalized in {'micro', 'detail', 'field', 'fields', '微观'}:
        return 'micro'
    return 'macro'


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on', '启用'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off', '停用'}:
        return False
    return default


def normalize_index_payload(index_payload):
    if not index_payload:
        return None
    if isinstance(index_payload, dict) and index_payload.get('run'):
        run = index_payload['run']
        return {'queued': False, 'run': serialize_run(run)}
    if isinstance(index_payload, dict):
        return index_payload
    return {'detail': str(index_payload)}


def build_project_knowledge_status_message(space, configs, ready_configs):
    if not space:
        return '当前项目尚未启用项目知识库。'
    if not configs:
        return '项目知识库已创建，请先配置代码仓库和数据库信息。'
    if not ready_configs:
        return '已配置知识库数据源，但仓库或数据库配置尚未就绪。'
    if space.build_status == 'indexed':
        return '项目知识库已建模，可用于资产图谱、代码排查和知识库助手问答。'
    return space.build_status_message or '项目知识库已就绪，可执行建模。'


def infer_language(path):
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
        '.cpp': 'C++',
        '.cc': 'C++',
        '.cxx': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.rs': 'Rust',
        '.sql': 'SQL',
    }.get(suffix, suffix.lstrip('.').upper() if suffix else 'Text')


def extract_code_symbols(relative_path, text, max_symbols=40):
    language = infer_language(relative_path)
    symbols = []
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
            ('function', r'\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'),
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
    for symbol_type, pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            name = match.group(1)
            if name.startswith('_') and symbol_type == 'function':
                continue
            symbols.append({'type': symbol_type, 'name': name})
            if len(symbols) >= max_symbols:
                return symbols
    return symbols
