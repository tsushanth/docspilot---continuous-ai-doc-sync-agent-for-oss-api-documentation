# DocsPilot (local MVP scaffold)

DocsPilot detects when a code change makes your documentation wrong. Point it
at a repo and two commits (a "before" and "after" — e.g. the parent commit
and head of a merged PR), and it:

1. Diffs the code between the two refs.
2. Extracts the public-surface symbols/flags touched (function/class defs,
   CLI flags — regex-based, language-agnostic best-effort).
3. Scans the repo's `*.md` docs, splits them into sections by heading, and
   shortlists sections that mention a touched symbol.
4. Asks an LLM (Claude) to judge which shortlisted sections are now
   semantically stale, and to draft a rewrite for each.
5. Writes a findings report and proposed rewritten doc files to a local
   output directory — no GitHub access required.

This is a scaffold for the core detection+rewrite loop only. It does **not**
include the GitHub App/Action packaging, auto-opened PRs, auth/billing, or
doc-site-generator integrations (Mintlify/Docusaurus/GitBook) that the full
product would have — those are deliberately out of scope here. See
[`plan.md`](./plan.md) for the full scope rationale.

## What "auto-opens a PR" means in this scaffold

Instead of opening a real GitHub PR, DocsPilot writes:

- `output/report.md` — human-readable findings (which sections are stale, why).
- `output/proposed/<doc path>` — the full doc file with stale sections rewritten.
- `output/proposed.diff` — a unified diff of the proposed changes, ready to
  eyeball or apply with `git apply` / `patch`.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running it

### Mock mode (no API key needed)

```bash
python -m docspilot.cli \
  --repo /path/to/some/repo \
  --base <sha-before> --head <sha-after> \
  --out ./output \
  --mock
```

`--mock` swaps the LLM call for a canned response, so you can see the full
pipeline (diff → signal extraction → doc shortlisting → report → proposed
rewrite) without an `ANTHROPIC_API_KEY`.

### Real mode (calls Claude)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m docspilot.cli \
  --repo /path/to/some/repo \
  --base <sha-before> --head <sha-after> \
  --out ./output
```

Then review the results:

```bash
cat ./output/report.md
diff /path/to/some/repo/README.md ./output/proposed/README.md
```

## Trying it against the bundled fixture

`tests/fixtures/sample_repo/{before,after}/` contains a tiny two-state
fixture: a `get_user` function that gets renamed to `fetch_user` (with a
signature change) while the README's `get_user` section is left untouched —
i.e. exactly the drift DocsPilot is meant to catch.

```bash
mkdir /tmp/dp_demo && cp -r tests/fixtures/sample_repo/before/* /tmp/dp_demo
cd /tmp/dp_demo && git init -q && git add -A && git commit -q -m before
BASE=$(git rev-parse HEAD)
cp -r ../tests/fixtures/sample_repo/after/* .   # adjust path as needed
git add -A && git commit -q -m after
HEAD=$(git rev-parse HEAD)
cd -

python -m docspilot.cli --repo /tmp/dp_demo --base $BASE --head $HEAD \
  --out /tmp/dp_demo_out --mock
cat /tmp/dp_demo_out/report.md
```

## Tests

```bash
pytest tests/
```

All tests run offline (the end-to-end test uses `--mock`); no API key is
required for the test suite.

## Layout

```
docspilot/
  cli.py            # argparse entry point
  git_diff.py        # git subprocess wrappers: changed files, diffs, hunks
  code_signals.py     # regex extraction of changed public symbols/flags
  docs_scanner.py     # markdown section splitting + symbol-overlap shortlisting
  llm_analyzer.py     # prompt construction + Anthropic call (+ --mock fixture)
  report.py           # renders report.md + writes proposed rewrites/diff

tests/
  fixtures/sample_repo/  # before/after snapshots used to build a temp git repo
  conftest.py             # builds the temp repo fixture from the snapshots
  test_git_diff.py
  test_docs_scanner.py
  test_cli_mock_e2e.py
```
