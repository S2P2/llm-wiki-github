# Architecture Specification: GitHub-Native LLM Wiki
**Version:** 4.0
**Design Paradigm:** Compilation over Retrieval (Stateless RAG Alternative)
**Infrastructure:** 100% GitHub-Native (Serverless)
**Stage:** MVP / Proof of Concept

---

## Changelog: v3 → v4

| # | Change | Section |
|---|---|---|
| O1 | Local LLM inference via Ollama added; `LLM_PROVIDER` abstraction in `compile.py`; Ollama merged into `openai` provider via `OPENAI_BASE_URL` | §0, §6, §9 |
| O2 | Jina Reader pricing documented; Trafilatura added as free local fallback scraper | §5 |
| O3 | `uv` replaces `pip` as package manager in all workflows and local setup | §6, §9 |
| O4 | `pyproject.toml` + `uv.lock` added as project standard; `requirements.txt` becomes generated export | §2, §9 |
| O5 | `requirements.txt` example updated with `openai`, `ollama`, `trafilatura` | §9 |

---

## Changelog: v2 → v3

| # | Change | Section |
|---|---|---|
| R1 | LLM JSON output: structured output API + sanitization fallback + `max_tokens` guard | §6 |
| N1 | Infinite Actions loop prevention via commit message condition | §6 |
| N2 | `REQUIRE_PR_APPROVAL` repo variable; human review recommended; AI review noted post-MVP | §4 |
| N3 | `[[wikilinks]]` corrected to kebab-case filename, not page title | §3, §11 |
| N4 | `manifest.csv` URL normalization + SHA256 field clarification | §2 |
| N5 | Ripgrep relevance strategy made explicit | §6 |
| N6 | `index_patch` application defined via `<!-- COMPILE_INSERT_HERE -->` marker | §6 |
| N7 | Funnel B content validation replaced with layered flexible approach | §5 |
| N8 | Lint frequency configurable; reporting via `$GITHUB_STEP_SUMMARY` + conditional Issue | §7 |
| N9 | `requirements.txt` added to directory structure and §9 | §2, §9 |
| L1 | Python confirmed as primary stack; TypeScript noted in appendix | §9, Appendix |

---

## 0. MVP Scope Boundary

This section defines what is in and out of scope for v1. Planning and task breakdown should not exceed this boundary.

| Feature | MVP (v1) | Post-MVP |
|---|---|---|
| Funnel A — Manual local push | ✅ | |
| Funnel B — GitHub Issues scraper | ✅ | |
| Funnel C — Autonomous AI agent | ❌ | v2 |
| Compilation engine (Actions) | ✅ | |
| Static site — MkDocs + Material | ✅ | |
| Graph visualization | ❌ | v2 (Quartz) |
| Client-side search | ✅ (MkDocs built-in) | |
| Wiki lint / health action | ✅ | |
| Local LLM via Ollama (local dev, GPU) | ✅ via `openai` provider + `OPENAI_BASE_URL` | |
| Local LLM via Ollama (Actions, CPU-only) | ✅ slow — small models only | |
| Local LLM via Ollama (Actions, GPU) | ❌ | v2 (self-hosted runner) |
| AI-assisted PR review | ❌ | v2 |
| Multi-repo support | ❌ | v3 |
| Private GitHub Pages (auth) | ❌ | v2 |
| Funnel C cost guard | ❌ | v2 |

**SSG Decision:** MkDocs + Material theme. Quartz noted as future upgrade for graph visualization.
**Search Decision:** Ripgrep for local file search in compilation scripts. `qmd` noted as future upgrade for hybrid BM25/vector search at scale.
**Language Decision:** Python 3.11+. TypeScript noted as a valid alternative in Appendix.
**Package Manager Decision:** `uv` for all environments. Faster installs, better caching, `uv.lock` for reproducibility.
**LLM Provider Decision:** Provider-agnostic via `LLM_PROVIDER` env var. Supports `anthropic` and `openai`. Ollama is covered by the `openai` provider via `OPENAI_BASE_URL` — no separate provider needed.

---

## 1. Executive Summary

