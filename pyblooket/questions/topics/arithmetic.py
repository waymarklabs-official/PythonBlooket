"""Question generators for the "arithmetic" topic (CSF.2.A1: Arithmetic Operators).

Source: the lesson file `arithmetic_operators.py`
    print(6 + 7)  print(100 - 33)  print(5 * 13.4)  print(603 / 9)
    print(10 // 3)  print(10 % 3)  print(3.44821724038 ** 3)
(addition, subtraction, multiplication, division, floor, modulus, exponentiation), plus what the
Unit 2 lessons and the Python Bingo list build on it: `/` always gives a float (`603 / 9` is
`67.0`), `//` rounds down, `%` is the remainder (even/odd, multiples of 5), `**` is a power,
the order of operations, `+=` and friends, int vs float results, `round()`, and the Bingo tasks
"area of a circle", "simple interest" and "modulo for multiples of 5".

Formats: multiple choice, fill in the blanks, matching, and typed code (graded in the sandbox).
"""

from __future__ import annotations

import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    expression_task,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
    which_expression_question,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "arithmetic"

OP_NAMES = {
    "+": "addition",
    "-": "subtraction",
    "*": "multiplication",
    "/": "division",
    "//": "floor division",
    "%": "modulus",
    "**": "exponentiation",
}
ALL_OPS = list(OP_NAMES)

# What each operator does, as a verb phrase ("`%` gives the remainder ...").
OP_DOES = {
    "+": "adds the two numbers",
    "-": "subtracts the right number from the left one",
    "*": "multiplies the two numbers (a float on either side gives a float)",
    "/": "divides and always gives a float, even when it divides evenly (`603 / 9` is `67.0`)",
    "//": "divides and rounds down to a whole number (`10 // 3` is `3`)",
    "%": "gives the remainder left over after dividing (`10 % 3` is `1`)",
    "**": "raises the left number to the power of the right one (`2 ** 3` is `8`)",
}
OP_FACT = {op: f"`{op}` {does}." for op, does in OP_DOES.items()}

NUM_VARS = ["score", "total", "count", "points", "money", "coins", "price", "number"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _ev(expr: str):
    """Evaluate one of OUR OWN generated arithmetic expressions."""
    return eval(expr, {"__builtins__": {}, "round": round}, {})  # noqa: S307 - trusted, generated text


def _clean(value, limit: int = 9):
    """Reject floats with noisy tails (3.3000000000000003) and huge numbers."""
    if isinstance(value, float):
        if len(repr(value)) > limit or value != round(value, 6):
            raise GenerationError(f"noisy float {value!r}")
    elif isinstance(value, int) and abs(value) > 10**7:
        raise GenerationError("number too big")
    return value


def _tries(build, n: int = 80):
    """Call ``build()`` (which draws from rng) until it stops raising GenerationError."""
    last = None
    for _ in range(n):
        try:
            return build()
        except (GenerationError, ArithmeticError) as exc:
            last = exc
    raise GenerationError(f"no valid variant: {last}")


def _so(fact: str, expr: str, value: str) -> str:
    """'<fact> So `expr` is `value`.' -- without repeating an example the fact already gives."""
    if f"`{expr}` is `{value}`" in fact:
        return fact
    return f"{fact} So `{expr}` is `{value}`."


def _fmt(value) -> str:
    """The text print() shows for a number."""
    return str(value)


def _operands(rng: random.Random, op: str) -> tuple:
    """Two operands that give a tidy result for ``op`` (printed output stays short)."""
    if op == "+":
        return rng.randint(6, 60), rng.randint(3, 50)
    if op == "-":
        b = rng.randint(3, 60)
        return b + rng.randint(5, 70), b
    if op == "*":
        if rng.random() < 0.5:
            return rng.randint(3, 15), rng.randint(3, 12)
        return rng.randint(2, 9), round(rng.uniform(1, 15), 1)
    if op == "/":
        b = rng.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
        a = b * rng.randint(4, 95)
        if rng.random() < 0.35:
            a += rng.choice([1, 2, 3])
        return a, b
    if op == "//":
        return rng.randint(10, 99), rng.randint(2, 9)
    if op == "%":
        b = rng.randint(3, 9)
        a = rng.randint(10, 99)
        if a % b == 0:
            a += 1
        return a, b
    if op == "**":
        return rng.randint(2, 9), rng.randint(2, 3)
    raise GenerationError(op)


def _all_groupings(nums: list, ops: list) -> list:
    """Every way of fully parenthesizing ``nums[0] ops[0] nums[1] ...`` (as strings)."""
    if len(nums) == 1:
        return [str(nums[0])]
    out = []
    for i in range(1, len(nums)):
        for left in _all_groupings(nums[:i], ops[:i - 1]):
            for right in _all_groupings(nums[i:], ops[i:]):
                out.append(f"({left}) {ops[i - 1]} ({right})")
    return out


def _other_results(nums: list, ops: list, correct_text: str, extra: list | None = None, filler: list | None = None, maxlen: int = 14) -> list:
    """Printed results of wrong groupings (left-to-right first), tidy values first.
    ``filler`` expressions (near misses) are only used after the groupings."""
    left_to_right = str(nums[0])
    for n, op in zip(nums[1:], ops):
        left_to_right = f"({left_to_right}) {op} {n}"
    texts = []
    for expr in [left_to_right, *(extra or []), *_all_groupings(nums, ops), *(filler or [])]:
        try:
            value = _ev(expr)
        except (ZeroDivisionError, ValueError, OverflowError):
            continue
        text = _fmt(value)
        if text != correct_text and text not in texts and len(text) <= maxlen:
            texts.append(text)
    tidy = [t for t in texts if len(t) <= 8]
    return tidy + [t for t in texts if t not in tidy]


def _expr(nums: list, ops: list) -> str:
    out = str(nums[0])
    for n, op in zip(nums[1:], ops):
        out += f" {op} {n}"
    return out


def _nearby_outputs(text: str) -> list:
    """Near misses of a printed result: reversed order / one number off (space-separated ints)."""
    parts = text.split()
    out = []
    if len(parts) > 1:
        out.append(" ".join(reversed(parts)))
    for i, part in enumerate(parts):
        try:
            n = int(part)
        except ValueError:
            continue
        for d in (1, -1, 2):
            out.append(" ".join([*parts[:i], str(n + d), *parts[i + 1:]]))
    return out


def _mutant_outputs(code: str, swaps: list) -> list:
    """Printed output of ``code`` after each (old, new) text swap that still runs."""
    outs = []
    for old, new in swaps:
        if old not in code:
            continue
        res = run_code(code.replace(old, new, 1))
        if not res.error and res.output.strip():
            outs.append(res.output)
    return outs


# --------------------------------------------------------------------------
# EASY -- multiple choice (vocabulary and one-line results, like the Canvas quizzes)
# --------------------------------------------------------------------------

_SYMBOL_DISTRACTORS = {
    "+": ["-", "*", "&"],
    "-": ["+", "--", "*"],
    "*": ["**", "x", "+"],
    "/": ["//", "%", "\\"],
    "//": ["/", "%", "**"],
    "%": ["//", "/", "**"],
    "**": ["^", "*", "//"],
}


@generator(TOPIC, EASY)
def gen_operator_name(rng: random.Random) -> Question:
    """'Which symbol is the floor division operator?' / 'What is the % operator called?'"""
    sym = rng.choice(["//", "%", "**", "/", "*", "+", "-", "//", "%", "**"])
    name = OP_NAMES[sym]
    if rng.random() < 0.5:
        prompt = rng.choice(
            [f'Which symbol is the "{name}" operator in Python?', f"Which operator performs {name}?"]
        )
        correct, distractors = sym, _SYMBOL_DISTRACTORS[sym]
    else:
        prompt = rng.choice([f"What is the `{sym}` operator called?", f"Which name goes with the `{sym}` operator?"])
        others = [n for s, n in OP_NAMES.items() if s != sym]
        rng.shuffle(others)
        correct, distractors = name, others
        if sym == "%":
            distractors = ["division", "percent", *distractors]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=distractors,
        explanation=f"`{sym}` is the {name} operator: it {OP_DOES[sym]}." + (' The lesson comment calls it the "floor" operator.' if sym == "//" else ""),
        rng=rng,
    )


LESSON_LINES = [("6", "+", "7"), ("100", "-", "33"), ("5", "*", "13.4"), ("603", "/", "9"), ("10", "//", "3"), ("10", "%", "3")]


