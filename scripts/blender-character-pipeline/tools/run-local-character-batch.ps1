$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$blender = if ($env:BLENDER_PATH) { $env:BLENDER_PATH } else { 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' }
$generator = Join-Path $repo 'scripts\blender-character-pipeline\blender\generate_mpfb_body.py'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$batchRoot = Join-Path $repo "artifacts\model-jobs\local-character-batch-$stamp"
$logPath = Join-Path $batchRoot 'batch.log'

New-Item -ItemType Directory -Force -Path $batchRoot | Out-Null
"Local character batch started $(Get-Date -Format o)" | Tee-Object -FilePath $logPath
"Blender: $blender" | Tee-Object -FilePath $logPath -Append
"Provider: local MPFB only; paidServiceUsed=false; networkUsed=false" | Tee-Object -FilePath $logPath -Append

if (-not (Test-Path -LiteralPath $blender)) { throw "Blender was not found: $blender" }
if (-not (Test-Path -LiteralPath $generator)) { throw "MPFB generator was not found: $generator" }

$jobs = @(
  @{ family = 'civic_humanoid_v2'; variant = 'm'; profile = 'battle_prelate_hammer' },
  @{ family = 'civic_humanoid_v2'; variant = 'f'; profile = 'unarmed' },
  @{ family = 'mire_brutish_v1'; variant = 'm'; profile = 'unarmed' },
  @{ family = 'mire_brutish_v1'; variant = 'f'; profile = 'unarmed' }
)

$failed = $false
foreach ($job in $jobs) {
  $jobRoot = Join-Path $batchRoot "$($job.family)_$($job.variant)"
  $output = Join-Path $jobRoot "body_$($job.family)_$($job.variant).glb"
  $review = Join-Path $jobRoot 'review'
  $blend = Join-Path $jobRoot 'source.blend'
  New-Item -ItemType Directory -Force -Path $jobRoot | Out-Null
  "[$(Get-Date -Format o)] START $($job.family)/$($job.variant)" | Tee-Object -FilePath $logPath -Append
  $args = @(
    '--background', '--python', $generator, '--',
    '--family', $job.family, '--variant', $job.variant,
    '--animation-profile', $job.profile,
    '--output', $output, '--review-dir', $review, '--save-blend', $blend
  )
  # Blender writes harmless deprecation/add-on notices to stderr. Do not let
  # PowerShell's native-command error conversion abort the batch before the
  # actual process exit code is available.
  $previousErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $blender @args 2>&1 | Tee-Object -FilePath $logPath -Append
  $blenderExitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousErrorAction
  if ($blenderExitCode -ne 0) {
    "[$(Get-Date -Format o)] FAIL $($job.family)/$($job.variant) exit=$blenderExitCode" | Tee-Object -FilePath $logPath -Append
    $failed = $true
  } else {
    "[$(Get-Date -Format o)] DONE $($job.family)/$($job.variant) output=$output" | Tee-Object -FilePath $logPath -Append
  }
}

if ($failed) {
  "Local character batch finished with failures. Inspect $logPath" | Tee-Object -FilePath $logPath -Append
  exit 1
}
"Local character batch finished successfully. Inspect $logPath" | Tee-Object -FilePath $logPath -Append
