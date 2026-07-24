from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import PermissionItem, Role, RoleMembership, User, UserProfile


def resolve_users_by_ids(user_ids):
    if not user_ids:
        return []

    users = list(User.objects.filter(id__in=user_ids).order_by('username', 'id'))
    user_map = {user.id: user for user in users}
    missing_ids = [user_id for user_id in user_ids if user_id not in user_map]
    if missing_ids:
        raise serializers.ValidationError(
            {'member_ids': f'以下成员不存在：{", ".join(str(item) for item in missing_ids)}'}
        )

    return [user_map[user_id] for user_id in user_ids]


def resolve_permission_items_by_ids(permission_ids):
    if not permission_ids:
        return []

    permission_items = list(
        PermissionItem.objects.filter(id__in=permission_ids).select_related('parent').order_by('sort_order', 'name', 'id')
    )
    permission_map = {permission_item.id: permission_item for permission_item in permission_items}
    missing_ids = [permission_id for permission_id in permission_ids if permission_id not in permission_map]
    if missing_ids:
        raise serializers.ValidationError(
            {'permission_ids': f'以下权限项不存在：{", ".join(str(item) for item in missing_ids)}'}
        )

    return [permission_map[permission_id] for permission_id in permission_ids]


def normalize_text_list(values):
    normalized_items = []
    seen_items = set()

    for item in values or []:
        text = str(item or '').strip()
        if not text or text in seen_items:
            continue
        seen_items.add(text)
        normalized_items.append(text)

    return normalized_items


def sync_role_memberships(role, users):
    desired_user_ids = []

    for user in users:
        desired_user_ids.append(user.id)
        RoleMembership.objects.get_or_create(
            role=role,
            user=user,
            defaults={'tags': []},
        )

    RoleMembership.objects.filter(role=role).exclude(user_id__in=desired_user_ids).delete()


class UserSimpleSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'avatar', 'full_name')


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    effective_permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'avatar',
            'phone',
            'department',
            'position',
            'is_active',
            'is_staff',
            'is_superuser',
            'effective_permission_codes',
            'date_joined',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']

    def get_effective_permission_codes(self, obj):
        return obj.get_effective_permission_codes()


