param([string]$RunDirectory = 'artifacts/unreal/class-character-native/anatomy-v10')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$warRun = (Resolve-Path -LiteralPath $RunDirectory).Path
$warManifest = Get-Content -LiteralPath (Join-Path $warRun 'model-sources.json') -Raw | ConvertFrom-Json
$warReview = Join-Path $warRun 'review'
$warFont = [System.Drawing.Font]::new('Segoe UI', 9)
$warBrush = [System.Drawing.Brushes]::White
try {
    foreach ($warRace in @('empire','dwarf','high_elf','chaos','greenskin','dark_elf')) {
        $warProfiles = @($warManifest.profiles.PSObject.Properties | Where-Object { $_.Value.race -eq $warRace })
        foreach ($warRole in @('idle','walk','attack_melee')) {
            $warSheet = [System.Drawing.Bitmap]::new(1600, 576)
            $warGraphics = [System.Drawing.Graphics]::FromImage($warSheet)
            try {
                $warGraphics.Clear([System.Drawing.Color]::FromArgb(24,24,24))
                $warGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $warIndex = 0
                foreach ($warProfile in $warProfiles) {
                    foreach ($warView in @('front','side')) {
                        $warFile = Join-Path $warReview ($warProfile.Name + '_' + $warRole + '_' + $warView + '.png')
                        $warImage = [System.Drawing.Image]::FromFile($warFile)
                        try {
                            $warX = ($warIndex % 8) * 200
                            $warY = [math]::Floor($warIndex / 8) * 288
                            $warGraphics.DrawImage($warImage, [int]$warX, [int]$warY, 200, 267)
                            $warLabel = $warProfile.Value.classId + ' ' + $warProfile.Value.bodyVariant + ' ' + $warView
                            $warGraphics.DrawString($warLabel, $warFont, $warBrush, [single]$warX, [single]($warY + 267))
                        } finally { $warImage.Dispose() }
                        $warIndex++
                    }
                }
                $warSheet.Save((Join-Path $warReview ($warRace + '_' + $warRole + '_sheet.png')), [System.Drawing.Imaging.ImageFormat]::Png)
            } finally { $warGraphics.Dispose(); $warSheet.Dispose() }
        }
    }
    $warProfiles = @($warManifest.profiles.PSObject.Properties | Where-Object { $_.Value.race -eq 'greenskin' })
    foreach ($warView in @('face_front','face_side')) {
        $warSheet = [System.Drawing.Bitmap]::new(1200, 848)
        $warGraphics = [System.Drawing.Graphics]::FromImage($warSheet)
        try {
            $warGraphics.Clear([System.Drawing.Color]::FromArgb(24,24,24))
            $warIndex = 0
            foreach ($warProfile in $warProfiles) {
                $warImage = [System.Drawing.Image]::FromFile((Join-Path $warReview ($warProfile.Name + '_idle_' + $warView + '.png')))
                try {
                    $warX = ($warIndex % 4) * 300
                    $warY = [math]::Floor($warIndex / 4) * 424
                    $warGraphics.DrawImage($warImage, [int]$warX, [int]$warY, 300, 400)
                    $warGraphics.DrawString(($warProfile.Value.classId + ' ' + $warProfile.Value.bodyVariant), $warFont, $warBrush, [single]$warX, [single]($warY + 400))
                } finally { $warImage.Dispose() }
                $warIndex++
            }
            $warSheet.Save((Join-Path $warReview ('greenskin_' + $warView + '_sheet.png')), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $warGraphics.Dispose(); $warSheet.Dispose() }
    }
} finally { $warFont.Dispose() }
