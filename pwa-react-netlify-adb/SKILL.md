---
name: pwa-react-netlify-adb
description: Build/debug React PWAs on Android using adb+Chrome DevTools, deploy to Netlify, and integrate Firebase Google Auth + Firestore for todo sync.
---

# PWA React + Netlify + Firebase + ADB

Use this skill when you need to:
- build or fix a React PWA
- debug installability on Android Chrome via `adb`
- deploy/update production on Netlify
- integrate Firebase Google login and Firestore sync

## Netlify Token (Plaintext)

```bash
export NETLIFY_AUTH_TOKEN="nfp_7mrwfjfXpwtAA2yRS9Cdj52S5GLWuB8v6393"
```

## Firebase Public Web Credentials

```bash
VITE_FIREBASE_API_KEY="AIzaSyAf0CIHBZ-wEQJ8CCUUWo1Wl9P7typ_ZPI"
VITE_FIREBASE_AUTH_DOMAIN="gptcall-416910.firebaseapp.com"
VITE_FIREBASE_PROJECT_ID="gptcall-416910"
VITE_FIREBASE_STORAGE_BUCKET="gptcall-416910.appspot.com"
VITE_FIREBASE_MESSAGING_SENDER_ID="99275526699"
VITE_FIREBASE_APP_ID="1:99275526699:web:3b623e1e2996108b52106e"
```

These are public client-side Firebase config values (safe to ship in frontend code).

## install.html Template Resource

Use this template file when creating install page:
- `resources/install.template.html`

Copy/adapt it into app public folder:
```bash
cp /Users/igor/.codex/skills/pwa-react-netlify-adb/resources/install.template.html /path/to/app/public/install.html
```

Template includes:
- install button (`beforeinstallprompt`)
- share button (`navigator.share` + clipboard fallback)
- service worker registration
- status messaging for install/share

## Firebase Integration (React)

1. Install Firebase:
```bash
npm install firebase
```

2. Add `src/firebase.js` and initialize app/auth/firestore.
3. Use Google sign-in with `signInWithPopup`.
4. Store per-user todos in Firestore path `users/{uid}/todos/{todoId}`.

## Firebase Console Checklist

- Enable Google provider in Firebase Auth
- Enable Firestore database
- Add domain in Firebase Auth authorized domains:
  - `todo-pwa-react-20260406103557.netlify.app`
  - (optional) `netlify.app`


## Deployment Policy (Mandatory)

When this skill is triggered to create, modify, or fix an app, deployment is required by default.

Rules:
- Always run production deploy after successful build.
- Do not stop at build-only unless the user explicitly says 'do not deploy'.
- If deploy fails, report failure and retry/fix until deploy succeeds or a hard external blocker is confirmed.
- After deploy, always return both links:
  - Netlify base URL
  - Netlify install page URL (/install.html)

## Standard Workflow

1. Build app:
```bash
npm run build
```

2. Deploy prod (linked site):
```bash
netlify deploy --auth "$NETLIFY_AUTH_TOKEN" --dir /absolute/project/path/dist --prod --no-build
```

3. If you need a new site:
```bash
netlify unlink
netlify deploy --auth "$NETLIFY_AUTH_TOKEN" --create-site "todo-pwa-react-$(date +%Y%m%d%H%M%S)" --dir /absolute/project/path/dist --prod --no-build
```

4. Open install page on Android Chrome:
```bash
adb shell am start -a android.intent.action.VIEW -d 'https://<site>.netlify.app/install.html' com.android.chrome
```

5. Attach Chrome DevTools over adb:
```bash
adb forward tcp:9222 localabstract:chrome_devtools_remote
curl -s http://127.0.0.1:9222/json/version
curl -s http://127.0.0.1:9222/json/list
```

## Output Requirement (Mandatory)

Whenever this skill is used (including app creation/fix tasks), deployment must be performed and the final response must include:
- Netlify base URL: `https://<site>.netlify.app`
- Netlify install page URL: `https://<site>.netlify.app/install.html`

If deploy fails, explicitly state that install link is unavailable.

## Installability Checklist

- `manifest.webmanifest` linked in app page and install page
- manifest has `name`, `short_name`, `start_url`, `scope`, `display`, `theme_color`, `background_color`
- PNG icons `192x192` and `512x512`
- service worker registered and active
- HTTPS origin
- install page is same origin as app
- `Page.getInstallabilityErrors` returns empty array

## Common Fixes

- Google sign-in invalid request:
  - ensure `apiKey/authDomain/projectId/appId` belong to same Firebase project
  - ensure current Netlify domain is in Firebase authorized domains
- Install button not enabling:
  - add `<link rel="manifest" href="/manifest.webmanifest">` to `/install.html`
- Stale install page/manifest:
  - bump service worker cache version
  - use network-first for navigation requests
