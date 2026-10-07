/**
 * PyBlooket app shell: HOME -> SETUP -> GAME -> RESULTS, plus HIGH SCORES.
 * Game modes live in ./modes/ (see engine.js for the mode contract).
 *
 * HOME has two big classroom buttons (Host a game -> host.js, Join a game -> play.js; a shared link
 * /?join=483920 opens Join with the code filled in) above the solo mode grid. Solo SETUP picks the
 * lesson topics (Unit 2 lessons first, extras tucked away), the question types (Mixed / Multiple
 * choice / Typing) and the difficulty; renderGame() hands the choices to the engine and the QuestionFeed.
 */

import { fetchTopics, QuestionFeed } from "./api.js";
import { isAbortError, startGame } from "./engine.js";
import { playLookup, prettyCode, savedHost, savedPlayer } from "./hostapi.js";
import { renderHost } from "./host.js";
import modes from "./modes/index.js";
import { renderJoin } from "./play.js";
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
  sfx,
  storageGet,
  storageSet,
  toast,
} from "./ui.js";

const SETTINGS_KEY = "pyblooket.settings";
const HIGHSCORES_KEY = "pyblooket.highscores";
const MAX_SCORES = 10;
const NAME_MAX = 16;

const MODE_COLORS = {
  gold: "#ffb703",
  race: "#2f8cff",
  survival: "#ff4d5e",
  blitz: "#a855f7",
  boss: "#19b86b",
};
const FALLBACK_COLORS = ["#ff8a1f", "#19c3c3", "#ff5cb8", "#2f8cff", "#ffb703"];

/** Bump when the saved topic ids change meaning: older saved selections are then reset to the lessons. */
const TOPICS_VERSION = 2;

/** The "Question types" presets (ids match catalog.type_presets); wording adapts to catalog.code_enabled. */
const TYPE_CHOICES = [
  {
    id: "mixed",
    icon: "🎲",
    label: "Mixed",
    sub: (code) => (code ? "choice + typing" : "choice + blanks"),
    blurb: (code) => (code ? "Multiple choice plus fill-in-the-blanks and coding." : "Multiple choice plus fill-in-the-blanks."),
  },
  {
    id: "choice",
    icon: "👆",
    label: "Multiple choice",
    sub: () => "tap an answer",
    blurb: () => "Pick the right answer or match things up. No typing.",
  },
  {
    id: "typing",
    icon: "⌨️",
    label: "Typing",
    sub: (code) => (code ? "blanks + code" : "fill the blanks"),
    blurb: (code) => (code ? "Fill in the blanks and write real code." : "Fill in the blanks."),
  },
];
const TYPE_IDS = TYPE_CHOICES.map((c) => c.id);
/** What each preset means if the server did not say (older servers). */
const DEFAULT_PRESETS = { mixed: ["choice", "blanks", "match", "code"], choice: ["choice", "match"], typing: ["blanks", "code"] };
const QTYPE_LABELS = { choice: "Multiple choice", blanks: "Fill in the blanks", match: "Matching", code: "Write the code" };

const DIFFICULTY_CHOICES = [
  { id: 1, label: "Easy", stars: "★", points: "100 pts" },
  { id: 2, label: "Medium", stars: "★★", points: "250 pts" },
  { id: 3, label: "Hard", stars: "★★★", points: "500 pts" },
  { id: "mixed", label: "Mixed", stars: "🎲", points: "100–500" },
];

const app = document.getElementById("app");

const state = {
  catalog: null, // {topics, difficulties, qtypes, type_presets, code_enabled} (see normalizeCatalog)
  catalogPromise: null,
  catalogError: null,
  settings: loadSettings(),
  game: null, // running game handle
};

// AbortError rejections from modes that don't await ctx.ask() are expected on quit.
window.addEventListener("unhandledrejection", (e) => {
  if (isAbortError(e.reason)) e.preventDefault();
});

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

function loadSettings() {
  const raw = storageGet(SETTINGS_KEY, {});
  const s = raw && typeof raw === "object" ? raw : {};
  return {
    playerName: typeof s.playerName === "string" ? s.playerName.slice(0, NAME_MAX) : "",
    avatar: AVATARS.includes(s.avatar) ? s.avatar : AVATARS[Math.floor(Math.random() * AVATARS.length)],
    // null = every lesson topic. Selections saved before the lesson groups existed are dropped once.
    topics: s.topicsV === TOPICS_VERSION && Array.isArray(s.topics) ? s.topics.filter((t) => typeof t === "string") : null,
    types: TYPE_IDS.includes(s.types) ? s.types : "mixed",
    difficulty: [1, 2, 3, "mixed"].includes(s.difficulty) ? s.difficulty : "mixed",
    options: s.options && typeof s.options === "object" ? s.options : {},
  };
}

function saveSettings() {
  storageSet(SETTINGS_KEY, { ...state.settings, topicsV: TOPICS_VERSION });
}

function loadHighScores() {
  const raw = storageGet(HIGHSCORES_KEY, {});
  return raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
}

/** Insert a score; returns {rank (1-based) | null, isBest}. */
function recordHighScore(modeId, entry) {
  const all = loadHighScores();
  const list = Array.isArray(all[modeId]) ? all[modeId].filter((e) => e && Number.isFinite(e.score)) : [];
  const previousBest = list.length ? Math.max(...list.map((e) => e.score)) : null;
  list.push(entry);
  list.sort((a, b) => b.score - a.score || (b.accuracy || 0) - (a.accuracy || 0) || String(a.date).localeCompare(String(b.date)));
  const trimmed = list.slice(0, MAX_SCORES);
  all[modeId] = trimmed;
  storageSet(HIGHSCORES_KEY, all);
  const idx = trimmed.indexOf(entry);
  return {
    rank: idx >= 0 ? idx + 1 : null,
    isBest: entry.score > 0 && (previousBest === null || entry.score > previousBest),
  };
}

// ---------------------------------------------------------------------------
// Catalogue (topics, difficulties and question types from the server)
// ---------------------------------------------------------------------------

