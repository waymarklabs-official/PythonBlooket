"""Question generators for the "while_loops" topic (CSF.2.I: Loops, Part 1 -- ``while`` loops).

Everything here follows the lesson: the classic counter (initialization / condition / update,
``Count is:``), what goes wrong without an update (infinite loop, Ctrl + C), a controlled
infinite loop (``while True`` + ``break``, the ``quit`` prompt), the Countdown mini-challenge
(``Blastoff!``) and the Python Bingo "While loop" squares (count 1 to 5, password until
correct, break on ``quit``, sum positives until 0).

Wherever the right answer depends on running a snippet, it is computed by *running* it
(``_sim``: a tiny tracer that also stops runaway loops and feeds scripted ``input()``
answers), and the wrong answers are taken from slightly broken copies of the same code
(off-by-one, update in the wrong place, ...), so every question is correct by construction.
"""

from __future__ import annotations

import random
import sys

from ..base import (
    EASY,
    HARD,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    MEDIUM,
    NAMES,
    NOTHING_PRINTED,
    GenerationError,
    Question,
    blanks_question,
    build_question,
    code_question,
    expression_task,
    function_task,
    generator,
    match_question,
    output_question,
    program_task,
)
from ..spec import Blank, Case, blank_mark

TOPIC = "while_loops"

LOOPING = "(the loop never ends)"
BLANK = "____"

# The lesson names its counter ``count`` (and ``num`` in the infinite-loop demo).
_COUNTERS = ["count"] * 4 + ["num"] * 3 + ["number", "n", "lap", "level"]
_LABELS = {
    "count": "Count is:",
    "num": "Number:",
    "number": "Number:",
    "n": "Value:",
    "lap": "Lap",
    "level": "Level",
}
_QUIT_WORDS = ["quit", "quit", "quit", "stop", "done", "exit"]
_STOP_WORDS = ["quit", "stop", "done", "exit", "bye", "end"]
_SECRETS = ["python", "rocket", "banana", "tiger", "pixel", "orbit", "lemon", "blook"]
_FINALES = ["Blastoff!", "Blastoff!", "Blastoff!", "Liftoff!", "Go!", "Launch!"]


# --------------------------------------------------------------------------
# Running snippets (scripted input, runaway-loop guard)
# --------------------------------------------------------------------------

_STEP_CAP = 4000


class _StepCap(BaseException):
    pass


def _sim(code: str, stdin=()) -> tuple[str, str | None, int]:
    """Run a *generated* snippet; ``input()`` answers come from ``stdin``.

    Returns ``(printed text, error, steps)`` where ``error`` is None for a clean run, ``"LOOP"``
    when the snippet was still going after ``_STEP_CAP`` lines (a runaway loop), or the
    exception class name.  Only ever used on code produced by our own generators."""
    lines = [str(s) for s in stdin]
    out: list[str] = []
    steps = [0]

    def _print(*args, sep=" ", end="\n"):
        out.append((" " if sep is None else sep).join(str(a) for a in args) + ("\n" if end is None else end))

    def _input(prompt=""):
        if not lines:
            raise EOFError("the scripted input ran out")
        return lines.pop(0)

    def _tracer(frame, event, arg):
        if frame.f_code.co_filename != "<snippet>":
            return None
        if event == "line":
            steps[0] += 1
            if steps[0] > _STEP_CAP:
                raise _StepCap()
        return _tracer

    try:
        compiled = compile(code, "<snippet>", "exec")
    except SyntaxError:
        return "", "SyntaxError", 0
    ns = {"__name__": "__main__", "print": _print, "input": _input}
    err = None
    previous = sys.gettrace()
    sys.settrace(_tracer)
    try:
        exec(compiled, ns)
    except _StepCap:
        err = "LOOP"
    except Exception as exc:  # noqa: BLE001 - we want the class name
        err = type(exc).__name__
    finally:
        sys.settrace(previous)
    text = "".join(out)
    if text.endswith("\n"):
        text = text[:-1]
    return text, err, steps[0]


def _must_run(code: str, stdin=()) -> str:
    text, err, _ = _sim(code, stdin)
    if err:
        raise GenerationError(f"snippet failed ({err}):\n{code}")
    return text


def _runs_forever(code: str, stdin=()) -> bool:
    return _sim(code, stdin)[1] == "LOOP"


# --------------------------------------------------------------------------
# Building choice questions
# --------------------------------------------------------------------------


def _fits(choice: str) -> bool:
    lines = [ln.rstrip() for ln in choice.strip("\n").split("\n")]
    return (
        bool(choice.strip())
        and len(lines) <= MAX_CHOICE_LINES
        and all(len(ln) <= MAX_CHOICE_LINE_LEN for ln in lines)
    )


def _usable(distractors) -> list[str]:
    out = []
    for d in distractors:
        if d is None:
            continue
        d = str(d)
        if d == "":
            d = NOTHING_PRINTED
        if _fits(d):
            out.append(d)
    return out


def _choice(
    *,
    difficulty: int,
    prompt: str,
    correct,
    distractors,
    explanation: str,
    rng: random.Random,
    code: str | None = None,
) -> Question:
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=str(correct),
        distractors=_usable(distractors),
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _concept(difficulty: int, rng: random.Random, pool) -> Question:
    """One question from a pool of ``(prompt, correct, [wrong...], explanation)`` entries."""
    prompt, correct, wrong, explanation = rng.choice(pool)
    wrong = list(wrong)
    rng.shuffle(wrong)
    return _choice(
        difficulty=difficulty,
        prompt=prompt,
        correct=correct,
        distractors=wrong,
        explanation=explanation,
        rng=rng,
    )


def _mutant_outputs(code: str, mutations, stdin=None, forever: bool = False) -> list[str]:
    """What slightly broken copies of ``code`` print -- the answers a student who made that
    mistake would pick.  ``mutations`` = [(old, new), ...] applied one at a time.  A copy
    that never ends gives ``LOOPING`` (only if ``forever``); one that crashes is skipped."""
    outs = []
    for old, new in mutations:
        if old not in code:
            continue
        text, err, _ = _sim(code.replace(old, new, 1), stdin or ())
        if err == "LOOP":
            if forever:
                outs.append(LOOPING)
        elif err is None:
            outs.append(text)
    return outs


def _trace(
    difficulty: int,
    code: str,
    rng: random.Random,
    explanation: str,
    *,
    mutations=(),
    extras=(),
    prompt: str | None = None,
    stdin=None,
    forever: bool = False,
) -> Question:
    """'What does this print?' for a snippet.  The right answer is what the snippet really
    prints; wrong answers come from mutated copies first, then ``extras``."""
    code = code.strip("\n")
    if prompt is None:
        prompt = rng.choice(["What does this code print?", "What is printed when this code runs?"])
    correct = _must_run(code, stdin or ())
    wrong = _mutant_outputs(code, mutations, stdin, forever=forever) + [str(e) for e in extras]
    wrong = [w for w in wrong if w != correct]
    if stdin is None:
        # no input(): the base helper re-runs the snippet itself (tests do too)
        return output_question(
            topic=TOPIC,
            difficulty=difficulty,
            code=code,
            distractors=_usable(wrong),
            explanation=explanation,
            rng=rng,
            prompt=prompt,
        )
    return build_question(
        topic=TOPIC,
        difficulty=difficulty,
        prompt=prompt,
        correct=correct if correct else NOTHING_PRINTED,
        distractors=_usable(wrong),
        explanation=explanation,
        rng=rng,
        code=code,
    )


def _typed(words) -> str:
    """'`hi`, `ok`, then `quit`' for a prompt."""
    words = [f"`{w}`" for w in words]
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + ", then " + words[-1]


def _var(rng: random.Random) -> str:
    return rng.choice(_COUNTERS)


def _lines(*parts: str) -> str:
    return "\n".join(parts)


# ==========================================================================
# EASY -- choice (vocabulary, one-line results, the lesson's own snippets)
# ==========================================================================


@generator(TOPIC, EASY)
def gen_which_piece(rng: random.Random) -> Question:
    """Lesson 1) 'The Classic Counter': name the line that is the initialization / condition / update."""
    var = _var(rng)
    label = _LABELS[var]
    if rng.random() < 0.7:
        start = rng.choice([1, 1, 1, 2, 3])
        limit = start + rng.randint(3, 7)
        step = rng.choice([1, 1, 1, 2])
        init, cond, upd = f"{var} = {start}", f"while {var} <= {limit}:", f"{var} += {step}"
    else:
        start = rng.randint(4, 9)
        init, cond, upd = f"{var} = {start}", f"while {var} > 0:", f"{var} -= 1"
    body = f'print("{label}", {var})'
    code = _lines(init, cond, f"    {body}", f"    {upd}")
    which = rng.choice(["init", "cond", "update"])
    parts = {"init": init, "cond": cond, "update": upd}
    prompt = {
        "init": "In this loop, which line is the initialization?",
        "cond": "In this loop, which line is the condition?",
        "update": "In this loop, which line is the update?",
    }[which]
    explanation = {
        "init": "The initialization sets the starting value before the loop begins.",
        "cond": "The condition is the test after `while`: the loop keeps running as long as it is True.",
        "update": "The update changes the value each time so the condition can eventually become False.",
    }[which]
    others = [t for t in (init, cond, body, upd) if t != parts[which]]
    return _choice(
        difficulty=EASY,
        prompt=prompt,
        code=code,
        correct=parts[which],
        distractors=others,
        explanation=explanation,
        rng=rng,
    )


_HOW_WHILE_WORKS = [
    (
        "A `while` loop keeps running as long as what is true?",
        "Its condition is True",
        ["It has repeated fewer than 10 times", "The user keeps typing input", "No `break` has been written yet"],
        "A `while` loop checks its condition; if it is True it runs the indented block, then checks again.",
    ),
    (
        "What does a `while` loop do after it finishes the indented block?",
        "It checks the condition again",
        [
            "It stops, because loops only run once",
            "It jumps back to the first line of the file",
            "It waits for the user to press Ctrl + C",
        ],
        "If the condition is True the block runs, then Python checks the condition again. If it is False, the loop stops.",
    ),
    (
        "What happens if the condition is False the first time Python checks it?",
        "The indented block is skipped",
        ["The block runs once, then the loop stops", "Python shows a SyntaxError", "The loop runs forever"],
        "A `while` loop tests the condition first. If it is False right away, the block never runs.",
    ),
    (
        "What is the difference between `if` and `while`?",
        "`while` repeats its block; `if` runs it at most once",
        ["`if` repeats its block; `while` runs it once", "`while` only works with numbers", "There is no difference"],
        "An `if` block runs at most once. A `while` block keeps repeating as long as its condition stays True.",
    ),
    (
        "Which keyword starts a loop that repeats while a condition is True?",
        "`while`",
        ["`if`", "`elif`", "`repeat`", "`else`"],
        "`while condition:` followed by an indented block is a while loop.",
    ),
    (
        "Which of these is a good use of a `while` loop?",
        "Repeating a prompt until the user chooses to stop",
        ["Printing a message exactly one time", "Choosing between two paths", "Storing a value in a variable"],
        "While loops are great for repeated input when you don't know how many rounds you'll need.",
    ),
    (
        "How does a `while` loop decide whether to run its block again?",
        "It checks the condition after every pass",
        ["It counts the lines in the block", "It asks the user each time", "It always repeats the block 5 times"],
        "Before every pass the condition is tested: True means run the block again, False means stop.",
    ),
    (
        "The lesson compares a `while` loop to \"while there are dishes, keep washing.\" What plays the role of \"there are dishes\"?",
        "The condition",
        ["The update", "The initialization", "The `print()` call"],
        "\"There are dishes\" is the test that keeps the loop going, which is the condition.",
    ),
    (
        "Which lines belong to the body of a `while` loop?",
        "The indented lines under the `while` line",
        ["Every line in the file", "Only the `while` line itself", "The lines above the `while` line"],
        "The indented block under `while condition:` is what repeats; unindented lines before or after it are not part of the loop.",
    ),
    (
        "What must the end of a `while` line look like?",
        "A colon `:` after the condition",
        ["A semicolon `;`", "The word `do`", "Nothing, a colon is optional"],
        "Like `if`, a `while` line ends with a colon and is followed by an indented block.",
    ),
    (
        "A `while` loop is a good fit when you...",
        "Want to repeat code until something changes",
        ["Want to run code exactly one time", "Need to choose between two paths", "Need to store one value in a variable"],
        "Decisions let a program pick one path; loops let it repeat actions.",
    ),
    (
        "How do you run the file `loops_p1_lab.py` from the VS Code terminal?",
        "`python3 loops_p1_lab.py`",
        ["`run loops_p1_lab.py`", "`python loops_p1_lab`", "`open loops_p1_lab.py`"],
        "In the terminal, type `python3` followed by the file name: `python3 loops_p1_lab.py`.",
    ),
    (
        "What is the main job of a loop?",
        "To repeat actions",
        ["To pick one path out of two", "To store a value", "To change a value's type"],
        "Decisions let a program pick one path; loops let it repeat actions.",
    ),
]


@generator(TOPIC, EASY)
def gen_how_while_works(rng: random.Random) -> Question:
    """Concept: how a while loop runs (quiz-style one-liners)."""
    return _concept(EASY, rng, _HOW_WHILE_WORKS)


_LOOP_VOCAB = [
    (
        "Which three pieces make the classic counter loop safe and predictable?",
        "Initialization, condition, update",
        ["Start, stop, step", "Input, output, print", "If, elif, else"],
        "Set a starting value (initialization), test it (condition), and change it each time (update).",
    ),
    (
        "What is the job of the update in a `while` loop?",
        "To change a value so the condition can become False",
        ["To set the starting value", "To print the current value", "To start the program over"],
        "Without an update the condition never changes, so the loop never stops.",
    ),
    (
        "What is the job of the initialization in a `while` loop?",
        "To set the starting value before the loop begins",
        ["To change the value on every pass", "To stop the loop early", "To print the result"],
        "The initialization (like `count = 1`) happens once, before the `while` line.",
    ),
    (
        "What does the condition of a `while` loop do?",
        "It is the test that keeps the loop running",
        ["It sets the starting value", "It changes the counter each pass", "It prints the result"],
        "The loop keeps going as long as the condition is True.",
    ),
    (
        "What should you plan first when you write a `while` loop?",
        "How the loop will make progress toward stopping",
        ["The name of the file", "Which message to print", "How many comments to write"],
        "The lesson's habit: plan the update first, so the condition can eventually become False.",
    ),
    (
        "A `while` loop can end in two ways. Which pair is correct?",
        "The condition becomes False, or a `break` runs",
        [
            "The loop runs 10 times, or the user presses Enter",
            "A comment is reached, or the file is saved",
            "The condition becomes True, or `print` runs",
        ],
        "Know your exits: either the condition becomes False or you use `break`.",
    ),
    (
        "Which is the update in `count = 1`, `while count <= 5:`, `count += 1`?",
        "`count += 1`",
        ["`count = 1`", "`while count <= 5:`", "`count <= 5`"],
        "`count += 1` changes the counter each time around, which is what an update does.",
    ),
    (
        "Which is the initialization in `count = 1`, `while count <= 5:`, `count += 1`?",
        "`count = 1`",
        ["`count += 1`", "`while count <= 5:`", "`count <= 5`"],
        "`count = 1` sets the starting value once, before the loop begins.",
    ),
    (
        "Which is the condition in `count = 1`, `while count <= 5:`, `count += 1`?",
        "`count <= 5`",
        ["`count = 1`", "`count += 1`", "`print(count)`"],
        "The condition is the test after `while`; the loop runs as long as it is True.",
    ),
    (
        "The lesson calls `count += 1` an \"update (increment)\". What does an increment do?",
        "Adds to the value",
        ["Subtracts from the value", "Resets the value to 0", "Prints the value"],
        "An increment like `count += 1` raises the value by 1 each time.",
    ),
    (
        "Why should you plan the update first when you write a `while` loop?",
        "So the condition can eventually become False",
        ["So the loop prints faster", "So Python skips the condition", "So the loop runs exactly once"],
        "If nothing in the loop changes, the condition never changes either, and the loop runs forever.",
    ),
    (
        "Your loop behaves strangely. Which habit from the lesson helps you debug it?",
        "Print key values, like the counter, to see what is happening",
        ["Delete the loop and start over", "Add more `break` statements", "Make the counter a string"],
        "Quality check: print key values for quick debugging (for example, the counter) if behavior looks off.",
    ),
    (
        "When does the initialization (like `count = 1`) run?",
        "Once, before the loop starts",
        ["On every pass of the loop", "After the loop ends", "Only when the user types `quit`"],
        "The initialization sets the starting value one time, above the `while` line.",
    ),
]


@generator(TOPIC, EASY)
def gen_loop_vocab(rng: random.Random) -> Question:
    """Concept: initialization / condition / update vocabulary."""
    return _concept(EASY, rng, _LOOP_VOCAB)


