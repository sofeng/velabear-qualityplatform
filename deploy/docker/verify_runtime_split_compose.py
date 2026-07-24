import argparse
import json
import subprocess
import sys
from pathlib import Path


REQUIRED_SERVICES = {
    'testhub-mysql',
    'testhub-redis',
    'testhub-backend-init',
    'testhub-backend',
    'testhub-automation-service',
    'testhub-document-service',
    'testhub-asset-service',
    'testhub-integration-service',
    'testhub-report-service',
    'testhub-deployment-service',
    'testhub-asset-worker',
    'testhub-deployment-worker',
    'testhub-ai-dev-worker',
    'testhub-frontend',
    'testhub-codex-runtime',
}

SOCKET_SERVICES = {
    'testhub-integration-service',
    'testhub-deployment-worker',
    'testhub-ai-dev-worker',
}

EXPECTED_RUNTIME_CONTRACTS = {
    'testhub-backend-init': ('core', 'backend.urls_core'),
    'testhub-backend': ('core', 'backend.urls_core'),
    'testhub-automation-service': ('automation', 'backend.urls_automation'),
    'testhub-document-service': ('document', 'backend.urls_document'),
    'testhub-asset-service': ('asset', 'backend.urls_asset'),
    'testhub-integration-service': ('integration', 'backend.urls_integration'),
    'testhub-report-service': ('report', 'backend.urls_report'),
    'testhub-deployment-service': ('deployment', 'backend.urls_deployment'),
    'testhub-asset-worker': ('asset-worker', 'backend.urls_asset'),
    'testhub-deployment-worker': ('deployment-worker', 'backend.urls_deployment'),
    'testhub-ai-dev-worker': ('ai-dev-worker', 'backend.urls_integration'),
}


def parse_args():
    parser = argparse.ArgumentParser(description='Verify TestHub split-runtime Compose policy.')
    parser.add_argument('-f', '--file', action='append', required=True, dest='files')
    parser.add_argument('--protected', action='store_true')
    return parser.parse_args()


def load_compose_config(files):
    command = ['docker', 'compose']
    for file_name in files:
        command.extend(['-f', str(Path(file_name))])
    command.extend(['config', '--format', 'json'])
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def volume_targets(service):
    return {
        str(volume.get('target') or '')
        for volume in service.get('volumes') or []
        if isinstance(volume, dict)
    }


def published_targets(service):
    return {
        int(port.get('target'))
        for port in service.get('ports') or []
        if isinstance(port, dict) and port.get('target') is not None
    }


def main():
    args = parse_args()
    config = load_compose_config(args.files)
    services = config.get('services') or {}
    violations = []

    missing = sorted(REQUIRED_SERVICES - set(services))
    unexpected_generic_workers = sorted(
        name for name in services if name in {'testhub-celery-worker', 'celery-worker'}
    )
    if missing:
        violations.append(f'missing services: {missing}')
    if unexpected_generic_workers:
        violations.append(f'generic workers are forbidden: {unexpected_generic_workers}')

    backend = services.get('testhub-backend') or {}
    backend_targets = volume_targets(backend)
    for forbidden_target in ('/var/run/docker.sock', '/workspace/source-repo', '/app/tools'):
        if forbidden_target in backend_targets:
            violations.append(f'core backend mounts forbidden target: {forbidden_target}')
    unexpected_backend_ports = published_targets(backend) - {8000}
    if unexpected_backend_ports:
        violations.append(f'core backend publishes tool ports: {sorted(unexpected_backend_ports)}')

    automation = services.get('testhub-automation-service') or {}
    automation_ports = published_targets(automation)
    if not ({9222, 6080} <= automation_ports):
        violations.append('automation service does not publish CDP and noVNC ranges')
    if '/var/run/docker.sock' in volume_targets(automation):
        violations.append('automation service must not mount Docker Socket')

    actual_socket_services = {
        name
        for name, service in services.items()
        if '/var/run/docker.sock' in volume_targets(service)
    }
    if actual_socket_services != SOCKET_SERVICES:
        violations.append(
            'Docker Socket service set mismatch: '
            f'expected={sorted(SOCKET_SERVICES)} actual={sorted(actual_socket_services)}'
        )

    for service_name, (expected_role, expected_urlconf) in EXPECTED_RUNTIME_CONTRACTS.items():
        environment = (services.get(service_name) or {}).get('environment') or {}
        if environment.get('TESTHUB_RUNTIME_ROLE') != expected_role:
            violations.append(
                f'{service_name} runtime role mismatch: '
                f'{environment.get("TESTHUB_RUNTIME_ROLE")!r}'
            )
        if environment.get('DJANGO_ROOT_URLCONF') != expected_urlconf:
            violations.append(
                f'{service_name} URLConf mismatch: '
                f'{environment.get("DJANGO_ROOT_URLCONF")!r}'
            )

    deployment_service_image = (services.get('testhub-deployment-service') or {}).get('image')
    deployment_worker_image = (services.get('testhub-deployment-worker') or {}).get('image')
    if deployment_service_image != deployment_worker_image:
        violations.append(
            'deployment service and worker must use the same role image: '
            f'service={deployment_service_image!r} worker={deployment_worker_image!r}'
        )

    for service_name in ('testhub-deployment-service', 'testhub-deployment-worker'):
        if '/workspace-release' not in volume_targets(services.get(service_name) or {}):
            violations.append(f'{service_name} does not mount /workspace-release')

    expected_task_modules = {
        'testhub-asset-worker': 'apps.knowledge.tasks',
        'testhub-deployment-worker': 'apps.deployments.tasks',
        'testhub-ai-dev-worker': 'apps.ai_development.tasks',
    }
    for service_name, expected_module in expected_task_modules.items():
        environment = (services.get(service_name) or {}).get('environment') or {}
        if environment.get('TESTHUB_CELERY_TASK_MODULES') != expected_module:
            violations.append(
                f'{service_name} task module mismatch: '
                f'{environment.get("TESTHUB_CELERY_TASK_MODULES")!r}'
            )

    if args.protected:
        for service_name, service in services.items():
            targets = volume_targets(service)
            if '/workspace/source-repo' in targets:
                violations.append(
                    f'protected service mounts plaintext source: {service_name}'
                )

    payload = {
        'compose_files': args.files,
        'protected': args.protected,
        'service_count': len(services),
        'status': 'failed' if violations else 'passed',
        'violations': violations,
    }
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
