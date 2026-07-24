from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.testcases.models import ManualTestCaseCategory, ManualTestCaseMindmap
from apps.users.models import User
from apps.versions.models import Version

from .models import Project, ProjectEnvironment, ProjectMember


class ProjectVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='project_owner',
            email='project-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='project_viewer',
            email='project-viewer@example.com',
            password='viewer123456',
        )
        self.project = Project.objects.create(
            name='Admin Created Project',
            owner=self.owner,
            description='visible to all authenticated workspace users',
        )
        self.empty_project = Project.objects.create(
            name='Empty Project',
            owner=self.owner,
            description='has no manual workspace data',
        )

    def test_non_member_can_list_projects_created_by_other_users(self):
        self.client.force_authenticate(self.viewer)

        response = self.client.get('/api/projects/list/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            self.project.id,
            [item['id'] for item in response.data['results']],
        )

    def test_project_list_includes_manual_workspace_counts(self):
        version = Version.objects.create(
            name='2026.04.22',
            created_by=self.owner,
        )
        version.projects.add(self.project)
        category = ManualTestCaseCategory.objects.create(
            project=self.project,
            name='客户端',
            order=1,
        )
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='有数据的脑图',
            category=category,
            version=version,
            author=self.owner,
            mindmap_data={
                'root': {
                    'data': {
                        'text': '根节点',
                        'nodeType': 'requirement',
                    },
                    'children': [],
                }
            },
        )
        ManualTestCaseMindmap.objects.create(
            project=self.project,
            name='Requirement Analysis Mindmap',
            author=self.owner,
            mindmap_scope=ManualTestCaseMindmap.SCOPE_REQUIREMENT_ANALYSIS,
            mindmap_data={
                'root': {
                    'data': {
                        'text': 'Requirement Analysis Mindmap',
                        'nodeType': 'requirement',
                    },
                    'children': [],
                }
            },
        )
        self.client.force_authenticate(self.viewer)

        response = self.client.get('/api/projects/list/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_item = next(item for item in response.data['results'] if item['id'] == self.project.id)
        self.assertEqual(target_item['version_count'], 1)
        self.assertEqual(target_item['manual_category_count'], 1)
        self.assertEqual(target_item['mindmap_count'], 1)

    def test_project_list_includes_default_flag(self):
        self.project.is_default = True
        self.project.save(update_fields=['is_default'])
        self.client.force_authenticate(self.viewer)

        response = self.client.get('/api/projects/list/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target_item = next(item for item in response.data['results'] if item['id'] == self.project.id)
        self.assertTrue(target_item['is_default'])


class ProjectMemberManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='member_owner',
            email='member-owner@example.com',
            password='owner123456',
        )
        self.viewer = User.objects.create_user(
            username='member_viewer',
            email='member-viewer@example.com',
            password='viewer123456',
        )
        self.developer = User.objects.create_user(
            username='member_developer',
            email='member-developer@example.com',
            password='developer123456',
            department='研发',
            position='开发工程师',
        )
        self.tester = User.objects.create_user(
            username='member_tester',
            email='member-tester@example.com',
            password='tester123456',
            department='测试',
            position='测试工程师',
        )
        self.reviewer = User.objects.create_user(
            username='member_reviewer',
            email='member-reviewer@example.com',
            password='reviewer123456',
        )
        self.project = Project.objects.create(
            name='Project Member Workspace',
            owner=self.owner,
            description='project member management tests',
        )
        self.existing_member = ProjectMember.objects.create(
            project=self.project,
            user=self.developer,
            role='developer',
        )

    def test_authenticated_user_can_view_project_members(self):
        self.client.force_authenticate(self.viewer)

        response = self.client.get(f'/api/projects/{self.project.id}/members/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        owner_row = next(item for item in response.data if item['user_id'] == self.owner.id)
        self.assertTrue(owner_row['is_owner'])
        self.assertEqual(owner_row['role'], 'owner')
        self.assertIsNone(owner_row['membership_id'])

        member_row = next(item for item in response.data if item['user_id'] == self.developer.id)
        self.assertFalse(member_row['is_owner'])
        self.assertEqual(member_row['membership_id'], self.existing_member.id)
        self.assertEqual(member_row['role'], 'developer')
        self.assertEqual(member_row['department'], '研发')
        self.assertEqual(member_row['position'], '开发工程师')

    def test_owner_can_add_update_and_delete_project_members_by_user_id(self):
        self.client.force_authenticate(self.owner)

        add_response = self.client.post(
            f'/api/projects/{self.project.id}/members/add/',
            {'user_id': self.tester.id},
            format='json',
        )
        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)
        created_membership = ProjectMember.objects.get(project=self.project, user=self.tester)
        self.assertEqual(created_membership.role, 'tester')
        self.assertEqual(add_response.data['member']['user_id'], self.tester.id)
        self.assertEqual(add_response.data['member']['role'], 'tester')

        update_response = self.client.patch(
            f'/api/projects/{self.project.id}/members/{self.developer.id}/',
            {'user_id': self.reviewer.id},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.developer).exists())
        updated_membership = ProjectMember.objects.get(project=self.project, user=self.reviewer)
        self.assertEqual(updated_membership.role, 'developer')
        self.assertEqual(update_response.data['member']['user_id'], self.reviewer.id)
        self.assertEqual(update_response.data['member']['role'], 'developer')

        delete_response = self.client.delete(
            f'/api/projects/{self.project.id}/members/{self.tester.id}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.tester).exists())


class ProjectEnvironmentManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='environment_owner',
            email='environment-owner@example.com',
            password='owner123456',
        )
        self.project = Project.objects.create(
            name='Environment Project',
            owner=self.owner,
            description='project environment management tests',
        )

    def test_authenticated_user_can_create_update_list_and_delete_project_environment(self):
        self.client.force_authenticate(self.owner)

        create_response = self.client.post(
            '/api/projects/environments/',
            {
                'project': self.project.id,
                'name': '测试环境',
                'base_url': 'https://test.example.com',
                'account': 'tester',
                'password': 'secret123',
                'is_default': True,
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create_response.data['has_password'])
        self.assertNotIn('password', create_response.data)

        environment = ProjectEnvironment.objects.get(id=create_response.data['id'])
        self.assertEqual(environment.project, self.project)
        self.assertEqual(environment.account, 'tester')
        self.assertTrue(environment.password_encrypted)

        list_response = self.client.get('/api/projects/environments/', {'project': self.project.id})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['project_name'], self.project.name)

        update_response = self.client.patch(
            f'/api/projects/environments/{environment.id}/',
            {
                'name': '预发环境',
                'base_url': 'https://staging.example.com',
                'account': 'staging-user',
            },
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        environment.refresh_from_db()
        self.assertEqual(environment.name, '预发环境')
        self.assertEqual(environment.base_url, 'https://staging.example.com')
        self.assertEqual(environment.account, 'staging-user')
        self.assertTrue(environment.password_encrypted)

        delete_response = self.client.delete(f'/api/projects/environments/{environment.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectEnvironment.objects.filter(id=environment.id).exists())

    def test_project_environment_list_supports_configured_field_filters(self):
        self.client.force_authenticate(self.owner)
        other_project = Project.objects.create(
            name='Other Environment Project',
            owner=self.owner,
            description='other project',
        )
        ProjectEnvironment.objects.create(
            project=self.project,
            name='预发环境',
            base_url='https://staging.example.com',
            account='staging-user',
            password_encrypted='encrypted-secret',
            description='backend configured filters',
        )
        ProjectEnvironment.objects.create(
            project=other_project,
            name='生产环境',
            base_url='https://prod.example.com',
            account='prod-user',
            password_encrypted='',
            description='production environment',
        )

        project_response = self.client.get('/api/projects/environments/', {'project_name': 'Environment Project'})
        self.assertEqual(project_response.status_code, status.HTTP_200_OK)
        self.assertEqual(project_response.data['count'], 2)

        name_response = self.client.get('/api/projects/environments/', {'name': '预发'})
        self.assertEqual(name_response.status_code, status.HTTP_200_OK)
        self.assertEqual(name_response.data['count'], 1)
        self.assertEqual(name_response.data['results'][0]['name'], '预发环境')

        password_response = self.client.get('/api/projects/environments/', {'has_password': 'true'})
        self.assertEqual(password_response.status_code, status.HTTP_200_OK)
        self.assertEqual(password_response.data['count'], 1)
        self.assertEqual(password_response.data['results'][0]['account'], 'staging-user')


class ProjectDefaultTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='default_project_owner',
            email='default-project-owner@example.com',
            password='owner123456',
        )
        self.project_a = Project.objects.create(
            name='Project A',
            owner=self.owner,
            description='A project',
            is_default=True,
        )
        self.project_b = Project.objects.create(
            name='Project B',
            owner=self.owner,
            description='B project',
            is_default=False,
        )

    def test_setting_default_project_clears_previous_default(self):
        self.client.force_authenticate(self.owner)

        response = self.client.patch(
            f'/api/projects/{self.project_b.id}/',
            {'is_default': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project_a.refresh_from_db()
        self.project_b.refresh_from_db()
        self.assertFalse(self.project_a.is_default)
        self.assertTrue(self.project_b.is_default)
