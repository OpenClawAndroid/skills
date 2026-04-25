---
name: search-codex-chats
description: Search all local Codex chat logs for keywords or phrases across sessions and archived_sessions, returning matching thread IDs, project/cwd values, timestamps, paths, and snippets. Use when the user asks to scan chats, find mentions, filter chats by project, or locate historical messages in Codex.
---

# Search Codex Chats

Use this skill when the user wants full-text search over local Codex chats.

## Scope

Search these sources:
- `/Users/igor/.codex/sessions`
- `/Users/igor/.codex/archived_sessions`

Prefer structured extraction from JSONL message fields to avoid false positives from encrypted/reasoning blobs.

## Workflow

1. Run keyword search:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "elon musk"
```

2. For broad scans, include partial matches:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "musk" --regex
```

3. Filter by exact absolute project/cwd path:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "memory"
```
Exact project paths include the whole project family by default:
- a repo root path includes matching worktree chats
- a worktree path includes the repo root and sibling worktree chats for the same repo name
- by default, noisy injected preambles such as app-context and AGENTS boilerplate are excluded from text matches

4. Filter by project/cwd substring:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "codex-web-local" --project-contains --query "memory"
```

5. List discovered projects:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --list-projects
```

6. If the user asks for unique threads only:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only
```

If they want those threads ordered by date, add:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only --sort-threads-by-date
```

7. If the user asks for all thread IDs and titles for a project:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-with-titles
```

To sort those thread listings by date:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-with-titles --sort-threads-by-date
```

To ask for only the newest few threads directly:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-with-titles --sort-threads-by-date --newest-first --limit 3
```

If you intentionally need injected app/skill instructions in matches, opt back in:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "memory" --include-boilerplate
```

## Output conventions

Return:
- total matches
- unique thread IDs
- unique project/cwd count
- for each match: timestamp, thread ID, project/cwd, file:line, short snippet

When relevant, deduplicate mirrored pairs (`event_msg` and `response_item`) by `(thread_id, normalized_text)`.

Normal search output excludes injected developer/system preambles by default so results are more useful for actual chat-content queries.
