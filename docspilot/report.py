"""Render a markdown findings report and write proposed rewritten doc files
plus a unified diff to an output directory.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from docspilot.docs_scanner import Doc
from docspilot.llm_analyzer import Finding


def render_report(findings: list[Finding]) -> str:
    if not findings:
        return "# DocsPilot Report\n\nNo stale documentation sections detected.\n"

    lines = ["# DocsPilot Report", "", f"Found {len(findings)} stale section(s):", ""]
    for f in findings:
        lines.append(f"## {f.doc_path} — \"{f.heading}\"")
        lines.append("")
        lines.append(f"**Why it's stale:** {f.reason}")
        lines.append("")
        lines.append("**Proposed rewrite:**")
        lines.append("")
        lines.append("```markdown")
        lines.append(f.rewritten_text)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _apply_rewrite(doc: Doc, finding: Finding) -> str:
    """Return the doc's full text with the matching section's text replaced
    by the finding's rewritten_text.
    """
    section = next(
        (s for s in doc.sections if s.heading == finding.heading),
        None,
    )
    if section is None:
        return doc.full_text

    lines = doc.full_text.splitlines()
    before = lines[: section.start_line - 1]
    after = lines[section.end_line :]
    new_section_lines = finding.rewritten_text.splitlines()
    while new_section_lines and new_section_lines[-1] == "":
        new_section_lines.pop()
    if after:
        new_section_lines.append("")
    return "\n".join(before + new_section_lines + after) + "\n"


def write_outputs(
    repo: str,
    docs: list[Doc],
    findings: list[Finding],
    out_dir: str,
) -> None:
    """Write output/report.md, output/proposed/<doc>, and output/proposed.diff."""
    out_path = Path(out_dir)
    proposed_dir = out_path / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    report_text = render_report(findings)
    (out_path / "report.md").write_text(report_text, encoding="utf-8")

    findings_by_doc: dict[str, list[Finding]] = {}
    for f in findings:
        findings_by_doc.setdefault(f.doc_path, []).append(f)

    diff_chunks = []
    for doc in docs:
        doc_findings = findings_by_doc.get(doc.path)
        if not doc_findings:
            continue

        # Apply bottom-to-top so each rewrite's line-range offsets (computed
        # against the original doc) stay valid for sections above it.
        ordered = sorted(
            doc_findings,
            key=lambda f: next(
                (s.start_line for s in doc.sections if s.heading == f.heading), 0
            ),
            reverse=True,
        )
        new_text = doc.full_text
        for finding in ordered:
            working_doc = Doc(path=doc.path, full_text=new_text, sections=doc.sections)
            new_text = _apply_rewrite(working_doc, finding)

        proposed_path = proposed_dir / doc.path
        proposed_path.parent.mkdir(parents=True, exist_ok=True)
        proposed_path.write_text(new_text, encoding="utf-8")

        diff_chunks.append(
            "".join(
                difflib.unified_diff(
                    doc.full_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=f"a/{doc.path}",
                    tofile=f"b/{doc.path}",
                )
            )
        )

    (out_path / "proposed.diff").write_text("".join(diff_chunks), encoding="utf-8")
