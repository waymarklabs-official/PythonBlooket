/**
 * PyBlooket UI helpers — DOM builder, Python syntax highlighter, sounds,
 * confetti, toasts and other small shared bits. No dependencies.
 *
 * Everything here is also re-exported on the game context (ctx.el, ctx.sfx, ...)
 * so game modes rarely need to import this file directly.
 */

// ---------------------------------------------------------------------------
// Storage (every access wrapped: private mode / disabled storage must not crash)
// ---------------------------------------------------------------------------

export function storageGet(key, fallback = null) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------

const PROP_KEYS = new Set(["value", "checked", "disabled", "selected", "hidden", "indeterminate", "tabIndex"]);

/**
 * Tiny hyperscript helper.
 *   el('button', {class: 'btn', onClick: fn, dataset: {id: 3}, style: {color: 'red'}}, 'Hi', childNode)
 * props: class/className (string or array), text, html, style (object or string),
 * on<Event> handlers (onClick -> 'click'), dataset (object), value/checked/disabled/...
 * (set as properties), any other key -> attribute (true -> "", false/null/undefined -> skipped).
 * children: strings, numbers, Nodes, arrays (flattened); null/undefined/false are skipped.
 */
export function el(tag, props, ...children) {
  const node = document.createElement(tag);
  if (props !== null && props !== undefined && (typeof props !== "object" || props instanceof Node || Array.isArray(props))) {
    children.unshift(props);
    props = null;
  }
  if (props) {
    for (const [key, value] of Object.entries(props)) {
      if (value === undefined || value === null) continue;
      if (key === "class" || key === "className") {
        const cls = Array.isArray(value) ? value.filter(Boolean).join(" ") : value;
        if (cls) node.className = cls;
      } else if (key === "text") {
        node.textContent = String(value);
      } else if (key === "html") {
        node.innerHTML = value;
      } else if (key === "style") {
        if (typeof value === "string") node.style.cssText = value;
        else
          for (const [prop, v] of Object.entries(value)) {
            if (v === undefined || v === null) continue;
            if (prop.startsWith("--") || prop.includes("-")) node.style.setProperty(prop, String(v));
            else node.style[prop] = v;
          }
      } else if (key === "dataset") {
        for (const [k, v] of Object.entries(value)) if (v !== undefined && v !== null) node.dataset[k] = String(v);
      } else if (/^on[A-Z]/.test(key) && typeof value === "function") {
        node.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (PROP_KEYS.has(key)) {
        node[key] = value;
      } else if (value === true) {
        node.setAttribute(key, "");
      } else if (value !== false) {
        node.setAttribute(key, String(value));
      }
    }
  }
  appendChildren(node, children);
  return node;
}

function appendChildren(node, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false || child === true) continue;
    if (Array.isArray(child)) appendChildren(node, child);
    else node.append(child instanceof Node ? child : String(child));
  }
}

export function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** `**bold**` outside code spans: the markers must hug the text, so `a ** b ** c` stays maths. */
function boldMarkers(escaped) {
  return escaped.replace(/\*\*(?=\S)([^*]+?)(?<=\S)\*\*/g, "<strong>$1</strong>");
}

/** Turn `backtick` spans into <code> and **bold** into <strong>; everything else is HTML-escaped. Returns an HTML string. */
export function renderInlineCode(text) {
  const parts = String(text ?? "").split("`");
  // An odd number of backticks leaves the last one unmatched: show it literally.
  let html = "";
  for (let i = 0; i < parts.length; i++) {
    const isCode = i % 2 === 1;
    if (isCode && i === parts.length - 1) {
      html += "`" + escapeHtml(parts[i]);
    } else if (isCode) {
      html += `<code class="inline-code">${escapeHtml(parts[i])}</code>`;
    } else {
      html += boldMarkers(escapeHtml(parts[i]));
    }
  }
  return html;
}

