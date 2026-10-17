#!/usr/bin/env python3
"""Phase 241 toolkit extras: codemod, absent, decision (a cleanup.py plugin).

cleanup.py imports this file lazily and calls register(subparsers); it also calls
selftest_cases() from `cleanup.py selftest`. The three commands share cleanup.py's selection
options, prose extraction and tag pattern; nothing is copied.

    codemod [--dry-run] [--scope FILE] [paths...]
        Rewrites the two safe tag shapes in comments and docstrings and prints every changed line
        as a before/after pair. Everything else that still carries a tag is listed as
        "needs hand edit" and left untouched.
    absent --map FILE [--map FILE ...]
        Whole-word git grep of every rename-map `old` over that row's absent_paths. Exit 1 on a hit.
    decision PHASE D-NN
        Prints the decision text from the phase's CONTEXT.md (active or archived).

Exit codes follow cleanup.py: 0 pass, 1 findings, 2 usage or environment error.
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
import tokenize
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple


def _load_core():
    """cleanup.py as a module. When it runs as a script it is aliased as `cleanup` in sys.modules,
    so this module and the script share one set of globals (ROOT, SEEDS_DIR, ...)."""
    mod = sys.modules.get("cleanup")
    if mod is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        mod = importlib.import_module("cleanup")
    return mod


core = _load_core()

EXIT_OK = 0
EXIT_FINDINGS = 1

# ---------------------------------------------------------------------------
# codemod: the two safe tag shapes (STYLE-GUIDE 2.1)
# ---------------------------------------------------------------------------

# Separators between the tags of one group: "D-05/D-08", "Phase 210, SEED-042", "Phase 230 D-16".
GROUP_SEP_RE = re.compile(r"(?:\s*[,/;+&]\s*|\s+(?:and|or)\s+|\s+)")
# Separator between a leading tag group and the sentence it introduces.
LEAD_SEP_RE = re.compile(r"(?:\s*(?::|—|–)|\s+-(?=\s)|\.(?=\s+[A-Z]))\s*")
PAREN_RE = re.compile(r"\(([^()]*)\)")
DASH_SEP_RE = re.compile(r"\s+[—–-]\s+")
# A tag after one of these words is a reference ("per D-04", "since Phase 118"), not a label.
KEYWORD_BEFORE_RE = re.compile(
    r"\b(?:per|see|under|by|from|in|since|after|before|until|of|via|replaces|supersedes)"
    r"\s*[(\[]?\s*$",
    re.IGNORECASE,
)
FIRST_WORD_RE = re.compile(r"^([a-z]+)(?=\s|$|[,;:!?]|\.(?:\s|$)|-(?=[A-Za-z]))")
HAS_TEXT_RE = re.compile(r"[A-Za-z0-9]")
SENTENCE_END = (".", "!", "?", ":")
LEADING_PUNCT = frozenset(".,;:!?)")

BULLET = r"(?:[-*•][ \t]+)?"
PY_COMMENT_HEAD = re.compile(r"#+[ \t]*" + BULLET)
PY_DOC_OPEN = re.compile(r"[ \t]*[rRuUbBfF]{0,2}(?:\"\"\"|'''|\"|')[ \t]*" + BULLET)
PY_DOC_CONT = re.compile(r"[ \t]*" + BULLET)
PY_DOC_TAIL = re.compile(r"[ \t]*(?:\"\"\"|'''|\"|')[ \t]*$")
FE_HEAD = re.compile(r"[ \t]*(?:\{?/\*+|//+|\*+(?!/))?[ \t]*" + BULLET)
FE_TAIL = re.compile(r"[ \t]*\*+/\}?[ \t]*$")
FE_COMMENT_STARTS = ("//", "*", "/*", "{/*")

PROSE_KINDS = ("comment", "docstring")

NOTE_NO_TEXT = "no text left"
NOTE_KEYWORD = "keyword-led reference"
NOTE_SHAPE = "unrecognized shape"


class Change(NamedTuple):
    line: int
    before: str
    after: str


class Hand(NamedTuple):
    line: int
    reason: str
    text: str


class CodemodResult(NamedTuple):
    new_text: str
    changes: list[Change]
    hand: list[Hand]


class Tagger:
    """Tag spans and tag groups for one run (open seeds are read once, not per line)."""

    def __init__(self) -> None:
        self.open_ids = core.open_seeds()

    def spans(self, s: str) -> list[tuple[int, int]]:
        raw = [(m.start(), m.end()) for m in core.TAG_RE.finditer(s)]
        raw += [
            (m.start(), m.end())
            for m in core.REQ_RE.finditer(s)
            if m.group(1) not in core.REQ_STOPLIST
        ]
        merged: list[tuple[int, int]] = []
        for a, b in sorted(raw):
            if merged and a < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        # An open seed is a deliberate pointer (D-12), never part of a removable group.
        return [(a, b) for a, b in merged if s[a:b] not in self.open_ids]

    def group_end(self, s: str, spans: Sequence[tuple[int, int]], first: int) -> int:
        """End offset of the maximal tag group whose first tag starts at `first`."""
        starts = dict(spans)
        end = starts[first]
        while True:
            m = GROUP_SEP_RE.match(s, end)
            nxt = m.end() if m else end
            if nxt in starts and nxt > end:
                end = starts[nxt]
            else:
                return end

    def is_pure(self, s: str) -> bool:
        """True when `s` is nothing but one tag group."""
        s = s.strip()
        spans = self.spans(s)
        if not spans or spans[0][0] != 0:
            return False
        return self.group_end(s, spans, 0) == len(s)

    def only_tags(self, s: str) -> bool:
        """True when removing the tags (and glue) leaves no text: nothing to keep."""
        spans = self.spans(s)
        if not spans:
            return False
        rest = "".join(s[a:b] for a, b in _gaps(s, spans))
        rest = re.sub(r"\b(?:and|or)\b", "", rest)
        return not HAS_TEXT_RE.search(rest)

    def keyword_led(self, s: str, spans: Sequence[tuple[int, int]]) -> bool:
        return any(KEYWORD_BEFORE_RE.search(s[:a]) for a, _b in spans)

    def leading_prefix_end(self, s: str) -> int | None:
        """R1: end of `TAGS [(TAGS)] separator` at the start of `s`, or None."""
        spans = self.spans(s)
        if not spans or spans[0][0] != 0:
            return None
        pos = self.group_end(s, spans, 0)
        paren = re.match(r"\s*\(([^()]*)\)", s[pos:])
        if paren and self.is_pure(paren.group(1)):
            pos += paren.end()
        sep = LEAD_SEP_RE.match(s, pos)
        if sep is None or not s[sep.end() :].strip():
            return None
        return sep.end()

    def drop_parentheticals(self, s: str) -> tuple[str, bool]:
        """R2: remove `(TAGS)` and the space before it. Returns (text, removed_at_start)."""
        out: list[str] = []
        pos = 0
        at_start = False
        for m in PAREN_RE.finditer(s):
            a, b = m.span()
            if a > 0 and not s[a - 1].isspace():
                continue  # call syntax such as foo(D-04), not a parenthetical
            if not self.is_pure(m.group(1)):
                continue
            lead = "".join(out) + s[pos:a]
            if not lead.strip():
                at_start = True
                out = []
                pos = b
                while pos < len(s) and s[pos].isspace():
                    pos += 1
            else:
                out.append(s[pos:a].rstrip())
                pos = b
        out.append(s[pos:])
        return "".join(out), at_start

    def drop_trailing_group(self, s: str) -> str:
        """R3: a final ` - TAGS` / ` — TAGS` at the end of the line."""
        for m in DASH_SEP_RE.finditer(s):
            rest = s[m.end() :].rstrip()
            has_period = rest.endswith(".")
            if self.is_pure(rest[:-1] if has_period else rest):
                return s[: m.start()] + ("." if has_period else "")
        return s

    def transform(self, body: str, cont: bool) -> tuple[str, str | None]:
        """Apply R1-R3 to one line of prose. Returns (new body, note); a note marks a line that was
        left as is on purpose."""
        spans = self.spans(body)
        if not spans:
            return body, None
        if self.only_tags(body):
            return body, NOTE_NO_TEXT
        if self.keyword_led(body, spans):
            return body, NOTE_KEYWORD
        out = body
        capitalize = False
        end = self.leading_prefix_end(out)
        if end is not None:
            out = out[end:]
            capitalize = True
        out, at_start = self.drop_parentheticals(out)
        capitalize = capitalize or at_start
        out = self.drop_trailing_group(out)
        if not HAS_TEXT_RE.search(out):
            return body, NOTE_NO_TEXT
        if out.lstrip()[:1] in LEADING_PUNCT:
            # "(D-07). Next sentence" would become ". Next sentence": the sentence end it
            # dangles from sits on the previous line, so a person has to join them.
            return body, NOTE_SHAPE
        if capitalize and not cont:
            out = capitalize_first(out)
        return out, None


def _gaps(s: str, spans: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """The complement of `spans` inside `s`, as (start, end) slices."""
    gaps: list[tuple[int, int]] = []
    pos = 0
    for a, b in spans:
        gaps.append((pos, a))
        pos = b
    gaps.append((pos, len(s)))
    return gaps


def capitalize_first(s: str) -> str:
    """Capitalize the first word only when it is plain lowercase letters (`useFoo`, `_bar`,
    backticked words, `foo(` and `e.g.` keep their case)."""
    m = FIRST_WORD_RE.match(s)
    if m is None:
        return s
    word = m.group(1)
    return word.capitalize() + s[len(word) :]


def _record_regions(rel: str, rec: core.Prose, lines: Sequence[str]):
    """Yield (line index, start col, end col, head regex, tail regex or None) per record line."""
    py = PurePosixPath(rel).suffix in core.PY_SUFFIXES
    n = rec.end_line - rec.line + 1
    for k in range(n):
        idx = rec.line - 1 + k
        if idx >= len(lines):
            return
        line = lines[idx]
        last = k == n - 1
        start = 0
        if k == 0:
            start = rec.col
            if py and rec.kind == "docstring":
                # ast reports UTF-8 byte offsets; the line prefix is normally plain indentation.
                start = len(line.encode("utf-8")[:start].decode("utf-8", errors="ignore"))
        if py and rec.kind == "comment":
            yield idx, start, len(line), PY_COMMENT_HEAD, None
        elif py:
            head = PY_DOC_OPEN if k == 0 else PY_DOC_CONT
            yield idx, start, len(line), head, PY_DOC_TAIL if last else None
        else:
            end = rec.end_col if last and rec.end_col <= len(line) else len(line)
            yield idx, start, end, FE_HEAD, FE_TAIL if last else None


def _head_of(head_re: re.Pattern[str], s: str) -> str:
    m = head_re.match(s)
    return m.group(0) if m else ""


def _previous_comment_body(rel: str, lines: Sequence[str], idx: int) -> str | None:
    """Prose of the comment-only line right above `idx`, to decide if this line continues a sentence."""
    if idx == 0:
        return None
    prev = lines[idx - 1].strip()
    if PurePosixPath(rel).suffix in core.PY_SUFFIXES:
        if not prev.startswith("#"):
            return None
        return prev[len(_head_of(PY_COMMENT_HEAD, prev)) :]
    if not prev.startswith(FE_COMMENT_STARTS):
        return None
    prev = FE_TAIL.sub("", prev)
    return prev[len(_head_of(FE_HEAD, prev)) :]


def _continues(prev_body: str | None) -> bool:
    return (
        prev_body is not None
        and bool(prev_body.strip())
        and not prev_body.rstrip().endswith(SENTENCE_END)
    )


def codemod_source(rel: str, text: str) -> CodemodResult:
    """Rewrite the safe tag shapes in the prose regions of one file's text."""
    tagger = Tagger()
    lines = text.split("\n")
    new_lines = list(lines)
    changes: list[Change] = []
    hand: list[Hand] = []
    for rec in core.prose_for(rel, text):
        if rec.kind not in PROSE_KINDS:
            continue
        prev_body: str | None = None
        for k, (idx, start, end, head_re, tail_re) in enumerate(_record_regions(rel, rec, lines)):
            line = lines[idx]
            region = line[start:end]
            head = head_re.match(region)
            head_len = head.end() if head else 0
            tail = tail_re.search(region, head_len) if tail_re is not None else None
            body_end = tail.start() if tail else len(region)
            body = region[head_len:body_end]
            if k == 0:
                prev_body = (
                    _previous_comment_body(rel, lines, idx) if rec.kind == "comment" else None
                )
            new_body, note = tagger.transform(body, _continues(prev_body))
            prev_body = body
            new_line = line[:start] + region[:head_len] + new_body + region[body_end:] + line[end:]
            if new_body != body:
                new_lines[idx] = new_line
                changes.append(Change(idx + 1, line, new_line))
            residual = core.find_tags(core.strip_allowed_pointers(new_body))
            if residual:
                hand.append(Hand(idx + 1, note or NOTE_SHAPE, new_line))
    return CodemodResult("\n".join(new_lines), changes, hand)


