import pandas as pd


RESPONSIBILITIES = ['产品侧', '开发侧', '测试侧', '前端侧', '历史', '其他']
DEFECT_JIRA_COLUMNS = ['JIAR任务编码', 'JIRA任务编码']
REQ_JIRA_COLUMNS = ['JIRA需求编号', 'JIRA任务编码', '需求编号']


def _find_column(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _non_empty(df, column):
    return df[column].notna() & (df[column].astype(str).str.strip() != '')


def _to_int_list(values):
    return [int(value) for value in values]


def get_requirement_defect_stats(df):
    jira_col = _find_column(df, DEFECT_JIRA_COLUMNS)
    if not jira_col:
        return {'requirements': [], 'defect_counts': []}

    stats = df[df[jira_col].notna()][jira_col].value_counts()
    return {
        'requirements': stats.index.tolist(),
        'defect_counts': _to_int_list(stats.values.tolist()),
    }


def get_root_cause_responsibility_stats(df):
    if 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'root_causes': [], 'responsibilities': {}}

    valid_df = df[_non_empty(df, 'bug根因登记') & _non_empty(df, '责任方')]
    root_causes = valid_df['bug根因登记'].value_counts().index.tolist()[:15]

    result = {'root_causes': root_causes, 'responsibilities': {}}
    for responsibility in RESPONSIBILITIES:
        counts = []
        for root_cause in root_causes:
            count = len(
                valid_df[
                    (valid_df['bug根因登记'] == root_cause) &
                    (valid_df['责任方'] == responsibility)
                ]
            )
            counts.append(int(count))
        result['responsibilities'][responsibility] = counts
    return result


def get_requirement_root_cause_responsibility_stats(df):
    jira_col = _find_column(df, DEFECT_JIRA_COLUMNS)
    if not jira_col or 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'requirements': [], 'responsibilities': {}}

    valid_df = df[
        df[jira_col].notna() &
        _non_empty(df, 'bug根因登记') &
        _non_empty(df, '责任方')
    ]
    requirements = valid_df[jira_col].value_counts().index.tolist()[:10]

    result = {'requirements': requirements, 'responsibilities': {}}
    for responsibility in RESPONSIBILITIES:
        counts = []
        for requirement in requirements:
            count = len(
                valid_df[
                    (valid_df[jira_col] == requirement) &
                    (valid_df['责任方'] == responsibility)
                ]
            )
            counts.append(int(count))
        result['responsibilities'][responsibility] = counts
    return result


def get_product_root_cause_stats(df):
    if not {'产品', 'bug根因登记', '责任方'}.issubset(df.columns):
        return {'root_causes': [], 'products': {}}

    product_df = df[
        (df['责任方'] == '产品侧') &
        _non_empty(df, 'bug根因登记') &
        df['产品'].notna()
    ]
    if product_df.empty:
        return {'root_causes': [], 'products': {}}

    root_causes = product_df['bug根因登记'].value_counts().index.tolist()
    products = product_df['产品'].value_counts().index.tolist()[:10]

    result = {'root_causes': root_causes, 'products': {}}
    for product in products:
        counts = []
        for root_cause in root_causes:
            count = len(
                product_df[
                    (product_df['bug根因登记'] == root_cause) &
                    (product_df['产品'] == product)
                ]
            )
            counts.append(int(count))
        result['products'][product] = counts
    return result


def get_developer_root_cause_stats(df):
    if 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'root_causes': [], 'developers': {}}

    developer_df = df[
        (df['责任方'] == '开发侧') &
        _non_empty(df, 'bug根因登记')
    ]
    if developer_df.empty:
        return {'root_causes': [], 'developers': {}}

    root_causes = developer_df['bug根因登记'].value_counts().index.tolist()
    result = {'root_causes': root_causes, 'developers': {}}

    frontend_col = _find_column(df, ['前端', '前端开发'])
    if frontend_col:
        frontend_df = developer_df[developer_df[frontend_col].notna()]
        frontends = frontend_df[frontend_col].value_counts().index.tolist()[:10]
        for frontend in frontends:
            counts = []
            for root_cause in root_causes:
                count = len(
                    frontend_df[
                        (frontend_df['bug根因登记'] == root_cause) &
                        (frontend_df[frontend_col] == frontend)
                    ]
                )
                counts.append(int(count))
            result['developers'][f'前端-{frontend}'] = counts

    backend_col = _find_column(df, ['后端', '后端开发'])
    if backend_col:
        backend_df = developer_df[developer_df[backend_col].notna()]
        backends = backend_df[backend_col].value_counts().index.tolist()[:10]
        for backend in backends:
            counts = []
            for root_cause in root_causes:
                count = len(
                    backend_df[
                        (backend_df['bug根因登记'] == root_cause) &
                        (backend_df[backend_col] == backend)
                    ]
                )
                counts.append(int(count))
            result['developers'][f'后端-{backend}'] = counts
    return result


