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
