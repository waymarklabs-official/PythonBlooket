"""Data classes describing the *typed* question formats.

Besides classic multiple choice, PyBlooket has three typed formats:

``blanks``  fill in the blanks of a code snippet (like the Canvas "fill in multiple
            blanks" quiz questions) -- graded by comparing text, nothing is executed;
``match``   match each item to one of a few options (like the Canvas matching
            questions) -- graded by index;
``code``    type real Python -- graded by running it in the sandbox
            (:mod:`pyblooket.sandbox`) against hidden test cases.

Everything here is plain data (no I/O) so generators can build it cheaply.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

BLANK_MARK_RE = re.compile(r"⟦(\d+)⟧")


def blank_mark(n: int) -> str:
    """The marker for blank number ``n`` (1-based) inside a ``code`` template."""
    return f"⟦{n}⟧"


class _Unset:
    """Sentinel: 'this case does not check the return value'."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _Unset()


# --------------------------------------------------------------------------
# blanks
# --------------------------------------------------------------------------


def _norm_text(s: str) -> str:
    """Whitespace-insensitive form of a short typed answer."""
    return re.sub(r"\s+", "", str(s))


def _norm_expr(s: str) -> str | None:
    """Canonical AST dump of an expression, or None if it doesn't parse."""
    try:
        return ast.dump(ast.parse(str(s).strip(), mode="eval"), annotate_fields=False)
    except (SyntaxError, ValueError):
        return None


@dataclass
class Blank:
    """One blank.  ``accepted`` lists every answer that counts (first one is shown).

    mode "text": the typed text must equal an accepted answer once all whitespace is
                 removed (so ``strip`` / ``strip()`` are different, ``1,4`` == ``1, 4``).
    mode "expr": the typed text must parse to the same Python expression as an accepted
                 answer (``n+1`` == ``n + 1``; quote style may differ: ``'a'`` == ``"a"``).
    ``ignore_case`` is for answers like ``true`` that we want to be forgiving about.
    """

    accepted: list[str]
    hint: str = ""
    mode: str = "text"
    ignore_case: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.accepted, str):
            self.accepted = [self.accepted]
        self.accepted = [str(a) for a in self.accepted]
        if not self.accepted or not all(a.strip() for a in self.accepted):
            raise ValueError("a blank needs at least one non-empty accepted answer")
        if self.mode not in ("text", "expr"):
            raise ValueError(f"bad blank mode {self.mode!r}")

    @property
    def width(self) -> int:
        return max(len(a) for a in self.accepted)

    def check(self, typed: Any) -> bool:
        if not isinstance(typed, str) or not typed.strip() or len(typed) > 200:
            return False
        if self.mode == "expr":
            got = _norm_expr(typed)
            if got is not None:
                return any(got == _norm_expr(a) for a in self.accepted)
        got_t = _norm_text(typed)
        if self.ignore_case:
            return any(got_t.lower() == _norm_text(a).lower() for a in self.accepted)
        return any(got_t == _norm_text(a) for a in self.accepted)

    def public(self, n: int) -> dict:
        return {"id": n, "hint": self.hint, "width": min(max(self.width, 3), 24)}


# --------------------------------------------------------------------------
# match
# --------------------------------------------------------------------------


@dataclass
class MatchSpec:
    """``items[i]`` must be matched with ``options[answer[i]]``."""

    items: list[str]
    options: list[str]
    answer: list[int]

    def __post_init__(self) -> None:
        if len(self.items) != len(self.answer) or len(self.items) < 2:
            raise ValueError("match needs >= 2 items and one answer per item")
        if len(set(self.options)) != len(self.options):
            raise ValueError("match options must be distinct")
        if any(not (0 <= a < len(self.options)) for a in self.answer):
            raise ValueError("match answer out of range")

    def public(self) -> dict:
        return {"items": list(self.items), "options": list(self.options)}


# --------------------------------------------------------------------------
# typed code
# --------------------------------------------------------------------------

CODE_MODES = ("function", "program", "expression")


def literal_roundtrips(value: Any) -> bool:
    """True if ``value`` survives ``ast.literal_eval(repr(value))`` unchanged."""
    try:
        back = ast.literal_eval(repr(value))
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False
    return back == value and type(back) is type(value)


