import unittest
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl
from unittest.mock import patch

import pandas as pd
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.plaintext_secrets import encrypt_password
from .analytics import (
    get_defect_req_rate_stats,
    get_requirement_defect_stats,
    get_root_cause_responsibility_stats,
)
from .excel_reader import analyze_with_fallback
from .jira_services import (
    DEFAULT_BUG_JIRA_COOKIE,
    build_default_jira_headers,
    build_default_jira_request_body,
    build_default_requirement_jira_headers,
    build_default_requirement_jira_request_body,
    execute_jira_config,
    execute_jira_requirement_config,
    JIRA_BUG_COOKIE_ENV,
    JIRA_GENERAL_AUTHORIZATION_ENV,
    JIRA_GENERAL_COOKIE_ENV,
    JIRA_GENERAL_PASSWORD_ENV,
    JIRA_GENERAL_USERNAME_ENV,
    RAW_FIELD_LABELS_META_KEY,
    REQUIREMENT_PROFILE,
    parse_jira_issue_table_payload,
)
from .models import (
    JiraBugRecord,
    JiraInterfaceConfig,
    JiraRequirementInterfaceConfig,
    JiraRequirementRecord,
    JiraRequirementRecordAttachment,
)
from .serializers import JiraBugRecordSerializer, JiraRequirementRecordSerializer
from .root_cause_analyzer import (
    RESPONSIBILITY_RESULT_COLUMN,
    ROOT_CAUSE_RESULT_COLUMN,
)
from .version_report_analytics import (
    build_rd_progress_overview_payload,
    build_requirement_overview_payload,
    build_testing_overview_payload,
    build_version_analysis_payload,
)
from .version_utils import jira_version_timeline_sort_key, normalize_jira_version
from apps.defects.models import Defect
from apps.projects.models import Project
from apps.testcases.models import ManualTestCaseMindmap
from apps.users.models import Role
from apps.versions.models import Version


def build_issue_table_payload(issue_key='SYSWIN-1', issue_id='101', summary='线上问题一'):
    return {
        'issueTable': {
            'total': 1,
            'displayed': 1,
            'startIndex': 0,
            'end': 1,
            'page': 0,
            'pageSize': 200,
            'issueKeys': [issue_key],
            'issueIds': [issue_id],
            'columns': [
                'issuetype',
                'issuekey',
                'summary',
                'customfield_10762',
                'customfield_10702',
                'status',
                'creator',
                'customfield_10222',
                'customfield_10731',
                'customfield_11000',
                'created',
            ],
            'table': f'''
                <table>
                  <tbody>
                    <tr id="issuerow{issue_id}" rel="{issue_id}" data-issuekey="{issue_key}" class="issuerow">
                      <td class="issuetype"><img alt="BUG" /></td>
                      <td class="issuekey"><a class="issue-link" data-issue-key="{issue_key}" href="/browse/{issue_key}">{issue_key}</a></td>
                      <td class="summary"><p><a class="issue-link" data-issue-key="{issue_key}" href="/browse/{issue_key}">{summary}</a></p></td>
                      <td class="customfield_10762"><span>客户A</span></td>
                      <td class="customfield_10702">P1</td>
                      <td class="status"><span>缺陷受理</span></td>
                      <td class="creator"><a>张三</a></td>
                      <td class="customfield_10222"><a>测试用户</a></td>
                      <td class="customfield_10731"><a>责任人甲</a></td>
                      <td class="customfield_11000"><span>平台组</span></td>
                      <td class="created">2026-04-18</td>
                    </tr>
                  </tbody>
                </table>
            ''',
        }
    }


ISSUE_CAUSE = '问题原因'
PRODUCT_SIDE = '产品侧'
DEVELOPER_SIDE = '开发侧'
REQ_DOC_ISSUE = '需求文档问题'
CODE_LOGIC_ISSUE = '代码逻辑错误'
DEFECT_PRESENT = '有缺陷需求'
DEFECT_ABSENT = '无缺陷需求'


