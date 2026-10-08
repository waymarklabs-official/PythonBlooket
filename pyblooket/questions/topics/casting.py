"""Question generators for the "casting" topic (CSF.2.C: Python Casting).

Everything here comes from the lesson `casting_lab.py` and its Mini-Challenge "Double It":
`int(2.8)` cuts the decimal off (2), `float("3.5")`, `str(100)`, `bool(0)` / `bool(1)` /
`bool("")` / `bool("hi")`, `input()` always returns a string (so cast it before math), the
"Common Errors" list (`int("3.5")` -> ValueError, `"Age: " + 16` -> TypeError, `"5" * 2`
repeats the string) and the Pro Tip (prefer `float()` when the user might type decimals).

Formats: multiple choice, fill in the blanks, matching, and typed code (graded in the sandbox).
"""

from __future__ import annotations

import random
import re

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    display_output,
    error_choice,
    expression_task,
    fn_cases,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "casting"

PEOPLE = ["Ada", "Reid", "Sam", "Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon", "Mia", "Noah", "Zoe"]

_CASTS = {"int": int, "float": float, "str": str, "bool": bool}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _lit(value) -> str:
    """How a value is written in code: strings with double quotes (the lesson's style)."""
    if isinstance(value, str):
        return '"' + value + '"'
    return repr(value)


def _describe(value) -> str:
    """The quiz's answer style: `"100" as a string`, `100 as an int` ..."""
    if isinstance(value, bool):
        return f"{value} as a bool"
    if isinstance(value, int):
        return f"{value} as an int"
    if isinstance(value, float):
        return f"{value} as a float"
    return f'"{value}" as a string'


def _show(value) -> str:
    """What `print(value, type(value))` shows."""
    return f"{value} <class '{type(value).__name__}'>"


def _cast_or_error(name: str, source) -> str | None:
    try:
        return _CASTS[name](source)
    except ValueError:
        return None


def _q(difficulty, prompt, correct, distractors, explanation, rng, code=None):
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=list(distractors),
        explanation=explanation,
        rng=rng,
        code=code,
    )


_PRINT_PROMPTS = [
    "What does this code print?",
    "What is the output of this code?",
    "What will this program print?",
    "What is printed when this code runs?",
]


def _out(difficulty, code, distractors, explanation, rng, prompt=None, allow_error=False):
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=list(distractors),
        explanation=explanation,
        rng=rng,
        prompt=prompt or rng.choice(_PRINT_PROMPTS),
        allow_error=allow_error,
    )


_INPUT_CALL = re.compile(r"input\([^()]*\)")


def _run_typed(code: str, typed: list[str]):
    """Run a snippet in which every `input(...)` is answered by the next string in `typed`
    (the player is told what the user types).  Used to compute answers by construction."""
    answers = iter(typed)
    patched = _INPUT_CALL.sub(lambda m: repr(next(answers)), code)
    return run_code(patched)


def _typed_q(difficulty, prompt, code, typed, distractors, explanation, rng):
    """A choice question about code that calls input(): the answer comes from running it."""
    res = _run_typed(code, typed)
    correct = error_choice(res.error) if res.error else display_output(res.output)
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=list(distractors),
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _num_text(rng, whole=True):
    if whole:
        return str(rng.choice([4, 7, 9, 12, 15, 20, 25, 36, 41, 50]))
    return rng.choice(["2.5", "3.5", "7.5", "1.75", "9.5", "12.5", "0.5", "4.25"])


# --------------------------------------------------------------------------
# EASY choice
# --------------------------------------------------------------------------


@generator(TOPIC, EASY)
def gen_input_returns(rng: random.Random) -> Question:
    """'What does input() return (before any casting)?' and friends."""
    typed = rng.choice(["42", "7", "3.5", "100", "16", "2026", "9.99"])
    prompt = rng.choice(
        [
            "What does `input()` return (before any casting)?",
            "Which type does `input()` always return, even if the user types digits?",
            f"A user types `{typed}` at `user_num = input(\"Enter a number: \")`. What type is `user_num`?",
            f"After `age = input(\"How old are you? \")`, the user types `{typed}`. What type does `age` hold?",
            "What type of value comes back from `input()` before you cast it?",
        ]
    )
    return _q(
        EASY,
        prompt,
        "str",
        ["int", "float", "bool"],
        "`input()` always returns a string, even if the user types digits. Cast it with `int()` or `float()` before doing math.",
        rng,
    )


_PRODUCE_CASES = [
    ("str", 100), ("str", 99), ("str", 2026), ("str", 3.5), ("str", 16),
    ("int", "42"), ("int", "7"), ("int", "365"), ("int", 2.8), ("int", 9.99), ("int", 7.5),
    ("float", "3.14"), ("float", "7"), ("float", "2.5"), ("float", "10"), ("float", 4),
]


@generator(TOPIC, EASY)
def gen_what_cast_produces(rng: random.Random) -> Question:
    """'What does str(100) produce?' (quiz wording)."""
    func, src = rng.choice(_PRODUCE_CASES)
    result = _CASTS[func](src)
    wrong = []
    if func == "int" and isinstance(src, float):
        wrong.append(_describe(int(src) + 1))  # rounding is the classic mistake
    for other in rng.sample([n for n in _CASTS if n != func], 3):
        got = _cast_or_error(other, src)
        wrong.append(error_choice("ValueError") if got is None else _describe(got))
    call = f"{func}({_lit(src)})"
    if func == "str":
        why = f"`{call}` turns the value into text, so you get the string `\"{result}\"`."
    elif func == "int" and isinstance(src, float):
        why = f"`{call}` cuts off the decimal part (it does not round), so you get the whole number `{result}`."
    elif func == "int":
        why = f"`{call}` turns the text into a whole number, so you get `{result}` as an int."
    elif isinstance(src, str):
        why = f"`{call}` turns the text into a decimal number, so you get `{result}` as a float."
    else:
        why = f"`{call}` gives a decimal number (a float), so you get `{result}`."
    return _q(EASY, f"What does `{call}` produce?", _describe(result), wrong, why, rng)


_BEST_CAST = [
    ("Which cast is best if the user might enter decimals?", "float()",
     "Use `float()` when the user might type decimals. `int()` would fail on text like `\"3.5\"`."),
    ("Which cast should you use on `input()` when the player might type `9.99`?", "float()",
     "`float()` handles decimals like `9.99`; `int(\"9.99\")` raises a ValueError."),
    ("A program asks for a whole number of coins. Which cast turns the typed text into a number you can add?", "int()",
     "`int()` turns text such as `\"42\"` into a whole number."),
    ("Which cast turns the number `99` into text so it can be joined to a message?", "str()",
     "`str(99)` gives `\"99\"`, which can be joined with other strings."),
    ("Which cast do you use to put a number inside a `\"Score: \" + ...` message?", "str()",
     "`\"Score: \" + str(score)` works because both sides are strings."),
    ("Which cast tells you whether a value counts as True or False?", "bool()",
     "`bool(value)` gives `False` for `0`, `\"\"`, `None` and empty collections, `True` otherwise."),
    ("Which cast cuts the decimal part off `2.8` and gives `2`?", "int()",
     "`int(2.8)` is `2`: the decimal part is cut off, not rounded."),
    ("Which cast is useful for displaying a number in a message?", "str()",
     "`str()` converts a number to text, which is what you need for messages."),
    ("Which cast turns the text `\"3.5\"` into a number with a decimal part?", "float()",
     "`float(\"3.5\")` gives the decimal number `3.5`."),
    ("Which cast turns the text `\"7\"` into the whole number `7`?", "int()",
     "`int(\"7\")` gives the whole number `7`."),
    ("`\"Age: \" + 16` raises a TypeError. Which cast on the `16` fixes it?", "str()",
     "`\"Age: \" + str(16)` joins two strings, so it works."),
    ("A player's name might be empty. Which cast tells you if they typed anything?", "bool()",
     "`bool(name)` is `False` for empty text and `True` otherwise."),
]


