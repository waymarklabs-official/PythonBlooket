"""The sandbox that grades typed code: right answers pass, wrong ones fail kindly, and
hostile ones are contained.  (Every test here starts a real sandbox process.)"""

from __future__ import annotations

import random
import time

import pytest

from pyblooket.questions.base import (
    Question,
    code_question,
    expression_task,
    fn_cases,
    function_task,
    program_task,
    GenerationError,
    EASY,
)
from pyblooket.questions.spec import Case, CodeTask
from pyblooket.sandbox import code_skeleton, grade_task

AVERAGE = function_task(
    "average",
    "def average(a, b, c):\n    return (a + b + c) / 3",
    fn_cases([((2, 4, 6), 4.0), ((1, 2, 4), 7 / 3), ((0, 0, 0), 0.0)]),
)


def grade(task, code, **kw):
    return grade_task(task, code, **kw)


# -- function mode ---------------------------------------------------------


def test_function_correct():
    r = grade(AVERAGE, AVERAGE.solution)
    assert r["status"] == "ok" and r["correct"] and r["passed"] == r["total"] == 3
    assert [c["hidden"] for c in r["cases"]] == [False, False, True]


def test_function_wrong_result_is_reported():
    r = grade(AVERAGE, "def average(a, b, c):\n    return (a + b + c) // 3")
    assert not r["correct"] and r["passed"] == 0
    assert r["cases"][0]["got"] == "4" and r["cases"][0]["expected"] == "4.0"


def test_int_and_float_are_different_unless_lenient():
    strict = function_task("f", "def f(n):\n    return n * 2", fn_cases([((2,), 4), ((3,), 6), ((5,), 10)]))
    assert grade(strict, "def f(n):\n    return n * 2.0")["passed"] == 0
    lenient = function_task("f", "def f(n):\n    return n * 2", fn_cases([((2,), 4), ((3,), 6), ((5,), 10)]), lenient=True)
    assert grade(lenient, "def f(n):\n    return n * 2.0")["correct"]


def test_bool_is_not_int():
    t = function_task("f", "def f(n):\n    return n > 1", fn_cases([((2,), True), ((0,), False), ((5,), True)]))
    assert not grade(t, "def f(n):\n    return 1 if n > 1 else 0")["correct"]
    assert grade(t, t.solution)["correct"]


def test_wrong_function_name():
    r = grade(AVERAGE, "def avg(a, b, c):\n    return 1")
    assert not r["correct"] and "no function named 'average'" in r["cases"][0]["error"]


def test_printing_function():
    t = function_task(
        "greet_person",
        'def greet_person(name):\n    print(f"Hello, {name}")',
        [Case(args=["Sarah"], out="Hello, Sarah"), Case(args=["Ben"], out="Hello, Ben"), Case(args=["Ada"], out="Hello, Ada")],
    )
    assert grade(t, t.solution)["correct"]
    # a stray call at module level must not count as the function's output
    assert grade(t, t.solution + '\ngreet_person("Sarah")')["correct"]
    assert not grade(t, 'def greet_person(name):\n    return f"Hello, {name}"')["correct"]


def test_each_case_gets_a_fresh_namespace():
    t = function_task("bump", "def bump():\n    return 1", [Case(args=[], ret=1)] * 3)
    code = "count = 0\ndef bump():\n    global count\n    count += 1\n    return count"
    assert grade(t, code)["correct"]


# -- program mode ----------------------------------------------------------


def test_program_with_input():
    t = program_task(
        'n = int(input("Enter a number: "))\nprint(n * 2)',
        [Case(stdin=["4"], out="8"), Case(stdin=["-3"], out="-6"), Case(stdin=["0"], out="0")],
    )
    assert grade(t, t.solution)["correct"]
    assert grade(t, 'x = int(input())\nprint(x * 2)')["correct"]  # the prompt text is not graded
    assert not grade(t, "n = input()\nprint(n * 2)")["correct"]  # '4' * 2 == '44'


def test_program_output_ignores_trailing_whitespace():
    t = program_task('print("hi")', [Case(out="hi"), Case(out="hi")])
    assert grade(t, 'print("hi   ")\nprint()')["correct"]
    assert not grade(t, 'print("Hi")')["correct"]


def test_program_asking_for_too_much_input():
    t = program_task("print(input())", [Case(stdin=["a"], out="a"), Case(stdin=["b"], out="b")])
    r = grade(t, "print(input())\nprint(input())")
    assert not r["correct"] and "EOFError" in r["cases"][0]["error"]


def test_expect_vars():
    t = program_task("age = 15", [Case(expect_vars={"age": 15}), Case(expect_vars={"age": 15})])
    assert grade(t, "age = 15")["correct"]
    assert not grade(t, "age = '15'")["correct"]
    r = grade(t, "agee = 15")
    assert not r["correct"] and "never created" in r["cases"][0]["got"]


