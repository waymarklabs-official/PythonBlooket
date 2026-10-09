/**
 * Client for hosted games (see pyblooket/hosting.py for the endpoints).
 *
 *   const { code, host_token } = await hostCreate({ mode: "live", ... });
 *   const host = hostSession(code, host_token);
 *   const poller = new Poller((since) => host.state(since), { onState, onFatal });
 *   poller.start();
 *   await host.action("start");
 *
 *   const joined = await playJoin({ code, name, avatar });
 *   const me = playerSession(code, joined.token);
 *
 * Every response from the server carries `server_time` (epoch seconds). `clock` turns that
 * into a countdown that is right even when the device's clock is off:
 *   clock.remaining(state.deadline)  // seconds left
 */

import { ApiError } from "./api.js";
import { storageGet, storageSet } from "./ui.js";

const REQUEST_TIMEOUT_MS = 10000;

export class GameApiError extends ApiError {
  constructor(message, status = 0, reason = "") {
    super(message, status);
    this.name = "GameApiError";
    this.reason = reason; // "not_found" | "bad_token" | "locked" | "name_taken" | ... | "network"
  }
}

// ---------------------------------------------------------------------------
// Server clock
// ---------------------------------------------------------------------------

/** Estimates (server time - local time); keeps the sample with the smallest round trip. */
export const clock = {
  offset: 0,
  bestRtt: Infinity,
  samples: 0,
  /** Feed every response: sentAt/receivedAt are Date.now() values (ms) around the request. */
  sync(serverTime, sentAt, receivedAt) {
    if (!Number.isFinite(serverTime)) return;
    const rtt = Math.max(0, receivedAt - sentAt);
    const estimate = serverTime - (sentAt + rtt / 2) / 1000;
    // A much faster sample is more trustworthy; otherwise drift slowly towards new ones.
    if (this.samples === 0 || rtt <= this.bestRtt) {
      this.offset = estimate;
      this.bestRtt = rtt;
    } else {
      this.offset += (estimate - this.offset) * 0.1;
      this.bestRtt = this.bestRtt * 1.05 + 1; // let a stale "best" fade so we re-learn after a network change
    }
    this.samples++;
  },
  /** Server epoch seconds, as the server would read them right now. */
  now() {
    return Date.now() / 1000 + this.offset;
  },
  /** Seconds until a server timestamp (negative once it has passed). */
  remaining(serverTimestamp) {
    return serverTimestamp - this.now();
  },
};

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function call(method, url, { body, headers = {} } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  const sentAt = Date.now();
  let res;
  try {
    res = await fetch(url, {
      method,
      signal: ctrl.signal,
      headers: { Accept: "application/json", ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new GameApiError("Can't reach the game server. Check your connection.", 0, "network");
  } finally {
    clearTimeout(timer);
  }
  const receivedAt = Date.now();
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (data && typeof data.server_time === "number") clock.sync(data.server_time, sentAt, receivedAt);
  if (!res.ok) throw new GameApiError((data && data.error) || `Server error (${res.status})`, res.status, (data && data.reason) || "");
  if (!data) throw new GameApiError("Bad response from the server", res.status, "bad_response");
  return data;
}

const sinceQuery = (since) => (Number.isInteger(since) ? `?since=${since}` : "");

// ---------------------------------------------------------------------------
// Host
// ---------------------------------------------------------------------------

/** Create a game. settings: see HOSTING_API.md. -> {code, host_token, game, join_urls, lan, join_url_path} */
export const hostCreate = (settings) => call("POST", "/api/host/games", { body: settings });

/** -> {lan, bind_host, port, urls} */
export const hostLan = () => call("GET", "/api/host/lan");

/** URL of a QR code image (SVG) for `text`. */
export const qrUrl = (text) => `/api/host/qr?text=${encodeURIComponent(text)}`;

export function hostSession(code, token) {
  const headers = { "X-Host-Token": token };
  return {
    code,
    token,
    /** Host state (or {unchanged: true, version}). */
    state: (since) => call("GET", `/api/host/games/${code}${sinceQuery(since)}`, { headers }),
    /** start | skip | next | end | lock {locked} | kick {player_id} -> updated host state. */
    action: (name, body = {}) => call("POST", `/api/host/games/${code}/${name}`, { body, headers }),
    csvUrl: () => `/api/host/games/${code}/results.csv?token=${encodeURIComponent(token)}`,
  };
}

// ---------------------------------------------------------------------------
// Player
// ---------------------------------------------------------------------------

/** -> {exists, title, mode, phase, locked, players} (throws GameApiError reason "not_found"). */
export const playLookup = (code) => call("GET", `/api/play/lookup?code=${encodeURIComponent(code)}`);

/** body {code, name, avatar, token?} -> {player_id, token, code, state} */
export const playJoin = (body) => call("POST", "/api/play/join", { body });

export function playerSession(code, token) {
  const headers = { "X-Player-Token": token };
  return {
    code,
    token,
    state: (since) => call("GET", `/api/play/${code}/state${sinceQuery(since)}`, { headers }),
    /** response: int | string[] | int[] | string (see HOSTING_API.md). */
    answer: (qid, response) => call("POST", `/api/play/${code}/answer`, { body: { qid, response }, headers }),
    run: (qid, codeText) => call("POST", `/api/play/${code}/run`, { body: { qid, code: codeText }, headers }),
    leave: () => call("POST", `/api/play/${code}/leave`, { body: {}, headers }),
  };
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------

const FATAL_REASONS = new Set(["not_found", "kicked", "bad_token"]);

/**
 * Sequential poller (never overlaps requests). `fetchState(since)` returns the state JSON.
 * onState(state) runs only when something changed. onError(err) on transient failures
 * (polling carries on with a back-off); onFatal(err) once, for not_found / kicked / bad_token
 * (polling stops).
 */
export class Poller {
  constructor(fetchState, { onState, onError, onFatal, interval = 1000 } = {}) {
    this.fetchState = fetchState;
    this.onState = onState || (() => {});
    this.onError = onError || (() => {});
    this.onFatal = onFatal || (() => {});
    this.interval = interval;
    this.version = null;
    this.timer = 0;
    this.running = false;
    this.failures = 0;
    this.inflight = false;
    this.last = null;
    this._onVisible = () => {
      if (this.running && !document.hidden) this.nudge();
    };
  }

  start() {
    if (this.running) return;
    this.running = true;
    document.addEventListener("visibilitychange", this._onVisible);
    this.nudge();
  }

  stop() {
    this.running = false;
    clearTimeout(this.timer);
    document.removeEventListener("visibilitychange", this._onVisible);
  }

  /** Poll right now (e.g. after the player pressed something). */
  nudge() {
    if (!this.running) return;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this._tick(), 0);
  }

  /** Accept a state that arrived some other way (e.g. in an action's response). */
  push(state) {
    if (!state || state.unchanged) return;
    if (Number.isInteger(state.version) && this.version !== null && state.version < this.version) return;
    this.version = state.version ?? this.version;
    this.last = state;
    this.onState(state);
  }

  async _tick() {
    if (!this.running || this.inflight) return;
    this.inflight = true;
    let delay = document.hidden ? Math.max(this.interval, 3000) : this.interval;
    try {
      const state = await this.fetchState(this.version === null ? undefined : this.version);
      this.failures = 0;
      if (!this.running) return;
      if (!state.unchanged) this.push(state);
    } catch (err) {
      if (!this.running) return;
      if (err && FATAL_REASONS.has(err.reason)) {
        this.stop();
        this.onFatal(err);
        return;
      }
      this.failures++;
      delay = Math.min(5000, this.interval * (1 + this.failures));
      this.onError(err, this.failures);
    } finally {
      this.inflight = false;
    }
    if (this.running) this.timer = setTimeout(() => this._tick(), delay);
  }
}

// ---------------------------------------------------------------------------
// Remembering games across page reloads
// ---------------------------------------------------------------------------

const HOSTED_KEY = "pyblooket.hosting";
const JOINED_KEY = "pyblooket.joined";

export const savedHost = {
  get: () => {
    const v = storageGet(HOSTED_KEY, null);
    return v && typeof v.code === "string" && typeof v.token === "string" ? v : null;
  },
  set: (code, token, title = "") => storageSet(HOSTED_KEY, { code, token, title, at: Date.now() }),
  clear: () => storageSet(HOSTED_KEY, null),
};

export const savedPlayer = {
  get: () => {
    const v = storageGet(JOINED_KEY, null);
    return v && typeof v.code === "string" && typeof v.token === "string" ? v : null;
  },
  set: (info) => storageSet(JOINED_KEY, { ...info, at: Date.now() }),
  clear: () => storageSet(JOINED_KEY, null),
};

/** "483920" -> "483 920" for reading aloud. */
export const prettyCode = (code) => String(code).replace(/^(\d{3})(\d+)$/, "$1 $2");

/** Keep only digits, max 6 (for the join box). */
export const cleanCode = (raw) => String(raw || "").replace(/\D/g, "").slice(0, 6);
