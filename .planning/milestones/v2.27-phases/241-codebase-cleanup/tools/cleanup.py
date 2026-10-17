#!/usr/bin/env python3
"""Phase 241 cleanup toolkit: scan, apply-edits, diff, rows, ledger.

Run from the checkout root:
    uv run python .planning/phases/241-codebase-cleanup/tools/cleanup.py <command> [options] [paths...]

Commands
    scan        list planning tags left in comments, docstrings and Python test names
    apply-edits apply a JSON batch of line edits (all-or-nothing)
    diff        prove that only comments, docstrings, test names and renames changed
    rows        print the INVENTORY section 6 rows located in the selection
    ledger      fail until every selected INVENTORY row has a status line in a ledger

Exit codes: 0 pass, 1 findings, 2 usage or environment error.

Library surface for plugins (tools/extras.py, tools/fe_support.py):
    TAG_PATTERNS, find_tags(text), open_seeds(), py_prose(text), py_tokens(text),
    directive_heads(prose_records), Prose, add_selection_args(parser), resolve_selection(args).
    Prose is a 6-tuple (line, col, end_line, end_col, kind, text); a token is a 3-tuple
    (kind, text, line). FE plugins return the same shapes.
Commands are registered with parser.set_defaults(func=fn) where fn(args) -> int.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import difflib
import fnmatch
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Locations (recomputed by set_root so the selftest can run against a temp repo)
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parents[3]
PHASE_DIR = TOOLS_DIR.parent
SEEDS_DIR = ROOT / ".planning" / "seeds"


def set_root(root: Path, phase_dir: Path | None = None) -> None:
    global ROOT, PHASE_DIR, SEEDS_DIR
    ROOT = root
    PHASE_DIR = (
        phase_dir
        if phase_dir is not None
        else root / ".planning" / "phases" / "241-codebase-cleanup"
    )
    SEEDS_DIR = root / ".planning" / "seeds"


class UsageError(Exception):
    """Bad invocation or environment problem: exit code 2."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

PY_SUFFIXES = {".py"}
FE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css"}
APP_EXCLUDED = ("app/prompts/", "app/data/")
TESTS_EXCLUDED = ("tests/fixtures/",)
FE_ROOT = "frontend/src/"
FE_EXCLUDED = ("frontend/src/generated/", "frontend/src/assets/")
INVENTORY_LOCATION_ROOTS = ("app/", "tests/", "scripts/", "frontend/", "docs/", "bin/", "alembic/")

# Words that look like a REQ-id (WORD-NN) but are ordinary names.
REQ_STOPLIST = frozenset(
    {"UTF", "ISO", "RFC", "CVE", "SHA", "FLAWCHESS", "GPT", "HTTP", "TLS", "WCAG", "ECMA"}
)
LEDGER_STATUSES = ("APPLIED", "MOVED", "SKIPPED", "LEFT", "DEFERRED")
DIFF_TOKEN_PREVIEW = 12

# ---------------------------------------------------------------------------
# Tag patterns (D-11: planning ids only; case-sensitive)
# ---------------------------------------------------------------------------

TAG_PATTERNS: tuple[str, ...] = (
    r"\bPhase \d{2,3}(?:\.\d+)?(?!\d)",
    r"\bD-\d{2,3}(?:-\d{2})?(?!\d)",
    r"\bSEED-\d{3}(?!\d)",
    r"\b(?:FE-)?(?:CR|WR|IN|MD|BL)-\d{2}(?!\d)",
    r"\bFE-[A-Z]{2}-\d{2}(?!\d)",
    r"\bT-\d{2,3}(?:\.\d+)?-\d{2}(?:-\d{2})?(?!\d)",
    r"(?:\b[Qq]uick(?: task)? )?\b2[56]\d{4}-[a-z0-9]{3}\b",
    r"(?<![\w.-])(?:[5-9]\d|1\d\d|2[0-4]\d)(?:\.\d+)?-(?:0[1-9]|1\d)(?!\d)",
    r"\b[Pp]lan \d{2}(?!\d)",
    r"\bRESEARCH\b",
    r"\bPitfall \d+\b",
    r"\bPATTERNS\.md\b",
    r"-(?:PLAN|SUMMARY|CONTEXT|REVIEW|VERIFICATION|UAT)\.md\b",
    r"\bSC\d\b",
)
TAG_RE = re.compile("|".join(f"(?:{p})" for p in TAG_PATTERNS))
REQ_RE = re.compile(r"\b([A-Z]{3,})-\d{2}(?!\d)")
SEED_POINTER_RE = re.compile(r"\(see SEED-(\d{3})\)")

# Python test-name tags (D-14).
TEST_FUNC_RES = (
    re.compile(r"phase\d{2,3}", re.IGNORECASE),
    re.compile(r"seed\d{3}", re.IGNORECASE),
    re.compile(r"(?:^|_)2[56]\d{4}[-_][a-z0-9]{3}(?:_|$)"),
)
TEST_FUNC_PART_RE = re.compile(r"(?:d|cr|wr)\d{2}")
TEST_CLASS_RES = (
    re.compile(r"(?:Phase|Seed)\d+"),
    re.compile(r"D\d{2}(?=[A-Z_]|$)"),
    re.compile(r"(?:Cr|Wr)\d{2}"),
)


def open_seeds() -> set[str]:
    """Seed ids ("SEED-042") whose file sits directly in .planning/seeds/ (open = not in closed/)."""
    if not SEEDS_DIR.is_dir():
        return set()
    found: set[str] = set()
    for p in SEEDS_DIR.glob("SEED-*.md"):
        m = re.match(r"(SEED-\d{3})-", p.name)
        if m:
            found.add(m.group(1))
    return found


def find_tags(text: str) -> list[str]:
    """All planning tags in `text` (no seed-pointer allowance applied)."""
    tags = [m.group(0) for m in TAG_RE.finditer(text)]
    for m in REQ_RE.finditer(text):
        if m.group(1) not in REQ_STOPLIST:
            tags.append(m.group(0))
    return tags


def strip_allowed_pointers(text: str) -> str:
    """Remove `(see SEED-NNN)` for seeds that are still open (D-12)."""
    seeds = open_seeds()
    return SEED_POINTER_RE.sub(lambda m: "" if f"SEED-{m.group(1)}" in seeds else m.group(0), text)


def name_has_tag(name: str, is_class: bool) -> bool:
    if is_class:
        return any(r.search(name) for r in TEST_CLASS_RES)
    if any(r.search(name) for r in TEST_FUNC_RES):
        return True
    return any(TEST_FUNC_PART_RE.fullmatch(part) for part in name.split("_"))


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if check and proc.returncode != 0:
        raise UsageError(
            f"git {' '.join(args)} failed: {proc.stderr.decode(errors='replace').strip()}"
        )
    return proc


def resolve_base(args: argparse.Namespace) -> str:
    base = getattr(args, "base", None)
    if not base:
        base_file = PHASE_DIR / "tools" / "PHASE_BASE"
        if not base_file.is_file():
            raise UsageError(f"no --base given and {base_file} is missing")
        base = base_file.read_text().strip()
    sha = git("rev-parse", "--verify", f"{base}^{{commit}}", check=False)
    if sha.returncode != 0:
        raise UsageError(f"base {base} is not a commit")
    full = sha.stdout.decode().strip()
    if git("merge-base", "--is-ancestor", full, "HEAD", check=False).returncode != 0:
        raise UsageError(f"base {full} is not an ancestor of HEAD")
    return full