@generator(TOPIC, EASY)
def gen_infinite_concept(rng: random.Random) -> Question:
    """Lesson 2) 'What Goes Wrong: Infinite Loops' (the loop with no update)."""
    var = rng.choice(["num", "num", "count", "number"])
    limit = rng.randint(3, 9)
    msg = rng.choice(["Stuck here forever...", "Still going...", "Help!", "Looping..."])
    code = _lines(f"{var} = 1", f"while {var} <= {limit}:", f'    print("{msg}")')
    if not _runs_forever(code):
        raise GenerationError("expected an infinite loop")
    kind = rng.choice(["why", "missing", "what"])
    if kind == "why":
        prompt = "Why does this loop repeat forever?"
        correct = f"`{var}` never changes, so the condition stays True"
        wrong = [
            "`print()` can't be used inside a `while` loop",
            f"`{var}` should start at 0",
            "The condition should use `<` instead of `<=`",
        ]
    elif kind == "missing":
        prompt = "What is missing from this loop?"
        correct = f"An update that changes `{var}`"
        wrong = ["A second `while` line", "A `return` statement", "A `def` line"]
    else:
        prompt = "What happens when you run this code?"
        correct = f'It prints "{msg}" again and again'
        wrong = [f'It prints "{msg}" {limit} times', f'It prints "{msg}" once', "It raises a SyntaxError"]
    return _choice(
        difficulty=EASY,
        prompt=prompt,
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=f"Nothing inside the loop changes `{var}`, so `{var} <= {limit}` is always True. The loop needs an update.",
        rng=rng,
    )


_CTRL_C = [
    (
        "How do you stop a runaway (infinite) loop in the terminal?",
        "Press Control + C",
        ["Press Command + C", "Press Command + S", "Press Enter twice"],
        "Press Ctrl + C in the terminal to stop a runaway loop. On a Mac use Control + C, not Command + C.",
    ),
    (
        "On a Mac, which keys stop a program that is stuck in an infinite loop?",
        "Control + C",
        ["Command + C", "Command + S", "Control + V"],
        "The lesson says: press Ctrl + C in the terminal (Windows and Mac). Not Command + C on a Mac.",
    ),
    (
        "Your program keeps printing forever in the VS Code terminal. What should you do?",
        "Press Ctrl + C in the terminal",
        ["Press Command + C", "Wait; Python stops every loop after a minute", "Press Enter twice"],
        "Ctrl + C interrupts a runaway loop. An infinite loop never finishes on its own.",
    ),
    (
        "Which statement about Ctrl + C is true?",
        "It stops a program that is stuck in a loop",
        ["It saves your file", "It starts the loop over", "It fixes the missing update"],
        "Ctrl + C only stops the runaway program. You still need to fix the code (add the update).",
    ),
    (
        "You are testing a loop and it floods the terminal with \"Stuck here forever...\". What do you do first?",
        "Press Ctrl + C to stop it",
        ["Press Command + C to copy the loop", "Press the Escape key", "Type `quit` and hope it stops"],
        "Safety: if you accidentally create an infinite loop while testing, press Ctrl + C to stop it.",
    ),
    (
        "Where do you press Ctrl + C to stop a runaway loop?",
        "In the terminal where the program is running",
        ["In the Explorer sidebar", "In the Canvas assignment page", "In a new empty file"],
        "The program runs in the VS Code terminal, so that is where Ctrl + C interrupts it.",
    ),
    (
        "Which key does the lesson say to use on a Mac for stopping a runaway loop?",
        "Control, not Command",
        ["Command, not Control", "Option, not Control", "Shift, not Command"],
        "Use Control + C. Command + C is the copy shortcut and does not stop the program.",
    ),
    (
        "After you stop a runaway loop with Ctrl + C, what should you do next?",
        "Fix the code (for example, add the update)",
        ["Run the same code again", "Delete the file", "Change the file name"],
        "Ctrl + C only stops the program. The loop still has a bug that you need to fix.",
    ),
]


@generator(TOPIC, EASY)
def gen_ctrl_c(rng: random.Random) -> Question:
    """Lesson: 'Press Ctrl + C in the terminal to stop a runaway loop'."""
    return _concept(EASY, rng, _CTRL_C)


_BREAK_WORDS = ["stop", "exit", "end", "quit", "halt"]


@generator(TOPIC, EASY)
def gen_break_keyword(rng: random.Random) -> Question:
    """Quiz: 'Which keyword exits a loop early?' / what `break` does."""
    kind = rng.choice(["keyword", "keyword_quiz", "does", "does", "next", "where", "needs_if", "after"])
    if kind == "keyword_quiz":
        return _choice(
            difficulty=EASY,
            prompt="Which keyword exits a loop early?",
            correct="break",
            distractors=["stop", "exit", "return"],
            explanation="`break` jumps out of the current loop immediately.",
            rng=rng,
        )
    if kind == "keyword":
        wrong = rng.sample(_BREAK_WORDS, 3)
        return _choice(
            difficulty=EASY,
            prompt=rng.choice(
                ["Which keyword exits a `while` loop immediately?", "Which keyword jumps out of a loop from the inside?"]
            ),
            correct="break",
            distractors=wrong,
            explanation="`break` exits the current loop immediately.",
            rng=rng,
        )
    if kind == "does":
        return _choice(
            difficulty=EASY,
            prompt="What does `break` do inside a `while` loop?",
            correct="Exits the loop immediately",
            distractors=[
                "Starts the loop over from the first pass",
                "Ends the whole program",
                "Pauses the loop until the user presses a key",
            ],
            explanation="`break` exits the current loop immediately and returns control to the outer (left-aligned) level.",
            rng=rng,
        )
    if kind == "next":
        return _choice(
            difficulty=EASY,
            prompt="After a `break` runs, which code runs next?",
            correct="The first line after the loop",
            distractors=[
                "The first line of the loop body again",
                "The `while` condition, checked once more",
                "Nothing - the program ends",
            ],
            explanation="`break` leaves the loop and control returns to the outer (left-aligned) level, so the code after the loop runs.",
            rng=rng,
        )
    if kind == "needs_if":
        return _choice(
            difficulty=EASY,
            prompt="Why is a `break` usually written inside an `if`?",
            correct="So the loop only ends when the stop condition is met",
            distractors=[
                "Because `break` only works with numbers",
                "So the loop runs faster",
                "Because `break` needs a colon after it",
            ],
            explanation="Without an `if`, `break` would end the loop on the very first pass. The `if` makes it happen only at the right moment.",
            rng=rng,
        )
    if kind == "after":
        return _choice(
            difficulty=EASY,
            prompt="A loop ends because of a `break`. Which statement is true?",
            correct="The program continues with the code after the loop",
            distractors=[
                "The program stops completely",
                "The loop starts again from the top",
                "Python asks the user whether to keep going",
            ],
            explanation="`break` exits the current loop immediately and returns control to the outer (left-aligned) level.",
            rng=rng,
        )
    return _choice(
        difficulty=EASY,
        prompt="Where does `break` send control?",
        correct="Out of the loop, to the code after it",
        distractors=["Back to the top of the loop", "To the end of the program", "To the `else:` block"],
        explanation="`break` exits the current loop immediately; the program continues after the loop.",
        rng=rng,
    )


_WHILE_TRUE = [
    (
        "If you need repeated user input until they choose to stop, a common pattern is...",
        "`while True:` with a `break` condition",
        ["`for i in range(1):`", "`if True:`", "`range(input())`"],
        "`while True:` loops \"forever\", and a `break` inside decides when to stop.",
    ),
    (
        "Which pattern keeps asking the user for input until they type `quit`?",
        "`while True:` with `break` when the text is \"quit\"",
        ["`if text == \"quit\":` alone", "`for text in \"quit\":`", "`range(quit)`"],
        "Loop with `while True:` and use `break` when the user types the stop word.",
    ),
    (
        "What does `while True:` mean?",
        "The loop runs until a `break` stops it",
        ["The loop runs exactly once", "Python checks if the user typed True", "It is a syntax error"],
        "The condition `True` is always True, so only a `break` (or Ctrl + C) ends the loop.",
    ),
    (
        "Why use `while True:` with `break`?",
        "You don't know how many rounds you'll need",
        ["It makes the loop run faster", "It stops you from needing a condition", "It prevents infinite loops"],
        "It is great for repeated input (menus, calculators, quizzes) when the number of rounds is unknown.",
    ),
    (
        "What is the condition in `while True:`?",
        "`True`, which is always true",
        ["`while`, which is the loop keyword", "The text the user types", "There is no condition"],
        "`while True:` has the condition `True`, so the loop only ends with `break`.",
    ),
    (
        "Which programs are a good fit for `while True:` with `break`?",
        "Menus and quizzes that repeat until the user quits",
        ["Programs that print one line", "Programs that never ask for input", "Programs with no loops at all"],
        "Use it for repeated input when you don't know how many rounds you'll need.",
    ),
    (
        "What does the lesson call a loop made with `while True:` and a `break`?",
        "A controlled infinite loop",
        ["A countdown loop", "A syntax error", "A broken loop"],
        "It would run forever, but you decide inside the loop when to stop with `break`.",
    ),
    (
        "A `while True:` loop has no `break` inside. What happens when you run it?",
        "It runs forever until you press Ctrl + C",
        ["It runs once and stops", "Python refuses to run it", "It stops after 10 passes"],
        "Nothing makes `True` False, and there is no `break`, so you must stop it with Ctrl + C.",
    ),
    (
        "In `while True:` with `break`, where does the `break` usually go?",
        "Inside an `if` that checks for the stop word",
        ["On the same line as `while`", "Before the `while` line", "At the very end of the file"],
        "A `break` inside an `if` ends the loop only when the stop condition is met.",
    ),
]


@generator(TOPIC, EASY)
def gen_while_true_pattern(rng: random.Random) -> Question:
    """Quiz: the `while True` + `break` pattern."""
    return _concept(EASY, rng, _WHILE_TRUE)


@generator(TOPIC, EASY)
def gen_last_line(rng: random.Random) -> Question:
    """Lesson 1) counter: <= vs <, last value printed / how many lines."""
    var = _var(rng)
    label = _LABELS[var]
    start = rng.choice([1, 1, 2, 3])
    limit = start + rng.randint(3, 8)
    op = rng.choice(["<=", "<=", "<"])
    code = _lines(f"{var} = {start}", f"while {var} {op} {limit}:", f'    print("{label}", {var})', f"    {var} += 1")
    shown = _must_run(code).split("\n")
    last_value = int(shown[-1].split()[-1])
    if rng.random() < 0.55:
        prompt = "What is the last line this loop prints?"
        correct = f"{label} {last_value}"
        wrong = [f"{label} {v}" for v in (last_value + 1, last_value - 1, limit, limit + 1, last_value + 2, last_value - 2, start)]
        why = (
            f"`{var} <= {limit}` is still True when {var} is {limit}, so {limit} is printed."
            if op == "<="
            else f"`{var} < {limit}` becomes False as soon as {var} reaches {limit}, so the last line is {limit - 1}."
        )
    else:
        prompt = "How many lines does this loop print?"
        correct = str(len(shown))
        wrong = [str(v) for v in (len(shown) + 1, len(shown) - 1, limit, limit - start, limit + 1, len(shown) + 2, len(shown) - 2)]
        why = f"It prints once for each value of {var} from {start} to {last_value}, which is {len(shown)} lines."
    return _choice(
        difficulty=EASY,
        prompt=prompt,
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=why + " Watch `<=` versus `<`.",
        rng=rng,
    )


@generator(TOPIC, EASY)
def gen_output_counter(rng: random.Random) -> Question:
    """Lesson 1) 'Count is:' -- trace a tiny counter loop."""
    var = _var(rng)
    label = _LABELS[var]
    start = rng.choice([1, 1, 1, 2])
    n_lines = rng.randint(3, 4)
    op = rng.choice(["<=", "<=", "<"])
    limit = start + n_lines - 1 if op == "<=" else start + n_lines
    body = f'print("{label}", {var})' if rng.random() < 0.7 else f"print({var})"
    code = _lines(f"{var} = {start}", f"while {var} {op} {limit}:", f"    {body}", f"    {var} += 1")
    shown = _must_run(code).split("\n")
    nxt = start + n_lines
    more = shown + [shown[-1].rsplit(" ", 1)[0] + f" {nxt}" if " " in shown[-1] else str(nxt)]
    return _trace(
        EASY,
        code,
        rng,
        f"The loop runs while `{var} {op} {limit}`, printing and then adding 1 each time. It prints {n_lines} lines.",
        mutations=[
            ("<=", "<"),
            ("< ", "<= "),
            (f"{var} = {start}\n", f"{var} = {start + 1}\n"),
            ("+= 1", "+= 2"),
        ],
        extras=["\n".join(more), "\n".join(shown[1:]), NOTHING_PRINTED],
    )


@generator(TOPIC, EASY)
def gen_loop_skipped(rng: random.Random) -> Question:
    """A condition that is False the very first time: the body never runs."""
    var = _var(rng)
    label = _LABELS[var]
    start = rng.randint(6, 12)
    limit = rng.randint(2, 5)
    op = rng.choice(["<", "<="])
    end = rng.choice(["Done", "Loop ended.", "Finished"])
    code = _lines(
        f"{var} = {start}",
        f"while {var} {op} {limit}:",
        f'    print("{label}", {var})',
        f"    {var} += 1",
        f'print("{end}")',
    )
    return _trace(
        EASY,
        code,
        rng,
        f"{var} starts at {start}, so `{var} {op} {limit}` is False the first time Python checks it. The loop body is skipped and only the last line runs.",
        mutations=[(f"{var} = {start}\n", f"{var} = 1\n")],
        extras=[f"{label} {start}\n{end}", LOOPING, f"{label} {start}"],
    )


@generator(TOPIC, EASY)
def gen_countdown_header(rng: random.Random) -> Question:
    """Which `while` condition makes a countdown print n..1 and stop."""
    var = _var(rng)
    start = rng.randint(3, 6)
    template = _lines(f"{var} = {start}", "while {cond}:", f"    print({var})", f"    {var} -= 1")
    target = "\n".join(str(i) for i in range(start, 0, -1))
    correct = rng.choice([f"{var} > 0", f"{var} >= 1"])
    if _sim(template.format(cond=correct))[0:2] != (target, None):
        raise GenerationError("countdown header is wrong")
    cands = [
        f"{var} >= 0",
        f"{var} > 1",
        f"{var} < {start}",
        f"{var} <= {start}",
        f"{var} != 1",
        f"{var} == 0",
    ]
    wrong = [c for c in cands if _sim(template.format(cond=c))[0:2] != (target, None)]
    head, tail = wrong[:2], wrong[2:]
    rng.shuffle(tail)
    nums = ", ".join(str(i) for i in range(start, 0, -1))
    return _choice(
        difficulty=EASY,
        prompt=f"Which condition makes the loop print {nums} and then stop?",
        code=template.format(cond=BLANK),
        correct=correct,
        distractors=head + tail,
        explanation=f"The loop must keep going while {var} is still 1 or more, so use `{correct}`. A condition like `{var} >= 0` would print 0 as well.",
        rng=rng,
    )


_HEADER_KINDS = [
    # (what the loop should do, comparison, value is the same as n?, explanation)
    ("`{var}` is at most {n}", "<=", "{n}", "\"At most\" means less than or equal to, so use `<=`."),
    ("`{var}` is less than {n}", "<", "{n}", "\"Less than\" does not include {n} itself, so use `<`."),
    ("`{var}` is still above 0", ">", "0", "\"Above 0\" means greater than 0, so use `>`."),
    ("`{var}` is at least 1", ">=", "1", "\"At least 1\" means greater than or equal to 1, so use `>=`."),
    ("`{var}` is not {n} yet", "!=", "{n}", "\"Not equal\" is written `!=`."),
]
_HEADER_FLIPS = {"<=": ["<", ">="], "<": ["<=", ">"], ">": [">=", "<"], ">=": [">", "<="], "!=": ["==", "<"]}


@generator(TOPIC, EASY)
def gen_valid_header(rng: random.Random) -> Question:
    """Which `while` line is written correctly (colon, `==` vs `=`) AND does what is asked."""
    var = _var(rng)
    n = rng.randint(3, 9)
    want, op, value, why = rng.choice(_HEADER_KINDS)
    value = value.format(n=n)
    good = f"while {var} {op} {value}:"
    compile(good + "\n    pass", "<h>", "exec")  # the correct line must be valid Python
    syntax_bad = [
        f"while {var} {op} {value}",
        f"while {var} = {value}:",
        f"while {var} {op} {value};",
        f"while: {var} {op} {value}",
        f"while {var} {op} {value} then:",
    ]
    ok_syntax = []
    for line in syntax_bad:
        try:
            compile(line + "\n    pass", "<h>", "exec")
        except SyntaxError:
            ok_syntax.append(line)
    if len(ok_syntax) < 3:
        raise GenerationError("expected syntax errors")
    rng.shuffle(ok_syntax)
    flip = f"while {var} {rng.choice(_HEADER_FLIPS[op])} {value}:"
    return _choice(
        difficulty=EASY,
        prompt=f"Which line starts a `while` loop that keeps going while {want.format(var=var, n=n)}?",
        correct=good,
        distractors=[flip, *ok_syntax[:2]],
        explanation=f"A `while` line is the word `while`, the condition, and a colon. {why}",
        rng=rng,
    )


