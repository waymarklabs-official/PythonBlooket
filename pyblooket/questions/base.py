"""Core building blocks shared by every question generator.

A *generator* is a function ``fn(rng: random.Random) -> Question`` registered
with :func:`generator`.  Generators must draw all randomness from ``rng`` so a
given seed always yields the same question.

Correctness is enforced by construction wherever possible: the helpers below
*execute* the generated snippet to compute the right answer, and drop any
distractor that turns out to be equal to it.
"""

from __future__ import annotations

import builtins
import io
import random
import threading
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .spec import BLANK_MARK_RE, UNSET, Blank, Case, CodeTask, MatchSpec, blank_mark

EASY, MEDIUM, HARD = 1, 2, 3
DIFFICULTIES = (EASY, MEDIUM, HARD)
DIFFICULTY_LABELS = {EASY: "Easy", MEDIUM: "Medium", HARD: "Hard"}
DIFFICULTY_POINTS = {EASY: 100, MEDIUM: 250, HARD: 500}

# Question formats.  "choice" is classic multiple choice; the others are typed / matched:
#   blanks  fill in the blanks of a code snippet      (graded by text, nothing runs)
#   match   match each item to one of a few options   (graded by index)
#   code    type real Python                          (graded by running it in the sandbox)
QTYPES = ("choice", "blanks", "match", "code")
QTYPE_LABELS = {
    "choice": "Multiple choice",
    "blanks": "Fill in the blanks",
    "match": "Matching",
    "code": "Write the code",
}
# How much longer than a multiple-choice question each format gets when a mode has a timer.
TIME_FACTOR = {"choice": 1.0, "blanks": 2.0, "match": 2.0, "code": 6.0}

NUM_CHOICES = 4
NOTHING_PRINTED = "(nothing is printed)"
MAX_CHOICE_LINES = 6
MAX_CHOICE_LINE_LEN = 60


class GenerationError(Exception):
    """Raised when a generator cannot produce a valid question for a seed."""


@dataclass
class Grade:
    """The verdict on one response."""

    correct: bool
    detail: dict = field(default_factory=dict)


@dataclass
class Question:
    topic: str
    difficulty: int
    prompt: str
    choices: list[str]
    answer: int
    explanation: str
    code: str | None = None
    # "output": choices[answer] is exactly what ``code`` prints (tests re-run it).
    # "other": any other question style (value of an expression, concept, ...).
    kind: str = "other"
    qtype: str = "choice"
    blanks: list[Blank] = field(default_factory=list)  # qtype "blanks": markers in ``code``
    match: MatchSpec | None = None  # qtype "match"
    task: CodeTask | None = None  # qtype "code"
    # qtype "blanks": what the snippet prints once filled in (tests re-run it). None = not checked.
    expect_output: str | None = None

    @property
    def points(self) -> int:
        return DIFFICULTY_POINTS[self.difficulty]

    @property
    def time_factor(self) -> float:
        return TIME_FACTOR[self.qtype]

    def public_dict(self) -> dict:
        """Everything the client may see before answering (no answer!)."""
        data = {
            "topic": self.topic,
            "difficulty": self.difficulty,
            "difficulty_label": DIFFICULTY_LABELS[self.difficulty],
            "points": self.points,
            "prompt": self.prompt,
            "code": self.code,
            "qtype": self.qtype,
            "time_factor": self.time_factor,
            "choices": list(self.choices),
        }
        if self.qtype == "blanks":
            data["blanks"] = [b.public(i + 1) for i, b in enumerate(self.blanks)]
        elif self.qtype == "match" and self.match is not None:
            data["match"] = self.match.public()
        elif self.qtype == "code" and self.task is not None:
            data["task"] = self.task.public()
        return data

    # -- grading ------------------------------------------------------------
    def grade(self, response) -> Grade:
        """Judge a player's response. Formats: choice -> int index (None = no answer),
        blanks -> list[str], match -> list[int], code -> str."""
        if self.qtype == "choice":
            ok = isinstance(response, int) and not isinstance(response, bool) and response == self.answer
            return Grade(ok)
        if self.qtype == "blanks":
            if not isinstance(response, list) or len(response) != len(self.blanks):
                return Grade(False, {"blanks": [False] * len(self.blanks)})
            marks = [b.check(r) for b, r in zip(self.blanks, response)]
            return Grade(all(marks), {"blanks": marks})
        if self.qtype == "match" and self.match is not None:
            n = len(self.match.items)
            if (
                not isinstance(response, list)
                or len(response) != n
                or any(not isinstance(r, int) or isinstance(r, bool) for r in response)
            ):
                return Grade(False, {"match": [False] * n})
            marks = [r == a for r, a in zip(response, self.match.answer)]
            return Grade(all(marks), {"match": marks})
        if self.qtype == "code" and self.task is not None:
            from ..sandbox import grade_task  # lazy: only code questions need the sandbox

            result = grade_task(self.task, response if isinstance(response, str) else "")
            return Grade(bool(result["correct"]), result)
        return Grade(False)

    def run_examples(self, code: str) -> dict:
        """The "Run" button: try the code on the visible examples (never an answer)."""
        from ..sandbox import grade_task

        if self.qtype != "code" or self.task is None:
            return {"status": "error", "message": "This question can't be run.", "cases": []}
        return grade_task(self.task, code if isinstance(code, str) else "", only_examples=True)

    def reveal(self) -> dict:
        """The correct answer in a form the client can show once the question is over."""
        if self.qtype == "choice":
            return {"answer": self.answer}
        if self.qtype == "blanks":
            return {"blanks": [b.accepted[0] for b in self.blanks], "accepted": [list(b.accepted) for b in self.blanks]}
        if self.qtype == "match" and self.match is not None:
            return {"match": list(self.match.answer)}
        if self.qtype == "code" and self.task is not None:
            return {"solution": self.task.solution}
        return {}

    def answer_text(self) -> str:
        """A one-line plain-text version of the correct answer (for exports)."""
        if self.qtype == "choice":
            return self.choices[self.answer]
        if self.qtype == "blanks":
            return " | ".join(b.accepted[0] for b in self.blanks)
        if self.qtype == "match" and self.match is not None:
            return "; ".join(f"{i} -> {self.match.options[a]}" for i, a in zip(self.match.items, self.match.answer))
        if self.qtype == "code" and self.task is not None:
            return self.task.solution
        return ""


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