def base_blob(base: str, rel: str) -> str | None:
    proc = git("show", f"{base}:{rel}", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8")


def name_status(base: str) -> list[tuple[str, list[str]]]:
    """`git diff --name-status -M BASE` (tracked files, working tree included) as (status, paths)."""
    out = git("diff", "--name-status", "-z", "-M", base, "--").stdout.decode("utf-8", "replace")
    fields = out.split("\0")
    entries: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        count = 2 if status[0] in "RC" else 1
        entries.append((status, fields[i + 1 : i + 1 + count]))
        i += 1 + count
    return entries


def renames_since(base: str) -> tuple[dict[str, str], dict[str, str]]:
    """(new -> old, old -> new) for renames between base and the working tree."""
    from_old: dict[str, str] = {}
    to_new: dict[str, str] = {}
    for status, names in name_status(base):
        if status.startswith("R") and len(names) == 2:
            from_old[names[1]] = names[0]
            to_new[names[0]] = names[1]
    return from_old, to_new


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def in_scope(rel: str) -> bool:
    """The one definition of "a file this phase may edit" (D-13)."""
    p = PurePosixPath(rel)
    s = p.as_posix()
    if s.startswith("app/"):
        return p.suffix in PY_SUFFIXES and not s.startswith(APP_EXCLUDED)
    if s.startswith("tests/"):
        return p.suffix in PY_SUFFIXES and not s.startswith(TESTS_EXCLUDED)
    if s.startswith(FE_ROOT):
        return p.suffix in FE_SUFFIXES and not s.startswith(FE_EXCLUDED)
    return False


def abs_arg(arg: str) -> Path:
    """A command-line path: absolute as given, relative to the cwd when that lies in the checkout,
    otherwise relative to the checkout root (so repo-relative paths work from any directory)."""
    p = Path(arg)
    if p.is_absolute():
        return p.resolve()
    candidate = (Path.cwd() / p).resolve()
    if candidate.is_relative_to(ROOT.resolve()):
        return candidate
    return (ROOT / p).resolve()


def to_rel(arg: str) -> str:
    try:
        return abs_arg(arg).relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise UsageError(f"{arg} is outside the checkout {ROOT}") from exc


def read_scope_file(arg: str) -> list[str]:
    path = abs_arg(arg)
    if not path.is_file():
        raise UsageError(f"scope file {arg} not found")
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def expand_dir(rel: str) -> list[str]:
    base = ROOT / rel
    return sorted(
        q.relative_to(ROOT).as_posix()
        for q in base.rglob("*")
        if q.is_file() and in_scope(q.relative_to(ROOT).as_posix())
    )


def add_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        action="append",
        default=[],
        metavar="FILE",
        help="file with one repo-relative path per line (repeatable)",
    )
    parser.add_argument("paths", nargs="*", help="files or directories (repo-relative or absolute)")


def resolve_selection(args: argparse.Namespace, allow_missing: bool = False) -> list[str]:
    """Selected in-scope files as sorted repo-relative paths. Out-of-scope files are an error."""
    entries: list[str] = []
    for scope in args.scope:
        entries.extend(to_rel(e) for e in read_scope_file(scope))
    entries.extend(to_rel(a) for a in args.paths)
    selected: set[str] = set()
    for rel in entries:
        full = ROOT / rel
        if full.is_dir():
            selected.update(expand_dir(rel))
            continue
        if not in_scope(rel):
            raise UsageError(
                f"{rel} is outside the cleanup scope (D-13); use diff --outside for rename follow-ups"
            )
        if not full.is_file() and not allow_missing:
            raise UsageError(f"{rel} does not exist")
        selected.add(rel)
    return sorted(selected)


def ensure_plugins(selection: Sequence[str]) -> None:
    """Fail fast (exit 2) when the selection holds FE files and the FE plugin is absent."""
    if any(PurePosixPath(rel).suffix in FE_SUFFIXES for rel in selection):
        load_fe_support()


def read_text(rel: str) -> str:
    return (ROOT / rel).read_bytes().decode("utf-8")


# ---------------------------------------------------------------------------
# Prose and token extraction
# ---------------------------------------------------------------------------


class Prose(NamedTuple):
    line: int
    col: int
    end_line: int
    end_col: int
    kind: str
    text: str


def py_prose(text: str) -> list[Prose]:
    """Comments, docstrings (every bare string statement) and tagged-or-not test names."""
    records: list[Prose] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            records.append(
                Prose(tok.start[0], tok.start[1], tok.end[0], tok.end[1], "comment", tok.string)
            )
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            seg = ast.get_source_segment(text, node.value) or ""
            end_line = node.end_lineno if node.end_lineno is not None else node.lineno
            end_col = node.end_col_offset if node.end_col_offset is not None else 0
            records.append(Prose(node.lineno, node.col_offset, end_line, end_col, "docstring", seg))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test"
        ):
            records.append(
                Prose(
                    node.lineno,
                    node.col_offset,
                    node.lineno,
                    node.col_offset,
                    "test-name",
                    node.name,
                )
            )
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            records.append(
                Prose(
                    node.lineno,
                    node.col_offset,
                    node.lineno,
                    node.col_offset,
                    "test-name",
                    node.name,
                )
            )
    records.sort(key=lambda r: (r.line, r.col))
    return records


def prose_for(rel: str, text: str) -> list[Prose]:
    suffix = PurePosixPath(rel).suffix
    if suffix in PY_SUFFIXES:
        return py_prose(text)
    fe = load_fe_support()
    return [Prose(*r) for r in fe.prose(rel, text)]


Token = tuple[str, str, int]
_BLOCK_KINDS = ("INDENT", "DEDENT", "NEWLINE")


def _docstring_starts(tree: ast.AST) -> set[tuple[int, int]]:
    starts: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            starts.add((node.value.lineno, node.value.col_offset))
    return starts


def py_tokens(text: str) -> list[Token]:
    """Code tokens as (kind, text, line): comments, docstring statements and test names removed."""
    raw = [
        t
        for t in tokenize.generate_tokens(io.StringIO(text).readline)
        if t.type not in (tokenize.ENDMARKER, tokenize.COMMENT, tokenize.NL)
    ]
    starts = _docstring_starts(ast.parse(text))
    out: list[Token] = []
    drop: set[int] = set()
    i = 0
    while i < len(raw):
        if raw[i].type == tokenize.STRING and raw[i].start in starts:
            j = i
            while j < len(raw) and raw[j].type == tokenize.STRING:
                j += 1
            if j < len(raw) and raw[j].type == tokenize.NEWLINE:
                drop.update(range(i, j + 1))
                i = j + 1
                continue
        i += 1
    prev_kw = ""
    for idx, t in enumerate(raw):
        if idx in drop:
            continue
        kind = tokenize.tok_name[t.type]
        string = t.string
        if kind in _BLOCK_KINDS:
            string = ""
        elif kind == "NAME":
            if prev_kw == "def" and string.startswith("test"):
                string = "test"
            elif prev_kw == "class" and string.startswith("Test"):
                string = "Test"
            prev_kw = string if string in ("def", "class") else ""
        else:
            prev_kw = ""
        out.append((kind, string, t.start[0]))
    return out


