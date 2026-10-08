"""Question generators for the "functions" topic (CSF.2.L: Functions).

Everything follows the lesson and nothing more: ``def`` and indentation, defining a function does
not run it (you must call it), ``print()`` and ``input()`` are functions too, parameters (the
variables in the parentheses of the ``def`` line) versus arguments (the values you pass when you
call it), ``return`` versus ``print`` (``add(1, 1)`` computes 2 but shows nothing, while
``print("Total:", add(1, 1))`` shows ``Total: 2``), why functions matter, the Mini-Challenge trio
``fahrenheit_to_celsius(f)`` / ``square_area(side)`` / ``average(a, b, c)`` and the Python Bingo
functions (``greet(name)``, ``add(a, b)``, ``is_even(n)``, ``square_list(lst)`` with a loop,
``max_of_three(a, b, c)`` without ``max()``).

Wherever an answer depends on running code it is computed by *running* the snippet
(``output_question`` / ``_out``), and typed code answers are checked by the sandbox against hidden
tests, so the questions are correct by construction.  Nothing here uses default arguments, ``*args``,
lambda, closures, recursion or other ideas the lesson does not teach.
"""

from __future__ import annotations

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

TOPIC = "functions"

# Names and wording copied from the lesson (greet_person("Sarah"), greet_person("Ben"), add(1, 1) ...).
PEOPLE = ["Sarah", "Ben", "Ava", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon", "Sam", "Ada"]
GREET_FUNCS = ["greet_person", "greet_person", "greet_player", "greet_student", "welcome_player"]
NO_ARG_FUNCS = [
    ("greet", "Hello world"),
    ("greet", "Hello world"),
    ("say_hi", "Hi there!"),
    ("start_game", "Game on!"),
    ("show_menu", "Main menu"),
    ("welcome", "Welcome to class"),
    ("say_goodbye", "Goodbye!"),
    ("show_score", "Score: 100"),
    ("show_title", "Python Quest"),
    ("start_level", "Level 1 begins"),
]
# "NAME" marks where the player's name goes (turned into {name} inside an f-string).
GREETINGS = ["Hello, NAME", "Hello, NAME", "Welcome, NAME!", "Hi NAME", "Hey NAME, ready?"]
# (function name, return expression) -- the lesson's add(a, b) and math_tools' multiply(a, b).
MATH = [("add", "a + b"), ("add", "a + b"), ("multiply", "a * b"), ("subtract", "a - b")]

PARAM_DEF = "A variable in the parentheses of the def line"
ARG_DEF = "A value you pass in when you call the function"


def _fmt(template: str, name: str) -> str:
    """Greeting text for one person."""
    return template.replace("NAME", name)


def _fstr(template: str) -> str:
    """The f-string source for a greeting template, e.g. f"Hello, {name}"."""
    return 'f"' + template.replace("NAME", "{name}") + '"'


def _out(code: str) -> str:
    """What a snippet prints (as an answer choice): output, nothing, or the error it raises."""
    res = run_code(code.strip("\n"))
    return error_choice(res.error) if res.error else display_output(res.output)


def _apply(expr: str, **names) -> object:
    """Evaluate one of our own tiny arithmetic expressions."""
    return eval(expr, {"__builtins__": {}}, names)


def _two_ints(rng: random.Random) -> tuple[int, int]:
    a, b = rng.sample(range(2, 10), 2)
    return a, b


def _triple_div3(rng: random.Random, lo: int, hi: int) -> tuple[int, int, int]:
    """Three distinct numbers whose sum is a multiple of 3 (so their average prints tidily)."""
    while True:
        t = tuple(rng.sample(range(lo, hi), 3))
        if sum(t) % 3 == 0:
            return t  # type: ignore[return-value]


# ==========================================================================
# CHOICE -- EASY (vocabulary and one-line results, like the Canvas quiz)
# ==========================================================================


@generator(TOPIC, EASY)
def gen_def_keyword(rng: random.Random) -> Question:
    """Which keyword defines a function? (concept wording, or read it off a snippet)"""
    if rng.random() < 0.5:
        fn, msg = rng.choice(NO_ARG_FUNCS)
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt="In this code, which keyword tells Python you are defining a function?",
            code=f'def {fn}():\n    print("{msg}")',
            correct="def",
            distractors=[fn, "print", rng.choice(["function", "define", "func"])],
            explanation="You use the keyword `def` to define a function. The name after it (and `print`) are not keywords for defining.",
            rng=rng,
        )
    prompt = rng.choice(
        [
            "Which keyword is used to define a function in Python?",
            "A function definition starts with which keyword?",
            "Which keyword do you use to create your own function?",
        ]
    )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct="def",
        distractors=rng.sample(["function", "func", "define", "fun", "create", "make"], 3),
        explanation="Use the keyword `def` to define a function, for example `def greet():`.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_parameter_or_argument(rng: random.Random) -> Question:
    """Parameter vs argument, with the lesson's exact definitions or a greet_person snippet."""
    fn = rng.choice(GREET_FUNCS)
    person = rng.choice(PEOPLE)
    code = f'def {fn}(name):\n    print(f"Hello, {{name}}")\n\n{fn}("{person}")'
    kind = rng.choice(["param_code", "arg_code", "param_def", "arg_def"])
    other = ["A return value", "The function's name"]
    if kind == "param_code":
        prompt, correct, wrong, shown = f"In `def {fn}(name):`, what is `name`?", "A parameter", ["An argument", *other], code
    elif kind == "arg_code":
        prompt, correct, wrong, shown = f'In the call `{fn}("{person}")`, what is `"{person}"`?', "An argument", ["A parameter", *other], code
    elif kind == "param_def":
        prompt, correct, shown = "Which statement describes a parameter?", PARAM_DEF, None
        wrong = [ARG_DEF, "The value a function sends back with `return`", "The name that comes right after `def`"]
    else:
        prompt, correct, shown = "Which statement describes an argument?", ARG_DEF, None
        wrong = [PARAM_DEF, "The value a function sends back with `return`", "The name that comes right after `def`"]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation="A parameter is the variable inside the parentheses when you define the function; an argument is the value you pass in when you call it.",
        rng=rng,
        code=shown,
    )


@generator(TOPIC, EASY)
def gen_defining_does_not_run(rng: random.Random) -> Question:
    """'Just defining it won't make it run -- you must call it.'"""
    fn, msg = rng.choice(NO_ARG_FUNCS)
    called = rng.random() < 0.35
    code = f'def {fn}():\n    print("{msg}")'
    if called:
        return output_question(
            topic=TOPIC,
            difficulty=EASY,
            code=code + f"\n\n{fn}()",
            distractors=[NOTHING_PRINTED, f"{msg}\n{msg}", fn, error_choice("NameError")],
            explanation=f"`def` only defines the function. The call `{fn}()` is what runs it, so the message is printed once.",
            rng=rng,
        )
    return output_question(
        topic=TOPIC,
        difficulty=EASY,
        code=code,
        distractors=[msg, fn, error_choice("NameError"), f"{fn}()"],
        explanation=f"Defining a function does not run it. Nothing happens until you call it with `{fn}()`.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_return_concept(rng: random.Random) -> Question:
    """What does `return` do? ('Return sends the value back to wherever the function was called.')"""
    prompt = rng.choice(
        [
            "What does `return` do in a function?",
            "Which statement is true about `return`?",
            "What happens to a value that a function gives to `return`?",
        ]
    )
    fn, expr = rng.choice(MATH)
    code = f"def {fn}(a, b):\n    return {expr}" if rng.random() < 0.5 else None
    correct = rng.choice(
        [
            "It sends a value back to wherever the function was called",
            "It gives the result back to the code that called it",
        ]
    )
    wrong = rng.sample(
        [
            "It prints the value on the screen",
            "It makes the function run",
            "It defines a new function",
            "It asks the user to type a value",
            "It repeats the function's code",
        ],
        3,
    )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation="`return` sends the value back to wherever the function was called. It does not print anything by itself.",
        rng=rng,
        code=code,
    )


@generator(TOPIC, EASY)
def gen_print_input_are_functions(rng: random.Random) -> Question:
    """'print() and input() are functions too' (already defined in the background)."""
    if rng.random() < 0.5:
        name = rng.choice(["print", "input"])
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt=f"Which statement is true about `{name}()`?",
            correct="It is a function that Python already defined for us",
            distractors=rng.sample(
                [
                    "It is a keyword, like `def` and `return`",
                    "It is not a function because we never wrote `def` for it",
                    "It only works after you define it with `def`",
                    "It is a variable that stores text",
                ],
                3,
            ),
            explanation="`print()` and `input()` are functions we have used all along. They were already defined in the background, just like the functions we write ourselves.",
            rng=rng,
        )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Which of these is a function we have already used?",
        correct=rng.choice(["print()", "input()"]),
        distractors=rng.sample(["def", "return", "while", "if", "for"], 3),
        explanation="`print()` and `input()` are functions that were already defined for us. `def`, `return`, `if`, `while` and `for` are keywords, not functions.",
        rng=rng,
    )


