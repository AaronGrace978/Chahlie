"""
Chahlie's Agentic Tools
The hands that do the work
"""

import os
import re
import subprocess
import glob as glob_module
import webbrowser
import urllib.parse
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass

from .verifier import verify_file
from .config import REQUIRE_APPROVAL


# --- Approval hook (set by UI layer to prompt user; default: auto-deny danger) ---
# Signature: (command: str, reason: str) -> bool. True means approved.
_approval_hook: Optional[Callable[[str, str], bool]] = None


def set_approval_hook(hook: Optional[Callable[[str, str], bool]]) -> None:
    """UI layer calls this once at startup to install an interactive prompter.

    If no hook is installed and approval is required, dangerous commands are
    refused rather than silently executed.
    """
    global _approval_hook
    _approval_hook = hook


# Patterns that should require explicit user approval before running
_DANGER_PATTERNS = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)"), "recursive force delete"),
    (re.compile(r"\bgit\s+push\s+(--force|-f)\b"),                        "git force-push"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"),                             "git hard reset"),
    (re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"),                          "git clean -f"),
    (re.compile(r"\b(drop|truncate)\s+(table|database|schema)\b", re.I),  "destructive SQL"),
    (re.compile(r"\bdd\s+if="),                                           "raw disk dd"),
    (re.compile(r"\b(mkfs|format)\b"),                                    "filesystem format"),
    (re.compile(r">\s*/dev/(sd|nvme|disk|hd)"),                           "write to raw device"),
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\}"),                              "fork bomb"),
    (re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b"),                     "system shutdown"),
    (re.compile(r"\bsudo\s+"),                                            "sudo elevation"),
    (re.compile(r"\bchmod\s+(-R\s+)?[0-7]*777"),                          "chmod 777"),
]


def _check_command_safety(command: str) -> Optional[str]:
    """Return the reason string if command is dangerous, else None."""
    for pattern, reason in _DANGER_PATTERNS:
        if pattern.search(command):
            return reason
    return None


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    output: str
    error: Optional[str] = None


# Tool definitions for Claude
TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use this to understand code before making changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a path. Use to explore the codebase structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list (defaults to current directory)"
                }
            },
            "required": []
        }
    },
    {
        "name": "search_files",
        "description": "Search for files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g., '**/*.py', 'src/**/*.js')"
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in (defaults to current directory)"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "search_content",
        "description": "Search for text content within files. Like grep but friendlier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The text to search for"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g., '*.py')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command. Use for git, npm, pip, tests, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Directory to run the command in"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "create_directory",
        "description": "Create a new directory (and parent directories if needed).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to create"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "open_browser",
        "description": "Open a URL in the user's default web browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to open (e.g., 'https://google.com')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web using Google. Opens the search results in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "verify_code",
        "description": (
            "Run static checks on a file (syntax + undefined names for Python; "
            "syntax for JS/TS/Go/Rust/JSON/YAML when toolchain is available). "
            "Use this after writing code to catch typos BEFORE declaring done."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to verify"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "edit_file",
        "description": (
            "Make a surgical edit to an existing file by replacing one exact "
            "string with another. MUCH cheaper than rewriting the whole file "
            "and less error-prone. `old_string` must appear EXACTLY ONCE in the "
            "file (include enough context to make it unique). Python files are "
            "auto-verified after edit, same as write_file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "old_string": {
                    "type": "string",
                    "description": "Exact text to replace (must appear exactly once)"
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text"
                }
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "delegate",
        "description": (
            "Spawn a short-lived sub-agent to handle an exploration/search task "
            "without polluting your main context. Use for 'find all X', 'summarize "
            "directory Y', etc. The sub-agent has NO memory and returns one "
            "synthesized answer. Don't delegate your core implementation work."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "A self-contained task description for the sub-agent."
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "run_tests",
        "description": (
            "Auto-detect and run the project's test suite (pytest / npm test / "
            "cargo test / go test). Use after making code changes to confirm "
            "nothing broke semantically (syntax-level checks won't catch logic bugs)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Optional: specific test file/dir to run"
                }
            },
            "required": []
        }
    },
]


def read_file(path: str) -> ToolResult:
    """Read a file's contents"""
    try:
        filepath = Path(path)
        if not filepath.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}"
            )
        
        content = filepath.read_text(encoding='utf-8')
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def _maybe_verify(path: str, base_msg: str) -> ToolResult:
    """Shared post-write verification logic. Returns the tool result."""
    p = Path(path)
    result = verify_file(str(p))
    if result.errors:
        return ToolResult(
            success=False,
            output=base_msg,
            error=(
                "File was written but has errors you must fix before "
                "proceeding:\n" + result.format()
            ),
        )
    if result.warnings:
        return ToolResult(
            success=True,
            output=(
                base_msg
                + "\n\nVERIFICATION WARNINGS (fix these before declaring done):\n"
                + result.format()
            ),
        )
    return ToolResult(success=True, output=base_msg)


