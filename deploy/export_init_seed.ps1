param(
    [string]$Output = "",
    [string]$Database = "default",
    [switch]$IncludeMedia,
    [switch]$RedactSecrets,
    [switch]$SkipCombinedFixture
)

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$arguments = @("manage.py", "export_init_seed", "--database", $Database)

if ($Output) {
    $arguments += @("--output", $Output)
}
if ($IncludeMedia) {
    $arguments += "--include-media"
}
if ($RedactSecrets) {
    $arguments += "--redact-secrets"
}
if ($SkipCombinedFixture) {
    $arguments += "--skip-combined-fixture"
}

python @arguments