/** GET /api/topics, including the fields fetchTopics() may not hand on (type_presets, code_enabled). */
async function fetchCatalog() {
  const data = await fetchTopics();
  if (data.type_presets && typeof data.code_enabled === "boolean") return data;
  try {
    const res = await fetch("/api/topics", { headers: { Accept: "application/json" } });
    if (res.ok) return { ...data, ...(await res.json()) };
  } catch {
    /* fall back to the defaults below */
  }
  return data;
}

/**
 * The catalogue the screens (and host.js / play.js) can rely on:
 *   topics [{id, name, icon, description, group: "course"|"extra", lesson: "CSF.2.D"|"", types: {qtype: count}}]
 *   difficulties [{id, label, points}]    qtypes [{id, label, time_factor}]
 *   type_presets {mixed|choice|typing: [qtype, ...]}    code_enabled (false = the server has typed code switched off)
 */
function normalizeCatalog(data) {
  const codeEnabled = data.code_enabled !== false;
  const type_presets = {};
  for (const key of TYPE_IDS) {
    const raw = data.type_presets && Array.isArray(data.type_presets[key]) ? data.type_presets[key] : DEFAULT_PRESETS[key];
    type_presets[key] = raw.filter((t) => typeof t === "string" && (codeEnabled || t !== "code"));
  }
  return {
    ...data,
    topics: (data.topics || []).map((t) => ({ ...t, group: t.group === "extra" ? "extra" : "course", lesson: typeof t.lesson === "string" ? t.lesson : "" })),
    difficulties: data.difficulties || [],
    qtypes: Array.isArray(data.qtypes) ? data.qtypes : [],
    type_presets,
    code_enabled: codeEnabled,
  };
}

function loadCatalog() {
  if (state.catalog) return Promise.resolve(state.catalog);
  if (!state.catalogPromise) {
    state.catalogError = null;
    state.catalogPromise = fetchCatalog()
      .then((data) => {
        state.catalog = normalizeCatalog(data);
        return state.catalog;
      })
      .catch((err) => {
        state.catalogError = err;
        state.catalogPromise = null;
        throw err;
      });
  }
  return state.catalogPromise;
}

function topicIds() {
  return (state.catalog?.topics || []).map((t) => t.id);
}

/** Lesson topics (sorted by lesson tag) and the extras. A catalogue with only extras counts them as the lessons. */
function topicGroups() {
  const topics = state.catalog?.topics || [];
  let lessons = topics.filter((t) => t.group !== "extra").sort((a, b) => a.lesson.localeCompare(b.lesson, undefined, { numeric: true }));
  let extras = topics.filter((t) => t.group === "extra");
  if (!lessons.length) [lessons, extras] = [extras, []];
  return { lessons, extras };
}

/** The saved topic selection, restricted to topics the server actually has (none left = every lesson topic). */
function selectedTopics() {
  const ids = topicIds();
  const picked = (state.settings.topics || []).filter((t) => ids.includes(t));
  return picked.length ? picked : topicGroups().lessons.map((t) => t.id);
}

// ---- question types -------------------------------------------------------

function typeChoice(id) {
  return TYPE_CHOICES.find((c) => c.id === id) || TYPE_CHOICES[0];
}

/** The question formats a preset ("mixed" | "choice" | "typing") stands for. */
function presetTypes(key) {
  return state.catalog?.type_presets?.[key] || DEFAULT_PRESETS[key] || DEFAULT_PRESETS.mixed;
}

function qtypeLabel(id) {
  return state.catalog?.qtypes?.find((q) => q.id === id)?.label || QTYPE_LABELS[id] || id;
}

/** The formats of a preset that the mode can show (a mode may declare questionTypes, see engine.js). */
function modeFormats(mode, key) {
  const preset = presetTypes(key);
  const allowed = Array.isArray(mode.questionTypes) && mode.questionTypes.length ? mode.questionTypes : null;
  return allowed ? preset.filter((t) => allowed.includes(t)) : preset;
}

/** `settings.types` for the engine / QuestionFeed: the preset id, or an explicit list when the mode allows fewer formats. */
function resolveTypes(mode, key) {
  const formats = modeFormats(mode, key);
  if (formats.length === presetTypes(key).length) return key;
  return formats.length ? formats : [...mode.questionTypes];
}

/** One line on the setup screen when the mode leaves some of the chosen formats out. */
function modeTypesNote(mode, key) {
  const left = presetTypes(key).filter((t) => !modeFormats(mode, key).includes(t));
  if (!left.length) return "";
  return `${mode.name} skips ${left.map((t) => `“${qtypeLabel(t)}”`).join(" and ")} questions: they are too slow for this mode.`;
}

/** True when none of `topicIdList` has a question in any of `formats` (only checks what the server reported). */
function lacksFormats(topicIdList, formats) {
  const topics = (state.catalog?.topics || []).filter((t) => topicIdList.includes(t.id));
  if (!topics.length || topics.some((t) => !t.types)) return false;
  return !topics.some((t) => formats.some((f) => (t.types[f] || 0) > 0));
}

function modeColor(mode, i = 0) {
  return mode.color || MODE_COLORS[mode.id] || FALLBACK_COLORS[i % FALLBACK_COLORS.length];
}

function modeById(id) {
  return modes.find((m) => m.id === id);
}

function optionValues(mode) {
  const saved = state.settings.options[mode.id] || {};
  const out = {};
  for (const opt of mode.options || []) {
    const values = (opt.choices || []).map((c) => c[0]);
    out[opt.key] = values.includes(saved[opt.key]) ? saved[opt.key] : values.includes(opt.default) ? opt.default : values[0];
  }
  return out;
}

// ---------------------------------------------------------------------------
// Screen plumbing
// ---------------------------------------------------------------------------

