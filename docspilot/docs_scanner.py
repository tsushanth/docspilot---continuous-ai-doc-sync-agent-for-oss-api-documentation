"""Find Markdown docs in a repo, split them into heading-delimited sections,
and shortlist which sections plausibly reference a set of changed symbols.

Plain-text/regex only — no doc-site-generator-specific parsing (frontmatter,
Mintlify/Docusaurus/GitBook config) is in scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class DocSection:
    doc_path: str
    heading: str
    level: int
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    text: str  # full section text including heading line

    @property
    def id(self) -> str:
        return f"{self.doc_path}#{self.heading}"


@dataclass
class Doc:
    path: str
    full_text: str
    sections: list[DocSection] = field(default_factory=list)


def find_docs(repo: str) -> list[str]:
    """Return relative paths of all *.md files in the repo, excluding .git."""
    root = Path(repo)
    paths = []
    for p in sorted(root.rglob("*.md")):
        if ".git" in p.parts:
            continue
        paths.append(str(p.relative_to(root)))
    return paths


def split_sections(doc_path: str, text: str) -> list[DocSection]:
    """Split a markdown doc's text into sections, one per heading.

    Any text before the first heading is captured as a section with an
    empty heading (the doc's preamble), so no content is lost.
    """
    lines = text.splitlines()
    sections: list[DocSection] = []

    heading = ""
    level = 0
    start_line = 1
    buffer: list[str] = []

    def flush(end_line: int):
        if buffer or heading:
            sections.append(
                DocSection(
                    doc_path=doc_path,
                    heading=heading,
                    level=level,
                    start_line=start_line,
                    end_line=end_line,
                    text="\n".join(buffer),
                )
            )

    for i, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            flush(i - 1)
            heading = m.group(2).strip()
            level = len(m.group(1))
            start_line = i
            buffer = [line]
        else:
            buffer.append(line)

    flush(len(lines))
    return [s for s in sections if s.text.strip()]


def load_docs(repo: str) -> list[Doc]:
    docs = []
    for rel_path in find_docs(repo):
        full_path = Path(repo) / rel_path
        text = full_path.read_text(encoding="utf-8")
        docs.append(Doc(path=rel_path, full_text=text, sections=split_sections(rel_path, text)))
    return docs


_TOKEN_RE = re.compile(r"--[\w-]+|[A-Za-z_]\w*")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text))


def shortlist_candidates(docs: list[Doc], symbol_names: set[str]) -> list[DocSection]:
    """Return doc sections whose text mentions at least one of the given
    symbol/flag names, ordered by (doc path, start_line).
    """
    if not symbol_names:
        return []

    candidates: list[DocSection] = []
    for doc in docs:
        for section in doc.sections:
            tokens = _tokenize(section.text)
            if tokens & symbol_names:
                candidates.append(section)

    candidates.sort(key=lambda s: (s.doc_path, s.start_line))
    return candidates
