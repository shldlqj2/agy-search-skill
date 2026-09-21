[CmdletBinding()]
param(
    [string]$Target,
    [switch]$DryRun,
    [switch]$NoBackup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SourceRoot = Join-Path $PSScriptRoot '.agents\skills'
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
if ([string]::IsNullOrWhiteSpace($Target)) {
    $Target = Join-Path $CodexRoot 'skills'
}
$Target = [System.IO.Path]::GetFullPath($Target)
$UnsafeTargets = @(
    [System.IO.Path]::GetPathRoot($Target),
    [System.IO.Path]::GetFullPath($HOME),
    [System.IO.Path]::GetFullPath($CodexRoot)
)
if ($UnsafeTargets -contains $Target) {
    throw "Refusing unsafe target directory: $Target"
}
$Skills = @('agy-search', 'agy-search-verifier')

foreach ($Skill in $Skills) {
    $SourceDir = Join-Path $SourceRoot $Skill
    $SkillFile = Join-Path $SourceDir 'SKILL.md'
    if (-not (Test-Path -LiteralPath $SkillFile -PathType Leaf)) {
        throw "Missing skill entrypoint: $SkillFile"
    }
    $SkillText = Get-Content -LiteralPath $SkillFile -Raw
    if ($SkillText -notmatch '(?m)^name:\s*\S+' -or $SkillText -notmatch '(?m)^description:\s*\S+') {
        throw "Invalid YAML frontmatter in $SkillFile"
    }
}

if ($DryRun) {
    foreach ($Skill in $Skills) {
        $SourceDir = Join-Path $SourceRoot $Skill
        $Destination = Join-Path $Target $Skill
        Write-Output "Would install $SourceDir -> $Destination"
    }
    exit 0
}

New-Item -ItemType Directory -Path $Target -Force | Out-Null
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($Skill in $Skills) {
    $SourceDir = Join-Path $SourceRoot $Skill
    $Destination = Join-Path $Target $Skill
    $Staging = Join-Path $Target ".$Skill.install.$PID.$([guid]::NewGuid().ToString('N'))"
    $Backup = $null

    Copy-Item -LiteralPath $SourceDir -Destination $Staging -Recurse
    if (-not (Test-Path -LiteralPath (Join-Path $Staging 'SKILL.md') -PathType Leaf)) {
        Remove-Item -LiteralPath $Staging -Recurse -Force
        throw "Staged skill is invalid: $Skill"
    }

    if (Test-Path -LiteralPath $Destination) {
        if ($NoBackup) {
            Remove-Item -LiteralPath $Destination -Recurse -Force
        }
        else {
            $Backup = Join-Path $Target ".$Skill.backup.$Timestamp.$PID"
            Move-Item -LiteralPath $Destination -Destination $Backup
            Write-Output "Backed up existing $Skill to $Backup"
        }
    }

    try {
        Move-Item -LiteralPath $Staging -Destination $Destination
    }
    catch {
        if ($Backup -and (Test-Path -LiteralPath $Backup) -and -not (Test-Path -LiteralPath $Destination)) {
            Move-Item -LiteralPath $Backup -Destination $Destination
        }
        throw
    }
    Write-Output "Installed $Skill to $Destination"
}

if (-not (Get-Command agy -ErrorAction SilentlyContinue)) {
    Write-Warning 'agy is not currently on PATH; the skill is installed but searches cannot run yet.'
}
if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warning 'Python 3 is not currently on PATH; install it before running the search adapter.'
}

Write-Output 'Global installation complete. Restart Codex or reload skills if the new skills are not visible.'
