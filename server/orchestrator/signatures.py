"""Dedup keys. Normalized per domain so trivially-reworded duplicates collide."""
import ast
import re

from .contracts import Attack, Domain, sha

_STOP = {"the", "and", "was", "were", "for", "with", "that", "this", "from", "its", "are", "has", "had"}


def _norm_literal(s: str) -> str:
    s = s.strip()
    try:
        return repr(ast.literal_eval(s))
    except Exception:
        return re.sub(r"\s+", "", s)


def norm_expr(s: str) -> str:
    s = (s.replace("×", "*").replace("·", "*").replace("÷", "/").replace("^", "**").replace("−", "-"))
    return re.sub(r"[\s,]", "", s).lower()


def claim_tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower())
            if (len(t) > 2 or t.isdigit()) and t not in _STOP}


def compute_signature(domain: Domain, a: Attack) -> str:
    if a.test:                       # same probe input == same attack, whatever 'expected' says
        return sha(f"{domain}|test|{_norm_literal(a.test.input)}")
    if a.computation:
        return sha(f"{domain}|comp|{norm_expr(a.computation.expr)}")
    assert a.claim_check
    return sha(f"{domain}|claim|{' '.join(sorted(claim_tokens(a.claim_check.claim)))}")
