from pathlib import Path

from llm_wiki.compile import validate_pages


def test_valid_pages_pass(raw_dir: Path, wiki_dir: Path, valid_result: dict):
    errors = validate_pages(valid_result, wiki_dir, raw_dir)
    assert errors == []


def test_missing_frontmatter_field(raw_dir: Path, wiki_dir: Path):
    result = {
        "new_pages": [
            {
                "filename": "wiki/bad.md",
                "content": "---\ntitle: Bad\n---\nNo created/updated/sources fields.",
            }
        ],
        "updated_pages": [],
        "index_patch": "",
    }
    errors = validate_pages(result, wiki_dir, raw_dir)
    assert any("created" in e for e in errors)
    assert any("updated" in e for e in errors)
    assert any("sources" in e for e in errors)


def test_missing_source_file(wiki_dir: Path, raw_dir: Path):
    result = {
        "new_pages": [
            {
                "filename": "wiki/orphan.md",
                "content": (
                    "---\n"
                    "title: Orphan\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/nonexistent.md\n"
                    "tags: []\n"
                    "---\n\nNo real source.\n"
                ),
            }
        ],
        "updated_pages": [],
        "index_patch": "",
    }
    errors = validate_pages(result, wiki_dir, raw_dir)
    assert any("nonexistent" in e for e in errors)


def test_broken_wikilink_in_updated_page(wiki_dir: Path, raw_dir: Path):
    existing = wiki_dir / "existing-page.md"
    existing.write_text("---\ntitle: Existing\n---\nContent.\n")

    result = {
        "new_pages": [],
        "updated_pages": [
            {
                "filename": "wiki/existing-page.md",
                "content": (
                    "---\n"
                    "title: Existing\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/vector-databases.md\n"
                    "tags: []\n"
                    "---\n\nSee [[nonexistent-page]].\n"
                ),
            }
        ],
        "index_patch": "",
    }
    errors = validate_pages(result, wiki_dir, raw_dir)
    assert any("nonexistent-page" in e for e in errors)


def test_new_page_wikilinks_not_checked_against_existing(wiki_dir: Path, raw_dir: Path):
    """New pages may link to each other — wikilinks are only validated for updated_pages."""
    result = {
        "new_pages": [
            {
                "filename": "wiki/page-a.md",
                "content": (
                    "---\n"
                    "title: Page A\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/vector-databases.md\n"
                    "tags: []\n"
                    "---\n\nSee [[page-b]].\n"
                ),
            },
            {
                "filename": "wiki/page-b.md",
                "content": (
                    "---\n"
                    "title: Page B\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/vector-databases.md\n"
                    "tags: []\n"
                    "---\n\nSee [[page-a]].\n"
                ),
            },
        ],
        "updated_pages": [],
        "index_patch": "",
    }
    errors = validate_pages(result, wiki_dir, raw_dir)
    assert errors == []
