/**
 * Player screens: a student joins a hosted game from their own phone or laptop and plays it.
 *
 *   renderJoin(env, { code })   // the only export; env comes from app.js (show, goHome, backButton, ...)
 *
 * Flow
 *   Join form  -> code + name + blook; the code is looked up as soon as 6 digits are typed.
 *                 A game remembered in this browser (savedPlayer) is resumed silently with the same token.
 *   Lobby      -> "You're in!" while the host waits for everybody.
 *   Live Quiz  -> `question` (sticky bar: question n/N, countdown, rank, score; the QuestionView; on submit the
 *                 view locks and says "Answer locked in"; when the countdown ends whatever is typed/picked
 *                 is submitted exactly once) -> `reveal` (points breakdown, rank change, explanation, top 5)
 *                 -> next question ... -> finished.
 *   Time Rush  -> `running`: one question at a time at your own pace; the answer is graded right away
 *                 (feedback card + Continue; auto-continues after a correct one), a wrong answer starts the
 *                 server's cooldown ("Engine cooling down 2..."), a small top-5 strip under the question.
 *   Finished   -> rank, medal, confetti for the podium, stats, podium, Play again / Home.
 *   Also       -> kicked, game gone/ended, connection banner (polling keeps retrying), reload = resume.
 *
 * The server is authoritative: answers are never in a payload before the reveal. Everything typed is kept in
 * localStorage per question id (`store`), so a reload / dropped connection never loses code.
 * Every piece of player-controlled text goes through textContent (el()), never innerHTML.
 */

import { Poller, cleanCode, clock, playJoin, playLookup, playerSession, prettyCode, savedPlayer } from "./hostapi.js";
import { createQuestionView } from "./questions.js";
import {
  AVATARS,
  animateNumber,
  avatarColor,
  blook,
  confetti,
  confirmDialog,
  createMuteButton,
  el,
  formatTime,
  renderInlineCode,
  sfx,
  storageGet,
  storageSet,
  toast,
} from "./ui.js";

const NAME_MAX = 16;
const TICK_MS = 100;
const RUSH_COOLDOWN = 3; // seconds, only used to scale the cooldown bar
const FATAL = new Set(["not_found", "kicked", "bad_token"]);
const MODE_LABEL = { live: "Live Quiz", rush: "Time Rush" };
const WAIT_LINES = [
  "Warming up your fingers…",
  "Remember: indentation matters!",
  "Colons are not optional.",
  "Stretching the keyboard…",
  "Loading 100% of your brain…",
  "No semicolons needed. Relax.",
];

const isCoarse = () => {
  try {
    return window.matchMedia("(pointer: coarse)").matches;
  } catch {
    return false;
  }
};

const fmtNum = (n) => Math.round(Number(n) || 0).toLocaleString();
const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

function ordinal(n) {
  const v = n % 100;
  if (v >= 11 && v <= 13) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th"}`;
}

const plural = (n, one, many = `${one}s`) => `${fmtNum(n)} ${n === 1 ? one : many}`;

/** Friendly text for an API failure. */
function errorText(err) {
  switch (err && err.reason) {
    case "not_found":
      return "No game with that code. Check the number on your teacher's screen.";
    case "locked":
      return "This game is locked. Ask your teacher to unlock it.";
    case "finished":
      return "That game is already over.";
    case "name_taken":
      return "Somebody already has that name. Try another one (add a number?).";
    case "bad_name":
      return (err && err.message) || "Please pick a different name.";
    case "full":
      return "This game is full.";
    case "rate_limited":
      return "Slow down a little, then try again.";
    case "network":
      return "Can't reach the game server. Check your Wi-Fi and try again.";
    default:
      return (err && err.message) || "Something went wrong. Please try again.";
  }
}

// ---------------------------------------------------------------------------
// Typed answers survive reloads: drafts, sent answers and rank history per question id
// ---------------------------------------------------------------------------

const STORE_KEY = "pyblooket.playdrafts";
const store = {
  load(code) {
    const v = storageGet(STORE_KEY, null);
    return v && v.code === code && v.items ? v : { code, items: {}, order: [], rankAt: {} };
  },
  patch(code, qid, patch) {
    const s = this.load(code);
    s.items[qid] = { ...(s.items[qid] || {}), ...patch };
    const ids = Object.keys(s.items);
    for (const id of ids.slice(0, Math.max(0, ids.length - 40))) delete s.items[id];
    storageSet(STORE_KEY, s);
  },
  get(code, qid) {
    return this.load(code).items[qid] || {};
  },
  /** Remember my rank after question `qid`; returns the rank after the question before it (or null). */
  rank(code, qid, rank) {
    const s = this.load(code);
    if (!s.order.includes(qid)) s.order.push(qid);
    s.rankAt[qid] = rank;
    s.order = s.order.slice(-60);
    storageSet(STORE_KEY, s);
    const i = s.order.indexOf(qid);
    return i > 0 ? s.rankAt[s.order[i - 1]] ?? null : null;
  },
  clear() {
    storageSet(STORE_KEY, null);
  },
};

/** True when `resp` is nothing worth sending (time ran out with nothing typed/picked). */
function isBlankResponse(q, resp) {
  if (resp === null || resp === undefined) return true;
  switch (q.qtype) {
    case "choice":
      return !Number.isInteger(resp);
    case "blanks":
      return !Array.isArray(resp) || resp.every((s) => !String(s ?? "").trim());
    case "match":
      return !Array.isArray(resp) || resp.every((v) => v === null || v === undefined);
    case "code": {
      const text = String(resp).trim();
      return text === "" || text === String((q.task && q.task.starter) || "").trim();
    }
    default:
      return false;
  }
}

/** A saved response is only restored when it still has the right shape for the question. */
function validInitial(q, v) {
  if (v === undefined || v === null) return undefined;
  if (q.qtype === "choice") return Number.isInteger(v) ? v : undefined;
  if (q.qtype === "blanks") return Array.isArray(v) && v.length === (q.blanks || []).length && v.every((s) => typeof s === "string") ? v : undefined;
  if (q.qtype === "match") return Array.isArray(v) && v.length === ((q.match && q.match.items) || []).length ? v : undefined;
  if (q.qtype === "code") return typeof v === "string" ? v : undefined;
  return undefined;
}

// ---------------------------------------------------------------------------
// Entry point: resume or show the join form
// ---------------------------------------------------------------------------

let active = null; // the Play currently on screen (only one at a time)

export function renderJoin(env, { code } = {}) {
  if (active) active.dispose();
  const wanted = code ? cleanCode(code) : "";
  const saved = savedPlayer.get();
  if (saved && (!wanted || saved.code === wanted)) {
    resumeGame(env, saved, { explicit: !!wanted });
    return;
  }
  showJoinForm(env, { code: wanted });
}

