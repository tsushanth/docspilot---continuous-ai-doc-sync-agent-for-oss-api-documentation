from docspilot.docs_scanner import load_docs, shortlist_candidates, split_sections


def test_split_sections_splits_by_heading():
    text = (
        "# Title\n"
        "\n"
        "intro text\n"
        "\n"
        "## get_user\n"
        "\n"
        "Call get_user(user_id).\n"
        "\n"
        "## Installation\n"
        "\n"
        "pip install -e .\n"
    )

    sections = split_sections("README.md", text)

    headings = [s.heading for s in sections]
    assert headings == ["Title", "get_user", "Installation"]

    get_user_section = next(s for s in sections if s.heading == "get_user")
    assert "Call get_user(user_id)." in get_user_section.text
    assert get_user_section.level == 2


def test_shortlist_candidates_matches_changed_symbol(sample_repo):
    repo, _base, _head = sample_repo

    docs = load_docs(repo)
    candidates = shortlist_candidates(docs, {"get_user"})

    assert len(candidates) == 1
    assert candidates[0].doc_path == "README.md"
    assert candidates[0].heading == "get_user"


def test_shortlist_candidates_empty_when_no_overlap(sample_repo):
    repo, _base, _head = sample_repo

    docs = load_docs(repo)
    candidates = shortlist_candidates(docs, {"totally_unrelated_symbol"})

    assert candidates == []
