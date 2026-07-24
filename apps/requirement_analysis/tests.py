import json
import tarfile
import zipfile
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from apps.projects.models import Project
from backend.internal_service_auth import build_internal_service_signature
from .models import RequirementDocument, RequirementAnalysis, BusinessRequirement, GeneratedTestCase, PromptConfig, TestCaseGenerationTask, AIModelConfig
from .prompt_defaults import DEFAULT_PROMPT_TYPES, get_preferred_prompt_config, ensure_default_prompt_config

User = get_user_model()


def build_xmind_file_bytes():
    payload = [
        {
            'title': '登录功能测试脑图',
            'rootTopic': {
                'title': '邮箱密码登录',
                'children': {
                    'attached': [
                        {'title': '输入正确邮箱和密码登录成功'},
                        {'title': '输入错误密码提示错误原因'},
                    ]
                },
            },
        }
    ]
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('content.json', json.dumps(payload, ensure_ascii=False))
    return buffer.getvalue()


def build_zip_requirement_bytes():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('docs/login.md', '# Login requirement\nSupport email and password login.')
        archive.writestr('notes/readme.txt', 'The system must show validation errors.')
    return buffer.getvalue()


def build_tar_gz_requirement_bytes():
    buffer = BytesIO()
    content = b'Archive requirement: generate testcase from tar.gz.'
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        info = tarfile.TarInfo('requirements/archive.txt')
        info.size = len(content)
        archive.addfile(info, BytesIO(content))
    return buffer.getvalue()


def build_excel_requirement_bytes():
    import openpyxl

    buffer = BytesIO()
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Requirements'
    worksheet.append(['ID', 'Title', 'Acceptance Criteria'])
    worksheet.append(['REQ-1', 'Email login', 'Valid email and password can login.'])
    workbook.save(buffer)
    return buffer.getvalue()


class RequirementAnalysisTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='Test Project',
            description='A test project',
            owner=self.user,
        )
        self.client = APIClient()

    def test_requirement_document_creation(self):
        """测试需求文档创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.status, 'uploaded')

    @override_settings(ROOT_URLCONF='backend.urls_document')
    @patch('apps.requirement_analysis.internal_views.DocumentProcessor.extract_text', return_value='service extracted text')
    def test_internal_document_extraction_requires_valid_signature(self, extract_text_mock):
        document = RequirementDocument.objects.create(
            title='Internal extraction',
            file=SimpleUploadedFile('internal.txt', b'internal content'),
            document_type='txt',
            uploaded_by=self.user,
            project=self.project,
        )

        rejected = self.client.post(
            '/internal/document-extraction/',
            {'document_id': document.id},
            format='json',
        )
        self.assertEqual(rejected.status_code, status.HTTP_403_FORBIDDEN)

        signature = build_internal_service_signature('document-extraction', document.id)
        accepted = self.client.post(
            '/internal/document-extraction/',
            {'document_id': document.id},
            format='json',
            HTTP_X_TESTHUB_INTERNAL_SIGNATURE=signature,
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(accepted.json()['extracted_text'], 'service extracted text')
        extract_text_mock.assert_called_once()

    def test_requirement_analysis_creation(self):
        """测试需求分析创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report',
            requirements_count=5
        )
        self.assertEqual(analysis.requirements_count, 5)
        self.assertEqual(analysis.document, doc)

    def test_business_requirement_creation(self):
        """测试业务需求创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report'
        )
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id='REQ-001',
            requirement_name='Test Requirement',
            requirement_type='functional',
            module='Test Module',
            requirement_level='high',
            description='Test description',
            acceptance_criteria='Test criteria'
        )
        self.assertEqual(requirement.requirement_id, 'REQ-001')
        self.assertEqual(requirement.requirement_type, 'functional')
        self.assertEqual(requirement.audit_status, 'pending')

    def test_business_requirement_audit_updates_status_user_and_time(self):
        """AI需求审核应记录审核状态、审核人和审核时间"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report'
        )
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id='REQ-AUDIT-001',
            requirement_name='Audit Requirement',
            requirement_type='functional',
            module='Test Module',
            requirement_level='medium',
            description='Test description',
            acceptance_criteria='Test criteria'
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            f'/api/requirement-analysis/api/requirements/{requirement.id}/audit/',
            {'audit_status': 'approved'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        requirement.refresh_from_db()
        self.assertEqual(requirement.audit_status, 'approved')
        self.assertEqual(requirement.audited_by, self.user)
        self.assertIsNotNone(requirement.audited_at)
        self.assertEqual(response.data['requirement']['audit_status_display'], '已审核')
        self.assertEqual(response.data['requirement']['audited_by_name'], self.user.username)

    def test_generated_test_case_creation(self):
        """测试生成测试用例创建"""
        doc = RequirementDocument.objects.create(
            title='Test Document',
            document_type='txt',
            uploaded_by=self.user,
            project=self.project
        )
        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report='Test analysis report'
        )
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id='REQ-001',
            requirement_name='Test Requirement',
            requirement_type='functional',
            module='Test Module',
            requirement_level='high',
            description='Test description',
            acceptance_criteria='Test criteria'
        )
        test_case = GeneratedTestCase.objects.create(
            requirement=requirement,
            case_id='TC-001',
            title='Test Case Title',
            priority='P1',
            precondition='Test precondition',
            test_steps='Test steps',
            expected_result='Test result'
        )
        self.assertEqual(test_case.case_id, 'TC-001')
        self.assertEqual(test_case.status, 'generated')

    def test_prefer_default_prompt_config(self):
        """默认提示词应优先于临时模板"""
        default_writer = PromptConfig.objects.create(
            name='默认用例编写提示词',
            prompt_type='writer',
            content='default writer',
            is_active=True,
            created_by=self.user,
        )
        PromptConfig.objects.create(
            name='临时用例编写提示词',
            prompt_type='writer',
            content='temp writer',
            is_active=True,
            created_by=self.user,
        )
        selected = get_preferred_prompt_config('writer')
        self.assertEqual(selected.id, default_writer.id)

    def test_ensure_default_prompt_config_creates_default(self):
        """缺失默认提示词时应自动恢复"""
        prompt = ensure_default_prompt_config('reviewer', created_by=self.user)
        self.assertEqual(prompt.name, '默认用例评审提示词')
        self.assertTrue(prompt.is_active)

    def test_ensure_default_requirement_prompt_configs_create_defaults(self):
        """需求分析和需求评审默认提示词应可自动恢复"""
        writer = ensure_default_prompt_config('requirement_writer', created_by=self.user)
        reviewer = ensure_default_prompt_config('requirement_reviewer', created_by=self.user)

        self.assertEqual(writer.name, '默认需求分析与编写提示词')
        self.assertEqual(writer.prompt_type, 'requirement_writer')
        self.assertIn('需求分析与编写专家', writer.content)
        self.assertEqual(reviewer.name, '默认需求评审提示词')
        self.assertEqual(reviewer.prompt_type, 'requirement_reviewer')
        self.assertIn('需求评审专家', reviewer.content)

    def test_all_default_prompt_types_can_be_seeded(self):
        """四类内置默认提示词均应可落库"""
        prompts = [ensure_default_prompt_config(prompt_type, created_by=self.user) for prompt_type in DEFAULT_PROMPT_TYPES]

        self.assertEqual({prompt.prompt_type for prompt in prompts}, set(DEFAULT_PROMPT_TYPES))
        self.assertTrue(all(prompt.is_active for prompt in prompts))

    def test_document_create_requirement_endpoint(self):
        """上传需求文档后应可直接创建AI需求"""
        self.client.force_authenticate(self.user)
        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': '邮箱登录需求文档',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'login.txt',
                    '用户可以使用邮箱和密码登录系统。登录失败需要提示原因。'.encode('utf-8'),
                    content_type='text/plain',
                ),
            },
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/create_requirement/",
            {'title': '邮箱与密码登录', 'project': self.project.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['requirement']['requirement_name'], '邮箱与密码登录')
        self.assertEqual(BusinessRequirement.objects.count(), 1)
        requirement = BusinessRequirement.objects.first()
        self.assertIn('用户可以使用邮箱和密码登录系统', requirement.description)
        self.assertEqual(requirement.analysis.document.project, self.project)

    def test_document_relationships_endpoint_returns_lifecycle_graph(self):
        """Uploaded files should expose AI研发链路关系 for the file tab."""
        self.client.force_authenticate(self.user)
        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': 'Login requirement file',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'login.txt',
                    'User can login with email and password.'.encode('utf-8'),
                    content_type='text/plain',
                ),
            },
            format='multipart',
        )
        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)

        create_response = self.client.post(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/create_requirement/",
            {'title': 'Email password login', 'project': self.project.id},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        relationship_response = self.client.get(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/relationships/",
        )
        self.assertEqual(relationship_response.status_code, status.HTTP_200_OK)
        self.assertEqual(relationship_response.data['summary']['analysis_count'], 1)
        self.assertEqual(relationship_response.data['summary']['requirement_count'], 1)
        self.assertIn('创建需求-上传需求文档', relationship_response.data['summary']['source_channels'])
        node_types = {item['type'] for item in relationship_response.data['nodes']}
        self.assertIn('file', node_types)
        self.assertIn('requirement_analysis', node_types)
        self.assertIn('ai_requirement', node_types)

        list_response = self.client.get('/api/requirement-analysis/api/documents/', {'search': 'Login'})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        list_payload = list_response.data.get('results', list_response.data)
        self.assertGreaterEqual(list_payload[0]['relationship_summary']['requirement_count'], 1)

    def test_document_generate_testcases_endpoint_creates_task(self):
        """上传需求文档后应可创建需求并启动测试用例生成任务"""
        AIModelConfig.objects.create(
            name='Writer',
            model_type='deepseek',
            role='writer',
            api_key='test-key',
            base_url='https://api.example.com',
            model_name='deepseek-chat',
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)
        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': '邮箱登录需求文档',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'login.txt',
                    '用户可以使用邮箱和密码登录系统。登录失败需要提示原因。'.encode('utf-8'),
                    content_type='text/plain',
                ),
            },
            format='multipart',
        )

        response = self.client.post(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/generate_testcases/",
            {'title': '邮箱与密码登录', 'project': self.project.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(BusinessRequirement.objects.filter(requirement_name='邮箱与密码登录').exists())
        self.assertTrue(TestCaseGenerationTask.objects.filter(task_id=response.data['task_id']).exists())
        requirement = BusinessRequirement.objects.get(requirement_name='邮箱与密码登录')
        self.assertEqual(requirement.case_generation_status, 'generating')

    def test_xmind_document_upload_extract_and_generate_testcases(self):
        """AI会话上传XMind时应能作为需求文档提取节点并生成用例任务"""
        AIModelConfig.objects.create(
            name='Writer',
            model_type='deepseek',
            role='writer',
            api_key='test-key',
            base_url='https://api.example.com',
            model_name='deepseek-chat',
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)
        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': '邮箱登录测试脑图',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'login.xmind',
                    build_xmind_file_bytes(),
                    content_type='application/octet-stream',
                ),
            },
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RequirementDocument.objects.get(id=upload_response.data['id']).document_type, 'xmind')

        extract_response = self.client.get(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/extract_text/",
        )
        self.assertEqual(extract_response.status_code, status.HTTP_200_OK)
        self.assertIn('邮箱密码登录', extract_response.data['extracted_text'])
        self.assertIn('输入错误密码提示错误原因', extract_response.data['extracted_text'])

        response = self.client.post(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/generate_testcases/",
            {'title': '邮箱与密码登录', 'project': self.project.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TestCaseGenerationTask.objects.filter(task_id=response.data['task_id']).exists())
        requirement = BusinessRequirement.objects.get(requirement_name='邮箱与密码登录')
        self.assertIn('输入正确邮箱和密码登录成功', requirement.description)

    def test_archive_document_upload_extracts_supported_inner_files(self):
        """Archive uploads should extract supported requirement files inside."""
        self.client.force_authenticate(self.user)

        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': 'Archived requirements',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'requirements.zip',
                    build_zip_requirement_bytes(),
                    content_type='application/zip',
                ),
            },
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RequirementDocument.objects.get(id=upload_response.data['id']).document_type, 'archive')

        extract_response = self.client.get(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/extract_text/",
        )
        self.assertEqual(extract_response.status_code, status.HTTP_200_OK)
        self.assertIn('docs/login.md', extract_response.data['extracted_text'])
        self.assertIn('Support email and password login', extract_response.data['extracted_text'])
        self.assertIn('validation errors', extract_response.data['extracted_text'])

    def test_tar_gz_document_upload_extracts_supported_inner_files(self):
        """tar.gz uploads should be decompressed and parsed."""
        self.client.force_authenticate(self.user)

        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': 'Tar requirements',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'requirements.tar.gz',
                    build_tar_gz_requirement_bytes(),
                    content_type='application/gzip',
                ),
            },
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RequirementDocument.objects.get(id=upload_response.data['id']).document_type, 'archive')

        extract_response = self.client.get(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/extract_text/",
        )
        self.assertEqual(extract_response.status_code, status.HTTP_200_OK)
        self.assertIn('requirements/archive.txt', extract_response.data['extracted_text'])
        self.assertIn('generate testcase from tar.gz', extract_response.data['extracted_text'])

    def test_excel_document_upload_extracts_sheet_text(self):
        """Excel uploads should be stored as requirement documents and extract sheet text."""
        self.client.force_authenticate(self.user)

        upload_response = self.client.post(
            '/api/requirement-analysis/api/documents/',
            {
                'title': 'Excel requirements',
                'project': self.project.id,
                'file': SimpleUploadedFile(
                    'requirements.xlsx',
                    build_excel_requirement_bytes(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ),
            },
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RequirementDocument.objects.get(id=upload_response.data['id']).document_type, 'excel')

        extract_response = self.client.get(
            f"/api/requirement-analysis/api/documents/{upload_response.data['id']}/extract_text/",
        )
        self.assertEqual(extract_response.status_code, status.HTTP_200_OK)
        self.assertIn('[Sheet] Requirements', extract_response.data['extracted_text'])
        self.assertIn('Email login', extract_response.data['extracted_text'])

    def test_document_default_prompt_configs_create_defaults(self):
        """需求文档创建需求和文档生成用例默认提示词应可自动恢复"""
        requirement_prompt = ensure_default_prompt_config('document_requirement_writer', created_by=self.user)
        testcase_prompt = ensure_default_prompt_config('document_testcase_writer', created_by=self.user)

        self.assertEqual(requirement_prompt.name, '默认需求文档创建需求提示词')
        self.assertEqual(requirement_prompt.prompt_type, 'document_requirement_writer')
        self.assertIn('需求文档分析与需求编写专家', requirement_prompt.content)
        self.assertEqual(testcase_prompt.name, '默认需求文档生成测试用例提示词')
        self.assertEqual(testcase_prompt.prompt_type, 'document_testcase_writer')
        self.assertIn('需求文档中提炼测试点', testcase_prompt.content)
