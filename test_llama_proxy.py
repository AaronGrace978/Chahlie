"""Tests for OpenAI-compatible proxy helpers."""

import unittest
from unittest.mock import MagicMock, patch

from chahlie.deck_setup import needs_api_key_setup, verify_openai_compatible


class TestLlamaProxy(unittest.TestCase):
    def test_needs_key_false_for_openai_compatible(self):
        import os
        os.environ["CHAHLIE_BACKEND"] = "openai-compatible"
        self.assertFalse(needs_api_key_setup())

    @patch("requests.get")
    def test_verify_openai_compatible_ok(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        ok, err = verify_openai_compatible("http://127.0.0.1:11435/v1")
        self.assertTrue(ok)
        self.assertEqual(err, "")

    @patch("requests.get")
    def test_verify_openai_compatible_401(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401)
        ok, err = verify_openai_compatible("http://127.0.0.1:11435/v1", "bad-key")
        self.assertFalse(ok)
        self.assertIn("401", err)


if __name__ == "__main__":
    unittest.main()
