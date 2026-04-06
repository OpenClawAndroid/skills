---
name: twitter-auto-post-shizuku
description: Automatically publish short text posts to X/Twitter via Shizuku and Android UI automation. Use when the user asks to open Twitter and post text fully autonomously without manual tapping.
---

# Twitter Auto Post via Shizuku

Execute this deterministic workflow end-to-end unless blocked.

1. Validate prerequisites.
- Confirm `shizuku` command is available.
- Confirm Twitter package exists with `shizuku pm list packages | rg -i com.twitter.android`.
- If missing, stop and report the blocker.

2. Start compose intent with user text.
- Run:
```bash
shizuku am start -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT "<TEXT>" -p com.twitter.android
```

3. Handle Android share chooser automatically.
- Dump UI: `shizuku uiautomator dump /sdcard/uidump.xml`.
- If package is `com.android.intentresolver`, locate app tile with text `Post` and tap center of its bounds using `shizuku input tap X Y`.
- If chooser shows buttons like `Once`/`Always`, still pick `Post` tile first.

4. Confirm Twitter composer screen.
- Dump UI again and verify package `com.twitter.android`.
- Verify tweet text field contains the intended text (for example node id `com.twitter.android:id/tweet_text`).
- Locate post button (`com.twitter.android:id/button_tweet` or visible text `POST`) and tap center.

5. Post-submission verification.
- Wait 2-3 seconds.
- Dump UI again.
- Report whether compose screen closed and what foreground package is now.
- State clearly if post status is probable vs confirmed.

6. Reporting format.
- Include the exact commands used.
- Include key UI checks discovered in dumps: package names, target node ids/text, and tap coordinates.
- If any step fails, stop immediately and report the precise failing step.

## Guardrails

- Do not post if the text is empty.
- Do not post multiple times unless user explicitly requests retries.
- Do not modify account settings or permissions.
- Keep actions limited to composing and posting one message.