def write_file(path: str, content: str) -> ToolResult:
    """Write content to a file.

    For Python files, automatically runs verification afterwards. If the file
    has a syntax error, the tool reports failure so the agent loop surfaces
    the error and must fix it before continuing. Undefined-name warnings are
    included in the output but do not fail the write.
    """
    try:
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding='utf-8')
        base_msg = f"Successfully wrote {len(content)} characters to {path}"
        return _maybe_verify(str(filepath), base_msg)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def edit_file(path: str, old_string: str, new_string: str) -> ToolResult:
    """Surgical edit: replace exactly one occurrence of old_string with new_string."""
    try:
        filepath = Path(path)
        if not filepath.exists():
            return ToolResult(
                success=False, output="",
                error=f"File not found: {path}. Use write_file to create new files.",
            )
        original = filepath.read_text(encoding="utf-8")
        count = original.count(old_string)
        if count == 0:
            return ToolResult(
                success=False, output="",
                error=(
                    "old_string not found. Check whitespace/indentation exactly "
                    "matches the file, and include enough context to make it unique."
                ),
            )
        if count > 1:
            return ToolResult(
                success=False, output="",
                error=(
                    f"old_string appears {count} times. Add more surrounding "
                    "context so exactly one match is found."
                ),
            )
        updated = original.replace(old_string, new_string, 1)
        filepath.write_text(updated, encoding="utf-8")
        delta = len(updated) - len(original)
        sign = "+" if delta >= 0 else ""
        base_msg = f"Edited {path} ({sign}{delta} chars)"
        return _maybe_verify(str(filepath), base_msg)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def delegate(task: str) -> ToolResult:
    """Dispatch to a sub-agent. Returns its synthesized text answer."""
    # Local import to avoid tools <-> subagent <-> agent circular import.
    from .subagent import delegate as _delegate
    try:
        answer = _delegate(task)
        return ToolResult(success=True, output=answer)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def run_tests(path: str = None) -> ToolResult:
    """Auto-detect and run the project's test framework.

    Detection order (first match wins):
    - pyproject.toml / pytest.ini / tests/ or test_*.py present -> pytest
    - package.json with 'test' script -> npm test
    - Cargo.toml -> cargo test
    - go.mod -> go test ./...
    """
    cwd = Path.cwd()

    def _has_any(*names):
        return any((cwd / n).exists() for n in names)

    cmd = None
    # Python
    if _has_any("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini") or list(cwd.glob("test_*.py")):
        cmd = "pytest -q"
        if path:
            cmd += f" {path}"
    # JavaScript / TypeScript
    elif (cwd / "package.json").exists():
        try:
            import json as _json
            pkg = _json.loads((cwd / "package.json").read_text(encoding="utf-8"))
            if pkg.get("scripts", {}).get("test"):
                cmd = "npm test --silent"
        except Exception:
            pass
    # Rust
    elif (cwd / "Cargo.toml").exists():
        cmd = "cargo test --quiet"
    # Go
    elif (cwd / "go.mod").exists():
        cmd = "go test ./..."

    if not cmd:
        return ToolResult(
            success=False, output="",
            error=(
                "Couldn't detect a test framework (no pyproject/pytest, package.json, "
                "Cargo.toml, or go.mod). Run tests manually via run_command."
            ),
        )

    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd),
            capture_output=True, text=True, timeout=300,
        )
        combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return ToolResult(
            success=proc.returncode == 0,
            output=f"$ {cmd}\n{combined[-4000:] or '(no output)'}",
            error=None if proc.returncode == 0 else f"Tests failed (exit {proc.returncode})",
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error="Test run timed out after 5 minutes")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def verify_code(path: str) -> ToolResult:
    """Explicitly verify a file. Use to re-check after fixes."""
    try:
        result = verify_file(path)
        if result.errors:
            return ToolResult(
                success=False,
                output=result.format(),
                error=f"{len(result.errors)} error(s) found",
            )
        if result.warnings:
            return ToolResult(
                success=True,
                output=(
                    f"No hard errors, but {len(result.warnings)} warning(s):\n"
                    + result.format()
                ),
            )
        return ToolResult(
            success=True,
            output=f"✓ {path} passed verification (no issues)",
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def list_directory(path: str = ".") -> ToolResult:
    """List directory contents"""
    try:
        dirpath = Path(path)
        if not dirpath.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory not found: {path}"
            )
        
        items = []
        for item in sorted(dirpath.iterdir()):
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")
        
        output = f"Contents of {path}:\n" + "\n".join(items) if items else f"{path} is empty"
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def search_files(pattern: str, directory: str = ".") -> ToolResult:
    """Search for files matching a glob pattern"""
    try:
        search_pattern = os.path.join(directory, pattern)
        matches = glob_module.glob(search_pattern, recursive=True)
        
        if not matches:
            return ToolResult(
                success=True,
                output=f"No files found matching '{pattern}'"
            )
        
        output = f"Found {len(matches)} file(s):\n" + "\n".join(f"  📄 {m}" for m in matches[:50])
        if len(matches) > 50:
            output += f"\n  ... and {len(matches) - 50} more"
        
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def search_content(query: str, path: str = ".", file_pattern: str = None) -> ToolResult:
    """Search for content within files"""
    try:
        results = []
        search_path = Path(path)
        
        if search_path.is_file():
            files = [search_path]
        else:
            pattern = file_pattern or "**/*"
            files = list(search_path.glob(pattern))
        
        for filepath in files[:100]:  # Limit files searched
            if not filepath.is_file():
                continue
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        results.append(f"{filepath}:{i}: {line.strip()[:100]}")
                        if len(results) >= 50:
                            break
            except:
                continue
            
            if len(results) >= 50:
                break
        
        if not results:
            return ToolResult(
                success=True,
                output=f"No matches found for '{query}'"
            )
        
        output = f"Found {len(results)} match(es) for '{query}':\n" + "\n".join(results)
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def run_command(command: str, working_directory: str = None) -> ToolResult:
    """Run a shell command. Dangerous commands require approval."""
    if REQUIRE_APPROVAL:
        reason = _check_command_safety(command)
        if reason:
            if _approval_hook is None:
                return ToolResult(
                    success=False, output="",
                    error=(
                        f"BLOCKED: command looks dangerous ({reason}). "
                        "No approval prompter is installed, so refusing to run. "
                        "If this is intentional, set CHAHLIE_REQUIRE_APPROVAL=false "
                        "or use a more specific command."
                    ),
                )
            if not _approval_hook(command, reason):
                return ToolResult(
                    success=False, output="",
                    error=f"User denied approval for dangerous command ({reason}).",
                )
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        
        return ToolResult(
            success=result.returncode == 0,
            output=output or "(no output)",
            error=None if result.returncode == 0 else f"Exit code: {result.returncode}"
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            output="",
            error="Command timed out after 60 seconds"
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def create_directory(path: str) -> ToolResult:
    """Create a directory"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, output=f"Created directory: {path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def open_browser(url: str) -> ToolResult:
    """Open a URL in the default browser"""
    try:
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        webbrowser.open(url)
        return ToolResult(
            success=True,
            output=f"Opened {url} in your browser, kehd!"
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def web_search(query: str) -> ToolResult:
    """Search the web using Google"""
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        webbrowser.open(search_url)
        return ToolResult(
            success=True,
            output=f"Searched Google for '{query}' - check your browser!"
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


_plugin_dispatch: dict = {}


def register_plugin_dispatch(name: str, fn) -> None:
    """Called by the agent at startup for each plugin-provided tool."""
    _plugin_dispatch[name] = fn


def execute_tool(name: str, arguments: dict) -> ToolResult:
    """Execute a tool by name with given arguments"""
    tools = {
        "read_file": lambda args: read_file(args.get("path", "")),
        "write_file": lambda args: write_file(args.get("path", ""), args.get("content", "")),
        "list_directory": lambda args: list_directory(args.get("path", ".")),
        "search_files": lambda args: search_files(args.get("pattern", ""), args.get("directory", ".")),
        "search_content": lambda args: search_content(
            args.get("query", ""),
            args.get("path", "."),
            args.get("file_pattern")
        ),
        "run_command": lambda args: run_command(
            args.get("command", ""),
            args.get("working_directory")
        ),
        "create_directory": lambda args: create_directory(args.get("path", "")),
        "open_browser": lambda args: open_browser(args.get("url", "")),
        "web_search": lambda args: web_search(args.get("query", "")),
        "verify_code": lambda args: verify_code(args.get("path", "")),
        "edit_file": lambda args: edit_file(
            args.get("path", ""), args.get("old_string", ""), args.get("new_string", ""),
        ),
        "run_tests": lambda args: run_tests(args.get("path")),
        "delegate": lambda args: delegate(args.get("task", "")),
    }
    
    if name in tools:
        return tools[name](arguments)

    if name in _plugin_dispatch:
        try:
            result = _plugin_dispatch[name](arguments)
            if isinstance(result, ToolResult):
                return result
            # Plugins may return plain dicts; wrap them
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"plugin '{name}' raised: {e}")

    return ToolResult(
        success=False, output="",
        error=f"Unknown tool: {name}",
    )
