# LLM Wiki — Implementation Design

**Date:** 2026-05-07
**Spec:** v4.0 (`spec/llm-wiki-spec-v4.md`)
**Approach:** Vertical slice — validate core compilation paradigm first

---

## Implementation Phases

1. **Core loop** — `compile.py` + `AGENTS.md` + MkDocs + one test doc. Run locally end-to-end.
2. **Template polish** — configurable defaults, `.env.example`, setup docs, clean repo template.
3. **Full MVP** — Funnel B (Issues scraper), lint action, GitHub Actions workflows.

---

## Project Structure

```
/
├── .github/
│   ├── ISSUE_TEMPLATE/new-source.yml      # Phase 3
│   ├── PULL_REQUEST_TEMPLATE.md           # Phase 2
│   └── workflows/
│       ├── compile.yml                    # Phase 2 (after scripts work locally)
│       ├── ingest-issue.yml               # Phase 3
│       └── lint-wiki.yml                 # Phase 3
├── raw/
│   └── manifest.csv
├── wiki/
│   └── index.md
├── scripts/
│   ├── compile.py                         # Phase 1
│   ├── scrape.py                          # Phase 3
│   └── lint.py                            # Phase 3
├── mkdocs.yml
├── pyproject.toml
├── uv.lock
├── requirements.txt                       # generated
├── AGENTS.md                              # system prompt for all AI harnesses
└── .gitignore
```

**Tooling:** `uv` (deps), `ruff` (lint/format), `ty` (types), `prek` (git hooks).

---

## Compilation Engine (`compile.py`)

### Flow

1. **Input** — path to a new raw doc (e.g. `raw/my-new-doc.md`)
2. **Context gathering** — extract keyphrases from title + first paragraph, ripgrep `/wiki/` for top-5 relevant pages
3. **LLM call** — system prompt (from `AGENTS.md`) + new doc + relevant wiki context + current `index.md`
4. **Parse response** — sanitize (strip code fences) + `json.loads()`
5. **Validate** — frontmatter, wikilinks, sources references
6. **Write** — create/update wiki files, insert `index_patch` above `<!-- COMPILE_INSERT_HERE -->`
7. **Commit** — `chore(compile): {sha}` (or stdout in dry-run mode)

### Provider Abstraction

Controlled by `LLM_PROVIDER` env var:

| Value | Backend | Requires |
|---|---|---|
| `anthropic` | Anthropic API | `ANTHROPIC_API_KEY` |
| `openai` (default) | OpenAI or compatible endpoint | `OPENAI_API_KEY`, optional `OPENAI_BASE_URL` |

OpenAI-compatible endpoints (Ollama, LiteLLM, LM Studio) work by setting `OPENAI_BASE_URL`. No separate provider needed.

### Structured Output

- **OpenAI / compatible:** `response_format: { type: "json_object" }`
- **Anthropic:** tool use with JSON schema
- **Fallback:** sanitize raw response (strip code fences) before `json.loads()`

### Key Parameters

- `max_tokens` defaults to 16384, configurable via `MAX_TOKENS`
- `COMPILE_DRY_RUN=true` prints output without writing files
- Chunking for docs >80K tokens (split by `# ` headings, process sequentially)

### Error Handling

| Failure | Behavior |
|---|---|
| LLM API timeout/error | Script exits non-zero; raw doc unchanged |
| Invalid JSON after sanitization | Exit with raw response logged |
| `max_tokens` truncation | Caught by `json.loads()`; exit cleanly |
| Validation failure | Exit before any write |

---

## MkDocs Site

```yaml
# mkdocs.yml
site_name: LLM Wiki
site_url: https://{username}.github.io/{repo}/
theme:
  name: material
  features:
    - navigation.instant
    - search.highlight
plugins:
  - search
  - roamlinks
```

`wiki/index.md` contains `<!-- COMPILE_INSERT_HERE -->` marker. Compilation inserts new entries above it.

**Deployment:** GitHub Pages via `actions/deploy-pages`. One-time setup: Settings → Pages → Source = "GitHub Actions".

