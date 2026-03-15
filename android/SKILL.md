# Android Device & Intents

You run inside proot on Android. Access device hardware via `termux-*` commands (native bridge) and launch Android actions via `am`.

## Device Commands

| Command | Usage |
|---------|-------|
| `termux-camera-photo [-c 0\|1] <file.jpg>` | Take photo |
| `termux-calendar-list [--from YYYY-MM-DD] [--to YYYY-MM-DD]` | List calendar events |
| `termux-location` | GPS/network location (JSON) |
| `termux-notification -t "Title" -c "Content" [--id N]` | Show/update notification |
| `termux-clipboard-get` / `termux-clipboard-set "text"` | Clipboard |
| `termux-device-info` | Model, manufacturer, SDK, etc. |

## Communication (am intents)

```bash
# Email
am start -a android.intent.action.SENDTO -d "mailto:user@example.com" --es android.intent.extra.SUBJECT "Subj" --es android.intent.extra.TEXT "Body"
# SMS
am start -a android.intent.action.SENDTO -d "smsto:+1234567890" --es sms_body "Msg"
# Phone
am start -a android.intent.action.DIAL -d "tel:+1234567890"
# Share
am start -a android.intent.action.SEND -t "text/plain" --es android.intent.extra.TEXT "Content"
```

## Navigation & Apps

```bash
# Maps
am start -a android.intent.action.VIEW -d "geo:0,0?q=Tokyo+Tower"
# URL
am start -a android.intent.action.VIEW -d "https://example.com"
# App Store
am start -a android.intent.action.VIEW -d "market://details?id=com.app.pkg"
# Settings
am start -a android.settings.SETTINGS
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d "package:gptos.intelligence.assistant"
```

## Alarms & Calendar

```bash
# Alarm
am start -a android.intent.action.SET_ALARM --ei android.intent.extra.alarm.HOUR 8 --ei android.intent.extra.alarm.MINUTES 30
# Timer
am start -a android.intent.action.SET_TIMER --ei android.intent.extra.alarm.LENGTH 300
# Calendar event
am start -a android.intent.action.INSERT -t "vnd.android.cursor.dir/event" --es title "Meeting" --es eventLocation "Office"
```

## am Extra Types
`--es` String | `--ei` Int | `--el` Long | `--ez` Boolean | `--ef` Float

## Storage
`/root/` persists. `/sdcard/` for Android shared storage (needs permission).
