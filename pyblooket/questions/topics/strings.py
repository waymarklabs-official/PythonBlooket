"""Question generators for the "strings" topic (CSF.2.D: Python Strings).

Everything here follows the lesson and its Canvas quiz items: indexing ``[0]`` / ``[-1]``,
slicing ``[0:4]`` and ``[::-1]``, ``upper`` / ``lower`` / ``strip`` / ``replace`` / ``count``,
``split`` / ``join``, f-strings with expressions, immutability (methods return NEW strings),
``len()``, the ``"\\n"`` escape and off-by-one slicing.  The Mini-Challenge "First Name Slice"
(``Reid C.``) and the Bingo string tasks (strip, replace, count, split + dashes, reverse)
appear as code questions.
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
    display_output,
    error_choice,
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

TOPIC = "strings"
PRINT_OR_ERROR = "What is printed, or which error is raised?"

# Words whose letters are all different, so "which letter?" questions have one answer.
WORDS6 = ["Python", "planet", "rocket", "castle", "jungle", "guitar", "pencil", "monkey"]
# Any ordinary lesson-flavoured words (repeated letters allowed).
WORDS_ANY = ["Python", "coding", "banana", "cherry", "school", "laptop", "program", "puzzle", "garden", "teacher"]
PHRASES = [
    "I love Python programming!",
    "Python makes coding fun",
    "I like Python a lot",
    "We code in Python",
    "Coding is my favorite class",
    "I code after school",
    "Python is fun to learn",
]
# (phrase, old word, new word) for replace(); old and new have different lengths.
REPLACE_TRIPLES = [
    ("I love Python programming!", "Python", "coding"),
    ("Python is fun to learn", "fun", "easy"),
    ("We code in Python", "Python", "class"),
    ("Coding is my favorite class", "favorite", "best"),
    ("I like pizza a lot", "pizza", "tacos"),
]
FULL_NAMES = [
    ("Reid", "Carter"),
    ("Ada", "Lovelace"),
    ("Grace", "Hopper"),
    ("Alan", "Turing"),
    ("Mia", "Lopez"),
    ("Noah", "Brooks"),
    ("Zoe", "Parker"),
    ("Sam", "Rivera"),
    ("Eli", "Nguyen"),
    ("Hana", "Kim"),
]
FIRST_NAMES = ["Ada", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivy", "Jon", "Sam", "Mia"]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _q(text: str) -> str:
    """Display a string value the way the quiz does: in double quotes."""
    return '"' + text + '"'


def _show(value) -> str:
    if isinstance(value, str):
        return _q(value)
    if isinstance(value, list):
        return "[" + ", ".join(_show(v) for v in value) + "]"
    return str(value)


def _pad(rng: random.Random, text: str) -> str:
    """The lesson's ``"   I love Python programming!   "`` -- spaces around the text."""
    left = rng.choice([2, 3, 3, 4])
    right = rng.choice([2, 3, 3, 4])
    return " " * left + text + " " * right


def _run(code: str) -> str:
    """The choice text for what ``code`` prints (or the error it raises)."""
    res = run_code(code)
    if res.error:
        return error_choice(res.error)
    return display_output(res.output)


def _value_of(expr: str, setup: str) -> str:
    try:
        return _show(eval_expr(expr, setup))
    except GenerationError:
        raise
    except Exception as exc:  # noqa: BLE001 - an erroring distractor is fine
        return error_choice(type(exc).__name__)


def _value_question(
    *,
    difficulty: int,
    setup: str,
    expr: str,
    wrong,
    explanation: str,
    rng: random.Random,
    prompt: str | None = None,
    extra=(),
) -> Question:
    """'What does <expr> return?' -- the answer is computed; ``wrong`` are expressions to evaluate."""
    correct = _show(eval_expr(expr, setup))
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt or f"What does `{expr}` return?",
        correct=correct,
        distractors=[*[_value_of(w, setup) for w in wrong], *extra],
        explanation=explanation,
        rng=rng,
        code=setup,
    )


def _print_question(
    *,
    difficulty: int,
    code: str,
    wrong_codes,
    explanation: str,
    rng: random.Random,
    prompt: str = "What does this code print?",
    allow_error: bool = False,
    extra=(),
) -> Question:
    """'What does this print?' -- ``wrong_codes`` are alternative snippets whose output is used as distractors."""
    return output_question(
        topic=TOPIC,
        difficulty=difficulty,
        code=code,
        distractors=[*[_run(w) for w in wrong_codes], *extra],
        explanation=explanation,
        rng=rng,
        prompt=prompt,
        allow_error=allow_error,
    )


def _which_code(
    *,
    difficulty: int,
    prompt: str,
    setup: str,
    target: str,
    correct: str,
    wrong,
    explanation: str,
    rng: random.Random,
) -> Question:
    """'Which code does X?' -- every choice is run; exactly the correct one prints ``target``."""
    if _run(setup + "\n" + correct) != target:
        raise GenerationError(f"{correct!r} does not print {target!r}")
    bad = [w for w in wrong if _run(setup + "\n" + w) != target]
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=bad,
        explanation=explanation,
        rng=rng,
        code=setup,
    )


def _letters_except(word: str, banned: str, rng: random.Random) -> list[str]:
    pool = [c for c in dict.fromkeys(word) if c != banned]
    rng.shuffle(pool)
    return pool


# ==========================================================================
# EASY -- choice
# ==========================================================================


@generator(TOPIC, EASY)
def gen_first_last_char(rng: random.Random) -> Question:
    """Quiz item: 'What is the first character of word = "Python" using indexing?'"""
    word = rng.choice(WORDS6)
    kind = rng.choice(["first", "last", "second"])
    idx = {"first": 0, "last": -1, "second": 1}[kind]
    ch = word[idx]
    others = [j for j in (0, 1, 2, -1, -2) if j != idx]
    rng.shuffle(others)
    other_letter = rng.choice(_letters_except(word, ch, rng))
    wrong = [f'word[{others[0]}] is "{ch}"', f'word[{idx}] is "{other_letter}"', f'word[{others[1]}] is "{ch}"', f'word[{others[2]}] is "{ch}"']
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f'What is the {kind} character of `word = "{word}"` using indexing?',
        correct=f'word[{idx}] is "{ch}"',
        distractors=wrong,
        explanation="Indexing starts at 0, so `word[0]` is the first character, and `word[-1]` counts from the end to give the last one.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_index_value(rng: random.Random) -> Question:
    """'What does word[-1] return?'"""
    word = rng.choice(WORDS6)
    idx = rng.choice([0, 1, 2, 3, -1, -1])
    n = len(word)
    wrong = [f"word[{j}]" for j in (idx + 1, idx - 1, 0, -1, 1, 2) if j != idx and -n <= j < n]
    return _value_question(
        difficulty=EASY,
        setup=f'word = "{word}"',
        expr=f"word[{idx}]",
        wrong=wrong,
        explanation=f"`word[{idx}]` is the character at index {idx}. Index 0 is the first character and -1 is the last one.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_slice_value(rng: random.Random) -> Question:
    """'What does word[0:4] return?' -- the end index is NOT included."""
    if rng.random() < 0.25:  # the data-types lesson's title = "Intro to Python"
        var, word = "title", "Intro to Python"
        a, b = rng.choice([(0, 5), (0, 2), (6, 8)])
    else:
        var, word = "word", rng.choice(["Python", "Python"] + WORDS6)
        a, b = rng.choice([(0, 4), (0, 3), (0, 2), (1, 4), (2, 5), (0, 5), (1, 3)])
    wrong = [f"{var}[{a}:{b + 1}]", f"{var}[{a}:{b - 1}]", f"{var}[{a + 1}:{b + 1}]", f"{var}[{b}]", f"{var}[{a - 1}:{b}]" if a else f"{var}[{a + 1}:{b}]"]
    return _value_question(
        difficulty=EASY,
        setup=f'{var} = "{word}"',
        expr=f"{var}[{a}:{b}]",
        wrong=wrong,
        explanation=f"A slice `[start:end]` stops BEFORE the end index, so `{var}[{a}:{b}]` takes indexes {a} to {b - 1}.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_len_value(rng: random.Random) -> Question:
    """'What does len(...) return?' -- spaces and punctuation count."""
    kind = rng.choice(["word", "phrase", "padded", "padded_strip", "title"])
    if kind == "title":  # the data-types lesson: title = "Intro to Python"
        text = "Intro to Python"
        setup, expr = f'title = "{text}"', "len(title)"
        note = "`len()` counts every character, including the spaces."
    elif kind == "word":
        w = rng.choice(WORDS_ANY)
        setup, expr, text = f'word = "{w}"', "len(word)", w
        note = "`len()` counts every character in the string."
    elif kind == "phrase":
        text = rng.choice(PHRASES)
        setup, expr = f'phrase = "{text}"', "len(phrase)"
        note = "`len()` counts every character, including spaces and punctuation."
    else:
        text = _pad(rng, rng.choice(PHRASES))
        setup = f'text = "{text}"'
        expr = "len(text)" if kind == "padded" else "len(text.strip())"
        note = (
            "`len()` counts the spaces at the ends too." if kind == "padded" else "`strip()` first removes the spaces at both ends, then `len()` counts what is left."
        )
    correct = len(text) if kind != "padded_strip" else len(text.strip())
    near = [correct + 1, correct - 1, len(text.replace(" ", "")), len(text.strip()), len(text), correct + 2]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"What does `{expr}` return?",
        correct=str(correct),
        distractors=[str(x) for x in near if x != correct],
        explanation=note,
        rng=rng,
        code=setup,
    )


@generator(TOPIC, EASY)
def gen_newline(rng: random.Random) -> Question:
    """Quiz item: 'What does "\\n" represent in a string?' plus print variants."""
    variant = rng.choice(["meaning", "which", "print", "print", "count"])
    note = 'The escape sequence `"\\n"` is a new line: whatever comes after it starts on the next line.'
    if variant == "meaning":
        wrong = rng.sample(["A tab", "A quote", "A space", "A backslash", "The letter n"], 3)
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt='What does `"\\n"` represent in a string?',
            correct="A new line",
            distractors=wrong,
            explanation=note,
            rng=rng,
        )
    if variant == "which":
        wrong = rng.sample(["/n", "\\t", "n\\", "<br>", "\\\\n"], 3)
        return build_question(
            topic=TOPIC,
            difficulty=EASY,
            prompt="Which escape sequence starts a new line inside a string?",
            correct="\\n",
            distractors=wrong,
            explanation=note,
            rng=rng,
        )
    a, b = rng.choice([("Line1", "Line2"), ("Hello", "World"), ("Python", "Strings"), ("Roses", "Violets"), ("Top", "Bottom")])
    if variant == "print":
        code = f'print("{a}\\n{b}")'
        return output_question(
            topic=TOPIC,
            difficulty=EASY,
            code=code,
            distractors=[f"{a}\\n{b}", f"{a} {b}", f"{a}{b}", f"{a}\n\n{b}"],
            explanation=note,
            rng=rng,
        )
    c = rng.choice(["Last", "Done", "End"])
    code = f'print("{a}\\n{b}\\n{c}")'
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="How many lines of output does this print?",
        correct="3",
        distractors=["1", "2", "4"],
        explanation="Each `\"\\n\"` starts a new line, so two of them split the text into 3 lines.",
        rng=rng,
        code=code,
    )


