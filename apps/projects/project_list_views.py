from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Project


def build_project_count_map(queryset, count_field='id'):
    return {
        item['project_id']: item['total']
        for item in queryset.values('project_id').annotate(total=Count(count_field, distinct=True))
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_projects_list(request):
    """Return all projects for workspace selectors with lightweight counts."""

    projects = list(
        Project.objects
        .values('id', 'name', 'status', 'is_default')
        .order_by('-is_default', 'name', 'id')
    )

    project_ids = [item['id'] for item in projects]
    if project_ids:
        from apps.testcases.models import ManualTestCaseCategory, ManualTestCaseMindmap
        from apps.versions.models import Version

        version_count_map = build_project_count_map(
            Version.projects.through.objects.filter(project_id__in=project_ids),
            'version_id',
        )
        manual_category_count_map = build_project_count_map(
            ManualTestCaseCategory.objects.filter(project_id__in=project_ids),
        )
        mindmap_count_map = build_project_count_map(
            ManualTestCaseMindmap.objects.filter(
                project_id__in=project_ids,
                mindmap_scope=ManualTestCaseMindmap.SCOPE_TESTING,
            ),
        )

        for project in projects:
            project_id = project['id']
            project['version_count'] = version_count_map.get(project_id, 0)
            project['manual_category_count'] = manual_category_count_map.get(project_id, 0)
            project['mindmap_count'] = mindmap_count_map.get(project_id, 0)

    return Response({'results': projects})
