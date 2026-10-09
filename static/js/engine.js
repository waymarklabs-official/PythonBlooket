/**
 * PyBlooket game engine: builds the `ctx` object handed to a game mode and
 * implements ctx.ask() (the question card).
 *
 * =============================================================================
 * MODE CONTRACT
 * =============================================================================
 * Each static/js/modes/<id>.js default-exports:
 *
 *   export default {
 *     id: 'gold',                    // also the CSS hook: ctx.root gets class "mode-gold"
 *     name: 'Gold Quest',
 *     icon: '💰',
 *     tagline: 'One short line for the home card',
 *     description: 'How to play (plain text, shown on the setup screen; \n = new paragraph)',
 *     difficultySelectable: true,    // false -> setup hides the difficulty picker and
 *                                    //          ctx.settings.difficulty is 'mixed'
 *     difficultyNote: '...',         // optional: shown instead of the picker when not selectable
 *     color: '#ffcb2e',              // optional accent for the home/setup card
 *     options: [                     // rendered as segmented controls on the setup screen;
 *                                    // chosen values arrive as-is (numbers stay numbers)
 *                                    // in ctx.settings.options[key] and are remembered
 *       { key: 'goal', label: 'Gold goal', choices: [[1000, '1,000'], [5000, '5,000']], default: 1000 },
 *     ],
 *     scoreLabel: 'Gold',            // label under the big number on RESULTS / high scores
 *     questionTypes: ['choice', 'match', 'blanks'],  // optional: the question formats this mode can
 *                                    // show (default: all four, see ctx.ask). The player's
 *                                    // "Question types" choice is intersected with it.
 *     async play(ctx) { ...; return { score, won, headline, details } },
 *   };
 *
 * play(ctx) renders everything inside ctx.root and resolves to the RESULT:
 *   { score: number,               // saved to the high-score table
 *     won: true | false | null,    // true -> confetti + win styling, false -> "lost" styling,
 *                                  //   null -> neutral (e.g. endless modes)
 *     headline: string,            // e.g. "You escaped with 4,200 gold!"
 *     details: [[label, valueString], ...] }   // extra rows on the results screen
 * The engine then shows RESULTS (score, headline, details + the engine stats below),
 * saves the score to the high-score table, and plays the win/lose sound + confetti
 * itself (on won === true or a new best) — modes shouldn't do that at the very end.
 * Instead of returning, a mode may also end the game from anywhere (e.g. a timer
 * callback) with ctx.finish(result); any pending ctx.ask()/ctx.sleep() then rejects
 * with AbortError, which play() should simply let propagate.
 *
 * =============================================================================
 * ctx (created by startGame() below)
 * =============================================================================
 *   ctx.root       <main> element the mode owns (the full game area below the sticky
 *                  top bar, whose height is about var(--topbar-h) = 64px). Starts empty,
 *                  has classes "game-area mode-<id>", is a flex column (flex: 1) that fills
 *                  the rest of the viewport, and has NO padding — use a
 *                  `<div class="game-stage">` child for a centred, padded column
 *                  (max-width 940px), or lay out your own full-bleed scene.
 *   ctx.settings   { topics: [ids], difficulty: 1|2|3|'mixed', types: 'mixed'|'choice'|'typing'|[qtypes],
 *                    playerName, avatar, options: {key: value} }
 *   ctx.topics     topic metadata array from /api/topics: [{id, name, icon, description, generators}]
 *   ctx.difficulties [{id: 1, label: 'Easy', points: 100}, {id: 2, ...250}, {id: 3, ...500}]
 *   ctx.player     { name, avatar, color }   (color = avatar circle background)
 *                  (same as settings.playerName/avatar; name defaults to "Player")
 *   ctx.mode       the mode module object itself
 *
 *   ctx.ask(container, opts?) -> Promise<AskResult>
 *     Clears `container` and renders a question card in it (topic chip, difficulty
 *     badge with points, prompt, highlighted code, the answer area, optional countdown
 *     bar). The answer area depends on the question's format (q.qtype, see questions.js):
 *       choice  4 coloured answer buttons; keys 1-4 pick one
 *       blanks  the code snippet with <input> boxes to type into (Enter = next blank)
 *       match   rows of "item -> dropdown"
 *       code    "write the code": examples, an editor, Run examples and Submit
 *     Which formats appear is decided by ctx.settings.types (the feed asks the server).
 *     After the server replies it marks the answer (right = green ✓, wrong = red ✗, the
 *     model answer is shown for the typed formats), shows "Correct! +N" or "Not quite" +
 *     the explanation and plays a sound. Then:
 *       - correct: auto-continues after opts.correctDelay ms (default 1200; typed answers wait
 *         at least 2.5 s so the model solution can be read); a click on the card (on the banner
 *         for typed formats), Enter or Space skips the wait;
 *       - wrong: waits for "Continue ▶" (click / Enter / Space), unless opts.wrongDelay
 *         is a number -> auto-continue after that many ms (at least 3.5 s for blanks / 6 s for
 *         code); click/Enter/Space skips.
 *     Enter / Space never skip while a text field or the editor has focus.
 *     The card stays on screen after resolving; the next ask() (or the mode) replaces it.
 *     Calling ask() again on the same container while an earlier ask() there is still
 *     pending supersedes it: the old card's listeners/timers are removed and its
 *     promise never settles (so don't await it). Hotkeys only act on cards still in the DOM.
 *     opts:
 *       difficulty    1|2|3|'mixed' — overrides ctx.settings.difficulty for this question
 *       timeLimit     seconds for a MULTIPLE-CHOICE question. Other formats get
 *                     round(timeLimit * q.time_factor) (blanks / match x2, code x6) but at least
 *                     20 s (60 s for code), see questionTimeLimit(). On expiry whatever is typed
 *                     or picked so far is submitted (a half-finished answer is simply wrong):
 *                     timedOut=true. Last 5 s tick and turn red.
 *       correctDelay  ms (default 1200)
 *       wrongDelay    ms or undefined (undefined = wait for the Continue button)
 *       pointsLabel   string, or fn(result) -> string, replacing "+250" in the
 *                     "Correct! +250" banner (e.g. "+1 lap", "⚔️ 250 damage")
 *       onAnswered    fn(result) called the instant the server replies, before the
 *                     continue delay (good for updating HUDs immediately)
 *     The ask card is width:100% of `container`; size the container to taste (typed formats
 *     are taller than multiple choice: don't give the container a fixed height).
 *     AskResult: { correct: bool,
 *                  points: number — the question's base points (Easy 100 / Medium 250 /
 *                          Hard 500) if correct, else 0. Modes apply their own scoring
 *                          (e.g. gold = points * multiplier) — the engine does not.
 *                  question: the public question {id, topic, topic_name, topic_icon, difficulty,
 *                             difficulty_label, points, prompt, code, qtype, choices, blanks?,
 *                             match?, task?, time_factor},
 *                  qtype: 'choice'|'blanks'|'match'|'code',
 *                  response: what was submitted (index | null, string[], (index|null)[], code string),
 *                  chosen: index|null (multiple choice only, else null),
 *                  answer: correct index (multiple choice), else -1,
 *                  reveal: the server's model answer ({answer} | {blanks, accepted} | {match} | {solution}),
 *                  detail: per-blank / per-row marks or the code-run report ({} for choice),
 *                  timedOut: bool, timeMs: number, explanation: string }
 *     Rejects with an Error named 'AbortError' if the game is quit (or finished)
 *     while it is pending. Network problems show a retry message inside the card and
 *     retry automatically; they never reject. A question the server no longer knows
 *     (404) is silently replaced by a fresh one.
 *
 *   Answer hotkeys (1-4 on multiple choice, Enter/Space to continue) are ignored while a modal
 *   dialog is open, while typing in an input, or with modifier keys held — modes can use other
 *   keys freely.
 *
 *   ctx.stats  live object, updated by every ask() (don't mutate it; it feeds RESULTS):
 *     { answered, correct, streak, bestStreak, pointsEarned, totalTimeMs,
 *       byTopic: { [topicId]: {answered, correct} },
 *       byDifficulty: { 1: {answered, correct, points}, 2: {...}, 3: {...} } }
 *
 *   ctx.setTimeout(fn, ms) / ctx.clearTimeout(id)
 *   ctx.setInterval(fn, ms) / ctx.clearInterval(id)
 *   ctx.onCleanup(fn)       run when the game ends or is quit (timers are cleared automatically)
 *   ctx.sleep(ms)           Promise; rejects with AbortError when the game is quit/finished
 *   ctx.aborted             true once the game is over (quit OR finished)
 *   ctx.signal              AbortSignal aborted at the same moment
 *   ctx.finish(result)      end the game now with `result` (see above)
 *   ctx.prefetch(difficulty?) warm the question buffer for a difficulty you'll ask soon
 *
 *   UI helpers (re-exported from ui.js): ctx.el, ctx.toast, ctx.sfx, ctx.confetti,
 *   ctx.formatTime, ctx.randomBots, ctx.animateNumber, ctx.highlightPython,
 *   ctx.renderInlineCode, ctx.codeBlock, ctx.blook, ctx.avatarColor, ctx.AVATARS, ctx.shuffle
 *     el(tag, props, ...children)  props: class, text, html, style{}, onClick..., dataset{}, attrs
 *     sfx(name)  'correct' 'wrong' 'click' 'chest' 'win' 'lose' 'tick' 'hit' 'levelup'
 *     confetti({count, x, y})  randomBots(n) -> [{name, avatar, color}]
 *     animateNumber(el, from, to, ms) -> Promise   formatTime(sec) -> "m:ss" (rounds up)
 *     blook(avatar, {size, color}) -> <span class="blook"> emoji in a coloured circle
 *     toast(message, type='info'|'success'|'error'|'warn', ms=2800)
 *     codeBlock(code) -> highlighted code element with line numbers
 *     renderInlineCode(text) -> HTML string with `backticks` as <code> (rest escaped)
 *
 * Quitting: the engine aborts ctx.signal, clears timers, runs cleanups (in reverse
 * order), empties ctx.root and goes HOME. Pending ask()/sleep() reject with AbortError;
 * just let it propagate out of play() — the engine ignores AbortError.
 *
 * CSS: every mode stylesheet (css/modes/<id>.css) is loaded globally on every page,
 * so scope ALL rules under `.mode-<id>` (or prefix class names with `<id>-`).
 * Shared tokens live on :root in style.css: --c-yellow/-blue/-green/-red/-purple/-orange
 * (each with a darker "-d" edge variant, e.g. --c-blue-d, for 3D bottom borders),
 * --c-yellow-ink (text on yellow), --c-pink, --c-teal, --c-gold, --c-green-bright,
 * --c-bg1/--c-bg2/--c-bg3, --c-card, --c-card-2, --c-text, --c-muted, --c-border,
 * --radius, --radius-sm, --radius-lg, --shadow, --shadow-sm, --font-display (Titan One),
 * --font-body (Nunito), --font-mono (JetBrains Mono), --topbar-h.
 * Utility classes: .btn (+ .btn-green/-blue/-yellow/-red/-purple/-white/-ghost,
 * .btn-sm/.btn-lg/.btn-xl), .card, .card-title, .game-stage, .hud, .hud-pill, .blook,
 * .meta-pill, .diff-1/.diff-2/.diff-3 (difficulty colours), .spinner,
 * and animations .pop-in, .shake, .pulse, .bounce. prefers-reduced-motion is honoured
 * globally. White cards need dark text (var(--c-text)); the page background is purple,
 * so text placed directly on it should be white.
 */

