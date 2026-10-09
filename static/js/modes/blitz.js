/**
 * Time Attack (id "blitz") — answer as many Python questions as you can before
 * the clock runs out.
 *
 * Rules (small pure functions below, exported for tests):
 *   - One shared countdown (60 / 90 / 120 / 180 s) that keeps running during the
 *     answer feedback. It starts after a short "3-2-1-GO!" and only pauses while the
 *     question card is stuck on a loading spinner or a network-error/retry message.
 *   - A correct answer scores  round(base × combo) + speed bonus
 *       base   = the question's points (Easy 100 / Medium 250 / Hard 500)
 *       combo  = 1 + 0.25 per correct answer already in the current streak, max ×3
 *                (the HUD always shows the multiplier your NEXT correct answer gets)
 *       speed  = +50% of base if answered within 5 s, +25% within 10 s
 *   - A wrong answer costs 5 seconds ("-5s") and resets the combo.
 *   - When the clock hits 0 the game ends immediately: the question card is pulled off
 *     the screen (the unanswered question doesn't count), a "Time's up!" splash shows
 *     for a moment, then RESULTS. An answer already clicked before the buzzer whose
 *     server reply lands during the splash still counts ("buzzer beater").
 *   - Result: score = points, won = null (no win/lose), headline "⚡ N points in 90 s!".
 *
 * Every timer goes through ctx.* (setInterval/setTimeout/sleep) so quitting never
 * leaks; AbortError from ctx.ask()/ctx.sleep() is simply allowed to propagate.
 */

// ---------------------------------------------------------------------------
// Tuning
// ---------------------------------------------------------------------------

export const DURATIONS = [60, 90, 120, 180];
export const DEFAULT_DURATION = 90;
export const WRONG_PENALTY_MS = 5000;
export const COMBO_STEP = 0.25;
export const MAX_MULTIPLIER = 3;
/** Speed bonus tiers, fastest first: answered within `withinMs` -> +rate × base. */
export const SPEED_TIERS = [
  { withinMs: 5000, rate: 0.5, label: "Lightning" },
  { withinMs: 10000, rate: 0.25, label: "Quick" },
];
export const DANGER_MS = 10000; // red clock + ticking
export const WARN_MS = 30000; // orange bar

const CORRECT_DELAY = 600;
const WRONG_DELAY = 1800;
const TICK_MS = 100;
const COUNTDOWN_BEAT_MS = 620;
const GO_MS = 480;
const TIME_UP_SPLASH_MS = 1900;
const FLOAT_MS = 1450;
const TIME_UP = Symbol("time-up");

// ---------------------------------------------------------------------------
// Pure rules
// ---------------------------------------------------------------------------

/** Clamp a duration option to one of DURATIONS (seconds). */
export function normalizeDuration(value) {
  const n = Number(value);
  return DURATIONS.includes(n) ? n : DEFAULT_DURATION;
}

/** Multiplier for the next correct answer, given how many are already in a row. */
export function comboMultiplier(streak) {
  const s = Math.max(0, Math.floor(Number(streak) || 0));
  return Math.min(MAX_MULTIPLIER, 1 + COMBO_STEP * s);
}

/** 0 (×1) … 3 (×3): drives the combo badge colour. */
export function comboLevel(mult) {
  return mult >= MAX_MULTIPLIER ? 3 : mult >= 2 ? 2 : mult > 1 ? 1 : 0;
}

/** The speed tier earned by an answer that took `timeMs`, or null. */
export function speedTier(timeMs) {
  const t = Number(timeMs);
  if (!Number.isFinite(t)) return null;
  for (const tier of SPEED_TIERS) if (t <= tier.withinMs) return tier;
  return null;
}

/** Points for a correct answer: {base, mult, comboPoints, bonus, bonusRate, speedLabel, total}. */
export function scoreAnswer({ base, streak, timeMs }) {
  const b = Math.max(0, Number(base) || 0);
  const mult = comboMultiplier(streak);
  const comboPoints = Math.round(b * mult);
  const tier = speedTier(timeMs);
  const bonus = tier ? Math.round(b * tier.rate) : 0;
  return {
    base: b,
    mult,
    comboPoints,
    bonus,
    bonusRate: tier ? tier.rate : 0,
    speedLabel: tier ? tier.label : null,
    total: comboPoints + bonus,
  };
}