def code_unchanged(rel: str, old: str, new: str) -> bool:
    """T-241-05: the rewritten file has the same code tokens and lint directives as the original."""
    try:
        old_toks = [(kind, string) for kind, string, _line in core.tokens_for(rel, old)]
        new_toks = [(kind, string) for kind, string, _line in core.tokens_for(rel, new)]
        if old_toks != new_toks:
            return False
        old_dir = core.directives_for(rel, core.prose_for(rel, old))
        new_dir = core.directives_for(rel, core.prose_for(rel, new))
    except SyntaxError, tokenize.TokenError, IndentationError:
        return False
    return old_dir == new_dir


def cmd_codemod(args: argparse.Namespace) -> int:
    selection = core.resolve_selection(args)
    core.ensure_plugins(selection)
    if not selection:
        raise core.UsageError("codemod: no files selected")
    changed_lines = hand_lines = files_changed = 0
    refused: list[str] = []
    for rel in selection:
        text = core.read_text(rel)
        result = codemod_source(rel, text)
        for c in result.changes:
            print(f"{rel}:{c.line}: before: {c.before.strip()}")
            print(f"{rel}:{c.line}: after:  {c.after.strip()}")
        for h in result.hand:
            print(f"{rel}:{h.line}: needs hand edit ({h.reason}): {h.text.strip()}")
        changed_lines += len(result.changes)
        hand_lines += len(result.hand)
        if result.new_text == text:
            continue
        if not code_unchanged(rel, text, result.new_text):
            refused.append(rel)
            print(f"{rel}:0: REFUSED: the rewrite would change code tokens or directives")
            continue
        files_changed += 1
        if not args.dry_run:
            (core.ROOT / rel).write_bytes(result.new_text.encode("utf-8"))
    mode = "dry run, nothing written" if args.dry_run else "written"
    print(
        f"codemod: {len(selection)} files, {changed_lines} lines changed in {files_changed} "
        f"files ({mode}), {hand_lines} need hand edit, {len(refused)} refused",
        file=sys.stderr,
    )
    return EXIT_FINDINGS if refused else EXIT_OK


