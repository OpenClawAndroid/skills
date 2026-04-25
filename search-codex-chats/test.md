# Testing a Skill with Codex CLI

This is a generic workflow for testing any Codex skill through `codex exec`.

## Goal

Verify that:
- Codex discovers the skill
- Codex reads and follows the skill
- the skill works from a clean prompt
- failures, bottlenecks, and missing instructions are visible

## 1. Pick a neutral test workspace

Use a simple directory that is not the skill directory itself if you want a more realistic test.

Example:

```bash
mkdir -p /tmp/skill-test
```

Or use any existing project:

```bash
cd /path/to/test/project
```

## 2. Confirm the skill path

Make sure the skill exists and has a valid `SKILL.md`.

```bash
ls /path/to/skill
sed -n '1,200p' /path/to/skill/SKILL.md
```

## 3. Run a direct skill-invocation test

Ask Codex explicitly to use the skill by name and perform one concrete task.

Template:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /path/to/test/project \
  'Use the <skill-name> skill. Perform this task: <concrete task>. Report what worked, what failed, and any friction in the skill instructions.'
```

Example shape:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /tmp/skill-test \
  'Use the my-skill skill. Perform this task: inspect the available commands and run the simplest valid example. Report what worked, what failed, and any friction in the skill instructions.'
```

## 4. Run a minimal-output test

Check whether the skill supports a concise, well-scoped request without extra prompting.

Template:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /path/to/test/project \
  'Use the <skill-name> skill. Do only this: <single task>. Return the result only.'
```

This helps catch:
- ambiguous instructions
- missing command examples
- bad defaults
- noisy output

## 5. Run an adversarial test

Try a request that exposes weak spots in the skill.

Examples:
- ask for the latest 3 items
- ask it to filter by another project
- ask it to explain errors it hits
- ask it to use the fastest built-in path
- ask it to avoid unrelated tools

Template:

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /path/to/test/project \
  'Use the <skill-name> skill. Solve this slightly harder task: <task>. Prefer built-in flags and the shortest reliable path. If the skill is missing something, say exactly what.'
```

## 6. Test writable flows separately

If the skill writes files, updates code, downloads data, or needs temp output, switch to a writable sandbox.

```bash
codex exec \
  --skip-git-repo-check \
  --sandbox workspace-write \
  --cd /path/to/test/project \
  'Use the <skill-name> skill. Perform this writable task: <task>. State every file changed or created.'
```

Use `--add-dir` if the skill must write outside the main test workspace.

## 7. What to look for

A skill usually needs improvement if you see any of these:
- Codex does not mention or use the skill even when explicitly asked
- Codex has to inspect many files before finding the right command
- the first documented command fails
- required flags are missing from `SKILL.md`
- output is too noisy to be useful
- common tasks need post-filtering outside the skill
- the skill works only from its own folder
- the skill requires hidden assumptions not stated in `SKILL.md`

## 8. Typical fixes

When a test fails, usually fix one of these:
- add a clearer “Use when…” description
- add exact one-line commands for common tasks
- document required flags and defaults
- document read-only vs writable usage
- reduce noisy/default output
- add built-in flags for common post-processing like sort, limit, or filtering
- make the fastest path the documented default

## 9. Good test prompt pattern

This prompt shape works well across many skills:

```text
Use the <skill-name> skill.
Work from <project-or-temp-dir>.
Do this exact task: <task>.
Prefer built-in commands and the shortest reliable path.
If something fails, explain the failure precisely.
If the skill is missing an obvious helper or flag, say what should be added.
```

## 10. Optional JSON capture

If you need machine-readable logs from the Codex run:

```bash
codex exec \
  --json \
  --skip-git-repo-check \
  --sandbox read-only \
  --cd /path/to/test/project \
  'Use the <skill-name> skill. <task>'
```

## 11. Minimal checklist

- skill exists and `SKILL.md` is readable
- Codex explicitly recognizes and uses the skill
- first example command works
- one realistic task works end to end
- one edge-case task exposes remaining friction
- docs are updated to match the working command shape
