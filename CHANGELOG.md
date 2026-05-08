# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-08

### Added

- Compilation engine (`llm_wiki/compile.py`) with parse, validate, context gathering, LLM calls, and file application
- `parse_llm_response` — strips code fences and parses JSON from LLM output
- `validate_pages` — checks frontmatter fields, source file references, and wikilink integrity
- `gather_context` — finds relevant existing wiki pages via keyphrase extraction (ripgrep with Python fallback)
- `call_llm` — provider-agnostic LLM calls supporting OpenAI-compatible endpoints and Anthropic
- `apply_compilation` — writes wiki pages to disk and updates index with new entries
- `main()` CLI with dry-run and full-run modes
- `AGENTS.md` system prompt defining wiki compilation rules for the LLM
- MkDocs site with Material theme and roamlinks plugin (`docs_dir: wiki`)
- `wiki/index.md` with `<!-- COMPILE_INSERT_HERE -->` compile marker
- `raw/manifest.csv` header for source deduplication
- `raw/vector-databases.md` test document
- 25 tests covering all compilation components
- `pyproject.toml` with `uv` package management
- UTF-8 encoding on all file I/O for Windows compatibility
