"""Tests for Deck setup helpers."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chahlie.deck_setup import (
    needs_api_key_setup,
    sanitize_api_key,
    save_api_key,
    verify_api_key,
)


class TestDeckSetup(unittest.TestCase):
    def test_sanitize_strips_quotes(self):
        self.assertEqual(sanitize_api_key('"abc12345"'), "abc12345")
        self.assertEqual(sanitize_api_key("  key12345  "), "key12345")

    def test_needs_key_when_placeholder(self):
        os.environ["CHAHLIE_BACKEND"] = "ollama-cloud"
        os.environ["OLLAMA_API_KEY"] = "your-ollama-cloud-api-key-here"
        self.assertTrue(needs_api_key_setup())

    def test_save_api_key_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            save_api_key("test-key-12345678", path)
            text = path.read_text()
            self.assertIn("OLLAMA_API_KEY=test-key-12345678", text)

    @patch("requests.get")
    def test_verify_rejects_401(self, mock_get):
        mock_get.return_value.status_code = 401
        ok, msg = verify_api_key("bad-key-12345678")
        self.assertFalse(ok)
        self.assertIn("401", msg)


if __name__ == "__main__":
    unittest.main()
