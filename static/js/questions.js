/**
 * QuestionView: renders ONE question of ANY format as a `.q-card`, and is shared by the solo
 * game modes (engine.js `ctx.ask`) and the hosted games (play.js).
 *
 *   const view = createQuestionView(q, {
 *     onSubmit(response),               // once, when the player commits an answer
 *     onRun(code) -> Promise<RunResult>, // code questions: the "Run examples" button
 *     onChange(response),               // optional: every edit (use it to keep a draft)
 *     initial,                          // optional: a response to pre-fill (a saved draft)
 *     hotkeys: true, showMeta: true, submitLabel: "Submit",
 *   });
 *   container.append(view.el);  view.timerSlot / view.feedbackSlot are empty slots for the caller
 *   view.focus(); view.getResponse(); view.submit(); view.lock();
 *   view.showResult({correct, reveal, detail, ...}, {response}); view.destroy();
 *
 * Formats (q.qtype):
 *   choice  four coloured `.answer` buttons (keys 1-4), exactly the classic look
 *   blanks  the code snippet with an <input> for every ⟦n⟧ marker
 *   match   rows of "item -> <select>" (all rows must be chosen before Submit enables)
 *   code    prompt + examples + a real editor (highlighted <pre> under a transparent <textarea>),
 *           "Run examples" and Submit; on touch screens a symbol bar sits above the keyboard
 *
 * Responses: choice -> index | null, blanks -> string[], match -> (index | null)[], code -> string.
 * `showResult` marks right/wrong and shows the model answer; the server's answer payload
 * ({correct, reveal, detail, ...}) can be passed as is. See FRONTEND.md section 1.
 *
 * The code editor in a nutshell: the <textarea> and the highlighted <pre> sit in ONE grid cell,
 * so the <pre> sizes both of them and a single scroll container (`.qv-scroll`) scrolls them
 * together -- they can never drift apart. Both use the very same font metrics (16px mono,
 * 24px lines, no ligatures, no bold) so the caret and the selection line up with the colours.
 */

import { codeBlock, el, highlightPython, isModalOpen, renderInlineCode, sfx } from "./ui.js";

const QTYPES = ["choice", "blanks", "match", "code"];
const TYPE_LABEL = { blanks: "Fill in the blanks", match: "Matching", code: "Write the code" };
const TYPE_ICON = { blanks: "✍️", match: "🔗", code: "⌨️" };
const DIFF_STARS = { 1: "★", 2: "★★", 3: "★★★" };
const ANSWER_CLASSES = ["answer-yellow", "answer-blue", "answer-green", "answer-red"];
const MAX_CODE_CHARS = 6000;
const INDENT = "    ";
const MOD_KEY = /Mac|iPhone|iPad|iPod/.test(String(navigator.platform || navigator.userAgent || "")) ? "⌘" : "Ctrl";
const SYMBOLS = ['(', ')', '[', ']', '{', '}', '"', "'", ":", "=", "+", "-", "*", "/", "%", "<", ">", "!", ",", ".", "_", "#"];

let uid = 0;

const isCoarse = () => {
  try {
    return window.matchMedia("(pointer: coarse)").matches;
  } catch {
    return false;
  }
};

