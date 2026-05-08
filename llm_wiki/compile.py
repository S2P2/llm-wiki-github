"""Wiki compilation engine — transforms raw documents into structured wiki pages."""

import json
import re
import subprocess
from pathlib import Path

import frontmatter

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
    keyphrases = extract_keyphrases(raw_doc.read_text())
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
