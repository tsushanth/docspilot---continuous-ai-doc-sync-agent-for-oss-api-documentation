from docspilot.git_diff import changed_files, file_hunks, unified_diff


def test_changed_files_reports_modified_paths(sample_repo):
    repo, base, head = sample_repo

    files = changed_files(repo, base, head)

    assert ("M", "api.py") in files
    assert "README.md" not in [path for _, path in files]


def test_unified_diff_contains_renamed_function(sample_repo):
    repo, base, head = sample_repo

    diff_text = unified_diff(repo, base, head)

    assert "-def get_user(user_id):" in diff_text
    assert "+def fetch_user(user_id, include_deleted=False):" in diff_text


def test_file_hunks_splits_by_file(sample_repo):
    repo, base, head = sample_repo

    hunks = file_hunks(repo, base, head)

    assert len(hunks) == 1
    assert hunks[0].path == "api.py"
    assert hunks[0].status == "M"
    assert "fetch_user" in hunks[0].hunk
