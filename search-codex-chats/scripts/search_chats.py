#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

BASES = [
    Path('/Users/igor/.codex/sessions'),
    Path('/Users/igor/.codex/archived_sessions'),
]

BOILERPLATE_PREFIXES = (
    '<app-context>',
    '<environment_context>',
    '<skills_instructions>',
    '<plugins_instructions>',
    '# AGENTS.md instructions for ',
    '<INSTRUCTIONS>',
)


def iter_jsonl_files() -> Iterable[Path]:
    for base in BASES:
        if not base.exists():
            continue
        yield from base.rglob('*.jsonl')


def is_boilerplate_text(text: str) -> bool:
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in BOILERPLATE_PREFIXES)


def extract_text_fields(obj: Dict, include_boilerplate: bool = False) -> List[str]:
    payload = obj.get('payload') or {}
    out: List[str] = []

    if (
        not include_boilerplate
        and payload.get('type') == 'message'
        and payload.get('role') in {'developer', 'system'}
    ):
        return out

    msg = payload.get('message')
    if isinstance(msg, str):
        out.append(msg)

    text = payload.get('text')
    if isinstance(text, str):
        out.append(text)

    if payload.get('type') == 'message' and isinstance(payload.get('content'), list):
        for c in payload['content']:
            if isinstance(c, dict):
                t = c.get('text')
                if isinstance(t, str):
                    out.append(t)

    if include_boilerplate:
        return out
    return [text for text in out if not is_boilerplate_text(text)]


def extract_cwd(obj: Dict) -> Optional[str]:
    payload = obj.get('payload') or {}
    cwd = payload.get('cwd')
    if isinstance(cwd, str) and cwd:
        return cwd
    return None


def get_thread_id(path: Path) -> str:
    name = path.name
    m = re.search(r'(019[0-9a-f\-]+)', name)
    if m:
        return m.group(1)
    m = re.search(r'([0-9a-f]{8}-[0-9a-f\-]{27,})', name)
    return m.group(1) if m else ''


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def normalize_path(s: str) -> str:
    expanded = s.replace('~', str(Path.home()), 1) if s == '~' or s.startswith('~/') else s
    return str(Path(expanded).expanduser().resolve(strict=False))


def is_worktree_project_path(path: str) -> bool:
    return '/.codex/worktrees/' in path or '/.git/worktrees/' in path


def project_family_name(path: str) -> str:
    return Path(path).name


def in_same_project_family(left: str, right: str) -> bool:
    left_norm = normalize_path(left)
    right_norm = normalize_path(right)
    if left_norm == right_norm:
        return True
    if project_family_name(left_norm) != project_family_name(right_norm):
        return False
    return is_worktree_project_path(left_norm) or is_worktree_project_path(right_norm)


def project_path_matcher(project_path: str):
    project_path_norm = normalize_path(project_path)

    def match(candidate: str) -> bool:
        if not candidate:
            return False
        candidate_norm = normalize_path(candidate)
        return in_same_project_family(project_path_norm, candidate_norm)

    return match


def safe_name(s: str) -> str:
    name = re.sub(r'[^A-Za-z0-9_.-]+', '-', s).strip('-')
    return name[:80] or 'unknown'


def load_thread_titles(db_path: Path) -> Dict[str, str]:
    if not db_path.exists():
        return {}
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                """
                SELECT
                    id,
                    COALESCE(NULLIF(title, ''), NULLIF(first_user_message, ''), '(untitled)')
                FROM threads
                """
            ).fetchall()
    except sqlite3.Error:
        return {}
    return {str(thread_id): str(title) for thread_id, title in rows if thread_id}


def load_thread_created_at(db_path: Path) -> Dict[str, int]:
    if not db_path.exists():
        return {}
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                """
                SELECT
                    id,
                    COALESCE(created_at_ms, created_at * 1000)
                FROM threads
                """
            ).fetchall()
    except sqlite3.Error:
        return {}
    out: Dict[str, int] = {}
    for thread_id, created_at_ms in rows:
        if not thread_id:
            continue
        try:
            out[str(thread_id)] = int(created_at_ms)
        except (TypeError, ValueError):
            continue
    return out


def load_thread_metadata(db_path: Path, need_titles: bool, need_created_at: bool) -> Tuple[Dict[str, str], Dict[str, int]]:
    if not need_titles and not need_created_at:
        return {}, {}
    titles = load_thread_titles(db_path) if need_titles else {}
    created_at = load_thread_created_at(db_path) if need_created_at else {}
    return titles, created_at