# ---------------------------------------------------------------------------
# absent
# ---------------------------------------------------------------------------


class AbsentRow(NamedTuple):
    old: str
    paths: list[str]
    source: str


def load_absent_rows(map_arg: str) -> list[AbsentRow]:
    path = core.abs_arg(map_arg)
    if not path.is_file():
        raise core.UsageError(f"rename map {map_arg} not found")
    rows: list[AbsentRow] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if n == 0 or not raw.strip() or raw.startswith("#"):
            continue
        cols = [c.strip() for c in raw.split("\t")] + [""] * 6
        old, absent = cols[0], cols[3]
        if not old or absent in ("", "-"):
            continue
        paths = [p.strip() for p in absent.split(",") if p.strip()]
        rows.append(AbsentRow(old, paths, f"{path.name}:{n + 1}"))
    return rows


def grep_old_name(row: AbsentRow) -> list[str]:
    proc = core.git(
        "grep", "--untracked", "-n", "-w", "-F", "-e", row.old, "--", *row.paths, check=False
    )
    if proc.returncode == 0:
        return proc.stdout.decode("utf-8", "replace").splitlines()
    if proc.returncode == 1:
        return []
    raise core.UsageError(
        f"git grep for {row.old!r} failed: {proc.stderr.decode(errors='replace').strip()}"
    )


