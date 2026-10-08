"""Question generators for the "classes" topic (CSF.2.M: Modules and Classes).

Everything comes from the lesson: organising code across files (`math_tools.py`, `shapes.py`,
`main_program.py`), `import math_tools` then `math_tools.add(1, 2)`, `from math_tools import add,
multiply` (no prefix), a class as a blueprint, methods as functions inside a class, `__init__`
running automatically, `self` meaning "this specific object", the `Square` class with `area()` and
`perimeter()` (`side * 4`), every object keeping its own attributes (`sq1` vs `sq2`), the output
`Area: 25`, and the Triangle mini-challenge.  Nothing here uses inheritance, dunder methods other
than `__init__`, class attributes, `@property` or any other idea the lesson does not teach.

Imports cannot run in the code sandbox, so questions about `import` are multiple choice, blanks or
matching only.  Class and method questions are typed code: the player writes the class and a hidden
`after=` harness creates the objects and stores what their methods return in variables.  Wherever an answer depends on running
code, it is computed by running the snippet (``output_question``), so the questions are correct by
construction.
"""

from __future__ import annotations

import functools
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
    display_output,
    error_choice,
    fn_cases,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "classes"

# --------------------------------------------------------------------------
# Shapes: the lesson's Square, its Triangle mini-challenge and one look-alike (Rectangle)
# --------------------------------------------------------------------------

SHAPES = {
    "Square": {
        "params": ["side"],
        "var": "sq",
        "area": "self.side * self.side",
        "perimeter": "self.side * 4",
    },
    "Rectangle": {
        "params": ["width", "height"],
        "var": "r",
        "area": "self.width * self.height",
        "perimeter": "2 * (self.width + self.height)",
    },
    "Triangle": {
        "params": ["base", "height"],
        "var": "t",
        "area": "0.5 * self.base * self.height",
    },
}
SHAPE_NAMES = list(SHAPES)
TITLE = {"area": "Area", "perimeter": "Perimeter"}


def shape_args(rng: random.Random, name: str) -> list[int]:
    """Small whole-number arguments for a shape (distinct for two-parameter shapes)."""
    if name == "Square":
        return [rng.choice([3, 5, 6, 7, 8, 9, 10, 12])]
    if name == "Rectangle":
        w = rng.randint(2, 9)
        return [w, rng.choice([h for h in range(2, 10) if h != w])]
    return [rng.randint(3, 12), rng.randint(2, 9)]


def class_text(name: str, methods=(), *, gap: bool = True) -> str:
    """Source of the shape class: `__init__` plus the listed methods (lesson style)."""
    d = SHAPES[name]
    lines = [f"class {name}:", f"    def __init__({', '.join(['self', *d['params']])}):"]
    lines += [f"        self.{p} = {p}" for p in d["params"]]
    for m in methods:
        if gap:
            lines.append("")
        lines += [f"    def {m}(self):", f"        return {d[m]}"]
    return "\n".join(lines)


def call_text(name: str, args) -> str:
    return f"{name}({', '.join(str(a) for a in args)})"


def var_name(name: str, n: int = 1) -> str:
    return f"{SHAPES[name]['var']}{n}"


def method_value(name: str, method: str, args) -> object:
    """The real value of `Name(*args).method()` (computed by running the class source)."""
    res = run_code(f"{class_text(name, [method])}\nprint({call_text(name, args)}.{method}())")
    if res.error:
        raise GenerationError(f"{name}.{method} raised {res.error}")
    return eval(res.output)  # our own printed number


def _out(code: str) -> str:
    """What a snippet prints, as an answer choice (or the error it raises)."""
    res = run_code(code.strip("\n"))
    return error_choice(res.error) if res.error else display_output(res.output)


def _retry(fn):
    """Re-draw (deterministically, from the same rng) if a random draw gives too few distinct answers."""

    @functools.wraps(fn)
    def wrapper(rng: random.Random) -> Question:
        last: Exception | None = None
        for _ in range(40):
            try:
                return fn(rng)
            except GenerationError as exc:
                last = exc
        raise last  # type: ignore[misc]

    return wrapper


def _pool_question(rng: random.Random, pool, difficulty: int) -> Question:
    """One question from a pool of (prompt, correct, wrong answers, explanation)."""
    prompt, correct, wrong, why = rng.choice(pool)
    wrong = list(wrong)
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC, difficulty=difficulty, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


# the lesson's math_tools.py
MATH_TOOLS = {"add": "a + b", "multiply": "a * b", "square": "a ** 2"}


def math_value(fn: str, args) -> int:
    a = args[0]
    if fn == "square":
        return a**2
    b = args[1]
    return a + b if fn == "add" else a * b


def math_args(rng: random.Random, fn: str) -> list[int]:
    if fn == "square":
        return [rng.randint(3, 9)]
    a, b = rng.sample(range(2, 10), 2)
    return [a, b]


# ==========================================================================
# CHOICE -- EASY (vocabulary and one-line results, like the Canvas quiz)
# ==========================================================================

_CLASS_IDEA = [
    (
        "What is a class in Python?",
        "A blueprint for creating objects",
        ["A built-in function that prints output", "A file full of reusable functions", "A variable that stores one value"],
        "A class is a blueprint: it describes the data and behavior its objects will have. `Square` is the blueprint and `sq1 = Square(5)` builds one object from it.",
    ),
    (
        "Which statement about classes is true?",
        "Classes group data and behavior together",
        ["Classes can only store numbers", "A class is just another name for a loop", "A class can only be used one time"],
        "A class keeps related data and the functions that work with that data in one place.",
    ),
    (
        "How many objects can you create from one class such as `Square`?",
        "As many as you want",
        ["Exactly one", "None until the program ends", "Only as many as it has methods"],
        "The class is only a blueprint, so you can build many objects (`sq1`, `sq2`, ...) from it.",
    ),
    (
        "Why do programmers put related data and functions into a class?",
        "It keeps the code organized and reusable",
        ["It makes Python skip error messages", "It lets them avoid writing any functions", "Every program needs exactly one class"],
        "Classes group data and behavior together, which keeps related code organized, reusable and modular.",
    ),
    (
        "In Python, a class is best described as a ...",
        "blueprint for objects",
        ["list of files", "type of loop", "kind of error message"],
        "A class is a blueprint for creating objects.",
    ),
]


@generator(TOPIC, EASY)
def gen_class_blueprint(rng: random.Random) -> Question:
    """'A class is a blueprint for creating objects' in the quiz's voice."""
    return _pool_question(rng, _CLASS_IDEA, EASY)


_VOCAB = [
    (
        "What is a function that is defined inside a class called?",
        "A method",
        ["A module", "An object", "An attribute"],
        "Functions inside a class are called methods, like `area()` and `perimeter()` in `Square`.",
    ),
    (
        "What do we call something created from a class, like `sq1 = Square(5)`?",
        "An object",
        ["A method", "A module", "A blueprint"],
        "`Square` is the blueprint (the class); `sq1` is an object built from it.",
    ),
    (
        "Which keyword starts the definition of a class?",
        "class",
        ["def", "import", "new"],
        "A class starts with the keyword `class`, followed by its name and a colon: `class Square:`.",
    ),
    (
        "What do we call a Python file such as `math_tools.py` whose functions other files can import?",
        "A module",
        ["A method", "An object", "An attribute"],
        "Any Python file can be used as a module with `import`; `math_tools.py` is the toolbox module.",
    ),
    (
        "What do we call the data stored inside an object, like the `side` of a Square?",
        "An attribute",
        ["A method", "A module", "A blueprint"],
        "Each object stores its own data in attributes such as `self.side`.",
    ),
    (
        "Which keyword starts a method definition inside a class?",
        "def",
        ["class", "self", "import"],
        "Methods are functions inside a class, so they start with `def` just like any function.",
    ),
]


@generator(TOPIC, EASY)
def gen_class_vocabulary(rng: random.Random) -> Question:
    """'What do we call ...?' (method, object, module, attribute, class)."""
    return _pool_question(rng, _VOCAB, EASY)


_INIT = [
    (
        "When does `__init__` run?",
        "Automatically, when a new object is created",
        ["Only when you call `obj.__init__()`", "Every time you call `area()`", "When the program ends"],
        "`__init__` runs automatically whenever you create an object, such as `Square(5)`.",
    ),
    (
        "What is `__init__` used for in a class?",
        "Setting up the data of a new object",
        ["Printing the final answer", "Importing another file", "Deleting an object"],
        "`__init__` initializes the object's data, for example `self.side = side`.",
    ),
    (
        "Which line makes `__init__` of the `Square` class run?",
        "sq1 = Square(5)",
        ["print(sq1.area())", "from shapes import Square", "class Square:"],
        "Creating an object, like `Square(5)`, runs `__init__` automatically. Importing or defining the class does not.",
    ),
    (
        "In `def __init__(self, side):`, where does the value of `side` come from?",
        "From the value passed in, like the 5 in Square(5)",
        ["From the file name shapes.py", "From the last method that ran", "Python picks a random number"],
        "`Square(5)` sends 5 to `__init__`, which stores it with `self.side = side`.",
    ),
]


