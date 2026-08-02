
<#
.SYNOPSIS
    Generate the Tauri app icon (256x256 amber "M" on zinc-950).

.DESCRIPTION
    Renders native/icons/icon.png with System.Drawing. Used when the
    native wrapper needs a fresh icon without a design tool.

.EXAMPLE
    .\scripts\generate-tauri-icon.ps1
#>
#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$iconDir = Join-Path (Split-Path -Parent $PSScriptRoot) "native\icons"
New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
$out = Join-Path $iconDir "icon.png"

Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 512, 512
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::FromArgb(255, 30, 27, 75))
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 124, 92, 252))
$font = New-Object System.Drawing.Font("Segoe UI", 168, [System.Drawing.FontStyle]::Bold)
$g.DrawString("M", $font, $brush, 118, 92)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
$brush.Dispose()
$font.Dispose()
Write-Host "Wrote $out" -ForegroundColor Green