_BENEFITS = [
    "You can reuse code just by calling the function again",
    "They keep a program more organized",
    "Write the steps once, call them whenever you need them",
    "They make code more reusable",
]
_NOT_BENEFITS = [
    "They are the only way to print text on the screen",
    "Python will not run a program unless it has a function",
    "They let you skip using variables",
    "They change a value's data type automatically",
    "They make every line of the program run twice",
]


@generator(TOPIC, EASY)
def gen_why_functions(rng: random.Random) -> Question:
    """'Why functions matter': organized, efficient, reusable."""
    prompt = rng.choice(
        [
            "Which is a reason to use functions?",
            "Why do programmers write functions?",
            "Which statement about why functions matter is true?",
        ]
    )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=rng.choice(_BENEFITS),
        distractors=rng.sample(_NOT_BENEFITS, 3),
        explanation="Functions make programs more organized, more efficient and more reusable: write the code once, then call it whenever you need it.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_indentation_concept(rng: random.Random) -> Question:
    """'Indent the code inside the function.'"""
    fn, msg = rng.choice(NO_ARG_FUNCS)
    prompt = rng.choice(
        [
            "How does Python know which lines belong inside a function?",
            "Which statement about the code inside a function is true?",
            "How do you show that a line is part of a function?",
        ]
    )
    code = f'def {fn}():\n    print("{msg}")' if rng.random() < 0.5 else None
    correct = rng.choice(
        [
            "The lines are indented under the `def` line",
            "They are indented below the `def` line",
        ]
    )
    wrong = rng.sample(
        [
            "The lines are written inside quotes",
            "Each line ends with a semicolon",
            "The lines start with the word `body`",
            "The lines come after the word `return`",
            "The lines are written in capital letters",
        ],
        3,
    )
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation="Indent the code inside the function (4 spaces). The indented lines are the function's body, and they only run when the function is called.",
        rng=rng,
        code=code,
    )


_DEF_LINES = [
    ("greet_person", "name"),
    ("greet_person", "name"),
    ("square_area", "side"),
    ("add", "a, b"),
    ("average", "a, b, c"),
    ("is_even", "n"),
    ("fahrenheit_to_celsius", "f"),
]


@generator(TOPIC, EASY)
def gen_def_line(rng: random.Random) -> Question:
    """Which line correctly starts the function? (colon, def, parentheses)"""
    fn, params = rng.choice(_DEF_LINES)
    many = "," in params
    prompt = f"Which line correctly starts a function named `{fn}` with the parameter{'s' if many else ''} `{params}`?"
    pool = [
        f"def {fn}({params})",
        f"function {fn}({params}):",
        f"def {fn}[{params}]:",
        f"{fn}({params}):",
        f"def {params}({fn}):",
    ]
    wrong = [pool[0], *rng.sample(pool[1:], 2)]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=f"def {fn}({params}):",
        distractors=wrong,
        explanation="A definition is `def`, the function name, the parameters in parentheses, and a colon at the end. The indented lines below it are the body.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_call_result_simple(rng: random.Random) -> Question:
    """One-line result: what does print(add(2, 3)) show?"""
    fn, expr = rng.choice(MATH)
    a, b = _two_ints(rng)
    right = _apply(expr, a=a, b=b)
    wrong = [str(_apply(e, a=a, b=b)) for e in ("a + b", "a * b", "a - b", "b - a")] + [f"{a}{b}"]
    code = f"def {fn}(a, b):\n    return {expr}\n\nprint({fn}({a}, {b}))"
    return output_question(
        topic=TOPIC,
        difficulty=EASY,
        code=code,
        distractors=[w for w in wrong if w != str(right)],
        explanation=f"The arguments {a} and {b} go into `a` and `b`, `return {expr}` sends {right} back, and `print` shows it.",
        rng=rng,
    )


# ==========================================================================
# CHOICE -- MEDIUM (trace a short lab-style snippet, spot the classic mistake)
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_call_without_print(rng: random.Random) -> Question:
    """The lesson's `add(1, 1)`: it computes the result but does not show it."""
    fn, expr = rng.choice(MATH)
    a, b = _two_ints(rng)
    right = _apply(expr, a=a, b=b)
    stored = rng.random() < 0.4
    call = f"{fn}({a}, {b})"
    code = f"def {fn}(a, b):\n    return {expr}\n\n" + (f"result = {call}" if stored else call)
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[str(right), f"Total: {right}", call, error_choice("NameError")],
        explanation=f"`{fn}({a}, {b})` computes {right}, but nothing prints it"
        + (" (it is only stored in `result`)." if stored else " (the value is just thrown away).")
        + " To see it, use `print(...)`.",
        rng=rng,
    )


_LABELS = ["Total:", "Total:", "Sum:", "Result:", "Answer:"]


@generator(TOPIC, MEDIUM)
def gen_print_label_total(rng: random.Random) -> Question:
    """The lesson's `print("Total:", add(1, 1))` -> `Total: 2`."""
    fn, expr = rng.choice(MATH[:3])
    a, b = _two_ints(rng)
    right = _apply(expr, a=a, b=b)
    label = rng.choice(_LABELS)
    call = f"{fn}({a}, {b})"
    if rng.random() < 0.5:
        tail = f'print("{label}", {call})'
    else:
        tail = f"value = {call}\nprint(\"{label}\", value)"
    code = f"def {fn}(a, b):\n    return {expr}\n\n{tail}"
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[f"{label} {call}", str(right), f"{label}{right}", f"{label} {a}{b}"],
        explanation=f"The call gives back {right}, and `print` joins the label and the value with a space: `{label} {right}`.",
        rng=rng,
    )


_PRINT_RETURN_PAIRS = [
    ("show_total", "get_total", "a + b"),
    ("show_total", "get_total", "a + b"),
    ("show_product", "get_product", "a * b"),
    ("show_sum", "get_sum", "a + b"),
]


@generator(TOPIC, MEDIUM)
def gen_print_vs_return_two_functions(rng: random.Random) -> Question:
    """One function prints its answer, the other returns it: only the printing one shows anything."""
    show, get, expr = rng.choice(_PRINT_RETURN_PAIRS)
    for _ in range(20):
        (a1, b1), (a2, b2) = _two_ints(rng), _two_ints(rng)
        shown, kept = _apply(expr, a=a1, b=b1), _apply(expr, a=a2, b=b2)
        if shown != kept:
            break
    else:
        raise GenerationError("same value")
    calls = [f"{show}({a1}, {b1})", f"{get}({a2}, {b2})"]
    if rng.random() < 0.5:
        calls.reverse()
    code = f"def {show}(a, b):\n    print({expr})\n\ndef {get}(a, b):\n    return {expr}\n\n" + "\n".join(calls)
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[str(kept), f"{shown}\n{kept}", f"{kept}\n{shown}", NOTHING_PRINTED],
        explanation=f"`{show}` prints {shown} itself. `{get}` only returns {kept} to the caller, and since nobody prints it, nothing is shown.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_trace_two_calls(rng: random.Random) -> Question:
    """greet_person("Sarah") then greet_person("Ben"): the argument fills the parameter each time."""
    fn = rng.choice(GREET_FUNCS)
    tmpl = rng.choice(GREETINGS)
    first, second = rng.sample(PEOPLE, 2)
    code = f'def {fn}(name):\n    print({_fstr(tmpl)})\n\n{fn}("{first}")\n{fn}("{second}")'
    lit = _fmt(tmpl, "name")
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[
            f"{_fmt(tmpl, second)}\n{_fmt(tmpl, first)}",
            f"{lit}\n{lit}",
            _fmt(tmpl, first),
            f"{_fmt(tmpl, first)}\n{_fmt(tmpl, first)}",
        ],
        explanation=f"Each call runs the body again with a new argument: `name` is \"{first}\" the first time and \"{second}\" the second time.",
        rng=rng,
    )


_SEQUENCES = [("Start", "Middle", "End"), ("Ready", "Set", "Go!"), ("Loading...", "Almost there", "Done")]


