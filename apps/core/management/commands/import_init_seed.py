import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import an init-seed bundle exported by export_init_seed."

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            nargs="?",
            default="",
            help="Path to a bundle directory or a seed_data.json fixture file.",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias used for import.",
        )
        parser.add_argument(
            "--copy-media",
            action="store_true",
            help="Copy bundle media/ into MEDIA_ROOT after loaddata succeeds.",
        )
        parser.add_argument(
            "--skip-loaddata",
            action="store_true",
            help="Skip fixture import and only run optional media copy.",
        )
        parser.add_argument(
            "--strict-fields",
            action="store_true",
            help="Fail when the fixture contains fields that no longer exist on the model.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        copy_media = bool(options["copy_media"])
        skip_loaddata = bool(options["skip_loaddata"])
        strict_fields = bool(options["strict_fields"])

        bundle_dir, fixture_path, media_dir = self._resolve_bundle_paths(options["source"])

        self.stdout.write(self.style.SUCCESS(f"Using init-seed bundle: {bundle_dir}"))

        if not skip_loaddata:
            if not fixture_path.exists():
                raise CommandError(f"Seed fixture not found: {fixture_path}")
            self.stdout.write(f"Loading fixture into database `{database}`: {fixture_path}")
            call_options = {"database": database}
            if not strict_fields:
                call_options["ignorenonexistent"] = True
            call_command("loaddata", str(fixture_path), **call_options)

        if copy_media:
            if not media_dir.exists():
                self.stdout.write("Bundle media directory not found, skipping media copy.")
            else:
                target_media_root = Path(settings.MEDIA_ROOT)
                target_media_root.mkdir(parents=True, exist_ok=True)
                shutil.copytree(media_dir, target_media_root, dirs_exist_ok=True)
                self.stdout.write(f"Copied media into: {target_media_root}")

        self.stdout.write(self.style.SUCCESS("Init seed import completed."))

    def _resolve_bundle_paths(self, source: str):
        if source:
            resolved = Path(source).expanduser()
            if not resolved.is_absolute():
                resolved = Path(settings.BASE_DIR) / resolved
        else:
            resolved = Path(settings.BASE_DIR) / "deploy" / "init-seed"

        resolved = resolved.resolve()

        if resolved.is_dir():
            fixture_path = resolved / "seed_data.json"
            media_dir = resolved / "media"
            return resolved, fixture_path, media_dir

        if resolved.is_file():
            return resolved.parent, resolved, resolved.parent / "media"

        raise CommandError(f"Init-seed source not found: {resolved}")
