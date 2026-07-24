from rest_framework import serializers
from .models import (
    DevSelfTestRecord,
    TestCase,
    TestCaseStep,
    TestCaseAttachment,
    TestCaseComment,
    ManualTestCaseMindmap,
    ManualTestCaseCategory,
)
from .mindmap_node_utils import iter_mindmap_target_nodes
from apps.quality_analysis.models import JiraRequirementRecord
from apps.users.group_utils import normalize_existing_group_name
from apps.users.models import User
from apps.users.serializers import UserSerializer
from apps.versions.serializers import VersionSimpleSerializer

VALID_MINDMAP_NODE_TYPES = {'module', 'case', 'requirement', 'page', 'function', 'testpoint'}
DEFAULT_MINDMAP_DATA = {
    'root': {
        'data': {
            'text': '新建脑图',
            'nodeType': 'module',
        },
        'children': [],
    },
    'template': 'right',
    'theme': 'fresh-blue',
    'version': '1.4.43',
}


def parse_powershell_object_string(value):
    text = str(value or '').strip()
    if not text.startswith('@{') or not text.endswith('}'):
        return None

    parsed = {}
    for part in text[2:-1].split(';'):
        if '=' not in part:
            continue
        key, raw_value = part.split('=', 1)
        key = key.strip()
        if key:
            parsed[key] = raw_value.strip()
    return parsed or None


def normalize_mindmap_node_data(value, fallback_text='未命名节点'):
    data = value
    if isinstance(data, str):
        data = parse_powershell_object_string(data) or {'text': data}
    if not isinstance(data, dict):
        data = {}

    normalized = dict(data)
    text = str(normalized.get('text') or fallback_text or '未命名节点').strip()
    normalized['text'] = text or '未命名节点'

    node_type = normalized.get('nodeType')
    if node_type and node_type not in VALID_MINDMAP_NODE_TYPES:
        normalized['nodeType'] = 'module'

    resource = normalized.get('resource')
    if isinstance(resource, list):
        normalized['resource'] = [str(item).strip() for item in resource if str(item or '').strip()]

    return normalized


def normalize_mindmap_node(node, fallback_text='未命名节点'):
    if isinstance(node, str):
        parsed_data = parse_powershell_object_string(node)
        return {
            'data': normalize_mindmap_node_data(parsed_data or {'text': node}, fallback_text),
            'children': [],
        }

    source = dict(node) if isinstance(node, dict) else {}
    raw_children = source.get('children')
    children = [
        normalize_mindmap_node(child)
        for child in (raw_children if isinstance(raw_children, list) else [])
    ]
    children = [child for child in children if str(child.get('data', {}).get('text') or '').strip()]
    source['data'] = normalize_mindmap_node_data(source.get('data'), fallback_text)
    source['children'] = children
    return source


def normalize_mindmap_data(value):
    source = dict(value) if isinstance(value, dict) else {}
    root = normalize_mindmap_node(source.get('root'), '新建脑图')
    root_data = root.setdefault('data', {})
    root_data['nodeType'] = root_data.get('nodeType') or 'module'
    source['root'] = root
    source.setdefault('template', DEFAULT_MINDMAP_DATA['template'])
    source.setdefault('theme', DEFAULT_MINDMAP_DATA['theme'])
    source.setdefault('version', DEFAULT_MINDMAP_DATA['version'])
    return source


def count_mindmap_nodes(node):
    if not isinstance(node, dict):
        return 0
    children = node.get('children')
    return 1 + sum(count_mindmap_nodes(child) for child in (children if isinstance(children, list) else []))


def count_mindmap_descendants(mindmap_data):
    if not isinstance(mindmap_data, dict):
        return 0
    return max(0, count_mindmap_nodes(mindmap_data.get('root')) - 1)


class TestCaseStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseStep
        fields = '__all__'

class TestCaseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseAttachment
        fields = '__all__'

class TestCaseCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseComment
        fields = '__all__'

class ProjectSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


STATUS_COUNT_KEYS = ('not_run', 'pass', 'fail', 'block', 'not_test')


def create_empty_status_counts():
    return {key: 0 for key in STATUS_COUNT_KEYS}


def normalize_node_priority(value):
    try:
        normalized_value = int(value)
    except (TypeError, ValueError):
        return None

    return normalized_value or None


def normalize_node_status(value):
    normalized_value = str(value or '').strip()
    return normalized_value if normalized_value in STATUS_COUNT_KEYS else 'not_run'


def user_can_see_dev_self_test_record(user, record):
    if not record:
        return False

    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True

    return getattr(record, 'audit_status', '') == 'approved'


