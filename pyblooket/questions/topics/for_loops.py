"""Question generators for the "for_loops" topic (CSF.2.J: Loops, Part 2 -- ``for`` loops).

Everything here follows the lesson: ``range(n)`` counts 0 .. n-1, ``range(start, stop)`` stops
*before* ``stop`` (so ``range(1, n + 1)`` for "normal" counting), ``range(start, stop, step)``
(odd numbers, counting by 100s, "why it may stop early"), looping over a list (singular
``fruit`` / plural ``fruits``) and over a string (``for letter in word``), ``for`` + ``if`` with
``%`` (even / odd), running totals, and the three mini-challenges (multiples of 3, numbered
favourite things done with a *counter variable* -- not ``enumerate`` -- and the running total
that stops when the user enters 0).  The quiz items "What does range(3) produce?", "which loop
header prints 1 through n inclusive?", "what does ``for item in my_list`` do?" and "which
keyword exits a loop early?" are all here in the quiz's own words.

Wherever the right answer depends on running a snippet, it is computed by *running* it
(``output_question`` / ``_mutants``), and the wrong answers come from slightly broken copies of
the same code (off-by-one, wrong list name, counter in the wrong place ...), so every question
is correct by construction.
"""

from __future__ import annotations

import random

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
    NAMES,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    display_output,
    expression_task,
    generator,
    match_question,
    output_question,
    program_task,
    run_code,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "for_loops"

# (singular, plural, what the lab prints before the item, items) -- "fruits" is the lesson's own list.
_LISTS = [
    ("fruit", "fruits", "I like", ["apple", "banana", "cherry", "mango", "lemon", "grape", "peach", "kiwi", "pear"]),
    ("color", "colors", "I like", ["red", "green", "blue", "purple", "orange", "yellow", "pink"]),
    ("food", "foods", "I like", ["sushi", "pizza", "tacos", "ramen", "pasta", "salad", "waffles"]),
    ("game", "games", "I like", ["chess", "tag", "soccer", "minecraft", "checkers", "hockey", "tetris"]),
    ("pet", "pets", "I like", ["dog", "cat", "fish", "hamster", "parrot", "turtle", "rabbit"]),
    ("song", "songs", "I like", ["jazz", "pop", "rock", "country", "lo-fi", "blues", "disco"]),
    ("name", "names", "Hello", NAMES),
]
_SHORT_WORDS = ["code", "loop", "snake", "pixel", "tiger", "lemon", "mango", "orbit", "quest", "blook", "candy", "apple"]
_COUNT_WORDS = ["banana", "apple", "pepper", "balloon", "mississippi", "coffee", "letter", "bubble", "lesson", "cherry"]


def _run(code: str) -> str:
    """Output of a *generated* snippet (a crash is a generator bug)."""
    res = run_code(code)
    if res.error:
        raise GenerationError(f"snippet raised {res.error}:\n{code}")
    return res.output


def _csv(values) -> str:
    return ", ".join(str(v) for v in values)


def _lst(items) -> str:
    """A list literal the way the lessons write it (double quotes)."""
    return "[" + ", ".join(f'"{s}"' if isinstance(s, str) else str(s) for s in items) + "]"


def _fits(text: str) -> bool:
    lines = text.split("\n")
    return bool(text.strip()) and len(lines) <= MAX_CHOICE_LINES and all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines)


def _pick_list(rng: random.Random, k: int):
    sing, plur, msg, items = rng.choice(_LISTS)
    return sing, plur, msg, rng.sample(items, k)


def _mutants(code: str, edits) -> list[str]:
    """What slightly broken copies of ``code`` print.  ``edits`` = [(old, new), ...]; each
    replaces the first ``old`` in the code.  Broken copies that crash or print too much are dropped."""
    outs = []
    for old, new in edits:
        if old not in code:
            raise GenerationError(f"edit {old!r} is not in the code:\n{code}")
        res = run_code(code.replace(old, new, 1))
        if res.error:
            continue
        text = display_output(res.output)
        if _fits(text):
            outs.append(text)
    return outs


def _output(difficulty: int, code: str, edits, why: str, rng: random.Random, extra=(), prompt="What does this code print?"):
    code = code.strip("\n")
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[*_mutants(code, edits), *extra],
        explanation=why,
        rng=rng,
        prompt=prompt,
    )


def _choice(difficulty: int, prompt: str, correct: str, wrong, why: str, rng: random.Random, code: str | None = None):
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
        code=code,
    )


def _lines(prefix: str, values) -> str:
    return "\n".join(f"{prefix} {v}" for v in values)


# ==========================================================================
# EASY -- multiple choice (the level of the Canvas quizzes)
# ==========================================================================


@generator(TOPIC, EASY)
def gen_range_stop_values(rng: random.Random) -> Question:
    """Quiz item: 'What does range(3) produce in a loop?'"""
    n = rng.randint(2, 7)
    correct = _csv(range(n))
    if rng.random() < 0.55:
        prompt = f"What does `range({n})` produce in a loop?"
    else:
        prompt = f"Which values does `i` take in `for i in range({n}):`?"
    return _choice(
        EASY,
        prompt,
        correct,
        [_csv(range(1, n + 1)), _csv(range(n + 1)), _csv(range(1, n))],
        f"`range({n})` gives {n} numbers starting at 0: {correct}. Remember: `range(stop)` starts at 0 and stops right before `stop`.",
        rng,
    )


