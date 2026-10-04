<#
.SYNOPSIS
    One-shot: make the USB-connected phone's 127.0.0.1:8000 reach the API on this PC.

.DESCRIPTION
    Runs "adb reverse tcp:8000 tcp:8000" for every authorized device, skipping devices
    that already have the mapping, and verifies the result. Use android-dev.ps1 instead
    to keep the mapping restored automatically while you work.

.EXAMPLE
    .\scripts\android-reverse.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\android-reverse.ps1 -Port 8000
#>
param(
    [int]$Port = 8000
)

. (Join-Path $PSScriptRoot 'adb-common.ps1')

$adb = Find-Adb
if (-not $adb) {
    Write-Host 'ERROR: adb was not found.' -ForegroundColor Red
    Write-Host '       Install Android SDK Platform-Tools, or add its platform-tools folder to PATH.'
    exit 1
}

$devices = Get-AdbDevices -Adb $adb
if ($devices.Count -eq 0) {
    Write-Host 'ERROR: no Android device is connected.' -ForegroundColor Red
    Write-Host '       Plug the phone in over USB and enable USB debugging in Developer options.'
    exit 1
}

$failed = $false
$ready = 0
foreach ($device in $devices) {
    if ($device.State -ne 'device') {
        Write-Host "ERROR: $($device.Serial) is '$($device.State)'." -ForegroundColor Red
        Write-Host "       $(Get-DeviceStateHelp $device.State)"
        $failed = $true
        continue
    }

    $result = Set-AdbReverse -Adb $adb -Serial $device.Serial -Port $Port
    switch ($result) {
        'present' { Write-Host "OK: $($device.Serial) already forwards tcp:$Port to this PC." -ForegroundColor Green; $ready++ }
        'created' { Write-Host "OK: $($device.Serial) now forwards tcp:$Port to this PC." -ForegroundColor Green; $ready++ }
        default {
            Write-Host "ERROR: could not create the reverse mapping on $($device.Serial)." -ForegroundColor Red
            $failed = $true
        }
    }
}

if ($ready -gt 0 -and -not (Test-LocalBackend -Port $Port)) {
    Write-Host "WARNING: nothing answered on http://127.0.0.1:$Port/api/v1/health/live." -ForegroundColor Yellow
    Write-Host '         The tunnel is in place, but start the backend before using the app.'
}

if ($failed) { exit 1 }
exit 0
