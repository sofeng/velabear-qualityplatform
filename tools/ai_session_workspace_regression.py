#!/usr/bin/env python
"""Run AI session workspace governance browser regressions.

This runner keeps the existing scenario scripts repeatable and Harness-ready:
it performs local TestHub preflight checks, runs selected browser scenarios,
parses their JSON evidence files, verifies screenshots, and writes suite-level
JSON and Markdown reports.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except Exception as exc:  # pragma: no cover - handled by preflight output
    requests = None
    REQUESTS_IMPORT_ERROR = exc
else:
    REQUESTS_IMPORT_ERROR = None


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = 'http://localhost:41080'
DEFAULT_OUTPUT_DIR = REPO_ROOT / 'playwright_snapshot' / 'ai-session-workspace-regression'
LEGACY_RESULT_PREFIX = '.tmp-ai-session-workspace-'


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    script: str
    result_file: str
    screenshot_file: str
    category: str
    required_for_smoke: bool = False


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key='space-url',
        name='空间与独立预览 URL 治理',
        script='.tmp-verify-ai-session-workspace-space-url.py',
        result_file='.tmp-ai-session-workspace-space-url-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-space-url-e2e.png',
        category='foundation',
        required_for_smoke=True,
    ),
    Scenario(
        key='snapshots',
        name='快照与基线治理',
        script='.tmp-verify-ai-session-workspace-snapshots.py',
        result_file='.tmp-ai-session-workspace-snapshots-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-snapshots-e2e.png',
        category='foundation',
        required_for_smoke=True,
    ),
    Scenario(
        key='governance',
        name='生命周期、审计与策略治理',
        script='.tmp-verify-ai-session-workspace-governance.py',
        result_file='.tmp-ai-session-workspace-governance-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-governance-e2e.png',
        category='foundation',
    ),
    Scenario(
        key='index',
        name='跨会话工作区索引治理',
        script='.tmp-verify-ai-session-workspace-index.py',
        result_file='.tmp-ai-session-workspace-index-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-index-e2e.png',
        category='foundation',
    ),
    Scenario(
        key='report',
        name='治理报告导出',
        script='.tmp-verify-ai-session-workspace-report.py',
        result_file='.tmp-ai-session-workspace-report-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-report-e2e.png',
        category='foundation',
    ),
    Scenario(
        key='delivery',
        name='交付包与归档只读治理',
        script='.tmp-verify-ai-session-workspace-delivery.py',
        result_file='.tmp-ai-session-workspace-delivery-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-delivery-e2e.png',
        category='hardening',
        required_for_smoke=True,
    ),
    Scenario(
        key='backfill',
        name='历史会话工作区补建',
        script='.tmp-verify-ai-session-workspace-backfill.py',
        result_file='.tmp-ai-session-workspace-backfill-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-backfill-e2e.png',
        category='hardening',
    ),
    Scenario(
        key='boundary',
        name='边界与异常治理',
        script='.tmp-verify-ai-session-workspace-boundary.py',
        result_file='.tmp-ai-session-workspace-boundary-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-boundary-e2e.png',
        category='hardening',
        required_for_smoke=True,
    ),
    Scenario(
        key='cleanup',
        name='清理与配额治理',
        script='.tmp-verify-ai-session-workspace-cleanup.py',
        result_file='.tmp-ai-session-workspace-cleanup-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-cleanup-e2e.png',
        category='hardening',
        required_for_smoke=True,
    ),
    Scenario(
        key='permission',
        name='权限与只读策略治理',
        script='.tmp-verify-ai-session-workspace-permission.py',
        result_file='.tmp-ai-session-workspace-permission-result.json',
        screenshot_file='playwright_snapshot/ai-session-workspace-permission-e2e.png',
        category='hardening',
        required_for_smoke=True,
    ),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run TestHub AI session workspace governance browser regression scenarios.',
    )
    parser.add_argument(
        '--base-url',
        default=os.environ.get('TESTHUB_BASE_URL', DEFAULT_BASE_URL),
        help=f'TestHub frontend URL. Defaults to {DEFAULT_BASE_URL}.',
    )
    parser.add_argument(
        '--scenario',
        action='append',
        dest='scenarios',
        choices=[item.key for item in SCENARIOS],
        help='Scenario key to run. Can be passed multiple times.',
    )
    parser.add_argument(
        '--suite',
        choices=['smoke', 'hardening', 'foundation', 'all'],
        default='smoke',
        help='Scenario group to run when --scenario is not supplied. Defaults to smoke.',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available scenarios and exit.',
    )
    parser.add_argument(
        '--output-dir',
        default=str(DEFAULT_OUTPUT_DIR),
        help='Directory for suite-level JSON and Markdown reports.',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=int(os.environ.get('TESTHUB_WORKSPACE_REGRESSION_TIMEOUT', '360')),
        help='Per-scenario timeout in seconds.',
    )
    parser.add_argument(
        '--skip-preflight',
        action='store_true',
        help='Skip local service and dependency checks.',
    )
    parser.add_argument(
        '--keep-going',
        action='store_true',
        help='Continue running later scenarios after a failure.',
    )
    parser.add_argument(
        '--python',
        default=sys.executable,
        help='Python executable used to run scenario scripts.',
    )
    return parser.parse_args(argv)


def list_scenarios() -> None:
    for item in SCENARIOS:
        smoke = ' smoke' if item.required_for_smoke else ''
        print(f'{item.key:12} {item.category:10}{smoke:7} {item.name}')


def select_scenarios(args: argparse.Namespace) -> list[Scenario]:
    if args.scenarios:
        requested = set(args.scenarios)
        return [item for item in SCENARIOS if item.key in requested]
    if args.suite == 'all':
        return list(SCENARIOS)
    if args.suite == 'smoke':
        return [item for item in SCENARIOS if item.required_for_smoke]
    return [item for item in SCENARIOS if item.category == args.suite]


def run_command(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ},
    )


def check_http(base_url: str) -> dict[str, Any]:
    if requests is None:
        return {
            'name': 'python_requests',
            'ok': False,
            'detail': f'Cannot import requests: {REQUESTS_IMPORT_ERROR}',
        }
    try:
        response = requests.get(base_url, timeout=10)
        return {
            'name': 'frontend_http',
            'ok': response.status_code < 500,
            'status': response.status_code,
            'detail': base_url,
        }
    except Exception as exc:
        return {
            'name': 'frontend_http',
            'ok': False,
            'detail': str(exc),
        }


def check_python_module(module: str) -> dict[str, Any]:
    completed = run_command(
        [
            sys.executable,
            '-c',
            f'import {module}; print("ok")',
        ],
        timeout=30,
    )
    return {
        'name': f'python_module:{module}',
        'ok': completed.returncode == 0,
        'detail': (completed.stdout or completed.stderr).strip(),
    }


def check_docker_container(name: str) -> dict[str, Any]:
    completed = run_command(
        ['docker', 'inspect', '-f', '{{.State.Running}}', name],
        timeout=30,
    )
    detail = (completed.stdout or completed.stderr).strip()
    return {
        'name': f'container:{name}',
        'ok': completed.returncode == 0 and detail.lower() == 'true',
        'detail': detail,
    }


def run_preflight(base_url: str) -> dict[str, Any]:
    checks = [
        check_http(base_url),
        check_python_module('requests'),
        check_python_module('playwright'),
    ]
    for container in (
        'testhub-local-frontend',
        'testhub-local-backend',
        'testhub-local-ai-dev-worker',
        'testhub-local-celery-worker',
    ):
        checks.append(check_docker_container(container))
    return {
        'ok': all(item.get('ok') for item in checks),
        'checks': checks,
    }


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {'ok': False, 'error': f'Failed to read JSON: {exc}'}


def result_passed(payload: dict[str, Any]) -> bool:
    if 'ok' in payload:
        return bool(payload.get('ok'))
    if 'allPassed' in payload:
        return bool(payload.get('allPassed'))
    checks = payload.get('checks')
    if isinstance(checks, dict):
        return all(bool(value) for value in checks.values())
    return False


def collect_evidence(scenario: Scenario, started_at: float) -> dict[str, Any]:
    result_path = REPO_ROOT / scenario.result_file
    screenshot_path = REPO_ROOT / scenario.screenshot_file
    payload = read_json(result_path) if result_path.exists() else {'ok': False, 'error': 'Result JSON was not created.'}
    screenshot_exists = screenshot_path.is_file()
    screenshot_recent = screenshot_exists and screenshot_path.stat().st_mtime >= started_at - 2
    return {
        'result_file': str(result_path),
        'result_file_exists': result_path.is_file(),
        'screenshot_file': str(screenshot_path),
        'screenshot_exists': screenshot_exists,
        'screenshot_recent': screenshot_recent,
        'screenshot_size': screenshot_path.stat().st_size if screenshot_exists else 0,
        'payload_ok': result_passed(payload),
        'payload': payload,
    }


def run_scenario(scenario: Scenario, args: argparse.Namespace) -> dict[str, Any]:
    script_path = REPO_ROOT / scenario.script
    started = time.time()
    started_at = utc_now_iso()
    if not script_path.is_file():
        return {
            'key': scenario.key,
            'name': scenario.name,
            'category': scenario.category,
            'ok': False,
            'started_at': started_at,
            'finished_at': utc_now_iso(),
            'duration_seconds': 0,
            'error': f'Scenario script not found: {script_path}',
            'evidence': collect_evidence(scenario, started),
        }

    completed = run_command([args.python, str(script_path)], timeout=args.timeout)
    finished = time.time()
    evidence = collect_evidence(scenario, started)
    ok = completed.returncode == 0 and evidence['payload_ok'] and evidence['screenshot_exists'] and evidence['screenshot_recent']
    return {
        'key': scenario.key,
        'name': scenario.name,
        'category': scenario.category,
        'ok': ok,
        'started_at': started_at,
        'finished_at': utc_now_iso(),
        'duration_seconds': round(finished - started, 2),
        'returncode': completed.returncode,
        'stdout_tail': completed.stdout[-4000:],
        'stderr_tail': completed.stderr[-4000:],
        'evidence': evidence,
    }


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        '# AI 会话工作区治理回归报告',
        '',
        f"- 生成时间：{report['generated_at']}",
        f"- 平台地址：{report['base_url']}",
        f"- 套件：{report['suite']}",
        f"- 结论：{'通过' if report['ok'] else '失败'}",
        f"- 场景：{report['passed_count']} / {report['scenario_count']} 通过",
        '',
        '## 前置检查',
        '',
    ]
    for item in report.get('preflight', {}).get('checks') or []:
        lines.append(f"- {'通过' if item.get('ok') else '失败'}：{item.get('name')} - {item.get('detail', '')}")
    lines.extend(['', '## 场景结果', ''])
    for item in report.get('results') or []:
        evidence = item.get('evidence') or {}
        lines.extend([
            f"### {item.get('name')} ({item.get('key')})",
            '',
            f"- 结果：{'通过' if item.get('ok') else '失败'}",
            f"- 耗时：{item.get('duration_seconds')} 秒",
            f"- JSON：{evidence.get('result_file')}",
            f"- 截图：{evidence.get('screenshot_file')}",
            f"- 截图有效：{'是' if evidence.get('screenshot_exists') and evidence.get('screenshot_recent') else '否'}",
            '',
        ])
        if not item.get('ok'):
            lines.extend([
                '```text',
                str(item.get('error') or item.get('stderr_tail') or item.get('stdout_tail') or 'no failure output')[-2000:],
                '```',
                '',
            ])
    path.write_text('\n'.join(lines), encoding='utf-8')


def build_report(args: argparse.Namespace, scenarios: list[Scenario], preflight: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    passed_count = len([item for item in results if item.get('ok')])
    return {
        'schema_version': 'ai-session-workspace-regression-suite.v1',
        'generated_at': utc_now_iso(),
        'base_url': args.base_url,
        'suite': args.suite,
        'selected_scenarios': [item.key for item in scenarios],
        'scenario_count': len(results),
        'passed_count': passed_count,
        'failed_count': len(results) - passed_count,
        'ok': bool(preflight.get('ok') and results and passed_count == len(results)),
        'preflight': preflight,
        'results': results,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.list:
        list_scenarios()
        return 0

    scenarios = select_scenarios(args)
    if not scenarios:
        print('No scenarios selected.', file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = {'ok': True, 'checks': []} if args.skip_preflight else run_preflight(args.base_url)
    if not preflight.get('ok'):
        report = build_report(args, scenarios, preflight, [])
        json_path = output_dir / 'ai-session-workspace-regression-result.json'
        md_path = output_dir / 'ai-session-workspace-regression-report.md'
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        write_markdown_report(report, md_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        print(f'[workspace-regression] running {scenario.key}: {scenario.name}', flush=True)
        result = run_scenario(scenario, args)
        results.append(result)
        print(
            f"[workspace-regression] {'PASS' if result.get('ok') else 'FAIL'} "
            f"{scenario.key} ({result.get('duration_seconds')}s)",
            flush=True,
        )
        if not result.get('ok') and not args.keep_going:
            break

    report = build_report(args, scenarios, preflight, results)
    json_path = output_dir / 'ai-session-workspace-regression-result.json'
    md_path = output_dir / 'ai-session-workspace-regression-report.md'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    write_markdown_report(report, md_path)
    print(json.dumps({
        'ok': report['ok'],
        'scenario_count': report['scenario_count'],
        'passed_count': report['passed_count'],
        'failed_count': report['failed_count'],
        'json_report': str(json_path),
        'markdown_report': str(md_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