function show(screen, { focus = true } = {}) {
  for (const layer of document.querySelectorAll(".confetti-layer")) layer.remove();
  app.replaceChildren(screen);
  window.scrollTo(0, 0);
  if (focus) {
    const target = screen.querySelector("[data-autofocus]") || screen.querySelector("h1");
    if (target) {
      if (!target.hasAttribute("tabindex") && !/^(BUTTON|INPUT|A)$/.test(target.tagName)) target.setAttribute("tabindex", "-1");
      try {
        target.focus({ preventScroll: true });
      } catch {
        /* ignore */
      }
    }
  }
}

function backButton(label, onClick) {
  return el("button", { class: "btn btn-ghost btn-sm back-btn", type: "button", onClick }, el("span", { "aria-hidden": "true", text: "◀ " }), label);
}

function logo(small = false) {
  return el(
    small ? "div" : "h1",
    { class: ["logo", small && "logo-sm"] },
    el("span", { class: "logo-py", text: "Py" }),
    el("span", { class: "logo-blooket", text: "Blooket" })
  );
}

function segmented({ label, choices, value, onChange, className = "" }) {
  const group = el("div", { class: ["segmented", className], role: "group", "aria-label": label });
  const buttons = choices.map((c) => {
    const btn = el(
      "button",
      {
        class: ["seg", c.className],
        type: "button",
        disabled: c.disabled,
        title: c.title,
        "aria-pressed": String(c.value === value),
        onClick: () => {
          for (const b of buttons) b.setAttribute("aria-pressed", String(b === btn));
          sfx("click");
          onChange(c.value);
        },
      },
      c.content
    );
    return btn;
  });
  group.append(...buttons);
  return group;
}

// ---------------------------------------------------------------------------
// Hosted games (screens live in host.js / play.js)
// ---------------------------------------------------------------------------

/** What host.js / play.js need from the shell. */
const hostEnv = {
  show,
  goHome: () => renderHome(),
  loadCatalog,
  /** The live settings object (always current: setup screens replace it when they save). */
  get settings() {
    return state.settings;
  },
  rememberPlayer({ playerName, avatar }) {
    if (typeof playerName === "string") state.settings.playerName = playerName.trim().slice(0, NAME_MAX);
    if (AVATARS.includes(avatar)) state.settings.avatar = avatar;
    saveSettings();
  },
  backButton,
  logo,
  segmented,
};

function openHost(opts) {
  renderHost(hostEnv, opts);
}

function openJoin(code) {
  renderJoin(hostEnv, { code });
}

// ---------------------------------------------------------------------------
// HOME
// ---------------------------------------------------------------------------

/**
 * A "Resume ..." button for a game remembered in this browser. The game may be long gone
 * (server restarted, host ended it): ask the server once and drop the button if so.
 */
function resumeButton(label, saved, onClick, forget) {
  const btn = el(
    "button",
    { class: "btn btn-sm btn-white classroom-resume", type: "button", onClick },
    el("span", { "aria-hidden": "true", text: "↩ " }),
    label,
    " ",
    el("b", { class: "classroom-resume-code", text: prettyCode(saved.code) })
  );
  playLookup(saved.code).catch((err) => {
    if (err && (err.reason === "not_found" || err.status === 404)) {
      forget();
      btn.remove();
    }
  });
  return btn;
}

function classroomButton({ color, icon, title, sub, onClick }) {
  return el(
    "button",
    { class: ["btn", "btn-xl", "classroom-btn", color], type: "button", onClick },
    el("span", { class: "classroom-icon", "aria-hidden": "true", text: icon }),
    el("span", { class: "classroom-text" }, el("span", { class: "classroom-title", text: title }), el("span", { class: "classroom-sub", text: sub }))
  );
}

function renderHome() {
  const statsLine = el("p", { class: "home-meta" });
  const updateMeta = () => {
    const lessons = state.catalog ? topicGroups().lessons.length : 0;
    const code = state.catalog ? state.catalog.code_enabled : true;
    statsLine.replaceChildren(
      el("span", { class: "meta-pill" }, "📚 ", lessons ? `${lessons} Unit 2 lesson topics` : "Unit 2 lessons"),
      el("span", { class: "meta-pill" }, code ? "⌨️ Type real code" : "⌨️ Fill in the blanks"),
      el("span", { class: "meta-pill diff-1" }, "★ Easy 100"),
      el("span", { class: "meta-pill diff-2" }, "★★ Medium 250"),
      el("span", { class: "meta-pill diff-3" }, "★★★ Hard 500")
    );
  };
  updateMeta();
  loadCatalog().then(updateMeta, () => {});

  const cards = modes.map((mode, i) =>
    el(
      "button",
      {
        class: "mode-card pop-in",
        type: "button",
        style: { "--mode-color": modeColor(mode, i), "--delay": `${i * 60}ms` },
        "aria-label": `${mode.name}: ${mode.tagline}`,
        onClick: () => {
          sfx("click");
          renderSetup(mode);
        },
      },
      el("span", { class: "mode-card-icon", "aria-hidden": "true", text: mode.icon }),
      el("span", { class: "mode-card-name", text: mode.name }),
      el("span", { class: "mode-card-tagline", text: mode.tagline }),
      el("span", { class: "mode-card-play", "aria-hidden": "true", text: "Play ▶" })
    )
  );

  const hosted = savedHost.get();
  const joined = savedPlayer.get();
  const classroom = el(
    "section",
    { class: "home-classroom", "aria-label": "Classroom games" },
    el(
      "div",
      { class: "classroom-cell pop-in" },
      classroomButton({
        color: "btn-yellow",
        icon: "🎮",
        title: "Host a game",
        sub: "Teachers: show a code on the projector",
        onClick: () => {
          sfx("click");
          openHost();
        },
      }),
      hosted ? resumeButton("Resume hosting", hosted, () => openHost({ resume: true }), () => savedHost.clear()) : null
    ),
    el(
      "div",
      { class: "classroom-cell pop-in", style: { "--delay": "70ms" } },
      classroomButton({
        color: "btn-green",
        icon: "🙋",
        title: "Join a game",
        sub: "Students: enter the code on your device",
        onClick: () => {
          sfx("click");
          openJoin();
        },
      }),
      joined ? resumeButton("Resume your game", joined, () => openJoin(joined.code), () => savedPlayer.clear()) : null
    )
  );

  const screen = el(
    "div",
    { class: "screen home-screen" },
    el(
      "header",
      { class: "home-topbar" },
      el(
        "button",
        { class: "btn btn-yellow btn-sm", type: "button", onClick: () => renderHighScores() },
        el("span", { "aria-hidden": "true", text: "🏆 " }),
        "High Scores"
      ),
      createMuteButton()
    ),
    el(
      "div",
      { class: "hero" },
      el("div", { class: "hero-blooks", "aria-hidden": "true" }, ["🐍", "🦊", "🐸", "🐙", "🦄"].map((a, i) => blook(a, { size: i === 0 ? 76 : 50, className: `hero-blook hb-${i}` }))),
      logo(),
      el("p", { class: "tagline", text: "Play live with your class or practice solo: pick answers, fill in the blanks and type real Python code!" }),
      statsLine
    ),
    classroom,
    el("h2", { class: "section-title", text: "Practice solo" }),
    el("div", { class: "mode-grid" }, cards),
    el(
      "footer",
      { class: "home-footer only-mouse" },
      el("p", null, "Tip: press ", el("kbd", { text: "1" }), "–", el("kbd", { text: "4" }), " to answer and ", el("kbd", { text: "Enter" }), " to continue."),
      el(
        "p",
        null,
        "Typing questions: ",
        el("kbd", { text: "Enter" }),
        " jumps to the next blank. In the code editor ",
        el("kbd", { text: "Ctrl" }),
        "+",
        el("kbd", { text: "Enter" }),
        " submits and ",
        el("kbd", { text: "Ctrl" }),
        "+",
        el("kbd", { text: "Shift" }),
        "+",
        el("kbd", { text: "Enter" }),
        " runs your code."
      )
    ),
    el("p", { class: "home-footer only-touch", text: "Typing questions have a symbol bar above the keyboard for ( ) [ ] : and more." })
  );
  show(screen, { focus: false });
}

