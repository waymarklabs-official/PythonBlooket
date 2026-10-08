/**
 * Host screens: the TEACHER's side of a hosted game, built for a projector.
 *
 *   renderHost(env, {resume})
 *
 * Flow (the server owns the game, this file only shows it and sends the teacher's buttons):
 *   SETUP   pick Live Quiz or Time Rush, topics, difficulty, question types and the mode's options,
 *           then "Create game" (POST /api/host/games). A game remembered in this browser can be resumed.
 *   LOBBY   huge join code, join address(es) + QR code, the players as they arrive (kick, lock), Start.
 *   LIVE QUIZ   `question` (countdown, how many answered, the question for the room) -> `reveal`
 *           (right answer, who got it, top 5) -> Next ... -> `finished`.
 *   TIME RUSH   `running`: a giant clock and the live top-10 leaderboard, then `finished`.
 *   FINISHED    podium, full standings, hardest questions, CSV download, "host another game".
 *
 * Everything on screen comes from one object, the host state, which a Poller fetches about once a
 * second (hostapi.js). A HostGame owns the page shell (header, connection banner, stage) and swaps
 * *views* in and out of the stage. A view is `{el, update(state), tick(), primary(), destroy()}`:
 * update() patches the DOM in place when the state changes (no flicker while 60 players answer),
 * tick() runs every animation frame (countdowns), primary() is what Space/Enter should do.
 *
 * Keys: Space/Enter = the big button (Start, Skip, Next), F = fullscreen, M = mute, L = lock joining.
 * All text from players (names) goes through textContent, never innerHTML.
 */

import { hostCreate, hostLan, hostSession, Poller, clock, prettyCode, qrUrl, savedHost } from "./hostapi.js";
import {
  animateNumber,
  blook,
  confetti,
  confirmDialog,
  createMuteButton,
  el,
  formatTime,
  highlightPython,
  isModalOpen,
  prefersReducedMotion,
  renderInlineCode,
  sfx,
  storageGet,
  storageSet,
  toast,
} from "./ui.js";

const SETUP_KEY = "pyblooket.hostsetup";
const TITLE_MAX = 40;
const DEFAULT_MAX_PLAYERS = 60;
const KEY_GUARD_MS = 600; // ignore Space/Enter right after a screen change (a held key must not skip twice)
const RUSH_ROWS = 10;
const WALL_LIMIT = 80;

const MODE_INFO = {
  live: {
    id: "live",
    icon: "🎤",
    name: "Live Quiz",
    color: "#2f8cff",
    blurb: "Everyone answers the same question together — fastest correct answers win.",
  },
  rush: {
    id: "rush",
    icon: "🏁",
    name: "Time Rush",
    color: "#ff8a1f",
    blurb: "Race through questions at your own pace until the clock runs out.",
  },
};

const TYPE_CHOICES = [
  {
    id: "mixed",
    icon: "🎲",
    label: "Mixed",
    sub: (code) => (code ? "choice + typing" : "choice + blanks"),
    blurb: (code) => (code ? "Multiple choice plus fill-in-the-blanks and coding." : "Multiple choice plus fill-in-the-blanks."),
  },
  { id: "choice", icon: "👆", label: "Multiple choice", sub: () => "tap an answer", blurb: () => "Pick the right answer or match things up. No typing." },
  {
    id: "typing",
    icon: "⌨️",
    label: "Typing",
    sub: (code) => (code ? "blanks + code" : "fill the blanks"),
    blurb: (code) => (code ? "Fill in the blanks and write real code." : "Fill in the blanks."),
  },
];
const TYPE_IDS = TYPE_CHOICES.map((c) => c.id);

const DIFFICULTY_CHOICES = [
  { id: 1, label: "Easy", stars: "★", points: "100 pts" },
  { id: 2, label: "Medium", stars: "★★", points: "250 pts" },
  { id: 3, label: "Hard", stars: "★★★", points: "500 pts" },
  { id: "mixed", label: "Mixed", stars: "🎲", points: "100–500" },
];

const COUNT_CHOICES = [10, 15, 20, 30];
const DURATION_CHOICES = [3, 5, 10, 15];
const TIME_SCALES = [
  { id: "short", label: "Short", sub: "15–20 s" },
  { id: "normal", label: "Normal", sub: "15–25 s" },
  { id: "long", label: "Long", sub: "25–40 s" },
];

const CHOICE_CLASSES = ["hs-c0", "hs-c1", "hs-c2", "hs-c3"]; // yellow, blue, green, red (like the players' buttons)
const QTYPE_LABEL = { choice: "Multiple choice", blanks: "Fill in the blanks", match: "Matching", code: "Write the code" };
const QTYPE_ICON = { choice: "👆", blanks: "✍️", match: "🔗", code: "⌨️" };
const DIFF_STARS = { 1: "★", 2: "★★", 3: "★★★" };
const MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

/** The one host session on screen (a new renderHost() ends the old one). */
let current = null;

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

const fmt = (n) => Number(n || 0).toLocaleString();
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const pct = (num, den) => (den > 0 ? Math.round((100 * num) / den) : 0);
/** A medal for the top three, but not when nobody has scored yet (everybody would be "first"). */
const rankLabel = (p) => (p.score > 0 && MEDALS[p.rank]) || String(p.rank);
const plural = (n, one, many = `${one}s`) => `${fmt(n)} ${n === 1 ? one : many}`;

/** An avatar circle whose size scales with the projector font size (k = multiples of the base unit). */
function hsBlook(avatar, k = 2.4) {
  const node = blook(avatar, { className: "hs-blook" });
  node.style.setProperty("--blook-size", `calc(var(--hs-u) * ${k})`);
  return node;
}

/** "http://192.168.1.7:8000/?join=483920" -> "192.168.1.7:8000". */
function shortUrl(url) {
  try {
    return new URL(url).host;
  } catch {
    return String(url).replace(/^https?:\/\//, "").replace(/[/?#].*$/, "");
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    /* fall through to the old way (http pages have no clipboard API) */
  }
  const area = el("textarea", { class: "sr-only", "aria-hidden": "true", readonly: true, value: text });
  document.body.append(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  area.remove();
  return ok;
}

const fullscreenSupported = () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);

function toggleFullscreen() {
  try {
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    } else {
      const root = document.documentElement;
      const p = (root.requestFullscreen || root.webkitRequestFullscreen).call(root);
      if (p && p.catch) p.catch(() => toast("Your browser didn't allow fullscreen.", "warn"));
    }
  } catch {
    toast("Your browser didn't allow fullscreen.", "warn");
  }
}

function syncFullscreenButtons() {
  const on = !!(document.fullscreenElement || document.webkitFullscreenElement);
  for (const btn of document.querySelectorAll(".hs-fs-btn")) {
    btn.setAttribute("aria-pressed", String(on));
    btn.querySelector(".hs-fs-label").textContent = on ? "Exit fullscreen" : "Fullscreen";
    btn.querySelector(".hs-fs-icon").textContent = on ? "🡼" : "⛶";
  }
}

/** Disable a button while a promise runs. */
async function whileBusy(btn, promise) {
  if (btn) btn.disabled = true;
  try {
    return await promise;
  } finally {
    if (btn && btn.isConnected) btn.disabled = false;
  }
}

function friendly(err) {
  if (!err) return "Something went wrong.";
  if (err.reason === "network") return "Can't reach the server. Check the connection and try again.";
  return err.message || "Something went wrong.";
}

function kbd(text) {
  return el("kbd", { class: "hs-kbd only-mouse", "aria-hidden": "true", text });
}

/** Shrink the text inside `box` a step at a time (never below `min` x) until it no longer has to scroll. */
function fitBox(box, min = 0.7) {
  if (!box || !box.isConnected) return;
  box.style.removeProperty("font-size");
  let scale = 1;
  while (box.scrollHeight > box.clientHeight + 1 && scale > min) {
    scale = Math.max(min, scale - 0.05);
    box.style.fontSize = `${scale}em`;
  }
}

// ---------------------------------------------------------------------------
// Setup (remembered in localStorage)
// ---------------------------------------------------------------------------

function loadSetup() {
  const raw = storageGet(SETUP_KEY, {});
  const s = raw && typeof raw === "object" ? raw : {};
  const mp = Number.parseInt(s.maxPlayers, 10);
  return {
    mode: s.mode === "rush" ? "rush" : "live",
    title: typeof s.title === "string" ? s.title.slice(0, TITLE_MAX) : "",
    topics: Array.isArray(s.topics) ? s.topics.filter((t) => typeof t === "string") : null, // null = every lesson topic
    types: TYPE_IDS.includes(s.types) ? s.types : "mixed",
    difficulty: [1, 2, 3, "mixed"].includes(s.difficulty) ? s.difficulty : "mixed",
    count: COUNT_CHOICES.includes(s.count) ? s.count : 10,
    timeScale: TIME_SCALES.some((t) => t.id === s.timeScale) ? s.timeScale : "normal",
    auto: s.auto === true,
    duration: DURATION_CHOICES.includes(s.duration) ? s.duration : 5,
    maxPlayers: Number.isFinite(mp) ? clamp(mp, 1, 200) : DEFAULT_MAX_PLAYERS,
  };
}

const saveSetup = (d) => storageSet(SETUP_KEY, { ...d, topics: d.topics ? [...d.topics] : null });

