param(
    [string]$RepoPath = "E:\AI-news"
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $RepoPath

git pull --ff-only origin main

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$reportDate = Get-Date -Format "yyyy-MM-dd"
@(
    "REPORT_DATE=$reportDate"
    "TRIGGERED_AT=$timestamp"
) | Set-Content -LiteralPath ".github/automation-trigger.txt" -Encoding UTF8

git add .github/automation-trigger.txt

if (-not (git diff --cached --quiet)) {
    git commit -m "ci: trigger daily ai news"
    git push origin main
}