@generator(TOPIC, EASY)
def gen_init_basics(rng: random.Random) -> Question:
    """`__init__` runs automatically and sets up the data."""
    return _pool_question(rng, _INIT, EASY)


@generator(TOPIC, EASY)
def gen_init_header_line(rng: random.Random) -> Question:
    """Which line correctly starts `__init__`?"""
    name = rng.choice(SHAPE_NAMES)
    params = SHAPES[name]["params"]
    args = shape_args(rng, name)
    full = ", ".join(["self", *params])
    correct = f"def __init__({full}):"
    wrong = [
        f"def __init__({', '.join(params)}):",
        f"def _init_({full}):",
        f"def init({full}):",
        f"__init__({full}):",
        "def __init__(self):",
    ]
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which line correctly starts the `__init__` method of the `{name}` class, so `{call_text(name, args)}` can set up the new object?",
        correct=correct,
        distractors=wrong,
        explanation="The method is named `__init__` (two underscores on each side), starts with `def`, and its first parameter is `self`, followed by the values it receives.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_self_meaning(rng: random.Random) -> Question:
    """What `self` refers to (the specific object)."""
    s1, s2 = rng.sample([3, 4, 5, 6, 7, 8, 9], 2)
    which = rng.choice([1, 2])
    mine, other = (s1, s2) if which == 1 else (s2, s1)
    pool = [
        (
            "In `def area(self):`, what does `self` refer to?",
            "The specific object the method is called on",
            ["The class itself, shared by every object", "The file that contains the class", "The number the method returns"],
            "`self` refers to the specific object created from the class, so each object uses its own data.",
        ),
        (
            "What does `self.side` mean inside a `Square` method?",
            "The `side` value stored in this particular object",
            ["The `side` of every Square at once", "A variable named side in main_program.py", "A function called side"],
            "`self.side` is the `side` attribute of the object the method was called on.",
        ),
        (
            f"With `sq1 = Square({s1})` and `sq2 = Square({s2})`, what is `self.side` while `sq{which}.area()` runs?",
            str(mine),
            [str(other), str(s1 + s2), str(s1 * s2)],
            f"`self` is the object the method was called on. Here that is `sq{which}`, whose side is {mine}.",
        ),
        (
            "Why does every method in the `Square` class start with the parameter `self`?",
            "So the method can use the data of the object it is called on",
            ["So the method can import other files", "So Python knows the method returns a number", "So the class runs only once"],
            "`self` gives each method access to its own object's attributes, like `self.side`.",
        ),
    ]
    return _pool_question(rng, pool, EASY)


@generator(TOPIC, EASY)
def gen_import_which_line(rng: random.Random) -> Question:
    """Which line imports the whole module / selected functions / a class?"""
    kind = rng.choice(["whole", "select", "class"])
    if kind == "whole":
        mod = rng.choice(["math_tools", "math_tools", "shapes"])
        prompt = f"Which line imports the whole `{mod}` module?"
        correct = f"import {mod}"
        wrong = [f"include {mod}", f"import {mod}.py", f"using {mod}", f"from {mod}"]
        why = f"`import {mod}` gives access to everything inside {mod}.py."
    elif kind == "select":
        a, b = rng.sample(list(MATH_TOOLS), 2)
        prompt = f"Which line imports only `{a}` and `{b}` from `math_tools`?"
        correct = f"from math_tools import {a}, {b}"
        wrong = [f"import {a}, {b} from math_tools", f"from {a}, {b} import math_tools", f"import math_tools {a} {b}"]
        why = f"A selective import has the form `from module import name1, name2`, so you can call {a} and {b} without the `math_tools.` prefix."
    else:
        cls = rng.choice(["Square", "Triangle"])
        prompt = f"Which line brings the `{cls}` class from `shapes.py` into `main_program.py`?"
        correct = f"from shapes import {cls}"
        wrong = [f"import {cls} from shapes", f"from {cls} import shapes", f"from shapes get {cls}"]
        why = f"`from shapes import {cls}` imports just that class, so you can write `{cls}(...)` directly."
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


@generator(TOPIC, EASY)
def gen_module_file_roles(rng: random.Random) -> Question:
    """Which file does what in the lesson's project."""
    decoy = rng.choice(["utils.py", "toolbox.py", "classes.py", "helpers.py"])
    pool = [
        ("In the lesson's project, which file holds the reusable math functions (the toolbox)?", "math_tools.py",
         "`math_tools.py` is the toolbox: `add`, `multiply` and `square` live there so any file can reuse them."),
        ("In the lesson's project, which file defines the `Square` class?", "shapes.py",
         "`shapes.py` holds the class definitions, such as `Square`."),
        ("In the lesson's project, which file contains the main logic that uses the other files?", "main_program.py",
         "`main_program.py` is the main script: it imports from `math_tools.py` and `shapes.py` and uses them."),
    ]
    prompt, correct, why = rng.choice(pool)
    wrong = [f for f in ("math_tools.py", "shapes.py", "main_program.py") if f != correct] + [decoy]
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


_WHY_FILES = [
    (
        "Why do large programs use more than one file?",
        "Each file handles a specific job, keeping code organized",
        ["Python can only run 50 lines per file", "Functions only work when each has its own file", "Every variable needs its own file"],
        "Large programs split their code into files that each do one job and share information with each other.",
    ),
    (
        "What is the benefit of separating a project into math_tools.py, shapes.py and main_program.py?",
        "The project is easier to read, debug and reuse",
        ["The program runs without a main file", "Python can then skip the import keyword", "The classes no longer need methods"],
        "Separating files makes large projects easier to read, debug and reuse.",
    ),
    (
        "What does the `import` keyword allow you to do?",
        "Use the functions that are inside another file",
        ["Delete a file you no longer need", "Turn a function into a class", "Run a loop one extra time"],
        "The `import` keyword gives access to the functions inside another file.",
    ),
    (
        "In the lesson, what is `math_tools` compared to?",
        "A toolbox of reusable functions",
        ["A blueprint for one object", "A list of variables", "A game loop"],
        "Think of `math_tools` as the toolbox and `main_program` as the project that uses those tools.",
    ),
    (
        "Which sentence best describes how files, classes and functions connect?",
        "Files hold functions and classes; main_program.py uses them",
        ["Every function must live inside its own class", "Files can only share code by copying and pasting it", "Classes replace functions, so files are not needed"],
        "Functions and classes are defined in files such as math_tools.py and shapes.py, and main_program.py imports them and puts them to work.",
    ),
]


@generator(TOPIC, EASY)
def gen_why_multiple_files(rng: random.Random) -> Question:
    """Why modules / multiple files (lesson sections 1, 4 and 9)."""
    return _pool_question(rng, _WHY_FILES, EASY)


@generator(TOPIC, EASY)
def gen_create_object_line(rng: random.Random) -> Question:
    """Which line creates an object from the class?"""
    name = rng.choice(SHAPE_NAMES)
    args = shape_args(rng, name)
    var = var_name(name, rng.choice([1, 1, 2]))
    low = name.lower()
    correct = f"{var} = {call_text(name, args)}"
    wrong = [
        f"{var} = new {call_text(name, args)}",
        f"{var} = {low}({', '.join(map(str, args))})",
        f"{var} = {name}[{', '.join(map(str, args))}]",
        f"{var} = {name}.{SHAPES[name]['params'][0]}({args[0]})",
        f"{var} = {name}",
    ]
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which line creates a `{name}` object with {_arg_words(name, args)}?",
        correct=correct,
        distractors=wrong,
        explanation=f"You create an object by calling the class like a function: `{call_text(name, args)}`. The values go to `__init__`.",
        rng=rng,
    )


def _arg_words(name: str, args) -> str:
    params = SHAPES[name]["params"]
    if len(args) == 1:
        return f"a {params[0]} of {args[0]}"
    return f"a {params[0]} of {args[0]} and a {params[1]} of {args[1]}"


