from pathlib import Path

import pytest

from llm_wiki.compile import COMPILE_INSERT_MARKER


@pytest.fixture
def wiki_dir(tmp_path: Path) -> Path:
    """Temporary wiki/ directory with index.md containing the compile marker."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    index = wiki / "index.md"
    index.write_text(
        "# Wiki Index\n\n## Pages\n\n" + COMPILE_INSERT_MARKER + "\n"
    )
    return wiki


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Temporary raw/ directory with a sample source file."""
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "vector-databases.md"
    source.write_text("# Understanding Vector Databases\n\nContent about vector databases.\n")
    return raw


@pytest.fixture
def index_path(wiki_dir: Path) -> Path:
    """Path to wiki/index.md."""
    return wiki_dir / "index.md"


@pytest.fixture
def valid_result() -> dict:
    """Valid LLM compilation output matching the output contract."""
    return {
        "new_pages": [
            {
                "filename": "wiki/vector-databases.md",
                "content": (
                    "---\n"
                    "title: Vector Databases\n"
                    "created: 2026-05-07T14:30:00Z\n"
                    "updated: 2026-05-07T14:30:00Z\n"
                    "sources:\n"
                    "  - raw/vector-databases.md\n"
                    "tags: [databases, vector-search]\n"
                    "---\n"
                    "\n"
                    "# Vector Databases\n"
                    "\n"
                    "Vector databases store and query high-dimensional vectors.\n"
                    "\n"
                    "See also: [[embeddings]]\n"
                ),
            },
            {
                "filename": "wiki/embeddings.md",
                "content": (
                    "---\n"
                    "title: Embeddings\n"
                    "created: 2026-05-07T14:30:00Z\n"
                    "updated: 2026-05-07T14:30:00Z\n"
                    "sources:\n"
                    "  - raw/vector-databases.md\n"
                    "tags: [embeddings, machine-learning]\n"
                    "---\n"
                    "\n"
                    "# Embeddings\n"
                    "\n"
                    "Embeddings convert data into numerical vectors.\n"
                    "\n"
                    "See also: [[vector-databases]]\n"
                ),
            },
        ],
        "updated_pages": [],
        "index_patch": "- [[vector-databases]] — Specialized databases for vector storage and similarity search\n- [[embeddings]] — Numerical vector representations of data",
    }