import { runCode, submitAnswer } from "./api.js";
import { createQuestionView } from "./questions.js";
import {
  AVATARS,
  animateNumber,
  avatarColor,
  blook,
  codeBlock,
  confetti,
  el,
  formatTime,
  highlightPython,
  isModalOpen,
  randomBots,
  renderInlineCode,
  sfx,
  shuffle,
  toast,
} from "./ui.js";

// Typed formats get more time and more reading time than a multiple-choice question.
const TIME_FACTORS = { blanks: 2, match: 2, code: 6 };
const MIN_TIME_LIMIT = { blanks: 20, match: 20, code: 60 }; // seconds
const MIN_CORRECT_DELAY = { blanks: 2500, match: 1500, code: 2500 }; // ms: read the model answer
const MIN_WRONG_DELAY = { blanks: 3500, code: 6000 }; // ms, only when a mode auto-continues wrong answers
const RETRY_NEW_QUESTION = Symbol("retry-new-question");
const never = () => new Promise(() => {});

export function abortError(message = "Game ended") {
  try {
    return new DOMException(message, "AbortError");
  } catch {
    const err = new Error(message);
    err.name = "AbortError";
    return err;
  }
}

export function isAbortError(err) {
  return !!err && err.name === "AbortError";
}

/** Seconds a question gets when a mode asks for `timeLimit` seconds per multiple-choice question (0 = no timer). */
export function questionTimeLimit(q, timeLimit) {
  const seconds = Number(timeLimit) || 0;
  const type = (q && q.qtype) || "choice";
  if (seconds <= 0) return 0;
  if (type === "choice") return seconds;
  const factor = Number(q.time_factor) || TIME_FACTORS[type] || 1;
  return Math.max(MIN_TIME_LIMIT[type] || 0, Math.round(seconds * factor));
}

