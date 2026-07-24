from django.core.management.base import BaseCommand, CommandError

from apps.projects.models import Project
from apps.testcases.category_import import DEFAULT_ROOT_NAME, import_manual_categories_from_excel


class Command(BaseCommand):
    help = '将Excel中的一二级菜单导入到手工用例目录树中'

    def add_arguments(self, parser):
        parser.add_argument('excel_path', help='Excel文件路径')
        parser.add_argument('--project-id', type=int, help='目标项目ID')
        parser.add_argument('--project-name', help='目标项目名称，未传project-id时使用')
        parser.add_argument('--sheet-name', help='工作表名称，默认取第一个工作表')
        parser.add_argument('--root-name', default=DEFAULT_ROOT_NAME, help='目录树根节点名称')

    def handle(self, *args, **options):
        project = self._resolve_project(options)
        summary = import_manual_categories_from_excel(
            excel_path=options['excel_path'],
            project=project,
            root_name=options['root_name'],
            sheet_name=options.get('sheet_name'),
        )

        self.stdout.write(self.style.SUCCESS(
            f'已导入项目【{project.name}】目录树，根节点ID={summary["root_category_id"]}。'
        ))
        self.stdout.write(
            '一级菜单 {level_1_total} 个，二级菜单 {level_2_total} 个；'
            '新增一级 {created_level_1} 个，新增二级 {created_level_2} 个；'
            '更新一级排序 {updated_level_1} 个，更新二级排序 {updated_level_2} 个。'.format(**summary)
        )

    def _resolve_project(self, options):
        project_id = options.get('project_id')
        project_name = options.get('project_name')

        if project_id:
            project = Project.objects.filter(id=project_id).first()
            if not project:
                raise CommandError(f'未找到项目ID={project_id} 对应的项目')
            return project

        target_name = (project_name or DEFAULT_ROOT_NAME).strip()
        project = Project.objects.filter(name=target_name).order_by('id').first()
        if project:
            return project

        raise CommandError(f'未找到项目名称为【{target_name}】的项目，请改用 --project-id 指定')