This document outlines the technical specification for implementing the "LLM Wiki" architecture entirely within the GitHub ecosystem. Bypassing traditional, stateless RAG (Retrieval-Augmented Generation) architectures that rely on external vector databases, this system uses a **Compilation Paradigm**. All knowledge is stored as dense, interlinked Markdown files.

GitHub serves as the complete infrastructure stack: Repositories act as the database, GitHub Actions replace compute servers, Pull Requests handle multi-agent coordination and human-in-the-loop validation, and GitHub Pages hosts the frontend.

---

## 2. Structural Layer (Repository File System)

The repository acts as the immutable ground truth, enforcing a strict unidirectional flow of data.

```
/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── new-source.yml          # Structured form for Funnel B submissions
│   ├── PULL_REQUEST_TEMPLATE.md    # Standard PR body for all ingest funnels
│   └── workflows/
│       ├── ingest-issue.yml        # Funnel B: triggered on issues: opened
│       ├── compile.yml             # Compilation engine: triggered on push to main /raw/**
│       └── lint-wiki.yml           # Configurable wiki health check
│
├── raw/                            # Append-only source of truth
│   └── manifest.csv               # Deduplication registry (see schema below)
│
├── wiki/                           # Compiled substrate — LLM-owned
│   └── index.md                   # Central routing node and semantic map
│
├── scripts/
│   ├── scrape.py                   # Funnel B: URL → Markdown conversion + content validation
│   ├── compile.py                  # Compilation engine script
│   └── lint.py                     # Wiki health check script
│
├── mkdocs.yml                      # MkDocs configuration
├── pyproject.toml                  # Project metadata and dependencies (uv)
├── uv.lock                         # Pinned lockfile — committed to repo (uv)
├── requirements.txt                # Generated export via `uv pip compile` — for pip compatibility
├── CLAUDE.md                       # Behavioral schema for LLM agents
└── AGENTS.md                       # Research targets and autonomous agent rules (Funnel C, post-MVP)
```

### Directory Rules

- **`/raw/`** — Append-only. Documents are immutable once merged. The LLM reads from here but never writes.
- **`/wiki/`** — LLM-owned. Humans read from here but should not manually edit.
- **`raw/manifest.csv`** — Updated by every ingest workflow before creating a PR. Prevents duplicate ingestion across all funnels.
- **`uv.lock`** — Must be committed to the repository. This is the canonical source of pinned versions across all environments.
- **`requirements.txt`** — Generated file. Do not edit manually. Regenerate with `uv pip compile pyproject.toml -o requirements.txt` when dependencies change.

### manifest.csv Schema

```
url_normalized, url_sha256, content_sha256, date_ingested, pr_number, funnel
```

| Field | Description |
|---|---|
| `url_normalized` | URL with query params and UTM parameters stripped (e.g. `https://example.com/article`) |
| `url_sha256` | SHA256 of `url_normalized` — used as the deduplication key |
| `content_sha256` | SHA256 of scraped content — used for integrity verification, not deduplication |
| `date_ingested` | ISO 8601 timestamp |
| `pr_number` | GitHub PR number that introduced this entry |
| `funnel` | `A`, `B`, or `C` |

**URL normalization rules:** Strip all query parameters, UTM parameters, and trailing slashes before hashing. `https://example.com/article?utm_source=twitter` and `https://example.com/article` resolve to the same `url_normalized`.

---

## 3. Wiki Page Schema

Every page in `/wiki/` must conform to the following frontmatter schema, defined in `CLAUDE.md`. MkDocs uses this metadata for navigation and the lint action validates against it.

```yaml
---
title: "Human-readable Page Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - raw/filename.md
tags: []
---
```

**Rules enforced by lint action:**
- `title`, `created`, `updated`, `sources` are required fields
- `sources` must reference files that exist in `/raw/`
- Pages with no inbound `[[wikilinks]]` from other wiki pages are flagged as orphans

### Wikilink Format

MkDocs does not natively render `[[wikilinks]]`. The **`mkdocs-roamlinks-plugin`** is required. This preserves `[[wikilinks]]` syntax throughout, keeping future Obsidian and Quartz compatibility intact.