@generator(TOPIC, MEDIUM)
def gen_trace_define_then_call(rng: random.Random) -> Question:
    """Order of execution: the def line only stores the function; the call runs the body."""
    fn, msg = rng.choice(NO_ARG_FUNCS)
    l1, l2, l3 = rng.choice(_SEQUENCES)
    twice = rng.random() < 0.4
    calls = f"{fn}()\n{fn}()" if twice else f"{fn}()"
    code = f'print("{l1}")\n\ndef {fn}():\n    print("{msg}")\n\nprint("{l2}")\n{calls}\nprint("{l3}")'
    if twice:
        wrong = [
            [l1, l2, msg, l3],
            [l1, msg, l2, msg, msg, l3],
            [l1, msg, msg, l2, l3],
            [l1, l2, l3],
        ]
    else:
        wrong = [
            [l1, msg, l2, msg, l3],
            [l1, l2, l3],
            [l1, msg, l2, l3],
            [msg, l1, l2, l3],
        ]
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=["\n".join(w) for w in wrong],
        explanation=f"Python runs top to bottom. The `def` line does not print anything; `{fn}()` runs the body "
        + ("each time it is called." if twice else "at the moment it is called, between the other prints."),
        rng=rng,
    )


# Plausible-sounding but false reasons, per kind of bug (so every wrong choice is really wrong for that code).
_FALSE_REASONS = {
    "never_called": [
        "The function needs a `return` to show anything",
        "`print()` can't be used inside a function",
        "The message must be written as an f-string",
        "The function needs a parameter before it can print",
    ],
    "not_printed": [
        "`return` can't be used with two parameters",
        "The call needs the word `call` in front of it",
        "The function should be defined after the call",
        "The arguments must be written inside quotes",
    ],
    "arg_count": [
        "The function should use `print` instead of `return`",
        "`return` can't be used with two parameters",
        "The call has to be written before the `def` line",
        "Numbers can't be passed as arguments",
    ],
    "typo": [
        "The `def` line is missing a parameter",
        "`print()` can't be used inside a function",
        "The argument must not be written in quotes",
        "The function needs a `return` to show anything",
    ],
    "text_plus": [
        "The function is missing the `def` keyword",
        "The function has to be called twice",
        "`print()` can't be given a function call",
        "The arguments must be written inside quotes",
    ],
    "colon": [
        "The function name can't contain an underscore",
        "The parameter must be written inside quotes",
        "`def` has to be followed by the word `function`",
        "The line must end with a semicolon",
    ],
}


@generator(TOPIC, MEDIUM)
def gen_spot_the_bug(rng: random.Random) -> Question:
    """Classic function mistakes: never called, result never printed, wrong number of arguments,
    a misspelled call, `+` with text, a missing colon."""
    fn = rng.choice(GREET_FUNCS)
    math, expr = rng.choice(MATH[:3])
    scenario = rng.choice(list(_FALSE_REASONS))
    related: list[str] = []
    if scenario == "never_called":
        name, msg = rng.choice(NO_ARG_FUNCS)
        prompt = "Nothing appears on the screen when this code runs. What is the problem?"
        code = f'def {name}():\n    print("{msg}")'
        right = "The function is defined but never called"
        why = f"`def` only defines `{name}`. Add the call `{name}()` to run it."
        related = ["It is missing the colon (:) at the end"]
    elif scenario == "not_printed":
        prompt = "Nothing appears on the screen when this code runs. What is the problem?"
        a, b = _two_ints(rng)
        code = f"def {math}(a, b):\n    return {expr}\n\n{math}({a}, {b})"
        right = f"`{math}({a}, {b})` returns a value, but nothing prints it"
        why = f"The call computes {_apply(expr, a=a, b=b)} but does not show it. Use `print({math}({a}, {b}))`."
        related = ["It is missing the colon (:) at the end"]
    elif scenario == "arg_count":
        prompt = "This code raises a `TypeError`. What is the problem?"
        a = rng.randint(2, 9)
        code = f"def {math}(a, b):\n    return {expr}\n\nprint({math}({a}))"
        right = f"`{math}` needs two arguments but only one was passed"
        why = f"`{math}` has two parameters, so every call must give two arguments."
        related = [f"`{math}({a})` returns a value, but nothing prints it"]
    elif scenario == "typo":
        typo = fn.replace("er", "e", 1) if "er" in fn else fn[:-1]
        prompt = f"Python reports `name '{typo}' is not defined`. What is the problem?"
        code = f'def {fn}(name):\n    print(f"Hello, {{name}}")\n\n{typo}("{rng.choice(PEOPLE)}")'
        right = "The call uses a different name than the `def` line"
        why = f"The function is `{fn}`, but the call says `{typo}`. Python can't find a function with that name."
        related = ["It is missing the colon (:) at the end"]
    elif scenario == "text_plus":
        label = rng.choice(["Total: ", "Sum: ", "Result: "])
        a, b = _two_ints(rng)
        prompt = "This code raises a `TypeError`. What is the problem?"
        code = f'def {math}(a, b):\n    return {expr}\n\nprint("{label}" + {math}({a}, {b}))'
        right = "A number can't be joined to text with `+`"
        why = f'`{math}({a}, {b})` returns a number, so `"{label}" + ...` mixes text and a number. Use `print("{label.strip()}", {math}({a}, {b}))`.'
        related = [f"`{math}` needs two arguments but only one was passed"]
    else:
        prompt = f"What is wrong with the line `def {fn}(name)`?"
        code = None
        right = "It is missing the colon (:) at the end"
        why = "Every `def` line must end with a colon `:`; the indented body follows on the next lines."
    wrong = [*related[:1], *rng.sample(_FALSE_REASONS[scenario], 3)]
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        correct=right,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=code,
    )


@generator(TOPIC, MEDIUM)
def gen_which_line_shows(rng: random.Random) -> Question:
    """Which statement shows `Total: 2` on the screen? (verified by running every choice)"""
    fn, expr = rng.choice(MATH[:3])
    a, b = _two_ints(rng)
    label = rng.choice(_LABELS)
    call = f"{fn}({a}, {b})"
    setup = f"def {fn}(a, b):\n    return {expr}"
    target = f"{label} {_apply(expr, a=a, b=b)}"
    right = f'print("{label}", {call})'
    candidates = [
        call,
        f'print("{label}" + {call})',
        f'print("{label} {call}")',
        f'print({call}, "{label}")',
        f"total = {call}",
    ]
    wrong = []
    for cand in candidates:
        res = run_code(f"{setup}\n{cand}")
        if res.error is None and res.output == target:
            continue
        wrong.append(cand)
    if _out(f"{setup}\n{right}") != target:
        raise GenerationError("right answer does not print the target")
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Which line shows `{target}` on the screen?",
        code=setup,
        correct=right,
        distractors=wrong,
        explanation=f"`{call}` on its own computes the value but shows nothing. Put the call inside `print(...)` with the label to display `{target}`.",
        rng=rng,
    )


# The Mini-Challenge trio.  (function, parameters, correct return expr, wrong exprs, example args)
_LAB = [
    (
        "fahrenheit_to_celsius",
        "f",
        "(f - 32) * 5 / 9",
        ["f - 32 * 5 / 9", "(f - 32) * 9 / 5", "(f + 32) * 5 / 9", "(f - 32) / 5 * 9"],
        [(212,), (50,), (86,), (68,), (104,)],
        "returns the temperature in Celsius",
    ),
    (
        "square_area",
        "side",
        "side * side",
        ["side + side", "side * 4", "side * 2", "side"],
        [(3,), (5,), (6,), (7,)],
        "returns the area of a square",
    ),
    (
        "average",
        "a, b, c",
        "(a + b + c) / 3",
        ["a + b + c / 3", "(a + b + c) / 2", "a + b + c", "(a + b + c) * 3"],
        [(2, 4, 9), (3, 6, 9), (1, 5, 6), (4, 5, 9)],
        "returns the average of the three numbers",
    ),
]


def _lab_value(fn: str, params: str, expr: str, args: tuple) -> object:
    """What ``fn(*args)`` returns when its body is ``return <expr>``."""
    call = f"{fn}({', '.join(repr(x) for x in args)})"
    res = run_code(f"def {fn}({params}):\n    return {expr}\n\nresult = {call}")
    return res.namespace.get("result")


