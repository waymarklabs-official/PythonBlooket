"""Hosted games: the rules (games.py, with a fake clock and injected questions) and the HTTP
layer (hosting.py, through the Flask test client).  One test per group grades typed code in
the real sandbox."""

from __future__ import annotations

import csv
import io
import itertools
import json
import random
import threading

import pytest

from app import app
from pyblooket import games, hosting, sandbox
from pyblooket.games import GameError, GameStore
from pyblooket.questions.base import (
    GenerationError,
    blanks_question,
    build_question,
    code_question,
    fn_cases,
    function_task,
    match_question,
)
from pyblooket.questions.spec import Blank

T0 = 1_000_000.0
DOUBLE = function_task("double", "def double(n):\n    return n * 2", fn_cases([((2,), 4), ((3,), 6), ((5,), 10)]))
GOOD_CODE = "def double(n):\n    return n * 2"
BAD_CODE = "def double(n):\n    return n + 1"


class Clock:
    def __init__(self, t: float = T0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> float:
        self.t += seconds
        return self.t


# -- question builders ---------------------------------------------------------------------


def choice_q(n: int = 0, difficulty: int = 1):
    return build_question(
        topic="variables",
        difficulty=difficulty,
        prompt=f"Pick number {n}",
        correct=f"right{n}",
        distractors=["w1", "w2", "w3"],
        explanation=f"EXPLAIN_{n}",
        rng=random.Random(n),
    )


def blanks_q(n: int = 0, difficulty: int = 2):
    return blanks_question(
        topic="variables",
        difficulty=difficulty,
        prompt=f"Fill it in {n}",
        template="x = ⟦1⟧\nprint(x)",
        blanks=[Blank(["5"])],
        explanation=f"EXPLAIN_{n}",
        expect_output="5",
    )


def match_q(n: int = 0, difficulty: int = 1):
    return match_question(
        topic="datatypes",
        difficulty=difficulty,
        prompt=f"Match them {n}",
        pairs=[("1", "int"), ("'a'", "str"), ("2", "int")],
        explanation=f"EXPLAIN_{n}",
        rng=random.Random(n),
    )


def code_q(n: int = 0, difficulty: int = 1):
    return code_question(
        topic="functions",
        difficulty=difficulty,
        prompt=f"Write double {n}",
        task=DOUBLE,
        explanation=f"EXPLAIN_{n}",
    )


class Pool:
    """A question factory (same call shape as generate_question) that serves a fixed list in order."""

    def __init__(self, questions):
        self.questions = list(questions)
        self.calls = 0

    def __call__(self, topics=None, difficulty=None, rng=None, types=None):
        q = self.questions[self.calls % len(self.questions)]
        self.calls += 1
        return q


class Endless:
    """An endless supply of distinct easy choice questions."""

    def __init__(self, difficulty: int = 1):
        self.n = itertools.count()
        self.difficulty = difficulty
        self.args: list = []

    def __call__(self, topics=None, difficulty=None, rng=None, types=None):
        self.args.append((topics, difficulty, types))
        return choice_q(next(self.n), self.difficulty)


def make_store(factory, clock=None, **kw):
    kw.setdefault("code_enabled", True)
    return GameStore(question_factory=factory, clock=clock or Clock(), rng=random.Random(7), **kw)


def live_settings(**kw):
    return {"mode": "live", "question_count": 4, **kw}


def right(q):
    """A correct response for a (non-code) question."""
    if q.qtype == "choice":
        return q.answer
    if q.qtype == "blanks":
        return [b.accepted[0] for b in q.blanks]
    if q.qtype == "match":
        return list(q.match.answer)
    return q.task.solution


def wrong(q):
    if q.qtype == "choice":
        return (q.answer + 1) % len(q.choices)
    if q.qtype == "blanks":
        return ["nope"] * len(q.blanks)
    if q.qtype == "match":
        return [(a + 1) % len(q.match.options) for a in q.match.answer]
    return BAD_CODE


def qid_of(state):
    return state["question"]["id"]


def err_reason(fn, *args, **kw):
    with pytest.raises(GameError) as info:
        fn(*args, **kw)
    return info.value.reason


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "qtype,expected",
    [
        ("choice", (15, 20, 25)),
        ("match", (30, 40, 50)),
        ("blanks", (30, 40, 50)),
        ("code", (90, 120, 180)),
    ],
)
def test_time_limits_normal(qtype, expected):
    assert tuple(games.time_limit(qtype, d) for d in (1, 2, 3)) == expected


def test_time_limits_scaled_round_up_to_five():
    assert [games.time_limit("choice", d, "short") for d in (1, 2, 3)] == [15, 15, 20]  # 10.5, 14, 17.5
    assert [games.time_limit("choice", d, "long") for d in (1, 2, 3)] == [25, 30, 40]  # 22.5, 30, 37.5
    assert [games.time_limit("code", d, "short") for d in (1, 2, 3)] == [65, 85, 130]  # 63, 84, 126
    assert [games.time_limit("match", d, "long") for d in (1, 2, 3)] == [45, 60, 75]
    for qtype in games.BASE_LIMITS:
        for scale in games.TIME_SCALES:
            assert all(games.time_limit(qtype, d, scale) % 5 == 0 for d in (1, 2, 3))


def test_live_points_formula():
    assert games.live_points(100, 0, 15, 0) == (100, 50, 0)  # instant
    assert games.live_points(100, 15, 15, 0) == (100, 0, 0)  # at the limit
    assert games.live_points(100, 99, 15, 0) == (100, 0, 0)  # clamped
    assert games.live_points(100, -4, 15, 0) == (100, 50, 0)
    assert games.live_points(250, 10, 40, 1) == (250, 94, 25)  # 93.75 -> 94
    assert games.live_points(500, 0, 25, 9) == (500, 250, 250)  # streak capped at 5


def test_rush_points_streak_cap():
    assert games.rush_points(100, 0) == (100, 0, 0)
    assert games.rush_points(100, 3) == (100, 0, 30)
    assert games.rush_points(100, 10) == (100, 0, 100)
    assert games.rush_points(100, 25) == (100, 0, 100)


def test_competition_ranks():
    assert games.competition_ranks([]) == []
    assert games.competition_ranks([0, 0, 0]) == [1, 1, 1]
    assert games.competition_ranks([300, 200, 200, 200, 50]) == [1, 2, 2, 2, 5]
    assert games.competition_ranks([100, 100, 50]) == [1, 1, 3]


def test_name_rules():
    assert games.validate_name("  Ana   Maria ") == "Ana Maria"
    assert games.validate_name("x" * 16) == "x" * 16
    assert games.validate_name("Zoë 🐍") == "Zoë 🐍"
    for bad in ["", "   ", "x" * 17, "bad\x00name", "tab\tname", "new\nline", None, 5, ["a"], "​", "a‮b"]:
        assert err_reason(games.validate_name, bad) == "bad_name", bad


def test_avatar_is_forgiving():
    assert games.clean_avatar("🐍") == "🐍"
    for bad in [None, "", 5, "x" * 9, "\x00"]:
        assert games.clean_avatar(bad) == games.DEFAULT_AVATAR


def test_settings_defaults_and_clamping():
    s = games.public_settings(games.normalize_settings({"mode": "live"}, True))
    assert s == {
        "mode": "live",
        "title": "",
        "topics": [],
        "difficulty": "mixed",
        "types": "mixed",
        "question_count": 10,
        "duration_min": 5,
        "time_scale": "normal",
        "auto_advance": False,
        "max_players": 60,
    }
    s = games.normalize_settings(
        {
            "mode": "rush",
            "title": "  Period\n3  review " + "x" * 80,
            "topics": ["variables", "nope", "variables"],
            "difficulty": "2",
            "types": "typing",
            "question_count": 999,
            "duration_min": 0,
            "max_players": 5000,
        },
        True,
    )
    assert s["title"].startswith("Period 3 review") and len(s["title"]) == games.MAX_TITLE
    assert s["topics"] == ["variables"] and s["difficulty"] == 2 and s["_difficulty"] == 2
    assert (s["question_count"], s["duration_min"], s["max_players"]) == (40, 1, 200)
    assert s["types"] == "typing" and s["_types"] == ["blanks", "code"]
    assert games.normalize_settings({"question_count": 1}, True)["question_count"] == 3


def test_settings_drop_code_when_the_sandbox_is_off():
    assert games.normalize_settings({"types": "typing"}, False)["_types"] == ["blanks"]
    assert games.normalize_settings({"types": ["code"]}, False)["_types"] == ["choice"]
    assert "code" not in games.normalize_settings({"types": "mixed"}, False)["_types"]
    assert games.normalize_settings({"types": "mixed"}, True)["_types"] is None  # None = every format
    assert games.normalize_settings({"types": ["choice", "code"]}, True)["_types"] == ["choice", "code"]


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        "live",
        {"mode": "zoom"},
        {"topics": "variables", "difficulty": 9},
        {"topics": ["nope"]},
        {"topics": [1]},
        {"question_count": "many"},
        {"question_count": True},
        {"time_scale": "forever"},
        {"auto_advance": "yes"},
        {"difficulty": "brutal"},
        {"types": 5},
    ],
)
def test_settings_rejects_nonsense(body):
    assert err_reason(games.normalize_settings, body, True) == "bad_request"


def test_csv_safe():
    assert games.csv_safe("=1+1") == "'=1+1"
    assert games.csv_safe("+x") == "'+x" and games.csv_safe("-x") == "'-x" and games.csv_safe("@x") == "'@x"
    assert games.csv_safe("Ana") == "Ana" and games.csv_safe("") == ""


# --------------------------------------------------------------------------
# A whole live game (real sandbox for the typed-code question)
# --------------------------------------------------------------------------