def get_tester_root_cause_stats(df):
    tester_col = _find_column(df, ['提交人', '测试人员'])
    if not tester_col or 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'root_causes': [], 'testers': {}}

    tester_df = df[
        (df['责任方'] == '测试侧') &
        _non_empty(df, 'bug根因登记') &
        df[tester_col].notna()
    ]
    if tester_df.empty:
        return {'root_causes': [], 'testers': {}}

    root_causes = tester_df['bug根因登记'].value_counts().index.tolist()
    testers = tester_df[tester_col].value_counts().index.tolist()[:10]

    result = {'root_causes': root_causes, 'testers': {}}
    for tester in testers:
        counts = []
        for root_cause in root_causes:
            count = len(
                tester_df[
                    (tester_df['bug根因登记'] == root_cause) &
                    (tester_df[tester_col] == tester)
                ]
            )
            counts.append(int(count))
        result['testers'][tester] = counts
    return result


def get_product_manager_root_cause_stats(df, req_df=None):
    if 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'product_managers': [], 'root_causes': {}}

    product_df = df[
        (df['责任方'] == '产品侧') &
        _non_empty(df, 'bug根因登记')
    ].copy()
    if product_df.empty:
        return {'product_managers': [], 'root_causes': {}}

    manager_col = None
    if req_df is not None:
        defect_jira_col = _find_column(df, DEFECT_JIRA_COLUMNS)
        req_jira_col = _find_column(req_df, REQ_JIRA_COLUMNS)
        req_manager_col = _find_column(req_df, ['产品经理', '产品'])
        if defect_jira_col and req_jira_col and req_manager_col:
            manager_mapping = req_df.dropna(subset=[req_jira_col, req_manager_col]).set_index(req_jira_col)[req_manager_col].to_dict()
            product_df['_产品经理'] = product_df[defect_jira_col].map(manager_mapping)
            manager_col = '_产品经理'

    if not manager_col:
        manager_col = _find_column(product_df, ['产品', '产品经理'])
        if not manager_col:
            return {'product_managers': [], 'root_causes': {}}

    product_df = product_df[product_df[manager_col].notna()]
    if product_df.empty:
        return {'product_managers': [], 'root_causes': {}}

    product_managers = product_df[manager_col].value_counts().index.tolist()[:10]
    root_causes = product_df['bug根因登记'].value_counts().index.tolist()[:10]

    result = {'product_managers': product_managers, 'root_causes': {}}
    for root_cause in root_causes:
        counts = []
        for product_manager in product_managers:
            count = len(
                product_df[
                    (product_df['bug根因登记'] == root_cause) &
                    (product_df[manager_col] == product_manager)
                ]
            )
            counts.append(int(count))
        result['root_causes'][root_cause] = counts
    return result


def get_frontend_developer_root_cause_stats(df):
    frontend_col = _find_column(df, ['前端', '前端开发'])
    if not frontend_col or 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'frontend_developers': [], 'root_causes': {}}

    frontend_df = df[
        df['责任方'].isin(['开发侧', '前端侧']) &
        _non_empty(df, 'bug根因登记') &
        df[frontend_col].notna()
    ]
    if frontend_df.empty:
        return {'frontend_developers': [], 'root_causes': {}}

    frontend_developers = frontend_df[frontend_col].value_counts().index.tolist()[:10]
    root_causes = frontend_df['bug根因登记'].value_counts().index.tolist()[:10]

    result = {'frontend_developers': frontend_developers, 'root_causes': {}}
    for root_cause in root_causes:
        counts = []
        for developer in frontend_developers:
            count = len(
                frontend_df[
                    (frontend_df['bug根因登记'] == root_cause) &
                    (frontend_df[frontend_col] == developer)
                ]
            )
            counts.append(int(count))
        result['root_causes'][root_cause] = counts
    return result


