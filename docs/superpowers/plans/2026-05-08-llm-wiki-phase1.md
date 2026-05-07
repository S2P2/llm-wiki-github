# LLM Wiki Phase 1 — Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core compilation pipeline — feed a raw markdown doc through an LLM, produce structured wiki pages, and serve them via MkDocs — all running locally.

**Architecture:** Single-pass compilation. `compile.py` reads a raw doc, gathers context from existing wiki pages via ripgrep, calls an LLM (OpenAI-compatible endpoint), parses structured JSON output, validates it, and writes wiki pages + updates the index.

**Tech Stack:** Python 3.11+, uv, OpenAI/Anthropic SDKs, python-frontmatter, ripgrep (pre-installed), MkDocs + Material theme + roamlinks plugin, pytest.

---

## File Structure

```
llm_wiki/                     # Testable package — all compilation logic lives here
  __init__.py
  compile.py                  # parse, validate, gather, call_llm, apply, main
scripts/
  compile.py                  # Thin CLI wrapper: from llm_wiki.compile import main
tests/
  conftest.py                 # Shared fixtures (tmp wiki/raw dirs, sample docs, mock responses)
  test_parse.py               # parse_llm_response tests
  test_validate.py            # validate_pages tests
  test_context.py             # gather_context + extract_keyphrases tests
  test_llm.py                 # call_llm tests (mocked)
  test_apply.py               # apply_compilation tests
  test_compile.py             # Integration: main() dry-run + full-run
mkdocs.yml
AGENTS.md                     # System prompt loaded by compile.py
wiki/
  index.md                    # Contains <!-- COMPILE_INSERT_HERE --> marker
raw/
  manifest.csv                # Header only for Phase 1
  vector-databases.md         # Test document for E2E validation
pyproject.toml
.gitignore                    # Already exists
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `llm_wiki/__init__.py`
- Create: `llm_wiki/compile.py` (empty module)
- Create: `scripts/compile.py` (thin CLI wrapper)
- Create: `tests/conftest.py`
- Create: `wiki/`, `raw/` directories

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "llm-wiki"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.49.0",
    "openai>=1.75.0",
    "requests>=2.32.3",
    "trafilatura>=2.0.0",
    "python-frontmatter>=1.1.0",
    "mkdocs>=1.6.1",
    "mkdocs-material>=9.6.14",
    "mkdocs-roamlinks-plugin>=0.3.1",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.11.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Create directory structure and placeholder files**

```bash
mkdir -p llm_wiki scripts tests wiki raw
touch llm_wiki/__init__.py
```

Create `llm_wiki/compile.py` with module-level constants and imports that later tasks will build on:

```python
"""Wiki compilation engine — transforms raw documents into structured wiki pages."""

COMPILE_INSERT_MARKER = "<!-- COMPILE_INSERT_HERE -->"
```

Create `scripts/compile.py` (thin CLI wrapper):

```python
"""CLI entry point for wiki compilation."""

from llm_wiki.compile import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create tests/conftest.py with shared fixtures**

```python
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
```

- [ ] **Step 4: Install dependencies and verify**

Run: `uv sync`
Expected: dependencies installed, `uv.lock` created.

Run: `uv run pytest --co -q`
Expected: no tests collected yet, no errors.

Run: `uv run ruff check llm_wiki/ scripts/ tests/`
Expected: clean output (no errors).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock llm_wiki/ scripts/ tests/ wiki/ raw/
git commit -m "feat: project scaffolding with pyproject.toml and directory structure"
```

---

### Task 2: AGENTS.md System Prompt

**Files:**
- Create: `AGENTS.md`

This file is loaded by `compile.py` as the system prompt sent to the LLM. It defines the wiki compilation rules.

- [ ] **Step 1: Create AGENTS.md**

```markdown
# Wiki Compilation Rules

## Output Format
Always respond with a single valid JSON object matching this schema:
{
  "new_pages": [
    { "filename": "wiki/concept-name.md", "content": "frontmatter + body" }
  ],
  "updated_pages": [
    { "filename": "wiki/existing-page.md", "content": "complete updated content" }
  ],
  "index_patch": "- [[concept-name]] — one-line description"
}

Never return free-form markdown. Never wrap the JSON in backtick code fences.

