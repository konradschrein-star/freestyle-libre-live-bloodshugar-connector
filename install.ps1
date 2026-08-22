<#
.SYNOPSIS
    FreeStyle Libre Monitor - Professional Windows Installer Script
    Installs the app to %LOCALAPPDATA%\Programs\FreeStyleLibreMonitor, creates shortcuts, and enables Autostart.
#>

$ErrorActionPreference = "Stop"

$AppName = "FreeStyle Libre 3 Monitor"
$ExeName = "FreeStyleLibreMonitor.exe"
$SourceExe = Join-Path $PSScriptRoot "dist\FreeStyleLibreTaskbar.exe"

# If running from within dist or repository
if (-not (Test-Path $SourceExe)) {
    $SourceExe = Join-Path $PSScriptRoot "FreeStyleLibreTaskbar.exe"
}

$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\FreeStyleLibreMonitor"
$TargetExe = Join-Path $InstallDir $ExeName

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Installing $AppName..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stop any currently running instance
Write-Host "Stopping running instances..." -ForegroundColor Yellow
Stop-Process -Name "FreeStyleLibreTaskbar" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "FreeStyleLibreMonitor" -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# 2. Create Destination Directory
Write-Host "Creating installation directory: $InstallDir" -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

# 3. Copy Executable & Assets
Write-Host "Copying application binaries..." -ForegroundColor Yellow
Copy-Item -Path $SourceExe -Destination $TargetExe -Force

# 4. Create Desktop & Start Menu Shortcuts via WScript.Shell
$WshShell = New-Object -ComObject WScript.Shell

# Desktop Shortcut
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = Join-Path $DesktopPath "$AppName.lnk"
$Shortcut = $WshShell.CreateShortcut($DesktopShortcut)
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "FreeStyle Libre 3 Live Taskbar Blood Sugar Monitor"
$Shortcut.Save()
Write-Host "Created Desktop Shortcut: $DesktopShortcut" -ForegroundColor Green

# Start Menu Shortcut
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
$StartMenuShortcut = Join-Path $StartMenuPath "$AppName.lnk"
$Shortcut2 = $WshShell.CreateShortcut($StartMenuShortcut)
$Shortcut2.TargetPath = $TargetExe
$Shortcut2.WorkingDirectory = $InstallDir
$Shortcut2.Description = "FreeStyle Libre 3 Live Taskbar Blood Sugar Monitor"
$Shortcut2.Save()
Write-Host "Created Start Menu Shortcut: $StartMenuShortcut" -ForegroundColor Green

# Startup Folder Shortcut (Autostart on Reboot)
$StartupPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$StartupShortcut = Join-Path $StartupPath "$AppName.lnk"
$Shortcut3 = $WshShell.CreateShortcut($StartupShortcut)
$Shortcut3.TargetPath = $TargetExe
$Shortcut3.WorkingDirectory = $InstallDir
$Shortcut3.Description = "FreeStyle Libre 3 Live Background Monitor"
$Shortcut3.Save()
Write-Host "Created Autostart Shortcut: $StartupShortcut" -ForegroundColor Green

# 5. Register in Windows Registry Run key
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $RegPath -Name "FreeStyleLibreMonitor" -Value "`"$TargetExe`""
Write-Host "Registered in Windows Autostart Registry." -ForegroundColor Green

# 6. Launch the application
Write-Host "Launching $AppName in background..." -ForegroundColor Cyan
Start-Process -FilePath $TargetExe

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Installation completed successfully!" -ForegroundColor Green
Write-Host "  The monitor is now running in your taskbar." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
