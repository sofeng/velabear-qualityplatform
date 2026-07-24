from django.http import JsonResponse
from django.views import View
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .notification_services import (
    build_notification_stream_response,
    get_or_build_defect_email_config,
    get_stream_user_from_token,
    get_user_defect_notification_types,
    save_defect_email_config,
    send_defect_test_email,
    update_user_defect_notification_types,
    verify_defect_email_config,
)
from .serializers import (
    DefectEmailConfigSerializer,
    DefectEmailTestSerializer,
    DefectNotificationSettingsSerializer,
)


class DefectEmailConfigView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = DefectEmailConfigSerializer(get_or_build_defect_email_config())
        return Response(serializer.data)

    def put(self, request):
        serializer = DefectEmailConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = save_defect_email_config(serializer.validated_data, request.user)
        return Response(DefectEmailConfigSerializer(config).data)


class DefectEmailConfigTestSendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        config = get_or_build_defect_email_config()
        serializer = DefectEmailTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            send_defect_test_email(
                config,
                serializer.validated_data['to'],
                subject=serializer.validated_data.get('subject', ''),
                text=serializer.validated_data.get('text', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'测试邮件发送失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': '测试邮件发送成功'})


class DefectEmailConfigVerifySMTPView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        config = get_or_build_defect_email_config()
        try:
            verify_defect_email_config(config)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'SMTP 校验失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'SMTP 连接正常'})


class DefectNotificationSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'types': get_user_defect_notification_types(request.user)})

    def put(self, request):
        serializer = DefectNotificationSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        types = update_user_defect_notification_types(request.user, serializer.validated_data.get('types', []))
        return Response({'types': types})


class DefectNotificationStreamView(View):
    def get(self, request):
        user = request.user if getattr(request.user, 'is_authenticated', False) else None
        if user is None:
            token = request.GET.get('token')
            user = get_stream_user_from_token(token)

        if user is None:
            return JsonResponse({'detail': '未授权访问'}, status=status.HTTP_401_UNAUTHORIZED)

        return build_notification_stream_response(user)
