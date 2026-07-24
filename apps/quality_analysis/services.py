from io import BytesIO
from pathlib import Path

import pandas as pd
from django.core.files.base import ContentFile

from apps.users.models import User

from .excel_reader import analyze_with_fallback


def get_default_user(user=None):
    if user and getattr(user, 'is_authenticated', False):
        return user

    default_user = User.objects.filter(is_superuser=True).first()
    if default_user:
        return default_user
    return User.objects.first()


def load_excel_dataframe(file_field):
    if not file_field:
        raise ValueError('缺少 Excel 文件')
    return pd.read_excel(file_field.path)


def load_defect_dataframe(report):
    if report.processed_excel:
        return pd.read_excel(report.processed_excel.path)
    return pd.read_excel(report.source_excel.path)


def save_processed_excel(report, df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    base_name = Path(report.source_excel.name).stem
    filename = f'{report.version}_{base_name}_processed.xlsx'
    if report.processed_excel:
        report.processed_excel.delete(save=False)
    report.processed_excel.save(filename, ContentFile(output.getvalue()), save=False)


def analyze_report(report):
    dataframe, result, generated_processed = analyze_with_fallback(report.source_excel.path)
    if generated_processed:
        save_processed_excel(report, dataframe)

    report.status = 'completed'
    report.total_defects = result['total']
    report.classified_defects = result['classified']
    report.analysis_result = result
    report.error_message = ''
    return dataframe, result

