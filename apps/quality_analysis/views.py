import base64
import binascii
import json
import re
from datetime import timedelta
from types import SimpleNamespace

from django.core import signing
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.testcases.models import ManualTestCaseMindmap
from apps.defects.models import Defect
from apps.testcases.mindmap_node_utils import (
    parse_public_node_id,
    relation_item_matches_public_node_id,
    resolve_public_node_descriptor,
)
from .analytics import (
    get_backend_developer_root_cause_stats,
    get_defect_req_rate_stats,
    get_developer_root_cause_stats,
    get_frontend_developer_root_cause_stats,
    get_product_manager_root_cause_stats,
    get_product_root_cause_stats,
    get_req_developer_stats,
    get_req_group_stats,
    get_req_priority_status_stats,
    get_req_priority_type_stats,
    get_req_product_manager_stats,
    get_req_tester_workload_stats,
    get_requirement_defect_stats,
    get_requirement_root_cause_responsibility_stats,
    get_root_cause_responsibility_stats,
    get_tester_person_root_cause_stats,
    get_tester_root_cause_stats,
    get_testcase_tester_stats,
)

TESTING_MINDMAP_SCOPE = ManualTestCaseMindmap.SCOPE_TESTING
from .jira_services import build_role_member_lookup_bundle, execute_jira_config, execute_jira_requirement_config
from .models import (
    JiraBugRecord,
    JiraInterfaceConfig,
    JiraRequirementInterfaceConfig,
    JiraRequirementRecord,
    JiraRequirementRecordAttachment,
    QualityAnalysisSettings,
    QualityReport,
    cleanup_rich_text_images,
    extract_rich_text_image_paths,
)
from .serializers import (
    JiraBugRecordSerializer,
    JiraBugRecordAssociationSerializer,
    JiraInterfaceConfigSerializer,
    JiraRequirementInterfaceConfigSerializer,
    JiraRequirementRecordCreateUpdateSerializer,
    JiraRequirementRecordSerializer,
    QualityAnalysisSettingsSerializer,
    QualityReportCreateSerializer,
    QualityReportSerializer,
    SupplementalExcelUploadSerializer,
)
from .services import analyze_report, load_defect_dataframe, load_excel_dataframe
from .version_report_analytics import (
    build_all_versions_online_defect_analysis_payload,
    build_rd_progress_overview_payload,
    build_requirement_overview_payload,
    build_testing_overview_payload,
    build_version_analysis_payload,
    filter_online_bugs_for_all_version_analysis,
)
from .version_utils import jira_version_timeline_sort_key, normalize_jira_version


CHART_GENERATORS = {
    'requirement-defects': lambda report: get_requirement_defect_stats(load_defect_dataframe(report)),
    'root-cause-responsibility': lambda report: get_root_cause_responsibility_stats(load_defect_dataframe(report)),
    'requirement-root-cause-responsibility': lambda report: get_requirement_root_cause_responsibility_stats(load_defect_dataframe(report)),
    'product-root-cause': lambda report: get_product_root_cause_stats(load_defect_dataframe(report)),
    'developer-root-cause': lambda report: get_developer_root_cause_stats(load_defect_dataframe(report)),
    'tester-root-cause': lambda report: get_tester_root_cause_stats(load_defect_dataframe(report)),
    'product-manager-root-cause': lambda report: get_product_manager_root_cause_stats(
        load_defect_dataframe(report),
        req_df=load_excel_dataframe(report.requirement_excel) if report.requirement_excel else None,
    ),
    'frontend-developer-root-cause': lambda report: get_frontend_developer_root_cause_stats(load_defect_dataframe(report)),
    'backend-developer-root-cause': lambda report: get_backend_developer_root_cause_stats(load_defect_dataframe(report)),
    'tester-person-root-cause': lambda report: get_tester_person_root_cause_stats(load_defect_dataframe(report)),
    'req-priority-status': lambda report: get_req_priority_status_stats(load_excel_dataframe(report.requirement_excel)),
    'req-priority-type': lambda report: get_req_priority_type_stats(load_excel_dataframe(report.requirement_excel)),
    'req-group': lambda report: get_req_group_stats(load_excel_dataframe(report.requirement_excel)),
    'req-product-manager': lambda report: get_req_product_manager_stats(load_excel_dataframe(report.requirement_excel)),
    'req-developer': lambda report: get_req_developer_stats(load_excel_dataframe(report.requirement_excel)),
    'req-tester-workload': lambda report: get_req_tester_workload_stats(load_excel_dataframe(report.requirement_excel)),
    'testcase-tester': lambda report: get_testcase_tester_stats(load_excel_dataframe(report.testcase_excel)),
    'defect-req-rate': lambda report: get_defect_req_rate_stats(
        load_defect_dataframe(report),
        load_excel_dataframe(report.requirement_excel),
        load_excel_dataframe(report.testcase_excel),
    ),
}