DIRECTIVE_RES = (
    re.compile(r"\bnoqa(?::\s*([A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*))?"),
    re.compile(r"\b(ty|type):\s*ignore(\[[^\]]*\])?"),
    re.compile(r"\bpragma:\s*no cover\b"),
    re.compile(r"\bfmt:\s*(off|on|skip)\b"),
    re.compile(r"\bpylint:\s*disable=[\w,\- ]+"),
)


def directive_heads(prose_records: Sequence[Prose]) -> Counter[str]:
    """Multiset of lint/type directive heads found in Python comments."""
    heads: Counter[str] = Counter()
    for rec in prose_records:
        if rec[4] != "comment":
            continue
        text = rec[5]
        for m in DIRECTIVE_RES[0].finditer(text):
            codes = m.group(1)
            heads[
                "noqa"
                if not codes
                else "noqa: " + ",".join(sorted(c.strip() for c in codes.split(",")))
            ] += 1
        for m in DIRECTIVE_RES[1].finditer(text):
            inner = (m.group(2) or "").replace(" ", "")
            heads[f"{m.group(1)}: ignore{inner}"] += 1
        for rx in DIRECTIVE_RES[2:]:
            for m in rx.finditer(text):
                heads[" ".join(m.group(0).split())] += 1
    return heads


_fe_module = None


def load_fe_support():
    """Lazy import of tools/fe_support.py (added by 241-04)."""
    global _fe_module
    if _fe_module is not None:
        return _fe_module
    path = TOOLS_DIR / "fe_support.py"
    if not path.is_file():
        raise UsageError("FE support is added by 241-04")
    import importlib.util

    spec = importlib.util.spec_from_file_location("fe_support", path)
    if spec is None or spec.loader is None:
        raise UsageError("FE support is added by 241-04")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _fe_module = module
    return module


def tokens_for(rel: str, text: str) -> list[Token]:
    if PurePosixPath(rel).suffix in PY_SUFFIXES:
        return py_tokens(text)
    return [tuple(t) for t in load_fe_support().tokens(rel, text)]  # type: ignore[misc]  # plugin shape


def directives_for(rel: str, records: Sequence[Prose]) -> Counter[str]:
    if PurePosixPath(rel).suffix in PY_SUFFIXES:
        return directive_heads(records)
    return Counter(load_fe_support().directive_heads(records))


# ---------------------------------------------------------------------------
# Rename maps
# ---------------------------------------------------------------------------


class RenameRule(NamedTuple):
    old: str
    new: str
    canon_paths: frozenset[str] | None


def load_rename_rules() -> list[RenameRule]:
    rules: list[RenameRule] = []
    directory = PHASE_DIR / "rename-maps"
    if not directory.is_dir():
        return rules
    for tsv in sorted(directory.glob("*.tsv")):
        for n, raw in enumerate(tsv.read_text(encoding="utf-8").splitlines()):
            if n == 0 or not raw.strip() or raw.startswith("#"):
                continue
            cols = raw.split("\t") + [""] * 6
            old, new, kind = cols[0].strip(), cols[1].strip(), cols[2].strip()
            canon = cols[5].strip()
            paths = (
                None
                if canon in ("", "*")
                else frozenset(p.strip() for p in canon.split(",") if p.strip())
            )
            for o, nw in _expand_rule(old, new, kind):
                rules.append(RenameRule(o, nw, paths))
    return rules


def _expand_rule(old: str, new: str, kind: str) -> list[tuple[str, str]]:
    if kind != "file" or not (old.endswith(".py") and new.endswith(".py")):
        return [(old, new)]
    pairs = [(old, new), (old[:-3].replace("/", "."), new[:-3].replace("/", "."))]
    stem_old, stem_new = PurePosixPath(old).stem, PurePosixPath(new).stem
    if stem_old != stem_new:
        pairs.append((stem_old, stem_new))
    return pairs


class Canon:
    """Rename-map canonicalization for one file path (the same function serves string tokens and text)."""

    def __init__(self, rules: Sequence[RenameRule], rel: str) -> None:
        applicable = [r for r in rules if r.canon_paths is None or rel in r.canon_paths]
        self.names = {r.old: r.new for r in applicable}
        olds = sorted(self.names, key=len, reverse=True)
        self.rx = (
            re.compile(
                r"(?<![A-Za-z0-9_])(?:"
                + "|".join(re.escape(o) for o in olds)
                + r")(?![A-Za-z0-9_])"
            )
            if olds
            else None
        )

    def text(self, s: str) -> str:
        if self.rx is None:
            return s
        return self.rx.sub(lambda m: self.names[m.group(0)], s)

    def token(self, tok: Token) -> tuple[str, str]:
        kind, string, _line = tok
        upper = kind.upper()
        if upper in ("NAME", "IDENTIFIER"):
            return kind, self.names.get(string, string)
        if "STRING" in upper or "TEMPLATE" in upper:
            return kind, self.text(string)
        return kind, string


# ---------------------------------------------------------------------------
# allow lists
# ---------------------------------------------------------------------------


class AllowEntry(NamedTuple):
    kind: str
    path: str
    needle: str
    reason: str


ALLOW_KINDS = ("scan", "diff", "directive")


def load_allow_file(path: Path) -> list[AllowEntry]:
    """TSV `kind<TAB>path<TAB>needle<TAB>reason`; a missing file is an empty list."""
    if not path.is_file():
        return []
    entries: list[AllowEntry] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.startswith("#"):
            continue
        cols = [c.strip() for c in raw.split("\t")] + [""] * 4
        if cols[0] == "kind":
            continue
        if cols[0] not in ALLOW_KINDS:
            raise UsageError(f"{path}:{n}: unknown allow kind {cols[0]!r}")
        entries.append(AllowEntry(cols[0], cols[1], cols[2], cols[3]))
    return entries


def add_allow_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow", action="append", default=[], metavar="FILE", help="allow-list TSV (repeatable)"
    )
    parser.add_argument("--plan", metavar="241-NN", help="load allow/<plan>.tsv for this plan")
    parser.add_argument(
        "--all-allow", action="store_true", help="load every allow/*.tsv (final gate)"
    )


def resolve_allow(args: argparse.Namespace) -> list[AllowEntry]:
    allow_dir = PHASE_DIR / "allow"
    files: list[Path] = []
    if getattr(args, "all_allow", False):
        files.extend(sorted(allow_dir.glob("*.tsv")))
    else:
        plan_ids = [args.plan] if getattr(args, "plan", None) else []
        for scope in getattr(args, "scope", []):
            m = re.fullmatch(r"(\d+-\d+)\.txt", Path(scope).name)
            if m:
                plan_ids.append(m.group(1))
        files.extend(allow_dir / f"{pid}.tsv" for pid in plan_ids)
    for extra in getattr(args, "allow", []):
        files.append(abs_arg(extra))
    entries: list[AllowEntry] = []
    for f in files:
        entries.extend(load_allow_file(f))
    return entries


def allowed_reason(entries: Sequence[AllowEntry], kind: str, rel: str, text: str) -> str | None:
    for e in entries:
        if e.kind == kind and fnmatch.fnmatchcase(rel, e.path) and e.needle in text:
            return e.reason
    return None


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

ADVISORY_RES = (re.compile(r"\bUAT\b"), re.compile(r"\.planning/"), re.compile(r"\bTask \d+\b"))
IDENT_TAG_RE = re.compile(r"(?i:phase_?\d{2,3}|seed_?\d{3})|PHASE_\d+|Phase\d+")
ADVISORY_SUFFIX = "/advisory"


