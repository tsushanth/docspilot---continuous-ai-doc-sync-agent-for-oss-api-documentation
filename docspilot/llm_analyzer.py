"""Build a prompt from (diff + candidate doc sections) and ask Claude to
judge which sections are now stale and draft rewrites.

`--mock` swaps in a canned fixture response so tests and a no-key demo run
without a network call.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from docspilot.code_signals import DiffSignals
from docspilot.docs_scanner import DocSection

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are DocsPilot, an assistant that reviews a code diff \
against candidate documentation sections and decides which sections are now \
stale (i.e. describe behavior that no longer matches the code) and, for each \
stale section, drafts a corrected rewrite.

Respond ONLY with a JSON object of this exact shape:
{
  "findings": [
    {
      "doc_path": "<path to the markdown file>",
      "heading": "<section heading text>",
      "is_stale": true,
      "reason": "<one or two sentences on why this section is now wrong>",
      "rewritten_text": "<full replacement text for this section, including its heading line>"
    }
  ]
}

Only include sections in "findings" where is_stale is true. If no candidate \
section is actually stale, return {"findings": []}. Do not invent sections \
that were not in the candidate list."""


@dataclass
class Finding:
    doc_path: str
    heading: str
    reason: str
    rewritten_text: str


def _build_user_prompt(diff_text: str, signals: DiffSignals, candidates: list[DocSection]) -> str:
    candidate_blocks = []
    for section in candidates:
        candidate_blocks.append(
            f"### Candidate section: {section.doc_path} :: {section.heading!r}\n"
            f"{section.text}"
        )

    return (
        "## Code diff\n"
        f"{diff_text}\n\n"
        "## Public-surface symbols/flags touched by this diff\n"
        f"{sorted(signals.all_names())}\n\n"
        "## Candidate documentation sections (shortlisted by symbol overlap)\n"
        + "\n\n".join(candidate_blocks)
    )


def _mock_response(candidates: list[DocSection]) -> dict:
    """Canned response used with --mock: flags the first candidate section as
    stale with a simple rewrite fixture, for deterministic tests/demos.
    """
    if not candidates:
        return {"findings": []}

    section = candidates[0]
    return {
        "findings": [
            {
                "doc_path": section.doc_path,
                "heading": section.heading,
                "is_stale": True,
                "reason": (
                    "[mock] The code diff changed a public symbol referenced "
                    "in this section, so the described behavior is likely stale."
                ),
                "rewritten_text": (
                    f"{'#' * section.level} {section.heading}\n\n"
                    "[mock] This section has been updated to reflect the new "
                    "function behavior introduced in the latest change.\n"
                ),
            }
        ]
    }


def analyze(
    diff_text: str,
    signals: DiffSignals,
    candidates: list[DocSection],
    mock: bool = False,
) -> list[Finding]:
    """Ask the LLM (or the mock fixture) which candidate sections are stale
    and how to rewrite them.
    """
    if mock:
        raw = _mock_response(candidates)
    else:
        raw = _call_anthropic(diff_text, signals, candidates)

    findings = []
    for item in raw.get("findings", []):
        if not item.get("is_stale"):
            continue
        findings.append(
            Finding(
                doc_path=item["doc_path"],
                heading=item["heading"],
                reason=item.get("reason", ""),
                rewritten_text=item.get("rewritten_text", ""),
            )
        )
    return findings


def _call_anthropic(diff_text: str, signals: DiffSignals, candidates: list[DocSection]) -> dict:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it, or pass --mock to run "
            "without calling the network."
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_user_prompt(diff_text, signals, candidates)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    return json.loads(text)
