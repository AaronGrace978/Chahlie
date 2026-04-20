"""
Chahlie's Agentic Tools
The hands that do the work
"""

import os
import subprocess
import glob as glob_module
import webbrowser
import urllib.parse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .verifier import verify_file


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
            "Run static checks on a Python file (syntax + undefined names). "
            "Use this after writing code to catch typos and unbound variables "
            "BEFORE declaring a task complete. Returns any issues found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the Python file to verify"
                }
            },
            "required": ["path"]
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

        # Auto-verify Python files
        if filepath.suffix == ".py":
            result = verify_file(str(filepath))
            if result.errors:
                # Syntax errors -> fail the tool so the agent MUST fix
                report = result.format()
                return ToolResult(
                    success=False,
                    output=base_msg,
                    error=(
                        "File was written but has errors you must fix before "
                        "proceeding:\n" + report
                    ),
                )
            if result.warnings:
                warn_report = result.format()
                return ToolResult(
                    success=True,
                    output=(
                        base_msg
                        + "\n\nVERIFICATION WARNINGS (fix these before declaring done):\n"
                        + warn_report
                    ),
                )

        return ToolResult(success=True, output=base_msg)
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
    """Run a shell command"""
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
    }
    
    if name not in tools:
        return ToolResult(
            success=False,
            output="",
            error=f"Unknown tool: {name}"
        )
    
    return tools[name](arguments)
