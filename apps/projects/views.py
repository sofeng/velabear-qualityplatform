from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import UserSerializer
from apps.knowledge.services import ensure_project_knowledge_space

from .models import Project, ProjectEnvironment, ProjectMember
from .serializers import (
    ProjectCreateSerializer,
    ProjectEnvironmentSerializer,
    ProjectMemberMutationSerializer,
    ProjectSerializer,
)


PROJECT_MEMBER_DEFAULT_ROLE = ProjectMember._meta.get_field('role').default


def sync_default_project(project):
    if not project.is_default:
        return

    Project.objects.exclude(id=project.id).update(is_default=False)


def serialize_project_member(project, user, membership=None):
    user_data = UserSerializer(user).data
    joined_at = membership.joined_at if membership else project.created_at
    is_owner = membership is None

    return {
        **user_data,
        'id': user.id,
        'user_id': user.id,
        'membership_id': membership.id if membership else None,
        'role': 'owner' if is_owner else membership.role,
        'is_owner': is_owner,
        'joined_at': joined_at.isoformat() if joined_at else None,
    }


def list_project_members(project):
    members = [serialize_project_member(project, project.owner)]
    project_members = project.projectmember_set.select_related('user').order_by('user__username', 'user_id')
    members.extend(serialize_project_member(project, item.user, item) for item in project_members)
    return members


def can_manage_project_members(user, project):
    if not user or not user.is_authenticated:
        return False

    return bool(user.is_staff or user.is_superuser or project.owner_id == user.id)


def sync_default_project_environment(environment):
    if not environment.is_default:
        return

    ProjectEnvironment.objects.filter(project=environment.project).exclude(id=environment.id).update(is_default=False)


class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.select_related('owner').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'is_default']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_queryset(self):
        return Project.objects.select_related('owner').all()

    def perform_create(self, serializer):
        instance = serializer.save()
        sync_default_project(instance)
        ensure_project_knowledge_space(instance, user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_projects(request):
    """获取所有项目列表，用于下拉选择等场景"""

    projects = Project.objects.all().values('id', 'name', 'description', 'status', 'is_default').order_by('-is_default', 'name', 'id')
    return Response(list(projects))


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.select_related('owner').prefetch_related('projectmember_set__user', 'environments').all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        instance = serializer.save()
        sync_default_project(instance)


class ProjectMemberListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self, project_id):
        return get_object_or_404(Project.objects.select_related('owner'), pk=project_id)

    def get(self, request, project_id):
        project = self.get_project(project_id)
        return Response(list_project_members(project))


class ProjectMemberCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self, project_id):
        return get_object_or_404(Project.objects.select_related('owner'), pk=project_id)

    def post(self, request, project_id):
        project = self.get_project(project_id)
        if not can_manage_project_members(request.user, project):
            return Response({'error': '无权限维护项目成员'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectMemberMutationSerializer(
            data=request.data,
            context={'project': project, 'action': 'create'},
        )
        serializer.is_valid(raise_exception=True)

        membership = ProjectMember.objects.create(
            project=project,
            user=serializer.validated_data['user'],
            role=serializer.validated_data.get('role') or PROJECT_MEMBER_DEFAULT_ROLE,
        )

        return Response(
            {
                'message': '项目成员已添加',
                'member': serialize_project_member(project, membership.user, membership),
            },
            status=status.HTTP_201_CREATED,
        )


class ProjectMemberDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self, project_id):
        return get_object_or_404(Project.objects.select_related('owner'), pk=project_id)

    def get_member(self, project, member_id):
        member_queryset = ProjectMember.objects.select_related('user').filter(project=project)
        member = member_queryset.filter(user_id=member_id).first()
        if member:
            return member
        return get_object_or_404(member_queryset, pk=member_id)

    def patch(self, request, project_id, member_id):
        project = self.get_project(project_id)
        if not can_manage_project_members(request.user, project):
            return Response({'error': '无权限维护项目成员'}, status=status.HTTP_403_FORBIDDEN)

        current_member = self.get_member(project, member_id)
        serializer = ProjectMemberMutationSerializer(
            data=request.data,
            context={
                'project': project,
                'action': 'update',
                'current_member_id': current_member.user_id,
            },
        )
        serializer.is_valid(raise_exception=True)

        next_user = serializer.validated_data['user']
        next_role = serializer.validated_data.get('role') or current_member.role or PROJECT_MEMBER_DEFAULT_ROLE

        if next_user.id != current_member.user_id:
            current_member.delete()
            membership = ProjectMember.objects.create(
                project=project,
                user=next_user,
                role=next_role,
            )
        else:
            if current_member.role != next_role:
                current_member.role = next_role
                current_member.save(update_fields=['role'])
            membership = current_member

        return Response(
            {
                'message': '项目成员已更新',
                'member': serialize_project_member(project, membership.user, membership),
            }
        )

    def delete(self, request, project_id, member_id):
        project = self.get_project(project_id)
        if not can_manage_project_members(request.user, project):
            return Response({'error': '无权限维护项目成员'}, status=status.HTTP_403_FORBIDDEN)

        member = self.get_member(project, member_id)
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectEnvironmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        return ProjectEnvironment.objects.select_related('project').filter(project_id=project_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            context['project'] = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return context

    def perform_create(self, serializer):
        instance = serializer.save()
        sync_default_project_environment(instance)


class ProjectEnvironmentViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'is_default']
    search_fields = ['name', 'base_url', 'account', 'description', 'project__name']
    ordering_fields = ['project__name', 'name', 'created_at', 'updated_at', 'is_default']
    ordering = ['project__name', '-is_default', 'name', 'id']

    def apply_contains_filter(self, queryset, param_name, lookup):
        value = (self.request.query_params.get(param_name) or '').strip()
        if not value:
            return queryset
        return queryset.filter(**{f'{lookup}__icontains': value})

    def apply_has_password_filter(self, queryset):
        raw_value = (self.request.query_params.get('has_password') or '').strip().lower()
        if raw_value in {'true', '1', 'yes', 'y'}:
            return queryset.exclude(password_encrypted='')
        if raw_value in {'false', '0', 'no', 'n'}:
            return queryset.filter(password_encrypted='')
        return queryset

    def apply_updated_at_filter(self, queryset):
        updated_at = (self.request.query_params.get('updated_at') or '').strip()
        updated_at_start = (self.request.query_params.get('updated_at_start') or '').strip()
        updated_at_end = (self.request.query_params.get('updated_at_end') or '').strip()
        if updated_at:
            queryset = queryset.filter(updated_at__date=updated_at)
        if updated_at_start:
            queryset = queryset.filter(updated_at__date__gte=updated_at_start)
        if updated_at_end:
            queryset = queryset.filter(updated_at__date__lte=updated_at_end)
        return queryset

    def get_queryset(self):
        queryset = ProjectEnvironment.objects.select_related('project').all()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        queryset = self.apply_contains_filter(queryset, 'project_name', 'project__name')
        queryset = self.apply_contains_filter(queryset, 'name', 'name')
        queryset = self.apply_contains_filter(queryset, 'base_url', 'base_url')
        queryset = self.apply_contains_filter(queryset, 'account', 'account')
        queryset = self.apply_contains_filter(queryset, 'description', 'description')
        queryset = self.apply_has_password_filter(queryset)
        queryset = self.apply_updated_at_filter(queryset)

        keyword = (self.request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(base_url__icontains=keyword) |
                Q(account__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(project__name__icontains=keyword)
            )

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        sync_default_project_environment(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        sync_default_project_environment(instance)