def get_backend_developer_root_cause_stats(df):
    backend_col = _find_column(df, ['后端', '后端开发'])
    if not backend_col or 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'backend_developers': [], 'root_causes': {}}

    backend_df = df[
        (df['责任方'] == '开发侧') &
        _non_empty(df, 'bug根因登记') &
        df[backend_col].notna()
    ]
    if backend_df.empty:
        return {'backend_developers': [], 'root_causes': {}}

    backend_developers = backend_df[backend_col].value_counts().index.tolist()[:10]
    root_causes = backend_df['bug根因登记'].value_counts().index.tolist()[:10]

    result = {'backend_developers': backend_developers, 'root_causes': {}}
    for root_cause in root_causes:
        counts = []
        for developer in backend_developers:
            count = len(
                backend_df[
                    (backend_df['bug根因登记'] == root_cause) &
                    (backend_df[backend_col] == developer)
                ]
            )
            counts.append(int(count))
        result['root_causes'][root_cause] = counts
    return result


def get_tester_person_root_cause_stats(df):
    tester_col = _find_column(df, ['提交人', '测试人员'])
    if not tester_col or 'bug根因登记' not in df.columns or '责任方' not in df.columns:
        return {'tester_persons': [], 'root_causes': {}}

    tester_df = df[
        (df['责任方'] == '测试侧') &
        _non_empty(df, 'bug根因登记') &
        df[tester_col].notna()
    ]
    if tester_df.empty:
        return {'tester_persons': [], 'root_causes': {}}

    tester_persons = tester_df[tester_col].value_counts().index.tolist()[:10]
    root_causes = tester_df['bug根因登记'].value_counts().index.tolist()[:10]

    result = {'tester_persons': tester_persons, 'root_causes': {}}
    for root_cause in root_causes:
        counts = []
        for tester in tester_persons:
            count = len(
                tester_df[
                    (tester_df['bug根因登记'] == root_cause) &
                    (tester_df[tester_col] == tester)
                ]
            )
            counts.append(int(count))
        result['root_causes'][root_cause] = counts
    return result


def get_req_priority_status_stats(req_df):
    priority_col = _find_column(req_df, ['版本内研发优先级别', '优先级', '需求优先级'])
    status_col = _find_column(req_df, ['需求状态', '状态'])
    if not priority_col or not status_col:
        return {'priorities': [], 'statuses': {}}

    valid_df = req_df[req_df[priority_col].notna() & req_df[status_col].notna()]
    priorities = valid_df[priority_col].value_counts().index.tolist()
    statuses = valid_df[status_col].dropna().unique().tolist()

    result = {'priorities': priorities, 'statuses': {}}
    for status in statuses:
        counts = []
        for priority in priorities:
            count = len(valid_df[(valid_df[priority_col] == priority) & (valid_df[status_col] == status)])
            counts.append(int(count))
        result['statuses'][status] = counts
    return result


def get_req_priority_type_stats(req_df):
    priority_col = _find_column(req_df, ['版本内研发优先级别', '优先级', '需求优先级'])
    type_col = _find_column(req_df, ['需求类型', '类型'])
    if not priority_col or not type_col:
        return {'priorities': [], 'types': {}}

    valid_df = req_df[req_df[priority_col].notna() & req_df[type_col].notna()]
    priorities = valid_df[priority_col].value_counts().index.tolist()
    types = valid_df[type_col].dropna().unique().tolist()

    result = {'priorities': priorities, 'types': {}}
    for req_type in types:
        counts = []
        for priority in priorities:
            count = len(valid_df[(valid_df[priority_col] == priority) & (valid_df[type_col] == req_type)])
            counts.append(int(count))
        result['types'][req_type] = counts
    return result


def get_req_group_stats(req_df):
    group_col = _find_column(req_df, ['责任小组', '负责小组', '责任组'])
    if not group_col:
        return {'groups': [], 'counts': []}

    group_stats = req_df[req_df[group_col].notna()][group_col].value_counts()
    return {
        'groups': group_stats.index.tolist(),
        'counts': _to_int_list(group_stats.values.tolist()),
    }


def get_req_product_manager_stats(req_df):
    manager_col = _find_column(req_df, ['产品经理', '产品'])
    if not manager_col:
        return {'product_managers': [], 'counts': []}

    manager_stats = req_df[req_df[manager_col].notna()][manager_col].value_counts()
    return {
        'product_managers': manager_stats.index.tolist(),
        'counts': _to_int_list(manager_stats.values.tolist()),
    }