// ---------------------------------------------------------------------------
// SETUP
// ---------------------------------------------------------------------------

function renderSetup(mode) {
  const s = state.settings;
  const draft = {
    playerName: s.playerName,
    avatar: s.avatar,
    topics: new Set(),
    types: s.types,
    difficulty: s.difficulty,
    options: optionValues(mode),
  };
  const color = modeColor(mode, modes.indexOf(mode));

  // ---- player -------------------------------------------------------------
  const preview = { node: blook(draft.avatar, { size: 72, className: "setup-blook pop-in" }) };
  const nameInput = el("input", {
    class: "text-input",
    id: "player-name",
    type: "text",
    maxlength: String(NAME_MAX),
    placeholder: "Player",
    autocomplete: "off",
    spellcheck: "false",
    value: draft.playerName,
    onInput: (e) => (draft.playerName = e.target.value.slice(0, NAME_MAX)),
    onKeydown: (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        startBtn.click();
      }
    },
  });
  const avatarButtons = AVATARS.map((a) =>
    el(
      "button",
      {
        class: "avatar-btn",
        type: "button",
        style: { "--blook-bg": avatarColor(a) },
        "aria-label": `Blook ${a}`,
        "aria-pressed": String(a === draft.avatar),
        dataset: { avatar: a },
        onClick: () => {
          draft.avatar = a;
          for (const b of avatarButtons) b.setAttribute("aria-pressed", String(b.dataset.avatar === a));
          const fresh = blook(a, { size: 72, className: "setup-blook pop-in" });
          preview.node.replaceWith(fresh);
          preview.node = fresh;
          sfx("click");
        },
      },
      el("span", { "aria-hidden": "true", text: a })
    )
  );

  const playerCard = el(
    "section",
    { class: "card setup-card player-card" },
    el("h2", { class: "card-title", text: "Your Blook" }),
    el(
      "div",
      { class: "player-row" },
      preview.node,
      el("div", { class: "field" }, el("label", { for: "player-name", text: "Player name" }), nameInput)
    ),
    el("div", { class: "avatar-grid", role: "group", "aria-label": "Choose your blook" }, avatarButtons)
  );

  // ---- how to play --------------------------------------------------------
  const howCard = el(
    "section",
    { class: "card setup-card how-card", style: { "--mode-color": color } },
    el("h2", { class: "card-title" }, el("span", { "aria-hidden": "true", text: "📜 " }), "How to play"),
    String(mode.description || mode.tagline || "")
      .split(/\n+/)
      .filter(Boolean)
      .map((p) => el("p", { text: p }))
  );

  // ---- topics -------------------------------------------------------------
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
  const lessonHeading = el("h3", { class: "topic-group-title" }, "Unit 2 lessons");
  const topicHint = el("p", { class: "hint hint-error", role: "alert", hidden: true, text: "Pick at least one topic to play." });
  const allBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "All", title: "Select every lesson topic", onClick: () => setLessonTopics() });
  const noneBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "None", title: "Clear the selection", onClick: () => setAllTopics(false) });
  const extrasBtn = el("button", {
    class: "btn btn-sm btn-white btn-toggle",
    type: "button",
    text: "+ extras",
    title: "Add or remove all the extra challenge topics",
    "aria-pressed": "false",
    hidden: true,
    onClick: () => toggleExtras(),
  });
  const topicsCard = el(
    "section",
    { class: "card setup-card topics-card" },
    el(
      "div",
      { class: "card-head" },
      el("h2", { class: "card-title" }, "Topics ", topicCount),
      el("div", { class: "card-head-actions" }, allBtn, noneBtn, extrasBtn)
    ),
    lessonHeading,
    lessonGrid,
    extraBox,
    topicHint
  );
  let chipButtons = [];
  let extraIds = [];
  let lessonIds = [];

  function refreshTopics() {
    const total = state.catalog?.topics.length || 0;
    topicCount.textContent = `${draft.topics.size} selected`;
    for (const b of chipButtons) b.setAttribute("aria-pressed", String(draft.topics.has(b.dataset.topic)));
    const pickedExtras = extraIds.filter((id) => draft.topics.has(id)).length;
    extraCount.textContent = `${pickedExtras}/${extraIds.length}`;
    extrasBtn.setAttribute("aria-pressed", String(extraIds.length > 0 && pickedExtras === extraIds.length));
    const ok = draft.topics.size > 0;
    topicHint.hidden = ok || total === 0;
    startBtn.disabled = !ok;
    startBtn.title = ok ? "" : "Pick at least one topic";
    refreshTypes();
  }

  function setLessonTopics() {
    draft.topics = new Set(lessonIds);
    sfx("click");
    refreshTopics();
  }

  function setAllTopics(on) {
    draft.topics = new Set(on ? topicIds() : []);
    sfx("click");
    refreshTopics();
  }

  function toggleExtras() {
    const allOn = extraIds.every((id) => draft.topics.has(id));
    for (const id of extraIds) {
      if (allOn) draft.topics.delete(id);
      else draft.topics.add(id);
    }
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
          if (draft.topics.has(t.id)) draft.topics.delete(t.id);
          else draft.topics.add(t.id);
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
    const topics = state.catalog.topics;
    if (!topics.length) {
      lessonGrid.replaceChildren(el("p", { class: "hint", text: "No question topics are available yet — check back soon!" }));
      lessonHeading.hidden = true;
      allBtn.disabled = noneBtn.disabled = true;
      refreshTopics();
      return;
    }
    const groups = topicGroups();
    lessonIds = groups.lessons.map((t) => t.id);
    extraIds = groups.extras.map((t) => t.id);
    draft.topics = new Set(selectedTopics());
    const lessonChips = groups.lessons.map(topicChip);
    const extraChips = groups.extras.map(topicChip);
    chipButtons = [...lessonChips, ...extraChips];
    lessonHeading.hidden = false;
    lessonGrid.replaceChildren(...lessonChips);
    extraGrid.replaceChildren(...extraChips);
    extraBox.hidden = extrasBtn.hidden = extraIds.length === 0;
    extraBox.open = extraIds.some((id) => draft.topics.has(id)); // never hide a chosen topic
    allBtn.disabled = noneBtn.disabled = false;
    refreshTopics();
  }

  function topicsLoading() {
    lessonGrid.replaceChildren(el("div", { class: "loading-inline" }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), "Loading topics…"));
  }

  function topicsFailed(err) {
    fillTypes(); // works from the built-in presets
    lessonGrid.replaceChildren(
      el(
        "div",
        { class: "load-error" },
        el("p", { text: `😵 Couldn't load topics: ${err?.message || "network error"}` }),
        el("button", {
          class: "btn btn-sm btn-yellow",
          type: "button",
          text: "Try again",
          onClick: () => {
            topicsLoading();
            loadCatalog().then(fillAll, topicsFailed);
          },
        })
      )
    );
  }

  // ---- question types -----------------------------------------------------
  const typesBody = el("div", { class: "types-body" });
  const typesBlurb = el("p", { class: "hint types-blurb", "aria-live": "polite" });
  const typesNote = el("p", { class: "hint types-note", hidden: true });
  const typesWarn = el("p", { class: "hint hint-warn types-warn", role: "status", hidden: true });
  const typesCard = el("section", { class: "card setup-card types-card" }, el("h2", { class: "card-title", text: "Question types" }), typesBody);

  /** Blurb, mode note and the "no typing questions in these topics" warning follow the choices made so far. */
  function refreshTypes() {
    const code = state.catalog ? state.catalog.code_enabled : true;
    const info = typeChoice(draft.types);
    typesBlurb.textContent = `${info.blurb(code)}${draft.types === "choice" ? "" : " Typed answers get more time."}`;
    const note = modeTypesNote(mode, draft.types);
    typesNote.textContent = note;
    typesNote.hidden = !note;
    const typed = modeFormats(mode, draft.types).filter((t) => t === "blanks" || t === "code");
    const warn = state.catalog && draft.types === "typing" && draft.topics.size > 0 && lacksFormats([...draft.topics], typed);
    typesWarn.textContent = warn ? "None of the topics you picked have typing questions yet, so you will get multiple choice instead." : "";
    typesWarn.hidden = !warn;
  }

  function fillTypes() {
    const code = state.catalog ? state.catalog.code_enabled : true;
    const usable = (id) => modeFormats(mode, id).length > 0;
    if (!usable(draft.types)) draft.types = "mixed";
    typesBody.replaceChildren(
      segmented({
        label: "Question types",
        className: "seg-types",
        value: draft.types,
        choices: TYPE_CHOICES.map((c) => ({
          value: c.id,
          disabled: !usable(c.id),
          title: usable(c.id) ? undefined : `${mode.name} can't use this`,
          content: [el("span", { class: "seg-icon", "aria-hidden": "true", text: c.icon }), el("span", { class: "seg-label", text: c.label }), el("span", { class: "seg-sub", text: c.sub(code) })],
        })),
        onChange: (v) => {
          draft.types = v;
          refreshTypes();
        },
      }),
      typesBlurb,
      typesNote,
      typesWarn
    );
    refreshTypes();
  }

  // ---- difficulty ---------------------------------------------------------
  let difficultyCard;
  if (mode.difficultySelectable === false) {
    difficultyCard = el(
      "section",
      { class: "card setup-card difficulty-card" },
      el("h2", { class: "card-title", text: "Difficulty" }),
      el(
        "div",
        { class: "note-box" },
        el("span", { class: "note-icon", "aria-hidden": "true", text: "📈" }),
        el("p", { text: mode.difficultyNote || "This mode picks the difficulty for you — questions get harder (and worth more) as you go!" })
      ),
      difficultyLegend()
    );
  } else {
    difficultyCard = el(
      "section",
      { class: "card setup-card difficulty-card" },
      el("h2", { class: "card-title", text: "Difficulty" }),
      segmented({
        label: "Difficulty",
        className: "seg-difficulty",
        value: draft.difficulty,
        choices: DIFFICULTY_CHOICES.map((d) => ({
          value: d.id,
          className: `seg-diff-${d.id}`,
          content: [
            el("span", { class: "seg-stars", "aria-hidden": "true", text: d.stars }),
            el("span", { class: "seg-label", text: d.label }),
            el("span", { class: "seg-sub", text: d.points }),
          ],
        })),
        onChange: (v) => (draft.difficulty = v),
      }),
      el("p", { class: "hint", text: "Harder questions are worth more points!" })
    );
  }

  // ---- mode options -------------------------------------------------------
  const optionsCard =
    mode.options && mode.options.length
      ? el(
          "section",
          { class: "card setup-card options-card" },
          el("h2", { class: "card-title", text: "Game options" }),
          mode.options.map((opt) =>
            el(
              "div",
              { class: "option-row" },
              el("h3", { class: "option-label", text: opt.label }),
              segmented({
                label: opt.label,
                value: draft.options[opt.key],
                choices: (opt.choices || []).map(([value, label]) => ({ value, content: el("span", { class: "seg-label", text: label }) })),
                onChange: (v) => (draft.options[opt.key] = v),
              })
            )
          )
        )
      : null;

  // ---- start --------------------------------------------------------------
  /** Remember the choices made on this screen (also when leaving via Back). */
  function commitDraft() {
    state.settings = {
      playerName: draft.playerName.trim().slice(0, NAME_MAX),
      avatar: draft.avatar,
      topics: draft.topics.size ? [...draft.topics] : state.settings.topics,
      types: draft.types,
      difficulty: draft.difficulty,
      options: { ...state.settings.options, [mode.id]: { ...draft.options } },
    };
    saveSettings();
  }

  const startBtn = el(
    "button",
    {
      class: "btn btn-green btn-xl start-btn",
      type: "button",
      disabled: true,
      onClick: () => {
        if (draft.topics.size === 0 || !state.catalog) return;
        const name = draft.playerName.trim().slice(0, NAME_MAX) || "Player";
        commitDraft();
        const ordered = topicIds().filter((t) => draft.topics.has(t));
        sfx("levelup");
        renderGame(mode, {
          topics: ordered,
          types: resolveTypes(mode, draft.types), // preset id, or a list when the mode allows fewer formats
          typesChoice: draft.types, // what the player picked ("mixed" | "choice" | "typing")
          difficulty: mode.difficultySelectable === false ? "mixed" : draft.difficulty,
          playerName: name,
          avatar: draft.avatar,
          options: { ...draft.options },
        });
      },
    },
    "Start Game ",
    el("span", { "aria-hidden": "true", text: "▶" })
  );

  const screen = el(
    "div",
    { class: "screen setup-screen", style: { "--mode-color": color } },
    el(
      "header",
      { class: "screen-header" },
      backButton("Back", () => {
        if (state.catalog) commitDraft();
        renderHome();
      }),
      el(
        "h1",
        { class: "screen-title" },
        el("span", { class: "title-icon", "aria-hidden": "true", text: mode.icon }),
        mode.name
      ),
      createMuteButton()
    ),
    el("p", { class: "screen-sub", text: mode.tagline }),
    el(
      "div",
      { class: "setup-grid" },
      el("div", { class: "setup-col" }, playerCard, howCard),
      el("div", { class: "setup-col" }, topicsCard, typesCard, difficultyCard, optionsCard)
    ),
    el("div", { class: "setup-footer" }, startBtn)
  );
  show(screen);

  const fillAll = () => {
    fillTopics();
    fillTypes();
  };
  if (state.catalog) fillAll();
  else {
    topicsLoading();
    typesBody.replaceChildren(el("div", { class: "loading-inline" }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), "Loading…"));
    loadCatalog().then(
      () => screen.isConnected && fillAll(),
      (err) => screen.isConnected && topicsFailed(err)
    );
  }
}

