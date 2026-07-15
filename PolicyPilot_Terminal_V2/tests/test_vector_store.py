from pathlib import Path

from vector_store import build_index, load_records, search


class FakeOllamaClient:
    def embed(self, texts, model):
        if isinstance(texts, str):
            texts = [texts]
        return [
            [float(len(text)), float(text.lower().count("equipment")), 1.0]
            for text in texts
        ]


def test_build_and_search_csv_index(tmp_path: Path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "policy.txt").write_text(
        "Equipment checkout requires approval. Equipment is due in seven days.",
        encoding="utf-8",
    )
    csv_path = tmp_path / "vectors.csv"
    client = FakeOllamaClient()

    files, chunks = build_index(
        documents_dir,
        csv_path,
        client,
        "fake-embed",
        max_chunk_chars=200,
        overlap_chars=20,
        batch_size=8,
    )

    assert files == 1
    assert chunks == 1
    assert len(load_records(csv_path)) == 1

    query_embedding = client.embed("equipment approval", "fake-embed")[0]
    results = search(csv_path, query_embedding, "fake-embed", top_k=1)
    assert results[0].record.source == "policy.txt"
