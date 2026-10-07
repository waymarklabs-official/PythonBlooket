"""Hosted games: HTTP API (blueprint).  The game rules live in :mod:`pyblooket.games`.

(Placeholder: the real endpoints are added by the hosted-games work. ``lan_urls`` is used
by the launcher in app.py.)
"""

from __future__ import annotations

import socket

from flask import Blueprint

bp = Blueprint("hosting", __name__)


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