@pytest.fixture
def live4():
    """A live game with 3 players in the lobby: choice(easy), blanks(medium), code(easy), match(easy)."""
    clock = Clock()
    store = make_store(Pool([choice_q(1), blanks_q(2), code_q(3), match_q(4)]), clock)
    game = store.create(live_settings(title="Period 3"))
    joined = {n: game.join(n, "🐍") for n in ("alice", "bob", "carol")}
    return clock, store, game, joined


def tok(joined, name):
    return joined[name]["token"]


def test_full_live_game_with_typed_code(live4):
    clock, store, game, joined = live4
    host = game.host_token
    qs = game.questions
    assert [q.qtype for q in qs] == ["choice", "blanks", "code", "match"]
    assert game.limits == [15, 40, 90, 30]

    # lobby: join order, everybody rank 1, nothing to see yet
    st = game.host_state(host)
    assert st["phase"] == "lobby" and [p["name"] for p in st["players"]] == ["alice", "bob", "carol"]
    assert {p["rank"] for p in st["players"]} == {1} and st["question"] is None and st["summary"] is None
    assert st["question_total"] == 4 and st["question_index"] == -1
    assert game.lookup() == {"exists": True, "title": "Period 3", "mode": "live", "phase": "lobby", "locked": False, "players": 3}

    # nothing can be answered before the start
    assert err_reason(game.answer, tok(joined, "alice"), "whatever", 0) == "bad_state"
    assert err_reason(game.host_action, host, "next") == "bad_state"
    assert err_reason(game.host_action, host, "skip") == "bad_state"

    st = game.host_action(host, "start")
    assert st["phase"] == "question" and st["question_index"] == 0
    assert st["deadline"] == clock.t + 15 and st["question_started"] == clock.t
    assert st["answers"] == {"count": 0, "total": 3}
    assert err_reason(game.host_action, host, "start") == "bad_state"

    # -- Q1: alice right after 3 s, bob wrong, carol silent ----------------------------------
    q1 = qs[0]
    qid = game.qids[0]
    clock.advance(3)
    res = game.answer(tok(joined, "alice"), qid, right(q1))
    assert res["accepted"] is True and "result" not in res
    assert res["state"]["my_answer"] == {"submitted": True} and res["state"]["result"] is None
    assert res["state"]["me"]["score"] == 0  # nothing is scored (or revealed) until the reveal
    clock.advance(3)
    game.answer(tok(joined, "bob"), qid, wrong(q1))
    assert game.host_state(host)["answers"] == {"count": 2, "total": 3}
    assert game.player_state(tok(joined, "carol"))["my_answer"] is None

    clock.advance(10)  # t = 16 s = deadline (15) + 1 s grace -> the question ends by itself
    st = game.host_state(host)
    assert st["phase"] == "reveal"
    assert st["reveal"]["correct_count"] == 1 and st["reveal"]["answered_count"] == 2 and st["reveal"]["total"] == 3
    assert sum(st["reveal"]["distribution"]) == 2 and st["reveal"]["distribution"][q1.answer] == 1
    assert st["reveal"]["fastest"] == {"name": "alice", "ms": 3000}
    assert st["reveal"]["answer"] == {"answer": q1.answer} and st["reveal"]["explanation"] == "EXPLAIN_1"
    by = {p["name"]: p for p in st["players"]}
    assert by["alice"]["score"] == 140 and by["alice"]["rank"] == 1 and by["alice"]["delta"] == 140  # 100 + 40 speed
    assert by["bob"]["score"] == 0 and by["carol"]["score"] == 0 and by["bob"]["rank"] == by["carol"]["rank"] == 2
    assert [p["name"] for p in st["players"]] == ["alice", "bob", "carol"]  # rank, then name
    assert by["alice"]["answered_now"] and by["bob"]["answered_now"] and not by["carol"]["answered_now"]

    ps = game.player_state(tok(joined, "alice"))
    r = ps["result"]
    assert (r["correct"], r["points"], r["base_points"], r["speed_points"], r["streak_points"], r["streak"]) == (True, 140, 100, 40, 0, 1)
    assert r["time_ms"] == 3000 and r["late"] is False and r["qid"] == qid and r["explanation"] == "EXPLAIN_1"
    assert ps["reveal"]["answer"] == {"answer": q1.answer} and "fastest" not in ps["reveal"]
    assert ps["leaderboard"][0]["name"] == "alice" and ps["leaderboard"][0]["delta"] == 140
    cs = game.player_state(tok(joined, "carol"))["result"]
    assert cs["correct"] is False and cs["points"] == 0 and cs["answered"] is False and cs["time_ms"] is None
    assert game.player_state(tok(joined, "bob"))["result"]["correct"] is False

    # -- Q2 (blanks, medium, 40 s): everyone answers -> it ends early ------------------------
    assert err_reason(game.host_action, host, "skip") == "bad_state"
    game.host_action(host, "next")
    q2, qid2 = qs[1], game.qids[1]
    clock.advance(10)
    game.answer(tok(joined, "alice"), qid2, right(q2))
    clock.advance(10)
    game.answer(tok(joined, "bob"), qid2, right(q2))
    assert game.host_state(host)["phase"] == "question"
    clock.advance(1)
    game.answer(tok(joined, "carol"), qid2, wrong(q2))
    st = game.host_state(host)
    assert st["phase"] == "reveal"  # all three answered
    by = {p["name"]: p for p in st["players"]}
    # alice: 250 + round(125 * 0.75)=94 speed + 25 streak (1 before); bob: 250 + round(125 * 0.5)=62 speed (banker's rounding)
    assert by["alice"]["score"] == 140 + 369 and by["alice"]["streak"] == 2
    assert by["bob"]["score"] == 312 and by["bob"]["streak"] == 1
    assert by["carol"]["score"] == 0 and by["carol"]["streak"] == 0
    assert st["reveal"]["distribution"] == [2, 1, 0]
    assert st["reveal"]["answer"]["blanks"] == ["5"]

    # -- Q3 (typed code, easy, 90 s): graded in the real sandbox ----------------------------
    game.host_action(host, "next")
    qid3 = game.qids[2]
    q3pub = game.player_state(tok(joined, "alice"))["question"]
    assert q3pub["qtype"] == "code" and q3pub["task"]["func"] == "double" and "solution" not in json.dumps(q3pub)
    ran = game.run_examples(tok(joined, "carol"), qid3, GOOD_CODE)
    assert ran["status"] == "ok" and ran["correct"] is True and ran["total"] == 2  # only the visible examples
    clock.advance(30)
    game.answer(tok(joined, "alice"), qid3, GOOD_CODE)
    game.answer(tok(joined, "bob"), qid3, BAD_CODE)
    clock.advance(15)
    game.answer(tok(joined, "carol"), qid3, GOOD_CODE)
    st = game.host_state(host)
    assert st["phase"] == "reveal"
    by = {p["name"]: p for p in st["players"]}
    # alice 100 + round(50 * (1 - 30/90))=33 + 20 streak(2); carol 100 + round(50 * 0.5)=25
    assert by["alice"]["score"] == 509 + 153 == 662
    assert by["bob"]["score"] == 312 and by["bob"]["streak"] == 0
    assert by["carol"]["score"] == 125
    assert st["reveal"]["distribution"] == [2, 1, 0]  # not a choice question: [right, wrong, none]
    assert st["reveal"]["answer"] == {"solution": DOUBLE.solution}
    alice_r = game.player_state(tok(joined, "alice"))["result"]
    assert alice_r["detail"]["status"] == "ok" and alice_r["detail"]["passed"] == 3 and alice_r["points"] == 153
    bob_r = game.player_state(tok(joined, "bob"))["result"]
    assert bob_r["correct"] is False and bob_r["detail"]["passed"] == 0

    # -- Q4: the host skips it (nobody answered), then the game ends -------------------------
    game.host_action(host, "next")
    assert game.host_state(host)["phase"] == "question" and game.host_state(host)["question_index"] == 3
    st = game.host_action(host, "skip")
    assert st["phase"] == "reveal" and st["reveal"]["answered_count"] == 0 and st["reveal"]["distribution"] == [0, 0, 3]
    st = game.host_action(host, "next")
    assert st["phase"] == "finished" and st["next_at"] is None
    assert [p["name"] for p in st["players"]] == ["alice", "bob", "carol"]
    summ = st["summary"]
    assert [p["name"] for p in summ["podium"]] == ["alice", "bob", "carol"] and summ["podium"][0]["score"] == 662
    assert [q["index"] for q in summ["questions"]] == [1, 2, 3, 4]
    assert summ["questions"][0]["correct"] == 1 and summ["questions"][0]["answered"] == 2 and summ["questions"][0]["correct_pct"] == 33
    assert summ["questions"][2]["correct"] == 2 and summ["questions"][2]["avg_ms"] > 0
    assert summ["questions"][3]["correct_pct"] == 0
    assert summ["totals"] == {"players": 3, "answers": 2 + 3 + 3, "correct": 1 + 2 + 2}
    fin = game.player_state(tok(joined, "alice"))
    assert fin["phase"] == "finished" and fin["final"]["rank"] == 1 and fin["final"]["score"] == 662
    assert fin["final"]["correct"] == 3 and fin["final"]["answered"] == 3 and fin["final"]["best_streak"] == 3
    assert fin["final"]["players_total"] == 3 and [p["name"] for p in fin["final"]["podium"]] == ["alice", "bob", "carol"]
    assert fin["question"] is not None and fin["result"] is not None  # the last question's reveal stays readable
    assert game.player_state(tok(joined, "carol"))["final"]["rank"] == 3

    # finished: new joiners are turned away, answers are too late, end is idempotent
    assert err_reason(game.join, "dave") == "finished"
    assert err_reason(game.answer, tok(joined, "alice"), game.qids[3], 0) == "too_late"
    assert game.host_action(host, "end")["phase"] == "finished"

    # CSV
    rows = list(csv.reader(io.StringIO(game.csv_text(host))))
    assert rows[0] == ["Rank", "Name", "Score", "Correct", "Answered", "Accuracy %", "Avg answer time (s)", "Best streak", "Q1", "Q2", "Q3", "Q4"]
    assert rows[1][:3] == ["1", "alice", "662"] and rows[1][8:] == ["140", "369", "153", "0"]
    assert rows[2][:3] == ["2", "bob", "312"] and rows[2][8:] == ["0", "312", "0", "0"]
    assert rows[3][:3] == ["3", "carol", "125"] and rows[3][8:] == ["0", "0", "125", "0"]
    assert rows[1][3:8] == ["3", "3", "100", "14.3", "3"]  # correct, answered, accuracy %, avg s (3, 10, 30), best streak
    assert len(rows) == 4


