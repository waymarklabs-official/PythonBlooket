"""Question generators for the "booleans" topic (CSF.2.E Booleans + CSF.2.F Operators).

Everything here follows the two lessons: ``True`` / ``False``, the comparison operators
(``==  !=  >  <  >=  <=``), ``"apple" < "banana"`` (alphabetical), comparisons returning ``bool``,
``and`` / ``or`` / ``not`` with ``x, y = True, False`` (and ``is_student`` / ``has_permission``),
truthiness (``0``, ``""``, ``None``, ``[]`` are False; ``"hi"`` is True), the chained comparison
``13 <= age <= 19`` and ``=`` vs ``==``.  The Canvas items about the "not equal" operator, "which value
has the type bool", "between 13 and 19 (chained comparison)" and the Truthiness / Boolean logic
matching questions are reused almost word for word.  The two Mini-Challenges (Driving Age, Number
Test) come back as typed-code questions.

The formats mirror the Canvas quizzes: short concept questions, "what does this print", "which line
fixes it", fill-in-the-blanks, matching and typed code (graded in the sandbox).
"""

from __future__ import annotations

import itertools
import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NOTHING_PRINTED,
    WORDS,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    error_choice,
    expression_task,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
    which_expression_question,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "booleans"

FRUITS = ["apple", "banana", "cherry", "grape", "lemon", "mango", "orange", "peach", "pear", "plum"]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _b(value: object) -> str:
    return "True" if value else "False"


def _pick(difficulty: int, prompt: str, correct: str, wrong: list[str], explanation: str,
          rng: random.Random, code: str | None = None) -> Question:
    """A plain multiple-choice question (most plausible wrong answers first)."""
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


def _out(code: str, difficulty: int, wrong: list[str], explanation: str, rng: random.Random, *,
         prompt: str = "What does this code print?", allow_error: bool = False) -> Question:
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


def _nearby(values: list[bool], rng: random.Random) -> list[list[bool]]:
    """Every other True/False combination, the ones with the fewest slips first."""
    others = [list(c) for c in itertools.product([True, False], repeat=len(values)) if list(c) != list(values)]
    rng.shuffle(others)
    others.sort(key=lambda c: sum(a != b for a, b in zip(c, values)))
    return others


def _show(labels: list[str], values: list[bool]) -> str:
    """The text a run of ``print(label, value)`` lines produces (a label may be empty)."""
    return "\n".join(f"{lab} {_b(v)}" if lab else _b(v) for lab, v in zip(labels, values))


def _combo_wrong(labels: list[str], values: list[bool], rng: random.Random) -> list[str]:
    return [_show(labels, c) for c in _nearby(values, rng)]


def _truth(expr: str, **names: object) -> object:
    """Evaluate one of OUR generated conditions with the given names bound."""
    return eval(expr, {"__builtins__": {"bool": bool, "len": len, "range": range}}, dict(names))  # noqa: S307


def _numbers_in(*texts: str) -> list[int]:
    import re

    found: list[int] = []
    for t in texts:
        found += [int(m) for m in re.findall(r"-?\d+", t)]
    return found


def _same_behaviour(a: str, b: str, var: str) -> bool:
    """True if conditions ``a`` and ``b`` agree for every probe value of ``var``."""
    nums = _numbers_in(a, b) or [0]
    probes = range(min(nums) - 3, max(nums) + 4)
    return all(bool(_truth(a, **{var: p})) == bool(_truth(b, **{var: p})) for p in probes)


def _distinct_from(correct: str, wrong: list[str], var: str) -> list[str]:
    """Drop every wrong condition that behaves exactly like the correct one."""
    return [w for w in wrong if not _same_behaviour(correct, w, var)]


# ==========================================================================
# EASY - choice (the level of the Canvas quizzes)
# ==========================================================================