def cmd_absent(args: argparse.Namespace) -> int:
    rows: list[AbsentRow] = []
    for map_arg in args.map:
        rows.extend(load_absent_rows(map_arg))
    hits = 0
    for row in rows:
        for hit in grep_old_name(row):
            print(f"{row.source}: {row.old!r} still present: {hit}")
            hits += 1
    print(f"absent: {len(rows)} rows checked, {hits} hits", file=sys.stderr)
    return EXIT_FINDINGS if hits else EXIT_OK


# ---------------------------------------------------------------------------
# decision
# ---------------------------------------------------------------------------

PHASE_NUMBER_RE = re.compile(r"(\d+)((?:\.\d+)*)")
DECISION_ID_RE = re.compile(r"D-\d{2,3}")
HEADING_RE = re.compile(r"(#{1,6})\s")
BULLET_RE = re.compile(r"[-*+]\s")


def phase_prefixes(phase: str) -> list[str]:
    """Directory prefixes for PHASE: 238, 94.4 and 06 all match zero-padded or plain spellings."""
    m = PHASE_NUMBER_RE.fullmatch(phase.strip())
    if m is None:
        raise core.UsageError(f"phase {phase!r} is not a number like 238, 94.4 or 06")
    whole, rest = int(m.group(1)), m.group(2)
    return sorted({f"{whole}{rest}", f"{whole:02d}{rest}", f"{whole:03d}{rest}"})