export function newGameState() {
  return {
    score: 0,
    answered: 0,
    correct: 0,
    wrong: 0,
    streak: 0,
    bestStreak: 0,
    bestMult: 1,
    fastestMs: null,
    speedBonusCount: 0,
    speedBonusPoints: 0,
    penaltyMs: 0,
  };
}

/**
 * Apply one answered question. Returns {state, award} — award is the scoreAnswer()
 * breakdown for a correct answer, null for a wrong one. (Time penalties live on the clock.)
 */
export function applyAnswer(state, { correct, base, timeMs }) {
  if (!correct) {
    return {
      state: { ...state, answered: state.answered + 1, wrong: state.wrong + 1, streak: 0 },
      award: null,
    };
  }
  const award = scoreAnswer({ base, streak: state.streak, timeMs });
  const streak = state.streak + 1;
  const t = Number(timeMs);
  return {
    state: {
      ...state,
      score: state.score + award.total,
      answered: state.answered + 1,
      correct: state.correct + 1,
      streak,
      bestStreak: Math.max(state.bestStreak, streak),
      bestMult: Math.max(state.bestMult, award.mult),
      fastestMs: Number.isFinite(t) && (state.fastestMs === null || t < state.fastestMs) ? t : state.fastestMs,
      speedBonusCount: state.speedBonusCount + (award.bonus > 0 ? 1 : 0),
      speedBonusPoints: state.speedBonusPoints + award.bonus,
    },
    award,
  };
}

// ---- clock (all times are performance.now() milliseconds) -------------------

export function createClock(durationSec, now) {
  const totalMs = normalizeDuration(durationSec) * 1000;
  return { totalMs, endsAt: now + totalMs, pausedAt: null };
}

export function remainingMs(clock, now) {
  const t = clock.pausedAt ?? now;
  return Math.max(0, clock.endsAt - t);
}

export function pauseClock(clock, now) {
  return clock.pausedAt === null ? { ...clock, pausedAt: now } : clock;
}

export function resumeClock(clock, now) {
  if (clock.pausedAt === null) return clock;
  return { ...clock, endsAt: clock.endsAt + Math.max(0, now - clock.pausedAt), pausedAt: null };
}

/** Take up to `ms` off the clock. Returns {clock, lostMs} (never below zero). */
export function penalize(clock, ms, now) {
  const lostMs = Math.min(Math.max(0, ms), remainingMs(clock, now));
  return { clock: { ...clock, endsAt: clock.endsAt - lostMs }, lostMs };
}

/** 'ok' | 'warn' | 'danger' for the time left. */
export function timeZone(ms) {
  return ms <= DANGER_MS ? "danger" : ms <= WARN_MS ? "warn" : "ok";
}

// ---- formatting --------------------------------------------------------------

/** ×1, ×1.25, ×1.5 … ×3 */
export function formatMultiplier(mult) {
  return `×${Number(Number(mult).toFixed(2))}`;
}

