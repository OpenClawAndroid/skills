---
name: CodexUI Dev Mode
description: Modify your own UI when running in dev mode (codexUI source at /root/codexUI)
---

# CodexUI Dev Mode

When running in "dev" version, CodexUI is cloned from `https://github.com/friuns2/codexUI` at `/root/codexUI` and served with Vite dev server (hot-reload).

## Making Changes
Edit files in `/root/codexUI/` — Vite auto-reloads the browser.

Key directories:
- `src/components/` — Vue components
- `src/views/` — Page views
- `src/composables/` — Shared logic
- `src/assets/` — Static assets

## Pull Latest
```bash
cd /root/codexUI && git pull
```

## Restart After Config Changes
If you modify `vite.config.*` or `package.json`, restart Codex from the Android UI (Stop → Start).

## Build
```bash
cd /root/codexUI && npm run build
```
Output in `dist/`.