def context_files(phase: str) -> tuple[list[Path], list[str]]:
    """CONTEXT.md files of the phase (active or archived) and the glob patterns searched."""
    planning = core.ROOT / ".planning"
    globs: list[str] = []
    found: list[Path] = []
    for prefix in phase_prefixes(phase):
        for pattern in (f"phases/{prefix}-*", f"milestones/*-phases/{prefix}-*"):
            globs.append(f".planning/{pattern}/*CONTEXT.md")
            for directory in sorted(planning.glob(pattern)):
                if directory.is_dir():
                    found.extend(sorted(directory.glob("*CONTEXT.md")))
    return found, globs


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def decision_block(lines: Sequence[str], decision: str) -> str | None:
    """The bullet, heading section, table row or paragraph that defines `decision`."""
    num = re.escape(decision)
    start_re = re.compile(
        rf"^(?P<ind>[ \t]*)(?P<mark>[-*+][ \t]+|#{{1,6}}[ \t]+|\|[ \t]*)?"
        rf"(?:\*\*|__)?\[?{num}(?!\d)"
    )
    for i, line in enumerate(lines):
        m = start_re.match(line)
        if m is None:
            continue
        mark = (m.group("mark") or "").strip()
        base = len(m.group("ind").replace("\t", "    "))
        block = [line]
        if mark.startswith("#"):
            level = len(mark)
            for nxt in lines[i + 1 :]:
                head = HEADING_RE.match(nxt)
                if head and len(head.group(1)) <= level:
                    break
                block.append(nxt)
        elif mark == "|":
            pass  # a table row is one line
        else:
            pending: list[str] = []
            for nxt in lines[i + 1 :]:
                if not nxt.strip():
                    if not mark:
                        break  # a paragraph ends at the first blank line
                    pending.append(nxt)
                    continue
                if mark and _indent(nxt) <= base:
                    break  # the next bullet, or text outside this bullet
                block.extend(pending)
                pending = []
                block.append(nxt)
        while block and not block[-1].strip():
            block.pop()
        return "\n".join(ln[base:] if ln[:base].strip() == "" else ln for ln in block)
    return None


def cmd_decision(args: argparse.Namespace) -> int:
    if not DECISION_ID_RE.fullmatch(args.decision):
        raise core.UsageError(f"decision {args.decision!r} is not like D-04")
    files, globs = context_files(args.phase)
    texts: list[tuple[Path, str]] = []
    for path in files:
        block = decision_block(path.read_text(encoding="utf-8").split("\n"), args.decision)
        if block is not None:
            texts.append((path, block))
    if not texts:
        print(
            f"decision: {args.decision} not found for phase {args.phase}. Searched: "
            + (", ".join(globs)),
            file=sys.stderr,
        )
        return EXIT_FINDINGS
    for path, block in texts:
        rel = path.relative_to(core.ROOT).as_posix()
        if len(texts) > 1:
            print(f"--- {rel}")
        else:
            print(rel, file=sys.stderr)
        print(block)
    return EXIT_OK


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "codemod", help="strip the two safe tag shapes from comments and docstrings"
    )
    core.add_selection_args(p)
    p.add_argument("--dry-run", action="store_true", help="print the changes without writing")
    p.set_defaults(func=cmd_codemod)

    p = subparsers.add_parser(
        "absent", help="fail while an old name from a rename map still occurs in its absent_paths"
    )
    p.add_argument("--map", action="append", required=True, metavar="FILE", help="rename map TSV")
    p.set_defaults(func=cmd_absent)

    p = subparsers.add_parser("decision", help="print a decision from a phase CONTEXT.md")
    p.add_argument("phase", help="phase number such as 238, 94.4 or 06")
    p.add_argument("decision", help="decision id such as D-04")
    p.set_defaults(func=cmd_decision)