def test_preset_vars():
    t = program_task(
        'if age >= 16:\n    print("Can drive")\nelse:\n    print("Too young")',
        [Case(vars={"age": 15}, out="Too young"), Case(vars={"age": 16}, out="Can drive"), Case(vars={"age": 40}, out="Can drive")],
    )
    assert grade(t, t.solution)["correct"]
    assert not grade(t, 'print("Can drive")')["correct"]


# -- expression mode -------------------------------------------------------


def test_expression():
    t = expression_task("word[0:4]", [({"word": "Python"}, "Pyth"), ({"word": "Blooket"}, "Bloo"), ({"word": "snake"}, "snak")])
    assert grade(t, "word[:4]")["correct"]
    assert grade(t, "  word[0:4]  ")["correct"]
    assert not grade(t, "word[0:3]")["correct"]
    assert not grade(t, '"Pyth"')["correct"]  # hard-coding fails the other cases
    r = grade(t, "x = 1")
    assert r["status"] == "syntax_error" and "single expression" in r["message"]


# -- messages --------------------------------------------------------------


def test_syntax_error_message():
    r = grade(AVERAGE, "def average(a, b, c)\n    return 1")
    assert r["status"] == "syntax_error" and "line 1" in r["message"]


def test_runtime_error_has_line_number():
    r = grade(AVERAGE, "def average(a, b, c):\n    return total / 3")
    assert "NameError" in r["cases"][0]["error"] and "line 2" in r["cases"][0]["error"]


def test_empty_answer():
    assert grade(AVERAGE, "   ")["status"] == "empty"


def test_run_only_examples():
    r = grade(AVERAGE, AVERAGE.solution, only_examples=True)
    assert r["total"] == 2 and len(r["cases"]) == 2


# -- requirements ------------------------------------------------------------


def test_requires_and_forbids():
    t = function_task(
        "biggest",
        "def biggest(a, b, c):\n    if a >= b and a >= c:\n        return a\n    if b >= c:\n        return b\n    return c",
        fn_cases([((1, 2, 3), 3), ((9, 2, 3), 9), ((1, 8, 3), 8)]),
        forbids=[(r"\bmax\s*\(", "Don't use max() - use if statements")],
    )
    assert grade(t, t.solution)["correct"]
    r = grade(t, "def biggest(a, b, c):\n    return max(a, b, c)")
    assert not r["correct"] and r["status"] == "requirements" and "max()" in r["message"]
    # mentioning it in a comment or string is fine
    ok = t.solution + '\n# not using max() here\nnote = "max("'
    assert grade(t, ok)["correct"]
    assert "max" not in code_skeleton('x = "max(" # max(')


# -- containment ---------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "import os\ndef average(a,b,c): return 1",
        "from os import system\ndef average(a,b,c): return 1",
        "def average(a,b,c):\n    return __import__('os')",
        "def average(a,b,c):\n    return average.__globals__",
        "def average(a,b,c):\n    return ().__class__.__bases__[0].__subclasses__()",
        "def average(a,b,c):\n    return print.__closure__",
        "def average(a,b,c):\n    return '{0.__globals__}'.format(print)",
        "def average(a,b,c):\n    return '{}'.format_map({})",
        "def average(a,b,c):\n    yield 1",
        "def average(a,b,c):\n    return (x for x in [1]).gi_frame",
        "def average(a,b,c):\n    return __builtins__",
        "def average(a,b,c):\n    return f'{print.__globals__}'",
        "def average(a,b,c):\n    return int.mro()",
    ],
)
def test_rejects_dangerous_code(code):
    r = grade(AVERAGE, code)
    assert r["status"] == "rejected" and not r["correct"], r


@pytest.mark.parametrize(
    "code",
    [
        "def average(a,b,c):\n    return open('/etc/passwd').read()",
        "def average(a,b,c):\n    return eval('1+1')",
        "def average(a,b,c):\n    return exec('x=1')",
        "def average(a,b,c):\n    return getattr(print, 'x')",
        "def average(a,b,c):\n    return globals()",
        "def average(a,b,c):\n    exit()",
        "def average(a,b,c):\n    return compile('1', 'x', 'eval')",
        "def average(a,b,c):\n    return type('X', (), {})",
    ],
)
def test_missing_builtins_just_fail(code):
    r = grade(AVERAGE, code)
    assert not r["correct"] and r["status"] == "ok"
    assert all(c["error"] for c in r["cases"]), r


