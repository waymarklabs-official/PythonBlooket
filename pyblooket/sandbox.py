"""Run a player's typed code against a :class:`~pyblooket.questions.spec.CodeTask`.

The code runs in a *separate* Python process (``_sandbox_runner.py``) that is started
with ``-I -S`` and an empty environment, limited in CPU/memory, and killed after a
timeout.  See that file for the static checks and the restricted builtins.

Set ``PYBLOOKET_CODE=off`` to disable typed-code grading entirely (the question
generators still work; the server then never serves ``code`` questions).
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import tokenize

from .questions.spec import CodeTask

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sandbox_runner.py")
MARK = "@@RESULT@@ "
PROCESS_TIMEOUT = float(os.environ.get("PYBLOOKET_CODE_TIMEOUT", "10"))
MAX_CONCURRENT = int(os.environ.get("PYBLOOKET_CODE_WORKERS", "4"))
MAX_CODE_CHARS = 6000

_slots = threading.BoundedSemaphore(MAX_CONCURRENT)


def enabled() -> bool:
    return os.environ.get("PYBLOOKET_CODE", "on").strip().lower() not in ("off", "0", "false", "no")


def _child_env() -> dict:
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    for k in ("SYSTEMROOT", "SystemRoot", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def run_request(request: dict, timeout: float = PROCESS_TIMEOUT) -> dict:
    """Send ``request`` to a sandbox process; always returns a dict with a ``status``."""
    payload = json.dumps(request)
    kwargs: dict = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    with _slots:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", RUNNER],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=_child_env(),
                cwd=tempfile.gettempdir(),
                **kwargs,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Your code took too long to finish - is there a loop that never ends?"}
        except OSError as exc:
            return {"status": "error", "message": f"Couldn't start the code checker: {exc}"}
    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith(MARK):
            try:
                return json.loads(line[len(MARK):])
            except ValueError:
                break
    if proc.returncode and proc.returncode < 0:
        return {"status": "timeout", "message": "Your code used too much time or memory and was stopped."}
    return {"status": "error", "message": "The code checker crashed - please try again."}


# --------------------------------------------------------------------------
# Requirements such as "use a for loop"
# --------------------------------------------------------------------------


def code_skeleton(code: str) -> str:
    """The code with comments removed and string contents blanked (for regex checks)."""
    try:
        out = []
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING:
                # keep the quotes / f prefix, drop the contents
                m = re.match(r"^([rRbBuUfF]*)('''|\"\"\"|'|\")", tok.string)
                out.append((m.group(1) + m.group(2) * 2) if m else '""')
                continue
            out.append(tok.string if tok.type not in (tokenize.NL, tokenize.NEWLINE) else "\n")
        return " ".join(out)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return code


def check_requirements(task: CodeTask, code: str) -> str | None:
    skeleton = code_skeleton(code)
    for pattern, message in task.requires:
        if not re.search(pattern, skeleton):
            return message
    for pattern, message in task.forbids:
        if re.search(pattern, skeleton):
            return message
    return None


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------


def grade_task(task: CodeTask, code: str, *, only_examples: bool = False) -> dict:
    """Run ``code`` on the task's cases.

    Returns ``{"status", "correct", "passed", "total", "message", "cases": [...]}``.
    ``only_examples`` (the "Run" button) uses just the visible example cases and never
    counts as an answer.  Each entry of ``cases`` has ``label``, ``ok``, ``expected``,
    ``got``, ``error`` and ``hidden`` (True for cases the player hasn't been shown).
    """
    cases = task.cases[: task.examples] if only_examples else task.cases
    total = len(cases)
    base = {"status": "ok", "correct": False, "passed": 0, "total": total, "message": "", "cases": []}
    if not isinstance(code, str) or not code.strip():
        base.update(status="empty", message="Type some code first!")
        return base
    if len(code) > MAX_CODE_CHARS:
        base.update(status="rejected", message="That answer is too long for this challenge.")
        return base
    if not enabled():
        base.update(status="error", message="Typed-code questions are turned off on this server.")
        return base

    reply = run_request(
        {
            "mode": task.mode,
            "code": code,
            "func": task.func,
            "lenient": task.lenient,
            "cases": [c.to_request() for c in cases],
        }
    )
    status = reply.get("status", "error")
    if status != "ok":
        base.update(status=status, message=reply.get("message", "Something went wrong."))
        return base

    results = reply.get("results", [])
    out_cases = []
    for i, c in enumerate(cases):
        r = results[i] if i < len(results) else {"ok": False, "got": "", "error": "(not run)"}
        out_cases.append(
            {
                "label": c.label,
                "ok": bool(r.get("ok")),
                "expected": c.expected_text(),
                "got": r.get("got", ""),
                "error": r.get("error"),
                "stdout": r.get("stdout", ""),
                "hidden": (i >= task.examples),
            }
        )
    passed = sum(1 for c in out_cases if c["ok"])
    base.update(cases=out_cases, passed=passed)
    timed_out = any((r.get("timeout") for r in results))
    if timed_out:
        base["status"] = "timeout"
        base["message"] = "Your code took too long to finish - is there a loop that never ends?"
        return base
    problem = check_requirements(task, code) if passed == total else None
    if problem:
        base.update(status="requirements", message=problem)
        return base
    base["correct"] = passed == total
    if passed == total:
        base["message"] = "All tests passed!" if total > 1 else "Test passed!"
    else:
        base["message"] = f"{passed} of {total} tests passed."
    return base


def verify_solution(task: CodeTask) -> dict:
    """Used by the tests: the reference solution must pass every case."""
    return grade_task(task, task.solution)
