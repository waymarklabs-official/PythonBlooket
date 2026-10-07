/**
 * PyBlooket app shell: HOME -> SETUP -> GAME -> RESULTS, plus HIGH SCORES.
 * Game modes live in ./modes/ (see engine.js for the mode contract).
 */

import { fetchTopics, QuestionFeed } from "./api.js";
import { isAbortError, startGame } from "./engine.js";
import { prettyCode, savedHost, savedPlayer } from "./hostapi.js";
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

const DIFFICULTY_CHOICES = [
  { id: 1, label: "Easy", stars: "★", points: "100 pts" },
  { id: 2, label: "Medium", stars: "★★", points: "250 pts" },
  { id: 3, label: "Hard", stars: "★★★", points: "500 pts" },
  { id: "mixed", label: "Mixed", stars: "🎲", points: "100–500" },
];

const app = document.getElementById("app");

const state = {
  catalog: null, // {topics, difficulties}
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
    topics: Array.isArray(s.topics) ? s.topics.filter((t) => typeof t === "string") : null, // null = all
    difficulty: [1, 2, 3, "mixed"].includes(s.difficulty) ? s.difficulty : "mixed",
    options: s.options && typeof s.options === "object" ? s.options : {},
  };
}

function saveSettings() {
  storageSet(SETTINGS_KEY, state.settings);
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
// Catalogue (topics + difficulties from the server)
// ---------------------------------------------------------------------------

function loadCatalog() {
  if (state.catalog) return Promise.resolve(state.catalog);
  if (!state.catalogPromise) {
    state.catalogError = null;
    state.catalogPromise = fetchTopics()
      .then((data) => {
        state.catalog = data;
        return data;
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

/** The saved topic selection, restricted to topics the server actually has. */
function selectedTopics() {
  const ids = topicIds();
  if (!state.settings.topics) return ids;
  const picked = state.settings.topics.filter((t) => ids.includes(t));
  return picked.length ? picked : ids;
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
  settings: state.settings,
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

function renderHome() {
  const statsLine = el("p", { class: "home-meta" });
  const updateMeta = () => {
    const n = state.catalog?.topics.length;
    statsLine.replaceChildren(
      el("span", { class: "meta-pill" }, "🐍 ", n ? `${n} Python topics` : "Python topics"),
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
      el("p", { class: "tagline", text: "Answer Python questions, rack up points, and win the game!" }),
      statsLine
    ),
    el(
      "section",
      { class: "home-classroom", "aria-label": "Classroom games" },
      el(
        "button",
        { class: "btn btn-purple btn-xl classroom-btn", type: "button", onClick: () => { sfx("click"); openHost(); } },
        el("span", { "aria-hidden": "true", text: "🎮 " }),
        "Host a game"
      ),
      el(
        "button",
        { class: "btn btn-green btn-xl classroom-btn", type: "button", onClick: () => { sfx("click"); openJoin(); } },
        el("span", { "aria-hidden": "true", text: "🙋 " }),
        "Join a game"
      ),
      savedHost.get()
        ? el("button", { class: "btn btn-sm btn-white", type: "button", onClick: () => openHost({ resume: true }) }, `Resume hosting ${prettyCode(savedHost.get().code)}`)
        : null,
      savedPlayer.get()
        ? el("button", { class: "btn btn-sm btn-white", type: "button", onClick: () => openJoin(savedPlayer.get().code) }, `Rejoin game ${prettyCode(savedPlayer.get().code)}`)
        : null
    ),
    el("h2", { class: "section-title", text: "Practice solo" }),
    el("div", { class: "mode-grid" }, cards),
    el(
      "footer",
      { class: "home-footer only-mouse" },
      el("span", null, "Tip: press ", el("kbd", { text: "1" }), "–", el("kbd", { text: "4" }), " to answer and ", el("kbd", { text: "Enter" }), " to continue.")
    )
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
  const topicGrid = el("div", { class: "chip-grid", role: "group", "aria-label": "Topics" });
  const topicHint = el("p", { class: "hint hint-error", role: "alert", hidden: true, text: "Pick at least one topic to play." });
  const allBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "All", onClick: () => setAllTopics(true) });
  const noneBtn = el("button", { class: "btn btn-sm btn-white", type: "button", text: "None", onClick: () => setAllTopics(false) });
  const topicsCard = el(
    "section",
    { class: "card setup-card topics-card" },
    el(
      "div",
      { class: "card-head" },
      el("h2", { class: "card-title" }, "Topics ", topicCount),
      el("div", { class: "card-head-actions" }, allBtn, noneBtn)
    ),
    topicGrid,
    topicHint
  );
  let chipButtons = [];

  function refreshTopics() {
    const total = state.catalog?.topics.length || 0;
    topicCount.textContent = `${draft.topics.size}/${total}`;
    for (const b of chipButtons) b.setAttribute("aria-pressed", String(draft.topics.has(b.dataset.topic)));
    const ok = draft.topics.size > 0;
    topicHint.hidden = ok || total === 0;
    startBtn.disabled = !ok;
    startBtn.title = ok ? "" : "Pick at least one topic";
  }

  function setAllTopics(on) {
    draft.topics = new Set(on ? topicIds() : []);
    sfx("click");
    refreshTopics();
  }

  function fillTopics() {
    const topics = state.catalog.topics;
    if (!topics.length) {
      topicGrid.replaceChildren(el("p", { class: "hint", text: "No question topics are available yet — check back soon!" }));
      allBtn.disabled = noneBtn.disabled = true;
      refreshTopics();
      return;
    }
    draft.topics = new Set(selectedTopics());
    chipButtons = topics.map((t) =>
      el(
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
        el("span", { class: "chip-check", "aria-hidden": "true", text: "✓" })
      )
    );
    topicGrid.replaceChildren(...chipButtons);
    refreshTopics();
  }

  function topicsLoading() {
    topicGrid.replaceChildren(el("div", { class: "loading-inline" }, el("span", { class: "spinner spinner-sm", "aria-hidden": "true" }), "Loading topics…"));
  }

  function topicsFailed(err) {
    topicGrid.replaceChildren(
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
            loadCatalog().then(fillTopics, topicsFailed);
          },
        })
      )
    );
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
      el("div", { class: "setup-col" }, topicsCard, difficultyCard, optionsCard)
    ),
    el("div", { class: "setup-footer" }, startBtn)
  );
  show(screen);

  if (state.catalog) fillTopics();
  else {
    topicsLoading();
    loadCatalog().then(
      () => screen.isConnected && fillTopics(),
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

  const feed = new QuestionFeed({ topics: gameSettings.topics, difficulty: gameSettings.difficulty });
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
          return el(
            "li",
            { class: ["hs-row", i < 3 && `hs-top hs-top-${i + 1}`] },
            el("span", { class: "hs-rank", text: medals[i] || `#${i + 1}` }),
            blook(e.avatar || "🐸", { size: 40 }),
            el(
              "div",
              { class: "hs-who" },
              el("span", { class: "hs-name", text: e.name || "Player" }),
              el("span", { class: "hs-sub", text: [dateText, difficultyText(e.difficulty), topicsText, `${e.accuracy ?? 0}% acc.`].filter(Boolean).join(" · ") })
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

/** A shared link looks like  /?join=483920  -> open the Join screen with the code filled in. */
function joinCodeFromUrl() {
  const fromQuery = new URLSearchParams(window.location.search).get("join");
  const fromHash = /(?:^#|&)join=(\d{1,6})/.exec(window.location.hash || "");
  const code = String(fromQuery || (fromHash && fromHash[1]) || "").replace(/\D/g, "").slice(0, 6);
  return code || null;
}

const startCode = joinCodeFromUrl();
if (startCode) {
  window.history.replaceState(null, "", window.location.pathname);
  openJoin(startCode);
} else {
  renderHome();
}

// Exposed for debugging / tests.
window.PyBlooket = { state, modes, renderHome, renderSetup: (id) => renderSetup(modeById(id)), renderHighScores, formatTime, openHost, openJoin };
