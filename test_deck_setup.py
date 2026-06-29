"""Tests for Deck first-run setup helpers."""

import os
import tempfile
import unittest
from pathlib import Path

from chahlie.deck_setup import needs_api_key_setup, save_api_key


class TestDeckSetup(unittest.TestCase):
    def test_needs_key_when_placeholder(self):
        os.environ["CHAHLIE_BACKEND"] = "ollama-cloud"
        os.environ["OLLAMA_API_KEY"] = "your-ollama-cloud-api-key-here"
        self.assertTrue(needs_api_key_setup())

    def test_needs_key_when_missing(self):
        os.environ["CHAHLIE_BACKEND"] = "ollama-cloud"
        os.environ.pop("OLLAMA_API_KEY", None)
        self.assertTrue(needs_api_key_setup())

    def test_save_api_key_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            save_api_key("test-key-12345678", path)
            text = path.read_text()
            self.assertIn("OLLAMA_API_KEY=test-key-12345678", text)


if __name__ == "__main__":
    unittest.main()
