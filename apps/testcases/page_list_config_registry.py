from copy import deepcopy


MODULE_KEY = 'manual-testcases'

FILTER_CONTROL_TYPES = (
    'text',
    'single_select',
    'multi_select',
    'number',
    'number_range',
    'date',
    'date_range',
    'boolean',
)

DATA_TYPE_DEFAULT_CONTROLS = {
    'text': ['text', 'single_select', 'multi_select'],
    'number': ['number', 'number_range', 'single_select', 'multi_select'],
    'date': ['date', 'date_range'],
    'datetime': ['date', 'date_range'],
    'boolean': ['boolean', 'single_select'],
    'enum': ['single_select', 'multi_select'],
}


def field(
    field_key,
    label,
    *,
    data_type='text',
    filterable=True,
    list_column=True,
    default_filter=False,
    visible=True,
    locked=False,
    controls=None,
    option_source='',
    options=None,
):
    supported_controls = controls or DATA_TYPE_DEFAULT_CONTROLS.get(data_type, ['text'])
    return {
        'field_key': field_key,
        'label': label,
        'data_type': data_type,
        'filterable': bool(filterable),
        'list_column': bool(list_column),
        'default_filter': bool(default_filter),
        'default_visible': bool(visible),
        'locked': bool(locked),
        'supported_filter_controls': list(supported_controls),
        'option_source': option_source,
        'options': list(options or []),
    }


def action_field():
    return field('label:操作', '操作', filterable=False, locked=True)


def selection_field():
    return field('type:selection', '选择', filterable=False, locked=True)


STATUS_OPTIONS = [
    {'label': '未执行', 'value': 'not_run'},
    {'label': '通过', 'value': 'pass'},
    {'label': '失败', 'value': 'fail'},
    {'label': '阻塞', 'value': 'block'},
    {'label': '本版本不测', 'value': 'not_test'},
]

PRIORITY_OPTIONS = [
    {'label': 'P0', 'value': '0'},
    {'label': 'P1', 'value': '1'},
    {'label': 'P2', 'value': '2'},
    {'label': 'P3', 'value': '3'},
]


JIRA_BUG_FIELDS = [
    field('prop:version', '版本号', default_filter=True),
    field('prop:issuekey', '缺陷编号', default_filter=True),
    field('prop:summary', '缺陷标题', default_filter=True),
    field('prop:customfield_10762', '客户或项目名称'),
    field('prop:customfield_10754', 'BUG处理反馈'),
    field('prop:customfield_11101', 'BUG定性分类'),
    field('prop:customfield_11102', 'BUG产生根因'),
    field('prop:customfield_11103', 'BUG直接责任岗位'),
    field('prop:components', '模块', default_filter=True),
    field('prop:status', '状态', data_type='enum', default_filter=True),
    field('prop:creator', '创建人'),
    field('prop:customfield_10222', '测试人员'),
    field('prop:customfield_11100', '版本内研发优先级别'),
    field('prop:customfield_10743', '前端'),
    field('prop:customfield_10741', '后端'),
    field('prop:customfield_10746', '测试进度'),
    field('prop:customfield_10761', '测试预估工时', data_type='number'),
    field('prop:customfield_10738', 'PM进度'),
    field('prop:customfield_10100', '必须发版', data_type='boolean'),
    field('prop:customfield_10737', 'PM'),
    field('prop:customfield_11000', '组别'),
    field('prop:customfield_10523', '前端开始日期', data_type='date'),
    field('prop:customfield_11017', '前端结束日期', data_type='date'),
    field('prop:customfield_10522', '后端开始日期', data_type='date'),
    field('prop:customfield_11019', '后端结束日期', data_type='date'),
    field('prop:created', '创建日期', data_type='date'),
    field('prop:customfield_10014', '预计提测日期', data_type='date'),
    field('prop:customfield_11018', '提测时间', data_type='date'),
    field('prop:customfield_10765', '整体进度|延期原因'),
    field('prop:customfield_10015', '用例预估完成时间', data_type='date'),
    field('prop:customfield_11020', '测试进展'),
    field('prop:customfield_10749', '前端预估工时', data_type='number'),
    field('prop:customfield_10748', '后端预估工时', data_type='number'),
    field('prop:customfield_10731', 'BUG责任人'),
    field('prop:customfield_10019', 'BUG重新打开次数', data_type='number'),
    field('prop:synced_at', '同步时间', data_type='datetime'),
]

