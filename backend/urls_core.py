from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .urls_base import runtime_base_patterns


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/testcases/', include('apps.testcases.urls_core')),
    path('api/defects/', include('apps.defects.urls')),
    path('api/testsuites/', include('apps.testsuites.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/reviews/', include('apps.reviews.urls')),
    path('api/versions/', include('apps.versions.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/quality-analysis/', include('apps.quality_analysis.urls')),
    path('api/workflow/', include('apps.workflow.urls')),
]

if getattr(settings, 'ENABLE_API_DOCS', False):
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]

urlpatterns += runtime_base_patterns()