/** Quietly rejoin the game this browser remembers (same token). */
function resumeGame(env, saved, { explicit }) {
  let cancelled = false;
  let timer = 0;
  const session = playerSession(saved.code, saved.token);
  const status = el("p", { class: "pl-connect-text", role: "status", text: `Reconnecting to game ${prettyCode(saved.code)}…` });
  const notYou = el("button", {
    class: "pl-link",
    type: "button",
    text: "Not you? Leave this game",
    onClick: () => {
      cancelled = true;
      window.clearTimeout(timer);
      session.leave().catch(() => {});
      savedPlayer.clear();
      store.clear();
      showJoinForm(env, {});
    },
  });
  const screen = el(
    "div",
    { class: "screen pl-screen pl-connect" },
    el("div", { class: "card pl-card pl-connect-card" }, blook(saved.avatar || AVATARS[0], { size: 72 }), el("h1", { class: "pl-h", text: saved.name || "Welcome back" }), el("div", { class: "spinner", "aria-hidden": "true" }), status, notYou)
  );
  env.show(screen, { focus: false });

  const attempt = async () => {
    if (cancelled) return;
    try {
      const state = await session.state();
      if (cancelled) return;
      if (state.phase === "finished" && !explicit) {
        // "Join a game" with an old, finished game remembered: start fresh
        savedPlayer.clear();
        store.clear();
        showJoinForm(env, {});
        return;
      }
      startPlay(env, saved, state);
    } catch (err) {
      if (cancelled) return;
      if (err && FATAL.has(err.reason)) {
        savedPlayer.clear();
        store.clear();
        const notice =
          err.reason === "kicked"
            ? "The host removed you from that game."
            : err.reason === "not_found"
              ? "That game has ended."
              : "You're not in that game any more.";
        showJoinForm(env, { code: explicit ? saved.code : "", notice });
        return;
      }
      status.textContent = "Can't reach the game server. Trying again…";
      timer = window.setTimeout(attempt, 2500);
    }
  };
  attempt();
}

function startPlay(env, info, state) {
  if (active) active.dispose();
  const play = new Play(env, info, state);
  active = play;
  play.start();
}

// ---------------------------------------------------------------------------
// Join form
// ---------------------------------------------------------------------------

function showJoinForm(env, { code = "", notice = "" } = {}) {
  const settings = env.settings || {};
  const draft = {
    name: String(settings.playerName || "").slice(0, NAME_MAX),
    avatar: AVATARS.includes(settings.avatar) ? settings.avatar : AVATARS[0],
  };
  let lookupSeq = 0;
  let joining = false;

  const status = el("p", { class: "pl-code-status", id: "pl-code-status", role: "status" });
  const setStatus = (kind, text) => {
    status.className = `pl-code-status is-${kind}`;
    status.textContent = text;
  };

  const codeInput = el("input", {
    class: "pl-code-input",
    id: "pl-code",
    type: "text",
    inputmode: "numeric",
    pattern: "[0-9 ]*",
    autocomplete: "off",
    autocapitalize: "off",
    autocorrect: "off",
    spellcheck: "false",
    enterkeyhint: "next",
    maxlength: "40",
    placeholder: "000 000",
    "aria-describedby": "pl-code-status",
    value: code ? prettyCode(code) : "",
    onInput: () => {
      // a pasted join link works too
      const link = /join=(\d{6})/.exec(codeInput.value);
      const digits = link ? link[1] : cleanCode(codeInput.value);
      codeInput.value = prettyCode(digits);
      if (digits.length === 6) lookup(digits);
      else {
        lookupSeq++;
        setStatus("", "");
      }
    },
    onKeydown: (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (cleanCode(codeInput.value).length === 6) nameInput.focus();
      }
    },
  });

  const nameInput = el("input", {
    class: "text-input pl-name-input",
    id: "pl-name",
    type: "text",
    maxlength: String(NAME_MAX),
    autocomplete: "off",
    autocapitalize: "words",
    autocorrect: "off",
    spellcheck: "false",
    enterkeyhint: "go",
    placeholder: "Your name",
    "aria-describedby": "pl-name-error",
    value: draft.name,
    onInput: () => {
      draft.name = nameInput.value;
      nameError.textContent = "";
      nameInput.removeAttribute("aria-invalid");
    },
  });
  const nameError = el("p", { class: "pl-field-error", id: "pl-name-error", role: "alert" });

  const preview = { node: blook(draft.avatar, { size: 64, className: "pl-preview" }) };
  const avatarButtons = AVATARS.map((a) =>
    el(
      "button",
      {
        class: "pl-avatar",
        type: "button",
        style: { "--blook-bg": avatarColor(a) },
        "aria-label": `Blook ${a}`,
        "aria-pressed": String(a === draft.avatar),
        dataset: { avatar: a },
        onClick: () => {
          draft.avatar = a;
          for (const b of avatarButtons) b.setAttribute("aria-pressed", String(b.dataset.avatar === a));
          const fresh = blook(a, { size: 64, className: "pl-preview pop-in" });
          preview.node.replaceWith(fresh);
          preview.node = fresh;
          sfx("click");
        },
      },
      el("span", { "aria-hidden": "true", text: a })
    )
  );

  const joinBtn = el("button", { class: "btn btn-green btn-lg pl-join-btn", type: "submit" }, "Join game");
  const formError = el("p", { class: "pl-form-error", role: "alert" });

  async function lookup(digits) {
    const seq = ++lookupSeq;
    setStatus("busy", "Looking for that game…");
    try {
      const g = await playLookup(digits);
      if (seq !== lookupSeq) return null;
      const label = `${g.title ? `${g.title} · ` : ""}${MODE_LABEL[g.mode] || "Game"}`;
      if (g.phase === "finished") setStatus("warn", `${label} is already over.`);
      else if (g.locked) setStatus("warn", `${label} is locked. Ask your teacher to unlock it.`);
      else if (g.phase === "lobby") setStatus("ok", `✓ ${label} · ${plural(g.players, "player")} waiting`);
      else setStatus("ok", `✓ ${label} · already started, you'll join with 0 points`);
      return g;
    } catch (err) {
      if (seq !== lookupSeq) return null;
      setStatus("error", errorText(err));
      return null;
    }
  }

  async function submit() {
    if (joining) return;
    formError.textContent = "";
    const digits = cleanCode(codeInput.value);
    const name = nameInput.value.replace(/\s+/g, " ").trim();
    if (digits.length !== 6) {
      setStatus("error", "The game code has 6 numbers.");
      codeInput.focus();
      return;
    }
    if (!name) {
      nameError.textContent = "Type your name first.";
      nameInput.setAttribute("aria-invalid", "true");
      nameInput.focus();
      return;
    }
    joining = true;
    joinBtn.disabled = true;
    joinBtn.replaceChildren(el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), " Joining…");
    try {
      const g = await playLookup(digits);
      if (g.phase === "finished") throw Object.assign(new Error(), { reason: "finished" });
      if (g.locked && !(savedPlayer.get() || {}).token) throw Object.assign(new Error(), { reason: "locked" });
      const saved = savedPlayer.get();
      const joined = await playJoin({ code: digits, name, avatar: draft.avatar, ...(saved && saved.code === digits ? { token: saved.token } : {}) });
      const me = (joined.state && joined.state.me) || {};
      const info = { code: digits, token: joined.token, playerId: joined.player_id, name: me.name || name, avatar: me.avatar || draft.avatar };
      savedPlayer.set(info);
      store.clear();
      env.rememberPlayer({ playerName: info.name, avatar: info.avatar });
      sfx("correct");
      startPlay(env, info, joined.state);
    } catch (err) {
      joining = false;
      joinBtn.disabled = false;
      joinBtn.replaceChildren("Join game");
      const text = errorText(err);
      if (err.reason === "name_taken" || err.reason === "bad_name") {
        nameError.textContent = text;
        nameInput.setAttribute("aria-invalid", "true");
        nameInput.focus();
      } else {
        if (err.reason === "not_found" || err.reason === "locked" || err.reason === "finished") {
          // the status line under the code box already says it (and is an aria-live region)
          setStatus(err.reason === "not_found" ? "error" : "warn", text);
          codeInput.scrollIntoView({ block: "center", behavior: "smooth" });
        } else formError.textContent = text;
        if (err.reason === "not_found") codeInput.focus();
      }
      sfx("wrong");
    }
  }

  const form = el(
    "form",
    { class: "card pl-card pl-join-card", novalidate: true, onSubmit: (e) => (e.preventDefault(), submit()) },
    el("div", { class: "pl-field" }, el("label", { for: "pl-code", text: "Game code" }), codeInput, status),
    el("div", { class: "pl-field" }, el("label", { for: "pl-name", text: "Your name" }), nameInput, nameError),
    el(
      "div",
      { class: "pl-field" },
      el("span", { class: "pl-label", id: "pl-blook-label", text: "Your blook" }),
      el("div", { class: "pl-blook-row" }, preview.node, el("div", { class: "pl-avatar-grid", role: "group", "aria-labelledby": "pl-blook-label" }, avatarButtons))
    ),
    formError,
    el("div", { class: "pl-sticky-actions" }, joinBtn)
  );

  const screen = el(
    "div",
    { class: "screen pl-screen pl-join" },
    el("div", { class: "pl-join-top" }, env.backButton("Back", () => env.goHome())),
    el("h1", { class: "pl-title", tabindex: "-1", text: "Join a game" }),
    el("p", { class: "pl-sub", text: "Type the code from your teacher's screen." }),
    notice ? el("div", { class: "pl-notice", role: "status" }, el("span", { "aria-hidden": "true", text: "ℹ️" }), el("span", { text: notice })) : null,
    form
  );
  const prefilled = cleanCode(code).length === 6;
  (prefilled && draft.name ? nameInput : prefilled ? nameInput : codeInput).setAttribute("data-autofocus", "");
  env.show(screen);
  if (prefilled) lookup(cleanCode(code));
}

