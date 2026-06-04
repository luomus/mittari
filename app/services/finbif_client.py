"""Minimal FinBIF (api.laji.fi) HTTP client."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class FinbifApiError(Exception):
    """Raised when the FinBIF API returns an error response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_json(url: str, *, timeout: float = 60.0) -> dict:
    """GET a JSON document from api.laji.fi using the warehouse REST headers."""
    token = (os.environ.get("LAJI_API_ACCESS_TOKEN") or "").strip()
    if not token:
        raise FinbifApiError("Access token is missing from environment.")

    logger.info("api.laji.fi request: %s", url)

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "API-Version": "1",
            "Accept-Language": "fi",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        msg = f"api.laji.fi error ({e.code})."
        if detail:
            msg = f"{msg} {detail}"
        raise FinbifApiError(msg, status_code=e.code) from e
    except urllib.error.URLError as e:
        raise FinbifApiError(f"Connection error to api.laji.fi: {e.reason!s}") from e

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise FinbifApiError("api.laji.fi response is not valid JSON.") from e

    if not isinstance(data, dict):
        raise FinbifApiError("api.laji.fi response is not a dictionary.")
    return data
