"""
Voice input/output for Chahlie — talk to your coding agent.

Uses SpeechRecognition for STT and pyttsx3 for TTS on Linux/Steam Deck.
All heavy imports are lazy so the classic CLI stays fast when voice is off.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Availability probes (no hard deps at import time)
# ---------------------------------------------------------------------------

_STT_AVAILABLE: Optional[bool] = None
_TTS_AVAILABLE: Optional[bool] = None


def stt_available() -> bool:
    """Return True if speech-to-text dependencies are importable."""
    global _STT_AVAILABLE
    if _STT_AVAILABLE is None:
        try:
            import speech_recognition  # noqa: F401
            _STT_AVAILABLE = True
        except ImportError:
            _STT_AVAILABLE = False
    return _STT_AVAILABLE


def tts_available() -> bool:
    """Return True if text-to-speech dependencies are importable."""
    global _TTS_AVAILABLE
    if _TTS_AVAILABLE is None:
        try:
            import pyttsx3  # noqa: F401
            _TTS_AVAILABLE = True
        except ImportError:
            _TTS_AVAILABLE = False
    return _TTS_AVAILABLE


def voice_available() -> bool:
    return stt_available() or tts_available()


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
        self._mic = sr.Microphone()

    def listen(self, on_status: Optional[Callable[[str], None]] = None) -> str:
        """
        Block until the user speaks (or timeout). Returns transcribed text.
        Raises RuntimeError on missing deps or recognition failure.
        """
        if not stt_available():
            raise RuntimeError(
                "Voice input needs: pip install SpeechRecognition PyAudio"
            )

        import speech_recognition as sr

        self._ensure()
        assert self._recognizer is not None
        assert self._mic is not None

        if on_status:
            on_status("listening")

        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
            try:
                audio = self._recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_limit,
                )
            except sr.WaitTimeoutError:
                raise RuntimeError("Didn't catch anything — try again, kehd.")

        if on_status:
            on_status("transcribing")

        # Offline first (Vosk) when model path is set, else Google web API.
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
                pass  # fall through to cloud STT

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
    """Speak agent replies aloud via pyttsx3 (espeak on Linux)."""

    def __init__(self, rate: int = 175, volume: float = 0.9):
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._lock = threading.Lock()
        self._speaking = False

    def _ensure(self) -> None:
        if self._engine is not None:
            return
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self.rate)
        self._engine.setProperty("volume", self.volume)
        # Prefer a clear English voice when available.
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
        if self._engine is None:
            return
        with self._lock:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._speaking = False

    def speak(self, text: str, block: bool = False) -> None:
        """Speak *text*. Runs in a background thread unless block=True."""
        if not text or not text.strip():
            return
        if not tts_available():
            raise RuntimeError("Voice output needs: pip install pyttsx3")

        cleaned = _clean_for_speech(text)
        if not cleaned:
            return

        def _run() -> None:
            with self._lock:
                self._speaking = True
                try:
                    self._ensure()
                    assert self._engine is not None
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
            bits.append("mic")
        elif self.enabled:
            bits.append("mic (install SpeechRecognition)")
        if self.can_speak:
            bits.append("speaker")
        elif self.tts_enabled:
            bits.append("speaker (install pyttsx3)")
        return " | ".join(bits) if bits else "voice off"
