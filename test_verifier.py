#!/usr/bin/env python3
"""
Regression tests for chahlie.verifier

Uses real bugs Chahlie shipped tonight (2026-04-20) as fixtures:
- `weaknesses_counts` typo (should-be `weakness_counts`)
- `import_imports` undefined (should-be `import_lines`)
- Plain syntax errors

Run: python test_verifier.py
"""

import tempfile
from pathlib import Path
from chahlie.verifier import verify_python, verify_file
from chahlie.tools import write_file, verify_code


def assert_true(cond, msg):
    if not cond:
        print(f"  FAIL: {msg}")
        raise SystemExit(1)
    print(f"  PASS: {msg}")


def test_syntax_error_detected():
    print("\n[1] Syntax error detection")
    content = "def foo(:\n    pass\n"
    result = verify_python("bad.py", content)
    assert_true(not result.ok, "returns ok=False on syntax error")
    assert_true(len(result.errors) == 1, "reports exactly one syntax error")
    assert_true(result.errors[0].code == "E-SYNTAX", "error coded as E-SYNTAX")


def test_clean_file_passes():
    print("\n[2] Clean file passes")
    content = (
        "import os\n"
        "def greet(name: str) -> str:\n"
        "    return f'hello {name} from {os.getcwd()}'\n"
    )
    result = verify_python("clean.py", content)
    assert_true(result.ok, "ok=True on clean file")
    assert_true(len(result.issues) == 0, "no issues on clean file")


def test_chahlies_weaknesses_counts_bug():
    print("\n[3] Chahlie's real bug: `weaknesses_counts` typo")
    # Reduced repro of the bug from reflection.py:219
    content = (
        "def generate_plan(reflections):\n"
        "    weakness_counts = {}\n"
        "    for r in reflections:\n"
        "        for w in r.get('weaknesses', []):\n"
        "            weakness_counts[w] = weakness_counts.get(w, 0) + 1\n"
        "    top = sorted(weaknesses_counts.items(), key=lambda x: x[1])[:5]\n"
        "    return top\n"
    )
    result = verify_python("reflection.py", content)
    assert_true(result.ok, "syntax is fine (ok=True)")
    undef_names = [i.message for i in result.warnings]
    assert_true(
        any("weaknesses_counts" in m for m in undef_names),
        "flags `weaknesses_counts` as undefined",
    )


def test_chahlies_import_imports_bug():
    print("\n[4] Chahlie's real bug: `import_imports` undefined")
    # Reduced repro of the bug from pattern_learner.py:139
    content = (
        "import re\n"
        "def style(code):\n"
        "    from_imports = len(re.findall(r'from', code))\n"
        "    import_lines = len(re.findall(r'import', code))\n"
        "    if from_imports > import_imports * 1.5:\n"
        "        return 'from_style'\n"
        "    return None\n"
    )
    result = verify_python("patterns.py", content)
    undef_names = [i.message for i in result.warnings]
    assert_true(
        any("import_imports" in m for m in undef_names),
        "flags `import_imports` as undefined",
    )


def test_write_file_fails_on_syntax_error():
    print("\n[5] write_file reports failure on syntax error")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "broken.py"
        res = write_file(str(target), "def oops(:\n    pass\n")
        assert_true(not res.success, "write_file returns success=False")
        assert_true(target.exists(), "file was still written to disk")
        assert_true("E-SYNTAX" in (res.error or ""), "error mentions E-SYNTAX")


def test_write_file_warns_on_undefined_name():
    print("\n[6] write_file surfaces undefined-name warnings")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "typo.py"
        res = write_file(
            str(target),
            "def f():\n    return weaknesses_counts\n",
        )
        assert_true(res.success, "write still succeeds (warning, not error)")
        assert_true(
            "VERIFICATION WARNINGS" in res.output,
            "output mentions VERIFICATION WARNINGS",
        )
        assert_true(
            "weaknesses_counts" in res.output,
            "output names the undefined identifier",
        )


def test_verify_code_tool():
    print("\n[7] verify_code tool works standalone")
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "ok.py"
        clean.write_text("x = 1\nprint(x)\n", encoding="utf-8")
        res = verify_code(str(clean))
        assert_true(res.success, "clean file passes")
        assert_true("passed verification" in res.output, "says passed")


def test_star_import_skips_undef_check():
    print("\n[8] star imports disable undef check (no false positives)")
    content = (
        "from os import *\n"
        "def f():\n    return getcwd()\n"  # getcwd only exists via star import
    )
    result = verify_python("star.py", content)
    assert_true(len(result.warnings) == 0, "no warnings when star import present")


def test_non_python_files_skipped():
    print("\n[9] Non-Python files are not verified")
    with tempfile.TemporaryDirectory() as tmp:
        readme = Path(tmp) / "README.md"
        res = write_file(str(readme), "# This is not python def foo(:\n")
        assert_true(res.success, "markdown writes succeed regardless of content")


if __name__ == "__main__":
    print("=" * 60)
    print("VERIFIER REGRESSION TESTS")
    print("=" * 60)

    tests = [
        test_syntax_error_detected,
        test_clean_file_passes,
        test_chahlies_weaknesses_counts_bug,
        test_chahlies_import_imports_bug,
        test_write_file_fails_on_syntax_error,
        test_write_file_warns_on_undefined_name,
        test_verify_code_tool,
        test_star_import_skips_undef_check,
        test_non_python_files_skipped,
    ]

    for t in tests:
        t()

    print("\n" + "=" * 60)
    print(f"ALL {len(tests)} TESTS PASSED")
    print("=" * 60)
