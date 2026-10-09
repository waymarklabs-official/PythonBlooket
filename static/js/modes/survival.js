/**
 * Survival (id "survival") — endless Python questions, three lives.
 *
 * Rules (small pure functions below, exported for tests):
 *   - Start with 3 lives on the chosen tier (Easy / Medium / Hard).
 *   - 3 correct in a row at the current tier climbs one tier (max Hard) — "Level up!".
 *   - A wrong answer (or running out of time) costs a life and drops one tier (min Easy).
 *   - Each correct answer earns the question's base points (Easy 100 / Medium 250 /
 *     Hard 500) times the streak multiplier shown in the HUD when you answer:
 *     ×1 (streak 0-2), ×1.5 (3-5), ×2 (6-9), ×3 (10+). What you see is what you earn.
 *   - Every 10th correct answer grants a bonus life (max 5).
 *   - Game over at 0 lives. Score = total points; won = null (endless, no win/lose).
 *
 * play(ctx) wires the rules to the DOM: a HUD (hearts, tier + level-up pips,
 * multiplier, animated score, questions survived), the ctx.ask() card, a level-up
 * splash between questions and a break-heart game-over panel. Every timer goes
 * through ctx.* so quitting never leaks; AbortError is simply allowed to propagate.
 */

import { isModalOpen } from "../ui.js";

// ---------------------------------------------------------------------------
// Tuning
// ---------------------------------------------------------------------------

export const TIERS = {
  1: { id: 1, label: "Easy", stars: "★", points: 100 },
  2: { id: 2, label: "Medium", stars: "★★", points: 250 },
  3: { id: 3, label: "Hard", stars: "★★★", points: 500 },
};
export const MIN_TIER = 1;
export const MAX_TIER = 3;
export const START_LIVES = 3;
export const MAX_LIVES = 5;
export const LEVEL_UP_STREAK = 3; // correct in a row at the current tier to climb
export const BONUS_LIFE_EVERY = 10; // every Nth correct answer grants a life
/** Streak -> multiplier, highest first. */
export const MULTIPLIER_STEPS = [
  { streak: 10, mult: 3 },
  { streak: 6, mult: 2 },
  { streak: 3, mult: 1.5 },
  { streak: 0, mult: 1 },
];
export const TIMER_CHOICES = [0, 30, 15];

const LEVEL_SPLASH_MS = 1500;
const GAME_OVER_MS = 4800;
const HEART_BREAK_MS = 720;
const FLOAT_MS = 1150;

// ---------------------------------------------------------------------------
// Pure rules
// ---------------------------------------------------------------------------

export function clampTier(tier) {
  const n = Math.round(Number(tier));
  if (!Number.isFinite(n) || n <= MIN_TIER) return MIN_TIER;
  return n >= MAX_TIER ? MAX_TIER : n;
}

export function multiplierFor(streak) {
  for (const step of MULTIPLIER_STEPS) if (streak >= step.streak) return step.mult;
  return 1;
}

/** 0 (×1) … 3 (×3): drives the badge colour. */
export function multiplierLevel(mult) {
  return mult >= 3 ? 3 : mult >= 2 ? 2 : mult > 1 ? 1 : 0;
}

/** The next multiplier step above `streak` ({streak, mult}), or null at the top. */
export function nextMultiplierStep(streak) {
  let next = null;
  for (const step of MULTIPLIER_STEPS) if (step.streak > streak) next = step;
  return next;
}

export function formatMultiplier(mult) {
  return `×${mult}`;
}

export function formatNumber(n) {
  return Math.round(Number(n) || 0).toLocaleString();
}

export function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export function livesText(n) {
  return n === 1 ? "1 life" : `${n} lives`;
}

export function pointsFor(base, mult) {
  return Math.round(base * mult);
}

export function newRun(startTier = MIN_TIER) {
  const tier = clampTier(startTier);
  return {
    lives: START_LIVES,
    score: 0,
    tier,
    startTier: tier,
    streak: 0,
    tierStreak: 0, // correct in a row at the current tier
    answered: 0,
    correct: 0,
    survived: 0, // questions answered and lived through
    bestStreak: 0,
    highestTier: tier,
    topMultiplier: 1,
    livesEarned: 0,
    hardAnswered: 0,
    hardCorrect: 0,
  };
}

