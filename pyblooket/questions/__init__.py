"""Question generation: topic catalogue, registry and the public entry point."""

from __future__ import annotations

import importlib
import random

from .base import (
    DIFFICULTIES,
    DIFFICULTY_LABELS,
    DIFFICULTY_POINTS,
    QTYPE_LABELS,
    QTYPES,
    REGISTRY,
    TIME_FACTOR,
    GenerationError,
    Question,
)

# id -> (display name, emoji icon, short description). Order = display order.
#
# The first group follows the Unit 2 lessons ("CSF.2.x: Python") of the course, in the
# order they were taught; the questions copy the lessons' code, names and quiz wording.
# The "extra" group goes beyond the lessons (harder, for students who want a challenge).
TOPICS: dict[str, tuple[str, str, str]] = {
    # ---- Unit 2 lessons ----------------------------------------------------
    "variables": ("Variables", "📦", "Assignment, naming rules, snake_case, reassignment, f-strings, dynamic typing"),
    "datatypes": ("Data Types", "🧬", "int, float, str, bool, None, list, tuple, set, dict and type()"),
    "casting": ("Casting", "🔄", "int(), float(), str(), bool(), input() and ValueError"),
    "strings": ("Strings", "🔤", "Indexing, slicing, methods, split/join, f-strings, immutability"),
    "arithmetic": ("Arithmetic Operators", "➕", "+ - * / // % ** and the order of operations"),
    "booleans": ("Booleans & Operators", "✅", "True/False, comparisons, and / or / not, truthiness"),
    "conditionals": ("Conditionals", "🔀", "if / elif / else, combining conditions, nesting"),
    "while_loops": ("While Loops", "🔁", "Counters, infinite loops, while True + break"),
    "for_loops": ("For Loops", "🔂", "range(), looping over lists and strings, loops + decisions"),
    "functions": ("Functions", "🧩", "def, parameters & arguments, return, print vs return"),
    "classes": ("Classes & Methods", "🏛️", "Modules, import, classes, __init__, self, methods"),
    "challenges": ("Mini-Challenges", "🏆", "Write the program: the lab mini-challenges and Python Bingo tasks"),
    # ---- Beyond the lessons ------------------------------------------------
    "lists": ("Lists (extra)", "📋", "Indexing, methods, slicing, mutation & aliasing"),
    "dicts": ("Dictionaries (extra)", "📖", "Keys & values, get, methods, iteration"),
    "tuples_sets": ("Tuples & Sets (extra)", "🧺", "Unpacking, immutability, set operations"),
    "comprehensions": ("Comprehensions (extra)", "✨", "List/dict/set comprehensions, generator expressions"),
    "builtins": ("Built-in Functions (extra)", "🧰", "len, sorted, zip, enumerate, map, filter, min/max, sum"),
    "exceptions": ("Exceptions (extra)", "💥", "try/except/else/finally, raising, error types"),
    "recursion": ("Recursion (extra)", "🌀", "Base cases, tracing recursive calls"),
}

# Which lesson of the course each topic belongs to (shown in the topic picker).
TOPIC_LESSONS: dict[str, str] = {
    "variables": "CSF.2.A",
    "datatypes": "CSF.2.B",
    "casting": "CSF.2.C",
    "strings": "CSF.2.D",
    "arithmetic": "CSF.2.A1",
    "booleans": "CSF.2.E-F",
    "conditionals": "CSF.2.H",
    "while_loops": "CSF.2.I",
    "for_loops": "CSF.2.J",
    "functions": "CSF.2.L",
    "classes": "CSF.2.M",
    "challenges": "CSF.2.K / CSF.2.O",
}

COURSE_TOPICS = tuple(TOPIC_LESSONS)
EXTRA_TOPICS = tuple(t for t in TOPICS if t not in TOPIC_LESSONS)


def topic_group(topic: str) -> str:
    return "course" if topic in TOPIC_LESSONS else "extra"


_loaded = False


def load_generators() -> None:
    """Import every topic module so their @generator decorators register."""
    global _loaded
    if _loaded:
        return
    for topic in TOPICS:
        try:
            importlib.import_module(f"{__name__}.topics.{topic}")
        except ModuleNotFoundError as exc:
            if exc.name != f"{__name__}.topics.{topic}":
                raise
    _loaded = True


def generators_for(topic: str, difficulty: int, qtype: str | None = None):
    load_generators()
    return [
        g
        for g in REGISTRY
        if g.topic == topic and g.difficulty == difficulty and (qtype is None or g.qtype == qtype)
    ]


