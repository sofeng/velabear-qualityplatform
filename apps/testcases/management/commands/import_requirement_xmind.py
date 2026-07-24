from django.core.management.base import BaseCommand, CommandError

from apps.testcases.xmind_requirement_import import (
    XMindImportError,
    build_import_context,
    import_requirement_mindmaps,
)


class Command(BaseCommand):
    help = '将“版本号+用户名+测试分析”结构的 XMind 文件按需求拆分导入为多个手工测试脑图'

    def add_arguments(self, parser):
        parser.add_argument('xmind_path', help='XMind 文件路径')
        parser.add_argument('--project-id', type=int, help='目标项目ID，默认根据版本自动推断')
        parser.add_argument('--category-id', type=int, help='目标目录ID，默认使用项目根目录')
        parser.add_argument('--dry-run', action='store_true', help='仅解析并输出结果，不写入数据库')

    def handle(self, *args, **options):
        try:
            context, requirement_items = build_import_context(
                file_path=options['xmind_path'],
                project_id=options.get('project_id'),
                category_id=options.get('category_id'),
            )
            summary = import_requirement_mindmaps(
                context,
                requirement_items,
                dry_run=options.get('dry_run', False),
            )
        except XMindImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            '根节点：{root}；版本：{version}；用户：{user}；项目：{project}；目录：{category}。'.format(
                root=context.root_title,
                version=context.version.name,
                user=context.author.username,
                project=context.project.name,
                category=context.category.name,
            )
        )
        self.stdout.write(f'共识别需求 {summary["total"]} 条。')

        for item in summary['created']:
            label = f'ID={item["id"]}' if item['id'] is not None else 'DRY-RUN'
            jira_key = f' [{item["jira_key"]}]' if item.get('jira_key') else ''
            self.stdout.write(f'  {label}{jira_key} {item["name"]}')

        for item in summary['skipped']:
            self.stdout.write(f'  SKIP ID={item["id"]} {item["name"]} ({item["reason"]})')

        if summary['dry_run']:
            self.stdout.write(self.style.WARNING('dry-run 完成，未写入数据库。'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'导入完成：新增 {len(summary["created"])} 条，跳过 {len(summary["skipped"])} 条。'
            )
        )
