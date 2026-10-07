"""Question generators for the "datatypes" topic (CSF.2.B: Python Data Types).

Everything here is built from the lesson `datatypes_lab.py` and its quizzes: int / float /
complex, str, bool, None, list (append, indexing, changeable), tuple (unchangeable), set
(unique, unordered -- we never ask for the printed ORDER of a set), dict (key:value), `type()`,
`len()`, "When to use which?", the "Common Gotchas" and the Mini-Challenge "Classes
Dictionary" (the `me` dict).  The data and names are the lesson's own (`an_int`, `fruits`,
`point`, `colors`, `student`, `me`, ...), varied with the same flavour.
"""

from __future__ import annotations

import ast
import random

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NAMES,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    eval_expr,
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

TOPIC = "datatypes"

# --------------------------------------------------------------------------
# Data pools (the lesson's own flavour)
# --------------------------------------------------------------------------

FRUITS = ["apple", "banana", "cherry", "date", "kiwi", "mango", "lemon", "grape", "peach", "plum", "pear", "melon"]
COLOR_WORDS = ["red", "green", "blue", "yellow", "orange", "purple", "pink", "black", "white"]
SUBJECTS = ["Math", "English", "Art", "Science", "History", "PE", "Music", "Spanish", "Biology", "Coding", "Band", "Health"]
PEOPLE = ["Sam", "Ada", "Reid", "Ava", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon"]
LIST_NAMES = ["fruits", "snacks", "pets", "games", "songs", "foods"]
SNACKS = ["pretzel", "popcorn", "cookie", "granola", "cracker", "chips", "pizza", "taco"]
PETS = ["cat", "dog", "fish", "bird", "hamster", "turtle", "rabbit", "gecko"]
GAMES = ["chess", "tag", "poker", "bingo", "tetris", "checkers", "minecraft", "soccer"]
SONGS = ["thunder", "sunrise", "echoes", "stargazer", "firefly", "gravity", "horizon", "rhythm"]
FOODS = ["sushi", "tacos", "pasta", "pizza", "salad", "ramen", "burger", "waffles"]
ITEM_POOLS = {"fruits": FRUITS, "snacks": SNACKS, "pets": PETS, "games": GAMES, "songs": SONGS, "foods": FOODS}

# What type() reports, and the wrong types a student is most likely to pick instead.
CONFUSE = {
    "int": ["float", "str", "bool"],
    "float": ["int", "str", "complex"],
    "str": ["int", "list", "bool"],
    "bool": ["int", "str", "NoneType"],
    "NoneType": ["bool", "int", "str"],
    "list": ["tuple", "set", "dict"],
    "tuple": ["list", "set", "dict"],
    "set": ["dict", "list", "tuple"],
    "dict": ["set", "list", "tuple"],
    "complex": ["float", "int", "str"],
}


def cls(name: str) -> str:
    """How print(type(x)) shows a type."""
    return f"<class '{name}'>"


def lit(value) -> str:
    """Python source for a value, in the lesson's style (double-quoted strings)."""
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(lit(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(lit(v) for v in value) + ("," if len(value) == 1 else "") + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{lit(k)}: {lit(v)}" for k, v in value.items()) + "}"
    return repr(value)


def set_src(items) -> str:
    """Source of a set literal that lists ``items`` in the given order (duplicates allowed)."""
    return "{" + ", ".join(lit(v) for v in items) + "}"


def out_text(code: str) -> str:
    """What a (trusted) snippet prints."""
    res = run_code(code.strip("\n"))
    if res.error:
        raise GenerationError(f"snippet raised {res.error}:\n{code}")
    return res.output


def type_name(expr_src: str) -> str | None:
    """The type name of a literal expression, or None if it is not a valid literal."""
    try:
        return type(ast.literal_eval(expr_src)).__name__
    except (ValueError, SyntaxError):
        return None


def as_choice(value) -> str:
    """A value as it reads in an answer choice (strings keep their quotes)."""
    return lit(value) if isinstance(value, str) else repr(value)


def mutated_outputs(lines, rng: random.Random) -> list[str]:
    """Wrong full outputs for a trace question.

    ``lines`` is ``[(right_line, [wrong_line, ...]), ...]``.  Each wrong output changes exactly one
    line (the usual slip for that line); the last few change two lines.  Most plausible first.
    """
    lines = [(r, [w for w in ws if w != r]) for r, ws in lines]
    n = len(lines)
    right = [r for r, _ in lines]

    def with_(changes: dict[int, str]) -> str:
        row = list(right)
        for i, w in changes.items():
            row[i] = w
        return "\n".join(row)

    firsts, rest, doubles = [], [], []
    for i, (_, wrongs) in enumerate(lines):
        if wrongs:
            firsts.append(with_({i: wrongs[0]}))
            rest.extend(with_({i: w}) for w in wrongs[1:])
    for i in range(n):
        for j in range(i + 1, n):
            if lines[i][1] and lines[j][1]:
                doubles.append(with_({i: lines[i][1][0], j: lines[j][1][0]}))
    for group in (firsts, rest, doubles):
        rng.shuffle(group)
    return firsts + rest + doubles


def trace_question(
    difficulty: int,
    code: str,
    lines,
    rng: random.Random,
    explanation: str,
    prompt: str = "What does this code print?",
    first: list[str] | None = None,
) -> Question:
    """'What does this print?' where I also spell out the expected lines, so a typo in a generator
    (the right text not matching what Python really prints) is caught immediately."""
    right = "\n".join(r for r, _ in lines)
    got = out_text(code)
    if got != right:
        raise GenerationError(f"expected output {right!r} but the snippet prints {got!r}:\n{code}")
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[*(first or []), *mutated_outputs(lines, rng)],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
    )


def student_dict(rng: random.Random) -> dict:
    """The lesson's `student = {"name": "Sam", "grade": 11, "gpa": 3.6}`, varied."""
    name = rng.choice(PEOPLE)
    return {"name": name, "grade": rng.choice([9, 10, 11, 12]), "gpa": round(rng.choice([2.8, 3.0, 3.2, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0]), 1)}


def me_dict(rng: random.Random, n_classes: int | None = None) -> dict:
    """The Mini-Challenge `me` dictionary: name, grade and a list of class names."""
    n = n_classes if n_classes is not None else rng.choice([3, 3, 4, 5])
    return {"name": rng.choice(PEOPLE), "grade": rng.choice([9, 10, 11, 12]), "classes": rng.sample(SUBJECTS, n)}


def item_list(rng: random.Random, n: int | None = None) -> tuple[str, list[str]]:
    """A (variable_name, items) pair such as ("fruits", ["apple", "banana", "cherry"])."""
    name = rng.choice(list(ITEM_POOLS))
    count = n if n is not None else rng.choice([3, 3, 4])
    return name, rng.sample(ITEM_POOLS[name], count)


# --------------------------------------------------------------------------
# One-line rules about literals, reused in explanations
# --------------------------------------------------------------------------

TYPE_RULE = {
    "int": "A whole number with no decimal point and no quotes is an `int`.",
    "float": "A number with a decimal point is a `float`.",
    "str": "Anything inside quotes is a `str`, even if it looks like a number.",
    "bool": "`True` and `False` (capital first letter, no quotes) are the `bool` values.",
    "NoneType": "`None` means \"no value\", and its type is `NoneType`.",
    "list": "Square brackets `[ ]` make a `list`.",
    "tuple": "Parentheses `( )` with commas make a `tuple`.",
    "set": "Curly braces holding single items make a `set`.",
    "dict": "Curly braces holding `key: value` pairs make a `dict`.",
    "complex": "A number ending in `j`, like `2 + 3j`, is a `complex` number.",
}

# ==========================================================================
# EASY -- multiple choice (vocabulary and one-line results, like the Canvas quiz)
# ==========================================================================

LITERALS = [
    ("42", "int"), ("-7", "int"), ("100", "int"), ("2024", "int"),
    ("3.14159", "float"), ("2.0", "float"), ("9.81", "float"), ("0.5", "float"),
    ('"Intro to Python"', "str"), ('"42"', "str"), ('"True"', "str"), ('"3.5"', "str"), ('"Sam"', "str"),
    ("True", "bool"), ("False", "bool"),
    ("None", "NoneType"),
    ('["apple", "banana", "cherry"]', "list"), ("[1, 2, 3]", "list"),
    ("(10, 20)", "tuple"), ('("red", "green")', "tuple"),
    ('{"red", "green", "blue"}', "set"), ("{1, 2, 3}", "set"),
    ('{"name": "Sam", "grade": 11}', "dict"), ('{"x": 10, "y": 20}', "dict"),
    ("2 + 3j", "complex"), ("4 - 1j", "complex"),
]


@generator(TOPIC, EASY)
def gen_type_of_literal(rng: random.Random) -> Question:
    """'What does print(type(...)) show?' for a literal -- the lab's `type()` idea."""
    src, t = rng.choice(LITERALS)
    if type_name(src) != t:
        raise GenerationError(f"{src} is not a {t}")
    first = None
    if t == "str":  # the classic trap: "42" looks like an int
        inner = ast.literal_eval(src)
        if inner.isdigit():
            first = "int"
        elif inner.replace(".", "", 1).isdigit():
            first = "float"
        elif inner in ("True", "False"):
            first = "bool"
    wrong_types = ([first] if first else []) + CONFUSE[t]
    distractors = [cls(w) for w in wrong_types]
    explanation = f"{TYPE_RULE[t]} So `type` reports `{cls(t)}`."
    style = rng.choice(["direct", "variable", "inline"])
    if style == "inline":
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=f"What does `type({src})` return?",
            correct=cls(t),
            distractors=distractors,
            explanation=explanation,
            rng=rng,
        )
    if style == "direct":
        code = f"print(type({src}))"
    else:
        var = {"int": "an_int", "float": "a_float", "str": "title", "bool": "is_ready", "NoneType": "mystery",
               "list": "fruits", "tuple": "point", "set": "colors", "dict": "student", "complex": "a_complex"}[t]
        code = f"{var} = {src}\nprint(type({var}))"
    return output_question(
        topic=TOPIC, difficulty=EASY, code=code, distractors=distractors, explanation=explanation, rng=rng
    )


def _value_and_traps(t: str, rng: random.Random) -> tuple[str, list[str], str]:
    """(a literal of type t, look-alike literals of other types, extra note for the explanation)."""
    if t == "bool":
        return rng.choice(["True", "False"]), ['"False"', '"True"', "0", "1", "none", "true"], \
            " `\"False\"` has quotes, so it is a `str`, and `0` is an `int`."
    if t == "int":
        n = rng.choice([7, 42, 100, 15, 2024, 365, 12])
        return str(n), [f'"{n}"', f"{n}.0", f"[{n}]", f"({n}, {n + 1})"], ""
    if t == "float":
        x = rng.choice(["3.14", "2.5", "9.81", "0.75", "1.80"])
        return x, [f'"{x}"', str(int(float(x))), x.replace(".", ""), f"[{x}]"], ""
    if t == "str":
        s = rng.choice(["Python", "hello", "Sam", "42", "3.5", "True"])
        if s == "True":
            return f'"{s}"', ["True", "1", f"[{s}]", "None"], ""
        if s in ("42", "3.5"):
            return f'"{s}"', [s, f"[{s}]", "True", "None"], ""
        return f'"{s}"', ["42", "3.5", f'["{s}"]', "True", "None"], ""
    if t == "NoneType":
        return "None", ['"None"', "0", '""', "False", "[]", "none"], " `0`, `\"\"` and `False` are real values; `None` means there is no value."
    if t == "list":
        items = rng.sample(FRUITS, 3)
        return lit(items), [lit(tuple(items)), set_src(items), '"' + ", ".join(items) + '"', lit({items[0]: items[1]})], ""
    if t == "tuple":
        a, b = rng.choice([(10, 20), (3, 4), (5, 9), (0, 7)])
        return f"({a}, {b})", [f"[{a}, {b}]", f"{{{a}, {b}}}", f'"({a}, {b})"', f"{{{a}: {b}}}"], ""
    if t == "set":
        colors = rng.sample(COLOR_WORDS, 3)
        return set_src(colors), [lit(colors), lit(tuple(colors)), lit({colors[0]: colors[1]}), '"' + " ".join(colors) + '"'], ""
    if t == "dict":
        nm = rng.choice(PEOPLE)
        g = rng.choice([9, 10, 11, 12])
        return lit({"name": nm, "grade": g}), [set_src(["name", nm]), lit(["name", nm]), lit(("name", nm)), f'"name: {nm}"'], ""
    if t == "complex":
        c = rng.choice(["2 + 3j", "4 - 1j", "1 + 5j"])
        re_part = c.split()[0]
        return c, [f"{re_part} + 3", f'"{c.replace(" ", "")}"', "2.3", "[2, 3]", "(2, 3)"], ""
    raise GenerationError(t)


@generator(TOPIC, EASY)
def gen_which_value_has_type(rng: random.Random) -> Question:
    """Canvas: 'Which value has the type bool?'  (choices "False", 0, False, none)"""
    t = rng.choice(list(CONFUSE))
    correct, traps, note = _value_and_traps(t, rng)
    if type_name(correct) != t:
        raise GenerationError(f"{correct} is not a {t}")
    traps = [x for x in traps if type_name(x) != t]
    rng.shuffle(traps)
    prompt = 'Which value represents "no value" in Python?' if t == "NoneType" else f"Which value has the type `{t}`?"
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=traps,
        explanation=TYPE_RULE[t] + note,
        rng=rng,
    )


