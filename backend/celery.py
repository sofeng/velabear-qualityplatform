import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')

task_modules = tuple(
    item.strip()
    for item in os.environ.get('TESTHUB_CELERY_TASK_MODULES', '').split(',')
    if item.strip()
)
if task_modules:
    app.conf.imports = task_modules
else:
    app.autodiscover_tasks()
