"""
Chahlie's Project Auto-Primer

Runs once when the agent starts in a directory it hasn't seen before. Scans
the filesystem for cheap signals (README, build manifests, top-level layout)
and synthesizes a short ProjectContext summary that gets injected into the
system prompt, so Chahlie doesn't spend the first 5 turns asking
"what IS this project?".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


# Max characters per snippet we pull from README/manifests; keeps the prompt
# from exploding if the user has a 50KB README.
_SNIPPET_CHARS = 1200


def _read_head(path: Path, chars: int = _SNIPPET_CHARS) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    return text[:chars]


def _detect_language_and_framework(root: Path) -> Dict[str, str]:
    """Best-effort detection based on files present at the project root."""
    markers: List[tuple[str, str, str]] = [
        ("pyproject.toml", "Python", ""),
        ("setup.py",       "Python", ""),
        ("requirements.txt", "Python", ""),
        ("package.json",   "JavaScript/TypeScript", ""),
        ("tsconfig.json",  "TypeScript", ""),
        ("Cargo.toml",     "Rust", ""),
        ("go.mod",         "Go", ""),
        ("pom.xml",        "Java", "Maven"),
        ("build.gradle",   "Java/Kotlin", "Gradle"),
        ("Gemfile",        "Ruby", ""),
        ("composer.json",  "PHP", ""),
        ("mix.exs",        "Elixir", ""),
        ("Dockerfile",     "", "Docker"),
    ]
    language = ""
    framework = ""
    for filename, lang, fw in markers:
        if (root / filename).exists():
            if lang and not language:
                language = lang
            if fw and not framework:
                framework = fw

    # Framework guesses from package.json
    pkg_path = root / "package.json"
    if pkg_path.exists() and not framework:
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for fw_name in ("next", "react", "vue", "svelte", "astro", "express", "fastify", "nestjs"):
                if fw_name in deps:
                    framework = fw_name
                    break
        except Exception:
            pass

    # Framework guesses from pyproject/requirements
    reqs = ""
    for f in ("pyproject.toml", "requirements.txt", "setup.py"):
        p = root / f
        if p.exists():
            reqs += _read_head(p, 4000).lower()
    if not framework and reqs:
        for fw_name in ("django", "flask", "fastapi", "starlette", "pyramid", "streamlit", "click", "typer"):
            if fw_name in reqs:
                framework = fw_name
                break

    return {"language": language, "framework": framework}


def _top_level_layout(root: Path, max_items: int = 25) -> List[str]:
    """Sorted list of top-level entries, dirs-first, hidden excluded."""
    try:
        entries = [
            p for p in root.iterdir()
            if not p.name.startswith(".") and p.name not in ("node_modules", "__pycache__", "dist", "build", "target")
        ]
    except Exception:
        return []
    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    out: List[str] = []
    for p in entries[:max_items]:
        out.append(("📁 " if p.is_dir() else "📄 ") + p.name)
    if len(entries) > max_items:
        out.append(f"... +{len(entries) - max_items} more")
    return out


def _git_summary(root: Path) -> Dict[str, str]:
    """Grab basic git state without shelling out (reads .git/HEAD)."""
    head = root / ".git" / "HEAD"
    if not head.exists():
        return {}
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref: refs/heads/"):
            return {"branch": ref.split("refs/heads/", 1)[1]}
        return {"branch": ref[:12] + " (detached)"}
    except Exception:
        return {}


def prime_project(project_path: Optional[str] = None) -> Dict[str, object]:
    """Build a summary dict describing the project at `project_path`.

    Safe to call on any directory; returns {"primed": False} if the path
    doesn't exist.
    """
    root = Path(project_path or ".").resolve()
    if not root.exists() or not root.is_dir():
        return {"primed": False, "reason": "path not a directory"}

    info = _detect_language_and_framework(root)
    layout = _top_level_layout(root)
    git = _git_summary(root)

    readme_snippet = ""
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.exists():
            readme_snippet = _read_head(p)
            break

    manifests: Dict[str, str] = {}
    for manifest_name in ("pyproject.toml", "package.json", "Cargo.toml", "go.mod"):
        p = root / manifest_name
        if p.exists():
            manifests[manifest_name] = _read_head(p, 600)

    return {
        "primed": True,
        "path": str(root),
        "name": root.name,
        "language": info["language"],
        "framework": info["framework"],
        "branch": git.get("branch", ""),
        "layout": layout,
        "readme_snippet": readme_snippet,
        "manifests": manifests,
    }


def render_primer_prompt(primer: Dict[str, object]) -> str:
    """Render a primer dict into a short text block suitable for the system prompt."""
    if not primer.get("primed"):
        return ""

    lines: List[str] = ["PROJECT CONTEXT (auto-detected - don't ask the user what you already know):"]
    lines.append(f"- Name: {primer.get('name')}")
    if primer.get("language"):
        lines.append(f"- Language: {primer.get('language')}")
    if primer.get("framework"):
        lines.append(f"- Framework: {primer.get('framework')}")
    if primer.get("branch"):
        lines.append(f"- Git branch: {primer.get('branch')}")

    layout = primer.get("layout") or []
    if layout:
        lines.append("- Top-level layout:")
        for entry in layout[:12]:
            lines.append(f"    {entry}")

    readme = primer.get("readme_snippet") or ""
    if readme:
        lines.append("- README (first ~1KB):")
        for raw in readme.splitlines()[:20]:
            lines.append(f"    {raw}")

    return "\n".join(lines)
