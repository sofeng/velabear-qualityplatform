import io
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


@dataclass(frozen=True)
class SeedGroup:
    key: str
    description: str
    model_labels: tuple[str, ...]
    notes: tuple[str, ...] = ()


SEED_GROUPS = (
    SeedGroup(
        key="01_users_permissions",
        description="Users, Django auth groups, custom roles, and custom permissions",
        model_labels=(
            "auth.Group",
            "users.User",
            "users.UserProfile",
            "users.Role",
            "users.RoleMembership",
            "users.PermissionItem",
            "users.RolePermission",
        ),
        notes=(
            "Includes login accounts and permission dependencies required by the selected init scope.",
            "User passwords are exported as hashed values from the current database.",
        ),
    ),
    SeedGroup(
        key="02_projects_versions",
        description="Projects, project members, and versions",
        model_labels=(
            "projects.Project",
            "projects.ProjectMember",
            "versions.Version",
        ),
        notes=(
            "Version fixtures include the implicit versions_projects many-to-many relation.",
        ),
    ),
    SeedGroup(
        key="03_quality_analysis",
        description="JIRA interface configs and shared JIRA browse prefix settings",
        model_labels=(
            "quality_analysis.QualityAnalysisSettings",
            "quality_analysis.JiraInterfaceConfig",
            "quality_analysis.JiraRequirementInterfaceConfig",
        ),
        notes=(
            "Covers the database-backed JIRA browse prefix and current JIRA config records.",
            "Current synced JIRA bug/requirement records are intentionally excluded from init seed scope.",
        ),
    ),
    SeedGroup(
        key="04_defect_notifications",
        description="Defect email SMTP/template settings",
        model_labels=(
            "defects.DefectEmailConfig",
        ),
        notes=(
            "Includes SMTP settings and the four defect email templates.",
        ),
    ),
    SeedGroup(
        key="05_manual_catalog",
        description="Manual testcase directory tree and linked mindmaps",
        model_labels=(
            "testcases.ManualTestCaseCategory",
            "testcases.ManualTestCaseMindmap",
        ),
        notes=(
            "Current database mainly contains directory tree records; mindmaps are exported too for completeness.",
        ),
    ),
    SeedGroup(
        key="06_ai_development",
        description="Deployment targets and AI development baseline configuration records",
        model_labels=(
            "deployments.DeploymentTarget",
            "ai_development.AIDevelopmentRepositoryConfig",
            "ai_development.AIDevelopmentLLMConfig",
            "ai_development.AIDevelopmentTestToolConfig",
            "ai_development.AIDevelopmentRuntimeConfig",
            "ai_development.AIDevelopmentBuildConfig",
            "ai_development.AIDevelopmentConfig",
        ),
        notes=(
            "Covers reusable deployment targets referenced by AI development runtime configs.",
            "Exports only baseline AI development configuration records; tasks and execution history remain excluded.",
        ),
    ),
)


REDACTION_RULES = {
    "quality_analysis.jirainterfaceconfig": {
        "request_headers": {},
        "request_body": "",
    },
    "quality_analysis.jirarequirementinterfaceconfig": {
        "request_headers": {},
        "request_body": "",
    },
    "defects.defectemailconfig": {
        "password": "",
    },
}