@generator(TOPIC, EASY)
def gen_print_result(rng: random.Random) -> Question:
    """'What does print(603 / 9) print?' -- the lesson's own lines first, then lookalikes."""

    def build() -> Question:
        if rng.random() < 0.3:
            a, op, b = rng.choice(LESSON_LINES)
            a, b = (int(a) if "." not in a else float(a)), (int(b) if "." not in b else float(b))
        else:
            op = rng.choice(["+", "-", "*", "/", "//", "%", "**", "/", "//", "%"])
            a, b = _operands(rng, op)
        expr = f"{a} {op} {b}"
        value = _clean(_ev(expr))
        wrong = []
        if isinstance(value, float) and value == int(value):
            wrong.append(str(int(value)))  # the classic: "603 / 9 is 67"
        if op == "//":
            wrong.append(_fmt(a / b))  # forgot to round down
        if op == "%":
            wrong.append(_fmt(a // b))  # quotient instead of remainder
        if op == "+":
            wrong.append(f"{a}{b}")  # joined like text
        others = [o for o in ALL_OPS if o != op]
        rng.shuffle(others)
        for o in others:
            try:
                text = _fmt(_ev(f"{a} {o} {b}"))
            except (ZeroDivisionError, ValueError):
                continue
            if len(text) <= 12:
                wrong.append(text)
        return output_question(
            topic=TOPIC,
            difficulty=EASY,
            code=f"print({expr})",
            distractors=wrong,
            explanation=_so(OP_FACT[op], expr, _fmt(value)),
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, EASY)
def gen_result_type(rng: random.Random) -> Question:
    """'What data type does 603 / 9 give?'"""

    def build() -> Question:
        kind = rng.choice(["div", "div", "floor", "mod", "pow", "mulf", "addf", "powf"])
        if kind == "div":
            b = rng.choice([2, 3, 4, 5, 6, 8, 9, 10])
            a = b * rng.randint(3, 80)
            expr, want = f"{a} / {b}", "float"
            why = f"`/` always gives a float, even when it divides evenly: `{a} / {b}` is `{_fmt(a / b)}`."
        elif kind == "floor":
            a, b = _operands(rng, "//")
            expr, want = f"{a} // {b}", "int"
            why = f"`//` on two ints gives an int: `{a} // {b}` is `{a // b}`."
        elif kind == "mod":
            a, b = _operands(rng, "%")
            expr, want = f"{a} % {b}", "int"
            why = f"The remainder of two ints is an int: `{a} % {b}` is `{a % b}`."
        elif kind == "pow":
            a, b = _operands(rng, "**")
            expr, want = f"{a} ** {b}", "int"
            why = f"An int to a whole-number power stays an int: `{a} ** {b}` is `{a ** b}`."
        elif kind == "powf":
            expr, want = f"{rng.choice(['3.44821724038', '2.5', '1.5', '0.5'])} ** {rng.choice([2, 3])}", "float"
            why = "A float raised to a power is still a float (the lesson's `3.44821724038 ** 3` is a float too)."
        elif kind == "mulf":
            a, b = _operands(rng, "*")
            if not isinstance(b, float):
                b = round(rng.uniform(1, 15), 1)
            expr, want = f"{a} * {b}", "float"
            why = f"A float on either side makes the result a float: `{a} * {b}` is `{_fmt(_clean(_ev(expr)))}`."
        else:
            a = rng.randint(2, 40)
            b = round(rng.uniform(1, 9), 1)
            expr, want = f"{a} + {b}", "float"
            why = f"int + float gives a float: `{a} + {b}` is `{_fmt(_clean(_ev(expr)))}`."
        prompt = rng.choice(
            [f"What data type does `{expr}` give?", f"What is the type of the result of `{expr}`?"]
        )
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=prompt,
            correct=want,
            distractors=[t for t in ("int", "float") if t != want] + ["str", "bool"],
            explanation=why,
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, EASY)
def gen_multiple_condition(rng: random.Random) -> Question:
    """'Which condition is True when n is a multiple of 5?' (modulo for even/odd/multiples)"""
    v = rng.choice(["n", "number", "num", "score", "count", "x"])
    kind = rng.choice(["even", "odd", "multiple", "multiple"])
    if kind == "even":
        k, prompt, correct = 2, f"Which condition is True when `{v}` is even?", f"{v} % 2 == 0"
        wrong = [f"{v} % 2 == 1", f"{v} // 2 == 0", f"{v} % 2 = 0", f"{v} / 2 == 0"]
        why = f"A number is even when dividing by 2 leaves remainder 0: `{v} % 2 == 0`."
    elif kind == "odd":
        k, prompt, correct = 2, f"Which condition is True when `{v}` is odd?", f"{v} % 2 == 1"
        wrong = [f"{v} % 2 == 0", f"{v} // 2 == 1", f"{v} / 2 == 1", f"{v} % 2 = 1"]
        why = f"A number is odd when dividing by 2 leaves remainder 1: `{v} % 2 == 1`."
    else:
        k = rng.choice([3, 5, 5, 10, 4])
        prompt = f"Which condition is True when `{v}` is a multiple of {k}?"
        correct = f"{v} % {k} == 0"
        wrong = [f"{k} % {v} == 0", f"{v} // {k} == 0", f"{v} % {k} = 0", f"{v} / {k} == 0", f"{v} % {k} == 1"]
        why = f"A multiple of {k} leaves no remainder when divided by {k}: `{v} % {k} == 0`. Use `==` to compare, not `=`."
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


_OP_DOES = {
    "/": "Divides and always gives a float",
    "//": "Divides and rounds the result down to a whole number",
    "%": "Gives the remainder left over after dividing",
    "**": "Raises the left number to the power of the right one",
    "*": "Multiplies the two numbers",
    "-": "Subtracts the right number from the left one",
}


@generator(TOPIC, EASY)
def gen_operator_does(rng: random.Random) -> Question:
    """'What does the // operator do?'"""
    sym = rng.choice(["/", "//", "%", "**", "//", "%", "/"])
    others = [s for s in _OP_DOES if s != sym]
    rng.shuffle(others)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=rng.choice([f"What does the `{sym}` operator do?", f"Which statement about `{sym}` is true?"]),
        correct=_OP_DOES[sym],
        distractors=[_OP_DOES[s] for s in others],
        explanation=OP_FACT[sym],
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_divide_by_zero(rng: random.Random) -> Question:
    """'Which line causes an error when it runs?' (dividing by zero)"""
    a = rng.randint(4, 60)
    b = rng.randint(2, 9)
    op = rng.choice(["/", "//", "%"])
    pool = [f"print({a} / {b})", f"print({a} // {b})", f"print({a} % {b})", f"print(0 / {b})", f"print({a} ** 0)", f"print({a} * 0)"]
    rng.shuffle(pool)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Which line causes an error when it runs?",
        correct=f"print({a} {op} 0)",
        distractors=pool,
        explanation=f"You can't divide by zero: `/`, `//` and `%` with `0` on the right raise a ZeroDivisionError. Lines like `0 / {b}` or `{a} * 0` are fine.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_which_line_prints(rng: random.Random) -> Question:
    """'Which line prints 67.0?' -- the lesson's print lines read backwards."""

    def build() -> Question:
        if rng.random() < 0.3:
            a, op, b = rng.choice(LESSON_LINES)
            a, b = (int(a) if "." not in a else float(a)), (int(b) if "." not in b else float(b))
        else:
            op = rng.choice(["/", "//", "%", "*", "**", "+", "-", "/", "//", "%"])
            a, b = _operands(rng, op)
        target = _fmt(_clean(_ev(f"{a} {op} {b}")))
        wrong = []
        others = [o for o in ALL_OPS if o != op]
        rng.shuffle(others)
        for o in others:
            try:
                text = _fmt(_ev(f"{a} {o} {b}"))
            except (ZeroDivisionError, ValueError):
                continue
            if text != target and len(text) <= 12:
                wrong.append(f"print({a} {o} {b})")
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=f"Which line prints `{target}`?",
            correct=f"print({a} {op} {b})",
            distractors=wrong,
            explanation=_so(OP_FACT[op], f"{a} {op} {b}", target),
            rng=rng,
        )

    return _tries(build)


# --------------------------------------------------------------------------
# MEDIUM -- multiple choice (read a short snippet, pick the right formula, spot the classic mistake)
# --------------------------------------------------------------------------

PRECEDENCE_RULE = "Order of operations: parentheses first, then `**`, then `*` `/` `//` `%` (left to right), then `+` `-`."
_PREC = {"**": 3, "*": 2, "/": 2, "//": 2, "%": 2, "+": 1, "-": 1}


def _first_step(nums: list, ops: list, first: int | None = None) -> tuple:
    """(the sub-expression done first, its value, the expression that is left)"""
    if first is None:
        first = max(range(len(ops)), key=lambda i: (_PREC[ops[i]], -i))
    sub = f"{nums[first]} {ops[first]} {nums[first + 1]}"
    value = _ev(sub)
    return sub, value, _expr(nums[:first] + [value] + nums[first + 2:], ops[:first] + ops[first + 1:])


@generator(TOPIC, MEDIUM)
def gen_precedence_print(rng: random.Random) -> Question:
    """'What does print(2 + 3 * 4) print?' -- precedence and parentheses, wrong answers = other groupings."""

    def build() -> Question:
        ops = [rng.choice(["+", "-", "*", "*", "//", "%", "**", "+"]) for _ in range(2)]
        if ops.count("**") > 1:
            raise GenerationError("two powers")
        nums = [rng.randint(2, 9) for _ in range(3)]
        for i, op in enumerate(ops):
            if op == "**":
                nums[i] = rng.randint(2, 5)
                nums[i + 1] = rng.choice([2, 3])
        plain = _expr(nums, ops)
        shape = rng.choice(["plain", "left", "right"])
        if shape == "left":
            expr = f"({nums[0]} {ops[0]} {nums[1]}) {ops[1]} {nums[2]}"
        elif shape == "right":
            expr = f"{nums[0]} {ops[0]} ({nums[1]} {ops[1]} {nums[2]})"
        else:
            expr = plain
        value = _clean(_ev(expr))
        correct = _fmt(value)
        extra = [plain] if shape != "plain" else []
        if shape == "plain" and _ev(plain) == _ev(_expr_ltr(nums, ops)):
            raise GenerationError("precedence does not matter here")
        if shape != "plain" and _ev(plain) == value:
            raise GenerationError("the parentheses do not matter here")
        wrong = _other_results(nums, ops, correct, extra, [f"{value} + 1", f"{value} - 1", f"{value} + 2", f"{value} * 2"])
        sub, sub_value, left = _first_step(nums, ops, {"plain": None, "left": 0, "right": 1}[shape])
        return output_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            code=f"print({expr})",
            distractors=wrong,
            explanation=(
                f"{'Parentheses go first' if shape != 'plain' else 'The higher-precedence operator goes first'}: "
                f"`{sub}` is {sub_value}. Then `{left}` is `{correct}`."
            ),
            rng=rng,
        )

    return _tries(build)


def _expr_ltr(nums: list, ops: list) -> str:
    out = str(nums[0])
    for n, op in zip(nums[1:], ops):
        out = f"({out}) {op} {n}"
    return out


@generator(TOPIC, MEDIUM)
def gen_augmented_trace(rng: random.Random) -> Question:
    """score = 10; score += 5; score *= 2; score -= 4; print(score)"""
    var = rng.choice(["score", "total", "count", "points", "money", "coins"])
    start = rng.randint(4, 20)

    def build():
        steps = [(rng.choice(["+=", "-=", "*="]), rng.randint(2, 9)) for _ in range(3)]
        steps = [(op, min(n, 4) if op == "*=" else n) for op, n in steps]
        if len({op for op, _ in steps}) < 2 or [op for op, _ in steps].count("*=") > 1:
            raise GenerationError("boring")
        return steps

    steps = _tries(build)

    def run(order, begin=start):
        v = begin
        for op, n in order:
            v = v + n if op == "+=" else v - n if op == "-=" else v * n
        return v

    lines = [f"{var} = {start}"] + [f"{var} {op} {n}" for op, n in steps] + [f"print({var})"]
    trace, v = [], start
    for op, n in steps:
        v = run([(op, n)], v)
        trace.append(f"`{var} {op} {n}` makes it {v}")
    wrong = [str(run(steps[:i] + steps[i + 1:])) for i in (0, 1, 2)]
    wrong += [str(run(steps[::-1])), str(steps[-1][1]), str(start + sum(n for _, n in steps))]
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code="\n".join(lines),
        distractors=wrong,
        explanation=f"Each line updates `{var}`: it starts at {start}, " + ", ".join(trace) + ".",
        rng=rng,
    )


