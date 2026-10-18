"""Runs INSIDE the jailed subprocess. stdin: JSON request. stdout: '@@RESULT@@<json>'.
Modes: probe (test | snippet | script) · eval (math/reasoning snippet) · diff (differential fuzz).
Best-effort jail (rlimits + blocked network/spawn); the real boundary is the Render container."""
import ast, contextlib, copy, io, itertools, json, linecache, math, random, re, signal, sys, time, traceback

MAXLEN = 300


def _jail(mem_mb, cpu_s):
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 2**20, mem_mb * 2**20))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    except Exception:
        pass
    import os, socket
    def blocked(*a, **k):
        raise PermissionError("disabled in sandbox")
    socket.socket = blocked; socket.create_connection = blocked; socket.getaddrinfo = blocked
    for n in ("system", "popen", "fork", "execv", "execve", "execvp", "posix_spawn", "kill"):
        if hasattr(os, n):
            setattr(os, n, blocked)
    sys.modules["subprocess"] = None


# ---------- comparison ----------
def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _norm(x):
    if isinstance(x, (list, tuple)):
        return [_norm(i) for i in x]
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, (set, frozenset)):
        return sorted(repr(_norm(i)) for i in x)
    return x


def _eq(a, b):                         # strict where it matters: bool != int; list == tuple (lenient)
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) == type(b) and a == b
    if _isnum(a) and _isnum(b) and (isinstance(a, float) or isinstance(b, float)):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_eq(a[k], b[k]) for k in a)
    return a == b


def _s(x):
    r = repr(x)
    return r if len(r) <= MAXLEN else r[:MAXLEN] + "...<truncated>"


# ---------- property-testing helpers exposed to probes ----------
class CounterExample:
    def __init__(self, args): self.args = args
    def __bool__(self): return False
    def __repr__(self): return "counterexample: " + ", ".join(map(repr, self.args))


def ints(lo=-20, hi=20): return lambda r: r.randint(lo, hi)
def floats(lo=-100.0, hi=100.0): return lambda r: round(r.uniform(lo, hi), 3)
def strs(alphabet="abc ", max_len=8): return lambda r: "".join(r.choice(alphabet) for _ in range(r.randint(0, max_len)))
def lists(g, max_len=8, min_len=0): return lambda r: [g(r) for _ in range(r.randint(min_len, max_len))]
def tuples(*gs): return lambda r: tuple(g(r) for g in gs)
def pairs(lo=0, hi=20): return lambda r: sorted([r.randint(lo, hi), r.randint(lo, hi)])


def _fails(prop, args):
    try:
        return not prop(*copy.deepcopy(args))
    except BaseException:
        return True


