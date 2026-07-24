import tempfile
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.users.models import User
from apps.versions.models import Version

from .models import Defect, DefectComment
from .notification_services import resolve_frontend_base_url


class DefectCodeGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='tester', password='pass123')
        self.project = Project.objects.create(name='Defect Project', owner=self.user)
        self.version_v1 = Version.objects.create(name='V1.2.3', created_by=self.user)
        self.version_v1.projects.add(self.project)
        self.version_v2 = Version.objects.create(name='V2.0.0', created_by=self.user)
        self.version_v2.projects.add(self.project)

    def test_generates_version_based_code_with_four_digit_sequence(self):
        first_defect = Defect.objects.create(
            project=self.project,
            version=self.version_v1,
            title='First version defect',
            description='first detail',
            created_by=self.user,
        )
        second_defect = Defect.objects.create(
            project=self.project,
            version=self.version_v1,
            title='Second version defect',
            description='second detail',
            created_by=self.user,
        )

        self.assertEqual(first_defect.code, 'BUGV1.2.30001')
        self.assertEqual(second_defect.code, 'BUGV1.2.30002')

    def test_sequences_are_independent_per_version(self):
        first_v1 = Defect.objects.create(
            project=self.project,
            version=self.version_v1,
            title='V1 defect',
            description='v1 detail',
            created_by=self.user,
        )
        first_v2 = Defect.objects.create(
            project=self.project,
            version=self.version_v2,
            title='V2 defect',
            description='v2 detail',
            created_by=self.user,
        )

        self.assertEqual(first_v1.code, 'BUGV1.2.30001')
        self.assertEqual(first_v2.code, 'BUGV2.0.00001')

    def test_unversioned_defect_keeps_legacy_code_format(self):
        defect = Defect.objects.create(
            project=self.project,
            title='Legacy defect',
            description='legacy detail',
            created_by=self.user,
        )

        self.assertRegex(defect.code, r'^BUG\d{14}$')

    def test_api_create_returns_generated_version_code(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            '/api/defects/',
            {
                'project_id': self.project.id,
                'version_id': self.version_v1.id,
                'title': 'API defect',
                'description': 'API detail',
                'severity': 'high',
                'status': 'new',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['code'], 'BUGV1.2.30001')

    def test_technical_solution_design_uses_independent_code_sequence(self):
        defect = Defect.objects.create(
            project=self.project,
            version=self.version_v1,
            title='Version defect',
            description='defect detail',
            created_by=self.user,
        )
        technical_solution_design = Defect.objects.create(
            record_type=Defect.RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN,
            project=self.project,
            version=self.version_v1,
            title='Technical solution design',
            description='design detail',
            created_by=self.user,
        )

        self.assertEqual(defect.code, 'BUGV1.2.30001')
        self.assertEqual(technical_solution_design.code, 'TSDV1.2.30001')

    def test_technical_solution_design_api_is_separate_from_defect_list(self):
        self.client.force_authenticate(self.user)

        defect = Defect.objects.create(
            project=self.project,
            version=self.version_v1,
            title='Visible defect',
            description='defect detail',
            created_by=self.user,
        )
        technical_solution_design = Defect.objects.create(
            record_type=Defect.RECORD_TYPE_TECHNICAL_SOLUTION_DESIGN,
            project=self.project,
            version=self.version_v1,
            title='Visible design',
            description='design detail',
            created_by=self.user,
        )

        defect_response = self.client.get('/api/defects/')
        design_response = self.client.get('/api/defects/technical-solution-designs/')

        self.assertEqual(defect_response.status_code, 200, defect_response.data)
        self.assertEqual(design_response.status_code, 200, design_response.data)
        self.assertEqual([item['id'] for item in defect_response.data['results']], [defect.id])
        self.assertEqual([item['id'] for item in design_response.data['results']], [technical_solution_design.id])


class DefectNotificationUrlTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='notification-url-user', password='pass123')

    @override_settings(FRONTEND_BASE_URL='http://configured.example.com')
    def test_resolves_frontend_base_url_from_current_request_origin_first(self):
        request = self.client.get(
            '/api/defects/',
            HTTP_ORIGIN='https://deployed.example.com:41080',
        ).wsgi_request

        self.assertEqual(resolve_frontend_base_url(request), 'https://deployed.example.com:41080')

    @override_settings(FRONTEND_BASE_URL='http://configured.example.com')
    def test_resolves_frontend_base_url_from_referer_before_static_setting(self):
        request = self.client.get(
            '/api/defects/',
            HTTP_REFERER='https://referer.example.com/manual-testcases/defects',
        ).wsgi_request

        self.assertEqual(resolve_frontend_base_url(request), 'https://referer.example.com')