@generator(TOPIC, EASY)
def gen_inclusive_header(rng: random.Random) -> Question:
    """Quiz item: 'If you want to print 1 through n inclusive, which loop header fits?'"""
    kind = rng.choice(["one_to_n", "one_to_n", "zero_to_n", "const"])
    if kind == "one_to_n":
        n = rng.choice(["n", "n", "num", "limit", "target"])
        prompt = f"If you want to print 1 through `{n}` inclusive, which loop header fits?"
        correct = f"for i in range(1, {n} + 1):"
        wrong = [f"for i in range({n}):", f"for i in range(1, {n}):", f"for i in range({n} + 1, 1):"]
        why = f"The second number in `range(start, stop)` is exclusive, so use `{n} + 1` to include `{n}`. `range(1, {n} + 1)` is the lesson's way to count 1 through {n}."
    elif kind == "zero_to_n":
        n = rng.choice(["n", "num", "laps", "times"])
        prompt = f"Which loop header repeats `{n}` times, with `i` counting 0, 1, 2, ...?"
        correct = f"for i in range({n}):"
        wrong = [f"for i in range(1, {n}):", f"for i in range({n} + 1):", f"for i in range(0, {n} - 1):"]
        why = f"`range({n})` starts at 0 and stops before {n}, so the body runs exactly {n} times."
    else:
        a = rng.randint(1, 5)
        b = a + rng.randint(3, 9)
        prompt = f"Which loop header prints the numbers {a} through {b} (including {b})?"
        correct = f"for i in range({a}, {b + 1}):"
        wrong = [f"for i in range({a}, {b}):", f"for i in range({a + 1}, {b + 1}):", f"for i in range({a}, {b + 2}):"]
        why = f"`range({a}, {b + 1})` starts at {a} and stops right before {b + 1}, so the last number printed is {b}."
    return _choice(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_how_many_times(rng: random.Random) -> Question:
    """How many times does the loop body run? (range forms, a list, a string)."""
    kind = rng.choice(["range_n", "range_ab", "list", "string"])
    extra: list[int] = []
    if kind == "range_n":
        n = rng.randint(3, 9)
        code = f'for i in range({n}):\n    print("Hello", i)'
        why = f"`range({n})` has {n} values (0 up to {n - 1}), so the body runs {n} times."
    elif kind == "range_ab":
        a = rng.randint(1, 6)
        b = a + rng.randint(3, 7)
        code = f'for i in range({a}, {b}):\n    print("Hello", i)'
        why = f"`range({a}, {b})` gives {a} up to {b - 1}. That is {b} - {a} = {b - a} values, so the body runs {b - a} times."
        extra = [a, b]
    elif kind == "list":
        sing, plur, msg, items = _pick_list(rng, rng.randint(3, 6))
        code = f'{plur} = {_lst(items)}\nfor {sing} in {plur}:\n    print("{msg}", {sing})'
        why = f"The body runs once for each item in the list, and `{plur}` has {len(items)} items."
    else:
        word = rng.choice(_SHORT_WORDS)
        code = f'word = "{word}"\nfor letter in word:\n    print(letter)'
        why = f"A `for` loop visits each character once, and \"{word}\" has {len(word)} characters."
    count = len(_run(code).split("\n"))
    wrong = [count + 1, count - 1, count + 2, *extra]
    return _choice(
        EASY,
        "How many lines does this code print?",
        str(count),
        [str(w) for w in wrong if w > 0],
        why,
        rng,
        code=code,
    )


@generator(TOPIC, EASY)
def gen_hello_i_output(rng: random.Random) -> Question:
    """The lesson's first snippet: for i in range(5): print("Hello", i)."""
    n = rng.randint(2, 4)
    msg = rng.choice(["Hello", "Hello", "Lap", "Round", "Level"])
    code = f'for i in range({n}):\n    print("{msg}", i)'
    extra = [_lines(msg, [n] * n)]
    return _output(
        EASY,
        code,
        [(f"range({n})", f"range(1, {n + 1})"), (f"range({n})", f"range({n + 1})")],
        f"`i` starts at 0 and the loop stops before {n}, so it prints \"{msg} 0\" up to \"{msg} {n - 1}\" ({n} lines).",
        rng,
        extra=extra,
    )


@generator(TOPIC, EASY)
def gen_list_loop_output(rng: random.Random) -> Question:
    """Lesson section 4: for fruit in fruits: print("I like", fruit)."""
    sing, plur, msg, items = _pick_list(rng, 3)
    code = f'{plur} = {_lst(items)}\nfor {sing} in {plur}:\n    print("{msg}", {sing})'
    return _output(
        EASY,
        code,
        [
            (f'print("{msg}", {sing})', f'print("{msg}", {plur})'),
            (f'print("{msg}", {sing})', f'print("{msg} {sing}")'),
            (f'print("{msg}", {sing})', f"print({sing})"),
        ],
        f"`{sing}` holds one item of `{plur}` on each pass, so the loop prints one \"{msg} ...\" line per item, in order.",
        rng,
        extra=[f"{msg} {items[0]}"],
    )


@generator(TOPIC, EASY)
def gen_string_loop_output(rng: random.Random) -> Question:
    """Lesson section 5: for letter in word: print(letter)."""
    word = rng.choice(_SHORT_WORDS)
    code = f'word = "{word}"\nfor letter in word:\n    print(letter)'
    return _output(
        EASY,
        code,
        [("print(letter)", "print(word)"), ('print(letter)', 'print("letter")')],
        "A string behaves like a sequence of characters, so the loop visits each character in order and `print(letter)` puts each on its own line.",
        rng,
        extra=[word, "\n".join(reversed(word))],
    )


def _concept(rng: random.Random):
    """(prompt, correct, wrong choices, explanation) for one 'vocabulary' question."""
    kind = rng.choice(
        ["list_each", "list_each", "string_each", "loop_var", "iterator", "best_fit", "break", "colon", "indent", "run_file", "nothing_prints"]
    )
    if kind == "list_each":
        header = rng.choice(["for item in my_list:", "for item in my_list:", "for fruit in fruits:", "for score in scores:", "for name in names:", "for food in foods:"])
        wrong = ["Loops over indexes automatically only", "Changes the list into a tuple", "Removes duplicates", "Sorts the list", "Adds a new item to the list"]
        rng.shuffle(wrong)
        return (
            f"What does `{header}` do?",
            "Loops over each element in the list",
            wrong[:3],
            "A `for` loop steps through a collection: the loop variable holds each element of the list, one at a time.",
        )
    if kind == "string_each":
        header = rng.choice(["for letter in word:", "for letter in word:", "for char in text:", "for ch in name:"])
        return (
            f"What does `{header}` do?",
            "Visits each character in the string, one at a time",
            ["Visits each word in the string", "Visits the whole string only once", "Changes every character to uppercase"],
            "Strings behave like a sequence of characters, so the loop visits each character in order.",
        )
    if kind == "loop_var":
        n = rng.randint(3, 9)
        return (
            f"In `for i in range({n}):`, what is `i`?",
            "The loop variable: a new value on each pass",
            [f"The number of times the loop runs ({n})", "A function that creates the numbers", f"The last number in the range ({n - 1})"],
            "The loop variable takes on each value from the sequence, one at a time. `range(n)` makes the values, `i` holds the current one.",
        )
    if kind == "iterator":
        return (
            "Why do programmers often use `i` as the loop variable?",
            "It is short for \"iterator\"",
            ["Python requires the loop variable to be called `i`", "It is short for \"input\"", "It is short for \"integer\""],
            "`i` is just a habit (short for \"iterator\"). You can name the loop variable anything, such as `fruit` or `letter`.",
        )
    if kind == "best_fit":
        return (
            "According to the lesson, a `for` loop repeats...",
            "a known number of times, or through a collection",
            ["until something changes", "forever, unless you press Ctrl + C", "only when the condition is `False`"],
            "While loops repeat until something changes. For loops repeat a known number of times or step through a collection.",
        )
    if kind == "break":
        return (
            "Which keyword exits a loop early?",
            "break",
            ["stop", "exit", "return"],
            "`break` leaves the loop immediately, in both `while` and `for` loops.",
        )
    if kind == "colon":
        return (
            "What must the first line of a `for` loop end with?",
            "A colon `:`",
            ["A semicolon `;`", "A period `.`", "Parentheses `()`"],
            "The anatomy is `for <variable> in <sequence>:` followed by an indented block.",
        )
    if kind == "run_file":
        fname = rng.choice(["loops_p2_lab.py", "loops_p2_mini_challenge.py"])
        return (
            f"In the VS Code terminal on a Mac, which command runs the file `{fname}`?",
            f"python3 {fname}",
            [f"run {fname}", f"open {fname}", f"start python3 {fname}"],
            "Save the file, open View, Terminal in VS Code, and run it with `python3 file_name.py`.",
        )
    if kind == "nothing_prints":
        return (
            "Your `for` loop prints nothing. According to the lesson's tips, what should you check first?",
            "Whether your `range` has the correct start and stop",
            ["Whether the loop variable is named `i`", "Whether the file is saved in the Documents folder", "Whether you used a `while` loop instead"],
            "If nothing prints, check whether your `range` has the correct start and stop. A `range` like `range(5, 1)` is empty.",
        )
    return (
        "How does Python know which lines are inside a `for` loop?",
        "They are indented under the `for` line",
        ["They are inside curly braces `{ }`", "They end with a semicolon", "They come right after the word `loop`"],
        "After the `for ...:` line, the indented block is what repeats. Lines that are not indented run once, after the loop.",
    )


@generator(TOPIC, EASY)
def gen_for_vocab(rng: random.Random) -> Question:
    """Definition / concept questions in the quiz's wording."""
    prompt, correct, wrong, why = _concept(rng)
    return _choice(EASY, prompt, correct, wrong, why, rng)


@generator(TOPIC, EASY)
def gen_range_facts(rng: random.Random) -> Question:
    """Facts about range(): zero-based, exclusive stop, step."""
    kind = rng.choice(["zero_based", "first_last", "step_meaning", "size"])
    if kind == "zero_based":
        n = rng.randint(4, 9)
        return _choice(
            EASY,
            f"Which statement about `range({n})` is true?",
            f"It starts at 0 and its last value is {n - 1}",
            [f"It starts at 1 and its last value is {n}", f"It starts at 0 and its last value is {n}", f"It starts at 1 and its last value is {n - 1}"],
            f"Zero-based counting: the first value is 0, and the last value is one less than the size ({n - 1}).",
            rng,
        )
    if kind == "first_last":
        a = rng.randint(1, 6)
        b = a + rng.randint(3, 8)
        which = rng.choice(["first", "last"])
        right, other = (a, b - 1) if which == "first" else (b - 1, a)
        return _choice(
            EASY,
            f"In `for i in range({a}, {b}):`, what is the {which} value of `i`?",
            str(right),
            [str(v) for v in (b if which == "last" else a - 1, other, b - 2 if which == "last" else a + 1)],
            f"`range({a}, {b})` includes the start value {a} but stops right before {b}, so it runs {a} up to {b - 1}.",
            rng,
        )
    if kind == "step_meaning":
        start = rng.choice([0, 1, 2, 10])
        step = rng.choice([2, 3, 5, 10])
        stop = start + step * rng.randint(4, 9)
        return _choice(
            EASY,
            f"In `range({start}, {stop}, {step})`, what does the `{step}` mean?",
            "The step: how much to add each time",
            ["The stop value", "The starting number", "How many numbers to print"],
            f"`range(start, stop, step)` lets you count by 2s, 5s, 100s... Here the loop counts by {step}.",
            rng,
        )
    n = rng.randint(4, 9)
    a = rng.randint(2, 5)
    b = a + n
    return _choice(
        EASY,
        f"How many numbers does `range({a}, {b})` produce?",
        str(n),
        [str(n + 1), str(n - 1), str(b)],
        f"`range({a}, {b})` runs {a} up to {b - 1}: that is {b} - {a} = {n} numbers (the stop value is not included).",
        rng,
    )


@generator(TOPIC, EASY)
def gen_loop_naming(rng: random.Random) -> Question:
    """Lesson section 4: singular name for each item, plural name for the whole list."""
    sing, plur, _msg, _items = _pick_list(rng, 3)
    return _choice(
        EASY,
        f"`{plur}` is a list. Which loop header follows the lesson's naming tip (singular for each item, plural for the whole list)?",
        f"for {sing} in {plur}:",
        [f"for {plur} in {sing}:", f"for {plur} in {plur}:", f"for {sing} in {sing}:"],
        f"Use a singular name for each item and a plural name for the whole list: `for {sing} in {plur}:` reads naturally, like \"for each {sing} in the {plur}\".",
        rng,
    )


# ==========================================================================
# MEDIUM -- read / trace a short lab-style snippet, spot the classic mistake
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_step_values(rng: random.Random) -> Question:
    """Lesson section 3: range(start, stop, step) -- odd numbers, counting by 5s, counting by 100s."""
    kind = rng.choice(["odd", "odd", "by_five", "by_hundred"])
    if kind == "odd":
        num = rng.randint(7, 13)
        code = f"num = {num}\nfor i in range(1, num + 1, 2):\n    print(i)"
        values = list(range(1, num + 1, 2))
        wrong = [list(range(1, num + 1)), list(range(2, num + 1, 2)), values[1:], values + [values[-1] + 2]]
        why = f"`range(1, num + 1, 2)` starts at 1 and adds 2 each time, so it prints the odd numbers up to {num}: {_csv(values)}."
    elif kind == "by_five":
        num = rng.randint(18, 33)
        code = f"num = {num}\nfor i in range(0, num + 1, 5):\n    print(i)"
        values = list(range(0, num + 1, 5))
        wrong = [values[1:], values + [values[-1] + 5], list(range(1, num + 1, 5)), list(range(5, num, 5))]
        why = f"The loop starts at 0 and adds 5 each time while the value is still within `num + 1`: {_csv(values)}."
    else:
        target = rng.randint(250, 480)
        code = f"target = {target}\nfor i in range(1, target + 1, 100):\n    print(i)"
        values = list(range(1, target + 1, 100))
        wrong = [list(range(100, target + 1, 100)), values[1:], values + [values[-1] + 100], [0, *range(100, target + 1, 100)]]
        why = f"Counting by 100s from 1 gives {_csv(values)}. The next value, {values[-1] + 100}, would go past `target + 1`, so the loop ends."
    return _choice(MEDIUM, "Which numbers does this code print, in order?", _csv(values), [_csv(w) for w in wrong], why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_stops_early(rng: random.Random) -> Question:
    """Lesson: 'Why it may stop early' -- the next step would overshoot stop."""
    start = rng.choice([1, 1, 0, 2])
    step = rng.choice([2, 3, 4, 5, 10])
    num = start + step * rng.randint(2, 5) + rng.randint(1, step - 1)
    last = start + step * ((num - start) // step)
    code = f"num = {num}\nfor i in range({start}, num + 1, {step}):\n    print(i)"
    return _choice(
        MEDIUM,
        "What is the last number this code prints?",
        str(last),
        [str(num), str(last + step), str(num + 1), str(last - step)],
        f"Counting by {step} from {start} gives ... {last}; the next step would be {last + step}, which overshoots the stop, so the loop ends early at {last} and never reaches {num}.",
        rng,
        code=code,
    )


@generator(TOPIC, MEDIUM)
def gen_empty_range(rng: random.Random) -> Question:
    """Lesson troubleshooting: 'If nothing prints, check whether your range has the correct start and stop.'"""
    kind = rng.choice(["start_past_stop", "equal", "zero", "empty_list"])
    generic = [
        "`print()` can't be used inside a `for` loop",
        "A `for` loop needs a `break` to print anything",
        "`i` has to be changed with `str(i)` before printing",
        "The loop needs an `else:` line",
    ]
    if kind == "start_past_stop":
        a = rng.randint(4, 9)
        b = rng.randint(1, a - 1)
        code = f"for i in range({a}, {b}):\n    print(i)"
        correct = f"The start ({a}) is already past the stop ({b})"
        why = f"`range({a}, {b})` has no numbers because {a} is already past {b}, so the body never runs. If nothing prints, check your `range` start and stop."
    elif kind == "equal":
        a = rng.randint(2, 9)
        code = f"for i in range({a}, {a}):\n    print(i)"
        correct = f"The start and stop are the same ({a})"
        why = f"`range({a}, {a})` starts and stops at the same place, so it is empty and the body never runs."
    elif kind == "zero":
        code = "for i in range(0):\n    print(i)"
        correct = "`range(0)` has no numbers to loop over"
        why = "`range(0)` produces 0 numbers, so the body runs 0 times and nothing prints."
    else:
        sing, plur, _msg, _items = _pick_list(rng, 3)
        code = f"{plur} = []\nfor {sing} in {plur}:\n    print({sing})"
        correct = f"`{plur}` is an empty list"
        why = f"A `for` loop runs once per item. `{plur}` has no items, so the body never runs."
        generic = [g for g in generic if "str(i)" not in g and "`i`" not in g] + ["The loop variable should be plural"]
    return _choice(MEDIUM, "Why does this code print nothing?", correct, generic, why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_total_trace(rng: random.Random) -> Question:
    """Running totals: total = 0, then total += ... inside the loop."""
    kind = rng.choice(["range_sum", "list_sum", "so_far"])
    if kind == "range_sum":
        n = rng.randint(3, 5)
        code = f"total = 0\nfor i in range(1, {n + 1}):\n    total += i\nprint(total)"
        edits = [
            (f"range(1, {n + 1})", f"range({n})"),
            (f"range(1, {n + 1})", f"range(1, {n + 2})"),
            ("total = 0", "total = 1"),
            ("total += i", "total = i"),
        ]
        why = f"`total` starts at 0 and adds each `i` from 1 to {n}: {' + '.join(str(i) for i in range(1, n + 1))} = {n * (n + 1) // 2}."
    elif kind == "list_sum":
        plur, sing = rng.choice([("scores", "score"), ("points", "point"), ("coins", "coin")])
        items = [rng.randint(2, 12) for _ in range(rng.randint(3, 4))]
        code = f"{plur} = {_lst(items)}\ntotal = 0\nfor {sing} in {plur}:\n    total += {sing}\nprint(total)"
        edits = [
            (f"total += {sing}", f"total = {sing}"),
            (f"total += {sing}", "total += 1"),
            ("total = 0", "total = 1"),
            ("\nprint(total)", "\n    print(total)"),
        ]
        why = f"`total` starts at 0 and each pass adds one item of `{plur}`. After the loop it holds {sum(items)}."
    else:
        n = rng.randint(3, 4)
        code = f'total = 0\nfor i in range(1, {n + 1}):\n    total += i\n    print("Total so far:", total)'
        edits = [
            ('    print("Total so far:", total)', 'print("Total so far:", total)'),
            ("total += i", "total = i"),
            (f"range(1, {n + 1})", f"range({n})"),
            (f"range(1, {n + 1})", f"range(1, {n})"),
        ]
        why = "The `print` is inside the loop (indented), so it shows the running total after every pass, not just at the end."
    return _output(MEDIUM, code, edits, why, rng)


@generator(TOPIC, MEDIUM)
def gen_even_odd_output(rng: random.Random) -> Question:
    """Lesson section 6: for + if/else with the remainder operator."""
    m = rng.choice([2, 2, 2, 3, 5])
    while True:
        a = rng.randint(1, 8)
        if any(i % m == 0 for i in range(a, a + 3)) and any(i % m != 0 for i in range(a, a + 3)):
            break
    yes, no = ("is even", "is odd") if m == 2 else (f"is a multiple of {m}", f"is not a multiple of {m}")
    code = f'for i in range({a}, {a + 3}):\n    if i % {m} == 0:\n        print(i, "{yes}")\n    else:\n        print(i, "{no}")'
    edits = [
        ("== 0", "== 1"),
        (f"range({a}, {a + 3})", f"range({a - 1}, {a + 2})"),
        (f"range({a}, {a + 3})", f"range({a}, {a + 4})"),
        (f"range({a}, {a + 3})", f"range({a + 1}, {a + 4})"),
    ]
    return _output(
        MEDIUM,
        code,
        edits,
        f"`i % {m}` is the remainder after dividing by {m}. When it is 0 the `if` branch prints \"{yes}\"; otherwise the `else` branch prints \"{no}\". The range stops before {a + 3}.",
        rng,
    )


def _range_list(args: str) -> list[int]:
    return list(range(*(int(part) for part in args.split(","))))


@generator(TOPIC, MEDIUM)
def gen_header_for_task(rng: random.Random) -> Question:
    """'Which loop header prints ...?' -- odd numbers, counting by k."""
    kind = rng.choice(["odd", "even", "by_k", "by_k"])
    if kind == "odd":
        b = rng.choice([7, 9, 11, 13, 15])
        task, good = f"the odd numbers from 1 to {b}", f"1, {b + 1}, 2"
        bad = [f"1, {b}, 2", f"1, {b + 1}", f"0, {b + 1}, 2", f"2, {b + 1}, 2"]
    elif kind == "even":
        b = rng.choice([8, 10, 12, 14, 20])
        task, good = f"the even numbers from 2 to {b}", f"2, {b + 1}, 2"
        bad = [f"2, {b}, 2", f"0, {b + 1}, 2", f"1, {b + 1}, 2", f"2, {b + 1}"]
    else:
        k = rng.choice([3, 5, 10, 25, 100])
        m = rng.randint(4, 8)
        task, good = f"{k}, {2 * k}, {3 * k}, ... up to {m * k}", f"{k}, {m * k + 1}, {k}"
        bad = [f"{k}, {m * k}, {k}", f"0, {m * k + 1}, {k}", f"{k}, {m * k + 1}", f"1, {m * k + 1}, {k}"]
    want = _range_list(good)
    wrong = [f"for i in range({args}):" for args in bad if _range_list(args) != want]
    return _choice(
        MEDIUM,
        f"Which loop header counts through {task}?",
        f"for i in range({good}):",
        wrong,
        f"`range(start, stop, step)` stops right before `stop`, so `range({good})` gives {_csv(want[:3])}{', ...' if len(want) > 3 else ''}, ending at {want[-1]}.",
        rng,
    )


def _patch_q(prompt, code, target, good, bad, why, rng):
    """'Which change fixes the bug?' -- every patch is applied and the program is run."""

    def works(patch):
        old, new = patch
        res = run_code(code.replace(old, new, 1))
        return res.error is None and res.output == target

    if not works(good):
        raise GenerationError(f"the intended fix does not work: {good}")
    show = lambda p: f"Change `{p[0]}` to `{p[1]}`"  # noqa: E731
    return _choice(MEDIUM, prompt, show(good), [show(p) for p in bad if not works(p)], why, rng, code=code)


@generator(TOPIC, MEDIUM)
def gen_fix_the_bug(rng: random.Random) -> Question:
    """Classic mistakes from the lesson's troubleshooting tips."""
    kind = rng.choice(["missing_last", "starts_at_zero", "wrong_parity", "wrong_variable"])
    num = rng.randint(4, 8)
    if kind == "missing_last":
        code = f"num = {num}\nfor i in range(1, num):\n    print(i)"
        target = "\n".join(str(i) for i in range(1, num + 1))
        return _patch_q(
            "This code should print 1 through `num`, but the last number is missing. Which change fixes it?",
            code,
            target,
            ("range(1, num)", "range(1, num + 1)"),
            [("range(1, num)", "range(num)"), ("print(i)", "print(i + 1)"), ("range(1, num)", "range(0, num)"), ("range(1, num)", "range(1, num - 1)")],
            "The stop value is exclusive. Use `range(1, stop + 1)` for \"normal\" counting.",
            rng,
        )
    if kind == "starts_at_zero":
        code = f"num = {num}\nfor i in range(num):\n    print(i)"
        target = "\n".join(str(i) for i in range(1, num + 1))
        return _patch_q(
            "This code should print 1 through `num`, but it starts at 0. Which change fixes it?",
            code,
            target,
            ("range(num)", "range(1, num + 1)"),
            [("range(num)", "range(1, num)"), ("range(num)", "range(num + 1)"), ("print(i)", "print(i - 1)"), ("range(num)", "range(0, num + 1)")],
            "`range(stop)` starts at 0. To count 1 through `num`, start at 1 and stop at `num + 1`.",
            rng,
        )
    if kind == "wrong_parity":
        num = rng.choice([7, 9, 11])
        code = f"num = {num}\nfor i in range(0, num + 1, 2):\n    print(i)"
        target = "\n".join(str(i) for i in range(1, num + 1, 2))
        return _patch_q(
            "This code should print the odd numbers up to `num`, but it prints even numbers. Which change fixes it?",
            code,
            target,
            ("range(0, num + 1, 2)", "range(1, num + 1, 2)"),
            [("range(0, num + 1, 2)", "range(1, num + 1)"), ("range(0, num + 1, 2)", "range(1, num, 2)"), ("range(0, num + 1, 2)", "range(0, num + 1, 3)"), ("print(i)", "print(i - 1)")],
            "Counting by 2s from 0 gives even numbers. Start at 1 instead: `range(1, num + 1, 2)` gives 1, 3, 5, ...",
            rng,
        )
    sing, plur, msg, items = _pick_list(rng, 3)
    code = f'{plur} = {_lst(items)}\nfor {sing} in {plur}:\n    print("{msg}", {plur})'
    target = _lines(msg, items)
    return _patch_q(
        f'This code should print one line per item, like "{msg} {items[0]}", but it prints the whole list each time. Which change fixes it?',
        code,
        target,
        (f'print("{msg}", {plur})', f'print("{msg}", {sing})'),
        [(f"for {sing} in {plur}:", f"for {plur} in {sing}:"), (f"for {sing} in {plur}:", f"for {sing} in {sing}:"), (f'print("{msg}", {plur})', f'print("{msg} {sing}")')],
        f"`{sing}` is the current item; `{plur}` is the whole list. Print the singular name inside the loop.",
        rng,
    )


@generator(TOPIC, MEDIUM)
def gen_numbered_list(rng: random.Random) -> Question:
    """Challenge B (numbered favourites, 1) sushi) done with a counter variable."""
    sing, plur, _msg, items = _pick_list(rng, 3)
    kind = rng.choice(["trace", "missing_line", "reset"])
    body = f'for {sing} in {plur}:\n    print(f"{{number}}) {{{sing}}}")\n    number += 1'
    code = f"{plur} = {_lst(items)}\nnumber = 1\n{body}"
    target = "\n".join(f"{i}) {x}" for i, x in enumerate(items, 1))
    if kind == "trace":
        return _output(
            MEDIUM,
            code,
            [("\n    number += 1", ""), ("number = 1", "number = 0"), ("number += 1", "number += 2")],
            "`number` is the counter: it starts at 1 and `number += 1` adds one after every item, so the lines are numbered 1), 2), 3).",
            rng,
        )
    if kind == "missing_line":
        gap = f'{plur} = {_lst(items)}\nnumber = 1\nfor {sing} in {plur}:\n    print(f"{{number}}) {{{sing}}}")\n    # missing line'
        good, bad = "number += 1", ["number = 1", "number = number", f"{sing} += 1", "number + 1"]

        def works(line: str) -> bool:
            res = run_code(gap.replace("# missing line", line))
            return res.error is None and res.output == target

        if not works(good):
            raise GenerationError("numbered-list fix does not work")
        return _choice(
            MEDIUM,
            f"Which line belongs where the comment is, so the list prints as {target.splitlines()[0]}, {target.splitlines()[1]}, ...?",
            good,
            [b for b in bad if not works(b)],
            "The counter has to grow by 1 on every pass of the loop: `number += 1` inside the loop body.",
            rng,
            code=gap,
        )
    bug = f'{plur} = {_lst(items)}\nfor {sing} in {plur}:\n    number = 1\n    print(f"{{number}}) {{{sing}}}")\n    number += 1'
    return _choice(
        MEDIUM,
        "This should number the list 1), 2), 3), but every line starts with `1)`. What is wrong?",
        "`number = 1` is inside the loop, so it resets each pass",
        [
            "`number += 1` is missing from the loop",
            f"The loop should use `range(len({plur}))`",
            "An f-string can't contain a variable",
        ],
        "Set the counter up before the loop. If it is inside the loop, it goes back to 1 on every pass.",
        rng,
        code=bug,
    )


@generator(TOPIC, MEDIUM)
def gen_count_letter(rng: random.Random) -> Question:
    """for + if over a string: count one letter."""
    word = rng.choice(_COUNT_WORDS)
    letters = [c for c in set(word) if 1 <= word.count(c) <= 3]
    letter = rng.choice(sorted(letters))
    code = f'word = "{word}"\ncount = 0\nfor letter in word:\n    if letter == "{letter}":\n        count += 1\nprint(count)'
    n = word.count(letter)
    return _output(
        MEDIUM,
        code,
        [
            (f'if letter == "{letter}":', 'if letter != "' + letter + '":'),
            ("count = 0", "count = 1"),
        ],
        f"The loop checks every letter of \"{word}\" and adds 1 to `count` each time it finds \"{letter}\". It appears {n} time{'s' if n != 1 else ''}.",
        rng,
        extra=[str(len(word)), str(n + 1), str(max(n - 1, 0))],
    )


def _multiples(k: int, n: int) -> str:
    return "\n".join(str(i) for i in range(k, n + 1, k))


@generator(TOPIC, MEDIUM)
def gen_multiples_header(rng: random.Random) -> Question:
    """Challenge A (multiples of 3): which code prints every multiple of k from 1 through n?"""
    k = rng.choice([3, 3, 3, 4, 5])
    var = rng.choice(["n", "n", "num"])
    good_variants = [
        f"for i in range({k}, {var} + 1, {k}):\n    print(i)",
        f"for i in range(1, {var} + 1):\n    if i % {k} == 0:\n        print(i)",
    ]
    bad_pool = [
        f"for i in range({k}, {var}, {k}):\n    print(i)",
        f"for i in range(1, {var} + 1, {k}):\n    print(i)",
        f"for i in range(1, {var} + 1):\n    if i % {k} == 1:\n        print(i)",
        f"for i in range(1, {var}):\n    if i % {k} == 0:\n        print(i)",
        f"for i in range(1, {var} + 1):\n    if i / {k} == 0:\n        print(i)",
        f"for i in range({k}, {var} + 1):\n    print(i * {k})",
    ]

    def behaves(code: str) -> list[bool]:
        return [_run(f"{var} = {n}\n{code}") == _multiples(k, n) for n in range(1, 3 * k + 4)]

    good = rng.choice(good_variants)
    if not all(behaves(good)):
        raise GenerationError("multiples header is wrong")
    rng.shuffle(bad_pool)
    wrong = [b for b in bad_pool if not all(behaves(b))]
    return _choice(
        MEDIUM,
        f"Which code prints every multiple of {k} from 1 through `{var}` (inclusive), one per line?",
        good,
        wrong,
        f"Multiples of {k} are {k}, {2 * k}, {3 * k}, ... Either count by {k} with `range({k}, {var} + 1, {k})` or test every number with `i % {k} == 0`. The `+ 1` makes sure `{var}` itself is included.",
        rng,
    )


# ==========================================================================
# HARD -- a lab-style snippet with a twist, or two steps to trace
# ==========================================================================


@generator(TOPIC, HARD)
def gen_total_if_trace(rng: random.Random) -> Question:
    """for + if + running total: add only the numbers that pass a % test."""
    n = rng.randint(7, 10)
    kind = rng.choice(["even", "odd", "mult3", "count_even"])
    cond, flipped, test, label = {
        "even": ("i % 2 == 0", "i % 2 == 1", lambda i: i % 2 == 0, "even numbers"),
        "odd": ("i % 2 == 1", "i % 2 == 0", lambda i: i % 2 == 1, "odd numbers"),
        "mult3": ("i % 3 == 0", "i % 3 == 1", lambda i: i % 3 == 0, "multiples of 3"),
        "count_even": ("i % 2 == 0", "i % 2 == 1", lambda i: i % 2 == 0, "even numbers"),
    }[kind]
    add, other = ("1", "i") if kind == "count_even" else ("i", "1")
    code = f"total = 0\nfor i in range(1, {n + 1}):\n    if {cond}:\n        total += {add}\nprint(total)"
    picked = [i for i in range(1, n + 1) if test(i)]
    edits = [
        (f"range(1, {n + 1})", f"range(1, {n})"),
        (f"range(1, {n + 1})", f"range({n})"),
        (f"total += {add}", f"total += {other}"),
        (cond, flipped),
    ]
    if add == "i":
        why = f"Only the {label} pass `if {cond}`, so `total` adds up {' + '.join(map(str, picked))} = {sum(picked)}."
    else:
        why = f"`total` goes up by 1 each time `if {cond}` is True. That happens for {_csv(picked)}: {len(picked)} times."
    return _output(HARD, code, edits, why, rng, extra=[str(sum(range(1, n + 1)))])


@generator(TOPIC, HARD)
def gen_total_reset_bug(rng: random.Random) -> Question:
    """Gotcha: the accumulator is created INSIDE the loop (Programming Assessment hint)."""
    n = rng.randint(4, 7)
    code = f"for i in range(1, {n + 1}):\n    total = 0\n    total += i\nprint(total)"
    if rng.random() < 0.5:
        return output_question(
            topic=TOPIC,
            difficulty=HARD,
            code=code,
            distractors=[str(n * (n + 1) // 2), "0", str(n - 1), str(sum(range(1, n)))],
            explanation=f"`total = 0` runs again on every pass, so the earlier additions are thrown away. Only the last pass counts: `total` ends as {n}.",
            rng=rng,
        )
    return _choice(
        HARD,
        f"This code should print the total of 1 through {n} ({n * (n + 1) // 2}), but it prints {n}. What is wrong?",
        "`total = 0` is inside the loop, so it resets every pass",
        [
            "`total += i` should be `total = i`",
            "`range(1, ...)` should start at 0",
            "`print(total)` should be inside the loop",
        ],
        "Whatever keeps track of the total must exist before the repeating part starts. If you create it inside the loop, it goes back to 0 every time.",
        rng,
        code=code,
    )


@generator(TOPIC, HARD)
def gen_average_trace(rng: random.Random) -> Question:
    """Total with a loop, then divide by len(): `/` gives a float."""
    plur, sing = rng.choice([("scores", "score"), ("points", "point"), ("grades", "grade")])
    while True:
        items = [rng.randrange(60, 101, 5) for _ in range(rng.choice([3, 4]))]
        avg = sum(items) / len(items)
        if len(repr(avg)) <= 5:
            break
    code = (
        f"{plur} = {_lst(items)}\ntotal = 0\nfor {sing} in {plur}:\n    total += {sing}\n"
        f"average = total / len({plur})\nprint(average)"
    )
    return _output(
        HARD,
        code,
        [
            (f"total / len({plur})", f"total // len({plur})"),
            (f"total / len({plur})", "total"),
            (f"total / len({plur})", f"total / (len({plur}) + 1)"),
            (f"total / len({plur})", f"{items[-1]} / len({plur})"),
        ],
        f"The loop adds the items up (total {sum(items)}). Then `/` divides by the number of items ({len(items)}) and always gives a float: {avg}.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_break_in_for(rng: random.Random) -> Question:
    """`break` exits a for loop early; the line after the loop still runs."""
    if rng.random() < 0.5:
        sing, plur, _msg, items = _pick_list(rng, rng.randint(3, 4))
        stop_word = rng.choice(["quit", "quit", "stop", "done"])
        pos = rng.randint(1, 2)
        seq = [*items[:pos], stop_word, *items[pos:]]
        code = (
            f"{plur} = {_lst(seq)}\nfor {sing} in {plur}:\n    if {sing} == \"{stop_word}\":\n        break\n"
            f"    print({sing})\nprint(\"Done\")"
        )
        before = items[:pos]
        wrong = [
            "\n".join([*before, stop_word, "Done"]),
            "\n".join([*seq, "Done"]),
            "\n".join(before),
            "\n".join([*before, *items[pos:], "Done"]),
        ]
        why = f"The loop prints items until it reaches \"{stop_word}\"; `break` leaves the loop right there. The un-indented `print(\"Done\")` runs once after the loop."
    else:
        s = rng.choice([1, 2])
        k = rng.choice([3, 4, 5])
        code = f'for i in range({s}, {s + 6}):\n    if i % {k} == 0:\n        break\n    print(i)\nprint("Done")'
        before = list(range(s, next(i for i in range(s, s + 6) if i % k == 0)))
        wrong = [
            "\n".join([*map(str, before), str(before[-1] + 1), "Done"]),
            "\n".join([*map(str, range(s, s + 6)), "Done"]),
            "\n".join(map(str, before)),
            "\n".join([*(str(i) for i in range(s, s + 6) if i % k), "Done"]),
        ]
        why = f"The loop prints the numbers until `i % {k} == 0` is True at i = {before[-1] + 1}. `break` ends the loop before that number is printed, then \"Done\" prints once."
    return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=[w for w in wrong if _fits(w)], explanation=why, rng=rng)


@generator(TOPIC, HARD)
def gen_two_totals(rng: random.Random) -> Question:
    """Two running totals: even_total and odd_total (for + if/else)."""
    n = rng.randint(6, 8)
    code = (
        "even_total = 0\nodd_total = 0\n"
        f"for i in range(1, {n + 1}):\n    if i % 2 == 0:\n        even_total += i\n    else:\n        odd_total += i\n"
        "print(even_total, odd_total)"
    )
    return _output(
        HARD,
        code,
        [
            ("i % 2 == 0", "i % 2 == 1"),
            (f"range(1, {n + 1})", f"range(1, {n})"),
            (f"range(1, {n + 1})", f"range({n})"),
            ("even_total += i", "even_total += 1"),
        ],
        "Each number goes to exactly one total: even numbers into `even_total`, the rest into `odd_total`. `print` with a comma puts a space between the two values.",
        rng,
    )


@generator(TOPIC, HARD)
def gen_string_build(rng: random.Random) -> Question:
    """Build a new string one letter at a time (the string itself is never changed)."""
    word = rng.choice(["code", "loop", "tiger", "pixel", "snake", "quest", "orbit"])
    kind = rng.choice(["reverse", "dash", "double"])
    if kind == "reverse":
        body, edits = "result = letter + result", [("letter + result", "result + letter"), ("result = letter + result", "result = letter"), ('result = ""', 'result = "x"')]
        why = "Each new letter is glued on the FRONT of `result`, so the letters end up in reverse order."
    elif kind == "dash":
        body, edits = 'result = result + letter + "-"', [('result + letter + "-"', 'letter + "-" + result'), ('result + letter + "-"', 'result + letter'), ('result = ""', 'result = "-"')]
        why = "Every pass adds the letter and a dash to the END of `result`, so the last letter is followed by a dash too."
    else:
        body, edits = "result = result + letter * 2", [("letter * 2", "letter"), ("result + letter * 2", "letter * 2"), ("letter * 2", "letter * 3")]
        why = "`letter * 2` repeats the letter twice, and each pass adds those two letters to the end of `result`."
    code = f'word = "{word}"\nresult = ""\nfor letter in word:\n    {body}\nprint(result)'
    return _output(HARD, code, edits, why, rng, extra=[word.upper()])


@generator(TOPIC, HARD)
def gen_filter_count(rng: random.Random) -> Question:
    """Count the items in a range with a chained comparison -- boundary values matter."""
    lo = rng.choice([60, 70, 80])
    hi = lo + rng.choice([9, 19])
    inside = [rng.randint(lo + 1, hi - 1) for _ in range(rng.randint(1, 2))]
    edge = [lo, hi]
    outside = [lo - rng.randint(1, 15), hi + rng.randint(1, 8)]
    items = inside + edge + outside
    rng.shuffle(items)
    plur, sing = rng.choice([("scores", "score"), ("points", "point")])
    code = (
        f"{plur} = {_lst(items)}\ncount = 0\nfor {sing} in {plur}:\n    if {lo} <= {sing} <= {hi}:\n        count += 1\nprint(count)"
    )
    good = sum(1 for x in items if lo <= x <= hi)
    return _output(
        HARD,
        code,
        [
            (f"{lo} <= {sing}", f"{lo} < {sing}"),
            (f"<= {hi}:", f"< {hi}:"),
            (f"{lo} <= {sing} <= {hi}", f"{lo} < {sing} < {hi}"),
            ("count += 1", f"count += {sing}"),
        ],
        f"`{lo} <= {sing} <= {hi}` is a chained comparison that includes {lo} and {hi} themselves. Counting the items from {lo} to {hi}: {good}.",
        rng,
        extra=[str(len(items))],
    )


@generator(TOPIC, HARD)
def gen_how_many_with_step(rng: random.Random) -> Question:
    """Two-step trace: how many times does a stepped range run the body?"""
    step = rng.choice([2, 3, 4, 5])
    a = rng.randint(0, 3)
    b = a + step * rng.randint(3, 6) + rng.randint(1, step - 1)
    code = f"count = 0\nfor i in range({a}, {b}, {step}):\n    count += 1\nprint(count)"
    n = len(range(a, b, step))
    return _choice(
        HARD,
        "What does this code print?",
        str(n),
        [str((b - a) // step + 2), str((b - a) // step + 1 if (b - a) % step == 0 else (b - a) // step), str(b - a), str(b // step)],
        f"The values are {_csv(range(a, b, step))}: {n} numbers. The next step ({a + step * n}) would reach or pass the stop value {b}, so the loop ends.",
        rng,
        code=code,
    )


@generator(TOPIC, HARD)
def gen_ladder_in_loop(rng: random.Random) -> Question:
    """if/elif/else inside a loop: the ORDER of the checks decides which branch a number takes."""
    a = rng.randint(1, 6)
    w3 = rng.choice(["Fizz", "Three", "Ping"])
    w2 = rng.choice(["Even", "Two", "Pong"])

    def ladder(first: str, second: str) -> str:
        return (
            f"for i in range({a}, {a + 6}):\n    if i % {first[0]} == 0:\n        print(\"{first[1]}\")\n"
            f"    elif i % {second[0]} == 0:\n        print(\"{second[1]}\")\n    else:\n        print(i)"
        )

    code = ladder((3, w3), (2, w2))
    swapped = _run(ladder((2, w2), (3, w3)))
    as_ifs = code.replace("    elif i % 2", "    if i % 2")
    return _output(
        HARD,
        code,
        [(f"range({a}, {a + 6})", f"range({a}, {a + 5})"), (f"range({a}, {a + 6})", f"range({a - 1}, {a + 5})")],
        f"`if`/`elif` checks run in order and stop at the first True branch. A number that is a multiple of both 3 and 2 (like 6) takes the first branch, so it prints \"{w3}\".",
        rng,
        extra=[swapped, display_output(_run(as_ifs))] if _fits(_run(as_ifs)) else [swapped],
    )


# ==========================================================================
# BLANKS -- fill in the missing pieces (like the quiz's "fill in multiple blanks")
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_header(rng: random.Random) -> Question:
    """Anatomy of a for loop: for <variable> in <sequence>:"""
    if rng.random() < 0.6:
        sing, plur, msg, items = _pick_list(rng, 3)
        template = f'{plur} = {_lst(items)}\nfor {sing} {blank_mark(1)} {plur}{blank_mark(2)}\n    print("{msg}", {sing})'
        out = _lines(msg, items)
    else:
        word = rng.choice(_SHORT_WORDS)
        template = f'word = "{word}"\nfor letter {blank_mark(1)} word{blank_mark(2)}\n    print(letter)'
        out = "\n".join(word)
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Complete the `for` loop header.",
        template=template,
        blanks=[Blank(["in"], hint="keyword"), Blank([":"], hint="ends the header")],
        explanation="The anatomy of a loop is `for <variable> in <sequence>:` followed by an indented block.",
        expect_output=out,
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_range(rng: random.Random) -> Question:
    """Fill in the range() arguments: 1 through num, a step, or 0 up to n - 1."""
    kind = rng.choice(["inclusive", "inclusive", "step", "stop_only"])
    if kind == "inclusive":
        num = rng.randint(4, 8)
        template = f"num = {num}\nfor i in range({blank_mark(1)}, {blank_mark(2)}):\n    print(i)"
        blanks = [
            Blank(["1"], hint="start", mode="expr"),
            Blank(["num + 1", "1 + num", str(num + 1)], hint="stop", mode="expr"),
        ]
        prompt = f"Fill in the blanks so the loop prints 1 through `num` ({_csv(range(1, num + 1))})."
        out = "\n".join(str(i) for i in range(1, num + 1))
        why = "Start at 1, and since the stop value is exclusive, stop at `num + 1`."
    elif kind == "step":
        step, num = rng.choice([(2, rng.choice([7, 9, 11])), (5, rng.choice([20, 25, 30])), (3, rng.choice([10, 13, 16]))])
        start = 1 if step == 2 else 0
        template = f"num = {num}\nfor i in range({start}, num + 1, {blank_mark(1)}):\n    print(i)"
        values = list(range(start, num + 1, step))
        blanks = [Blank([str(step)], hint="step", mode="expr")]
        prompt = f"Fill in the blank so the loop prints {_csv(values)}."
        out = "\n".join(str(v) for v in values)
        why = f"The third number in `range(start, stop, step)` is the step. Counting by {step} from {start} gives {_csv(values)}."
    else:
        n = rng.randint(3, 6)
        template = f'for i in range({blank_mark(1)}):\n    print("Hello", i)'
        blanks = [Blank([str(n)], hint="how many times", mode="expr")]
        prompt = f"Fill in the blank so the loop prints `Hello 0` up to `Hello {n - 1}`."
        out = _lines("Hello", range(n))
        why = f"`range({n})` counts 0 up to {n - 1}, so the loop runs {n} times."
    return blanks_question(topic=TOPIC, difficulty=EASY, prompt=prompt, template=template, blanks=blanks, explanation=why, expect_output=out)


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_even_odd(rng: random.Random) -> Question:
    """Lesson section 6: for + if with the remainder operator."""
    kind = rng.choice(["even", "odd", "multiple"])
    if kind in ("even", "odd"):
        want = 0 if kind == "even" else 1
        label = "is even" if kind == "even" else "is odd"
        top = rng.randint(5, 7)
        template = (
            f"for i in range(1, {top}):\n    if i {blank_mark(1)} 2 == {blank_mark(2)}:\n"
            f'        print(i, "{label}")'
        )
        blanks = [Blank(["%"], hint="operator"), Blank([str(want)], hint="remainder", mode="expr")]
        prompt = f"Fill in the blanks so only the {kind} numbers are printed."
        why = "`i % 2` is the remainder when `i` is divided by 2: it is 0 for even numbers and 1 for odd numbers."
        out = "\n".join(f"{i} {label}" for i in range(1, top) if i % 2 == want)
    else:
        k = rng.choice([3, 4, 5])
        top = rng.randint(11, 16)
        template = f'for i in range(1, {top}):\n    if i {blank_mark(1)} {blank_mark(2)} == 0:\n        print(i, "is a multiple of {k}")'
        blanks = [Blank(["%"], hint="operator"), Blank([str(k)], hint="number", mode="expr")]
        prompt = f"Fill in the blanks so only the multiples of {k} are printed."
        why = f"`i % {k} == 0` means the remainder is 0 when `i` is divided by {k}, so `i` is a multiple of {k}."
        out = "\n".join(f"{i} is a multiple of {k}" for i in range(1, top) if i % k == 0)
    return blanks_question(topic=TOPIC, difficulty=MEDIUM, prompt=prompt, template=template, blanks=blanks, explanation=why, expect_output=out)


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_counter(rng: random.Random) -> Question:
    """Challenge B: number a list with a counter variable (1) sushi, 2) pizza ...)."""
    sing, plur, _msg, items = _pick_list(rng, 3)
    template = (
        f"{plur} = {_lst(items)}\nnumber = {blank_mark(1)}\nfor {sing} in {blank_mark(2)}:\n"
        f'    print(f"{{number}}) {{{sing}}}")\n    {blank_mark(3)} += 1'
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Fill in the blanks so the list is numbered `1)`, `2)`, `3)`, ... using a counter variable.",
        template=template,
        blanks=[
            Blank(["1"], hint="start", mode="expr"),
            Blank([plur], hint="the whole list"),
            Blank(["number"], hint="the counter"),
        ],
        explanation=f"The counter starts at 1 before the loop, the loop goes through `{plur}`, and `number += 1` adds one after every item.",
        expect_output="\n".join(f"{i}) {x}" for i, x in enumerate(items, 1)),
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_total(rng: random.Random) -> Question:
    """Running total / counting with an accumulator."""
    if rng.random() < 0.6:
        n = rng.randint(4, 7)
        template = (
            f"n = {n}\ntotal = {blank_mark(1)}\nfor i in range(1, {blank_mark(2)}):\n    total {blank_mark(3)} i\nprint(total)"
        )
        blanks = [
            Blank(["0"], hint="start value", mode="expr"),
            Blank(["n + 1", "1 + n", str(n + 1)], hint="stop", mode="expr"),
            Blank(["+=", "= total +"], hint="add to total"),
        ]
        prompt = f"Fill in the blanks so the code prints the total of 1 through `n` ({n * (n + 1) // 2})."
        why = "The total starts at 0, the range goes up to `n + 1` so that `n` is included, and `total += i` adds each number."
        out = str(n * (n + 1) // 2)
    else:
        word = rng.choice(_COUNT_WORDS)
        letter = rng.choice(sorted(c for c in set(word) if 1 <= word.count(c) <= 3))
        template = (
            f'word = "{word}"\ncount = {blank_mark(1)}\nfor letter in word:\n    if letter {blank_mark(2)} "{letter}":\n'
            f"        count {blank_mark(3)} 1\nprint(count)"
        )
        blanks = [
            Blank(["0"], hint="start value", mode="expr"),
            Blank(["=="], hint="compare"),
            Blank(["+=", "= count +"], hint="add 1"),
        ]
        prompt = f'Fill in the blanks so the code prints how many times "{letter}" appears in the word.'
        why = "`count` starts at 0, `==` compares each letter with the one we are looking for (a single `=` would be an assignment), and `count += 1` counts a match."
        out = str(word.count(letter))
    return blanks_question(topic=TOPIC, difficulty=HARD, prompt=prompt, template=template, blanks=blanks, explanation=why, expect_output=out)


# ==========================================================================
# MATCH
# ==========================================================================


def _range_spec(rng: random.Random, form: str):
    if form == "stop":
        n = rng.randint(2, 6)
        return f"range({n})", list(range(n))
    if form == "start_stop":
        a = rng.randint(1, 4)
        b = a + rng.randint(2, 5)
        return f"range({a}, {b})", list(range(a, b))
    step = rng.choice([2, 3, 5])
    a = rng.choice([0, 1, 2])
    b = a + step * rng.randint(2, 4) + rng.randint(1, step - 1)
    return f"range({a}, {b}, {step})", list(range(a, b, step))


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_range_values(rng: random.Random) -> Question:
    """Match each range(...) to the numbers it produces."""
    forms = ["stop", "stop", "start_stop", "start_stop", "step"]
    for _ in range(50):
        specs = [_range_spec(rng, f) for f in rng.sample(forms, 4)]
        if len({_csv(v) for _, v in specs}) == 4 and len({e for e, _ in specs}) == 4:
            break
    else:
        raise GenerationError("could not draw four different ranges")
    expr, vals = rng.choice(specs)
    decoy = _csv([*vals, vals[-1] + 1])
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each `range` to the numbers a loop gets from it.",
        pairs=[(e, _csv(v)) for e, v in specs],
        extra_options=[decoy] if decoy not in {_csv(v) for _, v in specs} else [],
        explanation="`range(stop)` starts at 0; `range(start, stop)` starts at `start`; the stop value is never included; the third number is the step.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_header_values(rng: random.Random) -> Question:
    """Match each for-loop header to what the loop variable holds."""
    a, b = rng.randint(1, 3), rng.randint(5, 8)
    step = rng.choice([2, 3])
    word = rng.choice(["go", "hi", "yes", "cat"])
    sing, plur, _msg, _items = _pick_list(rng, 3)
    pairs = [
        (f"for i in range({b - 2}):", f"i is {_csv(range(b - 2))}"),
        (f"for i in range({a}, {b}):", f"i is {_csv(range(a, b))}"),
        (f"for i in range({a}, {b}, {step}):", f"i is {_csv(range(a, b, step))}"),
        (f'for letter in "{word}":', f"letter is {_csv(word)}, one at a time"),
        (f"for {sing} in {plur}:", f"{sing} is each item in the list {plur}"),
    ]
    if len({p[1] for p in pairs}) != 5:
        raise GenerationError("two headers give the same values")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each loop header to the values the loop variable takes.",
        pairs=pairs,
        explanation="The loop variable takes each value of the sequence, one at a time: numbers from `range`, characters of a string, or items of a list.",
        rng=rng,
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_loop_parts(rng: random.Random) -> Question:
    """Anatomy: for <variable> in <sequence>:"""
    var, seq = rng.choice(
        [("i", "range(5)"), ("i", "range(1, 11)"), ("fruit", "fruits"), ("letter", "word"), ("item", "my_list"), ("score", "scores"), ("i", "range(num)")]
    )
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Match each part of `for {var} in {seq}:` to its job.",
        pairs=[
            ("for", "Starts the loop"),
            (var, "The loop variable (one value at a time)"),
            ("in", "Connects the variable to the sequence"),
            (seq, "The sequence to loop over"),
            (":", "Ends the header, an indented block follows"),
        ],
        explanation="Anatomy of a `for` loop: `for <variable> in <sequence>:` then an indented block. The loop variable takes on each value from the sequence, one at a time.",
        rng=rng,
    )


# ==========================================================================
# CODE -- type real Python, graded in the sandbox
# ==========================================================================


@generator(TOPIC, EASY, qtype="code")
def gen_code_condition(rng: random.Random) -> Question:
    """for + if with %: type the condition (even / odd / multiple of k)."""
    kind = rng.choice(["even", "odd", "mult"])
    var = rng.choice(["i", "i", "num"])
    if kind == "even":
        sol, what, test = f"{var} % 2 == 0", "even", lambda v: v % 2 == 0
        why = f"`{var} % 2` is the remainder after dividing by 2, so `{var} % 2 == 0` is True for even numbers."
    elif kind == "odd":
        sol, what, test = f"{var} % 2 == 1", "odd", lambda v: v % 2 == 1
        why = f"`{var} % 2` is 1 for odd numbers, so `{var} % 2 == 1` (or `!= 0`) is True when `{var}` is odd."
    else:
        k = rng.choice([3, 5])
        sol, what, test = f"{var} % {k} == 0", f"a multiple of {k}", lambda v, k=k: v % k == 0
        why = f"A multiple of {k} leaves remainder 0 when divided by {k}, so `{var} % {k} == 0`."
    yes = rng.sample([v for v in range(1, 40) if test(v)], 3)
    no = rng.sample([v for v in range(1, 40) if not test(v)], 3)
    cases = [({var: v}, bool(test(v))) for v in (yes[0], no[0], yes[1], no[1], yes[2], no[2])]
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Inside the loop below, type the condition that is `True` when `{var}` is {what}.",
        task=expression_task(sol, cases),
        explanation=why,
        code=f"for {var} in range(1, 40):\n    if <your condition>:\n        print({var})",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_loop_items(rng: random.Random) -> Question:
    """Lesson sections 4 and 5: loop over a list, or over the letters of a string."""
    if rng.random() < 0.65:
        sing, plur, msg, pool = rng.choice(_LISTS)
        lists = [rng.sample(pool, k) for k in (3, 1, 4, 2)]
        cases = [Case(vars={plur: items}, out=_lines(msg, items)) for items in lists]
        solution = f'for {sing} in {plur}:\n    print("{msg}", {sing})'
        prompt = f"The list `{plur}` already exists. Write a `for` loop that prints `{msg}` and the {sing} on one line for each {sing}, like `{msg} {lists[0][0]}`."
        shown = f"{plur} = {_lst(lists[0])}"
        why = f"Loop through the list with a singular name for each item (`for {sing} in {plur}:`), then print the message and `{sing}`."
    else:
        words = rng.sample([*_SHORT_WORDS, "python"], 4)
        cases = [Case(vars={"word": w}, out="\n".join(w)) for w in words]
        solution = "for letter in word:\n    print(letter)"
        prompt = "The variable `word` already holds a string. Write a `for` loop that prints each letter of `word` on its own line."
        shown = f'word = "{words[0]}"'
        why = "A string is a sequence of characters, so `for letter in word:` visits each one. Print `letter` inside the loop."
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why, code=shown)


@generator(TOPIC, EASY, qtype="code")
def gen_code_print_range(rng: random.Random) -> Question:
    """Lesson sections 1-2: range(n) and range(1, n + 1)."""
    var = rng.choice(["num", "num", "n"])
    kind = rng.choice(["one_to_n", "zero_to_n", "hello"])
    if kind == "one_to_n":
        values = [rng.randint(5, 9), 1, rng.randint(2, 4), rng.randint(5, 10)]
        solution = f"for i in range(1, {var} + 1):\n    print(i)"
        outs = ["\n".join(str(i) for i in range(1, v + 1)) for v in values]
        prompt = f"`{var}` already holds a whole number. Write a `for` loop that prints 1 through `{var}` (including `{var}`), one number per line."
        why = f"The stop value is exclusive, so use `range(1, {var} + 1)` to include `{var}`."
    elif kind == "zero_to_n":
        values = [rng.randint(4, 8), 1, rng.randint(2, 3), rng.randint(4, 9)]
        solution = f"for i in range({var}):\n    print(i)"
        outs = ["\n".join(str(i) for i in range(v)) for v in values]
        prompt = f"`{var}` already holds a whole number. Write a `for` loop that prints 0 up to `{var} - 1`, one number per line."
        why = f"`range({var})` starts at 0 and stops before `{var}`."
    else:
        values = [rng.randint(3, 5), 1, rng.randint(2, 3), rng.randint(4, 6)]
        solution = f'for i in range({var}):\n    print("Hello", i)'
        outs = [_lines("Hello", range(v)) for v in values]
        prompt = f"`{var}` already holds a whole number. Write a `for` loop that runs `{var}` times and prints `Hello 0`, `Hello 1`, ... (one line per pass)."
        why = f'`range({var})` gives `{var}` values starting at 0, and `print("Hello", i)` puts a space between the two parts.'
    seen: dict = {}
    for v, o in zip(values, outs):
        seen.setdefault(v, o)
    cases = [Case(vars={var: v}, out=o) for v, o in seen.items()]
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=program_task(solution, cases, examples=2), explanation=why, code=f"{var} = {values[0]}")


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_step_program(rng: random.Random) -> Question:
    """Lesson section 3: odd numbers, counting by 5s, counting by 100s."""
    start, step, var, what = rng.choice(
        [
            (1, 2, "num", "the odd numbers from 1 up to `num`"),
            (1, 2, "num", "the odd numbers from 1 up to `num`"),
            (2, 2, "num", "the even numbers from 2 up to `num`"),
            (0, 5, "num", "0, 5, 10, ... (counting by 5s) up to `num`"),
            (1, 100, "target", "1, 101, 201, ... (counting by 100s from 1) up to `target`"),
            (3, 3, "num", "3, 6, 9, ... (counting by 3s) up to `num`"),
        ]
    )
    values = [
        start + step * rng.randint(2, 5),
        start + step * rng.randint(1, 3) + rng.randint(1, step - 1),
        start,
        start + step * rng.randint(3, 5) + rng.randint(1, step - 1),
    ]
    values = list(dict.fromkeys(values))
    cases = [Case(vars={var: v}, out="\n".join(str(i) for i in range(start, v + 1, step))) for v in values]
    solution = f"for i in range({start}, {var} + 1, {step}):\n    print(i)"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`{var}` already holds a whole number. Write a `for` loop that prints {what} (including `{var}` itself if it is reached), one number per line.",
        task=program_task(solution, cases, examples=2),
        explanation=f"Use the three-argument form `range(start, stop, step)`: start at {start}, stop at `{var} + 1` so `{var}` is allowed, and count by {step}.",
        code=f"{var} = {values[0]}",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_multiples(rng: random.Random) -> Question:
    """Challenge A -- Multiples of 3 (ask for n, print the multiples from 1 through n)."""
    k = rng.choice([3, 3, 3, 4, 5])
    ns = [k * rng.randint(2, 5) + rng.randint(1, k - 1), k * rng.randint(2, 5), rng.randint(1, k - 1), k]
    ns = list(dict.fromkeys(ns))
    cases = [Case(stdin=[str(n)], out="\n".join(str(i) for i in range(k, n + 1, k))) for n in ns]
    solution = f'n = int(input("Enter a number: "))\nfor i in range({k}, n + 1, {k}):\n    print(i)'
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks the user for a number `n` (an int) and prints every multiple of {k} from 1 through `n` (inclusive), one per line. Print nothing if there are none.",
        task=program_task(solution, cases, starter='n = int(input("Enter a number: "))\n', examples=2),
        explanation=f"Count by {k} with `range({k}, n + 1, {k})`, or loop through every number and test `i % {k} == 0`. The `+ 1` includes `n` itself when it is a multiple of {k}.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_numbered(rng: random.Random) -> Question:
    """Challenge B -- Favorite Things, numbered with a counter variable (not enumerate)."""
    sing, plur, _msg, pool = rng.choice(_LISTS)
    fmt, shown_fmt = rng.choice([("{n}) {x}", "1) sushi"), ("{n}) {x}", "1) sushi"), ("{n}. {x}", "1. sushi"), ("#{n} {x}", "#1 sushi")])
    lists = [rng.sample(pool, k) for k in (3, 1, 5, 2)]
    shown_fmt = shown_fmt.replace("sushi", lists[0][0])
    cases = [Case(vars={plur: items}, out="\n".join(fmt.format(n=i, x=x) for i, x in enumerate(items, 1))) for items in lists]
    pre, post = fmt.split("{n}")[0], fmt.split("{n}")[1].split("{x}")[0]
    solution = f'number = 1\nfor {sing} in {plur}:\n    print(f"{pre}{{number}}{post}{{{sing}}}")\n    number += 1'
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"The list `{plur}` already exists. Write a loop that prints the items numbered from 1, like `{shown_fmt}`. Use a counter variable.",
        task=program_task(solution, cases, examples=2, forbids=[(r"\benumerate\b", "Use a counter variable that you add 1 to, not enumerate()")]),
        explanation="Make a counter before the loop (`number = 1`), print it with each item, then add 1 with `number += 1` at the end of every pass.",
        code=f"{plur} = {_lst(lists[0])}",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_even_odd(rng: random.Random) -> Question:
    """Lesson section 6: print whether each number from 1 through num is even or odd."""
    m = rng.choice([2, 2, 3])
    yes, no = ("is even", "is odd") if m == 2 else ("is a multiple of 3", "is not a multiple of 3")
    values = list(dict.fromkeys([rng.randint(4, 6), 1, rng.randint(2, 3), rng.randint(5, 7)]))
    cases = [Case(vars={"num": v}, out="\n".join(f"{i} {yes if i % m == 0 else no}" for i in range(1, v + 1))) for v in values]
    solution = f'for i in range(1, num + 1):\n    if i % {m} == 0:\n        print(i, "{yes}")\n    else:\n        print(i, "{no}")'
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`num` already holds a whole number. For each number from 1 through `num`, print the number followed by `{yes}` or `{no}`, like `3 {yes if 3 % m == 0 else no}`.",
        task=program_task(solution, cases, examples=2),
        explanation=f"Loop with `range(1, num + 1)` and test `i % {m} == 0`: the `if` branch prints one message, the `else` branch prints the other.",
        code=f"num = {values[0]}",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_list_total(rng: random.Random) -> Question:
    """Running total over a list."""
    plur, sing, label = rng.choice([("scores", "score", "Total:"), ("points", "point", "Total points:"), ("coins", "coin", "Total coins:"), ("prices", "price", "Total:")])
    lists = [[rng.randint(3, 30) for _ in range(3)], [rng.randint(1, 20)], [rng.randint(2, 9)] * 4, [], [rng.randint(10, 60) for _ in range(5)]]
    cases = [Case(vars={plur: items}, out=f"{label} {sum(items)}") for items in lists]
    solution = f"total = 0\nfor {sing} in {plur}:\n    total += {sing}\nprint(\"{label}\", total)"
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"The list `{plur}` already exists (it may be empty). Use a `for` loop to add up its numbers, then print `{label}` and the total on one line, like `{label} {sum(lists[0])}`.",
        task=program_task(solution, cases, examples=2, requires=[(r"\bfor\b", "Use a for loop to add up the numbers")]),
        explanation="Start `total = 0` before the loop, add each item with `total += ...` inside it, and print once after the loop (not indented).",
        code=f"{plur} = {lists[0]}",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_times_table(rng: random.Random) -> Question:
    """Bingo: generate a multiplication table."""
    top = rng.choice([5, 10, 10, 12])
    ns = list(dict.fromkeys([rng.randint(2, 9), rng.randint(10, 12), 1, rng.randint(2, 9)]))
    cases = [Case(vars={"n": n}, out="\n".join(f"{n} x {i} = {n * i}" for i in range(1, top + 1))) for n in ns]
    solution = f'for i in range(1, {top + 1}):\n    print(n, "x", i, "=", n * i)'
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"`n` already holds a whole number. Print its multiplication table from 1 to {top}, one line per row, like `{ns[0]} x 1 = {ns[0]}`.",
        task=program_task(solution, cases, examples=1),
        explanation=f"Loop `i` from 1 through {top} with `range(1, {top + 1})`, and print `n`, \"x\", `i`, \"=\" and `n * i` (print puts spaces between the pieces).",
        code=f"n = {ns[0]}",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_running_total(rng: random.Random) -> Question:
    """Challenge C -- Running Total: keep asking for numbers until the user enters 0."""
    style = rng.choice([0, 0, 1, 2])
    each, last = [
        ("Total so far:", "You entered {c} numbers. Final total: {t}"),
        ("Running total:", "{c} numbers entered. Final total: {t}"),
        ("Sum so far:", "Entries: {c}. Final sum: {t}"),
    ][style]
    lesson = [rng.randint(2, 15), rng.randint(2, 15), rng.randint(2, 15)]
    runs = [
        lesson,
        [],
        [rng.randint(1, 20)],
        [rng.randint(3, 12), -rng.randint(1, 3), rng.randint(5, 20), rng.randint(1, 9)],
        [8, -8, rng.randint(2, 6)],  # a total of 0 in the middle must not stop the loop
    ]
    cases = []
    for nums in runs:
        total, lines = 0, []
        for x in nums:
            total += x
            lines.append(f"{each} {total}")
        lines.append(last.format(c=len(nums), t=total))
        cases.append(Case(stdin=[*map(str, nums), "0"], out="\n".join(lines)))
    solution = (
        "total = 0\ncount = 0\nwhile True:\n    num = int(input(\"Enter a number (0 to stop): \"))\n    if num == 0:\n        break\n"
        f"    total += num\n    count += 1\n    print(\"{each}\", total)\n"
        + [
            'print("You entered", count, "numbers. Final total:", total)',
            'print(count, "numbers entered. Final total:", total)',
            'print("Entries: " + str(count) + ". Final sum:", total)',
        ][style]
    )
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            "Write a program that keeps asking for whole numbers, one at a time. Add each number to a running total and print "
            f"`{each} <total>` after every entry. When the user enters `0`, stop and print `{last.format(c='<count>', t='<total>')}` "
            "(the 0 itself does not count)."
        ),
        task=program_task(solution, cases, examples=2),
        explanation="Keep a `total` and a `count` that start at 0 before the loop. Inside the loop read a number, `break` when it is 0, otherwise add it, count it and print the total so far. Print the summary after the loop.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_ask_n_numbers(rng: random.Random) -> Question:
    """Let the user choose how many times (lesson section 2) + a running total (Match Tracker style)."""
    things, noun, unit = rng.choice(
        [("matches", "eliminations", "match"), ("laps", "seconds", "lap"), ("rounds", "points", "round"), ("levels", "coins", "level")]
    )
    runs = [
        [rng.randint(1, 9) for _ in range(3)],
        [rng.randint(1, 9)],
        [],
        [rng.randint(0, 9) for _ in range(5)],
        [rng.randint(5, 20), 0, rng.randint(1, 4), rng.randint(3, 9)],
    ]
    cases = [Case(stdin=[str(len(nums)), *map(str, nums)], out=f"Total {noun}: {sum(nums)}") for nums in runs]
    solution = (
        f'count = int(input("How many {things}? "))\ntotal = 0\nfor i in range(1, count + 1):\n'
        f'    total += int(input(f"{noun.capitalize()} in {unit} {{i}}: "))\nprint("Total {noun}:", total)'
    )
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"Write a program that first asks how many {things} were played (an int), then asks for the {noun} in each one. "
            f"At the end print `Total {noun}:` and the total on one line (for example `Total {noun}: 13`)."
        ),
        task=program_task(solution, cases, examples=2),
        explanation="The number of repeats is known after the first `input()`, so use `for i in range(count)` (or `range(1, count + 1)`). Create `total = 0` BEFORE the loop and add each answer inside it.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_count_filter(rng: random.Random) -> Question:
    """Count the items of a list that pass a test (for + if + counter)."""
    kind = rng.choice(["even", "big", "mult3"])
    plur, sing = rng.choice([("numbers", "number"), ("scores", "score"), ("points", "point")])
    if kind == "even":
        cond, test, what = f"{sing} % 2 == 0", (lambda v: v % 2 == 0), "even"
    elif kind == "big":
        t = rng.choice([10, 50, 70])
        cond, test, what = f"{sing} > {t}", (lambda v, t=t: v > t), f"greater than {t}"
    else:
        cond, test, what = f"{sing} % 3 == 0", (lambda v: v % 3 == 0), "multiples of 3"
    hi = 20 if kind == "even" or kind == "mult3" else 100
    lo = [v for v in range(1, hi) if not test(v)]
    ok = [v for v in range(1, hi + 10) if test(v)]
    lists = [
        [rng.choice(ok), rng.choice(lo), rng.choice(ok), rng.choice(lo), rng.choice(lo)],
        [rng.choice(lo), rng.choice(lo)],
        [rng.choice(ok), rng.choice(ok), rng.choice(ok)],
        [rng.choice(lo), rng.choice(ok), rng.choice(lo), rng.choice(ok), rng.choice(ok), rng.choice(lo)],
        [],
    ]
    if kind == "big":
        lists[0].append(t)  # the boundary value itself must NOT be counted
    cases = [Case(vars={plur: items}, out=str(sum(1 for v in items if test(v)))) for items in lists]
    solution = f"count = 0\nfor {sing} in {plur}:\n    if {cond}:\n        count += 1\nprint(count)"
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"The list `{plur}` already exists (it may be empty). Write a program that counts how many of its numbers are {what} and prints just that count.",
        task=program_task(solution, cases, examples=2),
        explanation="Start `count = 0` before the loop, test each item with an `if`, add 1 when it passes, and print the count once after the loop.",
        code=f"{plur} = {lists[0]}",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_reverse_word(rng: random.Random) -> Question:
    """Build a new string with a loop (the original string never changes)."""
    words = rng.sample([*_SHORT_WORDS, "python", "robot", "level", "a"], 5)
    cases = [Case(vars={"word": w}, out=w[::-1]) for w in words]
    solution = 'result = ""\nfor letter in word:\n    result = letter + result\nprint(result)'
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="`word` already holds a string. Use a `for` loop to build a new string with the letters in reverse order, then print it (no slicing).",
        task=program_task(
            solution,
            cases,
            examples=2,
            requires=[(r"\bfor\b", "Use a for loop")],
            forbids=[(r":\s*:\s*-\s*1", "Build the reversed word with a loop, not slicing"), (r"\breversed\b", "Build the reversed word with a loop")],
        ),
        explanation="Start with `result = \"\"`. On each pass put the new letter in FRONT of what you have so far: `result = letter + result`. Print after the loop.",
        code=f'word = "{words[0]}"',
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_fizz(rng: random.Random) -> Question:
    """for + if/elif/else with %: the order of the checks matters (both multiples first)."""
    a, wa, b, wb = rng.choice([(3, "Fizz", 5, "Buzz"), (2, "Tic", 3, "Tac"), (3, "Ping", 4, "Pong")])
    lcm = {(3, 5): 15, (2, 3): 6, (3, 4): 12}[(a, b)]

    def lines(n: int) -> str:
        out = []
        for i in range(1, n + 1):
            if i % a == 0 and i % b == 0:
                out.append(wa + wb)
            elif i % a == 0:
                out.append(wa)
            elif i % b == 0:
                out.append(wb)
            else:
                out.append(str(i))
        return "\n".join(out)

    ns = list(dict.fromkeys([lcm, rng.randint(2, lcm - 1), lcm + rng.randint(1, 3), 1]))
    cases = [Case(vars={"n": n}, out=lines(n)) for n in ns]
    solution = (
        f'for i in range(1, n + 1):\n    if i % {a} == 0 and i % {b} == 0:\n        print("{wa}{wb}")\n'
        f'    elif i % {a} == 0:\n        print("{wa}")\n    elif i % {b} == 0:\n        print("{wb}")\n    else:\n        print(i)'
    )
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"`n` already holds a whole number. For each number from 1 through `n`, print `{wa}` if it is a multiple of {a}, "
            f"`{wb}` if it is a multiple of {b}, `{wa}{wb}` if it is a multiple of both, and otherwise the number itself."
        ),
        task=program_task(solution, cases, examples=1),
        explanation=f"Check the 'both' case first (`i % {a} == 0 and i % {b} == 0`), because an `elif` ladder stops at the first True branch. Then the single cases, then `else`.",
        code=f"n = {ns[0]}",
    )
