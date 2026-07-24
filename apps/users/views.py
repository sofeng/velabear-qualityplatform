import logging

from django.contrib.auth import login, logout
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

from .models import PermissionItem, Role, RoleMembership, RolePermission, User
from .serializers import (
    EmailCodeLoginSerializer,
    GroupMemberMutationSerializer,
    GroupSerializer,
    LoginSerializer,
    PermissionItemSerializer,
    RoleMembershipSerializer,
    RoleMemberMutationSerializer,
    RolePermissionMutationSerializer,
    RoleSerializer,
    SendEmailCodeSerializer,
    UserAdminCreateSerializer,
    UserCreateSerializer,
    UserPasswordResetSerializer,
    UserSerializer,
)
from .email_verification import (
    generate_username_from_email,
    send_email_verification_code,
    verify_email_code,
)


class UserListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsAuthenticatedReadOnlyOrStaffWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(user.is_staff or user.is_superuser)


PERMISSION_ITEM_CREATE_CODE = 'button:manual-testcases:permissions:create'
PERMISSION_ITEM_EDIT_CODE = 'button:manual-testcases:permissions:edit'
PERMISSION_ITEM_DELETE_CODE = 'button:manual-testcases:permissions:delete'
ROLE_PERMISSION_ASSIGN_CODE = 'action:manual-testcases:permissions:assign'


class PermissionItemAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'POST':
            return user.has_permission_code(PERMISSION_ITEM_CREATE_CODE)

        if request.method in {'PUT', 'PATCH'}:
            return user.has_permission_code(PERMISSION_ITEM_EDIT_CODE)

        if request.method == 'DELETE':
            return user.has_permission_code(PERMISSION_ITEM_DELETE_CODE)

        return False


class RolePermissionAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'PUT':
            return user.has_permission_code(ROLE_PERMISSION_ASSIGN_CODE)

        return False


def build_permission_tree(permission_items):
    serialized_items = PermissionItemSerializer(permission_items, many=True).data
    item_mapping = {
        item['id']: {
            **item,
            'children': [],
        }
        for item in serialized_items
    }
    roots = []

    for item in serialized_items:
        node = item_mapping[item['id']]
        parent_id = item.get('parent')
        if parent_id and parent_id in item_mapping:
            item_mapping[parent_id]['children'].append(node)
        else:
            roots.append(node)

    return roots


def summarize_permission_items(permission_items):
    summary = {
        'module': 0,
        'menu': 0,
        'button': 0,
        'action': 0,
    }

    for permission_item in permission_items:
        if permission_item.item_type in summary:
            summary[permission_item.item_type] += 1

    return summary


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            from rest_framework.authtoken.models import Token

            token, _ = Token.objects.get_or_create(user=user)
            token_key = token.key
        except ImportError:
            token_key = f'temp_token_{user.id}'

        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token_key,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    login(request, user)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response(
        {
            'user': UserSerializer(user).data,
            'access': access_token,
            'refresh': refresh_token,
            'message': '登录成功',
        }
    )


def build_email_code_auth_response(user, *, created=False):
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'created': created,
            'message': '注册并登录成功' if created else '登录成功',
        }
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def send_email_code_view(request):
    serializer = SendEmailCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = send_email_verification_code(serializer.validated_data['email'])
    except ValueError as error:
        return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    payload = {
        'message': '验证码已发送' if result['email_sent'] else '验证码已生成（本地环境）',
        'email': result['email'],
        'email_sent': result['email_sent'],
        'delivery_configured': result.get('delivery_configured', False),
        'expires_in': result['expires_in'],
        'cooldown_seconds': result['cooldown_seconds'],
    }
    if result.get('debug_code'):
        payload['debug_code'] = result['debug_code']
    return Response(payload)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def email_code_login_view(request):
    serializer = EmailCodeLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']

    try:
        normalized_email = verify_email_code(email, code)
    except ValueError as error:
        return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=normalized_email).order_by('id').first()
    created = False

    if user is None:
        user = User.objects.create_user(
            username=generate_username_from_email(normalized_email),
            email=normalized_email,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        created = True
    elif not user.is_active:
        return Response({'error': '用户已被禁用'}, status=status.HTTP_403_FORBIDDEN)

    login(request, user)
    return build_email_code_auth_response(user, created=created)


@api_view(['POST'])
@csrf_exempt
def logout_view(request):
    if request.user.is_authenticated:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        try:
            request.user.auth_token.delete()
        except Exception:
            pass

        logout(request)

    return Response({'message': '退出成功'})


@api_view(['GET'])
def profile_view(request):
    if not request.user.is_authenticated:
        return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    pagination_class = UserListPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'department', 'position']
    ordering_fields = ['username', 'date_joined', 'created_at', 'updated_at']
    ordering = ['username']

    def get_queryset(self):
        return User.objects.all().order_by('username')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserAdminCreateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.all().order_by('username')