@generator(TOPIC, EASY)
def gen_best_cast(rng: random.Random) -> Question:
    """'Which cast is best if the user might enter decimals?' (quiz wording)."""
    prompt, correct, why = rng.choice(_BEST_CAST)
    return _q(EASY, prompt, correct, [c for c in ["int()", "float()", "bool()", "str()"] if c != correct], why, rng)


_FAILING = ['int("3.5")', 'int("2.75")', 'int("9.99")', 'int("1.5")', 'int("hello")', 'int("12.0")']
_FINE = ['int("42")', 'float("3.5")', "str(100)", 'float("7")', "int(2.8)", "bool(0)", "str(3.5)", 'int("12")',
         'float("0.25")', "float(4)", 'bool("hi")']


@generator(TOPIC, EASY)
def gen_which_call_fails(rng: random.Random) -> Question:
    """'Which call fails and raises an error?' (bank wording)."""
    bad = rng.choice(_FAILING)
    good = rng.sample(_FINE, 3)
    for expr in [*good]:
        if run_code(f"x = {expr}").error:
            raise GenerationError(f"{expr} should be fine")
    if run_code(f"x = {bad}").error != "ValueError":
        raise GenerationError(f"{bad} should raise ValueError")
    prompt = rng.choice(
        ["Which call fails and raises an error?", "Which of these calls raises a `ValueError`?",
         "Which line would crash with an error?"]
    )
    if bad == 'int("hello")':
        why = "`int(\"hello\")` fails with a ValueError: the text is not a whole number."
    else:
        why = f"`{bad}` raises a ValueError: `int()` only accepts text that is a whole number. Use `float()` for decimals."
    return _q(EASY, prompt, bad, good, why, rng)


_FALSY = ["0", '""', "None", "[]"]
_TRUTHY = ["1", '"hi"', "5", "-1", '"Python"', "0.5", '"apple"']