# ==========================================================================
# MEDIUM -- choice (trace a lab-style snippet, pick the code, spot the classic mistake)
# ==========================================================================


def _swap(a: str, b: str) -> tuple[str, str]:
    """A mutation that swaps two consecutive lines."""
    return (f"{a}\n{b}", f"{b}\n{a}")


@generator(TOPIC, MEDIUM)
def gen_final_value(rng: random.Random) -> Question:
    """What is the counter's value once the loop is over? (6, not 5)"""
    var = _var(rng)
    kind = rng.choice(["up", "up", "step", "down"])
    if kind == "up":
        start, step = 1, 1
        limit = rng.randint(3, 9)
        code = _lines(f"{var} = {start}", f"while {var} <= {limit}:", f"    {var} += 1", f"print({var})")
        why = f"The loop stops only when `{var} <= {limit}` is False. {var} reaches {limit}, the loop adds 1 once more, and then the test fails."
    elif kind == "step":
        start, step = rng.choice([1, 2]), rng.choice([2, 3, 4])
        limit = rng.randint(8, 15)
        code = _lines(f"{var} = {start}", f"while {var} < {limit}:", f"    {var} += {step}", f"print({var})")
        why = f"{var} jumps by {step} each time and the loop stops as soon as `{var} < {limit}` is False, so {var} can end up past {limit}."
    else:
        start, step = rng.randint(3, 8), -1
        limit = 0
        code = _lines(f"{var} = {start}", f"while {var} > 0:", f"    {var} -= 1", f"print({var})")
        why = f"The loop keeps subtracting while `{var} > 0`. It stops when {var} reaches 0, so 0 is printed."
    correct = int(_must_run(code))
    wrong = [limit, limit - 1, limit + 1, start, correct + 1, correct - 1, correct + step, correct - step]
    wrong = [str(w) for w in wrong if w != correct]
    return _trace(
        MEDIUM,
        code,
        rng,
        why,
        extras=wrong,
        prompt=rng.choice(["What does this code print?", "What is printed after the loop finishes?"]),
    )


@generator(TOPIC, MEDIUM)
def gen_accumulator_trace(rng: random.Random) -> Question:
    """A running total built with `total += count` inside a while loop."""
    n = rng.randint(3, 6)
    step = rng.choice([1, 1, 2])
    show = rng.choice(['print("Total:", total)', "print(total)"])
    code = _lines("total = 0", "count = 1", f"while count <= {n}:", "    total += count", f"    count += {step}", show)
    mutations = [
        ("<=", "<"),
        ("total = 0", "total = 1"),
        ("total += count", "total += 1"),
        ("count = 1", "count = 0"),
        (f"count += {step}", "count += 1") if step != 1 else ("total += count", "count += 1"),
    ]
    values = list(range(1, n + 1, step))

    def fmt(v):
        return f"Total: {v}" if "Total" in show else str(v)

    return _trace(
        MEDIUM,
        code,
        rng,
        f"`total` starts at 0 and adds `count` on each pass, with count taking the values {', '.join(map(str, values))}.",
        mutations=mutations,
        extras=[fmt(sum(values) + 1), fmt(sum(values) + n), fmt(sum(range(1, n + 1)) + n + 1)],
    )


@generator(TOPIC, MEDIUM)
def gen_step_trace(rng: random.Random) -> Question:
    """Counting by 2s / 3s / 5s with `+=` (the update can be any step)."""
    var = _var(rng)
    step = rng.choice([2, 3, 5, 10])
    start = rng.choice([step, step, 1, 0] if step == 2 else [step, step, 0])
    prints = rng.randint(3, 5)
    last = start + step * (prints - 1)
    limit = last + (0 if rng.random() < 0.5 else rng.randint(1, step - 1))
    code = _lines(f"{var} = {start}", f"while {var} <= {limit}:", f"    print({var})", f"    {var} += {step}")
    shown = _must_run(code).split("\n")
    more = "\n".join(shown + [str(int(shown[-1]) + step)])
    return _trace(
        MEDIUM,
        code,
        rng,
        f"{var} goes up by {step} each pass: {', '.join(shown)}. The next value, {last + step}, is bigger than {limit}, so the loop stops.",
        mutations=[("<=", "<"), (f"+= {step}", "+= 1"), (f"{var} = {start}\n", f"{var} = {start + 1}\n")],
        extras=[more, "\n".join(shown[:-1])],
    )


@generator(TOPIC, MEDIUM)
def gen_blastoff_trace(rng: random.Random) -> Question:
    """Mini-Challenge Countdown: trace the countdown, print-then-update or update-then-print."""
    var = _var(rng)
    start = rng.randint(3, 5)
    finale = rng.choice(_FINALES)
    cond = rng.choice([f"{var} > 0", f"{var} >= 1"])
    print_first = rng.random() < 0.65

    def build(first_print=print_first, c=cond, indent_finale=False):
        a, b = f"    print({var})", f"    {var} -= 1"
        body = [a, b] if first_print else [b, a]
        tail = f'    print("{finale}")' if indent_finale else f'print("{finale}")'
        return _lines(f"{var} = {start}", f"while {c}:", *body, tail)

    code = build()
    shown = _must_run(code).split("\n")
    wrong_codes = [build(first_print=not print_first), build(c=f"{var} >= 0" if "> 0" in cond else f"{var} > 0")]
    extras = [_sim(w)[0] for w in wrong_codes] + [_sim(build(c=f"{var} > 1"))[0], _sim(build(indent_finale=True))[0]]
    extras += ["\n".join(shown[:-1]), "\n".join([finale, *shown[:-1]]), "\n".join(shown[:-2] + [finale])]
    if print_first:
        why = f"It prints {var}, then subtracts 1, and repeats while {var} is still 1 or more. When the loop is over, \"{finale}\" prints once."
    else:
        why = f"The update comes before the print, so each pass prints the already-smaller value (the loop ends after printing 0). \"{finale}\" prints once at the end."
    return _trace(MEDIUM, code, rng, why, extras=extras)


