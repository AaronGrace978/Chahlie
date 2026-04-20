"""
Diff rendering helpers for Chahlie.

Used by write_file / edit_file to show a compact unified diff in the tool
output, so the user (and the LLM reading the tool_result) can see exactly
what changed instead of just "wrote N characters to path".

Pure stdlib (`difflib`). Output is plain text with +/- line prefixes; the
UI layer can colorize later if it wants.
"""

from __future__ import annotations

import difflib
from typing import List


def render_unified_diff(old: str, new: str, path: str, *, context: int = 3, max_lines: int = 80) -> str:
    """Render a unified diff, truncating very long diffs to `max_lines` body lines."""
    if old == new:
        return ""

    diff = list(difflib.unified_diff(
        old.splitlines(keepends=False),
        new.splitlines(keepends=False),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context,
        lineterm="",
    ))
    if not diff:
        return ""

    header, body = diff[:2], diff[2:]
    if len(body) > max_lines:
        body = body[:max_lines] + [f"... (+{len(diff) - 2 - max_lines} more lines truncated)"]
    return "\n".join(header + body)


def summarize_diff(old: str, new: str) -> str:
    """One-line summary: '+7 / -3 lines' style."""
    matcher = difflib.SequenceMatcher(a=old.splitlines(), b=new.splitlines())
    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            added += (j2 - j1)
        if tag in ("delete", "replace"):
            removed += (i2 - i1)
    if added == 0 and removed == 0:
        return "no line-level changes"
    return f"+{added} / -{removed} lines"
