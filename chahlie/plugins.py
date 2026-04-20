"""
Chahlie plugin system.

Drop a Python file into ~/.chahlie/plugins/ (or CHAHLIE_PLUGINS_DIR) that
defines a module-level `TOOLS` list and it gets loaded on startup. Each
entry in `TOOLS` is a dict:

    {
        "definition": { ... anthropic/ollama tool spec ... },
        "function":   callable(args_dict) -> ToolResult,
    }

Zero magic - plugins just register more tools that the agent can call.
A plugin that raises during import is skipped with a warning; it never
takes down the agent.
"""

from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Tuple


def load_plugins(plugins_dir: str) -> Tuple[List[dict], Dict[str, Callable], List[str]]:
    """Load plugins from `plugins_dir`.

    Returns
    -------
    (tool_definitions, dispatch_map, warnings)
        - tool_definitions: list of tool schemas to append to TOOL_DEFINITIONS
        - dispatch_map: {tool_name: callable(args_dict) -> ToolResult}
        - warnings: human-readable notes about skipped plugins
    """
    base = Path(plugins_dir)
    definitions: List[dict] = []
    dispatch: Dict[str, Callable] = {}
    warnings: List[str] = []

    if not base.is_dir():
        return definitions, dispatch, warnings

    for file in sorted(base.glob("*.py")):
        if file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"chahlie_plugin_{file.stem}", file)
            if spec is None or spec.loader is None:
                warnings.append(f"{file.name}: could not create import spec")
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            tools = getattr(module, "TOOLS", None)
            if not tools:
                warnings.append(f"{file.name}: no TOOLS list found, skipping")
                continue
            for entry in tools:
                definition = entry.get("definition")
                fn = entry.get("function")
                if not definition or not callable(fn):
                    warnings.append(f"{file.name}: invalid tool entry, skipping")
                    continue
                name = definition.get("name")
                if not name:
                    warnings.append(f"{file.name}: tool missing 'name', skipping")
                    continue
                definitions.append(definition)
                dispatch[name] = fn
        except Exception:
            warnings.append(f"{file.name}: failed to load\n{traceback.format_exc().splitlines()[-1]}")

    return definitions, dispatch, warnings