# ---------------------------------------------------------------------------
# selftest cases (called by `cleanup.py selftest`)
# ---------------------------------------------------------------------------

SEED_FILES = {
    ".planning/seeds/SEED-160-open.md": "open",
    ".planning/seeds/closed/SEED-042-closed.md": "closed",
}


def _codemod_one(text: str, rel: str = "app/x.py") -> str:
    return codemod_source(rel, text).new_text


def _expect(cases: dict[str, str], rel: str = "app/x.py") -> None:
    for before, after in cases.items():
        got = _codemod_one(before, rel)
        assert got == after, f"codemod {before!r}: expected {after!r}, got {got!r}"


def st_codemod_leading_group() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        _expect(
            {
                "# Phase 230 D-16: None means unchanged\nx = 1\n": "# None means unchanged\nx = 1\n",
                "# D-04: the cap applies\nx = 1\n": "# The cap applies\nx = 1\n",
                "# D-04: `useFoo` is the hook\n": "# `useFoo` is the hook\n",
                "# D-04: _bar is private\n": "# _bar is private\n",
                "# D-04: useFoo is the hook\n": "# useFoo is the hook\n",
                "# Phase 112 (D-05/D-08) — the cap applies\n": "# The cap applies\n",
                "# (D-04) the cap applies\n": "# The cap applies\n",
                "# Phase 189 Plan 01 (POOL-04, D-06). One row per user.\n": "# One row per user.\n",
                "# D-06 eligibility watermark: the cap\n": "# D-06 eligibility watermark: the cap\n",
            }
        )


def st_codemod_parenthetical_and_trailing() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        _expect(
            {
                "# the limiter (D-07/D-08) rejects\n": "# the limiter rejects\n",
                "# the limiter rejects (Phase 210, SEED-042)\n": "# the limiter rejects\n",
                "# cap is five (Phase 230 and D-16).\n": "# cap is five.\n",
                "# the cap applies — D-04\n": "# the cap applies\n",
                "# the cap applies - Phase 230, D-16.\n": "# the cap applies.\n",
                "# call foo(D-04) here\n": "# call foo(D-04) here\n",
            }
        )


def st_codemod_docstring() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        before = (
            "def f():\n"
            '    """Phase 112 (D-05/D-08): extended with joins.\n\n'
            "    Body line one\n"
            "    D-07: and the second clause.\n"
            '    """\n'
            "    return 1\n"
        )
        after = (
            "def f():\n"
            '    """Extended with joins.\n\n'
            "    Body line one\n"
            "    and the second clause.\n"
            '    """\n'
            "    return 1\n"
        )
        got = _codemod_one(before)
        assert got == after, f"docstring rewrite: {got!r}"
        one = '"""Phase 112 (D-05/D-08): extended with joins"""\nx = 1\n'
        assert _codemod_one(one) == '"""Extended with joins"""\nx = 1\n'


def st_codemod_leaves_references() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        left = [
            "# the cap, per D-04, applies\n",
            "# see D-04 for the cap\n",
            "# under D-11 the cap applies\n",
            "# retired since Phase 118\n",
            "# Phase 238 — retired in Phase 118\n",
            "# the cap applies (see SEED-160)\n",
            "# Phase 230 (D-16)\n",
            "# D-04\n",
            "# Phase 230, D-16 and D-17\n",
        ]
        for text in left:
            result = codemod_source("app/x.py", text)
            assert result.new_text == text and not result.changes, f"changed {text!r}"
        for text in left:
            result = codemod_source("app/x.py", text)
            listed = bool(result.hand)
            assert listed == ("SEED-160" not in text), f"hand-edit listing wrong for {text!r}"


