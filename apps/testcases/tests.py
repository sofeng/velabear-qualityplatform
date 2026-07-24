import ast
import json
import os
import zipfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.users.models import PermissionItem, Role, RolePermission, User
from apps.versions.models import Version

from .models import (
    DevSelfTestRecord,
    ManualTestCaseCategory,
    ManualTestCaseMindmap,
    ManualWorkspacePageListConfig,
    PlaywrightAutomationScript,
    PlaywrightRecordingSession,
    PlaywrightRecordingStep,
    VisualFlow,
)
from .playwright_recorder import (
    build_recorder_runtime_config,
    build_recorder_novnc_url,
    can_cleanup_orphan_recorder_processes,
    cleanup_stale_recording_sessions,
    is_recorder_orphan_process,
    normalize_recorder_display_number,
    reap_recorder_child_processes,
    stop_recording_session,
)
from .xmind_requirement_import import parse_uploaded_xmind


def build_xmind_upload(root_title, *, child_titles=None, file_name='requirement-import.xmind'):
    root_topic = {
        'title': root_title,
        'children': {
            'attached': [
                {
                    'title': child_title,
                    'children': {'attached': []},
                }
                for child_title in (child_titles or [])
            ]
        },
    }
    content = json.dumps([{'rootTopic': root_topic}], ensure_ascii=False).encode('utf-8')
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('content.json', content)

    return SimpleUploadedFile(
        file_name,
        buffer.getvalue(),
        content_type='application/octet-stream',
    )


def build_nested_xmind_upload(root_title, module_title, testpoint_title, file_name='nested-import.xmind'):
    root_topic = {
        'title': root_title,
        'children': {
            'attached': [
                {
                    'title': module_title,
                    'children': {
                        'attached': [
                            {
                                'title': testpoint_title,
                                'children': {'attached': []},
                            }
                        ]
                    },
                }
            ]
        },
    }
    content = json.dumps([{'rootTopic': root_topic}], ensure_ascii=False).encode('utf-8')
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('content.json', content)
    return SimpleUploadedFile(file_name, buffer.getvalue(), content_type='application/octet-stream')


class ManualWorkspacePageListConfigAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='list-config-admin', password='pwd', is_staff=True)
        self.client.force_authenticate(self.user)

    def test_registry_exposes_stable_page_and_field_keys(self):
        response = self.client.get('/api/testcases/manual-workspace-page-list-registry/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['module_key'], 'manual-testcases')
        page_keys = {page['page_key'] for page in response.data['pages']}
        self.assertIn('project-environments', page_keys)
        project_page = next(page for page in response.data['pages'] if page['page_key'] == 'project-environments')
        field_keys = {field['field_key'] for field in project_page['fields']}
        self.assertIn('prop:project_name', field_keys)
        self.assertIn('prop:base_url', field_keys)

        mindmap_page = next(page for page in response.data['pages'] if page['page_key'] == 'mindmaps')
        mindmap_field_keys = {field['field_key'] for field in mindmap_page['fields']}
        self.assertIn('prop:name', mindmap_field_keys)
        self.assertIn('prop:frontend_name', mindmap_field_keys)
        self.assertIn('prop:backend_name', mindmap_field_keys)
        self.assertIn('prop:created_at', mindmap_field_keys)

    def test_save_and_read_config_by_storage_key(self):
        payload = {
            'module_key': 'manual-testcases',
            'page_key': 'project-environments',
            'filter_conditions': [
                {
                    'id': 'env-name-filter',
                    'field_key': 'prop:name',
                    'filter_type': 'text',
                    'operator': 'contains',
                    'placeholder': '搜索环境名称',
                    'enabled': True,
                    'order': 1,
                },
            ],
            'columns': [
                {'field_key': 'prop:name', 'visible': True, 'order': 1},
                {'field_key': 'prop:project_name', 'visible': True, 'order': 2},
                {'field_key': 'prop:base_url', 'visible': False, 'order': 3},
                {'field_key': 'label:操作', 'visible': False, 'order': 4},
            ],
        }

        save_response = self.client.put(
            '/api/testcases/manual-workspace-page-list-config/',
            payload,
            format='json',
        )
        self.assertEqual(save_response.status_code, status.HTTP_200_OK)
        self.assertEqual(save_response.data['version'], 1)
        self.assertEqual(save_response.data['columns'][0]['field_key'], 'prop:name')
        self.assertTrue(save_response.data['columns'][-1]['visible'])

        read_response = self.client.get(
            '/api/testcases/manual-workspace-page-list-config/',
            {'storage_key': 'manual-testcases.project-environments'},
        )
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertFalse(read_response.data['is_factory'])
        self.assertEqual(read_response.data['columns'][0]['field_key'], 'prop:name')

    def test_read_mindmap_config_merges_current_registry_fields(self):
        ManualWorkspacePageListConfig.objects.create(
            module_key='manual-testcases',
            page_key='mindmaps',
            filter_conditions=[],
            columns=[
                {'field_key': 'prop:requirement_key', 'visible': True, 'order': 1},
                {'field_key': 'prop:name', 'visible': True, 'order': 2},
                {'field_key': 'stale:removed-column', 'visible': True, 'order': 3},
            ],
            version=2,
            updated_by=self.user,
        )

        response = self.client.get(
            '/api/testcases/manual-workspace-page-list-config/',
            {'storage_key': 'manual-testcases.mindmaps'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        column_keys = [item['field_key'] for item in response.data['columns']]
        self.assertNotIn('stale:removed-column', column_keys)
        self.assertIn('prop:frontend_name', column_keys)
        self.assertIn('prop:backend_name', column_keys)
        self.assertIn('prop:created_at', column_keys)
        self.assertEqual(column_keys[0], 'type:selection')
        self.assertTrue(column_keys[-1].startswith('label:'))

    def test_rejects_unregistered_fields(self):
        response = self.client.put(
            '/api/testcases/manual-workspace-page-list-config/',
            {
                'module_key': 'manual-testcases',
                'page_key': 'project-environments',
                'filter_conditions': [
                    {'field_key': 'drop table', 'filter_type': 'text', 'enabled': True, 'order': 1},
                ],
                'columns': [{'field_key': 'prop:name', 'visible': True, 'order': 1}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ManualWorkspacePageListConfig.objects.exists())

    def test_rejects_stale_version(self):
        config = ManualWorkspacePageListConfig.objects.create(
            module_key='manual-testcases',
            page_key='project-environments',
            filter_conditions=[],
            columns=[{'field_key': 'prop:name', 'visible': True, 'order': 1}],
            version=3,
            updated_by=self.user,
        )

        response = self.client.put(
            '/api/testcases/manual-workspace-page-list-config/',
            {
                'module_key': config.module_key,
                'page_key': config.page_key,
                'version': 2,
                'filter_conditions': [],
                'columns': [{'field_key': 'prop:name', 'visible': True, 'order': 1}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['current_version'], 3)


class PlaywrightRecordingStateTests(TestCase):
    def test_recorder_display_number_normalization(self):
        self.assertEqual(normalize_recorder_display_number(':99'), '99')
        self.assertEqual(normalize_recorder_display_number('99.0'), '99')
        self.assertEqual(normalize_recorder_display_number('invalid'), '')

    def test_novnc_url_includes_explicit_websocket_settings(self):
        with self.settings():
            import os

            previous_origin = os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_EXTERNAL_ORIGIN')
            previous_path = os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_PATH')
            os.environ['PLAYWRIGHT_RECORDER_NOVNC_EXTERNAL_ORIGIN'] = 'http://recorder.example:46080'
            os.environ['PLAYWRIGHT_RECORDER_NOVNC_PATH'] = 'websockify'
            try:
                url = build_recorder_novnc_url()
            finally:
                if previous_origin is None:
                    os.environ.pop('PLAYWRIGHT_RECORDER_NOVNC_EXTERNAL_ORIGIN', None)
                else:
                    os.environ['PLAYWRIGHT_RECORDER_NOVNC_EXTERNAL_ORIGIN'] = previous_origin
                if previous_path is None:
                    os.environ.pop('PLAYWRIGHT_RECORDER_NOVNC_PATH', None)
                else:
                    os.environ['PLAYWRIGHT_RECORDER_NOVNC_PATH'] = previous_path

        self.assertIn('host=recorder.example', url)
        self.assertIn('port=46080', url)
        self.assertIn('path=websockify', url)
        self.assertIn('encrypt=0', url)

    def test_runtime_config_offsets_display_and_ports(self):
        import os

        previous_host_port = os.environ.get('PLAYWRIGHT_RECORDER_CDP_HOST_PORT')
        try:
            os.environ['PLAYWRIGHT_RECORDER_CDP_HOST_PORT'] = '49222'
            runtime_config = build_recorder_runtime_config(2)
        finally:
            if previous_host_port is None:
                os.environ.pop('PLAYWRIGHT_RECORDER_CDP_HOST_PORT', None)
            else:
                os.environ['PLAYWRIGHT_RECORDER_CDP_HOST_PORT'] = previous_host_port

        self.assertEqual(runtime_config.slot, 2)
        self.assertEqual(runtime_config.display, ':101')
        self.assertEqual(runtime_config.cdp_public_port, 9224)
        self.assertEqual(runtime_config.cdp_internal_port, 9335)
        self.assertEqual(runtime_config.cdp_host_port, 49224)
        self.assertEqual(runtime_config.vnc_port, 5902)
        self.assertEqual(runtime_config.novnc_port, 6082)
        self.assertEqual(runtime_config.novnc_host_port, 46082)

    def test_novnc_url_uses_runtime_host_port(self):
        runtime_config = build_recorder_runtime_config(1)
        url = build_recorder_novnc_url(runtime_config)

        self.assertIn('localhost:46081', url)
        self.assertIn('port=46081', url)

    def test_recorder_orphan_process_matching_is_scoped(self):
        self.assertTrue(is_recorder_orphan_process('Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp'))
        self.assertTrue(is_recorder_orphan_process('Xvfb :100 -screen 0 1920x1080x24 -nolisten tcp'))
        self.assertTrue(is_recorder_orphan_process('x11vnc -display :99 -rfbport 5900 -forever'))
        self.assertTrue(is_recorder_orphan_process('websockify --web /usr/share/novnc 0.0.0.0:6080 127.0.0.1:5900'))
        self.assertTrue(is_recorder_orphan_process('websockify --web /usr/share/novnc 0.0.0.0:6081 127.0.0.1:5901'))
        self.assertTrue(is_recorder_orphan_process('chromium --remote-debugging-port=9333 --remote-allow-origins=*'))
        self.assertTrue(is_recorder_orphan_process('[fcitx5] <defunct>'))
        self.assertFalse(is_recorder_orphan_process('Xvfb :120 -screen 0 1920x1080x24 -nolisten tcp'))
        self.assertFalse(is_recorder_orphan_process('python manage.py runserver 0.0.0.0:8000'))

    def test_stop_without_in_memory_runner_marks_session_completed(self):
        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-state-stop',
            name='Stop stale recording',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_RECORDING,
            metadata={'active_recorder': True},
        )

        stop_recording_session(session.session_id)

        session.refresh_from_db()
        self.assertEqual(session.status, PlaywrightRecordingSession.STATUS_COMPLETED)
        self.assertIsNotNone(session.stopped_at)
        self.assertFalse(session.metadata.get('active_recorder'))
        self.assertTrue(session.metadata.get('stop_requested'))

    def test_cleanup_stale_recording_sessions_clears_active_statuses(self):
        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-state-stale',
            name='Stale recording',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_STARTING,
            metadata={'active_recorder': True},
        )

        cleanup_stale_recording_sessions()

        session.refresh_from_db()
        self.assertEqual(session.status, PlaywrightRecordingSession.STATUS_COMPLETED)
        self.assertIsNotNone(session.stopped_at)
        self.assertFalse(session.metadata.get('active_recorder'))
        self.assertTrue(session.metadata.get('stale_recorder_cleanup'))

    def test_orphan_cleanup_guard_respects_other_active_sessions(self):
        PlaywrightRecordingSession.objects.create(
            session_id='recording-state-active-other',
            name='Active recording',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_RECORDING,
            metadata={'active_recorder': True},
        )

        self.assertFalse(can_cleanup_orphan_recorder_processes(exclude_session_id='new-recording'))

    def test_chromium_launch_uses_container_safe_args_with_desktop_access_ready(self):
        from pathlib import Path

        source = Path(__file__).with_name('playwright_recorder.py').read_text(encoding='utf-8')
        launch_index = source.index('browser = launcher.launch')
        desktop_index = source.index('desktop_processes, desktop_url, desktop_warning = self._start_desktop_access(display, desktop_env)')
        self.assertLess(desktop_index, launch_index)
        self.assertLess(source.index('desktop_env = build_recorder_desktop_env(display)'), launch_index)
        self.assertIn("'--no-sandbox'", source)
        self.assertIn("'--disable-dev-shm-usage'", source)
        self.assertIn("'--ignore-certificate-errors'", source)
        self.assertIn("'--start-fullscreen'", source)
        self.assertIn('no_viewport=True', source)
        self.assertIn("'-xkb'", source)
        self.assertIn('ignore_https_errors=should_ignore_https_errors()', source)

    def test_visual_flow_script_generator_falls_back_to_headless_without_linux_display(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'utils'
            / 'playwrightGenerator.js'
        ).read_text(encoding='utf-8')

        self.assertIn("import os", source)
        self.assertIn("import platform", source)
        self.assertIn("def resolve_browser_runtime_options(requested_headless, maximize, viewport_width, viewport_height):", source)
        self.assertIn("if platform.system() == 'Linux':", source)
        self.assertIn("has_linux_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))", source)
        self.assertIn("actual_headless = requested_headless or not has_linux_display", source)
        self.assertIn("print('No display server detected; running Playwright in headless mode.')", source)
        self.assertIn("browser = await p.${browserType}.launch(**launch_options)", source)
        self.assertIn("context = await browser.new_context(viewport=viewport, ignore_https_errors=True)", source)
        self.assertIn("context = await browser.new_context(no_viewport=True, ignore_https_errors=True)", source)
        self.assertIn("await browser.new_context(ignore_https_errors=True)", source)
        self.assertIn("def should_install_testhub_runtime_auth(target_url):", source)
        self.assertIn("TESTHUB_PLAYWRIGHT_API_ORIGIN", source)
        self.assertNotIn("if (this.currentGraphHasMaskedPasswordComponents)", source)

    def test_visual_flow_script_generator_validates_browser_start_node(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'utils'
            / 'playwrightGenerator.js'
        ).read_text(encoding='utf-8')

        self.assertIn('this.validateGraph(nodes, edges)', source)
        self.assertIn("throw new Error('流程缺少开始节点，请添加「开始」节点并设置启动 URL')", source)
        self.assertIn('流程存在未连接到开始节点的节点', source)

    def test_visual_flow_script_generator_closes_browser_without_hiding_failures(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'utils'
            / 'playwrightGenerator.js'
        ).read_text(encoding='utf-8')

        self.assertIn('browser = None', source)
        self.assertIn('        try:', source)
        self.assertIn('        finally:', source)
        self.assertIn('if browser is not None:', source)

    def test_visual_flow_script_generator_indents_custom_code_blocks(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'utils'
            / 'playwrightGenerator.js'
        ).read_text(encoding='utf-8')

        self.assertIn('this.indentPythonBlock(config.customCode', source)
        self.assertIn('indentPythonBlock(code, indentSize = 8)', source)
        self.assertIn("replace(/\\r\\n/g, '\\n')", source)

    def test_visual_flow_script_generator_uses_visible_text_reads_for_assertions(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'utils'
            / 'playwrightGenerator.js'
        ).read_text(encoding='utf-8')

        self.assertIn('async def read_testhub_visible_text(locator):', source)
        self.assertIn("actual_value = await read_testhub_visible_text(page.locator('body'))", source)
        self.assertIn("actual_value = await read_testhub_visible_text(assertion_locator)", source)
        self.assertIn("flow_vars['${outputKey}'] = await read_testhub_visible_text(page.locator('body'))", source)
        self.assertIn("flow_vars['${outputKey}'] = await read_testhub_visible_text(current_scope.locator('body'))", source)
        self.assertNotIn("page.locator('body').text_content()", source)
        self.assertNotIn('assertion_locator.text_content()', source)

    def test_playwright_script_execute_view_uses_xvfb_when_linux_display_missing(self):
        from unittest import mock

        from .views import PlaywrightScriptExecuteView

        view = PlaywrightScriptExecuteView()
        with mock.patch('apps.testcases.views.platform.system', return_value='Linux'):
            with mock.patch.dict('apps.testcases.views.os.environ', {}, clear=True):
                with mock.patch('apps.testcases.views.shutil.which', return_value='/usr/bin/xvfb-run'):
                    with mock.patch('apps.testcases.views.get_recorder_xvfb_screen_spec', return_value='1920x1080x24'):
                        command = view._build_script_command('/tmp/generated_script.py')

        self.assertEqual(
            command,
            [
                '/usr/bin/xvfb-run',
                '-a',
                '-s',
                '-screen 0 1920x1080x24',
                'python',
                '/tmp/generated_script.py',
            ],
        )

    def test_manual_mindmap_png_export_streams_huge_mindmaps_as_single_png(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'src'
            / 'views'
            / 'manual-testcases'
            / 'ManualTestCaseEditor.vue'
        ).read_text(encoding='utf-8')

        self.assertIn('serializeCurrentMindmapSvg', source)
        self.assertIn('getCurrentMindmapSvgContentBounds', source)
        self.assertIn('svgTextToFullPngBlobByTiles', source)
        self.assertIn("createPngChunk('IHDR'", source)
        self.assertIn("createPngChunk('IDAT'", source)
        self.assertIn("createPngChunk('IEND'", source)
        self.assertIn("await import('pako')", source)
        self.assertIn('streamPngTileRows', source)
        self.assertIn('const handleExportCommand = async', source)
        self.assertIn('ElLoading.service', source)
        self.assertIn('annotateCurrentMindmapSvgExportBounds', source)
        self.assertIn('pruneSvgElementForPngTile', source)
        self.assertIn('data-export-min-x', source)
        self.assertIn('已导出${scaleText}', source)
        self.assertNotIn('exportSvgTextToPngTilesZip', source)
        self.assertNotIn('高清PNG切片', source)
        self.assertNotIn("type: 'zip'", source)

    def test_playwright_script_execute_view_rewrites_legacy_visual_flow_script_for_headless_linux(self):
        from unittest import mock

        from .views import PlaywrightScriptExecuteView

        legacy_script = '''
"""
自动生成的 Playwright 测试脚本
"""
browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
context = await browser.new_context(viewport=None)
'''.strip()

        view = PlaywrightScriptExecuteView()
        with mock.patch('apps.testcases.views.platform.system', return_value='Linux'):
            with mock.patch.dict('apps.testcases.views.os.environ', {}, clear=True):
                rewritten = view._prepare_script_content(legacy_script)

        self.assertIn("launch(headless=True)", rewritten)
        self.assertNotIn("--start-maximized", rewritten)
        self.assertIn("new_context(viewport={'width': 1920, 'height': 1080})", rewritten)

    def test_playwright_script_execute_view_rewrites_localhost_urls_for_container_runtime(self):
        from unittest import mock

        from .views import PlaywrightScriptExecuteView

        script = "await page.goto('http://localhost:41080/manual-testcases/list?tab=defects')"

        view = PlaywrightScriptExecuteView()
        with mock.patch.dict(
            'apps.testcases.playwright_recorder.os.environ',
            {'PLAYWRIGHT_RECORDER_LOCALHOST_REWRITE_HOST': 'host.docker.internal'},
            clear=True,
        ):
            rewritten = view._prepare_script_content(script)

        self.assertIn(
            "http://host.docker.internal:41080/manual-testcases/list?tab=defects",
            rewritten,
        )

    def test_playwright_script_execute_view_rejects_non_string_script(self):
        from unittest import mock

        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username='script-runner',
            password='password',
        )
        client = APIClient()
        client.force_authenticate(user)

        with mock.patch('apps.testcases.views.subprocess.run') as run_mock:
            response = client.post(
                '/api/testcases/playwright-execute/',
                {'script': {'content': "print('hello')"}},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'script must be a string')
        run_mock.assert_not_called()

    def test_recorder_drains_events_from_iframes(self):
        from pathlib import Path

        source = Path(__file__).with_name('playwright_recorder.py').read_text(encoding='utf-8')
        self.assertIn('for frame in list(page.frames):', source)
        self.assertIn('self._persist_event(page, event, frame=frame)', source)
        self.assertIn('event[\'is_iframe_event\'] = not is_main', source)
        self.assertIn("'-no6'", source)

    def test_local_agent_drains_events_from_iframes(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / 'tools' / 'local_playwright_agent.py').read_text(encoding='utf-8')
        self.assertIn('def drain_page_events(page, flush_pending=False):', source)
        self.assertIn('for frame in list(page.frames):', source)
        self.assertIn('for frame, event in drain_page_events(current_page):', source)
        self.assertIn('frame=frame', source)
        self.assertIn("event['is_iframe_event'] = not is_main", source)

    def test_recording_script_captures_clickable_and_checkable_controls(self):
        from pathlib import Path

        source = Path(__file__).with_name('playwright_recorder.py').read_text(encoding='utf-8')
        self.assertIn('const findLabelControl = element =>', source)
        self.assertIn('const visibleControlProxy = (control, triggerElement = null) =>', source)
        self.assertIn('const fallbackClickElement = element =>', source)
        self.assertIn('emitCheckable(nativeControl, target, \'click\')', source)
        self.assertIn('emitRoleCheckable(roleControl, \'click\')', source)
        self.assertIn("checked ? 'check' : 'uncheck'", source)
        self.assertIn('controlSelectors: selectorCandidates(control)', source)
        self.assertIn('payload.element.cssSelector', source)

    def test_recording_action_value_keeps_boolean_state_readable(self):
        from .playwright_recorder import PlaywrightRecorder

        recorder = PlaywrightRecorder('recording-state-value')
        self.assertEqual(recorder._extract_action_value({'checked': True}), 'true')
        self.assertEqual(recorder._extract_action_value({'checked': False}), 'false')

    def test_reap_recorder_child_processes_is_safe_without_children(self):
        self.assertGreaterEqual(reap_recorder_child_processes(), 0)


class PlaywrightRecordingManagementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='recording_api_user',
            email='recording-api-user@example.com',
            password='user123456',
        )
        self.client.force_authenticate(self.user)

    def test_recording_script_skill_uses_builtin_recording_skill(self):
        from .views import DEFAULT_RECORDING_SCRIPT_SKILL_CODE, select_recording_script_skill

        selected = select_recording_script_skill()

        self.assertEqual(selected.code, DEFAULT_RECORDING_SCRIPT_SKILL_CODE)

    def test_fallback_recording_script_is_valid_local_agent_script(self):
        from .views import build_recording_script_fallback_payload

        payload = build_recording_script_fallback_payload(
            instruction='在姓名输入Alice，点击保存',
            target_url='http://127.0.0.1:8765/index.html',
            module={'module_name': '录制脚本管理'},
            skill=None,
            ai_error='no model',
        )
        script = payload['script']

        ast.parse(script)
        self.assertIn('TESTHUB_REPLAY_CDP_URL', script)
        self.assertIn('connect_over_cdp', script)
        self.assertNotIn('.launch(', script)
        self.assertNotIn('browser.close(', script)
        self.assertEqual([item['action'] for item in payload['planned_actions']], ['fill', 'click'])

    def test_local_agent_package_prefers_distribution_assets(self):
        import tempfile
        from django.test import override_settings
        from .views import LOCAL_AGENT_PACKAGE_FILES

        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = os.path.join(temp_dir, 'local-agent-package')
            tools_dir = os.path.join(temp_dir, 'tools')
            os.makedirs(package_dir)
            os.makedirs(tools_dir)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            for file_name in LOCAL_AGENT_PACKAGE_FILES:
                source_path = os.path.join(project_root, 'tools', file_name)
                with open(source_path, 'r', encoding='utf-8') as source_obj:
                    source_content = source_obj.read()
                with open(os.path.join(package_dir, file_name), 'w', encoding='utf-8') as file_obj:
                    file_obj.write(f'# package asset: {file_name}\n{source_content}')
            with open(os.path.join(tools_dir, 'local_playwright_agent.pyc'), 'wb') as file_obj:
                file_obj.write(b'\0\0\0\0')

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.get('/api/testcases/local-agent/package/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            archive = zipfile.ZipFile(BytesIO(response.content))
            names = set(archive.namelist())
            self.assertTrue(set(LOCAL_AGENT_PACKAGE_FILES).issubset(names))
            self.assertIn('install.ps1', names)
            self.assertIn('install.bat', names)
            self.assertIn('README.md', names)
            self.assertIn('# package asset: local_playwright_agent.py', archive.read('local_playwright_agent.py').decode('utf-8'))
            install_script = archive.read('install.ps1').decode('utf-8')
            self.assertIn('$installArgs', install_script)
            self.assertNotIn('-InstallDir $InstallDir', install_script)
            agent_installer = archive.read('install_local_playwright_agent.ps1').decode('utf-8')
            self.assertIn('$minPipVersion = "23.0"', agent_installer)
            self.assertIn('$minRequestsVersion = "2.31.0"', agent_installer)
            self.assertIn('$minPlaywrightVersion = "1.44.0"', agent_installer)
            self.assertIn('"requests>=$minRequestsVersion"', agent_installer)
            self.assertIn('"playwright>=$minPlaywrightVersion"', agent_installer)
            self.assertIn('agent_health_url = $agentHealthUrl', agent_installer)
            self.assertIn('configuredPlatformUrl', agent_installer)
            self.assertIn('resolvedSourcePath -ieq $resolvedDestinationPath', agent_installer)
            self.assertIn('(Join-Path $env:LOCALAPPDATA "Programs\\Python")', agent_installer)
            self.assertNotIn('Join-Path $env:LOCALAPPDATA "Programs\\Python",', agent_installer)
            self.assertIn('"TargetDir=$targetDir"', agent_installer)
            self.assertIn('function Wait-ForUsablePython', agent_installer)
            self.assertIn('Resolving installed Python', agent_installer)
            self.assertIn('App Paths\\python.exe', agent_installer)
            self.assertIn('function Install-EmbeddedPythonRuntime', agent_installer)
            self.assertIn('python-runtime', agent_installer)
            self.assertIn('get-pip.py', agent_installer)
            self.assertIn('domesticPipIndexUrls', agent_installer)
            self.assertIn('mirrors.aliyun.com/pypi/simple', agent_installer)
            self.assertIn('npmmirror.com/mirrors/playwright', agent_installer)
            self.assertIn('function Test-DependencySourceFailure', agent_installer)
            self.assertIn('function Invoke-PipCommandWithMirrorRetry', agent_installer)
            self.assertIn('function Invoke-PlaywrightInstallWithMirrorRetry', agent_installer)
            self.assertIn('pip_index_url = $script:selectedPipIndexUrl', agent_installer)
            self.assertIn('playwright_download_host = $script:selectedPlaywrightDownloadHost', agent_installer)
            self.assertIn('Lib\\site-packages', agent_installer)
            self.assertIn("New-Object System.Text.UTF8Encoding($false)", agent_installer)
            self.assertIn('[System.IO.File]::WriteAllText((Join-Path $InstallDir "agent_config.json"), $configJson, $configUtf8NoBom)', agent_installer)
            self.assertIn("print('%d.%d.%d' % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro))", agent_installer)
            self.assertIn('Falling back to an embedded Python runtime managed by TestHub Agent', agent_installer)
            self.assertNotIn('pip install --user', agent_installer)
            self.assertNotIn('Restart this terminal and run install.bat again', agent_installer)
            protocol_script = archive.read('testhub_agent_protocol.ps1').decode('utf-8')
            self.assertIn('-InstallDir $scriptDir -Python $agentPython', protocol_script)
            self.assertNotIn('-SkipDependencyInstall', protocol_script)
            agent_source = archive.read('local_playwright_agent.py').decode('utf-8')
            self.assertIn('restart_agent_service_soon(delay_seconds=1.0, platform_url=', agent_source)
            self.assertIn('-File $installer -InstallDir $installDir -Python $python -PlatformUrl $platformUrl', agent_source)
            self.assertIn("encoding='utf-8-sig'", agent_source)
            self.assertIn("'configured_platform_url': configured_platform_url", agent_source)
            self.assertIn("'platform_bound': bool(configured_platform_url)", agent_source)
            self.assertIn('def is_allowed_agent_update_origin(self, platform_url', agent_source)
            self.assertIn('return origin_matches_platform_url(origin, platform_url)', agent_source)

    def test_local_agent_package_falls_back_when_distribution_assets_are_stale(self):
        import tempfile
        from django.test import override_settings
        from .views import LOCAL_AGENT_PACKAGE_FILES

        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = os.path.join(temp_dir, 'local-agent-package')
            tools_dir = os.path.join(temp_dir, 'tools')
            os.makedirs(package_dir)
            os.makedirs(tools_dir)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            for file_name in LOCAL_AGENT_PACKAGE_FILES:
                source_path = os.path.join(project_root, 'tools', file_name)
                with open(source_path, 'r', encoding='utf-8') as source_obj:
                    source_content = source_obj.read()
                with open(os.path.join(tools_dir, file_name), 'w', encoding='utf-8') as file_obj:
                    file_obj.write(source_content)
                with open(os.path.join(package_dir, file_name), 'w', encoding='utf-8') as file_obj:
                    if file_name == 'local_playwright_agent.py':
                        file_obj.write('# stale package asset without platform binding repair\n')
                    else:
                        file_obj.write(source_content)

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.get('/api/testcases/local-agent/package/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            archive = zipfile.ZipFile(BytesIO(response.content))
            agent_source = archive.read('local_playwright_agent.py').decode('utf-8')
            self.assertNotIn('stale package asset', agent_source)
            self.assertIn("encoding='utf-8-sig'", agent_source)
            self.assertIn("'platform_bound': bool(configured_platform_url)", agent_source)
            self.assertIn('def is_allowed_agent_update_origin(self, platform_url', agent_source)

    def test_local_agent_config_loader_accepts_utf8_bom_config(self):
        import importlib.util
        import tempfile

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        agent_path = os.path.join(project_root, 'tools', 'local_playwright_agent.py')
        spec = importlib.util.spec_from_file_location('testhub_local_playwright_agent_config_for_test', agent_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        original_agent_install_dir = agent_module.agent_install_dir
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = os.path.join(temp_dir, 'agent_config.json')
                with open(config_path, 'w', encoding='utf-8-sig') as config_file:
                    json.dump({'platform_url': 'http://172.31.119.49:42380'}, config_file)
                agent_module.agent_install_dir = lambda: temp_dir

                self.assertEqual(
                    agent_module.load_agent_config().get('platform_url'),
                    'http://172.31.119.49:42380',
                )
        finally:
            agent_module.agent_install_dir = original_agent_install_dir

    def test_local_agent_update_origin_allows_only_first_time_same_platform_repair(self):
        import importlib.util

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        agent_path = os.path.join(project_root, 'tools', 'local_playwright_agent.py')
        spec = importlib.util.spec_from_file_location('testhub_local_playwright_agent_for_test', agent_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        class FakeHandler:
            def __init__(self, origin, local_origin_allowed=False):
                self.headers = {'Origin': origin}
                self.local_origin_allowed = local_origin_allowed

            def is_allowed_local_origin(self):
                return self.local_origin_allowed

        original_get_configured_platform_url = agent_module.get_configured_platform_url
        try:
            agent_module.get_configured_platform_url = lambda: ''
            self.assertTrue(agent_module.LocalAgentHandler.is_allowed_agent_update_origin(
                FakeHandler('http://172.31.119.49:42380'),
                'http://172.31.119.49:42380',
            ))
            self.assertFalse(agent_module.LocalAgentHandler.is_allowed_agent_update_origin(
                FakeHandler('http://evil.example.com'),
                'http://172.31.119.49:42380',
            ))

            agent_module.get_configured_platform_url = lambda: 'http://localhost:41080'
            self.assertFalse(agent_module.LocalAgentHandler.is_allowed_agent_update_origin(
                FakeHandler('http://172.31.119.49:42380'),
                'http://172.31.119.49:42380',
            ))
            self.assertTrue(agent_module.LocalAgentHandler.is_allowed_agent_update_origin(
                FakeHandler('http://localhost:41080', local_origin_allowed=True),
                'http://localhost:41080',
            ))
        finally:
            agent_module.get_configured_platform_url = original_get_configured_platform_url

    def test_generate_recording_script_falls_back_without_llm(self):
        response = self.client.post(
            '/api/testcases/playwright-recording-scripts/generate/',
            {
                'instruction': '在姓名输入Alice，点击保存',
                'target_url': 'http://127.0.0.1:8765/index.html',
                'module': {
                    'module_name': '录制脚本管理',
                    'module_path': '思源研发管理 / 录制 / 录制脚本管理',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['generation_source'], 'deterministic_fallback')
        self.assertEqual(response.data['capability']['code'], 'skill_playwright_recording_script_agent')
        self.assertIn('TESTHUB_REPLAY_CDP_URL', response.data['script'])
        self.assertIn('connect_over_cdp', response.data['script'])
        self.assertEqual([item['action'] for item in response.data['planned_actions']], ['fill', 'click'])

    def test_create_automation_script_persists_first_version(self):
        response = self.client.post(
            '/api/testcases/playwright-automation-scripts/',
            {
                'name': '收费管理自动化脚本',
                'instruction': '新增收费标准',
                'target_url': 'http://127.0.0.1:8765/index.html',
                'script': "print('v1')",
                'summary': '生成收费管理录制脚本',
                'warnings': ['缺少账号'],
                'planned_actions': [{'action': 'click'}],
                'generation_source': 'deterministic_fallback',
                'module': {
                    'module_name': '收费管理',
                    'module_path': '思源研发管理 / 录制 / 收费管理',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['latest_version'], 1)
        self.assertEqual(response.data['instruction'], '新增收费标准')
        self.assertEqual(response.data['version_record']['instruction'], '新增收费标准')
        self.assertEqual(response.data['version_record']['version'], 1)
        script = PlaywrightAutomationScript.objects.get(script_id=response.data['script_id'])
        self.assertEqual(script.script, "print('v1')")
        self.assertEqual(script.instruction, '新增收费标准')
        self.assertEqual(script.versions.count(), 1)
        self.assertEqual(script.versions.first().instruction, '新增收费标准')

    def test_automation_script_list_includes_descendant_modules(self):
        project = Project.objects.create(name='Recording Script Scope Project', owner=self.user)
        version = Version.objects.create(name='26-05.15', created_by=self.user)
        version.projects.add(project)
        root = ManualTestCaseCategory.objects.create(project=project, name='物业通')
        child = ManualTestCaseCategory.objects.create(project=project, parent=root, name='登录')
        other = ManualTestCaseCategory.objects.create(project=project, parent=root, name='首页')

        matching = PlaywrightAutomationScript.objects.create(
            script_id='script-descendant-login',
            name='登录录制脚本',
            target_url='http://example.com/login',
            script="print('login')",
            module={
                'project_id': project.id,
                'version_id': version.id,
                'version_name': version.name,
                'module_id': child.id,
                'module_name': child.name,
                'module_path': '物业通 / 登录',
            },
            project=project,
            version=version,
            module_id=child.id,
            module_name=child.name,
            module_path='物业通 / 登录',
        )
        PlaywrightAutomationScript.objects.create(
            script_id='script-descendant-home',
            name='首页录制脚本',
            target_url='http://example.com/home',
            script="print('home')",
            module={
                'project_id': project.id,
                'version_id': version.id,
                'version_name': version.name,
                'module_id': other.id,
                'module_name': other.name,
                'module_path': '物业通 / 首页',
            },
            project=project,
            version=version,
            module_id=other.id,
            module_name=other.name,
            module_path='物业通 / 首页',
        )

        response = self.client.get(
            '/api/testcases/playwright-automation-scripts/',
            {
                'project_id': project.id,
                'version_id': version.id,
                'module_id': root.id,
                'module_path': '物业通',
                'module_name': '物业通',
                'include_descendants': 'true',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(matching.script_id, [item['script_id'] for item in response.data['results']])

    def test_append_automation_script_version_updates_current_script(self):
        create_response = self.client.post(
            '/api/testcases/playwright-automation-scripts/',
            {
                'name': '收费管理自动化脚本',
                'target_url': 'http://127.0.0.1:8765/index.html',
                'script': "print('v1')",
            },
            format='json',
        )
        script_id = create_response.data['script_id']

        response = self.client.post(
            f'/api/testcases/playwright-automation-scripts/{script_id}/versions/',
            {
                'script': "print('v2')",
                'change_summary': '更新保存脚本',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['version']['version'], 2)
        script = PlaywrightAutomationScript.objects.get(script_id=script_id)
        self.assertEqual(script.latest_version, 2)
        self.assertEqual(script.script, "print('v2')")
        self.assertEqual(list(script.versions.order_by('version').values_list('version', flat=True)), [1, 2])

    def test_restore_automation_script_version_creates_new_current_version(self):
        create_response = self.client.post(
            '/api/testcases/playwright-automation-scripts/',
            {
                'name': '收费管理自动化脚本',
                'target_url': 'http://127.0.0.1:8765/index.html',
                'script': "print('v1')",
            },
            format='json',
        )
        script_id = create_response.data['script_id']
        self.client.post(
            f'/api/testcases/playwright-automation-scripts/{script_id}/versions/',
            {'script': "print('v2')"},
            format='json',
        )

        response = self.client.post(
            f'/api/testcases/playwright-automation-scripts/{script_id}/versions/1/restore/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['script']['latest_version'], 3)
        script = PlaywrightAutomationScript.objects.get(script_id=script_id)
        self.assertEqual(script.script, "print('v1')")
        self.assertEqual(script.versions.count(), 3)

    def test_recording_list_supports_pagination(self):
        from datetime import timedelta

        from django.utils import timezone

        base_time = timezone.now()
        for index in range(3):
            PlaywrightRecordingSession.objects.create(
                session_id=f'recording-api-{index}',
                name=f'Recording {index}',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
                started_at=base_time + timedelta(minutes=index),
                stopped_at=base_time + timedelta(minutes=index, seconds=30),
            )

        response = self.client.get(
            '/api/testcases/playwright-recordings/',
            {'page': 2, 'page_size': 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('recorder_settings', response.data)
        self.assertIn('active_session_ids', response.data)

    def test_recording_list_includes_created_visual_flow(self):
        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-with-flow',
            name='Recording With Flow',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
        )
        VisualFlow.objects.create(
            flow_id='flow-from-recording',
            name='Recording Flow',
            source=VisualFlow.SOURCE_RECORDING,
            status=VisualFlow.STATUS_DRAFT,
            target_url='http://example.com',
            browser_type='chromium',
            recording_session=session,
            created_by=self.user,
        )

        response = self.client.get('/api/testcases/playwright-recordings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(item for item in response.data['results'] if item['session_id'] == session.session_id)
        self.assertTrue(row['has_visual_flow'])
        self.assertEqual(row['visual_flow_id'], 'flow-from-recording')
        self.assertEqual(row['visual_flow_name'], 'Recording Flow')

    def test_recording_allure_report_generates_static_artifacts(self):
        import os
        import tempfile

        from django.test import override_settings

        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-allure-report',
            name='Recording Allure Report',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
            metadata={
                'module': {
                    'module_name': '录制结果管理',
                    'module_path': '思源研发管理 / 录制 / 录制结果管理',
                }
            },
        )
        PlaywrightRecordingStep.objects.create(
            session=session,
            step_number=1,
            action_type='click',
            action_value='保存',
            page_url='http://example.com',
            page_title='Example',
            element={'tag': 'button', 'text': '保存'},
            selectors=[{'type': 'text', 'value': '保存'}],
            raw_event={'type': 'click', 'element': {'text': '保存'}},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, 'playwright_snapshot'), exist_ok=True)
            with override_settings(BASE_DIR=temp_dir, MEDIA_ROOT=temp_dir):
                response = self.client.post(
                    '/api/testcases/playwright-recordings/recording-allure-report/allure-report/',
                    {},
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['summary']['total'], 1)
                self.assertIn('/media/allure-reports/recording_recording-allure-report/summary.html', response.data['summary_url'])
                self.assertTrue(os.path.exists(os.path.join(
                    temp_dir,
                    'allure-reports',
                    'recording_recording-allure-report',
                    'summary.html',
                )))
                result_files = [
                    name for name in os.listdir(os.path.join(
                        temp_dir,
                        'allure-results',
                        'recording_recording-allure-report',
                    ))
                    if name.endswith('-result.json')
                ]
                self.assertEqual(len(result_files), 1)

        session.refresh_from_db()
        self.assertEqual(session.metadata['allure_report']['step_count'], 1)
        self.assertTrue(session.metadata['allure_report']['summary_url'].endswith('/summary.html'))

    def test_start_recording_requires_selected_directory_node(self):
        response = self.client.post(
            '/api/testcases/playwright-recordings/',
            {
                'name': 'No Directory Recording',
                'target_url': 'http://example.com',
                'browser_type': 'chromium',
                'recording_method': PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('目录树', response.data['error'])

    def test_recording_list_filters_by_module_path_when_module_id_missing(self):
        matching = PlaywrightRecordingSession.objects.create(
            session_id='recording-module-path-match',
            name='Path Match Recording',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
            metadata={
                'module': {
                    'project_id': 1,
                    'module_name': '录制结果管理',
                    'module_path': '思源研发管理 / 录制 / 录制结果管理',
                }
            },
        )
        PlaywrightRecordingSession.objects.create(
            session_id='recording-module-path-other',
            name='Other Recording',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
            metadata={
                'module': {
                    'project_id': 1,
                    'module_name': '其他页面',
                    'module_path': '思源研发管理 / 录制 / 其他页面',
                }
            },
        )

        response = self.client.get(
            '/api/testcases/playwright-recordings/',
            {
                'project_id': 1,
                'module_id': 999,
                'module_path': '思源研发管理 / 录制 / 录制结果管理',
                'module_name': '录制结果管理',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['session_id'] for item in response.data['results']], [matching.session_id])

    def test_snapshot_list_filters_by_module_path_when_module_id_missing(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import save_playwright_snapshot_metadata

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            for filename in ('match.yml', 'other.yml'):
                with open(os.path.join(snapshot_dir, filename), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write('- document:\n')
            with override_settings(BASE_DIR=temp_dir):
                save_playwright_snapshot_metadata({
                    'match.yml': {
                        'page_name': '录制结果管理',
                        'project_id': 1,
                        'module_name': '录制结果管理',
                        'module_path': '思源研发管理 / 录制 / 录制结果管理',
                    },
                    'other.yml': {
                        'page_name': '其他页面',
                        'project_id': 1,
                        'module_name': '其他页面',
                        'module_path': '思源研发管理 / 录制 / 其他页面',
                    },
                })
                response = self.client.get(
                    '/api/testcases/playwright-snapshots/',
                    {
                        'project_id': 1,
                        'module_id': 999,
                        'module_path': '思源研发管理 / 录制 / 录制结果管理',
                        'module_name': '录制结果管理',
                    },
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['filename'] for item in response.data['results']], ['match.yml'])

    def test_snapshot_metadata_persists_version_fields(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import load_playwright_snapshot_metadata, save_playwright_snapshot_metadata

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            with open(os.path.join(snapshot_dir, 'versioned.yml'), 'w', encoding='utf-8') as snapshot_file:
                snapshot_file.write('- document:\n')

            with override_settings(BASE_DIR=temp_dir):
                save_playwright_snapshot_metadata({
                    'versioned.yml': {
                        'page_name': '登录',
                        'project_id': 1,
                        'version_id': 6,
                        'version_name': '26-05.15',
                        'module_name': '登录',
                        'module_path': '物业通 / 登录',
                    },
                })
                metadata = load_playwright_snapshot_metadata()
                response = self.client.get(
                    '/api/testcases/playwright-snapshots/',
                    {'project_id': 1, 'version_id': 6, 'module_path': '物业通 / 登录'},
                )

        self.assertEqual(metadata['versioned.yml']['version_id'], 6)
        self.assertEqual(metadata['versioned.yml']['version_name'], '26-05.15')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['version_id'], 6)

    def test_snapshot_list_uses_recording_module_for_descendant_filter(self):
        import os
        import tempfile

        from django.test import override_settings

        project = Project.objects.create(name='Snapshot Scope Project', owner=self.user)
        version = Version.objects.create(name='26-05.15', created_by=self.user)
        version.projects.add(project)
        root = ManualTestCaseCategory.objects.create(project=project, name='物业通')
        child = ManualTestCaseCategory.objects.create(project=project, parent=root, name='登录')
        other = ManualTestCaseCategory.objects.create(project=project, parent=root, name='首页')
        matching_session = PlaywrightRecordingSession.objects.create(
            session_id='snapshot-child-session',
            name='Child Snapshot Recording',
            target_url='http://example.com/login',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
            metadata={
                'module': {
                    'project_id': project.id,
                    'version_id': version.id,
                    'version_name': version.name,
                    'module_id': child.id,
                    'module_name': child.name,
                    'module_path': '物业通 / 登录',
                }
            },
        )
        other_session = PlaywrightRecordingSession.objects.create(
            session_id='snapshot-other-session',
            name='Other Snapshot Recording',
            target_url='http://example.com/home',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
            metadata={
                'module': {
                    'project_id': project.id,
                    'version_id': version.id,
                    'version_name': version.name,
                    'module_id': other.id,
                    'module_name': other.name,
                    'module_path': '物业通 / 首页',
                }
            },
        )
        PlaywrightRecordingStep.objects.create(
            session=matching_session,
            step_number=1,
            action_type='click',
            snapshot_filename='recording-snapshot-child-session-step-0001.yml',
        )
        PlaywrightRecordingStep.objects.create(
            session=other_session,
            step_number=1,
            action_type='click',
            snapshot_filename='recording-snapshot-other-session-step-0001.yml',
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            for filename in (
                'recording-snapshot-child-session-step-0001.yml',
                'recording-snapshot-other-session-step-0001.yml',
            ):
                with open(os.path.join(snapshot_dir, filename), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write('- document:\n')

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.get(
                    '/api/testcases/playwright-snapshots/',
                    {
                        'project_id': project.id,
                        'version_id': version.id,
                        'module_id': root.id,
                        'module_path': '物业通',
                        'module_name': '物业通',
                        'include_descendants': 'true',
                        'sort_by': 'name_asc',
                    },
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['filename'] for item in response.data['results']],
            [
                'recording-snapshot-child-session-step-0001.yml',
                'recording-snapshot-other-session-step-0001.yml',
            ],
        )
        self.assertEqual(response.data['results'][0]['module_path'], '物业通 / 登录')

    def test_snapshot_list_ignores_non_utf8_metadata_file(self):
        import os
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            with open(os.path.join(snapshot_dir, '.snapshot-meta.json'), 'wb') as meta_file:
                meta_file.write(b'{"broken": "\xb3"}')
            with open(os.path.join(snapshot_dir, 'snapshot.yml'), 'w', encoding='utf-8') as snapshot_file:
                snapshot_file.write('- document:\n')

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.get('/api/testcases/playwright-snapshots/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['filename'] for item in response.data['results']], ['snapshot.yml'])

    def test_visual_flow_list_filters_by_module_path_and_saves_module_metadata(self):
        matching = VisualFlow.objects.create(
            flow_id='flow-module-path-match',
            name='Path Match Flow',
            source=VisualFlow.SOURCE_MANUAL,
            status=VisualFlow.STATUS_DRAFT,
            metadata={
                'module': {
                    'project_id': 1,
                    'module_name': '录制结果管理',
                    'module_path': '思源研发管理 / 录制 / 录制结果管理',
                }
            },
        )
        VisualFlow.objects.create(
            flow_id='flow-module-path-other',
            name='Other Flow',
            source=VisualFlow.SOURCE_MANUAL,
            status=VisualFlow.STATUS_DRAFT,
            metadata={
                'module': {
                    'project_id': 1,
                    'module_name': '其他页面',
                    'module_path': '思源研发管理 / 录制 / 其他页面',
                }
            },
        )

        response = self.client.get(
            '/api/testcases/visual-flows/',
            {
                'project_id': 1,
                'module_id': 999,
                'module_path': '思源研发管理 / 录制 / 录制结果管理',
                'module_name': '录制结果管理',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['flow_id'] for item in response.data['results']], [matching.flow_id])
        self.assertEqual(response.data['results'][0]['module_path'], '思源研发管理 / 录制 / 录制结果管理')

        create_response = self.client.post(
            '/api/testcases/visual-flows/',
            {
                'name': 'Created With Module',
                'source': VisualFlow.SOURCE_MANUAL,
                'module_path': '思源研发管理 / 录制 / 新建页面',
                'module_name': '新建页面',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['module_path'], '思源研发管理 / 录制 / 新建页面')

    def test_visual_flow_list_supports_pagination(self):
        for index in range(3):
            VisualFlow.objects.create(
                flow_id=f'flow-api-{index}',
                name=f'Flow {index}',
                description=f'Description {index}',
                source=VisualFlow.SOURCE_MANUAL,
                status=VisualFlow.STATUS_DRAFT,
                target_url='http://example.com',
                browser_type='chromium',
                created_by=self.user,
            )

        response = self.client.get(
            '/api/testcases/visual-flows/',
            {'page': 2, 'page_size': 2},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 1)

    def test_snapshot_list_supports_pagination(self):
        import os
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            for index in range(3):
                with open(os.path.join(snapshot_dir, f'page-{index}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(f'page: {index}\n')

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.get(
                    '/api/testcases/playwright-snapshots/',
                    {'page': 2, 'page_size': 1},
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_recording_settings_respect_active_sessions_and_capacity(self):
        import os
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = os.path.join(temp_dir, 'playwright-recording-settings.json')
            env = {
                'PLAYWRIGHT_RECORDER_SETTINGS_FILE': settings_file,
                'PLAYWRIGHT_RECORDER_MAX_SESSIONS': '5',
                'PLAYWRIGHT_RECORDER_CDP_PORT': '9222',
                'PLAYWRIGHT_RECORDER_CDP_PORT_END': '9223',
            }

            with mock.patch.dict(os.environ, env, clear=True):
                for index in range(2):
                    PlaywrightRecordingSession.objects.create(
                        session_id=f'recording-settings-{index}',
                        name=f'Active Recording {index}',
                        target_url='http://example.com',
                        browser_type='chromium',
                        status=PlaywrightRecordingSession.STATUS_RECORDING,
                    )

                response = self.client.get('/api/testcases/playwright-recordings/settings/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['active_count'], 2)
                self.assertEqual(response.data['max_sessions'], 2)
                self.assertEqual(response.data['capacity'], 2)

                response = self.client.patch(
                    '/api/testcases/playwright-recordings/settings/',
                    {'max_sessions': 1},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('活动录制会话', response.data['error'])

                response = self.client.patch(
                    '/api/testcases/playwright-recordings/settings/',
                    {'max_sessions': 3},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('端口容量', response.data['error'])

                response = self.client.patch(
                    '/api/testcases/playwright-recordings/settings/',
                    {'max_sessions': 2},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['max_sessions'], 2)
                self.assertEqual(response.data['configured_max_sessions'], 2)

    def test_identify_junk_steps_marks_intermediate_fill_and_noop_click(self):
        import os
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-junk',
                name='Recording Junk',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number, content in (
                (1, 'page: before\n'),
                (2, 'page: before\n'),
                (3, 'page: after\n'),
                (4, 'page: after\n'),
            ):
                with open(os.path.join(snapshot_dir, f'recording-recording-junk-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)
            for step_number, value in ((1, 'a'), (2, 'ab')):
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type='fill',
                    action_value=value,
                    page_url='http://example.com',
                    page_title='Example',
                    element={'tag': 'input', 'id': 'keyword'},
                    selectors=[{'type': 'id', 'value': '#keyword'}],
                )
            for step_number, element_id in ((3, 'open-detail'), (4, 'confirm-noop')):
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type='click',
                    page_url='http://example.com',
                    page_title='Example',
                    element={'tag': 'button', 'id': element_id},
                    selectors=[{'type': 'id', 'value': f'#{element_id}'}],
                )

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.post('/api/testcases/playwright-recordings/recording-junk/identify-junk-steps/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reasons = {item['step_number']: item['reason'] for item in response.data['junk_steps']}
        self.assertEqual(reasons[1], 'continuous_fill_intermediate')
        self.assertEqual(reasons[4], 'noop_click_same_snapshot')

    def test_identify_junk_steps_keeps_click_followed_by_page_change(self):
        import os
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-click-navigation',
                name='Recording Click Navigation',
                target_url='http://example.com/login',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number, content in (
                (1, 'page: login\n'),
                (2, 'page: login\n'),
                (3, 'page: home\n'),
            ):
                with open(os.path.join(snapshot_dir, f'recording-recording-click-navigation-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=1,
                action_type='fill',
                action_value='admin',
                page_url='http://example.com/login',
                page_title='Login',
                element={'tag': 'input', 'id': 'username'},
                selectors=[{'type': 'id', 'value': '#username'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=2,
                action_type='click',
                page_url='http://example.com/login',
                page_title='Login',
                element={'tag': 'button', 'id': 'login', 'text': 'Login'},
                selectors=[{'type': 'id', 'value': '#login'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=3,
                action_type='click',
                page_url='http://example.com/home',
                page_title='Home',
                element={'tag': 'button', 'id': 'open-menu', 'text': 'Open'},
                selectors=[{'type': 'id', 'value': '#open-menu'}],
            )

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.post('/api/testcases/playwright-recordings/recording-click-navigation/identify-junk-steps/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reasons = {item['step_number']: item['reason'] for item in response.data['junk_steps']}
        self.assertNotIn(2, reasons)

    def test_identify_junk_steps_filters_container_clicks_but_keeps_command_buttons(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-container-command',
                name='Recording Container Command',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number in (1, 2, 3):
                with open(os.path.join(snapshot_dir, f'recording-recording-container-command-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write('page: same\n- button "确定"\n')
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=1,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={'tag': 'span', 'text': '详情'},
                selectors=[{'type': 'text', 'value': 'text="详情"'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=2,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={'tag': 'button', 'role': 'button', 'text': '确定'},
                selectors=[{'type': 'text', 'value': 'button:has-text("确定")'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=3,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={
                    'tag': 'html',
                    'text': '返回门户 服务台 数据仓 资产管理 基础档案 仪表档案 空间档案 客户档案',
                    'rect': {'x': 0, 'y': 0, 'width': 1680, 'height': 985},
                },
                selectors=[{'type': 'css', 'value': 'html:nth-of-type(1)'}],
            )

            with override_settings(BASE_DIR=temp_dir):
                response = self.client.post('/api/testcases/playwright-recordings/recording-container-command/identify-junk-steps/')
                payload = build_recording_flow_data(session)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reasons = {item['step_number']: item['reason'] for item in response.data['junk_steps']}
        self.assertNotIn(2, reasons)
        self.assertEqual(reasons[3], 'generic_container_click')

        page_cells = [
            cell
            for cell in payload['graph_data']['cells']
            if cell.get('data', {}).get('type') == 'page'
        ]
        step_numbers = [
            component['config'].get('recordingStepNumber')
            for page in page_cells
            for component in page['data']['config']['innerComponents']
            if component['type'] != 'iframe'
        ]
        self.assertEqual(step_numbers, [1, 2])

    def test_batch_delete_recording_steps_renumbers_remaining_steps(self):
        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-delete-steps',
            name='Recording Delete Steps',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
        )
        steps = [
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=index,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={'tag': 'button', 'id': f'button-{index}'},
            )
            for index in range(1, 5)
        ]

        response = self.client.post(
            '/api/testcases/playwright-recordings/recording-delete-steps/steps/batch-delete/',
            {'step_ids': [steps[1].id, steps[2].id]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        remaining_numbers = list(session.steps.order_by('step_number').values_list('step_number', flat=True))
        self.assertEqual(remaining_numbers, [1, 2])

    def test_recording_flow_filters_junk_steps_from_components(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-flow-filter',
                name='Recording Flow Filter',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number, content in (
                (1, 'page: input\n'),
                (2, 'page: input\n'),
                (3, 'page: after\n'),
                (4, 'page: after\n'),
            ):
                with open(os.path.join(snapshot_dir, f'recording-recording-flow-filter-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)
            for step_number, value in ((1, 'a'), (2, 'ab')):
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type='fill',
                    action_value=value,
                    page_url='http://example.com',
                    page_title='Example',
                    element={'tag': 'input', 'id': 'keyword'},
                    selectors=[{'type': 'id', 'value': '#keyword'}],
                )
            for step_number, element_id in ((3, 'open-detail'), (4, 'confirm-noop')):
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type='click',
                    page_url='http://example.com',
                    page_title='Example',
                    element={'tag': 'button', 'id': element_id},
                    selectors=[{'type': 'id', 'value': f'#{element_id}'}],
                )

            with override_settings(BASE_DIR=temp_dir):
                payload = build_recording_flow_data(session)

        page_cells = [
            cell
            for cell in payload['graph_data']['cells']
            if cell.get('data', {}).get('type') == 'page'
        ]
        components = [
            component
            for page in page_cells
            for component in page['data']['config']['innerComponents']
        ]
        step_numbers = [
            component['config'].get('recordingStepNumber')
            for component in components
            if component['type'] != 'iframe'
        ]

        self.assertEqual(step_numbers, [2, 3])
        self.assertEqual(payload['snapshot_summary']['total_step_count'], 4)
        self.assertEqual(payload['snapshot_summary']['flow_step_count'], 2)
        self.assertEqual(payload['snapshot_summary']['filtered_step_count'], 2)
        filtered_reasons = {item['step_number']: item['reason'] for item in payload['snapshot_summary']['filtered_steps']}
        self.assertEqual(filtered_reasons[1], 'continuous_fill_intermediate')
        self.assertEqual(filtered_reasons[4], 'noop_click_same_snapshot')

    def test_recording_flow_groups_steps_by_system_page_scope_not_snapshot_hash(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-system-page-flow',
                name='Recording System Page Flow',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
                metadata={
                    'module': {
                        'project_id': 1,
                        'module_id': 10,
                        'module_name': '录制结果管理',
                        'module_path': '思源研发管理 / 录制 / 录制结果管理',
                    }
                },
            )
            for step_number, content in (
                (1, '- document:\n  - textbox "关键字" [id=keyword]\n'),
                (2, '- document:\n  - textbox "关键字" [id=keyword]\n  - button "查询" [id=search]\n  - table "结果已刷新"\n'),
                (3, '- document:\n  - checkbox "只看失败" [id=failed-only]\n  - table "结果再次刷新"\n'),
            ):
                with open(os.path.join(snapshot_dir, f'recording-recording-system-page-flow-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)

            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=1,
                action_type='fill',
                action_value='流程',
                page_url='http://example.com/recordings?page=1',
                page_title='录制结果管理',
                element={'tag': 'input', 'id': 'keyword'},
                selectors=[{'type': 'id', 'value': '#keyword'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=2,
                action_type='click',
                page_url='http://example.com/recordings?page=2',
                page_title='录制结果管理',
                element={'tag': 'button', 'id': 'search', 'text': '查询'},
                selectors=[{'type': 'id', 'value': '#search'}],
            )
            PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=3,
                action_type='check',
                action_value='true',
                page_url='http://example.com/recordings?page=2',
                page_title='录制结果管理',
                element={'tag': 'input', 'type': 'checkbox', 'id': 'failed-only', 'text': '只看失败'},
                selectors=[{'type': 'id', 'value': '#failed-only'}],
            )

            with override_settings(BASE_DIR=temp_dir):
                payload = build_recording_flow_data(session)

        page_cells = [
            cell
            for cell in payload['graph_data']['cells']
            if cell.get('data', {}).get('type') == 'page'
        ]
        components = page_cells[0]['data']['config']['innerComponents']
        actionable_components = [component for component in components if component['type'] != 'iframe']

        self.assertEqual(len(page_cells), 1)
        self.assertEqual([component['config']['recordingStepNumber'] for component in actionable_components], [1, 2, 3])
        self.assertEqual(page_cells[0]['data']['config']['recordingPagePath'], '思源研发管理 / 录制 / 录制结果管理')
        self.assertEqual(payload['snapshot_summary']['grouping_strategy'], 'system_page')
        self.assertEqual(payload['snapshot_summary']['snapshots'][0]['snapshot_count'], 3)
        self.assertEqual(
            actionable_components[1]['config']['recordingSnapshotFile'],
            'recording-recording-system-page-flow-step-0002.yml',
        )
        self.assertIn('contentHash', actionable_components[1]['config']['recordingSnapshotRef'])

    def test_recording_flow_url_identity_does_not_split_when_title_changes(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-title-change-flow',
                name='Recording Title Change Flow',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number, title in ((1, '列表 10 条'), (2, '列表 11 条')):
                with open(os.path.join(snapshot_dir, f'recording-recording-title-change-flow-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(f'- document:\n  - button "{title}" [id=refresh]\n')
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type='click',
                    page_url='http://example.com/recordings?page=1',
                    page_title=title,
                    element={'tag': 'button', 'id': 'refresh', 'text': '刷新'},
                    selectors=[{'type': 'id', 'value': '#refresh'}],
                )

            with override_settings(BASE_DIR=temp_dir):
                payload = build_recording_flow_data(session)

        page_cells = [
            cell
            for cell in payload['graph_data']['cells']
            if cell.get('data', {}).get('type') == 'page'
        ]
        self.assertEqual(len(page_cells), 1)
        self.assertEqual(
            page_cells[0]['data']['config']['recordingPageIdentity'],
            'url:http://example.com/recordings',
        )

    def test_recording_flow_filters_real_login_noise_and_groups_by_selected_page(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-real-login-noise',
                name='Recording Real Login Noise',
                target_url='http://localhost:41080/login',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
                metadata={
                    'module': {
                        'project_id': 1,
                        'module_id': 10,
                        'module_name': 'test',
                        'module_path': '物业通 / 录制快照 / test',
                    }
                },
            )
            login_empty = '- document:\n  - textbox "请输入用户名"\n  - textbox "请输入密码"\n  - button "登录"\n'
            login_user_partial = '- document:\n  - textbox "请输入用户名": adm\n  - textbox "请输入密码"\n  - button "登录"\n'
            login_user_done = '- document:\n  - textbox "请输入用户名": admin\n  - textbox "请输入密码"\n  - button "登录"\n'
            login_password_done = '- document:\n  - textbox "请输入用户名": admin\n  - textbox "请输入密码": ********\n  - button "登录"\n'
            home_snapshot = '- document:\n  - heading "AIOps 测试平台"\n  - button "思源研发管理"\n  - alert:\n    - paragraph: 登录成功\n'
            for step_number, content in (
                (1, login_empty),
                (2, login_user_partial),
                (3, login_user_done),
                (4, login_user_done),
                (5, login_user_done),
                (6, login_user_done),
                (7, login_password_done),
                (8, home_snapshot),
                (9, home_snapshot),
            ):
                with open(os.path.join(snapshot_dir, f'recording-recording-real-login-noise-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(content)

            username_element = {
                'tag': 'input',
                'type': 'text',
                'role': 'textbox',
                'id': 'username',
                'text': '请输入用户名',
                'placeholder': '请输入用户名',
                'cssSelector': 'input#username',
                'xpath': '/html/body/form/input[1]',
            }
            password_element = {
                'tag': 'input',
                'type': 'password',
                'role': 'textbox',
                'id': 'password',
                'text': '请输入密码',
                'placeholder': '请输入密码',
                'cssSelector': 'input#password',
                'xpath': '/html/body/form/input[2]',
            }
            login_button = {
                'tag': 'button',
                'type': 'button',
                'role': 'button',
                'text': '登录',
                'cssSelector': 'button.login',
                'xpath': '/html/body/form/button',
            }

            step_payloads = [
                (1, 'click', '', 'http://localhost:41080/login', username_element, {}),
                (2, 'click', '', 'http://localhost:41080/login', {**username_element, 'value': 'a'}, {}),
                (3, 'fill', 'admin', 'http://localhost:41080/login', {**username_element, 'value': 'admin'}, {'value': 'admin'}),
                (4, 'fill', 'admin', 'http://localhost:41080/login', {**username_element, 'value': 'admin'}, {'value': 'admin'}),
                (5, 'press', 'Tab', 'http://localhost:41080/login', {**username_element, 'value': 'admin'}, {'key': 'Tab'}),
                (6, 'fill', 'admin', 'http://localhost:41080/login', {**username_element, 'value': 'admin'}, {'value': 'admin'}),
                (7, 'fill', '********', 'http://localhost:41080/login', password_element, {'value': '********'}),
                (8, 'fill', '********', 'http://localhost:41080/home', password_element, {'value': '********'}),
                (9, 'click', '', 'http://localhost:41080/home', login_button, {}),
            ]
            for step_number, action, value, url, element, extra_event in step_payloads:
                PlaywrightRecordingStep.objects.create(
                    session=session,
                    step_number=step_number,
                    action_type=action,
                    action_value=value,
                    page_url=url,
                    page_title='AIDevTestOps - AI一体化测试平台',
                    element=element,
                    selectors=[{'type': 'css', 'value': element.get('cssSelector')}],
                    raw_event={
                        'url': url,
                        'frame': {'url': url, 'name': '', 'isMain': True},
                        'frame_url': url,
                        'title': 'AIDevTestOps - AI一体化测试平台',
                        'element': element,
                        'selectors': [{'type': 'css', 'value': element.get('cssSelector')}],
                        **extra_event,
                    },
                )

            with override_settings(BASE_DIR=temp_dir):
                payload = build_recording_flow_data(session)

        page_cells = [
            cell
            for cell in payload['graph_data']['cells']
            if cell.get('data', {}).get('type') == 'page'
        ]
        components = page_cells[0]['data']['config']['innerComponents']
        actionable_components = [component for component in components if component['type'] != 'iframe']
        step_numbers = [component['config']['recordingStepNumber'] for component in actionable_components]
        filtered_reasons = {
            item['step_number']: item['reason']
            for item in payload['snapshot_summary']['filtered_steps']
        }

        self.assertEqual(len(page_cells), 1)
        self.assertEqual(page_cells[0]['data']['config']['recordingPageIdentity'], 'system-page:物业通 / 录制快照 / test')
        self.assertEqual(step_numbers, [4, 7, 9])
        self.assertEqual(payload['snapshot_summary']['flow_step_count'], 3)
        self.assertEqual(payload['snapshot_summary']['filtered_step_count'], 6)
        self.assertEqual(filtered_reasons[1], 'focus_click_before_input')
        self.assertEqual(filtered_reasons[2], 'focus_click_before_input')
        self.assertEqual(filtered_reasons[3], 'duplicate_fill_same_element')
        self.assertEqual(filtered_reasons[5], 'noop_press_same_snapshot')
        self.assertEqual(filtered_reasons[6], 'duplicate_value_same_element')
        self.assertEqual(filtered_reasons[8], 'target_missing_after_value_action')

    def test_create_recording_flow_updates_existing_flow_after_step_changes(self):
        import os
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, 'playwright_snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            session = PlaywrightRecordingSession.objects.create(
                session_id='recording-regenerate-flow',
                name='Recording Regenerate Flow',
                target_url='http://example.com',
                browser_type='chromium',
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
            )
            for step_number in (1, 2):
                with open(os.path.join(snapshot_dir, f'recording-recording-regenerate-flow-step-{step_number:04d}.yml'), 'w', encoding='utf-8') as snapshot_file:
                    snapshot_file.write(f'page: step {step_number}\n')
            step_one = PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=1,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={'tag': 'button', 'id': 'first'},
                selectors=[{'type': 'id', 'value': '#first'}],
            )
            step_two = PlaywrightRecordingStep.objects.create(
                session=session,
                step_number=2,
                action_type='click',
                page_url='http://example.com',
                page_title='Example',
                element={'tag': 'button', 'id': 'second'},
                selectors=[{'type': 'id', 'value': '#second'}],
            )

            with override_settings(BASE_DIR=temp_dir):
                first_response = self.client.post(
                    '/api/testcases/playwright-recordings/recording-regenerate-flow/create-flow/',
                    {'force_new': False},
                    format='json',
                )
                step_two.delete()
                step_one.step_number = 1
                step_one.save(update_fields=['step_number'])
                second_response = self.client.post(
                    '/api/testcases/playwright-recordings/recording-regenerate-flow/create-flow/',
                    {'force_new': False},
                    format='json',
                )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data['flow']['flow_id'], first_response.data['flow']['flow_id'])
        self.assertEqual(VisualFlow.objects.filter(recording_session=session).count(), 1)
        summary = second_response.data['flow']['snapshot_summary']
        self.assertEqual(summary['total_step_count'], 1)
        self.assertEqual(summary['flow_step_count'], 1)

    def test_recording_flow_places_iframe_step_component_inside_iframe(self):
        import os
        import tempfile

        from django.test import override_settings

        from .views import build_recording_flow_data

        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-iframe-flow',
            name='Recording Iframe Flow',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
        )
        step = PlaywrightRecordingStep.objects.create(
            session=session,
            step_number=1,
            action_type='click',
            page_url='http://example.com',
            page_title='Example',
            element={'tag': 'button', 'id': 'inside-frame'},
            selectors=[{'type': 'id', 'value': '#inside-frame'}],
            raw_event={
                'is_iframe_event': True,
                'frame': {
                    'isMain': False,
                    'url': 'http://example.com/frame',
                    'name': 'child-frame',
                    'element': {'tag': 'iframe', 'id': 'child-frame'},
                    'selectors': [{'type': 'id', 'value': '#child-frame'}],
                },
            },
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, 'playwright_snapshot'), exist_ok=True)
            with override_settings(BASE_DIR=temp_dir):
                payload = build_recording_flow_data(session)
        page = next(cell for cell in payload['graph_data']['cells'] if cell.get('data', {}).get('type') == 'page')
        components = page['data']['config']['innerComponents']
        iframe = next(component for component in components if component['type'] == 'iframe')
        recorded_component = next(component for component in components if component['config'].get('recordingStepId') == step.id)
        execution_path = page['data']['config']['executionPath']
        port_pairs = [
            (item['from']['portId'], item['to']['portId'])
            for item in execution_path
        ]
        port_ids = [
            port['id']
            for port in page['ports']['items']
        ]

        self.assertEqual(recorded_component['parentId'], iframe['id'])
        self.assertIn(f'iframe-{iframe["id"]}-left-in', port_ids)
        self.assertIn(f'iframe-{iframe["id"]}-right-out', port_ids)
        self.assertNotIn(f'iframe-{iframe["id"]}-outer-left-in', port_ids)
        self.assertNotIn(f'iframe-{iframe["id"]}-inner-left-in', port_ids)
        self.assertIn(('page-left-in', f'iframe-{iframe["id"]}-left-in'), port_pairs)
        self.assertIn((f'iframe-{iframe["id"]}-left-in', f'component-{recorded_component["id"]}-left-in'), port_pairs)
        self.assertIn((f'component-{recorded_component["id"]}-right-out', f'iframe-{iframe["id"]}-right-out'), port_pairs)
        self.assertIn((f'iframe-{iframe["id"]}-right-out', 'page-right-out'), port_pairs)

    def test_recording_flow_detail_refreshes_legacy_iframe_execution_path(self):
        import copy
        import os
        import tempfile

        from django.test import override_settings

        from .views import create_or_update_visual_flow_from_recording

        session = PlaywrightRecordingSession.objects.create(
            session_id='recording-legacy-iframe-flow',
            name='Recording Legacy Iframe Flow',
            target_url='http://example.com',
            browser_type='chromium',
            status=PlaywrightRecordingSession.STATUS_COMPLETED,
        )
        step = PlaywrightRecordingStep.objects.create(
            session=session,
            step_number=1,
            action_type='click',
            page_url='http://example.com',
            page_title='Example',
            element={'tag': 'button', 'id': 'inside-frame'},
            selectors=[{'type': 'id', 'value': '#inside-frame'}],
            raw_event={
                'is_iframe_event': True,
                'frame': {
                    'isMain': False,
                    'url': 'http://example.com/frame',
                    'name': 'child-frame',
                    'element': {'tag': 'iframe', 'id': 'child-frame'},
                    'selectors': [{'type': 'id', 'value': '#child-frame'}],
                },
            },
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, 'playwright_snapshot'), exist_ok=True)
            with override_settings(BASE_DIR=temp_dir):
                flow, _ = create_or_update_visual_flow_from_recording(session, self.user)
                graph_data = copy.deepcopy(flow.graph_data)
                page = next(cell for cell in graph_data['cells'] if cell.get('data', {}).get('type') == 'page')
                components = page['data']['config']['innerComponents']
                recorded_component = next(
                    component
                    for component in components
                    if component['config'].get('recordingStepId') == step.id
                )
                page['data']['config']['executionPath'] = [
                    {
                        'from': {'portId': 'page-left-in'},
                        'to': {'portId': f'component-{recorded_component["id"]}-left-in'},
                        'action': 'enter',
                        'value': '',
                    },
                    {
                        'from': {'portId': f'component-{recorded_component["id"]}-right-out'},
                        'to': {'portId': 'page-right-out'},
                        'action': 'click',
                        'value': '',
                    },
                ]
                flow.graph_data = graph_data
                flow.save(update_fields=['graph_data'])

                response = self.client.get(f'/api/testcases/visual-flows/{flow.flow_id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        page = next(cell for cell in response.data['graph_data']['cells'] if cell.get('data', {}).get('type') == 'page')
        components = page['data']['config']['innerComponents']
        iframe = next(component for component in components if component['type'] == 'iframe')
        recorded_component = next(component for component in components if component['config'].get('recordingStepId') == step.id)
        port_pairs = [
            (item['from']['portId'], item['to']['portId'])
            for item in page['data']['config']['executionPath']
        ]

        self.assertIn(('page-left-in', f'iframe-{iframe["id"]}-left-in'), port_pairs)
        self.assertIn((f'iframe-{iframe["id"]}-left-in', f'component-{recorded_component["id"]}-left-in'), port_pairs)
        self.assertIn((f'component-{recorded_component["id"]}-right-out', f'iframe-{iframe["id"]}-right-out'), port_pairs)
        self.assertIn((f'iframe-{iframe["id"]}-right-out', 'page-right-out'), port_pairs)


class ManualWorkspaceVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='mindmap_owner',
            email='mindmap-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='mindmap_viewer',
            email='mindmap-viewer@example.com',
            password='viewer123456',
        )
        self.project = Project.objects.create(
            name='Shared Manual Workspace Project',
            owner=self.owner,
        )
        self.version = Version.objects.create(
            name='260422',
            created_by=self.owner,
        )
        self.version.projects.add(self.project)
        self.category = ManualTestCaseCategory.objects.create(
            project=self.project,
            name='客户端',
            description='root category',
            order=1,
        )
        self.mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14086 熊谷-APP支持轮播图展示',
            description='imported by owner',
            category=self.category,
            version=self.version,
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'root-node',
                    'data': {
                        'text': 'SYSWIN-14086 熊谷-APP支持轮播图展示',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'testpoint-1',
                            'data': {
                                'text': '支持轮播图切换展示',
                                'nodeType': 'testpoint',
                                'priority': 1,
                                'status': 'not_run',
                            },
                            'children': [],
                        }
                    ],
                }
            },
        )

    def test_non_member_can_list_manual_categories_and_mindmaps(self):
        self.client.force_authenticate(self.viewer)

        category_response = self.client.get('/api/testcases/manual-categories/', {'project': self.project.id})
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
        category_items = (
            category_response.data['results']
            if isinstance(category_response.data, dict)
            else category_response.data
        )
        self.assertIn(
            self.category.id,
            [item['id'] for item in category_items],
        )

        mindmap_response = self.client.get('/api/testcases/manual-mindmaps/', {'project': self.project.id})
        self.assertEqual(mindmap_response.status_code, status.HTTP_200_OK)
        self.assertEqual(mindmap_response.data['count'], 1)
        self.assertEqual(mindmap_response.data['results'][0]['id'], self.mindmap.id)


class DevSelfTestAdminEditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='devself_owner',
            email='devself-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='devself_viewer',
            email='devself-viewer@example.com',
            password='viewer123456',
        )
        self.admin = User.objects.create_superuser(
            username='devself_admin',
            email='devself-admin@example.com',
            password='admin123456',
        )
        self.project = Project.objects.create(
            name='Dev Self Test Project',
            owner=self.owner,
        )
        self.version = Version.objects.create(
            name='260423',
            created_by=self.owner,
        )
        self.version.projects.add(self.project)
        self.category = ManualTestCaseCategory.objects.create(
            project=self.project,
            name='Client',
            description='root category',
            order=1,
        )
        self.mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14086 Feature',
            description='mindmap for dev self test',
            category=self.category,
            version=self.version,
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'root-node',
                    'data': {
                        'text': 'SYSWIN-14086 Feature',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-1',
                            'data': {
                                'text': 'Module A',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'testpoint-1',
                                    'data': {
                                        'text': 'Verify main flow',
                                        'nodeType': 'testpoint',
                                        'priority': 1,
                                        'status': 'not_run',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

    def test_admin_can_edit_unapproved_dev_self_test_and_record_is_created(self):
        self.client.force_authenticate(self.admin)

        list_response = self.client.get('/api/testcases/dev-self-test/', {'project': self.project.id})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertTrue(list_response.data['results'][0]['can_edit'])
        self.assertEqual(list_response.data['results'][0]['requirement_key'], self.mindmap.requirement_key)
        self.assertEqual(list_response.data['results'][0]['requirement_title'], self.mindmap.requirement_title)
        self.assertEqual(
            list_response.data['results'][0]['path'],
            'SYSWIN-14086 Feature / Module A / Verify main flow',
        )

        patch_response = self.client.patch(
            f'/api/testcases/dev-self-test/detail/?mindmap_id={self.mindmap.id}&node_id=testpoint-1',
            {
                'steps': '1. open page\n2. verify result',
                'remark': 'updated by admin',
                'status': 'pass',
            },
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_response.data['can_edit'])
        self.assertEqual(patch_response.data['status'], 'pass')

        record = DevSelfTestRecord.objects.get(mindmap=self.mindmap, node_id='testpoint-1')
        self.assertEqual(record.audit_status, 'pending')
        self.assertEqual(record.steps, '1. open page\n2. verify result')
        self.assertEqual(record.remark, 'updated by admin')
        self.assertEqual(record.status, 'pass')

    def test_detail_supports_public_id_for_nodes_without_native_id(self):
        self.client.force_authenticate(self.admin)
        mindmap_without_node_ids = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14088 Missing Node IDs',
            description='mindmap with xmind-style nodes without native ids',
            category=self.category,
            version=self.version,
            author=self.owner,
            mindmap_data={
                'root': {
                    'data': {
                        'text': 'SYSWIN-14088 Missing Node IDs',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'data': {
                                'text': 'Module Without IDs',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'data': {
                                        'text': 'Verify public id flow',
                                        'nodeType': 'testpoint',
                                        'priority': 1,
                                        'status': 'not_run',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        list_response = self.client.get('/api/testcases/dev-self-test/', {'project': self.project.id})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        target = next(
            item for item in list_response.data['results']
            if item['mindmap_id'] == mindmap_without_node_ids.id
        )
        self.assertEqual(target['id'], f'{mindmap_without_node_ids.id}:testpoint:1')

        detail_response = self.client.get(
            f"/api/testcases/dev-self-test/detail/?mindmap_id={mindmap_without_node_ids.id}&node_id={target['id']}",
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['testpoint'], 'Verify public id flow')

        patch_response = self.client.patch(
            f"/api/testcases/dev-self-test/detail/?mindmap_id={mindmap_without_node_ids.id}&node_id={target['id']}",
            {
                'steps': '1. verify public id',
                'status': 'pass',
            },
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        record = DevSelfTestRecord.objects.get(mindmap=mindmap_without_node_ids, node_id=target['id'])
        self.assertEqual(record.status, 'pass')

    def test_regular_user_cannot_edit_unapproved_dev_self_test(self):
        self.client.force_authenticate(self.viewer)

        patch_response = self.client.patch(
            f'/api/testcases/dev-self-test/detail/?mindmap_id={self.mindmap.id}&node_id=testpoint-1',
            {
                'steps': 'blocked',
                'status': 'fail',
            },
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DevSelfTestRecord.objects.filter(mindmap=self.mindmap, node_id='testpoint-1').exists())

    def test_user_with_dev_self_test_edit_permission_can_edit_unapproved_record(self):
        edit_permission, _ = PermissionItem.objects.update_or_create(
            code='button:manual-testcases:devselftest:edit',
            defaults={
                'name': '编辑自测测试点',
                'item_type': 'button',
                'is_active': True,
            },
        )
        role = Role.objects.create(name='Dev Self Test Editor')
        role.members.add(self.viewer)
        RolePermission.objects.create(role=role, permission_item=edit_permission)
        self.client.force_authenticate(self.viewer)

        list_response = self.client.get('/api/testcases/dev-self-test/', {'project': self.project.id})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertTrue(list_response.data['results'][0]['can_edit'])

        patch_response = self.client.patch(
            f'/api/testcases/dev-self-test/detail/?mindmap_id={self.mindmap.id}&node_id=testpoint-1',
            {
                'steps': '1. execute as test role',
                'status': 'pass',
            },
            format='json',
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_response.data['can_edit'])
        record = DevSelfTestRecord.objects.get(mindmap=self.mindmap, node_id='testpoint-1')
        self.assertEqual(record.audit_status, 'pending')
        self.assertEqual(record.steps, '1. execute as test role')
        self.assertEqual(record.status, 'pass')

    def test_audit_endpoint_accepts_id_alias_for_node_id(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            '/api/testcases/dev-self-test/audit/',
            {
                'audit_status': 'approved',
                'items': [
                    {
                        'mindmap_id': self.mindmap.id,
                        'id': 'testpoint-1',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['processed_count'], 1)
        self.assertEqual(response.data['skipped_count'], 0)

        record = DevSelfTestRecord.objects.get(mindmap=self.mindmap, node_id='testpoint-1')
        self.assertEqual(record.audit_status, 'approved')
        self.assertEqual(record.audited_by_id, self.admin.id)

    def test_list_supports_requirement_filters(self):
        self.client.force_authenticate(self.admin)

        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14087 Another Feature',
            description='another mindmap for dev self test',
            category=self.category,
            version=self.version,
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'root-node-2',
                    'data': {
                        'text': 'SYSWIN-14087 Another Feature',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-2',
                            'data': {
                                'text': 'Module B',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'testpoint-2',
                                    'data': {
                                        'text': 'Verify secondary flow',
                                        'nodeType': 'testpoint',
                                        'priority': 1,
                                        'status': 'not_run',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        key_response = self.client.get(
            '/api/testcases/dev-self-test/',
            {
                'project': self.project.id,
                'requirement_key': self.mindmap.requirement_key,
            },
        )
        self.assertEqual(key_response.status_code, status.HTTP_200_OK)
        self.assertEqual(key_response.data['count'], 1)
        self.assertEqual(key_response.data['results'][0]['mindmap_id'], self.mindmap.id)

        title_response = self.client.get(
            '/api/testcases/dev-self-test/',
            {
                'project': self.project.id,
                'requirement_title': self.mindmap.requirement_title,
            },
        )
        self.assertEqual(title_response.status_code, status.HTTP_200_OK)
        self.assertEqual(title_response.data['count'], 1)
        self.assertEqual(title_response.data['results'][0]['mindmap_id'], self.mindmap.id)


class ManualMindmapGroupValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='mindmap_group_owner',
            email='mindmap-group-owner@example.com',
            password='owner123456',
        )
        self.client.force_authenticate(self.user)
        self.project = Project.objects.create(
            name='Mindmap Group Validation Project',
            owner=self.user,
        )
        Group.objects.create(name='平台组')

    def test_create_manual_mindmap_rejects_unknown_group(self):
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Unknown Group Mindmap',
                'description': 'invalid group',
                'responsibility_group': '不存在的组别',
                'mindmap_data': {
                    'root': {
                        'data': {
                            'text': 'Unknown Group Mindmap',
                            'nodeType': 'module',
                        },
                        'children': [],
                    }
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('responsibility_group', response.data)

    def test_create_manual_mindmap_accepts_existing_group(self):
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Known Group Mindmap',
                'description': 'valid group',
                'responsibility_group': '平台组',
                'mindmap_data': {
                    'root': {
                        'data': {
                            'text': 'Known Group Mindmap',
                            'nodeType': 'module',
                        },
                        'children': [],
                    }
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['responsibility_group'], '平台组')


class ManualMindmapRequirementExtractionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='mindmap_requirement_owner',
            email='mindmap-requirement-owner@example.com',
            password='owner123456',
        )
        self.project = Project.objects.create(
            name='Requirement Extraction Project',
            owner=self.owner,
        )

    def test_model_extracts_requirement_info_from_bracketed_name(self):
        mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='【SYSWIN-14086】登录页支持轮播图展示',
            description='bracketed requirement name',
            author=self.owner,
            mindmap_data={},
        )

        self.assertEqual(mindmap.requirement_key, 'SYSWIN-14086')
        self.assertEqual(mindmap.requirement_title, '登录页支持轮播图展示')

    def test_model_preserves_explicit_requirement_fields_when_name_is_not_splittable(self):
        mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='客户端测试分析',
            description='imported from xmind',
            author=self.owner,
            mindmap_data={},
            requirement_key='SYSWIN-14086',
            requirement_title='登录页支持轮播图展示',
        )

        self.assertEqual(mindmap.requirement_key, 'SYSWIN-14086')
        self.assertEqual(mindmap.requirement_title, '登录页支持轮播图展示')

    def test_model_extracts_requirement_info_when_title_precedes_requirement_key(self):
        mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='登录页支持轮播图展示【SYSWIN-14086】',
            description='suffix requirement key name',
            author=self.owner,
            mindmap_data={},
        )

        self.assertEqual(mindmap.requirement_key, 'SYSWIN-14086')
        self.assertEqual(mindmap.requirement_title, '登录页支持轮播图展示')


class ManualCategoryXMindImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='category_xmind_import_owner',
            email='category-xmind-import-owner@example.com',
            password='owner123456',
        )
        self.project = Project.objects.create(
            name='Category XMind Import Project',
            owner=self.owner,
        )
        self.client.force_authenticate(self.owner)
        self.url = '/api/testcases/manual-categories/import-xmind/'

    def test_import_xmind_without_selected_parent_creates_root_category(self):
        response = self.client.post(
            self.url,
            {
                'project_id': self.project.id,
                'xmind_file': build_xmind_upload(
                    '产品中心',
                    child_titles=['订单管理', '客户管理'],
                    file_name='category-root-import.xmind',
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['imported_count'], 3)
        self.assertIsNone(response.data['parent_id'])
        root = ManualTestCaseCategory.objects.get(project=self.project, name='产品中心')
        self.assertIsNone(root.parent_id)
        self.assertEqual(
            list(root.children.order_by('order', 'id').values_list('name', flat=True)),
            ['订单管理', '客户管理'],
        )

    def test_import_xmind_with_selected_parent_creates_root_as_child(self):
        selected_parent = ManualTestCaseCategory.objects.create(
            project=self.project,
            name='已有目录',
            order=0,
        )

        response = self.client.post(
            self.url,
            {
                'project_id': self.project.id,
                'parent_id': selected_parent.id,
                'xmind_file': build_xmind_upload(
                    '服务台',
                    child_titles=['工单管理'],
                    file_name='category-child-import.xmind',
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['parent_id'], selected_parent.id)
        imported_root = ManualTestCaseCategory.objects.get(project=self.project, name='服务台')
        self.assertEqual(imported_root.parent_id, selected_parent.id)
        self.assertTrue(imported_root.children.filter(name='工单管理').exists())


class ManualMindmapXMindImportRequirementSplitTests(TestCase):
    def test_parse_uploaded_xmind_supports_single_requirement_title_then_key(self):
        upload = build_xmind_upload('登录页支持轮播图展示 SYSWIN-14086')

        parsed = parse_uploaded_xmind(upload)

        self.assertEqual(parsed.mode, 'single_requirement')
        self.assertEqual(len(parsed.requirement_items), 1)
        self.assertEqual(parsed.requirement_items[0].jira_key, 'SYSWIN-14086')
        self.assertEqual(parsed.requirement_items[0].requirement_title, '登录页支持轮播图展示')

    def test_parse_uploaded_xmind_supports_split_requirement_child_title_then_key(self):
        upload = build_xmind_upload(
            '260425张三测试分析',
            child_titles=['登录页支持轮播图展示 SYSWIN-14086'],
        )

        parsed = parse_uploaded_xmind(upload)

        self.assertEqual(parsed.mode, 'split_requirements')
        self.assertEqual(len(parsed.requirement_items), 1)
        self.assertEqual(parsed.requirement_items[0].name, '登录页支持轮播图展示 SYSWIN-14086')
        self.assertEqual(parsed.requirement_items[0].jira_key, 'SYSWIN-14086')
        self.assertEqual(parsed.requirement_items[0].requirement_title, '登录页支持轮播图展示')


class ManualMindmapXMindImportReplaceExistingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='mindmap_xmind_import_owner',
            email='mindmap-xmind-import-owner@example.com',
            password='owner123456',
        )
        self.client.force_authenticate(self.owner)
        self.project = Project.objects.create(
            name='XMind Import Replace Project',
            owner=self.owner,
        )

    def create_mindmap(self, *, project=None, name, requirement_key=None, requirement_title=None):
        return ManualTestCaseMindmap.objects.create(
            project=project or self.project,
            name=name,
            description='existing mindmap',
            author=self.owner,
            requirement_key=requirement_key or '',
            requirement_title=requirement_title or '',
            mindmap_data={
                'root': {
                    'id': f'root-{name}',
                    'data': {
                        'text': name,
                        'nodeType': 'requirement',
                    },
                    'children': [],
                }
            },
        )

    def test_import_xmind_replaces_existing_mindmap_with_same_requirement_key(self):
        existing = self.create_mindmap(
            name='SYSWIN-14086 旧测试脑图',
            requirement_key='SYSWIN-14086',
            requirement_title='旧需求标题',
        )
        unaffected = self.create_mindmap(
            name='SYSWIN-14087 其他测试脑图',
            requirement_key='SYSWIN-14087',
            requirement_title='其他需求标题',
        )

        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'xmind_file': build_xmind_upload('登录页支持轮播图展示 SYSWIN-14086'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(ManualTestCaseMindmap.objects.filter(id=existing.id).exists())
        self.assertTrue(ManualTestCaseMindmap.objects.filter(id=unaffected.id).exists())

        matching = ManualTestCaseMindmap.objects.filter(
            project=self.project,
            requirement_key='SYSWIN-14086',
        )
        self.assertEqual(matching.count(), 1)
        created = matching.first()
        self.assertNotEqual(created.id, existing.id)
        self.assertEqual(created.name, '登录页支持轮播图展示 SYSWIN-14086')
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(response.data['created_records'][0]['id'], created.id)

    def test_import_xmind_without_requirement_key_does_not_delete_existing_mindmaps(self):
        existing = self.create_mindmap(
            name='SYSWIN-14086 已有测试脑图',
            requirement_key='SYSWIN-14086',
            requirement_title='已有需求标题',
        )

        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'xmind_file': build_xmind_upload('客户端测试分析'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ManualTestCaseMindmap.objects.filter(id=existing.id).exists())
        self.assertEqual(ManualTestCaseMindmap.objects.filter(project=self.project).count(), 2)

        created = ManualTestCaseMindmap.objects.exclude(id=existing.id).get(project=self.project)
        self.assertEqual(created.name, '客户端测试分析')
        self.assertEqual(created.requirement_key, '')

    def test_import_xmind_only_replaces_matching_requirement_in_current_project(self):
        existing = self.create_mindmap(
            name='SYSWIN-14086 当前项目旧脑图',
            requirement_key='SYSWIN-14086',
            requirement_title='当前项目旧需求',
        )
        other_project = Project.objects.create(
            name='Another XMind Import Project',
            owner=self.owner,
        )
        other_project_mindmap = self.create_mindmap(
            project=other_project,
            name='SYSWIN-14086 其他项目脑图',
            requirement_key='SYSWIN-14086',
            requirement_title='其他项目需求',
        )

        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'xmind_file': build_xmind_upload('登录页支持轮播图展示 SYSWIN-14086'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(ManualTestCaseMindmap.objects.filter(id=existing.id).exists())
        self.assertTrue(ManualTestCaseMindmap.objects.filter(id=other_project_mindmap.id).exists())
        self.assertEqual(
            ManualTestCaseMindmap.objects.filter(project=other_project, requirement_key='SYSWIN-14086').count(),
            1,
        )


class ManualMindmapCategoryMatchingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='category_match_owner',
            email='category-match-owner@example.com',
            password='owner123456',
        )
        self.project = Project.objects.create(
            name='Category Match Project',
            owner=self.owner,
        )
        self.root_category = ManualTestCaseCategory.objects.create(
            project=self.project,
            name='Product',
            order=0,
        )
        self.portal_category = ManualTestCaseCategory.objects.create(
            project=self.project,
            parent=self.root_category,
            name='Portal',
            order=0,
        )
        self.workbench_category = ManualTestCaseCategory.objects.create(
            project=self.project,
            parent=self.portal_category,
            name='Workbench',
            order=0,
        )
        self.client.force_authenticate(self.owner)

    def build_mindmap_data(self, *, extra_children=None):
        children = [
            {
                'id': 'module-portal',
                'data': {
                    'text': 'Portal',
                    'nodeType': 'module',
                },
                'children': [
                    {
                        'id': 'module-workbench',
                        'data': {
                            'text': 'Workbench',
                            'nodeType': 'module',
                        },
                        'children': [
                            {
                                'id': 'testpoint-1',
                                'data': {
                                    'text': 'Verify portal flow',
                                    'nodeType': 'testpoint',
                                },
                                'children': [],
                            }
                        ],
                    }
                ],
            }
        ]

        if extra_children:
            children.extend(extra_children)

        return {
            'root': {
                'id': 'root-node',
                'data': {
                    'text': 'Requirement Root',
                    'nodeType': 'requirement',
                },
                'children': children,
            }
        }

    @staticmethod
    def find_node(node, text):
        if (node.get('data') or {}).get('text') == text:
            return node
        for child in node.get('children') or []:
            matched = ManualMindmapCategoryMatchingTests.find_node(child, text)
            if matched:
                return matched
        return None

    def test_create_mindmap_matches_modules_without_creating_categories(self):
        category_count = ManualTestCaseCategory.objects.filter(project=self.project).count()
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Portal Mindmap',
                'description': 'match modules on create',
                'mindmap_data': self.build_mindmap_data(
                    extra_children=[
                        {
                            'id': 'module-reports',
                            'data': {
                                'text': 'Reports',
                                'nodeType': 'module',
                            },
                            'children': [],
                        }
                    ]
                ),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ManualTestCaseCategory.objects.filter(project=self.project).count(), category_count)
        self.assertFalse(
            ManualTestCaseCategory.objects.filter(project=self.project, name='Reports').exists()
        )

        root = response.data['mindmap_data']['root']
        portal = self.find_node(root, 'Portal')['data']
        workbench = self.find_node(root, 'Workbench')['data']
        reports = self.find_node(root, 'Reports')['data']
        self.assertTrue(portal['moduleCategoryMatched'])
        self.assertEqual(portal['moduleCategoryId'], self.portal_category.id)
        self.assertTrue(workbench['moduleCategoryMatched'])
        self.assertEqual(workbench['moduleCategoryId'], self.workbench_category.id)
        self.assertFalse(reports['moduleCategoryMatched'])
        self.assertIsNone(reports['moduleCategoryId'])

    def test_update_mindmap_recomputes_matches_without_appending_categories(self):
        create_response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Portal Mindmap',
                'description': 'match modules on update',
                'mindmap_data': self.build_mindmap_data(),
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        category_count = ManualTestCaseCategory.objects.filter(project=self.project).count()

        update_response = self.client.put(
            f"/api/testcases/manual-mindmaps/{create_response.data['id']}/",
            {
                'name': 'Portal Mindmap',
                'description': 'match modules on update',
                'mindmap_data': self.build_mindmap_data(
                    extra_children=[
                        {
                            'id': 'module-billing',
                            'data': {
                                'text': 'Billing',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'module-dashboard',
                                    'data': {
                                        'text': 'Dashboard',
                                        'nodeType': 'module',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ]
                ),
            },
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.data)
        self.assertEqual(ManualTestCaseCategory.objects.filter(project=self.project).count(), category_count)
        self.assertFalse(ManualTestCaseCategory.objects.filter(project=self.project, name='Billing').exists())
        self.assertFalse(ManualTestCaseCategory.objects.filter(project=self.project, name='Dashboard').exists())

        root = update_response.data['mindmap_data']['root']
        self.assertTrue(self.find_node(root, 'Portal')['data']['moduleCategoryMatched'])
        self.assertTrue(self.find_node(root, 'Workbench')['data']['moduleCategoryMatched'])
        self.assertFalse(self.find_node(root, 'Billing')['data']['moduleCategoryMatched'])
        self.assertFalse(self.find_node(root, 'Dashboard')['data']['moduleCategoryMatched'])

    def test_create_mindmap_without_categories_does_not_create_default_root(self):
        empty_project = Project.objects.create(name='Empty Category Project', owner=self.owner)
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': empty_project.id,
                'name': 'No Category Mindmap',
                'mindmap_data': self.build_mindmap_data(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertFalse(ManualTestCaseCategory.objects.filter(project=empty_project).exists())
        created_mindmap = ManualTestCaseMindmap.objects.get(id=response.data['id'])
        self.assertIsNone(created_mindmap.category_id)
        self.assertFalse(
            self.find_node(response.data['mindmap_data']['root'], 'Portal')['data']['moduleCategoryMatched']
        )

    def test_xmind_mindmap_import_matches_existing_modules_without_creating_categories(self):
        category_count = ManualTestCaseCategory.objects.filter(project=self.project).count()
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'xmind_file': build_nested_xmind_upload(
                    'Portal requirement SYSWIN-41001',
                    'Portal',
                    'Verify portal entry',
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ManualTestCaseCategory.objects.filter(project=self.project).count(), category_count)
        imported_root = response.data['created_records'][0]['mindmap_data']['root']
        portal = self.find_node(imported_root, 'Portal')['data']
        self.assertEqual(portal['nodeType'], 'module')
        self.assertTrue(portal['moduleCategoryMatched'])
        self.assertEqual(portal['moduleCategoryId'], self.portal_category.id)


class ManualMindmapNodeAuthorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='node_author_owner',
            email='node-author-owner@example.com',
            password='owner123456',
            first_name='Node',
            last_name='Owner',
        )
        self.viewer = User.objects.create_user(
            username='node_author_viewer',
            email='node-author-viewer@example.com',
            password='viewer123456',
        )
        self.project = Project.objects.create(
            name='Node Author Project',
            owner=self.owner,
        )
        self.client.force_authenticate(self.viewer)
        self.mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Node Author Mindmap',
            description='mindmap for node author tests',
            author=self.owner,
            requirement_key='SYSWIN-14086',
            requirement_title='所属测试脑图需求标题',
            mindmap_data={
                'root': {
                    'id': 'root-node',
                    'data': {
                        'text': '节点根标题与脑图需求字段不同',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-1',
                            'data': {
                                'text': 'Module A',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'case-1',
                                    'data': {
                                        'text': 'Verify case flow',
                                        'nodeType': 'case',
                                        'priority': 1,
                                        'status': 'not_run',
                                    },
                                    'children': [],
                                },
                                {
                                    'id': 'testpoint-1',
                                    'data': {
                                        'text': 'Verify testpoint flow',
                                        'nodeType': 'testpoint',
                                        'priority': 2,
                                        'status': 'pass',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

    def test_case_nodes_use_mindmap_author_as_creator(self):
        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'case', 'project': self.project.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        author = response.data['results'][0]['author']
        self.assertEqual(author['id'], self.owner.id)
        self.assertEqual(author['username'], self.owner.username)
        self.assertEqual(response.data['results'][0]['requirement_key'], self.mindmap.requirement_key)
        self.assertEqual(response.data['results'][0]['requirement_title'], self.mindmap.requirement_title)

    def test_testpoint_nodes_use_mindmap_author_as_creator(self):
        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'testpoint', 'project': self.project.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        author = response.data['results'][0]['author']
        self.assertEqual(author['id'], self.owner.id)
        self.assertEqual(author['username'], self.owner.username)
        self.assertEqual(response.data['results'][0]['requirement_key'], self.mindmap.requirement_key)
        self.assertEqual(response.data['results'][0]['requirement_title'], self.mindmap.requirement_title)

    def test_testpoint_nodes_include_review_fields(self):
        mindmap_data = self.mindmap.mindmap_data
        testpoint_data = mindmap_data['root']['children'][0]['children'][1]['data']
        testpoint_data.update({
            'reviewOpinion': 'Needs additional boundary checks',
            'reviewerId': self.owner.id,
            'reviewerName': 'Node Owner',
            'reviewTime': '2026-05-15 09:30:00',
            'reviewStatus': '未处理',
        })
        self.mindmap.mindmap_data = mindmap_data
        self.mindmap.save(update_fields=['mindmap_data'])

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'testpoint', 'project': self.project.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['results'][0]
        self.assertEqual(item['review_opinion'], 'Needs additional boundary checks')
        self.assertEqual(item['reviewer_id'], self.owner.id)
        self.assertEqual(item['reviewer_name'], 'Node Owner')
        self.assertEqual(item['review_time'], '2026-05-15 09:30:00')
        self.assertEqual(item['review_status'], '未处理')

    def test_mindmap_list_includes_review_testpoint_count(self):
        mindmap_data = self.mindmap.mindmap_data
        module_children = mindmap_data['root']['children'][0]['children']
        module_children[1]['data'].update({
            'reviewOpinion': 'Pending review item',
            'reviewStatus': '未处理',
        })
        module_children.append({
            'id': 'testpoint-2',
            'data': {
                'text': 'Verify processed review item',
                'nodeType': 'testpoint',
                'priority': 2,
                'status': 'pass',
                'reviewOpinion': 'Already handled',
                'reviewStatus': '已处理',
            },
            'children': [],
        })
        self.mindmap.mindmap_data = mindmap_data
        self.mindmap.save(update_fields=['mindmap_data'])

        response = self.client.get(
            '/api/testcases/manual-mindmaps/',
            {'project': self.project.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count = response.data['results'][0]['review_testpoint_count']
        self.assertEqual(count['unprocessed'], 1)
        self.assertEqual(count['processed'], 1)
        self.assertEqual(count['total'], 2)

    def test_mindmap_list_counts_not_test_status_separately(self):
        mindmap_data = self.mindmap.mindmap_data
        testpoint_data = mindmap_data['root']['children'][0]['children'][1]['data']
        testpoint_data['status'] = 'not_test'
        self.mindmap.mindmap_data = mindmap_data
        self.mindmap.save(update_fields=['mindmap_data'])

        response = self.client.get(
            '/api/testcases/manual-mindmaps/',
            {'project': self.project.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        counts = response.data['results'][0]['testpoint_count']
        self.assertEqual(counts['not_test'], 1)
        self.assertEqual(counts['not_run'], 0)

    def test_case_node_creator_filter_options_include_all_filtered_results_not_current_page(self):
        second_owner = User.objects.create_user(
            username='node_author_owner_2',
            email='node-author-owner-2@example.com',
            password='owner123456',
            first_name='Second',
            last_name='Owner',
        )
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14087 Feature Two',
            description='second mindmap for node author tests',
            author=second_owner,
            mindmap_data={
                'root': {
                    'id': 'root-node-2',
                    'data': {
                        'text': 'SYSWIN-14087 Feature Two',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-2',
                            'data': {
                                'text': 'Module B',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'case-2',
                                    'data': {
                                        'text': 'Verify second case flow',
                                        'nodeType': 'case',
                                        'priority': 2,
                                        'status': 'pass',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'case', 'project': self.project.id, 'page': 1, 'page_size': 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        creator_ids = {item['id'] for item in response.data['creators']}
        self.assertEqual(creator_ids, {self.owner.id, second_owner.id})

    def test_case_nodes_support_requirement_key_filter(self):
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='SYSWIN-14087 Feature Two',
            description='second mindmap for case requirement filter',
            author=self.owner,
            requirement_key='SYSWIN-14087',
            requirement_title='另一个需求标题',
            mindmap_data={
                'root': {
                    'id': 'root-node-2',
                    'data': {
                        'text': 'Another root title',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-2',
                            'data': {
                                'text': 'Module B',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'case-2',
                                    'data': {
                                        'text': 'Verify second case flow',
                                        'nodeType': 'case',
                                        'priority': 2,
                                        'status': 'pass',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'case', 'project': self.project.id, 'requirement_key': 'SYSWIN-14086'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['requirement_key'], 'SYSWIN-14086')

    def test_testpoint_status_filter_options_include_all_filtered_results_not_current_page(self):
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Node Author Mindmap Two',
            description='second mindmap for testpoint status options',
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'root-node-2',
                    'data': {
                        'text': 'Second mindmap root',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-2',
                            'data': {
                                'text': 'Module B',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'testpoint-2',
                                    'data': {
                                        'text': 'Verify second testpoint flow',
                                        'nodeType': 'testpoint',
                                        'priority': 2,
                                        'status': 'fail',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'testpoint', 'project': self.project.id, 'page': 1, 'page_size': 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(set(response.data['statuses']), {'pass', 'fail'})

    def test_testpoint_nodes_support_status_filter(self):
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Node Author Mindmap Three',
            description='third mindmap for testpoint status filter',
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'root-node-3',
                    'data': {
                        'text': 'Third mindmap root',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-3',
                            'data': {
                                'text': 'Module C',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'testpoint-3',
                                    'data': {
                                        'text': 'Verify third testpoint flow',
                                        'nodeType': 'testpoint',
                                        'priority': 2,
                                        'status': 'fail',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'testpoint', 'project': self.project.id, 'status': 'pass'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'pass')
        self.assertEqual(set(response.data['statuses']), {'pass', 'fail'})

    def test_testpoint_nodes_support_mindmap_id_filter(self):
        second_mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Node Author Mindmap Four',
            description='fourth mindmap for testpoint mindmap filter',
            author=self.owner,
            requirement_key='SYSWIN-14088',
            requirement_title='脑图ID筛选需求',
            mindmap_data={
                'root': {
                    'id': 'root-node-4',
                    'data': {
                        'text': 'Fourth mindmap root',
                        'nodeType': 'requirement',
                    },
                    'children': [
                        {
                            'id': 'module-4',
                            'data': {
                                'text': 'Module D',
                                'nodeType': 'module',
                            },
                            'children': [
                                {
                                    'id': 'testpoint-4',
                                    'data': {
                                        'text': 'Verify fourth testpoint flow',
                                        'nodeType': 'testpoint',
                                        'priority': 1,
                                        'status': 'not_run',
                                    },
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            },
        )

        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'node_type': 'testpoint', 'project': self.project.id, 'mindmap_id': second_mindmap.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['mindmap_id'], second_mindmap.id)
        self.assertEqual(response.data['results'][0]['requirement_key'], 'SYSWIN-14088')


class ManualMindmapScopeIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='mindmap_scope_owner',
            email='mindmap-scope-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='mindmap_scope_viewer',
            email='mindmap-scope-viewer@example.com',
            password='viewer123456',
        )
        self.project = Project.objects.create(
            name='Mindmap Scope Project',
            owner=self.owner,
        )
        self.client.force_authenticate(self.viewer)
        self.testing_mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Testing Mindmap',
            author=self.owner,
            mindmap_data={
                'root': {
                    'id': 'testing-root',
                    'data': {'text': 'Testing Root', 'nodeType': 'requirement'},
                    'children': [],
                }
            },
        )
        self.requirement_mindmap = ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Requirement Analysis Mindmap',
            author=self.owner,
            mindmap_scope=ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
            mindmap_data={
                'root': {
                    'id': 'requirement-root',
                    'data': {'text': 'Requirement Root', 'nodeType': 'requirement'},
                    'children': [
                        {
                            'id': 'requirement-testpoint',
                            'data': {
                                'text': 'Requirement-only testpoint',
                                'nodeType': 'testpoint',
                                'priority': 1,
                                'status': 'pass',
                            },
                            'children': [],
                        }
                    ],
                }
            },
        )

    def test_create_requirement_analysis_mindmap_uses_scope(self):
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Created Requirement Analysis Mindmap',
                'mindmap_scope': ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
                'mindmap_data': {
                    'root': {
                        'data': {'text': 'Created Requirement Analysis Mindmap', 'nodeType': 'requirement'},
                        'children': [],
                    }
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['mindmap_scope'], ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS)
        created = ManualTestCaseMindmap.objects.get(id=response.data['id'])
        self.assertEqual(created.mindmap_scope, ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS)

    def test_requirement_analysis_mindmap_normalizes_malformed_nodes(self):
        response = self.client.post(
            '/api/testcases/manual-mindmaps/',
            {
                'project_id': self.project.id,
                'name': 'Malformed Requirement Analysis Mindmap',
                'mindmap_scope': ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
                'mindmap_data': {
                    'root': {
                        'data': '@{text=需求分析; nodeType=requirement}',
                        'children': [
                            {
                                'data': '@{text=页面清单; nodeType=page}',
                                'children': '  ',
                            }
                        ],
                    }
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = ManualTestCaseMindmap.objects.get(id=response.data['id'])
        root = created.mindmap_data['root']
        self.assertEqual(root['data']['text'], '需求分析')
        self.assertEqual(root['data']['nodeType'], 'requirement')
        self.assertEqual(root['children'][0]['data']['text'], '页面清单')
        self.assertEqual(root['children'][0]['data']['nodeType'], 'page')
        self.assertEqual(root['children'][0]['children'], [])

    def test_requirement_analysis_mindmap_rejects_empty_overwrite(self):
        response = self.client.put(
            f'/api/testcases/manual-mindmaps/{self.requirement_mindmap.id}/',
            {
                'name': self.requirement_mindmap.name,
                'description': self.requirement_mindmap.description,
                'mindmap_scope': ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
                'mindmap_data': {
                    'root': {
                        'data': {'text': 'Requirement Root', 'nodeType': 'requirement'},
                        'children': [],
                    }
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.requirement_mindmap.refresh_from_db()
        self.assertEqual(len(self.requirement_mindmap.mindmap_data['root']['children']), 1)

    def test_default_mindmap_list_excludes_requirement_analysis_scope(self):
        response = self.client.get('/api/testcases/manual-mindmaps/', {'project': self.project.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in response.data['results']}
        self.assertIn(self.testing_mindmap.id, ids)
        self.assertNotIn(self.requirement_mindmap.id, ids)

    def test_explicit_requirement_analysis_scope_lists_requirement_mindmaps(self):
        response = self.client.get(
            '/api/testcases/manual-mindmaps/',
            {
                'project': self.project.id,
                'mindmap_scope': ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in response.data['results']}
        self.assertIn(self.requirement_mindmap.id, ids)
        self.assertNotIn(self.testing_mindmap.id, ids)

    def test_node_list_excludes_requirement_analysis_scope(self):
        response = self.client.get(
            '/api/testcases/manual-mindmap-nodes/',
            {'project': self.project.id, 'node_type': 'testpoint'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