## Link Format
Use [[kebab-case-filename]] for all internal wiki cross-references.
The filename must match an existing or newly created wiki page filename without the .md extension.
Use standard markdown links [text](url) for external URLs only.

Examples:
  ✅ [[machine-learning-basics]]
  ❌ [[Machine Learning Basics]]

## Page Frontmatter
Every page must include these fields: title, created, updated, sources, tags.
- title: Title Case human-readable string
- created / updated: ISO 8601 datetime (e.g. 2026-05-07T14:30:00Z)
- sources: list of /raw/ filenames that contributed to this page
- tags: list of lowercase hyphenated strings

## Naming Conventions
- Page filenames: kebab-case (e.g. machine-learning-basics.md)
- Page titles: Title Case (e.g. "Machine Learning Basics")
- Tags: lowercase, hyphenated (e.g. "neural-networks")

## Synthesis Rules
- Extract key claims, entities, and concepts from the new source
- Create new wiki pages for each distinct concept mentioned in the source
- Update existing pages when new source adds, contradicts, or refines existing content
- Note contradictions explicitly with a > ⚠️ Contradiction: blockquote
- Do not delete content from existing pages — only add or annotate
- Do not fabricate citations or sources not present in the provided raw document
- Use [[wikilinks]] generously to connect related concepts across pages
```

- [ ] **Step 2: Verify readability**

Run: `python -c "from pathlib import Path; print(Path('AGENTS.md').read_text()[:100])"`
Expected: prints the first 100 chars of the file.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "feat: add AGENTS.md system prompt for wiki compilation"
```

---

### Task 3: Response Parsing — `parse_llm_response`

**Files:**
- Create: `tests/test_parse.py`
- Modify: `llm_wiki/compile.py`

- [ ] **Step 1: Write tests for parse_llm_response**

Create `tests/test_parse.py`:

```python
import json

import pytest

from llm_wiki.compile import parse_llm_response


def test_parse_valid_json():
    raw = '{"new_pages": [], "updated_pages": [], "index_patch": ""}'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_in_code_fences():
    raw = '```json\n{"new_pages": [], "updated_pages": [], "index_patch": ""}\n```'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_in_unlabeled_code_fences():
    raw = '```\n{"new_pages": [], "updated_pages": [], "index_patch": ""}\n```'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_with_leading_trailing_whitespace():
    raw = '  \n  {"new_pages": [], "updated_pages": [], "index_patch": ""}  \n  '
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_response("this is not json")


def test_parse_invalid_json_in_fences_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_response("```json\nnot json\n```")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_parse.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_llm_response'`

- [ ] **Step 3: Implement parse_llm_response**

Add to `llm_wiki/compile.py`:

```python
import json
import re

COMPILE_INSERT_MARKER = "<!-- COMPILE_INSERT_HERE -->"


def parse_llm_response(raw: str) -> dict:
    """Parse LLM response, stripping markdown code fences if present."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_parse.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_parse.py llm_wiki/compile.py
git commit -m "feat: add parse_llm_response with code-fence sanitization"
```

---

### Task 4: Page Validation — `validate_pages`

**Files:**
- Create: `tests/test_validate.py`
- Modify: `llm_wiki/compile.py`

- [ ] **Step 1: Write tests for validate_pages**

Create `tests/test_validate.py`:

```python
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
    # Create an existing page to "update"
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_pages'`

- [ ] **Step 3: Implement validate_pages**

Add to `llm_wiki/compile.py` (after `parse_llm_response`):

```python
import re
from pathlib import Path

import frontmatter


REQUIRED_FRONTMATTER_FIELDS = ("title", "created", "updated", "sources")


def validate_pages(result: dict, wiki_dir: Path, raw_dir: Path) -> list[str]:
    """Validate compilation output. Returns list of error messages."""
    errors: list[str] = []

    for page_type in ("new_pages", "updated_pages"):
        for page in result.get(page_type, []):
            filename = page.get("filename", "")
            content = page.get("content", "")

            try:
                fm = frontmatter.loads(content)
            except Exception:
                errors.append(f"{filename}: invalid frontmatter")
                continue

            for field in REQUIRED_FRONTMATTER_FIELDS:
                if field not in fm.metadata:
                    errors.append(f"{filename}: missing required field '{field}'")

            for source in fm.metadata.get("sources", []):
                source_name = Path(source).name
                if not (raw_dir / source_name).exists():
                    errors.append(f"{filename}: source '{source}' not found in raw/")

            if page_type == "updated_pages":
                for link in re.findall(r"\[\[([^\]]+)\]\]", content):
                    target = wiki_dir / f"{link}.md"
                    if not target.exists():
                        errors.append(f"{filename}: broken wikilink [[{link}]]")

    return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_validate.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_validate.py llm_wiki/compile.py
git commit -m "feat: add validate_pages with frontmatter, source, and wikilink checks"
```