/** Lesson topics (sorted by lesson tag) and extras, like the solo setup screen. */
function topicGroups(catalog) {
  const topics = catalog?.topics || [];
  let lessons = topics.filter((t) => t.group !== "extra").sort((a, b) => String(a.lesson).localeCompare(String(b.lesson), undefined, { numeric: true }));
  let extras = topics.filter((t) => t.group === "extra");
  if (!lessons.length) [lessons, extras] = [extras, []];
  return { lessons, extras };
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

export function renderHost(env, { resume } = {}) {
  if (current) {
    current.dispose();
    current = null;
  }
  if (resume) {
    const saved = savedHost.get();
    if (saved) return resumeSaved(env, saved);
  }
  return renderSetup(env);
}

/** Open a HostGame from a created/resumed game. */
function openGame(env, info) {
  if (current) current.dispose();
  current = new HostGame(env, info);
  current.start();
  return current;
}

/** The join addresses for a game: the server's LAN urls, else this page's own address. */
function joinUrlsFor(code, urls, path) {
  const rel = path || `/?join=${code}`;
  const list = (urls || []).filter((u) => typeof u === "string" && u);
  return list.length ? list : [`${location.origin}${rel}`];
}

async function resumeSaved(env, saved) {
  env.show(
    el(
      "div",
      { class: "screen hs-center-screen" },
      el("div", { class: "hs-center-card card" }, el("div", { class: "spinner", "aria-hidden": "true" }), el("h1", { class: "hs-center-title", text: "Reconnecting to your game…" }))
    ),
    { focus: false }
  );
  const api = hostSession(saved.code, saved.token);
  try {
    const [state, lan] = await Promise.all([api.state(), hostLan().catch(() => null)]);
    const path = `/?join=${saved.code}`;
    openGame(env, {
      code: saved.code,
      token: saved.token,
      state,
      lan: lan ? !!lan.lan : false,
      joinUrls: joinUrlsFor(saved.code, lan && lan.urls ? lan.urls.map((u) => u + path) : [], path),
    });
  } catch (err) {
    if (err && (err.reason === "not_found" || err.reason === "bad_token")) {
      savedHost.clear();
      renderSetup(env, { notice: "Your last game isn't running any more (the server was restarted or the game expired). Let's start a new one." });
      return;
    }
    env.show(
      el(
        "div",
        { class: "screen hs-center-screen" },
        el(
          "div",
          { class: "hs-center-card card" },
          el("div", { class: "hs-center-icon", "aria-hidden": "true", text: "📡" }),
          el("h1", { class: "hs-center-title", text: "Can't reach the game" }),
          el("p", { class: "hs-center-text", text: friendly(err) }),
          el(
            "div",
            { class: "hs-center-actions" },
            el("button", { class: "btn btn-green", type: "button", text: "Try again", onClick: () => resumeSaved(env, saved) }),
            el("button", { class: "btn btn-white", type: "button", text: "Home", onClick: () => env.goHome() })
          )
        )
      )
    );
  }
}

// ---------------------------------------------------------------------------
// SETUP screen
// ---------------------------------------------------------------------------

function renderSetup(env, { notice = "" } = {}) {
  const d = loadSetup();
  let catalog = null;
  let creating = false;
  const { backButton, segmented } = env;

  // ---- resume card (only when the remembered game is still alive) --------------------------
  const resumeSlot = el("div", { class: "hs-resume-slot" });
  const saved = savedHost.get();
  if (saved) {
    hostSession(saved.code, saved.token)
      .state()
      .then(
        (state) => {
          if (!resumeSlot.isConnected) return;
          const label = state.phase === "finished" ? "View results" : state.phase === "lobby" ? "Resume lobby" : "Resume game";
          resumeSlot.replaceChildren(
            el(
              "section",
              { class: "card hs-resume pop-in" },
              el("span", { class: "hs-resume-icon", "aria-hidden": "true", text: MODE_INFO[state.mode]?.icon || "🎮" }),
              el(
                "div",
                { class: "hs-resume-text" },
                el("strong", { text: state.title || `${MODE_INFO[state.mode]?.name || "Game"} in progress` }),
                el("span", { text: `Code ${prettyCode(state.code)} · ${plural(state.players.length, "player")} · ${state.phase === "finished" ? "finished" : state.phase === "lobby" ? "waiting in the lobby" : "playing now"}` })
              ),
              el("button", { class: "btn btn-green", type: "button", onClick: () => renderHost(env, { resume: true }) }, `${label} `, el("b", { text: prettyCode(state.code) }))
            )
          );
        },
        (err) => {
          if (err && (err.reason === "not_found" || err.reason === "bad_token")) savedHost.clear();
        }
      );
  }

  // ---- mode ------------------------------------------------------------------------------
  const modeButtons = Object.values(MODE_INFO).map((m) =>
    el(
      "button",
      {
        class: "hs-modecard",
        type: "button",
        style: { "--mode-color": m.color },
        dataset: { mode: m.id },
        "aria-pressed": String(d.mode === m.id),
        onClick: () => {
          d.mode = m.id;
          sfx("click");
          refreshMode();
        },
      },
      el("span", { class: "hs-modecard-icon", "aria-hidden": "true", text: m.icon }),
      el("span", { class: "hs-modecard-text" }, el("span", { class: "hs-modecard-name", text: m.name }), el("span", { class: "hs-modecard-blurb", text: m.blurb })),
      el("span", { class: "hs-modecard-check", "aria-hidden": "true", text: "✓" })
    )
  );
  const modeCard = el("section", { class: "card setup-card" }, el("h2", { class: "card-title", text: "Game mode" }), el("div", { class: "hs-modecards", role: "group", "aria-label": "Game mode" }, modeButtons));

  // ---- options (depend on the mode) ------------------------------------------------------
  const optionsTitle = el("h2", { class: "card-title" });
  const optionsBody = el("div", { class: "hs-options-body" });
  const optionsCard = el("section", { class: "card setup-card" }, optionsTitle, optionsBody);

  function optionRow(label, control, hint) {
    return el("div", { class: "option-row" }, el("h3", { class: "option-label", text: label }), control, hint ? el("p", { class: "hint", text: hint }) : null);
  }

  function switchControl() {
    const input = el("input", {
      type: "checkbox",
      role: "switch",
      id: "hs-auto",
      checked: d.auto,
      onChange: (e) => {
        d.auto = e.target.checked;
        sfx("click");
      },
    });
    return el(
      "label",
      { class: "hs-switch", for: "hs-auto" },
      input,
      el("span", { class: "hs-switch-track", "aria-hidden": "true" }, el("span", { class: "hs-switch-knob" })),
      el("span", { class: "hs-switch-text" }, el("b", { text: "Auto-advance" }), el("span", { text: "Continue by itself 10 seconds after each answer reveal" }))
    );
  }

  function fillOptions() {
    if (d.mode === "live") {
      optionsTitle.textContent = "Live Quiz options";
      optionsBody.replaceChildren(
        optionRow(
          "Questions",
          segmented({
            label: "Number of questions",
            value: d.count,
            choices: COUNT_CHOICES.map((n) => ({ value: n, content: el("span", { class: "seg-label", text: String(n) }) })),
            onChange: (v) => (d.count = v),
          })
        ),
        optionRow(
          "Time per question",
          segmented({
            label: "Time per question",
            value: d.timeScale,
            choices: TIME_SCALES.map((t) => ({ value: t.id, content: [el("span", { class: "seg-label", text: t.label }), el("span", { class: "seg-sub", text: t.sub })] })),
            onChange: (v) => (d.timeScale = v),
          }),
          "Times shown are for multiple choice. Fill-in-the-blanks and coding questions get extra time automatically."
        ),
        el("div", { class: "option-row" }, switchControl())
      );
    } else {
      optionsTitle.textContent = "Time Rush options";
      optionsBody.replaceChildren(
        optionRow(
          "Game length",
          segmented({
            label: "Game length in minutes",
            value: d.duration,
            choices: DURATION_CHOICES.map((n) => ({ value: n, content: [el("span", { class: "seg-label", text: String(n) }), el("span", { class: "seg-sub", text: "minutes" })] })),
            onChange: (v) => (d.duration = v),
          }),
          "Every player gets their own questions. After a wrong answer they wait 3 seconds."
        )
      );
    }
  }

  function refreshMode() {
    for (const b of modeButtons) b.setAttribute("aria-pressed", String(b.dataset.mode === d.mode));
    fillOptions();
  }

  // ---- details ---------------------------------------------------------------------------
  const titleInput = el("input", {
    class: "text-input",
    id: "hs-title",
    type: "text",
    maxlength: String(TITLE_MAX),
    placeholder: "e.g. Period 3 review",
    autocomplete: "off",
    value: d.title,
    onInput: (e) => (d.title = e.target.value.slice(0, TITLE_MAX)),
  });
  const maxInput = el("input", {
    class: "text-input hs-number",
    id: "hs-max",
    type: "number",
    inputmode: "numeric",
    min: "1",
    max: "200",
    value: String(d.maxPlayers),
    onInput: (e) => {
      const n = Number.parseInt(e.target.value, 10);
      if (Number.isFinite(n)) d.maxPlayers = clamp(n, 1, 200);
    },
    onBlur: (e) => (e.target.value = String(d.maxPlayers)),
  });
  const detailsCard = el(
    "section",
    { class: "card setup-card" },
    el("h2", { class: "card-title", text: "Game details" }),
    el("div", { class: "field" }, el("label", { for: "hs-title", text: "Game title (optional)" }), titleInput),
    el("div", { class: "field hs-field-gap" }, el("label", { for: "hs-max", text: "Max players" }), maxInput)
  );

  // ---- topics ----------------------------------------------------------------------------
  const topicCount = el("span", { class: "count-pill" });
  const lessonGrid = el("div", { class: "chip-grid", role: "group", "aria-label": "Unit 2 lesson topics" });
  const extraGrid = el("div", { class: "chip-grid", role: "group", "aria-label": "Extra challenge topics" });
  const extraCount = el("span", { class: "count-pill" });
  const extraBox = el(
    "details",
    { class: "topic-extras", hidden: true },
    el("summary", { class: "topic-extras-summary" }, el("span", { class: "topic-extras-label", text: "More challenge (beyond the lessons)" }), extraCount),
    extraGrid
  );
  const lessonHeading = el("h3", { class: "topic-group-title", text: "Unit 2 lessons" });
  const topicHint = el("p", { class: "hint hint-error", role: "alert", hidden: true, text: "Pick at least one topic." });
  const allBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "All", title: "Select every lesson topic", onClick: () => setTopics(lessonIds) });
  const noneBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "None", title: "Clear the selection", onClick: () => setTopics([]) });
  const extrasBtn = el("button", { class: "btn btn-sm btn-white btn-toggle", type: "button", text: "+ extras", "aria-pressed": "false", hidden: true, onClick: () => toggleExtras() });
  const topicsCard = el(
    "section",
    { class: "card setup-card" },
    el("div", { class: "card-head" }, el("h2", { class: "card-title" }, "Topics ", topicCount), el("div", { class: "card-head-actions" }, allBtn, noneBtn, extrasBtn)),
    lessonHeading,
    lessonGrid,
    extraBox,
    topicHint
  );
  let chips = [];
  let lessonIds = [];
  let extraIds = [];
  let picked = new Set();

  function refreshTopics() {
    topicCount.textContent = `${picked.size} selected`;
    for (const b of chips) b.setAttribute("aria-pressed", String(picked.has(b.dataset.topic)));
    const pickedExtras = extraIds.filter((id) => picked.has(id)).length;
    extraCount.textContent = `${pickedExtras}/${extraIds.length}`;
    extrasBtn.setAttribute("aria-pressed", String(extraIds.length > 0 && pickedExtras === extraIds.length));
    const ok = picked.size > 0;
    topicHint.hidden = ok || !catalog;
    createBtn.disabled = !ok || creating;
    createBtn.title = ok ? "" : "Pick at least one topic";
  }

  function setTopics(ids) {
    picked = new Set(ids);
    sfx("click");
    refreshTopics();
  }

  function toggleExtras() {
    const allOn = extraIds.every((id) => picked.has(id));
    for (const id of extraIds) allOn ? picked.delete(id) : picked.add(id);
    if (!allOn) extraBox.open = true;
    sfx("click");
    refreshTopics();
  }

  function topicChip(t) {
    return el(
      "button",
      {
        class: "chip",
        type: "button",
        dataset: { topic: t.id },
        title: t.description,
        "aria-pressed": "false",
        onClick: () => {
          picked.has(t.id) ? picked.delete(t.id) : picked.add(t.id);
          sfx("click");
          refreshTopics();
        },
      },
      el("span", { class: "chip-icon", "aria-hidden": "true", text: t.icon }),
      el("span", { class: "chip-name", text: t.name }),
      t.lesson ? el("span", { class: "chip-lesson", text: t.lesson }) : null,
      el("span", { class: "chip-check", "aria-hidden": "true", text: "✓" })
    );
  }

  function fillTopics() {
    const groups = topicGroups(catalog);
    lessonIds = groups.lessons.map((t) => t.id);
    extraIds = groups.extras.map((t) => t.id);
    const all = [...lessonIds, ...extraIds];
    const keep = (d.topics || []).filter((id) => all.includes(id));
    picked = new Set(keep.length ? keep : lessonIds);
    const lessonChips = groups.lessons.map(topicChip);
    const extraChips = groups.extras.map(topicChip);
    chips = [...lessonChips, ...extraChips];
    lessonGrid.replaceChildren(...lessonChips);
    extraGrid.replaceChildren(...extraChips);
    extraBox.hidden = extrasBtn.hidden = extraIds.length === 0;
    extraBox.open = extraIds.some((id) => picked.has(id));
    allBtn.disabled = noneBtn.disabled = false;
    refreshTopics();
  }

  function topicsLoading() {
    allBtn.disabled = noneBtn.disabled = true;
    lessonGrid.replaceChildren(el("div", { class: "loading-inline" }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), "Loading topics…"));
  }

  function topicsFailed(err) {
    lessonGrid.replaceChildren(
      el(
        "div",
        { class: "load-error" },
        el("p", { text: `😵 Couldn't load topics: ${err?.message || "network error"}` }),
        el("button", { class: "btn btn-sm btn-yellow", type: "button", text: "Try again", onClick: () => load() })
      )
    );
  }

  // ---- question types + difficulty ----------------------------------------------------------
  const typesBody = el("div", { class: "types-body" });
  const typesBlurb = el("p", { class: "hint types-blurb", "aria-live": "polite" });
  const typesCard = el("section", { class: "card setup-card" }, el("h2", { class: "card-title", text: "Question types" }), typesBody);

  function fillTypes() {
    const code = catalog ? catalog.code_enabled !== false : true;
    const blurb = () => {
      typesBlurb.textContent = `${TYPE_CHOICES.find((c) => c.id === d.types).blurb(code)}${d.types === "choice" ? "" : " Typed answers get more time."}`;
    };
    typesBody.replaceChildren(
      segmented({
        label: "Question types",
        className: "seg-types",
        value: d.types,
        choices: TYPE_CHOICES.map((c) => ({
          value: c.id,
          content: [el("span", { class: "seg-icon", "aria-hidden": "true", text: c.icon }), el("span", { class: "seg-label", text: c.label }), el("span", { class: "seg-sub", text: c.sub(code) })],
        })),
        onChange: (v) => {
          d.types = v;
          blurb();
        },
      }),
      typesBlurb
    );
    blurb();
  }

  const difficultyCard = el(
    "section",
    { class: "card setup-card" },
    el("h2", { class: "card-title", text: "Difficulty" }),
    segmented({
      label: "Difficulty",
      className: "seg-difficulty",
      value: d.difficulty,
      choices: DIFFICULTY_CHOICES.map((x) => ({
        value: x.id,
        className: `seg-diff-${x.id}`,
        content: [el("span", { class: "seg-stars", "aria-hidden": "true", text: x.stars }), el("span", { class: "seg-label", text: x.label }), el("span", { class: "seg-sub", text: x.points })],
      })),
      onChange: (v) => (d.difficulty = v),
    }),
    el("p", { class: "hint", text: "Harder questions are worth more points." })
  );

  // ---- create ------------------------------------------------------------------------------
  const errorBox = el("p", { class: "hint hint-warn hs-create-error", role: "alert", hidden: true });
  const createBtn = el(
    "button",
    {
      class: "btn btn-green btn-xl start-btn",
      type: "button",
      disabled: true,
      onClick: () => create(),
    },
    "Create game ",
    el("span", { "aria-hidden": "true", text: "▶" })
  );

  async function create() {
    if (creating || !catalog || picked.size === 0) return;
    creating = true;
    createBtn.disabled = true;
    errorBox.hidden = true;
    d.topics = [...picked];
    saveSetup(d);
    const ordered = [...lessonIds, ...extraIds].filter((id) => picked.has(id));
    const payload = {
      mode: d.mode,
      title: d.title.trim(),
      topics: ordered,
      difficulty: d.difficulty,
      types: d.types,
      max_players: d.maxPlayers,
    };
    if (d.mode === "live") Object.assign(payload, { question_count: d.count, time_scale: d.timeScale, auto_advance: d.auto });
    else payload.duration_min = d.duration;
    createBtn.firstChild.textContent = "Creating… ";
    try {
      const made = await hostCreate(payload);
      savedHost.set(made.code, made.host_token, made.game?.title || d.title.trim());
      sfx("levelup");
      openGame(env, {
        code: made.code,
        token: made.host_token,
        state: made.game,
        lan: !!made.lan,
        joinUrls: joinUrlsFor(made.code, made.join_urls, made.join_url_path),
      });
    } catch (err) {
      creating = false;
      createBtn.firstChild.textContent = "Create game ";
      errorBox.textContent = `Couldn't create the game: ${friendly(err)}`;
      errorBox.hidden = false;
      refreshTopics();
    }
  }

  // ---- assemble ----------------------------------------------------------------------------
  const screen = el(
    "div",
    { class: "screen setup-screen hs-setup" },
    el(
      "header",
      { class: "screen-header" },
      backButton("Back", () => {
        saveSetup({ ...d, topics: picked.size ? [...picked] : d.topics });
        env.goHome();
      }),
      el("h1", { class: "screen-title" }, el("span", { class: "title-icon", "aria-hidden": "true", text: "🎮" }), "Host a game"),
      createMuteButton()
    ),
    el("p", { class: "screen-sub", text: "Run a live Python quiz for your class. Students join from their own phones or laptops with a code." }),
    notice ? el("p", { class: "hint hint-warn hs-notice", role: "status", text: notice }) : null,
    resumeSlot,
    el("div", { class: "setup-grid hs-setup-grid" }, el("div", { class: "setup-col" }, modeCard, optionsCard, detailsCard), el("div", { class: "setup-col" }, topicsCard, typesCard, difficultyCard)),
    el("div", { class: "setup-footer" }, el("div", { class: "hs-footer-stack" }, errorBox, createBtn))
  );
  env.show(screen);
  refreshMode();
  topicsLoading();
  fillTypes();

  function load() {
    topicsLoading();
    env.loadCatalog().then(
      (c) => {
        if (!screen.isConnected) return;
        catalog = c;
        fillTopics();
        fillTypes();
      },
      (err) => screen.isConnected && topicsFailed(err)
    );
  }
  load();
}

