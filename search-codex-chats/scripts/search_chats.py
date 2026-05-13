#!/usr/bin/env python3
import argparse
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

BASES = [
    Path('/Users/igor/.codex/sessions'),
    Path('/Users/igor/.codex/archived_sessions'),
]
SUMMARY_BASE = Path('/Users/igor/.codex/memories/rollout_summaries')
THREAD_ID_RE = re.compile(r'019[0-9a-f]{5,}-[0-9a-f-]{20,}', re.IGNORECASE)

BOILERPLATE_PREFIXES = (
    '<app-context>',
    '<environment_context>',
    '<skills_instructions>',
    '<plugins_instructions>',
    '<skill>',
    '<subagent_notification>',
    '# AGENTS.md instructions for ',
    '<INSTRUCTIONS>',
)


def iter_jsonl_files() -> Iterable[Path]:
    for base in BASES:
        if not base.exists():
            continue
        yield from base.rglob('*.jsonl')


def all_jsonl_files() -> List[Path]:
    return list(iter_jsonl_files())


def iter_summary_files() -> Iterable[Path]:
    if not SUMMARY_BASE.exists():
        return
    yield from SUMMARY_BASE.glob('*.md')


def all_summary_files() -> List[Path]:
    return list(iter_summary_files())


def summary_files_for_thread_ids(thread_ids: set) -> List[Path]:
    if not SUMMARY_BASE.exists() or not thread_ids:
        return []
    command = ['rg', '--files-with-matches', '--fixed-strings']
    for thread_id in sorted(thread_ids):
        command.extend(['--regexp', thread_id])
    try:
        completed = subprocess.run(
            [*command, str(SUMMARY_BASE)],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return filter_summary_files_by_thread_ids(all_summary_files(), thread_ids)
    if completed.returncode not in (0, 1):
        return filter_summary_files_by_thread_ids(all_summary_files(), thread_ids)
    candidates = [Path(line) for line in completed.stdout.splitlines() if line.strip()]
    return filter_summary_files_by_thread_ids(candidates, thread_ids)


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


def output_cell(s: str, max_chars: int = 220) -> str:
    return normalize(s)[:max_chars]


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


def load_rollout_paths_for_thread_ids(db_path: Path, thread_ids: set) -> List[Path]:
    if not db_path.exists() or not thread_ids:
        return []
    placeholders = ','.join('?' for _ in thread_ids)
    try:
        with sqlite3.connect(str(db_path)) as con:
            rows = con.execute(
                f'SELECT rollout_path FROM threads WHERE id IN ({placeholders})',
                tuple(sorted(thread_ids)),
            ).fetchall()
    except sqlite3.Error:
        return []
    paths: List[Path] = []
    seen = set()
    for (rollout_path,) in rows:
        if not rollout_path:
            continue
        path = Path(str(rollout_path))
        if path.exists() and path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def format_created_at_ms(created_at_ms: int) -> str:
    if created_at_ms <= 0:
        return ''
    return datetime.fromtimestamp(created_at_ms / 1000, tz=timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


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


def summary_metadata(lines: List[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for line in lines:
        if not line.strip():
            break
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        metadata[key.strip()] = value.strip()
    return metadata


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


def build_matcher(query: Optional[str], regex: bool):
    if not query:
        return lambda s: True
    if regex:
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f'invalid regex: {exc}') from exc
        return lambda s: bool(pattern.search(s))
    query_lower = query.lower()
    return lambda s: query_lower in s.lower()


def looks_like_regex(query: Optional[str]) -> bool:
    if not query:
        return False
    return bool(re.search(r'[|()[\]{}.*+?\\]', query))


def split_simple_title_terms(query: Optional[str]) -> List[str]:
    if not query:
        return []
    terms = [term.strip() for term in query.split('|')]
    if not terms or any(not term for term in terms):
        return []
    if any(re.search(r'[()[\]{}.*+?\\]', term) for term in terms):
        return []
    return terms


def title_search_text(title: str) -> str:
    for line in title.splitlines():
        line = line.strip()
        if line:
            return line[:260]
    return title[:260]


def term_boundary_pattern(term: str) -> re.Pattern:
    return re.compile(rf'(?<![A-Za-z0-9]){re.escape(term)}[A-Za-z0-9-]*', re.IGNORECASE)


def build_title_scorer(args: argparse.Namespace) -> Callable[[str], int]:
    title_query = args.title_query or args.query
    simple_terms = split_simple_title_terms(title_query)
    if simple_terms:
        boundary_patterns = [(term, term_boundary_pattern(term)) for term in simple_terms]

        def score(title: str) -> int:
            searchable_title = title_search_text(title)
            title_lower = searchable_title.lower()
            total = 0
            for term, pattern in boundary_patterns:
                term_lower = term.lower()
                if pattern.search(searchable_title):
                    total += 10 + min(len(term_lower), 8)
                elif len(term_lower) >= 8 and term_lower in title_lower:
                    total += 3
            return total

        return score

    title_matcher = build_title_matcher(args)
    return lambda title: 1 if title_matcher(title) else 0


def code_like_term(term: str) -> bool:
    return bool(re.search(r'[-_/]', term) or re.search(r'[a-z][A-Z]', term))


def build_text_scorer(query: Optional[str]) -> Callable[[str], int]:
    terms = split_simple_title_terms(query)
    if not terms and query:
        terms = [query]
    normalized_terms = [term.lower() for term in terms if term]

    def score(text: str) -> int:
        text_lower = text.lower()
        total = 0
        for term, term_lower in zip(terms, normalized_terms):
            if term_lower not in text_lower:
                continue
            if code_like_term(term):
                total += 30
            elif len(term_lower) >= 10:
                total += 18
            elif len(term_lower) >= 7:
                total += 10
            else:
                total += 4
        return total

    return score


def build_text_matcher(args: argparse.Namespace):
    if args.list_projects and not args.query:
        return lambda s: True
    return build_matcher(args.query, args.regex or args.query_mode == 'regex')


def build_title_matcher(args: argparse.Namespace):
    title_query = args.title_query or args.query
    use_regex = args.regex or args.query_mode == 'regex' or looks_like_regex(title_query)
    try:
        return build_matcher(title_query, use_regex)
    except ValueError as exc:
        raise ValueError(f'invalid --title-query regex: {exc}') from exc


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


def apply_limit(items: List, limit: Optional[int]) -> List:
    if limit is None or limit < 0:
        return items
    return items[:limit]


def should_use_rg_prefilter(args: argparse.Namespace) -> bool:
    return bool(
        args.query
        and args.query_mode in ('auto', 'literal', 'regex', 'hybrid')
        and not args.list_projects
        and not args.threads_only
        and not args.threads_with_titles
    )


def candidate_files_via_rg(query: str, regex: bool) -> Optional[List[Path]]:
    bases = [str(base) for base in BASES if base.exists()]
    if not bases:
        return []
    command = ['rg', '--files-with-matches', '--ignore-case', '--glob', '*.jsonl']
    if regex:
        command.extend(['--regexp', query])
    else:
        command.extend(['--fixed-strings', query])
    try:
        completed = subprocess.run(
            [*command, *bases],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None

    if completed.returncode not in (0, 1):
        return None

    files = [Path(line) for line in completed.stdout.splitlines() if line.strip()]
    return files


def candidate_jsonl_files(args: argparse.Namespace) -> List[Path]:
    if should_use_rg_prefilter(args):
        rg_files = candidate_files_via_rg(args.query, args.regex or args.query_mode == 'regex')
        if rg_files is not None:
            return rg_files
    return all_jsonl_files()


def session_files_for_thread_ids(thread_ids: set, known_paths: Optional[List[Path]] = None) -> List[Path]:
    files: List[Path] = []
    seen = set()
    for file in known_paths or []:
        if file not in seen:
            files.append(file)
            seen.add(file)
    if files:
        return files
    for thread_id in sorted(thread_ids):
        for base in BASES:
            if not base.exists():
                continue
            for file in base.rglob(f'*{thread_id}*.jsonl'):
                if file not in seen:
                    files.append(file)
                    seen.add(file)
    return files


def parse_thread_ids(values: Optional[List[str]]) -> set:
    thread_ids = set()
    for value in values or []:
        for item in value.split(','):
            item = item.strip()
            if item:
                thread_ids.add(item)
    return thread_ids


def thread_ids_from_query(query: Optional[str]) -> set:
    if not query:
        return set()
    normalized_query = query.strip()
    if not normalized_query:
        return set()
    thread_ids = set(THREAD_ID_RE.findall(normalized_query))
    remainder = THREAD_ID_RE.sub('', normalized_query)
    remainder = re.sub(r'[\s,;:()"\']+', '', remainder)
    return thread_ids if thread_ids and not remainder else set()


def filter_session_files_by_thread_ids(files: List[Path], thread_ids: set) -> List[Path]:
    if not thread_ids:
        return files
    return [file for file in files if get_thread_id(file) in thread_ids]


def filter_summary_files_by_thread_ids(files: List[Path], thread_ids: set) -> List[Path]:
    if not thread_ids:
        return files
    filtered: List[Path] = []
    for file in files:
        try:
            lines = file.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue
        metadata = summary_metadata(lines)
        if (metadata.get('thread_id') or get_thread_id(file)) in thread_ids:
            filtered.append(file)
    return filtered


def collect_sessions(
    candidate_files: List[Path],
    project_matcher,
 ) -> Tuple[Dict[str, int], set]:
    projects: Dict[str, int] = {}
    matching_threads = set()

    for file in candidate_files:
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

    return projects, matching_threads


def collect_search_results(
    candidate_files: List[Path],
    matcher,
    project_matcher,
    dedupe: bool,
    include_boilerplate: bool,
) -> Tuple[List[Tuple[str, str, str, Path, int, str]], Dict[str, int], set]:
    results: List[Tuple[str, str, str, Path, int, str]] = []
    projects: Dict[str, int] = {}
    matching_threads = set()
    seen = set()

    for file in candidate_files:
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

        for idx, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except Exception:
                continue

            ts = obj.get('timestamp', '')
            for text in extract_text_fields(obj, include_boilerplate=include_boilerplate):
                if not matcher(text):
                    continue
                norm = normalize(text)
                key = (thread_id, norm)
                if dedupe and key in seen:
                    continue
                if dedupe:
                    seen.add(key)
                results.append((ts, thread_id, project, file, idx, norm))

    return results, projects, matching_threads


def collect_summary_results(
    candidate_files: List[Path],
    matcher,
    project_matcher,
    dedupe: bool,
) -> Tuple[List[Tuple[str, str, str, Path, int, str]], Dict[str, int], set]:
    results: List[Tuple[str, str, str, Path, int, str]] = []
    projects: Dict[str, int] = {}
    matching_threads = set()
    seen = set()

    for file in candidate_files:
        try:
            lines = file.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue

        metadata = summary_metadata(lines)
        thread_id = metadata.get('thread_id') or get_thread_id(file)
        project = metadata.get('cwd', '')
        ts = metadata.get('updated_at', '')

        if project:
            projects[project] = projects.get(project, 0) + 1

        if not project_matcher(project):
            continue

        if thread_id:
            matching_threads.add(thread_id)

        for idx, line in enumerate(lines, start=1):
            text = normalize(line)
            if not text or not matcher(text):
                continue
            key = (thread_id, text)
            if dedupe and key in seen:
                continue
            if dedupe:
                seen.add(key)
            results.append((ts, thread_id, project, file, idx, text))

    return results, projects, matching_threads


def print_list_projects(projects: Dict[str, int], project_matcher) -> int:
    filtered = [(project, count) for project, count in projects.items() if project_matcher(project)]
    filtered.sort(key=lambda item: (-item[1], item[0]))
    print(f'projects={len(filtered)}')
    for project, count in filtered:
        print(f'{count}\t{project}')
    return 0


def collect_title_results(
    thread_rows: List[Tuple[str, str, str, int]],
    title_scorer: Callable[[str], int],
    project_matcher,
) -> List[Tuple[str, str, str, int, int]]:
    return [
        (thread_id, title, cwd, created_at_ms, score)
        for thread_id, title, cwd, created_at_ms in thread_rows
        if project_matcher(cwd)
        for score in [title_scorer(title)]
        if score > 0
    ]


def sort_title_results(
    args: argparse.Namespace,
    rows: List[Tuple[str, str, str, int, int]],
    rank_by_score: bool = False,
) -> List[Tuple[str, str, str, int, int]]:
    if rank_by_score:
        rows = sorted(rows, key=lambda item: (item[4], item[3], item[0]), reverse=True)
    elif args.sort_threads_by_date or args.newest_first:
        rows = sorted(rows, key=lambda item: (item[3], item[0]), reverse=args.newest_first)
    else:
        rows = sorted(rows, key=lambda item: (-item[4], item[0]))
    return apply_limit(rows, args.limit)


def print_title_results(rows: List[Tuple[str, str, str, int, int]], args: argparse.Namespace) -> int:
    rows = sort_title_results(args, rows)
    print(f'matches={len(rows)}')
    print(f'threads={len({row[0] for row in rows})}')
    print(f'projects={len({row[2] for row in rows if row[2]})}')
    for thread_id, title, cwd, created_at_ms, score in rows:
        ts = format_created_at_ms(created_at_ms)
        print(f'{ts}\t{thread_id}\t{cwd}\tstate_5.sqlite:title:score={score}\t{output_cell(title)}')
    return 0


def print_hybrid_results(
    args: argparse.Namespace,
    title_rows: List[Tuple[str, str, str, int, int]],
    text_results: List[Tuple[str, str, str, Path, int, str]],
) -> int:
    snippet_thread_ids = {row[1] for row in text_results if row[1]}
    if snippet_thread_ids:
        title_rows = [row for row in title_rows if row[0] in snippet_thread_ids or row[4] >= 17]
    title_rows = sort_title_results(args, title_rows, rank_by_score=True)
    if args.title_limit is not None:
        title_rows = apply_limit(title_rows, args.title_limit)
    elif args.limit is not None and args.limit >= 0:
        title_rows = apply_limit(title_rows, max(1, min(3, args.limit // 2 or 1)))
    preferred_thread_ids = {row[0] for row in title_rows}
    synthetic_title_results = [
        (format_created_at_ms(created_at_ms), thread_id, cwd, Path('state_5.sqlite'), 0, output_cell(title), f'title:score={score}')
        for thread_id, title, cwd, created_at_ms, score in title_rows
    ]
    text_scorer = build_text_scorer(args.query)
    ranked_snippets = sorted(
        text_results,
        key=lambda row: (
            row[1] in preferred_thread_ids,
            text_scorer(row[5]),
            row[0] if args.newest_first else '',
        ),
        reverse=True,
    )
    text_score_map = {
        (row[0], row[1], row[3], row[4]): float(text_scorer(row[5]))
        for row in ranked_snippets
    }
    combined = synthetic_title_results + [
        (
            ts,
            tid,
            project,
            path,
            line_no,
            text,
            (
                f'preferred-snippet:heuristic={text_score_map.get((ts, tid, path, line_no), 0.0):.4f}'
                if tid in preferred_thread_ids
                else f'snippet:heuristic={text_score_map.get((ts, tid, path, line_no), 0.0):.4f}'
            ),
        )
        for ts, tid, project, path, line_no, text in ranked_snippets
    ]
    combined = apply_limit(combined, args.limit)
    print(f'matches={len(combined)}')
    print(f'threads={len({row[1] for row in combined if row[1]})}')
    print(f'projects={len({row[2] for row in combined if row[2]})}')
    for ts, tid, project, path, line_no, text, kind in combined:
        print(f'{ts}\t{tid}\t{project}\t{path}:{line_no}:{kind}\t{output_cell(text)}')
    return 0


def print_search_results(
    args: argparse.Namespace,
    results: List[Tuple[str, str, str, Path, int, str]],
    matching_threads: set,
    state_db_path: Path,
) -> int:
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
            print(f'{t}\t{output_cell(titles_by_thread.get(t, "(untitled)"))}')
        return 0

    print(f'matches={len(results)}')
    print(f'threads={len({r[1] for r in results if r[1]})}')
    print(f'projects={len({r[2] for r in results if r[2]})}')
    for ts, tid, project, path, line_no, text in results:
        snippet = output_cell(text)
        print(f'{ts}\t{tid}\t{project}\t{path}:{line_no}\t{snippet}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Search local Codex chats.')
    parser.add_argument('--query', help='Literal text or regex pattern')
    parser.add_argument('--title-query', help='Match against thread title and first user message via SQLite metadata')
    parser.add_argument('--query-mode', choices=['auto', 'literal', 'regex', 'title', 'hybrid'], default='auto', help='Search mode: text search, title search, or hybrid ranking')
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
    parser.add_argument('--title-limit', type=int, help='Cap title rows in hybrid output before adding snippets')
    parser.add_argument('--include-boilerplate', action='store_true', help='Include system/developer instructions and injected preambles in search text')
    parser.add_argument('--thread-id', action='append', help='Restrict search to one thread id. Repeat or pass comma-separated values.')
    parser.add_argument('--source', choices=['auto', 'sessions', 'summaries', 'both'], default='auto', help='Search raw session JSONL, rollout summaries, or both. auto uses summaries first for --thread-id and sessions otherwise.')
    parser.add_argument('--state-db', default=str(Path.home() / '.codex/state_5.sqlite'), help='Path to Codex state sqlite database used for thread metadata')
    parser.add_argument('--dedupe', dest='dedupe', action='store_true', default=True, help='Dedupe by (thread_id, normalized_text)')
    parser.add_argument('--no-dedupe', dest='dedupe', action='store_false', help='Do not dedupe mirrored or repeated messages')
    args = parser.parse_args()

    thread_listing_mode = args.threads_only or args.threads_with_titles
    thread_ids = parse_thread_ids(args.thread_id)
    implicit_thread_ids = set()
    if (
        not thread_ids
        and args.query
        and not args.regex
        and args.query_mode in ('auto', 'literal')
        and not args.title_query
    ):
        implicit_thread_ids = thread_ids_from_query(args.query)
        if implicit_thread_ids:
            thread_ids = implicit_thread_ids
            args.query = None
    if not args.query and not args.title_query and not args.list_projects and not thread_listing_mode and not thread_ids:
        parser.error('--query, --title-query, or --thread-id is required unless --list-projects or a thread-listing mode is used')
    if args.query_mode in ('title', 'hybrid') and not (args.title_query or args.query):
        parser.error('--query-mode title/hybrid requires --title-query or --query')

    try:
        matcher = build_text_matcher(args)
        project_matcher = build_project_matcher(args)
        title_scorer = build_title_scorer(args)
    except ValueError as exc:
        parser.error(str(exc))

    state_db_path = Path(args.state_db).expanduser()
    thread_rows = load_threads_from_state_db(state_db_path)

    if thread_listing_mode and not args.query and not thread_ids:
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
                    print(f'{thread_id}\t{output_cell(title)}')
            return 0

    auto_thread_summary_first = args.source == 'auto' and bool(thread_ids)
    source = args.source
    if source == 'auto':
        source = 'both' if thread_ids else 'sessions'

    if source in ('sessions', 'both'):
        known_session_paths = load_rollout_paths_for_thread_ids(state_db_path, thread_ids) if thread_ids else []
        candidate_files = session_files_for_thread_ids(thread_ids, known_session_paths) if thread_ids else candidate_jsonl_files(args)
    else:
        candidate_files = []
    if source in ('summaries', 'both'):
        summary_files = summary_files_for_thread_ids(thread_ids) if thread_ids else all_summary_files()
    else:
        summary_files = []

    if args.list_projects:
        projects, matching_threads = {}, set()
        if candidate_files:
            session_projects, session_threads = collect_sessions(
                candidate_files,
                project_matcher,
            )
            projects.update(session_projects)
            matching_threads.update(session_threads)
        if summary_files:
            _, summary_projects, summary_threads = collect_summary_results(
                summary_files,
                matcher,
                project_matcher,
                dedupe=args.dedupe,
            )
            for project, count in summary_projects.items():
                projects[project] = projects.get(project, 0) + count
            matching_threads.update(summary_threads)
    else:
        projects, matching_threads = {}, set()

    if args.list_projects:
        return print_list_projects(projects, project_matcher)

    if args.query_mode == 'title':
        title_results = collect_title_results(thread_rows, title_scorer, project_matcher)
        return print_title_results(title_results, args)

    results: List[Tuple[str, str, str, Path, int, str]] = []
    if summary_files:
        summary_results, _, summary_threads = collect_summary_results(
            summary_files,
            matcher,
            project_matcher,
            dedupe=args.dedupe,
        )
        results.extend(summary_results)
        matching_threads.update(summary_threads)
    should_search_sessions = bool(candidate_files) and not (auto_thread_summary_first and results)
    if should_search_sessions:
        session_results, _, session_threads = collect_search_results(
            candidate_files,
            matcher,
            project_matcher,
            dedupe=args.dedupe,
            include_boilerplate=args.include_boilerplate,
        )
        results.extend(session_results)
        matching_threads.update(session_threads)
    if args.query_mode == 'hybrid':
        title_results = collect_title_results(thread_rows, title_scorer, project_matcher)
        return print_hybrid_results(args, title_results, results)
    return print_search_results(args, results, matching_threads, state_db_path)


if __name__ == '__main__':
    raise SystemExit(main())
