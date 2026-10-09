"""Isolated runner for typed-code answers.  NOT imported by the app -- run as

    python -I -S _sandbox_runner.py  < request.json

It reads ONE JSON request on stdin and writes ONE line ``@@RESULT@@ {json}`` to stdout.
(The student's own ``print`` output is captured in memory, never written to stdout.)

Defence in depth (a classroom LAN is not the open internet, but students are creative):
  1. the code is parsed and walked *before* it runs: no imports, no dunder access, no
     generators/async (frames are reachable from them), no ``.format`` (it can walk
     attributes of any object);
  2. it runs with a tiny whitelist of builtins, in a namespace of its own;
  3. the whole process runs under CPU / memory / file-size limits (where the OS has them)
     and the parent kills it after a timeout;
  4. the process starts with -I -S and an empty environment, and the hidden test data is
     not reachable from anything the student's code can touch.

Request:  {"mode": "function"|"program"|"expression", "code": str, "func": str,
           "lenient": bool, "cases": [Case.to_request(), ...]}
"""

import ast
import builtins
import json
import math
import sys

REAL_STDOUT = sys.stdout
MARK = "@@RESULT@@ "

MAX_CODE_CHARS = 6000
MAX_CODE_LINES = 150
MAX_OUT_CHARS = 20000
MAX_SHOW = 300
CASE_SECONDS = 2


def emit(obj):
    REAL_STDOUT.write(MARK + json.dumps(obj) + "\n")
    REAL_STDOUT.flush()


def limit_resources():
    try:
        import resource
    except ImportError:  # Windows
        return
    for name, soft, hard in (
        ("RLIMIT_CPU", 6, 7),
        ("RLIMIT_AS", 768 * 1024 * 1024, 768 * 1024 * 1024),
        ("RLIMIT_FSIZE", 1024 * 1024, 1024 * 1024),
        ("RLIMIT_CORE", 0, 0),
        ("RLIMIT_NOFILE", 32, 32),
    ):
        try:
            resource.setrlimit(getattr(resource, name), (soft, hard))
        except (ValueError, OSError, AttributeError):
            pass  # e.g. macOS ignores RLIMIT_AS; the parent's timeout is the backstop


# --------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------

BANNED_ATTRS = {
    "format", "format_map", "mro",
    "gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "ag_frame", "ag_code",
    "f_globals", "f_locals", "f_back", "f_builtins", "f_code", "tb_frame", "tb_next",
    "co_code", "co_consts", "co_names", "func_globals", "func_code",
}
ALLOWED_DUNDER_ATTRS = {"__init__"}
ALLOWED_DUNDER_NAMES = {"__name__"}


class Rejected(Exception):
    pass


class Validator(ast.NodeVisitor):
    def fail(self, node, why):
        raise Rejected(f"line {getattr(node, 'lineno', '?')}: {why}")

    def visit_Import(self, node):
        self.fail(node, "`import` isn't available in this challenge")

    visit_ImportFrom = visit_Import

    def visit_Attribute(self, node):
        a = node.attr
        if a in BANNED_ATTRS:
            if a in ("format", "format_map"):
                self.fail(node, "`.format()` isn't available here - use an f-string instead")
            self.fail(node, f"`.{a}` isn't available in this challenge")
        if a.startswith("__") and a not in ALLOWED_DUNDER_ATTRS:
            self.fail(node, f"`.{a}` isn't available in this challenge")
        self.generic_visit(node)

    def visit_Name(self, node):
        n = node.id
        if n.startswith("__") and n not in ALLOWED_DUNDER_NAMES:
            self.fail(node, f"`{n}` isn't available in this challenge")
        self.generic_visit(node)

    def _no(self, node):
        self.fail(node, "generators and async code aren't available in this challenge")

    visit_Yield = visit_YieldFrom = visit_Await = visit_AsyncFunctionDef = _no
    visit_AsyncFor = visit_AsyncWith = visit_GeneratorExp = _no

    def visit_Match(self, node):
        # `case object(__globals__=g)` reads attributes by *string*, which the Attribute check can't see.
        self.fail(node, "`match` isn't available in this challenge")

    def visit_Global(self, node):
        for n in node.names:
            if n.startswith("__"):
                self.fail(node, f"`{n}` isn't available in this challenge")

    visit_Nonlocal = visit_Global


def validate(tree):
    Validator().visit(tree)


