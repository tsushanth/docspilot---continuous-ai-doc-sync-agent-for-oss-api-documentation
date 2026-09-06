"""DocsPilot CLI: detect stale docs between two commits and propose rewrites.

Usage:
    python -m docspilot.cli --repo <path> --base <sha> --head <sha> \\
        [--out ./output] [--mock]
"""

from __future__ import annotations

import argparse
import sys

from docspilot.code_signals import extract_signals
from docspilot.docs_scanner import load_docs, shortlist_candidates
from docspilot.git_diff import file_hunks, unified_diff
from docspilot.llm_analyzer import analyze
from docspilot.report import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docspilot",
        description="Detect stale docs between two git refs and propose rewrites.",
    )
    parser.add_argument("--repo", required=True, help="Path to the git repository")
    parser.add_argument("--base", required=True, help="Base ref (before the PR)")
    parser.add_argument("--head", required=True, help="Head ref (after the PR)")
    parser.add_argument(
        "--out", default="./output", help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use a canned analyzer response instead of calling the Anthropic API",
    )
    return parser


def run(repo: str, base: str, head: str, out: str, mock: bool) -> int:
    diffs = file_hunks(repo, base, head)
    diff_text = unified_diff(repo, base, head)

    signals = extract_signals(diffs)
    docs = load_docs(repo)
    candidates = shortlist_candidates(docs, signals.all_names())

    findings = analyze(diff_text, signals, candidates, mock=mock)

    write_outputs(repo, docs, findings, out)

    print(f"DocsPilot: {len(findings)} stale section(s) found. See {out}/report.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args.repo, args.base, args.head, args.out, args.mock)


if __name__ == "__main__":
    sys.exit(main())