def _formula_family(rng: random.Random, which: str) -> tuple:
    """(setup, prompt, correct, wrongs, explanation)"""
    if which == "average":
        names = rng.choice([("test1", "test2", "test3"), ("quiz1", "quiz2", "quiz3"), ("a", "b", "c")])
        vals = [rng.randint(60, 100) for _ in names]
        if sum(vals) % 3 == 0:
            vals[0] += 1
        setup = "\n".join(f"{n} = {v}" for n, v in zip(names, vals))
        total = " + ".join(names)
        return (
            setup,
            "Which expression gives the exact average of the three numbers?",
            f"({total}) / 3",
            [f"{total} / 3", f"({total}) // 3", f"({total}) / 2", total],
            "Division runs before addition, so the sum needs parentheses: `(a + b + c) / 3`. `//` would drop the decimals.",
        )
    if which == "circle":
        r = rng.randint(3, 12)
        return (
            f"pi = 3.14\nradius = {r}",
            "Which expression gives the area of the circle?",
            "pi * radius ** 2",
            ["(pi * radius) ** 2", "pi * radius * 2", "pi * 2 ** radius", "2 * pi * radius"],
            "Area is pi times the radius squared. `**` runs before `*`, so `pi * radius ** 2` squares only the radius.",
        )
    if which == "fahrenheit":
        c = rng.choice([10, 20, 25, 30, 35, 40, 100])
        return (
            f"celsius = {c}",
            "Which expression converts `celsius` to Fahrenheit?",
            "celsius * 9 / 5 + 32",
            ["celsius * 9 / (5 + 32)", "celsius * (9 / 5 + 32)", "celsius + 32 * 9 / 5", "celsius * 5 / 9 + 32"],
            "The formula is multiply by 9, divide by 5, then add 32. `*` and `/` run left to right before the `+`.",
        )
    if which == "percent":
        total = rng.choice([20, 25, 40, 50, 80])
        score = rng.randint(total // 2, total - 1)
        return (
            f"score = {score}\ntotal = {total}",
            "Which expression gives the score as a percent of the total?",
            "score / total * 100",
            ["score / (total * 100)", "score * total / 100", "score / total + 100", "score / total"],
            "Divide the score by the total, then multiply by 100: `score / total * 100`.",
        )
    if which == "interest":
        p = rng.choice([500, 800, 1000, 1200, 2000])
        return (
            f"principal = {p}\nrate = {rng.choice([3, 4, 5, 6, 8])}\ntime = {rng.randint(2, 5)}",
            "Which expression gives the simple interest? (`rate` is a percent.)",
            "principal * rate * time / 100",
            ["principal + rate * time / 100", "principal * rate * time * 100", "principal * (rate + time) / 100", "principal * rate / time / 100"],
            "Simple interest is principal times rate times time, divided by 100 because the rate is a percent.",
        )
    if which == "perimeter":
        w = rng.randint(3, 9)
        return (
            f"length = {w + rng.randint(2, 8)}\nwidth = {w}",
            "Which expression gives the perimeter of the rectangle?",
            "2 * (length + width)",
            ["2 * length + width", "length + width * 2", "2 * length * width", "length * width"],
            "The perimeter adds both sides and doubles it. Without parentheses, `*` would only double one of them.",
        )
    price = rng.choice([40, 60, 80, 120, 200])
    return (
        f"price = {price}\ndiscount = {rng.choice([10, 15, 20, 25])}",
        "Which expression gives the price after taking `discount` percent off?",
        "price - price * discount / 100",
        ["price - discount / 100", "price * discount / 100", "(price - discount) / 100", "price - discount"],
        "First find the discount amount (`price * discount / 100`), then subtract it from the price.",
    )


@generator(TOPIC, MEDIUM)
def gen_formula_pick(rng: random.Random) -> Question:
    """'Which expression gives the average / area / percent ...?' -- precedence in real formulas."""

    def build() -> Question:
        which = rng.choice(["average", "circle", "fahrenheit", "percent", "interest", "perimeter", "discount"])
        setup, prompt, correct, wrong, why = _formula_family(rng, which)
        rng.shuffle(wrong)
        target = _ev_setup(correct, setup)
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=prompt,
            setup=setup,
            target=target,
            correct_expr=correct,
            wrong_exprs=wrong,
            explanation=why,
            rng=rng,
        )

    return _tries(build)


def _ev_setup(expr: str, setup: str):
    res = run_code(setup)
    return eval(expr, res.namespace)  # noqa: S307 - trusted, generated text


@generator(TOPIC, MEDIUM)
def gen_float_or_int(rng: random.Random) -> Question:
    """'Which expression gives a float?' / 'Which expression gives an int?'"""

    def build() -> Question:
        a, b = rng.randint(6, 40), rng.randint(2, 6)
        f = rng.choice([1.5, 2.5, 0.5, 4.0, 2.0])
        floats = [f"{a} / {b}", f"{a * b} / {b}", f"{a} * {f}", f"{a} + {f}", f"{a} // {f}", f"{a} % {f}"]
        ints = [f"{a} // {b}", f"{a} % {b}", f"{a} * {b}", f"{a} + {b}", f"{a} - {b}", f"{a} ** 2"]
        assert all(isinstance(_ev(e), float) for e in floats) and all(isinstance(_ev(e), int) for e in ints)
        want_float = rng.random() < 0.5
        good, bad = (floats, ints) if want_float else (ints, floats)
        pick = rng.choice(good)
        rng.shuffle(bad)
        if not want_float:
            bad = [f"{a * b} / {b}", *bad]  # looks like it divides evenly, still a float
        value = _ev(pick)
        why = (
            f"`{pick}` is `{_fmt(value)}`, a {'float' if want_float else 'int'}. "
            "`/` always gives a float, and a float anywhere in `+ - * // %` makes the result a float; "
            "two ints with `+ - * // % **` stay ints."
        )
        return build_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=f"Which expression gives {'a float' if want_float else 'an int'}?",
            correct=pick,
            distractors=bad,
            explanation=why,
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, MEDIUM)
def gen_round_print(rng: random.Random) -> Question:
    """price = 7.8463; print(round(price, 2))"""

    def build() -> Question:
        var = rng.choice(["price", "total", "average", "result", "area", "gpa"])
        kind = rng.choice(["digits", "digits", "quotient", "whole"])
        if kind == "quotient":
            b = rng.choice([3, 6, 7, 9, 11])
            a = rng.randint(2, 40)
            if a % b == 0:
                raise GenerationError("exact")
            x = a / b
            setup = f"{var} = {a} / {b}"
        else:
            x = round(rng.uniform(1, 30), rng.choice([3, 4]))
            setup = f"{var} = {x}"
        digits = None if kind == "whole" else 2
        scaled = x * 10 ** (digits or 0)
        if abs(scaled % 1 - 0.5) < 0.12 or scaled % 1 < 0.05:
            raise GenerationError("too close to a tie")
        if digits is None:
            r = round(x)
            code = f"{setup}\nprint(round({var}))"
            wrong = [str(float(r)), str(int(x) if r != int(x) else int(x) + 1), str(x)]
            why = f"`round({var})` with one argument rounds to the nearest whole number and gives an int: `{r}`."
        else:
            r = round(x, 2)
            code = f"{setup}\nprint(round({var}, 2))"
            trunc = int(x * 100) / 100
            wrong = [str(x), str(trunc), str(round(x, 1)), f"{r:.2f}", str(round(x, 3)), str(round(x))]
            why = f"`round({var}, 2)` keeps 2 decimal places and rounds the last one: `{r}`. It does not cut digits off."
        return output_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            code=code,
            distractors=wrong,
            explanation=why,
            rng=rng,
        )

    return _tries(build)


_THINGS = [("cookies", "box", "boxes"), ("pencils", "bag", "bags"), ("stickers", "pack", "packs"), ("cards", "pile", "piles"), ("marbles", "jar", "jars")]


@generator(TOPIC, MEDIUM)
def gen_word_problem_operator(rng: random.Random) -> Question:
    """'47 cookies are packed 6 to a box. Which expression gives the number of full boxes?'"""

    def build() -> Question:
        which = rng.choice(["full", "left", "hours", "rest", "share", "square", "cube", "cost"])
        things, one, many = rng.choice(_THINGS)
        if which in ("full", "left"):
            b = rng.randint(4, 9)
            a = rng.randint(3 * b, 12 * b)
            if a % b == 0:
                a += rng.randint(1, b - 1)
            setup = f"total = {a}\nper_{one} = {b}"
            q = f"{a} {things} are put {b} to a {one}. Which expression gives "
            if which == "full":
                prompt, correct = q + f"the number of FULL {many}?", f"total // per_{one}"
                wrong = [f"total / per_{one}", f"total % per_{one}", f"total * per_{one}", f"per_{one} // total"]
                why = f"Full groups are counted with floor division: `total // per_{one}`. `%` would give the leftovers."
            else:
                prompt, correct = q + f"the number of {things} left over?", f"total % per_{one}"
                wrong = [f"total // per_{one}", f"total / per_{one}", f"total - per_{one}", f"per_{one} % total"]
                why = f"The leftovers are the remainder, so use the modulus: `total % per_{one}`."
        elif which in ("hours", "rest"):
            a = rng.randint(130, 700)
            if a % 60 == 0:
                a += 7
            setup = f"minutes = {a}"
            if which == "hours":
                prompt = "Which expression gives the number of WHOLE hours in `minutes`?"
                correct, wrong = "minutes // 60", ["minutes % 60", "minutes / 60", "minutes * 60", "60 // minutes"]
                why = "Whole hours means rounding down: `minutes // 60`."
            else:
                prompt = "Which expression gives the minutes left over after taking out the whole hours?"
                correct, wrong = "minutes % 60", ["minutes // 60", "minutes / 60", "60 % minutes", "minutes - 60"]
                why = "What is left after the whole hours is the remainder: `minutes % 60`."
        elif which == "share":
            f = rng.randint(3, 7)
            a = f * rng.randint(4, 12) + rng.randint(1, f - 1)
            setup = f"money = {a}\nfriends = {f}"
            prompt = "Which expression gives the exact amount each friend gets, decimals allowed?"
            correct, wrong = "money / friends", ["money // friends", "money % friends", "money * friends", "friends / money"]
            why = "Splitting into an exact (decimal) share is plain division: `money / friends`."
        elif which == "square":
            setup = f"side = {rng.randint(3, 12)}"
            prompt = "Which expression gives the area of a square with this side?"
            correct, wrong = "side ** 2", ["side * 2", "side + side", "side ** 3", "2 ** side"]
            why = "Area is side times side, which is `side ** 2`."
        elif which == "cube":
            setup = f"side = {rng.randint(3, 9)}"
            prompt = "Which expression gives the volume of a cube with this side?"
            correct, wrong = "side ** 3", ["side * 3", "side ** 2", "3 ** side", "side + side + side"]
            why = "Volume of a cube is side times side times side: `side ** 3`."
        else:
            setup = f"price = {rng.randint(3, 20)}\nquantity = {rng.randint(3, 9)}"
            prompt = "Which expression gives the total cost of `quantity` items at `price` each?"
            correct, wrong = "price * quantity", ["price + quantity", "price / quantity", "price ** quantity", "price // quantity"]
            why = "Equal-sized groups are multiplication: `price * quantity`."
        rng.shuffle(wrong)
        return which_expression_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt=prompt,
            setup=setup,
            target=_ev_setup(correct, setup),
            correct_expr=correct,
            wrong_exprs=wrong,
            explanation=why,
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, MEDIUM)
def gen_mistake_explain(rng: random.Random) -> Question:
    """'This should print the average of a and b, but prints 125.0. Why?' -- classic mix-ups."""
    return _tries(lambda: _mistake_explain(rng))


def _mistake_explain(rng: random.Random) -> Question:
    which = rng.choice(["average", "square", "remainder", "floor_avg", "last_digit"])
    if which == "average":
        a, b = rng.randint(60, 99), rng.choice([70, 80, 90, 100])
        code = f"a = {a}\nb = {b}\naverage = a + b / 2\nprint(average)"
        goal = f"the average of a and b ({(a + b) / 2})"
        correct = "Division happens before addition, so only b is halved"
        wrong = ["Addition always happens before division", "The sum has to be stored in a variable first", "Python can't divide inside an assignment"]
        why = "`/` runs before `+`, so only `b` is halved. Use parentheses: `(a + b) / 2`."
    elif which == "square":
        r = rng.randint(3, 9)
        code = f"radius = {r}\narea = 3.14 * radius * 2\nprint(area)"
        goal = f"the area of a circle (3.14 * radius squared = {round(3.14 * r * r, 2)})"
        correct = "radius * 2 doubles the radius; squaring needs ** 2"
        wrong = ["3.14 has to be written as pi", "Python runs * before **, so radius is multiplied first", "radius has to be a float to be squared"]
        why = "`radius * 2` doubles the radius. To square it, write `radius ** 2`: `3.14 * radius ** 2`."
    elif which == "remainder":
        t, d = rng.randint(30, 95), rng.choice([7, 8, 9])
        code = f"total = {t}\nleftover = total / {d}\nprint(leftover)"
        goal = f"the remainder of {t} divided by {d} ({t % d})"
        correct = "/ gives the exact quotient as a float; % gives the remainder"
        wrong = ["/ gives only the whole-number part", "% gives the quotient instead of the remainder", "total has to be a float before dividing"]
        why = f"`/` gives the exact quotient as a float. For the remainder use `%`: `total % {d}`."
    elif which == "floor_avg":
        a, b = rng.randint(60, 99), rng.randint(60, 99)
        if (a + b) % 2 == 0:
            b += 1
        code = f"a = {a}\nb = {b}\naverage = (a + b) // 2\nprint(average)"
        goal = f"the exact average ({(a + b) / 2})"
        correct = "// rounds down and drops the .5; use / for an exact average"
        wrong = ["// gives the remainder, not the quotient", "The parentheses make Python round up", "a and b have to be floats before adding"]
        why = "`//` is floor division, so it rounds the answer down. Use `/` to keep the decimal part."
    else:
        n = rng.randint(21, 98)
        code = f"number = {n}\nlast_digit = number // 10\nprint(last_digit)"
        goal = f"the last digit of {n} ({n % 10})"
        correct = "// 10 gives the tens; % 10 gives the last digit"
        wrong = ["% 10 gives the tens; // 10 gives the last digit", "/ 10 is needed to get any digit", "number has to be a string to get its digits"]
        why = "`number // 10` removes the last digit. The last digit is the remainder, `number % 10`."
    shown = run_code(code).output
    if len(shown) > 8:
        raise GenerationError("noisy float in the shown output")
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"This should print {goal}, but it prints `{shown}`. What is wrong?",
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=code,
    )


