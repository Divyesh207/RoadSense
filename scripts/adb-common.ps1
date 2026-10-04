# Shared helpers for the Android USB development scripts (android-reverse.ps1, android-dev.ps1).
# Dot-source this file; it defines functions only and runs nothing.
# Written for Windows PowerShell 5.1 and later.

function Find-Adb {
    # Returns the full path to adb.exe, or $null when it cannot be found.
    $cmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $roots = @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT)
    if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA 'Android\Sdk') }
    foreach ($root in $roots) {
        if (-not $root) { continue }
        $candidate = Join-Path $root 'platform-tools\adb.exe'
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Get-AdbDevices {
    # Returns one object per attached device: Serial and State
    # (device | unauthorized | offline | ...). Starts the adb server if needed.
    param([Parameter(Mandatory = $true)][string]$Adb)

    $lines = & $Adb devices
    $devices = @()
    foreach ($line in $lines) {
        if ($line -match '^(\S+)\s+(device|unauthorized|offline|recovery|sideload|bootloader|no permissions.*|authorizing|connecting)\s*$') {
            $devices += [pscustomobject]@{ Serial = $Matches[1]; State = $Matches[2] }
        }
    }
    return , $devices
}

function Test-AdbReverse {
    # True when the device already forwards its tcp:<Port> to the host's tcp:<Port>.
    param(
        [Parameter(Mandatory = $true)][string]$Adb,
        [Parameter(Mandatory = $true)][string]$Serial,
        [Parameter(Mandatory = $true)][int]$Port
    )
    $list = & $Adb -s $Serial reverse --list
    if ($LASTEXITCODE -ne 0) { return $false }
    foreach ($line in $list) {
        if ($line -match "tcp:$Port\s+tcp:$Port\s*$") { return $true }
    }
    return $false
}

function Set-AdbReverse {
    # Makes sure the reverse mapping exists and returns one of:
    #   'present'  - it was already there, nothing was changed
    #   'created'  - it was missing and has been added and verified
    #   'failed'   - adb could not add it, or it did not appear afterwards
    param(
        [Parameter(Mandatory = $true)][string]$Adb,
        [Parameter(Mandatory = $true)][string]$Serial,
        [Parameter(Mandatory = $true)][int]$Port
    )
    if (Test-AdbReverse -Adb $Adb -Serial $Serial -Port $Port) { return 'present' }

    & $Adb -s $Serial reverse "tcp:$Port" "tcp:$Port" | Out-Null
    if ($LASTEXITCODE -ne 0) { return 'failed' }

    if (Test-AdbReverse -Adb $Adb -Serial $Serial -Port $Port) { return 'created' }
    return 'failed'
}

function Get-DeviceStateHelp {
    # What to do about a device that is attached but not usable.
    param([string]$State)
    switch -Regex ($State) {
        '^unauthorized$' { return 'Unlock the phone and accept the "Allow USB debugging?" prompt (tick "Always allow from this computer").' }
        '^authorizing$'  { return 'Waiting for the USB debugging prompt on the phone to be accepted.' }
        '^offline$'      { return 'Unplug and replug the cable, or toggle USB debugging off and on in Developer options.' }
        '^no permissions' { return 'Reconnect the cable and accept the USB debugging prompt.' }
        default          { return "The phone is in '$State' mode; boot it normally with USB debugging enabled." }
    }
}

function Test-LocalBackend {
    # True when the API answers on this PC. The tunnel works without it, but the app cannot.
    param([Parameter(Mandatory = $true)][int]$Port)
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/health/live" -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}
