# Android development over USB

The debug build of the field app talks to `http://127.0.0.1:8000/`. On a phone, `127.0.0.1` is
the phone itself, so the app only reaches the backend on your PC while an ADB reverse tunnel
is in place:

```
adb reverse tcp:8000 tcp:8000
```

That tunnel belongs to the USB connection and disappears whenever the phone is unplugged.
The scripts in `scripts/` put it back for you.

## Start the monitor

From the repository root, in a PowerShell window:

```powershell
.\scripts\android-dev.ps1
```

If Windows blocks scripts ("running scripts is disabled on this system"), run it this way
instead. It applies to this one command only and changes no system setting:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\android-dev.ps1
```

Leave the window open while you work. It does not need Claude Code, Android Studio or
anything else to be running. It prints one line per change, for example:

```
[11:56:37] Backend is answering on port 8000.
[11:56:37] <serial> connected: reverse tcp:8000 created and verified.
[12:03:10] <serial> disconnected. The tunnel will be restored when it is plugged back in.
[12:03:41] <serial> connected: reverse tcp:8000 created and verified.
```

| Event | What the monitor does |
|---|---|
| Phone plugged in and authorized | Adds the tunnel, checks it is listed, reports it |
| Tunnel already present | Leaves it alone (no duplicate mapping) |
| Phone unplugged | Reports the disconnect and waits |
| Phone replugged | Adds the tunnel again within about 2 seconds |
| Tunnel dropped without unplugging (adb server restart) | Adds it again |
| Phone attached but unauthorized or offline | Says what to do on the phone, then continues once it is usable |

Options: `-Port 8000` (default) and `-IntervalSeconds 2` (default check interval).

## Stop the monitor

Press `Ctrl+C` in its window, or close the window. The tunnel it created stays until the
phone is unplugged.

## Restore the tunnel by hand

One-shot script (exit code 0 on success):

```powershell
.\scripts\android-reverse.ps1
```

Or directly:

```powershell
adb reverse tcp:8000 tcp:8000
adb reverse --list
```

`adb reverse --list` should show `tcp:8000 tcp:8000`.

## Troubleshooting

**"adb was not found"**
Install Android SDK Platform-Tools. The scripts look on `PATH`, then in `ANDROID_HOME`,
`ANDROID_SDK_ROOT` and `%LOCALAPPDATA%\Android\Sdk\platform-tools`.

**Device shows `unauthorized`**
Unlock the phone and accept the "Allow USB debugging?" prompt; tick "Always allow from this
computer". If no prompt appears: Developer options > Revoke USB debugging authorizations,
then replug the cable.

**Device shows `offline`**
Replug the cable, try another USB port or cable, or switch USB debugging off and on. If it
stays offline, restart the adb server:

```powershell
adb kill-server
adb start-server
```

**No device listed at all**
Check that USB debugging is enabled, the cable carries data (not charge-only), and the
phone's USB mode is "File transfer" rather than "Charging only".

**Tunnel is up but the app says the server is offline**
The backend is not answering on the PC. Check `http://127.0.0.1:8000/api/v1/health/live`
in a browser on the PC and start the stack (`docker compose up -d`) if it is down.

**The app was built with a different URL**
The debug URL is chosen at build time (`roadintel.apiBaseUrl.debug`). For USB development
build with `-Proadintel.apiBaseUrl.debug=http://127.0.0.1:8000/`. A value in
`apps/android/local.properties` is used when that flag is not given.

## Limits

- The first connection to a PC still needs the USB debugging prompt accepted on the phone.
- The monitor only runs while its window is open; it is not installed as a Windows service.
- It forwards one port (8000). The web console and other services are not tunnelled.