VOCAB = [
    # (prompt, correct, distractors, explanation)
    ("Which data type uses key:value pairs?", "dict", ["list", "tuple", "set"],
     "A `dict` stores labeled `key: value` pairs, like `{\"name\": \"Sam\"}`."),
    ("Which data type is best for \"a collection where uniqueness matters\"?", "set", ["list", "tuple", "str"],
     "A `set` keeps only one copy of each item, so duplicates collapse."),
    ("Which data type is ordered and changeable?", "list", ["tuple", "set", "str"],
     "A `list` keeps its order and you can change it, for example with `append`."),
    ("Which data type is ordered but unchangeable?", "tuple", ["list", "set", "dict"],
     "A `tuple` keeps its order but can't be changed after it is created, which makes it a safer choice for fixed data like `(10, 20)`."),
    ("Which data type is unordered and removes duplicates?", "set", ["list", "tuple", "str"],
     "A `set` is unordered, and a repeated item like the second `\"red\"` collapses into one."),
    ("Which value represents \"no value\" in Python?", "None", ["0", "\"\"", "False"],
     "`None` is the special value that means \"no value\". `0`, an empty string and `False` are real values."),
    ("Which data type is used for whole numbers?", "int", ["float", "str", "bool"],
     "An `int` holds whole numbers such as `42`."),
    ("Which data type is used for numbers with a decimal point?", "float", ["int", "str", "complex"],
     "A `float` holds numbers with a decimal point, such as `3.14159`."),
    ("Which data type is used for text?", "str", ["int", "bool", "float"],
     "A `str` (string) is text inside quotes, like `\"Intro to Python\"`."),
    ("Which data type has only two possible values?", "bool", ["int", "str", "list"],
     "A `bool` is either `True` or `False`."),
    ("What does `type(value)` return?", "The value's data type", ["The value's memory address", "The value as a string", "The number of characters"],
     "`type(value)` tells you the data type of a value, such as `<class 'int'>`."),
    ("Which built-in function tells you how many items a list has?", "len()", ["size()", "length()", "count()"],
     "`len()` returns the number of items, for example `len([\"a\", \"b\", \"c\"])` is `3`."),
    ("Which list method adds an item to the end of the list?", "append()", ["add()", "push()", "put()"],
     "`fruits.append(\"date\")` puts \"date\" at the end of the list."),
    ("In a list, which index gets the first item?", "0", ["1", "-1", "first"],
     "Python counts from 0, so `fruits[0]` is the first item."),
    ("In a list, which index gets the last item?", "-1", ["0", "1", "-0"],
     "A negative index counts from the end, so `fruits[-1]` is the last item."),
    ("What does it mean that a list is \"mutable\"?", "It can be changed after it is created", ["It can never be changed", "It can only hold text", "It has no value"],
     "Lists are changeable: you can add, remove or replace items. Tuples are the unchangeable ones."),
    ("What does the `j` in `2 + 3j` tell Python?", "The number is a complex number", ["The number is a float", "The number is negative", "The number is text"],
     "A number with a `j` part, like `2 + 3j`, has the type `complex`."),
]


@generator(TOPIC, EASY)
def gen_vocab(rng: random.Random) -> Question:
    """Definition / vocabulary questions in the voice of the Canvas quiz."""
    prompt, correct, wrong, why = rng.choice(VOCAB)
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


TRUE_STATEMENTS = [
    # (prompt, correct, wrong list, explanation)
    ("Which statement about lists and tuples is true?", "Lists are changeable; tuples are unchangeable.",
     ["Lists are unchangeable and tuples are changeable.", "Both lists and tuples are changeable.", "Both lists and tuples are unchangeable."],
     "A list can be changed (for example with `append`), but a tuple like `(10, 20)` can't."),
    ("Which statement about sets is true?", "A set removes duplicate items.",
     ["A set keeps its items in a fixed order.", "A set stores key:value pairs.", "A set can be indexed with `colors[0]`."],
     "In `{\"red\", \"green\", \"blue\", \"red\"}` the duplicate `\"red\"` collapses. Sets are unordered, so there is no `[0]`."),
    ("Which statement about dictionaries is true?", "A value is found by using its key.",
     ["A value is found by its position number.", "A dictionary can only hold numbers.", "A dictionary keeps duplicate keys."],
     "You look values up by key, like `student[\"name\"]`."),
    ("Which statement about `None` is true?", "It represents \"no value\".",
     ["It is the same as the number 0.", "It is the same as an empty string.", "It is the same as `False`."],
     "`None` means there is no value at all; its type is `NoneType`."),
    ("Which statement about the `bool` type is true?", "It can only be `True` or `False`.",
     ["It can be any whole number.", "It must be written in quotes.", "It can be written `true` or `false`."],
     "Python's booleans are `True` and `False`, with a capital first letter and no quotes."),
    ("Which statement about tuples is true?", "Their items can't be changed after they are created.",
     ["You can add items to them with `append`.", "They hold key:value pairs.", "They use curly braces."],
     "A tuple is ordered and unchangeable: `point = (10, 20)` stays `(10, 20)`."),
    ("Which statement about lists is true?", "You can add an item with `append`.",
     ["You can't change them after creating them.", "They can only hold text.", "They remove duplicates automatically."],
     "A list is ordered and changeable, so `fruits.append(\"date\")` works."),
    ("Which statement about `fruits[0]` is true?", "It is the first item of the list.",
     ["It is the last item of the list.", "It is the number of items in the list.", "It causes an error because lists start at 1."],
     "Indexes start at 0, so `fruits[0]` is the first item."),
    ("Which statement about `len()` is true?", "It returns how many items (or characters) there are.",
     ["It returns the last item.", "It returns the data type.", "It only works on numbers."],
     "`len([\"a\", \"b\", \"c\"])` is `3` and `len(\"Python\")` is `6`."),
    ("Which statement about Python types is true?", "The type is decided by the value assigned.",
     ["You must declare the type before using a variable.", "A variable can never change type.", "Only strings have types."],
     "This is called dynamic typing: `age = 17` makes an `int`, and later `age = \"seventeen\"` makes it a `str`."),
    ("Which statement about `\"5\"` and `5` is true?", "`\"5\"` is a str and `5` is an int.",
     ["Both are ints.", "Both are strs.", "`\"5\"` is an int and `5` is a str."],
     "Quotes make a value a `str`, even when it looks like a number."),
    ("Which statement about the `input()` function is true?", "It always returns a str.",
     ["It returns an int when you type digits.", "It returns a float when possible.", "It returns None unless you cast it."],
     "`input()` gives back text, so cast it with `int()` or `float()` when you need math."),
]


@generator(TOPIC, EASY)
def gen_true_statement(rng: random.Random) -> Question:
    """Canvas: 'Which statement about lists and tuples is true?' -- one true statement, three slips."""
    prompt, correct, wrong, why = rng.choice(TRUE_STATEMENTS)
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


@generator(TOPIC, EASY)
def gen_len_result(rng: random.Random) -> Question:
    """Canvas: 'What does len(["a","b","c"]) return?'  Also strings, tuples, dicts, and a set with a repeat."""
    form = rng.choice(["list_inline", "list_var", "string", "tuple", "dict", "set"])
    err_choice = rng.random() < 0.5
    if form == "list_inline":
        items = rng.choice([["a", "b", "c"], ["x", "y"], ["red", "green", "blue", "gold"], ["one", "two", "three", "four", "five"]])
        expr, setup = f"len({lit(items)})", ""
        n, why = len(items), f"`len` counts the items in the list: there are {len(items)}."
    elif form == "list_var":
        name, items = item_list(rng, rng.choice([3, 4, 5]))
        expr, setup = f"len({name})", f"{name} = {lit(items)}"
        n, why = len(items), f"`len({name})` counts the items in the list, and there are {len(items)}."
    elif form == "string":
        word = rng.choice(["Python", "Intro to Python", "Blast off", "code", "Data Types", "banana"])
        expr, setup = "len(title)", f"title = {lit(word)}"
        n, why = len(word), "`len` counts every character in a string, including the spaces." if " " in word else "`len` counts the characters in a string."
    elif form == "tuple":
        a = rng.choice([(10, 20), (3, 4, 5), (1, 2, 3, 4), (7, 8, 9)])
        expr, setup = "len(point)", f"point = {lit(a)}"
        n, why = len(a), f"`len` counts the items in the tuple: there are {len(a)}."
    elif form == "dict":
        d = student_dict(rng)
        expr, setup = "len(student)", f"student = {lit(d)}"
        n, why = 3, "`len` of a dict counts the keys (`name`, `grade` and `gpa`), so it is 3."
    else:
        colors = rng.sample(COLOR_WORDS, 3)
        items = colors + [colors[0]]
        rng.shuffle(items)
        expr, setup = "len(colors)", f"colors = {set_src(items)}"
        n, why = 3, "The repeated item collapses in a set, so only 3 different items are left."
    if eval_expr(expr, setup) != n:
        raise GenerationError("len mismatch")
    distractors = [str(n - 1), str(n + 1), str(n + 2) if n < 3 else str(n - 2)]
    if err_choice and form in ("list_inline", "list_var", "tuple"):
        distractors = [str(n - 1), str(n + 1), "Error"]
    if form == "set":
        distractors = ["4", "2", "6"]
    if form == "dict":
        distractors = ["2", "4", "6"]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"What does `{expr}` return?",
        correct=str(n),
        distractors=distractors,
        explanation=why,
        rng=rng,
        code=setup or None,
    )


def _record(rng: random.Random) -> tuple[str, dict]:
    """A labeled-fields dictionary: the lesson's `student`, sometimes a pet or a player."""
    kind = rng.choice(["student", "student", "student", "pet", "player"])
    if kind == "student":
        return "student", student_dict(rng)
    if kind == "pet":
        return "pet", {"name": rng.choice(["Rex", "Milo", "Luna", "Coco", "Bella"]), "age": rng.choice([2, 3, 5, 8]), "kind": rng.choice(["dog", "cat", "gecko"])}
    return "player", {"name": rng.choice(PEOPLE), "score": rng.choice([120, 450, 980, 1500]), "level": rng.choice([2, 3, 5, 7])}


@generator(TOPIC, EASY)
def gen_dict_access_syntax(rng: random.Random) -> Question:
    """Canvas: 'Which access gets the value for key "name" in student = {...}?'"""
    var, d = _record(rng)
    key = rng.choice(list(d))
    wrong = [f'{var}("{key}")', f"{var}.{key}", f"{var}[0]", f"{var}[{key}]"]
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f'Which expression gets the value for the key "{key}"?',
        setup=f"{var} = {lit(d)}",
        target=d[key],
        correct_expr=f'{var}["{key}"]',
        wrong_exprs=wrong,
        explanation=f'Use square brackets and the key in quotes: `{var}["{key}"]` is `{lit(d[key])}`. Without the quotes Python looks for a variable named `{key}`.',
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_list_index_expr(rng: random.Random) -> Question:
    """'Which expression gives the first / last / "cherry" item?'"""
    name, items = item_list(rng, rng.choice([3, 4]))
    setup = f"{name} = {lit(items)}"
    mode = rng.choice(["first", "last", "second", "named"])
    if mode == "first":
        prompt, correct, target = f"Which expression gets the first item of `{name}`?", f"{name}[0]", items[0]
        wrong = [f"{name}[1]", f"{name}[-1]", f'{name}("first")', f"{name}[first]"]
        why = f"Indexes start at 0, so the first item is `{name}[0]`."
    elif mode == "last":
        prompt, correct, target = f"Which expression gets the last item of `{name}`?", f"{name}[-1]", items[-1]
        wrong = [f"{name}[0]", f"{name}[{len(items)}]", f"{name}[last]", f"{name}[1]"]
        why = f"`{name}[-1]` counts from the end. `{name}[{len(items)}]` is one past the end, because the last index is {len(items) - 1}."
    elif mode == "second":
        prompt, correct, target = f"Which expression gets the second item of `{name}`?", f"{name}[1]", items[1]
        wrong = [f"{name}[2]", f"{name}[0]", f"{name}(2)", f"{name}[-2]" if len(items) > 3 else f"{name}[second]"]
        why = f"Indexes start at 0, so the second item is `{name}[1]`."
    else:
        i = rng.randrange(1, len(items))
        prompt, correct, target = f'Which expression gets the item "{items[i]}"?', f"{name}[{i}]", items[i]
        wrong = [f"{name}[{i + 1}]", f"{name}[{i - 1}]", f'{name}["{items[i]}"]', f"{name}({i})"]
        why = f'"{items[i]}" is at index {i} (counting from 0), so use `{name}[{i}]`.'
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, setup=setup, target=target,
        correct_expr=correct, wrong_exprs=wrong, explanation=why, rng=rng,
    )


@generator(TOPIC, EASY)
def gen_append_effect(rng: random.Random) -> Question:
    """Canvas: 'If fruits = ["apple", "banana"], what does fruits.append("cherry") do?'"""
    name, items = item_list(rng, 2)
    pool = [x for x in ITEM_POOLS[name] if x not in items]
    new = rng.choice(pool)
    prompt = f"If {name} = {lit(items)}, what does {name}.append({lit(new)}) do?"
    correct = f"Adds {lit(new)} to the end of {name}"
    distractors = [
        f"Returns a new list but doesn't change {name}",
        f"Removes {lit(items[1])}",
        f"Adds {lit(new)} to the start of {name}",
        f"Replaces {lit(items[0])} with {lit(new)}",
        "Sorts the list",
    ]
    rng.shuffle(distractors)
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=distractors,
        explanation=f"`append` changes the list itself by adding the new item at the end: `{lit(items + [new])}`.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_input_type(rng: random.Random) -> Question:
    """Common Gotcha: input() returns a string -- even when the user types digits."""
    typed = rng.choice(["16", "3.5", "100", "42", "True", "7.25"])
    var = rng.choice(["age", "user_num", "answer", "score"])
    code = f'{var} = input("Enter a value: ")'
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"A user types `{typed}` when this runs. What is `type({var})`?",
        correct=cls("str"),
        distractors=[cls("float") if "." in typed else cls("int"), cls("bool") if typed == "True" else cls("int"), cls("float"), cls("list")],
        explanation=f"`input()` always returns a `str`, even if the user types digits. Cast it with `int()` or `float()` when you need a number.",
        rng=rng,
        code=code,
    )


# ==========================================================================
# MEDIUM -- multiple choice (trace a lab-style snippet, pick the right code, spot the mistake)
# ==========================================================================

SCALAR_SPECS = [
    # (type, variable, source)
    ("int", "an_int", "42"), ("int", "count", "7"), ("int", "score", "100"), ("int", "year", "2024"), ("int", "age", "17"),
    ("float", "a_float", "3.14159"), ("float", "price", "4.5"), ("float", "height_m", "1.80"), ("float", "gpa", "3.6"),
    ("float", "temperature", "98.6"),
    ("complex", "a_complex", "2 + 3j"), ("complex", "z", "4 - 1j"),
    ("bool", "is_ready", "False"), ("bool", "is_student", "True"), ("bool", "is_raining", "False"),
    ("NoneType", "mystery", "None"), ("NoneType", "result", "None"),
    ("str", "title", '"Intro to Python"'), ("str", "name", '"Ada"'), ("str", "word", '"Python"'),
]


