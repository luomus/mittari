"""FinBIF taxon id strings used in this app (``MX.<n>`` only)."""

from __future__ import annotations

import re

_MAX_NUM = 10_000_000


def normalize_taxon_id(raw: str) -> str | None:
    """Return ``MX.<n>`` with ``1 <= n <= 10_000_000``, else ``None``.

    Case-insensitive ``mx.`` prefix; leading zeros in ``n`` are stripped
    (e.g. ``MX.007`` → ``MX.7``).
    """
    s = (raw or "").strip()
    m = re.fullmatch(r"(?i)MX\.(\d+)", s)
    if not m:
        return None
    n = int(m.group(1))
    if n < 1 or n > _MAX_NUM:
        return None
    return f"MX.{n}"