// ---------------------------------------------------------------------------
// Question rendering for the room (no inputs: the host only shows it)
// ---------------------------------------------------------------------------

/** Turn `template` (code with ⟦n⟧ markers) into a fragment: highlight it whole, then swap in `makePiece(n)` per marker. */
function renderTemplate(template, makePiece) {
  const PH = ["`", "$", "?", "\u0001"].find((c) => !template.includes(c));
  const order = [];
  const text = template.replace(/⟦(\d+)⟧/g, (_, n) => {
    order.push(Number(n));
    return PH;
  });
  const tpl = document.createElement("template");
  tpl.innerHTML = highlightPython(text); // safe: highlightPython escapes everything
  const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_TEXT);
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);
  let k = 0;
  for (const node of texts) {
    if (!node.nodeValue.includes(PH)) continue;
    const parts = node.nodeValue.split(PH);
    const frag = document.createDocumentFragment();
    parts.forEach((part, i) => {
      if (part) frag.append(part);
      if (i < parts.length - 1) frag.append(makePiece(order[k++]));
    });
    node.replaceWith(frag);
  }
  return tpl.content;
}

/**
 * A code block with line numbers. When `q.blanks` exist the ⟦n⟧ markers become empty boxes
 * (with the blank's hint) or, when `answers` is given, the right text.
 */
function codeView(code, { blanks = null, answers = null } = {}) {
  const text = String(code ?? "").replace(/\s+$/, "");
  const lines = text.split("\n").length;
  const gutter = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  const body = el("code");
  if (/⟦\d+⟧/.test(text)) {
    body.append(
      renderTemplate(text, (n) => {
        const idx = blanks ? blanks.findIndex((b) => b.id === n) : -1;
        const info = idx >= 0 ? blanks[idx] : null;
        if (answers && idx >= 0 && answers[idx] !== undefined) return el("span", { class: "hs-blank hs-blank-filled", text: answers[idx] });
        return el("span", { class: "hs-blank", style: { "--w": info ? clamp(info.width || 4, 3, 24) : 5 }, text: info?.hint || `#${n}` });
      })
    );
  } else {
    body.innerHTML = highlightPython(text);
  }
  const longest = Math.max(...text.split("\n").map((l) => l.length));
  return el(
    "div",
    { class: ["code-block", "hs-code", lines <= 7 && longest <= 46 && "hs-code-lg"] },
    el("pre", { class: "code-gutter", "aria-hidden": "true", text: gutter }),
    el("pre", { class: "code-body", tabindex: "0" }, body)
  );
}

