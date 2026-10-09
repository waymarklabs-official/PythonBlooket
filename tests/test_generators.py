"""Property tests run against every registered question generator.

Run one topic only with e.g. ``pytest tests/test_generators.py -k "topics.strings"``.

Every format is checked:
  choice  4 distinct choices, one correct, "output" questions re-run the snippet;
  blanks  markers match the blanks, the filled-in snippet really prints what it should;
  match   3-6 items, answers in range;
  code    the reference solution passes every case *in the real sandbox*, the starter
          alone does not, and nothing secret is in the public dict.
"""

from __future__ import annotations

import random

import pytest

from pyblooket.questions import COURSE_TOPICS, TOPICS, load_generators
from pyblooket.questions.base import (
    DIFFICULTIES,
    MAX_CHOICE_LINE_LEN,
    MAX_CHOICE_LINES,
    NUM_CHOICES,
    QTYPES,
    REGISTRY,
    Question,
    display_output,
    error_choice,
    fill_template,
    run_code,
)
from pyblooket.questions.spec import BLANK_MARK_RE
from pyblooket.sandbox import grade_task

SEEDS = range(150)
CODE_SEEDS = range(12)  # each one runs the sandbox (~30 ms) several times
MIN_GENERATORS_PER_LEVEL = 3
MAX_DISPLAY_LINES = 18

load_generators()
GENS = list(REGISTRY)
IDS = [g.name for g in GENS]
CODE_GENS = [g for g in GENS if g.qtype == "code"]


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip("\n").split("\n"))


def _signature(q: Question):
    """Everything that makes two questions 'the same question'."""
    return (
        q.qtype,
        q.prompt,
        q.code,
        tuple(q.choices),
        q.answer,
        tuple(tuple(b.accepted) for b in q.blanks),
        None if q.match is None else (tuple(q.match.items), tuple(q.match.options), tuple(q.match.answer)),
        None if q.task is None else (q.task.starter, q.task.solution, tuple(c.label for c in q.task.cases)),
    )


def _check_common(q: Question, gen, ctx: str):
    assert isinstance(q, Question), ctx
    assert q.topic == gen.topic, ctx
    assert q.difficulty == gen.difficulty, ctx
    assert q.qtype == gen.qtype, f"{ctx}: generator registered as {gen.qtype} but made {q.qtype}"
    assert q.prompt.strip(), ctx
    assert q.explanation.strip(), ctx
    if q.code is not None:
        assert len(q.code.split("\n")) <= MAX_DISPLAY_LINES, f"snippet too long: {ctx}"


def _check_choice(q: Question, ctx: str):
    assert len(q.choices) == NUM_CHOICES, ctx
    assert len({_norm(c) for c in q.choices}) == NUM_CHOICES, f"duplicate choices: {ctx}"
    assert 0 <= q.answer < NUM_CHOICES, ctx
    for c in q.choices:
        lines = c.split("\n")
        assert len(lines) <= MAX_CHOICE_LINES, ctx
        assert all(len(line) <= MAX_CHOICE_LINE_LEN for line in lines), ctx
    if q.code is not None:
        compile(q.code, "<snippet>", "exec")
    if q.kind == "output":
        res = run_code(q.code)
        expected = error_choice(res.error) if res.error else display_output(res.output)
        assert _norm(q.choices[q.answer]) == _norm(expected), ctx


def _check_blanks(q: Question, ctx: str):
    assert q.code and 1 <= len(q.blanks) <= 4, ctx
    marks = sorted(int(m) for m in BLANK_MARK_RE.findall(q.code))
    assert marks == list(range(1, len(q.blanks) + 1)), f"bad markers {marks}: {ctx}"
    for b in q.blanks:
        assert b.accepted and all(a.strip() for a in b.accepted), ctx
        assert b.check(b.accepted[0]), ctx
        assert not b.check(""), ctx
    filled = fill_template(q.code, [b.accepted[0] for b in q.blanks])
    if q.expect_output is not None:
        res = run_code(filled)
        assert not res.error, f"filled snippet raised {res.error}: {ctx}"
        assert _norm(res.output) == _norm(q.expect_output), ctx
    assert q.grade([b.accepted[0] for b in q.blanks]).correct, ctx
    assert not q.grade(["zzz-not-it"] * len(q.blanks)).correct, ctx
    public = q.public_dict()
    assert len(public["blanks"]) == len(q.blanks), ctx
    assert all("accepted" not in b for b in public["blanks"]), ctx


