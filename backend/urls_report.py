from django.urls import include, path

from .urls_base import runtime_base_patterns


urlpatterns = [
    path('api/', include('apps.api_testing.urls')),
    path('api/testcases/', include('apps.testcases.urls_report')),
    *runtime_base_patterns(),
]