@generator(TOPIC, EASY)
def gen_name_the_part(rng: random.Random) -> Question:
    """In `sq1 = Square(5)`, what is sq1 / Square / the value?"""
    name = rng.choice(SHAPE_NAMES)
    args = shape_args(rng, name)
    params = SHAPES[name]["params"]
    var = var_name(name)
    line = f"{var} = {call_text(name, args)}"
    which = rng.choice(["obj", "cls", "arg"])
    if which == "obj":
        prompt = f"In `{line}`, what is `{var}`?"
        correct = f"An object created from the {name} class"
        wrong = [f"The {name} class itself", f"A method of {name}", f"A module named {var}"]
        why = f"`{name}` is the class (the blueprint). `{var}` is an object built from it."
    elif which == "cls":
        prompt = f"In `{line}`, what is `{name}`?"
        correct = "The class (the blueprint)"
        wrong = ["An object", "A method", f"A variable that stores {args[0]}"]
        why = f"`{name}` is the class, the blueprint. `{var}` is the object created from it."
    else:
        if len(args) == 1:
            prompt = f"In `{line}`, what happens to the value {args[0]}?"
            correct = f"It is passed to `__init__` as `{params[0]}`"
        else:
            prompt = f"In `{line}`, what happens to the values {args[0]} and {args[1]}?"
            correct = f"They are passed to `__init__` as `{params[0]}` and `{params[1]}`"
        wrong = ["It becomes the name of the object", "It runs the area() method", "It is how many objects to create"]
        why = "The values in the parentheses are handed to `__init__`, which stores them as attributes of the new object."
    return build_question(
        topic=TOPIC, difficulty=EASY, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


# ==========================================================================
# CHOICE -- MEDIUM (read a short lab-style snippet, spot the classic mistake)
# ==========================================================================


@generator(TOPIC, MEDIUM)
@_retry
def gen_call_form_after_import(rng: random.Random) -> Question:
    """After `import math_tools` vs `from math_tools import add, multiply`: which call works?"""
    fn = rng.choice(list(MATH_TOOLS))
    argtxt = ", ".join(map(str, math_args(rng, fn)))
    if rng.random() < 0.5:
        code = "import math_tools"
        correct = f"math_tools.{fn}({argtxt})"
        wrong = [f"{fn}({argtxt})", f"math_tools({fn}, {argtxt})", f"{fn}.math_tools({argtxt})", f"math_tools({argtxt})"]
        why = f"After `import math_tools` you reach its functions through the module name: `math_tools.{fn}(...)`."
    else:
        other = rng.choice([n for n in MATH_TOOLS if n != fn])
        names = [fn, other]
        rng.shuffle(names)
        code = f"from math_tools import {names[0]}, {names[1]}"
        correct = f"{fn}({argtxt})"
        wrong = [f"math_tools.{fn}({argtxt})", f"{fn}.math_tools({argtxt})", f"math_tools({fn}, {argtxt})"]
        why = f"A selective import gives you the function names directly, without the `math_tools.` prefix: `{fn}(...)`."
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"With this import at the top of main_program.py, which call runs the `{fn}` function?",
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
@_retry
def gen_import_error_why(rng: random.Random) -> Question:
    """Spot the import mistake that raises NameError."""
    f1, f2 = rng.sample(list(MATH_TOOLS), 2)
    a1 = ", ".join(map(str, math_args(rng, f1)))
    a2 = ", ".join(map(str, math_args(rng, f2)))
    kind = rng.choice(["no_module", "no_prefix", "not_imported"])
    if kind == "no_module":
        code = f"from math_tools import {f1}, {f2}\n\nprint(math_tools.{f1}({a1}))"
        correct = f"Only {f1} and {f2} were imported, not math_tools"
        wrong = [
            f"{f1} cannot be imported from a module",
            "print() cannot show an imported function's result",
            "A from-import needs the file name math_tools.py",
        ]
        why = f"`from math_tools import {f1}, {f2}` brings in just those two names, so call `{f1}({a1})` without the prefix."
    elif kind == "no_prefix":
        code = f"import math_tools\n\nprint({f1}({a1}))"
        correct = f"The call needs the prefix: math_tools.{f1}(...)"
        wrong = [
            f"math_tools.py has no function named {f1}",
            "import only works for classes",
            "print() cannot call imported functions",
        ]
        why = f"`import math_tools` imports the whole module, so its functions need the prefix: `math_tools.{f1}({a1})`."
    else:
        code = f"from math_tools import {f1}\n\nprint({f2}({a2}))"
        correct = f"Only {f1} was imported, so {f2} is not defined here"
        wrong = [
            "print has to be imported as well",
            "A from-import only works with the math_tools. prefix",
            f"{f2} is not a real function in math_tools.py",
        ]
        why = f"`from math_tools import {f1}` gives access to only `{f1}`. Import `{f2}` too, or use `import math_tools`."
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="main_program.py raises a `NameError`. Why?",
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
@_retry
def gen_import_trace_values(rng: random.Random) -> Question:
    """The lesson's main_program.py: three prints using math_tools (add, multiply, square)."""
    while True:
        a, b = rng.sample(range(2, 10), 2)
        c = rng.randint(3, 9)
        s, m, q = a + b, a * b, c**2
        if len({s, m, q, c * 2}) == 4:
            break
    prefixed = rng.random() < 0.6
    if prefixed:
        head = "import math_tools"
        calls = [f"math_tools.add({a}, {b})", f"math_tools.multiply({a}, {b})", f"math_tools.square({c})"]
        why_import = "With `import math_tools`, each call uses the `math_tools.` prefix."
    else:
        head = "from math_tools import add, multiply, square"
        calls = [f"add({a}, {b})", f"multiply({a}, {b})", f"square({c})"]
        why_import = "A selective import lets you call the functions without a prefix."
    code = head + "\n\n" + "\n".join(f"print({c_})" for c_ in calls)
    right = [s, m, q]
    options = {
        "right": right,
        "swapped": [m, s, q],
        "star": [s, m, c * 2],
    }
    one_line = " ".join(str(v) for v in right)
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="math_tools.py has `add(a, b)`, `multiply(a, b)` and `square(a)` (which returns `a ** 2`). What does main_program.py print?",
        code=code,
        correct="\n".join(map(str, options["right"])),
        distractors=["\n".join(map(str, options["swapped"])), "\n".join(map(str, options["star"])), one_line],
        explanation=f"{why_import} add({a}, {b}) is {s}, multiply({a}, {b}) is {m} and square({c}) is {c} ** 2 = {q}, each on its own line.",
        rng=rng,
        kind="other",
    )


@generator(TOPIC, MEDIUM)
@_retry
def gen_trace_shape_method(rng: random.Random) -> Question:
    """Trace the lesson's `print("Area:", sq1.area())` for Square / Rectangle / Triangle."""
    name = rng.choice(SHAPE_NAMES)
    method = "area" if name == "Triangle" else rng.choice(["area", "area", "perimeter"])
    args = shape_args(rng, name)
    var = var_name(name)
    code = (
        class_text(name, [method])
        + f"\n\n{var} = {call_text(name, args)}\n"
        + f'print("{TITLE[method]}:", {var}.{method}())'
    )
    d = SHAPES[name]
    a = args[0]
    if name == "Square":
        wrong = [a * 4, a * 2, a, a**3] if method == "area" else [a * a, a * 2, a, a + 4]
    elif name == "Rectangle":
        w, h = args
        wrong = [2 * (w + h), w + h, w * h * 2, w * h + h] if method == "area" else [w * h, w + h, 2 * w + h, w * 2 * h]
    else:
        w, h = args
        wrong = [w * h, (w * h) // 2, w + h, w * h * 2]
    value = method_value(name, method, args)
    why = f"`{method}()` returns `{d[method]}`, which is {value} for `{call_text(name, args)}`."
    if name == "Triangle":
        why += " The `0.5 *` makes the result a float, so it prints with a decimal point."
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[f"{TITLE[method]}: {w_}" for w_ in wrong],
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
@_retry
def gen_method_call_syntax(rng: random.Random) -> Question:
    """Calling a method / reading an attribute on an object."""
    name = rng.choice(SHAPE_NAMES)
    d = SHAPES[name]
    var = var_name(name)
    methods = [m for m in ("area", "perimeter") if m in d]
    if rng.random() < 0.55:
        m = rng.choice(methods)
        prompt = f"Which statement calls the `{m}` method on the object `{var}`?"
        correct = f"{var}.{m}()"
        wrong = [f"{m}({var})", f"{name}.{m}()", f"{var}.{m}", f"{var}({m})"]
        why = f"You call a method on an object with a dot and parentheses: `{var}.{m}()`. Without the parentheses nothing is called."
    else:
        p = rng.choice(d["params"])
        prompt = f"Which expression gives the `{p}` stored in the object `{var}`?"
        correct = f"{var}.{p}"
        wrong = [f"{var}({p})", f"{name}.{p}", f"{p}.{var}", f'{var}["{p}"]']
        why = f"Attributes belong to each object, so you read them with a dot: `{var}.{p}`."
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC, difficulty=MEDIUM, prompt=prompt, correct=correct, distractors=wrong, explanation=why, rng=rng
    )


@generator(TOPIC, MEDIUM)
@_retry
def gen_objects_keep_own_data(rng: random.Random) -> Question:
    """Each object keeps its own attributes (sq1 vs sq2)."""
    s1, s2 = rng.sample([3, 4, 5, 6, 7, 8, 9, 10], 2)
    pool = [
        (
            f"Which statement is true about `sq1 = Square({s1})` and `sq2 = Square({s2})`?",
            "Each object keeps its own `side` value",
            ["Both objects share one `side` value", "`sq2` replaces `sq1`", "`sq1.area()` and `sq2.area()` always return the same number"],
            "Each Square object has its own `side` value, so `sq1` and `sq2` can give different results.",
        ),
        (
            f"After `sq1 = Square({s1})` and `sq2 = Square({s2})`, what is `sq1.side`?",
            str(s1),
            [str(s2), str(s1 + s2), "Error: side is shared"],
            f"`sq1` was created with {s1}, so its own `side` is {s1}. Creating `sq2` does not change `sq1`.",
        ),
        (
            "Why can you create `sq1` and `sq2` from the same class and get different areas?",
            "Each object stores its own data in its own attributes",
            ["The area() method changes every time it is called", "Python picks a random side", "The second object replaces the first one"],
            "The class is one blueprint, but every object built from it keeps its own attribute values.",
        ),
    ]
    return _pool_question(rng, pool, MEDIUM)