JIRA_REQUIREMENT_FIELDS = [
    field('prop:version', '版本号', default_filter=True),
    field('prop:issuekey', '需求编号', default_filter=True),
    field('prop:summary', '需求标题', default_filter=True),
    field('prop:customfield_10762', '客户或项目名称'),
    field('prop:status', '状态', data_type='enum', default_filter=True),
    field('prop:creator', '创建人'),
    field('prop:customfield_10222', '测试人员'),
    field('prop:customfield_11100', '版本内研发优先级别'),
    field('prop:customfield_10761', '测试预估工时', data_type='number'),
    field('prop:customfield_10738', 'PM进度'),
    field('prop:customfield_10100', '必须发版', data_type='boolean'),
    field('prop:customfield_10737', 'PM'),
    field('prop:customfield_11000', '组别'),
    field('prop:customfield_10743', '前端'),
    field('prop:customfield_10523', '前端开始日期', data_type='date'),
    field('prop:customfield_11017', '前端结束日期', data_type='date'),
    field('prop:customfield_10741', '后端'),
    field('prop:customfield_10522', '后端开始日期', data_type='date'),
    field('prop:customfield_11019', '后端结束日期', data_type='date'),
    field('prop:created', '创建日期', data_type='date'),
    field('prop:customfield_10014', '预计提测日期', data_type='date'),
    field('prop:customfield_11018', '提测时间', data_type='date'),
    field('prop:customfield_10765', '整体进度|延期原因'),
    field('prop:customfield_10015', '用例预估完成时间', data_type='date'),
    field('prop:customfield_11020', '测试进展'),
    field('prop:customfield_10746', '测试进度'),
    field('prop:components', '模块', default_filter=True),
    field('prop:customfield_10602', '前端是否完成', data_type='boolean'),
    field('prop:customfield_10749', '前端预估工时', data_type='number'),
    field('prop:customfield_10603', '后端是否完成', data_type='boolean'),
    field('prop:customfield_10748', '后端预估工时', data_type='number'),
    field('prop:synced_at', '同步时间', data_type='datetime'),
]

DEFECT_FIELDS = [
    field('prop:code', '缺陷编号', default_filter=True),
    field('prop:title', '标题', default_filter=True),
    field('prop:priority', '优先级', data_type='enum', default_filter=True),
    field('prop:problem_reason', '问题原因'),
    field('prop:root_cause', '问题根因'),
    field('label:需求编号', '需求编号', default_filter=True),
    field('prop:frontend_developer', '前端开发'),
    field('prop:backend_developer', '后端开发'),
    field('label:模块路径', '模块路径', default_filter=True),
    field('label:关联测试用例', '关联测试用例'),
    field('label:关联测试点', '关联测试点'),
    field('label:项目', '项目'),
    field('label:版本', '版本'),
    field('label:严重程度', '严重程度', data_type='enum'),
    field('label:状态', '状态', data_type='enum', default_filter=True),
    field('label:处理人', '处理人'),
    field('label:创建人', '创建人'),
    field('prop:attachments_count', '附件数', data_type='number'),
    field('label:更新时间', '更新时间', data_type='datetime'),
]