/** "1:23" while 10 s or more remain, then "9.3" (tenths, rounded up so 0.0 means really over). */
export function formatClock(ms) {
  const m = Math.max(0, Number(ms) || 0);
  if (m >= DANGER_MS) {
    const s = Math.ceil(m / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }
  return (Math.ceil(m / 100) / 10).toFixed(1);
}

export function formatSeconds(ms) {
  return `${(Math.max(0, Number(ms) || 0) / 1000).toFixed(1)} s`;
}

export function accuracyPercent(correct, answered) {
  return answered ? Math.round((correct / answered) * 100) : 0;
}

/** The {score, won, headline, details} handed back to the engine. */
export function buildResult(state, durationSec) {
  const secs = normalizeDuration(durationSec);
  const fmt = (n) => Number(n).toLocaleString();
  return {
    score: state.score,
    won: null,
    headline: `⚡ ${fmt(state.score)} points in ${secs} s!`,
    details: [
      ["Questions answered", String(state.answered)],
      ["Accuracy", state.answered ? `${accuracyPercent(state.correct, state.answered)}% (${state.correct}/${state.answered})` : "—"],
      ["Best combo", state.bestStreak ? `${formatMultiplier(state.bestMult)} · ${state.bestStreak} in a row` : "—"],
      ["Fastest answer", state.fastestMs === null ? "—" : formatSeconds(state.fastestMs)],
      ["Speed bonuses", state.speedBonusCount ? `${state.speedBonusCount} (+${fmt(state.speedBonusPoints)} pts)` : "None"],
      [
        "Time lost to mistakes",
        state.penaltyMs ? `−${Math.round(state.penaltyMs / 1000)} s` : state.answered ? "None — flawless!" : "None",
      ],
    ],
  };
}

// ---------------------------------------------------------------------------
// Mode
// ---------------------------------------------------------------------------

export default {
  id: "blitz",
  name: "Time Attack",
  icon: "⚡",
  tagline: "Beat the clock — rack up points before time runs out!",
  description:
    "Answer as many questions as you can before the clock hits zero! Correct answers score the question's points — Easy 100, Medium 250, Hard 500 — so harder questions are worth more.\n" +
    "Every correct answer in a row adds ×0.25 to your combo multiplier (max ×3), and answering within 5 seconds earns a +50% speed bonus (+25% within 10 s).\n" +
    "Careful: a wrong answer costs 5 seconds and resets your combo!",
  difficultySelectable: true,
  // a code-writing question would eat a 60-second game: only quick formats here
  questionTypes: ["choice", "match", "blanks"],
  options: [
    {
      key: "duration",
      label: "Time limit",
      choices: [
        [60, "60 s"],
        [90, "90 s"],
        [120, "120 s"],
        [180, "180 s"],
      ],
      default: DEFAULT_DURATION,
    },
  ],
  scoreLabel: "Points",

  async play(ctx) {
    const { el } = ctx;
    const durationSec = normalizeDuration(ctx.settings?.options?.duration);
    let state = newGameState();
    let clock = null; // created at "GO!"
    let ticker = 0;
    let over = false;
    let zone = "ok";
    let lastWhole = null;
    let resolveTimeUp;
    const timeUp = new Promise((resolve) => (resolveTimeUp = resolve));

    // ---- DOM ---------------------------------------------------------------
    const clockText = el("span", { class: "blitz-clock-time", text: formatClock(durationSec * 1000) });
    const clockBox = el(
      "div",
      { class: "blitz-clock", role: "timer", "aria-label": `Time left, ${durationSec} second game` },
      el("span", { class: "blitz-clock-icon", "aria-hidden": "true", text: "⏱" }),
      clockText
    );
    const scoreVal = el("b", { class: "blitz-stat-value", text: "0" });
    const scoreStat = el(
      "div",
      { class: "blitz-stat blitz-score" },
      el("span", { class: "blitz-stat-label", text: "Score" }),
      el("span", { class: "blitz-stat-row" }, scoreVal, el("span", { class: "blitz-unit", text: "pts" }))
    );
    const comboVal = el("b", { class: "blitz-stat-value", text: formatMultiplier(1) });
    const comboStreak = el("span", { class: "blitz-combo-streak", "aria-hidden": "true" });
    const comboStat = el(
      "div",
      { class: "blitz-stat blitz-combo lvl-0", title: "Combo multiplier for your next correct answer" },
      el("span", { class: "blitz-stat-label", text: "Combo" }),
      el(
        "span",
        { class: "blitz-stat-row" },
        el("span", { class: "blitz-flame", "aria-hidden": "true", text: "🔥" }),
        comboVal,
        comboStreak
      )
    );
    const tallyVal = el("b", { class: "blitz-stat-value", text: "0/0" });
    const tallyStat = el(
      "div",
      { class: "blitz-stat blitz-tally" },
      el("span", { class: "blitz-stat-label", text: "Correct" }),
      el("span", { class: "blitz-stat-row" }, el("span", { class: "blitz-check", "aria-hidden": "true", text: "✓" }), tallyVal)
    );
    const barFill = el("div", { class: "blitz-bar-fill" });
    const barGhost = el("div", { class: "blitz-bar-ghost" });
    const bar = el(
      "div",
      { class: "blitz-bar", "aria-hidden": "true" },
      el("div", { class: "blitz-bar-danger", style: { width: `${(DANGER_MS / (durationSec * 1000)) * 100}%` } }),
      barGhost,
      barFill
    );
    const hud = el("div", { class: "blitz-hud blitz-zone-ok" }, clockBox, scoreStat, comboStat, tallyStat, bar);
    const qArea = el("div", { class: "blitz-q" });
    const live = el("p", { class: "sr-only", "aria-live": "polite" });
    const vignette = el("div", { class: "blitz-vignette", "aria-hidden": "true" });
    const stage = el("div", { class: "game-stage blitz-stage" }, hud, qArea);
    ctx.root.append(stage, vignette, live);

    // The HUD is sticky under the top bar; square its top corners while it is stuck.
    const onScroll = () => {
      const top = parseFloat(window.getComputedStyle(hud).top) || 0;
      hud.classList.toggle("is-stuck", window.scrollY > 0 && hud.getBoundingClientRect().top <= top + 0.5);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    ctx.onCleanup(() => window.removeEventListener("scroll", onScroll));

    // ---- small DOM helpers ---------------------------------------------------
    /** Restart a one-shot CSS animation class (only one fx class per node at a time). */
    const FX = ["blitz-bump", "blitz-break", "blitz-hurt", "blitz-throb", "blitz-beat"];
    const retrigger = (node, cls) => {
      node.classList.remove(...FX);
      void node.offsetWidth;
      node.classList.add(cls);
    };
    const announce = (text) => {
      live.textContent = text;
    };
    /**
     * A "+N" / "-5s" bubble that pops up from the HUD's bottom edge under `anchor`
     * and rises towards it (so the number it changes stays readable).
     * Only one bubble per kind at a time — fast answering never stacks them up.
     */
    const floatAt = (anchor, className, ...children) => {
      const kind = className.split(" ")[0];
      for (const old of hud.querySelectorAll(`.${kind}`)) old.remove();
      const h = hud.getBoundingClientRect();
      const a = anchor.getBoundingClientRect();
      const node = el(
        "div",
        {
          class: ["blitz-float", className],
          "aria-hidden": "true",
          style: { left: `${a.left - h.left + a.width / 2}px`, top: `${h.height}px` },
        },
        ...children
      );
      hud.append(node);
      ctx.setTimeout(() => node.remove(), FLOAT_MS);
      return node;
    };

    function renderHud() {
      ctx.animateNumber(scoreVal, Number(scoreVal.dataset.v || 0), state.score, 450);
      scoreVal.dataset.v = String(state.score);
      const mult = comboMultiplier(state.streak);
      comboVal.textContent = formatMultiplier(mult);
      comboStreak.textContent = state.streak ? `${state.streak} in a row` : "";
      for (let i = 0; i <= 3; i++) comboStat.classList.toggle(`lvl-${i}`, comboLevel(mult) === i);
      comboStat.classList.toggle("is-max", mult >= MAX_MULTIPLIER);
      tallyVal.textContent = `${state.correct}/${state.answered}`;
    }

    function renderClock(left, paused) {
      clockText.textContent = formatClock(left);
      barFill.style.width = `${(clock ? left / clock.totalMs : 1) * 100}%`;
      const z = timeZone(left);
      if (z !== zone) {
        hud.classList.remove(`blitz-zone-${zone}`);
        hud.classList.add(`blitz-zone-${z}`);
        ctx.root.classList.toggle("blitz-danger", z === "danger");
        if (z === "warn" && zone === "ok") announce("30 seconds left");
        if (z === "danger") announce("10 seconds left — hurry!");
        zone = z;
      }
      clockBox.classList.toggle("is-paused", !!paused);
    }

    /** Red "lost time" segment that drains after a penalty (fighting-game health bar). */
    function flashLoss(fromFrac, toFrac) {
      barGhost.style.transition = "none";
      barGhost.style.width = `${fromFrac * 100}%`;
      barGhost.classList.add("on");
      void barGhost.offsetWidth;
      barGhost.style.transition = "";
      barGhost.style.width = `${toFrac * 100}%`;
      ctx.setTimeout(() => barGhost.classList.remove("on"), 950);
    }

    // ---- clock ---------------------------------------------------------------
    function tick() {
      if (over || !clock) return;
      const now = performance.now();
      // Don't burn the player's time while the card is stuck loading / retrying.
      const stalled = !!qArea.querySelector(".q-loading, .q-error, .q-banner-warn");
      if (stalled) clock = pauseClock(clock, now);
      else clock = resumeClock(clock, now);
      const left = remainingMs(clock, now);
      renderClock(left, stalled);
      if (left <= 0) {
        endGame();
        return;
      }
      const whole = Math.ceil(left / 1000);
      if (left <= DANGER_MS && whole !== lastWhole && !stalled) {
        ctx.sfx("tick");
        retrigger(clockBox, "blitz-throb");
      }
      lastWhole = whole;
    }

    function endGame() {
      if (over) return;
      over = true;
      ctx.clearInterval(ticker);
      renderClock(0, false);
      clockBox.classList.add("is-over");
      ctx.root.classList.remove("blitz-danger");
      ctx.sfx("hit");
      announce(`Time's up! You scored ${state.score.toLocaleString()} points.`);
      // Pull the question off screen right away: a detached card ignores clicks and
      // number keys, and anything the pending ask() renders later stays detached.
      qArea.replaceWith(splash());
      resolveTimeUp(TIME_UP);
    }

    // ---- answering -------------------------------------------------------------
    const baseOf = (r) => Number(r.points) || Number(r.question && r.question.points) || 0;

    function onAnswered(r) {
      const late = over; // a click made before the buzzer whose reply arrived after it
      const before = state;
      const { state: next, award } = applyAnswer(state, { correct: r.correct, base: baseOf(r), timeMs: r.timeMs });
      state = next;
      renderHud();

      if (award) {
        celebrate(award, before, late);
      } else {
        retrigger(comboStat, "blitz-break");
        if (!late && clock) {
          const now = performance.now();
          const fromFrac = remainingMs(clock, now) / clock.totalMs;
          const { clock: c, lostMs } = penalize(clock, WRONG_PENALTY_MS, now);
          clock = c;
          state = { ...state, penaltyMs: state.penaltyMs + lostMs };
          tick(); // may end the game right here if the penalty emptied the clock
          if (lostMs > 0) {
            floatAt(clockBox, "blitz-float-penalty", el("b", { text: `−${WRONG_PENALTY_MS / 1000}s` }));
            flashLoss(fromFrac, remainingMs(clock, now) / clock.totalMs);
            retrigger(clockBox, "blitz-hurt");
          }
        }
      }
      if (late) updateSplash();
    }

    function celebrate(award, before, late) {
      const parts = [el("span", { class: "blitz-part", text: `${award.base.toLocaleString()}` })];
      if (award.mult > 1) parts.push(el("span", { class: "blitz-part blitz-part-combo", text: `${formatMultiplier(award.mult)} 🔥` }));
      if (award.bonus) parts.push(el("span", { class: "blitz-part blitz-part-speed", text: `+${award.bonus.toLocaleString()} ⚡` }));
      floatAt(
        scoreStat,
        award.bonus ? "blitz-float-score is-fast" : "blitz-float-score",
        el("b", { text: `+${award.total.toLocaleString()}` }),
        el("span", { class: "blitz-parts" }, parts)
      );
      retrigger(scoreStat, "blitz-bump");
      if (late) {
        ctx.toast(`Buzzer beater! +${award.total.toLocaleString()}`, "success", 2000);
        return;
      }
      const prevMult = comboMultiplier(before.streak);
      const nextMult = comboMultiplier(state.streak);
      if (nextMult > prevMult) retrigger(comboStat, "blitz-bump");
      if (nextMult >= MAX_MULTIPLIER && prevMult < MAX_MULTIPLIER) {
        ctx.sfx("levelup");
        ctx.toast("MAX COMBO ×3 — triple points!", "success", 2200);
        const rect = comboStat.getBoundingClientRect();
        ctx.confetti({
          count: 70,
          x: (rect.left + rect.width / 2) / Math.max(1, window.innerWidth),
          y: (rect.top + rect.height / 2) / Math.max(1, window.innerHeight),
        });
      } else if (nextMult >= 2 && prevMult < 2) {
        ctx.toast("Combo ×2 — double points!", "success", 1800);
      }
    }

    // ---- splash screens ----------------------------------------------------------
    let splashScore = null;
    let splashSub = null;

    function splash() {
      splashScore = el("b", { class: "blitz-timeup-score", text: state.score.toLocaleString() });
      splashSub = el("p", { class: "blitz-timeup-sub" });
      updateSplash();
      return el(
        "section",
        { class: "blitz-timeup", role: "status" },
        el("div", { class: "blitz-timeup-icon", "aria-hidden": "true", text: "⏰" }),
        el("h2", { class: "blitz-timeup-title", text: "Time's up!" }),
        el("p", { class: "blitz-timeup-points" }, el("span", { "aria-hidden": "true", text: "⚡ " }), splashScore, " points"),
        splashSub
      );
    }

    function updateSplash() {
      if (!splashScore) return;
      splashScore.textContent = state.score.toLocaleString();
      const bits = [`${state.answered} answered`];
      if (state.answered) bits.push(`${accuracyPercent(state.correct, state.answered)}% accuracy`);
      if (state.bestStreak >= 2) bits.push(`best combo ${formatMultiplier(state.bestMult)}`);
      splashSub.textContent = bits.join(" · ");
    }

    async function countdown() {
      const num = el("div", { class: "blitz-count", text: "3" });
      qArea.replaceChildren(
        el(
          "section",
          { class: "blitz-ready pop-in", "aria-live": "assertive" },
          el("p", { class: "blitz-ready-title", text: "Get ready!" }),
          num,
          el("p", { class: "blitz-ready-hint" }, `${durationSec} seconds on the clock — wrong answers cost 5 s`),
          el("p", { class: "blitz-ready-keys only-mouse" }, "Press ", el("kbd", { text: "1" }), "–", el("kbd", { text: "4" }), " to answer")
        )
      );
      for (const n of ["3", "2", "1"]) {
        num.textContent = n;
        retrigger(num, "blitz-beat");
        ctx.sfx("tick");
        await ctx.sleep(COUNTDOWN_BEAT_MS);
      }
      num.textContent = "GO!";
      num.classList.add("is-go");
      retrigger(num, "blitz-beat");
      ctx.sfx("levelup");
      await ctx.sleep(GO_MS);
    }

    // ---- game ------------------------------------------------------------------
    renderHud();
    renderClock(durationSec * 1000, false);
    await countdown();

    clock = createClock(durationSec, performance.now());
    ticker = ctx.setInterval(tick, TICK_MS);
    tick();

    while (!over) {
      // Each new question starts at the top so the HUD + prompt are in view on phones.
      if (window.scrollY > 0) window.scrollTo({ top: 0, behavior: "auto" });
      const asked = ctx.ask(qArea, {
        correctDelay: CORRECT_DELAY,
        wrongDelay: WRONG_DELAY,
        pointsLabel: (r) => `+${scoreAnswer({ base: baseOf(r), streak: state.streak, timeMs: r.timeMs }).total.toLocaleString()}`,
        onAnswered,
      });
      // An ask abandoned at the buzzer rejects (AbortError) only when the game is torn
      // down; nobody awaits it any more, so swallow that late rejection.
      asked.catch(() => {});
      const outcome = await Promise.race([asked, timeUp]);
      if (outcome === TIME_UP) break;
    }

    await ctx.sleep(TIME_UP_SPLASH_MS);
    return buildResult(state, durationSec);
  },
};
