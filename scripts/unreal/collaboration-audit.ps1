param([string]$Output = (Join-Path $PSScriptRoot '../../artifacts/collaboration/host-audit.json'))
$ErrorActionPreference = 'Stop'
# Read-only. The host's work Tailscale account and settings are explicitly out of scope.
$report = [ordered]@{ schemaVersion = 1; observedAt = (Get-Date).ToUniversalTime().ToString('o'); collaboratorAccess = 'closed'; findings = @{}; unavailable = @{} }
function Observe([string]$Name, [scriptblock]$Action) {
    try { $report.findings[$Name] = & $Action }
    catch { $report.unavailable[$Name] = $_.Exception.Message }
}
Observe 'firewall' { @(Get-NetFirewallProfile -PolicyStore ActiveStore | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction) }
Observe 'defender' { Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated,AMRunningMode }
Observe 'encryption' { @(Get-BitLockerVolume -MountPoint 'C:' | Select-Object MountPoint,VolumeStatus,ProtectionStatus) }
Observe 'system' { Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory,HypervisorPresent }
Observe 'hyperv' { Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All | Select-Object FeatureName,State }
Observe 'freeSpace' { Get-PSDrive C | Select-Object Free,Used }
Observe 'remoteServices' { @(Get-Service TermService,sshd,WinRM -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType) }
Observe 'recentUpdates' { @(Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 8 HotFixID,InstalledOn) }
Observe 'currentUserIsAdministrator' {
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
Observe 'inboundAllowRules' { @(Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Inbound -Action Allow | Select-Object DisplayName,Profile,Enabled) }
$target = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $target -Encoding utf8
[pscustomobject]@{ Report = $target; UnavailableChecks = @($report.unavailable.Keys); CollaboratorAccess = 'closed' } | ConvertTo-Json