@generator(TOPIC, MEDIUM)
def gen_blastoff_indent(rng: random.Random) -> Question:
    """Common mistake: the final message is indented, so it is inside the loop."""
    var = _var(rng)
    start = rng.randint(2, 3)
    finale = rng.choice(_FINALES)
    good = _lines(f"{var} = {start}", f"while {var} > 0:", f"    print({var})", f"    {var} -= 1", f'print("{finale}")')
    bad = good.replace(f'\nprint("{finale}")', f'\n    print("{finale}")')
    if rng.random() < 0.5:
        return _trace(
            MEDIUM,
            bad,
            rng,
            f'`print("{finale}")` is indented, so it is part of the loop body and prints on every pass, not just at the end.',
            extras=[_sim(good)[0], "\n".join(str(i) for i in range(start, 0, -1)), f"{finale}\n" + _sim(good)[0].replace(f"\n{finale}", "")],
        )
    return _choice(
        difficulty=MEDIUM,
        prompt=f"This countdown should print `{finale}` only once, at the end. What is wrong?",
        code=bad,
        correct=f'`print("{finale}")` is indented, so it is inside the loop',
        distractors=[
            f"`{var} -= 1` should be `{var} += 1`",
            f"The condition should be `{var} >= 0`",
            f"`print({var})` must come after the update",
        ],
        explanation=f'Un-indent `print("{finale}")` so it is not part of the loop body. Then it runs once, after the loop ends.',
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_break_trace(rng: random.Random) -> Question:
    """`while True` with a counter and `break`: where the check sits matters."""
    label = rng.choice(["Pass", "Round", "Lap"])
    limit = rng.randint(2, 4)
    check_last = rng.random() < 0.6

    def build(n=limit, last=check_last):
        body = ["    count += 1", f'    print("{label}", count)']
        check = [f"    if count == {n}:", "        break"]
        parts = body + check if last else [body[0]] + check + [body[1]]
        return _lines("count = 0", "while True:", *parts, 'print("Done")')

    code = build()
    extras = [_sim(build(last=not check_last))[0], _sim(build(n=limit + 1))[0], _sim(build(n=limit - 1))[0], LOOPING]
    if check_last:
        why = f"Each pass adds 1, prints, and then checks. When count reaches {limit} it prints that pass and then `break` leaves the loop."
    else:
        why = f"The check comes before the print. When count reaches {limit}, `break` runs first, so that pass is never printed."
    return _trace(MEDIUM, code, rng, why, extras=extras)


def _quit_code(word: str, mode: str) -> str:
    prompt = f"Type '{word}' to stop: "
    head = ["while True:", f'    text = input("{prompt}")']
    if mode == "plain":
        mid = [f'    if text == "{word}":', "        break"]
    elif mode == "echo_after":
        mid = [f'    if text == "{word}":', "        break", '    print("You typed:", text)']
    else:  # echo_before
        mid = ['    print("You typed:", text)', f'    if text == "{word}":', "        break"]
    return _lines(*head, *mid, 'print("Loop ended.")')


@generator(TOPIC, MEDIUM)
def gen_quit_trace(rng: random.Random) -> Question:
    """Lesson 3) the quit loop, traced with scripted typing."""
    word = rng.choice(_QUIT_WORDS)
    pool = ["hi", "ok", "yes", "go", "python", "cat", "hello", "maybe"]
    typed = rng.sample(pool, rng.randint(1, 3)) + [word]
    mode = rng.choice(["plain", "echo_after", "echo_before"])
    code = _quit_code(word, mode)
    prompt = f"The player types {_typed(typed)}. What does the program print?"
    outs = {m: _sim(_quit_code(word, m), typed)[0] for m in ("plain", "echo_after", "echo_before")}
    extras = [o for m, o in outs.items() if m != mode]
    extras.append("\n".join(f"You typed: {t}" for t in typed))
    why = {
        "plain": f"The loop never prints what was typed, it only waits for `{word}`. After the `break`, only \"Loop ended.\" prints.",
        "echo_after": f"Every word before `{word}` is printed. When `{word}` is typed, `break` runs before the `print`, so it is not shown.",
        "echo_before": f"The `print` comes before the check, so `You typed: {word}` is shown too, and then `break` ends the loop.",
    }[mode]
    return _trace(MEDIUM, code, rng, why, stdin=typed, prompt=prompt, extras=extras)


@generator(TOPIC, MEDIUM)
def gen_quit_count_inputs(rng: random.Random) -> Question:
    """How many times does the quit loop ask? (the quit word counts too)"""
    word = rng.choice(_QUIT_WORDS)
    pool = ["hi", "ok", "yes", "go", "python", "cat", "hello", "maybe"]
    typed = rng.sample(pool, rng.randint(1, 4)) + [word]
    code = _quit_code(word, "plain")
    # count the calls to input() by running the loop on the script
    n = len(typed)
    return _choice(
        difficulty=MEDIUM,
        prompt=f"The player types {_typed(typed)}. How many times does the program run `input()`?",
        code=code,
        correct=str(n),
        distractors=[str(n - 1), str(n + 1), "1", str(n + 2), "0"],
        explanation=f"It asks again after every word. The last answer, `{word}`, is also read by `input()`, and then `break` ends the loop. That is {n} times.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_password_trace(rng: random.Random) -> Question:
    """Bingo: keep asking for a password until it is correct."""
    secret = rng.choice(_SECRETS)
    wrong_pool = ["cat", "123", "abc", "hello", secret.upper(), secret[:-1], "password"]
    k = rng.choice([0, 1, 2, 2, 3])
    guesses = rng.sample(wrong_pool, k) + [secret]
    code = _lines(
        f'password = "{secret}"',
        'guess = input("Password: ")',
        "while guess != password:",
        '    print("Wrong, try again.")',
        '    guess = input("Password: ")',
        'print("Welcome!")',
    )

    def out(m):
        return "\n".join(["Wrong, try again."] * m + ["Welcome!"])

    extras = [out(m) for m in (k + 1, k - 1, 0, 1, 2) if m >= 0] + ["\n".join(["Wrong, try again."] * k)]
    return _trace(
        MEDIUM,
        code,
        rng,
        f"Each wrong guess prints \"Wrong, try again.\" and asks again. The loop ends when the guess equals `{secret}`, then \"Welcome!\" prints. Wrong guesses here: {k}." + (f" (`{secret.upper()}` is not the same as `{secret}`: capital letters count.)" if secret.upper() in guesses else ""),
        stdin=guesses,
        prompt=f"The player types {_typed(guesses)}. What does the program print?",
        extras=extras,
    )


@generator(TOPIC, MEDIUM)
def gen_fix_infinite(rng: random.Random) -> Question:
    """Which line, added inside the loop, fixes the infinite loop? (verified by running each)"""
    var = rng.choice(["num", "count", "number"])
    if rng.random() < 0.6:
        limit = rng.randint(3, 9)
        head = _lines(f"{var} = 1", f"while {var} <= {limit}:", '    print("Stuck here forever...")')
        correct = f"{var} += 1"
        cands = [f"{var} -= 1", f"{var} = 1", f"{var} == {var} + 1", f"print({var})", f"{var} + 1"]
    else:
        start = rng.randint(3, 9)
        head = _lines(f"{var} = {start}", f"while {var} > 0:", f"    print({var})")
        correct = f"{var} -= 1"
        cands = [f"{var} += 1", f"{var} = {start}", f"{var} - 1", f"{var} == {var} - 1", f"print({var})"]
    if _runs_forever(head) is False:
        raise GenerationError("head should be infinite")
    if _sim(head + f"\n    {correct}")[1] is not None:
        raise GenerationError("fix does not fix")
    wrong = [c for c in cands if _sim(head + f"\n    {c}")[1] == "LOOP"]
    rng.shuffle(wrong)
    return _choice(
        difficulty=MEDIUM,
        prompt="Which line, added inside the loop, stops it from running forever?",
        code=head,
        correct=correct,
        distractors=wrong,
        explanation=f"The loop needs an update that moves `{var}` toward making the condition False. `{correct}` does that; the other lines leave the loop running forever.",
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_spot_mistake(rng: random.Random) -> Question:
    """'What is wrong with this loop?' -- the classic while-loop mistakes."""
    var = rng.choice(["count", "count", "num", "number"])
    label = _LABELS[var]
    limit = rng.randint(3, 8)
    kind = rng.choice(["unindented", "reset", "direction", "colon"])
    if kind == "unindented":
        code = _lines(f"{var} = 1", f"while {var} <= {limit}:", f'    print("{label}", {var})', f"{var} += 1")
        expect = "LOOP"
        correct = f"`{var} += 1` is not indented, so it is not part of the loop"
        wrong = [f"The condition should be `{var} < {limit}`", "`print` can't be used inside a loop", f"`{var}` has to start at 0"]
        why = f"The update must be indented under `while`. Here it runs only after the loop, which never ends because `{var}` never changes."
    elif kind == "reset":
        code = _lines(
            f"{var} = 1",
            f"while {var} <= {limit}:",
            f"    {var} = 1",
            f'    print("{label}", {var})',
            f"    {var} += 1",
        )
        expect = "LOOP"
        correct = f"`{var} = 1` inside the loop resets the counter every pass"
        wrong = [f"`{var} += 1` should be `{var} + 1`", "`while` lines need parentheses", f"The condition should be `{var} < {limit}`"]
        why = f"Initialization belongs before the loop. Setting `{var} = 1` inside it undoes the update each time, so the condition never becomes False."
    elif kind == "direction":
        start = rng.randint(3, 6)
        code = _lines(f"{var} = {start}", f"while {var} > 0:", f"    print({var})", f"    {var} += 1")
        expect = "LOOP"
        correct = f"{var} counts up, so `{var} > 0` is always True"
        wrong = [f"{var} has to start at 0", f"`print({var})` changes {var}", "`while` can't use `>`"]
        why = f"A countdown needs `{var} -= 1`. With `+= 1` the value moves away from 0 and the condition never becomes False."
    else:
        # the broken line can't be shown as a code block (it must compile), so it goes in the prompt
        bad = f"while {var} <= {limit}"
        if _sim(_lines(bad, "    pass"))[1] != "SyntaxError":
            raise GenerationError("expected a SyntaxError")
        return _choice(
            difficulty=MEDIUM,
            prompt=f"Python reports a SyntaxError for the line `{bad}`. What is missing?",
            correct="A colon `:` at the end of the line",
            distractors=["A semicolon `;` at the end", "The word `do` after the condition", f"Parentheses around `{var} <= {limit}`"],
            explanation="Every `while` line must end with a colon `:` before the indented block (the same goes for `if`, `elif` and `else`).",
            rng=rng,
        )
    if _sim(code)[1] != expect:
        raise GenerationError(f"{kind}: expected {expect}")
    return _choice(
        difficulty=MEDIUM,
        prompt=rng.choice(["What is wrong with this loop?", "This loop has a bug. What is it?"]),
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


def _counter_loop(var: str, start: int, cond: str, upd: str | None) -> str:
    parts = [f"{var} = {start}", f"while {cond}:", f"    print({var})"]
    if upd:
        parts.append(f"    {upd}")
    return _lines(*parts)


@generator(TOPIC, MEDIUM)
def gen_which_loop_prints(rng: random.Random) -> Question:
    """Which code prints 1, 2, 3, 4, 5? (each choice is a whole loop, checked by running it)"""
    var = _var(rng)
    kind = rng.choice(["up", "down", "evens"])
    if kind == "up":
        n = rng.randint(4, 6)
        good = _counter_loop(var, 1, f"{var} <= {n}", f"{var} += 1")
        bad = [
            _counter_loop(var, 0, f"{var} <= {n}", f"{var} += 1"),
            _counter_loop(var, 1, f"{var} < {n}", f"{var} += 1"),
            _counter_loop(var, 1, f"{var} <= {n}", None),
            _counter_loop(var, 1, f"{var} <= {n}", f"{var} -= 1"),
            _counter_loop(var, 2, f"{var} <= {n}", f"{var} += 1"),
            _counter_loop(var, 1, f"{var} <= {n}", f"{var} += 2"),
        ]
        target = list(range(1, n + 1))
        why = f"Start at 1, keep going while `{var} <= {n}`, and add 1 each time."
    elif kind == "down":
        n = rng.randint(4, 6)
        good = _counter_loop(var, n, f"{var} > 0", f"{var} -= 1")
        bad = [
            _counter_loop(var, n, f"{var} >= 0", f"{var} -= 1"),
            _counter_loop(var, n, f"{var} > 1", f"{var} -= 1"),
            _counter_loop(var, n, f"{var} > 0", f"{var} += 1"),
            _counter_loop(var, n, f"{var} > 0", None),
            _counter_loop(var, n - 1, f"{var} > 0", f"{var} -= 1"),
        ]
        target = list(range(n, 0, -1))
        why = f"Start at {n}, keep going while `{var} > 0`, and subtract 1 each time."
    else:
        k = rng.randint(3, 5)
        n = 2 * k
        good = _counter_loop(var, 2, f"{var} <= {n}", f"{var} += 2")
        bad = [
            _counter_loop(var, 0, f"{var} <= {n}", f"{var} += 2"),
            _counter_loop(var, 2, f"{var} < {n}", f"{var} += 2"),
            _counter_loop(var, 1, f"{var} <= {n}", f"{var} += 2"),
            _counter_loop(var, 2, f"{var} <= {n}", f"{var} += 1"),
            _counter_loop(var, 2, f"{var} <= {n}", None),
        ]
        target = list(range(2, n + 1, 2))
        why = f"Start at 2, keep going while `{var} <= {n}`, and add 2 each time."
    want = "\n".join(map(str, target))
    if _sim(good)[:2] != (want, None):
        raise GenerationError("good loop does not print the target")
    wrong = [b for b in bad if _sim(b)[:2] != (want, None)]
    head, tail = wrong[:2], wrong[2:]
    rng.shuffle(tail)
    return _choice(
        difficulty=MEDIUM,
        prompt=f"Which loop prints {', '.join(map(str, target))} and then stops?",
        correct=good,
        distractors=head + tail,
        explanation=why,
        rng=rng,
    )


@generator(TOPIC, MEDIUM)
def gen_update_position(rng: random.Random) -> Question:
    """Update before or after the print changes what you see."""
    var = _var(rng)
    label = _LABELS[var]
    n = rng.randint(3, 4)
    update_first = rng.random() < 0.5
    op = rng.choice(["<", "<="])
    start = 0 if op == "<" else rng.choice([0, 1])
    show, upd = f'    print("{label}", {var})', f"    {var} += 1"
    body = [upd, show] if update_first else [show, upd]
    code = _lines(f"{var} = {start}", f"while {var} {op} {n}:", *body)
    other = _lines(f"{var} = {start}", f"while {var} {op} {n}:", *body[::-1])
    flip = _lines(f"{var} = {start}", f"while {var} {'<=' if op == '<' else '<'} {n}:", *body)
    if update_first:
        why = f"The update comes first, so each pass prints the value after adding 1. The first line printed is {label} {start + 1}."
    else:
        why = f"The print comes first, so each pass shows the value before it is updated. The first line printed is {label} {start}."
    return _trace(MEDIUM, code, rng, why, extras=[_sim(other)[0], _sim(flip)[0]], mutations=[(f"{var} = {start}\n", f"{var} = {start + 1}\n")])


@generator(TOPIC, MEDIUM)
def gen_countdown_cast(rng: random.Random) -> Question:
    """Mini-Challenge Countdown: `input()` gives a string, so the first line needs `int()`."""
    var = rng.choice(["start", "num", "count", "number"])
    finale = rng.choice(_FINALES)
    typed = rng.randint(3, 6)
    ask = 'input("Start at: ")'
    rest = [f"while {var} >= 1:", f"    print({var})", f"    {var} -= 1", f'print("{finale}")']
    broken = _lines(f"{var} = {ask}", *rest)
    fixed = f"{var} = int({ask})"
    want = _must_run(_lines(fixed, *rest), [str(typed)])
    if _sim(broken, [str(typed)])[1] != "TypeError":
        raise GenerationError("expected a TypeError")
    cands = [
        f"{var} = str({ask})",
        f"{var} = {ask} + 0",
        f"{var} = print({ask})",
        f"{var} = input(int(\"Start at: \"))",
        f"{var} = {ask}.int()",
    ]
    wrong = [c for c in cands if _sim(_lines(c, *rest), [str(typed)])[:2] != (want, None)]
    rng.shuffle(wrong)
    return _choice(
        difficulty=MEDIUM,
        prompt=f"The player types `{typed}`, but this Countdown program crashes with a TypeError. Which version of the first line fixes it?",
        code=broken,
        correct=fixed,
        distractors=wrong,
        explanation=f"`input()` always gives a string, and a string can't be compared with the number 1. Cast it with `int()`: `{fixed}`.",
        rng=rng,
    )


def _finite_loop(rng: random.Random, var: str, used: set) -> str:
    """A small loop that DOES end (for 'which loop never ends' choices)."""
    for _ in range(20):
        kind = rng.choice(["up", "down", "step", "break"])
        n = rng.randint(3, 9)
        if kind == "up":
            code = _lines(f"{var} = 1", f"while {var} <= {n}:", f"    print({var})", f"    {var} += 1")
        elif kind == "down":
            code = _lines(f"{var} = {n}", f"while {var} > 0:", f"    print({var})", f"    {var} -= 1")
        elif kind == "step":
            code = _lines(f"{var} = 0", f"while {var} < {n * 2}:", f"    print({var})", f"    {var} += 2")
        else:
            code = _lines(f"{var} = 0", "while True:", f"    {var} += 1", f"    if {var} == {n}:", "        break")
        if kind not in used:
            used.add(kind)
            if _sim(code)[1] is not None:
                raise GenerationError("expected a loop that ends")
            return code
    raise GenerationError("no finite loop")


@generator(TOPIC, MEDIUM)
def gen_which_runs_forever(rng: random.Random) -> Question:
    """Concept check: out of four loops, which one never ends (and why)."""
    var = rng.choice(["count", "count", "num", "number"])
    n = rng.randint(3, 8)
    kind = rng.choice(["no_update", "unindented", "wrong_way", "true_no_break", "jumps_over"])
    if kind == "no_update":
        bad = _lines(f"{var} = 1", f"while {var} <= {n}:", f"    print({var})")
        why = f"Nothing inside the loop changes `{var}`, so `{var} <= {n}` stays True forever."
    elif kind == "unindented":
        bad = _lines(f"{var} = 1", f"while {var} <= {n}:", f"    print({var})", f"{var} += 1")
        why = f"`{var} += 1` is not indented, so it is not in the loop body. `{var}` never changes while the loop runs."
    elif kind == "wrong_way":
        bad = _lines(f"{var} = {n}", f"while {var} > 0:", f"    print({var})", f"    {var} += 1")
        why = f"{var} counts up, away from 0, so `{var} > 0` never becomes False."
    elif kind == "true_no_break":
        bad = _lines("while True:", f"    {var} = {n}", f"    print({var})")
        why = "`while True:` never becomes False and there is no `break`, so only Ctrl + C can stop it."
    else:
        bad = _lines(f"{var} = 1", f"while {var} != {2 * n}:", f"    print({var})", f"    {var} += 2")
        why = f"{var} is odd (1, 3, 5, ...) and jumps over {2 * n}, so `{var} != {2 * n}` is always True."
    if not _runs_forever(bad):
        raise GenerationError("expected an infinite loop")
    used: set[str] = set()
    others = [_finite_loop(rng, var, used) for _ in range(3)]
    return _choice(
        difficulty=MEDIUM,
        prompt=rng.choice(["Which of these loops never ends?", "Only one of these loops runs forever. Which one?"]),
        correct=bad,
        distractors=others,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# HARD -- choice (a twist or two steps to trace, still only lesson ideas)
# ==========================================================================


@generator(TOPIC, HARD)
def gen_total_threshold(rng: random.Random) -> Question:
    """The loop stops because of the *total*, not the counter."""
    goal = rng.choice([8, 10, 12, 15, 20])
    first = rng.choice([1, 1, 2])
    code = _lines(
        "total = 0",
        f"count = {first}",
        f"while total < {goal}:",
        "    total += count",
        "    count += 1",
        "print(count, total)",
    )
    out = _must_run(code)
    c, t = (int(x) for x in out.split())
    return _trace(
        HARD,
        code,
        rng,
        f"The condition tests `total`, so the loop stops as soon as total reaches {goal} or more. By then count has already been increased once past the last number added.",
        mutations=[("total < ", "total <= "), ("    total += count\n    count += 1", "    count += 1\n    total += count")],
        extras=[f"{c - 1} {t}", f"{c + 1} {t}", f"{c} {t - (c - 1)}", f"{c - 1} {t - (c - 1)}"],
    )


@generator(TOPIC, HARD)
def gen_grow_until(rng: random.Random) -> Question:
    """Step / accumulator while loops: doubling coins, saving money -- how many passes?"""
    if rng.random() < 0.5:
        start = rng.choice([1, 2, 3, 5])
        goal = rng.choice([20, 30, 50, 100])
        code = _lines(
            f"coins = {start}",
            "days = 0",
            f"while coins < {goal}:",
            "    coins = coins * 2",
            "    days += 1",
            "print(days, coins)",
        )
        out = _must_run(code)
        days, coins = (int(x) for x in out.split())
        why = f"coins doubles each pass: it first reaches {goal} or more after {days} passes, when it is {coins}."
        extras = [f"{days - 1} {coins // 2}", f"{days + 1} {coins * 2}", f"{days} {coins // 2}", f"{days - 1} {coins}"]
        muts = [("coins < ", "coins <= "), ("days = 0", "days = 1")]
    else:
        start = rng.choice([0, 5, 10])
        weekly = rng.choice([4, 6, 7, 8])
        goal = start + weekly * rng.randint(3, 5) + rng.choice([0, 1, 2])
        code = _lines(
            f"money = {start}",
            "weeks = 0",
            f"while money < {goal}:",
            f"    money += {weekly}",
            "    weeks += 1",
            'print("Weeks:", weeks)',
        )
        out = _must_run(code)
        weeks = int(out.split()[-1])
        why = f"Each pass adds {weekly} to money and 1 to weeks. money reaches {goal} or more after {weeks} passes."
        extras = [f"Weeks: {weeks - 1}", f"Weeks: {weeks + 1}", f"Weeks: {goal // weekly}", f"Weeks: {goal}"]
        muts = [("money < ", "money <= "), ("weeks = 0", "weeks = 1")]
    return _trace(HARD, code, rng, why, mutations=muts, extras=extras)


@generator(TOPIC, HARD)
def gen_break_modulo(rng: random.Random) -> Question:
    """`break` inside an `if` inside a `while`; what is count when the loop stops?"""
    k = rng.choice([3, 4, 5])
    limit = rng.choice([10, 12])
    code = _lines(
        "count = 1",
        f"while count <= {limit}:",
        f"    if count % {k} == 0:",
        "        break",
        "    print(count)",
        "    count += 1",
        'print("Stopped at", count)',
    )
    out = _must_run(code).split("\n")
    swapped = code.replace(f"    if count % {k} == 0:\n        break\n    print(count)", f"    print(count)\n    if count % {k} == 0:\n        break")
    return _trace(
        HARD,
        code,
        rng,
        f"count is printed until it reaches {k}, the first multiple of {k} (remainder 0). Then `break` leaves the loop before printing it, and count is still {k}.",
        extras=[
            _sim(swapped)[0],
            "\n".join(out[:-1] + [f"Stopped at {k + 1}"]),
            "\n".join(out[:-1] + [f"Stopped at {k - 1}"]),
            "\n".join(str(i) for i in range(1, k + 1)) + f"\nStopped at {k}",
        ],
    )


@generator(TOPIC, HARD)
def gen_positives_trace(rng: random.Random) -> Question:
    """`while num > 0` stops at the first non-positive number, not just at 0."""
    first = [rng.randint(2, 9) for _ in range(rng.randint(2, 3))]
    neg = -rng.randint(1, 5)
    after = rng.randint(2, 9)
    typed = [*first, neg, after, 0]
    code = _lines(
        "total = 0",
        'num = int(input("Enter a number: "))',
        "while num > 0:",
        "    total += num",
        '    num = int(input("Enter a number: "))',
        'print("Total:", total)',
    )
    s_first = sum(first)
    wrong = [s_first + neg + after, s_first + after, s_first + neg, s_first + after + abs(neg) * 0 + 1]
    return _trace(
        HARD,
        code,
        rng,
        f"The loop condition is `num > 0`, so it ends at the first number that is not positive ({neg}), not only at 0. The numbers after it are never read. Total: {s_first}.",
        stdin=[str(x) for x in typed],
        prompt=f"The player types {_typed([str(x) for x in typed])}. What does the program print?",
        extras=[f"Total: {w}" for w in wrong],
    )


@generator(TOPIC, HARD)
def gen_quit_count_ignored(rng: random.Random) -> Question:
    """Counting words until the stop word -- anything typed after it is never read."""
    word = rng.choice(_QUIT_WORDS)
    pool = ["sun", "moon", "star", "cloud", "rain", "wind", "snow", "fog"]
    before = rng.sample(pool, rng.randint(2, 4))
    after = rng.sample([p for p in pool if p not in before], rng.randint(1, 2))
    typed = [*before, word, *after]
    code = _lines(
        "count = 0",
        "while True:",
        '    word = input("Word: ")',
        f'    if word == "{word}":',
        "        break",
        "    count += 1",
        'print("Words typed:", count)',
    )
    n = len(before)
    return _trace(
        HARD,
        code,
        rng,
        f"The loop counts the {n} words typed before `{word}`. When `{word}` is read, `break` runs before `count += 1`, and the words after it are never read.",
        stdin=typed,
        prompt=f"The player types {_typed(typed)}. What does the program print?",
        extras=[f"Words typed: {x}" for x in (n + 1, len(typed), n - 1, len(typed) - 1)],
    )


@generator(TOPIC, HARD)
def gen_menu_trace(rng: random.Random) -> Question:
    """`while True` menu: an `if`/`elif` inside the loop, only one answer breaks out."""
    add_word, end_word = rng.choice([("yes", "no"), ("add", "stop"), ("more", "done")])
    others = [o for o in ["maybe", "hmm", "ok", "later"]]
    n_items = rng.randint(3, 5)
    items = [rng.choice([add_word, add_word, rng.choice(others)]) for _ in range(n_items)]
    if items.count(add_word) < 2 or all(x == add_word for x in items):
        items[0], items[1] = add_word, others[0]
        items[-1] = add_word
    typed = [*items, end_word, add_word]
    code = _lines(
        "coins = 0",
        "while True:",
        f'    choice = input("Add a coin? ({add_word}/{end_word}): ")',
        f'    if choice == "{add_word}":',
        "        coins += 1",
        f'    elif choice == "{end_word}":',
        "        break",
        'print("Coins:", coins)',
    )
    k = items.count(add_word)
    run = 0
    for x in items:
        if x != add_word:
            break
        run += 1
    return _trace(
        HARD,
        code,
        rng,
        f"Only `{add_word}` adds a coin ({k} times here). Other words fall through both tests and the loop simply asks again. Only `{end_word}` runs `break`; the last answer is never read.",
        stdin=typed,
        prompt=f"The player types {_typed(typed)}. What does the program print?",
        extras=[f"Coins: {v}" for v in (len(items), k + 1, run, k - 1, len(typed))],
    )


@generator(TOPIC, HARD)
def gen_count_matches(rng: random.Random) -> Question:
    """An `if` (with `%`) inside a `while`: count the evens / multiples."""
    limit = rng.randint(8, 14)
    if rng.random() < 0.45:
        code = _lines(
            "count = 1",
            "evens = 0",
            "odds = 0",
            f"while count <= {limit}:",
            "    if count % 2 == 0:",
            "        evens += 1",
            "    else:",
            "        odds += 1",
            "    count += 1",
            "print(evens, odds)",
        )
        ev, od = limit // 2, limit - limit // 2
        why = f"count goes from 1 to {limit}. Even numbers (remainder 0 when divided by 2) are counted in evens, all the others in odds: {ev} and {od}."
        extras = [f"{od} {ev}", f"{ev + 1} {od - 1}", f"{ev} {od + 1}", f"{ev - 1} {od}"]
        return _trace(HARD, code, rng, why, extras=extras, mutations=[("<=", "<"), ("count = 1", "count = 0")])
    k = rng.choice([3, 4, 5, 2])
    name = rng.choice(["hits", "multiples", "found"])
    code = _lines(
        "count = 1",
        f"{name} = 0",
        f"while count <= {limit}:",
        f"    if count % {k} == 0:",
        f"        {name} += 1",
        "    count += 1",
        f"print({name})",
    )
    want = limit // k
    return _trace(
        HARD,
        code,
        rng,
        f"Only the numbers from 1 to {limit} that divide evenly by {k} (remainder 0) add 1, so the loop counts {want}.",
        extras=[str(want + 1), str(want - 1), str(limit), str(limit % k), str(limit - want)],
        mutations=[("<=", "<"), ("count = 1", "count = 0")],
    )


@generator(TOPIC, HARD)
def gen_never_hits_target(rng: random.Random) -> Question:
    """`!=` with a step that jumps over the target: the update exists, the loop still never ends."""
    var = rng.choice(["count", "num", "number"])
    step = rng.choice([2, 3, 4])
    overshoot = rng.random() < 0.55
    k = rng.randint(3, 4)
    start = step * k + (rng.randint(1, step - 1) if overshoot else 0)
    code = _lines(f"{var} = {start}", f"while {var} != 0:", f"    print({var})", f"    {var} -= {step}")
    out, err, _ = _sim(code)
    shown = [str(start - step * i) for i in range(k + (1 if overshoot else 0))]
    if overshoot:
        if err != "LOOP":
            raise GenerationError("expected an endless loop")
        correct = "It never stops: it counts past 0 into negative numbers"
        wrong = [
            f"It prints {', '.join(shown)} and then stops",
            f"It prints {', '.join(shown)}, 0 and then stops",
            "It prints nothing",
        ]
        why = f"{var} goes {', '.join(shown)}, then {int(shown[-1]) - step}, ... It jumps over 0, so `{var} != 0` is always True. Use `{var} > 0` instead."
    else:
        if err is not None:
            raise GenerationError("expected a loop that ends")
        correct = f"It prints {', '.join(shown)} and then stops"
        wrong = [
            f"It prints {', '.join(shown)}, 0 and then stops",
            "It never stops: it counts past 0 into negative numbers",
            "It prints nothing",
        ]
        why = f"{var} lands exactly on 0 after {k} passes, so `{var} != 0` becomes False and the loop stops (0 itself is not printed)."
    return _choice(
        difficulty=HARD,
        prompt="What happens when this code runs?",
        code=code,
        correct=correct,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


def _countdown_program(var: str, start: int, finale: str, *, cond: str = "> 0", update: bool = True,
                       finale_inside: bool = False, finale_first: bool = False, update_first: bool = False) -> str:
    parts = []
    if finale_first:
        parts.append(f'print("{finale}")')
    parts += [f"{var} = {start}", f"while {var} {cond}:"]
    body = [f"    print({var})"]
    if update:
        body = ([f"    {var} -= 1"] + body) if update_first else (body + [f"    {var} -= 1"])
    if finale_inside:
        body.append(f'    print("{finale}")')
    parts += body
    if not finale_inside and not finale_first:
        parts.append(f'print("{finale}")')
    return _lines(*parts)


@generator(TOPIC, HARD)
def gen_which_program_blastoff(rng: random.Random) -> Question:
    """Which whole program prints the countdown and then the finale exactly once?"""
    var = _var(rng)
    start = rng.randint(3, 4)
    finale = rng.choice(_FINALES)
    good = _countdown_program(var, start, finale, cond=rng.choice(["> 0", ">= 1"]))
    target = "\n".join([*(str(i) for i in range(start, 0, -1)), finale])
    if _sim(good)[:2] != (target, None):
        raise GenerationError("good program is wrong")
    bad = [
        _countdown_program(var, start, finale, finale_inside=True),
        _countdown_program(var, start, finale, cond=">= 0"),
        _countdown_program(var, start, finale, update=False),
        _countdown_program(var, start, finale, finale_first=True),
        _countdown_program(var, start, finale, update_first=True),
    ]
    wrong = [b for b in bad if _sim(b)[:2] != (target, None)]
    head, tail = wrong[:2], wrong[2:]
    rng.shuffle(tail)
    nums = ", ".join(str(i) for i in range(start, 0, -1))
    return _choice(
        difficulty=HARD,
        prompt=f"Which program prints {nums} and then `{finale}` exactly once?",
        correct=good,
        distractors=head + tail,
        explanation=f"Count down while {var} is above 0, update inside the loop, and put `print(\"{finale}\")` after the loop (not indented).",
        rng=rng,
    )


@generator(TOPIC, HARD)
def gen_stop_condition(rng: random.Random) -> Question:
    """Which `if` condition ends the `while True` loop for any capital letters / for either of two words."""
    var = rng.choice(["text", "text", "answer", "reply"])
    kind = rng.choice(["capitals", "either"])
    template = _lines(
        "while True:",
        f'    {var} = input("Type to stop: ")',
        "    if {cond}:",
        "        break",
        f'    print("You typed:", {var})',
    )
    if kind == "capitals":
        word = rng.choice(["quit", "stop", "done"])
        good = f'{var}.lower() == "{word}"'
        cands = [
            f'{var} == "{word}"',
            f'{var}.upper() == "{word}"',
            f'{var}.lower == "{word}"',
            f'{var} == "{word.upper()}"',
            f'{var}.lower() = "{word}"',
        ]
        typed = ["hi", word.capitalize(), "go"]
        prompt = f"The loop should stop when the player types `{word}` in any capital letters (`{word}`, `{word.capitalize()}` or `{word.upper()}`). Which condition does that?"
        why = f'`{var}.lower()` turns whatever was typed into lowercase letters first, so `{word.capitalize()}` and `{word.upper()}` also match `"{word}"`.'
    else:
        word1, word2 = rng.choice([("quit", "exit"), ("stop", "done"), ("quit", "stop"), ("end", "bye")])
        good = f'{var} == "{word1}" or {var} == "{word2}"'
        cands = [
            f'{var} == "{word1}" and {var} == "{word2}"',
            f'{var} == "{word1}" or "{word2}"',
            f'{var} != "{word1}" or {var} != "{word2}"',
            f'{var} == "{word1}"',
            f'{var} == "{word1}" or {var} = "{word2}"',
        ]
        typed = ["hi", word2, "go"]
        prompt = f"The loop should stop when the player types `{word1}` or `{word2}`. Which condition does that?"
        why = f'Compare `{var}` with each word using `==` and join the two tests with `or`. In `{var} == "{word1}" or "{word2}"` the second part is just a non-empty string, which counts as True, so that condition is always True.'
    ref = _sim(template.format(cond=good), typed)
    if ref[1] is not None:
        raise GenerationError("reference should run cleanly")
    wrong = [c for c in cands if _sim(template.format(cond=c), typed)[:2] != ref[:2]]
    if len(wrong) < 3:
        raise GenerationError("not enough distinct wrong conditions")
    rng.shuffle(wrong)
    return _choice(
        difficulty=HARD,
        prompt=prompt,
        code=template.format(cond=BLANK),
        correct=good,
        distractors=wrong,
        explanation=why,
        rng=rng,
    )


# ==========================================================================
# BLANKS -- type the missing piece of a lesson-style loop
# ==========================================================================


def _expect(code: str, stdin=()) -> str:
    """What the *filled-in* snippet prints (used as expect_output)."""
    return _must_run(code, stdin)


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_pieces(rng: random.Random) -> Question:
    """The three pieces of the classic counter: starting value, comparison, update."""
    var = _var(rng)
    label = _LABELS[var]
    start = rng.choice([1, 1, 2])
    limit = start + rng.randint(2, 4)
    template = _lines(
        f"{var} = {blank_mark(1)}",
        f"while {var} {blank_mark(2)} {limit}:",
        f'    print("{label}", {var})',
        f"    {var} {blank_mark(3)} 1",
    )
    filled = template.replace(blank_mark(1), str(start)).replace(blank_mark(2), "<=").replace(blank_mark(3), "+=")
    nums = ", ".join(str(i) for i in range(start, limit + 1))
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the three pieces so the loop prints {nums}.",
        template=template,
        blanks=[
            Blank([str(start)], hint="initialization"),
            Blank(["<="], hint="condition"),
            Blank(["+=", f"= {var} +"], hint="update"),
        ],
        explanation=f"Start at {start} (initialization), keep going while `{var} <= {limit}` (condition), and add 1 each time with `{var} += 1` (update).",
        expect_output=_expect(filled),
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_countdown_pieces(rng: random.Random) -> Question:
    """The three pieces of a countdown: starting value, comparison, update (Blastoff! mini-challenge)."""
    var = _var(rng)
    start = rng.randint(3, 6)
    template = _lines(
        f"{var} = {blank_mark(1)}",
        f"while {var} {blank_mark(2)} 0:",
        f"    print({var})",
        f"    {var} {blank_mark(3)} 1",
    )
    filled = template.replace(blank_mark(1), str(start)).replace(blank_mark(2), ">").replace(blank_mark(3), "-=")
    nums = ", ".join(str(i) for i in range(start, 0, -1))
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"Fill in the three pieces so the countdown prints {nums}.",
        template=template,
        blanks=[
            Blank([str(start)], hint="initialization"),
            Blank([">", "!="], hint="condition"),
            Blank(["-=", f"= {var} -"], hint="update"),
        ],
        explanation=f"Start at {start} (initialization), keep going while `{var} > 0` (condition), and subtract 1 each time with `{var} -= 1` (update).",
        expect_output=_expect(filled),
    )


@generator(TOPIC, EASY, qtype="blanks")
def gen_blanks_vocab(rng: random.Random) -> Question:
    """Type the lesson's word for each part of the loop (the comments in section 1)."""
    var = _var(rng)
    label = _LABELS[var]
    if rng.random() < 0.7:
        start = rng.choice([1, 1, 2])
        limit = start + rng.randint(2, 4)
        head, cond, upd = f"{var} = {start}", f"while {var} <= {limit}:", f"{var} += 1"
        last = "update"
        names = [["update", "increment", "update (increment)"]]
    else:
        start = rng.randint(3, 5)
        head, cond, upd = f"{var} = {start}", f"while {var} > 0:", f"{var} -= 1"
        last = "update"
        names = [["update", "decrement", "update (decrement)"]]
    template = _lines(
        f"{head:<24}# {blank_mark(1)}",
        f"{cond:<24}# {blank_mark(2)}",
        f'    print("{label}", {var})',
        f"    {upd:<20}# {blank_mark(3)}",
    )
    filled = template.replace(blank_mark(1), "x").replace(blank_mark(2), "y").replace(blank_mark(3), "z")
    return blanks_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Type the name of each piece of the loop (initialization, condition or update).",
        template=template,
        blanks=[
            Blank(["initialization", "initialisation", "initialize", "init"], hint="word", ignore_case=True),
            Blank(["condition"], hint="word", ignore_case=True),
            Blank(names[0], hint="word", ignore_case=True),
        ],
        explanation="Initialization sets the starting value, the condition keeps the loop running, and the update changes the value so the condition can become False.",
        expect_output=_expect(filled),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_update(rng: random.Random) -> Question:
    """Type the update statement (the line that makes progress)."""
    var = _var(rng)
    kind = rng.choice(["up", "up_step", "down", "down_step"])
    if kind == "up":
        start, step, op = 1, 1, "<="
        limit = rng.randint(3, 6)
        accepted = [f"{var} += 1", f"{var} = {var} + 1", f"{var} = 1 + {var}"]
        cond = f"{var} <= {limit}"
    elif kind == "up_step":
        step = rng.choice([2, 5, 10])
        start = step
        limit = step * rng.randint(3, 5)
        accepted = [f"{var} += {step}", f"{var} = {var} + {step}", f"{var} = {step} + {var}"]
        cond = f"{var} <= {limit}"
    elif kind == "down":
        start = rng.randint(3, 6)
        accepted = [f"{var} -= 1", f"{var} = {var} - 1"]
        cond = f"{var} > 0"
    else:
        step = rng.choice([2, 5])
        start = step * rng.randint(3, 5)
        accepted = [f"{var} -= {step}", f"{var} = {var} - {step}"]
        cond = f"{var} > 0"
    template = _lines(f"{var} = {start}", f"while {cond}:", f"    print({var})", f"    {blank_mark(1)}", 'print("Done")')
    filled = template.replace(blank_mark(1), accepted[0])
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=("Type the update line so the loop counts "
                + ("up" if kind.startswith("up") else "down")
                + (f" by {step}" if kind.endswith("step") else "")
                + " and eventually stops."),
        template=template,
        blanks=[Blank(accepted, hint="update statement")],
        explanation=f"The update changes {var} each time so the condition `{cond}` can eventually become False: `{accepted[0]}`.",
        expect_output=_expect(filled),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_quit(rng: random.Random) -> Question:
    """Lesson 3) 'prompt until user types quit': while True + break."""
    word = rng.choice(_STOP_WORDS)
    var = rng.choice(["text", "text", "answer", "reply"])
    end = rng.choice(["Loop ended.", "Loop ended.", "Goodbye!", "All done."])
    template = _lines(
        f"{blank_mark(1)} True:",
        f'    {var} = input("Type \'{word}\' to stop: ")',
        f"    if {var} == {blank_mark(2)}:",
        f"        {blank_mark(3)}",
        f'print("{end}")',
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Complete the program so it keeps asking until the player types `{word}`.",
        template=template,
        blanks=[
            Blank(["while"], hint="keyword"),
            Blank([f'"{word}"', f"'{word}'"], hint="the stop word", mode="expr"),
            Blank(["break"], hint="exit the loop"),
        ],
        explanation=f"`while True:` loops until something stops it. When the text equals `\"{word}\"`, `break` jumps out of the loop and the code after the loop runs.",
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_blastoff(rng: random.Random) -> Question:
    """Mini-Challenge Countdown: the condition and the update."""
    var = _var(rng)
    start = rng.randint(3, 6)
    finale = rng.choice(_FINALES)
    template = _lines(
        f"{var} = {start}",
        f"while {blank_mark(1)}:",
        f"    print({var})",
        f"    {blank_mark(2)}",
        f'print("{finale}")',
    )
    cond = [f"{var} > 0", f"{var} >= 1", f"0 < {var}", f"1 <= {var}", f"{var} != 0"]
    upd = [f"{var} -= 1", f"{var} = {var} - 1"]
    filled = template.replace(blank_mark(1), cond[0]).replace(blank_mark(2), upd[0])
    nums = ", ".join(str(i) for i in range(start, 0, -1))
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the condition and the update so the program prints {nums} and then {finale}",
        template=template,
        blanks=[
            Blank(cond, hint="condition", mode="expr"),
            Blank(upd, hint="update"),
        ],
        explanation=f"Keep looping while {var} is still above 0, and subtract 1 each pass. When the loop ends, \"{finale}\" prints once.",
        expect_output=_expect(filled),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_accumulator(rng: random.Random) -> Question:
    """An accumulator: start the total at 0 and add the counter to it."""
    n = rng.randint(3, 6)
    acc = rng.choice(["total", "total", "score", "coins"])
    seq = " + ".join(str(i) for i in range(1, n + 1))
    template = _lines(
        f"{acc} = {blank_mark(1)}",
        "count = 1",
        f"while count <= {n}:",
        f"    {acc} {blank_mark(2)} count",
        "    count += 1",
        f'print("Total:", {acc})',
    )
    filled = template.replace(blank_mark(1), "0").replace(blank_mark(2), "+=")
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the program adds {seq} and prints the total.",
        template=template,
        blanks=[
            Blank(["0"], hint="starting value"),
            Blank(["+=", f"= {acc} +"], hint="add count"),
        ],
        explanation=f"The running total must start at 0 before the loop, and each pass adds count to it with `{acc} += count`.",
        expect_output=_expect(filled),
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_password(rng: random.Random) -> Question:
    """Bingo: password until correct -- the input() inside the loop is the update."""
    secret = rng.choice(_SECRETS)
    target = rng.choice(["secret", "secret", "password"])
    guess = rng.choice(["guess", "guess", "attempt", "answer"])
    wrong_msg = rng.choice(["Wrong, try again.", "Wrong, try again.", "Try again!", "Access denied."])
    ok_msg = rng.choice(["Welcome!", "Welcome!", "Access granted!", "You're in!"])
    if rng.random() < 0.5:
        template = _lines(
            f'{target} = "{secret}"',
            f'{guess} = input("Password: ")',
            f"while {guess} {blank_mark(1)} {target}:",
            f'    print("{wrong_msg}")',
            f'    {blank_mark(2)} = input("Password: ")',
            f'print("{ok_msg}")',
        )
        blanks = [Blank(["!="], hint="comparison"), Blank([guess], hint="variable")]
        why = f"Keep looping while the guess is NOT equal to the {target} (`!=`). Asking again inside the loop and storing it in `{guess}` is the update."
        prompt = f"Complete the loop so it keeps asking until the guess equals the {target}."
    else:
        template = _lines(
            f'{target} = "{secret}"',
            f'{guess} = {blank_mark(1)}("Password: ")',
            f"while {guess} != {target}:",
            f'    print("{wrong_msg}")',
            f'    {guess} = input("Password: ")',
            f'print("{ok_msg}")',
        )
        blanks = [Blank(["input"], hint="function")]
        why = "`input(...)` asks the player to type and gives back what they typed. The loop asks once before it starts and again at the end of every pass."
        prompt = "Fill in the blank so the program asks for the first guess before the loop starts."
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=prompt,
        template=template,
        blanks=blanks,
        explanation=why,
    )


@generator(TOPIC, MEDIUM, qtype="blanks")
def gen_blanks_break_count(rng: random.Random) -> Question:
    """`while True` with a counter and a `break`."""
    var = rng.choice(["count", "count", "num", "number", "n", "lap"])
    if rng.random() < 0.6:
        limit = rng.randint(3, 9)
        head, step, goal = f"{var} = 0", f"{var} += 1", limit
        said = f"reaches {limit}"
    else:
        limit = rng.randint(3, 6)
        head, step, goal = f"{var} = {limit + rng.randint(0, 2)}", f"{var} -= 1", 0
        said = "reaches 0"
    template = _lines(
        head,
        f"while {blank_mark(1)}:",
        f"    {step}",
        f"    if {var} == {goal}:",
        f"        {blank_mark(2)}",
        f'print("Stopped at", {var})',
    )
    filled = template.replace(blank_mark(1), "True").replace(blank_mark(2), "break")
    return blanks_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Fill in the blanks so the loop stops by itself when {var} {said}.",
        template=template,
        blanks=[Blank(["True"], hint="always-true condition"), Blank(["break"], hint="exit")],
        explanation=f"`while True:` never ends on its own, so the `if` uses `break` to leave the loop when {var} is {goal}.",
        expect_output=_expect(filled),
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_sum_zero(rng: random.Random) -> Question:
    """Bingo: sum what the player types until 0 (while True + break + accumulator)."""
    stop = rng.choice([0, 0, 0, -1])
    acc = rng.choice(["total", "total", "sum_total", "score"])
    num = rng.choice(["num", "num", "value", "number"])
    label = rng.choice(["Total:", "Total:", "Sum:", "Score:"])
    template = _lines(
        f"{acc} = 0",
        "while True:",
        f'    {num} = int(input("Enter a number ({stop} to stop): "))',
        f"    if {num} {blank_mark(1)} {stop}:",
        f"        {blank_mark(2)}",
        f"    {acc} {blank_mark(3)} {num}",
        f'print("{label}", {acc})',
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Complete the program that adds up the numbers the player types and stops when they type {stop}.",
        template=template,
        blanks=[
            Blank(["=="], hint="comparison"),
            Blank(["break"], hint="exit the loop"),
            Blank(["+=", f"= {acc} +"], hint="add to the total"),
        ],
        explanation=f"Compare with `==` to spot the stop number {stop}, `break` before adding it, and keep the running total with `{acc} += {num}`.",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_menu(rng: random.Random) -> Question:
    """`if` / `elif` inside `while True`: one answer adds, another breaks."""
    add_word, end_word = rng.choice([("yes", "no"), ("add", "stop"), ("more", "done"), ("coin", "quit")])
    thing = rng.choice(["coins", "points", "stars", "lives"])
    template = _lines(
        f"{thing} = 0",
        "while True:",
        f'    choice = input("Add one? ({add_word}/{end_word}): ")',
        f'    if choice == "{add_word}":',
        f"        {thing} {blank_mark(1)} 1",
        f'    {blank_mark(2)} choice == "{end_word}":',
        f"        {blank_mark(3)}",
        f'print("{thing.capitalize()}:", {thing})',
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Complete the menu loop: `{add_word}` adds 1 and `{end_word}` ends the loop.",
        template=template,
        blanks=[
            Blank(["+=", f"= {thing} +"], hint="add"),
            Blank(["elif"], hint="keyword"),
            Blank(["break"], hint="exit the loop"),
        ],
        explanation=f"`{thing} += 1` adds one. The second check uses `elif`, and `break` leaves the loop when the player types `{end_word}`.",
    )


@generator(TOPIC, HARD, qtype="blanks")
def gen_blanks_guess(rng: random.Random) -> Question:
    """A guessing loop: the condition compares the guess with the secret."""
    secret = rng.randint(4, 40)
    template = _lines(
        f"secret = {secret}",
        "guess = 0",
        "tries = 0",
        f"while guess {blank_mark(1)} secret:",
        '    guess = int(input("Guess: "))',
        f"    tries {blank_mark(2)} 1",
        'print("Correct! Tries:", tries)',
    )
    return blanks_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Complete the loop so it keeps asking for guesses until the player gets the secret and counts the tries.",
        template=template,
        blanks=[Blank(["!="], hint="comparison"), Blank(["+=", "= tries +"], hint="count a try")],
        explanation="`guess` starts at 0 so the loop begins; keep going while `guess != secret`, and add 1 to `tries` on every pass.",
    )


# ==========================================================================
# MATCH
# ==========================================================================


@generator(TOPIC, EASY, qtype="match")
def gen_match_pieces(rng: random.Random) -> Question:
    """Match each line of the counter loop to its job."""
    var = _var(rng)
    label = _LABELS[var]
    if rng.random() < 0.7:
        start = rng.choice([1, 1, 2])
        limit = start + rng.randint(3, 6)
        init, cond, upd = f"{var} = {start}", f"while {var} <= {limit}:", f"{var} += 1"
    else:
        start = rng.randint(4, 8)
        init, cond, upd = f"{var} = {start}", f"while {var} > 0:", f"{var} -= 1"
    body = f'print("{label}", {var})'
    code = _lines(init, cond, f"    {body}", f"    {upd}")
    pairs = [
        (init, "Initialization (the starting value)"),
        (cond, "Condition (keeps the loop running)"),
        (body, "The repeated work (loop body)"),
        (upd, "Update (changes the value each time)"),
    ]
    if rng.random() < 0.4:
        pairs.pop(2)
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt="Match each line of the loop to its job.",
        pairs=pairs,
        explanation="Initialization sets the starting value, the condition keeps the loop running, and the update changes the value so the condition can become False.",
        rng=rng,
        code=code,
    )


_VOCAB_PAIRS = [
    ("`while`", "Repeats a block while a condition is True"),
    ("`break`", "Exits the loop immediately"),
    ("Ctrl + C", "Stops a runaway loop in the terminal"),
    ("`while True:`", "A loop that only ends with a `break`"),
    ("`count += 1`", "Adds 1 to count (an update)"),
    ("`count -= 1`", "Subtracts 1 from count (counts down)"),
    ("`input()`", "Asks the player to type something (a string)"),
    ("Initialization", "Sets the starting value before the loop"),
    ("Condition", "The test that keeps the loop running"),
]


@generator(TOPIC, EASY, qtype="match")
def gen_match_vocab(rng: random.Random) -> Question:
    """Match loop words and symbols to what they do."""
    pairs = rng.sample(_VOCAB_PAIRS, rng.choice([4, 5]))
    return match_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=rng.choice(["Match each term to what it means.", "Match each loop word or symbol to what it does."]),
        pairs=pairs,
        explanation="These are the key words from the while-loop lesson: the loop itself, the three pieces, break, while True and Ctrl + C.",
        rng=rng,
        extra_options=[rng.choice(["Shows a message on the screen", "Checks whether two values are equal"])] if rng.random() < 0.5 else (),
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_headers(rng: random.Random) -> Question:
    """Match each condition to what the countdown loop does (checked by running each)."""
    var = _var(rng)
    start = rng.randint(3, 4)
    template = _lines(f"{var} = {start}", "while {cond}:", f"    print({var})", f"    {var} -= 1")
    groups = {
        "full": [f"{var} > 0", f"{var} >= 1", f"{var} != 0"],
        "zero": [f"{var} >= 0"],
        "short": [f"{var} > 1", f"{var} >= 2"],
        "none": [f"{var} > {start}", f"{var} < {start}", f"{var} == 0"],
        "forever": [f"{var} <= {start}"],
    }
    names = rng.sample(list(groups), 4)
    chosen = [rng.choice(groups[g]) for g in names]
    spare = [c for g in rng.sample(list(groups), 2) for c in groups[g] if c not in chosen]
    if spare and rng.random() < 0.6:
        chosen.append(rng.choice(spare))
    pairs = []
    for c in chosen:
        text, err, _ = _sim(template.format(cond=c))
        if err == "LOOP":
            ans = "Never stops"
        elif not text:
            ans = "Prints nothing"
        else:
            ans = "Prints " + ", ".join(text.split("\n"))
        pairs.append((c, ans))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each `while` condition to what the countdown loop does.",
        pairs=pairs,
        explanation="Trace each condition: the loop runs while it is True. A condition that is False at the start prints nothing; one that never becomes False never stops.",
        rng=rng,
        code=template.format(cond=BLANK),
    )


_FIX_PAIRS = [
    ("The loop is missing its update", "Add an update such as `count += 1` inside the loop"),
    ("The update line is not indented", "Indent it so it is part of the loop body"),
    ("The `while` line has no colon", "Add `:` at the end of the `while` line"),
    ("Blastoff! prints on every pass", "Un-indent it so it runs after the loop"),
    ("A countdown counts up and never stops", "Change `+= 1` to `-= 1`"),
    ("A program is stuck in a loop right now", "Press Ctrl + C in the terminal"),
    ("`count = 1` is inside the loop", "Move it above the `while` line"),
    ("You can't tell how many rounds you need", "Use `while True:` with a `break`"),
]


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_fixes(rng: random.Random) -> Question:
    """Common mistakes and their fixes."""
    pairs = rng.sample(_FIX_PAIRS, rng.choice([4, 5]))
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt="Match each while-loop problem to its fix.",
        pairs=pairs,
        explanation="Plan the update first, keep the update indented inside the loop, put initialization before the loop, and use Ctrl + C to stop a runaway loop.",
        rng=rng,
    )


@generator(TOPIC, HARD, qtype="match")
def gen_match_typed_lines(rng: random.Random) -> Question:
    """Match what the player types to how many lines the quit loop prints."""
    word = rng.choice(_QUIT_WORDS)
    code = _lines(
        "while True:",
        f'    text = input("Type \'{word}\' to stop: ")',
        '    print("You typed:", text)',
        f'    if text == "{word}":',
        "        break",
    )
    pool = ["hi", "ok", "yes", "go", "cat", "sun", "moon"]
    lengths = [1, 2, 3, 4]
    rng.shuffle(lengths)
    pairs = []
    for n in lengths[: rng.choice([3, 4])]:
        words = rng.sample(pool, n - 1) + [word]
        if rng.random() < 0.5:
            words += rng.sample(pool, rng.randint(1, 2))
        count = len(_must_run(code, words).split("\n"))
        pairs.append((", ".join(words), f"{count} line" + ("" if count == 1 else "s")))
    return match_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt="Match each list of typed answers to how many lines the loop prints.",
        pairs=pairs,
        explanation=f"Each answer is printed before the check, including `{word}` itself. Then `break` ends the loop, so anything typed after `{word}` is never read.",
        rng=rng,
        code=code,
    )


@generator(TOPIC, MEDIUM, qtype="match")
def gen_match_loop_summaries(rng: random.Random) -> Question:
    """Match short loop descriptions (initialization, condition, update) to what they print."""
    var = _var(rng)
    templates = [
        "{v} = 1, {v} <= {n}, {v} += 1",
        "{v} = 1, {v} < {n}, {v} += 1",
        "{v} = 2, {v} <= {n}, {v} += 2",
        "{v} = {n}, {v} > 0, {v} -= 1",
        "{v} = {n}, {v} >= 0, {v} -= 1",
        "{v} = 0, {v} < {n}, {v} += 1",
    ]
    rng.shuffle(templates)
    wanted = rng.choice([4, 4, 5])
    pairs = []
    seen = set()
    for text in templates:
        n = rng.randint(3, 6)
        item = text.format(v=var, n=n)
        init, cond, upd = item.split(", ")
        code = _lines(init, f"while {cond}:", f"    print({var})", f"    {upd}")
        answer = "Prints " + ", ".join(_must_run(code).split("\n"))
        if answer in seen:
            continue
        seen.add(answer)
        pairs.append((item, answer))
        if len(pairs) == wanted:
            break
    if len(pairs) < 4:
        raise GenerationError("not enough distinct loops")
    return match_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Each line gives a loop's initialization, condition and update, and the loop body is `print({var})`. Match each loop to what it prints.",
        pairs=pairs,
        explanation="Trace each loop: start at the initialization, print while the condition is True, and apply the update each time.",
        rng=rng,
    )


