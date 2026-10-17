"""Attack signatures (TR-10): a normalized hash per domain, used as the dedup key.

Two attacks with the same signature are the same probe, whichever breaker sent it:
  code (test)          -> canonical Python literal of the input
  math (computation)   -> canonical expression (AST round-trip, whitespace-free)
  factual (claimCheck) -> lemmatized claim (lowercase, no punctuation/stopwords, crude stem)
"""

from __future__ import annotations

import ast
import hashlib
import re

from contracts import Attack

_STOPWORDS = frozenset(
    "a an the is are was were be been being of in on at to for by with and or that this it its as from".split()
)
_SUFFIXES = ("ing", "ed", "es", "s")


def normalize_input(raw: str) -> str:
    s = raw.strip()
    try:
        return repr(ast.literal_eval(s))
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return re.sub(r"\s+", " ", s)


def normalize_expr(raw: str) -> str:
    s = raw.strip()
    try:
        s = ast.unparse(ast.parse(s, mode="eval"))
    except (SyntaxError, ValueError, RecursionError):
        pass
    return re.sub(r"\s+", "", s).lower()


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if len(word) > len(suf) + 2 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def normalize_claim(raw: str) -> str:
    words = re.sub(r"[^\w\s]", " ", raw.lower()).split()
    return " ".join(_stem(w) for w in words if w not in _STOPWORDS)


def signature(attack: Attack) -> str:
    if attack.test is not None:
        key = "test:" + normalize_input(attack.test.input)
    elif attack.computation is not None:
        key = "computation:" + normalize_expr(attack.computation.expr)
    else:
        key = "claimCheck:" + normalize_claim(attack.claim_check.claim)
    return "sha256:" + hashlib.sha256(key.encode()).hexdigest()
