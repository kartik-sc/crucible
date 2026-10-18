"""High-precision static rules (pure `ast`, never executes code => safe to run in the parent).
Each finding is deterministic, so a lint attack needs no oracle vote."""
from __future__ import annotations

import ast
import builtins

RULE_CLASS = {   # which weakness class a rule's attack is filed under (affects score weight only)
    "mutable_default": "boundary", "undefined_name": "spec_gap", "mutator_result": "spec_gap",
    "is_literal": "numeric_type", "swallowed_exception": "spec_gap", "unreachable_code": "spec_gap",
    "mutate_while_iterating": "boundary",
}
_MUT_RESULT = {"sort", "reverse", "shuffle", "extend", "append"}      # builtin mutators returning None
_MUT_ITER = {"remove", "pop", "insert", "append", "extend", "clear"}


def _parse(src: str):
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def mutable_default(t):
    out = []
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for d in [*n.args.defaults, *[k for k in n.args.kw_defaults if k]]:
                bad = isinstance(d, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)) or (
                    isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id in {"list", "dict", "set"})
                if bad:
                    nm = getattr(n, "name", "<lambda>")
                    out.append(f"line {d.lineno}: mutable default argument in {nm}() is shared across calls")
    return out


def undefined_name(t):
    if any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(t)):
        return []
    defined = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "__builtins__"}
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(n.name)
        elif isinstance(n, ast.arg):
            defined.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            defined.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            defined.update((a.asname or a.name).split(".")[0] for a in n.names)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            defined.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            defined.update(n.names)
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name:
            defined.add(n.name)
        elif isinstance(n, ast.MatchMapping) and n.rest:
            defined.add(n.rest)
    return [f"line {n.lineno}: name '{n.id}' is used but never defined"
            for n in ast.walk(t) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined]


def mutator_result(t):
    out = []
    for n in ast.walk(t):
        val = n.value if isinstance(n, (ast.Assign, ast.AnnAssign, ast.Return)) else None
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr in _MUT_RESULT \
                and isinstance(val.func.value, (ast.Name, ast.Attribute)):
            out.append(f"line {n.lineno}: .{val.func.attr}() returns None; its result is used")
    return out


def is_literal(t):
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Compare) and any(isinstance(o, (ast.Is, ast.IsNot)) for o in n.ops):
            for c in [n.left, *n.comparators]:
                if isinstance(c, ast.Constant) and not (c.value is None or isinstance(c.value, bool) or c.value is Ellipsis):
                    out.append(f"line {n.lineno}: `is` compared with a literal; use == (identity is not equality)")
                    break
    return out


def swallowed_exception(t):
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.ExceptHandler):
            broad = n.type is None or (isinstance(n.type, ast.Name) and n.type.id in {"Exception", "BaseException"})
            silent = all(isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
                         for s in n.body)
            if broad and silent:
                out.append(f"line {n.lineno}: broad except silently swallows every error")
    return out


def unreachable_code(t):
    out = []
    for n in ast.walk(t):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(n, field, None)
            if isinstance(stmts, list):
                for a, b in zip(stmts, stmts[1:]):
                    if isinstance(a, (ast.Return, ast.Raise, ast.Break, ast.Continue)) and isinstance(b, ast.stmt):
                        out.append(f"line {b.lineno}: unreachable code after {type(a).__name__.lower()}")
    return out


def mutate_while_iterating(t):
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Name):
            name = n.iter.id
            for s in ast.walk(ast.Module(body=n.body, type_ignores=[])):
                if (isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr in _MUT_ITER
                        and isinstance(s.func.value, ast.Name) and s.func.value.id == name) or (
                        isinstance(s, ast.Delete) and any(isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name)
                                                          and x.value.id == name for x in s.targets)):
                    out.append(f"line {s.lineno}: '{name}' is modified while being iterated over")
                    break
    return out


RULES = {"mutable_default": mutable_default, "undefined_name": undefined_name, "mutator_result": mutator_result,
         "is_literal": is_literal, "swallowed_exception": swallowed_exception,
         "unreachable_code": unreachable_code, "mutate_while_iterating": mutate_while_iterating}


def run_rule(rule: str, src: str) -> list[str]:
    t = _parse(src)
    return RULES[rule](t) if t is not None and rule in RULES else []


def all_findings(src: str) -> dict[str, list[str]]:
    t = _parse(src)
    if t is None:
        return {}
    return {r: f for r, fn in RULES.items() if (f := fn(t))}