# ==========================================================================
# CODE -- the player types the expression / program / function
# ==========================================================================

_NEED_WHILE = [(r"\bwhile\b", "Use a while loop for this challenge")]


def _lines_out(rows) -> str:
    return "\n".join(str(r) for r in rows)


# ---- EASY ---------------------------------------------------------------------


@generator(TOPIC, EASY, qtype="code")
def gen_code_condition(rng: random.Random) -> Question:
    """Type the condition that goes after `while` (or after `if` for a break)."""
    var = _var(rng)
    kind = rng.choice(["at_most", "less_than", "above_zero", "until", "wrong_guess", "total_below", "quit", "at_least"])
    if kind == "at_most":
        sol = f"{var} <= limit"
        prompt = f"The loop should keep going while `{var}` is at most `limit`. Type the condition that goes after `while`."
        code = _lines(f"{var} = 1", f"while {BLANK}:", f"    print({var})", f"    {var} += 1")
        data = [(3, 5, True), (5, 5, True), (6, 5, False), (1, 1, True), (9, 4, False), (2, 8, True)]
        cases = [({var: a, "limit": b}, r) for a, b, r in data]
        why = f"\"At most\" means less than or equal to, so the condition is `{sol}`."
    elif kind == "less_than":
        sol = f"{var} < limit"
        prompt = f"The loop should keep going while `{var}` is less than `limit`. Type the condition that goes after `while`."
        code = _lines(f"{var} = 0", f"while {BLANK}:", f"    print({var})", f"    {var} += 1")
        data = [(3, 5, True), (5, 5, False), (6, 5, False), (0, 1, True), (1, 1, False), (4, 9, True)]
        cases = [({var: a, "limit": b}, r) for a, b, r in data]
        why = f"\"Less than\" does not include `limit` itself, so the condition is `{sol}`."
    elif kind == "above_zero":
        sol = f"{var} > 0"
        start = rng.randint(3, 6)
        prompt = f"A countdown should keep going while `{var}` is still above 0. Type the condition that goes after `while`."
        code = _lines(f"{var} = {start}", f"while {BLANK}:", f"    print({var})", f"    {var} -= 1")
        data = [(3, True), (1, True), (0, False), (5, True), (-1, False), (2, True)]
        cases = [({var: a}, r) for a, r in data]
        why = f"The loop keeps going while {var} is greater than 0, so the condition is `{sol}`."
    elif kind == "until":
        sol = f"{var} != limit"
        prompt = f"The loop should keep going until `{var}` reaches `limit` (it stops when they are equal). Type the condition that goes after `while`."
        code = _lines(f"{var} = 1", f"while {BLANK}:", f"    print({var})", f"    {var} += 1")
        data = [(1, 5, True), (4, 5, True), (5, 5, False), (2, 3, True), (3, 3, False), (7, 9, True)]
        cases = [({var: a, "limit": b}, r) for a, b, r in data]
        why = f"Keep looping while {var} is NOT yet equal to limit: `{sol}`."
    elif kind == "wrong_guess":
        sol = "guess != password"
        prompt = "The loop should keep asking while the player's `guess` is not the `password`. Type the condition that goes after `while`."
        code = _lines('password = "python"', 'guess = input("Password: ")', f"while {BLANK}:", '    guess = input("Password: ")')
        data = [("cat", "python", True), ("python", "python", False), ("pyth", "python", True), ("Python", "python", True), ("rocket", "rocket", False), ("a", "b", True)]
        cases = [({"guess": a, "password": b}, r) for a, b, r in data]
        why = "Keep looping while the guess is wrong, so use `!=` (not equal)."
    elif kind == "total_below":
        sol = "total < goal"
        prompt = "The loop should keep adding while `total` is below `goal`. Type the condition that goes after `while`."
        code = _lines("total = 0", "count = 1", f"while {BLANK}:", "    total += count", "    count += 1")
        data = [(0, 10, True), (9, 10, True), (10, 10, False), (12, 10, False), (4, 20, True), (20, 20, False)]
        cases = [({"total": a, "goal": b}, r) for a, b, r in data]
        why = "The loop continues only while total is still below goal, so `total < goal`."
    elif kind == "quit":
        word = rng.choice(_QUIT_WORDS)
        sol = f'text == "{word}"'
        prompt = f"The player's answer is stored in `text`. Type the condition for the `if` that should `break` when they type `{word}`."
        code = _lines("while True:", f"    text = input(\"Type '{word}' to stop: \")", f"    if {BLANK}:", "        break")
        data = [(word, True), ("hello", False), (word[:-1], False), (word + "ting", False), ("go", False), ("ok", False)]
        cases = [({"text": a}, r) for a, r in data]
        why = "Compare with `==`: the loop breaks when the text equals the stop word."
    else:
        sol = f"{var} >= limit"
        prompt = f"Type the condition for the `if` that should `break` once `{var}` reaches `limit` or goes past it."
        code = _lines(f"{var} = 0", "while True:", f"    {var} += 1", f"    if {BLANK}:", "        break")
        data = [(3, 5, False), (5, 5, True), (6, 5, True), (1, 1, True), (0, 4, False), (2, 9, False)]
        cases = [({var: a, "limit": b}, r) for a, b, r in data]
        why = f"\"Reaches or goes past\" means greater than or equal to: `{sol}`."
    task = expression_task(sol, cases)
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=task, explanation=why, code=code)


