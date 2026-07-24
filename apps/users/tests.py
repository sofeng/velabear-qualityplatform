from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .admin_forms import UserAdminChangeForm, UserAdminCreationForm
from .models import PermissionItem, Role, RoleMembership, RolePermission, User


class UserAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123456',
        )
        self.target_user = User.objects.create_user(
            username='normal_user',
            email='normal@example.com',
            password='user123456',
            first_name='Initial',
        )
        self.client.force_login(self.admin_user)

    def test_admin_change_page_renders(self):
        response = self.client.get(reverse('admin:users_user_change', args=[self.target_user.pk]))

        self.assertEqual(response.status_code, 200)

    def test_admin_forms_expose_full_name_field(self):
        change_form = UserAdminChangeForm(instance=self.target_user)
        creation_form = UserAdminCreationForm()

        self.assertIn('full_name', change_form.fields)
        self.assertIn('full_name', creation_form.fields)
        self.assertEqual(change_form.fields['full_name'].initial, self.target_user.full_name)


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='staff123456',
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username='member_user',
            email='member@example.com',
            password='member123456',
            first_name='Common',
            last_name='Member',
        )
        self.other_user = User.objects.create_user(
            username='search_target',
            email='search@example.com',
            password='target123456',
            department='Quality',
            position='QA Engineer',
        )

    def grant_role_permissions(self, user, *permission_items):
        role = Role.objects.create(name=f'Role for {user.username} {Role.objects.count() + 1}')
        role.members.add(user)
        RoleMembership.objects.create(role=role, user=user, tags=[])
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission_item=permission_item)
                for permission_item in permission_items
            ]
        )
        return role

    def test_authenticated_user_can_list_users_with_search(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.get('/api/auth/users/', {'search': 'Quality'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['username'], self.other_user.username)

    def test_non_staff_user_cannot_create_user(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            '/api/auth/users/',
            {
                'username': 'blocked_user',
                'email': 'blocked@example.com',
                'password': 'blocked123456',
                'password_confirm': 'blocked123456',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_user_with_admin_flags(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.post(
            '/api/auth/users/',
            {
                'username': 'managed_user',
                'email': 'managed@example.com',
                'password': 'managed123456',
                'password_confirm': 'managed123456',
                'first_name': 'Managed',
                'last_name': 'User',
                'department': 'Platform',
                'position': 'Manager',
                'is_active': True,
                'is_staff': True,
                'is_superuser': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(username='managed_user')
        self.assertEqual(created_user.email, 'managed@example.com')
        self.assertTrue(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)

    def test_non_staff_user_cannot_update_user(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.patch(
            f'/api/auth/users/{self.other_user.id}/',
            {'department': 'Forbidden'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_list_groups(self):
        group = Group.objects.create(name='QA Group')
        group.user_set.add(self.other_user)
        self.client.force_authenticate(self.member_user)

        response = self.client.get('/api/auth/groups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'QA Group')
        self.assertEqual(response.data['results'][0]['member_count'], 1)

    def test_non_staff_user_cannot_create_group(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            '/api/auth/groups/',
            {
                'name': 'Forbidden Group',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_group_with_members(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.post(
            '/api/auth/groups/',
            {
                'name': 'Platform Group',
                'member_ids': [self.member_user.id, self.other_user.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group = Group.objects.get(name='Platform Group')
        self.assertEqual(list(group.user_set.order_by('id').values_list('id', flat=True)), [self.member_user.id, self.other_user.id])

    def test_staff_user_can_manage_group_members(self):
        group = Group.objects.create(name='Editable Group')
        self.client.force_authenticate(self.staff_user)

        add_response = self.client.post(
            f'/api/auth/groups/{group.id}/members/',
            {'user_id': self.other_user.id},
            format='json',
        )
        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list(group.user_set.values_list('id', flat=True)), [self.other_user.id])

        update_response = self.client.patch(
            f'/api/auth/groups/{group.id}/members/{self.other_user.id}/',
            {'user_id': self.member_user.id},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(group.user_set.values_list('id', flat=True)), [self.member_user.id])

        delete_response = self.client.delete(
            f'/api/auth/groups/{group.id}/members/{self.member_user.id}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(group.user_set.count(), 0)

    def test_authenticated_user_can_list_roles(self):
        role = Role.objects.create(name='Review Role')
        role.members.add(self.other_user)
        RoleMembership.objects.create(role=role, user=self.other_user, tags=['核心', '冒烟'])
        self.client.force_authenticate(self.member_user)

        response = self.client.get('/api/auth/roles/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Review Role')
        self.assertEqual(response.data['results'][0]['member_count'], 1)
        self.assertEqual(response.data['results'][0]['members'][0]['tags'], ['核心', '冒烟'])

    def test_non_staff_user_cannot_create_role(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            '/api/auth/roles/',
            {
                'name': 'Forbidden Role',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_list_permission_items(self):
        PermissionItem.objects.create(
            name='测试权限目录',
            code='menu:test:catalog',
            item_type='menu',
            route_path='/test/catalog',
            sort_order=999,
        )
        self.client.force_authenticate(self.member_user)

        response = self.client.get('/api/auth/permission-items/', {'search': '测试权限目录'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['code'], 'menu:test:catalog')

    def test_manual_testcase_permission_tree_matches_latest_workspace_structure(self):
        module_permission = PermissionItem.objects.get(code='module:manual-testcases')
        workspace_permission = PermissionItem.objects.get(code='menu:manual-testcases:list')
        requirement_overview_permission = PermissionItem.objects.get(code='menu:manual-testcases:requirement-overview')
        testing_overview_permission = PermissionItem.objects.get(code='menu:manual-testcases:testing-overview')
        product_permission = PermissionItem.objects.get(code='menu:manual-testcases:product')
        development_permission = PermissionItem.objects.get(code='menu:manual-testcases:development')
        testing_permission = PermissionItem.objects.get(code='menu:manual-testcases:testing')
        defect_permission = PermissionItem.objects.get(code='menu:manual-testcases:defect')
        reports_permission = PermissionItem.objects.get(code='menu:manual-testcases:reports')
        config_permission = PermissionItem.objects.get(code='menu:manual-testcases:config')
        management_permission = PermissionItem.objects.get(code='menu:manual-testcases:management')
        recording_permission = PermissionItem.objects.get(code='menu:manual-testcases:recording')
        project_permission = PermissionItem.objects.get(code='menu:manual-testcases:projects')
        version_permission = PermissionItem.objects.get(code='menu:manual-testcases:versions')
        permission_page = PermissionItem.objects.get(code='menu:manual-testcases:permissions')
        permission_catalog = PermissionItem.objects.get(code='menu:manual-testcases:permissions:permission-catalog')
        version_requirement_permission = PermissionItem.objects.get(code='menu:manual-testcases:version-requirements')
        email_template_permission = PermissionItem.objects.get(code='menu:manual-testcases:defect-notifications')
        email_config_permission = PermissionItem.objects.get(code='menu:manual-testcases:defect-notifications:email-config')
        test_email_permission = PermissionItem.objects.get(code='menu:manual-testcases:defect-notifications:test-email')
        notification_settings_permission = PermissionItem.objects.get(code='menu:manual-testcases:defect-notifications:notification-settings')
        snapshots_permission = PermissionItem.objects.get(code='menu:manual-testcases:snapshots')
        recordings_permission = PermissionItem.objects.get(code='menu:manual-testcases:recordings')
        controlled_browser_permission = PermissionItem.objects.get(code='menu:manual-testcases:controlled-browser-lab')
        flows_permission = PermissionItem.objects.get(code='menu:manual-testcases:flows')
        visual_flow_permission = PermissionItem.objects.get(code='menu:manual-testcases:visual-flow')
        workflow_workbench_permission = PermissionItem.objects.get(code='menu:manual-testcases:workflow-workbench')
        technical_solution_design_permission = PermissionItem.objects.get(
            code='menu:manual-testcases:technical-solution-designs'
        )

        self.assertEqual(module_permission.name, '思源研发管理')
        self.assertEqual(workspace_permission.name, '总览')
        self.assertEqual(workspace_permission.parent_id, module_permission.id)
        self.assertEqual(workspace_permission.route_path, '/manual-testcases/list?tab=requirement-overview')
        self.assertEqual(requirement_overview_permission.parent_id, workspace_permission.id)
        self.assertEqual(testing_overview_permission.parent_id, workspace_permission.id)
        self.assertEqual(requirement_overview_permission.route_path, '/manual-testcases/list?tab=requirement-overview')
        self.assertEqual(testing_overview_permission.route_path, '/manual-testcases/list?tab=testing-overview')
        self.assertEqual(product_permission.parent_id, module_permission.id)
        self.assertEqual(development_permission.parent_id, module_permission.id)
        self.assertEqual(technical_solution_design_permission.parent_id, development_permission.id)
        self.assertEqual(
            technical_solution_design_permission.route_path,
            '/manual-testcases/list?tab=technical-solution-designs',
        )
        self.assertEqual(testing_permission.parent_id, module_permission.id)
        self.assertEqual(defect_permission.parent_id, module_permission.id)
        self.assertEqual(reports_permission.parent_id, module_permission.id)
        self.assertSequenceEqual(
            list(reports_permission.children.filter(item_type='menu').order_by('sort_order').values_list('code', flat=True)),
            [
                'menu:manual-testcases:quality-report-list',
                'menu:manual-testcases:quality-report-live',
            ],
        )
        self.assertFalse(
            PermissionItem.objects.filter(code='menu:manual-testcases:quality-report-excel').exists()
        )
        self.assertEqual(config_permission.parent_id, module_permission.id)
        self.assertEqual(management_permission.parent_id, module_permission.id)
        self.assertEqual(recording_permission.parent_id, module_permission.id)
        self.assertEqual(project_permission.parent_id, management_permission.id)
        self.assertEqual(version_permission.parent_id, management_permission.id)
        self.assertEqual(permission_page.parent_id, management_permission.id)
        self.assertEqual(project_permission.route_path, '/manual-testcases/list?tab=projects')
        self.assertEqual(version_permission.route_path, '/manual-testcases/list?tab=versions')
        self.assertEqual(permission_catalog.parent_id, permission_page.id)
        self.assertEqual(version_requirement_permission.parent_id, product_permission.id)
        self.assertEqual(email_template_permission.name, '邮件模板配置')
        self.assertEqual(email_template_permission.parent_id, config_permission.id)
        self.assertEqual(email_template_permission.route_path, '/manual-testcases/list?tab=email-template-config')
        self.assertEqual(email_config_permission.parent_id, email_template_permission.id)
        self.assertEqual(test_email_permission.parent_id, email_template_permission.id)
        self.assertEqual(notification_settings_permission.parent_id, email_template_permission.id)
        self.assertEqual(email_config_permission.route_path, '/manual-testcases/list?tab=email-config')
        self.assertEqual(test_email_permission.route_path, '/manual-testcases/list?tab=test-email')
        self.assertEqual(notification_settings_permission.route_path, '/manual-testcases/list?tab=notification-settings')
        self.assertEqual(workflow_workbench_permission.parent_id, config_permission.id)
        self.assertEqual(recording_permission.route_path, '/manual-testcases/snapshots')
        self.assertEqual(snapshots_permission.parent_id, recording_permission.id)
        self.assertEqual(recordings_permission.parent_id, recording_permission.id)
        self.assertEqual(controlled_browser_permission.parent_id, recording_permission.id)
        self.assertEqual(flows_permission.parent_id, recording_permission.id)
        self.assertEqual(visual_flow_permission.parent_id, recording_permission.id)
        self.assertEqual(snapshots_permission.route_path, '/manual-testcases/snapshots')
        self.assertEqual(recordings_permission.route_path, '/manual-testcases/recordings')
        self.assertEqual(controlled_browser_permission.route_path, '/manual-testcases/controlled-browser-lab')
        self.assertEqual(flows_permission.route_path, '/manual-testcases/flows')
        self.assertEqual(visual_flow_permission.route_path, '/manual-testcases/visual-flow')
        self.assertEqual(workflow_workbench_permission.route_path, '/manual-testcases/workflow-workbench')
        self.assertSequenceEqual(
            list(module_permission.children.filter(item_type='menu').order_by('sort_order').values_list('code', flat=True)),
            [
                'menu:manual-testcases:list',
                'menu:manual-testcases:product',
                'menu:manual-testcases:development',
                'menu:manual-testcases:testing',
                'menu:manual-testcases:defect',
                'menu:manual-testcases:reports',
                'menu:manual-testcases:config',
                'menu:manual-testcases:management',
                'menu:manual-testcases:recording',
            ]
        )
        self.assertTrue(PermissionItem.objects.filter(code='button:manual-testcases:mindmaps:create').exists())
        self.assertTrue(PermissionItem.objects.filter(code='button:manual-testcases:projects:create').exists())
        self.assertTrue(PermissionItem.objects.filter(code='action:manual-testcases:versions:set-default').exists())
        self.assertTrue(PermissionItem.objects.filter(code='action:manual-testcases:defect-notifications:send-test-email').exists())

    def test_ai_generation_permission_tree_matches_workspace_structure(self):
        module_permission = PermissionItem.objects.get(code='module:ai-generation')
        workspace_permission = PermissionItem.objects.get(code='menu:ai-generation:list')
        conversation_permission = PermissionItem.objects.get(code='menu:ai-generation:conversation')
        files_permission = PermissionItem.objects.get(code='menu:ai-generation:files')
        new_project_blueprints_permission = PermissionItem.objects.get(code='menu:ai-generation:new-project-blueprints')
        foundation_permission = PermissionItem.objects.get(code='menu:ai-generation:foundation')
        projects_permission = PermissionItem.objects.get(code='menu:ai-generation:projects')
        versions_permission = PermissionItem.objects.get(code='menu:ai-generation:versions')
        ai_dev_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-configs')
        ai_dev_runtime_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-runtime-configs')
        requirement_permission = PermissionItem.objects.get(code='menu:ai-generation:requirement')
        requirement_analysis_permission = PermissionItem.objects.get(code='menu:ai-generation:requirement-analysis')
        generated_permission = PermissionItem.objects.get(code='menu:ai-generation:generated-testcases')
        testing_permission = PermissionItem.objects.get(code='menu:ai-generation:testing')
        testcase_permission = PermissionItem.objects.get(code='menu:ai-generation:testcases')
        ui_automation_cases_permission = PermissionItem.objects.get(code='menu:ai-generation:ui-automation-cases')
        reviews_permission = PermissionItem.objects.get(code='menu:ai-generation:reviews')
        review_templates_permission = PermissionItem.objects.get(code='menu:ai-generation:review-templates')
        executions_permission = PermissionItem.objects.get(code='menu:ai-generation:executions')
        reports_permission = PermissionItem.objects.get(code='menu:ai-generation:reports')
        testcase_create_permission = PermissionItem.objects.get(code='button:ai-generation:testcases:create')
        development_permission = PermissionItem.objects.get(code='menu:ai-generation:development')
        ai_dev_tasks_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-tasks')
        workflow_workbench_permission = PermissionItem.objects.get(code='menu:ai-generation:workflow-workbench')
        defect_permission = PermissionItem.objects.get(code='menu:ai-generation:defect')
        operations_permission = PermissionItem.objects.get(code='menu:ai-generation:operations')
        ai_dev_build_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-build-configs')
        deployment_targets_permission = PermissionItem.objects.get(code='menu:ai-generation:deployment-targets')
        deployment_templates_permission = PermissionItem.objects.get(code='menu:ai-generation:deployment-templates')
        build_artifacts_permission = PermissionItem.objects.get(code='menu:ai-generation:build-artifacts')
        deployment_executions_permission = PermissionItem.objects.get(code='menu:ai-generation:deployment-executions')
        rollback_records_permission = PermissionItem.objects.get(code='menu:ai-generation:rollback-records')
        workshop_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop')
        tools_permission = PermissionItem.objects.get(code='menu:ai-generation:tools')
        ai_dev_test_tool_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-test-tool-configs')
        prompt_permission = PermissionItem.objects.get(code='menu:ai-generation:prompt-config')
        skill_permission = PermissionItem.objects.get(code='menu:ai-generation:skill')
        agent_permission = PermissionItem.objects.get(code='menu:ai-generation:agent')
        flow_permission = PermissionItem.objects.get(code='menu:ai-generation:flow')
        mcp_permission = PermissionItem.objects.get(code='menu:ai-generation:mcp')
        marketplace_permission = PermissionItem.objects.get(code='menu:ai-generation:marketplace')
        ai_dev_llm_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-llm-configs')
        ai_dev_repository_config_permission = PermissionItem.objects.get(code='menu:ai-generation:ai-dev-repository-configs')
        cicd_permission = PermissionItem.objects.get(code='menu:ai-generation:ci-cd')
        workshop_models_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop-models')
        workshop_test_tools_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop-test-tools')
        workshop_ui_env_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop-ui-env')
        workshop_integrations_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop-integrations')
        workshop_notifications_permission = PermissionItem.objects.get(code='menu:ai-generation:workshop-notifications')

        self.assertEqual(module_permission.name, 'AI研发平台')
        self.assertEqual(workspace_permission.parent_id, module_permission.id)
        self.assertEqual(workspace_permission.route_path, '/ai-generation/list')
        self.assertFalse(workspace_permission.is_active)

        expected_primary_permissions = [
            (conversation_permission, 'AI产品', '/ai-generation/products', 10),
            (workshop_permission, 'AI军火库', '/ai-generation/workshop', 80),
            (foundation_permission, '基础配置', '/ai-generation/list?tab=projects', 90),
        ]
        for permission, name, route_path, sort_order in expected_primary_permissions:
            self.assertEqual(permission.parent_id, module_permission.id)
            self.assertEqual(permission.name, name)
            self.assertEqual(permission.route_path, route_path)
            self.assertEqual(permission.sort_order, sort_order)

        self.assertEqual(new_project_blueprints_permission.parent_id, files_permission.id)
        self.assertEqual(projects_permission.parent_id, foundation_permission.id)
        self.assertEqual(versions_permission.parent_id, foundation_permission.id)
        self.assertEqual(ai_dev_config_permission.parent_id, foundation_permission.id)
        self.assertEqual(ai_dev_runtime_config_permission.parent_id, foundation_permission.id)
        self.assertEqual(requirement_analysis_permission.parent_id, requirement_permission.id)
        self.assertEqual(generated_permission.parent_id, requirement_permission.id)
        self.assertEqual(testcase_create_permission.parent_id, module_permission.id)
        self.assertEqual(testcase_create_permission.name, '新建用例')
        self.assertEqual(testcase_create_permission.item_type, 'button')
        self.assertEqual(testcase_create_permission.route_path, '/ai-generation/testcases/create')
        self.assertEqual(testcase_create_permission.sort_order, 55)
        self.assertTrue(testcase_create_permission.is_active)
        self.assertEqual(ai_dev_tasks_permission.parent_id, development_permission.id)
        self.assertEqual(workflow_workbench_permission.parent_id, development_permission.id)
        self.assertEqual(ai_dev_build_config_permission.parent_id, operations_permission.id)
        self.assertEqual(deployment_targets_permission.parent_id, operations_permission.id)
        self.assertEqual(deployment_templates_permission.parent_id, operations_permission.id)
        self.assertEqual(build_artifacts_permission.parent_id, operations_permission.id)
        self.assertEqual(deployment_executions_permission.parent_id, operations_permission.id)
        self.assertEqual(rollback_records_permission.parent_id, operations_permission.id)
        self.assertEqual(workshop_permission.parent_id, module_permission.id)
        self.assertTrue(workshop_permission.is_active)
        self.assertEqual(ai_dev_test_tool_config_permission.parent_id, tools_permission.id)
        self.assertEqual(prompt_permission.parent_id, tools_permission.id)
        self.assertEqual(skill_permission.parent_id, tools_permission.id)
        self.assertEqual(agent_permission.parent_id, tools_permission.id)
        self.assertEqual(flow_permission.parent_id, tools_permission.id)
        self.assertEqual(mcp_permission.parent_id, tools_permission.id)
        self.assertEqual(marketplace_permission.parent_id, tools_permission.id)
        self.assertEqual(ai_dev_llm_config_permission.parent_id, tools_permission.id)
        self.assertEqual(ai_dev_repository_config_permission.parent_id, tools_permission.id)
        self.assertEqual(cicd_permission.parent_id, tools_permission.id)
        expected_workshop_config_permissions = [
            (workshop_models_permission, '/ai-generation/workshop?workshop_tab=models&config_tab=llm'),
            (workshop_test_tools_permission, '/ai-generation/workshop?workshop_tab=test-tools&config_tab=test-tools'),
            (workshop_ui_env_permission, '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env'),
            (workshop_integrations_permission, '/ai-generation/workshop?workshop_tab=integrations&config_tab=git'),
            (workshop_notifications_permission, '/ai-generation/workshop?workshop_tab=integrations&config_tab=notifications'),
        ]
        for permission, route_path in expected_workshop_config_permissions:
            self.assertEqual(permission.parent_id, workshop_permission.id)
            self.assertEqual(permission.route_path, route_path)
            self.assertTrue(permission.is_active)
        self.assertEqual(projects_permission.route_path, '/ai-generation/list?tab=projects')
        self.assertEqual(versions_permission.route_path, '/ai-generation/list?tab=versions')
        self.assertEqual(ai_dev_runtime_config_permission.route_path, '/ai-generation/list?tab=ai-dev-runtime-configs')
        for retired_permission in [
            files_permission,
            new_project_blueprints_permission,
            requirement_permission,
            requirement_analysis_permission,
            generated_permission,
            development_permission,
            ai_dev_tasks_permission,
            workflow_workbench_permission,
            defect_permission,
            operations_permission,
            ai_dev_build_config_permission,
            deployment_targets_permission,
            deployment_templates_permission,
            build_artifacts_permission,
            deployment_executions_permission,
            rollback_records_permission,
        ]:
            self.assertFalse(retired_permission.is_active)
            self.assertEqual(retired_permission.route_path, '/ai-generation/codex-chat')
        for retired_permission in [
            testing_permission,
            testcase_permission,
            ui_automation_cases_permission,
            reviews_permission,
            review_templates_permission,
            executions_permission,
            reports_permission,
        ]:
            self.assertFalse(retired_permission.is_active)
            self.assertEqual(retired_permission.route_path, '/home')
        for retired_permission in [
            tools_permission,
            ai_dev_test_tool_config_permission,
            prompt_permission,
            skill_permission,
            agent_permission,
            flow_permission,
            mcp_permission,
            marketplace_permission,
            ai_dev_llm_config_permission,
            ai_dev_repository_config_permission,
            cicd_permission,
        ]:
            self.assertFalse(retired_permission.is_active)
            self.assertEqual(retired_permission.route_path, '/ai-generation/workshop')

    def test_home_card_permission_items_exist_for_ui_role_permissions(self):
        home_module_permission = PermissionItem.objects.get(code='module:home')
        home_page_permission = PermissionItem.objects.get(code='menu:home:view')
        ai_home_card_permission = PermissionItem.objects.get(code='menu:home:ai-generation')
        configuration_home_card_permission = PermissionItem.objects.get(code='menu:home:configuration')
        api_home_card_permission = PermissionItem.objects.get(code='menu:home:api-testing')
        ui_home_card_permission = PermissionItem.objects.get(code='menu:home:ui-automation')
        ai_intelligent_home_card_permission = PermissionItem.objects.get(code='menu:home:ai-intelligent-mode')
        manual_home_card_permission = PermissionItem.objects.get(code='menu:home:manual-testcases')
        assistant_home_card_permission = PermissionItem.objects.get(code='menu:home:assistant')
        configuration_module_permission = PermissionItem.objects.get(code='module:configuration')
        ai_model_config_permission = PermissionItem.objects.get(code='menu:configuration:ai-model')
        ui_env_config_permission = PermissionItem.objects.get(code='menu:configuration:ui-env')
        scheduled_task_config_permission = PermissionItem.objects.get(code='menu:configuration:scheduled-task')
        ai_intelligent_config_permission = PermissionItem.objects.get(code='menu:configuration:ai-mode')
        ai_intelligent_config_view_permission = PermissionItem.objects.get(code='button:configuration:ai-mode:view')
        dify_config_permission = PermissionItem.objects.get(code='menu:configuration:dify')
        dify_config_view_permission = PermissionItem.objects.get(code='button:configuration:dify:view')

        self.assertFalse(PermissionItem.objects.filter(code='menu:home:data-factory').exists())
        self.assertEqual(home_page_permission.parent_id, home_module_permission.id)
        self.assertEqual(ai_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(configuration_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(api_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(ui_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(ai_intelligent_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(manual_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(assistant_home_card_permission.parent_id, home_page_permission.id)
        self.assertEqual(ai_home_card_permission.route_path, '/ai-generation/list')
        self.assertFalse(configuration_home_card_permission.is_active)
        self.assertEqual(configuration_home_card_permission.route_path, '/ai-generation/workshop?workshop_tab=models&config_tab=llm')
        self.assertFalse(configuration_module_permission.is_active)
        self.assertEqual(configuration_module_permission.route_path, '/ai-generation/workshop')
        self.assertFalse(ai_model_config_permission.is_active)
        self.assertEqual(ai_model_config_permission.route_path, '/ai-generation/workshop?workshop_tab=models&config_tab=llm')
        self.assertFalse(ui_env_config_permission.is_active)
        self.assertEqual(ui_env_config_permission.route_path, '/ai-generation/workshop?workshop_tab=test-tools&config_tab=ui-env')
        self.assertFalse(scheduled_task_config_permission.is_active)
        self.assertEqual(scheduled_task_config_permission.route_path, '/ai-generation/workshop?workshop_tab=integrations&config_tab=notifications')
        self.assertFalse(api_home_card_permission.is_active)
        self.assertEqual(api_home_card_permission.route_path, '/home')
        self.assertFalse(ui_home_card_permission.is_active)
        self.assertEqual(ui_home_card_permission.route_path, '/home')
        self.assertFalse(ai_intelligent_home_card_permission.is_active)
        self.assertEqual(ai_intelligent_home_card_permission.route_path, '/home')
        self.assertEqual(manual_home_card_permission.route_path, '/manual-testcases/list')
        self.assertFalse(assistant_home_card_permission.is_active)
        self.assertEqual(assistant_home_card_permission.route_path, '/home')
        self.assertFalse(ai_intelligent_config_permission.is_active)
        self.assertEqual(ai_intelligent_config_permission.route_path, '/ai-generation/workshop?workshop_tab=models&config_tab=llm')
        self.assertFalse(ai_intelligent_config_view_permission.is_active)
        self.assertFalse(dify_config_permission.is_active)
        self.assertEqual(dify_config_permission.route_path, '/ai-generation/workshop?workshop_tab=models&config_tab=llm')
        self.assertFalse(dify_config_view_permission.is_active)
        self.assertFalse(PermissionItem.objects.get(code='module:api-testing').is_active)
        self.assertFalse(PermissionItem.objects.get(code='menu:api-testing:projects').is_active)
        self.assertFalse(PermissionItem.objects.get(code='module:ui-automation').is_active)
        self.assertFalse(PermissionItem.objects.get(code='menu:ui-automation:test-cases').is_active)
        self.assertFalse(PermissionItem.objects.get(code='module:ai-intelligent-mode').is_active)
        self.assertFalse(PermissionItem.objects.get(code='menu:ai-intelligent-mode:cases').is_active)

    def test_page_view_permissions_exist_under_page_menus(self):
        expected_view_permissions = [
            ('button:ai-generation:workshop-models:view', 'menu:ai-generation:workshop-models'),
            ('button:ai-generation:workshop:view', 'menu:ai-generation:workshop'),
            ('button:manual-testcases:projects:view', 'menu:manual-testcases:projects'),
            ('button:manual-testcases:permissions:view', 'menu:manual-testcases:permissions'),
            (
                'button:manual-testcases:permissions:permission-catalog:view',
                'menu:manual-testcases:permissions:permission-catalog',
            ),
            ('button:manual-testcases:snapshots:view', 'menu:manual-testcases:snapshots'),
        ]

        for view_code, parent_code in expected_view_permissions:
            with self.subTest(view_code=view_code):
                view_permission = PermissionItem.objects.get(code=view_code)
                parent_permission = PermissionItem.objects.get(code=parent_code)
                self.assertEqual(view_permission.name, '查看')
                self.assertEqual(view_permission.item_type, 'button')
                self.assertEqual(view_permission.parent_id, parent_permission.id)
                self.assertEqual(view_permission.sort_order, 5)
                self.assertTrue(view_permission.is_active)
        self.assertFalse(PermissionItem.objects.get(code='button:api-testing:projects:view').is_active)
        self.assertFalse(PermissionItem.objects.get(code='button:ui-automation:test-cases:view').is_active)
        self.assertFalse(PermissionItem.objects.get(code='button:ai-generation:ai-dev-tasks:view').is_active)
        self.assertFalse(PermissionItem.objects.get(code='button:ai-intelligent-mode:cases:view').is_active)
        for retired_configuration_view_code in [
            'button:configuration:ai-model:view',
            'button:configuration:ui-env:view',
            'button:configuration:scheduled-task:view',
        ]:
            self.assertFalse(PermissionItem.objects.get(code=retired_configuration_view_code).is_active)
        for retired_ai_testing_view_code in [
            'button:ai-generation:testing:view',
            'button:ai-generation:testcases:view',
            'button:ai-generation:ui-automation-cases:view',
            'button:ai-generation:reviews:view',
            'button:ai-generation:review-templates:view',
            'button:ai-generation:executions:view',
            'button:ai-generation:reports:view',
        ]:
            self.assertFalse(PermissionItem.objects.get(code=retired_ai_testing_view_code).is_active)

    def test_non_staff_user_cannot_create_permission_item(self):
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            '/api/auth/permission-items/',
            {
                'name': '受限权限',
                'code': 'button:test:forbidden',
                'item_type': 'button',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_returns_effective_permission_codes_for_role_member(self):
        granted_permission = PermissionItem.objects.create(
            name='Granted Permission',
            code='menu:test:granted',
            item_type='menu',
            route_path='/test/granted',
            sort_order=1200,
        )
        self.grant_role_permissions(self.member_user, granted_permission)
        self.client.force_authenticate(self.member_user)

        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['effective_permission_codes'], ['menu:test:granted'])

    def test_non_staff_user_with_permission_item_create_code_can_create_permission_item(self):
        create_permission = PermissionItem.objects.get(code='button:manual-testcases:permissions:create')
        self.grant_role_permissions(self.member_user, create_permission)
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            '/api/auth/permission-items/',
            {
                'name': 'Granted Button Permission',
                'code': 'button:test:granted-create',
                'item_type': 'button',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PermissionItem.objects.filter(code='button:test:granted-create').exists())

    def test_staff_user_can_create_role_with_members(self):
        self.client.force_authenticate(self.staff_user)

        response = self.client.post(
            '/api/auth/roles/',
            {
                'name': 'Platform Role',
                'member_ids': [self.member_user.id, self.other_user.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        role = Role.objects.get(name='Platform Role')
        self.assertEqual(list(role.members.order_by('id').values_list('id', flat=True)), [self.member_user.id, self.other_user.id])
        self.assertEqual(
            list(role.role_memberships.order_by('user_id').values_list('user_id', 'tags')),
            [(self.member_user.id, []), (self.other_user.id, [])],
        )

    def test_staff_user_can_manage_role_members(self):
        role = Role.objects.create(name='Editable Role')
        self.client.force_authenticate(self.staff_user)

        add_response = self.client.post(
            f'/api/auth/roles/{role.id}/members/',
            {'user_id': self.other_user.id, 'tags': ['核心', '冒烟', '核心']},
            format='json',
        )
        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list(role.members.values_list('id', flat=True)), [self.other_user.id])
        membership = RoleMembership.objects.get(role=role, user=self.other_user)
        self.assertEqual(membership.tags, ['核心', '冒烟'])
        self.assertEqual(add_response.data['member']['tags'], ['核心', '冒烟'])

        list_response = self.client.get(f'/api/auth/roles/{role.id}/members/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['tags'], ['核心', '冒烟'])

        update_response = self.client.patch(
            f'/api/auth/roles/{role.id}/members/{self.other_user.id}/',
            {'user_id': self.member_user.id, 'tags': ['负责人', '回归']},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(role.members.values_list('id', flat=True)), [self.member_user.id])
        self.assertFalse(RoleMembership.objects.filter(role=role, user=self.other_user).exists())
        self.assertEqual(RoleMembership.objects.get(role=role, user=self.member_user).tags, ['负责人', '回归'])
        self.assertEqual(update_response.data['member']['tags'], ['负责人', '回归'])

        relabel_response = self.client.patch(
            f'/api/auth/roles/{role.id}/members/{self.member_user.id}/',
            {'user_id': self.member_user.id, 'tags': ['主责', '接口']},
            format='json',
        )
        self.assertEqual(relabel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(RoleMembership.objects.get(role=role, user=self.member_user).tags, ['主责', '接口'])

        delete_response = self.client.delete(
            f'/api/auth/roles/{role.id}/members/{self.member_user.id}/'
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(role.members.count(), 0)
        self.assertFalse(RoleMembership.objects.filter(role=role).exists())

    def test_staff_user_can_manage_role_permissions(self):
        role = Role.objects.create(name='Permission Role')
        module_permission = PermissionItem.objects.create(
            name='测试模块',
            code='module:test:permission-module',
            item_type='module',
            sort_order=1000,
        )
        menu_permission = PermissionItem.objects.create(
            name='测试菜单',
            code='menu:test:permission-menu',
            item_type='menu',
            parent=module_permission,
            route_path='/test/permission-menu',
            sort_order=1010,
        )
        action_permission = PermissionItem.objects.create(
            name='测试操作',
            code='action:test:permission-action',
            item_type='action',
            parent=menu_permission,
            sort_order=1020,
        )
        self.client.force_authenticate(self.staff_user)

        save_response = self.client.put(
            f'/api/auth/roles/{role.id}/permissions/',
            {
                'permission_ids': [module_permission.id, menu_permission.id, action_permission.id, menu_permission.id],
            },
            format='json',
        )
        self.assertEqual(save_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(RolePermission.objects.filter(role=role).order_by('permission_item__sort_order').values_list('permission_item_id', flat=True)),
            [module_permission.id, menu_permission.id, action_permission.id],
        )
        self.assertEqual(save_response.data['summary']['module'], 1)
        self.assertEqual(save_response.data['summary']['menu'], 1)
        self.assertEqual(save_response.data['summary']['action'], 1)

        detail_response = self.client.get(f'/api/auth/roles/{role.id}/permissions/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['permission_ids'], [module_permission.id, menu_permission.id, action_permission.id])

        replace_response = self.client.put(
            f'/api/auth/roles/{role.id}/permissions/',
            {
                'permission_ids': [menu_permission.id],
            },
            format='json',
        )
        self.assertEqual(replace_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(RolePermission.objects.filter(role=role).values_list('permission_item_id', flat=True)),
            [menu_permission.id],
        )

    def test_non_staff_user_with_assign_permission_code_can_manage_role_permissions(self):
        target_role = Role.objects.create(name='Target Role')
        assign_permission = PermissionItem.objects.get(code='action:manual-testcases:permissions:assign')
        target_permission = PermissionItem.objects.get(code='menu:manual-testcases:groups')
        self.grant_role_permissions(self.member_user, assign_permission)
        self.client.force_authenticate(self.member_user)

        response = self.client.put(
            f'/api/auth/roles/{target_role.id}/permissions/',
            {
                'permission_ids': [target_permission.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(RolePermission.objects.filter(role=target_role).values_list('permission_item_id', flat=True)),
            [target_permission.id],
        )


class EmailCodeAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.email = 'new-user@example.com'

    def _set_verification_code(self, email, code='123456'):
        from apps.users import email_verification as email_verification_service

        email_verification_service._store_set(
            email_verification_service._code_key(email),
            code,
            email_verification_service.CODE_TTL_SECONDS,
        )
        return code

    def test_send_email_code_returns_success(self):
        response = self.client.post(
            '/api/auth/send-email-code/',
            {'email': self.email},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.email)

    def test_email_code_login_creates_user(self):
        code = self._set_verification_code(self.email)

        response = self.client.post(
            '/api/auth/email-code-login/',
            {'email': self.email, 'code': code},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['created'])
        self.assertIn('access', response.data)
        self.assertTrue(User.objects.filter(email__iexact=self.email).exists())

    def test_email_code_login_for_existing_user(self):
        user = User.objects.create_user(
            username='existing_user',
            email='existing@example.com',
            password='password123456',
        )
        code = self._set_verification_code(user.email)

        response = self.client.post(
            '/api/auth/email-code-login/',
            {'email': user.email, 'code': code},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['created'])
        self.assertEqual(response.data['user']['id'], user.id)

    def test_email_code_login_rejects_invalid_code(self):
        self._set_verification_code(self.email)

        response = self.client.post(
            '/api/auth/email-code-login/',
            {'email': self.email, 'code': '000000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], '验证码错误或已过期')
