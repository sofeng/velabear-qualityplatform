from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.users.models import User

from .models import Version


class VersionVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='version_owner',
            email='version-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='version_viewer',
            email='version-viewer@example.com',
            password='viewer123456',
        )
        self.project = Project.objects.create(
            name='Shared Version Project',
            owner=self.owner,
        )
        self.version = Version.objects.create(
            name='2026.04.22',
            description='created by owner',
            created_by=self.owner,
        )
        self.version.projects.add(self.project)

    def test_non_member_can_list_versions_for_project(self):
        self.client.force_authenticate(self.viewer)

        response = self.client.get(f'/api/versions/projects/{self.project.id}/versions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [self.version.id])