@generator(TOPIC, EASY, qtype="code")
def gen_code_update_expr(rng: random.Random) -> Question:
    """Type the expression an update line needs (the new value)."""
    var = _var(rng)
    kind = rng.choice(["step", "down", "total", "double"])
    if kind == "step":
        sol = f"{var} + step"
        prompt = f"The update line is `{var} = ____`. Type the expression that adds `step` to `{var}`."
        data = [(1, 1, 2), (5, 2, 7), (10, 5, 15), (0, 3, 3), (7, 10, 17), (20, 4, 24)]
        cases = [({var: a, "step": b}, r) for a, b, r in data]
        why = f"Counting by `step` means the new value is the old value plus step: `{var} = {sol}` (the same as `{var} += step`)."
    elif kind == "down":
        sol = f"{var} - 1"
        prompt = f"A countdown's update line is `{var} = ____`. Type the expression that takes 1 away from `{var}`."
        data = [(5, 4), (1, 0), (10, 9), (3, 2), (8, 7), (2, 1)]
        cases = [({var: a}, r) for a, r in data]
        why = f"`{var} = {sol}` is the same as `{var} -= 1`."
    elif kind == "total":
        sol = "total + num"
        prompt = "The running-total update is `total = ____`. Type the expression that adds `num` to `total`."
        data = [(0, 5, 5), (5, 12, 17), (17, 3, 20), (20, 0, 20), (8, 8, 16), (100, 1, 101)]
        cases = [({"total": a, "num": b}, r) for a, b, r in data]
        why = "`total = total + num` is the same as `total += num`."
    else:
        sol = "coins * 2"
        prompt = "The coins double every day: `coins = ____`. Type the expression for double the current `coins`."
        data = [(1, 2), (2, 4), (5, 10), (8, 16), (0, 0), (30, 60)]
        cases = [({"coins": a}, r) for a, r in data]
        why = "Doubling means multiplying by 2: `coins = coins * 2`."
    task = expression_task(sol, cases)
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=task, explanation=why)