def get_req_developer_stats(req_df):
    developers = {}
    frontend_col = _find_column(req_df, ['前端开发', '前端'])
    backend_col = _find_column(req_df, ['后端开发', '后端'])

    if frontend_col:
        frontend_stats = req_df[req_df[frontend_col].notna()][frontend_col].value_counts()
        for developer, count in frontend_stats.items():
            developers[f'前端-{developer}'] = int(count)

    if backend_col:
        backend_stats = req_df[req_df[backend_col].notna()][backend_col].value_counts()
        for developer, count in backend_stats.items():
            key = f'后端-{developer}'
            developers[key] = developers.get(key, 0) + int(count)

    sorted_developers = sorted(developers.items(), key=lambda item: item[1], reverse=True)
    return {
        'developers': [item[0] for item in sorted_developers],
        'counts': [item[1] for item in sorted_developers],
    }


def get_req_tester_workload_stats(req_df):
    tester_col = _find_column(req_df, ['测试人员', '提交人'])
    workload_col = _find_column(req_df, ['测试工时（天）', '测试工时(天)', '测试工时'])
    if not tester_col:
        return {'testers': [], 'req_counts': [], 'workloads': []}

    valid_df = req_df[req_df[tester_col].notna()]
    testers = valid_df[tester_col].value_counts().index.tolist()

    req_counts = []
    workloads = []
    for tester in testers:
        tester_df = valid_df[valid_df[tester_col] == tester]
        req_counts.append(int(len(tester_df)))
        if workload_col:
            workload = pd.to_numeric(tester_df[workload_col], errors='coerce').sum()
            workloads.append(round(float(workload), 2) if not pd.isna(workload) else 0)
        else:
            workloads.append(0)
    return {'testers': testers, 'req_counts': req_counts, 'workloads': workloads}


def get_testcase_tester_stats(tc_df):
    tester_col = _find_column(tc_df, ['测试人员', '测试负责人'])
    executed_col = _find_column(tc_df, ['已执行', '已执行数'])
    not_executed_col = _find_column(tc_df, ['未执行', '未执行数'])
    total_col = _find_column(tc_df, ['总测试用例数量', '测试用例总数', '总数'])
    if not tester_col:
        return {
            'testers': [],
            'executed': [],
            'not_executed': [],
            'total': [],
            'total_executed': 0,
            'total_not_executed': 0,
            'total_all': 0,
            'total_rate': 0,
        }

    valid_df = tc_df[tc_df[tester_col].notna()].copy()
    testers = valid_df[tester_col].tolist()

    def to_int_list(column):
        if column and column in valid_df.columns:
            return pd.to_numeric(valid_df[column], errors='coerce').fillna(0).astype(int).tolist()
        return [0] * len(testers)

    executed = to_int_list(executed_col)
    not_executed = to_int_list(not_executed_col)
    total = to_int_list(total_col)

    total_executed = int(sum(executed))
    total_not_executed = int(sum(not_executed))
    total_all = int(sum(total))
    total_rate = round(total_executed / total_all * 100, 2) if total_all else 0

    return {
        'testers': testers,
        'executed': executed,
        'not_executed': not_executed,
        'total': total,
        'total_executed': total_executed,
        'total_not_executed': total_not_executed,
        'total_all': total_all,
        'total_rate': total_rate,
    }


def get_defect_req_rate_stats(defect_df, req_df, tc_df):
    req_tester_col = _find_column(req_df, ['测试人员', '提交人'])
    tc_tester_col = _find_column(tc_df, ['测试人员', '测试负责人'])
    if not req_tester_col or not tc_tester_col:
        return {'categories': ['有缺陷需求', '无缺陷需求'], 'counts': [0, 0]}

    tc_testers = set(tc_df[tc_tester_col].dropna().tolist())
    filtered_req = req_df[req_df[req_tester_col].isin(tc_testers)]
    if filtered_req.empty:
        return {'categories': ['有缺陷需求', '无缺陷需求'], 'counts': [0, 0]}

    defect_jira_col = _find_column(defect_df, DEFECT_JIRA_COLUMNS)
    req_jira_col = _find_column(req_df, REQ_JIRA_COLUMNS)
    if not defect_jira_col or not req_jira_col:
        return {'categories': ['有缺陷需求', '无缺陷需求'], 'counts': [0, int(len(filtered_req))]}

    defect_jiras = set(defect_df[defect_jira_col].dropna().tolist())
    has_defect = filtered_req[filtered_req[req_jira_col].isin(defect_jiras)]
    no_defect = filtered_req[~filtered_req[req_jira_col].isin(defect_jiras)]

    return {
        'categories': ['有缺陷需求', '无缺陷需求'],
        'counts': [int(len(has_defect)), int(len(no_defect))],
    }
