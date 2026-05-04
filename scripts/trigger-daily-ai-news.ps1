param(
    [string]$RepoPath = "E:\AI-news"
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $RepoPath

git pull --ff-only origin main

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$reportDate = Get-Date -Format "yyyy-MM-dd"
$triggerContent = @(
    "REPORT_DATE=$reportDate"
    "TRIGGERED_AT=$timestamp"
) -join [Environment]::NewLine
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) ".github/automation-trigger.txt"),
    $triggerContent + [Environment]::NewLine,
    $utf8NoBom
)

git add .github/automation-trigger.txt

if (-not (git diff --cached --quiet)) {
    git commit -m "ci: trigger daily ai news"
    git push origin main
}
