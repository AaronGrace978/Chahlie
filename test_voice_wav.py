"""Tests for voice WAV helpers."""

import os
import tempfile
import unittest
import wave

from chahlie.voice import _wav_ok, _wrap_raw_pcm_as_wav


class TestVoiceWav(unittest.TestCase):
    def test_wav_ok_rejects_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name
        try:
            open(path, "wb").write(b"tiny")
            self.assertFalse(_wav_ok(path))
        finally:
            os.unlink(path)

    def test_wrap_raw_pcm(self):
        with tempfile.TemporaryDirectory() as d:
            raw = os.path.join(d, "a.raw")
            wav = os.path.join(d, "a.wav")
            open(raw, "wb").write(b"\x00\x01" * 800)
            _wrap_raw_pcm_as_wav(raw, wav)
            self.assertTrue(_wav_ok(wav))
            with wave.open(wav, "rb") as wf:
                self.assertEqual(wf.getframerate(), 16000)


if __name__ == "__main__":
    unittest.main()