class Finding(NamedTuple):
    path: str
    line: int
    kind: str
    text: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.kind}: {self.text}"

    @property
    def gating(self) -> bool:
        return not self.kind.endswith(ADVISORY_SUFFIX)


def scan_file(rel: str, identifiers: bool = False, advisory: bool = False) -> list[Finding]:
    text = read_text(rel)
    findings: list[Finding] = []
    for rec in prose_for(rel, text):
        if rec.kind == "test-name":
            if name_has_tag(rec.text, rec.text.startswith("Test")):
                findings.append(Finding(rel, rec.line, "test-name", rec.text))
            continue
        for offset, segment in enumerate(rec.text.split("\n")):
            if find_tags(strip_allowed_pointers(segment)):
                findings.append(Finding(rel, rec.line + offset, rec.kind, segment.strip()))
            elif advisory and any(rx.search(segment) for rx in ADVISORY_RES):
                findings.append(
                    Finding(rel, rec.line + offset, rec.kind + ADVISORY_SUFFIX, segment.strip())
                )
    if identifiers:
        seen: set[tuple[int, str]] = set()
        for kind, string, line in tokens_for(rel, text):
            if kind.upper() in ("NAME", "IDENTIFIER") and IDENT_TAG_RE.search(string):
                if (line, string) not in seen:
                    seen.add((line, string))
                    findings.append(Finding(rel, line, "identifier", string))
    return findings


def cmd_scan(args: argparse.Namespace) -> int:
    selection = resolve_selection(args)
    ensure_plugins(selection)
    allow = resolve_allow(args)
    findings: list[Finding] = []
    for rel in selection:
        findings.extend(scan_file(rel, args.identifiers, args.advisory))
    blocking = 0
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.kind)):
        reason = allowed_reason(allow, "scan", f.path, f.text) if f.gating else None
        suffix = f" (allowed: {reason})" if reason is not None else ""
        print(f.render() + suffix)
        if f.gating and reason is None:
            blocking += 1
    print(
        f"scan: {len(selection)} files, {len(findings)} matches, {blocking} blocking",
        file=sys.stderr,
    )
    return EXIT_FINDINGS if (args.gate and blocking) else EXIT_OK


# ---------------------------------------------------------------------------
# apply-edits
# ---------------------------------------------------------------------------


def cmd_apply_edits(args: argparse.Namespace) -> int:
    try:
        edits = json.loads(abs_arg(args.batch).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageError(f"cannot read edit batch {args.batch}: {exc}") from exc
    by_file: dict[str, list[dict]] = {}
    for e in edits:
        rel = to_rel(e["path"])
        if not in_scope(rel):
            raise UsageError(f"{rel} is outside the cleanup scope; apply-edits refuses it")
        by_file.setdefault(rel, []).append(e)
    new_texts: dict[str, str] = {}
    errors: list[str] = []
    for rel, file_edits in by_file.items():
        if not (ROOT / rel).is_file():
            errors.append(f"{rel}: file does not exist")
            continue
        lines = read_text(rel).split("\n")
        spans: list[tuple[int, int, list[str]]] = []
        for e in sorted(file_edits, key=lambda x: x["line"]):
            old_lines = e["old"].split("\n")
            start = e["line"] - 1
            end = start + len(old_lines)
            if start < 0 or end > len(lines) or lines[start:end] != old_lines:
                errors.append(f"{rel}:{e['line']}: old text does not match the current file")
                continue
            if spans and start < spans[-1][1]:
                errors.append(f"{rel}:{e['line']}: overlaps the previous edit")
                continue
            spans.append((start, end, e["new"].split("\n") if e["new"] != "" else []))
        for start, end, repl in reversed(spans):
            lines[start:end] = repl
        new_texts[rel] = "\n".join(lines)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("apply-edits: batch rejected, no file written", file=sys.stderr)
        return EXIT_FINDINGS
    for rel, new_text in new_texts.items():
        (ROOT / rel).write_bytes(new_text.encode("utf-8"))
    print(f"apply-edits: {len(edits)} edits in {len(new_texts)} files", file=sys.stderr)
    return EXIT_OK


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

NO_TOKENS = "(none)"


class Residue(NamedTuple):
    line: int
    base: str
    head: str

    def render(self) -> str:
        return f"- {self.base or NO_TOKENS} / + {self.head or NO_TOKENS}"


def _preview(toks: Sequence[tuple[str, str]]) -> str:
    shown = [t[1] if t[1] else f"<{t[0]}>" for t in toks[:DIFF_TOKEN_PREVIEW]]
    more = " ..." if len(toks) > DIFF_TOKEN_PREVIEW else ""
    return " ".join(shown) + more


def diff_token_streams(
    base_toks: Sequence[tuple[str, str]],
    head_toks: Sequence[tuple[str, str]],
    head_lines: Sequence[int],
) -> list[Residue]:
    """One Residue per non-equal opcode, positioned at the head line."""
    lo = 0
    while lo < len(base_toks) and lo < len(head_toks) and base_toks[lo] == head_toks[lo]:
        lo += 1
    hi_b, hi_h = len(base_toks), len(head_toks)
    while hi_b > lo and hi_h > lo and base_toks[hi_b - 1] == head_toks[hi_h - 1]:
        hi_b -= 1
        hi_h -= 1
    a, b = list(base_toks[lo:hi_b]), list(head_toks[lo:hi_h])
    if not a and not b:
        return []
    residue: list[Residue] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        pos = min(lo + j1, len(head_lines) - 1)
        line = head_lines[pos] if pos >= 0 and head_lines else 0
        residue.append(Residue(line, _preview(a[i1:i2]), _preview(b[j1:j2])))
    return residue


def duplicate_test_defs(text: str) -> set[tuple[str, str]]:
    """(scope, name) of test functions/classes defined more than once in the same scope."""
    dups: set[tuple[str, str]] = set()
    tree = ast.parse(text)
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.Module, ast.ClassDef)):
            continue
        names = Counter(
            n.name
            for n in scope.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.name.startswith(("test", "Test"))
        )
        scope_name = scope.name if isinstance(scope, ast.ClassDef) else "<module>"
        dups.update((scope_name, name) for name, count in names.items() if count > 1)
    return dups


class DiffResult(NamedTuple):
    residue: list[Residue]
    directive_residue: list[str]


def diff_python_like(
    rel: str, base_text: str, head_text: str, rules: Sequence[RenameRule]
) -> DiffResult:
    """Token-level comparison (Python and, through fe_support, FE files) plus directive multiset."""
    canon = Canon(rules, rel)
    try:
        base_all = tokens_for(rel, base_text)
        head_all = tokens_for(rel, head_text)
    except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
        return DiffResult([Residue(0, "", f"parse error: {exc}")], [])
    base_toks = [canon.token(t) for t in base_all]
    head_toks = [canon.token(t) for t in head_all]
    residue = diff_token_streams(base_toks, head_toks, [t[2] for t in head_all])
    if PurePosixPath(rel).suffix in PY_SUFFIXES:
        # A renamed test that collides with an existing name silently shadows a test.
        for scope_name, name in sorted(
            duplicate_test_defs(head_text) - duplicate_test_defs(base_text)
        ):
            residue.append(Residue(0, "", f"duplicate definition of {name} in {scope_name}"))
    base_dir = directives_for(rel, prose_for(rel, base_text))
    head_dir = directives_for(rel, prose_for(rel, head_text))
    directive_residue = [f"directive removed or changed: {h}" for h in sorted(base_dir - head_dir)]
    directive_residue += [f"directive added or changed: {h}" for h in sorted(head_dir - base_dir)]
    return DiffResult(residue, directive_residue)


