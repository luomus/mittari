"""URL paths that may be closed via DISABLED_ROUTE_PREFIXES (comma-separated)."""

from __future__ import annotations

import os
from functools import wraps
from typing import Callable, TypeVar

from flask import abort, current_app, request

F = TypeVar("F", bound=Callable[..., object])


def parse_disabled_route_prefixes() -> frozenset[str]:
    raw = os.environ.get("DISABLED_ROUTE_PREFIXES", "")
    parts: list[str] = []
    for chunk in raw.split(","):
        s = chunk.strip()
        if s:
            if not s.startswith("/"):
                s = "/" + s
            parts.append(s)
    return frozenset(parts)


def path_matches_disabled(path: str, disabled: frozenset[str]) -> bool:
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    path_n = path.rstrip("/") or "/"
    for d in disabled:
        d_n = d.rstrip("/") or "/"
        if d_n == "/":
            continue
        if path_n == d_n or path_n.startswith(d_n + "/"):
            return True
    return False


def is_url_path_disabled(path: str) -> bool:
    disabled = current_app.config.get("DISABLED_ROUTE_PREFIXES") or frozenset()
    return path_matches_disabled(path, disabled)


def reject_if_request_path_disabled(f: F) -> F:
    """Run before inner wrappers (e.g. cache): abort 404 when the request path is disabled."""

    @wraps(f)
    def wrapper(*args: object, **kwargs: object) -> object:
        disabled = current_app.config.get("DISABLED_ROUTE_PREFIXES") or frozenset()
        if path_matches_disabled(request.path, disabled):
            abort(404)
        return f(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
