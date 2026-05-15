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
When the user gives specific thread IDs, use `--thread-id` first. Do not pass a thread UUID as `--query`, and do not start with `rg` or `MEMORY.md` for that case. The script also auto-promotes a bare UUID query into a thread filter, but skill users should call `--thread-id` explicitly.
For thread-ID lookups, the script searches the matching rollout summary first and falls back to raw session JSONL only if the summary has no matching output.
For broad prior-work discovery, summary search is also usually cheaper and cleaner than raw transcript search. Use raw sessions when the user needs exact quotes, line-level evidence, full transcript context, or the summary hit is not enough.

Do not inspect `/Users/igor/.codex/memories/MEMORY.md` for normal raw chat-history answers; it is a registry over summaries. Use it only when you need to locate relevant rollout summaries faster than searching summary files directly.

## Workflow

1. If the prompt contains a thread UUID, extract it and run `--thread-id` before any other search:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --thread-id "019e20f4-8ae6-7bb3-a599-4af7d5efeccf" --limit 20
```

Add `--query` to filter inside those summaries:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --thread-id "019e20f4-8ae6-7bb3-a599-4af7d5efeccf" --query "verification" --limit 10
```

Use `--source sessions` only when exact raw transcript evidence is needed:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --thread-id "019e20f4-8ae6-7bb3-a599-4af7d5efeccf" --source sessions --query "pnpm run build"
```

Anti-pattern:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "019e20f4-8ae6-7bb3-a599-4af7d5efeccf"
```
This is accepted for compatibility, but it is less clear than `--thread-id` and previously led agents into broad noisy searches.

2. For broad prior-work discovery, search rollout summaries first:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --source summaries --query "project persistence" --newest-first --limit 8
```

If a summary result is enough, answer from that summary and name the source file. If exact evidence is needed, use the returned `thread_id` or terms to search raw sessions next.

3. Run raw keyword search:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "elon musk"
```

4. For broad raw scans, include partial matches:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --query "musk" --regex
```

If the user really wants threads about a topic rather than body-text matches, prefer title query:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --title-query "persistence|draft|workspace-roots|localstorage" --query-mode title --newest-first --limit 8
```

5. Filter by exact absolute project/cwd path:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "memory"
```
Exact project paths include the whole project family by default:
- a repo root path includes matching worktree chats
- a worktree path includes the repo root and sibling worktree chats for the same repo name
- by default, noisy injected preambles such as app-context and AGENTS boilerplate are excluded from text matches

6. Filter by project/cwd substring:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "codex-web-local" --project-contains --query "memory"
```

For better "useful hits" ranking, use hybrid mode:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --query "workspace-roots-state|localStorage|thread-draft|persistence" --title-query "persistence|draft|workspace-roots|localstorage" --query-mode hybrid --regex --newest-first --limit 10 --title-limit 2
```

7. List discovered projects:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --list-projects
```

8. If the user asks for unique threads only:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only
```

If they want those threads ordered by date, add:
```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py --project "/Users/igor/Git-projects/codex-web-local" --threads-only --sort-threads-by-date
```

9. If the user asks for all thread IDs and titles for a project:
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
- clickable thread links in Markdown form: `[Open thread](codex://threads/<thread_id>)`
- unique project/cwd count
- for each match: timestamp, thread ID, project/cwd, file:line, short snippet
- script rows are tab-separated and title/snippet cells are normalized to one line

When returning one or more thread IDs to the user, include the clickable Codex app link next to the ID or in the thread summary, for example:
`019e04cb-9670-7d91-be85-3ba35312170c` - [Open thread](codex://threads/019e04cb-9670-7d91-be85-3ba35312170c)

When relevant, deduplicate mirrored pairs (`event_msg` and `response_item`) by `(thread_id, normalized_text)`.

Normal search output excludes injected developer/system preambles, skill blocks, and subagent notifications by default so results are more useful for actual chat-content queries.
