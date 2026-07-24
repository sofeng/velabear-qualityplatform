import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
BACKEND_DB = ROOT / "smoke_workflow.sqlite3"
BACKEND_LOG = ROOT / "logs" / "workflow-smoke-backend.log"
FRONTEND_LOG = ROOT / "logs" / "workflow-smoke-frontend.log"

SMOKE_HOST = os.environ.get("WORKFLOW_SMOKE_HOST", "127.0.0.1")
SMOKE_BACKEND_PORT = int(os.environ.get("WORKFLOW_SMOKE_BACKEND_PORT", "18080"))
SMOKE_FRONTEND_PORT = int(os.environ.get("WORKFLOW_SMOKE_FRONTEND_PORT", "13000"))
BACKEND_URL = f"http://{SMOKE_HOST}:{SMOKE_BACKEND_PORT}"
FRONTEND_URL = f"http://{SMOKE_HOST}:{SMOKE_FRONTEND_PORT}"
SMOKE_PASSWORD = "Pass123456"


def wait_for_http(url, timeout=120):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=5) as response:
                return response.status
        except HTTPError as exc:
            return exc.code
        except (URLError, OSError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Timeout waiting for {url}: {last_error}")


def terminate_process(proc):
    if not proc or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            pass
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def seed_smoke_data():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_smoke")
    sys.path.insert(0, str(ROOT))

    import django

    django.setup()

    from django.core.management import call_command
    from django.utils import timezone
    from apps.defects.models import Defect
    from apps.projects.models import Project, ProjectMember
    from apps.requirement_analysis.models import (
        BusinessRequirement,
        RequirementAnalysis,
        RequirementDocument,
    )
    from apps.users.models import PermissionItem, Role, RolePermission, User
    from apps.workflow.models import WorkflowRule
    from apps.workflow.services import get_open_task_for_instance, start_workflow

    if BACKEND_DB.exists():
        BACKEND_DB.unlink()

    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)

    workflow_admin = User.objects.create_user(
        username="workflow_admin",
        password=SMOKE_PASSWORD,
        first_name="Workflow",
        last_name="Admin",
        is_staff=True,
        is_superuser=True,
    )
    developer = User.objects.create_user(
        username="workflow_dev",
        password=SMOKE_PASSWORD,
        first_name="Workflow",
        last_name="Developer",
    )
    tester = User.objects.create_user(
        username="workflow_tester",
        password=SMOKE_PASSWORD,
        first_name="Workflow",
        last_name="Tester",
    )
    outsider = User.objects.create_user(
        username="workflow_outsider",
        password=SMOKE_PASSWORD,
        first_name="Workflow",
        last_name="Outsider",
    )

    smoke_permission_codes = [
        "menu:manual-testcases:list",
        "menu:ai-generation:ai-requirements",
    ]
    smoke_permissions = list(
        PermissionItem.objects.filter(code__in=smoke_permission_codes).order_by("sort_order", "name", "id")
    )
    missing_permission_codes = sorted(set(smoke_permission_codes) - {item.code for item in smoke_permissions})
    if missing_permission_codes:
        raise RuntimeError(f"Missing smoke permission items: {', '.join(missing_permission_codes)}")

    smoke_operator_role = Role.objects.create(name="Workflow Smoke Collaborator")
    smoke_operator_role.members.add(developer, tester)
    RolePermission.objects.bulk_create(
        [RolePermission(role=smoke_operator_role, permission_item=item) for item in smoke_permissions]
    )

    project = Project.objects.create(name="Workflow Smoke Project", owner=workflow_admin)
    ProjectMember.objects.create(project=project, user=developer, role="developer")
    ProjectMember.objects.create(project=project, user=tester, role="tester")
    ProjectMember.objects.create(project=project, user=workflow_admin, role="admin")

    defect = Defect.objects.create(
        project=project,
        title="Workflow smoke defect",
        description="Smoke defect detail for workflow regression.",
        severity="critical",
        created_by=tester,
    )
    defect.assignees.set([developer])

    overdue_defect = Defect.objects.create(
        project=project,
        title="Workflow overdue defect",
        description="Smoke overdue defect detail for SLA regression.",
        severity="critical",
        created_by=tester,
    )
    overdue_defect.assignees.set([developer])

    terminated_defect = Defect.objects.create(
        project=project,
        title="Workflow terminated defect",
        description="Smoke defect detail for termination regression.",
        severity="high",
        created_by=tester,
    )
    terminated_defect.assignees.set([developer])

    document = RequirementDocument.objects.create(
        title="Workflow smoke requirement doc",
        file="",
        document_type="txt",
        status="analyzed",
        uploaded_by=workflow_admin,
        project=project,
        extracted_text="Smoke requirement detail",
    )
    analysis = RequirementAnalysis.objects.create(
        document=document,
        analysis_report="Workflow smoke analysis",
        requirements_count=1,
        analysis_time=0.1,
    )
    requirement = BusinessRequirement.objects.create(
        analysis=analysis,
        requirement_id="REQ-SMOKE-001",
        requirement_name="Workflow smoke requirement",
        requirement_type="functional",
        module="Workflow",
        requirement_level="high",
        reviewer=workflow_admin.username,
        estimated_hours=8,
        description="Smoke requirement detail for workflow regression.",
        acceptance_criteria="Smoke acceptance criteria",
    )

    defect_instance = start_workflow("defect", defect.id, workflow_admin)
    overdue_instance = start_workflow("defect", overdue_defect.id, workflow_admin)
    terminated_instance = start_workflow("defect", terminated_defect.id, workflow_admin)
    requirement_instance = start_workflow("requirement", requirement.id, workflow_admin)
    overdue_task = get_open_task_for_instance(overdue_instance)
    now = timezone.now()
    overdue_task.remind_at = now - timedelta(minutes=5)
    overdue_task.escalation_due_at = now - timedelta(minutes=1)
    overdue_task.due_at = now - timedelta(minutes=1)
    overdue_task.save(update_fields=["remind_at", "escalation_due_at", "due_at"])

    sample_rule = WorkflowRule.objects.filter(name="Critical Defect Triage SLA").first()

    return {
        "users": {
            "admin": {"username": workflow_admin.username, "password": SMOKE_PASSWORD},
            "developer": {"username": developer.username, "password": SMOKE_PASSWORD},
            "tester": {"username": tester.username, "password": SMOKE_PASSWORD},
            "outsider": {"username": outsider.username, "password": SMOKE_PASSWORD},
        },
        "defect_definition_id": defect_instance.definition_id,
        "requirement_definition_id": requirement_instance.definition_id,
        "defect_id": defect.id,
        "defect_code": defect.code,
        "overdue_defect_id": overdue_defect.id,
        "overdue_defect_code": overdue_defect.code,
        "terminated_defect_id": terminated_defect.id,
        "terminated_defect_code": terminated_defect.code,
        "terminated_instance_id": terminated_instance.id,
        "requirement_id": requirement.id,
        "requirement_code": requirement.requirement_id,
        "sample_rule_name": sample_rule.name if sample_rule else "Critical Defect Triage SLA",
    }