@generator(TOPIC, MEDIUM)
def gen_lab_scalars_trace(rng: random.Random) -> Question:
    """The lab's Numbers / Booleans / None blocks: `print(x, type(x))`."""
    first = rng.choice(SCALAR_SPECS)
    second = rng.choice([sp for sp in SCALAR_SPECS if sp[0] != first[0]])
    specs = [first, second]
    code = "\n".join(f"{v} = {s}\nprint({v}, type({v}))" for _, v, s in specs)
    lines = []
    notes = []
    for t, v, s in specs:
        printed = out_text(f"{v} = {s}\nprint({v})")
        right = f"{printed} {cls(t)}"
        wrong = []
        if t == "float" and printed != s:
            wrong.append(f"{s} {cls(t)}")
            notes.append(f"Python prints `{s}` as `{printed}`.")
        if t == "complex":
            wrong.append(f"{s.replace(' ', '')} {cls(t)}")
            notes.append("Complex numbers print in parentheses, like `(2+3j)`.")
        if t == "str":
            wrong.append(f"{s} {cls(t)}")
            notes.append("`print` shows a string without its quotes.")
        if t == "NoneType":
            wrong.append(f"{printed} <class 'None'>")
        wrong += [f"{printed} {cls(c)}" for c in CONFUSE[t]]
        lines.append((right, wrong))
    explanation = "Each `print(x, type(x))` shows the value, then its type. " + " ".join(notes[:1] or ["Remember: `42` is an `int`, `3.14159` is a `float`, and `True`/`False` are `bool`."])
    return trace_question(MEDIUM, code, lines, rng, explanation.strip())


TITLES = ["Intro to Python", "Data Types Lab", "Hello World", "Python Rocks", "Code Club", "Learn to Code", "Blast Off"]


@generator(TOPIC, MEDIUM)
def gen_lab_string_trace(rng: random.Random) -> Question:
    """The lab's String block: len, upper and a slice."""
    title = rng.choice(TITLES)
    k = rng.choice([3, 4, 5, 6])
    code = (
        f"title = {lit(title)}\n"
        'print("Length:", len(title))\n'
        'print("Upper:", title.upper())\n'
        f'print("Slice [0:{k}]:", title[0:{k}])'
    )
    n = len(title)
    lines = [
        (f"Length: {n}", [f"Length: {n - title.count(' ')}", f"Length: {n - 1}", f"Length: {n + 1}"]),
        (f"Upper: {title.upper()}", [f"Upper: {title}", f"Upper: {title.lower()}"]),
        (f"Slice [0:{k}]: {title[0:k]}", [f"Slice [0:{k}]: {title[0:k + 1]}", f"Slice [0:{k}]: {title[1:k]}", f"Slice [0:{k}]: {title[0:k - 1]}"]),
    ]
    return trace_question(
        MEDIUM, code, lines, rng,
        f"`len` counts every character (spaces too), `.upper()` makes capitals, and `title[0:{k}]` takes {k} characters: positions 0 up to but not including {k}.",
    )


@generator(TOPIC, MEDIUM)
def gen_lab_list_trace(rng: random.Random) -> Question:
    """The lab's List block: append, print, index, len."""
    name, items = item_list(rng, rng.choice([2, 3]))
    new = rng.choice([x for x in ITEM_POOLS[name] if x not in items])
    single = name[:-1]
    idx = rng.choice([0, -1])
    word = "first" if idx == 0 else "last"
    code = (
        f"{name} = {lit(items)}\n"
        f"{name}.append({lit(new)})\n"
        f"print({name})\n"
        f'print("{word} {single}:", {name}[{idx}])\n'
        f"print(len({name}))"
    )
    after = items + [new]
    n = len(after)
    right_item = after[idx]
    other_item = after[-1] if idx == 0 else after[0]
    lines = [
        (repr(after), [repr(items), repr([new] + items)]),
        (f"{word} {single}: {right_item}", [f"{word} {single}: {other_item}"]),
        (str(n), [str(n - 1), str(n + 1)]),
    ]
    forgot = [repr(items), f"{word} {single}: {items[idx]}", str(len(items))]
    front = [repr([new] + items), f"{word} {single}: {([new] + items)[idx]}", str(n)]
    return trace_question(
        MEDIUM, code, lines, rng,
        f"`append` adds {lit(new)} to the end, so the list now has {n} items. Index `0` is still the first item and `-1` is the new last item.",
        first=["\n".join(forgot), "\n".join(front)],
    )


@generator(TOPIC, MEDIUM)
def gen_lab_dict_trace(rng: random.Random) -> Question:
    """The lab's Dictionary block: `student["name"]`, plus a bit of math and type()."""
    d = student_dict(rng)
    templates = [
        (
            'print("student name:", student["name"])',
            f"student name: {d['name']}",
            [f"student name: {d['grade']}", "student name: name"],
        ),
        (
            'print(student["grade"] + 1)',
            str(d["grade"] + 1),
            [f"{d['grade']}1", str(d["grade"])],
        ),
        (
            'print(type(student["gpa"]))',
            cls("float"),
            [cls("str"), cls("int")],
        ),
        (
            "print(len(student))",
            "3",
            ["2", "4"],
        ),
    ]
    chosen = rng.sample(templates, 3)
    code = f"student = {lit(d)}\n" + "\n".join(c for c, _, _ in chosen)
    lines = [(r, w) for _, r, w in chosen]
    return trace_question(
        MEDIUM, code, lines, rng,
        'Use the key in square brackets to get a value: `student["grade"]` is a number, so `+ 1` is real addition. `len(student)` counts the keys.',
    )


ALIAS_PAIRS = [("scores", "backup"), ("team", "squad"), ("fruits", "basket"), ("players", "roster"), ("names", "group")]


