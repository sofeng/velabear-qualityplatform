import pandas as pd

from .root_cause_analyzer import (
    RESPONSIBILITY_RESULT_COLUMN,
    ROOT_CAUSE_RESULT_COLUMN,
    analyze_dataframe,
)


JIRA_COLUMNS = ['JIAR任务编码', 'JIRA任务编码']


def _get_jira_column(df):
    for column in JIRA_COLUMNS:
        if column in df.columns:
            return column
    return None


def generate_statistics(df):
    total = len(df)
    classified_df = df[
        df[ROOT_CAUSE_RESULT_COLUMN].notna() &
        (df[ROOT_CAUSE_RESULT_COLUMN].astype(str).str.strip() != '')
    ]
    classified = len(classified_df)

    result = {
        'total': int(total),
        'classified': int(classified),
        'unclassified': int(total - classified),
    }

    responsibility_series = df[
        df[RESPONSIBILITY_RESULT_COLUMN].notna() &
        (df[RESPONSIBILITY_RESULT_COLUMN].astype(str).str.strip() != '')
    ][RESPONSIBILITY_RESULT_COLUMN].value_counts()
    result['responsibility'] = {key: int(value) for key, value in responsibility_series.items()}

    root_cause_series = classified_df[ROOT_CAUSE_RESULT_COLUMN].value_counts()
    result['root_cause'] = {key: int(value) for key, value in root_cause_series.items()}

    if '产品' in df.columns:
        product_series = df[df['产品'].notna()]['产品'].value_counts()
        result['product'] = {key: int(value) for key, value in product_series.items()}

    jira_col = _get_jira_column(df)
    if jira_col:
        requirement_series = df[df[jira_col].notna()][jira_col].value_counts()
        result['requirements'] = {key: int(value) for key, value in requirement_series.items()}
    else:
        result['requirements'] = {}

    return result


def read_and_analyze_dataframe(df):
    if ROOT_CAUSE_RESULT_COLUMN not in df.columns:
        raise ValueError(f'Excel 文件缺少【{ROOT_CAUSE_RESULT_COLUMN}】列，请先完成根因分析')
    if RESPONSIBILITY_RESULT_COLUMN not in df.columns:
        raise ValueError(f'Excel 文件缺少【{RESPONSIBILITY_RESULT_COLUMN}】列，请先完成责任方分析')

    analyzed_df = df.copy()
    if '产品' in analyzed_df.columns:
        analyzed_df['产品'] = analyzed_df['产品'].apply(
            lambda value: str(value).replace('\t', '').strip() if pd.notna(value) else value
        )

    return analyzed_df, generate_statistics(analyzed_df)


def read_and_analyze_excel(file_path):
    df = pd.read_excel(file_path)
    return read_and_analyze_dataframe(df)


def analyze_with_fallback(file_path):
    df = pd.read_excel(file_path)

    try:
        analyzed_df, statistics = read_and_analyze_dataframe(df)
        return analyzed_df, statistics, False
    except ValueError:
        analyzed_df = analyze_dataframe(df)
        return analyzed_df, generate_statistics(analyzed_df), True

