import tempfile
import unittest
from pathlib import Path

from vector_store import CsvVectorStore, VectorRecord, cosine_similarity


class VectorStoreTests(unittest.TestCase):
    def test_cosine_similarity(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_csv_round_trip_and_search(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vectors.csv"
            store = CsvVectorStore(path)
            store.write(
                [
                    VectorRecord("a", "a.txt", 0, "alpha", "test-model", [1.0, 0.0]),
                    VectorRecord("b", "b.txt", 0, "beta", "test-model", [0.0, 1.0]),
                ]
            )

            results = store.search([0.9, 0.1], "test-model", top_k=1, minimum_score=-1.0)
            self.assertEqual(results[0].record.source_file, "a.txt")


if __name__ == "__main__":
    unittest.main()
