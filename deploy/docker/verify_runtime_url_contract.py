import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Verify one TestHub runtime URL contract.')
    parser.add_argument('--urlconf', required=True)
    parser.add_argument('--positive', action='append', default=[])
    parser.add_argument('--negative', action='append', default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    app_root = Path(os.environ.get('TESTHUB_APP_ROOT', '/app')).resolve()
    if app_root.is_dir():
        sys.path.insert(0, str(app_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_container')
    os.environ['DJANGO_ROOT_URLCONF'] = args.urlconf

    import django

    django.setup()

    from django.urls import Resolver404, resolve

    violations = []
    resolved = {}
    for path in args.positive:
        try:
            match = resolve(path)
            resolved[path] = match.view_name or str(match.func)
        except Resolver404:
            violations.append(f'expected route is missing: {path}')

    for path in args.negative:
        try:
            match = resolve(path)
        except Resolver404:
            continue
        violations.append(
            f'forbidden route is exposed: {path} -> {match.view_name or match.func}'
        )

    payload = {
        'urlconf': args.urlconf,
        'status': 'failed' if violations else 'passed',
        'resolved': resolved,
        'violations': violations,
    }
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
