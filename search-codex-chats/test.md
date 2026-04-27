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
- `search_chats.py --ranker bm25`

## Sources

- `/Users/igor/.codex/sessions`
- `/Users/igor/.codex/archived_sessions`
- `/Users/igor/.codex/state_5.sqlite`

## Workflow

Use this order:
1. analyze existing chats for the target project first
2. derive a few concrete topic questions from real prior work
3. ask those questions through `codex exec`
4. compare output quality and speed

Do not start with a vague prompt if you can mine the project history first.

## Fast direct checks

Analyze likely threads/topics first:

```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py \
  --project "/Users/igor/Git-projects/codex-web-local" \
  --title-query "persistence|draft|workspace-roots|localstorage|pinned|scroll" \
  --query-mode title \
  --newest-first \
  --limit 15
```

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
  --query "workspace-roots-state|localStorage|thread-draft|persistence" \
  --regex \
  --dedupe \
  --newest-first \
  --limit 10
```

BM25 text search:

```bash
python3 /Users/igor/.codex/skills/shared_skills/search-codex-chats/scripts/search_chats.py \
  --project "/Users/igor/Git-projects/codex-web-local" \
  --query "workspace roots state localStorage thread draft persistence" \
  --query-mode hybrid \
  --ranker bm25 \
  --newest-first \
  --limit 10 \
  --title-limit 2
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
mkdir -p /private/tmp/skill-bench/{rg-technique,script-technique}/.agents/skills
```

Put one local skill variant in each workspace and keep the task identical.

Recommended local variant names:
- `chat-search-rg`
- `chat-search-script`

Run each variant with the same prompt shape:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /private/tmp/skill-bench/script-technique \
  -o /private/tmp/skill-bench/script-technique/result.txt \
  'Use the chat-search-script skill. For /Users/igor/Git-projects/codex-web-local, list the latest 3 threads with titles, then find 5 useful hits about persistence or memory behavior. Prefer the shortest reliable path. If something fails, explain it precisely.'
```

Better prompt pattern after analyzing chats first:

```text
Use the <skill-name> skill.
For /Users/igor/Git-projects/codex-web-local, answer one concrete question from prior project history.
Examples:
- find threads about project persistence
- find threads about pinned-thread persistence
- find threads about scroll-position restore
- find threads about thread draft restore
Prefer title-based discovery first when the task is thematic.
Only then pull supporting snippets.
Keep the result concise.
```

## What to compare

For each technique, record:
- did it finish?
- end-to-end `codex exec` time
- did it use the intended method?
- were the results clean and relevant?
- did thread-title output stay one row per thread?
- what failed?

## How to judge

- Best raw speed: usually `rg`
- Best final answer quality: usually `search_chats.py`
- Best text ranking on broad thematic queries may shift between `heuristic` and `bm25`; measure both.
Do not judge only by primitive speed. Judge the full agent workflow.

## Current practical default

Use `search_chats.py` as the default skill path.

Use `rg` for:
- fast forensic checks
- confirming whether a string exists at all
- debugging raw session files

## Recommended test questions

Good project-specific questions for this repo:
- Which threads are about project persistence?
- Which threads are about pinned-thread persistence?
- Which threads are about scroll position per thread?
- Which threads are about draft restore after refresh or thread switch?
- Which threads mention `workspace-roots-state`, `threadWorkspaceRootHints`, `project-order`, or `composerThreadContextId`?