def _check_match(q: Question, ctx: str):
    m = q.match
    assert m is not None and 3 <= len(m.items) <= 6 and 2 <= len(m.options) <= 6, ctx
    assert len(set(m.items)) == len(m.items), ctx
    assert q.grade(list(m.answer)).correct, ctx
    wrong = [(a + 1) % len(m.options) for a in m.answer]
    assert not q.grade(wrong).correct, ctx
    assert "answer" not in q.public_dict()["match"], ctx


def _check_code(q: Question, ctx: str):
    t = q.task
    assert t is not None, ctx
    assert len(t.cases) >= (2 if t.mode == "program" else 3), f"too few test cases: {ctx}"
    assert t.starter is not None and t.solution.strip(), ctx
    public = q.public_dict()
    blob = repr(public)
    assert t.solution not in blob, f"solution leaked: {ctx}"
    assert len(public["task"]["examples"]) == t.examples <= len(t.cases), ctx
    verdict = grade_task(t, t.solution)
    assert verdict["status"] == "ok" and verdict["correct"], f"{ctx}: reference solution failed: {verdict}"
    assert not grade_task(t, t.starter)["correct"], f"{ctx}: the starter code already passes"


CHECKS = {"choice": _check_choice, "blanks": _check_blanks, "match": _check_match, "code": _check_code}


@pytest.mark.parametrize("gen", GENS, ids=IDS)
def test_generator_produces_valid_questions(gen):
    seeds = CODE_SEEDS if gen.qtype == "code" else SEEDS
    for seed in seeds:
        q = gen.fn(random.Random(seed))
        ctx = f"{gen.name} seed={seed}"
        _check_common(q, gen, ctx)
        CHECKS[gen.qtype](q, ctx)


@pytest.mark.parametrize("gen", GENS, ids=IDS)
def test_generator_is_deterministic(gen):
    for seed in range(5):
        assert _signature(gen.fn(random.Random(seed))) == _signature(gen.fn(random.Random(seed)))


@pytest.mark.parametrize("gen", GENS, ids=IDS)
def test_generator_varies(gen):
    seen = {_signature(gen.fn(random.Random(s))) for s in SEEDS}
    assert len(seen) >= 8, f"{gen.name} only produced {len(seen)} distinct questions"


@pytest.mark.parametrize("topic", list(TOPICS))
def test_topic_has_generators_at_every_difficulty(topic):
    if not any(g.topic == topic for g in GENS):
        pytest.skip(f"topic {topic} has no generators yet")
    for d in DIFFICULTIES:
        n = sum(1 for g in REGISTRY if g.topic == topic and g.difficulty == d)
        assert n >= MIN_GENERATORS_PER_LEVEL, f"{topic} has {n} generators at difficulty {d}"


@pytest.mark.parametrize("topic", list(COURSE_TOPICS))
def test_lesson_topics_have_typed_questions(topic):
    """Every lesson topic must make the players type something (and keep plenty of choice)."""
    by_type = {t: sum(1 for g in REGISTRY if g.topic == topic and g.qtype == t) for t in QTYPES}
    if sum(by_type.values()) == 0:
        pytest.skip(f"topic {topic} has no generators yet")
    if topic == "challenges":
        assert by_type["code"] >= 9, by_type
        return
    assert by_type["choice"] >= 4, by_type
    assert by_type["code"] >= 2, by_type
    assert by_type["blanks"] + by_type["match"] >= 1, by_type


def test_correct_answer_positions_are_balanced():
    counts = [0] * NUM_CHOICES
    for gen in GENS:
        if gen.qtype != "choice":
            continue
        for seed in range(40):
            counts[gen.fn(random.Random(seed)).answer] += 1
    total = sum(counts)
    for c in counts:
        assert c > total / NUM_CHOICES * 0.7, counts
