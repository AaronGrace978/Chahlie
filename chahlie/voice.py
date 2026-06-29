"""
Voice input/output for Chahlie — talk to your coding agent.

On Steam Deck / Linux we use system audio tools (pw-record, espeak-ng) so
nothing needs to compile. PyAudio is optional fallback only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Availability probes (no hard deps at import time)
# ---------------------------------------------------------------------------

_STT_AVAILABLE: Optional[bool] = None
_TTS_AVAILABLE: Optional[bool] = None
_LINUX_RECORDER: Optional[str] = None


def _linux_recorder() -> Optional[str]:
    """Return pw-record or parecord path when available."""
    global _LINUX_RECORDER
    if _LINUX_RECORDER is None:
        for name in ("pw-record", "parecord"):
            path = shutil.which(name)
            if path:
                _LINUX_RECORDER = path
                break
        if _LINUX_RECORDER is None:
            _LINUX_RECORDER = ""
    return _LINUX_RECORDER or None


def _pyaudio_available() -> bool:
    try:
        import pyaudio  # noqa: F401
        return True
    except ImportError:
        return False


def stt_available() -> bool:
    """Return True if speech-to-text can run on this machine."""
    global _STT_AVAILABLE
    if _STT_AVAILABLE is None:
        try:
            import speech_recognition  # noqa: F401
        except ImportError:
            _STT_AVAILABLE = False
        else:
            _STT_AVAILABLE = bool(_linux_recorder() or _pyaudio_available())
    return _STT_AVAILABLE


def tts_available() -> bool:
    """Return True if text-to-speech can run on this machine."""
    global _TTS_AVAILABLE
    if _TTS_AVAILABLE is None:
        if shutil.which("espeak-ng") or shutil.which("espeak"):
            _TTS_AVAILABLE = True
        else:
            try:
                import pyttsx3  # noqa: F401
                _TTS_AVAILABLE = True
            except ImportError:
                _TTS_AVAILABLE = False
    return _TTS_AVAILABLE


def voice_available() -> bool:
    return stt_available() or tts_available()


# ---------------------------------------------------------------------------
# Linux mic capture (no PyAudio / no gcc)
# ---------------------------------------------------------------------------

def _record_wav_linux(path: str, seconds: float) -> None:
    """Record microphone audio to a WAV file using PipeWire/PulseAudio tools."""
    recorder = _linux_recorder()
    if not recorder:
        raise RuntimeError(
            "No mic recorder found. On Steam Deck run:\n"
            "  sudo pacman -S pipewire-pulse"
        )

    secs = max(1, int(seconds))
    name = os.path.basename(recorder)

    if name == "pw-record":
        cmd = [
            recorder,
            "--rate", "16000",
            "--channels", "1",
            "--format", "s16",
            path,
        ]
    else:
        cmd = [
            recorder,
            f"--rate=16000",
            "--channels=1",
            "--file-format=wav",
            path,
        ]

    try:
        subprocess.run(
            ["timeout", str(secs), *cmd],
            check=True,
            capture_output=True,
            timeout=secs + 5,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="replace").strip()
        raise RuntimeError(f"Mic recording failed: {stderr or exc}") from exc
    except FileNotFoundError:
        # timeout binary missing — run recorder directly
        subprocess.run(cmd, check=True, capture_output=True, timeout=secs + 5)

    if not os.path.isfile(path) or os.path.getsize(path) < 100:
        raise RuntimeError("Didn't catch anything — try again, kehd.")


# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------

class SpeechListener:
    """Capture microphone audio and transcribe to text."""

    def __init__(
        self,
        language: str = "en-US",
        timeout: float = 8.0,
        phrase_limit: float = 12.0,
        energy_threshold: int = 300,
    ):
        self.language = language
        self.timeout = timeout
        self.phrase_limit = phrase_limit
        self.energy_threshold = energy_threshold
        self._recognizer = None
        self._mic = None

    def _ensure(self) -> None:
        if self._recognizer is not None:
            return
        import speech_recognition as sr
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = self.energy_threshold
        self._recognizer.dynamic_energy_threshold = True
        if _pyaudio_available():
            self._mic = sr.Microphone()

    def _capture_audio(self, on_status: Optional[Callable[[str], None]]):
        import speech_recognition as sr

        if on_status:
            on_status("listening")

        if _linux_recorder() and sys.platform.startswith("linux"):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            try:
                _record_wav_linux(wav_path, self.phrase_limit)
                with sr.AudioFile(wav_path) as source:
                    return self._recognizer.record(source)
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

        if self._mic is None:
            raise RuntimeError(
                "Mic unavailable. On Steam Deck run:\n"
                "  sudo pacman -S pipewire-pulse espeak-ng"
            )

        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
            try:
                return self._recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_limit,
                )
            except sr.WaitTimeoutError:
                raise RuntimeError("Didn't catch anything — try again, kehd.")

    def listen(self, on_status: Optional[Callable[[str], None]] = None) -> str:
        """
        Block until the user speaks (or timeout). Returns transcribed text.
        Raises RuntimeError on missing deps or recognition failure.
        """
        if not stt_available():
            raise RuntimeError(
                "Voice input needs:\n"
                "  pip install SpeechRecognition\n"
                "  sudo pacman -S pipewire-pulse   # Steam Deck mic"
            )

        import speech_recognition as sr

        self._ensure()
        assert self._recognizer is not None

        audio = self._capture_audio(on_status)

        if on_status:
            on_status("transcribing")

        vosk_model = os.getenv("CHAHLIE_VOSK_MODEL", "").strip()
        if vosk_model and os.path.isdir(vosk_model):
            try:
                import json
                raw = self._recognizer.recognize_vosk(audio)
                text = json.loads(raw).get("text", "").strip()
                if text:
                    return text
            except sr.UnknownValueError:
                raise RuntimeError("Couldn't make out the words.")
            except Exception:
                pass

        try:
            return self._recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            raise RuntimeError("Couldn't make out the words.")
        except sr.RequestError as exc:
            raise RuntimeError(f"Speech service unavailable: {exc}") from exc


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------

class SpeechSpeaker:
    """Speak agent replies aloud — espeak-ng on Linux, pyttsx3 elsewhere."""

    def __init__(self, rate: int = 175, volume: float = 0.9):
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._lock = threading.Lock()
        self._speaking = False
        self._proc: Optional[subprocess.Popen] = None
        self._espeak = shutil.which("espeak-ng") or shutil.which("espeak")

    def _ensure(self) -> None:
        if self._engine is not None or self._espeak:
            return
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self.rate)
        self._engine.setProperty("volume", self.volume)
        voices = self._engine.getProperty("voices") or []
        for voice in voices:
            name = (voice.name or "").lower()
            if "english" in name or "en" in (voice.id or "").lower():
                self._engine.setProperty("voice", voice.id)
                break

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=1)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
            self._proc = None
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
            self._speaking = False

    def _speak_espeak(self, text: str) -> None:
        assert self._espeak
        # espeak-ng rate: ~80 default; map our 175 wpm-ish to ~160
        wpm = min(300, max(80, self.rate))
        self._proc = subprocess.Popen(
            [self._espeak, "-s", str(wpm), text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._proc.wait()
        self._proc = None

    def speak(self, text: str, block: bool = False) -> None:
        """Speak *text*. Runs in a background thread unless block=True."""
        if not text or not text.strip():
            return
        if not tts_available():
            raise RuntimeError(
                "Voice output needs: sudo pacman -S espeak-ng   # Steam Deck"
            )

        cleaned = _clean_for_speech(text)
        if not cleaned:
            return

        def _run() -> None:
            with self._lock:
                self._speaking = True
                try:
                    self._ensure()
                    if self._espeak:
                        self._speak_espeak(cleaned)
                    elif self._engine is not None:
                        self._engine.say(cleaned)
                        self._engine.runAndWait()
                finally:
                    self._speaking = False

        if block:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()


def _clean_for_speech(text: str, max_chars: int = 600) -> str:
    """Strip markdown/code so TTS doesn't read asterisks and backticks."""
    import re
    t = text
    t = re.sub(r"```[\s\S]*?```", " code block. ", t)
    t = re.sub(r"`[^`]+`", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[#*_~>|]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > max_chars:
        t = t[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return t


# ---------------------------------------------------------------------------
# Convenience facade used by the Deck UI
# ---------------------------------------------------------------------------

class VoiceManager:
    """Single object the UI talks to for mic + speaker."""

    def __init__(self):
        from .config import (
            VOICE_ENABLED,
            VOICE_TTS_ENABLED,
            VOICE_LANGUAGE,
            VOICE_LISTEN_TIMEOUT,
            VOICE_TTS_RATE,
        )
        self.enabled = VOICE_ENABLED
        self.tts_enabled = VOICE_TTS_ENABLED
        self._listener: Optional[SpeechListener] = None
        self._speaker: Optional[SpeechSpeaker] = None
        self._language = VOICE_LANGUAGE
        self._timeout = VOICE_LISTEN_TIMEOUT
        self._tts_rate = VOICE_TTS_RATE

    @property
    def can_listen(self) -> bool:
        return self.enabled and stt_available()

    @property
    def can_speak(self) -> bool:
        return self.tts_enabled and tts_available()

    def listen(self, on_status: Optional[Callable[[str], None]] = None) -> str:
        if self._listener is None:
            self._listener = SpeechListener(
                language=self._language,
                timeout=self._timeout,
            )
        return self._listener.listen(on_status=on_status)

    def speak(self, text: str) -> None:
        if not self.can_speak:
            return
        if self._speaker is None:
            self._speaker = SpeechSpeaker(rate=self._tts_rate)
        self._speaker.speak(text)

    def stop_speaking(self) -> None:
        if self._speaker:
            self._speaker.stop()

    def status_line(self) -> str:
        bits = []
        if self.can_listen:
            rec = _linux_recorder()
            bits.append(f"mic ({os.path.basename(rec) if rec else 'pyaudio'})")
        elif self.enabled:
            bits.append("mic (needs pipewire-pulse)")
        if self.can_speak:
            bits.append("speaker (espeak)")
        elif self.tts_enabled:
            bits.append("speaker (needs espeak-ng)")
        return " | ".join(bits) if bits else "voice off"