class Command(BaseCommand):
    help = "Export the initialization seed scope into Django fixture files and inventory manifests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Output directory. Defaults to .seed_exports/init-seed-<timestamp>.",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias used for export.",
        )
        parser.add_argument(
            "--include-media",
            action="store_true",
            help="Copy the local media directory into the export bundle.",
        )
        parser.add_argument(
            "--redact-secrets",
            action="store_true",
            help="Blank selected sensitive fields such as SMTP password and JIRA request headers/body.",
        )
        parser.add_argument(
            "--skip-combined-fixture",
            action="store_true",
            help="Do not generate the combined seed_data.json file.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        redact_secrets = bool(options["redact_secrets"])
        include_media = bool(options["include_media"])
        skip_combined_fixture = bool(options["skip_combined_fixture"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output = (
            Path(options["output"]).expanduser()
            if options["output"]
            else Path(settings.BASE_DIR) / ".seed_exports" / f"init-seed-{timestamp}"
        )
        if not base_output.is_absolute():
            base_output = Path(settings.BASE_DIR) / base_output
        output_dir = base_output.resolve()
        fixtures_dir = output_dir / "fixtures"

        fixtures_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f"Exporting init seed into: {output_dir}"))

        groups_payload = []
        combined_objects = []
        total_object_count = 0

        for group in SEED_GROUPS:
            objects = self._dump_group(group, database=database)
            if redact_secrets:
                objects = self._apply_redaction(objects)

            fixture_path = fixtures_dir / f"{group.key}.json"
            self._write_json(fixture_path, objects)

            model_entries = self._build_model_entries(group, database=database)
            object_count = len(objects)
            total_object_count += object_count
            combined_objects.extend(objects)

            groups_payload.append(
                {
                    "key": group.key,
                    "description": group.description,
                    "fixture": self._relative_to_output(fixture_path, output_dir),
                    "object_count": object_count,
                    "models": model_entries,
                    "notes": list(group.notes),
                }
            )

            self.stdout.write(f"  - {group.key}: {object_count} objects")

        combined_fixture_path = None
        if not skip_combined_fixture:
            combined_fixture_path = output_dir / "seed_data.json"
            self._write_json(combined_fixture_path, combined_objects)
            self.stdout.write(f"  - combined fixture: {self._relative_to_output(combined_fixture_path, output_dir)}")

        media_summary = None
        if include_media:
            media_summary = self._copy_media(output_dir)
            self.stdout.write(
                f"  - media copy: {media_summary['file_count']} files, {media_summary['directory_count']} directories"
            )

        inventory = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "database": database,
            "output_dir": str(output_dir),
            "redact_secrets": redact_secrets,
            "include_media": include_media,
            "groups": groups_payload,
            "totals": {
                "group_count": len(SEED_GROUPS),
                "object_count": total_object_count,
                "model_count": sum(len(group["models"]) for group in groups_payload),
            },
            "combined_fixture": (
                self._relative_to_output(combined_fixture_path, output_dir) if combined_fixture_path else None
            ),
            "media": media_summary,
            "warnings": [
                "This export contains current database state for the selected init scope.",
                "Do not share the bundle externally unless you understand the secrets and account data it contains.",
                "Load into an empty database after migrations. This export is not intended for merge-style imports.",
            ],
        }

        inventory_json_path = output_dir / "seed_inventory.json"
        inventory_md_path = output_dir / "seed_inventory.md"
        self._write_json(inventory_json_path, inventory)
        inventory_md_path.write_text(self._render_inventory_markdown(inventory), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Init seed export completed."))
        self.stdout.write(f"Inventory JSON: {inventory_json_path}")
        self.stdout.write(f"Inventory MD:   {inventory_md_path}")

    def _dump_group(self, group: SeedGroup, *, database: str) -> list[dict]:
        buffer = io.StringIO()
        call_command(
            "dumpdata",
            *group.model_labels,
            database=database,
            indent=2,
            stdout=buffer,
        )
        payload = buffer.getvalue().strip() or "[]"
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Failed to parse dumpdata output for {group.key}: {exc}") from exc
        if not isinstance(data, list):
            raise CommandError(f"Unexpected dumpdata payload for {group.key}: expected JSON list.")
        return data

    def _build_model_entries(self, group: SeedGroup, *, database: str) -> list[dict]:
        entries = []
        for model_label in group.model_labels:
            app_label, model_name = model_label.split(".", 1)
            model = apps.get_model(app_label, model_name)
            if model is None:
                raise CommandError(f"Unknown model label: {model_label}")
            entries.append(
                {
                    "label": model_label,
                    "db_table": model._meta.db_table,
                    "count": model._default_manager.using(database).count(),
                }
            )
        return entries

    def _apply_redaction(self, objects: list[dict]) -> list[dict]:
        redacted = []
        for item in objects:
            updated = {
                "model": item["model"],
                "pk": item["pk"],
                "fields": dict(item.get("fields") or {}),
            }
            for field_name, replacement in REDACTION_RULES.get(updated["model"], {}).items():
                if field_name in updated["fields"]:
                    updated["fields"][field_name] = replacement
            redacted.append(updated)
        return redacted

    def _copy_media(self, output_dir: Path) -> dict:
        source_media = Path(settings.BASE_DIR) / "media"
        if not source_media.exists():
            return {
                "copied": False,
                "source": str(source_media),
                "target": None,
                "file_count": 0,
                "directory_count": 0,
            }

        target_media = output_dir / "media"
        shutil.copytree(source_media, target_media, dirs_exist_ok=True)

        file_count = 0
        directory_count = 0
        for path in target_media.rglob("*"):
            if path.is_file():
                file_count += 1
            elif path.is_dir():
                directory_count += 1

        return {
            "copied": True,
            "source": str(source_media),
            "target": self._relative_to_output(target_media, output_dir),
            "file_count": file_count,
            "directory_count": directory_count,
        }

    @staticmethod
    def _write_json(path: Path, payload):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _relative_to_output(path: Path | None, output_dir: Path) -> str | None:
        if path is None:
            return None
        return str(path.relative_to(output_dir)).replace("\\", "/")

    def _render_inventory_markdown(self, inventory: dict) -> str:
        lines = [
            "# Init Seed Inventory",
            "",
            f"- Generated at: `{inventory['generated_at']}`",
            f"- Database alias: `{inventory['database']}`",
            f"- Combined fixture: `{inventory['combined_fixture'] or 'not generated'}`",
            f"- Secrets redacted: `{inventory['redact_secrets']}`",
            f"- Media copied: `{inventory['include_media']}`",
            "",
            "## Export Scope",
            "",
        ]

        for group in inventory["groups"]:
            lines.append(f"### {group['key']}")
            lines.append("")
            lines.append(group["description"])
            lines.append("")
            lines.append(f"- Fixture: `{group['fixture']}`")
            lines.append(f"- Object count: `{group['object_count']}`")
            for model in group["models"]:
                lines.append(
                    f"- `{model['label']}` -> table `{model['db_table']}` -> `{model['count']}` records"
                )
            for note in group["notes"]:
                lines.append(f"- Note: {note}")
            lines.append("")

        lines.extend(
            [
                "## Import Order",
                "",
                "1. Apply all Django migrations on the target database.",
                "2. Load the exported combined fixture with `python manage.py loaddata <seed_data.json>`.",
                "3. If media was exported, copy the `media/` directory into the deployment media volume.",
                "",
                "## Warnings",
                "",
            ]
        )

        for warning in inventory["warnings"]:
            lines.append(f"- {warning}")

        lines.append("")
        return "\n".join(lines)