/** "m:ss". Fractions round UP so countdowns never show 0:00 while time remains. */
export function formatTime(seconds) {
  const s = Math.max(0, Math.ceil(Number(seconds) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function prefersReducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ---------------------------------------------------------------------------
// Python syntax highlighting
// ---------------------------------------------------------------------------

const KEYWORDS = new Set(
  ("and as assert async await break class continue def del elif else except finally for from " +
    "global if import in is lambda nonlocal not or pass raise return try while with yield").split(" ")
);
const CONSTANTS = new Set(["True", "False", "None", "NotImplemented", "Ellipsis", "__name__"]);
const BUILTINS = new Set(
  ("print len range int str float bool list dict set tuple sorted reversed enumerate zip map filter " +
    "sum min max abs round type isinstance issubclass input open any all iter next super object repr " +
    "chr ord hex bin oct divmod pow hash id format frozenset getattr setattr hasattr delattr callable " +
    "slice property staticmethod classmethod vars dir bytes bytearray complex globals locals " +
    "Exception BaseException ValueError TypeError KeyError IndexError ZeroDivisionError NameError " +
    "AttributeError RuntimeError StopIteration RecursionError ArithmeticError LookupError " +
    "NotImplementedError AssertionError OverflowError ImportError ModuleNotFoundError " +
    "FileNotFoundError OSError UnboundLocalError").split(" ")
);
const STRING_PREFIX = /^(?:[rRbBuUfF]|[rR][bBfF]|[bBfF][rR])$/;
const NUMBER_RE =
  /^(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?[jJ]?)/;
const IDENT_RE = /^[A-Za-z_À-￿][\wÀ-￿]*/;
const OPERATOR_CHARS = "+-*/%=<>!&|^~@:";

function span(cls, text) {
  return `<span class="tok-${cls}">${escapeHtml(text)}</span>`;
}

/** Scan a string literal starting at `i` (at the opening quote). Returns end index (exclusive). */
function scanString(code, i) {
  const q = code[i];
  const triple = code.startsWith(q.repeat(3), i);
  const delim = triple ? q.repeat(3) : q;
  let j = i + delim.length;
  while (j < code.length) {
    const ch = code[j];
    if (ch === "\\") {
      j += 2; // even raw strings can't end on an escaped quote
      continue;
    }
    if (!triple && ch === "\n") return j; // unterminated: stop at end of line
    if (code.startsWith(delim, j)) return j + delim.length;
    j++;
  }
  return code.length;
}

/** Highlight an f-string literal: literal parts as strings, {expr} parts as code. */
function highlightFString(text, prefixLen) {
  const quoteLen = text.startsWith('"""', prefixLen) || text.startsWith("'''", prefixLen) ? 3 : 1;
  const head = text.slice(0, prefixLen + quoteLen);
  const closes = text.length - prefixLen >= quoteLen * 2 && text.endsWith(text.slice(prefixLen, prefixLen + quoteLen));
  const tail = closes ? text.slice(text.length - quoteLen) : "";
  const body = text.slice(head.length, text.length - tail.length);
  let out = span("str", head);
  let lit = "";
  let i = 0;
  const flush = () => {
    if (lit) out += span("str", lit);
    lit = "";
  };
  while (i < body.length) {
    const ch = body[i];
    if ((ch === "{" || ch === "}") && body[i + 1] === ch) {
      lit += ch + ch;
      i += 2;
      continue;
    }
    if (ch === "{") {
      // find the matching close brace, tracking nesting and nested quotes
      let depth = 1;
      let j = i + 1;
      let inQuote = null;
      while (j < body.length && depth > 0) {
        const c = body[j];
        if (inQuote) {
          if (c === inQuote) inQuote = null;
        } else if (c === "'" || c === '"') inQuote = c;
        else if (c === "{") depth++;
        else if (c === "}") depth--;
        j++;
      }
      flush();
      const inner = body.slice(i + 1, depth === 0 ? j - 1 : j);
      out += span("interp", "{") + `<span class="tok-fexpr">${highlightPython(inner)}</span>`;
      if (depth === 0) out += span("interp", "}");
      i = j;
      continue;
    }
    lit += ch;
    i++;
  }
  flush();
  if (tail) out += span("str", tail);
  return out;
}

/**
 * Highlight Python source. Returns an HTML string (all text escaped) with
 * <span class="tok-*"> wrappers: kw, const, builtin, str, interp, fexpr, num,
 * com, def (function/class names after def/class), self, call, deco, op.
 */
export function highlightPython(code) {
  code = String(code ?? "");
  let out = "";
  let i = 0;
  let prevWord = ""; // previous significant identifier/keyword
  let lineStart = true;
  while (i < code.length) {
    const ch = code[i];
    const rest = code.slice(i);

    if (ch === "\n") {
      out += "\n";
      i++;
      lineStart = true;
      prevWord = "";
      continue;
    }
    if (ch === " " || ch === "\t" || ch === "\r") {
      let j = i;
      while (j < code.length && (code[j] === " " || code[j] === "\t" || code[j] === "\r")) j++;
      out += code.slice(i, j);
      i = j;
      continue;
    }
    if (ch === "#") {
      let j = code.indexOf("\n", i);
      if (j === -1) j = code.length;
      out += span("com", code.slice(i, j));
      i = j;
      continue;
    }
    if (ch === "'" || ch === '"') {
      const end = scanString(code, i);
      out += span("str", code.slice(i, end));
      i = end;
      prevWord = "";
      lineStart = false;
      continue;
    }
    if (ch === "@" && lineStart) {
      const m = IDENT_RE.exec(code.slice(i + 1));
      if (m) {
        let j = i + 1 + m[0].length;
        while (code[j] === "." && IDENT_RE.test(code.slice(j + 1))) j += 1 + IDENT_RE.exec(code.slice(j + 1))[0].length;
        out += span("deco", code.slice(i, j));
        i = j;
        lineStart = false;
        continue;
      }
    }
    const num = /[0-9.]/.test(ch) ? NUMBER_RE.exec(rest) : null;
    if (num && num[0] !== ".") {
      out += span("num", num[0]);
      i += num[0].length;
      prevWord = "";
      lineStart = false;
      continue;
    }
    const id = IDENT_RE.exec(rest);
    if (id) {
      const word = id[0];
      const after = code[i + word.length];
      if (STRING_PREFIX.test(word) && (after === "'" || after === '"')) {
        const end = scanString(code, i + word.length);
        const lit = code.slice(i, end);
        out += /f/i.test(word) ? highlightFString(lit, word.length) : span("str", lit);
        i = end;
        prevWord = "";
        lineStart = false;
        continue;
      }
      let cls = null;
      if (prevWord === "def" || prevWord === "class") cls = "def";
      else if (KEYWORDS.has(word)) cls = "kw";
      else if (CONSTANTS.has(word)) cls = "const";
      else if (word === "self" || word === "cls") cls = "self";
      else if (BUILTINS.has(word) && code[i - 1] !== ".") cls = "builtin";
      else if (/^\s*\(/.test(code.slice(i + word.length, i + word.length + 40))) cls = "call";
      out += cls ? span(cls, word) : escapeHtml(word);
      prevWord = word;
      i += word.length;
      lineStart = false;
      continue;
    }
    if (OPERATOR_CHARS.includes(ch)) {
      let j = i;
      while (j < code.length && OPERATOR_CHARS.includes(code[j]) && j - i < 3) j++;
      out += span("op", code.slice(i, j));
      i = j;
      prevWord = "";
      lineStart = false;
      continue;
    }
    out += escapeHtml(ch);
    i++;
    lineStart = false;
    if (ch !== "." && ch !== ",") prevWord = "";
  }
  return out;
}

/** A <div class="code-block"> with line numbers + highlighted code. */
export function codeBlock(code) {
  const text = String(code ?? "").replace(/\s+$/, "");
  const lines = text.split("\n").length;
  const gutter = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  return el(
    "div",
    { class: "code-block", role: "group", "aria-label": "Python code" },
    el("pre", { class: "code-gutter", "aria-hidden": "true", text: gutter }),
    el("pre", { class: "code-body", tabindex: "0" }, el("code", { html: highlightPython(text) }))
  );
}

// ---------------------------------------------------------------------------
// Avatars ("blooks"), colours and bots
// ---------------------------------------------------------------------------

export const AVATARS = ["🐸", "🦊", "🐼", "🐙", "🦄", "🐲", "🐧", "🦁", "🐯", "🐨", "🐵", "🦉", "🐢", "🐳", "🦖", "🐝"];

export const AVATAR_COLORS = [
  "#4ade80", "#fb923c", "#e2e8f0", "#f472b6", "#c084fc", "#34d399", "#93c5fd", "#fbbf24",
  "#fdba74", "#cbd5e1", "#d6a77a", "#a78bfa", "#86efac", "#7dd3fc", "#a3e635", "#fde047",
];

/** Background colour for an avatar circle (stable per emoji). */
export function avatarColor(avatar) {
  const i = AVATARS.indexOf(avatar);
  if (i >= 0) return AVATAR_COLORS[i];
  let h = 0;
  for (const ch of String(avatar)) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

/** <span class="blook"> emoji in a coloured circle. size in px (default 48). */
export function blook(avatar, { size = 48, color, className = "" } = {}) {
  return el("span", {
    class: ["blook", className],
    style: { "--blook-size": `${size}px`, "--blook-bg": color || avatarColor(avatar) },
    "aria-hidden": "true",
    text: avatar,
  });
}

const BOT_FIRST = [
  "Byte", "Loop", "Pixel", "Code", "Syntax", "Lambda", "Tuple", "Debug", "Turbo", "Captain",
  "Sneaky", "Mega", "Cosmic", "Ninja", "Quantum", "Fuzzy", "Sir", "Lil", "Hyper", "Giga",
];
const BOT_LAST = [
  "Bandit", "Llama", "Panda", "Wizard", "Goblin", "Noodle", "Ranger", "Pickle", "Comet", "Taco",
  "Muffin", "Dragon", "Viper", "Gecko", "Biscuit", "Rocket", "Waffle", "Badger", "Sprout", "Yeti",
];
const BOT_COLORS = ["#ffcb2e", "#2f8cff", "#2fbf71", "#ff4d5e", "#a855f7", "#ff8a1f", "#ff5cb8", "#19c3c3"];

/** n bots: [{name, avatar, color}] with unique fun names. */
export function randomBots(n) {
  const names = new Set();
  const avatars = shuffle(AVATARS);
  const out = [];
  let guard = 0;
  while (out.length < n && guard++ < 5000) {
    const first = BOT_FIRST[Math.floor(Math.random() * BOT_FIRST.length)];
    const last = BOT_LAST[Math.floor(Math.random() * BOT_LAST.length)];
    let name = first + last;
    if (names.has(name)) {
      if (guard < 400) continue;
      name += out.length + 1;
    }
    names.add(name);
    out.push({
      name,
      avatar: avatars[out.length % avatars.length],
      color: BOT_COLORS[out.length % BOT_COLORS.length],
    });
  }
  return out;
}

// ---------------------------------------------------------------------------
// Toasts
// ---------------------------------------------------------------------------

let toastStack = null;

/** Small notification at the top of the screen. type: 'info' | 'success' | 'error' | 'warn'. */
export function toast(message, type = "info", ms = 2800) {
  if (!toastStack || !toastStack.isConnected) {
    toastStack = el("div", { class: "toast-stack", role: "status", "aria-live": "polite" });
    document.body.append(toastStack);
  }
  const icons = { info: "💡", success: "✅", error: "⚠️", warn: "⏳" };
  const node = el(
    "div",
    { class: `toast toast-${type}` },
    el("span", { class: "toast-icon", "aria-hidden": "true", text: icons[type] || icons.info }),
    el("span", { class: "toast-text", text: message })
  );
  toastStack.append(node);
  while (toastStack.children.length > 4) toastStack.firstElementChild.remove();
  window.setTimeout(() => {
    node.classList.add("toast-out");
    window.setTimeout(() => node.remove(), 300);
  }, ms);
  return node;
}

// ---------------------------------------------------------------------------
// Modal confirm dialog
// ---------------------------------------------------------------------------

let openModals = 0;

/** True while a modal dialog is open (the engine ignores answer hotkeys then). */
export function isModalOpen() {
  return openModals > 0;
}

/** Promise<boolean>. */
export function confirmDialog({
  title = "Are you sure?",
  message = "",
  confirmText = "Yes",
  cancelText = "Cancel",
  danger = false,
  icon = "🤔",
} = {}) {
  return new Promise((resolve) => {
    const previouslyFocused = document.activeElement;
    let closed = false;
    const close = (value) => {
      if (closed) return;
      closed = true;
      openModals = Math.max(0, openModals - 1);
      document.removeEventListener("keydown", onKey, true);
      overlay.classList.add("modal-out");
      window.setTimeout(() => overlay.remove(), 160);
      if (previouslyFocused && previouslyFocused.isConnected && previouslyFocused.focus) previouslyFocused.focus();
      resolve(value);
    };
    const cancelBtn = el("button", { class: "btn btn-white", type: "button", text: cancelText, onClick: () => close(false) });
    const okBtn = el("button", {
      class: ["btn", danger ? "btn-red" : "btn-green"],
      type: "button",
      text: confirmText,
      onClick: () => close(true),
    });
    const titleId = `modal-title-${Date.now()}`;
    const dialog = el(
      "div",
      { class: "modal-card pop-in", role: "dialog", "aria-modal": "true", "aria-labelledby": titleId },
      el("div", { class: "modal-icon", "aria-hidden": "true", text: icon }),
      el("h2", { class: "modal-title", id: titleId, text: title }),
      message ? el("p", { class: "modal-message", text: message }) : null,
      el("div", { class: "modal-actions" }, cancelBtn, okBtn)
    );
    const overlay = el("div", { class: "modal-overlay", onClick: (e) => e.target === overlay && close(false) }, dialog);
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close(false);
      } else if (e.key === "Tab") {
        // trap focus between the two buttons
        e.preventDefault();
        (document.activeElement === cancelBtn ? okBtn : cancelBtn).focus();
      } else if (!["Enter", " "].includes(e.key)) {
        e.stopPropagation(); // keep game hotkeys (1-4) from firing underneath
      }
    };
    openModals++;
    document.addEventListener("keydown", onKey, true);
    document.body.append(overlay);
    cancelBtn.focus();
  });
}

// ---------------------------------------------------------------------------
// Sound effects (tiny synthesized WebAudio beeps) + mute toggle
// ---------------------------------------------------------------------------

const MUTE_KEY = "pyblooket.muted";
let muted = storageGet(MUTE_KEY, false) === true;
let audioCtx = null;
let master = null;

export function isMuted() {
  return muted;
}

export function setMuted(value) {
  muted = !!value;
  storageSet(MUTE_KEY, muted);
  for (const btn of document.querySelectorAll(".mute-btn")) syncMuteButton(btn);
  window.dispatchEvent(new CustomEvent("pyblooket:mute", { detail: { muted } }));
}

export function toggleMute() {
  setMuted(!muted);
  if (!muted) sfx("click");
  return muted;
}

function syncMuteButton(btn) {
  btn.textContent = muted ? "🔇" : "🔊";
  btn.setAttribute("aria-pressed", String(muted));
  btn.setAttribute("aria-label", muted ? "Unmute sounds" : "Mute sounds");
  btn.title = muted ? "Sound off" : "Sound on";
}

/** A round icon button that toggles mute; all instances stay in sync. */
export function createMuteButton(extraClass = "") {
  const btn = el("button", { class: ["icon-btn", "mute-btn", extraClass], type: "button", onClick: () => toggleMute() });
  syncMuteButton(btn);
  return btn;
}

function getAudio() {
  try {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      audioCtx = new AC();
      master = audioCtx.createGain();
      master.gain.value = 0.5;
      master.connect(audioCtx.destination);
    }
    if (audioCtx.state === "suspended") audioCtx.resume().catch(() => {});
    return audioCtx;
  } catch {
    return null;
  }
}

function tone(ac, { f, t = 0, d = 0.12, type = "sine", g = 0.2, to = null }) {
  const start = ac.currentTime + t;
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(f, start);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, start + d);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(g, start + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + d);
  osc.connect(gain);
  gain.connect(master);
  osc.start(start);
  osc.stop(start + d + 0.03);
}

const SOUNDS = {
  click: [{ f: 880, d: 0.05, type: "triangle", g: 0.12 }],
  tick: [{ f: 1250, d: 0.04, type: "square", g: 0.05 }],
  correct: [
    { f: 784, d: 0.1, type: "triangle" },
    { f: 1047, t: 0.08, d: 0.1, type: "triangle" },
    { f: 1319, t: 0.16, d: 0.2, type: "triangle" },
  ],
  wrong: [
    { f: 220, d: 0.18, type: "sawtooth", g: 0.1, to: 180 },
    { f: 160, t: 0.16, d: 0.28, type: "sawtooth", g: 0.1, to: 110 },
  ],
  chest: [
    { f: 523, d: 0.08, type: "triangle", g: 0.15 },
    { f: 659, t: 0.06, d: 0.08, type: "triangle", g: 0.15 },
    { f: 784, t: 0.12, d: 0.08, type: "triangle", g: 0.15 },
    { f: 1047, t: 0.18, d: 0.12, type: "triangle", g: 0.15 },
    { f: 1568, t: 0.26, d: 0.25, type: "sine", g: 0.12 },
  ],
  hit: [
    { f: 180, d: 0.15, type: "square", g: 0.14, to: 60 },
    { f: 90, t: 0.02, d: 0.12, type: "sawtooth", g: 0.08, to: 40 },
  ],
  levelup: [
    { f: 523, d: 0.09, type: "square", g: 0.08 },
    { f: 659, t: 0.09, d: 0.09, type: "square", g: 0.08 },
    { f: 784, t: 0.18, d: 0.09, type: "square", g: 0.08 },
    { f: 1047, t: 0.27, d: 0.22, type: "square", g: 0.09 },
  ],
  win: [
    { f: 523, d: 0.12, type: "triangle" },
    { f: 659, t: 0.12, d: 0.12, type: "triangle" },
    { f: 784, t: 0.24, d: 0.12, type: "triangle" },
    { f: 1047, t: 0.36, d: 0.18, type: "triangle" },
    { f: 784, t: 0.54, d: 0.1, type: "triangle" },
    { f: 1047, t: 0.64, d: 0.45, type: "triangle", g: 0.22 },
  ],
  lose: [
    { f: 392, d: 0.2, type: "triangle", g: 0.16 },
    { f: 370, t: 0.22, d: 0.2, type: "triangle", g: 0.16 },
    { f: 349, t: 0.44, d: 0.2, type: "triangle", g: 0.16 },
    { f: 330, t: 0.66, d: 0.5, type: "triangle", g: 0.16, to: 300 },
  ],
};

/** Play a named sound: click, tick, correct, wrong, chest, hit, levelup, win, lose. */
export function sfx(name) {
  if (muted) return;
  const notes = SOUNDS[name];
  if (!notes) return;
  const ac = getAudio();
  if (!ac) return;
  try {
    for (const n of notes) tone(ac, n);
  } catch {
    /* audio is best-effort */
  }
}

// ---------------------------------------------------------------------------
// Confetti + number animation
// ---------------------------------------------------------------------------

const CONFETTI_COLORS = ["#ffcb2e", "#2f8cff", "#2fbf71", "#ff4d5e", "#a855f7", "#ff8a1f", "#ff5cb8", "#19c3c3", "#ffffff"];

/** Celebratory burst. opts: {count=140, x=0.5, y=0.35} (x/y are viewport fractions). */
export function confetti({ count = 140, x = 0.5, y = 0.35 } = {}) {
  if (prefersReducedMotion() || typeof Element.prototype.animate !== "function") return;
  const layer = el("div", { class: "confetti-layer", "aria-hidden": "true" });
  document.body.append(layer);
  const W = window.innerWidth;
  const H = window.innerHeight;
  const ox = W * x;
  const oy = H * y;
  let longest = 0;
  for (let i = 0; i < count; i++) {
    const w = 7 + Math.random() * 7;
    const piece = el("i", {
      class: "confetti-piece",
      style: {
        left: `${ox}px`,
        top: `${oy}px`,
        width: `${w}px`,
        height: `${w * (Math.random() < 0.3 ? 1 : 1.6)}px`,
        background: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        borderRadius: Math.random() < 0.3 ? "50%" : "2px",
      },
    });
    layer.append(piece);
    const angle = (-90 + (Math.random() - 0.5) * 140) * (Math.PI / 180);
    const speed = (0.55 + Math.random() * 0.75) * Math.min(W, 1100);
    const vx = Math.cos(angle) * speed;
    const vy = Math.sin(angle) * speed;
    const gravity = 1300;
    const duration = 1.6 + Math.random() * 1.3;
    const spin = (Math.random() - 0.5) * 1440;
    const frames = [];
    for (let k = 0; k <= 8; k++) {
      const t = (k / 8) * duration;
      const drag = 1 - Math.min(0.6, t * 0.25);
      frames.push({
        transform: `translate(${vx * t * drag}px, ${vy * t + 0.5 * gravity * t * t}px) rotate(${spin * (k / 8)}deg) rotateX(${k * 120}deg)`,
        opacity: k < 6 ? 1 : 1 - (k - 5) / 3,
      });
    }
    piece.animate(frames, { duration: duration * 1000, easing: "linear", fill: "forwards" });
    longest = Math.max(longest, duration);
  }
  window.setTimeout(() => layer.remove(), longest * 1000 + 200);
}

const numberAnimations = new WeakMap();

/** Count el's text from `from` to `to` over `ms` (ease-out). Returns a Promise. */
export function animateNumber(node, from, to, ms = 900) {
  const fmt = (v) => Math.round(v).toLocaleString();
  const prev = numberAnimations.get(node);
  if (prev) prev.cancelled = true;
  if (!node || prefersReducedMotion() || ms <= 0 || from === to) {
    if (node) node.textContent = fmt(to);
    return Promise.resolve();
  }
  const job = { cancelled: false };
  numberAnimations.set(node, job);
  return new Promise((resolve) => {
    const t0 = performance.now();
    const step = (now) => {
      if (job.cancelled) return resolve();
      const p = Math.min(1, (now - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      node.textContent = fmt(from + (to - from) * eased);
      if (p < 1) requestAnimationFrame(step);
      else {
        numberAnimations.delete(node);
        resolve();
      }
    };
    requestAnimationFrame(step);
  });
}
