# Testing `search-codex-chats`

Use this to compare search techniques for local Codex chat history in this environment.

## Goal

Compare which approach works best for:
- latest threads by project
- project-scoped chat search
- persistence/memory-style queries

Main techniques:
- raw `rg`
- structured `search_chats.py`
- `zvec` semantic search

## Sources

- `/Users/igor/.codex/sessions`
- `/Users/igor/.codex/archived_sessions`
- `/Users/igor/.codex/state_5.sqlite`

## Fast direct checks

Structured thread listing:

```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py \
  --project "/Users/igor/Git-projects/codex-web-local" \
  --threads-with-titles \
  --sort-threads-by-date \
  --newest-first \
  --limit 3
```

Structured text search:

```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py \
  --project "/Users/igor/Git-projects/codex-web-local" \
  --query "workspace-roots-state|localStorage|thread-draft|persist|persistence" \
  --regex \
  --dedupe \
  --newest-first \
  --limit 10
```

Raw `rg` search:

```bash
rg -l -g "*.jsonl" \
  -e "/Users/igor/Git-projects/codex-web-local" \
  -e "/Users/igor/.codex/worktrees/.*/codex-web-local" \
  /Users/igor/.codex/sessions /Users/igor/.codex/archived_sessions \
| xargs rg -n "persist|persistence|localStorage|thread-draft|workspace-roots-state" \
| sed -n '1,20p'
```

## Variant benchmarking with `codex exec`

Create one workspace per technique:

```bash
mkdir -p /private/tmp/skill-bench/{rg-technique,script-technique,zvec-technique}/.agents/skills
```

Put one local skill variant in each workspace and keep the task identical.

Recommended local variant names:
- `chat-search-rg`
- `chat-search-script`
- `chat-search-zvec`

Run each variant with the same prompt shape:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /private/tmp/skill-bench/script-technique \
  -o /private/tmp/skill-bench/script-technique/result.txt \
  'Use the chat-search-script skill. For /Users/igor/Git-projects/codex-web-local, list the latest 3 threads with titles, then find 5 useful hits about persistence or memory behavior. Prefer the shortest reliable path. If something fails, explain it precisely.'
```

If testing `zvec`, use `workspace-write` and an explicit writable corpus dir:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox workspace-write \
  --cd /private/tmp/skill-bench/zvec-technique \
  -o /private/tmp/skill-bench/zvec-technique/result.txt \
  'Use the chat-search-zvec skill. For /Users/igor/Git-projects/codex-web-local, list the latest 3 threads with titles, then run semantic search. If zvec fails, report the exact error.'
```

The underlying command must use `--zvec-corpus-dir /tmp/...` or another writable temp path, because the default corpus dir under `~/.codex` may be blocked in sandboxed runs.

## What to compare

For each technique, record:
- did it finish?
- end-to-end `codex exec` time
- did it use the intended method?
- were the results clean and relevant?
- what failed?

## How to judge

- Best raw speed: usually `rg`
- Best final answer quality: usually `search_chats.py`
- Best semantic search: `zvec`, only if corpus export and local HTTP ingest/search both work

Do not judge only by primitive speed. Judge the full agent workflow.

## Current practical default

Use `search_chats.py` as the default skill path.

Use `rg` for:
- fast forensic checks
- confirming whether a string exists at all
- debugging raw session files

Use `zvec` only when:
- the service is reachable
- the corpus dir is writable
- local HTTP calls to the service are allowed
