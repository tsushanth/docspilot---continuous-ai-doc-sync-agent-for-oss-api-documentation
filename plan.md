# DocsPilot — Local MVP Scaffold Plan

## Goal of this scaffold

Prove the core value loop locally, with zero deployment:

> Given a repo at two commits (before/after a merged PR), detect which code
> changes affect documented behavior, flag exactly which doc sections are now
> stale, and produce a proposed rewrite for each — as local files/diffs a
> maintainer could review and apply.

Everything about *how the trigger arrives* (GitHub webhook, Marketplace app,
Action YAML) and *how the fix lands* (auto-opened PR) is packaging around this
loop, not the loop itself. The scaffold proves the loop; it does not ship the
packaging.

## 1. Stack

**Python 3 CLI, single small package, stdlib + one LLM SDK.**

- `git` via `subprocess` (no GitPython dependency) — just need `git diff`,
  `git show`, changed-file lists between two refs.
- Plain-text/markdown parsing with stdlib (`re`, `pathlib`) — no doc-site
  framework parsers (no Mintlify/Docusaurus/GitBook SDKs).
- `anthropic` Python SDK for the one step that is genuinely irreplaceable by
  hand-rolled logic: deciding *semantically* whether a doc section is now
  wrong, and drafting the rewrite. This is core value, not infra — a
  regex/AST diff can tell you a function signature changed, but not whether
  prose describing it is now misleading.
- `pytest` for tests.
- No web framework, no database, no queue, no Docker.

Why Python over Node/TS despite the real product being a GitHub Action (which
would be JS/TS in production): the scaffold's job is to validate the
detection+rewrite logic, not the Action runtime. Python's stdlib text/subprocess
handling is less ceremony for a throwaway CLI, and porting the validated logic
to a TS Action later is a translation exercise, not a redesign.

## 2. Explicitly out of scope for this scaffold

- **No GitHub integration of any kind**: no webhook listener, no GitHub App,
  no Octokit/PyGithub calls, no auto-opened PRs against a real remote. The
  "auto-opens a PR" step is simulated by writing proposed doc content to a
  local `output/proposed/` directory plus a unified diff — a maintainer-ready
  patch without needing repo write access or a GitHub token.
- **No GitHub Actions/Marketplace packaging**: no `action.yml`, no Docker
  action image, no Marketplace listing assets.
- **No auth, no accounts, no billing/tiers**: free vs. paid tier logic,
  private-repo entitlement checks, and org/user accounts are all product
  concerns unrelated to whether the detection works.
- **No hosting/deploy**: runs as a local CLI invocation only.
- **No Mintlify/Docusaurus/GitBook-specific integrations**: docs are read as
  plain Markdown files on disk; site-generator-specific config/frontmatter
  parsing is deferred.
- **No database or persistence layer**: no tracking of "already flagged"
  sections across runs, no history — each run is a fresh, stateless analysis
  of one before/after commit pair.
- **No CI/webhook trigger logic**: the user supplies `--base` and `--head`
  refs by hand instead of the tool watching for merges.
- **LLM API call is the one exception left in**: it's kept because the core
  value (semantic staleness judgment + rewrite drafting) is not demonstrable
  without it. To keep tests and a no-key demo possible, the CLI supports a
  `--mock` mode that swaps in a canned analyzer response instead of calling
  the network.

## 3. File/directory layout

```
docspilot/
  __init__.py
  cli.py              # argparse entry point: --repo --base --head --mock --out
  git_diff.py         # subprocess wrappers: changed files, unified diff, per-file hunks
  code_signals.py      # naive extraction of "public surface" touches from a diff
                        # (function/class defs, CLI flags, exported symbols — regex-based, language-agnostic best-effort)
  docs_scanner.py      # find *.md docs in repo, split into sections (by heading),
                        # do keyword/symbol overlap to shortlist candidate-stale sections
  llm_analyzer.py      # build prompt from (diff + candidate doc sections),
                        # call Anthropic API for verdict + rewrite; --mock path
                        # returns a fixture response instead
  report.py            # render markdown report of findings; write proposed
                        # rewritten doc files + unified diff to output dir

tests/
  fixtures/
    sample_repo/        # tiny throwaway git repo fixture (initialized in a
                          # pytest fixture, not committed as a real .git):
                          # README.md + api.py, two commits representing a
                          # "PR" that renames/changes a documented function
  test_git_diff.py       # asserts changed-file/hunk extraction is correct
  test_docs_scanner.py   # asserts section splitting + candidate shortlisting
  test_cli_mock_e2e.py   # runs the full CLI with --mock against the fixture
                          # repo, asserts report.md + proposed/README.md content

requirements.txt         # anthropic, pytest
plan.md                  # this file
```

No `src/` nesting, no `pyproject.toml`/packaging metadata beyond what's needed
to run `python -m docspilot.cli` and `pytest` locally.

## 4. Verification

- **Unit tests** (`pytest tests/`) for the pure-logic pieces that need no
  network: `git_diff.py` (given two commits in a fixture repo, returns the
  right changed files/hunks) and `docs_scanner.py` (given a README with
  multiple headings, returns correct sections and correctly shortlists the
  one mentioning the changed function).
- **Mocked end-to-end test** (`test_cli_mock_e2e.py`): runs the actual CLI
  entry point against the fixture repo with `--mock`, asserts that
  `output/report.md` names the stale section and `output/proposed/README.md`
  contains the expected rewritten text — proves the full pipeline wires
  together without requiring an API key in CI.
- **Manual run-through** (real LLM call, requires `ANTHROPIC_API_KEY`):
  ```
  python -m docspilot.cli \
    --repo ./tests/fixtures/sample_repo \
    --base <sha-before> --head <sha-after> \
    --out ./output

  cat ./output/report.md
  diff ./tests/fixtures/sample_repo/README.md ./output/proposed/README.md
  ```
  Success criteria: the report correctly identifies the README section
  describing the changed function/endpoint as stale, and the proposed
  rewrite in `output/proposed/README.md` accurately reflects the new code
  behavior (judged by eye against the fixture's intentional change).
