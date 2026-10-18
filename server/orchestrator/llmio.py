"""Tolerant parsing of raw LLM text (think-tags, fences, prose around JSON)."""
import json
import re

_THINK = re.compile(r"<(?:think|thought)>.*?</(?:think|thought)>", re.S)
_THINK_OPEN = re.compile(r"<(?:think|thought)>")
_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*[ \t]*\n(.*?)```", re.S)


def strip_think(t: str) -> str:
    t = _THINK.sub("", t)
    m = _THINK_OPEN.search(t)          # unclosed (truncated) reasoning: drop from the open tag
    if m:
        t = t[: m.start()]
    return t.strip()


def first_fence(t: str) -> str | None:
    m = _FENCE.search(t)
    return m.group(1) if m else None


def extract_tag(t: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", t, re.S)
    if m:
        return m.group(1)
    m = re.search(rf"<{tag}>(.*)$", t, re.S)      # unterminated tag: take the rest
    return m.group(1) if m else None


def _balanced_end(s: str, i: int) -> int | None:
    depth, in_str, esc = 0, False, False
    for j in range(i, len(s)):
        c = s[j]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
            continue
        if c == '"': in_str = True
        elif c in "{[": depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return j
    return None


def extract_json(text: str):
    """First parseable JSON object/array in text. Raises ValueError if none."""
    text = strip_think(text)
    for cand in filter(None, [first_fence(text), text]):
        try:
            return json.loads(cand.strip())
        except Exception:
            pass
        for i, ch in enumerate(cand):
            if ch in "{[":
                end = _balanced_end(cand, i)
                if end is not None:
                    try:
                        return json.loads(cand[i:end + 1])
                    except Exception:
                        continue
    raise ValueError("no JSON found in model output")
