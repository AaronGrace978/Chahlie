"""
Chahlie's Self-Verification System
The "check ya work" loop - catches bugs BEFORE declaring done.

Runs fast static checks on Python files after they're written, so Chahlie
gets immediate feedback on syntax errors and undefined names instead of
shipping typos like `weaknesses_counts` or `import_imports`.
"""

import ast
import builtins
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Issue:
    """A single verification issue"""
    severity: str  # 'error' | 'warning'
    line: int
    column: int
    code: str      # short code like 'E-SYNTAX', 'W-UNDEF'
    message: str

    def format(self) -> str:
        loc = f"line {self.line}"
        if self.column:
            loc += f", col {self.column}"
        return f"  [{self.severity.upper():7}] {loc}: {self.code} {self.message}"


@dataclass
class VerifyResult:
    """Result of verifying a file"""
    ok: bool
    path: str
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    def format(self) -> str:
        """Human-readable report. Empty string if no issues."""
        if not self.issues:
            return ""
        lines = [f"Verification for {self.path}:"]
        for issue in self.issues:
            lines.append(issue.format())
        return "\n".join(lines)


def verify_python(path: str, content: Optional[str] = None) -> VerifyResult:
    """
    Verify a Python file. Returns a VerifyResult with any issues found.

    - ok=False only when there are hard errors (syntax). Warnings keep ok=True
      so the write still succeeds, but the agent sees them in the tool output.
    - If `content` is omitted, reads from disk.
    """
    if content is None:
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            return VerifyResult(
                ok=False,
                path=path,
                issues=[Issue("error", 0, 0, "E-READ", f"could not read file: {e}")],
            )

    # 1) Syntax check
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError as e:
        return VerifyResult(
            ok=False,
            path=path,
            issues=[Issue(
                severity="error",
                line=e.lineno or 0,
                column=e.offset or 0,
                code="E-SYNTAX",
                message=(e.msg or "syntax error"),
            )],
        )

    # 2) Undefined-name check (conservative, module-wide)
    issues = _check_undefined_names(tree)
    return VerifyResult(ok=True, path=path, issues=issues)