@generator(TOPIC, EASY)
def gen_operator_symbol(rng: random.Random) -> Question:
    """'Which operator means "not equal"?' and its relatives, in both directions."""
    ask_symbol = [
        ('Which operator means "not equal"?', "!=", ["=!", "<>", "=="],
         '`!=` means "not equal": `5 != 4` is True. (`==` is "equal", and `=!` or `<>` are not Python.)'),
        ("Which operator checks if two values are equal?", "==", ["=", "===", "!="],
         "`==` compares two values. A single `=` assigns a value instead."),
        ('Which operator means "greater than or equal to"?', ">=", ["=>", ">", "<="],
         'Write `>=` with the `>` first: `age >= 16`. `=>` is not a Python operator.'),
        ('Which operator means "less than or equal to"?', "<=", ["=<", "<", ">="],
         'Write `<=` with the `<` first: `2 <= 1` is False. `=<` is not a Python operator.'),
        ('Which operator means "greater than"?', ">", ["<", ">=", "!="],
         "`>` is greater than: `7 > 3` is True."),
    ]
    ask_meaning = [
        ("What does the operator `!=` mean?", "not equal to", ["equal to", "greater than", "assign a value"],
         '`!=` means "not equal to": `5 != 4` is True.'),
        ("What does the operator `==` do?", "compares two values", ["assigns a value", "checks if two values are different", "joins two strings"],
         "`==` compares two values and gives `True` or `False`. A single `=` assigns."),
        ("What does the operator `>=` mean?", "greater than or equal to", ["greater than", "less than or equal to", "not equal to"],
         "`>=` is true when the left side is bigger than or the same as the right side."),
        ("What does the operator `<=` mean?", "less than or equal to", ["less than", "greater than or equal to", "equal to"],
         "`<=` is true when the left side is smaller than or the same as the right side."),
    ]
    if rng.random() < 0.55:
        prompt, correct, wrong, why = rng.choice(ask_symbol)
    else:
        prompt, correct, wrong, why = rng.choice(ask_meaning)
    return _pick(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_which_value_is_bool(rng: random.Random) -> Question:
    """'Which value has the type bool?'"""
    if rng.random() < 0.6:
        correct = rng.choice(["True", "False"])
        pool = ['"False"', '"True"', "0", "1", "None", '"true"', "[]"]
        if correct == "True":
            pool.remove('"True"')
        else:
            pool.remove('"False"')
        # keep the quiz's flavour: a quoted word and a number come first
        wrong = [f'"{correct}"', rng.choice(["0", "1"]), *rng.sample([p for p in pool if p not in (f'"{correct}"', "0", "1")], 3)]
        why = f"`{correct}` (no quotes, capital first letter) is a bool. `\"{correct}\"` in quotes is a string, and `0` / `1` are ints."
        return _pick(EASY, "Which value has the type bool?", correct, wrong, why, rng)
    a, b = rng.sample(range(2, 20), 2)
    op = rng.choice([">", "<", "==", "!=", ">=", "<="])
    correct = f"{a} {op} {b}"
    wrong = [f'"{correct}"', f"{a} + {b}", f"{a} * {b}", f"{a} / {b}"]
    for w in wrong[1:]:
        assert not isinstance(eval(w), bool)
    why = f"A comparison gives a bool (`{correct}` is `{_b(eval(correct))}`). Text in quotes is a str, and the math expressions give numbers."
    return _pick(EASY, "Which of these has the type bool?", correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_print_booleans(rng: random.Random) -> Question:
    """Lesson E's first lines: print(True, False) and print(10 > 5)."""
    if rng.random() < 0.25:
        vals = [rng.random() < 0.5 for _ in range(rng.choice([2, 2, 3]))]
        if len(set(vals)) == 1:
            vals[-1] = not vals[-1]
        code = "print(" + ", ".join(_b(v) for v in vals) + ")"
        res = " ".join(_b(v) for v in vals)
        wrong = [", ".join(_b(v) for v in vals), "".join(_b(v) for v in vals), "\n".join(_b(v) for v in vals),
                 " ".join(_b(not v) for v in vals)]
        why = "`print` with several values separated by commas shows them on one line with a space between them. `True` and `False` print as plain words."
        return _out(code, EASY, wrong, why, rng)
    lesson = ["10 > 5", "10 == 5", "5 == 5", "5 != 4", "7 > 3", "2 <= 1"]
    if rng.random() < 0.5:
        exprs = rng.sample(lesson, rng.choice([2, 3]))
    else:
        exprs = []
        for _ in range(rng.choice([2, 3])):
            a, b = rng.sample(range(1, 13), 2)
            exprs.append(f"{a} {rng.choice(['>', '<', '==', '!=', '>=', '<='])} {b}")
    vals = [bool(eval(e)) for e in exprs]
    code = "\n".join(f"print({e})" for e in exprs)
    why = "Each comparison gives `True` or `False`, and `print` shows it. " + " ".join(f"`{e}` is {_b(v)}." for e, v in zip(exprs, vals))
    return _out(code, EASY, _combo_wrong([""] * len(vals), vals, rng), why, rng)


@generator(TOPIC, EASY)
def gen_compare_strings(rng: random.Random) -> Question:
    """'What is the result of "apple" < "banana" in Python?'"""
    pool = FRUITS + [w for w in WORDS if w not in FRUITS]
    while True:
        a, b = rng.sample(pool, 2)
        if a[0] != b[0]:
            break
    op = rng.choice(["<", ">"])
    expr = f'"{a}" {op} "{b}"'
    result = eval(expr)
    earlier, later = (a, b) if a < b else (b, a)
    why = (f'Python compares strings alphabetically (dictionary order). `"{earlier}"` comes before `"{later}"`, '
           f"so `{expr}` is {_b(result)}.")
    return _pick(EASY, f"What is the result of `{expr}` in Python?", _b(result),
                 [_b(not result), "Error at runtime", "It depends on the word lengths"], why, rng)


@generator(TOPIC, EASY)
def gen_bool_concepts(rng: random.Random) -> Question:
    """Vocabulary: the Key Ideas of lessons E and F as one-line concept questions."""
    items = [
        ("Which are the only two boolean values in Python?", "`True` and `False`",
         ["`yes` and `no`", "`true` and `false`", "`on` and `off`"],
         "A boolean is either `True` or `False`, with a capital first letter and no quotes."),
        ("What do comparison operators like `==` and `>` always return?", "A boolean (`True` or `False`)",
         ["A string", "A whole number", "Nothing (`None`)"],
         "Comparison operators always return booleans, so `10 > 5` is `True`."),
        ("Which statement about `True` and `False` is correct?", "They start with a capital letter",
         ["They are written in quotes", "They can be written in any case", "They are the same as the strings \"yes\" and \"no\""],
         "Python is case-sensitive: `True` works, `true` does not."),
        ('How does Python compare `"apple" < "banana"`?', "Alphabetically (dictionary order)",
         ["By the length of the words", "By the number of vowels", "It can't compare strings"],
         '`"apple"` comes before `"banana"` in the alphabet, so the result is `True`.'),
        ("What are booleans the foundation of?", "`if` / `else` decision-making",
         ["Storing long text", "Storing decimal numbers", "Repeating code a fixed number of times"],
         "Conditions are booleans: `if grade >= 70:` runs its block only when the condition is `True`."),
        ("Which operators combine or invert booleans?", "`and`, `or`, `not`",
         ["`+`, `-`, `*`", "`==`, `!=`, `>`", "`if`, `elif`, `else`"],
         "The logical operators are `and`, `or` and `not`. The comparison operators (`==`, `!=`, `>` ...) produce booleans."),
        ("What does the `not` operator do to a boolean?", "Flips it: True becomes False and False becomes True",
         ["Always makes it True", "Checks if two values are equal", "Turns it into a string"],
         "`not x` negates `x`: with `x = True`, `not x` is `False`."),
        ("What kind of value does a condition like `grade >= 70` give?", "A boolean",
         ["A string", "An integer", "A list"],
         "Comparisons give `True` or `False`, which is what an `if` needs to decide."),
    ]
    prompt, correct, wrong, why = rng.choice(items)
    return _pick(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_logical_operator_meaning(rng: random.Random) -> Question:
    """and = both must be True, or = at least one True, not = negates."""
    a, b = rng.choice([("is_student", "has_permission"), ("is_raining", "has_umbrella"), ("x", "y")])
    items = [
        ("Which operator is True only when both sides are True?", "and", ["or", "not", "!"],
         "`and` needs both sides to be True: `True and False` is False."),
        ("Which operator is True when at least one side is True?", "or", ["and", "not", "!"],
         "`or` needs at least one True side: `True or False` is True."),
        ("Which operator turns True into False and False into True?", "not", ["and", "or", "!"],
         "`not` negates a boolean: `not True` is False."),
        (f"What does `{a} and {b}` need to be True?", "Both must be True", ["At least one must be True", "Both must be False", f"Only `{a}` must be True"],
         "`and` is True only when both sides are True."),
        (f"What does `{a} or {b}` need to be True?", "At least one must be True", ["Both must be True", "Both must be False", f"Only `{b}` must be True"],
         "`or` is True when at least one side is True (and also when both are)."),
        (f"What does `not {a}` do?", f"Gives the opposite of `{a}`", [f"Gives `{a}` unchanged", f"Compares `{a}` to `{b}`", "Always gives False"],
         f"`not` negates its value: if `{a}` is True, `not {a}` is False."),
    ]
    prompt, correct, wrong, why = rng.choice(items)
    return _pick(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_logic_two_lines(rng: random.Random) -> Question:
    """The lab's x, y = True, False prints (two lines, so every True/False combo is a plausible answer)."""
    if rng.random() < 0.55:
        vx, vy = rng.choice([(True, False), (True, False), (False, True), (True, True), (False, False)])
        setup = f"x, y = {vx}, {vy}"
        a, b = "x", "y"
        names = {"and": "x and y:", "or": "x or y:", "not": "not x:"}
    else:
        vx, vy = rng.choice([(True, False), (True, False), (False, True), (True, True), (False, False)])
        a, b = rng.choice([("is_student", "has_permission"), ("is_raining", "has_umbrella")])
        setup = f"{a} = {vx}\n{b} = {vy}"
        names = {"and": "and:", "or": "or:", "not": "not:"}
    ops = rng.sample(["and", "or", "not"], 2)
    lines, labels, vals = [], [], []
    for op in ops:
        expr = f"not {a}" if op == "not" else f"{a} {op} {b}"
        lines.append(f'print("{names[op]}", {expr})')
        labels.append(names[op])
        vals.append(bool(eval(expr, {a: vx, b: vy})))
    code = setup + "\n" + "\n".join(lines)
    rules = {"and": "`and` is True only if both are True", "or": "`or` is True if at least one is True",
             "not": "`not` flips the value"}
    why = "; ".join(rules[o] for o in ops) + "."
    return _out(code, EASY, _combo_wrong(labels, vals, rng), why, rng)


@generator(TOPIC, EASY)
def gen_equals_vs_assign(rng: random.Random) -> Question:
    """= assigns, == compares."""
    var, val = rng.choice([("age", 16), ("grade", 70), ("score", 100), ("money", 5), ("count", 10), ("temperature", 72)])
    items = [
        ("What is the difference between `=` and `==`?", "`=` assigns a value, `==` compares two values",
         ["`=` compares two values, `==` assigns a value", "They both compare two values", "They both assign a value"],
         "`=` stores a value in a variable. `==` asks whether two values are equal and gives `True` or `False`."),
        (f"Which line COMPARES `{var}` to {val} (and does not change `{var}`)?", f"{var} == {val}",
         [f"{var} = {val}", f"{val} = {var}", f"{var} equals {val}"],
         f"`{var} == {val}` is a comparison that gives True or False. `{var} = {val}` would store {val} in `{var}`."),
        (f"Which line ASSIGNS {val} to the variable `{var}`?", f"{var} = {val}",
         [f"{var} == {val}", f"{val} = {var}", f"{var} equals {val}"],
         f"`{var} = {val}` stores the value. `==` only compares."),
    ]
    prompt, correct, wrong, why = rng.choice(items)
    return _pick(EASY, prompt, correct, wrong, why, rng)


def _between_set(rng: random.Random) -> tuple[str, int, int]:
    return rng.choice([("age", 13, 19), ("age", 13, 19), ("score", 70, 100), ("temperature", 60, 80),
                       ("grade", 90, 100), ("money", 5, 20), ("age", 12, 17), ("score", 50, 90), ("grade", 80, 89), ("count", 1, 10)])


@generator(TOPIC, EASY)
def gen_between_condition(rng: random.Random) -> Question:
    """'Which condition checks if age is between 13 and 19 inclusive (chained comparison)?'"""
    var, lo, hi = _between_set(rng)
    correct = f"{lo} <= {var} <= {hi}"
    wrong = [f"{var} = {lo} or {hi}", f"{var} >= {lo} <= {hi}", f"{var} in {lo}..{hi}"]
    why = (f"A chained comparison writes the range like in math: `{correct}` is True when {var} is {lo}, {hi} "
           f"or anything in between.")
    return _pick(EASY, f"Which condition checks if {var} is between {lo} and {hi} inclusive (chained comparison)?",
                 correct, wrong, why, rng)


# ==========================================================================
# MEDIUM - read a short lab-style snippet, pick the right code, spot the classic mistake
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_cleanest_chain(rng: random.Random) -> Question:
    """'Which is the cleanest way to check if age is between 13 and 19 inclusive?'"""
    var, lo, hi = _between_set(rng)
    correct = f"{lo} <= {var} <= {hi}"
    wrong = [f"{var} >= {lo} and {var} <= {hi}", f"{var} in range({lo}, {hi})", f"{var} > {lo - 1} or {var} < {hi + 1}"]
    why = (f"`{correct}` is the pro tip from the lesson: a chained comparison is cleaner than "
           f"`{wrong[0]}`. The `range({lo}, {hi})` version stops before {hi}, and with `or` the condition is always True.")
    return _pick(MEDIUM, f"Which is the cleanest way to check if {var} is between {lo} and {hi} inclusive?",
                 correct, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_chained_if_else(rng: random.Random) -> Question:
    """if 13 <= age <= 19 with a value on or just outside the edge."""
    var, lo, hi, yes, no = rng.choice([
        ("age", 13, 19, "Teenager", "Not a teenager"),
        ("age", 13, 19, "Teenager", "Not a teenager"),
        ("grade", 90, 100, "A", "Not an A"),
        ("temperature", 60, 80, "Nice day", "Not nice"),
        ("score", 70, 100, "Pass", "Fail"),
    ])
    value = rng.choice([lo - 1, lo, lo, hi, hi, hi + 1, (lo + hi) // 2, lo - 5])
    code = f'{var} = {value}\nif {lo} <= {var} <= {hi}:\n    print("{yes}")\nelse:\n    print("{no}")'
    inside = lo <= value <= hi
    why = (f"`{lo} <= {var} <= {hi}` includes both ends. With {var} = {value} it is {_b(inside)}, "
           f"so Python runs the `{'if' if inside else 'else'}` block.")
    return _out(code, MEDIUM, [no if inside else yes, f"{yes}\n{no}", NOTHING_PRINTED], why, rng)


_FALSY = ["0", '""', "None", "[]", "{}", "0.0", "set()"]
_TRUTHY = ['"hi"', '"False"', '"0"', '" "', "[0]", "-1", "3", '"None"', '["a", "b"]', "42", '"Python"']


@generator(TOPIC, MEDIUM)
def gen_truthiness_pick(rng: random.Random) -> Question:
    """Which value is treated as False / True (0, "", None, [] vs "hi")."""
    if rng.random() < 0.5:
        correct = rng.choice(_FALSY)
        wrong = rng.sample(_TRUTHY, 3)
        prompt = "Which value is treated as `False` in an `if` condition?"
        why = (f"`{correct}` is empty or zero, so it counts as False. Non-empty values like `{wrong[0]}` are True, "
               "even `\"False\"` and `\"0\"` (they are non-empty strings).")
    else:
        correct = rng.choice(_TRUTHY)
        wrong = rng.sample(_FALSY, 3)
        prompt = "Which value is treated as `True` in an `if` condition?"
        why = (f"`{correct}` is not empty and not zero, so it counts as True. Zero, empty text, empty collections "
               "and `None` are all False.")
    for v in wrong:
        assert bool(eval(v)) == (not bool(eval(correct)))
    return _pick(MEDIUM, prompt, correct, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_truthiness_if_trace(rng: random.Random) -> Question:
    """if name: ... else: ... with an empty / non-empty value."""
    var, empty, full, yes, no = rng.choice([
        ("name", '""', '"Ada"', "Hello, player", "No name"),
        ("fruits", "[]", '["apple", "banana"]', "Has fruits", "Empty basket"),
        ("score", "0", "85", "You scored", "No points yet"),
        ("nickname", "None", '"Sam"', "Welcome back", "Who are you?"),
        ("text", '""', '"hi"', "Got text", "Nothing typed"),
        ("colors", "set()", '{"red", "green", "blue"}', "Pick one", "No colors"),
    ])
    value = rng.choice([empty, full])
    code = f'{var} = {value}\nif {var}:\n    print("{yes}")\nelse:\n    print("{no}")'
    truthy = bool(eval(value))
    why = (f"An `if` treats `{value}` as {_b(truthy)}: " +
           ("it is not empty/zero, so the `if` block runs." if truthy else "it is empty/zero/None, so Python skips the `if` block and runs `else`."))
    return _out(code, MEDIUM, [no if truthy else yes, f"{yes}\n{no}", error_choice("TypeError")], why, rng)


@generator(TOPIC, MEDIUM)
def gen_which_expression_true(rng: random.Random) -> Question:
    """'Given x, y = True, False, which expression is True / False?'"""
    pool = ["x and y", "x or y", "not x", "not y", "x == y", "x != y", "x and not y", "not x or y",
            "not (x and y)", "not x and not y", "not (x or y)", "not x or not y", "y or not x", "x and (y or x)"]
    for _ in range(40):
        vx, vy = rng.choice([(True, False), (True, False), (False, True), (True, True), (False, False)])
        trues = [e for e in pool if eval(e, {"x": vx, "y": vy})]
        falses = [e for e in pool if not eval(e, {"x": vx, "y": vy})]
        want = rng.choice([True, False])
        good, bad = (trues, falses) if want else (falses, trues)
        if len(good) >= 1 and len(bad) >= 3:
            break
    else:
        raise GenerationError("no usable expression set")
    correct = rng.choice(good)
    wrong = rng.sample(bad, 3)
    setup = f"x, y = {vx}, {vy}"
    why = f"With x = {vx} and y = {vy}, `{correct}` works out to {_b(want)}. " + \
        "Remember: `and` needs both True, `or` needs at least one, `not` flips."
    return which_expression_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Given `x, y = {vx}, {vy}`, which expression is {_b(want)}?",
        setup=setup, target=want, correct_expr=correct, wrong_exprs=wrong, explanation=why, rng=rng,
    )


_RULES = [
    # (var, op, number, phrase)
    ("age", ">=", 16, "16 or older"),
    ("grade", ">=", 70, "at least 70"),
    ("score", ">=", 100, "100 or more"),
    ("money", ">=", 5, "5 or more"),
    ("age", "<", 12, "under 12"),
    ("count", ">", 10, "more than 10"),
    ("temperature", "<=", 32, "32 or less"),
    ("temperature", ">", 90, "above 90"),
    ("score", "!=", 0, "anything except 0"),
    ("money", "==", 20, "exactly 20"),
    ("grade", "<", 60, "below 60"),
    ("age", "<=", 12, "12 or younger"),
]


@generator(TOPIC, MEDIUM)
def gen_condition_for_rule(rng: random.Random) -> Question:
    """Pick the comparison that matches a plain-English rule (boundary: >= vs >)."""
    var, op, n, phrase = rng.choice(_RULES)
    correct = f"{var} {op} {n}"
    wrong = [f"{var} {o} {n}" for o in [">=", ">", "<=", "<", "==", "!="] if o != op]
    # most tempting first: the neighbouring operator (boundary slip), then the reversed direction
    flip = {">=": ">", ">": ">=", "<=": "<", "<": "<=", "==": "!=", "!=": "=="}[op]
    opposite = {">=": "<=", ">": "<", "<=": ">=", "<": ">", "==": "!=", "!=": "=="}[op]
    ordered = [f"{var} {flip} {n}", f"{var} {opposite} {n}", *wrong]
    wrong = _distinct_from(correct, ordered, var)
    prompt = f"Which condition is True when {var} is {phrase}?"
    why = f"`{correct}` reads \"{var} {phrase}\". Check the boundary: with {var} = {n}, `{correct}` is {_b(_truth(correct, **{var: n}))}."
    return _pick(MEDIUM, prompt, correct, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_fix_the_bug(rng: random.Random) -> Question:
    """The classic comparison mistakes: = vs ==, =>, =!, true, && .  (A line with a SyntaxError can't be shown as
    a runnable snippet, so those bugs are quoted in the prompt.)"""
    kind = rng.choice(["assign", "arrow", "bang", "lower", "and"])
    code = None
    if kind == "assign":
        var, val, yes = rng.choice([("grade", 70, "Exactly 70"), ("score", 100, "Perfect"), ("count", 10, "Ten")])
        prompt = f"The line `if {var} = {val}:` should print `{yes}` only when {var} is exactly {val}, but it gives a SyntaxError. Which line fixes it?"
        correct, wrong = f"if {var} == {val}:", [f"if {var} === {val}:", f"if {var} == {val}", f"if {var} equals {val}:"]
        why = "The bug is the single `=` in the `if` line: `=` assigns, `==` compares. The line also needs its colon."
    elif kind == "arrow":
        var, val, yes = rng.choice([("score", 70, "Pass"), ("age", 16, "Can drive"), ("money", 5, "Buy it")])
        prompt = f"The line `if {var} => {val}:` should print `{yes}` when {var} is {val} or more, but it gives a SyntaxError. Which line fixes it?"
        correct, wrong = f"if {var} >= {val}:", [f"if {var} > {val}:", f"if {var} =< {val}:", f"if {var} == {val}:"]
        why = f"\"Greater than or equal to\" is written `>=` (the `>` comes first). `=>` is not a Python operator, and `>` would leave out exactly {val}."
    elif kind == "bang":
        name = rng.choice(["Ada", "Sam", "Ben"])
        prompt = f"The line `if name =! \"{name}\":` should print `Not you` when name is not \"{name}\", but it gives a SyntaxError. Which line fixes it?"
        correct, wrong = f'if name != "{name}":', [f'if name <> "{name}":', f'if name == "{name}":', f'if name !== "{name}":']
        why = "The \"not equal\" operator is `!=`: the exclamation mark comes first. `=!` and `<>` are not Python."
    elif kind == "lower":
        var = rng.choice(["is_raining", "is_student", "has_permission", "is_sunny"])
        code = f"{var} = true\nprint({var})"
        prompt = f"This code raises a NameError. Which line makes `{var}` a real boolean?"
        correct, wrong = f"{var} = True", [f'{var} = "True"', f"{var} = TRUE", f"{var} == True"]
        why = "Booleans are `True` and `False` with a capital first letter and no quotes. `\"True\"` in quotes would be a string."
    else:
        var, lo, hi = rng.choice([("age", 13, 19), ("score", 70, 100), ("temperature", 60, 80)])
        prompt = f"Python has no `&&`, so `if {var} >= {lo} && {var} <= {hi}:` gives a SyntaxError. Which line checks that {var} is between {lo} and {hi} (inclusive)?"
        correct = f"if {var} >= {lo} and {var} <= {hi}:"
        wrong = [f"if {var} >= {lo} or {var} <= {hi}:", f"if {var} >= {lo}, {var} <= {hi}:", f"if {var} >= {lo} and <= {hi}:"]
        why = "Python spells it `and`. Both sides need their own full comparison, and `or` would be True for almost every value."
    return _pick(MEDIUM, prompt, correct, wrong, why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_string_compare_trace(rng: random.Random) -> Question:
    """Comparing strings: alphabetical < > and == / != (case matters)."""
    if rng.random() < 0.6:
        pool = FRUITS + ["python", "code", "loop", "snake"]
        a, b = rng.sample(pool, 2)
        if rng.random() < 0.2:
            b = a
        ops = rng.sample(["<", ">", "==", "!="], 3)
        code = f'first = "{a}"\nsecond = "{b}"\n' + "\n".join(f"print(first {o} second)" for o in ops)
        vals = [bool(eval(f"'{a}' {o} '{b}'")) for o in ops]
        why = (f'Strings compare alphabetically: "{a}" {"comes before" if a < b else "comes after" if a > b else "is the same as"} "{b}". ' +
               " ".join(f"`first {o} second` is {_b(v)}." for o, v in zip(ops, vals)))
        return _out(code, MEDIUM, _combo_wrong([""] * 3, vals, rng), why, rng)
    word = rng.choice(["Python", "Apple", "Hello", "Banana"])
    low = word.lower()
    code = f'word = "{word}"\nprint(word == "{low}")\nprint(word.lower() == "{low}")'
    vals = [False, True]
    why = (f'`==` compares exactly, capital letters included, so "{word}" is not equal to "{low}". '
           f'`word.lower()` makes it "{low}" first, so the second comparison is True.')
    return _out(code, MEDIUM, _combo_wrong([""] * 2, vals, rng), why, rng)


@generator(TOPIC, MEDIUM)
def gen_type_of_comparison(rng: random.Random) -> Question:
    """type() of True, "True", a comparison ... (which value has the type bool?)."""
    pool = [
        ("True", "bool"), ('"True"', "str"), ("10 > 5", "bool"), ("5 == 5", "bool"), ("not False", "bool"),
        ("10", "int"), ("3.5", "float"), ('"apple" < "banana"', "bool"), ("None", "NoneType"),
        ('"5" == 5', "bool"), ("1", "int"), ('"False"', "str"),
    ]
    items = rng.sample(pool, 2)
    if len({t for _, t in items}) == 1 and rng.random() < 0.8:
        items[1] = rng.choice([p for p in pool if p[1] != items[0][1]])
    code = "\n".join(f"print(type({e}))" for e, _ in items)
    names = [t for _, t in items]
    wrong_for = {"bool": "int", "str": "bool", "int": "bool", "float": "int", "NoneType": "bool"}

    def fmt(ts: list[str]) -> str:
        return "\n".join(f"<class '{t}'>" for t in ts)

    wrong = [fmt([wrong_for[names[0]], names[1]]), fmt([names[0], wrong_for[names[1]]]),
             fmt([wrong_for[names[0]], wrong_for[names[1]]]), fmt(names[::-1])]
    why = "A comparison (`==`, `<`, `>` ...) and the words `True` / `False` are `bool`. Anything in quotes is a `str`. " + \
        " ".join(f"`{e}` is {t}." for e, t in items)
    return _out(code, MEDIUM, wrong, why, rng)


# ==========================================================================
# HARD - choice (lab-level snippets with a twist)
# ==========================================================================

_FLAG_NAMES = [
    ("is_student", "has_permission"),
    ("is_raining", "has_umbrella"),
    ("is_ready", "is_online"),
    ("has_ticket", "is_adult"),
]


@generator(TOPIC, HARD)
def gen_hard_flag_trace(rng: random.Random) -> Question:
    """The lesson's and / or / not lines, with ``not`` wrapped around a whole ``and``."""
    n1, n2 = rng.choice(_FLAG_NAMES)
    a, b = rng.choice([(True, False), (False, True), (True, True), (False, False)])
    code = (
        f"{n1} = {a}\n{n2} = {b}\n"
        f'print("and:", {n1} and {n2})\n'
        f'print("or:", {n1} or {n2})\n'
        f'print("not:", not ({n1} and {n2}))'
    )
    values = [a and b, a or b, not (a and b)]
    wrong = _combo_wrong(["and:", "or:", "not:"], values, rng)
    why = (
        f"`and` is True only when both sides are True, `or` when at least one is, and `not` flips whatever is "
        f"inside the parentheses: {_b(values[0])}, {_b(values[1])}, {_b(values[2])}."
    )
    return _out(code, HARD, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_hard_boundary_count(rng: random.Random) -> Question:
    """Chained comparisons at, just inside and just outside the edges."""
    lo, hi = rng.choice([(13, 19), (10, 18), (16, 25), (5, 12), (60, 90)])
    probes = rng.sample([lo - 1, lo, (lo + hi) // 2, hi, hi + 1], 4)
    code = "\n".join(f"print({lo} <= {p} <= {hi})" for p in probes)
    count = sum(lo <= p <= hi for p in probes)
    wrong = [str(c) for c in (count - 1, count + 1, count + 2, count - 2, 0, 4) if 0 <= c <= 4 and c != count]
    why = (
        f"`{lo} <= x <= {hi}` is True for {lo} and {hi} themselves (the signs include the ends) "
        f"but not for {lo - 1} or {hi + 1}. Here {count} of the four lines print True."
    )
    return _pick(HARD, "How many of these lines print `True`?", str(count), wrong, why, rng, code=code)


@generator(TOPIC, HARD)
def gen_hard_always_true(rng: random.Random) -> Question:
    """The classic slip: ``or`` between two range checks is True for every number."""
    var = rng.choice(["age", "score", "level"])
    lo, hi = rng.choice([(13, 19), (10, 18), (20, 30)])
    value = rng.choice([lo - 8, lo - 3, hi + 5, hi + 20])
    if rng.random() < 0.5:
        code = (
            f"{var} = {value}\nif {var} >= {lo} or {var} <= {hi}:\n"
            f'    print("In range")\nelse:\n    print("Out of range")'
        )
        why = (
            f"With `or`, only ONE side has to be True, and every number is at least {lo} or at most {hi}. "
            f"So the condition is True for {value} and it prints In range. The range check needs `and`."
        )
        return _out(code, HARD, ["Out of range", "In range\nOut of range", "Error: SyntaxError"], why, rng)
    code = f"{var} = {value}\nif {var} >= {lo} or {var} <= {hi}:\n    print(\"In range\")"
    correct = f"Change `or` to `and`"
    wrong = [
        f"Change `>=` to `>`",
        f"Change `<=` to `<`",
        f"Swap the numbers {lo} and {hi}",
    ]
    why = (
        f"`or` is True when either check passes, so every number gets through. A range needs BOTH checks: "
        f"`{var} >= {lo} and {var} <= {hi}` (or the chained `{lo} <= {var} <= {hi}`)."
    )
    return _pick(HARD, f"This should print In range only when `{var}` is between {lo} and {hi}. What fixes it?", correct, wrong, why, rng, code=code)


@generator(TOPIC, HARD)
def gen_hard_not_truthiness(rng: random.Random) -> Question:
    """``if not value:`` with an empty or a filled-in value."""
    var, value, empty = rng.choice(
        [("name", '""', True), ("name", '"Ada"', False), ("items", "[]", True), ("items", '["pen"]', False),
         ("count", "0", True), ("count", "3", False), ("text", '""', True), ("text", '"hi"', False)]
    )
    code = f'{var} = {value}\nif not {var}:\n    print("Nothing here")\nelse:\n    print("Found", {var})'
    spoiler = f"Found {value.strip(chr(34))}" if not empty else "Found"
    if empty:
        wrong = ['Found', 'Nothing here\nFound', 'Error: TypeError', f'Found {value}']
        why = (
            f"`{value}` counts as False (empty things and 0 are False), so `not {var}` is True and the first branch "
            f"prints Nothing here."
        )
    else:
        wrong = ['Nothing here', 'Nothing here\nFound', 'Error: TypeError', f'Found {value}']
        why = (
            f"`{value}` counts as True (non-empty things and non-zero numbers are True), so `not {var}` is False and the "
            f"else branch runs."
        )
    return _out(code, HARD, [w for w in wrong if w != spoiler], why, rng)


# ==========================================================================
# BLANKS (typed)
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_driving_age(rng: random.Random) -> Question:
    """Mini-Challenge "Driving Age": which comparison lets the exact limit through?"""
    limit, yes = rng.choice(
        [(16, "Can drive"), (16, "Learner permit"), (18, "Can vote"), (18, "Adult ticket"), (21, "Allowed"), (13, "Can join"), (13, "Teen club")]
    )
    no = rng.choice(["Too young", "Not yet", "Sorry, too young"])
    var = rng.choice(["age", "age", "years_old"])
    template = f'{var} = {limit}\nif {var} {blank_mark(1)} {limit}:\n    print("{yes}")\nelse:\n    print("{no}")'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blank so this prints `{yes}` for someone who is exactly {limit}.",
        template=template,
        blanks=[Blank([">="], hint="operator")],
        explanation=f"`{var} >= {limit}` is True when the age is {limit} or more, including exactly {limit}. `{var} > {limit}` would leave {limit} out.",
        expect_output=yes,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_chain_edge(rng: random.Random) -> Question:
    """The chained comparison, with the value sitting on one edge of the range."""
    var = rng.choice(["age", "score", "level"])
    lo, hi = rng.choice([(13, 19), (10, 18), (1, 10), (60, 100)])
    low_edge = rng.random() < 0.5
    value = lo if low_edge else hi
    if low_edge:
        template = f"{var} = {value}\nprint({lo} {blank_mark(1)} {var} <= {hi})"
    else:
        template = f"{var} = {value}\nprint({lo} <= {var} {blank_mark(1)} {hi})"
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blank so the chained comparison prints `True` when `{var}` is {value}, one of the ends of the range.",
        template=template,
        blanks=[Blank(["<="], hint="comparison")],
        explanation=f"`<=` includes the end value. With `<` the check would be False for {value}, because {value} is not strictly {'greater than ' + str(lo) if low_edge else 'less than ' + str(hi)}.",
        expect_output="True",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_and_or_not(rng: random.Random) -> Question:
    """Choose ``and`` / ``or`` / ``not`` so each print line shows the stated result."""
    n1, n2 = rng.choice(_FLAG_NAMES)
    a, b = rng.choice([(True, False), (False, True)])
    template = (
        f"{n1} = {a}\n{n2} = {b}\n"
        f'print("both:", {n1} {blank_mark(1)} {n2})\n'
        f'print("either:", {n1} {blank_mark(2)} {n2})\n'
        f'print("opposite:", {blank_mark(3)} {n1})'
    )
    out = f"both: {_b(a and b)}\neither: {_b(a or b)}\nopposite: {_b(not a)}"
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Fill in the three blanks (`and`, `or` or `not`) so the program prints exactly:\n" + out.replace("\n", "  /  "),
        template=template,
        blanks=[Blank(["and"], hint="and / or / not"), Blank(["or"], hint="and / or / not"), Blank(["not"], hint="and / or / not")],
        explanation=(
            f"Because the two values differ, `and` gives {_b(a and b)} and `or` gives {_b(a or b)}; `not {n1}` flips "
            f"{n1} to {_b(not a)}."
        ),
        expect_output=out,
    )


# ==========================================================================
# MATCH (clicks)
# ==========================================================================


@generator(TOPIC, EASY, qtype="match")
def gen_match_comparisons(rng: random.Random) -> Question:
    pool = [
        ("5 == 5", "True"), ("5 != 4", "True"), ("7 > 3", "True"), ("2 <= 1", "False"),
        ('"apple" < "banana"', "True"), ("10 == 5", "False"), ("10 > 5", "True"),
        ('"banana" < "apple"', "False"), ("3 >= 3", "True"), ("4 < 4", "False"),
    ]
    while True:
        pairs = rng.sample(pool, 5)
        if {a for _, a in pairs} == {"True", "False"}:
            break
    for expr, ans in pairs:
        if _b(eval(expr)) != ans:  # noqa: S307 - our own literals
            raise GenerationError(f"{expr} is not {ans}")
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each comparison to its result.",
        pairs=pairs,
        explanation="Comparison operators always give a boolean. Strings are compared alphabetically, so \"apple\" < \"banana\" is True.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_boolean_logic(rng: random.Random) -> Question:
    """The bank question: 'Match each expression to its result assuming x=True, y=False.'"""
    pool = {"x and y": "False", "x or y": "True", "not x": "False", "not y": "True", "x == y": "False", "x != y": "True"}
    x, y = True, False
    for expr, ans in pool.items():
        if _b(eval(expr)) != ans:  # noqa: S307
            raise GenerationError(f"{expr} should be {ans}")
    while True:
        pairs = rng.sample(list(pool.items()), 5)
        if {a for _, a in pairs} == {"True", "False"}:
            break
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each expression to its result.",
        pairs=pairs,
        explanation="`and` needs both sides True, `or` needs one, `not` flips the value, and `x == y` / `x != y` compare the two values.",
        rng=rng,
        code="x = True\ny = False",
    )


# ==========================================================================
# CODE (typed, graded in the sandbox)
# ==========================================================================


@generator(TOPIC, EASY, qtype="code")
def gen_code_between(rng: random.Random) -> Question:
    """Type the condition 'between lo and hi (inclusive)'."""
    var = rng.choice(["age", "score", "temperature", "level"])
    lo = rng.choice([13, 10, 1, 60, 70])
    hi = lo + rng.choice([6, 9, 20, 30])
    probes = [(lo + hi) // 2, hi + 1, lo, lo - 1, hi]
    cases = [({var: v}, lo <= v <= hi) for v in probes]
    task = expression_task(f"{lo} <= {var} <= {hi}", cases, examples=2)
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds a number. Type a condition that is `True` when `{var}` is between {lo} and {hi}, including {lo} and {hi}.",
        task=task,
        explanation=f"A chained comparison does it: `{lo} <= {var} <= {hi}` (or `{var} >= {lo} and {var} <= {hi}`).",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_logic_expression(rng: random.Random) -> Question:
    """One expression with and / or / not / != over two preset booleans."""
    n1, n2 = rng.choice(_FLAG_NAMES)
    kind = rng.choice(
        [
            (f"{n1} and {n2}", f"`{n1}` and `{n2}` are both True", lambda p, q: p and q),
            (f"{n1} or {n2}", f"at least one of `{n1}` and `{n2}` is True", lambda p, q: p or q),
            (f"not {n1}", f"`{n1}` is False", lambda p, q: not p),
            (f"{n1} != {n2}", f"`{n1}` and `{n2}` are different", lambda p, q: p != q),
            (f"not ({n1} or {n2})", f"neither `{n1}` nor `{n2}` is True", lambda p, q: not (p or q)),
        ]
    )
    solution, meaning, fn = kind
    order = [(True, True), (True, False), (False, True), (False, False)]
    rng.shuffle(order)
    cases = [({n1: p, n2: q}, bool(fn(p, q))) for p, q in order]
    task = expression_task(solution, cases, examples=2)
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{n1}` and `{n2}` hold `True` or `False`. Type an expression that is `True` only when {meaning}.",
        task=task,
        explanation="Combine the booleans with `and`, `or`, `not` or a comparison, so the result is itself True or False.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_driving_age(rng: random.Random) -> Question:
    """Mini-Challenge "Driving Age": an if/else on a preset age."""
    limit, yes = rng.choice(
        [(16, "Can drive"), (16, "Learner permit"), (18, "Can vote"), (18, "Adult ticket"), (21, "Can enter"), (13, "Can join"), (13, "Teen club")]
    )
    no = rng.choice(["Too young", "Not yet", "Sorry, too young"])
    ages = [limit - 1, limit, limit + rng.randint(1, 9), max(1, limit - rng.randint(2, 9)), limit + rng.randint(10, 30)]
    ages = list(dict.fromkeys(ages))
    rng.shuffle(ages)
    cases = [Case(vars={"age": a}, out=yes if a >= limit else no) for a in ages]
    solution = f'if age >= {limit}:\n    print("{yes}")\nelse:\n    print("{no}")'
    task = program_task(solution, cases, starter="", examples=2)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"The variable `age` already exists. Write an `if`/`else` that prints `{yes}` if `age >= {limit}` and `{no}` otherwise.",
        task=task,
        explanation=f"`if age >= {limit}:` runs the first print when the age is {limit} or more; `else:` handles everyone younger.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_is_function(rng: random.Random) -> Question:
    """A function that returns the result of a chained comparison."""
    name, var, lo, hi, what = rng.choice(
        [
            ("is_teen", "age", 13, 19, "between 13 and 19, including both"),
            ("is_valid_score", "score", 0, 100, "from 0 to 100, including both"),
            ("is_warm", "temperature", 60, 90, "from 60 to 90, including both"),
            ("is_single_digit", "n", 0, 9, "from 0 to 9, including both"),
        ]
    )
    probes = [lo - 1, lo, (lo + hi) // 2, hi, hi + 1, hi + 20]
    cases = [((v,), lo <= v <= hi) for v in probes]
    rng.shuffle(cases)
    solution = f"def {name}({var}):\n    return {lo} <= {var} <= {hi}"
    task = function_task(name, solution, cases, examples=2)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{name}({var})` that returns `True` when `{var}` is {what}, and `False` otherwise. Use `return`, not `print`.",
        task=task,
        explanation=f"A comparison is already True or False, so the function can simply `return {lo} <= {var} <= {hi}`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_number_test(rng: random.Random) -> Question:
    """Mini-Challenge "Number Test": the special number must be checked BEFORE the range."""
    lo, hi = rng.choice([(1, 100), (1, 10), (10, 99), (0, 50)])
    special = rng.choice([(lo + hi) // 2, lo + 3, hi - 2])
    inside, special_msg, outside = "In range", "Special number", "Out of range"
    values = [special, lo, hi, hi + 1, lo - 1, (lo + hi) // 3 + 1]
    values = [v for i, v in enumerate(values) if v not in values[:i]]
    cases = [Case(stdin=[str(v)], out=special_msg if v == special else inside if lo <= v <= hi else outside) for v in values]
    solution = (
        f"n = int(input())\nif n == {special}:\n    print(\"{special_msg}\")\nelif {lo} <= n <= {hi}:\n"
        f"    print(\"{inside}\")\nelse:\n    print(\"{outside}\")"
    )
    task = program_task(solution, cases, starter="n = int(input())\n", examples=2)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"Ask for a whole number with `input()`. Print `{special_msg}` if it is exactly {special}; otherwise print `{inside}` if it is "
            f"between {lo} and {hi} (including both), and `{outside}` if not. Check the special number first - it is also inside the range."
        ),
        task=task,
        explanation=f"Put the `== {special}` check first. If the range check came first, {special} would print In range and the special message would never run.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_access_rule(rng: random.Random) -> Question:
    """A rule that combines and / or over three booleans; all eight combinations are tested."""
    a, b, c = rng.choice([("is_student", "has_permission", "is_teacher"), ("has_ticket", "is_adult", "is_staff"), ("is_member", "has_code", "is_owner")])
    forms = [
        (f"({a} and {b}) or {c}", f"`{c}` is True, or both `{a}` and `{b}` are True", lambda p, q, r: (p and q) or r),
        (f"{a} and ({b} or {c})", f"`{a}` is True and at least one of `{b}` and `{c}` is True", lambda p, q, r: p and (q or r)),
        (f"{a} and not {b}", f"`{a}` is True and `{b}` is False (`{c}` does not matter)", lambda p, q, r: p and not q),
    ]
    body, meaning, fn = rng.choice(forms)
    name = rng.choice(["can_enter", "has_access", "is_allowed"])
    combos = [(p, q, r) for p in (True, False) for q in (True, False) for r in (True, False)]
    rng.shuffle(combos)
    cases = [((p, q, r), bool(fn(p, q, r))) for p, q, r in combos]
    solution = f"def {name}({a}, {b}, {c}):\n    return {body}"
    task = function_task(name, solution, cases, examples=3)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a function `{name}({a}, {b}, {c})` that returns `True` when {meaning}, and `False` otherwise.",
        task=task,
        explanation=f"Combine the three booleans with `and`, `or` and `not`: `return {body}`. Parentheses make the grouping clear.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_count_true(rng: random.Random) -> Question:
    """Bingo task: count how many of three booleans are True."""
    name = rng.choice(["count_true", "how_many_true", "true_count"])
    combos = [(p, q, r) for p in (True, False) for q in (True, False) for r in (True, False)]
    rng.shuffle(combos)
    cases = [((p, q, r), sum((p, q, r))) for p, q, r in combos]
    solution = (
        f"def {name}(a, b, c):\n    count = 0\n    if a:\n        count += 1\n    if b:\n        count += 1\n"
        f"    if c:\n        count += 1\n    return count"
    )
    task = function_task(name, solution, cases, examples=3)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a function `{name}(a, b, c)` that returns how many of the three values are `True` (a number from 0 to 3).",
        task=task,
        explanation="Start a counter at 0 and add 1 for each value that is True (`if a:` is the same as `if a == True:`), then return it.",
    )