/**
 * Apply one answer. Returns {state, ev} — a NEW state plus what happened (for the UI).
 * answer: {correct, difficulty (of the question asked), basePoints (server points if correct)}
 */
export function applyAnswer(prev, { correct = false, difficulty, basePoints } = {}) {
  const s = { ...prev };
  const asked = TIERS[difficulty] ? Number(difficulty) : prev.tier;
  const multiplier = multiplierFor(prev.streak);
  const ev = {
    correct: !!correct,
    earned: 0,
    multiplier, // applied to this answer
    multiplierAfter: multiplier,
    multiplierUp: false,
    streakLost: false,
    tierBefore: prev.tier,
    leveledUp: false,
    tierDown: false,
    lostLife: false,
    lastLife: false,
    bonusLife: false,
    livesFull: false,
    gameOver: false,
  };
  s.answered += 1;
  if (asked === 3) s.hardAnswered += 1;

  if (correct) {
    const base = Number(basePoints) > 0 ? Number(basePoints) : TIERS[asked].points;
    ev.earned = pointsFor(base, multiplier);
    s.score += ev.earned;
    s.correct += 1;
    if (asked === 3) s.hardCorrect += 1;
    s.streak += 1;
    s.bestStreak = Math.max(s.bestStreak, s.streak);
    s.tierStreak += 1;
    if (s.tierStreak >= LEVEL_UP_STREAK && s.tier < MAX_TIER) {
      s.tier += 1;
      s.tierStreak = 0;
      ev.leveledUp = true;
    }
    if (s.correct % BONUS_LIFE_EVERY === 0) {
      if (s.lives < MAX_LIVES) {
        s.lives += 1;
        s.livesEarned += 1;
        ev.bonusLife = true;
      } else ev.livesFull = true;
    }
  } else {
    ev.streakLost = multiplier > 1;
    s.streak = 0;
    s.tierStreak = 0;
    s.lives = Math.max(0, s.lives - 1);
    ev.lostLife = true;
    ev.lastLife = s.lives === 1;
    if (s.lives > 0 && s.tier > MIN_TIER) {
      s.tier -= 1;
      ev.tierDown = true;
    }
  }

  ev.multiplierAfter = multiplierFor(s.streak);
  ev.multiplierUp = ev.multiplierAfter > multiplier;
  s.topMultiplier = Math.max(s.topMultiplier, ev.multiplierAfter);
  s.highestTier = Math.max(s.highestTier, s.tier);
  ev.gameOver = s.lives <= 0;
  if (!ev.gameOver) s.survived += 1;
  return { state: s, ev };
}

/** Text for the "Correct! +N" banner. */
export function pointsLabelFor(ev) {
  const pts = `+${formatNumber(ev.earned)}`;
  return ev.multiplier > 1 ? `${pts} (${formatMultiplier(ev.multiplier)})` : pts;
}

/** Caption under the tier badge. */
export function levelProgressText(s) {
  if (s.tier >= MAX_TIER) return "Top tier!";
  const left = LEVEL_UP_STREAK - s.tierStreak;
  return `${left} to level up`;
}

/** Caption under the multiplier: "🔥 4 streak" + how far to the next step. */
export function streakText(s) {
  const next = nextMultiplierStep(s.streak);
  return {
    count: `🔥 ${s.streak}`,
    next: next ? `${formatMultiplier(next.mult)} in ${next.streak - s.streak}` : "max!",
  };
}

export function bonusProgress(s) {
  const into = s.correct % BONUS_LIFE_EVERY;
  return {
    fraction: into / BONUS_LIFE_EVERY,
    left: BONUS_LIFE_EVERY - into,
    full: s.lives >= MAX_LIVES,
  };
}

