from rest_framework import serializers

from apps.core.plaintext_secrets import encrypt_password
from apps.users.models import User
from apps.users.serializers import UserSerializer

from .models import Project, ProjectEnvironment, ProjectMember


class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name', 'is_default')


class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), required=False)
    project_name = serializers.CharField(source='project.name', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = ProjectEnvironment
        fields = [
            'id',
            'project',
            'project_name',
            'name',
            'base_url',
            'account',
            'password',
            'has_password',
            'description',
            'variables',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'project_name', 'has_password', 'created_at', 'updated_at']

    def get_has_password(self, obj):
        return bool(obj.password_encrypted)

    def validate(self, attrs):
        context_project = self.context.get('project')
        if context_project and not self.instance:
            attrs['project'] = context_project

        project = attrs.get('project') or context_project or getattr(self.instance, 'project', None)
        name = (attrs.get('name', getattr(self.instance, 'name', '')) or '').strip()
        if name:
            attrs['name'] = name
        if not project and not self.instance:
            raise serializers.ValidationError({'project': '请选择项目'})
        if project and not attrs.get('project') and not self.instance:
            attrs['project'] = project
        if not project or not name:
            return attrs

        queryset = ProjectEnvironment.objects.filter(project=project, name=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError({'name': '同一项目下环境名称不能重复'})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', '')
        if password:
            validated_data['password_encrypted'] = encrypt_password(password)
        instance = super().create(validated_data)
        if instance.is_default:
            ProjectEnvironment.objects.filter(project=instance.project).exclude(pk=instance.pk).update(is_default=False)
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            validated_data['password_encrypted'] = encrypt_password(password)
        instance = super().update(instance, validated_data)
        if instance.is_default:
            ProjectEnvironment.objects.filter(project=instance.project).exclude(pk=instance.pk).update(is_default=False)
        return instance


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = ProjectMemberSerializer(source='projectmember_set', many=True, read_only=True)
    environments = ProjectEnvironmentSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'status',
            'is_default',
            'owner',
            'members',
            'environments',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'is_default']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class ProjectMemberMutationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(
        choices=[choice[0] for choice in ProjectMember.ROLE_CHOICES],
        required=False,
    )

    def validate(self, attrs):
        project = self.context['project']
        action = self.context.get('action')
        current_member_id = self.context.get('current_member_id')
        user_id = attrs['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({'user_id': '指定成员不存在'}) from exc

        if project.owner_id == user.id:
            raise serializers.ValidationError({'user_id': '项目负责人已默认在成员列表中，无需重复添加'})

        existing_member = ProjectMember.objects.filter(project=project, user_id=user.id)
        if action == 'create' and existing_member.exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前项目中'})

        if action == 'update' and user.id != current_member_id and existing_member.exists():
            raise serializers.ValidationError({'user_id': '该成员已在当前项目中'})

        attrs['user'] = user
        return attrs
