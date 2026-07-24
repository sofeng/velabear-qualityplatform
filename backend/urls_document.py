from django.urls import include, path

from apps.requirement_analysis.internal_views import extract_document_text_internal

from .urls_base import runtime_base_patterns


urlpatterns = [
    path(
        'internal/document-extraction/',
        extract_document_text_internal,
        name='internal-document-extraction',
    ),
    path('api/requirement-analysis/', include('apps.requirement_analysis.urls')),
    *runtime_base_patterns(),
]