// ---------------------------------------------------------------------------
// End screens (kicked / game gone)
// ---------------------------------------------------------------------------

function showEndScreen(env, { icon, title, text, again = true }) {
  const screen = el(
    "div",
    { class: "screen pl-screen pl-end" },
    el(
      "div",
      { class: "card pl-card pl-end-card pop-in" },
      el("div", { class: "pl-end-icon", "aria-hidden": "true", text: icon }),
      el("h1", { class: "pl-h", tabindex: "-1", "data-autofocus": "", text: title }),
      el("p", { class: "pl-end-text", text }),
      el(
        "div",
        { class: "pl-end-actions" },
        again ? el("button", { class: "btn btn-green btn-lg", type: "button", text: "Join another game", onClick: () => renderJoin(env, {}) }) : null,
        el("button", { class: "btn btn-white", type: "button", text: "Home", onClick: () => env.goHome() })
      )
    )
  );
  env.show(screen);
}

// ---------------------------------------------------------------------------
// The game itself
// ---------------------------------------------------------------------------

class Play {
  constructor(env, info, state) {
    this.env = env;
    this.info = info;
    this.code = info.code;
    this.session = playerSession(info.code, info.token);
    this.initialState = state;
    this.state = null;
    this.key = ""; // what the main area currently shows: "lobby", "lq:<qid>", "lr:<qid>", "rq:<qid>", "cool", "final" ...
    this.view = null;
    this.viewQid = null;
    this.deadline = null;
    this.limit = 0;
    this.sentLive = new Set(); // live qids already sent (or deliberately skipped)
    this.timeUp = new Set(); // live qids whose countdown already ran out
    this.hold = null; // rush: feedback of my last answer is on screen
    this.cool = null; // rush: cooldown screen state
    this.online = true;
    this.disposed = false;
    this.draftTimer = 0;
    this.pendingDraft = null;
    this.lastNudge = 0;
    this.announced = new Set();
    this.waitIdx = 0;
    this.waitTimer = 0;
    this.score = 0;
    this.buildFrame();
    this.poller = new Poller(
      async (since) => {
        const s = await this.session.state(since);
        this.setOnline(true);
        return s;
      },
      {
        onState: (s) => this.onState(s),
        onError: () => this.setOnline(false),
        onFatal: (err) => this.onFatal(err),
      }
    );
    this._pagehide = () => this.flushDraft();
    this._offline = () => this.setOnline(false);
    this._online = () => {
      this.setOnline(true);
      this.poller.nudge();
    };
  }

  // -- frame ------------------------------------------------------------------------------