@generator(TOPIC, MEDIUM)
@_retry
def gen_two_objects_trace(rng: random.Random) -> Question:
    """Two objects from one class: print both results."""
    name = rng.choice(SHAPE_NAMES)
    method = "area"
    while True:
        a1, a2 = shape_args(rng, name), shape_args(rng, name)
        v1, v2 = method_value(name, method, a1), method_value(name, method, a2)
        if len({v1, v2}) == 2:
            break
    x, y = var_name(name, 1), var_name(name, 2)
    code = (
        class_text(name, [method])
        + f"\n\n{x} = {call_text(name, a1)}\n{y} = {call_text(name, a2)}\n"
        + f"print({x}.{method}(), {y}.{method}())"
    )
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[f"{v2} {v1}", f"{v1} {v1}", f"{v2} {v2}"],
        explanation=f"`{x}` and `{y}` each keep their own attributes, so `{x}.area()` is {v1} and `{y}.area()` is {v2}.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_store_attribute_line(rng: random.Random) -> Question:
    """Which line inside `__init__` makes the object keep its own value?"""
    name = rng.choice(SHAPE_NAMES)
    p = rng.choice(SHAPES[name]["params"])
    wrong = [f"{p} = {p}", f"{p} = self.{p}", f"self.{p} == {p}", f"self = {p}", f"self.{p}({p})"]
    rng.shuffle(wrong)
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Inside `__init__` of the `{name}` class, which line makes the object keep its own `{p}` value?",
        correct=f"self.{p} = {p}",
        distractors=wrong,
        explanation=f"`self.{p} = {p}` stores the value in the object as an attribute. `{p} = {p}` only changes a throw-away local variable.",
        rng=rng,
    )


def _mistake_case(rng: random.Random):
    """(code, distractors, explanation) for a classic class mistake whose result we compute."""
    name = rng.choice(SHAPE_NAMES)
    d = SHAPES[name]
    args = shape_args(rng, name)
    var = var_name(name)
    good = class_text(name, ["area"])
    value = method_value(name, "area", args)
    kind = rng.choice(["no_self", "no_self_attr", "no_args", "init_typo", "no_return"])
    use = f"\n\n{var} = {call_text(name, args)}\nprint({var}.area())"
    if kind == "no_self":
        code = good.replace("def area(self):", "def area():") + use
        wrong = [str(value), error_choice("NameError"), error_choice("AttributeError"), "None"]
        why = "Every method needs `self` as its first parameter. Without it, Python still passes the object in, so the call fails with a TypeError."
    elif kind == "no_self_attr":
        bare = d["area"].replace("self.", "")
        code = good.replace(d["area"], bare) + use
        wrong = [str(value), error_choice("TypeError"), error_choice("AttributeError"), "None"]
        why = f"Inside a method, data must be reached through `self`. `{bare}` uses names that don't exist there, so Python raises a NameError."
    elif kind == "no_args":
        code = good + f"\n\n{var} = {name}()\nprint({var}.area())"
        wrong = [str(value), error_choice("NameError"), error_choice("AttributeError"), "None"]
        why = f"`__init__` needs the values for {', '.join(d['params'])}. Creating `{name}()` without them is a TypeError."
    elif kind == "init_typo":
        code = good.replace("__init__", "_init_") + use
        wrong = [str(value), error_choice("NameError"), error_choice("AttributeError"), "None"]
        why = "The method must be named exactly `__init__` (two underscores on each side) to run automatically. `_init_` is just another method, so `__init__` is missing and the values have nowhere to go."
    else:
        code = good.replace("return ", "") + use
        wrong = [str(value), error_choice("TypeError"), error_choice("NameError"), "0"]
        why = "Without `return`, the method calculates the value but gives nothing back, so `print` shows `None`."
    return code, wrong, why


@generator(TOPIC, MEDIUM)
@_retry
def gen_class_mistake_error(rng: random.Random) -> Question:
    """What happens with the classic class mistakes (missing self, typo in __init__, ...)?"""
    code, wrong, why = _mistake_case(rng)
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        prompt="What does this code print, or which error does it raise?",
        distractors=wrong,
        allow_error=True,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# CHOICE -- HARD (a twist, two steps to trace, or "which class is written correctly")
# ==========================================================================

_SIGNATURES = {
    "add": "def add(a, b):\n    return a + b",
    "multiply": "def multiply(a, b):\n    return a * b",
    "square": "def square(a):\n    return a ** 2",
}


@generator(TOPIC, HARD)
@_retry
def gen_count_methods(rng: random.Random) -> Question:
    """Module-level functions vs methods: how many of the defined functions are methods?"""
    m, k = rng.choice([(2, 2), (1, 3), (1, 2), (2, 1)])
    funcs = rng.sample(list(MATH_TOOLS), m)
    code = "\n\n".join([*(_SIGNATURES[f] for f in funcs), class_text("Square", ["area", "perimeter"][: k - 1])])
    others = [str(m + k), str(m), str(k + 1), str(k - 1), "1", "2", "3", "4"]
    names = [f"`{n}`" for n in ["__init__", "area", "perimeter"][:k]]
    inside = names[0] if k == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    outside = " and ".join(f"`{f}`" for f in funcs)
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="How many of the functions defined in this code are methods?",
        code=code,
        correct=str(k),
        distractors=others,
        explanation=f"A method is a function defined inside a class. Here {inside} {'is' if k == 1 else 'are'} inside `Square`, while {outside} {'is an ordinary function' if m == 1 else 'are ordinary functions'} outside it.",
        rng=rng,
    )


@generator(TOPIC, HARD)
@_retry
def gen_print_vs_return_method(rng: random.Random) -> Question:
    """A method that prints instead of returning: print("Area:", sq1.area()) shows None."""
    name = rng.choice(SHAPE_NAMES)
    method = "area" if name == "Triangle" else rng.choice(["area", "perimeter"])
    args = shape_args(rng, name)
    expr = SHAPES[name][method]
    value = method_value(name, method, args)
    var = var_name(name)
    code = (
        class_text(name, [method]).replace(f"return {expr}", f"print({expr})")
        + f"\n\n{var} = {call_text(name, args)}\n"
        + f'print("{TITLE[method]}:", {var}.{method}())'
    )
    label = TITLE[method]
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[f"{label}: {value}", f"{label}: None", f"{value}", f"{value}\n{label}: {value}"],
        explanation=f"`{method}()` prints {value} itself and returns nothing, so the second `print` shows `None`. Use `return` when you want the value back.",
        rng=rng,
    )


@generator(TOPIC, HARD)
@_retry
def gen_init_runs_each_time(rng: random.Random) -> Question:
    """`__init__` runs automatically for every new object, at the moment it is created."""
    n1, n2 = rng.sample(NAMES, 2)
    hello = rng.choice(["Welcome,", "Hello,", "Ready:", "Joined:"])
    wait = rng.choice(["Waiting...", "Round starts", "Next player", "Please wait"])
    code = (
        f"class Player:\n    def __init__(self, name):\n        print(\"{hello}\", name)\n        self.name = name\n\n"
        f'p1 = Player("{n1}")\nprint("{wait}")\np2 = Player("{n2}")'
    )
    l1, l2 = f"{hello} {n1}", f"{hello} {n2}"
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[f"{wait}\n{l1}\n{l2}", f"{l1}\n{l2}\n{wait}", f"{l1}\n{wait}", f"{wait}"],
        explanation="`__init__` runs automatically every time an object is created, right at that line. So the greeting for the first player prints before the middle line and the second one after it.",
        rng=rng,
    )


