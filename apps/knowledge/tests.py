from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.users.models import User

from .models import KnowledgeRepositoryConfig, KnowledgeSpace
from .services import maybe_auto_index_repository, test_database_schema_connection


class KnowledgeObjectLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='knowledge_owner',
            email='knowledge-owner@example.com',
            password='owner123456',
        )

    def test_project_creation_creates_empty_knowledge_space(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            '/api/projects/',
            {
                'name': 'Knowledge Lifecycle Project',
                'description': 'created from API',
                'status': 'active',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        project = Project.objects.get(name='Knowledge Lifecycle Project')
        space = KnowledgeSpace.objects.get(project=project)
        self.assertEqual(space.key, f'project_{project.id}_knowledge')
        self.assertEqual(space.build_status, 'pending_config')
        self.assertEqual(space.owner, self.user)

    def test_ready_repository_config_marks_space_ready_when_auto_index_disabled(self):
        project = Project.objects.create(name='Ready Project', owner=self.user)
        space = KnowledgeSpace.objects.create(
            key='ready_project_space',
            name='Ready Project Knowledge',
            project=project,
            owner=self.user,
            build_status='pending_config',
        )
        config = KnowledgeRepositoryConfig.objects.create(
            name='Ready Repository',
            project=project,
            space=space,
            provider='local',
            repository_mode='local_path',
            auth_mode='none',
            local_path='D:/AI/syswin-testhub/testhub-platform-src',
            auto_index_on_ready=False,
            created_by=self.user,
        )

        result = maybe_auto_index_repository(config, user=self.user)

        self.assertIsNone(result)
        space.refresh_from_db()
        self.assertEqual(space.build_status, 'ready')

    @override_settings(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
    def test_disabled_schema_connection_is_safe(self):
        project = Project.objects.create(name='Schema Disabled Project', owner=self.user)
        space = KnowledgeSpace.objects.create(
            key='schema_disabled_space',
            name='Schema Disabled Knowledge',
            project=project,
            owner=self.user,
        )
        config = KnowledgeRepositoryConfig.objects.create(
            name='Schema Disabled Repository',
            project=project,
            space=space,
            provider='local',
            repository_mode='local_path',
            auth_mode='none',
            local_path='D:/AI/syswin-testhub/testhub-platform-src',
            database_engine='none',
            created_by=self.user,
        )

        payload, status_code = test_database_schema_connection(config)

        self.assertEqual(status_code, 200)
        self.assertTrue(payload['success'])
        self.assertEqual(payload['table_count'], 0)