def test_everyone_answers_ends_the_question_and_leavers_do_not_block():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings())
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    qid = game.qids[0]
    game.answer(a["token"], qid, 0)
    assert game.phase == "question"
    game.leave(b["token"])  # the only unanswered player leaves -> the rest have all answered
    assert game.phase == "reveal"
    assert err_reason(game.player_state, b["token"]) == "bad_token"


def test_kicking_the_last_unanswered_player_ends_the_question():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings())
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], 0)
    game.host_action(game.host_token, "kick", {"player_id": b["player_id"]})
    assert game.phase == "reveal" and game.host_state(game.host_token)["reveal"]["total"] == 1


def test_auto_advance_after_the_reveal():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3, auto_advance=True))
    a = game.join("a")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], 0)
    st = game.host_state(game.host_token)
    assert st["phase"] == "reveal" and st["next_at"] == clock.t + 10
    clock.advance(9.9)
    assert game.host_state(game.host_token)["phase"] == "reveal"
    clock.advance(0.2)
    st = game.host_state(game.host_token)
    assert st["phase"] == "question" and st["question_index"] == 1 and st["next_at"] is None
    # a long silence crosses several steps at once: question 2 expires, 10 s reveal, question 3 starts
    clock.advance(15 + 1 + 10 + 0.5)
    assert game.host_state(game.host_token)["question_index"] == 2
    clock.advance(1000)  # everything times out: last reveal then finished
    st = game.host_state(game.host_token)
    assert st["phase"] == "finished" and st["summary"]["totals"]["answers"] == 1


def test_deadline_and_grace():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a, b, c = game.join("a"), game.join("b"), game.join("c")
    game.host_action(game.host_token, "start")
    qid, q = game.qids[0], game.questions[0]
    clock.advance(15.9)  # past the deadline, inside the 1 s grace: still accepted, scored as the slowest
    game.answer(a["token"], qid, q.answer)
    clock.advance(0.2)  # 16.1 s: over
    assert game.host_state(game.host_token)["phase"] == "reveal"
    assert game.player_state(a["token"])["result"]["points"] == 100  # speed bonus 0 at the limit
    assert game.player_state(a["token"])["result"]["time_ms"] == 15000
    with pytest.raises(GameError) as info:
        game.answer(b["token"], qid, q.answer)
    assert info.value.reason == "too_late" and info.value.status == 409
    assert game.player_state(b["token"])["result"]["answered"] is False


def test_duplicate_answer_and_wrong_qid():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    qid = game.qids[0]
    game.answer(a["token"], qid, 0)
    with pytest.raises(GameError) as info:
        game.answer(a["token"], qid, 1)
    assert info.value.reason == "bad_state" and info.value.payload()["accepted"] is False
    assert err_reason(game.answer, b["token"], "not-a-qid", 0) == "bad_state"
    assert err_reason(game.answer, b["token"], 12, 0) == "bad_request"
    assert err_reason(game.answer, b["token"], None, 0) == "bad_request"
    game.answer(b["token"], qid, None)  # null = "nothing" is accepted and simply wrong
    game.host_action(game.host_token, "next")
    assert err_reason(game.answer, a["token"], qid, 0) == "too_late"  # the previous question
    assert game.player_state(a["token"])["result"] is None


def test_malformed_responses_are_just_wrong():
    game = make_store(Pool([blanks_q(1), match_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a = game.join("a")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], {"nope": [1, 2, 3]})
    st = game.player_state(a["token"])
    assert st["phase"] == "reveal" and st["result"]["correct"] is False and st["me"]["score"] == 0
    game.host_action(game.host_token, "next")
    game.answer(a["token"], game.qids[1], [True, "x", 2.5])
    assert game.player_state(a["token"])["result"]["correct"] is False


def test_same_player_cannot_double_submit_concurrently_and_grading_holds_no_lock():
    """A slow (sandbox-like) grade runs outside the lock: others keep working, and the player's
    second submission of the same qid is refused while the first is being graded."""
    clock = Clock()
    q = choice_q(1)
    started, release = threading.Event(), threading.Event()
    real_grade = q.grade

    def slow_grade(response):
        started.set()
        assert release.wait(10)
        return real_grade(response)

    q.grade = slow_grade
    game = make_store(Pool([q, choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    qid = game.qids[0]
    out: dict = {}
    t = threading.Thread(target=lambda: out.update(game.answer(a["token"], qid, q.answer)))
    t.start()
    assert started.wait(5)
    # the lock is free: the host, the other player and even a second answer from b are served immediately
    assert game.host_state(game.host_token)["answers"]["count"] == 0  # a's answer is not stored yet
    assert game.player_state(a["token"])["my_answer"] == {"submitted": True}
    assert err_reason(game.answer, a["token"], qid, 0) == "bad_state"  # duplicate while in flight
    assert err_reason(game.run_examples, a["token"], qid, "x") == "bad_state"
    release.set()
    t.join(5)
    assert out["accepted"] is True
    assert game.host_state(game.host_token)["answers"]["count"] == 1
    assert err_reason(game.answer, a["token"], qid, 0) == "bad_state"


def test_answer_that_finishes_grading_after_the_reveal_still_counts():
    clock = Clock()
    q = choice_q(1)
    started, release = threading.Event(), threading.Event()
    real_grade = q.grade

    def slow_grade(response):
        started.set()
        release.wait(10)
        return real_grade(response)

    q.grade = slow_grade
    game = make_store(Pool([q, choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    clock.advance(2)
    t = threading.Thread(target=lambda: game.answer(a["token"], game.qids[0], q.answer))
    t.start()
    assert started.wait(5)
    clock.advance(30)  # the question times out while a's answer is still being graded
    st = game.host_state(game.host_token)
    assert st["phase"] == "reveal" and {p["name"]: p["score"] for p in st["players"]} == {"a": 0, "b": 0}
    release.set()
    t.join(5)
    st = game.host_state(game.host_token)
    assert {p["name"]: p["score"] for p in st["players"]} == {"a": 143, "b": 0}  # arrival time (2 s) was what counted
    assert st["reveal"]["correct_count"] == 1
    assert game.player_state(a["token"])["result"]["points"] == 143


def test_ties_share_a_rank():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    ps = {n: game.join(n) for n in ("zed", "amy", "bo", "cy")}
    game.host_action(game.host_token, "start")
    qid, q = game.qids[0], game.questions[0]
    for n in ("zed", "amy"):  # same arrival time -> same points
        game.answer(ps[n]["token"], qid, q.answer)
    game.answer(ps["bo"]["token"], qid, wrong(q))
    game.host_action(game.host_token, "skip")
    st = game.host_state(game.host_token)
    assert [(p["name"], p["rank"], p["score"]) for p in st["players"]] == [
        ("amy", 1, 150),
        ("zed", 1, 150),
        ("bo", 3, 0),
        ("cy", 3, 0),
    ]
    assert game.player_state(ps["cy"]["token"])["me"]["rank"] == 3
    assert [r["rank"] for r in game.player_state(ps["cy"]["token"])["leaderboard"]] == [1, 1, 3, 3]


def test_leaderboard_is_top_five_only():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    ps = [game.join(f"p{i}") for i in range(8)]
    game.host_action(game.host_token, "start")
    game.host_action(game.host_token, "skip")
    assert len(game.player_state(ps[0]["token"])["leaderboard"]) == 5
    assert len(game.host_state(game.host_token)["players"]) == 8


def test_end_mid_question_scores_what_was_answered():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], game.questions[0].answer)
    st = game.host_action(game.host_token, "end")
    assert st["phase"] == "finished" and st["summary"]["questions"][0]["answered"] == 1
    assert {p["name"]: p["score"] for p in st["players"]} == {"a": 150, "b": 0}
    assert st["reveal"] is not None and st["question_index"] == 0


def test_end_from_the_lobby_and_start_needs_a_player():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    assert err_reason(game.host_action, game.host_token, "start") == "bad_state"
    st = game.host_action(game.host_token, "end")
    assert st["phase"] == "finished" and st["summary"]["questions"] == []
    assert err_reason(game.join, "late") == "finished"


def test_late_joiner_starts_at_zero_and_counts_for_early_end():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a = game.join("a")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], game.questions[0].answer)
    assert game.phase == "reveal"
    game.host_action(game.host_token, "next")
    b = game.join("b")  # joins mid-game
    st = b["state"]
    assert st["phase"] == "question" and st["me"]["score"] == 0 and st["question"]["id"] == game.qids[1]
    game.answer(a["token"], game.qids[1], 0)
    assert game.phase == "question"  # b has not answered yet
    game.answer(b["token"], game.qids[1], 0)
    assert game.phase == "reveal"


def test_kick():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    host = game.host_token
    assert err_reason(game.host_action, host, "kick", {"player_id": "p99"}) == "not_found"
    assert err_reason(game.host_action, host, "kick", {}) == "not_found"
    st = game.host_action(host, "kick", {"player_id": b["player_id"]})
    assert [p["name"] for p in st["players"]] == ["a"]
    assert err_reason(game.player_state, b["token"]) == "kicked"
    assert err_reason(game.answer, b["token"], "x", 0) == "kicked"
    assert err_reason(game.leave, b["token"]) == "kicked"
    # a kicked player may come back as somebody new (the name is free again) but their old token is dead
    b2 = game.join("b")
    assert b2["token"] != b["token"] and b2["player_id"] != b["player_id"]
    assert err_reason(game.player_state, b["token"]) == "kicked"


def test_lock_and_rejoin():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a = game.join("a")
    st = game.host_action(game.host_token, "lock", {"locked": True})
    assert st["locked"] is True and game.lookup()["locked"] is True
    assert err_reason(game.join, "newbie") == "locked"
    again = game.join("whatever", None, a["token"])  # rejoining with a token still works
    assert again["player_id"] == a["player_id"] and again["token"] == a["token"] and again["state"]["me"]["name"] == "a"
    assert err_reason(game.join, "a") == "locked"
    assert game.host_action(game.host_token, "lock", {"locked": False})["locked"] is False
    assert game.join("newbie")["player_id"] == "p2"
    assert err_reason(game.host_action, game.host_token, "lock", {"locked": "yes"}) == "bad_request"
    assert err_reason(game.host_action, game.host_token, "lock", {}) == "bad_request"


def test_join_rules():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3, max_players=3))
    a = game.join("  Ana   M ", "🐱")
    assert a["state"]["me"]["name"] == "Ana M" and a["state"]["me"]["avatar"] == "🐱" and a["code"] == game.code
    assert err_reason(game.join, "ana m") == "name_taken"  # case-insensitive
    assert err_reason(game.join, "ANA   m") == "name_taken"
    assert err_reason(game.join, "") == "bad_name"
    assert err_reason(game.join, "x" * 17) == "bad_name"
    assert err_reason(game.join, "ctl\x07") == "bad_name"
    wrong_token_same_name = err_reason(game.join, "Ana M", "🐱", "not-her-token")
    assert wrong_token_same_name == "name_taken"  # a wrong token is not a rejoin
    game.join("b")
    game.join("c")
    assert err_reason(game.join, "d") == "full"
    assert game.join("x", None, a["token"])["player_id"] == a["player_id"]  # rejoin is fine even when full
    assert game.join("c", None, game.join("c", None, game.players["p3"].token)["token"])["player_id"] == "p3"


def test_player_cap_is_200():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3, max_players=9999))
    assert game.settings["max_players"] == 200
    for i in range(200):
        game.join(f"p{i}")
    assert err_reason(game.join, "one more") == "full"