@generator(TOPIC, HARD)
@_retry
def gen_cross_file_trace(rng: random.Random) -> Question:
    """shapes.py + main_program.py: trace a program that spans two files."""
    method = rng.choice(["area", "perimeter"])
    other = "perimeter" if method == "area" else "area"
    s1, s2 = sorted(rng.sample([2, 3, 4, 5, 6, 7], 2), reverse=True)
    op = rng.choice(["+", "-"])
    shapes_src = class_text("Square", [method], gap=False)
    shapes_other = class_text("Square", [other], gap=False)
    main_body = f"sq1 = Square({s1})\nsq2 = Square({s2})\nprint(sq1.{method}() {op} sq2.{method}())"
    code = f"# shapes.py\n{shapes_src}\n\n# main_program.py\nfrom shapes import Square\n{main_body}"
    run = run_code(shapes_src + "\n" + main_body)
    if run.error:
        raise GenerationError(f"cross-file trace raised {run.error}")
    v1, v2 = (method_value("Square", method, [s]) for s in (s1, s2))
    w1, w2 = (method_value("Square", other, [s]) for s in (s1, s2))
    combine = (lambda x, y: x + y) if op == "+" else (lambda x, y: x - y)
    if str(combine(v1, v2)) != run.output:
        raise GenerationError("cross-file trace disagrees with arithmetic")
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="shapes.py and main_program.py are in the same folder. What does main_program.py print?",
        code=code,
        correct=run.output,
        distractors=[str(combine(w1, w2)), str(v1), str(v2), str(combine(s1, s2)), str(v1 + v2 if op == '-' else v1 - v2)],
        explanation=f"`from shapes import Square` brings the class into main_program.py. Then `sq1.{method}()` is {v1} and `sq2.{method}()` is {v2}, and {v1} {op} {v2} = {combine(v1, v2)}.",
        rng=rng,
    )


def _break_class(name: str, text: str):
    """Yield (mutation name, broken source) for the classic class-writing slips."""
    d = SHAPES[name]
    first = d["params"][0]
    bad = {
        "no_self_init": text.replace("def __init__(self, ", "def __init__(", 1),
        "not_stored": text.replace(f"self.{first} = {first}", f"{first} = {first}", 1),
        "bare_names": text.replace(d["area"], d["area"].replace("self.", "")),
        "no_self_area": text.replace("def area(self):", "def area():"),
        "init_typo": text.replace("__init__", "_init_"),
        "no_colon": text.replace(f"class {name}:", f"class {name}", 1),
    }
    return bad


@generator(TOPIC, HARD)
@_retry
def gen_pick_correct_class(rng: random.Random) -> Question:
    """Which version of the class is written correctly?"""
    name = rng.choice(SHAPE_NAMES)
    good = class_text(name, ["area"], gap=False)
    bad = _break_class(name, good)
    picks = rng.sample(sorted(bad), 3)
    args = shape_args(rng, name)
    want = method_value(name, "area", args)

    def works(src: str) -> bool:
        ns: dict = {"__name__": "__main__"}
        try:
            exec(compile(src, "<choice>", "exec"), ns)
            return ns[name](*args).area() == want
        except Exception:  # noqa: BLE001 - a broken class is the point
            return False

    if not works(good) or any(works(bad[p]) for p in picks):
        raise GenerationError("class choices are not unambiguous")
    why = {
        "no_self_init": "`__init__` must start with `self`.",
        "not_stored": "Without `self.` the value is never stored in the object.",
        "bare_names": "Inside a method the data must be reached with `self.`.",
        "no_self_area": "Every method, including `area`, needs `self` as its first parameter.",
        "init_typo": "It must be spelled exactly `__init__` to run automatically.",
        "no_colon": "A class line ends with a colon.",
    }
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Which version of the `{name}` class is written correctly?",
        correct=good,
        distractors=[bad[p] for p in picks],
        explanation="Only one version follows the lesson's pattern: `self` in every method, and `self.` to store and read the values. " + " ".join(why[p] for p in picks),
        rng=rng,
    )


@generator(TOPIC, HARD)
@_retry
def gen_change_attribute_trace(rng: random.Random) -> Question:
    """Changing one object's attribute does not touch the other object."""
    name = rng.choice(["Square", "Rectangle"])
    first = SHAPES[name]["params"][0]
    a1 = shape_args(rng, name)
    a2 = list(a1) if rng.random() < 0.5 else shape_args(rng, name)
    which = rng.choice([1, 2])
    new = rng.choice([n for n in range(10, 16) if n not in a1 + a2])
    changed = [new, *(a1 if which == 1 else a2)[1:]]
    x, y = var_name(name, 1), var_name(name, 2)
    code = (
        class_text(name, ["area"])
        + f"\n\n{x} = {call_text(name, a1)}\n{y} = {call_text(name, a2)}\n"
        + f"{var_name(name, which)}.{first} = {new}\nprint({x}.area(), {y}.area())"
    )
    init = [method_value(name, "area", a) for a in (a1, a2)]
    after = [method_value(name, "area", changed if which == 1 else a1), method_value(name, "area", changed if which == 2 else a2)]
    if which == 1:
        both, swapped = f"{after[0]} {after[0]}", f"{after[1]} {after[0]}"
    else:
        both, swapped = f"{after[1]} {after[1]}", f"{after[1]} {after[0]}"
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[both, f"{init[0]} {init[1]}", swapped],
        explanation=f"Only `{var_name(name, which)}` changed: its own `{first}` is now {new}. The other object keeps the value it was created with.",
        rng=rng,
    )


@generator(TOPIC, HARD)
@_retry
def gen_player_score_trace(rng: random.Random) -> Question:
    """A method that updates the object's own attribute; each object keeps its own score."""
    n1, n2 = rng.sample(NAMES, 2)
    pts = rng.sample([50, 100, 150, 200, 250, 500], 3)
    cls = (
        "class Player:\n    def __init__(self, name):\n        self.name = name\n        self.score = 0\n\n"
        "    def add_points(self, points):\n        self.score = self.score + points\n"
    )
    if rng.random() < 0.5:
        calls = [pts[0], pts[1]] + ([pts[2]] if rng.random() < 0.5 else [])
        code = cls + f'\np1 = Player("{n1}")\n' + "\n".join(f"p1.add_points({p})" for p in calls) + "\nprint(p1.name, p1.score)"
        total = sum(calls)
        wrong = [f"{n1} {calls[-1]}", f"{n1} 0", f"{n1} {calls[0]}", f"{n1} {total + calls[0]}"]
        why = f"`__init__` starts the score at 0 and every `add_points` call adds to it, so the score ends at {total}."
    else:
        code = (
            cls
            + f'\np1 = Player("{n1}")\np2 = Player("{n2}")\np1.add_points({pts[0]})\np2.add_points({pts[1]})\np1.add_points({pts[2]})\nprint(p1.score, p2.score)'
        )
        s1, s2 = pts[0] + pts[2], pts[1]
        wrong = [f"{s1 + s2} {s1 + s2}", f"{pts[2]} {pts[1]}", f"{pts[0]} {pts[1]}", f"{s2} {s1}"]
        why = f"Each player has their own score: p1 got {pts[0]} + {pts[2]} = {s1} and p2 got {s2}."
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=wrong, explanation=why, rng=rng
    )


@generator(TOPIC, HARD)
@_retry
def gen_missing_self_attribute(rng: random.Random) -> Question:
    """__init__ that never stores the value on self -> AttributeError later."""
    name = rng.choice(SHAPE_NAMES)
    d = SHAPES[name]
    args = shape_args(rng, name)
    var = var_name(name)
    # forget `self.` for the last parameter
    last = d["params"][-1]
    code = class_text(name, ["area"]).replace(f"self.{last} = {last}", f"{last} = {last}", 1)
    code += f"\n\n{var} = {call_text(name, args)}\nprint({var}.area())"
    value = method_value(name, "area", args)
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        prompt="What does this code print, or which error does it raise?",
        distractors=[str(value), error_choice("TypeError"), error_choice("NameError"), "None"],
        allow_error=True,
        explanation=f"`{last} = {last}` only changes a local variable; without `self.{last} = {last}` the object never stores `{last}`. Later, `self.{last}` doesn't exist: AttributeError.",
        rng=rng,
    )