@generator(TOPIC, EASY, qtype="code")
def gen_code_count_up(rng: random.Random) -> Question:
    """Bingo: 'While loop: count from 1 to 5' -- with `limit` preset so it can't be hard-coded."""
    var = _var(rng)
    label = _LABELS[var]
    labelled = rng.random() < 0.6
    body = f'print("{label}", {var})' if labelled else f"print({var})"
    kind = rng.choice(["from_one", "from_one", "from_start"])

    def out(a, b):
        return _lines_out((f"{label} {i}" if labelled else i) for i in range(a, b + 1))

    shown = f"`{label} 1`, `{label} 2`, ..." if labelled else "`1`, `2`, `3`, ..."
    if kind == "from_one":
        solution = _lines(f"{var} = 1", f"while {var} <= limit:", f"    {body}", f"    {var} += 1")
        cases = [Case(vars={"limit": n}, out=out(1, n)) for n in (3, 5, 1, 7, 0)]
        prompt = f"The variable `limit` is already set. Write a `while` loop that prints {shown} up to `limit`, one per line."
        starter = f"{var} = 1\n"
        why = f"Initialize `{var} = 1`, loop while `{var} <= limit`, print, and update with `{var} += 1`."
    else:
        solution = _lines(f"{var} = first", f"while {var} <= limit:", f"    {body}", f"    {var} += 1")
        pairs = [(3, 6), (1, 4), (5, 5), (2, 7), (6, 4)]
        cases = [Case(vars={"first": a, "limit": b}, out=out(a, b)) for a, b in pairs]
        shown = f"`{label} 3`, `{label} 4`, ..." if labelled else "`3`, `4`, `5`, ..."
        prompt = f"The variables `first` and `limit` are already set. Write a `while` loop that starts at `first` and prints {shown} up to `limit`, one per line (if `first` is already past `limit`, print nothing)."
        starter = ""
        why = f"Start the counter at `first` (`{var} = first`), loop while `{var} <= limit`, print, and update with `{var} += 1`."
    task = program_task(solution, cases, starter=starter, examples=2, requires=_NEED_WHILE)
    return code_question(topic=TOPIC, difficulty=EASY, prompt=prompt, task=task, explanation=why)