function difficultyLegend() {
  return el(
    "div",
    { class: "diff-legend" },
    DIFFICULTY_CHOICES.slice(0, 3).map((d) =>
      el("span", { class: `meta-pill diff-${d.id}` }, `${d.stars} ${d.label} ${d.points}`)
    )
  );
}

// ---------------------------------------------------------------------------
// GAME
// ---------------------------------------------------------------------------

function renderGame(mode, gameSettings) {
  const root = el("main", { class: "game-area", id: "game-root" });
  const quitBtn = el(
    "button",
    {
      class: "btn btn-red btn-sm quit-btn",
      type: "button",
      onClick: async () => {
        const handle = state.game;
        if (!handle) return;
        sfx("click");
        const ok = await confirmDialog({
          title: "Quit this game?",
          message: "Your progress in this game will be lost.",
          confirmText: "Quit",
          cancelText: "Keep playing",
          danger: true,
          icon: "🚪",
        });
        if (ok && state.game === handle) handle.quit();
      },
    },
    el("span", { "aria-hidden": "true", text: "✕ " }),
    "Quit"
  );
  const screen = el(
    "div",
    { class: "screen game-screen", style: { "--mode-color": modeColor(mode, modes.indexOf(mode)) } },
    el(
      "header",
      { class: "game-topbar" },
      el(
        "div",
        { class: "gt-mode" },
        el("span", { class: "gt-icon", "aria-hidden": "true", text: mode.icon }),
        el("span", { class: "gt-name", text: mode.name })
      ),
      el(
        "div",
        { class: "gt-player" },
        blook(gameSettings.avatar, { size: 32 }),
        el("span", { class: "gt-player-name", text: gameSettings.playerName })
      ),
      el("div", { class: "gt-actions" }, createMuteButton(), quitBtn)
    ),
    root
  );
  show(screen, { focus: false });

  const feed = new QuestionFeed({ topics: gameSettings.topics, difficulty: gameSettings.difficulty, types: gameSettings.types });
  const handle = startGame({
    root,
    mode,
    settings: gameSettings,
    topics: state.catalog?.topics || [],
    difficulties: state.catalog?.difficulties || [],
    feed,
  });
  state.game = handle;
  handle.done.then((outcome) => {
    if (state.game !== handle) return;
    state.game = null;
    if (outcome.status === "finished") renderResults(mode, gameSettings, outcome);
    else if (outcome.status === "quit") renderHome();
    else renderCrash(mode, gameSettings, outcome.error);
  });
}

