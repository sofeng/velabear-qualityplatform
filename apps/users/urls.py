from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import test_views, views


urlpatterns = [
    path('me/', views.get_current_user, name='get_current_user'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('test-register/', test_views.test_register, name='test-register'),
    path('login/', views.login_view, name='login'),
    path('send-email-code/', views.send_email_code_view, name='send-email-code'),
    path('email-code-login/', views.email_code_login_view, name='email-code-login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/reset_password/', views.UserPasswordResetView.as_view(), name='user-reset-password'),
    path('permission-items/', views.PermissionItemListView.as_view(), name='permission-item-list'),
    path('permission-items/<int:pk>/', views.PermissionItemDetailView.as_view(), name='permission-item-detail'),
    path('groups/', views.GroupListView.as_view(), name='group-list'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:group_id>/members/', views.GroupMemberListCreateView.as_view(), name='group-member-list'),
    path('groups/<int:group_id>/members/<int:member_id>/', views.GroupMemberDetailView.as_view(), name='group-member-detail'),
    path('roles/', views.RoleListView.as_view(), name='role-list'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role-detail'),
    path('roles/<int:role_id>/members/', views.RoleMemberListCreateView.as_view(), name='role-member-list'),
    path('roles/<int:role_id>/members/<int:member_id>/', views.RoleMemberDetailView.as_view(), name='role-member-detail'),
    path('roles/<int:role_id>/permissions/', views.RolePermissionView.as_view(), name='role-permission'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
