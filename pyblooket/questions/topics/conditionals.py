"""Question generators for the "conditionals" topic (CSF.2.H: Conditionals).

Everything here follows the lesson: the driver's-license ``if / else`` (age 16), the grade
``elif`` ladder (score 85 -> ``Grade: B``) and why the ORDER of the thresholds matters, combining
conditions with ``and`` / ``or`` / ``not`` (``temperature = 72``, ``is_raining``), nested
conditionals (the ``money`` snack / drink code), indentation, the missing-colon and ``=`` vs
``==`` pitfalls, the Quick Debug Trick, the Sign Checker and Number Test mini-challenges, the
even / odd ``%`` check and the Programming Assessment's Rank Checker (Bronze / Silver / Gold and
the Diamond bonus).

The formats mirror the Canvas quizzes: short concept questions, "what does this print", "which
line fixes it", fill-in-the-blanks, matching and typed code (graded in the sandbox).
"""

from __future__ import annotations

import operator
import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NOTHING_PRINTED,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    display_output,
    error_choice,
    expression_task,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "conditionals"

_CMP = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}
_FLIP = {">=": "<=", ">": "<", "<=": ">=", "<": ">"}  # reversed direction
_EDGE = {">=": ">", ">": ">=", "<=": "<", "<": "<="}  # same direction, other boundary


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _ran(code: str) -> str:
    """What running ``code`` shows as a choice: its output, or the error it raises."""
    res = run_code(code)
    return error_choice(res.error) if res.error else display_output(res.output)


def _truth(expr: str, **names: object) -> object:
    """Evaluate one of OUR generated conditions with the given names bound."""
    return eval(expr, {"__builtins__": {}}, dict(names))  # noqa: S307 - trusted, generated text


def _say(msg: str) -> str:
    return f'print("{msg}")'


def _if_else(cond: str, yes: str, no: str, *, first: str = "if") -> list[str]:
    return [f"{first} {cond}:", f"    {_say(yes)}", "else:", f"    {_say(no)}"]


def _ladder(rungs: list[tuple[str, str]], last: str | None) -> list[str]:
    """if / elif / ... / else lines from ``[(condition, message), ...]`` and the else message."""
    lines: list[str] = []
    for i, (cond, msg) in enumerate(rungs):
        lines += [f"{'if' if i == 0 else 'elif'} {cond}:", f"    {_say(msg)}"]
    if last is not None:
        lines += ["else:", f"    {_say(last)}"]
    return lines


def _join(lines: list[str]) -> str:
    return "\n".join(lines)


def _out(
    code: str,
    difficulty: int,
    wrong: list[str],
    explanation: str,
    rng: random.Random,
    *,
    prompt: str = "What does this code print?",
    allow_error: bool = False,
) -> Question:
    """'What does this print?' - the right answer comes from running ``code``."""
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=wrong,
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _pick(difficulty: int, prompt: str, correct: str, wrong: list[str], explanation: str, rng: random.Random,
          code: str | None = None) -> Question:
    """A plain multiple-choice question."""
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _stop(msg: str) -> str:
    """`msg` at the end of a sentence (no extra full stop if the message already ends in one)."""
    return f"`{msg}`" + ("" if msg[-1] in ".!?" else ".")


def _period(text: str) -> str:
    """The full stop to add after ``text`` (nothing if it already ends with . ! or ?, even inside backticks)."""
    stripped = text.rstrip("`")
    return "" if stripped and stripped[-1] in ".!?" else "."


def _edge_note(op: str, value: int, limit: int) -> str:
    """A short reminder when the value sits exactly on the limit."""
    if value != limit:
        return ""
    if op in (">", "<"):
        return f" (`{op}` does not include {limit} itself)"
    if op in (">=", "<="):
        return f" (`{op}` includes {limit} itself)"
    return ""


# Stories for a plain two-way decision: (variable, limit, message when True for ">=", message otherwise).
_DECISIONS = [
    ("age", 16, "You can get your driver's license.", "You are too young."),
    ("age", 16, "You can get your driver's license.", "You are too young."),
    ("age", 16, "You can get your driver's license.", "You are too young."),
    ("age", 18, "You can vote.", "You are too young."),
    ("age", 13, "You can join the club.", "You are too young."),
    ("score", 60, "You passed.", "Try again."),
    ("money", 5, "You can buy a snack.", "Not enough money."),
    ("temperature", 70, "Great day for the park!", "Stay inside."),
    ("points", 100, "Level up!", "Keep playing."),
    ("height", 48, "You can ride.", "Too short to ride."),
]


# ==========================================================================
# EASY - choice
# ==========================================================================

# Vocabulary / concept questions in the voice of the Canvas quizzes.
# (prompt, right answer, wrong answers, explanation)
_VOCAB = [
    (
        'Which keyword means "else if" in Python?',
        "elif",
        ["elseif", "else if", "elsif"],
        "`elif` is Python's \"else if\": it checks another condition only when the conditions above it were False.",
    ),
    (
        "What character must come at the end of an `if`, `elif` or `else` line?",
        "A colon (:)",
        ["A semicolon (;)", "A period (.)", "A comma (,)"],
        "Forgetting the colon after `if`/`elif`/`else` is one of the common pitfalls in the lesson.",
    ),
    (
        "What tells Python which lines belong inside an `if` block?",
        "Indentation (spaces at the start of the line)",
        ["Curly braces { }", "The word `end`", "A semicolon after each line"],
        "Indentation matters: the indented lines are the block that runs when the condition is True.",
    ),
    (
        "How many spaces does the lesson use for each level of indentation?",
        "4",
        ["1", "2", "8"],
        "Use 4 spaces per level (VS Code does this automatically).",
    ),
    (
        "What does the lesson say to stick with for indentation?",
        "Spaces",
        ["Tabs", "A mix of tabs and spaces", "Curly braces"],
        "Inconsistent indentation (mixing tabs and spaces) is a common pitfall, so stick with spaces.",
    ),
    (
        "Which operator checks whether two values are equal?",
        "==",
        ["=", "!=", "==="],
        "`=` assigns a value, `==` compares two values. Mixing them up is a common pitfall.",
    ),
    (
        "What does a single `=` do in `score = 90`?",
        "It assigns the value 90 to score",
        ["It checks if score equals 90", "It checks if score is not 90", "It prints 90"],
        "`=` assigns; `==` compares.",
    ),
    (
        "When does the `else` block run?",
        "When the conditions above it were all False",
        ["Every time the program runs", "When the `if` condition is True", "Only when the program has an error"],
        "`else:` is the fallback that runs when none of the conditions above it were True.",
    ),
    (
        "In an `if / elif / else` chain, how many branches run?",
        "Only one",
        ["All of them", "Every branch whose condition is True", "Two: the `if` and the `else`"],
        "Only one branch runs: the first condition that evaluates to True (or the `else` if none are).",
    ),
    (
        "What does a conditional check before it chooses a path?",
        "A boolean expression (True or False)",
        ["A variable name", "A loop counter", "A string method"],
        "A conditional evaluates a boolean expression. If it's True, the indented block runs.",
    ),
    (
        "What type of value does `age >= 16` produce?",
        "bool",
        ["int", "str", "float"],
        "Comparison operators always return booleans: `True` or `False`.",
    ),
    (
        "Which operator makes a combined condition True only when both sides are True?",
        "and",
        ["or", "not", "elif"],
        "With `and`, both sides must be True for the whole expression to be True.",
    ),
    (
        "Which operator makes a combined condition True when at least one side is True?",
        "or",
        ["and", "not", "elif"],
        "With `or`, at least one side has to be True.",
    ),
    (
        "Which operator turns True into False (and False into True)?",
        "not",
        ["and", "or", "elif"],
        "`not` negates a boolean: `not True` is `False`.",
    ),
    (
        "What is a nested conditional?",
        "An `if` placed inside another `if`",
        ["An `if` with no `else`", "Two `elif` lines in a row", "An `else` written before the `if`"],
        "Nest when a second check only makes sense after a first check succeeds.",
    ),
    (
        "What happens when an `if` condition is False and there is no `else`?",
        "The indented block is skipped",
        ["Python raises an error", "The indented block runs anyway", "The program stops"],
        "If the condition is False and nothing else matches, Python simply skips the block and carries on.",
    ),
    (
        'Why does the Quick Debug Trick `print("x =", x, "y =", y)` come before the `if`?',
        "To check the values the `if` is about to compare",
        ["To change the values of x and y", "To make the `if` run", "To end the program"],
        "Printing key values (a sanity check) is a quick way to see what your variables really hold.",
    ),
    (
        "According to the lesson, what is the #1 cause of beginner errors with conditionals?",
        "Mis-indentation",
        ["Using too many variables", "Forgetting to save the file", "Using the word `print`"],
        "Indentation matters: use 4 spaces per level. Mis-indentation is the #1 cause of beginner errors.",
    ),
    (
        "When does it make sense to nest one `if` inside another?",
        "When the second check depends on the first one passing",
        ["Whenever you have two variables", "Whenever you want to skip the `else`", "Never: nesting is not allowed"],
        "Design tip: nest when a second check only makes sense after a first check succeeds.",
    ),
    (
        "What should the Sign Checker print when the number is 0?",
        "Zero",
        ["Positive", "Negative", "Nothing"],
        "Zero is neither above 0 nor below 0, so it falls through to the `else` and prints `Zero`.",
    ),
    (
        "What must the Sign Checker do to the text from `input()` before comparing it with 0?",
        "Cast it to int (or float)",
        ["Nothing: text can be compared with numbers", "Add quotes around it", "Print it twice"],
        "`input()` always returns text, so cast it with `int()` (or `float()` for decimals) before using `>` or `<`.",
    ),
    (
        "What does the condition `n % 2 == 0` check?",
        "That n is even",
        ["That n is odd", "That n equals 2", "That n is divisible by 0"],
        "`n % 2` is the remainder after dividing by 2. A remainder of 0 means n is even.",
    ),
    (
        "When does the indented block under an `if` run?",
        "When the condition is True",
        ["Every time the program runs", "When the condition is False", "Only after an `else`"],
        "If the condition is True the indented block runs. Otherwise Python continues to the next option (`elif` or `else`).",
    ),
    (
        "In a grading ladder, which condition should be checked first?",
        "The highest threshold (like `score >= 90`)",
        ["The lowest threshold (like `score >= 60`)", "The `else` branch", "It doesn't matter"],
        "Logic order: put the most restrictive (highest) thresholds first in a grading ladder.",
    ),
]