@generator(TOPIC, MEDIUM)
def gen_list_alias(rng: random.Random) -> Question:
    """Common Gotcha: 'Lists are mutable: changing one place changes all references to that same list.'"""
    a, b = rng.choice(ALIAS_PAIRS)
    use_numbers = rng.random() < 0.5
    if use_numbers:
        items = rng.sample([60, 70, 75, 80, 85, 90, 95], 3)
        new = rng.choice([100, 55, 65])
    else:
        items = rng.sample(FRUITS, 3)
        new = rng.choice([f for f in FRUITS if f not in items])
    if rng.random() < 0.5:
        change = f"{b}.append({lit(new)})"
        result = items + [new]
        wrong = [repr(items), repr([new]), repr(items + [new, new])]
    else:
        change = f"{b}[0] = {lit(new)}"
        result = [new] + items[1:]
        wrong = [repr(items), repr(items + [new]), repr([new])]
    code = f"{a} = {lit(items)}\n{b} = {a}\n{change}\nprint({a})"
    return output_question(
        topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong,
        explanation=f"`{b} = {a}` doesn't make a new list: both names refer to the same list. So changing it through `{b}` changes what `{a}` shows too.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_index_read(rng: random.Random) -> Question:
    """What happens when you read an item: lists, tuples and strings can be indexed; sets can't."""
    form = rng.choice(["list", "tuple", "str", "set", "dict", "list_range"])
    name, items = item_list(rng, 3)
    colors = rng.sample(COLOR_WORDS, 3)
    d = student_dict(rng)
    if form == "list":
        i = rng.choice([1, 2])
        code = f"{name} = {lit(items)}\nprint({name}[{i}])"
        wrong = [items[i - 1], items[(i + 1) % 3], "None"]
        why = f"Indexes start at 0, so `{name}[{i}]` is the item in position {i + 1}."
    elif form == "tuple":
        a, b = rng.choice([(10, 20), (3, 4), (5, 9)])
        i = rng.choice([0, 1])
        code = f"point = ({a}, {b})\nprint(point[{i}])"
        wrong = [str((a, b)[1 - i]), str(a + b), "None"]
        why = "A tuple can be indexed like a list; it just can't be changed."
    elif form == "str":
        word = rng.choice(["Python", "banana", "loops", "student"])
        i = rng.choice([0, -1])
        code = f"word = {lit(word)}\nprint(word[{i}])"
        wrong = [word[-1 if i == 0 else 0], word[1], word, word[2], "None"]
        why = "Strings can be indexed too: `word[0]` is the first character and `word[-1]` is the last."
    elif form == "set":
        code = f"colors = {set_src(colors)}\nprint(colors[0])"
        wrong = [colors[0], colors[1], "None"]
        why = "A set is unordered, so it has no positions. `colors[0]` is an error; use `in` to check whether an item is in a set."
    elif form == "dict":
        code = f"student = {lit(d)}\nprint(student[0])"
        wrong = [d["name"], str(d["grade"]), "None"]
        why = 'A dict is looked up by key, not by position. `student[0]` fails; `student["name"]` works.'
    else:
        code = f"{name} = {lit(items)}\nprint({name}[3])"
        wrong = [items[2], items[0], "None"]
        why = f"The list has 3 items, so the last index is 2. `{name}[3]` is past the end."
    return output_question(
        topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong, explanation=why, rng=rng,
        prompt="What happens when this code runs?", allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_change_in_place(rng: random.Random) -> Question:
    """Mutable vs unchangeable: change one item of a list, a tuple or a string."""
    form = rng.choice(["list", "list", "tuple", "str"])
    name, items = item_list(rng, 3)
    if form == "list":
        new = rng.choice([f for f in ITEM_POOLS[name] if f not in items])
        i = rng.choice([0, 1, 2])
        code = f"{name} = {lit(items)}\n{name}[{i}] = {lit(new)}\nprint({name})"
        changed = list(items)
        changed[i] = new
        wrong = [repr(items), repr(items + [new]), "Error: TypeError"]
        why = f"Lists are changeable: `{name}[{i}] = {lit(new)}` replaces that item."
    elif form == "tuple":
        a, b = rng.choice([(10, 20), (3, 4), (5, 9)])
        code = f"point = ({a}, {b})\npoint[0] = 99\nprint(point)"
        wrong = [f"(99, {b})", f"({a}, {b})", f"({a}, 99)"]
        why = "Tuples are unchangeable, so `point[0] = 99` is an error."
    else:
        word = rng.choice(["Python", "banana", "student", "coding"])
        code = f'word = {lit(word)}\nword[0] = "J"\nprint(word)'
        wrong = ["J" + word[1:], word, "J"]
        why = "Strings are unchangeable too, so `word[0] = \"J\"` is an error. You would have to build a new string."
    return output_question(
        topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong, explanation=why, rng=rng,
        prompt="What happens when this code runs?", allow_error=True,
    )


@generator(TOPIC, MEDIUM)
def gen_set_dedupe(rng: random.Random) -> Question:
    """Lab: `colors = {"red", "green", "blue", "red"}  # duplicate "red" collapses`.  Never prints the set itself."""
    form = rng.choice(["literal", "from_list", "names"])
    if form == "literal":
        colors = rng.sample(COLOR_WORDS, rng.choice([3, 4]))
        items = colors + rng.sample(colors, rng.choice([1, 2]))
        rng.shuffle(items)
        code = f"colors = {set_src(items)}\nprint(len(colors))"
        n = len(colors)
        wrong = [str(len(items)), str(n - 1), str(n + 1), str(n + 2), "2"]
        why = f"Duplicates collapse in a set, so only {n} different colors are left."
    elif form == "from_list":
        pool = rng.sample([1, 2, 3, 4, 5, 6], 3)
        numbers = pool + rng.choices(pool, k=rng.choice([3, 4]))
        rng.shuffle(numbers)
        code = f"numbers = {lit(numbers)}\nunique = set(numbers)\nprint(len(numbers), len(unique))"
        wrong = [f"{len(numbers)} {len(numbers)}", f"{len(pool)} {len(numbers)}", f"{len(numbers)} {len(pool) + 1}"]
        why = "`set(numbers)` keeps one copy of each number. The list still has all its items, but the set only has the different ones."
    else:
        names = rng.sample(PEOPLE, 3)
        items = names + [rng.choice(names)]
        rng.shuffle(items)
        code = f"names = {lit(items)}\nprint(len(set(names)))"
        wrong = ["4", "2", "1"]
        why = "`set(names)` removes the repeated name, so `len` counts only the different names."
    return output_question(topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong, explanation=why, rng=rng)


MEMBER_WORDS = [
    ("words", ["python", "java", "ruby", "swift"]),
    ("fruits", ["apple", "banana", "cherry", "date"]),
    ("colors", ["red", "green", "blue", "yellow"]),
    ("pets", ["cat", "dog", "fish", "bird"]),
]


@generator(TOPIC, MEDIUM)
def gen_membership_trace(rng: random.Random) -> Question:
    """Lab: sets are for 'uniqueness & membership tests (`in`)'.  Case matters!"""
    name, pool = rng.choice(MEMBER_WORDS)
    items = rng.sample(pool, 3)
    absent = [x for x in pool if x not in items][0]
    kind = rng.choice(["list", "set", "tuple"])
    src = {"list": lit(items), "tuple": lit(tuple(items)), "set": set_src(items)}[kind]
    tests = [
        (f"{lit(items[rng.randrange(3)])} in {name}", True),
        (f"{lit(items[rng.randrange(3)].capitalize())} in {name}", False),
        (f"{lit(absent)} in {name}", False),
    ]
    rng.shuffle(tests)
    code = f"{name} = {src}\n" + "\n".join(f"print({t})" for t, _ in tests)
    lines = [(str(r), [str(not r)]) for _, r in tests]
    return trace_question(
        MEDIUM, code, lines, rng,
        "`x in collection` is `True` when x is one of the items. Text must match exactly, so `\"Cat\"` is not `\"cat\"`.",
    )


SCENARIOS = [
    # (need, best type, why)
    ("a student's name, grade and GPA, each with a label", "dict", "it stores labeled fields, like a mini record."),
    ("a phone book that looks up a number by a person's name", "dict", "it finds a value from its key."),
    ("a game character's name, health and speed, each with a label", "dict", "each field has a label, like a mini record."),
    ("the names of players in the order they joined, with more joining later", "list", "order matters and the items will change."),
    ("a shopping cart where items are added over time", "list", "it keeps order and you can `append` new items."),
    ("the scores of a game, added after every round", "list", "the items keep their order and the collection keeps growing."),
    ("the (x, y) position of a point that will never change", "tuple", "order matters and the items won't change."),
    ("a date stored as (month, day, year) that should not be changed by mistake", "tuple", "it is the safer choice for fixed data."),
    ("an RGB color such as (255, 128, 0) with three fixed values", "tuple", "the values are in a fixed order and won't change."),
    ("the different colors used in a drawing, ignoring repeats", "set", "it keeps only one copy of each item."),
    ("a collection where uniqueness matters", "set", "it guarantees uniqueness."),
    ("student IDs where each ID may appear only once and you quickly check if one is there", "set", "it is unique and fast for `in` membership tests."),
]


@generator(TOPIC, MEDIUM)
def gen_when_to_use(rng: random.Random) -> Question:
    """Lab: 'When to Use Which?' -- list, tuple, set or dict."""
    need, best, why = rng.choice(SCENARIOS)
    others = [t for t in ("list", "tuple", "set", "dict") if t != best]
    rng.shuffle(others)
    return build_question(
        topic=TOPIC, difficulty=MEDIUM, prompt=f"Which data type is the best fit for {need}?",
        correct=best, distractors=others, explanation=f"A `{best}` fits because {why}",
        rng=rng,
    )


WHY_FAILS = [
    # (code template using {a}, {b}, ..., right reason, wrong reasons, explanation)
    (
        "point = ({a}, {b})\npoint.append({c})",
        "A tuple can't be changed, so it has no `append`",
        ["`append` only works on strings", "A tuple can only hold two items", "`append` needs two values inside the brackets"],
        "Tuples are unchangeable: you can't add to them. Use a list if the items must change.",
    ),
    (
        "colors = {colors}\nprint(colors[0])",
        "A set is unordered, so it has no index positions",
        ["Index numbers start at 1 in a set", "A set can only be printed with `type()`", "The items need single quotes"],
        "Sets are unordered, so there is no \"first\" item to ask for. Use `in` to test membership.",
    ),
    (
        'student = {student}\nprint(student["age"])',
        'There is no key "age" in the dictionary',
        ["Dictionary keys must be numbers", "`student` must be turned into a list first", "You must write `student.age`"],
        "A dictionary can only give you values for keys it actually has: `name`, `grade` and `gpa`.",
    ),
    (
        'word = "{word}"\nword[0] = "J"',
        "Strings are unchangeable, so one letter can't be replaced",
        ["Strings can only be changed with `append`", "`\"J\"` must be a number", "Index 0 does not exist"],
        "Strings are immutable. To get a different word you have to build a new string.",
    ),
    (
        "{name} = {items}\nprint({name}[{n}])",
        "There is no item at that index; the last index is {last}",
        ["Lists can't be printed with an index", "The items need single quotes", "`print` only works on the first item"],
        "Indexes start at 0, so a list with {n} items ends at index {last}.",
    ),
    (
        'age = input("Age: ")\nprint(age + 1)',
        "`input()` gives a str, and a str can't be added to an int",
        ["`input()` returns a float", "`print` can't add numbers", "`age` is None until you cast it"],
        "`input()` always returns text. Cast it first: `int(age) + 1`.",
    ),
    (
        'me = {me}\nme.append("PE")',
        "`append` is a list method, and `me` is a dictionary",
        ["`\"PE\"` is not a valid class", "`append` needs a number", "A dictionary can only be changed with `+=`"],
        'The classes are in a list inside the dictionary: `me["classes"].append("PE")`.',
    ),
]


@generator(TOPIC, MEDIUM)
def gen_why_fails(rng: random.Random) -> Question:
    """'Why does this code fail?' -- the classic data type mistakes, in plain words."""
    template, right, wrong, why = rng.choice(WHY_FAILS)
    runnable = "input(" not in template
    name, items = item_list(rng, 3)
    a, b, c = rng.choice([(10, 20, 30), (3, 4, 5), (5, 9, 12), (1, 2, 3)])
    d = student_dict(rng)
    me = me_dict(rng, 3)
    fields = dict(
        a=a, b=b, c=c, colors=set_src(rng.sample(COLOR_WORDS, 3)), student=lit(d),
        word=rng.choice(["Python", "banana", "coding"]), name=name, items=lit(items), n=3, last=2, me=lit(me),
    )
    code = template.format(**fields)
    if runnable and run_code(code).error is None:
        raise GenerationError("this snippet should fail but runs fine")
    return build_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Why does this code fail?", correct=right.format(**fields),
        distractors=wrong, explanation=why.format(**fields), rng=rng, code=code,
    )


TYPE_PROBES = [
    # (setup, expression, resulting type, the usual wrong guess)
    ('fruits = ["apple", "banana", "cherry"]', "fruits", "list", "tuple"),
    ('fruits = ["apple", "banana", "cherry"]', "fruits[0]", "str", "list"),
    ('fruits = ["apple", "banana", "cherry"]', "len(fruits)", "int", "str"),
    ("point = (10, 20)", "point", "tuple", "list"),
    ("point = (10, 20)", "point[0]", "int", "tuple"),
    ('colors = {"red", "green", "blue"}', "colors", "set", "dict"),
    ('colors = {"red", "green", "blue"}', "len(colors) > 2", "bool", "int"),
    ('student = {"name": "Sam", "grade": 11, "gpa": 3.6}', "student", "dict", "set"),
    ('student = {"name": "Sam", "grade": 11, "gpa": 3.6}', 'student["gpa"]', "float", "str"),
    ('student = {"name": "Sam", "grade": 11, "gpa": 3.6}', 'student["name"]', "str", "list"),
    ('student = {"name": "Sam", "grade": 11, "gpa": 3.6}', 'student["grade"]', "int", "str"),
    ("", "10 / 2", "float", "int"),
    ("", "7 // 2", "int", "float"),
    ("", '"5" * 2', "str", "int"),
    ("", "5 > 3", "bool", "int"),
    ("", "3 + 4.0", "float", "int"),
    ("", "str(42)", "str", "int"),
    ("", "2 + 3j", "complex", "float"),
    ("", "[1, 2, 3][0]", "int", "list"),
]


@generator(TOPIC, MEDIUM)
def gen_type_of_expression(rng: random.Random) -> Question:
    """`type()` of a value you have to work out first: an item, a len(), a division, a comparison."""
    setup, expr, t, usual = rng.choice(TYPE_PROBES)
    # vary the lesson data a little so the same probe doesn't repeat verbatim
    if "Sam" in setup:
        d = student_dict(rng)
        setup = f"student = {lit(d)}"
    if setup.startswith("fruits"):
        setup = f"fruits = {lit(rng.sample(FRUITS, 3))}"
    if setup.startswith("point"):
        setup = f"point = {lit(rng.choice([(10, 20), (3, 4), (5, 9)]))}"
    if setup.startswith("colors"):
        setup = f"colors = {set_src(rng.sample(COLOR_WORDS, 3))}"
    code = (setup + "\n" if setup else "") + f"print(type({expr}))"
    wrong = [cls(usual)] + [cls(c) for c in CONFUSE[t] if c != usual]
    return output_question(
        topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong, rng=rng,
        prompt="What does this code print?",
        explanation=f"`{expr}` produces a `{t}`, so `type` shows `{cls(t)}`. Work out the value first, then ask for its type.",
    )


@generator(TOPIC, MEDIUM)
def gen_me_trace(rng: random.Random) -> Question:
    """Mini-Challenge 'Classes Dictionary': the `me` dict with a list inside."""
    me = me_dict(rng, rng.choice([4, 5]))
    classes = me["classes"]
    k = len(classes)
    templates = [
        ("print(len(me))", "3", [str(k), "2"]),
        ('print(len(me["classes"]))', str(k), ["3", str(k - 1)]),
        ('print(me["classes"][1])', classes[1], [classes[0], classes[2]]),
        ('print(me["classes"][-1])', classes[-1], [classes[0], classes[-2]]),
        ('print(me["name"])', me["name"], ["name", str(me["grade"])]),
        ('print(len(me["name"]))', str(len(me["name"])), [str(len(me["name"]) + 1), "1"]),
    ]
    chosen = rng.sample(templates, 3)
    code = f"me = {lit(me)}\n" + "\n".join(c for c, _, _ in chosen)
    return trace_question(
        MEDIUM, code, [(r, w) for _, r, w in chosen], rng,
        'The dictionary has 3 keys, so `len(me)` is 3. `me["classes"]` is a list, so you can index it or count it with `len`.',
    )


@generator(TOPIC, MEDIUM)
def gen_me_expression(rng: random.Random) -> Question:
    """Mini-Challenge: 'The second class from the list.'"""
    me = me_dict(rng, rng.choice([3, 4, 5]))
    classes = me["classes"]
    mode = rng.choice(["second", "first", "last", "count"])
    if mode == "second":
        prompt, correct, target = "Which expression gets the second class?", 'me["classes"][1]', classes[1]
        wrong = ['me["classes"][2]', "me[1]", 'me["classes[1]"]', "me.classes[1]", 'me[1]["classes"]']
        why = '`me["classes"]` is the list, and index `1` is its second item (indexes start at 0).'
    elif mode == "first":
        prompt, correct, target = "Which expression gets the first class?", 'me["classes"][0]', classes[0]
        wrong = ['me["classes"][1]', "me[0]", 'me["classes[0]"]', "me.classes[0]", 'me[0]["classes"]']
        why = '`me["classes"]` is the list, and index `0` is its first item.'
    elif mode == "last":
        prompt, correct, target = "Which expression gets the last class?", 'me["classes"][-1]', classes[-1]
        wrong = [f'me["classes"][{len(classes)}]', 'me["classes"][0]', "me[-1]", "me.classes[-1]", 'me[-1]["classes"]']
        why = f'`me["classes"][-1]` counts from the end. `me["classes"][{len(classes)}]` is past the end of the list.'
    else:
        prompt, correct, target = "Which expression gives the number of classes?", 'len(me["classes"])', len(classes)
        wrong = ["len(me)", 'me["classes"]', "len(classes)", 'len(me["name"])', 'me["classes"].len()']
        why = '`me["classes"]` is the list of classes, and `len` counts its items. `len(me)` would count the dictionary\'s keys.'
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC, difficulty=MEDIUM, prompt=prompt, setup=f"me = {lit(me)}", target=target,
        correct_expr=correct, wrong_exprs=wrong, explanation=why, rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_me_add_class(rng: random.Random) -> Question:
    """Which statement adds a class to the list inside `me`?"""
    me = me_dict(rng, 3)
    new = rng.choice([s for s in SUBJECTS if s not in me["classes"]])
    wrong = [
        f'me.append({lit(new)})',
        f'me["classes"].add({lit(new)})',
        f'me["classes"] = {lit(new)}',
        f'append(me["classes"], {lit(new)})',
        f'me["classes"].push({lit(new)})',
    ]
    rng.shuffle(wrong)
    return which_expression_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Which statement adds {lit(new)} to the end of the classes list inside `me`?",
        setup=f"me = {lit(me)}", target=None, correct_expr=f'me["classes"].append({lit(new)})', wrong_exprs=wrong,
        explanation='The classes are a list stored under the key `"classes"`, so get the list first and then call `append` on it. `me.append(...)` fails because `me` is a dictionary.',
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_me_fstring(rng: random.Random) -> Question:
    """Mini-Challenge: the f-string '{name} is in grade {grade} and is taking {N} classes.'"""
    me = me_dict(rng, rng.choice([4, 5, 2]))
    k = len(me["classes"])
    code = (
        f"me = {lit(me)}\n"
        'name = me["name"]\n'
        'grade = me["grade"]\n'
        'n = len(me["classes"])\n'
        'print(f"{name} is in grade {grade} and is taking {n} classes.")'
    )
    right = f"{me['name']} is in grade {me['grade']} and is taking {k} classes."
    wrong = [
        f"{me['name']} is in grade {me['grade']} and is taking 3 classes.",
        f"{me['name']} is in grade {k} and is taking {me['grade']} classes.",
        f"{me['grade']} is in grade {me['name']} and is taking {k} classes.",
        f"name is in grade grade and is taking n classes.",
    ]
    return output_question(
        topic=TOPIC, difficulty=MEDIUM, code=code, distractors=wrong,
        explanation='An f-string fills each `{...}` with the variable\'s value. `n` is `len(me["classes"])`, the number of items in the list, not the number of keys.',
        rng=rng,
    )


# -- "which line causes / avoids an error" ----------------------------------------------------

def _line_world(rng: random.Random):
    """Setup code with fruits / point / colors / student / word, plus the lines to try against it."""
    name_items = rng.sample(FRUITS, 3)
    point = rng.choice([(10, 20), (3, 4), (5, 9)])
    colors = rng.sample(COLOR_WORDS, 3)
    d = {"name": rng.choice(PEOPLE), "grade": rng.choice([9, 10, 11, 12])}
    word = rng.choice(["Python", "banana", "coding"])
    setup = (
        f"fruits = {lit(name_items)}\n"
        f"point = {lit(point)}\n"
        f"colors = {set_src(colors)}\n"
        f"student = {lit(d)}\n"
        f"word = {lit(word)}"
    )
    errors = [
        ("point[0] = 5", "A tuple can't be changed."),
        ("point.append(30)", "A tuple has no `append` because it can't be changed."),
        ("colors[0]", "A set is unordered, so it has no index positions."),
        ('student["age"]', 'The dictionary has no key "age".'),
        ("fruits[3]", "The list has 3 items, so the last index is 2."),
        ('word[0] = "J"', "A string can't be changed."),
    ]
    new_fruit = rng.choice([f for f in FRUITS if f not in name_items])
    fine = [
        (f'fruits[0] = {lit(new_fruit)}', "A list can be changed."),
        (f'fruits.append({lit(new_fruit)})', "A list can be changed."),
        ("print(fruits[2])", "Index 2 is the third item."),
        ("print(point[1])", "A tuple can be indexed; it just can't be changed."),
        ("print(len(colors))", "`len` works on a set."),
        (f'print({lit(colors[0])} in colors)', "`in` works on a set."),
        ('print(student["name"])', "The key exists."),
        ("print(type(point))", "`type` works on anything."),
        ("print(word[0])", "Reading a character is fine; only changing one fails."),
        ("print(len(student))", "`len` counts the keys."),
    ]
    return setup, errors, fine


def _runs_ok(setup: str, line: str) -> bool:
    return run_code(setup + "\n" + line).error is None


@generator(TOPIC, MEDIUM)
def gen_which_line_errors(rng: random.Random) -> Question:
    """'Which line causes an error?' -- one bad line among three that work."""
    setup, errors, fine = _line_world(rng)
    bad, bad_why = rng.choice(errors)
    good = rng.sample(fine, 3)
    if _runs_ok(setup, bad) or not all(_runs_ok(setup, g) for g, _ in good):
        raise GenerationError("line world mismatch")
    return build_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Which line causes an error?", correct=bad,
        distractors=[g for g, _ in good], explanation=bad_why, rng=rng, code=setup,
    )


# ==========================================================================
# HARD -- multiple choice (a twist or two steps to trace; needs care, never obscure)
# ==========================================================================