IMMUTABLE_CONCEPTS = [
    (
        "What does it mean that strings are unchangeable (immutable) in Python?",
        "Methods return new strings; the original isn't changed.",
        [
            "String methods permanently change the original string.",
            "Strings can't be printed.",
            "Strings can only contain letters.",
            "Strings can only be used once.",
        ],
    ),
    (
        'If `word = "Python"`, what does `word.upper()` do to `word`?',
        "Nothing: it returns a new string, `word` is unchanged.",
        ['It changes `word` to "PYTHON".', "It deletes `word`.", "It raises an error.", 'It changes `word` to "python".'],
    ),
    (
        "Why do we write `text = text.strip()` instead of just `text.strip()`?",
        "`strip()` returns a new string, so we store the result.",
        [
            "`strip()` changes `text` anyway, so `text =` is optional.",
            "Python needs `text =` to understand the method.",
            "Without it, `text` becomes empty.",
            "The assignment makes `strip()` run faster.",
        ],
    ),
    (
        "Which statement about `upper()`, `lower()` and `replace()` is true?",
        "They return a new string and leave the original alone.",
        [
            "They change the original string in place.",
            "They only work on numbers.",
            "They return a list of characters.",
            "They return the length of the string.",
        ],
    ),
]


@generator(TOPIC, EASY)
def gen_immutable_concept(rng: random.Random) -> Question:
    """Quiz item: 'What does it mean that strings are unchangeable (immutable)?'"""
    prompt, correct, wrong = rng.choice(IMMUTABLE_CONCEPTS)
    wrong = rng.sample(wrong, 3)
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation="Strings are immutable: methods return a new string, and the original stays the same unless you assign the result back.",
        rng=rng,
    )


METHOD_PURPOSES = [
    ("returns the text in all capital letters", "upper", "capital"),
    ("returns the text in all lowercase letters", "lower", "small"),
    ("removes extra spaces from both ends of the text", "strip", "trim"),
    ("swaps one piece of text for another", "replace", "swap"),
    ("counts how many times a piece of text appears", "count", "total"),
    ("turns a string into a list of words", "split", "slice"),
    ("stitches a list of words into one string", "join", "glue"),
]
LESSON_METHODS = ["upper", "lower", "strip", "replace", "count", "split", "join"]


@generator(TOPIC, EASY)
def gen_method_purpose(rng: random.Random) -> Question:
    """'Which method removes extra spaces from both ends of text?'"""
    desc, method, invented = rng.choice(METHOD_PURPOSES)
    others = [m for m in LESSON_METHODS if m != method and not (method == "strip" and m == "replace")]
    wrong = [invented, *rng.sample(others, 2)]
    return build_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Which string method {desc}?",
        correct=f"{method}()",
        distractors=[f"{w}()" for w in wrong],
        explanation=f"`{method}()` is the method that {desc}. It returns a new value and leaves the original string alone.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_fstring_print(rng: random.Random) -> Question:
    """Lesson line: print(f"My name is {name}, and I am {age} years old.")"""
    name = rng.choice(FIRST_NAMES)
    age = rng.randint(12, 18)
    if rng.random() < 0.7:
        template = rng.choice(["My name is {name}, and I am {age} years old.", "{name} is {age} years old.", "Hi, I'm {name} and I'm {age}!"])
        head = f'name, age = "{name}", {age}\n'
        code = head + f'print(f"{template}")'
        bare = template.replace("{name}", "name").replace("{age}", "age")
        wrong = [
            head + f'print("{template}")',
            head + f'print(f"{bare}")',
            head + f'print(f"{template.replace("{age}", "{age + 1}")}")',
            head + f'print(f"{template.replace("{name}", "{name.upper()}")}")',
        ]
        expl = "The `f` in front of the string lets Python put the values of `name` and `age` where the `{}` are."
    else:
        head = f'name = "{name}"\n'
        code = head + 'print("Hello, {name}!")'
        wrong = [
            head + 'print(f"Hello, {name}!")',
            head + 'print(f"Hello, name!")',
            head + 'print("Hello, " + name.upper() + "!")',
            head + 'print("Hello, name!")',
        ]
        expl = "Without the `f` in front of the quotes, Python does not fill in `{name}`: it prints the braces exactly as written."
    return _print_question(difficulty=EASY, code=code, wrong_codes=wrong, explanation=expl, rng=rng)


@generator(TOPIC, EASY)
def gen_reverse_expr(rng: random.Random) -> Question:
    """'Which expression reverses word?' -- word[::-1]."""
    word = rng.choice(WORDS6)
    return which_expression_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f'Which expression gives `"{word[::-1]}"` (the word backwards)?',
        setup=f'word = "{word}"',
        target=word[::-1],
        correct_expr="word[::-1]",
        wrong_exprs=["word[-1]", "word[0:-1]", "word.reverse()", "word[-1:0]", "word[1:]"],
        explanation='`word[::-1]` reverses a string. `word[-1]` is only the last character.',
        rng=rng,
    )


# ==========================================================================
# MEDIUM -- choice
# ==========================================================================


@generator(TOPIC, MEDIUM)
def gen_method_result(rng: random.Random) -> Question:
    """'What does text.strip() return?' on the lesson's padded sentence."""
    phrase, old, new = rng.choice(REPLACE_TRIPLES)
    text = _pad(rng, phrase)
    setup = f'text = "{text}"'
    op = rng.choice(["strip", "upper", "lower", "replace", "count", "len_strip"])
    if op == "strip":
        expr = "text.strip()"
        wrong = ["text", "text.lstrip()", "text.rstrip()", "text.replace(' ', '')"]
        note = "`strip()` removes the spaces at the beginning and end only; the spaces between words stay. It returns a new string."
    elif op == "upper":
        expr = "text.upper()"
        wrong = ["text", "text.lower()", "text.strip().upper()", "text.strip()"]
        note = "`upper()` makes every letter a capital. The spaces around the text are still there because `strip()` was not used."
    elif op == "lower":
        expr = "text.lower()"
        wrong = ["text", "text.upper()", "text.strip().lower()", "text.strip()"]
        note = "`lower()` makes every letter lowercase. The spaces around the text are still there because `strip()` was not used."
    elif op == "replace":
        expr = f'text.replace("{old}", "{new}")'
        wrong = ["text", f'text.strip().replace("{old}", "{new}")', f'text.replace("{old}", "")', f'text.replace("{old}", "{new}").strip()']
        note = f"`replace()` swaps every `{old}` for `{new}` (it is case-sensitive) and keeps the other characters, spaces included."
    elif op == "count":
        letter = rng.choice([c for c in "oaeit" if c in phrase.lower()])
        expr = f'text.count("{letter}")'
        n = text.count(letter)
        wrong = [str(n + 1), str(n - 1), f'text.count("{letter.upper()}")', str(n + 2), "len(text)"]
        note = f'`count("{letter}")` counts how many times `{letter}` appears. It is case-sensitive: `{letter.upper()}` is a different character.'
    else:
        expr = "len(text.strip())"
        wrong = ["len(text)", "len(text) - 1", "len(text.strip()) + 1", "len(text.replace(' ', ''))"]
        note = "`strip()` removes the end spaces first, then `len()` counts the characters that are left (the spaces between words still count)."
    return _value_question(difficulty=MEDIUM, setup=setup, expr=expr, wrong=wrong, explanation=note, rng=rng)