# --------------------------------------------------------------------------
# HARD -- multiple choice (lab-style snippets with a twist or several steps)
# --------------------------------------------------------------------------


def _swap_op_outputs(code: str) -> list:
    """Outputs of ``code`` when the `//` / `%` on ONE line is swapped for the other one."""
    lines = code.split("\n")
    outs = []
    for i, line in enumerate(lines):
        if " // " in line:
            new = line.replace(" // ", " % ", 1)
        elif " % " in line:
            new = line.replace(" % ", " // ", 1)
        else:
            continue
        res = run_code("\n".join([*lines[:i], new, *lines[i + 1:]]))
        if not res.error and res.output.strip():
            outs.append(res.output)
    return outs


@generator(TOPIC, HARD)
def gen_split_units_trace(rng: random.Random) -> Question:
    """Seconds -> hours, minutes, seconds with // and % (the lab-style two-step trace)."""
    kind = rng.choice(["time", "time", "inches", "coins"])
    if kind == "coins":
        cents = rng.randint(41, 99)
        code = (
            f"cents = {cents}\nquarters = cents // 25\ncents = cents % 25\n"
            "dimes = cents // 10\ncents = cents % 10\nprint(quarters, dimes, cents)"
        )
        q, r = divmod(cents, 25)
        d, r2 = divmod(r, 10)
        why = (
            f"{cents} // 25 = {q} quarters, leaving {cents} % 25 = {r}. Then {r} // 10 = {d} dimes, "
            f"leaving {r} % 10 = {r2}. `cents` is reassigned each time."
        )
    else:
        var, (n1, f1), (n2, f2), last, total = (
            ("total_seconds", ("hours", 3600), ("minutes", 60), "seconds", rng.randint(3700, 40000))
            if kind == "time"
            else ("total_inches", ("yards", 36), ("feet", 12), "inches", rng.randint(100, 900))
        )
        code = (
            f"{var} = {total}\n{n1} = {var} // {f1}\nrest = {var} % {f1}\n"
            f"{n2} = rest // {f2}\n{last} = rest % {f2}\nprint({n1}, {n2}, {last})"
        )
        a, rest = divmod(total, f1)
        b, c = divmod(rest, f2)
        why = (
            f"{total} // {f1} = {a} {n1}, and {total} % {f1} = {rest} is left. "
            f"Then {rest} // {f2} = {b} {n2} and {rest} % {f2} = {c} {last}."
        )
    right = run_code(code).output
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[*_swap_op_outputs(code), *_nearby_outputs(right)],
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_digits_trace(rng: random.Random) -> Question:
    """number = 47; tens = number // 10; ones = number % 10; print(ones * 10 + tens)"""
    three = rng.random() < 0.5
    if three:
        digits = [rng.randint(1, 9) for _ in range(3)]
        n = digits[0] * 100 + digits[1] * 10 + digits[2]
        body = "hundreds = number // 100\nrest = number % 100\ntens = rest // 10\nones = rest % 10"
        final = rng.choice(["hundreds + tens + ones", "ones * 100 + tens * 10 + hundreds", "hundreds * tens * ones"])
    else:
        digits = [rng.randint(1, 9), rng.randint(1, 9)]
        n = digits[0] * 10 + digits[1]
        body = "tens = number // 10\nones = number % 10"
        final = rng.choice(["tens + ones", "ones * 10 + tens", "tens * ones"])
    code = f"number = {n}\n{body}\nprint({final})"
    if final.startswith("ones"):
        why = f"The digits of {n} are split with `//` and `%`, then put back in reverse order, which gives `{run_code(code).output}`."
    elif "+" in final:
        why = f"`//` and `%` pull the digits out of {n} ({', '.join(str(d) for d in digits)}), and the line adds them."
    else:
        why = f"`//` and `%` pull the digits out of {n} ({', '.join(str(d) for d in digits)}), and the line multiplies them."
    finals = ["hundreds + tens + ones", "ones * 100 + tens * 10 + hundreds", "hundreds * tens * ones"] if three else ["tens + ones", "ones * 10 + tens", "tens * ones"]
    wrong = [run_code(code.replace(f"print({final})", f"print({f})")).output for f in finals if f != final]
    wrong += _swap_op_outputs(code)
    wrong += _nearby_outputs(run_code(code).output)
    return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, explanation=why, rng=rng)


_HARD_AUG = {
    "/=": [2, 3, 4, 5],
    "//=": [2, 3, 4, 5],
    "%=": [3, 4, 5, 7],
    "**=": [2],
    "+=": [1, 2, 3, 5, 8],
    "-=": [1, 2, 3, 4],
    "*=": [2, 3],
}


@generator(TOPIC, HARD)
def gen_augmented_hard(rng: random.Random) -> Question:
    """value = 20; value /= 4; value += 2; value //= 3; print(value) -> 2.0"""
    var = rng.choice(["value", "total", "score", "money"])

    def build() -> Question:
        start = rng.choice([12, 16, 18, 20, 24, 30, 36, 40, 48])
        steps = []
        for _ in range(4):
            op = rng.choice(list(_HARD_AUG))
            steps.append((op, rng.choice(_HARD_AUG[op])))
        hard_ops = sum(1 for op, _ in steps if op in ("/=", "//=", "%=", "**="))
        if hard_ops < 2 or len({op for op, _ in steps}) < 3 or sum(1 for op, _ in steps if op == "**=") > 1:
            raise GenerationError("not the right mix")
        lines = [f"{var} = {start}"] + [f"{var} {op} {n}" for op, n in steps] + [f"print({var})"]
        code = "\n".join(lines)
        res = run_code(code)
        if res.error or len(res.output) > 8:
            raise GenerationError("ugly")
        value = res.namespace[var]
        seen, v = [start], start
        for op, n in steps:
            v = _ev(f"{v} {op[:-1]} {n}")
            seen.append(v)
        if max(seen) > 999 or min(seen) < 0 or len(res.output) > 5:
            raise GenerationError("numbers too big for a trace")
        if value <= 0 or ("/=" in [op for op, _ in steps] and not isinstance(value, float)):
            raise GenerationError("pick another")
        wrong = []
        if isinstance(value, float) and value == int(value):
            wrong.append(str(int(value)))
        for i, (op, n) in enumerate(steps):
            for other in ("/=", "//=", "%=", "+=", "-=", "*="):
                if other != op:
                    alt = list(lines)
                    alt[i + 1] = f"{var} {other} {n}"
                    r = run_code("\n".join(alt))
                    if not r.error and len(r.output) <= 10:
                        wrong.append(r.output)
        rng.shuffle(wrong)
        first = wrong[:1]
        wrong = first + sorted(wrong[1:], key=lambda t: len(t))
        trace, v = [], start
        for op, n in steps:
            v = _ev(f"{v} {op[:-1]} {n}")
            trace.append(f"`{var} {op} {n}` gives {v}")
        float_note = " `/=` makes the value a float, and it stays a float." if any(op == "/=" for op, _ in steps) else ""
        return output_question(
            topic=TOPIC,
            difficulty=HARD,
            code=code,
            distractors=wrong,
            explanation=f"Starting at {start}: " + ", ".join(trace) + "." + float_note,
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, HARD)
def gen_division_identity(rng: random.Random) -> Question:
    """q = n // d, r = n % d -> n == q * d + r"""
    n = rng.randint(25, 99)
    d = rng.randint(3, 9)
    if n % d == 0:
        n += 1
    setup = f"n = {n}\nd = {d}\nq = n // d\nr = n % d"
    wrong = ["q * r + d", "q + r", "q * d - r", "d * r + q", "q * (d + r)", "(q + d) * r", "q * d * r"]
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="After this code runs, which expression is equal to `n` again?",
        setup=setup,
        target=n,
        correct_expr="q * d + r",
        wrong_exprs=wrong,
        explanation=f"Division with a remainder always satisfies n = (n // d) * d + n % d. Here {n} = {n // d} * {d} + {n % d}.",
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_negative_floor(rng: random.Random) -> Question:
    """a = -7; b = 2; print(a // b) -> -4 (floor means round DOWN)"""

    def build() -> Question:
        a, b = rng.randint(3, 40), rng.randint(2, 7)
        if a % b == 0:
            raise GenerationError("exact")
        if rng.random() < 0.5:
            a = -a
        else:
            b = -b
        code = f"a = {a}\nb = {b}\nprint(a // b)"
        value = a // b
        wrong = [str(int(a / b)), str(a / b), str(abs(value)), str(float(value)), str(value + 1), str(value - 1)]
        return output_question(
            topic=TOPIC,
            difficulty=HARD,
            prompt="`//` is the floor operator: it rounds down, toward negative infinity. What does this print?",
            code=code,
            distractors=wrong,
            explanation=f"{a} / {b} is {a / b}. Floor division rounds that DOWN to the next smaller whole number, `{value}` (not toward zero).",
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, HARD)
def gen_receipt_trace(rng: random.Random) -> Question:
    """price * quantity, add tax, round to 2 decimals -- float results and round()."""

    def build() -> Question:
        price = rng.choice([4.5, 7.25, 12.5, 19.99, 3.75, 24.5, 8.99, 15.0, 2.49])
        quantity = rng.randint(2, 6)
        form = rng.choice(["rate", "tax"])
        subtotal = price * quantity
        if form == "rate":
            rate = rng.choice([1.05, 1.07, 1.08, 1.1])
            code = f"price = {price}\nquantity = {quantity}\nsubtotal = price * quantity\ntotal = round(subtotal * {rate}, 2)\nprint(total)"
            x = subtotal * rate
            swaps = [
                (f"round(subtotal * {rate}, 2)", f"subtotal * {rate}"),
                (f"round(subtotal * {rate}, 2)", "round(subtotal, 2)"),
                (f"round(subtotal * {rate}, 2)", f"round(price * {rate}, 2)"),
                (f"round(subtotal * {rate}, 2)", f"round(subtotal * {rate}, 1)"),
            ]
            why = f"`subtotal` is {_fmt(round(subtotal, 2))}. Times {rate} is about {round(x, 4)}, and `round(..., 2)` keeps 2 decimals: `{round(x, 2)}`."
        else:
            pct = rng.choice([5, 7, 8, 10])
            code = (
                f"price = {price}\nquantity = {quantity}\nsubtotal = price * quantity\n"
                f"tax = subtotal * {pct} / 100\nprint(round(subtotal + tax, 2))"
            )
            x = subtotal + subtotal * pct / 100
            swaps = [
                ("round(subtotal + tax, 2)", "subtotal + tax"),
                ("round(subtotal + tax, 2)", "round(tax, 2)"),
                ("round(subtotal + tax, 2)", "round(subtotal, 2)"),
                ("round(subtotal + tax, 2)", "round(price + tax, 2)"),
            ]
            why = f"`subtotal` is {_fmt(round(subtotal, 2))} and `tax` is {_fmt(round(subtotal * pct / 100, 4))}. Their sum rounded to 2 decimals is `{round(x, 2)}`."
        if abs((x * 100) % 1 - 0.5) < 0.1 or (x * 100) % 1 < 0.04:
            raise GenerationError("too close to a rounding tie")
        wrong = _mutant_outputs(code, swaps)
        return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, explanation=why, rng=rng)

    return _tries(build)


