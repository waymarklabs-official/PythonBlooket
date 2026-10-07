/**
 * PyBlooket backend client.
 *
 *   GET  /api/topics                       -> {topics: [...], difficulties: [...], type_presets, code_enabled, ...}
 *   GET  /api/questions?topics=&difficulty=&count=&types=  -> {questions: [...]}   (any of the four formats)
 *   POST /api/answer {id, response}        -> {correct, answer, points, explanation, qtype, reveal, detail}
 *   POST /api/run {id, code}               -> RunResult (the "Run examples" button of a code question)
 */

const BATCH_SIZE = 5;
const LOW_WATER = 2; // refill in the background when a buffer drops to this many
const RECENT_LIMIT = 60; // how many served questions to remember for de-duplication
const REQUEST_TIMEOUT_MS = 12000;
const CODE_TIMEOUT_MS = 40000; // typed code runs in a sandbox: allow for a busy server

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status; // HTTP status, or 0 for network failure / timeout
  }
}

async function request(url, { timeout = REQUEST_TIMEOUT_MS, ...options } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  let res;
  try {
    res = await fetch(url, { ...options, signal: ctrl.signal, headers: { Accept: "application/json", ...(options.headers || {}) } });
  } catch {
    throw new ApiError("Can't reach the PyBlooket server.", 0);
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) throw new ApiError((data && data.error) || `Server error (${res.status})`, res.status);
  if (!data) throw new ApiError("Bad response from server", res.status);
  return data;
}

/** -> {topics: [{id, name, icon, description, generators}], difficulties: [{id, label, points}]} */
export async function fetchTopics() {
  const data = await request("/api/topics");
  return { topics: data.topics || [], difficulties: data.difficulties || [] };
}

/**
 * -> {correct, answer, points, explanation, qtype, reveal, detail}.
 * response: choice -> index (null = ran out of time) | blanks -> string[] | match -> (index|null)[] | code -> string.
 */
export async function submitAnswer(id, response) {
  const typedCode = typeof response === "string";
  return request("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, response: response === undefined ? null : response }),
    timeout: typedCode ? CODE_TIMEOUT_MS : REQUEST_TIMEOUT_MS,
  });
}

/** Try typed code on a code question's visible examples (never counts as an answer). -> RunResult */
export async function runCode(id, code) {
  return request("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, code }),
    timeout: CODE_TIMEOUT_MS,
  });
}

/** Identity of a question for de-duplication: works for every format. */
function signature(q) {
  const parts = [q.qtype || "choice", q.prompt, q.code || "", [...(q.choices || [])].sort().join("\u0001")];
  if (Array.isArray(q.blanks)) parts.push(q.blanks.map((b) => `${b.hint}:${b.width}`).join("|"));
  if (q.match) parts.push([...q.match.items].join("\u0001"), [...q.match.options].sort().join("\u0001"));
  if (q.task) parts.push(q.task.starter || "", (q.task.examples || []).map((e) => e.label).join("\u0001"));
  return parts.join("\u0000");
}

/**
 * Prefetching question source. One buffer per difficulty key ('1', '2', '3',
 * 'mixed'), so modes that switch difficulty mid-game still get questions instantly.
 *
 *   const feed = new QuestionFeed({topics: ['strings'], difficulty: 'mixed', types: 'mixed'});
 *   const q = await feed.next();      // uses settings.difficulty
 *   const hard = await feed.next(3);  // per-call override
 */
export class QuestionFeed {
  constructor(settings = {}) {
    this.topics = Array.isArray(settings.topics) ? settings.topics : [];
    this.difficulty = settings.difficulty ?? "mixed";
    // "mixed" | "choice" | "typing" | array of formats; undefined lets the server decide (= mixed)
    const types = settings.types;
    this.types = Array.isArray(types) ? types.join(",") : typeof types === "string" ? types : "";
    this.buffers = new Map();
    this.inflight = new Map();
    this.recent = [];
    this.recentSet = new Set();
    this.closed = false;
  }

  key(difficulty) {
    const d = difficulty ?? this.difficulty;
    return [1, 2, 3].includes(Number(d)) ? String(Number(d)) : "mixed";
  }

  buffer(key) {
    if (!this.buffers.has(key)) this.buffers.set(key, []);
    return this.buffers.get(key);
  }

  /** Start filling a buffer without waiting (e.g. while the game screen renders). */
  prefetch(difficulty) {
    const key = this.key(difficulty);
    if (this.buffer(key).length <= LOW_WATER) this.fill(key).catch(() => {});
  }

  /** Next question for `difficultyOverride` (1|2|3|'mixed') or the feed's default difficulty. */
  async next(difficultyOverride) {
    const key = this.key(difficultyOverride);
    const buf = this.buffer(key);
    while (buf.length === 0) {
      if (this.closed) throw new ApiError("Question feed closed", 0);
      await this.fill(key);
    }
    const q = buf.shift();
    this.remember(q);
    if (buf.length <= LOW_WATER) this.fill(key).catch(() => {});
    return q;
  }

  remember(q) {
    const sig = signature(q);
    this.recent.push(sig);
    this.recentSet.add(sig);
    while (this.recent.length > RECENT_LIMIT) this.recentSet.delete(this.recent.shift());
  }

  fill(key) {
    if (this.closed) return Promise.resolve();
    if (this.inflight.has(key)) return this.inflight.get(key);
    const params = new URLSearchParams({ difficulty: key, count: String(BATCH_SIZE) });
    if (this.topics.length) params.set("topics", this.topics.join(","));
    if (this.types) params.set("types", this.types);
    const job = request(`/api/questions?${params}`)
      .then((data) => {
        if (this.closed) return;
        const incoming = (data.questions || []).filter((q) => q && q.id && Array.isArray(q.choices));
        const buf = this.buffer(key);
        const seen = new Set([...this.recentSet, ...buf.map(signature)]);
        const fresh = [];
        for (const q of incoming) {
          const sig = signature(q);
          if (seen.has(sig)) continue;
          seen.add(sig);
          fresh.push(q);
        }
        // With very few generators everything may be a repeat; never starve.
        if (fresh.length === 0 && buf.length === 0 && incoming.length) fresh.push(incoming[0]);
        buf.push(...fresh);
        if (incoming.length === 0 && buf.length === 0) throw new ApiError("The server sent no questions", 500);
      })
      .finally(() => this.inflight.delete(key));
    this.inflight.set(key, job);
    return job;
  }

  close() {
    this.closed = true;
    this.buffers.clear();
  }
}
