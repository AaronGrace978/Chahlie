"""Smoke tests for v2.3.2 Speed Pass changes.

Covers:
- Intent router: open/go-to/launch/search -> correct tool+url
- Intent router: file-ish and path-ish messages are NOT hijacked
- Action-turn detector: imperative vs explanatory
- Preamble dedup: simulated multi-iteration streaming
- Version bump
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import chahlie
from chahlie.agent import ChahlieAgent


def _agent() -> ChahlieAgent:
    # enable_memory=False avoids touching disk
    return ChahlieAgent(backend="ollama-cloud", enable_memory=False)


def test_version():
    assert chahlie.__version__ == "2.3.2", chahlie.__version__
    assert "Speed Pass" in chahlie.__codename__
    print("  version:", chahlie.__version__, "-", chahlie.__codename__)


def test_intent_router_browser_aliases():
    a = _agent()
    cases_with_url = [
        ("open chrome", "https://google.com"),
        ("open up chrome please", "https://google.com"),
        ("launch firefox", "https://google.com"),
        ("fire up the browser", "https://google.com"),
        ("open the internet", "https://google.com"),
    ]
    for msg, want_url in cases_with_url:
        got = a._try_intent_shortcut(msg)
        assert got is not None, f"no shortcut for {msg!r}"
        tool, args, _ = got
        assert tool == "open_browser", (msg, got)
        assert args["url"] == want_url, (msg, got)
    print(f"  browser aliases: {len(cases_with_url)} passed")


def test_intent_router_sites():
    a = _agent()
    cases = [
        ("open youtube", "https://youtube.com"),
        ("go to github", "https://github.com"),
        ("navigate to reddit", "https://reddit.com"),
        ("pull up hacker news", "https://news.ycombinator.com"),
        ("open stackoverflow please", "https://stackoverflow.com"),
        ("open claude", "https://claude.ai"),
        ("bring up gmail", "https://mail.google.com"),
    ]
    for msg, want in cases:
        got = a._try_intent_shortcut(msg)
        assert got is not None, f"no shortcut for {msg!r}"
        _, args, _ = got
        assert args["url"] == want, (msg, got)
    print(f"  site aliases: {len(cases)} passed")


def test_intent_router_raw_urls():
    a = _agent()
    cases = [
        ("open https://example.com", "https://example.com"),
        ("go to example.com", "https://example.com"),
        ("navigate to docs.python.org", "https://docs.python.org"),
    ]
    for msg, want in cases:
        got = a._try_intent_shortcut(msg)
        assert got is not None, f"no shortcut for {msg!r}"
        _, args, _ = got
        assert args["url"] == want, (msg, got)
    print(f"  raw urls: {len(cases)} passed")


def test_intent_router_search():
    a = _agent()
    got = a._try_intent_shortcut("google boston celtics score")
    assert got is not None
    tool, args, _ = got
    assert tool == "web_search", got
    assert "celtics" in args["query"].lower()
    got = a._try_intent_shortcut("search for python asyncio docs")
    assert got and got[0] == "web_search"
    print("  search intent: 2 passed")


def test_intent_router_does_not_hijack_files():
    """These should NOT match - they're filesystem/editor tasks, not browser."""
    a = _agent()
    should_skip = [
        "open the config file",
        "open README.md",
        "open the terminal",
        "open my notes",
        "open the editor",
        "open a pull request",
        "open C:\\Users\\me\\notes.txt",
        "open /etc/hosts",
        "run the tests",
        "git status",
        "explain how git rebase works",
        "what does the open() function do",
        "hey kehd",
        "yo",
        "sup",
    ]
    for msg in should_skip:
        got = a._try_intent_shortcut(msg)
        assert got is None, f"unexpectedly hijacked {msg!r} -> {got}"
    print(f"  correctly skipped: {len(should_skip)} cases")


def test_action_turn_detector():
    a = _agent()
    action = [
        "open chrome",
        "run the tests",
        "git status",
        "install numpy",
        "list the files",
        "push to main",
        "execute npm run build",
    ]
    not_action = [
        "hey",
        "yo",
        "explain how git works",
        "what does asyncio.gather do?",
        "why is this failing?",
        "can you explain the code?",
        "tell me about cursor boston",
        "how come my tests are slow",
    ]
    for msg in action:
        assert a._is_action_turn(msg), f"should be action: {msg!r}"
    for msg in not_action:
        assert not a._is_action_turn(msg), f"should NOT be action: {msg!r}"
    print(f"  action detector: {len(action)} action + {len(not_action)} non-action passed")


def test_action_mode_prompt_is_leaner():
    a = _agent()
    full = a._get_enhanced_system_prompt("add a new feature to the project")
    action = a._get_enhanced_system_prompt("open chrome", action_mode=True)
    social = a._get_enhanced_system_prompt("yo", lightweight=True)
    # Action prompt must be meaningfully shorter than the full primer+memory one.
    assert len(action) < len(full), (len(action), len(full))
    # Social is tinier still.
    assert len(social) < len(action), (len(social), len(action))
    print(f"  prompt sizes: social={len(social)} action={len(action)} full={len(full)}")


def test_intent_shortcut_yields_expected_events():
    """Run the intent shortcut generator and check the event sequence."""
    a = _agent()
    shortcut = a._try_intent_shortcut("open chrome")
    assert shortcut is not None

    # Monkey-patch execute_tool to avoid actually opening a browser.
    import chahlie.agent as agent_mod
    from chahlie.tools import ToolResult
    real = agent_mod.execute_tool
    agent_mod.execute_tool = lambda name, args: ToolResult(
        success=True, output=f"(fake) opened {args.get('url')}",
    )
    try:
        events = list(a._run_intent_shortcut("open chrome", *shortcut))
    finally:
        agent_mod.execute_tool = real

    types = [e.type for e in events]
    assert "tool_use" in types
    assert "tool_result" in types
    assert "text" in types
    assert types[-1] == "done"
    print(f"  event sequence: {types}")


def test_preamble_dedup_logic():
    """Simulate the dedup state machine directly."""
    prior = "Alright kehd, let me take a look at your files.\n"
    chunks = [
        "Alright kehd, let me take a look at your files.\n",
        "Now let me also check the config.",
    ]

    dedup_target = prior
    dedup_buffer = ""
    dedup_active = True
    emitted = ""

    for piece in chunks:
        emit_piece = piece
        if dedup_active:
            dedup_buffer += piece
            if dedup_target.startswith(dedup_buffer):
                continue
            if dedup_buffer.startswith(dedup_target):
                emit_piece = dedup_buffer[len(dedup_target):]
                dedup_active = False
            else:
                emit_piece = dedup_buffer
                dedup_active = False
        emitted += emit_piece

    assert emitted == "Now let me also check the config.", repr(emitted)
    print("  preamble dedup: prior prefix correctly stripped")


def main():
    tests = [
        test_version,
        test_intent_router_browser_aliases,
        test_intent_router_sites,
        test_intent_router_raw_urls,
        test_intent_router_search,
        test_intent_router_does_not_hijack_files,
        test_action_turn_detector,
        test_action_mode_prompt_is_leaner,
        test_intent_shortcut_yields_expected_events,
        test_preamble_dedup_logic,
    ]
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[OK] {name}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {name}: {type(e).__name__}: {e}")
    print()
    total = len(tests)
    if failed:
        print(f"FAILED: {failed}/{total}")
        sys.exit(1)
    print(f"PASSED: {total}/{total} - v2.3.2 Speed Pass looks good, kehd.")


if __name__ == "__main__":
    main()
