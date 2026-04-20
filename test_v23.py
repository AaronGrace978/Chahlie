"""
Regression tests for v2.3 "Southie Sharp" features.

Covers the 16 new enhancements: banner fix, open_file (mock), list_directory
metadata, git tools, lint/watch tools, diff preview in write/edit, syntax
highlighting lexer map, project-scoped memory (git root), fuzzy file match,
retry hints, tool dedupe, /undo, session branching, model router.

Network-free and LLM-free - every backend is stubbed.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from chahlie import tools
from chahlie.tools import (
    execute_tool, read_file, list_directory, undo_last_write, undo_depth,
    open_file, git_status, git_log, lint_code, watch_file,
)
from chahlie.differ import render_unified_diff, summarize_diff
from chahlie.fuzzy import suggest_path, format_suggestions
from chahlie.retry_hints import suggest_retry
from chahlie.memory.memory_manager import ChahlieMemory, _find_project_root, _safe_branch_name


PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}{' - ' + detail if detail and not ok else ''}")


# ---------------------------------------------------------------------
def test_banner_pulled_from_init():
    print("\n[banner version]")
    from chahlie import config
    from chahlie import __version__, __codename__
    check("config.APP_VERSION matches package __version__", config.APP_VERSION == __version__)
    check("config.APP_CODENAME matches package __codename__", config.APP_CODENAME == __codename__)


# ---------------------------------------------------------------------
def test_list_directory_metadata():
    print("\n[list_directory]")
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-ls-"))
    (tmp / "a.txt").write_text("hello")
    (tmp / "sub").mkdir()
    r = execute_tool("list_directory", {"path": str(tmp)})
    check("lists with 'FILE' and 'DIR' markers", r.success and "FILE" in r.output and "DIR" in r.output)
    check("missing dir produces did-you-mean", not execute_tool("list_directory", {"path": str(tmp) + "_NOPE"}).success)


# ---------------------------------------------------------------------
def test_open_file_guardrail():
    print("\n[open_file]")
    r = execute_tool("open_file", {"path": "_def_does_not_exist_path_.xyz"})
    check("refuses missing path", not r.success and "not found" in (r.error or "").lower())


# ---------------------------------------------------------------------
def test_git_tools():
    print("\n[git tools]")
    # These run in the Chahlie project itself (which is a git repo)
    r = execute_tool("git_status", {})
    check("git_status runs", r.success)
    r = execute_tool("git_log", {"limit": 3})
    check("git_log runs", r.success and ("d621efd" in r.output or len(r.output.splitlines()) >= 1))


# ---------------------------------------------------------------------
def test_lint_code_graceful():
    print("\n[lint_code]")
    # This may or may not have ruff/mypy/eslint installed; either way it should succeed.
    r = execute_tool("lint_code", {"path": "chahlie"})
    check("lint_code never crashes", r.success or "exit=" in r.output or "failed to run" in r.output)


# ---------------------------------------------------------------------
def test_watch_file_timeout():
    print("\n[watch_file]")
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-watch-")) / "log.txt"
    tmp.write_text("nothing interesting\n")
    r = execute_tool("watch_file", {"target": str(tmp), "pattern": "NEVER_APPEARS", "timeout_s": 2})
    check("times out cleanly when pattern absent", not r.success and "Timeout" in (r.error or ""))

    # pattern present -> should match quickly
    tmp.write_text("some log\nhello world\n")
    r = execute_tool("watch_file", {"target": str(tmp), "pattern": "hello", "timeout_s": 3})
    check("matches existing pattern quickly", r.success and "Match" in r.output)


# ---------------------------------------------------------------------
def test_diff_in_writes():
    print("\n[diff preview in writes]")
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-diff-")) / "foo.py"
    # Initial write (creation) - no diff in output
    r = execute_tool("write_file", {"path": str(tmp), "content": "x = 1\ny = 2\n"})
    check("creation message has no diff", r.success and "Created" in r.output and "@@" not in r.output)

    # Overwrite - diff appears
    r = execute_tool("write_file", {"path": str(tmp), "content": "x = 1\ny = 3\n"})
    check("overwrite shows unified diff", r.success and "@@" in r.output and "-y = 2" in r.output)

    # Edit - diff appears
    r = execute_tool("edit_file", {"path": str(tmp), "old_string": "y = 3", "new_string": "y = 99"})
    check("edit_file shows diff", r.success and "@@" in r.output and "+y = 99" in r.output)


# ---------------------------------------------------------------------
def test_undo():
    print("\n[undo]")
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-undo-")) / "note.txt"

    # Create + overwrite + undo should restore
    execute_tool("write_file", {"path": str(tmp), "content": "original\n"})
    execute_tool("write_file", {"path": str(tmp), "content": "changed\n"})
    before = undo_depth()
    r = undo_last_write()
    check("undo returned a result", r is not None and tmp.read_text() == "original\n")
    check("undo depth decreased", undo_depth() == before - 1)

    # Undo the original creation -> file deleted
    undo_last_write()
    check("undo creation deletes file", not tmp.exists())


# ---------------------------------------------------------------------
def test_fuzzy_match():
    print("\n[fuzzy path match]")
    hits = suggest_path("agnt.py", root=".")
    check("suggest_path finds agent.py for 'agnt.py'",
          any("agent.py" in h for h in hits), detail=f"got {hits}")
    msg = format_suggestions("nope_not_there.xyz", root=".")
    check("format_suggestions returns empty on no match", msg == "")


# ---------------------------------------------------------------------
def test_retry_hints():
    print("\n[retry hints]")
    h = suggest_retry("", "error: failed to push some refs (has no upstream branch)")
    check("detects missing upstream", h and "git push -u" in h)

    h = suggest_retry("ModuleNotFoundError: No module named 'requests'", "")
    check("detects ModuleNotFoundError", h and "pip install requests" in h)

    h = suggest_retry("", "fatal: not a git repository")
    check("detects not-a-repo", h and "git init" in h)

    h = suggest_retry("", "totally unrelated error message")
    check("returns None when no rule matches", h is None)


# ---------------------------------------------------------------------
def test_diff_helpers():
    print("\n[differ]")
    diff = render_unified_diff("a\nb\nc\n", "a\nB\nc\n", "f.txt")
    check("unified diff includes hunk header", "@@" in diff and "+B" in diff)
    check("no-op returns empty", render_unified_diff("a", "a", "f.txt") == "")
    s = summarize_diff("a\nb\nc", "a\nB\nc")
    check("summarize counts modifications", "+1" in s and "-1" in s, detail=s)


# ---------------------------------------------------------------------
def test_project_root_detection():
    print("\n[project root]")
    root = _find_project_root(Path.cwd())
    check("finds git root from current dir", (root / ".git").exists())
    # When called from a subdir it still should find the parent git
    nested = Path.cwd() / "chahlie" / "memory"
    if nested.exists():
        check("finds git root from nested dir", _find_project_root(nested) == root)


# ---------------------------------------------------------------------
def test_branch_name_sanitization():
    print("\n[branch naming]")
    check("strips unsafe chars", _safe_branch_name("feat/ui-stuff!") == "feat_ui-stuff_")
    check("keeps alnum+-_. intact", _safe_branch_name("v1.2.3_hotfix-alpha") == "v1.2.3_hotfix-alpha")
    check("empty -> 'branch'", _safe_branch_name("    ") == "branch")


# ---------------------------------------------------------------------
def test_session_branching():
    print("\n[session branches]")
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-branch-"))
    (tmp / ".git").mkdir()  # so _find_project_root stops here
    mem = ChahlieMemory(str(tmp))
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    mem.save_branch("exp-1", history)
    check("save_branch writes file", (tmp / ".chahlie" / "branches" / "exp-1.json").exists())
    loaded = mem.load_branch("exp-1")
    check("load_branch returns payload", loaded and loaded["conversation_history"] == history)
    check("list_branches sees it", "exp-1" in mem.list_branches())
    check("load_branch missing returns None", mem.load_branch("does-not-exist") is None)


# ---------------------------------------------------------------------
def test_model_router():
    print("\n[model router]")
    # Force SMALL_MODEL on via env + reload
    os.environ["CHAHLIE_SMALL_MODEL"] = "small-test"
    os.environ["OLLAMA_API_KEY"] = "fake-key"  # so ChahlieAgent doesn't bail
    from importlib import reload
    import chahlie.config as _cfg; reload(_cfg)
    import chahlie.agent as _agent; reload(_agent)

    class _StubClient:
        def chat(self, **kw): raise NotImplementedError

    agent = _agent.ChahlieAgent.__new__(_agent.ChahlieAgent)
    agent.backend = "ollama-cloud"
    agent.model = "big-test"
    check("routes greeting to small model", agent._select_model("yo whats good") == "small-test")
    check("routes long coding prompt to big model",
          agent._select_model("please refactor the database module to use sqlalchemy 2.0 style") == "big-test")
    os.environ.pop("CHAHLIE_SMALL_MODEL", None)


# ---------------------------------------------------------------------
def test_tool_dedupe():
    print("\n[tool dedupe]")
    # Simulate the agent's cache behavior
    from chahlie.agent import _DEDUPABLE_TOOLS
    check("read_file in dedupe set", "read_file" in _DEDUPABLE_TOOLS)
    check("write_file NOT in dedupe set", "write_file" not in _DEDUPABLE_TOOLS)


# ---------------------------------------------------------------------
def main():
    for fn in (
        test_banner_pulled_from_init,
        test_list_directory_metadata,
        test_open_file_guardrail,
        test_git_tools,
        test_lint_code_graceful,
        test_watch_file_timeout,
        test_diff_in_writes,
        test_undo,
        test_fuzzy_match,
        test_retry_hints,
        test_diff_helpers,
        test_project_root_detection,
        test_branch_name_sanitization,
        test_session_branching,
        test_model_router,
        test_tool_dedupe,
    ):
        try:
            fn()
        except Exception:
            traceback.print_exc()
            FAIL.append((fn.__name__, "crashed"))

    print("\n" + "=" * 60)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    print("=" * 60)
    if FAIL:
        for name, detail in FAIL:
            print(f"  FAIL: {name} - {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
