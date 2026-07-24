import re

from django.conf import settings
from django.urls import path, re_path
from django.views.static import serve

from .runtime_health import runtime_health


def runtime_base_patterns():
    patterns = [path('internal/runtime-health/', runtime_health, name='runtime-health')]
    if settings.MEDIA_URL:
        patterns.append(
            re_path(
                r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')),
                serve,
                {'document_root': settings.MEDIA_ROOT},
            )
        )
    return patterns
