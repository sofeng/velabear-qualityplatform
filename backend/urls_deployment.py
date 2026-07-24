from django.urls import include, path

from .urls_base import runtime_base_patterns


urlpatterns = [
    path('api/deployments/', include('apps.deployments.urls')),
    *runtime_base_patterns(),
]