@generator(TOPIC, MEDIUM)
def gen_complete_lab_function(rng: random.Random) -> Question:
    """Mini-Challenge: which return line completes fahrenheit_to_celsius / square_area / average?"""
    fn, params, expr, wrong_exprs, examples, what = rng.choice(_LAB)
    args = rng.choice(examples)
    want = _lab_value(fn, params, expr, args)
    call = f"{fn}({', '.join(repr(x) for x in args)})"
    wrong = []
    for w in wrong_exprs:
        if _lab_value(fn, params, w, args) != want:
            wrong.append(f"return {w}")
    wrong.insert(1, f"print({expr})")
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Complete `def {fn}({params}):` with the line that makes `{call}` return `{want}`.",
        correct=f"return {expr}",
        distractors=wrong,
        explanation=f"`{fn}` {what}, so its last line must `return` the formula `{expr}`. "
        + ("Watch the parentheses: the sum must be divided as a whole." if fn == "average" else "`print(...)` would show a value but not give it back."),
        rng=rng,
    )


# (function, parameters, return expression, label, argument tuples, buggy expression)
_LAB_CALLS = [
    ("fahrenheit_to_celsius", "f", "(f - 32) * 5 / 9", "Celsius:", [(212,), (50,), (86,), (68,), (104,)], "f - 32 * 5 / 9"),
    ("square_area", "side", "side * side", "Area:", [(3,), (4,), (5,), (6,), (9,)], "side + side"),
    ("average", "a, b, c", "(a + b + c) / 3", "Average:", [(2, 4, 9), (3, 6, 9), (1, 5, 6), (4, 5, 9)], "a + b + c / 3"),
]


@generator(TOPIC, MEDIUM)
def gen_trace_lab_calls(rng: random.Random) -> Question:
    """Mini-Challenge: 'call each one and print the results' -- two lab functions, two labelled prints."""
    first, second = rng.sample(_LAB_CALLS, 2)
    defs = "\n\n".join(f"def {fn}({ps}):\n    return {ex}" for fn, ps, ex, *_ in (first, second))
    order = [first, second]
    rng.shuffle(order)
    picked = [(entry, rng.choice(entry[4])) for entry in order]
    prints = []
    values = []
    wrong_vals = []
    for (fn, ps, ex, label, _args, bad), args in picked:
        call = f"{fn}({', '.join(map(str, args))})"
        prints.append(f'print("{label}", {call})')
        values.append(_lab_value(fn, ps, ex, args))
        wrong_vals.append(_lab_value(fn, ps, bad, args))
    labels = [p[0][3] for p in picked]
    right = [f"{lab} {v}" for lab, v in zip(labels, values)]
    as_int = [f"{lab} {int(v)}" if isinstance(v, float) and v == int(v) else r for lab, v, r in zip(labels, values, right)]
    wrong = [
        "\n".join(as_int),
        f"{labels[0]} {wrong_vals[0]}\n{right[1]}",
        f"{right[0]}\n{labels[1]} {wrong_vals[1]}",
        "\n".join(right[::-1]),
        right[0],
        right[1],
    ]
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=defs + "\n\n" + "\n".join(prints),
        distractors=wrong,
        explanation="Each call returns a value that `print` shows after its label. Dividing with `/` always gives a float, so a whole-number result still prints with `.0` (like `5.0`).",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_argument_order(rng: random.Random) -> Question:
    """Arguments fill the parameters in order: subtract(10, 3) is not subtract(3, 10)."""
    if rng.random() < 0.5:
        a, b = rng.sample(range(2, 12), 2)
        code = f"def subtract(a, b):\n    return a - b\n\nprint(subtract({a}, {b}))\nprint(subtract({b}, {a}))"
        d = a - b
        return output_question(
            topic=TOPIC,
            difficulty=MEDIUM,
            code=code,
            distractors=[f"{d}\n{d}", f"{abs(d)}\n{abs(d)}", f"{-d}\n{d}", f"{a + b}\n{a + b}"],
            explanation=f"The first argument goes into `a` and the second into `b`, so the order matters: {a} - {b} is {d}, but {b} - {a} is {-d}.",
            rng=rng,
        )
    person = rng.choice(PEOPLE)
    age = rng.randint(12, 18)
    code = f'def describe(name, age):\n    print(f"{{name}} is {{age}} years old")\n\ndescribe({age}, "{person}")'
    return output_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        code=code,
        distractors=[f"{person} is {age} years old", f"{age} is {age} years old", "name is age years old", error_choice("TypeError")],
        explanation="Arguments are matched to parameters by position. The first argument fills `name` and the second fills `age`, even when they are in the wrong order.",
        rng=rng,
    )


# ==========================================================================
# CHOICE -- HARD (a twist or two steps to trace; lab-style snippets)
# ==========================================================================

_NOISY = [
    ("add", "Adding...", "a + b", "Total:"),
    ("add", "Adding...", "a + b", "Total:"),
    ("multiply", "Multiplying...", "a * b", "Product:"),
]


@generator(TOPIC, HARD)
def gen_print_inside_and_return(rng: random.Random) -> Question:
    """A function that prints AND returns: the inner print runs first, then the outer print shows the value."""
    fn, msg, expr, label = rng.choice(_NOISY)
    variant = rng.choice(["inline", "stored", "two"])
    (a, b), (c, d) = _two_ints(rng), _two_ints(rng)
    head = f'def {fn}(a, b):\n    print("{msg}")\n    return {expr}\n\n'
    r1, r2 = _apply(expr, a=a, b=b), _apply(expr, a=c, b=d)
    if variant == "inline":
        code = head + f'print("{label}", {fn}({a}, {b}))'
        wrong = [f"{label} {r1}\n{msg}", f"{label} {r1}", msg, f"{msg}\n{r1}"]
        why = f"Python must call `{fn}({a}, {b})` before it can print, so `{msg}` appears first. Then `print` shows `{label} {r1}`."
    elif variant == "stored":
        code = head + f'result = {fn}({a}, {b})\nprint("{label}", result)'
        wrong = [f"{label} {r1}\n{msg}", f"{label} {r1}", msg, f"{msg}\n{r1}"]
        why = f"The call runs first and prints `{msg}`; its return value {r1} is stored in `result`, then `print` shows `{label} {r1}`."
    else:
        joiner = "+" if expr == "a + b" else "*"
        both = r1 + r2 if joiner == "+" else r1 * r2
        code = head + f'first = {fn}({a}, {b})\nsecond = {fn}({c}, {d})\nprint("{label}", first {joiner} second)'
        wrong = [
            f"{label} {both}\n{msg}\n{msg}",
            f"{msg}\n{label} {both}",
            f"{label} {both}",
            f"{msg}\n{msg}\n{both}",
        ]
        why = f"`{fn}` runs twice and prints `{msg}` each time. Only then does `print` show `{label} {both}`."
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


_BOOL_FUNCS = [
    ("is_even", "n % 2 == 0"),
    ("is_even", "n % 2 == 0"),
    ("is_odd", "n % 2 == 1"),
    ("is_multiple_of_five", "n % 5 == 0"),
]