@generator(TOPIC, HARD)
def gen_long_precedence(rng: random.Random) -> Question:
    """x = 3; y = 2; print(x ** y * 4 // 5 + 1) -- several operators, precedence AND left-to-right."""

    def build() -> Question:
        ops = [rng.choice(["+", "-", "*", "//", "%", "**", "*", "//"]) for _ in range(3)]
        if ops.count("**") > 1 or not set(ops) & {"//", "%", "**"}:
            raise GenerationError("not interesting")
        nums = [rng.randint(2, 9) for _ in range(4)]
        if len(set(nums)) < 3:
            raise GenerationError("too many repeated numbers")
        for i, op in enumerate(ops):
            if op == "**":
                nums[i], nums[i + 1] = rng.randint(2, 5), rng.choice([2, 3])
        value = _ev(_expr(nums, ops))
        if not 0 < value < 1000 or value == _ev(_expr_ltr(nums, ops)):
            raise GenerationError("precedence does not matter")
        names = {}
        shown = list(map(str, nums))
        for var, pos in zip("xy", rng.sample(range(4), 2)):
            names[var] = nums[pos]
            shown[pos] = var
        text = shown[0]
        for n, op in zip(shown[1:], ops):
            text += f" {op} {n}"
        code = f"x = {names['x']}\ny = {names['y']}\nprint({text})"
        wrong = _other_results(nums, ops, str(value), maxlen=8)
        return output_question(
            topic=TOPIC,
            difficulty=HARD,
            code=code,
            distractors=wrong,
            explanation=f"{PRECEDENCE_RULE} With the numbers filled in this is `{_expr(nums, ops)}`, which is `{value}`.",
            rng=rng,
        )

    return _tries(build)


# --------------------------------------------------------------------------
# Fill in the blanks (typed; like the quiz's "fill in multiple blanks")
# --------------------------------------------------------------------------

AUG_OPS = ["+=", "-=", "*=", "/=", "//=", "%=", "**="]


def _unique_fill(template: str, choices: list, expect: str, n_blanks: int) -> bool:
    """True if exactly ONE combination of ``choices`` for the blanks prints ``expect``."""
    from itertools import product

    hits = 0
    for combo in product(choices, repeat=n_blanks):
        code = template
        for i, text in enumerate(combo, 1):
            code = code.replace(blank_mark(i), text)
        res = run_code(code)
        if not res.error and res.output.strip() == expect.strip():
            hits += 1
            if hits > 1:
                return False
    return hits == 1


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_operators(rng: random.Random) -> Question:
    """print(10 __ 3)  # 3 -- which operator prints the number in the comment?"""

    def build() -> Question:
        a, b = rng.choice([(10, 3), (10, 3), (17, 5), (20, 6), (9, 4), (14, 4), (25, 7), (12, 5), (30, 8), (8, 3), (21, 4)])
        results = {o: _fmt(_ev(f"{a} {o} {b}")) for o in ALL_OPS}
        tidy = [o for o in ALL_OPS if list(results.values()).count(results[o]) == 1 and len(results[o]) <= 6]
        if len(tidy) < 3:
            raise GenerationError("not enough tidy operators")
        ops = rng.sample(tidy, 3)
        lines = [f"print({a} {blank_mark(i)} {b})   # {results[o]}" for i, o in enumerate(ops, 1)]
        return blanks_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt="Fill in each blank with the operator that makes the line print the number in the comment.",
            template="\n".join(lines),
            blanks=[Blank([o], hint="operator") for o in ops],
            explanation=" ".join(f"`{a} {o} {b}` is `{results[o]}` ({OP_NAMES[o]})." for o in ops),
            expect_output="\n".join(results[o] for o in ops),
        )

    return _tries(build)


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_round_division(rng: random.Random) -> Question:
    """share = 10 __ 3; print(round(share, __))  # 3.33"""

    def build() -> Question:
        a, b = rng.choice([(10, 3), (20, 3), (22, 7), (2, 3), (50, 6), (100, 7), (5, 3), (17, 6), (8, 7)])
        digits = rng.choice([1, 2, 2])
        x = a / b
        if abs((x * 10**digits) % 1 - 0.5) < 0.1:
            raise GenerationError("tie")
        want = _fmt(round(x, digits))
        var = rng.choice(["share", "average", "result", "each"])
        template = f"{var} = {a} {blank_mark(1)} {b}\nprint(round({var}, {blank_mark(2)}))   # {want}"
        return blanks_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt="Fill in the blanks so the code prints the number in the comment.",
            template=template,
            blanks=[Blank(["/"], hint="operator"), Blank([str(digits)], hint="decimal places", mode="expr")],
            explanation=f"`/` gives the exact quotient ({x}) and `round({var}, {digits})` keeps {digits} decimal place{'s' if digits > 1 else ''}: `{want}`.",
            expect_output=want,
        )

    return _tries(build)


_UNIT_SPLITS = [
    ("total_seconds", 60, "minutes", "seconds", (75, 600)),
    ("total_minutes", 60, "hours", "minutes", (75, 500)),
    ("total_days", 7, "weeks", "days", (10, 60)),
    ("total_inches", 12, "feet", "inches", (30, 200)),
    ("cents", 100, "dollars", "cents_left", (105, 999)),
]


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_split_units(rng: random.Random) -> Question:
    """minutes = total_seconds __ 60; seconds = total_seconds __ 60"""
    var, f, big, small, (lo, hi) = rng.choice(_UNIT_SPLITS)
    total = rng.randint(lo, hi)
    if total % f == 0:
        total += 1
    q, r = divmod(total, f)
    template = (
        f"{var} = {total}\n{big} = {var} {blank_mark(1)} {f}\n{small} = {var} {blank_mark(2)} {f}\n"
        f"print({big}, {small})   # {q} {r}"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks to split `{var}` into whole {big} and what is left over.",
        template=template,
        blanks=[Blank(["//"], hint="operator"), Blank(["%"], hint="operator")],
        explanation=f"Whole {big} come from floor division, `{var} // {f}` = {q}. What is left is the remainder, `{var} % {f}` = {r}.",
        expect_output=f"{q} {r}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_augmented(rng: random.Random) -> Question:
    """score = 10; score __ 5; score __ 2; print(score)  # 30"""

    def build() -> Question:
        var = rng.choice(["score", "total", "count", "coins", "money"])
        start = rng.randint(4, 20)
        ops = rng.sample(["+=", "-=", "*=", "+=", "-="], 2)
        nums = [rng.randint(2, 9), rng.randint(2, 5)]
        code = f"{var} = {start}\n" + "\n".join(f"{var} {o} {n}" for o, n in zip(ops, nums)) + f"\nprint({var})"
        res = run_code(code)
        want = res.output
        template = (
            f"{var} = {start}\n{var} {blank_mark(1)} {nums[0]}\n{var} {blank_mark(2)} {nums[1]}\nprint({var})   # {want}"
        )
        if not _unique_fill(template, AUG_OPS, want, 2):
            raise GenerationError("more than one answer")
        return blanks_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt="Fill in the blanks with `+=`, `-=` or `*=` so the code prints the number in the comment.",
            template=template,
            blanks=[Blank([ops[0]], hint="operator"), Blank([ops[1]], hint="operator")],
            explanation=f"Start at {start}: `{var} {ops[0]} {nums[0]}` updates it, then `{var} {ops[1]} {nums[1]}` updates it again, giving {want}.",
            expect_output=want,
        )

    return _tries(build)


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_multiple_check(rng: random.Random) -> Question:
    """if number % 5 == 0: ... -- modulo to detect even/odd and multiples."""
    k = rng.choice([2, 3, 5, 5, 10])
    number = rng.randint(11, 98)
    if k == 2:
        desc, yes, no = "even or odd", "Even", "Odd"
    else:
        desc, yes, no = f"a multiple of {k}", f"Multiple of {k}", "Not a multiple"
    template = (
        f"number = {number}\nif number {blank_mark(1)} {blank_mark(2)} == 0:\n    print(\"{yes}\")\nelse:\n    print(\"{no}\")"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the code prints whether `number` is {desc}.",
        template=template,
        blanks=[Blank(["%"], hint="operator"), Blank([str(k)], hint="number", mode="expr")],
        explanation=f"`number % {k} == 0` is True when dividing by {k} leaves no remainder. Here {number} % {k} is {number % k}, so it prints `{yes if number % k == 0 else no}`.",
        expect_output=yes if number % k == 0 else no,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_formula(rng: random.Random) -> Question:
    """area = pi __ radius __ 2 / interest = principal __ rate __ time __ 100 / Fahrenheit"""

    def build() -> Question:
        which = rng.choice(["circle", "interest", "fahrenheit"])
        if which == "circle":
            r = rng.randint(2, 12)
            head = f"pi = 3.14\nradius = {r}\narea = pi {blank_mark(1)} radius {blank_mark(2)} 2\nprint(area)"
            answers, value, tail = ["*", "**"], _ev(f"3.14 * {r} ** 2"), "The area is pi times radius squared, so `pi * radius ** 2`."
            prompt = "Fill in the blanks to find the area of the circle."
        elif which == "interest":
            p, rate, t = rng.choice([500, 1000, 1200, 2000]), rng.choice([3, 4, 5, 8]), rng.randint(2, 5)
            head = (
                f"principal = {p}\nrate = {rate}\ntime = {t}\n"
                f"interest = principal {blank_mark(1)} rate {blank_mark(2)} time {blank_mark(3)} 100\nprint(interest)"
            )
            answers, value, tail = ["*", "*", "/"], _ev(f"{p} * {rate} * {t} / 100"), "Simple interest is principal times rate times time, divided by 100."
            prompt = "Fill in the blanks to find the simple interest (`rate` is a percent)."
        else:
            c = rng.choice([10, 20, 25, 30, 40, 100])
            head = f"celsius = {c}\nfahrenheit = celsius {blank_mark(1)} 9 {blank_mark(2)} 5 {blank_mark(3)} 32\nprint(fahrenheit)"
            answers, value, tail = ["*", "/", "+"], _ev(f"{c} * 9 / 5 + 32"), "Multiply by 9, divide by 5, then add 32."
            prompt = "Fill in the blanks to convert `celsius` to Fahrenheit."
        want = _fmt(_clean(value))
        template = head + f"   # {want}"
        n = len(answers)
        # (`**` is only tried where it can't run away: 5 ** 3 ** 100 never finishes)
        if not _unique_fill(template, ["+", "-", "*", "/", "//", "%", *(["**"] if which == "circle" else [])], want, n):
            raise GenerationError("more than one answer")
        return blanks_question(
            topic=TOPIC,
            difficulty=HARD,
            prompt=prompt + " It should print the number in the comment.",
            template=template,
            blanks=[Blank([a], hint="operator") for a in answers],
            explanation=tail + f" The result is `{want}`.",
            expect_output=want,
        )

    return _tries(build)


# --------------------------------------------------------------------------
# Matching (like the quiz's "Match each ..." questions)
# --------------------------------------------------------------------------


@generator(TOPIC, EASY, qtype="match")
def gen_match_operator_names(rng: random.Random) -> Question:
    """Match each arithmetic operator to its name."""
    syms = rng.sample(ALL_OPS, 5)
    if "//" not in syms and "%" not in syms:
        syms[0] = rng.choice(["//", "%"])
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each arithmetic operator to its name.",
        pairs=[(s, OP_NAMES[s]) for s in syms],
        explanation="The lesson's operators: `+` addition, `-` subtraction, `*` multiplication, `/` division, `//` floor division, `%` modulus, `**` exponentiation.",
        rng=rng,
        extra_options=[n for s, n in OP_NAMES.items() if s not in syms][:1],
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_expression_results(rng: random.Random) -> Question:
    """Match each expression (same two numbers) to its result."""

    def build() -> Question:
        a, b = rng.choice([(17, 5), (23, 4), (10, 3), (19, 4), (13, 2), (29, 6), (22, 5)])
        pool = []
        for o in ALL_OPS:
            text = _fmt(_ev(f"{a} {o} {b}"))
            if len(text) <= 6:
                pool.append((f"{a} {o} {b}", text))
        if len(pool) < 5 or len({t for _, t in pool}) != len(pool):
            raise GenerationError("not enough tidy results")
        pairs = rng.sample(pool, 5)
        return match_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt="Match each expression to its result.",
            pairs=pairs,
            explanation=f"With {a} and {b}: `//` rounds the quotient down, `%` is the remainder, and `/` always gives a float. " + f"For example `{a} // {b}` is {a // b} and `{a} % {b}` is {a % b}.",
            rng=rng,
        )

    return _tries(build)