# --------------------------------------------------------------------------
# The namespace the student's code sees
# --------------------------------------------------------------------------


class OutputLimit(BaseException):
    pass


class CaseTimeout(BaseException):
    pass


def literal(text):
    return ast.literal_eval(text)


SAFE_NAMES = (
    "abs all any bin bool chr complex dict divmod enumerate filter float frozenset hex int "
    "isinstance issubclass iter len list map max min next oct ord pow range repr "
    "reversed round set slice sorted str sum tuple zip callable id hash "
    "Exception ArithmeticError AssertionError AttributeError IndexError KeyError "
    "LookupError NameError NotImplementedError OverflowError RecursionError "
    "RuntimeError StopIteration TypeError ValueError ZeroDivisionError "
    "BaseException object super property staticmethod classmethod "
    "True False None"
).split()


def make_builtins(stdin_lines, out_parts):
    """A fresh builtins dict for one case. ``out_parts`` collects what print() writes."""
    safe = {n: getattr(builtins, n) for n in SAFE_NAMES if hasattr(builtins, n)}
    safe["__build_class__"] = builtins.__build_class__
    safe["__name__"] = "builtins"
    queue = list(stdin_lines)
    written = [0]

    def student_print(*args, sep=" ", end="\n", file=None, flush=False):
        if sep is None:
            sep = " "
        if end is None:
            end = "\n"
        if not isinstance(sep, str) or not isinstance(end, str):
            raise TypeError("sep and end must be strings")
        text = sep.join(str(a) for a in args) + end
        written[0] += len(text)
        if written[0] > MAX_OUT_CHARS:
            raise OutputLimit()
        out_parts.append(text)

    def student_input(prompt=""):
        if queue:
            return queue.pop(0)
        raise EOFError("EOF when reading a line (the program asked for more input than it was given)")

    def student_type(*args):
        if len(args) != 1:
            raise TypeError("type() takes exactly one argument here")
        return type(args[0])

    safe["print"] = student_print
    safe["input"] = student_input
    safe["type"] = student_type
    return safe


# --------------------------------------------------------------------------
# Comparing results
# --------------------------------------------------------------------------


