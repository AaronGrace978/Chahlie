"""Smoke tests for Chahlie Tauri API server."""

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from chahlie.tauri_server import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "fastapi not installed")
class TauriServerTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("chahlie.tauri_server.needs_api_key_setup", return_value=False)
    def test_status(self, _mock):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("version", body)
        self.assertIn("greeting", body)


if __name__ == "__main__":
    unittest.main()