function renderCrash(mode, gameSettings, error) {
  show(
    el(
      "div",
      { class: "screen crash-screen" },
      el(
        "div",
        { class: "card crash-card pop-in" },
        el("div", { class: "crash-icon", "aria-hidden": "true", text: "🐛" }),
        el("h1", { text: "Oops — the game hit a bug!" }),
        el("p", { class: "hint", text: String(error?.message || error || "Unknown error") }),
        el(
          "div",
          { class: "results-actions" },
          el("button", { class: "btn btn-green", type: "button", text: "Try again", onClick: () => renderGame(mode, gameSettings) }),
          el("button", { class: "btn btn-white", type: "button", text: "Home", onClick: () => renderHome() })
        )
      )
    )
  );
}

// ---------------------------------------------------------------------------
// RESULTS
// ---------------------------------------------------------------------------

function pct(correct, answered) {
  return answered ? Math.round((correct / answered) * 100) : 0;
}

function renderResults(mode, gameSettings, { result, stats }) {
  const accuracy = pct(stats.correct, stats.answered);
  const entry = {
    name: gameSettings.playerName,
    avatar: gameSettings.avatar,
    score: result.score,
    accuracy,
    date: new Date().toISOString(),
    topics: gameSettings.topics,
    types: gameSettings.typesChoice || "mixed",
    difficulty: gameSettings.difficulty,
  };
  const { rank, isBest } = recordHighScore(mode.id, entry);
  const outcomeClass = result.won === true ? "is-won" : result.won === false ? "is-lost" : "is-neutral";
  const color = modeColor(mode, modes.indexOf(mode));

  const scoreNum = el("span", { class: "score-num", text: "0" });
  const badge = isBest
    ? el("div", { class: "hs-badge pulse" }, "🏆 New high score!")
    : rank
      ? el("div", { class: "rank-badge" }, `#${rank} on your ${mode.name} leaderboard`)
      : null;

  const topicMeta = new Map((state.catalog?.topics || []).map((t) => [t.id, t]));
  const topicRows = Object.entries(stats.byTopic)
    .sort((a, b) => b[1].answered - a[1].answered)
    .map(([id, t]) => {
      const meta = topicMeta.get(id) || { name: id, icon: "🐍" };
      const p = pct(t.correct, t.answered);
      const tone = p >= 80 ? "good" : p >= 50 ? "ok" : "bad";
      return el(
        "div",
        { class: "topic-bar" },
        el("div", { class: "topic-bar-label" }, el("span", { "aria-hidden": "true", text: meta.icon }), " ", meta.name),
        el(
          "div",
          {
            class: "topic-bar-track",
            role: "progressbar",
            "aria-label": `${meta.name} accuracy`,
            "aria-valuemin": "0",
            "aria-valuemax": "100",
            "aria-valuenow": String(p),
          },
          el("div", { class: `topic-bar-fill tone-${tone}`, style: { "--w": `${p}%` } })
        ),
        el("div", { class: "topic-bar-value", text: `${t.correct}/${t.answered} · ${p}%` })
      );
    });

  const diffTiles = [1, 2, 3].map((d) => {
    const s = stats.byDifficulty[d] || { answered: 0, correct: 0, points: 0 };
    const info = DIFFICULTY_CHOICES[d - 1];
    return el(
      "div",
      { class: `diff-tile diff-${d}` },
      el("div", { class: "diff-tile-head" }, `${info.stars} ${info.label}`),
      el("div", { class: "diff-tile-points", text: s.points.toLocaleString() }),
      el("div", { class: "diff-tile-sub", text: `${s.correct}/${s.answered} correct` })
    );
  });

  const avgTime = stats.answered ? stats.totalTimeMs / stats.answered / 1000 : 0;
  const statTiles = [
    ["Questions", String(stats.answered), "❓"],
    ["Accuracy", `${accuracy}%`, "🎯"],
    ["Best streak", String(stats.bestStreak), "🔥"],
    ["Avg. time", stats.answered ? `${avgTime.toFixed(1)}s` : "—", "⏱️"],
  ].map(([label, value, icon]) =>
    el(
      "div",
      { class: "stat-tile" },
      el("div", { class: "stat-icon", "aria-hidden": "true", text: icon }),
      el("div", { class: "stat-value", text: value }),
      el("div", { class: "stat-label", text: label })
    )
  );

  const screen = el(
    "div",
    { class: ["screen", "results-screen", outcomeClass], style: { "--mode-color": color } },
    el(
      "section",
      { class: "card results-hero pop-in" },
      el("div", { class: "results-mode" }, el("span", { "aria-hidden": "true", text: mode.icon }), ` ${mode.name}`),
      el(
        "div",
        { class: "results-player" },
        blook(gameSettings.avatar, { size: 64, className: result.won === true ? "bounce" : "" }),
        el("span", { class: "results-player-name", text: gameSettings.playerName })
      ),
      el("h1", { class: "results-headline", text: result.headline }),
      el("div", { class: "results-score" }, scoreNum, el("span", { class: "score-label", text: mode.scoreLabel || "Score" })),
      badge,
      el(
        "div",
        { class: "results-actions" },
        el(
          "button",
          { class: "btn btn-green btn-lg", type: "button", "data-autofocus": true, onClick: () => renderGame(mode, gameSettings) },
          el("span", { "aria-hidden": "true", text: "↻ " }),
          "Play Again"
        ),
        el("button", { class: "btn btn-blue", type: "button", onClick: () => renderSetup(mode) }, el("span", { "aria-hidden": "true", text: "⚙ " }), "Change Settings"),
        el("button", { class: "btn btn-white", type: "button", onClick: () => renderHome() }, el("span", { "aria-hidden": "true", text: "⌂ " }), "Home")
      )
    ),
    el(
      "div",
      { class: "results-grid" },
      result.details.length
        ? el(
            "section",
            { class: "card results-card" },
            el("h2", { class: "card-title", text: "Game summary" }),
            el(
              "dl",
              { class: "details-list" },
              result.details.map(([k, v]) => el("div", { class: "details-row" }, el("dt", { text: k }), el("dd", { text: v })))
            )
          )
        : null,
      el("section", { class: "card results-card" }, el("h2", { class: "card-title", text: "Your stats" }), el("div", { class: "stat-grid" }, statTiles)),
      el(
        "section",
        { class: ["card", "results-card", result.details.length && "results-card-wide"] },
        el("h2", { class: "card-title", text: "Points by difficulty" }),
        el("div", { class: "diff-tiles" }, diffTiles)
      ),
      el(
        "section",
        { class: "card results-card topics-result" },
        el("h2", { class: "card-title", text: "Topic accuracy" }),
        topicRows.length ? el("div", { class: "topic-bars" }, topicRows) : el("p", { class: "hint", text: "No questions answered this time." })
      )
    )
  );
  show(screen);

  animateNumber(scoreNum, 0, result.score, 1100);
  if (result.won === true || isBest) {
    sfx("win");
    window.setTimeout(() => confetti(), 150);
  } else if (result.won === false) {
    sfx("lose");
  }
}

