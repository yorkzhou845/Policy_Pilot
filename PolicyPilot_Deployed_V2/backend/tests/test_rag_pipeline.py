import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Settings
from rag import answer_question, rebuild_index


class FakeOllamaClient:
    def embed(self, model, inputs):
        values = [inputs] if isinstance(inputs, str) else list(inputs)
        vectors = []
        for value in values:
            lowered = value.lower()
            vectors.append([1.0, 0.0] if "retain" in lowered or "retention" in lowered else [0.0, 1.0])
        return vectors

    def chat(self, model, system_prompt, user_prompt):
        return "Approved records are retained for three years. (Source: sample.md)"


class RagPipelineTests(unittest.TestCase):
    def test_rebuild_and_answer_with_fake_ollama(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            documents = base / "documents"
            documents.mkdir()
            (documents / "sample.md").write_text(
                "Approved records must be retained for three years.", encoding="utf-8"
            )

            settings = Settings(
                ollama_base_url="http://localhost:11434",
                chat_model="chat-model",
                embed_model="embed-model",
                ollama_timeout_seconds=10,
                documents_dir=documents,
                vector_store_csv=base / "vectors.csv",
                top_k=3,
                min_similarity=-1.0,
                chunk_size_chars=500,
                chunk_overlap_chars=20,
                max_context_chars=2000,
            )

            with patch("rag._client", return_value=FakeOllamaClient()):
                count = rebuild_index(settings)
                result = answer_question("How long are records retained?", config=settings)

            self.assertEqual(count, 1)
            self.assertIn("three years", result.answer)
            self.assertEqual(result.citations[0].source_file, "sample.md")


if __name__ == "__main__":
    unittest.main()