def st_codemod_code_lines_untouched() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        code = 'LABEL = "Phase 238: the label"\n'
        assert codemod_source("app/x.py", code).new_text == code
        assert not codemod_source("app/x.py", code).hand, "string literal listed as prose"
        mixed = 'LABEL = "Phase 238: the label"  # Phase 238: the label\n'
        want = 'LABEL = "Phase 238: the label"  # The label\n'
        assert codemod_source("app/x.py", mixed).new_text == want, "trailing comment"
        tail = 'x = "# D-04: not a comment"\n'
        assert codemod_source("app/x.py", tail).new_text == tail, "# inside a string"


def st_codemod_continuation_and_idempotence() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        text = "# the limiter rejects the call\n# D-07: and logs the reason\nx = 1\n"
        want = "# the limiter rejects the call\n# and logs the reason\nx = 1\n"
        once = _codemod_one(text)
        assert once == want, f"continuation line capitalized: {once!r}"
        twice = codemod_source("app/x.py", once)
        assert twice.new_text == once and not twice.changes, "codemod is not idempotent"
        assert code_unchanged("app/x.py", text, once), "code tokens reported changed"
        assert not code_unchanged("app/x.py", text, once.replace("x = 1", "x = 2")), (
            "code change not detected"
        )
        noqa = "import os  # noqa: F401\n"
        assert not code_unchanged("app/x.py", noqa, "import os\n"), "directive removal missed"


def st_codemod_command() -> None:
    with core.temp_repo():
        core.write_files(SEED_FILES)
        src = "# D-04: the cap applies\nx = 1\n# per D-05 the rest\n"
        core.write_files({"app/core/a.py": src})
        sel = {"paths": ["app/core/a.py"]}
        code, out, _err = core.run_captured(cmd_codemod, core.ns(dry_run=True, **sel))
        assert code == EXIT_OK and (core.ROOT / "app/core/a.py").read_text() == src, "dry run wrote"
        assert "before: # D-04: the cap applies" in out, out
        assert "after:  # The cap applies" in out, out
        assert "needs hand edit (keyword-led reference): # per D-05 the rest" in out, out
        code, _out, _err = core.run_captured(cmd_codemod, core.ns(dry_run=False, **sel))
        written = (core.ROOT / "app/core/a.py").read_text()
        assert code == EXIT_OK and written == src.replace("# D-04: the cap", "# The cap"), written
        assert core.raises_usage(cmd_codemod, core.ns(dry_run=True)), "empty selection accepted"


def _absent_repo() -> Path:
    core.write_files(
        {
            "app/a.py": "def old_name():\n    return old_name_extra\n",
            "app/b.py": "x = 1\n",
            "maps/hit.tsv": "old\tnew\tkind\tabsent_paths\tref\tcanon_paths\n"
            "old_name\tnew_name\tidentifier\tapp/a.py,app/b.py\tt\t\n",
            "maps/skip.tsv": "old\tnew\tkind\tabsent_paths\tref\tcanon_paths\n"
            "old_name\tnew_name\tidentifier\t-\tt\t\n",
            "maps/clean.tsv": "old\tnew\tkind\tabsent_paths\tref\tcanon_paths\n"
            "old_name_extra\tnew_extra\tidentifier\tapp/b.py\tt\t\n"
            "old_n\tnew_n\tidentifier\tapp/a.py\tt\t\n",
        }
    )
    core.commit_all()
    return core.ROOT