def load_threads_from_state_db(db_path: Path) -> List[Tuple[str, str, str, int]]:
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                """
                SELECT
                    id,
                    COALESCE(NULLIF(title, ''), NULLIF(first_user_message, ''), '(untitled)'),
                    COALESCE(cwd, ''),
                    COALESCE(created_at_ms, created_at * 1000, 0)
                FROM threads
                """
            ).fetchall()
    except sqlite3.Error:
        return []

    out: List[Tuple[str, str, str, int]] = []
    for thread_id, title, cwd, created_at_ms in rows:
        if not thread_id:
            continue
        try:
            created_at = int(created_at_ms or 0)
        except (TypeError, ValueError):
            created_at = 0
        out.append((str(thread_id), str(title), str(cwd or ''), created_at))
    return out


def file_project(lines: List[str]) -> str:
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            continue
        cwd = extract_cwd(obj)
        if cwd:
            return cwd
    return ''


def first_session_timestamp(lines: List[str]) -> str:
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            continue
        ts = obj.get('timestamp', '')
        if isinstance(ts, str) and ts:
            return ts
    return ''


def build_text_matcher(args: argparse.Namespace):
    if args.list_projects and not args.query:
        return lambda s: True
    if args.regex:
        try:
            pattern = re.compile(args.query or '', re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f'invalid --query regex: {exc}') from exc
        return lambda s: bool(pattern.search(s))
    query = (args.query or '').lower()
    return lambda s: query in s.lower()


def build_project_matcher(args: argparse.Namespace):
    if not args.project:
        return lambda s: True
    if args.project_regex:
        try:
            pattern = re.compile(args.project, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f'invalid --project regex: {exc}') from exc
        return lambda s: bool(pattern.search(s))
    if args.project_contains:
        query = args.project.lower()
        return lambda s: query in s.lower()
    if args.project.startswith('/') or args.project == '~' or args.project.startswith('~/'):
        return project_path_matcher(args.project)
    query = args.project.lower()
    return lambda s: query in s.lower()


def session_text(lines: List[str], max_chars: int = 12000, include_boilerplate: bool = False) -> str:
    parts: List[str] = []
    total = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for text in extract_text_fields(obj, include_boilerplate=include_boilerplate):
            norm = normalize(text)
            if norm:
                if max_chars > 0 and total + len(norm) > max_chars:
                    remaining = max_chars - total
                    if remaining > 0:
                        parts.append(norm[:remaining])
                    return '\n\n'.join(parts)
                parts.append(norm)
                total += len(norm)
    return '\n\n'.join(parts)


def write_zvec_corpus(
    sessions: List[Tuple[str, str, str, Path, List[str]]],
    out_dir: Path,
    max_chars_per_session: int = 12000,
    include_boilerplate: bool = False,
) -> Tuple[int, int]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for ts, thread_id, project, path, lines in sessions:
        text = session_text(lines, max_chars=max_chars_per_session, include_boilerplate=include_boilerplate)
        if not text:
            continue
        digest = hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:12]
        target = out_dir / f'{safe_name(thread_id or path.stem)}-{digest}.md'
        target.write_text(
            '\n'.join([
                f'# Codex Chat {thread_id or path.stem}',
                '',
                f'- timestamp: {ts}',
                f'- project: {project}',
                f'- source: {path}',
                '',
                text,
                '',
            ]),
            encoding='utf-8',
        )
        written += 1
    return written, sum(1 for _ in out_dir.glob('*.md'))


def post_json(url: str, payload: Dict, timeout: int = 120) -> Dict:
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode('utf-8'))
    except (TimeoutError, urllib.error.URLError) as exc:
        raise RuntimeError(f'zvec request failed for {url}: {exc}') from exc