function promptNode(q) {
  const len = String(q.prompt || "").length;
  const size = len <= 60 ? "xl" : len <= 140 ? "lg" : "md";
  return el("div", { class: ["hs-prompt", `hs-prompt-${size}`], html: renderInlineCode(q.prompt) });
}

function metaRow(q, extra = []) {
  return el(
    "div",
    { class: "hs-qmeta" },
    el("span", { class: "topic-chip" }, el("span", { "aria-hidden": "true", text: q.topic_icon || "📚" }), ` ${q.topic_name || q.topic}`),
    el("span", { class: "hs-qtype-chip" }, el("span", { "aria-hidden": "true", text: QTYPE_ICON[q.qtype] || "" }), ` ${QTYPE_LABEL[q.qtype] || q.qtype}`),
    el("span", { class: `diff-badge diff-${q.difficulty}`, title: `${q.difficulty_label} question` }, el("span", { class: "diff-stars", "aria-hidden": "true", text: DIFF_STARS[q.difficulty] || "★" }), el("span", { text: `${q.difficulty_label} · ${q.points}` })),
    extra
  );
}

/** The left half of the question screens: prompt + (code | blanks template). */
function questionBody(q, { answers = null } = {}) {
  const parts = [promptNode(q)];
  if (q.code) parts.push(codeView(q.code, { blanks: q.blanks, answers }));
  else if (q.qtype === "code" && q.task?.starter) parts.push(codeView(q.task.starter));
  return el("div", { class: "hs-qbody" }, parts);
}

function exampleRows(task) {
  const rows = (task?.examples || []).map((ex) =>
    el(
      "li",
      { class: "hs-example" },
      ex.stdin && ex.stdin.length && !/^\s*input/i.test(ex.label) ? el("span", { class: "hs-example-in", text: `input: ${ex.stdin.join(" · ")}` }) : null,
      el("code", { class: "hs-example-label", text: ex.label }),
      el("span", { class: "hs-example-arrow", "aria-hidden": "true", text: "→" }),
      el("code", { class: "hs-example-expected", text: ex.expected })
    )
  );
  return rows;
}

/** The right half while the question is open: what the players are being asked to do. */
function taskPanel(q) {
  if (q.qtype === "choice") {
    const grid = el("div", { class: "hs-choices", role: "list" });
    (q.choices || []).forEach((text, i) =>
      grid.append(
        el(
          "div",
          { class: ["hs-choice", CHOICE_CLASSES[i % 4]], role: "listitem" },
          el("span", { class: "hs-choice-key", "aria-hidden": "true", text: String(i + 1) }),
          el("span", { class: "hs-choice-text", text })
        )
      )
    );
    return grid;
  }
  if (q.qtype === "match") {
    const items = q.match?.items || [];
    const options = q.match?.options || [];
    return el(
      "div",
      { class: "hs-taskcard hs-match" },
      el("h3", { class: "hs-task-title", text: "Match each item with an option" }),
      el("div", { class: "hs-match-cols" },
        el("ol", { class: "hs-match-items" }, items.map((t) => el("li", {}, el("code", { text: t })))),
        el("ul", { class: "hs-match-options" }, options.map((t, i) => el("li", {}, el("b", { class: "hs-letter", text: String.fromCharCode(65 + i) }), el("span", { text: t }))))
      )
    );
  }
  if (q.qtype === "blanks") {
    const blanks = q.blanks || [];
    return el(
      "div",
      { class: "hs-taskcard" },
      el("h3", { class: "hs-task-title", text: `Fill in ${plural(blanks.length, "blank")}` }),
      el("ul", { class: "hs-blank-list" }, blanks.map((b, i) => el("li", {}, el("b", { class: "hs-letter", text: String(i + 1) }), el("span", { text: b.hint ? `type: ${b.hint}` : "type the missing code" })))),
      typingNote("typing the missing code")
    );
  }
  // code
  const task = q.task || {};
  return el(
    "div",
    { class: "hs-taskcard" },
    el("h3", { class: "hs-task-title", text: "Write the code" }),
    task.examples && task.examples.length ? el("ul", { class: "hs-examples", "aria-label": "Examples" }, exampleRows(task)) : null,
    task.hidden_tests ? el("p", { class: "hs-hidden-tests", text: `+ ${plural(task.hidden_tests, "hidden test")}` }) : null,
    task.note ? el("p", { class: "hs-task-note", text: task.note }) : null,
    typingNote("writing code")
  );
}

function typingNote(text) {
  return el("p", { class: "hs-typing-note" }, el("span", { class: "hs-typing-dots", "aria-hidden": "true" }, el("i"), el("i"), el("i")), ` Players are ${text}…`);
}

// ---------------------------------------------------------------------------
// The HostGame: page shell, polling, actions, view switching
// ---------------------------------------------------------------------------

class HostGame {
  constructor(env, info) {
    this.env = env;
    this.code = info.code;
    this.token = info.token;
    this.lan = !!info.lan;
    this.joinUrls = info.joinUrls;
    this.api = hostSession(info.code, info.token);
    this.state = null;
    this.initial = info.state;
    this.view = null;
    this.viewKey = "";
    this.viewSince = 0;
    this.prevPhase = null;
    this.alive = true;
    this.pending = new Set();
    this.failSince = 0;
    this.raf = 0;

    this.announcer = el("div", { class: "sr-only", role: "status", "aria-live": "polite" });
    this.banner = el("div", { class: "hs-banner", role: "alert", hidden: true });
    this.stage = el("main", { class: "hs-stage", id: "hs-stage" });
    this.root = el("div", { class: "hs hs-game" }, this.stage, this.banner, this.announcer);

    this.poller = new Poller((since) => this.fetchState(since), {
      onState: (s) => this.onState(s),
      onError: (err, n) => this.onPollError(err, n),
      onFatal: (err) => this.onFatal(err),
    });
    this.onKey = this.onKey.bind(this);
    this.onFrame = this.onFrame.bind(this);
    this.onResize = () => {
      window.clearTimeout(this.resizeTimer);
      this.resizeTimer = window.setTimeout(() => this.alive && this.fit(), 120);
    };
  }