GeneratorFn = Callable[[random.Random], Question]


@dataclass
class RegisteredGenerator:
    topic: str
    difficulty: int
    fn: GeneratorFn
    name: str = field(default="")
    qtype: str = "choice"


REGISTRY: list[RegisteredGenerator] = []


def generator(topic: str, difficulty: int, qtype: str = "choice"):
    """Decorator registering ``fn(rng) -> Question`` for a topic/difficulty/format.

    ``qtype`` must match the ``qtype`` of every Question the function returns."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"bad difficulty {difficulty!r}")
    if qtype not in QTYPES:
        raise ValueError(f"bad qtype {qtype!r}")

    def deco(fn: GeneratorFn) -> GeneratorFn:
        REGISTRY.append(
            RegisteredGenerator(topic, difficulty, fn, f"{fn.__module__}.{fn.__name__}", qtype)
        )
        return fn

    return deco


# --------------------------------------------------------------------------
# Running snippets
# --------------------------------------------------------------------------

_EXEC_LOCK = threading.Lock()


@dataclass
class RunResult:
    output: str  # captured stdout with the final newline stripped
    error: str | None  # exception class name, or None if it ran cleanly
    namespace: dict


def run_code(code: str) -> RunResult:
    """Execute a *generated* snippet and capture what it prints.

    Only ever call this on code produced by our own generators, never on user
    input. ``print`` is redirected per call (not via sys.stdout) so concurrent
    requests can't interleave output; the lock is belt-and-braces.
    """
    buf = io.StringIO()

    def _print(*args, **kwargs):
        kwargs.setdefault("file", buf)
        builtins.print(*args, **kwargs)

    ns: dict = {"__name__": "__main__", "print": _print}
    error = None
    with _EXEC_LOCK:
        try:
            exec(compile(code, "<snippet>", "exec"), ns)
        except Exception as exc:  # noqa: BLE001 - we want the class name
            error = type(exc).__name__
    out = buf.getvalue()
    if out.endswith("\n"):
        out = out[:-1]
    return RunResult(out, error, ns)


def eval_expr(expr: str, setup: str = "") -> object:
    """Evaluate ``expr`` after running ``setup``. Raises on error."""
    res = run_code(setup)
    if res.error:
        raise GenerationError(f"setup raised {res.error}")
    ns = res.namespace
    with _EXEC_LOCK:
        return eval(compile(expr, "<expr>", "eval"), ns)


def error_choice(exc_name: str) -> str:
    """How a raised exception is shown as an answer choice."""
    return f"Error: {exc_name}"


def display_output(output: str) -> str:
    return output if output != "" else NOTHING_PRINTED


# --------------------------------------------------------------------------
# Building questions
# --------------------------------------------------------------------------


def _norm(choice: str) -> str:
    return "\n".join(line.rstrip() for line in str(choice).strip("\n").split("\n"))


def _check_choice_shape(choice: str) -> None:
    lines = choice.split("\n")
    if len(lines) > MAX_CHOICE_LINES:
        raise GenerationError(f"choice has {len(lines)} lines: {choice!r}")
    for line in lines:
        if len(line) > MAX_CHOICE_LINE_LEN:
            raise GenerationError(f"choice line too long: {line!r}")
    if not choice.strip():
        raise GenerationError("empty choice")


def build_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    correct: str,
    distractors: Iterable[str],
    explanation: str,
    rng: random.Random,
    code: str | None = None,
    kind: str = "other",
) -> Question:
    """Assemble a multiple-choice question.

    ``distractors`` may contain duplicates or even the correct answer; they are
    de-duplicated (after normalising whitespace) and the first three distinct
    wrong ones are used, in the order given.  Put your most plausible wrong
    answers first.  Raises :class:`GenerationError` if fewer than three remain.
    """
    correct = _norm(correct)
    seen = {correct}
    wrong: list[str] = []
    for d in distractors:
        d = _norm(d)
        if d in seen or not d.strip():
            continue
        seen.add(d)
        wrong.append(d)
        if len(wrong) == NUM_CHOICES - 1:
            break
    if len(wrong) < NUM_CHOICES - 1:
        raise GenerationError(f"only {len(wrong)} distinct distractors for {correct!r}")
    choices = [correct, *wrong]
    for c in choices:
        _check_choice_shape(c)
    rng.shuffle(choices)
    return Question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        choices=choices,
        answer=choices.index(correct),
        explanation=explanation,
        code=code,
        kind=kind,
    )


def output_question(
    *,
    topic: str,
    difficulty: int,
    code: str,
    distractors: Iterable[str],
    explanation: str,
    rng: random.Random,
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    """'What does this print?' — the correct answer is computed by running ``code``.

    If ``allow_error`` is true and the code raises, the correct answer becomes
    ``error_choice(ExcName)`` (and the prompt should say so, e.g. "What is
    printed, or which error is raised?").  Otherwise raising is a bug.
    Empty output is shown as :data:`NOTHING_PRINTED`.
    """
    code = code.strip("\n")
    res = run_code(code)
    if res.error:
        if not allow_error:
            raise GenerationError(f"snippet raised {res.error}:\n{code}")
        correct = error_choice(res.error)
    else:
        correct = display_output(res.output)
    return build_question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=[display_output(d) if d == "" else d for d in distractors],
        explanation=explanation,
        rng=rng,
        code=code,
        kind="output",
    )


def which_expression_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    setup: str,
    target: object,
    correct_expr: str,
    wrong_exprs: Iterable[str],
    explanation: str,
    rng: random.Random,
) -> Question:
    """'Which expression evaluates to X?' — verified by evaluation.

    ``correct_expr`` must evaluate to ``target``; any wrong expression that
    *also* evaluates to ``target`` (or raises, if target isn't an error) is
    discarded automatically, so exactly one choice is right.
    """
    if eval_expr(correct_expr, setup) != target:
        raise GenerationError(f"{correct_expr!r} does not evaluate to {target!r}")
    wrong = []
    for e in wrong_exprs:
        try:
            val = eval_expr(e, setup)
        except Exception:  # noqa: BLE001 - erroring expressions are fine distractors
            wrong.append(e)
            continue
        # Drop anything equal to the target (6.0 == 6 would make two right answers).
        if val != target:
            wrong.append(e)
    return build_question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct_expr,
        distractors=wrong,
        explanation=explanation,
        rng=rng,
        code=setup.strip("\n") or None,
    )


# --------------------------------------------------------------------------
# Typed formats: blanks, match, code
# --------------------------------------------------------------------------

MAX_BLANKS = 4
MAX_SNIPPET_LINES = 18


def fill_template(template: str, answers: list[str]) -> str:
    """``template`` with every ⟦n⟧ marker replaced by ``answers[n-1]``."""
    return BLANK_MARK_RE.sub(lambda m: answers[int(m.group(1)) - 1], template)


def blanks_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    template: str,
    blanks: list[Blank],
    explanation: str,
    expect_output: str | None = None,
) -> Question:
    """'Fill in the blanks' (typed).  ``template`` is the snippet with ⟦1⟧, ⟦2⟧ ... markers
    (``blank_mark(n)``), one per Blank, each appearing exactly once.

    If ``expect_output`` is given, the snippet is run with every accepted answer (one
    blank at a time) and must print exactly that text -- so a wrong "accepted" answer is
    a generator bug, not a quiz bug.  Pass ``""`` for "prints nothing".
    """
    template = template.strip("\n")
    marks = [int(m) for m in BLANK_MARK_RE.findall(template)]
    if sorted(marks) != list(range(1, len(blanks) + 1)) or not 1 <= len(blanks) <= MAX_BLANKS:
        raise GenerationError(f"template markers {marks} don't match {len(blanks)} blank(s)")
    if len(template.split("\n")) > MAX_SNIPPET_LINES:
        raise GenerationError("blanks snippet too long")
    if expect_output is not None:
        firsts = [b.accepted[0] for b in blanks]
        variants = [firsts]
        for i, b in enumerate(blanks):
            for alt in b.accepted[1:]:
                variants.append([*firsts[:i], alt, *firsts[i + 1 :]])
        for answers in variants:
            res = run_code(fill_template(template, answers))
            if res.error or _norm(res.output) != _norm(expect_output):
                raise GenerationError(
                    f"blanks {answers!r} print {res.output!r} (error {res.error}), wanted {expect_output!r}"
                )
    return Question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        choices=[],
        answer=-1,
        explanation=explanation,
        code=template,
        kind="other",
        qtype="blanks",
        blanks=blanks,
        expect_output=expect_output,
    )


def match_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    pairs: list[tuple[str, str]],
    explanation: str,
    rng: random.Random,
    extra_options: Iterable[str] = (),
    code: str | None = None,
) -> Question:
    """'Match each item to its ...'.  ``pairs`` = [(item, right answer), ...] (3-6 pairs).
    Several items may share an answer (e.g. five values -> "True"/"False").  The option
    list is the distinct answers plus ``extra_options``, shuffled."""
    if not 3 <= len(pairs) <= 6:
        raise GenerationError(f"match needs 3-6 pairs, got {len(pairs)}")
    options: list[str] = []
    for _, a in [*pairs, *[(None, e) for e in extra_options]]:
        if a not in options:
            options.append(a)
    if len(options) < 2:
        raise GenerationError("match needs at least 2 distinct options")
    if len({a for _, a in pairs}) < 2:
        raise GenerationError("all match answers are the same")
    items = [i for i, _ in pairs]
    if len(set(items)) != len(items):
        raise GenerationError("duplicate match items")
    order = list(range(len(pairs)))
    rng.shuffle(order)
    rng.shuffle(options)
    spec = MatchSpec(
        items=[pairs[i][0] for i in order],
        options=options,
        answer=[options.index(pairs[i][1]) for i in order],
    )
    for text in [*spec.items, *spec.options]:
        if len(text) > MAX_CHOICE_LINE_LEN or "\n" in text:
            raise GenerationError(f"match text too long: {text!r}")
    return Question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        choices=[],
        answer=-1,
        explanation=explanation,
        code=code,
        qtype="match",
        match=spec,
    )


def fn_cases(pairs) -> list[Case]:
    """Cases for a function task from ``[(args_tuple, expected_return), ...]``."""
    return [Case(args=list(a), ret=r) for a, r in pairs]


def selfcheck_task(task: CodeTask) -> None:
    """Run the *reference solution* against every case in-process (it is our own trusted
    code), and make sure it also passes the sandbox's static checks.  Raises
    :class:`GenerationError` on any mismatch -- typed questions are correct by construction.
    """
    import ast
    import copy

    from .._sandbox_runner import Rejected, same, validate
    from ..sandbox import check_requirements

    try:
        tree = ast.parse(task.solution if task.mode != "expression" else task.solution.strip(), "<solution>",
                         "eval" if task.mode == "expression" else "exec")
        validate(tree)
    except (SyntaxError, Rejected) as exc:
        raise GenerationError(f"reference solution is not valid sandbox code: {exc}") from exc
    problem = check_requirements(task, task.solution)
    if problem:
        raise GenerationError(f"reference solution breaks its own requirement: {problem}")

    for case in task.cases:
        out: list[str] = []
        stdin = list(case.stdin)

        def _print(*args, sep=" ", end="\n", **_kw):
            out.append((sep or " ").join(str(a) for a in args) + (end if end is not None else "\n"))

        def _input(prompt=""):
            if not stdin:
                raise EOFError("solution asked for more input than the case provides")
            return stdin.pop(0)

        ns: dict = {"__name__": "__main__", "print": _print, "input": _input}
        ns.update(copy.deepcopy(case.vars))
        got = None
        has_got = False
        try:
            with _EXEC_LOCK:
                if task.mode == "expression":
                    got, has_got = eval(compile(task.solution.strip(), "<solution>", "eval"), ns), True
                else:
                    exec(compile(task.solution, "<solution>", "exec"), ns)
                    if task.mode == "program" and case.after:
                        exec(compile(case.after, "<harness>", "exec"), ns)
                    if task.mode == "function":
                        skip = len(out)
                        got, has_got = ns[task.func](*copy.deepcopy(case.args)), True
                        out = out[skip:]
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"reference solution raised {type(exc).__name__}: {exc} on {case.label or case.args}") from exc
        if case.ret is not UNSET and not (has_got and same(got, case.ret, task.lenient)):
            raise GenerationError(f"reference solution returned {got!r}, case expects {case.ret!r} ({case.label})")
        if case.out is not None:
            from .._sandbox_runner import norm_output

            if norm_output("".join(out)) != norm_output(case.out):
                raise GenerationError(f"reference solution printed {''.join(out)!r}, case expects {case.out!r}")
        for name, want in case.expect_vars.items():
            if name not in ns or not same(ns[name], want, task.lenient):
                raise GenerationError(f"reference solution leaves {name} = {ns.get(name)!r}, expected {want!r}")


def code_question(
    *,
    topic: str,
    difficulty: int,
    prompt: str,
    task: CodeTask,
    explanation: str,
    code: str | None = None,
) -> Question:
    """'Write the code' (typed, graded by the sandbox).  ``code`` is optional context shown
    above the editor (e.g. the variables that already exist).  The reference solution is
    verified against the cases before the question is returned."""
    selfcheck_task(task)
    return Question(
        topic=topic,
        difficulty=difficulty,
        prompt=prompt,
        choices=[],
        answer=-1,
        explanation=explanation,
        code=code,
        qtype="code",
        task=task,
    )


def function_task(
    func: str,
    solution: str,
    cases,
    *,
    starter: str | None = None,
    examples: int = 2,
    **kw,
) -> CodeTask:
    """A 'write the function' task. ``cases`` = [(args_tuple, expected_return), ...] or Case objects.
    The default starter is the solution's ``def`` line plus an indented blank line."""
    solution = solution.strip("\n")
    if starter is None:
        starter = solution.split("\n")[0] + "\n    "
    cs = [c if isinstance(c, Case) else Case(args=list(c[0]), ret=c[1]) for c in cases]
    return CodeTask("function", starter, solution, cs, func=func, examples=examples, **kw)


def program_task(solution: str, cases, *, starter: str = "", examples: int = 1, **kw) -> CodeTask:
    """A 'write the program' task. ``cases`` = Case objects or dicts of Case fields
    (``stdin=[...]``, ``vars={...}``, ``out="..."``, ``expect_vars={...}``)."""
    cs = [c if isinstance(c, Case) else Case(**c) for c in cases]
    return CodeTask("program", starter, solution.strip("\n"), cs, examples=examples, **kw)


def expression_task(solution: str, cases, *, starter: str = "", examples: int = 2, **kw) -> CodeTask:
    """A 'type an expression' task. ``cases`` = [(vars_dict, expected_value), ...] or Case objects."""
    cs = [c if isinstance(c, Case) else Case(vars=dict(c[0]), ret=c[1]) for c in cases]
    return CodeTask("expression", starter, solution.strip(), cs, examples=examples, **kw)


# --------------------------------------------------------------------------
# Small helpers for making varied snippets / distractors
# --------------------------------------------------------------------------

VAR_NAMES = ["a", "b", "c", "x", "y", "z", "n", "m", "total", "count", "val", "num"]
WORDS = [
    "apple", "banana", "cherry", "python", "code", "loop", "snake", "pixel",
    "rocket", "tiger", "lemon", "mango", "orbit", "quest", "blook", "candy",
]
NAMES = ["Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon"]


def pick_vars(rng: random.Random, k: int) -> list[str]:
    return rng.sample(VAR_NAMES, k)


def int_distractors(correct: int, rng: random.Random, spread: int = 3) -> list[str]:
    """Nearby integers, shuffled — a generic fallback for numeric answers."""
    cands = {correct + d for d in range(-spread, spread + 1) if d}
    cands |= {correct * 2, -correct}
    cands.discard(correct)
    out = sorted(cands)
    rng.shuffle(out)
    return [str(c) for c in out]