class DefectRichTextImageTests(TestCase):
    TRANSPARENT_PNG_BYTES = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff'
        b'\xff?\x00\x05\xfe\x02\xfeA\xd9\x8f\xb5\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='richtext-user', password='pass123')
        self.project = Project.objects.create(name='RichText Project', owner=self.user)
        self.version = Version.objects.create(name='V3.0.0', created_by=self.user)
        self.version.projects.add(self.project)
        self.client.force_authenticate(self.user)

    def test_detail_response_normalizes_description_and_comment_image_urls(self):
        image_path = '/media/defect_rich_text_images/2026/04/example.png'
        external_image = 'https://example.com/external.png'
        defect = Defect.objects.create(
            project=self.project,
            version=self.version,
            title='Rich text defect',
            description=(
                f'<p>描述图片<img src="{image_path}"></p>'
                f'<p>外部图片<img src="{external_image}"></p>'
            ),
            created_by=self.user,
        )
        DefectComment.objects.create(
            defect=defect,
            author=self.user,
            content=f'<p>评论图片<img src="{image_path}"></p>',
        )

        response = self.client.get(f'/api/defects/{defect.id}/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('http://testserver/media/defect_rich_text_images/2026/04/example.png', response.data['description'])
        self.assertIn(external_image, response.data['description'])
        self.assertEqual(len(response.data['comments']), 1)
        self.assertIn(
            'http://testserver/media/defect_rich_text_images/2026/04/example.png',
            response.data['comments'][0]['content'],
        )

    def test_rich_text_image_upload_returns_absolute_media_url(self):
        upload_file = SimpleUploadedFile(
            'inline-image.png',
            self.TRANSPARENT_PNG_BYTES,
            content_type='image/png',
        )

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                response = self.client.post(
                    '/api/defects/rich-text-images/',
                    {'images': [upload_file]},
                    format='multipart',
                )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['url'].startswith('http://testserver/media/defect_rich_text_images/'))

    def test_uploaded_rich_text_image_is_accessible_when_debug_is_false(self):
        upload_file = SimpleUploadedFile(
            'inline-image.png',
            self.TRANSPARENT_PNG_BYTES,
            content_type='image/png',
        )

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root, DEBUG=False):
                upload_response = self.client.post(
                    '/api/defects/rich-text-images/',
                    {'images': [upload_file]},
                    format='multipart',
                )

                self.assertEqual(upload_response.status_code, 201, upload_response.data)
                image_path = urlparse(upload_response.data['results'][0]['url']).path

                media_response = self.client.get(image_path)

        self.assertEqual(media_response.status_code, 200)


