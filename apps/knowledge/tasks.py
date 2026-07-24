from celery import shared_task
from django.contrib.auth import get_user_model

from .models import KnowledgeRepositoryConfig
from .services import index_repository


@shared_task(bind=True, time_limit=900, soft_time_limit=840)
def index_knowledge_repository_task(self, config_id, user_id=None, trigger='auto_ready'):
    config = KnowledgeRepositoryConfig.objects.select_related('project', 'space', 'created_by').get(id=config_id)
    user = None
    if user_id:
        user = get_user_model().objects.filter(id=user_id).first()
    return {
        'run_id': index_repository(config, user=user, trigger=trigger).id,
        'config_id': config.id,
    }