# ==========================================================================
# BLANKS (fill in the blanks of lesson code)
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_import_module(rng: random.Random) -> Question:
    """`import math_tools` then `math_tools.add(...)`."""
    fn = rng.choice(list(MATH_TOOLS))
    args = math_args(rng, fn)
    argtxt = ", ".join(map(str, args))
    result = math_value(fn, args)
    template = f"{blank_mark(1)} math_tools\n\nprint(math_tools.{blank_mark(2)}({argtxt}))"
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blanks so main_program.py imports the whole module and prints {result}. (math_tools has `add`, `multiply` and `square`.)",
        template=template,
        blanks=[Blank(["import"], hint="keyword"), Blank([fn], hint="function name")],
        explanation=f"`import math_tools` loads the module, then `math_tools.{fn}({argtxt})` calls its `{fn}` function, which gives {result}.",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_from_import(rng: random.Random) -> Question:
    """`from math_tools import add, multiply` -- call without the prefix."""
    fn = rng.choice(list(MATH_TOOLS))
    args = math_args(rng, fn)
    argtxt = ", ".join(map(str, args))
    result = math_value(fn, args)
    template = f"from math_tools {blank_mark(1)} add, multiply, square\n\nprint({blank_mark(2)}({argtxt}))"
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blanks so the program prints {result}. Call the function with no `math_tools.` prefix.",
        template=template,
        blanks=[Blank(["import"], hint="keyword"), Blank([fn], hint="function name")],
        explanation=f"`from math_tools import ...` brings the names in directly, so you call `{fn}({argtxt})` without a prefix.",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_class_header(rng: random.Random) -> Question:
    """class / __init__ / self in the lesson's Square class."""
    name = rng.choice(["Square", "Square", "Rectangle"])
    method = rng.choice(["area", "perimeter"])
    args = shape_args(rng, name)
    var = var_name(name)
    src = class_text(name, [method])
    first_params = ", ".join(["self", *SHAPES[name]["params"]])
    template = (
        src.replace(f"class {name}:", f"{blank_mark(1)} {name}:", 1)
        .replace(f"def __init__({first_params}):", f"def {blank_mark(2)}({first_params}):", 1)
        .replace(f"self.{SHAPES[name]['params'][0]} = ", f"{blank_mark(3)}.{SHAPES[name]['params'][0]} = ", 1)
    )
    template += f"\n\n{var} = {call_text(name, args)}\nprint(\"{TITLE[method]}:\", {var}.{method}())"
    value = method_value(name, method, args)
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks to finish the {name} class so the program prints `{TITLE[method]}: {value}`.",
        template=template,
        blanks=[Blank(["class"], hint="keyword"), Blank(["__init__"], hint="runs automatically"), Blank(["self"], hint="this object")],
        explanation="A class starts with `class`, `__init__` runs automatically when an object is created, and `self` is how a method reaches its own object's data.",
        expect_output=f"{TITLE[method]}: {value}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_create_and_call(rng: random.Random) -> Question:
    """Create the object (`t1 = Triangle(6, 4)`) and call its method (`t1.area()`)."""
    name = rng.choice(SHAPE_NAMES)
    method = "area" if name == "Triangle" else rng.choice(["area", "perimeter"])
    args = shape_args(rng, name)
    var = var_name(name)
    value = method_value(name, method, args)
    template = (
        class_text(name, [method])
        + f"\n\n{var} = {blank_mark(1)}({', '.join(map(str, args))})\nprint(\"{TITLE[method]}:\", {var}.{blank_mark(2)}())"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks to create the object and call its method so the program prints `{TITLE[method]}: {value}`.",
        template=template,
        blanks=[Blank([name], hint="the class"), Blank([method], hint="the method")],
        explanation=f"You create an object by calling the class (`{name}(...)`), then call a method on the object with a dot: `{var}.{method}()`.",
        expect_output=f"{TITLE[method]}: {value}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_attribute_names(rng: random.Random) -> Question:
    """Attribute names in __init__ must match what the method uses (self.width, self.height)."""
    name = rng.choice(["Rectangle", "Triangle"])
    method = "area" if name == "Triangle" else rng.choice(["area", "perimeter"])
    p1, p2 = SHAPES[name]["params"]
    args = shape_args(rng, name)
    var = var_name(name)
    value = method_value(name, method, args)
    template = (
        class_text(name, [method])
        .replace(f"self.{p1} = {p1}", f"self.{blank_mark(1)} = {p1}", 1)
        .replace(f"self.{p2} = {p2}", f"self.{blank_mark(2)} = {p2}", 1)
        + f"\n\n{var} = {call_text(name, args)}\nprint({var}.{blank_mark(3)}())"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the attributes match what the method uses and the program prints {value}.",
        template=template,
        blanks=[Blank([p1], hint="attribute name"), Blank([p2], hint="attribute name"), Blank([method], hint="method name")],
        explanation=f"`__init__` must store the values under the same names the method reads (`self.{p1}` and `self.{p2}`). Then `{var}.{method}()` returns {value}.",
        expect_output=str(value),
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_player_score(rng: random.Random) -> Question:
    """A Player whose methods keep a score: starting value, update and the method call."""
    name = rng.choice(NAMES)
    p1, p2 = rng.sample([50, 100, 150, 250, 500], 2)
    template = (
        "class Player:\n    def __init__(self, name):\n        self.name = name\n"
        f"        self.score = {blank_mark(1)}\n\n"
        f"    def add_points(self, points):\n        self.score = self.score {blank_mark(2)} points\n\n"
        f'p1 = Player("{name}")\np1.{blank_mark(3)}({p1})\np1.add_points({p2})\nprint(p1.name, p1.score)'
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Fill in the blanks so the program prints `{name} {p1 + p2}`.",
        template=template,
        blanks=[
            Blank(["0"], hint="starting score", mode="expr"),
            Blank(["+"], hint="operator"),
            Blank(["add_points"], hint="method name"),
        ],
        explanation=f"`__init__` starts the score at 0, `add_points` adds to this object's own score, and calling `p1.add_points(...)` twice gives {p1} + {p2} = {p1 + p2}.",
        expect_output=f"{name} {p1 + p2}",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_two_files(rng: random.Random) -> Question:
    """shapes.py + main_program.py: the formula and the `from ... import ...` line."""
    name = rng.choice(["Square", "Triangle"])
    method = "perimeter" if name == "Square" and rng.random() < 0.5 else "area"
    args = shape_args(rng, name)
    var = var_name(name)
    value = method_value(name, method, args)
    expr = SHAPES[name][method]
    head, tail = expr.rsplit(" * ", 1)
    blank1 = Blank([tail], hint="finish the formula", mode="expr")
    shapes_src = class_text(name, [method]).replace(f"return {expr}", f"return {head} * {blank_mark(1)}")
    template = (
        f"# shapes.py\n{shapes_src}\n\n# main_program.py\nfrom {blank_mark(2)} import {blank_mark(3)}\n"
        f"{var} = {call_text(name, args)}\nprint(\"{TITLE[method]}:\", {var}.{method}())"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Fill in the blanks so main_program.py prints `{TITLE[method]}: {value}`.",
        template=template,
        blanks=[blank1, Blank(["shapes"], hint="file name, no .py"), Blank([name], hint="the class")],
        explanation=f"The formula finishes as `{expr}`. In main_program.py, `from shapes import {name}` brings the class in from shapes.py.",
    )


# ==========================================================================
# MATCH
# ==========================================================================

_TERMS = [
    ("class", "A blueprint for creating objects"),
    ("object", "Something created from a class"),
    ("method", "A function defined inside a class"),
    ("__init__", "Runs automatically when an object is created"),
    ("self", "The specific object the method works on"),
    ("module", "A Python file you can import"),
    ("attribute", "Data stored inside an object"),
]


@generator(TOPIC, EASY, qtype="match")
def gen_match_terms(rng: random.Random) -> Question:
    """Match the vocabulary of the lesson to its meaning."""
    pairs = rng.sample(_TERMS, rng.choice([4, 5]))
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each term from the lesson to what it means.",
        pairs=pairs,
        explanation="A class is the blueprint, objects are built from it, methods are its functions, `__init__` runs automatically for each new object and `self` is the object itself.",
        rng=rng,
        extra_options=["A loop that repeats code"],
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_import_lines(rng: random.Random) -> Question:
    """Match lines of main_program.py to what they do."""
    fn = rng.choice(["add", "multiply"])
    cls = rng.choice(["Square", "Triangle"])
    args = shape_args(rng, cls)
    pool = [
        ("import math_tools", f"Lets you call math_tools.{fn}(...) with a prefix"),
        (f"from math_tools import {fn}", f"Lets you call {fn}(...) with no prefix"),
        (f"from shapes import {cls}", f"Brings the {cls} class into this file"),
        (f"obj = {call_text(cls, args)}", f"Creates an object from the {cls} class"),
        ("obj.area()", "Calls a method on the object obj"),
    ]
    pairs = rng.sample(pool, rng.choice([4, 5]))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each line of main_program.py to what it does.",
        pairs=pairs,
        explanation="`import module` keeps the prefix, `from module import name` drops it, `from shapes import Class` brings in a class, `Class(...)` makes an object and `obj.method()` calls a method.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_class_parts(rng: random.Random) -> Question:
    """Match each line of the class (and its use) to its role."""
    name = rng.choice(SHAPE_NAMES)
    d = SHAPES[name]
    var = var_name(name)
    args = shape_args(rng, name)
    params = ", ".join(["self", *d["params"]])
    pool = [
        (f"class {name}:", "Starts the class (the blueprint)"),
        (f"def __init__({params}):", "Runs automatically for each new object"),
        (f"self.{d['params'][0]} = {d['params'][0]}", "Stores data in this object"),
        ("def area(self):", "Defines a method"),
        (f"{var} = {call_text(name, args)}", "Creates an object from the class"),
    ]
    pairs = rng.sample(pool, rng.choice([4, 5]))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Match each line of the {name} code to its job.",
        pairs=pairs,
        explanation="The `class` line starts the blueprint, `__init__` runs for each new object, `self.x = x` stores data in the object, `def` inside a class defines a method, and calling the class creates an object.",
        rng=rng,
    )


@generator(TOPIC, HARD, qtype="match")
def gen_match_expression_values(rng: random.Random) -> Question:
    """Evaluate expressions on two Square objects (each keeps its own side)."""
    while True:
        s1, s2 = rng.sample(range(2, 10), 2)
        values = [s1, s2, s1 * s1, s2 * 4, s2 * s2, s1 * 4]
        if len(set(values)) == 6:
            break
    pool = [("sq1.side", s1), ("sq2.side", s2), ("sq1.area()", s1 * s1), ("sq2.perimeter()", s2 * 4), ("sq2.area()", s2 * s2), ("sq1.perimeter()", s1 * 4)]
    pairs = [(e, str(v)) for e, v in rng.sample(pool, rng.choice([4, 5]))]
    code = class_text("Square", ["area", "perimeter"]) + f"\n\nsq1 = Square({s1})\nsq2 = Square({s2})"
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Match each expression to its value.",
        pairs=pairs,
        explanation="Each object keeps its own `side`: `area()` is side times side and `perimeter()` is side times 4, using the object the method is called on.",
        rng=rng,
        code=code,
    )


# ==========================================================================
# CODE (typed Python, graded in the sandbox)
#
# The class questions are graded by a hidden `after=` harness that creates the objects and stores
# what their methods return in variables (`expect_vars`), so a stray test `print` of the player's
# own never causes a false "wrong".  Only the main-program question checks printed output.
# ==========================================================================

JUST_THE_CLASS = " Just define the class: the checker creates the objects and tests them."


def lit(value) -> str:
    """A value as it is written in code (strings with double quotes, like the lessons)."""
    return '"' + value + '"' if isinstance(value, str) else repr(value)


def args_text(args) -> str:
    return ", ".join(lit(a) for a in args)


# ---- Easy -------------------------------------------------------------------------


_MODULE_FUNCS = {
    "add": (["a", "b"], "a + b", "returns the sum of `a` and `b`", lambda a, b: a + b),
    "subtract": (["a", "b"], "a - b", "returns `a` minus `b`", lambda a, b: a - b),
    "multiply": (["a", "b"], "a * b", "returns `a` times `b`", lambda a, b: a * b),
    "square": (["a"], "a ** 2", "returns `a` squared (`a ** 2`)", lambda a: a**2),
    "cube": (["a"], "a ** 3", "returns `a` cubed (`a ** 3`)", lambda a: a**3),
}


@generator(TOPIC, EASY, qtype="code")
def gen_code_module_function(rng: random.Random) -> Question:
    """One function of math_tools.py (add / multiply / square ...)."""
    fn = rng.choice(["add", "multiply", "square", "add", "multiply", "square", "subtract", "cube"])
    params, expr, what, f = _MODULE_FUNCS[fn]
    sig = f"{fn}({', '.join(params)})"
    if len(params) == 2:
        arg_sets = [(1, 2), (0, 5), (-3, 4), *[tuple(rng.sample(range(2, 20), 2)) for _ in range(2)]]
    else:
        arg_sets = [(2,), (0,), (-3,), *[(n,) for n in rng.sample(range(3, 15), 2)]]
    rng.shuffle(arg_sets)
    cases = fn_cases([(a, f(*a)) for a in arg_sets])
    solution = f"def {sig}:\n    return {expr}"
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"math_tools.py is a toolbox of reusable functions. Write the function `{sig}` that {what}.",
        task=function_task(fn, solution, cases),
        explanation=f"Define it with `def`, then `return` the result: `return {expr}`. Other files can then call it with `math_tools.{fn}(...)`.",
    )


