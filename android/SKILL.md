---
name: Android Device Access
description: Access camera, microphone, calendar, location, clipboard, notifications, battery, contacts, SMS, TTS, typed Android intents, Shizuku privileged shell, and run Java on the Android host via bsh and termux- commands
---

# Android Device Access

You run inside proot on Android. Four ways to interact with the device:
1. **termux-\* commands** — simple shell commands for common tasks
2. **intent** — typed Android app/activity/service/broadcast control
3. **bsh** — BeanShell interpreter for direct Android Java API access
4. **shizuku** — privileged shell commands via ADB/root identity

## termux-* Commands (simple device access)

| Command | Usage |
|---------|-------|
| `termux-camera-photo [-c 0\|1] <file.jpg>` | Take photo |
| `termux-clipboard-get` / `termux-clipboard-set "text"` | Clipboard |
| `termux-location` | GPS/network location (JSON) |
| `termux-device-info` | Model, manufacturer, SDK |
| `termux-notification -t "Title" -c "Content" [--id N]` | Show notification |
| `termux-calendar-list` | List calendar events |
| `termux-calendar-insert -t "Title" -d "Description" [-b start_ms] [-e end_ms] [-a "Location"]` | Insert calendar event |
| `termux-battery-status` | Battery level, status, temperature |
| `termux-vibrate [-d ms]` | Vibrate device (default 200ms) |
| `termux-torch [on\|off]` | Toggle flashlight |
| `termux-volume [level]` | Get/set media volume |
| `termux-wifi-connectioninfo` | WiFi SSID, IP, signal |
| `termux-tts-speak "text"` | Text-to-speech |
| `termux-toast "text"` | Show Android toast |
| `termux-share "text"` | Android share intent |

For contacts and SMS drafts, use Shizuku `content query` and `am start`. Query phones explicitly; never assume a contact name is SMS-capable.

## Typed Intent Bridge

Prefer `intent` for app launch, service start, broadcasts, `VIEW`, `SEND`, and typed extras. It avoids shell quoting problems in `shizuku am ...` and avoids writing Java snippets for common app/service control.

```bash
intent '{"start":"activity","action":"android.intent.action.VIEW","data":"https://example.com"}'
intent '{"start":"activity","action":"android.settings.SETTINGS"}'
intent '{"start":"activity","action":"android.intent.action.SEND","type":"text/plain","package":"com.twitter.android","extras":[{"key":"android.intent.extra.TEXT","type":"string","value":"hello world"}]}'
intent '{"start":"service","component":"gptos.intelligence.assistant/app.anyclaw.service.GatewayService","action":"app.anyclaw.action.STOP","respond_before_start":true}'
```

Supported fields: `start` (`activity`, `service`, `broadcast`), `action`, `package`, `component`, `component_object`, `data`, `type`, `categories`, `flags`, `extras`, `respond_before_start`, and `defer_ms`. Extras support `string`, `int`, `long`, `float`, `double`, `boolean`, `uri`, and primitive arrays.

Use `respond_before_start:true` for destructive actions that can kill the current proot/SSH session, such as stopping the AnyClaw gateway. The bridge writes a successful response first, then starts the requested intent shortly after.

Use `bsh` when you need arbitrary Android APIs or callbacks. Use `shizuku` when the operation needs shell/ADB identity, protected paths, package manager control, `dumpsys`, or UI automation.

## Shizuku — Privileged Shell (ADB/root)

Shizuku lets you run commands with ADB shell (UID 2000) or root identity via the `rish` binary. Requires the Shizuku app to be installed and running on the device.

```bash
shizuku ls /data/data
shizuku pm list packages
shizuku settings put global adb_enabled 1
shizuku dumpsys battery
shizuku am force-stop com.example.app
shizuku cmd package install-existing com.example.app
```