@generator(TOPIC, EASY)
def gen_truthy_value(rng: random.Random) -> Question:
    """'Which value is False / True when cast with bool()?'"""
    want_true = rng.random() < 0.5
    if want_true:
        correct, wrong = rng.choice(_TRUTHY), rng.sample(_FALSY, 3)
        prompt = rng.choice(["Which value gives `True` when passed to `bool()`?", "Which of these is `True` as a bool?"])
        why = "Zero, empty strings, `None` and empty collections are `False`. Almost everything else is `True`."
    else:
        correct, wrong = rng.choice(_FALSY), rng.sample(_TRUTHY, 3)
        prompt = rng.choice(["Which value gives `False` when passed to `bool()`?", "Which of these is `False` as a bool?"])
        why = "`bool()` is `False` for `0`, `\"\"` (empty text), `None` and empty lists, sets and dicts. Anything else is `True`."
    for v in [correct, *wrong]:
        if bool(eval(v)) != want_true and v == correct:
            raise GenerationError("bad truthiness")
        if v != correct and bool(eval(v)) == want_true:
            raise GenerationError("bad distractor truthiness")
    return _q(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_int_drops_decimals(rng: random.Random) -> Question:
    """int(2.8) is 2 -- it cuts the decimal off, it does not round."""
    x = rng.choice([2.8, 3.9, 7.2, 9.5, 5.99, 4.5, 1.1, 8.7, 6.25, 2.6])
    wrong = [str(int(x) + 1), str(x), f"{int(x)}.0", str(round(x))]
    why = f"`int({x})` cuts off the decimal part (it does not round), so the result is `{int(x)}`."
    form = rng.choice(["print", "var", "value"])
    if form == "value":
        return _q(EASY, f"What is the value of `int({x})`?", str(int(x)), wrong, why, rng)
    code = f"print(int({x}))" if form == "print" else f"whole = int({x})\nprint(whole)"
    return _out(EASY, code, wrong, why, rng)


_TYPE_CASES = [
    ('y = float("3.5")', "y", "float"), ('x = int(2.8)', "x", "int"), ("z = str(100)", "z", "str"),
    ('count = int("42")', "count", "int"), ("price = float(3)", "price", "float"), ("label = str(7)", "label", "str"),
    ("flag = bool(0)", "flag", "bool"), ('ready = bool("hi")', "ready", "bool"), ('height_m = float("1.80")', "height_m", "float"),
]


@generator(TOPIC, EASY)
def gen_type_after_cast(rng: random.Random) -> Question:
    """print(type(x)) after a cast."""
    line, var, tname = rng.choice(_TYPE_CASES)
    wrong = [f"<class '{n}'>" for n in ("int", "float", "str", "bool") if n != tname]
    return _out(
        EASY,
        f"{line}\nprint(type({var}))",
        wrong,
        f"The cast decides the type: `{tname}()` makes `{var}` {'an' if tname == 'int' else 'a'} `{tname}`, so `type({var})` shows `<class '{tname}'>`.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_why_cast_input(rng: random.Random) -> Question:
    """Why you must cast input() before math (bank wording and variations)."""
    which = rng.choice(["why", "wrong", "plus", "repeat", "concat"])
    if which == "why":
        return _q(
            EASY,
            "Why must you cast the result of `input()` before doing math?",
            "`input()` always returns a str.",
            ["`input()` always returns an int.", "`input()` returns a float when possible.", "`input()` returns None unless cast."],
            "`input()` always gives you text. You must cast it with `int()` or `float()` before doing math.",
            rng,
        )
    if which == "wrong":
        return _q(
            EASY,
            "A student does math on the text from `input()` without casting it. What is the problem?",
            "The value is text, so math fails or does the wrong thing.",
            ["Python casts it to int automatically.", "The value is always None.", "The value is always a float."],
            "`input()` returns a string. Without `int()` or `float()`, `+` joins text, `*` repeats it, and other math raises an error.",
            rng,
        )
    if which == "repeat":
        d = rng.choice(["5", "3", "7", "4"])
        t = rng.choice([2, 3])
        return _q(
            EASY,
            f"What does `\"{d}\" * {t}` do in Python?",
            f"It repeats the string, giving `\"{d * t}\"`.",
            [f"It multiplies the numbers, giving `{int(d) * t}`.", "It raises a TypeError.", f"It gives `\"{d}{t}\"`."],
            f"`\"{d}\"` is a string, so `* {t}` repeats it. Cast first (`int(\"{d}\") * {t}`) to do math.",
            rng,
        )
    if which == "concat":
        var, label = rng.choice([("age", "Age: "), ("score", "Score: "), ("coins", "Coins: ")])
        val = rng.choice([16, 250, 40, 12])
        return _q(
            EASY,
            f"Why does `\"{label}\" + {val}` raise a TypeError?",
            "A string and an int can't be joined with `+`.",
            ["`print` can't show numbers.", "Strings can't be joined with `+` at all.", f"`\"{label}\"` must be cast to an int first."],
            f"Text and numbers don't mix with `+`. Cast the number with `str({val})` or use an f-string.",
            rng,
        )
    n = rng.choice([5, 7, 10, 20])
    return _q(
        EASY,
        f"The user types a number and the code does `user_num + {n}` on the `input()` result. What must come first?",
        "Cast `user_num` with `int()` or `float()`.",
        ["Cast `user_num` with `str()`.", "Nothing - `input()` already gives an int.", "Cast `user_num` with `bool()`."],
        "`input()` returns a string, so cast it with `int()` or `float()` before adding.",
        rng,
    )


# --------------------------------------------------------------------------
# MEDIUM choice
# --------------------------------------------------------------------------

_PRINT_CASES = [
    ("int", 2.8), ("int", 9.5), ("int", 7.2), ("int", 3.9), ("int", "42"), ("float", "3.5"), ("float", "2"),
    ("float", "10"), ("float", 4), ("str", 100), ("str", 7), ("str", 2026), ("bool", 0), ("bool", "hi"),
    ("bool", 1),
]


@generator(TOPIC, MEDIUM)
def gen_cast_print(rng: random.Random) -> Question:
    """The lesson's `print(x, type(x))` lines."""
    func, src = rng.choice(_PRINT_CASES)
    var = {"int": "x", "float": "y", "str": "z", "bool": "flag"}[func]
    code = f"{var} = {func}({_lit(src)})\nprint({var}, type({var}))"
    result = _CASTS[func](src)
    wrong = []
    if func == "int" and isinstance(src, float):
        wrong.append(f"{int(src) + 1} <class 'int'>")
    for other in rng.sample([n for n in _CASTS if n != func], 3):
        got = _cast_or_error(other, src)
        wrong.append(error_choice("ValueError") if got is None else _show(got))
    if func == "bool":
        wrong += [f"{not result} <class 'bool'>", f"{result} <class 'str'>"]
    if func == "int" and isinstance(src, float):
        why = f"`int({src})` cuts off the decimal part (it does not round), so `{var}` is `{result}` and its type is `int`."
    else:
        why = f"`{func}({_lit(src)})` gives `{result}`, and `type({var})` shows the new type: `<class '{func}'>`."
    return _out(MEDIUM, code, wrong, why, rng)


_CONCAT = [
    ("age", "Age: ", lambda r: r.randint(12, 18)),
    ("score", "Score: ", lambda r: r.choice([120, 250, 400, 980])),
    ("coins", "Coins: ", lambda r: r.choice([10, 25, 40, 75])),
    ("level", "Level: ", lambda r: r.randint(2, 9)),
    ("temperature", "Temperature: ", lambda r: r.choice([68, 72, 75, 81])),
    ("height_m", "Height: ", lambda r: r.choice([1.5, 1.6, 1.75, 1.8])),
]


_JOINER = {"age": " is ", "score": " scored ", "coins": " has ", "level": " is on level ", "temperature": " felt ", "height_m": " is "}


@generator(TOPIC, MEDIUM)
def gen_concat_error(rng: random.Random) -> Question:
    """`"Age: " + 16` is a TypeError; `"Age: " + str(age)` works."""
    var, label, make = rng.choice(_CONCAT)
    val = make(rng)
    if rng.random() < 0.3:
        code = f"{var} = {val}\nprint(\"{label}\" + str({var}))"
        text = f"{label}{val}"
        return _out(
            MEDIUM, code,
            [error_choice("TypeError"), f"{label}str({var})", error_choice("ValueError"), f'{label}"{val}"'],
            f"`str({var})` turns the number into text, so `+` can join the two strings: `{text}`.",
            rng, prompt="What happens when this code runs?", allow_error=True,
        )
    if rng.random() < 0.4:
        name = rng.choice(PEOPLE)
        joiner = _JOINER[var]
        code = f'name = "{name}"\n{var} = {val}\nprint(name + "{joiner}" + {var})'
        text, as_name = f"{name}{joiner}{val}", f"{name}{joiner}{var}"
    else:
        code = f'{var} = {val}\nprint("{label}" + {var})'
        text, as_name = f"{label}{val}", f"{label}{var}"
    return _out(
        MEDIUM, code,
        [text, error_choice("ValueError"), as_name],
        f"You can't join a string and a number with `+`: that is a TypeError. Fix it with `str({var})` or an f-string.",
        rng, prompt="What happens when this code runs?", allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_fix_concat(rng: random.Random) -> Question:
    """Which line fixes `"Age: " + age` (str() or f-string)."""
    var, label, make = rng.choice(_CONCAT)
    val = make(rng)
    setup = f"{var} = {val}"
    expected = f"{label}{val}"
    bug = f'print("{label}" + {var})'
    code = f"{setup}\n{bug}"
    use_f = rng.random() < 0.5
    if use_f:
        prompt = f"The code crashes with a TypeError. Which line prints `{expected}` using an f-string?"
        correct = f'print(f"{label}{{{var}}}")'
        wrong = [f'print("{label}{{{var}}}")', f'print(f"{label}" + {var})', f'print(f"{label}{var}")', f'print(f"{label}({var})")']
        why = f"An f-string needs the `f` before the quote and braces around the variable: `f\"{label}{{{var}}}\"`."
    else:
        prompt = f"The code crashes with a TypeError. Which line prints `{expected}` using `str()`?"
        correct = f'print("{label}" + str({var}))'
        wrong = [f'print("{label}" + int({var}))', f'print("{label}" + float({var}))', f'print("{label}" + bool({var}))',
                 f'print(str("{label}") + {var})']
        why = f"`str({var})` turns the number into text, so `+` joins two strings: `{expected}`."
    # every distractor must really fail to print the expected text
    good_wrong = []
    for w in wrong:
        res = run_code(f"{setup}\n{w}")
        if res.error or res.output != expected:
            good_wrong.append(w)
    res = run_code(f"{setup}\n{correct}")
    if res.error or res.output != expected:
        raise GenerationError("fix does not print the expected text")
    return _q(MEDIUM, prompt, correct, good_wrong, why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_repeat_string(rng: random.Random) -> Question:
    """`"5" * 2` repeats the string -- cast first."""
    digits = rng.choice(["5", "7", "3", "12", "4", "9"])
    n = rng.choice([2, 3])
    cast_first = rng.random() < 0.4
    var = rng.choice(["num", "text", "user_num", "answer"])
    if cast_first:
        code = f'{var} = "{digits}"\nprint(int({var}) * {n})'
        want = int(digits) * n
        wrong = [digits * n, f"{digits}{n}", error_choice("TypeError"), f"{want}.0"]
        why = f"`int({var})` makes it a number first, so `*` multiplies: `{want}`."
    else:
        code = f'{var} = "{digits}"\nprint({var} * {n})'
        want = digits * n
        wrong = [str(int(digits) * n), f"{digits}{n}", error_choice("TypeError"), f"{int(digits) * n}.0"]
        why = f"`{var}` is a string, so `* {n}` repeats it instead of multiplying. Cast first with `int({var})`."
    return _out(MEDIUM, code, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_input_trace(rng: random.Random) -> Question:
    """The lesson's input example, traced for a typed number."""
    typed = rng.choice([7, 12, 20, 41, 5, 33, 16])
    add = rng.choice([5, 10])
    code = (
        'user_num = input("Enter a number: ")\n'
        'print("As string:", user_num, type(user_num))\n'
        "user_num = int(user_num)\n"
        f'print("As int:", user_num + {add})'
    )
    s1 = f"As string: {typed} <class 'str'>"
    wrong = [
        f"{s1}\nAs int: {typed}{add}",
        f"As string: {typed} <class 'int'>\nAs int: {typed + add}",
        f"As string: {typed + add} <class 'str'>\nAs int: {typed + add}",
        f"{s1}\n{error_choice('TypeError')}",
    ]
    return _typed_q(
        MEDIUM, f"The user types `{typed}`. What does this program print?", code, [str(typed)], wrong,
        f"Before the cast, `user_num` is the string `\"{typed}\"`. After `int()` it is a number, so `+ {add}` really adds: `{typed + add}`.",
        rng,
    )


_BOOL_MEDIUM = [("0", False), ("1", True), ("5", True), ('""', False), ('"hi"', True), ('"Python"', True), ("None", False), ("[]", False)]


@generator(TOPIC, MEDIUM)
def gen_bool_print(rng: random.Random) -> Question:
    """Three `print(bool(...))` lines."""
    while True:
        picks = rng.sample(_BOOL_MEDIUM, 3)
        if 0 < sum(t for _, t in picks) < 3:
            break
    code = "\n".join(f"print(bool({v}))" for v, _ in picks)
    truth = [str(t) for _, t in picks]
    wrong = []
    for i in rng.sample(range(3), 3):
        flipped = list(truth)
        flipped[i] = "True" if flipped[i] == "False" else "False"
        wrong.append("\n".join(flipped))
    return _out(
        MEDIUM, code, wrong,
        "`bool()` is `False` for `0`, `\"\"` (empty text), `None` and empty collections, and `True` for everything else.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_valueerror_fix(rng: random.Random) -> Question:
    """int() on a decimal -> ValueError; float() fixes it."""
    var, noun = rng.choice([("age_text", "age"), ("height_text", "height_m"), ("price_text", "price"), ("score_text", "score")])
    typed = rng.choice(["15.5", "1.75", "2.5", "9.99", "12.5", "3.5"])
    code = f'{var} = input("Enter a number: ")\n{noun} = int({var})\nprint({noun} + 1)'
    expected = str(float(typed) + 1)
    prompt = f"The user types `{typed}` and the program crashes with a ValueError. Which version of line 2 fixes it?"
    correct = f"{noun} = float({var})"
    wrong = [f"{noun} = str({var})", f"{noun} = int({var}) * 1.0", f"{noun} = bool({var})", f"{noun} = int({var} + 1)"]
    check = []
    for cand in [correct, *wrong]:
        fixed = code.replace(f"{noun} = int({var})", cand)
        res = _run_typed(fixed, [typed])
        check.append(res.output == expected and not res.error)
    if check != [True] + [False] * len(wrong):
        raise GenerationError(f"fix check failed: {check}")
    return _q(
        MEDIUM, prompt, correct, wrong,
        f"`int(\"{typed}\")` raises a ValueError because the text is not a whole number. `float()` accepts decimals.",
        rng, code=code,
    )


@generator(TOPIC, MEDIUM)
def gen_cast_without_assign(rng: random.Random) -> Question:
    """`int(text)` on its own line does not change `text`."""
    var = rng.choice(["text", "user_num", "answer", "num"])
    digits = rng.choice(["5", "8", "4", "6", "12"])
    mode = rng.choice(["lost", "lost", "saved"])
    if mode == "lost":
        code = f'{var} = "{digits}"\nint({var})\nprint({var} * 2)'
        wrong = [str(int(digits) * 2), digits, error_choice("TypeError"), f"{int(digits) * 2}.0"]
        why = f"`int({var})` makes a new number but throws it away, so `{var}` is still the string `\"{digits}\"` and `* 2` repeats it. Assign it: `{var} = int({var})`."
    else:
        code = f'{var} = "{digits}"\n{var} = int({var})\nprint({var} * 2)'
        wrong = [digits * 2, digits, error_choice("TypeError"), f"{int(digits) * 2}.0"]
        why = f"`{var} = int({var})` stores the number back in `{var}`, so `* 2` is real multiplication: `{int(digits) * 2}`."
    return _out(MEDIUM, code, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_complete_input_code(rng: random.Random) -> Question:
    """Which line goes after input() so the math works (lesson 'Input example')."""
    whole = rng.random() < 0.6
    typed = _num_text(rng, whole)
    word = "int" if whole else "float"
    add = rng.choice([5, 10])
    code = f'user_num = input("Enter a number: ")\n# missing line\nprint("As {word}:", user_num + {add})'
    expected_out = f"As {word}: {_CASTS[word](typed) + add}"
    correct = f"user_num = {word}(user_num)"
    wrong = [f"user_num = {n}(user_num)" for n in ("str", "bool") if n != word]
    wrong.append("user_num = float(user_num)" if whole else "user_num = int(user_num)")
    wrong.append(f"user_num = input({word})")
    for cand in [correct, *wrong]:
        full = code.replace("# missing line", cand)
        try:
            res = _run_typed(full, [typed, typed])
            ok = (not res.error) and res.output == expected_out
        except StopIteration:
            ok = False
        if (cand == correct) != ok:
            raise GenerationError(f"candidate check failed for {cand}: {res.output!r} {res.error}")
    return _q(
        MEDIUM,
        f"The user types `{typed}`. Which line replaces the comment `# missing line` so the program prints `{expected_out}`?",
        correct, wrong,
        f"`input()` gives a string, so cast it with `{word}()` before adding. "
        + ("Here the text is a whole number, so `int()`." if whole else "The text has a decimal point, so `int()` would raise a ValueError; use `float()`."),
        rng, code=code,
    )


# --------------------------------------------------------------------------
# HARD choice
# --------------------------------------------------------------------------


def _nested_options(rng):
    """(code, distractors, explanation) for a few two-step cast chains."""
    dec = rng.choice([2.8, 3.9, 5.5, 7.2])
    digit = rng.choice(["3", "4", "5", "7"])
    times = rng.choice([2, 3])
    k = rng.choice([4, 7, 9])
    half = rng.choice(["0.5", "1.5", "2.5"])
    big = rng.choice([2026, 1999, 100, 12345])
    return [
        (
            f'print(int(float("{dec}")))',
            [error_choice("ValueError"), str(round(dec)), str(dec), f"{int(dec)}.0"],
            f'`float("{dec}")` gives `{dec}`, then `int()` cuts off the decimal part: `{int(dec)}`. (`int("{dec}")` on its own would raise a ValueError.)',
        ),
        (
            f"print(float(int({dec})))",
            [str(int(dec)), str(dec), str(round(dec)), error_choice("ValueError")],
            f"`int({dec})` is `{int(dec)}`, then `float()` turns that into `{float(int(dec))}`.",
        ),
        (
            f'print(int("{digit}" * {times}))',
            [str(int(digit) * times), error_choice("TypeError"), f"{digit}{times}", f"{digit * times}.0"],
            f'`"{digit}" * {times}` repeats the string to `"{digit * times}"`, then `int()` makes it the number `{digit * times}`.',
        ),
        (
            f"print(str({k}) + str({times}))",
            [str(k + times), error_choice("TypeError"), f"{k} {times}", f"{k + times}.0"],
            f"Both numbers are turned into text first, so `+` joins them: `{k}{times}`.",
        ),
        (
            f"print(int(str({k})) + {times})",
            [f"{k}{times}", error_choice("TypeError"), f"{k + times}.0", str(k)],
            f'`str({k})` is the text `"{k}"`, `int()` turns it back into `{k}`, so `+ {times}` adds: `{k + times}`.',
        ),
        (
            f'print(int("{k}") + float("{half}"))',
            [str(int(k + float(half))), f"{k}{half}", error_choice("TypeError"), str(k)],
            f'`int("{k}")` is `{k}` and `float("{half}")` is `{half}`. An int plus a float gives a float: `{k + float(half)}`.',
        ),
        (
            f"print(len(str({big})))",
            [str(big), error_choice("TypeError"), str(len(str(big)) + 1), f"{len(str(big))}.0"],
            f'`str({big})` is the text `"{big}"`, and `len()` counts its characters: `{len(str(big))}`.',
        ),
        (
            'print(bool(int("0")), bool(str(0)))',
            ["True True", "False False", "True False", error_choice("ValueError")],
            '`int("0")` is the number `0`, which is `False`. `str(0)` is the text `"0"`, which is not empty, so it is `True`.',
        ),
    ]


@generator(TOPIC, HARD)
def gen_nested_casts(rng: random.Random) -> Question:
    """Two casts in a row."""
    code, wrong, why = rng.choice(_nested_options(rng))
    return _out(HARD, code, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_receipt_trace(rng: random.Random) -> Question:
    """Two casts feeding one calculation."""
    price = rng.choice(["2.50", "4.50", "1.25", "0.75", "6.50", "3.75"])
    qty = rng.choice(["2", "3", "4", "5", "6"])
    code = f'price = "{price}"\nquantity = "{qty}"\ntotal = float(price) * int(quantity)\nprint("Total:", total)'
    total = float(price) * int(qty)
    wrong = [
        f"Total: {int(total)}",
        f"Total: {price * int(qty)}",
        error_choice("TypeError"),
        f"Total: {float(price) + int(qty)}",
    ]
    return _out(
        HARD, code, wrong,
        f"`float(\"{price}\")` is `{float(price)}` and `int(\"{qty}\")` is `{qty}`. Multiplying a float by an int gives a float: `{total}`.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_join_vs_add(rng: random.Random) -> Question:
    """Text '+' joins, numbers '+' add."""
    a = rng.choice(["12", "4", "20", "8", "15", "30"])
    b = rng.choice(["3", "5", "7", "9", "2"])
    if rng.random() < 0.6:
        code = f'first = "{a}"\nsecond = "{b}"\nprint(first + second)\nprint(int(first) + int(second))'
        l1, l2 = a + b, str(int(a) + int(b))
        why = f"The first line joins two strings: `{l1}`. The second casts both to `int` first, so it adds: `{l2}`."
    else:
        code = f'first = "{a}"\nprint(first * 2)\nprint(int(first) * 2)'
        l1, l2 = a * 2, str(int(a) * 2)
        why = f"`first * 2` repeats the string: `{l1}`. After `int(first)` the `*` multiplies: `{l2}`."
    wrong = [f"{l2}\n{l1}", f"{l1}\n{l1}", f"{l2}\n{l2}", f"{l1}\n{error_choice('TypeError')}"]
    return _out(HARD, code, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_double_bug(rng: random.Random) -> Question:
    """The Double It mistake: math on the raw input() string."""
    typed = rng.choice(["4", "7", "12", "3", "25", "9"])
    expr, label = rng.choice([("n * 2", "Double:"), ("n * 3", "Triple:"), ("n + 5", "Plus five:"), ("n / 2", "Half:"), ("n - 1", "Minus one:")])
    code = f'n = input("Enter a number: ")\nprint("{label}", {expr})'
    num = int(typed)
    fake = {"n * 2": typed * 2, "n * 3": typed * 3}.get(expr)
    nice = {"n * 2": num * 2, "n * 3": num * 3, "n + 5": num + 5, "n / 2": num / 2, "n - 1": num - 1}[expr]
    wrong = [f"{label} {nice}", error_choice("ValueError"), f"{label} {float(nice)}", f"{label} {typed}"]
    if fake is not None:
        wrong.insert(0, error_choice("TypeError"))
        why = f"`n` is the string `\"{typed}\"`, so `{expr}` repeats the text instead of doing math: `{fake}`. Cast first: `n = float(n)`."
    else:
        wrong.insert(0, f"{label} {nice}")
        why = f"`n` is a string, so `{expr}` mixes text and a number, which raises a TypeError. Cast first: `n = float(n)`."
    return _typed_q(HARD, f"The user types `{typed}`. What happens when this program runs?", code, [typed], wrong, why, rng)


_BUGGY = [
    # (lines, typed answers, bad line number, why)
    (
        ['name = input("Name: ")', 'age = input("Age: ")', "next_year = age + 1", 'print(name, "will be", next_year)'],
        ["Ada", "15"], 3,
        "`age` is still a string, so `age + 1` raises a TypeError. Fix: `age = int(input(\"Age: \"))`.",
    ),
    (
        ['score_text = input("Score: ")', "score = int(score_text)", "bonus = score + 10", 'print("Total:", bonus)'],
        ["12.5"], 2,
        "`int(\"12.5\")` raises a ValueError because the text has a decimal point. Use `float(score_text)`.",
    ),
    (
        ['age = int(input("Age: "))', 'message = "In 5 years you will be " + (age + 5)', "print(message)", 'print("Done!")'],
        ["15"], 2,
        "You can't join a string and a number with `+`: that's a TypeError. Use `str(age + 5)`.",
    ),
    (
        ["coins = 10", 'bonus = "5"', "total = coins + bonus", "print(total)"],
        [], 3,
        "`coins` is a number and `bonus` is a string, so `coins + bonus` raises a TypeError. Cast with `int(bonus)`.",
    ),
    (
        ['price = float(input("Price: "))', 'count = input("How many? ")', 'print("Calculating...")', "total = price * count", 'print("Total:", total)'],
        ["2.5", "4"], 4,
        "`count` is still a string, and `float * str` raises a TypeError. Use `count = int(input(\"How many? \"))`.",
    ),
    (
        ['height_text = input("Height in meters: ")', "height_m = float(height_text)", 'print("Got it!")', 'message = "Height: " + height_m', "print(message)"],
        ["1.75"], 4,
        "You can't join a string and a float with `+`: that's a TypeError. Use `str(height_m)`.",
    ),
    (
        ['lives = int(input("Lives: "))', 'bonus = input("Bonus lives: ")', "lives = lives + bonus", "print(lives)"],
        ["3", "2"], 3,
        "`bonus` is still a string, so `lives + bonus` raises a TypeError. Cast it: `bonus = int(input(\"Bonus lives: \"))`.",
    ),
    (
        ['price = int("4.99")', "quantity = 3", "total = price * quantity", "print(total)"],
        [], 1,
        "`int(\"4.99\")` raises a ValueError because the text has a decimal point. Use `float(\"4.99\")`.",
    ),
    (
        ['name = input("Name: ")', 'age = int(input("Age: "))', "years = 10", 'print("Hello", name)', 'print(name + " will be " + (age + years))'],
        ["Eli", "14"], 5,
        "`age + years` is a number, and `+` can't join text and a number: that's a TypeError. Use `str(age + years)`.",
    ),
]


@generator(TOPIC, HARD)
def gen_find_buggy_line(rng: random.Random) -> Question:
    """Which line causes the crash?"""
    lines, typed, bad, why = rng.choice(_BUGGY)
    code = "\n".join(lines)
    res = _run_typed(code, typed)
    if not res.error:
        raise GenerationError("buggy program did not crash")
    if typed:
        shown = " and ".join(f"`{t}`" for t in typed)
        prompt = f"The user types {shown} and the program crashes with an error. Which line raises the error?"
    else:
        prompt = "This program crashes with an error. Which line raises the error?"
    others = [i for i in range(1, len(lines) + 1) if i != bad]
    wrong = [f"Line {i}" for i in rng.sample(others, 3)]
    return _q(HARD, prompt, f"Line {bad}", wrong, why, rng, code=code)


@generator(TOPIC, HARD)
def gen_truthiness_trace(rng: random.Random) -> Question:
    """bool() of numbers vs text numbers, and of casts."""
    num_var, str_var, empty_var = rng.choice([("coins", "label", "name"), ("score", "word", "text"), ("count", "answer", "nickname")])
    num = rng.choice([0, 0, 5])
    s = rng.choice(["0", " ", "False"])
    code = (
        f"{num_var} = {num}\n{str_var} = \"{s}\"\n{empty_var} = \"\"\n"
        f"print(bool({num_var}), bool({str_var}), bool({empty_var}))\n"
        f"print(bool(str({num_var})), bool({empty_var} + {str_var}))"
    )
    t = [bool(num), bool(s), False]
    t2 = [True, bool(s)]
    line1 = " ".join(str(v) for v in t)
    line2 = " ".join(str(v) for v in t2)
    flip = lambda line, i: " ".join(("False" if w == "True" else "True") if j == i else w for j, w in enumerate(line.split()))
    wrong = [f"{flip(line1, 0)}\n{line2}", f"{line1}\n{flip(line2, 0)}", f"{flip(line1, 1)}\n{flip(line2, 1)}"]
    wrong.append(f"{line1.replace('True', 'False')}\n{line2.replace('True', 'False')}")
    return _out(
        HARD, code, wrong,
        f"Text is `True` unless it is empty: even `\"{s}\"` is `True`. The number `{num}` is `{bool(num)}`, but `str({num})` is the non-empty text `\"{num}\"`, so it is `True`.",
        rng,
    )


# --------------------------------------------------------------------------
# blanks
# --------------------------------------------------------------------------


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_cast(rng: random.Random) -> Question:
    """Fill in the cast function so the text becomes a number."""
    whole = rng.random() < 0.6
    text = _num_text(rng, whole)
    func = "int" if whole else "float"
    var = rng.choice(["text", "user_num", "answer"])
    expected = str(_CASTS[func](text) + 1)
    template = f'{var} = "{text}"\nnumber = {blank_mark(1)}({var})\nprint(number + 1)'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blank so the code prints `{expected}`.",
        template=template,
        blanks=[Blank([func], hint="cast function")],
        explanation=f"`{func}({var})` turns the string into a number, so `+ 1` is real addition."
        + ("" if whole else " The text has a decimal point, so `int()` would raise a ValueError."),
        expect_output=expected,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_lesson_types(rng: random.Random) -> Question:
    """The lesson's casting_lab: int(2.8), float("3.5"), str(100) and their types."""
    a = rng.choice(["2.8", "7.9", "5.5", "9.1"])
    b = rng.choice(['"3.5"', '"2.25"', '"10"', '"0.5"'])
    c = rng.choice(["100", "42", "2026", "7"])
    template = (
        f"x = {blank_mark(1)}({a})\n"
        f"y = {blank_mark(2)}({b})\n"
        f"z = {blank_mark(3)}({c})\n"
        "print(type(x), type(y), type(z))"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Fill in the cast functions so `x` is an int, `y` is a float and `z` is a str.",
        template=template,
        blanks=[Blank(["int"], hint="whole number"), Blank(["float"], hint="decimal number"), Blank(["str"], hint="text")],
        explanation="`int()` makes a whole number (it cuts off decimals), `float()` makes a decimal number, and `str()` makes text.",
        expect_output="<class 'int'> <class 'float'> <class 'str'>",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_concat(rng: random.Random) -> Question:
    """Quiz Q11: str(age) and the f prefix."""
    var, label, make = rng.choice(_CONCAT)
    val = make(rng)
    template = f'{var} = {val}\nprint("{label}" + {blank_mark(1)}({var}))\nprint({blank_mark(2)}"{label}{{{var}}}")'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Fill in the blanks so both lines print the same text. The first joins with `+`, the second uses an f-string.",
        template=template,
        blanks=[Blank(["str"], hint="cast to text"), Blank(["f", "F"], hint="string prefix")],
        explanation=f"`\"{label}\" + {var}` fails because a number can't be joined to text, so cast with `str({var})`. An f-string starts with `f` and puts the variable in braces.",
        expect_output=f"{label}{val}\n{label}{val}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_repeat_fix(rng: random.Random) -> Question:
    """`"5" * 2` repeats; cast with int() to multiply."""
    digits = rng.choice(["5", "4", "7", "8", "6", "9"])
    n = rng.choice([2, 3])
    var = rng.choice(["num", "text", "user_num"])
    template = f'{var} = "{digits}"\nprint({blank_mark(1)}({var}) * {n})'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Right now `{var} * {n}` would repeat the string. Fill in the blank so the code prints `{int(digits) * n}`.",
        template=template,
        blanks=[Blank(["int"], hint="cast function")],
        explanation=f"`\"{digits}\" * {n}` repeats the text. Cast first with `int({var})` and `*` multiplies.",
        expect_output=str(int(digits) * n),
    )


_DOUBLE_OPS = [
    ("Double:", "* 2", "double"), ("Triple:", "* 3", "triple"), ("Half:", "/ 2", "half"),
    ("Plus ten:", "+ 10", "ten more than"), ("Times five:", "* 5", "five times"), ("Minus one:", "- 1", "one less than"),
]


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_double_it(rng: random.Random) -> Question:
    """Mini-Challenge 'Double It' with two blanks."""
    label, op, word = rng.choice(_DOUBLE_OPS)
    var = rng.choice(["n", "n", "num", "user_num"])
    ask = rng.choice(["Enter a number: ", "Pick a number: ", "Number: "])
    template = (
        f'{var} = {blank_mark(1)}("{ask}")\n'
        f"{var} = {blank_mark(2)}({var})\n"
        f'print("{label}", {var} {op})'
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Complete the program: read the text from the user, cast it to a decimal number, and print {word} the number.",
        template=template,
        blanks=[Blank(["input"], hint="ask the user"), Blank(["float"], hint="decimal cast")],
        explanation=f"`input()` gives a string, so `{var} = float({var})` casts it before the math. `float()` also works when the user types decimals.",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_two_way(rng: random.Random) -> Question:
    """Text -> numbers -> text again."""
    coins = rng.choice(["7", "12", "20", "5"])
    bonus = rng.choice(["2.5", "1.5", "0.5", "4.5"])
    template = (
        f'coins_text = "{coins}"\nbonus_text = "{bonus}"\n'
        f"total = {blank_mark(1)}(coins_text) + {blank_mark(2)}(bonus_text)\n"
        f'print("Total: " + {blank_mark(3)}(total))'
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Fill in the blanks so the program prints `Total: {int(coins) + float(bonus)}`.",
        template=template,
        blanks=[Blank(["int", "float"], hint="cast"), Blank(["float"], hint="cast (has a decimal)"), Blank(["str"], hint="back to text")],
        explanation="Cast the texts to numbers to add them (`float()` for the decimal one), then cast the total back to text with `str()` so `+` can join it to the message.",
        expect_output=f"Total: {int(coins) + float(bonus)}",
    )


# --------------------------------------------------------------------------
# match
# --------------------------------------------------------------------------

_MATCH_TYPES = [
    ('int("42")', "int"), ('float("3.14")', "float"), ("str(99)", "str"), ('bool("hi")', "bool"), ("int(2.8)", "int"),
    ("float(3)", "float"), ("bool(0)", "bool"), ("str(True)", "str"), ("input()", "str"), ('str(3.5)', "str"),
]


@generator(TOPIC, EASY, qtype="match")
def gen_match_cast_types(rng: random.Random) -> Question:
    """Match each call to the type it produces."""
    while True:
        pairs = rng.sample(_MATCH_TYPES, 5)
        if len({a for _, a in pairs}) >= 3:
            break
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each call to the type of value it gives.",
        pairs=pairs,
        extra_options=["int", "float", "str", "bool"],
        explanation="`int()` gives whole numbers, `float()` decimals, `str()` text and `bool()` True/False. `input()` always gives a str.",
        rng=rng,
    )


_MATCH_RESULTS = [
    ("int(2.8)", "2"), ('float("3.5")', "3.5"), ("str(100)", '"100"'), ("bool(0)", "False"), ('"5" * 2', '"55"'),
    ('int("42")', "42"), ("float(2)", "2.0"), ('bool("hi")', "True"), ("str(7) + str(3)", '"73"'), ("int(9.99)", "9"),
]


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_cast_results(rng: random.Random) -> Question:
    """Match each expression to its result."""
    while True:
        pairs = rng.sample(_MATCH_RESULTS, 5)
        if len({a for _, a in pairs}) == 5:
            break
    extra = []
    if any(i.startswith("int(") and "." in i for i, _ in pairs):
        extra.append("3")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each expression to its result.",
        pairs=pairs,
        extra_options=extra,
        explanation="`int()` cuts off decimals (no rounding), `float()` adds `.0`, `str()` makes text, and `\"5\" * 2` repeats the string.",
        rng=rng,
    )


_MATCH_TRUTH = [
    ("0", "False"), ('""', "False"), ("None", "False"), ("[]", "False"), ("{}", "False"),
    ('"hi"', "True"), ("1", "True"), ("-5", "True"), ('"0"', "True"), ("[0]", "True"), ('" "', "True"), ('"False"', "True"),
]


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_truthiness(rng: random.Random) -> Question:
    """Bank Q1: match each value to its truthiness."""
    while True:
        pairs = rng.sample(_MATCH_TRUTH, rng.choice([5, 6]))
        n_true = sum(1 for _, a in pairs if a == "True")
        if 2 <= n_true <= len(pairs) - 2:
            break
    for item, ans in pairs:
        if str(bool(eval(item))) != ans:
            raise GenerationError("bad truthiness pair")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each value to its truthiness in Python (what `bool(value)` gives).",
        pairs=pairs,
        extra_options=["True", "False"],
        explanation="Zero, empty text, `None` and empty collections are `False`; everything else is `True` - even `\"0\"`, `\" \"` and `[0]`.",
        rng=rng,
    )


_MATCH_ERRORS = [
    ('int("42")', "42"), ('int("3.5")', "ValueError"), ('"Age: " + 16', "TypeError"), ('"5" * 2', '"55"'),
    ('float("3.5")', "3.5"), ('int("hello")', "ValueError"), ('"Score: " + 10', "TypeError"), ('"3" * 3', '"333"'),
    ('"Level " + str(2)', '"Level 2"'), ('int("7")', "7"), ('float("2")', "2.0"), ('int("2.75")', "ValueError"),
]


@generator(TOPIC, HARD, qtype="match")
def gen_match_errors(rng: random.Random) -> Question:
    """The lesson's Common Errors: what does each line do?"""
    while True:
        pairs = rng.sample(_MATCH_ERRORS, 5)
        answers = [a for _, a in pairs]
        if "ValueError" in answers and "TypeError" in answers and len(set(answers)) >= 4:
            break
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Match each line to what happens when it runs.",
        pairs=pairs,
        extra_options=["ValueError", "TypeError"],
        explanation="`int()` on text that is not a whole number is a ValueError; joining text and a number with `+` is a TypeError; `\"5\" * 2` just repeats the string.",
        rng=rng,
    )


# --------------------------------------------------------------------------
# code
# --------------------------------------------------------------------------


@generator(TOPIC, EASY, qtype="code")
def gen_code_cast_expr(rng: random.Random) -> Question:
    """Type an expression that casts text to int / float."""
    var = rng.choice(["user_num", "answer", "text", "num_text"])
    if rng.random() < 0.5:
        vals = rng.sample(range(2, 60), 4)
        cases = [({var: str(v)}, v) for v in vals]
        task = expression_task(f"int({var})", cases)
        prompt = f"`{var}` holds a whole number as text, such as `\"3\"`. Type an expression that gives it as an `int`."
        why = f"`int({var})` converts the string to a whole number."
    else:
        raw = ["3.5", "2", "10.25", "7", "0.5", "12.75", "4"]
        cases = [({var: v}, float(v)) for v in rng.sample(raw, 4)]
        task = expression_task(f"float({var})", cases)
        prompt = f"`{var}` holds a number as text, such as `\"3.5\"`. Type an expression that gives it as a `float`."
        why = f"`float({var})` converts the string to a decimal number (`\"2\"` becomes `2.0`)."
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=task, explanation=why)


@generator(TOPIC, EASY, qtype="code")
def gen_code_str_message(rng: random.Random) -> Question:
    """Type an expression that builds 'Score: 12' from a number."""
    var, label, _ = rng.choice([("score", "Score: ", 0), ("age", "Age: ", 0), ("coins", "Coins: ", 0), ("level", "Level: ", 0)])
    vals = rng.sample([3, 7, 12, 25, 40, 100, 250, 1000], 4)
    cases = [({var: v}, f"{label}{v}") for v in vals]
    task = expression_task(f'"{label}" + str({var})', cases)
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds a whole number such as `{vals[0]}`. Type an expression that gives the text `{label}{vals[0]}`.",
        task=task,
        explanation=f'You can\'t add a number to text, so use `"{label}" + str({var})` (or an f-string: `f"{label}{{{var}}}"`).',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_cast_statement(rng: random.Random) -> Question:
    """Write one line that casts a variable and stores the result."""
    kind = rng.choice(["int", "float", "str"])
    if kind == "int":
        src, dst = rng.choice([("age_text", "age"), ("count_text", "count"), ("score_text", "score")])
        values = [("16", 16), ("40", 40), ("7", 7), ("250", 250)]
        sol = f"{dst} = int({src})"
        prompt = f"`{src}` holds a whole number as text. Write one line that casts it to an `int` and stores it in `{dst}`."
    elif kind == "float":
        src, dst = rng.choice([("price_text", "price"), ("height_text", "height_m"), ("temp_text", "temperature")])
        values = [("2.5", 2.5), ("1.8", 1.8), ("10", 10.0), ("0.75", 0.75)]
        sol = f"{dst} = float({src})"
        prompt = f"`{src}` holds a number as text. Write one line that casts it to a `float` and stores it in `{dst}`."
    else:
        src, dst = rng.choice([("coins", "coins_text"), ("score", "score_text"), ("level", "level_text")])
        values = [(25, "25"), (7, "7"), (300, "300"), (1, "1")]
        sol = f"{dst} = str({src})"
        prompt = f"`{src}` holds a whole number. Write one line that casts it to a `str` and stores it in `{dst}`."
    cases = [Case(vars={src: v}, expect_vars={dst: w}) for v, w in values]
    task = program_task(sol, cases, starter="")
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        task=task,
        explanation=f"Casting makes a new value, so assign it: `{sol}`.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_bool_expr(rng: random.Random) -> Question:
    """Type an expression using bool()."""
    var = rng.choice(["name", "word", "nickname"])
    cases = [({var: v}, bool(v)) for v in rng.sample(["Ada", "", "Reid", "0", "hi", " "], 4)]
    if not any(not c[1] for c in cases):
        cases[0] = ({var: ""}, False)
    if all(not c[1] for c in cases):
        cases[1] = ({var: "hi"}, True)
    task = expression_task(f"bool({var})", cases, requires=[(r"\bbool\s*\(", "Use bool() for this one.")])
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds some text (it may be empty). Type an expression that uses `bool()` to give `False` for empty text and `True` otherwise.",
        task=task,
        explanation=f"`bool({var})` is `False` only for empty text; even `\"0\"` and `\" \"` are `True`.",
    )


_FN_SPECS = [
    ("double_it", "{p} * 2", "float", "double", ["2", "3.5", "10", "0.25", "7"]),
    ("triple_it", "{p} * 3", "float", "triple", ["2", "1.5", "10", "0.5", "4"]),
    ("half_it", "{p} / 2", "float", "half", ["4", "3", "10", "0.5", "7.5"]),
    ("add_five", "{p} + 5", "int", "five more than", ["2", "10", "0", "37", "100"]),
    ("add_ten", "{p} + 10", "int", "ten more than", ["5", "40", "0", "90", "250"]),
    ("minus_one", "{p} - 1", "int", "one less than", ["5", "1", "0", "90", "250"]),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_cast_function(rng: random.Random) -> Question:
    """Write a function that casts its text parameter and returns the result."""
    name, pattern, cast, word, vals = rng.choice(_FN_SPECS)
    param = rng.choice(["text", "num_text", "value", "user_num"])
    expr = pattern.format(p=f"{cast}({param})")
    solution = f"def {name}({param}):\n    return {expr}"
    ns: dict = {}
    exec(solution, ns)  # trusted reference solution, only used to build the expected values
    cases = [((v,), ns[name](v)) for v in vals]
    task = function_task(name, solution, fn_cases(cases))
    kind = "a float" if cast == "float" else "a whole number (int)"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{name}({param})` that takes text, casts it to `{cast}`, and returns {word} that number.",
        task=task,
        explanation=f"Cast first with `{cast}({param})`, then do the math. Use `return` (not `print`) so the caller gets {kind}.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_double_program(rng: random.Random) -> Question:
    """The Mini-Challenge 'Double It' (and variations)."""
    label, op, word = rng.choice([_DOUBLE_OPS[0], _DOUBLE_OPS[0], *_DOUBLE_OPS[1:]])
    ask = rng.choice(["Enter a number: ", "Pick a number: ", "Number: "])
    solution = f'n = input("{ask}")\nn = float(n)\nprint("{label}", n {op})'
    ops = {"* 2": lambda v: v * 2, "* 3": lambda v: v * 3, "/ 2": lambda v: v / 2, "+ 10": lambda v: v + 10,
           "* 5": lambda v: v * 5, "- 1": lambda v: v - 1}
    fn = ops[op]
    typed = list(dict.fromkeys([rng.choice(["4", "10", "2.5", "6"]), "0.5", "7", "2.5", "12"]))
    cases = [Case(stdin=[s], out=f"{label} {fn(float(s))}") for s in typed]
    task = program_task(solution, cases, starter=f'n = input("{ask}")\n')
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks the user for a number, casts it to `float`, and prints `{label}` followed by {word} the number. Typing `{typed[0]}` prints `{label} {fn(float(typed[0]))}`.",
        task=task,
        explanation=f"`input()` gives a string, so cast with `float()` before the math. `print(\"{label}\", n {op})` joins the pieces with a space.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_age_next_year(rng: random.Random) -> Question:
    """Read an age, cast to int, print a sentence with the changed age."""
    label, delta = rng.choice([("Next year you will be", 1), ("In 5 years you will be", 5), ("In 10 years you will be", 10), ("Last year you were", -1)])
    var = rng.choice(["age", "years_old"])
    ages = rng.sample(range(12, 19), 4)
    solution = f'{var} = int(input("How old are you? "))\nprint("{label}", {var} {"+" if delta > 0 else "-"} {abs(delta)})'
    cases = [Case(stdin=[str(a)], out=f"{label} {a + delta}") for a in ages]
    task = program_task(solution, cases, starter="")
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks for the user's age (a whole number) with `input()` and prints `{label}` followed by the new age. Typing `{ages[0]}` prints `{label} {ages[0] + delta}`.",
        task=task,
        explanation=f"Cast the text with `int()` so you can do math, then `print(\"{label}\", {var} {'+' if delta > 0 else '-'} {abs(delta)})`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_sum_two(rng: random.Random) -> Question:
    """Two inputs, cast both, print the total."""
    noun, label, op, opword = rng.choice(
        [("coins", "Total:", "+", "sum"), ("points", "Total:", "+", "sum"), ("eliminations", "Total:", "+", "sum"), ("coins", "Product:", "*", "product")]
    )
    solution = f"a = int(input())\nb = int(input())\nprint(\"{label}\", a {op} b)"
    pairs = rng.sample([(5, 7), (12, 30), (0, 9), (21, 4), (8, 8), (100, 25), (3, 6)], 4)
    fn = (lambda x, y: x + y) if op == "+" else (lambda x, y: x * y)
    cases = [Case(stdin=[str(x), str(y)], out=f"{label} {fn(x, y)}") for x, y in pairs]
    task = program_task(solution, cases, starter="")
    x0, y0 = pairs[0]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks for the {noun} from round 1 and then round 2 (two whole numbers, two `input()` calls) and prints `{label}` followed by their {opword}. Typing `{x0}` then `{y0}` prints `{label} {fn(x0, y0)}`.",
        task=task,
        explanation="Each `input()` returns a string, so cast both with `int()`; otherwise `+` would join the texts (`\"5\" + \"7\"` is `\"57\"`).",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_typed_anything(rng: random.Random) -> Question:
    """bool() of the text the user typed."""
    ask, var, story = rng.choice(
        [
            ("Type something: ", "text", "reads one line with `input()` and prints `True` if the user typed anything"),
            ("Enter your name: ", "name", "asks for the player's name and prints `True` if they typed a name"),
            ("Nickname: ", "nickname", "asks for a nickname and prints `True` if the user typed one"),
        ]
    )
    solution = f'{var} = input("{ask}")\nprint(bool({var}))'
    typed = ["", rng.choice(["hi", "Ada", "Reid", "Sam"]), rng.choice(["0", " ", "False"]), *rng.sample(["hello", "Python", "x", "2026"], 2)]
    rng.shuffle(typed)
    cases = [Case(stdin=[s], out=str(bool(s))) for s in typed]
    task = program_task(solution, cases, starter=f'{var} = input("{ask}")\n', requires=[(r"\bbool\s*\(", "Use bool() for this one.")])
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that {story}, or `False` if they just pressed Enter. Use `bool()`.",
        task=task,
        explanation=f"`bool({var})` is `False` only for empty text. Even `\"0\"` and a single space are `True`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_whole_part(rng: random.Random) -> Question:
    """int(float(text)): the decimal input fix from the Common Errors list."""
    label = rng.choice(["Whole part:", "Whole coins:", "Whole score:", "Whole number:"])
    solution = f'n = float(input("Enter a number: "))\nprint("{label}", int(n))'
    typed = ["7.8", "3.5", "10", "0.9", "12.99", "5"]
    cases = [Case(stdin=[s], out=f"{label} {int(float(s))}") for s in rng.sample(typed, 5)]
    task = program_task(solution, cases, starter="")
    first = cases[0]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that asks for a number (it may have a decimal point, like `7.8`) and prints `{label}` followed by the number with the decimal part cut off. Typing `{first.stdin[0]}` prints `{first.out}`.",
        task=task,
        explanation="`int(\"7.8\")` raises a ValueError, so cast with `float()` first and then `int()` to cut off the decimal part.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_total_price(rng: random.Random) -> Question:
    """float price * int quantity."""
    one, many = rng.choice([("apple", "apples"), ("ticket", "tickets"), ("pencil", "pencils"), ("sticker", "stickers"), ("card", "cards")])
    solution = 'price = float(input("Price: "))\nquantity = int(input("Quantity: "))\nprint("Total:", price * quantity)'
    combos = rng.sample([("2.5", "4"), ("1.25", "2"), ("0.75", "6"), ("4.5", "3"), ("10", "5"), ("3.75", "2"), ("6.5", "0")], 4)
    cases = [Case(stdin=[p, q], out=f"Total: {float(p) * int(q)}") for p, q in combos]
    task = program_task(solution, cases, starter="")
    p0, q0 = combos[0]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that asks for the price of one {one} (it may have decimals) and then how many {many} were bought (a whole number), and prints `Total:` followed by the cost. Typing `{p0}` then `{q0}` prints `Total: {float(p0) * int(q0)}`.",
        task=task,
        explanation="Cast the price with `float()` and the quantity with `int()`, then multiply: `print(\"Total:\", price * quantity)`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_name_age_sentence(rng: random.Random) -> Question:
    """name + age -> 'Ada will be 18 next year.'"""
    solution = 'name = input("Name: ")\nage = int(input("Age: "))\nprint(name + " will be " + str(age + 1) + " next year.")'
    people = rng.sample(PEOPLE, 4)
    ages = rng.sample(range(12, 20), 4)
    cases = [Case(stdin=[n, str(a)], out=f"{n} will be {a + 1} next year.") for n, a in zip(people, ages)]
    task = program_task(solution, cases, starter="")
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that asks for a name and then an age (a whole number) and prints `<name> will be <age + 1> next year.` For example, `{people[0]}` and `{ages[0]}` print `{cases[0].out}`",
        task=task,
        explanation="Cast the age with `int()` to add 1, then turn it back into text with `str()` (or use an f-string) to build the sentence.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_join_and_add(rng: random.Random) -> Question:
    """Join two typed numbers as text, then add them as numbers."""
    solution = (
        'first = input("First: ")\nsecond = input("Second: ")\n'
        'print("Joined:", first + second)\nprint("Sum:", int(first) + int(second))'
    )
    pairs = rng.sample([("12", "3"), ("4", "5"), ("20", "7"), ("8", "15"), ("1", "99"), ("30", "30"), ("6", "0")], 4)
    cases = [Case(stdin=[a, b], out=f"Joined: {a + b}\nSum: {int(a) + int(b)}") for a, b in pairs]
    task = program_task(solution, cases, starter="")
    a0, b0 = pairs[0]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that reads two numbers with `input()`, then prints `Joined:` with the two texts stuck together and, on the next line, `Sum:` with their sum as numbers. Typing `{a0}` then `{b0}` prints `Joined: {a0 + b0}` and `Sum: {int(a0) + int(b0)}`.",
        task=task,
        explanation="The two strings are joined with `+` as they are. For the sum, cast each with `int()` first.",
    )