@generator(TOPIC, MEDIUM)
def gen_immutability_trace(rng: random.Random) -> Question:
    """word.upper() on its own line does NOT change word."""
    word = rng.choice(["Python", "Coding", "Banana", "Planet", "Rocket"])
    new = word.upper()
    v = rng.choice(["ignored", "kept", "reassigned", "replace", "strip_len"])
    extra = []
    if v == "ignored":
        code = f'word = "{word}"\nword.upper()\nprint(word)'
        wrong = [f'word = "{word}"\nprint(word.upper())', f'word = "{word}"\nprint(word.lower())']
        extra = [error_choice("TypeError")]
        expl = "`word.upper()` creates a new string, but it is never stored, so `word` is unchanged."
    elif v == "kept":
        code = f'word = "{word}"\nloud = word.upper()\nprint(word, loud)'
        wrong = [f'print("{new} {new}")', f'print("{word} {word}")', f'print("{new} {word}")', f'print("{word.lower()} {new}")']
        expl = "`upper()` returns a new string that is stored in `loud`. The original `word` stays the same."
    elif v == "reassigned":
        code = f'word = "{word}"\nword = word.upper()\nprint(word)'
        wrong = [f'print("{word}")', f'print("{word.lower()}")', f'print("{word.swapcase()}")', 'print("word")']
        expl = "Assigning the result back (`word = word.upper()`) is how you keep the new string."
    elif v == "replace":
        a = rng.choice([c for c in word if c.isalpha()])
        code = f'word = "{word}"\nword.replace("{a}", "X")\nprint(word)'
        wrong = [f'print("{word.replace(a, "X")}")', f'print("{word.upper()}")', f'print("{word.lower()}")', 'print("X")']
        expl = "`replace()` returns a new string. Since nothing stores it, `word` is unchanged."
    else:
        text = _pad(rng, rng.choice(["hi there", "ready go", "hello"]))
        code = f'text = "{text}"\ntext.strip()\nprint(len(text))'
        wrong = [f'print({len(text.strip())})', f'print({len(text) + 1})', f'print({len(text) - 1})', f'print({len(text.replace(" ", ""))})']
        expl = "`text.strip()` returns a trimmed copy but is never stored, so `text` keeps its spaces and `len(text)` is unchanged."
    return _print_question(difficulty=MEDIUM, code=code, wrong_codes=wrong, extra=extra, explanation=expl, rng=rng)


@generator(TOPIC, MEDIUM)
def gen_slice_which(rng: random.Random) -> Question:
    """'Which slice gets the first 4 letters?' -- the end index is exclusive."""
    word = rng.choice(["Python", "Python"] + WORDS6)
    setup = f'word = "{word}"'
    if rng.random() < 0.5:
        n = rng.choice([3, 4, 5])
        correct, target = f"word[0:{n}]", word[0:n]
        prompt = f"Which slice gets the first {n} characters of `word`?"
        wrong = [f"word[0:{n - 1}]", f"word[0:{n + 1}]", f"word[1:{n}]", f"word[{n}]", f"word[1:{n + 1}]"]
        expl = f"The end index is not included, so `word[0:{n}]` takes indexes 0 to {n - 1}: {n} characters."
    else:
        a, b = rng.choice([(1, 4), (2, 5), (1, 3), (2, 4), (3, 6)])
        correct, target = f"word[{a}:{b}]", word[a:b]
        prompt = f'Which slice of `word` gives `"{target}"`?'
        wrong = [f"word[{a}:{b + 1}]", f"word[{a - 1}:{b}]", f"word[{a + 1}:{b}]", f"word[{a}:{b - 1}]", f"word[{a}:{b + 2}]"]
        expl = f"Start at index {a} and stop BEFORE index {b}: `word[{a}:{b}]`. Count the indexes: {', '.join(str(i) for i in range(a, b))}."
    return which_expression_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        setup=setup,
        target=target,
        correct_expr=correct,
        wrong_exprs=wrong,
        explanation=expl,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_concat_fix(rng: random.Random) -> Question:
    """'Using + with numbers and strings -- prefer str() or f-strings.'"""
    label = rng.choice(["Age", "Score", "Level", "Coins", "Grade"])
    var = label.lower()
    value = rng.randint(3, 99)
    setup = f"{var} = {value}"
    target = f"{label}: {value}"
    if rng.random() < 0.5:
        correct = f'print("{label}: " + str({var}))'
        why = f"`str({var})` turns the number into text, so `+` can join the two strings."
    else:
        correct = f'print(f"{label}: {{{var}}}")'
        why = f"An f-string puts the value of `{var}` into the text, no `str()` needed."
    wrong = [
        f'print("{label}: " + {var})',
        f'print("{label}: {{{var}}}")',
        f'print("{label}:" + str({var}))',
        f'print(f"{label}: {var}")',
        f'print(f"{label}: {{str}}")' if False else f'print("{label}: " + "{var}")',
    ]
    return _which_code(
        difficulty=MEDIUM,
        prompt=f"Which line prints `{target}` without an error?",
        setup=setup,
        target=target,
        correct=correct,
        wrong=wrong,
        explanation=why + " Joining a string and a number with `+` is a TypeError.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_split_join_trace(rng: random.Random) -> Question:
    """Lesson code: words = text.strip().split(" ") ... "-".join(words)"""
    phrase = rng.choice(PHRASES)
    text = _pad(rng, phrase)
    words = phrase.split(" ")
    sep = rng.choice(["-", "-", "_", "*"])
    final = rng.choice(["list", "joined", "count", "word"])
    head = f'text = "{text}"\nwords = text.strip().split(" ")\n'
    if final == "list":
        code = head + "print(words)"
        extra = [phrase, str([phrase]), sep.join(words), str(words[1:])]
        expl = "`split(\" \")` cuts the stripped text at every space and returns a LIST of words (printed with square brackets and quotes)."
    elif final == "joined":
        code = head + f'joined = "{sep}".join(words)\nprint(joined)'
        extra = [phrase, "".join(words), (sep + " ").join(words), sep + sep.join(words)]
        expl = f'`"{sep}".join(words)` stitches the list back into ONE string with `{sep}` between the words.'
    elif final == "count":
        code = head + "print(len(words))"
        extra = [str(len(words) + 1), str(len(words) - 1), str(len(phrase)), str(len(text))]
        expl = "`words` is a list with one item per word, so `len(words)` counts words, not characters."
    else:
        i = rng.choice([1, 2, -1])
        code = head + f"print(words[{i}])"
        extra = [words[k] for k in (0, 1, 2, -1, -2) if words[k] != words[i]]
        expl = f"After `split(\" \")`, `words` is a list, so `words[{i}]` is one whole word (index 0 is the first word)."
    return _print_question(difficulty=MEDIUM, code=code, wrong_codes=[], extra=extra, explanation=expl, rng=rng)


@generator(TOPIC, MEDIUM)
def gen_fstring_expression(rng: random.Random) -> Question:
    """Pro Tip from the lesson: f"{name.upper()} is {age + 1} next year"."""
    name = rng.choice(FIRST_NAMES)
    age = rng.randint(12, 17)
    setup = f'name = "{name}"\nage = {age}\n'
    v = rng.choice(["next_year", "len", "initial", "double"])
    if v == "next_year":
        code = setup + 'print(f"{name.upper()} is {age + 1} next year")'
        wrong = [
            setup + 'print(f"{name} is {age + 1} next year")',
            setup + 'print(f"{name.upper()} is {age} next year")',
            setup + 'print(f"{name.upper()} is {age} + 1 next year")',
            setup + 'print(f"{name.upper()} is {str(age) + str(1)} next year")',
        ]
        expl = "Anything inside `{}` in an f-string is evaluated: `name.upper()` gives the capitals and `age + 1` does real math."
    elif v == "len":
        code = setup + 'print(f"{name} has {len(name)} letters")'
        wrong = [
            setup + 'print(f"{name} has {len(name) + 1} letters")',
            setup + 'print(f"{name} has {age} letters")',
            setup + 'print(f"{name} has len(name) letters")',
            setup + 'print(f"{name} has {len(name) - 1} letters")',
        ]
        expl = "`{len(name)}` is replaced by the number of characters in `name`."
    elif v == "initial":
        code = setup + 'print(f"{name[0]}. is {age} years old")'
        wrong = [
            setup + 'print(f"{name[1]}. is {age} years old")',
            setup + 'print(f"{name}. is {age} years old")',
            setup + 'print(f"{name[-1]}. is {age} years old")',
            setup + 'print(f"{name[0:2]}. is {age} years old")',
        ]
        expl = "`{name[0]}` puts only the first character of `name` into the text."
    else:
        code = setup + 'print(f"{age} doubled is {age * 2}")'
        wrong = [
            setup + 'print(f"{age} doubled is {age * 3}")',
            setup + 'print(f"{age} doubled is {age} * 2")',
            setup + 'print(f"{age} doubled is {age + 2}")',
            setup + 'print(f"{age * 2} doubled is {age}")',
        ]
        expl = "Expressions like `{age * 2}` are calculated before they are put into the text."
    return _print_question(difficulty=MEDIUM, code=code, wrong_codes=wrong, explanation=expl, rng=rng)


@generator(TOPIC, MEDIUM)
def gen_mistake_spotting(rng: random.Random) -> Question:
    """The lesson's 'Common Mistakes' list as 'what is wrong here?' questions."""
    name = rng.choice(FIRST_NAMES)
    word = rng.choice(["Python", "coding", "planet", "rocket"])
    var = rng.choice(["name", "student", "player"])
    label = rng.choice(["Age", "Score", "Level"])
    lv = label.lower()
    num = rng.randint(5, 30)
    variants = [
        dict(
            code=f"{var} = {name}\nprint({var})",
            prompt="What is wrong with this code?",
            correct=f"`{name}` needs quotes; it is text, not a variable.",
            wrong=[
                "`print` can't show a variable.",
                f"`{var}` isn't a legal variable name.",
                "Text must always use single quotes.",
                "A variable can't hold text.",
            ],
            expl=f'Text must be inside quotes: `{var} = "{name}"`. Forgetting the quotes is a classic mistake.',
        ),
        dict(
            code=f'{lv} = {num}\nprint("{label}: " + {lv})',
            prompt="What is wrong with this code?",
            correct=f"You can't add a number to a string; use `str({lv})`.",
            wrong=[
                "`print` only accepts one value.",
                f"`{lv}` must be a float to be printed.",
                "There must be no space after the colon.",
                "The plus sign only works with numbers.",
            ],
            expl=f'Joining text and a number with `+` is a TypeError. Use `str({lv})` or an f-string such as `f"{label}: {{{lv}}}"`.',
        ),
        dict(
            code=f'word = "{word}"\nword.upper()\nprint(word)',
            prompt=f"This code should print `{word.upper()}`, but it prints `{word}`. Why?",
            correct="`upper()` returns a new string that was never stored.",
            wrong=[
                "`upper()` only works on numbers.",
                "Strings can't be made uppercase.",
                "`print` always shows the first value assigned.",
                "`upper()` must be called after `print`.",
            ],
            expl="Strings are immutable. Fix it with `word = word.upper()` or `print(word.upper())`.",
        ),
        dict(
            code=f'word = "{word}"\nprint(word[0:3])',
            prompt=f"This code should print `{word[0:4]}`, but it prints `{word[0:3]}`. What is wrong?",
            correct="The end index is not included; use `word[0:4]`.",
            wrong=[
                "Slices must start at 1, so use `word[1:4]`.",
                "The slice needs a negative end index.",
                "`word[0:3]` is only allowed in a loop.",
                "The slice must use a comma: `word[0, 4]`.",
            ],
            expl="Off-by-one slicing is a common mistake: `word[0:4]` stops before index 4, so it gives 4 characters.",
        ),
        dict(
            code=f'word = "{word}"\nword[0] = "J"',
            prompt="What happens when this code runs?",
            correct="Error: a string can't be changed by index (immutable).",
            wrong=[
                f'`word` becomes "J{word[1:]}".',
                '`word` becomes "J".',
                "Nothing happens; the line is ignored.",
                "The first and last characters swap places.",
            ],
            expl=f'A string cannot be changed in place (TypeError). Build a new string instead, for example with `word.replace("{word[0]}", "J")`.',
        ),
        dict(
            code=f'{var} = "{name}"\nprint("Hello, {{{var}}}!")',
            prompt=f"This prints `Hello, {{{var}}}!` instead of `Hello, {name}!`. What is missing?",
            correct=f'The `f` before the quote: `f"Hello, {{{var}}}!"`.',
            wrong=[
                f"Single quotes around `{var}`.",
                f"Parentheses instead of braces: `({var})`.",
                "A comma after the string.",
                f"`{var}` must be written in capitals.",
            ],
            expl="Only an f-string fills in the `{}` placeholders. A normal string prints them as written.",
        ),
    ]
    v = rng.choice(variants)
    return build_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=v["prompt"],
        correct=v["correct"],
        distractors=rng.sample(v["wrong"], 3),
        explanation=v["expl"],
        rng=rng,
        code=v["code"],
    )