function isTypingTarget(target) {
  return !!target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

/** "2 of 3" style counter of true marks. */
const countTrue = (marks) => (Array.isArray(marks) ? marks.filter(Boolean).length : 0);

function difficultyBadge(q) {
  return el(
    "span",
    { class: `diff-badge diff-${q.difficulty}`, title: `${q.difficulty_label} question worth ${q.points} points` },
    el("span", { class: "diff-stars", "aria-hidden": "true", text: DIFF_STARS[q.difficulty] || "★" }),
    el("span", { text: `${q.difficulty_label} · ${q.points}` })
  );
}

// ---------------------------------------------------------------------------
// The view
// ---------------------------------------------------------------------------

export function createQuestionView(q, options = {}) {
  const o = { hotkeys: true, showMeta: true, submitLabel: "Submit", ...options };
  const qtype = QTYPES.includes(q.qtype) ? q.qtype : "choice";
  const id = `qv${++uid}`;
  const state = { submitted: false, locked: false, destroyed: false, response: undefined, result: null };
  const cleanups = [];

  const timerSlot = el("div", { class: "qv-timer-slot" });
  const feedbackSlot = el("div", { class: "q-feedback", "aria-live": "polite" });
  const status = el("div", { class: "sr-only", role: "status", "aria-live": "polite" });
  const submitBtn =
    qtype === "choice"
      ? null
      : el("button", { class: "btn btn-green qv-submit", type: "button", text: o.submitLabel, onClick: () => host.trySubmit() });

  /** What a format builder may call. */
  const host = {
    q,
    o,
    id,
    submitBtn,
    announce: (text) => {
      status.textContent = "";
      window.setTimeout(() => (status.textContent = text), 30);
    },
    onCleanup: (fn) => cleanups.push(fn),
    isLocked: () => state.locked || state.submitted,
    notify() {
      updateSubmit();
      if (typeof o.onChange === "function") {
        try {
          o.onChange(fmt.getResponse());
        } catch (err) {
          console.error("onChange failed", err);
        }
      }
    },
    trySubmit() {
      if (fmt.complete()) submit();
    },
    submit: () => submit(),
  };

  const fmt = BUILDERS[qtype](host);

  const meta = o.showMeta
    ? el(
        "div",
        { class: "q-meta" },
        qtype === "choice"
          ? el("span", { class: "topic-chip" }, el("span", { "aria-hidden": "true", text: q.topic_icon || "🐍" }), " ", q.topic_name || q.topic)
          : el(
              "span",
              { class: "qv-meta-left" },
              el("span", { class: "topic-chip" }, el("span", { "aria-hidden": "true", text: q.topic_icon || "🐍" }), " ", q.topic_name || q.topic),
              el("span", { class: "qv-type-pill" }, el("span", { "aria-hidden": "true", text: TYPE_ICON[qtype] }), " ", TYPE_LABEL[qtype])
            ),
        difficultyBadge(q)
      )
    : null;

  const card = el(
    "section",
    { class: ["q-card", "pop-in", `qv-type-${qtype}`], tabindex: "-1", "aria-label": `${q.difficulty_label || ""} ${q.topic_name || ""} question`.replace(/\s+/g, " ").trim() },
    meta,
    timerSlot,
    el("div", { class: "q-prompt", html: renderInlineCode(q.prompt) }),
    fmt.body,
    status,
    feedbackSlot
  );

  function updateSubmit() {
    if (submitBtn) submitBtn.disabled = state.locked || state.submitted || !fmt.complete();
  }

  function lock() {
    if (state.locked) return;
    state.locked = true;
    card.classList.add("qv-locked");
    fmt.setLocked(true);
    updateSubmit();
  }

  function submit() {
    if (state.submitted || state.destroyed) return;
    state.submitted = true;
    const response = fmt.getResponse();
    state.response = response;
    fmt.onCommit?.(response);
    lock();
    if (typeof o.onSubmit === "function") {
      try {
        o.onSubmit(response);
      } catch (err) {
        console.error("onSubmit failed", err);
      }
    }
  }

  function showResult(result = {}, { response } = {}) {
    lock();
    const reveal = result.reveal || (qtype === "choice" && Number.isInteger(result.answer) ? { answer: result.answer } : {});
    const resp = response !== undefined ? response : state.submitted ? state.response : fmt.getResponse();
    state.result = result;
    card.classList.add("answered");
    card.classList.toggle("is-correct", !!result.correct);
    card.classList.toggle("is-wrong", !result.correct);
    fmt.applyResult({ ...result, reveal, detail: result.detail || {} }, resp);
  }

  // number keys pick a choice
  if (o.hotkeys && qtype === "choice") {
    const onKey = (e) => {
      if (state.locked || state.submitted || !card.isConnected) return;
      if (e.defaultPrevented || e.repeat || e.ctrlKey || e.metaKey || e.altKey || isModalOpen() || isTypingTarget(e.target)) return;
      const n = Number(e.key);
      if (Number.isInteger(n) && n >= 1 && n <= (q.choices || []).length) {
        e.preventDefault();
        fmt.pick(n - 1);
      }
    };
    document.addEventListener("keydown", onKey);
    cleanups.push(() => document.removeEventListener("keydown", onKey));
  }

  if (o.initial !== undefined && o.initial !== null) fmt.setInitial?.(o.initial);
  updateSubmit();

  return {
    el: card,
    qtype,
    timerSlot,
    feedbackSlot,
    get submitted() {
      return state.submitted;
    },
    focus() {
      try {
        // a format may decline (returns false), e.g. code on a touch screen: no surprise keyboard
        if (state.locked || !fmt.focus || fmt.focus() === false) card.focus({ preventScroll: true });
      } catch {
        /* focus is best-effort */
      }
    },
    getResponse: () => fmt.getResponse(),
    submit,
    lock,
    showResult,
    destroy() {
      if (state.destroyed) return;
      state.destroyed = true;
      while (cleanups.length) {
        try {
          cleanups.pop()();
        } catch (err) {
          console.warn("cleanup failed", err);
        }
      }
    },
  };
}

// ---------------------------------------------------------------------------
// Format: choice
// ---------------------------------------------------------------------------

function buildChoice(host) {
  const { q } = host;
  let picked = null;
  const answers = (q.choices || []).map((choice, i) =>
    el(
      "button",
      {
        class: ["answer", ANSWER_CLASSES[i % 4]],
        type: "button",
        dataset: { index: i },
        "aria-label": `Answer ${i + 1}: ${choice}`,
        style: { "--i": i },
        onClick: () => pick(i),
      },
      el("span", { class: "answer-key", "aria-hidden": "true" }, el("b", { text: String(i + 1) })),
      el("span", { class: "answer-text", text: choice }),
      el("span", { class: "answer-mark", "aria-hidden": "true" })
    )
  );
  const baseLabel = answers.map((b) => b.getAttribute("aria-label"));

  function pick(i) {
    if (host.isLocked()) return;
    picked = i;
    host.notify();
    host.submit();
  }

  // a fragment keeps the DOM exactly as it always was: code block, then the answers grid
  const body = document.createDocumentFragment();
  body.append(...[q.code ? codeBlock(q.code) : null, el("div", { class: "answers" }, answers)].filter(Boolean));

  return {
    body,
    pick,
    getResponse: () => picked,
    complete: () => true,
    setInitial: (v) => {
      if (Number.isInteger(v)) picked = v;
    },
    setLocked: (locked) => {
      for (const b of answers) b.disabled = locked;
    },
    onCommit: (response) => {
      if (Number.isInteger(response) && answers[response]) {
        answers[response].classList.add("chosen");
        sfx("click");
      }
    },
    applyResult: (result, response) => {
      const right = result.reveal.answer;
      const chosen = Number.isInteger(response) ? response : null;
      answers.forEach((b, i) => {
        b.classList.remove("chosen", "correct", "wrong", "dim");
        b.querySelector(".answer-mark").textContent = "";
        b.setAttribute("aria-label", baseLabel[i]);
        if (i === right) {
          b.classList.add("correct");
          b.querySelector(".answer-mark").textContent = "✓";
          b.setAttribute("aria-label", `${baseLabel[i]} (correct answer)`);
        } else if (i === chosen) {
          b.classList.add("wrong");
          b.querySelector(".answer-mark").textContent = "✗";
          b.setAttribute("aria-label", `${baseLabel[i]} (your answer, wrong)`);
        } else b.classList.add("dim");
      });
    },
  };
}

// ---------------------------------------------------------------------------
// Format: blanks
// ---------------------------------------------------------------------------

/**
 * Turn `template` (code with ⟦n⟧ markers) into a DocumentFragment: the whole snippet is
 * highlighted in one go (so strings and f-strings colour correctly around a marker) and
 * every marker is then replaced by `makePiece(n)`.
 */
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

function lineNumbers(template) {
  const lines = template.replace(/\s+$/, "").split("\n").length;
  return Array.from({ length: lines }, (_, i) => i + 1).join("\n");
}

function templateBlock(template, makePiece, extraClass = "") {
  const body = el("code");
  body.append(renderTemplate(template, makePiece));
  return el(
    "div",
    { class: ["code-block", "qv-code16", extraClass], role: "group", "aria-label": "Python code" },
    el("pre", { class: "code-gutter", "aria-hidden": "true", text: lineNumbers(template) }),
    el("pre", { class: "code-body" }, body)
  );
}

function buildBlanks(host) {
  const { q } = host;
  const template = String(q.code || "").replace(/\s+$/, "");
  const specs = q.blanks || [];
  const inputs = [];
  const wraps = [];

  const makeBlank = (n) => {
    const spec = specs[n - 1] || { id: n, hint: "", width: 6 };
    const width = Math.min(Math.max(Number(spec.width) || 6, String(spec.hint || "").length, 3), 24) + 1;
    const input = el("input", {
      class: "qv-input",
      type: "text",
      autocomplete: "off",
      autocapitalize: "off",
      autocorrect: "off",
      spellcheck: "false",
      "data-gramm": "false",
      enterkeyhint: n >= specs.length ? "done" : "next",
      maxlength: 200,
      placeholder: spec.hint || "",
      "aria-label": `Blank ${n}${spec.hint ? `, hint: ${spec.hint}` : ""}`,
      style: { width: `calc(${width}ch + 18px)` },
    });
    input.addEventListener("input", () => host.notify());
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.isComposing) return;
      e.preventDefault();
      const i = inputs.indexOf(input);
      if (i < inputs.length - 1) {
        inputs[i + 1].focus();
        inputs[i + 1].select();
      } else if (complete()) host.submit();
      else {
        const empty = inputs.find((inp) => !inp.value.trim());
        if (empty) empty.focus();
      }
    });
    const wrap = el("span", { class: "qv-blank", dataset: { n } }, input);
    inputs[n - 1] = input;
    wraps[n - 1] = wrap;
    return wrap;
  };

  const block = templateBlock(template, makeBlank, "qv-blanks-code");
  const hint = el("span", { class: "qv-hint only-mouse", text: "Enter jumps to the next blank. Enter in the last one submits." });
  const actions = el("div", { class: "qv-actions" }, host.submitBtn, hint);
  const key = el("div", { class: "qv-key", hidden: true });
  const complete = () => inputs.length > 0 && inputs.every((inp) => inp.value.trim() !== "");

  return {
    body: el("div", { class: "qv-body" }, block, actions, key),
    getResponse: () => inputs.map((inp) => inp.value),
    complete,
    setInitial: (v) => {
      if (Array.isArray(v)) inputs.forEach((inp, i) => (inp.value = String(v[i] ?? "")));
    },
    focus: () => {
      if (isCoarse() || !inputs[0]) return false; // no surprise keyboard on a phone
      inputs[0].focus({ preventScroll: true });
      return true;
    },
    setLocked: (locked) => {
      for (const inp of inputs) inp.readOnly = locked;
    },
    applyResult: (result, response) => {
      const marks = result.detail.blanks;
      if (Array.isArray(response)) inputs.forEach((inp, i) => (inp.value = String(response[i] ?? "")));
      wraps.forEach((w, i) => {
        w.classList.remove("is-ok", "is-bad");
        if (marks && marks[i] === true) w.classList.add("is-ok");
        else if (marks && marks[i] === false) w.classList.add("is-bad");
        else if (!marks) w.classList.add(result.correct ? "is-ok" : "is-bad");
        inputs[i].setAttribute("aria-invalid", w.classList.contains("is-bad") ? "true" : "false");
      });
      const answers = result.reveal.blanks;
      const anyBad = wraps.some((w) => w.classList.contains("is-bad"));
      key.replaceChildren();
      key.hidden = !(anyBad && Array.isArray(answers));
      if (!key.hidden) {
        const fill = (n) => {
          const piece = el("span", { class: "qv-fill" });
          piece.innerHTML = highlightPython(String(answers[n - 1] ?? ""));
          return piece;
        };
        key.append(el("div", { class: "qv-key-title", text: "Right answer" }), templateBlock(template, fill));
      }
      if (marks) host.announce(`${countTrue(marks)} of ${marks.length} blanks correct.`);
    },
  };
}