---

## Data Formats

### `raw/manifest.csv`

```
url_normalized,url_sha256,content_sha256,date_ingested,pr_number,funnel
```

- URL normalization: strip query params, UTM params, trailing slashes
- `url_sha256` is the dedup key
- `date_ingested` is ISO 8601 datetime

### Wiki Page Frontmatter

```yaml
---
title: "Human-Readable Title"
created: 2026-05-07T14:30:00Z
updated: 2026-05-07T14:30:00Z
sources:
  - raw/filename.md
tags: [lowercase, hyphenated]
---
```

All fields required. `created` and `updated` are ISO 8601 datetime. `sources` must reference existing `/raw/` files.

### Wikilinks

`[[kebab-case-filename]]` — matches filename without `.md`. No title-case. External URLs use standard markdown.

### LLM Output Contract

```json
{
  "new_pages": [
    { "filename": "wiki/concept-name.md", "content": "---\ntitle: ...\n---\n..." }
  ],
  "updated_pages": [
    { "filename": "wiki/existing-page.md", "content": "..." }
  ],
  "index_patch": "- [[concept-name]] — one-line description"
}
```

### Branch & Commit Conventions

| Context | Format |
|---|---|
| Funnel A (manual) | `ingest/manual-{slug}` |
| Funnel B (Issues) | `ingest/issue-{issue_number}` |
| Compile commit | `chore(compile): {sha}` |

Compile commit format enables targeted `git revert` and prevents infinite Actions loop.

---

## GitHub Actions (Phase 2-3)

### `compile.yml`

- Trigger: push to `main` with changes in `raw/**`
- Condition: `if: "!startsWith(github.event.head_commit.message, 'chore(compile):')"`
- Concurrency: `compile-wiki` group, `cancel-in-progress: false`
- Steps: checkout → uv setup → install deps → `compile.py` → commit → `mkdocs build` → deploy Pages
- Permissions: `contents: write`, `pages: write`, `id-token: write`
- All actions pinned to SHA hashes

### `ingest-issue.yml` (Phase 3)

- Trigger: `issues: opened` with `new-source` label
- Runs `scrape.py` (Jina Reader with Trafilatura fallback)
- Content validation: HTTP status → error keywords → min content size
- Updates `manifest.csv`, opens PR via `peter-evans/create-pull-request`
- Closes originating issue

### `lint-wiki.yml` (Phase 3)

- Configurable cron + manual dispatch
- Checks: broken wikilinks, orphans, missing frontmatter, stale sources, index drift
- Reports to `$GITHUB_STEP_SUMMARY` always, creates `wiki-health` issue only on problems

---

## Local Testing

All scripts run standalone with env vars. No CI dependency.

```bash
# Dry run — prints to stdout, writes nothing
COMPILE_DRY_RUN=true \
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
python scripts/compile.py raw/my-test-doc.md

# Full run
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
python scripts/compile.py raw/my-test-doc.md

# Preview site
mkdocs serve

# Run lint
python scripts/lint.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No | `anthropic` or `openai` (default) |
| `ANTHROPIC_API_KEY` | If `anthropic` | Anthropic API key |
| `OPENAI_API_KEY` | If `openai` | OpenAI or compatible API key |
| `OPENAI_BASE_URL` | No | Override endpoint (e.g. Ollama at `http://localhost:11434/v1`) |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o`) |
| `MAX_TOKENS` | No | Output token limit (default: `16384`) |
| `JINA_API_KEY` | No | Jina Reader key; unset = Trafilatura fallback |
| `MIN_CONTENT_BYTES` | No | Min scraped content size (default: `500`) |
| `COMPILE_DRY_RUN` | No | `true` = print output without writing |
| `REQUIRE_PR_APPROVAL` | No | Branch protection mode (default: `true`) |

---

## Rollback

- Every compile commit: `chore(compile): {sha}` — trivially identifiable in `git log`
- Revert: `git revert <sha>` — restores wiki pages without touching `/raw/`
- Bad source identified by SHA in commit message, removable via new PR