class DefectExcelImportTests(TestCase):
    TRANSPARENT_PNG_BYTES = DefectRichTextImageTests.TRANSPARENT_PNG_BYTES

    def setUp(self):
        self.client = APIClient()
        self.operator = User.objects.create_user(username='excel-import-operator', password='pass123')
        self.submitter = User.objects.create_user(
            username='excel-import-submitter',
            password='pass123',
            first_name='刘',
            last_name='佳莹',
        )
        self.project = Project.objects.create(name='物业通', owner=self.operator)
        self.version = Version.objects.create(name='V2026.04.30', created_by=self.operator)
        self.version.projects.add(self.project)
        self.client.force_authenticate(self.operator)

    def build_excel_upload(self, rows, *, image_cells=None):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = '缺陷导入'
        worksheet.append([
            '序号',
            '责任小组',
            '需求编号',
            '模块',
            '页面',
            '类型',
            '提交人',
            '问题描述',
            '预期',
            '截图1',
            '截图2',
            '截图3',
            '截图4',
            '优先级',
            '解决状态',
            '打回备注',
            '后端',
            '前端',
            '问题原因',
            '问题根因',
            '问题提交日期',
            '备注',
        ])

        for row in rows:
            worksheet.append(row)

        temp_paths = []
        try:
            for cell_ref in image_cells or []:
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_file.write(self.TRANSPARENT_PNG_BYTES)
                temp_file.close()
                temp_paths.append(temp_file.name)
                worksheet.add_image(OpenpyxlImage(temp_file.name), cell_ref)

            buffer = BytesIO()
            workbook.save(buffer)
        finally:
            for temp_path in temp_paths:
                path = Path(temp_path)
                if path.exists():
                    path.unlink()

        return SimpleUploadedFile(
            'version-defects.xlsx',
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_excel_import_creates_defects_and_maps_fields(self):
        upload = self.build_excel_upload([
            [
                1,
                '业财组',
                'SYSWIN-10001',
                '物业通-数据仓-报表中心',
                '税金报表',
                'BUG',
                '刘佳莹',
                '导入后的缺陷标题',
                '预期结果文本',
                '',
                '',
                '',
                '',
                'P2',
                '提测',
                '',
                '@廖中义',
                '@张建',
                '数据计算错误',
                '代码程序问题',
                '',
                '',
            ],
        ])

        response = self.client.post(
            '/api/defects/import-excel/',
            {
                'project_id': self.project.id,
                'version_id': self.version.id,
                'file': upload,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 1)
        defect = Defect.objects.get()
        self.assertEqual(defect.project_id, self.project.id)
        self.assertEqual(defect.version_id, self.version.id)
        self.assertEqual(defect.title, '导入后的缺陷标题')
        self.assertEqual(defect.created_by_id, self.submitter.id)
        self.assertEqual(defect.priority, 'P2')
        self.assertEqual(defect.severity, 'medium')
        self.assertEqual(defect.status, 'resolved')
        self.assertEqual(defect.requirement_id, 'SYSWIN-10001')
        self.assertEqual(defect.problem_reason, '数据计算错误')
        self.assertEqual(defect.root_cause, '代码程序问题')
        self.assertEqual(defect.frontend_developer, '张建')
        self.assertEqual(defect.backend_developer, '廖中义')
        self.assertEqual(defect.modules[0]['path'], '物业通 / 数据仓 / 报表中心')
        self.assertIn('【版本号】', defect.description)
        self.assertIn('V2026.04.30', defect.description)
        self.assertIn('【测试环境】', defect.description)
        self.assertIn('思源测试环境', defect.description)
        self.assertIn('税金报表', defect.description)
        self.assertIn('导入后的缺陷标题', defect.description)
        self.assertIn('预期结果文本', defect.description)

    def test_excel_import_embeds_images_and_falls_back_to_operator_when_submitter_missing(self):
        upload = self.build_excel_upload(
            [[
                1,
                '经营组',
                'SYSWIN-10002',
                '物业通-资产租赁',
                '租赁合同',
                'BUG',
                '不存在的提交人',
                '带图片的缺陷',
                '',
                '',
                '',
                '',
                '',
                'P3',
                '回归验证完成',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
            ]],
            image_cells=['I2', 'J2'],
        )

        with tempfile.TemporaryDirectory() as temp_media_root:
            with override_settings(MEDIA_ROOT=temp_media_root):
                response = self.client.post(
                    '/api/defects/import-excel/',
                    {
                        'project_id': self.project.id,
                        'version_id': self.version.id,
                        'file': upload,
                    },
                    format='multipart',
                )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(response.data['warning_count'], 1)
        self.assertIn('未匹配到平台用户', response.data['warnings'][0])

        defect = Defect.objects.get(requirement_id='SYSWIN-10002')
        self.assertEqual(defect.created_by_id, self.operator.id)
        self.assertEqual(defect.status, 'closed')
        self.assertIn('/media/defect_rich_text_images/', defect.description)
        self.assertGreaterEqual(defect.description.count('<img src="'), 2)