@generator(TOPIC, HARD)
def gen_alias_two_step(rng: random.Random) -> Question:
    """Common Gotcha: 'Lists are mutable: changing one place changes all references to that same list.'"""
    form = rng.choice(["both_append", "rebind", "index_pair"])
    a, b = rng.choice(ALIAS_PAIRS)
    if form == "both_append":
        items = rng.sample([60, 70, 75, 80, 85, 90, 95], 2)
        x, y = rng.sample([100, 55, 65, 40], 2)
        code = f"{a} = {lit(items)}\n{b} = {a}\n{b}.append({x})\n{a}.append({y})\nprint(len({a}), len({b}))"
        wrong = ["3 4", "3 3", "4 3", "2 3"]
        why = f"`{b} = {a}` means both names refer to one list, so the two `append` calls add to the same list. Both names see all 4 items."
    elif form == "rebind":
        items = rng.sample([1, 2, 3, 4, 5, 6], 3)
        new = rng.sample([7, 8, 9], 2)
        code = f"{a} = {lit(items)}\n{b} = {a}\n{a} = {lit(new)}\nprint({b})"
        wrong = [repr(new), repr(items + new), repr([new[0]] + items[1:])]
        why = f"`{a} = {lit(new)}` points `{a}` at a brand-new list. `{b}` still refers to the original list, so it is unchanged."
    else:
        items = rng.sample(PEOPLE, 3)
        new = rng.choice([p for p in PEOPLE if p not in items])
        code = f"{a} = {lit(items)}\n{b} = {a}\n{b}[0] = {lit(new)}\nprint({a}[0], {b}[0])"
        wrong = [f"{items[0]} {new}", f"{new} {items[0]}", f"{items[0]} {items[0]}", f"{new} {items[1]}"]
        why = f"Both names refer to the same list, so changing item 0 through `{b}` also changes it when you look through `{a}`."
    return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, explanation=why, rng=rng)


@generator(TOPIC, HARD)
def gen_me_mutate_trace(rng: random.Random) -> Question:
    """Mini-Challenge dictionary, twist: append to the list inside `me`, then look again."""
    me = me_dict(rng, rng.choice([2, 3]))
    new = rng.choice([s for s in SUBJECTS if s not in me["classes"]])
    old_n = len(me["classes"])
    after = me["classes"] + [new]
    code = (
        f"me = {lit(me)}\n"
        f'me["classes"].append({lit(new)})\n'
        'print(len(me["classes"]))\n'
        'print(me["classes"][-1])\n'
        "print(len(me))"
    )
    lines = [
        (str(old_n + 1), [str(old_n), str(old_n + 2)]),
        (new, [me["classes"][-1], me["classes"][0]]),
        ("3", [str(old_n + 1), "4"]),
    ]
    return trace_question(
        HARD, code, lines, rng,
        'The list inside `me` grows by one, but `me` itself still has just 3 keys: `"name"`, `"grade"` and `"classes"`.',
        first=["\n".join([str(old_n), me["classes"][-1], "3"])],
    )


COUNT_VALUES = [
    [5, "5", 5.0, "five", True],
    [7, "7", 7.5, "seven", False],
    [3, 3.0, "3", True, "three"],
    [1, True, 1.0, "1"],
    [42, "42", 4.2, "forty-two", None],
    ["a", "b", 1, 2, 3.5],
    [10, 20, "30", 40.0, True, "50"],
    [False, True, 0, 1, "0"],
]


@generator(TOPIC, HARD)
def gen_count_by_type(rng: random.Random) -> Question:
    """Loop over mixed values and count one type with `type(value) == ...` (True is a bool, not an int)."""
    values = list(rng.choice(COUNT_VALUES))
    rng.shuffle(values)
    present = [t for t in ("str", "int", "float", "bool") if any(type(v).__name__ == t for v in values)]
    target = rng.choice(present)
    code = (
        f"values = {lit(values)}\n"
        "count = 0\n"
        "for value in values:\n"
        f"    if type(value) == {target}:\n"
        "        count += 1\n"
        "print(count)"
    )
    count = sum(1 for v in values if type(v).__name__ == target)
    if count == 0:
        raise GenerationError("no values of the target type")
    bool_as_int = sum(1 for v in values if isinstance(v, int))
    numbers = sum(1 for v in values if isinstance(v, (int, float)))
    wrong = [count + 1, bool_as_int, numbers, count - 1, len(values), count + 2]
    why = f"The loop counts only the values whose type is `{target}`: {count}. Remember `True` and `False` are `bool`, not `int`, and `\"5\"` in quotes is a `str`."
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=[str(w) for w in wrong if w >= 0], explanation=why, rng=rng
    )


UNIQUE_WORDS = ["banana", "apple", "letter", "success", "Mississippi", "balloon", "pepper", "coffee", "little", "tomorrow", "Python", "book"]


@generator(TOPIC, HARD)
def gen_unique_letters(rng: random.Random) -> Question:
    """Python Bingo: 'Create a set of unique letters from a word' -- compare len(word) and len(set(word))."""
    word = rng.choice(UNIQUE_WORDS)
    n, u = len(word), len(set(word))
    form = rng.choice(["both", "both", "unique_only"])
    if form == "both":
        code = f"word = {lit(word)}\nletters = set(word)\nprint(len(word), len(letters))"
        correct = f"{n} {u}"
        wrong = [f"{n} {n}", f"{u} {n}", f"{u} {u}", f"{n} {u + 1}", f"{n - 1} {u}", f"{n} {u - 1}", f"{n + 1} {u}"]
    else:
        code = f"word = {lit(word)}\nletters = set(word)\nprint(len(letters))"
        correct = str(u)
        wrong = [str(n), str(u + 1), str(u - 1), str(n - 1), str(u + 2), str(n + 1)]
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, rng=rng,
        explanation=f"`set(word)` keeps one copy of each different letter, so it has {u} items. The word itself still has {n} characters.",
    )


@generator(TOPIC, HARD)
def gen_dict_variable_key(rng: random.Random) -> Question:
    """Twist: a key stored in a variable (no quotes) vs the word "key" in quotes."""
    d = student_dict(rng)
    key = rng.choice(["grade", "gpa", "name"])
    var = rng.choice(["key", "field", "label"])
    if rng.random() < 0.5:
        # the variable holds the key: use it WITHOUT quotes
        expr = f"student[{var}]"
        if key == "name":
            code = f'student = {lit(d)}\n{var} = "{key}"\nprint({expr})'
            wrong = [var, key, "Error: KeyError"]
        else:
            code = f'student = {lit(d)}\n{var} = "{key}"\nprint({expr} + 1)'
            wrong = [var, str(d[key]), "Error: KeyError", f"{d[key]}1"]
        why = f'`{var}` holds the text `"{key}"`, so `student[{var}]` is the same as `student["{key}"]`.'
    else:
        # quotes around the variable name make it a (missing) key
        code = f'student = {lit(d)}\n{var} = "{key}"\nprint(student["{var}"])'
        wrong = [str(d[key]), key, var, "None"]
        wrong = [w for w in wrong]
        why = f'With quotes, `"{var}"` is just the text `{var}`. The dictionary has no key named `{var}`, so this is an error.'
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, explanation=why, rng=rng,
        prompt="What happens when this code runs?", allow_error=True,
    )


@generator(TOPIC, HARD)
def gen_append_returns_none(rng: random.Random) -> Question:
    """Twist: `append` changes the list but gives back None (the lab's 'no value')."""
    name, items = item_list(rng, 2)
    new = rng.choice([x for x in ITEM_POOLS[name] if x not in items])
    code = f"{name} = {lit(items)}\nresult = {name}.append({lit(new)})\nprint(result)\nprint({name})"
    after = items + [new]
    lines = [
        ("None", [repr(after), repr(items)]),
        (repr(after), [repr(items), repr([new] + items)]),
    ]
    return trace_question(
        HARD, code, lines, rng,
        f"`append` changes the list in place and returns `None` (no value). So `result` is `None`, while `{name}` now has the new item.",
    )


@generator(TOPIC, HARD)
def gen_which_line_works(rng: random.Random) -> Question:
    """'Which line runs without an error?' -- three look-alike mistakes and one line that works."""
    setup, errors, fine = _line_world(rng)
    tricky = [f for f in fine if f[0].startswith(("fruits[0] =", "fruits.append", "print(point[1])", "print(word[0])", "print(len(colors))"))]
    ok, ok_why = rng.choice(tricky)
    bad = rng.sample(errors, 3)
    if not _runs_ok(setup, ok) or any(_runs_ok(setup, b) for b, _ in bad):
        raise GenerationError("line world mismatch")
    return build_question(
        topic=TOPIC, difficulty=HARD, prompt="Which line runs without an error?", correct=ok,
        distractors=[b for b, _ in bad], explanation=f"{ok_why} The others fail: tuples, sets and strings can't be changed like that, and a dict needs a key it actually has.",
        rng=rng, code=setup,
    )


@generator(TOPIC, HARD)
def gen_nested_lookup(rng: random.Random) -> Question:
    """A dictionary whose values are lists: two lookups in a row."""
    names = rng.sample(["Ava", "Ben", "Cara", "Dev", "Eli"], 2)
    s1 = rng.sample([60, 65, 70, 75, 80, 85, 90, 95], 3)
    s2 = rng.sample([62, 68, 72, 78, 82, 88, 92, 98], 3)
    d = {names[0]: s1, names[1]: s2}
    who = rng.choice(names)
    other = names[1] if who == names[0] else names[0]
    mine, theirs = d[who], d[other]
    mode = rng.choice(["index", "index", "last", "len", "sum"])
    if mode == "index":
        i = rng.choice([0, 1, 2])
        expr, ans = f'scores["{who}"][{i}]', mine[i]
        wrong = [mine[(i + 1) % 3], theirs[i], mine[(i + 2) % 3], repr(mine)]
        why = f'`scores["{who}"]` is the list `{mine}`; index `{i}` picks one item from it.'
    elif mode == "last":
        expr, ans = f'scores["{who}"][-1]', mine[-1]
        wrong = [mine[0], theirs[-1], mine[1], repr(mine)]
        why = f'`scores["{who}"][-1]` is the last item of {who}\'s list.'
    elif mode == "len":
        expr, ans = f'len(scores["{who}"])', 3
        wrong = ["2", "4", "6"]
        why = f'`scores["{who}"]` is a list of 3 scores, and `len` counts them. (`len(scores)` would count the 2 names.)'
    else:
        expr, ans = f'scores["{who}"][0] + scores["{other}"][0]', mine[0] + theirs[0]
        wrong = [mine[0] + mine[1], theirs[0] + theirs[1], mine[0], f"{mine[0]}{theirs[0]}"]
        why = f"Each lookup gives a number, then `+` adds them."
    code = f"scores = {lit(d)}\nprint({expr})"
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=[str(w) for w in wrong], explanation=why, rng=rng
    )


@generator(TOPIC, HARD)
def gen_dedupe_loop_trace(rng: random.Random) -> Question:
    """Trace a loop that builds a list of different items with `not in` and `append`."""
    pool = rng.sample(COLOR_WORDS, 3)
    words = pool + rng.choices(pool, k=rng.choice([2, 3]))
    rng.shuffle(words)
    unique = []
    for w in words:
        if w not in unique:
            unique.append(w)
    code = (
        f"words = {lit(words)}\n"
        "unique = []\n"
        "for word in words:\n"
        "    if word not in unique:\n"
        "        unique.append(word)\n"
        "print(unique)\n"
        "print(len(unique))"
    )
    lines = [
        (repr(unique), [repr(words), repr(sorted(unique)) if sorted(unique) != unique else repr(unique[::-1])]),
        (str(len(unique)), [str(len(words)), str(len(unique) + 1)]),
    ]
    return trace_question(
        HARD, code, lines, rng,
        "A word is only appended if it isn't already in `unique`, so each different word is added once, in the order it first appears.",
        first=["\n".join([repr(words), str(len(words))])],
    )


TYPE_LOOP_VALUES = [
    ("7", "int"), ("7.0", "float"), ('"7"', "str"), ("True", "bool"), ("None", "NoneType"),
    ("[7]", "list"), ("(7, 8)", "tuple"), ('{"n": 7}', "dict"),
]


@generator(TOPIC, HARD)
def gen_types_loop_trace(rng: random.Random) -> Question:
    """A for loop printing type(item) for look-alike values (7, 7.0, "7", True)."""
    picks = rng.sample(TYPE_LOOP_VALUES, 4)
    if not any(t == "bool" for _, t in picks) and rng.random() < 0.6:
        picks[rng.randrange(4)] = ("True", "bool")
    srcs = [s for s, _ in picks]
    code = f"items = [{', '.join(srcs)}]\nfor item in items:\n    print(type(item))"
    lines = [(cls(t), [cls(CONFUSE[t][0]), cls(CONFUSE[t][1])]) for _, t in picks]
    return trace_question(
        HARD, code, lines, rng,
        "The loop prints one `type` per item: `7` is an `int`, `7.0` a `float`, `\"7\"` a `str`, and `True` a `bool` (not an `int`).",
        prompt="What does this code print?",
    )