@generator(TOPIC, MEDIUM)
def gen_first_name_which(rng: random.Random) -> Question:
    """Mini-Challenge 'First Name Slice': which code prints Reid C. ?"""
    first, last = rng.choice(FULL_NAMES)
    target = f"{first} {last[0]}."
    setup = f'full_name = "{first} {last}"\nparts = full_name.split()'
    if rng.random() < 0.5:
        correct = 'print(parts[0], parts[1][0] + ".")'
    else:
        correct = 'print(parts[0] + " " + parts[1][0] + ".")'
    wrong = [
        "print(parts[0], parts[1][0])",
        'print(parts[0], parts[1] + ".")',
        'print(parts[1][0], parts[0] + ".")',
        'print(parts[0], parts[1][1] + ".")',
        'print(parts[1], parts[0][0] + ".")',
    ]
    return _which_code(
        difficulty=MEDIUM,
        prompt=f"Which code prints the first name and last initial, like `{target}`?",
        setup=setup,
        target=target,
        correct=correct,
        wrong=rng.sample(wrong, 4),
        explanation="`split()` gives a list of two words. `parts[0]` is the first name, `parts[1][0]` is the first letter of the last name, and `+ \".\"` adds the period.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_slice_combo_trace(rng: random.Random) -> Question:
    """Indexing + slicing + a method in one print()."""
    word = rng.choice(WORDS6)
    setup = f'word = "{word}"\n'
    v = rng.choice(["ends", "ends", "cut_last", "mid_upper", "mid_len"])
    if v == "ends":
        expr, wrong_e = "word[0] + word[-1]", ["word[-1] + word[0]", "word[0] + word[-2]", "word[0] + word[1]", "word[1] + word[-1]"]
        expl = "`word[0]` is the first character and `word[-1]` the last one. `+` joins the two characters."
    elif v == "cut_last":
        k = rng.choice([2, 3])
        expr = f"word[0:{k}] + word[-1]"
        wrong_e = [f"word[0:{k + 1}] + word[-1]", f"word[0:{k - 1}] + word[-1]", f"word[0:{k}] + word[-2]", f"word[-1] + word[0:{k}]"]
        expl = f"`word[0:{k}]` takes the first {k} characters (the end index is not included) and `word[-1]` adds the last one."
    elif v == "mid_upper":
        a, b = rng.choice([(1, 4), (1, 3), (2, 5)])
        expr = f"word[{a}:{b}].upper()"
        wrong_e = [f"word[{a}:{b + 1}].upper()", f"word[{a - 1}:{b}].upper()", f"word[{a}:{b}].lower()", f"word[{a}:{b}]"]
        expl = f"First `word[{a}:{b}]` takes indexes {a} to {b - 1}, then `.upper()` makes that piece capitals."
    else:
        a, b = rng.choice([(1, 4), (0, 3), (2, 5), (1, 5)])
        expr = f"len(word[{a}:{b}])"
        wrong_e = [str(x) for x in (b - a + 1, b - a - 1, b, b + 1, len(word) - a) if x != b - a]
        expl = f"`word[{a}:{b}]` has {b - a} characters (indexes {a} to {b - 1}), and `len()` counts them."
    return _print_question(
        difficulty=MEDIUM,
        code=setup + f"print({expr})",
        wrong_codes=[setup + f"print({e})" for e in wrong_e],
        explanation=expl,
        rng=rng,
    )


# ==========================================================================
# HARD -- choice
# ==========================================================================


@generator(TOPIC, HARD)
def gen_method_chain_trace(rng: random.Random) -> Question:
    """strip -> lower -> replace -> print (order and case-sensitivity matter)."""
    phrase, old, new = rng.choice(
        [("Hello Python", "python", "code"), ("Good Morning", "morning", "day"), ("I Love Pizza", "pizza", "pie"), ("Hi Everyone", "everyone", "all")]
    )
    text = _pad(rng, phrase)
    clean = text.strip().lower()
    result = clean.replace(old, new)
    final = rng.choice(["result", "len"])
    code = f'text = "{text}"\nclean = text.strip().lower()\nresult = clean.replace("{old}", "{new}")\n'
    if final == "result":
        code += "print(result)"
        extra = [clean, text.strip().replace(old.capitalize(), new), clean.upper(), result.upper()]
    else:
        code += "print(len(result))"
        extra = [str(len(clean)), str(len(text.strip().replace(old.capitalize(), new))), str(len(text)), str(len(result) + 1)]
    return output_question(
        topic=TOPIC,
        difficulty=HARD,
        code=code,
        distractors=extra,
        explanation="Trace one step at a time: `strip()` removes the end spaces, `lower()` makes everything lowercase, then `replace()` swaps the word. Each step makes a new string.",
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_off_by_one_index(rng: random.Random) -> Question:
    """word[len(word)] is one past the end; word[len(word) - 1] is the last character."""
    word = rng.choice(WORDS6)
    n = len(word)
    v = rng.choice(["past_end", "last", "second_last", "past_end"])
    setup = f'word = "{word}"\n'
    if v == "past_end":
        code = setup + "print(word[len(word)])"
        extra = [word[-1], word[0], error_choice("ValueError"), error_choice("NameError")]
        expl = f"`word` has {n} characters, so the indexes are 0 to {n - 1}. Index {n} does not exist: IndexError. The last character is `word[len(word) - 1]` or `word[-1]`."
        return output_question(
            topic=TOPIC, difficulty=HARD, code=code, distractors=extra, explanation=expl, rng=rng, prompt=PRINT_OR_ERROR, allow_error=True
        )
    if v == "last":
        code = setup + "print(word[len(word) - 1])"
        extra = [word[-2], word[0], error_choice("IndexError"), word[1]]
        expl = f"`len(word) - 1` is {n - 1}, the index of the last character (`word[-1]` is the same character)."
    else:
        code = setup + "print(word[len(word) - 2])"
        extra = [word[-1], word[-3], error_choice("IndexError"), word[1]]
        expl = f"`len(word) - 2` is {n - 2}, the second-to-last character (the same as `word[-2]`)."
    return output_question(
        topic=TOPIC, difficulty=HARD, code=code, distractors=extra, explanation=expl, rng=rng, prompt=PRINT_OR_ERROR, allow_error=True
    )


@generator(TOPIC, HARD)
def gen_alias_reassign(rng: random.Random) -> Question:
    """Two names, one string: methods never change the old string."""
    w = rng.choice(["cat", "dog", "sun", "bug", "ant", "owl"])
    up = w.upper()
    v = rng.choice(["upper_reassign", "upper_lost", "plus_reassign", "plus_new"])
    if v == "upper_reassign":
        code = f'a = "{w}"\nb = a\na = a.upper()\nprint(a, b)'
        extra = [f"{up} {up}", f"{w} {w}", f"{w} {up}"]
        expl = "`a.upper()` makes a NEW string and `a` is reassigned to it. `b` still points at the old string."
    elif v == "upper_lost":
        code = f'a = "{w}"\nb = a\na.upper()\nprint(a, b)'
        extra = [f"{up} {up}", f"{up} {w}", f"{w} {up}"]
        expl = "`a.upper()` creates a new string that is thrown away, so both `a` and `b` are unchanged."
    elif v == "plus_reassign":
        code = f'a = "{w}"\nb = a\na = a + "s"\nprint(a, b)'
        extra = [f"{w}s {w}s", f"{w} {w}s", f"{w} {w}"]
        expl = "`a + \"s\"` builds a new string and `a` now points to it. `b` keeps the old string."
    else:
        code = f'a = "{w}"\nb = a + "s"\nprint(a, b)'
        extra = [f"{w}s {w}s", f"{w}s {w}", f"{w} {w}"]
        expl = "`a + \"s\"` creates a new string stored in `b`; `a` is not changed."
    return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=extra, explanation=expl, rng=rng)


@generator(TOPIC, HARD)
def gen_loop_letters(rng: random.Random) -> Question:
    """Build a new string letter by letter (strings are never changed in place)."""
    word = rng.choice(["Python", "coding", "planet", "rocket", "jungle"])
    v = rng.choice(["reverse", "double", "skip", "count"])
    if v == "reverse":
        code = f'word = "{word}"\nresult = ""\nfor letter in word:\n    result = letter + result\nprint(result)'
        extra = [word, word.upper(), word[::-1].upper(), word[-1]]
        expl = "Each new `letter` is added to the FRONT of `result`, so the letters end up in reverse order."
    elif v == "double":
        code = f'word = "{word}"\nresult = ""\nfor letter in word:\n    result = result + letter + letter\nprint(result)'
        extra = [word, word + word, word[::-1], "".join(c + c for c in word[::-1])]
        expl = "Every pass adds the current `letter` twice to the end of `result`."
    elif v == "skip":
        letter = rng.choice([c for c in word[1:] if word.count(c) == 1])
        code = f'word = "{word}"\nresult = ""\nfor letter in word:\n    if letter != "{letter}":\n        result = result + letter\nprint(result)'
        extra = [word, letter, word[::-1].replace(letter, ""), word.replace(letter, "").upper()]
        expl = f'The `if` skips the letter `{letter}`; every other letter is added to the end of `result`.'
    else:
        code = f'word = "{word}"\ncount = 0\nfor letter in word:\n    count += 1\nprint(count)'
        extra = [str(len(word) - 1), str(len(word) + 1), "1", word]
        expl = "`count` goes up by 1 for every letter, so it ends up equal to `len(word)`."
    return output_question(topic=TOPIC, difficulty=HARD, code=code, distractors=extra, explanation=expl, rng=rng)


@generator(TOPIC, HARD)
def gen_sentence_trace(rng: random.Random) -> Question:
    """split() then index into the list and into the words."""
    phrase = rng.choice(["I love Python programming!", "Python makes coding fun", "We code in Python", "I code after school", "Python is fun to learn"])
    words = phrase.split()
    setup = f'sentence = "{phrase}"\nwords = sentence.split()\n'
    v = rng.choice(["count_last", "letters", "reverse_word"])
    prompt = "What does this code print?"
    if v == "count_last":
        expr = "len(words), words[-1]"
        wrong_e = ["len(sentence), words[-1]", "len(words), words[0]", "len(words) - 1, words[-1]", "len(words), words[len(words)]"]
        expl = "`split()` makes a list of words: `len(words)` counts the words and `words[-1]` is the LAST word."
        prompt = PRINT_OR_ERROR
    elif v == "letters":
        expr = "words[1][0] + words[2][-1]"
        wrong_e = ["words[1][-1] + words[2][0]", "words[0][0] + words[2][-1]", "words[1][0] + words[2][0]", "words[1][0] + words[3][-1]" if len(words) > 3 else "words[2][0] + words[1][-1]"]
        expl = "`words[1]` is the second word, so `words[1][0]` is its first letter. `words[2][-1]` is the last letter of the third word."
    else:
        expr = "words[2][::-1]"
        wrong_e = ["words[2]", "words[-1][::-1]", "words[1][::-1]", "sentence[::-1]"]
        expl = "`words[2]` is the third word, and `[::-1]` reverses just that word."
    return _print_question(
        difficulty=HARD,
        code=setup + f"print({expr})",
        wrong_codes=[setup + f"print({e})" for e in wrong_e],
        explanation=expl,
        rng=rng,
        prompt=prompt,
        allow_error=True,
    )


@generator(TOPIC, HARD)
def gen_slice_chain(rng: random.Random) -> Question:
    """Two slices in a row: word[::-1][0:3] -- reverse first, then slice."""
    word = rng.choice(WORDS6)
    setup = f'word = "{word}"\n'
    v = rng.choice(["rev_then_cut", "cut_then_rev", "rev_part"])
    if v == "rev_then_cut":
        k = rng.choice([2, 3, 4])
        expr = f"word[::-1][0:{k}]"
        wrong_e = [f"word[0:{k}][::-1]", f"word[0:{k}]", f"word[::-1][1:{k + 1}]", f"word[::-1][0:{k - 1}]"]
        expl = f"Left to right: `word[::-1]` reverses first, then `[0:{k}]` keeps the first {k} characters of the reversed word."
    elif v == "cut_then_rev":
        a, b = rng.choice([(1, 5), (0, 4), (1, 4), (2, 5)])
        expr = f"word[{a}:{b}][::-1]"
        wrong_e = [f"word[{a}:{b}]", f"word[::-1][{a}:{b}]", f"word[{a}:{b + 1}][::-1]", f"word[{a - 1}:{b}][::-1]" if a else f"word[{a + 1}:{b}][::-1]"]
        expl = f"First `word[{a}:{b}]` cuts out indexes {a} to {b - 1}, then `[::-1]` reverses that piece."
    else:
        a, b = rng.choice([(1, 3), (2, 4), (0, 2), (1, 4)])
        expr = f"word[::-1][{a}:{b}]"
        wrong_e = [f"word[{a}:{b}]", f"word[{a}:{b}][::-1]", f"word[::-1][{a}:{b + 1}]", f"word[::-1][{a + 1}:{b + 1}]"]
        expl = f"Reverse the whole word first, then take indexes {a} to {b - 1} of the reversed word."
    return _print_question(
        difficulty=HARD,
        code=setup + f"print({expr})",
        wrong_codes=[setup + f"print({e})" for e in wrong_e],
        explanation=expl,
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_fstring_hard(rng: random.Random) -> Question:
    """f-strings with indexes, len() and arithmetic -- evaluate each {} separately."""
    first, last = rng.choice(FULL_NAMES)
    setup = f'first = "{first}"\nlast = "{last}"\n'
    v = rng.choice(["initials", "total", "username"])
    if v == "initials":
        body = 'print(f"{first[0]}.{last[0]}. has {len(first) + len(last)} letters")'
        alts = [
            'print(f"{first[0]}.{last[0]}. has {len(first)} + {len(last)} letters")',
            'print(f"{first[1]}.{last[1]}. has {len(first) + len(last)} letters")',
            'print(f"{first}.{last}. has {len(first) + len(last)} letters")',
            'print(f"{first[0]}.{last[0]}. has {len(first) * len(last)} letters")',
        ]
        expl = "Work out each `{}` on its own: `first[0]` and `last[0]` are first letters; `len(first) + len(last)` is real addition of two numbers."
    elif v == "total":
        body = 'print(f"{first.upper()} {last[0]}. ({len(first) + len(last)})")'
        alts = [
            'print(f"{first} {last[0]}. ({len(first) + len(last)})")',
            'print(f"{first.upper()} {last[1]}. ({len(first) + len(last)})")',
            'print(f"{first.upper()} {last[0]}. ({len(first)} + {len(last)})")',
            'print(f"{first.upper()} {last}. ({len(first) + len(last)})")',
        ]
        expl = "`first.upper()` gives capitals, `last[0]` is the first letter of the last name, and `len(first) + len(last)` adds the two lengths."
    else:
        body = 'print(f"{first[0]}{last}{len(first)}")'
        alts = [
            'print(f"{first[0]}{last}{len(last)}")',
            'print(f"{first[0]}{last[0]}{len(first)}")',
            'print(f"{first[-1]}{last}{len(first)}")',
            'print(f"{first}{last[0]}{len(first)}")',
        ]
        expl = "Work out each `{}`: `first[0]` is the first letter, `last` is the whole last name, and `len(first)` is the number of letters in the first name."
    return _print_question(
        difficulty=HARD,
        code=setup + body,
        wrong_codes=[setup + a for a in alts],
        explanation=expl,
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_palindrome_which(rng: random.Random) -> Question:
    """Reverse with slicing and compare: word == word[::-1]."""
    var = rng.choice(["word", "text", "name"])
    correct = rng.choice([f"{var} == {var}[::-1]", f"{var}[::-1] == {var}"])
    pool = [
        f"{var} == {var}[-1]",
        f"{var}[0] == {var}[-1]",
        f"{var} != {var}[::-1]",
        f"{var} == {var}[0:-1]",
        f"{var}[::-1]",
        f"{var}[0] == {var}[1]",
    ]
    return build_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Which condition checks that `{var}` reads the same forwards and backwards (like `level`)?",
        correct=correct,
        distractors=rng.sample(pool, 3),
        explanation=f"`{var}[::-1]` is the string backwards. If it equals `{var}`, the word is the same in both directions. Comparing only the first and last letter is not enough (`tent`).",
        rng=rng,
    )


# ==========================================================================
# BLANKS
# ==========================================================================


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_slice_method(rng: random.Random) -> Question:
    """Quiz item 'String methods & slicing': word[0:4] and text.strip()."""
    word = rng.choice(["Python"] + WORDS_ANY)
    n = rng.choice([3, 4, 5])
    phrase = rng.choice(PHRASES)
    text = _pad(rng, phrase)
    method, ask, result = rng.choice(
        [
            ("strip", "trim the extra spaces from both ends of `text`", text.strip()),
            ("upper", "make `text` all capital letters", text.upper()),
            ("lower", "make `text` all lowercase", text.lower()),
        ]
    )
    template = (
        f'word = "{word}"\ntext = "{text}"\n'
        f"print(word[{blank_mark(1)}:{blank_mark(2)}])\nprint(text.{blank_mark(3)}())"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the blanks: get the first {n} characters of `word`, and {ask}.",
        template=template,
        blanks=[
            Blank(["0"], hint="start", mode="expr"),
            Blank([str(n)], hint="end", mode="expr"),
            Blank([method], hint="method"),
        ],
        explanation=f"`word[0:{n}]` takes indexes 0 to {n - 1} (the end is not included), and `text.{method}()` returns the changed string.",
        expect_output=f"{word[:n]}\n{result}",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_fstring(rng: random.Random) -> Question:
    """Quiz item 'Printing & f-strings': str(age) and f."""
    label = rng.choice(["Age", "Score", "Level", "Coins"])
    var = label.lower()
    value = rng.randint(5, 99)
    template = f'{var} = {value}\nprint("{label}: " + {blank_mark(1)}({var}))\nprint({blank_mark(2)}"{label}: {{{var}}}")'
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Fill in the blanks: join text and a number safely, then use modern formatting.",
        template=template,
        blanks=[Blank(["str"], hint="function"), Blank(["f", "F"], hint="prefix letter")],
        explanation=f"`str({var})` turns the number into text so `+` works. An `f` in front of the quotes makes an f-string that fills in `{{{var}}}`.",
        expect_output=f"{label}: {value}\n{label}: {value}",
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_first_last_reverse(rng: random.Random) -> Question:
    """word[0], word[-1] and word[::-1]."""
    word = rng.choice(WORDS6)
    template = (
        f'word = "{word}"\nfirst = word[{blank_mark(1)}]\nlast = word[{blank_mark(2)}]\nbackwards = word[{blank_mark(3)}]\nprint(first, last, backwards)'
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Fill in the blanks to get the first character, the last character, and the word backwards.",
        template=template,
        blanks=[
            Blank(["0"], hint="first", mode="expr"),
            Blank(["-1", "len(word) - 1"], hint="last", mode="expr"),
            Blank(["::-1"], hint="reverse"),
        ],
        explanation="`word[0]` is the first character, `word[-1]` is the last, and `word[::-1]` reverses the whole string.",
        expect_output=f"{word[0]} {word[-1]} {word[::-1]}",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_split_join(rng: random.Random) -> Question:
    """Lesson: words = text.split(" ") ... "-".join(words)"""
    phrase = rng.choice(PHRASES)
    sep = rng.choice(["-", "-", "_", "*"])
    template = f'text = "{phrase}"\nwords = text.{blank_mark(1)}(" ")\njoined = "{sep}".{blank_mark(2)}(words)\nprint(joined)'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks: split `text` into a list of words, then join them with `{sep}` between the words.",
        template=template,
        blanks=[Blank(["split"], hint="text to list"), Blank(["join"], hint="list to text")],
        explanation='`split(" ")` turns the string into a list of words. `"-".join(words)` stitches the list back into one string.',
        expect_output=sep.join(phrase.split(" ")),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_immutable(rng: random.Random) -> Question:
    """Methods return new strings: assign the result back."""
    var = rng.choice(["word", "text", "name"])
    method, ask = rng.choice([("upper", "in capital letters"), ("lower", "in lowercase letters")])
    value = rng.choice(["Python", "coding", "planet", "Ada"] if method == "upper" else ["Python", "Banana", "Ada", "Coding"])
    result = value.upper() if method == "upper" else value.lower()
    template = f'{var} = "{value}"\n{blank_mark(1)} = {var}.{blank_mark(2)}()\nprint({var})'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so that `{var}` itself ends up {ask}.",
        template=template,
        blanks=[Blank([var], hint="variable"), Blank([method], hint="method")],
        explanation=f"Methods return a new string, so the result must be assigned back: `{var} = {var}.{method}()`.",
        expect_output=result,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_count_replace(rng: random.Random) -> Question:
    """Bingo: count how many 'o' letters; replace 'Python' with 'coding'."""
    phrase, old, new = rng.choice(REPLACE_TRIPLES)
    letter = rng.choice([c for c in "oaeit" if c in phrase])
    template = f'text = "{phrase}"\nprint(text.{blank_mark(1)}("{letter}"))\nprint(text.{blank_mark(2)}("{old}", "{new}"))'
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks: count the letter `{letter}` in `text`, then swap `{old}` for `{new}`.",
        template=template,
        blanks=[Blank(["count"], hint="how many"), Blank(["replace"], hint="swap")],
        explanation=f'`text.count("{letter}")` counts the letter; `text.replace("{old}", "{new}")` returns the text with the word swapped.',
        expect_output=f"{phrase.count(letter)}\n{phrase.replace(old, new)}",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_first_name(rng: random.Random) -> Question:
    """Mini-Challenge 'First Name Slice': print Reid C. from a full name."""
    first, last = rng.choice(FULL_NAMES)
    template = (
        f'full_name = "{first} {last}"\nparts = full_name.{blank_mark(1)}()\nfirst = parts[{blank_mark(2)}]\n'
        f"initial = parts[1][{blank_mark(3)}]\nprint(first, initial + {blank_mark(4)})"
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Complete the Mini-Challenge so it prints the first name and the last initial with a period, like `{first} {last[0]}.`",
        template=template,
        blanks=[
            Blank(["split"], hint="method"),
            Blank(["0"], hint="index", mode="expr"),
            Blank(["0"], hint="index", mode="expr"),
            Blank(['"."', "'.'"], hint="the period", mode="expr"),
        ],
        explanation="`split()` gives `[first, last]`. `parts[0]` is the first name, `parts[1][0]` is the first letter of the last name, and `\".\"` adds the period.",
        expect_output=f"{first} {last[0]}.",
    )


# ==========================================================================
# MATCH
# ==========================================================================


@generator(TOPIC, EASY, qtype="match")
def gen_match_methods(rng: random.Random) -> Question:
    """Match each string method to what it does."""
    var = rng.choice(["text", "word", "sentence"])
    pairs = [
        (f"{var}.upper()", "All capital letters"),
        (f"{var}.lower()", "All lowercase letters"),
        (f"{var}.strip()", "Removes spaces at both ends"),
        (f'{var}.replace("a", "b")', "Swaps one piece of text for another"),
        (f'{var}.count("a")', "Counts how many times it appears"),
        (f"{var}.split()", "Makes a list of words"),
        ('"-".join(words)', "Stitches a list into one string"),
    ]
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each string method to what it does.",
        pairs=rng.sample(pairs, 5),
        explanation="Every one of these methods returns a NEW value (a string, a list or a number) and leaves the original string unchanged.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_index_slice(rng: random.Random) -> Question:
    """Match each indexing / slicing expression to its result."""
    word = rng.choice(["Python", "planet", "rocket", "castle", "jungle", "guitar", "pencil"])
    exprs = ["word[0]", "word[-1]", "word[1]", "word[0:4]", "word[2:5]", "word[::-1]", "len(word)"]
    chosen = rng.sample(exprs, 5)
    pairs = [(e, _show(eval_expr(e, f'word = "{word}"'))) for e in chosen]
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f'Match each expression to its result, where `word = "{word}"`.',
        pairs=pairs,
        explanation="Index 0 is the first character, -1 is the last, `[a:b]` stops before `b`, `[::-1]` reverses, and `len()` counts the characters.",
        rng=rng,
        code=f'word = "{word}"',
    )


@generator(TOPIC, EASY, qtype="match")
def gen_match_return_types(rng: random.Random) -> Question:
    """Match each expression to the type it returns."""
    pairs = [
        ('text.upper()', "str"),
        ('text.strip()', "str"),
        ('text.split()', "list"),
        ('len(text)', "int"),
        ('text.count("o")', "int"),
        ('text[0]', "str"),
        ('text[::-1]', "str"),
        ('"-".join(words)', "str"),
    ]
    chosen = rng.sample(pairs, 5)
    if len({a for _, a in chosen}) < 3:
        chosen = [p for p in pairs if p[1] == "list"] + [p for p in pairs if p[1] == "int"][:2] + [p for p in pairs if p[1] == "str"][:2]
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each expression to the type of value it gives.",
        pairs=chosen,
        explanation="Methods that change text give a `str`, `split()` gives a `list` of words, and `len()` / `count()` give an `int`.",
        rng=rng,
        extra_options=["bool"],
        code='text = "I love Python"\nwords = ["I", "love"]',
    )


@generator(TOPIC, HARD, qtype="match")
def gen_match_fstring(rng: random.Random) -> Question:
    """Match each f-string to what it prints."""
    name = rng.choice(["Ada", "Eli", "Sam", "Ivy"])
    age = rng.randint(12, 17)
    setup = f'name = "{name}"\nage = {age}'
    templates = ['{name}', '{name.upper()}', '{age + 1}', '{len(name)}', '{name[0]}', '{name[::-1]}', '{age * 2}']
    chosen = rng.sample(templates, 5)
    pairs = [(f'f"{t}"', eval_expr(f'f"{t}"', setup)) for t in chosen]
    pairs = [(a, str(b)) for a, b in pairs]
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Match each f-string to the text it produces.",
        pairs=pairs,
        explanation="Python evaluates whatever is inside `{}` (methods, indexes, `len()`, math) and puts the result into the text.",
        rng=rng,
        code=setup,
    )


# ==========================================================================
# CODE
# ==========================================================================


@generator(TOPIC, EASY, qtype="code")
def gen_code_char_expr(rng: random.Random) -> Question:
    """Type an expression: first / last character of word."""
    var = rng.choice(["word", "text", "name"])
    kind = rng.choice(["first", "last"])
    sol = f"{var}[0]" if kind == "first" else f"{var}[-1]"
    pool = [w for w in ["Python", "rocket", "banana", "coding", "school", "planet", "puzzle", "garden", "teacher", "cherry", "laptop", "program"] if w[0] != w[-1]]
    vals = rng.sample(pool, 4)
    cases = [({var: w}, w[0] if kind == "first" else w[-1]) for w in vals]
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds some text. Type an expression that gives its **{kind} character**.",
        task=expression_task(sol, cases),
        explanation="Indexing starts at 0, so `[0]` is the first character; `[-1]` counts from the end and gives the last one.",
        code=f'{var} = "{vals[0]}"',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_slice_expr(rng: random.Random) -> Question:
    """Type an expression: word[0:4]."""
    var = rng.choice(["word", "text", "name"])
    a, b = rng.choice([(0, 3), (0, 4), (0, 4), (0, 5), (1, 4), (2, 5)])
    sol = f"{var}[{a}:{b}]"
    pool = ["Python", "rocket", "banana", "coding", "school", "planet", "puzzle", "garden", "teacher", "cherry", "laptop", "program"]
    vals = rng.sample(pool, 4)
    if a == 0:
        what = f"the first {b} characters"
    else:
        what = f"the characters from index {a} up to (but not including) index {b}"
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"`{var}` holds a word. Type a slice that gives {what} of `{var}`.",
        task=expression_task(sol, [({var: w}, w[a:b]) for w in vals]),
        explanation=f"`{sol}` starts at index {a} and stops BEFORE index {b}. (`{var}[:{b}]` also works for the first {b}.)" if a == 0 else f"`{sol}` starts at index {a} and stops BEFORE index {b}.",
        code=f'{var} = "{vals[0]}"',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_reverse_expr(rng: random.Random) -> Question:
    """Type an expression: word[::-1] (optionally .upper())."""
    var = rng.choice(["word", "text", "name"])
    upper = rng.random() < 0.4
    sol = f"{var}[::-1].upper()" if upper else f"{var}[::-1]"
    pool = ["Python", "rocket", "banana", "coding", "school", "planet", "puzzle", "garden", "teacher", "cherry", "laptop", "program", "Ada", "level"]
    vals = rng.sample(pool, 4)
    cases = [({var: w}, w[::-1].upper() if upper else w[::-1]) for w in vals]
    tail = " and in CAPITAL letters" if upper else ""
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Type an expression that gives `{var}` backwards{tail}.",
        task=expression_task(sol, cases),
        explanation="`[::-1]` reverses a string" + (", and `.upper()` makes the letters capitals." if upper else "."),
        code=f'{var} = "{vals[0]}"',
    )