def test_connected_flag_and_version_bump_on_disconnect():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a = game.join("a")
    st = game.host_state(game.host_token)
    assert st["players"][0]["connected"] is True
    v = st["version"]
    clock.advance(5)
    assert game.host_state(game.host_token, since=v)["unchanged"] is True
    clock.advance(4)  # 9 s since a last polled
    st = game.host_state(game.host_token, since=v)
    assert st["unchanged"] is False and st["players"][0]["connected"] is False
    game.player_state(a["token"])
    st = game.host_state(game.host_token)
    assert st["players"][0]["connected"] is True and st["version"] > v


def test_versions_and_unchanged_shortcut():
    clock = Clock()
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock).create(live_settings(question_count=3))
    a = game.join("a")
    host = game.host_token
    st = game.host_state(host)
    v = st["version"]
    assert st["unchanged"] is False
    same = game.host_state(host, since=v)
    assert same == {"unchanged": True, "version": v, "server_time": clock.t}
    assert game.host_state(host, since=v - 1)["unchanged"] is False
    assert game.host_state(host, since=v + 5)["unchanged"] is False
    ps = game.player_state(a["token"])
    assert game.player_state(a["token"], since=ps["version"]) == {"unchanged": True, "version": ps["version"], "server_time": clock.t}
    game.join("b")
    assert game.host_state(host, since=v)["version"] > v  # a join is a change
    assert game.player_state(a["token"], since=ps["version"])["players_total"] == 2
    v = game.version
    game.host_action(host, "start")
    assert game.version > v
    v = game.version
    clock.advance(20)  # time passes: the deadline hit, a time-based change bumps the version
    assert game.host_state(host, since=v)["phase"] == "reveal"
    assert game.player_state(a["token"], since=v)["phase"] == "reveal"
    assert game.version > v


def test_game_limit_makes_room_by_dropping_the_oldest_finished_game():
    clock = Clock()
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock, max_games=2)
    g1 = store.create(live_settings(question_count=3))
    g2 = store.create(live_settings(question_count=3))
    with pytest.raises(GameError) as info:
        store.create(live_settings(question_count=3))
    assert info.value.reason == "full" and info.value.status == 503
    clock.advance(5)
    g1.join("a")
    g1.host_action(g1.host_token, "end")
    g3 = store.create(live_settings(question_count=3))
    assert store.count() == 2 and err_reason(store.get, g1.code) == "not_found"
    assert store.get(g2.code) is g2 and store.get(g3.code) is g3


def test_purge_by_age():
    clock = Clock()
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock)
    finished = store.create(live_settings(question_count=3))
    finished.join("a")
    finished.host_action(finished.host_token, "end")
    idle = store.create(live_settings(question_count=3))
    busy = store.create(live_settings(question_count=3))
    clock.advance(2 * 3600 - 1)
    busy.host_state(busy.host_token)  # activity keeps a game alive
    store.create(live_settings(question_count=3))
    assert {finished.code, idle.code, busy.code} <= {c for c in store._games}
    clock.advance(2)  # finished is now over 2 h old
    store.create(live_settings(question_count=3))
    assert finished.code not in store._games and idle.code in store._games
    clock.advance(8 * 3600 - 10)  # idle has now been quiet for > 8 h; busy for 8 h - 8 s
    store.create(live_settings(question_count=3))
    assert idle.code not in store._games and busy.code in store._games
    clock.advance(20)
    store.purge()
    assert busy.code not in store._games


def test_codes_are_six_digits_and_unique():
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), max_games=50)
    codes = {store.create(live_settings(question_count=3)).code for _ in range(50)}
    assert len(codes) == 50 and all(len(c) == 6 and c.isdigit() and c[0] != "0" for c in codes)
    assert err_reason(store.get, "123") == "not_found" and err_reason(store.get, None) == "not_found"


def test_live_questions_are_unique_and_requested_count_is_honoured():
    factory = Endless()
    game = make_store(factory).create({"mode": "live", "question_count": 12, "topics": ["variables"], "difficulty": 2, "types": "choice"})
    assert len(game.questions) == 12 and len({q.prompt for q in game.questions}) == 12
    assert factory.args[0] == (["variables"], 2, ["choice", "match"])
    # a pool with only 2 distinct questions can't make a game
    with pytest.raises(GameError) as info:
        make_store(Pool([choice_q(1), choice_q(2)])).create(live_settings(question_count=5))
    assert info.value.reason == "bad_request"

    class Flaky:
        def __init__(self):
            self.n = 0

        def __call__(self, *a, **k):
            self.n += 1
            if self.n % 2:
                raise GenerationError("unlucky")
            return choice_q(self.n)

    assert len(make_store(Flaky()).create(live_settings(question_count=5)).questions) == 5


# --------------------------------------------------------------------------
# Time Rush
# --------------------------------------------------------------------------


def rush_game(clock=None, factory=None, **kw):
    clock = clock or Clock()
    store = make_store(factory or Endless(), clock)
    game = store.create({"mode": "rush", "duration_min": 2, **kw})
    return clock, store, game


def test_rush_flow_scoring_cooldown_and_finish():
    clock, store, game = rush_game()
    host = game.host_token
    a, b = game.join("a"), game.join("b")
    assert a["state"]["question"] is None and a["state"]["phase"] == "lobby"
    st = game.host_action(host, "start")
    assert st["phase"] == "running" and st["started_at"] == clock.t and st["ends_at"] == clock.t + 120
    assert st["stats"] == {"questions_answered": 0, "correct": 0} and st["answers"] is None and st["question"] is None

    ps = game.player_state(a["token"])
    q = ps["question"]
    assert q["id"] and "time_limit" not in q and ps["cooldown_until"] is None and ps["ends_at"] == clock.t + 120
    cur = game.players[a["player_id"]].current["q"]
    assert "answer" not in json.dumps(q)

    # three right answers in a row: 100, 110, 120 (streak bonus 10 % per streak step)
    pts = []
    for _ in range(3):
        clock.advance(2)
        cur = game.players[a["player_id"]].current["q"]
        res = game.answer(a["token"], ps["question"]["id"], cur.answer)
        assert res["accepted"] is True and res["result"]["correct"] is True
        assert res["result"]["time_ms"] > 0 and res["result"]["reveal"] == {"answer": cur.answer}
        assert res["result"]["speed_points"] == 0 and res["result"]["answer_text"] == cur.choices[cur.answer]
        pts.append(res["result"]["points"])
        ps = res["state"]
        assert ps["question"] is not None and ps["question"]["id"] != res["result"]["qid"]  # the NEXT question is already there
    assert pts == [100, 110, 120]
    assert ps["me"]["score"] == 330 and ps["me"]["streak"] == 3 and ps["me"]["answered"] == 3 and ps["result"]["points"] == 120

    # a wrong answer: 0 points, streak reset, 3 s cooldown with no question served
    cur = game.players[a["player_id"]].current["q"]
    qid = ps["question"]["id"]
    res = game.answer(a["token"], qid, wrong(cur))
    assert res["result"]["correct"] is False and res["result"]["points"] == 0 and res["result"]["streak"] == 0
    ps = res["state"]
    assert ps["question"] is None and ps["cooldown_until"] == clock.t + 3 and ps["me"]["streak"] == 0
    nxt = game.players[a["player_id"]].current
    assert nxt is not None  # generated in advance, just not served
    clock.advance(2)
    assert game.player_state(a["token"])["question"] is None
    assert err_reason(game.answer, a["token"], nxt["qid"], 0) == "bad_state"  # still cooling down
    v = game.version
    clock.advance(1.1)
    st = game.player_state(a["token"], since=v)  # the cooldown ending is a (time-based) change
    assert st["unchanged"] is False and st["question"]["id"] == nxt["qid"] and st["cooldown_until"] is None

    # live leaderboard (host) with ranks and stats
    hs = game.host_state(host)
    assert [(p["name"], p["score"], p["rank"], p["correct"], p["answered"]) for p in hs["players"]] == [("a", 330, 1, 3, 4), ("b", 0, 2, 0, 0)]
    assert hs["stats"] == {"questions_answered": 4, "correct": 3}
    assert game.player_state(b["token"])["me"]["rank"] == 2 and game.player_state(b["token"])["leaderboard"][0]["name"] == "a"

    # b answers too, then the clock runs out
    bq = game.player_state(b["token"])["question"]
    res = game.answer(b["token"], bq["id"], game.players[b["player_id"]].current["q"].answer)
    assert res["result"]["points"] == 100
    clock.advance(200)
    hs = game.host_state(host)
    assert hs["phase"] == "finished" and hs["ends_at"] == hs["started_at"] + 120
    assert hs["summary"]["questions"][0]["topic"] == "variables" and hs["summary"]["questions"][0]["answered"] == 5
    assert hs["summary"]["totals"] == {"players": 2, "answers": 5, "correct": 4}
    cur = game.players[a["player_id"]].current
    cur_id = cur["qid"] if cur else "x"
    assert err_reason(game.answer, a["token"], cur_id, 0) == "too_late"
    fin = game.player_state(a["token"])
    assert fin["phase"] == "finished" and fin["final"]["rank"] == 1 and fin["final"]["score"] == 330 and fin["final"]["best_streak"] == 3
    assert fin["final"]["correct"] == 3 and fin["final"]["answered"] == 4 and fin["question"] is None
    assert err_reason(game.join, "late") == "finished"