def diff_text(
    rel: str, base_text: str, head_text: str, rules: Sequence[RenameRule]
) -> list[Residue]:
    """Rename-only check for a non-code text file: both sides canonicalized, then byte-identical."""
    canon = Canon(rules, rel)
    a = [canon.text(line) for line in base_text.split("\n")]
    b = [canon.text(line) for line in head_text.split("\n")]
    residue: list[Residue] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            base_line = a[i1 + k] if i1 + k < i2 else ""
            head_line = b[j1 + k] if j1 + k < j2 else ""
            residue.append(Residue(j1 + k + 1, base_line, head_line))
    return residue


def check_outside_path(arg: str, base: str, from_old: dict[str, str]) -> tuple[str, str]:
    """Validate one --outside PATH; return (head path, base path)."""
    rel = to_rel(arg)
    full = ROOT / rel
    if in_scope(rel):
        raise UsageError(
            f"--outside {rel}: the path is inside the cleanup scope; select it normally"
        )
    if full.is_dir():
        raise UsageError(f"--outside {rel}: expected one file, got a directory")
    base_rel = from_old.get(rel, rel)
    if not full.is_file() and base_blob(base, rel) is None:
        raise UsageError(f"--outside {rel}: missing in the working tree and in the base commit")
    return rel, base_rel


def pair_selection(
    selection: Sequence[str], base: str, from_old: dict[str, str], to_new: dict[str, str]
) -> tuple[dict[str, str], list[str]]:
    """Map head path -> base path (rename-aware) and list the selected files deleted since base."""
    heads: dict[str, str] = {}
    deleted: list[str] = []
    for rel in selection:
        if (ROOT / rel).is_file():
            heads[rel] = from_old.get(rel, rel)
        elif rel in to_new:
            heads[to_new[rel]] = rel
        elif base_blob(base, rel) is not None:
            deleted.append(rel)
    return heads, deleted


class FileDiff(NamedTuple):
    lines: list[str]
    failed: bool


def report_file_diff(
    head_rel: str,
    base_text: str,
    head_text: str,
    mode: str,
    rules: Sequence[RenameRule],
    allow: Sequence[AllowEntry],
) -> FileDiff:
    """Printable residue lines for one changed file; allowed items carry a suffix and do not fail."""
    if mode == "text":
        result = DiffResult(diff_text(head_rel, base_text, head_text, rules), [])
    else:
        result = diff_python_like(head_rel, base_text, head_text, rules)
    lines: list[str] = []
    failed = False
    for r in result.residue:
        reason = allowed_reason(allow, "diff", head_rel, r.head or r.base)
        suffix = f" (allowed: {reason})" if reason is not None else ""
        failed = failed or reason is None
        lines.append(f"{head_rel}:{r.line}: {r.render()}{suffix}")
    for msg in result.directive_residue:
        reason = allowed_reason(allow, "directive", head_rel, msg)
        suffix = f" (allowed: {reason})" if reason is not None else ""
        failed = failed or reason is None
        lines.append(f"{head_rel}:0: {msg}{suffix}")
    return FileDiff(lines, failed)


def cmd_diff(args: argparse.Namespace) -> int:
    base = resolve_base(args)
    selection = resolve_selection(args, allow_missing=True)
    ensure_plugins(selection)
    from_old, to_new = renames_since(base)
    outside = [check_outside_path(p, base, from_old) for p in args.outside]
    if not selection and not outside:
        raise UsageError("diff: no files selected")
    rules = load_rename_rules()
    allow = resolve_allow(args)
    heads, deleted = pair_selection(selection, base, from_old, to_new)
    failed = bool(deleted)
    for rel in deleted:
        print(f"{rel}:0: file deleted since base")
    targets: list[tuple[str, str, str]] = [(h, b, "code") for h, b in sorted(heads.items())]
    for head_rel, base_rel in outside:
        mode = "code" if PurePosixPath(head_rel).suffix in PY_SUFFIXES else "text"
        targets.append((head_rel, base_rel, mode))
    compared = 0
    for head_rel, base_rel, mode in targets:
        full = ROOT / head_rel
        if not full.is_file():
            print(f"{head_rel}:0: file deleted since base")
            failed = True
            continue
        base_text = base_blob(base, base_rel)
        head_text = read_text(head_rel)
        if base_text is None:
            print(f"{head_rel}:0: file added since base (not in {base[:9]})")
            failed = True
            continue
        if base_text == head_text:
            continue
        compared += 1
        report = report_file_diff(head_rel, base_text, head_text, mode, rules, allow)
        for line in report.lines:
            print(line)
        failed = failed or report.failed
    print(f"diff: {len(targets)} files selected, {compared} changed", file=sys.stderr)
    return EXIT_FINDINGS if failed else EXIT_OK


def cmd_outside(args: argparse.Namespace) -> int:
    """List changed paths (both sides of a rename) that the in-scope filter rejects."""
    base = resolve_base(args)
    paths: set[str] = set()
    for _status, names in name_status(base):
        paths.update(names)
    for p in sorted(paths):
        if not in_scope(p) and not p.startswith(".planning/"):
            print(p)
    return EXIT_OK


# ---------------------------------------------------------------------------
# rows and ledger
# ---------------------------------------------------------------------------

ROW_RE = re.compile(r"^\| `([^`]+)` \| ([ABM]) \| (.*?) \| (.*) \|\s*$")


class InvRow(NamedTuple):
    row_id: int
    verdict: str
    location: str
    path: str
    excerpt: str
    replacement: str


