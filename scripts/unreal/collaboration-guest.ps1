param(
    [ValidateSet('Preflight','Server','Editor')][string]$Mode = 'Preflight',
    [string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8',
    [string]$ProjectOwner,
    [string]$ServerVpnIp,
    [string]$EvidencePath
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$policy = Get-Content -LiteralPath (Join-Path $root 'migration/collaboration-policy.json') -Raw | ConvertFrom-Json
# This check must precede even discovery/status of Tailscale. Never touch the host's work account.
$system = Get-CimInstance Win32_ComputerSystem
if ($system.Model -ne 'Virtual Machine' -or $system.Manufacturer -ne 'Microsoft Corporation' -or $env:COMPUTERNAME -ne $policy.guestComputerName) {
    throw 'Run only inside the designated Hyper-V guest. Host Tailscale use is forbidden.'
}
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run Unreal under the standard project account, not an administrator.' }
if (!$ProjectOwner -or $ProjectOwner -notmatch '^[^@\s]+@[^@\s]+$') { throw 'Supply the separate project VPN owner; never use a work account.' }
$version = Get-Content -LiteralPath (Join-Path $EngineRoot 'Engine/Build/Build.version') -Raw | ConvertFrom-Json
if ("$($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion)" -ne $policy.engineVersion) { throw 'Unreal engine build mismatch.' }
$vpn = & tailscale status --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $vpn.BackendState -ne 'Running') { throw 'The guest project VPN is not running.' }
$owner = $vpn.User.PSObject.Properties[[string]$vpn.Self.UserID].Value.LoginName
if ($owner -ne $ProjectOwner) { throw 'Guest VPN identity does not match the separate project owner.' }
$localIp = @($vpn.TailscaleIPs | Where-Object { $_ -match '^100\.' })[0]
if (!$localIp) { throw 'Guest project VPN IPv4 address unavailable.' }
if ($Mode -eq 'Preflight') {
    [pscustomobject]@{ GuestValidated = $true; EngineVersion = $policy.engineVersion; AccountMatched = $true; CollaboratorAccess = 'closed' } | ConvertTo-Json
    exit 0
}
if ($policy.collaboratorAccess -ne 'verified' -or !$EvidencePath) { throw 'Collaboration remains closed until all isolation and remote acceptance checks are recorded.' }
$evidence = Get-Content -LiteralPath $EvidencePath -Raw | ConvertFrom-Json
$code = (& git -C $root rev-parse HEAD).Trim()
$contentLock = Get-Content -LiteralPath (Join-Path $root 'migration/native-content.lock.json') -Raw | ConvertFrom-Json
if ($evidence.codeCommit -ne $code -or $evidence.contentCommit -ne $contentLock.commit -or $evidence.guestName -ne $env:COMPUTERNAME) { throw 'Acceptance evidence is stale or belongs to another machine.' }
foreach ($check in $policy.requiredEvidence) {
    $receipt = $evidence.checks.PSObject.Properties[$check].Value
    if ($receipt.result -ne 'passed' -or !$receipt.evidence) { throw "Missing actual acceptance evidence: $check" }
}
if ($Mode -eq 'Server') {
    $program = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealMultiUserServer.exe'
    $arguments = @("-UDPMESSAGING_TRANSPORT_UNICAST=$($localIp):$($policy.serverPort)", '-ConcertProject=AegisWar')
} else {
    $address = $null
    if (![Net.IPAddress]::TryParse($ServerVpnIp, [ref]$address) -or $ServerVpnIp -notmatch '^100\.') { throw 'Supply the project guest server VPN address.' }
    $program = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
    $arguments = @(('"' + (Join-Path $root 'unreal/AegisWar/AegisWar.uproject') + '"'), '-EnablePlugins=MultiUserClient', '-messaging', "-UDPMESSAGING_TRANSPORT_UNICAST=$($localIp):0", "-UDPMESSAGING_TRANSPORT_STATIC=$($ServerVpnIp):$($policy.serverPort)")
}
Start-Process -FilePath $program -ArgumentList $arguments -WindowStyle Hidden -PassThru | Select-Object Id,ProcessName
