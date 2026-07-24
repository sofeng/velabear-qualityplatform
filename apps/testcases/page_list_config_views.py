from django.db import transaction
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ManualWorkspacePageListConfig
from .page_list_config_registry import (
    MODULE_KEY,
    build_factory_config,
    build_registry_payload,
    get_page_definition,
    get_page_definition_by_storage_key,
)
from .page_list_config_serializers import (
    ManualWorkspacePageListConfigRestoreSerializer,
    ManualWorkspacePageListConfigSerializer,
    ManualWorkspacePageListConfigUpsertSerializer,
)


CONFIG_PERMISSION_CODE = 'menu:manual-testcases:config'


def can_manage_page_list_config(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    has_permission_code = getattr(user, 'has_permission_code', None)
    return callable(has_permission_code) and has_permission_code(CONFIG_PERMISSION_CODE)


def enforce_manage_permission(request):
    if not can_manage_page_list_config(request.user):
        raise PermissionDenied('无权限维护列表排序配置')


def get_or_factory_config(module_key, page_key):
    page_def = get_page_definition(page_key)
    if not page_def:
        raise ValidationError({'page_key': '不支持的页面标识'})

    config = ManualWorkspacePageListConfig.objects.filter(
        module_key=module_key,
        page_key=page_def['page_key'],
    ).first()
    if config:
        return config, False

    factory = build_factory_config(page_def)
    return ManualWorkspacePageListConfig(
        module_key=module_key,
        page_key=page_def['page_key'],
        filter_conditions=factory['filter_conditions'],
        columns=factory['columns'],
        version=0,
    ), True


class ManualWorkspacePageListRegistryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(build_registry_payload())


class ManualWorkspacePageListConfigView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        page_key = request.query_params.get('page_key')
        storage_key = request.query_params.get('storage_key')

        if storage_key and not page_key:
            page_def = get_page_definition_by_storage_key(storage_key)
            if not page_def:
                raise ValidationError({'storage_key': '不支持的列表配置标识'})
            page_key = page_def['page_key']

        if not page_key:
            configs = ManualWorkspacePageListConfig.objects.filter(module_key=MODULE_KEY).order_by('page_key')
            return Response(ManualWorkspacePageListConfigSerializer(configs, many=True).data)

        config, is_factory = get_or_factory_config(MODULE_KEY, page_key)
        data = ManualWorkspacePageListConfigSerializer(config).data
        data['is_factory'] = is_factory
        return Response(data)

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        enforce_manage_permission(request)
        serializer = ManualWorkspacePageListConfigUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        page_key = data['page_key']

        config = ManualWorkspacePageListConfig.objects.select_for_update().filter(
            module_key=data['module_key'],
            page_key=page_key,
        ).first()
        requested_version = data.get('version')
        if config and requested_version and requested_version != config.version:
            return Response(
                {'detail': '配置已被其他用户更新，请刷新后再保存', 'current_version': config.version},
                status=status.HTTP_409_CONFLICT,
            )

        if not config:
            config = ManualWorkspacePageListConfig(
                module_key=data['module_key'],
                page_key=page_key,
                version=0,
            )

        config.filter_conditions = data['filter_conditions']
        config.columns = data['columns']
        config.version = config.version + 1
        config.updated_by = request.user
        config.save()
        return Response(ManualWorkspacePageListConfigSerializer(config).data)

    patch = put


class ManualWorkspacePageListConfigRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        enforce_manage_permission(request)
        serializer = ManualWorkspacePageListConfigRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        config = ManualWorkspacePageListConfig.objects.select_for_update().filter(
            module_key=data['module_key'],
            page_key=data['page_key'],
        ).first()
        requested_version = data.get('version')
        if config and requested_version and requested_version != config.version:
            return Response(
                {'detail': '配置已被其他用户更新，请刷新后再恢复默认', 'current_version': config.version},
                status=status.HTTP_409_CONFLICT,
            )

        if not config:
            config = ManualWorkspacePageListConfig(
                module_key=data['module_key'],
                page_key=data['page_key'],
                version=0,
            )
        factory = data['factory_config']
        config.filter_conditions = factory['filter_conditions']
        config.columns = factory['columns']
        config.version = config.version + 1
        config.updated_by = request.user
        config.save()
        return Response(ManualWorkspacePageListConfigSerializer(config).data)