def test_infinite_loop_is_stopped():
    t0 = time.time()
    r = grade(AVERAGE, "def average(a,b,c):\n    while True:\n        pass")
    assert r["status"] == "timeout" and not r["correct"]
    assert time.time() - t0 < 8


def test_loop_swallowing_exceptions_is_still_stopped():
    t0 = time.time()
    code = "def average(a,b,c):\n    while True:\n        try:\n            while True:\n                pass\n        except BaseException:\n            pass"
    r = grade(AVERAGE, code)
    assert r["status"] == "timeout" and not r["correct"]
    assert time.time() - t0 < 14


def test_print_flood_is_stopped():
    r = grade(AVERAGE, "def average(a,b,c):\n    while True:\n        print('spam' * 100)")
    assert not r["correct"] and "too much" in (r["cases"][0]["error"] or "")


def test_memory_bomb_is_contained():
    r = grade(AVERAGE, "def average(a,b,c):\n    x = []\n    while True:\n        x.append('a' * 10**7)")
    assert not r["correct"]


def test_deep_recursion_is_an_error_not_a_crash():
    r = grade(AVERAGE, "def average(a,b,c):\n    return average(a,b,c)")
    assert not r["correct"] and "RecursionError" in r["cases"][0]["error"]


def test_student_cannot_forge_a_result():
    code = 'def average(a,b,c):\n    print("@@RESULT@@ {\\"status\\": \\"ok\\"}")\n    return 4.0'
    r = grade(AVERAGE, code)
    assert r["passed"] == 1 and not r["correct"]  # only the first case really returns 4.0


def test_too_long_answer():
    r = grade(AVERAGE, "x = 1\n" * 5000)
    assert r["status"] == "rejected"


def test_class_definitions_work():
    t = function_task(
        "area_of",
        "class Square:\n    def __init__(self, side):\n        self.side = side\n\n    def area(self):\n        return self.side * self.side\n\n\ndef area_of(side):\n    return Square(side).area()",
        fn_cases([((2,), 4), ((3,), 9), ((5,), 25)]),
    )
    assert grade(t, t.solution)["correct"]


def test_type_builtin_with_one_argument():
    t = expression_task("type(x) == int", [({"x": 3}, True), ({"x": "3"}, False), ({"x": 2.5}, False)])
    assert grade(t, t.solution)["correct"]
    t2 = expression_task("type(x)", [({"x": 3}, int)] if False else [({"x": 3}, True)] * 3)
    assert not grade(t2, "type('X', (), {})")["correct"]


# -- the builders refuse inconsistent questions ------------------------------------


def test_selfcheck_rejects_a_wrong_reference_solution():
    bad = function_task("f", "def f(n):\n    return n + 1", fn_cases([((1,), 2), ((2,), 4), ((3,), 4)]))
    with pytest.raises(GenerationError):
        code_question(topic="functions", difficulty=EASY, prompt="p", task=bad, explanation="e")


def test_selfcheck_rejects_a_solution_the_sandbox_would_refuse():
    bad = function_task("f", "def f(n):\n    return '{}'.format(n)", fn_cases([((1,), "1"), ((2,), "2"), ((3,), "3")]))
    with pytest.raises(GenerationError):
        code_question(topic="functions", difficulty=EASY, prompt="p", task=bad, explanation="e")


def test_code_question_grades_through_question_object():
    q = code_question(topic="functions", difficulty=EASY, prompt="Write average", task=AVERAGE, explanation="e")
    assert q.qtype == "code" and q.time_factor > 1
    assert q.grade(AVERAGE.solution).correct
    assert not q.grade("def average(a, b, c): return 0").correct
    assert not q.grade(None).correct
    assert q.run_examples(AVERAGE.solution)["total"] == 2
    assert q.reveal() == {"solution": AVERAGE.solution}
    assert "solution" not in repr(q.public_dict())


def test_hidden_harness_tests_a_class():
    solution = "class Triangle:\n    def __init__(self, base, height):\n        self.base = base\n        self.height = height\n\n    def area(self):\n        return self.base * self.height / 2"
    t = program_task(
        solution,
        [
            Case(label="Triangle(4, 3).area()", after="print(Triangle(4, 3).area())", out="6.0"),
            Case(label="Triangle(10, 5).area()", after="t = Triangle(10, 5)\nprint(t.area())", out="25.0"),
            Case(label="Triangle(1, 1).area()", after="print(Triangle(1, 1).area())", out="0.5"),
        ],
    )
    q = code_question(topic="classes", difficulty=EASY, prompt="p", task=t, explanation="e")
    assert q.grade(solution).correct
    wrong = solution.replace(" / 2", "")
    assert not q.grade(wrong).correct
    r = grade(t, "class Square:\n    pass")
    assert not r["correct"] and "Triangle" in r["cases"][0]["error"]