def apply_limit(items: List, limit: Optional[int]) -> List:
    if limit is None or limit < 0:
        return items
    return items[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description='Search local Codex chats.')
    parser.add_argument('--query', help='Literal text or regex pattern')
    parser.add_argument('--regex', action='store_true', help='Treat query as regex')
    parser.add_argument('--project', help='Only search sessions from this project/cwd. Absolute paths match exactly.')
    parser.add_argument('--project-regex', action='store_true', help='Treat --project as regex')
    parser.add_argument('--project-contains', action='store_true', help='Treat --project as a substring instead of an exact path')
    parser.add_argument('--list-projects', action='store_true', help='List discovered project/cwd values and exit')
    parser.add_argument('--threads-only', action='store_true', help='Show unique thread IDs only')
    parser.add_argument('--threads-with-titles', action='store_true', help='Show unique thread IDs with titles')
    parser.add_argument('--sort-threads-by-date', action='store_true', help='Sort thread listings by created date instead of thread id')
    parser.add_argument('--newest-first', action='store_true', help='Reverse date or match ordering so the newest results come first')
    parser.add_argument('--limit', type=int, help='Cap the number of returned rows after sorting')
    parser.add_argument('--include-boilerplate', action='store_true', help='Include system/developer instructions and injected preambles in search text')
    parser.add_argument('--state-db', default=str(Path.home() / '.codex/state_5.sqlite'), help='Path to Codex state sqlite database used for thread metadata')
    parser.add_argument('--dedupe', dest='dedupe', action='store_true', default=True, help='Dedupe by (thread_id, normalized_text)')
    parser.add_argument('--no-dedupe', dest='dedupe', action='store_false', help='Do not dedupe mirrored or repeated messages')
    parser.add_argument('--zvec-export-dir', help='Export matching project chats as Markdown files for zvec ingestion')
    parser.add_argument('--zvec-ingest', action='store_true', help='Export matching project chats and ingest them into the zvec RAG service')
    parser.add_argument('--zvec-search', action='store_true', help='Run semantic search through the zvec RAG service after ingesting matching project chats')
    parser.add_argument('--zvec-url', default='http://127.0.0.1:8787', help='Base URL for zvec-local-rag-service')
    parser.add_argument('--zvec-topk', type=int, default=5, help='Number of zvec semantic results to return')
    parser.add_argument('--zvec-timeout', type=int, default=600, help='Timeout in seconds for zvec ingest/search HTTP calls')
    parser.add_argument('--zvec-max-sessions', type=int, help='Limit the number of matching Codex sessions exported to zvec')
    parser.add_argument('--zvec-max-chars-per-session', type=int, default=12000, help='Maximum extracted characters per session for zvec export; set 0 for unlimited')
    parser.add_argument('--zvec-corpus-dir', default=str(Path.home() / '.codex/search-codex-chats/zvec-corpus'), help='Temporary corpus directory used for zvec ingest/search')
    args = parser.parse_args()

    zvec_mode = args.zvec_export_dir or args.zvec_ingest or args.zvec_search
    thread_listing_mode = args.threads_only or args.threads_with_titles
    if not args.query and not args.list_projects and not zvec_mode and not thread_listing_mode:
        parser.error('--query is required unless --list-projects, a thread-listing mode, or a zvec export/ingest mode is used')
    if args.zvec_search and not args.query:
        parser.error('--query is required with --zvec-search')

    try:
        matcher = build_text_matcher(args)
        project_matcher = build_project_matcher(args)
    except ValueError as exc:
        parser.error(str(exc))

    state_db_path = Path(args.state_db).expanduser()

    if thread_listing_mode and not args.query:
        thread_rows = load_threads_from_state_db(state_db_path)
        if thread_rows:
            filtered_threads = [
                (thread_id, title, created_at_ms)
                for thread_id, title, cwd, created_at_ms in thread_rows
                if project_matcher(cwd)
            ]
            if args.sort_threads_by_date:
                filtered_threads.sort(key=lambda item: (item[2], item[0]), reverse=args.newest_first)
            else:
                filtered_threads.sort(key=lambda item: item[0], reverse=args.newest_first)
            filtered_threads = apply_limit(filtered_threads, args.limit)
            print(f'threads={len(filtered_threads)}')
            if args.threads_only:
                for thread_id, _, _ in filtered_threads:
                    print(thread_id)
            else:
                for thread_id, title, _ in filtered_threads:
                    print(f'{thread_id}\t{title}')
            return 0

    results: List[Tuple[str, str, str, Path, int, str]] = []
    zvec_sessions: List[Tuple[str, str, str, Path, List[str]]] = []
    projects: Dict[str, int] = {}
    seen = set()
    matching_threads = set()

    for file in iter_jsonl_files():
        thread_id = get_thread_id(file)
        try:
            lines = file.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue

        project = file_project(lines)
        if project:
            projects[project] = projects.get(project, 0) + 1

        if not project_matcher(project):
            continue

        if thread_id:
            matching_threads.add(thread_id)

        if zvec_mode:
            if args.zvec_max_sessions is not None and len(zvec_sessions) >= args.zvec_max_sessions:
                continue
            zvec_sessions.append((first_session_timestamp(lines), thread_id, project, file, lines))

        if args.list_projects:
            continue

        if zvec_mode and not args.query:
            continue

        for idx, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except Exception:
                continue

            ts = obj.get('timestamp', '')
            for text in extract_text_fields(obj, include_boilerplate=args.include_boilerplate):
                if not matcher(text):
                    continue
                norm = normalize(text)
                key = (thread_id, norm)
                if args.dedupe and key in seen:
                    continue
                if args.dedupe:
                    seen.add(key)
                results.append((ts, thread_id, project, file, idx, norm))

    if args.list_projects:
        filtered = [(project, count) for project, count in projects.items() if project_matcher(project)]
        filtered.sort(key=lambda item: (-item[1], item[0]))
        print(f'projects={len(filtered)}')
        for project, count in filtered:
            print(f'{count}\t{project}')
        return 0

    if zvec_mode:
        corpus_dir = Path(args.zvec_export_dir or args.zvec_corpus_dir).expanduser()
        sessions_written, files_written = write_zvec_corpus(
            zvec_sessions,
            corpus_dir,
            max_chars_per_session=args.zvec_max_chars_per_session,
            include_boilerplate=args.include_boilerplate,
        )
        print(f'zvec_corpus={corpus_dir}')
        print(f'zvec_sessions={sessions_written}')
        print(f'zvec_files={files_written}')

        if args.zvec_ingest or args.zvec_search:
            try:
                ingest = post_json(
                    f'{args.zvec_url.rstrip("/")}/ingest',
                    {'dir': str(corpus_dir), 'reset': True},
                    timeout=args.zvec_timeout,
                )
            except RuntimeError as exc:
                print(f'zvec_error={exc}')
                print('zvec_hint=start the service with: /Users/igor/.codex/skills2/zvec-local-rag-service/scripts/manage.sh start')
                return 2
            print('zvec_ingest=' + json.dumps(ingest, ensure_ascii=False))

        if args.zvec_search:
            try:
                search = post_json(
                    f'{args.zvec_url.rstrip("/")}/search',
                    {'query': args.query, 'topk': args.zvec_topk},
                    timeout=args.zvec_timeout,
                )
            except RuntimeError as exc:
                print(f'zvec_error={exc}')
                print('zvec_hint=start the service with: /Users/igor/.codex/skills2/zvec-local-rag-service/scripts/manage.sh start')
                return 2
            print(f'zvec_results={len(search.get("results", []))}')
            for item in search.get('results', []):
                source = item.get('source', '')
                chunk = item.get('chunkIndex', '')
                score = item.get('score', '')
                text = normalize(str(item.get('text', '')))[:300]
                print(f'{score}\t{source}#{chunk}\t{text}')
            return 0

        if not args.query:
            return 0

    results.sort(key=lambda r: r[0], reverse=args.newest_first)
    results = apply_limit(results, args.limit)
    titles_by_thread, created_at_by_thread = load_thread_metadata(
        state_db_path,
        need_titles=args.threads_with_titles,
        need_created_at=args.sort_threads_by_date,
    )

    def sort_threads(threads: List[str]) -> List[str]:
        if not args.sort_threads_by_date:
            return sorted(threads, reverse=args.newest_first)
        return sorted(threads, key=lambda t: (created_at_by_thread.get(t, 0), t), reverse=args.newest_first)

    if args.threads_only:
        if args.query:
            threads = list({r[1] for r in results if r[1]})
        else:
            threads = list(matching_threads)
        threads = sort_threads(threads)
        threads = apply_limit(threads, args.limit)
        print(f'threads={len(threads)}')
        for t in threads:
            print(t)
        return 0

    if args.threads_with_titles:
        threads = sort_threads(list(matching_threads))
        threads = apply_limit(threads, args.limit)
        print(f'threads={len(threads)}')
        for t in threads:
            print(f'{t}\t{titles_by_thread.get(t, "(untitled)")}')
        return 0

    print(f'matches={len(results)}')
    print(f'threads={len({r[1] for r in results if r[1]})}')
    print(f'projects={len({r[2] for r in results if r[2]})}')
    for ts, tid, project, path, line_no, text in results:
        snippet = text[:220]
        print(f'{ts}\t{tid}\t{project}\t{path}:{line_no}\t{snippet}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
