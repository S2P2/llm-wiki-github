from pathlib import Path

from llm_wiki.compile import COMPILE_INSERT_MARKER, apply_compilation


def test_creates_new_pages(wiki_dir: Path, index_path: Path, valid_result: dict):
    apply_compilation(valid_result, wiki_dir, index_path)

    assert (wiki_dir / "vector-databases.md").exists()
    assert (wiki_dir / "embeddings.md").exists()
    content = (wiki_dir / "vector-databases.md").read_text()
    assert "Vector Databases" in content


def test_updates_existing_pages(wiki_dir: Path, index_path: Path):
    existing = wiki_dir / "existing-page.md"
    existing.write_text("---\ntitle: Old\n---\nOld content.\n")

    result = {
        "new_pages": [],
        "updated_pages": [
            {
                "filename": "wiki/existing-page.md",
                "content": "---\ntitle: Updated\n---\nNew content.\n",
            }
        ],
        "index_patch": "",
    }
    apply_compilation(result, wiki_dir, index_path)

    assert "New content." in existing.read_text()


def test_applies_index_patch(wiki_dir: Path, index_path: Path, valid_result: dict):
    apply_compilation(valid_result, wiki_dir, index_path)

    index_content = index_path.read_text()
    assert "[[vector-databases]]" in index_content
    assert "[[embeddings]]" in index_content
    # Marker should still exist
    assert COMPILE_INSERT_MARKER in index_content
    # Patch should be ABOVE the marker
    marker_pos = index_content.index(COMPILE_INSERT_MARKER)
    patch_pos = index_content.index("[[vector-databases]]")
    assert patch_pos < marker_pos


def test_empty_patch_leaves_index_unchanged(wiki_dir: Path, index_path: Path):
    original = index_path.read_text()

    result = {
        "new_pages": [],
        "updated_pages": [],
        "index_patch": "",
    }
    apply_compilation(result, wiki_dir, index_path)

    assert index_path.read_text() == original