function newStats() {
  return {
    answered: 0,
    correct: 0,
    streak: 0,
    bestStreak: 0,
    pointsEarned: 0,
    totalTimeMs: 0,
    byTopic: {},
    byDifficulty: {
      1: { answered: 0, correct: 0, points: 0 },
      2: { answered: 0, correct: 0, points: 0 },
      3: { answered: 0, correct: 0, points: 0 },
    },
  };
}

function normalizeResult(result, stats) {
  const r = result && typeof result === "object" ? result : {};
  const score = Number.isFinite(Number(r.score)) ? Number(r.score) : stats.pointsEarned;
  return {
    score: Math.round(score),
    won: r.won === true ? true : r.won === false ? false : null,
    headline: typeof r.headline === "string" && r.headline ? r.headline : "Game over!",
    details: Array.isArray(r.details)
      ? r.details.filter((row) => Array.isArray(row) && row.length >= 2).map(([k, v]) => [String(k), String(v)])
      : [],
  };
}

/**
 * Create the ctx for one game. Prefer startGame(), which also runs mode.play().
 * internals: ctx._dispose() ends everything (idempotent).
 */
export function createGameContext({ root, mode, settings, topics = [], difficulties = [], feed }) {
  const controller = new AbortController();
  const timeouts = new Set();
  const intervals = new Set();
  const cleanups = [];
  const stats = newStats();
  const activeAsks = new WeakMap(); // container -> pending ask token
  let finishHandler = null;

  const throwIfAborted = () => {
    if (controller.signal.aborted) throw abortError();
  };

  /** Race a promise against the game ending. */
  const abortable = (promise) =>
    new Promise((resolve, reject) => {
      if (controller.signal.aborted) return reject(abortError());
      const onAbort = () => reject(abortError());
      controller.signal.addEventListener("abort", onAbort, { once: true });
      promise.then(
        (v) => {
          controller.signal.removeEventListener("abort", onAbort);
          resolve(v);
        },
        (e) => {
          controller.signal.removeEventListener("abort", onAbort);
          reject(e);
        }
      );
    });

  const ctx = {
    root,
    mode,
    settings,
    topics,
    difficulties,
    stats,
    signal: controller.signal,
    get aborted() {
      return controller.signal.aborted;
    },
    player: {
      name: settings.playerName,
      avatar: settings.avatar,
      color: avatarColor(settings.avatar),
    },

    setTimeout(fn, ms) {
      if (controller.signal.aborted) return 0;
      const id = window.setTimeout(() => {
        timeouts.delete(id);
        if (!controller.signal.aborted) fn();
      }, ms);
      timeouts.add(id);
      return id;
    },
    clearTimeout(id) {
      window.clearTimeout(id);
      timeouts.delete(id);
    },
    setInterval(fn, ms) {
      if (controller.signal.aborted) return 0;
      const id = window.setInterval(() => {
        if (!controller.signal.aborted) fn();
      }, ms);
      intervals.add(id);
      return id;
    },
    clearInterval(id) {
      window.clearInterval(id);
      intervals.delete(id);
    },
    onCleanup(fn) {
      if (typeof fn !== "function") return;
      if (controller.signal.aborted) {
        try {
          fn();
        } catch (err) {
          console.warn("cleanup failed", err);
        }
      } else cleanups.push(fn);
    },
    sleep(ms) {
      return abortable(new Promise((resolve) => ctx.setTimeout(resolve, ms)));
    },
    finish(result) {
      if (finishHandler) finishHandler(result);
    },
    prefetch(difficulty) {
      feed.prefetch(difficulty ?? settings.difficulty);
    },
    ask(container, opts) {
      return ask(container, opts);
    },

    // ui.js helpers
    el,
    toast,
    sfx,
    confetti,
    formatTime,
    randomBots,
    animateNumber,
    highlightPython,
    renderInlineCode,
    codeBlock,
    blook,
    avatarColor,
    shuffle,
    AVATARS,

    _setFinishHandler(fn) {
      finishHandler = fn;
    },
    _dispose() {
      if (!controller.signal.aborted) controller.abort(abortError());
      for (const id of timeouts) window.clearTimeout(id);
      for (const id of intervals) window.clearInterval(id);
      timeouts.clear();
      intervals.clear();
      while (cleanups.length) {
        const fn = cleanups.pop();
        try {
          fn();
        } catch (err) {
          console.warn("cleanup failed", err);
        }
      }
      feed.close();
    },
  };

  // ---------------------------------------------------------------------------
  // ctx.ask
  // ---------------------------------------------------------------------------

  /** Listeners/timers scoped to one question card. */
  function scope() {
    const offs = [];
    return {
      on(target, type, fn, options) {
        target.addEventListener(type, fn, options);
        offs.push(() => target.removeEventListener(type, fn, options));
      },
      timeout(fn, ms) {
        const id = window.setTimeout(fn, ms);
        offs.push(() => window.clearTimeout(id));
        return id;
      },
      interval(fn, ms) {
        const id = window.setInterval(fn, ms);
        offs.push(() => window.clearInterval(id));
        return id;
      },
      add(fn) {
        offs.push(fn);
      },
      clear() {
        while (offs.length) offs.pop()();
      },
    };
  }

  /** Resolve when `wait` resolves; reject on abort; always run scope cleanup. */
  function waitScoped(sc, executor) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const done = (fn, v) => {
        if (settled) return;
        settled = true;
        sc.clear();
        fn(v);
      };
      if (controller.signal.aborted) return done(reject, abortError());
      sc.on(controller.signal, "abort", () => done(reject, abortError()));
      try {
        executor(
          (v) => done(resolve, v),
          (e) => done(reject, e)
        );
      } catch (err) {
        done(reject, err);
      }
    });
  }

  function isTypingTarget(target) {
    return (
      target &&
      (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
    );
  }

  function hotkeyAllowed(e) {
    return !e.defaultPrevented && !e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey && !isModalOpen() && !isTypingTarget(e.target);
  }

  function resolveDifficulty(d) {
    if (d === "mixed") return "mixed";
    if ([1, 2, 3].includes(Number(d))) return Number(d);
    return settings.difficulty;
  }

  async function ask(container, opts = {}) {
    throwIfAborted();
    if (!(container instanceof HTMLElement)) throw new TypeError("ctx.ask(container): container must be an element");
    const o = {
      correctDelay: 1200,
      wrongDelay: undefined,
      timeLimit: 0,
      ...opts,
    };
    const difficulty = resolveDifficulty(o.difficulty);
    // A new ask() on a container supersedes one still pending there: the old
    // one is detached (listeners/timers removed) and its promise never settles.
    const token = { cancelled: false, cleanups: [] };
    const previous = activeAsks.get(container);
    if (previous) cancelAsk(previous);
    activeAsks.set(container, token);
    try {
      for (;;) {
        const question = await loadQuestion(container, difficulty, token);
        const result = await presentQuestion(container, question, o, token);
        if (result !== RETRY_NEW_QUESTION) return result;
      }
    } finally {
      if (activeAsks.get(container) === token) activeAsks.delete(container);
    }
  }

  function cancelAsk(token) {
    token.cancelled = true;
    while (token.cleanups.length) token.cleanups.pop()();
  }

  /** Get a question from the feed, showing a loader if it is slow and a retry message on failure. */
  async function loadQuestion(container, difficulty, token) {
    let attempt = 0;
    for (;;) {
      throwIfAborted();
      const sc = scope();
      token.cleanups.push(() => sc.clear());
      sc.timeout(() => {
        container.replaceChildren(
          el(
            "div",
            { class: "q-card q-loading", "aria-busy": "true" },
            el("div", { class: "spinner", "aria-hidden": "true" }),
            el("p", { text: "Loading question…" })
          )
        );
      }, 180);
      try {
        const q = await abortable(feed.next(difficulty));
        sc.clear();
        if (token.cancelled) return never();
        return q;
      } catch (err) {
        sc.clear();
        if (isAbortError(err)) throw err;
        if (token.cancelled) return never();
        attempt++;
        await showRetry(container, err, attempt, token);
      }
    }
  }

  /** Error card with countdown auto-retry + "Try again" button. Resolves when it's time to retry. */
  function showRetry(container, err, attempt, token) {
    const sc = scope();
    token.cleanups.push(() => sc.clear());
    const wait = Math.min(2 + attempt * 2, 10);
    return waitScoped(sc, (resolve) => {
      let left = wait;
      const count = el("span", { text: String(left) });
      const btn = el("button", { class: "btn btn-yellow", type: "button", text: "Try again now", onClick: () => resolve() });
      container.replaceChildren(
        el(
          "div",
          { class: "q-card q-error pop-in", role: "alert" },
          el("div", { class: "q-error-icon", "aria-hidden": "true", text: "😵" }),
          el("h3", { text: "Couldn't load a question" }),
          el("p", { text: err && err.message ? err.message : "Network problem." }),
          el("p", { class: "q-error-retry" }, "Retrying in ", count, "s…"),
          btn
        )
      );
      btn.focus();
      sc.interval(() => {
        left--;
        count.textContent = String(Math.max(0, left));
        if (left <= 0) resolve();
      }, 1000);
    });
  }

  /** The countdown bar that goes into the view's timer slot. */
  function buildTimer(limit) {
    return el(
      "div",
      { class: "q-timer", role: "timer", "aria-label": "Time left" },
      el("div", { class: "q-timer-track" }, el("div", { class: "q-timer-fill" })),
      el("span", { class: "q-timer-text", text: formatTime(limit) })
    );
  }

  /** "Checking your answer…" banner (typed answers can take a moment: code runs in a sandbox). */
  function checkingBanner(qtype) {
    return el(
      "div",
      { class: "q-banner q-banner-warn", role: "status" },
      el("span", { class: "spinner qv-spin", "aria-hidden": "true" }),
      el("strong", { text: qtype === "code" ? "Running your code against the tests…" : "Checking your answer…" })
    );
  }

  function presentQuestion(container, q, o, token) {
    const qtype = q.qtype || "choice";
    const limit = questionTimeLimit(q, o.timeLimit);
    let onSubmitted = () => {};
    let timingOut = false;
    const view = createQuestionView(q, {
      onSubmit: (response) => onSubmitted(response, timingOut),
      onRun: qtype === "code" ? (code) => runCode(q.id, code) : undefined,
      hotkeys: true,
      showMeta: true,
    });
    const card = view.el;
    const feedback = view.feedbackSlot;
    const timer = limit ? buildTimer(limit) : null;
    if (timer) view.timerSlot.append(timer);
    container.replaceChildren(card);
    view.focus();

    const sc = scope();
    token.cleanups.push(() => sc.clear());
    const t0 = performance.now();
    let locked = false;

    return waitScoped(sc, (resolve, reject) => {
      sc.add(() => view.destroy());

      // ---- countdown -------------------------------------------------------
      let timeoutId = null;
      let deadline = 0;
      let lastTick = Infinity;
      const stopTimer = () => {
        if (timeoutId) window.clearTimeout(timeoutId);
        timeoutId = null;
        if (timer) {
          const fill = timer.querySelector(".q-timer-fill");
          const frac = Math.max(0, (deadline - performance.now()) / (limit * 1000));
          fill.style.setProperty("transition", "none", "important");
          fill.style.transform = `scaleX(${frac})`;
          timer.classList.add("stopped");
        }
      };
      if (timer && limit > 0) {
        deadline = performance.now() + limit * 1000;
        const fill = timer.querySelector(".q-timer-fill");
        const text = timer.querySelector(".q-timer-text");
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            if (locked) return;
            // !important so prefers-reduced-motion's global transition override can't skip the countdown
            fill.style.setProperty("transition", `transform ${Math.max(0, deadline - performance.now())}ms linear`, "important");
            fill.style.transform = "scaleX(0)";
          })
        );
        const ticker = sc.interval(() => {
          if (locked) return window.clearInterval(ticker);
          const left = (deadline - performance.now()) / 1000;
          text.textContent = formatTime(left);
          const frac = left / limit;
          timer.classList.toggle("warn", frac <= 0.5 && left > 5);
          timer.classList.toggle("urgent", left <= 5);
          const whole = Math.ceil(left);
          if (left <= 5 && whole < lastTick && whole > 0) sfx("tick");
          lastTick = whole;
        }, 200);
        // Out of time: hand in whatever is typed / picked so far (never throw it away silently).
        timeoutId = window.setTimeout(() => {
          timingOut = true;
          view.submit();
        }, limit * 1000);
        sc.add(() => timeoutId && window.clearTimeout(timeoutId));
      }

      // ---- answering -------------------------------------------------------
      // The view calls this once, when the player commits (click, Submit, Enter, or the timer).
      onSubmitted = async (response, timedOut) => {
        if (locked) return;
        locked = true;
        const timeMs = Math.round(performance.now() - t0);
        stopTimer();
        card.classList.add("answering");

        let res;
        let failures = 0;
        // typed answers: say so if grading takes a moment
        const checking = qtype === "choice" ? 0 : window.setTimeout(() => feedback.replaceChildren(checkingBanner(qtype)), 350);
        sc.add(() => window.clearTimeout(checking));
        for (;;) {
          try {
            res = await abortable(submitAnswer(q.id, response));
            if (token.cancelled) return;
            break;
          } catch (err) {
            if (isAbortError(err)) return reject(err);
            if (token.cancelled) return;
            if (err && err.status === 404) {
              toast("That question expired — here's a fresh one!", "warn");
              return resolve(RETRY_NEW_QUESTION);
            }
            failures++;
            feedback.replaceChildren(
              el("div", { class: "q-banner q-banner-warn" }, el("strong", { text: "Connection problem — retrying…" }))
            );
            try {
              await abortable(new Promise((r) => window.setTimeout(r, Math.min(1000 * failures, 4000))));
            } catch (abortErr) {
              return reject(abortErr);
            }
          }
        }
        window.clearTimeout(checking);
        if (controller.signal.aborted) return reject(abortError());

        const result = {
          correct: !!res.correct,
          points: Number(res.points) || 0,
          question: q,
          qtype,
          response,
          chosen: qtype === "choice" && Number.isInteger(response) ? response : null,
          answer: Number.isInteger(res.answer) ? res.answer : -1,
          reveal: res.reveal && typeof res.reveal === "object" ? res.reveal : {},
          detail: res.detail && typeof res.detail === "object" ? res.detail : {},
          timedOut,
          timeMs,
          explanation: res.explanation || "",
        };
        recordStats(q, result);
        showOutcome(result);
        if (typeof o.onAnswered === "function") {
          try {
            o.onAnswered(result);
          } catch (err) {
            console.error("onAnswered callback failed", err);
          }
        }
        if (controller.signal.aborted) return reject(abortError());
        awaitContinue(result).then(() => resolve(result), reject);
      };

      // ---- outcome + continue ---------------------------------------------
      function showOutcome(r) {
        card.classList.remove("answering");
        view.showResult(
          { correct: r.correct, reveal: r.reveal.answer === undefined && r.answer >= 0 ? { ...r.reveal, answer: r.answer } : r.reveal, detail: r.detail, explanation: r.explanation, points: r.points },
          { response: r.response }
        );
        // leave the (now read-only) text field so Enter / Space can skip, and the phone keyboard closes
        if (qtype !== "choice") {
          try {
            card.focus({ preventScroll: true });
          } catch {
            /* ignore */
          }
        }

        let title;
        if (r.correct) {
          let label = `+${r.points.toLocaleString()}`;
          if (typeof o.pointsLabel === "function") {
            try {
              label = String(o.pointsLabel(r));
            } catch (err) {
              console.error("pointsLabel failed", err);
            }
          } else if (typeof o.pointsLabel === "string") label = o.pointsLabel;
          title = el(
            "div",
            { class: "q-banner-title" },
            el("span", { class: "q-banner-icon", "aria-hidden": "true", text: "🎉" }),
            el("strong", { text: "Correct! " }),
            el("span", { class: "q-points pop-in", text: label })
          );
        } else {
          title = el(
            "div",
            { class: "q-banner-title" },
            el("span", { class: "q-banner-icon", "aria-hidden": "true", text: r.timedOut ? "⏰" : "😬" }),
            el("strong", { text: r.timedOut ? "Time's up!" : "Not quite!" })
          );
        }
        const streak = r.correct && stats.streak >= 3 ? el("span", { class: "q-streak pulse", text: `🔥 ${stats.streak} in a row!` }) : null;
        // "2 of 3 blanks right" for a partly right typed answer
        const marks = qtype === "blanks" ? r.detail.blanks : qtype === "match" ? r.detail.match : null;
        const score =
          !r.correct && Array.isArray(marks) && marks.some(Boolean)
            ? el("p", { class: "qv-score-line", text: `${marks.filter(Boolean).length} of ${marks.length} ${qtype === "blanks" ? "blanks" : "matches"} right.` })
            : null;
        feedback.replaceChildren(
          el(
            "div",
            { class: ["q-banner", r.correct ? "q-banner-correct" : "q-banner-wrong"] },
            el("div", { class: "q-banner-head" }, title, streak),
            score,
            r.explanation ? el("p", { class: "q-explanation", html: renderInlineCode(r.explanation) }) : null
          )
        );
        sfx(r.correct ? "correct" : "wrong");
        if (!r.correct) {
          card.classList.remove("pop-in");
          void card.offsetWidth;
          card.classList.add("shake");
        }
      }

      function awaitContinue(r) {
        const csc = scope();
        sc.add(() => csc.clear());
        const shownAt = performance.now();
        // Ignore skips in the first moments so a double-click on an answer
        // doesn't blow straight past the feedback.
        const settledEnough = () => performance.now() - shownAt > 350;
        return waitScoped(csc, (resolveContinue) => {
          const go = () => settledEnough() && resolveContinue();
          const banner = feedback.querySelector(".q-banner");
          let auto = r.correct ? Number(o.correctDelay) : typeof o.wrongDelay === "number" ? o.wrongDelay : null;
          // typed answers come with a model answer to read: give it some time
          if (auto !== null && Number.isFinite(auto)) auto = Math.max(auto, (r.correct ? MIN_CORRECT_DELAY : MIN_WRONG_DELAY)[qtype] || 0);
          const actions = el("div", { class: "q-actions" });
          banner.append(actions);
          if (auto !== null && Number.isFinite(auto)) {
            const ms = Math.max(0, auto);
            const bar = el("div", { class: "q-autobar", "aria-hidden": "true" }, el("i", { style: { animationDuration: `${ms}ms` } }));
            actions.append(
              el(
                "span",
                { class: "q-skip-hint" },
                el("span", { class: "only-mouse", text: "Click or press Enter to skip" }),
                el("span", { class: "only-touch", text: "Tap to skip" })
              ),
              bar
            );
            csc.timeout(resolveContinue, ms);
            // typed answers: only the banner skips (the player may want to select / read the model answer)
            csc.on(qtype === "choice" ? card : feedback, "click", () => go());
          } else {
            const btn = el("button", { class: "btn btn-blue q-continue", type: "button", text: "Continue ▶", onClick: () => resolveContinue() });
            actions.append(btn);
            try {
              btn.focus({ preventScroll: true });
            } catch {
              /* ignore */
            }
          }
          csc.on(document, "keydown", (e) => {
            if (!hotkeyAllowed(e)) return;
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              go();
            }
          });
          // Make sure the result/continue button is visible on small screens.
          try {
            feedback.scrollIntoView({ block: "nearest", behavior: "smooth" });
          } catch {
            /* ignore */
          }
        });
      }
    });
  }

  function recordStats(q, r) {
    stats.answered++;
    if (r.correct) {
      stats.correct++;
      stats.streak++;
      stats.bestStreak = Math.max(stats.bestStreak, stats.streak);
    } else {
      stats.streak = 0;
    }
    stats.pointsEarned += r.points;
    stats.totalTimeMs += r.timeMs;
    const t = (stats.byTopic[q.topic] ||= { answered: 0, correct: 0 });
    t.answered++;
    if (r.correct) t.correct++;
    const d = (stats.byDifficulty[q.difficulty] ||= { answered: 0, correct: 0, points: 0 });
    d.answered++;
    if (r.correct) d.correct++;
    d.points += r.points;
  }

  return ctx;
}

