"""
Fuzzy file-path matching for 'did you mean' hints.

Used when a tool complains 'file not found' - we scan the project's top-level
layout (from the primer) and common subdirectories for a close match and
return a short suggestion string, keeping the LLM from wasting a turn on
a typo it could have self-corrected.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import List, Optional

# Skip these noisy dirs when scanning for candidates.
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build", "target",
    ".venv", "venv", ".mypy_cache", ".pytest_cache", ".tox", ".next",
    ".chahlie",
}

# Don't scan enormous trees; a typo-suggester only needs a few hundred files.
_MAX_FILES = 2000


def _collect_files(root: Path) -> List[str]:
    out: List[str] = []
    try:
        for p in root.rglob("*"):
            if len(out) >= _MAX_FILES:
                break
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            try:
                out.append(str(p.relative_to(root)))
            except ValueError:
                out.append(str(p))
    except Exception:
        pass
    return out


def suggest_path(missing: str, *, root: Optional[str] = None, top_k: int = 3) -> List[str]:
    """Return up to `top_k` best candidate paths for a missing one."""
    root_path = Path(root or ".").resolve()
    candidates = _collect_files(root_path)
    if not candidates:
        return []

    # difflib compares whole strings. Compare both the full path and the
    # basename so 'agnt.py' matches 'chahlie/agent.py' even though the
    # dirname differs.
    basenames = {c: Path(c).name for c in candidates}
    miss_base = Path(missing).name

    full_matches = difflib.get_close_matches(missing, candidates, n=top_k, cutoff=0.6)
    base_matches = difflib.get_close_matches(
        miss_base, list(basenames.values()), n=top_k, cutoff=0.6,
    )
    # Reverse-map basenames back to full paths, dedupe preserving order.
    seen = set()
    out: List[str] = []
    for match in full_matches:
        if match not in seen:
            out.append(match); seen.add(match)
    for base in base_matches:
        for candidate, b in basenames.items():
            if b == base and candidate not in seen:
                out.append(candidate); seen.add(candidate)
                break
    return out[:top_k]


def format_suggestions(missing: str, *, root: Optional[str] = None) -> str:
    """Return a 'Did you mean: ...' suffix, or empty string if no close match."""
    hits = suggest_path(missing, root=root)
    if not hits:
        return ""
    return " Did you mean: " + ", ".join(f"'{h}'" for h in hits) + "?"
