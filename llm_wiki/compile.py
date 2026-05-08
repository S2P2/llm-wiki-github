"""Wiki compilation engine — transforms raw documents into structured wiki pages."""

import json
import re

COMPILE_INSERT_MARKER = "<!-- COMPILE_INSERT_HERE -->"


def parse_llm_response(raw: str) -> dict:
    """Parse LLM response, stripping markdown code fences if present."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned)