@generator(TOPIC, HARD)
def gen_trace_bool_function(rng: random.Random) -> Question:
    """Bingo `is_even(n)`: trace an if + return True / return False function over a list of values."""
    fn, cond = rng.choice(_BOOL_FUNCS)
    for _ in range(30):
        values = rng.sample(range(1, 16), 3)
        results = [bool(_apply(cond, n=v)) for v in values]
        if len(set(results)) == 2:
            break
    else:
        raise GenerationError("no mix of True and False")
    words = fn == "is_even" and rng.random() < 0.4
    if words:  # same idea, but the function answers with words
        fn = "parity"
        body = f'    if {cond}:\n        return "even"\n    return "odd"'
        outs = ["even" if r else "odd" for r in results]
        flip = ["odd" if r else "even" for r in results]
    else:
        body = f"    if {cond}:\n        return True\n    return False"
        outs = [str(r) for r in results]
        flip = [str(not r) for r in results]
    code = f"def {fn}(n):\n{body}\n\nfor number in {values}:\n    print({fn}(number))"
    wrong = [
        "\n".join(flip),
        "\n".join([flip[0], *outs[1:]]),
        "\n".join([*outs[:-1], flip[-1]]),
        "\n".join(outs[::-1]),
        "\n".join([outs[0], flip[1], outs[2]]),
    ]
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=wrong,
        explanation=f"Each loop pass calls `{fn}` with the next number. If the condition is True the function returns right away; otherwise it reaches the last `return`.",
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_trace_loop_function(rng: random.Random) -> Question:
    """Bingo `square_list(lst)` / running total inside a function -- sometimes with `return` inside the loop."""
    nums = rng.sample(range(2, 9), 3)
    bug = rng.random() < 0.45
    family = rng.choice(["square", "double", "total"])
    if family == "total":
        head = "def total_of(lst):\n    total = 0\n    for n in lst:\n        total += n\n"
        call = f"print(total_of({nums}))"
        s = sum(nums)
        wrong = [s, nums[0], nums[-1], s - nums[0], s - nums[-1], nums[0] + nums[1]]
        why_ok = "The loop adds every number before `return total` runs once, after the loop."
        why_bug = "`return` is inside the loop, so the function ends on the first pass and returns only the first number."
        ret = "return total"
    else:
        op, name = ("n * n", "square_list") if family == "square" else ("n * 2", "double_list")
        head = f"def {name}(lst):\n    result = []\n    for n in lst:\n        result.append({op})\n"
        call = f"print({name}({nums}))"
        full = [n * n for n in nums] if family == "square" else [n * 2 for n in nums]
        wrong = [full, nums, full[:1], full[:-1], full[1:], full[0]]
        why_ok = "The loop builds the whole new list, and `return result` runs once, after the loop has finished."
        why_bug = "`return result` is inside the loop, so the function ends after the first item and the list holds only one value."
        ret = "return result"
    tail = ("        " if bug else "    ") + ret
    code = f"{head}{tail}\n\n{call}"
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[str(w) for w in wrong],
        explanation=why_bug if bug else why_ok,
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_trace_max_of_three(rng: random.Random) -> Question:
    """Bingo `max_of_three(a, b, c)` without max(): trace two calls, or the version that forgets what it already found."""
    bug = rng.random() < 0.5

    def buggy(x: int, y: int, z: int) -> int:  # compares c with a instead of with biggest
        return z if z > x else (y if y > x else x)

    for _ in range(60):
        first, second = rng.sample(range(1, 20), 3), rng.sample(range(1, 20), 3)
        if not bug or buggy(*first) != max(first):
            break
    else:
        raise GenerationError("no suitable arguments")
    cmp_with = "a" if bug else "biggest"  # the bug: compare with `a` instead of with `biggest`
    body = f"    biggest = a\n    if b > {cmp_with}:\n        biggest = b\n    if c > {cmp_with}:\n        biggest = c\n    return biggest"
    if bug:
        why = "The second `if` compares `c` with `a` instead of with `biggest`, so a smaller `c` can overwrite a bigger `b`."
    else:
        why = "`biggest` starts as `a`, is replaced by `b` if `b` is bigger, then by `c` if `c` is bigger than the current `biggest`."
    f1, f2 = ", ".join(map(str, first)), ", ".join(map(str, second))
    code = f"def max_of_three(a, b, c):\n{body}\n\nprint(max_of_three({f1}))\nprint(max_of_three({f2}))"
    got = (buggy if bug else lambda x, y, z: max(x, y, z))
    r1, r2 = got(*first), got(*second)
    t1, t2 = max(first), max(second)
    wrong = [
        f"{t1}\n{t2}",
        f"{first[0]}\n{second[0]}",
        f"{r1}\n{t2}",
        f"{t1}\n{r2}",
        f"{r2}\n{r1}",
        f"{first[1]}\n{second[1]}",
        f"{first[2]}\n{second[2]}",
    ]
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


_BUGGY_FORMULAS = [
    (
        "average",
        "a, b, c",
        "a + b + c / 3",
        "(a + b + c) / 3",
        ["a + (b + c) / 3", "(a + b + c) / 2", "a + b + c // 3", "(a + b + c) / 4", "(a + b + c) - 3", "(a + b + c) * 3"],
        [(3, 6, 9), (2, 4, 9), (6, 9, 12), (1, 5, 6)],
        "Division happens before addition, so only `c` is divided by 3.",
    ),
    (
        "fahrenheit_to_celsius",
        "f",
        "f - 32 * 5 / 9",
        "(f - 32) * 5 / 9",
        ["f - (32 * 5 / 9)", "(f - 32) / 5 * 9", "(f + 32) * 5 / 9", "(f - 32) * 9 / 5", "(f - 32) * 5 / 3"],
        [(212,), (50,), (86,), (104,)],
        "Multiplication and division happen before subtraction, so `32 * 5 / 9` is computed first. Parentheses make `f - 32` happen first.",
    ),
]


@generator(TOPIC, HARD)
def gen_fix_the_formula(rng: random.Random) -> Question:
    """The classic order-of-operations bug inside a lab function: which return line fixes it?"""
    fn, params, bad, good, wrong_exprs, examples, why = rng.choice(_BUGGY_FORMULAS)
    args = rng.choice(examples)
    shown = _lab_value(fn, params, bad, args)
    want = _lab_value(fn, params, good, args)
    call = f"{fn}({', '.join(repr(x) for x in args)})"
    wrong = [f"return {w}" for w in wrong_exprs if _lab_value(fn, params, w, args) not in (want, shown)]
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"`{call}` should return `{want}` but returns `{shown}`. Which line fixes the function?",
        code=f"def {fn}({params}):\n    return {bad}",
        correct=f"return {good}",
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


_PREDICATES = [
    ("is_even", "n % 2 == 0", "even numbers"),
    ("is_even", "n % 2 == 0", "even numbers"),
    ("is_odd", "n % 2 == 1", "odd numbers"),
    ("is_multiple_of_three", "n % 3 == 0", "multiples of 3"),
]


@generator(TOPIC, HARD)
def gen_function_in_loop(rng: random.Random) -> Question:
    """A True/False function used in a for loop + if: add up (or count) the numbers that pass."""
    fn, cond, _ = rng.choice(_PREDICATES)
    stop = rng.randint(6, 10)
    count_it = rng.random() < 0.4
    acc = "count" if count_it else "total"
    update = f"{acc} += 1" if count_it else f"{acc} += number"

    def snippet(c: str, hi: int, upd: str) -> str:
        return (
            f"def {fn}(n):\n    return {c}\n\n{acc} = 0\n"
            f"for number in range(1, {hi}):\n    if {fn}(number):\n        {upd}\nprint({acc})"
        )

    code = snippet(cond, stop, update)
    other_cond = {"n % 2 == 0": "n % 2 == 1", "n % 2 == 1": "n % 2 == 0", "n % 3 == 0": "n % 3 == 1"}[cond]
    wrong = [
        _out(snippet(cond, stop + 1, update)),
        _out(snippet(other_cond, stop, update)),
        _out(snippet(cond, stop, f"{acc} += number" if count_it else f"{acc} += 1")),
        _out(snippet(cond, stop - 1, update)),
        _out(snippet(cond, stop + 2, update)),
        _out(snippet(other_cond, stop + 1, update)),
    ]
    right = _out(code)
    if right.isdigit():  # fallbacks: off-by-one answers
        wrong += [str(int(right) + 1), str(int(right) + 2), str(max(int(right) - 1, 0))]
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=wrong,
        explanation=f"`range(1, {stop})` gives 1 to {stop - 1}. The loop calls `{fn}` on each number and "
        + ("counts" if count_it else "adds up")
        + " the ones where it returns True.",
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_print_instead_of_return(rng: random.Random) -> Question:
    """The classic print-vs-return mistake: the function prints, so the variable gets nothing back."""
    fn, expr = rng.choice(MATH[:3])
    a, b = _two_ints(rng)
    r = _apply(expr, a=a, b=b)
    label = rng.choice(["Total:", "Result:", "Answer:"])
    code = f'def {fn}(a, b):\n    print({expr})\n\nresult = {fn}({a}, {b})\nprint("{label}", result)'
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=[f"{r}\n{label} {r}", f"{label} {r}", str(r), f"{label} None"],
        explanation=f"`{fn}` prints {r} itself but has no `return`, so it gives nothing back and `result` holds `None`. The second `print` shows `{label} None`.",
        rng=rng,
    )


