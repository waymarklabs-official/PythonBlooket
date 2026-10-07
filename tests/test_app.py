from __future__ import annotations

import pytest

from app import app
from pyblooket.questions import COURSE_TOPICS, QTYPES, TOPICS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def get_questions(client, query=""):
    return client.get(f"/api/questions?{query}").get_json()["questions"]


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<html" in res.data.lower()


def test_topics_endpoint(client):
    data = client.get("/api/topics").get_json()
    ids = {t["id"] for t in data["topics"]}
    assert ids and ids <= set(TOPICS)
    assert [d["points"] for d in data["difficulties"]] == [100, 250, 500]
    assert {q["id"] for q in data["qtypes"]} <= set(QTYPES)
    assert data["type_presets"]["mixed"] and data["type_presets"]["typing"]
    for t in data["topics"]:
        assert t["group"] in ("course", "extra")
        assert set(t["types"]) == set(QTYPES)


def test_default_topics_are_the_lesson_topics(client):
    qs = get_questions(client, "count=20")
    assert {q["topic"] for q in qs} <= set(COURSE_TOPICS)


def test_question_does_not_leak_answer(client):
    qs = get_questions(client, "count=20")
    assert len(qs) == 20
    for q in qs:
        assert "answer" not in q and "explanation" not in q and "solution" not in repr(q.get("task", ""))
        assert q["qtype"] in QTYPES
        if q["qtype"] == "choice":
            assert len(q["choices"]) == 4
        elif q["qtype"] == "blanks":
            assert q["blanks"] and all("accepted" not in b for b in q["blanks"])
        elif q["qtype"] == "match":
            assert q["match"]["items"] and q["match"]["options"] and "answer" not in q["match"]
        else:
            assert q["task"]["examples"] and "solution" not in q["task"]


@pytest.mark.parametrize("difficulty,points", [(1, 100), (2, 250), (3, 500)])
def test_difficulty_filter_and_points(client, difficulty, points):
    for q in get_questions(client, f"difficulty={difficulty}&count=10"):
        assert q["difficulty"] == difficulty
        assert q["points"] == points


def test_topic_filter(client):
    qs = get_questions(client, "topics=strings,conditionals&count=20")
    assert {q["topic"] for q in qs} <= {"strings", "conditionals"}


@pytest.mark.parametrize(
    "types,allowed",
    [
        ("choice", {"choice"}),
        ("typing", {"blanks", "code"}),
        ("choice,match", {"choice", "match"}),
        ("code", {"code"}),
    ],
)
def test_type_filter(client, types, allowed):
    qs = get_questions(client, f"types={types}&count=20")
    assert {q["qtype"] for q in qs} <= allowed


def test_multiple_choice_answer_flow(client):
    q = get_questions(client, "types=choice")[0]
    first = client.post("/api/answer", json={"id": q["id"], "response": 0}).get_json()
    assert {"correct", "answer", "points", "explanation", "qtype", "reveal", "detail"} <= set(first)
    assert first["correct"] == (first["answer"] == 0)
    assert first["reveal"] == {"answer": first["answer"]}
    assert first["points"] == (q["points"] if first["correct"] else 0)
    # A question can only be answered once.
    again = client.post("/api/answer", json={"id": q["id"], "response": first["answer"]})
    assert again.status_code == 404


def test_legacy_choice_field_still_works(client):
    q = get_questions(client, "types=choice")[0]
    first = client.post("/api/answer", json={"id": q["id"], "choice": 1}).get_json()
    assert first["correct"] == (first["answer"] == 1)


def test_timeout_answer_is_wrong(client):
    for t in ("choice", "blanks", "match", "code"):
        qs = get_questions(client, f"types={t}")
        if qs[0]["qtype"] != t:
            continue  # no generators of that format yet
        res = client.post("/api/answer", json={"id": qs[0]["id"], "response": None}).get_json()
        assert res["correct"] is False and res["points"] == 0


def test_typed_answers_are_graded(client):
    seen = set()
    for _ in range(40):
        for q in get_questions(client, "types=blanks,match,code&count=5"):
            seen.add(q["qtype"])
            res = client.post("/api/answer", json={"id": q["id"], "response": None}).get_json()
            assert not res["correct"]
            if q["qtype"] == "blanks":
                assert len(res["reveal"]["blanks"]) == len(q["blanks"])
            if q["qtype"] == "match":
                assert len(res["reveal"]["match"]) == len(q["match"]["items"])
            if q["qtype"] == "code":
                assert res["reveal"]["solution"].strip()
        if len(seen) == 3:
            break


def test_run_endpoint_only_for_code_questions(client):
    qs = [q for q in get_questions(client, "types=code&count=5") if q["qtype"] == "code"]
    if not qs:
        pytest.skip("no code generators yet")
    q = qs[0]
    res = client.post("/api/run", json={"id": q["id"], "code": q["task"]["starter"]})
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == len(q["task"]["examples"]) and not body["correct"]
    # a run never consumes the question
    ans = client.post("/api/answer", json={"id": q["id"], "response": q["task"]["starter"]})
    assert ans.status_code == 200
    assert client.post("/api/run", json={"id": q["id"], "code": "x"}).status_code == 404
    mc = get_questions(client, "types=choice")[0]
    assert client.post("/api/run", json={"id": mc["id"], "code": "x"}).status_code == 404


def test_unknown_question(client):
    assert client.post("/api/answer", json={"id": "nope", "response": 1}).status_code == 404
    assert client.post("/api/run", json={"id": "nope", "code": "x"}).status_code == 404