_STORIES = [
    ("How many FULL boxes fit?", "//"),
    ("How many items are LEFT OVER?", "%"),
    ("Exact share, decimals allowed", "/"),
    ("Square of the side length", "**"),
    ("Total cost of equal-priced items", "*"),
    ("Price plus a fee", "+"),
    ("Points left after a penalty", "-"),
    ("Whole minutes in some seconds", "//"),
    ("Seconds left after the whole minutes", "%"),
    ("Is a number even? Check the remainder", "%"),
    ("Cube of the side length", "**"),
    ("Last digit of a number", "%"),
]


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_story_operator(rng: random.Random) -> Question:
    """Match each little job to the operator that does it."""

    def build() -> Question:
        pairs = rng.sample(_STORIES, 5)
        if len({o for _, o in pairs}) < 4:
            raise GenerationError("too few distinct operators")
        return match_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            prompt="Match each job to the operator that does it.",
            pairs=pairs,
            explanation="`//` counts whole groups, `%` gives what is left over, `/` is an exact (float) quotient, `**` is a power, `*` repeated addition.",
            rng=rng,
        )

    return _tries(build)


@generator(TOPIC, HARD, qtype="match")
def gen_match_precedence(rng: random.Random) -> Question:
    """The same numbers with and without parentheses: match each to its result."""

    def build() -> Question:
        pairs = []
        used = set()
        for _ in range(2):
            ops = [rng.choice(["+", "-", "*", "//", "%", "**"]) for _ in range(2)]
            nums = [rng.randint(2, 9) for _ in range(3)]
            for i, op in enumerate(ops):
                if op == "**":
                    nums[i], nums[i + 1] = rng.randint(2, 5), rng.choice([2, 3])
            plain = _expr(nums, ops)
            grouped = f"({nums[0]} {ops[0]} {nums[1]}) {ops[1]} {nums[2]}"
            for e in (plain, grouped):
                v = _fmt(_clean(_ev(e)))
                if v in used:
                    raise GenerationError("duplicate result")
                used.add(v)
                pairs.append((e, v))
        if len(pairs) != 4 or pairs[0][0] == pairs[1][0]:
            raise GenerationError("no parentheses effect")
        return match_question(
            topic=TOPIC,
            difficulty=HARD,
            prompt="Match each expression to its result. Watch the order of operations.",
            pairs=pairs,
            explanation=PRECEDENCE_RULE,
            rng=rng,
        )

    return _tries(build)


# --------------------------------------------------------------------------
# Write the code (typed, graded in the sandbox against hidden tests)
# --------------------------------------------------------------------------


def _ev_vars(expr: str, variables: dict):
    return eval(expr, {"__builtins__": {}, "round": round}, dict(variables))  # noqa: S307 - trusted


def _distinct(rng: random.Random, make, count: int, tries: int = 60) -> list:
    """``count`` items from ``make()`` with different expected values (last element of each)."""
    out, seen = [], set()
    for _ in range(tries):
        item = make()
        key = repr(item[-1])
        if key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) == count:
            return out
    raise GenerationError("could not find enough different cases")


@generator(TOPIC, EASY, qtype="code")
def gen_code_expr_operator(rng: random.Random) -> Question:
    """Type an expression: remainder / whole-number quotient / float quotient / square / last digit."""
    kind = rng.choice(["remainder", "floor", "quotient", "square", "cube", "last_digit", "rest_digits"])
    a, b = rng.choice([("total", "groups"), ("cookies", "kids"), ("score", "team_size"), ("coins", "friends"), ("points", "players")])
    if kind in ("remainder", "floor", "quotient"):
        if kind == "remainder":
            sol = f"{a} % {b}"
            prompt = f"`{a}` and `{b}` hold whole numbers. Type an expression that gives the remainder when `{a}` is divided by `{b}`."
            why = f"`%` (modulus) is the remainder: `{sol}`."
        elif kind == "floor":
            sol = f"{a} // {b}"
            prompt = f"`{a}` and `{b}` hold whole numbers. Type an expression that gives how many whole times `{b}` fits into `{a}`."
            why = f"`//` (floor division) divides and rounds down: `{sol}`."
        else:
            sol = f"{a} / {b}"
            prompt = f"`{a}` and `{b}` hold whole numbers. Type an expression that gives `{a}` divided by `{b}` as a float."
            why = f"`/` always gives a float, even for an even split: `{sol}`."

        def make():
            y = rng.randint(2, 9)
            x = rng.randint(12, 95)
            if kind == "quotient" and rng.random() < 0.4:
                x = y * rng.randint(3, 12)
            return ({a: x, b: y}, _ev_vars(sol, {a: x, b: y}))

        cases = _distinct(rng, make, 5)
        if kind == "quotient":
            cases[0] = ({a: 12, b: 4}, 3.0)  # an even split must still be a float
        task = expression_task(sol, cases)
    else:
        v = rng.choice(["number", "n", "side", "num"])
        if kind == "square":
            sol, prompt, why = f"{v} ** 2", f"`{v}` holds a whole number. Type an expression that gives its square (the number times itself).", f"The square is the number to the power of 2: `{v} ** 2`."
            pool = [3, 4, 5, 6, 7, 9, 10, 12]
        elif kind == "cube":
            sol, prompt, why = f"{v} ** 3", f"`{v}` holds a whole number. Type an expression that gives its cube (the number to the power of 3).", f"The cube is `{v} ** 3`."
            pool = [2, 3, 4, 5, 6, 7, 10]
        elif kind == "last_digit":
            sol, prompt, why = f"{v} % 10", f"`{v}` holds a whole number such as `472`. Type an expression that gives its last digit (`2`).", f"Dividing by 10 leaves the last digit as the remainder: `{v} % 10`."
            pool = [472, 85, 1907, 36, 250, 9, 7351]
        else:
            sol, prompt, why = f"{v} // 10", f"`{v}` holds a whole number such as `472`. Type an expression that gives the number without its last digit (`47`).", f"Floor division by 10 drops the last digit: `{v} // 10`."
            pool = [472, 85, 1907, 36, 250, 99, 7351]
        cases = [({v: x}, _ev_vars(sol, {v: x})) for x in rng.sample(pool, 4)]
        task = expression_task(sol, cases)
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=task, explanation=why)


@generator(TOPIC, EASY, qtype="code")
def gen_code_expr_condition(rng: random.Random) -> Question:
    """Type a condition that is True for even / odd / multiples of k (modulo)."""
    v = rng.choice(["number", "n", "num", "score", "count"])
    kind = rng.choice(["even", "odd", "multiple", "multiple"])
    if kind == "even":
        sol, k = f"{v} % 2 == 0", 2
        prompt = f"`{v}` holds a whole number. Type a condition that is `True` when `{v}` is even and `False` when it is odd."
    elif kind == "odd":
        sol, k = f"{v} % 2 == 1", 2
        prompt = f"`{v}` holds a whole number. Type a condition that is `True` when `{v}` is odd and `False` when it is even."
    else:
        k = rng.choice([3, 4, 5, 5, 10])
        sol = f"{v} % {k} == 0"
        prompt = f"`{v}` holds a whole number. Type a condition that is `True` when `{v}` is a multiple of {k}."
    values = set()
    while len(values) < 6:
        values.add(rng.randint(1, 60))
    values = sorted(values)
    if len({_ev_vars(sol, {v: x}) for x in values}) < 2:
        values[0] = k * rng.randint(1, 9)
        values[1] = k * rng.randint(10, 20) + 1
    cases = [({v: x}, _ev_vars(sol, {v: x})) for x in values]
    if kind == "even":
        why = "An even number leaves remainder 0 when divided by 2: `n % 2 == 0`. Use `==` to compare, not `=`.".replace("n %", f"{v} %")
    elif kind == "odd":
        why = "An odd number leaves remainder 1 when divided by 2: `n % 2 == 1`. Use `==` to compare, not `=`.".replace("n %", f"{v} %")
    else:
        why = f"A multiple of {k} leaves remainder 0 when divided by {k}: `{sol}`. Use `==` to compare, not `=`."
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=expression_task(sol, cases), explanation=why)