@dataclass
class Case:
    """One test of a code task.

    function mode:    call ``func(*args)``; check the return value against ``ret`` and/or the
                      printed text against ``out`` (whichever is set).
    program mode:     run the student's statements with ``vars`` preset and ``input()``
                      answering from ``stdin`` (then the hidden ``after`` code, if any);
                      check the printed text against ``out`` and (optionally) variables
                      against ``expect_vars``.
    expression mode:  evaluate the student's expression with ``vars`` preset; compare to ``ret``.

    All data must be Python literals (``ast.literal_eval(repr(x)) == x``).
    """

    label: str = ""
    args: list = field(default_factory=list)
    ret: Any = UNSET
    out: str | None = None
    stdin: list[str] = field(default_factory=list)
    vars: dict = field(default_factory=dict)
    expect_vars: dict = field(default_factory=dict)
    # program mode only: *trusted* hidden code run right after the student's code, in the
    # same namespace -- e.g. "t = Triangle(4, 3)\nprint(t.area())" to test a class.
    after: str = ""

    def __post_init__(self) -> None:
        self.args = list(self.args)
        for v in [*self.args, *self.vars.values(), *self.expect_vars.values()]:
            if not literal_roundtrips(v):
                raise ValueError(f"case value is not a plain literal: {v!r}")
        if self.ret is not UNSET and not literal_roundtrips(self.ret):
            raise ValueError(f"expected value is not a plain literal: {self.ret!r}")
        self.stdin = [str(s) for s in self.stdin]

    def to_request(self) -> dict:
        return {
            "label": self.label,
            "args": repr(self.args),
            "has_ret": self.ret is not UNSET,
            "ret": None if self.ret is UNSET else repr(self.ret),
            "out": self.out,
            "stdin": list(self.stdin),
            "vars": {k: repr(v) for k, v in self.vars.items()},
            "expect_vars": {k: repr(v) for k, v in self.expect_vars.items()},
            "after": self.after,
        }

    def expected_text(self) -> str:
        parts = []
        if self.ret is not UNSET:
            parts.append(repr(self.ret))
        if self.out is not None:
            parts.append(self.out if self.out else "(nothing printed)")
        for k, v in self.expect_vars.items():
            parts.append(f"{k} == {v!r}")
        return "\n".join(parts)


@dataclass
class CodeTask:
    """A typed-code question: what the editor starts with, the tests, a model answer."""

    mode: str
    starter: str
    solution: str
    cases: list[Case]
    func: str = ""
    examples: int = 2  # the first N cases are shown to the player and used by "Run"
    lenient: bool = False  # allow 4 == 4.0 (default: ints and floats are different types)
    requires: list[tuple[str, str]] = field(default_factory=list)  # (regex, message)
    forbids: list[tuple[str, str]] = field(default_factory=list)  # (regex, message)
    note: str = ""  # one-line extra instruction shown under the prompt (e.g. "Don't use max()")

    def __post_init__(self) -> None:
        if self.mode not in CODE_MODES:
            raise ValueError(f"bad code mode {self.mode!r}")
        if not self.cases:
            raise ValueError("a code task needs at least one case")
        if self.mode == "function" and not self.func:
            raise ValueError("function tasks need `func`")
        self.examples = max(1, min(self.examples, len(self.cases)))
        for c in self.cases:
            if not c.label:
                c.label = self.default_label(c)

    # -- labels -----------------------------------------------------------
    def default_label(self, c: Case) -> str:
        if self.mode == "function":
            return f"{self.func}({', '.join(repr(a) for a in c.args)})"
        bits = [f"{k} = {v!r}" for k, v in c.vars.items()]
        if c.after:
            bits.append(c.after.strip().replace("\n", "; "))
        if c.stdin:
            bits.append("input: " + ", ".join(c.stdin))
        return "; ".join(bits) if bits else "run it"

    # -- what the client may see ------------------------------------------
    def public(self) -> dict:
        return {
            "mode": self.mode,
            "starter": self.starter,
            "func": self.func,
            "note": self.note,
            "examples": [
                {"label": c.label, "expected": c.expected_text(), "stdin": list(c.stdin)}
                for c in self.cases[: self.examples]
            ],
            "hidden_tests": max(0, len(self.cases) - self.examples),
        }
