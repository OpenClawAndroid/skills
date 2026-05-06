---
name: anyclaw-publish
description: Build and publish beautiful web apps to Anyclaw hosting using the REST API. Use when asked to create, deploy, publish, update, or list hosted apps (both local dev and production).
---

# Anyclaw Publish

## When to use

Use this skill when building or publishing web apps on Anyclaw via the REST API:

- `POST /api/deploy` — upload an app and receive a claim URL
- `GET /api/apps` — list all apps

Creating, building, updating, or improving an Anyclaw app includes publishing unless the user explicitly says not to deploy.

## Default workflow (Mandatory)

For app creation/update requests:

1. Create/update files, including an app icon and `app.json`.
2. ZIP the app with a no-spaces path.
3. Build a `site_map` list for all major views/pages when the app has multiple views/pages (examples: `#settings`, `/pricing`, `about.html`).
4. Deploy to production with `POST /api/deploy` and `site_map` when available. If `site_map` is omitted, the server captures `/` by default.
5. Reply only with the requested `app_id` and `claim_url` from the deploy response.

Do not stop at local files when production deployment is possible. Use local dev only when explicitly requested or targeted.

## Design Standards (Default when not specified)

When stack is not specified, default to fast iteration stack:
- HTML + Vue 3 CDN + Tailwind CDN + https://picsum.photos
- No build step unless explicitly requested

When the user does not provide design direction, use these defaults:
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

### Icon (`icon.svg` or existing PNG)
Generate a custom SVG icon for the app unless a suitable PNG icon already exists. The icon should:
- Be a clean, modern, recognizable symbol related to the app's purpose
- Use **bright, vibrant colors** with good contrast — avoid dark/black backgrounds
- Use a colored or white background with a bold accent shape
- Work at small sizes (simple shapes, no fine detail)
- Prefer `icon.svg` in the project root for newly created icons
- Use an existing PNG icon when the project already has a good one; place it at the ZIP root as `icon.png` or keep its existing relative path and reference that path in `app.json`


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

### Screenshots (Mandatory)
- Keep screenshots small:
  - landscape: `1366x768`
  - portrait: `768x1366`
- Provide all major app views in `site_map` during deploy; server auto-captures both orientations for each entry.
- If no `site_map` is provided, the server captures the front page (`/`) in both orientations.
- Prefer concise page/view coverage over redundant near-duplicate routes.

## Endpoints

| Environment | Base URL | Deploy | List |
|---|---|---|---|
| **Production** | `https://anyclaw.store` | `POST /api/deploy` | `GET /api/apps` |
| **Local dev** | `http://localhost:<PORT>` (set by `npm run dev`) | `POST /api/deploy` | `GET /api/apps` |

Use local when the local dev server is running (`cd /Users/igor/Git-projects/incus-mcp-php-hosting && npm run dev`).
If you run `npm run dev`, capture the printed port in its output and use that value as `<PORT>`.
Use production for real deployments.

## Deploy

Create a ZIP of your app, base64-encode it, then deploy with curl:

```bash
ZIP_B64=$(base64 < /path/to/app.zip | tr -d '\n')
curl -X POST <BASE_URL>/api/deploy \
  -H "Content-Type: application/json" \
  -d "{
    \"app_id\": \"my-app\",
    \"zip_b64\": \"$ZIP_B64\",
    \"app_type\": \"<web_app|website|game>\",
    \"site_map\": [\"/\", \"#settings\", \"/pricing\", \"about.html\"]
  }"
```

Set `app_type` to categorize the app:
- `website` — informational/marketing sites, landing pages, company sites, restaurant/kitchen/studio sites, portfolios, blogs, documentation, and other content-first sites
- `web_app` — interactive applications, dashboards, tools, authenticated apps, productivity apps, and app-like utilities
- `game` — browser games

If the user asks for a "site", "website", "landing page", "homepage", "marketing page", "portfolio", "blog", "docs", "restaurant site", or similar content-first project, deploy with `app_type: "website"`.

Do not republish a website as `web_app` just to get PWA install behavior. Website deploys intentionally keep `app_type: "website"` and still get an Anyclaw store/detail page at `/install`.

Deploy response returns `claim_token` and `claim_url`. Do not claim uploads from this skill; return the claim link to the user.

All app types are claimed through the returned claim URL. Only `web_app` and `game` deploys get manifests, service workers, PWA icons, and an install button after claim. `website` deploys do not get PWA assets or install prompts.


## List apps

```bash
curl <BASE_URL>/api/apps
```

## URL Structure

- Claim page: `<base>/claim/<claim-token>`
- Listing: `<base>/`

## Completion reply

After successful deployment, reply with a short, friendly, non-technical message like:

> Your app is uploaded! Open it here: <claim-url>

Do not dump raw JSON or technical deployment details. Just share the claim link.

## Common mistakes to avoid

- Do NOT use `--headed` with Playwright — always headless
- Do NOT forget to close the browser after screenshots
- Do NOT create dark/black SVG icons — use bright, vibrant colors
- Do NOT skip the `app_type` param — set it to match your app's category
- Do NOT change `app_type` from `website` to `web_app` to get PWA install behavior; websites have a store/detail page but no PWA install button
- Do NOT skip `site_map` when there are multiple important views/pages; single-page apps can rely on the server default front-page screenshots
- Do NOT dump raw JSON responses — give the user a friendly message with links
- Do NOT create the ZIP path with spaces — use hyphens in names

## Response handling

- Always return the requested `app_id` and `claim_url` from the deploy response.
- If deploy fails, return the full API error and the command used.
- Iterative updates use the same deploy flow and should still return the new claim links.
