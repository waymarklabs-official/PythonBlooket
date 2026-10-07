"""Hosted games: the rules.  Pure Python -- no Flask, no real clock (see :mod:`pyblooket.hosting`
for the HTTP layer and ``HOSTING_API`` for the JSON shapes).

Two modes, both server-authoritative (a client never sees an answer before the reveal):

``live``  Live Quiz.  Every player gets the same questions at the same time; each has a time
          limit; the host steps through ``question -> reveal -> question -> ...``.
``rush``  Time Rush.  Everyone races through their OWN stream of questions until the clock
          ends; answers are graded immediately.

Design notes
------------
* One :class:`GameStore` holds the games; each :class:`Game` has its own ``RLock``.  A request
  takes the lock, applies any time-based change (:meth:`Game.tick`), does its work and lets go.
  **Grading never happens under a lock**: typed code runs in a sandbox process and can take
  seconds.  An answer is stamped with its arrival time under the lock, graded outside it and
  stored afterwards; ``Player.inflight`` stops the same player submitting twice meanwhile.
* The game has ONE integer ``version`` that goes up on every visible change, so clients can poll
  ``?since=<version>`` and get a tiny ``unchanged`` reply.  Time-based changes (a deadline
  passing, the rush clock, a cooldown ending, a player going offline) are applied lazily at the
  start of each request and bump the version too.
* Live scores are applied at the reveal (so nothing leaks while a question is open); rush
  scores are applied the moment the answer is graded.
* Everything takes the clock as a parameter, so tests drive time with a fake one.
"""

from __future__ import annotations

import csv
import io
import random
import secrets
import threading
import time
import unicodedata
from collections import OrderedDict, deque
from typing import Any, Callable

from . import sandbox
from .questions import QTYPES, TOPICS, GenerationError, parse_types

# -- limits --------------------------------------------------------------------------------
MAX_GAMES = 50
MAX_PLAYERS = 200
MAX_NAME = 16
MAX_TITLE = 40
GRACE = 1.0  # seconds an answer may arrive after the live deadline
RUSH_COOLDOWN = 3.0  # seconds after a wrong answer in Time Rush
CONNECTED_WINDOW = 8.0  # polled within this many seconds = "connected"
AUTO_ADVANCE_DELAY = 10.0
CREATES_PER_MINUTE = 120  # a guard against a script hammering "create game" (each one generates questions)
FINISHED_TTL = 2 * 3600.0  # a finished game is deleted after 2 h ...
IDLE_TTL = 8 * 3600.0  # ... any game after 8 h without a request
MAX_RUNS_PER_QUESTION = 30
RECENT_QUESTIONS = 30  # rush: questions remembered per player to avoid repeats
MAX_REMEMBERED_REMOVED = 500  # tokens of kicked players remembered (to say "kicked", not "bad token")
STREAK_CAP_LIVE = 5
STREAK_CAP_RUSH = 10
DEFAULT_AVATAR = "🙂"

# Live time limits (seconds, scale "normal") by question format and difficulty (easy/medium/hard).
BASE_LIMITS = {
    "choice": (15, 20, 25),
    "match": (30, 40, 50),
    "blanks": (30, 40, 50),
    "code": (90, 120, 180),
}
TIME_SCALES = {"short": (7, 10), "normal": (1, 1), "long": (3, 2)}  # numerator, denominator

# reason -> HTTP status
STATUS = {
    "not_found": 404,
    "kicked": 404,
    "bad_token": 401,
    "locked": 403,
    "full": 403,
    "name_taken": 409,
    "bad_name": 400,
    "bad_state": 409,
    "finished": 409,
    "too_late": 409,
    "bad_request": 400,
    "rate_limited": 429,
}


