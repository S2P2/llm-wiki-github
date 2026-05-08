"""Wiki compilation engine — transforms raw documents into structured wiki pages."""

import json
import re
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