Shizuku runs commands as the shell user (same as `adb shell`), giving access to:
- Protected paths (`/data`, `/system`)
- Package management (`pm install/uninstall`)
- System settings (`settings put/get`)
- Service management (`dumpsys`, `cmd`)
- App control (`am force-stop`, `am start`)
- UI automation (`uiautomator dump`, `input tap/swipe`)
- Grant permissions: `shizuku appops set gptos.intelligence.assistant MANAGE_EXTERNAL_STORAGE allow`

The AnyClaw `shizuku` wrapper propagates remote nonzero exits. Some `rish` builds drop the original remote stderr; in that case AnyClaw emits a generic stderr message such as `shizuku: command failed with exit 127`. Treat the exit code as authoritative and do not assume empty original stderr means success.

### UI Automation via Shizuku

```bash
shizuku uiautomator dump /sdcard/ui.xml && cat /sdcard/ui.xml
shizuku input tap 500 800
shizuku input swipe 500 1500 500 500 300
shizuku input text "hello"
shizuku input keyevent KEYCODE_HOME
shizuku screencap -p /sdcard/screen.png
```

If Shizuku is not installed, the connector UI shows a dialog with install link.

For complex UI parsing, prefer writing a short script and running it on-device. Long one-line Python/regex commands are easy to break across host shell, SSH, Android shell, and Python quoting.

When transferring scripts from macOS, use a portable base64 form:

```bash
base64 -i /tmp/script.sh | tr -d '\n'
# or: base64 < /tmp/script.sh | tr -d '\n'
```

Do not assume Linux-style `base64 /tmp/script.sh` works on macOS.

### App Launch Verification

Launch apps by package/activity, then verify foreground state with `dumpsys window`:

```bash
shizuku am start -n com.spotify.music/.MainActivity
shizuku dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
```

If `uiautomator dump` does not show stable labels, trust foreground state over grepping UI text. `dumpsys window` can sometimes be hard to parse or return no useful match; fall back to a bounded `dumpsys activity activities` filter. For large producers, put the pipe inside Shizuku's remote shell so the full dump is not streamed back to proot:

```bash
shizuku sh -c 'dumpsys activity activities | grep -E "mResumedActivity|topResumedActivity" | head -n 5'
```

On MIUI, `shizuku dumpsys activity activities` can time out with a battery-optimization warning even when short Shizuku commands work. Prefer `shizuku uiautomator dump` for intent-launch smoke tests, and use `dumpsys window` only as a bounded final foreground check.

## BeanShell (bsh) — Java on Android Host

```bash
bsh -c '<code>'          # Execute inline Java
bsh -e '<expression>'    # Evaluate and print result
bsh <file.bsh>           # Execute file
```

### Built-in Variables

`context`, `app`, `activity`, `handler`, `bridge`, `prootManager`, `pm`, `contentResolver`, `runtime`

### Callback Helpers

| Helper | Methods |
|--------|---------|
| `camera` | `info()`, `takePhoto(path)`, `takePhoto(path, cameraId)` |
| `audio` | `record(path)`, `record(path, durationSec)` |
| `location` | `getCurrentLocation()`, `getCurrentLocation(timeoutSec)` |
| `sensor` | `read(sensorType)` — 1=accel, 2=magnetic, 4=gyro |
| `clipboard` | `get()`, `set(text)` |

```bash
bsh -e 'camera.takePhoto(context.getCacheDir().getAbsolutePath() + "/photo.jpg")'
bsh -e 'camera.info()'
bsh -e 'audio.record(context.getCacheDir().getAbsolutePath() + "/rec.m4a", 5)'
bsh -e 'sensor.read(1)'
bsh -e 'clipboard.get()'
bsh -e 'Build.MODEL + " " + Build.MANUFACTURER'
```

Camera capture requires AnyClaw to be foreground. If capture fails with `camera requires AnyClaw foreground activity` or `Fail to connect to camera service`, bring AnyClaw to foreground first:

```bash
shizuku input keyevent KEYCODE_WAKEUP
shizuku monkey -p gptos.intelligence.assistant 1
termux-camera-photo /root/photo.jpg
ls -l /root/photo.jpg
```

If the screen is off, keyguard/AOD is showing, or focus is `NotificationShade`, AnyClaw is not a real foreground activity even when its task appears visible in activity dumps. Check screen/focus before retrying:

```bash
shizuku dumpsys power | grep -E 'mWakefulness|Display Power'
shizuku sh -c 'dumpsys window | grep -E "mCurrentFocus|mFocusedApp|mKeyguardShowing" | head -n 5'
```

Treat `termux-camera-photo` or `camera.takePhoto(...)` as failed if it returns an `error:` string or the expected output file does not exist; do not rely on a wrapper exit alone.

For `bsh` camera calls, use an Android app path, not `/root`:

```bash
bsh -e 'camera.takePhoto(context.getCacheDir().getAbsolutePath() + "/photo.jpg")'
```

### BeanShell Callbacks

BeanShell CAN implement Java interfaces — use simplified syntax without types:

```bash
bsh -c 'cb = new Runnable() { run() { print("callback!"); } }; cb.run();'
```

### Permissions

```bash
bsh -e 'androidx.core.content.ContextCompat.checkSelfPermission(context, "android.permission.CAMERA") == PackageManager.PERMISSION_GRANTED ? "granted" : "denied"'
# Grant via adb: adb shell pm grant gptos.intelligence.assistant android.permission.RECORD_AUDIO
```

### Notifications (bsh)

```bash
bsh -c 'NotificationManager nm = (NotificationManager)context.getSystemService("notification"); String ch = "bsh_ch"; nm.createNotificationChannel(new NotificationChannel(ch, "BSH", NotificationManager.IMPORTANCE_DEFAULT)); nm.notify(42, new Notification.Builder(context, ch).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Title").setContentText("Body").build());'
```

### Device Info (bsh)

```bash
bsh -c 'BatteryManager bm = (BatteryManager)context.getSystemService("batterymanager"); print(bm.getIntProperty(4) + "%");'
bsh -e 'pm.getInstalledPackages(0).size() + " packages"'
```

Auto-imports: `android.os.*`, `android.content.*`, `android.provider.*`, `android.app.*`, `android.net.*`, `android.media.*`, `android.hardware.*`, `android.location.*`, `java.io.*`, `java.util.*`, `java.net.*`. Built-in `print()`, `runOnUi(Runnable)`.

## Communication (am intents)

```bash
am start -a android.intent.action.SENDTO -d "mailto:user@example.com" --es android.intent.extra.SUBJECT "Subj" --es android.intent.extra.TEXT "Body"
am start -a android.intent.action.SENDTO -d "smsto:+1234567890" --es sms_body "Msg"
am start -a android.intent.action.DIAL -d "tel:+1234567890"
am start -a android.intent.action.SEND -t "text/plain" --es android.intent.extra.TEXT "Content"
am start -a android.intent.action.VIEW -d "geo:0,0?q=Tokyo+Tower"
am start -a android.intent.action.VIEW -d "https://example.com"
am start -a android.settings.SETTINGS
am start -a android.intent.action.SET_ALARM --ei android.intent.extra.alarm.HOUR 8 --ei android.intent.extra.alarm.MINUTES 30
```

am extra types: `--es` String | `--ei` Int | `--el` Long | `--ez` Boolean | `--ef` Float

### Contacts and SMS Drafts

Find contacts by display name:

```bash
shizuku content query --uri content://com.android.contacts/contacts --projection display_name --where "display_name LIKE '%Igor Levochkin%'"
```

Find SMS-capable phone rows:

```bash
shizuku content query --uri content://com.android.contacts/data --projection display_name:data1:mimetype:contact_id --where "display_name LIKE '%Igor Levochkin%' AND mimetype='vnd.android.cursor.item/phone_v2'"
```