// ---------------------------------------------------------------------------
// Format: match
// ---------------------------------------------------------------------------

const LOOKS_LIKE_CODE = /[()[\]{}"'=+\-*/%<>_.:,]|^\d|^(True|False|None)$/;

function buildMatch(host) {
  const { q } = host;
  const spec = q.match || { items: [], options: [] };
  const selects = [];
  const rows = [];

  const block = q.code ? codeBlock(q.code) : null;
  // On a phone a dropdown only gets half the row: stack every row when any option is long.
  const longOptions = spec.options.some((opt) => opt.length > 14);
  const list = el(
    "div",
    { class: "qv-match", role: "group", "aria-label": "Match each item" },
    spec.items.map((item, i) => {
      const select = el(
        "select",
        { class: "qv-select", "aria-label": `Match for ${item}` },
        el("option", { value: "", text: "Choose…", disabled: true, selected: true }),
        spec.options.map((opt, j) => el("option", { value: String(j), text: opt }))
      );
      select.addEventListener("change", () => host.notify());
      const mark = el("span", { class: "qv-mark", "aria-hidden": "true" });
      const fix = el("div", { class: "qv-fix", hidden: true });
      const row = el(
        "div",
        { class: ["qv-match-row", item.length > 13 || longOptions ? "is-long" : ""] },
        el("div", { class: ["qv-match-item", LOOKS_LIKE_CODE.test(item) ? "is-code" : ""], text: item }),
        el("div", { class: "qv-match-pick" }, select, mark),
        fix
      );
      selects[i] = select;
      rows[i] = { row, mark, fix, select };
      return row;
    })
  );
  const actions = el("div", { class: "qv-actions" }, host.submitBtn, el("span", { class: "qv-hint", text: "Choose an answer for every row." }));

  return {
    body: el("div", { class: "qv-body" }, block, list, actions),
    getResponse: () => selects.map((s) => (s.value === "" ? null : Number(s.value))),
    complete: () => selects.length > 0 && selects.every((s) => s.value !== ""),
    setInitial: (v) => {
      if (Array.isArray(v)) selects.forEach((s, i) => (s.value = Number.isInteger(v[i]) ? String(v[i]) : ""));
    },
    focus: () => false,
    setLocked: (locked) => {
      for (const s of selects) s.disabled = locked;
    },
    applyResult: (result, response) => {
      const marks = result.detail.match;
      const right = result.reveal.match;
      rows.forEach(({ row, mark, fix, select }, i) => {
        if (Array.isArray(response) && Number.isInteger(response[i])) select.value = String(response[i]);
        const ok = marks ? marks[i] === true : null;
        row.classList.remove("is-ok", "is-bad");
        fix.hidden = true;
        if (ok === null) return;
        row.classList.add(ok ? "is-ok" : "is-bad");
        mark.textContent = ok ? "✓" : "✗";
        if (!ok && Array.isArray(right) && spec.options[right[i]] !== undefined) {
          fix.hidden = false;
          fix.replaceChildren("Right answer: ", el("b", { text: spec.options[right[i]] }));
        }
      });
      if (marks) host.announce(`${countTrue(marks)} of ${marks.length} matches correct.`);
    },
  };
}

// ---------------------------------------------------------------------------
// Format: code (examples, editor, Run, results)
// ---------------------------------------------------------------------------

/** One <li> of a result table. */
function caseItem(c, final) {
  const ok = !!c.ok;
  const rows = [];
  const add = (term, value, cls = "") =>
    rows.push(el("dt", { text: term }), el("dd", {}, el("pre", { class: cls, text: value === "" ? "(nothing)" : value })));
  if (!ok) {
    add("Expected", String(c.expected ?? ""));
    if (!c.error) add("You got", String(c.got ?? ""));
  }
  if (c.error) add("Error", String(c.error), "is-error");
  if (c.stdout && !ok && c.stdout !== c.got) add("Printed", String(c.stdout));
  return el(
    "li",
    { class: ["qv-case", ok ? "is-ok" : "is-bad"] },
    el("span", { class: "qv-case-mark", "aria-hidden": "true", text: ok ? "✓" : "✗" }),
    el(
      "div",
      { class: "qv-case-body" },
      el(
        "div",
        { class: "qv-case-label" },
        el("span", { class: "sr-only", text: ok ? "Passed: " : "Failed: " }),
        el("code", { text: c.label || "test" }),
        ok && final && c.got ? el("span", { class: "qv-case-got", text: `→ ${String(c.got).replace(/\s+/g, " ")}` }) : null,
        c.hidden ? el("span", { class: "qv-tag", text: "hidden test" }) : null
      ),
      rows.length ? el("dl", { class: "qv-io" }, rows) : null
    )
  );
}

const STATUS_ICON = { syntax_error: "🛠️", timeout: "⏱️", rejected: "🚫", requirements: "☝️", empty: "✍️", error: "⚠️", ok: "✅" };

/**
 * Render a RunResult (a "Run examples" reply or the final grading detail) into `panel`.
 * final=false: Run button (examples only, never an answer); final=true: the graded answer.
 */
function renderRunResult(panel, res, { final = false, solution = null } = {}) {
  panel.replaceChildren();
  panel.removeAttribute("aria-busy");
  const nodes = [];
  const r = res && typeof res === "object" ? res : {};
  let cases = Array.isArray(r.cases) ? r.cases : [];
  const status = r.status || (cases.length ? "ok" : "");
  // an endless loop makes every later case "(not run)": that is noise, the message says it all
  if (status === "timeout") cases = cases.filter((c) => c.error !== "(not run)");
  if (status) {
    const passed = Number(r.passed) || 0;
    const total = Number(r.total) || cases.length;
    let tone = "bad";
    let icon = STATUS_ICON[status] || "ℹ️";
    let message = String(r.message || "");
    if (status === "ok") {
      const all = total > 0 && passed === total;
      if (final) {
        tone = r.correct ? "ok" : "bad";
        if (!r.correct) icon = passed > 0 ? "🤔" : "❌";
      } else {
        tone = all ? "ok" : "warn";
        if (!all) icon = "🤔";
        message = all
          ? `${total === 1 ? "The example passed" : `All ${total} examples passed`}. Press Submit when you're ready!`
          : `${passed} of ${total} example${total === 1 ? "" : "s"} passed. Keep going!`;
      }
    } else if (status === "requirements" || status === "empty") tone = "warn";
    nodes.push(
      el(
        "div",
        { class: ["qv-msg", `qv-msg-${tone}`] },
        el("span", { class: "qv-msg-icon", "aria-hidden": "true", text: icon }),
        el("span", { class: "qv-msg-text", text: message || "Something went wrong." })
      )
    );
  }
  if (cases.length) {
    nodes.push(el("div", { class: "qv-cases-title", text: final ? "Tests" : "Examples" }));
    nodes.push(el("ul", { class: "qv-cases" }, cases.map((c) => caseItem(c, final))));
  }
  if (final && typeof solution === "string" && solution.trim()) {
    nodes.push(el("div", { class: "qv-solution" }, el("div", { class: "qv-key-title", text: "One way to do it:" }), codeBlock(solution)));
  }
  panel.append(...nodes);
  panel.hidden = nodes.length === 0;
}

function buildCode(host) {
  const { q, o } = host;
  const task = q.task || {};
  const coarse = isCoarse();
  const hintId = `${host.id}-hint`;
  let runToken = 0;
  let running = false;

  // ---- examples ------------------------------------------------------------
  const examples = Array.isArray(task.examples) ? task.examples : [];
  const exBox = el("div", { class: "qv-examples" }, el("div", { class: "qv-ex-title", text: examples.length === 1 ? "Example" : "Examples" }));
  if (examples.length) {
    exBox.append(
      el(
        "ul",
        { class: "qv-ex-list" },
        examples.map((ex) => {
          const stdin = Array.isArray(ex.stdin) ? ex.stdin : [];
          const label = String(ex.label || "run it");
          const showInput = stdin.length && !/input/i.test(label);
          return el(
            "li",
            { class: "qv-ex" },
            el("code", { class: "qv-ex-label", text: label }),
            showInput ? el("span", { class: "qv-ex-input", text: `input: ${stdin.join(", ")}` }) : null,
            el("span", { class: "qv-ex-arrow", "aria-label": "gives", text: "→" }),
            el("pre", { class: "qv-ex-expected", text: String(ex.expected ?? "") })
          );
        })
      )
    );
  }
  const hidden = Number(task.hidden_tests) || 0;
  const foot = [];
  if (hidden > 0) foot.push(`${hidden} hidden test${hidden === 1 ? "" : "s"} will also be checked.`);
  if (task.note) foot.push(String(task.note));
  if (foot.length) exBox.append(el("div", { class: "qv-ex-foot", text: foot.join(" ") }));

  // ---- editor --------------------------------------------------------------
  const editor = createEditor({
    value: typeof o.initial === "string" ? o.initial : String(task.starter || ""),
    label: "Your code",
    describedBy: hintId,
    maxLength: MAX_CODE_CHARS,
    coarse,
    onInput: () => host.notify(),
    onSubmit: () => host.trySubmit(),
    onRun: () => run(),
  });

  host.onCleanup(() => editor.destroy());

  // ---- buttons + results ---------------------------------------------------
  const panel = el("div", { class: "qv-run", "aria-live": "polite", hidden: true });
  const runBtn =
    typeof o.onRun === "function"
      ? el("button", { class: "btn btn-blue qv-run-btn", type: "button", onClick: () => run() }, el("span", { "aria-hidden": "true", text: "▶ " }), "Run examples")
      : null;
  const hint = el("div", { class: "qv-hint-block", id: hintId },
    el("span", { class: "only-mouse", text: `${MOD_KEY}+Enter submits${runBtn ? ` · ${MOD_KEY}+Shift+Enter runs` : ""} · Tab indents · Esc then Tab leaves the editor` }),
    el("span", { class: "only-touch", text: "Use the symbol bar above the keyboard for ( ) [ ] : and more." })
  );
  const actions = el("div", { class: "qv-actions" }, runBtn, host.submitBtn);

  async function run() {
    if (!runBtn || running || host.isLocked()) return;
    running = true;
    const token = ++runToken;
    runBtn.disabled = true;
    runBtn.replaceChildren(el("span", { class: "spinner qv-spin", "aria-hidden": "true" }), "Running…");
    panel.hidden = false;
    panel.setAttribute("aria-busy", "true");
    panel.replaceChildren(el("div", { class: "qv-msg qv-msg-warn" }, el("span", { class: "qv-msg-icon", "aria-hidden": "true", text: "⏳" }), el("span", { text: "Running your code…" })));
    let res;
    try {
      res = await o.onRun(editor.getValue());
    } catch (err) {
      res = { status: "error", message: `Couldn't run your code: ${err && err.message ? err.message : "network problem"}. Try again.`, cases: [] };
    }
    if (!res || typeof res !== "object" || (!res.status && !Array.isArray(res.cases))) {
      res = { status: "error", message: (res && res.error) || "Couldn't run your code. Try again.", cases: [] };
    }
    running = false;
    runBtn.replaceChildren(el("span", { "aria-hidden": "true", text: "▶ " }), "Run examples");
    runBtn.disabled = host.isLocked();
    if (token !== runToken || host.isLocked()) return; // answered meanwhile: the final result wins
    renderRunResult(panel, res, { final: false });
    if (res && res.status === "ok" && res.total > 0 && res.passed === res.total) sfx("correct");
    else sfx("click");
  }

  return {
    body: el("div", { class: "qv-body" }, q.code ? codeBlock(q.code) : null, exBox, editor.el, hint, actions, panel),
    getResponse: () => editor.getValue(),
    complete: () => editor.getValue().trim() !== "",
    setInitial: (v) => {
      if (typeof v === "string") editor.setValue(v);
    },
    focus: () => {
      if (coarse) return false; // don't pop the keyboard open on a phone
      editor.focus();
      return true;
    },
    setLocked: (locked) => {
      editor.setReadOnly(locked);
      if (runBtn) runBtn.disabled = locked || running;
    },
    applyResult: (result, response) => {
      runToken++; // drop any run still in flight
      if (typeof response === "string" && response !== editor.getValue()) editor.setValue(response);
      const detail = result.detail || {};
      renderRunResult(panel, detail.status || detail.cases ? detail : { status: "", cases: [] }, { final: true, solution: result.reveal.solution });
    },
  };
}

// ---------------------------------------------------------------------------
// The code editor
// ---------------------------------------------------------------------------

function createEditor({ value = "", label, describedBy, maxLength, coarse, onInput, onSubmit, onRun }) {
  const ta = el("textarea", {
    class: "qv-ta",
    wrap: "off",
    rows: 1,
    spellcheck: "false",
    autocapitalize: "off",
    autocorrect: "off",
    autocomplete: "off",
    maxlength: maxLength,
    "aria-label": label,
    "aria-describedby": describedBy,
    placeholder: "Type your code here…",
    "data-gramm": "false",
    "data-gramm_editor": "false",
    "data-enable-grammarly": "false",
  });
  ta.value = value;
  const code = el("code");
  const hl = el("pre", { class: "qv-hl", "aria-hidden": "true" }, code);
  const gutter = el("pre", { class: "qv-gutter", "aria-hidden": "true" });
  const probe = el("span", { class: "qv-probe", "aria-hidden": "true", text: "0".repeat(40) });
  const stack = el("div", { class: "qv-stack" }, hl, ta);
  const scroller = el("div", { class: "qv-scroll" }, el("div", { class: "qv-sizer" }, gutter, stack), probe);
  const counter = el("div", { class: "qv-count", "aria-hidden": "true", hidden: true });
  const root = el("div", { class: "qv-editor" }, scroller, counter);
  const offs = [];
  const on = (target, type, fn, opts) => {
    target.addEventListener(type, fn, opts);
    offs.push(() => target.removeEventListener(type, fn, opts));
  };
  let lastText = null;
  let lastLines = 0;
  let escapeArmed = false;
  let caretPlaced = false;

  // ---- drawing -------------------------------------------------------------
  function render() {
    const text = ta.value;
    if (text === lastText) return;
    lastText = text;
    // The extra "\n " keeps a line box for a trailing empty line and one spare line, so the
    // <pre> is always taller than the textarea's content and the textarea never scrolls itself.
    code.innerHTML = highlightPython(text) + "\n ";
    const n = text.split("\n").length;
    if (n !== lastLines) {
      lastLines = n;
      gutter.textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
    }
    counter.hidden = text.length < maxLength - 800;
    counter.textContent = `${text.length.toLocaleString()} / ${maxLength.toLocaleString()}`;
    counter.classList.toggle("is-full", text.length >= maxLength - 50);
  }

  function metrics() {
    const cs = getComputedStyle(ta);
    return {
      lh: parseFloat(cs.lineHeight) || 24,
      ch: probe.getBoundingClientRect().width / 40 || 9.6,
      padL: parseFloat(cs.paddingLeft) || 0,
      padT: parseFloat(cs.paddingTop) || 0,
      padB: parseFloat(cs.paddingBottom) || 0,
    };
  }

  /** Scroll the editor (and, with the symbol bar open, the page) so the caret stays visible. */
  function revealCaret() {
    if (!ta.isConnected) return;
    const { lh, ch, padL, padT, padB } = metrics();
    const before = ta.value.slice(0, ta.selectionEnd);
    const row = before.split("\n").length - 1;
    const col = before.length - (before.lastIndexOf("\n") + 1);
    const gw = gutter.offsetWidth;
    const x = gw + padL + col * ch;
    const y = padT + row * lh;
    const margin = 28;
    if (x - margin < scroller.scrollLeft + gw) scroller.scrollLeft = Math.max(0, x - gw - margin);
    else if (x + ch + margin > scroller.scrollLeft + scroller.clientWidth) scroller.scrollLeft = x + ch + margin - scroller.clientWidth;
    if (y < scroller.scrollTop) scroller.scrollTop = Math.max(0, y - padT);
    else if (y + lh + padB > scroller.scrollTop + scroller.clientHeight) scroller.scrollTop = y + lh + padB - scroller.clientHeight;
    if (barOpen) {
      // keep the caret line clear of the fixed symbol bar / keyboard
      const vv = window.visualViewport;
      const top = scroller.getBoundingClientRect().top + (y - scroller.scrollTop);
      const bottomLimit = (vv ? vv.offsetTop + vv.height : window.innerHeight) - bar.offsetHeight - 12;
      if (top + lh > bottomLimit) window.scrollBy(0, top + lh - bottomLimit);
    }
  }

  // ---- editing helpers (go through execCommand so Ctrl+Z keeps working) ----------
  function replace(start, end, text, selStart = start + text.length, selEnd = selStart) {
    if (ta.readOnly) return false;
    const value = ta.value;
    const expected = value.slice(0, start) + text + value.slice(end);
    if (expected.length > maxLength) return false;
    ta.setSelectionRange(start, end);
    let ok = false;
    try {
      ok = text === "" ? document.execCommand("delete") : document.execCommand("insertText", false, text);
    } catch {
      ok = false;
    }
    if (!ok || ta.value !== expected) {
      ta.value = expected; // fallback: works everywhere, but starts a new undo step
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    }
    ta.setSelectionRange(selStart, selEnd);
    return true;
  }

  const lineStartOf = (pos) => ta.value.lastIndexOf("\n", pos - 1) + 1;

  function indent() {
    const v = ta.value;
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    if (!v.slice(s, e).includes("\n")) return void replace(s, e, INDENT);
    const from = lineStartOf(s);
    const to = e > s && v[e - 1] === "\n" ? e - 1 : e;
    const lines = v.slice(from, to).split("\n");
    const out = lines.map((l) => (l.length ? INDENT + l : l));
    const added = out.reduce((n, l, i) => n + (l.length - lines[i].length), 0);
    replace(from, to, out.join("\n"), s + (lines[0].length ? INDENT.length : 0), e + added);
  }

  function outdent() {
    const v = ta.value;
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    const from = lineStartOf(s);
    const to = e > s && v[e - 1] === "\n" ? e - 1 : e;
    const lines = v.slice(from, to).split("\n");
    const cut = lines.map((l) => (/^ {1,4}/.exec(l) || /^\t/.exec(l) || [""])[0].length);
    if (!cut.some(Boolean)) return;
    const out = lines.map((l, i) => l.slice(cut[i]));
    const removed = cut.reduce((a, b) => a + b, 0);
    replace(from, to, out.join("\n"), Math.max(from, s - cut[0]), Math.max(from, e - removed));
  }

  function newline() {
    const v = ta.value;
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    const before = v.slice(lineStartOf(s), s);
    let pad = /^[ \t]*/.exec(before)[0];
    // a line that ends with ":" (ignoring a trailing comment) opens a block
    if (/:\s*(#.*)?$/.test(before.replace(/^\s+/, "")) && !/^\s*#/.test(before)) pad += INDENT;
    replace(s, e, "\n" + pad);
  }

  function smartBackspace() {
    const s = ta.selectionStart;
    if (s !== ta.selectionEnd) return false;
    const before = ta.value.slice(lineStartOf(s), s);
    if (before.length < 2 || !/^ +$/.test(before)) return false;
    const n = before.length % INDENT.length || INDENT.length;
    return replace(s - n, s, "");
  }

  function insertText(text) {
    replace(ta.selectionStart, ta.selectionEnd, text);
  }

  // ---- events --------------------------------------------------------------
  on(ta, "input", () => {
    if (ta.value.includes("\t")) {
      // tabs would break the 4-space world of the editor: turn them into spaces
      const caret = ta.selectionStart;
      const tabsBefore = (ta.value.slice(0, caret).match(/\t/g) || []).length;
      ta.value = ta.value.replace(/\t/g, INDENT);
      ta.setSelectionRange(caret + tabsBefore * (INDENT.length - 1), caret + tabsBefore * (INDENT.length - 1));
    }
    render();
    revealCaret();
    if (typeof onInput === "function") onInput(ta.value);
  });
  on(ta, "scroll", () => {
    // the textarea itself must never scroll: the scroller does
    if (ta.scrollTop || ta.scrollLeft) {
      ta.scrollTop = 0;
      ta.scrollLeft = 0;
    }
  });
  on(ta, "keyup", (e) => {
    if (e.key.startsWith("Arrow") || ["Home", "End", "PageUp", "PageDown"].includes(e.key)) revealCaret();
  });
  on(ta, "paste", (e) => {
    const text = e.clipboardData && e.clipboardData.getData("text/plain");
    if (typeof text !== "string") return;
    e.preventDefault();
    const room = maxLength - (ta.value.length - (ta.selectionEnd - ta.selectionStart));
    replace(ta.selectionStart, ta.selectionEnd, text.replace(/\r\n?/g, "\n").replace(/\t/g, INDENT).slice(0, Math.max(0, room)));
  });
  on(ta, "keydown", (e) => {
    if (e.isComposing || e.keyCode === 229) return;
    if (["Shift", "Control", "Alt", "Meta"].includes(e.key)) return;
    const mod = e.ctrlKey || e.metaKey;
    if (e.key === "Enter" && mod) {
      e.preventDefault();
      if (e.shiftKey) onRun?.();
      else onSubmit?.();
      return;
    }
    if (e.key === "Escape") {
      escapeArmed = true; // the next Tab moves focus on instead of indenting
      return;
    }
    if (e.key === "Tab" && !mod && !e.altKey) {
      if (escapeArmed) {
        escapeArmed = false;
        return;
      }
      e.preventDefault();
      if (e.shiftKey) outdent();
      else indent();
      return;
    }
    escapeArmed = false;
    if (mod || e.altKey) return;
    if (e.key === "Enter") {
      e.preventDefault();
      newline();
    } else if (e.key === "Backspace" && smartBackspace()) e.preventDefault();
  });

  // ---- the touch symbol bar --------------------------------------------------
  let bar = null;
  let barOpen = false;
  if (coarse) {
    const keys = [
      ["Tab", indent, "Indent (4 spaces)"],
      ["⇤", outdent, "Un-indent"],
      ...SYMBOLS.map((s) => [s, () => insertText(s), `Insert ${s}`]),
    ];
    bar = el(
      "div",
      { class: "qv-symbar", role: "toolbar", "aria-label": "Code symbols", hidden: true },
      keys.map(([text, action, title]) => {
        const btn = el("button", { class: ["qv-symkey", text.length > 1 || text === "⇤" ? "is-wide" : ""], type: "button", "aria-label": title, text });
        // pointerdown + preventDefault: the tap never steals focus, so the keyboard stays open
        btn.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          ta.focus({ preventScroll: true });
          action();
        });
        btn.addEventListener("mousedown", (e) => e.preventDefault());
        btn.addEventListener("click", (e) => {
          if (e.detail === 0) action(); // keyboard / screen-reader activation
        });
        return btn;
      })
    );
    const place = () => {
      const vv = window.visualViewport;
      bar.style.bottom = `${vv ? Math.max(0, window.innerHeight - vv.height - vv.offsetTop) : 0}px`;
    };
    const open = () => {
      if (ta.readOnly) return;
      if (!bar.isConnected) document.body.append(bar);
      bar.hidden = false;
      barOpen = true;
      document.documentElement.classList.add("qv-bar-open");
      place();
    };
    const close = () => {
      barOpen = false;
      bar.hidden = true;
      document.documentElement.classList.remove("qv-bar-open");
    };
    on(ta, "focus", open);
    on(ta, "blur", () =>
      window.setTimeout(() => {
        if (document.activeElement !== ta) close();
      }, 0)
    );
    if (window.visualViewport) {
      on(window.visualViewport, "resize", () => barOpen && (place(), revealCaret()));
      on(window.visualViewport, "scroll", () => barOpen && place());
    }
    // a card removed while focused never fires blur: don't leave the bar behind
    const watchdog = window.setInterval(() => {
      if (barOpen && !ta.isConnected) close();
    }, 1000);
    offs.push(() => window.clearInterval(watchdog), () => (close(), bar.remove()));
  }

  render();

  return {
    el: root,
    getValue: () => ta.value,
    setValue(v) {
      ta.value = String(v);
      render();
      if (typeof onInput === "function") onInput(ta.value);
    },
    setReadOnly(locked) {
      ta.readOnly = locked;
      ta.setAttribute("aria-readonly", String(locked));
      root.classList.toggle("is-locked", locked);
      if (locked && bar) {
        barOpen = false;
        bar.hidden = true;
        document.documentElement.classList.remove("qv-bar-open");
      }
    },
    focus() {
      ta.focus({ preventScroll: true });
      if (!caretPlaced) {
        caretPlaced = true;
        ta.setSelectionRange(ta.value.length, ta.value.length);
      }
      revealCaret();
    },
    destroy() {
      while (offs.length) offs.pop()();
    },
  };
}

// ---------------------------------------------------------------------------

const BUILDERS = {
  choice: buildChoice,
  blanks: buildBlanks,
  match: buildMatch,
  code: buildCode,
};