# ==========================================================================
# BLANKS (typed, like the quiz's "fill in multiple blanks")
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_def_and_call(rng: random.Random) -> Question:
    """The lesson's first example: `def greet():` ... then call it with `greet()`."""
    fn, msg = rng.choice(NO_ARG_FUNCS)
    template = f'{blank_mark(1)} {fn}():\n    print("{msg}")\n\n{fn}{blank_mark(2)}'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blanks: define the function, then call it so the program prints `{msg}`.",
        template=template,
        blanks=[Blank(["def"], hint="keyword"), Blank(["()"], hint="how to call it")],
        explanation=f"`def` defines the function, but it only runs when you call it: `{fn}()`.",
        expect_output=msg,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_param_arg(rng: random.Random) -> Question:
    """greet_person(name): type the parameter in the def line and the argument in the call."""
    fn = rng.choice(GREET_FUNCS)
    param = rng.choice(["name", "name", "player", "student"])
    person = rng.choice(PEOPLE)
    tmpl = rng.choice(GREETINGS)
    line = "print(f\"" + tmpl.replace("NAME", "{" + param + "}") + "\")"
    template = f"def {fn}({blank_mark(1)}):\n    {line}\n\n{fn}({blank_mark(2)})"
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the program prints `{_fmt(tmpl, person)}`.",
        template=template,
        blanks=[
            Blank([param], hint="the parameter"),
            Blank([f'"{person}"', f"'{person}'"], hint="the argument", mode="expr"),
        ],
        explanation=f"The parameter (`{param}`) goes inside the parentheses of the `def` line. The argument (`\"{person}\"`) is the value you pass when you call the function.",
        expect_output=_fmt(tmpl, person),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_return_value(rng: random.Random) -> Question:
    """`return` the result, then print it with a label: `print("Total:", add(1, 1))`."""
    fn, expr = rng.choice(MATH[:3])
    a, b = _two_ints(rng)
    label = rng.choice(_LABELS)
    result = _apply(expr, a=a, b=b)
    call = f"{fn}({a}, {b})"
    calls = [call, f"{fn}({b}, {a})"] if fn in ("add", "multiply") else [call]  # order doesn't matter for + and *
    template = f'def {fn}(a, b):\n    {blank_mark(1)} {expr}\n\nprint("{label}", {blank_mark(2)})'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the program prints `{label} {result}` (call `{fn}` with {a} and {b}).",
        template=template,
        blanks=[Blank(["return"], hint="keyword"), Blank(calls, hint="a function call", mode="expr")],
        explanation=f"`return` sends the value back to the caller, and `{call}` is the call whose result `print` displays.",
        expect_output=f"{label} {result}",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_lab_formula(rng: random.Random) -> Question:
    """Mini-Challenge formulas: fahrenheit_to_celsius, celsius_to_fahrenheit or the average with a helper variable."""
    kind = rng.choice(["f2c", "c2f", "average"])
    if kind == "f2c":
        f = rng.choice([212, 50, 86, 104, 68])
        template = (
            f"def fahrenheit_to_celsius(f):\n    return (f - {blank_mark(1)}) * {blank_mark(2)} / {blank_mark(3)}"
            f"\n\nprint(fahrenheit_to_celsius({f}))"
        )
        blanks = [Blank(["32"], mode="expr"), Blank(["5"], mode="expr"), Blank(["9"], mode="expr")]
        prompt = "Fill in the blanks: Celsius = (Fahrenheit - 32) * 5 / 9."
        out = str((f - 32) * 5 / 9)
        why = "Subtract 32 first (the parentheses), then multiply by 5 and divide by 9."
    elif kind == "c2f":
        c = rng.choice([100, 0, 20, 30, 40])
        template = (
            f"def celsius_to_fahrenheit(c):\n    return c * {blank_mark(1)} / {blank_mark(2)} + {blank_mark(3)}"
            f"\n\nprint(celsius_to_fahrenheit({c}))"
        )
        blanks = [Blank(["9"], mode="expr"), Blank(["5"], mode="expr"), Blank(["32"], mode="expr")]
        prompt = "Fill in the blanks: Fahrenheit = Celsius * 9 / 5 + 32."
        out = str(c * 9 / 5 + 32)
        why = "Multiply by 9, divide by 5, then add 32."
    else:
        a, b, c = _triple_div3(rng, 2, 20)
        template = (
            f"def average(a, b, c):\n    total = {blank_mark(1)}\n    return {blank_mark(2)} / 3"
            f"\n\nprint(average({a}, {b}, {c}))"
        )
        sums = ["a + b + c", "a + c + b", "b + a + c", "b + c + a", "c + a + b", "c + b + a"]
        blanks = [Blank(sums, hint="add the three numbers", mode="expr"), Blank(["total"], hint="the helper variable")]
        prompt = "Fill in the blanks so `average` returns the average of the three numbers."
        out = str((a + b + c) / 3)
        why = "Store the sum in `total`, then `return total / 3`."
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=prompt,
        template=template,
        blanks=blanks,
        explanation=why,
        expect_output=out,
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_bool_function_loop(rng: random.Random) -> Question:
    """Bingo `is_even(n)` used in a loop: type the operator and the call."""
    fn, op_expr, k = rng.choice(
        [("is_even", "n {op} 2 == 0", 2), ("is_multiple_of_three", "n {op} 3 == 0", 3), ("is_multiple_of_five", "n {op} 5 == 0", 5)]
    )
    stop = rng.randint(k + 2, k + 7)
    template = (
        f"def {fn}(n):\n    return {op_expr.format(op=blank_mark(1))}\n\n"
        f"for number in range(1, {stop}):\n    if {blank_mark(2)}(number):\n        print(number)"
    )
    shown = [str(n) for n in range(1, stop) if n % k == 0]
    if not shown:
        raise GenerationError("nothing printed")
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Fill in the blanks so the loop prints only the numbers for which the function returns `True`.",
        template=template,
        blanks=[Blank(["%"], hint="remainder operator"), Blank([fn], hint="the function name")],
        explanation="`%` gives the remainder, so `n % 2 == 0` is True for even numbers. The `if` calls the function with `number`.",
        expect_output="\n".join(shown),
    )


# ==========================================================================
# MATCH (clicks)
# ==========================================================================

_TERMS = [
    ("def", "Starts a function definition"),
    ("return", "Sends a value back to the caller"),
    ("parameter", "A variable in the parentheses of the def line"),
    ("argument", "A value you pass when you call the function"),
    ("greet()", "A call that runs the function"),
    ("print()", "A function Python already defined for us"),
]


@generator(TOPIC, EASY, qtype="match")
def gen_match_terms(rng: random.Random) -> Question:
    """Match the lesson's vocabulary: def, return, parameter, argument, a call, print()."""
    pairs = rng.sample(_TERMS, 5)
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each term to what it means in Python functions.",
        pairs=pairs,
        explanation="`def` defines a function; the parameter is in the def line; the argument is passed in the call; `return` sends a value back; `print()` and `input()` were already defined for us.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_code_parts(rng: random.Random) -> Question:
    """Label the parts of `def add(a, b): ... print("Total:", add(1, 1))`."""
    fn, expr = rng.choice(MATH)
    a, b = _two_ints(rng)
    label = rng.choice(_LABELS)
    code = f'def {fn}(a, b):\n    return {expr}\n\nprint("{label}", {fn}({a}, {b}))'
    pool = [
        (f"def {fn}(a, b):", "Function definition line"),
        (rng.choice(["a", "b"]), "Parameter"),
        (str(rng.choice([a, b])), "Argument"),
        (f"{fn}({a}, {b})", "Function call"),
        (f"return {expr}", "Return statement"),
    ]
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each part of the code to its name.",
        code=code,
        pairs=pool,
        explanation="The `def` line defines the function; `a` and `b` are its parameters; the values in the call are arguments; `return` sends the result back to the call.",
        rng=rng,
    )


_FUNCS_DEFS = {
    "add": ("def add(a, b):\n    return a + b", lambda a, b: a + b, 2),
    "multiply": ("def multiply(a, b):\n    return a * b", lambda a, b: a * b, 2),
    "square": ("def square(a):\n    return a ** 2", lambda a: a**2, 1),
}


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_call_values(rng: random.Random) -> Question:
    """Match each call to the value it returns (the math_tools functions)."""
    names = rng.sample(list(_FUNCS_DEFS), 3)
    code = "\n\n".join(_FUNCS_DEFS[n][0] for n in names)
    pairs = []
    used: set[int] = set()
    for n in names:
        _, fn, arity = _FUNCS_DEFS[n]
        for _ in range(30):
            args = tuple(rng.randint(2, 9) for _ in range(arity))
            val = fn(*args)
            if val not in used:
                used.add(val)
                break
        else:
            raise GenerationError("no distinct values")
        pairs.append((f"{n}({', '.join(map(str, args))})", str(val)))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each call to the value it returns.",
        code=code,
        pairs=pairs,
        extra_options=[str(max(used) + rng.randint(1, 5))],
        explanation="Each call passes its arguments to the parameters in order, and `return` sends back the result.",
        rng=rng,
    )


# ==========================================================================
# CODE (typed, graded in the sandbox)
# ==========================================================================

# Fahrenheit / Celsius values whose conversions are exact floats.
_F_VALUES = [212, 32, 41, 50, 59, 68, 77, 86, 95, 104, 14, 23, -40]
_C_VALUES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 100, -10, -40]


