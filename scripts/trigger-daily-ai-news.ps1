param(
    [string]$RepoPath = "C:\Users\Administrator\Documents\Codex\AI-News"
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $RepoPath

git pull --ff-only origin main

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
Set-Content -LiteralPath ".github/automation-trigger.txt" -Value "Triggered at $timestamp" -Encoding UTF8

git add .github/automation-trigger.txt

if (-not (git diff --cached --quiet)) {
    git commit -m "ci: trigger daily ai news"
    git push origin main
}