class GameError(Exception):
    """A request that can't be done; ``reason`` is one of the documented codes."""

    def __init__(self, reason: str, message: str, *, status: int | None = None, extra: dict | None = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.status = status or STATUS.get(reason, 400)
        self.extra = extra or {}

    def payload(self) -> dict:
        return {"error": self.message, "reason": self.reason, **self.extra}


# --------------------------------------------------------------------------
# Scoring and time limits (pure functions)
# --------------------------------------------------------------------------


def time_limit(qtype: str, difficulty: int, scale: str = "normal") -> int:
    """Seconds a live question lasts: the table value x the scale, rounded up to a multiple of 5."""
    row = BASE_LIMITS.get(qtype, BASE_LIMITS["choice"])
    base = row[min(max(difficulty, 1), 3) - 1]
    num, den = TIME_SCALES.get(scale, TIME_SCALES["normal"])
    seconds = -(-base * num // den)  # ceil, in integers (no float fuzz)
    return -(-seconds // 5) * 5


def streak_bonus(base: int, streak_before: int, cap: int) -> int:
    return round(base * 0.1 * min(streak_before, cap))


def live_points(base: int, elapsed: float, limit: float, streak_before: int) -> tuple[int, int, int]:
    """(base, speed, streak) points of a CORRECT live answer."""
    elapsed = min(max(elapsed, 0.0), float(limit))
    speed = round(base * 0.5 * (1 - elapsed / limit))
    return base, speed, streak_bonus(base, streak_before, STREAK_CAP_LIVE)


def rush_points(base: int, streak_before: int) -> tuple[int, int, int]:
    return base, 0, streak_bonus(base, streak_before, STREAK_CAP_RUSH)


def competition_ranks(scores: list[int]) -> list[int]:
    """Ranks for scores sorted high -> low; ties share the better rank (100, 100, 50 -> 1, 1, 3)."""
    ranks: list[int] = []
    for i, s in enumerate(scores):
        ranks.append(ranks[-1] if i and s == scores[i - 1] else i + 1)
    return ranks


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------


def _clean_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    text = "".join(" " if ch.isspace() else ch for ch in value if ch.isspace() or unicodedata.category(ch)[0] != "C")
    return " ".join(text.split())[:limit]


def _int_setting(raw: dict, key: str, default: int, lo: int, hi: int) -> int:
    value = raw.get(key)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise GameError("bad_request", f"{key} must be a number")
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise GameError("bad_request", f"{key} must be a number") from None
    if isinstance(value, float) and value == value and abs(value) < 1e9:
        value = int(value)
    if not isinstance(value, int):
        raise GameError("bad_request", f"{key} must be a number")
    return max(lo, min(hi, value))


def normalize_settings(raw: Any, code_enabled: bool | None = None) -> dict:
    """Validate the body of "create a game"; returns the settings echoed in the host state.

    Out-of-range numbers are clamped; things of the wrong kind raise ``bad_request``.
    The extra keys ``_types`` (the format list to generate with) and ``_difficulty`` (1/2/3 or None)
    are for the game itself and are stripped from public payloads.
    """
    if not isinstance(raw, dict):
        raise GameError("bad_request", "Send a JSON object with the game settings.")
    if code_enabled is None:
        code_enabled = sandbox.enabled()
    mode = raw.get("mode", "live")
    if mode not in ("live", "rush"):
        raise GameError("bad_request", 'mode must be "live" or "rush"')

    topics_raw = raw.get("topics")
    if topics_raw in (None, ""):
        topics_raw = []
    if isinstance(topics_raw, str):
        topics_raw = [t for t in topics_raw.split(",") if t]
    if not isinstance(topics_raw, list) or not all(isinstance(t, str) for t in topics_raw):
        raise GameError("bad_request", "topics must be a list of topic ids")
    topics: list[str] = []
    for t in topics_raw:
        if t in TOPICS and t not in topics:
            topics.append(t)
    if topics_raw and not topics:
        raise GameError("bad_request", "None of those topics exist.")

    diff_raw = raw.get("difficulty", "mixed")
    if diff_raw in (None, "", "mixed"):
        difficulty: int | str = "mixed"
    else:
        try:
            difficulty = int(diff_raw)
        except (TypeError, ValueError):
            raise GameError("bad_request", 'difficulty must be 1, 2, 3 or "mixed"') from None
        if difficulty not in (1, 2, 3) or isinstance(diff_raw, bool):
            raise GameError("bad_request", 'difficulty must be 1, 2, 3 or "mixed"')

    types_raw = raw.get("types", "mixed")
    if types_raw is None:
        types_raw = "mixed"
    if not isinstance(types_raw, (str, list)):
        raise GameError("bad_request", "types must be a preset name or a list of formats")
    if isinstance(types_raw, list):
        types_raw = [t for t in types_raw if isinstance(t, str)]
    parsed = parse_types(types_raw)
    effective = parsed if code_enabled else ([t for t in (parsed or QTYPES) if t != "code"] or ["choice"])
    if isinstance(types_raw, str):
        preset = types_raw.strip().lower()
        shown_types: Any = preset if preset in ("mixed", "choice", "typing") else (parsed or "mixed")
    else:
        shown_types = parsed or "mixed"

    time_scale = raw.get("time_scale", "normal")
    if time_scale in (None, ""):
        time_scale = "normal"
    if time_scale not in TIME_SCALES:
        raise GameError("bad_request", 'time_scale must be "short", "normal" or "long"')
    auto = raw.get("auto_advance", False)
    if auto is None:
        auto = False
    if not isinstance(auto, bool):
        raise GameError("bad_request", "auto_advance must be true or false")

    return {
        "mode": mode,
        "title": _clean_text(raw.get("title"), MAX_TITLE),
        "topics": topics,
        "difficulty": difficulty,
        "types": shown_types,
        "question_count": _int_setting(raw, "question_count", 10, 3, 40),
        "duration_min": _int_setting(raw, "duration_min", 5, 1, 30),
        "time_scale": time_scale,
        "auto_advance": auto,
        "max_players": _int_setting(raw, "max_players", 60, 1, MAX_PLAYERS),
        "_types": effective,
        "_difficulty": None if difficulty == "mixed" else difficulty,
    }


def public_settings(settings: dict) -> dict:
    return {k: (list(v) if isinstance(v, list) else v) for k, v in settings.items() if not k.startswith("_")}


_BIDI = set("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u2028\u2029")


def validate_name(raw: Any) -> str:
    """Trim, collapse inner whitespace; 1..16 characters, no control characters."""
    if not isinstance(raw, str):
        raise GameError("bad_name", "Please type a name.")
    if any(unicodedata.category(ch) == "Cc" or ch in _BIDI for ch in raw.strip()):
        raise GameError("bad_name", "That name has characters we can't use.")
    name = " ".join(raw.split())
    if not any(unicodedata.category(ch) not in ("Cf", "Zs") for ch in name):
        raise GameError("bad_name", "Please type a name.")
    if len(name) > MAX_NAME:
        raise GameError("bad_name", f"Names can be at most {MAX_NAME} characters.")
    return name


def clean_avatar(raw: Any) -> str:
    if isinstance(raw, str):
        text = raw.strip()
        if text and len(text) <= 8 and not any(unicodedata.category(ch)[0] == "C" for ch in text):
            return text
    return DEFAULT_AVATAR


def _question_key(q) -> str:
    return f"{q.prompt}\n{q.code or ''}"


def _topic_meta(topic: str) -> tuple[str, str]:
    name, icon, _ = TOPICS.get(topic, (topic, "❓", ""))
    return name, icon


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------


class Player:
    """One participant (plain data; every field is guarded by the owning game's lock)."""

    def __init__(self, pid: str, name: str, avatar: str, token: str, now: float):
        self.id = pid
        self.name = name
        self.avatar = avatar
        self.token = token
        self.joined_at = now
        self.last_seen = now
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.correct = 0
        self.answered = 0
        self.total_ms = 0
        self.timed = 0  # answers that contributed to total_ms
        self.delta = 0
        self.inflight: set[str] = set()  # qids whose answers are being graded right now
        self.running = False  # a "Run" is executing
        self.runs_qid: str | None = None
        self.runs = 0
        self.last_detail: tuple[Any, dict] | None = None  # (index or qid, Grade.detail) of the last graded answer
        # live
        self.pending: dict | None = None  # graded answer to the open question (scored at the reveal)
        self.records: dict[int, dict] = {}  # question index -> lean record, once scored
        # rush
        self.current: dict | None = None  # {"qid", "q", "served_at"}
        self.generating = False
        self.cooldown_until: float | None = None
        self.cooldown_watch = False  # bump the version when the cooldown ends
        self.recent: deque[int] = deque(maxlen=RECENT_QUESTIONS)
        self.topics: dict[str, list[int]] = {}  # rush: topic -> [answered, correct, ms]
        self.last_result: dict | None = None  # rush: Result of the last answer


# --------------------------------------------------------------------------
# The game
# --------------------------------------------------------------------------

QuestionFactory = Callable[..., Any]


class Game:
    """One hosted game.  All public methods are thread-safe and raise :class:`GameError`."""

    def __init__(
        self,
        code: str,
        host_token: str,
        settings: dict,
        clock: Callable[[], float],
        rng: random.Random,
        factory: QuestionFactory,
        questions: list | None = None,
    ):
        self.code = code
        self.host_token = host_token
        self.settings = settings
        self.mode: str = settings["mode"]
        self.title: str = settings["title"]
        self.clock = clock
        self.rng = rng
        self.factory = factory
        self.lock = threading.RLock()
        now = clock()
        self.created_at = now
        self.last_activity = now
        self.finished_at: float | None = None
        self.version = 1
        self.phase = "lobby"
        self.locked = False
        self.players: dict[str, Player] = {}
        self._next_pid = 1
        self._removed: OrderedDict[str, None] = OrderedDict()  # tokens of kicked players
        self._ranked_cache: tuple[int, list[Player], dict[str, int]] | None = None
        self._conn_sig: frozenset[str] = frozenset()
        # live
        self.questions: list = list(questions or [])
        self.qids = [secrets.token_hex(6) for _ in self.questions]
        self.limits = [time_limit(q.qtype, q.difficulty, settings["time_scale"]) for q in self.questions]
        self._public_cache: dict[int, dict] = {}
        self.q_index = -1
        self.question_started: float | None = None
        self.deadline: float | None = None
        self.next_at: float | None = None
        self.scored_upto = -1  # highest question index whose scores are in
        # rush
        self.started_at: float | None = None
        self.ends_at: float | None = None

    # -- small helpers ---------------------------------------------------------------------
    def _bump(self) -> None:
        self.version += 1
        self._ranked_cache = None

    def _connected(self, p: Player, now: float) -> bool:
        return now - p.last_seen <= CONNECTED_WINDOW

    def _enter(self, now: float | None = None) -> float:
        """Start of every request (lock held): note activity and apply time-based changes."""
        now = self.clock() if now is None else now
        self.last_activity = now
        self._tick(now)
        return now

    def _auth_host(self, token: Any) -> None:
        if not isinstance(token, str) or not secrets.compare_digest(token.encode(), self.host_token.encode()):
            raise GameError("bad_token", "That host token isn't right.")

    def _auth_player(self, token: Any) -> Player:
        if isinstance(token, str) and token:
            tok = token.encode()
            found = None
            for p in self.players.values():
                if secrets.compare_digest(tok, p.token.encode()):
                    found = p
            if found is not None:
                return found
            if token in self._removed:
                raise GameError("kicked", "The host removed you from this game.")
        raise GameError("bad_token", "That player token isn't right.")

    def check_host(self, token: Any) -> None:
        with self.lock:
            self._auth_host(token)

    def _ranked(self) -> tuple[list[Player], dict[str, int]]:
        """Players best first (score, then name) and each player's competition rank."""
        if self._ranked_cache is None or self._ranked_cache[0] != self.version:
            order = sorted(self.players.values(), key=lambda p: (-p.score, p.name.lower(), p.joined_at, p.id))
            ranks = competition_ranks([p.score for p in order])
            self._ranked_cache = (self.version, order, {p.id: r for p, r in zip(order, ranks)})
        return self._ranked_cache[1], self._ranked_cache[2]

    # -- time ------------------------------------------------------------------------------
    def tick(self) -> None:
        with self.lock:
            self._tick(self.clock())

    def _tick(self, now: float) -> None:
        if self.mode == "live":
            for _ in range(2 * len(self.questions) + 3):  # a long gap may cross several steps
                # Steps are dated when they were DUE, not when somebody noticed (a long gap crosses several).
                if self.phase == "question" and self.deadline is not None and now >= self.deadline + GRACE:
                    self._end_question(self.deadline + GRACE)
                elif self.phase == "reveal" and self.next_at is not None and now >= self.next_at:
                    self._advance(self.next_at)
                else:
                    break
        elif self.phase == "running":
            if self.ends_at is not None and now >= self.ends_at:
                self._finish(now)
            else:
                for p in self.players.values():
                    if p.cooldown_watch and p.cooldown_until is not None and now >= p.cooldown_until:
                        p.cooldown_watch = False
                        self._bump()
        sig = frozenset(p.id for p in self.players.values() if self._connected(p, now))
        if sig != self._conn_sig:
            self._conn_sig = sig
            self._bump()

    # -- live flow -------------------------------------------------------------------------
    def _start_question(self, idx: int, now: float) -> None:
        self.q_index = idx
        self.phase = "question"
        self.question_started = now
        self.deadline = now + self.limits[idx]
        self.next_at = None
        for p in self.players.values():
            p.pending = None
        self._bump()

    def _answered_current(self, p: Player) -> bool:
        """Has ``p`` a stored answer to the OPEN question?"""
        return self.phase == "question" and p.pending is not None and p.pending["idx"] == self.q_index

    def _answered_shown(self, p: Player) -> bool:
        """Has ``p`` answered the question on screen (open, or revealed)?"""
        if self.phase == "question":
            return self._answered_current(p)
        rec = p.records.get(self.q_index) if self.phase == "reveal" else None
        return bool(rec and rec["answered"])

    def _end_question(self, now: float) -> None:
        """Question over (time up / everyone answered / skipped): score it and show the reveal."""
        idx = self.q_index
        for p in list(self.players.values()):
            if self.qids[idx] not in p.inflight:  # one still being graded is scored when it lands
                self._score_player(p, idx)
        self.scored_upto = max(self.scored_upto, idx)
        self.phase = "reveal"
        self.next_at = now + AUTO_ADVANCE_DELAY if self.settings["auto_advance"] else None
        self._bump()

    def _advance(self, now: float) -> None:
        if self.q_index + 1 < len(self.questions):
            self._start_question(self.q_index + 1, now)
        else:
            self._finish(now)

    def _finish(self, now: float) -> None:
        if self.phase == "question":
            self._end_question(now)
        if self.phase == "finished":
            return
        self.phase = "finished"
        self.finished_at = now
        self.next_at = None
        for p in self.players.values():
            p.cooldown_until = None
            p.cooldown_watch = False
        self._bump()

    def _score_player(self, p: Player, idx: int) -> None:
        """Turn the player's stored answer to question ``idx`` (or the lack of one) into points."""
        if idx in p.records:
            return
        q = self.questions[idx]
        pend = p.pending if p.pending is not None and p.pending["idx"] == idx else None
        rec = {"answered": False, "correct": False, "points": 0, "base": 0, "speed": 0, "streak_pts": 0, "ms": None, "choice": None}
        if pend is None:
            p.streak = 0
        else:
            correct = bool(pend["correct"])
            rec.update(answered=True, correct=correct, ms=pend["ms"], choice=pend["choice"])
            p.answered += 1
            p.total_ms += pend["ms"]
            p.timed += 1
            if correct:
                base, speed, bonus = live_points(q.points, pend["elapsed"], self.limits[idx], p.streak)
                rec.update(points=base + speed + bonus, base=base, speed=speed, streak_pts=bonus)
                p.correct += 1
                p.streak += 1
                p.best_streak = max(p.best_streak, p.streak)
            else:
                p.streak = 0
            p.pending = None
        rec["streak"] = p.streak
        p.records[idx] = rec
        p.score += rec["points"]
        p.delta = rec["points"]

    def _maybe_end_early(self, now: float) -> None:
        """Everyone currently in the game has answered -> reveal now."""
        if self.mode == "live" and self.phase == "question" and self.players:
            if all(self._answered_current(p) for p in self.players.values()):
                self._end_question(now)

    # -- public builders -------------------------------------------------------------------
    def _public_question(self, idx: int) -> dict:
        data = self._public_cache.get(idx)
        if data is None:
            q = self.questions[idx]
            data = q.public_dict()
            data["id"] = self.qids[idx]
            data["topic_name"], data["topic_icon"] = _topic_meta(q.topic)
            data["time_limit"] = self.limits[idx]
            self._public_cache[idx] = data
        return dict(data)

    def _public_rush_question(self, cur: dict) -> dict:
        q = cur["q"]
        data = q.public_dict()
        data["id"] = cur["qid"]
        data["topic_name"], data["topic_icon"] = _topic_meta(q.topic)
        return data

    def _entry(self, p: Player, ranks: dict[str, int], now: float) -> dict:
        return {
            "id": p.id,
            "name": p.name,
            "avatar": p.avatar,
            "score": p.score,
            "rank": ranks.get(p.id, 1),
            "streak": p.streak,
            "correct": p.correct,
            "answered": p.answered,
            "connected": self._connected(p, now),
            "answered_now": self._answered_shown(p) if self.mode == "live" else False,
            "delta": p.delta,
        }

    def _entries(self, now: float) -> list[dict]:
        order, ranks = self._ranked()
        if self.phase == "lobby":
            order = list(self.players.values())  # join order
        return [self._entry(p, ranks, now) for p in order]

    def _reveal_block(self, idx: int) -> dict:
        q = self.questions[idx]
        records = [r for p in self.players.values() if (r := p.records.get(idx)) is not None]
        answered = [r for r in records if r["answered"]]
        right = [r for r in answered if r["correct"]]
        if q.qtype == "choice":
            dist = [0] * len(q.choices)
            for r in answered:
                if isinstance(r["choice"], int) and 0 <= r["choice"] < len(dist):
                    dist[r["choice"]] += 1
        else:
            dist = [len(right), len(answered) - len(right), len(self.players) - len(answered)]
        fastest = None
        for p in self.players.values():
            r = p.records.get(idx)
            if r and r["correct"] and r["ms"] is not None and (fastest is None or r["ms"] < fastest["ms"]):
                fastest = {"name": p.name, "ms": r["ms"]}
        return {
            "correct_count": len(right),
            "answered_count": len(answered),
            "total": len(self.players),
            "distribution": dist,
            "answer": q.reveal(),
            "answer_text": q.answer_text(),
            "explanation": q.explanation,
            "fastest": fastest,
        }

    def _revealed_index(self) -> int:
        """The live question whose reveal is showing (reveal phase) or showed last (finished); -1 if none."""
        if self.mode != "live":
            return -1
        if self.phase == "reveal":
            return self.q_index
        if self.phase == "finished":
            return self.scored_upto
        return -1

    def _shown_index(self) -> int:
        """The live question on screen: the open one, the revealed one, or (finished) the last scored."""
        if self.mode != "live":
            return -1
        if self.phase in ("question", "reveal"):
            return self.q_index
        return self.scored_upto if self.phase == "finished" else -1

    def _summary(self, now: float) -> dict:
        order, ranks = self._ranked()
        questions: list[dict] = []
        if self.mode == "live":
            for idx in range(self.scored_upto + 1):
                q = self.questions[idx]
                recs = [r for p in self.players.values() if (r := p.records.get(idx)) is not None]
                ans = [r for r in recs if r["answered"]]
                right = [r for r in ans if r["correct"]]
                questions.append(
                    {
                        "index": idx + 1,
                        "prompt": q.prompt,
                        "qtype": q.qtype,
                        "topic": q.topic,
                        "difficulty": q.difficulty,
                        "answered": len(ans),
                        "correct": len(right),
                        "correct_pct": round(100 * len(right) / len(recs)) if recs else 0,
                        "avg_ms": round(sum(r["ms"] for r in ans) / len(ans)) if ans else 0,
                    }
                )
        else:
            agg: dict[str, list[int]] = {}
            for p in self.players.values():
                for topic, (n, ok, ms) in p.topics.items():
                    a = agg.setdefault(topic, [0, 0, 0])
                    a[0] += n
                    a[1] += ok
                    a[2] += ms
            for i, (topic, (n, ok, ms)) in enumerate(sorted(agg.items(), key=lambda kv: (-kv[1][0], kv[0]))):
                questions.append(
                    {
                        "index": i + 1,
                        "prompt": _topic_meta(topic)[0],
                        "qtype": "mixed",
                        "topic": topic,
                        "difficulty": None,
                        "answered": n,
                        "correct": ok,
                        "correct_pct": round(100 * ok / n) if n else 0,
                        "avg_ms": round(ms / n) if n else 0,
                    }
                )
        return {
            "podium": [self._entry(p, ranks, now) for p in order[:3]],
            "questions": questions,
            "totals": {
                "players": len(self.players),
                "answers": sum(p.answered for p in self.players.values()),
                "correct": sum(p.correct for p in self.players.values()),
            },
        }

    def _result(self, p: Player, idx: int) -> dict | None:
        """The player's full Result for scored live question ``idx``."""
        rec = p.records.get(idx)
        if rec is None:
            return None
        q = self.questions[idx]
        detail = p.last_detail[1] if p.last_detail and p.last_detail[0] == idx else {}
        return {
            "qid": self.qids[idx],
            "correct": rec["correct"],
            "points": rec["points"],
            "base_points": rec["base"],
            "speed_points": rec["speed"],
            "streak_points": rec["streak_pts"],
            "streak": rec["streak"],
            "time_ms": rec["ms"],
            "late": False,
            "answered": rec["answered"],
            "explanation": q.explanation,
            "reveal": q.reveal(),
            "answer_text": q.answer_text(),
            "detail": detail,
            "qtype": q.qtype,
        }

    # -- host side -------------------------------------------------------------------------
    def host_state(self, token: Any, since: int | None = None) -> dict:
        with self.lock:
            self._auth_host(token)
            now = self._enter()
            return self._host_state(now, since)

    def host_snapshot(self) -> dict:
        """The full host state, for the reply to "create game" (the caller just made the token)."""
        with self.lock:
            return self._host_state(self._enter())

    def _unchanged(self, now: float) -> dict:
        return {"unchanged": True, "version": self.version, "server_time": now}

    def _host_state(self, now: float, since: int | None = None) -> dict:
        if since is not None and since == self.version:
            return self._unchanged(now)
        live = self.mode == "live"
        shown = self._shown_index()
        ridx = self._revealed_index()
        answered_count = sum(1 for p in self.players.values() if self._answered_shown(p))
        return {
            "version": self.version,
            "server_time": now,
            "unchanged": False,
            "code": self.code,
            "mode": self.mode,
            "title": self.title,
            "phase": self.phase,
            "settings": public_settings(self.settings),
            "locked": self.locked,
            "created_at": self.created_at,
            "players": self._entries(now),
            "question_index": shown,
            "question_total": len(self.questions) if live else None,
            "question": self._public_question(shown) if shown >= 0 else None,
            "question_started": self.question_started if live else None,
            "deadline": self.deadline if live else None,
            "answers": {"count": answered_count, "total": len(self.players)} if live else None,
            "reveal": self._reveal_block(ridx) if ridx >= 0 else None,
            "next_at": self.next_at if live else None,
            "started_at": self.started_at,
            "ends_at": self.ends_at,
            "stats": (
                {
                    "questions_answered": sum(p.answered for p in self.players.values()),
                    "correct": sum(p.correct for p in self.players.values()),
                }
                if not live
                else None
            ),
            "summary": self._summary(now) if self.phase == "finished" else None,
        }

    def host_action(self, token: Any, action: str, body: dict | None = None) -> dict:
        """start | skip | next | end | lock | kick -> the updated host state."""
        body = body if isinstance(body, dict) else {}
        with self.lock:
            self._auth_host(token)
            now = self._enter()
            handler = {
                "start": self._act_start,
                "skip": self._act_skip,
                "next": self._act_next,
                "end": self._act_end,
                "lock": self._act_lock,
                "kick": self._act_kick,
            }.get(action)
            if handler is None:
                raise GameError("not_found", f"Unknown action {action!r}.", status=404)
            handler(now, body)
            return self._host_state(now)

    def _act_start(self, now: float, body: dict) -> None:
        if self.phase != "lobby":
            raise GameError("bad_state", "The game has already started.")
        if not self.players:
            raise GameError("bad_state", "Wait for at least one player to join.")
        if self.mode == "live":
            self._start_question(0, now)
        else:
            self.phase = "running"
            self.started_at = now
            self.ends_at = now + self.settings["duration_min"] * 60
            self._bump()

    def _act_skip(self, now: float, body: dict) -> None:
        if self.mode != "live" or self.phase != "question":
            raise GameError("bad_state", "There is no open question to skip.")
        self._end_question(now)

    def _act_next(self, now: float, body: dict) -> None:
        if self.mode != "live" or self.phase != "reveal":
            raise GameError("bad_state", "Show the answer first (Skip), then go to the next question.")
        self._advance(now)

    def _act_end(self, now: float, body: dict) -> None:
        if self.phase != "finished":
            self._finish(now)

    def _act_lock(self, now: float, body: dict) -> None:
        locked = body.get("locked")
        if not isinstance(locked, bool):
            raise GameError("bad_request", 'Send {"locked": true} or {"locked": false}.')
        if locked != self.locked:
            self.locked = locked
            self._bump()

    def _act_kick(self, now: float, body: dict) -> None:
        pid = body.get("player_id")
        p = self.players.get(pid) if isinstance(pid, str) else None
        if p is None:
            raise GameError("not_found", "No such player.", status=404)
        self._remove(p, now, kicked=True)

    def _remove(self, p: Player, now: float, *, kicked: bool) -> None:
        self.players.pop(p.id, None)
        if kicked:
            self._removed[p.token] = None
            while len(self._removed) > MAX_REMEMBERED_REMOVED:
                self._removed.popitem(last=False)
        self._bump()
        self._maybe_end_early(now)

    # -- player side -----------------------------------------------------------------------
    def lookup(self) -> dict:
        with self.lock:
            self._enter()
            return {
                "exists": True,
                "title": self.title,
                "mode": self.mode,
                "phase": self.phase,
                "locked": self.locked,
                "players": len(self.players),
            }

    def join(self, name: Any, avatar: Any = None, token: Any = None) -> dict:
        with self.lock:
            now = self._enter()
            p: Player | None = None
            if isinstance(token, str) and token:
                tok = token.encode()
                for cand in self.players.values():
                    if secrets.compare_digest(tok, cand.token.encode()):
                        p = cand
            if p is not None:  # rejoin
                p.last_seen = now
            else:
                if self.phase == "finished":
                    raise GameError("finished", "This game is already over.")
                if self.locked:
                    raise GameError("locked", "The host has locked this game.")
                clean = validate_name(name)
                if len(self.players) >= min(self.settings["max_players"], MAX_PLAYERS):
                    raise GameError("full", "This game is full.")
                folded = clean.casefold()
                if any(q.name.casefold() == folded for q in self.players.values()):
                    raise GameError("name_taken", "Someone is already using that name.")
                p = Player(f"p{self._next_pid}", clean, clean_avatar(avatar), secrets.token_urlsafe(18), now)
                self._next_pid += 1
                self.players[p.id] = p
                self._conn_sig |= {p.id}
                self._bump()
        self._ensure_question(p)
        with self.lock:
            now = self.clock()
            return {"player_id": p.id, "token": p.token, "code": self.code, "state": self._player_state(p, now, None)}

    def leave(self, token: Any) -> dict:
        with self.lock:
            p = self._auth_player(token)
            now = self._enter()
            if self.phase != "finished":  # after the end, leaving must not erase a student from the results
                self._remove(p, now, kicked=False)
            return {"ok": True}

    def player_state(self, token: Any, since: int | None = None) -> dict:
        with self.lock:
            p = self._auth_player(token)
            p.last_seen = self.clock()
            self._enter()
        self._ensure_question(p)
        with self.lock:
            if self.players.get(p.id) is not p:
                raise GameError("kicked", "The host removed you from this game.")
            return self._player_state(p, self.clock(), since)

    def _player_state(self, p: Player, now: float, since: int | None) -> dict:
        if since is not None and since == self.version:
            return self._unchanged(now)
        order, ranks = self._ranked()
        live = self.mode == "live"
        ridx = self._revealed_index()
        shown = self._shown_index()
        question = None
        result = None
        reveal = None
        my_answer = None
        cooldown = None
        if live:
            if shown >= 0:
                question = self._public_question(shown)
            if self.phase == "question" and (self._answered_current(p) or self.qids[self.q_index] in p.inflight):
                my_answer = {"submitted": True}
            if ridx >= 0:
                result = self._result(p, ridx)
                reveal = self._reveal_block(ridx)
                reveal.pop("fastest", None)
        else:
            result = p.last_result
            if self.phase == "running":
                if p.cooldown_until is not None and now < p.cooldown_until:
                    cooldown = p.cooldown_until
                elif p.current is not None:
                    question = self._public_rush_question(p.current)
        show_board = (live and self.phase in ("reveal", "finished")) or (not live and self.phase in ("running", "finished"))
        board = [
            {"id": q.id, "name": q.name, "avatar": q.avatar, "score": q.score, "rank": ranks[q.id], "delta": q.delta}
            for q in order[:5]
        ] if show_board else []
        final = None
        if self.phase == "finished":
            final = {
                "rank": ranks.get(p.id, 1),
                "score": p.score,
                "correct": p.correct,
                "answered": p.answered,
                "avg_ms": round(p.total_ms / p.timed) if p.timed else 0,
                "best_streak": p.best_streak,
                "podium": [
                    {"name": q.name, "avatar": q.avatar, "score": q.score, "rank": ranks[q.id]} for q in order[:3]
                ],
                "players_total": len(self.players),
            }
        return {
            "version": self.version,
            "server_time": now,
            "unchanged": False,
            "code": self.code,
            "mode": self.mode,
            "title": self.title,
            "phase": self.phase,
            "me": {
                "id": p.id,
                "name": p.name,
                "avatar": p.avatar,
                "score": p.score,
                "rank": ranks.get(p.id, 1),
                "streak": p.streak,
                "correct": p.correct,
                "answered": p.answered,
            },
            "players_total": len(self.players),
            "question_index": shown if live else p.answered,
            "question_total": len(self.questions) if live else None,
            "question": question,
            "deadline": self.deadline if live and self.phase in ("question", "reveal") else None,
            "my_answer": my_answer,
            "result": result,
            "reveal": reveal,
            "cooldown_until": cooldown,
            "started_at": self.started_at,
            "ends_at": self.ends_at,
            "leaderboard": board,
            "final": final,
        }

    # -- answering -------------------------------------------------------------------------
    def answer(self, token: Any, qid: Any, response: Any) -> dict:
        """Submit an answer.  Live: ``{"accepted": True, "state"}`` (nothing revealed yet);
        rush: also ``"result"`` and the state already holds the next question."""
        if not isinstance(qid, str):
            raise GameError("bad_request", "Send the question id (qid).")
        dup = {"accepted": False}
        with self.lock:
            p = self._auth_player(token)
            p.last_seen = self.clock()
            now = self._enter()
            if self.mode == "live":
                q, idx = self._open_live_question(p, qid, dup)
                elapsed = min(max(now - (self.question_started or now), 0.0), float(self.limits[idx]))
            else:
                q, idx = self._open_rush_question(p, qid, now, dup)
                elapsed = max(0.0, now - p.current["served_at"])
            p.inflight.add(qid)
        # -- graded OUTSIDE the lock (typed code runs in a sandbox process) --
        try:
            grade = q.grade(response)
            correct, detail = bool(grade.correct), dict(grade.detail)
        except Exception as exc:  # noqa: BLE001 - a broken answer is a wrong answer, never a 500
            correct, detail = False, {"error": type(exc).__name__}
        generate = False
        choice = response if q.qtype == "choice" and isinstance(response, int) and not isinstance(response, bool) else None
        with self.lock:
            p.inflight.discard(qid)
            if self.players.get(p.id) is not p:
                raise GameError("kicked", "The host removed you from this game.")
            end = self.clock()
            if self.mode == "live":
                pend = {"idx": idx, "correct": correct, "elapsed": elapsed, "ms": round(elapsed * 1000), "choice": choice}
                p.pending = pend
                p.last_detail = (idx, detail)
                if idx <= self.scored_upto:  # the reveal came while we were grading: score it now
                    self._score_player(p, idx)
                    self._bump()
                else:
                    self._bump()
                    self._maybe_end_early(end)
                result = None
            else:
                result = self._apply_rush_answer(p, q, qid, correct, detail, elapsed, end)
                p.generating = generate = self.phase == "running"
        if self.mode == "rush" and generate:
            self._finish_generation(p)
        with self.lock:
            out = {"accepted": True, "state": self._player_state(p, self.clock(), None)}
            if result is not None:
                out["result"] = result
            return out

    def _known_qid(self, qid: str) -> bool:
        return qid in self.qids[: self.q_index + 1]

    def _open_live_question(self, p: Player, qid: str, dup: dict):
        """The current live question if ``p`` may answer it now (lock held)."""
        if self.phase == "question" and qid == self.qids[self.q_index]:
            if qid in p.inflight or self._answered_current(p):
                raise GameError("bad_state", "You already answered this question.", extra=dup)
            return self.questions[self.q_index], self.q_index
        if self.phase in ("reveal", "finished") and self._known_qid(qid):
            raise GameError("too_late", "Time's up for that question.", extra=dup)
        if self.phase == "question" and self._known_qid(qid):
            raise GameError("too_late", "Time's up for that question.", extra=dup)
        raise GameError("bad_state", "That isn't the question being asked.", extra=dup)

    def _open_rush_question(self, p: Player, qid: str, now: float, dup: dict):
        if self.phase == "finished":
            raise GameError("too_late", "The clock has run out.", extra=dup)
        if self.phase != "running":
            raise GameError("bad_state", "The game hasn't started.", extra=dup)
        cur = p.current
        if p.inflight:
            raise GameError("bad_state", "Your last answer is still being checked.", extra=dup)
        if cur is None or cur["qid"] != qid:
            raise GameError("bad_state", "That isn't your current question.", extra=dup)
        if p.cooldown_until is not None and now < p.cooldown_until:
            raise GameError("bad_state", "Your engine is still cooling down.", extra=dup)
        return cur["q"], p.answered

    def _apply_rush_answer(self, p: Player, q, qid: str, correct: bool, detail: dict, elapsed: float, now: float) -> dict:
        ms = round(elapsed * 1000)
        base = pts_speed = bonus = 0
        if correct:
            base, pts_speed, bonus = rush_points(q.points, p.streak)
            p.correct += 1
            p.streak += 1
            p.best_streak = max(p.best_streak, p.streak)
        else:
            p.streak = 0
        points = base + pts_speed + bonus
        p.answered += 1
        p.total_ms += ms
        p.timed += 1
        p.score += points
        p.delta = points
        t = p.topics.setdefault(q.topic, [0, 0, 0])
        t[0] += 1
        t[1] += 1 if correct else 0
        t[2] += ms
        p.recent.append(hash(_question_key(q)))
        p.last_detail = (qid, detail)
        p.current = None
        if not correct:
            p.cooldown_until = now + RUSH_COOLDOWN
            p.cooldown_watch = True
        result = {
            "qid": qid,
            "correct": correct,
            "points": points,
            "base_points": base,
            "speed_points": pts_speed,
            "streak_points": bonus,
            "streak": p.streak,
            "time_ms": ms,
            "late": False,
            "answered": True,
            "explanation": q.explanation,
            "reveal": q.reveal(),
            "answer_text": q.answer_text(),
            "detail": detail,
            "qtype": q.qtype,
        }
        p.last_result = result
        self._bump()
        return result

    def run_examples(self, token: Any, qid: Any, code: Any) -> dict:
        """The "Run" button: try typed code on the visible examples (never an answer)."""
        if not isinstance(qid, str):
            raise GameError("bad_request", "Send the question id (qid).")
        if not isinstance(code, str):
            raise GameError("bad_request", "Send the code as text.")
        with self.lock:
            p = self._auth_player(token)
            p.last_seen = self.clock()
            now = self._enter()
            if self.mode == "live":
                q, _ = self._open_live_question(p, qid, {})
            else:
                q, _ = self._open_rush_question(p, qid, now, {})
            if q.qtype != "code":
                raise GameError("bad_state", "This question can't be run.")
            if p.runs_qid != qid:
                p.runs_qid, p.runs = qid, 0
            if p.runs >= MAX_RUNS_PER_QUESTION or p.running:
                raise GameError("rate_limited", "Slow down - too many test runs for this question.")
            p.runs += 1
            p.running = True
        try:
            return q.run_examples(code)
        finally:
            with self.lock:
                p.running = False

    # -- rush question stream ----------------------------------------------------------------
    def _ensure_question(self, p: Player) -> None:
        """Rush: make sure the player has a current question (generated outside the lock)."""
        if self.mode != "rush":
            return
        with self.lock:
            if self.phase != "running" or p.current is not None or p.generating or self.players.get(p.id) is not p:
                return
            p.generating = True
        self._finish_generation(p)

    def _finish_generation(self, p: Player) -> None:
        """Generate the player's next rush question (``p.generating`` was set under the lock)."""
        q = None
        try:
            with self.lock:
                seed = self.rng.random()
                recent = set(p.recent)
            rng = random.Random(seed)
            for _ in range(8):
                q = self.factory(
                    self.settings["topics"] or None,
                    self.settings["_difficulty"],
                    rng,
                    types=self.settings["_types"],
                )
                if hash(_question_key(q)) not in recent:
                    break
        except GenerationError:
            q = None
        finally:
            with self.lock:
                p.generating = False
                if q is not None and self.phase == "running" and p.current is None and self.players.get(p.id) is p:
                    now = self.clock()
                    served = max(now, p.cooldown_until or 0.0)
                    p.current = {"qid": secrets.token_hex(6), "q": q, "served_at": served}
                    self._bump()

    # -- results export ----------------------------------------------------------------------
    def csv_text(self, token: Any) -> str:
        with self.lock:
            self._auth_host(token)
            self._enter()
            order, ranks = self._ranked()
            live = self.mode == "live"
            nq = self.scored_upto + 1 if live else 0
            out = io.StringIO()
            w = csv.writer(out, lineterminator="\n")
            w.writerow(
                ["Rank", "Name", "Score", "Correct", "Answered", "Accuracy %", "Avg answer time (s)", "Best streak"]
                + [f"Q{i + 1}" for i in range(nq)]
            )
            for p in order:
                acc = round(100 * p.correct / p.answered) if p.answered else 0
                avg = round(p.total_ms / p.timed / 1000, 1) if p.timed else 0
                w.writerow(
                    [ranks[p.id], csv_safe(p.name), p.score, p.correct, p.answered, acc, avg, p.best_streak]
                    + [p.records.get(i, {}).get("points", 0) for i in range(nq)]
                )
            return out.getvalue()


def csv_safe(text: str) -> str:
    """Stop spreadsheets treating a name as a formula."""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


# --------------------------------------------------------------------------
# The store
# --------------------------------------------------------------------------


class GameStore:
    """All running games (in memory).  ``question_factory(topics, difficulty, rng, types=...)``
    defaults to :func:`pyblooket.questions.generate_question`."""

    def __init__(
        self,
        question_factory: QuestionFactory | None = None,
        clock: Callable[[], float] = time.time,
        rng: random.Random | None = None,
        code_enabled: bool | None = None,
        max_games: int = MAX_GAMES,
        create_limit: int | None = CREATES_PER_MINUTE,
    ):
        self._factory = question_factory
        self.clock = clock
        self.rng = rng or random.Random()
        self.code_enabled = code_enabled
        self.max_games = max_games
        self.create_limit = create_limit
        self._created: deque[float] = deque()  # when recent games were created (sliding minute)
        self._games: dict[str, Game] = {}
        self._lock = threading.Lock()

    def factory(self) -> QuestionFactory:
        if self._factory is not None:
            return self._factory
        from .questions import generate_question  # lazy: importing the topics takes a moment

        return generate_question

    def count(self) -> int:
        with self._lock:
            return len(self._games)

    def create(self, raw_settings: Any, clock: Callable[[], float] | None = None) -> Game:
        clock = clock or self.clock
        settings = normalize_settings(raw_settings, self.code_enabled)
        factory = self.factory()
        with self._lock:
            now = clock()
            while self._created and now - self._created[0] >= 60.0:
                self._created.popleft()
            if self.create_limit is not None and len(self._created) >= self.create_limit:
                raise GameError("rate_limited", "Too many games were created just now. Wait a minute and try again.")
            self._created.append(now)
            seed = self.rng.random()
        rng = random.Random(seed)
        questions: list = []
        if settings["mode"] == "live":
            questions = self._generate_live(settings, factory, rng)  # no lock: this can take a moment
        with self._lock:
            now = clock()
            self._purge(now)
            if len(self._games) >= self.max_games:  # still full: sacrifice the oldest finished game
                done = sorted((g for g in self._games.values() if g.finished_at is not None), key=lambda g: g.finished_at)
                if done:
                    del self._games[done[0].code]
            if len(self._games) >= self.max_games:
                raise GameError("full", "The server is hosting as many games as it can. Try again in a while.", status=503)
            while True:
                code = f"{100000 + secrets.randbelow(900000)}"
                if code not in self._games:
                    break
            if questions:
                settings["question_count"] = len(questions)  # fewer than asked if the topics ran dry
            game = Game(code, secrets.token_urlsafe(24), settings, clock, rng, factory, questions)
            self._games[code] = game
            return game

    @staticmethod
    def _generate_live(settings: dict, factory: QuestionFactory, rng: random.Random) -> list:
        want = settings["question_count"]
        seen: set[str] = set()
        out: list = []
        errors = 0
        for _ in range(want * 12):
            if len(out) >= want:
                break
            try:
                q = factory(settings["topics"] or None, settings["_difficulty"], rng, types=settings["_types"])
            except GenerationError:
                errors += 1
                if errors > 20:
                    break
                continue
            key = _question_key(q)
            if key in seen:
                continue
            seen.add(key)
            out.append(q)
        if len(out) < 3:
            raise GameError(
                "bad_request",
                "Couldn't make enough different questions for those settings - pick more topics or formats.",
                status=422,
            )
        return out

    def get(self, code: Any) -> Game:
        with self._lock:
            game = self._games.get(code) if isinstance(code, str) else None
        if game is None:
            raise GameError("not_found", "No game with that code.")
        return game

    def _purge(self, now: float) -> None:
        for code, g in list(self._games.items()):
            if (g.finished_at is not None and now - g.finished_at > FINISHED_TTL) or now - g.last_activity > IDLE_TTL:
                del self._games[code]

    def purge(self) -> None:
        with self._lock:
            self._purge(self.clock())