@generator(TOPIC, EASY, qtype="code")
def gen_code_expr_formula(rng: random.Random) -> Question:
    """Type an expression for an average / percent / perimeter / conversion (precedence matters)."""
    kind = rng.choice(["average2", "average3", "percent", "perimeter", "fahrenheit", "discount", "triangle", "bmi", "tip"])

    def rnd(lo, hi):
        return rng.randint(lo, hi)

    def build(variables: dict):
        return (variables, _ev_vars(sol, variables))

    if kind == "average2":
        sol = "(a + b) / 2"
        prompt = "`a` and `b` hold numbers. Type an expression that gives their average."
        why = "Add first (parentheses!), then divide by 2: `(a + b) / 2`. Without parentheses only `b` would be halved."
        cases = _distinct(rng, lambda: build({"a": rnd(50, 100), "b": rnd(50, 100)}), 4)
        cases[0] = build({"a": 85, "b": 90})
    elif kind == "average3":
        sol = "(a + b + c) / 3"
        prompt = "`a`, `b` and `c` hold numbers. Type an expression that gives their average."
        why = "Add all three inside parentheses, then divide by 3: `(a + b + c) / 3`."
        cases = _distinct(rng, lambda: build({"a": rnd(50, 100), "b": rnd(50, 100), "c": rnd(50, 100)}), 4)
    elif kind == "percent":
        sol = "score / total * 100"
        prompt = "`score` and `total` hold whole numbers. Type an expression that gives the score as a percent of the total (for example `18` out of `24` is `75.0`)."
        why = "Divide the score by the total, then multiply by 100: `score / total * 100`."

        def make():
            t = rng.choice([20, 25, 40, 50, 80, 24, 30])
            return build({"score": rnd(t // 3, t), "total": t})

        cases = _distinct(rng, make, 4)
    elif kind == "perimeter":
        sol = "2 * (length + width)"
        prompt = "`length` and `width` hold whole numbers. Type an expression that gives the perimeter of the rectangle."
        why = "Both sides are added, then doubled: `2 * (length + width)`. The parentheses matter."
        cases = _distinct(rng, lambda: build({"length": rnd(3, 20), "width": rnd(2, 15)}), 4)
    elif kind == "fahrenheit":
        sol = "celsius * 9 / 5 + 32"
        prompt = "`celsius` holds a whole number. Type an expression that converts it to Fahrenheit (multiply by 9, divide by 5, add 32)."
        why = "`*` and `/` run left to right before the `+`: `celsius * 9 / 5 + 32`."
        cases = [build({"celsius": c}) for c in rng.sample([0, 10, 20, 25, 30, 37, 40, 100, -10], 4)]
    elif kind == "discount":
        sol = "price - price * discount / 100"
        prompt = "`price` and `discount` hold numbers (`discount` is a percent). Type an expression for the price after the discount."
        why = "The discount amount is `price * discount / 100`; subtract it from `price`."
        cases = _distinct(rng, lambda: build({"price": rng.choice([20, 40, 50, 60, 80, 120, 200]), "discount": rng.choice([10, 15, 20, 25, 50])}), 4)
    elif kind == "triangle":
        sol = "base * height / 2"
        prompt = "`base` and `height` hold whole numbers. Type an expression that gives the area of the triangle (base times height, divided by 2)."
        why = "`base * height / 2` multiplies first, then halves. `/` always gives a float, so a 3 by 4 triangle is `6.0`."
        cases = _distinct(rng, lambda: build({"base": rnd(3, 15), "height": rnd(2, 12)}), 4)
    elif kind == "bmi":
        sol = "weight / height_m ** 2"
        prompt = "`weight` (kg) and `height_m` (meters) hold numbers. Type an expression for the BMI: the weight divided by the height squared."
        why = "`**` runs before `/`, so `weight / height_m ** 2` squares only the height. Without it you would divide by the height once."
        cases = _distinct(rng, lambda: build({"weight": rng.choice([50, 60, 72, 80, 90]), "height_m": rng.choice([1.5, 1.6, 1.8, 2.0, 1.75])}), 4)
    else:
        sol = "bill + bill * tip / 100"
        prompt = "`bill` and `tip` hold numbers (`tip` is a percent). Type an expression for the bill plus the tip."
        why = "The tip amount is `bill * tip / 100`; add it to `bill`."
        cases = _distinct(rng, lambda: build({"bill": rng.choice([20, 40, 50, 60, 80, 120]), "tip": rng.choice([10, 15, 20, 25])}), 4)
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=expression_task(sol, cases), explanation=why)


@generator(TOPIC, EASY, qtype="code")
def gen_code_prog_add(rng: random.Random) -> Question:
    """Bingo: add two numbers and print the result (input, cast, arithmetic)."""
    kind = rng.choice(["sum", "sum", "product", "difference", "float_sum", "average"])
    v1, v2 = rng.choice([("a", "b"), ("first", "second"), ("x", "y"), ("num1", "num2")])
    cast = "float" if kind in ("float_sum", "average") else "int"
    expr, noun = {
        "sum": (f"{v1} + {v2}", "sum"),
        "float_sum": (f"{v1} + {v2}", "sum"),
        "product": (f"{v1} * {v2}", "product"),
        "difference": (f"{v1} - {v2}", "difference (the first number minus the second)"),
        "average": (f"({v1} + {v2}) / 2", "average"),
    }[kind]
    solution = f"{v1} = {cast}(input())\n{v2} = {cast}(input())\nprint({expr})"
    if cast == "int":
        pairs = [(3, 4), (10, 25), (0, 7), (12, 5)] if kind != "difference" else [(9, 4), (10, 25), (7, 0), (12, 5)]
        pairs = [(x + rng.randint(0, 4), y + rng.randint(0, 3)) for x, y in pairs]
    else:
        pairs = [(2.5, 1.25), (3, 4), (0.5, 0.25), (10, 2.5)]
    conv = float if cast == "float" else int
    cases = [Case(stdin=[str(x), str(y)], out=str(_ev_vars(expr, {v1: conv(x), v2: conv(y)}))) for x, y in pairs]
    kind_word = "whole numbers (`int`s)" if cast == "int" else "numbers that may have decimals (`float`s)"
    prompt = f"Write a program that asks for two {kind_word}, one after the other, and prints their {noun}. Print just the number."
    why = f"`input()` gives strings, so cast both with `{cast}()` before doing math, then print `{expr}`."
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why)


# ---- functions (Medium) -----------------------------------------------------


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fn_circle(rng: random.Random) -> Question:
    """Bingo: area of a circle from a radius (and the circumference)."""
    pi = rng.choice(["3.14", "3.14", "3.14159"])
    param = rng.choice(["radius", "radius", "r"])
    if rng.random() < 0.65:
        name = rng.choice(["circle_area", "area_of_circle"])
        solution = f"def {name}({param}):\n    return {pi} * {param} ** 2"
        what, why = "area", f"The area is pi times the radius squared: `{pi} * {param} ** 2`."
        formula = lambda r: float(pi) * r ** 2  # noqa: E731
    else:
        name = rng.choice(["circumference", "circle_circumference"])
        solution = f"def {name}({param}):\n    return 2 * {pi} * {param}"
        what, why = "circumference", f"The circumference is 2 times pi times the radius: `2 * {pi} * {param}`."
        formula = lambda r: 2 * float(pi) * r  # noqa: E731
    radii = [1, 2, 5, 10, 3.5, 0.5, 7]
    cases = [((r,), round(formula(r), 10)) for r in rng.sample(radii, 5)]
    task = function_task(name, solution, cases)
    prompt = f"Write a function `{name}({param})` that returns the {what} of a circle with that radius. Use `{pi}` for pi (no imports needed)."
    return code_question(topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=task, explanation=why + " Remember `return`, not `print`.")


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fn_interest(rng: random.Random) -> Question:
    """Bingo: simple interest for principal, rate, time."""
    name = rng.choice(["simple_interest", "interest", "calc_interest"])
    p, r, t = rng.choice([("principal", "rate", "time"), ("principal", "rate", "years"), ("money", "rate", "years")])
    percent = rng.random() < 0.7
    if percent:
        solution = f"def {name}({p}, {r}, {t}):\n    return {p} * {r} * {t} / 100"
        note = f"`{r}` is a percent, so `5` means 5%."
        data = [(1000, 5, 2), (2500, 4, 3), (1250, 3, 1), (800, 6.5, 2), (999, 5, 1), (1200, 8, 5)]
        calc = lambda a, b, c: a * b * c / 100  # noqa: E731
        why = f"Simple interest is `{p} * {r} * {t} / 100` because the rate is a percent."
    else:
        solution = f"def {name}({p}, {r}, {t}):\n    return {p} * {r} * {t}"
        note = f"`{r}` is a decimal, so `0.05` means 5%."
        data = [(1000, 0.05, 2), (2500, 0.04, 3), (1250, 0.03, 1), (800, 0.065, 2), (2000, 0.5, 4), (1200, 0.08, 5)]
        calc = lambda a, b, c: a * b * c  # noqa: E731
        why = f"Simple interest is just `{p} * {r} * {t}` when the rate is already a decimal."
    cases = [((a, b, c), round(calc(a, b, c), 6)) for a, b, c in rng.sample(data, 5)]
    cases = [(args, float(exp)) for args, exp in cases]
    task = function_task(name, solution, cases)
    prompt = f"Write a function `{name}({p}, {r}, {t})` that returns the simple interest earned: {p} times {r} times {t}{' divided by 100' if percent else ''}. {note}"
    return code_question(topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=task, explanation=why)


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fn_multiple(rng: random.Random) -> Question:
    """Bingo: modulo to detect multiples of 5 / is_even(n)."""
    k, name = rng.choice(
        [(2, "is_even"), (5, "is_multiple_of_five"), (3, "is_multiple_of_three"), (10, "ends_in_zero"), (4, "is_divisible_by_four"), (5, "is_multiple_of_5")]
    )
    param = rng.choice(["n", "number", "num"])
    odd = k == 2 and rng.random() < 0.3
    if odd:
        name = "is_odd"
        solution = f"def {name}({param}):\n    return {param} % 2 == 1"
        what = "odd"
    else:
        solution = f"def {name}({param}):\n    return {param} % {k} == 0"
        what = "even" if k == 2 else f"a multiple of {k}" if name != "ends_in_zero" else "a multiple of 10 (it ends in 0)"
    values = set()
    while len(values) < 7:
        values.add(rng.randint(1, 80))
    values = sorted(values)
    values[0], values[1] = k * rng.randint(1, 5), k * rng.randint(6, 12)
    values[2] = k * rng.randint(13, 20) + 1
    values = sorted(set(values))
    cases = [((v,), (v % 2 == 1) if odd else (v % k == 0)) for v in values]
    task = function_task(name, solution, cases)
    prompt = f"Write a function `{name}({param})` that returns `True` if `{param}` is {what}, otherwise `False`."
    why = f"Use the remainder: `{param} % {2 if odd else k} == {1 if odd else 0}` is already `True` or `False`, so you can return it directly."
    return code_question(topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=task, explanation=why)


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fn_money(rng: random.Random) -> Question:
    """Total with tax / sale price, rounded to 2 decimals (round + percent)."""

    def build() -> Question:
        tax = rng.random() < 0.6
        p2 = rng.choice(["tax_percent", "tax_rate", "percent"]) if tax else rng.choice(["percent_off", "discount", "percent"])
        name = rng.choice(["total_with_tax", "price_with_tax", "final_price"]) if tax else rng.choice(["sale_price", "discounted_price"])
        if tax:
            solution = f"def {name}(price, {p2}):\n    return round(price + price * {p2} / 100, 2)"
            alts = [lambda p, t: round(p * (1 + t / 100), 2), lambda p, t: round(p + p * t * 0.01, 2)]
            prompt = f"Write a function `{name}(price, {p2})` that returns the price plus tax, rounded to 2 decimal places. `{p2}` is a percent (`8` means 8%)."
            why = f"Tax is `price * {p2} / 100`; add it to `price` and wrap everything in `round(..., 2)`."
            main = lambda p, t: round(p + p * t / 100, 2)  # noqa: E731
        else:
            solution = f"def {name}(price, {p2}):\n    return round(price - price * {p2} / 100, 2)"
            alts = [lambda p, t: round(p * (1 - t / 100), 2), lambda p, t: round(p - p * t * 0.01, 2)]
            prompt = f"Write a function `{name}(price, {p2})` that returns the price after taking `{p2}` percent off, rounded to 2 decimal places."
            why = f"The discount is `price * {p2} / 100`; subtract it from `price` and wrap everything in `round(..., 2)`."
            main = lambda p, t: round(p - p * t / 100, 2)  # noqa: E731
        cases = []
        for _ in range(40):
            p = round(rng.choice([9.99, 14.5, 19.99, 24.0, 35.25, 49.99, 5.0, 12.75, 60.0, 7.49]), 2)
            t = rng.choice([5, 6, 7, 8, 10, 15, 20, 25])
            exact = p + p * t / 100 if tax else p - p * t / 100
            if abs((exact * 100) % 1 - 0.5) < 0.12:
                continue
            if any(f(p, t) != main(p, t) for f in alts):
                continue
            if (p, t) not in [c[0] for c in cases]:
                cases.append(((p, t), main(p, t)))
            if len(cases) == 5:
                break
        if len(cases) < 5:
            raise GenerationError("not enough safe cases")
        return code_question(topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=function_task(name, solution, cases), explanation=why)

    return _tries(build)


# ---- programs and a Hard function ---------------------------------------------


@generator(TOPIC, HARD, qtype="code")
def gen_code_prog_split(rng: random.Random) -> Question:
    """Ask for a total and print whole units + leftover (// and %)."""
    big, small, f, unit_in, big_word, small_word = rng.choice(
        [
            ("min", "sec", 60, "seconds", "minutes", "seconds"),
            ("hr", "min", 60, "minutes", "hours", "minutes"),
            ("weeks", "days", 7, "days", "weeks", "days"),
            ("ft", "in", 12, "inches", "feet", "inches"),
        ]
    )
    var = f"total_{unit_in}"
    solution = f"{var} = int(input())\nprint({var} // {f}, \"{big}\", {var} % {f}, \"{small}\")"
    totals = [rng.randint(f + 5, 8 * f) for _ in range(2)] + [f - 1, f, 50 * f + rng.randint(1, f - 1)]
    cases = []
    for t in dict.fromkeys(totals):
        cases.append(Case(stdin=[str(t)], out=f"{t // f} {big} {t % f} {small}"))
    ex = cases[0].out
    prompt = (
        f"Write a program that asks for a number of {unit_in} (an `int`) and prints it as whole {big_word} and leftover {small_word}, "
        f"like `{ex}`."
    )
    why = f"`input()` gives a string, so cast it with `int()`. The whole {big_word} are `{var} // {f}` and the leftover {small_word} are `{var} % {f}`."
    return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why)