def test_rush_answer_after_ends_at_is_too_late_even_before_anyone_polls():
    clock, store, game = rush_game()
    a = game.join("a")
    game.host_action(game.host_token, "start")
    qid = game.player_state(a["token"])["question"]["id"]
    clock.advance(120)  # exactly ends_at
    assert err_reason(game.answer, a["token"], qid, 0) == "too_late"
    assert game.phase == "finished"


def test_rush_streak_bonus_is_capped_at_ten():
    clock, store, game = rush_game()
    a = game.join("a")
    game.host_action(game.host_token, "start")
    qid = game.player_state(a["token"])["question"]["id"]
    got = []
    for _ in range(13):
        cur = game.players[a["player_id"]].current
        res = game.answer(a["token"], cur["qid"], cur["q"].answer)
        got.append(res["result"]["points"])
    assert got == [100 + 10 * min(i, 10) for i in range(13)]
    assert game.players[a["player_id"]].best_streak == 13


def test_rush_questions_are_per_player_and_not_repeated():
    pool = [choice_q(1), choice_q(2)]
    seq = itertools.cycle([pool[0], pool[0], pool[0], pool[1]])  # the factory likes to repeat itself

    def factory(topics=None, difficulty=None, rng=None, types=None):
        return next(seq)

    clock, store, game = rush_game(factory=factory)
    a = game.join("a")
    game.host_action(game.host_token, "start")
    first = game.player_state(a["token"])["question"]
    cur = game.players[a["player_id"]].current
    res = game.answer(a["token"], cur["qid"], cur["q"].answer)
    assert res["state"]["question"]["prompt"] != first["prompt"]  # re-rolled: it was the same as the last one


def test_rush_uses_the_game_settings_for_every_question():
    factory = Endless()
    clock, store, game = rush_game(factory=factory, topics=["strings"], difficulty=3, types="typing")
    a = game.join("a")
    game.host_action(game.host_token, "start")
    game.player_state(a["token"])
    assert factory.args[0] == (["strings"], 3, ["blanks", "code"])


def test_rush_generation_failure_is_retried_on_the_next_poll():
    state = {"fail": True}
    endless = Endless()

    def factory(*a, **k):
        if state["fail"]:
            raise GenerationError("no luck")
        return endless(*a, **k)

    clock, store, game = rush_game(factory=factory)
    a = game.join("a")
    game.host_action(game.host_token, "start")
    assert game.player_state(a["token"])["question"] is None
    state["fail"] = False
    assert game.player_state(a["token"])["question"] is not None


def test_rush_wrong_qid_and_phase_errors():
    clock, store, game = rush_game()
    a = game.join("a")
    assert err_reason(game.answer, a["token"], "x", 0) == "bad_state"  # lobby
    game.host_action(game.host_token, "start")
    game.player_state(a["token"])
    assert err_reason(game.answer, a["token"], "not-mine", 0) == "bad_state"
    assert err_reason(game.host_action, game.host_token, "skip") == "bad_state"
    assert err_reason(game.host_action, game.host_token, "next") == "bad_state"
    assert game.host_action(game.host_token, "end")["phase"] == "finished"


def test_rush_run_button_limit():
    clock = Clock()
    store = make_store(Pool([code_q(1)]), clock)
    game = store.create({"mode": "rush"})
    a = game.join("a")
    game.host_action(game.host_token, "start")
    qid = game.player_state(a["token"])["question"]["id"]
    game.players[a["player_id"]].runs = 0
    # use a stubbed example runner: the limit is what is under test here
    q = game.players[a["player_id"]].current["q"]
    calls = []
    q.run_examples = lambda code: calls.append(code) or {"status": "ok", "correct": False, "passed": 0, "total": 2, "message": "", "cases": []}
    for _ in range(games.MAX_RUNS_PER_QUESTION):
        assert game.run_examples(a["token"], qid, "x = 1")["status"] == "ok"
    assert err_reason(game.run_examples, a["token"], qid, "x = 1") == "rate_limited"
    assert len(calls) == games.MAX_RUNS_PER_QUESTION
    assert err_reason(game.run_examples, a["token"], qid, 42) == "bad_request"


def test_run_is_only_for_code_questions_and_the_open_question():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a = game.join("a")
    assert err_reason(game.run_examples, a["token"], "x", "print(1)") == "bad_state"
    game.host_action(game.host_token, "start")
    assert err_reason(game.run_examples, a["token"], game.qids[0], "print(1)") == "bad_state"  # a choice question
    assert err_reason(game.run_examples, a["token"], "nope", "print(1)") == "bad_state"


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------


def test_csv_escaping_and_formula_neutralising():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    names = ['=SUM(A1)', '+1', '-2', '@x', 'Ann, "Q"', "Zoë"]
    ps = {n: game.join(n) for n in names}
    game.host_action(game.host_token, "start")
    game.answer(ps["Zoë"]["token"], game.qids[0], game.questions[0].answer)
    game.host_action(game.host_token, "skip")
    text = game.csv_text(game.host_token)
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][-1] == "Q1" and len(rows) == 7
    assert rows[1][:2] == ["1", "Zoë"]
    by_name = {r[1]: r for r in rows[1:]}
    assert set(by_name) == {"Zoë", "'=SUM(A1)", "'+1", "'-2", "'@x", 'Ann, "Q"'}
    assert '"Ann, ""Q"""' in text  # quoted properly
    for r in rows[1:]:
        assert not r[1].startswith(("=", "+", "-", "@"))


def test_csv_before_start_and_for_rush():
    clock, store, game = rush_game()
    a = game.join("a")
    rows = list(csv.reader(io.StringIO(game.csv_text(game.host_token))))
    assert rows[0] == ["Rank", "Name", "Score", "Correct", "Answered", "Accuracy %", "Avg answer time (s)", "Best streak"]
    assert rows[1] == ["1", "a", "0", "0", "0", "0", "0", "0"]
    game.host_action(game.host_token, "start")
    cur = game.players[a["player_id"]].current
    game.player_state(a["token"])
    cur = game.players[a["player_id"]].current
    clock.advance(2.5)
    game.answer(a["token"], cur["qid"], cur["q"].answer)
    rows = list(csv.reader(io.StringIO(game.csv_text(game.host_token))))
    assert rows[1] == ["1", "a", "100", "1", "1", "100", "2.5", "1"]


# --------------------------------------------------------------------------
# Auth and no-leak
# --------------------------------------------------------------------------


def test_auth_failures_at_the_game_level():
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]))
    game = store.create(live_settings(question_count=3))
    other = store.create(live_settings(question_count=3))
    a = game.join("a")
    for bad in ["", "nope", None, other.host_token, a["token"], "é" * 10]:
        assert err_reason(game.host_state, bad) == "bad_token"
        assert err_reason(game.host_action, bad, "start") == "bad_token"
        assert err_reason(game.csv_text, bad) == "bad_token"
    for bad in ["", "nope", None, game.host_token, 17]:
        assert err_reason(game.player_state, bad) == "bad_token"
        assert err_reason(game.answer, bad, "q", 0) == "bad_token"
        assert err_reason(game.run_examples, bad, "q", "x") == "bad_token"
        assert err_reason(game.leave, bad) == "bad_token"
    # a token from another game is not valid here
    b = other.join("b")
    assert err_reason(game.player_state, b["token"]) == "bad_token"
    assert err_reason(game.host_action, game.host_token, "explode") == "not_found"
    assert game.phase == "lobby"  # none of the above started anything


def test_a_player_cannot_act_as_another_player():
    game = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)])).create(live_settings(question_count=3))
    a, b = game.join("a"), game.join("b")
    game.host_action(game.host_token, "start")
    game.answer(a["token"], game.qids[0], game.questions[0].answer)
    # b's token only ever touches b: a's answer stands, b can still answer
    assert game.player_state(b["token"])["my_answer"] is None
    assert game.player_state(b["token"])["me"]["id"] == b["player_id"]
    assert err_reason(game.answer, a["player_id"], game.qids[0], 0) == "bad_token"  # an id is not a token
    assert err_reason(game.host_action, a["token"], "end") == "bad_token"  # a player token is not a host token


