[CmdletBinding()]
param(
    [string]$Python = 'py',
    [string]$Name = 'agy-search',
    [string]$DataDir,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    if ($env:LOCALAPPDATA) {
        $DataDir = Join-Path $env:LOCALAPPDATA 'agy-search-mcp'
    }
    elseif ($env:XDG_STATE_HOME) {
        $DataDir = Join-Path $env:XDG_STATE_HOME 'agy-search-mcp'
    }
    else {
        $DataDir = Join-Path $HOME '.local\state\agy-search-mcp'
    }
}
if ($Name -notmatch '^[A-Za-z0-9_-]+$') {
    throw 'Name may contain only letters, digits, hyphens, and underscores.'
}

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python executable not found: $Python"
}
& $Python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Python 3.10 or newer is required")'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI is required to register the MCP server.'
}
if (-not (Get-Command agy -ErrorAction SilentlyContinue)) {
    throw 'agy is not on PATH; install and authenticate AGY before registering.'
}

$DataDir = [System.IO.Path]::GetFullPath($DataDir)
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$ConfigPath = Join-Path $CodexRoot 'config.toml'
& codex mcp get $Name *> $null
if ($LASTEXITCODE -eq 0) {
    throw "MCP server '$Name' already exists. Remove or rename it before registering this one."
}

if ($DryRun) {
    Write-Output "Would install package: $Python -m pip install --user --upgrade $PSScriptRoot"
    Write-Output "Would create state directory: $DataDir"
    Write-Output "Would register: codex mcp add $Name --env AGY_SEARCH_MCP_DATA_DIR=$DataDir -- $Python -m agy_search_mcp.server"
    Write-Output "Would set startup_timeout_sec=30 and tool_timeout_sec=660 in $ConfigPath"
    exit 0
}

New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
& $Python -m pip install --user --upgrade $PSScriptRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& codex mcp add $Name --env "AGY_SEARCH_MCP_DATA_DIR=$DataDir" -- $Python -m agy_search_mcp.server
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Content = [System.IO.File]::ReadAllText($ConfigPath)
$Pattern = "(?m)^\[mcp_servers\.$([regex]::Escape($Name))\]\r?$"
$Newline = if ($Content.Contains("`r`n")) { "`r`n" } else { "`n" }
$Replacement = '${0}' + $Newline + 'startup_timeout_sec = 30' + $Newline + 'tool_timeout_sec = 660'
$Updated = [regex]::Replace($Content, $Pattern, $Replacement, 1)
if ($Updated -eq $Content) {
    throw "Could not locate the new MCP section in $ConfigPath"
}
[System.IO.File]::WriteAllText($ConfigPath, $Updated, [System.Text.UTF8Encoding]::new($false))

Write-Output "Installed and registered MCP server '$Name'. Restart Codex or start a new session before using it."
Write-Output 'Existing agy-search skills were left untouched; remove them only after confirming the MCP server works.'