  start() {
    this.env.show(this.root, { focus: false });
    document.addEventListener("keydown", this.onKey);
    document.addEventListener("fullscreenchange", syncFullscreenButtons);
    window.addEventListener("resize", this.onResize);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => this.alive && this.fit());
    this.raf = requestAnimationFrame(this.onFrame);
    this.poller.push(this.initial);
    this.poller.start();
  }

  dispose() {
    if (!this.alive) return;
    this.alive = false;
    this.poller.stop();
    cancelAnimationFrame(this.raf);
    document.removeEventListener("keydown", this.onKey);
    document.removeEventListener("fullscreenchange", syncFullscreenButtons);
    window.removeEventListener("resize", this.onResize);
    if (this.view) this.view.destroy();
    this.view = null;
    if (current === this) current = null;
  }

  /** Called from every callback: the app shell replaced our DOM (the teacher went Home), so stop. */
  gone() {
    if (!this.alive) return true;
    if (!this.root.isConnected) {
      this.dispose();
      return true;
    }
    return false;
  }

  // ---- polling ---------------------------------------------------------------------------
  async fetchState(since) {
    const state = await this.api.state(since);
    this.setOnline(true);
    return state;
  }

  setOnline(ok) {
    if (!this.alive) return;
    if (ok) {
      if (this.failSince) {
        this.failSince = 0;
        this.banner.hidden = true;
        toast("Back online", "success", 1800);
      }
      return;
    }
    if (!this.failSince) this.failSince = Date.now();
  }

  onPollError(err, failures) {
    if (this.gone()) return;
    this.setOnline(false);
    const secs = Math.round((Date.now() - this.failSince) / 1000);
    this.banner.replaceChildren(
      el("span", { class: "hs-banner-icon", "aria-hidden": "true", text: "📡" }),
      el("span", { text: `Connection problem — still trying to reach the server${secs > 3 ? ` (${secs}s)` : ""}. The game keeps running for your players.` })
    );
    this.banner.hidden = false;
  }

  onFatal(err) {
    if (this.gone()) return;
    savedHost.clear();
    this.showEnded(err);
  }

  /** The game is not on the server any more (restart, expired, wrong token). */
  showEnded(err) {
    this.poller.stop();
    if (this.view) this.view.destroy();
    this.view = null;
    this.viewKey = "ended";
    this.banner.hidden = true;
    const setupAgain = () => renderSetup(this.env);
    this.stage.replaceChildren(
      el(
        "div",
        { class: "hs-center-card card pop-in" },
        el("div", { class: "hs-center-icon", "aria-hidden": "true", text: "😴" }),
        el("h1", { class: "hs-center-title", text: "This game isn't running any more" }),
        el("p", { class: "hs-center-text", text: "The server was restarted or the game expired, so it can't be resumed. Your next game is one click away." }),
        el(
          "div",
          { class: "hs-center-actions" },
          el("button", { class: "btn btn-green btn-lg", type: "button", "data-autofocus": "", text: "Host a new game", onClick: () => { this.dispose(); setupAgain(); } }),
          el("button", { class: "btn btn-white btn-lg", type: "button", text: "Home", onClick: () => { this.dispose(); this.env.goHome(); } })
        )
      )
    );
    this.announce("This game is not running any more.");
  }

  announce(text) {
    this.announcer.textContent = "";
    window.setTimeout(() => (this.announcer.textContent = text), 40);
  }

  // ---- state -> view ---------------------------------------------------------------------
  onState(state) {
    if (this.gone()) return;
    const prev = this.state;
    this.state = state;
    let kind = state.phase;
    if (!["lobby", "question", "reveal", "running", "finished"].includes(kind)) kind = "lobby";
    const key = kind === "question" || kind === "reveal" ? `${kind}:${state.question_index}` : kind;
    if (key !== this.viewKey) {
      if (this.view) this.view.destroy();
      const factory = { lobby: lobbyView, question: questionView, reveal: revealView, running: rushView, finished: finishedView }[kind];
      this.view = factory(this, state, prev);
      this.viewKey = key;
      this.viewSince = performance.now();
      this.stage.replaceChildren(this.view.el);
      if (prev) this.view.el.classList.add("hs-view-in");
      this.stage.scrollTop = 0;
      window.scrollTo(0, 0);
      this.fit();
      this.announce(this.view.announce || "");
      this.prevPhase = prev ? prev.phase : null;
    } else {
      this.view.update(state);
    }
  }

  /** Let a view shrink its text boxes so everything fits the projector without scrolling. */
  fit() {
    if (this.view && this.view.fit) this.view.fit();
  }

  onFrame() {
    if (!this.alive) return;
    if (this.gone()) return;
    if (this.view && this.view.tick) this.view.tick();
    this.raf = requestAnimationFrame(this.onFrame);
  }

  // ---- actions ---------------------------------------------------------------------------
  /** Send a host action; resolves to the new state or null (errors are shown to the teacher). */
  async act(name, body = {}) {
    if (this.pending.has(name)) return null;
    this.pending.add(name);
    try {
      const state = await this.api.action(name, body);
      this.poller.push(state);
      return state;
    } catch (err) {
      if (err.reason === "bad_state") {
        this.poller.nudge(); // the timer or a double click got there first
      } else if (err.reason === "not_found" || err.reason === "bad_token") {
        savedHost.clear();
        this.showEnded(err);
      } else {
        toast(friendly(err), "error");
      }
      return null;
    } finally {
      this.pending.delete(name);
    }
  }

  async confirmEnd({ lobby = false } = {}) {
    const ok = await confirmDialog(
      lobby
        ? { title: "Cancel this game?", message: "Nobody has started playing yet. The code will stop working and the players will see that the game ended.", confirmText: "Cancel game", cancelText: "Keep it", danger: true, icon: "🚪" }
        : { title: "End the game now?", message: "The scores so far become the final results.", confirmText: "End game", cancelText: "Keep playing", danger: true, icon: "🏁" }
    );
    if (!ok) return;
    const state = await this.act("end");
    if (state && lobby) {
      savedHost.clear();
      this.dispose();
      renderSetup(this.env);
    }
  }

  // ---- shared chrome ---------------------------------------------------------------------
  fsButton() {
    if (!fullscreenSupported()) return null;
    const on = !!document.fullscreenElement;
    return el(
      "button",
      { class: "btn btn-ghost btn-sm hs-fs-btn", type: "button", title: "Fullscreen (F)", "aria-pressed": String(on), onClick: () => toggleFullscreen() },
      el("span", { class: "hs-fs-icon", "aria-hidden": "true", text: on ? "🡼" : "⛶" }),
      el("span", { class: "hs-fs-label", text: on ? "Exit fullscreen" : "Fullscreen" })
    );
  }

  /** Page header: mode + title on the left; code, fullscreen, mute and extra buttons on the right. */
  header({ left = [], right = [], code = true } = {}) {
    const st = this.state;
    const mode = MODE_INFO[st.mode] || MODE_INFO.live;
    return el(
      "header",
      { class: "hs-top" },
      el(
        "div",
        { class: "hs-top-left" },
        left,
        el("span", { class: "hs-modepill", style: { "--mode-color": mode.color } }, el("span", { "aria-hidden": "true", text: mode.icon }), ` ${mode.name}`),
        st.title ? el("span", { class: "hs-title", text: st.title }) : null
      ),
      el(
        "div",
        { class: "hs-top-right" },
        right,
        code ? el("span", { class: "hs-codepill", title: "Join code" }, el("span", { text: "Join code" }), el("b", { text: prettyCode(this.code) })) : null,
        this.fsButton(),
        createMuteButton("hs-mute")
      )
    );
  }

  endButton() {
    return el("button", { class: "btn btn-red btn-sm", type: "button", text: "End game", onClick: () => this.confirmEnd() });
  }

  // ---- keyboard --------------------------------------------------------------------------
  onKey(e) {
    if (this.gone()) return;
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || isModalOpen()) return;
    const t = e.target;
    if (t && t.closest && t.closest("input, textarea, select, [contenteditable='true']")) return;
    const k = e.key;
    if (k === "f" || k === "F") {
      e.preventDefault();
      toggleFullscreen();
    } else if (k === "m" || k === "M") {
      e.preventDefault();
      document.querySelector(".hs-mute")?.click();
    } else if (k === "l" || k === "L") {
      if (this.view && this.view.toggleLock) {
        e.preventDefault();
        this.view.toggleLock();
      }
    } else if (k === " " || k === "Enter") {
      if (e.repeat) return;
      if (t && t.closest && t.closest("button, a, summary, [role='button']")) return; // let the focused control handle it
      if (performance.now() - this.viewSince < KEY_GUARD_MS) return;
      const go = this.view && this.view.primary && this.view.primary();
      if (go) {
        e.preventDefault();
        go();
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Player tiles (lobby grid) -- keyed so people pop in without redrawing the others
// ---------------------------------------------------------------------------

function playerGrid(game, { kickable = true } = {}) {
  const grid = el("ul", { class: "hs-tiles", "aria-label": "Players in the game" });
  const tiles = new Map();
  const empty = el("li", { class: "hs-tiles-empty" }, el("span", { class: "hs-empty-blooks", "aria-hidden": "true", text: "🐸 🦊 🐼" }), el("strong", { text: "Waiting for players…" }), el("span", { text: "They will pop up here as soon as they join." }));

  function makeTile(p) {
    const kick = kickable
      ? el("button", {
          class: "hs-kick",
          type: "button",
          "aria-label": `Remove ${p.name} from the game`,
          title: "Remove player",
          text: "✕",
          onClick: async (e) => {
            e.stopPropagation();
            const ok = await confirmDialog({ title: `Remove ${p.name}?`, message: "They will be taken out of the game and can join again with a new name while joining is open.", confirmText: "Remove", cancelText: "Keep", danger: true, icon: "👋" });
            if (ok) game.act("kick", { player_id: p.id });
          },
        })
      : null;
    return el("li", { class: "hs-tile pop-in", title: p.name, dataset: { id: p.id } }, hsBlook(p.avatar, 2.2), el("span", { class: ["hs-tile-name", p.name.length > 9 && "is-long"], text: p.name }), kick);
  }

  return {
    el: grid,
    /** Sync with the player list; returns how many are new. */
    update(players) {
      const seen = new Set();
      let added = 0;
      players.forEach((p, i) => {
        seen.add(p.id);
        let tile = tiles.get(p.id);
        if (!tile) {
          tile = makeTile(p);
          tiles.set(p.id, tile);
          added++;
        }
        tile.classList.toggle("is-away", p.connected === false);
        if (grid.children[i] !== tile) grid.insertBefore(tile, grid.children[i] || null);
      });
      for (const [id, tile] of tiles) {
        if (!seen.has(id)) {
          tile.remove();
          tiles.delete(id);
        }
      }
      if (players.length === 0) {
        if (!empty.isConnected) grid.append(empty);
      } else if (empty.isConnected) empty.remove();
      return added;
    },
  };
}

// ---------------------------------------------------------------------------
// LOBBY view
// ---------------------------------------------------------------------------

function lobbyView(game, state) {
  let selected = 0;
  const urls = game.joinUrls;
  const prettyHost = () => shortUrl(urls[selected]);

  const hostText = el("strong", { class: "hs-join-host", text: prettyHost() });
  const qrImg = el("img", { class: "hs-qr-img", alt: `QR code that opens ${prettyHost()} with the code filled in`, src: qrUrl(urls[selected]), width: 200, height: 200 });
  const qrBox = el("div", { class: "hs-qr" }, qrImg, el("span", { class: "hs-qr-cap", text: "Scan to join" }));
  qrImg.addEventListener("error", () => (qrBox.hidden = true));
  qrImg.addEventListener("load", () => (qrBox.hidden = false));

  const urlRows = urls.map((u, i) =>
    el(
      "li",
      { class: "hs-url-row", "aria-current": String(i === selected) },
      el("button", {
        class: "hs-url-pick",
        type: "button",
        title: urls.length > 1 ? "Show the QR code for this address" : u,
        "aria-pressed": String(i === selected),
        onClick: () => selectUrl(i),
        text: u.replace(/^https?:\/\//, ""),
      }),
      el("button", {
        class: "btn btn-white btn-sm hs-copy",
        type: "button",
        "aria-label": `Copy join link ${u}`,
        onClick: async (e) => {
          const ok = await copyText(u);
          toast(ok ? "Join link copied" : "Couldn't copy — select the link and copy it", ok ? "success" : "warn", 1800);
          sfx("click");
        },
        text: "⧉ Copy",
      })
    )
  );

  function selectUrl(i) {
    selected = i;
    hostText.textContent = prettyHost();
    qrImg.src = qrUrl(urls[i]);
    qrImg.alt = `QR code that opens ${prettyHost()} with the code filled in`;
    urlRows.forEach((row, k) => {
      row.setAttribute("aria-current", String(k === i));
      row.querySelector(".hs-url-pick").setAttribute("aria-pressed", String(k === i));
    });
  }

  const lanWarn = game.lan
    ? null
    : el(
        "div",
        { class: "hs-warn", role: "note" },
        el("span", { class: "hs-warn-icon", "aria-hidden": "true", text: "⚠️" }),
        el("div", {}, el("strong", { text: "Only this computer can join." }), el("p", {}, "Stop the server and start it with ", el("code", { text: "python app.py --lan" }), " so other devices on the network can connect."))
      );

  const lockedBadge = el("span", { class: "hs-locked-badge", hidden: true, text: "🔒 Joining is locked" });
  const joinCard = el(
    "section",
    { class: "hs-joincard card" },
    el(
      "div",
      { class: "hs-join-top" },
      el("div", { class: "hs-join-step" }, el("span", { class: "hs-step", text: "1" }), el("span", { class: "hs-join-line" }, "Go to ", hostText)),
      el("div", { class: "hs-join-step" }, el("span", { class: "hs-step", text: "2" }), el("span", { class: "hs-join-line", text: "Type this code" }))
    ),
    el("div", { class: "hs-bigcode", role: "img", "aria-label": `Join code ${String(game.code).split("").join(" ")}`, text: prettyCode(game.code) }),
    lockedBadge,
    el("div", { class: "hs-join-bottom" }, qrBox, el("ul", { class: "hs-urls", "aria-label": "Join addresses" }, urlRows)),
    lanWarn
  );

  // ---- players ------------------------------------------------------------------------------
  const grid = playerGrid(game);
  const count = el("span", { class: "hs-count-num", text: "0" });
  const countMax = el("span", { class: "hs-count-max" });
  const lockBtn = el("button", { class: "btn btn-sm btn-white btn-toggle hs-lock", type: "button", "aria-pressed": "false", title: "Stop new players joining (L)", onClick: () => toggleLock() });
  const lockLabel = el("span", { class: "hs-lock-label", text: "Lock joining" });
  lockBtn.append(el("span", { "aria-hidden": "true", class: "hs-lock-icon", text: "🔓" }), lockLabel);

  const playersCard = el(
    "section",
    { class: "hs-playerscard card" },
    el("div", { class: "hs-players-head" }, el("h2", { class: "hs-players-title" }, el("span", { "aria-hidden": "true", text: "👥 " }), "Players ", el("span", { class: "hs-count" }, count, countMax)), lockBtn),
    el("div", { class: "hs-players-scroll" }, grid.el)
  );

  const startBtn = el("button", { class: "btn btn-green btn-xl hs-start", type: "button", disabled: true, onClick: () => start() }, "Start game ", el("span", { "aria-hidden": "true", text: "▶" }), kbd("Enter"));
  const startHint = el("p", { class: "hs-start-hint", text: "Waiting for the first player…" });
  const cancelBtn = el("button", { class: "btn btn-ghost btn-sm", type: "button", text: "✕ Cancel game", onClick: () => game.confirmEnd({ lobby: true }) });

  let locked = false;
  async function toggleLock() {
    const next = !locked;
    await whileBusy(lockBtn, game.act("lock", { locked: next }));
    sfx("click");
  }

  async function start() {
    if (startBtn.disabled) return;
    sfx("levelup");
    await whileBusy(startBtn, game.act("start"));
  }

  const screen = el(
    "div",
    { class: "hs-lobby" },
    game.header({ left: [cancelBtn], code: false }),
    el("div", { class: "hs-lobby-grid" }, joinCard, playersCard),
    el("footer", { class: "hs-foot" }, startBtn, startHint)
  );

  let lastCount = 0;
  function update(s) {
    const added = grid.update(s.players);
    if (added && lastCount !== 0 || (added && s.players.length > 0 && lastCount === 0 && added < s.players.length)) sfx("click");
    else if (added) sfx("click");
    lastCount = s.players.length;
    count.textContent = fmt(s.players.length);
    countMax.textContent = ` / ${fmt(s.settings?.max_players || DEFAULT_MAX_PLAYERS)}`;
    locked = !!s.locked;
    lockBtn.setAttribute("aria-pressed", String(locked));
    lockLabel.textContent = locked ? "Joining locked" : "Lock joining";
    lockBtn.querySelector(".hs-lock-icon").textContent = locked ? "🔒" : "🔓";
    lockedBadge.hidden = !locked;
    const n = s.players.length;
    startBtn.disabled = n === 0;
    startHint.textContent = n === 0 ? "Waiting for the first player…" : `${plural(n, "player")} ready${s.mode === "live" ? ` · ${plural(s.question_total || s.settings?.question_count || 0, "question")}` : ` · ${s.settings?.duration_min || 5} minutes`}`;
  }
  update(state);

  return {
    el: screen,
    announce: "Lobby. Waiting for players to join.",
    update,
    toggleLock,
    primary: () => (startBtn.disabled ? null : () => start()),
    destroy() {},
  };
}

// ---------------------------------------------------------------------------
// LIVE QUESTION view
// ---------------------------------------------------------------------------

/** Countdown bar + big number. total/deadline are read lazily so the same widget can be re-aimed. */
function timerWidget() {
  const fill = el("div", { class: "hs-timer-fill" });
  const text = el("div", { class: "hs-timer-num", text: "–" });
  const label = el("div", { class: "hs-timer-label", text: "seconds" });
  const wrap = el("div", { class: "hs-timer", role: "timer", "aria-label": "Time left" }, el("div", { class: "hs-timer-track" }, fill), el("div", { class: "hs-timer-read" }, text, label));
  let lastSecs = null;
  return {
    el: wrap,
    /** remaining/total in seconds. */
    set(remaining, total, { beep = true } = {}) {
      const frac = total > 0 ? clamp(remaining / total, 0, 1) : 0;
      fill.style.transform = `scaleX(${frac})`;
      const secs = Math.max(0, Math.ceil(remaining));
      if (secs !== lastSecs) {
        text.textContent = secs >= 100 ? formatTime(secs) : String(secs);
        label.textContent = remaining <= 0 ? "time's up" : secs >= 100 ? "min" : secs === 1 ? "second" : "seconds";
        if (beep && lastSecs !== null && secs > 0 && secs <= 5) sfx("tick");
        lastSecs = secs;
      }
      wrap.classList.toggle("urgent", remaining <= 5);
      wrap.classList.toggle("warn", remaining > 5 && frac <= 0.34);
      wrap.classList.toggle("is-over", remaining <= 0);
    },
  };
}

/** Row of small avatars: lit when that player has answered. */
function answerWall() {
  const wall = el("ul", { class: "hs-wall", "aria-hidden": "true" });
  const items = new Map();
  let signature = "";
  return {
    el: wall,
    update(players) {
      const sig = players.map((p) => p.id).join(",");
      if (sig !== signature) {
        signature = sig;
        items.clear();
        wall.replaceChildren(
          ...players.slice(0, WALL_LIMIT).map((p) => {
            const li = el("li", { class: "hs-wall-item", title: p.name }, hsBlook(p.avatar, 1.55));
            items.set(p.id, li);
            return li;
          })
        );
      }
      for (const p of players) items.get(p.id)?.classList.toggle("is-in", !!p.answered_now);
    },
  };
}

function questionView(game, state) {
  const q = state.question;
  const timer = timerWidget();
  const wall = answerWall();
  const countNum = el("b", { class: "hs-answered-num", text: "0" });
  const countTotal = el("span", { class: "hs-answered-total" });
  const progressFill = el("div", { class: "hs-progress-fill" });
  const answered = el(
    "div",
    { class: "hs-answered" },
    el("div", { class: "hs-answered-text" }, countNum, countTotal, " answered"),
    el("div", { class: "hs-progress" }, progressFill)
  );
  const skipBtn = el(
    "button",
    { class: "btn btn-yellow btn-lg hs-skip", type: "button", title: "End this question now and show the answer (Space)", onClick: () => skip() },
    "Skip ",
    el("span", { "aria-hidden": "true", text: "⏭" }),
    el("span", { class: "hs-btn-sub", text: "show the answer" }),
    kbd("Space")
  );
  async function skip() {
    if (skipBtn.disabled) return;
    await whileBusy(skipBtn, game.act("skip"));
  }

  const counter = el("span", { class: "hs-qcount", "aria-label": `Question ${state.question_index + 1} of ${state.question_total}` }, el("b", { text: String(state.question_index + 1) }), ` / ${state.question_total}`);
  const screen = el(
    "div",
    { class: ["hs-question", `hs-q-${q.qtype}`, q.code || q.qtype === "code" ? "has-code" : "no-code"] },
    game.header({ left: [counter], right: [game.endButton()] }),
    el("div", { class: "hs-timerrow" }, timer.el, answered),
    el("div", { class: "hs-qgrid" }, el("section", { class: "hs-qcard card" }, metaRow(q), questionBody(q)), el("section", { class: "hs-apanel" }, taskPanel(q))),
    el("footer", { class: "hs-foot hs-foot-split" }, wall.el, skipBtn)
  );

  let nudgedAt = 0;
  let deadline = state.deadline;
  let total = q.time_limit || (state.deadline && state.question_started ? state.deadline - state.question_started : 20);

  function update(s) {
    deadline = s.deadline;
    const a = s.answers || { count: 0, total: s.players.length };
    countNum.textContent = fmt(a.count);
    countTotal.textContent = ` / ${fmt(a.total)}`;
    progressFill.style.transform = `scaleX(${a.total ? a.count / a.total : 0})`;
    wall.update(s.players);
  }
  update(state);
  game.root.style.setProperty("--hs-time-total", String(total));

  return {
    el: screen,
    announce: `Question ${state.question_index + 1} of ${state.question_total}. ${q.prompt}`,
    update,
    fit() {
      for (const box of screen.querySelectorAll(".hs-qcard, .hs-taskcard")) fitBox(box);
    },
    tick() {
      const rem = clock.remaining(deadline);
      timer.set(rem, total);
      // The server applies "time is up" on the next request; ask for it once the grace second has passed.
      if (rem < -1.05) {
        const now = performance.now();
        if (now - nudgedAt > 700) {
          nudgedAt = now;
          game.poller.nudge();
        }
      }
    },
    primary: () => (skipBtn.disabled ? null : () => skip()),
    destroy() {},
  };
}

// ---------------------------------------------------------------------------
// REVEAL view
// ---------------------------------------------------------------------------

/** Top-N standings. Scores count up from what the player had before this question. */
function leaderboardList(players, { limit = 5, showDelta = true, animate = true } = {}) {
  const top = players.slice(0, limit);
  const maxScore = Math.max(1, ...top.map((p) => p.score));
  const list = el("ol", { class: "hs-board" });
  top.forEach((p, i) => {
    const score = el("span", { class: "hs-board-score", text: fmt(animate ? Math.max(0, p.score - (p.delta || 0)) : p.score) });
    list.append(
      el(
        "li",
        { class: ["hs-board-row", `hs-rank-${Math.min(p.rank, 4)}`], style: { "--i": i, "--share": clamp(p.score / maxScore, 0.04, 1) } },
        el("span", { class: "hs-board-rank", text: rankLabel(p) }),
        hsBlook(p.avatar, 1.9),
        el("span", { class: "hs-board-name", text: p.name }),
        showDelta ? el("span", { class: ["hs-delta", !p.delta && "is-zero"], text: p.delta ? `+${fmt(p.delta)}` : "+0" }) : null,
        score
      )
    );
    if (animate && p.delta) animateNumber(score, Math.max(0, p.score - p.delta), p.score, 1100);
  });
  return list;
}

function distributionBar(dist, total) {
  const [right = 0, wrong = 0, none = 0] = dist;
  const sum = Math.max(1, right + wrong + none);
  const seg = (n, cls, label) => (n > 0 ? el("div", { class: ["hs-dist-seg", cls], style: { flexGrow: n }, title: `${label}: ${n}` }, el("b", { text: String(n) })) : null);
  return el(
    "div",
    { class: "hs-dist" },
    el("div", { class: "hs-dist-bar", role: "img", "aria-label": `${right} correct, ${wrong} wrong, ${none} no answer` }, seg(right, "is-right", "Correct"), seg(wrong, "is-wrong", "Wrong"), seg(none, "is-none", "No answer")),
    el(
      "div",
      { class: "hs-dist-legend" },
      el("span", { class: "is-right", text: "Correct" }),
      el("span", { class: "is-wrong", text: "Wrong" }),
      el("span", { class: "is-none", text: "No answer" })
    )
  );
}

/** The right answer, shown the way it was asked (the choice bars use the colours of the players' buttons). */
function answerPanel(q, rev) {
  const ans = rev.answer || {};
  if (q.qtype === "choice") {
    const dist = rev.distribution || [];
    const most = Math.max(1, ...dist);
    const grid = el("div", { class: "hs-choices hs-choices-reveal", role: "list" });
    (q.choices || []).forEach((text, i) => {
      const isRight = i === ans.answer;
      const n = dist[i] || 0;
      grid.append(
        el(
          "div",
          { class: ["hs-choice", CHOICE_CLASSES[i % 4], isRight ? "is-right" : "is-dim"], role: "listitem" },
          el("span", { class: "hs-choice-bar", style: { "--share": n / most } }),
          el("span", { class: "hs-choice-key", "aria-hidden": "true", text: isRight ? "✓" : String(i + 1) }),
          el("span", { class: "hs-choice-text", text }),
          el("span", { class: "hs-choice-count", "aria-label": `${n} players` }, el("b", { text: String(n) }), el("small", { text: n === 1 ? " player" : " players" }))
        )
      );
    });
    return grid;
  }
  if (q.qtype === "blanks") {
    return el("div", { class: "hs-solution" }, el("h3", { class: "hs-solution-title" }, el("span", { "aria-hidden": "true", text: "✓ " }), "Correct code"), codeView(q.code, { blanks: q.blanks, answers: ans.blanks || [] }));
  }
  if (q.qtype === "match") {
    const items = q.match?.items || [];
    const options = q.match?.options || [];
    return el(
      "div",
      { class: "hs-solution" },
      el("h3", { class: "hs-solution-title" }, el("span", { "aria-hidden": "true", text: "✓ " }), "Correct matches"),
      el("ul", { class: "hs-matched" }, items.map((it, i) => el("li", {}, el("code", { text: it }), el("span", { class: "hs-example-arrow", "aria-hidden": "true", text: "→" }), el("span", { text: options[(ans.match || [])[i]] ?? "?" }))))
    );
  }
  return el("div", { class: "hs-solution" }, el("h3", { class: "hs-solution-title" }, el("span", { "aria-hidden": "true", text: "✓ " }), "One way to do it"), codeView(ans.solution || ""));
}

function revealView(game, state) {
  const q = state.question;
  const rev = state.reveal || { correct_count: 0, answered_count: 0, total: state.players.length, distribution: [], answer: {} };
  const last = state.question_index + 1 >= state.question_total;
  const nextLabel = last ? "See the results" : "Next question";

  // ---- left: the question with its answer -------------------------------------------------
  const left = el("section", { class: "hs-revealcard card" }, metaRow(q), q.qtype === "blanks" ? promptNode(q) : questionBody(q), answerPanel(q, rev));
  if (rev.explanation) {
    left.append(el("div", { class: "hs-explain" }, el("span", { class: "hs-explain-icon", "aria-hidden": "true", text: "💡" }), el("p", { html: renderInlineCode(rev.explanation) })));
  }

  // ---- right: how the room did + standings ------------------------------------------------
  const gotIt = el(
    "div",
    { class: "hs-gotit" },
    el("div", { class: "hs-gotit-main" }, el("b", { class: "hs-gotit-num", text: String(rev.correct_count) }), el("span", { class: "hs-gotit-of", text: ` of ${rev.total}` })),
    el("div", { class: "hs-gotit-cap", text: rev.total === 1 ? "player got it right" : "players got it right" }),
    rev.fastest ? el("div", { class: "hs-fastest" }, el("span", { "aria-hidden": "true", text: "⚡ " }), el("b", { text: rev.fastest.name }), ` was fastest · ${(rev.fastest.ms / 1000).toFixed(1)} s`) : el("div", { class: "hs-fastest is-none", text: rev.answered_count ? "Nobody got it right this time." : "Nobody answered this one." })
  );
  const right = el(
    "aside",
    { class: "hs-reveal-side" },
    el("section", { class: "hs-sidecard card" }, gotIt, q.qtype === "choice" ? null : distributionBar(rev.distribution || [], rev.total)),
    el("section", { class: "hs-sidecard hs-boardcard card" }, el("h2", { class: "hs-side-title", text: "Leaderboard" }), leaderboardList(state.players, { limit: 5 }))
  );

  // ---- footer -----------------------------------------------------------------------------
  const nextBtn = el("button", { class: "btn btn-green btn-lg hs-next", type: "button", onClick: () => next() }, nextLabel, " ", el("span", { "aria-hidden": "true", text: "▶" }), kbd("Space"));
  const autoText = el("span", { class: "hs-auto-text" });
  const autoFill = el("span", { class: "hs-auto-fill" });
  const auto = el("div", { class: "hs-auto", hidden: true, role: "timer" }, autoText, el("span", { class: "hs-auto-track" }, autoFill));
  let nextAt = state.next_at;
  let nextTotal = null;
  async function next() {
    if (nextBtn.disabled) return;
    await whileBusy(nextBtn, game.act("next"));
  }

  const counter = el("span", { class: "hs-qcount" }, el("b", { text: String(state.question_index + 1) }), ` / ${state.question_total}`);
  const screen = el(
    "div",
    { class: ["hs-reveal", `hs-q-${q.qtype}`, q.code ? "has-code" : "no-code"] },
    game.header({ left: [counter], right: [game.endButton()] }),
    el("div", { class: "hs-revealgrid" }, left, right),
    el("footer", { class: "hs-foot hs-foot-split" }, auto, nextBtn)
  );

  sfx(rev.correct_count > 0 ? "chest" : "wrong");

  let nudgedAt = 0;
  return {
    el: screen,
    announce: `Answer revealed. ${rev.correct_count} of ${rev.total} got it right.`,
    fit() {
      fitBox(left);
    },
    update(s) {
      nextAt = s.next_at;
    },
    tick() {
      if (nextAt) {
        const rem = clock.remaining(nextAt);
        if (nextTotal === null) nextTotal = Math.max(rem, 1);
        auto.hidden = false;
        autoText.textContent = rem > 0 ? `Next question in ${Math.ceil(rem)}s` : "Starting…";
        autoFill.style.transform = `scaleX(${clamp(rem / nextTotal, 0, 1)})`;
        if (rem < -0.3) {
          const now = performance.now();
          if (now - nudgedAt > 700) {
            nudgedAt = now;
            game.poller.nudge();
          }
        }
      } else if (!auto.hidden) auto.hidden = true;
    },
    primary: () => (nextBtn.disabled ? null : () => next()),
    destroy() {},
  };
}

// ---------------------------------------------------------------------------
// TIME RUSH view
// ---------------------------------------------------------------------------

function rushView(game, state, prev) {
  const timeNum = el("div", { class: "hs-rush-time", text: "0:00", role: "timer", "aria-label": "Time left" });
  const timeFill = el("div", { class: "hs-timer-fill" });
  const timeBar = el("div", { class: "hs-timer hs-rush-bar" }, el("div", { class: "hs-timer-track" }, timeFill));
  const answeredNum = el("b", { class: "hs-stat-num", text: "0" });
  const accuracy = el("b", { class: "hs-stat-num", text: "–" });
  const playersNum = el("b", { class: "hs-stat-num", text: "0" });

  const stat = (node, caption, icon) => el("div", { class: "hs-stat" }, el("span", { class: "hs-stat-icon", "aria-hidden": "true", text: icon }), el("div", {}, node, el("span", { class: "hs-stat-cap", text: caption })));
  const rows = new Map();
  const board = el("ol", { class: "hs-rush-board", "aria-label": "Leaderboard" });
  const more = el("p", { class: "hs-more", hidden: true });
  const emptyNote = el("p", { class: "hs-rush-empty", text: "Waiting for the first answers…" });

  const endBtn = game.endButton();
  endBtn.classList.add("hs-rush-end");

  const screen = el(
    "div",
    { class: "hs-rush" },
    game.header({ right: [] }),
    el(
      "div",
      { class: "hs-rush-top" },
      el("section", { class: "hs-rush-clock" }, el("span", { class: "hs-rush-clock-cap", text: "Time left" }), timeNum, timeBar),
      el("section", { class: "hs-rush-stats" }, stat(answeredNum, "questions answered", "📝"), stat(accuracy, "correct", "🎯"), stat(playersNum, "players racing", "👥"))
    ),
    el("section", { class: "hs-rush-boardcard card" }, board, emptyNote, more),
    el("footer", { class: "hs-foot hs-foot-split" }, el("span", { class: "hs-foot-note", text: "Players race through their own questions. After a wrong answer they wait 3 seconds." }), endBtn)
  );

  const endsAt = () => game.state.ends_at;
  const total = () => Math.max(1, (game.state.ends_at || 0) - (game.state.started_at || 0));
  let lastSecs = null;
  let nudgedAt = 0;
  let rowH = 0;

  function update(s) {
    const st = s.stats || { questions_answered: 0, correct: 0 };
    answeredNum.textContent = fmt(st.questions_answered);
    accuracy.textContent = st.questions_answered ? `${pct(st.correct, st.questions_answered)}%` : "–";
    playersNum.textContent = fmt(s.players.length);
    const top = s.players.slice(0, RUSH_ROWS);
    const maxScore = Math.max(1, ...top.map((p) => p.score));
    emptyNote.hidden = s.players.length > 0 && s.players.some((p) => p.answered > 0);
    const keep = new Set();
    top.forEach((p, i) => {
      keep.add(p.id);
      let row = rows.get(p.id);
      if (!row) {
        row = makeRow(p);
        rows.set(p.id, row.el);
        row.el._parts = row;
        board.append(row.el);
        row = row.el;
      }
      const parts = row._parts;
      row.style.setProperty("--i", String(i));
      row.style.setProperty("--share", String(clamp(p.score / maxScore, p.score > 0 ? 0.03 : 0, 1)));
      row.className = `hs-rush-row hs-rank-${Math.min(p.rank, 4)}`;
      parts.rank.textContent = rankLabel(p);
      parts.name.textContent = p.name;
      const from = parts.score;
      if (from !== p.score) {
        animateNumber(parts.scoreEl, from, p.score, 700);
        parts.score = p.score;
      }
      parts.acc.textContent = p.answered ? `${pct(p.correct, p.answered)}%` : "–";
      parts.accChip.title = `${p.correct} of ${p.answered} correct`;
      parts.streak.textContent = p.streak >= 2 ? `🔥 ${p.streak}` : "";
      parts.streak.hidden = p.streak < 2;
      row.setAttribute("aria-label", `${p.rank}. ${p.name}, ${p.score} points`);
    });
    for (const [id, row] of rows) {
      if (!keep.has(id)) {
        row.remove();
        rows.delete(id);
      }
    }
    board.style.setProperty("--n", String(Math.max(1, top.length)));
    const extra = s.players.length - top.length;
    more.hidden = extra <= 0;
    more.textContent = extra > 0 ? `+ ${plural(extra, "more player")} racing` : "";
  }

  function makeRow(p) {
    const rank = el("span", { class: "hs-board-rank" });
    const name = el("span", { class: "hs-board-name" });
    const scoreEl = el("span", { class: "hs-board-score", text: fmt(p.score) });
    const acc = el("span");
    const accChip = el("span", { class: "hs-chip" }, "🎯 ", acc);
    const streak = el("span", { class: "hs-chip hs-chip-streak", hidden: true });
    const node = el(
      "li",
      { class: "hs-rush-row" },
      rank,
      hsBlook(p.avatar, 1.9),
      el("span", { class: "hs-rush-main" }, name, el("span", { class: "hs-rush-bar-track" }, el("span", { class: "hs-rush-bar-fill" }))),
      el("span", { class: "hs-chips" }, accChip, streak),
      scoreEl
    );
    return { el: node, rank, name, scoreEl, acc, accChip, streak, score: p.score };
  }
  update(state);

  const wasPlaying = prev && prev.phase === "lobby";
  if (wasPlaying) sfx("levelup");

  return {
    el: screen,
    announce: "Time Rush started. Players are racing.",
    update,
    tick() {
      const rem = clock.remaining(endsAt());
      const secs = Math.max(0, Math.ceil(rem));
      if (secs !== lastSecs) {
        timeNum.textContent = formatTime(secs);
        timeNum.classList.toggle("urgent", rem <= 10);
        if (lastSecs !== null && secs > 0 && secs <= 5) sfx("tick");
        lastSecs = secs;
      }
      timeFill.style.transform = `scaleX(${clamp(rem / total(), 0, 1)})`;
      timeBar.classList.toggle("urgent", rem <= 10);
      timeBar.classList.toggle("warn", rem > 10 && rem / total() <= 0.25);
      if (rem < -0.2) {
        const now = performance.now();
        if (now - nudgedAt > 700) {
          nudgedAt = now;
          game.poller.nudge();
        }
      }
    },
    primary: () => null,
    destroy() {},
  };
}

// ---------------------------------------------------------------------------
// FINISHED view
// ---------------------------------------------------------------------------

function podium(entries) {
  // On screen: 2nd | 1st | 3rd. Ties share the medal, the order in the list decides the place on the stage.
  const slots = [entries[1], entries[0], entries[2]];
  const wrap = el("ol", { class: ["hs-podium", `hs-podium-${entries.length}`], "aria-label": "Top players" });
  slots.forEach((p, slot) => {
    if (!p) return;
    const place = Math.min(p.rank, 3);
    wrap.append(
      el(
        "li",
        { class: ["hs-podium-slot", `place-${place}`], style: { "--delay": `${[0.45, 0.9, 0.05][slot]}s` } },
        el("div", { class: "hs-podium-who" }, el("span", { class: "hs-podium-medal", "aria-hidden": "true", text: MEDALS[place] }), hsBlook(p.avatar, place === 1 ? 3.8 : 3.1), el("strong", { class: "hs-podium-name", text: p.name }), el("span", { class: "hs-podium-score", text: `${fmt(p.score)} pts` })),
        el("div", { class: "hs-podium-step" }, el("span", { text: String(p.rank) }))
      )
    );
  });
  return wrap;
}

function finishedView(game, state, prev) {
  const summary = state.summary || { podium: [], questions: [], totals: { players: state.players.length, answers: 0, correct: 0 } };
  const players = state.players;
  const totals = summary.totals;
  const live = state.mode === "live";

  const standingRows = players.map((p) =>
    el(
      "tr",
      { class: p.rank <= 3 ? `hs-rank-${p.rank}` : null },
      el("td", { class: "hs-col-rank", text: rankLabel(p) }),
      el("td", { class: "hs-col-name" }, el("span", { class: "hs-name-cell" }, hsBlook(p.avatar, 1.7), el("span", { text: p.name }))),
      el("td", { class: "hs-col-num", text: fmt(p.score) }),
      el("td", { class: "hs-col-num", text: `${p.correct}/${p.answered}` }),
      el("td", { class: "hs-col-num hs-col-acc", text: p.answered ? `${pct(p.correct, p.answered)}%` : "–" })
    )
  );
  const standings = el(
    "section",
    { class: "hs-fin-card card" },
    el("h2", { class: "hs-fin-title", text: "Final standings" }),
    players.length
      ? el(
          "div",
          { class: "hs-table-wrap" },
          el(
            "table",
            { class: "hs-table" },
            el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Rank" }), el("th", { scope: "col", text: "Player" }), el("th", { scope: "col", class: "hs-col-num", text: "Score" }), el("th", { scope: "col", class: "hs-col-num", text: "Correct" }), el("th", { scope: "col", class: "hs-col-num", text: "Accuracy" }))),
            el("tbody", {}, standingRows)
          )
        )
      : el("p", { class: "hs-muted", text: "Nobody played this game." })
  );

  // hardest questions (live) / weakest topics (rush): lowest % correct first, only those somebody answered
  const hard = [...(summary.questions || [])].filter((x) => x.answered > 0 || live).sort((a, b) => a.correct_pct - b.correct_pct || b.answered - a.answered).slice(0, 4);
  const hardList = el(
    "ol",
    { class: "hs-hard" },
    hard.map((x) =>
      el(
        "li",
        { class: "hs-hard-row" },
        el("span", { class: ["hs-hard-pct", x.correct_pct < 40 ? "is-low" : x.correct_pct < 70 ? "is-mid" : "is-high"], text: `${x.correct_pct}%` }),
        el("span", { class: "hs-hard-text" }, el("span", { class: "hs-hard-q" }, live ? el("b", { text: `Q${x.index} ` }) : null, el("span", { class: "hs-hard-prompt", text: String(x.prompt || "").replace(/`/g, "") })), el("span", { class: "hs-hard-meta", text: live ? `${QTYPE_LABEL[x.qtype] || x.qtype} · ${x.correct} of ${x.answered} correct${x.avg_ms ? ` · avg ${(x.avg_ms / 1000).toFixed(1)} s` : ""}` : `${x.correct} of ${x.answered} correct${x.avg_ms ? ` · avg ${(x.avg_ms / 1000).toFixed(1)} s` : ""}` }))
      )
    )
  );
  const hardCard = el(
    "section",
    { class: "hs-fin-card card" },
    el("h2", { class: "hs-fin-title", text: live ? "Hardest questions" : "Weakest topics" }),
    hard.length ? hardList : el("p", { class: "hs-muted", text: "No answers to show." }),
    el("div", { class: "hs-totals" }, el("span", { class: "meta-pill hs-total-pill" }, `👥 ${plural(totals.players, "player")}`), el("span", { class: "meta-pill hs-total-pill" }, `📝 ${plural(totals.answers, "answer")}`), el("span", { class: "meta-pill hs-total-pill" }, `🎯 ${pct(totals.correct, totals.answers)}% correct`))
  );

  const csv = el("a", { class: "btn btn-blue", href: game.api.csvUrl(), download: `pyblooket-${game.code}-results.csv`, text: "⬇ Download results (CSV)" });
  const again = el("button", {
    class: "btn btn-green",
    type: "button",
    text: "🎮 Host another game",
    onClick: () => {
      savedHost.clear();
      game.dispose();
      renderSetup(game.env);
    },
  });
  const home = el("button", {
    class: "btn btn-white",
    type: "button",
    text: "Home",
    onClick: () => {
      savedHost.clear();
      game.dispose();
      game.env.goHome();
    },
  });

  const winner = summary.podium[0];
  const screen = el(
    "div",
    { class: "hs-finished" },
    game.header({ code: false }),
    el("div", { class: "hs-fin-hero" }, el("h1", { class: "hs-fin-headline", text: winner && winner.answered ? "Game over!" : "Game over" }), winner ? podium(summary.podium) : el("p", { class: "hs-muted", text: "Nobody joined this game." })),
    el("div", { class: "hs-fin-grid" }, standings, hardCard),
    el("footer", { class: "hs-foot hs-fin-actions" }, csv, again, home)
  );

  // fanfare only when we actually saw the game end (not when the page was re-opened later)
  if (prev && prev.phase !== "finished" && winner) {
    sfx("win");
    window.setTimeout(() => game.alive && game.viewKey === "finished" && confetti({ count: 170, x: 0.5, y: 0.3 }), 350);
    window.setTimeout(() => game.alive && game.viewKey === "finished" && confetti({ count: 90, x: 0.2, y: 0.4 }), 1100);
    window.setTimeout(() => game.alive && game.viewKey === "finished" && confetti({ count: 90, x: 0.8, y: 0.4 }), 1500);
  }

  return {
    el: screen,
    announce: winner ? `Game over. ${winner.name} won with ${winner.score} points.` : "Game over.",
    update() {},
    primary: () => null,
    destroy() {
      for (const layer of document.querySelectorAll(".confetti-layer")) layer.remove();
    },
  };
}