# ---- MEDIUM -------------------------------------------------------------------


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_countdown(rng: random.Random) -> Question:
    """Mini-Challenge: Countdown (ask for a number, count down to 1, then Blastoff!)."""
    var = rng.choice(["start", "num", "count", "number"])
    finale = rng.choice(_FINALES)
    solution = _lines(
        f'{var} = int(input("Start at: "))',
        f"while {var} >= 1:",
        f"    print({var})",
        f"    {var} -= 1",
        f'print("{finale}")',
    )
    cases = [Case(stdin=[str(n)], out=_lines_out([*range(n, 0, -1), finale])) for n in (5, 3, 1, 8, 10, 7)]
    task = program_task(solution, cases, starter=f'{var} = int(input("Start at: "))\n', examples=2, requires=_NEED_WHILE)
    intro = rng.choice(
        [
            "Write a program that asks for a starting number with `input()` (a positive integer), ",
            "Mini-Challenge Countdown: write a program that asks for a starting number with `input()` (a positive integer), ",
            "A rocket needs a countdown. Write a program that asks for the starting number with `input()` (a positive integer), ",
        ]
    )
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"{intro}counts down to 1 one number per line, and then prints `{finale}`.",
        task=task,
        explanation=f"Cast the input with `int()`, loop while the number is 1 or more, print it and subtract 1, then print `{finale}` after the loop (not indented).",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_password(rng: random.Random) -> Question:
    """Bingo: 'While loop: keep asking password until correct'."""
    secret = rng.choice(_SECRETS)
    wrong_msg = rng.choice(["Wrong, try again.", "Wrong, try again.", "Try again!", "Access denied."])
    ok_msg = rng.choice(["Welcome!", "Welcome!", "Access granted!", "You're in!"])
    solution = _lines(
        f'secret = "{secret}"',
        'guess = input("Password: ")',
        "while guess != secret:",
        f'    print("{wrong_msg}")',
        '    guess = input("Password: ")',
        f'print("{ok_msg}")',
    )
    scripts = [
        [secret],
        ["cat", secret],
        ["abc", "123", "hello", secret],
        [secret.capitalize(), secret],
        ["no", secret[:-1], secret],
    ]
    cases = [Case(stdin=s, out=_lines_out([*([wrong_msg] * (len(s) - 1)), ok_msg])) for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"The secret word is `{secret}`. Write a program that keeps asking for a guess with `input()`. Print `{wrong_msg}` after each wrong guess and `{ok_msg}` once the guess is right.",
        task=task,
        explanation="Ask once before the loop, then loop while the guess is wrong: print the message and ask again. The new `input()` inside the loop is the update.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_quit_echo(rng: random.Random) -> Question:
    """Lesson 3) `while True` + `break` -- echo each line until the stop word."""
    word = rng.choice(_STOP_WORDS)
    echo = rng.choice(["You typed:", "You typed:", "You entered:", "Echo:"])
    end = rng.choice(["Loop ended.", "Loop ended.", "Goodbye!", "All done."])
    var = rng.choice(["text", "text", "word", "answer"])
    solution = _lines(
        "while True:",
        f'    {var} = input("Type \'{word}\' to stop: ")',
        f'    if {var} == "{word}":',
        "        break",
        f'    print("{echo}", {var})',
        f'print("{end}")',
    )
    scripts = [
        [word],
        ["hi", word],
        ["a", "b", "c", word],
        ["hello world", word],
        [word.upper(), "ok", word],
    ]

    def out(s):
        return _lines_out([*(f"{echo} {t}" for t in s[:-1]), end])

    cases = [Case(stdin=s, out=out(s)) for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that keeps asking for text with `input()`. For each answer print `{echo} ` and the text, but when the player types `{word}` stop asking and print `{end}` (do not echo `{word}`).",
        task=task,
        explanation=f"Use `while True:`; inside, read the text, `break` if it equals `{word}`, otherwise print it. `{end}` goes after the loop.",
    )


_STEP_KINDS = [
    ("the multiples of 5", 5, 5),
    ("the multiples of 3", 3, 3),
    ("the even numbers", 2, 2),
    ("the odd numbers", 1, 2),
    ("the multiples of 10", 10, 10),
    ("the multiples of 4", 4, 4),
    ("the multiples of 6", 6, 6),
    ("the multiples of 7", 7, 7),
    ("the numbers counting by 5s", 0, 5),
    ("the numbers counting by 10s", 0, 10),
    ("the numbers counting by 2s", 0, 2),
    ("the numbers counting by 3s", 1, 3),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_step_loop(rng: random.Random) -> Question:
    """Step while loops: count by 2s / 5s... up to a preset `limit`."""
    name, start, step = rng.choice(_STEP_KINDS)
    var = rng.choice(["num", "count", "number"])
    solution = _lines(f"{var} = {start}", f"while {var} <= limit:", f"    print({var})", f"    {var} += {step}")
    limits = [start + step * 3, start + step * 2 + (step // 2 or 1), start, start - 1, start + step * 5 - 1, start + step * 4]
    cases = [Case(vars={"limit": lim}, out=_lines_out(range(start, lim + 1, step))) for lim in limits]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"The variable `limit` is already set. Write a `while` loop that prints {name} from {start} up to `limit` (never past it), one per line.",
        task=task,
        explanation=f"Start at {start}, loop while the number is at most `limit`, print it, and update with `{var} += {step}`. If {start} is already past `limit` nothing prints.",
    )


_SUM_KINDS = [
    ("sum_to", "add 1 + 2 + 3 + ... + {p}", 1, 1),
    ("add_up_to", "add 1 + 2 + 3 + ... + {p}", 1, 1),
    ("total_to", "add 1 + 2 + 3 + ... + {p}", 1, 1),
    ("sum_evens", "add the even numbers 2 + 4 + 6 + ... up to {p}", 2, 2),
    ("sum_odds", "add the odd numbers 1 + 3 + 5 + ... up to {p}", 1, 2),
    ("sum_threes", "add the multiples of 3 (3 + 6 + 9 + ...) up to {p}", 3, 3),
    ("sum_fives", "add the multiples of 5 (5 + 10 + 15 + ...) up to {p}", 5, 5),
]


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_sum_to(rng: random.Random) -> Question:
    """An accumulator inside a function: use a while loop and return the total."""
    fn, desc, start, step = rng.choice(_SUM_KINDS)
    p = rng.choice(["n", "n", "top", "last", "limit"])
    desc = desc.format(p=p)
    solution = _lines(
        f"def {fn}({p}):",
        "    total = 0",
        f"    count = {start}",
        f"    while count <= {p}:",
        "        total += count",
        f"        count += {step}",
        "    return total",
    )
    cases = [((n,), sum(range(start, n + 1, step))) for n in (4, 10, 0, 1, 7, 12)]
    task = function_task(fn, solution, cases, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{fn}({p})` that uses a `while` loop to {desc}, and returns the total (don't print it).",
        task=task,
        explanation="Start `total` at 0 before the loop, add the counter to it on every pass, update the counter, and `return total` after the loop.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_launch_fn(rng: random.Random) -> Question:
    """The Countdown as a function that prints."""
    fn = rng.choice(["countdown", "launch", "count_down"])
    finale = rng.choice(_FINALES)
    solution = _lines(
        f"def {fn}(n):",
        "    while n >= 1:",
        "        print(n)",
        "        n -= 1",
        f'    print("{finale}")',
    )
    cases = [Case(args=[n], out=_lines_out([*range(n, 0, -1), finale])) for n in (3, 5, 1, 0, 6)]
    task = function_task(fn, solution, cases, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a function `{fn}(n)` that uses a `while` loop to print n, n-1, ..., 1 (one per line) and then prints `{finale}`.",
        task=task,
        explanation=f"Loop while n is 1 or more: print it, subtract 1. After the loop print `{finale}`. If n is 0 only `{finale}` prints.",
    )


# ---- HARD ---------------------------------------------------------------------


@generator(TOPIC, HARD, qtype="code")
def gen_code_sum_until_zero(rng: random.Random) -> Question:
    """Bingo: 'sum user-entered positives until 0' (and two variations of it)."""
    kind = rng.choice(["total", "total", "count_total", "largest"])
    stop = 0 if kind != "total" else rng.choice([0, 0, -1])
    ask = f'int(input("Enter a number ({stop} to stop): "))'
    acc = rng.choice(["total", "total", "sum_total", "score"])
    tl = rng.choice(["Total:", "Total:", "Sum:", "Score:"])
    ll = rng.choice(["Largest:", "Biggest:", "Max:"])
    if kind == "total":
        solution = _lines(
            f"{acc} = 0",
            f"num = {ask}",
            f"while num != {stop}:",
            f"    {acc} += num",
            f"    num = {ask}",
            f'print("{tl}", {acc})',
        )
        want = f"print `{tl} ` followed by the sum of the numbers"
        scripts = [[5, 12, 3], [7], [], [1, 2, 3, 4, 5], [10, 20]]

        def out(s):
            return f"{tl} {sum(s)}"

    elif kind == "count_total":
        solution = _lines(
            "count = 0",
            "total = 0",
            f"num = {ask}",
            "while num != 0:",
            "    count += 1",
            "    total += num",
            f"    num = {ask}",
            'print("Count:", count)',
            f'print("{tl}", total)',
        )
        want = f"print `Count: ` and how many numbers were typed, then `{tl} ` and their sum (two lines)"
        scripts = [[5, 12, 3], [7], [], [1, 2, 3, 4, 5], [10, 20]]

        def out(s):
            return f"Count: {len(s)}\n{tl} {sum(s)}"

    else:
        solution = _lines(
            "largest = 0",
            f"num = {ask}",
            "while num != 0:",
            "    if num > largest:",
            "        largest = num",
            f"    num = {ask}",
            f'print("{ll}", largest)',
        )
        want = f"print `{ll} ` followed by the biggest number typed"
        scripts = [[5, 12, 3], [7], [3, 9, 2, 9], [1, 2, 3, 4, 5], [10, 20, 4]]

        def out(s):
            return f"{ll} {max(s)}"

    cases = [Case(stdin=[*map(str, s), str(stop)], out=out(s)) for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that keeps asking the player for positive numbers (use `input()` and `int()`). When they type {stop}, stop asking and {want}. The {stop} itself is not one of the numbers.",
        task=task,
        explanation=f"Ask once before the loop and again at the end of each pass. The loop ends when the number is {stop}, so it never gets added. Create the running variables (like the total) before the loop.",
    )


_MENU_PAIRS = [("yes", "no"), ("add", "stop"), ("more", "done"), ("coin", "quit")]
_MENU_THINGS = ["coins", "points", "stars", "lives"]


@generator(TOPIC, HARD, qtype="code")
def gen_code_menu_loop(rng: random.Random) -> Question:
    """`while True` menu: one answer adds, one breaks, anything else is ignored."""
    add_word, end_word = rng.choice(_MENU_PAIRS)
    thing = rng.choice(_MENU_THINGS)
    solution = _lines(
        f"{thing} = 0",
        "while True:",
        f'    choice = input("Add one? ({add_word}/{end_word}): ")',
        f'    if choice == "{add_word}":',
        f"        {thing} += 1",
        f'    elif choice == "{end_word}":',
        "        break",
        f'print("{thing.capitalize()}:", {thing})',
    )
    scripts = [
        [end_word],
        [add_word, add_word, end_word],
        [add_word, "maybe", add_word, add_word, end_word],
        ["hmm", end_word],
        ["ok", add_word, "later", end_word],
    ]
    cases = [Case(stdin=s, out=f"{thing.capitalize()}: {s.count(add_word)}") for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"Write a program that keeps asking `input()` for an answer. `{add_word}` adds 1 to a counter, `{end_word}` stops asking, and any other answer is ignored (just ask again). At the end print `{thing.capitalize()}: ` and the counter.",
        task=task,
        explanation=f"Use `while True:` with an `if`/`elif`: `{add_word}` adds 1, `{end_word}` runs `break`, and anything else matches neither, so the loop just asks again.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_grow_until(rng: random.Random) -> Question:
    """Step / accumulator loop with a goal: how many days / weeks / launches?"""
    kind = rng.choice(["grow", "grow", "save", "fuel"])
    if kind == "grow":
        mult = rng.choice([2, 2, 3])
        thing = rng.choice(["coins", "stars", "points"])
        unit_s, unit_p = rng.choice([("day", "Days"), ("round", "Rounds"), ("week", "Weeks")])
        counter = unit_s + "s"
        verb = {2: "double", 3: "triple"}[mult]
        solution = _lines(
            f"{counter} = 0",
            f"while {thing} < goal:",
            f"    {thing} = {thing} * {mult}",
            f"    {counter} += 1",
            f'print("{unit_p}:", {counter})',
        )

        def passes(c, g):
            k = 0
            while c < g:
                c, k = c * mult, k + 1
            return k

        data = [(1, 100), (3, 20), (5, 5), (10, 15), (2, 33), (1, 1)]
        cases = [Case(vars={thing: c, "goal": g}, out=f"{unit_p}: {passes(c, g)}") for c, g in data]
        prompt = (
            f"The variables `{thing}` and `goal` are already set. Every {unit_s} the {thing} {verb} (multiply by {mult}). "
            f"Use a `while` loop to find how many {counter} pass until `{thing}` is at least `goal`, then print `{unit_p}: ` and that number."
        )
        why = f"Start a counter at 0. While {thing} is still below goal, multiply it by {mult} and add 1 to the counter. Print the counter after the loop; if {thing} is already enough, the answer is 0."
    elif kind == "save":
        thing = rng.choice(["money", "money", "coins"])
        solution = _lines("weeks = 0", f"while {thing} < goal:", f"    {thing} += weekly", "    weeks += 1", 'print("Weeks:", weeks)')

        def weeks(m, w, g):
            k = 0
            while m < g:
                m, k = m + w, k + 1
            return k

        data = [(0, 10, 35), (50, 10, 50), (5, 5, 6), (0, 7, 21), (12, 4, 30), (3, 8, 2)]
        cases = [Case(vars={thing: m, "weekly": w, "goal": g}, out=f"Weeks: {weeks(m, w, g)}") for m, w, g in data]
        prompt = (
            f"The variables `{thing}`, `weekly` and `goal` are already set. Each week `weekly` is added to `{thing}`. "
            f"Use a `while` loop to find how many weeks until `{thing}` is at least `goal`, then print `Weeks: ` and that number."
        )
        why = f"Start a week counter at 0. While {thing} is still below goal, add weekly and add 1 to the counter. If it is already enough, the answer is 0."
    else:
        fuel, use, unit, counter, label = rng.choice(
            [
                ("fuel", "use", "launch", "launches", "Launches:"),
                ("energy", "cost", "move", "moves", "Moves:"),
                ("money", "price", "snack", "snacks", "Snacks:"),
            ]
        )
        solution = _lines(
            f"{counter} = 0",
            f"while {fuel} >= {use}:",
            f"    {fuel} -= {use}",
            f"    {counter} += 1",
            f'print("{label}", {counter})',
        )
        data = [(100, 30), (10, 10), (5, 10), (90, 30), (47, 5), (0, 4)]
        cases = [Case(vars={fuel: f, use: u}, out=f"{label} {f // u}") for f, u in data]
        prompt = (
            f"The variables `{fuel}` and `{use}` are already set. Each {unit} uses `{use}` of `{fuel}` and you can't go below 0. "
            f"Use a `while` loop to count how many {counter} are possible, then print `{label}` and that number."
        )
        why = f"Keep going while there is still enough: `{fuel} >= {use}`. Each pass subtracts {use} and adds 1 to the counter. Print the counter after the loop."
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(topic=TOPIC, difficulty=HARD, prompt=prompt, task=task, explanation=why)


_ROUND_STORIES = [
    ("rounds_to_reach", "A player earns 1 point in round 1, 2 points in round 2, 3 points in round 3, and so on.", "rounds"),
    ("days_to_reach", "A coin collector gets 1 coin on day 1, 2 coins on day 2, 3 coins on day 3, and so on.", "days"),
    ("levels_needed", "Level 1 gives 1 star, level 2 gives 2 stars, level 3 gives 3 stars, and so on.", "levels"),
    ("laps_needed", "Lap 1 earns 1 point, lap 2 earns 2 points, lap 3 earns 3 points, and so on.", "laps"),
    ("weeks_to_save", "You save 1 coin in week 1, 2 coins in week 2, 3 coins in week 3, and so on.", "weeks"),
    ("matches_needed", "Match 1 gives 1 elimination, match 2 gives 2, match 3 gives 3, and so on.", "matches"),
]


@generator(TOPIC, HARD, qtype="code")
def gen_code_numbers_needed(rng: random.Random) -> Question:
    """How many terms of 1 + 2 + 3 + ... are needed to reach a goal (accumulator + counter)."""
    fn, story, unit = rng.choice(_ROUND_STORIES)
    arg = rng.choice(["goal", "target", "limit"])
    solution = _lines(
        f"def {fn}({arg}):",
        "    total = 0",
        "    count = 0",
        f"    while total < {arg}:",
        "        count += 1",
        "        total += count",
        "    return count",
    )

    def need(g):
        total = count = 0
        while total < g:
            count += 1
            total += count
        return count

    cases = [((g,), need(g)) for g in (10, 11, 1, 0, 15, 16, 100)]
    task = function_task(fn, solution, cases, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"{story} Write a function `{fn}({arg})` that uses a `while` loop and returns how many {unit} it takes for the total to reach at least `{arg}`.",
        task=task,
        explanation=f"Keep a running total and a counter. While the total is below {arg}: add 1 to the counter and add the counter to the total. Return the counter after the loop. If {arg} is 0, no {unit} are needed.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_guess_game(rng: random.Random) -> Question:
    """A guessing loop: ask until right, hint on each miss, count the tries."""
    low, high = rng.choice([("Too low", "Too high"), ("Higher", "Lower"), ("Go higher", "Go lower"), ("Too small", "Too big")])
    end = rng.choice(["Correct! Tries:", "You got it! Tries:", "Found it! Guesses:"])
    solution = _lines(
        "tries = 0",
        "guess = 0",
        "while guess != secret:",
        '    guess = int(input("Guess: "))',
        "    tries += 1",
        "    if guess < secret:",
        f'        print("{low}")',
        "    elif guess > secret:",
        f'        print("{high}")',
        f'print("{end}", tries)',
    )
    data = [(7, [7]), (7, [3, 9, 7]), (12, [20, 15, 10, 12]), (50, [25, 75, 60, 50]), (4, [1, 2, 3, 4])]

    def out(secret, guesses):
        rows = [low if g < secret else high for g in guesses if g != secret]
        return _lines_out([*rows, f"{end} {len(guesses)}"])

    cases = [Case(vars={"secret": s}, stdin=[str(g) for g in gs], out=out(s, gs)) for s, gs in data]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"The variable `secret` is already set. Write a program that keeps asking for guesses (`input()` then `int()`). After a wrong guess print `{low}` if it is under the secret or `{high}` if it is over. When the guess is right, print `{end} ` and the number of guesses.",
        task=task,
        explanation="Count a try on every pass. Loop while the guess is not the secret; inside, read the guess, add 1 to tries, and print the right hint. Print the tries after the loop.",
    )


# ---- more programs ---------------------------------------------------------------


@generator(TOPIC, EASY, qtype="code")
def gen_code_blastoff_fixed(rng: random.Random) -> Question:
    """Bingo: 'countdown from 5 to 1 and print Blastoff!' with the start value preset."""
    var = rng.choice(["start", "num", "count", "number"])
    finale = rng.choice(_FINALES)
    solution = _lines(f"while {var} >= 1:", f"    print({var})", f"    {var} -= 1", f'print("{finale}")')
    cases = [Case(vars={var: n}, out=_lines_out([*range(n, 0, -1), finale])) for n in (5, 3, 1, 7, 0)]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=EASY,
        prompt=f"The variable `{var}` is already set to a whole number (0 or more). Write a `while` loop that counts down from `{var}` to 1, one number per line, and then prints `{finale}`.",
        task=task,
        explanation=f"Loop while `{var} >= 1`: print it, then subtract 1. The final `print(\"{finale}\")` is not indented, so it runs once after the loop. If {var} is 0 only `{finale}` prints.",
    )


@generator(TOPIC, MEDIUM, qtype="code")
def gen_code_validate(rng: random.Random) -> Question:
    """Keep asking until the answer is valid (repeated input is the lesson's reason for `while`)."""
    kind = rng.choice(["positive", "range", "teen", "yes_no"])
    retry = rng.choice(["Try again.", "Try again.", "Not valid.", "Please retry."])
    if kind == "positive":
        what = "Keep asking until the number is greater than 0"
        ok = "You entered:"
        solution = _lines(
            'num = int(input("Enter a positive number: "))',
            "while num <= 0:",
            f'    print("{retry}")',
            '    num = int(input("Enter a positive number: "))',
            f'print("{ok}", num)',
        )
        scripts = [["5"], ["-3", "0", "4"], ["0", "1"], ["-1", "-2", "-3", "9"], ["12"]]
        ask = "a number (use `input()` and `int()`)"
        why = "Ask once before the loop, and again inside it. Loop while the number is NOT valid (`num <= 0`)."
    elif kind == "range":
        low, high = rng.choice([(1, 10), (1, 5), (1, 100), (0, 3)])
        what = f"Keep asking until the number is from {low} to {high} (including both ends)"
        ok = "You picked"
        solution = _lines(
            f'num = int(input("Pick a number from {low} to {high}: "))',
            f"while num < {low} or num > {high}:",
            f'    print("{retry}")',
            f'    num = int(input("Pick a number from {low} to {high}: "))',
            f'print("{ok}", num)',
        )
        scripts = [[str(low + 1)], [str(low - 1), str(high + 1), str(high)], [str(low)], [str(high)], ["-4", str(high + 7), str(low)]]
        ask = "a number (use `input()` and `int()`)"
        why = f"The loop must continue while the number is NOT valid: below {low} OR above {high}. Use `or` (a number can't be both)."
    elif kind == "teen":
        what = "Keep asking until the age is from 13 to 19 (including both ends)"
        ok = "Welcome, teen! Age:"
        solution = _lines(
            'age = int(input("Enter your age: "))',
            "while age < 13 or age > 19:",
            f'    print("{retry}")',
            '    age = int(input("Enter your age: "))',
            f'print("{ok}", age)',
        )
        scripts = [["15"], ["12", "20", "13"], ["19"], ["13"], ["5", "40", "99", "17"]]
        ask = "an age (use `input()` and `int()`)"
        why = "The loop continues while the age is NOT in the range: under 13 OR over 19. (`while not 13 <= age <= 19` works too.)"
    else:
        ok = "You said:"
        solution = _lines(
            'answer = input("Continue? (yes/no): ")',
            'while answer != "yes" and answer != "no":',
            f'    print("{retry}")',
            '    answer = input("Continue? (yes/no): ")',
            f'print("{ok}", answer)',
        )
        what = "Keep asking until the answer is exactly `yes` or `no`"
        scripts = [["yes"], ["maybe", "no"], ["Yes", "YES", "no"], ["ok", "sure", "yes"], ["no"]]
        ask = "a yes/no answer (use `input()` only, no `int()`)"
        why = 'Loop while the answer is NOT yes AND NOT no: `answer != "yes" and answer != "no"`. Using `or` here would be True for every answer.'
    cases = [Case(stdin=s, out=_lines_out([*([retry] * (len(s) - 1)), f"{ok} {s[-1]}"])) for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=MEDIUM,
        prompt=f"Write a program that asks the player for {ask}. {what}: print `{retry}` after each invalid answer. When the answer is valid, print `{ok} ` followed by the answer.",
        task=task,
        explanation=why,
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_count_multiples(rng: random.Random) -> Question:
    """`while` + `if` + `%`: count (or add up) the numbers from 1 to `limit` that divide evenly."""
    k = rng.choice([2, 3, 4, 5, 7])
    kind = rng.choice(["count", "sum"])
    label = rng.choice(["Multiples:", "Found:"]) if kind == "count" else rng.choice(["Total:", "Sum:"])
    solution = _lines(
        "count = 1",
        "answer = 0",
        "while count <= limit:",
        f"    if count % {k} == 0:",
        "        answer += 1" if kind == "count" else "        answer += count",
        "    count += 1",
        f'print("{label}", answer)',
    )
    limits = [10, 20, 1, 0, 7, 30, 14]
    cases = [
        Case(
            vars={"limit": lim},
            out=f"{label} {sum(1 for i in range(1, lim + 1) if i % k == 0) if kind == 'count' else sum(i for i in range(1, lim + 1) if i % k == 0)}",
        )
        for lim in limits
    ]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    what = "how many of the numbers from 1 to `limit` divide evenly by" if kind == "count" else "the sum of the numbers from 1 to `limit` that divide evenly by"
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=f"The variable `limit` is already set. Use a `while` loop to find {what} {k} (remainder 0 when you use `%`), then print `{label} ` and the answer.",
        task=task,
        explanation=f"Loop `count` from 1 to `limit`. An `if count % {k} == 0:` inside the loop " + ("adds 1 to a counter" if kind == "count" else "adds `count` to a total") + "; the update `count += 1` stays outside the `if`.",
    )


@generator(TOPIC, HARD, qtype="code")
def gen_code_limited_tries(rng: random.Random) -> Question:
    """Password with a limited number of tries: the condition combines `!=` and a tries counter with `and`."""
    secret = rng.choice(_SECRETS)
    k = rng.choice([3, 3, 4])
    wrong = rng.choice(["Wrong", "Nope", "Incorrect"])
    ok = rng.choice(["Access granted!", "Welcome!", "Unlocked!"])
    fail = rng.choice(["Locked out!", "Too many tries!", "Game over"])
    solution = _lines(
        "tries = 0",
        'guess = ""',
        f"while guess != secret and tries < {k}:",
        '    guess = input("Password: ")',
        "    tries += 1",
        "    if guess != secret:",
        f'        print("{wrong}")',
        "if guess == secret:",
        f'    print("{ok}")',
        "else:",
        f'    print("{fail}")',
    )
    bad = ["cat", "123", "abc", "hello", "no"]
    scripts = [
        [secret],
        ["cat", secret],
        [*bad[: k - 1], secret],
        bad[:k],
        [*bad[:k], secret],
        [secret, "cat"],
    ]

    def out(s):
        rows = []
        for i, g in enumerate(s[:k]):
            if g == secret:
                rows.append(ok)
                return _lines_out(rows)
            rows.append(wrong)
        rows.append(fail)
        return _lines_out(rows)

    cases = [Case(vars={"secret": secret}, stdin=s, out=out(s)) for s in scripts]
    task = program_task(solution, cases, starter="", examples=2, requires=_NEED_WHILE)
    return code_question(
        topic=TOPIC,
        difficulty=HARD,
        prompt=(
            f"The variable `secret` is already set. The player gets {k} guesses (ask with `input()`). Print `{wrong}` after each wrong guess. "
            f"If a guess is right, print `{ok}` and stop asking. If all {k} guesses are wrong, print `{fail}` as the last line."
        ),
        task=task,
        explanation=f"Keep a `tries` counter. Loop while the guess is wrong AND `tries < {k}`; inside, ask, add 1 to tries and print the wrong message. After the loop, check whether the last guess was right.",
    )
