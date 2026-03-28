---
name: Android Device Access
description: Access camera, microphone, calendar, location, clipboard, notifications, and run Java on the Android host via bsh
---

# Android Device Access

You run inside proot on Android. Use `bsh` to run Java directly on the Android host with full SDK access. Use `am` for intents.

**Self-improvement**: When you discover a new working `bsh` command pattern, add it to this file under the relevant section.

## BeanShell (bsh) — Java on Android Host

```bash
bsh -c '<code>'          # Execute inline Java
bsh -e '<expression>'    # Evaluate and print result
bsh <file.bsh>           # Execute file
echo '<code>' | bsh      # Execute from stdin
bsh --help               # Show help
```

### Built-in Variables

| Variable | Type |
|----------|------|
| `context` | `android.content.Context` |
| `app` | `AnyClawApp` instance |
| `activity` | Current foreground `Activity` (null if backgrounded) |
| `handler` | Main thread `Handler` (for UI operations) |
| `bridge` | `DeviceBridge` instance |
| `pm` | `PackageManager` |
| `contentResolver` | `ContentResolver` |
| `runtime` | `Runtime` |

### BeanShell Callbacks (simplified syntax)

BeanShell CAN implement Java interfaces — use simplified syntax without types:

```bash
# Example: Camera.PictureCallback
bsh -c 'import android.hardware.Camera; cb = new Camera.PictureCallback() { onPictureTaken(data, camera) { print("got " + data.length + " bytes"); } }; print(cb);'
# Use: methodName(args) — NOT: public void methodName(Type arg)
```

### Callback Helpers (convenience wrappers)

Pre-built helpers for common callback patterns:

| Helper | Methods |
|--------|---------|
| `camera` | `info()`, `info(cameraId)`, `takePhoto(path)`, `takePhoto(path, cameraId)` |
| `audio` | `record(path)`, `record(path, durationSec)` |
| `location` | `getCurrentLocation()`, `getCurrentLocation(timeoutSec)` |
| `sensor` | `read(sensorType)` — 1=accelerometer, 2=magnetic, 4=gyroscope, 3=orientation |
| `clipboard` | `get()`, `set(text)` |

```bash
# Take photo (rear camera)
bsh -e 'camera.takePhoto(context.getCacheDir().getAbsolutePath() + "/photo.jpg")'
# Front camera
bsh -e 'camera.takePhoto(context.getCacheDir().getAbsolutePath() + "/selfie.jpg", 1)'
# Camera info
bsh -e 'camera.info()'
# Record 5s audio
bsh -e 'audio.record(context.getCacheDir().getAbsolutePath() + "/rec.m4a", 5)'
# Read accelerometer
bsh -e 'sensor.read(1)'
# Clipboard
bsh -e 'clipboard.get()'
bsh -e 'clipboard.set("hello")'
```

Auto-imports: `android.os.*`, `android.content.*`, `android.provider.*`, `android.app.*`, `android.net.*`, `android.media.*`, `android.hardware.*`, `android.location.*`, `android.content.pm.*`, `java.io.*`, `java.util.*`, `java.net.*`. Built-in `print()`, `println()`, `runOnUi(Runnable)`.

**Important**: `requestPermissions` and UI operations MUST run on UI thread. Use `runOnUi()`.

### Device Info

```bash
bsh -e 'Build.MODEL + " " + Build.MANUFACTURER'
bsh -c 'BatteryManager bm = (BatteryManager)context.getSystemService("batterymanager"); print(bm.getIntProperty(4) + "%");'
bsh -e 'pm.getInstalledPackages(0).size() + " packages"'
bsh -e 'java.util.TimeZone.getDefault().getID()'
```

### Permissions (check & request)

Always check permission before using protected APIs. If denied, request via runtime dialog or grant via adb.

```bash
# Check any permission
bsh -e 'androidx.core.content.ContextCompat.checkSelfPermission(context, "android.permission.CAMERA") == PackageManager.PERMISSION_GRANTED ? "granted" : "denied"'

# Request via runtime dialog (MUST use runOnUi)
bsh -c 'if (activity != null) { runOnUi(new Runnable(){public void run(){androidx.core.app.ActivityCompat.requestPermissions(activity, new String[]{"android.permission.RECORD_AUDIO"}, 1);}}); print("dialog shown"); } else { print("no activity"); }'

# Grant via adb (from host)
# adb shell pm grant gptos.intelligence.assistant android.permission.RECORD_AUDIO
```

Common permissions: `CAMERA`, `RECORD_AUDIO`, `READ_CALENDAR`, `ACCESS_FINE_LOCATION`, `POST_NOTIFICATIONS`.

### Notifications

```bash
bsh -c 'NotificationManager nm = (NotificationManager)context.getSystemService("notification"); String ch = "bsh_ch"; nm.createNotificationChannel(new NotificationChannel(ch, "BSH", NotificationManager.IMPORTANCE_DEFAULT)); Notification n = new Notification.Builder(context, ch).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Title").setContentText("Body").build(); nm.notify(42, n); print("sent");'
```

### Calendar

```bash
bsh -c 'import android.provider.CalendarContract; String[] p = {"_id","title","dtstart"}; long now = System.currentTimeMillis(); android.database.Cursor c = contentResolver.query(CalendarContract.Events.CONTENT_URI, p, "dtstart >= ? AND dtstart <= ?", new String[]{String.valueOf(now), String.valueOf(now+30L*86400000)}, "dtstart ASC"); while(c.moveToNext()){print(c.getString(1) + " @ " + new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm").format(new Date(c.getLong(2))));} c.close();'
```

## Communication (am intents)

```bash
am start -a android.intent.action.SENDTO -d "mailto:user@example.com" --es android.intent.extra.SUBJECT "Subj" --es android.intent.extra.TEXT "Body"
am start -a android.intent.action.SENDTO -d "smsto:+1234567890" --es sms_body "Msg"
am start -a android.intent.action.DIAL -d "tel:+1234567890"
am start -a android.intent.action.SEND -t "text/plain" --es android.intent.extra.TEXT "Content"
am start -a android.intent.action.VIEW -d "geo:0,0?q=Tokyo+Tower"
am start -a android.intent.action.VIEW -d "https://example.com"
am start -a android.settings.SETTINGS
```

## am Extra Types
`--es` String | `--ei` Int | `--el` Long | `--ez` Boolean | `--ef` Float

## Storage
`/root/` persists. `/sdcard/` for Android shared storage (needs permission). Write files to `context.getCacheDir()` from bsh for host-accessible paths.
