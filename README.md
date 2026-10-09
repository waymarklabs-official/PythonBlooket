# PyBlooket 🐍

A Blooket-style Python quiz game for the classroom. Questions are generated on the fly (so they never run out), follow the
**Unit 2: Python Console** lessons (CSF.2.A – CSF.2.O) and mix three kinds of answers:

| Format | What the player does | How it is graded |
|---|---|---|
| **Multiple choice** | picks one of four answers | by index |
| **Fill in the blanks** | types the missing pieces of a code snippet (like the `4` in `word[0:4]` or `strip` in `text.strip()`) | compared with the accepted spellings |
| **Matching** | matches each item to its type / result / meaning | by index |
| **Write the code** | types real Python – an expression, a function or a whole program that uses `input()` | **run in a sandbox** against hidden tests |

You can play **solo** (five game modes against bots) or **host a live game** for the whole class: students join from their own
phones or laptops with a 6-digit code, and the leaderboard is on your projector.

## Quick start

```bash
python3 -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                          # solo practice: http://127.0.0.1:8000
python app.py --lan                                    # hosting: lets other devices on your network connect
```

`PORT=9000 python app.py` changes the port (default **8000** – port 5000 is taken by AirPlay on recent Macs).

## Hosting a game in class

1. Start the server with **`python app.py --lan`** on the teacher computer (it prints the address students should open, e.g.
   `http://192.168.1.23:8000`). Everyone must be on the same Wi-Fi / network. If macOS asks *"Allow incoming network
   connections?"* choose **Allow**. Some school Wi-Fi blocks devices from talking to each other ("client isolation") – if students
   can't connect, ask IT or use the teacher's phone hotspot.
2. Open that address on the projector computer and press **Host a game**. Pick a mode, the topics, the difficulty and the kinds of
   questions (*Mixed*, *Multiple choice* or *Typing*), then **Create game**.
3. The lobby shows a big join code, the address and a QR code. Students open the address (or scan the QR code), type the code,
   choose a name and a blook – and appear in the lobby. You can kick a player or lock the game.
4. Press **Start game**.
   * **Live Quiz** – everyone gets the same question at the same time. Correct answers earn the question's points plus a speed
     bonus (up to +50 %) and a streak bonus (up to +50 %). After every question the screen shows the right answer, how many got
     it and the top five; press **Next** (or turn on auto-advance).
   * **Time Rush** – everyone races through their own stream of questions until the clock runs out. Streaks multiply points;
     a wrong answer cools the player's engine down for three seconds.
5. At the end you get a podium, the full standings, the hardest questions, and a **CSV** to open in a spreadsheet.

Games live in the server's memory: closing the server ends every game. Closing the host *page* is fine – reopen PyBlooket and press
**Resume**.

## Practice solo

Pick a mode (Gold Quest, Python Race, Survival, Time Attack, Boss Battle), your topics, a difficulty and the kinds of questions.
*Typing* mixes fill-in-the-blanks and coding questions; typed questions get more time when a mode has a question timer.

## The questions

Topics follow the lessons (every question copies the lessons' code, variable names and Canvas-quiz wording):

`Variables · Data Types · Casting · Strings · Arithmetic Operators · Booleans & Operators · Conditionals · While Loops · For Loops ·
Functions · Classes & Methods · Mini-Challenges` – plus an "extra challenge" group (lists, dictionaries, comprehensions, …) that
goes beyond the lessons and is switched off by default.

Add or change questions in `pyblooket/questions/topics/<topic>.py`: every generator is a small function that draws everything
from the `rng` it is given, builds the question with the helpers in `pyblooket/questions/base.py` (`build_question`,
`output_question`, `blanks_question`, `match_question`, `code_question` …) and is registered with `@generator(topic, difficulty, qtype)`.
The test-suite runs *every* generator for 150 seeds: answers are computed by running the code, reference solutions of coding
questions are run through the real sandbox, and variety / determinism / balance are checked.

## About running students' code

"Write the code" answers are executed on the machine that runs the server, in a separate Python process that

* starts with `-I -S` and an empty environment, under CPU / memory / file-size limits and a hard timeout,
* only runs code that passed a static check (no `import`, no dunder attributes, no `.format()`, no generators / async) with a small
  whitelist of builtins (no `open`, `eval`, `exec`, `getattr`, …),
* never sees the hidden tests.

That is defence in depth for a classroom network, **not** a guarantee against a determined attacker – only host on a network you
trust. (On Windows the CPU/memory limits are not available, so only the hard timeout protects the server.) To switch typed-code questions off completely run `PYBLOOKET_CODE=off python app.py` (the typed blanks and matching
questions keep working; no student code is ever executed).

## Development

```bash
pip install -r requirements-dev.txt
pytest                      # ~2,700 tests; add -k "topics.strings" to run one topic
```

Layout: `app.py` (Flask app + solo API) · `pyblooket/questions/` (generators, formats, grading) · `pyblooket/sandbox.py` +
`_sandbox_runner.py` (typed-code grader) · `pyblooket/games.py` + `hosting.py` (live games) · `static/` (single-page app:
`js/engine.js` question card & game contract, `js/questions.js` question renderer & code editor, `js/modes/` solo modes,
`js/host.js` and `js/play.js` classroom screens).
