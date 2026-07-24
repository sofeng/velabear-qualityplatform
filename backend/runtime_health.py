import os

from django.http import JsonResponse


def runtime_health(request):
    return JsonResponse(
        {
            'status': 'ok',
            'runtime_role': os.environ.get('TESTHUB_RUNTIME_ROLE', 'core'),
        }
    )
