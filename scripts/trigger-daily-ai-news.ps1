param(
    [string]$RepoPath = "E:\AI-news"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    & git @args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($args -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Invoke-WorkflowDispatch {
    param([string]$ReportDate)

    $credentialInput = "protocol=https`nhost=github.com`npath=Xhuiz/AI-News.git`n`n"
    $credential = $credentialInput | git credential fill
    $token = ($credential | Where-Object { $_ -like "password=*" }) -replace "^password=", ""
    if (-not $token) {
        throw "No GitHub token found in git credential helper."
    }

    $headers = @{
        "User-Agent" = "AI-News-Local-Trigger"
        "Accept" = "application/vnd.github+json"
        "Authorization" = "Bearer $token"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    $body = @{
        ref = "main"
        inputs = @{
            report_date = $ReportDate
        }
    } | ConvertTo-Json -Depth 4

    Invoke-RestMethod `
        -Method Post `
        -Uri "https://api.github.com/repos/Xhuiz/AI-News/actions/workflows/daily-ai-news.yml/dispatches" `
        -Headers $headers `
        -Body $body `
        -ContentType "application/json" | Out-Null
}

Set-Location -LiteralPath $RepoPath

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$reportDate = Get-Date -Format "yyyy-MM-dd"

try {
    Invoke-Git fetch origin main:refs/remotes/origin/main
    Invoke-Git rebase origin/main

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
        throw "git diff --cached --quiet failed with exit code $diffExitCode."
    }
} catch {
    Write-Warning "git trigger failed; dispatched workflow through GitHub API. $($_.Exception.Message)"
    Invoke-WorkflowDispatch -ReportDate $reportDate
    exit 0
}
