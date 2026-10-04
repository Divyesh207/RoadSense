<#
.SYNOPSIS
    Keeps "adb reverse tcp:8000 tcp:8000" alive while you develop over USB.

.DESCRIPTION
    Watches the ADB device list. Whenever an authorized phone is attached without the
    reverse mapping (first connect, replug, adb server restart), the mapping is added and
    verified. A phone that already has it is left alone. Leave this window open while you
    work and press Ctrl+C to stop; the mapping it created stays until the phone is unplugged.

.EXAMPLE
    .\scripts\android-dev.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\android-dev.ps1 -Port 8000 -IntervalSeconds 2
#>
param(
    [int]$Port = 8000,
    [int]$IntervalSeconds = 2
)

. (Join-Path $PSScriptRoot 'adb-common.ps1')

function Write-Log {
    param([string]$Message, [string]$Color = 'Gray')
    Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Message) -ForegroundColor $Color
}

$adb = Find-Adb
if (-not $adb) {
    Write-Host 'ERROR: adb was not found.' -ForegroundColor Red
    Write-Host '       Install Android SDK Platform-Tools, or add its platform-tools folder to PATH.'
    exit 1
}

Write-Host "RoadSense Android USB monitor" -ForegroundColor Cyan
Write-Host "  adb:     $adb"
Write-Host "  tunnel:  phone 127.0.0.1:$Port  ->  this PC 127.0.0.1:$Port"
Write-Host "  stop:    Ctrl+C"
Write-Host ''

if (Test-LocalBackend -Port $Port) {
    Write-Log "Backend is answering on port $Port." 'Green'
} else {
    Write-Log "Backend is not answering on port $Port yet. The tunnel will still be kept up." 'Yellow'
}

# Last reported condition per device serial, so each change is printed once.
$known = @{}
$announcedWaiting = $false

while ($true) {
    $devices = Get-AdbDevices -Adb $adb
    $present = @{}

    foreach ($device in $devices) {
        $present[$device.Serial] = $true
        $previous = $known[$device.Serial]

        if ($device.State -ne 'device') {
            $condition = "state:$($device.State)"
            if ($previous -ne $condition) {
                Write-Log "$($device.Serial) is '$($device.State)'. $(Get-DeviceStateHelp $device.State)" 'Yellow'
                $known[$device.Serial] = $condition
            }
            continue
        }

        $result = Set-AdbReverse -Adb $adb -Serial $device.Serial -Port $Port
        switch ($result) {
            'created' {
                if ($previous -eq 'ready') {
                    Write-Log "$($device.Serial): reverse tcp:$Port had been dropped; restored and verified." 'Green'
                } else {
                    Write-Log "$($device.Serial) connected: reverse tcp:$Port created and verified." 'Green'
                }
                $known[$device.Serial] = 'ready'
            }
            'present' {
                if ($previous -ne 'ready') {
                    Write-Log "$($device.Serial) connected: reverse tcp:$Port already in place." 'Green'
                    $known[$device.Serial] = 'ready'
                }
            }
            default {
                if ($previous -ne 'failed') {
                    Write-Log "$($device.Serial): could not create reverse tcp:$Port. Retrying every $IntervalSeconds s." 'Red'
                    $known[$device.Serial] = 'failed'
                }
            }
        }
    }

    foreach ($serial in @($known.Keys)) {
        if (-not $present.ContainsKey($serial)) {
            Write-Log "$serial disconnected. The tunnel will be restored when it is plugged back in." 'Yellow'
            $known.Remove($serial)
            $announcedWaiting = $false
        }
    }

    if ($devices.Count -eq 0 -and -not $announcedWaiting) {
        Write-Log 'Waiting for a phone over USB (USB debugging must be enabled)...'
        $announcedWaiting = $true
    }
    if ($devices.Count -gt 0) { $announcedWaiting = $false }

    Start-Sleep -Seconds $IntervalSeconds
}