SECRET_KEYS = {"answer", "answer_text", "explanation", "solution", "accepted", "distribution", "correct_count", "fastest"}


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + "/" + str(k), k, v
            yield from walk(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def assert_no_secrets(payload, extra_secrets=()):
    text = json.dumps(payload, ensure_ascii=False)
    for path, key, value in walk(payload):
        assert key not in SECRET_KEYS, f"{key} leaked at {path}"
        if key in ("reveal", "result", "summary", "final"):
            assert value is None, f"{key} filled in at {path}"
    assert "EXPLAIN_" not in text and "SOLUTION" not in text
    for s in extra_secrets:
        assert s not in text, f"{s!r} leaked"


def test_no_answers_in_public_payloads_while_a_question_is_open():
    clock = Clock()
    qs = [choice_q(1), blanks_q(2), match_q(3), code_q(4)]
    game = make_store(Pool(qs), clock).create(live_settings(title="t"))
    a, b = game.join("a"), game.join("b")
    host = game.host_token
    assert_no_secrets(game.lookup())
    assert_no_secrets(game.host_state(host))
    assert_no_secrets(a["state"])
    game.host_action(host, "start")
    for i, q in enumerate(qs):
        secrets_ = [DOUBLE.solution] if q.qtype == "code" else []
        if q.qtype == "blanks":
            secrets_ = ["accepted"]
        assert_no_secrets(game.host_state(host), secrets_)
        assert_no_secrets(game.player_state(a["token"]), secrets_)
        assert_no_secrets(game.player_state(b["token"]), secrets_)
        game.answer(a["token"], game.qids[i], wrong(q) if q.qtype != "code" else BAD_CODE)
        # a has answered, b has not: a's own state must still not say whether it was right
        assert_no_secrets(game.player_state(a["token"]), secrets_)
        assert_no_secrets(game.host_state(host), secrets_)
        game.host_action(host, "skip")
        st = game.host_state(host)
        assert st["reveal"] is not None  # ... and now it is allowed
        if i < len(qs) - 1:
            game.host_action(host, "next")
            nxt = game.host_state(host)
            assert nxt["reveal"] is None


def test_no_answers_in_rush_payloads_beyond_the_question_just_answered():
    clock, store, game = rush_game()
    a = game.join("a")
    game.host_action(game.host_token, "start")
    for _ in range(4):
        st = game.player_state(a["token"])
        assert_no_secrets({k: v for k, v in st.items() if k != "result"})
        assert_no_secrets(game.host_state(game.host_token))
        cur = game.players[a["player_id"]].current
        res = game.answer(a["token"], cur["qid"], cur["q"].answer)
        nxt = game.players[a["player_id"]].current["q"]
        text = json.dumps(res["state"])
        assert nxt.explanation not in text  # the NEXT question's explanation is not in the response
        assert_no_secrets({k: v for k, v in res["state"].items() if k != "result"})


# --------------------------------------------------------------------------
# HTTP layer
# --------------------------------------------------------------------------


@pytest.fixture
def web(monkeypatch):
    """(client, clock, install): install(factory) swaps in a fresh store with a fake clock."""
    clock = Clock()
    app.config["TESTING"] = True
    client = app.test_client()

    def install(factory, **kw):
        store = make_store(factory, clock, **kw)
        monkeypatch.setattr(hosting, "STORE", store)
        return store

    install(Pool([choice_q(1), blanks_q(2), code_q(3), match_q(4)]))
    client.install = install
    client.clock = clock
    return client


def H(token):
    return {"X-Host-Token": token}


def P(token):
    return {"X-Player-Token": token}


def post(client, url, body=None, headers=None):
    res = client.post(url, data=json.dumps(body if body is not None else {}), content_type="application/json", headers=headers or {})
    return res


def err(res, status, reason):
    assert res.status_code == status, (res.status_code, res.get_data(as_text=True)[:300])
    data = res.get_json()
    assert data["reason"] == reason and isinstance(data["error"], str) and data["error"]
    return data


def create_http(client, **settings):
    res = post(client, "/api/host/games", {"mode": "live", "question_count": 4, **settings})
    assert res.status_code == 201, res.get_data(as_text=True)
    return res.get_json()


def join_http(client, code, name, avatar="🐍", token=None):
    body = {"code": code, "name": name, "avatar": avatar}
    if token:
        body["token"] = token
    res = post(client, "/api/play/join", body)
    assert res.status_code == 200, res.get_data(as_text=True)
    return res.get_json()


def test_http_full_live_game_with_three_players(web):
    c, clock = web, web.clock
    made = create_http(c, title="Period 3")
    code, ht = made["code"], made["host_token"]
    assert len(code) == 6 and made["join_url_path"] == f"/?join={code}" and made["lan"] is False and made["join_urls"] == []
    assert made["game"]["phase"] == "lobby" and made["game"]["settings"]["question_count"] == 4 and made["game"]["title"] == "Period 3"
    assert "_types" not in made["game"]["settings"]
    assert c.get(f"/api/play/lookup?code={code}").get_json() == {"exists": True, "title": "Period 3", "mode": "live", "phase": "lobby", "locked": False, "players": 0}

    joined = {n: join_http(c, code, n) for n in ("ann", "ben", "cat")}
    assert joined["ann"]["code"] == code and joined["ann"]["state"]["phase"] == "lobby"
    state = c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()
    assert [p["name"] for p in state["players"]] == ["ann", "ben", "cat"] and state["server_time"] == clock.t

    state = post(c, f"/api/host/games/{code}/start", headers=H(ht)).get_json()
    assert state["phase"] == "question" and state["question"]["qtype"] == "choice" and state["question"]["time_limit"] == 15
    qid = state["question"]["id"]
    ps = c.get(f"/api/play/{code}/state", headers=P(joined["ann"]["token"])).get_json()
    assert ps["question"]["id"] == qid and ps["deadline"] == clock.t + 15 and ps["my_answer"] is None
    assert_no_secrets(ps)
    game = hosting.STORE.get(code)
    q = game.questions[0]
    clock.advance(2)
    res = post(c, f"/api/play/{code}/answer", {"qid": qid, "response": q.answer}, P(joined["ann"]["token"]))
    assert res.status_code == 200 and res.get_json()["accepted"] is True and res.get_json()["state"]["my_answer"] == {"submitted": True}
    err(post(c, f"/api/play/{code}/answer", {"qid": qid, "response": 0}, P(joined["ann"]["token"])), 409, "bad_state")
    assert post(c, f"/api/play/{code}/answer", {"qid": qid, "response": 0}, P(joined["ann"]["token"])).get_json()["accepted"] is False
    post(c, f"/api/play/{code}/answer", {"qid": qid, "response": (q.answer + 1) % 4}, P(joined["ben"]["token"]))
    post(c, f"/api/play/{code}/answer", {"qid": qid, "response": None}, P(joined["cat"]["token"]))
    state = c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()
    assert state["phase"] == "reveal"  # all three answered
    assert state["reveal"]["correct_count"] == 1 and state["players"][0]["name"] == "ann" and state["players"][0]["score"] == 143  # 100 + round(50 * 13/15)=43 speed
    ps = c.get(f"/api/play/{code}/state", headers=P(joined["ann"]["token"])).get_json()
    assert ps["result"]["correct"] is True and ps["result"]["speed_points"] == 43 and ps["reveal"]["answer"] == {"answer": q.answer}

    # second question: blanks (typed), then the typed-code question graded by the real sandbox
    post(c, f"/api/host/games/{code}/next", headers=H(ht))
    q2 = game.questions[1]
    res = post(c, f"/api/play/{code}/answer", {"qid": game.qids[1], "response": ["5"]}, P(joined["ann"]["token"]))
    assert res.get_json()["accepted"] is True
    post(c, f"/api/host/games/{code}/skip", headers=H(ht))
    post(c, f"/api/host/games/{code}/next", headers=H(ht))
    qid3 = game.qids[2]
    run = post(c, f"/api/play/{code}/run", {"qid": qid3, "code": GOOD_CODE}, P(joined["ben"]["token"]))
    assert run.status_code == 200 and run.get_json()["correct"] is True and run.get_json()["total"] == 2
    res = post(c, f"/api/play/{code}/answer", {"qid": qid3, "response": GOOD_CODE}, P(joined["ann"]["token"]))
    assert res.get_json()["accepted"] is True
    post(c, f"/api/play/{code}/answer", {"qid": qid3, "response": BAD_CODE}, P(joined["ben"]["token"]))
    post(c, f"/api/host/games/{code}/skip", headers=H(ht))
    ps = c.get(f"/api/play/{code}/state", headers=P(joined["ann"]["token"])).get_json()
    assert ps["result"]["correct"] is True and ps["result"]["detail"]["passed"] == 3 and ps["reveal"]["answer"] == {"solution": DOUBLE.solution}
    ps = c.get(f"/api/play/{code}/state", headers=P(joined["ben"]["token"])).get_json()
    assert ps["result"]["correct"] is False and ps["result"]["detail"]["passed"] == 0

    # end it, read the results
    state = post(c, f"/api/host/games/{code}/end", headers=H(ht)).get_json()
    assert state["phase"] == "finished" and state["summary"]["totals"]["players"] == 3
    csv_res = c.get(f"/api/host/games/{code}/results.csv?token={ht}")
    assert csv_res.status_code == 200 and csv_res.mimetype == "text/csv"
    assert f"pyblooket-{code}-results.csv" in csv_res.headers["Content-Disposition"]
    rows = list(csv.reader(io.StringIO(csv_res.get_data(as_text=True))))
    assert rows[0][:3] == ["Rank", "Name", "Score"] and rows[1][1] == "ann" and len(rows) == 4
    assert c.get(f"/api/host/games/{code}/results.csv", headers=H(ht)).status_code == 200  # header works too
    # the only game over the wire that stays on is the one in the store
    left = post(c, f"/api/play/{code}/leave", {}, P(joined["cat"]["token"]))
    assert left.get_json() == {"ok": True}
    # after the end, leaving does not erase the student from the results
    assert c.get(f"/api/play/{code}/state", headers=P(joined["cat"]["token"])).get_json()["final"]["players_total"] == 3
    rows = list(csv.reader(io.StringIO(c.get(f"/api/host/games/{code}/results.csv?token={ht}").get_data(as_text=True))))
    assert len(rows) == 4


def test_http_leaving_mid_game_removes_the_player(web):
    c = web
    made = create_http(c)
    code, ht = made["code"], made["host_token"]
    ann, ben = join_http(c, code, "ann"), join_http(c, code, "ben")
    assert post(c, f"/api/play/{code}/leave", {}, P(ben["token"])).get_json() == {"ok": True}
    err(c.get(f"/api/play/{code}/state", headers=P(ben["token"])), 401, "bad_token")
    assert [p["name"] for p in c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()["players"]] == ["ann"]


def test_http_rush_game(web):
    web.install(Endless())
    c, clock = web, web.clock
    made = post(c, "/api/host/games", {"mode": "rush", "duration_min": 3, "title": "rush"}).get_json()
    code, ht = made["code"], made["host_token"]
    ann = join_http(c, code, "ann")
    st = post(c, f"/api/host/games/{code}/start", headers=H(ht)).get_json()
    assert st["phase"] == "running" and st["ends_at"] == clock.t + 180
    ps = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()
    assert ps["question"]["id"] and ps["phase"] == "running"
    cur = hosting.STORE.get(code).players[ann["player_id"]].current
    res = post(c, f"/api/play/{code}/answer", {"qid": ps["question"]["id"], "response": cur["q"].answer}, P(ann["token"])).get_json()
    assert res["accepted"] and res["result"]["points"] == 100 and res["state"]["question"]["id"] != ps["question"]["id"]
    cur = hosting.STORE.get(code).players[ann["player_id"]].current
    res = post(c, f"/api/play/{code}/answer", {"qid": cur["qid"], "response": wrong(cur["q"])}, P(ann["token"])).get_json()
    assert res["result"]["correct"] is False and res["state"]["question"] is None and res["state"]["cooldown_until"] == clock.t + 3
    err(post(c, f"/api/play/{code}/answer", {"qid": cur["qid"], "response": 0}, P(ann["token"])), 409, "bad_state")
    clock.advance(500)
    st = c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()
    assert st["phase"] == "finished" and st["players"][0]["score"] == 100
    err(post(c, f"/api/play/{code}/answer", {"qid": cur["qid"], "response": 0}, P(ann["token"])), 409, "too_late")


def test_http_polling_unchanged_shortcut(web):
    c, clock = web, web.clock
    made = create_http(c)
    code, ht = made["code"], made["host_token"]
    ann = join_http(c, code, "ann")
    first = c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()
    again = c.get(f"/api/host/games/{code}?since={first['version']}", headers=H(ht)).get_json()
    assert again == {"unchanged": True, "version": first["version"], "server_time": clock.t}
    assert c.get(f"/api/host/games/{code}?since=oops", headers=H(ht)).get_json()["unchanged"] is False  # junk is ignored
    ps = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()
    assert c.get(f"/api/play/{code}/state?since={ps['version']}", headers=P(ann["token"])).get_json()["unchanged"] is True
    join_http(c, code, "ben")
    assert c.get(f"/api/play/{code}/state?since={ps['version']}", headers=P(ann["token"])).get_json()["players_total"] == 2


def test_http_error_shapes_and_auth(web):
    c = web
    made = create_http(c)
    code, ht = made["code"], made["host_token"]
    ann = join_http(c, code, "ann")
    # unknown game
    err(c.get("/api/host/games/000000", headers=H(ht)), 404, "not_found")
    err(c.get("/api/play/lookup?code=000000"), 404, "not_found")
    err(c.get("/api/play/lookup"), 404, "not_found")
    err(post(c, "/api/play/join", {"code": "000000", "name": "x"}), 404, "not_found")
    err(post(c, "/api/play/000000/answer", {"qid": "x"}, P(ann["token"])), 404, "not_found")
    err(c.get("/api/play/000000/state", headers=P(ann["token"])), 404, "not_found")
    err(c.get("/api/play/nope/state", headers=P(ann["token"])), 404, "not_found")
    # host endpoints: no / wrong token
    for url, method in [
        (f"/api/host/games/{code}", "get"),
        (f"/api/host/games/{code}/results.csv", "get"),
        (f"/api/host/games/{code}/start", "post"),
        (f"/api/host/games/{code}/end", "post"),
        (f"/api/host/games/{code}/kick", "post"),
        (f"/api/host/games/{code}/lock", "post"),
    ]:
        for headers in ({}, H("wrong"), H(ann["token"]), P(ht)):
            res = c.get(url, headers=headers) if method == "get" else post(c, url, {"player_id": "p1", "locked": True}, headers)
            err(res, 401, "bad_token")
    err(c.get(f"/api/host/games/{code}/results.csv?token=wrong"), 401, "bad_token")
    err(c.get(f"/api/host/games/{code}?token={ht}"), 401, "bad_token")  # the query-string token is for the CSV link only
    # player endpoints: no / wrong token (a host token is not a player token)
    for headers in ({}, P("wrong"), P(ht), H(ann["token"])):
        err(c.get(f"/api/play/{code}/state", headers=headers), 401, "bad_token")
        err(post(c, f"/api/play/{code}/answer", {"qid": "x", "response": 1}, headers), 401, "bad_token")
        err(post(c, f"/api/play/{code}/run", {"qid": "x", "code": "1"}, headers), 401, "bad_token")
        err(post(c, f"/api/play/{code}/leave", {}, headers), 401, "bad_token")
    # nothing above changed the game
    assert c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()["phase"] == "lobby"
    # bad requests
    err(post(c, "/api/host/games", {"mode": "nope"}), 400, "bad_request")
    err(c.post("/api/host/games", data="not json", content_type="application/json"), 400, "bad_request")
    err(c.post("/api/host/games", data="[1,2]", content_type="application/json"), 400, "bad_request")
    err(c.post("/api/host/games"), 400, "bad_request")
    err(post(c, "/api/play/join", {"code": code, "name": ""}), 400, "bad_name")
    err(post(c, "/api/play/join", {"code": code, "name": "ann"}), 409, "name_taken")
    err(post(c, "/api/play/join", {"code": code}), 400, "bad_name")
    err(post(c, "/api/play/join", {}), 404, "not_found")
    err(post(c, f"/api/host/games/{code}/explode", headers=H(ht)), 404, "not_found")
    err(post(c, f"/api/host/games/{code}/lock", {"locked": "maybe"}, H(ht)), 400, "bad_request")
    err(post(c, f"/api/host/games/{code}/next", headers=H(ht)), 409, "bad_state")
    err(post(c, f"/api/host/games/{code}/kick", {"player_id": "zzz"}, H(ht)), 404, "not_found")
    err(post(c, f"/api/play/{code}/answer", {"response": 1}, P(ann["token"])), 400, "bad_request")
    err(post(c, f"/api/play/{code}/run", {"qid": "x"}, P(ann["token"])), 400, "bad_request")
    # wrong method and unknown API routes keep the JSON shape
    err(c.get("/api/host/games"), 405, "bad_request")
    err(c.get("/api/play/nothing/here/at/all"), 404, "not_found")
    # lock / kick over HTTP
    assert post(c, f"/api/host/games/{code}/lock", {"locked": True}, H(ht)).get_json()["locked"] is True
    err(post(c, "/api/play/join", {"code": code, "name": "late"}), 403, "locked")
    assert post(c, "/api/play/join", {"code": code, "name": "x", "token": ann["token"]}).get_json()["player_id"] == ann["player_id"]
    st = post(c, f"/api/host/games/{code}/kick", {"player_id": ann["player_id"]}, H(ht)).get_json()
    assert st["players"] == []
    err(c.get(f"/api/play/{code}/state", headers=P(ann["token"])), 404, "kicked")
    assert c.get("/api/play/lookup?code=" + code + " ").get_json()["players"] == 0  # a stray space is forgiven


def test_http_rejects_oversized_bodies(web):
    c = web
    made = create_http(c)
    code = made["code"]
    big = json.dumps({"code": code, "name": "x" * 70_000})
    err(c.post("/api/play/join", data=big, content_type="application/json"), 413, "bad_request")
    ann = join_http(c, code, "ann")
    post(c, f"/api/host/games/{code}/start", headers=H(made["host_token"]))
    qid = hosting.STORE.get(code).qids[0]
    huge = json.dumps({"qid": qid, "response": "x" * 100_000})
    err(c.post(f"/api/play/{code}/answer", data=huge, content_type="application/json", headers=P(ann["token"])), 413, "bad_request")
    # chunked / unknown length is capped too
    res = c.post("/api/host/games", data=io.BytesIO(b'{"title": "' + b"x" * 70_000 + b'"}'), content_type="application/json", headers={"Content-Length": ""})
    assert res.status_code in (400, 413) and res.get_json()["reason"] == "bad_request"
    assert post(c, "/api/host/games", {"mode": "rush", "title": "x" * 5000}).status_code == 201  # large but < 64 KB: title is truncated
    # a 60 KB code answer is below the HTTP limit and is rejected by the grader instead
    fine = post(c, f"/api/play/{code}/run", {"qid": qid, "code": "x" * 60_000}, P(ann["token"]))
    assert fine.status_code == 409  # q1 is a choice question


def test_http_lan_and_qr(web):
    c = web
    app.config.pop("PYBLOOKET_BIND_HOST", None)
    app.config.pop("PYBLOOKET_PORT", None)
    info = c.get("/api/host/lan").get_json()
    assert info["lan"] is False and info["urls"] == [] and info["bind_host"] in ("localhost", "127.0.0.1")
    try:
        app.config["PYBLOOKET_BIND_HOST"] = "0.0.0.0"
        app.config["PYBLOOKET_PORT"] = 8123
        info = c.get("/api/host/lan").get_json()
        assert info["lan"] is True and info["port"] == 8123 and info["bind_host"] == "0.0.0.0"
        assert info["urls"] == hosting.lan_urls(8123)
        made = create_http(c)
        assert made["lan"] is True and made["join_urls"] == [u + f"/?join={made['code']}" for u in hosting.lan_urls(8123)]
        app.config["PYBLOOKET_BIND_HOST"] = "192.168.1.7"
        assert c.get("/api/host/lan").get_json()["urls"] == ["http://192.168.1.7:8123"]
        app.config["PYBLOOKET_BIND_HOST"] = "127.0.0.1"
        assert c.get("/api/host/lan").get_json() == {"lan": False, "bind_host": "127.0.0.1", "port": 8123, "urls": []}
    finally:
        app.config.pop("PYBLOOKET_BIND_HOST", None)
        app.config.pop("PYBLOOKET_PORT", None)
    # the fallback reads the address the browser used
    info = c.get("/api/host/lan", headers={"Host": "192.168.0.9:8000"}).get_json()
    assert info["lan"] is True and info["port"] == 8000


def test_http_qr_code(web):
    pytest.importorskip("segno")
    c = web
    res = c.get("/api/host/qr?text=" + "http://192.168.1.7:8000/?join=123456".replace("?", "%3F"))
    assert res.status_code == 200 and res.mimetype == "image/svg+xml"
    body = res.get_data(as_text=True)
    assert body.lstrip().startswith("<svg") and 'xmlns="http://www.w3.org/2000/svg"' in body and "<script" not in body
    err(c.get("/api/host/qr"), 404, "not_found")
    err(c.get("/api/host/qr?text="), 404, "not_found")
    err(c.get("/api/host/qr?text=" + "x" * 301), 404, "not_found")


def test_http_qr_without_segno(web, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "segno":
            raise ImportError("no segno")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    err(web.get("/api/host/qr?text=hello"), 404, "not_found")


def test_http_csv_escapes_names(web):
    c = web
    made = create_http(c)
    code, ht = made["code"], made["host_token"]
    join_http(c, code, "=HYPERLINK(1)")
    join_http(c, code, 'a,"b"')
    text = c.get(f"/api/host/games/{code}/results.csv?token={ht}").get_data(as_text=True)
    rows = list(csv.reader(io.StringIO(text)))
    assert {r[1] for r in rows[1:]} == {"'=HYPERLINK(1)", 'a,"b"'}


def test_http_real_typed_code_end_to_end_with_generated_questions(web):
    """The default question factory + the real sandbox: a typing-only live game, the reference
    solution of every code question is accepted, wrong code is not."""
    if not sandbox.enabled():
        pytest.skip("sandbox disabled")
    c = web
    web.install(None, code_enabled=True)
    made = post(c, "/api/host/games", {"mode": "live", "question_count": 6, "types": ["code"], "difficulty": 1, "topics": ["functions"]}).get_json()
    code, ht = made["code"], made["host_token"]
    ann = join_http(c, code, "ann")
    game = hosting.STORE.get(code)
    assert len(game.questions) == 6
    post(c, f"/api/host/games/{code}/start", headers=H(ht))
    for i, q in enumerate(game.questions):
        st = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()
        assert st["question"]["id"] == game.qids[i]
        if q.qtype == "code":
            assert "solution" not in json.dumps(st) and st["question"]["task"]["starter"] is not None
            ran = post(c, f"/api/play/{code}/run", {"qid": game.qids[i], "code": q.task.solution}, P(ann["token"]))
            assert ran.status_code == 200 and ran.get_json()["status"] in ("ok", "requirements")
            answer = q.task.solution
        else:
            answer = right(q)
        if i % 2 == 0:
            res = post(c, f"/api/play/{code}/answer", {"qid": game.qids[i], "response": answer}, P(ann["token"]))
            assert res.status_code == 200
            post(c, f"/api/host/games/{code}/skip", headers=H(ht))
            result = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()["result"]
            assert result["correct"] is True and result["points"] >= 100, (q.prompt, result)
        else:
            res = post(c, f"/api/play/{code}/answer", {"qid": game.qids[i], "response": wrong(q) if q.qtype != "code" else "pass"}, P(ann["token"]))
            post(c, f"/api/host/games/{code}/skip", headers=H(ht))
            result = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()["result"]
            assert result["correct"] is False and result["points"] == 0
        if i < 5:
            post(c, f"/api/host/games/{code}/next", headers=H(ht))
    st = post(c, f"/api/host/games/{code}/next", headers=H(ht)).get_json()
    assert st["phase"] == "finished" and st["players"][0]["correct"] == 3


def test_http_game_with_the_real_generators_is_playable_in_rush(web):
    c = web
    web.install(None, code_enabled=True)
    made = post(c, "/api/host/games", {"mode": "rush", "types": "mixed", "duration_min": 1}).get_json()
    code, ht = made["code"], made["host_token"]
    ann = join_http(c, code, "ann")
    post(c, f"/api/host/games/{code}/start", headers=H(ht))
    game = hosting.STORE.get(code)
    seen = set()
    for _ in range(12):
        st = c.get(f"/api/play/{code}/state", headers=P(ann["token"])).get_json()
        q = st["question"]
        assert q is not None
        assert_no_secrets({k: v for k, v in st.items() if k != "result"})
        seen.add(q["prompt"] + (q["code"] or ""))
        cur = game.players[ann["player_id"]].current["q"]
        resp = cur.task.solution if cur.qtype == "code" else right(cur)
        res = post(c, f"/api/play/{code}/answer", {"qid": q["id"], "response": resp}, P(ann["token"])).get_json()
        assert res["result"]["correct"] is True, (cur.prompt, res["result"])
    assert len(seen) >= 10  # no immediate repeats
    assert c.get(f"/api/host/games/{code}", headers=H(ht)).get_json()["players"][0]["answered"] == 12


# --------------------------------------------------------------------------
# Limits, long games, concurrency
# --------------------------------------------------------------------------


def test_creating_games_is_rate_limited():
    clock = Clock()
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]), clock, create_limit=3, max_games=10)
    for _ in range(3):
        store.create(live_settings(question_count=3))
    assert err_reason(store.create, live_settings(question_count=3)) == "rate_limited"
    clock.advance(61)
    store.create(live_settings(question_count=3))


