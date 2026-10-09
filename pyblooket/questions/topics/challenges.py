"""Question generators for the "challenges" topic (Mini-Challenges: CSF.2.K / CSF.2.O).

Every question here is "write the program" (qtype ``code``, graded in the sandbox).  The stories come
from the lab mini-challenges (Profile Line, Double It, First Name Slice, Sign Checker, Countdown,
Multiples of 3, Favorite Things, Running Total, the function trio, Triangle), from the Programming
Assessment (Rank Checker, Match Tracker) and from the 50 Python Bingo tasks.  Each prompt says exactly
what to print, because the checker compares the output line by line.  What goes inside ``input("...")``
is never shown or graded, so players can word their prompts as they like.
"""

from __future__ import annotations

import random
from math import factorial

from ..base import (
    EASY,
    HARD,
    MEDIUM,
    NAMES,
    WORDS,
    Question,
    code_question,
    function_task,
    generator,
    program_task,
)
from ..spec import Case

TOPIC = "challenges"

FOODS = ["sushi", "pizza", "tacos", "ramen", "pancakes", "burgers", "noodles", "waffles"]
GAMES = ["basketball", "chess", "soccer", "minecraft", "tag", "volleyball", "Fortnite", "Mario Kart"]
SONGS = ["lo-fi beats", "rock", "jazz", "pop hits", "country", "movie scores", "synthwave"]
SCHOOLS = ["DBHS", "Lincoln High", "Central High", "Ridgeview High", "Tech Prep"]
SURNAMES = ["Lovelace", "Turing", "Hopper", "Johnson", "Jackson", "Torvalds", "Ritchie", "Wozniak", "Berners", "Cerf"]
PHRASES = [
    "banana bread", "a rare red rose", "pepper and salt", "learn python today", "balloon animals",
    "assess the stress", "mississippi river", "coffee break", "tattoo parlor", "bookkeeper",
]


def _make(difficulty: int, prompt: str, task, explanation: str, code: str | None = None) -> Question:
    return code_question(topic=TOPIC, difficulty=difficulty, prompt=prompt, task=task, explanation=explanation, code=code)


def _runs(stdins, fn) -> list[Case]:
    """One case per input script; ``fn(inputs)`` gives the exact printed text."""
    return [Case(stdin=[str(s) for s in ins], out=fn(ins)) for ins in stdins]


# ==========================================================================
# EASY - a few lines
# ==========================================================================