  buildFrame() {
    const { info } = this;
    const sr = (id) => el("span", { id, class: "sr-only", role: "status", "aria-live": "polite" });
    this.live = sr("pl-live");
    this.pills = {
      q: el("span", { class: "pl-pill pl-pill-q", hidden: true }),
      time: el("span", { class: "pl-pill pl-pill-time", role: "timer", "aria-label": "Time left", hidden: true }, el("span", { "aria-hidden": "true", text: "⏱" }), el("b", { text: "0:00" })),
      rank: el("span", { class: "pl-pill pl-pill-rank", "aria-label": "Your rank" }, el("span", { "aria-hidden": "true", text: "🏆" }), el("b", { text: "-" })),
      score: el("span", { class: "pl-pill pl-pill-score", "aria-label": "Your score" }, el("span", { "aria-hidden": "true", text: "⭐" }), el("b", { text: "0" })),
      streak: el("span", { class: "pl-pill pl-pill-streak", hidden: true }, el("span", { "aria-hidden": "true", text: "🔥" }), el("b", { text: "0" })),
    };
    this.bar = el("i", { class: "pl-bar-fill" });
    this.stats = el(
      "div",
      { class: "pl-stats", hidden: true },
      el("div", { class: "pl-pills" }, this.pills.q, this.pills.time, this.pills.rank, this.pills.score, this.pills.streak),
      el("div", { class: "pl-bar", "aria-hidden": "true" }, this.bar)
    );
    this.conn = el("div", { class: "pl-conn", role: "status", hidden: true }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), el("span", { text: "Connection problem. Trying again… your answers are safe." }));
    this.leaveBtn = el("button", { class: "icon-btn pl-leave", type: "button", "aria-label": "Leave game", title: "Leave game", onClick: () => this.leave() }, el("span", { "aria-hidden": "true", text: "🚪" }));
    this.main = el("main", { class: "pl-main" });
    this.root = el(
      "div",
      { class: "screen pl-screen pl-play" },
      el(
        "header",
        { class: "pl-top" },
        el("div", { class: "pl-me" }, blook(info.avatar || AVATARS[0], { size: 36 }), el("span", { class: "pl-me-name", text: info.name })),
        el("div", { class: "pl-top-actions" }, createMuteButton("pl-mute"), this.leaveBtn)
      ),
      this.stats,
      this.conn,
      this.main,
      this.live
    );
  }

  start() {
    this.env.show(this.root, { focus: false });
    window.addEventListener("pagehide", this._pagehide);
    window.addEventListener("offline", this._offline);
    window.addEventListener("online", this._online);
    this.ticker = window.setInterval(() => this.tick(), TICK_MS);
    this.poller.push(this.initialState);
    this.poller.start();
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.poller.stop();
    window.clearInterval(this.ticker);
    window.clearTimeout(this.draftTimer);
    window.clearTimeout(this.waitTimer);
    this.clearHold();
    this.dropView();
    window.removeEventListener("pagehide", this._pagehide);
    window.removeEventListener("offline", this._offline);
    window.removeEventListener("online", this._online);
    if (active === this) active = null;
  }

  announce(text) {
    this.live.textContent = "";
    window.setTimeout(() => (this.live.textContent = text), 30);
  }

  setOnline(ok) {
    if (this.disposed || ok === this.online) return;
    this.online = ok;
    this.conn.hidden = ok;
  }

  // -- state --------------------------------------------------------------------------------

  onState(state) {
    if (this.disposed) return;
    this.state = state;
    this.render();
  }

  render() {
    const state = this.state;
    if (!state) return;
    this.updateStats(state);
    switch (state.phase) {
      case "lobby":
        return this.showLobby(state);
      case "question":
        return this.showLiveQuestion(state);
      case "reveal":
        return this.showReveal(state);
      case "running":
        return this.showRush(state);
      case "finished":
        return this.showFinished(state);
      default:
        return this.showWaiting("Hold on…");
    }
  }

  onFatal(err) {
    if (this.disposed) return;
    savedPlayer.clear();
    store.clear();
    const env = this.env;
    this.dispose();
    if (err.reason === "kicked") showEndScreen(env, { icon: "👋", title: "The host removed you", text: "You were taken out of the game. You can join again if it was a mistake." });
    else if (err.reason === "not_found") showEndScreen(env, { icon: "🏁", title: "This game has ended", text: "The game is over or the host closed it." });
    else showEndScreen(env, { icon: "🚪", title: "You're not in this game", text: "You left the game or it no longer knows you. Join again with the code." });
  }

  /** Common handling for API errors from answer/run calls; true when it was a game-over style error. */
  fatalError(err) {
    if (err && FATAL.has(err.reason)) {
      this.onFatal(err);
      return true;
    }
    return false;
  }

  async leave() {
    if (this.disposed) return;
    const phase = this.state && this.state.phase;
    if (phase !== "finished") {
      const ok = await confirmDialog({
        title: "Leave this game?",
        message: phase === "lobby" ? "You can join again with the code." : "Your score will be removed from the game.",
        confirmText: "Leave",
        cancelText: "Stay",
        danger: true,
        icon: "🚪",
      });
      if (!ok || this.disposed) return;
    }
    const env = this.env;
    const session = this.session;
    this.dispose();
    savedPlayer.clear();
    store.clear();
    if (phase !== "finished") session.leave().catch(() => {});
    if (phase === "finished") env.goHome();
    else renderJoin(env, {});
  }

  // -- header ---------------------------------------------------------------------------------

  updateStats(state) {
    const me = state.me || {};
    const showStats = state.phase !== "lobby" && state.phase !== "finished";
    this.stats.hidden = !showStats;
    const live = state.mode === "live";
    this.pills.q.hidden = !(live && showStats);
    if (live && showStats) this.pills.q.textContent = `Q ${Math.max(0, (state.question_index ?? 0) + 1)}/${state.question_total || "?"}`;
    const timed = showStats && (state.phase === "question" || state.phase === "running");
    this.pills.time.hidden = !timed;
    this.bar.parentElement.hidden = !timed;
    this.pills.rank.lastChild.textContent = me.rank ? `#${me.rank}` : "-";
    const scoreNode = this.pills.score.lastChild;
    if (me.score !== this.score) {
      animateNumber(scoreNode, this.score, me.score || 0, 700);
      this.score = me.score || 0;
    } else if (!scoreNode.textContent || scoreNode.textContent === "0") scoreNode.textContent = fmtNum(this.score);
    const streak = me.streak || 0;
    this.pills.streak.hidden = streak < 2 || !showStats;
    this.pills.streak.lastChild.textContent = String(streak);
    this.pills.streak.setAttribute("aria-label", `${streak} correct in a row`);
  }

  setTimePill(remaining, total, { warnAt, urgentAt }) {
    const rem = Math.max(0, remaining);
    const text = formatTime(rem);
    const b = this.pills.time.lastChild;
    if (b.textContent !== text) b.textContent = text;
    this.pills.time.classList.toggle("is-warn", rem <= warnAt && rem > urgentAt);
    this.pills.time.classList.toggle("is-urgent", rem <= urgentAt);
    this.bar.style.transform = `scaleX(${total > 0 ? Math.min(1, rem / total) : 0})`;
    this.bar.parentElement.classList.toggle("is-warn", rem <= warnAt && rem > urgentAt);
    this.bar.parentElement.classList.toggle("is-urgent", rem <= urgentAt);
  }

  // -- ticking (countdowns, time-outs) -----------------------------------------------------------

  tick() {
    if (this.disposed) return;
    if (!this.root.isConnected) return this.dispose(); // the app moved on to another screen
    const st = this.state;
    if (!st) return;
    const now = Date.now();
    if (st.phase === "question" && this.deadline) {
      const rem = clock.remaining(this.deadline);
      this.setTimePill(rem, this.limit, { warnAt: Math.max(8, this.limit * 0.3), urgentAt: 5 });
      const qid = st.question && st.question.id;
      if (qid && this.key === `lq:${qid}`) {
        if (rem <= 10 && rem > 9.8 && !this.announced.has(`10:${qid}`)) (this.announced.add(`10:${qid}`), this.announce("10 seconds left"));
        if (rem <= 0.15 && !this.timeUp.has(qid)) this.liveTimeUp(qid, st.question);
      }
      // the server closes the question a second after the deadline: look right then
      if (rem < -0.9 && now - this.lastNudge > 700) {
        this.lastNudge = now;
        this.poller.nudge();
      }
    } else if (st.phase === "running" && st.ends_at) {
      const rem = clock.remaining(st.ends_at);
      const total = st.started_at ? st.ends_at - st.started_at : rem;
      this.setTimePill(rem, total, { warnAt: 60, urgentAt: 30 });
      if (rem <= 0) {
        if (this.key !== "timesup") this.rushTimeUp();
        if (now - this.lastNudge > 700) {
          this.lastNudge = now;
          this.poller.nudge();
        }
      }
    }
    if (this.cool) this.tickCooldown(now);
  }

  // -- drafts ---------------------------------------------------------------------------------------

  saveDraft(qid, resp) {
    if (resp === null || resp === undefined) return;
    this.pendingDraft = { qid, resp };
    window.clearTimeout(this.draftTimer);
    this.draftTimer = window.setTimeout(() => this.flushDraft(), 250);
  }

  flushDraft() {
    window.clearTimeout(this.draftTimer);
    if (!this.pendingDraft) return;
    const { qid, resp } = this.pendingDraft;
    this.pendingDraft = null;
    store.patch(this.code, qid, { draft: resp });
  }

  // -- screens: plumbing --------------------------------------------------------------------------------

  /** Switch the main area to screen `key`. The question view of `keepQid` survives. */
  enter(key, keepQid = null) {
    this.key = key;
    window.clearTimeout(this.waitTimer);
    this.cool = null;
    if (this.view && this.viewQid !== keepQid) this.dropView();
  }

  dropView() {
    if (this.view) {
      this.flushDraft();
      this.view.destroy();
    }
    this.view = null;
    this.viewQid = null;
  }

  focusHeading() {
    const h = this.main.querySelector("[data-autofocus]");
    if (h) {
      try {
        h.focus({ preventScroll: true });
      } catch {
        /* best effort */
      }
    }
  }

  /** Create the QuestionView for `q` with whatever was typed before (reload-safe). */
  makeView(q, { onSubmit, restore = true }) {
    const saved = store.get(this.code, q.id);
    const initial = restore ? validInitial(q, saved.sent !== undefined ? saved.sent : saved.draft) : undefined;
    const view = createQuestionView(q, {
      onSubmit,
      onRun: q.qtype === "code" ? (code) => this.runCode(q.id, code) : undefined,
      onChange: (resp) => this.saveDraft(q.id, resp),
      initial: q.qtype === "choice" ? undefined : initial,
      hotkeys: true,
      showMeta: true,
    });
    this.view = view;
    this.viewQid = q.id;
    return { view, saved, initial };
  }

  async runCode(qid, code) {
    try {
      return await this.session.run(qid, code);
    } catch (err) {
      if (this.fatalError(err)) return { status: "error", message: "The game is over.", cases: [] };
      return { status: "error", message: err.reason === "rate_limited" ? "You've run your code a lot. Try submitting instead." : errorText(err), cases: [] };
    }
  }

  showWaiting(text, key = "waiting") {
    if (this.key === key) {
      const p = this.main.querySelector(".pl-waiting-text");
      if (p && p.textContent !== text) p.textContent = text;
      return;
    }
    this.enter(key);
    this.main.replaceChildren(el("section", { class: "card pl-card pl-waiting pop-in" }, el("div", { class: "spinner", "aria-hidden": "true" }), el("p", { class: "pl-waiting-text", text })));
  }

  // -- lobby ------------------------------------------------------------------------------------------------

  showLobby(state) {
    if (this.key !== "lobby") {
      this.enter("lobby");
      const me = state.me || this.info;
      this.lobby = {
        count: el("p", { class: "pl-lobby-count" }),
        wait: el("p", { class: "pl-lobby-wait", "aria-live": "off" }),
      };
      this.main.replaceChildren(
        el(
          "section",
          { class: "card pl-card pl-lobby pop-in" },
          el("div", { class: "pl-lobby-blook" }, blook(me.avatar || this.info.avatar, { size: 104 })),
          el("h1", { class: "pl-h", tabindex: "-1", "data-autofocus": "", text: "You're in!" }),
          el("p", { class: "pl-lobby-name", text: me.name || this.info.name }),
          state.title ? el("p", { class: "pl-lobby-title", text: state.title }) : null,
          el("p", { class: "pl-lobby-mode" }, el("span", { class: "pl-chip", text: MODE_LABEL[state.mode] || "Game" })),
          this.lobby.count,
          this.lobby.wait,
          el("button", { class: "btn btn-white pl-lobby-leave", type: "button", text: "Leave game", onClick: () => this.leave() })
        )
      );
      this.cycleWait();
      this.focusHeading();
    }
    const n = state.players_total || 1;
    this.lobby.count.textContent = n === 1 ? "You're the only one here so far" : `${n} players are here`;
  }

  cycleWait() {
    if (this.key !== "lobby" || this.disposed) return;
    this.lobby.wait.textContent = `Watch the big screen. ${WAIT_LINES[this.waitIdx++ % WAIT_LINES.length]}`;
    this.waitTimer = window.setTimeout(() => this.cycleWait(), 4500);
  }

  // -- live quiz: question ------------------------------------------------------------------------------------

  showLiveQuestion(state) {
    const q = state.question;
    if (!q) return this.showWaiting("Waiting for the question…");
    this.deadline = state.deadline;
    this.limit = q.time_limit || Math.max(1, (state.deadline || 0) - clock.now());
    const key = `lq:${q.id}`;
    if (this.key !== key) {
      this.enter(key, q.id);
      const { view, saved } = this.view && this.viewQid === q.id ? { view: this.view, saved: {} } : this.makeView(q, { onSubmit: (resp) => this.onLiveSubmit(q, resp) });
      this.announced.delete(`10:${q.id}`);
      this.liveBanner = null;
      this.main.replaceChildren(el("div", { class: "pl-live-q" }, view.el));
      if (saved && saved.sent !== undefined && !this.sentLive.has(q.id)) {
        // reloaded after answering: do not let the student answer twice
        this.sentLive.add(q.id);
        view.lock();
        this.setLiveBanner(q.id, "locked");
      }
      if (!isCoarse()) view.focus();
      this.announce(`Question ${(state.question_index ?? 0) + 1}. ${q.prompt}`);
    }
    if (state.my_answer && state.my_answer.submitted && !this.sentLive.has(q.id)) {
      this.sentLive.add(q.id);
      this.view.lock();
      this.setLiveBanner(q.id, "locked");
    }
    if (this.sentLive.has(q.id) && this.view && !this.liveBanner) this.setLiveBanner(q.id, "locked");
  }

  /** The countdown ran out: send what is typed (once), or just lock if there is nothing. */
  liveTimeUp(qid, q) {
    this.timeUp.add(qid);
    const view = this.view;
    if (!view || this.viewQid !== qid) return;
    if (this.sentLive.has(qid)) return view.lock();
    if (isBlankResponse(q, view.getResponse())) {
      this.sentLive.add(qid);
      view.lock();
      this.setLiveBanner(qid, "none");
      return;
    }
    view.submit(); // -> onLiveSubmit
  }

  onLiveSubmit(q, response) {
    const qid = q.id;
    this.sentLive.add(qid);
    window.clearTimeout(this.draftTimer);
    this.pendingDraft = null;
    store.patch(this.code, qid, { sent: response, draft: response });
    this.setLiveBanner(qid, "sending");
    this.sendLive(qid, response);
  }

  async sendLive(qid, response) {
    for (let attempt = 0; ; attempt++) {
      if (this.disposed || !this.state || (this.key !== `lq:${qid}` && this.key !== `lr:${qid}`)) return;
      try {
        const res = await this.session.answer(qid, response);
        if (this.disposed) return;
        this.setOnline(true);
        this.setLiveBanner(qid, "locked");
        if (res && res.state) this.poller.push(res.state);
        return;
      } catch (err) {
        if (this.disposed) return;
        if (this.fatalError(err)) return;
        if (err.reason === "too_late") return this.setLiveBanner(qid, "late");
        if (err.reason === "bad_state") {
          this.setLiveBanner(qid, "locked"); // already answered (or the question moved on): the server knows
          this.poller.nudge();
          return;
        }
        // network trouble, rate limit or a server hiccup: keep trying while the question is still open
        if (this.deadline && clock.remaining(this.deadline) < -1.5) return this.setLiveBanner(qid, "late");
        this.setLiveBanner(qid, "retry");
        await sleep(Math.min(2500, 600 + attempt * 400));
      }
    }
  }

  setLiveBanner(qid, kind) {
    if (this.disposed || this.viewQid !== qid || !this.view || this.key !== `lq:${qid}`) return;
    const slot = this.view.feedbackSlot;
    const specs = {
      sending: ["pl-banner-wait", null, "Sending your answer…", ""],
      locked: ["pl-banner-ok", "✓", "Answer locked in", "Waiting for the others…"],
      none: ["pl-banner-late", "⏰", "Time's up!", "No answer this time. The right answer is coming up."],
      late: ["pl-banner-late", "⏰", "Too late!", "The question closed before your answer arrived."],
      retry: ["pl-banner-warn", "⚠️", "Couldn't send your answer", "Trying again…"],
    };
    const [cls, icon, title, sub] = specs[kind];
    if (this.liveBanner && this.liveBanner.kind === kind) return;
    const node = el(
      "div",
      { class: ["pl-banner", cls] },
      icon ? el("span", { class: "pl-banner-icon", "aria-hidden": "true", text: icon }) : el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }),
      el("div", { class: "pl-banner-text" }, el("strong", { text: title }), sub ? el("span", { text: sub }) : null)
    );
    slot.replaceChildren(node);
    this.liveBanner = { kind, node };
    if (kind !== "sending") sfx("click");
    window.setTimeout(() => {
      try {
        node.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch {
        /* ignore */
      }
    }, 60);
  }

  // -- live quiz: reveal ---------------------------------------------------------------------------------------

  showReveal(state) {
    const q = state.question;
    if (!q) return this.showWaiting("Getting the results…");
    const key = `lr:${q.id}`;
    const result = state.result;
    if (this.key !== key) {
      this.enter(key, q.id);
      let saved = {};
      if (!this.view || this.viewQid !== q.id) {
        const made = this.makeView(q, { onSubmit: () => {} });
        saved = made.saved;
        made.view.lock();
      } else saved = store.get(this.code, q.id);
      this.rv = {
        sig: "",
        summary: el("section", { class: "pl-summary", "aria-live": "polite" }),
        board: el("section", { class: "card pl-card pl-board" }),
        response: saved.sent,
        first: true,
      };
      this.main.replaceChildren(
        el("div", { class: "pl-reveal" }, this.rv.summary, this.view.el, this.rv.board, el("p", { class: "pl-wait-host", text: state.phase === "reveal" && state.question_index + 1 >= state.question_total ? "Waiting for the host to show the final results…" : "Waiting for the host to continue…" }))
      );
      this.main.querySelector(".pl-reveal").prepend();
    }
    const prev = store.rank(this.code, q.id, (state.me || {}).rank || 1);
    const sig = JSON.stringify([result, state.me && state.me.rank, state.leaderboard, state.reveal && state.reveal.correct_count]);
    if (sig === this.rv.sig) return;
    const firstTime = this.rv.first;
    this.rv.sig = sig;
    this.rv.first = false;

    const sent = this.rv.response;
    const pending = !result && this.sentLive.has(q.id) && sent !== undefined;
    const res = result
      ? { ...result, reveal: result.reveal || (state.reveal && state.reveal.answer) || {} }
      : { correct: false, answered: false, points: 0, reveal: (state.reveal && state.reveal.answer) || {}, detail: {}, explanation: (state.reveal && state.reveal.explanation) || "" };
    this.view.showResult(res, { response: sent });
    const explanation = res.explanation || (state.reveal && state.reveal.explanation) || "";
    this.view.feedbackSlot.replaceChildren(explanation ? el("div", { class: "pl-explain" }, el("strong", { text: "Why: " }), el("span", { html: renderInlineCode(explanation) })) : null);
    this.rv.summary.replaceChildren(...this.summaryNodes(res, state, prev, pending));
    this.rv.board.replaceChildren(...this.boardNodes(state, res));
    if (firstTime && !pending) {
      sfx(res.correct ? "correct" : "wrong");
      this.announce(res.correct ? `Correct! ${res.points} points.` : res.answered === false ? "No answer." : "Not quite.");
      this.view.el.classList.remove("pop-in");
    }
    if (firstTime) {
      window.scrollTo({ top: 0 });
      this.rv.summary.setAttribute("tabindex", "-1");
    }
  }

  /** The "+166 = 100 + 41 + 25" card shown on the reveal. */
  summaryNodes(res, state, prevRank, pending) {
    const me = state.me || {};
    const kind = pending ? "wait" : res.answered === false ? "none" : res.correct ? "ok" : "bad";
    const head = {
      wait: ["⏳", "Checking your answer…"],
      none: ["⏰", "No answer"],
      ok: ["🎉", "Correct!"],
      bad: ["😬", "Not quite"],
    }[kind];
    const marks = res.detail && (res.detail.blanks || res.detail.match);
    const partial =
      kind === "bad" && Array.isArray(marks) && marks.some(Boolean) ? `${marks.filter(Boolean).length} of ${marks.length} ${res.detail.blanks ? "blanks" : "matches"} right` : "";
    const parts = [];
    if (res.correct) {
      if (res.base_points) parts.push(["base", `${fmtNum(res.base_points)} correct`]);
      if (res.speed_points) parts.push(["speed", `+${fmtNum(res.speed_points)} speed`]);
      if (res.streak_points) parts.push(["streak", `+${fmtNum(res.streak_points)} streak`]);
    }
    const rankNow = me.rank || 1;
    let move = null;
    if (prevRank && prevRank !== rankNow) {
      const up = rankNow < prevRank;
      move = el("span", { class: ["pl-move", up ? "is-up" : "is-down"], "aria-label": up ? `up ${prevRank - rankNow}` : `down ${rankNow - prevRank}` }, up ? "▲" : "▼", ` ${Math.abs(prevRank - rankNow)}`);
    }
    const rv = state.reveal;
    return [
      el(
        "div",
        { class: ["card", "pl-card", "pl-sum", `is-${kind}`, "pop-in"] },
        el("div", { class: "pl-sum-head" }, el("span", { class: "pl-sum-icon", "aria-hidden": "true", text: head[0] }), el("h2", { class: "pl-sum-title", text: head[1] })),
        kind === "wait"
          ? el("div", { class: "spinner", "aria-hidden": "true" })
          : el("div", { class: "pl-sum-points" }, el("b", { class: "pl-sum-num", text: res.points > 0 ? `+${fmtNum(res.points)}` : "0" }), el("span", { text: res.points > 0 ? "points" : "No points this time" })),
        parts.length ? el("div", { class: "pl-parts" }, parts.map(([k, t]) => el("span", { class: `pl-part pl-part-${k}`, text: t }))) : null,
        partial ? el("p", { class: "pl-partial", text: partial }) : null,
        el(
          "div",
          { class: "pl-sum-foot" },
          res.correct && res.streak >= 2 ? el("span", { class: "pl-flame pulse", text: `🔥 ${res.streak} in a row` }) : null,
          el("span", { class: "pl-rank-line" }, "You're ", el("b", { text: ordinal(rankNow) }), me.score !== undefined ? ` · ${fmtNum(me.score)} pts` : "", move ? [" ", move] : null),
          rv && rv.answered_count !== undefined ? el("span", { class: "pl-gotit", text: `${rv.correct_count} of ${rv.answered_count} got it right` }) : null
        )
      ),
    ];
  }

  /** Top-5 leaderboard (plus my own row when I'm further down). */
  boardNodes(state, res) {
    const rows = state.leaderboard || [];
    const me = state.me || {};
    const nodes = [el("h2", { class: "pl-board-title" }, el("span", { "aria-hidden": "true", text: "🏆 " }), "Leaderboard")];
    const mkRow = (p, { me: mine = false, delta } = {}) =>
      el(
        "li",
        { class: ["pl-row", mine && "is-me"], "aria-current": mine ? "true" : null },
        el("span", { class: "pl-row-rank", text: String(p.rank) }),
        blook(p.avatar, { size: 32 }),
        el("span", { class: "pl-row-name", text: p.name }, mine ? el("em", { text: " (you)" }) : null),
        delta ? el("span", { class: "pl-row-delta", text: `+${fmtNum(delta)}` }) : null,
        el("b", { class: "pl-row-score", text: fmtNum(p.score) })
      );
    const list = el("ol", { class: "pl-rows" });
    const inTop = rows.some((p) => p.id === me.id);
    for (const p of rows) list.append(mkRow(p, { me: p.id === me.id, delta: p.delta }));
    if (!inTop && me.id) {
      list.append(el("li", { class: "pl-row-gap", "aria-hidden": "true", text: "⋮" }));
      list.append(mkRow({ ...me, rank: me.rank || 1 }, { me: true, delta: res.points }));
    }
    if (!rows.length && !me.id) list.append(el("li", { class: "pl-row", text: "No scores yet" }));
    nodes.push(list);
    return nodes;
  }

  // -- time rush ---------------------------------------------------------------------------------------------------

  showRush(state) {
    if (this.hold) {
      // my last answer's feedback is on screen: only the strip and header may change underneath it
      this.refreshStrip(state);
      return;
    }
    if (state.question) return this.showRushQuestion(state);
    if (state.cooldown_until && clock.remaining(state.cooldown_until) > 0) return this.showCooldown(state);
    this.showWaiting("Getting your next question…", "waiting-rush");
  }

  showRushQuestion(state) {
    const q = state.question;
    const key = `rq:${q.id}`;
    if (this.key === key) return this.refreshStrip(state);
    this.enter(key);
    const { view } = this.makeView(q, { onSubmit: (resp) => this.onRushSubmit(q, resp) });
    this.strip = el("section", { class: "pl-strip", "aria-label": "Top five players" });
    this.main.replaceChildren(el("div", { class: "pl-rush-q" }, view.el, this.strip));
    this.refreshStrip(state);
    if (!isCoarse()) view.focus();
    window.scrollTo({ top: 0 });
  }

  refreshStrip(state) {
    if (!this.strip || !this.strip.isConnected) return;
    const rows = state.leaderboard || [];
    const meId = (state.me || {}).id;
    const sig = JSON.stringify(rows.map((r) => [r.id, r.rank, r.score]));
    if (sig === this.stripSig) return;
    this.stripSig = sig;
    this.strip.replaceChildren(
      el("h2", { class: "pl-strip-title", text: "Top 5" }),
      el(
        "ol",
        { class: "pl-strip-list" },
        rows.map((p) =>
          el("li", { class: ["pl-strip-item", p.id === meId && "is-me"] }, el("b", { text: String(p.rank) }), blook(p.avatar, { size: 22 }), el("span", { class: "pl-strip-name", text: p.name }), el("span", { class: "pl-strip-score", text: fmtNum(p.score) }))
        )
      )
    );
  }

  onRushSubmit(q, response) {
    window.clearTimeout(this.draftTimer);
    this.pendingDraft = null;
    store.patch(this.code, q.id, { sent: response, draft: response });
    this.hold = { qid: q.id, q, response, phase: "sending", timer: 0 };
    this.setRushFeedback(el("div", { class: "pl-banner pl-banner-wait" }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), el("div", { class: "pl-banner-text" }, el("strong", { text: "Checking your answer…" }))));
    this.sendRush();
  }

  setRushFeedback(node) {
    if (this.view) this.view.feedbackSlot.replaceChildren(node);
    window.setTimeout(() => {
      try {
        node.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch {
        /* ignore */
      }
    }, 60);
  }

  async sendRush() {
    const hold = this.hold;
    if (!hold) return;
    const { qid, response } = hold;
    for (let attempt = 0; ; attempt++) {
      if (this.disposed || this.hold !== hold) return;
      try {
        const res = await this.session.answer(qid, response);
        if (this.disposed || this.hold !== hold) return;
        this.setOnline(true);
        hold.phase = "feedback";
        hold.state = res.state;
        this.showRushResult(res.result);
        if (res.state) this.poller.push(res.state);
        return;
      } catch (err) {
        if (this.disposed || this.hold !== hold) return;
        if (this.fatalError(err)) return;
        if (err.reason === "too_late") {
          this.clearHold();
          this.rushTimeUp();
          this.poller.nudge();
          return;
        }
        if (err.reason === "bad_state") return this.recoverRush(hold);
        if (attempt >= 8) {
          this.clearHold();
          toast("Couldn't send your answer. Check your connection.", "error");
          return;
        }
        this.setRushFeedback(el("div", { class: "pl-banner pl-banner-warn" }, el("span", { class: "pl-banner-icon", "aria-hidden": "true", text: "⚠️" }), el("div", { class: "pl-banner-text" }, el("strong", { text: "Couldn't send your answer" }), el("span", { text: "Trying again…" }))));
        await sleep(Math.min(2500, 600 + attempt * 500));
      }
    }
  }

  /** The server says my answer was already taken (e.g. a reply got lost): read the result from the state. */
  async recoverRush(hold) {
    try {
      const s = await this.session.state();
      if (this.disposed || this.hold !== hold) return;
      if (s.result && s.result.qid === hold.qid) {
        hold.phase = "feedback";
        this.showRushResult(s.result);
        this.poller.push(s);
        return;
      }
      this.clearHold();
      this.poller.push(s);
      this.render();
    } catch (err) {
      if (this.fatalError(err)) return;
      this.clearHold();
      this.poller.nudge();
    }
  }

  showRushResult(result) {
    const hold = this.hold;
    if (!hold || !this.view) return;
    const q = hold.q;
    this.view.showResult({ ...result, reveal: result.reveal || {} }, { response: hold.response });
    const typed = q.qtype !== "choice";
    const auto = result.correct ? (typed ? 2400 : 1300) : 0;
    const parts = [];
    if (result.correct) {
      if (result.base_points) parts.push(`${fmtNum(result.base_points)}`);
      if (result.streak_points) parts.push(`${fmtNum(result.streak_points)} streak`);
    }
    const marks = result.detail && (result.detail.blanks || result.detail.match);
    const partial = !result.correct && Array.isArray(marks) && marks.some(Boolean) ? `${marks.filter(Boolean).length} of ${marks.length} right` : "";
    const cont = el("button", { class: ["btn", result.correct ? "btn-green" : "btn-purple", "pl-continue"], type: "button", onClick: () => this.releaseHold() }, auto ? "Next ▶" : "Continue ▶");
    const node = el(
      "div",
      { class: ["pl-banner", result.correct ? "pl-banner-ok" : "pl-banner-bad", "pop-in"] },
      el("span", { class: "pl-banner-icon", "aria-hidden": "true", text: result.correct ? "🎉" : "😬" }),
      el(
        "div",
        { class: "pl-banner-text" },
        el("strong", { text: result.correct ? `Correct! +${fmtNum(result.points)}` : "Not quite" }),
        parts.length > 1 ? el("span", { text: `${parts.join(" + ")} = ${fmtNum(result.points)}` }) : null,
        partial ? el("span", { text: partial }) : null,
        result.correct && result.streak >= 2 ? el("span", { class: "pl-flame", text: `🔥 ${result.streak} in a row` }) : null,
        !result.correct ? el("span", { text: "Engine cooling down for a few seconds." }) : null
      ),
      result.explanation ? el("p", { class: "pl-explain", html: renderInlineCode(result.explanation) }) : null,
      el("div", { class: "pl-banner-actions" }, cont, auto ? el("span", { class: "pl-autobar", "aria-hidden": "true" }, el("i", { style: { animationDuration: `${auto}ms` } })) : null)
    );
    this.setRushFeedback(node);
    sfx(result.correct ? "correct" : "wrong");
    this.announce(result.correct ? `Correct! ${result.points} points.` : "Not quite.");
    if (!result.correct) this.view.el.classList.add("shake");
    window.setTimeout(() => cont.isConnected && cont.focus({ preventScroll: true }), 80);
    if (auto) hold.timer = window.setTimeout(() => this.releaseHold(), auto);
  }

  clearHold() {
    if (this.hold) window.clearTimeout(this.hold.timer);
    this.hold = null;
  }

  releaseHold() {
    const hold = this.hold;
    if (!hold || hold.phase !== "feedback") return;
    this.clearHold();
    this.stripSig = "";
    this.render();
  }

  showCooldown(state) {
    const until = state.cooldown_until;
    if (this.key === "cool" && this.cool) {
      this.cool.until = until;
      return;
    }
    this.enter("cool");
    const num = el("b", { class: "pl-cool-num", text: String(Math.ceil(Math.max(0, clock.remaining(until)))) });
    const fill = el("i", { class: "pl-cool-fill" });
    this.cool = { until, num, fill, last: 0 };
    this.main.replaceChildren(
      el(
        "section",
        { class: "card pl-card pl-cool pop-in" },
        el("div", { class: "pl-cool-icon", "aria-hidden": "true", text: "🧊" }),
        el("h2", { class: "pl-h", tabindex: "-1", "data-autofocus": "", text: "Engine cooling down…" }),
        num,
        el("div", { class: "pl-cool-bar", role: "progressbar", "aria-label": "Cooldown" }, fill),
        el("p", { class: "pl-cool-text", text: "Think about the last answer. The next question is on its way." })
      )
    );
    this.tickCooldown(Date.now());
  }

  tickCooldown(now) {
    const c = this.cool;
    if (!c) return;
    const rem = clock.remaining(c.until);
    c.fill.style.transform = `scaleX(${Math.max(0, Math.min(1, 1 - rem / RUSH_COOLDOWN))})`;
    const text = String(Math.max(0, Math.ceil(rem)));
    if (c.num.textContent !== text) c.num.textContent = text;
    if (rem <= 0 && now - c.last > 600) {
      c.last = now;
      this.poller.nudge();
    }
  }

  rushTimeUp() {
    this.clearHold();
    if (this.key === "timesup") return;
    this.enter("timesup");
    this.main.replaceChildren(
      el("section", { class: "card pl-card pl-waiting pop-in" }, el("div", { class: "pl-end-icon", "aria-hidden": "true", text: "⏰" }), el("h2", { class: "pl-h", tabindex: "-1", "data-autofocus": "", text: "Time's up!" }), el("p", { class: "pl-waiting-text", text: "Counting the scores…" }))
    );
    this.focusHeading();
    sfx("lose");
  }

  // -- finished -----------------------------------------------------------------------------------------------------

  showFinished(state) {
    if (this.key === "final") return;
    this.clearHold();
    this.enter("final");
    this.poller.stop();
    const me = state.me || {};
    const f = state.final || {
      rank: me.rank || 1,
      score: me.score || 0,
      correct: me.correct || 0,
      answered: me.answered || 0,
      avg_ms: 0,
      best_streak: 0,
      podium: [],
      players_total: state.players_total || 1,
    };
    const env = this.env;
    const podiumRank = f.rank <= 3 && f.score > 0;
    const medal = { 1: "🥇", 2: "🥈", 3: "🥉" }[f.rank] && f.score > 0 ? { 1: "🥇", 2: "🥈", 3: "🥉" }[f.rank] : "🎮";
    const headline = f.rank === 1 && f.score > 0 ? "You won!" : podiumRank ? `You finished ${ordinal(f.rank)}!` : "Game over";
    const acc = f.answered ? Math.round((f.correct / f.answered) * 100) : 0;
    const tile = (icon, value, label) =>
      el("div", { class: "pl-tile" }, el("span", { class: "pl-tile-icon", "aria-hidden": "true", text: icon }), el("b", { class: "pl-tile-value", text: value }), el("span", { class: "pl-tile-label", text: label }));

    // podium: 2nd, 1st, 3rd
    const byRank = [...(f.podium || [])].slice(0, 3);
    const order = byRank.length >= 3 ? [byRank[1], byRank[0], byRank[2]] : byRank.length === 2 ? [byRank[1], byRank[0]] : byRank;
    const podium = el(
      "ol",
      { class: "pl-podium", "aria-label": "Podium" },
      order.map((p, i) => {
        const place = Math.min(3, Math.max(1, p.rank || byRank.indexOf(p) + 1)); // tied players share a step
        const mine = p.name === me.name && p.score === me.score && p.rank === f.rank;
        return el(
          "li",
          { class: ["pl-pod", `pl-pod-${place}`, mine && "is-me"], style: { "--i": i } },
          blook(p.avatar, { size: place === 1 ? 64 : 52 }),
          el("span", { class: "pl-pod-name", text: p.name }),
          el("span", { class: "pl-pod-score", text: fmtNum(p.score) }),
          el("span", { class: "pl-pod-block" }, el("b", { text: String(place) }))
        );
      })
    );

    this.stats.hidden = true;
    this.main.replaceChildren(
      el(
        "section",
        { class: "pl-final" },
        el(
          "div",
          { class: "card pl-card pl-final-hero pop-in" },
          el("div", { class: "pl-medal", "aria-hidden": "true", text: medal }),
          el("h1", { class: "pl-h", tabindex: "-1", "data-autofocus": "", text: headline }),
          el("p", { class: "pl-final-rank" }, "You came ", el("b", { text: ordinal(f.rank) }), ` out of ${plural(f.players_total || 1, "player")}`),
          el("p", { class: "pl-final-score" }, el("b", { text: fmtNum(f.score) }), " points")
        ),
        el(
          "div",
          { class: "pl-tiles" },
          tile("✅", f.answered ? `${f.correct}/${f.answered}` : "0", f.answered ? `correct (${acc}%)` : "correct"),
          tile("🔥", String(f.best_streak || 0), "best streak"),
          tile("⚡", f.avg_ms ? `${(f.avg_ms / 1000).toFixed(1)}s` : "-", "avg. answer time")
        ),
        order.length ? el("div", { class: "card pl-card pl-podium-card" }, el("h2", { class: "pl-board-title" }, el("span", { "aria-hidden": "true", text: "🏆 " }), "Podium"), podium) : null,
        el(
          "div",
          { class: "pl-final-actions" },
          el("button", { class: "btn btn-green btn-lg", type: "button", text: "Play again", onClick: () => (this.dispose(), savedPlayer.clear(), store.clear(), renderJoin(env, {})) }),
          el("button", { class: "btn btn-white", type: "button", text: "Home", onClick: () => (this.dispose(), savedPlayer.clear(), store.clear(), env.goHome()) })
        )
      )
    );
    this.focusHeading();
    window.scrollTo({ top: 0 });
    if (podiumRank) {
      sfx("win");
      confetti({ count: f.rank === 1 ? 220 : 130 });
    } else sfx("levelup");
    this.announce(`${headline} You scored ${f.score} points.`);
  }
}