REQUIRE_ANALYZED_REPORT = {
    'requirement-defects',
    'root-cause-responsibility',
    'requirement-root-cause-responsibility',
    'product-root-cause',
    'developer-root-cause',
    'tester-root-cause',
    'product-manager-root-cause',
    'frontend-developer-root-cause',
    'backend-developer-root-cause',
    'tester-person-root-cause',
    'defect-req-rate',
}
REQUIRE_REQUIREMENT_FILE = {
    'req-priority-status',
    'req-priority-type',
    'req-group',
    'req-product-manager',
    'req-developer',
    'req-tester-workload',
    'defect-req-rate',
    'product-manager-root-cause',
}
REQUIRE_TESTCASE_FILE = {'testcase-tester', 'defect-req-rate'}
LIVE_SHARE_TOKEN_SALT = 'quality-analysis-live-share'
INVALID_SHARE_LINK_MESSAGE = 'Share link is invalid or expired'
ONLINE_ANALYSIS_EMPTY_VERSION_LABEL = '未关联版本'
ONLINE_DEFECT_FIXED_STATUS_KEYWORDS = {
    'resolved',
    'regression_verified',
    'requirement_created',
    'closed',
    'done',
    'fixed',
    'finish',
    'finished',
    'completed',
    '已解决',
    '已关闭',
    '关闭',
    '完成',
    '修复',
}
ONLINE_BUG_FIX_RD_ESTIMATE_FIELDS = [
    '版本线上缺陷修复的研发预估工时',
    '线上缺陷修复研发预估工时',
    '线上缺陷修复的研发预估工时',
    '研发预估工时',
    '开发预估工时',
    '修复预估工时',
    '前端预估工时',
    '后端预估工时',
    'customfield_10749',
    'customfield_10748',
]
ONLINE_BUG_REGRESSION_TEST_ACTUAL_FIELDS = [
    '线上缺陷回归的测试实际工时',
    '线上缺陷回归测试实际工时',
    '回归测试实际工时',
    '测试实际投入工时',
    '测试实际工时',
    '测试预估工时',
    'customfield_10761',
]
REQUIREMENT_DEV_ESTIMATE_HOUR_FIELDS = [
    '需求开发预估投入工时',
    '开发预估投入工时',
    '研发预估投入工时',
    '前端预估工时',
    '后端预估工时',
    'customfield_10749',
    'customfield_10748',
]
REQUIREMENT_TEST_ESTIMATE_HOUR_FIELDS = [
    '需求测试预估投入工时',
    '测试预估投入工时',
    '测试预估工时',
    'customfield_10761',
]
ONLINE_DEFECT_ANALYSIS_SERIES = [
    ('requirement_dev_estimated_hours', '需求开发预估投入工时'),
    ('requirement_test_estimated_hours', '需求测试预估投入工时'),
    ('bug_fix_rd_estimated_hours', '版本线上缺陷修复的研发预估工时'),
    ('bug_regression_test_actual_hours', '线上缺陷回归的测试实际工时'),
    ('bug_created_count', '线上缺陷创建量'),
    ('bug_fixed_count', '线上缺陷修复量'),
]


def _normalize_online_analysis_version(value):
    normalized = normalize_jira_version(value)
    return normalized or ONLINE_ANALYSIS_EMPTY_VERSION_LABEL


def _normalize_raw_lookup_key(value):
    return re.sub(r'\s+', '', str(value or '').strip()).casefold()


def _iter_raw_field_values(raw_fields):
    if not isinstance(raw_fields, dict):
        return

    labels = raw_fields.get('__field_labels') if isinstance(raw_fields.get('__field_labels'), dict) else {}
    for field_key, field_value in raw_fields.items():
        if str(field_key or '').startswith('__'):
            continue
        yield str(field_key or ''), str(labels.get(field_key) or labels.get(str(field_key)) or ''), field_value


def _extract_number_from_value(value):
    if value in (None, ''):
        return 0.0

    if isinstance(value, bool):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, dict):
        for key in ('value', 'name', 'displayName'):
            if key in value:
                parsed_value = _extract_number_from_value(value.get(key))
                if parsed_value:
                    return parsed_value
        return 0.0

    if isinstance(value, (list, tuple)):
        return sum(_extract_number_from_value(item) for item in value)

    matched = re.search(r'-?\d+(?:\.\d+)?', str(value).replace(',', ''))
    return float(matched.group(0)) if matched else 0.0


def _sum_raw_numeric_fields(raw_fields, candidates):
    candidate_keys = {_normalize_raw_lookup_key(item) for item in candidates if str(item or '').strip()}
    total = 0.0

    for field_key, field_label, field_value in _iter_raw_field_values(raw_fields):
        lookup_keys = {
            _normalize_raw_lookup_key(field_key),
            _normalize_raw_lookup_key(field_label),
        }
        if lookup_keys & candidate_keys:
            total += _extract_number_from_value(field_value)

    return total


ONLINE_DEFECT_FIXED_STATUS = '\u5df2\u4ea4\u4ed8\u4e0a\u7ebf'


def _is_online_bug_fixed(status_value):
    return str(status_value or '').strip() == ONLINE_DEFECT_FIXED_STATUS


def _format_analysis_number(value):
    number = float(value or 0)
    return round(number, 2)


def _build_online_defect_analysis_payload(categories, bucket_map):
    normalized_categories = list(categories)
    return {
        'categories': normalized_categories,
        'series': [
            {
                'key': key,
                'name': name,
                'data': [_format_analysis_number(bucket_map.get(category, {}).get(key, 0)) for category in normalized_categories],
            }
            for key, name in ONLINE_DEFECT_ANALYSIS_SERIES
        ],
        'totals': {
            key: _format_analysis_number(sum(bucket_map.get(category, {}).get(key, 0) for category in normalized_categories))
            for key, _ in ONLINE_DEFECT_ANALYSIS_SERIES
        },
    }


def _parse_optional_project_id(raw_value):
    if raw_value in (None, ''):
        return None

    try:
        normalized_value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError('project_id 必须为整数') from exc

    if normalized_value <= 0:
        raise ValueError('project_id 必须为正整数')

    return normalized_value


def _build_live_share_token(*, version, project_id=None):
    payload = {
        'version': normalize_jira_version(version),
        'project_id': project_id,
    }
    signed_payload = signing.dumps(payload, salt=LIVE_SHARE_TOKEN_SALT, compress=True)
    encoded_token = base64.urlsafe_b64encode(signed_payload.encode('utf-8')).decode('ascii')
    return encoded_token.rstrip('=')


