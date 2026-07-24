from django.urls import path

from . import views


urlpatterns = [
    path(
        'playwright-recordings/<str:session_id>/allure-report/',
        views.PlaywrightRecordingSessionAllureReportView.as_view(),
        name='playwright-recording-allure-report',
    ),
]
