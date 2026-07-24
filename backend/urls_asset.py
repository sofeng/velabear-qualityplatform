from django.urls import include, path

from .urls_base import runtime_base_patterns


urlpatterns = [
    path('api/knowledge/', include('apps.knowledge.urls')),
    *runtime_base_patterns(),
]
