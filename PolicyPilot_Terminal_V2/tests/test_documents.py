from documents import DocumentSection, chunk_sections, split_text


def test_split_text_respects_size_and_overlap():
    text = "Sentence one. " * 80
    chunks = split_text(text, max_chars=220, overlap_chars=30)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 220 for chunk in chunks)


def test_chunk_sections_assigns_indexes_and_content():
    sections = [DocumentSection("sample.txt", "document", "A short test document.")]
    chunks = chunk_sections(sections, max_chars=100, overlap_chars=10)
    assert chunks[0].source == "sample.txt"
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "A short test document."