def start_backend():
    BACKEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    handle = BACKEND_LOG.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "manage.py",
            "runserver",
            f"{SMOKE_HOST}:{SMOKE_BACKEND_PORT}",
            "--noreload",
            "--settings=backend.settings_smoke",
        ],
        cwd=str(ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    return process, handle


def start_frontend():
    FRONTEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    handle = FRONTEND_LOG.open("w", encoding="utf-8")
    npm_executable = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    env = os.environ.copy()
    env["VITE_PROXY_TARGET"] = BACKEND_URL
    env["VITE_DEV_HOST"] = SMOKE_HOST
    env["VITE_DEV_PORT"] = str(SMOKE_FRONTEND_PORT)
    process = subprocess.Popen(
        [
            npm_executable,
            "run",
            "dev",
            "--",
            "--host",
            SMOKE_HOST,
            "--port",
            str(SMOKE_FRONTEND_PORT),
            "--strictPort",
        ],
        cwd=str(FRONTEND_DIR),
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return process, handle


def login(page, credentials):
    page.goto(f"{FRONTEND_URL}/login", wait_until="domcontentloaded")
    page.wait_for_selector(".login-form")
    page.locator("input").nth(0).fill(credentials["username"])
    page.locator("input").nth(1).fill(credentials["password"])
    page.locator(".login-button").click()
    page.wait_for_url("**/home")
    page.wait_for_selector(".home-container")
    page.wait_for_selector(".main-title")


def open_workbench(page):
    page.goto(f"{FRONTEND_URL}/manual-testcases/workflow-workbench", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="workflow-workbench-page"]')


def open_workbench_catalog(page):
    open_workbench(page)
    page.locator(".workflow-workbench-page .el-tabs__item").nth(2).click()
    page.wait_for_selector('[data-testid="workflow-catalog-layout"]')


def open_workbench_instances(page):
    open_workbench(page)
    page.locator(".workflow-workbench-page .el-tabs__item").nth(1).click()
    page.wait_for_selector('[data-testid="workflow-instance-table"]')


def open_defect_detail(page, defect_id, defect_code, timeout=60000):
    detail_url = f"{FRONTEND_URL}/manual-testcases/defects/{defect_id}"
    page.goto(detail_url, wait_until="domcontentloaded")
    try:
        page.wait_for_url(f"**/manual-testcases/defects/{defect_id}", timeout=timeout)
        page.wait_for_function(
            """([expectedCode, panelSelector]) => {
                const bodyText = document.body?.textContent || ''
                return bodyText.includes(expectedCode) && Boolean(document.querySelector(panelSelector))
            }""",
            arg=[defect_code, f'[data-testid="workflow-panel-defect-{defect_id}"]'],
            timeout=timeout,
        )
    except Exception as exc:
        raise AssertionError(build_page_debug_message(page, f"defect-{defect_id}", detail_url)) from exc


def open_requirement_detail(page, requirement_id, requirement_code, timeout=60000):
    detail_url = f"{FRONTEND_URL}/ai-generation/ai-requirements?detail_id={requirement_id}"
    page.goto(
        detail_url,
        wait_until="domcontentloaded",
    )
    try:
        page.wait_for_url(f"**/ai-generation/ai-requirements?detail_id={requirement_id}", timeout=timeout)
        page.wait_for_function(
            """([expectedCode, panelSelector]) => {
                const bodyText = document.body?.textContent || ''
                return bodyText.includes(expectedCode) && Boolean(document.querySelector(panelSelector))
            }""",
            arg=[requirement_code, f'[data-testid="workflow-panel-requirement-{requirement_id}"]'],
            timeout=timeout,
        )
    except Exception as exc:
        raise AssertionError(build_page_debug_message(page, f"requirement-{requirement_id}", detail_url)) from exc


def build_page_debug_message(page, page_key, expected_url):
    debug_dir = ROOT / "logs" / "workflow-smoke-debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = debug_dir / f"{page_key}-{int(time.time() * 1000)}.png"

    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        screenshot_path = None

    try:
        body_preview = page.evaluate("() => (document.body?.innerText || '').slice(0, 1200)")
    except Exception as body_error:
        body_preview = f"<body unavailable: {body_error}>"

    normalized_preview = re.sub(r"\s+", " ", str(body_preview or "")).strip()
    screenshot_label = str(screenshot_path) if screenshot_path else "<not captured>"
    return (
        f"Failed to open workflow business page. expected_url={expected_url}, "
        f"current_url={page.url}, screenshot={screenshot_label}, body_preview={normalized_preview}"
    )


def wait_for_workflow_step(page, biz_type, biz_id, expected_text, timeout=30000):
    selector = f'[data-testid="workflow-panel-{biz_type}-{biz_id}"] [data-testid="workflow-step-card"] strong'
    wait_for_panel_text(page, selector, expected_text, timeout=timeout)


def wait_for_workflow_assignee(page, biz_type, biz_id, expected_text, timeout=30000):
    selector = f'[data-testid="workflow-panel-{biz_type}-{biz_id}"] [data-testid="workflow-assignee-card"] strong'
    wait_for_panel_text(page, selector, expected_text, timeout=timeout)


def wait_for_panel_text(page, selector, expected_text, timeout=30000):
    page.wait_for_selector(selector)
    page.wait_for_function(
        """([targetSelector, expectedValue]) => {
            const element = document.querySelector(targetSelector)
            return Boolean(element && (element.textContent || '').includes(expectedValue))
        }""",
        arg=[selector, expected_text],
        timeout=timeout,
    )


def wait_for_no_workflow_actions(page, biz_type, biz_id, timeout=30000):
    panel_selector = f'[data-testid="workflow-panel-{biz_type}-{biz_id}"]'
    page.wait_for_selector(panel_selector)
    page.wait_for_function(
        """(targetSelector) => {
            const panel = document.querySelector(targetSelector)
            return Boolean(panel) && !panel.querySelector('[data-testid="workflow-task-actions"]')
        }""",
        arg=panel_selector,
        timeout=timeout,
    )


def wait_for_timeline_text(page, biz_type, biz_id, expected_text, timeout=30000):
    wait_for_panel_text(
        page,
        f'[data-testid="workflow-panel-{biz_type}-{biz_id}"] [data-testid="workflow-timeline"]',
        expected_text,
        timeout=timeout,
    )


def wait_for_instance_detail_text(page, expected_text, timeout=30000):
    wait_for_panel_text(
        page,
        '[data-testid="workflow-instance-detail-drawer"]',
        expected_text,
        timeout=timeout,
    )


def wait_for_table_rows_with_text(page, table_selector, expected_text, min_count, timeout=30000):
    page.wait_for_function(
        """([selector, textValue, count]) => {
            const table = document.querySelector(selector)
            if (!table) return false
            const rows = Array.from(table.querySelectorAll('tbody tr'))
            const matched = rows.filter((row) => (row.textContent || '').includes(textValue))
            return matched.length >= count
        }""",
        arg=[table_selector, expected_text, min_count],
        timeout=timeout,
    )


def fill_rule_dialog(page, *, name, priority, conditions_text, outputs_text, step_key="triage"):
    form = page.locator('[data-testid="workflow-rule-form"]')
    form.wait_for(state="visible", timeout=30000)
    form.locator('[data-testid="workflow-rule-step-key"] input').fill(step_key)
    form.locator('[data-testid="workflow-rule-name"] input').fill(name)
    form.locator('[data-testid="workflow-rule-priority"] input').fill(str(priority))
    form.locator('[data-testid="workflow-rule-conditions-input"] textarea').fill(conditions_text)
    form.locator('[data-testid="workflow-rule-outputs-input"] textarea').fill(outputs_text)


def parse_number_text(value):
    match = re.search(r"-?\d+", value or "")
    if not match:
        raise AssertionError(f"Unable to parse numeric value from: {value!r}")
    return int(match.group(0))


def read_numeric_text(page, selector, timeout=30000):
    page.wait_for_selector(selector, timeout=timeout)
    return parse_number_text(page.locator(selector).inner_text())


def wait_for_numeric_text(page, selector, expected, timeout=30000):
    page.wait_for_function(
        """([targetSelector, expectedValue]) => {
            const element = document.querySelector(targetSelector)
            if (!element) return false
            const matched = (element.textContent || '').match(/-?\\d+/)
            return Boolean(matched) && Number.parseInt(matched[0], 10) === expectedValue
        }""",
        arg=[selector, expected],
        timeout=timeout,
    )


def drag_palette_step_to_canvas(page, timeout=30000):
    palette_step = page.locator('[data-testid="workflow-definition-palette-step"]')
    canvas = page.locator('[data-testid="workflow-definition-canvas"]')
    palette_step.scroll_into_view_if_needed()
    canvas.scroll_into_view_if_needed()
    page.wait_for_selector('[data-testid="workflow-definition-palette-step"]', timeout=timeout)
    page.wait_for_selector('[data-testid="workflow-definition-canvas"]', timeout=timeout)

    palette_box = palette_step.bounding_box()
    canvas_box = canvas.bounding_box()
    if not palette_box or not canvas_box:
        raise AssertionError("Unable to resolve palette/canvas coordinates for drag and drop")

    start_x = palette_box["x"] + palette_box["width"] / 2
    start_y = palette_box["y"] + palette_box["height"] / 2
    drop_x = canvas_box["x"] + canvas_box["width"] * 0.78
    drop_y = canvas_box["y"] + canvas_box["height"] * 0.42

    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.wait_for_timeout(120)
    page.mouse.move(start_x + 40, start_y + 12, steps=8)
    page.mouse.move(drop_x, drop_y, steps=20)
    page.mouse.up()


def exercise_definition_canvas(page, original_step_name, timeout=30000):
    dialog = page.locator('[data-testid="workflow-definition-dialog"]')
    dialog.wait_for(state="visible", timeout=timeout)
    dialog.locator('[data-testid="workflow-definition-canvas"]').wait_for(state="visible", timeout=timeout)
    page.wait_for_function(
        """(selector) => {
            const element = document.querySelector(selector)
            return Boolean(
                element
                && (
                    element.querySelector('.x6-widget-minimap')
                    || element.querySelector('svg')
                ),
            )
        }""",
        arg='[data-testid="workflow-definition-minimap"]',
        timeout=timeout,
    )

    zoom_selector = '[data-testid="workflow-definition-zoom-label"]'
    initial_zoom = read_numeric_text(page, zoom_selector, timeout=timeout)
    dialog.locator('[data-testid="workflow-definition-zoom-in"]').click()
    page.wait_for_function(
        """([selector, previousValue]) => {
            const element = document.querySelector(selector)
            if (!element) return false
            const matched = (element.textContent || '').match(/-?\\d+/)
            return Boolean(matched) && Number.parseInt(matched[0], 10) > previousValue
        }""",
        arg=[zoom_selector, initial_zoom],
        timeout=timeout,
    )
    dialog.locator('[data-testid="workflow-definition-zoom-out"]').click()
    wait_for_numeric_text(page, zoom_selector, initial_zoom, timeout=timeout)

    step_count_selector = '[data-testid="workflow-definition-step-count"]'
    action_count_selector = '[data-testid="workflow-definition-action-count"]'
    initial_step_count = read_numeric_text(page, step_count_selector, timeout=timeout)
    initial_action_count = read_numeric_text(page, action_count_selector, timeout=timeout)

    dialog.locator('[data-testid="workflow-definition-add-step"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count + 1, timeout=timeout)
    if dialog.locator('[data-testid="workflow-definition-undo"]').is_disabled():
        raise AssertionError("Undo should be enabled after adding a step node")

    dialog.locator('[data-testid="workflow-definition-undo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)
    if dialog.locator('[data-testid="workflow-definition-redo"]').is_disabled():
        raise AssertionError("Redo should be enabled after undoing a step node insertion")

    dialog.locator('[data-testid="workflow-definition-redo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count + 1, timeout=timeout)

    dialog.locator('[data-testid="workflow-definition-undo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)

    drag_palette_step_to_canvas(page, timeout=timeout)
    wait_for_numeric_text(page, step_count_selector, initial_step_count + 1, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)
    if dialog.locator('[data-testid="workflow-definition-undo"]').is_disabled():
        raise AssertionError("Undo should be enabled after dragging a palette step into the canvas")

    dialog.locator('[data-testid="workflow-definition-undo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)
    if dialog.locator('[data-testid="workflow-definition-redo"]').is_disabled():
        raise AssertionError("Redo should be enabled after undoing a palette drag insertion")

    dialog.locator('[data-testid="workflow-definition-redo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count + 1, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)

    dialog.locator('[data-testid="workflow-definition-undo"]').click()
    wait_for_numeric_text(page, step_count_selector, initial_step_count, timeout=timeout)
    wait_for_numeric_text(page, action_count_selector, initial_action_count, timeout=timeout)

    canvas = dialog.locator('[data-testid="workflow-definition-canvas"]')
    canvas.get_by_text(original_step_name, exact=True).first.click()
    dialog.locator('[data-testid="workflow-definition-step-name-0"] input').wait_for(
        state="visible",
        timeout=timeout,
    )


def fill_definition_dialog(page, *, flow_name, first_step_name, timeout=30000):
    dialog = page.locator('[data-testid="workflow-definition-dialog"]')
    dialog.wait_for(state="visible", timeout=timeout)
    dialog.locator('[data-testid="workflow-definition-name"] input').fill(flow_name)
    current_first_step_name = dialog.locator('[data-testid="workflow-definition-step-name-0"] input').input_value().strip()
    exercise_definition_canvas(page, current_first_step_name, timeout=timeout)
    dialog.locator('[data-testid="workflow-definition-step-name-0"] input').fill(first_step_name)


def open_definition_version_drawer(page, definition_name, timeout=30000):
    open_workbench_catalog(page)
    card = page.locator(".definition-card", has_text=definition_name).first
    card.wait_for(state="visible", timeout=timeout)
    card.locator('[data-testid^="workflow-definition-versions-"]').click()
    page.locator('[data-testid="workflow-definition-version-drawer"]').wait_for(state="visible", timeout=timeout)


def select_el_option(page, trigger_selector, option_text, timeout=30000):
    page.locator(trigger_selector).click()
    option = page.locator(".el-select-dropdown__item", has_text=option_text).last
    option.wait_for(state="visible", timeout=timeout)
    option.click()


def confirm_message_box(page, timeout=30000):
    dialog = page.locator(".el-message-box").last
    dialog.wait_for(state="visible", timeout=timeout)
    dialog.locator(".el-button--primary").last.click()
    dialog.wait_for(state="hidden", timeout=timeout)


def submit_prompt_action(page, trigger_selector, comment, timeout=30000):
    page.locator(trigger_selector).click()
    dialog = page.locator(".el-message-box").last
    dialog.wait_for(state="visible", timeout=timeout)
    textarea = dialog.locator("textarea")
    if textarea.count():
        textarea.fill(comment)
    dialog.locator(".el-button--primary").last.click()
    dialog.wait_for(state="hidden", timeout=timeout)


def submit_transfer_dialog(page, assignee_text, comment="", timeout=30000):
    dialog = page.locator('[data-testid="workflow-transfer-dialog"]')
    dialog.wait_for(state="visible", timeout=timeout)
    dialog.locator('[data-testid="workflow-transfer-assignee"] .el-select').click()
    option = page.locator(".el-select-dropdown__item", has_text=assignee_text).last
    option.wait_for(state="visible", timeout=timeout)
    option.click()
    textarea = dialog.locator('[data-testid="workflow-transfer-comment"] textarea')
    if textarea.count():
        textarea.fill(comment)
    dialog.locator('[data-testid="workflow-transfer-submit"]').click()
    dialog.wait_for(state="hidden", timeout=timeout)


def run_browser_checks(dataset):
    from playwright.sync_api import sync_playwright

    screenshots_dir = ROOT / "logs" / "workflow-smoke-screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    created_rule_name = f"Smoke UI Rule {dataset['overdue_defect_code']}"
    updated_rule_name = f"{created_rule_name} Updated"
    updated_definition_name = f"Defect Lifecycle Smoke {dataset['defect_code']}"
    updated_first_step_name = "Smoke Defect Review"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin_context = browser.new_context(viewport={"width": 1440, "height": 960})
        admin_page = admin_context.new_page()
        login(admin_page, dataset["users"]["admin"])
        admin_page.screenshot(path=str(screenshots_dir / "01-admin-home.png"), full_page=True)

        open_workbench(admin_page)
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-defect-{dataset["defect_code"]}-approve"]'
        )
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-approve"]'
        )
        admin_page.screenshot(path=str(screenshots_dir / "02-admin-workbench-tasks.png"), full_page=True)

        open_workbench_catalog(admin_page)
        admin_page.wait_for_selector('[data-testid^="workflow-definition-"]')
        admin_page.wait_for_selector('[data-testid^="workflow-rule-conditions-"]')
        admin_page.locator(f'[data-testid="workflow-definition-edit-{dataset["defect_definition_id"]}"]').click()
        fill_definition_dialog(
            admin_page,
            flow_name=updated_definition_name,
            first_step_name=updated_first_step_name,
        )
        admin_page.locator('[data-testid="workflow-definition-save"]').click()
        admin_page.locator('[data-testid="workflow-definition-dialog"]').wait_for(state="hidden", timeout=30000)
        updated_definition_card = admin_page.locator(".definition-card", has_text=updated_definition_name).first
        updated_definition_card.wait_for(state="visible", timeout=30000)
        updated_definition_card.get_by_text(updated_first_step_name).first.wait_for(state="visible", timeout=30000)
        updated_definition_card.get_by_text("v2").first.wait_for(state="visible", timeout=30000)
        admin_page.locator('[data-testid="workflow-add-rule"]').click()
        fill_rule_dialog(
            admin_page,
            name=created_rule_name,
            priority=88,
            conditions_text='{"severity":["critical"]}',
            outputs_text='{"remind_after_hours":1,"escalation_after_hours":2}',
        )
        admin_page.locator('[data-testid="workflow-rule-save"]').click()
        admin_page.locator('[data-testid="workflow-rule-form"]').wait_for(state="detached", timeout=30000)
        admin_page.locator('[data-testid="workflow-rule-table"] .el-table__row', has_text=created_rule_name).first.wait_for(
            state="visible",
            timeout=30000,
        )

        admin_page.locator('[data-testid="workflow-rule-table"] .el-table__row', has_text=created_rule_name).first.locator(
            '[data-testid^="workflow-rule-edit-"]'
        ).click()
        fill_rule_dialog(
            admin_page,
            name=updated_rule_name,
            priority=91,
            conditions_text='{"severity":["critical"]}',
            outputs_text='{"remind_after_hours":3,"escalation_after_hours":4}',
        )
        admin_page.locator('[data-testid="workflow-rule-save"]').click()
        admin_page.locator('[data-testid="workflow-rule-form"]').wait_for(state="detached", timeout=30000)
        admin_page.locator('[data-testid="workflow-rule-table"] .el-table__row', has_text=updated_rule_name).first.wait_for(
            state="visible",
            timeout=30000,
        )

        admin_page.locator('[data-testid="workflow-rule-table"] .el-table__row', has_text=updated_rule_name).first.locator(
            '[data-testid^="workflow-rule-delete-"]'
        ).click()
        confirm_message_box(admin_page)
        admin_page.locator('[data-testid="workflow-rule-table"] .el-table__row', has_text=updated_rule_name).first.wait_for(
            state="detached",
            timeout=30000,
        )
        admin_page.screenshot(path=str(screenshots_dir / "03-admin-rule-management.png"), full_page=True)

        admin_page.locator('[data-testid="workflow-run-escalations"]').click()
        admin_page.wait_for_selector(".el-message", timeout=30000)
        open_defect_detail(admin_page, dataset["overdue_defect_id"], dataset["overdue_defect_code"])
        wait_for_timeline_text(admin_page, "defect", dataset["overdue_defect_id"], "Reminder Triggered")
        wait_for_timeline_text(admin_page, "defect", dataset["overdue_defect_id"], "Escalation Triggered")
        admin_page.screenshot(path=str(screenshots_dir / "04-admin-overdue-sla.png"), full_page=True)

        open_workbench_instances(admin_page)
        admin_page.locator(f'[data-testid="workflow-instance-view-{dataset["terminated_instance_id"]}"]').click()
        admin_page.wait_for_selector('[data-testid="workflow-instance-detail-drawer"]')
        wait_for_instance_detail_text(admin_page, dataset["terminated_defect_code"])
        submit_prompt_action(
            admin_page,
            '[data-testid="workflow-instance-detail-terminate"]',
            "Smoke terminated by admin",
        )
        admin_page.wait_for_selector('[data-testid="workflow-instance-terminated-notice"]')
        wait_for_instance_detail_text(admin_page, "已终止")
        wait_for_instance_detail_text(admin_page, "Terminate Workflow")
        admin_page.screenshot(path=str(screenshots_dir / "05-admin-terminate-instance.png"), full_page=True)

        open_defect_detail(admin_page, dataset["terminated_defect_id"], dataset["terminated_defect_code"])
        wait_for_panel_text(
            admin_page,
            f'[data-testid="workflow-panel-defect-{dataset["terminated_defect_id"]}"] [data-testid="workflow-status-card"]',
            "已终止",
        )
        admin_page.wait_for_selector('[data-testid="workflow-terminated-notice"]')
        wait_for_no_workflow_actions(admin_page, "defect", dataset["terminated_defect_id"])
        wait_for_timeline_text(admin_page, "defect", dataset["terminated_defect_id"], "Terminate Workflow")
        admin_page.screenshot(path=str(screenshots_dir / "06-admin-terminated-defect-detail.png"), full_page=True)
        admin_page.wait_for_selector('[data-testid="workflow-restart-button"]')
        admin_page.locator('[data-testid="workflow-restart-button"]').click()
        wait_for_workflow_step(admin_page, "defect", dataset["terminated_defect_id"], updated_first_step_name)
        wait_for_panel_text(
            admin_page,
            f'[data-testid="workflow-panel-defect-{dataset["terminated_defect_id"]}"] [data-testid="workflow-run-card"] strong',
            "第2次",
        )
        admin_page.wait_for_selector('[data-testid="workflow-action-approve"]')
        admin_page.screenshot(path=str(screenshots_dir / "07-admin-restarted-defect-detail.png"), full_page=True)

        open_workbench_instances(admin_page)
        wait_for_table_rows_with_text(
            admin_page,
            '[data-testid="workflow-instance-table"]',
            dataset["terminated_defect_code"],
            2,
        )
        admin_page.screenshot(path=str(screenshots_dir / "08-admin-multi-run-instances.png"), full_page=True)

        open_workbench(admin_page)
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-defect-{dataset["defect_code"]}-approve"]'
        )
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-approve"]'
        )

        submit_prompt_action(
            admin_page,
            f'[data-testid="workbench-task-action-defect-{dataset["defect_code"]}-approve"]',
            "Smoke triage accepted",
        )
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-defect-{dataset["defect_code"]}-approve"]',
            state="detached",
        )

        submit_prompt_action(
            admin_page,
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-approve"]',
            "Smoke product review approved",
        )
        open_requirement_detail(admin_page, dataset["requirement_id"], dataset["requirement_code"])
        wait_for_workflow_step(admin_page, "requirement", dataset["requirement_id"], "Technical Review")
        open_workbench(admin_page)
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-claim"]'
        )
        admin_page.locator(
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-claim"]'
        ).click()
        admin_page.wait_for_selector(
            f'[data-testid="workbench-task-action-requirement-{dataset["requirement_code"]}-transfer"]'
        )
        open_requirement_detail(admin_page, dataset["requirement_id"], dataset["requirement_code"])
        wait_for_workflow_assignee(admin_page, "requirement", dataset["requirement_id"], "WorkflowAdmin")
        admin_page.wait_for_selector('[data-testid="workflow-action-transfer"]')
        admin_page.locator('[data-testid="workflow-action-transfer"]').click()
        submit_transfer_dialog(admin_page, "WorkflowDeveloper", "Smoke transfer to developer")
        wait_for_workflow_assignee(admin_page, "requirement", dataset["requirement_id"], "WorkflowDeveloper")
        admin_page.screenshot(path=str(screenshots_dir / "07-admin-requirement-collaboration.png"), full_page=True)

        open_defect_detail(admin_page, dataset["defect_id"], dataset["defect_code"])
        wait_for_workflow_step(admin_page, "defect", dataset["defect_id"], "Development Fix")
        admin_page.screenshot(path=str(screenshots_dir / "08-admin-defect-readonly.png"), full_page=True)
        admin_context.close()

        developer_context = browser.new_context(viewport={"width": 1440, "height": 960})
        developer_page = developer_context.new_page()
        login(developer_page, dataset["users"]["developer"])

        open_defect_detail(developer_page, dataset["defect_id"], dataset["defect_code"])
        wait_for_workflow_step(developer_page, "defect", dataset["defect_id"], "Development Fix")
        developer_page.wait_for_selector('[data-testid="workflow-action-resolve"]')
        developer_page.screenshot(path=str(screenshots_dir / "09-developer-defect-fixing.png"), full_page=True)
        submit_prompt_action(
            developer_page,
            '[data-testid="workflow-action-resolve"]',
            "Smoke fix resolved",
        )
        wait_for_workflow_step(developer_page, "defect", dataset["defect_id"], "Regression Validation")

        open_requirement_detail(developer_page, dataset["requirement_id"], dataset["requirement_code"])
        wait_for_workflow_step(developer_page, "requirement", dataset["requirement_id"], "Technical Review")
        wait_for_workflow_assignee(developer_page, "requirement", dataset["requirement_id"], "WorkflowDeveloper")
        developer_page.wait_for_selector('[data-testid="workflow-action-approve"]')
        submit_prompt_action(
            developer_page,
            '[data-testid="workflow-action-approve"]',
            "Smoke tech review approved",
        )
        wait_for_workflow_step(developer_page, "requirement", dataset["requirement_id"], "QA Review")
        developer_context.close()

        tester_context = browser.new_context(viewport={"width": 1440, "height": 960})
        tester_page = tester_context.new_page()
        login(tester_page, dataset["users"]["tester"])

        open_defect_detail(tester_page, dataset["defect_id"], dataset["defect_code"])
        wait_for_workflow_step(tester_page, "defect", dataset["defect_id"], "Regression Validation")
        tester_page.wait_for_selector('[data-testid="workflow-action-approve"]')
        tester_page.screenshot(path=str(screenshots_dir / "10-tester-defect-regression.png"), full_page=True)
        submit_prompt_action(
            tester_page,
            '[data-testid="workflow-action-approve"]',
            "Smoke regression approved",
        )
        wait_for_workflow_step(tester_page, "defect", dataset["defect_id"], "-")

        open_requirement_detail(tester_page, dataset["requirement_id"], dataset["requirement_code"])
        wait_for_workflow_step(tester_page, "requirement", dataset["requirement_id"], "QA Review")
        tester_page.wait_for_selector('[data-testid="workflow-action-approve"]')
        submit_prompt_action(
            tester_page,
            '[data-testid="workflow-action-approve"]',
            "Smoke QA review approved",
        )
        wait_for_workflow_step(tester_page, "requirement", dataset["requirement_id"], "Acceptance")
        tester_context.close()

        acceptance_context = browser.new_context(viewport={"width": 1440, "height": 960})
        acceptance_page = acceptance_context.new_page()
        login(acceptance_page, dataset["users"]["admin"])

        open_requirement_detail(acceptance_page, dataset["requirement_id"], dataset["requirement_code"])
        wait_for_workflow_step(acceptance_page, "requirement", dataset["requirement_id"], "Acceptance")
        acceptance_page.wait_for_selector('[data-testid="workflow-action-approve"]')
        acceptance_page.screenshot(path=str(screenshots_dir / "11-admin-requirement-acceptance.png"), full_page=True)
        submit_prompt_action(
            acceptance_page,
            '[data-testid="workflow-action-approve"]',
            "Smoke acceptance completed",
        )
        wait_for_workflow_step(acceptance_page, "requirement", dataset["requirement_id"], "-")

        open_workbench_instances(acceptance_page)
        wait_for_table_rows_with_text(
            acceptance_page,
            '[data-testid="workflow-instance-table"]',
            dataset["defect_code"],
            1,
        )
        wait_for_table_rows_with_text(
            acceptance_page,
            '[data-testid="workflow-instance-table"]',
            dataset["requirement_code"],
            1,
        )
        wait_for_table_rows_with_text(
            acceptance_page,
            '[data-testid="workflow-instance-table"]',
            dataset["terminated_defect_code"],
            2,
        )
        acceptance_page.screenshot(path=str(screenshots_dir / "12-admin-workbench-instances.png"), full_page=True)

        open_definition_version_drawer(acceptance_page, updated_definition_name)
        version_drawer = acceptance_page.locator('[data-testid="workflow-definition-version-drawer"]')
        version_drawer.locator(".definition-version-item", has_text="v2").first.wait_for(state="visible", timeout=30000)
        version_drawer.locator(".definition-version-item", has_text="v1").first.click()
        version_drawer.locator('[data-testid="workflow-definition-version-restore"]').click()
        confirm_message_box(acceptance_page)
        version_drawer.locator(".definition-version-item", has_text="v3").first.wait_for(state="visible", timeout=30000)
        version_drawer.get_by_text("Defect Lifecycle").first.wait_for(state="visible", timeout=30000)
        version_drawer.get_by_text("Defect Triage").first.wait_for(state="visible", timeout=30000)
        acceptance_page.screenshot(path=str(screenshots_dir / "13-admin-definition-version-history.png"), full_page=True)
        acceptance_page.keyboard.press("Escape")
        version_drawer.wait_for(state="hidden", timeout=30000)

        restored_definition_card = acceptance_page.locator(".definition-card", has_text="Defect Lifecycle").first
        restored_definition_card.wait_for(state="visible", timeout=30000)
        restored_definition_card.get_by_text("v3").first.wait_for(state="visible", timeout=30000)
        restored_definition_card.get_by_text("Defect Triage").first.wait_for(state="visible", timeout=30000)
        acceptance_page.screenshot(path=str(screenshots_dir / "14-admin-definition-version-restore.png"), full_page=True)

        simulation_card = acceptance_page.locator('[data-testid="workflow-definition-simulation-card"]')
        simulation_card.wait_for(state="visible", timeout=30000)
        select_el_option(
            acceptance_page,
            '[data-testid="workflow-definition-simulation-definition"] .el-select',
            "Defect Lifecycle",
        )
        select_el_option(
            acceptance_page,
            '[data-testid="workflow-definition-simulation-severity"] .el-select',
            "严重",
        )
        acceptance_page.locator('[data-testid="workflow-definition-simulate-run"]').click()
        simulation_card.locator('[data-testid="workflow-definition-simulation-first-step"]').wait_for(
            state="visible",
            timeout=30000,
        )
        simulation_card.get_by_text("Defect Triage").first.wait_for(state="visible", timeout=30000)
        simulation_card.get_by_text("Critical Defect Triage SLA").first.wait_for(state="visible", timeout=30000)
        simulation_card.get_by_text("SLA：4h").first.wait_for(state="visible", timeout=30000)
        acceptance_page.screenshot(path=str(screenshots_dir / "15-admin-rule-simulation.png"), full_page=True)
        acceptance_context.close()
        browser.close()


def main():
    dataset = seed_smoke_data()
    backend_proc = backend_handle = None
    frontend_proc = frontend_handle = None
    try:
        backend_proc, backend_handle = start_backend()
        wait_for_http(f"{BACKEND_URL}/api/users/me/", timeout=120)

        frontend_proc, frontend_handle = start_frontend()
        wait_for_http(f"{FRONTEND_URL}/login", timeout=120)

        run_browser_checks(dataset)

        print(json.dumps({"status": "ok", "dataset": dataset}, ensure_ascii=False))
        return 0
    finally:
        terminate_process(frontend_proc)
        terminate_process(backend_proc)
        if frontend_handle:
            frontend_handle.close()
        if backend_handle:
            backend_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