---

### Task 5: Context Gathering — `gather_context`

**Files:**
- Create: `tests/test_context.py`
- Modify: `llm_wiki/compile.py`

- [ ] **Step 1: Write tests for context gathering**

Create `tests/test_context.py`:

```python
from pathlib import Path

from llm_wiki.compile import extract_keyphrases, gather_context


def test_extract_keyphrases_from_title_and_body():
    text = "# Vector Databases and Embeddings\n\nVector databases store high-dimensional vectors for similarity search."
    phrases = extract_keyphrases(text)
    assert len(phrases) > 0
    assert all(isinstance(p, str) for p in phrases)


def test_extract_keyphrases_short_words_filtered():
    text = "# A Bit Of This And That\n\nThe end."
    phrases = extract_keyphrases(text)
    assert all(len(p) > 3 for p in phrases)


def test_gather_context_finds_relevant_pages(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "vector-search.md").write_text(
        "# Vector Search\n\nVector search uses approximate nearest neighbor algorithms.\n"
    )
    (wiki / "unrelated.md").write_text("# Cooking\n\nHow to bake bread.\n")

    raw_doc = tmp_path / "raw" / "new-vector-doc.md"
    raw_doc.parent.mkdir()
    raw_doc.write_text("# Vector Search Algorithms\n\nNew advances in vector search.\n")

    results = gather_context(raw_doc, wiki)
    filenames = [p.name for p in results]
    assert "vector-search.md" in filenames


def test_gather_context_returns_top_k(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    for i in range(10):
        (wiki / f"vector-page-{i}.md").write_text(
            f"# Vector Page {i}\n\nVector vector vector.\n"
        )

    raw_doc = tmp_path / "raw" / "new.md"
    raw_doc.parent.mkdir()
    raw_doc.write_text("# Vectors\n\nVector content.\n")

    results = gather_context(raw_doc, wiki, top_k=3)
    assert len(results) <= 3


def test_gather_context_empty_wiki(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    raw_doc = tmp_path / "raw" / "new.md"
    raw_doc.parent.mkdir()
    raw_doc.write_text("# Something New\n\nContent.\n")

    results = gather_context(raw_doc, wiki)
    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_context.py -v`
Expected: FAIL — `ImportError: cannot import name 'extract_keyphrases'`

- [ ] **Step 3: Implement extract_keyphrases and gather_context**

Add to `llm_wiki/compile.py` (after `validate_pages`):

```python
import subprocess


def extract_keyphrases(text: str, max_phrases: int = 5) -> list[str]:
    """Extract key search terms from title and first paragraph of a document."""
    lines = text.strip().split("\n")
    title = lines[0].lstrip("#").strip() if lines else ""

    words: set[str] = set()
    for line in [title] + lines[1:5]:
        for word in line.split():
            clean = word.strip(".,;:!?()[]{}\"'").lower()
            if len(clean) > 3:
                words.add(clean)

    return sorted(words, key=lambda w: (-len(w), w))[:max_phrases]


def gather_context(raw_doc: Path, wiki_dir: Path, top_k: int = 5) -> list[Path]:
    """Find relevant existing wiki pages using ripgrep."""
    keyphrases = extract_keyphrases(raw_doc.read_text())
    if not keyphrases or not wiki_dir.exists():
        return []

    pattern = "|".join(keyphrases)
    try:
        proc = subprocess.run(
            ["rg", "-l", "-c", pattern, str(wiki_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    matches: list[tuple[Path, int]] = []
    for line in proc.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.rsplit(":", 1)
        if len(parts) == 2:
            try:
                matches.append((Path(parts[0]), int(parts[1])))
            except ValueError:
                continue

    matches.sort(key=lambda x: x[1], reverse=True)
    return [path for path, _ in matches[:top_k]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_context.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_context.py llm_wiki/compile.py
git commit -m "feat: add context gathering via keyphrase extraction and ripgrep"
```