def test_fifty_games_at_most_and_the_default_limit_allows_them():
    store = make_store(Pool([choice_q(1), choice_q(2), choice_q(3)]))
    for _ in range(games.MAX_GAMES):
        store.create(live_settings(question_count=3))
    assert err_reason(store.create, live_settings(question_count=3)) == "full"
    assert store.count() == games.MAX_GAMES


def test_forty_question_auto_advance_game_runs_to_the_end_after_one_long_silence():
    clock = Clock()
    factory = Endless()
    game = make_store(factory, clock).create({"mode": "live", "question_count": 40, "auto_advance": True})
    a = game.join("a")
    game.host_action(game.host_token, "start")
    clock.advance(40 * (15 + 1 + 10) + 5)
    st = game.host_state(game.host_token)
    assert st["phase"] == "finished" and len(st["summary"]["questions"]) == 40


def test_threaded_live_game_stays_consistent():
    clock = Clock()
    game = make_store(Pool([choice_q(i) for i in range(1, 6)]), clock).create(live_settings(question_count=5))
    people = [game.join(f"p{i}") for i in range(30)]
    game.host_action(game.host_token, "start")
    errors: list = []

    def play(person, idx):
        try:
            for i in range(5):
                st = game.player_state(person["token"])
                while st["phase"] != "question" or st["question_index"] != i:
                    if st["phase"] == "finished":
                        return
                    st = game.player_state(person["token"])
                    threading.Event().wait(0.001)
                q = game.questions[i]
                try:
                    game.answer(person["token"], st["question"]["id"], q.answer if idx % 2 == 0 else wrong(q))
                except GameError as exc:
                    assert exc.reason in ("bad_state", "too_late")
                game.player_state(person["token"])
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=play, args=(p, i)) for i, p in enumerate(people)]
    for t in threads:
        t.start()
    for i in range(5):
        while True:
            st = game.host_state(game.host_token)
            if st["phase"] == "reveal" and st["question_index"] == i:
                break
            threading.Event().wait(0.001)
        game.host_action(game.host_token, "next")
    for t in threads:
        t.join(10)
    assert not errors, errors
    st = game.host_state(game.host_token)
    assert st["phase"] == "finished"
    assert st["summary"]["totals"] == {"players": 30, "answers": 150, "correct": 75}
    assert sum(q["correct"] for q in st["summary"]["questions"]) == 75
    assert all(p["score"] == sum(game.players[p["id"]].records[i]["points"] for i in range(5)) for p in st["players"])


def test_threaded_rush_game_stays_consistent():
    clock = Clock()
    game = make_store(Endless(), clock).create({"mode": "rush", "duration_min": 5})
    people = [game.join(f"p{i}") for i in range(12)]
    game.host_action(game.host_token, "start")
    counts = [0] * len(people)
    errors: list = []

    def play(k, person):
        try:
            for n in range(25):
                st = game.player_state(person["token"])
                if st["question"] is None:  # cooling down after a wrong answer
                    clock.advance(0)  # (fake time does not move; just poll again)
                    cur = game.players[person["player_id"]]
                    cur.cooldown_until = None
                    continue
                cur = game.players[person["player_id"]].current["q"]
                res = game.answer(person["token"], st["question"]["id"], cur.answer if n % 3 else wrong(cur))
                assert res["accepted"]
                counts[k] += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=play, args=(k, p)) for k, p in enumerate(people)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    assert not errors, errors
    st = game.host_state(game.host_token)
    assert st["stats"]["questions_answered"] == sum(counts)
    assert [p["answered"] for p in sorted(st["players"], key=lambda p: int(p["id"][1:]))] == counts
