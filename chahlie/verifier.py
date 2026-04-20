"""
Chahlie's Self-Verification System
The "check ya work" loop - catches bugs BEFORE declaring done.

Runs fast static checks on Python files after they're written, so Chahlie
gets immediate feedback on syntax errors and undefined names instead of
shipping typos like `weaknesses_counts` or `import_imports`.
"""

import ast
import builtins
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


def verify_file(path: str) -> VerifyResult:
    """Verify any supported file type. Currently only .py; extensible."""
    p = Path(path)
    if p.suffix == ".py":
        return verify_python(path)
    # Non-Python files: nothing to check (return clean)
    return VerifyResult(ok=True, path=path, issues=[])
