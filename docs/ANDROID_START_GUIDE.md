# How to start RoadSense Android development

This is the start-to-finish routine for working on the Android field app with a phone on
USB. Every command here was run against this repository on the Windows development laptop.

The debug app talks to `http://127.0.0.1:8000/`. An ADB reverse tunnel carries that to the
backend on the laptop. You never change the app's API URL.

## Quick start

Use two PowerShell windows, both opened in the repository root.

**Window 1 (backend, build, install):**

```powershell
docker compose up -d
```

```powershell
(Invoke-WebRequest http://127.0.0.1:8000/api/v1/health/live -UseBasicParsing).Content
```

Connect the phone by USB, then:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb devices
```

**Window 2 (leave it open):**

```powershell
.\scripts\android-dev.ps1
```

**Back in window 1:**

```powershell
& $adb reverse --list
```

```powershell
cd apps\android
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.14.7-hotspot"
$env:JAVA_TOOL_OPTIONS = "-Djdk.net.unixdomain.tmpdir=C:/no_afunix_dir"
& "$env:JAVA_HOME\bin\java.exe" "-Dorg.gradle.appname=gradlew" -classpath "gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain installDebug
cd ..\..
```

```powershell
& $adb shell am start -n com.roadintelligence.field/.MainActivity
```

Sign in and check that the app shows **Server online**.

The rest of this guide explains each step and what to do when one fails.

---

## 1. Open the repository

Open PowerShell in the repository root (the folder that contains `docker-compose.yml`,
`apps`, `scripts` and `docs`). All commands below start from there unless a `cd` is shown.

Two things about this laptop explain why some commands look longer than usual:

- `adb` is not on `PATH`, so the guide calls it through `$adb`. Set it once per window:

  ```powershell
  $adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
  ```

- The repository folder name contains `&`, which breaks `gradlew.bat`. The build is
  started through Java directly instead (step 6).

## 2. Start the backend

The backend runs in Docker. Docker Desktop must be running first.

```powershell
docker compose up -d
```

This starts PostgreSQL, Redis, the FastAPI API (port 8000), the AI worker, the web console
(port 3000) and Nginx. It uses the `.env` file in the repository root.

Check the containers:

```powershell
docker compose ps
```

`road_platform_api` should be `Up ... (healthy)`.

Check the API answers on port 8000:

```powershell
(Invoke-WebRequest http://127.0.0.1:8000/api/v1/health/live -UseBasicParsing).Content
```

The reply contains `"status":"alive"`. You can also open `http://localhost:8000/docs` in a
browser.

**Stop the backend** when you finish (data is kept):

```powershell
docker compose stop
```

## 3. Connect the phone

1. Plug the phone into the laptop with a data-capable USB cable.
2. On the phone, enable **Developer options > USB debugging** if it is not already on.
3. The first time on this laptop, the phone shows "Allow USB debugging?". Accept it and
   tick "Always allow from this computer".
4. Check the connection:

   ```powershell
   & $adb devices
   ```

The state next to the serial number means:

| State | Meaning | What to do |
|---|---|---|
| `device` | Connected and authorized | Nothing; carry on |
| `unauthorized` | The phone has not accepted this computer | Unlock the phone and accept the prompt |
| `offline` | ADB sees the phone but cannot talk to it | Replug the cable; see troubleshooting |
| (nothing listed) | The phone is not visible to ADB | Check cable, USB mode and USB debugging |

## 4. Start the automatic ADB reverse monitor

In a second PowerShell window, from the repository root:

```powershell
.\scripts\android-dev.ps1
```

If Windows says running scripts is disabled, use this form (it applies to this one command
and changes no system setting):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\android-dev.ps1
```

The monitor finds `adb` by itself and keeps this mapping in place:

```
adb reverse tcp:8000 tcp:8000
```

It adds the mapping when an authorized phone appears, leaves it alone when it already
exists, and adds it again after every reconnect. **Keep this window open while you work.**
Press `Ctrl+C` in it to stop the monitor; the current tunnel stays until the phone is
unplugged.

## 5. Verify the reverse connection

```powershell
& $adb reverse --list
```

Expected output includes:

```
tcp:8000 tcp:8000
```

**Manual fallback**, if you are not running the monitor or want to force it once:

```powershell
.\scripts\android-reverse.ps1
```

## 6. Build and install the debug APK

From `apps\android`:

```powershell
cd apps\android
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.14.7-hotspot"
$env:JAVA_TOOL_OPTIONS = "-Djdk.net.unixdomain.tmpdir=C:/no_afunix_dir"
& "$env:JAVA_HOME\bin\java.exe" "-Dorg.gradle.appname=gradlew" -classpath "gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain installDebug
cd ..\..
```

- `installDebug` builds the debug APK **and installs it on the connected phone**. No
  separate `adb install` is needed. It ends with `Installed on 1 device.` and
  `BUILD SUCCESSFUL`.
- Installing over the existing app keeps its data (login, queued inspections).
- To build without installing, replace `installDebug` with `assembleDebug`. The APK is
  written to `apps\android\app\build\outputs\apk\debug\app-debug.apk` and can be installed
  with `& $adb install -r apps\android\app\build\outputs\apk\debug\app-debug.apk` from the
  repository root.
- `JAVA_HOME` must point at JDK 17. The laptop's default Java is version 8, which cannot
  build the app.
- `JAVA_TOOL_OPTIONS` works around a "Unable to establish loopback connection" failure of
  Gradle on this laptop.
- The debug API URL comes from `roadintel.apiBaseUrl.debug` in the git-ignored
  `apps\android\local.properties`, which is set to `http://127.0.0.1:8000/`. No extra flag
  is needed.
- You can also build and run from Android Studio by opening `apps\android`; it uses the
  same `local.properties` value.

## 7. Launch the app

Tap the Road Intelligence icon on the phone, or:

```powershell
& $adb shell am start -n com.roadintelligence.field/.MainActivity
```

## 8. Verify everything works

1. The app opens on the sign-in screen, or on Home if you were already signed in.
2. Sign in with your account. Accounts are created by an administrator; the app's Create
   Account screen does not create one.
3. Home shows the **Server online** chip.
4. The backend is receiving requests: Home lists your inspections and New Inspection
   lists the roads defined on the server. Profile shows the server address
   `http://127.0.0.1:8000/`.
5. GPS and camera: open **New**, pick a road, capture GPS (allow the location permission,
   ideally outdoors), take a photo (allow the camera permission), then queue the
   inspection. On **Sync** it should move to `SYNCED`.

## 9. Unplugging and replugging the phone

- Unplugging removes the reverse tunnel. The app shows the server as offline and new
  inspections wait in the sync queue on the phone.
- When you plug the phone back in, the monitor recreates the tunnel within about two
  seconds and prints a line saying so.
- You do **not** change the Android API URL. It stays `http://127.0.0.1:8000/`.
- Queued inspections upload on the next sync; use **Sync Now** or **Retry** on the Sync
  screen to trigger it immediately.

## 10. Troubleshooting

**`adb` is not recognized**
`adb` is not on `PATH` on this laptop. Set `$adb` as in step 1 and call `& $adb ...`. The
two scripts locate `adb` themselves (PATH, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, then
`%LOCALAPPDATA%\Android\Sdk\platform-tools`).

**Device not detected (`adb devices` lists nothing)**
Check that USB debugging is on, the cable carries data, and the phone's USB mode is "File
transfer" and not "Charging only". Try another USB port.

**Device is `unauthorized`**
Unlock the phone and accept the "Allow USB debugging?" prompt. If no prompt appears, use
Developer options > Revoke USB debugging authorizations, then replug the cable.

**Device is `offline`**
Replug the cable, or switch USB debugging off and on. If it stays offline:

```powershell
& $adb kill-server
& $adb start-server
```

**Reverse mapping missing (`adb reverse --list` is empty)**
The monitor is probably not running. Start it (step 4), or run
`.\scripts\android-reverse.ps1` once.

**Backend not running**
The health check in step 2 fails. Run `docker compose ps`; if the containers are stopped,
run `docker compose up -d`. For API errors, read `docker compose logs --tail 100 api`.

**Port 8000 unavailable**
Another program is using the port, so the API container cannot start. Find it:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
```

Stop that program, then run `docker compose up -d` again.

**The app says "Server offline"**
Check in this order: the health check in step 2 answers; `& $adb devices` shows `device`;
`& $adb reverse --list` shows `tcp:8000 tcp:8000`; Profile in the app shows
`http://127.0.0.1:8000/`. If Profile shows another address, rebuild and reinstall
(step 6).

**USB reconnect does not restore the connection**
Look at the monitor window. If it is closed, start it again. If it reports `unauthorized`
or `offline`, follow those entries above. If it reports the tunnel as created but the app
still fails, tap the refresh icon on Home or reopen the app, then check the backend.

**Build fails while downloading dependencies (certificate / PKIX error)**
Add the Windows certificate store option and run the build again:

```powershell
$env:JAVA_TOOL_OPTIONS = "-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djdk.net.unixdomain.tmpdir=C:/no_afunix_dir"
```

## Which windows stay open

| Window | Purpose | Keep open? |
|---|---|---|
| PowerShell 2: `android-dev.ps1` | ADB reverse monitor | Yes, while developing. `Ctrl+C` to stop |
| PowerShell 1 | Backend commands, build, install | Only while you use it |
| Docker Desktop | Runs the backend containers | Yes. `docker compose stop` when finished |

More detail on the monitor itself is in [ANDROID_USB_DEV.md](ANDROID_USB_DEV.md).