_INIT_CLASSES = [
    ("Square", ["side"], [(5,), (3,), (10,), (7,)]),
    ("Rectangle", ["width", "height"], [(4, 6), (3, 8), (10, 2), (5, 5)]),
    ("Triangle", ["base", "height"], [(6, 4), (10, 3), (7, 2), (9, 9)]),
    ("Student", ["name", "grade"], [("Ava", 11), ("Ben", 9), ("Cara", 12), ("Dev", 10)]),
    ("Player", ["name", "score"], [("Eli", 250), ("Fay", 0), ("Gus", 1500), ("Hana", 90)]),
]


@generator(TOPIC, EASY, qtype="code")
def gen_code_class_init(rng: random.Random) -> Question:
    """A class whose `__init__` stores its values as attributes."""
    name, params, pool = rng.choice(_INIT_CLASSES)
    sets = rng.sample(pool, 3) if rng.random() < 0.5 else pool[:3]
    header = f"class {name}:\n    def __init__({', '.join(['self', *params])}):"
    solution = header + "\n" + "\n".join(f"        self.{p} = {p}" for p in params)
    cases = [
        Case(
            label=f"{name}({args_text(a)})",
            after=f"obj = {name}({args_text(a)})\n" + "\n".join(f"{p} = obj.{p}" for p in params),
            expect_vars=dict(zip(params, a)),
        )
        for a in sets
    ]
    param_text = " and ".join(f"`{p}`" for p in params)
    attr_text = " and ".join(f"`self.{p}`" for p in params)
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Write a class `{name}` whose `__init__(self, {', '.join(params)})` stores {param_text} as {attr_text}.{JUST_THE_CLASS}",
        task=program_task(solution, cases, starter=header + "\n        ", examples=2),
        explanation="`__init__` runs automatically when an object is created. Store each value on the object with `self.name = name`, so the object keeps its own data.",
    )


# ---- Medium -----------------------------------------------------------------------


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_shape_methods(rng: random.Random) -> Question:
    """The lesson's Square (or a Rectangle) with area() and perimeter()."""
    name = rng.choice(["Square", "Square", "Rectangle"])
    d = SHAPES[name]
    solution = class_text(name, ["area", "perimeter"])
    sets: list = []
    while len(sets) < 4:
        a = shape_args(rng, name)
        if a not in sets:
            sets.append(a)
    if name == "Square":
        sets[0] = [5]  # the lesson's own example: Area 25, Perimeter 20
    var = var_name(name)
    cases = [
        Case(
            label=call_text(name, a),
            after=f"{var} = {call_text(name, a)}\narea = {var}.area()\nperimeter = {var}.perimeter()",
            expect_vars={"area": method_value(name, "area", a), "perimeter": method_value(name, "perimeter", a)},
        )
        for a in sets
    ]
    params = ", ".join(d["params"])
    if name == "Square":
        how = "`area()` returns `side * side` and `perimeter()` returns `side * 4`"
    else:
        how = "`area()` returns `width * height` and `perimeter()` returns `2 * (width + height)`"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a class `{name}` with `__init__(self, {params})`, an `area()` method and a `perimeter()` method: {how}.{JUST_THE_CLASS}",
        task=program_task(solution, cases, starter=f"class {name}:\n    ", examples=2),
        explanation="Store the values in `__init__` with `self.`, and make both methods `return` their result (using `self.`) instead of printing it.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_triangle_area(rng: random.Random) -> Question:
    """The lesson's Mini Challenge: a Triangle class with base, height and area()."""
    sets = [(4, 3)]
    pool = [(b, h) for b in range(3, 13) for h in range(2, 10) if (4, 3) != (b, h)]
    sets += rng.sample(pool, 2)
    odd = (rng.choice([3, 5, 7, 9]), rng.choice([3, 5, 7]))
    if odd not in sets:
        sets.append(odd)
    cases = [
        Case(
            label=f"Triangle({b}, {h})",
            after=f"t1 = Triangle({b}, {h})\narea = t1.area()",
            expect_vars={"area": 0.5 * b * h},
        )
        for b, h in sets
    ]
    solution = class_text("Triangle", ["area"])
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Mini challenge: write a class `Triangle` with `__init__(self, base, height)` and an `area()` method that returns half of base times height (so `Triangle(4, 3).area()` is `6.0`).{JUST_THE_CLASS}",
        task=program_task(solution, cases, starter="class Triangle:\n    ", examples=2),
        explanation="Store `base` and `height` on the object in `__init__`, then `area()` returns `0.5 * self.base * self.height` (or `self.base * self.height / 2`).",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_module_functions(rng: random.Random) -> Question:
    """Write the whole math_tools.py toolbox (three functions)."""
    names = ["add", "multiply", "square"] if rng.random() < 0.5 else rng.sample(list(_MODULE_FUNCS), 3)
    parts = []
    for fn in names:
        params, expr, _, _ = _MODULE_FUNCS[fn]
        parts.append(f"def {fn}({', '.join(params)}):\n    return {expr}")
    solution = "\n\n".join(parts)
    cases = []
    for _ in range(3):
        a, b = rng.sample(range(2, 12), 2)
        calls, expect = [], {}
        for fn in names:
            params, _, _, f = _MODULE_FUNCS[fn]
            vals = (a, b)[: len(params)]
            calls.append(f"{fn}_result = {fn}({', '.join(map(str, vals))})")
            expect[f"{fn}_result"] = f(*vals)
        label = "; ".join(c.split(" = ", 1)[1] for c in calls)
        cases.append(Case(label=label, after="\n".join(calls), expect_vars=expect))
    sigs = ", ".join(f"`{n}({', '.join(_MODULE_FUNCS[n][0])})`" for n in names)
    what = "; ".join(f"`{n}` {_MODULE_FUNCS[n][2]}" for n in names)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write the contents of math_tools.py: the functions {sigs}. Each one returns its result: {what}.",
        task=program_task(solution, cases, starter="", examples=1),
        explanation="Each function is a normal `def` with a `return`. Other files could then use them with `import math_tools` or `from math_tools import ...`.",
    )