// ---------------------------------------------------------------------------
// HIGH SCORES
// ---------------------------------------------------------------------------

function renderHighScores(selectedId) {
  let current = modeById(selectedId) ? selectedId : modes[0]?.id;
  const listWrap = el("div", { class: "hs-list-wrap" });

  function difficultyText(d) {
    const info = DIFFICULTY_CHOICES.find((c) => c.id === d);
    return info ? info.label : "Mixed";
  }

  function fillList() {
    const mode = modeById(current);
    const scores = (loadHighScores()[current] || []).filter((e) => e && Number.isFinite(e.score));
    if (!scores.length) {
      listWrap.replaceChildren(
        el(
          "div",
          { class: "hs-empty" },
          el("div", { class: "hs-empty-icon", "aria-hidden": "true", text: mode.icon }),
          el("p", { text: `No ${mode.name} scores yet — go set one!` }),
          el("button", { class: "btn btn-green", type: "button", text: `Play ${mode.name}`, onClick: () => renderSetup(mode) })
        )
      );
      return;
    }
    const medals = ["🥇", "🥈", "🥉"];
    listWrap.replaceChildren(
      el(
        "ol",
        { class: "hs-list" },
        scores.map((e, i) => {
          const date = new Date(e.date);
          const dateText = Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
          const topicsText = Array.isArray(e.topics) ? `${e.topics.length} topic${e.topics.length === 1 ? "" : "s"}` : "";
          const typesText = e.types === "choice" || e.types === "typing" ? typeChoice(e.types).label : ""; // "mixed" (and old entries) say nothing
          return el(
            "li",
            { class: ["hs-row", i < 3 && `hs-top hs-top-${i + 1}`] },
            el("span", { class: "hs-rank", text: medals[i] || `#${i + 1}` }),
            blook(e.avatar || "🐸", { size: 40 }),
            el(
              "div",
              { class: "hs-who" },
              el("span", { class: "hs-name", text: e.name || "Player" }),
              el("span", { class: "hs-sub", text: [dateText, difficultyText(e.difficulty), typesText, topicsText, `${e.accuracy ?? 0}% acc.`].filter(Boolean).join(" · ") })
            ),
            el("span", { class: "hs-score" }, el("b", { text: Number(e.score).toLocaleString() }), el("small", { text: mode.scoreLabel || "Score" }))
          );
        })
      )
    );
  }

  const tabs = segmented({
    label: "Game mode",
    className: "hs-tabs",
    value: current,
    choices: modes.map((m) => ({
      value: m.id,
      content: [el("span", { "aria-hidden": "true", text: m.icon }), el("span", { class: "seg-label", text: m.name })],
    })),
    onChange: (v) => {
      current = v;
      fillList();
    },
  });

  const clearBtn = el("button", {
    class: "btn btn-sm btn-ghost",
    type: "button",
    text: "Clear all scores",
    onClick: async () => {
      const ok = await confirmDialog({
        title: "Clear all high scores?",
        message: "This removes every saved score for every mode on this device.",
        confirmText: "Clear",
        danger: true,
        icon: "🧹",
      });
      if (ok) {
        storageSet(HIGHSCORES_KEY, {});
        fillList();
        toast("High scores cleared", "success");
      }
    },
  });

  show(
    el(
      "div",
      { class: "screen hs-screen" },
      el(
        "header",
        { class: "screen-header" },
        backButton("Home", () => renderHome()),
        el("h1", { class: "screen-title" }, el("span", { class: "title-icon", "aria-hidden": "true", text: "🏆" }), "High Scores"),
        createMuteButton()
      ),
      el("section", { class: "card hs-card" }, tabs, listWrap, el("div", { class: "hs-footer" }, clearBtn))
    )
  );
  fillList();
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

loadCatalog().catch((err) => toast(`Couldn't load topics: ${err.message}`, "error", 5000));

/**
 * A shared link looks like  /?join=483920  (or  /#join=483920): open the Join screen with the code
 * filled in. Returns null for a normal visit, otherwise {code} (code is "" when the link had none).
 */
function joinLinkFromUrl() {
  const query = new URLSearchParams(window.location.search);
  const fromHash = /(?:^#|&)join=([^&]*)/.exec(window.location.hash || "");
  if (!query.has("join") && !fromHash) return null;
  return { code: String(query.get("join") || (fromHash && fromHash[1]) || "").replace(/\D/g, "").slice(0, 6) };
}

const joinLink = joinLinkFromUrl();
if (joinLink) {
  window.history.replaceState(null, "", window.location.pathname); // the code is only needed once
  openJoin(joinLink.code || undefined);
} else {
  renderHome();
}

// Exposed for debugging / tests.
window.PyBlooket = { state, modes, renderHome, renderSetup: (id) => renderSetup(modeById(id)), renderHighScores, formatTime, openHost, openJoin };
