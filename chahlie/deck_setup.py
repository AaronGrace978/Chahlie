"""First-run setup helpers for the Steam Deck UI."""

from __future__ import annotations

import os
import re
from pathlib import Path


def env_file_path() -> Path:
    custom = os.getenv("CHAHLIE_ENV_FILE", "").strip()
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".local" / "share" / "chahlie" / ".env"


def sanitize_api_key(key: str) -> str:
    """Strip whitespace and accidental quotes from pasted keys."""
    key = (key or "").strip()
    if (key.startswith('"') and key.endswith('"')) or (
        key.startswith("'") and key.endswith("'")
    ):
        key = key[1:-1].strip()
    return key


def verify_api_key(api_key: str) -> tuple[bool, str]:
    """Ping Ollama Cloud to confirm the key works. Returns (ok, error_message)."""
    import requests

    key = sanitize_api_key(api_key)
    if not key or len(key) < 8:
        return False, "That key looks too short."

    try:
        resp = requests.get(
            "https://ollama.com/api/tags",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20,
        )
    except requests.RequestException as exc:
        return False, f"Can't reach Ollama Cloud: {exc}"

    if resp.status_code == 401:
        return False, (
            "401 Unauthorized — key is wrong or expired.\n"
            "Get a fresh key at ollama.com/settings/keys"
        )
    if resp.status_code >= 400:
        return False, f"Ollama returned error {resp.status_code}. Try again in a minute."

    return True, ""


def needs_api_key_setup() -> bool:
    """True when cloud backend is selected but no real API key is set."""
    backend = os.getenv("CHAHLIE_BACKEND", "ollama-cloud")
    if backend != "ollama-cloud":
        return False
    key = sanitize_api_key(os.getenv("OLLAMA_API_KEY") or "")
    if not key:
        return True
    placeholders = (
        "your-ollama-cloud-api-key-here",
        "your-key-here",
        "changeme",
        "xxx",
    )
    return key.lower() in placeholders or key.startswith("your-")


def save_api_key(api_key: str, env_path: Path | None = None) -> Path:
    """Write OLLAMA_API_KEY into the deck config file."""
    api_key = sanitize_api_key(api_key)
    path = env_path or env_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = (
            "CHAHLIE_BACKEND=ollama-cloud\n"
            "OLLAMA_CLOUD_MODEL=qwen3.5:cloud\n"
            "CHAHLIE_VOICE=true\n"
            "CHAHLIE_VOICE_TTS=true\n"
            "OLLAMA_API_KEY=\n"
        )

    if re.search(r"^OLLAMA_API_KEY=", text, flags=re.MULTILINE):
        text = re.sub(
            r"^OLLAMA_API_KEY=.*$",
            f"OLLAMA_API_KEY={api_key}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = text.rstrip() + f"\nOLLAMA_API_KEY={api_key}\n"

    if not re.search(r"^CHAHLIE_BACKEND=", text, flags=re.MULTILINE):
        text = "CHAHLIE_BACKEND=ollama-cloud\n" + text

    path.write_text(text, encoding="utf-8")
    os.environ["OLLAMA_API_KEY"] = api_key
    os.environ["CHAHLIE_BACKEND"] = "ollama-cloud"
    return path


def reload_config() -> None:
    """Reload config module after .env changes."""
    from importlib import reload
    from . import config
    reload(config)
