from .urls_automation import urlpatterns as automation_urlpatterns
from .urls_core import urlpatterns as core_urlpatterns
from .urls_report import urlpatterns as report_urlpatterns


urlpatterns = [*core_urlpatterns, *automation_urlpatterns, *report_urlpatterns]
