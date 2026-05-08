import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_wiki.compile import COMPILE_INSERT_MARKER


def test_dry_run_prints_json_no_files_written(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index\n\n" + COMPILE_INSERT_MARKER + "\n")

    raw = tmp_path / "raw"
    raw.mkdir()
    test_doc = raw / "test.md"
    test_doc.write_text("# Test Document\n\nSome content about testing.\n")

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("You are a wiki compiler.\n")

    mock_response = json.dumps({
        "new_pages": [
            {
                "filename": "wiki/test-document.md",
                "content": (
                    "---\n"
                    "title: Test Document\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/test.md\n"
                    "tags: [test]\n"
                    "---\n\n# Test Document\n\nCompiled content.\n"
                ),
            }
        ],
        "updated_pages": [],
        "index_patch": "- [[test-document]] — A test page",
    })

    with (
        patch.dict(os.environ, {"COMPILE_DRY_RUN": "true"}),
        patch("llm_wiki.compile.call_llm", return_value=mock_response),
    ):
        from llm_wiki.compile import main
        main([str(test_doc)], root=tmp_path)

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "new_pages" in output
    assert len(output["new_pages"]) == 1

    # Verify no files were written
    assert not (wiki / "test-document.md").exists()


def test_full_run_writes_files(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Index\n\n" + COMPILE_INSERT_MARKER + "\n")

    raw = tmp_path / "raw"
    raw.mkdir()
    test_doc = raw / "test.md"
    test_doc.write_text("# Test Document\n\nSome content about testing.\n")

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("You are a wiki compiler.\n")

    mock_response = json.dumps({
        "new_pages": [
            {
                "filename": "wiki/test-document.md",
                "content": (
                    "---\n"
                    "title: Test Document\n"
                    "created: 2026-05-07T00:00:00Z\n"
                    "updated: 2026-05-07T00:00:00Z\n"
                    "sources:\n"
                    "  - raw/test.md\n"
                    "tags: [test]\n"
                    "---\n\n# Test Document\n\nCompiled content.\n"
                ),
            }
        ],
        "updated_pages": [],
        "index_patch": "- [[test-document]] — A test page",
    })

    with (
        patch.dict(os.environ, {"COMPILE_DRY_RUN": ""}),
        patch("llm_wiki.compile.call_llm", return_value=mock_response),
    ):
        from llm_wiki.compile import main
        main([str(test_doc)], root=tmp_path)

    assert (wiki / "test-document.md").exists()
    assert "Compiled content." in (wiki / "test-document.md").read_text()
    assert "[[test-document]]" in (wiki / "index.md").read_text()