def load_inventory_rows() -> list[InvRow]:
    inventory = PHASE_DIR / "241-INVENTORY.md"
    if not inventory.is_file():
        raise UsageError(f"{inventory} not found")
    rows: list[InvRow] = []
    in_section = False
    for lineno, line in enumerate(inventory.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## 6."):
            in_section = True
            continue
        if line.startswith("## 7."):
            break
        if not in_section:
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        loc = m.group(1)
        path = loc.split(":", 1)[0].strip()
        if not path.startswith(INVENTORY_LOCATION_ROOTS):
            path = FE_ROOT + path
        rows.append(InvRow(lineno, m.group(2), loc, path, m.group(3), m.group(4)))
    return rows


def selected_rows(args: argparse.Namespace) -> list[InvRow]:
    selection = set(resolve_selection(args, allow_missing=True))
    return [r for r in load_inventory_rows() if r.path in selection]


def cmd_rows(args: argparse.Namespace) -> int:
    for r in selected_rows(args):
        print(f"INV-L{r.row_id} {r.verdict} {r.location} | {r.excerpt} | {r.replacement}")
    return EXIT_OK


LEDGER_LINE_RE = re.compile(rf"^INV-L(\d+):\s+({'|'.join(LEDGER_STATUSES)})\b[\s:,;\-—]*(.*)$")


def cmd_ledger(args: argparse.Namespace) -> int:
    ledger = abs_arg(args.ledger)
    if not ledger.is_file():
        print(f"ledger file {args.ledger} not found")
        return EXIT_FINDINGS
    entries: dict[int, tuple[str, str]] = {}
    failed = False
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LEDGER_LINE_RE.match(line)
        if not m:
            print(f"unparseable ledger line: {line}")
            failed = True
            continue
        entries[int(m.group(1))] = (m.group(2), m.group(3).strip())
    all_ids = {r.row_id for r in load_inventory_rows()}
    for row_id in sorted(entries):
        status, reason = entries[row_id]
        if row_id not in all_ids:
            print(f"unknown INV-L{row_id}: not an INVENTORY section 6 row")
            failed = True
        elif status != "APPLIED" and not reason:
            print(f"INV-L{row_id}: {status} needs a reason")
            failed = True
    for r in selected_rows(args):
        if r.row_id not in entries:
            print(f"missing INV-L{r.row_id} ({r.location})")
            failed = True
    return EXIT_FINDINGS if failed else EXIT_OK


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------

_extras_module = None


def load_extras():
    """Import tools/extras.py when present (added by 241-03); never fatal for the other commands."""
    global _extras_module
    if _extras_module is not None:
        return _extras_module
    path = TOOLS_DIR / "extras.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("extras", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["extras"] = module
        spec.loader.exec_module(module)
    except Exception as exc:  # a broken plugin must not take scan/diff down with it
        print(f"cleanup.py: extras.py failed to import: {exc}", file=sys.stderr)
        return None
    _extras_module = module
    return module


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

TAG_POSITIVES = (
    "Phase 238",
    "Phase 94.4",
    "D-04",
    "D-116-04",
    "SEED-042",
    "CR-01",
    "FE-WR-01",
    "T-189-17",
    "quick 260414-smt",
    "261016-fwd",
    "215-06",
    "Plan 03",
    "RESEARCH Pitfall 4",
    "BACK-01",
    "SC2",
)
TAG_NEGATIVES = (
    "Phase 1",
    "Phase 2/3",
    "20-40%",
    "45-55 band",
    "2026-05-04",
    "UTF-16",
    "FLAWCHESS-56",
    "game phase 2",
    "h-17",
)
SELFTEST_COMMIT_ARGS = ("-c", "user.name=selftest", "-c", "user.email=selftest@example.invalid")


@contextlib.contextmanager
def temp_repo():
    """A throwaway git repo that becomes ROOT for the duration of the block."""
    saved = (ROOT, PHASE_DIR, SEEDS_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        set_root(root)
        git("init", "-q")
        try:
            yield root
        finally:
            globals().update(ROOT=saved[0], PHASE_DIR=saved[1], SEEDS_DIR=saved[2])


def write_files(files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def commit_all(message: str = "selftest") -> str:
    git("add", "-A")
    git(*SELFTEST_COMMIT_ARGS, "-c", "commit.gpgsign=false", "commit", "-q", "-m", message)
    return git("rev-parse", "HEAD").stdout.decode().strip()


def run_captured(func, *args) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = func(*args)
    return code, out.getvalue(), err.getvalue()


def ns(**kw) -> argparse.Namespace:
    base = dict(
        scope=[],
        paths=[],
        allow=[],
        plan=None,
        all_allow=False,
        base=None,
        outside=[],
        gate=False,
        identifiers=False,
        advisory=False,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def raises_usage(func, *args) -> bool:
    try:
        func(*args)
    except UsageError:
        return True
    return False


def st_tag_pattern():
    for s in TAG_POSITIVES:
        assert find_tags(s), f"no tag found in {s!r}"
    for s in TAG_NEGATIVES:
        assert not find_tags(s), f"false tag {find_tags(s)} in {s!r}"


def st_seed_pointers():
    with temp_repo():
        write_files(
            {".planning/seeds/SEED-042-open.md": "x", ".planning/seeds/closed/SEED-043-c.md": "x"}
        )
        assert not find_tags(strip_allowed_pointers("# (see SEED-042)")), "open pointer rejected"
        assert find_tags(strip_allowed_pointers("# (see SEED-043)")), "closed seed allowed"
        assert find_tags(strip_allowed_pointers("# (see SEED-099)")), "missing seed allowed"
        assert find_tags(strip_allowed_pointers("# deferred to SEED-042")), "bare open seed allowed"


def st_in_scope_filter():
    yes = ("app/core/a.py", "tests/test_x.py", "frontend/src/a.tsx", "frontend/src/index.css")
    no = (
        "app/prompts/p.py",
        "app/data/d.py",
        "tests/fixtures/f.py",
        "frontend/src/generated/g.ts",
        "frontend/src/assets/a.js",
        "scripts/s.py",
        "docs/d.md",
        "app/readme.md",
    )
    for p in yes:
        assert in_scope(p), f"{p} should be in scope"
    for p in no:
        assert not in_scope(p), f"{p} should be out of scope"


def st_python_diff_ignores_prose():
    base = (
        '"""Mod."""\n\n\ndef f():\n    """Doc Phase 12."""\n    # old\n    return 1\n\n\n'
        "def test_phase238_x():\n    assert f() == 1\n\n\nclass TestPhase230Foo:\n    pass\n"
    )
    head = (
        '"""Module doc."""\n\n\ndef f():\n    """Better doc."""\n    return 1\n\n\n'
        "def test_f_returns_one():\n    assert f() == 1\n\n\nclass TestFoo:\n    pass\n"
    )
    res = diff_python_like("app/x.py", base, head, [])
    assert not res.residue and not res.directive_residue, f"unexpected residue {res}"


def st_python_diff_reports_code():
    base = 'X = "a"\nY = 1\nZ = foo(1)  # noqa: F401\n'
    cases = {
        "string": 'X = "b"\nY = 1\nZ = foo(1)  # noqa: F401\n',
        "number": 'X = "a"\nY = 2\nZ = foo(1)  # noqa: F401\n',
        "name": 'X = "a"\nY = 1\nZ = bar(1)  # noqa: F401\n',
    }
    for label, head in cases.items():
        assert diff_python_like("app/x.py", base, head, []).residue, f"{label} change not reported"
    removed = diff_python_like("app/x.py", base, 'X = "a"\nY = 1\nZ = foo(1)\n', [])
    assert removed.directive_residue and not removed.residue, "removed noqa head not reported"
    changed = diff_python_like("app/x.py", base, 'X = "a"\nY = 1\nZ = foo(1)  # noqa: F811\n', [])
    assert changed.directive_residue, "changed noqa codes not reported"


def st_rename_maps():
    base = 'a = old_name(1)\nb = "x old_name y"\nc = "old_names"\n'
    head = 'a = new_name(1)\nb = "x new_name y"\nc = "old_names"\n'
    rule = RenameRule("old_name", "new_name", None)
    assert not diff_python_like("app/x.py", base, head, [rule]).residue, "rename not canonicalized"
    assert diff_python_like("app/x.py", base, head, []).residue, "rename accepted without a map"
    scoped = RenameRule("old_name", "new_name", frozenset({"app/y.py"}))
    assert not diff_python_like("app/y.py", base, head, [scoped]).residue, "scoped rule ignored"
    assert diff_python_like("app/x.py", base, head, [scoped]).residue, "scoped rule leaked"


def st_duplicate_test_names():
    base = "def test_a():\n    pass\n\n\ndef test_b():\n    pass\n"
    head = "def test_a():\n    pass\n\n\ndef test_a():\n    pass\n"
    assert diff_python_like("tests/t.py", base, head, []).residue, "colliding test rename passed"


def st_apply_edits_atomic():
    with temp_repo() as root:
        write_files({"app/core/a.py": "# one\nx = 1\n# two\n", "app/core/b.py": "# three\ny = 2\n"})
        batch = root / "batch.json"
        batch.write_text(
            json.dumps(
                [
                    {"path": "app/core/a.py", "line": 1, "old": "# one", "new": "# uno"},
                    {"path": "app/core/b.py", "line": 1, "old": "# WRONG", "new": "# drei"},
                ]
            )
        )
        code, _out, _err = run_captured(cmd_apply_edits, ns(batch=str(batch)))
        assert code == EXIT_FINDINGS, "bad batch accepted"
        assert (root / "app/core/a.py").read_text() == "# one\nx = 1\n# two\n", "partial write"
        batch.write_text(
            json.dumps(
                [
                    {"path": "app/core/a.py", "line": 1, "old": "# one", "new": "# uno\n# eins"},
                    {"path": "app/core/a.py", "line": 3, "old": "# two", "new": ""},
                ]
            )
        )
        code, _out, _err = run_captured(cmd_apply_edits, ns(batch=str(batch)))
        assert code == EXIT_OK and (root / "app/core/a.py").read_text() == "# uno\n# eins\nx = 1\n"
        batch.write_text(json.dumps([{"path": "scripts/s.py", "line": 1, "old": "a", "new": "b"}]))
        assert raises_usage(cmd_apply_edits, ns(batch=str(batch))), "out-of-scope edit accepted"


def _outside_repo() -> str:
    write_files(
        {
            "docs/note.md": "Use old_name here\nand more\n",
            "scripts/tool.py": 'NAME = "old_name"\nx = 1\n',
            "app/core/a.py": "x = 1\n",
            "app/prompts/p.py": "P = 1\n",
            ".planning/phases/241-codebase-cleanup/rename-maps/241-99.tsv": (
                "old\tnew\tkind\tabsent_paths\tref\tcanon_paths\nold_name\tnew_name\tidentifier\t-\tt\t\n"
            ),
        }
    )
    return commit_all()


def st_diff_outside():
    with temp_repo():
        sha = _outside_repo()
        write_files({"docs/note.md": "Use new_name here\nand more\n"})
        code, out, _ = run_captured(cmd_diff, ns(base=sha, outside=["docs/note.md"]))
        assert code == EXIT_OK and not out, f"rename-only markdown rejected: {out}"
        write_files({"docs/note.md": "Use new_name here\nand different\n"})
        code, out, _ = run_captured(cmd_diff, ns(base=sha, outside=["docs/note.md"]))
        assert code == EXIT_FINDINGS and "docs/note.md:2:" in out, f"extra change missed: {out}"
        write_files({"docs/note.md": "Use old_name here\nand more\n"})
        write_files({"scripts/tool.py": 'NAME = "new_name"\nx = 1\n'})
        code, out, _ = run_captured(cmd_diff, ns(base=sha, outside=["scripts/tool.py"]))
        assert code == EXIT_OK, f"renamed string in outside .py rejected: {out}"
        write_files({"scripts/tool.py": 'NAME = "other"\nx = 1\n'})
        code, out, _ = run_captured(cmd_diff, ns(base=sha, outside=["scripts/tool.py"]))
        assert code == EXIT_FINDINGS, "changed string literal in outside .py accepted"
        write_files({"scripts/tool.py": 'NAME = "old_name"\nx = 1\n'})
        assert raises_usage(cmd_diff, ns(base=sha, outside=["app/core/a.py"])), "in-scope --outside"
        assert raises_usage(cmd_diff, ns(base=sha, outside=["docs"])), "directory --outside"
        assert raises_usage(cmd_diff, ns(base=sha, outside=["docs/missing.md"])), (
            "missing --outside"
        )
        assert raises_usage(cmd_diff, ns(base=sha, paths=["scripts/tool.py"])), (
            "positional accepted"
        )
        assert raises_usage(cmd_diff, ns(base=sha, scope=[]))  # empty selection is an error
        code, out, _ = run_captured(cmd_diff, ns(base=sha, outside=["scripts/tool.py"]))
        assert code == EXIT_OK and not out, "unchanged outside file must pass silently"


def st_scan_rejects_outside_option():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            build_parser().parse_args(["scan", "--outside", "docs/a.md"])
        except SystemExit as exc:
            assert exc.code == EXIT_USAGE, f"exit code {exc.code}"
            return
    raise AssertionError("scan accepted --outside")


def st_outside_command():
    with temp_repo():
        sha = _outside_repo()
        write_files(
            {
                "docs/note.md": "changed\n",
                "app/prompts/p.py": "P = 2\n",
                "app/core/a.py": "x = 2\n",
                ".planning/phases/241-codebase-cleanup/rename-maps/241-98.tsv": "old\tnew\n",
            }
        )
        git("add", "-A")
        code, out, _ = run_captured(cmd_outside, ns(base=sha))
        listed = out.split()
        assert code == EXIT_OK
        assert "docs/note.md" in listed and "app/prompts/p.py" in listed, f"missed: {listed}"
        assert "app/core/a.py" not in listed, "in-scope file listed"
        assert not any(p.startswith(".planning/") for p in listed), ".planning listed"


def st_allow_lists():
    with temp_repo():
        write_files(
            {
                "app/core/a.py": "# Phase 123 kept\nx = 1  # noqa: F401\n",
                ".planning/phases/241-codebase-cleanup/allow/241-99.tsv": (
                    "kind\tpath\tneedle\treason\nscan\tapp/core/a.py\tPhase 123\tkept on purpose\n"
                ),
            }
        )
        code, out, _ = run_captured(cmd_scan, ns(paths=["app/core/a.py"], gate=True))
        assert code == EXIT_FINDINGS, "tag passed without an allow entry"
        code, out, _ = run_captured(cmd_scan, ns(paths=["app/core/a.py"], gate=True, plan="241-99"))
        assert code == EXIT_OK and "(allowed: kept on purpose)" in out, f"scan allow: {out}"
        code, out, _ = run_captured(
            cmd_scan, ns(paths=["app/core/a.py"], gate=True, allow=["nonexistent.tsv"])
        )
        assert code == EXIT_FINDINGS, "missing --allow file must act as an empty list"
        sha = commit_all()
        write_files({"app/core/a.py": "# Phase 123 kept\nx = 2  # noqa: F401\n"})
        assert run_captured(cmd_diff, ns(base=sha, paths=["app/core/a.py"]))[0] == EXIT_FINDINGS
        extra = ROOT / "d.tsv"
        extra.write_text("kind\tpath\tneedle\treason\ndiff\tapp/core/a.py\t2\tvalue bump\n")
        code, out, _ = run_captured(
            cmd_diff, ns(base=sha, paths=["app/core/a.py"], allow=[str(extra)])
        )
        assert code == EXIT_OK and "(allowed: value bump)" in out, f"diff allow: {out}"
        write_files({"app/core/a.py": "# Phase 123 kept\nx = 1\n"})
        extra.write_text(
            "kind\tpath\tneedle\treason\ndirective\tapp/core/a.py\tnoqa: F401\tmoved\n"
        )
        code, out, _ = run_captured(
            cmd_diff, ns(base=sha, paths=["app/core/a.py"], allow=[str(extra)])
        )
        assert code == EXIT_OK and "(allowed: moved)" in out, f"directive allow: {out}"


def st_identifiers_and_advisory():
    with temp_repo():
        write_files(
            {
                "app/core/a.py": (
                    "def _phase80_item_from_metrics():\n    return 1\n\n\n"
                    "PHASE_12 = 3\nphase_count = 2\n\n\ndef test_phase238_x():\n    pass\n"
                    "# UAT note for .planning/ files, Task 4\n"
                )
            }
        )
        found = scan_file("app/core/a.py", identifiers=True)
        idents = {f.text for f in found if f.kind == "identifier"}
        assert idents == {"_phase80_item_from_metrics", "PHASE_12"}, f"identifiers: {idents}"
        assert not any(f.kind.endswith(ADVISORY_SUFFIX) for f in found), "advisory without flag"
        advisory = [f for f in scan_file("app/core/a.py", advisory=True) if not f.gating]
        assert advisory, "advisory hints missing"
        code, _out, _ = run_captured(
            cmd_scan, ns(paths=["app/core/a.py"], gate=True, advisory=True)
        )
        assert code == EXIT_FINDINGS  # the tagged test name still gates
        write_files({"app/core/a.py": "# UAT note\n"})
        code, out, _ = run_captured(cmd_scan, ns(paths=["app/core/a.py"], gate=True, advisory=True))
        assert code == EXIT_OK and "comment/advisory" in out, f"advisory must not gate: {out}"


def st_rows_and_ledger():
    inventory = (
        "## 6. Comment fixes\n\n| Location | V | Current excerpt | Replacement |\n|---|---|---|---|\n"
        "| `app/core/a.py:3` | A | old text | new text |\n"
        "| `app/core/b.py:4` | M | other | fix |\n"
        "| `hooks/useX.ts:9` | B | fe row | leave |\n\n## 7. Seeds\n"
    )
    with temp_repo() as root:
        write_files(
            {
                ".planning/phases/241-codebase-cleanup/241-INVENTORY.md": inventory,
                "app/core/a.py": "x = 1\n",
                "app/core/b.py": "x = 1\n",
                "frontend/src/hooks/useX.ts": "export {}\n",
            }
        )
        code, out, _ = run_captured(
            cmd_rows, ns(paths=["app/core/a.py", "frontend/src/hooks/useX.ts"])
        )
        rows = out.strip().splitlines()
        assert code == EXIT_OK and len(rows) == 2, f"rows: {rows}"
        assert rows[0].startswith("INV-L5 A app/core/a.py:3 |"), rows[0]
        assert rows[1].startswith("INV-L7 B hooks/useX.ts:9 |"), rows[1]
        ledger = root / "ledger.txt"
        sel = ns(paths=["app/core/a.py", "frontend/src/hooks/useX.ts"], ledger=str(ledger))
        ledger.write_text("INV-L5: APPLIED\n")
        code, out, _ = run_captured(cmd_ledger, sel)
        assert code == EXIT_FINDINGS and "missing INV-L7" in out, f"missing row not reported: {out}"
        ledger.write_text("INV-L5: APPLIED\nINV-L7: LEFT\n")
        assert run_captured(cmd_ledger, sel)[0] == EXIT_FINDINGS, "reasonless LEFT accepted"
        ledger.write_text("INV-L5: APPLIED\nINV-L7: LEFT contract row\n")
        assert run_captured(cmd_ledger, sel)[0] == EXIT_OK, "complete ledger rejected"


def st_fe_hook_wired():
    if (TOOLS_DIR / "fe_support.py").is_file():
        return  # the plugin exists (241-04); its own cases live there
    with temp_repo():
        write_files({"frontend/src/main.tsx": "export {}\n"})
        sha = commit_all()
        write_files({"frontend/src/main.tsx": "export {} // x\n"})
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                cmd_diff(ns(base=sha, paths=["frontend/src/main.tsx"]))
        except UsageError as exc:
            assert "FE support is added by 241-04" in str(exc)
            return
        raise AssertionError("FE diff did not hit the plugin hook")


SELFTEST_CASES: tuple[tuple[str, Callable[[], None]], ...] = (
    ("tag pattern matches and non-matches", st_tag_pattern),
    ("open seed pointers only", st_seed_pointers),
    ("in-scope filter", st_in_scope_filter),
    ("python diff ignores prose and test names", st_python_diff_ignores_prose),
    ("python diff reports code and directive changes", st_python_diff_reports_code),
    ("rename maps and canon_paths", st_rename_maps),
    ("duplicate test names after a rename", st_duplicate_test_names),
    ("apply-edits is all-or-nothing", st_apply_edits_atomic),
    ("diff --outside", st_diff_outside),
    ("--outside is diff-only", st_scan_rejects_outside_option),
    ("outside command", st_outside_command),
    ("allow lists", st_allow_lists),
    ("identifiers and advisory", st_identifiers_and_advisory),
    ("rows and ledger", st_rows_and_ledger),
    ("FE plugin hook wired", st_fe_hook_wired),
)


def cmd_selftest(_args: argparse.Namespace) -> int:
    cases = list(SELFTEST_CASES)
    extras = load_extras()
    if extras is not None and hasattr(extras, "selftest_cases"):
        cases.extend(extras.selftest_cases())
    failures = 0
    for name, fn in cases:
        try:
            fn()
        except Exception as exc:  # report every failing case instead of stopping at the first
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {name}")
    print(f"selftest: {len(cases) - failures}/{len(cases)} passed")
    return EXIT_FINDINGS if failures else EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleanup.py", description=(__doc__ or "").split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="list planning tags in prose")
    add_selection_args(p)
    add_allow_args(p)
    p.add_argument("--gate", action="store_true", help="exit 1 when any match is not allowed")
    p.add_argument("--identifiers", action="store_true", help="also report tag-shaped identifiers")
    p.add_argument("--advisory", action="store_true", help="also print non-gating chronology hints")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("apply-edits", help="apply a JSON batch of line edits")
    p.add_argument("batch", metavar="FILE.json")
    p.set_defaults(func=cmd_apply_edits)

    p = sub.add_parser(
        "diff", help="prove only comments, docstrings, test names and renames changed"
    )
    add_selection_args(p)
    add_allow_args(p)
    p.add_argument("--base", help="base commit (default: tools/PHASE_BASE)")
    p.add_argument(
        "--outside",
        action="append",
        default=[],
        metavar="PATH",
        help="opt in one out-of-scope file a rename follows into (repeatable)",
    )
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("outside", help="list changed paths the in-scope filter rejects")
    p.add_argument("--base", help="base commit (default: tools/PHASE_BASE)")
    p.set_defaults(func=cmd_outside)

    p = sub.add_parser("rows", help="print INVENTORY section 6 rows in the selection")
    add_selection_args(p)
    p.set_defaults(func=cmd_rows)

    p = sub.add_parser("ledger", help="check every selected row has a ledger status")
    add_selection_args(p)
    p.add_argument("--ledger", required=True, metavar="FILE")
    p.set_defaults(func=cmd_ledger)

    p = sub.add_parser("selftest", help="run the built-in fixtures")
    p.set_defaults(func=cmd_selftest)

    extras = load_extras()
    if extras is not None and hasattr(extras, "register"):
        extras.register(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UsageError as exc:
        print(f"cleanup.py: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.modules.setdefault("cleanup", sys.modules["__main__"])
    sys.exit(main())