Add to `mkdocs.yml`:
```yaml
plugins:
  - roamlinks
```

**Critical:** `mkdocs-roamlinks-plugin` resolves links by **filename**, not by page title. The LLM must use `[[kebab-case-filename]]` syntax — matching the file's name without the `.md` extension.

```markdown
✅ Correct:   [[machine-learning-basics]]   → resolves to wiki/machine-learning-basics.md
❌ Incorrect: [[Machine Learning Basics]]   → will not resolve
```

Standard markdown links `[text](url)` are only used for external URLs.

---

## 4. The Human Approval Gateway (Branch Protection)

To prevent dataset corruption and AI hallucinations from entering the corpus, the `main` branch is strictly locked. **Human review before merge is the strongly recommended default** for all deployment modes.

### Configuration

**Settings → Branches → Branch Protection Rules:**
- Target: `main`
- Require pull request before merging

The required approval count is controlled by the `REQUIRE_PR_APPROVAL` repository variable:

| `REQUIRE_PR_APPROVAL` | Behavior | Recommended for |
|---|---|---|
| `true` (default) | Minimum 1 approval required; admins cannot bypass | Teams, collaborative wikis |
| `false` | Branch protection allows admin bypass; solo user can self-merge | Solo users only |

> ⚠️ Setting `REQUIRE_PR_APPROVAL=false` removes the second pair of eyes on incoming data. In solo mode, the PR itself still provides a review checkpoint — use it deliberately.

**Result:** All incoming data — whether from a human or an AI agent — must be staged in a Pull Request before compilation begins.

### AI-Assisted PR Review (Post-MVP)

An optional future feature: a GitHub Action triggered on `pull_request: opened` that invokes the LLM to review the incoming raw document and post a structured comment on the PR assessing relevance, quality, and potential issues. The human operator retains final merge authority. Flagged for v2.

### PR Conventions

All ingest PRs must follow the branch naming convention enforced in each workflow:

| Funnel | Branch Pattern |
|---|---|
| Funnel A (manual) | `ingest/manual-{slug}` |
| Funnel B (Issues) | `ingest/issue-{issue_number}` |
| Funnel C (agent, post-MVP) | `ingest/agent-{YYYYMMDD}-{slug}` |

The `PULL_REQUEST_TEMPLATE.md` must include: source URL, funnel type, AI-generated relevance summary (for Funnel B/C), and a checklist confirming the manifest was updated.

---

## 5. Data Ingestion Funnels (Pre-Compilation)

Data enters the system through two pipelines for MVP, both converging on the PR Gateway.

### Funnel A: Direct Local Push (Manual Curators)
**Actor:** Human user.
**Flow:**
1. User saves or clips source content locally
2. Checks `raw/manifest.csv` to confirm URL not already ingested
3. Adds document to `/raw/` and updates manifest
4. Commits to a new branch following `ingest/manual-{slug}` pattern
5. Pushes and opens PR against `main`

### Funnel B: GitHub Issues (Semi-Automated)
**Actor:** Human user + GitHub Action.
**Flow:**
1. User submits a GitHub Issue using the `new-source.yml` template (fields: URL, topic tags, notes)
2. Action trigger: `issues: opened` with label `new-source`
3. Action normalizes the URL and checks `raw/manifest.csv` — if `url_sha256` already exists, closes Issue with a comment and stops
4. Action runs `scripts/scrape.py` (see scraping strategy below)
5. **Content validation** — layered checks before proceeding (see below)
6. Converts to Markdown, saves to `/raw/{slug}.md`
7. Updates `raw/manifest.csv` with new entry
8. Uses `peter-evans/create-pull-request` to open a PR on branch `ingest/issue-{issue_number}`
9. PR body includes: source URL, scraper used, scrape timestamp, byte count, and an AI-generated relevance summary
10. Closes the originating Issue

**Permissions required in `ingest-issue.yml`:**
```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
```

### Funnel B: Scraping Strategy (Jina Reader + Trafilatura Fallback)

`scripts/scrape.py` uses a two-tier scraping strategy to balance Cloudflare avoidance with zero-dependency operation:

**Tier 1 — Jina Reader (default, Cloudflare-safe):**
Prepends `https://r.jina.ai/` to the target URL. Jina's servers handle the request, avoiding Cloudflare blocks that affect GitHub runner IPs directly.

- **Free tier (no API key):** Rate-limited by IP. Sufficient for MVP ingest volumes (a few URLs per day).
- **Free API key:** 100 RPM, 100K TPM, 10M token trial — set as `JINA_API_KEY` secret.
- **Limitation:** Jina does not actively bypass anti-bot systems. Strictly paywalled or bot-protected sites will still fail — Layer 2 content validation catches these.

**Tier 2 — Trafilatura (fallback, fully free, no API):**
If `JINA_API_KEY` is not set, `scrape.py` falls back to `trafilatura.fetch_url()` + `trafilatura.extract()`. Trafilatura runs entirely within the GitHub runner — no external service required. Trade-off: subject to Cloudflare blocking on GitHub runner IPs for heavily protected sites.

```python
def scrape(url: str, jina_api_key: str | None) -> str:
    if jina_api_key:
        # Tier 1: Jina Reader
        headers = {"Authorization": f"Bearer {jina_api_key}"}
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers)
        return response.text
    else:
        # Tier 2: Trafilatura (local, free)
        downloaded = trafilatura.fetch_url(url)
        return trafilatura.extract(downloaded) or ""
```

Template users who want zero external dependencies use Tier 2. Users who need Cloudflare-heavy source coverage use Tier 1 with a free Jina key.

### Funnel B: Content Validation (Layered)

`scripts/scrape.py` applies three sequential checks before creating a PR. All thresholds are configurable via repository variables or environment variables.

| Layer | Check | Failure behavior |
|---|---|---|
| 1. HTTP status | Response code is 2xx | Close Issue with error message; stop |
| 2. Error keyword detection | Scraped content does not contain strings like `"enable JavaScript"`, `"subscribe to read"`, `"access denied"`, `"403 Forbidden"`, `"429 Too Many Requests"` | Close Issue with detected keyword; stop |
| 3. Minimum content size | Content length ≥ `MIN_CONTENT_BYTES` (default: `500`, configurable) | Close Issue with byte count; stop |

> **Design note:** Layer 3 uses bytes rather than word count to remain format-agnostic. A short but valid source (e.g., a paper abstract, a structured data page) can pass Layer 3 by adjusting `MIN_CONTENT_BYTES` downward. Layers 1 and 2 are not configurable — they represent hard failure states with no valid exception.

### Funnel C: Autonomous AI Agent (Post-MVP)
Deferred to v2. Architecture will follow the same PR gateway pattern with branch naming `ingest/agent-{YYYYMMDD}-{slug}`. Will include a `MAX_SOURCES_PER_RUN` environment variable (default: `5`) and a token budget check before LLM invocation to prevent runaway API costs. Research sources will use RSS feeds, Tavily, or Exa APIs as defined in `AGENTS.md`.

---

## 6. The Compilation Engine (GitHub Actions)

Once a PR containing new documents in `/raw/` is approved and merged, the core compilation sequence begins.

### Trigger

```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'raw/**'

concurrency:
  group: compile-wiki
  cancel-in-progress: false
```

> **Note:** `cancel-in-progress: false` is intentional. Concurrent merges queue rather than drop, ensuring every new source is compiled.

### Infinite Loop Prevention

The compilation Action commits directly to `main`. Without a guard, this commit would retrigger the Action. Add the following condition to all jobs in `compile.yml`:

```yaml
jobs:
  compile:
    if: "!startsWith(github.event.head_commit.message, 'chore(compile):')"
```

### Dependency Installation (uv)

All workflows use `uv` for dependency installation. `uv` installs dependencies significantly faster than `pip` and caches the `uv.lock` hash across runs — unchanged dependencies are restored from cache without re-downloading.

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@{SHA}   # pin to SHA per spec rules
  with:
    enable-cache: true

- name: Install dependencies
  run: uv pip install -r requirements.txt
  env:
    UV_SYSTEM_PYTHON: 1             # install to system Python, not a venv