# ==========================================================================
# BLANKS -- fill in the blanks of lab code (typed)
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_type_call(rng: random.Random) -> Question:
    """The lab's `print(an_int, type(an_int))`: fill in the function that shows the type."""
    t, var, src = rng.choice([s for s in SCALAR_SPECS if s[0] in ("int", "float", "str", "bool")])
    code = f"{var} = {src}\nprint({var}, {blank_mark(1)}({var}))"
    shown = out_text(f"{var} = {src}\nprint({var}, type({var}))")
    return blanks_question(
        topic=TOPIC, difficulty=EASY,
        prompt="Fill in the blank so the code prints the value and then its type.",
        template=code, blanks=[Blank(["type"], hint="function")],
        explanation=f"`type({var})` returns the data type of the value, so the line prints `{shown}`.",
        expect_output=shown,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_type_names(rng: random.Random) -> Question:
    """Fill in the type name that `type()` reports for each variable (like the lab's printed types)."""
    pool = [s for s in SCALAR_SPECS if s[0] in ("int", "float", "bool", "NoneType", "str", "complex")]
    picks = []
    seen = set()
    for spec in rng.sample(pool, len(pool)):
        if spec[0] not in seen:
            seen.add(spec[0])
            picks.append(spec)
        if len(picks) == 3:
            break
    assigns = "\n".join(f"{v} = {s}" for _, v, s in picks)
    prints = "\n".join(
        f"print(type({v}))   # <class '{blank_mark(i + 1)}'>" for i, (_, v, _) in enumerate(picks)
    )
    expect = "\n".join(cls(t) for t, _, _ in picks)
    return blanks_question(
        topic=TOPIC, difficulty=EASY,
        prompt="Fill in the type name that each `print(type(...))` shows.",
        template=f"{assigns}\n{prints}",
        blanks=[Blank([t], hint="type name") for t, _, _ in picks],
        explanation="Whole numbers are `int`, numbers with a decimal point are `float`, quotes make a `str`, `True`/`False` are `bool`, `2 + 3j` is `complex`, and `None` has the type `NoneType`.",
        expect_output=expect,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_list_append(rng: random.Random) -> Question:
    """The lab's list lines: `fruits.append("date")` and `fruits[0]`."""
    name, items = item_list(rng, 3)
    new = rng.choice([x for x in ITEM_POOLS[name] if x not in items])
    single = name[:-1]
    after = items + [new]
    if rng.random() < 0.5:
        word, idx_accept, idx = "first", ["0"], 0
    else:
        word, idx_accept, idx = "last", ["-1", str(len(after) - 1)], -1
    template = (
        f"{name} = {lit(items)}\n"
        f"{name}.{blank_mark(1)}({lit(new)})\n"
        f"print({name})\n"
        f'print("{word} {single}:", {name}[{blank_mark(2)}])'
    )
    return blanks_question(
        topic=TOPIC, difficulty=EASY,
        prompt=f"Fill in the blanks so the code adds {lit(new)} to the list and prints the {word} {single}.",
        template=template,
        blanks=[Blank(["append"], hint="list method"), Blank(idx_accept, hint="index", mode="expr")],
        explanation=f"`append` adds an item to the end of the list. Index `0` is the first item and `-1` is the last one.",
        expect_output=f"{after!r}\n{word} {single}: {after[idx]}",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_dict_keys(rng: random.Random) -> Question:
    """The lab's `print("student name:", student["name"])`: the key goes in quotes inside [ ]."""
    d = student_dict(rng)
    k1, k2 = rng.sample(["name", "grade", "gpa"], 2)
    template = f"student = {lit(d)}\nprint(\"first:\", student[{blank_mark(1)}])\nprint(\"second:\", student[{blank_mark(2)}])"
    expect = f"first: {d[k1]}\nsecond: {d[k2]}"
    return blanks_question(
        topic=TOPIC, difficulty=EASY,
        prompt=f'Fill in the keys so the code prints the student\'s {k1} and then the student\'s {k2}.',
        template=template,
        blanks=[Blank([f'"{k1}"'], hint="key", mode="expr"), Blank([f'"{k2}"'], hint="key", mode="expr")],
        explanation='Put the key in quotes inside square brackets, like `student["name"]`. Without quotes Python would look for a variable.',
        expect_output=expect,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_string_lab(rng: random.Random) -> Question:
    """Canvas-style 'fill in multiple blanks' for the lab's String block (len, upper, slice)."""
    title = rng.choice(TITLES)
    k = rng.choice([3, 4, 5, 6])
    template = (
        f"title = {lit(title)}\n"
        f'print("Length:", {blank_mark(1)}(title))\n'
        f'print("Upper:", title.{blank_mark(2)}())\n'
        f'print("Slice [0:{k}]:", title[0:{blank_mark(3)}])'
    )
    expect = f"Length: {len(title)}\nUpper: {title.upper()}\nSlice [0:{k}]: {title[:k]}"
    return blanks_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt="Fill in the blanks to finish the lab's String section.",
        template=template,
        blanks=[Blank(["len"], hint="function"), Blank(["upper"], hint="method"), Blank([str(k)], hint="number", mode="expr")],
        explanation=f"`len(title)` counts the characters, `title.upper()` makes capitals, and `title[0:{k}]` takes the first {k} characters.",
        expect_output=expect,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_me_lookup(rng: random.Random) -> Question:
    """Mini-Challenge 'Classes Dictionary': get the name, then a class out of the list."""
    me = me_dict(rng, rng.choice([3, 4]))
    k = len(me["classes"])
    which = rng.choice(["second", "first", "last"])
    idx_accept, pos = {"second": (["1"], 1), "first": (["0"], 0), "last": (["-1", str(k - 1)], -1)}[which]
    template = (
        f"me = {lit(me)}\n"
        f"print(me[{blank_mark(1)}])\n"
        f'print(me["classes"][{blank_mark(2)}])'
    )
    return blanks_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Fill in the blanks to print the name, then the {which} class.",
        template=template,
        blanks=[Blank(['"name"'], hint="key", mode="expr"), Blank(idx_accept, hint="index", mode="expr")],
        explanation='`me["name"]` looks up the name by its key. `me["classes"]` is a list, so a number in brackets picks one class: indexes start at 0 and `-1` is the last.',
        expect_output=f"{me['name']}\n{me['classes'][pos]}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_set_unique(rng: random.Random) -> Question:
    """Sets keep one copy of each item: `set(...)` and `len(...)`."""
    if rng.random() < 0.5:
        pool = rng.sample([1, 2, 3, 4, 5, 6], 3)
        data = pool + rng.choices(pool, k=3)
        rng.shuffle(data)
        var, label = "numbers", "numbers"
    else:
        pool = rng.sample(COLOR_WORDS, 3)
        data = pool + rng.choices(pool, k=3)
        rng.shuffle(data)
        var, label = "colors", "colors"
    template = (
        f"{var} = {lit(data)}\n"
        f"unique = {blank_mark(1)}({var})\n"
        f"print({blank_mark(2)}({var}), len(unique))"
    )
    return blanks_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the code prints how many {label} there are, then how many different ones.",
        template=template,
        blanks=[Blank(["set"], hint="function"), Blank(["len"], hint="function")],
        explanation="`set(...)` keeps one copy of each different item, and `len(...)` counts items.",
        expect_output=f"{len(data)} {len(set(data))}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_in_operator(rng: random.Random) -> Question:
    """Sets are for membership tests: `in` and `not in`."""
    colors = rng.sample(COLOR_WORDS, 3)
    absent = rng.choice([c for c in COLOR_WORDS if c not in colors])
    present = rng.choice(colors)
    template = (
        f"colors = {set_src(colors)}\n"
        f"print({lit(present)} {blank_mark(1)} colors)\n"
        f"print({lit(absent)} {blank_mark(2)} colors)"
    )
    return blanks_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt="Fill in the operators so the code prints `True` on both lines.",
        template=template,
        blanks=[Blank(["in"], hint="operator"), Blank(["not in"], hint="operator")],
        explanation=f"{lit(present)} is in the set, so `in` gives `True`. {lit(absent)} is not in the set, so `not in` gives `True` too.",
        expect_output="True\nTrue",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_me_fstring(rng: random.Random) -> Question:
    """Mini-Challenge: '{name} is in grade {grade} and is taking {N} classes.'"""
    me = me_dict(rng, rng.choice([2, 4, 5]))
    template = (
        f"me = {lit(me)}\n"
        f"name = me[{blank_mark(1)}]\n"
        f"grade = me[{blank_mark(2)}]\n"
        f'n = {blank_mark(3)}(me["classes"])\n'
        'print(f"{name} is in grade {grade} and is taking {n} classes.")'
    )
    return blanks_question(
        topic=TOPIC, difficulty=HARD,
        prompt="Fill in the blanks to finish the Classes Dictionary mini-challenge.",
        template=template,
        blanks=[
            Blank(['"name"'], hint="key", mode="expr"),
            Blank(['"grade"'], hint="key", mode="expr"),
            Blank(["len"], hint="function"),
        ],
        explanation='Look up the name and grade by their keys, and count the classes with `len(me["classes"])`. The f-string then fills in each `{...}`.',
        expect_output=f"{me['name']} is in grade {me['grade']} and is taking {len(me['classes'])} classes.",
    )


# ==========================================================================
# MATCH -- click to match (like the Canvas matching questions)
# ==========================================================================

MATCH_LITERALS = {
    "integer": ["42", "-7", "100", "2024"],
    "float": ["3.14159", "9.81", "0.5", "2.0"],
    "string": ['"Intro to Python"', '"42"', '"Sam"', '"True"'],
    "boolean": ["True", "False"],
    "list": ['["apple", "banana"]', "[1, 2, 3]", '["red", "blue"]'],
    "tuple": ["(10, 20)", '("red", "green")', "(3, 4)"],
    "set": ['{"red", "green", "blue"}', "{1, 2, 3}", '{"cat", "dog"}'],
    "dictionary": ['{"name": "Sam", "grade": 11}', '{"x": 10, "y": 20}', '{"cat": 2}'],
    "complex": ["2 + 3j", "4 - 1j"],
    "NoneType": ["None"],
}


@generator(TOPIC, EASY, qtype="match")
def gen_match_literal_type(rng: random.Random) -> Question:
    """Canvas: 'Match each literal to its Python type.'"""
    kinds = rng.sample(list(MATCH_LITERALS), 5)
    pairs = [(rng.choice(MATCH_LITERALS[k]), k) for k in kinds]
    extra = rng.choice([k for k in MATCH_LITERALS if k not in kinds])
    return match_question(
        topic=TOPIC, difficulty=EASY, prompt="Match each literal to its Python type.",
        pairs=pairs, extra_options=[extra], rng=rng,
        explanation="Quotes make a string, brackets make a list, parentheses a tuple, and braces a set (single items) or a dictionary (`key: value` pairs). A `j` makes a complex number.",
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_type_output(rng: random.Random) -> Question:
    """Match `type(...)` calls to what they print: `<class 'int'>` and friends."""
    kinds = rng.sample([k for k in MATCH_LITERALS if k != "complex"], 5)
    names = {"integer": "int", "float": "float", "string": "str", "boolean": "bool", "list": "list", "tuple": "tuple",
             "set": "set", "dictionary": "dict", "NoneType": "NoneType"}
    pairs = [(f"type({rng.choice(MATCH_LITERALS[k])})", cls(names[k])) for k in kinds]
    rest = [cls(v) for k, v in names.items() if k not in kinds]
    return match_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Match each `type(...)` call to what it shows.",
        pairs=pairs, extra_options=[rng.choice(rest)], rng=rng,
        explanation="`type(value)` reports the class of the value: `int`, `float`, `str`, `bool`, `list`, `tuple`, `set`, `dict` or `NoneType`.",
    )


WHEN_TO_USE = {
    "list": ["order matters and items will change", "an ordered collection you can add to with append"],
    "tuple": ["order matters and items won't change", "a fixed pair like a point (10, 20)"],
    "set": ["uniqueness and fast membership tests (in)", "a collection with no repeated items"],
    "dict": ["labeled fields, like a mini record", "values you look up by a key"],
    "str": ["a name or a sentence of text", "text such as \"Intro to Python\""],
    "bool": ["a yes/no answer: True or False", "the result of a comparison"],
}


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_when_to_use(rng: random.Random) -> Question:
    """Lab: 'When to Use Which?'"""
    core = ["list", "tuple", "set", "dict"]
    kinds = list(core)
    if rng.random() < 0.5:
        kinds.append(rng.choice(["str", "bool"]))
    pairs = [(rng.choice(WHEN_TO_USE[k]), k) for k in kinds]
    extras = [k for k in ("str", "bool") if k not in kinds][:1]
    return match_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Match each need to the data type that fits best.",
        pairs=pairs, extra_options=extras, rng=rng,
        explanation="list: order matters and items change. tuple: order matters and items won't change. set: uniqueness and fast `in` checks. dict: labeled fields.",
    )


def _context_world(rng: random.Random):
    name, items = item_list(rng, 3)
    colors = rng.sample(COLOR_WORDS, 3)
    point = rng.choice([(10, 20), (3, 4), (5, 9)])
    d = student_dict(rng)
    setup = f"{name} = {lit(items)}\ncolors = {set_src(colors)}\npoint = {lit(point)}\nstudent = {lit(d)}"
    exprs = [
        f"len({name})", f"{name}[0]", f"{name}[-1]", "len(colors)", "point[1]", 'student["name"]',
        'student["grade"]', "len(student)", "type(point)", f"{lit(colors[0])} in colors", f"{lit(items[0])} in {name}", "point[0]",
    ]
    return setup, exprs, name, items, colors, point, d


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_expression_result(rng: random.Random) -> Question:
    """Match each expression to its result (values from the lab's list / tuple / set / dict)."""
    setup, exprs, name, items, colors, point, d = _context_world(rng)
    # prefer expressions with different results
    rng.shuffle(exprs)
    chosen, seen = [], set()
    for e in exprs:
        val = as_choice(eval_expr(e, setup))
        if val in seen and rng.random() < 0.8:
            continue
        seen.add(val)
        chosen.append((e, val))
        if len(chosen) == 5:
            break
    if len(chosen) < 4:
        raise GenerationError("not enough distinct expressions")
    extra = [as_choice(items[1]), as_choice(d["grade"] + 1), "Error"]
    extra = [x for x in extra if x not in seen][:1]
    return match_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Match each expression to its result.",
        pairs=chosen, extra_options=extra, rng=rng, code=setup,
        explanation="Indexes start at 0 and `-1` is the last item. `len` counts items (a dict's keys; a set's different items). A dictionary is read by key, and a tuple by index.",
    )


ROLE_PAIRS = [
    ("type(x)", "Tells you the data type of x"),
    ("len(x)", "Counts the items (or characters) in x"),
    ("fruits.append(x)", "Adds x to the end of the list"),
    ("x in colors", "Checks if x is in the set: True or False"),
    ('student["name"]', "Looks up the value stored under a key"),
    ("fruits[0]", "Gets the first item of the list"),
    ("fruits[-1]", "Gets the last item of the list"),
    ("set(numbers)", "Keeps one copy of each different value"),
]


@generator(TOPIC, EASY, qtype="match")
def gen_match_function_role(rng: random.Random) -> Question:
    """Match each function / method / operator from the lab to what it does."""
    pairs = rng.sample(ROLE_PAIRS, 5)
    return match_question(
        topic=TOPIC, difficulty=EASY, prompt="Match each piece of code to what it does.",
        pairs=pairs, rng=rng,
        explanation="`type` shows the data type, `len` counts items, `append` adds to the end of a list, `in` tests membership, `[key]` looks up a dict value, and `[0]` / `[-1]` pick the first / last item.",
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_line_outcome(rng: random.Random) -> Question:
    """Which of these lines work and which cause an error?  (changeable vs unchangeable types)"""
    setup, errors, fine = _line_world(rng)
    bad = rng.sample(errors, rng.choice([2, 3]))
    good = rng.sample(fine, 5 - len(bad))
    for line, _ in bad:
        if _runs_ok(setup, line):
            raise GenerationError(f"{line} should fail")
    for line, _ in good:
        if not _runs_ok(setup, line):
            raise GenerationError(f"{line} should work")
    pairs = [(line, "Causes an error") for line, _ in bad] + [(line, "Runs fine") for line, _ in good]
    return match_question(
        topic=TOPIC, difficulty=MEDIUM, prompt="Match each line to what happens when it runs.",
        pairs=pairs, rng=rng, code=setup,
        explanation="Lists can be changed. Tuples and strings can't be changed, sets have no index positions, and a dict only answers for keys it really has.",
    )


EXPR_TYPES = [
    ("10 / 2", "float"), ("7 // 2", "int"), ('"5" * 2', "str"), ("5 > 3", "bool"), ("3 + 4.0", "float"),
    ("str(42)", "str"), ('len("hi")', "int"), ("2 + 3j", "complex"), ('"7" + "3"', "str"), ("7 + 3", "int"),
    ("3 == 3.0", "bool"), ("float(3)", "float"), ("int(2.8)", "int"), ("[1, 2, 3][0]", "int"), ('["a", "b"][1]', "str"),
]


@generator(TOPIC, HARD, qtype="match")
def gen_match_expression_type(rng: random.Random) -> Question:
    """Work out each value first, then its type."""
    chosen = rng.sample(EXPR_TYPES, 5)
    while len({t for _, t in chosen}) < 3:
        chosen = rng.sample(EXPR_TYPES, 5)
    pairs = [(f"type({e})", cls(t)) for e, t in chosen]
    present = {cls(t) for _, t in chosen}
    extras = [cls(c) for c in ("int", "float", "str", "bool") if cls(c) not in present][:1]
    return match_question(
        topic=TOPIC, difficulty=HARD, prompt="Work out each value, then match its type.",
        pairs=pairs, extra_options=extras, rng=rng,
        explanation="`/` always gives a `float`, `//` on ints gives an `int`, a comparison gives a `bool`, and anything in quotes is a `str` (so `\"5\" * 2` is the text `\"55\"`).",
    )


# ==========================================================================
# CODE -- type real Python (graded in the sandbox against hidden tests)
# ==========================================================================


def _varied(rng: random.Random, make_case, k: int, min_distinct: int = 3):
    """k cases from ``make_case(i)`` -> (case_object, key); retry until at least ``min_distinct``
    different keys (so a hard-coded answer can't pass)."""
    for _ in range(40):
        made = [make_case(i) for i in range(k)]
        if len({repr(key) for _, key in made}) >= min_distinct:
            return [c for c, _ in made]
    raise GenerationError("could not make varied cases")


# ---- EASY (one expression / one statement) -----------------------------------------------

@generator(TOPIC, EASY, qtype="code")
def gen_code_list_item(rng: random.Random) -> Question:
    """Lab: `fruits[0]` and `len(...)` on a list."""
    mode = rng.choice(["first", "last", "second", "count"])
    numeric = rng.random() < 0.3
    name = rng.choice(["scores", "numbers", "prices"]) if numeric else rng.choice(list(ITEM_POOLS))
    sizes = {"first": [3, 4, 3, 5], "last": [3, 4, 5, 3], "second": [3, 4, 3, 5], "count": [3, 5, 2, 4]}[mode]

    def make(i):
        n = sizes[i]
        items = rng.sample(range(10, 100), n) if numeric else rng.sample(ITEM_POOLS[name], n)
        ret = {"first": items[0], "last": items[-1], "second": items[1], "count": n}[mode]
        return ({name: items}, ret), ret

    pairs = _varied(rng, make, 4)
    solution = {"first": f"{name}[0]", "last": f"{name}[-1]", "second": f"{name}[1]", "count": f"len({name})"}[mode]
    what = {"first": "the first item", "last": "the last item", "second": "the second item", "count": "how many items it has"}[mode]
    why = {
        "first": "Indexes start at 0, so the first item is `[0]`.",
        "last": "`[-1]` counts from the end, so it is always the last item, whatever the length.",
        "second": "Indexes start at 0, so the second item is `[1]`.",
        "count": "`len(...)` returns the number of items in the list.",
    }[mode]
    return code_question(
        topic=TOPIC, difficulty=EASY,
        prompt=f"`{name}` is a list. Type an expression that gives {what}.",
        task=expression_task(solution, pairs),
        explanation=f"`{solution}` works for any list. {why}",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_dict_value(rng: random.Random) -> Question:
    """Lab: `student["name"]`; Mini-Challenge: `me["classes"][1]`."""
    mode = rng.choice(["name", "grade", "gpa", "second_class", "first_class", "class_count"])
    if mode in ("name", "grade", "gpa"):
        def make(i):
            d = student_dict(rng)
            return ({"student": d}, d[mode]), d[mode]

        pairs = _varied(rng, make, 4)
        solution = f'student["{mode}"]'
        prompt = f'`student` is a dictionary with the keys "name", "grade" and "gpa". Type an expression that gives the student\'s {mode}.'
        why = f'Use the key in quotes inside square brackets: `{solution}`.'
    else:
        def make(i):
            m = me_dict(rng, [3, 4, 5, 3][i])
            ret = {"second_class": m["classes"][1], "first_class": m["classes"][0], "class_count": len(m["classes"])}[mode]
            return ({"me": m}, ret), ret

        pairs = _varied(rng, make, 4)
        solution = {"second_class": 'me["classes"][1]', "first_class": 'me["classes"][0]', "class_count": 'len(me["classes"])'}[mode]
        what = {"second_class": "the second class", "first_class": "the first class", "class_count": "how many classes there are"}[mode]
        prompt = f'`me` is a dictionary with the keys "name", "grade" and "classes" (a list of course names). Type an expression that gives {what}.'
        why = 'First get the list with `me["classes"]`, then index it (indexes start at 0) or count it with `len`.'
    return code_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, task=expression_task(solution, pairs),
        explanation=f"`{solution}`. {why}",
    )


TYPE_CASE_VALUES = [42, 3.5, "Python", True, None, [1, 2, 3], (10, 20), {"name": "Sam"}, 7, "7", False, 2.0, 0, ["a", "b"]]


@generator(TOPIC, EASY, qtype="code")
def gen_code_print_type(rng: random.Random) -> Question:
    """Python Bingo: 'Use type() to print a variable's type' (and the lab's print(x, type(x)))."""
    style = rng.choice(["type_only", "value_type", "labelled"])
    values = rng.sample(TYPE_CASE_VALUES, 5)
    while len({type(v) for v in values}) < 3:
        values = rng.sample(TYPE_CASE_VALUES, 5)
    cases = []
    for v in values:
        shown = out_text(f"value = {lit(v)}\n" + {
            "type_only": "print(type(value))",
            "value_type": "print(value, type(value))",
            "labelled": 'print("Type:", type(value))',
        }[style])
        cases.append(Case(vars={"value": v}, out=shown))
    solution = {
        "type_only": "print(type(value))",
        "value_type": "print(value, type(value))",
        "labelled": 'print("Type:", type(value))',
    }[style]
    prompt = {
        "type_only": "The variable `value` already holds something. Print its type, e.g. `<class 'int'>`.",
        "value_type": "The variable `value` already holds something. Print the value, a space, then its type on one line, e.g. `42 <class 'int'>`.",
        "labelled": "The variable `value` already holds something. Print `Type:` followed by its type, e.g. `Type: <class 'int'>`.",
    }[style]
    return code_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, task=program_task(solution, cases, examples=2),
        explanation="`type(value)` gives the data type, and `print` shows it. `print(a, b)` puts a space between the pieces.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_in_expression(rng: random.Random) -> Question:
    """Python Bingo: 'Check membership: is "python" in a given list?'  Sets are for membership tests."""
    form = rng.choice(["list_in", "set_in", "list_not_in"])
    target, pool = rng.choice([
        ("python", ["java", "ruby", "swift", "go", "rust", "perl"]),
        ("red", ["green", "blue", "yellow", "pink", "orange", "black"]),
        ("apple", ["kiwi", "mango", "lemon", "grape", "peach", "plum"]),
        ("cat", ["dog", "fish", "bird", "hamster", "turtle", "rabbit"]),
    ])
    var = {"list_in": "words", "set_in": "colors", "list_not_in": "words"}[form]
    wants_in = form != "list_not_in"
    contains = [True, False, True, False, True]
    rng.shuffle(contains)
    cases = []
    for has in contains:
        others = rng.sample(pool, 3)
        items = others + ([target] if has else [])
        rng.shuffle(items)
        if not has and rng.random() < 0.4:
            items[rng.randrange(len(items))] = target.capitalize()  # "Python" is not "python"
        value = set(items) if form == "set_in" else items
        cases.append(({var: value}, (target in items) == wants_in))
    solution = f'{lit(target)} {"in" if wants_in else "not in"} {var}'
    kind = "set" if form == "set_in" else "list"
    if wants_in:
        prompt = f'`{var}` is a {kind} of text. Type an expression that is `True` when {lit(target)} is in `{var}` and `False` otherwise.'
    else:
        prompt = f'`{var}` is a {kind} of text. Type an expression that is `True` when {lit(target)} is NOT in `{var}`.'
    return code_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, task=expression_task(solution, cases),
        explanation=f"`{solution}` checks membership and gives `True` or `False`. Text must match exactly, including capital letters.",
    )


# ---- MEDIUM (a function or a short program) ---------------------------------------------------

@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_unique_letters(rng: random.Random) -> Question:
    """Python Bingo: 'Create a set of unique letters from a word'."""
    words = rng.sample(UNIQUE_WORDS, 4) + [rng.choice(["aaaa", "xyz", "hello", "ee"])]
    cases = [({"word": w}, len(set(w))) for w in words]
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt="`word` is a string. Type an expression that gives how many different letters it contains (`\"banana\"` has 3: b, a and n).",
        task=expression_task("len(set(word))", cases),
        explanation="`set(word)` keeps one copy of each different letter, and `len(...)` counts them.",
    )


RECORDS = [
    ("make_student", ["name", "grade", "gpa"]),
    ("make_pet", ["name", "age", "kind"]),
    ("make_player", ["name", "score", "level"]),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_make_record(rng: random.Random) -> Question:
    """Lab: `student = {"name": "Sam", "grade": 11, "gpa": 3.6}` as a function that builds the dictionary."""
    fn, keys = rng.choice(RECORDS)
    params = ", ".join(keys)
    solution = f"def {fn}({params}):\n    return {{{', '.join(f'{lit(k)}: {k}' for k in keys)}}}"

    def value(k):
        return {
            "name": rng.choice(PEOPLE + ["Rex", "Milo", "Luna"]), "grade": rng.choice([9, 10, 11, 12]),
            "gpa": round(rng.choice([2.8, 3.1, 3.5, 3.9, 4.0]), 1), "age": rng.choice([1, 2, 3, 5, 8]),
            "kind": rng.choice(["dog", "cat", "gecko", "fish"]), "score": rng.choice([0, 120, 450, 980]),
            "level": rng.choice([1, 2, 5, 7]),
        }[k]

    def make(i):
        args = tuple(value(k) for k in keys)
        return (args, dict(zip(keys, args))), args

    cases = _varied(rng, make, 4)
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Write a function `{fn}({params})` that returns a dictionary with the keys {', '.join(lit(k) for k in keys)} holding those values.",
        task=function_task(fn, solution, cases),
        explanation="A dictionary is written `{key: value, ...}`. Use `return` so the function gives the dictionary back.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_return_tuple(rng: random.Random) -> Question:
    """Tuples are ordered and unchangeable: a function that returns one."""
    form = rng.choice(["make_point", "first_and_last", "min_max"])
    if form == "make_point":
        fn = "make_point"
        solution = "def make_point(x, y):\n    return (x, y)"

        def make(i):
            a, b = rng.randint(-5, 20), rng.randint(-5, 20)
            return ((a, b), (a, b)), (a, b)

        cases = _varied(rng, make, 4)
        prompt = "Write a function `make_point(x, y)` that returns the point as a tuple `(x, y)`."
        why = "A tuple is written with parentheses: `(x, y)`. It keeps the order and can't be changed."
    elif form == "first_and_last":
        fn = "first_and_last"
        solution = "def first_and_last(items):\n    return (items[0], items[-1])"

        def make(i):
            items = rng.sample(FRUITS, [3, 4, 2, 5][i])
            return ((items,), (items[0], items[-1])), (items[0], items[-1])

        cases = _varied(rng, make, 4)
        cases.append(Case(args=[["kiwi"]], ret=("kiwi", "kiwi")))
        prompt = "Write a function `first_and_last(items)` that returns a tuple with the first item and the last item of the list."
        why = "`items[0]` is the first item and `items[-1]` the last. Return them together as a tuple."
    else:
        fn = "min_max"
        solution = "def min_max(numbers):\n    return (min(numbers), max(numbers))"

        def make(i):
            nums = rng.sample(range(-5, 60), [3, 4, 5, 3][i])
            return ((nums,), (min(nums), max(nums))), (min(nums), max(nums))

        cases = _varied(rng, make, 4)
        cases.append(Case(args=[[7]], ret=(7, 7)))
        prompt = "Write a function `min_max(numbers)` that returns a tuple `(smallest, largest)` for a list of numbers."
        why = "`min(numbers)` and `max(numbers)` find the two values; return them together in a tuple."
    return code_question(
        topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=function_task(fn, solution, cases),
        explanation=why,
    )


ME_FUNCS = [
    ("class_count", "returns how many classes there are", 'len(me["classes"])', lambda m: len(m["classes"])),
    ("second_class", "returns the second class", 'me["classes"][1]', lambda m: m["classes"][1]),
    ("last_class", "returns the last class", 'me["classes"][-1]', lambda m: m["classes"][-1]),
    ("first_class", "returns the first class", 'me["classes"][0]', lambda m: m["classes"][0]),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_me_function(rng: random.Random) -> Question:
    """Mini-Challenge dictionary `me` (name, grade, classes) used inside a function."""
    fn, what, expr, f = rng.choice(ME_FUNCS)

    def make(i):
        m = me_dict(rng, [3, 4, 5, 3][i])
        return ((m,), f(m)), f(m)

    cases = _varied(rng, make, 4)
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f'Write a function `{fn}(me)` that {what}. `me` is a dictionary with the keys "name", "grade" and "classes" (a list of course names).',
        task=function_task(fn, f"def {fn}(me):\n    return {expr}", cases),
        explanation=f'`me["classes"]` is the list of classes. Return `{expr}` (use `return`, not `print`).',
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_append_program(rng: random.Random) -> Question:
    """Python Bingo: 'Append an item to a list and print the new length'."""
    name = rng.choice(list(ITEM_POOLS))
    final = rng.choice(["list", "length", "last"])

    def make(i):
        n = [3, 0, 2, 4][i]
        items = rng.sample(ITEM_POOLS[name], n + 1)
        new, items = items[0], items[1:]
        after = items + [new]
        out = {"list": repr(after), "length": str(len(after)), "last": new}[final]
        return Case(vars={name: items, "new_item": new}, out=out, expect_vars={name: after}), (new, tuple(items))

    cases = _varied(rng, make, 4)
    printed = {"list": f"print({name})", "length": f"print(len({name}))", "last": f"print({name}[-1])"}[final]
    what = {"list": "the list", "length": "how many items it has now", "last": "its last item"}[final]
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"The list `{name}` and the text `new_item` already exist. Add `new_item` to the end of `{name}`, then print {what}.",
        task=program_task(f"{name}.append(new_item)\n{printed}", cases, examples=2),
        explanation=f"`{name}.append(new_item)` changes the list itself, so the next line sees the new item.",
    )


DICT_BUILDS = [
    ("student", ["name", "grade", "gpa"], "gpa"),
    ("student", ["name", "grade", "gpa"], "grade"),
    ("pet", ["name", "age", "kind"], "kind"),
    ("pet", ["name", "age", "kind"], "age"),
    ("player", ["name", "score", "level"], "score"),
    ("player", ["name", "score", "level"], "level"),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_build_dict(rng: random.Random) -> Question:
    """Python Bingo: 'Create a dict with name/grade/gpa and print gpa'."""
    var, keys, show_key = rng.choice(DICT_BUILDS)

    def val(k):
        return {
            "name": rng.choice(PEOPLE), "grade": rng.choice([9, 10, 11, 12]), "gpa": round(rng.choice([2.8, 3.1, 3.5, 3.9, 4.0]), 1),
            "age": rng.choice([1, 2, 3, 5, 8]), "kind": rng.choice(["dog", "cat", "gecko", "fish"]),
            "score": rng.choice([0, 120, 450, 980]), "level": rng.choice([1, 2, 5, 7]),
        }[k]

    def make(i):
        vals = {k: val(k) for k in keys}
        return Case(vars=dict(vals), out=str(vals[show_key]), expect_vars={var: dict(vals)}), repr(vals[show_key])

    cases = _varied(rng, make, 3)
    fields = ", ".join(f'{lit(k)}: {k}' for k in keys)
    solution = f"{var} = {{{fields}}}\nprint({var}[{lit(show_key)}])"
    names = ", ".join(f"`{k}`" for k in keys)
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"The variables {names} already exist. Create a dictionary named `{var}` with the keys {', '.join(lit(k) for k in keys)} holding those values, then print its {lit(show_key)} by looking it up in the dictionary.",
        task=program_task(solution, cases, examples=2),
        explanation=f'Build it like the lab\'s `student = {{"name": "Sam", ...}}`, then look a value up with `{var}[{lit(show_key)}]`.',
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_has_duplicates(rng: random.Random) -> Question:
    """Sets keep one copy of each item, so a list has repeats when len(list) != len(set(list))."""
    inverse = rng.random() < 0.4
    fn = "all_unique" if inverse else "has_duplicates"
    pool_kind = rng.choice(["numbers", "words"])
    pool = list(range(1, 9)) if pool_kind == "numbers" else rng.sample(FRUITS, 6)
    cases = []
    for dup in [False, True, True, False, True]:
        base = rng.sample(pool, rng.choice([3, 4]))
        if dup:
            base = base + [rng.choice(base)]
            rng.shuffle(base)
        cases.append(Case(args=[base], ret=(not dup) if inverse else dup))
    cases.insert(2, Case(args=[[]], ret=True if inverse else False))
    if inverse:
        solution = f"def {fn}(items):\n    return len(items) == len(set(items))"
        prompt = f"Write a function `{fn}(items)` that returns `True` if no item appears twice in the list, and `False` otherwise."
    else:
        solution = f"def {fn}(items):\n    return len(items) != len(set(items))"
        prompt = f"Write a function `{fn}(items)` that returns `True` if any item appears more than once in the list, and `False` otherwise."
    return code_question(
        topic=TOPIC, difficulty=MEDIUM, prompt=prompt, task=function_task(fn, solution, cases),
        explanation="`set(items)` drops repeats, so it is shorter than the list exactly when something appeared twice. Compare `len(items)` with `len(set(items))`.",
    )


TYPE_TESTS = [
    ("is_text", str, "a string (text)"),
    ("is_list", list, "a list"),
    ("is_decimal", float, "a float (a number with a decimal point)"),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_type_check(rng: random.Random) -> Question:
    """`type(value)` in a function: is this value a str / list / float?"""
    fn, t, label = rng.choice(TYPE_TESTS)
    samples = ["hi", "5", 7, 2.5, 3.0, [1, 2], ["a"], True, None, (1, 2), "", 0, "3.5"]
    chosen = rng.sample(samples, 7)
    if not any(type(v) is t for v in chosen):
        chosen[rng.randrange(7)] = {str: "Python", list: [1, 2, 3], float: 9.81}[t]
    cases = [Case(args=[v], ret=type(v) is t) for v in chosen]
    solution = f"def {fn}(value):\n    return type(value) == {t.__name__}"
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"Write a function `{fn}(value)` that returns `True` if `value` is {label}, and `False` for anything else.",
        task=function_task(fn, solution, cases),
        explanation=f"`type(value)` gives the data type, so compare it with `{t.__name__}` using `==`. Remember `\"5\"` in quotes is a `str`, not a number.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_types_loop(rng: random.Random) -> Question:
    """Loop over a list and print the type of every item."""
    pool = [7, "7", 7.0, True, None, [7], (7, 8), {"n": 7}, "hi", 3.5, 0, False]

    def make(i):
        vals = rng.sample(pool, [3, 4, 3, 5][i])
        out = "\n".join(cls(type(v).__name__) for v in vals)
        return Case(vars={"values": vals}, out=out), out

    cases = _varied(rng, make, 4)
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt="The list `values` holds a mix of data types. Use a loop to print the type of every item, one per line, e.g. `<class 'int'>`.",
        task=program_task("for value in values:\n    print(type(value))", cases, examples=2,
                          requires=[(r"\bfor\b", "Use a for loop to visit every item.")]),
        explanation="`for value in values:` visits each item in order, and `print(type(value))` shows its type.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_list_stats(rng: random.Random) -> Question:
    """Python Bingo: 'Create a list of 5 integers and print the max' -- count, highest, lowest."""
    label_set = rng.choice([("Count", "Highest", "Lowest"), ("Items", "Max", "Min")])

    def make(i):
        nums = rng.sample(range(5, 100), [5, 4, 1, 6][i])
        out = f"{label_set[0]}: {len(nums)}\n{label_set[1]}: {max(nums)}\n{label_set[2]}: {min(nums)}"
        return Case(vars={"scores": nums}, out=out), out

    cases = _varied(rng, make, 4)
    a, b, c = label_set
    solution = f'print("{a}:", len(scores))\nprint("{b}:", max(scores))\nprint("{c}:", min(scores))'
    return code_question(
        topic=TOPIC, difficulty=MEDIUM,
        prompt=f"The list `scores` already exists. Print three lines: `{a}: ` and how many scores there are, `{b}: ` and the biggest score, then `{c}: ` and the smallest score.",
        task=program_task(solution, cases, examples=2),
        explanation="`len(scores)` counts the items, `max(scores)` finds the biggest and `min(scores)` the smallest. `print(\"Count:\", n)` puts a space after the colon.",
    )


# ---- HARD (multi-step program or function) --------------------------------------------------------

@generator(TOPIC, HARD, qtype="code")
def gen_code_kind_of(rng: random.Random) -> Question:
    """Use type() with if / elif to describe a value (True and False are bool, not int)."""
    solution = (
        "def kind_of(value):\n"
        "    if type(value) == str:\n"
        '        return "text"\n'
        "    elif type(value) == bool:\n"
        '        return "boolean"\n'
        "    elif type(value) == int:\n"
        '        return "whole number"\n'
        "    elif type(value) == float:\n"
        '        return "decimal"\n'
        "    elif value == None:\n"
        '        return "nothing"\n'
        "    else:\n"
        '        return "other"'
    )
    first = [rng.choice(["hi", "Python", "Sam"]), rng.choice([7, 42, 100])]
    others = [False, 0, "5", "", (3, 4), [1, 2], {"a": 1}, 3.0]
    hidden = [True, None, 2.5, *rng.sample(others, 3)]
    rng.shuffle(hidden)
    cases = [Case(args=[v], ret=_kind(v)) for v in first + hidden]
    return code_question(
        topic=TOPIC, difficulty=HARD,
        prompt=(
            'Write a function `kind_of(value)` that returns "text" for a str, "whole number" for an int, "decimal" for a float, '
            '"boolean" for `True` or `False`, "nothing" for `None`, and "other" for anything else.'
        ),
        task=function_task("kind_of", solution, cases),
        explanation="Check `type(value)` with `==` in an if/elif chain. `True` and `False` are `bool`, so they must not be called whole numbers.",
    )


def _kind(v) -> str:
    if type(v) is str:
        return "text"
    if type(v) is bool:
        return "boolean"
    if type(v) is int:
        return "whole number"
    if type(v) is float:
        return "decimal"
    if v is None:
        return "nothing"
    return "other"


COUNT_TYPES = [
    ("count_strings", str, "str", "strings (text)", ""),
    ("count_ints", int, "int", "ints (whole numbers)", " `True` and `False` are not ints."),
    ("count_floats", float, "float", "floats (numbers with a decimal point)", ""),
]


@generator(TOPIC, HARD, qtype="code")
def gen_code_count_type(rng: random.Random) -> Question:
    """Loop over mixed values and count one type."""
    fn, t, tname, label, note = rng.choice(COUNT_TYPES)
    pool = ["a", "b", "five", "7", 5, 12, 0, 3.5, 2.0, True, False, None]
    solution = (
        f"def {fn}(items):\n"
        "    count = 0\n"
        "    for item in items:\n"
        f"        if type(item) == {tname}:\n"
        "            count += 1\n"
        "    return count"
    )

    def make(i):
        k = [5, 4, 6, 3][i]
        items = rng.sample(pool, k)
        ret = sum(1 for x in items if type(x) is t)
        return ((items,), ret), (ret, k)

    cases = _varied(rng, make, 4)
    cases.insert(2, Case(args=[[]], ret=0))
    cases.append(Case(args=[[True, 1, 1.0, "1"]], ret=sum(1 for x in [True, 1, 1.0, "1"] if type(x) is t)))
    return code_question(
        topic=TOPIC, difficulty=HARD,
        prompt=f"Write a function `{fn}(items)` that returns how many of the items in the list are {label}.{note}",
        task=function_task(fn, solution, cases),
        explanation=f"Loop over the list, check `type(item) == {tname}`, and add 1 to a counter each time. Return the counter after the loop (an empty list gives 0).",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_add_class(rng: random.Random) -> Question:
    """Mini-Challenge dictionary: change the list inside `me`."""
    solution = 'def add_class(me, class_name):\n    me["classes"].append(class_name)\n    return me'

    def make(i):
        m = me_dict(rng, [2, 3, 1, 4][i])
        new = rng.choice([s for s in SUBJECTS if s not in m["classes"]])
        after = {"name": m["name"], "grade": m["grade"], "classes": m["classes"] + [new]}
        return ((m, new), after), (new, tuple(m["classes"]))

    cases = _varied(rng, make, 4)
    return code_question(
        topic=TOPIC, difficulty=HARD,
        prompt='Write a function `add_class(me, class_name)` that adds `class_name` to the end of the "classes" list inside the dictionary `me`, then returns `me`.',
        task=function_task("add_class", solution, cases),
        explanation='`me["classes"]` is a list, so `me["classes"].append(class_name)` adds to it. Then `return me` gives back the updated dictionary.',
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_me_challenge(rng: random.Random) -> Question:
    """The Mini-Challenge 'Classes Dictionary': name, second class, and the f-string."""
    def make(i):
        m = me_dict(rng, [3, 4, 5, 3][i])
        out = f"{m['name']}\n{m['classes'][1]}\n{m['name']} is in grade {m['grade']} and is taking {len(m['classes'])} classes."
        return Case(vars={"me": m}, out=out), out

    cases = _varied(rng, make, 4)
    solution = (
        'print(me["name"])\n'
        'print(me["classes"][1])\n'
        'name = me["name"]\n'
        'grade = me["grade"]\n'
        'n = len(me["classes"])\n'
        'print(f"{name} is in grade {grade} and is taking {n} classes.")'
    )
    return code_question(
        topic=TOPIC, difficulty=HARD,
        prompt=(
            'The dictionary `me` already exists with the keys "name", "grade" and "classes" (a list of course names). Print 3 lines: '
            "just the name; the second class; then a sentence like `Reid is in grade 11 and is taking 3 classes.`"
        ),
        task=program_task(solution, cases, examples=2),
        explanation='Look values up with `me["name"]`, `me["classes"][1]` and `len(me["classes"])`, then put them into an f-string.',
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_remove_duplicates(rng: random.Random) -> Question:
    """Build a new list with each different item once, in the order it first appears."""
    solution = (
        "def remove_duplicates(items):\n"
        "    result = []\n"
        "    for item in items:\n"
        "        if item not in result:\n"
        "            result.append(item)\n"
        "    return result"
    )
    use_words = rng.random() < 0.5
    pool = rng.sample(COLOR_WORDS, 5) if use_words else rng.sample(range(1, 10), 5)
    cases = []
    for k in (5, 6, 4, 7):
        base = rng.sample(pool, 3)
        items = base + rng.choices(base, k=k - 3)
        rng.shuffle(items)
        out = []
        for x in items:
            if x not in out:
                out.append(x)
        cases.append(Case(args=[items], ret=out))
    cases.append(Case(args=[[]], ret=[]))
    cases.append(Case(args=[[pool[0], pool[0], pool[0]]], ret=[pool[0]]))
    return code_question(
        topic=TOPIC, difficulty=HARD,
        prompt="Write a function `remove_duplicates(items)` that returns a new list with each different item once, keeping the order in which they first appear.",
        task=function_task("remove_duplicates", solution, cases),
        explanation="Start with an empty list, loop over `items`, and `append` an item only if it is not already in the new list. A set would drop the duplicates but lose the order.",
    )