def available_topics() -> list[dict]:
    load_generators()
    out = []
    for tid, (name, icon, desc) in TOPICS.items():
        counts = {d: len(generators_for(tid, d)) for d in DIFFICULTIES}
        if sum(counts.values()) == 0:
            continue
        types = {t: sum(1 for g in REGISTRY if g.topic == tid and g.qtype == t) for t in QTYPES}
        out.append(
            {
                "id": tid,
                "name": name,
                "icon": icon,
                "description": desc,
                "group": topic_group(tid),
                "lesson": TOPIC_LESSONS.get(tid, ""),
                "generators": counts,
                "types": types,
            }
        )
    return out


# Weights used when the player picks "Mixed" difficulty.
MIXED_WEIGHTS = {1: 0.45, 2: 0.35, 3: 0.20}

# How often each question format is drawn when several are allowed (and available).
QTYPE_WEIGHTS = {"choice": 0.58, "blanks": 0.14, "match": 0.06, "code": 0.22}

# Presets the client offers ("Question types" picker) -> allowed formats.
TYPE_PRESETS = {
    "mixed": list(QTYPES),
    "choice": ["choice", "match"],  # point-and-click only
    "typing": ["blanks", "code"],  # the keyboard comes out
}


def parse_types(raw) -> list[str] | None:
    """'mixed' / 'choice' / 'typing' / 'choice,code' / ['blanks'] -> list of formats (None = all)."""
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip().lower()
        if raw in ("", "all", "any"):
            return None
        if raw in TYPE_PRESETS:
            return None if raw == "mixed" else list(TYPE_PRESETS[raw])
        raw = [p for p in raw.split(",") if p]
    types = [t for t in raw if t in QTYPES]
    return types or None


def generate_question(
    topics: list[str] | None = None,
    difficulty: int | None = None,
    rng: random.Random | None = None,
    max_attempts: int = 25,
    types: list[str] | None = None,
) -> Question:
    """Generate one random question.

    ``topics``: topic ids to draw from (None/empty = all the lesson topics).
    ``difficulty``: 1/2/3, or None for a weighted mix.
    ``types``: allowed formats (``QTYPES``); None = all, drawn with ``QTYPE_WEIGHTS``.
               If nothing matches the topics/difficulty, the filter is relaxed step by
               step (other difficulties, then other formats) rather than failing.
    """
    load_generators()
    rng = rng or random.Random()
    valid = [t for t in (topics or COURSE_TOPICS) if t in TOPICS]
    if not valid:
        valid = list(COURSE_TOPICS)
    wanted = [t for t in (types or QTYPES) if t in QTYPES] or list(QTYPES)
    last_err: Exception | None = None
    for _ in range(max_attempts):
        diff = difficulty
        if diff is None:
            diff = rng.choices(list(MIXED_WEIGHTS), weights=list(MIXED_WEIGHTS.values()))[0]
        pool: list = []
        for allowed, diffs in (
            (wanted, [diff]),
            (wanted, list(DIFFICULTIES)),
            (list(QTYPES), [diff]),
            (list(QTYPES), list(DIFFICULTIES)),
        ):
            pool = [g for t in valid for d in diffs for g in generators_for(t, d) if g.qtype in allowed]
            if pool:
                break
        if not pool:
            raise GenerationError("no generators registered")
        present = sorted({g.qtype for g in pool})
        qtype = rng.choices(present, weights=[QTYPE_WEIGHTS[t] for t in present])[0]
        pool = [g for g in pool if g.qtype == qtype]
        # Pick a topic first so topics with many generators don't dominate.
        topic = rng.choice(sorted({g.topic for g in pool}))
        gen = rng.choice([g for g in pool if g.topic == topic])
        try:
            return gen.fn(random.Random(rng.random()))
        except GenerationError as exc:
            last_err = exc
    raise GenerationError(f"could not generate a question: {last_err}")


__all__ = [
    "DIFFICULTIES",
    "DIFFICULTY_LABELS",
    "DIFFICULTY_POINTS",
    "COURSE_TOPICS",
    "EXTRA_TOPICS",
    "QTYPES",
    "QTYPE_LABELS",
    "QTYPE_WEIGHTS",
    "TIME_FACTOR",
    "TOPICS",
    "TOPIC_LESSONS",
    "TYPE_PRESETS",
    "Question",
    "GenerationError",
    "available_topics",
    "generate_question",
    "generators_for",
    "load_generators",
    "parse_types",
    "topic_group",
]