class QualityAnalysisUnitTests(unittest.TestCase):
    def test_normalize_jira_version_keeps_text_before_release_marker(self):
        self.assertEqual(normalize_jira_version('26-04.18发版（8.2.1）'), '26-04.18')
        self.assertEqual(normalize_jira_version(' 26-04.18 发版（8.2.1） '), '26-04.18')
        self.assertEqual(normalize_jira_version('26-04.18'), '26-04.18')

    def test_jira_version_timeline_sort_key_orders_release_dates_old_to_new(self):
        versions = ['26-03.31', '26-04.15', '26-04.30', '26-05.15', '26-06.15', '26-05.30']

        self.assertEqual(
            sorted(versions, key=jira_version_timeline_sort_key),
            ['26-03.31', '26-04.15', '26-04.30', '26-05.15', '26-05.30', '26-06.15'],
        )

    def test_analyze_with_fallback_generates_classification_columns(self):
        source_df = pd.DataFrame(
            [
                {
                    ISSUE_CAUSE: '需求未说明，原型没写',
                    '产品': 'CRM',
                    'JIRA任务编码': 'REQ-1',
                },
                {
                    ISSUE_CAUSE: '逻辑错误导致计算异常',
                    '产品': 'CRM',
                    'JIRA任务编码': 'REQ-2',
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            excel_path = Path(temp_dir) / 'defects.xlsx'
            source_df.to_excel(excel_path, index=False)

            analyzed_df, statistics, generated_processed = analyze_with_fallback(excel_path)

        self.assertTrue(generated_processed)
        self.assertIn(ROOT_CAUSE_RESULT_COLUMN, analyzed_df.columns)
        self.assertIn(RESPONSIBILITY_RESULT_COLUMN, analyzed_df.columns)
        self.assertEqual(statistics['total'], 2)
        self.assertEqual(statistics['classified'], 2)
        self.assertEqual(analyzed_df.loc[0, ROOT_CAUSE_RESULT_COLUMN], REQ_DOC_ISSUE)
        self.assertEqual(analyzed_df.loc[0, RESPONSIBILITY_RESULT_COLUMN], PRODUCT_SIDE)
        self.assertEqual(analyzed_df.loc[1, ROOT_CAUSE_RESULT_COLUMN], CODE_LOGIC_ISSUE)
        self.assertEqual(analyzed_df.loc[1, RESPONSIBILITY_RESULT_COLUMN], DEVELOPER_SIDE)

    def test_analyze_with_fallback_reuses_existing_result_columns(self):
        source_df = pd.DataFrame(
            [
                {
                    ROOT_CAUSE_RESULT_COLUMN: REQ_DOC_ISSUE,
                    RESPONSIBILITY_RESULT_COLUMN: PRODUCT_SIDE,
                    'JIRA任务编码': 'REQ-1',
                },
                {
                    ROOT_CAUSE_RESULT_COLUMN: CODE_LOGIC_ISSUE,
                    RESPONSIBILITY_RESULT_COLUMN: DEVELOPER_SIDE,
                    'JIRA任务编码': 'REQ-1',
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            excel_path = Path(temp_dir) / 'processed.xlsx'
            source_df.to_excel(excel_path, index=False)

            analyzed_df, statistics, generated_processed = analyze_with_fallback(excel_path)

        self.assertFalse(generated_processed)
        self.assertEqual(statistics['total'], 2)
        self.assertEqual(statistics['classified'], 2)
        self.assertEqual(list(analyzed_df[ROOT_CAUSE_RESULT_COLUMN]), [REQ_DOC_ISSUE, CODE_LOGIC_ISSUE])
        self.assertEqual(list(analyzed_df[RESPONSIBILITY_RESULT_COLUMN]), [PRODUCT_SIDE, DEVELOPER_SIDE])

    def test_requirement_and_root_cause_statistics_follow_dataframe_content(self):
        defect_df = pd.DataFrame(
            [
                {
                    'JIRA任务编码': 'REQ-1',
                    ROOT_CAUSE_RESULT_COLUMN: REQ_DOC_ISSUE,
                    RESPONSIBILITY_RESULT_COLUMN: PRODUCT_SIDE,
                },
                {
                    'JIRA任务编码': 'REQ-1',
                    ROOT_CAUSE_RESULT_COLUMN: CODE_LOGIC_ISSUE,
                    RESPONSIBILITY_RESULT_COLUMN: DEVELOPER_SIDE,
                },
                {
                    'JIRA任务编码': 'REQ-2',
                    ROOT_CAUSE_RESULT_COLUMN: CODE_LOGIC_ISSUE,
                    RESPONSIBILITY_RESULT_COLUMN: DEVELOPER_SIDE,
                },
            ]
        )

        requirement_stats = get_requirement_defect_stats(defect_df)
        cause_stats = get_root_cause_responsibility_stats(defect_df)

        self.assertEqual(requirement_stats['requirements'], ['REQ-1', 'REQ-2'])
        self.assertEqual(requirement_stats['defect_counts'], [2, 1])
        self.assertEqual(cause_stats['root_causes'], [CODE_LOGIC_ISSUE, REQ_DOC_ISSUE])
        self.assertEqual(cause_stats['responsibilities'][DEVELOPER_SIDE], [2, 0])
        self.assertEqual(cause_stats['responsibilities'][PRODUCT_SIDE], [0, 1])

    def test_defect_requirement_rate_filters_by_testcase_testers_and_jira(self):
        defect_df = pd.DataFrame(
            [
                {'JIRA任务编码': 'REQ-1'},
                {'JIRA任务编码': 'REQ-3'},
            ]
        )
        req_df = pd.DataFrame(
            [
                {'JIRA需求编号': 'REQ-1', '测试人员': 'Alice'},
                {'JIRA需求编号': 'REQ-2', '测试人员': 'Alice'},
                {'JIRA需求编号': 'REQ-3', '测试人员': 'Bob'},
                {'JIRA需求编号': 'REQ-4', '测试人员': 'Carol'},
            ]
        )
        testcase_df = pd.DataFrame(
            [
                {'测试人员': 'Alice'},
                {'测试人员': 'Bob'},
            ]
        )

        result = get_defect_req_rate_stats(defect_df, req_df, testcase_df)

        self.assertEqual(result['categories'], [DEFECT_PRESENT, DEFECT_ABSENT])
        self.assertEqual(result['counts'], [2, 1])

    def test_default_jira_template_contains_filter_and_version(self):
        version = '26-04.18发版（8.2.1）'
        headers = build_default_jira_headers(version)
        body = build_default_jira_request_body(version)
        body_query = dict(parse_qsl(body))

        self.assertIn('filter=16128', headers['referer'])
        self.assertTrue(body.startswith('startIndex=0&filterId=16128&jql='))
        self.assertEqual(body_query['filterId'], '16128')
        self.assertEqual(body_query['layoutKey'], 'list-view')
        self.assertIn(version, body_query['jql'])
        self.assertNotIn('cookie', {key.lower(): value for key, value in headers.items()})

    def test_default_requirement_jira_template_contains_filter_and_version(self):
        version = '26-04.18发版（8.2.1）'
        headers = build_default_requirement_jira_headers(version)
        body = build_default_requirement_jira_request_body(version)
        body_query = dict(parse_qsl(body))

        self.assertIn('filter=15943', headers['referer'])
        self.assertTrue(body.startswith('startIndex=0&filterId=15943&jql='))
        self.assertEqual(body_query['filterId'], '15943')
        self.assertEqual(body_query['layoutKey'], 'list-view')
        self.assertIn(version, body_query['jql'])
        self.assertNotIn('cookie', {key.lower(): value for key, value in headers.items()})

    def test_default_jira_headers_allow_environment_auth_overrides(self):
        version = '26-04.18'
        with patch.dict(
            os.environ,
            {
                JIRA_GENERAL_COOKIE_ENV: 'cookie-from-env',
                JIRA_GENERAL_AUTHORIZATION_ENV: 'Bearer token-from-env',
            },
            clear=False,
        ):
            headers = build_default_jira_headers(version)

        self.assertEqual(headers['cookie'], 'cookie-from-env')
        self.assertEqual(headers['authorization'], 'Bearer token-from-env')

    def test_parse_jira_issue_table_payload_extracts_rows(self):
        payload = {
            'issueTable': {
                'total': 2,
                'displayed': 2,
                'startIndex': 0,
                'end': 2,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-1', 'SYSWIN-2'],
                'issueIds': ['101', '102'],
                'columns': [
                    'issuetype',
                    'issuekey',
                    'summary',
                    'customfield_10762',
                    'customfield_10702',
                    'status',
                    'creator',
                    'customfield_10222',
                    'customfield_10731',
                    'customfield_11000',
                    'customfield_11102',
                    'created',
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow101" rel="101" data-issuekey="SYSWIN-1" class="issuerow">
                          <td class="issuetype"><img alt="BUG" /></td>
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-1" href="/browse/SYSWIN-1">SYSWIN-1</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-1" href="/browse/SYSWIN-1">线上问题一</a></p></td>
                          <td class="customfield_10762"><span>客户A</span></td>
                          <td class="customfield_10702">P1 重要</td>
                          <td class="status"><span>缺陷受理</span></td>
                          <td class="creator"><a>张三</a></td>
                          <td class="customfield_10222"><a>测试甲</a></td>
                          <td class="customfield_10731"><a>责任人甲</a></td>
                          <td class="customfield_11000"><span>平台组</span></td>
                          <td class="customfield_11102"><span>需求遗漏</span></td>
                          <td class="created">2026-04-16</td>
                        </tr>
                        <tr id="issuerow102" rel="102" data-issuekey="SYSWIN-2" class="issuerow">
                          <td class="issuetype"><img alt="BUG" /></td>
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-2" href="/browse/SYSWIN-2">SYSWIN-2</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-2" href="/browse/SYSWIN-2">线上问题二</a></p></td>
                          <td class="customfield_10762"><span>客户B</span></td>
                          <td class="customfield_10702">P0 阻塞</td>
                          <td class="status"><span>开发任务完结</span></td>
                          <td class="creator"><a>李四</a></td>
                          <td class="customfield_10222"><a>测试乙</a></td>
                          <td class="customfield_10731"><a>责任人乙</a></td>
                          <td class="customfield_11000"><span>业务组</span></td>
                          <td class="customfield_11102"><span>代码逻辑错误</span></td>
                          <td class="created">2026-04-17</td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

        result = parse_jira_issue_table_payload(payload)

        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['records']), 2)
        self.assertEqual(result['records'][0]['issue_key'], 'SYSWIN-1')
        self.assertEqual(result['records'][0]['issue_type'], 'BUG')
        self.assertEqual(result['records'][0]['customer_name'], '客户A')
        self.assertEqual(result['records'][0]['tester'], '测试甲')
        self.assertEqual(result['records'][0]['handler'], '责任人甲')
        self.assertEqual(result['records'][1]['priority'], 'P0 阻塞')
        self.assertEqual(result['records'][1]['status'], '开发任务完结')
        self.assertEqual(result['records'][1]['group_name'], '业务组')

    def test_parse_jira_issue_table_payload_requires_documented_bug_field_keys(self):
        payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-9'],
                'issueIds': ['109'],
                'columns': [
                    {'id': 'keyword_field', 'label': '关键字'},
                    {'id': 'summary_field', 'label': '缺陷标题'},
                    {'id': 'group_field', 'label': '责任小组'},
                    {'id': 'frontend_field', 'label': '前端'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow109" rel="109" class="issuerow">
                          <td class="keyword_field">SYSWIN-9</td>
                          <td class="summary_field">线上缺陷标题</td>
                          <td class="group_field">平台组</td>
                          <td class="frontend_field">张三</td>
                          <td class="status"><span>归档缺陷</span></td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

        result = parse_jira_issue_table_payload(payload)

        self.assertEqual(result['records'], [])

    def test_parse_jira_issue_table_payload_normalizes_dirty_bug_field_key(self):
        payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-10'],
                'issueIds': ['110'],
                'columns': [
                    {'id': 'issuekey', 'label': '缺陷编号'},
                    {'id': 'summary', 'label': '缺陷标题'},
                    {'id': 'customfield_10019"', 'label': 'BUG重新打开次数'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow110" rel="110" data-issuekey="SYSWIN-10" class="issuerow">
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-10" href="/browse/SYSWIN-10">SYSWIN-10</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-10" href="/browse/SYSWIN-10">线上缺陷标题</a></p></td>
                          <td class="customfield_10019&quot;">3</td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

        result = parse_jira_issue_table_payload(payload)
        record = result['records'][0]

        self.assertEqual(record['raw_fields']['customfield_10019'], '3')
        self.assertNotIn('customfield_10019"', record['raw_fields'])
        self.assertEqual(record['raw_fields'][RAW_FIELD_LABELS_META_KEY]['customfield_10019'], 'BUG重新打开次数')

    def test_parse_jira_issue_table_payload_maps_requirement_fields(self):
        payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-REQ-1'],
                'issueIds': ['201'],
                'columns': [
                    {'id': 'issuekey', 'label': '需求编号'},
                    {'id': 'summary', 'label': '需求标题'},
                    {'id': 'customfield_10762', 'label': '客户或项目名称'},
                    {'id': 'customfield_11100', 'label': '版本内研发优先级别'},
                    {'id': 'status', 'label': '状态'},
                    {'id': 'creator', 'label': '创建人'},
                    {'id': 'customfield_10222', 'label': '测试人员'},
                    {'id': 'customfield_10743', 'label': '前端'},
                    {'id': 'customfield_10741', 'label': '后端'},
                    {'id': 'components', 'label': '模块'},
                    {'id': 'customfield_11017', 'label': '前端结束日期'},
                    {'id': 'customfield_11018', 'label': '提测时间'},
                    {'id': 'customfield_11020', 'label': '测试进展'},
                    {'id': 'customfield_10602', 'label': '前端是否完成'},
                    {'id': 'customfield_10603', 'label': '后端是否完成'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow201" rel="201" data-issuekey="SYSWIN-REQ-1" class="issuerow">
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-REQ-1" href="/browse/SYSWIN-REQ-1">SYSWIN-REQ-1</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-REQ-1" href="/browse/SYSWIN-REQ-1">需求一</a></p></td>
                          <td class="customfield_10762"><span>物业通</span></td>
                          <td class="customfield_11100"><span>P1</span></td>
                          <td class="status"><span>功能研发中</span></td>
                          <td class="creator"><a>张三</a></td>
                          <td class="customfield_10222"><a>测试甲</a></td>
                          <td class="customfield_10743"><a>前端乙</a></td>
                          <td class="customfield_10741"><a>后端丙</a></td>
                          <td class="components"><span>收费管理</span></td>
                          <td class="customfield_11017">2026-05-08</td>
                          <td class="customfield_11018">2026-05-09 10:00</td>
                          <td class="customfield_11020">联调中</td>
                          <td class="customfield_10602">是</td>
                          <td class="customfield_10603">否</td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

        result = parse_jira_issue_table_payload(payload, profile=REQUIREMENT_PROFILE)
        record = result['records'][0]

        self.assertEqual(record['issue_key'], 'SYSWIN-REQ-1')
        self.assertEqual(record['summary'], '需求一')
        self.assertEqual(record['customer_name'], '物业通')
        self.assertEqual(record['priority'], 'P1')
        self.assertEqual(record['tester'], '测试甲')
        self.assertEqual(record['frontend_developer'], '前端乙')
        self.assertEqual(record['backend_developer'], '后端丙')
        self.assertEqual(record['module'], '收费管理')
        self.assertEqual(record['raw_fields'][RAW_FIELD_LABELS_META_KEY]['customfield_11100'], '版本内研发优先级别')

    def test_parse_jira_issue_table_payload_requires_documented_requirement_field_keys(self):
        payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-REQ-9'],
                'issueIds': ['209'],
                'columns': [
                    {'id': 'keyword_field', 'label': '需求编号'},
                    {'id': 'summary_field', 'label': '需求标题'},
                    {'id': 'tester_field', 'label': '测试人员'},
                    {'id': 'frontend_field', 'label': '前端'},
                    {'id': 'status', 'label': '状态'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow209" rel="209" class="issuerow">
                          <td class="keyword_field">SYSWIN-REQ-9</td>
                          <td class="summary_field">需求标题</td>
                          <td class="tester_field">测试甲</td>
                          <td class="frontend_field">前端甲</td>
                          <td class="status"><span>归档需求</span></td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

        result = parse_jira_issue_table_payload(payload, profile=REQUIREMENT_PROFILE)

        self.assertEqual(result['records'], [])

    def test_requirement_record_serializer_uses_documented_raw_fields_only(self):
        record = JiraRequirementRecord.objects.create(
            version='26-05.15',
            issue_key='SYSWIN-REQ-STRICT-1',
            summary='旧标题',
            tester='旧测试',
            group_name='旧组别',
            frontend_developer='旧前端',
            backend_developer='旧后端',
            raw_fields={
                'issuekey': 'SYSWIN-REQ-STRICT-1',
                'summary': '文档字段需求标题',
                'status': '归档需求',
                'customfield_10222': '测试甲',
                'customfield_10737': '产品甲',
                'customfield_10743': '前端甲',
                'customfield_10741': '后端甲',
                'customfield_11000': '平台组',
                'tester_field': '测试乙',
                'frontend_field': '前端乙',
                RAW_FIELD_LABELS_META_KEY: {
                    'issuekey': '需求编号',
                    'summary': '需求标题',
                    'status': '状态',
                    'customfield_10222': '测试人员',
                    'customfield_10737': 'PM',
                    'customfield_10743': '前端',
                    'customfield_10741': '后端',
                    'customfield_11000': '组别',
                    'tester_field': '测试人员',
                    'frontend_field': '前端',
                },
            },
        )

        data = JiraRequirementRecordSerializer(record).data

        self.assertEqual(data['mapped_fields']['issue_key'], 'SYSWIN-REQ-STRICT-1')
        self.assertEqual(data['mapped_fields']['summary'], '文档字段需求标题')
        self.assertEqual(data['mapped_fields']['status'], '归档需求')
        self.assertEqual(data['mapped_fields']['tester'], '测试甲')
        self.assertEqual(data['mapped_fields']['product_manager'], '产品甲')
        self.assertEqual(data['mapped_fields']['frontend_developer'], '前端甲')
        self.assertEqual(data['mapped_fields']['backend_developer'], '后端甲')
        self.assertEqual(data['mapped_fields']['group_name'], '平台组')
        self.assertNotEqual(data['mapped_fields']['tester'], '归档需求')
        self.assertNotEqual(data['mapped_fields']['frontend_developer'], '归档需求')
        self.assertNotEqual(data['mapped_fields']['backend_developer'], '归档需求')

    def test_bug_record_serializer_uses_documented_raw_fields_only(self):
        record = JiraBugRecord(
            version='26-04.30',
            issue_key='SYSWIN-9',
            summary='旧标题',
            handler='旧责任人',
            tester='旧测试',
            group_name='旧组别',
            raw_fields={
                'issuekey': 'SYSWIN-9',
                'summary': '文档字段标题',
                'status': '归档缺陷',
                'customfield_10731': '责任人甲',
                'customfield_10222': '测试甲',
                'customfield_10743': '前端甲',
                'customfield_10741': '后端甲',
                'customfield_11000': '平台组',
                'group_field': '平台组',
                'frontend_field': '张三',
                'customfield_11102': '代码逻辑问题',
                'customfield_11101': '功能缺陷',
                'customfield_11103': '后端',
                RAW_FIELD_LABELS_META_KEY: {
                    'issuekey': '缺陷编号',
                    'summary': '缺陷标题',
                    'status': '状态',
                    'customfield_10731': 'BUG责任人',
                    'customfield_10222': '测试人员',
                    'customfield_10743': '前端',
                    'customfield_10741': '后端',
                    'customfield_11000': '组别',
                    'group_field': '责任小组',
                    'frontend_field': '前端',
                    'customfield_11102': 'BUG产生原因',
                    'customfield_11101': 'BUG定性分类',
                    'customfield_11103': 'BUG直接责任岗位',
                },
            },
        )

        data = JiraBugRecordSerializer(record).data

        self.assertEqual(data['mapped_fields']['defect_code'], 'SYSWIN-9')
        self.assertEqual(data['mapped_fields']['group_name'], '平台组')
        self.assertEqual(data['mapped_fields']['summary'], '文档字段标题')
        self.assertEqual(data['mapped_fields']['status'], '归档缺陷')
        self.assertEqual(data['mapped_fields']['handler'], '责任人甲')
        self.assertEqual(data['mapped_fields']['tester'], '测试甲')
        self.assertEqual(data['mapped_fields']['frontend_developer'], '前端甲')
        self.assertEqual(data['mapped_fields']['backend_developer'], '后端甲')
        self.assertNotEqual(data['mapped_fields']['handler'], '归档缺陷')
        self.assertNotEqual(data['mapped_fields']['tester'], '归档缺陷')
        self.assertNotEqual(data['mapped_fields']['frontend_developer'], '归档缺陷')
        self.assertNotEqual(data['mapped_fields']['backend_developer'], '归档缺陷')


class VersionAnalysisPayloadTests(unittest.TestCase):
    def test_requirements_tab_contains_version_requirement_capability(self):
        report = SimpleNamespace(id=101)
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    issue_type='标准化需求',
                    status='功能研发中',
                    priority='P1',
                    module='账号 / 登录',
                    creator='Alice',
                    handler='Bob',
                    tester='Carol',
                    group_name='会员组',
                    raw_fields={
                        'customfield_10737': '产品A',
                        'customfield_10749': '2',
                        'customfield_10748': '3',
                        'customfield_10761': '1',
                    },
                )
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_version_analysis_payload(report, user=SimpleNamespace(id=1))

        requirements_tab = next(item for item in payload['tabs'] if item['key'] == 'requirements')
        block_titles = [block['title'] for block in requirements_tab['blocks']]

        self.assertIn('版本需求状态分布', block_titles)
        self.assertIn('版本需求模块分布', block_titles)
        self.assertIn('版本需求关键信息', block_titles)
        self.assertIn('版本需求优先级 × 状态', block_titles)

        detail_block = next(block for block in requirements_tab['blocks'] if block['title'] == '版本需求关键信息')
        self.assertEqual(
            [column['key'] for column in detail_block['columns']],
            ['issue_key', 'summary', 'issue_type', 'priority', 'status', 'module', 'product_manager', 'tester', 'group_name'],
        )
        self.assertEqual(detail_block['rows'][0]['issue_key'], 'SYSWIN-REQ-1')

    def test_dev_self_test_tab_includes_blocked_count_in_module_coverage(self):
        report = SimpleNamespace(id=102)
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [],
            'modules': [],
            'cases': [],
            'testpoints': [
                {
                    'module_path': '账号 / 登录',
                    'status': 'pass',
                }
            ],
            'dev_self_tests': [
                {
                    'module_path': '账号 / 登录',
                    'status': 'block',
                    'audit_status': 'pending',
                    'responsibility_group': '会员组',
                }
            ],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_version_analysis_payload(report, user=SimpleNamespace(id=1))

        dev_self_test_tab = next(item for item in payload['tabs'] if item['key'] == 'dev-self-test')
        module_block = next(block for block in dev_self_test_tab['blocks'] if block['title'] == '模块自测覆盖')

        self.assertEqual(module_block['rows'][0]['module'], '账号 / 登录')
        self.assertEqual(module_block['rows'][0]['dev_self_tests'], 1)
        self.assertEqual(module_block['rows'][0]['dev_self_test_failed'], 0)
        self.assertEqual(module_block['rows'][0]['dev_self_test_blocked'], 1)
        self.assertEqual(module_block['rows'][0]['testpoints'], 1)

    def test_version_analysis_groups_empty_group_into_no_group_bucket(self):
        report = SimpleNamespace(id=103)
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=41,
                    name='SYSWIN-REQ-1 登录流程优化',
                    responsibility_group='',
                    author=None,
                    frontend_developer=None,
                    backend_developer=None,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [
                {
                    'module_path': '账号 / 登录',
                    'status': 'pass',
                    'audit_status': 'approved',
                    'responsibility_group': '',
                    'frontend_developer': '',
                    'backend_developer': '',
                }
            ],
            'version_defects': [],
            'online_bugs': [
                SimpleNamespace(
                    issue_key='BUG-1',
                    summary='登录页异常',
                    status='处理中',
                    priority='P1',
                    module='账号 / 登录',
                    creator='',
                    handler='',
                    tester='',
                    group_name='',
                    raw_fields={
                        'customfield_11102': '测试遗漏',
                    },
                )
            ],
            'requirements': [
                SimpleNamespace(
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    issue_type='标准化需求',
                    status='处理中',
                    priority='P1',
                    module='账号 / 登录',
                    creator='',
                    handler='',
                    tester='',
                    group_name='',
                    raw_fields={},
                )
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_version_analysis_payload(report, user=SimpleNamespace(id=1))

        requirements_tab = next(item for item in payload['tabs'] if item['key'] == 'requirements')
        group_distribution = next(block for block in requirements_tab['blocks'] if block['title'] == '版本需求组别分布')
        self.assertEqual(group_distribution['rows'][0]['label'], '无组别')

        people_tab = next(item for item in payload['tabs'] if item['key'] == 'people')
        group_view = next(block for block in people_tab['blocks'] if block['title'] == '组别视角')
        self.assertEqual(group_view['rows'][0]['name'], '无组别')


class LiveOverviewPayloadTests(unittest.TestCase):
    def test_requirement_overview_payload_uses_live_scope_and_timeline_fields(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=31,
                    name='SYSWIN-REQ-1 登录流程优化',
                    responsibility_group='会员组',
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    status='已完成',
                    group_name='会员组',
                    tester='后端开发甲',
                    raw_fields={
                        'customfield_10522': '2026-04-20',
                        'customfield_11017': '2026-04-22',
                        'customfield_10523': '2026-04-21',
                        'customfield_11019': '2026-04-23',
                        'customfield_10743': '前端开发甲',
                    },
                    created_at=current_time,
                    synced_at=current_time,
                ),
                SimpleNamespace(
                    id=12,
                    issue_key='SYSWIN-REQ-2',
                    summary='结算流程优化',
                    status='处理中',
                    group_name='结算组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_requirement_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['report_version'], '26-04.21')
        self.assertEqual(payload['project']['id'], 7)
        self.assertEqual(len(payload['requirements']), 2)
        item = payload['requirements'][0]
        self.assertEqual(item['issueKey'], 'SYSWIN-REQ-1')
        self.assertEqual(item['issue_key'], 'SYSWIN-REQ-1')
        self.assertEqual(item['groupName'], '会员组')
        self.assertEqual(item['group_name'], '会员组')
        self.assertEqual(item['frontendDeveloper'], '前端开发甲')
        self.assertEqual(item['frontend_developer'], '前端开发甲')
        self.assertEqual(item['backendDeveloper'], '后端开发甲')
        self.assertEqual(item['backend_developer'], '后端开发甲')
        self.assertEqual(item['statusState'], 'completed')
        self.assertEqual(item['frontendTask']['startLabel'], '2026-04-21')
        self.assertEqual(item['backendTask']['startLabel'], '2026-04-20')
        self.assertEqual(item['backendTask']['endLabel'], '2026-04-23')

    def test_requirement_overview_payload_uses_jira_requirements_as_group_count_source(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=31,
                    name='登录流程优化',
                    requirement_key='SYSWIN-REQ-1',
                    responsibility_group='会员组',
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    status='处理中',
                    group_name='会员组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
                SimpleNamespace(
                    id=12,
                    issue_key='SYSWIN-REQ-2',
                    summary='结算流程优化',
                    status='已完成',
                    group_name='结算组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_requirement_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(len(payload['requirements']), 2)
        self.assertEqual(payload['requirements'][0]['issueKey'], 'SYSWIN-REQ-1')
        self.assertEqual(payload['requirements'][1]['issueKey'], 'SYSWIN-REQ-2')

    def test_requirement_overview_payload_keeps_jira_requirements_when_no_mindmap_matches(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=31,
                    name='登录流程优化',
                    responsibility_group='会员组',
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='历史需求A',
                    status='处理中',
                    group_name='会员组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
                SimpleNamespace(
                    id=12,
                    issue_key='SYSWIN-REQ-2',
                    summary='历史需求B',
                    status='已完成',
                    group_name='结算组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_requirement_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['report_version'], '26-04.21')
        self.assertEqual(payload['project']['id'], 7)
        self.assertEqual(len(payload['requirements']), 2)
        self.assertEqual(payload['requirements'][0]['issueKey'], 'SYSWIN-REQ-1')
        self.assertEqual(payload['requirements'][1]['issueKey'], 'SYSWIN-REQ-2')

    def test_requirement_overview_payload_maps_empty_group_to_no_group_bucket(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=31,
                    name='SYSWIN-REQ-1 登录流程优化',
                    responsibility_group='',
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    status='处理中',
                    group_name='',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_requirement_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['requirements'][0]['groupName'], '无组别')
        self.assertEqual(payload['requirements'][0]['group_name'], '无组别')

    def test_testing_overview_payload_returns_status_segments(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=41,
                    name='SYSWIN-REQ-1 登录流程优化',
                    requirement_key='SYSWIN-REQ-1',
                    requirement_title='登录流程优化',
                    responsibility_group='会员组',
                    author=SimpleNamespace(full_name='测试甲'),
                    frontend_developer=SimpleNamespace(full_name='前端开发甲'),
                    backend_developer=SimpleNamespace(full_name='后端开发甲'),
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [
                {'mindmap_id': 41, 'status': 'pass'},
                {'mindmap_id': 41, 'status': 'fail'},
                {'mindmap_id': 41, 'status': ''},
                {'mindmap_id': 41, 'status': 'not_test'},
            ],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_testing_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['report_version'], '26-04.21')
        self.assertEqual(payload['project']['name'], 'CRM')
        self.assertEqual(len(payload['mindmaps']), 1)
        item = payload['mindmaps'][0]
        self.assertEqual(item['name'], 'SYSWIN-REQ-1 登录流程优化')
        self.assertEqual(item['mindmapName'], 'SYSWIN-REQ-1 登录流程优化')
        self.assertEqual(item['requirementKey'], 'SYSWIN-REQ-1')
        self.assertEqual(item['requirement_key'], 'SYSWIN-REQ-1')
        self.assertEqual(item['requirementTitle'], '登录流程优化')
        self.assertEqual(item['requirement_title'], '登录流程优化')
        self.assertEqual(item['responsibility_group'], '会员组')
        self.assertEqual(item['testerName'], '测试甲')
        self.assertEqual(item['tester'], '测试甲')
        self.assertEqual(item['frontendDeveloper'], '前端开发甲')
        self.assertEqual(item['frontend_developer'], '前端开发甲')
        self.assertEqual(item['backendDeveloper'], '后端开发甲')
        self.assertEqual(item['backend_developer'], '后端开发甲')
        self.assertEqual(item['testpoint_count']['not_run'], 1)
        self.assertEqual(item['testpoint_count']['pass'], 1)
        self.assertEqual(item['testpoint_count']['fail'], 1)
        self.assertEqual(item['testpoint_count']['not_test'], 1)
        self.assertEqual(item['totalCount'], 4)
        self.assertEqual(item['progressState'], 'risk')
        self.assertEqual([segment['key'] for segment in item['segments']], ['not_run', 'pass', 'fail', 'not_test'])

    def test_testing_overview_payload_maps_empty_group_to_no_group_bucket(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=41,
                    name='SYSWIN-REQ-1 登录流程优化',
                    responsibility_group='',
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_testing_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['mindmaps'][0]['groupName'], '无组别')
        self.assertEqual(payload['mindmaps'][0]['responsibility_group'], '无组别')

    def test_testing_overview_payload_prefers_jira_requirement_group_for_grouping(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=41,
                    name='登录流程优化',
                    requirement_key='SYSWIN-REQ-1',
                    responsibility_group='本地脑图组',
                    author=SimpleNamespace(full_name='测试甲'),
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [
                {'mindmap_id': 41, 'status': 'pass'},
            ],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    status='处理中',
                    group_name='JIRA会员组',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_testing_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['mindmaps'][0]['groupName'], 'JIRA会员组')
        self.assertEqual(payload['mindmaps'][0]['responsibility_group'], 'JIRA会员组')


    def test_testing_overview_payload_keeps_jira_requirement_without_mindmap_for_group_count(self):
        current_time = timezone.now()
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [
                SimpleNamespace(
                    id=41,
                    name='login',
                    requirement_key='SYSWIN-REQ-1',
                    requirement_title='login',
                    responsibility_group='local-group',
                    author=SimpleNamespace(full_name='tester-a'),
                    created_at=current_time,
                    updated_at=current_time,
                )
            ],
            'modules': [],
            'cases': [],
            'testpoints': [
                {'mindmap_id': 41, 'status': 'pass'},
            ],
            'dev_self_tests': [],
            'version_defects': [],
            'online_bugs': [],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    issue_key='SYSWIN-REQ-1',
                    summary='login',
                    status='处理中',
                    group_name='jira-group',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
                SimpleNamespace(
                    id=12,
                    issue_key='SYSWIN-REQ-2',
                    summary='settlement',
                    status='处理中',
                    group_name='jira-group',
                    raw_fields={},
                    created_at=current_time,
                    synced_at=current_time,
                ),
            ],
        }

        with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
            payload = build_testing_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(len(payload['mindmaps']), 2)
        self.assertEqual(payload['mindmaps'][0]['requirementKey'], 'SYSWIN-REQ-1')
        self.assertEqual(payload['mindmaps'][1]['requirementKey'], 'SYSWIN-REQ-2')
        self.assertEqual(payload['mindmaps'][1]['groupName'], 'jira-group')
        self.assertEqual(payload['mindmaps'][1]['totalCount'], 0)

    def test_rd_progress_overview_payload_aggregates_requirement_mindmap_counts(self):
        current_time = timezone.now()
        mindmap = SimpleNamespace(
            id=41,
            name='SYSWIN-REQ-1 登录流程优化',
            requirement_key='SYSWIN-REQ-1',
            requirement_title='登录流程优化',
            responsibility_group='本地组',
            author=SimpleNamespace(full_name='测试甲'),
            frontend_developer=SimpleNamespace(full_name='前端本地'),
            backend_developer=SimpleNamespace(full_name='后端本地'),
            mindmap_data={
                'root': {
                    'data': {'nodeType': 'root', 'text': 'root'},
                    'children': [
                        {
                            'data': {'nodeType': 'testpoint', 'text': '点A', 'reviewOpinion': '补充边界', 'reviewStatus': '已处理'},
                            'children': [],
                        },
                        {
                            'data': {'nodeType': 'testpoint', 'text': '点B', 'reviewOpinion': '补充异常', 'reviewStatus': ''},
                            'children': [],
                        },
                    ],
                }
            },
            created_at=current_time,
            updated_at=current_time,
        )
        workspace_context = {
            'project': SimpleNamespace(id=7, name='CRM'),
            'version': '26-04.21',
            'version_ids': [],
            'mindmaps': [mindmap],
            'modules': [],
            'cases': [
                {'mindmap_id': 41, 'status': 'pass'},
                {'mindmap_id': 41, 'status': 'fail'},
            ],
            'testpoints': [
                {'mindmap_id': 41, 'status': 'pass'},
                {'mindmap_id': 41, 'status': 'block'},
                {'mindmap_id': 41, 'status': ''},
            ],
            'dev_self_tests': [
                {'mindmap_id': 41, 'status': 'pass'},
                {'mindmap_id': 41, 'status': 'fail'},
            ],
            'version_defects': [
                SimpleNamespace(status='new', related_testpoints=[{'mindmap_id': 41, 'node_id': 'tp-1'}]),
                SimpleNamespace(status='closed', related_testpoints=[{'mindmap_id': '41', 'node_id': 'tp-2'}]),
                SimpleNamespace(status='new', related_testpoints=[{'mindmap_id': 99, 'node_id': 'tp-x'}]),
            ],
            'online_bugs': [
                SimpleNamespace(status='待处理', related_requirements=[{'issue_key': 'SYSWIN-REQ-1'}], related_testpoints=[]),
                SimpleNamespace(status='已关闭', related_requirements=[], related_testpoints=[{'mindmap_id': 41, 'node_id': 'tp-3'}]),
                SimpleNamespace(status='待处理', related_requirements=[{'issue_key': 'SYSWIN-REQ-X'}], related_testpoints=[]),
            ],
            'requirements': [
                SimpleNamespace(
                    id=11,
                    row_index=2,
                    issue_key='SYSWIN-REQ-1',
                    summary='登录流程优化',
                    customer_name='客户A',
                    priority='P2',
                    status='处理中',
                    module='会员',
                    group_name='JIRA组',
                    product_manager='',
                    frontend_developer='前端甲',
                    backend_developer='后端乙',
                    tester='测试甲',
                    raw_fields={
                        'customfield_11100': 'P1',
                        'customfield_10737': 'PM甲',
                    },
                    related_mindmaps=[{'mindmap_id': 41, 'mindmap_name': 'SYSWIN-REQ-1 登录流程优化'}],
                    created_at=current_time,
                    synced_at=current_time,
                )
            ],
        }

        with patch('apps.quality_analysis.models.QualityAnalysisSettings.get_solo') as mocked_settings:
            mocked_settings.return_value = SimpleNamespace(jira_browse_prefix='https://jira.example.com/browse/')
            with patch('apps.quality_analysis.version_report_analytics._collect_workspace_context', return_value=workspace_context):
                payload = build_rd_progress_overview_payload(SimpleNamespace(id=None, version='26-04.21'), user=SimpleNamespace(id=1))

        self.assertEqual(payload['report_version'], '26-04.21')
        self.assertEqual(payload['project']['name'], 'CRM')
        self.assertEqual(len(payload['rows']), 1)
        row = payload['rows'][0]
        self.assertEqual(row['requirement_key'], 'SYSWIN-REQ-1')
        self.assertEqual(row['requirement_url'], 'https://jira.example.com/browse/SYSWIN-REQ-1')
        self.assertEqual(row['requirement_title'], '登录流程优化')
        self.assertEqual(row['customer_name'], '客户A')
        self.assertEqual(row['priority'], 'P1')
        self.assertEqual(row['group_name'], 'JIRA组')
        self.assertEqual(row['pm'], 'PM甲')
        self.assertEqual(row['frontend_developer'], '前端甲')
        self.assertEqual(row['backend_developer'], '后端乙')
        self.assertEqual(row['tester'], '测试甲')
        self.assertEqual(row['mindmaps'], [{'id': 41, 'name': 'SYSWIN-REQ-1 登录流程优化'}])
        self.assertEqual(row['dev_self_test_count']['pass'], 1)
        self.assertEqual(row['dev_self_test_count']['fail'], 1)
        self.assertEqual(row['case_count']['pass'], 1)
        self.assertEqual(row['case_count']['fail'], 1)
        self.assertEqual(row['testpoint_count']['not_run'], 1)
        self.assertEqual(row['testpoint_count']['pass'], 1)
        self.assertEqual(row['testpoint_count']['block'], 1)
        self.assertEqual(row['review_testpoint_count'], {'unprocessed': 1, 'processed': 1, 'total': 2})
        self.assertEqual(
            row['version_defect_count'],
            [
                {'key': 'new', 'label': '新缺陷', 'count': 1},
                {'key': 'closed', 'label': '已关闭', 'count': 1},
            ],
        )
        self.assertEqual(row['version_defect_count_total'], 2)
        self.assertCountEqual(
            row['online_defect_count'],
            [
                {'key': '待处理', 'label': '待处理', 'count': 1},
                {'key': '已关闭', 'label': '已关闭', 'count': 1},
            ],
        )
        self.assertEqual(row['online_defect_count_total'], 2)
        self.assertEqual(payload['summary']['requirement_count'], [{'key': '处理中', 'label': '处理中', 'count': 1}])
        self.assertEqual(payload['summary']['requirement_count_total'], 1)
        self.assertEqual(payload['summary']['dev_self_test_count']['pass'], 1)
        self.assertEqual(payload['summary']['dev_self_test_count']['fail'], 1)
        self.assertEqual(payload['summary']['dev_self_test_count_total'], 2)
        self.assertEqual(payload['summary']['testpoint_count']['not_run'], 1)
        self.assertEqual(payload['summary']['testpoint_count']['pass'], 1)
        self.assertEqual(payload['summary']['testpoint_count']['block'], 1)
        self.assertEqual(payload['summary']['testpoint_count_total'], 3)
        self.assertEqual(
            payload['summary']['version_defect_count'],
            [
                {'key': 'new', 'label': '新缺陷', 'count': 2},
                {'key': 'closed', 'label': '已关闭', 'count': 1},
            ],
        )
        self.assertEqual(payload['summary']['version_defect_count_total'], 3)
        self.assertCountEqual(
            payload['summary']['online_defect_count'],
            [
                {'key': '待处理', 'label': '待处理', 'count': 2},
                {'key': '已关闭', 'label': '已关闭', 'count': 1},
            ],
        )
        self.assertEqual(payload['summary']['online_defect_count_total'], 3)


class JiraSyncExecutionTests(TestCase):
    def _build_payload(self, issue_key='SYSWIN-1', issue_id='101', summary='线上问题一'):
        return {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': [issue_key],
                'issueIds': [issue_id],
                'columns': [
                    'issuetype',
                    'issuekey',
                    'summary',
                    'customfield_10762',
                    'customfield_10702',
                    'status',
                    'creator',
                    'customfield_10222',
                    'customfield_10731',
                    'customfield_11000',
                    'created',
                ],
                'table': f'''
                    <table>
                      <tbody>
                        <tr id="issuerow{issue_id}" rel="{issue_id}" data-issuekey="{issue_key}" class="issuerow">
                          <td class="issuetype"><img alt="BUG" /></td>
                          <td class="issuekey"><a class="issue-link" data-issue-key="{issue_key}" href="/browse/{issue_key}">{issue_key}</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="{issue_key}" href="/browse/{issue_key}">{summary}</a></p></td>
                          <td class="customfield_10762"><span>客户A</span></td>
                          <td class="customfield_10702">P1</td>
                          <td class="status"><span>缺陷受理</span></td>
                          <td class="creator"><a>张三</a></td>
                          <td class="customfield_10222"><a>测试甲</a></td>
                          <td class="customfield_10731"><a>责任人甲</a></td>
                          <td class="customfield_11000"><span>平台组</span></td>
                          <td class="created">2026-04-18</td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }

    def test_execute_jira_config_recreates_current_version_records(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15发版（8.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )
        self.assertEqual(config.version, '26-04.15')
        original = JiraBugRecord.objects.create(
            config=config,
            version=config.version,
            issue_id='legacy-1',
            issue_key='SYSWIN-1',
            issue_type='BUG',
            summary='旧数据',
            row_index=1,
        )

        class MockResponse:
            def __init__(self, payload):
                self.status_code = 200
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        with patch('apps.quality_analysis.jira_services.requests.request', return_value=MockResponse(self._build_payload())):
            result = execute_jira_config(config)

        refreshed = JiraBugRecord.objects.get(version=config.version, issue_key='SYSWIN-1')
        self.assertEqual(result['cleared_count'], 1)
        self.assertEqual(result['synced_count'], 1)
        self.assertNotEqual(refreshed.id, original.id)
        self.assertEqual(refreshed.version, '26-04.15')
        self.assertEqual(refreshed.summary, '线上问题一')

    def test_execute_jira_requirement_config_enriches_documented_requirement_fields(self):
        config = JiraRequirementInterfaceConfig.objects.create(
            version='26-05.15',
            name='requirement-config',
            request_url='http://example.com/rest/issueNav/1/issueTable',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=15943&layoutKey=list-view',
        )

        issue_table_payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-REQ-1'],
                'issueIds': ['201'],
                'columns': [
                    {'id': 'issuekey', 'label': '需求编号'},
                    {'id': 'summary', 'label': '需求标题'},
                    {'id': 'status', 'label': '状态'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow201" rel="201" data-issuekey="SYSWIN-REQ-1" class="issuerow">
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-REQ-1" href="/browse/SYSWIN-REQ-1">SYSWIN-REQ-1</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-REQ-1" href="/browse/SYSWIN-REQ-1">需求一</a></p></td>
                          <td class="status"><span>功能研发中</span></td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }
        search_payload = {
            'names': {
                'issuetype': '任务类型',
                'summary': '需求标题',
                'status': '状态',
                'creator': '创建人',
                'assignee': '经办人',
                'created': '创建日期',
                'components': '模块',
                'customfield_10762': '客户或项目名称',
                'customfield_10702': '任务优先级',
                'customfield_10222': '测试人员',
                'customfield_11100': '版本内研发优先级别',
                'customfield_10761': '测试预估工时',
                'customfield_10738': 'PM进度',
                'customfield_10100': '必须发版',
                'customfield_10737': 'PM',
                'customfield_11000': '组别',
                'customfield_10743': '前端',
                'customfield_10523': '前端开始日期',
                'customfield_11017': '前端结束日期',
                'customfield_10741': '后端',
                'customfield_10522': '后端开始日期',
                'customfield_11019': '后端结束日期',
                'customfield_10014': '预计提测日期',
                'customfield_11018': '提测时间',
                'customfield_10765': '整体进度|延期原因',
                'customfield_10015': '用例预估完成时间',
                'customfield_11020': '测试进展',
                'customfield_10746': '测试进度',
                'customfield_10602': '前端是否完成',
                'customfield_10749': '前端预估工时',
                'customfield_10603': '后端是否完成',
                'customfield_10748': '后端预估工时',
            },
            'issues': [
                {
                    'id': '201',
                    'key': 'SYSWIN-REQ-1',
                    'fields': {
                        'issuetype': {'name': '任务'},
                        'summary': '需求一',
                        'status': {'name': '功能研发中'},
                        'creator': {'displayName': '张三'},
                        'assignee': {'displayName': '李四'},
                        'created': '2026-04-24T14:15:16.000+0800',
                        'components': [{'name': '收费管理'}],
                        'customfield_10762': '物业通',
                        'customfield_10702': {'value': 'P0'},
                        'customfield_10222': {'displayName': '测试甲'},
                        'customfield_11100': 'P1',
                        'customfield_10761': '3',
                        'customfield_10738': '80%',
                        'customfield_10100': True,
                        'customfield_10737': {'displayName': '王产品'},
                        'customfield_11000': '平台组',
                        'customfield_10743': {'displayName': '前端甲'},
                        'customfield_10523': '2026-05-01',
                        'customfield_11017': '2026-05-08',
                        'customfield_10741': {'displayName': '后端乙'},
                        'customfield_10522': '2026-04-30',
                        'customfield_11019': '2026-05-09',
                        'customfield_10014': '2026-05-10',
                        'customfield_11018': '2026-05-10T09:30:00.000+0800',
                        'customfield_10765': '联调延后，等待接口',
                        'customfield_10015': '2026-05-07',
                        'customfield_11020': '联调中',
                        'customfield_10746': '80%',
                        'customfield_10602': True,
                        'customfield_10749': '2',
                        'customfield_10603': False,
                        'customfield_10748': '5',
                    },
                }
            ],
        }

        class MockResponse:
            def __init__(self, payload, status_code=200):
                self.status_code = status_code
                self._payload = payload
                self.text = json.dumps(payload, ensure_ascii=False)
                self.headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def mocked_request(method, url, **kwargs):
            if url.endswith('/rest/issueNav/1/issueTable'):
                return MockResponse(issue_table_payload)
            if url.endswith('/rest/api/2/search'):
                self.assertEqual(kwargs.get('json', {}).get('fields')[0], 'issuetype')
                return MockResponse(search_payload)
            raise AssertionError(f'unexpected request url: {url}')

        with patch('apps.quality_analysis.jira_services.requests.request', side_effect=mocked_request):
            result = execute_jira_requirement_config(config)

        self.assertEqual(result['synced_count'], 1)
        record = JiraRequirementRecord.objects.get(version='26-05.15', issue_key='SYSWIN-REQ-1')
        self.assertEqual(record.customer_name, '物业通')
        self.assertEqual(record.priority, 'P1')
        self.assertEqual(record.tester, '测试甲')
        self.assertEqual(record.handler, '')
        self.assertEqual(record.group_name, '平台组')
        self.assertEqual(record.frontend_developer, '前端甲')
        self.assertEqual(record.backend_developer, '后端乙')
        self.assertEqual(record.module, '收费管理')
        self.assertEqual(record.raw_fields['customfield_10702'], 'P0')
        self.assertEqual(record.raw_fields['customfield_11100'], 'P1')
        self.assertEqual(record.raw_fields['customfield_10100'], '是')
        self.assertEqual(record.raw_fields['customfield_10603'], '否')
        self.assertEqual(record.raw_fields['created'], '2026-04-24')
        self.assertEqual(record.raw_fields['customfield_11018'], '2026-05-10 09:30')
        self.assertNotIn('assignee', record.raw_fields)
        self.assertEqual(record.raw_fields[RAW_FIELD_LABELS_META_KEY]['customfield_10748'], '后端预估工时')

    def test_execute_jira_requirement_config_does_not_preserve_documented_jira_fields(self):
        config = JiraRequirementInterfaceConfig.objects.create(
            version='26-05.16',
            name='requirement-config-strict-preserve',
            request_url='http://example.com/rest/issueNav/1/issueTable',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=15943&layoutKey=list-view',
        )
        JiraRequirementRecord.objects.create(
            config=config,
            version='26-05.16',
            issue_key='SYSWIN-REQ-PRESERVE-1',
            summary='旧需求标题',
            frontend_developer='旧前端',
            backend_developer='旧后端',
            description='旧描述',
            related_mindmaps=[{'id': 1, 'name': '脑图A'}],
        )

        issue_table_payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-REQ-PRESERVE-1'],
                'issueIds': ['402'],
                'columns': [
                    {'id': 'issuekey', 'label': '需求编号'},
                    {'id': 'summary', 'label': '需求标题'},
                    {'id': 'customfield_10743', 'label': '前端'},
                    {'id': 'customfield_10741', 'label': '后端'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow402" rel="402" data-issuekey="SYSWIN-REQ-PRESERVE-1" class="issuerow">
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-REQ-PRESERVE-1" href="/browse/SYSWIN-REQ-PRESERVE-1">SYSWIN-REQ-PRESERVE-1</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-REQ-PRESERVE-1" href="/browse/SYSWIN-REQ-PRESERVE-1">新需求标题</a></p></td>
                          <td class="customfield_10743"><a>新前端</a></td>
                          <td class="customfield_10741"><a>新后端</a></td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }
        search_payload = {
            'names': {
                'issuekey': '需求编号',
                'summary': '需求标题',
                'customfield_10743': '前端',
                'customfield_10741': '后端',
            },
            'issues': [
                {
                    'key': 'SYSWIN-REQ-PRESERVE-1',
                    'fields': {
                        'summary': '新需求标题',
                        'customfield_10743': '新前端',
                        'customfield_10741': '新后端',
                    },
                }
            ],
        }

        class MockResponse:
            def __init__(self, payload):
                self.status_code = 200
                self._payload = payload
                self.text = json.dumps(payload, ensure_ascii=False)
                self.headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def mocked_request(method, url, **kwargs):
            if url.endswith('/rest/issueNav/1/issueTable'):
                return MockResponse(issue_table_payload)
            if url.endswith('/rest/api/2/search'):
                return MockResponse(search_payload)
            raise AssertionError(f'unexpected request url: {url}')

        with patch('apps.quality_analysis.jira_services.requests.request', side_effect=mocked_request):
            execute_jira_requirement_config(config)

        record = JiraRequirementRecord.objects.get(version='26-05.16', issue_key='SYSWIN-REQ-PRESERVE-1')
        self.assertEqual(record.summary, '新需求标题')
        self.assertEqual(record.frontend_developer, '新前端')
        self.assertEqual(record.backend_developer, '新后端')
        self.assertEqual(record.description, '')
        self.assertEqual(record.related_mindmaps, [{'id': 1, 'name': '脑图A'}])

    def test_execute_jira_config_enriches_documented_bug_fields(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-05.15',
            name='bug-config',
            request_url='http://example.com/rest/issueNav/1/issueTable',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=16128&layoutKey=list-view',
        )

        issue_table_payload = {
            'issueTable': {
                'total': 1,
                'displayed': 1,
                'startIndex': 0,
                'end': 1,
                'page': 0,
                'pageSize': 200,
                'issueKeys': ['SYSWIN-BUG-1'],
                'issueIds': ['301'],
                'columns': [
                    {'id': 'issuekey', 'label': '缺陷编号'},
                    {'id': 'summary', 'label': '缺陷标题'},
                    {'id': 'status', 'label': '状态'},
                ],
                'table': '''
                    <table>
                      <tbody>
                        <tr id="issuerow301" rel="301" data-issuekey="SYSWIN-BUG-1" class="issuerow">
                          <td class="issuekey"><a class="issue-link" data-issue-key="SYSWIN-BUG-1" href="/browse/SYSWIN-BUG-1">SYSWIN-BUG-1</a></td>
                          <td class="summary"><p><a class="issue-link" data-issue-key="SYSWIN-BUG-1" href="/browse/SYSWIN-BUG-1">线上问题一</a></p></td>
                          <td class="status"><span>缺陷受理</span></td>
                        </tr>
                      </tbody>
                    </table>
                ''',
            }
        }
        search_payload = {
            'names': {
                'issuetype': '任务类型',
                'issuekey': '缺陷编号',
                'summary': '缺陷标题',
                'customfield_10762': '客户或项目名称',
                'customfield_10702': '任务优先级',
                'customfield_10754': 'BUG处理反馈',
                'customfield_11101': 'BUG定性分类',
                'customfield_11102': 'BUG产生根因',
                'customfield_11103': 'BUG直接责任岗位',
                'components': '模块',
                'status': '状态',
                'creator': '创建人',
                'customfield_10222': '测试人员',
                'customfield_11100': '版本内研发优先级别',
                'customfield_10743': '前端',
                'customfield_10741': '后端',
                'customfield_10746': '测试进度',
                'customfield_10761': '测试预估工时',
                'customfield_10738': 'PM进度',
                'customfield_10100': '必须发版',
                'customfield_10737': 'PM',
                'customfield_11000': '组别',
                'customfield_10523': '前端开始日期',
                'customfield_11017': '前端结束日期',
                'customfield_10522': '后端开始日期',
                'customfield_11019': '后端结束日期',
                'created': '创建日期',
                'customfield_10014': '预计提测日期',
                'customfield_11018': '提测时间',
                'customfield_10765': '整体进度|延期原因',
                'customfield_10015': '用例预估完成时间',
                'customfield_11020': '测试进展',
                'customfield_10749': '前端预估工时',
                'customfield_10748': '后端预估工时',
                'customfield_10731': 'BUG责任人',
                'customfield_10019': 'BUG重新打开次数',
            },
            'issues': [
                {
                    'key': 'SYSWIN-BUG-1',
                    'fields': {
                        'issuetype': {'name': 'BUG'},
                        'summary': '线上问题一',
                        'customfield_10762': '物业通',
                        'customfield_10702': 'P1 重要',
                        'customfield_10754': '已修复待回归',
                        'customfield_11101': {'value': '功能缺陷'},
                        'customfield_11102': '代码逻辑错误',
                        'customfield_11103': {'value': '后端'},
                        'components': [{'name': '收费管理'}],
                        'status': {'name': '缺陷受理'},
                        'creator': {'displayName': '张三'},
                        'customfield_10222': {'displayName': '测试甲'},
                        'customfield_11100': {'value': '高'},
                        'customfield_10743': '前端乙',
                        'customfield_10741': '后端丙',
                        'customfield_10746': '联调中',
                        'customfield_10761': '2h',
                        'customfield_10738': '排期中',
                        'customfield_10100': True,
                        'customfield_10737': '产品甲',
                        'customfield_11000': '平台组',
                        'customfield_10523': '2026-05-01T00:00:00.000+0800',
                        'customfield_11017': '2026-05-02T00:00:00.000+0800',
                        'customfield_10522': '2026-05-03T00:00:00.000+0800',
                        'customfield_11019': '2026-05-04T00:00:00.000+0800',
                        'created': '2026-05-05T10:20:30.000+0800',
                        'customfield_10014': '2026-05-06T00:00:00.000+0800',
                        'customfield_11018': '2026-05-07T11:22:33.000+0800',
                        'customfield_10765': '整体正常',
                        'customfield_10015': '2026-05-08T00:00:00.000+0800',
                        'customfield_11020': '回归中',
                        'customfield_10749': '1.5h',
                        'customfield_10748': '2h',
                        'customfield_10731': '责任人甲',
                        'customfield_10019': 3,
                    },
                }
            ],
        }

        request_calls = []

        class MockResponse:
            def __init__(self, payload, status_code=200):
                self.status_code = status_code
                self._payload = payload
                self.text = json.dumps(payload, ensure_ascii=False)
                self.headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def mocked_request(method, url, **kwargs):
            request_calls.append({'method': method, 'url': url, **kwargs})
            if url.endswith('/rest/issueNav/1/issueTable'):
                return MockResponse(issue_table_payload)
            if url.endswith('/rest/api/2/search'):
                self.assertEqual(kwargs.get('json', {}).get('fields')[0], 'issuetype')
                return MockResponse(search_payload)
            raise AssertionError(f'unexpected request url: {url}')

        with patch('apps.quality_analysis.jira_services.requests.request', side_effect=mocked_request):
            result = execute_jira_config(config)

        self.assertEqual(result['synced_count'], 1)
        self.assertEqual(len(request_calls), 2)
        self.assertTrue(request_calls[1]['url'].endswith('/rest/api/2/search'))
        record = JiraBugRecord.objects.get(version='26-05.15', issue_key='SYSWIN-BUG-1')
        self.assertEqual(record.customer_name, '物业通')
        self.assertEqual(record.tester, '测试甲')
        self.assertEqual(record.handler, '责任人甲')
        self.assertEqual(record.module, '收费管理')
        self.assertEqual(record.raw_fields['customfield_10731'], '责任人甲')
        self.assertEqual(record.raw_fields['customfield_11102'], '代码逻辑错误')
        self.assertEqual(record.raw_fields['customfield_10741'], '后端丙')
        self.assertEqual(record.raw_fields['customfield_10222'], '测试甲')
        self.assertEqual(record.raw_fields['customfield_10019'], '3')
        self.assertEqual(record.raw_fields['customfield_10100'], '是')
        self.assertEqual(record.raw_fields['created'], '2026-05-05')
        self.assertEqual(record.raw_fields['customfield_11018'], '2026-05-07 11:22')
        self.assertEqual(record.raw_fields[RAW_FIELD_LABELS_META_KEY]['customfield_11102'], 'BUG产生根因')


class JiraRecordApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quality-admin', password='secret123')
        self.client.force_authenticate(self.user)
        Group.objects.create(name='测试组')

    @staticmethod
    def paginated_results(response):
        data = response.data
        return data.get('results', data) if isinstance(data, dict) else data

    def test_list_bug_configs_can_filter_by_normalized_version(self):
        JiraInterfaceConfig.objects.create(
            version='26-04.15发版（8.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira-bug',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )
        JiraInterfaceConfig.objects.create(
            version='26-04.16发版（8.2.1）',
            name='JIRA线上BUG接口-次日',
            request_url='http://example.com/jira-bug-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )

        response = self.client.get(reverse('jira-interface-config-list'), {'version': '26-04.15发版（8.2.0）'})

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['version'], '26-04.15')
        self.assertEqual(response.data[0]['request_url'], 'http://example.com/jira-bug')

    def test_list_requirement_configs_can_filter_by_normalized_version(self):
        JiraRequirementInterfaceConfig.objects.update_or_create(
            version='26-04.15',
            defaults={
                'name': 'JIRA需求接口',
                'request_url': 'http://example.com/jira-req',
                'request_method': 'POST',
                'request_headers': {},
                'request_body': 'startIndex=0&layoutKey=list-view',
            },
        )
        JiraRequirementInterfaceConfig.objects.create(
            version='26-04.16发版（8.2.1）',
            name='JIRA需求接口-次日',
            request_url='http://example.com/jira-req-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )

        response = self.client.get(reverse('jira-requirement-interface-config-list'), {'version': '26-04.15'})

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['version'], '26-04.15')
        self.assertEqual(response.data[0]['request_url'], 'http://example.com/jira-req')

    def test_combined_config_endpoint_returns_bug_and_requirement_rows(self):
        JiraInterfaceConfig.objects.create(
            version='26-04.15发版（8.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira-bug',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )
        JiraInterfaceConfig.objects.create(
            version='26-04.16发版（8.2.1）',
            name='JIRA线上BUG接口-次日',
            request_url='http://example.com/jira-bug-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )
        JiraRequirementInterfaceConfig.objects.update_or_create(
            version='26-04.15',
            defaults={
                'name': 'JIRA需求接口',
                'request_url': 'http://example.com/jira-req',
                'request_method': 'POST',
                'request_headers': {},
                'request_body': 'startIndex=0&layoutKey=list-view',
            },
        )
        JiraRequirementInterfaceConfig.objects.create(
            version='26-04.16发版（8.2.1）',
            name='JIRA需求接口-次日',
            request_url='http://example.com/jira-req-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )

        response = self.client.get(reverse('jira-interface-config-combined'), {'version': '26-04.15'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({item['interface_type'] for item in response.data}, {'bug', 'requirement'})
        self.assertEqual({item['version'] for item in response.data}, {'26-04.15'})
    """

    def test_refresh_bug_records_executes_matching_version_config(self):
        JiraInterfaceConfig.objects.all().delete()
        matched_config = JiraInterfaceConfig.objects.create(
            version='26-04.15发版（2.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira-bug',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        JiraInterfaceConfig.objects.create(
            version='26-04.16发版（2.2.1）',
            name='JIRA线上BUG接口-次日',
            request_url='http://example.com/jira-bug-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )

        with patch(
            'apps.quality_analysis.views.JiraBugRecordViewSet.config_executor',
            return_value={'message': 'bug sync ok', 'synced_count': 12, 'cleared_count': 0, 'status_code': 200},
        ) as mocked_executor:
            response = self.client.post(f"{reverse('jira-bug-record-refresh')}?version=26-04.15")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version_count'], 1)
        self.assertEqual(response.data['synced_count'], 12)
        self.assertEqual(response.data['results'][0]['config_id'], matched_config.id)
        mocked_executor.assert_called_once()
        self.assertEqual(mocked_executor.call_args.args[0].id, matched_config.id)


class _JiraRequirementRoleAssociationSerializerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quality-role-admin', password='secret123')
        self.client.force_authenticate(self.user)
        Group.objects.create(name='测试组')
        self.pm_user = user_model.objects.create_user(
            username='pm.zhang',
            password='secret123',
            first_name='\u5f20\u4ea7\u54c1',
        )
        self.tester_user = user_model.objects.create_user(
            username='tester.li',
            password='secret123',
            first_name='\u674e\u6d4b\u8bd5',
        )
        self.frontend_user = user_model.objects.create_user(
            username='frontend.wang',
            password='secret123',
            first_name='\u738b\u524d\u7aef',
        )
        self.backend_user = user_model.objects.create_user(
            username='backend.zhao',
            password='secret123',
            first_name='\u8d75\u540e\u7aef',
        )

        role_members = {
            '\u4ea7\u54c1': [self.pm_user],
            '\u6d4b\u8bd5': [self.tester_user],
            '\u524d\u7aef': [self.frontend_user],
            '\u540e\u7aef': [self.backend_user],
        }
        for role_name, members in role_members.items():
            role = Role.objects.create(name=role_name)
            role.members.set(members)

    def test_requirement_serializer_maps_role_bound_people_fields(self):
        record = JiraRequirementRecord(
            version='26-05.15',
            issue_key='SYSWIN-REQ-ROLE-1',
            summary='角色关联验证',
            tester='tester.li',
            frontend_developer='frontend.wang',
            backend_developer='backend.zhao',
            raw_fields={
                'customfield_10737': '\u5f20\u4ea7\u54c1',
                'customfield_10222': 'tester.li',
                'customfield_10743': 'frontend.wang',
                'customfield_10741': 'backend.zhao',
            },
        )

        data = JiraRequirementRecordSerializer(record).data

        self.assertEqual(data['mapped_fields']['product_manager'], '\u5f20\u4ea7\u54c1')
        self.assertEqual(data['mapped_fields']['tester'], '\u674e\u6d4b\u8bd5')
        self.assertEqual(data['mapped_fields']['frontend_developer'], '\u738b\u524d\u7aef')
        self.assertEqual(data['mapped_fields']['backend_developer'], '\u8d75\u540e\u7aef')
        self.assertEqual(data['mapped_fields']['product_manager_members'][0]['id'], self.pm_user.id)
        self.assertEqual(data['mapped_fields']['tester_members'][0]['id'], self.tester_user.id)
        self.assertEqual(data['mapped_fields']['frontend_developer_members'][0]['id'], self.frontend_user.id)
        self.assertEqual(data['mapped_fields']['backend_developer_members'][0]['id'], self.backend_user.id)

    def test_refresh_requirement_records_executes_all_active_configs_without_version_filter(self):
        JiraRequirementInterfaceConfig.objects.all().delete()
        first_config = JiraRequirementInterfaceConfig.objects.create(
            version='26-04.15新增需求.2.0版',
            name='JIRA需求接口-1',
            request_url='http://example.com/jira-req-1',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        second_config = JiraRequirementInterfaceConfig.objects.create(
            version='26-04.16新增需求.2.1版',
            name='JIRA需求接口-2',
            request_url='http://example.com/jira-req-2',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        JiraRequirementInterfaceConfig.objects.create(
            version='26-04.17新增需求.2.2版',
            name='JIRA需求接口-inactive',
            request_url='http://example.com/jira-req-3',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=False,
        )

        called_versions = []

        def fake_requirement_executor(config):
            called_versions.append(config.version)
            if config.version == '27-04.15':
                return {'message': 'requirement sync 1', 'synced_count': 5, 'cleared_count': 0, 'status_code': 200}
            if config.version == '27-04.16':
                return {'message': 'requirement sync 2', 'synced_count': 7, 'cleared_count': 0, 'status_code': 200}
            raise AssertionError(f'unexpected version: {config.version}')

        from . import views as quality_analysis_views

        original_executor = quality_analysis_views.JiraRequirementRecordViewSet.config_executor
        quality_analysis_views.JiraRequirementRecordViewSet.config_executor = staticmethod(fake_requirement_executor)
        try:
            response = self.client.post(reverse('jira-requirement-record-refresh'))
        finally:
            quality_analysis_views.JiraRequirementRecordViewSet.config_executor = original_executor

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['version_count'], 2)
        self.assertEqual(response.data['synced_count'], 12)
        self.assertEqual([item['config_id'] for item in response.data['results']], [first_config.id, second_config.id])
        self.assertEqual(called_versions, ['27-04.15', '27-04.16'])

    """

    def test_refresh_bug_records_executes_matching_version_config(self):
        JiraInterfaceConfig.objects.all().delete()
        matched_config = JiraInterfaceConfig.objects.create(
            version='26-04.15',
            name='bug-config-current',
            request_url='http://example.com/jira-bug',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        JiraInterfaceConfig.objects.create(
            version='26-04.16',
            name='bug-config-next',
            request_url='http://example.com/jira-bug-next',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )

        with patch(
            'apps.quality_analysis.views.JiraBugRecordViewSet.config_executor',
            return_value={'message': 'bug sync ok', 'synced_count': 12, 'cleared_count': 0, 'status_code': 200},
        ) as mocked_executor:
            response = self.client.post(f"{reverse('jira-bug-record-refresh')}?version=26-04.15")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version_count'], 1)
        self.assertEqual(response.data['synced_count'], 12)
        self.assertEqual(response.data['results'][0]['config_id'], matched_config.id)
        mocked_executor.assert_called_once()
        self.assertEqual(mocked_executor.call_args.args[0].id, matched_config.id)

    def test_refresh_requirement_records_executes_all_active_configs_without_version_filter(self):
        JiraRequirementInterfaceConfig.objects.all().delete()
        first_config = JiraRequirementInterfaceConfig.objects.create(
            version='27-04.15',
            name='requirement-config-1',
            request_url='http://example.com/jira-req-1',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        second_config = JiraRequirementInterfaceConfig.objects.create(
            version='27-04.16',
            name='requirement-config-2',
            request_url='http://example.com/jira-req-2',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=True,
        )
        JiraRequirementInterfaceConfig.objects.create(
            version='27-04.17',
            name='requirement-config-inactive',
            request_url='http://example.com/jira-req-3',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
            is_active=False,
        )

        called_versions = []

        def fake_requirement_executor(config):
            called_versions.append(config.version)
            if config.version == '27-04.15':
                return {'message': 'requirement sync 1', 'synced_count': 5, 'cleared_count': 0, 'status_code': 200}
            if config.version == '27-04.16':
                return {'message': 'requirement sync 2', 'synced_count': 7, 'cleared_count': 0, 'status_code': 200}
            raise AssertionError(f'unexpected version: {config.version}')

        from . import views as quality_analysis_views

        original_executor = quality_analysis_views.JiraRequirementRecordViewSet.config_executor
        quality_analysis_views.JiraRequirementRecordViewSet.config_executor = staticmethod(fake_requirement_executor)
        try:
            response = self.client.post(reverse('jira-requirement-record-refresh'))
        finally:
            quality_analysis_views.JiraRequirementRecordViewSet.config_executor = original_executor

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['version_count'], 2)
        self.assertEqual(response.data['synced_count'], 12)
        self.assertEqual([item['config_id'] for item in response.data['results']], [first_config.id, second_config.id])
        self.assertEqual(called_versions, ['27-04.15', '27-04.16'])

    def test_requirement_records_support_no_module_tree_filter(self):
        JiraRequirementRecord.objects.create(version='26-04.15', issue_key='SYSWIN-REQ-1', module='', row_index=1)
        JiraRequirementRecord.objects.create(version='26-04.15', issue_key='SYSWIN-REQ-2', module='收费管理', row_index=2)

        response = self.client.get(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.15',
                'module_names': json.dumps(['无模块'], ensure_ascii=False),
            },
        )

        self.assertEqual(response.status_code, 200)
        records = self.paginated_results(response)
        self.assertEqual([item['issue_key'] for item in records], ['SYSWIN-REQ-1'])
        self.assertEqual(records[0]['module'], '')

    def test_requirement_records_keyword_matches_issue_key_and_summary(self):
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-KEY-1',
            summary='Parking payment optimization',
            row_index=1,
        )
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-OTHER-1',
            summary='Inventory module update',
            row_index=2,
        )

        summary_response = self.client.get(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.15',
                'keyword': 'payment',
            },
        )
        key_response = self.client.get(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.15',
                'keyword': 'REQ-KEY',
            },
        )

        self.assertEqual(summary_response.status_code, 200, summary_response.data)
        self.assertEqual(key_response.status_code, 200, key_response.data)
        self.assertEqual([item['issue_key'] for item in self.paginated_results(summary_response)], ['SYSWIN-REQ-KEY-1'])
        self.assertEqual([item['issue_key'] for item in self.paginated_results(key_response)], ['SYSWIN-REQ-KEY-1'])

    def test_requirement_records_accept_search_alias_for_defect_form_remote_select(self):
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-ALIAS-1',
            summary='Lease billing flow',
            row_index=1,
        )
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-ALIAS-2',
            summary='Access control flow',
            row_index=2,
        )

        for param_name in ('search', 'q', 'jira_keyword'):
            response = self.client.get(
                reverse('jira-requirement-record-list'),
                {
                    'version': '26-04.15',
                    param_name: 'billing',
                },
            )

            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual([item['issue_key'] for item in self.paginated_results(response)], ['SYSWIN-REQ-ALIAS-1'])

    def test_requirement_records_include_relation_counts(self):
        project = Project.objects.create(name='Relation Count Project', owner=self.user)
        version = Version.objects.create(name='26-04.15', created_by=self.user)
        version.projects.add(project)
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-1',
            summary='关联需求',
            related_mindmaps=[{'mindmap_id': 1, 'mindmap_name': '脑图A'}],
            row_index=1,
        )
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-2',
            summary='无关联需求',
            row_index=2,
        )
        Defect.objects.create(
            project=project,
            version=version,
            title='版本缺陷',
            description='版本缺陷描述',
            requirement_id='SYSWIN-REQ-1',
            created_by=self.user,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-1',
            related_requirements=[{'issue_key': 'SYSWIN-REQ-1', 'summary': '关联需求', 'version': '26-04.15'}],
            row_index=1,
        )

        response = self.client.get(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.15',
                'project_id': project.id,
                'manual_version_id': version.id,
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        records_by_key = {item['issue_key']: item for item in self.paginated_results(response)}
        self.assertEqual(records_by_key['SYSWIN-REQ-1']['related_mindmap_count'], 1)
        self.assertEqual(records_by_key['SYSWIN-REQ-1']['version_defect_count'], 1)
        self.assertEqual(records_by_key['SYSWIN-REQ-1']['bug_record_count'], 1)
        self.assertEqual(records_by_key['SYSWIN-REQ-2']['related_mindmap_count'], 0)
        self.assertEqual(records_by_key['SYSWIN-REQ-2']['version_defect_count'], 0)
        self.assertEqual(records_by_key['SYSWIN-REQ-2']['bug_record_count'], 0)

    def test_bug_record_keyword_matches_related_requirement(self):
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-1',
            summary='线上缺陷',
            related_requirements=[{'issue_key': 'SYSWIN-REQ-1', 'summary': '关联需求'}],
            row_index=1,
        )
        JiraBugRecord.objects.create(version='26-04.15', issue_key='SYSWIN-BUG-2', summary='其他缺陷', row_index=2)

        response = self.client.get(
            reverse('jira-bug-record-list'),
            {
                'version': '26-04.15',
                'keyword': 'SYSWIN-REQ-1',
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item['issue_key'] for item in self.paginated_results(response)], ['SYSWIN-BUG-1'])

    def test_bug_records_are_paginated(self):
        synced_at = timezone.now()
        for index in range(3):
            JiraBugRecord.objects.create(
                version='26-04.15',
                issue_key=f'SYSWIN-BUG-PAGE-{index + 1}',
                synced_at=synced_at,
                row_index=index + 1,
            )

        response = self.client.get(
            reverse('jira-bug-record-list'),
            {'version': '26-04.15', 'page': 2, 'page_size': 2},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual([item['issue_key'] for item in response.data['results']], ['SYSWIN-BUG-PAGE-3'])

    def test_requirement_records_are_paginated(self):
        synced_at = timezone.now()
        for index in range(3):
            JiraRequirementRecord.objects.create(
                version='26-04.15',
                issue_key=f'SYSWIN-REQ-PAGE-{index + 1}',
                synced_at=synced_at,
                row_index=index + 1,
            )

        response = self.client.get(
            reverse('jira-requirement-record-list'),
            {'version': '26-04.15', 'page': 2, 'page_size': 2},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual([item['issue_key'] for item in response.data['results']], ['SYSWIN-REQ-PAGE-3'])

    def test_clear_selected_bug_records(self):
        first = JiraBugRecord.objects.create(version='26-04.15发版（8.2.0）', issue_key='SYSWIN-1', row_index=1)
        second = JiraBugRecord.objects.create(version='26-04.15发版（8.2.0）', issue_key='SYSWIN-2', row_index=2)

        response = self.client.post(
            reverse('jira-bug-record-clear-selected'),
            {'ids': [first.id, second.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cleared_count'], 2)
        self.assertFalse(JiraBugRecord.objects.filter(id__in=[first.id, second.id]).exists())

    def test_clear_selected_requirement_records(self):
        first = JiraRequirementRecord.objects.create(version='26-04.15发版（8.2.0）', issue_key='SYSWIN-REQ-1', row_index=1)
        second = JiraRequirementRecord.objects.create(version='26-04.15发版（8.2.0）', issue_key='SYSWIN-REQ-2', row_index=2)

        response = self.client.post(
            reverse('jira-requirement-record-clear-selected'),
            {'ids': [first.id, second.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cleared_count'], 2)
        self.assertFalse(JiraRequirementRecord.objects.filter(id__in=[first.id, second.id]).exists())

    def test_create_requirement_record(self):
        response = self.client.post(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.21发版（8.2.2）',
                'issue_key': 'REQ-1001',
                'issue_type': '功能需求',
                'summary': '支持版本需求新增',
                'module': '手工用例',
                'priority': 'P1',
                'status': '新建',
                'creator': '产品经理A',
                'handler': '开发A',
                'tester': '测试A',
                'group_name': '测试组',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        created = JiraRequirementRecord.objects.get(issue_key='REQ-1001')
        self.assertEqual(created.version, '26-04.21')
        self.assertEqual(created.summary, '支持版本需求新增')
        self.assertEqual(created.row_index, 1)

    def test_create_requirement_record_rejects_unknown_group(self):
        response = self.client.post(
            reverse('jira-requirement-record-list'),
            {
                'version': '26-04.21发版（2.2.2）',
                'issue_key': 'REQ-1009',
                'issue_type': '功能需求',
                'summary': '缁勫埆鏍￠獙',
                'group_name': '不存在的组别',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('group_name', response.data)

    def test_update_requirement_record(self):
        record = JiraRequirementRecord.objects.create(
            version='26-04.21',
            issue_key='REQ-1002',
            issue_type='功能需求',
            summary='旧标题',
            row_index=1,
        )

        response = self.client.patch(
            reverse('jira-requirement-record-detail', args=[record.id]),
            {
                'summary': '新标题',
                'status': '处理中',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.summary, '新标题')
        self.assertEqual(record.status, '处理中')

    def test_delete_requirement_record(self):
        record = JiraRequirementRecord.objects.create(version='26-04.21', issue_key='REQ-1003', row_index=1)

        response = self.client.delete(reverse('jira-requirement-record-detail', args=[record.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(JiraRequirementRecord.objects.filter(id=record.id).exists())

    def test_report_jira_versions_returns_merged_versions(self):
        JiraInterfaceConfig.objects.create(
            version='26-04.15发版（8.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&layoutKey=list-view',
        )
        JiraRequirementRecord.objects.create(version='26-04.16发版（8.2.1）', issue_key='SYSWIN-REQ-3', row_index=1)

        response = self.client.get(reverse('quality-report-jira-versions'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['version'] for item in response.data], ['26-04.16', '26-04.15'])

    def test_online_defect_analysis_all_version_excludes_closed_problem_and_role_creators(self):
        user_model = get_user_model()
        product_user = user_model.objects.create_user(
            username='product-owner',
            password='secret123',
            first_name='\u4ea7\u54c1',
            last_name='\u4eba\u5458',
        )
        product_role = Role.objects.create(name='\u4ea7\u54c1')
        product_role.members.add(product_user)

        synced_at = timezone.now()
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-1',
            raw_fields={'customfield_10749': '8', 'customfield_10761': '3'},
            synced_at=synced_at,
            row_index=1,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-1',
            status='\u5df2\u4ea4\u4ed8\u4e0a\u7ebf',
            creator='\u5916\u90e8\u5ba2\u6237',
            raw_fields={'customfield_10749': '2', 'customfield_10761': '1'},
            synced_at=synced_at,
            row_index=1,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-2',
            status='\u5904\u7406\u4e2d',
            creator='\u4ea7\u54c1\u4eba\u5458',
            raw_fields={'customfield_10749': '7', 'customfield_10761': '4'},
            synced_at=synced_at,
            row_index=2,
        )
        JiraBugRecord.objects.create(
            version='26-04.16',
            issue_key='SYSWIN-BUG-3',
            status='\u5df2\u5173\u95ed\u95ee\u9898',
            creator='\u5916\u90e8\u5ba2\u6237',
            raw_fields={'customfield_10749': '5', 'customfield_10761': '2'},
            synced_at=synced_at,
            row_index=3,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-4',
            status='\u4fee\u590d\u5b8c\u6210',
            creator='\u5916\u90e8\u5ba2\u6237',
            raw_fields={'customfield_10749': '4', 'customfield_10761': '2'},
            synced_at=synced_at,
            row_index=4,
        )

        response = self.client.get(reverse('jira-bug-record-online-defect-analysis'), {'version': 'all'})

        self.assertEqual(response.status_code, 200, response.data)
        totals = response.data['totals']
        self.assertEqual(totals['bug_created_count'], 2)
        self.assertEqual(totals['bug_fixed_count'], 1)
        self.assertEqual(totals['bug_fix_rd_estimated_hours'], 6)
        self.assertEqual(totals['bug_regression_test_actual_hours'], 3)
        self.assertEqual(totals['requirement_dev_estimated_hours'], 8)
        self.assertEqual(totals['requirement_test_estimated_hours'], 3)


class JiraRequirementRecordAttachmentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quality-requirement-admin', password='secret123')
        self.client.force_authenticate(self.user)
        Group.objects.create(name='测试组')

    def test_create_update_and_delete_requirement_record_attachments_via_multipart(self):
        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                create_response = self.client.post(
                    reverse('jira-requirement-record-list'),
                    {
                        'version': '26-04.28发版（8.2.2）',
                        'issue_key': 'REQ-ATTACH-1',
                        'summary': '需求附件创建',
                        'description': '<p>附件说明</p>',
                        'group_name': '测试组',
                        'raw_fields': json.dumps({'acceptance_criteria': 'A'}, ensure_ascii=False),
                        'attachments': [
                            SimpleUploadedFile('first.txt', b'first attachment', content_type='text/plain'),
                        ],
                    },
                    format='multipart',
                )

                self.assertEqual(create_response.status_code, 201, create_response.data)
                self.assertEqual(create_response.data['attachments_count'], 1)
                self.assertEqual(len(create_response.data['attachments']), 1)

                record = JiraRequirementRecord.objects.get(issue_key='REQ-ATTACH-1')
                first_attachment = JiraRequirementRecordAttachment.objects.get(requirement=record)
                first_attachment_path = Path(temp_media_root) / first_attachment.file.name
                self.assertTrue(first_attachment_path.exists())

                update_response = self.client.patch(
                    reverse('jira-requirement-record-detail', args=[record.id]),
                    {
                        'description': '<p>附件说明已更新</p>',
                        'retain_attachment_ids': json.dumps([first_attachment.id]),
                        'attachments': [
                            SimpleUploadedFile('second.txt', b'second attachment', content_type='text/plain'),
                        ],
                    },
                    format='multipart',
                )

                self.assertEqual(update_response.status_code, 200, update_response.data)
                self.assertEqual(update_response.data['attachments_count'], 2)

                attachment_ids = {
                    item['name']: item['id']
                    for item in update_response.data['attachments']
                }
                second_attachment = JiraRequirementRecordAttachment.objects.get(id=attachment_ids['second.txt'])
                second_attachment_path = Path(temp_media_root) / second_attachment.file.name
                self.assertTrue(second_attachment_path.exists())

                replace_response = self.client.patch(
                    reverse('jira-requirement-record-detail', args=[record.id]),
                    {
                        'retain_attachment_ids': json.dumps([second_attachment.id]),
                    },
                    format='multipart',
                )

                self.assertEqual(replace_response.status_code, 200, replace_response.data)
                self.assertEqual(replace_response.data['attachments_count'], 1)
                self.assertFalse(JiraRequirementRecordAttachment.objects.filter(id=first_attachment.id).exists())
                self.assertFalse(first_attachment_path.exists())

                delete_response = self.client.delete(reverse('jira-requirement-record-detail', args=[record.id]))

                self.assertEqual(delete_response.status_code, 204, delete_response.data)
                self.assertFalse(JiraRequirementRecord.objects.filter(id=record.id).exists())
                self.assertFalse(second_attachment_path.exists())

    def test_delete_requirement_record_cleans_inline_rich_text_images(self):
        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                relative_path = Path('defect_rich_text_images/2026/04/requirement-inline.png')
                inline_image_path = Path(temp_media_root) / relative_path
                inline_image_path.parent.mkdir(parents=True, exist_ok=True)
                inline_image_path.write_bytes(b'inline image')

                record = JiraRequirementRecord.objects.create(
                    version='26-04.28',
                    issue_key='REQ-RICH-1',
                    summary='富文本图片清理',
                    description=f'<p><img src="/media/{relative_path.as_posix()}"></p>',
                    row_index=1,
                )

                response = self.client.delete(reverse('jira-requirement-record-detail', args=[record.id]))

                self.assertEqual(response.status_code, 204, response.data)
                self.assertFalse(inline_image_path.exists())

    def test_clear_selected_requirement_records_cleans_attachment_files(self):
        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                record = JiraRequirementRecord.objects.create(
                    version='26-04.28',
                    issue_key='REQ-CLEAR-1',
                    summary='批量清空附件',
                    row_index=1,
                )
                attachment = JiraRequirementRecordAttachment.objects.create(
                    requirement=record,
                    name='clear.txt',
                    file=SimpleUploadedFile('clear.txt', b'clear attachment', content_type='text/plain'),
                    uploaded_by=self.user,
                )
                attachment_path = Path(temp_media_root) / attachment.file.name
                self.assertTrue(attachment_path.exists())

                response = self.client.post(
                    reverse('jira-requirement-record-clear-selected'),
                    {'ids': [record.id]},
                    format='json',
                )

                self.assertEqual(response.status_code, 200, response.data)
                self.assertFalse(JiraRequirementRecord.objects.filter(id=record.id).exists())
                self.assertFalse(attachment_path.exists())


class QualityReportLiveApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quality-live-admin', password='secret123')
        self.client.force_authenticate(self.user)

    def test_live_snapshot_returns_generated_report_for_current_version(self):
        with patch(
            'apps.quality_analysis.views.build_version_analysis_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'summary': {
                    'requirements': 6,
                    'dev_self_tests': 5,
                    'cases': 8,
                    'testpoints': 12,
                    'version_defects': 3,
                    'online_defects': 2,
                    'modules': 4,
                    'groups': 2,
                },
                'generated_at': '2026-04-23T19:00:00+08:00',
                'tabs': [],
            },
        ) as mocked_builder:
            response = self.client.get(
                reverse('quality-report-live-snapshot'),
                {
                    'version': '26-04.21发版（2.2.2）',
                    'project_id': 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version'], '26-04.21')
        self.assertEqual(response.data['project_id'], 7)
        self.assertEqual(response.data['project_name'], 'CRM')
        self.assertEqual(response.data['requirements_count'], 6)
        self.assertEqual(response.data['version_defects_count'], 3)
        self.assertEqual(response.data['online_defects_count'], 2)
        self.assertEqual(response.data['total_defects'], 5)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')

    def test_live_version_analysis_returns_current_scope_payload(self):
        with patch(
            'apps.quality_analysis.views.build_version_analysis_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'summary': {'requirements': 1},
                'generated_at': '2026-04-23T19:05:00+08:00',
                'tabs': [{'key': 'overview', 'label': '总览', 'metrics': [], 'blocks': []}],
            },
        ) as mocked_builder:
            response = self.client.get(
                reverse('quality-report-live-version-analysis'),
                {
                    'version': '26-04.21',
                    'project_id': 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['report_id'])
        self.assertEqual(response.data['report_version'], '26-04.21')
        self.assertEqual(response.data['project']['id'], 7)
        self.assertEqual(response.data['summary']['requirements'], 1)
        self.assertEqual(response.data['tabs'][0]['key'], 'overview')
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')

    def test_live_version_analysis_all_versions_excludes_closed_problem_and_role_creators(self):
        user_model = get_user_model()
        frontend_user = user_model.objects.create_user(
            username='frontend-owner',
            password='secret123',
            first_name='\u524d\u7aef',
            last_name='\u4eba\u5458',
        )
        frontend_role = Role.objects.create(name='\u524d\u7aef')
        frontend_role.members.add(frontend_user)

        project = Project.objects.create(name='\u7269\u4e1a\u901a', owner=self.user)
        version_0415 = Version.objects.create(name='26-04.15', created_by=self.user)
        version_0415.projects.add(project)
        version_0416 = Version.objects.create(name='26-04.16', created_by=self.user)
        version_0416.projects.add(project)
        ManualTestCaseMindmap.objects.create(
            project=project,
            version=version_0415,
            author=self.user,
            name='26-04.15\u6d4b\u8bd5\u8111\u56fe',
            mindmap_scope=ManualTestCaseMindmap.SCOPE_TESTING,
            mindmap_data={
                'root': {
                    'id': 'root-0415',
                    'data': {'text': '\u6839\u8282\u70b9', 'nodeType': 'root'},
                    'children': [
                        {
                            'id': 'module-0415',
                            'data': {'text': '\u6a21\u5757A', 'nodeType': 'module'},
                            'children': [
                                {'id': 'tp-0415-1', 'data': {'text': '\u6d4b\u8bd5\u70b91', 'nodeType': 'testpoint'}},
                                {'id': 'tp-0415-2', 'data': {'text': '\u6d4b\u8bd5\u70b92', 'nodeType': 'testpoint'}},
                                {'id': 'case-0415-1', 'data': {'text': '\u6d4b\u8bd5\u7528\u4f8b1', 'nodeType': 'case'}},
                            ],
                        },
                    ],
                },
            },
        )
        ManualTestCaseMindmap.objects.create(
            project=project,
            version=version_0416,
            author=self.user,
            name='26-04.16\u6d4b\u8bd5\u8111\u56fe',
            mindmap_scope=ManualTestCaseMindmap.SCOPE_TESTING,
            mindmap_data={
                'root': {
                    'id': 'root-0416',
                    'data': {'text': '\u6839\u8282\u70b9', 'nodeType': 'root'},
                    'children': [
                        {
                            'id': 'module-0416',
                            'data': {'text': '\u6a21\u5757B', 'nodeType': 'module'},
                            'children': [
                                {'id': 'tp-0416-1', 'data': {'text': '\u6d4b\u8bd5\u70b93', 'nodeType': 'testpoint'}},
                            ],
                        },
                    ],
                },
            },
        )

        synced_at = timezone.now()
        JiraRequirementRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-REQ-1',
            raw_fields={'customfield_10749': '5', 'customfield_10761': '2'},
            synced_at=synced_at,
            row_index=1,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-1',
            status='\u5df2\u4ea4\u4ed8\u4e0a\u7ebf',
            creator='\u5ba2\u6237\u7532',
            raw_fields={
                'customfield_10749': '3',
                'customfield_10761': '1',
                'customfield_11102': '\u9700\u6c42\u7406\u89e3\u504f\u5dee',
            },
            synced_at=synced_at,
            row_index=1,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-2',
            status='\u5904\u7406\u4e2d',
            creator='\u524d\u7aef\u4eba\u5458',
            raw_fields={'customfield_10749': '9', 'customfield_10761': '5'},
            synced_at=synced_at,
            row_index=2,
        )
        JiraBugRecord.objects.create(
            version='26-04.16',
            issue_key='SYSWIN-BUG-3',
            status='\u5df2\u5173\u95ed\u95ee\u9898',
            creator='\u5ba2\u6237\u4e59',
            raw_fields={'customfield_10749': '6', 'customfield_10761': '4'},
            synced_at=synced_at,
            row_index=3,
        )
        JiraBugRecord.objects.create(
            version='26-04.15',
            issue_key='SYSWIN-BUG-4',
            status='\u5df2\u89e3\u51b3',
            creator='\u5ba2\u6237\u7532',
            raw_fields={
                'customfield_10749': '4',
                'customfield_10761': '2',
                '__field_labels': {'rootCauseAlias': 'BUG\u4ea7\u751f\u6839\u56e0'},
                'rootCauseAlias': '\u8bbe\u8ba1\u9057\u6f0f',
            },
            synced_at=synced_at,
            row_index=4,
        )

        response = self.client.get(
            reverse('quality-report-live-version-analysis'),
            {'version': 'all', 'project_id': project.id},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['summary']['online_defects'], 2)
        self.assertEqual(response.data['summary']['testpoints'], 3)

        tabs = {tab['key']: tab for tab in response.data['tabs']}
        self.assertIn('online-defects', tabs)
        self.assertIn('test-assets', tabs)
        metrics = {
            item['label']: item['value']
            for item in tabs['online-defects']['metrics']
        }
        self.assertEqual(metrics['\u7ebf\u4e0a\u7f3a\u9677'], 2)
        self.assertEqual(metrics['\u7d2f\u8ba1\u4fee\u590d\u7f3a\u9677'], 1)
        self.assertEqual(metrics['\u5269\u4f59\u7f3a\u9677'], 1)

        effort_block = next(
            block
            for block in tabs['online-defects']['blocks']
            if block['title'] == '\u8fd112\u4e2a\u6708\u7ebf\u4e0a\u7f3a\u9677\u6295\u5165\u4e0e\u4fee\u590d\u7edf\u8ba1'
        )
        series_by_key = {item['key']: item['data'] for item in effort_block['series']}
        self.assertEqual(sum(series_by_key['bug_created_count']), 2)
        self.assertEqual(sum(series_by_key['bug_fixed_count']), 1)
        self.assertEqual(sum(series_by_key['bug_fix_rd_estimated_hours']), 7)
        self.assertEqual(sum(series_by_key['bug_regression_test_actual_hours']), 3)

        root_cause_block = next(
            block
            for block in tabs['online-defects']['blocks']
            if block['title'] == '\u7ebf\u4e0a\u7f3a\u9677\u6839\u56e0\u5206\u6790\u7edf\u8ba1'
        )
        root_cause_counts = {row['label']: row['count'] for row in root_cause_block['rows']}
        self.assertEqual(root_cause_counts['\u9700\u6c42\u7406\u89e3\u504f\u5dee'], 1)
        self.assertEqual(root_cause_counts['\u8bbe\u8ba1\u9057\u6f0f'], 1)

        testpoint_block = next(
            block
            for block in tabs['test-assets']['blocks']
            if block['title'] == '\u5404\u7248\u672c\u6d4b\u8bd5\u70b9\u7edf\u8ba1'
        )
        testpoint_counts = dict(zip(testpoint_block['categories'], testpoint_block['series'][0]['data']))
        self.assertEqual(testpoint_counts['26-04.15'], 2)
        self.assertEqual(testpoint_counts['26-04.16'], 1)

    def test_live_requirement_overview_returns_generated_scope_payload(self):
        with patch(
            'apps.quality_analysis.views.build_requirement_overview_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'generated_at': '2026-04-23T19:10:00+08:00',
                'requirements': [
                    {
                        'issueKey': 'SYSWIN-REQ-1',
                        'statusState': 'completed',
                    }
                ],
            },
        ) as mocked_builder:
            response = self.client.get(
                reverse('quality-report-live-requirement-overview'),
                {
                    'version': '26-04.21',
                    'project_id': 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['report_version'], '26-04.21')
        self.assertEqual(response.data['project']['id'], 7)
        self.assertEqual(response.data['requirements'][0]['issueKey'], 'SYSWIN-REQ-1')
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')

    def test_live_testing_overview_returns_generated_scope_payload(self):
        with patch(
            'apps.quality_analysis.views.build_testing_overview_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'generated_at': '2026-04-23T19:12:00+08:00',
                'mindmaps': [
                    {
                        'id': 21,
                        'totalCount': 5,
                    }
                ],
            },
        ) as mocked_builder:
            response = self.client.get(
                reverse('quality-report-live-testing-overview'),
                {
                    'version': '26-04.21',
                    'project_id': 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['report_version'], '26-04.21')
        self.assertEqual(response.data['project']['name'], 'CRM')
        self.assertEqual(response.data['mindmaps'][0]['totalCount'], 5)
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')

    def test_live_rd_progress_overview_returns_generated_scope_payload(self):
        with patch(
            'apps.quality_analysis.views.build_rd_progress_overview_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'generated_at': '2026-04-23T19:15:00+08:00',
                'rows': [
                    {
                        'requirement_key': 'SYSWIN-REQ-1',
                        'testpoint_count': {'not_run': 0, 'pass': 1, 'fail': 0, 'block': 0},
                    }
                ],
            },
        ) as mocked_builder:
            response = self.client.get(
                reverse('quality-report-live-rd-progress-overview'),
                {
                    'version': '26-04.21',
                    'project_id': 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['report_version'], '26-04.21')
        self.assertEqual(response.data['project']['id'], 7)
        self.assertEqual(response.data['rows'][0]['requirement_key'], 'SYSWIN-REQ-1')
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')

    def test_live_share_returns_public_token_for_current_scope(self):
        with patch(
            'apps.quality_analysis.views.build_version_analysis_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'summary': {
                    'requirements': 6,
                    'cases': 8,
                    'testpoints': 12,
                    'version_defects': 3,
                    'online_defects': 2,
                    'modules': 4,
                    'groups': 2,
                },
                'generated_at': '2026-04-23T19:00:00+08:00',
                'tabs': [],
            },
        ):
            response = self.client.post(
                reverse('quality-report-live-share'),
                {
                    'version': '26-04.21发版（2.2.2）',
                    'project_id': 7,
                },
                format='json',
            )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['share_token'])

    def test_shared_live_version_analysis_allows_anonymous_access(self):
        with patch(
            'apps.quality_analysis.views.build_version_analysis_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'summary': {
                    'requirements': 6,
                    'cases': 8,
                    'testpoints': 12,
                    'version_defects': 3,
                    'online_defects': 2,
                    'modules': 4,
                    'groups': 2,
                },
                'generated_at': '2026-04-23T19:00:00+08:00',
                'tabs': [],
            },
        ):
            share_response = self.client.post(
                reverse('quality-report-live-share'),
                {
                    'version': '26-04.21',
                    'project_id': 7,
                },
                format='json',
            )

        self.assertEqual(share_response.status_code, 200, share_response.data)
        share_token = share_response.data['share_token']

        anonymous_client = APIClient()
        with patch(
            'apps.quality_analysis.views.build_version_analysis_payload',
            return_value={
                'report_id': None,
                'report_version': '26-04.21',
                'project': {'id': 7, 'name': 'CRM'},
                'summary': {'requirements': 1},
                'generated_at': '2026-04-23T19:05:00+08:00',
                'tabs': [{'key': 'overview', 'label': '总览', 'metrics': [], 'blocks': []}],
            },
        ) as mocked_builder:
            response = anonymous_client.get(
                reverse('quality-share-live-version-analysis', args=[share_token])
            )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['report_version'], '26-04.21')
        self.assertEqual(response.data['project']['id'], 7)
        self.assertEqual(response.data['tabs'][0]['key'], 'overview')
        self.assertEqual(mocked_builder.call_args.kwargs['project_id'], 7)
        self.assertEqual(mocked_builder.call_args.args[0].version, '26-04.21')


class JiraBugAssociationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quality-bug-admin', password='secret123')
        self.client.force_authenticate(self.user)

    def test_update_bug_record_associations(self):
        record = JiraBugRecord.objects.create(version='26-04.15', issue_key='SYSWIN-3', row_index=1)

        response = self.client.post(
            reverse('jira-bug-record-associations', args=[record.id]),
            {
                'related_requirements': [
                    {'issue_key': 'SYSWIN-REQ-9', 'summary': '历史需求', 'version': '26-04.14'}
                ],
                'related_testcases': [
                    {
                        'mindmap_id': 12,
                        'mindmap_name': '收费管理脑图',
                        'node_text': '收费计算校验',
                        'node_type': 'case',
                        'path': '收费管理 / 收费计算校验',
                        'version_name': '26-04.14',
                    }
                ],
                'related_testpoints': [
                    {
                        'mindmap_id': 13,
                        'mindmap_name': '收费管理脑图',
                        'node_text': '金额边界值',
                        'node_type': 'testpoint',
                        'path': '收费管理 / 金额边界值',
                        'version_name': '26-04.13',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.related_requirements[0]['issue_key'], 'SYSWIN-REQ-9')
        self.assertEqual(record.related_requirements[0]['version'], '26-04.14')
        self.assertEqual(record.related_testcases[0]['version_name'], '26-04.14')
        self.assertEqual(record.related_testpoints[0]['node_type'], 'testpoint')


class JiraSyncPreserveAssociationTests(TestCase):
    def test_execute_jira_config_prefers_runtime_cookie_override(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={'cookie': DEFAULT_BUG_JIRA_COOKIE},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )

        class MockResponse:
            def __init__(self, payload):
                self.status_code = 200
                self.headers = {}
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        with patch.dict(os.environ, {JIRA_BUG_COOKIE_ENV: 'runtime-cookie-value'}, clear=False):
            with patch(
                'apps.quality_analysis.jira_services.requests.request',
                return_value=MockResponse(build_issue_table_payload()),
            ) as mocked_request:
                execute_jira_config(config)

        self.assertEqual(mocked_request.call_args.kwargs['headers']['cookie'], 'runtime-cookie-value')

    def test_execute_jira_config_removes_saved_legacy_cookie(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15',
            name='JIRA bug API',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={'Cookie': DEFAULT_BUG_JIRA_COOKIE, 'x-custom': '1'},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )

        class MockResponse:
            def __init__(self, payload):
                self.status_code = 200
                self.headers = {}
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        with patch(
            'apps.quality_analysis.jira_services.requests.request',
            return_value=MockResponse(build_issue_table_payload()),
        ) as mocked_request:
            execute_jira_config(config)

        sent_headers = {key.lower(): value for key, value in mocked_request.call_args.kwargs['headers'].items()}
        self.assertNotIn('cookie', sent_headers)
        self.assertEqual(sent_headers['x-custom'], '1')

    def test_execute_jira_config_raises_actionable_error_on_401(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={'cookie': DEFAULT_BUG_JIRA_COOKIE},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )

        class MockUnauthorizedResponse:
            status_code = 401
            headers = {
                'WWW-Authenticate': 'OAuth realm="http%3A%2F%2F172.31.119.34%3A8080"',
            }

            def raise_for_status(self):
                raise AssertionError('401 should be handled before raise_for_status')

            def json(self):
                return {}

        with patch(
            'apps.quality_analysis.jira_services.requests.request',
            return_value=MockUnauthorizedResponse(),
        ):
            with self.assertRaises(ValueError) as captured:
                execute_jira_config(config)

        message = str(captured.exception)
        self.assertIn('401', message)
        self.assertIn('Cookie', message)
        self.assertIn(JIRA_GENERAL_COOKIE_ENV, message)
        self.assertIn(JIRA_GENERAL_AUTHORIZATION_ENV, message)
        self.assertIn(JIRA_GENERAL_USERNAME_ENV, message)
        self.assertIn(JIRA_GENERAL_PASSWORD_ENV, message)

    def test_execute_jira_config_logs_in_before_sync_and_reuses_session(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15',
            name='JIRA线上BUG接口',
            request_url='http://jira.example.com/rest/issueNav/1/issueTable',
            request_method='POST',
            request_headers={'Cookie': 'stale-cookie', 'x-custom': '1'},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
            jira_login_enabled=True,
            jira_login_url='http://jira.example.com/login.jsp',
            jira_username='fengshaowen',
            jira_password_encrypted=encrypt_password('s123456'),
        )

        class MockResponse:
            def __init__(self, payload=None, status_code=200, text='', url='http://jira.example.com/secure/Dashboard.jspa'):
                self.status_code = status_code
                self.headers = {}
                self.text = text
                self.url = url
                self._payload = payload or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise AssertionError('unexpected HTTP error')

            def json(self):
                return self._payload

        class MockSession:
            def __init__(self):
                self.calls = []

            def get(self, url, **kwargs):
                self.calls.append(('get', url, kwargs))
                return MockResponse(
                    text='''
                        <form id="login-form" action="/login.jsp">
                          <input type="hidden" name="atl_token" value="token-1" />
                          <input name="os_username" />
                          <input name="os_password" />
                        </form>
                    ''',
                    url=url,
                )

            def post(self, url, **kwargs):
                self.calls.append(('post', url, kwargs))
                if url.endswith('/rest/auth/1/session'):
                    return MockResponse(status_code=404, text='REST login disabled', url=url)
                self.post_data = kwargs.get('data') or {}
                return MockResponse(text='<html>dashboard</html>', url='http://jira.example.com/secure/Dashboard.jspa')

            def request(self, **kwargs):
                self.calls.append(('request', kwargs.get('url'), kwargs))
                if kwargs.get('url', '').endswith('/rest/api/2/search'):
                    return MockResponse({'issues': [], 'names': {}})
                return MockResponse(build_issue_table_payload())

        session = MockSession()
        with patch('apps.quality_analysis.jira_services.requests.Session', return_value=session):
            result = execute_jira_config(config)

        self.assertEqual(result['status_code'], 200)
        self.assertEqual(session.calls[0][0], 'post')
        self.assertTrue(session.calls[0][1].endswith('/rest/auth/1/session'))
        self.assertEqual(session.calls[1][0], 'get')
        self.assertEqual(session.calls[2][0], 'post')
        self.assertEqual(session.post_data['os_username'], 'fengshaowen')
        self.assertEqual(session.post_data['os_password'], 's123456')
        request_calls = [call for call in session.calls if call[0] == 'request']
        self.assertGreaterEqual(len(request_calls), 1)
        first_headers = {key.lower(): value for key, value in request_calls[0][2]['headers'].items()}
        self.assertNotIn('cookie', first_headers)
        self.assertEqual(first_headers['x-custom'], '1')
        self.assertTrue(any(call[1].endswith('/rest/api/2/search') for call in request_calls))

    def test_execute_jira_requirement_config_retries_without_filter_id_on_private_filter_400(self):
        config = JiraRequirementInterfaceConfig.objects.create(
            version='26-04.99',
            name='JIRA requirement API',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=15943&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )

        class MockPrivateFilterResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text
                self.headers = {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise AssertionError('raise_for_status should not be reached for handled 400')

            def json(self):
                return build_issue_table_payload()

        calls = []

        def fake_request(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return MockPrivateFilterResponse(400, '请求的筛选器不存在或是私用。尝试重新登录。')
            return MockPrivateFilterResponse(200, '')

        with patch('apps.quality_analysis.jira_services.requests.request', side_effect=fake_request):
            result = execute_jira_requirement_config(config)

        self.assertEqual(result['status_code'], 200)
        self.assertEqual(len(calls), 2)
        self.assertIn('filterId=15943', calls[0]['data'])
        self.assertNotIn('filterId', calls[1]['data'])

    def test_execute_jira_sync_preserves_bug_record_associations(self):
        config = JiraInterfaceConfig.objects.create(
            version='26-04.15发版（8.2.0）',
            name='JIRA线上BUG接口',
            request_url='http://example.com/jira',
            request_method='POST',
            request_headers={},
            request_body='startIndex=0&filterId=16128&jql=project+%3D+SYSWIN&layoutKey=list-view',
        )
        original = JiraBugRecord.objects.create(
            config=config,
            version=config.version,
            issue_id='legacy-1',
            issue_key='SYSWIN-1',
            issue_type='BUG',
            summary='旧数据',
            related_requirements=[{'issue_key': 'SYSWIN-REQ-1', 'summary': '需求A', 'version': '26-04.15'}],
            related_testcases=[{'mindmap_id': 10, 'mindmap_name': '脑图A', 'node_text': '用例A', 'node_type': 'case', 'path': '模块A / 用例A'}],
            related_testpoints=[{'mindmap_id': 10, 'mindmap_name': '脑图A', 'node_text': '测试点A', 'node_type': 'testpoint', 'path': '模块A / 测试点A'}],
            row_index=1,
        )

        payload = build_issue_table_payload()

        class MockResponse:
            def __init__(self, payload):
                self.status_code = 200
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        with patch('apps.quality_analysis.jira_services.requests.request', return_value=MockResponse(payload)):
            result = execute_jira_config(config)

        refreshed = JiraBugRecord.objects.get(version=config.version, issue_key='SYSWIN-1')
        self.assertEqual(result['cleared_count'], 1)
        self.assertNotEqual(refreshed.id, original.id)
        self.assertEqual(refreshed.related_requirements, original.related_requirements)
        self.assertEqual(refreshed.related_testcases, original.related_testcases)
        self.assertEqual(refreshed.related_testpoints, original.related_testpoints)


class JiraRequirementRoleAssociationSerializerTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.pm_user = user_model.objects.create_user(
            username='pm.zhang',
            password='secret123',
            first_name='\u5f20\u4ea7\u54c1',
        )
        self.tester_user = user_model.objects.create_user(
            username='tester.li',
            password='secret123',
            first_name='\u674e\u6d4b\u8bd5',
        )
        self.frontend_user = user_model.objects.create_user(
            username='frontend.wang',
            password='secret123',
            first_name='\u738b\u524d\u7aef',
        )
        self.backend_user = user_model.objects.create_user(
            username='backend.zhao',
            password='secret123',
            first_name='\u8d75\u540e\u7aef',
        )

        role_members = {
            '\u4ea7\u54c1': [self.pm_user],
            '\u6d4b\u8bd5': [self.tester_user],
            '\u524d\u7aef': [self.frontend_user],
            '\u540e\u7aef': [self.backend_user],
        }
        for role_name, members in role_members.items():
            role = Role.objects.create(name=role_name)
            role.members.set(members)

    def test_requirement_serializer_maps_role_bound_people_fields(self):
        record = JiraRequirementRecord.objects.create(
            version='26-05.15',
            issue_key='SYSWIN-REQ-ROLE-1',
            summary='role mapping check',
            tester='tester.li',
            frontend_developer='frontend.wang',
            backend_developer='backend.zhao',
            raw_fields={
                'customfield_10737': '\u5f20\u4ea7\u54c1',
                'customfield_10222': 'tester.li',
                'customfield_10743': 'frontend.wang',
                'customfield_10741': 'backend.zhao',
            },
        )

        data = JiraRequirementRecordSerializer(record).data

        self.assertEqual(data['mapped_fields']['product_manager'], '\u5f20\u4ea7\u54c1')
        self.assertEqual(data['mapped_fields']['tester'], '\u674e\u6d4b\u8bd5')
        self.assertEqual(data['mapped_fields']['frontend_developer'], '\u738b\u524d\u7aef')
        self.assertEqual(data['mapped_fields']['backend_developer'], '\u8d75\u540e\u7aef')
        self.assertEqual(data['mapped_fields']['product_manager_members'][0]['id'], self.pm_user.id)
        self.assertEqual(data['mapped_fields']['tester_members'][0]['id'], self.tester_user.id)
        self.assertEqual(data['mapped_fields']['frontend_developer_members'][0]['id'], self.frontend_user.id)
        self.assertEqual(data['mapped_fields']['backend_developer_members'][0]['id'], self.backend_user.id)


if __name__ == '__main__':
    unittest.main()