def _resolve_live_share_scope(share_token):
    normalized_token = str(share_token or '').strip()
    if not normalized_token:
        raise ValueError(INVALID_SHARE_LINK_MESSAGE)

    try:
        padding = '=' * (-len(normalized_token) % 4)
        signed_payload = base64.urlsafe_b64decode(f'{normalized_token}{padding}'.encode('ascii')).decode('utf-8')
        payload = signing.loads(signed_payload, salt=LIVE_SHARE_TOKEN_SALT)
    except (binascii.Error, UnicodeDecodeError, signing.BadSignature, signing.SignatureExpired, ValueError) as exc:
        raise ValueError(INVALID_SHARE_LINK_MESSAGE) from exc

    version = normalize_jira_version(payload.get('version'))
    if not version:
        raise ValueError(INVALID_SHARE_LINK_MESSAGE)

    project_id = _parse_optional_project_id(payload.get('project_id'))
    return version, project_id


def _build_live_version_analysis_payload(*, version, user, project_id=None):
    normalized_version = normalize_jira_version(version)
    if normalized_version.casefold() == 'all' or normalized_version == '全部版本':
        return build_all_versions_online_defect_analysis_payload(
            user=user,
            project_id=project_id,
        )
    if not normalized_version:
        raise ValueError('请选择版本号')

    return build_version_analysis_payload(
        SimpleNamespace(id=None, version=normalized_version),
        user=user,
        project_id=project_id,
    )


def _build_live_requirement_overview_payload(*, version, user, project_id=None):
    normalized_version = normalize_jira_version(version)
    if not normalized_version:
        raise ValueError('请选择版本号')

    return build_requirement_overview_payload(
        SimpleNamespace(id=None, version=normalized_version),
        user=user,
        project_id=project_id,
    )


def _build_live_testing_overview_payload(*, version, user, project_id=None):
    normalized_version = normalize_jira_version(version)
    if not normalized_version:
        raise ValueError('请选择版本号')

    return build_testing_overview_payload(
        SimpleNamespace(id=None, version=normalized_version),
        user=user,
        project_id=project_id,
    )


def _build_live_rd_progress_overview_payload(*, version, user, project_id=None):
    normalized_version = normalize_jira_version(version)
    if not normalized_version:
        raise ValueError('请选择版本号')

    return build_rd_progress_overview_payload(
        SimpleNamespace(id=None, version=normalized_version),
        user=user,
        project_id=project_id,
    )


def _build_live_report_snapshot(*, version, user, project_id=None):
    payload = _build_live_version_analysis_payload(
        version=version,
        user=user,
        project_id=project_id,
    )
    summary = payload.get('summary') or {}
    project = payload.get('project') or {}
    generated_at = payload.get('generated_at') or timezone.now().isoformat()
    requirement_count = int(summary.get('requirements') or 0)
    case_count = int(summary.get('cases') or 0)
    testpoint_count = int(summary.get('testpoints') or 0)
    version_defect_count = int(summary.get('version_defects') or 0)
    online_defect_count = int(summary.get('online_defects') or 0)
    module_count = int(summary.get('modules') or 0)
    group_count = int(summary.get('groups') or 0)
    project_name = str(project.get('name') or '').strip()
    report_version = payload['report_version']

    return {
        'id': f'live::{project.get("id") or "all"}::{report_version}',
        'report_type': 'live',
        'version': report_version,
        'status': 'completed',
        'status_display': '实时生成',
        'project_id': project.get('id'),
        'project_name': project_name,
        'requirements_count': requirement_count,
        'cases_count': case_count,
        'testpoints_count': testpoint_count,
        'version_defects_count': version_defect_count,
        'online_defects_count': online_defect_count,
        'module_count': module_count,
        'group_count': group_count,
        'total_defects': version_defect_count + online_defect_count,
        'classified_defects': version_defect_count + online_defect_count,
        'source_excel_name': project_name or '全部项目',
        'requirement_excel_name': f'需求 {requirement_count} / 组别 {group_count}',
        'testcase_excel_name': f'用例 {case_count} / 测试点 {testpoint_count}',
        'created_at': generated_at,
        'updated_at': generated_at,
        'analyzed_at': generated_at,
    }


def _validate_chart_request(report, chart_name):
    if chart_name not in CHART_GENERATORS:
        raise ValueError('不支持的图表类型')
    if chart_name in REQUIRE_ANALYZED_REPORT and report.status != 'completed':
        raise ValueError('报告尚未完成分析')
    if chart_name in REQUIRE_REQUIREMENT_FILE and not report.requirement_excel:
        raise ValueError('请先上传需求清单 Excel')
    if chart_name in REQUIRE_TESTCASE_FILE and not report.testcase_excel:
        raise ValueError('请先上传测试用例统计 Excel')


class QualityAnalysisSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _get_settings():
        return QualityAnalysisSettings.get_solo()

    def get(self, request):
        serializer = QualityAnalysisSettingsSerializer(self._get_settings())
        return Response(serializer.data)

    def put(self, request):
        instance = self._get_settings()
        serializer = QualityAnalysisSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class QualityReportViewSet(viewsets.ModelViewSet):
    queryset = QualityReport.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = None

    def get_queryset(self):
        queryset = self.queryset.order_by('-created_at')

        version = normalize_jira_version(self.request.query_params.get('version'))
        if version:
            queryset = queryset.filter(version=version)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return QualityReportCreateSerializer
        return QualityReportSerializer

    @action(detail=False, methods=['get'], url_path='jira-versions')
    def jira_versions(self, request):
        version_map = {}

        def collect_versions(queryset, timestamp_field):
            for item in queryset.values('version').annotate(latest_at=Max(timestamp_field)):
                version = item.get('version')
                latest_at = item.get('latest_at')
                if not version:
                    continue

                existing = version_map.get(version)
                if not existing or (latest_at and (existing['latest_at'] is None or latest_at > existing['latest_at'])):
                    version_map[version] = {
                        'version': version,
                        'latest_at': latest_at,
                    }

        collect_versions(JiraBugRecord.objects.all(), 'synced_at')
        collect_versions(JiraRequirementRecord.objects.all(), 'synced_at')
        collect_versions(JiraInterfaceConfig.objects.all(), 'updated_at')
        collect_versions(JiraRequirementInterfaceConfig.objects.all(), 'updated_at')

        versions = sorted(
            version_map.values(),
            key=lambda item: (
                item['latest_at'] or timezone.datetime.min.replace(tzinfo=timezone.get_current_timezone()),
                item['version'],
            ),
            reverse=True,
        )
        return Response(versions)

    @action(detail=False, methods=['get'], url_path='live-snapshot')
    def live_snapshot(self, request):
        try:
            snapshot = _build_live_report_snapshot(
                version=request.query_params.get('version'),
                user=request.user,
                project_id=_parse_optional_project_id(request.query_params.get('project_id')),
            )
            return Response(snapshot)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时质量分析生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='live-version-analysis')
    def live_version_analysis(self, request):
        try:
            payload = _build_live_version_analysis_payload(
                version=request.query_params.get('version'),
                user=request.user,
                project_id=_parse_optional_project_id(request.query_params.get('project_id')),
            )
            return Response(payload)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时质量分析生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='live-requirement-overview')
    def live_requirement_overview(self, request):
        try:
            payload = _build_live_requirement_overview_payload(
                version=request.query_params.get('version'),
                user=request.user,
                project_id=_parse_optional_project_id(request.query_params.get('project_id')),
            )
            return Response(payload)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时需求总览生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='live-testing-overview')
    def live_testing_overview(self, request):
        try:
            payload = _build_live_testing_overview_payload(
                version=request.query_params.get('version'),
                user=request.user,
                project_id=_parse_optional_project_id(request.query_params.get('project_id')),
            )
            return Response(payload)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时测试总览生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='live-rd-progress-overview')
    def live_rd_progress_overview(self, request):
        try:
            payload = _build_live_rd_progress_overview_payload(
                version=request.query_params.get('version'),
                user=request.user,
                project_id=_parse_optional_project_id(request.query_params.get('project_id')),
            )
            return Response(payload)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时研发进展总览生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        detail=False,
        methods=['post'],
        url_path='live-share',
        parser_classes=[JSONParser, FormParser, MultiPartParser],
    )
    def live_share(self, request):
        try:
            project_id = _parse_optional_project_id(request.data.get('project_id'))
            snapshot = _build_live_report_snapshot(
                version=request.data.get('version'),
                user=request.user,
                project_id=project_id,
            )
            token = _build_live_share_token(
                version=snapshot['version'],
                project_id=project_id,
            )
            return Response({'share_token': token})
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'实时分享链接生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        report = self.get_object()
        if report.status == 'completed':
            return Response({'detail': '该报告已经完成分析'}, status=status.HTTP_400_BAD_REQUEST)
        if report.status == 'analyzing':
            return Response({'detail': '该报告正在分析中'}, status=status.HTTP_400_BAD_REQUEST)

        report.status = 'analyzing'
        report.error_message = ''
        report.save(update_fields=['status', 'error_message', 'updated_at'])

        try:
            _, result = analyze_report(report)
            report.analyzed_at = timezone.now()
            report.save(
                update_fields=[
                    'status',
                    'total_defects',
                    'classified_defects',
                    'analysis_result',
                    'error_message',
                    'processed_excel',
                    'updated_at',
                    'analyzed_at',
                ]
            )
            return Response(
                {
                    'id': report.id,
                    'status': report.status,
                    'message': '分析完成',
                    'result': result,
                }
            )
        except Exception as exc:
            report.status = 'failed'
            report.error_message = str(exc)
            report.save(update_fields=['status', 'error_message', 'updated_at'])
            return Response({'detail': f'分析失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        url_path='upload-requirements',
    )
    def upload_requirements(self, request, pk=None):
        report = self.get_object()
        serializer = SupplementalExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if report.requirement_excel:
            report.requirement_excel.delete(save=False)
        report.requirement_excel = serializer.validated_data['file']
        report.save(update_fields=['requirement_excel', 'updated_at'])

        return Response({'message': '需求清单上传成功'})

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        url_path='upload-testcases',
    )
    def upload_testcases(self, request, pk=None):
        report = self.get_object()
        serializer = SupplementalExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if report.testcase_excel:
            report.testcase_excel.delete(save=False)
        report.testcase_excel = serializer.validated_data['file']
        report.save(update_fields=['testcase_excel', 'updated_at'])

        return Response({'message': '测试用例统计上传成功'})

    @action(detail=True, methods=['get'], url_path=r'charts/(?P<chart_name>[^/.]+)')
    def chart(self, request, pk=None, chart_name=None):
        report = self.get_object()

        try:
            _validate_chart_request(report, chart_name)
            return Response(CHART_GENERATORS[chart_name](report))
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='version-analysis')
    def version_analysis(self, request, pk=None):
        report = self.get_object()

        project_id = request.query_params.get('project_id')
        try:
            normalized_project_id = int(project_id) if project_id not in (None, '') else None
        except (TypeError, ValueError):
            return Response({'detail': 'project_id 必须为整数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = build_version_analysis_payload(
                report,
                user=request.user,
                project_id=normalized_project_id,
            )
            return Response(payload)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'版本质量分析生成失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        report = self.get_object()
        if report.status != 'completed':
            return Response({'detail': '仅已完成的报告支持分享'}, status=status.HTTP_400_BAD_REQUEST)

        token = report.ensure_share_token()
        return Response({'share_token': token})


class BaseJiraConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    executor = None

    def filter_config_queryset(self, queryset):
        queryset = queryset.order_by('-updated_at', '-created_at')
        version = normalize_jira_version(self.request.query_params.get('version'))
        if version:
            queryset = queryset.filter(version=version)
        return queryset

    def get_queryset(self):
        return self.filter_config_queryset(self.queryset)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        config = self.get_object()
        try:
            summary = self.executor(config)
            return Response(summary)
        except Exception as exc:
            response = getattr(exc, 'response', None)
            config.last_executed_at = timezone.now()
            config.last_status_code = response.status_code if response is not None else None
            config.last_execution_message = f'接口执行失败: {exc}'
            config.save(
                update_fields=[
                    'last_executed_at',
                    'last_status_code',
                    'last_execution_message',
                    'updated_at',
                ]
            )
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class JiraInterfaceConfigViewSet(BaseJiraConfigViewSet):
    queryset = JiraInterfaceConfig.objects.all()
    serializer_class = JiraInterfaceConfigSerializer
    executor = staticmethod(execute_jira_config)

    @action(detail=False, methods=['get'], url_path='combined')
    def combined(self, request):
        context = self.get_serializer_context()
        bug_queryset = self.get_queryset()
        requirement_queryset = self.filter_config_queryset(JiraRequirementInterfaceConfig.objects.all())

        payload = [
            {**item, 'interface_type': 'bug'}
            for item in JiraInterfaceConfigSerializer(bug_queryset, many=True, context=context).data
        ]
        payload.extend(
            {**item, 'interface_type': 'requirement'}
            for item in JiraRequirementInterfaceConfigSerializer(requirement_queryset, many=True, context=context).data
        )

        return Response(payload)


class JiraRequirementInterfaceConfigViewSet(BaseJiraConfigViewSet):
    queryset = JiraRequirementInterfaceConfig.objects.all()
    serializer_class = JiraRequirementInterfaceConfigSerializer
    executor = staticmethod(execute_jira_requirement_config)


def resolve_testpoint_descriptor_from_queryset(mindmap_queryset, public_node_id):
    parsed_node_id = parse_public_node_id(public_node_id)
    if not parsed_node_id or parsed_node_id.get('node_type') != 'testpoint':
        return None

    mindmap = mindmap_queryset.filter(id=parsed_node_id['mindmap_id']).first()
    if not mindmap:
        return None

    return resolve_public_node_descriptor(mindmap, public_node_id)


def jira_bug_record_matches_testpoint_id(record, public_node_id, descriptor=None):
    return any(
        relation_item_matches_public_node_id(relation_item, public_node_id, descriptor)
        for relation_item in (record.related_testpoints or [])
    )


def jira_related_requirements_match_keyword(related_requirements, keyword):
    normalized_keyword = str(keyword or '').strip().casefold()
    if not normalized_keyword:
        return False

    for relation_item in related_requirements or []:
        if isinstance(relation_item, dict):
            candidates = [
                relation_item.get('issue_key'),
                relation_item.get('summary'),
                relation_item.get('version'),
            ]
        else:
            candidates = [relation_item]

        if any(normalized_keyword in str(candidate or '').strip().casefold() for candidate in candidates):
            return True

    return False


def jira_bug_record_matches_requirement_keyword(record, keyword):
    return jira_related_requirements_match_keyword(record.related_requirements, keyword)


class JiraRecordPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 500


class BaseJiraRecordViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = JiraRecordPagination
    config_model = None
    config_executor = None

    def _get_keyword_param(self):
        for param_name in ('keyword', 'search', 'q', 'jira_keyword'):
            keyword = str(self.request.query_params.get(param_name) or '').strip()
            if keyword:
                return keyword
        return ''
    sync_label = 'JIRA 数据'

    @staticmethod
    def _parse_module_names_param(module_names):
        if not module_names:
            return []

        try:
            raw_module_names = json.loads(module_names)
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_module_names = str(module_names).split(',')

        if isinstance(raw_module_names, str):
            raw_module_names = [raw_module_names]

        parsed_module_names = []
        for item in raw_module_names:
            normalized_item = str(item or '').strip()
            if normalized_item:
                parsed_module_names.append(normalized_item)

        return parsed_module_names

    @staticmethod
    def _match_records_by_module_names(queryset, parsed_module_names):
        if not parsed_module_names:
            return queryset

        no_module_label = '无模块'.casefold()
        wants_empty_module = any(str(item or '').strip().casefold() == no_module_label for item in parsed_module_names)
        normalized_needles = [
            item.casefold()
            for item in parsed_module_names
            if str(item or '').strip().casefold() != no_module_label
        ]
        matched_ids = []

        for record_id, module_value in queryset.values_list('id', 'module'):
            normalized_module_value = str(module_value or '').strip()
            if not normalized_module_value:
                if wants_empty_module:
                    matched_ids.append(record_id)
                continue

            haystack = normalized_module_value.casefold()
            if not haystack:
                continue

            if any(needle in haystack for needle in normalized_needles):
                matched_ids.append(record_id)

        if not matched_ids:
            return queryset.none()

        return queryset.filter(id__in=matched_ids)

    def get_queryset(self):
        queryset = self.queryset.order_by('-synced_at', 'row_index', 'issue_key')

        version = self.request.query_params.get('version')
        if version:
            queryset = queryset.filter(version=version)

        module_names = self.request.query_params.get('module_names')
        if module_names:
            parsed_module_names = self._parse_module_names_param(module_names)
            queryset = self._match_records_by_module_names(queryset, parsed_module_names)

        keyword = self._get_keyword_param()
        if keyword:
            keyword_queryset = queryset.filter(
                Q(issue_key__icontains=keyword) |
                Q(summary__icontains=keyword) |
                Q(module__icontains=keyword)
            )
            if self.queryset.model is JiraBugRecord:
                related_requirement_ids = [
                    record_id
                    for record_id, related_requirements in queryset.values_list('id', 'related_requirements')
                    if jira_related_requirements_match_keyword(related_requirements, keyword)
                ]
                queryset = queryset.filter(
                    Q(id__in=keyword_queryset.values('id')) |
                    Q(id__in=related_requirement_ids)
                )
            else:
                queryset = keyword_queryset

        testpoint_id = str(self.request.query_params.get('testpoint_id') or '').strip()
        if testpoint_id and self.queryset.model is JiraBugRecord:
            mindmap_queryset = ManualTestCaseMindmap.objects.filter(mindmap_scope=TESTING_MINDMAP_SCOPE)
            descriptor = resolve_testpoint_descriptor_from_queryset(mindmap_queryset, testpoint_id)
            matched_ids = [
                record.id
                for record in queryset
                if jira_bug_record_matches_testpoint_id(record, testpoint_id, descriptor)
            ]
            queryset = queryset.filter(id__in=matched_ids)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['role_member_lookup'] = build_role_member_lookup_bundle()
        return context

    def get_refresh_configs(self):
        if self.config_model is None or self.config_executor is None:
            raise ValueError('JIRA refresh is not configured for this viewset')

        queryset = self.config_model.objects.filter(is_active=True).order_by('version', 'id')
        version = normalize_jira_version(self.request.query_params.get('version'))
        if version:
            queryset = queryset.filter(version=version)
        return list(queryset), version

    @action(detail=False, methods=['post'], url_path='refresh')
    def refresh(self, request):
        try:
            configs, requested_version = self.get_refresh_configs()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not configs:
            detail = (
                f'未找到版本 {requested_version} 对应的启用接口配置'
                if requested_version
                else '未找到启用中的接口配置'
            )
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        total_synced_count = 0

        for config in configs:
            try:
                summary = self.config_executor(config)
            except Exception as exc:
                return Response(
                    {'detail': f'版本 {config.version} 同步失败: {exc}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            results.append(
                {
                    'config_id': config.id,
                    'version': config.version,
                    **summary,
                }
            )
            total_synced_count += int(summary.get('synced_count') or 0)

        version_count = len(results)
        if version_count == 1:
            message = results[0].get('message') or f'{self.sync_label}同步完成'
        else:
            message = f'已完成 {version_count} 个版本的{self.sync_label}同步，共同步 {total_synced_count} 条记录'

        return Response(
            {
                'message': message,
                'version_count': version_count,
                'synced_count': total_synced_count,
                'results': results,
            }
        )

    @action(detail=False, methods=['get'])
    def versions(self, request):
        model = self.queryset.model
        version_stats = (
            model.objects.values('version')
            .annotate(record_count=Count('id'), latest_synced_at=Max('synced_at'))
            .order_by('-latest_synced_at', '-version')
        )
        return Response(list(version_stats))

    @action(detail=False, methods=['post'], url_path='clear-selected')
    def clear_selected(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'detail': '请选择需要清空的记录'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.queryset.filter(id__in=ids)
        cleared_count = queryset.count()
        if not cleared_count:
            return Response({'detail': '未找到可清空的记录'}, status=status.HTTP_400_BAD_REQUEST)

        queryset.delete()
        return Response(
            {
                'message': f'已清空 {cleared_count} 条记录',
                'cleared_count': cleared_count,
            }
        )


class JiraBugRecordViewSet(BaseJiraRecordViewSet):
    queryset = JiraBugRecord.objects.select_related('config').all()
    serializer_class = JiraBugRecordSerializer
    config_model = JiraInterfaceConfig
    config_executor = staticmethod(execute_jira_config)
    sync_label = '线上缺陷'

    @action(detail=False, methods=['get'], url_path='online-defect-analysis')
    def online_defect_analysis(self, request):
        raw_version = request.query_params.get('version')
        requested_version = normalize_jira_version(raw_version)
        is_all_versions = not requested_version or requested_version.casefold() == 'all'
        bug_queryset = JiraBugRecord.objects.all()
        requirement_queryset = JiraRequirementRecord.objects.all()
        scope = {'mode': 'all' if is_all_versions else 'selected'}

        if is_all_versions:
            since = timezone.now() - timedelta(days=365)
            bug_queryset = bug_queryset.filter(synced_at__gte=since)
            requirement_queryset = requirement_queryset.filter(synced_at__gte=since)
            scope['since'] = since.isoformat()
        else:
            bug_queryset = bug_queryset.filter(version=requested_version)
            requirement_queryset = requirement_queryset.filter(version=requested_version)
            scope['version'] = requested_version

        bucket_map = {}
        version_latest_time = {}

        def ensure_bucket(version):
            version_label = _normalize_online_analysis_version(version)
            if version_label not in bucket_map:
                bucket_map[version_label] = {key: 0 for key, _ in ONLINE_DEFECT_ANALYSIS_SERIES}
            return version_label

        for record in requirement_queryset.only('version', 'raw_fields', 'synced_at'):
            version_label = ensure_bucket(record.version)
            bucket_map[version_label]['requirement_dev_estimated_hours'] += _sum_raw_numeric_fields(
                record.raw_fields,
                REQUIREMENT_DEV_ESTIMATE_HOUR_FIELDS,
            )
            bucket_map[version_label]['requirement_test_estimated_hours'] += _sum_raw_numeric_fields(
                record.raw_fields,
                REQUIREMENT_TEST_ESTIMATE_HOUR_FIELDS,
            )
            version_latest_time[version_label] = max(
                version_latest_time.get(version_label, record.synced_at),
                record.synced_at,
            )

        bug_records = list(bug_queryset.only('version', 'status', 'creator', 'raw_fields', 'synced_at'))
        if is_all_versions:
            bug_records = filter_online_bugs_for_all_version_analysis(bug_records)

        for record in bug_records:
            version_label = ensure_bucket(record.version)
            bucket_map[version_label]['bug_created_count'] += 1
            if _is_online_bug_fixed(record.status):
                bucket_map[version_label]['bug_fixed_count'] += 1
            bucket_map[version_label]['bug_fix_rd_estimated_hours'] += _sum_raw_numeric_fields(
                record.raw_fields,
                ONLINE_BUG_FIX_RD_ESTIMATE_FIELDS,
            )
            bucket_map[version_label]['bug_regression_test_actual_hours'] += _sum_raw_numeric_fields(
                record.raw_fields,
                ONLINE_BUG_REGRESSION_TEST_ACTUAL_FIELDS,
            )
            version_latest_time[version_label] = max(
                version_latest_time.get(version_label, record.synced_at),
                record.synced_at,
            )

        if not is_all_versions and requested_version:
            ensure_bucket(requested_version)

        fallback_time = timezone.now() - timedelta(days=36500)
        categories = sorted(
            bucket_map.keys(),
            key=lambda item: jira_version_timeline_sort_key(
                item,
                version_latest_time.get(item),
                fallback_time,
            ),
        )

        payload = _build_online_defect_analysis_payload(categories, bucket_map)
        payload['scope'] = scope
        return Response(payload)

    @action(detail=True, methods=['post'])
    def associations(self, request, pk=None):
        record = self.get_object()
        serializer = JiraBugRecordAssociationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        record.related_requirements = validated_data.get('related_requirements', [])
        record.related_testcases = validated_data.get('related_testcases', [])
        record.related_testpoints = validated_data.get('related_testpoints', [])
        record.save(
            update_fields=[
                'related_requirements',
                'related_testcases',
                'related_testpoints',
                'updated_at',
            ]
        )

        return Response(JiraBugRecordSerializer(record, context=self.get_serializer_context()).data)


def parse_request_list(data, key, cast=str):
    if hasattr(data, 'getlist') and key in data:
        values = data.getlist(key)
        if len(values) > 1:
            return [cast(item) for item in values if str(item).strip()]

    if key not in data:
        return None

    value = data.get(key)
    if value in (None, '', []):
        return []

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            values = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            values = [item.strip() for item in stripped.split(',') if item.strip()]
    else:
        values = [value]

    parsed_values = []
    for item in values:
        item_str = str(item).strip()
        if not item_str:
            continue
        try:
            parsed_values.append(cast(item))
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError({key: '字段格式不正确'}) from exc

    return parsed_values


def parse_request_json_list(data, key):
    if key not in data:
        return None

    value = data.get(key)
    if value in (None, '', []):
        return []

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError({key: '关联数据格式不正确'}) from exc
        values = parsed if isinstance(parsed, list) else [parsed]
    else:
        values = [value]

    normalized_values = []
    for item in values:
        if isinstance(item, dict):
            normalized_values.append(item)

    return normalized_values


def parse_request_json_object(data, key):
    if key not in data:
        return None

    value = data.get(key)
    if value in (None, ''):
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError({key: 'JSON 字段格式不正确'}) from exc
        if isinstance(parsed, dict):
            return parsed

    raise serializers.ValidationError({key: 'JSON 字段必须是对象'})


def normalize_requirement_request_data(request):
    data = {}
    for key in [
        'version',
        'issue_id',
        'issue_key',
        'issue_type',
        'summary',
        'module',
        'customer_name',
        'priority',
        'status',
        'description',
        'creator',
        'handler',
        'tester',
        'group_name',
        'frontend_developer',
        'backend_developer',
        'row_index',
    ]:
        if key in request.data:
            data[key] = request.data.get(key)

    related_mindmaps = parse_request_json_list(request.data, 'related_mindmaps')
    if related_mindmaps is not None:
        data['related_mindmaps'] = related_mindmaps

    raw_fields = parse_request_json_object(request.data, 'raw_fields')
    if raw_fields is not None:
        data['raw_fields'] = raw_fields

    retain_attachment_ids = parse_request_list(request.data, 'retain_attachment_ids', int)
    if retain_attachment_ids is not None:
        data['retain_attachment_ids'] = retain_attachment_ids

    return data


def clear_requirement_attachment_file(attachment):
    attachment.delete()


def apply_requirement_attachment_changes(record, request, operator, retain_attachment_ids=None):
    retain_attachment_ids = set(retain_attachment_ids or [])

    if retain_attachment_ids:
        removable_attachments = record.attachments.exclude(id__in=retain_attachment_ids)
    elif retain_attachment_ids == set():
        removable_attachments = record.attachments.all()
    else:
        removable_attachments = JiraRequirementRecordAttachment.objects.none()

    for attachment in removable_attachments:
        clear_requirement_attachment_file(attachment)

    for uploaded_file in request.FILES.getlist('attachments'):
        JiraRequirementRecordAttachment.objects.create(
            requirement=record,
            name=uploaded_file.name,
            file=uploaded_file,
            uploaded_by=operator,
        )


class JiraRequirementRecordViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    BaseJiraRecordViewSet,
):
    queryset = JiraRequirementRecord.objects.select_related('config').prefetch_related('attachments__uploaded_by').all()
    serializer_class = JiraRequirementRecordSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    config_model = JiraRequirementInterfaceConfig
    config_executor = staticmethod(execute_jira_requirement_config)
    sync_label = 'JIRA需求数据'

    @staticmethod
    def _normalize_issue_key(value):
        return str(value or '').strip()

    @staticmethod
    def _parse_positive_int(value):
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            return None
        return parsed_value if parsed_value > 0 else None

    def _get_manual_context_ids(self):
        query_params = self.request.query_params
        return {
            'project_id': self._parse_positive_int(query_params.get('project_id')),
            'manual_version_id': self._parse_positive_int(query_params.get('manual_version_id')),
        }

    def _build_requirement_relation_count_context(self, records):
        record_list = list(records)
        requirement_keys = {
            self._normalize_issue_key(record.issue_key)
            for record in record_list
            if self._normalize_issue_key(record.issue_key)
        }
        requirement_versions = {
            str(record.version or '').strip()
            for record in record_list
            if str(record.version or '').strip()
        }

        if not requirement_keys:
            return {
                'requirement_version_defect_count_lookup': {},
                'requirement_bug_record_count_lookup': {},
            }

        context_ids = self._get_manual_context_ids()
        defect_queryset = Defect.objects.filter(
            record_type=Defect.RECORD_TYPE_DEFECT,
            requirement_id__in=requirement_keys,
        )
        if context_ids['project_id']:
            defect_queryset = defect_queryset.filter(project_id=context_ids['project_id'])
        if context_ids['manual_version_id']:
            defect_queryset = defect_queryset.filter(version_id=context_ids['manual_version_id'])
            defect_rows = defect_queryset.values('requirement_id').annotate(record_count=Count('id'))
            defect_count_by_key = {
                self._normalize_issue_key(item['requirement_id']): item['record_count']
                for item in defect_rows
            }
            version_defect_lookup = {
                (str(record.version or '').strip(), self._normalize_issue_key(record.issue_key)): defect_count_by_key.get(
                    self._normalize_issue_key(record.issue_key),
                    0,
                )
                for record in record_list
                if self._normalize_issue_key(record.issue_key)
            }
        else:
            if requirement_versions:
                defect_queryset = defect_queryset.filter(version__name__in=requirement_versions)
            defect_rows = defect_queryset.values('requirement_id', 'version__name').annotate(record_count=Count('id'))
            version_defect_lookup = {
                (str(item['version__name'] or '').strip(), self._normalize_issue_key(item['requirement_id'])): item['record_count']
                for item in defect_rows
            }

        bug_record_lookup = {}
        bug_queryset = JiraBugRecord.objects.only('version', 'related_requirements')
        if requirement_versions:
            bug_queryset = bug_queryset.filter(version__in=requirement_versions)

        for bug_record in bug_queryset:
            bug_version = str(bug_record.version or '').strip()
            matched_keys = set()
            for item in bug_record.related_requirements or []:
                if isinstance(item, dict):
                    issue_key = self._normalize_issue_key(item.get('issue_key'))
                else:
                    issue_key = self._normalize_issue_key(item)
                if issue_key in requirement_keys:
                    matched_keys.add(issue_key)

            for issue_key in matched_keys:
                lookup_key = (bug_version, issue_key)
                bug_record_lookup[lookup_key] = bug_record_lookup.get(lookup_key, 0) + 1

        return {
            'requirement_version_defect_count_lookup': version_defect_lookup,
            'requirement_bug_record_count_lookup': bug_record_lookup,
        }

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return JiraRequirementRecordCreateUpdateSerializer
        return JiraRequirementRecordSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        records = list(page if page is not None else queryset)
        context = {
            **self.get_serializer_context(),
            **self._build_requirement_relation_count_context(records),
        }
        serializer = self.get_serializer(records, many=True, context=context)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        context = {
            **self.get_serializer_context(),
            **self._build_requirement_relation_count_context([instance]),
        }
        serializer = self.get_serializer(instance, context=context)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=normalize_requirement_request_data(request))
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop('retain_attachment_ids', None)
        record = serializer.save()
        apply_requirement_attachment_changes(record, request, request.user)

        output = JiraRequirementRecordSerializer(
            self.get_queryset().get(pk=record.pk),
            context={
                **self.get_serializer_context(),
                **self._build_requirement_relation_count_context([record]),
            },
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        record = self.get_object()
        previous_description = record.description
        serializer = self.get_serializer(
            record,
            data=normalize_requirement_request_data(request),
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        retain_attachment_ids = serializer.validated_data.pop('retain_attachment_ids', None)
        record = serializer.save()

        if previous_description != record.description:
            previous_image_paths = extract_rich_text_image_paths(previous_description)
            next_image_paths = extract_rich_text_image_paths(record.description)
            cleanup_rich_text_images(previous_image_paths - next_image_paths)

        if retain_attachment_ids is not None or request.FILES.getlist('attachments'):
            apply_requirement_attachment_changes(
                record,
                request,
                request.user,
                retain_attachment_ids=retain_attachment_ids,
            )

        output = JiraRequirementRecordSerializer(
            self.get_queryset().get(pk=record.pk),
            context={
                **self.get_serializer_context(),
                **self._build_requirement_relation_count_context([record]),
            },
        )
        return Response(output.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=['post'], url_path='clear-selected')
    @transaction.atomic
    def clear_selected(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'detail': '请选择需要清空的记录'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(id__in=ids)
        records = list(queryset)
        cleared_count = len(records)
        if not cleared_count:
            return Response({'detail': '未找到可清空的记录'}, status=status.HTTP_400_BAD_REQUEST)

        for record in records:
            self.perform_destroy(record)

        return Response(
            {
                'message': f'已清空 {cleared_count} 条记录',
                'cleared_count': cleared_count,
            }
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def shared_report_detail(request, share_token):
    report = QualityReport.objects.filter(share_token=share_token).first()
    if not report:
        return Response({'detail': '分享链接不存在或已失效'}, status=status.HTTP_404_NOT_FOUND)
    if report.status != 'completed':
        return Response({'detail': '报告尚未完成分析'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = QualityReportSerializer(report)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def shared_report_chart(request, share_token, chart_name):
    report = QualityReport.objects.filter(share_token=share_token).first()
    if not report:
        return Response({'detail': '分享链接不存在或已失效'}, status=status.HTTP_404_NOT_FOUND)

    try:
        _validate_chart_request(report, chart_name)
        return Response(CHART_GENERATORS[chart_name](report))
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def shared_live_report_version_analysis(request, share_token):
    try:
        version, project_id = _resolve_live_share_scope(share_token)
        payload = _build_live_version_analysis_payload(
            version=version,
            user=None,
            project_id=project_id,
        )
        return Response(payload)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        return Response({'detail': f'实时分享数据加载失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
