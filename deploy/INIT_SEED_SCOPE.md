# Init Seed Scope

This repository now provides a dedicated init-seed export command:

```powershell
python manage.py export_init_seed
```

Windows wrapper:

```powershell
.\deploy\export_init_seed.ps1
```

## Exported Scope

The command exports the current init-seed scope in grouped Django fixtures.

1. `01_users_permissions`
   - `auth.Group`
   - `users.User`
   - `users.UserProfile`
   - `users.Role`
   - `users.RoleMembership`
   - `users.PermissionItem`
   - `users.RolePermission`

2. `02_projects_versions`
   - `projects.Project`
   - `projects.ProjectMember`
   - `versions.Version`

3. `03_quality_analysis`
   - `quality_analysis.QualityAnalysisSettings`
   - `quality_analysis.JiraInterfaceConfig`
   - `quality_analysis.JiraRequirementInterfaceConfig`

4. `04_defect_notifications`
   - `defects.DefectEmailConfig`

5. `05_manual_catalog`
   - `testcases.ManualTestCaseCategory`
   - `testcases.ManualTestCaseMindmap`

## Generated Files

The export bundle contains:

- grouped fixture files under `fixtures/`
- combined fixture `seed_data.json` unless `--skip-combined-fixture` is used
- machine-readable inventory `seed_inventory.json`
- readable checklist `seed_inventory.md`
- optional `media/` copy when `--include-media` is used

## Usage Examples

Default export:

```powershell
python manage.py export_init_seed
```

Export to a fixed directory:

```powershell
python manage.py export_init_seed --output .seed_exports/current
```

Export with media:

```powershell
python manage.py export_init_seed --include-media
```

Redact selected secrets for sharing:

```powershell
python manage.py export_init_seed --redact-secrets
```

## Import Reminder

Load the export only into a migrated target database:

```powershell
python manage.py loaddata <path-to-seed_data.json>
```

If media was exported, copy the exported `media/` directory into the target media volume.
