"""Hosted games: the HTTP API (blueprint ``bp``, registered by app.py).  The game rules live in
:mod:`pyblooket.games`; the JSON shapes are documented in HOSTING_API.md.

Every route answers errors as ``{"error": "...", "reason": "<code>"}`` with an HTTP 4xx status.
Teacher endpoints need the ``X-Host-Token`` header (the CSV link may carry ``?token=``); student
endpoints need ``X-Player-Token``.  Request bodies are JSON and limited to 64 KB.
"""

from __future__ import annotations

import io
import json
import logging
import socket
from functools import wraps

from flask import Blueprint, Response, current_app, jsonify, request

from .games import GameError, GameStore

log = logging.getLogger(__name__)

MAX_BODY = 64 * 1024
MAX_QR_TEXT = 300
LOOPBACK = ("127.0.0.1", "localhost", "::1", "")
WILDCARD = ("0.0.0.0", "::")

bp = Blueprint("hosting", __name__)

# The one store of running games.  Tests swap it:  ``monkeypatch.setattr(hosting, "STORE", GameStore(...))``.
STORE = GameStore()


@bp.before_request
def _limit_body() -> None:
    # Werkzeug refuses (413) to read a body above this, whatever its Content-Length claims.
    request.max_content_length = MAX_BODY


def _error(err: GameError):
    return jsonify(err.payload()), err.status


def api(view):
    """Turn :class:`GameError` (and surprises) into the documented JSON error shape."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except GameError as err:
            return _error(err)
        except Exception:  # noqa: BLE001 - never leak a traceback page to a student's phone
            log.exception("hosting route %s failed", request.path)
            return jsonify({"error": "Something went wrong on the server.", "reason": "server_error"}), 500

    return wrapper


def _is_api_path() -> bool:
    return request.path.startswith(("/api/host", "/api/play"))


@bp.app_errorhandler(413)
def _too_large(exc):
    return jsonify({"error": "That request is too big.", "reason": "bad_request"}), 413


@bp.app_errorhandler(404)
def _not_found(exc):
    if _is_api_path():
        return jsonify({"error": "Not found.", "reason": "not_found"}), 404
    return exc


@bp.app_errorhandler(405)
def _bad_method(exc):
    if _is_api_path():
        return jsonify({"error": "Method not allowed.", "reason": "bad_request"}), 405
    return exc


def json_body(required: bool = False) -> dict:
    """The request's JSON object (``{}`` when the body is empty)."""
    length = request.content_length
    if length is not None and length > MAX_BODY:
        raise GameError("bad_request", "That request is too big.", status=413)
    raw = request.stream.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise GameError("bad_request", "That request is too big.", status=413)
    if not raw.strip():
        if required:
            raise GameError("bad_request", "Send a JSON body.")
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):
        raise GameError("bad_request", "The request body isn't valid JSON.") from None
    if not isinstance(data, dict):
        raise GameError("bad_request", "The request body must be a JSON object.")
    return data


def _since() -> int | None:
    return request.args.get("since", default=None, type=int)


def _host_token(allow_query: bool = False) -> str:
    token = request.headers.get("X-Host-Token", "")
    if not token and allow_query:
        token = request.args.get("token", "")
    return token


def _player_token() -> str:
    return request.headers.get("X-Player-Token", "")


def _bind() -> tuple[str, int]:
    """(host the server listens on, port) -- from app.py's launcher, else from this request."""
    cfg = current_app.config
    host = cfg.get("PYBLOOKET_BIND_HOST")
    port = cfg.get("PYBLOOKET_PORT")
    if not host or not port:
        req_host, _, req_port = request.host.rpartition(":") if ":" in request.host else (request.host, "", "")
        host = host or req_host.strip("[]") or "127.0.0.1"
        try:
            port = port or int(req_port or request.environ.get("SERVER_PORT") or 80)
        except ValueError:
            port = 80
    return str(host), int(port)


