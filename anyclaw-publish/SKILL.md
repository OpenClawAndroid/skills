---
name: anyclaw-publish
description: Build and publish beautiful web apps to Anyclaw hosting using the REST API. Use when asked to create, deploy, publish, update, or list hosted apps (both local dev and production).
---

# Anyclaw Publish

## When to use

Use this skill when building or publishing web apps on Anyclaw via the REST API:

- `POST /api/deploy` — deploy or update an app
- `GET /api/apps` — list all apps

Creating, building, updating, or improving an Anyclaw app includes publishing unless the user explicitly says not to deploy.

## Default workflow (Mandatory)

For app creation/update requests:

1. Create/update files, including `icon.svg` and `app.json`.
2. ZIP the app with a no-spaces path.
3. Deploy to production with `POST /api/deploy` and `update_existing=true`.
4. Reply only with `app_id`, app URL, and install URL.

Do not stop at local files when production deployment is possible. Use local dev only when explicitly requested or targeted.

## Design Standards (Mandatory)

When stack is not specified, default to fast iteration stack:
- HTML + Vue 3 CDN + Tailwind CDN + https://picsum.photos
- No build step unless explicitly requested

- Prioritize clean, minimalist aesthetics with excellent typography, generous whitespace, and smooth interactions.
- Use modern UI patterns: subtle shadows, rounded corners, smooth hover/focus states, and thoughtful micro-interactions.
- Ensure every component and page looks premium, polished, and visually appealing on both desktop and mobile.
- Apply consistent color schemes, harmonious spacing, and professional visual hierarchy.
- Make interfaces feel delightful and user-friendly while keeping them simple and elegant.
- Use toast components to inform the user about important events.
- Never create ugly or basic-looking designs — every change must result in something visually stunning.

## Firebase Usage (Mandatory when useful)

Use Firebase for login, signup, profiles, authenticated routes, user-owned data, persistence, or cross-device/shared state.

Use Firebase Auth for login apps. Use Firestore for user-owned data keyed by `auth.currentUser.uid`.

Do not use `localStorage` for fake login or durable app data unless the user explicitly requests a local-only prototype. `localStorage` is fine for transient UI state like theme, tips, drafts, or filters.

## Firebase Client Config

When an app needs Firebase, initialize Firebase with this client config:

```js
const firebaseConfig = {
  apiKey: "AIzaSyAf0CIHBZ-wEQJ8CCUUWo1Wl9P7typ_ZPI",
  authDomain: "gptcall-416910.firebaseapp.com",
  projectId: "gptcall-416910",
  storageBucket: "gptcall-416910.appspot.com",
  messagingSenderId: "99275526699",
  appId: "1:99275526699:web:3b623e1e2996108b52106e"
};
```

## App Assets (Mandatory)

Every app ZIP must include these assets before deployment:

### Icon (`icon.svg`)
Generate a custom SVG icon for the app. The icon should:
- Be a clean, modern, recognizable symbol related to the app's purpose
- Use **bright, vibrant colors** with good contrast — avoid dark/black backgrounds
- Use a colored or white background with a bold accent shape
- Work at small sizes (simple shapes, no fine detail)
- Be placed at `icon.svg` in the project root


### App metadata (`app.json`)
Include an `app.json` in the ZIP root:
```json
{
  "title": "My App",
  "description": "A clear, compelling description of what the app does.",
  "category": "Productivity",
  "icon": "icon.svg",
  (optional) "screenshots": ["screenshots/screenshot-1.png"] 
}
```

## Endpoints

| Environment | Base URL | Deploy | List |
|---|---|---|---|
| **Production** | `https://anyclaw.store` | `POST /api/deploy` | `GET /api/apps` |
| **Local dev** | `http://localhost:<PORT>` (set by `npm run dev`) | `POST /api/deploy` | `GET /api/apps` |

Use local when the local dev server is running (`cd /Users/igor/Git-projects/incus-mcp-php-hosting && npm run dev`).
If you run `npm run dev`, capture the printed port in its output and use that value as `<PORT>`.
Use production for real deployments.

## Deploy

Create a ZIP of your app, then deploy with curl:

```bash
curl -X POST <BASE_URL>/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "my-app",
    "zip_file_path": "/absolute/path/to/app.zip",
    "app_type": "web_app",
    "update_existing": true
  }'
```

Set `app_type` to categorize the app:
- `web_app` (default) — interactive web applications
- `website` — informational/marketing sites
- `game` — browser games

All types get an install page, manifest, service worker, and icons automatically.

### Alternative: base64 ZIP upload

```bash
ZIP_B64=$(base64 < /path/to/app.zip)
curl -X POST <BASE_URL>/api/deploy \
  -H "Content-Type: application/json" \
  -d "{
    \"app_id\": \"my-app\",
    \"zip_b64\": \"$ZIP_B64\",
    \"app_type\": \"web_app\",
    \"update_existing\": true
  }"
```

## List apps

```bash
curl <BASE_URL>/api/apps
```

## URL Structure

- App: `<base>/<claim-id>/<app-id>/`
- Install page: `<base>/<claim-id>/<app-id>/install`
- Listing: `<base>/`

## Completion reply

After successful deployment, reply with a short, friendly, non-technical message like:

> Your app is live! Open it here: <app-url>
> Install page: <install-url>

Do not dump raw JSON or technical deployment details. Just share the links.

## Common mistakes to avoid

- Do NOT use `--headed` with Playwright — always headless
- Do NOT forget to close the browser after screenshots
- Do NOT create dark/black SVG icons — use bright, vibrant colors
- Do NOT skip the `app_type` param — set it to match your app's category
- Do NOT dump raw JSON responses — give the user a friendly message with links
- Do NOT create the ZIP path with spaces — use hyphens in names

## Response handling

- Always return `app_id`, `url`, and `install_url` after publish.
- If deploy fails, return the full API error and the command used.
- Prefer `update_existing=true` for iterative updates unless user asks for strict create-only behavior.