---

### Task 6: LLM Provider — `call_llm`

**Files:**
- Create: `tests/test_llm.py`
- Modify: `llm_wiki/compile.py`

- [ ] **Step 1: Write tests for call_llm (mocked)**

Create `tests/test_llm.py`:

```python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from llm_wiki.compile import call_llm


def test_call_llm_openai():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "ok"}'

    with (
        patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_MODEL": "test-model"}),
        patch("llm_wiki.compile.OpenAI") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value
        mock_client.chat.completions.create.return_value = mock_response

        result = call_llm("system prompt", "user content")

    assert result == '{"result": "ok"}'
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "test-model"
    assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}


def test_call_llm_anthropic():
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = {"result": "ok"}

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "test-model"}):
        with patch("llm_wiki.compile.anthropic") as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_client.messages.create.return_value = mock_response

            result = call_llm("system prompt", "user content")

    assert json.loads(result) == {"result": "ok"}


def test_call_llm_anthropic_no_tool_use_raises():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "I cannot comply"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_MODEL": "test-model"}):
        with patch("llm_wiki.compile.anthropic") as mock_anthropic:
            mock_client = mock_anthropic.Anthropic.return_value
            mock_client.messages.create.return_value = mock_response

            with pytest.raises(RuntimeError, match="No tool_use block"):
                call_llm("system prompt", "user content")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_llm.py -v`
Expected: FAIL — `ImportError: cannot import name 'call_llm'`

- [ ] **Step 3: Implement call_llm**

Add to `llm_wiki/compile.py` (after `gather_context`). First update the imports at the top of the file:

```python
import json
import os
import re
import subprocess
from pathlib import Path

import anthropic
import frontmatter
from openai import OpenAI
```

Then add the function:

```python
COMPILE_SCHEMA = {
    "type": "object",
    "properties": {
        "new_pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
        "updated_pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
        "index_patch": {"type": "string"},
    },
    "required": ["new_pages", "updated_pages", "index_patch"],
}

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")


def call_llm(system_prompt: str, user_content: str) -> str:
    """Call LLM and return raw text response."""
    max_tokens = int(os.environ.get("MAX_TOKENS", "16384"))

    if LLM_PROVIDER == "anthropic":
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=max_tokens,
            tools=[
                {
                    "name": "compile_wiki",
                    "description": "Compile wiki pages from raw source document",
                    "input_schema": COMPILE_SCHEMA,
                }
            ],
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            tool_choice={"type": "tool", "name": "compile_wiki"},
        )
        for block in response.content:
            if block.type == "tool_use":
                return json.dumps(block.input)
        raise RuntimeError("No tool_use block in Anthropic response")

    client = OpenAI(
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_llm.py -v`
Expected: 3 passed.

Also run all tests to check for regressions:
Run: `uv run pytest -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm.py llm_wiki/compile.py
git commit -m "feat: add call_llm with OpenAI and Anthropic provider support"
```

---

### Task 7: File Application — `apply_compilation`

**Files:**
- Create: `tests/test_apply.py`
- Modify: `llm_wiki/compile.py`

- [ ] **Step 1: Write tests for apply_compilation**

Create `tests/test_apply.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_apply.py -v`
Expected: FAIL — `ImportError: cannot import name 'apply_compilation'`

- [ ] **Step 3: Implement apply_compilation**

Add to `llm_wiki/compile.py` (after `call_llm`):

```python
def apply_compilation(result: dict, wiki_dir: Path, index_path: Path) -> None:
    """Write compiled pages to disk and update index.md with new entries."""
    for page_type in ("new_pages", "updated_pages"):
        for page in result.get(page_type, []):
            filename = Path(page["filename"]).name
            filepath = wiki_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(page["content"])

    patch = result.get("index_patch", "")
    if not patch:
        return

    content = index_path.read_text()
    content = content.replace(COMPILE_INSERT_MARKER, f"{patch}\n{COMPILE_INSERT_MARKER}")
    index_path.write_text(content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_apply.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_apply.py llm_wiki/compile.py
git commit -m "feat: add apply_compilation for writing wiki pages and updating index"
```