Only open an SMS draft when a phone number is present. Use `smsto:+NUMBER`; do not put unescaped contact names or spaces in `smsto:`.

```bash
shizuku am start -a android.intent.action.SENDTO -d "smsto:+1234567890" --es sms_body "Draft message only"
shizuku dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
```

Do not send SMS unless the user explicitly asks.

### Notifications

Send and verify a test notification:

```bash
termux-notification -t "AnyClaw E2E" -c "notification test" --id 424242
shizuku dumpsys notification --noredact | awk '/id=424242/,/stats=/' | grep -E 'android.title|android.text|gptos.intelligence.assistant'
```

If Shizuku is not running, verify notifications through the app process with `bsh`:

```bash
bsh -e 'import android.service.notification.StatusBarNotification; NotificationManager nm = (NotificationManager)context.getSystemService("notification"); StatusBarNotification[] a = nm.getActiveNotifications(); print(a == null ? "null" : ("count=" + a.length)); if (a != null) for (StatusBarNotification n : a) print(n.getId() + " " + n.getPackageName() + " " + n.getNotification().extras.getString("android.title") + " | " + n.getNotification().extras.getCharSequence("android.text"));'
```

For strict test cleanup, do not assume `termux-notification-remove` exists. Cancel AnyClaw test notifications through `bsh`:

```bash
bsh -c 'NotificationManager nm = (NotificationManager)context.getSystemService("notification"); nm.cancel(424242); print("CANCELED");'
```

Broad Shizuku notification dumps can be very large. A pipe can print the matching notification but still return a bad pipeline exit. For strict assertions, prefer the `bsh` active-notification check above.

When using Shizuku with long `dumpsys` output, avoid fragile remote pipes that can leave `rish` running. Prefer a bounded command or run one command at a time and check processes after timeouts.

### Gateway Start / Stop

`GatewayService` is not exported, so direct host ADB `am startservice ...GatewayService` is expected to fail. To test the same in-app path as the notification Stop action, call the service through the in-app intent bridge:

```bash
intent '{"start":"service","component":"gptos.intelligence.assistant/app.anyclaw.service.GatewayService","action":"app.anyclaw.action.STOP","respond_before_start":true}'
```

## Storage

`/root/` persists inside proot.

**Play Store version**: Cannot request full file access. Use Shizuku or download the APK version instead.

### APK version (full access)

Download APK: https://github.com/friuns2/openclaw-android-assistant/releases

The APK version has `MANAGE_EXTERNAL_STORAGE` permission. After enabling via Storage connector (Settings toggle), `/sdcard/` is directly accessible:

```bash
ls /sdcard/Download/
cp /sdcard/DCIM/Camera/photo.jpg /root/photo.jpg
cp /root/output.pdf /sdcard/Download/
find /sdcard/ -name "*.pdf" -maxdepth 2
```

### Shizuku Storage (Play Store or APK)

Install Shizuku: https://shizuku.rikka.app/download/

With Shizuku connected, full filesystem access is available regardless of version:

```bash
shizuku ls /sdcard/Download/
shizuku cat /sdcard/Documents/notes.txt
shizuku cp /sdcard/DCIM/Camera/photo.jpg /data/local/tmp/
shizuku find /sdcard/ -name "*.pdf" -maxdepth 2
shizuku mv /sdcard/old.txt /sdcard/new.txt
```

Copy files between proot and sdcard via Shizuku:
```bash
shizuku cat /sdcard/file.txt > /root/file.txt
cp /root/file.txt /tmp/file.txt
shizuku cp /data/user/0/gptos.intelligence.assistant/cache/file.txt /sdcard/Download/
```
if shizuku is not available, reply with link to Shizuku download: https://shizuku.rikka.app/download/

sdcard/ full storage access only possible with github version, google play limits storage access - APK download: https://friuns2.github.io/openclaw-android-assistant/
