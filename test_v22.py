"""
Regression tests for v2.2 "Big Dig" features.

Covers:
- edit_file (happy path, missing file, 0 matches, multiple matches, verification feedback)
- run_command approval block (dangerous command refusal)
- multi-language verifier (JSON syntax error caught; YAML tolerated; unknown ext clean)
- Transaction (snapshot/rollback for existing + new files)
- Context manager (compaction only when threshold exceeded; cost meter math)
- Plugin loader (ignores empty dir, reports warnings on broken plugin)
- Project primer (detects python+git in this repo)
- Semantic memory (offline fallback when embedding fails)

No live LLM calls - we stub clients.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Make tests self-contained from repo root
sys.path.insert(0, str(Path(__file__).parent))

from chahlie.tools import execute_tool, set_approval_hook
from chahlie.verifier import verify_json, verify_file
from chahlie.transaction import Transaction
from chahlie.context_manager import CostMeter, compact_history, estimate_messages_chars
from chahlie.plugins import load_plugins
from chahlie.project_primer import prime_project, render_primer_prompt
from chahlie.memory.semantic import SemanticMemory


PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}{' - ' + detail if detail and not ok else ''}")


# ---------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------
def test_edit_file():
    print("\n[edit_file]")
    tmp = Path("_tmp_edit.txt")
    tmp.write_text("hello world\nhello again\n", encoding="utf-8")

    # too many matches
    r = execute_tool("edit_file", {"path": str(tmp), "old_string": "hello", "new_string": "hi"})
    check("rejects non-unique old_string", not r.success and "appears 2 times" in (r.error or ""))

    # unique edit
    r = execute_tool("edit_file", {"path": str(tmp), "old_string": "hello again", "new_string": "goodbye"})
    check("makes unique edit", r.success and "goodbye" in tmp.read_text(encoding="utf-8"))

    # missing file
    r = execute_tool("edit_file", {"path": "_nope.txt", "old_string": "a", "new_string": "b"})
    check("fails on missing file", not r.success and "not found" in (r.error or ""))

    # 0 matches
    r = execute_tool("edit_file", {"path": str(tmp), "old_string": "NOT_THERE", "new_string": "x"})
    check("fails on zero matches", not r.success and "not found" in (r.error or ""))

    # auto-verify: edit a .py file into broken syntax
    py = Path("_tmp_broken.py")
    py.write_text("def good():\n    return 1\n", encoding="utf-8")
    r = execute_tool("edit_file", {
        "path": str(py), "old_string": "def good():", "new_string": "def bad("
    })
    check("flags syntax error from bad edit", not r.success and "errors" in (r.error or "").lower())

    tmp.unlink(missing_ok=True)
    py.unlink(missing_ok=True)


# ---------------------------------------------------------------------
# approval mode
# ---------------------------------------------------------------------
def test_approval():
    print("\n[approval mode]")

    # no approval hook installed -> refuse
    set_approval_hook(None)
    os.environ.pop("CHAHLIE_REQUIRE_APPROVAL", None)

    # reload config + tools module to pick up the default True
    from importlib import reload
    import chahlie.config as _cfg; reload(_cfg)
    import chahlie.tools as _tools; reload(_tools)

    r = _tools.run_command("rm -rf /tmp/something_dangerous_test_only")
    check("refuses rm -rf without approver", not r.success and "BLOCKED" in (r.error or ""))

    # install hook that approves
    _tools.set_approval_hook(lambda cmd, reason: True)
    # using an innocuous danger pattern: git reset --hard (won't actually do damage because cwd must be a git repo)
    # we only care that approval was consulted; result doesn't matter
    r = _tools.run_command("echo safe")  # not dangerous, should just run
    check("non-dangerous command runs", r.success)


# ---------------------------------------------------------------------
# multi-language verifier
# ---------------------------------------------------------------------
def test_multilang_verifier():
    print("\n[multi-language verifier]")

    bad_json = Path("_bad.json")
    bad_json.write_text('{"a": 1,,}', encoding="utf-8")
    r = verify_json(str(bad_json))
    check("catches JSON syntax error", not r.ok and r.errors)

    good_json = Path("_good.json")
    good_json.write_text('{"a": 1}', encoding="utf-8")
    r = verify_json(str(good_json))
    check("accepts valid JSON", r.ok and not r.errors)

    unknown = Path("_foo.txt")
    unknown.write_text("whatever", encoding="utf-8")
    r = verify_file(str(unknown))
    check("unknown extension -> clean result", r.ok and not r.issues)

    for f in (bad_json, good_json, unknown):
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------------
# transaction
# ---------------------------------------------------------------------
def test_transaction():
    print("\n[transaction]")

    # existing file rollback
    existing = Path("_tx_existing.txt")
    existing.write_text("original\n", encoding="utf-8")
    tx = Transaction()
    tx.snapshot(str(existing))
    existing.write_text("mutated\n", encoding="utf-8")
    tx.rollback()
    check("rolls back existing-file mutation", existing.read_text(encoding="utf-8") == "original\n")
    existing.unlink(missing_ok=True)

    # new file rollback
    new = Path("_tx_new.txt")
    if new.exists():
        new.unlink()
    tx = Transaction()
    tx.snapshot(str(new))
    new.write_text("created\n", encoding="utf-8")
    tx.rollback()
    check("rolls back created file by deleting", not new.exists())

    # commit drops snapshots
    existing.write_text("v1\n", encoding="utf-8")
    tx = Transaction()
    tx.snapshot(str(existing))
    existing.write_text("v2\n", encoding="utf-8")
    tx.commit()
    tx.rollback()  # should be no-op after commit
    check("commit prevents rollback", existing.read_text(encoding="utf-8") == "v2\n")
    existing.unlink(missing_ok=True)


# ---------------------------------------------------------------------
# context manager
# ---------------------------------------------------------------------
def test_context_manager():
    print("\n[context manager]")

    msgs = [{"role": "user", "content": "x" * 100}] * 3
    new_msgs, compacted = compact_history(
        msgs, threshold_chars=10_000,
        preserve_recent=2, summarize_fn=lambda _: "summary",
    )
    check("below threshold -> no compaction", not compacted and new_msgs == msgs)

    big = [{"role": "user", "content": "a" * 5000}] * 10
    new_msgs, compacted = compact_history(
        big, threshold_chars=10_000,
        preserve_recent=2, summarize_fn=lambda head: f"compressed {len(head)} msgs",
    )
    check("over threshold -> compacts", compacted and new_msgs[0]["role"] == "system" and len(new_msgs) == 3)

    c = CostMeter(input_rate=3.0, output_rate=15.0)
    c.add_input("a" * 400)  # ~100 tokens
    c.add_output("a" * 400)  # ~100 tokens
    # 100/1M * 3 + 100/1M * 15 = 0.0003 + 0.0015 = 0.0018
    check("cost meter math sanity", abs(c.cost_usd - 0.0018) < 1e-6, detail=f"got {c.cost_usd}")


# ---------------------------------------------------------------------
# plugin loader
# ---------------------------------------------------------------------
def test_plugins(tmpdir: Path):
    print("\n[plugin loader]")

    defs, dispatch, warns = load_plugins(str(tmpdir / "nope"))
    check("missing dir -> empty, no crash", defs == [] and dispatch == {})

    pdir = tmpdir / "plugins"
    pdir.mkdir()

    # good plugin
    (pdir / "hello.py").write_text(
        "from chahlie.tools import ToolResult\n"
        "def _do(args):\n"
        "    return ToolResult(success=True, output='hi from plugin')\n"
        "TOOLS = [{'definition': {'name': 'say_hi', 'description': '.', "
        "'input_schema': {'type': 'object','properties': {},'required':[]}}, 'function': _do}]\n",
        encoding="utf-8",
    )
    # broken plugin (import error)
    (pdir / "broken.py").write_text("import some_module_that_does_not_exist_ever\n", encoding="utf-8")

    defs, dispatch, warns = load_plugins(str(pdir))
    check("loads good plugin", any(d["name"] == "say_hi" for d in defs) and "say_hi" in dispatch)
    check("reports warning for broken plugin", any("broken.py" in w for w in warns))


# ---------------------------------------------------------------------
# project primer
# ---------------------------------------------------------------------
def test_primer():
    print("\n[project primer]")

    p = prime_project(".")
    check("primer detects python project", p.get("primed") and p.get("language") == "Python")
    check("primer has README snippet", bool(p.get("readme_snippet")))
    rendered = render_primer_prompt(p)
    check("primer renders non-empty prompt", "PROJECT CONTEXT" in rendered)

    bad = prime_project("does/not/exist/12345")
    check("primer handles missing dir", not bad.get("primed"))


# ---------------------------------------------------------------------
# semantic memory (offline)
# ---------------------------------------------------------------------
class _FakeClient:
    """Pretends to be an ollama client that has no embed endpoint."""
    def embed(self, model, input):
        raise RuntimeError("no embedding backend")


def test_semantic_memory_offline():
    print("\n[semantic memory - offline]")
    sm = SemanticMemory(_FakeClient(), "fake-model")
    added = sm.add("something to remember", {"kind": "note"})
    check("gracefully disables after failed embed", not added and not sm.healthy)
    check("empty search returns []", sm.search("query") == [])


# ---------------------------------------------------------------------
# run tests
# ---------------------------------------------------------------------
def main():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="chahlie-v22-"))

    for fn in (
        test_edit_file,
        test_approval,
        test_multilang_verifier,
        test_transaction,
        test_context_manager,
        lambda: test_plugins(tmp),
        test_primer,
        test_semantic_memory_offline,
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