def _smaller(v):
    if isinstance(v, bool):
        return []
    if isinstance(v, int):
        return [] if v == 0 else [0, v // 2, v - 1 if v > 0 else v + 1]
    if isinstance(v, float):
        return [] if v == 0 else [0.0, float(int(v))]
    if isinstance(v, (list, str)) and v:
        c = [v[:len(v) // 2], v[1:], v[:-1]] + [v[:i] + v[i + 1:] for i in range(min(len(v), 8))]
        if isinstance(v, list):
            c += [v[:i] + [0] + v[i + 1:] for i in range(min(len(v), 8)) if isinstance(v[i], int) and v[i] != 0]
        return [x for x in c if x != v and len(x) <= len(v)]
    return []


def _shrink(args, prop):
    cur = list(args)
    for _ in range(60):
        for i, v in enumerate(cur):
            hit = next((c for c in _smaller(v) if _fails(prop, tuple(cur[:i] + [c] + cur[i + 1:]))), None)
            if hit is not None:
                cur[i] = hit
                break
        else:
            break
    return tuple(cur)


def forall(gen, prop, n=200, seed=0):
    """True, or a falsy CounterExample holding a SHRUNK failing input. Exceptions in prop = failure."""
    r = random.Random(seed)
    for _ in range(n):
        x = gen(r)
        args = x if isinstance(x, tuple) else (x,)
        if _fails(prop, args):
            return CounterExample(_shrink(args, prop))
    return True


# ---------- loading / snippets ----------
def _base_ns(code):
    import collections, decimal, fractions, functools
    return {"__name__": "__sandbox__", "__source__": code, "math": math, "itertools": itertools,
            "functools": functools, "collections": collections, "Fraction": fractions.Fraction,
            "Decimal": decimal.Decimal, "forall": forall, "ints": ints, "floats": floats, "strs": strs,
            "lists": lists, "tuples": tuples, "pairs": pairs, "random": random}


def _load(code, ns, allow_exit=False):
    linecache.cache["<artifact>"] = (len(code), None, code.splitlines(True), "<artifact>")
    try:
        exec(compile(code, "<artifact>", "exec"), ns)
    except SyntaxError as e:
        return {"status": "syntax_error", "error": f"{e.msg} (line {e.lineno})"}
    except SystemExit:
        if not allow_exit:
            return {"status": "load_error", "error": "SystemExit on load"}
    except BaseException as e:
        return {"status": "load_error", "error": f"{type(e).__name__}: {e}"}
    return None


def _compile_snippet(src):
    try:
        return "eval", compile(src.strip(), "<expr>", "eval")
    except SyntaxError:
        return "exec", compile(src, "<snippet>", "exec")      # SyntaxError propagates => bad_attack


def _run_snippet(compiled, ns):
    kind, code = compiled
    if kind == "eval":
        return eval(code, ns)
    exec(code, ns)
    if "result" not in ns:
        raise NameError("snippet must assign `result`")
    return ns["result"]


def _explicit(tb):
    frames = [f for f in traceback.extract_tb(tb) if f.filename == "<artifact>"]
    return bool(frames) and (frames[-1].line or "").lstrip().startswith("raise")


def _judge(call, exp, ns):
    raised, tb, actual = None, None, None
    try:
        actual = call()
    except BaseException as e:
        raised, tb = e, e.__traceback__
    info = {} if raised is None else {"exc": type(raised).__name__, "explicit": _explicit(tb)}
    if re.fullmatch(r"[A-Z]\w*(?:Error|Exception)", exp):  # bare "TypeError" means "raises TypeError"
        exp = "raises " + exp
    m = re.match(r"(?is)raises\b\s*:?\s*(\w+)?\s*$", exp)
    if m:
        want = m.group(1)
        if raised is None:
            return {"status": "fail", "actual": _s(actual), "error": "did not raise"}
        ok = want is None or want in {c.__name__ for c in type(raised).__mro__}
        return {"status": "pass" if ok else "fail", "actual": f"raised {type(raised).__name__}", **info}
    if exp.lower().replace(" ", "_") == "no_error":
        if raised is None:
            return {"status": "pass", "actual": _s(actual)}
        return {"status": "fail", "actual": f"raised {type(raised).__name__}: {raised}"[:MAXLEN], **info}
    if raised is not None:
        return {"status": "fail", "actual": f"raised {type(raised).__name__}: {raised}"[:MAXLEN], **info}
    if exp in ("True", "False"):
        return {"status": "pass" if bool(actual) == (exp == "True") else "fail", "actual": _s(actual)}
    try:
        expv = eval(exp, ns)
    except BaseException as e:
        return {"status": "bad_attack", "error": f"expected not evaluable: {type(e).__name__}: {e}"}
    return {"status": "pass" if _eq(_norm(actual), _norm(expv)) else "fail", "actual": _s(actual)}


# ---------- modes ----------
def _probe(req):
    code, kind, exp = req["code"], req["kind"], req["expected"].strip()
    ns = _base_ns(code)
    if kind == "script":                                  # stdin -> stdout programs
        sys.stdin = io.StringIO(req.get("input", ""))
        buf = io.StringIO()
        ns["__name__"] = "__main__"
        with contextlib.redirect_stdout(buf):
            err = _load(code, ns, allow_exit=True)
        if err:
            return err
        try:
            e = ast.literal_eval(exp)
            exp = e if isinstance(e, str) else exp
        except Exception:
            pass
        n = lambda s: "\n".join(l.rstrip() for l in s.strip().splitlines())
        return {"status": "pass" if n(buf.getvalue()) == n(exp) else "fail", "actual": _s(buf.getvalue().strip())}
    err = _load(code, ns)
    if err:
        return err
    if kind == "test":
        fn = ns.get(req.get("entry") or "")
        if not callable(fn):
            return {"status": "no_entry", "error": f"entry function '{req.get('entry')}' not found"}
        try:
            inp = req["input"].strip()
            args = eval(f"({inp},)", ns) if inp else ()
        except BaseException as e:
            return {"status": "bad_attack", "error": f"input not evaluable: {type(e).__name__}: {e}"}
        return _judge(lambda: fn(*args), exp, ns)
    try:
        compiled = _compile_snippet(req["expr"])
    except SyntaxError as e:
        return {"status": "bad_attack", "error": f"snippet syntax: {e.msg}"}
    return _judge(lambda: _run_snippet(compiled, ns), exp, ns)


def _eval(req):
    from fractions import Fraction
    from decimal import Decimal
    ns = _base_ns("")
    try:
        compiled = _compile_snippet(req["expr"])
    except SyntaxError as e:
        return {"status": "bad_attack", "error": f"snippet syntax: {e.msg}"}
    try:
        v = _run_snippet(compiled, ns)
    except BaseException as e:
        return {"status": "bad_attack", "error": f"snippet failed: {type(e).__name__}: {e}"}
    num = float(v) if (_isnum(v) or isinstance(v, (Fraction, Decimal))) else None
    return {"status": "ok", "actual": _s(v), "num": num, "is_true": v is True,
            "text": v if isinstance(v, str) else None}


class _TO(BaseException):
    pass


def _limited(fn, seconds):
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _run(fn, args):
    try:
        return ("ok", _limited(lambda: fn(*copy.deepcopy(args)), 0.3))
    except _TO:
        return ("timeout", None)
    except BaseException as e:
        return ("exc", type(e).__name__)


SHAPES = {
    "list_int": lambda r: [r.randint(-9, 9) for _ in range(r.randint(0, 8))],
    "pairs": lambda r: [sorted([r.randint(0, 12), r.randint(0, 12)]) for _ in range(r.randint(0, 6))],
    "int": lambda r: r.randint(-20, 20),
    "nat": lambda r: r.randint(0, 30),
    "str": lambda r: "".join(r.choice("abc ") for _ in range(r.randint(0, 8))),
    "list_str": lambda r: ["".join(r.choice("abc") for _ in range(r.randint(0, 3))) for _ in range(r.randint(0, 6))],
    "list_nat": lambda r: [r.randint(0, 9) for _ in range(r.randint(1, 8))],
    "float": lambda r: round(r.uniform(-50, 50), 2),
}


def _majority(oks):
    for i, a in enumerate(oks):
        grp = [b for b in oks if _eq(_norm(a), _norm(b))]
        if len(grp) >= 2:
            return True, a
    return False, None


def _diff(req):
    import inspect
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(_TO()))
    deadline = time.monotonic() + req.get("budget", 2.5)
    fns = []
    for i, (code, ent) in enumerate(zip(req["codes"], req["entries"])):
        ns = _base_ns(code)
        err = _load(code, ns)
        fn = None if err else ns.get(ent or "")
        if i == 0 and not callable(fn):
            return {"status": "none", "note": "artifact entry unavailable"}
        if callable(fn):
            fns.append(fn)
    orcl = fns[1:]
    if not orcl:
        return {"status": "none", "note": "no usable oracle"}
    try:
        params = [p for p in inspect.signature(fns[0]).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty]
    except (TypeError, ValueError):
        return {"status": "none"}
    k = len(params)
    if not 1 <= k <= 3:
        return {"status": "none", "note": "unsupported arity"}
    order = list(SHAPES)
    combos = [(s,) * k for s in order] + list(itertools.islice(itertools.product(order, repeat=k), 60))
    rnd = random.Random(req.get("seed", 7))
    gen = lambda combo: tuple(SHAPES[s](rnd) for s in combo)
    valid, seen = [], set()
    for combo in combos:
        if combo in seen:
            continue
        seen.add(combo)
        if sum(_run(orcl[0], gen(combo))[0] == "ok" for _ in range(6)) >= 4:
            valid.append(combo)
        if len(valid) == 3:
            break

    def verdict(args):
        outs = [_run(f, args) for f in fns]
        oks = [o[1] for o in outs[1:] if o[0] == "ok"]
        has_maj, maj = _majority(oks) if len(orcl) >= 2 else (bool(oks), oks[0] if oks else None)
        if not has_maj:
            return False, None, outs[0]
        a = outs[0]
        bad = a[0] != "ok" or not _eq(_norm(a[1]), _norm(maj))
        return bad, maj, a

    for combo in valid:
        for _ in range(req.get("n", 150) // max(1, len(valid))):
            if time.monotonic() > deadline:
                return {"status": "none", "note": "budget"}
            args = gen(combo)
            bad, maj, a = verdict(args)
            if bad:
                small = _shrink(args, lambda *x: not verdict(x)[0])
                bad, maj, a = verdict(small)
                if bad and len(repr(maj)) < 400:
                    return {"status": "found", "input": ", ".join(repr(x) for x in small),
                            "expected": repr(maj), "actual": a[0] if a[0] != "ok" else _s(a[1])}
    return {"status": "none"}


def main():
    req = json.load(sys.stdin)
    out_stream = sys.__stdout__
    _jail(req.get("mem_mb", 512), int(req.get("cpu_s", 2)))
    try:
        sys.setrecursionlimit(3000)
    except Exception:
        pass
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        out = {"probe": _probe, "eval": _eval, "diff": _diff}[req["mode"]](req)
    out_stream.write("\n@@RESULT@@" + json.dumps(out) + "\n")
    out_stream.flush()


if __name__ == "__main__":
    main()
