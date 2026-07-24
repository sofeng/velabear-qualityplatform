from django.core.management.base import BaseCommand, CommandError

from apps.testcases.models import ManualTestCaseMindmap
from apps.testcases.xmind_requirement_import import (
    XMindImportError,
    build_project_module_name_set,
    normalize_requirement_mindmap_data,
)


class Command(BaseCommand):
    help = '将指定手工测试脑图的节点类型规范化为：根节点=需求，叶子节点=测试点，其他节点=模块'

    def add_arguments(self, parser):
        parser.add_argument('mindmap_ids', nargs='+', type=int, help='要修正的脑图ID列表')
        parser.add_argument('--dry-run', action='store_true', help='仅检查，不写入数据库')

    def handle(self, *args, **options):
        mindmap_ids = options['mindmap_ids']
        dry_run = options.get('dry_run', False)

        mindmaps = list(ManualTestCaseMindmap.objects.filter(id__in=mindmap_ids).order_by('id'))
        found_ids = {item.id for item in mindmaps}
        missing_ids = [item_id for item_id in mindmap_ids if item_id not in found_ids]
        if missing_ids:
            raise CommandError(f'未找到脑图ID：{", ".join(str(item) for item in missing_ids)}')

        for mindmap in mindmaps:
            try:
                normalized = normalize_requirement_mindmap_data(
                    mindmap.mindmap_data or {},
                    module_name_set=build_project_module_name_set(mindmap.project),
                )
            except XMindImportError as exc:
                raise CommandError(f'脑图ID={mindmap.id} 处理失败：{exc}') from exc

            root = normalized.get('root') or {}
            root_type = (root.get('data') or {}).get('nodeType')

            if not dry_run:
                mindmap.mindmap_data = normalized
                mindmap.save(update_fields=['mindmap_data', 'updated_at'])

            action = 'DRY-RUN' if dry_run else 'UPDATED'
            self.stdout.write(
                f'{action} ID={mindmap.id} {mindmap.name} rootType={root_type}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING('dry-run 完成，未写入数据库。'))
        else:
            self.stdout.write(self.style.SUCCESS(f'已修正 {len(mindmaps)} 条脑图。'))