@generator(TOPIC, EASY, qtype="code")
def gen_code_clean_expr(rng: random.Random) -> Question:
    """Type an expression: strip + upper/lower, or replace."""
    if rng.random() < 0.6:
        meth = rng.choice(["upper", "lower"])
        sol = f"text.strip().{meth}()"
        phrases = rng.sample(PHRASES + ["Hello World", "Good Morning"], 4)
        cases = [({"text": _pad(rng, p)}, getattr(p, meth)()) for p in phrases]
        what = "all capital letters" if meth == "upper" else "all lowercase letters"
        prompt = f"`text` has extra spaces at both ends. Type an expression that removes them **and** gives the text in {what}."
        expl = f"`strip()` removes the end spaces and `{meth}()` changes the letters. Chain them: `{sol}`."
        code = f'text = "{cases[0][0]["text"]}"'
    else:
        phrase, old, new = rng.choice(REPLACE_TRIPLES)
        sol = f'text.replace("{old}", "{new}")'
        others = [t for t in REPLACE_TRIPLES if t[0] != phrase]
        vals = [phrase, "Say " + old + " and " + old + " again", "nothing to swap here"] + [o[0] for o in rng.sample(others, 1)]
        cases = [({"text": v}, v.replace(old, new)) for v in vals]
        prompt = f'Type an expression that replaces every `{old}` in `text` with `{new}`.'
        expl = f'`text.replace("{old}", "{new}")` returns a new string with every `{old}` swapped. If the word is not there, nothing changes.'
        code = f'text = "{phrase}"'
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=expression_task(sol, cases), explanation=expl, code=code)


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_fstring_expr(rng: random.Random) -> Question:
    """Type an f-string like the lesson's."""
    v = rng.choice(["lesson", "next_year", "letters"])
    names = rng.sample(FIRST_NAMES, 4)
    ages = rng.sample(range(11, 19), 4)
    n0, a0 = names[0], ages[0]
    if v == "lesson":
        sol = 'f"My name is {name}, and I am {age} years old."'
        want = lambda n, a: f"My name is {n}, and I am {a} years old."  # noqa: E731
        hint = "Use both `name` and `age`."
    elif v == "next_year":
        sol = 'f"{name.upper()} is {age + 1} next year"'
        want = lambda n, a: f"{n.upper()} is {a + 1} next year"  # noqa: E731
        hint = "The name is in capital letters and the age is one more."
    else:
        sol = 'f"{name} has {len(name)} letters"'
        want = lambda n, a: f"{n} has {len(n)} letters"  # noqa: E731
        hint = "Use `len(name)` for the number."
    cases = [({"name": n, "age": a}, want(n, a)) for n, a in zip(names, ages)]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Type an f-string that gives `{want(n0, a0)}` for these variables. {hint}",
        task=expression_task(sol, cases),
        explanation="Start the string with `f` and put variables or expressions inside `{}`.",
        code=f'name = "{n0}"\nage = {a0}',
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_first_name_program(rng: random.Random) -> Question:
    """Mini-Challenge: First Name Slice (Reid C.)"""
    names = rng.sample(FULL_NAMES, 4)
    solution = 'full_name = input("Enter your full name: ")\nparts = full_name.split()\nprint(parts[0], parts[1][0] + ".")'
    cases = [Case(stdin=[f"{f} {l}"], out=f"{f} {l[0]}.") for f, l in names]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks for a full name with `input()` (two words, like `{names[0][0]} {names[0][1]}`) and prints the first name and the last initial with a period, like `{names[0][0]} {names[0][1][0]}.`",
        task=program_task(solution, cases, starter='full_name = input("Enter your full name: ")\n'),
        explanation="`split()` turns the name into a list of two words. Print `parts[0]` and the first letter of `parts[1]`, then add the period.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_dash_function(rng: random.Random) -> Question:
    """Bingo: split a sentence into words and rejoin with dashes."""
    sep = rng.choice(["-", "-", "_"])
    solution = f'def dash_words(sentence):\n    return "{sep}".join(sentence.strip().split(" "))'
    sents = rng.sample(PHRASES, 3) + ["Hello"]
    vals = [sents[0], "  " + sents[1] + " ", sents[2], sents[3]]
    cases = [((v,), sep.join(v.strip().split(" "))) for v in vals]
    name = {"-": "hyphens (`-`)", "_": "underscores (`_`)"}[sep]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `dash_words(sentence)` that **returns** the words of `sentence` joined with {name}. The sentence may have extra spaces at the start or end, and has single spaces between words.",
        task=function_task("dash_words", solution, cases),
        explanation=f'`strip()` first removes the end spaces, `split(" ")` makes a list of words, and `"{sep}".join(...)` stitches them together.',
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_bingo_text_program(rng: random.Random) -> Question:
    """Python Bingo string tasks as tiny programs: count, strip, replace, reverse, first 3 characters."""
    v = rng.choice(["count", "strip", "replace", "reverse", "first3"])
    starter = 'text = input("Enter some text: ")\n'
    if v == "count":
        letter = rng.choice(["a", "e", "o", "s", "t"])
        solution = starter + f'print(text.count("{letter}"))'
        texts = rng.sample(PHRASES, 3) + [letter.upper() * 2 + " and zzz", "xyz"]
        cases = [Case(stdin=[t], out=str(t.count(letter))) for t in texts]
        prompt = f"Write a program that reads a line of text with `input()` and prints how many times the lowercase letter `{letter}` appears in it."
        expl = f'`text.count("{letter}")` counts the letter. It is case-sensitive, so `{letter.upper()}` is not counted.'
    elif v == "strip":
        solution = starter + 'print("[" + text.strip() + "]")'
        texts = [_pad(rng, p) for p in rng.sample(PHRASES, 3)] + ["  hello"]
        cases = [Case(stdin=[t], out=f"[{t.strip()}]") for t in texts]
        prompt = "Write a program that reads a line of text with `input()` (it may have extra spaces at the start or end) and prints it without those spaces, inside square brackets, like `[hello]`."
        expl = "`text.strip()` removes the spaces at both ends. Join the brackets on with `+`."
    elif v == "replace":
        phrase, old, new = rng.choice(REPLACE_TRIPLES)
        solution = starter + f'print(text.replace("{old}", "{new}"))'
        texts = [phrase, f"{old} and {old}", "nothing to swap"] + [rng.choice([t[0] for t in REPLACE_TRIPLES if t[0] != phrase])]
        cases = [Case(stdin=[t], out=t.replace(old, new)) for t in texts]
        prompt = f"Write a program that reads a sentence with `input()` and prints it with every `{old}` replaced by `{new}`."
        expl = f'`text.replace("{old}", "{new}")` returns a new string with every `{old}` swapped. If the word is missing, the text is unchanged.'
    elif v == "reverse":
        solution = starter + "print(text[::-1])"
        texts = [rng.choice(WORDS_ANY), rng.choice(PHRASES), "Ada", "level"]
        cases = [Case(stdin=[t], out=t[::-1]) for t in texts]
        prompt = "Write a program that reads a line of text with `input()` and prints it backwards."
        expl = "`text[::-1]` reverses a string."
    else:
        solution = starter + "print(text[0:3])"
        texts = [rng.choice(WORDS_ANY), rng.choice(PHRASES), "Ada", "Python"]
        cases = [Case(stdin=[t], out=t[0:3]) for t in texts]
        prompt = "Write a program that reads a line of text with `input()` and prints its first 3 characters."
        expl = "`text[0:3]` starts at index 0 and stops before index 3, so it gives the first 3 characters."
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        task=program_task(solution, cases, starter=starter),
        explanation=expl,
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_words_per_line(rng: random.Random) -> Question:
    """Print each word on its own line (the \\n escape / split)."""
    solution = 'sentence = input("Enter a sentence: ")\nwords = sentence.split()\nprint("\\n".join(words))'
    sents = rng.sample(PHRASES, 3) + ["Hello"]
    cases = [Case(stdin=[s], out="\n".join(s.split())) for s in sents]
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Write a program that reads a sentence with `input()` and prints each word on its own line.",
        task=program_task(solution, cases, starter='sentence = input("Enter a sentence: ")\n'),
        explanation='`split()` makes a list of words. `"\\n".join(words)` puts a new line between them (or print each word in a `for` loop).',
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_initials_function(rng: random.Random) -> Question:
    """initials("Ada Lovelace") -> "A.L." (loop over split())."""
    solution = (
        "def initials(full_name):\n"
        '    result = ""\n'
        "    for part in full_name.split():\n"
        '        result = result + part[0].upper() + "."\n'
        "    return result"
    )
    pool = ["Ada Lovelace", "grace hopper", "Alan Mathison Turing", "Cher", "sam rivera", "Mia Ann Lopez", "reid carter"]
    vals = rng.sample(pool, 4)

    def want(n):
        return "".join(p[0].upper() + "." for p in n.split())

    cases = [((v,), want(v)) for v in vals]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt='Write a function `initials(full_name)` that **returns** the capital first letter of every word, each followed by a period. For example `initials("ada lovelace")` returns `"A.L."`.',
        task=function_task("initials", solution, cases),
        explanation="`split()` gives the words. In a `for` loop, take `part[0]`, make it capital with `upper()`, add a period, and build up `result`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_palindrome_function(rng: random.Random) -> Question:
    """Reverse with [::-1] and compare, ignoring case and spaces."""
    solution = (
        "def is_palindrome(text):\n"
        '    clean = text.lower().replace(" ", "")\n'
        "    return clean == clean[::-1]"
    )
    yes_caps = ["Racecar", "Mom", "Level", "Radar", "Noon"]  # a capital letter, no spaces
    yes_spaces = ["never odd or even", "A man a plan a canal Panama", "Was it a car or a cat I saw", "Race car"]  # spaces
    no = ["Python", "hello world", "Ab", "not a palindrome", "Almost Level", "Never odd or odd"]
    n = rng.sample(no, 2)
    vals = [rng.choice(yes_caps), n[0], rng.choice(yes_spaces), n[1]]  # the visible examples show one True and one False
    cases = [((v,), v.lower().replace(" ", "") == v.lower().replace(" ", "")[::-1]) for v in vals]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt='Write a function `is_palindrome(text)` that **returns** `True` if `text` reads the same forwards and backwards, ignoring capital letters and spaces, otherwise `False`. For example `"Race car"` is a palindrome.',
        task=function_task("is_palindrome", solution, cases),
        explanation="Make the text lowercase and remove the spaces, then compare it with itself reversed: `clean == clean[::-1]`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_reverse_words_function(rng: random.Random) -> Question:
    """reverse_words("I love Python") -> "Python love I"."""
    solution = 'def reverse_words(sentence):\n    return " ".join(sentence.split()[::-1])'
    pool = ["I love Python", "Python makes coding fun", "We code in Python", "Hello", "I code after school", "one two"]
    vals = rng.sample(pool, 4)
    cases = [((v,), " ".join(v.split()[::-1])) for v in vals]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt='Write a function `reverse_words(sentence)` that **returns** the words of `sentence` in the opposite order, separated by single spaces. For example `reverse_words("I love Python")` returns `"Python love I"`.',
        task=function_task("reverse_words", solution, cases),
        explanation='`split()` makes a list of words, `[::-1]` reverses the list, and `" ".join(...)` stitches the words back into one string.',
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_count_vowels_function(rng: random.Random) -> Question:
    """Loop over a word and count the vowels (case-insensitive)."""
    solution = (
        "def count_vowels(word):\n"
        "    total = 0\n"
        "    for letter in word.lower():\n"
        '        if letter == "a" or letter == "e" or letter == "i" or letter == "o" or letter == "u":\n'
        "            total += 1\n"
        "    return total"
    )
    caps = ["AEIOU", "Orange", "Apple", "Ice", "Umbrella", "Eagle"]  # capital vowels count too
    plain = ["Python", "rhythm", "sky", "Happy", "Gym"]  # includes the letter y (not a vowel here)
    other = ["banana", "School", "Programming", "queue", "tree", "moon"]
    vals = [rng.choice(caps), rng.choice(plain)]
    rest = [w for w in other + plain if w not in vals]
    vals += rng.sample(rest, 2)

    def want(w):
        return sum(1 for c in w.lower() if c in "aeiou")

    cases = [((v,), want(v)) for v in vals]
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Write a function `count_vowels(word)` that **returns** how many vowels (`a`, `e`, `i`, `o`, `u`) are in `word`. Capital letters count too.",
        task=function_task("count_vowels", solution, cases),
        explanation="Loop over the letters of `word.lower()` (so capitals are handled), add 1 to `total` for each vowel, and return `total`.",
    )
