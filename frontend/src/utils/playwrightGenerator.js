class PlaywrightScriptGenerator {
  generate(graphData, options = {}) {
    const { cells = [] } = graphData || {}
    this.currentGraphHasRecordedLoginComponents = this.graphHasRecordedLoginComponents(cells)
    this.currentGraphHasMaskedPasswordComponents = this.graphHasMaskedPasswordComponents(cells)
    this.forceHeaded = Boolean(options.forceHeaded)

    if (options?.mode === 'cdp-replay') {
      return this.generateCdpReplayScript(graphData, options)
    }

    const nodes = cells.filter(cell => cell?.data?.type && cell.shape !== 'edge' && cell.data.type !== 'component')
    const edges = cells.filter(cell => cell.shape === 'edge')
    try {
      this.validateGraph(nodes, edges)
      this.runtimeStepOrder = 0

      let script = this.generateHeader()
      let body = ''
      body += this.generateBranchAwareFlowBody(nodes, edges)
      script += this.indentGeneratedPythonBody(body)
      script += this.generateFooter()

      return script
    } finally {
      this.forceHeaded = false
      this.currentGraphHasRecordedLoginComponents = false
      this.currentGraphHasMaskedPasswordComponents = false
    }
  }

  generateCdpReplayScript(graphData, options = {}) {
    const { cells = [] } = graphData || {}
    this.currentGraphHasRecordedLoginComponents = this.graphHasRecordedLoginComponents(cells)
    this.currentGraphHasMaskedPasswordComponents = this.graphHasMaskedPasswordComponents(cells)
    const nodes = cells.filter(cell => cell?.data?.type && cell.shape !== 'edge' && cell.data.type !== 'component')
    const edges = cells.filter(cell => cell.shape === 'edge')
    this.validateGraph(nodes, edges)

    this.runtimeStepOrder = 0
    const targetNodeId = options.targetNodeId || ''
    const targetComponentId = options.targetComponentId || ''
    const replaySteps = this.buildReplayStepsToTarget(nodes, edges, targetNodeId, targetComponentId)
    const body = replaySteps
      .map(step => this.generateReplayExecutionStepCode(step))
      .join('')

    const replayStartNode = nodes.find(node => node?.data?.type === 'start')
    const installRuntimeAuth = this.shouldInstallRuntimeAuth(replayStartNode?.data?.config || {})
    const helperHeader = this.generateHeader().split('\n\nasync def run_test():')[0]
    return `${helperHeader}

async def run_test():
    cdp_url = os.environ.get('TESTHUB_REPLAY_CDP_URL', '').strip()
    if not cdp_url:
        raise RuntimeError('TESTHUB_REPLAY_CDP_URL is required')

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context(ignore_https_errors=True)
        testhub_auth_init_script = ''
        testhub_runtime_auth_installed = False
        if ${this.toPythonBool(installRuntimeAuth)} and should_install_testhub_runtime_auth(page.url):
            testhub_auth_init_script = build_testhub_auth_init_script()
        if testhub_auth_init_script:
            await context.add_init_script(testhub_auth_init_script)
            testhub_runtime_auth_installed = True
        page = context.pages[0] if context.pages else await context.new_page()
        if testhub_auth_init_script:
            try:
                await page.evaluate(testhub_auth_init_script)
            except Exception:
                pass
        current_scope = page
        last_select_trigger = None
        flow_vars = load_testhub_flow_vars()
        try:
${this.indentGeneratedPythonBody(body)}
        finally:
            pass

if __name__ == "__main__":
    asyncio.run(run_test())
`
  }

  generateHeader() {
    return `"""
自动生成的 Playwright 测试脚本
生成时间: ${new Date().toLocaleString('zh-CN')}
"""

import asyncio
import json
import os
import platform
import re
import time
import traceback
from urllib.parse import urlparse, urlunparse
from playwright.async_api import async_playwright


LOCALHOST_NAMES = {'localhost', '127.0.0.1', '::1', '0.0.0.0'}


def rewrite_localhost_url_for_runtime(target_url):
    rewrite_host = os.environ.get('PLAYWRIGHT_RECORDER_LOCALHOST_REWRITE_HOST', '').strip()
    if not rewrite_host:
        return target_url

    parsed = urlparse(str(target_url))
    if (parsed.hostname or '').lower() not in LOCALHOST_NAMES:
        return target_url

    netloc = rewrite_host
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f'{auth}:{parsed.password}'
        netloc = f'{auth}@{netloc}'

    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def is_login_page_url(target_url):
    try:
        parsed = urlparse(str(target_url or ''))
    except Exception:
        return False

    candidates = [parsed.path or '']
    fragment = parsed.fragment or ''
    if fragment:
        candidates.append(fragment.split('?', 1)[0].split('&', 1)[0])

    for candidate in candidates:
        path = str(candidate or '').strip().rstrip('/').lower()
        if path == '/login' or path.endswith('/login'):
            return True
    return False


def same_origin_url(current_url, path):
    parsed = urlparse(str(current_url or ''))
    normalized_path = str(path or '/')
    if not normalized_path.startswith('/'):
        normalized_path = f'/{normalized_path}'
    if not parsed.scheme or not parsed.netloc:
        return normalized_path
    return urlunparse((parsed.scheme, parsed.netloc, normalized_path, '', '', ''))


def strip_api_path(api_origin):
    parsed = urlparse(str(api_origin or ''))
    if not parsed.scheme or not parsed.netloc:
        return ''
    path = (parsed.path or '').rstrip('/')
    if path == '/api':
        path = ''
    elif path.endswith('/api'):
        path = path[:-4]
    return urlunparse((parsed.scheme, parsed.netloc, path or '/', '', '', ''))


def same_web_origin(left, right):
    try:
        left_parsed = urlparse(str(left or ''))
        right_parsed = urlparse(str(right or ''))
    except Exception:
        return False
    if not left_parsed.scheme or not left_parsed.netloc or not right_parsed.scheme or not right_parsed.netloc:
        return False

    def normalized_port(parsed):
        if parsed.port:
            return parsed.port
        return 443 if parsed.scheme == 'https' else 80

    return (
        left_parsed.scheme.lower(),
        (left_parsed.hostname or '').lower(),
        normalized_port(left_parsed),
    ) == (
        right_parsed.scheme.lower(),
        (right_parsed.hostname or '').lower(),
        normalized_port(right_parsed),
    )


def should_install_testhub_runtime_auth(target_url):
    platform_web_origin = strip_api_path(os.environ.get('TESTHUB_PLAYWRIGHT_API_ORIGIN', '').strip())
    return bool(platform_web_origin and same_web_origin(target_url, platform_web_origin))


def load_testhub_flow_vars():
    flow_vars = {}
    raw_vars = os.environ.get('TESTHUB_FLOW_VARIABLES_JSON', '').strip()
    if raw_vars:
        try:
            parsed_vars = json.loads(raw_vars)
            if isinstance(parsed_vars, dict):
                for key, value in parsed_vars.items():
                    flow_vars[str(key)] = '' if value is None else str(value)
        except Exception:
            pass

    prefix = 'TESTHUB_FLOW_VAR_'
    for key, value in os.environ.items():
        if key.startswith(prefix):
            flow_vars[key[len(prefix):]] = value
    return flow_vars


def require_testhub_flow_var(flow_vars, variable_name, label=''):
    value = flow_vars.get(variable_name, '')
    if value == '':
        display_name = label or variable_name
        raise RuntimeError(f'Missing required replay input: {display_name} ({variable_name})')
    return str(value)


def resolve_browser_runtime_options(requested_headless, maximize, viewport_width, viewport_height):
    has_linux_display = True
    if platform.system() == 'Linux':
        has_linux_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))

    actual_headless = requested_headless or not has_linux_display
    if not requested_headless and not has_linux_display:
        print('No display server detected; running Playwright in headless mode.')

    launch_options = {'headless': actual_headless}
    viewport = {'width': viewport_width, 'height': viewport_height}
    if maximize and not actual_headless:
        launch_options['args'] = ['--start-maximized', '--window-position=0,0']
        viewport = None

    return launch_options, viewport


async def apply_browser_window_geometry(context, page, maximize, viewport_width, viewport_height):
    if page is None or not maximize:
        return
    try:
        cdp_session = await context.new_cdp_session(page)
        window_info = await cdp_session.send('Browser.getWindowForTarget')
        window_id = window_info.get('windowId')
        if not window_id:
            return
        await cdp_session.send('Browser.setWindowBounds', {
            'windowId': window_id,
            'bounds': {'windowState': 'maximized'},
        })
    except Exception:
        try:
            await page.set_viewport_size({'width': int(viewport_width), 'height': int(viewport_height)})
        except Exception:
            pass


def build_testhub_auth_init_script():
    access_token = os.environ.get('TESTHUB_PLAYWRIGHT_ACCESS_TOKEN', '').strip()
    if not access_token:
        return ''

    user_json = os.environ.get('TESTHUB_PLAYWRIGHT_USER_JSON', '').strip() or '{}'
    try:
        json.loads(user_json)
    except Exception:
        user_json = '{}'

    payload = {
        'access': access_token,
        'refresh': os.environ.get('TESTHUB_PLAYWRIGHT_REFRESH_TOKEN', '').strip(),
        'expires': os.environ.get('TESTHUB_PLAYWRIGHT_TOKEN_EXPIRES_AT', '').strip(),
        'userJson': user_json,
    }
    return f"""
(() => {{
  const payload = {json.dumps(payload, ensure_ascii=False)};
  if (!payload.access) {{
    return;
  }}
  window.localStorage.setItem('access_token', payload.access);
  if (payload.refresh) {{
    window.localStorage.setItem('refresh_token', payload.refresh);
  }}
  window.localStorage.setItem('token_expires_at', payload.expires || String(Date.now() + 30 * 60 * 1000));
  window.localStorage.setItem('user', payload.userJson || '{{}}');
}})();
"""


async def capture_testhub_flow_screenshot(page):
    if page is None:
        return ''
    try:
        import base64
        image_bytes = await page.screenshot(full_page=True)
        return base64.b64encode(image_bytes).decode('ascii')
    except Exception:
        return ''


async def emit_testhub_flow_event(page, payload):
    try:
        safe_payload = dict(payload or {})
        safe_payload['timestamp'] = int(time.time() * 1000)
        safe_payload['url'] = page.url if page is not None else ''
        if safe_payload.get('event') != 'start':
            safe_payload['screenshot_base64'] = await capture_testhub_flow_screenshot(page)
        print('__TESTHUB_FLOW_EVENT__' + json.dumps(safe_payload, ensure_ascii=False, default=str), flush=True)
    except Exception as event_error:
        print('__TESTHUB_FLOW_EVENT__' + json.dumps({
            'event': 'failed',
            'status': 'failed',
            'step_key': 'event-emitter',
            'title': '执行事件记录',
            'error': str(event_error),
            'timestamp': int(time.time() * 1000),
        }, ensure_ascii=False), flush=True)


async def run_testhub_flow_step(page, payload, action):
    safe_payload = dict(payload or {})
    started = time.monotonic()
    try:
        await emit_testhub_flow_event(page, {
            **safe_payload,
            'event': 'start',
            'status': 'running',
        })
        result = await action()
        output = result if isinstance(result, dict) else {}
        result_status = str(output.pop('__testhub_status', 'success') or 'success').lower()
        event_name = 'skipped' if result_status == 'skipped' else 'success'
        await emit_testhub_flow_event(page, {
            **safe_payload,
            'event': event_name,
            'status': result_status,
            'duration': round(time.monotonic() - started, 3),
            'output': output,
        })
        return result
    except Exception as error:
        await emit_testhub_flow_event(page, {
            **safe_payload,
            'event': 'failed',
            'status': 'failed',
            'duration': round(time.monotonic() - started, 3),
            'error': ''.join(traceback.format_exception(type(error), error, error.__traceback__)),
        })
        raise


async def safe_wait_for_network_idle(page, timeout=5000):
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except Exception:
        pass


async def wait_after_click(page):
    await page.wait_for_timeout(500)
    await safe_wait_for_network_idle(page, timeout=3000)


async def wait_until_not_login_page(page, timeout=8000):
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        if not is_login_page_url(page.url):
            return True
        await page.wait_for_timeout(250)
    return not is_login_page_url(page.url)


def normalize_testhub_assertion_value(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value).strip()


def assert_testhub_value(actual, expected, operator='equals'):
    actual_text = normalize_testhub_assertion_value(actual)
    expected_text = normalize_testhub_assertion_value(expected)
    operator_key = str(operator or 'equals')

    if operator_key == 'equals':
        passed = actual_text == expected_text
    elif operator_key == 'notEquals':
        passed = actual_text != expected_text
    elif operator_key == 'contains':
        passed = expected_text in actual_text
    elif operator_key == 'notContains':
        passed = expected_text not in actual_text
    elif operator_key == 'startsWith':
        passed = actual_text.startswith(expected_text)
    elif operator_key == 'endsWith':
        passed = actual_text.endswith(expected_text)
    elif operator_key == 'regex':
        passed = re.search(expected_text, actual_text) is not None
    else:
        raise AssertionError(f'Unsupported assertion operator: {operator_key}')

    if not passed:
        raise AssertionError(
            f'Assertion failed: actual={actual_text!r}, expected={expected_text!r}, operator={operator_key}'
        )

    return {
        'actual': actual_text,
        'expected': expected_text,
        'operator': operator_key,
    }


async def read_testhub_locator_value(locator):
    try:
        return await locator.input_value()
    except Exception:
        return await read_testhub_visible_text(locator)


async def read_testhub_visible_text(locator):
    try:
        if not await locator.is_visible():
            return ''
    except Exception:
        pass
    try:
        return await locator.inner_text() or ''
    except Exception:
        try:
            return await locator.text_content() or ''
        except Exception:
            return ''


async def select_trigger_has_value(trigger, option_text='', allow_any_value=False):
    if trigger is None:
        return False
    try:
        text = await trigger.evaluate(
            """
            (el, { wanted, allowAnyValue }) => {
              const normalize = value => String(value || '').replace(/\\\\s+/g, ' ').trim();
              const root = el.closest('.el-select') || el.closest('.el-form-item') || el;
              const placeholderPattern = /请选择|请输入|选择|输入|Select|Please/i;
              const values = [
                el.value,
                el.getAttribute('aria-label'),
                el.getAttribute('title'),
                root ? Array.from(root.querySelectorAll('.el-select__selected-item, .el-select__placeholder, .el-input__inner')).map(item => item.innerText || item.getAttribute('aria-label') || item.getAttribute('title') || item.value || '').join(' ') : '',
                root ? root.innerText || root.getAttribute('aria-label') || root.getAttribute('title') || '' : '',
              ].map(normalize).filter(Boolean).filter(value => !placeholderPattern.test(value));
              const normalizedWanted = normalize(wanted);
              if (normalizedWanted && values.some(value => value === normalizedWanted || value.includes(normalizedWanted))) {
                return true;
              }
              return Boolean(allowAnyValue && values.length);
            }
            """,
            {'wanted': option_text, 'allowAnyValue': allow_any_value},
        )
        return bool(text)
    except Exception:
        return False


async def click_visible_select_option(page, option_text, trigger=None, timeout=10000, allow_fallback=True):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        clicked = await page.evaluate(
            """
            ({ text, allowFallback }) => {
              const normalize = value => String(value || '').replace(/\\\\s+/g, ' ').trim();
              const wanted = normalize(text);
              const isVisible = element => {
                if (!element) return false;
                const style = window.getComputedStyle(element);
                if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
              };
              const candidates = Array.from(document.querySelectorAll(
                '.el-select-dropdown__item, [role="option"]'
              )).filter(element => {
                if (!isVisible(element)) return false;
                const disabled = element.classList.contains('is-disabled') || element.getAttribute('aria-disabled') === 'true';
                if (disabled) return false;
                const textValue = normalize(
                  element.innerText ||
                  element.getAttribute('aria-label') ||
                  element.getAttribute('title') ||
                  ''
                );
                return Boolean(textValue) && !/无数据|暂无数据|No data/i.test(textValue);
              });
              const option = candidates.find(element => {
                const textValue = normalize(
                  element.innerText ||
                  element.getAttribute('aria-label') ||
                  element.getAttribute('title') ||
                  ''
                );
                return wanted && (textValue === wanted || textValue.includes(wanted));
              }) || (allowFallback ? candidates[0] : null);
              if (!option) return false;
              option.click();
              return true;
            }
            """,
            {'text': option_text, 'allowFallback': allow_fallback},
        )
        if clicked:
            await page.wait_for_timeout(700)
            return
        if await select_trigger_has_value(trigger, option_text, allow_any_value=allow_fallback):
            return
        if trigger is not None:
            try:
                await trigger.click(timeout=1000)
            except Exception:
                pass
        await page.wait_for_timeout(250)

    if await select_trigger_has_value(trigger, option_text, allow_any_value=allow_fallback):
        return
    raise TimeoutError(f'No visible select option found: {option_text}')


async def click_visible_element_by_text(page, element_text, dialog_only=False):
    return await page.evaluate(
        """
        payload => {
          const normalize = value => String(value || '').replace(/\\\\s+/g, ' ').trim();
          const compact = value => normalize(value).replace(/[\\\\s:;,._|/\\\\\\\\-]+/g, '');
          const wanted = normalize(payload && payload.text);
          const compactWanted = compact(wanted);
          const dialogOnly = Boolean(payload && payload.dialogOnly);
          const isVisible = element => {
            if (!element) return false;
            const style = window.getComputedStyle(element);
            if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          };
          const isDisabled = element => {
            if (!element) return true;
            return Boolean(
              element.disabled ||
              element.getAttribute('disabled') !== null ||
              element.getAttribute('aria-disabled') === 'true' ||
              element.classList.contains('is-disabled')
            );
          };
          const textOf = element => normalize(
            element.innerText ||
            element.getAttribute('aria-label') ||
            element.getAttribute('title') ||
            ''
          );
          const scoreText = text => {
            const value = normalize(text);
            if (!wanted || !value) return 0;
            const compactValue = compact(value);
            if (!compactValue) return 0;
            if (value === wanted || compactValue === compactWanted) return 10000 - Math.min(value.length, 500);
            if (value.includes(wanted) || compactValue.includes(compactWanted)) return 8000 - Math.min(value.length, 500);
            if (wanted.includes(value) && value.length >= 4) return 6000 + Math.min(value.length, 300);
            if (compactWanted.includes(compactValue) && compactValue.length >= 4) return 5500 + Math.min(compactValue.length, 300);
            return 0;
          };
          const clickableSelector = [
            'button',
            '[role="button"]',
            'a',
            '[role="link"]',
            '[role="menuitem"]',
            '[role="tab"]',
            '.el-card',
            '.el-card__body',
            '.el-menu-item',
            '.el-sub-menu__title',
            '.module-card',
            '.app-card',
            '.workspace-card',
            '[onclick]',
            '[tabindex]:not([tabindex="-1"])'
          ].join(',');
          const dialogs = Array.from(document.querySelectorAll('.el-message-box, .el-dialog, [role="dialog"]'))
            .filter(isVisible)
            .reverse();
          const scopes = dialogOnly ? dialogs : [document, ...dialogs];
          const candidates = [];
          const seen = new Set();
          const addCandidate = (element, score, priority) => {
            if (!element || seen.has(element) || !isVisible(element) || isDisabled(element)) return;
            if (score <= 0) return;
            const rect = element.getBoundingClientRect();
            let contextPriority = 0;
            if (element.closest('.el-popper, .el-popover, .el-dropdown-menu, .el-cascader__dropdown, .context-menu')) {
              contextPriority += 500;
            }
            if (rect.left > 240) {
              contextPriority += 250;
            }
            if (element.classList.contains('is-active') || element.closest('.is-active')) {
              contextPriority -= 150;
            }
            seen.add(element);
            candidates.push({ element, score: score + priority + contextPriority });
          };
          for (const scope of scopes) {
            const clickables = Array.from(scope.querySelectorAll(clickableSelector));
            for (const element of clickables) {
              addCandidate(element, scoreText(textOf(element)), 100);
            }
            const textElements = Array.from(scope.querySelectorAll('span,div,p,h1,h2,h3,h4,h5,h6,li,td,th'));
            for (const element of textElements) {
              const score = scoreText(textOf(element));
              if (score <= 0) continue;
              const clickable = element.closest(clickableSelector);
              if (clickable) {
                addCandidate(clickable, score, 60);
                continue;
              }
              const style = window.getComputedStyle(element);
              if (style.cursor === 'pointer') {
                addCandidate(element, score, 20);
              }
            }
          }
          if (!candidates.length) return false;
          candidates.sort((left, right) => right.score - left.score);
          const target = candidates[0].element;
          target.scrollIntoView({ block: 'center', inline: 'center' });
          target.click();
          return true;
        }
        """,
        {'text': element_text, 'dialogOnly': dialog_only},
    )


async def click_playwright_locator(candidate, timeout=1500):
    if candidate is None:
        return False
    try:
        await candidate.first.click(timeout=timeout)
        return True
    except Exception:
        return False


async def read_checkable_locator_state(candidate, timeout=700):
    if candidate is None:
        return None
    target = candidate.first
    try:
        return bool(await target.is_checked(timeout=timeout))
    except Exception:
        pass
    try:
        state = await target.evaluate(
            """
            element => {
              const normalizeState = value => {
                const normalized = String(value || '').toLowerCase();
                if (normalized === 'true' || normalized === 'checked') return true;
                if (normalized === 'false' || normalized === 'mixed' || normalized === 'unchecked') return false;
                return null;
              };
              const readElement = el => {
                if (!el) return null;
                const tag = String(el.tagName || '').toLowerCase();
                const type = String(el.getAttribute('type') || '').toLowerCase();
                if (tag === 'input' && ['checkbox', 'radio'].includes(type)) {
                  return Boolean(el.checked);
                }
                const aria = normalizeState(el.getAttribute('aria-checked'));
                if (aria !== null) return aria;
                const root = el.closest('.el-checkbox, .el-radio, [role="checkbox"], [role="radio"], label') || el;
                const rootAria = normalizeState(root.getAttribute('aria-checked'));
                if (rootAria !== null) return rootAria;
                const input = root.querySelector('input[type="checkbox"], input[type="radio"]');
                if (input) return Boolean(input.checked);
                if (root.classList && root.classList.contains('is-checked')) return true;
                if (root.querySelector('.is-checked, [aria-checked="true"]')) return true;
                return null;
              };
              return readElement(element);
            }
            """,
            timeout=timeout,
        )
        if state is True or state is False:
            return bool(state)
    except Exception:
        pass
    try:
        aria_checked = await target.get_attribute('aria-checked', timeout=timeout)
        normalized = str(aria_checked or '').strip().lower()
        if normalized in ('true', 'checked'):
            return True
        if normalized in ('false', 'mixed', 'unchecked'):
            return False
    except Exception:
        pass
    return None


async def set_checkable_dom_state(candidate, checked, control_type='checkbox', timeout=1000):
    if candidate is None:
        return False
    try:
        result = await candidate.first.evaluate(
            """
            (element, payload) => {
              const type = payload && payload.controlType === 'radio' ? 'radio' : 'checkbox';
              const desired = Boolean(payload && payload.checked);
              const owner = element.closest('label') ||
                element.closest('.el-checkbox, .el-radio, [role="checkbox"], [role="radio"], [aria-checked]') ||
                element;
              const input = (
                String(element.tagName || '').toLowerCase() === 'input' &&
                String(element.getAttribute('type') || '').toLowerCase() === type
              )
                ? element
                : owner.querySelector('input[type="' + type + '"]') || element.querySelector('input[type="' + type + '"]');
              if (!input) return false;
              if (type === 'radio' && !desired) return false;
              input.checked = desired;
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
              if (owner && owner.classList) {
                owner.classList.toggle('is-checked', desired);
              }
              if (owner && owner.setAttribute) {
                owner.setAttribute('aria-checked', String(desired));
              }
              return Boolean(input.checked) === desired;
            }
            """,
            {'checked': checked, 'controlType': control_type},
            timeout=timeout,
        )
        return bool(result)
    except Exception:
        return False


async def set_checkable_locator_state(page, candidate, checked, control_type='checkbox'):
    if candidate is None:
        return False
    target = candidate.first
    native_selector = 'input[type="radio"]' if control_type == 'radio' else 'input[type="checkbox"]'
    current_state = await read_checkable_locator_state(candidate)
    if current_state is checked:
        return True

    for control in (target, target.locator(native_selector).first):
        try:
            if checked:
                await control.check(timeout=2500)
            else:
                await control.uncheck(timeout=2500)
            await wait_after_click(page)
            final_state = await read_checkable_locator_state(control)
            return final_state is None or final_state is checked
        except Exception:
            pass

    if await set_checkable_dom_state(candidate, checked, control_type=control_type):
        await wait_after_click(page)
        final_state = await read_checkable_locator_state(candidate)
        if final_state is None or final_state is checked:
            return True

    try:
        await target.click(timeout=1800)
        await wait_after_click(page)
        final_state = await read_checkable_locator_state(candidate)
        if final_state is checked:
            return True
        inner_state = await read_checkable_locator_state(target.locator(native_selector))
        if inner_state is checked:
            return True
        if await set_checkable_dom_state(candidate, checked, control_type=control_type):
            await wait_after_click(page)
            final_state = await read_checkable_locator_state(candidate)
            return final_state is None or final_state is checked
        return False
    except Exception:
        return False


async def click_checkable_in_scope(page, scope, checked, element_text='', control_type='checkbox', recorded_rect=None):
    search_scope = scope or page
    try:
        result = await search_scope.locator('body').evaluate(
            """
            (root, payload) => {
              const normalize = value => String(value || '').replace(/\\\\s+/g, ' ').trim();
              const wanted = normalize(payload && payload.text);
              const wantedLower = wanted.toLowerCase();
              const type = payload && payload.controlType === 'radio' ? 'radio' : 'checkbox';
              const desired = Boolean(payload && payload.checked);
              const rect = payload && payload.rect && Number.isFinite(Number(payload.rect.x))
                ? payload.rect
                : null;
              const genericText = new Set(['checkbox', 'radio', 'switch', '\\u590d\\u9009\\u6846', '\\u591a\\u9009\\u6846', '\\u5355\\u9009\\u6846']);
              const hasMeaningfulText = Boolean(wanted) && !genericText.has(wantedLower);
              const isVisible = element => {
                if (!element) return false;
                const style = window.getComputedStyle(element);
                if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) return false;
                const box = element.getBoundingClientRect();
                return box.width > 0 && box.height > 0;
              };
              const isDisabled = (element, input) => Boolean(
                (input && input.disabled) ||
                (element && (
                  element.disabled ||
                  element.getAttribute('disabled') !== null ||
                  element.getAttribute('aria-disabled') === 'true' ||
                  element.classList.contains('is-disabled')
                ))
              );
              const ownerOf = element => {
                if (!element) return null;
                return element.closest('label') ||
                  element.closest('.el-checkbox, .el-radio, [role="checkbox"], [role="radio"], [aria-checked]') ||
                  element;
              };
              const controlOf = element => {
                if (!element) return null;
                const tag = String(element.tagName || '').toLowerCase();
                const inputType = String(element.getAttribute('type') || '').toLowerCase();
                if (tag === 'input' && inputType === type) return element;
                return element.querySelector('input[type="' + type + '"]');
              };
              const stateOf = element => {
                const owner = ownerOf(element) || element;
                const input = controlOf(owner) || controlOf(element);
                if (input) return Boolean(input.checked);
                const ariaValue = String((owner && owner.getAttribute('aria-checked')) || (element && element.getAttribute('aria-checked')) || '').toLowerCase();
                if (ariaValue === 'true' || ariaValue === 'checked') return true;
                if (ariaValue === 'false' || ariaValue === 'mixed' || ariaValue === 'unchecked') return false;
                if (owner && owner.classList && owner.classList.contains('is-checked')) return true;
                if (owner && owner.querySelector('.is-checked, [aria-checked="true"]')) return true;
                return null;
              };
              const setNativeState = candidate => {
                const input = candidate && candidate.input;
                if (!input) return stateOf(candidate && (candidate.owner || candidate.target));
                if (type === 'radio' && !desired) return stateOf(candidate.owner || candidate.target);
                input.checked = desired;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                if (candidate.owner && candidate.owner.classList) {
                  candidate.owner.classList.toggle('is-checked', desired);
                }
                if (candidate.owner && candidate.owner.setAttribute) {
                  candidate.owner.setAttribute('aria-checked', String(desired));
                }
                return stateOf(candidate.owner || candidate.target || input);
              };
              const textOf = element => {
                const owner = ownerOf(element) || element;
                const input = controlOf(owner) || controlOf(element);
                return normalize([
                  owner && owner.innerText,
                  owner && owner.getAttribute('aria-label'),
                  owner && owner.getAttribute('title'),
                  input && input.getAttribute('aria-label'),
                  input && input.getAttribute('title'),
                  input && input.getAttribute('name'),
                  input && input.id,
                  input && input.value,
                ].filter(Boolean).join(' '));
              };
              const distanceScore = element => {
                if (!rect) return 0;
                const box = element.getBoundingClientRect();
                const targetX = Number(rect.x || 0) + Number(rect.width || 0) / 2;
                const targetY = Number(rect.y || 0) + Number(rect.height || 0) / 2;
                const candidateX = box.x + box.width / 2;
                const candidateY = box.y + box.height / 2;
                const distance = Math.hypot(candidateX - targetX, candidateY - targetY);
                return Math.max(0, 6000 - distance * 30);
              };
              const selectorGroups = type === 'radio'
                ? ['input[type="radio"]', '[role="radio"]', '.el-radio', '.el-radio__input', 'label:has(input[type="radio"])']
                : ['input[type="checkbox"]', '[role="checkbox"]', '[role="switch"]', '.el-checkbox', '.el-checkbox__input', 'label:has(input[type="checkbox"])'];
              const rawCandidates = [];
              for (const selector of selectorGroups) {
                try {
                  rawCandidates.push(...Array.from(root.querySelectorAll(selector)));
                } catch (error) {
                  // Ignore unsupported selector variants in older Chromium runtimes.
                }
              }
              const seen = new Set();
              const candidates = [];
              for (const element of rawCandidates) {
                const owner = ownerOf(element);
                const input = controlOf(owner) || controlOf(element);
                const target = [owner, element, input].find(isVisible) || owner || element || input;
                if (!target || !isVisible(target) || isDisabled(target, input)) continue;
                const key = owner || target;
                if (seen.has(key)) continue;
                seen.add(key);
                const text = textOf(target);
                let score = 100;
                if (hasMeaningfulText) {
                  const textLower = text.toLowerCase();
                  if (textLower === wantedLower) {
                    score += 10000 - Math.min(text.length, 500);
                  } else if (textLower.includes(wantedLower) || wantedLower.includes(textLower)) {
                    score += 7000 - Math.min(text.length, 500);
                  } else {
                    continue;
                  }
                }
                score += distanceScore(target);
                const state = stateOf(target);
                if (state === desired) score += 1200;
                if (state !== desired) score += 2200;
                candidates.push({ owner, input, target, state, score });
              }
              if (!candidates.length) {
                return { done: false, reason: 'no-candidate' };
              }
              candidates.sort((left, right) => right.score - left.score);
              const alreadyMatched = candidates.find(candidate => candidate.state === desired);
              if (alreadyMatched && (hasMeaningfulText || rect || candidates.length === 1)) {
                return { done: true, state: alreadyMatched.state, alreadyMatched: true };
              }
              if (!hasMeaningfulText && !rect && candidates.length > 1) {
                return { done: false, reason: 'ambiguous-generic-checkable', count: candidates.length };
              }
              const candidate = candidates.find(item => item.state !== desired) || candidates[0];
              const clickTarget = candidate.target || candidate.owner || candidate.input;
              clickTarget.scrollIntoView({ block: 'center', inline: 'center' });
              clickTarget.click();
              let nextState = stateOf(candidate.owner || clickTarget);
              if (nextState !== desired) {
                nextState = setNativeState(candidate);
              }
              return { done: nextState === desired, state: nextState, clicked: true };
            }
            """,
            {
                'checked': checked,
                'text': element_text,
                'controlType': control_type,
                'rect': recorded_rect,
            },
            timeout=2500,
        )
        if isinstance(result, dict) and result.get('done'):
            await wait_after_click(page)
            return True
    except Exception:
        pass
    return False


async def set_checkable_state(page, locator_candidates, checked, element_text='', control_type='checkbox', scope=None, recorded_rect=None):
    candidates = locator_candidates if isinstance(locator_candidates, (list, tuple)) else [locator_candidates]
    for candidate in candidates:
        if await set_checkable_locator_state(page, candidate, checked, control_type=control_type):
            return

    if await click_checkable_in_scope(
        page,
        scope or page,
        checked,
        element_text=element_text,
        control_type=control_type,
        recorded_rect=recorded_rect,
    ):
        return

    action_name = 'check' if checked else 'uncheck'
    raise TimeoutError(f'Unable to {action_name} {control_type}: {element_text}')


async def click_generic_element(page, locator, element_text='', scope=None):
    last_error = None
    try:
        await locator.first.click(timeout=8000)
        await wait_after_click(page)
        return
    except Exception as error:
        last_error = error

    search_scope = scope or page
    if element_text:
        for candidate in (
            search_scope.get_by_text(element_text, exact=True),
            search_scope.get_by_text(element_text),
        ):
            if await click_playwright_locator(candidate, timeout=3000):
                await wait_after_click(page)
                return

    if element_text:
        allow_page_fallback = scope is None or scope is page
        if allow_page_fallback:
            clicked = await click_visible_element_by_text(page, element_text, dialog_only=False)
            if clicked:
                await wait_after_click(page)
                return

    if last_error:
        raise last_error
    raise TimeoutError(f'No visible element found: {element_text}')


async def click_button_by_name(page, locator, button_text, expect_not_login=False, scope=None):
    deadline = time.monotonic() + 12
    last_error = None
    search_scope = scope or page
    allow_page_fallback = scope is None or scope is page
    while time.monotonic() < deadline:
        if button_text:
            try:
                dialog_scope = search_scope.locator('.el-message-box, .el-dialog, [role="dialog"]').last
                for candidate in (
                    dialog_scope.get_by_role('button', name=button_text),
                    dialog_scope.get_by_text(button_text),
                ):
                    if await click_playwright_locator(candidate):
                        await wait_after_click(page)
                        if expect_not_login and not await wait_until_not_login_page(page):
                            raise RuntimeError('Login click did not leave the login page.')
                        return
            except Exception:
                pass

        try:
            await locator.first.click(timeout=3000)
            await wait_after_click(page)
            if expect_not_login and not await wait_until_not_login_page(page):
                raise RuntimeError('Login click did not leave the login page.')
            return
        except Exception as error:
            last_error = error

        if button_text:
            for candidate in (
                search_scope.get_by_role('button', name=button_text),
                search_scope.get_by_text(button_text, exact=True),
                search_scope.get_by_text(button_text),
            ):
                if await click_playwright_locator(candidate):
                    await wait_after_click(page)
                    if expect_not_login and not await wait_until_not_login_page(page):
                        raise RuntimeError('Login click did not leave the login page.')
                    return

        if allow_page_fallback:
            clicked = await click_visible_element_by_text(page, button_text, dialog_only=False)
            if clicked:
                await wait_after_click(page)
                if expect_not_login and not await wait_until_not_login_page(page):
                    raise RuntimeError('Login click did not leave the login page.')
                return

        await page.wait_for_timeout(300)

    if last_error:
        raise last_error
    raise TimeoutError(f'No visible button found: {button_text}')


async def run_test():
    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        current_scope = None
        testhub_runtime_auth_installed = False
        last_select_trigger = None
        flow_vars = load_testhub_flow_vars()
        try:
`
  }

  generateFooter() {
    return `
        finally:
            if browser is not None:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
`
  }

  indentGeneratedPythonBody(code) {
    return String(code || '')
      .split('\n')
      .map(line => line ? `    ${line}` : line)
      .join('\n')
  }

  validateGraph(nodes, edges) {
    if (!nodes.length) {
      throw new Error('流程图为空，请先添加节点')
    }

    const startNodes = nodes.filter(node => node?.data?.type === 'start')
    if (!startNodes.length) {
      throw new Error('流程缺少开始节点，请添加「开始」节点并设置启动 URL')
    }

    const reachableNodeIds = this.getReachableNodeIds(startNodes, edges)
    const disconnectedNodes = nodes.filter(node => {
      const nodeType = node?.data?.type
      return nodeType !== 'start' && ['page', 'operation', 'end'].includes(nodeType) && !reachableNodeIds.has(node.id)
    })

    if (disconnectedNodes.length) {
      const nodeNames = disconnectedNodes
        .map(node => node?.data?.config?.name || node?.data?.config?.pageName || node.id)
        .slice(0, 5)
        .join('、')
      throw new Error(`流程存在未连接到开始节点的节点：${nodeNames}。请从「开始」节点连线后再生成脚本`)
    }
  }

  getReachableNodeIds(startNodes, edges) {
    const adjacency = new Map()
    edges
      .filter(edge => edge?.source?.cell && edge?.target?.cell)
      .forEach(edge => {
        if (!adjacency.has(edge.source.cell)) {
          adjacency.set(edge.source.cell, [])
        }
        adjacency.get(edge.source.cell).push(edge.target.cell)
      })

    const reachable = new Set()
    const queue = startNodes.map(node => node.id).filter(Boolean)
    queue.forEach(nodeId => reachable.add(nodeId))

    while (queue.length) {
      const currentId = queue.shift()
      ;(adjacency.get(currentId) || []).forEach(targetId => {
        if (!reachable.has(targetId)) {
          reachable.add(targetId)
          queue.push(targetId)
        }
      })
    }

    return reachable
  }

  generateBranchAwareFlowBody(nodes, edges) {
    const branches = this.buildExecutionBranches(nodes, edges)
    if (!branches.length) {
      const nodeMap = new Map(nodes.map(node => [node.id, node]))
      const executionOrder = this.topologicalSort(nodes, edges)
      return executionOrder
        .map(nodeId => nodeMap.get(nodeId))
        .filter(Boolean)
        .map(node => this.generateNodeCode(node))
        .join('')
    }

    return branches.map((branch, index) => {
      const branchSetup = `        if browser is not None:
            await browser.close()
        browser = None
        context = None
        page = None
        current_scope = None
        last_select_trigger = None
        flow_vars = load_testhub_flow_vars()
        print('Executing visual flow branch ${index + 1}/${branches.length}')
`
      return branchSetup + branch
        .map(step => this.generateExecutionStepCode(step))
        .join('')
    }).join('\n')
  }

  buildReplayStepsToTarget(nodes, edges, targetNodeId = '', targetComponentId = '') {
    const branches = this.buildExecutionBranches(nodes, edges)
    if (!branches.length) {
      return this.buildTopologicalReplayStepsToTarget(nodes, edges, targetNodeId, targetComponentId)
    }

    const candidates = branches
      .map(branch => this.truncateBranchToTarget(branch, targetNodeId, targetComponentId))
      .filter(steps => steps.length)

    if (candidates.length) {
      return candidates.sort((left, right) => left.length - right.length)[0]
    }

    return branches[0] || []
  }

  buildTopologicalReplayStepsToTarget(nodes, edges, targetNodeId = '', targetComponentId = '') {
    const nodeMap = new Map(nodes.map(node => [node.id, node]))
    const executionOrder = this.topologicalSort(nodes, edges)
    const steps = []
    for (const nodeId of executionOrder) {
      const node = nodeMap.get(nodeId)
      if (!node) {
        continue
      }
      const isTargetNode = targetNodeId && node.id === targetNodeId
      if (node?.data?.type === 'page') {
        const pageSteps = this.buildPageExecutionVariants(node, [])
        const variantSteps = pageSteps[0]?.steps || [{ kind: 'node', node }]
        variantSteps.forEach(step => {
          if (isTargetNode && targetComponentId && step.kind === 'page-components') {
            const componentIndex = (step.components || []).findIndex(component => component.id === targetComponentId)
            steps.push({
              ...step,
              components: componentIndex >= 0 ? step.components.slice(0, componentIndex + 1) : step.components
            })
          } else {
            steps.push(step)
          }
        })
      } else {
        steps.push({ kind: 'node', node })
      }
      if (isTargetNode) {
        break
      }
    }
    return steps
  }

  truncateBranchToTarget(branch = [], targetNodeId = '', targetComponentId = '') {
    if (!targetNodeId) {
      return branch
    }

    const steps = []
    for (let index = 0; index < branch.length; index += 1) {
      const step = branch[index]
      const nodeId = step?.node?.id || ''

      if (nodeId !== targetNodeId) {
        steps.push(step)
        continue
      }

      if (targetComponentId) {
        if (step.kind === 'page-components') {
          const componentIndex = (step.components || []).findIndex(component => component.id === targetComponentId)
          if (componentIndex < 0) {
            return []
          }
          steps.push({
            ...step,
            components: step.components.slice(0, componentIndex + 1)
          })
          return steps
        }
        steps.push(step)
        continue
      }

      steps.push(step)
      if (step.kind === 'page-node') {
        const nextStep = branch[index + 1]
        if (nextStep?.kind === 'page-components' && nextStep?.node?.id === targetNodeId) {
          steps.push(nextStep)
        }
      }
      return steps
    }

    return []
  }

  buildExecutionBranches(nodes, edges) {
    const nodeMap = new Map(nodes.map(node => [node.id, node]))
    const startNode = nodes.find(node => node?.data?.type === 'start')
    if (!startNode) {
      return []
    }

    const adjacency = new Map(nodes.map(node => [node.id, []]))
    edges
      .filter(edge => edge?.source?.cell && edge?.target?.cell)
      .filter(edge => nodeMap.has(edge.source.cell) && nodeMap.has(edge.target.cell))
      .filter(edge => edge.source.cell !== edge.target.cell)
      .forEach(edge => {
        adjacency.get(edge.source.cell).push({
          targetId: edge.target.cell,
          sourcePort: edge.source.port || edge.source.portId || '',
          targetPort: edge.target.port || edge.target.portId || ''
        })
      })

    adjacency.forEach(outgoing => {
      outgoing.sort((left, right) => {
        const leftNode = nodeMap.get(left.targetId)
        const rightNode = nodeMap.get(right.targetId)
        return this.compareNodeOrder(leftNode, rightNode)
      })
    })

    const branches = []
    const visit = (nodeId, path, stack) => {
      const node = nodeMap.get(nodeId)
      if (!node || stack.has(nodeId)) {
        return
      }

      const nodeType = node?.data?.type || ''
      const outgoing = adjacency.get(nodeId) || []
      const pageVariants = nodeType === 'page'
        ? this.buildPageExecutionVariants(node, outgoing)
        : [{ steps: [{ kind: 'node', node }], outgoing }]

      const nextStack = new Set(stack)
      nextStack.add(nodeId)

      pageVariants.forEach(variant => {
        const nextPath = [...path, ...variant.steps]
        const nextOutgoing = variant.outgoing || []
        if (nodeType === 'end' || !nextOutgoing.length) {
          branches.push(nextPath)
          return
        }

        nextOutgoing.forEach(edgeInfo => {
          visit(edgeInfo.targetId, nextPath, nextStack)
        })
      })
    }

    visit(startNode.id, [], new Set())
    return branches
  }

  compareNodeOrder(left, right) {
    const leftPosition = left?.position || {}
    const rightPosition = right?.position || {}
    const leftX = Number(left.x ?? leftPosition.x ?? 0)
    const rightX = Number(right.x ?? rightPosition.x ?? 0)
    if (leftX !== rightX) {
      return leftX - rightX
    }
    const leftY = Number(left.y ?? leftPosition.y ?? 0)
    const rightY = Number(right.y ?? rightPosition.y ?? 0)
    if (leftY !== rightY) {
      return leftY - rightY
    }
    return String(left?.id || '').localeCompare(String(right?.id || ''))
  }

  buildPageExecutionVariants(pageNode, outgoingEdges = []) {
    const config = {
      ...(pageNode?.data?.config || {}),
      id: pageNode.id,
      nodeId: pageNode.id
    }
    const resolved = this.resolvePageComponents(config)
    const componentMap = resolved.componentMap || new Map()
    const actionableComponents = resolved.components.filter(component => component.type !== 'iframe')
    const nodeStep = {
      kind: 'page-node',
      node: pageNode
    }

    if (!actionableComponents.length) {
      return [{ steps: [nodeStep], outgoing: outgoingEdges }]
    }

    const pathBranches = this.buildPageComponentBranches(config, actionableComponents, componentMap)
    if (!pathBranches.length) {
      return [{
        steps: [
          nodeStep,
          {
            kind: 'page-components',
            node: pageNode,
            components: actionableComponents
          }
        ],
        outgoing: outgoingEdges
      }]
    }

    const variants = []
    const seenVariantKeys = new Set()
    const addVariant = (componentBranch, outgoing) => {
      const key = [
        componentBranch.map(component => component.id).join('>'),
        (outgoing || []).map(edgeInfo => `${edgeInfo.sourcePort || ''}->${edgeInfo.targetId}:${edgeInfo.targetPort || ''}`).join('|')
      ].join('::')
      if (seenVariantKeys.has(key)) {
        return
      }
      seenVariantKeys.add(key)
      variants.push({
        steps: [
          nodeStep,
          {
            kind: 'page-components',
            node: pageNode,
            components: componentBranch
          }
        ],
        outgoing
      })
    }

    outgoingEdges.forEach(edgeInfo => {
      const sourceComponentId = this.getComponentIdFromPort(edgeInfo.sourcePort || '')
      if (!sourceComponentId || !componentMap.has(sourceComponentId)) {
        return
      }
      const containingBranches = pathBranches.filter(branch => branch.some(component => component.id === sourceComponentId))
      const handledByTerminalBranch = containingBranches.some(
        branch => branch[branch.length - 1]?.id === sourceComponentId
      )
      if (handledByTerminalBranch) {
        return
      }
      const containingBranch = containingBranches[0]
      const branch = containingBranch
        ? containingBranch.slice(0, containingBranch.findIndex(component => component.id === sourceComponentId) + 1)
        : [componentMap.get(sourceComponentId)].filter(Boolean)
      if (branch.length) {
        addVariant(branch, [edgeInfo])
      }
    })

    pathBranches.forEach(componentBranch => {
      const lastComponentId = componentBranch[componentBranch.length - 1]?.id || ''
      const genericOutgoing = outgoingEdges.filter(edgeInfo => !this.getComponentIdFromPort(edgeInfo.sourcePort || ''))
      const matchedOutgoing = outgoingEdges.filter(edgeInfo => {
        const sourceComponentId = this.getComponentIdFromPort(edgeInfo.sourcePort || '')
        return sourceComponentId === lastComponentId
      })

      addVariant(componentBranch, [...genericOutgoing, ...matchedOutgoing])
    })

    return variants
  }

  buildPageComponentBranches(config, actionableComponents, componentMap) {
    const orderedComponents = [...actionableComponents]
      .sort((left, right) => this.compareComponentOrder(left, right, componentMap))
    const actionableIds = new Set(orderedComponents.map(component => component.id))
    const adjacency = new Map()
    const incoming = new Map()
    const entryIds = new Set()
    const terminalIds = new Set()
    orderedComponents.forEach(component => {
      adjacency.set(component.id, [])
      incoming.set(component.id, 0)
    })

    ;(config.executionPath || []).forEach(step => {
      const fromId = step?.from?.componentId || this.getComponentIdFromPort(step?.from?.portId || '')
      const toId = step?.to?.componentId || this.getComponentIdFromPort(step?.to?.portId || '')
      if (!fromId && toId && actionableIds.has(toId)) {
        entryIds.add(toId)
        return
      }
      if (!fromId || !actionableIds.has(fromId)) {
        return
      }
      if (!toId || !actionableIds.has(toId)) {
        terminalIds.add(fromId)
        return
      }
      if (fromId === toId) {
        return
      }
      if (!adjacency.get(fromId).includes(toId)) {
        adjacency.get(fromId).push(toId)
        incoming.set(toId, incoming.get(toId) + 1)
      }
    })

    adjacency.forEach(targetIds => {
      targetIds.sort((leftId, rightId) => this.compareComponentOrder(componentMap.get(leftId), componentMap.get(rightId), componentMap))
    })

    if (![...adjacency.values()].some(targetIds => targetIds.length) && !entryIds.size && !terminalIds.size) {
      return orderedComponents.length ? [orderedComponents] : []
    }

    const startIds = entryIds.size
      ? orderedComponents.filter(component => entryIds.has(component.id)).map(component => component.id)
      : orderedComponents
        .filter(component => incoming.get(component.id) === 0)
        .map(component => component.id)
    const branchIds = []
    const visit = (componentId, pathIds, stack) => {
      if (stack.has(componentId)) {
        return
      }
      const nextPath = [...pathIds, componentId]
      const outgoing = adjacency.get(componentId) || []
      if (terminalIds.has(componentId)) {
        branchIds.push(nextPath)
      }
      if (!outgoing.length) {
        if (!terminalIds.has(componentId)) {
          branchIds.push(nextPath)
        }
        return
      }
      const nextStack = new Set(stack)
      nextStack.add(componentId)
      outgoing.forEach(targetId => visit(targetId, nextPath, nextStack))
    }

    ;(startIds.length ? startIds : [orderedComponents[0]?.id].filter(Boolean))
      .forEach(componentId => visit(componentId, [], new Set()))

    const seen = new Set()
    const branches = branchIds
      .map(ids => ids.map(id => componentMap.get(id)).filter(Boolean))
      .filter(components => components.length)
      .filter(components => {
        const key = components.map(component => component.id).join('>')
        if (seen.has(key)) {
          return false
        }
        seen.add(key)
        return true
      })

    return branches.length ? branches : [orderedComponents]
  }

  getComponentIdFromPort(portId = '') {
    const match = String(portId || '').match(/^component-(.+?)-(?:top|left|bottom|right)-(?:in|out)$/)
    return match ? match[1] : ''
  }

  generateExecutionStepCode(step) {
    if (!step) {
      return ''
    }
    if (step.kind === 'page-node') {
      return this.generatePageNodeOnlyCode(step.node)
    }
    if (step.kind === 'page-components') {
      return this.generatePageComponentsCode(step.node, step.components || [])
    }
    return this.generateNodeCode(step.node)
  }

  generateReplayExecutionStepCode(step) {
    if (!step) {
      return ''
    }
    if (step.kind === 'page-node') {
      return this.generatePageNodeOnlyCode(step.node)
    }
    if (step.kind === 'page-components') {
      return this.generatePageComponentsCode(step.node, step.components || [])
    }

    const node = step.node
    const data = node?.data || {}
    const config = data.config || {}
    switch (data.type) {
      case 'start':
        return this.generateReplayStartNode(config)
      case 'page':
        return this.generatePageNode(config)
      case 'operation':
        return this.generateOperationNode(config)
      case 'end':
        return this.generateEndNode(config)
      default:
        return ''
    }
  }

  generatePageNodeOnlyCode(node) {
    const data = node?.data || {}
    const config = {
      ...(data.config || {}),
      id: node.id,
      nodeId: node.id
    }
    return this.wrapRuntimeStep(
      this.buildNodeRuntimeMeta(node),
      `        # Page: ${this.escapePythonString(config.pageName || config.name || '页面节点')}\n${this.generateNodeInputSetup(config)}${this.generateNodeOutputAssignment(config, {
        selector: config.snapshotFile || ''
      })}`
    )
  }

  generatePageComponentsCode(node, components = []) {
    const data = node?.data || {}
    const config = {
      ...(data.config || {}),
      id: node.id,
      nodeId: node.id
    }
    const resolved = this.resolvePageComponents(config)
    const componentMap = resolved.componentMap || new Map()
    let code = ''
    let currentFrameChain = []
    components
      .filter(component => component?.type && component.type !== 'iframe')
      .forEach(component => {
        const targetFrameChain = this.getFrameChain(component, componentMap)
        code += this.syncFrameScope(currentFrameChain, targetFrameChain, config.snapshotData)
        code += this.generateComponentCode(component, config.snapshotData, {
          runtimeMeta: this.buildComponentRuntimeMeta(component, config)
        })
        currentFrameChain = targetFrameChain
      })
    code += this.closeFrameScope(currentFrameChain)
    code += '\n'
    return code
  }

  generateNodeCode(node) {
    const data = node.data || {}
    const config = {
      ...(data.config || {}),
      id: node.id,
      nodeId: node.id
    }
    const nodeMeta = this.buildNodeRuntimeMeta(node)

    switch (data.type) {
      case 'start':
        return this.wrapRuntimeStep(nodeMeta, this.generateStartNode(config))
      case 'page':
        return this.generatePageNode(config, { nodeMeta })
      case 'operation':
        return this.wrapRuntimeStep(nodeMeta, this.generateOperationNode(config))
      case 'end':
        return this.wrapRuntimeStep(nodeMeta, this.generateEndNode(config))
      default:
        return `        # Unsupported node type: ${data.type}\n`
    }
  }

  nextRuntimeStepOrder() {
    this.runtimeStepOrder = (this.runtimeStepOrder || 0) + 1
    return this.runtimeStepOrder
  }

  buildNodeRuntimeMeta(node) {
    const data = node?.data || {}
    const config = data.config || {}
    const nodeType = data.type || 'node'
    const title = config.name || config.pageName || {
      start: '开始节点',
      page: '页面节点',
      operation: '操作节点',
      end: '结束节点'
    }[nodeType] || nodeType
    return {
      step_key: `node:${node?.id || this.nextRuntimeStepOrder()}`,
      step_order: this.nextRuntimeStepOrder(),
      item_type: 'node',
      node_id: node?.id || '',
      component_id: '',
      title,
      input: {
        node_type: nodeType,
        node_id: node?.id || '',
        operation_type: config.operationType || '',
        page_name: config.pageName || config.name || '',
        url: config.url || '',
        assertion_target: config.assertionTarget || '',
        assertion_selector: config.assertionSelector || '',
        assertion_operator: config.assertionOperator || '',
        expected_mode: config.expectedMode || '',
        expected_value: config.expectedMode === 'reference'
          ? `{{${config.expectedReference || ''}}}`
          : (config.expectedValue || '')
      }
    }
  }

  buildComponentRuntimeMeta(component, pageConfig) {
    const pageId = pageConfig?.id || pageConfig?.nodeId || component.pageNodeId || ''
    return {
      step_key: `component:${pageId}:${component.id || this.nextRuntimeStepOrder()}`,
      step_order: this.nextRuntimeStepOrder(),
      item_type: 'component',
      node_id: pageId,
      component_id: component.id || '',
      title: this.getComponentLabel(component),
      input: {
        component_type: component.type || '',
        action: component.config?.action || component.config?.recordingActionType || '',
        value: component.config?.value ?? component.config?.inputValue ?? component.config?.selectedValue ?? component.config?.checked ?? '',
        element_id: component.elementId || '',
        page_name: pageConfig?.pageName || pageConfig?.name || ''
      }
    }
  }

  buildRuntimePayload(meta) {
    return this.toPythonLiteral(meta || {})
  }

  toPythonLiteral(value) {
    if (value === null || value === undefined) {
      return 'None'
    }
    if (typeof value === 'boolean') {
      return value ? 'True' : 'False'
    }
    if (typeof value === 'number') {
      return Number.isFinite(value) ? String(value) : 'None'
    }
    if (typeof value === 'string') {
      return `'${this.escapePythonString(value)}'`
    }
    if (Array.isArray(value)) {
      return `[${value.map(item => this.toPythonLiteral(item)).join(', ')}]`
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value)
        .filter(([, entryValue]) => entryValue !== undefined)
        .map(([entryKey, entryValue]) => (
          `'${this.escapePythonString(entryKey)}': ${this.toPythonLiteral(entryValue)}`
        ))
      return `{${entries.join(', ')}}`
    }
    return `'${this.escapePythonString(String(value))}'`
  }

  wrapRuntimeStep(meta, code) {
    const payload = this.buildRuntimePayload(meta)
    const body = this.indentExistingPython(this.normalizeRuntimeStepBody(code), 12)
    return `        async def __testhub_step_${meta.step_order}():
            nonlocal browser, context, page, current_scope, testhub_runtime_auth_installed, last_select_trigger, flow_vars
${body}
            return {'url': page.url}
        await run_testhub_flow_step(page, ${payload}, __testhub_step_${meta.step_order})

`
  }

  generateStartNode(config) {
    const browserType = config.browserType || 'chromium'
    const requestedHeadless = this.forceHeaded ? false : config.headless === true
    const viewportWidth = config.viewportWidth || 1920
    const viewportHeight = config.viewportHeight || 1080
    const maximize = config.maximize !== false
    const installRuntimeAuth = this.shouldInstallRuntimeAuth(config)
    const nodeInputSetup = this.generateNodeInputSetup(config, config.url || 'https://example.com')
    const urlExpr = this.resolveNodeInputExpression(config, config.url || 'https://example.com')

    return `        launch_options, viewport = resolve_browser_runtime_options(
            requested_headless=${this.toPythonBool(requestedHeadless)},
            maximize=${this.toPythonBool(maximize)},
            viewport_width=${viewportWidth},
            viewport_height=${viewportHeight},
        )
        browser = await p.${browserType}.launch(**launch_options)
        if viewport is None:
            context = await browser.new_context(no_viewport=True, ignore_https_errors=True)
        else:
            context = await browser.new_context(viewport=viewport, ignore_https_errors=True)
        testhub_auth_init_script = ''
        if ${this.toPythonBool(installRuntimeAuth)} and should_install_testhub_runtime_auth(rewrite_localhost_url_for_runtime(${urlExpr})):
            testhub_auth_init_script = build_testhub_auth_init_script()
        if testhub_auth_init_script:
            await context.add_init_script(testhub_auth_init_script)
            testhub_runtime_auth_installed = True
        page = await context.new_page()
        await apply_browser_window_geometry(context, page, ${this.toPythonBool(maximize)}, ${viewportWidth}, ${viewportHeight})
        current_scope = page

${nodeInputSetup}        await page.goto(rewrite_localhost_url_for_runtime(${urlExpr}), wait_until='domcontentloaded')
        if testhub_runtime_auth_installed and is_login_page_url(page.url):
            await page.goto(same_origin_url(page.url, '/home'), wait_until='domcontentloaded')
        await safe_wait_for_network_idle(page)
${this.generateNodeOutputAssignment(config, { selector: config.url || 'https://example.com' })}

`
  }

  generateReplayStartNode(config) {
    const nodeInputSetup = this.generateNodeInputSetup(config, config.url || 'https://example.com')
    const urlExpr = this.resolveNodeInputExpression(config, config.url || 'https://example.com')

    return `        current_scope = page
${nodeInputSetup}        await page.goto(rewrite_localhost_url_for_runtime(${urlExpr}), wait_until='domcontentloaded')
        if testhub_runtime_auth_installed and is_login_page_url(page.url):
            await page.goto(same_origin_url(page.url, '/home'), wait_until='domcontentloaded')
        await safe_wait_for_network_idle(page)
${this.generateNodeOutputAssignment(config, { selector: config.url || 'https://example.com' })}

`
  }

  generatePageNode(config, options = {}) {
    const pageName = this.escapePythonString(config.pageName || config.name || '页面节点')
    const resolved = this.resolvePageComponents(config)
    const componentMap = resolved.componentMap
    let actionableComponents = resolved.components.filter(component => component.type !== 'iframe')
    const targetComponentId = options?.targetComponentId || ''
    if (targetComponentId) {
      const targetIndex = actionableComponents.findIndex(component => component.id === targetComponentId)
      if (targetIndex >= 0) {
        actionableComponents = actionableComponents.slice(0, targetIndex + 1)
      }
    }
    const nodeMeta = options?.nodeMeta || {
      step_key: `node:page:${this.nextRuntimeStepOrder()}`,
      step_order: this.nextRuntimeStepOrder(),
      item_type: 'node',
      node_id: config.id || config.nodeId || '',
      component_id: '',
      title: config.pageName || config.name || '页面节点',
      input: { node_type: 'page', page_name: config.pageName || config.name || '' }
    }
    let code = this.wrapRuntimeStep(
      nodeMeta,
      `        # Page: ${pageName}\n${this.generateNodeInputSetup(config)}${this.generateNodeOutputAssignment(config, {
        selector: config.snapshotFile || ''
      })}`
    )

    if (actionableComponents.length === 0) {
      code += '        # 当前页面还没有配置可执行组件\n'
      code += '\n'
      return code
    }

    let currentFrameChain = []
    actionableComponents.forEach(component => {
      const targetFrameChain = this.getFrameChain(component, componentMap)
      code += this.syncFrameScope(currentFrameChain, targetFrameChain, config.snapshotData)
      code += this.generateComponentCode(component, config.snapshotData, {
        runtimeMeta: this.buildComponentRuntimeMeta(component, config)
      })
      currentFrameChain = targetFrameChain
    })

    code += this.closeFrameScope(currentFrameChain)
    code += '\n'
    return code
  }

  syncFrameScope(currentChain, nextChain, snapshotData) {
    const currentIds = currentChain.map(component => component.id).join('>')
    const nextIds = nextChain.map(component => component.id).join('>')
    if (currentIds === nextIds) {
      return ''
    }

    let code = ''
    if (currentChain.length) {
      currentChain
        .slice()
        .reverse()
        .forEach(component => {
          code += `        # 退出iframe: ${this.escapePythonString(this.getComponentLabel(component))}\n`
        })
    }

    code += '        current_scope = page\n'

    nextChain.forEach(component => {
      const frameLocatorSpec = this.getFrameLocatorSpec(component, snapshotData)
      const selector = this.escapePythonString(frameLocatorSpec.value)
      code += this.generateNodeInputSetup(component.config)
      code += `        # 切入iframe: ${this.escapePythonString(this.getComponentLabel(component))}\n`
      code += `        current_scope = current_scope.frame_locator('${selector}')\n`
      code += this.generateIframeOutputAssignment(
        component,
        this.escapePythonString(frameLocatorSpec.selector)
      )
    })

    return code
  }

  closeFrameScope(currentChain) {
    if (!currentChain.length) {
      return ''
    }

    let code = ''
    currentChain
      .slice()
      .reverse()
      .forEach(component => {
        code += `        # 退出iframe: ${this.escapePythonString(this.getComponentLabel(component))}\n`
      })
    code += '        current_scope = page\n'
    return code
  }

  generateComponentCode(component, snapshotData, options = {}) {
    if (this.shouldSkipEmptyInputComponent(component)) {
      return `        # 跳过空输入组件: ${this.escapePythonString(this.getComponentLabel(component))}\n\n`
    }

    const locatorSpec = this.getElementLocatorSpec(component, snapshotData)
    const label = this.escapePythonString(this.getComponentLabel(component))
    const locatorVar = 'locator'
    let code = `        # 组件: ${label}\n`
    code += this.buildLocatorAssignmentCode('current_scope', locatorVar, locatorSpec)

    switch (component.type) {
      case 'input':
        code += this.generateInputCode(component, locatorVar)
        break
      case 'button':
      case 'link':
      case 'tab':
      case 'menuitem':
      case 'clickable':
        code += this.generateClickCode(component, locatorVar)
        break
      case 'select':
        code += this.generateSelectCode(component, locatorVar)
        break
      case 'checkbox':
      case 'radio':
        code += this.generateCheckboxCode(component, locatorVar, locatorSpec)
        break
      case 'file':
        code += this.generateFileCode(component, locatorVar)
        break
      default:
        code += `        # Unsupported component type: ${component.type}\n`
        break
    }

    code += this.generateOutputAssignment(
      component,
      locatorVar,
      this.escapePythonString(locatorSpec.selector)
    )
    if (this.isRecordedLoginComponent(component) || this.isRecordedLoginPageComponent(component)) {
      const nestedCode = this.indentExistingPython(code, 4)
      code = `        if testhub_runtime_auth_installed and not is_login_page_url(page.url):\n            return {'__testhub_status': 'skipped', 'reason': 'runtime auth installed, recorded login step skipped', 'url': page.url}\n        else:\n${nestedCode}\n`
    }
    if (options?.runtimeMeta) {
      return this.wrapRuntimeStep(options.runtimeMeta, code)
    }
    return `${code}\n`
  }

  generateInputCode(component, locatorVar) {
    const action = component.config?.action || 'fill'
    const valueExpr = this.resolveInputExpression(component, ['value', 'inputValue'])

    if (action === 'press') {
      return `        await ${locatorVar}.press(${valueExpr})\n`
    }

    return `        await ${locatorVar}.fill(${valueExpr})\n`
  }

  generateClickCode(component, locatorVar) {
    const action = component.config?.action || 'click'
    if (this.isSelectDropdownOptionComponent(component)) {
      const optionText = this.getComponentLabel(component)
      return `        await click_visible_select_option(page, '${this.escapePythonString(optionText)}', last_select_trigger)\n        last_select_trigger = None\n`
    }
    if (component.type === 'button' && action === 'click') {
      return `        await click_button_by_name(page, ${locatorVar}, '${this.escapePythonString(this.getComponentLabel(component))}', expect_not_login=${this.toPythonBool(this.isRecordedLoginSubmitComponent(component))}, scope=current_scope)\n`
    }
    switch (action) {
      case 'dblclick':
        return `        await ${locatorVar}.dblclick()\n`
      case 'contextmenu':
        return `        await ${locatorVar}.click(button='right')\n`
      case 'hover':
        return `        await ${locatorVar}.hover()\n`
      default:
        return this.isSelectDropdownTriggerComponent(component)
          ? `        await ${locatorVar}.click()\n        last_select_trigger = ${locatorVar}\n        await page.wait_for_timeout(700)\n`
          : `        await click_generic_element(page, ${locatorVar}, '${this.escapePythonString(this.getComponentLabel(component))}', scope=current_scope)\n`
    }
  }

  generateSelectCode(component, locatorVar) {
    const recordedAction = component.config?.recordingActionType || component.config?.action || ''
    if (recordedAction !== 'select' || !component.config?.selectedValue) {
      return `        await ${locatorVar}.click()\n        last_select_trigger = ${locatorVar}\n        await page.wait_for_timeout(700)\n`
    }
    const valueExpr = this.resolveInputExpression(component, ['selectedValue', 'inputValue', 'value'])
    return `        await ${locatorVar}.select_option(${valueExpr})\n`
  }

  generateCheckboxCode(component, locatorVar, locatorSpec) {
    if (component.type === 'radio' && !component.config?.checked) {
      return '        # Radio controls cannot be unchecked directly; select another radio option if needed.\n'
    }

    const checked = this.toPythonBool(Boolean(component.config?.checked))
    const controlType = component.type === 'radio' ? 'radio' : 'checkbox'
    const label = this.escapePythonString(this.getComponentLabel(component))
    const recordedRect = this.buildCheckableRecordedRectLiteral(component)
    let code = this.buildLocatorCandidatesCode('current_scope', 'checkable_candidates', locatorVar, locatorSpec)
    code += `        await set_checkable_state(page, checkable_candidates, ${checked}, element_text='${label}', control_type='${controlType}', scope=current_scope, recorded_rect=${recordedRect})\n`
    return code
  }

  generateFileCode(component, locatorVar) {
    const valueExpr = this.resolveInputExpression(component, ['filePath', 'inputValue', 'value'])
    return `        await ${locatorVar}.set_input_files(${valueExpr})\n`
  }

  generateOutputAssignment(component, locatorVar, selector) {
    const outputName = component.config?.outputName?.trim()
    const outputSource = component.config?.outputSource || 'none'
    if (!outputName || outputSource === 'none') {
      return ''
    }

    const targetKey = this.escapePythonString(outputName)
    switch (outputSource) {
      case 'value':
        if (component.type === 'input' || component.type === 'select') {
          return `        flow_vars['${targetKey}'] = await read_testhub_locator_value(${locatorVar})\n`
        }
        return `        flow_vars['${targetKey}'] = await ${locatorVar}.get_attribute('value') or ''\n`
      case 'text':
        return `        flow_vars['${targetKey}'] = await read_testhub_visible_text(${locatorVar})\n`
      case 'selector':
        return `        flow_vars['${targetKey}'] = '${selector}'\n`
      case 'checked':
        return `        flow_vars['${targetKey}'] = await ${locatorVar}.is_checked()\n`
      case 'url':
        return `        flow_vars['${targetKey}'] = page.url\n`
      case 'custom':
        return `        flow_vars['${targetKey}'] = ${component.config?.outputValue || "''"}\n`
      default:
        return ''
    }
  }

  generateOperationNode(config) {
    const operationType = config.operationType || 'sleep'
    const nodeInputSetup = this.generateNodeInputSetup(config)
    const selectorExpr = this.resolveNodeInputExpression(config, config.selector || 'body')
    const timeoutExpr = `int(${this.resolveNodeInputExpression(config, String(config.timeout || 1000))})`

    switch (operationType) {
      case 'sleep':
        return `${nodeInputSetup}        await page.wait_for_timeout(${timeoutExpr})\n${this.generateNodeOutputAssignment(config)}\n`
      case 'waitForSelector':
        return `${nodeInputSetup}        await page.wait_for_selector(${selectorExpr})\n${this.generateNodeOutputAssignment(config, { selector: config.selector || 'body' })}\n`
      case 'waitForNavigation':
        return `${nodeInputSetup}        await safe_wait_for_network_idle(page)\n${this.generateNodeOutputAssignment(config)}\n`
      case 'waitForLoadState':
        return `${nodeInputSetup}        await page.wait_for_load_state('domcontentloaded')\n${this.generateNodeOutputAssignment(config)}\n`
      case 'screenshot':
        return `${nodeInputSetup}        await page.screenshot(path='screenshot.png')\n${this.generateNodeOutputAssignment(config)}\n`
      case 'assertValue':
        return this.generateAssertionOperation(config, nodeInputSetup)
      case 'custom':
        return `${nodeInputSetup}${this.indentPythonBlock(config.customCode || '# TODO: custom playwright logic')}${this.generateNodeOutputAssignment(config)}\n`
      default:
        return `        # Unsupported operation type: ${operationType}\n\n`
    }
  }

  generateAssertionOperation(config, nodeInputSetup = '') {
    const target = config.assertionTarget || 'selectorText'
    const selector = this.escapePythonString(config.assertionSelector || config.selector || 'body')
    const operator = this.escapePythonString(config.assertionOperator || 'equals')
    const timeout = Number(config.assertionTimeout ?? 5000)
    const timeoutValue = Number.isFinite(timeout) && timeout >= 0 ? Math.floor(timeout) : 5000
    const expectedExpr = this.resolveAssertionExpectedExpression(config)
    const outputKey = this.escapePythonString(String(config.outputName || '').trim())
    const outputAssignment = outputKey
      ? `        flow_vars['${outputKey}'] = assertion_result.get('actual', '')\n`
      : ''

    let actualCode = ''
    switch (target) {
      case 'pageText':
        actualCode = "        actual_value = await read_testhub_visible_text(page.locator('body'))\n"
        break
      case 'selectorValue':
        actualCode = `        assertion_locator = current_scope.locator('${selector}').first\n        await assertion_locator.wait_for(state='visible', timeout=${timeoutValue})\n        actual_value = await assertion_locator.input_value()\n`
        break
      case 'selectorChecked':
        actualCode = `        assertion_locator = current_scope.locator('${selector}').first\n        await assertion_locator.wait_for(state='attached', timeout=${timeoutValue})\n        actual_value = await assertion_locator.is_checked()\n`
        break
      case 'url':
        actualCode = '        actual_value = page.url\n'
        break
      case 'variable': {
        const variableName = this.escapePythonString(config.assertionActualReference || config.inputReference || '')
        actualCode = `        actual_value = flow_vars.get('${variableName}', '')\n`
        break
      }
      case 'custom':
        actualCode = `        actual_value = ${config.assertionActualExpression || "''"}\n`
        break
      case 'selectorText':
      default:
        actualCode = `        assertion_locator = current_scope.locator('${selector}').first\n        await assertion_locator.wait_for(state='visible', timeout=${timeoutValue})\n        actual_value = await read_testhub_visible_text(assertion_locator)\n`
        break
    }

    return `${nodeInputSetup}${actualCode}        expected_value = ${expectedExpr}\n        assertion_result = assert_testhub_value(actual_value, expected_value, '${operator}')\n${outputAssignment}        return {'url': page.url, **assertion_result}\n`
  }

  resolveAssertionExpectedExpression(config) {
    if (config?.expectedMode === 'reference' && config?.expectedReference) {
      return `flow_vars.get('${this.escapePythonString(config.expectedReference)}', '')`
    }
    return `'${this.escapePythonString(config?.expectedValue || '')}'`
  }

  indentPythonBlock(code, indentSize = 8) {
    const indent = ' '.repeat(indentSize)
    const lines = String(code || '')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\n')

    while (lines.length && !lines[0].trim()) {
      lines.shift()
    }
    while (lines.length && !lines[lines.length - 1].trim()) {
      lines.pop()
    }

    if (!lines.length) {
      return `${indent}# TODO: custom playwright logic\n`
    }

    const commonIndent = lines
      .filter(line => line.trim())
      .reduce((minIndent, line) => {
        const currentIndent = line.match(/^[ \t]*/)?.[0]?.length || 0
        return Math.min(minIndent, currentIndent)
      }, Number.MAX_SAFE_INTEGER)

    return lines
      .map(line => line.trim() ? `${indent}${line.slice(commonIndent)}` : '')
      .join('\n') + '\n'
  }

  generateEndNode(config) {
    const nodeInputSetup = this.generateNodeInputSetup(config)
    if (!config.generateReport) {
      return `${nodeInputSetup}        # Test flow completed\n${this.generateNodeOutputAssignment(config)}\n`
    }
    return `${nodeInputSetup}        print("测试执行完成")\n${this.generateNodeOutputAssignment(config)}\n`
  }

  generateNodeInputSetup(config, fallbackLiteral = '') {
    const hasInputConfig = config?.inputMode === 'reference'
      ? Boolean(config.inputReference)
      : Boolean(config.inputValue || fallbackLiteral)

    if (!hasInputConfig && !config?.inputAlias) {
      return ''
    }

    const inputExpr = this.resolveNodeInputExpression(config, fallbackLiteral)
    let code = `        node_input = ${inputExpr}\n`
    if (config?.inputAlias) {
      code += `        flow_vars['${this.escapePythonString(config.inputAlias)}'] = node_input\n`
    }
    return code
  }

  resolveNodeInputExpression(config, fallbackLiteral = '') {
    if (config?.inputMode === 'reference' && config?.inputReference) {
      return `str(flow_vars.get('${this.escapePythonString(config.inputReference)}', '${this.escapePythonString(fallbackLiteral)}'))`
    }

    if (config?.inputValue) {
      return `'${this.escapePythonString(config.inputValue)}'`
    }

    return `'${this.escapePythonString(fallbackLiteral)}'`
  }

  generateNodeOutputAssignment(config, context = {}) {
    const outputName = config?.outputName?.trim()
    const outputSource = config?.outputSource || 'none'
    const hasNodeInput = config?.inputMode === 'reference'
      ? Boolean(config?.inputReference)
      : Boolean(config?.inputValue)
    if (!outputName || outputSource === 'none') {
      return ''
    }

    const outputKey = this.escapePythonString(outputName)
    switch (outputSource) {
      case 'value':
        return hasNodeInput
          ? `        flow_vars['${outputKey}'] = node_input if 'node_input' in locals() else ''\n`
          : `        flow_vars['${outputKey}'] = ''\n`
      case 'text':
        return `        flow_vars['${outputKey}'] = await read_testhub_visible_text(page.locator('body'))\n`
      case 'selector':
        return `        flow_vars['${outputKey}'] = '${this.escapePythonString(context.selector || config?.selector || '')}'\n`
      case 'checked':
        return `        flow_vars['${outputKey}'] = False\n`
      case 'url':
        return `        flow_vars['${outputKey}'] = page.url\n`
      case 'custom':
        return `        flow_vars['${outputKey}'] = ${config?.outputValue || "''"}\n`
      default:
        return ''
    }
  }

  generateIframeOutputAssignment(component, selector) {
    const config = component?.config || {}
    const outputName = config?.outputName?.trim()
    const outputSource = config?.outputSource || 'none'
    const hasIframeInput = config?.inputMode === 'reference'
      ? Boolean(config?.inputReference)
      : Boolean(config?.inputValue)

    if (!outputName || outputSource === 'none') {
      return ''
    }

    const outputKey = this.escapePythonString(outputName)
    switch (outputSource) {
      case 'value':
        return hasIframeInput
          ? `        flow_vars['${outputKey}'] = node_input\n`
          : `        flow_vars['${outputKey}'] = ''\n`
      case 'text':
        return `        flow_vars['${outputKey}'] = await read_testhub_visible_text(current_scope.locator('body'))\n`
      case 'selector':
        return `        flow_vars['${outputKey}'] = '${selector}'\n`
      case 'checked':
        return `        flow_vars['${outputKey}'] = False\n`
      case 'url':
        return `        flow_vars['${outputKey}'] = page.url\n`
      case 'custom':
        return `        flow_vars['${outputKey}'] = ${config?.outputValue || "''"}\n`
      default:
        return ''
    }
  }

  indentExistingPython(code, extraSpaces = 4) {
    const indent = ' '.repeat(extraSpaces)
    return String(code || '')
      .split('\n')
      .map(line => line ? `${indent}${line}` : line)
      .join('\n')
  }

  normalizeRuntimeStepBody(code) {
    const lines = String(code || '')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\n')

    while (lines.length && !lines[0].trim()) {
      lines.shift()
    }
    while (lines.length && !lines[lines.length - 1].trim()) {
      lines.pop()
    }
    if (!lines.length) {
      return ''
    }

    const commonIndent = lines
      .filter(line => line.trim())
      .reduce((minIndent, line) => {
        const currentIndent = line.match(/^[ \t]*/)?.[0]?.length || 0
        return Math.min(minIndent, currentIndent)
      }, Number.MAX_SAFE_INTEGER)

    return lines
      .map(line => (line.trim() ? line.slice(commonIndent) : ''))
      .join('\n')
  }

  getAuthStateStrategy(config = {}) {
    const strategy = String(config.authStateStrategy || 'auto').trim()
    return ['auto', 'clean', 'inject'].includes(strategy) ? strategy : 'auto'
  }

  shouldInstallRuntimeAuth(config = {}) {
    const strategy = this.getAuthStateStrategy(config)
    if (strategy === 'clean') {
      return false
    }
    if (strategy === 'inject') {
      return true
    }
    return !this.currentGraphHasRecordedLoginComponents
  }

  graphHasRecordedLoginComponents(cells = []) {
    return cells.some(cell => {
      const components = cell?.data?.config?.innerComponents || []
      return components.some(component => this.isRecordedLoginComponent(component))
    })
  }

  graphHasMaskedPasswordComponents(cells = []) {
    return cells.some(cell => {
      const components = cell?.data?.config?.innerComponents || []
      return components.some(component => this.isMaskedPasswordInputComponent(component))
    })
  }

  isMaskedPasswordInputComponent(component) {
    if (component?.type !== 'input') {
      return false
    }

    const config = component.config || {}
    const value = String(config.value ?? config.inputValue ?? config.recordingActionValue ?? '')
    if (!/^\*{4,}$/.test(value)) {
      return false
    }

    const elementData = this.getElementData(component, null) || {}
    const attributes = elementData.attributes || {}
    const type = this.normalizeSnapshotAttributeValue(attributes.type || elementData.type).toLowerCase()
    const label = [
      this.getComponentLabel(component),
      config.placeholder,
      elementData.text,
      attributes.placeholder,
      attributes['aria-label'],
      attributes.name
    ].filter(Boolean).join(' ').toLowerCase()

    return type === 'password' || label.includes('password') || label.includes('密码')
  }

  getMaskedInputVariableName(component) {
    const explicitName = String(component?.config?.inputReference || '').trim()
    if (explicitName) {
      return explicitName
    }
    const componentId = String(component?.id || component?.componentId || '').trim()
    if (componentId) {
      return `secret_${componentId.replace(/[^A-Za-z0-9_]/g, '_')}`
    }
    return 'secret_password'
  }

  isRecordedLoginSubmitComponent(component) {
    if (!['button', 'clickable'].includes(component?.type)) {
      return false
    }

    const label = [
      this.getComponentLabel(component),
      component?.elementData?.text,
      component?.config?.recordingPagePath,
      component?.config?.recordingPageIdentity
    ].filter(Boolean).join(' ').toLowerCase()

    return (this.isRecordedLoginComponent(component) || this.isRecordedLoginPageComponent(component)) &&
      (label.includes('login') || label.includes('登录') || label.includes('登錄'))
  }

  isRecordedLoginPageComponent(component) {
    const config = component?.config || {}
    const pagePath = this.normalizeSnapshotAttributeValue(config.recordingPagePath || config.recordingPageIdentity || '')
    if (!pagePath) {
      return false
    }
    return /(?:^|[/#])login(?:[/?#]|$)/i.test(pagePath)
  }

  shouldSkipEmptyInputComponent(component) {
    if (component?.type !== 'input') {
      return false
    }
    const config = component.config || {}
    const value = config.value ?? config.inputValue ?? ''
    return config.recordingActionType === 'click' && String(value || '') === ''
  }

  isRecordedLoginComponent(component) {
    const config = component?.config || {}
    const elementData = component?.elementData || {}
    const attributes = elementData.attributes || {}
    const label = [
      this.getComponentLabel(component),
      config.placeholder,
      config.value,
      config.inputValue,
      elementData.text,
      attributes.placeholder,
      attributes['aria-label'],
      attributes.name,
      attributes.id,
      attributes.type
    ].filter(Boolean).join(' ').toLowerCase()
    const stepNumber = Number(config.recordingStepNumber || 0)
    if (stepNumber > 8) {
      return false
    }
    return [
      '请输入用户名',
      '用户名',
      '账号',
      '账户',
      '请输入密码',
      '密码',
      '登录',
      'login',
      'username',
      'user name',
      'password',
      'sign in'
    ].some(keyword => label.includes(keyword.toLowerCase()))
  }

  isSelectDropdownOptionComponent(component) {
    const elementData = this.getElementData(component, null) || {}
    const attributes = elementData.attributes || {}
    const role = this.normalizeSnapshotAttributeValue(attributes.role || elementData.type)
    const className = this.normalizeSnapshotAttributeValue(attributes.class)
    return role === 'option' || className.split(/\s+/).includes('el-select-dropdown__item')
  }

  isSelectDropdownTriggerComponent(component) {
    const elementData = this.getElementData(component, null) || {}
    const attributes = elementData.attributes || {}
    const role = this.normalizeSnapshotAttributeValue(attributes.role || elementData.type)
    const className = this.normalizeSnapshotAttributeValue(attributes.class)
    return role === 'combobox' || className.split(/\s+/).includes('el-select__wrapper')
  }

  isSelectDropdownWrapperComponent(component) {
    const elementData = this.getElementData(component, null) || {}
    const attributes = elementData.attributes || {}
    const role = this.normalizeSnapshotAttributeValue(attributes.role || elementData.type)
    const className = this.normalizeSnapshotAttributeValue(attributes.class)
    return role !== 'combobox' && className.split(/\s+/).includes('el-select__wrapper')
  }

  resolvePageComponents(config) {
    const components = [...(config.innerComponents || [])]
      .filter(component => component?.type && component.elementId)
      .sort((a, b) => (a.order ?? a.zIndex ?? 0) - (b.order ?? b.zIndex ?? 0))

    const componentMap = new Map(components.map(component => [component.id, component]))
    if (components.length <= 1) {
      return { components, componentMap }
    }

    const edges = (config.executionPath || [])
      .filter(step => step?.from?.portId && step?.to?.portId)
      .map(step => ({
        from: step.from,
        to: step.to
      }))

    const actionableComponents = components.filter(component => component.type !== 'iframe')
    const adjacency = new Map()
    const inDegree = new Map()

    actionableComponents.forEach(component => {
      adjacency.set(component.id, [])
      inDegree.set(component.id, 0)
    })

    edges.forEach(edge => {
      const fromId = edge.from?.componentId
      const toId = edge.to?.componentId
      if (!fromId || !toId || fromId === toId) {
        return
      }

      const fromComponent = componentMap.get(fromId)
      const toComponent = componentMap.get(toId)
      if (!fromComponent || !toComponent) {
        return
      }

      if (fromComponent.type === 'iframe' && toComponent.type !== 'iframe') {
        return
      }

      if (fromComponent.type !== 'iframe' && toComponent.type !== 'iframe') {
        adjacency.get(fromId).push(toId)
        inDegree.set(toId, inDegree.get(toId) + 1)
      }
    })

    const sortedIds = []
    const queue = actionableComponents
      .filter(component => inDegree.get(component.id) === 0)
      .sort((a, b) => this.compareComponentOrder(a, b, componentMap))
      .map(component => component.id)

    while (queue.length) {
      queue.sort((leftId, rightId) => this.compareComponentOrder(componentMap.get(leftId), componentMap.get(rightId), componentMap))
      const currentId = queue.shift()
      sortedIds.push(currentId)
      ;(adjacency.get(currentId) || []).forEach(targetId => {
        inDegree.set(targetId, inDegree.get(targetId) - 1)
        if (inDegree.get(targetId) === 0) {
          queue.push(targetId)
        }
      })
    }

    if (sortedIds.length !== actionableComponents.length) {
      return { components, componentMap }
    }

    const sortedActionables = sortedIds.map(id => componentMap.get(id)).filter(Boolean)
    const iframeComponents = components.filter(component => component.type === 'iframe')
    return {
      components: [...iframeComponents, ...sortedActionables].sort((a, b) => this.compareComponentOrder(a, b, componentMap)),
      componentMap
    }
  }

  compareComponentOrder(left, right, componentMap) {
    const leftPath = this.getComponentSortPath(left, componentMap)
    const rightPath = this.getComponentSortPath(right, componentMap)
    const maxLength = Math.max(leftPath.length, rightPath.length)
    for (let index = 0; index < maxLength; index += 1) {
      const leftValue = leftPath[index] ?? Number.MAX_SAFE_INTEGER
      const rightValue = rightPath[index] ?? Number.MAX_SAFE_INTEGER
      if (leftValue !== rightValue) {
        return leftValue - rightValue
      }
    }
    return String(left.id).localeCompare(String(right.id))
  }

  getComponentSortPath(component, componentMap) {
    const path = []
    let current = component
    while (current) {
      path.unshift(current.order ?? current.zIndex ?? 0)
      current = current.parentId ? componentMap.get(current.parentId) : null
    }
    return path
  }

  getFrameChain(component, componentMap) {
    const chain = []
    let current = component.parentId ? componentMap.get(component.parentId) : null
    while (current) {
      if (current.type === 'iframe') {
        chain.unshift(current)
      }
      current = current.parentId ? componentMap.get(current.parentId) : null
    }
    return chain
  }

  getComponentLabel(component) {
    return this.normalizeSnapshotAttributeValue(
      component?.elementData?.text || component?.elementData?.ref || component?.elementId || component?.type || 'component'
    )
  }

  getElementData(component, snapshotData) {
    return component?.elementData ||
      snapshotData?.interactiveElements?.find(element => element.id === component?.elementId)
  }

  normalizeSnapshotAttributeValue(value) {
    const normalized = String(value ?? '').trim()
    if (!normalized) {
      return ''
    }
    if (
      (normalized.startsWith('"') && normalized.endsWith('"')) ||
      (normalized.startsWith("'") && normalized.endsWith("'"))
    ) {
      return this.repairPossibleMojibake(normalized.slice(1, -1).trim())
    }
    return this.repairPossibleMojibake(normalized)
  }

  looksLikeUtf8Mojibake(value) {
    const text = String(value ?? '')
    if (!text) {
      return false
    }
    if (/[\u3400-\u9FFF\uF900-\uFAFF]/u.test(text)) {
      return false
    }
    if (/[\u0080-\u009F]/.test(text)) {
      return true
    }
    return /(?:Ã.|Â.|â.|æ.|ç.|å.|è.|é.|ê.|ë.|î.|ï.|ô.|ö.|ù.|ú.|û.|ü.|ñ.|ð.)/.test(text)
  }

  scoreReadableText(value) {
    const text = String(value ?? '')
    const cjkCount = (text.match(/[\u3400-\u9FFF\uF900-\uFAFF]/gu) || []).length
    const asciiCount = (text.match(/[A-Za-z0-9]/g) || []).length
    const whitespaceCount = (text.match(/\s/g) || []).length
    const latinCount = (text.match(/[\u00C0-\u00FF]/g) || []).length
    const controlCount = (text.match(/[\u0000-\u001F\u007F-\u009F]/g) || []).length
    const replacementCount = (text.match(/\uFFFD/g) || []).length
    return (cjkCount * 8) + asciiCount + (whitespaceCount * 0.2) - (latinCount * 3) - (controlCount * 8) - (replacementCount * 12)
  }

  repairPossibleMojibake(value) {
    let current = String(value ?? '')
    if (!this.looksLikeUtf8Mojibake(current)) {
      return current
    }
    if (typeof TextDecoder === 'undefined') {
      return current
    }

    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const bytes = Uint8Array.from(Array.from(current, char => char.charCodeAt(0) & 0xFF))
        const decoded = new TextDecoder('utf-8', { fatal: false }).decode(bytes).trim()
        if (!decoded) {
          break
        }
        const currentScore = this.scoreReadableText(current)
        const decodedScore = this.scoreReadableText(decoded)
        if (decodedScore <= currentScore + 1) {
          break
        }
        current = decoded
        if (!this.looksLikeUtf8Mojibake(current)) {
          break
        }
      } catch (error) {
        break
      }
    }

    return current
  }

  escapeSelectorText(value) {
    return this.normalizeSnapshotAttributeValue(value)
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
  }

  isMeaningfulLocatorText(value, maxLength = 80) {
    const normalized = this.normalizeSnapshotAttributeValue(value)
    if (!normalized || normalized.length > maxLength) {
      return false
    }

    const compact = normalized.replace(/\s+/g, '')
    if (!compact) {
      return false
    }

    return !/^[\uE000-\uF8FF]+$/u.test(compact)
  }

  getInputPlaceholder(component, snapshotData) {
    if (component?.type !== 'input') {
      return ''
    }

    const elementData = this.getElementData(component, snapshotData)

    const candidates = [
      component?.config?.placeholder,
      elementData?.attributes?.placeholder
    ]

    return candidates
      .map(value => this.normalizeSnapshotAttributeValue(value))
      .find(value => value && value !== '输入内容...' && value !== '输入内容') || ''
  }

  getLocatorRole(component, elementData) {
    const explicitRole = this.normalizeSnapshotAttributeValue(elementData?.attributes?.role)
    const validRoles = new Set([
      'button', 'checkbox', 'combobox', 'dialog', 'gridcell', 'link', 'listbox',
      'menuitem', 'option', 'radio', 'searchbox', 'switch', 'tab', 'textbox'
    ])
    if (explicitRole && explicitRole !== 'true' && validRoles.has(explicitRole)) {
      return explicitRole
    }

    const roleMap = {
      input: 'textbox',
      textbox: 'textbox',
      searchbox: 'textbox',
      button: 'button',
      link: 'link',
      a: 'link',
      select: 'combobox',
      combobox: 'combobox',
      listbox: 'listbox',
      checkbox: 'checkbox',
      radio: 'radio',
      tab: 'tab',
      menuitem: 'menuitem'
    }

    const role = roleMap[component?.type] || roleMap[elementData?.type] || ''
    return validRoles.has(role) ? role : ''
  }

  getRoleLocatorName(component, elementData) {
    const candidates = [
      elementData?.attributes?.['aria-label'],
      elementData?.attributes?.title,
      elementData?.attributes?.name
    ]

    if (component?.type !== 'input') {
      candidates.push(elementData?.attributes?.label)
    }

    if (['button', 'link', 'select', 'checkbox', 'radio', 'tab', 'menuitem', 'clickable'].includes(component?.type)) {
      candidates.push(elementData?.text)
    }

    return candidates
      .map(value => this.normalizeSnapshotAttributeValue(value))
      .find(value => this.isMeaningfulLocatorText(value)) || ''
  }

  getTextLocatorValue(component, elementData) {
    if (!['button', 'link', 'tab', 'menuitem', 'clickable'].includes(component?.type)) {
      return ''
    }

    const text = this.normalizeSnapshotAttributeValue(elementData?.text)
    return this.isMeaningfulLocatorText(text) ? text : ''
  }

  getConfiguredRecordingSelectors(component) {
    const configSelectors = component?.config?.recordingSelectors
    if (Array.isArray(configSelectors) && configSelectors.length) {
      return configSelectors
    }

    const rawEventSelectors = component?.config?.recordingSnapshotRef?.selectors
    if (Array.isArray(rawEventSelectors) && rawEventSelectors.length) {
      return rawEventSelectors
    }

    return []
  }

  parseRecordingSelectorSpec(selector) {
    if (!selector || typeof selector !== 'object') {
      return null
    }

    const selectorType = String(selector.type || '').trim().toLowerCase()
    const rawValue = this.normalizeSnapshotAttributeValue(selector.value || '')
    if (!rawValue || rawValue.includes('[data-ref=')) {
      return null
    }

    const roleMatch = rawValue.match(/^role=([A-Za-z0-9_-]+)(?:\[name=(["']?)(.*?)\2\])?$/)
    if (selectorType === 'role' && roleMatch) {
      const role = roleMatch[1]
      const name = this.normalizeSnapshotAttributeValue(roleMatch[3] || '')
      if (role && name) {
        return {
          type: 'role',
          role,
          name,
          selector: `get_by_role("${this.escapeSelectorText(role)}", name="${this.escapeSelectorText(name)}")`
        }
      }
      return null
    }

    if (selectorType === 'text' && rawValue.startsWith('text=')) {
      const text = rawValue.replace(/^text=/, '').trim()
      const normalizedText = this.normalizeSnapshotAttributeValue(text)
      if (this.isMeaningfulLocatorText(normalizedText)) {
        return {
          type: 'text',
          value: normalizedText,
          selector: `get_by_text("${this.escapeSelectorText(normalizedText)}")`
        }
      }
      return null
    }

    if (selectorType === 'by_xpath') {
      return null
    }

    if (selectorType === 'by_id') {
      return {
        type: 'selector',
        value: `#${this.escapeCssIdentifier(rawValue)}`,
        selector: `locator("#${this.escapeSelectorText(this.escapeCssIdentifier(rawValue))}")`
      }
    }

    if (selectorType === 'by_name') {
      const tag = this.getElementSelectorBases(component, component?.elementData || {})[0] || ''
      const base = tag && !tag.startsWith('[') ? tag : ''
      const value = `${base}[name="${this.escapeSelectorText(rawValue)}"]`
      return {
        type: 'selector',
        value,
        selector: `locator("${this.escapeSelectorText(value)}")`
      }
    }

    if (['css', 'id', 'name', 'placeholder', 'text', 'by_cssselector'].includes(selectorType)) {
      return {
        type: 'selector',
        value: rawValue,
        selector: `locator("${this.escapeSelectorText(rawValue)}")`
      }
    }

    return null
  }

  getRecordingSelectorRank(selector) {
    const selectorType = String(selector?.type || '').trim().toLowerCase()
    const rawValue = String(selector?.value || '').trim()
    if (['css', 'by_cssselector', 'by_id', 'by_name', 'id', 'name', 'placeholder'].includes(selectorType)) {
      return 0
    }
    if (selectorType === 'role' || rawValue.startsWith('role=')) {
      return 2
    }
    if (selectorType === 'text' || rawValue.startsWith('text=') || rawValue.includes(':has-text')) {
      return 3
    }
    return 4
  }

  buildRecordingLocatorSpecs(component) {
    return this.getConfiguredRecordingSelectors(component)
      .slice()
      .sort((left, right) => {
        const rankDiff = this.getRecordingSelectorRank(left) - this.getRecordingSelectorRank(right)
        if (rankDiff !== 0) {
          return rankDiff
        }
        return Number(left?.priority ?? 99) - Number(right?.priority ?? 99)
      })
      .map(selector => this.parseRecordingSelectorSpec(selector))
      .filter(Boolean)
  }

  getNonRefSnapshotSelector(elementData) {
    const selectors = elementData?.selectors || []
    const stableClassName = this.normalizeSnapshotAttributeValue(elementData?.attributes?.class)
      .split(/\s+/)
      .find(className => ['ql-editor'].includes(className))
    if (stableClassName) {
      const tag = this.normalizeSnapshotAttributeValue(elementData?.attributes?.tag || elementData?.type)
      return `${tag && tag !== 'textbox' ? tag : ''}.${this.escapeSelectorText(stableClassName)}`
    }

    const selectorEntry = selectors.find(selector => {
      const selectorType = String(selector?.type || '').toLowerCase()
      const value = String(selector?.value || '').trim()
      if (!value || selectorType === 'data-ref' || value.includes('[data-ref=')) {
        return false
      }
      if (value.startsWith('role=') || value.startsWith('text=')) {
        return false
      }
      if (selectorType === 'class' || selectorType === 'by_classname') {
        return false
      }
      return ['css', 'id', 'name', 'placeholder', 'by_cssselector'].includes(selectorType)
    }) || selectors.find(selector => {
      const selectorType = String(selector?.type || '').toLowerCase()
      const value = String(selector?.value || '').trim()
      if (!value || value.includes('[data-ref=') || value.startsWith('role=') || value.startsWith('text=')) {
        return false
      }
      if (selectorType === 'class' || selectorType === 'by_classname') {
        return false
      }
      return /^[#.[]/.test(value) || /^[a-z][a-z0-9_-]*(?:[#.:[].*)?$/i.test(value)
    })

    if (!selectorEntry) {
      const className = this.normalizeSnapshotAttributeValue(elementData?.attributes?.class).split(/\s+/).find(Boolean)
      const tag = this.normalizeSnapshotAttributeValue(elementData?.attributes?.tag || elementData?.type)
      if (className) {
        return `${tag && tag !== 'textbox' ? tag : ''}.${this.escapeSelectorText(className)}`
      }
      return ''
    }

    return selectorEntry?.value || ''
  }

  getElementSelectorBases(component, elementData) {
    const explicitType = elementData?.type

    switch (component?.type) {
      case 'input':
        return ['input', 'textarea', '[role="textbox"]']
      case 'button':
        return ['button', '[role="button"]']
      case 'link':
        return ['a', '[role="link"]']
      case 'select':
        return ['select', '[role="combobox"]', '[role="listbox"]']
      case 'checkbox':
        return ['input[type="checkbox"]', '[role="checkbox"]']
      case 'radio':
        return ['input[type="radio"]', '[role="radio"]']
      case 'tab':
        return ['[role="tab"]', 'button', 'a']
      case 'menuitem':
        return ['[role="menuitem"]', 'button', 'a']
      case 'clickable':
        return ['button', 'a', '[role="button"]', '[onclick]']
      case 'file':
        return ['input[type="file"]']
      case 'iframe':
        return explicitType === 'frame' ? ['frame', 'iframe'] : ['iframe', 'frame']
      default:
        return explicitType && explicitType !== 'generic'
          ? [explicitType]
          : [component?.elementId || 'body']
    }
  }

  getElementAttributeSelector(component, elementData) {
    const attributeKeysByType = {
      input: ['placeholder', 'name', 'id', 'aria-label', 'title', 'data-testid'],
      button: ['aria-label', 'title', 'name', 'id', 'data-testid'],
      link: ['aria-label', 'title', 'href', 'id', 'data-testid'],
      select: ['aria-label', 'name', 'id', 'title', 'data-testid'],
      checkbox: ['aria-label', 'name', 'id', 'title', 'data-testid'],
      radio: ['aria-label', 'name', 'id', 'title', 'value', 'data-testid'],
      tab: ['aria-label', 'name', 'id', 'title', 'data-testid'],
      menuitem: ['aria-label', 'name', 'id', 'title', 'data-testid'],
      clickable: ['aria-label', 'name', 'id', 'title', 'data-testid'],
      file: ['aria-label', 'name', 'id', 'title', 'data-testid', 'accept'],
      iframe: ['title', 'name', 'id', 'src']
    }

    const selectorBases = this.getElementSelectorBases(component, elementData)
    const attributeKeys = attributeKeysByType[component?.type] || ['id', 'name', 'title', 'data-testid']

    for (const key of attributeKeys) {
      const value = this.normalizeSnapshotAttributeValue(elementData?.attributes?.[key])
      if (!value || value === 'true' || value === 'false') {
        continue
      }

      const escapedValue = this.escapeSelectorText(value)
      for (const baseSelector of selectorBases) {
        return `${baseSelector}[${key}="${escapedValue}"]`
      }
    }

    return ''
  }

  getElementFallbackSelector(component, elementData) {
    const selectorBases = this.getElementSelectorBases(component, elementData)
    return selectorBases[0] || component?.elementId || 'body'
  }

  getFrameLocatorSpec(component, snapshotData) {
    const elementData = this.getElementData(component, snapshotData)
    const selector = this.getElementAttributeSelector(component, elementData) ||
      this.getElementFallbackSelector(component, elementData)

    return {
      value: selector,
      selector: `frame_locator("${this.escapeSelectorText(selector)}")`
    }
  }

  getElementLocatorSpec(component, snapshotData) {
    const elementData = this.getElementData(component, snapshotData)
    const selector = this.getElementSelector(component, snapshotData)
    const rawPlaceholderValues = [
      component?.config?.placeholder,
      elementData?.attributes?.placeholder
    ]
    const preferSelectorForInput = component?.type === 'input' &&
      selector &&
      rawPlaceholderValues.some(value => this.looksLikeUtf8Mojibake(value))
    const placeholder = this.getInputPlaceholder(component, snapshotData)
    const locatorSpecs = this.buildRecordingLocatorSpecs(component)

    if (preferSelectorForInput && selector) {
      locatorSpecs.push({
        type: 'selector',
        value: selector,
        selector: `locator("${this.escapeSelectorText(selector)}")`
      })
    }

    if (placeholder) {
      locatorSpecs.push({
        type: 'placeholder',
        value: placeholder,
        selector: `get_by_placeholder("${this.escapeSelectorText(placeholder)}")`
      })
    }

    if (component?.type === 'input' && selector) {
      locatorSpecs.push({
        type: 'selector',
        value: selector,
        selector: `locator("${this.escapeSelectorText(selector)}")`
      })
    }

    if (this.isSelectDropdownWrapperComponent(component) && selector) {
      locatorSpecs.push({
        type: 'selector',
        value: selector,
        selector: `locator("${this.escapeSelectorText(selector)}")`
      })
    }

    const role = this.getLocatorRole(component, elementData)
    const roleName = this.getRoleLocatorName(component, elementData)
    if (role && roleName) {
      locatorSpecs.push({
        type: 'role',
        role,
        name: roleName,
        selector: `get_by_role("${this.escapeSelectorText(role)}", name="${this.escapeSelectorText(roleName)}")`
      })
    }

    const textValue = this.getTextLocatorValue(component, elementData)
    if (textValue) {
      locatorSpecs.push({
        type: 'text',
        value: textValue,
        selector: `get_by_text("${this.escapeSelectorText(textValue)}")`
      })
    }

    locatorSpecs.push({
      type: 'selector',
      value: selector,
      selector: `locator("${this.escapeSelectorText(selector)}")`
    })

    const dedupedSpecs = []
    const seenSpecKeys = new Set()
    locatorSpecs
      .filter(spec => spec?.value || (spec?.role && spec?.name))
      .forEach(spec => {
        const key = spec.type === 'role'
          ? `${spec.type}:${spec.role}:${spec.name}`
          : `${spec.type}:${spec.value}`
        if (seenSpecKeys.has(key)) {
          return
        }
        seenSpecKeys.add(key)
        dedupedSpecs.push(spec)
      })

    const [primarySpec, ...fallbackSpecs] = dedupedSpecs
    return {
      ...(primarySpec || {
        type: 'selector',
        value: 'body',
        selector: 'locator("body")'
      }),
      fallbacks: fallbackSpecs
    }
  }

  buildLocatorAssignmentCode(scopeVar, locatorVar, locatorSpec) {
    const locatorSpecs = [locatorSpec, ...(locatorSpec?.fallbacks || [])]
      .filter(spec => spec?.type && (spec?.value || (spec?.role && spec?.name)))
    if (!locatorSpecs.length) {
      return `        ${locatorVar} = ${scopeVar}.locator('body')\n`
    }

    return locatorSpecs
      .map((spec, index) => {
        const locatorExpression = this.buildLocatorExpression(scopeVar, spec)
        if (index === 0) {
          return `        ${locatorVar} = ${locatorExpression}\n`
        }
        return `        try:\n            await ${locatorVar}.first.wait_for(state='visible', timeout=4000)\n        except Exception:\n            ${locatorVar} = ${locatorExpression}\n`
      })
      .join('')
  }

  buildLocatorCandidatesCode(scopeVar, candidatesVar, primaryLocatorVar, locatorSpec) {
    const locatorSpecs = [locatorSpec, ...(locatorSpec?.fallbacks || [])]
      .filter(spec => spec?.type && (spec?.value || (spec?.role && spec?.name)))
    const expressions = [primaryLocatorVar]
    const seen = new Set([primaryLocatorVar])

    locatorSpecs.forEach(spec => {
      const expression = this.buildLocatorExpression(scopeVar, spec)
      if (!seen.has(expression)) {
        seen.add(expression)
        expressions.push(expression)
      }
    })

    return `        ${candidatesVar} = [${expressions.join(', ')}]\n`
  }

  buildLocatorExpression(scopeVar, locatorSpec) {
    switch (locatorSpec?.type) {
      case 'placeholder':
        return `${scopeVar}.get_by_placeholder('${this.escapePythonString(locatorSpec.value)}')`
      case 'role':
        return `${scopeVar}.get_by_role('${this.escapePythonString(locatorSpec.role)}', name='${this.escapePythonString(locatorSpec.name)}')`
      case 'text':
        return `${scopeVar}.get_by_text('${this.escapePythonString(locatorSpec.value)}')`
      default:
        return `${scopeVar}.locator('${this.escapePythonString(locatorSpec.value)}')`
    }
  }

  buildCheckableRecordedRectLiteral(component) {
    const rectCandidates = [
      component?.elementData?.rect,
      component?.config?.control?.rect,
      component?.config?.recordingSnapshotRef?.element?.rect
    ]
    const rect = rectCandidates.find(candidate => (
      candidate &&
      Number.isFinite(Number(candidate.x)) &&
      Number.isFinite(Number(candidate.y))
    ))

    if (!rect) {
      return 'None'
    }

    const x = Number(rect.x) || 0
    const y = Number(rect.y) || 0
    const width = Number(rect.width) || 0
    const height = Number(rect.height) || 0
    return `{'x': ${x}, 'y': ${y}, 'width': ${width}, 'height': ${height}}`
  }

  resolveInputExpression(component, keys) {
    if (component.config?.inputMode === 'reference') {
      const variableName = this.escapePythonString(component.config?.inputReference || '')
      return `str(flow_vars.get('${variableName}', ''))`
    }

    if (this.isMaskedPasswordInputComponent(component)) {
      const variableName = this.escapePythonString(this.getMaskedInputVariableName(component))
      const label = this.escapePythonString(this.getComponentLabel(component) || variableName)
      return `require_testhub_flow_var(flow_vars, '${variableName}', '${label}')`
    }

    const literalValue = keys
      .map(key => component.config?.[key])
      .find(value => value !== undefined && value !== null && value !== '')

    return `'${this.escapePythonString(literalValue || '')}'`
  }

  getElementSelector(component, snapshotData) {
    const elementData = this.getElementData(component, snapshotData)

    const snapshotSelector = this.getNonRefSnapshotSelector(elementData)
    if (snapshotSelector) {
      return snapshotSelector
    }

    const attributeSelector = this.getElementAttributeSelector(component, elementData)
    if (attributeSelector) {
      return attributeSelector
    }

    const textValue = this.normalizeSnapshotAttributeValue(elementData?.text)
    if (this.isMeaningfulLocatorText(textValue, 40) && !['input', 'select', 'iframe'].includes(component?.type)) {
      return `text="${this.escapeSelectorText(textValue)}"`
    }

    return this.getElementFallbackSelector(component, elementData)
  }

  escapePythonString(value) {
    return this.normalizeSnapshotAttributeValue(value)
      .replace(/\\/g, '\\\\')
      .replace(/'/g, "\\'")
      .replace(/\r?\n/g, '\\n')
  }

  escapeCssIdentifier(value) {
    return String(value ?? '').replace(/([!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~ ])/g, '\\$1')
  }

  toPythonBool(value) {
    return value ? 'True' : 'False'
  }

  topologicalSort(nodes, edges) {
    const graph = new Map()
    const inDegree = new Map()

    nodes.forEach(node => {
      graph.set(node.id, [])
      inDegree.set(node.id, 0)
    })

    edges
      .filter(edge => edge.source?.cell && edge.target?.cell)
      .filter(edge => graph.has(edge.source.cell) && graph.has(edge.target.cell))
      .filter(edge => edge.source.cell !== edge.target.cell)
      .forEach(edge => {
        graph.get(edge.source.cell).push(edge.target.cell)
        inDegree.set(edge.target.cell, inDegree.get(edge.target.cell) + 1)
      })

    const queue = []
    const result = []

    inDegree.forEach((degree, nodeId) => {
      if (degree === 0) {
        queue.push(nodeId)
      }
    })

    while (queue.length > 0) {
      const nodeId = queue.shift()
      result.push(nodeId)

      const neighbors = graph.get(nodeId) || []
      neighbors.forEach(neighbor => {
        inDegree.set(neighbor, inDegree.get(neighbor) - 1)
        if (inDegree.get(neighbor) === 0) {
          queue.push(neighbor)
        }
      })
    }

    return result.length === nodes.length ? result : nodes.map(node => node.id)
  }
}

export default new PlaywrightScriptGenerator()
