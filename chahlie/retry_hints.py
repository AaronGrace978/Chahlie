"""
Smart retry hints for `run_command` failures.

When a shell command fails with a recognizable pattern, append a concrete
suggestion the LLM can act on in its next turn. We DON'T auto-run the fix -
silent command rewriting is a great way to do damage - we just surface the
hint so Chahlie (or the user) can choose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RetryHint:
    pattern: str
    hint: str


# Each rule: (regex over stderr+stdout, human-readable hint).
# Keep narrow - false positives here would be worse than no hint.
_RULES: List[tuple[re.Pattern, str]] = [
    (
        re.compile(r"has no upstream branch", re.I),
        "Try: git push -u origin HEAD   (sets upstream on first push)",
    ),
    (
        re.compile(r"Your branch is behind.*git pull", re.I | re.S),
        "Try: git pull --rebase   (then re-run your push)",
    ),
    (
        re.compile(r"Please tell me who you are", re.I),
        "Set git identity: git config user.email 'you@example.com' && git config user.name 'You'",
    ),
    (
        re.compile(r"Permission denied \(publickey\)", re.I),
        "SSH key not accepted - switch the remote to HTTPS or add the key to your git host.",
    ),
    (
        re.compile(r"ModuleNotFoundError: No module named '([^']+)'"),
        "Install the missing module: pip install {0}",
    ),
    (
        re.compile(r"command not found: (\w+)", re.I),
        "'{0}' isn't on PATH. Install it or try its absolute path.",
    ),
    (
        re.compile(r"'(\w+)' is not recognized as an internal or external command", re.I),
        "'{0}' isn't on PATH (Windows). Install it or use the full path.",
    ),
    (
        re.compile(r"EACCES|permission denied", re.I),
        "Permission denied. DO NOT just prefix with sudo - check file ownership/mode first.",
    ),
    (
        re.compile(r"ENOENT.*node_modules/\.bin/"),
        "Missing npm dependency. Run: npm install",
    ),
    (
        re.compile(r"EADDRINUSE.*:(\d+)"),
        "Port {0} is already in use. Kill the process holding it or pick another port.",
    ),
    (
        re.compile(r"fatal: not a git repository", re.I),
        "Not a git repo. Run 'git init' first, or cd into a repo.",
    ),
    (
        re.compile(r"merge conflict", re.I),
        "Merge conflict detected - resolve the marked files, then git add + git commit.",
    ),
    (
        re.compile(r"pytest: error: unrecognized arguments"),
        "Check pytest flags - some need a space ('--tb=short' not '--tbshort').",
    ),
]


def suggest_retry(stdout: str, stderr: str) -> Optional[str]:
    """Return a one-line hint string, or None if no rule fires."""
    haystack = (stderr or "") + "\n" + (stdout or "")
    for pattern, hint in _RULES:
        m = pattern.search(haystack)
        if m:
            try:
                return hint.format(*m.groups())
            except (IndexError, KeyError):
                return hint
    return None
