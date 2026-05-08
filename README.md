# LLM Wiki

A compiled knowledge base powered by LLMs. Feed raw documents in, get structured, interlinked wiki pages out — served as a static site via GitHub Pages.

## How It Works

LLM Wiki uses a **compilation paradigm** instead of traditional RAG:

1. **Ingest** — Add source documents to `raw/` (manually or via GitHub Issues)
2. **Compile** — `compile.py` sends the document + existing wiki context to an LLM
3. **Validate** — Output is checked for valid frontmatter, source references, and wikilinks
4. **Serve** — MkDocs builds a searchable static site from the compiled wiki pages

All infrastructure is GitHub-native: repositories for storage, Actions for compute, Pages for hosting.

## Quick Start

```bash
# Install dependencies
uv sync

# Dry run — prints compiled output without writing files
COMPILE_DRY_RUN=true \
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:8000/v1 \
OPENAI_API_KEY=local \
OPENAI_MODEL=your-model \
uv run python scripts/compile.py raw/your-document.md

# Full run — writes wiki pages and updates the index
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:8000/v1 \
OPENAI_API_KEY=local \
OPENAI_MODEL=your-model \
uv run python scripts/compile.py raw/your-document.md

# Preview the site
uv run mkdocs serve
```

## Project Structure

```
llm_wiki/compile.py     # Compilation engine (parse, validate, gather, call_llm, apply)
scripts/compile.py      # CLI entry point
raw/                    # Source documents (append-only)
wiki/                   # Compiled wiki pages (LLM-owned)
mkdocs.yml              # MkDocs configuration
AGENTS.md               # System prompt loaded by compile.py
```

## LLM Providers

Controlled by the `LLM_PROVIDER` environment variable:

| Provider | Env Var | Use Case |
|---|---|---|
| `openai` (default) | `OPENAI_API_KEY` | OpenAI API or any compatible endpoint |
| `anthropic` | `ANTHROPIC_API_KEY` | Anthropic API |

Any OpenAI-compatible endpoint (Ollama, LiteLLM, LM Studio) works by setting `OPENAI_BASE_URL`.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No | `openai` (default) or `anthropic` |
| `OPENAI_API_KEY` | If `openai` | API key (any string for local endpoints) |
| `OPENAI_BASE_URL` | No | Override endpoint (e.g. `http://localhost:11434/v1`) |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o`) |
| `ANTHROPIC_API_KEY` | If `anthropic` | Anthropic API key |
| `MAX_TOKENS` | No | Output token limit (default: `16384`) |
| `COMPILE_DRY_RUN` | No | `true` = print output without writing files |

## Development

```bash
uv sync                # install deps
uv run pytest -v       # run tests (25 tests)
uv run ruff check .    # lint
uv run mkdocs build    # build site
```

## License

MIT