---

### Task 8: CLI Entry Point — `main()`

**Files:**
- Create: `tests/test_compile.py`
- Modify: `llm_wiki/compile.py`
- Modify: `scripts/compile.py` (already created, verify content)

- [ ] **Step 1: Write integration tests for main()**

Create `tests/test_compile.py`:

```python
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_compile.py -v`
Expected: FAIL — `ImportError` or `TypeError` (main doesn't accept arguments yet)

- [ ] **Step 3: Implement main()**

Add to `llm_wiki/compile.py`:

```python
def main(argv: list[str] | None = None, *, root: Path | None = None) -> None:
    """Compile raw documents into structured wiki pages."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Compile raw documents into wiki pages")
    parser.add_argument("files", nargs="+", help="Raw document paths to compile")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    project_root = root or Path.cwd()
    wiki_dir = project_root / "wiki"
    raw_dir = project_root / "raw"
    index_path = wiki_dir / "index.md"
    agents_path = project_root / "AGENTS.md"

    if not agents_path.exists():
        print(f"Error: {agents_path} not found", file=sys.stderr)
        sys.exit(1)

    system_prompt = agents_path.read_text()
    dry_run = os.environ.get("COMPILE_DRY_RUN", "").lower() == "true"

    for raw_file in args.files:
        raw_path = Path(raw_file)
        if not raw_path.exists():
            print(f"Error: {raw_path} not found", file=sys.stderr)
            sys.exit(1)

        context_pages = gather_context(raw_path, wiki_dir)
        context_content = ""
        if context_pages:
            parts = [f"--- Existing wiki page: {p.name} ---\n{p.read_text()}" for p in context_pages]
            context_content = "\n\n".join(parts)

        index_content = ""
        if index_path.exists():
            index_content = f"--- Current index.md ---\n{index_path.read_text()}"

        user_parts = [f"--- New source document ---\n{raw_path.read_text()}"]
        if context_content:
            user_parts.append(context_content)
        if index_content:
            user_parts.append(index_content)
        user_content = "\n\n".join(user_parts)

        raw_response = call_llm(system_prompt, user_content)
        result = parse_llm_response(raw_response)

        errors = validate_pages(result, wiki_dir, raw_dir)
        if errors:
            for error in errors:
                print(f"Validation error: {error}", file=sys.stderr)
            sys.exit(1)

        if dry_run:
            print(json.dumps(result, indent=2))
        else:
            apply_compilation(result, wiki_dir, index_path)
            print(f"Compiled {raw_path.name} → {len(result.get('new_pages', []))} new, "
                  f"{len(result.get('updated_pages', []))} updated pages", file=sys.stderr)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_compile.py -v`
Expected: 2 passed.

Run full suite:
Run: `uv run pytest -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compile.py llm_wiki/compile.py
git commit -m "feat: add main() CLI entry point with dry-run and full-run modes"
```

---

### Task 9: MkDocs Setup + Test Data

**Files:**
- Create: `mkdocs.yml`
- Create: `wiki/index.md`
- Create: `raw/manifest.csv`
- Create: `raw/vector-databases.md`

- [ ] **Step 1: Create mkdocs.yml**

```yaml
site_name: LLM Wiki
site_url: https://S2P2.github.io/llm-wiki-github/
theme:
  name: material
  features:
    - navigation.instant
    - search.highlight
plugins:
  - search
  - roamlinks
```

- [ ] **Step 2: Create wiki/index.md**

```markdown
# LLM Wiki

A compiled knowledge base.

## Pages

<!-- COMPILE_INSERT_HERE -->
```

- [ ] **Step 3: Create raw/manifest.csv and test document**

Create `raw/manifest.csv`:

```
url_normalized,url_sha256,content_sha256,date_ingested,pr_number,funnel
```

Create `raw/vector-databases.md`:

```markdown
# Understanding Vector Databases

Vector databases are specialized database systems designed to store and query
high-dimensional vectors. They power semantic search, recommendation systems,
and retrieval-augmented generation (RAG) pipelines.

## How Vector Embeddings Work

Text and other data are converted into numerical vectors using embedding models
like OpenAI's text-embedding-3-small or open-source alternatives like BGE. Each
vector captures semantic meaning in a high-dimensional space (typically 384 to
3072 dimensions).

## Approximate Nearest Neighbor Search

Vector databases use approximate nearest neighbor (ANN) algorithms to quickly
find similar vectors without comparing against every entry. Popular ANN
approaches include:

- **HNSW (Hierarchical Navigable Small World):** Used by Milvus, Weaviate, and
  Qdrant. Provides excellent recall with moderate memory usage.
- **IVF (Inverted File Index):** Partitions vectors into clusters, reducing
  search scope. Used in FAISS.
- **Product Quantization:** Compresses vectors for memory-efficient storage at
  the cost of some accuracy.

## Popular Vector Database Systems

- **Milvus:** Open-source, supports multiple index types, designed for
  billion-scale datasets.
- **Qdrant:** Rust-based, offers filtering with vector search, lightweight
  deployment.
- **Weaviate:** Includes built-in modules for vectorization and generative
  search.
- **ChromaDB:** Lightweight, designed for AI application development.
- **Pinecone:** Fully managed service with automatic scaling.

## When to Use Vector Search vs. Traditional Search

Vector search excels at semantic similarity — finding content that *means*
similar things even without matching keywords. Traditional keyword search
(BM25, TF-IDF) remains better for exact term matching. Many production systems
use hybrid approaches combining both methods.

## Integration with LLMs

Vector databases serve as the retrieval backbone in RAG architectures. The
workflow: user query → embedding → vector search → top-k results → injected
into LLM context → generated response. This grounds LLM outputs in specific,
retrieved knowledge rather than relying solely on training data.
```

- [ ] **Step 4: Verify MkDocs can build**

Run: `uv run mkdocs build`
Expected: site/ directory created, no errors.

Run: `uv run mkdocs serve &` (optional, to preview in browser)
Expected: site served at http://127.0.0.1:8000

- [ ] **Step 5: Commit**

```bash
git add mkdocs.yml wiki/index.md raw/manifest.csv raw/vector-databases.md
git commit -m "feat: add MkDocs config, wiki index, and test document"
```

---

### Task 10: End-to-End Dry Run

**Files:** None (validation only)

This task validates the entire pipeline locally. It requires a running OpenAI-compatible endpoint (e.g. Ollama, LiteLLM).

- [ ] **Step 1: Run dry-run compilation against test document**

```bash
COMPILE_DRY_RUN=true \
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
uv run python scripts/compile.py raw/vector-databases.md
```

Expected: JSON printed to stdout with `new_pages`, `updated_pages`, and `index_patch`. Structure should match the output contract from AGENTS.md.

- [ ] **Step 2: Review the JSON output**

Verify:
- Each new page has valid frontmatter (title, created, updated, sources, tags)
- Wikilinks use `[[kebab-case-filename]]` format
- `index_patch` contains one line per new page with `[[name]] — description` format
- No fabricated sources — `sources` should only reference `raw/vector-databases.md`

- [ ] **Step 3: Run full compilation**

```bash
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
uv run python scripts/compile.py raw/vector-databases.md
```

Expected: wiki pages created in `wiki/`, index.md updated with new entries.

- [ ] **Step 4: Verify output and build site**

```bash
ls wiki/
cat wiki/index.md
uv run mkdocs build
```

Expected:
- New wiki pages exist (e.g. `vector-databases.md`, `embeddings.md`, `ann-algorithms.md`)
- `index.md` lists new pages above the compile marker
- `mkdocs build` succeeds with no errors

- [ ] **Step 5: Final lint check and commit**

```bash
uv run ruff check llm_wiki/ scripts/ tests/
uv run pytest -v
```

Expected: all checks pass.

If the compilation produced wiki files, commit them:
```bash
git add wiki/
git commit -m "chore(compile): add compiled wiki pages from test document"
```

---

## Phase 1 Definition of Done

- [ ] All tests pass (`uv run pytest -v`)
- [ ] Code is clean (`uv run ruff check llm_wiki/ scripts/ tests/`)
- [ ] Dry run produces valid JSON matching the output contract
- [ ] Full run creates wiki pages and updates index.md
- [ ] `mkdocs build` succeeds
- [ ] `mkdocs serve` shows the compiled wiki in a browser