def collect_dev_self_test_status_counts(mindmap, user=None):
    counts = create_empty_status_counts()
    mindmap_data = getattr(mindmap, 'mindmap_data', None)
    if not mindmap_data or not isinstance(mindmap_data, dict):
        return counts

    record_map = {
        str(record.node_id): record
        for record in DevSelfTestRecord.objects.filter(mindmap=mindmap)
    }
    counted_record_ids = set()

    for descriptor in iter_mindmap_target_nodes(
        mindmap_data.get('root', {}),
        mindmap_id=mindmap.id,
        target_type='testpoint',
    ):
        data = descriptor.get('data') or {}
        if normalize_node_priority(data.get('priority')) != 1:
            continue

        aliases = {
            str(descriptor.get('public_id') or '').strip(),
            str(descriptor.get('node_id') or '').strip(),
        }
        aliases.discard('')
        record = next((record_map.get(alias) for alias in aliases if record_map.get(alias)), None)
        if record:
            counted_record_ids.add(record.id)

        status = (
            record.status
            if user_can_see_dev_self_test_record(user, record)
            else data.get('status')
        )
        counts[normalize_node_status(status)] += 1

    for record in record_map.values():
        if record.id in counted_record_ids:
            continue
        if record.audit_status != 'approved':
            continue
        if normalize_node_priority(record.priority) != 1:
            continue
        counts[normalize_node_status(record.status)] += 1

    return counts

class TestCaseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    versions = VersionSimpleSerializer(many=True, read_only=True)
    step_details = TestCaseStepSerializer(many=True, read_only=True)
    attachments = TestCaseAttachmentSerializer(many=True, read_only=True)
    comments = TestCaseCommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class TestCaseCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    
    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result', 
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids'
        ]
    
    def create(self, validated_data):
        version_ids = validated_data.pop('version_ids', [])
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)
        
        testcase = super().create(validated_data)
        
        # 设置版本关联
        if version_ids:
            testcase.versions.set(version_ids)
        
        return testcase

class TestCaseUpdateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    
    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result', 
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids'
        ]
    
    def update(self, instance, validated_data):
        version_ids = validated_data.pop('version_ids', None)
        # project_id会在视图中处理
        validated_data.pop('project_id', None)

        instance = super().update(instance, validated_data)

        # 更新版本关联
        if version_ids is not None:
            instance.versions.set(version_ids)

        return instance


