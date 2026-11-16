# Work Companion - one-line installer (Windows PowerShell)
#
# Usage:
#   .\install.ps1                           Install to $HOME\.claude\skills\work-companion
#   .\install.ps1 -Target codex             Install to $HOME\.codex\skills\work-companion
#   .\install.ps1 -Target all               Install to every recognized harness
#   .\install.ps1 -Dir C:\custom\skills     Install to a custom skills directory
#   .\install.ps1 -Force                    Overwrite when the target exists
#   .\install.ps1 -WithScripts              Also install the optional ledger script
#
# Remote one-liner (repo must be public, or set $env:GITHUB_TOKEN):
#   irm https://raw.githubusercontent.com/EDboy-616/work-companion/main/install.ps1 | iex
#
# Messages are ASCII-only on purpose: Windows PowerShell 5.1 reads UTF-8
# script files as ANSI, which would corrupt non-ASCII output.

[CmdletBinding()]
param(
    [ValidateSet('claude-code', 'codex', 'cursor', 'all', 'dir')]
    [string]$Target = 'claude-code',
    [string]$Dir = '',
    [switch]$Force,
    [switch]$WithScripts
)

$ErrorActionPreference = 'Stop'

$Repo      = 'EDboy-616/work-companion'
$Branch    = 'main'
$SkillName = 'work-companion'

# -Dir implies the custom-directory target.
if (-not [string]::IsNullOrWhiteSpace($Dir)) { $Target = 'dir' }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalSrc  = Join-Path $ScriptDir "skills\$SkillName\SKILL.md"

function Get-SkillsDir([string]$name) {
    switch ($name) {
        'claude-code' { Join-Path $HOME '.claude\skills' }
        'codex'       { Join-Path $HOME '.codex\skills' }
        'cursor'      { Join-Path $HOME '.cursor\skills' }
        'dir'         { $Dir }
        default       { '' }
    }
}

function Get-RemoteContent([string]$relativePath) {
    $url = "https://raw.githubusercontent.com/$Repo/$Branch/$relativePath"
    $headers = @{}
    if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $($env:GITHUB_TOKEN)" }
    return (Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing).Content
}

function Get-SkillContent {
    if (Test-Path $LocalSrc) {
        return Get-Content -Raw -Encoding UTF8 $LocalSrc
    }
    return Get-RemoteContent "skills/$SkillName/SKILL.md"
}

function Install-Script([string]$dest) {
    $scriptDestDir = Join-Path $dest 'scripts'
    $scriptDest = Join-Path $scriptDestDir 'ledger.py'
    $localScript = Join-Path $ScriptDir "skills\$SkillName\scripts\ledger.py"
    try {
        New-Item -ItemType Directory -Force -Path $scriptDestDir | Out-Null
        if (Test-Path $localScript) {
            Copy-Item -Force $localScript $scriptDest
        } else {
            $content = Get-RemoteContent "skills/$SkillName/scripts/ledger.py"
            [System.IO.File]::WriteAllText($scriptDest, $content, (New-Object System.Text.UTF8Encoding $false))
        }
        Write-Host "Installed script: $scriptDest"
    } catch {
        Write-Host "Warning: optional script install failed; SKILL.md still works without it."
    }
}

function Install-One([string]$targetName) {
    $skillsDir = Get-SkillsDir $targetName
    if ([string]::IsNullOrWhiteSpace($skillsDir)) { throw "Unknown target: $targetName" }

    $dest     = Join-Path $skillsDir $SkillName
    $destFile = Join-Path $dest 'SKILL.md'

    if ((Test-Path $destFile) -and (-not $Force)) {
        Write-Host "Exists, skipped: $destFile (use -Force to overwrite)"
        if ($WithScripts) {
            Install-Script $dest
        }
        return
    }

    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $content = Get-SkillContent
    [System.IO.File]::WriteAllText($destFile, $content, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "Installed: $destFile"
    if ($WithScripts) {
        Install-Script $dest
    }
}

if ($Target -eq 'all') {
    Install-One 'claude-code'
    Install-One 'codex'
    Install-One 'cursor'
} else {
    Install-One $Target
}

Write-Host ""
Write-Host "Done. Restart the agent for the skill to take effect."
Write-Host "Uninstall: delete the skills\$SkillName directory shown above."
