param(
    [Parameter(Mandatory)][string]$IsoPath,
    [Parameter(Mandatory)][string]$GuestLicenseEvidence,
    [string]$StorageRoot = (Join-Path $PSScriptRoot '../../artifacts/collaboration/vm')
)
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Hyper-V provisioning requires an administrator PowerShell session.' }
if (!(Test-Path -LiteralPath $IsoPath -PathType Leaf) -or [IO.Path]::GetExtension($IsoPath) -ne '.iso') { throw 'Provide licensed Windows guest installation media.' }
if (!(Test-Path -LiteralPath $GuestLicenseEvidence -PathType Leaf)) { throw 'Record a valid guest license before provisioning; no purchases or host-license reuse are implicit.' }
if (!(Get-Command New-VM -ErrorAction SilentlyContinue)) { throw 'Hyper-V is unavailable. Enabling the Windows feature/restarting requires an owner maintenance window.' }
$storage = [IO.Path]::GetFullPath($StorageRoot)
$drive = Get-PSDrive ([IO.Path]::GetPathRoot($storage).TrimEnd('\',':'))
if ($drive.Free -lt 180GB) { throw 'Reserve at least 180 GiB free for a 160 GiB guest disk and host headroom.' }
if ((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory -lt 28GB) { throw 'Insufficient memory for the isolated Unreal Editor and host.' }
$name = 'AegisWar-Collaboration'
if (Get-VM -Name $name -ErrorAction SilentlyContinue) { throw 'VM already exists; inspect it instead of overwriting it.' }
New-Item -ItemType Directory -Path $storage -Force | Out-Null
# Start offline. No bridge/NAT, host filesystem mount, or work VPN access is created.
$vm = New-VM -Name $name -Generation 2 -MemoryStartupBytes 12GB -NewVHDPath (Join-Path $storage "$name.vhdx") -NewVHDSizeBytes 160GB -Path $storage
Set-VMProcessor -VM $vm -Count 4
Set-VMMemory -VM $vm -DynamicMemoryEnabled $true -MinimumBytes 8GB -StartupBytes 12GB -MaximumBytes 16GB
Get-VMNetworkAdapter -VM $vm | Disconnect-VMNetworkAdapter
Set-VMFirmware -VM $vm -EnableSecureBoot On
Set-VMKeyProtector -VM $vm -NewLocalKeyProtector
Enable-VMTPM -VM $vm
Get-VMIntegrationService -VM $vm | Where-Object Name -eq 'Guest Service Interface' | Disable-VMIntegrationService
Add-VMDvdDrive -VM $vm -Path ([IO.Path]::GetFullPath($IsoPath))
Set-VMFirmware -VM $vm -FirstBootDevice (Get-VMDvdDrive -VM $vm)
[pscustomobject]@{ Name = $name; Network = 'disconnected'; State = 'not-started'; Collaboration = 'closed'; Next = 'Install guest, validate graphics and configure/test isolated egress before attaching any network.' } | ConvertTo-Json