def same(a, b, lenient=False):
    """Equality that keeps bool/int/float/str/list/tuple distinct (floats within 1e-9)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    num_a, num_b = isinstance(a, (int, float)), isinstance(b, (int, float))
    if num_a and num_b:
        if type(a) is not type(b) and not lenient:
            return False
        if isinstance(a, float) or isinstance(b, float):
            if math.isnan(a) or math.isnan(b):
                return False
            return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y, lenient) for x, y in zip(a, b))
    if isinstance(a, dict):
        if set(map(repr, a)) != set(map(repr, b)):
            return False
        return all(k in b and same(a[k], b[k], lenient) for k in a)
    return a == b


def norm_output(text):
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    while lines and lines[0] == "":
        lines.pop(0)
    return "\n".join(lines)


def show(value):
    try:
        text = repr(value)
    except BaseException:  # a student's __repr__ may raise anything
        text = "<unprintable value>"
    return text if len(text) <= MAX_SHOW else text[: MAX_SHOW - 3] + "..."


def clip(text, n=MAX_SHOW):
    text = str(text)
    return text if len(text) <= n else text[: n - 3] + "..."


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------


def student_line(tb):
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<student>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def describe_error(exc):
    line = student_line(exc.__traceback__)
    where = f" (line {line})" if line else ""
    try:
        msg = str(exc)
    except BaseException:
        msg = ""
    return clip(f"{type(exc).__name__}: {msg}{where}" if msg else f"{type(exc).__name__}{where}", 240)


def install_timer():
    try:
        import signal

        def on_alarm(signum, frame):
            raise CaseTimeout()

        signal.signal(signal.SIGALRM, on_alarm)
        return signal
    except (ImportError, AttributeError, ValueError):
        return None


def run_case(compiled, mode, func, case, lenient, signal_mod):
    out_parts = []
    ns = {"__builtins__": make_builtins(case.get("stdin", []), out_parts), "__name__": "__main__"}
    for k, v in case.get("vars", {}).items():
        ns[k] = literal(v)
    res = {"label": case.get("label", ""), "ok": False, "got": "", "error": None, "stdout": ""}
    got = None
    has_got = False
    skip = 0  # function mode: ignore anything the module-level code printed
    try:
        if signal_mod:
            signal_mod.setitimer(signal_mod.ITIMER_REAL, CASE_SECONDS)
        try:
            if mode == "expression":
                got = eval(compiled, ns)
                has_got = True
            elif mode == "program":
                exec(compiled, ns)
                if case.get("after"):
                    exec(compile(case["after"], "<harness>", "exec"), ns)
            else:
                exec(compiled, ns)
                skip = len(out_parts)
                fn = ns.get(func)
                if not callable(fn):
                    raise NameError(f"no function named {func!r} was found - check the spelling of its name")
                got = fn(*literal(case.get("args", "[]")))
                has_got = True
        finally:
            if signal_mod:
                signal_mod.setitimer(signal_mod.ITIMER_REAL, 0)
    except CaseTimeout:
        res["error"] = "It took too long - is there a loop that never ends?"
        res["timeout"] = True
        res["stdout"] = clip("".join(out_parts), 400)
        return res
    except OutputLimit:
        res["error"] = "It printed far too much text - is there a loop that never ends?"
        res["stdout"] = clip("".join(out_parts), 400)
        return res
    except RecursionError as exc:
        res["error"] = clip(describe_error(exc))
        res["stdout"] = clip("".join(out_parts), 400)
        return res
    except BaseException as exc:  # includes SystemExit / KeyboardInterrupt from student code
        res["error"] = describe_error(exc)
        res["stdout"] = clip("".join(out_parts), 400)
        return res

    text = "".join(out_parts[skip:])
    res["stdout"] = clip(text, 400)
    ok = True
    shown = []
    if case.get("has_ret"):
        want = literal(case["ret"])
        ok = ok and has_got and same(got, want, lenient)
        shown.append(show(got) if has_got else "(nothing)")
    if case.get("out") is not None:
        ok = ok and norm_output(text) == norm_output(case["out"])
        shown.append(clip(text.rstrip("\n")) if text.strip() else "(nothing printed)")
    for name, want_repr in case.get("expect_vars", {}).items():
        if name in ns and same(ns[name], literal(want_repr), lenient):
            continue
        ok = False
        shown.append(f"{name} = {show(ns[name])}" if name in ns else f"{name} was never created")
    if not shown:
        shown.append(show(got) if has_got else "")
    res["ok"] = ok
    res["got"] = "\n".join(shown)
    return res


def main():
    limit_resources()
    try:
        req = json.loads(sys.stdin.read())
        mode = req["mode"]
        code = req["code"]
        func = req.get("func", "")
        lenient = bool(req.get("lenient"))
        cases = req["cases"]
        if mode not in ("function", "program", "expression") or not isinstance(code, str):
            raise ValueError("bad request")
    except Exception as exc:  # noqa: BLE001
        emit({"status": "error", "message": f"bad request: {exc}"})
        return
    req = None  # nothing but `cases` (needed below) stays alive

    if len(code) > MAX_CODE_CHARS or code.count("\n") > MAX_CODE_LINES:
        emit({"status": "rejected", "message": "That answer is too long for this challenge."})
        return
    if "\x00" in code:
        emit({"status": "rejected", "message": "Your code contains an invalid character."})
        return

    try:
        tree = ast.parse(code.strip() if mode == "expression" else code, "<student>", "eval" if mode == "expression" else "exec")
    except SyntaxError as exc:
        line = exc.lineno
        detail = clip(exc.msg or "invalid syntax", 120)
        msg = f"SyntaxError: {detail}" + (f" (line {line})" if line else "")
        if mode == "expression" and "invalid syntax" in detail:
            msg += " - type a single expression (no `=` and no multiple lines)"
        emit({"status": "syntax_error", "message": msg})
        return
    except (ValueError, RecursionError, MemoryError) as exc:
        emit({"status": "syntax_error", "message": clip(f"SyntaxError: {exc}", 160)})
        return
    try:
        validate(tree)
    except Rejected as exc:
        emit({"status": "rejected", "message": str(exc)})
        return
    compiled = compile(tree, "<student>", "eval" if mode == "expression" else "exec")

    signal_mod = install_timer()
    results = []
    for case in cases:
        r = run_case(compiled, mode, func, case, lenient, signal_mod)
        results.append(r)
        if r.get("timeout"):
            break
    emit({"status": "ok", "results": results})


if __name__ == "__main__":
    main()
