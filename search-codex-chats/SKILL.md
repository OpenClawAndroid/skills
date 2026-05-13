---
name: search-codex-chats
description: Search local Codex chat history by project, thread title, or message text across sessions and archived_sessions, returning thread IDs, project/cwd values, timestamps, and snippets. Use when the user asks to find prior chats, filter history to one project, discover threads about a topic, or locate historical Codex messages.
---

# Search Codex Chats

Use this skill when the user wants full-text search over local Codex chats.
Use the bundled script for normal answers. Raw `rg` is only for debugging or quick existence checks.

## Scope

Search these sources:
- `/Users/igor/.codex/sessions`
- `/Users/igor/.codex/archived_sessions`
- `/Users/igor/.codex/memories/rollout_summaries` for per-thread summaries
- `/Users/igor/.codex/state_5.sqlite` for thread metadata

Prefer structured extraction from JSONL message fields to avoid false positives from encrypted/reasoning blobs.
Use rollout summaries before raw chat search when the user asks broad questions like "what did we discuss about X?", "find prior work about X", or "which thread covered X?". Use raw sessions when the user needs exact quotes, line-level evidence, full transcript context, or the summary hit is not enough.

Do not inspect `/Users/igor/.codex/memories/MEMORY.md` for normal raw chat-history answers; it is a registry over summaries. Use it only when you need to locate relevant rollout summaries faster than searching summary files directly.

## Workflow

1. For broad prior-work discovery, search rollout summaries first:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --source summaries --query "project persistence" --newest-first --limit 8
```

If a summary result is enough, answer from that summary and name the source file. If exact evidence is needed, use the returned `thread_id` or terms to search raw sessions next.

2. Run raw keyword search:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "elon musk"
```

3. For broad raw scans, include partial matches:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "musk" --regex
```

If the user really wants threads about a topic rather than body-text matches, prefer title query:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --title-query "persistence|draft|workspace-roots|localstorage" --query-mode title --newest-first --limit 8
```

4. Filter by exact absolute project/cwd path:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "memory"
```
Exact project paths include the whole project family by default:
- a repo root path includes matching worktree chats
- a worktree path includes the repo root and sibling worktree chats for the same repo name
- by default, noisy injected preambles such as app-context and AGENTS boilerplate are excluded from text matches

5. Filter by project/cwd substring:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "codex-web-local" --project-contains --query "memory"
```

For better "useful hits" ranking, use hybrid mode:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "workspace-roots-state|localStorage|thread-draft|persistence" --title-query "persistence|draft|workspace-roots|localstorage" --query-mode hybrid --regex --newest-first --limit 10 --title-limit 2
```

6. List discovered projects:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --list-projects
```

7. If the user asks for unique threads only:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only
```

If they want those threads ordered by date, add:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only --sort-threads-by-date
```

8. If the user asks for all thread IDs and titles for a project:
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
- script rows are tab-separated and title/snippet cells are normalized to one line

When relevant, deduplicate mirrored pairs (`event_msg` and `response_item`) by `(thread_id, normalized_text)`.

Normal search output excludes injected developer/system preambles, skill blocks, and subagent notifications by default so results are more useful for actual chat-content queries.