def st_absent_command() -> None:
    with core.temp_repo():
        _absent_repo()
        code, out, _ = core.run_captured(cmd_absent, argparse.Namespace(map=["maps/hit.tsv"]))
        assert code == EXIT_FINDINGS and "app/a.py:1" in out, f"hit missed: {out}"
        code, out, _ = core.run_captured(cmd_absent, argparse.Namespace(map=["maps/skip.tsv"]))
        assert code == EXIT_OK and not out, f"'-' row not skipped: {out}"
        code, out, _ = core.run_captured(cmd_absent, argparse.Namespace(map=["maps/clean.tsv"]))
        assert code == EXIT_OK and not out, f"whole-word match too loose: {out}"
        both = argparse.Namespace(map=["maps/clean.tsv", "maps/hit.tsv"])
        assert core.run_captured(cmd_absent, both)[0] == EXIT_FINDINGS, "second --map ignored"
        assert core.raises_usage(cmd_absent, argparse.Namespace(map=["maps/missing.tsv"])), (
            "missing map accepted"
        )
        # An untracked new file still counts: a rename must not leave the old name behind.
        core.write_files({"app/b.py": "old_name = 1\n"})
        code, _out, _ = core.run_captured(cmd_absent, argparse.Namespace(map=["maps/hit.tsv"]))
        assert code == EXIT_FINDINGS


CONTEXT_FIXTURE = """# Phase 999 Context

## Decisions

- **D-02:** Earlier decision.
- **D-03:** The cap is five.
  A second line of the same decision.

  - nested detail

- **D-04:** Next decision.

### D-05 heading style

Body of the heading.

### D-06 next
"""


def st_decision_command() -> None:
    with core.temp_repo():
        core.write_files(
            {
                ".planning/phases/999-sample/999-CONTEXT.md": CONTEXT_FIXTURE,
                ".planning/milestones/v9.9-phases/06-old/06-CONTEXT.md": CONTEXT_FIXTURE,
                ".planning/milestones/v9.9-phases/94.4-sub/94.4-CONTEXT.md": "D-13: Para decision.\n"
                "Continued.\n\nOther text.\n",
            }
        )
        code, out, _ = core.run_captured(
            cmd_decision, argparse.Namespace(phase="999", decision="D-03")
        )
        want = (
            "- **D-03:** The cap is five.\n  A second line of the same decision.\n\n"
            "  - nested detail"
        )
        assert code == EXIT_OK and out.strip() == want, f"D-03 text: {out!r}"
        for spelling in ("6", "06", "006"):
            code, out, _ = core.run_captured(
                cmd_decision, argparse.Namespace(phase=spelling, decision="D-04")
            )
            assert code == EXIT_OK and out.strip() == "- **D-04:** Next decision.", (
                f"archived phase {spelling}: {out!r}"
            )
        code, out, _ = core.run_captured(
            cmd_decision, argparse.Namespace(phase="999", decision="D-05")
        )
        assert out.strip() == "### D-05 heading style\n\nBody of the heading.", f"heading: {out!r}"
        code, out, _ = core.run_captured(
            cmd_decision, argparse.Namespace(phase="94.4", decision="D-13")
        )
        assert out.strip() == "D-13: Para decision.\nContinued.", f"paragraph: {out!r}"
        code, _out, err = core.run_captured(
            cmd_decision, argparse.Namespace(phase="999", decision="D-99")
        )
        assert code == EXIT_FINDINGS and "Searched" in err, f"missing decision: {err!r}"
        code, _out, err = core.run_captured(
            cmd_decision, argparse.Namespace(phase="777", decision="D-01")
        )
        assert code == EXIT_FINDINGS and ".planning/milestones/*-phases/777-*" in err, err
        assert core.raises_usage(cmd_decision, argparse.Namespace(phase="x1", decision="D-01")), (
            "bad phase accepted"
        )
        assert core.raises_usage(cmd_decision, argparse.Namespace(phase="999", decision="XX")), (
            "bad decision id accepted"
        )


def selftest_cases() -> list[tuple[str, Callable[[], None]]]:
    return [
        ("codemod: leading tag group (R1)", st_codemod_leading_group),
        (
            "codemod: parenthetical and trailing group (R2, R3)",
            st_codemod_parenthetical_and_trailing,
        ),
        ("codemod: docstrings", st_codemod_docstring),
        (
            "codemod: references and tag-only lines are left for hand edit",
            st_codemod_leaves_references,
        ),
        ("codemod: code and string tokens untouched", st_codemod_code_lines_untouched),
        (
            "codemod: continuation lines, idempotence, code guard",
            st_codemod_continuation_and_idempotence,
        ),
        ("codemod: command dry run and write", st_codemod_command),
        ("absent: rename map rows", st_absent_command),
        ("decision: active, archived and padded phases", st_decision_command),
    ]
