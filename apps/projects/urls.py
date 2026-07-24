from django.urls import path
from . import views, project_list_views

urlpatterns = [
    path('', views.ProjectListCreateView.as_view(), name='project-list'),
    path('all/', views.get_all_projects, name='all-projects'),
    path(
        'environments/',
        views.ProjectEnvironmentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='project-environment-list',
    ),
    path(
        'environments/<int:pk>/',
        views.ProjectEnvironmentViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='project-environment-detail',
    ),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:project_id>/members/', views.ProjectMemberListView.as_view(), name='get-project-members'),
    path('<int:project_id>/members/add/', views.ProjectMemberCreateView.as_view(), name='add-member'),
    path('<int:project_id>/members/<int:member_id>/', views.ProjectMemberDetailView.as_view(), name='project-member-detail'),
    path('<int:project_id>/environments/', views.ProjectEnvironmentListCreateView.as_view(), name='environment-list'),
    path('list/', project_list_views.user_projects_list, name='user-projects-list'),
]