/**
 * Run a mode. Returns {ctx, quit(), done} where `done` resolves to one of
 *   {status: 'finished', result, stats}
 *   {status: 'quit'}
 *   {status: 'error', error}
 */
export function startGame({ root, mode, settings, topics, difficulties, feed }) {
  root.replaceChildren();
  root.className = `game-area mode-${mode.id}`;
  const ctx = createGameContext({ root, mode, settings, topics, difficulties, feed });
  feed.prefetch(settings.difficulty);

  let settled = false;
  let resolveDone;
  const done = new Promise((r) => (resolveDone = r));
  const settle = (outcome, { clearRoot = false } = {}) => {
    if (settled) return;
    settled = true;
    const statsSnapshot = JSON.parse(JSON.stringify(ctx.stats));
    ctx._dispose();
    if (clearRoot) root.replaceChildren();
    if (outcome.status === "finished") {
      outcome.stats = statsSnapshot;
      outcome.result = normalizeResult(outcome.result, statsSnapshot);
    }
    resolveDone(outcome);
  };
  ctx._setFinishHandler((result) => settle({ status: "finished", result }));

  Promise.resolve()
    .then(() => mode.play(ctx))
    .then(
      (result) => settle({ status: "finished", result }),
      (error) => {
        if (isAbortError(error)) settle({ status: "quit" }, { clearRoot: true });
        else {
          console.error(`Game mode "${mode.id}" crashed`, error);
          settle({ status: "error", error }, { clearRoot: true });
        }
      }
    );

  return {
    ctx,
    done,
    quit() {
      settle({ status: "quit" }, { clearRoot: true });
    },
  };
}