export function buildResult(s, { timeLimit = 0 } = {}) {
  const top = TIERS[s.highestTier];
  return {
    score: s.score,
    won: null,
    headline: `You survived ${plural(s.survived, "question")}!`,
    details: [
      ["Highest tier reached", `${top.stars} ${top.label}`],
      ["Best streak", s.bestStreak ? `🔥 ${s.bestStreak} in a row` : "0"],
      ["Top multiplier", formatMultiplier(s.topMultiplier)],
      ["Lives earned", s.livesEarned ? `+${s.livesEarned} ❤️` : "0"],
      ["Hard questions answered", s.hardAnswered ? `${s.hardAnswered} (${s.hardCorrect} ✓)` : "0"],
      ["Settings", `Start ${TIERS[s.startTier].label} · Timer ${timeLimit ? `${timeLimit}s` : "off"}`],
    ],
  };
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

const HEART_SVG =
  '<svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">' +
  '<path class="survival-heart-shape" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>' +
  '<ellipse class="survival-heart-shine" cx="7.4" cy="7.7" rx="2.4" ry="1.45" transform="rotate(-38 7.4 7.7)"/>' +
  "</svg>";

const HEART_STATES = ["is-full", "is-empty", "is-breaking", "is-gaining"];

function heartNode(el, state = "full", extraClass = "") {
  return el(
    "span",
    { class: ["survival-heart", `is-${state}`, extraClass], "aria-hidden": "true" },
    el("span", { class: "survival-heart-half survival-heart-l", html: HEART_SVG }),
    el("span", { class: "survival-heart-half survival-heart-r", html: HEART_SVG })
  );
}

function setHeartState(node, state) {
  node.classList.remove(...HEART_STATES);
  void node.offsetWidth; // restart the CSS animation
  node.classList.add(`is-${state}`);
}

/** Restart a one-shot CSS animation class. */
function replay(node, cls) {
  node.classList.remove(cls);
  void node.offsetWidth;
  node.classList.add(cls);
}

function abortErrorFrom(signal) {
  const reason = signal && signal.reason;
  if (reason && reason.name === "AbortError") return reason;
  try {
    return new DOMException("Game ended", "AbortError");
  } catch {
    const err = new Error("Game ended");
    err.name = "AbortError";
    return err;
  }
}

/**
 * Resolve after `ms`, or earlier on a click on `target` / Enter / Space (after `minMs`).
 * Rejects with AbortError when the game ends. Uses ctx timers; removes its listeners.
 */
function waitOrSkip(ctx, ms, { target = null, minMs = 300 } = {}) {
  return new Promise((resolve, reject) => {
    const signal = ctx.signal;
    if (signal.aborted) return reject(abortErrorFrom(signal));
    const t0 = performance.now();
    let timer = 0;
    const cleanup = () => {
      ctx.clearTimeout(timer);
      document.removeEventListener("keydown", onKey);
      if (target) target.removeEventListener("click", onClick);
      signal.removeEventListener("abort", onAbort);
    };
    const finish = () => {
      cleanup();
      resolve();
    };
    const ready = () => performance.now() - t0 >= minMs;
    function onKey(e) {
      if (e.repeat || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || isModalOpen()) return;
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      if (ready()) finish();
    }
    function onClick() {
      if (ready()) finish();
    }
    function onAbort() {
      cleanup();
      reject(abortErrorFrom(signal));
    }
    signal.addEventListener("abort", onAbort, { once: true });
    document.addEventListener("keydown", onKey);
    if (target) target.addEventListener("click", onClick);
    timer = ctx.setTimeout(finish, ms);
  });
}

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

function createView(ctx, run) {
  const { el } = ctx;

  // ---- lives --------------------------------------------------------------
  const hearts = Array.from({ length: MAX_LIVES }, (_, i) => {
    const h = heartNode(el, i < run.lives ? "full" : "empty", "survival-heart-intro");
    h.style.setProperty("--i", i);
    return h;
  });
  const heartsRow = el("div", { class: "survival-hearts", role: "img" }, hearts);
  const bonusFill = el("span", { class: "survival-bonus-fill" });
  const bonusText = el("span", { class: "survival-bonus-text" });
  const bonus = el("div", { class: "survival-bonus" }, el("span", { class: "survival-bonus-track" }, bonusFill), bonusText);
  const livesTile = el("div", { class: "survival-tile survival-tile-lives", style: { "--i": 0 } }, heartsRow, bonus);

  // ---- tier ---------------------------------------------------------------
  const tierStars = el("span", { class: "survival-tier-stars", "aria-hidden": "true" });
  const tierName = el("span", { class: "survival-tier-name" });
  const tierBadge = el("span", { class: "survival-tier-badge" }, tierStars, tierName);
  const tierWrap = el("div", { class: "survival-pop-wrap" }, tierBadge);
  const pips = Array.from({ length: LEVEL_UP_STREAK }, () => el("i"));
  const pipsRow = el("span", { class: "survival-pips", "aria-hidden": "true" }, pips);
  const tierLeft = el("span", { class: "survival-tier-left" });
  const tierTile = el(
    "div",
    { class: "survival-tile survival-tile-tier", style: { "--i": 1 } },
    tierWrap,
    el("div", { class: "survival-tier-sub survival-sub" }, pipsRow, tierLeft)
  );

  // ---- multiplier ---------------------------------------------------------
  const multBadge = el("span", { class: "survival-mult-badge", dataset: { level: 0 } });
  const multWrap = el("div", { class: "survival-pop-wrap" }, multBadge);
  const streakCount = el("span", { class: "survival-streak-count" });
  const streakNext = el("span", { class: "survival-streak-next" });
  const multTile = el(
    "div",
    { class: "survival-tile survival-tile-mult", style: { "--i": 2 } },
    multWrap,
    el("div", { class: "survival-streak survival-sub" }, streakCount, streakNext)
  );

  // ---- score --------------------------------------------------------------
  const scoreValue = el("span", { class: "survival-score-value", text: "0" });
  const scoreWrap = el("div", { class: "survival-pop-wrap" }, scoreValue);
  // On phones the Survived tile is hidden and its count rides along under the score.
  const survivedMini = el("span", { class: "survival-survived-mini" });
  const scoreTile = el(
    "div",
    { class: "survival-tile survival-tile-score", style: { "--i": 3 } },
    scoreWrap,
    el(
      "span",
      { class: "survival-sub" },
      el("span", { class: "survival-score-label", text: "Score" }),
      survivedMini
    )
  );

  // ---- survived -----------------------------------------------------------
  const survivedValue = el("span", { class: "survival-survived-value", text: "0" });
  const survivedWrap = el(
    "div",
    { class: "survival-pop-wrap survival-survived" },
    el("span", { class: "survival-shield", "aria-hidden": "true", text: "🛡️" }),
    survivedValue
  );
  const survivedTile = el(
    "div",
    { class: "survival-tile survival-tile-survived", style: { "--i": 4 } },
    survivedWrap,
    el("span", { class: "survival-sub" }, "Survived")
  );

  const hud = el(
    "section",
    { class: "survival-hud", "aria-label": "Survival status" },
    livesTile,
    tierTile,
    multTile,
    scoreTile,
    survivedTile
  );
  const live = el("p", { class: "sr-only", "aria-live": "polite" });
  const qarea = el("div", { class: "survival-qarea" });
  const stage = el(
    "div",
    { class: "game-stage survival-stage", dataset: { tier: run.tier } },
    el("div", { class: "survival-vignette survival-vignette-danger", "aria-hidden": "true" }),
    el("div", { class: "survival-vignette survival-vignette-hurt", "aria-hidden": "true" }),
    hud,
    qarea,
    live
  );

  let shown = run; // the state currently drawn

  // ---- rendering ------------------------------------------------------------
  function render(s) {
    // hearts (animated states are left alone; they settle themselves)
    hearts.forEach((h, i) => {
      if (h.classList.contains("is-breaking") || h.classList.contains("is-gaining")) return;
      const want = i < s.lives ? "is-full" : "is-empty";
      if (!h.classList.contains(want)) {
        h.classList.remove(...HEART_STATES);
        h.classList.add(want);
      }
    });
    heartsRow.setAttribute("aria-label", `${livesText(s.lives)} left`);
    const b = bonusProgress(s);
    bonusFill.style.width = `${Math.round(b.fraction * 100)}%`;
    bonusText.textContent = b.full ? "Max lives!" : `+❤️ in ${b.left}`;
    bonus.title = b.full
      ? `You have the maximum ${MAX_LIVES} lives`
      : `${plural(b.left, "more correct answer")} for a bonus life`;

    const t = TIERS[s.tier];
    tierBadge.className = `survival-tier-badge diff-${t.id}`;
    tierStars.textContent = t.stars;
    tierName.textContent = ` ${t.label}`;
    tierBadge.title = `${t.label} questions · ${t.points} points each`;
    pips.forEach((p, i) => p.classList.toggle("is-on", s.tier >= MAX_TIER || i < s.tierStreak));
    pipsRow.classList.toggle("is-max", s.tier >= MAX_TIER);
    pipsRow.classList.toggle("is-close", s.tier < MAX_TIER && s.tierStreak === LEVEL_UP_STREAK - 1);
    tierLeft.textContent = levelProgressText(s);
    stage.dataset.tier = String(s.tier);

    const mult = multiplierFor(s.streak);
    multBadge.textContent = formatMultiplier(mult);
    multBadge.dataset.level = String(multiplierLevel(mult));
    multBadge.title = `Points multiplier ${formatMultiplier(mult)} (streak ${s.streak})`;
    const st = streakText(s);
    streakCount.textContent = st.count;
    streakNext.textContent = ` · ${st.next}`;

    survivedValue.textContent = String(s.survived);
    survivedMini.textContent = `🛡️ ${s.survived} survived`;
    stage.classList.toggle("survival-danger", s.lives === 1);
  }

  function announce(text) {
    live.textContent = "";
    ctx.setTimeout(() => (live.textContent = text), 30);
  }

  /** Floating "+375" etc. rising from a HUD element. */
  function floatFrom(anchor, text, cls) {
    if (!anchor.isConnected) return;
    const sr = stage.getBoundingClientRect();
    const ar = anchor.getBoundingClientRect();
    const node = el("span", {
      class: ["survival-float", cls],
      "aria-hidden": "true",
      text,
      style: { left: `${ar.left - sr.left + ar.width / 2}px`, top: `${ar.top - sr.top + ar.height / 2}px` },
    });
    stage.append(node);
    ctx.setTimeout(() => node.remove(), FLOAT_MS);
  }

  /** Extra line in the engine's feedback banner (life lost, tier change…). */
  function annotateCard(s, ev) {
    const head = qarea.querySelector(".q-banner-head");
    if (!head) return;
    const parts = [];
    if (ev.lostLife) {
      parts.push(s.lives > 1 ? `💔 −1 life · ${s.lives} left` : s.lives === 1 ? "💔 −1 life · last life left!" : "💔 That was your last life!");
    }
    if (ev.tierDown) parts.push(`▼ Back to ${TIERS[s.tier].label}`);
    if (ev.leveledUp) parts.push(`▲ Level up: ${TIERS[s.tier].label}!`);
    if (ev.bonusLife) parts.push("❤️ Bonus life!");
    if (!parts.length) return;
    head.append(
      el("span", { class: ["survival-note", ev.correct ? "survival-note-good" : "survival-note-bad", "pop-in"], text: parts.join("  ·  ") })
    );
  }

  /** Called the instant the server replies. */
  function update(s, ev) {
    const prev = shown;
    shown = s;
    render(s);
    annotateCard(s, ev);

    if (ev.correct) {
      ctx.animateNumber(scoreValue, prev.score, s.score, 650);
      replay(scoreWrap, "survival-bump");
      floatFrom(scoreValue, `+${formatNumber(ev.earned)}`, "survival-float-good");
    }
    if (s.survived !== prev.survived) {
      replay(survivedWrap, "survival-bump");
      replay(survivedMini, "survival-bump");
    }

    // lives
    if (ev.lostLife) {
      const h = hearts[s.lives];
      if (h) {
        setHeartState(h, "breaking");
        ctx.setTimeout(() => {
          if (h.classList.contains("is-breaking")) setHeartState(h, shown.lives > s.lives ? "full" : "empty");
        }, HEART_BREAK_MS);
      }
      floatFrom(heartsRow, "−1 ❤️", "survival-float-bad");
      replay(stage, "survival-hurt");
      ctx.setTimeout(() => ctx.sfx("hit"), 120);
      if (ev.lastLife) {
        ctx.toast("Last life! Careful… 😰", "warn");
        announce("Wrong answer. Last life left!");
      } else if (!ev.gameOver) announce(`Wrong answer. ${livesText(s.lives)} left.`);
    }
    if (ev.bonusLife) {
      const h = hearts[s.lives - 1];
      if (h) {
        setHeartState(h, "gaining");
        ctx.setTimeout(() => {
          if (h.classList.contains("is-gaining")) setHeartState(h, shown.lives >= s.lives ? "full" : "empty");
        }, 900);
      }
      floatFrom(heartsRow, "+1 ❤️", "survival-float-life");
      ctx.toast(`Bonus life for ${s.correct} correct answers! ❤️`, "success");
      ctx.setTimeout(() => ctx.sfx("chest"), 380);
      announce(`Bonus life! You now have ${s.lives} lives.`);
    } else if (ev.livesFull) {
      ctx.toast(`${s.correct} correct! Lives already maxed out 💪`, "info");
    }

    // tier
    if (ev.leveledUp) replay(tierWrap, "survival-tier-up");
    if (ev.tierDown) {
      replay(tierWrap, "survival-tier-down");
      floatFrom(tierBadge, `▼ ${TIERS[s.tier].label}`, "survival-float-bad");
    }

    // multiplier
    if (ev.multiplierUp) {
      replay(multWrap, "survival-mult-up");
      floatFrom(multBadge, `${formatMultiplier(ev.multiplierAfter)}!`, "survival-float-mult");
      if (!ev.leveledUp && !ev.bonusLife) ctx.setTimeout(() => ctx.sfx("chest"), 300);
      if (!ev.leveledUp) announce(`Streak multiplier ${formatMultiplier(ev.multiplierAfter)}!`);
    } else if (ev.streakLost) {
      replay(multWrap, "survival-mult-lost");
    }
  }

  /** Make sure the HUD is on screen before a new question (phones scroll). */
  function bringIntoView() {
    const r = hud.getBoundingClientRect();
    const topbar = document.querySelector(".game-topbar");
    const limit = topbar ? topbar.getBoundingClientRect().bottom : 64;
    if (r.top < limit - 1 && window.scrollY > 0) {
      window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
    }
  }

  async function levelUp(s, ev) {
    bringIntoView();
    const t = TIERS[s.tier];
    const splash = el(
      "div",
      { class: ["survival-splash", `survival-splash-${t.id}`], role: "status", tabindex: "-1" },
      el("div", { class: "survival-splash-rays", "aria-hidden": "true" }),
      el(
        "div",
        { class: "survival-splash-inner" },
        el("div", { class: "survival-splash-kicker", text: "Level up!" }),
        el(
          "div",
          { class: `survival-splash-tier diff-${t.id}` },
          el("span", { "aria-hidden": "true", text: t.stars }),
          ` ${t.label}`
        ),
        el(
          "p",
          { class: "survival-splash-sub" },
          s.tier >= MAX_TIER ? "Top tier! " : "",
          "Questions are now worth ",
          el("b", { text: `${t.points} points` }),
          " each."
        ),
        ev.multiplierUp
          ? el("p", { class: "survival-splash-mult", text: `🔥 Streak bonus ${formatMultiplier(ev.multiplierAfter)}` })
          : null,
        el(
          "p",
          { class: "survival-splash-hint" },
          el("span", { class: "only-mouse", text: "Click or press Enter to continue" }),
          el("span", { class: "only-touch", text: "Tap to continue" })
        )
      )
    );
    qarea.replaceChildren(splash);
    try {
      splash.focus({ preventScroll: true });
    } catch {
      /* ignore */
    }
    ctx.sfx("levelup");
    const r = splash.getBoundingClientRect();
    if (r.width && window.innerWidth && window.innerHeight) {
      ctx.confetti({
        count: 70,
        x: (r.left + r.width / 2) / window.innerWidth,
        y: Math.min(0.6, Math.max(0.15, (r.top + 70) / window.innerHeight)),
      });
    }
    announce(`Level up! ${t.label} questions, ${t.points} points each.`);
    await waitOrSkip(ctx, LEVEL_SPLASH_MS, { target: splash });
  }

  async function gameOver(s) {
    stage.classList.remove("survival-danger");
    stage.classList.add("survival-is-over");
    bringIntoView();
    const big = heartNode(el, "full", "survival-bigheart");
    const btn = el("button", { class: "btn btn-yellow btn-lg survival-results-btn", type: "button" }, "See results ", el("span", { "aria-hidden": "true", text: "▶" }));
    const top = TIERS[s.highestTier];
    const stat = (label, value, cls = "") =>
      el("div", { class: ["survival-go-stat", cls] }, el("b", { text: value }), el("span", { text: label }));
    const panel = el(
      "div",
      { class: "survival-gameover", role: "status" },
      el("div", { class: "survival-bigheart-wrap", "aria-hidden": "true" }, el("span", { class: "survival-bigheart-glow" }), big),
      el("h2", { class: "survival-gameover-title", text: "Game over!" }),
      el("p", { class: "survival-gameover-sub" }, "You survived ", el("b", { text: plural(s.survived, "question") })),
      el(
        "div",
        { class: "survival-go-stats" },
        stat("points", formatNumber(s.score), "is-score"),
        stat("top tier", `${top.stars} ${top.label}`),
        stat("best streak", `🔥 ${s.bestStreak}`)
      ),
      btn
    );
    qarea.replaceChildren(panel);
    try {
      btn.focus({ preventScroll: true });
    } catch {
      /* ignore */
    }
    ctx.setTimeout(() => {
      setHeartState(big, "breaking");
      ctx.sfx("hit");
    }, 700);
    ctx.setTimeout(() => ctx.sfx("lose"), 1000);
    await waitOrSkip(ctx, GAME_OVER_MS, { target: btn, minMs: 500 });
  }

  render(run);
  // The pop-in intro must not replay when a heart later turns full again.
  ctx.setTimeout(() => hearts.forEach((h) => h.classList.remove("survival-heart-intro")), 1400);
  return { stage, qarea, update, levelUp, gameOver, bringIntoView };
}

/** Keep the question buffers for this tier and its neighbours warm. */
function warmBuffers(ctx, s) {
  if (typeof ctx.prefetch !== "function") return;
  for (const t of [s.tier, s.tier + 1, s.tier - 1]) if (TIERS[t]) ctx.prefetch(t);
}

// ---------------------------------------------------------------------------
// Mode
// ---------------------------------------------------------------------------

export default {
  id: "survival",
  name: "Survival",
  icon: "❤️",
  tagline: "Three lives. Questions get harder. How long can you last?",
  description:
    "Answer endless questions with 3 lives. A wrong answer (or running out of time) costs a life and drops you down a tier — lose them all and it's game over.\n" +
    "Get 3 right in a row to level up: Easy → Medium → Hard. Harder questions are worth more: Easy 100, Medium 250, Hard 500 points.\n" +
    "Streaks multiply your points: ×1.5 from 3 in a row, ×2 from 6, ×3 from 10. Every 10 correct answers earns a bonus life (up to 5).",
  difficultySelectable: false,
  difficultyNote:
    "Survival sets the difficulty for you: 3 right in a row moves you up a tier, a miss drops you back down. Pick your starting tier below.",
  options: [
    { key: "start", label: "Starting difficulty", choices: [[1, "Easy"], [2, "Medium"], [3, "Hard"]], default: 1 },
    { key: "timer", label: "Question timer", choices: [[0, "Off"], [30, "30s"], [15, "15s"]], default: 0 },
  ],
  scoreLabel: "Points",

  async play(ctx) {
    const options = (ctx.settings && ctx.settings.options) || {};
    const timeLimit = TIMER_CHOICES.includes(Number(options.timer)) ? Number(options.timer) : 0;
    let run = newRun(options.start);
    const view = createView(ctx, run);
    ctx.root.append(view.stage);
    warmBuffers(ctx, run);

    while (run.lives > 0) {
      const before = run;
      let outcome = null;
      // pointsLabel runs before onAnswered; both share one computed outcome.
      const settle = (r) =>
        (outcome ||= applyAnswer(before, {
          correct: r.correct,
          difficulty: r.question && r.question.difficulty,
          basePoints: r.points,
        }));
      const askOpts = {
        difficulty: run.tier,
        pointsLabel: (r) => pointsLabelFor(settle(r).ev),
        onAnswered: (r) => {
          const o = settle(r);
          run = o.state;
          view.update(o.state, o.ev);
        },
      };
      if (timeLimit) askOpts.timeLimit = timeLimit;

      const result = await ctx.ask(view.qarea, askOpts);
      if (run === before) {
        // onAnswered never ran (shouldn't happen) — apply the answer now.
        const o = settle(result);
        run = o.state;
        view.update(o.state, o.ev);
      }
      warmBuffers(ctx, run);
      if (run.lives <= 0) break;
      if (outcome.ev.leveledUp) await view.levelUp(run, outcome.ev);
      view.bringIntoView();
    }

    await view.gameOver(run);
    return buildResult(run, { timeLimit });
  },
};
