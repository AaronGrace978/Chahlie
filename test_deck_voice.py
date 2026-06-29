"""Smoke tests for Steam Deck voice helpers (no mic/hardware required)."""

import unittest

from chahlie.voice import _clean_for_speech, voice_available, stt_available, tts_available


class TestVoiceHelpers(unittest.TestCase):
    def test_clean_for_speech_strips_markdown(self):
        raw = "Check `foo.py` and **bold** text.\n```py\nprint(1)\n```\nDone."
        cleaned = _clean_for_speech(raw)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertIn("Done", cleaned)

    def test_clean_for_speech_truncates(self):
        long_text = "word " * 200
        cleaned = _clean_for_speech(long_text, max_chars=50)
        self.assertLessEqual(len(cleaned), 50)

    def test_availability_probes_are_bool(self):
        self.assertIsInstance(voice_available(), bool)
        self.assertIsInstance(stt_available(), bool)
        self.assertIsInstance(tts_available(), bool)


if __name__ == "__main__":
    unittest.main()
