"""Question generators for the "casting" topic (CSF.2.C: Python Casting).

SEED VERSION: a handful of questions, one per format, showing the patterns.  The casting
topic author expands this to the full set described in the authoring guide.
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
    fn_cases,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "casting"


# ---- choice, concept style (copies the Canvas quiz wording) -----------------
@generator(TOPIC, EASY)
def gen_input_returns(rng: random.Random) -> Question:
    """'What does input() return (before any casting)?'"""
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="What does `input()` return (before any casting)?",
        correct="str",
        distractors=["int", "float", "bool"],
        explanation="`input()` always returns a string, even if the user types digits. Cast it with `int()` or `float()` before doing math.",
        rng=rng,
    )


# ---- choice, "what does this print" (verified by running the snippet) --------
@generator(TOPIC, MEDIUM)
def gen_cast_print(rng: random.Random) -> Question:
    x = rng.choice([2.8, 3.9, 7.2, 9.5])
    code = f"x = int({x})\nprint(x, type(x))"
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[f"{x} <class 'float'>", f"{round(x)} <class 'int'>", f"{int(x)} <class 'str'>", "ValueError"],
        explanation=f"`int({x})` cuts off the decimal part (it does not round), so the result is `{int(x)}` and its type is `int`.",
        rng=rng,
    )


# ---- blanks (typed) -----------------------------------------------------------
@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_cast(rng: random.Random) -> Question:
    n = rng.choice(["42", "7", "100"])
    template = f'text = "{n}"\nnumber = {blank_mark(1)}(text)\nprint(number + 1)'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Fill in the blank so the code prints a number one bigger than the text.",
        template=template,
        blanks=[Blank(["int"], hint="function")],
        explanation="`int(text)` turns the string into a whole number, so `+ 1` is real addition.",
        expect_output=str(int(n) + 1),
    )


# ---- match (clicks) -------------------------------------------------------------
@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_truthiness(rng: random.Random) -> Question:
    pairs = [("0", "False"), ('""', "False"), ("None", "False"), ('"hi"', "True"), ("[]", "False"), ("[0]", "True")]
    pairs = rng.sample(pairs, 5)
    if len({a for _, a in pairs}) < 2:
        raise GenerationError("need both answers")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each value to what `bool(value)` gives.",
        pairs=pairs,
        explanation="Empty things and zero are `False`; everything else is `True`.",
        rng=rng,
    )


# ---- code: expression ------------------------------------------------------------
@generator(TOPIC, EASY, qtype="code")
def gen_code_cast_expr(rng: random.Random) -> Question:
    var = rng.choice(["user_num", "answer", "text"])
    cases = [({var: str(v)}, float(v)) for v in rng.sample(range(2, 40), 4)]
    task = expression_task(f"float({var})", cases, starter="")
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds text such as `\"3\"`. Type an expression that gives it as a float.",
        task=task,
        explanation=f"`float({var})` converts the string to a decimal number.",
    )


# ---- code: function ----------------------------------------------------------------
@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_double(rng: random.Random) -> Question:
    solution = "def double_it(text):\n    return float(text) * 2"
    vals = ["2", "3.5", "10", "0.25", "7"]
    task = function_task("double_it", solution, fn_cases([((v,), float(v) * 2) for v in vals]))
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Write a function `double_it(text)` that casts `text` to a float and returns double its value.",
        task=task,
        explanation="Cast first with `float(text)`, then multiply by 2. Use `return` (not `print`).",
    )


# ---- code: program with input() ------------------------------------------------------
@generator(TOPIC, HARD, qtype="code")
def gen_code_double_program(rng: random.Random) -> Question:
    solution = 'n = input("Enter a number: ")\nn = float(n)\nprint("Double:", n * 2)'
    cases = [Case(stdin=[s], out=f"Double: {float(s) * 2}") for s in ["4", "2.5", "10", "0.5"]]
    task = program_task(solution, cases, starter='n = input("Enter a number: ")\n')
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Write a program that asks the user for a number, casts it to `float`, and prints `Double: ` followed by double its value.",
        task=task,
        explanation="`input()` gives a string, so cast with `float()` before multiplying. `print(\"Double:\", n * 2)` joins the pieces with a space.",
    )
