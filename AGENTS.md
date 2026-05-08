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
