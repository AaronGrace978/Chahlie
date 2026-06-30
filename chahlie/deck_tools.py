"""
Steam Deck native utility tools for Chahlie.

These tools let Chahlie control the Deck like a personal assistant:
launch games/apps, adjust volume/brightness, check battery, run Steam commands, etc.
Only registered when CHAHLIE_DECK_MODE=true.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from pathlib import Path

from .tools import ToolResult, _check_command_safety, _approval_hook, REQUIRE_APPROVAL


def _run(cmd: list[str] | str, timeout: int = 30) -> tuple[bool, str, str]:
    """Run a subprocess and return (ok, stdout, stderr)."""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        ok = result.returncode == 0
        return ok, out, err
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as exc:
        return False, "", str(exc)


def _maybe_approve(command: str) -> ToolResult | None:
    """Return a blocked ToolResult if approval is denied, else None."""
    reason = _check_command_safety(command)
    if not reason:
        return None
    if REQUIRE_APPROVAL:
        if _approval_hook is None:
            return ToolResult(
                success=False, output="",
                error=f"BLOCKED: command looks dangerous ({reason}). "
                      "Approve in the popup or rephrase with a safer approach.",
            )
        if not _approval_hook(command, reason):
            return ToolResult(success=False, output="", error=f"User denied: {reason}")
    return None


DECK_TOOL_DEFINITIONS = [
    {
        "name": "deck_launch",
        "description": (
            "Launch an app, game, or URL on the Steam Deck. "
            "Use for 'open Steam', 'launch Hades', 'start Firefox', 'open Dolphin'. "
            "target_type: auto (guess), steam (app id or name), flatpak, desktop, url."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "App name, Steam app ID, flatpak ID, .desktop name, or URL",
                },
                "target_type": {
                    "type": "string",
                    "enum": ["auto", "steam", "flatpak", "desktop", "url"],
                    "description": "How to interpret target (default auto)",
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "deck_system_info",
        "description": (
            "Get Steam Deck system status: battery, disk space, memory, uptime, "
            "SteamOS version. Use when asked about storage, battery, or system health."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "deck_set_volume",
        "description": "Set system volume (0-100 percent) or mute/unmute the Deck speakers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Volume 0-100. Use -1 to toggle mute.",
                },
            },
            "required": ["level"],
        },
    },
    {
        "name": "deck_set_brightness",
        "description": "Set screen brightness (1-100 percent) on the Steam Deck.",
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Brightness 1-100 percent",
                },
            },
            "required": ["level"],
        },
    },
    {
        "name": "deck_steam",
        "description": (
            "Steam-specific actions: status (is Steam running), "
            "launch APPID, library (recent games), bigpicture, desktop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "launch", "library", "bigpicture", "desktop"],
                    "description": "Steam action to perform",
                },
                "app_id": {
                    "type": "string",
                    "description": "Steam app ID (required for launch)",
                },
            },
            "required": ["action"],
        },
    },
]


_STEAM_ALIASES = {
    "steam": "steam",
    "big picture": "bigpicture",
    "bigpicture": "bigpicture",
    "desktop mode": "desktop",
    "desktop": "desktop",
}


def deck_launch(target: str, target_type: str = "auto") -> ToolResult:
    target = (target or "").strip()
    if not target:
        return ToolResult(success=False, output="", error="No launch target given")

    ttype = (target_type or "auto").lower()

    # URL
    if ttype == "url" or target.startswith(("http://", "https://", "steam://")):
        cmd = f'xdg-open "{target}"'
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        return ToolResult(
            success=ok,
            output=f"Opened {target}" if ok else "",
            error=err or None,
        )

    # Steam app ID (numeric)
    if ttype in ("auto", "steam") and re.fullmatch(r"\d{3,8}", target):
        cmd = f'steam -applaunch {target}'
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        return ToolResult(
            success=ok,
            output=f"Launching Steam app {target}" + (f"\n{out}" if out else ""),
            error=err or None,
        )

    # Flatpak
    if ttype == "flatpak" or (ttype == "auto" and "." in target and " " not in target):
        cmd = f'flatpak run {target}'
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        if ok or ttype == "flatpak":
            return ToolResult(
                success=ok,
                output=f"Launched flatpak {target}" if ok else out,
                error=err or None,
            )

    # Desktop entry by name
    name_lower = target.lower().replace(".desktop", "")
    desktop_dirs = [
        Path.home() / ".local/share/applications",
        Path("/usr/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
        Path.home() / ".local/share/flatpak/exports/share/applications",
    ]
    for d in desktop_dirs:
        if not d.is_dir():
            continue
        for entry in d.glob("*.desktop"):
            stem = entry.stem.lower()
            if name_lower in stem or stem in name_lower:
                cmd = f'gtk-launch "{entry.stem}"'
                blocked = _maybe_approve(cmd)
                if blocked:
                    return blocked
                ok, out, err = _run(cmd)
                return ToolResult(
                    success=ok,
                    output=f"Launched {entry.stem}" if ok else out,
                    error=err or None,
                )

    # Steam by name
    if ttype in ("auto", "steam"):
        cmd = f'steam -applaunch {target}'
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        if ok:
            return ToolResult(success=True, output=f"Launched {target}")

    # Last resort: xdg-open as search term
    cmd = f'xdg-open "{target}"'
    blocked = _maybe_approve(cmd)
    if blocked:
        return blocked
    ok, out, err = _run(cmd)
    return ToolResult(
        success=ok,
        output=f"Tried to open {target}" if ok else out,
        error=err or f"Could not launch {target}",
    )


def deck_system_info() -> ToolResult:
    lines: list[str] = []

    ok, out, _ = _run("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME")
    if ok and out:
        lines.append(out.replace("PRETTY_NAME=", "").strip('"'))

    ok, out, _ = _run("uptime -p 2>/dev/null || uptime")
    if ok:
        lines.append(f"Uptime: {out}")

    for bat in sorted(glob.glob("/sys/class/power_supply/BAT*/capacity")):
        try:
            cap = Path(bat).read_text().strip()
            status_path = bat.replace("capacity", "status")
            status = Path(status_path).read_text().strip() if Path(status_path).exists() else "?"
            lines.append(f"Battery: {cap}% ({status})")
        except OSError:
            pass

    ok, out, _ = _run("df -h / /home 2>/dev/null | tail -n +2")
    if ok:
        lines.append("Disk:\n" + out)

    ok, out, _ = _run("free -h 2>/dev/null | head -3")
    if ok:
        lines.append("Memory:\n" + out)

    ok, out, _ = _run("pgrep -x steam >/dev/null && echo running || echo stopped")
    if ok:
        lines.append(f"Steam: {out}")

    return ToolResult(success=True, output="\n".join(lines) or "No system info available")


def deck_set_volume(level: int) -> ToolResult:
    if level == -1:
        cmd = "pactl set-sink-mute @DEFAULT_SINK@ toggle"
    else:
        level = max(0, min(100, int(level)))
        cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {level}%"
    if not shutil.which("pactl"):
        return ToolResult(success=False, output="", error="pactl not found (PulseAudio/PipeWire required)")
    ok, out, err = _run(cmd)
    return ToolResult(
        success=ok,
        output=f"Volume set to {level}%" if level >= 0 else "Toggled mute",
        error=err or None,
    )


def deck_set_brightness(level: int) -> ToolResult:
    level = max(1, min(100, int(level)))
    if shutil.which("brightnessctl"):
        ok, out, err = _run(f"brightnessctl set {level}%")
        return ToolResult(success=ok, output=f"Brightness {level}%", error=err or None)
    # Steam Deck fallback via sysfs if present
    backlight = "/sys/class/backlight/amdgpu_bl1/brightness"
    max_path = "/sys/class/backlight/amdgpu_bl1/max_brightness"
    if os.path.isfile(backlight) and os.path.isfile(max_path):
        try:
            max_val = int(Path(max_path).read_text().strip())
            val = max(1, int(max_val * level / 100))
            Path(backlight).write_text(str(val))
            return ToolResult(success=True, output=f"Brightness ~{level}%")
        except OSError as exc:
            return ToolResult(success=False, output="", error=str(exc))
    return ToolResult(
        success=False, output="",
        error="brightnessctl not installed and no amdgpu backlight found",
    )


def deck_steam(action: str, app_id: str = "") -> ToolResult:
    action = (action or "status").lower()
    if action in _STEAM_ALIASES:
        action = _STEAM_ALIASES[action]

    if action == "status":
        ok, out, _ = _run("pgrep -x steam >/dev/null && echo running || echo stopped")
        return ToolResult(success=True, output=f"Steam is {out}")

    if action == "launch":
        if not app_id:
            return ToolResult(success=False, output="", error="app_id required for launch")
        cmd = f"steam -applaunch {app_id}"
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        return ToolResult(
            success=ok,
            output=f"Launching Steam app {app_id}",
            error=err or None,
        )

    if action == "library":
        steam_dir = Path.home() / ".steam/steam"
        shortcuts = steam_dir / "userdata"
        ok, out, _ = _run(
            "find ~/.steam/steam/steamapps -name '*.acf' -maxdepth 1 2>/dev/null "
            "| head -20 | xargs -I{} basename {} .acf 2>/dev/null"
        )
        return ToolResult(success=True, output=out or "No recent library info found")

    if action == "bigpicture":
        cmd = "steam -bigpicture"
        blocked = _maybe_approve(cmd)
        if blocked:
            return blocked
        ok, out, err = _run(cmd)
        return ToolResult(success=ok, output="Opening Steam Big Picture", error=err or None)

    if action == "desktop":
        return ToolResult(
            success=True,
            output="Switch to Desktop Mode from the Steam menu (Power → Switch to Desktop).",
        )

    return ToolResult(success=False, output="", error=f"Unknown steam action: {action}")


DECK_TOOL_DISPATCH = {
    "deck_launch": lambda args: deck_launch(
        args.get("target", ""), args.get("target_type", "auto"),
    ),
    "deck_system_info": lambda args: deck_system_info(),
    "deck_set_volume": lambda args: deck_set_volume(int(args.get("level", 50))),
    "deck_set_brightness": lambda args: deck_set_brightness(int(args.get("level", 50))),
    "deck_steam": lambda args: deck_steam(args.get("action", "status"), args.get("app_id", "")),
}