def _collect_bindings(tree: ast.AST) -> set:
    """Collect every name bound anywhere in the module.

    Deliberately over-inclusive across scopes: we want to flag names that are
    NEVER defined anywhere, not simulate Python's scoping rules precisely.
    """
    bound = set(dir(builtins))
    # Common runtime names + dunders that aren't in `builtins`
    bound.update({
        "__name__", "__file__", "__doc__", "__package__", "__loader__",
        "__spec__", "__builtins__", "__path__", "__all__", "__version__",
        "self", "cls",
    })

    def add_target(node):
        """Add names bound by an assignment target (handles tuples/lists)."""
        if isinstance(node, ast.Name):
            bound.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                add_target(elt)
        elif isinstance(node, ast.Starred):
            add_target(node.value)

    saw_star_import = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Lambda):
            pass  # args handled below via ast.arguments
        elif isinstance(node, ast.arguments):
            for a in list(node.args) + list(node.kwonlyargs) + list(getattr(node, "posonlyargs", []) or []):
                bound.add(a.arg)
            if node.vararg:
                bound.add(node.vararg.arg)
            if node.kwarg:
                bound.add(node.kwarg.arg)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                add_target(t)
        elif isinstance(node, ast.AugAssign):
            add_target(node.target)
        elif isinstance(node, ast.AnnAssign):
            add_target(node.target)
        elif isinstance(node, ast.NamedExpr):  # walrus :=
            add_target(node.target)
        elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
            add_target(node.target)
        elif isinstance(node, ast.comprehension):
            add_target(node.target)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                add_target(node.optional_vars)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                bound.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    saw_star_import = True
                else:
                    bound.add(alias.asname or alias.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            for n in node.names:
                bound.add(n)

    return bound, saw_star_import


def _check_undefined_names(tree: ast.AST) -> List[Issue]:
    """Find bare `Name` loads that are never bound anywhere in the module."""
    bound, saw_star_import = _collect_bindings(tree)

    # If the module does `from x import *`, we can't know what's defined.
    # Skip the check rather than produce false positives.
    if saw_star_import:
        return []

    seen = set()  # dedupe (line, name)
    issues: List[Issue] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name in bound:
                continue
            key = (node.lineno, name)
            if key in seen:
                continue
            seen.add(key)
            issues.append(Issue(
                severity="warning",
                line=node.lineno,
                column=getattr(node, "col_offset", 0),
                code="W-UNDEF",
                message=f"undefined name '{name}' (did you mean something already defined?)",
            ))

    # Cap to avoid flooding the agent context
    if len(issues) > 15:
        extra = len(issues) - 15
        issues = issues[:15]
        issues.append(Issue(
            severity="warning", line=0, column=0, code="W-TRUNC",
            message=f"... and {extra} more undefined-name warnings (truncated)",
        ))

    return issues


def _run_check(cmd: List[str], path: str, code: str) -> Optional[VerifyResult]:
    """Run an external checker and translate its exit code into a VerifyResult.

    Returns None if the toolchain isn't installed (so callers can fall back
    silently instead of failing on missing tools).
    """
    if shutil.which(cmd[0]) is None:
        return None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception as e:
        return VerifyResult(ok=True, path=path, issues=[Issue(
            severity="warning", line=0, column=0, code="W-TOOLCHAIN",
            message=f"{cmd[0]} check failed to run: {e}",
        )])
    if proc.returncode == 0:
        return VerifyResult(ok=True, path=path, issues=[])
    msg = (proc.stderr or proc.stdout or "failed").strip().splitlines()[:5]
    return VerifyResult(
        ok=False, path=path,
        issues=[Issue(
            severity="error", line=0, column=0, code=code,
            message=" | ".join(msg)[:500],
        )],
    )


def verify_json(path: str, content: Optional[str] = None) -> VerifyResult:
    if content is None:
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            return VerifyResult(ok=False, path=path, issues=[
                Issue("error", 0, 0, "E-READ", f"could not read file: {e}"),
            ])
    try:
        json.loads(content)
        return VerifyResult(ok=True, path=path, issues=[])
    except json.JSONDecodeError as e:
        return VerifyResult(ok=False, path=path, issues=[Issue(
            severity="error", line=e.lineno, column=e.colno,
            code="E-JSON", message=e.msg,
        )])


def verify_yaml(path: str, content: Optional[str] = None) -> VerifyResult:
    # PyYAML is commonly available but not a hard dep - fail soft.
    try:
        import yaml  # type: ignore
    except ImportError:
        return VerifyResult(ok=True, path=path, issues=[])
    if content is None:
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            return VerifyResult(ok=False, path=path, issues=[
                Issue("error", 0, 0, "E-READ", f"could not read file: {e}"),
            ])
    try:
        list(yaml.safe_load_all(content))
        return VerifyResult(ok=True, path=path, issues=[])
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        return VerifyResult(ok=False, path=path, issues=[Issue(
            severity="error",
            line=(mark.line + 1) if mark else 0,
            column=(mark.column + 1) if mark else 0,
            code="E-YAML",
            message=str(getattr(e, "problem", e))[:300],
        )])


def verify_javascript(path: str) -> VerifyResult:
    """`node --check` for JS, `tsc --noEmit` for TS when available."""
    p = Path(path)
    if p.suffix in (".js", ".mjs", ".cjs"):
        res = _run_check(["node", "--check", str(p)], str(p), "E-JS")
        return res or VerifyResult(ok=True, path=str(p), issues=[])
    if p.suffix in (".ts", ".tsx"):
        res = _run_check(["tsc", "--noEmit", str(p)], str(p), "E-TS")
        return res or VerifyResult(ok=True, path=str(p), issues=[])
    return VerifyResult(ok=True, path=str(p), issues=[])


def verify_go(path: str) -> VerifyResult:
    res = _run_check(["gofmt", "-e", "-l", str(path)], str(path), "E-GO")
    return res or VerifyResult(ok=True, path=str(path), issues=[])


def verify_rust(path: str) -> VerifyResult:
    # `rustc --edition 2021 --emit=metadata -o -` is cleanest but assumes a
    # lib context; for a standalone file we just do a parse-style check via
    # rustc's --emit=dep-info which short-circuits on syntax errors.
    res = _run_check(
        ["rustc", "--edition", "2021", "--emit=dep-info", "--out-dir", "/tmp", str(path)],
        str(path), "E-RUST",
    )
    return res or VerifyResult(ok=True, path=str(path), issues=[])


def verify_file(path: str) -> VerifyResult:
    """Dispatch by extension. Returns clean result for unknown types."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".py":
        return verify_python(str(p))
    if ext in (".json",):
        return verify_json(str(p))
    if ext in (".yaml", ".yml"):
        return verify_yaml(str(p))
    if ext in (".js", ".mjs", ".cjs", ".ts", ".tsx"):
        return verify_javascript(str(p))
    if ext == ".go":
        return verify_go(str(p))
    if ext == ".rs":
        return verify_rust(str(p))
    return VerifyResult(ok=True, path=str(p), issues=[])
