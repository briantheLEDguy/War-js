param(
    [switch]$Apply,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../../artifacts/collaboration')
)
$ErrorActionPreference = 'Stop'
# Deliberately targets Unreal executable rules only; never queries or changes VPN settings.
$allowedPrograms = @(
    (Join-Path $env:LOCALAPPDATA 'UnrealEngine\Common\UnrealTrace\Bin\00010018\UnrealTraceServer.exe'),
    'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe',
    'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe',
    'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe'
)
$candidates = @(Get-NetFirewallRule -PolicyStore PersistentStore -Enabled True -Direction Inbound -Action Allow |
    Where-Object { $_.DisplayName -in @('UnrealEditor', 'UnrealPak', 'unrealtraceserver.exe') } |
    ForEach-Object {
        $rule = $_
        $application = $rule | Get-NetFirewallApplicationFilter
        $address = $rule | Get-NetFirewallAddressFilter
        if ($application.Program -in $allowedPrograms -and 'Any' -in $address.RemoteAddress) {
            [pscustomobject]@{ Name = $rule.Name; Program = $application.Program; Enabled = [string]$rule.Enabled; Profile = [string]$rule.Profile }
        }
    })
if (!$Apply) { $candidates | ConvertTo-Json -Depth 4; exit 0 }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'An elevated Windows administrator session is required to disable these firewall rules.'
}
$directory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $directory -Force | Out-Null
$backup = Join-Path $directory ('host-unreal-firewall-before-' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffff') + '.json')
# Persist exact local rule identities before mutation; do not delete rules.
ConvertTo-Json -InputObject $candidates -Depth 4 | Set-Content -LiteralPath $backup -Encoding utf8
foreach ($candidate in $candidates) {
    Disable-NetFirewallRule -PolicyStore PersistentStore -Name $candidate.Name | Out-Null
    $effective = Get-NetFirewallRule -PolicyStore ActiveStore -Name $candidate.Name
    if ($effective.Enabled -ne 'False') { throw "Rule remains enabled: $($candidate.Name)" }
}
$result = [ordered]@{ observedAt = (Get-Date).ToUniversalTime().ToString('o'); disabledRules = $candidates.Count; backup = $backup; verified = $true; vpnTouched = $false }
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $directory 'host-unreal-firewall-result.json') -Encoding utf8
$result | ConvertTo-Json