class PermissionItemSerializer(serializers.ModelSerializer):
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = PermissionItem
        fields = [
            'id',
            'name',
            'code',
            'item_type',
            'item_type_display',
            'parent',
            'parent_name',
            'route_path',
            'sort_order',
            'is_active',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'item_type_display', 'parent_name', 'created_at', 'updated_at']

    def validate_name(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入权限名称')
        return normalized

    def validate_code(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入权限编码')
        return normalized

    def validate_route_path(self, value):
        return str(value or '').strip()

    def validate_description(self, value):
        return str(value or '').strip()

    def validate(self, attrs):
        item_type = attrs.get('item_type', self.instance.item_type if self.instance else None)
        parent = attrs.get('parent', self.instance.parent if self.instance else None)
        instance_id = self.instance.id if self.instance else None

        if item_type == 'module' and parent is not None:
            raise serializers.ValidationError({'parent': '模块类型权限不能设置父级权限'})

        if parent is not None:
            if instance_id and parent.id == instance_id:
                raise serializers.ValidationError({'parent': '父级权限不能选择当前权限项'})

            ancestor = parent
            while ancestor is not None:
                if instance_id and ancestor.id == instance_id:
                    raise serializers.ValidationError({'parent': '父级权限不能选择当前权限项的下级节点'})
                ancestor = ancestor.parent

        return attrs


class RoleMembershipSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True, allow_blank=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True, allow_blank=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True, allow_blank=True, allow_null=True)
    department = serializers.CharField(source='user.department', read_only=True, allow_blank=True, allow_null=True)
    position = serializers.CharField(source='user.position', read_only=True, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    is_staff = serializers.BooleanField(source='user.is_staff', read_only=True)
    is_superuser = serializers.BooleanField(source='user.is_superuser', read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = RoleMembership
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'avatar',
            'phone',
            'department',
            'position',
            'is_active',
            'is_staff',
            'is_superuser',
            'tags',
        ]

    def get_tags(self, obj):
        return normalize_text_list(obj.tags)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'phone',
            'department',
            'position',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError('两次输入的密码不一致')
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        return User.objects.create_user(**validated_data)


class UserAdminCreateSerializer(UserCreateSerializer):
    is_active = serializers.BooleanField(required=False, default=True)
    is_staff = serializers.BooleanField(required=False, default=False)
    is_superuser = serializers.BooleanField(required=False, default=False)

    class Meta(UserCreateSerializer.Meta):
        fields = UserCreateSerializer.Meta.fields + [
            'is_active',
            'is_staff',
            'is_superuser',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get('is_superuser'):
            attrs['is_staff'] = True
        return attrs


class UserPasswordResetSerializer(serializers.Serializer):
    """序列化器：管理员重置用户密码"""
    password = serializers.CharField(write_only=True, min_length=6, max_length=128)
    password_confirm = serializers.CharField(write_only=True, max_length=128)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '两次输入的密码不一致'})
        return attrs

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError('密码长度不能少于 6 位')
        return value


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'members', 'member_count', 'member_ids']
        read_only_fields = ['id', 'members', 'member_count']

    def validate_name(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入组别名称')
        return normalized

    def validate_member_ids(self, value):
        normalized_ids = []
        seen_ids = set()
        for item in value:
            member_id = int(item)
            if member_id in seen_ids:
                continue
            seen_ids.add(member_id)
            normalized_ids.append(member_id)
        return normalized_ids

    def _get_ordered_members(self, obj):
        return sorted(obj.user_set.all(), key=lambda item: (str(item.username or ''), item.id))

    def get_members(self, obj):
        return UserSimpleSerializer(self._get_ordered_members(obj), many=True).data

    def get_member_count(self, obj):
        return len(self._get_ordered_members(obj))

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        group = Group.objects.create(**validated_data)
        if member_ids:
            group.user_set.set(resolve_users_by_ids(member_ids))
        return group

    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        if member_ids is not None:
            instance.user_set.set(resolve_users_by_ids(member_ids))
        return instance


class GroupMemberMutationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        group = self.context['group']
        action = self.context.get('action')
        current_member_id = self.context.get('current_member_id')
        user_id = attrs['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({'user_id': '指定成员不存在'}) from exc

        if action == 'create' and group.user_set.filter(id=user.id).exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前组别中'})

        if action == 'update' and user.id != current_member_id and group.user_set.filter(id=user.id).exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前组别中'})

        attrs['user'] = user
        return attrs


class RoleSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'members', 'member_count', 'member_ids', 'created_at', 'updated_at']
        read_only_fields = ['id', 'members', 'member_count', 'created_at', 'updated_at']

    def validate_name(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('请输入角色名称')
        return normalized

    def validate_member_ids(self, value):
        normalized_ids = []
        seen_ids = set()
        for item in value:
            member_id = int(item)
            if member_id in seen_ids:
                continue
            seen_ids.add(member_id)
            normalized_ids.append(member_id)
        return normalized_ids

    def _get_ordered_memberships(self, obj):
        memberships = list(obj.role_memberships.select_related('user').all())
        membership_user_ids = {item.user_id for item in memberships}
        fallback_users = [
            user
            for user in obj.members.all()
            if user.id not in membership_user_ids
        ]

        memberships.extend(RoleMembership(role=obj, user=user, tags=[]) for user in fallback_users)
        return sorted(memberships, key=lambda item: (str(item.user.username or ''), item.user.id))

    def get_members(self, obj):
        return RoleMembershipSerializer(self._get_ordered_memberships(obj), many=True).data

    def get_member_count(self, obj):
        return len(self._get_ordered_memberships(obj))

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        role = Role.objects.create(**validated_data)
        if member_ids:
            members = resolve_users_by_ids(member_ids)
            role.members.set(members)
            sync_role_memberships(role, members)
        return role

    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        if member_ids is not None:
            members = resolve_users_by_ids(member_ids)
            instance.members.set(members)
            sync_role_memberships(instance, members)
        return instance


class RolePermissionMutationSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )

    def validate_permission_ids(self, value):
        normalized_ids = []
        seen_ids = set()
        for item in value:
            permission_id = int(item)
            if permission_id in seen_ids:
                continue
            seen_ids.add(permission_id)
            normalized_ids.append(permission_id)
        return normalized_ids

    def validate(self, attrs):
        permission_ids = attrs.get('permission_ids', [])
        attrs['permission_items'] = resolve_permission_items_by_ids(permission_ids)
        return attrs


class RoleMemberMutationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        required=False,
        default=list,
    )

    def validate_tags(self, value):
        return normalize_text_list(value)

    def validate(self, attrs):
        role = self.context['role']
        action = self.context.get('action')
        current_member_id = self.context.get('current_member_id')
        user_id = attrs['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({'user_id': '指定角色成员不存在'}) from exc

        if action == 'create' and role.members.filter(id=user.id).exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前角色中'})

        if action == 'update' and user.id != current_member_id and role.members.filter(id=user.id).exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前角色中'})

        attrs['user'] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError('用户名和密码不能为空')

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError('用户名或密码错误')
        if not user.is_active:
            raise serializers.ValidationError('用户已被禁用')

        attrs['user'] = user
        return attrs


class SendEmailCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailCodeLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=10)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
