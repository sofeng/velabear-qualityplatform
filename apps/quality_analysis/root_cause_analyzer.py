import pandas as pd


ROOT_CAUSE_RESULT_COLUMN = 'bug根因登记'
RESPONSIBILITY_RESULT_COLUMN = '责任方'
SOURCE_CAUSE_COLUMN = '问题原因'


ROOT_CAUSE_KEYWORDS = {
    '需求文档问题': [
        '原型没写',
        '原型未写',
        '需求没说明',
        '需求未说明',
        '需求未体现',
        '需求文档',
        '产品未考虑',
    ],
    '需求变更未同步': [
        '需求变更',
        '需求更新',
        '未告知',
        '未同步',
        '补充要求',
    ],
    '需求设计问题': [
        '需求设计',
        '原始需求',
        '根据最新需求调整',
        '设计不合理',
    ],
    '需求问题': [
        '需求问题',
    ],
    '开发遗漏': [
        '做漏',
        '遗漏',
        '漏改',
        '未实现',
        '没有实现',
        '没有处理',
        '未处理',
        '未开发',
        '功能点遗漏',
        '漏字段',
    ],
    '代码逻辑错误': [
        '逻辑问题',
        '代码逻辑',
        '业务逻辑',
        '判断逻辑',
        '逻辑错误',
    ],
    '编码实现问题': [
        '字段映射',
        '字段错误',
        '参数传错',
        '参数错误',
        '赋值错误',
        '计算不对',
        '报错',
        '异常',
        '精度问题',
        '长度问题',
        '返回字段',
    ],
    '场景考虑不周': [
        '场景未覆盖',
        '场景考虑',
        '未考虑',
        '没考虑',
        '漏判',
    ],
    '性能问题/技术难题': [
        '性能',
        '超时',
        '过慢',
        '技术难题',
        '技术难度',
    ],
    '开发自测覆盖不足': [
        '自测遗漏',
        '未自测',
        '自测覆盖',
        '自测漏测',
    ],
    '测试覆盖不足': [
        '未测试到',
        '测试遗漏',
        '测试覆盖',
        '按测试要求',
    ],
    '历史遗留问题': [
        '历史bug',
        '历史BUG',
        '历史问题',
        '历史数据',
        '以前',
        '原来',
        '之前',
    ],
    '环境配置问题': [
        '环境',
        '部署',
        '打包',
        '构建',
        '服务器',
        'mysql',
        '版本发布',
    ],
    '权限配置问题': [
        '权限',
        '未登录',
        '登录失败',
        '流程配置',
        '配置问题',
    ],
    '第三方依赖/兼容性问题': [
        '第三方',
        '依赖',
        '兼容',
        '地图',
        '百度地图',
        '高德地图',
    ],
    '数据问题': [
        '脏数据',
        '数据问题',
        '数据空',
        '数据少',
        '数据缺失',
    ],
    '非BUG': [
        '非bug',
        '非BUG',
        '不属于bug',
        '非业务问题',
    ],
    'UI/交互问题': [
        'ui样式',
        '交互',
        '前端交互',
        '按钮',
        '预览',
    ],
    '前端问题': [
        '前端处理',
        '前端传入',
        '前端报错',
    ],
    '文案问题': [
        'tip提示',
        '提示文字',
        '文案',
        '错别字',
    ],
    '优化需求': [
        '优化需求',
        '下期版本处理',
        '这期先不改',
    ],
    '其他-已知问题/说明': [
        '一样的问题',
        '具体',
        '新增功能',
        '说明',
    ],
    '需进一步分析': [
        '后端处理',
        '需要沟通',
        '等待',
        'ai平台',
    ],
}

RESPONSIBILITY_MAP = {
    '需求文档问题': '产品侧',
    '需求变更未同步': '产品侧',
    '需求设计问题': '产品侧',
    '需求问题': '产品侧',
    '文案问题': '产品侧',
    '开发遗漏': '开发侧',
    '代码逻辑错误': '开发侧',
    '编码实现问题': '开发侧',
    '场景考虑不周': '开发侧',
    '性能问题/技术难题': '开发侧',
    '开发自测覆盖不足': '开发侧',
    '测试覆盖不足': '测试侧',
    '历史遗留问题': '历史',
    'UI/交互问题': '前端侧',
    '前端问题': '前端侧',
    '环境配置问题': '开发侧',
    '权限配置问题': '开发侧',
}


def classify_root_cause(cause):
    if pd.isna(cause):
        return ''

    cause_str = str(cause).strip()
    if not cause_str:
        return ''

    lowered = cause_str.lower()
    for category, keywords in ROOT_CAUSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lowered:
                return category
    return '其他'


def extract_responsibility(root_cause):
    if pd.isna(root_cause):
        return ''

    root_cause_str = str(root_cause).strip()
    if not root_cause_str:
        return ''

    return RESPONSIBILITY_MAP.get(root_cause_str, '其他')


def analyze_dataframe(df):
    if SOURCE_CAUSE_COLUMN not in df.columns:
        raise ValueError(f'Excel 文件缺少【{SOURCE_CAUSE_COLUMN}】列')

    analyzed_df = df.copy()
    if '产品' in analyzed_df.columns:
        analyzed_df['产品'] = analyzed_df['产品'].apply(
            lambda value: str(value).replace('\t', '').strip() if pd.notna(value) else value
        )

    analyzed_df[ROOT_CAUSE_RESULT_COLUMN] = analyzed_df[SOURCE_CAUSE_COLUMN].apply(classify_root_cause)
    analyzed_df[RESPONSIBILITY_RESULT_COLUMN] = analyzed_df[ROOT_CAUSE_RESULT_COLUMN].apply(extract_responsibility)
    return analyzed_df


def analyze_excel(file_path):
    df = pd.read_excel(file_path)
    return analyze_dataframe(df)