def _f2c(f: int) -> float:
    return (f - 32) * 5 / 9


def _c2f(c: int) -> float:
    return c * 9 / 5 + 32


@generator(TOPIC, EASY, qtype="code")
def gen_code_return_expression(rng: random.Random) -> Question:
    """Type the expression that goes after `return` in a Mini-Challenge function."""
    kind = rng.choice(["f2c", "c2f", "average", "area"])
    if kind == "f2c":
        var = rng.choice(["f", "temp_f", "fahrenheit"])
        cases = [({var: v}, _f2c(v)) for v in rng.sample(_F_VALUES, 5)]
        solution = f"({var} - 32) * 5 / 9"
        prompt = f"`{var}` holds a temperature in Fahrenheit. Type the expression a function would `return` to get Celsius: subtract 32, multiply by 5, divide by 9."
        ctx = f"{var} = 212"
        why = "Subtract 32 first (use parentheses), then multiply by 5 and divide by 9."
    elif kind == "c2f":
        var = rng.choice(["c", "temp_c", "celsius"])
        cases = [({var: v}, _c2f(v)) for v in rng.sample(_C_VALUES, 5)]
        solution = f"{var} * 9 / 5 + 32"
        prompt = f"`{var}` holds a temperature in Celsius. Type the expression a function would `return` to get Fahrenheit: multiply by 9, divide by 5, add 32."
        ctx = f"{var} = 100"
        why = "Multiply by 9, divide by 5, then add 32."
    elif kind == "average":
        triples = [_triple_div3(rng, 1, 21) for _ in range(5)]
        cases = [({"a": a, "b": b, "c": c}, (a + b + c) / 3) for a, b, c in triples]
        solution = "(a + b + c) / 3"
        prompt = "`a`, `b` and `c` hold three numbers. Type the expression a function would `return` for their average."
        ctx = "a = 2\nb = 4\nc = 9"
        why = "Add the three numbers inside parentheses, then divide the whole sum by 3."
    else:
        sides = rng.sample([1, 2, 3, 4, 5, 7, 10, 1.5, 2.5], 5)
        cases = [({"side": s}, s * s) for s in sides]
        solution = "side * side"
        prompt = "`side` holds the side length of a square. Type the expression a function would `return` for its area."
        ctx = "side = 5"
        why = "The area of a square is side times side."
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        task=expression_task(solution, cases, starter=""),
        explanation=why,
        code=ctx,
    )


_SIMPLE_FUNCS = [
    ("square_area", ["side"], "side * side", "the area of a square with that side length"),
    ("square_perimeter", ["side"], "side * 4", "the perimeter of a square with that side length"),
    ("double", ["number"], "number * 2", "the number doubled"),
    ("add", ["a", "b"], "a + b", "the sum of `a` and `b`"),
    ("multiply", ["a", "b"], "a * b", "`a` times `b`"),
]


@generator(TOPIC, EASY, qtype="code")
def gen_code_one_line_function(rng: random.Random) -> Question:
    """Write a one-line function that RETURNS a value (square_area, add, ...)."""
    name, params, expr, desc = rng.choice(_SIMPLE_FUNCS)
    arity = len(params)
    seen: set = set()
    cases = []
    while len(cases) < 5:
        args = tuple(rng.randint(1, 12) for _ in range(arity))
        if args in seen or (arity == 2 and args[0] == args[1]):
            continue
        seen.add(args)
        cases.append((args, _apply(expr, **dict(zip(params, args)))))
    solution = f"def {name}({', '.join(params)}):\n    return {expr}"
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Write a function `{name}({', '.join(params)})` that returns {desc}. Use `return` (don't print it).",
        task=function_task(name, solution, cases),
        explanation=f"The body is `return {expr}`. `return` sends the value back to whoever called `{name}`; `print` would only show it.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_greet_print(rng: random.Random) -> Question:
    """The lesson's greet_person(name): the function PRINTS the greeting (checked by its output)."""
    fn = rng.choice(GREET_FUNCS)
    tmpl = rng.choice(GREETINGS)
    names = rng.sample(PEOPLE, 4)
    cases = [Case(args=[n], out=_fmt(tmpl, n)) for n in names]
    solution = f"def {fn}(name):\n    print({_fstr(tmpl)})"
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f'Write a function `{fn}(name)` that prints a greeting for the name it is given. For example, `{fn}("{names[0]}")` prints `{_fmt(tmpl, names[0])}`.',
        task=function_task(fn, solution, cases),
        explanation="Put the parameter in an f-string inside `print`. This function prints; it does not need a `return`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_temperature_function(rng: random.Random) -> Question:
    """Mini-Challenge: fahrenheit_to_celsius(f) (or the reverse) as a function that returns the result."""
    if rng.random() < 0.65:
        fn, param, expr = "fahrenheit_to_celsius", "f", "(f - 32) * 5 / 9"
        cases = [((v,), _f2c(v)) for v in rng.sample(_F_VALUES, 5)]
        prompt = "Write a function `fahrenheit_to_celsius(f)` that returns the temperature in Celsius: subtract 32, multiply by 5, divide by 9."
        why = "`return (f - 32) * 5 / 9`: the parentheses make the subtraction happen first."
    else:
        fn, param, expr = "celsius_to_fahrenheit", "c", "c * 9 / 5 + 32"
        cases = [((v,), _c2f(v)) for v in rng.sample(_C_VALUES, 5)]
        prompt = "Write a function `celsius_to_fahrenheit(c)` that returns the temperature in Fahrenheit: multiply by 9, divide by 5, add 32."
        why = "`return c * 9 / 5 + 32`: multiplication and division happen before the addition."
    solution = f"def {fn}({param}):\n    return {expr}"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        task=function_task(fn, solution, cases),
        explanation=why,
    )


_AVG_FUNCS = [
    ("average", ["a", "b", "c"]),
    ("average", ["a", "b", "c"]),
    ("average_score", ["quiz1", "quiz2", "quiz3"]),
    ("average_points", ["round1", "round2", "round3"]),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_average(rng: random.Random) -> Question:
    """Mini-Challenge: average(a, b, c) returns the average of three numbers."""
    name, params = rng.choice(_AVG_FUNCS)
    triples = [(2, 4, 9), (3, 6, 9)]
    while len(triples) < 5:  # sums that are multiples of 3 keep the expected averages tidy
        t = tuple(rng.randint(0, 20) for _ in range(3))
        if t not in triples and sum(t) % 3 == 0:
            triples.append(t)
    rng.shuffle(triples)
    cases = [(t, sum(t) / 3) for t in triples]
    solution = f"def {name}({', '.join(params)}):\n    return ({' + '.join(params)}) / 3"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{name}({', '.join(params)})` that returns the average of the three numbers.",
        task=function_task(name, solution, cases),
        explanation=f"Add all three numbers, then divide the whole sum by 3: `return ({' + '.join(params)}) / 3`. Without the parentheses only the last number would be divided.",
    )


# (function, parameter, expression, description, values that must be tested, other values to draw from)
_BOOL_TASKS = [
    ("is_even", "n", "n % 2 == 0", "`n` is even", [0, 1, 2], [3, 4, 7, 10, 13, 22]),
    ("is_even", "n", "n % 2 == 0", "`n` is even", [0, 1, 2], [3, 4, 7, 10, 13, 22]),
    ("is_odd", "n", "n % 2 == 1", "`n` is odd", [0, 1, 2], [3, 4, 7, 10, 13, 22]),
    ("is_multiple_of_five", "n", "n % 5 == 0", "`n` is a multiple of 5", [0, 5, 7], [10, 12, 25, 3, 50, 49]),
    ("can_drive", "age", "age >= 16", "`age` is 16 or older", [15, 16, 17], [12, 30, 0, 45]),
    ("is_teen", "age", "13 <= age <= 19", "`age` is from 13 to 19 (inclusive)", [12, 13, 19, 20], [16, 25, 7, 15]),
    ("is_positive", "n", "n > 0", "`n` is greater than 0", [-1, 0, 1], [-3, 5, 12, -10]),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_true_false_function(rng: random.Random) -> Question:
    """Bingo `is_even(n)` and friends: return True or False (boundary values are always tested)."""
    name, param, expr, desc, must, pool = rng.choice(_BOOL_TASKS)
    yes = [v for v in pool if _apply(expr, **{param: v})]
    no = [v for v in pool if not _apply(expr, **{param: v})]
    values = [*must, rng.choice(yes), rng.choice(no)]  # one more True and one more False case
    rng.shuffle(values)
    cases = [((v,), bool(_apply(expr, **{param: v}))) for v in values]
    solution = f"def {name}({param}):\n    return {expr}"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{name}({param})` that returns `True` if {desc}, otherwise `False`.",
        task=function_task(name, solution, cases),
        explanation=f"A comparison already gives `True` or `False`, so `return {expr}` is enough. An `if` with `return True` / `return False` works too.",
    )