_TEXT_CLASSES = [
    ("Student", ["name", "grade"], "introduce", 'f"{self.name} is in grade {self.grade}"', "`Ava is in grade 11`",
     lambda a: f"{a[0]} is in grade {a[1]}", lambda rng: (rng.choice(NAMES), rng.randint(9, 12))),
    ("Player", ["name", "score"], "summary", 'f"{self.name} has {self.score} points"', "`Ava has 250 points`",
     lambda a: f"{a[0]} has {a[1]} points", lambda rng: (rng.choice(NAMES), rng.choice([0, 50, 100, 250, 500, 1200]))),
    ("Book", ["title", "pages"], "describe", 'f"{self.title} has {self.pages} pages"', "`Python Basics has 120 pages`",
     lambda a: f"{a[0]} has {a[1]} pages", lambda rng: (rng.choice(["Python Basics", "Space Quest", "Code Club", "Pixel Art"]), rng.choice([80, 120, 250, 304]))),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_class_text_method(rng: random.Random) -> Question:
    """A class with a method that RETURNS text built from its attributes."""
    name, params, method, ret, example, fmt, make = rng.choice(_TEXT_CLASSES)
    solution = (
        f"class {name}:\n    def __init__(self, {', '.join(params)}):\n"
        + "\n".join(f"        self.{p} = {p}" for p in params)
        + f"\n\n    def {method}(self):\n        return {ret}"
    )
    sets: list = []
    while len(sets) < 3:
        a = make(rng)
        if a not in sets:
            sets.append(a)
    cases = [
        Case(
            label=f"{name}({args_text(a)}).{method}()",
            after=f"obj = {name}({args_text(a)})\ntext = obj.{method}()",
            expect_vars={"text": fmt(a)},
        )
        for a in sets
    ]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a class `{name}` with `__init__(self, {', '.join(params)})` and a method called `{method}()` that returns text like {example}.{JUST_THE_CLASS}",
        task=program_task(solution, cases, starter=f"class {name}:\n    ", examples=2),
        explanation=f"Store the values with `self.`, then have `{method}()` return an f-string built from `self.{params[0]}` and `self.{params[1]}`. The method returns the text; it does not print it.",
    )


# ---- Hard -------------------------------------------------------------------------


@generator(TOPIC, HARD, qtype="code")
def gen_code_class_with_input(rng: random.Random) -> Question:
    """main_program.py in one box: define the class, read the side(s), create the object, print Area/Perimeter."""
    name = rng.choice(["Square", "Rectangle"])
    var = var_name(name)
    solution = class_text(name, ["area", "perimeter"])
    if name == "Square":
        solution += '\n\nside = int(input("Side: "))\n' + f"{var} = Square(side)"
        stdins = [[str(s)] for s in rng.sample([1, 3, 5, 8, 10, 12], 4)]
        ask = "asks for the side (an `int`)"
        how = "`area()` returns `side * side` and `perimeter()` returns `side * 4`"
    else:
        solution += '\n\nwidth = int(input("Width: "))\nheight = int(input("Height: "))\n' + f"{var} = Rectangle(width, height)"
        stdins = [[str(a), str(b)] for a, b in (rng.sample(range(2, 12), 2) for _ in range(4))]
        ask = "asks for the width and then the height (both `int`s)"
        how = "`area()` returns `width * height` and `perimeter()` returns `2 * (width + height)`"
    solution += f'\nprint("Area:", {var}.area())\nprint("Perimeter:", {var}.perimeter())'
    cases = []
    for s in stdins:
        a = [int(x) for x in s]
        cases.append(Case(stdin=s, out=f"Area: {method_value(name, 'area', a)}\nPerimeter: {method_value(name, 'perimeter', a)}"))
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"Write a class `{name}` (with `__init__`, `area()` and `perimeter()`: {how}). "
            f"Then write the main program: it {ask}, creates a `{name}` object named `{var}` and prints `Area: ...` and `Perimeter: ...` on two lines."
        ),
        task=program_task(
            solution,
            cases,
            starter=f"class {name}:\n    ",
            examples=2,
            requires=[
                (rf"\bclass\s+{name}\b", f"Define a class named {name}."),
                (rf"\b{name}\s*\(", f"Create a {name} object with {name}(...)."),
            ],
        ),
        explanation="Write the class first, then the main logic: read the number(s) with `input()` and cast with `int()`, create the object, and print `Area:` and `Perimeter:` using its methods.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_rectangle_is_square(rng: random.Random) -> Question:
    """Rectangle with area(), perimeter() and is_square() (returns True/False)."""
    squares = rng.sample([(4, 4), (6, 6), (9, 9), (5, 5), (7, 7)], 2)
    wide, tall = rng.choice([(8, 3), (10, 4), (7, 2), (9, 5)]), rng.choice([(3, 5), (2, 7), (4, 9), (5, 6)])
    sets = [squares[0], tall, wide, squares[1]]
    solution = (
        "class Rectangle:\n    def __init__(self, width, height):\n        self.width = width\n        self.height = height\n\n"
        "    def area(self):\n        return self.width * self.height\n\n"
        "    def perimeter(self):\n        return 2 * (self.width + self.height)\n\n"
        "    def is_square(self):\n        return self.width == self.height"
    )
    cases = [
        Case(
            label=f"Rectangle({w}, {h})",
            after=f"r1 = Rectangle({w}, {h})\narea = r1.area()\nperimeter = r1.perimeter()\nsquare = r1.is_square()",
            expect_vars={"area": w * h, "perimeter": 2 * (w + h), "square": w == h},
        )
        for w, h in sets
    ]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            "Write a class `Rectangle` with `__init__(self, width, height)`, `area()` (width times height), "
            "`perimeter()` (`2 * (width + height)`) and `is_square()`, which returns `True` when width and height are equal and `False` otherwise."
            + JUST_THE_CLASS
        ),
        task=program_task(solution, cases, starter="class Rectangle:\n    ", examples=2),
        explanation="`is_square()` can simply return the comparison `self.width == self.height`, which is already `True` or `False`. All three methods use `self.` to reach the object's own data.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_player_rank(rng: random.Random) -> Question:
    """Player class: name, score starting at 0, add_points(points), rank() with Bronze/Silver/Gold."""
    t1, t2 = rng.choice([(1000, 2000), (1000, 2000), (500, 1000), (100, 250), (50, 100)])
    solution = (
        "class Player:\n    def __init__(self, name):\n        self.name = name\n        self.score = 0\n\n"
        "    def add_points(self, points):\n        self.score = self.score + points\n\n"
        f"    def rank(self):\n        if self.score < {t1}:\n            return \"Bronze\"\n        elif self.score < {t2}:\n            return \"Silver\"\n        else:\n            return \"Gold\""
    )

    def rank(score):
        return "Bronze" if score < t1 else "Silver" if score < t2 else "Gold"

    plans = [
        [],  # a new player starts at 0
        [t1 - 1],
        [t1 // 2, t1 - t1 // 2],  # adds up to exactly t1
        [t2 - 1, 1],  # adds up to exactly t2
        [t2, t1],
    ]
    cases = []
    for plan in plans:
        name = rng.choice(NAMES)
        lines = [f'p1 = Player("{name}")'] + [f"p1.add_points({p})" for p in plan] + ["score = p1.score", "rank = p1.rank()"]
        total = sum(plan)
        label = f'Player("{name}")' + "".join(f", add_points({p})" for p in plan)
        cases.append(Case(label=label, after="\n".join(lines), expect_vars={"score": total, "rank": rank(total)}))
    # two players keep separate scores
    n1, n2 = rng.sample(NAMES, 2)
    cases.append(
        Case(
            label=f'Two players: only "{n1}" gets add_points({t2})',
            after=f'p1 = Player("{n1}")\np2 = Player("{n2}")\np1.add_points({t2})\nscore = p1.score\nrank = p1.rank()\nscore2 = p2.score\nrank2 = p2.rank()',
            expect_vars={"score": t2, "rank": "Gold", "score2": 0, "rank2": "Bronze"},
        )
    )
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            "Write a class `Player` with `__init__(self, name)` (store `self.name` and start `self.score` at 0), "
            "`add_points(self, points)` (add the points to the score) and `rank(self)`, which returns "
            f"`\"Bronze\"` if the score is below {t1}, `\"Silver\"` if it is below {t2}, and `\"Gold\"` otherwise.{JUST_THE_CLASS}"
        ),
        task=program_task(solution, cases, starter="class Player:\n    ", examples=2),
        explanation="`__init__` sets the starting score. `add_points` updates this object's own score, and `rank` uses an if / elif / else ladder on `self.score`, checking the lowest threshold first.",
    )