```

> `UV_SYSTEM_PYTHON: 1` is required in GitHub Actions when not using a virtual environment.

### Permissions

```yaml
permissions:
  contents: write
  pages: write
  id-token: write
```

All Actions must use SHA-pinned dependencies, not tag references:
```yaml
# ✅ Correct
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af68

# ❌ Avoid
uses: actions/checkout@v4
```

### LLM Provider Abstraction

`compile.py` is provider-agnostic, controlled by the `LLM_PROVIDER` environment variable. This allows switching between external APIs and local Ollama without code changes.

| `LLM_PROVIDER` | Backend | Requires | Notes |
|---|---|---|---|
| `anthropic` (default) | Anthropic API | `ANTHROPIC_API_KEY` | Best quality; recommended for GitHub Actions |
| `openai` | OpenAI API or any OpenAI-compatible endpoint | `OPENAI_API_KEY`, optionally `OPENAI_BASE_URL` | Use for OpenAI, Ollama, or any other compatible server |

**Using Ollama:** Set `LLM_PROVIDER=openai`, point `OPENAI_BASE_URL` at the Ollama server, and use any placeholder for `OPENAI_API_KEY`. Ollama's REST API is fully OpenAI-compatible — no separate provider type or SDK needed.

```bash
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
python scripts/compile.py raw/my-new-doc.md
```

**Provider routing pattern in `compile.py`:**

```python
import os
from openai import OpenAI
import anthropic

LLM_PROVIDER  = os.environ.get("LLM_PROVIDER", "anthropic")
OPENAI_MODEL  = os.environ.get("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")  # None = default OpenAI endpoint

def call_llm(system_prompt: str, user_content: str) -> str:
    if LLM_PROVIDER == "anthropic":
        client = anthropic.Anthropic()
        # Use tool use for structured output
        ...
    elif LLM_PROVIDER == "openai":
        # OPENAI_BASE_URL=None → OpenAI API
        # OPENAI_BASE_URL=http://localhost:11434/v1 → Ollama
        # OPENAI_BASE_URL=<any compatible endpoint> → works the same way
        client = OpenAI(base_url=OPENAI_BASE_URL)
        # Use response_format for structured output
        ...
```

**Ollama on GitHub Actions (standard runners):**
Ollama can be installed on `ubuntu-latest` runners via `ai-action/setup-ollama`. However, standard runners are CPU-only — large models (7B+) will be slow. Restrict to small models (tinyllama, phi3-mini) for Actions use. This mode is suitable for MVP testing and template demonstration, not for production compilation throughput.

```yaml
# Optional: for testing/demo with local LLM on standard runner
- name: Setup Ollama
  uses: ai-action/setup-ollama@{SHA}

- name: Pull model
  run: ollama pull tinyllama

- name: Run compilation
  run: python scripts/compile.py raw/my-new-doc.md
  env:
    LLM_PROVIDER: openai
    OPENAI_BASE_URL: http://localhost:11434/v1
    OPENAI_API_KEY: ollama
    OPENAI_MODEL: tinyllama