def lan_info() -> dict:
    host, port = _bind()
    lan = host not in LOOPBACK
    urls: list[str] = []
    if lan:
        urls = lan_urls(port) if host in WILDCARD else [f"http://{host}:{port}"]
    return {"lan": lan, "bind_host": host, "port": port, "urls": urls}


# --------------------------------------------------------------------------
# Teacher
# --------------------------------------------------------------------------


@bp.post("/api/host/games")
@api
def create_game():
    game = STORE.create(json_body(required=True))
    info = lan_info()
    path = f"/?join={game.code}"
    state = game.host_snapshot()
    return (
        jsonify(
            {
                "code": game.code,
                "host_token": game.host_token,
                "game": state,
                "join_url_path": path,
                "join_urls": [u + path for u in info["urls"]],
                "lan": info["lan"],
            }
        ),
        201,
    )


@bp.get("/api/host/lan")
@api
def host_lan():
    return jsonify(lan_info())


@bp.get("/api/host/qr")
@api
def host_qr():
    text = request.args.get("text", "")
    if not text or len(text) > MAX_QR_TEXT:
        raise GameError("not_found", "Nothing to encode.")
    try:
        import segno
    except ImportError:
        raise GameError("not_found", "QR codes need the 'segno' package (pip install segno).") from None
    try:
        buf = io.BytesIO()
        segno.make(text, error="m").save(buf, kind="svg", scale=8, border=2, dark="#000", light="#fff", xmldecl=False)
    except Exception:  # noqa: BLE001 - e.g. text too long for any QR version
        raise GameError("not_found", "That text can't be turned into a QR code.") from None
    return Response(buf.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@bp.get("/api/host/games/<code>")
@api
def host_state(code):
    return jsonify(STORE.get(code).host_state(_host_token(), _since()))


@bp.get("/api/host/games/<code>/results.csv")
@api
def host_csv(code):
    game = STORE.get(code)
    text = game.csv_text(_host_token(allow_query=True))
    return Response(
        text,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="pyblooket-{game.code}-results.csv"', "Cache-Control": "no-store"},
    )


@bp.post("/api/host/games/<code>/<action>")
@api
def host_action(code, action):
    game = STORE.get(code)
    body = json_body()
    return jsonify(game.host_action(_host_token(), action, body))


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------


@bp.get("/api/play/lookup")
@api
def play_lookup():
    return jsonify(STORE.get(request.args.get("code", "").strip()).lookup())


@bp.post("/api/play/join")
@api
def play_join():
    body = json_body(required=True)
    code = body.get("code")
    game = STORE.get(code.strip() if isinstance(code, str) else code)
    return jsonify(game.join(body.get("name"), body.get("avatar"), body.get("token")))


@bp.get("/api/play/<code>/state")
@api
def play_state(code):
    return jsonify(STORE.get(code).player_state(_player_token(), _since()))


@bp.post("/api/play/<code>/answer")
@api
def play_answer(code):
    game = STORE.get(code)
    body = json_body(required=True)
    return jsonify(game.answer(_player_token(), body.get("qid"), body.get("response")))


@bp.post("/api/play/<code>/run")
@api
def play_run(code):
    game = STORE.get(code)
    body = json_body(required=True)
    return jsonify(game.run_examples(_player_token(), body.get("qid"), body.get("code")))


@bp.post("/api/play/<code>/leave")
@api
def play_leave(code):
    game = STORE.get(code)
    json_body()
    return jsonify(game.leave(_player_token()))


# --------------------------------------------------------------------------
# Network helpers (also used by the launcher in app.py)
# --------------------------------------------------------------------------


def lan_addresses() -> list[str]:
    """This machine's private IPv4 addresses, best guess first (empty if offline)."""
    found: list[str] = []

    def add(ip: str) -> None:
        if ip and not ip.startswith(("127.", "169.254.", "0.")) and ip not in found:
            found.append(ip)

    # The address the OS would use to reach the internet (no packet is actually sent).
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            add(ip)
    except OSError:
        pass
    return found


def lan_urls(port: int) -> list[str]:
    return [f"http://{ip}:{port}" for ip in lan_addresses()]
