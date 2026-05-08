param(
    [string]$RepoPath = "E:\AI-news"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    & git @args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Set-Location -LiteralPath $RepoPath

Invoke-Git fetch origin main:refs/remotes/origin/main
Invoke-Git rebase origin/main

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

Invoke-Git add .github/automation-trigger.txt

& git diff --cached --quiet
$diffExitCode = $LASTEXITCODE
if ($diffExitCode -eq 1) {
    Invoke-Git commit -m "ci: trigger daily ai news"
    Invoke-Git push origin main
} elseif ($diffExitCode -ne 0) {
    exit $diffExitCode
}