PAGE_DEFINITIONS = [
    {
        'page_key': 'mindmaps',
        'page_name': '测试脑图',
        'storage_keys': ['manual-testcases.mindmaps'],
        'fields': [
            selection_field(),
            field('prop:id', 'ID', data_type='number', default_filter=True),
            field('prop:requirement_key', '需求编号', default_filter=True),
            field('prop:requirement_title', '需求标题', default_filter=True),
            field('prop:module', '模块', default_filter=True),
            field('prop:name', '脑图名称', default_filter=True),
            field('prop:case_count', '用例数', data_type='number'),
            field('prop:testpoint_count', '测试点数', data_type='number'),
            field('prop:review_testpoint_count', '评审测试点数', data_type='number'),
            field('prop:dev_self_test_count', '自测点数', data_type='number'),
            field('prop:responsibility_group', '组别', default_filter=True),
            field('prop:frontend_name', '前端'),
            field('prop:backend_name', '后端'),
            field('prop:author', '创建人'),
            field('prop:executor', '执行人'),
            field('prop:version', '版本号'),
            field('prop:created_at', '创建时间', data_type='datetime'),
            field('prop:updated_at', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'testcases',
        'page_name': '测试用例',
        'storage_keys': ['manual-testcases.testcases'],
        'fields': [
            field('prop:node_text', '测试用例', default_filter=True),
            field('prop:requirement_key', '需求编号', default_filter=True),
            field('prop:requirement_title', '需求标题', default_filter=True),
            field('prop:responsibility_group', '组别', default_filter=True),
            field('prop:module_path', '模块路径', default_filter=True),
            field('label:优先级', '优先级', data_type='enum', default_filter=True, options=PRIORITY_OPTIONS),
            field('label:状态', '状态', data_type='enum', default_filter=True, options=STATUS_OPTIONS),
            field('label:自测状态', '自测状态', data_type='enum'),
            field('label:标签', '标签'),
            field('prop:updated_at', '脑图更新时间', data_type='datetime'),
            field('prop:mindmap_name', '所属脑图'),
            action_field(),
        ],
    },
    {
        'page_key': 'testpoints',
        'page_name': '测试点',
        'storage_keys': ['manual-testcases.testpoints'],
        'fields': [
            field('prop:id', 'ID', default_filter=True),
            field('prop:node_text', '测试点', default_filter=True),
            field('prop:requirement_key', '需求编号', default_filter=True),
            field('prop:requirement_title', '需求标题', default_filter=True),
            field('prop:creator', '创建人'),
            field('prop:responsibility_group', '组别', default_filter=True),
            field('prop:module_path', '模块路径', default_filter=True),
            field('label:优先级', '优先级', data_type='enum', options=PRIORITY_OPTIONS),
            field('label:状态', '状态', data_type='enum', default_filter=True, options=STATUS_OPTIONS),
            field('label:自测状态', '自测状态', data_type='enum'),
            field('label:标签', '标签'),
            field('prop:updated_at', '脑图更新时间', data_type='datetime'),
            field('prop:mindmap_name', '所属脑图'),
            action_field(),
        ],
    },
    {
        'page_key': 'devselftest',
        'page_name': '自测测试点',
        'storage_keys': ['manual-testcases.devselftest'],
        'fields': [
            selection_field(),
            field('prop:testpoint', '测试点', default_filter=True),
            field('prop:requirement_key', '需求编号', default_filter=True),
            field('prop:requirement_title', '需求标题', default_filter=True),
            field('label:优先级', '优先级', data_type='enum', options=PRIORITY_OPTIONS),
            field('label:状态', '状态', data_type='enum', default_filter=True, options=STATUS_OPTIONS),
            field('label:审核状态', '审核状态', data_type='enum'),
            field('prop:responsibility_group', '组别', default_filter=True),
            field('label:前端', '前端'),
            field('label:后端', '后端'),
            field('prop:updated_at', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'version-requirements',
        'page_name': '版本需求',
        'storage_keys': ['manual-testcases.version-requirements'],
        'fields': [
            selection_field(),
            field('prop:version', '版本号', default_filter=True),
            field('prop:issue_key', '需求编号', default_filter=True),
            field('prop:summary', '需求标题', default_filter=True),
            field('prop:issue_type', '需求类型'),
            field('prop:module', '所属模块', default_filter=True),
            field('prop:customer_name', '客户'),
            field('prop:priority', '优先级', data_type='enum'),
            field('prop:status', '状态', data_type='enum', default_filter=True),
            field('prop:creator', '创建人'),
            field('prop:handler', '处理人'),
            field('prop:tester', '测试人员'),
            field('prop:group_name', '组别'),
            field('label:更新时间', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'requirement-records',
        'page_name': 'JIRA需求数据',
        'storage_keys': ['manual-testcases.requirement-records'],
        'fields': [selection_field(), *JIRA_REQUIREMENT_FIELDS, action_field()],
    },
    {
        'page_key': 'bug-records',
        'page_name': '线上缺陷',
        'storage_keys': ['manual-testcases.bug-records'],
        'fields': [selection_field(), *JIRA_BUG_FIELDS, action_field()],
    },
    {
        'page_key': 'version-defects',
        'page_name': '版本缺陷',
        'storage_keys': ['manual-testcases.defects', 'manual-testcases.version-defects'],
        'fields': [*DEFECT_FIELDS, action_field()],
    },
    {
        'page_key': 'technical-solution-designs',
        'page_name': '技术方案设计',
        'storage_keys': ['manual-testcases.technical-solution-designs'],
        'fields': [*DEFECT_FIELDS, action_field()],
    },
    {
        'page_key': 'project-environments',
        'page_name': '项目环境',
        'storage_keys': ['manual-testcases.project-environments'],
        'fields': [
            field('prop:project_name', '项目名称', default_filter=True),
            field('prop:name', '环境名称', default_filter=True),
            field('prop:base_url', 'URL地址', default_filter=True),
            field('prop:account', '账号', default_filter=True),
            field('label:密码', '密码', data_type='boolean'),
            field('prop:description', '说明'),
            field('label:更新时间', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'quality-report-list',
        'page_name': '报告列表',
        'storage_keys': ['manual-testcases.quality-report-list'],
        'fields': [
            field('prop:version', '版本号', default_filter=True),
            field('label:状态', '状态', data_type='enum', default_filter=True),
            field('label:缺陷数', '缺陷数', data_type='number'),
            field('label:已分类', '已分类', data_type='number'),
            field('label:缺陷文件', '缺陷文件', default_filter=True),
            field('label:需求清单', '需求清单'),
            field('label:测试用例统计', '测试用例统计'),
            field('label:创建时间', '创建时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'configs',
        'page_name': 'JIRA接口',
        'storage_keys': ['manual-testcases.jira-configs'],
        'fields': [
            field('label:接口类型', '接口类型', data_type='enum', default_filter=True),
            field('prop:version', '版本号', default_filter=True),
            field('prop:name', '配置名称', default_filter=True),
            field('prop:request_method', '方法'),
            field('prop:request_url', '接口地址'),
            field('label:启用登录', '启用登录', data_type='boolean'),
            field('label:启用状态', '启用状态', data_type='boolean'),
            field('label:最近执行', '最近执行', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'projects',
        'page_name': '项目',
        'storage_keys': ['manual-testcases.projects'],
        'fields': [
            field('prop:name', '项目名称', default_filter=True),
            field('prop:description', '描述'),
            field('prop:status', '状态', data_type='enum', default_filter=True),
            field('label:默认', '默认项目', data_type='boolean'),
            field('label:更新时间', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'versions',
        'page_name': '版本',
        'storage_keys': ['manual-testcases.versions'],
        'fields': [
            field('prop:name', '版本号', default_filter=True),
            field('prop:project_name', '项目名称', default_filter=True),
            field('prop:status', '状态', data_type='enum', default_filter=True),
            field('label:默认', '默认版本', data_type='boolean'),
            field('label:更新时间', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'members',
        'page_name': '成员',
        'storage_keys': ['manual-testcases.members'],
        'fields': [
            field('prop:username', '账号', default_filter=True),
            field('prop:name', '姓名', default_filter=True),
            field('prop:email', '邮箱'),
            field('prop:department', '部门', default_filter=True),
            field('prop:position', '职位'),
            field('prop:status', '状态', data_type='enum'),
            action_field(),
        ],
    },
    {
        'page_key': 'groups',
        'page_name': '组别',
        'storage_keys': ['manual-testcases.groups'],
        'fields': [
            field('prop:id', 'ID', data_type='number'),
            field('prop:name', '组别名称', default_filter=True),
            field('prop:member_count', '成员数', data_type='number'),
            field('prop:members', '成员'),
            action_field(),
        ],
    },
    {
        'page_key': 'roles',
        'page_name': '角色',
        'storage_keys': ['manual-testcases.roles'],
        'fields': [
            field('prop:id', 'ID', data_type='number'),
            field('prop:name', '角色名称', default_filter=True),
            field('prop:member_count', '成员数', data_type='number'),
            field('prop:permission_count', '权限数', data_type='number'),
            action_field(),
        ],
    },
    {
        'page_key': 'permissions',
        'page_name': '权限',
        'storage_keys': ['manual-testcases.permissions'],
        'fields': [
            field('prop:name', '权限名称', default_filter=True),
            field('prop:code', '权限编码', default_filter=True),
            field('prop:item_type', '权限类型', data_type='enum'),
            field('prop:route_path', '路由'),
            field('prop:is_active', '是否启用', data_type='boolean'),
            action_field(),
        ],
    },
    {
        'page_key': 'controlled-browser-lab',
        'page_name': '模拟页面组件',
        'storage_keys': ['manual-testcases.controlled-browser-lab'],
        'fields': [
            field('prop:name', '控件', default_filter=True),
            field('prop:type', '类型', data_type='enum'),
            field('prop:status', '状态', data_type='enum'),
            action_field(),
        ],
    },
    {
        'page_key': 'snapshots',
        'page_name': '快照管理',
        'storage_keys': ['manual-testcases.snapshots', 'manual-testcases.snapshot-recordings'],
        'fields': [
            field('prop:name', '快照名称', default_filter=True),
            field('prop:target_url', '目标地址', default_filter=True),
            field('prop:module_path', '页面目录'),
            field('prop:created_by_name', '创建人'),
            field('prop:updated_at', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
    {
        'page_key': 'flows',
        'page_name': '流程管理',
        'storage_keys': ['manual-testcases.visual-flows'],
        'fields': [
            selection_field(),
            field('prop:name', '流程名称', default_filter=True),
            field('prop:source', '来源', data_type='enum'),
            field('prop:status', '状态', data_type='enum'),
            field('label:节点数', '节点数', data_type='number'),
            field('label:快照/步骤', '快照/步骤'),
            field('prop:target_url', '目标地址'),
            field('label:页面目录', '页面目录'),
            field('label:录制会话', '录制会话'),
            field('label:更新时间', '更新时间', data_type='datetime'),
            action_field(),
        ],
    },
]


def _page_sort_key(page):
    return page.get('page_name') or page.get('page_key')


def get_page_definitions():
    return deepcopy(PAGE_DEFINITIONS)


def get_page_definition(page_key):
    normalized_page_key = str(page_key or '').strip()
    for page in PAGE_DEFINITIONS:
        if page['page_key'] == normalized_page_key:
            return deepcopy(page)
    return None


def get_page_definition_by_storage_key(storage_key):
    normalized_storage_key = str(storage_key or '').strip()
    for page in PAGE_DEFINITIONS:
        if normalized_storage_key in page.get('storage_keys', []):
            return deepcopy(page)
    return None


def get_field_map(page_def):
    return {item['field_key']: item for item in page_def.get('fields', [])}


def build_factory_config(page_def):
    filter_conditions = []
    for order, item in enumerate([field for field in page_def.get('fields', []) if field.get('default_filter')], start=1):
        controls = item.get('supported_filter_controls') or ['text']
        filter_conditions.append({
            'id': f"factory-filter-{item['field_key']}",
            'field_key': item['field_key'],
            'label_override': '',
            'filter_type': controls[0],
            'operator': 'contains' if controls[0] == 'text' else 'eq',
            'placeholder': f"请输入{item['label']}",
            'option_source': item.get('option_source') or '',
            'enabled': True,
            'order': order,
        })

    columns = []
    for order, item in enumerate([field for field in page_def.get('fields', []) if field.get('list_column')], start=1):
        columns.append({
            'field_key': item['field_key'],
            'label_override': '',
            'visible': bool(item.get('default_visible', True)),
            'locked': bool(item.get('locked', False)),
            'order': order,
        })

    return {
        'filter_conditions': filter_conditions,
        'columns': columns,
    }


def build_registry_payload():
    pages = sorted(get_page_definitions(), key=_page_sort_key)
    return {
        'module_key': MODULE_KEY,
        'filter_control_types': list(FILTER_CONTROL_TYPES),
        'pages': [
            {
                'module_key': MODULE_KEY,
                'page_key': page['page_key'],
                'page_name': page['page_name'],
                'storage_keys': list(page.get('storage_keys') or []),
                'fields': page.get('fields') or [],
                'factory_config': build_factory_config(page),
            }
            for page in pages
        ],
    }