@generator(TOPIC, EASY, qtype="code")
def gen_hello_name(rng: random.Random) -> Question:
    """Bingo: use an f-string to greet someone by name."""
    start, end = rng.choice([("Hello, ", "!"), ("Welcome, ", "!"), ("Hi ", "!"), ("Good luck, ", "!"), ("Hey ", ", ready to code?")])
    names = rng.sample(NAMES, 4)
    cases = [Case(vars={"name": n}, out=f"{start}{n}{end}") for n in names]
    solution = f'print(f"{start}{{name}}{end}")'
    task = program_task(solution, cases, examples=2)
    return _make(
        EASY,
        f"The variable `name` already holds a first name. Use an f-string to print `{start}` followed by the name and then `{end}`. For `{names[0]}` it prints `{start}{names[0]}{end}`.",
        task,
        "An f-string puts the variable inside the text: `f\"Hello, {name}!\"`. Keep the exact spaces and punctuation from the prompt.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_profile_line(rng: random.Random) -> Question:
    """Mini-Challenge "Profile Line": one sentence with three variables."""
    template = rng.choice(
        [
            ("{name} started at {school} in {year} and has a GPA of {gpa}", "{name} started at {school} in {year_started} and has a GPA of {gpa}"),
            ("{name} joined {school} in {year} with a GPA of {gpa}", "{name} joined {school} in {year_started} with a GPA of {gpa}"),
            ("In {year}, {name} began at {school}. GPA: {gpa}", "In {year_started}, {name} began at {school}. GPA: {gpa}"),
        ]
    )
    shown, source = template
    rows = []
    for _ in range(4):
        rows.append(
            {"name": rng.choice(NAMES), "school": rng.choice(SCHOOLS), "year_started": rng.choice([2020, 2021, 2022, 2023, 2024]), "gpa": rng.choice([3.2, 3.5, 3.7, 3.9, 4.0, 2.8])}
        )
    rows = [dict(t) for t in {tuple(sorted(r.items())) for r in rows}]
    rng.shuffle(rows)
    cases = [Case(vars=r, out=source.format(**r)) for r in rows]
    solution = "print(f\"" + source.replace("{year_started}", "{year_started}") + "\")"
    task = program_task(solution, cases, examples=2)
    first = rows[0]
    return _make(
        EASY,
        "The variables `name`, `school`, `year_started` and `gpa` already exist. Print ONE sentence built with an f-string, shaped like this example: "
        f"`{source.format(**first)}`",
        task,
        "Put each variable in braces inside an f-string. `gpa` and `year_started` are numbers, but an f-string turns them into text for you.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_add_two_inputs(rng: random.Random) -> Question:
    """Bingo: add two numbers and print the result (numbers arrive through input())."""
    label, what = rng.choice(
        [("Total:", "points"), ("Sum:", "numbers"), ("Together:", "coins"), ("Score:", "scores"), ("Eliminations:", "eliminations")]
    )
    pairs = [(rng.randint(1, 30), rng.randint(1, 30)) for _ in range(4)]
    pairs = list(dict.fromkeys(pairs))
    cases = _runs(pairs, lambda ins: f"{label} {int(ins[0]) + int(ins[1])}")
    solution = f"a = int(input())\nb = int(input())\nprint(\"{label}\", a + b)"
    task = program_task(solution, cases, examples=1)
    a, b = pairs[0]
    return _make(
        EASY,
        f"Ask for two whole numbers (two `input()` calls) and print `{label}` followed by their sum. Typing `{a}` then `{b}` prints `{label} {a + b}`.",
        task,
        "`input()` gives text, so cast each answer with `int()` before adding. `print(\"label\", value)` puts a space between the pieces.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_double_it(rng: random.Random) -> Question:
    """Mini-Challenge "Double It" (and its Triple / Half cousins)."""
    word, op, fn = rng.choice(
        [("Double", "* 2", lambda x: x * 2), ("Triple", "* 3", lambda x: x * 3), ("Half", "/ 2", lambda x: x / 2), ("Plus ten", "+ 10", lambda x: x + 10)]
    )
    values = rng.sample(["4", "2.5", "10", "0.5", "7", "12", "3.5", "1.25"], 4)
    cases = _runs([[v] for v in values], lambda ins: f"{word}: {fn(float(ins[0]))}")
    solution = f'n = float(input())\nprint("{word}:", n {op})'
    task = program_task(solution, cases, starter="n = input()\n", examples=2)
    return _make(
        EASY,
        f"Ask the user for a number, cast it to `float`, and print `{word}:` followed by the answer (the number {op.replace('*', 'times').replace('/', 'divided by').replace('+', 'plus')}). Typing `{values[0]}` prints `{word}: {fn(float(values[0]))}`.",
        task,
        "Cast first: `n = float(n)`. A float stays a float, so even `4` becomes `4.0` in the output.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_slice_letters(rng: random.Random) -> Question:
    """Bingo: slice a string to get the first 3 characters (and similar slices)."""
    kind, text, expr = rng.choice(
        [
            ("first", "the first 3 letters", "word[:3]"),
            ("first4", "the first 4 letters", "word[0:4]"),
            ("last", "the last letter", "word[-1]"),
            ("last2", "the last 2 letters", "word[-2:]"),
            ("firstlast", "the first letter followed by the last letter (no space)", "word[0] + word[-1]"),
        ]
    )
    words = rng.sample([w for w in WORDS if len(w) >= 5] + ["python", "program", "keyboard"], 4)
    cases = [Case(vars={"word": w}, out=str(eval(expr, {}, {"word": w}))) for w in words]  # noqa: S307 - our own slices
    task = program_task(f"print({expr})", cases, examples=2)
    return _make(
        EASY,
        f"The variable `word` already holds a word. Print {text} of it. For `{words[0]}` that is `{cases[0].out}`.",
        task,
        "Indexing starts at 0 and `-1` is the last character. A slice `word[start:end]` leaves out the end position.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_word_tricks(rng: random.Random) -> Question:
    """Bingo: reverse a string using slicing (plus shouting and counting)."""
    kind = rng.choice(["reverse", "shout", "length"])
    words = rng.sample(["robot", "python", "keyboard", "pixel", "dragon", "monitor", "laptop", "coder"], 4)
    if kind == "reverse":
        solution, out_of = "print(word[::-1])", lambda w: w[::-1]
        ask = "Print the word backwards (spelled in reverse)."
        why = "`word[::-1]` is the slice that steps backwards through the whole string."
    elif kind == "shout":
        solution, out_of = 'print(word.upper() + "!")', lambda w: w.upper() + "!"
        ask = "Print the word in capital letters followed by an exclamation mark."
        why = "`.upper()` returns a new string in capitals; add `\"!\"` to it with `+` (or use an f-string)."
    else:
        solution, out_of = 'print("Length:", len(word))', lambda w: f"Length: {len(w)}"
        ask = "Print `Length:` followed by the number of letters in the word."
        why = "`len(word)` counts the characters; `print(\"Length:\", number)` separates them with a space."
    cases = [Case(vars={"word": w}, out=out_of(w)) for w in words]
    task = program_task(solution, cases, examples=2)
    return _make(EASY, f"The variable `word` already holds a word. {ask} For `{words[0]}` it prints `{cases[0].out}`.", task, why)


@generator(TOPIC, EASY, qtype="code")
def gen_count_letter(rng: random.Random) -> Question:
    """Bingo: count how many 'a' letters are in a string."""
    letter = rng.choice(["a", "e", "o", "s", "n"])
    texts = rng.sample(PHRASES, 4)
    cases = [Case(vars={"text": t}, out=str(t.count(letter))) for t in texts]
    if len({c.out for c in cases}) < 2:
        cases[0] = Case(vars={"text": letter * 3 + " test"}, out=str((letter * 3 + " test").count(letter)))
    task = program_task(f'print(text.count("{letter}"))', cases, examples=2)
    return _make(
        EASY,
        f"The variable `text` already holds a sentence. Print how many times the letter `{letter}` appears in it (just the number). For \"{texts[0]}\" that is {cases[0].out}.",
        task,
        f"The string method `.count()` does it: `text.count(\"{letter}\")`. Only the number should be printed.",
    )


@generator(TOPIC, EASY, qtype="code")
def gen_simple_interest(rng: random.Random) -> Question:
    """Bingo: compute simple interest for principal, rate and time."""
    name = rng.choice(["simple_interest", "interest", "earn_interest"])
    combos = [(p, r, t) for p in (500, 1000, 1500, 2000, 2500) for r in (2, 4, 5, 10) for t in (1, 2, 3, 5)]
    picks = rng.sample(combos, 5)
    cases = [((p, r, t), p * r * t / 100) for p, r, t in picks]
    solution = f"def {name}(principal, rate, time):\n    return principal * rate * time / 100"
    task = function_task(name, solution, cases, examples=2)
    p, r, t = picks[0]
    return _make(
        EASY,
        f"Write a function `{name}(principal, rate, time)` that returns the simple interest: principal times rate times time, divided by 100. `{name}({p}, {r}, {t})` returns {p * r * t / 100}.",
        task,
        "Multiply the three values and divide by 100. Use `return` so the caller gets the number; `/` always gives a float.",
    )


# ==========================================================================
# MEDIUM - input + decisions, counting loops, small functions
# ==========================================================================


@generator(TOPIC, MEDIUM, qtype="code")
def gen_sign_checker(rng: random.Random) -> Question:
    """Mini-Challenge "Sign Checker": Positive / Negative / Zero."""
    pos, neg, zero = rng.choice(
        [("Positive", "Negative", "Zero"), ("Gain", "Loss", "Even"), ("Above", "Below", "Level"), ("Up", "Down", "Same")]
    )
    values = [0, rng.randint(1, 60), -rng.randint(1, 60), rng.randint(100, 900), -rng.randint(100, 900)]
    rng.shuffle(values)
    cases = _runs([[v] for v in values], lambda ins: pos if int(ins[0]) > 0 else neg if int(ins[0]) < 0 else zero)
    solution = f'n = int(input())\nif n > 0:\n    print("{pos}")\nelif n < 0:\n    print("{neg}")\nelse:\n    print("{zero}")'
    task = program_task(solution, cases, examples=2)
    return _make(
        MEDIUM,
        f"Ask for a whole number with `input()`. Print `{pos}` if it is more than 0, `{neg}` if it is less than 0, or `{zero}` if it is exactly 0.",
        task,
        "Cast with `int()`, then use `if` / `elif` / `else`: the three cases are > 0, < 0 and (everything left) 0.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_rank_checker(rng: random.Random) -> Question:
    """Programming Assessment, challenge 1: Rank Checker (three ranks)."""
    low, high = rng.choice([(1000, 2000), (500, 1500), (100, 250), (50, 90), (300, 800)])
    names = rng.choice([("Bronze", "Silver", "Gold"), ("Rookie", "Pro", "Legend"), ("Wood", "Iron", "Steel")])
    def rank(s: int) -> str:
        return names[0] if s < low else names[1] if s < high else names[2]
    scores = [low - 1, low, (low + high) // 2, high - 1, high, high + rng.randint(5, 900), max(0, low - rng.randint(5, low - 1))]
    scores = list(dict.fromkeys(scores))
    rng.shuffle(scores)
    cases = _runs([[s] for s in scores], lambda ins: f"You earned {rank(int(ins[0]))} rank!")
    solution = (
        f'score = int(input())\nif score < {low}:\n    rank = "{names[0]}"\nelif score < {high}:\n    rank = "{names[1]}"\nelse:\n    rank = "{names[2]}"\n'
        f'print("You earned", rank, "rank!")'
    )
    task = program_task(solution, cases, examples=2)
    return _make(
        MEDIUM,
        f"Ask the player for their match score (a whole number) and print their rank: `{names[0]}` for less than {low}, `{names[1]}` for {low} to {high - 1}, `{names[2]}` for {high} or more. "
        f"The output looks like `You earned {names[1]} rank!`.",
        task,
        f"`input()` gives text, so cast it to a number first. Check the lowest range first: `< {low}`, then `< {high}`, and let `else` catch the rest.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_grade_ladder(rng: random.Random) -> Question:
    """Lesson H: the elif grade ladder."""
    cut = rng.choice([(90, 80, 70, 60), (93, 85, 75, 65), (90, 80, 70, 50)])
    def grade(s: int) -> str:
        return "A" if s >= cut[0] else "B" if s >= cut[1] else "C" if s >= cut[2] else "D" if s >= cut[3] else "F"
    scores = [cut[0], cut[0] - 1, cut[1], cut[2] + 4, cut[3], cut[3] - 1, 100, rng.randint(0, 40)]
    scores = list(dict.fromkeys(scores))
    rng.shuffle(scores)
    cases = _runs([[s] for s in scores], lambda ins: f"Grade: {grade(int(ins[0]))}")
    solution = (
        f'score = int(input())\nif score >= {cut[0]}:\n    print("Grade: A")\nelif score >= {cut[1]}:\n    print("Grade: B")\n'
        f'elif score >= {cut[2]}:\n    print("Grade: C")\nelif score >= {cut[3]}:\n    print("Grade: D")\nelse:\n    print("Grade: F")'
    )
    task = program_task(solution, cases, examples=2)
    return _make(
        MEDIUM,
        f"Ask for a score (a whole number) and print `Grade: A` for {cut[0]} or more, `Grade: B` for {cut[1]} or more, `Grade: C` for {cut[2]} or more, `Grade: D` for {cut[3]} or more, and `Grade: F` for anything lower.",
        task,
        "Python takes the first branch that is True, so test the highest threshold first and work down with `elif`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_countdown(rng: random.Random) -> Question:
    """Mini-Challenge "Countdown": count down to 1, then Blastoff!"""
    end = rng.choice(["Blastoff!", "Liftoff!", "Go!", "Happy New Year!"])
    starts = rng.sample(range(1, 9), 4)
    cases = _runs([[s] for s in starts], lambda ins: "\n".join([*(str(i) for i in range(int(ins[0]), 0, -1)), end]))
    solution = f'n = int(input())\nwhile n > 0:\n    print(n)\n    n -= 1\nprint("{end}")'
    task = program_task(solution, cases, examples=2)
    return _make(
        MEDIUM,
        f"Ask for a starting number (a positive whole number). Print the numbers from there down to 1, one per line, then print `{end}`. Starting at 3 prints 3, 2, 1 and then `{end}`.",
        task,
        "A `while` loop with an update works: print the counter, subtract 1, and stop when it reaches 0. A `for` loop with `range(n, 0, -1)` works too.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_multiples(rng: random.Random) -> Question:
    """Mini-Challenge A (Loops part 2): multiples of 3 from 1 through n."""
    k = rng.choice([3, 3, 4, 5, 7])
    limits = [k * rng.randint(3, 6), k * rng.randint(3, 6) + rng.randint(1, k - 1), k, k - 1, k * 2 + 1]
    limits = list(dict.fromkeys(limits))
    rng.shuffle(limits)
    cases = _runs([[n] for n in limits], lambda ins: "\n".join(str(i) for i in range(k, int(ins[0]) + 1, k)))
    solution = f"n = int(input())\nfor i in range(1, n + 1):\n    if i % {k} == 0:\n        print(i)"
    task = program_task(solution, cases, examples=2)
    n0 = limits[0]
    return _make(
        MEDIUM,
        f"Ask for a number `n`. Print every multiple of {k} from 1 through `n` (including `n` itself if it is one), one per line. For `{n0}` that prints {', '.join(str(i) for i in range(k, n0 + 1, k))}, each on its own line. If there are none, print nothing.",
        task,
        f"Loop over `range(1, n + 1)` and print `i` when `i % {k} == 0`; or count by {k} with `range({k}, n + 1, {k})`.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_favorite_things(rng: random.Random) -> Question:
    """Mini-Challenge B (Loops part 2): a numbered list of favourites."""
    sep = rng.choice([") ", ". ", ": ", " - "])
    pools = [FOODS, GAMES, SONGS]
    lists = []
    for size in (3, 5, 4, 6):
        lists.append(rng.sample(rng.choice(pools), min(size, 6)))
    lists = [list(t) for t in dict.fromkeys(tuple(x) for x in lists)]
    cases = [Case(vars={"things": items}, out="\n".join(f"{i}{sep}{x}" for i, x in enumerate(items, 1))) for items in lists]
    solution = f'number = 1\nfor thing in things:\n    print(str(number) + "{sep}" + thing)\n    number += 1'
    task = program_task(
        solution,
        cases,
        examples=1,
        forbids=[(r"\benumerate\b", "enumerate comes later in the course - use a counter variable")],
    )
    first = lists[0]
    return _make(
        MEDIUM,
        f"The list `things` already exists. Loop through it and print each item numbered from 1, like `1{sep}{first[0]}`, `2{sep}{first[1]}`, ... (one per line, the number then `{sep.strip() or sep}` then the item). Use a counter variable.",
        task,
        "Make a counter before the loop (`number = 1`), print it with the item, then add 1 at the end of each pass.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_name_initial(rng: random.Random) -> Question:
    """Mini-Challenge "First Name Slice": first name and last initial."""
    style = rng.choice(["Ada L.", "L., Ada", "A. L."])
    firsts = rng.sample(NAMES, 4)
    lasts = rng.sample(SURNAMES, 4)
    def fmt(f: str, l: str) -> str:
        return {"Ada L.": f"{f} {l[0]}.", "L., Ada": f"{l[0]}., {f}", "A. L.": f"{f[0]}. {l[0]}."}[style]
    cases = _runs([[f"{f} {l}"] for f, l in zip(firsts, lasts)], lambda ins: fmt(*ins[0].split(" ")))
    body = {
        "Ada L.": 'print(first + " " + last[0] + ".")',
        "L., Ada": 'print(last[0] + ".,", first)',
        "A. L.": 'print(first[0] + ". " + last[0] + ".")',
    }[style]
    solution = f'full = input()\nfirst, last = full.split(" ")\n{body}'
    task = program_task(solution, cases, examples=2)
    f0, l0 = firsts[0], lasts[0]
    return _make(
        MEDIUM,
        f"Ask for a full name (first and last name with one space between). Print it as `{cases[0].out}` when the input is `{f0} {l0}` - that is {'the first name, a space, the last initial and a period' if style == 'Ada L.' else 'the last initial, a period and a comma, then the first name' if style == 'L., Ada' else 'both initials, each followed by a period'}.",
        task,
        "`.split(\" \")` turns the name into a list of words; index `[0]` of a word is its first letter.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_function_trio(rng: random.Random) -> Question:
    """The Functions mini-challenge: fahrenheit_to_celsius, square_area, average (plus the reverse conversion)."""
    which = rng.choice(["f_to_c", "c_to_f", "square_area", "average", "rect_area"])
    if which == "f_to_c":
        name, params, expr, doc = "fahrenheit_to_celsius", "f", "(f - 32) * 5 / 9", "converts degrees Fahrenheit to Celsius: subtract 32, multiply by 5, divide by 9"
        args = [(212,), (32,), (50,), (98,), (-40,), (0,)]
        val = lambda a: (a[0] - 32) * 5 / 9  # noqa: E731
    elif which == "c_to_f":
        name, params, expr, doc = "celsius_to_fahrenheit", "c", "c * 9 / 5 + 32", "converts degrees Celsius to Fahrenheit: multiply by 9, divide by 5, add 32"
        args = [(0,), (100,), (37,), (-40,), (20,), (25,)]
        val = lambda a: a[0] * 9 / 5 + 32  # noqa: E731
    elif which == "square_area":
        name, params, expr, doc = "square_area", "side", "side * side", "returns the area of a square (side times side)"
        args = [(3,), (5,), (10,), (1,), (7,), (12,)]
        val = lambda a: a[0] * a[0]  # noqa: E731
    elif which == "rect_area":
        name, params, expr, doc = "rectangle_area", "width, height", "width * height", "returns the area of a rectangle (width times height)"
        args = [(3, 4), (5, 5), (10, 2), (1, 9), (6, 7), (12, 3)]
        val = lambda a: a[0] * a[1]  # noqa: E731
    else:
        name, params, expr, doc = "average", "a, b, c", "(a + b + c) / 3", "returns the average of three numbers"
        args = [(2, 4, 6), (1, 2, 4), (10, 20, 30), (0, 0, 9), (5, 5, 5), (7, 8, 10)]
        val = lambda a: (a[0] + a[1] + a[2]) / 3  # noqa: E731
    picks = rng.sample(args, 5)
    cases = [(a, val(a)) for a in picks]
    solution = f"def {name}({params}):\n    return {expr}"
    task = function_task(name, solution, cases, examples=2)
    a0 = picks[0]
    return _make(
        MEDIUM,
        f"Write a function `{name}({params})` that {doc}. It must `return` the answer (not print it). For example `{name}({', '.join(map(str, a0))})` returns {val(a0)}.",
        task,
        "Write the formula after `return`. `/` always gives a float, so the results are floats like `4.0`.",
    )


# ==========================================================================
# HARD - loops with input and a sentinel, accumulators, several decisions, small classes
# ==========================================================================


def _example(lines: list[str], limit: int = 6) -> str:
    shown = lines[:limit]
    return "; ".join(shown) + ("; ..." if len(lines) > limit else "")


@generator(TOPIC, HARD, qtype="code")
def gen_running_total(rng: random.Random) -> Question:
    """Loops part 2, Challenge C "Running Total": 0 stops the loop."""
    unit, plural, label, final = rng.choice(
        [
            ("number", "numbers", "Total so far:", "Final total:"),
            ("score", "scores", "Score so far:", "Final score:"),
            ("price", "prices", "Spent so far:", "Final bill:"),
            ("point value", "point values", "Points so far:", "Final points:"),
        ]
    )

    def lines_for(seq: list[int]) -> list[str]:
        out, total = [], 0
        for v in seq:
            total += v
            out.append(f"{label} {total}")
        out.append(f"You entered {len(seq)} {plural}. {final} {total}")
        return out

    seqs = [
        [rng.randint(1, 20) for _ in range(rng.randint(3, 4))],
        [rng.randint(1, 15), rng.randint(16, 40)],
        [],
        [rng.randint(5, 25), -rng.randint(1, 4), rng.randint(5, 25), rng.randint(1, 9)],
    ]
    rng.shuffle(seqs)
    cases = [Case(stdin=[*map(str, s), "0"], out="\n".join(lines_for(s))) for s in seqs]
    solution = (
        f'count = 0\ntotal = 0\nn = int(input())\nwhile n != 0:\n    total += n\n    count += 1\n    print("{label}", total)\n    n = int(input())\n'
        f'print("You entered", count, "{plural}.", "{final}", total)'
    )
    task = program_task(solution, cases, examples=2)
    ex = next(s for s in seqs if len(s) >= 2)
    return _make(
        HARD,
        f"Keep asking for a {unit} (a whole number) until the user types `0`. After each {unit} print `{label}` and the running total. "
        f"When `0` is typed, stop and print `You entered N {plural}. {final} T` (N counts the entries, T is the total; the `0` itself is not counted). "
        f"For the input {', '.join(map(str, ex))}, 0 it prints: {_example(lines_for(ex))}.",
        task,
        "Make `count` and `total` BEFORE the loop (inside it they would reset each time). Read a number, loop while it is not 0, add it, print, then read the next one.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_match_tracker(rng: random.Random) -> Question:
    """Programming Assessment, challenge 2: Match Tracker (total, and the average bonus)."""
    event, unit, units, total_label = rng.choice(
        [
            ("eliminations", "match", "matches", "Total eliminations:"),
            ("goals", "game", "games", "Total goals:"),
            ("points", "round", "rounds", "Total points:"),
            ("coins", "level", "levels", "Total coins:"),
        ]
    )
    bonus = rng.random() < 0.5
    avg_label = f"Average {event} per {unit}:"
    counts = rng.sample([2, 4, 5], 3) + [1] if bonus else rng.sample([1, 2, 3, 4, 5, 6], 3) + [0]
    cases = []
    for n in counts:
        vals = [rng.randint(0, 12) for _ in range(n)]
        total = sum(vals)
        out = [f"{total_label} {total}"]
        if bonus:
            out.append(f"{avg_label} {total / n}")
        cases.append(Case(stdin=[str(n), *map(str, vals)], out="\n".join(out)))
    rng.shuffle(cases)
    solution = f"n = int(input())\ntotal = 0\nfor i in range(n):\n    total += int(input())\nprint(\"{total_label}\", total)"
    if bonus:
        solution += f'\nprint("{avg_label}", total / n)'
    task = program_task(solution, cases, examples=2)
    ex = next(c for c in cases if int(c.stdin[0]) >= 2)
    extra = f" Then print `{avg_label}` and the total divided by the number of {units}." if bonus else f" (If there are 0 {units} the total is 0.)"
    return _make(
        HARD,
        f"Ask how many {units} were played (a whole number), then ask for the {event} in each one (one `input()` per {unit}). "
        f"Print `{total_label}` and the total.{extra} For the input {', '.join(ex.stdin)} it prints `{ex.out.splitlines()[0]}`"
        + (f" and `{ex.out.splitlines()[1]}`." if bonus else "."),
        task,
        f"Make `total = 0` BEFORE the loop, then loop that many times (`for i in range(n)`) adding `int(input())`. "
        + ("`total / n` is a float, so the average prints like `4.0`." if bonus else "Created inside the loop, `total` would be reset every time."),
    )


@generator(TOPIC, HARD, qtype="code")
def gen_rank_with_diamond(rng: random.Random) -> Question:
    """Programming Assessment, challenge 1 bonus: add a top rank, then mind the order of the checks."""
    a, b, c = rng.choice([(1000, 2000, 3000), (500, 1500, 2500), (100, 200, 300), (250, 500, 1000), (2000, 4000, 6000)])
    names = rng.choice(
        [("Bronze", "Silver", "Gold", "Diamond"), ("Rookie", "Pro", "Master", "Legend"), ("Wood", "Iron", "Steel", "Titanium"), ("Pawn", "Knight", "Queen", "King")]
    )

    def rank(s: int) -> str:
        return names[0] if s < a else names[1] if s < b else names[2] if s < c else names[3]

    scores = list(dict.fromkeys([a - 1, a, b - 1, b, c - 1, c, c + rng.randint(1, 900), rng.randint(0, a - 1)]))
    rng.shuffle(scores)
    cases = _runs([[s] for s in scores], lambda ins: f"You earned {rank(int(ins[0]))} rank!")
    solution = (
        f"score = int(input())\nif score >= {c}:\n    rank = \"{names[3]}\"\nelif score >= {b}:\n    rank = \"{names[2]}\"\nelif score >= {a}:\n    rank = \"{names[1]}\"\nelse:\n    rank = \"{names[0]}\"\n"
        "print(\"You earned\", rank, \"rank!\")"
    )
    task = program_task(solution, cases, examples=2)
    return _make(
        HARD,
        f"Ask for the player's score (a whole number) and print `You earned RANK rank!`. The ranks: `{names[0]}` for less than {a}, `{names[1]}` for {a} to {b - 1}, `{names[2]}` for {b} to {c - 1}, `{names[3]}` for {c} or more. "
        f"A score of {c} prints `You earned {names[3]} rank!`.",
        task,
        f"With a ladder of `if` / `elif`, Python stops at the first True branch, so test the highest score first (`>= {c}`, then `>= {b}`, then `>= {a}`). Checking `>= {a}` first would give everyone {names[1]}.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_password_loop(rng: random.Random) -> Question:
    """Bingo: keep asking for the password until it is correct."""
    count_tries = rng.random() < 0.5
    secrets = rng.sample(["python123", "letmein", "blooket", "opensesame", "gold2026", "swordfish", "pixel99", "tigers"], 4)
    wrongs = ["password", "123456", "qwerty", "Python123", "guess", "abc", "hello", "Letmein"]
    plans = [0, 2, 1, 3]
    cases = []
    for secret, wrong_count in zip(secrets, plans):
        attempts = rng.sample([w for w in wrongs if w != secret], wrong_count) + [secret]
        if wrong_count and secret.upper() != secret:
            attempts[0] = secret.upper()  # a right word in the wrong case is still a wrong guess
        out = ["Wrong password. Try again."] * wrong_count
        out.append(f"Access granted. Attempts: {wrong_count + 1}" if count_tries else "Access granted!")
        cases.append(Case(vars={"password": secret}, stdin=attempts, out="\n".join(out)))
    rng.shuffle(cases)
    if count_tries:
        solution = (
            'tries = 1\nguess = input()\nwhile guess != password:\n    print("Wrong password. Try again.")\n    tries += 1\n    guess = input()\nprint("Access granted. Attempts:", tries)'
        )
        finale = "`Access granted. Attempts: N` (N is how many guesses it took, counting the right one)"
    else:
        solution = 'guess = input()\nwhile guess != password:\n    print("Wrong password. Try again.")\n    guess = input()\nprint("Access granted!")'
        finale = "`Access granted!`"
    task = program_task(solution, cases, examples=2)
    return _make(
        HARD,
        f"The variable `password` holds the secret word. Keep asking for a guess with `input()`. A guess only matches when it is exactly the same (capital letters count). Every wrong guess prints `Wrong password. Try again.`; when the guess matches, print {finale} and stop asking.",
        task,
        "Read the first guess before the loop, loop `while guess != password`, and read the next guess at the bottom of the loop body. Capital letters matter: `PYTHON123` is not `python123`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_quit_loop(rng: random.Random) -> Question:
    """Bingo: `while True` with a break on a keyword."""
    keyword = rng.choice(["quit", "stop", "exit", "done"])
    echo = rng.choice(["You typed:", "Echo:", "Got it:", "Received:"])
    closing = rng.choice(["Loop ended.", "Goodbye!", "Session closed.", "Finished."])
    pools = [["hi"], ["apple", "banana", "cherry"], [], ["python", "is", "fun", "yes"], ["go", "stopping", "quitting"]]
    picks = [rng.choice(pools[:2] + pools[3:]), pools[2], rng.choice([pools[1], pools[4]]), pools[3]]
    picks = [list(t) for t in dict.fromkeys(tuple(p) for p in picks)]
    rng.shuffle(picks)
    cases = [Case(stdin=[*p, keyword], out="\n".join([*(f"{echo} {w}" for w in p), closing])) for p in picks]
    solution = f'while True:\n    text = input()\n    if text == "{keyword}":\n        break\n    print("{echo}", text)\nprint("{closing}")'
    task = program_task(solution, cases, examples=2)
    ex = next(p for p in picks if len(p) >= 2)
    return _make(
        HARD,
        f"Use a `while True` loop that keeps asking for text with `input()`. Each time print `{echo}` followed by what was typed. When the user types exactly `{keyword}`, leave the loop with `break` (don't echo it) and print `{closing}`. "
        f"Typing {', '.join(ex)}, {keyword} prints: {_example([f'{echo} {w}' for w in ex] + [closing])}.",
        task,
        f"`while True:` never ends on its own, so check `if text == \"{keyword}\":` inside the loop and `break` out of it. The closing line is OUTSIDE the loop (not indented).",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_sum_positives(rng: random.Random) -> Question:
    """Bingo: sum user-entered positives until 0 (ignoring the negatives)."""
    label = rng.choice(["Sum of positives:", "Positive total:", "Points earned:"])
    seqs = [
        [rng.randint(1, 20), rng.randint(1, 20), rng.randint(1, 20)],
        [rng.randint(1, 15), -rng.randint(1, 9), rng.randint(5, 30), -rng.randint(1, 20)],
        [],
        [-rng.randint(1, 9), -rng.randint(1, 9)],
    ]
    rng.shuffle(seqs)
    cases = _runs([[*s, 0] for s in seqs], lambda ins: f"{label} {sum(int(v) for v in ins if int(v) > 0)}")
    solution = f'total = 0\nn = int(input())\nwhile n != 0:\n    if n > 0:\n        total += n\n    n = int(input())\nprint("{label}", total)'
    task = program_task(solution, cases, examples=2)
    ex = seqs[1] if len(seqs[1]) > 2 else seqs[0]
    return _make(
        HARD,
        f"Keep asking for whole numbers until the user types `0`. Add only the POSITIVE numbers to a total (ignore negatives) and finish by printing `{label}` and the total. "
        f"For the input {', '.join(map(str, ex))}, 0 it prints `{label} {sum(v for v in ex if v > 0)}`.",
        task,
        "`0` is the stop signal (it ends the loop, it isn't added). Inside the loop, only do `total += n` when `n > 0`; read the next number at the bottom of the loop.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_multiplication_table(rng: random.Random) -> Question:
    """Bingo: generate a multiplication table for 1-10."""
    sym = rng.choice([" x ", " * ", " times "])
    ns = rng.sample(range(2, 13), 4)
    cases = _runs([[n] for n in ns], lambda ins: "\n".join(f"{ins[0]}{sym}{i} = {int(ins[0]) * i}" for i in range(1, 11)))
    solution = f'n = int(input())\nfor i in range(1, 11):\n    print(f"{{n}}{sym}{{i}} = {{n * i}}")'
    task = program_task(solution, cases, examples=1)
    return _make(
        HARD,
        f"Ask for a whole number `n` and print its multiplication table from 1 through 10, one line each, like `{ns[0]}{sym}1 = {ns[0]}`, `{ns[0]}{sym}2 = {ns[0] * 2}`, ... up to `{ns[0]}{sym}10 = {ns[0] * 10}`.",
        task,
        "`for i in range(1, 11)` runs i = 1 ... 10 (the stop value is left out). An f-string builds each line: `f\"{n} x {i} = {n * i}\"`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_loop_function(rng: random.Random) -> Question:
    """Bingo: factorial with a loop (and three of its cousins)."""
    which = rng.choice(["factorial", "sum_to", "power", "count_evens"])
    forbids = []
    if which == "factorial":
        name, params = "factorial", "n"
        body = "result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result"
        ask = "returns n factorial: 1 * 2 * 3 * ... * n, and `1` when `n` is 0 or 1"
        args = [(0,), (1,), (3,), (5,), (6,), (8,)]
        val = lambda a: factorial(a[0])  # noqa: E731
        why = "Start `result = 1`, multiply it by each number from 2 to n in a `for` loop (`range(2, n + 1)`), then `return result`. For 0 and 1 the loop never runs, so the answer stays 1."
    elif which == "sum_to":
        name, params = rng.choice(["sum_to", "add_up_to", "total_to"]), "n"
        body = "total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total"
        ask = "returns the sum of the whole numbers from 1 through n (and `0` when n is 0)"
        args = [(0,), (1,), (4,), (10,), (7,), (20,)]
        val = lambda a: sum(range(1, a[0] + 1))  # noqa: E731
        why = "Start `total = 0` before the loop, add each `i` from `range(1, n + 1)`, and `return total` AFTER the loop (not inside it)."
    elif which == "power":
        name, params = "power", "base, exp"
        body = "result = 1\n    for i in range(exp):\n        result *= base\n    return result"
        ask = "returns base raised to the power exp, using a loop (no `**` and no `pow`)"
        args = [(2, 3), (5, 0), (3, 4), (10, 2), (7, 1), (2, 8)]
        val = lambda a: a[0] ** a[1]  # noqa: E731
        forbids = [(r"\*\*|\bpow\s*\(", "Use a loop instead of ** or pow()")]
        why = "Multiply `result` (starting at 1) by `base`, `exp` times: `for i in range(exp)`. With `exp` 0 the loop never runs and the answer is 1."
    else:
        name, params = "count_evens", "numbers"
        body = "count = 0\n    for number in numbers:\n        if number % 2 == 0:\n            count += 1\n    return count"
        ask = "returns how many even numbers are in the list `numbers`"
        args = [([1, 2, 3, 4],), ([],), ([7, 9, 11],), ([2, 4, 6, 8, 10],), ([0, 5, 10, 15],), ([13, 22, 31, 40, 49],)]
        val = lambda a: sum(1 for x in a[0] if x % 2 == 0)  # noqa: E731
        why = "Start `count = 0`, check `number % 2 == 0` for each item, add 1 when it is true, and `return count` after the loop."
    picks = rng.sample(args, 5)
    cases = [(a, val(a)) for a in picks]
    solution = f"def {name}({params}):\n    {body}"
    task = function_task(name, solution, cases, examples=2, forbids=forbids)
    a0 = picks[0]
    call = f"{name}({', '.join(repr(x) for x in a0)})"
    return _make(
        HARD,
        f"Write a function `{name}({params})` that {ask}. It must `return` the answer. For example `{call}` returns {val(a0)}.",
        task,
        why,
    )


@generator(TOPIC, HARD, qtype="code")
def gen_three_values(rng: random.Random) -> Question:
    """Bingo: max_of_three(a, b, c) without using max() (and its min / middle cousins)."""
    which = rng.choice(["max", "min", "middle"])
    if which == "max":
        name, ask, fn = "max_of_three", "returns the largest of the three numbers", lambda t: sorted(t)[-1]
        solution = "def max_of_three(a, b, c):\n    biggest = a\n    if b > biggest:\n        biggest = b\n    if c > biggest:\n        biggest = c\n    return biggest"
        forbids = [(r"\bmax\s*\(", "Don't use max() - compare with if"), (r"\bsorted\s*\(|\.sort\s*\(", "Don't sort - compare with if")]
        why = "Remember the biggest so far, compare it with each of the others and keep the larger one. Return it at the end."
    elif which == "min":
        name, ask, fn = "min_of_three", "returns the smallest of the three numbers", lambda t: sorted(t)[0]
        solution = "def min_of_three(a, b, c):\n    smallest = a\n    if b < smallest:\n        smallest = b\n    if c < smallest:\n        smallest = c\n    return smallest"
        forbids = [(r"\bmin\s*\(", "Don't use min() - compare with if"), (r"\bsorted\s*\(|\.sort\s*\(", "Don't sort - compare with if")]
        why = "Remember the smallest so far, compare it with each of the others and keep the smaller one. Return it at the end."
    else:
        name, ask, fn = "middle_of_three", "returns the middle value (the one that is neither the largest nor the smallest)", lambda t: sorted(t)[1]
        solution = (
            "def middle_of_three(a, b, c):\n    if (a >= b and a <= c) or (a <= b and a >= c):\n        return a\n    if (b >= a and b <= c) or (b <= a and b >= c):\n        return b\n    return c"
        )
        forbids = [(r"\bmax\s*\(|\bmin\s*\(", "Don't use max() or min()"), (r"\bsorted\s*\(|\.sort\s*\(", "Don't sort - compare with if")]
        why = "A value is in the middle when it is between the other two: `a >= b and a <= c` or `a <= b and a >= c`. Check each of the three."
    args = [(1, 2, 3), (3, 2, 1), (2, 3, 1), (1, 3, 2), (30, 10, 20), (5, 5, 2), (-4, 0, -9), (10, 30, 20), (7, 7, 7), (0, 8, 8), (9, 2, 5), (4, 9, 6)]
    while True:
        picks = rng.sample(args, 5)
        if {t.index(fn(t)) for t in picks} == {0, 1, 2}:  # the answer is a, b and c at least once each
            break
    cases = [(a, fn(a)) for a in picks]
    task = function_task(name, solution, cases, examples=2, forbids=forbids)
    a0 = picks[0]
    return _make(
        HARD,
        f"Write a function `{name}(a, b, c)` that {ask}, WITHOUT using `max()`, `min()` or sorting. For example `{name}({', '.join(map(str, a0))})` returns {fn(a0)}.",
        task,
        why,
    )


@generator(TOPIC, HARD, qtype="code")
def gen_list_function(rng: random.Random) -> Question:
    """Bingo: square_list(lst) - build a new list with a loop (and cousins)."""
    which = rng.choice(["square_list", "double_list", "only_evens", "add_one"])
    pick = {
        "square_list": ("square_list", "squares every number", lambda x: [v * v for v in x], "result.append(number * number)"),
        "double_list": ("double_list", "doubles every number", lambda x: [v * 2 for v in x], "result.append(number * 2)"),
        "only_evens": ("only_evens", "keeps only the even numbers (in their original order)", lambda x: [v for v in x if v % 2 == 0], "if number % 2 == 0:\n            result.append(number)"),
        "add_one": ("add_one", "adds 1 to every number", lambda x: [v + 1 for v in x], "result.append(number + 1)"),
    }[which]
    name, verb, fn, body = pick
    lists = [[1, 2, 3], [4, 5], [], [10], [2, 4, 6, 8], [7, 3, 9, 12], [-3, 0, 5], [6, 1, 8, 3, 5]]
    picks = rng.sample(lists, 5)
    if not any(fn(x) for x in picks):
        picks[0] = [2, 3, 4]
    cases = [((x,), fn(x)) for x in picks]
    solution = f"def {name}(numbers):\n    result = []\n    for number in numbers:\n        {body}\n    return result"
    task = function_task(name, solution, cases, examples=2)
    sample = next(x for x in picks if x)
    return _make(
        HARD,
        f"Write a function `{name}(numbers)` that takes a list of whole numbers and returns a NEW list in which it {verb}. For example `{name}({sample})` returns {fn(sample)}.",
        task,
        "Start with an empty list (`result = []`), loop over `numbers`, `.append()` what belongs in the answer, and `return result` after the loop. The empty list gives back an empty list.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_word_frequency(rng: random.Random) -> Question:
    """Bingo: count word frequencies in a short sentence (a dictionary of counts)."""
    pool = rng.sample(["red", "blue", "green", "gold", "pink", "cyan"], 3)
    shuffled = []
    for _ in range(4):
        words = [rng.choice(pool) for _ in range(rng.randint(4, 7))]
        shuffled.append(" ".join(words))
    sentences = list(dict.fromkeys(shuffled))
    if len(sentences) < 3:
        sentences.append(" ".join([pool[0], pool[1], pool[0]]))

    def lines(sentence: str) -> str:
        counts: dict[str, int] = {}
        for w in sentence.split():
            counts[w] = counts.get(w, 0) + 1
        return "\n".join(f"{w}: {n}" for w, n in counts.items())

    cases = [Case(vars={"sentence": s}, out=lines(s)) for s in sentences]
    solution = 'counts = {}\nfor word in sentence.split():\n    if word in counts:\n        counts[word] += 1\n    else:\n        counts[word] = 1\nfor word in counts:\n    print(f"{word}: {counts[word]}")'
    task = program_task(solution, cases, examples=2)
    s0 = sentences[0]
    return _make(
        HARD,
        f"The variable `sentence` holds some words separated by spaces. Count how many times each word appears and print one line per word, like `{lines(s0).splitlines()[0]}`, in the order the words FIRST appear. "
        f"For \"{s0}\" the lines are: {_example(lines(s0).splitlines())}.",
        task,
        "`sentence.split()` gives a list of words. Use a dictionary of counts: if the word is already a key add 1, otherwise start it at 1. A dictionary remembers the order its keys were added in.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_remove_if_present(rng: random.Random) -> Question:
    """Bingo: remove an item from a list if it is present."""
    pools = [
        ["apple", "banana", "cherry", "mango", "lemon", "grape"],
        ["red", "green", "blue", "pink", "gold", "cyan"],
        ["Ava", "Ben", "Cara", "Dev", "Eli", "Fay"],
    ]
    pool = rng.choice(pools)
    var, target_name = rng.choice([("fruits", "fruit"), ("items", "item"), ("names", "name")])
    cases = []
    for present in (True, False, True, False):
        items = rng.sample(pool, 4)
        item = rng.choice(items) if present else rng.choice([p for p in pool if p not in items])
        result = [x for x in items if x != item] if present else list(items)
        cases.append(Case(vars={var: items, target_name: item}, out=str(result)))
    rng.shuffle(cases)
    solution = f"if {target_name} in {var}:\n    {var}.remove({target_name})\nprint({var})"
    task = program_task(solution, cases, examples=2)
    c0 = cases[0]
    return _make(
        HARD,
        f"The list `{var}` and the variable `{target_name}` already exist. If `{target_name}` is in the list, remove it; if it isn't there, do nothing (no error). Then print the list. "
        f"With `{var} = {c0.vars[var]}` and `{target_name} = {c0.vars[target_name]!r}` it prints `{c0.out}`.",
        task,
        f"Check first with `if {target_name} in {var}:`, then call `{var}.remove({target_name})` (calling `.remove()` on a missing item would raise an error). Printing a list shows brackets and quotes.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_class_challenge(rng: random.Random) -> Question:
    """Classes lesson mini-challenge: Triangle (plus a Rectangle and a Player look-alike)."""
    which = rng.choice(["Triangle", "Rectangle", "Player"])
    if which == "Triangle":
        pairs = rng.sample([(b, h) for b in range(3, 14) for h in range(2, 10)], 3)
        solution = "class Triangle:\n    def __init__(self, base, height):\n        self.base = base\n        self.height = height\n\n    def area(self):\n        return self.base * self.height / 2"
        cases = [Case(label=f"Triangle({b}, {h})", after=f"t = Triangle({b}, {h})\narea = t.area()", expect_vars={"area": b * h / 2}) for b, h in pairs]
        starter = "class Triangle:\n    "
        b0, h0 = pairs[0]
        prompt = f"Write a class `Triangle` whose `__init__(self, base, height)` stores both numbers, plus an `area()` method that returns base times height divided by 2. `Triangle({b0}, {h0}).area()` is `{b0 * h0 / 2}`."
        why = "Store the values on the object (`self.base = base`), then `area()` returns `self.base * self.height / 2`. Use `return`, not `print`."
    elif which == "Rectangle":
        pairs = rng.sample([(w, h) for w in range(2, 12) for h in range(2, 9) if w != h], 3)
        solution = (
            "class Rectangle:\n    def __init__(self, width, height):\n        self.width = width\n        self.height = height\n\n    def area(self):\n        return self.width * self.height\n\n"
            "    def perimeter(self):\n        return 2 * (self.width + self.height)"
        )
        cases = [
            Case(label=f"Rectangle({w}, {h})", after=f"r = Rectangle({w}, {h})\narea = r.area()\nperimeter = r.perimeter()", expect_vars={"area": w * h, "perimeter": 2 * (w + h)})
            for w, h in pairs
        ]
        starter = "class Rectangle:\n    "
        w0, h0 = pairs[0]
        prompt = f"Write a class `Rectangle` with `__init__(self, width, height)`, an `area()` method (width times height) and a `perimeter()` method (2 times width plus height). `Rectangle({w0}, {h0}).area()` is `{w0 * h0}`."
        why = "`__init__` saves `width` and `height` on `self`; both methods `return` a result built from `self.width` and `self.height`."
    else:
        starts = [(rng.choice(NAMES), rng.randint(0, 50)) for _ in range(3)]
        steps = [(rng.randint(5, 30), rng.randint(5, 30)) for _ in range(3)]
        solution = "class Player:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n\n    def add_points(self, points):\n        self.score = self.score + points"
        cases = [
            Case(
                label=f"Player({n!r}, {s}) then add_points({p}) and add_points({q})",
                after=f"p = Player({n!r}, {s})\np.add_points({p})\np.add_points({q})\nscore = p.score\nname = p.name",
                expect_vars={"score": s + p + q, "name": n},
            )
            for (n, s), (p, q) in zip(starts, steps)
        ]
        starter = "class Player:\n    "
        n0, s0 = starts[0]
        p0, q0 = steps[0]
        prompt = (
            f"Write a class `Player` whose `__init__(self, name, score)` stores both values, plus an `add_points(self, points)` method that ADDS `points` to the player's score (it changes the object; it returns nothing). "
            f"After `p = Player({n0!r}, {s0})`, `p.add_points({p0})` and `p.add_points({q0})`, `p.score` is {s0 + p0 + q0}."
        )
        why = "A method can change the object: `self.score = self.score + points`. Each call builds on the score the earlier calls left behind."
    task = program_task(solution, cases, starter=starter, examples=2)
    return _make(HARD, prompt + " Write only the class.", task, why)
