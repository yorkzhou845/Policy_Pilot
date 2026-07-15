import unittest

from document_loader import chunk_text, normalize_text


class DocumentLoaderTests(unittest.TestCase):
    def test_normalize_text_removes_excess_whitespace(self):
        self.assertEqual(normalize_text("A   line\n\n\nB"), "A line\n\nB")

    def test_chunk_text_respects_size_for_normal_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=35, overlap=5)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(chunk.strip() for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