class ManualTestCaseMindmapSerializer(serializers.ModelSerializer):
    """手工用例脑图序列化器"""
    author = UserSerializer(read_only=True)
    executor = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    version = VersionSimpleSerializer(read_only=True)
    frontend_developer = UserSerializer(read_only=True)
    backend_developer = UserSerializer(read_only=True)
    case_count = serializers.SerializerMethodField()
    testpoint_count = serializers.SerializerMethodField()
    review_testpoint_count = serializers.SerializerMethodField()
    dev_self_test_count = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    requirement_group_name = serializers.SerializerMethodField()
    requirement_frontend_developer = serializers.SerializerMethodField()
    requirement_backend_developer = serializers.SerializerMethodField()

    class Meta:
        model = ManualTestCaseMindmap
        fields = '__all__'
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'requirement_key', 'requirement_title']

    def _get_linked_requirement_record(self, obj):
        requirement_key = str(getattr(obj, 'requirement_key', '') or '').strip()
        if not requirement_key:
            return None

        cache = self.context.setdefault('_manual_mindmap_requirement_record_cache', {})
        if requirement_key not in cache:
            cache[requirement_key] = (
                JiraRequirementRecord.objects
                .filter(issue_key=requirement_key)
                .order_by('-updated_at')
                .first()
            )
        return cache[requirement_key]

    def _get_linked_requirement_text(self, obj, field_name):
        record = self._get_linked_requirement_record(obj)
        return str(getattr(record, field_name, '') or '').strip() if record else ''

    def get_module(self, obj):
        return self._get_linked_requirement_text(obj, 'module')

    def get_requirement_group_name(self, obj):
        return self._get_linked_requirement_text(obj, 'group_name')

    def get_requirement_frontend_developer(self, obj):
        return self._get_linked_requirement_text(obj, 'frontend_developer')

    def get_requirement_backend_developer(self, obj):
        return self._get_linked_requirement_text(obj, 'backend_developer')

    def _count_nodes_by_type_and_status(self, node, node_type):
        """递归统计指定类型节点按状态分类的数量"""
        status_counts = create_empty_status_counts()

        # 检查当前节点类型
        if node and isinstance(node, dict):
            node_data = node.get('data', {})
            if node_data.get('nodeType') == node_type:
                # 获取节点状态，默认为未执行
                status = node_data.get('status', 'not_run')
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    # 如果状态不在已知状态中，归类为未执行
                    status_counts['not_run'] += 1

            # 递归统计子节点
            children = node.get('children', [])
            if children:
                for child in children:
                    child_counts = self._count_nodes_by_type_and_status(child, node_type)
                    for status, count in child_counts.items():
                        status_counts[status] += count

        return status_counts

    def _count_review_testpoints(self, node):
        counts = {
            'unprocessed': 0,
            'processed': 0,
            'total': 0,
        }

        if not node or not isinstance(node, dict):
            return counts

        node_data = node.get('data', {})
        if node_data.get('nodeType') == 'testpoint':
            review_opinion = str(node_data.get('reviewOpinion') or '').strip()
            review_status = str(node_data.get('reviewStatus') or '').strip()
            if review_opinion or review_status in {'未处理', '已处理'}:
                counts['total'] += 1
                if review_status == '已处理':
                    counts['processed'] += 1
                else:
                    counts['unprocessed'] += 1

        children = node.get('children', [])
        if children:
            for child in children:
                child_counts = self._count_review_testpoints(child)
                for key, count in child_counts.items():
                    counts[key] += count

        return counts

    def get_case_count(self, obj):
        """获取用例按状态分类的数量"""
        mindmap_data = obj.mindmap_data
        if not mindmap_data or not isinstance(mindmap_data, dict):
            return create_empty_status_counts()

        root = mindmap_data.get('root', {})
        return self._count_nodes_by_type_and_status(root, 'case')

    def get_testpoint_count(self, obj):
        """获取测试点按状态分类的数量"""
        mindmap_data = obj.mindmap_data
        if not mindmap_data or not isinstance(mindmap_data, dict):
            return create_empty_status_counts()

        root = mindmap_data.get('root', {})
        return self._count_nodes_by_type_and_status(root, 'testpoint')

    def get_review_testpoint_count(self, obj):
        mindmap_data = obj.mindmap_data
        if not mindmap_data or not isinstance(mindmap_data, dict):
            return {'unprocessed': 0, 'processed': 0, 'total': 0}

        root = mindmap_data.get('root', {})
        return self._count_review_testpoints(root)

    def get_dev_self_test_count(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return collect_dev_self_test_status_counts(
            obj,
            user=getattr(request, 'user', None),
        )


class ManualTestCaseMindmapCreateSerializer(serializers.ModelSerializer):
    """手工用例脑图创建序列化器"""
    project_id = serializers.IntegerField(required=True, help_text="项目ID")
    category_id = serializers.IntegerField(required=False, allow_null=True, help_text="目录ID")
    version_id = serializers.IntegerField(required=False, allow_null=True, help_text="版本ID")
    frontend_developer_id = serializers.IntegerField(required=False, allow_null=True, help_text="前端开发人员ID")
    backend_developer_id = serializers.IntegerField(required=False, allow_null=True, help_text="后端开发人员ID")

    executor_id = serializers.IntegerField(required=False, allow_null=True, help_text="执行人ID")

    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="Project ID")

    class Meta:
        model = ManualTestCaseMindmap
        fields = ['id', 'name', 'description', 'mindmap_data', 'project_id', 'category_id',
                  'version_id', 'responsibility_group', 'frontend_developer_id', 'backend_developer_id', 'executor_id', 'url', 'mindmap_scope',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_responsibility_group(self, value):
        return normalize_existing_group_name(value)

    def get_fields(self):
        fields = super().get_fields()
        if 'project_id' in fields:
            fields['project_id'].required = False
            fields['project_id'].allow_null = True
        return fields

    def validate_executor_id(self, value):
        if value is None:
            return value

        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('执行人不存在')

        return value

    def validate_mindmap_data(self, value):
        return normalize_mindmap_data(value)

    def create(self, validated_data):
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)
        executor_id = validated_data.pop('executor_id', None)
        if executor_id:
            validated_data['executor_id'] = executor_id
        return super().create(validated_data)


