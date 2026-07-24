from django.core.management.base import BaseCommand

from apps.testcases.models import ManualTestCaseMindmap
from apps.testcases.xmind_requirement_import import strip_module_resource_markers


class Command(BaseCommand):
    help = '移除所有手工测试脑图中 module 类型节点的显示标记(resource)'

    def add_arguments(self, parser):
        parser.add_argument('--mindmap-ids', nargs='*', type=int, help='指定要处理的脑图ID；默认处理全部')
        parser.add_argument('--dry-run', action='store_true', help='仅检查，不写入数据库')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        mindmap_ids = options.get('mindmap_ids') or []

        queryset = ManualTestCaseMindmap.objects.all().order_by('id')
        if mindmap_ids:
            queryset = queryset.filter(id__in=mindmap_ids)

        total_mindmaps = 0
        total_nodes = 0

        for mindmap in queryset:
            total_mindmaps += 1
            before_count = self._count_module_markers(mindmap.mindmap_data or {})
            if not before_count:
                self.stdout.write(f'SKIP ID={mindmap.id} {mindmap.name} moduleMarkers=0')
                continue

            normalized = strip_module_resource_markers(mindmap.mindmap_data or {})
            after_count = self._count_module_markers(normalized)
            total_nodes += before_count - after_count

            if not dry_run:
                mindmap.mindmap_data = normalized
                mindmap.save(update_fields=['mindmap_data', 'updated_at'])

            action = 'DRY-RUN' if dry_run else 'UPDATED'
            self.stdout.write(
                f'{action} ID={mindmap.id} {mindmap.name} moduleMarkers {before_count} -> {after_count}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'dry-run 完成，检查脑图 {total_mindmaps} 条，可移除模块标记 {total_nodes} 个。'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'处理完成，脑图 {total_mindmaps} 条，已移除模块标记 {total_nodes} 个。'
            ))

    def _count_module_markers(self, mindmap_data):
        count = 0
        stack = [((mindmap_data or {}).get('root') or {})]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue

            data = node.get('data') or {}
            if data.get('nodeType') == 'module' and data.get('resource'):
                count += 1

            stack.extend(node.get('children') or [])
        return count