```

> **Future upgrade:** For full-quality Ollama in GitHub Actions, register a machine with a GPU as a self-hosted runner (`runs-on: [self-hosted, gpu]`). This enables large model inference at zero API cost. Flagged for v2.

### Execution Steps

1. **Trigger** — Push to `main` with changes in `/raw/**` (commit message does not start with `chore(compile):`)

2. **Context gathering** — `compile.py` extracts keyphrases from the new document's title and first paragraph, then uses `ripgrep` to find relevant existing wiki nodes:
   ```bash
   rg -l "keyphrase1|keyphrase2|keyphrase3" wiki/
   ```
   The top 5 matching files (by match count) are included as context. Ripgrep is pre-installed on GitHub runners — zero setup required.

   > **Future upgrade:** Replace ripgrep with `qmd` for hybrid BM25/vector search once the wiki exceeds ~100 pages.

3. **LLM invocation** — Script sends a structured payload via `call_llm()`:
   - System prompt loaded from `CLAUDE.md`
   - New `/raw/` document content
   - Content of relevant existing `/wiki/` nodes found by ripgrep
   - Current `wiki/index.md`

   **Structured output is the primary mechanism** for forcing valid JSON — not prompt instructions alone:
   - **Anthropic:** Use the `tools` parameter with a JSON schema matching the output contract
   - **OpenAI / Ollama:** Use `response_format: { type: "json_object" }`

   Set `max_tokens` dynamically based on expected output size. A baseline of `4000` tokens handles up to ~3 page updates. Increase proportionally for larger compilations. Do not use the default of `1000` — it will truncate multi-page JSON responses.

4. **Output contract** — The LLM must return a JSON object with this exact structure:
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

   `compile.py` must sanitize the raw API response before parsing, as a fallback for cases where structured output is unavailable or returns fenced code blocks:
   ```python
   import re, json

   def parse_llm_response(raw: str) -> dict:
       cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip())
       cleaned = re.sub(r'\s*```$', '', cleaned.strip())
       return json.loads(cleaned)
   ```

5. **`index_patch` application** — `wiki/index.md` must contain the marker comment `<!-- COMPILE_INSERT_HERE -->`. The compilation script inserts the `index_patch` string directly above this marker on each run. Template `index.md` must include this marker at initial setup.

6. **Chunking strategy** — If the raw document exceeds 80,000 tokens, `compile.py` splits it by top-level heading (`# `) and processes each chunk sequentially, merging results before committing.

7. **Validation** — Before committing, `compile.py` runs a lightweight check:
   - Valid frontmatter on all new/updated pages
   - No `[[wikilinks]]` pointing to filenames that do not exist in `/wiki/`
   - All `sources` fields reference files that exist in `/raw/`

8. **Commit** — Action commits compiled files to `main` with message format: `chore(compile): {sha of triggering raw file}` — enables targeted `git revert` if needed, and prevents the infinite loop condition in step 1.

9. **MkDocs build** — Action runs `mkdocs build` and deploys to GitHub Pages via `actions/deploy-pages`.

### Error Handling

| Failure point | Behavior |
|---|---|
| LLM API timeout / error | Action fails; GitHub sends default failure notification; raw doc stays uncompiled; retry on next push |
| Structured output unavailable; sanitized response still invalid JSON | Action fails with log showing raw LLM response; no commit made |
| `max_tokens` truncation produces incomplete JSON | Caught by `json.loads()` exception; Action fails cleanly; increase `max_tokens` and retry |
| Validation fails (bad frontmatter / broken links) | Action fails before any commit; error annotated in Action log |
| MkDocs build fails | Wiki files already committed and intact; only Pages deployment fails; does not block next compilation |
| OpenAI-compatible endpoint unreachable (incl. Ollama) | `call_llm()` raises connection error; Action fails cleanly; check `OPENAI_BASE_URL` in logs |

---

## 7. Wiki Lint / Health Action

A separate scheduled Action maintains wiki integrity over time. The lint frequency is fully configurable — adjust the cron expression to match the wiki's activity level.

### Configuration

```yaml
# .github/workflows/lint-wiki.yml
on:
  schedule:
    - cron: '0 9 * * 1'  # Default: Every Monday 09:00 UTC — edit as needed
  workflow_dispatch:      # Allow manual trigger at any time
```

### Checks (`scripts/lint.py`)

- Broken `[[wikilinks]]` — link target filename does not exist in `/wiki/`
- Orphan pages — pages with no inbound links from any other wiki page
- Pages missing required frontmatter fields (`title`, `created`, `updated`, `sources`)
- `sources` entries pointing to files that do not exist in `/raw/`
- Pages listed in `index.md` that no longer exist as files
- Pages that exist as files but are not listed in `index.md`

### Reporting

**Always:** Write the full lint report to `$GITHUB_STEP_SUMMARY`. This appears in the Actions run UI, is naturally organized by run date, and creates zero tracker noise.

**Only when issues are found:** Create a new GitHub Issue with label `wiki-health`. Each run that finds problems creates its own Issue — this keeps individual runs inspectable and avoids the problem of a single accumulated issue becoming difficult to parse at high lint frequencies.

**When no issues are found:** No Issue is created. The clean run is visible in the Action summary only.

---

## 8. Visualization & Search (Frontend)

### Static Site Generator
**MkDocs** with the **Material theme**.

```yaml
# mkdocs.yml
site_name: LLM Wiki
site_url: https://{username}.github.io/{repo}/   # Required for correct GitHub Pages routing
theme:
  name: material
  features:
    - navigation.instant
    - search.highlight
plugins:
  - search          # Built-in, client-side, no backend required
  - roamlinks       # [[wikilink]] support
```

> **One-time setup:** In repository Settings → Pages, set Source to **GitHub Actions** (not a branch). This is required for `actions/deploy-pages` to work.

**Hosting:** GitHub Pages via `actions/deploy-pages`, triggered as the final step of the compilation engine Action.

> **Future upgrade:** Replace MkDocs with Quartz for interactive node-graph visualization of `[[wikilinks]]`. Quartz natively parses wikilinks and renders an Obsidian-style graph view. Migration is low-friction because the wiki content format (frontmatter + `[[kebab-case-filename]]` wikilinks) is identical between the two.

---

## 9. Local Development Setup

For contributors and template users forking this repo.

### Tech Stack

**Language:** Python 3.11+. Chosen for: first-class Anthropic/OpenAI/Ollama SDK support, mature text processing ecosystem, and wide familiarity in the AI tooling community.

**Package manager:** `uv`. Faster than pip (10–100x), smart caching, and `uv.lock` for reproducible installs across all environments. Used in both local dev and GitHub Actions.

### Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install dependencies from lockfile
git clone https://github.com/{org}/{repo}
cd {repo}
uv sync --frozen    # installs exact versions from uv.lock

# Set environment variables
cp .env.example .env
# Edit .env with your API keys
```

> `uv sync --frozen` installs exact pinned versions from `uv.lock`. Never edit `uv.lock` manually — it is managed by uv.

### pyproject.toml (template)

```toml
[project]
name = "llm-wiki"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    # LLM providers — all included; active provider set via LLM_PROVIDER env var
    "anthropic>=0.49.0",
    "openai>=1.75.0",       # used for OpenAI API and any OpenAI-compatible endpoint (e.g. Ollama)

    # Scraping
    "requests>=2.32.3",
    "trafilatura>=2.0.0",   # free local fallback scraper, no API required

    # Wiki compilation
    "python-frontmatter>=1.1.0",

    # MkDocs
    "mkdocs>=1.6.1",
    "mkdocs-material>=9.6.14",
    "mkdocs-roamlinks-plugin>=0.3.1",
]
```

### requirements.txt (generated export for pip compatibility)

> Do not edit manually. Regenerate with:
> ```bash
> uv pip compile pyproject.toml -o requirements.txt
> ```

```
# Auto-generated by uv pip compile — do not edit manually
anthropic==0.49.0
openai==1.75.0
requests==2.32.3
trafilatura==2.0.0
python-frontmatter==1.1.0
mkdocs==1.6.1
mkdocs-material==9.6.14
mkdocs-roamlinks-plugin==0.3.1
# ... (transitive dependencies pinned by uv)
```

### Running compilation locally

```bash
# Dry run — prints compiled output to stdout, writes nothing
COMPILE_DRY_RUN=true python scripts/compile.py raw/my-new-doc.md

# Full run with Anthropic (default)
LLM_PROVIDER=anthropic python scripts/compile.py raw/my-new-doc.md

# Full run with OpenAI
LLM_PROVIDER=openai python scripts/compile.py raw/my-new-doc.md

# Full run with Ollama (local, free) — same openai provider, different base URL
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
python scripts/compile.py raw/my-new-doc.md

# Preview the site
mkdocs serve
```

### Using Ollama locally

```bash
# Install Ollama (https://ollama.com)
ollama pull llama3.2          # or any model from ollama.com/library
ollama serve                  # starts REST server at http://localhost:11434

# Run compilation via openai provider pointed at Ollama
LLM_PROVIDER=openai \
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=llama3.2 \
python scripts/compile.py raw/my-new-doc.md
```

Ollama exposes a fully OpenAI-compatible REST API at `/v1`. No separate Ollama SDK or provider type is needed — the `openai` package handles it transparently by pointing `OPENAI_BASE_URL` at the local server. `OPENAI_API_KEY` can be any non-empty string; Ollama ignores it.

### Running lint locally

```bash
python scripts/lint.py
# Output written to stdout; no GitHub Issue created in local mode
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No | `anthropic` (default) or `openai` |
| `ANTHROPIC_API_KEY` | If `LLM_PROVIDER=anthropic` | Anthropic API key |
| `OPENAI_API_KEY` | If `LLM_PROVIDER=openai` | OpenAI API key — use any placeholder string for Ollama |
| `OPENAI_BASE_URL` | No | Override OpenAI endpoint (e.g. `http://localhost:11434/v1` for Ollama); if unset, defaults to OpenAI's API |
| `OPENAI_MODEL` | No | Model name for `openai` provider (default: `gpt-4o`); set to Ollama model name when using local inference |
| `JINA_API_KEY` | No | Jina Reader API key; if unset, Trafilatura fallback is used |
| `MIN_CONTENT_BYTES` | No | Minimum scraped content size (default: `500`) |
| `COMPILE_DRY_RUN` | No | If `true`, prints output without writing files |
| `REQUIRE_PR_APPROVAL` | No | Repository variable; controls branch protection mode (default: `true`) |

In GitHub Actions, secrets are stored as **Repository Secrets** (`${{ secrets.KEY_NAME }}`). Non-sensitive config uses Repository Variables (`${{ vars.VARIABLE_NAME }}`). Keys are never hardcoded.

---

## 10. Rollback & Recovery

- Every compilation commit uses the format `chore(compile): {sha}`, making it trivially identifiable in `git log`
- To revert a bad compilation: `git revert <commit-sha>` — this restores the affected wiki pages without touching `/raw/`
- The raw source that triggered a bad compile is identified by the SHA in the commit message and can be reviewed or removed via a new PR
- `/raw/` is append-only by convention, not by git enforcement — deletion of a bad raw source requires a PR to `main` like any other change

---

## 11. CLAUDE.md Behavioral Schema (Template)

`CLAUDE.md` is loaded by `compile.py` as the system prompt and governs all LLM behavior. At minimum it must define:

```markdown
# Wiki Compilation Rules

## Output Format
Always respond with a single valid JSON object matching the output contract schema.
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
- created / updated: YYYY-MM-DD format
- sources: list of /raw/ filenames that contributed to this page
- tags: list of lowercase hyphenated strings

## Naming Conventions
- Page filenames: kebab-case (e.g. machine-learning-basics.md)
- Page titles: Title Case (e.g. "Machine Learning Basics")
- Tags: lowercase, hyphenated (e.g. "neural-networks")

## Synthesis Rules
- Extract key claims, entities, and concepts from the new source
- Update existing pages when new source adds, contradicts, or refines existing content
- Note contradictions explicitly with a `> ⚠️ Contradiction:` blockquote
- Do not delete content from existing pages — only add or annotate
- Do not fabricate citations or sources not present in the provided /raw/ document
```

---

## Appendix: Future Considerations

| Item | Replaces | When to consider |
|---|---|---|
| Quartz SSG | MkDocs | When graph visualization becomes a priority |
| `qmd` search | ripgrep | When wiki exceeds ~100 pages |
| Funnel C autonomous agent | Manual research | v2, after compilation pipeline is stable |
| AI-assisted PR review | Manual-only review | v2, as an optional overlay on the PR gateway |
| Self-hosted GitHub runner + GPU | Standard runner + Ollama CPU | v2, for full-quality local LLM in Actions at zero API cost |
| Private GitHub Pages | Public deployment | When handling sensitive content |
| Multi-repo federation | Single repo | v3, when wiki spans multiple domains |
| TypeScript rewrite | Python scripts | If team prefers TypeScript; use `@anthropic-ai/sdk` or `openai` npm packages; note: requires `actions/setup-node` step in all workflows |