class ManualTestCaseMindmapUpdateSerializer(serializers.ModelSerializer):
    """手工用例脑图更新序列化器"""
    category_id = serializers.IntegerField(required=False, allow_null=True, help_text="目录ID")
    version_id = serializers.IntegerField(required=False, allow_null=True, help_text="版本ID")
    frontend_developer_id = serializers.IntegerField(required=False, allow_null=True, help_text="前端开发人员ID")
    backend_developer_id = serializers.IntegerField(required=False, allow_null=True, help_text="后端开发人员ID")

    executor_id = serializers.IntegerField(required=False, allow_null=True, help_text="执行人ID")

    class Meta:
        model = ManualTestCaseMindmap
        fields = ['name', 'description', 'mindmap_data', 'category_id',
                  'version_id', 'responsibility_group', 'frontend_developer_id', 'backend_developer_id', 'executor_id', 'url', 'mindmap_scope']

    def validate_responsibility_group(self, value):
        return normalize_existing_group_name(value)

    def validate_executor_id(self, value):
        if value is None:
            return value

        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('执行人不存在')

        return value

    def validate_mindmap_data(self, value):
        normalized = normalize_mindmap_data(value)
        instance = getattr(self, 'instance', None)
        if (
            instance
            and instance.mindmap_scope == ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS
            and count_mindmap_descendants(instance.mindmap_data) > 0
            and count_mindmap_descendants(normalized) == 0
        ):
            raise serializers.ValidationError('不能用空需求分析脑图覆盖已有分析结果')
        return normalized


class ManualTestCaseNodeSerializer(serializers.Serializer):
    """手工用例脑图节点平铺列表"""
    id = serializers.CharField()
    mindmap_id = serializers.IntegerField()
    mindmap_name = serializers.CharField()
    requirement_key = serializers.CharField(allow_blank=True, required=False)
    requirement_title = serializers.CharField(allow_blank=True, required=False)
    version_name = serializers.CharField(allow_blank=True, required=False)
    node_text = serializers.CharField()
    node_type = serializers.CharField()
    case_id = serializers.CharField(allow_blank=True, required=False)
    priority = serializers.IntegerField(allow_null=True, required=False)
    status = serializers.CharField(allow_blank=True, required=False)
    is_dev_self_test = serializers.BooleanField(required=False)
    self_test_status = serializers.CharField(allow_blank=True, required=False)
    self_test_audit_status = serializers.CharField(allow_blank=True, required=False)
    review_opinion = serializers.CharField(allow_blank=True, required=False)
    reviewer_id = serializers.IntegerField(allow_null=True, required=False)
    reviewer_name = serializers.CharField(allow_blank=True, required=False)
    review_time = serializers.CharField(allow_blank=True, required=False)
    review_status = serializers.CharField(allow_blank=True, required=False)
    responsibility_group = serializers.CharField(allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    path = serializers.CharField()
    module_path = serializers.CharField(allow_blank=True, required=False)
    parent_text = serializers.CharField(allow_blank=True, required=False)
    author = UserSerializer(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ManualTestCaseCategorySerializer(serializers.ModelSerializer):
    """手工用例目录序列化器 - 递归支持子目录"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = ManualTestCaseCategory
        fields = ['id', 'name', 'description', 'parent', 'order', 'children', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.all()
        return ManualTestCaseCategorySerializer(children, many=True).data


class ManualTestCaseCategoryCreateSerializer(serializers.ModelSerializer):
    """手工用例目录创建序列化器"""
    project_id = serializers.IntegerField(required=True, help_text="项目ID")
    parent_id = serializers.IntegerField(required=False, allow_null=True, help_text="父目录ID")

    class Meta:
        model = ManualTestCaseCategory
        fields = ['id', 'name', 'description', 'parent_id', 'project_id', 'order']
        read_only_fields = ['id']

    def create(self, validated_data):
        parent_id = validated_data.pop('parent_id', None)
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)

        if parent_id:
            validated_data['parent_id'] = parent_id

        return super().create(validated_data)


class ManualTestCaseCategoryUpdateSerializer(serializers.ModelSerializer):
    """手工用例目录更新序列化器"""
    parent_id = serializers.IntegerField(required=False, allow_null=True, help_text="父目录ID")

    class Meta:
        model = ManualTestCaseCategory
        fields = ['name', 'description', 'parent_id', 'order']

    def update(self, instance, validated_data):
        parent_id = validated_data.pop('parent_id', None)

        if parent_id is not None:
            instance.parent_id = parent_id

        return super().update(instance, validated_data)


class DevSelfTestSerializer(serializers.Serializer):
    """开发自测列表序列化器"""
    id = serializers.CharField(help_text="节点ID")
    mindmap_id = serializers.IntegerField(help_text="脑图ID")
    mindmap_name = serializers.CharField(help_text="脑图名称")
    module = serializers.CharField(help_text="模块名称")
    testpoint = serializers.CharField(help_text="测试点")
    priority = serializers.IntegerField(help_text="优先级")
    status = serializers.CharField(help_text="状态")
    responsibility_group = serializers.CharField(allow_blank=True, help_text="责任小组")
    frontend_developer = UserSerializer(allow_null=True, help_text="前端开发")
    backend_developer = UserSerializer(allow_null=True, help_text="后端开发")
    updated_at = serializers.DateTimeField(help_text="更新时间")
