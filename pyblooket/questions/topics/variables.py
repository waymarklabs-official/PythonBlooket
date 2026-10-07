"""Question generators for the "variables" topic (CSF.2.A: Python Variables).

Everything here comes from the lesson `variables_lab.py`: what a variable is, the naming
rules (letters / numbers / underscores, no leading digit, case-sensitive), snake_case
variables and SCREAMING_SNAKE_CASE constants, reassignment (value AND type can change),
multiple assignment and swapping, `print` with commas vs `+`, f-strings, dynamic typing,
the lesson's "Common Mistakes" and the Mini-Challenge "Profile Line".

Formats: multiple choice, fill in the blanks, matching, and typed code (graded in the sandbox).
Typed code never needs functions here -- those are taught later (CSF.2.L).
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
    error_choice,
    expression_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "variables"

# The lesson's own people first (Ada, Reid, Sam), then a few more.
PEOPLE = ["Ada", "Reid", "Sam", "Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon", "Mia", "Noah", "Zoe"]
SCHOOLS = ["DBHS", "KHS", "DHS", "SMS", "TJHS", "BHS", "MHS"]



# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


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


def _out(difficulty, code, distractors, explanation, rng, prompt="What does this code print?", allow_error=False):
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=list(distractors),
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _shown(literal: str) -> str:
    """How print() shows a value that was written as ``literal`` in the code (1.80 -> 1.8, "Ada" -> Ada)."""
    return str(eval(literal))  # our own literals only


def _type_text(literal: str) -> str:
    return f"<class '{type(eval(literal)).__name__}'>"  # our own literals only


def _which_code(difficulty, prompt, setup, correct, wrong, ok, explanation, rng):
    """Choices are snippets of code.  ``ok(RunResult, snippet) -> bool`` says whether a snippet (run
    after ``setup``) does the job; the correct one is verified, and any "wrong" one that also does the
    job is dropped, so there is always exactly one right answer."""

    def passes(snippet: str) -> bool:
        res = run_code(f"{setup}\n{snippet}" if setup else snippet)
        return bool(ok(res, snippet))

    if not passes(correct):
        raise GenerationError(f"the 'correct' snippet does not do the job:\n{correct}")
    keep = [w for w in wrong if not passes(w)]
    return _q(difficulty, prompt, correct, keep, explanation, rng, code=setup or None)


def _styles(words: list[str]) -> dict[str, str]:
    """The same name written in the common styles."""
    snake = "_".join(words)
    return {
        "snake": snake,
        "camel": words[0] + "".join(w.title() for w in words[1:]),
        "pascal": "".join(w.title() for w in words),
        "screaming": snake.upper(),
        "kebab": "-".join(words),
        "spaced": " ".join(words),
    }


NAME_PAIRS = [
    "student_count", "high_score", "player_name", "total_points", "year_started", "lives_left", "first_name", "best_time",
    "coin_count", "game_level", "last_score", "money_left", "game_speed", "top_score", "time_left", "player_score",
    "class_size", "start_year", "last_name", "final_score",
]


def _pick_words(rng: random.Random) -> list[str]:
    """Two sensible words for a variable name, e.g. ['high', 'score']."""
    return rng.choice(NAME_PAIRS).split("_")


# ==========================================================================
# EASY  (choice)
# ==========================================================================


@generator(TOPIC, EASY)
def gen_variable_basics(rng: random.Random) -> Question:
    """Definition-style questions: what a variable is, what `=` does, name vs value."""
    shape = rng.choice(["box", "line", "symbol", "part", "create"])
    if shape == "box":
        return _q(
            EASY,
            rng.choice(["In Python, what is a variable?", "Which description of a variable is best?"]),
            "A named box that holds a value",
            rng.sample(
                [
                    "A command that shows text on the screen",
                    "A value that can never change",
                    "A file that stores the whole program",
                    "A symbol that does math",
                    "A message Python prints when something goes wrong",
                ],
                3,
            ),
            "A variable is a named box that holds a value. You create it by assigning a value to a name, like `age = 17`.",
            rng,
        )
    var, lit = rng.choice(
        [("age", "17"), ("score", "0"), ("name", '"Ada"'), ("gpa", "3.7"), ("is_student", "True"), ("temperature", "72"),
         ("height_m", "1.80"), ("year_started", "2023"), ("school", '"DBHS"'), ("money", "50")]
    )
    if shape == "line":
        return _q(
            EASY,
            f"What does the line `{var} = {lit}` do?",
            f"Stores the value {lit} in a variable named {var}",
            [f"Checks whether {var} is equal to {lit}", f"Prints {lit} on the screen", f"Stores the value {var} in a variable named {lit}",
             f"Deletes the variable {var}"],
            f"The `=` sign assigns: the value on the right ({lit}) is stored in the name on the left ({var}).",
            rng,
        )
    if shape == "symbol":
        return _q(
            EASY,
            "Which symbol assigns a value to a variable?",
            "=",
            ["==", "=>", "->", ":"],
            "A single `=` is assignment: it stores the value on the right in the variable on the left. (`==` compares two values.)",
            rng,
        )
    if shape == "part":
        ask_name = rng.choice([True, False])
        return _q(
            EASY,
            f"In the line `{var} = {lit}`, which part is the {'variable name' if ask_name else 'value being stored'}?",
            var if ask_name else lit,
            [lit if ask_name else var, "=", f"{var} = {lit}"],
            f"In `{var} = {lit}` the name `{var}` is on the left of `=` and the value `{lit}` is on the right.",
            rng,
        )
    text = rng.choice(PEOPLE)
    vname = rng.choice(["name", "first_name", "player", "student"])
    return _q(
        EASY,
        f"Which line creates a variable named `{vname}` that holds the text {text}?",
        f'{vname} = "{text}"',
        [f"{vname} = {text}", f'{vname} == "{text}"', f'"{text}" = {vname}', f'{vname} -> "{text}"'],
        f'Text needs quotes, and the name goes on the left of `=`. Without quotes (`{vname} = {text}`) Python looks for a variable called {text}.',
        rng,
    )


@generator(TOPIC, EASY)
def gen_valid_name(rng: random.Random) -> Question:
    """'Which of these is a valid variable name?'"""
    valid = rng.choice(
        ["student_count", "high_score", "player1", "level_2", "gpa", "height_m", "is_student", "total_points",
         "my_variable", "age2", "year_started", "best_time", "x1"]
    )
    digit_first = rng.choice(["1st_place", "2player", "3d_model", "9lives", "4th_try", "2nd_score"])
    hyphen_space = rng.choice(["high-score", "my-name", "is-student", "student count", "high score", "my name", "best-time"])
    symbol = rng.choice(["score$", "my@name", "gpa!", "total%", "name#", "level+1"])
    return _q(
        EASY,
        rng.choice(["Which of these is a valid variable name in Python?", "Which variable name is allowed in Python?"]),
        valid,
        [digit_first, hyphen_space, symbol],
        "Names can contain letters, numbers, and underscores, but they cannot start with a number. "
        "Hyphens, spaces and symbols are not allowed.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_snake_case_name(rng: random.Random) -> Question:
    """'Which variable name follows the snake_case convention?'"""
    s = _styles(_pick_words(rng))
    if rng.random() < 0.5:
        prompt = "Which variable name follows the snake_case convention?"
    else:
        prompt = "Which is the best variable name according to the course style (snake_case)?"
    return _q(
        EASY,
        prompt,
        s["snake"],
        [s["camel"], s["pascal"], s["kebab"]],
        f"snake_case means lowercase words joined with underscores: `{s['snake']}`. "
        f"`{s['camel']}` is camelCase, which is the style the lesson warns about.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_constant_name(rng: random.Random) -> Question:
    """Constants are written in SCREAMING_SNAKE_CASE."""
    const = rng.choice(
        ["MAX_USERS", "STUDENT_LIMIT", "PASSING_SCORE", "MAX_LIVES", "GAME_TITLE", "MAX_SCORE", "TIME_LIMIT", "CLASS_SIZE",
         "MIN_AGE", "PLAYER_LIMIT"]
    )
    words = const.lower().split("_")
    s = _styles(words)
    value = rng.choice(["32", "100", "5", "20", "3"]) if "TITLE" not in const else '"Blooket"'
    if rng.random() < 0.5:
        return _q(
            EASY,
            "By convention, which name is best for a constant?",
            const,
            [s["snake"], s["camel"], s["pascal"]],
            f"Constants are written in SCREAMING_SNAKE_CASE (all capitals with underscores), like `{const}`.",
            rng,
        )
    return _q(
        EASY,
        "Which line follows the course convention for a constant?",
        f"{const} = {value}",
        [f"{s['snake']} = {value}", f"{s['camel']} = {value}", f"{s['pascal']} = {value}"],
        f"By convention a constant is written in SCREAMING_SNAKE_CASE, like `{const} = {value}` (the lesson's example is `MAX_USERS = 32`).",
        rng,
    )


@generator(TOPIC, EASY)
def gen_case_sensitive_concept(rng: random.Random) -> Question:
    """Names are case-sensitive: score, Score and SCORE are different."""
    word = rng.choice(["score", "name", "age", "gpa", "count", "money", "level", "total"])
    a, b, c = word, word.title(), word.upper()
    shape = rng.choice(["three", "two"])
    if shape == "three":
        return _q(
            EASY,
            f"Which statement is true about the names `{a}`, `{b}`, and `{c}`?",
            "They are three different variables",
            [
                "They all refer to the same variable",
                f"Only `{a}` is allowed",
                "Python gives an error if you use more than one of them",
            ],
            f"Names are case-sensitive, so `{a}`, `{b}`, and `{c}` are three different variables.",
            rng,
        )
    return _q(
        EASY,
        f"Names in Python are case-sensitive. What does that mean for `{a}` and `{b}`?",
        "They are two different variable names",
        [
            "They are the same variable",
            f"`{b}` is only allowed for constants",
            "Python changes them both to lowercase",
        ],
        f"Case-sensitive means that upper- and lowercase letters count as different characters, so `{a}` and `{b}` are different names.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_type_of_value(rng: random.Random) -> Question:
    """`type(x)` of the lesson's values."""
    var, lit = rng.choice(
        [("name", '"Ada"'), ("age", "17"), ("height_m", "1.80"), ("is_student", "True"), ("gpa", "3.7"), ("score", "95"),
         ("temperature", "72"), ("is_raining", "False"), ("word", '"Python"'), ("money", "12.5"), ("count", "0"),
         ("school", '"DBHS"'), ("year_started", "2023")]
    )
    t = type(eval(lit)).__name__
    others = [f"<class '{n}'>" for n in ("int", "float", "str", "bool") if n != t]
    rng.shuffle(others)
    code = f"{var} = {lit}\nprint(type({var}))"
    return _out(
        EASY,
        code,
        [*others, t, "<class 'type'>"],
        f"`type({var})` shows the data type of the value stored in `{var}`: `{lit}` is a `{t}`.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_print_values_easy(rng: random.Random) -> Question:
    """print(name, height_m) -- values are shown without quotes, and 1.80 shows as 1.8."""
    name = rng.choice(PEOPLE)
    first, flit = rng.choice(
        [("height_m", "1.80"), ("height_m", "1.50"), ("height_m", "1.60"), ("height_m", "1.70"), ("gpa", "2.50"), ("gpa", "3.70"),
         ("gpa", "3.50"), ("gpa", "3.90"), ("money", "12.50"), ("temperature", "98.60")]
    )
    second_kind = rng.choice(["name", "age", "is_student"])
    if second_kind == "name":
        slit, svar = f'"{name}"', "name"
    elif second_kind == "age":
        slit, svar = str(rng.randint(14, 18)), "age"
    else:
        slit, svar = rng.choice(["True", "False"]), "is_student"
    order = rng.choice([(svar, first), (first, svar)])
    lits = {svar: slit, first: flit}
    code = f"{order[0]} = {lits[order[0]]}\n{order[1]} = {lits[order[1]]}\nprint({order[0]}, {order[1]})"
    shown = [_shown(lits[n]) for n in order]
    wrong = [
        f"{lits[order[0]]} {lits[order[1]]}",
        f"{shown[0]}, {shown[1]}",
        f"{shown[0]}{shown[1]}",
        f"{order[0]} {order[1]}",
    ]
    return _out(
        EASY,
        code,
        wrong,
        "`print` shows the values (no quotes around text) and joins them with a space. A float such as `"
        + flit
        + "` prints without the extra zero.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_print_comma_concept(rng: random.Random) -> Question:
    """'Which statement is true about print("My name is", name)?' and its + cousin."""
    var, label = rng.choice([("name", "My name is"), ("name", "Hello,"), ("age", "Age:"), ("score", "Score:"), ("gpa", "GPA:"), ("school", "School:")])
    if rng.random() < 0.6:
        return _q(
            EASY,
            f'Which statement is true about `print("{label}", {var})`?',
            "It joins the pieces with spaces automatically",
            rng.sample(
                [
                    f"It requires casting {var} to str",
                    "It removes spaces automatically",
                    f"It errors unless {var} is a number",
                    "It prints the pieces with no space between them",
                    f"It prints the word {var} instead of its value",
                ],
                3,
            ),
            "With commas, `print` puts a space between the pieces and does not care whether each piece is text or a number.",
            rng,
        )
    return _q(
        EASY,
        f'Which statement is true about `print("{label} " + {var})` when `{var}` holds text?',
        "It joins them exactly; you type any space yourself",
        rng.sample(
            [
                "It adds a space between the pieces automatically",
                "It prints the sum of the two values",
                "It works the same way even if the variable holds a number",
                "It prints the quotes as well",
                f"It prints the word {var} instead of its value",
            ],
            3,
        ),
        'The `+` operator glues strings together exactly as written, so any space you want must be inside the quotes (`"My name is " + name`).',
        rng,
    )


@generator(TOPIC, EASY)
def gen_show_value(rng: random.Random) -> Question:
    """Which line shows the value of a variable on the screen? (quiz: print() displays output)."""
    var = rng.choice(["age", "score", "name", "gpa", "money", "count"])
    return _q(
        EASY,
        f"Which line displays the value of `{var}` on the screen?",
        f"print({var})",
        rng.sample([f"show({var})", f"display({var})", f"input({var})", f"say({var})", f"{var}.print()"], 3),
        "`print()` is the built-in function that displays output on the screen. `input()` reads what the user types.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_best_constant(rng: random.Random) -> Question:
    """'Use constants for fixed values you don't plan to change.'"""
    fixed = rng.choice(
        [
            "the largest number of users allowed (32)",
            "the number of seats in the classroom (32)",
            "the score needed to pass (70)",
            "the number of days in a week (7)",
            "the title of the game",
            "the most lives a player can have (3)",
        ]
    )
    changing = rng.sample(
        [
            "the player's current score",
            "the number of lives left",
            "the name the user types in",
            "a running total",
            "the temperature right now",
            "how many questions were answered so far",
        ],
        3,
    )
    return _q(
        EASY,
        "Which value is the best choice for a constant (SCREAMING_SNAKE_CASE)?",
        fixed[0].upper() + fixed[1:],
        [c[0].upper() + c[1:] for c in changing],
        "Use a constant for a fixed value you don't plan to change. Scores, totals and user input change while the program runs, so they are normal variables.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_meaningful_name(rng: random.Random) -> Question:
    """Pro Tip: keep names meaningful -- gpa is clearer than x1."""
    pool = [
        ("a student's grade point average", "gpa", ["x1", "a", "thing", "stuff"]),
        ("the player's score", "score", ["s", "x2", "q", "thing"]),
        ("the number of lives a player has left", "lives", ["l", "n1", "data", "stuff"]),
        ("a person's age", "age", ["a", "x", "thing", "num1"]),
        ("the temperature in degrees", "temperature", ["t", "x3", "stuff", "val"]),
        ("a student's first name", "first_name", ["fn1", "x", "var2", "thing"]),
        ("the year a student started school", "year_started", ["y", "x1", "num", "stuff"]),
        ("how much money a player has", "money", ["m", "x4", "stuff", "data"]),
        ("a person's height in meters", "height_m", ["h", "x5", "thing", "val"]),
    ]
    desc, good, bad = rng.choice(pool)
    return _q(
        EASY,
        f"Which is the most meaningful name for a variable that stores {desc}?",
        good,
        rng.sample(bad, 3),
        f"Keep names meaningful: `{good}` tells the reader what the variable holds, while names like `x1` do not.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_file_name(rng: random.Random) -> Question:
    """snake_case is also used for file names (variables_lab.py)."""
    first = rng.choice(["variables", "datatypes", "strings", "casting", "loops", "functions", "my"])
    second = rng.choice(["lab", "mini_challenge", "practice", "project"])
    words = [first, *second.split("_")]
    s = _styles(words)
    return _q(
        EASY,
        "Which file name follows the snake_case convention from the lab?",
        f"{s['snake']}.py",
        [f"{s['camel']}.py", f"{s['pascal']}.py", f"{s['spaced']}.py"],
        f"The lesson uses snake_case for variables and for files: `{s['snake']}.py`, like `variables_lab.py`.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_run_command(rng: random.Random) -> Question:
    """Run Your Code: python3 variables_lab.py"""
    fname = rng.choice(["variables_lab.py", "variables_mini_challenge.py", "datatypes_lab.py", "strings_lab.py", "casting_lab.py"])
    stem = fname[:-3]
    return _q(
        EASY,
        f"Which command runs `{fname}` from the VS Code terminal?",
        f"python3 {fname}",
        [f"python3 {stem}", f"run {fname}", f"{fname} python3", f"open python3 {fname}"],
        f"In the integrated terminal you type `python3` followed by the file name, including `.py`: `python3 {fname}`.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_multi_assign_value(rng: random.Random) -> Question:
    """x, y, z = 1, 2, 3  -- what is y?"""
    names = rng.choice([("x", "y", "z"), ("a", "b", "c"), ("first", "second", "third"), ("red", "green", "blue")])
    vals = rng.choice([(1, 2, 3), (10, 20, 30), (5, 6, 7), (4, 8, 12), (7, 14, 21), (2, 4, 6)])
    k = rng.randrange(3)
    one = rng.random() < 0.6
    if one:
        show_names = [names[k]]
        correct = str(vals[k])
        wrong = [str(v) for i, v in enumerate(vals) if i != k] + [f"{vals[0]} {vals[1]} {vals[2]}", names[k]]
    else:
        j = rng.choice([i for i in range(3) if i != k])
        show_names = [names[k], names[j]]
        correct = f"{vals[k]} {vals[j]}"
        wrong = [f"{vals[j]} {vals[k]}", f"{vals[0]} {vals[1]} {vals[2]}", f"{vals[k]} {vals[k]}", f"{names[k]} {names[j]}"]
    code = f"{', '.join(names)} = {', '.join(map(str, vals))}\nprint({', '.join(show_names)})"
    return _out(
        EASY,
        code,
        wrong,
        "Multiple assignment matches the names and the values by position: the first name gets the first value, the second name the second value, and so on.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_fstring_output(rng: random.Random) -> Question:
    """What an f-string prints (and what it prints without the f)."""
    name = rng.choice(PEOPLE)
    age = rng.randint(13, 18)
    shape = rng.choice(["two", "literal", "one", "limit"])
    if shape == "two":
        setup = f'name = "{name}"\nage = {age}'
        template = "{name} is {age} years old."
        values = {"name": name, "age": str(age)}
    elif shape == "literal":
        setup = f'name = "{name}"'
        template = "{name} is {17} years old."
        values = {"name": name, "17": "17"}
    elif shape == "one":
        setup = f'name = "{name}"'
        template = "My name is {name}"
        values = {"name": name}
    else:
        lim = rng.choice([32, 30, 25, 40])
        setup = f"STUDENT_LIMIT = {lim}"
        template = "Limit: {STUDENT_LIMIT}"
        values = {"STUDENT_LIMIT": str(lim)}
    code = f'{setup}\nprint(f"{template}")'
    correct = re.sub(r"\{(\w+)\}", lambda m: values[m.group(1)], template)
    bare = re.sub(r"\{(\w+)\}", lambda m: m.group(1), template)
    first_only = re.sub(r"\{(\w+)\}", lambda m: values[m.group(1)], template, count=1)
    wrong = [template, bare, first_only, f'"{correct}"']
    return _out(
        EASY,
        code,
        wrong,
        "The `f` in front of the quotes makes Python replace each `{...}` with the value inside it. Without the `f`, the braces would be printed as plain text.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_which_fstring_line(rng: random.Random) -> Question:
    """'Which line prints X using an f-string?' -- every choice is run."""
    name = rng.choice(PEOPLE)
    age = rng.randint(13, 18)
    setup = f'name = "{name}"\nage = {age}'
    target = f"{name} is {age}"
    correct = 'print(f"{name} is {age}")'
    wrong = [
        'print("{name} is {age}")',
        'print(f"name is age")',
        'print("f{name} is f{age}")',
        'print(f"{name}" + " is " + age)',
        'print(f{name} is {age})',
    ]
    rng.shuffle(wrong)
    return _which_code(
        EASY,
        f"Which line uses an f-string to print `{target}`?",
        setup,
        correct,
        wrong,
        lambda r, s: not r.error and r.output == target,
        'An f-string starts with `f` before the opening quote, and puts the variable names inside braces: `f"{name} is {age}"`.',
        rng,
    )


@generator(TOPIC, EASY)
def gen_dynamic_typing_concept(rng: random.Random) -> Question:
    """The quiz's 'dynamically typed' questions, in a few wordings."""
    items = [
        (
            "Python is “dynamically typed” because…",
            "the type is decided by the value assigned",
            ["you must declare types like `int x`", "variables can never change type", "only strings have types",
             "every variable is a string until you cast it"],
        ),
        (
            "What does “dynamic typing” mean in Python?",
            "The type comes from the value and can change later",
            ["Variables must be declared with a fixed type", "Variables automatically convert to strings when printed",
             "Python prevents reassignment once a variable is created", "Variables can only hold numbers"],
        ),
        (
            "Do you have to declare a variable's type (like `int age`) before you use it in Python?",
            "No - the type comes from the value you assign",
            ["Yes - you must write the type first", "Yes - but only for numbers", "No - every variable is a string by default"],
        ),
        (
            "In Python, can a variable that holds a number later hold text?",
            "Yes - assigning a new value can change its type",
            ["No - the variable keeps its first type forever", "Only if you cast the number with `str()` first",
             "Only if the name is written in SCREAMING_SNAKE_CASE"],
        ),
        (
            "What does `type(value)` return?",
            "The value's data type",
            ["The value's memory address", "The value as a string", "The number of characters in the value"],
        ),
        (
            "After `age = 17` and then `age = \"seventeen\"`, what happened to `age`?",
            "It now holds a str, so its type changed",
            ["Python raised an error because age was already an int", "It still holds an int", "It holds both values at once"],
        ),
    ]
    prompt, correct, wrong = rng.choice(items)
    return _q(
        EASY,
        prompt,
        correct,
        rng.sample(wrong, 3),
        "Python is dynamically typed: the type is decided by the value you assign, and assigning a new value can change it (the lesson changes `age` from an int to a str).",
        rng,
    )


# ==========================================================================
# MEDIUM  (choice)
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_reassign_type_trace(rng: random.Random) -> Question:
    """The lesson's reassignment: age = 17 then age = "seventeen" -- value AND type change."""
    var, v1, v2 = rng.choice(
        [
            ("age", "17", '"seventeen"'),
            ("age", "16", '"sixteen"'),
            ("score", "10", '"ten"'),
            ("count", "3", "3.5"),
            ("gpa", "3.5", "4"),
            ("is_student", "True", '"yes"'),
            ("temperature", "72", "72.5"),
            ("name", '"Ada"', "17"),
            ("level", "1", '"one"'),
            ("grade", '"A"', "95"),
            ("height_m", "1.80", '"tall"'),
            ("money", "50", "True"),
        ]
    )
    t1, t2 = type(eval(v1)).__name__, type(eval(v2)).__name__
    code = f'{var} = {v1}\n{var} = {v2}\nprint("{var} is now:", {var}, type({var}))'
    s1, s2 = _shown(v1), _shown(v2)
    wrong = [
        f"{var} is now: {s1} <class '{t1}'>",
        f"{var} is now: {s2} <class '{t1}'>",
        f"{var} is now: {s2} {t2}",
        f"{var} is now: {s1} <class '{t2}'>",
    ]
    return _out(
        MEDIUM,
        code,
        wrong,
        f"Reassignment replaces the old value, and the type changes with it: `{var}` now holds `{v2}`, a `{t2}`.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_reassign_value(rng: random.Random) -> Question:
    """Overwrite / update using the old value / copy then change."""
    x, y = rng.sample(["score", "money", "count", "level", "points", "total", "lives", "coins"], 2)
    shape = rng.choice(["overwrite", "update", "copy"])
    if shape == "overwrite":
        a, b = rng.sample(range(2, 40), 2)
        code = f"{x} = {a}\n{x} = {b}\nprint({x})"
        wrong = [str(a), str(a + b), f"{a} {b}", str(abs(a - b))]
        why = f"The second assignment replaces the first value: `{x}` is {b} now, and the old {a} is gone."
    elif shape == "update":
        op = rng.choice("+-*")
        b = rng.randint(2, 9)
        a = rng.randint(b + 2, 20) if op == "-" else rng.randint(3, 15)
        code = f"{x} = {a}\n{x} = {x} {op} {b}\nprint({x})"
        result = eval(f"{a} {op} {b}")
        other = {"+": a * b, "-": a + b, "*": a + b}[op]
        wrong = [str(a), str(b), str(other), str(result + 1)]
        why = (
            f"Python works out the right side first with the current value of `{x}` ({a} {op} {b} = {result}) "
            f"and then stores the answer back in `{x}`."
        )
    else:
        a, b = rng.sample(range(2, 40), 2)
        code = f"{x} = {a}\n{y} = {x}\n{x} = {b}\nprint({x}, {y})"
        wrong = [f"{b} {b}", f"{a} {a}", f"{a} {b}", f"{b}"]
        why = f"`{y} = {x}` copies the value {a} into `{y}`. Changing `{x}` afterwards does not change `{y}`."
    return _out(MEDIUM, code, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_swap_trace(rng: random.Random) -> Question:
    """The lesson's swap: x, y = y, x."""
    x, y, z = rng.choice([("x", "y", "z"), ("a", "b", "c"), ("first", "second", "third"), ("left", "right", "middle")])
    a, b, c = rng.choice([(1, 2, 3), (10, 20, 30)]) if rng.random() < 0.3 else rng.sample(range(1, 30), 3)
    show_z = rng.random() < 0.4
    shown = f"{x}, {y}, {z}" if show_z else f"{x}, {y}"
    code = f'{x}, {y}, {z} = {a}, {b}, {c}\n{x}, {y} = {y}, {x}\nprint("swapped:", {shown})'
    tail = f" {c}" if show_z else ""
    wrong = [f"swapped: {a} {b}{tail}", f"swapped: {b} {b}{tail}", f"swapped: {a} {a}{tail}", f"swapped: {b} {a}{' ' + str(a) if show_z else ''}"]
    return _out(
        MEDIUM,
        code,
        wrong,
        f"`{x}, {y} = {y}, {x}` swaps the two values at the same time: `{x}` gets {b} and `{y}` gets {a}."
        + (f" `{z}` is not touched." if show_z else ""),
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_which_swap(rng: random.Random) -> Question:
    """'Which code swaps the values of x and y?' -- every choice is run."""
    x, y = rng.choice([("x", "y"), ("a", "b"), ("first", "second"), ("left", "right")])
    a, b = rng.sample(range(1, 30), 2)
    setup = f"{x} = {a}\n{y} = {b}"
    correct = f"{x}, {y} = {y}, {x}"
    wrong = [
        f"{x} = {y}\n{y} = {x}",
        f"{y} = {x}\n{x} = {y}",
        f"{x}, {y} = {x}, {y}",
        f"{x} == {y}",
        f"swap({x}, {y})",
    ]
    rng.shuffle(wrong)
    return _which_code(
        MEDIUM,
        f"Which code swaps the values of `{x}` and `{y}`?",
        setup,
        correct,
        wrong,
        lambda r, s: not r.error and r.namespace.get(x) == b and r.namespace.get(y) == a,
        f"`{x}, {y} = {y}, {x}` evaluates both values first and then assigns them. Writing `{x} = {y}` first would overwrite `{x}` and lose its old value.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_which_print_line(rng: random.Random) -> Question:
    """'Which line prints My name is Ada?' -- comma, + with a space, or an f-string."""
    name = rng.choice(PEOPLE)
    label = rng.choice(["My name is", "Hello,", "Welcome,", "Player:", "Hi", "Student:"])
    setup = f'name = "{name}"'
    target = f"{label} {name}"
    correct = rng.choice([f'print("{label}", name)', f'print("{label} " + name)', f'print(f"{label} {{name}}")'])
    wrong = [
        f'print("{label}" + name)',
        f'print("{label}", "name")',
        f'print("{label} name")',
        f'print("{label} {{name}}")',
        f'print(f"{label} name")',
        f'print("{label}" name)',
    ]
    rng.shuffle(wrong)
    return _which_code(
        MEDIUM,
        f"Which line prints `{target}`?",
        setup,
        correct,
        wrong,
        lambda r, s: not r.error and r.output == target,
        'Commas make `print` add a space; with `+` you must type the space yourself; an f-string needs the `f` and the variable inside `{}`. Quotes around `name` print the word itself.',
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_comma_vs_plus_output(rng: random.Random) -> Question:
    """print("Hello,", name) vs print("Hello," + name)"""
    name = rng.choice(PEOPLE)
    word = rng.choice(["Hello,", "Hi", "Welcome,", "Go", "Player:"])
    plus_space = rng.random() < 0.5
    comma_line = f'print("{word}", name)'
    plus_line = f'print("{word} " + name)' if plus_space else f'print("{word}" + name)'
    lines = [comma_line, plus_line]
    rng.shuffle(lines)
    code = f'name = "{name}"\n' + "\n".join(lines)
    spaced, glued = f"{word} {name}", f"{word}{name}"
    outs = {comma_line: spaced, plus_line: spaced if plus_space else glued}
    results = [outs[line] for line in lines]
    combos = [[spaced, spaced], [spaced, glued], [glued, spaced], [glued, glued]]
    wrong = ["\n".join(c) for c in combos if c != results]
    if plus_space:
        why = (
            f'Both lines print `{spaced}`: the comma makes `print` add a space, and in the `+` line the space was typed inside the quotes (`"{word} "`).'
        )
    else:
        why = (
            f'The comma line prints `{spaced}` because `print` adds a space. The `+` line has no space inside its quotes, so it prints `{glued}`.'
        )
    return _out(MEDIUM, code, wrong, why, rng)


@generator(TOPIC, MEDIUM)
def gen_name_error_quotes(rng: random.Random) -> Question:
    """Common mistake: name = Ada (no quotes)."""
    var, value = rng.choice(
        [("name", "Ada"), ("name", "Reid"), ("school", "DBHS"), ("color", "blue"), ("pet", "Rex"), ("city", "Kingsport"), ("name", "Sam")]
    )
    if rng.random() < 0.65:
        code = f"{var} = {value}\nprint({var})"
        return _out(
            MEDIUM,
            code,
            [value, var, error_choice("TypeError"), error_choice("SyntaxError")],
            f'Without quotes, Python thinks `{value}` is the name of a variable. No such variable exists, so you get a NameError. The fix is `{var} = "{value}"`.',
            rng,
            prompt="What is printed, or which error is raised?",
            allow_error=True,
        )
    return _q(
        MEDIUM,
        f"Why does `{var} = {value}` cause an error?",
        f"Without quotes, Python looks for a variable named {value}",
        [
            "Variable names cannot contain capital letters",
            f"`{var}` is not allowed as a variable name",
            "Text can only be assigned with `==`",
        ],
        f'Text needs quotes. Without them Python treats `{value}` as a variable name that does not exist. The fix is `{var} = "{value}"`.',
        rng,
        code=f"{var} = {value}",
    )


@generator(TOPIC, MEDIUM)
def gen_concat_type_error(rng: random.Random) -> Question:
    """Common mistake: mixing a string and a number with + (no casting)."""
    var, value, label = rng.choice(
        [("age", 17, "Age"), ("score", 95, "Score"), ("gpa", 3.7, "GPA"), ("year_started", 2023, "Year"), ("STUDENT_LIMIT", 32, "Limit"),
         ("level", 4, "Level"), ("money", 50, "Money")]
    )
    code = f'{var} = {value}\nprint("{label}: " + {var})'
    return _out(
        MEDIUM,
        code,
        [f"{label}: {value}", f"{label}:{value}", error_choice("NameError"), f"{label}: {var}"],
        f'You cannot add a string and a number with `+`. Use `str({var})`, an f-string, or a comma: `print("{label}:", {var})`.',
        rng,
        prompt="What is printed, or which error is raised?",
        allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_fix_concat_line(rng: random.Random) -> Question:
    """Which line fixes print("Age: " + age)?  -- every choice is run."""
    var, value, label = rng.choice([("age", 17, "Age"), ("score", 95, "Score"), ("level", 4, "Level"), ("gpa", 3.7, "GPA"), ("money", 50, "Money")])
    setup = f"{var} = {value}"
    target = f"{label}: {value}"
    correct = rng.choice([f'print("{label}: " + str({var}))', f'print("{label}:", {var})', f'print(f"{label}: {{{var}}}")'])
    wrong = [
        f'print("{label}: " + int({var}))',
        f'print("{label}:" + str({var}))',
        f'print("{label}: " - {var})',
        f'print("{label}: " + "{var}")',
        f'print("{label}: {{{var}}}")',
    ]
    rng.shuffle(wrong)
    return _which_code(
        MEDIUM,
        f'`print("{label}: " + {var})` crashes. Which line fixes it so it prints `{target}`?',
        setup,
        correct,
        wrong,
        lambda r, s: not r.error and r.output == target,
        f"Mixing a string and a number with `+` is a classic mistake. Turn the number into text with `str({var})`, use a comma, or use an f-string.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_typo_name_error(rng: random.Random) -> Question:
    """Common mistake: studentCount vs student_count (names must match exactly)."""
    words = _pick_words(rng)
    s = _styles(words)
    var = s["snake"]
    value = rng.choice(["24", "980", "2023", '"Ada"', "12.5", "30"])
    kind = rng.choice(["camel", "pascal", "case"])
    typo = {"camel": s["camel"], "pascal": s["pascal"], "case": var.upper()}[kind]
    code = f"{var} = {value}\nprint({typo})"
    return _out(
        MEDIUM,
        code,
        [_shown(value), var, typo, error_choice("TypeError")],
        f"`{typo}` and `{var}` are different names (names are case-sensitive and underscores matter). `{typo}` was never created, so Python raises a NameError.",
        rng,
        prompt="What is printed, or which error is raised?",
        allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_invalid_name_reason(rng: random.Random) -> Question:
    """Why is `2nd_place = "Sam"` not allowed?"""
    digit = "A name cannot start with a number"
    chars = "A name can only contain letters, numbers, and underscores"
    items = [
        ('2nd_place = "Sam"', digit, chars),
        ("1st_score = 95", digit, chars),
        ("3d_model = True", digit, chars),
        ("high-score = 100", chars, digit),
        ('my name = "Ada"', chars, digit),
        ("year started = 2023", chars, digit),
        ("gpa$ = 3.7", chars, digit),
    ]
    line, correct, other_rule = rng.choice(items)
    return _q(
        MEDIUM,
        f"Why is `{line}` not allowed?",
        correct,
        [other_rule, "Names must be written in all lowercase letters", "Names cannot contain underscores", "The value must be written in SCREAMING_SNAKE_CASE"],
        "Names can contain letters, numbers, and underscores, but they cannot start with a number. Spaces, hyphens and symbols are not allowed either.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_find_bad_line(rng: random.Random) -> Question:
    """Which line of this lab code has a mistake?  (each line is run on its own)"""
    valid = [
        'name = "Ada"', "age = 17", "height_m = 1.80", "is_student = True", "gpa = 3.7", "score = 0", "high_score = 100",
        'school = "DBHS"', "year_started = 2023", "MAX_USERS = 32", 'player_name = "Sam"', "lives = 3", "student_count = 24",
    ]
    invalid = [
        ('2nd_place = "Sam"', "A name cannot start with a number, so `2nd_place` is not allowed."),
        ("1st_score = 95", "A name cannot start with a number, so `1st_score` is not allowed."),
        ("high-score = 100", "A hyphen is not allowed in a name (only letters, numbers, and underscores)."),
        ('my name = "Ada"', "A space is not allowed in a name (only letters, numbers, and underscores)."),
        ("year started = 2023", "A space is not allowed in a name (only letters, numbers, and underscores)."),
        ("school = DBHS", 'The text needs quotes: `school = "DBHS"`. Without them Python looks for a variable named DBHS.'),
        ("pet = Rex", 'The text needs quotes: `pet = "Rex"`. Without them Python looks for a variable named Rex.'),
        ("is_student = true", "Python's boolean is `True` with a capital T (names are case-sensitive), so `true` is just an unknown name."),
        ("gpa$ = 3.7", "A `$` is not allowed in a name (only letters, numbers, and underscores)."),
    ]
    bad, why = rng.choice(invalid)
    bad_name = re.split(r"\s*=", bad)[0]
    pool = [v for v in valid if v.split(" =")[0] != bad_name]
    lines = rng.sample(pool, 3)
    for ln in lines:
        if run_code(ln).error:
            raise GenerationError(f"valid line fails: {ln}")
    if not run_code(bad).error:
        raise GenerationError(f"bad line does not fail: {bad}")
    lines.append(bad)
    rng.shuffle(lines)
    return _q(
        MEDIUM,
        "Three of these lines are fine but one has a mistake. Which one?",
        bad,
        [ln for ln in lines if ln != bad],
        why,
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_case_sensitive_trace(rng: random.Random) -> Question:
    """score and Score are two different variables."""
    word = rng.choice(["score", "points", "count", "level", "money", "total", "age"])
    w1, w2, w3 = word, word.title(), word.upper()
    three = rng.random() < 0.4
    vals = rng.sample(range(2, 40), 3)
    if three:
        code = f"{w1} = {vals[0]}\n{w2} = {vals[1]}\n{w3} = {vals[2]}\nprint({w1}, {w2}, {w3})"
        a, b, c = vals
        wrong = [f"{c} {c} {c}", f"{a} {a} {a}", f"{c} {b} {a}", f"{a} {b} {a}"]
    else:
        code = f"{w1} = {vals[0]}\n{w2} = {vals[1]}\nprint({w1}, {w2})"
        a, b = vals[:2]
        wrong = [f"{b} {b}", f"{a} {a}", f"{b} {a}", f"{a + b}"]
    return _out(
        MEDIUM,
        code,
        wrong,
        "Names are case-sensitive, so each spelling is its own variable with its own value. Nothing is overwritten.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_constant_concept(rng: random.Random) -> Question:
    """SCREAMING_SNAKE_CASE is a convention -- Python does not stop you from reassigning."""
    const = rng.choice(["MAX_USERS", "STUDENT_LIMIT", "PASSING_SCORE", "MAX_LIVES", "TIME_LIMIT"])
    if rng.random() < 0.5:
        return _q(
            MEDIUM,
            f"Which statement about a constant such as `{const}` is true?",
            "The capital letters only signal: do not change this",
            [
                "Python raises an error if you assign to it again",
                "It can only hold a number",
                "Python stores it in a special place and never changes it",
            ],
            "By convention, constants are written in SCREAMING_SNAKE_CASE to tell other programmers not to change them. Python itself does not enforce it.",
            rng,
        )
    a, b = rng.sample([10, 20, 25, 30, 32, 40, 50, 100], 2)
    code = f'{const} = {a}\n{const} = {b}\nprint("Value:", {const})'
    return _out(
        MEDIUM,
        code,
        [f"Value: {a}", f"Value: {a} {b}", f"Value: {const}", f"Value: {a + b}"],
        f"A constant is only a naming convention. Python lets you assign to `{const}` again, so it now holds {b}.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_type_gotchas(rng: random.Random) -> Question:
    """Quotes make text; a decimal point makes a float."""
    var, lit = rng.choice(
        [("age", '"17"'), ("score", '"100"'), ("is_student", '"True"'), ("gpa", '"3.7"'), ("count", "5.0"), ("temperature", "72.0"),
         ("word", '"5"'), ("is_raining", '"False"'), ("height_m", "1.0"), ("year_started", '"2023"'), ("money", "10.50"), ("flag", "False")]
    )
    t = type(eval(lit)).__name__
    others = [f"<class '{n}'>" for n in ("int", "float", "str", "bool") if n != t]
    code = f"{var} = {lit}\nprint(type({var}))"
    if t == "str":
        why = f"Anything inside quotes is a string, even if it looks like a number or `True`: `{lit}` is a `str`."
    elif t == "float":
        why = f"A number with a decimal point is a float, even when it ends in `.0`: `{lit}` is a `float`."
    else:
        why = f"`{lit}` is a `{t}`."
    return _out(MEDIUM, code, [*others, "<class 'type'>"], why, rng)


@generator(TOPIC, MEDIUM)
def gen_which_changes_type(rng: random.Random) -> Question:
    """Which code changes the *type* of x (not just its value)?"""
    v = rng.choice(["x", "age", "score", "value", "data"])
    change = [("5", '"five"'), ('"5"', "5"), ("2.5", "2"), ("True", '"yes"'), ("10", "10.5"), ('"Ada"', "17"), ("3.5", '"3.5"')]
    same = [("5", "10"), ('"5"', '"10"'), ("2.5", "7.5"), ("True", "False"), ('"Ada"', '"Sam"'), ("17", "18")]
    a, b = rng.choice(change)
    correct = f"{v} = {a}\n{v} = {b}"
    wrong = [f"{v} = {p}\n{v} = {q}" for p, q in rng.sample(same, 3)]
    wrong.append(rng.choice([f"{v} = 5\n{v} = {v} + 1", f"{v} = 20\n{v} = {v} - 5"]))

    def changes(res, snippet):
        first = snippet.split("\n")[0].split(" = ", 1)[1]
        return not res.error and type(res.namespace[v]) is not type(eval(first))

    return _which_code(
        MEDIUM,
        f"Which code changes the type of `{v}`, not just its value?",
        "",
        correct,
        wrong,
        changes,
        f"Python is dynamically typed, so a new value can bring a new type: `{v}` starts as `{a}` and becomes `{b}`.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_multi_assign_trace(rng: random.Random) -> Question:
    """Multiple assignment followed by one or two reassignments."""
    a, b, c = rng.choice([("a", "b", "c"), ("x", "y", "z"), ("first", "second", "third")])
    va, vb, vc = rng.sample(range(2, 40), 3)
    stmts = [(f"{b} = {c}", f"{c} = {b}"), (f"{a} = {b}", f"{b} = {a}"), (f"{c} = {a}", f"{a} = {c}"), (f"{b} = {a}", f"{a} = {b}")]
    n = rng.choice([1, 2])
    chosen = rng.sample(stmts, n)
    head = f"{a}, {b}, {c} = {va}, {vb}, {vc}"
    body = "\n".join(s for s, _ in chosen)
    tail = f"print({a}, {b}, {c})"
    code = f"{head}\n{body}\n{tail}"
    reverse = "\n".join(r for _, r in chosen)
    wrong = [
        f"{va} {vb} {vc}",
        run_code(f"{head}\n{reverse}\n{tail}").output,
        run_code(f"{head}\n{a}, {b} = {b}, {a}\n{body}\n{tail}").output,
        f"{vc} {vb} {va}",
    ]
    return _out(
        MEDIUM,
        code,
        wrong,
        "Follow the lines from top to bottom. `x = y` copies the value on the right into the name on the left, and only that name changes.",
        rng,
    )


# ==========================================================================
# HARD  (choice)
# ==========================================================================


@generator(TOPIC, HARD)
def gen_rotate_three(rng: random.Random) -> Question:
    """a, b, c = b, c, a -- the right side is worked out first, so nothing is lost."""
    a, b, c = rng.choice([("a", "b", "c"), ("x", "y", "z"), ("first", "second", "third")])
    va, vb, vc = rng.sample(range(1, 30), 3)
    left = rng.random() < 0.5
    rhs = f"{b}, {c}, {a}" if left else f"{c}, {a}, {b}"
    head = f"{a}, {b}, {c} = {va}, {vb}, {vc}"
    code = f"{head}\n{a}, {b}, {c} = {rhs}\nprint({a}, {b}, {c})"
    sequential = f"{a} = {b}\n{b} = {c}\n{c} = {a}" if left else f"{a} = {c}\n{b} = {a}\n{c} = {b}"
    seq_out = run_code(f"{head}\n{sequential}\nprint({a}, {b}, {c})").output
    wrong = [
        seq_out,
        f"{va} {vb} {vc}",
        f"{vc} {vb} {va}",
        f"{vb} {va} {vc}",
        f"{vc} {va} {vb}" if left else f"{vb} {vc} {va}",
    ]
    return _out(
        HARD,
        code,
        wrong,
        "Python works out the whole right side first (using the old values) and only then assigns, so the values move together and none is lost.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_same_name_new_type(rng: random.Random) -> Question:
    """The same name holds text, then a number -- and + behaves differently."""
    var = rng.choice(["item", "amount", "value", "data", "entry"])
    p, q = rng.sample(range(1, 10), 2)
    code = f'{var} = "{p}"\nprint({var} + "{q}")\n{var} = {p}\nprint({var} + {q})'
    return _out(
        HARD,
        code,
        [f"{p + q}\n{p + q}", f"{p}{q}\n{p}{q}", f"{p + q}\n{p}{q}", f"{p}{q}\nError: TypeError"],
        f'While `{var}` holds the string `"{p}"`, `+` glues text together (`{p}{q}`). After it is reassigned to the number {p}, `+` adds ({p + q}).',
        rng,
    )


@generator(TOPIC, HARD)
def gen_count_matching_lines(rng: random.Random) -> Question:
    """How many of these lines print exactly `Name: Ada`?  (each line is run)"""
    var, label, value = rng.choice(
        [("name", "Name:", rng.choice(PEOPLE)), ("school", "School:", rng.choice(SCHOOLS)), ("player", "Player:", rng.choice(PEOPLE))]
    )
    good = [f'print("{label}", {var})', f'print("{label} " + {var})', f'print(f"{label} {{{var}}}")']
    bad = [
        f'print("{label}" + {var})',
        f'print("{label} {var}")',
        f'print(f"{label} {var}")',
        f'print("{label}", "{var}")',
        f'print("{label} {{{var}}}")',
        f'print({var}, "{label}")',
    ]
    k = rng.choice([1, 2, 2, 3])
    lines = rng.sample(good, k) + rng.sample(bad, 4 - k)
    rng.shuffle(lines)
    setup = f'{var} = "{value}"'
    target = f"{label} {value}"
    real = sum(1 for ln in lines if (lambda r: not r.error and r.output == target)(run_code(f"{setup}\n{ln}")))
    if real != k:
        raise GenerationError("line count mismatch")
    wrong = [str(n) for n in range(0, 5) if n != k]
    rng.shuffle(wrong)
    return _q(
        HARD,
        f"How many of these four print lines print exactly `{target}`?",
        str(k),
        wrong,
        f'Check each line: a comma adds a space; `+` needs the space inside the quotes; an f-string needs the `f` and `{{{var}}}`; quotes around `{var}` print the word itself.',
        rng,
        code=f"{setup}\n" + "\n".join(lines),
    )


@generator(TOPIC, HARD)
def gen_crash_midway(rng: random.Random) -> Question:
    """What prints before the mistake stops the program?"""
    scenario = rng.choice(["type", "typo", "quotes"])
    name = rng.choice(PEOPLE)
    if scenario == "type":
        age = rng.randint(13, 18)
        code = f'name = "{name}"\nage = {age}\nprint("Name: " + name)\nprint("Age: " + age)\nprint("Done")'
        fixed = code.replace('"Age: " + age', '"Age: " + str(age)')
        error = "TypeError"
        before = f"Name: {name}"
        why = "The program runs from the top. The first `print` works, but `\"Age: \" + age` mixes text and a number, so it stops there with a TypeError and never prints `Done`."
        other_error = "NameError"
    elif scenario == "typo":
        lvl = rng.randint(2, 9)
        code = f'name = "{name}"\nlevel = {lvl}\nprint("Player:", name)\nprint("Level:", Level)\nprint("Done")'
        fixed = code.replace("Level)", "level)")
        error = "NameError"
        before = f"Player: {name}"
        why = "`Level` and `level` are different names (names are case-sensitive). The first `print` works, then the typo stops the program with a NameError before `Done`."
        other_error = "TypeError"
    else:
        school = rng.choice(SCHOOLS)
        code = f'name = "{name}"\nprint("Hi,", name)\nschool = {school}\nprint("School:", school)\nprint("Done")'
        fixed = code.replace(f"school = {school}", f'school = "{school}"')
        error = "NameError"
        before = f"Hi, {name}"
        why = f'The first `print` works, then `school = {school}` (no quotes) makes Python look for a variable named {school}, so the program stops with a NameError.'
        other_error = "TypeError"
    res = run_code(code)
    if res.error != error or res.output != before:
        raise GenerationError(f"scenario misbehaved: {res.error!r} {res.output!r}")
    full = run_code(fixed)
    if full.error:
        raise GenerationError("fixed program fails")
    correct = f"{before}\nthen it stops with a {error}"
    wrong = [
        full.output,
        f"It stops with a {error} before printing anything",
        f"{before}\nthen it stops with a {other_error}",
        f"{before}\nDone",
    ]
    return _q(HARD, "What happens when this program runs?", correct, wrong, why, rng, code=code)


@generator(TOPIC, HARD)
def gen_case_chain(rng: random.Random) -> Question:
    """score, Score and SCORE are three variables that build on each other."""
    word = rng.choice(["score", "money", "count", "level", "total"])
    w1, w2, w3 = word, word.title(), word.upper()
    a = rng.randint(10, 25)
    b = rng.randint(2, 9)
    op1 = rng.choice("+-")
    k = rng.randint(2, 4)
    code = f"{w1} = {a}\n{w2} = {w1} {op1} {b}\n{w3} = {w2} * {k}\nprint({w1}, {w2}, {w3})"
    v2 = eval(f"{a} {op1} {b}")
    v3 = v2 * k
    one_var = eval(f"({a} {op1} {b}) * {k}")
    wrong = [
        f"{one_var} {one_var} {one_var}",
        f"{a} {v2} {eval(f'{a} * {k}')}",
        f"{v3} {v2} {a}",
        f"{a} {a} {a}",
        f"{a} {v2} {v2}",
        f"{v2} {v2} {v3}",
    ]
    return _out(
        HARD,
        code,
        wrong,
        f"`{w1}`, `{w2}` and `{w3}` are three different variables. `{w2}` is built from `{w1}`, and `{w3}` is built from `{w2}`, so each keeps its own value.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_lab_trace(rng: random.Random) -> Question:
    """A condensed variables_lab.py: reassignment (type changes) and a swap."""
    name = rng.choice(PEOPLE)
    age = rng.randint(14, 18)
    word = {14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen"}[age]
    x, y, z = rng.sample(range(1, 30), 3)
    code = (
        f'name = "{name}"\nage = {age}\nage = "{word}"\n'
        f"x, y, z = {x}, {y}, {z}\nx, y = y, x\n"
        f"print(name, age, type(age))\nprint(x, y, z)"
    )
    wrong = [
        f"{name} {word} <class 'int'>\n{y} {x} {z}",
        f"{name} {word} <class 'str'>\n{x} {y} {z}",
        f"{name} {age} <class 'int'>\n{y} {x} {z}",
        f"{name} {word} <class 'str'>\n{y} {y} {z}",
        f"{name} {word} <class 'str'>\n{x} {x} {z}",
    ]
    return _out(
        HARD,
        code,
        wrong,
        f"`age` was reassigned, so it is the text `{word}` and its type is `str`. The swap trades `x` and `y` and leaves `z` alone.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_odd_one_out(rng: random.Random) -> Question:
    """Three lines print the same text, one prints something different."""
    name = rng.choice(PEOPLE)
    label = rng.choice(["Hi", "Hello,", "Welcome,", "Player:", "Student:", "My name is"])
    setup = f'name = "{name}"'
    good = [f'print("{label}", name)', f'print("{label} " + name)', f'print(f"{label} {{name}}")']
    bad = [f'print("{label}" + name)', f'print("{label}", "name")', f'print("{label} name")']
    if label[-1] not in ",:":
        bad.append(f'print(f"{label}, {{name}}")')
    odd = rng.choice(bad)
    lines = [*good, odd]
    rng.shuffle(lines)
    outs = [run_code(f"{setup}\n{ln}") for ln in lines]
    if any(o.error for o in outs):
        raise GenerationError("a line failed")
    texts = [o.output for o in outs]
    if sorted(texts.count(t) for t in set(texts)) != [1, 3]:
        raise GenerationError("not three-and-one")
    return _q(
        HARD,
        "Three of these lines print exactly the same text. Which one prints something different?",
        odd,
        [ln for ln in lines if ln != odd],
        f'The odd line prints `{texts[lines.index(odd)]}`, while the other three print `{label} {name}`.',
        rng,
        code=f"{setup}\n" + "\n".join(lines),
    )


@generator(TOPIC, HARD)
def gen_lost_value(rng: random.Random) -> Question:
    """x = y then y = x loses a value; a temp variable does not."""
    x, y = rng.choice([("x", "y"), ("a", "b"), ("first", "second"), ("left", "right")])
    p, q = rng.sample(range(1, 30), 2)
    if rng.random() < 0.65:
        first, second = (f"{x} = {y}", f"{y} = {x}") if rng.random() < 0.5 else (f"{y} = {x}", f"{x} = {y}")
        code = f"{x} = {p}\n{y} = {q}\n{first}\n{second}\nprint({x}, {y})"
        wrong = [f"{q} {p}", f"{p} {q}", f"{p} {p}", f"{q} {q}"]
        why = "Each line runs in order. After the first assignment both names hold the same value, so the original value of the other name is already lost."
    else:
        code = f"{x} = {p}\n{y} = {q}\ntemp = {x}\n{x} = {y}\n{y} = temp\nprint({x}, {y})"
        wrong = [f"{p} {q}", f"{q} {q}", f"{p} {p}"]
        why = f"`temp` keeps the old value of `{x}` safe, so nothing is lost: `{x}` becomes {q} and `{y}` becomes {p}."
    return _out(HARD, code, wrong, why, rng)


@generator(TOPIC, HARD)
def gen_value_snapshot(rng: random.Random) -> Question:
    """An f-string (or str + concatenation) uses the value the variable has at that moment."""
    var, label = rng.choice([("score", "Score"), ("money", "Money"), ("level", "Level"), ("points", "Points")])
    a, b = rng.sample(range(2, 50), 2)
    if rng.random() < 0.5:
        build = f'message = f"{label}: {{{var}}}"'
    else:
        build = f'message = "{label}: " + str({var})'
    code = f'{var} = {a}\n{build}\n{var} = {b}\nprint(message)\nprint(f"{label}: {{{var}}}")'
    return _out(
        HARD,
        code,
        [f"{label}: {b}\n{label}: {b}", f"{label}: {a}\n{label}: {a}", f"{label}: {b}\n{label}: {a}", f"{label}: {a}\n{label}: {a + b}"],
        f"`message` was built when `{var}` was {a}, so it keeps `{label}: {a}`. The f-string in the last line is evaluated now, when `{var}` is {b}.",
        rng,
    )


# ==========================================================================
# BLANKS  (fill in the blanks, typed)
# ==========================================================================


def _str_blank(value: str, hint: str = "text") -> Blank:
    """A blank whose answer is a text literal (either kind of quote is fine)."""
    return Blank([f'"{value}"', f"'{value}'"], hint=hint, mode="expr")


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_value_literal(rng: random.Random) -> Question:
    """name = ____  (text needs quotes, True needs a capital T, floats are just numbers)."""
    shape = rng.choice(["text", "bool", "number"])
    mark = blank_mark(1)
    if shape == "text":
        var, value = rng.choice(
            [("name", "Ada"), ("name", "Reid"), ("school", "DBHS"), ("color", "blue"), ("pet", "Rex"), ("city", "Kingsport"), ("name", "Sam")]
        )
        return blanks_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=f"Fill in the blank so `{var}` holds the text {value} and the code prints it.",
            template=f"{var} = {mark}\nprint({var})",
            blanks=[_str_blank(value)],
            explanation=f'Text goes inside quotes: `{var} = "{value}"`. Without quotes Python would look for a variable named {value}.',
            expect_output=value,
        )
    if shape == "bool":
        var, value = rng.choice([("is_student", "True"), ("is_raining", "False"), ("is_ready", "True"), ("is_member", "False")])
        return blanks_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=f"Fill in the blank so the code prints `{value}`.",
            template=f"{var} = {mark}\nprint({var})",
            blanks=[Blank([value], hint="boolean")],
            explanation=f"Python's booleans are written `True` and `False` with a capital first letter (names are case-sensitive), so `{var} = {value}`.",
            expect_output=value,
        )
    var, lit = rng.choice([("height_m", "1.80"), ("gpa", "3.7"), ("age", "17"), ("score", "95"), ("temperature", "72"), ("money", "12.5")])
    shown = _shown(lit)
    accepted = [lit] if shown == lit else [lit, shown]
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blank so the code prints `{shown}`.",
        template=f"{var} = {mark}\nprint({var})",
        blanks=[Blank(accepted, hint="number", mode="expr")],
        explanation=f"Numbers are typed without quotes: `{var} = {lit}`.",
        expect_output=shown,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_case_sensitive(rng: random.Random) -> Question:
    """Two names that differ only in capitals: which one prints the expected line?"""
    lo, hi = rng.choice([("score", "Score"), ("total", "TOTAL"), ("high_score", "HIGH_SCORE"), ("count", "COUNT"), ("level", "Level"), ("money", "MONEY")])
    v_lo, v_hi = rng.sample(range(2, 99), 2)
    label = rng.choice(["Best", "Result", "Value", "Total"])
    target, expected = rng.choice([(lo, v_lo), (hi, v_hi)])
    template = f'{lo} = {v_lo}\n{hi} = {v_hi}\nprint("{label}:", {blank_mark(1)})'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blank so the code prints `{label}: {expected}`. Names are case-sensitive.",
        template=template,
        blanks=[Blank([target], hint="variable name")],
        explanation=f"`{lo}` and `{hi}` are two different variables. Only `{target}` holds {expected}.",
        expect_output=f"{label}: {expected}",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_constant_name(rng: random.Random) -> Question:
    """The constant's name is used on the last line -- type it in SCREAMING_SNAKE_CASE."""
    const, label = rng.choice(
        [("STUDENT_LIMIT", "Limit"), ("MAX_USERS", "Max users"), ("MAX_LIVES", "Lives"), ("PASSING_SCORE", "Pass"), ("TIME_LIMIT", "Time"),
         ("CLASS_SIZE", "Size"), ("MAX_SCORE", "Max"), ("PLAYER_LIMIT", "Players")]
    )
    value = rng.choice([32, 30, 25, 40, 100, 3, 5, 60, 70, 20])
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blank to create the constant that the last line prints. The code should print `{label}: {value}`.",
        template=f'{blank_mark(1)} = {value}\nprint("{label}:", {const})',
        blanks=[Blank([const], hint="CONSTANT_NAME")],
        explanation=f"The last line uses `{const}`, so the constant must be created with exactly that name. Constants are written in SCREAMING_SNAKE_CASE.",
        expect_output=f"{label}: {value}",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_type_call(rng: random.Random) -> Question:
    """print("age is now:", age, type(age))"""
    var, v1, v2 = rng.choice(
        [("age", "17", '"seventeen"'), ("age", "16", '"sixteen"'), ("score", "10", '"ten"'), ("count", "3", "3.5"), ("is_student", "True", '"yes"'),
         ("name", '"Ada"', "17"), ("level", "1", '"one"'), ("gpa", "3.5", "4"), ("temperature", "72", "72.5"), ("grade", '"A"', "95"),
         ("money", "50", "True"), ("height_m", "1.80", '"tall"')]
    )
    expected = f"{var} is now: {_shown(v2)} {_type_text(v2)}"
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Fill in the blank so the last line also prints the data type of the variable.",
        template=f'{var} = {v1}\n{var} = {v2}\nprint("{var} is now:", {var}, {blank_mark(1)}({var}))',
        blanks=[Blank(["type"], hint="function")],
        explanation=f"`type({var})` returns the type of the value stored in `{var}`. After reassignment that is `{type(eval(v2)).__name__}`.",
        expect_output=expected,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_multi_assign(rng: random.Random) -> Question:
    """name, age = "Ada", 17  (the values go in by position)."""
    people = rng.choice(PEOPLE)
    options = [
        (["name", "age"], [f'"{people}"', str(rng.randint(13, 18))]),
        (["school", "year_started"], [f'"{rng.choice(SCHOOLS)}"', str(rng.randint(2019, 2024))]),
        (["name", "age", "height_m"], [f'"{people}"', str(rng.randint(13, 18)), rng.choice(["1.80", "1.65", "1.70", "1.55"])]),
        (["x", "y", "z"], [str(v) for v in rng.sample(range(1, 30), 3)]),
    ]
    names, lits = rng.choice(options)
    blanks = []
    for lit in lits:
        if lit.startswith('"'):
            blanks.append(_str_blank(lit.strip('"'), hint="text"))
        else:
            shown = _shown(lit)
            blanks.append(Blank([lit] if shown == lit else [lit, shown], hint="number", mode="expr"))
    expected = " ".join(_shown(lit) for lit in lits)
    template = f"{', '.join(names)} = {', '.join(blank_mark(i + 1) for i in range(len(lits)))}\nprint({', '.join(names)})"
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Multiple assignment: fill in the blanks so the code prints `{expected}`.",
        template=template,
        blanks=blanks,
        explanation="Multiple assignment matches names and values by position, and `print` shows text without its quotes."
        + (" Text values still need quotes when you type them." if any(lit.startswith('"') for lit in lits) else ""),
        expect_output=expected,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_swap(rng: random.Random) -> Question:
    """x, y = y, x"""
    x, y, z = rng.choice([("x", "y", "z"), ("a", "b", "c"), ("first", "second", "third")])
    a, b, c = rng.sample(range(1, 30), 3)
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks (with variable names) to swap `{x}` and `{y}`.",
        template=f'{x}, {y}, {z} = {a}, {b}, {c}\n{x}, {y} = {blank_mark(1)}, {blank_mark(2)}\nprint("swapped:", {x}, {y})',
        blanks=[Blank([y], hint="variable"), Blank([x], hint="variable")],
        explanation=f"`{x}, {y} = {y}, {x}` swaps the two values: the right side is worked out first, then `{x}` gets the old `{y}` and `{y}` gets the old `{x}`.",
        expect_output=f"swapped: {b} {a}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_fstring(rng: random.Random) -> Question:
    """print(f"{name} is {age} years old.")"""
    name = rng.choice(PEOPLE)
    age = rng.randint(13, 18)
    if rng.random() < 0.5:
        template = f'name = "{name}"\nage = {age}\nprint({blank_mark(1)}"{{{blank_mark(2)}}} is {{age}} years old.")'
        blanks = [Blank(["f", "F"], hint="letter"), Blank(["name"], hint="variable")]
        why = 'An f-string starts with an `f` before the opening quote, and each `{...}` is replaced by the value of the variable named inside.'
    else:
        template = f'name = "{name}"\nage = {age}\nprint(f"{{{blank_mark(1)}}} is {{{blank_mark(2)}}} years old.")'
        blanks = [Blank(["name"], hint="variable"), Blank(["age"], hint="variable")]
        why = "Inside an f-string the braces hold the variable names: `{name}` becomes the text, `{age}` becomes the number."
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the code prints `{name} is {age} years old.`",
        template=template,
        blanks=blanks,
        explanation=why,
        expect_output=f"{name} is {age} years old.",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_str_cast(rng: random.Random) -> Question:
    """print("Age: " + str(age))"""
    var, value, label = rng.choice([("age", 17, "Age"), ("score", 95, "Score"), ("level", 4, "Level"), ("STUDENT_LIMIT", 32, "Limit"), ("year_started", 2023, "Year")])
    value = rng.choice([value, value + 1, value + 3, value + 10]) if var != "year_started" else rng.choice([2019, 2020, 2021, 2022, 2023, 2024])
    mark = blank_mark(1)
    if rng.random() < 0.5:
        template = f'{var} = {value}\nprint("{label}: " + {mark}({var}))'
        blanks = [Blank(["str"], hint="function")]
        prompt = f"Fill in the blank so the number can be joined to the text with `+`. The code should print `{label}: {value}`."
    else:
        template = f'{var} = {value}\nprint("{label}: " + {mark})'
        blanks = [Blank([f"str({var})"], hint="expression", mode="expr")]
        prompt = f"Fill in the blank with an expression that turns `{var}` into text. The code should print `{label}: {value}`."
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        template=template,
        blanks=blanks,
        explanation=f"`+` can only join text to text, so convert the number first: `str({var})`. (A comma or an f-string would also work.)",
        expect_output=f"{label}: {value}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_update_old_value(rng: random.Random) -> Question:
    """score = score + 5  -- the new value is built from the old one."""
    var = rng.choice(["score", "money", "level", "points", "count"])
    start = rng.randint(3, 30)
    add = rng.randint(2, 9)
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blank so `{var}` goes up by {add} and the code prints {start + add}.",
        template=f"{var} = {start}\n{var} = {blank_mark(1)} + {add}\nprint({var})",
        blanks=[Blank([var], hint="variable")],
        explanation=f"Python works out the right side first with the old value ({start} + {add}) and then stores the answer back in `{var}`.",
        expect_output=str(start + add),
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_profile_line(rng: random.Random) -> Question:
    """The Mini-Challenge: Reid started at DBHS in 2023 and has a GPA of 3.7"""
    person = rng.choice(PEOPLE)
    school = rng.choice(SCHOOLS)
    year = rng.randint(2019, 2024)
    gpa = rng.choice(["3.7", "3.5", "3.9", "3.2", "4.0", "2.8"])
    sentence = f"{person} started at {school} in {year} and has a GPA of {gpa}"
    shape = rng.choice(["year", "school"])
    if shape == "year":
        template = (
            f'school = "{school}"\nyear_started = {blank_mark(1)}\ngpa = {gpa}\n'
            f'print({blank_mark(2)}"{person} started at {{school}} in {{{blank_mark(3)}}} and has a GPA of {{gpa}}")'
        )
        blanks = [Blank([str(year)], hint="number", mode="expr"), Blank(["f", "F"], hint="letter"), Blank(["year_started"], hint="variable")]
    else:
        template = (
            f'school = {blank_mark(1)}\nyear_started = {year}\ngpa = {gpa}\n'
            f'print({blank_mark(2)}"{person} started at {{school}} in {{year_started}} and has a GPA of {{{blank_mark(3)}}}")'
        )
        blanks = [_str_blank(school), Blank(["f", "F"], hint="letter"), Blank(["gpa"], hint="variable")]
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Mini-Challenge: Profile Line. Fill in the blanks so the code prints `{sentence}`",
        template=template,
        blanks=blanks,
        explanation="Three variables hold the facts, and an f-string (an `f` before the quotes, variable names in `{}`) builds the sentence. Text values need quotes; numbers do not.",
        expect_output=sentence,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_rotate(rng: random.Random) -> Question:
    """a, b, c = b, c, a  -- work out which names go where from the printed result."""
    a, b, c = rng.choice([("a", "b", "c"), ("x", "y", "z")])
    va, vb, vc = rng.sample(range(1, 30), 3)
    left = rng.random() < 0.5
    answers = [b, c, a] if left else [c, a, b]
    expected = f"{vb} {vc} {va}" if left else f"{vc} {va} {vb}"
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Fill in the blanks (with variable names) so the code prints `{expected}`.",
        template=f"{a}, {b}, {c} = {va}, {vb}, {vc}\n{a}, {b}, {c} = {blank_mark(1)}, {blank_mark(2)}, {blank_mark(3)}\nprint({a}, {b}, {c})",
        blanks=[Blank([n], hint="variable") for n in answers],
        explanation=f"The right side uses the old values, so `{a}, {b}, {c} = {', '.join(answers)}` moves each value one place. `{a}` must receive the old `{answers[0]}`, `{b}` the old `{answers[1]}`, and `{c}` the old `{answers[2]}`.",
        expect_output=expected,
    )


# ==========================================================================
# MATCHING
# ==========================================================================

_TERMS = {
    "variable": "A named box that holds a value",
    "assignment (=)": "Stores a value in a variable",
    "reassignment": "Giving an existing variable a new value",
    "constant": "A value you don't plan to change",
    "snake_case": "Lowercase words joined by underscores",
    "SCREAMING_SNAKE_CASE": "ALL CAPS words joined by underscores",
    "f-string": "Text with an f in front and {} placeholders",
    "concatenation": "Joining strings together with +",
    "dynamic typing": "The type is decided by the value assigned",
}


@generator(TOPIC, EASY, qtype="match")
def gen_match_terms(rng: random.Random) -> Question:
    """Match each term to its meaning (vocabulary of the lesson)."""
    terms = rng.sample(list(_TERMS), 5)
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each term from the Variables lesson to what it means.",
        pairs=[(t, _TERMS[t]) for t in terms],
        explanation="A variable is a named box for a value; `=` assigns; constants are written in SCREAMING_SNAKE_CASE and normal variables in snake_case; f-strings and `+` build text; Python decides types from the value (dynamic typing).",
        rng=rng,
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_value_type(rng: random.Random) -> Question:
    """Match each value to its type."""
    pool = ['"Ada"', "17", "1.80", "True", '"17"', '"True"', "3.0", "False", '"3.14"', "0", '"DBHS"', "2023", "72", "3.7"]
    chosen = rng.sample(pool, 5)
    for _ in range(30):  # want at least three different types among the five values
        if len({type(eval(c)).__name__ for c in chosen}) >= 3:
            break
        chosen = rng.sample(pool, 5)
    pairs = [(c, type(eval(c)).__name__) for c in chosen]
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each value to its Python type.",
        pairs=pairs,
        explanation="Quotes make a `str` (even `\"17\"`), whole numbers are `int`, numbers with a decimal point are `float`, and `True` / `False` are `bool`.",
        rng=rng,
        extra_options=("int", "float", "str", "bool"),
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_name_styles(rng: random.Random) -> Question:
    """Match each name to the convention it follows."""
    snake_opt, const_opt, camel_opt = "snake_case variable", "SCREAMING_SNAKE_CASE constant", "camelCase (not the course style)"
    pairs = []
    for kind, opt in (("snake", snake_opt), ("screaming", const_opt), ("camel", camel_opt)):
        for _ in range(2 if kind != "camel" else 1):
            pairs.append((_styles(_pick_words(rng))[kind], opt))
    # make the picks distinct
    seen = set()
    unique = []
    for item, opt in pairs:
        if item not in seen:
            seen.add(item)
            unique.append((item, opt))
    if len(unique) < 4:
        raise GenerationError("too few distinct names")
    unique = unique[:5]
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each name to the convention it follows.",
        pairs=unique,
        explanation="Variables use snake_case (lowercase with underscores), constants use SCREAMING_SNAKE_CASE (all capitals with underscores), and camelCase is the style the lesson warns about.",
        rng=rng,
        extra_options=(snake_opt, const_opt, camel_opt),
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_valid_names(rng: random.Random) -> Question:
    """Valid, starts with a number, or has a space / hyphen / symbol."""
    ok_opt, digit_opt, char_opt = "Valid name", "Invalid: starts with a number", "Invalid: has a space, hyphen, or symbol"
    valid = rng.sample(["student_count", "high_score", "player1", "level_2", "gpa", "height_m", "is_student", "age2", "year_started"], 2)
    digit = rng.sample(["1st_place", "2player", "3d_model", "9lives", "4th_try", "2nd_score"], 1 if rng.random() < 0.5 else 2)
    chars = rng.sample(["high-score", "my-name", "student count", "high score", "score$", "my@name", "best-time", "gpa!"], 5 - 2 - len(digit))
    pairs = [(n, ok_opt) for n in valid] + [(n, digit_opt) for n in digit] + [(n, char_opt) for n in chars]
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Decide whether each variable name is allowed in Python.",
        pairs=pairs,
        explanation="Names may contain letters, numbers, and underscores, but cannot start with a number. Spaces, hyphens and symbols are not allowed.",
        rng=rng,
        extra_options=(ok_opt, digit_opt, char_opt),
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_print_lines(rng: random.Random) -> Question:
    """Match each print line to what it prints (name = "Ada")."""
    name = rng.choice(PEOPLE)
    label = rng.choice(["Hi", "Hello,", "Player:", "Welcome,"])
    setup = f'name = "{name}"'
    lines = [
        f'print("{label}", name)',
        f'print("{label} " + name)',
        f'print("{label}" + name)',
        f'print(f"{label} {{name}}")',
        f'print("{label}", "name")',
        f'print("{label} name")',
        f'print("{label} {{name}}")',
        f'print(f"{label} name")',
    ]
    pairs = []
    for _ in range(30):  # want at least three different outputs among the five lines
        pairs = []
        for ln in rng.sample(lines, 5):
            res = run_code(f"{setup}\n{ln}")
            if res.error:
                raise GenerationError("line failed")
            pairs.append((ln, res.output))
        if len({o for _, o in pairs}) >= 3:
            break
    else:
        raise GenerationError("outputs too similar")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each print line to the text it prints.",
        pairs=pairs,
        explanation="Commas add a space, `+` joins exactly what is written, an f-string fills in `{name}`, and without the `f` the braces are printed as plain text.",
        rng=rng,
        code=setup,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_mistakes(rng: random.Random) -> Question:
    """Match each classic mistake to the kind of error it causes."""
    name_opt = "NameError: Python doesn't know that name"
    type_opt = "TypeError: mixing text and a number"
    syn_opt = "SyntaxError: not valid Python"
    setup = 'score = 10\nage = 17'
    pool = [
        ("name = Ada", name_opt),
        ("print(Score)", name_opt),
        ("print(studentCount)", name_opt),
        ('print("Age: " + age)', type_opt),
        ('print("5" + 2)', type_opt),
        ("print(age + \"1\")", type_opt),
        ('my-name = "Ada"', syn_opt),
        ("2nd_place = 3", syn_opt),
        ('high score = 100', syn_opt),
    ]
    pairs = []
    for want in (name_opt, type_opt, syn_opt):
        pairs.append(rng.choice([p for p in pool if p[1] == want]))
    rest = [p for p in pool if p not in pairs]
    pairs += rng.sample(rest, 2)
    for line, opt in pairs:
        err = run_code(f"{setup}\n{line}").error
        if err != opt.split(":")[0]:
            raise GenerationError(f"{line!r} raised {err}, expected {opt}")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each line to the error Python reports when it runs.",
        pairs=pairs,
        explanation="Missing quotes and typos in a name give a NameError, joining text and a number with `+` gives a TypeError, and a name that breaks the naming rules is a SyntaxError.",
        rng=rng,
        code=setup,
    )


@generator(TOPIC, HARD, qtype="match")
def gen_match_final_values(rng: random.Random) -> Question:
    """Trace multiple assignment / swap / copy and match each variable to its final value."""
    va, vb, vc = rng.sample(range(1, 10), 3)
    script = rng.choice(
        [
            "x, y = y, x",
            "x, y, z = y, z, x",
            "x, y, z = z, x, y",
            "x, y = y, x\nz = x",
            "z = x\nx = y\ny = z",
            "x = y\ny = z",
        ]
    )
    code = f"x, y, z = {va}, {vb}, {vc}\n{script}"
    res = run_code(code)
    if res.error:
        raise GenerationError("script failed")
    ns = res.namespace
    pairs = [(f"x", str(ns["x"])), (f"y", str(ns["y"])), (f"z", str(ns["z"]))]
    if len({a for _, a in pairs}) < 2:
        raise GenerationError("all answers alike")
    extra = [str(v) for v in range(1, 10) if str(v) not in {a for _, a in pairs}]
    rng.shuffle(extra)
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="After this code runs, match each variable to the value it holds.",
        pairs=pairs,
        explanation=(
            "Follow the lines from top to bottom. In multiple assignment the whole right side is worked out first, so swaps and rotations never lose a value."
            if "," in script
            else "Follow the lines from top to bottom. Each `a = b` copies the value on the right into the name on the left, and the old value of that name is lost."
        ),
        rng=rng,
        extra_options=tuple(extra[:2]),
        code=code,
    )


# ==========================================================================
# CODE  (typed Python, graded in the sandbox -- no functions, those come later)
# ==========================================================================

F_STRING_ONLY = [(r"""\bf["']""", "Use an f-string: put an f right before the opening quote")]


def _py(value) -> str:
    """A value as it is typed in code (text in double quotes, like the lessons)."""
    return f'"{value}"' if isinstance(value, str) else repr(value)


# ---- EASY ------------------------------------------------------------------


@generator(TOPIC, EASY, qtype="code")
def gen_code_assign_value(rng: random.Random) -> Question:
    """Bingo: 'Create a variable named name and assign your first name' (one line)."""
    shape = rng.choice(["text", "int", "float", "bool", "constant"])
    if shape == "text":
        var, value = rng.choice([("name", "Ada"), ("name", "Reid"), ("name", "Sam"), ("school", "DBHS"), ("color", "blue"), ("pet", "Rex"), ("city", "Kingsport")])
        what = f"the text `{value}`"
    elif shape == "int":
        var, value = rng.choice([("age", 17), ("score", 95), ("year_started", 2023), ("count", 0), ("temperature", 72), ("level", 4), ("lives", 3)])
        what = f"the whole number `{value}`"
    elif shape == "float":
        var, value = rng.choice([("height_m", 1.8), ("gpa", 3.7), ("money", 12.5), ("temperature", 98.6), ("price", 2.25)])
        what = f"the decimal number `{value}`"
    elif shape == "bool":
        var, value = rng.choice([("is_student", True), ("is_raining", False), ("is_ready", True), ("is_member", False)])
        what = f"the boolean `{value}`"
    else:
        var, value = rng.choice([("MAX_USERS", 32), ("STUDENT_LIMIT", 32), ("MAX_LIVES", 3), ("PASSING_SCORE", 70), ("TIME_LIMIT", 60)])
        what = f"the number `{value}`"
    solution = f"{var} = {_py(value)}"
    cases = [
        Case(label=f"{var} should hold {_py(value)}", expect_vars={var: value}),
        Case(label=f"print({var}) should show {value}", after=f"print({var})", out=str(value)),
    ]
    if shape == "constant":
        prompt = f"Write one line that creates the constant `{var}` (by convention, in SCREAMING_SNAKE_CASE) holding {what}."
    else:
        prompt = f"Write one line that creates a variable named `{var}` holding {what}."
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"Assign with a single `=`: `{solution}`. Text needs quotes, numbers and `True` / `False` do not.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_expr_fstring(rng: random.Random) -> Question:
    """Bingo: 'Use an f-string to greet someone by name'."""
    templates = [
        (("name", "age"), 'f"{name} is {age} years old."', lambda: {"name": rng.choice(PEOPLE), "age": rng.randint(12, 18)}),
        (("name", "gpa"), 'f"{name} has a GPA of {gpa}"', lambda: {"name": rng.choice(PEOPLE), "gpa": rng.choice([3.2, 3.5, 3.7, 3.9, 2.8, 4.0])}),
        (("school", "year_started"), 'f"I started at {school} in {year_started}"', lambda: {"school": rng.choice(SCHOOLS), "year_started": rng.randint(2018, 2024)}),
        (("name", "score"), 'f"{name} scored {score} points"', lambda: {"name": rng.choice(PEOPLE), "score": rng.randint(10, 99)}),
        (("fruit", "price"), 'f"A {fruit} costs {price} coins"', lambda: {"fruit": rng.choice(["apple", "banana", "cherry", "mango", "lemon"]), "price": rng.randint(2, 20)}),
        (("name", "level"), 'f"{name} reached level {level}"', lambda: {"name": rng.choice(PEOPLE), "level": rng.randint(2, 30)}),
    ]
    names, solution, make = rng.choice(templates)
    cases = []
    seen = set()
    while len(cases) < 4:
        v = make()
        key = tuple(v.values())
        if key in seen:
            continue
        seen.add(key)
        cases.append((v, eval(solution, {}, dict(v))))
    task = expression_task(solution, cases, starter="", examples=2, requires=F_STRING_ONLY)
    first_vars, first_text = cases[0]
    shown_vars = " and ".join(f"`{k} = {_py(v)}`" for k, v in first_vars.items())
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"The variables {' and '.join('`' + n + '`' for n in names)} are already defined (for example {shown_vars}). Type an f-string that gives `{first_text}`",
        task=task,
        explanation="An f-string starts with `f` before the opening quote, and the variable names go inside `{}`, so the text changes when the variables do.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_expr_concat(rng: random.Random) -> Question:
    """Common mistake fixed: a label + a number, joined without a TypeError."""
    var, label = rng.choice([("score", "Score: "), ("age", "Age: "), ("level", "Level: "), ("money", "Money: "), ("year_started", "Year: "), ("lives", "Lives: ")])
    solution = f'"{label}" + str({var})'
    values = rng.sample(range(2019, 2025), 4) if var == "year_started" else rng.sample(range(2, 100), 4)
    cases = [({var: v}, f"{label}{v}") for v in values]
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f'`{var}` holds a number (for example `{var} = {values[0]}`). Type an expression that gives the text `{label}{values[0]}`',
        task=expression_task(solution, cases, starter="", examples=2),
        explanation=f'`"{label}" + {var}` would crash (text + number). Turn the number into text with `str({var})`, or use an f-string: `f"{label}{{{var}}}"`.',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_print_greeting(rng: random.Random) -> Question:
    """Bingo: 'Concatenate two strings with a space' / print with a variable."""
    var, label = rng.choice([("name", "My name is"), ("name", "Hello,"), ("name", "Welcome,"), ("school", "I go to"), ("pet", "My pet is")])
    pool = {"name": PEOPLE, "school": SCHOOLS, "pet": ["Rex", "Milo", "Luna", "Coco", "Max", "Bella"]}[var]
    values = rng.sample(pool, 4)
    solution = f'print("{label}", {var})'
    cases = [Case(vars={var: v}, out=f"{label} {v}") for v in values]
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` already holds some text (for example `{var} = \"{values[0]}\"`). Write one line that prints `{label} {values[0]}`",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f'`print("{label}", {var})` puts a space between the pieces automatically. `+` or an f-string also work, as long as the output matches exactly.',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_print_type(rng: random.Random) -> Question:
    """Bingo: 'Use type() to print a variable's type'."""
    pools = {
        "int": [17, 42, 3, 2023, 95],
        "float": [1.8, 3.7, 72.5, 0.5, 98.6],
        "str": ["Ada", "17", "Python", "True", "hello"],
        "bool": [True, False],
    }
    order = list(pools)
    rng.shuffle(order)
    cases = []
    for t in order:
        v = rng.choice(pools[t])
        cases.append(Case(vars={"value": v}, out=f"<class '{t}'>"))
    first = cases[0]
    shown = _py(first.vars["value"])
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`value` already holds something (for example `value = {shown}`). Write one line that prints its type, like `{first.out}`",
        task=program_task("print(type(value))", cases, starter="", examples=2),
        explanation="`type(value)` gives the data type of the value, and `print()` shows it: `print(type(value))`.",
    )


# ---- MEDIUM ----------------------------------------------------------------


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_swap(rng: random.Random) -> Question:
    """Lesson: x, y = y, x"""
    x, y = rng.choice([("x", "y"), ("a", "b"), ("first", "second"), ("left", "right")])
    pairs = [
        (rng.randint(1, 9), rng.randint(10, 30)),
        (rng.choice(["red", "apple", "cat"]), rng.choice(["blue", "banana", "dog"])),
        (rng.randint(31, 60), rng.randint(1, 9)),
        (rng.choice([1.5, 2.5, 3.75]), rng.choice([7, 8, 9])),
    ]
    cases = [Case(vars={x: p, y: q}, expect_vars={x: q, y: p}) for p, q in pairs]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`{x}` and `{y}` already hold values. Write code that swaps them, so `{x}` ends up with the old value of `{y}` and `{y}` with the old value of `{x}`.",
        task=program_task(f"{x}, {y} = {y}, {x}", cases, starter="", examples=2),
        explanation=f"`{x}, {y} = {y}, {x}` works out the right side first, then assigns. Doing `{x} = {y}` and then `{y} = {x}` would lose the old value of `{x}`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_profile_line(rng: random.Random) -> Question:
    """The lesson's Mini-Challenge: Profile Line."""
    person = rng.choice(PEOPLE)
    school = rng.choice(SCHOOLS)
    year = rng.randint(2019, 2024)
    gpa = rng.choice([3.7, 3.5, 3.9, 3.2, 4.0, 2.8])
    sentence = f"{person} started at {school} in {year} and has a GPA of {gpa}"
    solution = f'school = "{school}"\nyear_started = {year}\ngpa = {gpa}\nprint(f"{person} started at {{school}} in {{year_started}} and has a GPA of {{gpa}}")'
    cases = [
        Case(label="the sentence is printed", out=sentence, expect_vars={"school": school, "year_started": year, "gpa": gpa}),
        Case(label="the variables have the right types", after="print(type(school), type(year_started), type(gpa))", out=sentence + "\n<class 'str'> <class 'int'> <class 'float'>"),
    ]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=(
            f"Mini-Challenge: Profile Line. Create three variables, `school` (text), `year_started` (a whole number) and `gpa` (a decimal), "
            f"then print one sentence with an f-string: `{sentence}`"
        ),
        task=program_task(solution, cases, starter="", examples=1, requires=F_STRING_ONLY),
        explanation="Create the three variables first (text in quotes, numbers without), then build the sentence with an f-string: `f\"... {school} ... {year_started} ... {gpa}\"`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_update_variable(rng: random.Random) -> Question:
    """Reassignment using the old value, then print."""
    var, label, delta = rng.choice(
        [("level", "Level", 1), ("score", "Score", 10), ("money", "Money", 25), ("lives", "Lives", -1), ("points", "Points", 5), ("count", "Count", 1), ("coins", "Coins", 3)]
    )
    starts = rng.sample(range(3, 40), 4)
    sign = "+" if delta > 0 else "-"
    solution = f'{var} = {var} {sign} {abs(delta)}\nprint("{label}:", {var})'
    cases = [Case(vars={var: s}, expect_vars={var: s + delta}, out=f"{label}: {s + delta}") for s in starts]
    verb = f"adds {delta} to" if delta > 0 else f"takes {abs(delta)} away from"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`{var}` already holds a number. Write code that {verb} `{var}` (reassign it), then prints `{label}: ` followed by the new value, like `{label}: {starts[0] + delta}`",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"Reassign with the old value on the right: `{var} = {var} {sign} {abs(delta)}`. Only printing `{var} {sign} {abs(delta)}` would not change the variable.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_reassign_type(rng: random.Random) -> Question:
    """Lesson: age = "seventeen"; print("age is now:", age, type(age))"""
    var, newlit, kind = rng.choice(
        [
            ("age", '"seventeen"', "int"),
            ("age", '"sixteen"', "int"),
            ("score", '"ten"', "int"),
            ("level", '"one"', "int"),
            ("count", "3.5", "int"),
            ("gpa", "4", "float"),
            ("temperature", "72.5", "int"),
            ("is_student", '"yes"', "bool"),
            ("money", "12.5", "int"),
            ("grade", "95", "str"),
        ]
    )
    if kind == "int":
        starts = rng.sample(range(0, 100), 4)
    elif kind == "float":
        starts = rng.sample([3.5, 2.8, 3.9, 3.2, 3.0, 2.5], 4)
    elif kind == "bool":
        starts = [True, False, rng.choice([True, False]), rng.choice([True, False])]
    else:
        starts = rng.sample(["A", "B", "C", "D", "F"], 4)
    newval = eval(newlit)
    line = f"{var} is now: {newval} <class '{type(newval).__name__}'>"
    solution = f'{var} = {newlit}\nprint("{var} is now:", {var}, type({var}))'
    cases = [Case(vars={var: s}, expect_vars={var: newval}, out=line) for s in starts]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`{var}` already holds a value. Reassign it to `{newlit}`, then print `{line}` (use `type()` for the last part).",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"Reassignment replaces the value and the type: `{var} = {newlit}` makes it a `{type(newval).__name__}`. `print(\"{var} is now:\", {var}, type({var}))` shows both.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_multi_assign(rng: random.Random) -> Question:
    """Lesson: x, y, z = 1, 2, 3  -- several variables in one line."""
    person = rng.choice(PEOPLE)
    options = [
        (("name", "age", "height_m"), (person, rng.randint(13, 18), rng.choice([1.8, 1.65, 1.7, 1.55]))),
        (("school", "year_started", "gpa"), (rng.choice(SCHOOLS), rng.randint(2019, 2024), rng.choice([3.7, 3.5, 3.9, 3.2]))),
        (("fruit", "count", "price"), (rng.choice(["apple", "banana", "cherry"]), rng.randint(2, 12), rng.choice([0.5, 1.25, 2.5]))),
    ]
    names, values = rng.choice(options)
    names_txt = ", ".join(names)
    values_txt = ", ".join(_py(v) for v in values)
    shown = " ".join(str(v) for v in values)
    solution = f"{names_txt} = {values_txt}\nprint({names_txt})"
    types_out = " ".join(f"<class '{type(v).__name__}'>" for v in values)
    cases = [
        Case(label="the three values are printed", out=shown, expect_vars=dict(zip(names, values))),
        Case(label="the variables have the right types", after=f"print({', '.join(f'type({n})' for n in names)})", out=f"{shown}\n{types_out}"),
    ]
    listing = ", ".join(f"`{n}` = `{_py(v)}`" for n, v in zip(names, values))
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Use multiple assignment (one line) to create {listing}, then print all three with one `print`, like `{shown}`",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"`{names_txt} = {values_txt}` matches names and values by position. `print({names_txt})` joins the three values with spaces.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fix_bug(rng: random.Random) -> Question:
    """Fix one of the lesson's Common Mistakes (the editor starts with the buggy code)."""
    kind = rng.choice(["quotes", "concat", "typo", "case"])
    if kind == "quotes":
        var, value, label = rng.choice(
            [("name", "Ada", "My name is"), ("name", "Reid", "My name is"), ("name", "Sam", "Hello,"), ("school", "DBHS", "My school is"), ("pet", "Rex", "My pet is"), ("color", "blue", "My favorite color is")]
        )
        starter = f'{var} = {value}\nprint("{label}", {var})'
        solution = f'{var} = "{value}"\nprint("{label}", {var})'
        target = f"{label} {value}"
        cases = [
            Case(label="run the program", out=target),
            Case(label=f"print({var}) afterwards", after=f"print({var})", out=f"{target}\n{value}"),
        ]
        prompt = f"This program should print `{target}`, but it contains a mistake from the lesson's Common Mistakes list. Fix it."
        why = f'Text needs quotes. Without them Python looks for a variable named {value}. The fix is `{var} = "{value}"`.'
    elif kind == "concat":
        var, label = rng.choice([("age", "Age"), ("score", "Score"), ("level", "Level"), ("money", "Money"), ("year_started", "Year")])
        vals = rng.sample(range(2019, 2025), 4) if var == "year_started" else rng.sample(range(2, 99), 4)
        starter = f'print("{label}: " + {var})'
        solution = f'print("{label}: " + str({var}))'
        cases = [Case(vars={var: v}, out=f"{label}: {v}") for v in vals]
        prompt = f"`{var}` holds a number (for example `{var} = {vals[0]}`), so this line crashes. Fix it so it prints `{label}: {vals[0]}`."
        why = f"A string and a number cannot be added with `+`. Use `str({var})`, a comma, or an f-string."
    elif kind == "typo":
        words = rng.choice(NAME_PAIRS).split("_")
        s = _styles(words)
        label = words[0].title()
        vals = rng.sample(range(2, 99), 4)
        typo = s["camel"]
        starter = f'print("{label}:", {typo})'
        solution = f'print("{label}:", {s["snake"]})'
        cases = [Case(vars={s["snake"]: v}, out=f"{label}: {v}") for v in vals]
        prompt = f"`{s['snake']}` already holds a number (for example {vals[0]}), but this line has a typo in the name. Fix it so it prints `{label}: {vals[0]}`."
        why = f"Names must match exactly: `{typo}` and `{s['snake']}` are different names, and the lesson uses snake_case."
    else:
        word = rng.choice(["score", "level", "money", "count", "total"])
        vals = rng.sample(range(2, 99), 4)
        starter = f'print("{word.title()}:", {word.title()})'
        solution = f'print("{word.title()}:", {word})'
        cases = [Case(vars={word: v}, out=f"{word.title()}: {v}") for v in vals]
        prompt = f"`{word}` already holds a number (for example {vals[0]}). This line should print `{word.title()}: {vals[0]}`, but the name is wrong. Fix it."
        why = f"Names are case-sensitive: `{word.title()}` and `{word}` are different variables, and only `{word}` exists."
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        task=program_task(solution, cases, starter=starter, examples=2),
        explanation=why,
    )


# ---- HARD ------------------------------------------------------------------


@generator(TOPIC, HARD, qtype="code")
def gen_code_swap_report(rng: random.Random) -> Question:
    """Swap two variables, then report all three in one f-string line."""
    x, y, z = rng.choice([("x", "y", "z"), ("a", "b", "c")])
    triples = [(1, 2, 3)] + [tuple(rng.sample(range(1, 50), 3)) for _ in range(3)]
    solution = f'{x}, {y} = {y}, {x}\nprint(f"{x}={{{x}}} {y}={{{y}}} {z}={{{z}}}")'
    cases = []
    for p, q, r in triples:
        cases.append(Case(vars={x: p, y: q, z: r}, expect_vars={x: q, y: p, z: r}, out=f"{x}={q} {y}={p} {z}={r}"))
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"`{x}`, `{y}` and `{z}` already hold numbers. Swap `{x}` and `{y}`, then print one line showing all three, like `{x}=2 {y}=1 {z}=3`",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"First swap with `{x}, {y} = {y}, {x}`, then print an f-string such as `f\"{x}={{{x}}} {y}={{{y}}} {z}={{{z}}}\"`. `{z}` is untouched.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_profile_card(rng: random.Random) -> Question:
    """Three lines of output built from three variables (text, number + 1, boolean)."""
    label1, label2, label3 = rng.choice([("Name", "Next year", "Student"), ("Player", "Age next year", "Member"), ("Name", "Age in a year", "Enrolled")])
    names = rng.sample(PEOPLE, 4)
    ages = rng.sample(range(12, 19), 4)
    flags = [True, False, True, False]
    rng.shuffle(flags)
    solution = f'print("{label1}:", name)\nprint("{label2}:", age + 1)\nprint("{label3}:", is_student)'
    cases = []
    for n, a, f in zip(names, ages, flags):
        cases.append(Case(vars={"name": n, "age": a, "is_student": f}, out=f"{label1}: {n}\n{label2}: {a + 1}\n{label3}: {f}"))
    ex = cases[0].vars
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"`name`, `age` and `is_student` are already defined (for example `name = \"{ex['name']}\"`, `age = {ex['age']}`, `is_student = {ex['is_student']}`). "
            f"Print three lines: `{label1}: {ex['name']}`, `{label2}: {ex['age'] + 1}` (the age plus one) and `{label3}: {ex['is_student']}`."
        ),
        task=program_task(solution, cases, starter="", examples=2),
        explanation="Use three `print` calls. Commas or f-strings can show numbers and booleans without casting; the middle line needs `age + 1`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_rotate(rng: random.Random) -> Question:
    """Rotate three variables (a gets b, b gets c, c gets a), then print them."""
    a, b, c = rng.choice([("a", "b", "c"), ("x", "y", "z"), ("first", "second", "third")])
    triples = [tuple(rng.sample(range(1, 60), 3)) for _ in range(4)]
    solution = f"{a}, {b}, {c} = {b}, {c}, {a}\nprint({a}, {b}, {c})"
    cases = [Case(vars={a: p, b: q, c: r}, expect_vars={a: q, b: r, c: p}, out=f"{q} {r} {p}") for p, q, r in triples]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"`{a}`, `{b}` and `{c}` already hold numbers. Rotate them: `{a}` gets the old value of `{b}`, `{b}` gets the old value of `{c}`, "
            f"and `{c}` gets the old value of `{a}`. Then print the three values on one line."
        ),
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"`{a}, {b}, {c} = {b}, {c}, {a}` uses the old values on the right, so nothing is lost. Then `print({a}, {b}, {c})`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_constant_seats(rng: random.Random) -> Question:
    """Use a constant (SCREAMING_SNAKE_CASE) and a variable together."""
    limit = rng.choice([32, 30, 28, 40, 24, 36])
    label1, label2 = rng.choice([("Students", "Seats left"), ("Players", "Spots left"), ("Joined", "Open seats")])
    mids = rng.sample([5, 9, 12, 15, limit - 8, limit - 5, limit - 3], 2)
    counts = [*mids, 0, limit]
    solution = f'print("{label1}:", students, "of", STUDENT_LIMIT)\nprint("{label2}:", STUDENT_LIMIT - students)'
    cases = [Case(vars={"STUDENT_LIMIT": limit, "students": s}, out=f"{label1}: {s} of {limit}\n{label2}: {limit - s}") for s in counts]
    ex = cases[0].vars
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"The constant `STUDENT_LIMIT` (the class holds at most {limit}) and the variable `students` are already defined. "
            f"Print `{label1}: {ex['students']} of {limit}` and then, on the next line, `{label2}: {limit - ex['students']}`. Use the constant, not the number {limit}."
        ),
        task=program_task(
            solution,
            cases,
            starter="",
            examples=2,
            requires=[(r"\bSTUDENT_LIMIT\b", "Use the constant STUDENT_LIMIT instead of typing the number")],
        ),
        explanation="Constants such as `STUDENT_LIMIT` exist so a fixed value is written in one place. Print the pieces with commas or an f-string, and subtract to get the seats left.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_swap_types(rng: random.Random) -> Question:
    """Swapping moves the value AND its type -- print the type of each variable afterwards."""
    x, y = rng.choice([("x", "y"), ("a", "b"), ("first", "second")])
    pool = [(17, "seventeen"), (3.5, True), ("a", 5), (False, 2.5), (10, "ten"), ("hello", 4.5), (7, False), (1.5, "one")]
    chosen = rng.sample(pool, 4)
    solution = f"{x}, {y} = {y}, {x}\nprint(type({x}))\nprint(type({y}))"
    cases = []
    for p, q in chosen:
        cases.append(Case(vars={x: p, y: q}, expect_vars={x: q, y: p}, out=f"<class '{type(q).__name__}'>\n<class '{type(p).__name__}'>"))
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"`{x}` and `{y}` already hold values of different types. Swap them, then print the type of `{x}` on one line and the type of `{y}` on the next.",
        task=program_task(solution, cases, starter="", examples=2),
        explanation=f"Swapping moves the value and its type together: `{x}, {y} = {y}, {x}`. Then `print(type({x}))` and `print(type({y}))` show the new types (dynamic typing).",
    )
