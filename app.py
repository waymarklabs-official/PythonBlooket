"""PyBlooket web server.

Solo practice:   python app.py                 then open http://127.0.0.1:8000
Host a game:     python app.py --lan           then press "Host a game" and share the code
                 (players on the same Wi-Fi / network join from their own devices)

Environment: PORT (default 8000), HOST (overrides --lan), PYBLOOKET_CODE=off to turn the
typed-code questions off.
"""

from __future__ import annotations

import argparse
import os
import random
import threading
import uuid
from collections import OrderedDict

from flask import Flask, jsonify, request, send_from_directory

from pyblooket import sandbox
from pyblooket.questions import (
    DIFFICULTIES,
    DIFFICULTY_LABELS,
    DIFFICULTY_POINTS,
    QTYPE_LABELS,
    QTYPES,
    TIME_FACTOR,
    TOPICS,
    TYPE_PRESETS,
    GenerationError,
    Question,
    available_topics,
    generate_question,
    parse_types,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_PENDING = 20_000
MAX_BATCH = 20
MAX_RUNS_PER_QUESTION = 40

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.config["JSON_SORT_KEYS"] = False


class PendingQuestions:
    """Server-side answer store, so the client never sees the answer early.

    Bounded LRU: the oldest unanswered questions are forgotten first.
    """

    def __init__(self, limit: int = MAX_PENDING):
        self._items: OrderedDict[str, list] = OrderedDict()  # id -> [question, runs_used]
        self._lock = threading.Lock()
        self._limit = limit

    def add(self, q: Question) -> str:
        qid = uuid.uuid4().hex
        with self._lock:
            self._items[qid] = [q, 0]
            while len(self._items) > self._limit:
                self._items.popitem(last=False)
        return qid

    def pop(self, qid: str) -> Question | None:
        with self._lock:
            item = self._items.pop(qid, None)
        return item[0] if item else None

    def peek_for_run(self, qid: str) -> Question | None:
        """The question (not removed), counting one use of the "Run" button."""
        with self._lock:
            item = self._items.get(qid)
            if item is None or item[1] >= MAX_RUNS_PER_QUESTION:
                return None
            item[1] += 1
            return item[0]


pending = PendingQuestions()


def _parse_topics(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t for t in raw.split(",") if t in TOPICS]


def _parse_difficulty(raw: str | None) -> int | None:
    if raw in (None, "", "mixed"):
        return None
    try:
        d = int(raw)
    except ValueError:
        return None
    return d if d in DIFFICULTIES else None


def allowed_types(raw) -> list[str] | None:
    """The question formats a request may use (typed code is dropped when it is switched off)."""
    types = parse_types(raw)
    if sandbox.enabled():
        return types
    return [t for t in (types or QTYPES) if t != "code"] or ["choice"]


def question_payload(q: Question) -> dict:
    data = q.public_dict()
    data["id"] = pending.add(q)
    data["topic_name"], data["topic_icon"], _ = TOPICS[q.topic]
    return data


def answer_payload(q: Question, response) -> dict:
    """Grade ``response`` and build the JSON the client needs to show the outcome."""
    grade = q.grade(response)
    return {
        "correct": grade.correct,
        "answer": q.answer,
        "points": q.points if grade.correct else 0,
        "explanation": q.explanation,
        "qtype": q.qtype,
        "reveal": q.reveal(),
        "detail": grade.detail,
    }


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/topics")
def api_topics():
    return jsonify(
        {
            "topics": available_topics(),
            "difficulties": [
                {"id": d, "label": DIFFICULTY_LABELS[d], "points": DIFFICULTY_POINTS[d]}
                for d in DIFFICULTIES
            ],
            "qtypes": [
                {"id": t, "label": QTYPE_LABELS[t], "time_factor": TIME_FACTOR[t]}
                for t in QTYPES
                if t != "code" or sandbox.enabled()
            ],
            "type_presets": {k: [t for t in v if t != "code" or sandbox.enabled()] for k, v in TYPE_PRESETS.items()},
            "code_enabled": sandbox.enabled(),
        }
    )


@app.get("/api/questions")
def api_questions():
    """GET /api/questions?topics=a,b&difficulty=1|2|3|mixed&count=N&types=mixed|choice|typing|choice,code"""
    topics = _parse_topics(request.args.get("topics"))
    difficulty = _parse_difficulty(request.args.get("difficulty"))
    types = allowed_types(request.args.get("types"))
    try:
        count = max(1, min(MAX_BATCH, int(request.args.get("count", 1))))
    except ValueError:
        count = 1
    rng = random.Random()
    try:
        qs = [generate_question(topics, difficulty, rng, types=types) for _ in range(count)]
    except GenerationError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"questions": [question_payload(q) for q in qs]})


@app.post("/api/answer")
def api_answer():
    """POST {"id": "...", "response": <index | [text, ...] | [index, ...] | code>}.

    ``response`` is null when the player ran out of time.  (Old clients send
    ``"choice": <index>`` instead; that still works.)
    """
    body = request.get_json(silent=True) or {}
    q = pending.pop(str(body.get("id", "")))
    if q is None:
        return jsonify({"error": "unknown or already-answered question"}), 404
    response = body.get("response", body.get("choice"))
    return jsonify(answer_payload(q, response))


@app.post("/api/run")
def api_run():
    """POST {"id": "...", "code": "..."} -> try typed code on the example cases (not an answer)."""
    body = request.get_json(silent=True) or {}
    q = pending.peek_for_run(str(body.get("id", "")))
    if q is None or q.qtype != "code":
        return jsonify({"error": "unknown question, or too many test runs"}), 404
    return jsonify(q.run_examples(body.get("code")))


def _register_hosting() -> None:
    from pyblooket.hosting import bp as hosting_bp

    app.register_blueprint(hosting_bp)


def main() -> None:
    parser = argparse.ArgumentParser(description="PyBlooket server")
    parser.add_argument("--lan", action="store_true", help="listen on the whole network so other devices can join hosted games")
    parser.add_argument("--host", default=None, help="address to listen on (default 127.0.0.1, or 0.0.0.0 with --lan)")
    parser.add_argument("--port", type=int, default=None, help="port (default $PORT or 8000)")
    args = parser.parse_args()
    host = os.environ.get("HOST") or args.host or ("0.0.0.0" if args.lan else "127.0.0.1")
    port = args.port or int(os.environ.get("PORT", 8000))
    app.config["PYBLOOKET_BIND_HOST"] = host
    app.config["PYBLOOKET_PORT"] = port
    print(f"PyBlooket running on http://127.0.0.1:{port}")
    if host not in ("127.0.0.1", "localhost", "::1"):
        from pyblooket.hosting import lan_urls

        for url in lan_urls(port):
            print(f"  other devices can join at {url}")
    else:
        print("  (to let other devices join a hosted game, restart with:  python app.py --lan)")
    app.run(host=host, port=port, debug=False, threaded=True)


_register_hosting()

if __name__ == "__main__":
    main()