@generator(TOPIC, EASY)
def gen_keyword_vocab(rng: random.Random) -> Question:
    """A vocabulary question straight from the lesson's key ideas."""
    prompt, right, wrong, why = rng.choice(_VOCAB)
    return _pick(EASY, prompt, right, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_if_else_output(rng: random.Random) -> Question:
    """The driver's-license if / else, with other stories and the boundary value."""
    var, limit, yes, no = rng.choice(_DECISIONS)
    op = rng.choice([">=", ">=", "<"])
    value = limit if rng.random() < 0.3 else max(0, limit + rng.choice([-1, 1]) * rng.randint(1, 6))
    first, second = (yes, no) if op == ">=" else (no, yes)
    code = _join([f"{var} = {value}", *_if_else(f"{var} {op} {limit}", first, second)])
    cond = _CMP[op](value, limit)
    shown = first if cond else second
    why = (
        f"With `{var} = {value}`, `{var} {op} {limit}` is {cond}{_edge_note(op, value, limit)}, so Python runs the "
        f"{'`if`' if cond else '`else`'} block and prints {_stop(shown)} Only one of the two blocks ever runs."
    )
    return _out(code, EASY, [second if cond else first, f"{first}\n{second}", NOTHING_PRINTED], why, rng)


@generator(TOPIC, EASY)
def gen_which_condition_true(rng: random.Random) -> Question:
    """Which of four comparisons is True for the given value?"""
    var = rng.choice(["age", "score", "money", "temperature", "points"])
    lo, hi = (3, 20) if var == "money" else (14, 95)
    v = rng.randint(lo, hi)
    trues: list[str] = []
    near: list[str] = []
    far: list[str] = []
    for op in _CMP:
        for d in (-12, -5, -3, -2, -1, 0, 1, 2, 3, 5, 12):
            c = v + d
            if c < 1:
                continue
            cond = f"{var} {op} {c}"
            if _CMP[op](v, c):
                if op != "!=":
                    trues.append(cond)
            elif abs(d) <= 3:
                near.append(cond)
            else:
                far.append(cond)
    correct = rng.choice(trues)
    wrong = rng.sample(near, 3)
    why = (
        f"With `{var} = {v}`, `{correct}` is the only comparison that is True. "
        f"Check each one against the value; for example `{wrong[0]}` is False."
    )
    return _pick(EASY, "Which of these conditions is True?", correct, wrong, why, rng, code=f"{var} = {v}")


@generator(TOPIC, EASY)
def gen_first_true_wins(rng: random.Random) -> Question:
    """if / elif with no else: only the first True branch runs."""
    var, weak, strong = rng.choice(
        [
            ("x", "big", "huge"),
            ("temperature", "warm", "hot"),
            ("score", "pass", "honors"),
            ("speed", "fast", "very fast"),
        ]
    )
    low = rng.randint(3, 40)
    high = low + rng.randint(2, 8)
    layout = rng.choice(["natural", "natural", "trap", "trap", "neither"])
    if layout == "natural":  # the strongest check comes first
        rungs = [(f"{var} > {high}", strong), (f"{var} > {low}", weak)]
        value = rng.choice([rng.randint(high + 1, high + 6), rng.randint(low + 1, high)])
    elif layout == "trap":  # the easy check comes first, so the second one is never reached
        rungs = [(f"{var} > {low}", weak), (f"{var} > {high}", strong)]
        value = rng.randint(low + 1, high + 6)
    else:
        rungs = [(f"{var} > {high}", strong), (f"{var} > {low}", weak)]
        value = rng.randint(max(0, low - 4), low)
    code = _join([f"{var} = {value}", *_ladder(rungs, None)])
    (c1, m1), (c2, m2) = rungs
    t1, t2 = _truth(c1, **{var: value}), _truth(c2, **{var: value})
    if t1:
        why = (
            f"`{c1}` is True, so Python prints `{m1}` and skips the `elif`"
            + (f" (even though `{c2}` is True too)." if t2 else ".")
            + " Only the first True branch runs."
        )
    elif t2:
        why = f"`{c1}` is False, so Python moves on to the `elif`. `{c2}` is True, so it prints {_stop(m2)}"
    else:
        why = "Neither condition is True and there is no `else`, so nothing is printed."
    return _out(code, EASY, [m2, f"{m1}\n{m2}", NOTHING_PRINTED, m1], why, rng)


@generator(TOPIC, EASY)
def gen_equals_vs_assign(rng: random.Random) -> Question:
    """Which `if` line really compares (== and a colon)?"""
    var, val = rng.choice([("answer", "5"), ("guess", "7"), ("count", "10"), ("name", '"Ada"'), ("color", '"red"'), ("pet", '"cat"')])
    good = f"if {var} == {val}:"
    bad = [
        f"if {var} = {val}:",
        f"if {var} == {val}",
        f"if {var} === {val}:",
        f"if {var} equals {val}:",
    ]
    for line in bad:
        try:
            compile(f"{var} = {val}\n{line}\n    pass", "<check>", "exec")
        except SyntaxError:
            continue
        raise GenerationError(f"{line!r} compiles")
    compile(f"{var} = {val}\n{good}\n    pass", "<check>", "exec")
    wrong = [bad[0], *rng.sample(bad[1:], 2)]
    why = "`==` compares two values (a single `=` assigns), and the `if` line must end with a colon."
    return _pick(EASY, f"Which line correctly checks whether `{var}` equals {val}?", good, wrong, why, rng)


_BOOL_SCENES = [
    # (first flag, second flag, message when the condition is True, message when False)
    ("is_student", "has_permission", "You can enter.", "You cannot enter."),
    ("has_ticket", "is_early", "Come on in!", "Sorry, not today."),
    ("is_weekend", "has_homework", "Time to relax.", "Back to work."),
    ("is_raining", "has_umbrella", "Go outside.", "Stay inside."),
]


@generator(TOPIC, EASY)
def gen_and_or_not_branch(rng: random.Random) -> Question:
    """`and`, `or` and `not` inside an if / else with True/False variables."""
    a, b, yes, no = rng.choice(_BOOL_SCENES)
    kind = rng.choice(["and", "and", "or", "or", "not"])
    va, vb = rng.choice([True, False]), rng.choice([True, False])
    if kind == "not":
        cond, setup = f"not {a}", [f"{a} = {va}"]
        truth = not va
    else:
        cond, setup = f"{a} {kind} {b}", [f"{a} = {va}", f"{b} = {vb}"]
        truth = (va and vb) if kind == "and" else (va or vb)
    code = _join([*setup, *_if_else(cond, yes, no)])
    shown = yes if truth else no
    rule = {
        "and": "`and` is True only when both sides are True",
        "or": "`or` is True when at least one side is True",
        "not": "`not` flips True to False and False to True",
    }[kind]
    why = f"{rule}. Here `{cond}` is {truth}, so Python runs the {'`if`' if truth else '`else`'} block and prints {_stop(shown)}"
    return _out(code, EASY, [no if truth else yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)


@generator(TOPIC, EASY)
def gen_even_odd_output(rng: random.Random) -> Question:
    """if / else with `%`: even or odd, or a multiple of k."""
    k = rng.choice([2, 2, 2, 3, 5])
    var = rng.choice(["number", "n", "count"])
    value = rng.choice([0, rng.randint(1, 40), rng.randint(1, 40), rng.randint(1, 40)])
    if k == 2:
        yes, no = "Even", "Odd"
    else:
        yes, no = f"Multiple of {k}", f"Not a multiple of {k}"
    code = _join([f"{var} = {value}", *_if_else(f"{var} % {k} == 0", yes, no)])
    cond = value % k == 0
    meaning = "An even number leaves remainder 0 when divided by 2." if k == 2 else f"A multiple of {k} leaves remainder 0 when divided by {k}."
    why = f"`{value} % {k}` is {value % k}, so `{var} % {k} == 0` is {cond}. {meaning}"
    return _out(code, EASY, [no if cond else yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)


# ---- "Which condition says ...?" -------------------------------------------------

_NUM_ATOMS = [
    # (variable, operator, (low, high) for the number, English)
    ("age", ">=", (13, 18), "age is at least {v}"),
    ("age", ">", (12, 17), "age is more than {v}"),
    ("temperature", ">", (60, 80), "the temperature is above {v}"),
    ("temperature", "<", (40, 60), "the temperature is below {v}"),
    ("score", ">=", (60, 90), "the score is {v} or more"),
    ("score", "<", (50, 70), "the score is less than {v}"),
    ("money", ">=", (5, 15), "money is at least {v}"),
    ("money", "<=", (3, 9), "money is {v} or less"),
]
_FLAG_ATOMS = [
    ("is_raining", "it is raining", "it is not raining"),
    ("has_permission", "the player has permission", "the player does not have permission"),
    ("is_student", "the person is a student", "the person is not a student"),
    ("has_ticket", "the guest has a ticket", "the guest has no ticket"),
]


def _signatures(cond: str, var: str, flag: str, v: int) -> tuple:
    """The truth table of ``cond`` over values around the limit and both flag values."""
    rows = []
    for x in (v - 2, v - 1, v, v + 1, v + 2):
        for f in (True, False):
            try:
                rows.append(bool(_truth(cond, **{var: x, flag: f})))
            except Exception:  # noqa: BLE001
                rows.append(None)
    return tuple(rows)


@generator(TOPIC, EASY)
def gen_english_to_condition(rng: random.Random) -> Question:
    """Translate an English sentence into a condition with and / or / not."""
    var, op, (lo, hi), english = rng.choice(_NUM_ATOMS)
    flag, pos, neg = rng.choice(_FLAG_ATOMS)
    v = rng.randint(lo, hi)
    conn = rng.choice(["and", "and", "or"])
    negated = rng.random() < 0.5
    phrase = english.format(v=v)
    sentence = f"{phrase}{', ' if conn == 'or' else ' '}{conn} {neg if negated else pos}"
    num = f"{var} {op} {v}"
    fl = f"not {flag}" if negated else flag
    correct = f"{num} {conn} {fl}"
    other = "or" if conn == "and" else "and"
    flipped_flag = flag if negated else f"not {flag}"
    candidates = [
        f"{num} {other} {fl}",  # and <-> or
        f"{num} {conn} {flipped_flag}",  # forgot (or added) the not
        f"{var} {_FLIP[op]} {v} {conn} {fl}",  # comparison the wrong way round
        f"{var} {_EDGE[op]} {v} {conn} {fl}",  # off by one at the limit
        f"{num} {other} {flipped_flag}",
    ]
    want = _signatures(correct, var, flag, v)
    wrong = [c for c in candidates if _signatures(c, var, flag, v) != want]
    # The two classic mistakes (wrong connective, missing `not`) first, then a random extra one.
    classic, rest = wrong[:2], wrong[2:]
    rng.shuffle(rest)
    wrong = classic + rest
    why = (
        f'`{num}` says "{phrase}", and `{conn}` joins it with '
        + (f"`not {flag}`" if negated else f"`{flag}`")
        + ". Check the connective and whether the flag needs a `not`."
    )
    return _pick(EASY, f'Which condition means "{sentence}"?', correct, wrong, why, rng)


_BAD_LINES = [
    # (the broken line, what is wrong)
    ("if {var} >= {n}", "It is missing the colon (:) at the end"),
    ("if {var} = {n}:", "A single = assigns; use == to compare"),
    ("else if {var} >= {n}:", "Python writes \"else if\" as elif"),
    ("elif {var} >= {n}", "It is missing the colon (:) at the end"),
]
_NOT_WRONG = [
    "The condition has to be inside parentheses",
    "`if` has to be followed by the word `then`",
    "The number should be in quotes",
    "`>=` is not a valid Python operator",
    "The variable name must be written in capital letters",
]


@generator(TOPIC, EASY)
def gen_what_is_wrong_line(rng: random.Random) -> Question:
    """Spot the classic one-line mistake: missing colon, = vs ==, else if."""
    var, n = rng.choice([("age", 16), ("score", 90), ("money", 5), ("temperature", 70), ("points", 100)])
    template, answer = rng.choice(_BAD_LINES)
    line = template.format(var=var, n=n)
    wrong = rng.sample(_NOT_WRONG, 3)
    explanations = {
        "It is missing the colon (:) at the end": "Every `if`, `elif` and `else` line must end with a colon `:`.",
        "A single = assigns; use == to compare": "`=` assigns a value; `==` compares. A condition needs `==`.",
        "Python writes \"else if\" as elif": "Python's \"else if\" is the single keyword `elif`.",
    }
    return _pick(EASY, f"What is wrong with the line `{line}`?", answer, wrong, explanations[answer], rng)


@generator(TOPIC, EASY)
def gen_even_condition(rng: random.Random) -> Question:
    """Which condition is True for even numbers (or multiples of k)?"""
    var = rng.choice(["number", "n", "num"])
    what, correct, bad = rng.choice(
        [
            ("even", f"{var} % 2 == 0", [f"{var} % 2 == 1", f"{var} // 2 == 0", f"{var} / 2 == 0", f"{var} % 2 = 0"]),
            ("odd", f"{var} % 2 == 1", [f"{var} % 2 == 0", f"{var} // 2 == 1", f"{var} / 2 == 1", f"{var} % 2 = 1"]),
            (
                "a multiple of 3",
                f"{var} % 3 == 0",
                [f"{var} // 3 == 0", f"{var} / 3 == 0", f"{var} % 3 == 3", f"{var} % 3 = 0"],
            ),
            (
                "a multiple of 5",
                f"{var} % 5 == 0",
                [f"{var} // 5 == 0", f"{var} / 5 == 0", f"{var} % 5 == 5", f"{var} % 5 = 0"],
            ),
        ]
    )
    want = [bool(_truth(correct, **{var: n})) for n in range(0, 31)]
    wrong = []
    for cond in bad:
        try:
            got = [bool(_truth(cond, **{var: n})) for n in range(0, 31)]
        except SyntaxError:
            wrong.append(cond)
            continue
        if got != want:
            wrong.append(cond)
    rng.shuffle(wrong)
    why = f"`%` gives the remainder, so `{correct}` is True when `{var}` is {what}. (`/` and `//` divide; they don't give a remainder.)"
    return _pick(EASY, f"Which condition is True when `{var}` is {what}?", correct, wrong, why, rng)


_EQ_SCENES = [
    # (variable, value that triggers the "same" message, other values, same msg, different msg)
    ("answer", 5, [3, 4, 6, 8, 9], "Correct!", "Try again."),
    ("guess", 7, [1, 2, 5, 8, 10], "You win!", "Nope."),
    ("count", 10, [0, 5, 9, 11, 20], "Done counting.", "Keep counting."),
    ("lives", 0, [1, 2, 3, 5], "Game over", "Keep playing"),
    ("age", 16, [12, 14, 15, 17, 21], "Sweet sixteen!", "Not sixteen."),
    ("player_number", 1, [2, 3, 4, 5], "You go first.", "Wait your turn."),
]
_TEXT_SCENES = [
    ("name", "Ada", ["Sam", "Ben", "Ivy", "ada"], "Welcome back!", "Who are you?"),
    ("color", "red", ["blue", "green", "Red", "pink"], "Stop!", "Go!"),
    ("pet", "cat", ["dog", "fish", "Cat", "bird"], "Meow!", "Not a cat."),
    ("word", "Python", ["python", "code", "Java", "loop"], "Correct word!", "Wrong word."),
    ("password", "swordfish", ["Swordfish", "12345", "letmein"], "Access granted.", "Access denied."),
]


@generator(TOPIC, EASY)
def gen_equal_branch(rng: random.Random) -> Question:
    """`==` / `!=` in an if / else (numbers or text, including a different-case trap)."""
    use_text = rng.random() < 0.4
    if use_text:
        var, target, others, same, diff = rng.choice(_TEXT_SCENES)
        shown = lambda v: f'"{v}"'  # noqa: E731
    else:
        var, target, others, same, diff = rng.choice(_EQ_SCENES)
        shown = str  # noqa: E731
    value = rng.choice([target, target, *others])
    op = rng.choice(["==", "==", "!="])
    first, second = (same, diff) if op == "==" else (diff, same)
    code = _join([f"{var} = {shown(value)}", *_if_else(f"{var} {op} {shown(target)}", first, second)])
    cond = (value == target) if op == "==" else (value != target)
    printed = first if cond else second
    used = f"{var} {op} {shown(target)}"
    if value == target:
        why = f"`{var}` is exactly {shown(target)}, so `{used}` is {cond}."
    elif use_text and str(value).lower() == str(target).lower():
        why = f'Capital letters count: "{value}" and "{target}" are different text, so `{used}` is {cond}.'
    else:
        why = f"`{var}` is {shown(value)}, not {shown(target)}, so `{used}` is {cond}."
    why += f" Python runs the {'`if`' if cond else '`else`'} block and prints {_stop(printed)}"
    return _out(code, EASY, [second if cond else first, f"{first}\n{second}", NOTHING_PRINTED], why, rng)


# ==========================================================================
# MEDIUM - choice
# ==========================================================================


def _ladder_why(var: str, value: int, rungs: list[tuple[str, str]], last: str | None) -> str:
    """'Python goes top to bottom ...' explanation for an if / elif / else ladder."""
    steps = []
    for cond, msg in rungs:
        if _truth(cond, **{var: value}):
            steps.append(f"`{cond}` is True")
            return (
                f"With `{var} = {value}` Python goes top to bottom: "
                + ", ".join(steps)
                + f", so it prints `{msg}` and skips every branch below it."
            )
        steps.append(f"`{cond}` is False")
    tail = f", so the `else` runs and prints {_stop(last)}" if last is not None else ", so nothing is printed."
    return f"With `{var} = {value}` Python goes top to bottom: " + ", ".join(steps) + tail


@generator(TOPIC, MEDIUM)
def gen_grade_ladder_trace(rng: random.Random) -> Question:
    """A short grade ladder (A / B / else C): trace one score, often right on a threshold."""
    t1, t2 = rng.choice([(90, 80), (90, 75), (80, 70), (85, 70), (90, 70)])
    zone = rng.choice(["A", "B", "C", "edge", "edge"])
    if zone == "A":
        score = rng.randint(t1, 100)
    elif zone == "B":
        score = rng.randint(t2, t1 - 1)
    elif zone == "C":
        score = rng.randint(40, t2 - 1)
    else:
        score = rng.choice([t1, t1 - 1, t2, t2 - 1])
    rungs = [(f"score >= {t1}", "Grade: A"), (f"score >= {t2}", "Grade: B")]
    code = _join([f"score = {score}", *_ladder(rungs, "Grade: C")])
    why = _ladder_why("score", score, rungs, "Grade: C") + " Only one branch runs."
    wrong = ["Grade: A", "Grade: B", "Grade: C", "Grade: A\nGrade: B", "Grade: B\nGrade: C"]
    return _out(code, MEDIUM, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_sign_checker_output(rng: random.Random) -> Question:
    """The Sign Checker logic on a given number, or the `>= 0` version where Zero never prints."""
    var = rng.choice(["number", "n", "num", "value"])
    kind = rng.choice(["standard", "standard", "zero_trap"])
    if kind == "standard":
        value = rng.choice([0, rng.randint(1, 9), rng.randint(-9, -1), rng.randint(1, 50), rng.randint(-50, -1)])
        rungs = [(f"{var} > 0", "Positive"), (f"{var} < 0", "Negative")]
        last = "Zero"
        why = _ladder_why(var, value, rungs, last)
    else:
        value = rng.choice([0, 0, 0, rng.randint(1, 9), rng.randint(-9, -1)])
        rungs = [(f"{var} >= 0", "Positive"), (f"{var} < 0", "Negative")]
        last = "Zero"
        why = _ladder_why(var, value, rungs, last)
        if value == 0:
            why += " The `Zero` branch can never run, because `0 >= 0` is already True."
    code = _join([f"{var} = {value}", *_ladder(rungs, last)])
    return _out(code, MEDIUM, ["Positive", "Negative", "Zero", NOTHING_PRINTED], why, rng)


@generator(TOPIC, MEDIUM)
def gen_debug_trick_output(rng: random.Random) -> Question:
    """The Quick Debug Trick snippet: the sanity-check line plus the if / else."""
    a, b = rng.choice([("x", "y"), ("x", "y"), ("a", "b"), ("p", "q")])
    xv = rng.randint(1, 9)
    yv = xv if rng.random() < 0.2 else rng.randint(1, 9)
    code = _join(
        [
            f"{a} = {xv}",
            f"{b} = {yv}",
            f'print("{a} =", {a}, "{b} =", {b})  # sanity check',
            f"if {a} > {b}:",
            f'    print("{a} is larger")',
            "else:",
            f'    print("{b} is larger")',
        ]
    )
    first = f"{a} = {xv} {b} = {yv}"
    msg = f"{a} is larger" if xv > yv else f"{b} is larger"
    other = f"{b} is larger" if xv > yv else f"{a} is larger"
    why = "`print` with commas puts a space between the pieces, so the sanity check shows `" + first + "`. "
    if xv == yv:
        why += f"`{a} > {b}` is False when they are equal, so the `else` runs and prints {_stop(msg)}"
    else:
        why += f"`{xv} > {yv}` is {xv > yv}, so it prints {_stop(msg)}"
    wrong = [
        f"{first}\n{other}",
        f"{a} = {xv}, {b} = {yv}\n{msg}",
        f"{xv} {yv}\n{msg}",
        msg,
    ]
    return _out(code, MEDIUM, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_nested_snack_output(rng: random.Random) -> Question:
    """The nested money / snack / drink conditional."""
    t1, t2, item1, item2 = rng.choice(
        [(5, 8, "snack", "drink"), (5, 8, "snack", "drink"), (4, 6, "snack", "drink"), (10, 15, "ticket", "popcorn"), (3, 7, "pencil", "notebook")]
    )
    zone = rng.choice(["none", "first", "both", "edge"])
    if zone == "none":
        money = rng.randint(0, t1 - 1)
    elif zone == "first":
        money = rng.randint(t1, t2 - 1)
    elif zone == "both":
        money = rng.randint(t2, t2 + 6)
    else:
        money = rng.choice([t1, t1 - 1, t2, t2 - 1])
    m1, m2, m0 = f"You can buy a {item1}.", f"You can also buy a {item2}.", "Not enough money."
    code = _join(
        [
            f"money = {money}",
            "",
            f"if money >= {t1}:",
            f"    {_say(m1)}",
            f"    if money >= {t2}:",
            f"        {_say(m2)}",
            "else:",
            f"    {_say(m0)}",
        ]
    )
    if money < t1:
        why = f"`money >= {t1}` is False, so Python skips the whole block (including the inner `if`) and runs the `else`."
    elif money < t2:
        why = f"`money >= {t1}` is True, so the first message prints. The inner check `money >= {t2}` is False, so nothing else is printed."
    else:
        why = f"`money >= {t1}` is True, and then the inner `money >= {t2}` is True too, so both messages print."
    return _out(code, MEDIUM, [m1, f"{m1}\n{m2}", m0, m2], why, rng)


@generator(TOPIC, MEDIUM)
def gen_indent_scope_output(rng: random.Random) -> Question:
    """The same lines with one print indented differently: indentation decides when it runs."""
    limit = 16
    yes, no = "You can get your driver's license.", "You are too young."
    extra = rng.choice(["Have a nice day!", "Drive safe!", "Thanks for asking."])
    age = rng.choice([limit - rng.randint(1, 4), limit + rng.randint(0, 4)])

    def build(where: str, a: int) -> str:
        body_if = [f"    {_say(yes)}"] + ([f"    {_say(extra)}"] if where == "if" else [])
        body_else = [f"    {_say(no)}"] + ([f"    {_say(extra)}"] if where == "else" else [])
        tail = [_say(extra)] if where == "outside" else []
        return _join([f"age = {a}", f"if age >= {limit}:", *body_if, "else:", *body_else, *tail])

    where = rng.choice(["outside", "if", "else"])
    code = build(where, age)
    place = {
        "outside": f"`{_say(extra)}` is not indented, so it is outside the `if` / `else` and always runs.",
        "if": f"`{_say(extra)}` is indented under the `if`, so it only runs when the condition is True.",
        "else": f"`{_say(extra)}` is indented under the `else`, so it only runs when the condition is False.",
    }[where]
    wrong = []
    for other_where in ("outside", "if", "else"):
        for other_age in (age, limit - 2 if age >= limit else limit + 1):
            if (other_where, other_age) != (where, age):
                wrong.append(_ran(build(other_where, other_age)))
    why = f"{place} Indentation decides which lines belong to a block."
    return _out(code, MEDIUM, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_reordered_ladder_trace(rng: random.Random) -> Question:
    """Thresholds in the wrong order: the easy check catches everything first."""
    hi_letter, lo_letter, last_letter, t_hi, t_lo = rng.choice(
        [("A", "B", "C", 90, 80), ("B", "C", "D", 80, 70), ("C", "D", "F", 70, 60), ("A", "B", "F", 90, 70)]
    )
    zone = rng.choice(["high", "high", "high", "middle", "low"])
    score = {
        "high": rng.randint(t_hi, 100),
        "middle": rng.randint(t_lo, t_hi - 1),
        "low": rng.randint(40, t_lo - 1),
    }[zone]
    g_hi, g_lo, g_last = (f"Grade: {x}" for x in (hi_letter, lo_letter, last_letter))
    rungs = [(f"score >= {t_lo}", g_lo), (f"score >= {t_hi}", g_hi)]
    code = _join([f"score = {score}", *_ladder(rungs, g_last)])
    if zone == "high":
        why = (
            f"`score >= {t_lo}` is checked first and it is True, so Python prints `{g_lo}` and never reaches `score >= {t_hi}`. "
            "Put the highest threshold first in a grading ladder."
        )
    elif zone == "middle":
        why = f"`score >= {t_lo}` is True, so it prints {_stop(g_lo)} (The `score >= {t_hi}` check below it can never run, which is the bug.)"
    else:
        why = f"`score >= {t_lo}` is False and `score >= {t_hi}` is False, so the `else` runs and prints {_stop(g_last)}"
    return _out(code, MEDIUM, [g_hi, g_lo, g_last, f"{g_lo}\n{g_hi}"], why, rng)


@generator(TOPIC, MEDIUM)
def gen_separate_ifs(rng: random.Random) -> Question:
    """Two plain `if`s both run; an `elif` stops after the first True branch."""
    t1, t2 = rng.choice([(80, 70), (90, 80), (70, 60)])
    score = rng.randint(t1, min(t1 + 9, 100))
    letters = {90: "A", 80: "B", 70: "C", 60: "D"}
    g1, g2 = f"Grade: {letters[t1]}", f"Grade: {letters[t2]}"
    variant = rng.choice(["output", "output", "fix", "why"])
    code = _join(
        [
            f"score = {score}",
            f"if score >= {t1}:",
            f"    {_say(g1)}",
            f"if score >= {t2}:",
            f"    {_say(g2)}",
        ]
    )
    if variant == "output":
        why = (
            f"These are two separate `if` statements, so Python checks both. Both conditions are True when `score` is {score}, "
            f"so both lines print. Only an `elif` skips the rest after the first True branch."
        )
        return _out(code, MEDIUM, [g1, g2, f"{g2}\n{g1}", NOTHING_PRINTED], why, rng)
    if variant == "fix":
        return _pick(
            MEDIUM,
            f"This prints two grades. What change makes it print only `{g1}`?",
            "Change the second `if` to `elif`",
            ["Change `>=` to `>` in the first line", "Add a colon after each print", "Indent the second `print` less"],
            "An `elif` runs only if the conditions above it were False, so just one grade prints.",
            rng,
            code=code,
        )
    return _pick(
        MEDIUM,
        f"Why does this print two grades when `score` is {score}?",
        "The second check is a separate `if`, not an `elif`",
        ["`print` always runs twice", "The `>=` operator matches two numbers", "Python runs the `else` as well"],
        "Each plain `if` is checked on its own. Use `elif` so only the first True branch runs.",
        rng,
        code=code,
    )


@generator(TOPIC, MEDIUM)
def gen_park_message(rng: random.Random) -> Question:
    """Section 3 of the lesson: temperature and is_raining combined with and / not."""
    temperature = rng.choice([72, 72, rng.randint(50, 69), rng.randint(71, 95), 70, 71])
    is_raining = rng.choice([True, False])
    code = _join(
        [
            f"temperature = {temperature}",
            f"is_raining = {is_raining}",
            "",
            "if temperature > 70 and not is_raining:",
            '    print("Great day to go to the park!")',
            "elif temperature > 70 and is_raining:",
            '    print("Stay inside—it\'s raining.")',
            "else:",
            '    print("Might be too cold.")',
        ]
    )
    if temperature > 70 and not is_raining:
        why = f"`{temperature} > 70` is True and `not is_raining` is True, so both sides of the `and` are True: park."
    elif temperature > 70:
        why = f"`{temperature} > 70` is True, but `not is_raining` is False, so the first condition fails. The `elif` (warm and raining) is True."
    elif temperature == 70:
        why = "`70 > 70` is False (`>` does not include 70), so neither `and` condition can be True and the `else` runs."
    else:
        why = f"`{temperature} > 70` is False, so neither `and` condition can be True and the `else` runs."
    wrong = [
        "Great day to go to the park!",
        "Stay inside—it's raining.",
        "Might be too cold.",
        "Great day to go to the park!\nStay inside—it's raining.",
    ]
    return _out(code, MEDIUM, wrong, why, rng)


# Programs for "which version runs": (variable line, lines of the working program)
_PROGRAMS = [
    (
        "age = 16",
        ["if age >= 16:", '    print("Can drive")', "else:", '    print("Too young")'],
    ),
    (
        "money = 10",
        ["if money >= 5:", '    print("You can buy a snack.")', "else:", '    print("Not enough money.")'],
    ),
    (
        "score = 85",
        [
            "if score >= 90:",
            '    print("Grade: A")',
            "elif score >= 80:",
            '    print("Grade: B")',
            "else:",
            '    print("Grade: F")',
        ],
    ),
    (
        "temperature = 72",
        [
            "if temperature > 70:",
            '    print("Warm")',
            "elif temperature > 50:",
            '    print("Mild")',
            "else:",
            '    print("Cold")',
        ],
    ),
]


def _mutate(lines: list[str], how: str) -> list[str] | None:
    """A broken copy of a working program, or None if this bug doesn't fit."""
    out = list(lines)
    if how == "no_colon":
        out[0] = out[0].rstrip(":")
    elif how == "equals":
        out[0] = out[0].replace(" >= ", " = ").replace(" > ", " = ")
    elif how == "no_indent":
        out[1] = out[1].lstrip()
    elif how == "else_no_colon":
        i = out.index("else:")
        out[i] = "else"
    elif how == "else_if":
        if "elif" not in out[2]:
            return None
        out[2] = out[2].replace("elif", "else if", 1)
    elif how == "elif_no_colon":
        if "elif" not in out[2]:
            return None
        out[2] = out[2].rstrip(":")
    elif how == "else_indented":
        i = out.index("else:")
        out[i] = "    else:"
    return out


@generator(TOPIC, MEDIUM)
def gen_which_version_runs(rng: random.Random) -> Question:
    """Four versions of the same code: exactly one has no syntax error."""
    setup, good = rng.choice(_PROGRAMS)
    hows = ["no_colon", "equals", "no_indent", "else_no_colon", "else_if", "elif_no_colon", "else_indented"]
    rng.shuffle(hows)
    wrong, used = [], []
    for how in hows:
        bad = _mutate(good, how)
        if bad is None or bad == good:
            continue
        try:
            compile(_join([setup, *bad]), "<check>", "exec")
        except SyntaxError:
            wrong.append(_join(bad))
            used.append(how)
        else:
            raise GenerationError(f"mutation {how} still compiles")
        if len(wrong) == 3:
            break
    compile(_join([setup, *good]), "<check>", "exec")
    why = (
        "Check each version for the pitfalls from the lesson: a colon at the end of `if`/`elif`/`else`, "
        "`==` or a comparison (not `=`) in the condition, `elif` (not `else if`), and the lines inside a block indented."
    )
    return _pick(MEDIUM, "Which version of this code runs without an error?", _join(good), wrong, why, rng, code=setup)


_RANGES = [
    ("age", 13, 19),
    ("number", 1, 100),
    ("score", 60, 69),
    ("temperature", 60, 80),
    ("money", 5, 10),
]


@generator(TOPIC, MEDIUM)
def gen_between_condition(rng: random.Random) -> Question:
    """Which condition checks 'between lo and hi (inclusive)'? (chained comparison / and)"""
    var, lo, hi = rng.choice(_RANGES)
    chained = f"{lo} <= {var} <= {hi}"
    spelled = f"{var} >= {lo} and {var} <= {hi}"
    correct = rng.choice([chained, chained, spelled])
    pool = [
        f"{var} >= {lo} or {var} <= {hi}",
        f"{lo} < {var} < {hi}",
        f"{var} >= {lo} <= {hi}",
        f"{var} = {lo} or {hi}",
        f"{var} > {lo} and {var} < {hi}",
        f"{var} in {lo}..{hi}",
    ]
    values = range(lo - 3, hi + 4)

    def table(expr: str):
        try:
            return tuple(bool(_truth(expr, **{var: x})) for x in values)
        except SyntaxError:
            return None

    want = table(correct)
    wrong = [c for c in pool if table(c) != want]
    # keep the classic wrong turns near the front, but vary the rest
    head, tail = wrong[:2], wrong[2:]
    rng.shuffle(tail)
    why = (
        f"Between {lo} and {hi} inclusive means {var} can be {lo}, {hi} or anything in between. "
        f"`{chained}` (a chained comparison) and `{spelled}` both say that; `or` would be True for every number."
    )
    return _pick(MEDIUM, f"Which condition checks if {var} is between {lo} and {hi} (inclusive)?", correct, head + tail, why, rng)


@generator(TOPIC, MEDIUM)
def gen_text_vs_number(rng: random.Random) -> Question:
    """input() gives text: comparing text with a number raises a TypeError or is never equal."""
    variant = rng.choice(["ordering", "equality"])
    if variant == "ordering":
        var, limit, text, yes, no = rng.choice(
            [
                ("age", 16, rng.choice(["15", "16", "17", "21"]), "You can get your driver's license.", "You are too young."),
                ("score", 60, rng.choice(["45", "60", "88"]), "You passed.", "Try again."),
                ("money", 5, rng.choice(["3", "5", "10"]), "You can buy a snack.", "Not enough money."),
            ]
        )
        code = _join([f'{var} = "{text}"', *_if_else(f"{var} >= {limit}", yes, no)])
        why = (
            "A value typed with `input()` is text. Comparing text with a number using `>=` raises a TypeError; "
            f"cast it first, e.g. `{var} = int({var})`."
        )
        wrong = [yes, no, "Error: ValueError", "Error: NameError"]
        return _out(
            code, MEDIUM, wrong, why, rng, prompt=f"`{var}` holds text, like the result of `input()`. What is printed, or which error is raised?", allow_error=True
        )
    var, number = rng.choice([("answer", 5), ("guess", 7), ("count", 10), ("score", 100)])
    code = _join([f'{var} = "{number}"', *_if_else(f"{var} == {number}", "Correct!", "Try again.")])
    why = f'The text "{number}" and the number {number} are different types, so `==` says they are not equal. Cast with `int()` before comparing.'
    return _out(code, MEDIUM, ["Correct!", "Try again.", "Error: TypeError", "Error: ValueError"], why, rng)


@generator(TOPIC, MEDIUM)
def gen_snack_money_value(rng: random.Random) -> Question:
    """Which value of money prints exactly one line (or both)?"""
    t1, t2 = rng.choice([(5, 8), (5, 8), (4, 6), (6, 10), (3, 7)])
    m1, m2, m0 = "You can buy a snack.", "You can also buy a drink.", "Not enough money."
    template = [
        "if money >= {t1}:",
        f"    {_say(m1)}",
        "    if money >= {t2}:",
        f"        {_say(m2)}",
        "else:",
        f"    {_say(m0)}",
    ]
    code = _join(line.format(t1=t1, t2=t2) for line in template)
    target = rng.choice([m1, f"{m1}\n{m2}", m0])

    def printed(money: int) -> str:
        return _ran(f"money = {money}\n{code}")

    by_output: dict[str, list[int]] = {m1: [], f"{m1}\n{m2}": [], m0: []}
    for money in range(0, t2 + 8):
        by_output[printed(money)].append(money)
    correct = rng.choice(by_output[target])
    others = [m for out, vals in by_output.items() if out != target for m in vals]
    near = [m for m in others if abs(m - correct) <= 4 or m in (t1, t1 - 1, t2, t2 - 1)]
    rng.shuffle(near)
    wrong = [str(m) for m in near]
    what = {m1: "only `You can buy a snack.`", f"{m1}\n{m2}": "both messages", m0: "`Not enough money.`"}[target]
    why = f"The outer check is `money >= {t1}` and the inner check is `money >= {t2}`. With `money = {correct}` the code prints {what}{_period(what)}"
    return _pick(MEDIUM, f"Which value of `money` makes this code print {what}?", str(correct), wrong, why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_complete_the_ladder(rng: random.Random) -> Question:
    """Which condition completes the elif so the middle grade covers the right scores?"""
    t1, t2 = rng.choice([(90, 80), (90, 70), (80, 60), (85, 70)])
    code = _join(
        [
            f"if score >= {t1}:",
            '    print("Grade: A")',
            "elif ____:",
            '    print("Grade: B")',
            "else:",
            '    print("Grade: C")',
        ]
    )
    correct = f"score >= {t2}"
    pool = [f"score > {t2}", f"score <= {t2}", f"score == {t2}", f"score < {t1}", f"score >= {t1}"]
    probes = [100, t1, t1 - 1, t2 + 1, t2, t2 - 1, 0]

    def behaves(cond: str) -> tuple:
        filled = code.replace("____", cond)
        return tuple(_ran(f"score = {s}\n{filled}") for s in probes)

    want = behaves(correct)
    wrong = [c for c in pool if behaves(c) != want]
    rest = wrong[1:]
    rng.shuffle(rest)
    wrong = wrong[:1] + rest  # the off-by-one `>` stays in the mix
    why = f"`score >= {t1}` already caught the A grades, so the `elif` only needs the lower limit: `{correct}`, which includes {t2} itself."
    return _pick(
        MEDIUM,
        f"Which condition completes the `elif` so that scores {t2} to {t1 - 1} get `Grade: B` and everything lower gets `Grade: C`?",
        correct,
        wrong,
        why,
        rng,
        code=code,
    )


_RANK_SETS = [
    (("Bronze", "Silver", "Gold", "Diamond"), (1000, 2000, 3000)),
    (("Bronze", "Silver", "Gold", "Diamond"), (1000, 2000, 3000)),
    (("Bronze", "Silver", "Gold", "Diamond"), (500, 1000, 1500)),
    (("Rookie", "Pro", "Master", "Legend"), (100, 200, 300)),
]


@generator(TOPIC, MEDIUM)
def gen_diamond_placement(rng: random.Random) -> Question:
    """The Programming Assessment bonus: where must the new Diamond check go?"""
    (b, s, g, d), (t_s, t_g, t_d) = rng.choice(_RANK_SETS)
    code = _join(
        [
            f"if score >= {t_g}:",
            f"    {_say(g)}",
            f"elif score >= {t_s}:",
            f"    {_say(s)}",
            "else:",
            f"    {_say(b)}",
        ]
    )
    return _pick(
        MEDIUM,
        f"You add a `{d}` rank for `score >= {t_d}`. Where must the new check go so it can actually be reached?",
        f"At the top, above `score >= {t_g}`",
        [
            f"Between the `score >= {t_g}` and `score >= {t_s}` checks",
            f"Below the `score >= {t_s}` check",
            "Anywhere: the order doesn't matter",
        ],
        f"Any score of {t_d} or more is also {t_g} or more, so the {t_g} check would catch it first. "
        "Put the highest threshold first so it can be reached.",
        rng,
        code=code,
    )


_ASSIGN_SCENES = [
    # (variable, label printed, game flavour of the thresholds)
    ("coins", "Coins:"),
    ("points", "Points:"),
    ("lives", "Lives:"),
    ("bonus", "Bonus:"),
    ("total", "Total:"),
]


@generator(TOPIC, MEDIUM)
def gen_assign_in_branch(rng: random.Random) -> Question:
    """A variable is changed inside the branch that runs; print it afterwards."""
    var, label = rng.choice(_ASSIGN_SCENES)
    t1 = rng.choice([10, 20, 50, 100])
    t2 = t1 // 2
    a, b = rng.choice([(5, 2), (10, 5), (4, 2), (3, 2), (6, 3)])
    kind = rng.choice(["add", "add", "mix"])
    start = rng.choice([t1 + rng.randint(0, 9), t1, t2 + rng.randint(0, 3), t2, t2 - 1, rng.randint(0, t2 - 1)])
    use_plus_equals = rng.random() < 0.4
    inc = (lambda k: f"{var} += {k}") if use_plus_equals else (lambda k: f"{var} = {var} + {k}")
    first = inc(a)
    second = inc(b)
    third = f"{var} = 0" if kind == "mix" else inc(1)
    code = _join(
        [
            f"{var} = {start}",
            f"if {var} >= {t1}:",
            f"    {first}",
            f"elif {var} >= {t2}:",
            f"    {second}",
            "else:",
            f"    {third}",
            f'print("{label}", {var})',
        ]
    )
    results = {
        "first": start + a,
        "second": start + b,
        "third": 0 if kind == "mix" else start + 1,
        "none": start,
    }
    branch = "first" if start >= t1 else "second" if start >= t2 else "third"
    why = (
        f"With `{var} = {start}`, `{var} >= {t1}` is {start >= t1}"
        + (f" and `{var} >= {t2}` is {start >= t2}" if start < t1 else "")
        + f", so the {'`if`' if branch == 'first' else '`elif`' if branch == 'second' else '`else`'} branch runs and `{var}` becomes {results[branch]}. "
        "Only that one branch changes the variable, then the `print` after the block shows it."
    )
    wrong = [f"{label} {v}" for k, v in results.items() if k != branch]
    wrong += [f"{label} {start + a + b}", f"{label} {results[branch] + 1}", f"{label} {max(0, results[branch] - 1)}"]
    return _out(code, MEDIUM, wrong, why, rng)


_CASE_SCENES = [
    ("answer", ["yes", "no", "maybe"], "Great!", "Oh well."),
    ("color", ["red", "blue", "green"], "Stop!", "Keep going."),
    ("pet", ["cat", "dog", "fish"], "Meow!", "Not a cat."),
    ("name", ["Ada", "Sam", "Ben"], "Welcome back!", "Who are you?"),
    ("word", ["Python", "loop", "code"], "That's the word!", "Wrong word."),
]


@generator(TOPIC, MEDIUM)
def gen_string_equals_case(rng: random.Random) -> Question:
    """Text comparisons: capital letters, extra spaces and missing quotes."""
    var, words, yes, no = rng.choice(_CASE_SCENES)
    target = rng.choice(words)
    trap = rng.choice(["case", "case", "space", "quotes", "same"])
    if trap == "case":
        stored = target.upper() if target.islower() and rng.random() < 0.5 else target.capitalize() if target.islower() else target.lower()
        code = _join([f'{var} = "{stored}"', *_if_else(f'{var} == "{target}"', yes, no)])
        why = f'Capital letters count in Python text: "{stored}" and "{target}" are different, so `{var} == "{target}"` is False and the `else` runs.'
        return _out(code, MEDIUM, [yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)
    if trap == "space":
        code = _join([f'{var} = "{target} "', *_if_else(f'{var} == "{target}"', yes, no)])
        why = f'"{target} " has a space at the end, so it is not equal to "{target}". Text has to match exactly, including spaces.'
        return _out(code, MEDIUM, [yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)
    if trap == "quotes":
        code = _join([f'{var} = "{target}"', *_if_else(f"{var} == {target}", yes, no)])
        why = f'Without quotes Python reads `{target}` as a variable name, but no variable called `{target}` exists, so it raises a NameError. Text needs quotes: `"{target}"`.'
        return _out(
            code, MEDIUM, [yes, no, "Error: SyntaxError", "Error: TypeError"], why, rng,
            prompt="What is printed, or which error is raised?", allow_error=True,
        )
    code = _join([f'{var} = "{target}"', *_if_else(f'{var} != "{target}"', yes, no)])
    why = f'`{var}` is "{target}", so `{var} != "{target}"` (not equal) is False and the `else` block runs.'
    return _out(code, MEDIUM, [yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)


@generator(TOPIC, MEDIUM)
def gen_never_prints(rng: random.Random) -> Question:
    """Which message can never be printed because an earlier check catches everything first?"""
    kind = rng.choice(["grade", "grade", "rank"])
    if kind == "grade":
        steps = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]
        names = [f"Grade: {g}" for _, g in steps]
        fallback = "Grade: F"
        thresholds = [t for t, _ in steps]
    else:
        (b, s, g, d), (t_s, t_g, t_d) = rng.choice(_RANK_SETS)
        names = [d, g, s]
        thresholds = [t_d, t_g, t_s]
        fallback = b
    i = rng.randrange(len(names) - 1)  # swap rung i and i + 1: the higher one becomes unreachable
    order = list(range(len(names)))
    order[i], order[i + 1] = order[i + 1], order[i]
    rungs = [(f"score >= {thresholds[k]}", names[k]) for k in order]
    code = _join(['score = int(input("Enter a score: "))', *_ladder(rungs, fallback)])
    lost = names[i]
    hi_t, lo_t = thresholds[i], thresholds[i + 1]
    others = [n for n in [*names, fallback] if n != lost]
    why = (
        f"Any score of {hi_t} or more is also {lo_t} or more, and the `score >= {lo_t}` check comes first, so it catches those scores. "
        f"The `{lost}` branch can never run."
    )
    return _pick(
        MEDIUM,
        "Which message can this code never print?",
        lost,
        [others[min(i, len(others) - 1)], *others],
        why,
        rng,
        code=code,
    )


_COMBINED_SCENES = [
    # (kind, number variable, operator, limit, flag, message 1, message 2, message 3)
    ("and_not", "temperature", ">", 70, "is_raining", "Go to the park!", "Stay inside.", "Wear a jacket."),
    ("and_not", "temperature", ">", 75, "is_windy", "Fly a kite!", "Stay inside.", "Too cold to play."),
    ("and_flag", "age", ">=", 16, "has_permit", "You can drive.", "Get a permit first.", "You are too young."),
    ("and_flag", "money", ">=", 8, "is_hungry", "Buy a snack.", "Save your money.", "Not enough money."),
    ("and_flag", "score", ">=", 60, "did_homework", "You passed!", "Do your homework.", "Study more."),
    ("or_flag", "score", ">=", 90, "is_extra_credit", "Great job!", "Nice try.", "Keep studying."),
    ("or_flag", "age", "<", 13, "is_student", "Half-price ticket.", "Full-price ticket.", "Full-price ticket."),
]


@generator(TOPIC, MEDIUM)
def gen_combined_trace(rng: random.Random) -> Question:
    """if / elif / else with and / or / not mixing a number check and a True/False flag."""
    kind, var, op, limit, flag, m1, m2, m3 = rng.choice(_COMBINED_SCENES)
    if kind == "or_flag" and m2 == m3:  # the ticket story needs a real middle branch
        m2, middle = "Senior ticket.", f"{var} >= 65"
    elif kind == "or_flag":
        middle = f"{var} >= 70"
    else:
        middle = None
    num_cond = f"{var} {op} {limit}"
    swap = rng.random() < 0.4
    if kind == "and_not":
        first, second = (f"not {flag} and {num_cond}" if swap else f"{num_cond} and not {flag}"), num_cond
    elif kind == "and_flag":
        first, second = (f"{flag} and {num_cond}" if swap else f"{num_cond} and {flag}"), num_cond
    else:
        first, second = (f"{flag} or {num_cond}" if swap else f"{num_cond} or {flag}"), middle
    spread = rng.choice([1, 2, 5, 9])
    value = rng.choice([limit, limit - 1, limit + 1, limit + spread, max(0, limit - spread), 70 if kind == "or_flag" and var == "age" else limit + 2])
    if kind == "or_flag" and var == "age":
        value = rng.choice([12, 13, 30, 65, 70, 8])
    value = max(0, value)
    flag_val = rng.choice([True, False])
    code = _join([f"{var} = {value}", f"{flag} = {flag_val}", *_ladder([(first, m1), (second, m2)], m3)])
    env = {var: value, flag: flag_val}
    t1, t2 = bool(_truth(first, **env)), bool(_truth(second, **env))
    if t1:
        why = f"`{first}` is True here, so Python prints {_stop(m1)}"
    elif t2:
        why = f"`{first}` is False, so Python moves on to the `elif`. `{second}` is True, so it prints {_stop(m2)}"
    else:
        why = f"`{first}` is False and `{second}` is False, so the `else` runs and prints {_stop(m3)}"
    edge = _edge_note(op, value, limit)
    if edge:
        why += f" Remember: with `{var} = {value}`{edge}."
    return _out(code, MEDIUM, [m1, m2, m3, f"{m1}\n{m2}"], why, rng)


# ==========================================================================
# HARD - choice
# ==========================================================================

_GRADE_STEPS = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


@generator(TOPIC, HARD)
def gen_full_ladder_boundary(rng: random.Random) -> Question:
    """The lesson's five-grade ladder, with a score right on a threshold (sometimes a `>` twist)."""
    twist = rng.choice(["none", "gt", "gt"])
    steps = list(_GRADE_STEPS)
    ops = [">="] * 4
    if twist == "gt":
        k = rng.randrange(4)
        ops[k] = ">"
        score = steps[k][0]
    else:
        k = rng.randrange(4)
        score = steps[k][0] - 1 if rng.random() < 0.6 else steps[k][0]
    rungs = [(f"score {op} {t}", f"Grade: {g}") for op, (t, g) in zip(ops, steps)]
    code = _join([f"score = {score}", *_ladder(rungs, "Grade: F")])
    why = _ladder_why("score", score, rungs, "Grade: F")
    if twist == "gt":
        why += f" Careful: `>` does not include {score}, so {score} falls through to the next grade."
    wrong = [f"Grade: {g}" for g in "ABCDF"]
    return _out(code, HARD, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_ladder_order_hard(rng: random.Random) -> Question:
    """A four-rung ladder with two checks swapped: which grade really prints?"""
    steps = list(_GRADE_STEPS)
    i = rng.randrange(3)  # swap rung i and i + 1
    order = list(steps)
    order[i], order[i + 1] = order[i + 1], order[i]
    # a score that satisfies the swapped (lower) check first
    hi_t, hi_g = steps[i]
    lo_t, lo_g = steps[i + 1]
    score = rng.randint(hi_t, hi_t + 9)
    rungs = [(f"score >= {t}", f"Grade: {g}") for t, g in order]
    code = _join([f"score = {score}", *_ladder(rungs, "Grade: F")])
    why = (
        _ladder_why("score", score, rungs, "Grade: F")
        + f" The `score >= {lo_t}` check sits above `score >= {hi_t}`, so {score} is caught too early."
    )
    return _out(code, HARD, [f"Grade: {g}" for g in "ABCDF"], why, rng)


@generator(TOPIC, HARD)
def gen_debug_trick_twist(rng: random.Random) -> Question:
    """The Quick Debug Trick with a swap or an update before the check: trace the new values."""
    xv = rng.randint(1, 9)
    yv = xv if rng.random() < 0.12 else rng.randint(1, 9)
    twist = rng.choice(["swap", "swap", "add", "double"])
    if twist == "swap" and xv == yv:
        yv = xv % 9 + 1  # swapping two equal values would change nothing
    if twist == "swap":
        line, expl = "x, y = y, x", "The swap line exchanges the two values before anything is printed."
        nx, ny = yv, xv
    elif twist == "add":
        k = rng.randint(2, 6)
        line, expl = f"x = x + {k}", f"`x = x + {k}` changes x before anything is printed."
        nx, ny = xv + k, yv
    else:
        line, expl = "y = y * 2", "`y = y * 2` changes y before anything is printed."
        nx, ny = xv, yv * 2
    body = ["", 'print("x =", x, "y =", y)  # sanity check', "if x > y:", '    print("x is larger")', "else:", '    print("y is larger")']
    code = _join([f"x = {xv}", f"y = {yv}", line, *body[1:]])
    untwisted = _join([f"x = {xv}", f"y = {yv}", *body[1:]])
    msg = "x is larger" if nx > ny else "y is larger"
    other = "y is larger" if nx > ny else "x is larger"
    first = f"x = {nx} y = {ny}"
    old_first = f"x = {xv} y = {yv}"
    wrong = [
        _ran(untwisted),
        f"{first}\n{other}",
        f"{old_first}\n{msg}",
        f"{old_first}\n{other}",
        f"x = {nx}, y = {ny}\n{msg}",
        f"{nx} {ny}\n{msg}",
    ]
    why = f"{expl} So the check prints `{first}`, and `{nx} > {ny}` is {nx > ny}"
    why += ", so the `else` runs." if nx <= ny else ", so the `if` runs."
    return _out(code, HARD, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_diamond_trace(rng: random.Random) -> Question:
    """The Rank Checker with the Diamond bonus added in different places."""
    (b, s, g, d), (t_s, t_g, t_d) = rng.choice(_RANK_SETS)
    place = rng.choice(["top", "middle", "bottom", "bottom"])
    rungs = [(t_g, g), (t_s, s)]
    rungs.insert({"top": 0, "middle": 1, "bottom": 2}[place], (t_d, d))
    score = rng.choice([rng.randint(t_d, t_d + 800), t_d, t_d, rng.randint(t_g, t_d - 1)])
    code = _join([f"score = {score}", *_ladder([(f"score >= {t}", name) for t, name in rungs], b)])
    why = _ladder_why("score", score, [(f"score >= {t}", name) for t, name in rungs], b)
    if place != "top" and score >= t_d:
        why += f" The {d} check is never reached for a score like {score}, because an earlier `>=` check is already True."
    return _out(code, HARD, [b, s, g, d], why, rng)


def _simulate(ladder: list[tuple[str, int, str]], last: str, score: int) -> str:
    """Which rank a ladder of (operator, threshold, name) gives a score."""
    for op, limit, name in ladder:
        if _CMP[op](score, limit):
            return name
    return last


@generator(TOPIC, HARD)
def gen_which_ladder_correct(rng: random.Random) -> Question:
    """Which order of checks gives every score the right rank?"""
    (b, s, g, d), (t_s, t_g, t_d) = rng.choice(_RANK_SETS)
    good = [(">=", t_d, d), (">=", t_g, g), (">=", t_s, s)]

    def expected(sc: int) -> str:
        return d if sc >= t_d else g if sc >= t_g else s if sc >= t_s else b

    probes = [0, t_s - 1, t_s, t_g - 1, t_g, t_d - 1, t_d, t_d + 500]
    candidates = [
        [(">=", t_s, s), (">=", t_g, g), (">=", t_d, d)],  # lowest first
        [(">=", t_g, g), (">=", t_d, d), (">=", t_s, s)],  # Diamond tucked in the middle
        [(">=", t_g, g), (">=", t_s, s), (">=", t_d, d)],  # Diamond last
        [(">", t_d, d), (">", t_g, g), (">", t_s, s)],  # right order, wrong boundary
        [(">=", t_d, d), (">=", t_s, s), (">=", t_g, g)],  # Silver before Gold
    ]
    wrong = [c for c in candidates if any(_simulate(c, b, p) != expected(p) for p in probes)]
    if any(_simulate(good, b, p) != expected(p) for p in probes):
        raise GenerationError("the reference ladder is wrong")
    rng.shuffle(wrong)

    def show(ladder: list[tuple[str, int, str]]) -> str:
        lines = [f"{'if' if i == 0 else 'elif'} score {op} {limit}:  # {name}" for i, (op, limit, name) in enumerate(ladder)]
        return _join([*lines, f"else:  # {b}"])

    why = (
        f"The highest threshold has to come first: a score of {t_d} is also {t_g} or more and {t_s} or more, "
        "so a lower check placed above it would catch the score too early. Use `>=` so the limit itself counts."
    )
    return _pick(
        HARD,
        f"Which ladder gives {d} for {t_d} or more, {g} for {t_g} or more, {s} for {t_s} or more, and {b} for anything lower?",
        show(good),
        [show(c) for c in wrong],
        why,
        rng,
    )


@generator(TOPIC, HARD)
def gen_number_test_order(rng: random.Random) -> Question:
    """Number Test: the range check placed first makes the special number unreachable."""
    lo, hi = rng.choice([(1, 100), (1, 100), (1, 10), (10, 99)])
    special = rng.choice([50, 7, 25, 42]) if (lo, hi) == (1, 100) else rng.randint(lo + 1, hi - 1)
    layout = rng.choice(["range_first", "range_first", "special_first"])
    number = rng.choice([special, special, rng.randint(lo, hi), hi + 5, lo - 1])
    in_range = f"{lo} <= number <= {hi}"
    is_special = f"number == {special}"
    rungs = (
        [(in_range, "In range"), (is_special, "Special number")]
        if layout == "range_first"
        else [(is_special, "Special number"), (in_range, "In range")]
    )
    code = _join([f"number = {number}", *_ladder(rungs, "Out of range")])
    why = _ladder_why("number", number, rungs, "Out of range")
    if layout == "range_first" and number == special:
        why += f" {special} is in range too, so the `Special number` check can never be reached: put the more specific check first."
    return _out(code, HARD, ["In range", "Special number", "Out of range", "In range\nSpecial number"], why, rng)


@generator(TOPIC, HARD)
def gen_nested_license_trace(rng: random.Random) -> Question:
    """Two-level nesting; sometimes the `else` lines up with the outer `if` instead."""
    flag, ok, need = rng.choice(
        [
            ("has_permit", "You can drive.", "Get your permit first."),
            ("has_ticket", "Enjoy the show!", "Buy a ticket first."),
            ("has_pass", "Welcome in.", "Show your pass."),
        ]
    )
    age_limit = rng.choice([16, 16, 13, 18])
    young = "You are too young."
    layout = rng.choice(["inner_else", "inner_else", "outer_else"])
    age = rng.choice([age_limit - rng.randint(1, 3), age_limit + rng.randint(0, 3), age_limit])
    value = rng.choice([True, False])
    if layout == "inner_else":
        body = [
            f"if age >= {age_limit}:",
            f"    if {flag}:",
            f"        {_say(ok)}",
            "    else:",
            f"        {_say(need)}",
            "else:",
            f"    {_say(young)}",
        ]
    else:
        body = [
            f"if age >= {age_limit}:",
            f"    if {flag}:",
            f"        {_say(ok)}",
            "else:",
            f"    {_say(young)}",
        ]
    code = _join([f"age = {age}", f"{flag} = {value}", *body])
    outer = age >= age_limit
    if not outer:
        why = f"`age >= {age_limit}` is False, so Python skips the whole nested block and runs the outer `else`: {_stop(young)}"
    elif value:
        why = f"`age >= {age_limit}` is True and `{flag}` is True, so the inner `if` runs: {_stop(ok)}"
    elif layout == "inner_else":
        why = f"`age >= {age_limit}` is True, but `{flag}` is False, so the inner `else` runs: {_stop(need)}"
    else:
        why = (
            f"`age >= {age_limit}` is True, so the outer `else` is skipped. But `{flag}` is False and the `else` belongs to "
            "the outer `if` (look at its indentation), so nothing is printed."
        )
    return _out(code, HARD, [ok, need, young, NOTHING_PRINTED], why, rng)


_NEST_PAIRS = [
    ("temperature > 70", "not is_raining", ["temperature", "is_raining"], "Great day to go to the park!"),
    ("age >= 16", "has_permit", ["age", "has_permit"], "You can drive."),
    ("money >= 5", "is_hungry", ["money", "is_hungry"], "You can buy a snack."),
    ("score >= 60", "not is_absent", ["score", "is_absent"], "You passed."),
]


@generator(TOPIC, HARD)
def gen_nested_equivalent(rng: random.Random) -> Question:
    """Which single `if` with and / or does the same job as two nested ifs?"""
    first, second, names, msg = rng.choice(_NEST_PAIRS)
    code = _join([f"if {first}:", f"    if {second}:", f"        {_say(msg)}"])
    correct = f"if {first} and {second}:"
    neg_second = second[4:] if second.startswith("not ") else f"not {second}"
    neg_first = f"not ({first})"
    pool = [
        f"if {first} or {second}:",
        f"if {first} and {neg_second}:",
        f"if {neg_first} and {second}:",
        f"if {first}:",
        f"if {neg_first} or {neg_second}:",
    ]
    # Compare behaviour on every combination (number just under / over the limit, flag True / False).
    num_name, flag_name = names
    limit = int("".join(ch for ch in first if ch.isdigit()))

    def table(line: str) -> tuple:
        cond = line[3:-1]
        return tuple(
            bool(_truth(cond, **{num_name: n, flag_name: f})) for n in (limit - 1, limit, limit + 1) for f in (True, False)
        )

    want = tuple(
        bool(_truth(f"({first}) and ({second})", **{num_name: n, flag_name: f}))
        for n in (limit - 1, limit, limit + 1)
        for f in (True, False)
    )
    wrong = [p for p in pool if table(p) != want]
    if table(correct) != want:
        raise GenerationError("nested equivalent is wrong")
    rest = wrong[1:]
    rng.shuffle(rest)
    why = "Nesting means the second check only happens after the first one passed, so both must be True: that is exactly what `and` says."
    return _pick(HARD, "Which single `if` does exactly the same thing as the nested `if`s?", correct, wrong[:1] + rest, why, rng, code=code)


@generator(TOPIC, HARD)
def gen_dead_branch_mod(rng: random.Random) -> Question:
    """A `%` check that is a multiple of an earlier one: the later branch is dead."""
    a, b = rng.choice([(2, 4), (3, 6), (5, 10), (2, 6), (3, 9)])
    var = rng.choice(["number", "n"])
    names = {
        (2, 4): ("Even", "Multiple of 4", "Odd"),
        (2, 6): ("Even", "Multiple of 6", "Odd"),
        (3, 6): ("Multiple of 3", "Multiple of 6", "Neither"),
        (3, 9): ("Multiple of 3", "Multiple of 9", "Neither"),
        (5, 10): ("Multiple of 5", "Multiple of 10", "Neither"),
    }[(a, b)]
    value = rng.choice([b * rng.randint(1, 4), b * rng.randint(1, 4), a * rng.randint(1, 8), rng.randint(1, 30)])
    rungs = [(f"{var} % {a} == 0", names[0]), (f"{var} % {b} == 0", names[1])]
    code = _join([f"{var} = {value}", *_ladder(rungs, names[2])])
    why = _ladder_why(var, value, rungs, names[2])
    why += f" (Every multiple of {b} is also a multiple of {a}, so the `{var} % {b} == 0` branch can never run.)"
    return _out(code, HARD, [names[0], names[1], names[2], f"{names[0]}\n{names[1]}"], why, rng)


@generator(TOPIC, HARD)
def gen_weekend_plan_trace(rng: random.Random) -> Question:
    """Three variables and three conditions in one ladder."""
    weekend, homework, money = rng.choice([True, False]), rng.choice([True, False]), rng.choice([4, 8, 10, 12, 20])
    rungs = [
        ("is_weekend and has_homework", "Do homework first."),
        ("is_weekend and money >= 10", "Go to the movies."),
        ("is_weekend", "Stay home."),
    ]
    code = _join(
        [f"is_weekend = {weekend}", f"has_homework = {homework}", f"money = {money}", *_ladder(rungs, "Go to school.")]
    )
    env = {"is_weekend": weekend, "has_homework": homework, "money": money}
    steps = []
    for cond, msg in rungs:
        ok = _truth(cond, **env)
        steps.append(f"`{cond}` is {ok}")
        if ok:
            why = "Top to bottom: " + ", ".join(steps) + f", so it prints {_stop(msg)}"
            break
    else:
        why = "Top to bottom: " + ", ".join(steps) + ", so the `else` runs."
    return _out(code, HARD, [m for _, m in rungs] + ["Go to school."], why, rng)


@generator(TOPIC, HARD)
def gen_if_elif_mix(rng: random.Random) -> Question:
    """Separate ifs next to an if / elif pair: count which lines really print."""
    n = rng.randint(3, 20)
    a = rng.randint(2, 8)
    b = a + rng.randint(3, 7)
    c = a + rng.randint(1, b - a - 1)  # a < c < b, so the `elif` can really run
    k = rng.choice([2, 3])

    def build(chain: bool) -> str:
        return _join(
            [
                f"n = {n}",
                f"if n > {a}:",
                '    print("A")',
                f"if n > {b}:",
                '    print("B")',
                f"{'elif' if chain else 'if'} n > {c}:",
                '    print("C")',
                f"if n % {k} == 0:",
                '    print("D")',
            ]
        )

    code = build(True)
    printed = _ran(code)
    wrong = [_ran(build(False))]
    lines = printed.split("\n") if printed != NOTHING_PRINTED else []
    if lines:
        wrong.append(lines[0])
        wrong.append("\n".join(lines[:-1]) if len(lines) > 1 else NOTHING_PRINTED)
    wrong += ["A\nB\nC\nD", NOTHING_PRINTED, "A\nB\nD", "A\nD", "A\nC", "B\nC"]
    shown = "nothing" if printed == NOTHING_PRINTED else "`" + printed.replace("\n", "` then `") + "`"
    why = (
        f"The `elif` is tied to the `if n > {b}` line, so it only runs when that check is False. "
        f"The other two `if` lines are checked on their own. With `n = {n}` that prints {shown}."
    )
    return _out(code, HARD, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_updates_then_checks(rng: random.Random) -> Question:
    """One `if` changes the variable, so a later `if` sees the NEW value (an `elif` would not)."""
    var, label = rng.choice([("score", "Score:"), ("points", "Points:"), ("coins", "Coins:")])
    t1 = rng.choice([50, 80, 100])
    gain = rng.choice([5, 10, 15])
    t2 = t1 + gain - rng.choice([0, 1, 2, 3])
    msg = rng.choice(["Bonus!", "Level up!", "Treasure unlocked!"])
    zone = rng.choice(["update", "update", "update", "high", "low"])
    if zone == "update":
        start = rng.randint(t1, t2 - 1)
    elif zone == "high":
        start = rng.randint(t2, t2 + 6)
    else:
        start = rng.randint(max(0, t1 - 12), t1 - 1)
    chained = rng.random() < 0.45
    code = _join(
        [
            f"{var} = {start}",
            f"if {var} >= {t1}:",
            f"    {var} = {var} + {gain}",
            f"{'elif' if chained else 'if'} {var} >= {t2}:",
            f'    print("{msg}")',
            f'print("{label}", {var})',
        ]
    )
    new_value = start + gain if start >= t1 else start
    bonus = (start < t1 and new_value >= t2) if chained else (new_value >= t2)
    steps = []
    if start >= t1:
        steps.append(f"`{var} >= {t1}` is True, so `{var}` becomes {new_value}")
    else:
        steps.append(f"`{var} >= {t1}` is False, so `{var}` stays {start}")
    if chained and start >= t1:
        steps.append(f"the `elif` is skipped because the first branch already ran, so `{msg}` does not print")
    elif chained:
        steps.append(f"`{var} >= {t2}` is {new_value >= t2}")
    else:
        steps.append(f"the second `if` is checked on its own with `{var}` = {new_value}, and `{var} >= {t2}` is {new_value >= t2}")
    why = "; ".join(steps) + f". Then `print` shows {var} = {new_value}."

    def lines(show_msg: bool, value: int) -> str:
        return "\n".join(([msg] if show_msg else []) + [f"{label} {value}"])

    wrong = [
        lines(not bonus, new_value),
        lines(bonus, start) if start != new_value else lines(bonus, new_value + gain),
        lines(not bonus, start) if start != new_value else lines(not bonus, new_value + gain),
        lines(bonus, new_value + gain),
    ]
    return _out(code, HARD, wrong, why, rng)


# ==========================================================================
# BLANKS - fill in the blanks (typed, like the Canvas "fill in multiple blanks")
# ==========================================================================

B1, B2, B3, B4 = (blank_mark(i) for i in (1, 2, 3, 4))


def _blank_q(
    difficulty: int,
    prompt: str,
    template: str,
    blanks: list[Blank],
    explanation: str,
    expect: str,
) -> Question:
    return blanks_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        template=template,
        blanks=blanks,
        explanation=explanation,
        expect_output=expect,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_colons(rng: random.Random) -> Question:
    """The missing-colon pitfall: type the colon that ends each if / elif / else line."""
    shape = rng.choice(["if_else", "ladder"])
    if shape == "if_else":
        var, limit, yes, no = rng.choice(_DECISIONS)
        value = limit + rng.choice([0, 1, 3])
        lines = [f"{var} = {value}", f"if {var} >= {limit}{B1}", f"    {_say(yes)}", f"else{B2}", f"    {_say(no)}"]
        blanks = [Blank([":"], hint="symbol"), Blank([":"], hint="symbol")]
        expect = yes
    else:
        score = rng.choice([85, 72, 64, 93])
        lines = [
            f"score = {score}",
            f"if score >= 90{B1}",
            '    print("Grade: A")',
            f"elif score >= 80{B2}",
            '    print("Grade: B")',
            f"else{B3}",
            '    print("Grade: C")',
        ]
        blanks = [Blank([":"], hint="symbol") for _ in range(3)]
        expect = "Grade: A" if score >= 90 else "Grade: B" if score >= 80 else "Grade: C"
    return _blank_q(
        EASY,
        "Python needs one small symbol at the end of each of these lines. Type it in every blank.",
        _join(lines),
        blanks,
        "Every `if`, `elif` and `else` line ends with a colon `:`. Forgetting it is one of the lesson's common pitfalls.",
        expect,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_operator_else(rng: random.Random) -> Question:
    """The driver's-license if / else: pick the comparison and the fallback keyword."""
    var, limit, yes, no = rng.choice(_DECISIONS)
    op = rng.choice([">=", "<"])
    if op == ">=":
        value = limit + rng.choice([0, 0, 2, 5])
        first, second = yes, no
        rule = f"`{var}` is {limit} or more"
        rule_plain = f"{var} is {limit} or more"
        expect = yes
    else:
        value = max(0, limit - rng.choice([1, 3, 6]))
        first, second = no, yes
        rule = f"`{var}` is less than {limit}"
        rule_plain = f"{var} is less than {limit}"
        expect = no
    template = _join([f"{var} = {value}", f"if {var} {B1} {limit}:", f"    {_say(first)}", f"{B2}:", f"    {_say(second)}"])
    return _blank_q(
        EASY,
        f"Fill in the blanks so the first message prints when {rule}, and the second message is the fallback.",
        template,
        [Blank([op], hint="comparison"), Blank(["else"], hint="keyword")],
        f"`{var} {op} {limit}` says \"{rule_plain}\". `else:` is the fallback that runs when the condition is False.",
        expect,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_elif(rng: random.Random) -> Question:
    """The grade ladder: elif and else."""
    t1, t2, t3 = rng.choice([(90, 80, 70), (90, 80, 70), (80, 70, 60)])
    letters = "ABC" if t1 == 90 else "BCD"
    last = "F" if t1 == 90 else "F"
    three = rng.random() < 0.4
    score = rng.choice([t1 + 3, t2 + 5, t2, t3 + 4, t3 - 5])
    if three:
        lines = [
            f"score = {score}",
            f"if score >= {t1}:",
            f'    print("Grade: {letters[0]}")',
            f"{B1} score >= {t2}:",
            f'    print("Grade: {letters[1]}")',
            f"{B2} score >= {t3}:",
            f'    print("Grade: {letters[2]}")',
            f"{B3}:",
            f'    print("Grade: {last}")',
        ]
        blanks = [Blank(["elif"], hint="keyword"), Blank(["elif"], hint="keyword"), Blank(["else"], hint="keyword")]
        expect = f"Grade: {letters[0] if score >= t1 else letters[1] if score >= t2 else letters[2] if score >= t3 else last}"
    else:
        lines = [
            f"score = {score}",
            f"if score >= {t1}:",
            f'    print("Grade: {letters[0]}")',
            f"{B1} score >= {t2}:",
            f'    print("Grade: {letters[1]}")',
            f"{B2}:",
            f'    print("Grade: {letters[2]}")',
        ]
        blanks = [Blank(["elif"], hint="keyword"), Blank(["else"], hint="keyword")]
        expect = f"Grade: {letters[0] if score >= t1 else letters[1] if score >= t2 else letters[2]}"
    return _blank_q(
        EASY,
        'Fill in the keywords so the code checks "else if" and then the fallback.',
        _join(lines),
        blanks,
        "`elif` is Python's \"else if\" (another condition, checked only if the ones above were False) and `else:` is the fallback with no condition.",
        expect,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_equals(rng: random.Random) -> Question:
    """= vs ==: type the operator that compares."""
    kind = rng.choice(["number", "number", "text"])
    if kind == "number":
        var = rng.choice(["answer", "guess", "count", "number"])
        val = str(rng.randint(2, 12))
        yes, no = rng.choice([("Correct!", "Try again."), ("You win!", "Nope."), ("Match!", "No match.")])
    else:
        var, val = rng.choice(
            [
                ("name", f'"{rng.choice(["Ada", "Sam", "Ben", "Ivy", "Eli"])}"'),
                ("color", f'"{rng.choice(["red", "blue", "green"])}"'),
                ("pet", f'"{rng.choice(["cat", "dog", "fish"])}"'),
                ("word", f'"{rng.choice(["Python", "code", "loop"])}"'),
            ]
        )
        yes, no = rng.choice([("Same!", "Different."), ("Welcome back!", "Who are you?"), ("Match!", "No match.")])
    template = _join([f"{var} = {val}", f"if {var} {B1} {val}:", f"    {_say(yes)}", f"{B2}:", f"    {_say(no)}"])
    return _blank_q(
        EASY,
        f"Fill in the blanks so the code checks whether `{var}` equals {val}.",
        template,
        [Blank(["=="], hint="comparison"), Blank(["else"], hint="keyword")],
        "`=` assigns a value; `==` compares two values. `else:` is the fallback when the condition is False.",
        yes,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_logic_word(rng: random.Random) -> Question:
    """and / or / not inside the park conditions or a two-flag check."""
    variant = rng.choice(["park_and", "park_not", "flags"])
    if variant == "park_and":
        temperature = rng.choice([60, 65, 68])
        template = _join(
            [
                f"temperature = {temperature}",
                "is_raining = True",
                f"if temperature > 70 {B1} not is_raining:",
                '    print("Great day to go to the park!")',
                f"elif temperature > 70 {B2} is_raining:",
                '    print("Stay inside.")',
                "else:",
                '    print("Might be too cold.")',
            ]
        )
        return _blank_q(
            MEDIUM,
            'Both parts of each condition must be True ("warmer than 70 AND not raining"). Fill in the blanks.',
            template,
            [Blank(["and"], hint="and / or / not"), Blank(["and"], hint="and / or / not")],
            "With `and`, both sides must be True. The temperature is not above 70, so neither `and` condition is True and the `else` runs.",
            "Might be too cold.",
        )
    if variant == "park_not":
        temperature = rng.choice([72, 75, 80, 90])
        template = _join(
            [
                f"temperature = {temperature}",
                "is_raining = False",
                f"if temperature > 70 and {B1} is_raining:",
                '    print("Great day to go to the park!")',
                "else:",
                '    print("Stay inside.")',
            ]
        )
        return _blank_q(
            MEDIUM,
            'Fill in the blank so the park message prints when it is warm and it is NOT raining.',
            template,
            [Blank(["not"], hint="and / or / not")],
            "`not is_raining` is True when `is_raining` is False, so the park message prints on a warm, dry day.",
            "Great day to go to the park!",
        )
    a, b, yes, no = rng.choice(_BOOL_SCENES)
    template = _join(
        [
            f"{a} = True",
            f"{b} = False",
            f"if {a} {B1} {b}:",
            f"    {_say(yes)}",
            "else:",
            f"    {_say(no)}",
        ]
    )
    return _blank_q(
        MEDIUM,
        "Fill in the blank so the first message prints when at least one of the two flags is True.",
        template,
        [Blank(["or"], hint="and / or / not")],
        "`or` is True when at least one side is True. With `and`, both would have to be True.",
        yes,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_nested(rng: random.Random) -> Question:
    """The nested money / snack / drink code: the inner `if` and its condition."""
    t1, t2, item1, item2 = rng.choice([(5, 8, "snack", "drink"), (5, 8, "snack", "drink"), (4, 6, "snack", "drink"), (10, 15, "ticket", "popcorn")])
    money = t2 + rng.randint(0, 5)
    msg1, msg2 = f"You can buy a {item1}.", f"You can also buy a {item2}."
    template = _join(
        [
            f"money = {money}",
            f"if money >= {t1}:",
            f"    {_say(msg1)}",
            f"    {B1} {B2}:",
            f"        {_say(msg2)}",
            "else:",
            '    print("Not enough money.")',
        ]
    )
    return _blank_q(
        MEDIUM,
        f"Nest a second check inside the first: the {item2} costs {t2}, so it should be offered when `money` is {t2} or more.",
        template,
        [
            Blank(["if"], hint="keyword"),
            Blank([f"money >= {t2}", f"money > {t2 - 1}", f"{t2} <= money"], hint="condition", mode="expr"),
        ],
        "Nest an `if` inside another `if` when the second check only makes sense after the first one passed.",
        f"{msg1}\n{msg2}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_sign_checker(rng: random.Random) -> Question:
    """Sign Checker: > 0, < 0 and the else for zero."""
    var = rng.choice(["number", "n"])
    value = rng.choice([-4, -12, 7, 25, 0])
    template = _join(
        [
            f"{var} = {value}",
            f"if {var} {B1} 0:",
            '    print("Positive")',
            f"elif {var} {B2} 0:",
            '    print("Negative")',
            f"{B3}:",
            '    print("Zero")',
        ]
    )
    expect = "Positive" if value > 0 else "Negative" if value < 0 else "Zero"
    return _blank_q(
        MEDIUM,
        "Complete the Sign Checker: it should print Positive above zero, Negative below zero, and Zero otherwise.",
        template,
        [Blank([">"], hint="comparison"), Blank(["<"], hint="comparison"), Blank(["else"], hint="keyword")],
        "Positive is `> 0`, Negative is `< 0`, and zero is the only number left over, so it goes in the `else`.",
        expect,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_even_odd(rng: random.Random) -> Question:
    """even / odd (or multiple of k) with % and ==."""
    k = rng.choice([2, 2, 2, 3, 5])
    var = rng.choice(["number", "n"])
    value = rng.randint(1, 40)
    if k == 2:
        yes, no, what = "Even", "Odd", "even"
    else:
        yes, no, what = f"Multiple of {k}", f"Not a multiple of {k}", f"a multiple of {k}"
    template = _join([f"{var} = {value}", f"if {var} {B1} {k} {B2} 0:", f"    {_say(yes)}", f"{B3}:", f"    {_say(no)}"])
    return _blank_q(
        MEDIUM,
        f"Fill in the blanks so the code prints `{yes}` when `{var}` is {what}.",
        template,
        [Blank(["%"], hint="operator"), Blank(["=="], hint="comparison"), Blank(["else"], hint="keyword")],
        f"`{var} % {k}` is the remainder after dividing by {k}; when it `== 0` the number is {what}.",
        yes if value % k == 0 else no,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_rank_thresholds(rng: random.Random) -> Question:
    """Rank Checker thresholds."""
    (b, s, g, _d), (t_s, t_g, _t_d) = rng.choice(_RANK_SETS)
    score = rng.choice([t_s + 450, t_g + 120, t_s - 100, t_s, t_g])
    template = _join(
        [
            f"score = {score}",
            f"if score >= {B1}:",
            f"    {_say(g)}",
            f"elif score >= {B2}:",
            f"    {_say(s)}",
            "else:",
            f"    {_say(b)}",
        ]
    )
    expect = g if score >= t_g else s if score >= t_s else b
    return _blank_q(
        MEDIUM,
        f"Rank Checker: {g} is {t_g} or more, {s} is {t_s} to {t_g - 1}, and {b} is less than {t_s}. Type the two limits.",
        template,
        [Blank([str(t_g)], hint="number", mode="expr"), Blank([str(t_s)], hint="number", mode="expr")],
        f"The highest limit goes first: `score >= {t_g}` is {g}, and the `elif` only needs the lower limit `score >= {t_s}`.",
        expect,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_number_test(rng: random.Random) -> Question:
    """Number Test: the special number is checked first (if / elif / else + the upper limit)."""
    hi = rng.choice([100, 100, 50, 20])
    special = rng.choice([50, 7, 25]) if hi == 100 else rng.randint(3, hi - 2)
    number = rng.choice([special, special, rng.randint(1, hi), hi + 3])
    template = _join(
        [
            f"number = {number}",
            f"{B1} number == {special}:",
            '    print("Special number")',
            f"{B2} 1 <= number <= {B3}:",
            '    print("In range")',
            "else:",
            '    print("Out of range")',
        ]
    )
    expect = "Special number" if number == special else "In range" if 1 <= number <= hi else "Out of range"
    return _blank_q(
        HARD,
        f"Number Test: `{special}` is also in range, so it must be checked first. Numbers from 1 to {hi} (inclusive) are in range.",
        template,
        [Blank(["if"], hint="keyword"), Blank(["elif"], hint="keyword"), Blank([str(hi)], hint="number", mode="expr")],
        f"Check the most specific case first with `if`, then `elif` for the range ({hi} is the top of the range). If the range came first, {special} would print `In range`.",
        expect,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_nested_else(rng: random.Random) -> Question:
    """A nested license check: outer comparison, inner if, inner else."""
    flag, ok, need = rng.choice(
        [
            ("has_permit", "You can drive.", "Get your permit first."),
            ("has_ticket", "Enjoy the show!", "Buy a ticket first."),
        ]
    )
    age = rng.choice([16, 17, 20])
    value = rng.choice([True, False])
    template = _join(
        [
            f"age = {age}",
            f"{flag} = {value}",
            f"if age {B1} 16:",
            f"    {B2} {flag}:",
            f"        {_say(ok)}",
            f"    {B3}:",
            f"        {_say(need)}",
            "else:",
            '    print("You are too young.")',
        ]
    )
    return _blank_q(
        HARD,
        "Complete the nested check: people who are 16 or older get a second question about the flag.",
        template,
        [Blank([">="], hint="comparison"), Blank(["if"], hint="keyword"), Blank(["else"], hint="keyword")],
        "`age >= 16` lets 16 itself through. The inner `if` / `else` pair is indented inside the outer `if`, so it only runs for people who passed the first check.",
        ok if value else need,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_rank_ladder(rng: random.Random) -> Question:
    """The whole Diamond ladder: if / elif / elif / else."""
    (b, s, g, d), (t_s, t_g, t_d) = rng.choice(_RANK_SETS)
    score = rng.choice([t_d + 400, t_d, t_g + 100, t_s + 50, t_s - 20])
    template = _join(
        [
            f"score = {score}",
            f"{B1} score >= {t_d}:",
            f"    {_say(d)}",
            f"{B2} score >= {t_g}:",
            f"    {_say(g)}",
            f"{B3} score >= {t_s}:",
            f"    {_say(s)}",
            f"{B4}:",
            f"    {_say(b)}",
        ]
    )
    expect = d if score >= t_d else g if score >= t_g else s if score >= t_s else b
    return _blank_q(
        HARD,
        f"Rank Checker with the {d} bonus: type the four keywords that turn this into one if / elif / else chain.",
        template,
        [Blank(["if"], hint="keyword"), Blank(["elif"], hint="keyword"), Blank(["elif"], hint="keyword"), Blank(["else"], hint="keyword")],
        f"Only the first line is an `if`. The next checks are `elif` (so only the first True branch runs), and the fallback is `else:`. The highest threshold ({t_d}) comes first.",
        expect,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_debug_trick(rng: random.Random) -> Question:
    """The Quick Debug Trick: print the values, then compare them."""
    a, b = rng.choice([("x", "y"), ("x", "y"), ("a", "b")])
    xv, yv = rng.sample(range(1, 10), 2)
    template = _join(
        [
            f"{a} = {xv}",
            f"{b} = {yv}",
            f'print("{a} =", {B1}, "{b} =", {B2})  # sanity check',
            f"if {a} {B3} {b}:",
            f'    print("{a} is larger")',
            "else:",
            f'    print("{b} is larger")',
        ]
    )
    expect = f"{a} = {xv} {b} = {yv}\n" + (f"{a} is larger" if xv > yv else f"{b} is larger")
    return _blank_q(
        MEDIUM,
        f"Quick Debug Trick: print the current values of `{a}` and `{b}`, then check whether `{a}` is greater than `{b}`. Fill in the blanks.",
        template,
        [Blank([a], hint="variable"), Blank([b], hint="variable"), Blank([">"], hint="comparison")],
        f'The sanity check prints each value after its label: `print("{a} =", {a}, "{b} =", {b})`. Then `{a} > {b}` is True only when {a} is greater than {b}.',
        expect,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_between(rng: random.Random) -> Question:
    """A chained comparison for 'between lo and hi (inclusive)'."""
    var, lo, hi = rng.choice([("age", 13, 19), ("temperature", 60, 80), ("number", 1, 100), ("score", 70, 79), ("money", 5, 10)])
    value = rng.choice([lo, hi, (lo + hi) // 2, hi + 3, lo - 1])
    template = _join(
        [
            f"{var} = {value}",
            f"if {B1} <= {var} <= {B2}:",
            '    print("In range")',
            "else:",
            '    print("Out of range")',
        ]
    )
    return _blank_q(
        MEDIUM,
        f"Fill in the two limits so the condition is True when {var} is between {lo} and {hi}, including {lo} and {hi}.",
        template,
        [Blank([str(lo)], hint="number", mode="expr"), Blank([str(hi)], hint="number", mode="expr")],
        f"A chained comparison reads like math: `{lo} <= {var} <= {hi}`. Because it uses `<=` on both sides, {lo} and {hi} themselves count.",
        "In range" if lo <= value <= hi else "Out of range",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_cast_input(rng: random.Random) -> Question:
    """Sign Checker / Rank Checker set-up: input() is text, so cast it before comparing."""
    kind = rng.choice(["sign", "rank", "rank"])
    if kind == "sign":
        name = rng.choice(["number", "n", "num", "value"])
        template = _join(
            [
                f'{name} = {B1}(input("Enter a number: "))',
                f"if {name} {B2} 0:",
                '    print("Positive")',
                f"elif {name} {B3} 0:",
                '    print("Negative")',
                "else:",
                '    print("Zero")',
            ]
        )
        return blanks_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=rng.choice(
                [
                    "Sign Checker: `input()` gives text, so cast it to a number first. Then compare it with 0.",
                    "Sign Checker: fill in the cast and the two comparisons (Positive is above 0, Negative is below 0).",
                ]
            ),
            template=template,
            blanks=[
                Blank(["int", "float"], hint="cast"),
                Blank([">"], hint="comparison"),
                Blank(["<"], hint="comparison"),
            ],
            explanation="`input()` always returns a string, so cast it with `int()` (or `float()` for decimals) before comparing. Positive is `> 0`, Negative is `< 0`.",
        )
    var, ask, (r0, r1, r2), (t1, t2) = rng.choice(_RANK_STORIES)
    template = _join(
        [
            f'{var} = {B1}(input("{ask}"))',
            f"if {var} >= {t2}:",
            f'    print("You earned {r2} rank!")',
            f"{B2} {var} >= {t1}:",
            f'    print("You earned {r1} rank!")',
            f"{B3}:",
            f'    print("You earned {r0} rank!")',
        ]
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Rank Checker: turn the typed text into a whole number, then finish the ladder with the right keywords.",
        template=template,
        blanks=[Blank(["int"], hint="cast"), Blank(["elif"], hint="keyword"), Blank(["else"], hint="keyword")],
        explanation="`input()` returns text, so `int()` makes it a number you can compare. `elif` checks the next limit, and `else:` catches everything lower.",
    )


# ==========================================================================
# MATCH
# ==========================================================================


@generator(TOPIC, EASY, qtype="match")
def gen_match_keywords(rng: random.Random) -> Question:
    """Keyword -> what it does."""
    pairs = [
        ("if", "Starts a decision by checking a condition"),
        ("elif", "Checks another condition if the ones above were False"),
        ("else", "Runs when none of the conditions above were True"),
        ("and", "True only when both sides are True"),
        ("or", "True when at least one side is True"),
        ("not", "Flips True to False and False to True"),
    ]
    chosen = rng.sample(pairs, 5)
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each keyword to what it does.",
        pairs=chosen,
        explanation="`if` / `elif` / `else` build the decision; `and`, `or` and `not` combine or flip conditions.",
        rng=rng,
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_condition_truth(rng: random.Random) -> Question:
    """Condition -> True / False for the given values."""
    temperature = rng.choice([72, 65, 80, 70, 58])
    is_raining = rng.choice([True, False])
    pool = [
        "temperature > 70",
        "temperature >= 70",
        "temperature < 70",
        f"temperature == {temperature}",
        f"temperature != {temperature}",
        "is_raining",
        "not is_raining",
        "temperature > 70 and is_raining",
        "temperature > 70 and not is_raining",
        "temperature > 70 or is_raining",
        "temperature < 70 or not is_raining",
    ]
    for _ in range(50):
        items = rng.sample(pool, 5)
        pairs = [(c, str(bool(_truth(c, temperature=temperature, is_raining=is_raining)))) for c in items]
        if len({a for _, a in pairs}) == 2:
            break
    else:
        raise GenerationError("need both True and False")
    code = f"temperature = {temperature}\nis_raining = {is_raining}"
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each condition to its value (True or False).",
        pairs=pairs,
        explanation="Comparisons give True or False; `and` needs both sides True, `or` needs at least one, and `not` flips the value.",
        rng=rng,
        code=code,
    )


_BUGGY = {
    "Uses = instead of ==": ["if {v} = {n}:", "elif {v} = {n}:"],
    "Missing the colon": ["if {v} >= {n}", "elif {v} >= {n}", "if {v} == {n}", "else"],
    "Should be elif": ["else if {v} >= {n}:", "else if {v} == {n}:", "else if {v} < {n}:"],
}
_FINE = ["if {v} >= {n}:", "elif {v} >= {n}:", "else:", "if {v} == {n}:", "elif {v} < {n}:"]


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_bugs(rng: random.Random) -> Question:
    """Broken line -> what is wrong with it (the lesson's common pitfalls)."""
    var, n = rng.choice([("age", 16), ("score", 90), ("money", 5), ("temperature", 70)])
    kinds = list(_BUGGY)
    pairs = [(rng.choice(_BUGGY[k]).format(v=var, n=n), k) for k in kinds]
    for fine in rng.sample(_FINE, len(_FINE)):
        text = fine.format(v=var, n=n)
        if len(pairs) >= 5:
            break
        if text not in [t for t, _ in pairs]:
            pairs.append((text, "Nothing is wrong"))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each line to what is wrong with it.",
        pairs=pairs,
        explanation="Common pitfalls: `=` assigns while `==` compares, `if`/`elif`/`else` lines need a colon, and `else if` is spelled `elif`.",
        rng=rng,
        extra_options=[*_BUGGY, "Nothing is wrong"],
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_scores_to_grades(rng: random.Random) -> Question:
    """Score values -> the grade the lesson's ladder prints."""
    steps = list(_GRADE_STEPS)
    rungs = [(f"score >= {t}", f"Grade: {g}") for t, g in steps]
    ladder = _join(_ladder(rungs, "Grade: F"))
    candidates = [100, 95, 90, 89, 85, 80, 79, 75, 70, 69, 65, 60, 59, 40, 0]
    for _ in range(50):
        scores = rng.sample(candidates, 5)
        pairs = [(f"score = {sc}", _ran(f"score = {sc}\n{ladder}")) for sc in scores]
        if len({a for _, a in pairs}) >= 3:
            break
    else:
        raise GenerationError("too few different grades")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each score to the grade this ladder prints.",
        pairs=pairs,
        explanation="Python checks from the top and stops at the first True condition, and `>=` includes the threshold itself (90 is an A).",
        rng=rng,
        code=ladder,
        extra_options=[f"Grade: {g}" for g in "ABCDF"],
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_money_outputs(rng: random.Random) -> Question:
    """Money values -> what the nested snack / drink code prints."""
    t1, t2 = rng.choice([(5, 8), (5, 8), (4, 6), (10, 15)])
    code = _join(
        [
            f"if money >= {t1}:",
            '    print("You can buy a snack.")',
            f"    if money >= {t2}:",
            '        print("You can also buy a drink.")',
            "else:",
            '    print("Not enough money.")',
        ]
    )
    label = {
        "You can buy a snack.": "Only the snack line",
        "You can buy a snack.\nYou can also buy a drink.": "The snack line and the drink line",
        "Not enough money.": "Not enough money.",
    }
    values = [rng.randint(0, t1 - 1), rng.randint(t1, t2 - 1), rng.randint(t2, t2 + 6)]
    values += rng.sample([t1, t1 - 1, t2, t2 - 1, t2 + 3, 0], 3)
    seen: list[int] = []
    for v in values:
        if v not in seen and len(seen) < 5:
            seen.append(v)
    pairs = [(f"money = {v}", label[_ran(f"money = {v}\n{code}")]) for v in seen]
    if len({a for _, a in pairs}) < 2:
        raise GenerationError("too few different outputs")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each value of `money` to what the code prints.",
        pairs=pairs,
        explanation=f"The outer check is `money >= {t1}`; only inside it does Python check `money >= {t2}` for the drink.",
        rng=rng,
        code=code,
        extra_options=list(label.values()),
    )


@generator(TOPIC, HARD, qtype="match")
def gen_match_swapped_ladder(rng: random.Random) -> Question:
    """A ladder with two checks swapped: score -> what it really prints."""
    steps = list(_GRADE_STEPS)
    i = rng.randrange(3)
    order = list(steps)
    order[i], order[i + 1] = order[i + 1], order[i]
    rungs = [(f"score >= {t}", f"Grade: {g}") for t, g in order]
    ladder = _join(_ladder(rungs, "Grade: F"))
    lo, hi = steps[i + 1][0], steps[i][0]
    pool = [100, 95, hi + 4, hi, hi - 1, lo, lo - 1, lo - 5, 50, 0, 85, 75, 65]
    unique = list(dict.fromkeys(pool))
    for _ in range(50):
        affected = hi + rng.choice([0, 3, 6])  # these scores are caught by the lower check too early
        scores = [affected, *rng.sample([s for s in unique if s != affected], 4)]
        pairs = [(f"score = {sc}", _ran(f"score = {sc}\n{ladder}")) for sc in scores]
        if len({a for _, a in pairs}) >= 3:
            break
    else:
        raise GenerationError("too few different grades")
    rng.shuffle(pairs)
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Two checks in this ladder are in the wrong order. Match each score to the grade that really prints.",
        pairs=pairs,
        explanation="Python stops at the first True condition. The lower check sitting above a higher one catches scores before the higher one is reached.",
        rng=rng,
        code=ladder,
        extra_options=[f"Grade: {g}" for g in "ABCDF"],
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_symbols(rng: random.Random) -> Question:
    """Symbol -> what it does in a conditional."""
    pairs = [
        ("==", "Checks if two values are equal"),
        ("=", "Stores a value in a variable"),
        ("!=", "Checks if two values are NOT equal"),
        (">=", "Greater than or equal to"),
        (":", "Ends an if / elif / else line"),
        ("%", "Gives the remainder after dividing"),
    ]
    chosen = rng.sample(pairs, 5)
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each symbol to what it does.",
        pairs=chosen,
        explanation="`=` assigns while `==` compares, `!=` means not equal, `>=` includes the limit itself, `%` is the remainder, and a colon ends every `if` / `elif` / `else` line.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_park_outputs(rng: random.Random) -> Question:
    """Situations -> what the park code prints."""
    code = _join(
        [
            "if temperature > 70 and not is_raining:",
            '    print("Great day to go to the park!")',
            "elif temperature > 70 and is_raining:",
            '    print("Stay inside.")',
            "else:",
            '    print("Might be too cold.")',
        ]
    )
    label = {
        "Great day to go to the park!": "Great day to go to the park!",
        "Stay inside.": "Stay inside.",
        "Might be too cold.": "Might be too cold.",
    }
    for _ in range(50):
        pool = [(t, w) for t in (72, 85, 70, 65, 58, 71) for w in (True, False)]
        chosen = rng.sample(pool, 5)
        pairs = [(f"temperature = {t}, is_raining = {w}", label[_ran(f"temperature = {t}\nis_raining = {w}\n{code}")]) for t, w in chosen]
        if len({a for _, a in pairs}) >= 3:
            break
    else:
        raise GenerationError("too few different outputs")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each situation to what this code prints.",
        pairs=pairs,
        explanation="It is only a park day when the temperature is ABOVE 70 (70 itself is not) and it is not raining. Warm and raining gives `Stay inside.`; everything else falls to the `else`.",
        rng=rng,
        code=code,
        extra_options=list(label.values()),
    )


# ==========================================================================
# CODE - typed Python, graded in the sandbox
# ==========================================================================


def _code_q(difficulty: int, prompt: str, task, explanation: str, code: str | None = None) -> Question:
    return code_question(topic=TOPIC, difficulty=difficulty, prompt=prompt, task=task, explanation=explanation, code=code)


def _prog(
    solution: str,
    cases: list[Case],
    *,
    starter: str = "",
    examples: int = 2,
    requires: list[tuple[str, str]] | None = None,
    forbids: list[tuple[str, str]] | None = None,
) -> object:
    return program_task(
        solution, cases, starter=starter, examples=examples, requires=requires or [], forbids=forbids or []
    )


def _grade_ranges(steps: list[tuple[int, str]], top: int = 100) -> str:
    """'`Grade: A` for 90 or more, `Grade: B` for 80 to 89, ...' (without the final F)."""
    parts = []
    for i, (t, g) in enumerate(steps):
        parts.append(f"`Grade: {g}` for {t} or more" if i == 0 else f"`Grade: {g}` for {t} to {steps[i - 1][0] - 1}")
    return ", ".join(parts)


def _preset_starter(*names: str) -> str:
    listed = " and ".join(names)
    return f"# {listed} {'is' if len(names) == 1 else 'are'} already set for you - just use {'it' if len(names) == 1 else 'them'}\n"


def _examples_first(pairs: list[tuple[object, object]]) -> list[tuple[object, object]]:
    """Put one True-ish and one False-ish case first so the visible examples teach both outcomes."""
    seen: dict[object, tuple[object, object]] = {}
    for pair in pairs:
        seen.setdefault(repr(pair[1]), pair)
    firsts = list(seen.values())[:2]
    rest = [p for p in pairs if p not in firsts]
    return firsts + rest


# ---- EASY: expressions -----------------------------------------------------------

_COND_STORIES = [
    ("age", ">=", 16, "16 or older"),
    ("age", ">=", 16, "old enough for a driver's license (16 or older)"),
    ("age", ">=", 18, "18 or older"),
    ("age", "<", 13, "under 13"),
    ("score", ">=", 60, "at least 60 (a passing score)"),
    ("score", ">", 90, "above 90"),
    ("temperature", ">", 70, "above 70"),
    ("temperature", "<=", 32, "32 or below"),
    ("money", ">=", 5, "at least 5"),
    ("points", "<", 100, "less than 100"),
    ("answer", "==", 5, "exactly 5"),
    ("count", "!=", 0, "anything except 0"),
    ("height", ">=", 48, "48 or more (tall enough to ride)"),
    ("coins", ">", 10, "more than 10"),
    ("level", ">=", 5, "5 or higher"),
    ("lives", "==", 0, "exactly 0"),
    ("speed", "<=", 25, "25 or less"),
    ("score", "<", 60, "below 60 (not passing)"),
]


def condition_expr_question(var: str, op: str, limit: int, english: str) -> Question:
    values = [limit + 4, limit - 4, limit, limit - 1, limit + 1, limit + 9]
    values = [v for v in dict.fromkeys(values) if v >= 0]
    pairs = [(v, bool(_CMP[op](v, limit))) for v in values]
    pairs = _examples_first(pairs)
    task = expression_task(f"{var} {op} {limit}", [({var: v}, r) for v, r in pairs], examples=2)
    return _code_q(
        EASY,
        f"`{var}` already holds a whole number. Type a condition that is `True` when {var} is {english}.",
        task,
        f"`{var} {op} {limit}` is True exactly when {var} is {english}"
        + (f"; `{op}` includes {limit} itself." if op in (">=", "<=") else "."),
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_condition_expr(rng: random.Random) -> Question:
    var, op, limit, english = rng.choice(_COND_STORIES)
    return condition_expr_question(var, op, limit, english)


def parity_expr_question(var: str, what: str, k: int, want: int) -> Question:
    values = [0, 1, 2, 3, 7, 8, 12, 15, 20, 25, 30, 33]
    pairs = [(v, v % k == want) for v in values]
    pairs = _examples_first(pairs)
    task = expression_task(f"{var} % {k} == {want}", [({var: v}, r) for v, r in pairs], examples=2)
    return _code_q(
        EASY,
        f"`{var}` already holds a whole number. Type a condition that is `True` when {var} is {what}.",
        task,
        f"`{var} % {k}` is the remainder after dividing by {k}, so `{var} % {k} == {want}` is True when {var} is {what}.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_even_odd_expr(rng: random.Random) -> Question:
    var = rng.choice(["number", "n", "num"])
    what, k, want = rng.choice(
        [
            ("even", 2, 0),
            ("even", 2, 0),
            ("odd", 2, 1),
            ("a multiple of 3", 3, 0),
            ("a multiple of 4", 4, 0),
            ("a multiple of 5", 5, 0),
            ("a multiple of 10", 10, 0),
        ]
    )
    return parity_expr_question(var, what, k, want)


_RANGE_STORIES = [
    ("age", 13, 19, "a teenager"),
    ("number", 1, 100, "in range"),
    ("score", 60, 69, "a D"),
    ("temperature", 60, 80, "comfortable"),
    ("number", 1, 10, "a valid choice"),
    ("score", 70, 79, "a C"),
    ("age", 5, 12, "a kid"),
    ("money", 5, 10, "in your budget"),
    ("number", 10, 99, "a two-digit number"),
    ("points", 100, 199, "a silver player"),
    ("temperature", 32, 50, "chilly"),
]


def range_expr_question(var: str, lo: int, hi: int, label: str) -> Question:
    mid = (lo + hi) // 2
    values = [mid, hi + 1, lo, hi, lo - 1, lo + 1, hi - 1, hi + 20]
    values = [v for v in dict.fromkeys(values) if v >= 0]
    pairs = [(v, lo <= v <= hi) for v in values]
    task = expression_task(f"{lo} <= {var} <= {hi}", [({var: v}, r) for v, r in pairs], examples=2)
    return _code_q(
        EASY,
        f"`{var}` holds a whole number. Type one condition that is `True` when {var} is between {lo} and {hi}, including both {lo} and {hi} ({label}).",
        task,
        f"A chained comparison does it: `{lo} <= {var} <= {hi}` (or `{var} >= {lo} and {var} <= {hi}`). Both ends count, so use `<=`, not `<`.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_range_expr(rng: random.Random) -> Question:
    var, lo, hi, label = rng.choice(_RANGE_STORIES)
    return range_expr_question(var, lo, hi, label)


# ---- EASY: tiny programs ----------------------------------------------------------

_DRIVE_STORIES = [
    ("age", 16, "Can drive", "Too young"),
    ("age", 16, "Can drive", "Too young"),
    ("age", 18, "Can vote", "Too young"),
    ("age", 13, "Can join", "Too young"),
    ("age", 21, "Can enter", "Too young"),
    ("score", 60, "Pass", "Fail"),
    ("grade", 70, "Pass", "Fail"),
    ("money", 5, "Buy it", "Too expensive"),
    ("temperature", 70, "Warm", "Cold"),
    ("points", 100, "Level up", "Keep going"),
    ("height", 48, "Can ride", "Too short"),
    ("coins", 25, "Open the chest", "Need more coins"),
]


def driving_age_question(var: str, limit: int, yes: str, no: str) -> Question:
    values = [limit + 4, limit - 4, limit, limit - 1, limit + 1, 0]
    pairs = [(v, yes if v >= limit else no) for v in dict.fromkeys(values) if v >= 0]
    pairs = _examples_first(pairs)
    cases = [Case(vars={var: v}, out=out) for v, out in pairs]
    solution = _join(_if_else(f"{var} >= {limit}", yes, no))
    task = _prog(solution, cases, starter=_preset_starter(var))
    return _code_q(
        EASY,
        f"The variable `{var}` already exists. Print exactly `{yes}` if `{var}` is {limit} or more, otherwise print exactly `{no}`.",
        task,
        f"Use `if {var} >= {limit}:` for the first message and `else:` for everything else. `>=` makes {limit} itself count.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_driving_age(rng: random.Random) -> Question:
    """Mini-Challenge: Driving Age."""
    var, limit, yes, no = rng.choice(_DRIVE_STORIES)
    return driving_age_question(var, limit, yes, no)


_ONLY_IF_STORIES = [
    ("number", "number > 0", "Positive", "positive (greater than 0)", [5, -3, 0, 12, -100, 1]),
    ("number", "number % 2 == 0", "Even", "even", [4, 7, 0, 13, 22, 9]),
    ("number", "number < 0", "Negative", "negative (less than 0)", [-5, 3, 0, -12, 100, -1]),
    ("number", "number % 2 == 1", "Odd", "odd", [4, 7, 0, 13, 22, 9]),
    ("temperature", "temperature < 32", "Freezing", "below 32", [20, 50, 32, 31, 90, 0]),
    ("score", "score == 100", "Perfect score!", "exactly 100", [100, 99, 50, 0, 101, 75]),
    ("age", "age >= 65", "Senior discount", "65 or older", [70, 30, 65, 64, 90, 16]),
    ("money", "money > 0", "You have money", "more than 0", [5, 0, 12, 1, 100, 0]),
    ("lives", "lives == 0", "Game over", "exactly 0", [0, 3, 1, 2, 5, 10]),
    ("points", "points >= 1000", "New high score!", "1000 or more", [1500, 999, 1000, 20, 0, 4000]),
]


def only_if_question(var: str, cond: str, msg: str, english: str, values: list[int]) -> Question:
    pairs = [(v, msg if _truth(cond, **{var: v}) else "") for v in dict.fromkeys(values)]
    pairs = _examples_first(pairs)
    cases = [Case(vars={var: v}, out=out) for v, out in pairs]
    task = _prog(_join([f"if {cond}:", f"    {_say(msg)}"]), cases, starter=_preset_starter(var))
    return _code_q(
        EASY,
        f"The variable `{var}` already exists. If {var} is {english}, print exactly `{msg}`. Otherwise print nothing.",
        task,
        f"One `if` is enough: `if {cond}:` with the `print` indented underneath. With no `else`, nothing happens when the condition is False.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_if_only(rng: random.Random) -> Question:
    var, cond, msg, english, values = rng.choice(_ONLY_IF_STORIES)
    return only_if_question(var, cond, msg, english, rng.sample(values, len(values)))


# ---- MEDIUM ------------------------------------------------------------------------


def combined_expr_question(var: str, op: str, v: int, flag: str, conn: str, negated: bool, sentence: str) -> Question:
    fl = f"not {flag}" if negated else flag
    solution = f"{var} {op} {v} {conn} {fl}"
    low = max(0, v - 6)
    combos = [(v + 6, True), (low, False), (v + 6, False), (low, True), (v, True), (v, False), (v + 1, False), (v + 1, True), (v - 1, False), (v - 1, True)]
    pairs = [({var: n, flag: f}, bool(_truth(solution, **{var: n, flag: f}))) for n, f in combos]
    # the two visible examples should show a True and a False result
    first_true = next(p for p in pairs if p[1])
    first_false = next(p for p in pairs if not p[1])
    pairs = [first_true, first_false] + [p for p in pairs if p is not first_true and p is not first_false]
    task = expression_task(solution, pairs, examples=2)
    return _code_q(
        MEDIUM,
        f"`{var}` holds a whole number and `{flag}` holds `True` or `False`. Type one condition that is `True` when {sentence}.",
        task,
        f"Join the two parts with `{conn}`: `{var} {op} {v}` for the number" + (f" and `not {flag}` for the flag." if negated else f" and `{flag}` for the flag."),
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_combined_expr(rng: random.Random) -> Question:
    var, op, (lo, hi), english = rng.choice(_NUM_ATOMS)
    flag, pos, neg = rng.choice(_FLAG_ATOMS)
    v = rng.randint(lo, hi)
    conn = rng.choice(["and", "and", "or"])
    negated = rng.random() < 0.5
    sentence = f"{english.format(v=v)}{', ' if conn == 'or' else ' '}{conn} {neg if negated else pos}"
    return combined_expr_question(var, op, v, flag, conn, negated, sentence)


_SIGN_STORIES = [
    ("number", "Enter a number: ", ("Positive", "Negative", "Zero"), "a number"),
    ("number", "Enter a number: ", ("Positive", "Negative", "Zero"), "a number"),
    ("number", "Enter a number: ", ("Positive", "Negative", "Zero"), "a number"),
    ("change", "Points change: ", ("Gain", "Loss", "No change"), "how many points the player gained or lost"),
    ("balance", "Balance: ", ("In the black", "In the red", "Broke even"), "an account balance"),
]


def sign_checker_question(var: str, ask: str, words: tuple[str, str, str], what: str, values: list[int]) -> Question:
    pos, neg, zero = words
    solution = _join(
        [f'{var} = int(input("{ask}"))', *_ladder([(f"{var} > 0", pos), (f"{var} < 0", neg)], zero)]
    )
    cases = [Case(stdin=[str(v)], out=pos if v > 0 else neg if v < 0 else zero) for v in values]
    task = _prog(solution, cases, starter=f'{var} = int(input("{ask}"))\n')
    return _code_q(
        MEDIUM,
        f"Sign Checker: write a program that asks for {what} with `input()`, casts it to `int`, and prints exactly `{pos}` if it is above 0, `{neg}` if it is below 0, or `{zero}` if it is 0.",
        task,
        f"Cast first with `int(...)`, then use `if {var} > 0:`, `elif {var} < 0:` and `else:` for zero. Only one branch runs.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_sign_checker(rng: random.Random) -> Question:
    """Mini-Challenge: Sign Checker."""
    var, ask, words, what = rng.choice(_SIGN_STORIES)
    values = [rng.choice([5, 8, 21, 47]), rng.choice([-3, -9, -20]), 0, 1, -1, rng.choice([100, -100, 12])]
    return sign_checker_question(var, ask, words, what, values)


_RANK_STORIES = [
    ("score", "Enter your score: ", ("Bronze", "Silver", "Gold"), (1000, 2000)),
    ("score", "Enter your score: ", ("Bronze", "Silver", "Gold"), (1000, 2000)),
    ("score", "What is your score? ", ("Bronze", "Silver", "Gold"), (500, 1500)),
    ("score", "Enter your score: ", ("Rookie", "Pro", "Master"), (100, 300)),
    ("eliminations", "How many eliminations? ", ("Rookie", "Veteran", "Legend"), (10, 25)),
    ("coins", "How many coins? ", ("Copper", "Silver", "Gold"), (50, 100)),
    ("wins", "How many wins? ", ("Beginner", "Expert", "Champion"), (5, 20)),
    ("points", "Enter your points: ", ("Green", "Blue", "Red"), (250, 750)),
    ("matches", "How many matches did you play? ", ("Newbie", "Regular", "Veteran"), (10, 50)),
    ("level", "What level are you? ", ("Novice", "Skilled", "Elite"), (5, 15)),
    ("streak", "What is your streak? ", ("Spark", "Flame", "Inferno"), (3, 7)),
    ("stars", "How many stars? ", ("Tin", "Silver", "Gold"), (10, 20)),
]


def rank_checker_question(var: str, ask: str, ranks: tuple[str, str, str], limits: tuple[int, int]) -> Question:
    r0, r1, r2 = ranks
    t1, t2 = limits
    solution = _join(
        [
            f'{var} = int(input("{ask}"))',
            f"if {var} >= {t2}:",
            f'    print("You earned {r2} rank!")',
            f"elif {var} >= {t1}:",
            f'    print("You earned {r1} rank!")',
            "else:",
            f'    print("You earned {r0} rank!")',
        ]
    )
    values = [(t1 + t2) // 2, t2 + t1 // 2, 0, t1, t1 - 1, t2, t2 - 1, t2 + 3 * t1]
    cases = [Case(stdin=[str(v)], out=f"You earned {r2 if v >= t2 else r1 if v >= t1 else r0} rank!") for v in values]
    task = _prog(solution, cases, starter=f'{var} = int(input("{ask}"))\n')
    return _code_q(
        MEDIUM,
        f"Rank Checker: write a program that asks for the player's {var} (an `int`) and prints exactly `You earned {r0} rank!` for less than {t1}, "
        f"`You earned {r1} rank!` for {t1} to {t2 - 1}, or `You earned {r2} rank!` for {t2} or more.",
        task,
        f"Cast the input with `int()`, then use an `if / elif / else` ladder with the highest limit first: `{var} >= {t2}`, then `{var} >= {t1}`, then `else`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_rank_checker(rng: random.Random) -> Question:
    """Programming Assessment, Challenge 1: Rank Checker."""
    var, ask, ranks, limits = rng.choice(_RANK_STORIES)
    return rank_checker_question(var, ask, ranks, limits)


def grade_ladder_question(var: str, steps: list[tuple[int, str]], values: list[int]) -> Question:
    rungs = [(f"{var} >= {t}", f"Grade: {g}") for t, g in steps]
    solution = _join(_ladder(rungs, "Grade: F"))

    def grade(v: int) -> str:
        for t, g in steps:
            if v >= t:
                return g
        return "F"

    pairs = _examples_first([(v, f"Grade: {grade(v)}") for v in values])
    cases = [Case(vars={var: v}, out=out) for v, out in pairs]
    task = _prog(solution, cases, starter=_preset_starter(var))
    return _code_q(
        MEDIUM,
        f"The variable `{var}` already exists. Use an `if / elif / else` ladder to print exactly {_grade_ranges(steps)}, and `Grade: F` for anything lower.",
        task,
        f"Check the highest limit first and use `>=` so the limit itself counts ({steps[0][0]} is an {steps[0][1]}). Only the first True branch runs.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_grade_ladder(rng: random.Random) -> Question:
    """Lesson section 2: the elif grade ladder."""
    var = rng.choice(["score", "score", "percent", "points"])
    steps = rng.choice(
        [
            [(90, "A"), (80, "B"), (70, "C"), (60, "D")],
            [(90, "A"), (80, "B"), (70, "C"), (60, "D")],
            [(90, "A"), (80, "B"), (70, "C")],
            [(90, "A"), (75, "B"), (60, "C")],
            [(85, "A"), (70, "B"), (55, "C")],
        ]
    )
    values = [
        rng.randint(steps[0][0] + 1, 100),
        rng.randint(steps[1][0] + 1, steps[0][0] - 2),
        rng.randint(steps[2][0] + 1, steps[1][0] - 2),
        rng.randint(max(1, steps[-1][0] - 25), steps[-1][0] - 2),
        *[t for t, _ in steps],
        *[t - 1 for t, _ in steps],
    ]
    return grade_ladder_question(var, steps, list(dict.fromkeys(values)))


_PARK_STORIES = [
    # (threshold, message when warm and dry, message when warm and wet, message otherwise)
    (70, "Great day to go to the park!", "Stay inside.", "Might be too cold."),
    (70, "Great day to go to the park!", "Stay inside.", "Might be too cold."),
    (75, "Great day to go to the park!", "Stay inside.", "Might be too cold."),
    (80, "Great day to go to the park!", "Stay inside.", "Might be too cold."),
    (60, "Great day to go to the park!", "Stay inside.", "Might be too cold."),
    (85, "Time to go swimming!", "Stay inside.", "Too cold to swim."),
    (65, "Let's play outside!", "Stay inside.", "Wear a jacket."),
    (75, "Perfect for a picnic!", "Eat inside.", "Skip the picnic."),
    (72, "Go for a bike ride!", "Stay inside.", "Maybe tomorrow."),
    (68, "Walk the dog!", "Stay inside.", "Too chilly for a walk."),
    (78, "Fire up the grill!", "Cook inside.", "Skip the grill."),
    (55, "Go for a jog!", "Use the treadmill.", "Too cold to jog."),
]


def park_question(t: int, park: str, rain: str, cold: str) -> Question:
    solution = _join(
        [
            *_ladder(
                [(f"temperature > {t} and not is_raining", park), (f"temperature > {t} and is_raining", rain)],
                cold,
            )
        ]
    )

    def out(temp: int, wet: bool) -> str:
        return park if temp > t and not wet else rain if temp > t else cold

    combos = [(t + 2, False), (t + 12, True), (t, False), (t, True), (t - 20, False), (t - 20, True), (t + 1, True), (t + 1, False), (t + 25, False)]
    cases = [Case(vars={"temperature": temp, "is_raining": wet}, out=out(temp, wet)) for temp, wet in combos]
    task = _prog(solution, cases, starter=_preset_starter("temperature", "is_raining"))
    return _code_q(
        MEDIUM,
        f"`temperature` (a number) and `is_raining` (`True` or `False`) already exist. Print exactly `{park}` if it is above {t} and not raining, "
        f"`{rain}` if it is above {t} and raining, and `{cold}` otherwise.",
        task,
        f"Combine the checks with `and` / `not`: `temperature > {t} and not is_raining`, then `temperature > {t} and is_raining`, then `else`. {t} itself is not above {t}.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_park_decision(rng: random.Random) -> Question:
    """Lesson section 3: temperature and is_raining combined."""
    return park_question(*rng.choice(_PARK_STORIES))


_SNACK_STORIES = [
    (5, 8, "snack", "drink"),
    (5, 8, "snack", "drink"),
    (4, 6, "snack", "drink"),
    (10, 15, "ticket", "popcorn"),
    (3, 7, "pencil", "notebook"),
    (6, 10, "burger", "shake"),
    (2, 5, "sticker", "toy"),
    (20, 35, "game", "controller"),
    (12, 20, "hat", "jacket"),
    (7, 12, "taco", "soda"),
    (15, 25, "poster", "frame"),
    (8, 14, "cookie", "milkshake"),
]


def nested_snack_question(t1: int, t2: int, item1: str, item2: str) -> Question:
    m1, m2, m0 = f"You can buy a {item1}.", f"You can also buy a {item2}.", "Not enough money."
    solution = _join(
        [
            'money = int(input("How much money do you have? "))',
            f"if money >= {t1}:",
            f"    {_say(m1)}",
            f"    if money >= {t2}:",
            f"        {_say(m2)}",
            "else:",
            f"    {_say(m0)}",
        ]
    )

    def out(m: int) -> str:
        return m0 if m < t1 else m1 if m < t2 else f"{m1}\n{m2}"

    values = [t2 + 2, t1 + 0, 0, t2, t2 - 1, t1 - 1, t2 + 20]
    cases = [Case(stdin=[str(m)], out=out(m)) for m in dict.fromkeys(values)]
    task = _prog(solution, cases, starter='money = int(input("How much money do you have? "))\n')
    return _code_q(
        MEDIUM,
        f"Write a program that asks for `money` (an `int`). If money is at least {t1}, print `{m1}`, and if it is also at least {t2}, print `{m2}` on the next line. "
        f"If money is less than {t1}, print only {_stop(m0)}",
        task,
        f"Nest a second `if money >= {t2}:` inside the first one, because the {item2} check only makes sense after the {item1} check passed.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_nested_snack(rng: random.Random) -> Question:
    """Lesson section 4: nested conditionals (money / snack / drink)."""
    return nested_snack_question(*rng.choice(_SNACK_STORIES))


def larger_question(a: str, b: str, pairs: list[tuple[int, int]]) -> Question:
    solution = _join(
        [
            f'print("{a} =", {a}, "{b} =", {b})',
            f"if {a} > {b}:",
            f'    print("{a} is larger")',
            "else:",
            f'    print("{b} is larger")',
        ]
    )
    cases = [
        Case(vars={a: x, b: y}, out=f"{a} = {x} {b} = {y}\n" + (f"{a} is larger" if x > y else f"{b} is larger"))
        for x, y in pairs
    ]
    task = _prog(solution, cases, starter=_preset_starter(a, b))
    return _code_q(
        MEDIUM,
        f"Quick Debug Trick: `{a}` and `{b}` already hold numbers. First print their values like `{a} = 3 {b} = 7` (a sanity check), then print `{a} is larger` if `{a}` is bigger, otherwise `{b} is larger`.",
        task,
        f'`print("{a} =", {a}, "{b} =", {b})` puts a space between the pieces. Then `if {a} > {b}:` / `else:` picks the message; when they are equal the `else` runs.',
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_larger_of_two(rng: random.Random) -> Question:
    """Lesson 'Quick Debug Trick' as a program."""
    a, b = rng.choice([("x", "y"), ("x", "y"), ("x", "y"), ("a", "b")])
    pairs = [(rng.randint(1, 9), rng.randint(10, 20)), (rng.randint(10, 20), rng.randint(1, 9)), (rng.randint(3, 8),) * 2,
             (0, -2), (rng.randint(-9, -1), rng.randint(1, 9)), (-3, -3)]
    return larger_question(a, b, pairs)


_GROUP_STORIES = [
    ("age", "Enter your age: ", ("Child", "Teen", "Adult"), 13, 19, "an age"),
    ("age", "Enter your age: ", ("Child", "Teen", "Adult"), 13, 19, "an age"),
    ("temperature", "Temperature: ", ("Cold", "Mild", "Hot"), 50, 80, "a temperature"),
    ("score", "Enter your score: ", ("Low", "Medium", "High"), 40, 70, "a score"),
    ("height", "Height in inches: ", ("Short", "Average", "Tall"), 60, 72, "a height in inches"),
    ("speed", "Speed: ", ("Slow", "Normal", "Fast"), 30, 60, "a speed"),
    ("points", "Points: ", ("Beginner", "Intermediate", "Expert"), 100, 500, "a number of points"),
    ("minutes", "Minutes played: ", ("Short", "Medium", "Long"), 10, 30, "the minutes played"),
    ("age", "Enter your age: ", ("Kid", "Adult", "Senior"), 12, 64, "an age"),
    ("temperature", "Temperature: ", ("Freezing", "Cool", "Warm"), 32, 60, "a temperature"),
    ("wins", "How many wins? ", ("Few", "Some", "Many"), 3, 10, "the number of wins"),
    ("score", "Enter your score: ", ("Try again", "Nice job", "Amazing"), 50, 90, "a score"),
]


def three_way_question(var: str, ask: str, words: tuple[str, str, str], lo: int, hi: int, what: str) -> Question:
    below, inside, above = words
    solution = _join(
        [
            f'{var} = int(input("{ask}"))',
            f"if {var} < {lo}:",
            f"    {_say(below)}",
            f"elif {var} <= {hi}:",
            f"    {_say(inside)}",
            "else:",
            f"    {_say(above)}",
        ]
    )

    def out(v: int) -> str:
        return below if v < lo else inside if v <= hi else above

    values = [(lo + hi) // 2, lo - 8, hi + 10, lo, lo - 1, hi, hi + 1, 0]
    cases = [Case(stdin=[str(v)], out=out(v)) for v in dict.fromkeys(values) if v >= 0]
    task = _prog(solution, _reorder_cases(cases), starter=f'{var} = int(input("{ask}"))\n')
    return _code_q(
        MEDIUM,
        f"Write a program that asks for {what} with `input()`, casts it to `int`, and prints exactly `{below}` if it is under {lo}, `{inside}` if it is {lo} to {hi} (inclusive), or `{above}` if it is over {hi}.",
        task,
        f"Check `{var} < {lo}` first, then `{var} <= {hi}`, and let the `else` catch the rest. You could also write the middle test as a chained comparison, `{lo} <= {var} <= {hi}`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_three_way(rng: random.Random) -> Question:
    var, ask, words, lo, hi, what = rng.choice(_GROUP_STORIES)
    return three_way_question(var, ask, words, lo, hi, what)


def even_odd_program_question(var: str, k: int, yes: str, no: str, values: list[int]) -> Question:
    solution = _join([f'{var} = int(input("Enter a number: "))', *_if_else(f"{var} % {k} == 0", yes, no)])
    cases = [Case(stdin=[str(v)], out=yes if v % k == 0 else no) for v in values]
    cases = _reorder_cases(cases)
    task = _prog(solution, cases, starter=f'{var} = int(input("Enter a number: "))\n')
    return _code_q(
        MEDIUM,
        f"Write a program that asks for a whole number with `input()`, casts it to `int`, and prints exactly `{yes}` if it is {'even' if k == 2 else f'a multiple of {k}'}, otherwise `{no}`.",
        task,
        f"`{var} % {k} == 0` is True when there is no remainder after dividing by {k}. Cast with `int()` first, because `input()` gives text.",
    )


def _reorder_cases(cases: list[Case]) -> list[Case]:
    """Put one case per distinct expected output first (so the examples show both outcomes)."""
    firsts, seen = [], set()
    for c in cases:
        if c.out not in seen:
            seen.add(c.out)
            firsts.append(c)
    return firsts[:2] + [c for c in cases if c not in firsts[:2]]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_even_odd_program(rng: random.Random) -> Question:
    """Sign Checker extension idea: even or odd with %."""
    k = rng.choice([2, 2, 2, 3, 5])
    var = rng.choice(["number", "n"])
    if k == 2:
        yes, no = "Even", "Odd"
    else:
        yes, no = f"Multiple of {k}", f"Not a multiple of {k}"
    values = [0, 1, rng.randint(2, 9), rng.randint(10, 40), rng.randint(41, 99), k * 7, k * 7 + 1, 100]
    return even_odd_program_question(var, k, yes, no, list(dict.fromkeys(values)))


def _letter(score: int) -> str:
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"


def _fn_ladder(func: str, param: str, rungs: list[tuple[str, str]], last: str) -> str:
    """def line + an if / elif / else ladder that RETURNS a string."""
    lines = [f"def {func}({param}):"]
    for i, (cond, ret) in enumerate(rungs):
        lines += [f"    {'if' if i == 0 else 'elif'} {cond}:", f"        return {ret!r}".replace("'", '"')]
    lines += ["    else:", f"        return {last!r}".replace("'", '"')]
    return _join(lines)


def _fn_question(func: str, param: str, rungs: list[tuple[str, str]], last: str, values: list, prompt: str, why: str) -> Question:
    solution = _fn_ladder(func, param, rungs, last)
    pairs = []
    for v in dict.fromkeys(values):
        got = next((ret for cond, ret in rungs if _truth(cond, **{param: v})), last)
        pairs.append(((v,), got))
    task = function_task(func, solution, pairs)
    return _code_q(MEDIUM, prompt, task, why)


def function_question(kind: str, rng: random.Random) -> Question:
    if kind == "letter":
        rungs = [("score >= 90", "A"), ("score >= 80", "B"), ("score >= 70", "C"), ("score >= 60", "D")]
        values = [95, 85, 75, 65, 40, 90, 89, 80, 79, 70, 69, 60, 59, 100, 0]
        prompt = 'Write a function `letter_grade(score)` that returns (not prints) `"A"` for 90 or more, `"B"` for 80 to 89, `"C"` for 70 to 79, `"D"` for 60 to 69 and `"F"` for anything lower.'
        why = "Use an `if / elif / else` ladder with the highest limit first and `return` the letter in each branch. `return` hands the value back; `print` would not."
        return _fn_question("letter_grade", "score", rungs, "F", values, prompt, why)
    if kind == "sign":
        rungs = [("number > 0", "Positive"), ("number < 0", "Negative")]
        prompt = 'Write a function `sign_of(number)` that returns (not prints) `"Positive"` if number is above 0, `"Negative"` if it is below 0, and `"Zero"` if it is 0.'
        why = "Check `number > 0`, then `number < 0`, and let the `else` handle zero. Each branch uses `return`."
        return _fn_question("sign_of", "number", rungs, "Zero", [5, -3, 0, 12, -100, 1, -1], prompt, why)
    if kind == "rank":
        var, _ask, (r0, r1, r2), (t1, t2) = rng.choice(_RANK_STORIES)
        func = f"rank_for_{var}" if var != "score" else "rank_for"
        rungs = [(f"{var} >= {t2}", r2), (f"{var} >= {t1}", r1)]
        values = [t2 + t1, (t1 + t2) // 2, t1 // 2, t1, t1 - 1, t2, t2 - 1, 0]
        prompt = f'Write a function `{func}({var})` that returns (not prints) `"{r0}"` for less than {t1}, `"{r1}"` for {t1} to {t2 - 1} and `"{r2}"` for {t2} or more.'
        why = f"Put the highest limit first (`{var} >= {t2}`), then `{var} >= {t1}`, then `else`, and `return` the rank name."
        return _fn_question(func, var, rungs, r0, values, prompt, why)
    if kind == "pass_fail":
        limit = rng.choice([50, 60, 65, 70])
        rungs = [(f"score >= {limit}", "Pass")]
        values = [limit + 20, limit + 1, limit, limit - 1, limit - 30, 100, 0]
        prompt = f'Write a function `pass_or_fail(score)` that returns (not prints) `"Pass"` if score is {limit} or more, otherwise `"Fail"`.'
        why = f"A single `if score >= {limit}:` with an `else:` is enough. Use `return` in both branches."
        return _fn_question("pass_or_fail", "score", rungs, "Fail", values, prompt, why)
    if kind == "parity":
        k, yes, no = rng.choice([(2, "Even", "Odd"), (2, "Even", "Odd"), (3, "Multiple of 3", "Not a multiple of 3"), (5, "Multiple of 5", "Not a multiple of 5")])
        func = "even_or_odd" if k == 2 else f"check_multiple_of_{k}"
        rungs = [(f"number % {k} == 0", yes)]
        prompt = f'Write a function `{func}(number)` that returns (not prints) `"{yes}"` if number is {"even" if k == 2 else f"a multiple of {k}"}, otherwise `"{no}"`.'
        why = f"`number % {k} == 0` is True when there is no remainder after dividing by {k}. `return` the text in each branch."
        return _fn_question(func, "number", rungs, no, [0, 1, 2, 3, 4, 5, 9, 10, 15, 21, 30, 37], prompt, why)
    if kind == "ticket":
        lo, hi, p_kid, p_adult, p_senior = rng.choice([(13, 65, 5, 10, 7), (12, 60, 4, 9, 6), (13, 65, 8, 12, 9)])
        func = "ticket_price"
        solution = _join(
            [
                f"def {func}(age):",
                f"    if age < {lo}:",
                f"        return {p_kid}",
                f"    elif age < {hi}:",
                f"        return {p_adult}",
                "    else:",
                f"        return {p_senior}",
            ]
        )
        values = [5, lo - 1, lo, 30, hi - 1, hi, 80, 0]
        pairs = [((v,), p_kid if v < lo else p_adult if v < hi else p_senior) for v in values]
        task = function_task(func, solution, pairs)
        prompt = f"Write a function `{func}(age)` that returns (not prints) the price: {p_kid} if age is under {lo}, {p_adult} if age is {lo} to {hi - 1}, and {p_senior} if age is {hi} or more."
        why = f"Check `age < {lo}` first, then `age < {hi}`, and let `else` cover everyone older. `return` the number in each branch."
        return _code_q(MEDIUM, prompt, task, why)
    if kind == "can_enter":
        limit = rng.choice([13, 16, 18])
        solution = _join(
            [
                "def can_enter(age, has_ticket):",
                f"    if age >= {limit} and has_ticket:",
                '        return "Welcome"',
                "    else:",
                '        return "No entry"',
            ]
        )
        combos = [(limit, True), (limit - 1, True), (limit + 5, False), (limit - 1, False), (limit + 20, True), (5, False), (limit, False)]
        pairs = [(c, "Welcome" if c[0] >= limit and c[1] else "No entry") for c in combos]
        task = function_task("can_enter", solution, pairs)
        prompt = f'Write a function `can_enter(age, has_ticket)` that returns (not prints) `"Welcome"` if age is {limit} or more and `has_ticket` is `True`, otherwise `"No entry"`.'
        why = "Join the two checks with `and` so both must be True, then `return` in the `if` and in the `else`."
        return _code_q(MEDIUM, prompt, task, why)
    solution = _join(["def bigger(a, b):", "    if a > b:", "        return a", "    else:", "        return b"])
    pairs = [(3, 7), (9, 2), (5, 5), (-1, -8), (0, 4), (100, 99)]
    task = function_task("bigger", solution, [(p, max(p)) for p in pairs])
    prompt = "Write a function `bigger(a, b)` that returns (not prints) the larger of the two numbers."
    why = "Compare with `if a > b:` and `return` one of them in each branch. When they are equal either one is correct."
    return _code_q(MEDIUM, prompt, task, why)


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_decision_function(rng: random.Random) -> Question:
    """A decision wrapped in a small function that RETURNS the answer."""
    kind = rng.choice(["letter", "sign", "rank", "rank", "pass_fail", "parity", "ticket", "can_enter", "bigger"])
    return function_question(kind, rng)


_EQ_STORIES = [
    ("answer", 5, "Correct!", "Try again."),
    ("guess", 7, "You win!", "Nope."),
    ("count", 10, "Done!", "Keep counting."),
    ("age", 16, "Sweet sixteen!", "Not sixteen."),
    ("lives", 1, "Last life!", "Keep playing"),
    ("number", 50, "Special number", "Not special"),
]

_LADDER3_STORIES = [
    # (variable, upper limit, lower limit, top message, middle message, bottom message)
    ("score", 90, 80, "Grade: A", "Grade: B", "Grade: C"),
    ("age", 18, 13, "Adult", "Teen", "Child"),
    ("temperature", 80, 60, "Hot", "Mild", "Cold"),
    ("money", 10, 5, "Buy both", "Buy one", "Buy nothing"),
    ("points", 1000, 500, "Gold", "Silver", "Bronze"),
    ("speed", 60, 30, "Fast", "Medium", "Slow"),
]


def _bug_lines(bug: str, v: str, n: int, yes: str, no: str) -> tuple[str, str, str]:
    """(starter text, solution text, explanation) for one classic mistake in a two-way if / else."""
    ok_if = f"if {v} >= {n}:"
    yes_line, no_line = f'    print("{yes}")', f'    print("{no}")'
    if bug == "colons":
        broken = [f"if {v} >= {n}", yes_line, "else", no_line]
        fixed = [ok_if, yes_line, "else:", no_line]
        why = "Two colons are missing: every `if` and `else` line must end with `:`."
    elif bug == "equals":
        broken = [f"if {v} = {n}:", yes_line, "else:", no_line]
        fixed = [f"if {v} == {n}:", yes_line, "else:", no_line]
        why = "A single `=` assigns a value. To compare two values (is it exactly equal?) use `==`."
    elif bug == "indent":
        broken = [ok_if, yes_line.strip(), "else:", no_line.strip()]
        fixed = [ok_if, yes_line, "else:", no_line]
        why = "The `print` lines must be indented (4 spaces) under the `if` and the `else`."
    else:  # "else_indent": the else is pushed in so it no longer lines up with its if
        broken = [ok_if, yes_line, "    else:", no_line]
        fixed = [ok_if, yes_line, "else:", no_line]
        why = "`else:` must line up with the `if` it belongs to (no indentation), then its block is indented under it."
    return "\n".join(broken) + "\n", "\n".join(fixed), why


def fix_bugs_question(bug: str, var: str, limit: int, yes: str, no: str) -> Question:
    starter, solution, why = _bug_lines(bug, var, limit, yes, no)
    if bug == "equals":
        values = [limit, limit + 1, limit - 1, limit + 7, 0]
        pairs = [(v, yes if v == limit else no) for v in dict.fromkeys(values) if v >= 0]
        rule = f"when `{var}` is exactly {limit}"
    else:
        values = [limit + 3, limit - 3, limit, limit - 1, limit + 1]
        pairs = _examples_first([(v, yes if v >= limit else no) for v in values if v >= 0])
        rule = f"when `{var}` is {limit} or more"
    cases = [Case(vars={var: v}, out=out) for v, out in pairs]
    task = _prog(solution, cases, starter=starter)
    return _code_q(
        MEDIUM,
        f"Fix the bug! This program should print `{yes}` {rule} and `{no}` otherwise (`{var}` already exists). Edit the code so it runs correctly.",
        task,
        why,
    )


def fix_elseif_question(var: str, hi: int, lo: int, top: str, mid: str, bottom: str) -> Question:
    def text(word: str) -> str:
        return _join(
            [
                f"if {var} >= {hi}:",
                f'    print("{top}")',
                f"{word} {var} >= {lo}:",
                f'    print("{mid}")',
                "else:",
                f'    print("{bottom}")',
            ]
        )

    values = [hi + 5, hi, hi - 1, (hi + lo) // 2, lo, lo - 1, 0]
    pairs = _examples_first([(v, top if v >= hi else mid if v >= lo else bottom) for v in dict.fromkeys(values)])
    # keep three different results among the visible examples when possible
    cases = [Case(vars={var: v}, out=out) for v, out in pairs]
    task = _prog(text("elif"), cases, starter=text("else if") + "\n")
    return _code_q(
        MEDIUM,
        f"Fix the bug! This program should print `{top}` for {hi} or more, `{mid}` for {lo} to {hi - 1}, and `{bottom}` for anything lower (`{var}` already exists). Edit the code so it runs correctly.",
        task,
        "Python's \"else if\" is spelled `elif` - one word.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fix_the_bug(rng: random.Random) -> Question:
    """Common pitfalls as a debugging task: the starter code has the classic mistake."""
    bug = rng.choice(["colons", "equals", "equals", "indent", "elseif", "elseif", "else_indent"])
    if bug == "elseif":
        return fix_elseif_question(*rng.choice(_LADDER3_STORIES))
    if bug == "equals":
        var, limit, yes, no = rng.choice(_EQ_STORIES)
    else:
        var, limit, yes, no = rng.choice(_DRIVE_STORIES)
    return fix_bugs_question(bug, var, limit, yes, no)


# ---- HARD ----------------------------------------------------------------------------


def number_test_question(lo: int, hi: int, special: int) -> Question:
    solution = _join(
        [
            'number = int(input("Enter a number: "))',
            *_ladder([(f"number == {special}", "Special number"), (f"{lo} <= number <= {hi}", "In range")], "Out of range"),
        ]
    )

    def out(n: int) -> str:
        return "Special number" if n == special else "In range" if lo <= n <= hi else "Out of range"

    values = [special, (lo + hi) // 2 + 1 if (lo + hi) // 2 + 1 != special else lo + 2, hi + 5, lo, hi, lo - 1, hi + 1, -7]
    values = [v for v in dict.fromkeys(values)]
    cases = [Case(stdin=[str(v)], out=out(v)) for v in values]
    task = _prog(solution, _reorder_cases(cases), starter="")
    return _code_q(
        HARD,
        f"Number Test: write a program that asks for a whole number with `input()` and prints exactly `Special number` if it is exactly {special}, "
        f"`In range` if it is between {lo} and {hi} (inclusive), or `Out of range` otherwise. ({special} is in range too, but it counts as special.)",
        task,
        f"Check the special number first: `if number == {special}:`. If the range test came first, {special} would print `In range` and the special check could never run.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_number_test(rng: random.Random) -> Question:
    """Mini-Challenge: Number Test (with the order trap)."""
    lo, hi = rng.choice([(1, 100), (1, 100), (1, 10), (10, 99), (1, 50)])
    special = rng.choice([50, 7, 25, 42]) if (lo, hi) == (1, 100) else rng.randint(lo + 2, hi - 2)
    return number_test_question(lo, hi, special)


def rank_diamond_question(var: str, ask: str, ranks: tuple[str, str, str, str], limits: tuple[int, int, int]) -> Question:
    r0, r1, r2, r3 = ranks
    t1, t2, t3 = limits
    solution = _join(
        [
            f'{var} = int(input("{ask}"))',
            *_ladder(
                [(f"{var} >= {t3}", f"You earned {r3} rank!"), (f"{var} >= {t2}", f"You earned {r2} rank!"), (f"{var} >= {t1}", f"You earned {r1} rank!")],
                f"You earned {r0} rank!",
            ),
        ]
    )

    def out(v: int) -> str:
        return f"You earned {r3 if v >= t3 else r2 if v >= t2 else r1 if v >= t1 else r0} rank!"

    values = [t3 + t1 // 2, (t1 + t2) // 2, t2 + t1 // 4, 0, t1, t1 - 1, t2, t2 - 1, t3, t3 - 1]
    cases = [Case(stdin=[str(v)], out=out(v)) for v in dict.fromkeys(values)]
    task = _prog(solution, _reorder_cases(cases), starter="")
    return _code_q(
        HARD,
        f"Rank Checker with the bonus: write a program that asks for the player's {var} (an `int`) and prints exactly `You earned {r0} rank!` for less than {t1}, "
        f"`You earned {r1} rank!` for {t1} to {t2 - 1}, `You earned {r2} rank!` for {t2} to {t3 - 1}, or `You earned {r3} rank!` for {t3} or more.",
        task,
        f"The new {r3} check has to come first (`{var} >= {t3}`). A {var} of {t3} or more is also {t2} or more, so a lower check placed above it would catch it first.",
    )


_DIAMOND_STORIES = [
    ("score", "Enter your score: ", ("Bronze", "Silver", "Gold", "Diamond"), (1000, 2000, 3000)),
    ("score", "Enter your score: ", ("Bronze", "Silver", "Gold", "Diamond"), (1000, 2000, 3000)),
    ("score", "Enter your score: ", ("Bronze", "Silver", "Gold", "Diamond"), (500, 1000, 1500)),
    ("score", "What is your score? ", ("Bronze", "Silver", "Gold", "Platinum"), (800, 1600, 2400)),
    ("coins", "How many coins? ", ("Copper", "Silver", "Gold", "Platinum"), (50, 100, 200)),
    ("eliminations", "How many eliminations? ", ("Rookie", "Veteran", "Elite", "Legend"), (10, 25, 50)),
    ("wins", "How many wins? ", ("Beginner", "Expert", "Master", "Champion"), (5, 10, 20)),
    ("points", "Enter your points: ", ("Green", "Blue", "Red", "Black"), (100, 300, 600)),
    ("stars", "How many stars? ", ("Tin", "Bronze", "Silver", "Gold"), (10, 25, 40)),
    ("level", "What level are you? ", ("Beginner", "Skilled", "Expert", "Master"), (5, 10, 20)),
    ("score", "Enter your score: ", ("Mild", "Spicy", "Hot", "Inferno"), (250, 500, 1000)),
]


@generator(TOPIC, HARD, qtype="code")
def gen_code_rank_diamond(rng: random.Random) -> Question:
    """Programming Assessment bonus: add the Diamond rank (where does the check go?)."""
    var, ask, ranks, limits = rng.choice(_DIAMOND_STORIES)
    return rank_diamond_question(var, ask, ranks, limits)


def grade_validation_question(var: str, bad: str, steps: list[tuple[int, str]]) -> Question:
    rungs = [(f"{var} >= {t}", f"Grade: {g}") for t, g in steps]
    solution = _join(
        [
            f'{var} = int(input("Enter a score from 0 to 100: "))',
            f"if {var} < 0 or {var} > 100:",
            f'    print("{bad}")',
            *[("el" + line if line.startswith("if ") else line) for line in _ladder(rungs, "Grade: F")],
        ]
    )

    def out(v: int) -> str:
        if v < 0 or v > 100:
            return bad
        for t, g in steps:
            if v >= t:
                return f"Grade: {g}"
        return "Grade: F"

    values = [85, 101, -5, 100, 0, *[t for t, _ in steps], *[t - 1 for t, _ in steps], -1, 150, 72]
    cases = [Case(stdin=[str(v)], out=out(v)) for v in dict.fromkeys(values)]
    task = _prog(solution, _reorder_cases(cases), starter="")
    return _code_q(
        HARD,
        f"Write a program that asks for a {var} with `input()` (cast to `int`). If it is below 0 or above 100, print exactly `{bad}`. "
        f"Otherwise print {_grade_ranges(steps)}, and `Grade: F` for anything lower.",
        task,
        f"Check the invalid case first with `or` (`{var} < 0 or {var} > 100`), then use the grade ladder in the `elif` branches. "
        f"If the invalid check came last, a {var} of 150 would already have printed `Grade: A`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_grade_validation(rng: random.Random) -> Question:
    var = rng.choice(["score", "score", "percent"])
    bad = rng.choice(["Invalid", "Invalid score", "Not a valid score", "Out of range"])
    steps = rng.choice(
        [
            [(90, "A"), (80, "B"), (70, "C"), (60, "D")],
            [(90, "A"), (80, "B"), (70, "C"), (60, "D")],
            [(90, "A"), (80, "B"), (70, "C")],
            [(80, "A"), (65, "B"), (50, "C")],
        ]
    )
    return grade_validation_question(var, bad, steps)


def license_nested_question(limit: int, flag_word: str, ok: str, need: str, young: str = "You are too young.") -> Question:
    solution = _join(
        [
            'age = int(input("How old are you? "))',
            f"if age >= {limit}:",
            f'    answer = input("Do you have a {flag_word}? (yes/no) ")',
            '    if answer == "yes":',
            f"        {_say(ok)}",
            "    else:",
            f"        {_say(need)}",
            "else:",
            f"    {_say(young)}",
        ]
    )

    def out(age: int, ans: str) -> str:
        if age < limit:
            return young
        return ok if ans == "yes" else need

    combos = [(limit + 1, "yes"), (limit + 1, "no"), (limit, "yes"), (limit - 1, "yes"), (limit, "no"), (limit + 30, "yes"), (5, "no")]
    # under-age players are never asked the second question, so their case supplies only the age
    cases = [Case(stdin=[str(a), s] if a >= limit else [str(a)], out=out(a, s)) for a, s in combos]
    cases = list({tuple(c.stdin): c for c in cases}.values())
    task = _prog(solution, _reorder_cases(cases), starter="")
    return _code_q(
        HARD,
        f"Write a program that asks for the player's age (an `int`). If the age is {limit} or more, it also asks `Do you have a {flag_word}? (yes/no)` with a second `input()`: "
        f"print exactly `{ok}` if the answer is `yes`, otherwise {_stop(need)} If the age is under {limit}, print exactly `{young}` and do not ask the second question.",
        task,
        f"Nest the second decision inside `if age >= {limit}:`. Only people who pass the age check are asked the second question, so the inner `if answer == \"yes\":` / `else:` lives inside the first block.",
    )


_LICENSE_STORIES = [
    (16, "permit", "You can drive.", "Get your permit first."),
    (16, "permit", "You can drive.", "Get your permit first."),
    (18, "ticket", "Enjoy the show!", "Buy a ticket first."),
    (13, "signed form", "Welcome to camp!", "Bring a form first."),
    (21, "valid ID", "Come on in.", "Show your ID first."),
    (14, "parent note", "Enjoy the trip!", "Bring a note first."),
    (12, "pass", "Have fun!", "Get a pass first."),
    (18, "ballot", "Thanks for voting!", "Pick up a ballot first."),
    (15, "wristband", "Have a great time!", "Get a wristband first."),
    (10, "helmet", "Ride safe!", "Put on a helmet first."),
    (17, "guest list name", "Right this way.", "Check the guest list first."),
]


@generator(TOPIC, HARD, qtype="code")
def gen_code_license_nested(rng: random.Random) -> Question:
    limit, flag_word, ok, need = rng.choice(_LICENSE_STORIES)
    return license_nested_question(limit, flag_word, ok, need)


def sign_extension_question(lo: int, hi: int, style: str) -> Question:
    pos, neg, zero = "Positive", "Negative", "Zero"
    sign = _ladder([("number > 0", pos), ("number < 0", neg)], zero)
    if style == "parity_range":
        extra = [
            "if number % 2 == 0:",
            '    print("Even")',
            "else:",
            '    print("Odd")',
            f"if {lo} <= number <= {hi}:",
            f'    print("Between {lo} and {hi}")',
        ]
    elif style == "range_both":
        extra = [
            f"if {lo} <= number <= {hi}:",
            '    print("In range")',
            "else:",
            '    print("Out of range")',
        ]
    else:  # "range_parity": the range line first, then even / odd
        extra = [
            f"if {lo} <= number <= {hi}:",
            f'    print("Between {lo} and {hi}")',
            "if number % 2 == 0:",
            '    print("Even")',
            "else:",
            '    print("Odd")',
        ]
    solution = _join(['number = int(input("Enter a number: "))', *sign, *extra])

    def out(n: int) -> str:
        lines = [pos if n > 0 else neg if n < 0 else zero]
        inside = lo <= n <= hi
        parity = "Even" if n % 2 == 0 else "Odd"
        if style == "parity_range":
            lines.append(parity)
            if inside:
                lines.append(f"Between {lo} and {hi}")
        elif style == "range_both":
            lines.append("In range" if inside else "Out of range")
        else:
            if inside:
                lines.append(f"Between {lo} and {hi}")
            lines.append(parity)
        return "\n".join(lines)

    values = [lo + 6, 0, 1, -1, -4, hi, hi + 1, -7, lo, lo - 1, 64 if lo <= 64 <= hi else (lo + hi) // 2, hi + 150]
    cases = [Case(stdin=[str(v)], out=out(v)) for v in dict.fromkeys(values)]
    task = _prog(solution, cases, starter="")
    if style == "parity_range":
        lines_text = (
            f"Line 1: `{pos}`, `{neg}` or `{zero}`. Line 2: `Even` or `Odd`. "
            f"Line 3: `Between {lo} and {hi}` only if the number is from {lo} to {hi} inclusive (otherwise no third line)."
        )
        why = f"Use an if / elif / else for the sign, then a separate `if number % 2 == 0:` / `else:` for even or odd, then a third plain `if {lo} <= number <= {hi}:`. They are separate decisions, so they are separate statements."
    elif style == "range_both":
        lines_text = (
            f"Line 1: `{pos}`, `{neg}` or `{zero}`. Line 2: `In range` if the number is from {lo} to {hi} inclusive, otherwise `Out of range`."
        )
        why = f"Use an if / elif / else for the sign, then a second, separate if / else for the range: `if {lo} <= number <= {hi}:` / `else:`. Two decisions, two statements."
    else:
        lines_text = (
            f"Line 1: `{pos}`, `{neg}` or `{zero}`. Line 2: `Between {lo} and {hi}` only if the number is from {lo} to {hi} inclusive (if not, skip this line). "
            "Next line: `Even` or `Odd`."
        )
        why = f"Three separate decisions in a row: the sign ladder, a plain `if {lo} <= number <= {hi}:` with no `else`, and an if / else for even or odd. Each runs on its own."
    return _code_q(
        HARD,
        f"Sign Checker, extended: write a program that asks for a whole number (cast to `int`) and prints these lines in order. {lines_text}",
        task,
        why,
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_sign_extension(rng: random.Random) -> Question:
    """Sign Checker 'extension ideas': even / odd and between 1 and 100."""
    lo, hi = rng.choice([(1, 100), (1, 100), (1, 100), (1, 10), (1, 50), (10, 99), (5, 20)])
    style = rng.choice(["parity_range", "parity_range", "range_both", "range_parity"])
    return sign_extension_question(lo, hi, style)


def _chain(rungs: list[tuple[str, str]], last: str) -> str:
    """if / elif / else lines printing each message, as text."""
    return _join(_ladder(rungs, last))


def fix_order_question(kind: str, rng: random.Random) -> Question:
    if kind == "diamond":
        var, _ask, (r0, r1, r2, r3), (t1, t2, t3) = rng.choice(_DIAMOND_STORIES)
        starter = _chain([(f"{var} >= {t2}", r2), (f"{var} >= {t1}", r1), (f"{var} >= {t3}", r3)], r0)
        solution = _chain([(f"{var} >= {t3}", r3), (f"{var} >= {t2}", r2), (f"{var} >= {t1}", r1)], r0)
        values = [t3 + t1, t3, t3 - 1, t2 + t1 // 2, t2, t2 - 1, (t1 + t2) // 2, t1, t1 - 1, t1 // 2]
        out = lambda v: r3 if v >= t3 else r2 if v >= t2 else r1 if v >= t1 else r0  # noqa: E731
        prompt = (
            f"The Rank Checker below never prints `{r3}`, even when `{var}` is {t3 + t1} (`{var}` already exists). Fix the code so {t3} or more is `{r3}`, "
            f"{t2} to {t3 - 1} is `{r2}`, {t1} to {t2 - 1} is `{r1}` and anything lower is `{r0}`."
        )
        why = f"The `{var} >= {t3}` check is last, so a big {var} is caught by `{var} >= {t2}` first. Move the highest threshold to the top."
    elif kind == "ascending":
        var = rng.choice(["score", "score", "percent"])
        steps = rng.choice([[(90, "A"), (80, "B"), (70, "C"), (60, "D")], [(90, "A"), (80, "B"), (70, "C")], [(90, "A"), (75, "B"), (60, "C")]])
        down = [(f"{var} >= {t}", f"Grade: {g}") for t, g in steps]
        starter = _chain(list(reversed(down)), "Grade: F")
        solution = _chain(down, "Grade: F")
        values = [100, *[t for t, _ in steps], *[t - 1 for t, _ in steps], steps[1][0] + 2, steps[-1][0] + 3, 30]
        out = lambda v: next((f"Grade: {g}" for t, g in steps if v >= t), "Grade: F")  # noqa: E731
        low_t, low_g = steps[-1]
        top_t, top_g = steps[0]
        prompt = (
            f"This grade ladder gives `Grade: {low_g}` to every passing {var} (`{var}` already exists). Fix the code so it prints "
            f"{_grade_ranges(steps)}, and `Grade: F` for anything lower."
        )
        why = f"The thresholds are in the wrong order: `{var} >= {low_t}` catches every passing score first. Put the highest threshold first."
    elif kind == "swapped":
        steps = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]
        i = rng.randrange(3)
        down = [("score >= %d" % t, f"Grade: {g}") for t, g in steps]
        swapped = list(down)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        starter = _chain(swapped, "Grade: F")
        solution = _chain(down, "Grade: F")
        values = [100, 90, 89, 85, 80, 79, 75, 70, 69, 65, 60, 59, 20]
        out = lambda v: next((f"Grade: {g}" for t, g in steps if v >= t), "Grade: F")  # noqa: E731
        var = "score"
        lost = steps[i][1]
        prompt = (
            f"Two checks in this ladder are in the wrong order, so `Grade: {lost}` never prints (`score` already exists). "
            "Fix the code so 90 or more is A, 80 to 89 is B, 70 to 79 is C, 60 to 69 is D and anything lower is F."
        )
        why = f"The check just below `score >= {steps[i][0]}` sits above it and catches those scores first. Swap them back so the higher threshold comes first."
    else:  # number_test
        lo, hi = rng.choice([(1, 100), (1, 100), (1, 10), (10, 99), (1, 50)])
        special = rng.choice([50, 7, 25, 42]) if (lo, hi) == (1, 100) else rng.randint(lo + 2, hi - 2)
        var = "number"
        starter = _chain([(f"{lo} <= number <= {hi}", "In range"), (f"number == {special}", "Special number")], "Out of range")
        solution = _chain([(f"number == {special}", "Special number"), (f"{lo} <= number <= {hi}", "In range")], "Out of range")
        values = [special, special + 1, hi, lo, lo - 1, hi + 1, -3, hi + 40]
        out = lambda v: "Special number" if v == special else "In range" if lo <= v <= hi else "Out of range"  # noqa: E731
        prompt = (
            f"This Number Test never prints `Special number` for {special} (`number` already exists). Fix the code: exactly {special} is `Special number`, "
            f"{lo} to {hi} is `In range`, anything else is `Out of range`."
        )
        why = f"{special} is also in range, and the range check comes first, so the special check is never reached. Put the more specific check first."
    pairs = _examples_first([(v, out(v)) for v in dict.fromkeys(values)])
    cases = [Case(vars={var: v}, out=o) for v, o in pairs]
    task = _prog(solution, cases, starter=starter + "\n")
    return _code_q(HARD, prompt, task, why)


@generator(TOPIC, HARD, qtype="code")
def gen_code_fix_the_order(rng: random.Random) -> Question:
    """Debug a ladder whose checks are in the wrong order (Rank Checker bonus / grade ladder / Number Test)."""
    return fix_order_question(rng.choice(["diamond", "diamond", "ascending", "swapped", "swapped", "number_test"]), rng)


_WEEKEND_STORIES = [
    # (flag1, flag2, number, limits, (msg1, msg2, msg3, msg4), (plain-English conditions))
    (
        "is_weekend", "has_homework", "money", [10, 10, 15, 20, 8],
        ("Do homework first.", "Go to the movies.", "Stay home.", "Go to school."),
        ("it is the weekend and there is homework", "it is the weekend and money is at least {n}", "it is the weekend"),
    ),
    (
        "is_raining", "has_umbrella", "money", [5, 8, 10],
        ("Walk with your umbrella.", "Take the bus.", "Wait inside.", "Walk to school."),
        ("it is raining and there is an umbrella", "it is raining and money is at least {n}", "it is raining"),
    ),
    (
        "is_member", "has_coupon", "money", [10, 12, 15],
        ("Free entry.", "Pay and enter.", "Come back tomorrow.", "Join the club first."),
        ("the player is a member and has a coupon", "the player is a member and money is at least {n}", "the player is a member"),
    ),
    (
        "is_alive", "has_key", "coins", [20, 30, 50],
        ("Open the door.", "Buy a key.", "Keep exploring.", "Game over."),
        ("the player is alive and has a key", "the player is alive and coins is at least {n}", "the player is alive"),
    ),
]


def weekend_question(story: tuple, limit: int) -> Question:
    f1, f2, num, _limits, msgs, conds = story
    m1, m2, m3, m4 = msgs
    rungs = [(f"{f1} and {f2}", m1), (f"{f1} and {num} >= {limit}", m2), (f1, m3)]
    solution = _join(_ladder(rungs, m4))

    def out(a: bool, b: bool, n: int) -> str:
        if a and b:
            return m1
        if a and n >= limit:
            return m2
        return m3 if a else m4

    combos = [
        (True, False, limit + 2),
        (False, False, 50),
        (True, True, limit + 5),
        (True, False, limit - 1),
        (True, False, limit),
        (False, True, limit + 5),
        (True, True, 0),
        (False, False, 0),
    ]
    cases = [Case(vars={f1: a, f2: b, num: n}, out=out(a, b, n)) for a, b, n in combos]
    task = _prog(solution, _reorder_cases(cases), starter=_preset_starter(f1, f2, num))
    c1, c2, c3 = conds
    return _code_q(
        HARD,
        f"`{f1}` and `{f2}` (`True`/`False`) and `{num}` (a number) already exist. Print exactly one line: `{m1}` if {c1}; "
        f"otherwise `{m2}` if {c2.format(n=limit)}; otherwise `{m3}` if {c3}; otherwise `{m4}`",
        task,
        f"Order matters: put the most specific condition (`{f1} and {f2}`) first, then `{f1}` with `{num}`, then plain `{f1}`, and let `else` cover everything left.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_weekend_plan(rng: random.Random) -> Question:
    story = rng.choice(_WEEKEND_STORIES)
    return weekend_question(story, rng.choice(story[3]))
