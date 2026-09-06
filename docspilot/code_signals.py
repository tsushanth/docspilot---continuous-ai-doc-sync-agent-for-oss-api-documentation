"""Naive, language-agnostic-best-effort extraction of "public surface" symbols
touched by a diff (function/class defs, CLI flags, exported names).

This is intentionally regex-based rather than a real AST parser: the goal is
a cheap shortlist of symbol names to correlate against doc text, not a
correct parse of any one language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from docspilot.git_diff import FileDiff

# Patterns that plausibly denote a "public surface" symbol definition line,
# across a handful of common languages. Deliberately permissive.
_DEF_PATTERNS = [
    re.compile(r"^\s*def\s+(\w+)\s*\("),  # Python function
    re.compile(r"^\s*class\s+(\w+)\b"),  # Python/JS/TS class
    re.compile(r"^\s*(?:export\s+)?function\s+(\w+)\s*\("),  # JS/TS function
    re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?\w[\w<>\[\]]*\s+(\w+)\s*\("),  # Java/C#-ish method
    re.compile(r"^\s*func\s+(\w+)\s*\("),  # Go
]

# CLI flag / argparse option patterns, e.g. `--base`, `add_argument("--foo")`
_FLAG_PATTERN = re.compile(r"[\"'](--[\w-]+)[\"']")
_BARE_FLAG_PATTERN = re.compile(r"(?<![\w-])(--[\w-]+)")


@dataclass
class Signal:
    """A single touched public-surface symbol."""

    name: str
    kind: str  # "symbol" or "flag"
    file: str
    added: bool  # True if introduced/changed on the "+" side, False if removed


@dataclass
class DiffSignals:
    symbols: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)
    details: list[Signal] = field(default_factory=list)

    def all_names(self) -> set[str]:
        return self.symbols | self.flags


def _extract_from_line(line: str) -> list[tuple[str, str]]:
    """Return list of (name, kind) found in a single diff content line."""
    found: list[tuple[str, str]] = []
    for pattern in _DEF_PATTERNS:
        m = pattern.search(line)
        if m:
            found.append((m.group(1), "symbol"))
    for pattern in (_FLAG_PATTERN, _BARE_FLAG_PATTERN):
        for m in pattern.finditer(line):
            found.append((m.group(1), "flag"))
    return found


def extract_signals(file_diffs: list[FileDiff]) -> DiffSignals:
    """Scan unified-diff hunks for added/removed public-surface symbols."""
    signals = DiffSignals()

    for fd in file_diffs:
        for line in fd.hunk.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+") or line.startswith("-"):
                added = line.startswith("+")
                content = line[1:]
                for name, kind in _extract_from_line(content):
                    signals.details.append(
                        Signal(name=name, kind=kind, file=fd.path, added=added)
                    )
                    if kind == "symbol":
                        signals.symbols.add(name)
                    else:
                        signals.flags.add(name)

    return signals