class UserPasswordResetView(APIView):
    """重置用户密码（仅管理员）"""
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]

    def post(self, request, pk):
        """POST /auth/users/<id>/reset_password/"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 验证权限
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': '权限不足，仅管理员可重置密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 验证输入
        serializer = UserPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 重置密码
        new_password = serializer.validated_data['password']
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # 记录日志
        logger.info(
            f"Password reset for user {user.username} (ID: {user.id}) "
            f"by {request.user.username} (ID: {request.user.id})"
        )

        return Response({
            'message': f'用户 {user.username} 的密码已重置',
            'data': {
                'user_id': user.id,
                'username': user.username,
            }
        }, status=status.HTTP_200_OK)


class PermissionItemListView(generics.ListCreateAPIView):
    permission_classes = [PermissionItemAccessPermission]
    serializer_class = PermissionItemSerializer
    pagination_class = UserListPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['item_type', 'is_active', 'parent']
    search_fields = ['name', 'code', 'route_path', 'description']
    ordering_fields = ['sort_order', 'name', 'id', 'item_type']
    ordering = ['sort_order', 'name', 'id']

    def get_queryset(self):
        queryset = PermissionItem.objects.select_related('parent').all().order_by('sort_order', 'name', 'id')
        parent_id = self.request.query_params.get('parent_id')
        if parent_id not in (None, '', 'null'):
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def list(self, request, *args, **kwargs):
        if str(request.query_params.get('tree', '')).lower() in {'1', 'true', 'yes'}:
            queryset = self.filter_queryset(self.get_queryset())
            return Response(build_permission_tree(queryset))
        return super().list(request, *args, **kwargs)


class PermissionItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PermissionItemAccessPermission]
    serializer_class = PermissionItemSerializer

    def get_queryset(self):
        return PermissionItem.objects.select_related('parent').all().order_by('sort_order', 'name', 'id')


class GroupListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    serializer_class = GroupSerializer
    pagination_class = UserListPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['id', 'name']
    ordering = ['name']

    def get_queryset(self):
        return Group.objects.all().prefetch_related('user_set').order_by('name').distinct()


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.all().prefetch_related('user_set').order_by('name')


class GroupMemberListCreateView(APIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]

    def get_group(self, group_id):
        return get_object_or_404(Group.objects.all().prefetch_related('user_set'), pk=group_id)

    def get(self, request, group_id):
        group = self.get_group(group_id)
        serializer = UserSerializer(group.user_set.all().order_by('username'), many=True)
        return Response(serializer.data)

    def post(self, request, group_id):
        group = self.get_group(group_id)
        serializer = GroupMemberMutationSerializer(
            data=request.data,
            context={'group': group, 'action': 'create'},
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.validated_data['user']
        group.user_set.add(member)
        return Response(
            {
                'message': '组员已添加',
                'member': UserSerializer(member).data,
            },
            status=status.HTTP_201_CREATED,
        )


class GroupMemberDetailView(APIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]

    def get_group(self, group_id):
        return get_object_or_404(Group.objects.all().prefetch_related('user_set'), pk=group_id)

    def get_member(self, group, member_id):
        return get_object_or_404(group.user_set.all(), pk=member_id)

    def patch(self, request, group_id, member_id):
        group = self.get_group(group_id)
        current_member = self.get_member(group, member_id)
        serializer = GroupMemberMutationSerializer(
            data=request.data,
            context={
                'group': group,
                'action': 'update',
                'current_member_id': current_member.id,
            },
        )
        serializer.is_valid(raise_exception=True)
        next_member = serializer.validated_data['user']

        if next_member.id != current_member.id:
            group.user_set.remove(current_member)
            group.user_set.add(next_member)

        return Response(
            {
                'message': '组员已更新',
                'member': UserSerializer(next_member).data,
            }
        )

    def delete(self, request, group_id, member_id):
        group = self.get_group(group_id)
        member = self.get_member(group, member_id)
        group.user_set.remove(member)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    serializer_class = RoleSerializer
    pagination_class = UserListPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'members__username', 'members__email', 'members__first_name', 'members__last_name']
    ordering_fields = ['id', 'name', 'created_at', 'updated_at']
    ordering = ['name']

    def get_queryset(self):
        return Role.objects.all().prefetch_related('members', 'role_memberships__user').order_by('name', 'id').distinct()


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]
    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.all().prefetch_related('members', 'role_memberships__user').order_by('name', 'id')


class RoleMemberListCreateView(APIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]

    def get_role(self, role_id):
        return get_object_or_404(Role.objects.all().prefetch_related('members', 'role_memberships__user'), pk=role_id)

    def get_memberships(self, role):
        memberships = list(role.role_memberships.select_related('user').all())
        membership_user_ids = {item.user_id for item in memberships}
        fallback_users = [
            user
            for user in role.members.all()
            if user.id not in membership_user_ids
        ]

        memberships.extend(RoleMembership(role=role, user=user, tags=[]) for user in fallback_users)
        return sorted(memberships, key=lambda item: (str(item.user.username or ''), item.user.id))

    def get(self, request, role_id):
        role = self.get_role(role_id)
        serializer = RoleMembershipSerializer(self.get_memberships(role), many=True)
        return Response(serializer.data)

    def post(self, request, role_id):
        role = self.get_role(role_id)
        serializer = RoleMemberMutationSerializer(
            data=request.data,
            context={'role': role, 'action': 'create'},
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.validated_data['user']
        tags = serializer.validated_data.get('tags', [])
        role.members.add(member)
        membership, _ = role.role_memberships.update_or_create(
            user=member,
            defaults={'tags': tags},
        )
        return Response(
            {
                'message': '角色成员已添加',
                'member': RoleMembershipSerializer(membership).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RoleMemberDetailView(APIView):
    permission_classes = [IsAuthenticatedReadOnlyOrStaffWrite]

    def get_role(self, role_id):
        return get_object_or_404(Role.objects.all().prefetch_related('members', 'role_memberships__user'), pk=role_id)

    def get_member(self, role, member_id):
        return get_object_or_404(role.role_memberships.select_related('user'), user_id=member_id)

    def patch(self, request, role_id, member_id):
        role = self.get_role(role_id)
        current_membership = self.get_member(role, member_id)
        current_member = current_membership.user
        serializer = RoleMemberMutationSerializer(
            data=request.data,
            context={
                'role': role,
                'action': 'update',
                'current_member_id': current_member.id,
            },
        )
        serializer.is_valid(raise_exception=True)
        next_member = serializer.validated_data['user']
        tags = serializer.validated_data.get('tags', [])

        if next_member.id != current_member.id:
            role.members.remove(current_member)
            role.members.add(next_member)
            current_membership.delete()
            membership, _ = role.role_memberships.update_or_create(
                user=next_member,
                defaults={'tags': tags},
            )
        else:
            current_membership.tags = tags
            current_membership.save(update_fields=['tags', 'updated_at'])
            membership = current_membership

        return Response(
            {
                'message': '角色成员已更新',
                'member': RoleMembershipSerializer(membership).data,
            }
        )

    def delete(self, request, role_id, member_id):
        role = self.get_role(role_id)
        membership = self.get_member(role, member_id)
        role.members.remove(membership.user)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolePermissionView(APIView):
    permission_classes = [RolePermissionAccessPermission]

    def get_role(self, role_id):
        return get_object_or_404(
            Role.objects.all().prefetch_related('role_permissions__permission_item'),
            pk=role_id,
        )

    def get(self, request, role_id):
        role = self.get_role(role_id)
        permission_items = [
            role_permission.permission_item
            for role_permission in role.role_permissions.all()
            if role_permission.permission_item_id
        ]
        permission_items = sorted(permission_items, key=lambda item: (item.sort_order, str(item.name or ''), item.id))

        return Response(
            {
                'role': {
                    'id': role.id,
                    'name': role.name,
                },
                'permission_ids': [item.id for item in permission_items],
                'permissions': PermissionItemSerializer(permission_items, many=True).data,
                'summary': summarize_permission_items(permission_items),
            }
        )

    @transaction.atomic
    def put(self, request, role_id):
        role = self.get_role(role_id)
        serializer = RolePermissionMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_items = serializer.validated_data['permission_items']
        desired_permission_ids = [item.id for item in permission_items]

        RolePermission.objects.filter(role=role).exclude(permission_item_id__in=desired_permission_ids).delete()
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission_item=permission_item)
                for permission_item in permission_items
            ],
            ignore_conflicts=True,
        )

        refreshed_permission_items = list(
            PermissionItem.objects.filter(role_permissions__role=role).order_by('sort_order', 'name', 'id').distinct()
        )

        return Response(
            {
                'message': '角色权限已更新',
                'role': {
                    'id': role.id,
                    'name': role.name,
                },
                'permission_ids': [item.id for item in refreshed_permission_items],
                'permissions': PermissionItemSerializer(refreshed_permission_items, many=True).data,
                'summary': summarize_permission_items(refreshed_permission_items),
            }
        )
