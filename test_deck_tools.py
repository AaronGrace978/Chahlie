"""Tests for Steam Deck native tools."""

import os
import unittest
from unittest.mock import patch

from chahlie.deck_tools import (
    deck_set_volume,
    deck_steam,
    deck_system_info,
    DECK_TOOL_DEFINITIONS,
)
from chahlie.tools import get_tool_definitions


class TestDeckTools(unittest.TestCase):
    def test_deck_tool_definitions_count(self):
        self.assertEqual(len(DECK_TOOL_DEFINITIONS), 5)
        names = {t["name"] for t in DECK_TOOL_DEFINITIONS}
        self.assertIn("deck_launch", names)
        self.assertIn("deck_system_info", names)

    def test_get_tool_definitions_includes_deck_when_mode_on(self):
        os.environ["CHAHLIE_DECK_MODE"] = "true"
        from importlib import reload
        from chahlie import config
        reload(config)
        from chahlie import tools
        reload(tools)
        defs = tools.get_tool_definitions()
        names = {t["name"] for t in defs}
        self.assertIn("deck_launch", names)
        os.environ.pop("CHAHLIE_DECK_MODE", None)
        reload(config)
        reload(tools)

    @patch("chahlie.deck_tools._run")
    def test_deck_steam_status(self, mock_run):
        mock_run.return_value = (True, "running", "")
        result = deck_steam("status")
        self.assertTrue(result.success)
        self.assertIn("running", result.output)

    @patch("chahlie.deck_tools.shutil.which", return_value=None)
    def test_deck_set_volume_no_pactl(self, _mock):
        result = deck_set_volume(50)
        self.assertFalse(result.success)
        self.assertIn("pactl", result.error or "")

    @patch("chahlie.deck_tools._run")
    def test_deck_system_info(self, mock_run):
        mock_run.side_effect = [
            (True, 'PRETTY_NAME="SteamOS"', ""),
            (True, "up 1 hour", ""),
            (True, "Filesystem 50G 10G 40G", ""),
            (True, "Mem: 8Gi total", ""),
            (True, "running", ""),
        ]
        result = deck_system_info()
        self.assertTrue(result.success)
        self.assertIn("SteamOS", result.output)


if __name__ == "__main__":
    unittest.main()