@generator(TOPIC, HARD, qtype="code")
def gen_code_prog_coins(rng: random.Random) -> Question:
    """Make change: how many of each coin (floor division, then remainder)."""
    names, values, unit = rng.choice(
        [
            (["Quarters", "Dimes", "Nickels", "Pennies"], [25, 10, 5, 1], "cents"),
            (["Quarters", "Dimes", "Pennies"], [25, 10, 1], "cents"),
            (["Gold", "Silver", "Copper"], [100, 10, 1], "coins"),
            (["Twenties", "Tens", "Fives", "Ones"], [20, 10, 5, 1], "dollars"),
            (["Tens", "Fives", "Ones"], [10, 5, 1], "dollars"),
        ]
    )
    lines = ["amount = int(input())"]
    for nm, val in zip(names[:-1], values[:-1]):
        lines.append(f"{nm.lower()} = amount // {val}")
        lines.append(f"amount = amount % {val}")
    lines.append(f"{names[-1].lower()} = amount")
    for nm in names:
        lines.append(f'print("{nm}:", {nm.lower()})')
    solution = "\n".join(lines)

    def split(n):
        out = []
        for val in values:
            out.append(n // val)
            n %= val
        return out

    amounts = [rng.randint(60, 99), rng.randint(3, 9), values[0] * 2, 0, rng.randint(120, 480)]
    cases = [Case(stdin=[str(n)], out="\n".join(f"{nm}: {c}" for nm, c in zip(names, split(n)))) for n in dict.fromkeys(amounts)]
    prompt = (
        f"Write a program that asks for an amount in {unit} (an `int`) and prints how many "
        + ", ".join(f"{nm.lower()} ({v})" for nm, v in zip(names, values))
        + f" make it, using as few as possible. Print one line per kind, exactly like `{names[0]}: {split(amounts[0])[0]}`."
    )
    why = "Work from the biggest value down: `//` counts the whole coins, then `%` keeps what is left for the smaller ones."
    return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why)


@generator(TOPIC, HARD, qtype="code")
def gen_code_prog_digits(rng: random.Random) -> Question:
    """Pull the digits out of a whole number with // and %."""
    kind = rng.choice(["sum2", "sum3", "tens_ones", "product2", "reverse2", "last_rest"])
    two = [47, 85, 19, 36, 66, 31, 58, 72, 94, 23]
    if kind == "sum2":
        solution = "number = int(input())\ntens = number // 10\nones = number % 10\nprint(tens + ones)"
        cases = [Case(stdin=[str(n)], out=str(n // 10 + n % 10)) for n in [47, *rng.sample(two[1:] + [90, 10], 3)]]
        prompt = "Write a program that asks for a two-digit number (an `int`) and prints the sum of its digits. For `47` print `11`."
        why = "`number // 10` is the tens digit and `number % 10` is the ones digit. Add them."
    elif kind == "sum3":
        solution = "number = int(input())\nhundreds = number // 100\nrest = number % 100\ntens = rest // 10\nones = rest % 10\nprint(hundreds + tens + ones)"
        nums = [123, *rng.sample([507, 999, 100, 482, 360, 745, 218, 641], 3)]
        cases = [Case(stdin=[str(n)], out=str(sum(int(c) for c in str(n)))) for n in nums]
        prompt = "Write a program that asks for a three-digit number (an `int`) and prints the sum of its digits. For `123` print `6`."
        why = "`number // 100` is the hundreds digit; `number % 100` is the rest, which you split with `// 10` and `% 10`."
    elif kind == "tens_ones":
        solution = "number = int(input())\nprint(\"Tens:\", number // 10)\nprint(\"Ones:\", number % 10)"
        cases = [Case(stdin=[str(n)], out=f"Tens: {n // 10}\nOnes: {n % 10}") for n in [47, *rng.sample(two[1:] + [90], 3)]]
        prompt = "Write a program that asks for a two-digit number (an `int`) and prints its tens digit and its ones digit, one per line, like `Tens: 4` then `Ones: 7` for `47`."
        why = "`number // 10` is the tens digit and `number % 10` is the ones digit."
    elif kind == "product2":
        solution = "number = int(input())\ntens = number // 10\nones = number % 10\nprint(tens * ones)"
        cases = [Case(stdin=[str(n)], out=str(n // 10 * (n % 10))) for n in [47, *rng.sample(two[1:] + [90, 10], 3)]]
        prompt = "Write a program that asks for a two-digit number (an `int`) and prints the product of its digits. For `47` print `28`."
        why = "Get the digits with `number // 10` and `number % 10`, then multiply them."
    elif kind == "reverse2":
        solution = "number = int(input())\ntens = number // 10\nones = number % 10\nprint(ones * 10 + tens)"
        pool = [n for n in two if n % 10 != 0]
        cases = [Case(stdin=[str(n)], out=str(n % 10 * 10 + n // 10)) for n in [47, *rng.sample([n for n in pool if n != 47], 3)]]
        prompt = "Write a program that asks for a two-digit number (an `int`, no digit is 0) and prints it with the digits swapped. For `47` print `74`."
        why = "Pull the digits out with `// 10` and `% 10`, then rebuild the number the other way round: `ones * 10 + tens`."
    else:
        solution = "number = int(input())\nprint(\"Last digit:\", number % 10)\nprint(\"The rest:\", number // 10)"
        nums = [472, *rng.sample([85, 1907, 36, 250, 9, 7351, 618], 3)]
        cases = [Case(stdin=[str(n)], out=f"Last digit: {n % 10}\nThe rest: {n // 10}") for n in nums]
        prompt = "Write a program that asks for a whole number (an `int`) and prints its last digit, then the number without its last digit, like `Last digit: 2` then `The rest: 47` for `472`."
        why = "The last digit is the remainder when you divide by 10 (`number % 10`); the rest is `number // 10`."
    return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why)


@generator(TOPIC, HARD, qtype="code")
def gen_code_prog_split_bill(rng: random.Random) -> Question:
    """Several inputs, floats, a formula and round(): split a bill with a tip."""

    def build() -> Question:
        solution = (
            "bill = float(input())\ntip_percent = int(input())\npeople = int(input())\n"
            "total = bill + bill * tip_percent / 100\nprint(\"Each pays:\", round(total / people, 2))"
        )
        cases = []
        for _ in range(60):
            bill = rng.choice([45.5, 60.0, 82.4, 120.0, 37.8, 95.25, 150.0, 28.4, 64.0, 73.5])
            tip = rng.choice([10, 15, 18, 20])
            people = rng.choice([2, 3, 4, 5, 6])
            exact = (bill + bill * tip / 100) / people
            shown = round(exact, 2)
            alt1 = round(bill * (1 + tip / 100) / people, 2)
            alt2 = round((bill + bill * tip / 100) / people, 2)
            if len({shown, alt1, alt2}) > 1 or abs((exact * 100) % 1 - 0.5) < 0.12:
                continue
            if f"{shown:.2f}" != str(shown):
                continue  # keep outputs with two real decimals so round() and :.2f agree
            if all(c.stdin != [str(bill), str(tip), str(people)] for c in cases):
                cases.append(Case(stdin=[str(bill), str(tip), str(people)], out=f"Each pays: {shown}"))
            if len(cases) == 4:
                break
        if len(cases) < 4:
            raise GenerationError("not enough clean cases")
        prompt = (
            "Write a program that asks for the bill (a `float`), the tip percent (an `int`) and the number of people (an `int`), in that order. "
            f"Print `Each pays:` and the tip-included share per person, rounded to 2 decimal places, like `{cases[0].out}`."
        )
        why = "Cast each `input()`, add the tip (`bill * tip_percent / 100`) to the bill, divide by the people and wrap the share in `round(..., 2)`."
        return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why)

    return _tries(build)


@generator(TOPIC, HARD, qtype="code")
def gen_code_fn_boxes(rng: random.Random) -> Question:
    """How many containers are needed? (round UP with // and %)"""
    name, p1, p2, thing = rng.choice(
        [
            ("boxes_needed", "items", "per_box", "boxes"),
            ("buses_needed", "students", "seats", "buses"),
            ("pages_needed", "words", "per_page", "pages"),
            ("tables_needed", "guests", "per_table", "tables"),
        ]
    )
    solution = f"def {name}({p1}, {p2}):\n    full = {p1} // {p2}\n    if {p1} % {p2} != 0:\n        full += 1\n    return full"
    k = rng.choice([4, 5, 6, 8, 10])
    data = [(k * 2, k), (k * 2 + 1, k), (1, k), (0, k), (k * 3 - 1, k), (k * 5, k), (k + 1, k)]
    cases = [((a, b), -(-a // b)) for a, b in data]
    task = function_task(name, solution, cases)
    prompt = (
        f"Write a function `{name}({p1}, {p2})` that returns how many {thing} are needed to hold `{p1}` when each holds `{p2}`. "
        f"A partly filled one still counts: `{name}({k * 2 + 1}, {k})` is `3`."
    )
    why = f"`{p1} // {p2}` counts the full {thing}; if `{p1} % {p2}` is not 0 there is a leftover, so add one more."
    return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=task, explanation=why)
