"""Wiki compilation engine — transforms raw documents into structured wiki pages."""

import json
import os
import re
import subprocess
from pathlib import Path

import anthropic
import frontmatter
from openai import OpenAI

COMPILE_INSERT_MARKER = "<!-- COMPILE_INSERT_HERE -->"

REQUIRED_FRONTMATTER_FIELDS = ("title", "created", "updated", "sources")


def parse_llm_response(raw: str) -> dict:
    """Parse LLM response, stripping markdown code fences if present."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned)


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
    """Find relevant existing wiki pages using ripgrep with Python fallback."""
    keyphrases = extract_keyphrases(raw_doc.read_text(encoding="utf-8"))
    if not keyphrases or not wiki_dir.exists():
        return []

    pattern = "|".join(re.escape(kp) for kp in keyphrases)
    matches = _rg_search(pattern, wiki_dir)
    if matches is None:
        matches = _py_search(pattern, wiki_dir)

    matches.sort(key=lambda x: x[1], reverse=True)
    return [path for path, _ in matches[:top_k]]


def _rg_search(pattern: str, wiki_dir: Path) -> list[tuple[Path, int]] | None:
    """Search using ripgrep. Returns None if rg is unavailable."""
    try:
        proc = subprocess.run(
            ["rg", "-l", "-c", pattern, str(wiki_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

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
    return matches


def _py_search(pattern: str, wiki_dir: Path) -> list[tuple[Path, int]]:
    """Fallback search using Python regex when ripgrep is unavailable."""
    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[tuple[Path, int]] = []
    for md_file in wiki_dir.glob("*.md"):
        count = len(regex.findall(md_file.read_text(encoding="utf-8")))
        if count > 0:
            matches.append((md_file, count))
    return matches


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
    provider = os.environ.get("LLM_PROVIDER", "openai")

    if provider == "anthropic":
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


def apply_compilation(result: dict, wiki_dir: Path, index_path: Path) -> None:
    """Write compiled pages to disk and update index.md with new entries."""
    for page_type in ("new_pages", "updated_pages"):
        for page in result.get(page_type, []):
            filename = Path(page["filename"]).name
            filepath = wiki_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(page["content"], encoding="utf-8")

    patch = result.get("index_patch", "")
    if not patch:
        return

    content = index_path.read_text(encoding="utf-8")
    content = content.replace(COMPILE_INSERT_MARKER, f"{patch}\n{COMPILE_INSERT_MARKER}")
    index_path.write_text(content, encoding="utf-8")


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

    system_prompt = agents_path.read_text(encoding="utf-8")
    dry_run = os.environ.get("COMPILE_DRY_RUN", "").lower() == "true"

    for raw_file in args.files:
        raw_path = Path(raw_file)
        if not raw_path.exists():
            print(f"Error: {raw_path} not found", file=sys.stderr)
            sys.exit(1)

        context_pages = gather_context(raw_path, wiki_dir)
        context_content = ""
        if context_pages:
            parts = [f"--- Existing wiki page: {p.name} ---\n{p.read_text(encoding='utf-8')}" for p in context_pages]
            context_content = "\n\n".join(parts)

        index_content = ""
        if index_path.exists():
            index_content = f"--- Current index.md ---\n{index_path.read_text(encoding='utf-8')}"

        user_parts = [f"--- New source document ---\n{raw_path.read_text(encoding='utf-8')}"]
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
            print(
                f"Compiled {raw_path.name} → {len(result.get('new_pages', []))} new, "
                f"{len(result.get('updated_pages', []))} updated pages",
                file=sys.stderr,
            )
