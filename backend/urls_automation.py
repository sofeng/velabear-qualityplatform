from django.urls import include, path

from .urls_base import runtime_base_patterns


urlpatterns = [
    path('api/testcases/', include('apps.testcases.urls_automation')),
    path('api/ui-automation/', include('apps.ui_automation.urls')),
    path('api/executions/', include('apps.executions.urls')),
    *runtime_base_patterns(),
]
