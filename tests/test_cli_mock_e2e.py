from docspilot.cli import main


def test_cli_mock_e2e_flags_stale_section_and_writes_rewrite(sample_repo, tmp_path):
    repo, base, head = sample_repo
    out_dir = tmp_path / "output"

    exit_code = main(
        [
            "--repo",
            repo,
            "--base",
            base,
            "--head",
            head,
            "--out",
            str(out_dir),
            "--mock",
        ]
    )

    assert exit_code == 0

    report_text = (out_dir / "report.md").read_text()
    assert "get_user" in report_text
    assert "README.md" in report_text

    proposed_readme = (out_dir / "proposed" / "README.md").read_text()
    assert "This section has been updated" in proposed_readme
    # Sections that weren't flagged as stale should survive untouched.
    assert "## Installation" in proposed_readme
    assert "pip install -e ." in proposed_readme

    diff_text = (out_dir / "proposed.diff").read_text()
    assert "a/README.md" in diff_text
    assert "b/README.md" in diff_text


def test_cli_mock_e2e_no_findings_when_symbols_unchanged(tmp_path):
    import subprocess

    repo = tmp_path / "static_repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "T"], check=True)

    (repo / "README.md").write_text("# Static\n\nNothing to see here.\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    (repo / "notes.txt").write_text("just a plain text change\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "unrelated change"], check=True)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    out_dir = tmp_path / "output"
    exit_code = main(
        [
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--out",
            str(out_dir),
            "--mock",
        ]
    )

    assert exit_code == 0
    report_text = (out_dir / "report.md").read_text()
    assert "No stale documentation sections detected" in report_text