_PROGRAM_OPS = [
    ("add", "a + b", "Total:"),
    ("add", "a + b", "Total:"),
    ("multiply", "a * b", "Product:"),
    ("subtract", "a - b", "Difference:"),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_function_and_call_program(rng: random.Random) -> Question:
    """Define add(a, b), read two numbers with input(), print the label and the returned value."""
    fn, expr, label = rng.choice(_PROGRAM_OPS)
    pairs = [(3, 4), (10, 2), (0, 0), (7, 12), (-2, 5)]
    pairs = rng.sample(pairs, 4)
    cases = [Case(stdin=[str(a), str(b)], out=f"{label} {_apply(expr, a=a, b=b)}") for a, b in pairs]
    solution = (
        f"def {fn}(a, b):\n    return {expr}\n\n"
        f"first = int(input())\nsecond = int(input())\nprint(\"{label}\", {fn}(first, second))"
    )
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=(
            f"Define a function `{fn}(a, b)` that returns `{expr}`. Then read two whole numbers with `input()` "
            f"(cast them with `int()`) and print `{label}` followed by the result of calling `{fn}` on them, "
            f"for example `{label} {_apply(expr, a=pairs[0][0], b=pairs[0][1])}` for the inputs {pairs[0][0]} and {pairs[0][1]}."
        ),
        task=program_task(
            solution,
            cases,
            starter=f"def {fn}(a, b):\n    ",
            requires=[(rf"\bdef\s+{fn}\s*\(", f"Define a function named {fn}"), (r"\breturn\b", "Use return inside the function")],
        ),
        explanation=f"Define `{fn}` with `return {expr}`, cast both `input()` answers with `int()`, then `print(\"{label}\", {fn}(first, second))`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_max_of_three(rng: random.Random) -> Question:
    """Bingo `max_of_three(a, b, c)` without using max() (or min_of_three without min())."""
    use_max = rng.random() < 0.7
    name, op, builtin = ("max_of_three", ">", "max") if use_max else ("min_of_three", "<", "min")
    pick = max if use_max else min
    # the biggest / smallest sits in every position at least once; plus ties and negatives
    triples = [(1, 2, 3), (3, 2, 1), (2, 3, 1), (3, 1, 2), (1, 3, 2)]
    triples += rng.sample([(5, 5, 1), (-1, -5, -3), (7, 7, 7), (4, 9, 9), (6, 2, 6)], 1)
    triples.append(tuple(rng.sample(range(-9, 30), 3)))
    rng.shuffle(triples)
    cases = [(t, pick(t)) for t in triples]
    solution = (
        f"def {name}(a, b, c):\n    best = a\n    if b {op} best:\n        best = b\n    if c {op} best:\n        best = c\n    return best"
    )
    word = "biggest" if use_max else "smallest"
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a function `{name}(a, b, c)` that returns the {word} of three numbers without using `{builtin}()`.",
        task=function_task(
            name,
            solution,
            cases,
            forbids=[(rf"\b{builtin}\s*\(", f"Don't use {builtin}() - compare with if statements")],
        ),
        explanation=f"Start with `best = a`, replace it with `b` if `b` is {'bigger' if use_max else 'smaller'}, then with `c` if `c` is {'bigger' if use_max else 'smaller'} than the current `best`.",
    )


_LIST_FUNCS = [
    ("square_list", "returns a new list with each number squared", "result.append(n * n)", lambda xs: [x * x for x in xs], False),
    ("square_list", "returns a new list with each number squared", "result.append(n * n)", lambda xs: [x * x for x in xs], False),
    ("double_list", "returns a new list with each number doubled", "result.append(n * 2)", lambda xs: [x * 2 for x in xs], False),
    ("evens_only", "returns a new list with only the even numbers", "if n % 2 == 0:\n            result.append(n)", lambda xs: [x for x in xs if x % 2 == 0], False),
    ("total_of", "returns the sum of all the numbers (use a loop, not `sum()`)", "total += n", lambda xs: sum(xs), True),
]


@generator(TOPIC, HARD, qtype="code")
def gen_code_list_function(rng: random.Random) -> Question:
    """Bingo `square_list(lst)`: a function with a loop that builds / adds up a result and returns it."""
    name, desc, step, fn, is_total = rng.choice(_LIST_FUNCS)
    lists = [[1, 2, 3], []]  # always test an ordinary list and the empty list
    lists += rng.sample([[4], [-2, 5, 0, 8], [2, 7, 10, 3, 6], [9, 1]], 2)
    lists.append(rng.sample(range(-5, 15), rng.randint(2, 5)))
    rng.shuffle(lists)
    cases = [((lst,), fn(lst)) for lst in lists]
    if is_total:
        solution = f"def {name}(lst):\n    total = 0\n    for n in lst:\n        {step}\n    return total"
    else:
        solution = f"def {name}(lst):\n    result = []\n    for n in lst:\n        {step}\n    return result"
    forbids = [(r"\bsum\s*\(", "Use a loop instead of sum()")] if is_total else []
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a function `{name}(lst)` that {desc}." + ("" if is_total else " Use a loop."),
        task=function_task(name, solution, cases, requires=[(r"\b(for|while)\b", "Use a loop (for ... in ...)")], forbids=forbids),
        explanation="Loop over `lst` and "
        + ("add each number to `total`" if is_total else "build a new list with `append`")
        + ". Put the `return` after the loop (not inside it), and make sure an empty list still works.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_print_and_return(rng: random.Random) -> Question:
    """Both appear: the function prints a labelled line AND returns the value."""
    fn, expr, label = rng.choice(
        [("add_and_show", "a + b", "Total:"), ("add_and_show", "a + b", "Total:"), ("multiply_and_show", "a * b", "Product:")]
    )
    pairs = [(2, 3), (10, 5), (0, 4), (7, 7), (1, 9)]
    pairs = rng.sample(pairs, 4)
    cases = [Case(args=[a, b], ret=_apply(expr, a=a, b=b), out=f"{label} {_apply(expr, a=a, b=b)}") for a, b in pairs]
    solution = f"def {fn}(a, b):\n    result = {expr}\n    print(\"{label}\", result)\n    return result"
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"Write a function `{fn}(a, b)` that prints one line with the label and the result, and also returns the result. "
            f"For example, `{fn}({pairs[0][0]}, {pairs[0][1]})` prints `{label} {_apply(expr, a=pairs[0][0], b=pairs[0][1])}`."
        ),
        task=function_task(fn, solution, cases),
        explanation="A function can do both: `print` shows the value on the screen, and `return` hands it back to the caller. Store it in a variable so you only compute it once.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_mini_challenge_trio(rng: random.Random) -> Question:
    """The whole Mini-Challenge: fahrenheit_to_celsius(f), square_area(side) and average(a, b, c) together."""
    solution = (
        "def fahrenheit_to_celsius(f):\n    return (f - 32) * 5 / 9\n\n"
        "def square_area(side):\n    return side * side\n\n"
        "def average(a, b, c):\n    return (a + b + c) / 3"
    )
    starter = "def fahrenheit_to_celsius(f):\n    \n\ndef square_area(side):\n    \n\ndef average(a, b, c):\n    "
    cases = []
    for _ in range(3):
        f = rng.choice(_F_VALUES)
        side = rng.choice([3, 4, 5, 6, 9, 10])
        a, b, c = _triple_div3(rng, 1, 15)
        after = f"print(fahrenheit_to_celsius({f}))\nprint(square_area({side}))\nprint(average({a}, {b}, {c}))"
        out = f"{_f2c(f)}\n{side * side}\n{(a + b + c) / 3}"
        label = f"fahrenheit_to_celsius({f}), square_area({side}), average({a}, {b}, {c})"
        cases.append(Case(label=label, after=after, out=out))
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            "Write the three Mini-Challenge functions: `fahrenheit_to_celsius(f)`, `square_area(side)` and "
            "`average(a, b, c)`, each returning its result. Only write the three `def` blocks (don't print anything)."
        ),
        task=program_task(solution, cases, starter=starter, examples=1),
        explanation="Each function uses `return`: `(f - 32) * 5 / 9`, `side * side` and `(a + b + c) / 3`. The game calls them and prints the results for you.",
    )
